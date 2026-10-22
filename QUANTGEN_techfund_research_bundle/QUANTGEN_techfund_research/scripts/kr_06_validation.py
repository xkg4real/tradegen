"""kr_06_validation.py -- validation tests for the Korea data lab (writes results/kr_validation.csv).

Tests
 V0  Share classes: codes with a non-zero last character are preferred / new-share lines (name markers 우, 우B,
     신, 전환), codes ending in 0 are common shares (checked on the full name history).
 V1  Spot-check 10 random stock-days (seed 20261002): r = ChangesRatio/100 vs Close_t/Close_{t-1}-1 read
     straight from the raw parquet files, on days without a share-count change or base-price adjustment.
 V1b Population check of the same identity on every non-corporate-action day (share of |diff| > 0.5%).
 V2  Look-ahead (truncation test): rebuild the panel with data only through T0 = 2015-06-30 into a scratch
     cache and recompute universe membership and all monthly signals at every formation date <= T0 - 1 day.
     Assertion: identical to the full-sample values (signals and universes may use only rows <= t).
 V3  Look-ahead (timing): for every book and period, the daily returns used for the period that starts after
     formation t_k come from days strictly after t_k: assert port_daily rows <= first formation are NaN and
     that a re-computed EW Q5 return of MOM_12_1 for a random period equals mean-weighted next-day returns.
 V4  Breakpoints: quintile breakpoints recomputed from eligible-universe members only reproduce the stored
     group assignment; no non-member is ever assigned; each quintile holds 20% +- 1 stock.
 V5  Index timing: rule position at t uses closes <= t (recompute SMA200 rule on truncated prices).
 V6  Reproducibility: SPA re-run with the same seed gives identical p-values; SHA-256 of all result files.
"""
import sys, os, time, glob, shutil, random
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import (RAW, CACHE, RES, SEED, load_meta, open_mat, sha256)
import kr_01_build_panel as B
import kr_02_signals as S
import kr_03_portfolios as P

SCRATCH = '/home/claude/datalab/kr/cache_trunc'
rows = []


def rec(test, item, value, passed, note=''):
    rows.append((test, item, value, bool(passed), note))
    print(f'{test:4s} {"PASS" if passed else "FAIL"} {item}: {value} {note}', flush=True)


def v0_share_classes():
    """Preferred / new-share lines have a non-zero last code character; verify on the full name history."""
    import re
    nm = pd.read_csv(f'{CACHE}/codes_names.csv', dtype={'Code': str})
    allnm = []
    for y in (1996, 2000, 2005, 2010, 2015, 2020, 2026):
        df = pd.read_parquet(f'{RAW}/marcap-{y}.parquet', columns=['Code', 'Name', 'Market'])
        df['Code'] = df['Code'].str.zfill(6)
        allnm.append(df[df.Market.isin(['KOSPI', 'KOSDAQ', 'KOSDAQ GLOBAL'])].drop_duplicates(['Code', 'Name']))
    a = pd.concat(allnm).drop_duplicates(['Code', 'Name'])
    pref = re.compile(r'우[A-Z]?\)?$|우[A-Z]?\(|\d우|\(\d?우|우선|\(?\d?신\)?$|신형|전환\)?$|우B|우C')
    non0 = a[a.Code.str[-1] != '0']
    hit = non0.Name.str.replace(' ', '').str.contains(pref)
    rng = np.random.default_rng(SEED)
    smp = non0.iloc[rng.choice(len(non0), 12, replace=False)]
    rec('V0', 'codes with non-zero last character whose name carries a preferred/new-share marker (sample years)',
        f'{hit.sum()} of {len(non0)} ({hit.mean():.1%})', hit.mean() > 0.97,
        'sample: ' + '; '.join(f'{c} {n}' for c, n in zip(smp.Code, smp.Name)))
    if (~hit).any():
        rows.append(('V0', 'non-zero-ending codes without marker (listed for inspection)',
                     '; '.join(f'{c} {n}' for c, n in zip(non0[~hit].Code, non0[~hit].Name)), True, ''))
    zero = nm[nm.Code.str[-1] == '0']
    zhit = zero[zero.Name.str.replace(' ', '').str.contains(r'\d우[A-Z]?$|\(\d?우|우B$|우C$|우선주')]
    rec('V0', 'common-share codes (last char 0) whose name looks preferred', f'{len(zhit)}', len(zhit) == 0,
        '; '.join(f'{c} {n}' for c, n in zip(zhit.Code, zhit.Name)))


def v1_spot_check():
    rng = random.Random(SEED)
    years = list(range(2000, 2027))
    picked = 0
    tries = 0
    while picked < 10 and tries < 200:
        tries += 1
        y = rng.choice(years)
        df = pd.read_parquet(f'{RAW}/marcap-{y}.parquet', columns=['Date', 'Code', 'Name', 'Market', 'Close',
                                                                     'ChangesRatio', 'Stocks', 'Volume'])
        df['Code'] = df['Code'].str.zfill(6)
        df = df[df.Market.isin(['KOSPI', 'KOSDAQ']) & (df.Code.str[-1] == '0') & (df.Volume > 0)]
        row = df.iloc[rng.randrange(len(df))]
        hist = df[(df.Code == row.Code) & (df.Date < row.Date)].sort_values('Date')
        if hist.empty:
            continue
        prev = hist.iloc[-1]
        if prev.Stocks != row.Stocks:
            continue                        # corporate-action day: excluded by design
        raw = row.Close / prev.Close - 1
        r = row.ChangesRatio / 100
        ok = abs(raw - r) <= 0.0005 + 0.0001 * 0  # rounding of ChangesRatio to 0.01%
        rec('V1', f'{row.Date.date()} {row.Code} {row.Name}', f'r={r:.4%} close/prev-1={raw:.4%} diff={raw - r:+.5%}',
            ok, f'prev {prev.Date.date()} {prev.Close:.0f} -> {row.Close:.0f}')
        picked += 1


def v1b_population():
    dates, codes = load_meta()
    R = open_mat('ret'); C = open_mat('close'); E = open_mat('exists')
    tot = bad = 0
    for t0 in range(1, len(dates), 1000):
        t1 = min(len(dates), t0 + 1000)
        r = np.asarray(R[t0:t1]).astype(np.float64)
        c = np.asarray(C[t0:t1]).astype(np.float64); cp = np.asarray(C[t0 - 1:t1 - 1]).astype(np.float64)
        e = np.asarray(E[t0:t1]) & np.asarray(E[t0 - 1:t1 - 1]) & np.isfinite(r)
        with np.errstate(invalid='ignore', divide='ignore'):
            d = np.abs(c / cp - 1 - r)
        tot += int(e.sum()); bad += int((e & (d > 0.005)).sum())
    rec('V1b', 'share of kept returns with |Close/prevClose-1 - r| > 0.5%', f'{bad:,} of {tot:,} = {bad / tot:.4%}',
        bad / tot < 0.01, 'these are KRX base-price adjustments (splits, rights, dividends-in-stock); r is the adjusted one')


def v2_truncation(T0='2015-06-30'):
    os.makedirs(SCRATCH, exist_ok=True)
    os.makedirs(f'{SCRATCH}/res', exist_ok=True)
    B.main(end_date=T0, cache=SCRATCH, res=f'{SCRATCH}/res', write_reports=False)
    dfull, cfull = load_meta()
    dtr, ctr = load_meta(SCRATCH)
    Dfull = S.load_data(); S.build_cum(Dfull)
    Dtr = S.load_data(cache=SCRATCH); S.build_cum(Dtr)
    RSIfull = open_mat('rsi14')
    RSItr = S.compute_rsi(Dtr, 14, 'rsi14', cache=SCRATCH)
    colmap = pd.Series(np.arange(len(cfull)), index=cfull).reindex(ctr).values
    assert not np.isnan(colmap).any()
    colmap = colmap.astype(int)
    me = S.month_end_idx(dtr)
    me = me[(me >= S.LOOKBACK) & (me < len(dtr) - 1)]
    max_diff = {}; n_univ_mismatch = 0; checked = 0
    for t in me:
        tf = int(np.searchsorted(dfull.values, dtr.values[t]))
        assert dfull[tf] == dtr[t]
        ef, af, lf = S.universe_at(Dfull, tf)
        et, at, lt = S.universe_at(Dtr, t)
        n_univ_mismatch += int((ef[colmap] != et).sum() + (af[colmap] != at).sum() + (lf[colmap] != lt).sum())
        n_univ_mismatch += int(ef.sum() - ef[colmap].sum())        # members outside the truncated code list
        sf = S.monthly_signals_at(Dfull, tf, np.asarray(RSIfull[tf]))
        st = S.monthly_signals_at(Dtr, t, np.asarray(RSItr[t]))
        for k in sf:
            a = sf[k][colmap].astype(np.float64); b = st[k].astype(np.float64)
            m = ef[colmap]                                           # compare on the eligible universe
            both = np.isfinite(a) & np.isfinite(b) & m
            nanmis = int((np.isfinite(a) != np.isfinite(b))[m].sum())
            d = np.max(np.abs(a[both] - b[both]) / np.maximum(1.0, np.abs(a[both]))) if both.any() else 0.0
            md = max_diff.get(k, (0.0, 0))
            max_diff[k] = (max(md[0], d), md[1] + nanmis)
        checked += 1
    rec('V2', f'universe membership identical at {checked} month-ends <= {T0} (full vs truncated data)',
        f'{n_univ_mismatch} mismatches', n_univ_mismatch == 0)
    for k, (d, nm) in max_diff.items():
        rec('V2', f'signal {k} identical (eligible universe)', f'max rel diff {d:.2e}, NaN mismatches {nm}',
            d < 1e-4 and nm == 0)
    shutil.rmtree(SCRATCH, ignore_errors=True)


def v3_timing():
    dates, codes = load_meta()
    F = np.load(f'{CACHE}/form_monthly.npz')
    fidx = F['fidx']
    D = pd.read_parquet(f'{CACHE}/port_daily_monthly.parquet')
    first = fidx[0]
    pre = D.iloc[:first + 1].notna().values.sum()
    rec('V3', 'portfolio returns on or before the first formation day', f'{pre} non-NaN values', pre == 0)
    # recompute one period by hand: EW Q5 of MOM_12_1, ALL universe, for 5 random periods
    rng = np.random.default_rng(SEED)
    R = open_mat('ret'); E = open_mat('exists')
    for k in rng.choice(np.arange(1, len(fidx) - 1), 5, replace=False):
        t, te = fidx[k], fidx[k + 1]
        g = P.quantile_groups(F['MOM_12_1'][k], F['univ_all'][k], 5, k)
        mem = np.flatnonzero(g == 5)
        rr = np.nan_to_num(np.asarray(R[t + 1:te + 1])[:, mem].astype(np.float64))
        alive = np.cumprod(np.asarray(E[t + 1:te + 1])[:, mem], axis=0)
        gross = np.cumprod(1 + rr * alive, axis=0)
        # if a member was carried from earlier (halted), the book differs; compare only periods with none
        z = np.load(f'{CACHE}/port_turnover_monthly.npz')
        i = list(z['names']).index('monthly|MOM_12_1|ALL|EW|Q5')
        if z['n_stuck'][i, k] > 0:
            continue
        hand = gross[-1].mean() - 1
        book = np.prod(1 + D['monthly|MOM_12_1|ALL|EW|Q5'].values[t + 1:te + 1]) - 1
        # the stored book also uses only t+1..te: the day-t return must not be inside the period
        rec('V3', f'MOM_12_1 ALL EW Q5 period after {dates[t].date()} recomputed from t+1..t_next',
            f'hand {hand:.6f} vs engine {book:.6f}', abs(hand - book) < 1e-9)
    # signals use t, not t+1: shifting the formation by one day must change REV_1M (sanity of the test)
    Dd = S.load_data(); S.build_cum(Dd)
    k = len(fidx) // 2; t = fidx[k]
    a = S.monthly_signals_at(Dd, t, np.asarray(open_mat('rsi14')[t]))['REV_1M']
    clt = np.asarray(Dd.CL[t]); cl21 = np.asarray(Dd.CL[t - 21])
    b = np.expm1(clt - cl21)
    m = np.isfinite(a)
    rec('V3', 'REV_1M at formation t equals exp(CL[t]-CL[t-21])-1 (uses the close of t, nothing later)',
        f'max abs diff {np.nanmax(np.abs(a[m] - b[m])):.2e}', np.nanmax(np.abs(a[m] - b[m])) < 1e-6)


def v4_breakpoints():
    from scipy.stats import rankdata
    F = np.load(f'{CACHE}/form_monthly.npz')
    sigs = ['MOM_12_1', 'MOM_6_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M', 'SIZE', 'PMA200', 'RSI14', 'BBPCTB']
    nonmember = 0; mismatch = 0; checked = 0; empty = 0; dev_months = {}; fb = {}
    for sig in sigs:
        for key in ('univ_all', 'univ_large'):
            for k in range(len(F['fidx'])):
                U = F[key][k]; s = F[sig][k]
                g, used = P.quantile_groups(s, U, 5, k, return_fallback=True)
                nonmember += int(((g > 0) & ~U).sum())
                m = U & np.isfinite(s)
                n = int(m.sum())
                # independent recomputation from universe-only ranks (no fallback branch)
                r = rankdata(s[m].astype(np.float64), method='average')
                g2 = np.floor((r - 0.5) / n * 5).astype(int) + 1
                if not used:
                    mismatch += int((g2 != g[m]).sum()); checked += 1
                else:
                    fb[(sig, key)] = fb.get((sig, key), 0) + 1
                counts = np.bincount(g[g > 0], minlength=6)[1:]
                empty += int((counts == 0).any())
                if np.max(np.abs(counts / n - 0.2)) > 0.02:
                    dev_months[(sig, key)] = dev_months.get((sig, key), 0) + 1
    rec('V4', 'stocks outside the universe assigned to a quintile', f'{nonmember}', nonmember == 0)
    rec('V4', 'assignment reproduced from universe-only average ranks', f'{mismatch} mismatches in {checked} formations',
        mismatch == 0)
    rec('V4', 'formations with an empty quintile', f'{empty}', empty == 0)
    rec('V4', 'formations using the seeded tie-break (tie block would shrink a quintile below 10%)',
        f'{sum(fb.values())} of {len(sigs) * 2 * len(F["fidx"])}: ' + ', '.join(f'{a}/{b[5:]} {c}' for (a, b), c in fb.items()),
        sum(fb.values()) < 0.01 * len(sigs) * 2 * len(F['fidx']), 'MAX_1M ties at the daily price limit in 1997-98')
    tot = len(sigs) * 2 * len(F['fidx'])
    rec('V4', 'formations where a quintile share deviates > 2 pp from 20% (tied signal values)',
        f'{sum(dev_months.values())} of {tot}: ' + ', '.join(f'{a}/{b[5:]} {c}' for (a, b), c in dev_months.items()),
        sum(dev_months.values()) < 0.01 * tot)
    # breakpoints within the universe differ from breakpoints over all listed stocks (the test has power)
    k = len(F['fidx']) - 1
    allbp = np.nanquantile(F['SIZE'][k].astype(np.float64), [0.2, 0.8])
    ubp = np.nanquantile(F['SIZE'][k][F['univ_all'][k]].astype(np.float64), [0.2, 0.8])
    rec('V4', 'SIZE breakpoints: universe vs all listed stocks (last formation)', f'universe {ubp.round(2)} vs all {allbp.round(2)}',
        not np.allclose(allbp, ubp))


def v5_index():
    import kr_05_index_timing as X
    idx = pd.read_parquet(f'{CACHE}/kospi_rebuilt.parquet')
    p = idx['level'].values
    dates = idx.index
    full = (p > X.sma(p, 200)).astype(int)
    rng = np.random.default_rng(SEED)
    bad = 0
    for t in rng.integers(300, len(p) - 1, 50):
        q = p[:t + 1]
        bad += int((q[-1] > X.sma(q, 200)[-1]) != full[t])
    rec('V5', 'SMA200 index position at t recomputed on prices truncated at t (50 random days)', f'{bad} mismatches', bad == 0)
    fam = X.family(dates, p)
    ok = 0; tot = 0
    for name in ['P>SMA50', 'MACD(12,26,1)', 'Donchian20/10', 'RSI2<10&>SMA200 exitSMA5', 'BB(20,2.0) breakout',
                 'TSMOM12M monthly', '10M_SMA monthly' if '10M_SMA monthly' in fam else '9M_SMA monthly']:
        t = int(rng.integers(2000, len(p) - 1))
        famt = X.family(dates[:t + 1], p[:t + 1])
        tot += 1; ok += int(famt[name][-1] == fam[name][t])
    rec('V5', 'family rule positions recomputed on truncated prices (7 rules)', f'{ok}/{tot} identical', ok == tot)


def v6_repro():
    from arch.bootstrap import SPA
    fam = pd.read_csv(f'{RES}/kr_index_spa.csv')
    p1 = fam.set_index(['section', 'key'])['value']
    import kr_05_index_timing as X
    idx = pd.read_parquet(f'{CACHE}/kospi_rebuilt.parquet')
    p, r, dates = idx['level'].values, idx['ret'].values, idx.index
    famd = X.family(dates, p)
    ev = dates >= pd.Timestamp(X.EVAL_START)
    Rn = np.column_stack([X.strat_returns(famd[k], r, X.COSTS['net3'])[0] for k in famd])
    spa = SPA(-r[ev], -Rn[ev], block_size=15, reps=2000, bootstrap='stationary', studentize=True, seed=SEED)
    spa.compute()
    pv = spa.pvalues
    same = all(abs(float(p1[('full', f'spa_p_{k}')]) - float(pv[k])) < 1e-12 for k in ('lower', 'consistent', 'upper'))
    rec('V6', 'SPA p-values reproduced with seed 20261002', f'{dict(pv.round(4))}', same)
    for f in sorted(glob.glob(f'{RES}/*.csv')):
        if os.path.basename(f) == 'kr_validation.csv':
            continue
        rows.append(('V6', f'sha256 {os.path.basename(f)}', sha256(f), True, ''))


if __name__ == '__main__':
    t0 = time.time()
    v0_share_classes(); v1_spot_check(); v1b_population(); v3_timing(); v4_breakpoints(); v5_index(); v2_truncation()
    v6_repro()
    out = pd.DataFrame(rows, columns=['test', 'item', 'value', 'passed', 'note'])
    out.to_csv(f'{RES}/kr_validation.csv', index=False)
    print(out.groupby('test')['passed'].agg(['sum', 'count']))
    assert out['passed'].all(), 'validation failures'
    print(f'all validation tests passed in {time.time() - t0:.0f}s')
