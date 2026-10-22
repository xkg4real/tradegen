"""r2_kr_05_crash_controls.py -- Task 3: momentum crash controls on KRX (verify E5; test the macro programme's
R-03 own-volatility scaling and R-04 Daniel-Moskowitz gate on Korea), plus E5's name-level stop-loss claim.

Sleeves (12-1 momentum; books from r2_kr_03 cache/books_mom.npz):
  ALL universe quintiles (the grid): LS = Q5 - Q1 (EW, VW); LO = Q5 minus the ALL universe (EW vs EW, VW vs VW),
  i.e. the long-only book is universe + s x (Q5 - universe) and the scaled object is the excess sleeve.
  E5 construction: top 500 eligible stocks by Marcap, deciles D10 - D1 (EW, VW).
Unit-sleeve daily return x_d = gross daily return of the period-level construction (round-1 C_d series).
Controls (decided at the close of day t, applied to day t+1):
  static  s = 1
  VS      s_t = min(1, 0.12 / sigma126_t), sigma126_t = stdev(x over t-125..t) x sqrt(252), >= 126 obs (else 1)
  DM      dm_t = 0.5 if [24-month return of the rebuilt KOSPI to the last month-end <= t is < 0] and
          [sigma126 of KOSPI daily returns at t > expanding 2/3 quantile of its own history (>= 252 obs)], else 1
  VSxDM   s_t x dm_t
Costs: c x s x (formation turnover) at each rebalance + c x D x |s_t - s_{t-1}| for exposure changes, D = 2 for LS
(both legs), D = sum|w_Q5 - w_U| at formation for LO; for LO the book's own formation turnover is
(1-s) TO_U + s TO_Q5 (benchmark gross, as in the grid). Net = 35 bp (70 bp stress).
E5 stop-loss (DC-02 / E5-C07): top-500 D10-D1 EW and VW (and ALL quintiles), 15% stop from the formation close,
close trigger (long: cumulative return since formation <= -15%; short leg: >= +15%), exit at the NEXT close (the
position earns that day), proceeds in cash until the next rebalance, stop exits charged c on the value sold, the
short leg's costs reduce the long-short value. Variants: exit at the trigger close; a 10% stop. Static versions are
run through the same engine so the comparison is like-for-like.
Outputs: results/r2_kr_crash_controls.csv, r2_kr_crash_windows.csv, r2_kr_crash_exposure_2026.csv,
         r2_kr_stoploss.csv
"""
import sys, time, math
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (Panel, series, stats, quantile_groups, weights, log, to_csv, load_books, CRASH_WINDOWS,
                          window_returns, CACHE, CACHE2, RES2, max_drawdown, nw_tstat, year_returns)

C35, C70 = 0.0035, 0.0070


def sleeve_inputs(P, Lb, Sb=None, Bb=None, mc=None, memL=None, memB=None, ruleL='EW', ruleB='EW'):
    """Unit-sleeve gross daily returns x and per-formation cost bases."""
    if Sb is not None:
        _, x, _ = series(P, Lb, S=Sb, c=0.0)
        to = np.nan_to_num(Lb['to']) + np.nan_to_num(Sb['to'])
        return dict(kind='LS', x=x, to=to, D=np.full(P.K, 2.0))
    _, x, _ = series(P, Lb, B=Bb, c=0.0, cb=0.0)
    D = np.zeros(P.K)
    for k in range(P.K):
        mL = np.flatnonzero(memL[k]); mB = np.flatnonzero(memB[k])
        wl = np.zeros(P.N); wb = np.zeros(P.N)
        wl[mL] = weights(mL, ruleL, mc[k]); wb[mB] = weights(mB, ruleB, mc[k])
        D[k] = np.abs(wl - wb).sum()
    return dict(kind='LO', x=x, toL=np.nan_to_num(Lb['to']), toB=np.nan_to_num(Bb['to']), D=D)


def vol_scale(x, valid, target=0.12, win=126):
    """s_t from the sleeve's own daily returns through t (applied to t+1)."""
    s = np.ones(len(x))
    xs = pd.Series(np.where(valid, x, np.nan))
    sig = xs.rolling(win, min_periods=win).std(ddof=1).values * math.sqrt(252)
    with np.errstate(invalid='ignore', divide='ignore'):
        s = np.where(np.isfinite(sig) & (sig > 0), np.minimum(1.0, target / sig), 1.0)
    return s, sig


def dm_gate(P):
    k = pd.read_parquet(f'{CACHE}/kospi_rebuilt.parquet')
    assert (k.index.values.astype('datetime64[D]') == P.dates.values.astype('datetime64[D]')).all()
    r = k['ret'].values; lvl = k['level'].values
    sig = pd.Series(r).rolling(126, min_periods=126).std(ddof=1).values * math.sqrt(252)
    # expanding 2/3 quantile of sigma126 history through t (>= 252 observations of sigma126)
    q = pd.Series(sig).expanding(min_periods=252).quantile(2 / 3).values
    hivol = np.isfinite(q) & (sig > q)
    me = pd.Series(np.arange(len(P.dates)), index=P.dates).groupby([P.dates.year, P.dates.month]).max().values
    bear = np.zeros(len(r), bool); r24 = np.full(len(r), np.nan)
    for t in range(len(r)):
        j = np.searchsorted(me, t, side='right') - 1          # last month-end <= t
        if j >= 24:
            r24[t] = lvl[me[j]] / lvl[me[j - 24]] - 1.0
            bear[t] = r24[t] < 0
    dm = np.where(bear & hivol, 0.5, 1.0)
    return dm, dict(r24=r24, sig_mkt=sig, q23=q, bear=bear, hivol=hivol)


def apply_overlay(P, sl, s, c):
    """Daily net returns of the scaled sleeve. s[t] decided at close t, applied to day t+1 (s[-1] unused)."""
    x = sl['x']
    T = P.T
    out = np.full(T, np.nan)
    pos = np.full(T, np.nan)
    first = P.starts[0]
    prev_s = None
    for k in range(P.K):
        a, b = P.starts[k], P.ends[k]
        for d in range(a, b):
            sd = s[d - 1]                                    # exposure held over day d
            cost = 0.0
            if d == a:                                       # formation trade at close d-1 = t_k
                if sl['kind'] == 'LS':
                    cost += c * sd * sl['to'][k]
                else:
                    cost += c * ((1 - sd) * sl['toB'][k] + sd * sl['toL'][k])   # book (1-s)U + sQ5; benchmark gross
            if prev_s is not None and d != first:
                cost += c * sl['D'][k] * abs(sd - prev_s)     # exposure change traded at close d-1
            xd = x[d] if np.isfinite(x[d]) else 0.0
            out[d] = sd * xd - cost
            pos[d] = sd
            prev_s = sd
    return out, pos


def period_from_daily(P, daily):
    """Monthly holding-period returns compounded from a daily series."""
    per = np.full(P.K, np.nan)
    for k in range(P.K):
        seg = daily[P.starts[k]:P.ends[k]]
        per[k] = np.prod(1.0 + np.nan_to_num(seg)) - 1.0
    return per


def stoploss_book(P, members_fn, rule, mc, stop=None, side='long', exit_lag=1):
    """Monthly book with an optional name-level stop. side 'long': stop when the cumulative return since the
    formation close <= -stop; side 'short' (the short leg of a long-short): stop when it is >= +stop. A stopped
    name is sold at the close of trigger day + exit_lag and its proceeds sit in cash to the next rebalance.
    Returns gross daily returns, formation turnover per period, value sold at stop exits per day (as a share of
    the period-start book value) and the number of stops. Costs are applied by the caller."""
    T, N, K = P.T, P.N, P.K
    daily = np.full(T, np.nan); TO = np.zeros(K); exitv = np.zeros(T); nstop = 0
    v_names = np.zeros(N); cash = 0.0
    for k in range(K):
        t = P.fidx[k]; te = P.fidx[k + 1] if k + 1 < K else T - 1
        m = members_fn(k)
        tot = v_names.sum() + cash
        vn = v_names / tot if tot > 0 else v_names
        live = P.E[t]
        # round-1 Book rule: a holding halted at the formation close cannot be sold; it is carried at its value
        stuck = (vn > 0) & live & ~P.TR[t] if k > 0 else np.zeros(N, bool)
        w = np.zeros(N); w[m] = (1.0 - vn[stuck].sum()) * weights(m, rule, mc[k]); w[stuck] = vn[stuck]
        tradable = live & ~stuck
        TO[k] = 1.0 if k == 0 else float(np.abs(w[tradable] - vn[tradable]).sum())   # dead names / cash: buys only
        Rb = np.nan_to_num(P.R[t + 1:te + 1].astype(np.float64), nan=0.0)
        A = np.cumprod(P.E[t + 1:te + 1], axis=0).astype(bool)
        idx = np.flatnonzero(w)
        G = np.cumprod(1.0 + Rb[:, idx] * A[:, idx], axis=0)     # growth since the formation close
        nd = G.shape[0]
        still = np.ones(len(idx), bool)
        sold = np.zeros(nd)
        Gi = G.copy()
        if stop is not None and nd > 1:
            trig = (G <= 1 - stop) if side == 'long' else (G >= 1 + stop)
            has = trig.any(axis=0)
            dexit = np.where(has, trig.argmax(axis=0), nd) + exit_lag
            ex = has & (dexit <= nd - 1)
            for jj in np.flatnonzero(ex):
                de = dexit[jj]
                Gi[de + 1:, jj] = Gi[de, jj]                    # proceeds frozen in cash after the exit close
                sold[de] += w[idx[jj]] * Gi[de, jj]
            still = ~ex
            nstop += int(ex.sum())
        vals = w[idx][None, :] * Gi
        pv = vals.sum(axis=1)
        prev = np.concatenate(([1.0], pv[:-1]))
        daily[t + 1:te + 1] = pv / prev - 1.0
        exitv[t + 1:te + 1] = sold
        endv = np.zeros(N); endv[idx[still]] = vals[-1, still]
        cash = float(vals[-1, ~still].sum())
        v_names = endv
    return daily, TO, exitv, nstop


def ls_from_legs(P, L, S, c):
    """Long-short from two stop-loss legs: C_d = 1 + (V_L-1) - (V_S-1) - c*(TO_L+TO_S) - c*(cum. stop exits L+S),
    all in units of the period-start value of each $1 leg (the short leg's trading costs reduce C)."""
    dl, tol, exl, _ = L; ds, tos, exs, _ = S
    per = np.full(P.K, np.nan); daily = np.full(P.T, np.nan)
    for k in range(P.K):
        a, b = P.starts[k], P.ends[k]
        VL = np.cumprod(1 + np.nan_to_num(dl[a:b])); VS = np.cumprod(1 + np.nan_to_num(ds[a:b]))
        cc = c * (tol[k] + tos[k]) + c * np.cumsum(exl[a:b] + exs[a:b])
        Cc = 1 + (VL - 1) - (VS - 1) - cc
        daily[a:b] = Cc / np.concatenate(([1.0], Cc[:-1])) - 1
        per[k] = Cc[-1] - 1
    return per, daily, tol + tos


def main():
    t0 = time.time()
    P = Panel()
    X = P.extra()
    F = P.F
    U, mc = F['univ_all'], F['mcap']
    B = load_books(f'{CACHE2}/books_mom.npz')
    dm, dmi = dm_gate(P)
    q5 = {}; q1 = {}
    for k in range(P.K):
        g = quantile_groups(F['MOM_12_1'][k], U[k], 5, k)
        q5[k] = g == 5
    memQ5 = np.array([q5[k] for k in range(P.K)])
    sleeves = {
        'LS_EW (ALL quintiles)': sleeve_inputs(P, B['GRID|MOM_12_1|all|all|EW|Q5'], Sb=B['GRID|MOM_12_1|all|all|EW|Q1']),
        'LS_VW (ALL quintiles)': sleeve_inputs(P, B['GRID|MOM_12_1|all|all|VW|Q5'], Sb=B['GRID|MOM_12_1|all|all|VW|Q1']),
        'LO_EW excess (Q5 vs EW univ)': sleeve_inputs(P, B['GRID|MOM_12_1|all|all|EW|Q5'], Bb=B['UNIV|ALL|EW'], mc=mc,
                                                      memL=memQ5, memB=U, ruleL='EW', ruleB='EW'),
        'LO_VW excess (Q5 vs VW univ)': sleeve_inputs(P, B['GRID|MOM_12_1|all|all|VW|Q5'], Bb=B['UNIV|ALL|VW'], mc=mc,
                                                      memL=memQ5, memB=U, ruleL='VW', ruleB='VW'),
        'E5 top500 D10-D1 EW': sleeve_inputs(P, B['TOP500|MOM_12_1|n10|EW|Q10'], Sb=B['TOP500|MOM_12_1|n10|EW|Q1']),
        'E5 top500 D10-D1 VW': sleeve_inputs(P, B['TOP500|MOM_12_1|n10|VW|Q10'], Sb=B['TOP500|MOM_12_1|n10|VW|Q1']),
    }
    valid = np.zeros(P.T, bool); valid[P.starts[0]:] = True
    rows, wrows, exprows = [], [], []
    pm_full = np.ones(P.K, bool)
    pm_e5 = P.pmask('2000-01-01', '2026-12-31')
    pm_16 = P.pmask('2016-01-01', '2026-12-31')
    jun26 = (P.dates >= pd.Timestamp('2026-06-01')) & (P.dates <= pd.Timestamp('2026-06-30'))
    d0622 = int(np.searchsorted(P.dates.values, np.datetime64('2026-06-22')))
    d0630 = int(np.searchsorted(P.dates.values, np.datetime64('2026-06-30')))
    for nm, sl in sleeves.items():
        x = sl['x']
        s_vs, sig = vol_scale(x, valid)
        ctrl = {'static': np.ones(P.T), 'VS (own vol, 12%, cap 1)': s_vs, 'DM gate (KOSPI, floor 0.5)': dm,
                'VS x DM': s_vs * dm}
        for cn, s in ctrl.items():
            for cl, c in (('gross', 0.0), ('net35', C35), ('net70', C70)):
                daily, pos = apply_overlay(P, sl, s, c)
                per = period_from_daily(P, daily)
                for plab, pm in (('full 1996-04..2026-09', pm_full), ('E5 window 2000-01..2026-09', pm_e5),
                                 ('2016-01..2026-09', pm_16)):
                    st = stats(P, per, daily, None, pm, full=(plab.startswith('full')))
                    dmk = P.dmask(pm)
                    st['avg_exposure'] = float(np.nanmean(pos[dmk]))
                    st['pct_days_below_1'] = float(np.nanmean(pos[dmk] < 0.999))
                    for m, v in st.items():
                        rows.append(dict(sleeve=nm, control=cn, cost=cl, period=plab, metric=m, value=v))
                if cl == 'net35':
                    wr = window_returns(P, daily, CRASH_WINDOWS)
                    # static book with the same average exposure (E5 comparison)
                    avg = float(np.nanmean(pos[valid]))
                    for wl, v in wr.items():
                        wrows.append(dict(sleeve=nm, control=cn, window=wl, cum_return_net35=v))
                    kjul = int(np.flatnonzero((P.pstart.year == 2026) & (P.pstart.month == 7))[0])
                    wrows.append(dict(sleeve=nm, control=cn, window='Jul-2026 calendar month', cum_return_net35=per[kjul]))
                    if cn != 'static':
                        st_daily, _ = apply_overlay(P, sl, np.full(P.T, avg), c)
                        for wl, v in window_returns(P, st_daily, CRASH_WINDOWS).items():
                            wrows.append(dict(sleeve=nm, control=f'static at same avg exposure as {cn} ({avg:.2f})',
                                              window=wl, cum_return_net35=v))
                    # exposure path into the 2026 crash
                    cut26 = np.flatnonzero((P.dates >= pd.Timestamp('2026-01-01')) & (s < 0.999))
                    exprows.append(dict(sleeve=nm, control=cn, s_on_2026_06_22=float(s[d0622]), s_on_2026_06_30=float(s[d0630]),
                                        min_s_june_2026=float(np.min(s[jun26])),
                                        first_cut_in_2026=str(P.dates[cut26[0]].date()) if len(cut26) else 'none',
                                        cut_before_2026_07_01=bool(np.min(s[jun26]) < 0.999 or (len(cut26) and P.dates[cut26[0]] < pd.Timestamp('2026-07-01'))),
                                        sigma126_on_2026_06_22=float(sig[d0622]) if cn.startswith('VS') else np.nan))
        log(f'{nm} done')
    to_csv(pd.DataFrame(rows), 'r2_kr_crash_controls.csv')
    to_csv(pd.DataFrame(wrows), 'r2_kr_crash_windows.csv')
    to_csv(pd.DataFrame(exprows), 'r2_kr_crash_exposure_2026.csv')
    # D&M gate diagnostics
    on = dm < 1
    onsets = np.flatnonzero(on & ~np.concatenate(([False], on[:-1])))
    gd = pd.DataFrame(dict(date=P.dates, r24=dmi['r24'], sig_mkt=dmi['sig_mkt'], q23=dmi['q23'], bear=dmi['bear'],
                           hivol=dmi['hivol'], dm=dm))
    gd.iloc[::21].to_csv(f'{RES2}/r2_kr_dm_gate_sample.csv', index=False, float_format='%.6g')
    log(f'DM gate on {on[valid].mean():.3%} of days, onsets {len(onsets)}: '
        + ', '.join(str(P.dates[i].date()) for i in onsets[:20]))
    to_csv(pd.DataFrame(dict(onset=[str(P.dates[i].date()) for i in onsets])), 'r2_kr_dm_gate_onsets.csv')
    # ---------------- E5 stop-loss ----------------
    T5 = X['top500']
    sl_rows = []
    def mem(nq, q, uni=T5):
        return lambda k: np.flatnonzero(quantile_groups(F['MOM_12_1'][k], uni[k], nq, k) == q)
    for uname, uni, nq, (qh, ql) in (('E5 top500 deciles', T5, 10, (10, 1)), ('ALL quintiles', U, 5, (5, 1))):
        for w in ('EW', 'VW'):
            for stop, lag, lab in ((None, 1, 'no stop'), (0.15, 1, '15% stop, exit next close'),
                                   (0.15, 0, '15% stop, exit same close'), (0.10, 1, '10% stop, exit next close')):
                Lg = stoploss_book(P, mem(nq, qh, uni), w, mc, stop, 'long', lag)
                Sg = stoploss_book(P, mem(nq, ql, uni), w, mc, stop, 'short', lag)
                for cl, c in (('gross', 0.0), ('net35', C35)):
                    per, daily, to = ls_from_legs(P, Lg, Sg, c)
                    pmx = pm_e5 if uname.startswith('E5') else pm_full
                    st = stats(P, per, daily, to, pmx, full=True)
                    st16 = stats(P, per, daily, to, pm_16, full=False)
                    pp = per[pmx]
                    sl_rows.append(dict(sleeve=uname, weighting=w, cost=cl, variant=lab, sharpe=st['sharpe'],
                                        ann_mean=st['ann_mean'], max_dd=st['max_dd'], worst_month=float(np.nanmin(pp)),
                                        sharpe_2016_2026=st16['sharpe'], stops_long=Lg[3], stops_short=Sg[3],
                                        turnover_per_year=st['turnover_per_year'],
                                        period='2000-01..2026-09' if uname.startswith('E5') else '1996-04..2026-09'))
                    log(f'stop {uname} {w} {cl} {lab}: Sharpe {st["sharpe"]:.3f}, worst month {np.nanmin(pp):.3f}')
    SL = pd.DataFrame(sl_rows)
    to_csv(SL, 'r2_kr_stoploss.csv')
    # consistency check: no-stop custom engine vs the run_books top-500 decile books (gross EW Sharpe, E5 window)
    perB, dB, _ = series(P, B['TOP500|MOM_12_1|n10|EW|Q10'], S=B['TOP500|MOM_12_1|n10|EW|Q1'], c=0.0)
    chk = []
    for lab, bq, bl, sl_name, pmx in (('E5 top500 deciles', 'TOP500|MOM_12_1|n10|EW|Q10', 'TOP500|MOM_12_1|n10|EW|Q1', 'E5 top500 deciles', pm_e5),
                                      ('ALL quintiles', 'GRID|MOM_12_1|all|all|EW|Q5', 'GRID|MOM_12_1|all|all|EW|Q1', 'ALL quintiles', pm_full)):
        perB, dB, _ = series(P, B[bq], S=B[bl], c=0.0)
        a = stats(P, perB, dB, None, pmx)['sharpe']
        b2 = SL[(SL.sleeve == sl_name) & (SL.weighting == 'EW') & (SL.cost == 'gross') & (SL.variant == 'no stop')].sharpe.iloc[0]
        chk.append(dict(check=f'{lab} EW gross Sharpe: run_books vs stop engine (no stop)', run_books=a, stop_engine=b2))
        log(f'engine check {lab}: run_books {a:.4f} vs stop engine {b2:.4f}')
    to_csv(pd.DataFrame(chk), 'r2_kr_stoploss_engine_check.csv')
    log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
