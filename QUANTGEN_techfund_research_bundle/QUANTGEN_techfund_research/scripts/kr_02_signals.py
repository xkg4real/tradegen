"""kr_02_signals.py -- point-in-time universes and technical signals at formation dates.

Monthly formation: last trading day of each month. Weekly formation: last trading day on or before
Friday of each week. Everything at formation index t uses rows <= t only (tested in kr_06_validation.py).

Universe at t (eligible set):
  Market in {KOSPI, KOSDAQ, KOSDAQ GLOBAL}, common share (code ends in 0), name class = operating company
  (no SPAC / REIT / infrastructure or ship/other fund / KDR, see kr_common.classify_name),
  Close_t >= 1,000 KRW, Marcap_t > 0, >= 200 valid return days (finite return and Volume > 0) in t-251..t,
  Amount > 0 on >= 4 of t-4..t, and two point-in-time tightenings of the specified screen:
    (i)  traded on day t itself (Volume_t > 0): a stock halted at the formation close cannot be bought then;
    (ii) no beyond-limit move without a corporate action in t-29..t (flag BNC, observable at t). Such moves
         are liquidation trading (정리매매) or post-halt resumptions. This also guarantees that no universe
         member's signal history depends on the return-cleaning rule that looks at future delisting dates
         (kr_01 rule 2b), i.e. signals carry no look-ahead.
  ALL   = eligible with Marcap_t >= 20th percentile of eligible Marcap (microcap screen).
  LARGE = top 200 eligible stocks by Marcap_t.

Signals (raw values; the sort direction is applied in kr_03):
  MOM_12_1  exp(CL[t-21]-CL[t-252])-1, listed at t-252   MOM_6_1  exp(CL[t-21]-CL[t-126])-1, listed at t-126
  REV_1M    exp(CL[t]-CL[t-21])-1              HIGH52   adjusted Close_t / max adjusted High over t-251..t
  VOL_3M    std of valid daily returns t-62..t (>= 40 obs)
  MAX_1M    max valid daily return t-20..t (>= 15 obs)
  TURN_1M   mean Amount/Marcap over listed days t-20..t (>= 15 obs)
  SIZE      log Marcap_t
  PMA200    adjusted Close_t / SMA200 of adjusted close (>= 180 listed days in t-199..t)
  RSI14     Wilder RSI(14) on split-adjusted closes (full-history recursion)
  BBPCTB    Bollinger %B (20 days, 2 population sd) of adjusted closes (all 20 days listed)
  REV_1W    exp(CL[t]-CL[t-5])-1 (weekly)      VSPIKE   mean Amount t-4..t / mean Amount t-59..t (weekly)
"""
import sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import CACHE, load_meta, open_mat, month_end_idx, week_end_idx

LOOKBACK = 252


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Data:
    """Bundle of (memory-mapped) matrices; every method only touches rows <= t."""

    def __init__(self, arrays):
        for k, v in arrays.items():
            setattr(self, k, v)


def load_data(strict=False, cache=None):
    sfx = '_strict' if strict else ''
    o = lambda n: open_mat(n, cache=cache)
    d = dict(CL=o('cumlog' + sfx), R=o('ret' + sfx), VALID=o('valid' + sfx),
             E=o('exists'), CLOSE=o('close'), HIGH=o('high'), AMT=o('amount'),
             MCAP=o('marcap'), NCLS=o('namecls'), TR=o('traded'), BNC=o('beyond_nonca'), MK=o('mkt'))
    return Data(d)


def build_cum(D, cache_name=None):
    """Prefix counts (int16, T x N) of valid days, positive-amount days and beyond-limit non-CA days."""
    T, N = D.E.shape
    out = {k: np.empty((T, N), dtype=np.int16) for k in ('CV', 'CA', 'CB')}
    acc = {k: np.zeros(N, dtype=np.int16) for k in out}
    for t0 in range(0, T, 500):
        t1 = min(T, t0 + 500)
        src = {'CV': np.asarray(D.VALID[t0:t1]),
               'CA': np.nan_to_num(np.asarray(D.AMT[t0:t1]), nan=0.0) > 0,
               'CB': np.asarray(D.BNC[t0:t1])}
        for k in out:
            c = np.cumsum(src[k].astype(np.int16), axis=0, dtype=np.int16) + acc[k]
            out[k][t0:t1] = c
            acc[k] = c[-1].copy()
    D.CV, D.CA, D.CB = out['CV'], out['CA'], out['CB']
    return D


def window_count(C, t, w):
    """Number of flagged days in rows t-w+1..t from prefix counts C (requires t-w >= -1)."""
    assert t - w >= -1
    base = C[t - w].astype(np.int32) if t - w >= 0 else 0
    return C[t].astype(np.int32) - base


def universe_at(D, t, return_counts=False):
    assert t >= LOOKBACK - 1
    e = np.asarray(D.E[t])
    close = np.asarray(D.CLOSE[t]); mcap = np.asarray(D.MCAP[t])
    ncls = np.asarray(D.NCLS[t]); trd = np.asarray(D.TR[t])
    nvalid = window_count(D.CV, t, 252)
    npos = window_count(D.CA, t, 5)
    nbnc = window_count(D.CB, t, 30)
    with np.errstate(invalid='ignore'):
        base = e & (ncls == 0) & (close >= 1000) & (mcap > 0) & (nvalid >= 200) & (npos >= 4)
        elig = base & trd & (nbnc == 0)
    if return_counts:
        return elig, int(base.sum()), int((base & ~trd).sum()), int((base & trd & (nbnc > 0)).sum())
    m = mcap[elig]
    cut = np.quantile(m.astype(np.float64), 0.20) if m.size else np.inf
    allu = elig & (mcap >= cut)
    large = np.zeros_like(elig)
    if m.size:
        idx = np.nonzero(elig)[0]
        order = idx[np.argsort(-mcap[idx].astype(np.float64), kind='stable')]
        large[order[:200]] = True
    return elig, allu, large


def monthly_signals_at(D, t, rsi_row):
    assert t >= LOOKBACK
    out = {}
    cl = lambda i: np.asarray(D.CL[i])
    with np.errstate(invalid='ignore', over='ignore', divide='ignore'):
        clt = cl(t)
        ex252 = np.asarray(D.E[t - 252]); ex126 = np.asarray(D.E[t - 126])
        out['MOM_12_1'] = np.where(ex252, np.expm1(cl(t - 21) - cl(t - 252)), np.nan)
        out['MOM_6_1'] = np.where(ex126, np.expm1(cl(t - 21) - cl(t - 126)), np.nan)
        out['REV_1M'] = np.expm1(clt - cl(t - 21))
        # HIGH52 on split-adjusted prices: log adj high = log(High/Close) + CL
        w0 = t - 251
        hi = np.asarray(D.HIGH[w0:t + 1]).astype(np.float64)
        cc = np.asarray(D.CLOSE[w0:t + 1]).astype(np.float64)
        clw = np.asarray(D.CL[w0:t + 1])
        ex = np.asarray(D.E[w0:t + 1])
        lh = np.where(ex, np.log(hi / cc) + clw, -np.inf)
        mx = lh.max(axis=0)
        out['HIGH52'] = np.where(np.isfinite(mx), np.exp(clt - mx), np.nan)
        # VOL_3M, MAX_1M on valid daily returns
        r = np.asarray(D.R[t - 62:t + 1]).astype(np.float64)
        v = np.asarray(D.VALID[t - 62:t + 1])
        rv = np.where(v, r, np.nan)
        n63 = v.sum(axis=0)
        out['VOL_3M'] = np.where(n63 >= 40, np.nanstd(rv, axis=0, ddof=1), np.nan)
        rv21 = rv[-21:]; n21 = v[-21:].sum(axis=0)
        out['MAX_1M'] = np.where(n21 >= 15, np.nanmax(np.where(np.isnan(rv21), -np.inf, rv21), axis=0), np.nan)
        # TURN_1M: mean Amount/Marcap over listed days
        a = np.asarray(D.AMT[t - 20:t + 1]).astype(np.float64)
        mc = np.asarray(D.MCAP[t - 20:t + 1]).astype(np.float64)
        ex21 = np.asarray(D.E[t - 20:t + 1]) & (mc > 0)
        tr = np.where(ex21, a / mc, np.nan)
        out['TURN_1M'] = np.where(ex21.sum(axis=0) >= 15, np.nanmean(tr, axis=0), np.nan)
        out['SIZE'] = np.log(np.asarray(D.MCAP[t]).astype(np.float64))
        # PMA200: adjusted close / SMA200 (relative prices exp(CL_tau - CL_t) avoid scale issues)
        cl200 = np.asarray(D.CL[t - 199:t + 1]); ex200 = np.asarray(D.E[t - 199:t + 1])
        rel = np.where(ex200, np.exp(cl200 - clt), np.nan)
        out['PMA200'] = np.where(ex200.sum(axis=0) >= 180, 1.0 / np.nanmean(rel, axis=0), np.nan)
        # Bollinger %B (20, 2 population sd)
        rel20 = rel[-20:]
        full20 = ex200[-20:].all(axis=0)
        m20 = np.nanmean(rel20, axis=0); s20 = np.nanstd(rel20, axis=0, ddof=0)
        pb = (1.0 - (m20 - 2 * s20)) / (4 * s20)
        out['BBPCTB'] = np.where(full20 & (s20 > 1e-12), pb, np.nan)
        out['RSI14'] = rsi_row.astype(np.float64)
    e = np.asarray(D.E[t])
    for k in out:
        out[k] = np.where(e & np.isfinite(out[k]), out[k], np.nan).astype(np.float32)
    return out


def weekly_signals_at(D, t):
    assert t >= LOOKBACK
    with np.errstate(invalid='ignore', over='ignore', divide='ignore'):
        rev = np.expm1(np.asarray(D.CL[t]) - np.asarray(D.CL[t - 5]))
        a = np.nan_to_num(np.asarray(D.AMT[t - 59:t + 1]).astype(np.float64), nan=0.0)
        ex = np.asarray(D.E[t - 59:t + 1])
        n60 = ex.sum(axis=0)
        a60 = np.where(n60 >= 40, (a * ex).sum(axis=0) / np.maximum(n60, 1), np.nan)
        a5 = (a[-5:] * ex[-5:]).sum(axis=0) / np.maximum(ex[-5:].sum(axis=0), 1)
        vs = np.where(a60 > 0, a5 / a60, np.nan)
    e = np.asarray(D.E[t])
    return {'REV_1W': np.where(e & np.isfinite(rev), rev, np.nan).astype(np.float32),
            'VSPIKE': np.where(e & np.isfinite(vs), vs, np.nan).astype(np.float32)}


def compute_rsi(D, n=14, out_name='rsi14', cache=None):
    """Wilder RSI(n) on split-adjusted closes P = exp(CL); state frozen on non-listed days."""
    T, N = D.E.shape
    RSI = np.lib.format.open_memmap(f'{cache or CACHE}/{out_name}.npy', mode='w+', dtype=np.float32, shape=(T, N))
    au = np.zeros(N); ad = np.zeros(N); nobs = np.zeros(N, dtype=np.int64)
    prev_cl = np.full(N, np.nan)
    a = 1.0 / n
    for t in range(T):
        e = np.asarray(D.E[t]); clt = np.asarray(D.CL[t])
        r = np.asarray(D.R[t]).astype(np.float64)
        with np.errstate(invalid='ignore', over='ignore'):
            dp = np.exp(prev_cl) * np.nan_to_num(r, nan=0.0)
        upd = e & np.isfinite(prev_cl)
        up = np.where(upd, np.maximum(dp, 0.0), 0.0); dn = np.where(upd, np.maximum(-dp, 0.0), 0.0)
        au = np.where(upd, au + a * (up - au), au)
        ad = np.where(upd, ad + a * (dn - ad), ad)
        nobs = nobs + upd
        with np.errstate(invalid='ignore', divide='ignore'):
            rs = au / ad
            rsi = np.where(ad > 0, 100.0 - 100.0 / (1.0 + rs), np.where(au > 0, 100.0, np.nan))
        RSI[t] = np.where(e & (nobs >= 3 * n), rsi, np.nan).astype(np.float32)
        prev_cl = np.where(e, clt, prev_cl)
    RSI.flush()
    return RSI


def run(strict=False):
    t0 = time.time()
    dates, codes = load_meta()
    T, N = len(dates), len(codes)
    D = load_data(strict)
    build_cum(D)
    log('prefix counts built')
    sfx = '_strict' if strict else ''
    RSI = compute_rsi(D, 14, 'rsi14' + sfx)
    log('RSI14 done')
    me = month_end_idx(dates)
    me = me[(me >= LOOKBACK) & (me < T - 1)]          # need history and at least one future day
    we = week_end_idx(dates)
    we = we[(we >= LOOKBACK) & (we < T - 1)]
    # monthly
    nm = len(me)
    sig_names = ['MOM_12_1', 'MOM_6_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M', 'SIZE', 'PMA200',
                 'RSI14', 'BBPCTB']
    S = {k: np.full((nm, N), np.nan, dtype=np.float32) for k in sig_names}
    UE = np.zeros((nm, N), bool); UA = np.zeros((nm, N), bool); UL = np.zeros((nm, N), bool)
    MC = np.zeros((nm, N), np.float32)
    excl = []
    for i, t in enumerate(me):
        _, nbase, nhalt, nbnc = universe_at(D, t, return_counts=True)
        e, a, l = universe_at(D, t)
        UE[i], UA[i], UL[i] = e, a, l
        excl.append((str(dates[t].date()), nbase, nhalt, nbnc, int((a & (np.asarray(D.MK[t]) == 2)).sum())))
        MC[i] = np.nan_to_num(np.asarray(D.MCAP[t]), nan=0.0)
        s = monthly_signals_at(D, t, np.asarray(RSI[t]))
        for k in sig_names:
            S[k][i] = s[k]
    np.savez(f'{CACHE}/form_monthly{sfx}.npz', fidx=me, elig=UE, univ_all=UA, univ_large=UL, mcap=MC, **S)
    from kr_common import RES
    pd.DataFrame(excl, columns=['formation', 'n_pass_spec_screen', 'n_removed_halted_at_t',
                                'n_removed_beyond_limit_30d', 'n_kosdaq_in_all']).assign(
        n_eligible=UE.sum(1), n_all=UA.sum(1), n_large=UL.sum(1)).to_csv(
        f'{RES}/kr_universe_counts{sfx}.csv', index=False)
    log(f'monthly: {nm} formations {dates[me[0]].date()}..{dates[me[-1]].date()}, '
        f'mean |ALL| {UA.sum(1).mean():.0f}, mean |LARGE| {UL.sum(1).mean():.0f}')
    # weekly
    nw = len(we)
    W = {k: np.full((nw, N), np.nan, dtype=np.float32) for k in ('REV_1W', 'VSPIKE')}
    WE = np.zeros((nw, N), bool); WA = np.zeros((nw, N), bool); WL = np.zeros((nw, N), bool)
    WM = np.zeros((nw, N), np.float32)
    for i, t in enumerate(we):
        e, a, l = universe_at(D, t)
        WE[i], WA[i], WL[i] = e, a, l
        WM[i] = np.nan_to_num(np.asarray(D.MCAP[t]), nan=0.0)
        s = weekly_signals_at(D, t)
        for k in W:
            W[k][i] = s[k]
    np.savez(f'{CACHE}/form_weekly{sfx}.npz', fidx=we, elig=WE, univ_all=WA, univ_large=WL, mcap=WM, **W)
    log(f'weekly: {nw} formations {dates[we[0]].date()}..{dates[we[-1]].date()}, mean |ALL| {WA.sum(1).mean():.0f}')
    log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    run(strict='--strict' in sys.argv)
