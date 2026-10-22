"""r2_kr_run_all.py -- rerun the whole round-2 Korea data lab in order.

  python3 r2_kr_run_all.py              # everything (about 5 minutes, peak resident memory about 2.6 GB)
  python3 r2_kr_run_all.py --skip-build # reuse the extra matrices in cache/ (skip r2_kr_01)

Order: 01 extra matrices and formation flags -> 02 round-1 reproduction -> 03 momentum grid and claims ->
04 exclusion horse race -> 05 crash controls and stop-loss -> 06 reversal and low volatility -> 07 validation ->
08 charts and /home/claude/datalab/r2/R2_KR_summary.md -> SHA-256 of every result file (results/r2_kr_hashes.csv).
Logs: logs/<script>.log. Stops at the first failing script.
"""
import os, sys, time, glob, subprocess, resource
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r2_kr_common import RES2, sha256

SCRIPTS = ['r2_kr_01_build_extra.py', 'r2_kr_02_reproduce_r1.py', 'r2_kr_03_momentum.py', 'r2_kr_04_exclusion.py',
           'r2_kr_05_crash_controls.py', 'r2_kr_06_reversal_lowvol.py', 'r2_kr_07_validation.py', 'r2_kr_08_charts_summary.py']


def main():
    t0 = time.time()
    for sc in SCRIPTS:
        if '--skip-build' in sys.argv and sc.startswith('r2_kr_01'):
            continue
        t1 = time.time()
        with open(os.path.join(HERE, 'logs', sc.replace('.py', '.log')), 'w') as lf:
            rc = subprocess.run([sys.executable, os.path.join(HERE, sc)], cwd=HERE, stdout=lf, stderr=subprocess.STDOUT).returncode
        peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
        print(f'{sc:32s} rc={rc}  {time.time() - t1:6.0f}s  (max child RSS so far {peak:,.0f} MB)', flush=True)
        if rc != 0:
            sys.exit(f'{sc} failed; see logs/{sc.replace(".py", ".log")}')
    rows = [dict(file=os.path.basename(f), sha256=sha256(f), bytes=os.path.getsize(f))
            for f in sorted(glob.glob(f'{RES2}/*.csv')) if not f.endswith('r2_kr_hashes.csv')]
    pd.DataFrame(rows).to_csv(f'{RES2}/r2_kr_hashes.csv', index=False)
    val = pd.read_csv(f'{RES2}/r2_kr_validation.csv')
    print(f'validation {int(val.passed.sum())}/{len(val)} passed; {len(rows)} result files hashed; total {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
