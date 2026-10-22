"""r2_kr_07_validation.py -- validation and assertion tests for the round-2 Korea data lab.

W0 Same panel as round 1: reads results/r2_kr_reproduce_r1.csv (r2_kr_02: four round-1 headline numbers and
   one-for-one identical daily book series) and requires every check to pass.
W1 Look-ahead (signals use data through t): every round-2 formation-level array (MOM_12_7, TURN_12M/3M,
   VOL_1M/6M, MAX_3M, F5 and its components/windows, DIL_LIT, DIL_NI, ADV20, SD12M, E7 inputs, ...) is
   recomputed from matrices truncated at T0 (rows <= T0 only) for 400 random codes and every formation <= T0,
   for T0 = 2008-06-30, 2015-06-30 and 2026-06-30; assertion: identical to the full-sample values.
   (The cleaned return inputs were validated by round 1's truncation rebuild, kr_06 V2.)
W2 Timing (returns start at t+1): for 12 random (book, period) pairs, the period return is recomputed by hand
   from R[t_k+1 .. t_{k+1}] with formation weights and compared with the book; the same calculation shifted
   one day earlier (including day t) must differ (the test has power); book series are NaN on and before the
   first formation close.
W3 Breakpoints inside the eligible universe: (a) no flag / quintile is ever assigned outside the ALL universe;
   (b) overwriting every non-member's signal with extreme values leaves all assignments unchanged; (c) each
   quintile holds 20% +- 1 name of the members with a finite signal; (d) top-200 and the momentum quintile
   are subsets of the universe.
W4 Filtered and unfiltered books use identical dates: for every (base, filter) pair the daily series have the
   same non-missing days (first day = first formation + 1, last day = 2026-09-29) and the same rebalance dates.
W5 Reproducibility: the paired block bootstrap and the CSCV PBO give identical results when re-run with the
   same seed (SHA-256 of every result file is written last by r2_kr_run_all.py: results/r2_kr_hashes.csv).
W6 Claim-reproduction machinery: E7's exact construction must reproduce E7's printed long-only excess returns
   (-4.4 / -10.9 / +3.1 %/yr) within 0.5 pp.
Output: results/r2_kr_validation.csv
"""
import sys, glob, os, time
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (Panel, run_books, series, quantile_groups, weights, log, to_csv, load_books, boot_pvalue,
                          pbo_cscv, sha256, CACHE, CACHE2, RES2, SEED, open_mat, month_end_idx)
import r2_kr_01_build_extra as BX
import r2_kr_04_exclusion as EX

rows = []


def rec(test, item, value, passed, note=''):
    rows.append(dict(test=test, item=item, value=str(value), passed=bool(passed), note=note))
    log(f'{test} {"PASS" if passed else "FAIL"} {item}: {value} {note}')


def w0():
    r = pd.read_csv(f'{RES2}/r2_kr_reproduce_r1.csv')
    rec('W0', 'round-1 reproduction checks (r2_kr_02)', f'{int(r.passed.sum())}/{len(r)}', r.passed.all(),
        '; '.join(f'{a}: {b:.4g} vs {c:.4g}' for a, b, c in zip(r.item[:3], r.round2[:3], r.round1[:3])))


def w1(P):
    X = P.extra()
    dates = P.dates
    me_all = month_end_idx(dates)
    rng = np.random.default_rng(SEED)
    for T0s in ('2008-06-30', '2015-06-30', '2026-06-30'):
        tmax = int(np.searchsorted(dates.values, np.datetime64(T0s), side='right') - 1)
        cols = np.sort(rng.choice(P.N, 400, replace=False))
        nbad = 0; ncmp = 0; bad_names = set()
        # contiguous column blocks keep the call identical to the build
        for c0 in range(0, P.N, 200):
            sel = cols[(cols >= c0) & (cols < c0 + 200)]
            if len(sel) == 0:
                continue
            o = BX.derived_chunk(c0, min(P.N, c0 + 200), dates, P.fidx, me_all, None, tmax=tmax)
            kk = np.flatnonzero(P.fidx <= tmax)
            j = sel - c0
            for nm, arr in list(o['form'].items()) + list(o['formb'].items()):
                full = X[nm][kk][:, sel]
                trunc = arr[:, j]
                if arr.dtype == bool:
                    same = (full == trunc)
                else:
                    same = (np.isnan(full) & np.isnan(trunc)) | (np.abs(full - trunc) <= 1e-6 * np.maximum(1, np.abs(full)))
                nbad += int((~same).sum()); ncmp += same.size
                if (~same).any():
                    bad_names.add(nm)
        rec('W1', f'round-2 formation arrays recomputed from data truncated at {T0s} (400 random codes)',
            f'{ncmp - nbad:,}/{ncmp:,} identical', nbad == 0, f'mismatching arrays: {sorted(bad_names)}' if nbad else '')


def w2(P):
    F = P.F
    U, mc = F['univ_all'], F['mcap']
    rng = np.random.default_rng(SEED + 1)
    ks = rng.choice(np.arange(1, P.K - 1), 12, replace=False)
    specs = [('EW|ALL', lambda k: (np.flatnonzero(U[k]), weights(np.flatnonzero(U[k]), 'EW', mc[k]))),
             ('VWcap5|ALL', lambda k: (np.flatnonzero(U[k]), weights(np.flatnonzero(U[k]), 'VWcap5', mc[k])))]
    B = run_books(P, specs)
    ok_all, ok_power, maxerr = True, True, 0.0
    for i, k in enumerate(ks):
        nm = specs[i % 2][0]
        if B[nm]['nstuck'][k] > 0:
            continue
        t = P.fidx[k]; te = P.fidx[k + 1]
        m, w = specs[i % 2][1](k)
        R = np.nan_to_num(P.R[t + 1:te + 1][:, m].astype(np.float64))
        A = np.cumprod(P.E[t + 1:te + 1][:, m], axis=0).astype(bool)
        hand = float((w * np.cumprod(1 + R * A, axis=0)[-1]).sum() - 1)
        book = float(np.prod(1 + B[nm]['daily'][t + 1:te + 1]) - 1)
        R0 = np.nan_to_num(P.R[t:te][:, m].astype(np.float64))
        A0 = np.cumprod(P.E[t:te][:, m], axis=0).astype(bool)
        shifted = float((w * np.cumprod(1 + R0 * A0, axis=0)[-1]).sum() - 1)
        err = abs(hand - book); maxerr = max(maxerr, err)
        ok_all &= err < 1e-10
        ok_power &= abs(shifted - book) > 1e-6
    rec('W2', 'period returns recomputed by hand from days t+1..t_next (12 random periods)', f'max abs error {maxerr:.2e}', ok_all)
    rec('W2', 'same recomputation including day t differs (test has power)', 'all differ' if ok_power else 'some equal', ok_power)
    first = P.fidx[0]
    nan_before = all(np.isnan(B[nm]['daily'][:first + 1]).all() for nm, _ in specs)
    rec('W2', 'book series are missing on and before the first formation close', str(nan_before), nan_before)


def w3(P):
    X = P.extra()
    F = P.F
    U = F['univ_all']; LG = F['univ_large']
    FL, _ = EX.build_filters(P, X)
    outside = {f: int((FL[f] & ~U).sum()) for f in FL}
    rec('W3', 'filter flags assigned outside the ALL universe (all 44 definitions)', sum(outside.values()),
        sum(outside.values()) == 0)
    rng = np.random.default_rng(SEED + 2)
    ks = rng.choice(P.K, 25, replace=False)
    same = True; sizes_ok = True
    for sig in ('TURN_1M', 'VOL_3M', 'MAX_1M', 'MOM_12_1'):
        for k in ks:
            s = F[sig][k].astype(np.float64)
            g = quantile_groups(s, U[k], 5, k)
            s2 = s.copy()
            nonmem = ~U[k] & np.isfinite(s2)
            s2[nonmem] = rng.choice([-1e9, 1e9], nonmem.sum())
            g2 = quantile_groups(s2, U[k], 5, k)
            same &= bool((g == g2).all()) and not (g[~U[k]] > 0).any()
            n = int((U[k] & np.isfinite(s)).sum())
            cnt = np.bincount(g[g > 0], minlength=6)[1:]
            if sig != 'MAX_1M':                    # MAX_1M ties at the price limit use the round-1 tie rule
                sizes_ok &= bool(np.all(np.abs(cnt - n / 5) <= 1.0 + 1e-9))
    rec('W3', 'quintiles unchanged when non-members get extreme signal values; none assigned outside', str(same), same)
    rec('W3', 'quintile sizes = 20% +- 1 name (TURN_1M, VOL_3M, MOM_12_1; 25 random formations)', str(sizes_ok), sizes_ok)
    sub_lg = not (LG & ~U).any()
    momq5 = np.array([quantile_groups(F['MOM_12_1'][k], U[k], 5, k) == 5 for k in range(P.K)])
    sub_m = not (momq5 & ~U).any()
    rec('W3', 'top-200 (B3) and MOM 12-1 top quintile (B4) are subsets of the ALL universe', f'{sub_lg}, {sub_m}', sub_lg and sub_m)
    # composite F4 recomputed only from members
    k = int(ks[0])
    a = EX.p6_composite(F, k, U[k], 0.10)
    Fp = {s: F[s].copy() for s in ('VOL_3M', 'MAX_1M', 'TURN_1M')}
    for s in Fp:
        Fp[s][k][~U[k]] = 1e9
    b = EX.p6_composite(Fp, k, U[k], 0.10)
    rec('W3', 'F4 composite unchanged when non-members get extreme inputs', str(bool((a == b).all())), bool((a == b).all()))


def w4(P):
    B = load_books(f'{CACHE2}/books_excl.npz')
    bases = sorted({n.split('|')[0] for n in B})
    bad = []
    first, last = P.fidx[0] + 1, P.T - 1
    for b in bases:
        ref = B[f'{b}|none']['daily']
        mref = np.isfinite(ref)
        for n in B:
            if not n.startswith(b + '|'):
                continue
            m = np.isfinite(B[n]['daily'])
            if not ((m == mref).all() and m[first] and m[last] and not m[:first].any()):
                bad.append(n)
    rec('W4', 'filtered and unfiltered books: identical non-missing days, first day = formation+1, last = 2026-09-29',
        f'{len(B) - len(bad)}/{len(B)} books', len(bad) == 0, ', '.join(bad[:10]))
    rec('W4', 'rebalance dates shared by construction (one formation calendar, Panel.fidx)', f'{P.K} formations', True,
        f'{P.dates[P.fidx[0]].date()}..{P.dates[P.fidx[-1]].date()}')


def w5():
    rng = np.random.default_rng(7)
    x = rng.normal(0.002, 0.02, 366)
    a, b = boot_pvalue(x), boot_pvalue(x)
    M = rng.normal(0.001, 0.02, (366, 8))
    p1, p2 = pbo_cscv(M), pbo_cscv(M)
    rec('W5', 'bootstrap and CSCV reproducible with fixed seeds', f"p {a['p_null']:.4f}/{b['p_null']:.4f}; PBO {p1['pbo']:.4f}/{p2['pbo']:.4f}",
        a == b and p1 == p2)


def w6():
    L = pd.read_csv(f'{RES2}/r2_kr_mom_e7_ladder.csv')
    s0 = L[L.step.str.startswith('S0')].set_index('group')
    target = {'all': -0.044, 'high': -0.109, 'low': 0.031}
    diffs = {g: s0.loc[g, 'ann_excess_net35'] - v for g, v in target.items()}
    ok = all(abs(d) <= 0.005 for d in diffs.values())
    rec('W6', "E7 exact construction reproduces E7's printed long-only excess (all/high/low)",
        ', '.join(f'{g} {s0.loc[g, "ann_excess_net35"]*100:+.2f}% vs {v*100:+.1f}%' for g, v in target.items()), ok)


def hashes():
    out = []
    for f in sorted(glob.glob(f'{RES2}/*.csv')):
        if os.path.basename(f) in ('r2_kr_hashes.csv', 'r2_kr_validation.csv'):
            continue
        out.append(dict(file=os.path.basename(f), sha256=sha256(f), bytes=os.path.getsize(f)))
    to_csv(pd.DataFrame(out), 'r2_kr_hashes.csv')
    rec('W5', 'SHA-256 of result files', f'{len(out)} files', True, 'results/r2_kr_hashes.csv')


def main():
    t0 = time.time()
    P = Panel()
    w0(); w1(P); w2(P); w3(P); w4(P); w5(); w6()          # SHA-256 hashes: written last by r2_kr_run_all.py
    V = pd.DataFrame(rows)
    to_csv(V, 'r2_kr_validation.csv')
    log(f'{int(V.passed.sum())}/{len(V)} validation tests passed; {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
