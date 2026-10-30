"""Full Cloud acceptance run; isolated state and KEYLESS are required, original record restored on failure."""
import json,os,subprocess,sys,time
from pathlib import Path
root=Path('/workspace/tradegen');scratch=Path('/workspace/tradegen-session');label=sys.argv[1]
assert label in ('initial','final')
keys=('KIS_APP_KEY KIS_APP_SECRET KIS_ACCOUNT_8 KIS_ACCOUNT_PD UPBIT_ACCESS_KEY UPBIT_SECRET_KEY OKX_API_KEY OKX_API_SECRET OKX_API_PASSPHRASE OPENDART_API_KEY KRX_API_KEY FMP_API_KEY ANTHROPIC_API_KEY GS_CLIENT_ID GS_CLIENT_SECRET FINVIZ_API_KEY ALPACA_API_KEY ALPACA_SECRET_KEY FXMACRODATA_API_KEY').split()
assert all(os.environ.get(k)=='<unset>' for k in keys), 'KEYLESS prefix is required'
state=Path(os.environ['TRADEGEN_HOME']).resolve()
assert str(state).startswith(('/tmp/','/workspace/tradegen-session/')), 'isolated Cloud state is required'
assert state != Path.home()/'.tradegen'
assert not (root/'core/compliance/owner_pubkey.pem').exists(), 'unexpected owner key in Cloud checkout'
def listing(base):
 rows=[]
 if base.exists():rows.append(('.',0,0))
 for path in sorted(base.rglob('*')) if base.exists() else ():
  st=path.stat();rows.append((path.relative_to(base).as_posix(),0 if path.is_dir() else st.st_size,0 if path.is_dir() else st.st_mtime_ns))
 return rows
protected=(Path.home()/'.tradegen',Path.home()/'.nextgen')
before=[listing(p) for p in protected]
qa=root/'qa/acceptance_results.json';previous=qa.read_bytes()
log=scratch/f'task-19-{label}-full.log';start=time.perf_counter();result=None
print(f'Starting full acceptance run ({label}), isolated Cloud home, all 19 KEYLESS names asserted',flush=True)
try:
 with log.open('w') as stream:
  result=subprocess.run([sys.executable,'tests/run_all.py'],cwd=root,stdout=stream,stderr=subprocess.STDOUT,timeout=3600)
 wall=round(time.perf_counter()-start,3)
 after=[listing(p) for p in protected]
 rows=json.loads(qa.read_bytes())
 counts={v:sum(r['status']==v for r in rows) for v in ('PASS','FAIL','NOT_RUN')}
 info=dict(label=label,code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),exit_code=result.returncode,seconds=wall,total=len(rows),counts=counts,real_homes_unchanged=before==after,keyless=True,isolated_home=True,failures=[r for r in rows if r['status']=='FAIL'])
 (scratch/f'task-19-{label}-run.json').write_text(json.dumps(info,indent=2)+'\n')
 assert before==after, 'real-home metadata changed'
 assert result.returncode==0 and counts['FAIL']==0, 'full acceptance suite failed'
 raw=qa.read_bytes();qa.write_bytes(raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
 print(json.dumps(info),flush=True)
except BaseException:
 if qa.exists():(scratch/f'task-19-{label}-failed-record.json').write_bytes(qa.read_bytes())
 qa.write_bytes(previous)
 raise
