"""r2_kr_common.py -- shared code for the round-2 Korea data lab (QUANTGEN).

Re-uses the round-1 panel (/home/claude/datalab/kr/cache) and the round-1 portfolio mechanics
(kr_03_portfolios.Book and quantile_groups), so every number here is produced on the same panel,
universe and cleaning rules as round 1.

Conventions (identical to round 1 unless stated):
  * Decide at the close of formation day t (last trading day of the month); returns are earned from t+1.
  * Daily price returns r = ChangesRatio/100 after the round-1 cleaning (cache/ret.npy); dividends excluded.
  * Books are bought at the formation close and held buy-and-hold (weights drift) to the next formation
    close; delisted names are frozen as cash; names halted at a rebalance are carried (Book class).
  * Turnover per rebalance = sum |w_new - w_drifted| over listed, tradable names; costs = c x turnover,
    charged at the formation close, c in {0, 35 bp, 70 bp} per side.
  * Period statistics use monthly holding-period returns (x12, sqrt(12), Newey-West 6 lags); max drawdown,
    total return and calendar-year counts use the daily series. A period belongs to the calendar time of
    its first holding day.
"""
import os, sys, math, json, time, itertools
import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

sys.path.insert(0, '/home/claude/datalab/scripts')
from kr_common import (CACHE, RAW, SEED, load_meta, open_mat, nw_tstat, max_drawdown, month_end_idx,  # noqa: F401
                       write_json, clean_json, classify_name, sha256)
from kr_03_portfolios import Book, quantile_groups  # noqa: F401  (round-1 engine, reused unchanged)

R2 = '/home/claude/datalab/r2/kr'
CACHE2 = f'{R2}/cache'
RES2 = f'{R2}/results'
CH2 = f'{R2}/charts'
LOG2 = f'{R2}/logs'
for _d in (CACHE2, RES2, CH2, LOG2):
    os.makedirs(_d, exist_ok=True)

COSTS = {'gross': 0.0, 'net35': 0.0035, 'net70': 0.0070}
ANN = 12
NW_LAGS = 6
BOOT_B = 2000
BOOT_BLOCK = 3

# Task-1 grid periods (by first holding day of each monthly period)
GRID_PERIODS = [('full', '1990-01-01', '2026-12-31'),
                ('1996-2005', '1996-01-01', '2005-12-31'),
                ('2006-2015', '2006-01-01', '2015-12-31'),
                ('2015-07..2024-12', '2015-07-01', '2024-12-31'),
                ('2016-01..2026-09', '2016-01-01', '2026-12-31')]
SUB3 = [('full', '1990-01-01', '2026-12-31'),
        ('1996-2005', '1996-01-01', '2005-12-31'),
        ('2006-2015', '2006-01-01', '2015-12-31'),
        ('2016-2026-09', '2016-01-01', '2026-12-31')]

# Event windows: compounded over trading days d with start_close < d <= end_close (round-1 convention).
EXCL_WINDOWS = [('2008-06..2009-03 GFC', '2008-05-31', '2009-03-31'),
                ('2020-02-17..03-19 COVID crash', '2020-02-17', '2020-03-19'),
                ('2020-03-20..06-30 COVID rebound', '2020-03-19', '2020-06-30'),
                ('2022 full year', '2021-12-31', '2022-12-31'),
                ('2026-01-02..06-22 melt-up', '2025-12-31', '2026-06-22'),
                ('2026-06-22..07-30 crash', '2026-06-22', '2026-07-30'),
                ('2026-07-31..09-29 after crash', '2026-07-30', '2026-09-29')]
CRASH_WINDOWS = [('2008-06..2009-03 GFC', '2008-05-31', '2009-03-31'),
                 ('2009-03..2009-05 post-GFC rebound (D&M crash months)', '2009-02-27', '2009-05-29'),
                 ('2020-02-17..03-19 COVID crash', '2020-02-17', '2020-03-19'),
                 ('2020-03-20..06-30 COVID rebound', '2020-03-19', '2020-06-30'),
                 ('2026-01-02..06-22 melt-up', '2025-12-31', '2026-06-22'),
                 ('2026-06-22..07-30 crash', '2026-06-22', '2026-07-30'),
                 ('2026-07-31..09-29 after crash', '2026-07-30', '2026-09-29')]


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ----------------------------------------------------------------------------------------------
# Data access
# ----------------------------------------------------------------------------------------------
class Panel:
    """Round-1 daily matrices (memory-mapped) plus monthly formation data."""

    def __init__(self, load_returns=True):
        self.dates, self.codes = load_meta()
        self.T, self.N = len(self.dates), len(self.codes)
        self.F = dict(np.load(f'{CACHE}/form_monthly.npz'))
        self.fidx = self.F['fidx'].astype(np.int64)
        self.K = len(self.fidx)
        self.starts = self.fidx + 1                                  # first holding day of each period
        self.ends = np.append(self.fidx[1:], self.T - 1) + 1         # exclusive slice end
        self.pstart = self.dates[self.starts]
        if load_returns:
            self.R = np.asarray(open_mat('ret'))                     # float32, 136 MB
            self.E = np.asarray(open_mat('exists'))
            self.TR = np.asarray(open_mat('traded'))
        self._pid = None

    def extra(self):
        if not hasattr(self, '_X'):
            self._X = dict(np.load(f'{CACHE2}/form_r2.npz'))
        return self._X

    def pid(self):
        if self._pid is None:
            pid = np.full(self.T, -1)
            for k in range(self.K):
                pid[self.starts[k]:self.ends[k]] = k
            self._pid = pid
        return self._pid

    def pmask(self, a, b):
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        return np.asarray((self.pstart >= a) & (self.pstart <= b))

    def dmask(self, pm):
        pid = self.pid()
        return (pid >= 0) & pm[np.maximum(pid, 0)]

    def window_bounds(self, windows):
        out = []
        dv = self.dates.values
        for lab, a, b in windows:
            ia = int(np.searchsorted(dv, np.datetime64(a), side='right') - 1)
            ib = int(np.searchsorted(dv, np.datetime64(b), side='right') - 1)
            out.append((lab, ia, ib))
        return out


# ----------------------------------------------------------------------------------------------
# Weights
# ----------------------------------------------------------------------------------------------
def cap_weights(base, cap=0.05):
    """Normalise base (>0) to sum 1, cap every weight at `cap`, redistribute the excess pro rata to the
    uncapped names (by their base weights) until no weight exceeds the cap."""
    base = np.asarray(base, np.float64)
    w = base / base.sum()
    n = len(w)
    if n * cap < 1.0 - 1e-12:          # fewer than 1/cap names: the cap cannot be met; equal weights are the
        return np.full(n, 1.0 / n)     # closest feasible allocation (used only when a filter leaves < 20 names)
    capped = np.zeros(n, bool)
    for _ in range(n + 1):
        free = ~capped
        room = 1.0 - cap * capped.sum()
        w = np.where(capped, cap, base * room / base[free].sum())
        new = free & (w > cap + 1e-15)
        if not new.any():
            break
        capped |= new
    return w


def weights(members, rule, mcap_row):
    n = len(members)
    if rule == 'EW':
        return np.full(n, 1.0 / n)
    m = mcap_row[members].astype(np.float64)
    if rule == 'VW':
        return m / m.sum()
    if rule == 'VWcap5':
        return cap_weights(m, 0.05)
    raise ValueError(rule)


# ----------------------------------------------------------------------------------------------
# Book runner: many books in one pass over the monthly periods (round-1 mechanics)
# ----------------------------------------------------------------------------------------------
def run_books(P, specs, progress=None):
    """specs: list of (name, fn) with fn(k) -> (members int array, weights array summing to 1).
    Returns dict name -> dict(daily=gross daily returns (T, NaN outside the sample), to=turnover per
    rebalance (K), nmem=(K)), using kr_03_portfolios.Book unchanged."""
    T, N, K = P.T, P.N, P.K
    out = {nm: dict(daily=np.full(T, np.nan), to=np.full(K, np.nan), nmem=np.zeros(K, np.int32),
                    nstuck=np.zeros(K, np.int32)) for nm, _ in specs}
    books = {nm: Book(N) for nm, _ in specs}
    for k in range(K):
        t = P.fidx[k]
        te = P.fidx[k + 1] if k + 1 < K else T - 1
        Rb = np.nan_to_num(P.R[t + 1:te + 1].astype(np.float64), nan=0.0)
        A = np.cumprod(P.E[t + 1:te + 1], axis=0).astype(bool)
        G = np.cumprod(1.0 + Rb * A, axis=0)
        E_t, TR_t = P.E[t], P.TR[t]
        for nm, fn in specs:
            m, w = fn(k)
            if len(m) == 0:
                continue
            o = out[nm]
            o['to'][k], o['nstuck'][k] = books[nm].rebalance(np.asarray(m), np.asarray(w), E_t, TR_t)
            o['daily'][t + 1:te + 1] = books[nm].hold(G)
            o['nmem'][k] = len(m)
        if progress and k % progress == 0:
            log(f'  period {k}/{K} {P.dates[t].date()}')
    return out


def save_books(path, P, books):
    names = list(books)
    np.savez_compressed(path, names=np.array(names), daily=np.vstack([books[n]['daily'] for n in names]),
                        to=np.vstack([books[n]['to'] for n in names]),
                        nmem=np.vstack([books[n]['nmem'] for n in names]))


def load_books(path):
    z = np.load(path)
    names = list(z['names'])
    return {n: dict(daily=z['daily'][i], to=z['to'][i], nmem=z['nmem'][i]) for i, n in enumerate(names)}


# ----------------------------------------------------------------------------------------------
# Series construction (round-1 kr_04 semantics, generalised to a costed benchmark)
# ----------------------------------------------------------------------------------------------
def series(P, L, S=None, B=None, c=0.0, cb=0.0):
    """Per-period and daily returns of a self-financing combination built period by period:
         C_d = 1 + (V_L,d - 1 - c*TO_L) - [(V_S,d - 1) + c*TO_S if S] - [(V_B,d - 1 - cb*TO_B) if B]
    LO: S = B = None -> C_d = V_L,d - c*TO_L.  LS: $1 long, $1 short, both legs pay c (the short leg's
    trading cost reduces C, exactly as round-1's C = 1 - c*(TO_L+TO_S) + V_L - V_S).
    Excess vs benchmark B: the benchmark pays cb (cb = 0 -> gross benchmark, the round-1 convention).
    Daily return = C_d / C_{d-1} - 1 (C_0 = 1) so daily returns compound exactly to the period return.
    L, S, B are book dicts (daily, to)."""
    rl = np.nan_to_num(L['daily'], nan=0.0); tl = np.nan_to_num(L['to'], nan=0.0)
    if S is not None:
        rs = np.nan_to_num(S['daily'], nan=0.0); ts = np.nan_to_num(S['to'], nan=0.0)
    if B is not None:
        rb = np.nan_to_num(B['daily'], nan=0.0); tb = np.nan_to_num(B['to'], nan=0.0)
    daily = np.full(P.T, np.nan)
    per = np.full(P.K, np.nan)
    to = tl.copy()
    if S is not None:
        to = to + ts
    for k in range(P.K):
        s, e = P.starts[k], P.ends[k]
        C = np.cumprod(1.0 + rl[s:e]) - c * tl[k]
        if S is not None:
            C = C - (np.cumprod(1.0 + rs[s:e]) - 1.0) - c * ts[k]
        if B is not None:
            C = C - (np.cumprod(1.0 + rb[s:e]) - 1.0 - cb * tb[k])
        prev = np.concatenate(([1.0], C[:-1]))
        daily[s:e] = C / prev - 1.0
        per[k] = C[-1] - 1.0
    return per, daily, to


def diff_series(P, X, Y, c):
    """Filtered minus unfiltered, both net of their own costs at c per side (paired, same days)."""
    return series(P, X, B=Y, c=c, cb=c)


# ----------------------------------------------------------------------------------------------
# Statistics
# ----------------------------------------------------------------------------------------------
def stats(P, per, daily, to=None, pm=None, full=True):
    pm = np.ones(P.K, bool) if pm is None else pm
    p = per[pm]
    p = p[np.isfinite(p)]
    out = {'n_periods': len(p)}
    if len(p) < 3:
        return out
    mu, sd = p.mean(), p.std(ddof=1)
    out['mean_monthly'] = mu
    out['ann_mean'] = mu * ANN
    out['ann_vol'] = sd * np.sqrt(ANN)
    out['sharpe'] = mu / sd * np.sqrt(ANN) if sd > 0 else np.nan
    out['nw_t'] = nw_tstat(p, NW_LAGS)
    dm = P.dmask(pm)
    d = daily[dm]
    d = d[np.isfinite(d)]
    tr = float(np.prod(1.0 + d) - 1.0)
    out['total_return'] = tr
    out['cagr'] = (1.0 + tr) ** (ANN / len(p)) - 1.0 if tr > -1 else -1.0
    out['max_dd'] = max_drawdown(d)
    if to is not None:
        out['turnover_per_year'] = float(np.nanmean(to[pm]) * ANN)
    out['hit_rate'] = float((p > 0).mean())
    if full:
        dd = pd.Series(daily[dm], index=P.dates[dm]).dropna()
        yr = (1.0 + dd).groupby(dd.index.year).prod() - 1.0
        cnt = dd.groupby(dd.index.year).size()
        yr = yr[cnt >= 60]
        out['pct_pos_years'] = float((yr > 0).mean()) if len(yr) else np.nan
        out['n_years'] = int(len(yr))
    return out


def window_returns(P, daily, windows):
    out = {}
    for lab, ia, ib in P.window_bounds(windows):
        seg = daily[ia + 1:ib + 1]
        out[lab] = float(np.prod(1.0 + seg) - 1.0) if len(seg) and np.isfinite(seg).all() else np.nan
    return out


def year_returns(P, daily, min_days=60):
    dd = pd.Series(daily, index=P.dates).dropna()
    yr = (1.0 + dd).groupby(dd.index.year).prod() - 1.0
    cnt = dd.groupby(dd.index.year).size()
    return yr[cnt >= min_days]


# ----------------------------------------------------------------------------------------------
# Paired circular block bootstrap, deflated Sharpe, CSCV PBO
# ----------------------------------------------------------------------------------------------
_BOOT_IDX = {}


def boot_index(n, block=BOOT_BLOCK, B=BOOT_B, seed=SEED):
    """Circular block bootstrap index matrix (B x n); identical for every series of length n
    (common random numbers, so paired comparisons across filters use the same resamples)."""
    key = (n, block, B, seed)
    if key not in _BOOT_IDX:
        rng = np.random.default_rng(seed)
        nb = int(math.ceil(n / block))
        st = rng.integers(0, n, size=(B, nb)).astype(np.int32)
        idx = (st[:, :, None] + np.arange(block, dtype=np.int32)[None, None, :]) % n
        _BOOT_IDX[key] = np.ascontiguousarray(idx.reshape(B, nb * block)[:, :n])
    return _BOOT_IDX[key]


def boot_pvalue(x, block=BOOT_BLOCK, B=BOOT_B, seed=SEED):
    """One-sided p-value for H0: mean <= 0 vs H1: mean > 0 from a circular block bootstrap of x.
    p_null  = (1 + #{mean*_b - mean >= mean}) / (B + 1)   (bootstrap distribution re-centred under H0)
    p_perc  = (1 + #{mean*_b <= 0}) / (B + 1)              (percentile version)
    Also returns the 90% percentile interval of the mean."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    idx = boot_index(n, block, B, seed)
    mb = x[idx].mean(axis=1)
    mu = x.mean()
    p_null = (1 + np.sum(mb - mu >= mu)) / (B + 1)
    p_perc = (1 + np.sum(mb <= 0)) / (B + 1)
    lo, hi = np.quantile(mb, [0.05, 0.95])
    return dict(p_null=float(p_null), p_perc=float(p_perc), ci90_lo=float(lo), ci90_hi=float(hi))


def boot_sharpe_ci(x, block=10, B=BOOT_B, seed=SEED, ann=ANN):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    idx = boot_index(len(x), block, B, seed)
    xb = x[idx]
    sr = xb.mean(1) / xb.std(1, ddof=1) * np.sqrt(ann)
    return np.quantile(sr, [0.05, 0.95])


def lo_sharpe_se(x, ann=ANN):
    """Lo (2002): iid standard error of the per-period Sharpe ratio, sqrt((1 + SR^2/2)/T), annualised with
    Lo's serial-correlation factor eta(q) = q / sqrt(q + 2 sum_{k=1}^{q-1} (q-k) rho_k), q = periods per
    year. Returns (SR_ann, SE_ann, eta)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    sr = x.mean() / x.std(ddof=1)
    se = math.sqrt((1 + 0.5 * sr ** 2) / n)
    q = int(ann)
    rho = [np.corrcoef(x[l:], x[:-l])[0, 1] for l in range(1, q)]
    den = q + 2 * sum((q - l) * r for l, r in zip(range(1, q), rho))
    eta = q / math.sqrt(den) if den > 0 else math.sqrt(q)
    return sr * eta, se * eta, eta


def deflated_sharpe(x, n_trials, var_trials_sr):
    """Bailey & Lopez de Prado (2014). x: per-period returns of the selected strategy; SRs per period.
    var_trials_sr: variance of the per-period SRs across the trials. Returns (DSR prob, SR0, SR)."""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    T = len(x)
    sr = x.mean() / x.std(ddof=1)
    g3 = float(pd.Series(x).skew())
    g4 = float(pd.Series(x).kurt()) + 3.0
    emc = 0.5772156649015329
    N = max(int(n_trials), 2)
    sr0 = math.sqrt(max(var_trials_sr, 0.0)) * ((1 - emc) * norm.ppf(1 - 1.0 / N) + emc * norm.ppf(1 - 1.0 / (N * math.e)))
    den = math.sqrt(max(1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2, 1e-12))
    z = (sr - sr0) * math.sqrt(T - 1) / den
    return float(norm.cdf(z)), float(sr0), float(sr)


def pbo_cscv(M, S=16, metric='sharpe'):
    """Probability of backtest overfitting (Bailey, Borwein, Lopez de Prado, Zhu 2017) via CSCV.
    M: (T x N) per-period returns of N candidate configurations. Returns dict(pbo, n_combos,
    median_logit, share_is_winner_oos_below_median, mean_oos_rank)."""
    M = np.asarray(M, float)
    T, N = M.shape
    rows = (T // S) * S
    M = M[:rows]
    blocks = np.array_split(np.arange(rows), S)
    bs = np.array([M[b].sum(0) for b in blocks])            # block sums
    bss = np.array([(M[b] ** 2).sum(0) for b in blocks])    # block sums of squares
    bn = np.array([len(b) for b in blocks])
    logits = []
    oos_ranks = []
    loses = []
    for comb in itertools.combinations(range(S), S // 2):
        ins = np.zeros(S, bool); ins[list(comb)] = True
        def perf(mask):
            n = bn[mask].sum(); s = bs[mask].sum(0); ss = bss[mask].sum(0)
            mu = s / n
            if metric == 'mean':
                return mu
            var = (ss - n * mu ** 2) / (n - 1)
            return mu / np.sqrt(np.maximum(var, 1e-18))
        pi, po = perf(ins), perf(~ins)
        best = int(np.argmax(pi))
        n_o = bn[~ins].sum()
        loses.append(bs[~ins].sum(0)[best] / n_o < 0)          # in-sample winner loses money out of sample
        rk = rankdata(po)[best]                              # 1 = worst, N = best
        w = rk / (N + 1.0)
        logits.append(math.log(w / (1 - w)))
        oos_ranks.append(rk)
    logits = np.array(logits)
    return dict(pbo=float((logits <= 0).mean()), n_combos=len(logits), median_logit=float(np.median(logits)),
                mean_oos_rank=float(np.mean(oos_ranks)), n_strategies=N, winner_loses_share=float(np.mean(loses)))


def to_csv(df, name):
    path = f'{RES2}/{name}'
    df.to_csv(path, index=False, float_format='%.6g')
    return path
