"""r2_kr_03_momentum.py -- Task 1: Korean momentum reconciliation.

A. One standardised grid (ALL universe = round-1 eligible set with the 20th-percentile microcap cut):
   signal {MOM_12_1, MOM_12_7, MOM_6_1, HIGH52} x turnover tercile {all, low, mid, high} (independent sort:
   signal quintiles and turnover terciles are each formed over the whole ALL universe at the formation close;
   cell = intersection) x turnover definition {TURN_12M (primary; formation-period turnover as in the
   Lee-Swaminathan / Eom et al. design), TURN_1M (round-1)} x weighting {EW, VW (Marcap_t)} x leg
   {LS gross, LS net 35 bp (both legs pay), LO top quintile minus EW universe (net 35 bp on the LO book,
   gross benchmark = round-1/E7 convention), LO top quintile minus VW universe (same)} x period {1996-2005,
   2006-2015, 2015-07..2024-12, 2016-01..2026-09, full}. Newey-West t, 6 lags.
B. Each panel claim reproduced under its own definition on the same panel:
   B1 KJFS / brief (Eom, Chang, Kang, Lee, Park 2020) as approximated by P6 (p6_eom_x01.py): holding months
      2000-07..2019-06 excluding 2001-01; drop the highest-volatility decile (std of 12 monthly returns);
      top / bottom 30% of 12-month average turnover; momentum quintiles inside each group; EW; gross.
      Universes: all caps (BROAD + >= 15 traded days in the formation month) and ex-bottom-20% of Marcap.
      Diagnostic variant: signal and holding returns from UNADJUSTED closes (tests whether capital
      reductions / splits / bonus issues left in the price series can produce the paper's sign).
   B2 P6 decile sorts (p6_sorts.py): ALL universe, D10-D1, holding 2001-02..2026-09, EW and VW, gross, net 35/70.
   B3 Round-1: quintiles, ALL, EW, 1996-2026 (also in r2_kr_02); TURN_1M terciles, dependent sort.
   B4 E7 (e7_checks_part7.py): E7 liquid universe (Marcap >= 100bn, ADV20 >= 1bn, price >= 1,000, traded,
      not 관리/투자주의환기, not SPAC), E7 return cleaning, 12-month turnover terciles ranked across all listed
      common stocks, top quintile (rank 'first' + qcut), legs and benchmark re-weighted to equal weights EVERY
      DAY, cost 2 x (share of names replaced) x 35 bp, daily arithmetic mean x 252, iid daily t; 2015-07..2024-12.
      Attribution ladder: S0 E7 exact -> S1 same names, monthly buy-and-hold engine and round-1 returns ->
      S2 + terciles formed inside the liquid universe -> S3 grid cell (ALL universe, TURN_12M, MOM_12_1).
   B5 E5 / P2: top 500 eligible stocks by Marcap, D10-D1, daily buy-and-hold, 2000-01..2026-09, EW and VW.
Outputs: results/r2_kr_mom_grid_long.csv, r2_kr_mom_claims_long.csv, r2_kr_mom_e7_ladder.csv,
         cache/books_mom.npz (books reused by the crash-control script)
"""
import sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (Panel, run_books, series, stats, quantile_groups, weights, log, to_csv, save_books,
                          GRID_PERIODS, CACHE, CACHE2, open_mat, nw_tstat, month_end_idx)

SIGS = ['MOM_12_1', 'MOM_12_7', 'MOM_6_1', 'HIGH52']
TDEFS = ['TURN_12M', 'TURN_1M']
TERC = {'low': 1, 'mid': 2, 'high': 3}


def ordinal_pct(x, mask):
    """pandas rank(pct=True, method='first') of x over mask (ties by column order); NaN outside."""
    out = np.full(x.shape, np.nan)
    m = mask & np.isfinite(x)
    idx = np.flatnonzero(m)
    if len(idx) == 0:
        return out
    order = idx[np.argsort(x[idx], kind='stable')]
    out[order] = np.arange(1, len(order) + 1) / len(order)
    return out


def avg_pct(x, mask):
    """pandas rank(pct=True) (average ties) over mask."""
    from scipy.stats import rankdata
    out = np.full(x.shape, np.nan)
    m = mask & np.isfinite(x)
    if m.any():
        out[m] = rankdata(x[m], method='average') / m.sum()
    return out


def build_specs(P, X):
    F = P.F
    U = F['univ_all']; mc = F['mcap']
    sig = {s: (F[s] if s in F else X[s]) for s in SIGS}
    tdef = {'TURN_12M': X['TURN_12M'], 'TURN_1M': F['TURN_1M']}
    cache = {}

    def q5(s, k):
        key = ('q5', s, k)
        if key not in cache:
            cache[key] = quantile_groups(sig[s][k], U[k], 5, k)
        return cache[key]

    def t3(td, k):
        key = ('t3', td, k)
        if key not in cache:
            cache[key] = quantile_groups(tdef[td][k], U[k], 3, k)
        return cache[key]

    specs = []

    def add(name, memfn, rule):
        def fn(k):
            m = np.flatnonzero(memfn(k))
            return m, (weights(m, rule, mc[k]) if len(m) else np.array([]))
        specs.append((name, fn))
    for w in ('EW', 'VW'):
        add(f'UNIV|ALL|{w}', lambda k: U[k], w)
    # A. grid
    for s in SIGS:
        for w in ('EW', 'VW'):
            for q in (1, 5):
                add(f'GRID|{s}|all|all|{w}|Q{q}', lambda k, s=s, q=q: q5(s, k) == q, w)
                for td in TDEFS:
                    for tl, j in TERC.items():
                        add(f'GRID|{s}|{td}|{tl}|{w}|Q{q}', lambda k, s=s, q=q, td=td, j=j: (q5(s, k) == q) & (t3(td, k) == j), w)
    # B3 round-1 dependent sort (TURN_1M terciles, then momentum quintiles inside), EW, all three terciles
    mom = F['MOM_12_1']; t1 = F['TURN_1M']
    def dep(k, j, q):
        key = ('dep', k)
        if key not in cache:
            cache[key] = quantile_groups(t1[k], U[k] & np.isfinite(mom[k]), 3, k)
        return quantile_groups(mom[k], U[k] & (cache[key] == j), 5, k) == q
    for tl, j in TERC.items():
        for q in (1, 5):
            add(f'R1DEP|MOM_12_1|TURN_1M|{tl}|EW|Q{q}', lambda k, j=j, q=q: dep(k, j, q), 'EW')
    # B2 P6 deciles (ALL universe), MOM_12_1 and MOM_12_7, EW and VW
    for s in ('MOM_12_1', 'MOM_12_7'):
        for w in ('EW', 'VW'):
            for q in (1, 10):
                add(f'P6DEC|{s}|{w}|D{q}', lambda k, s=s, q=q: quantile_groups(sig[s][k], U[k], 10, k) == q, w)
    # B5 E5 / P2 top-500: deciles and quintiles
    T5 = X['top500']
    # looser top-500 (listed, traded at t, operating company, price >= 1,000, finite MOM_12_1): E5 sensitivity
    E_ = open_mat('exists'); TR_ = open_mat('traded'); NC_ = open_mat('namecls'); CLO_ = open_mat('close')
    T5L = np.zeros_like(T5)
    for k, t in enumerate(P.fidx):
        b = np.asarray(E_[t]) & np.asarray(TR_[t]) & (np.asarray(NC_[t]) == 0) & np.isfinite(mom[k]) & (mc[k] > 0) & \
            (np.asarray(CLO_[t]) >= 1000)
        idx = np.flatnonzero(b); order = idx[np.argsort(-mc[k, idx].astype(np.float64), kind='stable')]
        T5L[k, order[:500]] = True
    for w in ('EW', 'VW'):
        for q in (1, 10):
            add(f'TOP500L|MOM_12_1|n10|{w}|Q{q}', lambda k, q=q: quantile_groups(mom[k], T5L[k], 10, k) == q, w)
    for w in ('EW', 'VW'):
        for nq, qs in ((10, (1, 10)), (5, (1, 5))):
            for q in qs:
                add(f'TOP500|MOM_12_1|n{nq}|{w}|Q{q}', lambda k, nq=nq, q=q: quantile_groups(mom[k], T5[k], nq, k) == q, w)
        add(f'UNIV|TOP500|{w}', lambda k: T5[k], w)
    return specs


def eom_members(P, X, sig_mom, sd12, univ_name):
    """Eom et al. design as approximated by P6 (p6_eom_x01.py). Returns dict (group, leg) -> list of member arrays."""
    F = P.F
    base = X[univ_name] & (X['NDAYS_M'] >= 15)
    turn = X['TURN_12M']
    out = {(g, l): [np.array([], int)] * P.K for g in ('high', 'low') for l in ('W', 'L')}
    ok_k = np.zeros(P.K, bool)
    for k in range(P.K):
        t = P.dates[P.fidx[k]]
        if not (pd.Timestamp('2000-06-30') <= t <= pd.Timestamp('2019-05-31')) or (t.year == 2000 and t.month == 12):
            continue
        u = base[k] & np.isfinite(sig_mom[k]) & np.isfinite(turn[k]) & np.isfinite(sd12[k])
        sdp = avg_pct(sd12[k], u)
        u = u & (sdp <= 0.9)                                   # drop the highest-volatility decile
        tq = avg_pct(turn[k], u)
        for g, gm in (('high', tq > 0.7), ('low', tq <= 0.3)):
            gm = gm & u
            q = ordinal_pct(sig_mom[k], gm)
            out[(g, 'W')][k] = np.flatnonzero(q > 0.8)
            out[(g, 'L')][k] = np.flatnonzero(q <= 0.2)
        ok_k[k] = True
    return out, ok_k


def raw_sd12(P):
    """std of the last 12 unadjusted month-end-to-month-end close returns at each formation (raw diagnostic)."""
    CLOSE = open_mat('close'); E = open_mat('exists')
    me_all = month_end_idx(P.dates)
    pos = {int(t): j for j, t in enumerate(me_all)}
    out = np.full((P.K, P.N), np.nan, np.float32)
    for k, t in enumerate(P.fidx):
        j = pos[int(t)]
        if j < 12:
            continue
        mi = me_all[j - 12:j + 1]
        c = np.asarray(CLOSE[mi]).astype(np.float64)
        e = np.asarray(E[mi]).all(axis=0)
        with np.errstate(invalid='ignore', divide='ignore'):
            r = c[1:] / c[:-1] - 1.0
            out[k] = np.where(e, np.std(r, axis=0, ddof=1), np.nan)
    return out


def e7_exact(P, X):
    """E7 part-7 construction with a daily re-weighted engine. Returns dict name -> daily series and turnover."""
    cr = np.load(f'{CACHE2}/cr.npy', mmap_mode='r'); vol = np.load(f'{CACHE2}/volume.npy', mmap_mode='r')
    ncls = open_mat('namecls')
    k0 = int(np.searchsorted(P.dates[P.fidx], pd.Timestamp('2014-06-30')))
    t_lo = P.fidx[k0]
    seg_c = np.asarray(cr[t_lo:]).astype(np.float64); seg_v = np.asarray(vol[t_lo:])
    lim = np.where(P.dates[t_lo:] >= pd.Timestamp('2015-06-15'), 0.305, 0.155)[:, None]
    Re7 = np.where((seg_c <= lim) & (seg_v > 0), seg_c, np.nan)          # rows t_lo..T-1
    del seg_c, seg_v
    LIQ = X['liq_e7']; MOM = X['MOM_E7']; NOBS = X['NOBS_E7']; T12 = X['TURN12_E7']
    res = {}
    names = ('all', 'high', 'low', 'BENCH')
    for nm in names:
        res[nm] = dict(daily=np.full(P.T, np.nan), cost=np.zeros(P.T), tau=np.full(P.K, np.nan), n=np.zeros(P.K, int))
    prev = {nm: set() for nm in names}
    for k in range(k0, P.K):
        t = P.fidx[k]; te = P.fidx[k + 1] if k + 1 < P.K else P.T - 1
        liq = LIQ[k]
        nonspac = np.asarray(ncls[t]) != 1
        terc = avg_pct(T12[k], np.isfinite(T12[k]) & nonspac & np.asarray(P.E[t]))
        sets = {}
        for g, extra in (('all', np.ones(P.N, bool)), ('high', terc > 2 / 3), ('low', terc <= 1 / 3)):
            ok = liq & np.isfinite(MOM[k]) & (NOBS[k] >= 200) & extra
            idx = np.flatnonzero(ok)
            if len(idx) < 50:
                sets[g] = np.array([], int); continue
            # pd.qcut(s.rank(method='first'), 5, labels=False) == 4  (columns in code order)
            s = pd.Series(MOM[k, idx].astype(np.float64), index=idx)
            qs = pd.qcut(s.rank(method='first'), 5, labels=False)
            sets[g] = np.asarray(qs.index[qs.values == 4])
        sets['BENCH'] = np.flatnonzero(liq)
        rows = slice(t + 1 - t_lo, te + 1 - t_lo)
        for nm, m in sets.items():
            if len(m) == 0:
                continue
            L = set(m.tolist())
            tau = 1 - len(L & prev[nm]) / len(L) if prev[nm] else 1.0
            prev[nm] = L
            with np.errstate(invalid='ignore'):
                d = np.nanmean(Re7[rows][:, m], axis=1)
            res[nm]['daily'][t + 1:te + 1] = d
            res[nm]['cost'][t + 1] = 2 * tau * 0.0035
            res[nm]['tau'][k] = tau
            res[nm]['n'][k] = len(m)
        if k % 60 == 0:
            log(f'  E7 exact period {P.dates[t].date()}')
    return res, k0


def e7_members(P, X):
    """Member sets for the ladder (S1: E7 terciles; S2: terciles inside the liquid universe)."""
    LIQ = X['liq_e7']; MOM = X['MOM_E7']; NOBS = X['NOBS_E7']; T12 = X['TURN12_E7']
    ncls = open_mat('namecls')
    k0 = int(np.searchsorted(P.dates[P.fidx], pd.Timestamp('2014-06-30')))
    S = {}
    for key in ('S1|all', 'S1|high', 'S1|low', 'S2|high', 'S2|low', 'BENCH'):
        S[key] = [np.array([], int)] * P.K
    for k in range(k0, P.K):
        t = P.fidx[k]
        liq = LIQ[k]
        nonspac = np.asarray(ncls[t]) != 1
        terc_all = avg_pct(T12[k], np.isfinite(T12[k]) & nonspac & np.asarray(P.E[t]))
        base = liq & np.isfinite(MOM[k]) & (NOBS[k] >= 200)
        terc_in = avg_pct(T12[k], base)
        for key, extra in (('S1|all', np.ones(P.N, bool)), ('S1|high', terc_all > 2 / 3), ('S1|low', terc_all <= 1 / 3),
                           ('S2|high', terc_in > 2 / 3), ('S2|low', terc_in <= 1 / 3)):
            idx = np.flatnonzero(base & extra)
            if len(idx) < 50:
                continue
            s = pd.Series(MOM[k, idx].astype(np.float64), index=idx)
            qs = pd.qcut(s.rank(method='first'), 5, labels=False)
            S[key][k] = np.asarray(qs.index[qs.values == 4])
        S['BENCH'][k] = np.flatnonzero(liq)
    return S, k0


def main():
    t0 = time.time()
    P = Panel()
    X = P.extra()
    rows = []
    specs = build_specs(P, X)
    # B1 Eom design (adjusted returns)
    eom_sets = {}
    for un in ('broad', 'broad_cut'):
        mem, okk = eom_members(P, X, P.F['MOM_12_1'], X['SD12M'], un)
        for (g, l), lst in mem.items():
            nm = f'EOM|adj|{un}|{g}|{l}'
            specs.append((nm, lambda k, lst=lst: (lst[k], np.full(len(lst[k]), 1.0 / max(len(lst[k]), 1)))))
        eom_sets[un] = okk
    # B4 ladder S1/S2 member sets + liquid EW benchmark (buy-and-hold engine)
    S, k0e7 = e7_members(P, X)
    for key, lst in S.items():
        specs.append((f'E7|{key}', lambda k, lst=lst: (lst[k], np.full(len(lst[k]), 1.0 / max(len(lst[k]), 1)))))
    log(f'{len(specs)} books; running engine')
    books = run_books(P, specs, progress=120)
    save_books(f'{CACHE2}/books_mom.npz', P, books)
    log('books done')
    # ---------------- A. grid statistics ----------------
    pms = {lab: P.pmask(a, b) for lab, a, b in GRID_PERIODS}
    UEW, UVW = books['UNIV|ALL|EW'], books['UNIV|ALL|VW']

    def emit(tab, keys, per, daily, to, nmem=None):
        for plab, pm in pms.items():
            st = stats(P, per, daily, to, pm, full=(plab == 'full'))
            if nmem is not None:
                st['avg_names'] = float(nmem[pm & (nmem > 0)].mean()) if (pm & (nmem > 0)).any() else np.nan
            for m, v in st.items():
                tab.append(dict(**keys, period=plab, metric=m, value=v))
    grid = []
    for s in SIGS:
        for td in ['all'] + TDEFS:
            for tl in (['all'] if td == 'all' else list(TERC)):
                for w in ('EW', 'VW'):
                    q5b, q1b = books[f'GRID|{s}|{td}|{tl}|{w}|Q5'], books[f'GRID|{s}|{td}|{tl}|{w}|Q1']
                    base = dict(signal=s, turn_def=td, tercile=tl, weighting=w)
                    nm = (q5b['nmem'] + q1b['nmem']) / 2
                    for cl, c in (('gross', 0.0), ('net35', 0.0035), ('net70', 0.0070)):
                        per, daily, to = series(P, q5b, S=q1b, c=c)
                        emit(grid, dict(base, leg=f'LS_{cl}'), per, daily, to, nm)
                    for bl, B in (('UEW', UEW), ('UVW', UVW)):
                        for cl, c in (('gross', 0.0), ('net35', 0.0035)):
                            per, daily, to = series(P, q5b, B=B, c=c, cb=0.0)
                            emit(grid, dict(base, leg=f'LO_xs_{bl}_{cl}'), per, daily, to, q5b['nmem'])
    G = pd.DataFrame(grid)
    to_csv(G, 'r2_kr_mom_grid_long.csv')
    log(f'grid rows {len(G):,}')
    # ---------------- B. claims ----------------
    cl_rows = []

    def claim(claim_id, variant, per, daily, to, pm, extra=None):
        st = stats(P, per, daily, to, pm, full=True)
        p = per[pm]; p = p[np.isfinite(p)]
        st['mean_pct_month'] = p.mean() * 100
        if extra:
            st.update(extra)
        for m, v in st.items():
            cl_rows.append(dict(claim=claim_id, variant=variant, metric=m, value=v))
    # B1 Eom (adjusted)
    for un in ('broad', 'broad_cut'):
        pm = eom_sets[un]
        for g in ('high', 'low'):
            W, L = books[f'EOM|adj|{un}|{g}|W'], books[f'EOM|adj|{un}|{g}|L']
            per, daily, to = series(P, W, S=L, c=0.0)
            pw, _, _ = series(P, W, c=0.0); pl, _, _ = series(P, L, c=0.0)
            claim('KJFS/P6-Eom', f'adjusted|{un}|{g}-turnover W-L', per, daily, to, pm,
                  dict(winners_pct_month=np.nanmean(pw[pm]) * 100, losers_pct_month=np.nanmean(pl[pm]) * 100,
                       avg_names_W=float(W['nmem'][pm].mean()), avg_names_L=float(L['nmem'][pm].mean())))
    # B1 diagnostic: unadjusted closes. 2 x 2 decomposition: signal {adjusted, unadjusted} x holding returns
    # {adjusted (round-1 ret), unadjusted close-to-close}; plus the share of loser name-months whose holding
    # month contains a KRX base-price adjustment day (capital reduction, split, bonus/rights issue).
    log('raw-close diagnostic')
    raw = np.asarray(np.load(f'{CACHE2}/raw_ret.npy', mmap_mode='r'))
    Praw = Panel(load_returns=False)
    Praw.R, Praw.E, Praw.TR = raw, P.E, P.TR
    sd_raw = raw_sd12(P)
    msets = {}
    for un in ('broad', 'broad_cut'):
        msets[('adjsig', un)] = eom_members(P, X, P.F['MOM_12_1'], X['SD12M'], un)
        msets[('rawsig', un)] = eom_members(P, X, X['MOM_12_1_RAW'], sd_raw, un)
    for hold_lab, PP in (('adjhold', P), ('rawhold', Praw)):
        rspecs = []
        for (sg, un), (mem, okk) in msets.items():
            for (g, l), lst in mem.items():
                rspecs.append((f'{sg}|{un}|{g}|{l}', lambda k, lst=lst: (lst[k], np.full(len(lst[k]), 1.0 / max(len(lst[k]), 1)))))
        rb = run_books(PP, rspecs)
        for (sg, un), (mem, okk) in msets.items():
            if sg == 'adjsig' and hold_lab == 'adjhold':
                continue                                      # = the main adjusted run above
            for g in ('high', 'low'):
                W, L = rb[f'{sg}|{un}|{g}|W'], rb[f'{sg}|{un}|{g}|L']
                per, daily, to = series(PP, W, S=L, c=0.0)
                pw, _, _ = series(PP, W, c=0.0); pl, _, _ = series(PP, L, c=0.0)
                lab = {'rawsig': 'unadjusted signal', 'adjsig': 'adjusted signal'}[sg] + ' + ' + \
                      {'rawhold': 'unadjusted holding returns', 'adjhold': 'adjusted holding returns'}[hold_lab]
                claim('KJFS/P6-Eom', f'{lab}|{un}|{g}-turnover W-L', per, daily, to, okk,
                      dict(winners_pct_month=np.nanmean(pw[okk]) * 100, losers_pct_month=np.nanmean(pl[okk]) * 100))
    # what drives the unadjusted result? Unadjusted closes mix two artefacts: (i) corporate-action jumps that KRX
    # adjusts in its base price (capital reductions / reverse splits, splits, bonus and rights issues; 'KRX adjustment
    # day' = |unadjusted change - ChangesRatio| > 0.5%) and (ii) corrupt prints (e.g. +6,699,900% on one day) that the
    # round-1 cleaning removes. Variant: round-1 cleaned returns on every day EXCEPT KRX adjustment days, where the
    # unadjusted change is kept -> isolates (i).
    cr = np.asarray(np.load(f'{CACHE2}/cr.npy', mmap_mode='r'))
    with np.errstate(invalid='ignore'):
        adjday = np.isfinite(raw) & np.isfinite(cr) & (np.abs(raw - cr) > 0.005)
    rawfix = np.where(adjday, raw, np.nan_to_num(P.R, nan=0.0)).astype(np.float32)
    Pfix = Panel(load_returns=False)
    Pfix.R, Pfix.E, Pfix.TR = rawfix, P.E, P.TR
    rspecs = []
    for un in ('broad', 'broad_cut'):
        mem, okk = msets[('rawsig', un)]
        for (g, l), lst in mem.items():
            rspecs.append((f'fix|{un}|{g}|{l}', lambda k, lst=lst: (lst[k], np.full(len(lst[k]), 1.0 / max(len(lst[k]), 1)))))
    rb = run_books(Pfix, rspecs)
    for un in ('broad', 'broad_cut'):
        okk = msets[('rawsig', un)][1]
        for g in ('high', 'low'):
            W, L = rb[f'fix|{un}|{g}|W'], rb[f'fix|{un}|{g}|L']
            per, daily, to = series(Pfix, W, S=L, c=0.0)
            pw, _, _ = series(Pfix, W, c=0.0); pl, _, _ = series(Pfix, L, c=0.0)
            claim('KJFS/P6-Eom', f'unadjusted signal + cleaned returns except unadjusted corporate-action days|{un}|{g}-turnover W-L',
                  per, daily, to, okk, dict(winners_pct_month=np.nanmean(pw[okk]) * 100, losers_pct_month=np.nanmean(pl[okk]) * 100))
    cl_rows.append(dict(claim='KJFS/P6-Eom anatomy', variant='all panel stock-days', metric='share_of_days_that_are_KRX_adjustment_days',
                        value=float(adjday.sum() / np.isfinite(raw).sum())))
    # largest single-name contributions to the unadjusted high-turnover loser leg (all caps), incl. carried positions
    from kr_03_portfolios import Book
    mem, okk = msets[('rawsig', 'broad')]
    bk = Book(P.N); ev = []
    names = pd.read_csv(f'{CACHE}/codes_names.csv', dtype={'Code': str}).groupby('Code').Name.last()
    for k in range(P.K):
        t = P.fidx[k]; te = P.fidx[k + 1] if k + 1 < P.K else P.T - 1
        m = mem[('high', 'L')][k]
        if not okk[k] or len(m) == 0:
            bk = Book(P.N); continue
        bk.rebalance(m, np.full(len(m), 1.0 / len(m)), P.E[t], P.TR[t])
        held = np.flatnonzero(bk.v); w0 = bk.v[held].copy()
        Rb = np.nan_to_num(rawfix[t + 1:te + 1].astype(np.float64)); A = np.cumprod(P.E[t + 1:te + 1], axis=0).astype(bool)
        G = np.cumprod(1 + Rb * A, axis=0)
        contrib = w0 * (G[-1, held] - 1)
        for jj in np.argsort(-contrib)[:2]:
            c = held[jj]; seg = Rb[:, c]; dd = int(np.argmax(np.abs(seg)))
            ev.append(dict(formation=str(P.dates[t].date()), code=P.codes[c], name=names.get(P.codes[c], ''),
                           contribution_to_leg_month=float(contrib[jj]), leg_month_return=float(contrib.sum()),
                           event_day=str(P.dates[t + 1 + dd].date()), unadjusted_day_return=float(raw[t + 1 + dd, c]),
                           krx_changesratio=float(np.nan_to_num(cr[t + 1 + dd, c])), cleaned_return=float(np.nan_to_num(P.R[t + 1 + dd, c])),
                           krx_adjustment_day=bool(adjday[t + 1 + dd, c]), member_at_formation=bool(c in set(m.tolist()))))
        bk.hold(G)
    EV = pd.DataFrame(ev).sort_values('contribution_to_leg_month', ascending=False)
    to_csv(EV.head(40), 'r2_kr_mom_kjfs_events.csv')
    top = EV.head(40)
    for lab_, col_ in (('share_on_KRX_adjustment_days', top.krx_adjustment_day), ('share_positions_carried_not_members', ~top.member_at_formation)):
        cl_rows.append(dict(claim='KJFS/P6-Eom anatomy', variant='top-40 single-name contributions (losers, all caps, high turnover; '
                            'cleaned returns except unadjusted corporate-action days)', metric=lab_, value=float(col_.mean())))
    del cr, rawfix, Pfix, adjday
    del raw, Praw
    # B2 P6 deciles, holding 2001-02..2026-09
    pm6 = P.pmask('2001-02-01', '2026-12-31')
    for s in ('MOM_12_1', 'MOM_12_7'):
        for w in ('EW', 'VW'):
            D10, D1 = books[f'P6DEC|{s}|{w}|D10'], books[f'P6DEC|{s}|{w}|D1']
            for cl, c in (('gross', 0.0), ('net35', 0.0035), ('net70', 0.0070)):
                per, daily, to = series(P, D10, S=D1, c=c)
                claim('P6-deciles', f'{s}|{w}|D10-D1|{cl}', per, daily, to, pm6)
    # B3 round-1 dependent sort, EW
    pmf = np.ones(P.K, bool)
    for tl in TERC:
        Q5, Q1 = books[f'R1DEP|MOM_12_1|TURN_1M|{tl}|EW|Q5'], books[f'R1DEP|MOM_12_1|TURN_1M|{tl}|EW|Q1']
        for cl, c in (('gross', 0.0), ('net35', 0.0035)):
            per, daily, to = series(P, Q5, S=Q1, c=c)
            claim('Round-1', f'MOM_12_1 Q5-Q1 in {tl} TURN_1M tercile (dependent)|{cl}', per, daily, to, pmf)
    # B5 E5 / P2 top-500, 2000-01..2026-09
    pm5 = P.pmask('2000-01-01', '2026-12-31')
    pm5b = P.pmask('2016-01-01', '2026-12-31')
    kjul = int(np.flatnonzero((P.pstart.year == 2026) & (P.pstart.month == 7))[0])
    for nq, (qh, ql), pref in ((10, (10, 1), 'TOP500'), (5, (5, 1), 'TOP500'), (10, (10, 1), 'TOP500L')):
        for w in ('EW', 'VW'):
            H, L_ = books[f'{pref}|MOM_12_1|n{nq}|{w}|Q{qh}'], books[f'{pref}|MOM_12_1|n{nq}|{w}|Q{ql}']
            for cl, c in (('gross', 0.0), ('net35', 0.0035)):
                per, daily, to = series(P, H, S=L_, c=c)
                ex = {'jul2026_month': per[kjul]}
                st16 = stats(P, per, daily, to, pm5b, full=False)
                ex['sharpe_2016_2026'] = st16.get('sharpe', np.nan)
                tag = ('deciles' if nq == 10 else 'quintiles') + (' (looser top-500: no 200-day/limit screens)' if pref == 'TOP500L' else '')
                claim('E5/P2-top500', f'MOM_12_1|{tag}|{w}|{cl}', per, daily, to, pm5, ex)
    # Jul-2026 month for ALL-universe quintiles and deciles too
    for w in ('EW', 'VW'):
        per, _, _ = series(P, books[f'GRID|MOM_12_1|all|all|{w}|Q5'], S=books[f'GRID|MOM_12_1|all|all|{w}|Q1'])
        cl_rows.append(dict(claim='Jul-2026', variant=f'ALL quintiles {w} gross', metric='jul2026_month', value=per[kjul]))
        per, _, _ = series(P, books[f'P6DEC|MOM_12_1|{w}|D10'], S=books[f'P6DEC|MOM_12_1|{w}|D1'])
        cl_rows.append(dict(claim='Jul-2026', variant=f'ALL deciles {w} gross', metric='jul2026_month', value=per[kjul]))
    C = pd.DataFrame(cl_rows)
    to_csv(C, 'r2_kr_mom_claims_long.csv')
    # ---------------- B4 E7 ladder ----------------
    log('E7 exact (daily re-weighted engine)')
    res, k0 = e7_exact(P, X)
    lad = []
    d0 = P.dates
    win = (d0 >= pd.Timestamp('2015-07-01')) & (d0 <= pd.Timestamp('2024-12-31'))
    B = res['BENCH']['daily']
    for g in ('all', 'high', 'low'):
        L = res[g]['daily']; c = res[g]['cost']
        x = (L - B - c)[win]
        x = x[np.isfinite(x)]
        xg = (L - B)[win]; xg = xg[np.isfinite(xg)]
        lad.append(dict(step='S0 E7 exact (daily re-weighted EW legs and benchmark, E7 cleaning, iid daily t)',
                        group=g, ann_excess_net35=x.mean() * 252, t=x.mean() / x.std(ddof=1) * np.sqrt(len(x)),
                        ann_excess_gross=xg.mean() * 252, n_days=len(x),
                        avg_names=float(res[g]['n'][res[g]['n'] > 0].mean()),
                        one_way_turnover_per_year=float(np.nanmean(res[g]['tau'][k0:]) * 12)))
    pmE = P.pmask('2015-07-01', '2024-12-31')
    BB = books['E7|BENCH']
    for step, keys in (('S1 same names, monthly buy-and-hold engine, round-1 returns, NW t', ('S1|all', 'S1|high', 'S1|low')),
                       ('S2 + turnover terciles formed inside the liquid universe', ('S1|all', 'S2|high', 'S2|low'))):
        for key in keys:
            g = key.split('|')[1]
            per, daily, to = series(P, books[f'E7|{key}'], B=BB, c=0.0035, cb=0.0)
            st = stats(P, per, daily, to, pmE, full=True)
            perg, _, _ = series(P, books[f'E7|{key}'], B=BB, c=0.0, cb=0.0)
            lad.append(dict(step=step, group=g, ann_excess_net35=st['ann_mean'], t=st['nw_t'],
                            ann_excess_gross=np.nanmean(perg[pmE]) * 12, n_months=st['n_periods'],
                            avg_names=float(books[f'E7|{key}']['nmem'][pmE].mean()),
                            pct_pos_years=st.get('pct_pos_years')))
    for g, tl in (('all', None), ('high', 'high'), ('low', 'low')):
        nmb = f'GRID|MOM_12_1|all|all|EW|Q5' if tl is None else f'GRID|MOM_12_1|TURN_12M|{tl}|EW|Q5'
        per, daily, to = series(P, books[nmb], B=UEW, c=0.0035, cb=0.0)
        st = stats(P, per, daily, to, pmE, full=True)
        perg, _, _ = series(P, books[nmb], B=UEW, c=0.0, cb=0.0)
        lad.append(dict(step='S3 grid cell: ALL universe, TURN_12M terciles (independent), MOM_12_1, vs ALL EW universe',
                        group=g, ann_excess_net35=st['ann_mean'], t=st['nw_t'], ann_excess_gross=np.nanmean(perg[pmE]) * 12,
                        n_months=st['n_periods'], avg_names=float(books[nmb]['nmem'][pmE].mean()),
                        pct_pos_years=st.get('pct_pos_years')))
    # E7 universe size and overlap with ALL
    LQ = X['liq_e7']; UA = P.F['univ_all']
    kk = np.flatnonzero(pmE)
    lad.append(dict(step='info', group='universe', avg_names=float(LQ[kk].sum(1).mean()),
                    ann_excess_net35=np.nan, t=np.nan,
                    note=f'E7 liquid universe {LQ[kk].sum(1).mean():.0f} names vs ALL {UA[kk].sum(1).mean():.0f}; '
                         f'share of E7 names in ALL {((LQ[kk] & UA[kk]).sum(1) / LQ[kk].sum(1)).mean():.3f}'))
    LD = pd.DataFrame(lad)
    to_csv(LD, 'r2_kr_mom_e7_ladder.csv')
    pd.set_option('display.width', 250)
    print(LD[['step', 'group', 'ann_excess_net35', 't', 'ann_excess_gross', 'avg_names']].round(4).to_string())
    log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
