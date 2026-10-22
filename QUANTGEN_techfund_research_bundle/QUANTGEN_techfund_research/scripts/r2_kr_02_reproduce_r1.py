"""r2_kr_02_reproduce_r1.py -- prove round 2 runs on the round-1 panel: rebuild round-1 books with the
round-2 engine (r2_kr_common.run_books -> kr_03_portfolios.Book) and reproduce four round-1 headline numbers.

R1  MOM 12-1 long-short, ALL universe, EW, quintiles, 1996-04..2026-09: gross +9.3%/yr, Sharpe 0.45 (NW t 2.67),
    net-35 Sharpe 0.20                                            (round-1 summary, kr_signal_stats_long.csv)
R2  Exclusion screen: ALL EW universe minus the highest TURN_1M quintile, excess over the (gross) EW universe,
    net of 35 bp on the screened book: +3.6%/yr (t 5.63)            (round-1 summary 'Excl-worst excess')
R3  MOM 12-1 Q5-Q1 inside the high TURN_1M tercile (dependent sort, ALL, EW): +1.44%/month gross (t 3.41)
                                                                  (round-1 kr_crosschecks.csv, C2)
R4  Exclusion screen on VOL_3M (drop the most volatile quintile), same convention: +3.0%/yr (t 4.67)
Also: daily book returns are compared one-for-one with the round-1 cached series (port_daily_monthly.parquet).
Output: results/r2_kr_reproduce_r1.csv
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (Panel, run_books, series, stats, quantile_groups, weights, log, to_csv, CACHE)

R1RES = '/home/claude/datalab/kr/results'


def main():
    P = Panel()
    F = P.F
    U = F['univ_all']; mc = F['mcap']
    mom, turn, vol = F['MOM_12_1'], F['TURN_1M'], F['VOL_3M']

    def grp(sig, k, nq=5, mask=None):
        return quantile_groups(sig[k], U[k] if mask is None else mask, nq, k)

    def spec(name, memfn, rule='EW'):
        def fn(k):
            m = np.flatnonzero(memfn(k))
            return m, (weights(m, rule, mc[k]) if len(m) else np.array([]))
        return (name, fn)
    specs = [spec('UNIV|EW', lambda k: U[k]), spec('UNIV|VW', lambda k: U[k], 'VW'),
             spec('MOM|Q5', lambda k: grp(mom, k) == 5), spec('MOM|Q1', lambda k: grp(mom, k) == 1),
             spec('TURN|NOTQ5', lambda k: U[k] & (grp(turn, k) != 5)),
             spec('VOL|NOTQ5', lambda k: U[k] & (grp(vol, k) != 5))]
    for j, lab in ((3, 'high'),):
        def ter(k):
            return quantile_groups(turn[k], U[k] & np.isfinite(mom[k]), 3, k)
        for q in (1, 5):
            specs.append(spec(f'MOMxTURN{lab}|Q{q}',
                              lambda k, q=q, j=j: quantile_groups(mom[k], U[k] & (ter(k) == j), 5, k) == q))
    books = run_books(P, specs, progress=120)
    rows = []

    def add(test, item, ours, theirs, tol, note=''):
        # round-1 CSVs are written with 6 significant digits: allow that rounding (relative 1e-5) or tol
        ok = bool(np.isfinite(ours) and abs(ours - theirs) <= max(tol, 1e-5 * abs(theirs)))
        rows.append(dict(test=test, item=item, round2=ours, round1=theirs, abs_diff=abs(ours - theirs), tol=tol,
                         passed=ok, note=note))
        log(f'{test} {"PASS" if ok else "FAIL"} {item}: r2 {ours:.6g} vs r1 {theirs:.6g}')
    t1 = pd.read_csv(f'{R1RES}/kr_signal_stats_long.csv')

    def r1(sig, leg, cost, metric, w='EW'):
        q = t1[(t1.signal == sig) & (t1.universe == 'ALL') & (t1.weighting == w) & (t1.leg == leg) &
               (t1.cost_level == cost) & (t1.period == 'full') & (t1.metric == metric)]
        return float(q.value.iloc[0])
    # R1
    for cost, c in (('gross', 0.0), ('net35', 0.0035)):
        per, daily, to = series(P, books['MOM|Q5'], S=books['MOM|Q1'], c=c)
        st = stats(P, per, daily, to)
        for m in ('ann_mean', 'sharpe', 'nw_t', 'max_dd', 'turnover_per_year'):
            add('R1', f'MOM_12_1 LS EW {cost} {m}', st[m], r1('MOM_12_1', 'LS', cost, m), 1e-6)
    # R2, R4 (excess over the gross EW universe, screened book net of its own costs)
    for lab, b, sig in (('R2', 'TURN|NOTQ5', 'TURN_1M_LOW'), ('R4', 'VOL|NOTQ5', 'VOL_3M')):
        per, daily, to = series(P, books[b], B=books['UNIV|EW'], c=0.0035, cb=0.0)
        st = stats(P, per, daily, to)
        for m in ('ann_mean', 'nw_t', 'pct_pos_years'):
            add(lab, f'{sig} exclude-worst xs UEW net35 {m}', st[m], r1(sig, 'LO_excl_worst_xs_UEW', 'net35', m), 1e-6)
    # universe
    per, daily, to = series(P, books['UNIV|EW'], c=0.0035)
    st = stats(P, per, daily, to)
    add('R0', 'UNIV ALL EW net35 ann_mean', st['ann_mean'], r1('UNIV', 'LO', 'net35', 'ann_mean'), 1e-6)
    add('R0', 'UNIV ALL EW turnover/yr', st['turnover_per_year'], r1('UNIV', 'LO', 'net35', 'turnover_per_year'), 1e-6)
    # R3 (cross-check C2)
    cc = pd.read_csv(f'{R1RES}/kr_crosschecks.csv')
    q = cc[(cc.series.str.contains('TURNhigh')) & (cc.period.str.startswith('full')) & (cc.cost_level == 'gross')]
    per, daily, to = series(P, books['MOMxTURNhigh|Q5'], S=books['MOMxTURNhigh|Q1'], c=0.0)
    pm = np.isfinite(per)
    add('R3', 'MOM_12_1 Q5-Q1 in high TURN_1M tercile, mean %/month', per[pm].mean() * 100,
        float(q.mean_monthly.iloc[0]) * 100, 1e-6)
    from kr_common import nw_tstat
    add('R3', 'same, NW t', nw_tstat(per, 6), float(q.nw_t.iloc[0]), 1e-6)
    # one-for-one daily comparison with round-1 cached books
    D1 = pd.read_parquet(f'{CACHE}/port_daily_monthly.parquet')
    for ours, theirs in (('UNIV|EW', 'monthly|UNIV|ALL|EW|ALL'), ('UNIV|VW', 'monthly|UNIV|ALL|VW|ALL'),
                         ('MOM|Q5', 'monthly|MOM_12_1|ALL|EW|Q5'), ('MOM|Q1', 'monthly|MOM_12_1|ALL|EW|Q1'),
                         ('TURN|NOTQ5', 'monthly|TURN_1M|ALL|EW|NOTQ5'), ('VOL|NOTQ5', 'monthly|VOL_3M|ALL|EW|NOTQ5')):
        a = books[ours]['daily']; b = D1[theirs].values
        same_nan = bool((np.isnan(a) == np.isnan(b)).all())
        md = float(np.nanmax(np.abs(a - b)))
        add('R5', f'daily series identical: {ours}', md, 0.0, 1e-12, f'same NaN pattern: {same_nan}')
    out = pd.DataFrame(rows)
    to_csv(out, 'r2_kr_reproduce_r1.csv')
    log(f'{int(out.passed.sum())}/{len(out)} reproduction checks passed')


if __name__ == '__main__':
    main()
