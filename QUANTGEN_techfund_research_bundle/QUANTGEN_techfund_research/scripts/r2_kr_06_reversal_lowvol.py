"""r2_kr_06_reversal_lowvol.py -- Task 4 (P1's reversal flag) and Task 5 (low volatility: protection or alpha?).

Task 4: 1-month reversal (REV_1M = exp(CL[t]-CL[t-21])-1), long the losers minus the winners, monthly,
  value-weighted (Marcap_t) and, for reference, equal-weighted; universes ALL (round-1 eligible set with the
  20th-percentile microcap cut) and LARGE (top 200 by Marcap); quintiles and deciles; gross, net 35, net 70 bp
  (both legs pay); periods full, 1996-2005, 2006-2015, 2016-2026-09 and 1999-2021 (the brief's window for the
  literature figure 'WML -2.95%/month, t -3.77').
Task 5: long-only lowest VOL_3M quintile (ALL), EW and VW, net 35 bp: monthly CAPM regression on the VW ALL
  universe (gross, the investable market proxy) and on the rebuilt KOSPI; beta, alpha (x12) with Newey-West t
  (6 lags), rf = 0 (no Korean short-rate series is available offline; with a short rate rf the CAPM alpha of a
  beta<1 book is LOWER by (1-beta) x rf, reported for rf = 2% and 4% as labelled assumptions), max drawdown
  vs the market, up/down-market capture, crash windows vs rebound windows.
Outputs: results/r2_kr_reversal.csv, r2_kr_lowvol.csv, r2_kr_lowvol_windows.csv
"""
import sys, time, math
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/r2/kr')
from r2_kr_common import (Panel, run_books, series, stats, quantile_groups, weights, log, to_csv, window_returns,
                          nw_tstat, CACHE, SUB3, max_drawdown)

LV_WINDOWS = [  # crash windows
    ('C 1997-11..1998-06 Asian crisis', '1997-10-31', '1998-06-30'),
    ('C 2000-03..2000-12 dot-com bust', '2000-02-29', '2000-12-31'),
    ('C 2008-06..2009-03 GFC', '2008-05-31', '2009-03-31'),
    ('C 2020-02-17..03-19 COVID crash', '2020-02-17', '2020-03-19'),
    ('C 2022 full year', '2021-12-31', '2022-12-31'),
    ('C 2024-07-11..08-05 Aug-2024 crash', '2024-07-11', '2024-08-05'),
    ('C 2026-06-22..07-30 crash', '2026-06-22', '2026-07-30'),
    # rebound windows
    ('R 1998-07..1999-06 post-crisis rebound', '1998-06-30', '1999-06-30'),
    ('R 2009-03..2009-12 post-GFC rebound', '2009-02-27', '2009-12-31'),
    ('R 2020-03-20..06-30 COVID rebound', '2020-03-19', '2020-06-30'),
    ('R 2026-01-02..06-22 melt-up', '2025-12-31', '2026-06-22'),
    ('R 2026-07-31..09-29 after crash', '2026-07-30', '2026-09-29')]


def ols_nw(y, x, lags=6):
    """OLS y = a + b x with Newey-West (Bartlett) standard errors. Returns a, b, t_a, t_b, r2."""
    y = np.asarray(y, float); x = np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = len(y)
    Xm = np.column_stack([np.ones(n), x])
    beta = np.linalg.lstsq(Xm, y, rcond=None)[0]
    e = y - Xm @ beta
    XtX_inv = np.linalg.inv(Xm.T @ Xm)
    S = (Xm * e[:, None]).T @ (Xm * e[:, None])
    for l in range(1, lags + 1):
        w = 1 - l / (lags + 1)
        G = (Xm[l:] * e[l:, None]).T @ (Xm[:-l] * e[:-l, None])
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))
    return beta[0], beta[1], beta[0] / se[0], beta[1] / se[1], r2


def main():
    t0 = time.time()
    P = Panel()
    F = P.F
    U, LG, mc = F['univ_all'], F['univ_large'], F['mcap']
    rev, vol = F['REV_1M'], F['VOL_3M']
    specs = []

    def add(name, memfn, rule):
        def fn(k):
            m = np.flatnonzero(memfn(k))
            return m, weights(m, rule, mc[k])
        specs.append((name, fn))
    for un, UU in (('ALL', U), ('LARGE', LG)):
        for w in ('EW', 'VW'):
            add(f'UNIV|{un}|{w}', lambda k, UU=UU: UU[k], w)
            for nq in (5, 10):
                for q in (1, nq):
                    add(f'REV|{un}|{w}|n{nq}|Q{q}', lambda k, UU=UU, nq=nq, q=q: quantile_groups(rev[k], UU[k], nq, k) == q, w)
    for w in ('EW', 'VW'):
        add(f'LOWVOL|ALL|{w}|Q1', lambda k: quantile_groups(vol[k], U[k], 5, k) == 1, w)
    B = run_books(P, specs, progress=180)
    log('books done')
    # ---------------- Task 4 ----------------
    periods = [(lab, P.pmask(a, b)) for lab, a, b in SUB3] + [('1999-2021', P.pmask('1999-01-01', '2021-12-31'))]
    rows = []
    for un in ('ALL', 'LARGE'):
        for w in ('VW', 'EW'):
            for nq in (5, 10):
                Lb, Sb = B[f'REV|{un}|{w}|n{nq}|Q1'], B[f'REV|{un}|{w}|n{nq}|Q{nq}']
                for cl, c in (('gross', 0.0), ('net35', 0.0035), ('net70', 0.0070)):
                    per, daily, to = series(P, Lb, S=Sb, c=c)
                    for plab, pm in periods:
                        st = stats(P, per, daily, to, pm, full=(plab == 'full'))
                        p = per[pm]; p = p[np.isfinite(p)]
                        rows.append(dict(universe=un, weighting=w, sort='quintiles' if nq == 5 else 'deciles', cost=cl,
                                         period=plab, mean_pct_month=p.mean() * 100, nw_t=st['nw_t'], ann_mean=st['ann_mean'],
                                         sharpe=st['sharpe'], max_dd=st['max_dd'], turnover_per_year=st['turnover_per_year'],
                                         pct_pos_years=st.get('pct_pos_years', np.nan), n_months=st['n_periods'],
                                         avg_names_per_leg=float((Lb['nmem'][pm].mean() + Sb['nmem'][pm].mean()) / 2)))
    R4 = pd.DataFrame(rows)
    to_csv(R4, 'r2_kr_reversal.csv')
    pd.set_option('display.width', 250)
    print(R4[(R4.cost != 'net70')].pivot_table(index=['universe', 'weighting', 'sort', 'cost'], columns='period',
                                               values='mean_pct_month').round(3).to_string())
    # ---------------- Task 5 ----------------
    kospi = pd.read_parquet(f'{CACHE}/kospi_rebuilt.parquet')['ret'].values
    mkt = {'VW ALL universe (gross)': B['UNIV|ALL|VW'], 'EW ALL universe (gross)': B['UNIV|ALL|EW']}
    pm_full = np.ones(P.K, bool)
    lv_rows, wrows = [], []
    kpi_per = np.full(P.K, np.nan)
    for k in range(P.K):
        kpi_per[k] = np.prod(1 + np.nan_to_num(kospi[P.starts[k]:P.ends[k]])) - 1
    for w in ('EW', 'VW'):
        Lb = B[f'LOWVOL|ALL|{w}|Q1']
        for cl, c in (('gross', 0.0), ('net35', 0.0035)):
            per, daily, to = series(P, Lb, c=c)
            for plab, pm in [(lab, P.pmask(a, b)) for lab, a, b in SUB3]:
                st = stats(P, per, daily, to, pm, full=(plab == 'full'))
                for mname, mb in list(mkt.items()) + [('rebuilt KOSPI', None)]:
                    if mb is None:
                        mper = kpi_per; md = kospi
                    else:
                        mper, md, _ = series(P, mb, c=0.0)
                    a, b, ta, tb, r2 = ols_nw(per[pm], mper[pm])
                    dmk = P.dmask(pm)
                    mm = mper[pm]; pp = per[pm]
                    up = mm > 0; dn = mm < 0
                    row = dict(book=f'low-vol Q1 {w}', cost=cl, period=plab, market=mname, beta=b, beta_t=tb,
                               alpha_ann_rf0=a * 12, alpha_t=ta, r2=r2,
                               alpha_ann_if_rf2pct=a * 12 - (1 - b) * 0.02, alpha_ann_if_rf4pct=a * 12 - (1 - b) * 0.04,
                               book_ann_mean=st['ann_mean'], book_vol=st['ann_vol'], book_sharpe=st['sharpe'],
                               book_maxdd=st['max_dd'], mkt_ann_mean=np.nanmean(mm) * 12,
                               mkt_vol=np.nanstd(mm, ddof=1) * math.sqrt(12),
                               mkt_sharpe=np.nanmean(mm) / np.nanstd(mm, ddof=1) * math.sqrt(12),
                               mkt_maxdd=max_drawdown(np.where(dmk, md, 0.0)[dmk]),
                               excess_vs_mkt_ann=np.nanmean(pp - mm) * 12, excess_t=nw_tstat(pp - mm, 6),
                               up_capture=np.nanmean(pp[up]) / np.nanmean(mm[up]),
                               down_capture=np.nanmean(pp[dn]) / np.nanmean(mm[dn]),
                               turnover_per_year=st['turnover_per_year'])
                    lv_rows.append(row)
            if cl == 'net35':
                wr = window_returns(P, daily, LV_WINDOWS)
                mw = {mn: window_returns(P, series(P, mb, c=0.0)[1], LV_WINDOWS) for mn, mb in mkt.items()}
                kw = window_returns(P, kospi, LV_WINDOWS)
                for wl in wr:
                    wrows.append(dict(book=f'low-vol Q1 {w} net35', window=wl, kind='crash' if wl.startswith('C') else 'rebound',
                                      book_return=wr[wl], vw_universe=mw['VW ALL universe (gross)'][wl],
                                      ew_universe=mw['EW ALL universe (gross)'][wl], kospi_rebuilt=kw[wl],
                                      book_minus_vw=wr[wl] - mw['VW ALL universe (gross)'][wl],
                                      book_minus_ew=wr[wl] - mw['EW ALL universe (gross)'][wl]))
    LV = pd.DataFrame(lv_rows)
    to_csv(LV, 'r2_kr_lowvol.csv')
    WV = pd.DataFrame(wrows)
    to_csv(WV, 'r2_kr_lowvol_windows.csv')
    print(LV[(LV.period == 'full')][['book', 'cost', 'market', 'beta', 'alpha_ann_rf0', 'alpha_t', 'alpha_ann_if_rf4pct',
                                     'book_sharpe', 'mkt_sharpe', 'book_maxdd', 'mkt_maxdd', 'up_capture', 'down_capture']].round(3).to_string())
    print(WV.round(3).to_string())
    log(f'done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
