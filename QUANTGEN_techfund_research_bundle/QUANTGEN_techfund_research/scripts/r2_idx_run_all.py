"""r2_idx_run_all.py -- runs the round-2 index and governance lab end to end.

    python3 r2_idx_run_all.py            # everything (about 20-25 minutes on 2 shared CPUs, peak memory < 1 GB)
    python3 r2_idx_run_all.py --skip-sim # reuse results/r2_idx_gate_sim*.csv (the 5,000-path simulation)

Order: 01 protective cards (Task 1) -> 03 averaging bias (Task 3) -> 02 gate simulation (Task 2)
       -> 04 validation -> 05 summary (writes /home/claude/datalab/r2/R2_IDX_summary.md).
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [('r2_idx_01_protective.py', []), ('r2_idx_03_averaging.py', []),
         ('r2_idx_02_gate_sim.py', ['2000', '1000', '2000']), ('r2_idx_04_validation.py', []),
         ('r2_idx_05_summary.py', [])]


def main():
    skip_sim = '--skip-sim' in sys.argv
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    t0 = time.time()
    for script, args in STEPS:
        if skip_sim and script == 'r2_idx_02_gate_sim.py' and os.path.exists(f'{HERE}/results/r2_idx_gate_sim.csv'):
            print(f'--- skip {script} (existing results)', flush=True)
            continue
        print(f'--- {script} {" ".join(args)}', flush=True)
        t = time.time()
        subprocess.run([sys.executable, f'{HERE}/{script}', *args], cwd=HERE, env=env, check=True)
        print(f'--- {script} done in {time.time() - t:.0f}s', flush=True)
    print(f'all done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
