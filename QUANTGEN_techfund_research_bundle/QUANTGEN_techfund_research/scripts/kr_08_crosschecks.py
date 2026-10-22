"""kr_08_crosschecks.py -- cross-checks against the literature figures quoted in the QUANTGEN context brief.

C1 1-month reversal: brief quotes 'Korean 1-month reversal -2.95%/month (t -3.77, 1999-2021)'. Our base test
   (quintiles, microcap screen) is much weaker. Re-run REV_1M as deciles and quintiles in three universes:
   ALL (base), ELIG (no microcap screen) and BROAD (no microcap screen, no 1,000 KRW price floor), EW,
   reported as winners-minus-losers (WML, the literature sign) and as the reversal spread, gross and net 35 bp.
C2 Momentum and turnover: brief quotes 'Korean 12-1 momentum negative in high-turnover stocks'. MOM_12_1
   quintile spread (Q5-Q1, EW, ALL universe) within TURN_1M terciles formed at t.
Periods: full sample (1996-04..2026-09) and 1999-01..2021-12. Monthly statistics, Newey-West 6 lags.
Output: results/kr_crosschecks.csv
"""
import sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import CACHE, RES, load_meta, open_mat, nw_tstat
import kr_02_signals as S
from kr_03_portfolios import Book, quantile_groups

C35 = 0.0035


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def main():
    t0 = time.time()
    dates, codes = load_meta()
    T, N = len(dates), len(codes)
    F = np.load(f'{CACHE}/form_monthly.npz')
    fidx = F['fidx']; K = len(fidx)
    D = S.load_data(); S.build_cum(D)
    R = np.asarray(open_mat('ret')); E = np.asarray(open_mat('exists')); TR = np.asarray(open_mat('traded'))
    # BROAD universe: listed, traded at t, operating company, >= 200 valid days in 252, Amount>0 on >= 4 of 5
    broad = np.zeros((K, N), bool)
    for k, t in enumerate(fidx):
        e = np.asarray(D.E[t]); nc = np.asarray(D.NCLS[t]); tr = np.asarray(D.TR[t])
        nv = S.window_count(D.CV, t, 252); na = S.window_count(D.CA, t, 5); nb = S.window_count(D.CB, t, 30)
        broad[k] = e & tr & (nc == 0) & (nv >= 200) & (na >= 4) & (nb == 0)
    univ = {'ALL': F['univ_all'], 'ELIG': F['elig'], 'BROAD': broad}
    rev, mom, turn = F['REV_1M'], F['MOM_12_1'], F['TURN_1M']
    books = {}
    defs = []
    for u in univ:
        for nq in (5, 10):
            for q in (1, nq):
                defs.append((f'REV_1M|{u}|n{nq}|Q{q}', lambda k, u=u, nq=nq, q=q: quantile_groups(rev[k], univ[u][k], nq, k) == q))
    for j, lab in ((1, 'TURNlow'), (2, 'TURNmid'), (3, 'TURNhigh')):
        for q in (1, 5):
            def f(k, j=j, q=q):
                U = F['univ_all'][k]
                ter = quantile_groups(turn[k], U & np.isfinite(mom[k]), 3, k)
                return quantile_groups(mom[k], U & (ter == j), 5, k) == q
            defs.append((f'MOM_12_1|ALL|{lab}|Q{q}', f))
    for name, _ in defs:
        books[name] = Book(N)
    per = {name: np.full(K, np.nan) for name, _ in defs}
    to = {name: np.full(K, np.nan) for name, _ in defs}
    nmem = {name: np.zeros(K, int) for name, _ in defs}
    for k in range(K):
        t = fidx[k]; te = fidx[k + 1] if k + 1 < K else T - 1
        Rb = np.nan_to_num(R[t + 1:te + 1].astype(np.float64), nan=0.0)
        A = np.cumprod(E[t + 1:te + 1], axis=0).astype(bool)
        G = np.cumprod(1.0 + Rb * A, axis=0)
        for name, fn in defs:
            m = np.flatnonzero(fn(k))
            if len(m) == 0:
                continue
            to[name][k], _ = books[name].rebalance(m, np.full(len(m), 1.0 / len(m)), E[t], TR[t])
            per[name][k] = np.prod(1.0 + books[name].hold(G)) - 1.0
            nmem[name][k] = len(m)
    log('books done')
    pstart = dates[fidx + 1]
    masks = {'full 1996-04..2026-09': np.ones(K, bool),
             '1999-01..2021-12': (pstart >= pd.Timestamp('1999-01-01')) & (pstart <= pd.Timestamp('2021-12-31'))}
    rows = []

    def emit(test, label, spread, tsum, members):
        for pl, m in masks.items():
            for cl, c in (('gross', 0.0), ('net35', C35)):
                x = spread[m] - c * tsum[m]
                x = x[np.isfinite(x)]
                rows.append(dict(test=test, series=label, period=pl, cost_level=cl, n_months=len(x),
                                 mean_monthly=x.mean(), ann_mean=x.mean() * 12,
                                 sharpe=x.mean() / x.std(ddof=1) * np.sqrt(12), nw_t=nw_tstat(x, 6),
                                 avg_names_per_leg=float(np.mean(members[m])),
                                 turnover_per_year_both_legs=float(np.nanmean(tsum[m]) * 12)))
    for u in univ:
        for nq in (5, 10):
            lo, hi = f'REV_1M|{u}|n{nq}|Q1', f'REV_1M|{u}|n{nq}|Q{nq}'
            tsum = to[lo] + to[hi]
            emit('C1 1-month reversal', f'{u} {"deciles" if nq == 10 else "quintiles"}: losers minus winners',
                 per[lo] - per[hi], tsum, (nmem[lo] + nmem[hi]) / 2)
            emit('C1 1-month reversal', f'{u} {"deciles" if nq == 10 else "quintiles"}: WML (literature sign, gross only meaningful)',
                 per[hi] - per[lo], tsum * 0, (nmem[lo] + nmem[hi]) / 2)
    for lab in ('TURNlow', 'TURNmid', 'TURNhigh'):
        lo, hi = f'MOM_12_1|ALL|{lab}|Q1', f'MOM_12_1|ALL|{lab}|Q5'
        emit('C2 momentum by turnover tercile', f'MOM_12_1 Q5-Q1 within {lab} tercile (ALL, EW)',
             per[hi] - per[lo], to[lo] + to[hi], (nmem[lo] + nmem[hi]) / 2)
    out = pd.DataFrame(rows)
    out = out[~((out.series.str.contains('WML')) & (out.cost_level == 'net35'))]
    out.to_csv(f'{RES}/kr_crosschecks.csv', index=False, float_format='%.6g')
    pd.set_option('display.width', 250)
    print(out[['series', 'period', 'cost_level', 'mean_monthly', 'sharpe', 'nw_t', 'avg_names_per_leg']].round(4).to_string())
    log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
