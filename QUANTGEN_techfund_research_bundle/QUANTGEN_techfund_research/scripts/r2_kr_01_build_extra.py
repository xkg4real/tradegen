"""r2_kr_01_build_extra.py -- extra daily matrices and formation-level signals/flags for round 2.

Reads the raw marcap parquet files once (same row filter as round-1 kr_01: Market in KOSPI/KOSDAQ/
KOSDAQ GLOBAL, common share = code ending in 0, Close > 0) and writes, aligned to the round-1 calendar
and code list (asserted):
  cache/volume.npy  (f4)   Volume                      cache/cr.npy     (f4) raw ChangesRatio/100
  cache/low.npy     (f4)   Low (0 -> Close)            cache/stocks.npy (f8) shares outstanding
  cache/chgcode.npy (i1)   ChangeCode 4/5 (old KRX limit-up/limit-down codes; absent in 2026 data), else 0
  cache/admin.npy   (b)    Dept contains 관리 or 투자주의환기 (KOSDAQ designation; used only for E7's universe)
  cache/raw_ret.npy (f4)   unadjusted Close_t/Close_{t-1}-1 on consecutive listed days (diagnostic only)
Derived daily flags (all causal: day d uses rows <= d only):
  lu_lock  locked limit-up close: Close >= High, r > 0, Volume > 0 and (ChangeCode 4 or r >= L - 0.5 pp),
           L = daily price limit of the stock's market on day d (KOSPI 6% < 1996-11-25 <= 8% < 1998-03-02
           <= 12% < 1998-12-07 <= 15% < 2015-06-15 <= 30%; KOSDAQ 8% < 1998-05-25 <= 12% < 2005-03-28 <= 15%
           < 2015-06-15 <= 30%; dates verified from the data).  ld_lock: mirror image (limit-lock audit).
  vspike   Volume_d >= 5 x mean(Volume over the 20 previous listed rows, >= 15 rows) and r_d >= +5%
           (E7 e7_checks_part2: vavg = VOL.rolling(20, min 15).mean().shift(1); vspike = VOL >= 5 vavg & R >= .05)
  r20      exp(CL_d - CL_{d-20}) - 1 >= +50% (listed at d-20)
  lu_e7    E7's written limit-up definition (DC2): Close >= High and change >= 29.5% from 2015-06-15, >= 14.5% before
  f5ev     vspike | lu_e7 | r20 (E7 attention-fade events, primary F5); f5ev_reg uses lu_lock instead (variant)
Formation-level arrays (K x N, at the round-1 month-end formation dates, rows <= t only) in cache/form_r2.npz:
  MOM_12_7  exp(CL[t-126]-CL[t-252])-1, listed at t-252     TURN_12M mean Amount/Marcap over listed days t-251..t (>=120)
  TURN_3M   same over t-62..t (>= 40)                         VOL_1M / VOL_6M std of valid returns t-20..t (>=15) / t-125..t (>=80)
  MAX_3M    max valid return t-62..t (>= 40)
  F5        any f5ev in t-19..t (exclude for the next 20 trading days); F5_vspike/F5_lu/F5_r20 components;
            F5_w5/F5_w10/F5_w40/F5_w60 window neighbours; F5_reg (regime-limit lock variant), F5_lureg
  DIL_LIT   12-month (252-session) growth of shares outstanding, ignoring split-like days, literal rule:
            a share-count change day (s = Stocks_d/Stocks_{d-1}) is split-like if the shares multiplied
            (|s-1| > 5%) and the raw close moved by the inverse ratio within +-5%: |s * Close_d/Close_{d-1} - 1| <= 5%
  DIL_NI    net issuance = prod(s_d) / prod(a_d) - 1 over 252 sessions, a_d = KRX base-price adjustment
            factor (1+r_d)/(Close_d/Close_{d-1}) when |a_d - 1| > 0.5% (splits, bonus issues and rights
            issues are adjusted on their ex-date, which differs from the share-listing date)
  ADV20     mean Amount t-19..t (>= 15 rows), ADMIN_t, NDAYS_M (traded days in the formation month)
  top500    top 500 eligible stocks by Marcap_t (round-1 eligibility; E5/P2 universe)
  broad     listed, traded at t, operating company, >= 200 valid days in 252, Amount>0 on >= 4 of 5 days,
            no beyond-limit non-CA move in t-29..t (round-1 kr_08 BROAD: no price floor, no microcap cut)
  broad_cut broad with Marcap >= 20th percentile of broad Marcap
  SD12M     std of the last 12 month-end-to-month-end returns (Eom design)
  MOM_12_1_RAW, MOM_12_7_RAW  momentum from unadjusted closes (diagnostic for the KJFS claim)
  E7: MOM_E7, NOBS_E7, TURN12_E7, LIQ_E7 (E7 liquid universe), with E7's own return cleaning
      (r <= +30.5% / +15.5% and Volume > 0, negative beyond-limit prints kept)
"""
import os, sys, time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (CACHE, CACHE2, RAW, log, load_meta, open_mat)
sys.path.insert(0, '/home/claude/datalab/scripts')
import kr_02_signals as S1

YEARS = range(1995, 2027)
MARKETS = {'KOSPI': 1, 'KOSDAQ': 2, 'KOSDAQ GLOBAL': 2}
CH = 200


def limit_matrix(dates, mk):
    """Daily price limit (in %) per (date, column) from the market code matrix mk (1 KOSPI, 2 KOSDAQ)."""
    d = dates.values.astype('datetime64[D]')
    def kospi(x):
        return np.where(x >= np.datetime64('2015-06-15'), 30.0, np.where(x >= np.datetime64('1998-12-07'), 15.0,
               np.where(x >= np.datetime64('1998-03-02'), 12.0, np.where(x >= np.datetime64('1996-11-25'), 8.0, 6.0))))
    def kosdaq(x):
        return np.where(x >= np.datetime64('2015-06-15'), 30.0, np.where(x >= np.datetime64('2005-03-28'), 15.0,
               np.where(x >= np.datetime64('1998-05-25'), 12.0, 8.0)))
    lk, lq = kospi(d)[:, None], kosdaq(d)[:, None]
    return np.where(mk == 1, lk, np.where(mk == 2, lq, np.nan))


def build_raw():
    dates, codes = load_meta()
    T, N = len(dates), len(codes)
    cpos = pd.Series(np.arange(N), index=codes)
    dpos = pd.Series(np.arange(T), index=dates.values.astype('datetime64[D]'))

    def mm(name, dtype, fill):
        a = np.lib.format.open_memmap(f'{CACHE2}/{name}.npy', mode='w+', dtype=dtype, shape=(T, N))
        a[:] = fill
        return a
    VOL = mm('volume', np.float32, np.nan); CR = mm('cr', np.float32, np.nan); LOW = mm('low', np.float32, np.nan)
    STK = mm('stocks', np.float64, np.nan); CC = mm('chgcode', np.int8, 0); ADM = mm('admin', bool, False)
    E1 = open_mat('exists')
    nrows = 0
    for y in YEARS:
        df = pq.read_table(f'{RAW}/marcap-{y}.parquet', columns=['Date', 'Code', 'Market', 'Close', 'Low', 'Volume',
                                                                 'Stocks', 'ChangesRatio', 'ChangeCode', 'Dept']).to_pandas()
        df['Code'] = df['Code'].str.zfill(6)
        df = df[df['Market'].isin(list(MARKETS)) & (df['Code'].str[-1] == '0') & (df['Close'] > 0)]
        ti = dpos.reindex(df['Date'].values.astype('datetime64[D]')).values
        ci = cpos.reindex(df['Code'].values).values
        assert not (np.isnan(ti).any() or np.isnan(ci).any())
        ti = ti.astype(np.int64); ci = ci.astype(np.int64)
        assert np.asarray(E1[ti, ci]).all(), 'row not in the round-1 panel'
        close = df['Close'].values.astype(np.float64)
        low = df['Low'].values.astype(np.float64)
        VOL[ti, ci] = df['Volume'].values
        CR[ti, ci] = df['ChangesRatio'].values / 100.0
        LOW[ti, ci] = np.where(low > 0, low, close)
        STK[ti, ci] = df['Stocks'].values.astype(np.float64)
        cc = df['ChangeCode'].astype(str).values
        CC[ti, ci] = np.where(cc == '4', 4, np.where(cc == '5', 5, 0)).astype(np.int8)
        dept = df['Dept'].fillna('').astype(str)
        ADM[ti, ci] = dept.str.contains('관리|투자주의환기').values
        nrows += len(df)
        log(f'{y}: {len(df):,} rows')
    for a in (VOL, CR, LOW, STK, CC, ADM):
        a.flush()
    assert nrows == int(np.asarray(E1).sum()), f'row count {nrows} != round-1 exists {int(np.asarray(E1).sum())}'
    log(f'raw matrices written; {nrows:,} rows = round-1 exists count')


def rolling_sum_prev(x, valid, w):
    """Sum and count of x over rows d-w..d-1 (previous w rows) where valid; x, valid: (T, n)."""
    xs = np.where(valid, x, 0.0)
    cs = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(xs, axis=0)])
    cn = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(valid.astype(np.int32), axis=0)])
    T = x.shape[0]
    idx = np.arange(T)
    lo = np.maximum(idx - w, 0)
    s = cs[idx] - cs[lo]           # rows lo..d-1
    n = cn[idx] - cn[lo]
    return s, n


def window_stat_at(arr_win, valid_win, minobs, how):
    with np.errstate(invalid='ignore'):
        n = valid_win.sum(axis=0)
        if how == 'std':
            v = np.where(valid_win, arr_win, np.nan)
            out = np.nanstd(v, axis=0, ddof=1)
        elif how == 'max':
            v = np.where(valid_win, arr_win, -np.inf)
            out = v.max(axis=0)
        elif how == 'mean':
            v = np.where(valid_win, arr_win, 0.0)
            out = v.sum(axis=0) / np.maximum(n, 1)
    return np.where(n >= minobs, out, np.nan)


def derived_chunk(c0, c1, dates, fidx, me_all, F1, tmax=None):
    """All derived daily flags and formation-level arrays for columns c0:c1 (causal computations).
    tmax: if given, only rows <= tmax are read (look-ahead truncation test in r2_kr_07_validation.py)."""
    rows = slice(None) if tmax is None else slice(0, tmax + 1)
    if tmax is not None:
        dates = dates[:tmax + 1]; fidx = fidx[fidx <= tmax]; me_all = me_all[me_all <= tmax]
    o = lambda n: np.asarray(open_mat(n)[rows, c0:c1])
    o2 = lambda n: np.asarray(np.load(f'{CACHE2}/{n}.npy', mmap_mode='r')[rows, c0:c1])
    E = o('exists'); TRd = o('traded'); MK = o('mkt'); R = o('ret').astype(np.float64)
    CL = o('cumlog'); CLOSE = o('close').astype(np.float64); HIGH = o('high').astype(np.float64)
    AMT = o('amount').astype(np.float64); MC = o('marcap').astype(np.float64); VALID = o('valid')
    VOL = o2('volume').astype(np.float64); CRr = o2('cr').astype(np.float64); LOW = o2('low').astype(np.float64)
    STK = o2('stocks'); CC = o2('chgcode'); ADM = o2('admin')
    T, n = E.shape
    out = {}
    L = limit_matrix(dates, MK)
    with np.errstate(invalid='ignore', divide='ignore'):
        lu = E & TRd & (CLOSE >= HIGH) & (CRr > 0) & ((CC == 4) | (CRr * 100 >= L - 0.5))
        ld = E & TRd & (CLOSE <= LOW) & (CRr < 0) & ((CC == 5) | (CRr * 100 <= -(L - 0.5)))
        s20, n20 = rolling_sum_prev(np.nan_to_num(VOL), E, 20)
        vavg = np.where(n20 >= 15, s20 / np.maximum(n20, 1), np.nan)
        vspike = E & (VOL > 0) & (VOL >= 5 * vavg) & (R >= 0.05)
        CLp20 = np.full_like(CL, np.nan); CLp20[20:] = CL[:-20]
        Ep20 = np.zeros_like(E); Ep20[20:] = E[:-20]
        r20 = E & Ep20 & (np.exp(CL - CLp20) - 1 >= 0.5)
        # E7's written definition (DC2 / constraint 3): change >= 29.5% from 2015-06-15, >= 14.5% before, close = high
        thr_e7 = np.where(dates.values >= np.datetime64('2015-06-15'), 0.295, 0.145)[:, None]
        lu_e7 = E & TRd & (CLOSE >= HIGH) & (CRr >= thr_e7)
    f5 = vspike | lu_e7 | r20          # primary F5 (E7 definition)
    f5r = vspike | lu | r20            # variant: lock at the regime price limit (6/8/12/15/30%)
    out['daily'] = dict(lu_lock=lu, ld_lock=ld, lu_e7=lu_e7, vspike=vspike, r20=r20, f5ev=f5, f5ev_reg=f5r)
    # unadjusted close-to-close return on consecutive listed days
    Ep = np.zeros_like(E); Ep[1:] = E[:-1]
    CLOSEp = np.full_like(CLOSE, np.nan); CLOSEp[1:] = CLOSE[:-1]
    with np.errstate(invalid='ignore', divide='ignore'):
        raw = np.where(E & Ep & (CLOSEp > 0), CLOSE / CLOSEp - 1.0, np.nan)
    out['daily']['raw_ret'] = raw.astype(np.float32)
    # share-count changes: literal split-like rule and the net-issuance (adjustment-factor) measure
    STKp = np.full_like(STK, np.nan); STKp[1:] = STK[:-1]
    with np.errstate(invalid='ignore', divide='ignore'):
        s = np.where(E & Ep & (STKp > 0) & (STK > 0), STK / STKp, 1.0)
        p = np.where(E & Ep & (CLOSEp > 0), CLOSE / CLOSEp, 1.0)
        chg = np.abs(s - 1) > 0.001
        # 'share multiplication': |s-1| > 5%, so that the +-5% band around the inverse ratio excludes an
        # unchanged price (otherwise every small CB-conversion day would count as split-like)
        splitlike = chg & (np.abs(s - 1) > 0.05) & (np.abs(s * p - 1) <= 0.05)
        lit = np.where(chg & ~splitlike, np.log(s), 0.0)
        a = np.where(E & Ep & (CLOSEp > 0) & np.isfinite(CRr), (1 + CRr) / p, 1.0)
        a = np.where(np.abs(a - 1) > 0.005, a, 1.0)
        ni = np.where(chg, np.log(s), 0.0) - np.log(np.where(a > 0, a, 1.0))
    lit = np.nan_to_num(lit); ni = np.nan_to_num(ni)
    cs_lit = np.cumsum(lit, axis=0); cs_ni = np.cumsum(ni, axis=0)
    cs_f5 = np.cumsum(f5.astype(np.int32), axis=0)
    cs_f5r = np.cumsum(f5r.astype(np.int32), axis=0)
    cs_comp = {kname: np.cumsum(v.astype(np.int32), axis=0) for kname, v in (('vspike', vspike), ('lu', lu_e7), ('r20', r20),
                                                                              ('lureg', lu))}
    out['n_split_like_days'] = int(splitlike.sum()); out['n_share_change_days'] = int(chg.sum())
    # E7 return cleaning: r <= +30.5% (+15.5% before 2015-06-15) and Volume > 0
    lim_e7 = np.where(dates.values >= np.datetime64('2015-06-15'), 0.305, 0.155)[:, None]
    Re7 = np.where((CRr <= lim_e7) & (VOL > 0), CRr, np.nan)
    cum_e7 = np.cumsum(np.log1p(np.nan_to_num(Re7, nan=0.0)), axis=0)
    cs_e7obs = np.cumsum(np.isfinite(Re7).astype(np.int32), axis=0)
    tvr = np.where(E & (MC > 0), AMT / np.where(MC > 0, MC, 1.0), np.nan)
    cs_tvr = np.cumsum(np.nan_to_num(tvr), axis=0); cs_tvn = np.cumsum(np.isfinite(tvr).astype(np.int32), axis=0)
    amt_l = np.where(E, np.nan_to_num(AMT), 0.0)
    cs_amt = np.cumsum(amt_l, axis=0); cs_amtn = np.cumsum(E.astype(np.int32), axis=0)
    CLraw = np.cumsum(np.log1p(np.nan_to_num(raw, nan=0.0).clip(-0.999999)), axis=0)

    def wsum(cs, t, w):
        return cs[t] - (cs[t - w] if t - w >= 0 else 0)
    K = len(fidx)
    f = {k: np.full((K, n), np.nan, np.float32) for k in
         ('MOM_12_7', 'TURN_12M', 'TURN_3M', 'VOL_1M', 'VOL_6M', 'MAX_3M', 'DIL_LIT', 'DIL_NI', 'ADV20',
          'SD12M', 'MOM_12_1_RAW', 'MOM_12_7_RAW', 'MOM_E7', 'NOBS_E7', 'TURN12_E7')}
        # boolean arrays
    fb = {k: np.zeros((K, n), bool) for k in ('F5', 'F5_reg', 'F5_vspike', 'F5_lu', 'F5_lureg', 'F5_r20', 'F5_w5',
                                              'F5_w10', 'F5_w40', 'F5_w60', 'ADMIN', 'LU_LOCK_T', 'LD_LOCK_T')}
    NDM = np.zeros((K, n), np.int16)
    me_pos = {int(t): j for j, t in enumerate(me_all)}
    for k, t in enumerate(fidx):
        t = int(t)
        e = E[t]
        with np.errstate(invalid='ignore', over='ignore', divide='ignore'):
            f['MOM_12_7'][k] = np.where(e & E[t - 252], np.expm1(CL[t - 126] - CL[t - 252]), np.nan)
            f['MOM_12_1_RAW'][k] = np.where(e & E[t - 252], np.expm1(CLraw[t - 21] - CLraw[t - 252]), np.nan)
            f['MOM_12_7_RAW'][k] = np.where(e & E[t - 252], np.expm1(CLraw[t - 126] - CLraw[t - 252]), np.nan)
            for nm, w, mo in (('TURN_12M', 252, 120), ('TURN_3M', 63, 40)):
                ssum = wsum(cs_tvr, t, w); scnt = wsum(cs_tvn, t, w)
                f[nm][k] = np.where(e & (scnt >= mo), ssum / np.maximum(scnt, 1), np.nan)
            rv = np.where(VALID[t - 125:t + 1], R[t - 125:t + 1], np.nan)
            vv = VALID[t - 125:t + 1]
            f['VOL_6M'][k] = np.where(e, window_stat_at(rv, vv, 80, 'std'), np.nan)
            f['VOL_1M'][k] = np.where(e, window_stat_at(rv[-21:], vv[-21:], 15, 'std'), np.nan)
            f['MAX_3M'][k] = np.where(e, window_stat_at(rv[-63:], vv[-63:], 40, 'max'), np.nan)
            f['DIL_LIT'][k] = np.where(e, np.expm1(wsum(cs_lit, t, 252)), np.nan)
            f['DIL_NI'][k] = np.where(e, np.expm1(wsum(cs_ni, t, 252)), np.nan)
            an = wsum(cs_amtn, t, 20)
            f['ADV20'][k] = np.where(e & (an >= 15), wsum(cs_amt, t, 20) / np.maximum(an, 1), np.nan)
            # Eom design: std of the last 12 month-end to month-end returns
            j = me_pos[t]
            if j >= 12:
                mi = me_all[j - 12:j + 1]
                mr = np.expm1(np.diff(CL[mi], axis=0))
                okm = E[mi[1:]].all(axis=0) & E[mi[0]]
                f['SD12M'][k] = np.where(e & okm, np.std(mr, axis=0, ddof=1), np.nan)
            f['MOM_E7'][k] = np.where(e, cum_e7[t - 21] - cum_e7[t - 252], np.nan)
            f['NOBS_E7'][k] = wsum(cs_e7obs, t, 252)
            tn = wsum(cs_tvn, t, 252)
            f['TURN12_E7'][k] = np.where(tn >= 200, wsum(cs_tvr, t, 252) / np.maximum(tn, 1), np.nan)
        fb['F5'][k] = e & (wsum(cs_f5, t, 20) > 0)
        fb['F5_reg'][k] = e & (wsum(cs_f5r, t, 20) > 0)
        for kname, key in (('vspike', 'F5_vspike'), ('lu', 'F5_lu'), ('r20', 'F5_r20'), ('lureg', 'F5_lureg')):
            fb[key][k] = e & (wsum(cs_comp[kname], t, 20) > 0)
        for w in (5, 10, 40, 60):
            fb[f'F5_w{w}'][k] = e & (wsum(cs_f5, t, w) > 0)
        fb['ADMIN'][k] = ADM[t]
        fb['LU_LOCK_T'][k] = lu[t]
        fb['LD_LOCK_T'][k] = ld[t]
        # traded days in the calendar month of t
        m0 = np.searchsorted(dates.values, np.datetime64(f'{dates[t].year:04d}-{dates[t].month:02d}-01'))
        NDM[k] = TRd[m0:t + 1].sum(axis=0)
    out['form'] = f; out['formb'] = fb; out['NDM'] = NDM
    return out


def main():
    t0 = time.time()
    if '--skip-raw' not in sys.argv:
        build_raw()
    dates, codes = load_meta()
    T, N = len(dates), len(codes)
    F1 = np.load(f'{CACHE}/form_monthly.npz')
    fidx = F1['fidx'].astype(np.int64); K = len(fidx)
    from kr_common import month_end_idx
    me_all = month_end_idx(dates)
    daily_names = {'lu_lock': bool, 'ld_lock': bool, 'lu_e7': bool, 'vspike': bool, 'r20': bool, 'f5ev': bool,
                   'f5ev_reg': bool, 'raw_ret': np.float32}
    for nm, dt in daily_names.items():
        a = np.lib.format.open_memmap(f'{CACHE2}/{nm}.npy', mode='w+', dtype=dt, shape=(T, N)); del a
    form = None; formb = None; NDM = np.zeros((K, N), np.int16); nsplit = nchg = 0
    for c0 in range(0, N, CH):
        c1 = min(N, c0 + CH)
        o = derived_chunk(c0, c1, dates, fidx, me_all, F1)
        for nm, v in o['daily'].items():
            a = np.load(f'{CACHE2}/{nm}.npy', mmap_mode='r+'); a[:, c0:c1] = v; a.flush(); del a
        if form is None:
            form = {k: np.full((K, N), np.nan, np.float32) for k in o['form']}
            formb = {k: np.zeros((K, N), bool) for k in o['formb']}
        for k2, v in o['form'].items():
            form[k2][:, c0:c1] = v
        for k2, v in o['formb'].items():
            formb[k2][:, c0:c1] = v
        NDM[:, c0:c1] = o['NDM']
        nsplit += o['n_split_like_days']; nchg += o['n_share_change_days']
        log(f'derived cols {c0}-{c1}')
    # universes: top-500 (E5/P2), BROAD and BROAD with microcap cut (Eom/P6 'all caps'), E7 liquid universe
    D = S1.load_data(); S1.build_cum(D)
    elig = F1['elig']; mcap = F1['mcap'].astype(np.float64)
    top500 = np.zeros((K, N), bool); broad = np.zeros((K, N), bool); broad_cut = np.zeros((K, N), bool)
    liq_e7 = np.zeros((K, N), bool)
    NC = open_mat('namecls'); CLOSE = open_mat('close'); TRm = open_mat('traded'); Em = open_mat('exists')
    for k, t in enumerate(fidx):
        el = elig[k]
        idx = np.flatnonzero(el)
        order = idx[np.argsort(-mcap[k, idx], kind='stable')]
        top500[k, order[:500]] = True
        e = np.asarray(Em[t]); tr = np.asarray(TRm[t]); nc = np.asarray(NC[t])
        nv = S1.window_count(D.CV, t, 252); na = S1.window_count(D.CA, t, 5); nb = S1.window_count(D.CB, t, 30)
        b = e & tr & (nc == 0) & (nv >= 200) & (na >= 4) & (nb == 0) & (mcap[k] > 0)
        broad[k] = b
        cut = np.quantile(mcap[k][b], 0.20)
        broad_cut[k] = b & (mcap[k] >= cut)
        cl = np.asarray(CLOSE[t]).astype(np.float64)
        with np.errstate(invalid='ignore'):
            liq_e7[k] = e & tr & (mcap[k] >= 100e9) & (form['ADV20'][k] >= 1e9) & (cl >= 1000) & ~formb['ADMIN'][k] & (nc != 1)
    np.savez_compressed(f'{CACHE2}/form_r2.npz', fidx=fidx, top500=top500, broad=broad, broad_cut=broad_cut,
                        liq_e7=liq_e7, NDAYS_M=NDM, **form, **formb)
    log(f'form_r2.npz written: K={K}; share-change days {nchg:,}, literal split-like {nsplit:,}; '
        f'mean |top500| {top500.sum(1).mean():.0f}, |broad| {broad.sum(1).mean():.0f}, |liq_e7| (2014+) '
        f'{liq_e7[dates[fidx] >= pd.Timestamp("2014-06-30")].sum(1).mean():.0f}; {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
