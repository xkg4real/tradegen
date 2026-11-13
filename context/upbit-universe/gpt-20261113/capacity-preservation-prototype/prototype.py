"""Offline scratch model only; not a production history implementation."""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json
import os
import sys
import importlib.util
from unittest.mock import patch

OUT = Path('/workspace/tradegen-session/capacity-preserve-1113')
sys.path.insert(0, '/workspace/tradegen-session/universe-pr4d-1113')
import verify
verify.OUT = OUT
os.environ['TRADEGEN_HOME'] = str(OUT / 'isolated-home')
os.environ['TRADEGEN_RUNS_DIR'] = str(OUT / 'runs')
os.environ['MPLCONFIGDIR'] = str(OUT / 'mpl')
from execution_launch import live_history as LH
spec = importlib.util.spec_from_file_location('actual_probe', '/workspace/tradegen-session/universe-pr4d-1113/review-capacity-actual.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
rows = []
original_row = LH._row

def capture_row(*args):
    row = original_row(*args)
    if 'holdings' in row['data']:
        rows.append(LH._canonical(row) + b'\n')
    return row

before_source = verify.source_hash()
with patch.object(LH, '_row', side_effect=capture_row):
    probe.actual_residual_capacity_refusal()
assert rows and rows[0] != rows[-1]
full_row, fallback_row = rows[0], rows[-1]
full = json.loads(full_row)
assert len(full['data']['holdings']) == 1500
assert full['data']['universe']['flags'] != 'unavailable'
assert full['data']['universe']['tickers'] != 'unavailable'
assert full['data']['receipt'] != 'unavailable'
assert len(fallback_row) == 279312

CHUNK = 65536
LIMIT = 16 * 1024 * 1024  # scratch candidate admission bound, not approved production cap
ROW_CAP = 262144

def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def digest(kind, raw):
    return sha256(b'TRADEGEN-SCRATCH-CAS-v1\0' + kind + b'\0' + raw).hexdigest()

class Refused(ValueError):
    pass

class ModelStore:
    """Single-writer crash model. Does NOT model BaselineHead or Windows power loss."""
    def __init__(self, root):
        self.root = root
        self.head = None
        self.memory = None
        self.journal = None

    def publish(self, kind, raw):
        name = digest(kind, raw)
        target = self.root / name
        if target.exists():
            if target.read_bytes() != raw:
                raise Refused('corrupt existing object')
            return name
        temp = self.root / (name + '.tmp')
        with temp.open('xb') as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        # The model is single-writer. Production needs validated no-overwrite publication + store lock.
        os.replace(temp, target)
        return name

    def get(self, kind, name, limit):
        if len(name) != 64 or any(c not in '0123456789abcdef' for c in name):
            raise Refused('object name')
        p = self.root / name
        if not p.is_file() or p.is_symlink():
            raise Refused('object missing or unsafe')
        raw = p.read_bytes()
        if len(raw) > limit or digest(kind, raw) != name:
            raise Refused('object hash or bound')
        return raw

    def write(self, raw, fail=None):
        if not 0 < len(raw) <= LIMIT:
            raise Refused('capacity admission')
        parts = [raw[i:i+CHUNK] for i in range(0, len(raw), CHUNK)]
        manifest = {'schema': 1, 'bytes': len(raw), 'logical_sha256': sha256(raw).hexdigest(),
                    'chunks': [{'sha256': digest(b'chunk', c), 'bytes': len(c)} for c in parts]}
        mraw = canonical(manifest)
        envelope = {'schema': 3, 'manifest': digest(b'manifest', mraw), 'bytes': len(raw)}
        eraw = canonical(envelope) + b'\n'
        if len(eraw) > ROW_CAP or len(mraw) > CHUNK:
            raise Refused('manifest or envelope bound')
        for c in parts:
            self.publish(b'chunk', c)
        if fail == 'after_chunks':
            raise Refused('injected crash')
        self.publish(b'manifest', mraw)
        if fail == 'after_manifest':
            raise Refused('injected crash')
        self.journal = eraw
        if fail == 'after_journal':
            raise Refused('injected crash')
        # In production this must be independent trusted-head CAS and validated readback.
        self.head = sha256(eraw).hexdigest()
        if fail == 'after_head':
            raise Refused('injected crash')
        self.memory = raw
        return eraw

    def read(self, envelope=None):
        eraw = self.journal if envelope is None else envelope
        if eraw is None or self.head != sha256(eraw).hexdigest():
            raise Refused('head mismatch; no auto-adopt')
        obj = json.loads(eraw)
        manifest = json.loads(self.get(b'manifest', obj['manifest'], CHUNK))
        if not 0 < manifest['bytes'] <= LIMIT or not 0 < len(manifest['chunks']) <= LIMIT//CHUNK:
            raise Refused('admission')
        chunks = []
        for i, desc in enumerate(manifest['chunks']):
            c = self.get(b'chunk', desc['sha256'], CHUNK)
            if len(c) != desc['bytes'] or (i < len(manifest['chunks'])-1 and len(c) != CHUNK):
                raise Refused('chunk boundary')
            chunks.append(c)
        raw = b''.join(chunks)
        if len(raw) != manifest['bytes'] or len(raw) != obj['bytes'] or sha256(raw).hexdigest() != manifest['logical_sha256']:
            raise Refused('logical payload mismatch')
        return raw

results=[]
def case(name, test):
    test()
    results.append({'test': name, 'status': 'PASS'})

def roundtrip(raw):
    with TemporaryDirectory(dir=OUT) as d:
        s=ModelStore(Path(d)); eraw=s.write(raw)
        assert len(eraw) <= ROW_CAP and s.read() == raw

case('actual_full_original_row_lossless', lambda: roundtrip(full_row))
for size in (CHUNK-1, CHUNK, CHUNK+1, ROW_CAP-1, ROW_CAP, ROW_CAP+1, LIMIT):
    case('byte_boundary_' + str(size), lambda size=size: roundtrip(b'z'*size))

def over_bound():
    with TemporaryDirectory(dir=OUT) as d:
        s=ModelStore(Path(d)); before=list(Path(d).iterdir())
        try: s.write(b'z'*(LIMIT+1))
        except Refused: pass
        else: raise AssertionError('accepted oversized logical payload')
        assert list(Path(d).iterdir()) == before and (s.head,s.journal,s.memory)==(None,None,None)
case('over_admission_no_files_or_state', over_bound)

def crashed(stage):
    with TemporaryDirectory(dir=OUT) as d:
        s=ModelStore(Path(d))
        try: s.write(full_row, fail=stage)
        except Refused: pass
        else: raise AssertionError('crash not injected')
        assert s.memory is None
        if stage == 'after_head':
            assert s.read() == full_row
        else:
            assert s.head is None
            try: s.read()
            except Refused: pass
            else: raise AssertionError('adopted uncommitted state')
for stage in ('after_chunks','after_manifest','after_journal','after_head'):
    case('crash_model_' + stage, lambda stage=stage: crashed(stage))

def bad_chunk(mode):
    with TemporaryDirectory(dir=OUT) as d:
        s=ModelStore(Path(d)); s.write(full_row)
        env=json.loads(s.journal); manifest=json.loads(s.get(b'manifest',env['manifest'],CHUNK))
        p=Path(d)/manifest['chunks'][0]['sha256']
        if mode=='missing': p.unlink()
        else: p.write_bytes(b'bad')
        try: s.read()
        except Refused: pass
        else: raise AssertionError('accepted missing/corrupt evidence')
for mode in ('missing','corrupt'):
    case(mode+'_chunk_refuses_whole_slot',lambda mode=mode:bad_chunk(mode))

assert before_source == verify.source_hash()
report={'scope':'offline scratch prototype; production source unmodified; no actual account/venue query',
        'original_probe_refusal_reproduced':True,'positions':1500,'book_raw_bytes':131072,
        'original_full_row_bytes':len(full_row),'original_fallback_row_bytes':len(fallback_row),
        'original_logical_row_sha256':sha256(full_row).hexdigest(),
        'prototype_chunk_bytes':CHUNK,'prototype_admission_bytes':LIMIT,
        'tests':results,'pass':len(results),'fail':0,'source_unchanged':True,
        'not_tested':['production v3 integration','BaselineHead CAS integration','Windows durability','kill/power-loss','replay chooser integration','real account failure']}
(OUT/'prototype-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
