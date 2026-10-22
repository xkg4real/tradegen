"""kr_run_all.py -- run the Korea data lab end to end (about 10 minutes on 2 CPUs, peak memory about 2 GB).

  python3 kr_run_all.py            # base run + strict-return sensitivity + validation + charts
  python3 kr_run_all.py --fast     # skip the strict sensitivity run

Order: kr_01 panel -> kr_02 signals -> kr_03 portfolios -> kr_04 stats -> (strict: kr_02/03/04 --strict)
       -> kr_05 index timing + SPA -> kr_06 validation -> kr_07 charts -> kr_08 literature cross-checks
       -> kr_09 summary tables + markdown.
"""
import subprocess, sys, time

STEPS = [['kr_01_build_panel.py'], ['kr_02_signals.py'], ['kr_03_portfolios.py'], ['kr_04_stats.py']]
STRICT = [['kr_02_signals.py', '--strict'], ['kr_03_portfolios.py', '--strict'], ['kr_04_stats.py', '--strict']]
TAIL = [['kr_05_index_timing.py'], ['kr_06_validation.py'], ['kr_07_charts_summary.py'], ['kr_08_crosschecks.py'],
        ['kr_09_summary.py']]

if __name__ == '__main__':
    plan = STEPS + ([] if '--fast' in sys.argv else STRICT) + TAIL
    t0 = time.time()
    for step in plan:
        t = time.time()
        print(f'==> {" ".join(step)}', flush=True)
        subprocess.run([sys.executable, '-W', 'ignore', *step], check=True, cwd='/home/claude/datalab/scripts')
        print(f'    {time.time() - t:.0f}s', flush=True)
    print(f'all steps done in {time.time() - t0:.0f}s')
