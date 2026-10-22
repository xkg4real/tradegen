"""r2_idx_common.py -- shared loaders, rule builders, costed engine and protective-class checks.

QUANTGEN round-2 index and governance lab. Every r2_idx_*.py script imports this module.

Conventions (QUANTGEN rule 2 and macro spec v1.2 section 4.1 / 9.3):
  * A weight w_t is decided at the close of t from prices through t and earns r_{t+1}.
  * Cost = c * |w_t - w_{t-1}| per side, charged on the day the new weight earns; the initial entry is
    not charged; buy-and-hold and the static comparator S carry no cost (spec section 9.3, R4b).
  * Cash earns 0%. Returns are price returns (rebuilt KOSPI price index; SPY unadjusted closes).
  * Sharpe = mean / sd(ddof=1) * sqrt(252) on daily returns (spec: annualisation_days 252).
  * Max drawdown on the compounded NAV, the starting capital counting as the first peak.
  * SMA20 realised vol = rolling 20-session stdev (ddof=1) * sqrt(252); this reproduces the spec's R4
    state rows (KOSPI weight earning on 2026-06-22 = 0.3025 vs R4 0.3024).

Protective class (spec section 8.7), declared here before any result was computed:
  S = buy-and-hold x the rule's average held exposure (constant, same days, no cost). With 0% cash,
      Sharpe(S) == Sharpe(buy-and-hold), so PC-3's dSR vs S equals dSR vs buy-and-hold.
  PC-1 MDD(rule) - MDD(S) >= +3.0 pp at 1x and 2x costs, and MDD(rule) better than MDD(buy-and-hold).
  PC-2 mean held exposure on the worst 5% of buy-and-hold days / mean exposure on all days <= 0.90.
  PC-3 one-sided bootstrap p of {dSR* <= -0.10} <= 0.10; circular block bootstrap, block =
       max(10, PW_circ(d), PW_circ(d^2)) with d = r_rule(1x) - r_S, 2,000 resamples, seed 11
       (arch CircularBlockBootstrap indices); point estimate dSR >= -0.10 also at 2x.
  PC-4 >= 3 drawdown episodes with benefit (rule minus S episode return) > 0 and the largest benefit
       <= 50% of the summed positive benefit.
  PC-5 >= 60% of calendar years positive (years with >= 126 sessions in the window).
  PC-6 >= 50% of the declared neighbours keep >= half the centre's PC-1 improvement and dSR >= -0.10.
  PC-7 >= 882 sessions; >= 5 drawdown episodes in the sample; two-state (binary) rules also need
       >= 30 de-clustered de-risk onsets (an onset within the rule's own lookback of the previous onset
       is the same onset; chain merging).
"""
import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import io
import json
import math
import time
import hashlib
import zipfile

import numpy as np
import pandas as pd

ROOT = '/home/claude/datalab'
OUT = f'{ROOT}/r2/idx'
RES = f'{OUT}/results'
CHT = f'{OUT}/charts'
SUMMARY = f'{ROOT}/r2/R2_IDX_summary.md'
KOSPI_PARQUET = f'{ROOT}/kr/cache/kospi_rebuilt.parquet'
SPY_ZIP = '/home/claude/data_raw/us/spy_lean_daily.zip'
SHILLER_CSV = '/home/claude/data_raw/us/shiller_sp500_monthly.csv'
for _d in (RES, CHT):
    os.makedirs(_d, exist_ok=True)

SEED = 11            # QUANTGEN study seed (all bootstrap tests)
REPS = 2000          # gate resamples
ANN = 252
DELTA_NI = 0.10      # PC-3 non-inferiority margin
TAIL_Q = 0.05
MIN_YEAR_SESSIONS = 126

T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:7.1f}s]', *a, flush=True)


# ---------------------------------------------------------------------------------------------- data
class Market:
    def __init__(self, name, dates, p, r, cfg):
        self.name, self.dates, self.p, self.r, self.cfg = name, pd.DatetimeIndex(dates), np.asarray(p, float), \
            np.asarray(r, float), cfg
        self.i0 = int(np.searchsorted(self.dates.values, np.datetime64(cfg['start'])))
        self.i1 = int(np.searchsorted(self.dates.values, np.datetime64(cfg['end']), side='right') - 1)
        self._wcache = {}

    @property
    def ev_dates(self):
        return self.dates[self.i0:self.i1 + 1]

    @property
    def r_ev(self):
        return self.r[self.i0:self.i1 + 1]

    def idx_on_or_before(self, d):
        return int(np.searchsorted(self.dates.values, np.datetime64(d), side='right') - 1)

    def idx_on_or_after(self, d):
        return int(np.searchsorted(self.dates.values, np.datetime64(d), side='left'))


MARKET_CFG = {
    'KOSPI': dict(start='1996-09-02', end='2026-09-29', vt_target=0.20,
                  books={'KRX ETF 3bp': (0.0003, 0.0006)},
                  primary_book='KRX ETF 3bp'),
    'SPY': dict(start='1999-05-03', end='2021-03-31', vt_target=0.15,
                books={'US via KIS 50bp': (0.0050, 0.0100), 'Futures 5bp': (0.0005, 0.0010)},
                primary_book='US via KIS 50bp'),
}


def load_kospi(cfg=None):
    k = pd.read_parquet(KOSPI_PARQUET)
    p = k['level'].astype(float).values
    r = k['ret'].astype(float).values.copy()
    r[0] = np.nan
    return Market('KOSPI', k.index, p, r, cfg or MARKET_CFG['KOSPI'])


def load_spy_daily():
    with zipfile.ZipFile(SPY_ZIP) as z:
        raw = z.read('spy.csv')
    df = pd.read_csv(io.BytesIO(raw), header=None, names=['dt', 'o', 'h', 'l', 'c', 'v'])
    assert (df['dt'].str[8:] == ' 00:00').all()
    idx = pd.to_datetime(df['dt'].str[:8], format='%Y%m%d')
    s = pd.Series(df['c'].values / 1e4, index=idx, name='close')
    assert s.index.is_monotonic_increasing and s.index.is_unique
    return s


def load_spy(cfg=None):
    s = load_spy_daily()
    p = s.values
    r = np.r_[np.nan, p[1:] / p[:-1] - 1.0]
    return Market('SPY', s.index, p, r, cfg or MARKET_CFG['SPY'])


def load_sp500_arch():
    import arch.data.sp500 as sp
    d = sp.load()
    s = d['Adj Close'].astype(float)
    s.index = pd.DatetimeIndex(s.index).as_unit('ns')
    return s


def load_market(name):
    return load_kospi() if name == 'KOSPI' else load_spy()


# ---------------------------------------------------------------------------------------------- rules
def freeze(spec):
    """Hashable key for a (possibly nested) spec dict."""
    if isinstance(spec, dict):
        return tuple(sorted((k, freeze(v)) for k, v in spec.items()))
    if isinstance(spec, (list, tuple)):
        return tuple(freeze(v) for v in spec)
    return spec


def spec_label(spec):
    k = spec['kind']
    if k == 'bh':
        return 'buy-and-hold'
    if k == 'sma':
        return f"SMA{spec['n']}" + (f" band{spec['band']:.0%}" if spec.get('band', 0) else '')
    if k == 'ens':
        lb = '/'.join(str(int(round(x * spec.get('scale', 1.0)))) for x in spec['lbs'])
        m = {'share': 'vote share', 'binary2': '>=2/4 long/flat'}[spec.get('map', 'share')]
        return f'ens {lb} {m}'
    if k == 'tsm_m':
        return f"{spec['months']}M sign (monthly)"
    if k == 'tsm_d':
        return f"{spec['days']}d sign (daily)"
    if k == 'vt':
        return f"VT{int(round(spec['target'] * 100))} w{spec['window']}"
    if k == 'ewma_vt':
        return f"EWMA({spec['lam']}) VT{int(round(spec['target'] * 100))}"
    if k == 'prod':
        return f"{spec_label(spec['a'])} x {spec_label(spec['b'])}"
    if k == 'ovl':
        return f"overlay[{spec['how']}]({spec_label(spec['base'])})"
    raise ValueError(k)


def _lagged(p, L):
    out = np.full(len(p), np.nan)
    out[L:] = p[:-L]
    return out


def _sma(p, n):
    return pd.Series(p).rolling(n, min_periods=n).mean().values


def _state_machine(enter, exit_, valid):
    pos = np.full(len(enter), np.nan)
    cur = None
    for t in range(len(enter)):
        if not valid[t]:
            continue
        if cur is None:
            cur = 1.0 if enter[t] else 0.0
        elif cur == 0.0 and enter[t]:
            cur = 1.0
        elif cur == 1.0 and exit_[t]:
            cur = 0.0
        pos[t] = cur
    return pos


def _monthly_sign(dates, p, months):
    s = pd.Series(p, index=dates)
    g = s.groupby([dates.year, dates.month])
    me = g.tail(1)                                   # last session of each month (calendar known ex ante)
    prev = me.shift(months)
    sig = ((me / prev - 1.0) > 0).astype(float).where(prev.notna())
    pos = pd.Series(np.nan, index=dates)
    pos.loc[me.index] = sig.values
    return pos.ffill().values                       # held from the next session until the next month end


def _realised_vol(r, window, ddof=1):
    return pd.Series(r).rolling(window, min_periods=window).std(ddof=ddof).values * np.sqrt(ANN)


def build_weight(spec, mk):
    """Weight decided at the close of each session (NaN while undefined). Uses prices/returns <= t only."""
    key = freeze(spec)
    if key in mk._wcache:
        return mk._wcache[key]
    p, r, k = mk.p, mk.r, spec['kind']
    with np.errstate(invalid='ignore', divide='ignore'):
        if k == 'bh':
            w = np.ones(len(p))
        elif k == 'sma':
            m = _sma(p, spec['n'])
            b = spec.get('band', 0.0)
            valid = np.isfinite(m)
            if b == 0:
                w = np.where(valid, (p > m).astype(float), np.nan)
            else:
                w = _state_machine(p > m * (1 + b), p < m * (1 - b), valid)
        elif k == 'ens':
            sc = spec.get('scale', 1.0)
            votes = []
            for L in spec['lbs']:
                Ls = int(round(L * sc))
                prev = _lagged(p, Ls)
                votes.append(np.where(np.isfinite(prev), (p / prev - 1.0 > 0).astype(float), np.nan))
            V = np.vstack(votes)
            share = V.mean(0)                     # NaN until every lookback is available
            mp = spec.get('map', 'share')
            if mp == 'share':
                w = share
            elif mp == 'binary2':
                w = np.where(np.isfinite(share), (V.sum(0) >= 2).astype(float), np.nan)
            else:
                raise ValueError(mp)
        elif k == 'tsm_m':
            w = _monthly_sign(mk.dates, p, spec['months'])
        elif k == 'tsm_d':
            prev = _lagged(p, spec['days'])
            w = np.where(np.isfinite(prev), (p / prev - 1.0 > 0).astype(float), np.nan)
        elif k == 'vt':
            sig = _realised_vol(r, spec['window'])
            w = np.minimum(spec.get('cap', 1.0), spec['target'] / sig)
        elif k == 'ewma_vt':
            lam = spec['lam']
            r2 = pd.Series(np.nan_to_num(r) ** 2)
            v = r2.ewm(alpha=1 - lam, adjust=False).mean().to_numpy(copy=True)
            v[:21] = np.nan                       # 20-return warm-up as for SMA20
            w = np.minimum(spec.get('cap', 1.0), spec['target'] / (np.sqrt(v) * np.sqrt(ANN)))
        elif k == 'prod':
            w = build_weight(spec['a'], mk) * build_weight(spec['b'], mk)
        elif k == 'ovl':
            b = build_weight(spec['base'], mk)
            if spec['how'] == 'clip':
                w = np.clip(b, 0.5, 1.0)
            elif spec['how'] == 'lin':
                w = 0.5 + 0.5 * b
            else:
                raise ValueError(spec['how'])
        else:
            raise ValueError(k)
    w = np.asarray(w, float)
    assert np.nanmax(w) <= 1.0 + 1e-12 and np.nanmin(w) >= -1e-12, (spec, np.nanmin(w), np.nanmax(w))
    mk._wcache[key] = w
    return w


def run_book(w, r, i0, i1, c):
    """Held weight on day t is the weight decided at the close of t-1; cost charged on day t."""
    h = np.asarray(w[i0 - 1:i1], float)
    assert np.isfinite(h).all(), 'weight undefined inside the evaluation window'
    rr = np.asarray(r[i0:i1 + 1], float)
    assert np.isfinite(rr).all()
    net = h * rr
    if c:
        net[1:] -= c * np.abs(np.diff(h))        # initial entry not charged (spec 9.3)
    return net, h


def book(mk, spec, c, i0=None, i1=None):
    w = build_weight(spec, mk)
    return run_book(w, mk.r, mk.i0 if i0 is None else i0, mk.i1 if i1 is None else i1, c)


# ---------------------------------------------------------------------------------------------- metrics
def sharpe(x):
    x = np.asarray(x, float)
    sd = x.std(ddof=1)
    return float(x.mean() / sd * np.sqrt(ANN)) if sd > 0 else np.nan


def mdd(x):
    w = np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(x, float))])
    return float((w / np.maximum.accumulate(w) - 1.0).min())


def cum(x):
    return float(np.prod(1.0 + np.asarray(x, float)) - 1.0)


def years_of(dates):
    return (dates[-1] - dates[0]).days / 365.25 + 1.0 / 365.25


def cagr(x, dates):
    return float((1.0 + cum(x)) ** (1.0 / years_of(dates)) - 1.0)


def cvar(x, q=0.05):
    x = np.sort(np.asarray(x, float))
    k = max(1, int(math.ceil(q * len(x))))
    return float(x[:k].mean())


def tail_ratio(h, r_bh, q=TAIL_Q):
    k = int(math.ceil(q * len(r_bh)))
    worst = np.argsort(r_bh, kind='stable')[:k]
    return float(h[worst].mean() / h.mean())


def year_table(x, dates, min_sessions=MIN_YEAR_SESSIONS):
    s = pd.Series(np.log1p(x), index=dates)
    g = s.groupby(dates.year)
    n = g.size()
    yr = np.expm1(g.sum())
    return yr[n >= min_sessions], n


def psr(x, sr0_ann=0.0):
    """Probabilistic Sharpe ratio (Bailey-Lopez de Prado) with skew/kurtosis, daily data."""
    from scipy.stats import norm, skew, kurtosis
    x = np.asarray(x, float)
    T = len(x)
    srd = x.mean() / x.std(ddof=1)
    g3 = skew(x)
    g4 = kurtosis(x, fisher=False)
    sr0 = sr0_ann / np.sqrt(ANN)
    den = np.sqrt(max(1e-12, 1 - g3 * srd + (g4 - 1) / 4.0 * srd ** 2))
    return float(norm.cdf((srd - sr0) * np.sqrt(T - 1) / den))


def turnover_per_year(h, dates):
    return float(np.abs(np.diff(h)).sum() / years_of(dates))


# ---------------------------------------------------------------------------------------------- bootstrap
def pw_block(x):
    from arch.bootstrap import optimal_block_length
    v = optimal_block_length(np.asarray(x, float))
    return float(v['circular'].iloc[0])


def boot_sharpes(X, block, reps=REPS, seed=SEED):
    """Circular block bootstrap (arch indices, given seed) of the annualised Sharpe of each column of X.

    X is (n, k); the same resampled days are used for every column (paired bootstrap)."""
    from arch.bootstrap import CircularBlockBootstrap
    X = np.asarray(X, float)
    n, k = X.shape
    bs = CircularBlockBootstrap(int(block), np.arange(n), seed=seed)
    out = np.empty((reps, k))
    for i, (pa, _) in enumerate(bs.bootstrap(reps)):
        xi = X[pa[0]]
        out[i] = xi.mean(0) / xi.std(0, ddof=1) * np.sqrt(ANN)
    return out


# ---------------------------------------------------------------------------------------------- episodes
# Spec section 8.6 drawdown episodes (PC-4): (label, start, end, include_start_return, markets).
# include_start=False: returns dated after the start close through the end close (last close on or
# before each date). The four KOSPI windows that R4/R4b computed with the start-date return included
# (spec v1.2 note) carry include_start=True for KOSPI only.
SPEC_EPISODES = [
    ('GFC', '2008-09-01', '2009-03-09', {'KOSPI': False, 'SPY': False}),
    ('2011', '2011-07-22', '2011-10-03', {'KOSPI': False, 'SPY': False}),
    ('2015-16', '2015-08-10', '2016-02-11', {'KOSPI': False, 'SPY': False}),
    ('2018Q4', '2018-09-20', '2018-12-24', {'KOSPI': False, 'SPY': False}),
    ('2020 crash', {'KOSPI': '2020-02-19', 'SPY': '2020-02-19'}, {'KOSPI': '2020-03-19', 'SPY': '2020-03-23'},
     {'KOSPI': False, 'SPY': False}),
    ('2022', '2022-01-03', {'KOSPI': '2022-09-30', 'SPY': '2022-10-12'}, {'KOSPI': False, 'SPY': False}),
    ('Aug-2024', {'KOSPI': '2024-07-31', 'SPY': '2024-07-16'}, {'KOSPI': '2024-08-09', 'SPY': '2024-08-05'},
     {'KOSPI': True, 'SPY': False}),
    ('Dec-2024', '2024-12-03', '2024-12-09', {'KOSPI': False}),
    ('Apr-2025', {'KOSPI': '2025-03-28', 'SPY': '2025-02-19'}, {'KOSPI': '2025-04-09', 'SPY': '2025-04-08'},
     {'KOSPI': True, 'SPY': False}),
    ('Mar-2026', '2026-02-27', '2026-03-31', {'KOSPI': True, 'SPY': False}),
    ('Jul-2026', '2026-06-22', '2026-07-30', {'KOSPI': False, 'SPY': False}),
    ('Sep-2026', '2026-08-31', '2026-09-30', {'SPY': False}),     # declared US-only (as R4b); KOSPI info row
]
# Spec section 8.6 cost (non-drawdown) episodes, reported for information.
SPEC_COST_EPISODES = [
    ('2009 rebound', '2009-03-09', '2009-06-30', {'KOSPI': False, 'SPY': False}),
    ('2020 rebound', {'KOSPI': '2020-03-19', 'SPY': '2020-03-23'}, '2020-06-08', {'KOSPI': False, 'SPY': False}),
    ('H1-2026 bull', '2026-01-02', '2026-06-30', {'KOSPI': True}),
]


def _pick(v, market):
    return v[market] if isinstance(v, dict) else v


def window_slice(mk, start, end, include_start):
    """Index range [a, b] (inclusive) of the RETURN dates of a window."""
    if include_start:
        a = mk.idx_on_or_after(start)
    else:
        a = mk.idx_on_or_before(start) + 1
    b = mk.idx_on_or_before(end)
    return a, b


def kospi_peak_trough(mk, y_peak, y_end):
    p = pd.Series(mk.p, index=mk.dates)
    a = p[str(y_peak)]
    pk = a.idxmax()
    b = p[pk:f'{y_end}-12-31']
    tr = b.idxmin()
    return str(pk.date()), str(tr.date())


def drawdown_episodes(mk, info=False, truncate=False):
    """PC-4 episode list for the market: (label, a, b) index ranges inside the evaluation window.

    truncate=True clips a window that straddles the sample start to the first return of the sample
    (the spec's 2015-16 window becomes 2016-01-04 -> 2016-02-11 in a 2016-26 KOSPI sample)."""
    raw = []
    if mk.name == 'KOSPI':
        for lab, y0, y1 in (('1997-98', 1997, 1998), ('2000-01', 2000, 2001)):
            s, e = kospi_peak_trough(mk, y0, y1)
            a, b = window_slice(mk, s, e, False)
            raw.append((f'{lab} ({s}..{e})', a, b))
    for lab, s, e, inc in SPEC_EPISODES:
        if mk.name not in inc:
            if info and mk.name == 'KOSPI' and lab == 'Sep-2026':
                a, b = window_slice(mk, _pick(s, 'SPY'), _pick(e, 'SPY'), False)
                raw.append((lab + ' (info only, not in PC-4 set)', a, b))
            continue
        a, b = window_slice(mk, _pick(s, mk.name), _pick(e, mk.name), inc[mk.name])
        raw.append((lab, a, b))
    eps = []
    for lab, a, b in raw:
        if truncate and a < mk.i0 <= b:
            a = mk.i0
            lab = lab + ' (truncated)'
        if a < mk.i0 or b > mk.i1 or b <= a:
            continue                               # dates do not cover the sample
        eps.append((lab, a, b))
    return eps


def cost_episodes(mk):
    out = []
    for lab, s, e, inc in SPEC_COST_EPISODES:
        if mk.name not in inc:
            continue
        a, b = window_slice(mk, _pick(s, mk.name), _pick(e, mk.name), inc[mk.name])
        if a < mk.i0 or b > mk.i1 or b <= a:
            continue
        out.append((lab, a, b))
    return out


def underwater_episodes(mk, threshold=-0.20):
    """E3-style episodes: under-water spells of buy-and-hold (peak -> recovery) with depth <= threshold;
    the window runs from the peak close to the trough close."""
    p = mk.p[mk.i0 - 1:mk.i1 + 1]                 # include the close before the first return
    out = []
    peak_i = 0
    i = 1
    n = len(p)
    while i < n:
        if p[i] >= p[peak_i]:
            peak_i = i
            i += 1
            continue
        j = i
        while j < n and p[j] < p[peak_i]:
            j += 1
        seg = p[peak_i:j]
        tr = peak_i + int(np.argmin(seg))
        depth = p[tr] / p[peak_i] - 1
        if depth <= threshold:
            a = mk.i0 - 1 + peak_i + 1             # first return after the peak close
            b = mk.i0 - 1 + tr
            out.append((f'{mk.dates[mk.i0 - 1 + peak_i].date()}..{mk.dates[b].date()}', a, b, depth))
        peak_i = j if j < n else peak_i
        i = j + 1 if j < n else n
    return out


def declustered_onsets(h, gap):
    """De-risk onsets of a two-state weight path (1 -> 0), chain-merged within `gap` sessions."""
    h = np.asarray(h, float)
    on = np.where((h[:-1] >= 0.5) & (h[1:] < 0.5))[0] + 1
    if len(on) == 0:
        return 0, 0, 0
    chain = 1
    for k in range(1, len(on)):
        if on[k] - on[k - 1] > gap:
            chain += 1
    greedy, last = 1, on[0]
    for t in on[1:]:
        if t - last > gap:
            greedy += 1
            last = t
    return int(len(on)), int(chain), int(greedy)


# ---------------------------------------------------------------------------------------------- outputs
def save_csv(df, name):
    path = f'{RES}/{name}'
    df.to_csv(path, index=False, float_format='%.6g')
    return path


def clean_json(x):
    if isinstance(x, dict):
        return {str(k): clean_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean_json(v) for v in x]
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, np.ndarray):
        return clean_json(x.tolist())
    if isinstance(x, (pd.Timestamp,)):
        return str(x.date())
    return x


def save_json(obj, name):
    path = f'{CHT}/{name}'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(clean_json(obj), f, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return path


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------------------------- cards
def time_under_water(x, depth=0.10):
    """Share of days on which the NAV is at least `depth` below its running peak."""
    w = np.cumprod(1.0 + np.asarray(x, float))
    pk = np.maximum.accumulate(np.concatenate([[1.0], w]))[1:]
    return float((w / pk - 1.0 <= -depth).mean())


def episode_rows(mk, net, S, eps):
    i0 = mk.i0
    rows = []
    for lab, a, b in eps:
        sl = slice(a - i0, b - i0 + 1)
        rr, ss, bb = cum(net[sl]), cum(S[sl]), cum(mk.r[a:b + 1])
        rows.append(dict(episode=lab, start_return=str(mk.dates[a].date()), end_return=str(mk.dates[b].date()),
                         n_days=b - a + 1, rule_return=rr, S_return=ss, buy_hold_return=bb, benefit_vs_S=rr - ss))
    return rows


def protective_card(mk, spec, costs, neighbours=(), binary_gap=None, eps=None, reps=REPS, seed=SEED,
                    pc4_truncate=False, pc6_override=None):
    """All CARD-P checks (spec 8.7) plus the CARD-O gate lines for one rule / market / instrument book."""
    c1, c2 = costs
    net1, h = book(mk, spec, c1)
    net2, _ = book(mk, spec, c2)
    rbh = mk.r_ev
    dates = mk.ev_dates
    xbar = float(h.mean())
    S = xbar * rbh
    out = dict(market=mk.name, rule=spec_label(spec), start=str(dates[0].date()), end=str(dates[-1].date()),
               n_sessions=len(net1), cost_1x_bp=c1 * 1e4, cost_2x_bp=c2 * 1e4, avg_exposure=xbar,
               turnover_per_year=turnover_per_year(h, dates))
    out['cost_drag_1x_pct_yr'] = out['turnover_per_year'] * c1 * 100
    gross, _ = book(mk, spec, 0.0)
    for nm, x in (('rule_gross', gross), ('rule_1x', net1), ('rule_2x', net2), ('S', S), ('buy_hold', rbh)):
        out[f'sharpe_{nm}'] = sharpe(x)
        out[f'mdd_{nm}'] = mdd(x)
        out[f'cagr_{nm}'] = cagr(x, dates)
        out[f'vol_{nm}'] = float(np.std(x, ddof=1) * np.sqrt(ANN))
    out['cvar5_rule_1x'] = cvar(net1)
    out['cvar5_S'] = cvar(S)
    out['days_10pct_under_peak_rule_1x'] = time_under_water(net1)
    out['days_10pct_under_peak_S'] = time_under_water(S)
    # PC-1
    out['pc1_dmdd_pp_1x'] = (out['mdd_rule_1x'] - out['mdd_S']) * 100
    out['pc1_dmdd_pp_2x'] = (out['mdd_rule_2x'] - out['mdd_S']) * 100
    out['pc1_better_than_bh_1x'] = bool(out['mdd_rule_1x'] > out['mdd_buy_hold'])
    out['pc1_pass_1x'] = bool(out['pc1_dmdd_pp_1x'] >= 3.0 and out['pc1_better_than_bh_1x'])
    out['pc1_pass_2x'] = bool(out['pc1_dmdd_pp_2x'] >= 3.0 and out['mdd_rule_2x'] > out['mdd_buy_hold'])
    # PC-2
    out['pc2_tail_ratio'] = tail_ratio(h, rbh)
    out['pc2_pass'] = bool(out['pc2_tail_ratio'] <= 0.90)
    k20 = np.argsort(rbh, kind='stable')[:20]
    out['exposure_on_20_worst_days'] = float(h[k20].mean())
    # PC-3 (+ CARD-O step 2 / step 5 from the same paired bootstrap)
    out['dsr_vs_S_1x'] = out['sharpe_rule_1x'] - out['sharpe_S']
    out['dsr_vs_S_2x'] = out['sharpe_rule_2x'] - out['sharpe_S']
    d = net1 - S
    out['pw_d'] = pw_block(d)
    out['pw_d2'] = pw_block(d ** 2)
    blk = int(max(10, math.ceil(out['pw_d']), math.ceil(out['pw_d2'])))
    out['pc3_block'] = blk
    Bp = boot_sharpes(np.column_stack([net1, S]), blk, reps, seed)
    B10 = boot_sharpes(np.column_stack([net1, S]), 10, reps, seed)
    dp, d10 = Bp[:, 0] - Bp[:, 1], B10[:, 0] - B10[:, 1]
    out['pc3_p_ni'] = float((dp <= -DELTA_NI).mean())
    out['pc3_p_ni_block10'] = float((d10 <= -DELTA_NI).mean())
    out['pc3_dsr_ci90_lo'], out['pc3_dsr_ci90_hi'] = [float(v) for v in np.quantile(dp, [0.05, 0.95])]
    out['pc3_share_beats_S'] = float((dp > 0).mean())
    out['pc3_pass'] = bool(out['pc3_p_ni'] <= 0.10 and out['dsr_vs_S_1x'] >= -DELTA_NI)
    out['pc3_point_pass_2x'] = bool(out['dsr_vs_S_2x'] >= -DELTA_NI)
    out['o_step5_p_block10'] = float((d10 <= 0).mean())
    out['o_step5_p_blockpw'] = float((dp <= 0).mean())
    out['o_step5_pass'] = bool(out['o_step5_p_block10'] <= 0.10)
    lo, hi = np.quantile(B10[:, 0], [0.05, 0.95])
    out['o_step2_sr_ci90_lo'], out['o_step2_sr_ci90_hi'] = float(lo), float(hi)
    out['o_step2_pass'] = bool(lo > 0)
    out['o_step3_psr0'] = psr(net1, 0.0)
    out['o_step6_pass'] = bool(out['sharpe_rule_2x'] > 0)
    # PC-4
    eps = drawdown_episodes(mk, truncate=pc4_truncate) if eps is None else eps
    erows = episode_rows(mk, net1, S, eps)
    ben = np.array([e['benefit_vs_S'] for e in erows])
    pos = ben[ben > 0]
    out['pc4_n_episodes'] = len(ben)
    out['pc4_n_positive'] = int((ben > 0).sum())
    out['pc4_largest_share'] = float(pos.max() / pos.sum()) if len(pos) else np.nan
    out['pc4_largest_episode'] = erows[int(np.argmax(ben))]['episode'] if len(pos) else ''
    out['pc4_pass'] = bool(out['pc4_n_positive'] >= 3 and out['pc4_largest_share'] <= 0.5)
    # PC-5 (= gate step 8 for the CARD-O view)
    yr, _ = year_table(net1, dates)
    yS, _ = year_table(S, dates)
    out['pc5_n_years'] = int(len(yr))
    out['pc5_share_years_positive'] = float((yr > 0).mean())
    out['pc5_share_years_lagging_S'] = float((yr < yS).mean())
    out['pc5_pass'] = bool(out['pc5_share_years_positive'] >= 0.60)
    yb, _ = year_table(rbh, dates)
    out['bh_share_years_positive'] = float((yb > 0).mean())
    # PC-6
    nrows = []
    for nb in neighbours:
        n1, hn = book(mk, nb, c1)
        Sn = hn.mean() * rbh
        dm = (mdd(n1) - mdd(Sn)) * 100
        ds = sharpe(n1) - sharpe(Sn)
        keep = bool(dm >= 0.5 * out['pc1_dmdd_pp_1x'] and ds >= -DELTA_NI)
        nrows.append(dict(market=mk.name, centre=out['rule'], neighbour=spec_label(nb), avg_exposure=float(hn.mean()),
                          sharpe_1x=sharpe(n1), mdd_1x=mdd(n1), mdd_S=mdd(Sn), dmdd_pp_1x=dm, dsr_vs_S_1x=ds,
                          keeps=keep))
    out['pc6_n_neighbours'] = len(nrows)
    out['pc6_share_keep'] = float(np.mean([r['keeps'] for r in nrows])) if nrows else np.nan
    out['pc6_pass'] = bool(nrows and out['pc6_share_keep'] >= 0.5)
    out['pc6_evaluated'] = bool(nrows)
    if pc6_override is not None and np.isfinite(pc6_override):   # plateau taken from the primary-window run
        out['pc6_share_keep'] = float(pc6_override)
        out['pc6_pass'] = bool(pc6_override >= 0.5)
        out['pc6_evaluated'] = True
    # PC-7
    out['pc7_sessions_ok'] = bool(len(net1) >= 756 + 126)
    out['pc7_episodes_ok'] = bool(len(ben) >= 5)
    out['binary_rule'] = bool(binary_gap is not None)
    if binary_gap is not None:
        raw, chain, greedy = declustered_onsets(h, binary_gap)
        out['onsets_raw'], out['onsets_declustered'], out['onsets_declustered_greedy'] = raw, chain, greedy
        out['onset_gap_sessions'] = binary_gap
        out['pc7_onsets_ok'] = bool(chain >= 30)
    else:
        out['onsets_raw'] = out['onsets_declustered'] = out['onsets_declustered_greedy'] = np.nan
        out['onset_gap_sessions'] = np.nan
        out['pc7_onsets_ok'] = True
    out['pc7_pass'] = bool(out['pc7_sessions_ok'] and out['pc7_episodes_ok'] and out['pc7_onsets_ok'])
    out['verdict'], out['verdict_reasons'] = protective_verdict(out)
    v2, r2 = protective_verdict(out, waive_sufficiency=True)
    out['verdict_if_sufficient'], out['verdict_if_sufficient_reasons'] = v2, r2
    out['cardO_verdict'] = 'REJECT (step 5)' if not out['o_step5_pass'] else (
        'steps 2/5/6/8 pass' if (out['o_step2_pass'] and out['o_step6_pass'] and out['pc5_pass']) else
        'REVISE (step 2/6/8)')
    for e in erows:
        e.update(market=mk.name, rule=out['rule'], cost_1x_bp=c1 * 1e4)
    return out, erows, nrows, dict(net1=net1, net2=net2, h=h, S=S)


def protective_verdict(o, waive_sufficiency=False):
    """Spec 8.7 verdict order: sufficiency -> REJECT -> INSUFFICIENT (inconclusive) -> REVISE -> PASS."""
    if not waive_sufficiency and not o['pc7_pass']:
        why = []
        if not o['pc7_sessions_ok']:
            why.append('history < 882 sessions')
        if not o['pc7_episodes_ok']:
            why.append(f"{o['pc4_n_episodes']} drawdown episodes < 5")
        if not o['pc7_onsets_ok']:
            why.append(f"{o['onsets_declustered']} de-clustered onsets < 30 (Tier A)")
        return 'INSUFFICIENT DATA (sufficiency)', '; '.join(why)
    rej = []
    if not o['pc1_pass_1x']:
        rej.append(f"PC-1 at 1x (dMDD {o['pc1_dmdd_pp_1x']:+.1f} pp" +
                   ('' if o['pc1_better_than_bh_1x'] else '; not better than buy-and-hold') + ')')
    if not o['pc2_pass']:
        rej.append(f"PC-2 (tail ratio {o['pc2_tail_ratio']:.2f})")
    if o['dsr_vs_S_1x'] < -DELTA_NI:
        rej.append(f"PC-3 point (dSR {o['dsr_vs_S_1x']:+.3f})")
    if o['pc4_n_positive'] < 3:
        rej.append(f"PC-4 ({o['pc4_n_positive']} of {o['pc4_n_episodes']} episodes positive)")
    if rej:
        return 'REJECT', '; '.join(rej)
    inc = []
    if o['pc3_p_ni'] > 0.10:
        inc.append(f"PC-3 p_ni {o['pc3_p_ni']:.2f} > 0.10")
    if o['pc4_largest_share'] > 0.5:
        inc.append(f"PC-4 concentration ({o['pc4_largest_share']:.0%} from {o['pc4_largest_episode']})")
    if inc:
        return 'INSUFFICIENT DATA (inconclusive)', '; '.join(inc)
    rev = []
    if not o['pc1_pass_2x'] or not o['pc3_point_pass_2x']:
        rev.append('PC-1/PC-3 point at 2x -> lengthen holding period')
    if o.get('pc6_evaluated', True) and not o['pc6_pass']:
        rev.append(f"PC-6 plateau {o['pc6_share_keep']:.2f} -> widen grid")
    if not o['pc5_pass']:
        rev.append(f"PC-5 years {o['pc5_share_years_positive']:.0%} -> extend history")
    note = '' if o.get('pc6_evaluated', True) else ' (PC-6 not evaluated: no declared grid)'
    if rev:
        return 'REVISE', '; '.join(rev) + note
    return 'PASS', note.strip()
