"""kr_04_stats.py -- long-short / long-only statistics, sub-periods, years, event windows, correlations.

Series construction (per holding period k with formation close t_k, days t_k+1..t_{k+1}):
  V_L,d, V_S,d, V_B,d = compounded gross values of the long book, short book, benchmark (start 1).
  cost_k = c * (turnover_L,k [+ turnover_S,k for long-short]);  c in {0, 35 bp, 70 bp} per side.
  LO       : C_d = V_L,d - cost_k                         period return R_L - cost_k
  LS       : C_d = 1 - cost_k + V_L,d - V_S,d             period return R_L - R_S - cost_k
             ($1 long, $1 short, both legs pay costs, cash collateral earns 0%)
  LO_xs_UEW / LO_xs_UVW : C_d = 1 - cost_k + V_L,d - V_B,d (benchmark = universe EW / VW, gross)
  Daily return = C_d / C_{d-1} - 1 with C_0 = 1, so daily returns compound exactly to the period return.
  LO_excl_worst : universe minus the worst quintile (exclusion screen), long-only, with its own turnover.
Turnover: per leg per rebalance = sum |w_new - w_drifted_old|; 'turnover_per_year' is per year and, for LS, the
sum of both legs (the cost base); LS rows also carry turnover_per_year_long_leg / _short_leg.
Statistics use period returns (monthly: x12, sqrt12, NW 6 lags; weekly: x52, sqrt52, NW 4 lags);
max drawdown, total return and positive-year counts use the daily series. Periods are assigned to the
calendar time of their first holding day. Sharpe = mean/vol of raw returns (rf = 0; long-short and excess
series are self-financing; for absolute long-only Sharpe this ignores the KRW cash rate).
"""
import sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import (CACHE, RES, COST, SUBPERIODS, YEARS_REPORT, EVENT_WINDOWS, load_meta, nw_tstat,
                       max_drawdown)

# label -> (freq, book key, long quintile, short quintile)
SIGNALS = {
    'MOM_12_1': ('monthly', 'MOM_12_1', 5, 1), 'MOM_6_1': ('monthly', 'MOM_6_1', 5, 1),
    'REV_1M': ('monthly', 'REV_1M', 1, 5), 'HIGH52': ('monthly', 'HIGH52', 5, 1),
    'VOL_3M': ('monthly', 'VOL_3M', 1, 5), 'MAX_1M': ('monthly', 'MAX_1M', 1, 5),
    'TURN_1M_LOW': ('monthly', 'TURN_1M', 1, 5), 'TURN_1M_HIGH': ('monthly', 'TURN_1M', 5, 1),
    'SIZE': ('monthly', 'SIZE', 1, 5), 'PMA200': ('monthly', 'PMA200', 5, 1),
    'RSI14_CON': ('monthly', 'RSI14', 1, 5), 'RSI14_MOM': ('monthly', 'RSI14', 5, 1),
    'BBPCTB_CON': ('monthly', 'BBPCTB', 1, 5), 'BBPCTB_MOM': ('monthly', 'BBPCTB', 5, 1),
    'REV_1W': ('weekly', 'REV_1W', 1, 5), 'REV_1W_VSlow': ('weekly', 'REV_1W_VSlow', 1, 5),
    'REV_1W_VSmid': ('weekly', 'REV_1W_VSmid', 1, 5), 'REV_1W_VShigh': ('weekly', 'REV_1W_VShigh', 1, 5),
}
CORR_SIGNALS = ['MOM_12_1', 'MOM_6_1', 'REV_1M', 'HIGH52', 'VOL_3M', 'MAX_1M', 'TURN_1M_LOW', 'SIZE', 'PMA200',
                'RSI14_CON', 'BBPCTB_CON', 'REV_1W']
UNIVS = ('ALL', 'LARGE')
WTS = ('EW', 'VW')
ANN = {'monthly': 12, 'weekly': 52}
NWL = {'monthly': 6, 'weekly': 4}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


class Freq:
    def __init__(self, freq, dates, sfx=''):
        self.freq = freq
        self.D = pd.read_parquet(f'{CACHE}/port_daily_{freq}{sfx}.parquet')
        z = np.load(f'{CACHE}/port_turnover_{freq}{sfx}.npz')
        self.names = list(z['names']); self.idx = {n: i for i, n in enumerate(self.names)}
        self.TO = z['turnover']; self.fidx = z['fidx']
        self.dates = dates; self.T = len(dates); self.K = len(self.fidx)
        self.starts = self.fidx + 1
        self.ends = np.append(self.fidx[1:], self.T - 1) + 1          # exclusive slice end
        self.pstart = dates[self.starts]                              # first holding day of each period
        self.A = ANN[freq]; self.L = NWL[freq]

    def book(self, name):
        return np.nan_to_num(self.D[name].values, nan=0.0), np.nan_to_num(self.TO[self.idx[name]], nan=0.0)

    def series(self, long, short=None, bench=None, c=0.0):
        rl, tol = self.book(long)
        if short is not None:
            rs, tos = self.book(short)
        if bench is not None:
            rb, _ = self.book(bench)
        daily = np.full(self.T, np.nan); per = np.full(self.K, np.nan)
        for k in range(self.K):
            s, e = self.starts[k], self.ends[k]
            VL = np.cumprod(1.0 + rl[s:e])
            cost = c * tol[k]
            if short is not None:
                cost += c * tos[k]
                C = 1.0 - cost + VL - np.cumprod(1.0 + rs[s:e])
            elif bench is not None:
                C = 1.0 - cost + VL - np.cumprod(1.0 + rb[s:e])
            else:
                C = VL - cost
            prev = np.concatenate(([1.0], C[:-1]))
            daily[s:e] = C / prev - 1.0
            per[k] = C[-1] - 1.0
        to = tol + (tos if short is not None else 0.0)
        return per, daily, to


def stats_block(F, per, daily, to, pmask, dmask, full_metrics=True):
    p = per[pmask]
    p = p[np.isfinite(p)]
    out = {}
    n = len(p)
    out['n_periods'] = n
    if n < 3:
        return out
    d = daily[dmask]
    d = d[np.isfinite(d)]
    mu, sd = p.mean(), p.std(ddof=1)
    out['ann_mean'] = mu * F.A
    out['ann_vol'] = sd * np.sqrt(F.A)
    out['sharpe'] = mu / sd * np.sqrt(F.A) if sd > 0 else np.nan
    out['total_return'] = float(np.prod(1.0 + d) - 1.0)
    out['cagr'] = float((1.0 + out['total_return']) ** (F.A / n) - 1.0) if out['total_return'] > -1 else -1.0
    out['max_dd'] = max_drawdown(d)
    out['turnover_per_year'] = float(np.nanmean(to[pmask]) * F.A)
    out['hit_rate'] = float((p > 0).mean())
    if full_metrics:
        out['nw_t'] = nw_tstat(p, F.L)
        dd = pd.Series(daily[dmask], index=F.dates[dmask]).dropna()
        yr = (1.0 + dd).groupby(dd.index.year).prod() - 1.0
        cnt = dd.groupby(dd.index.year).size()
        yr = yr[cnt >= 60]
        out['pct_pos_years'] = float((yr > 0).mean()) if len(yr) else np.nan
        out['n_years'] = int(len(yr))
    return out


def period_masks(F):
    """Period masks by first holding day; the daily mask covers exactly the days of the selected periods
    (so daily-based metrics such as max drawdown use the same periods as the period-based ones)."""
    if not hasattr(F, '_pid'):
        pid = np.full(F.T, -1)
        for k in range(F.K):
            pid[F.starts[k]:F.ends[k]] = k
        F._pid = pid
    pid = F._pid

    def dmask(pm):
        return (pid >= 0) & pm[np.maximum(pid, 0)]
    sp = {}
    for lab, a, b in SUBPERIODS:
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        pm = np.asarray((F.pstart >= a) & (F.pstart <= b))
        sp[lab] = (pm, dmask(pm), True)
    for y in YEARS_REPORT:
        pm = np.asarray(F.pstart.year == y)
        sp[str(y)] = (pm, dmask(pm), False)
    return sp


def window_bounds(dates):
    out = []
    for lab, a, b in EVENT_WINDOWS:
        ia = int(np.searchsorted(dates.values, np.datetime64(a), side='right') - 1)   # last day <= a
        ib = int(np.searchsorted(dates.values, np.datetime64(b), side='right') - 1)
        out.append((lab, ia, ib))
    return out


def main(sfx=''):
    t0 = time.time()
    dates, _ = load_meta()
    FR = {f: Freq(f, dates, sfx) for f in ('monthly', 'weekly')}
    rows, ev_rows, daily_store, monthly_cal = [], [], {}, {}
    wins = window_bounds(dates)

    PM = {f: period_masks(F) for f, F in FR.items()}

    def emit(F, sig, u, wt, leg, cl, per, daily, to, metrics_full=True, periods=None):
        for plab, (pm, dm, full) in PM[F.freq].items():
            if periods is not None and plab not in periods:
                continue
            st = stats_block(F, per, daily, to, pm, dm, full and metrics_full)
            for m, v in st.items():
                rows.append((sig, F.freq, u, wt, leg, cl, plab, m, v))

    def emit_events(sig, u, wt, leg, cl, daily):
        for lab, ia, ib in wins:
            seg = daily[ia + 1:ib + 1]
            v = float(np.prod(1.0 + seg) - 1.0) if np.isfinite(seg).all() and len(seg) else np.nan
            ev_rows.append((sig, u, wt, leg, cl, lab, str(dates[ia].date()), str(dates[ib].date()), v))

    # universe benchmarks (as long-only portfolios, with their own turnover)
    for f, F in FR.items():
        for u in UNIVS:
            for wt in WTS:
                name = f'{f}|UNIV|{u}|{wt}|ALL'
                for cl, c in COST.items():
                    per, daily, to = F.series(name, c=c)
                    if f == 'monthly':
                        emit(F, 'UNIV', u, wt, 'LO', cl, per, daily, to)
                        emit_events('UNIV', u, wt, 'LO', cl, daily)
                        daily_store[('UNIV', u, wt, 'LO', cl)] = daily
    log('universe done')
    for sig, (f, key, ql, qs) in SIGNALS.items():
        F = FR[f]
        for u in UNIVS:
            for wt in WTS:
                L = f'{f}|{key}|{u}|{wt}|Q{ql}'; S = f'{f}|{key}|{u}|{wt}|Q{qs}'
                for cl, c in COST.items():
                    per, daily, to = F.series(L, short=S, c=c)
                    emit(F, sig, u, wt, 'LS', cl, per, daily, to); emit_events(sig, u, wt, 'LS', cl, daily)
                    daily_store[(sig, u, wt, 'LS', cl)] = daily
                    tol, tos = F.book(L)[1], F.book(S)[1]
                    for plab, (pm, dm, full) in PM[f].items():
                        rows.append((sig, f, u, wt, 'LS', cl, plab, 'turnover_per_year_long_leg', float(tol[pm].mean() * F.A)))
                        rows.append((sig, f, u, wt, 'LS', cl, plab, 'turnover_per_year_short_leg', float(tos[pm].mean() * F.A)))
                    per, daily, to = F.series(L, c=c)
                    emit(F, sig, u, wt, 'LO', cl, per, daily, to); emit_events(sig, u, wt, 'LO', cl, daily)
                    daily_store[(sig, u, wt, 'LO', cl)] = daily
                    for bw in WTS:
                        per, daily, to = F.series(L, bench=f'{f}|UNIV|{u}|{bw}|ALL', c=c)
                        emit(F, sig, u, wt, f'LO_xs_U{bw}', cl, per, daily, to)
                        emit_events(sig, u, wt, f'LO_xs_U{bw}', cl, daily)
                        daily_store[(sig, u, wt, f'LO_xs_U{bw}', cl)] = daily
                # exclusion screen: universe minus the worst quintile (long-only, monthly signals)
                if f == 'monthly':
                    X = f'{f}|{key}|{u}|{wt}|NOTQ{qs}'
                    for cl, c in COST.items():
                        per, daily, to = F.series(X, c=c)
                        emit(F, sig, u, wt, 'LO_excl_worst', cl, per, daily, to)
                        emit_events(sig, u, wt, 'LO_excl_worst', cl, daily)
                        daily_store[(sig, u, wt, 'LO_excl_worst', cl)] = daily
                        for bw in WTS:
                            per, daily, to = F.series(X, bench=f'{f}|UNIV|{u}|{bw}|ALL', c=c)
                            emit(F, sig, u, wt, f'LO_excl_worst_xs_U{bw}', cl, per, daily, to)
                            emit_events(sig, u, wt, f'LO_excl_worst_xs_U{bw}', cl, daily)
                            daily_store[(sig, u, wt, f'LO_excl_worst_xs_U{bw}', cl)] = daily
                # individual quintiles (base signal key only once; gross and net35; full + sub-periods)
                if sig in ('TURN_1M_HIGH', 'RSI14_MOM', 'BBPCTB_MOM'):
                    continue
                for q in range(1, 6):
                    nm = f'{f}|{key}|{u}|{wt}|Q{q}'
                    for cl in ('gross', 'net35'):
                        per, daily, to = F.series(nm, c=COST[cl])
                        emit(F, key, u, wt, f'Q{q}', cl, per, daily, to, metrics_full=False,
                             periods=[s[0] for s in SUBPERIODS])
                        daily_store[(key, u, wt, f'Q{q}', cl)] = daily
        log(f'{sig} done')
    tab = pd.DataFrame(rows, columns=['signal', 'freq', 'universe', 'weighting', 'leg', 'cost_level', 'period',
                                      'metric', 'value'])
    tab = tab[['signal', 'universe', 'weighting', 'leg', 'cost_level', 'period', 'metric', 'value', 'freq']]
    tab.to_csv(f'{RES}/kr_signal_stats_long{sfx}.csv', index=False, float_format='%.6g')
    ev = pd.DataFrame(ev_rows, columns=['signal', 'universe', 'weighting', 'leg', 'cost_level', 'window',
                                        'start_close', 'end_close', 'cum_return'])
    ev.to_csv(f'{RES}/kr_event_windows{sfx}.csv', index=False, float_format='%.6g')
    # correlations of calendar-month long-short gross returns
    corr_rows = []
    for u in UNIVS:
        for wt in WTS:
            M = {}
            for s in CORR_SIGNALS:
                d = pd.Series(daily_store[(s, u, wt, 'LS', 'gross')], index=dates).dropna()
                M[s] = (1.0 + d).groupby([d.index.year, d.index.month]).prod() - 1.0
            M = pd.DataFrame(M).dropna()
            C = M.corr()
            for a in CORR_SIGNALS:
                for b in CORR_SIGNALS:
                    corr_rows.append((u, wt, a, b, C.loc[a, b], len(M)))
            if u == 'ALL':
                C.to_csv(f'{RES}/kr_ls_correlation_{u}_{wt}{sfx}.csv', float_format='%.3f')
    pd.DataFrame(corr_rows, columns=['universe', 'weighting', 'signal_a', 'signal_b', 'corr', 'n_months']).to_csv(
        f'{RES}/kr_ls_correlations{sfx}.csv', index=False, float_format='%.4f')
    # keep daily series for charts / summary
    keys = list(daily_store)
    arr = np.vstack([daily_store[k] for k in keys]).astype(np.float64)
    cols = ['|'.join(k) for k in keys]
    pd.DataFrame(arr.T, index=dates, columns=cols).to_parquet(f'{CACHE}/series_daily{sfx}.parquet')
    log(f'stats rows {len(tab):,}, event rows {len(ev):,}; {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main('_strict' if '--strict' in sys.argv else '')
