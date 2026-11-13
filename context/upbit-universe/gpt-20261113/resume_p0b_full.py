"""Resume exact full-suite IDs after Cloud process loss, without inventing elapsed timings."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).parent))
from verify import ROOT, OUT, KEYS, source_hash, metadata
from tests.run_all import run, tests

EXPECTED='308ff5e1097a6e3960b83bae5ab723c61d453cfdaffef1f61af7c8c4864dd98b'
HEAD='a0b28d0fc0fee4a359f833f91a7c0f572777481e'
assert source_hash()==EXPECTED
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==HEAD
assert subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True)==''
entries=tests()
assert len({name for name,_ in entries})==len(entries)
original=OUT/'p0b-full-interrupted.log'
if not original.exists():original.write_bytes((OUT/'p0b-full.log').read_bytes())
prior=[]
for line in original.read_text().splitlines():
    parts=line.split(' ',2)
    if len(parts)<2 or parts[0] not in ('PASS','FAIL','NOT_RUN'):continue
    status,name=parts[:2]
    detail=parts[2] if len(parts)==3 else ''
    row={'test':name,'status':status,'seconds':None,'detail':detail if status=='FAIL' else '',
         'evidence':'interrupted process terminal log; per-test elapsed time unavailable'}
    if status=='NOT_RUN':row['reason']=detail
    prior.append(row)
assert [r['test'] for r in prior]==[n for n,_ in entries[:len(prior)]], 'terminal results are not an exact registry prefix'
assert not any(r['status']=='FAIL' for r in prior)
checkpoint=OUT/'p0b-full-resumed-checkpoint.json'
resumed=json.loads(checkpoint.read_text()) if checkpoint.exists() else []
assert [r['test'] for r in resumed]==[n for n,_ in entries[len(prior):len(prior)+len(resumed)]]
def save(path,value):
    pending=path.with_suffix(path.suffix+'.pending')
    with pending.open('w') as fh:
        json.dump(value,fh,indent=2);fh.write('\n');fh.flush();os.fsync(fh.fileno())
    pending.replace(path)
def home_hash():
    return hashlib.sha256(json.dumps([metadata(Path.home()/name) for name in ('.tradegen','.nextgen')],
                                    separators=(',',':')).encode()).hexdigest()
start_path=OUT/'p0b-full-resumed-start.json'
if start_path.exists():
    initial=json.loads(start_path.read_text())
    assert initial['source_hash']==EXPECTED and initial['real_home_metadata_sha256']==home_hash()
else:
    initial={'head':HEAD,'source_hash':EXPECTED,'real_home_metadata_sha256':home_hash(),
             'initial_terminal_rows':len(prior),'complete_registry_rows':len(entries),
             'initial_process_metadata_snapshot':'unavailable after environment restart'}
    save(start_path,initial)
print(json.dumps({'resuming':True,'recovered_terminal_rows':len(prior),
                  'checkpoint_rows':len(resumed),'remaining':len(entries)-len(prior)-len(resumed)}),flush=True)
qa=ROOT/'qa/acceptance_results.json';qa_before=qa.read_bytes()
started=time.perf_counter()
try:
    for entry in entries[len(prior)+len(resumed):]:
        resumed.extend(run([entry]))
        save(checkpoint,resumed)
    rows=prior+resumed
    assert [r['test'] for r in rows]==[n for n,_ in entries]
    counts={status:sum(r['status']==status for r in rows) for status in ('PASS','FAIL','NOT_RUN')}
    report={'label':'p0b-full','head':HEAD,'source_hash':EXPECTED,'total':len(rows),'counts':counts,
            'seconds':None,'resumed_segment_seconds':round(time.perf_counter()-started,3),
            'execution_mode':'complete registry across interrupted and resumed processes on identical frozen source',
            'initial_terminal_rows':len(prior),'resumed_rows':len(resumed),
            'keyless_names':len(KEYS),'source_unchanged':source_hash()==EXPECTED,
            'real_homes_unchanged':None,'real_homes_check_scope':'initial process snapshot lost; resumed segment checked',
            'resumed_real_homes_unchanged':home_hash()==initial['real_home_metadata_sha256'],
            'failures':[r for r in rows if r['status']=='FAIL']}
    save(OUT/'p0b-full-rows.json',rows)
    save(OUT/'p0b-full-summary.json',report)
    print(json.dumps(report),flush=True)
    assert counts['FAIL']==0 and report['source_unchanged'] and report['resumed_real_homes_unchanged']
finally:
    if qa.read_bytes()!=qa_before:qa.write_bytes(qa_before)
