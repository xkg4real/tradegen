"""Offline acceptance launcher; source fingerprint and QA preservation."""
from pathlib import Path
import argparse
import hashlib
import importlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('/workspace/tradegen-protective-state-1113')
OUT = Path('/workspace/tradegen-session/protective-state-1113')
KEYS = '''KIS_APP_KEY KIS_APP_SECRET KIS_ACCOUNT_8 KIS_ACCOUNT_PD UPBIT_ACCESS_KEY
UPBIT_SECRET_KEY OKX_API_KEY OKX_API_SECRET OKX_API_PASSPHRASE OPENDART_API_KEY KRX_API_KEY
FMP_API_KEY ANTHROPIC_API_KEY GS_CLIENT_ID GS_CLIENT_SECRET FINVIZ_API_KEY ALPACA_API_KEY
ALPACA_SECRET_KEY FXMACRODATA_API_KEY'''.split()
for key in KEYS:
    os.environ[key] = '<unset>'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['NEXTGEN_SKILLS_ROOT'] = str(Path('/workspace/.cloud-setup/dependencies') /
                                      'claude-trading-skills-cb0f3aadffed6d1089db4b224162c964368baa46')
os.environ['TRADEGEN_HOME'] = str(OUT / 'isolated-home')
os.environ['TRADEGEN_RUNS_DIR'] = str(OUT / 'runs')
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def source_hash():
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    rows = [(name, hashlib.sha256((ROOT / name).read_bytes()).hexdigest()) for name in files
            if name and name.endswith(('.py', '.yaml'))]
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).hexdigest()


def metadata(root):
    return [(p.relative_to(root).as_posix(), p.stat().st_size, p.stat().st_mtime_ns)
            for p in sorted(root.rglob('*')) if p.is_file()] if root.exists() else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('selectors', nargs='*', help='suite:module/test or suite:module/')
    args = parser.parse_args()
    protected = [Path.home() / '.tradegen', Path.home() / '.nextgen']
    before = [metadata(p) for p in protected]
    frozen = source_hash()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    qa = ROOT / 'qa/acceptance_results.json'
    prior = qa.read_bytes()
    started = time.perf_counter()
    from tests.run_all import run, tests
    try:
        if args.full:
            entries = tests()
        else:
            entries = []
            seen = set()
            for selector in args.selectors:
                suite, match = selector.split(':', 1)
                module = importlib.import_module('tests.' + suite + '_acceptance')
                selected = [(suite + '/' + name, fn) for name, fn in module.tests() if match in name]
                if not selected:
                    raise ValueError('selector matched no tests: ' + selector)
                for name, fn in selected:
                    if name not in seen:
                        entries.append((name, fn))
                        seen.add(name)
        rows = run(entries)
        after = [metadata(p) for p in protected]
        counts = {s: sum(row['status'] == s for row in rows) for s in ('PASS', 'FAIL', 'NOT_RUN')}
        report = dict(label=args.label, head=head, source_hash=frozen, total=len(rows), counts=counts,
                      seconds=round(time.perf_counter() - started, 3), keyless_names=len(KEYS),
                      source_unchanged=frozen == source_hash(), real_homes_unchanged=before == after,
                      failures=[row for row in rows if row['status'] == 'FAIL'])
        (OUT / (args.label + '-rows.json')).write_text(json.dumps(rows, indent=2) + '\n')
        (OUT / (args.label + '-summary.json')).write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
        return 0 if counts['FAIL'] == 0 and report['source_unchanged'] and before == after else 1
    finally:
        if qa.read_bytes() != prior:
            qa.write_bytes(prior)


if __name__ == '__main__':
    raise SystemExit(main())
