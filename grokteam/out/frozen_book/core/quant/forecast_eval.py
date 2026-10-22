"""R-30 rule 1 (forecast registry), the forecast-evaluation harness, rule 3-6 (the staged estimator gate), rule 8
(the incumbent's B5 calibration), R-16 (2) and the R-06 estimator row. TASK-M3-02, TASK-M3-03 (hooks), TASK-M3-04.
Items 11a / 29 (`kind: ml` refused), 25 (no switch outside a counted R-30 revision), 28 (no conformal label
layer: calibration is judged here by tick loss and B5), 30 (no max(SMA20, implied) sizing), 33 (no challenger on
the stock book).

Functional forms (binding where the spec prints them; [R] = brief reading, spec_M3_estimators section F):
- QLIKE(y, f) = y/f - ln(y/f) - 1 (Patton 2011 normalisation; zero at y = f; the app's existing scorecard form, with
  a 1e-18 guard inside the log for y = 0 at h = 1; F-8). y[t, h] = sum_{j=1..h} r^2_{t+j}, f = the forecast of it.
- MSE = (y - f)^2; tick loss (alpha - 1{x < q}) (x - q) for a quantile forecast q at level alpha.
- DM: Bartlett HAC with lags max(10, 2h) (`validate.newey_west_t`), Harvey-Leybourne-Newbold factor
  sqrt((n + 1 - 2h + h(h - 1)/n)/n), p from Student-t(n - 1). `validate.dm_test` itself is untouched.
- MCS: Hansen-Lunde-Nason T_max with a Politis-Romano stationary bootstrap (mean block max(10, 2h)), B resamples,
  one seed; p resolution 1/B; membership of the 90% set = p >= 0.10.
- B5 (kept, L1561, L3207): 5% VaR exceedance within 0.05 +- 2 sqrt(0.05 x 0.95 / n) over >= 200 origins AND the PIT
  chi-square on 10 equal bins with p >= 0.01 (`validate.pit_tests`); Kupiec / Christoffersen from `validate`.
  FHS form [R, F-9]: z_s = r_s / sigma_next[s-1]; VaR_{t+1} = sigma_next[t] q_0.05{z_s: s <= t}; expanding pool,
  first origin once 252 residuals exist. Under a normal quantile every estimator fails PIT, so a sigma is never
  shown as a normal VaR (the `normal` form exists for that disclosure only).
- Stage 1 [R, F-10]: at h = 21, non-overlapping origins (every 21st), exceedance inside +-2 binomial SE over >= 200
  origins, fan PIT chi-square p >= 0.01, Christoffersen CC p >= 0.05.
No `datetime.now()`, no network; the only I/O is the read of the shipped rules store for the gate's config block.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import numpy as np
from scipy import stats as sps

from core.ficc import pit as P
from core.quant import validate as V
from core.quant import vol_estimators as E
from core.quant.garch import TRADING_DAYS
from core.rules.macro_rules import MacroRefusal

SEED = 11                      # stage2.seed (L3219), seed_study (L4680)
B_RESAMPLES = 2000             # stage2.resamples
MCS_LEVEL = 0.90               # stage2.mcs_level
VAR_LEVEL = 0.05               # incumbent_calibration.var_level
MIN_ORIGINS = 200              # incumbent_calibration.min_origins
PIT_P_MIN = 0.01               # incumbent_calibration.pit_p_min
MIN_POOL = 252                 # FHS residual pool before the first origin (brief F-9)
CC_P_MIN = 0.05                # Stage-1 CC threshold (brief F-10; the I-11 M9 threshold)
STATUSES = ("registered_default", "challenger_selected", "fallback_to_sma20", "NOT_RUN")
B5_STATUSES = ("PASS", "FAIL", "NOT_RUN")
R06_KR_CARD = "MACRO-R06-KR-ETF"
ACTING_CLOSE = {"KR": "KOSPI_OFFICIAL_CLOSE", "US": "SPX_OFFICIAL_CLOSE"}
_EPS = 1e-18


class EstimatorSwitchRefused(MacroRefusal):
    """A non-SMA20 acting declaration that the switching rule refuses (R-30 rule 6, L3236-3237); nothing is written."""


# --------------------------------------------------------------------------- #
# Forecast registry (rule 1)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ForecastSpec:
    name: str
    kind: str                                  # sma | ewma | garch | har | comb; "ml" refused
    target: str = "sum_r2_next_h"
    horizons: tuple = (1, 5, 21)
    loss: str = "qlike"                        # selection loss, pre-declared
    benchmark: str = "sma20"
    test: str = "mcs_T_max"
    definition: str = ""


FORECAST_REGISTRY: dict[str, ForecastSpec] = {}


def register_forecast(spec: ForecastSpec) -> ForecastSpec:
    """Refuses `kind: ml` (items 11a, 29), a max() over an implied-vol series (item 30) and a duplicate name."""
    if spec.kind == "ml" or "ml" in spec.name.split("_"):
        raise MacroRefusal(f"{spec.name}: an ML vol-state classifier is not an estimator (DNB items 11a, 29)")
    low = (spec.definition + " " + spec.name).lower()
    if "implied" in low and re.search(r"\bmax\s*\(", low):
        raise MacroRefusal(f"{spec.name}: max(sigma, implied) sizing is retired (DNB item 30, L1573)")
    if spec.name in FORECAST_REGISTRY:
        raise MacroRefusal(f"{spec.name}: already registered; a forecaster is registered once (QF7-M2)")
    FORECAST_REGISTRY[spec.name] = spec
    return spec


for _n in E.ESTIMATORS:
    register_forecast(ForecastSpec(_n, E.KIND_OF[_n],
                                   definition={"comb": "0.5*(gjr_t + log_har_range)"}.get(_n, _n)))


def require_registered(name: str) -> ForecastSpec:
    if name not in FORECAST_REGISTRY:
        raise MacroRefusal(f"{name!r} is not a registered forecaster (R-30 rule 1)")
    return FORECAST_REGISTRY[name]


# --------------------------------------------------------------------------- #
# Losses and targets
# --------------------------------------------------------------------------- #
def qlike(y, f) -> np.ndarray:
    """QLIKE(y, f) = y/f - ln(y/f) - 1 (see the module docstring)."""
    z = np.asarray(y, dtype=float) / np.asarray(f, dtype=float)
    return z - np.log(z + _EPS) - 1.0


def mse(y, f) -> np.ndarray:
    return (np.asarray(y, dtype=float) - np.asarray(f, dtype=float)) ** 2


def tick_loss(x, q, alpha: float) -> np.ndarray:
    x, q = np.asarray(x, dtype=float), np.asarray(q, dtype=float)
    return (alpha - (x < q)) * (x - q)


LOSSES = {"qlike": qlike, "mse": mse, "tick": tick_loss}
loss_registry = LOSSES


def realised_target(r, h: int) -> np.ndarray:
    """y[t, h] = sum_{j=1..h} r^2_{t+j}; NaN where the window is not fully realised."""
    r2 = np.asarray(r, dtype=float) ** 2
    T = r2.size
    y = np.full(T, np.nan)
    if T > h:
        c = np.concatenate([[0.0], np.cumsum(r2)])
        y[:T - h] = c[h + 1:] - c[1:T - h + 1]
    return y


def forward_return(r, h: int) -> np.ndarray:
    """R_{t -> t+h} = sum_{j=1..h} r_{t+j}; NaN where incomplete."""
    r = np.asarray(r, dtype=float)
    T = r.size
    out = np.full(T, np.nan)
    if T > h:
        c = np.concatenate([[0.0], np.cumsum(r)])
        out[:T - h] = c[h + 1:] - c[1:T - h + 1]
    return out


# --------------------------------------------------------------------------- #
# Predictive-ability tests
# --------------------------------------------------------------------------- #
def dm_test(loss_a, loss_b, *, h: int = 1, lag: int | None = None) -> dict:
    """Diebold-Mariano on d = loss_a - loss_b (negative t favours A), HAC lags max(10, 2h), HLN small-sample
    factor, p from t(n - 1). The legacy `validate.dm_test(a, b, lag=)` is untouched."""
    lag = max(10, 2 * h) if lag is None else int(lag)
    base = V.dm_test(loss_a, loss_b, lag=lag)
    n = base["n"]
    k = math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n) if n > 2 * h else float("nan")
    t = base["t"] * k
    p = float(2 * sps.t.sf(abs(t), n - 1)) if math.isfinite(t) else float("nan")
    return {"t": float(t), "p": p, "mean_diff": base["mean_diff"], "n": n, "lag": lag, "hln": k}


def cw_test(y, f_small, f_large, *, h: int = 1) -> dict:
    """Clark-West for nested models: adj = e_small^2 - (e_large^2 - (f_small - f_large)^2); one-sided HAC t."""
    y, fs, fl = (np.asarray(a, dtype=float) for a in (y, f_small, f_large))
    adj = (y - fs) ** 2 - ((y - fl) ** 2 - (fs - fl) ** 2)
    lag = max(10, 2 * h)
    t = V.newey_west_t(adj, lag)
    return {"t": float(t), "p": float(sps.norm.sf(t)) if math.isfinite(t) else float("nan"), "n": int(adj.size), "lag": lag}


def gw_test(loss_a, loss_b, *, h: int = 1) -> dict:
    """Giacomini-White conditional predictive ability with instruments [1, d_{t-1}]; Wald chi-square(2) with a
    Bartlett HAC covariance (lags max(10, 2h) for h > 1, 0 at h = 1)."""
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    d = d[np.isfinite(d)]
    if d.size < 10:
        return {"stat": float("nan"), "p": float("nan"), "n": int(d.size)}
    Z = np.column_stack([np.ones(d.size - 1), d[:-1]]) * d[1:, None]
    n = Z.shape[0]
    m = Z.mean(0)
    U = Z - m
    S = U.T @ U / n
    lag = max(10, 2 * h) if h > 1 else 0
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        G = U[k:].T @ U[:-k] / n
        S += w * (G + G.T)
    try:
        stat = float(n * m @ np.linalg.solve(S, m))
    except np.linalg.LinAlgError:
        return {"stat": float("nan"), "p": float("nan"), "n": n}
    return {"stat": stat, "p": float(sps.chi2.sf(stat, 2)), "n": n, "lag": lag}


def stationary_bootstrap_indices(n: int, mean_block: float, rng) -> np.ndarray:
    """One Politis-Romano resample of 0..n-1: geometric block lengths (mean `mean_block`), uniform circular starts."""
    p = 1.0 / float(mean_block)
    lengths = rng.geometric(p, size=n)
    starts = rng.integers(0, n, size=n)
    k = int(np.searchsorted(np.cumsum(lengths), n, side="left")) + 1
    lengths, starts = lengths[:k], starts[:k]
    offs = np.arange(int(lengths.sum())) - np.repeat(np.cumsum(lengths) - lengths, lengths)
    return ((np.repeat(starts, lengths) + offs) % n)[:n]


def mcs(losses: dict, *, h: int = 1, stat: str = "T_max", block: float | None = None, B: int = B_RESAMPLES,
        seed: int = SEED, level: float = MCS_LEVEL) -> dict:
    """Model confidence set (Hansen-Lunde-Nason) on {name: loss series}: T_max statistic, stationary bootstrap with
    mean block max(10, 2h), B resamples drawn once from `seed`. Returns {"p": {name: mcs_p}, "in_set": {...},
    ...}; the last survivor has p = 1.0; p values are multiples of 1/B."""
    if stat != "T_max":
        raise ValueError("only stat='T_max' is implemented (R-30 stage2.stat)")
    names = list(losses)
    L = np.column_stack([np.asarray(losses[k], dtype=float) for k in names])
    L = L[np.all(np.isfinite(L), axis=1)]
    T, m = L.shape
    if T < 30 or m < 1:
        raise ValueError(f"mcs needs >= 30 common origins and >= 1 model; got {T} x {m}")
    block = max(10, 2 * h) if block is None else block
    rng = np.random.default_rng(seed)
    Lbar = L.mean(0)
    Lstar = np.empty((B, m))
    for b in range(B):
        Lstar[b] = L[stationary_bootstrap_indices(T, block, rng)].mean(0)
    M, p_prev, pvals = list(range(m)), 0.0, {}
    while len(M) > 1:
        cols = np.asarray(M)
        d = Lbar[cols] - Lbar[cols].mean()
        dstar = Lstar[:, cols] - Lstar[:, cols].mean(1, keepdims=True)
        se = np.sqrt(np.maximum(((dstar - d) ** 2).mean(0), 1e-300))
        t = d / se
        T_max = float(t.max())
        T_star = ((dstar - d) / se).max(1)
        p = float(np.mean(T_star >= T_max))
        p_prev = max(p_prev, p)
        e = int(cols[int(np.argmax(t))])
        pvals[names[e]] = p_prev
        M.remove(e)
    pvals[names[M[0]]] = 1.0
    return {"p": {k: pvals[k] for k in names}, "in_set": {k: pvals[k] >= 1.0 - level for k in names},
            "n": int(T), "B": int(B), "seed": int(seed), "block": block, "stat": stat, "level": level}


kupiec = V.kupiec
christoffersen_cc = V.christoffersen


# --------------------------------------------------------------------------- #
# Filtered historical simulation, B5, fan PIT, ES Z2 (rule 8, Stage 1)
# --------------------------------------------------------------------------- #
def band(n: int, level: float = VAR_LEVEL) -> tuple[float, float]:
    """level +- 2 sqrt(level (1 - level) / n) (L1561): n 2,594 -> 4.14-5.86%, 8,961 -> 4.54-5.46%."""
    se = math.sqrt(level * (1.0 - level) / n) if n > 0 else float("nan")
    return level - 2.0 * se, level + 2.0 * se


class _Pool:
    """Expanding sorted residual pool with quantile (linear interpolation) and ECDF (mid-rank on ties)."""

    def __init__(self) -> None:
        self.z: list = []

    def add(self, x: float) -> None:
        import bisect
        bisect.insort(self.z, float(x))

    def __len__(self) -> int:
        return len(self.z)

    def quantile(self, q: float) -> float:
        n = len(self.z)
        pos = q * (n - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, n - 1)
        return self.z[lo] + (pos - lo) * (self.z[hi] - self.z[lo])

    def ecdf(self, x: float) -> float:
        import bisect
        lo, hi = bisect.bisect_left(self.z, x), bisect.bisect_right(self.z, x)
        return (lo + 0.5 * (hi - lo)) / len(self.z)

    def tail_mean(self, q: float) -> float:
        import bisect
        k = bisect.bisect_right(self.z, q)
        return float(np.mean(self.z[:k])) if k else q


def fhs_eval(r, var_fc, h: int = 1, *, alpha: float = VAR_LEVEL, min_pool: int = MIN_POOL, stride: int | None = None,
             pool_var=None, origins_from: int | None = None, alphas: tuple = ()) -> dict:
    """Rolling-origin FHS at horizon h. Pool residuals z_s = R_{s,h} / sqrt(pool_var[s]) for every origin s whose
    h-day return is realised by t (s + h <= t; overlapping); evaluated origins run every `stride` sessions (default
    h: non-overlapping) once the pool holds `min_pool` residuals and t >= `origins_from`. hit = R < sigma q_alpha(pool);
    u = ECDF_pool(R / sigma). `pool_var` (default `var_fc`) lets a test scale the out-of-sample forecast alone
    (brief F-16). `alphas` adds hit series at other levels (e.g. 0.01 for the printed 99% lines)."""
    r = np.asarray(r, dtype=float)
    T = r.size
    var_fc = np.asarray(var_fc, dtype=float)
    pvar = var_fc if pool_var is None else np.asarray(pool_var, dtype=float)
    stride = h if stride is None else int(stride)
    R = forward_return(r, h)
    sig = np.sqrt(np.where(var_fc > 0, var_fc, np.nan))
    psig = np.sqrt(np.where(pvar > 0, pvar, np.nan))
    z = R / psig
    pool, hits, extra, u, origins, nxt = _Pool(), [], {a: [] for a in alphas}, [], [], None
    for t in range(T):
        s = t - h                                   # the residual of origin s is realised at t
        if s >= 0 and math.isfinite(z[s]):
            pool.add(z[s])
        if len(pool) < min_pool or not math.isfinite(sig[t]) or not math.isfinite(R[t]):
            continue
        if origins_from is not None and t < origins_from:
            continue
        if nxt is None:
            nxt = t
        if t < nxt:
            continue
        nxt = t + stride
        x = R[t] / sig[t]
        hits.append(x < pool.quantile(alpha))
        for a in alphas:
            extra[a].append(x < pool.quantile(a))
        u.append(pool.ecdf(x))
        origins.append(t)
    hits, u = np.asarray(hits, dtype=bool), np.asarray(u, dtype=float)
    n = int(hits.size)
    exceed = float(hits.mean()) if n else float("nan")
    lo, hi = band(n, alpha) if n else (float("nan"), float("nan"))
    pit = V.pit_tests(u) if n >= 20 else {"chi2_p": float("nan"), "ks_p": float("nan"), "n": n}
    return {"h": h, "n_origins": n, "exceedance": exceed, "band": (lo, hi), "in_band": bool(n and lo <= exceed <= hi),
            "pit_chi2_p": float(pit["chi2_p"]), "pit_ks_p": float(pit.get("ks_p", float("nan"))),
            "kupiec": V.kupiec(hits, alpha), "christoffersen": V.christoffersen(hits, alpha),
            "hits": hits, "hits_at": {a: np.asarray(v, dtype=bool) for a, v in extra.items()}, "u": u,
            "origins": np.asarray(origins, dtype=int), "alpha": alpha}


def _jsonable(x):
    """Plain JSON types only (the gate object is an acting artifact field): numpy scalars unboxed, non-finite
    numbers -> None, tuples -> lists."""
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.generic):
        x = x.item()
    if isinstance(x, bool) or x is None or isinstance(x, str):
        return x
    if isinstance(x, (int, float)):
        return x if math.isfinite(x) else None
    return str(x)


def _scalar(ev: dict) -> dict:
    """The JSON-serialisable part of an evaluation (no arrays)."""
    return _jsonable({k: v for k, v in ev.items() if k not in ("hits", "hits_at", "u", "origins")})


def b5(r, sigma_next, *, form: str = "fhs", var_level: float = VAR_LEVEL, min_origins: int = MIN_ORIGINS,
       pit_p_min: float = PIT_P_MIN, nu: float | None = None, pool_sigma=None, min_pool: int = MIN_POOL,
       origins_from: int | None = None) -> dict:
    """B5 (kept): `sigma_next[t]` is the 1-day sigma forecast for day t+1 made at close t (daily units).
    status NOT_RUN below `min_origins`; PASS iff the exceedance is inside the band and PIT chi2 p >= pit_p_min; else
    FAIL. Forms: "fhs" (sizing estimators), "normal" and "t" (disclosure only; a sigma is never shown as a normal
    VaR, L1561)."""
    r = np.asarray(r, dtype=float)
    sig = np.asarray(sigma_next, dtype=float)
    if form == "fhs":
        ev = fhs_eval(r, sig ** 2, 1, alpha=var_level, min_pool=min_pool, origins_from=origins_from,
                      pool_var=None if pool_sigma is None else np.asarray(pool_sigma, dtype=float) ** 2)
    elif form in ("normal", "t"):
        if form == "t" and not (nu and nu > 2):
            raise ValueError("form='t' needs nu > 2")
        T = r.size
        x = r[1:] / sig[:-1]
        ok = np.isfinite(x) & (sig[:-1] > 0)
        if origins_from is not None:
            ok &= np.arange(T - 1) >= origins_from
        x = x[ok]
        if form == "normal":
            q, u = sps.norm.ppf(var_level), sps.norm.cdf(x)
        else:
            sc = math.sqrt((nu - 2.0) / nu)
            q, u = sps.t.ppf(var_level, nu) * sc, sps.t.cdf(x / sc, nu)
        hits = x < q
        n = int(hits.size)
        exceed = float(hits.mean()) if n else float("nan")
        lo, hi = band(n, var_level) if n else (float("nan"), float("nan"))
        pit = V.pit_tests(u) if n >= 20 else {"chi2_p": float("nan"), "ks_p": float("nan")}
        ev = {"h": 1, "n_origins": n, "exceedance": exceed, "band": (lo, hi), "in_band": bool(n and lo <= exceed <= hi),
              "pit_chi2_p": float(pit["chi2_p"]), "pit_ks_p": float(pit["ks_p"]), "kupiec": V.kupiec(hits, var_level),
              "christoffersen": V.christoffersen(hits, var_level), "alpha": var_level}
    else:
        raise ValueError("form must be 'fhs', 'normal' or 't'")
    out = _scalar(ev)
    out["form"] = form
    n = out["n_origins"]
    if n < min_origins:
        out["status"] = "NOT_RUN"
    else:
        out["status"] = "PASS" if (out["in_band"] and out["pit_chi2_p"] >= pit_p_min) else "FAIL"
    out["min_origins"], out["pit_p_min"] = min_origins, pit_p_min
    return out


def fan_pit(r, var_h, h: int, **kw) -> dict:
    """The h-day fan PIT (chi-square on 10 equal bins) at non-overlapping origins; the Stage-1 `fan_pit_h21` line."""
    ev = fhs_eval(r, var_h, h, **kw)
    return {"h": h, "n_origins": ev["n_origins"], "chi2_p": ev["pit_chi2_p"], "ks_p": ev["pit_ks_p"]}


def es_z2(r, sigma_next, *, alpha: float = 0.025, min_pool: int = MIN_POOL, n_sim: int = B_RESAMPLES, seed: int = SEED,
          origins_from: int | None = None) -> dict:
    """Acerbi-Szekely Z2 for the FHS ES at level alpha: Z2 = sum_t x_t I_t / (n alpha ES_t) + 1, I_t = 1{x_t < -VaR_t},
    ES_t > 0; negative = risk understated. p = share of `n_sim` simulated Z2 (x*_t = sigma_t z*, z* iid from the
    final residual pool; brief F-11) at or below the observed value."""
    r = np.asarray(r, dtype=float)
    sig = np.asarray(sigma_next, dtype=float)
    T = r.size
    pool, xs, sigs, vars_, ess = _Pool(), [], [], [], []
    for t in range(T - 1):
        if t >= 1 and math.isfinite(r[t]) and sig[t - 1] > 0:
            pool.add(r[t] / sig[t - 1])
        if len(pool) < min_pool or not (sig[t] > 0) or not math.isfinite(r[t + 1]):
            continue
        if origins_from is not None and t < origins_from:
            continue
        q = pool.quantile(alpha)
        xs.append(r[t + 1]); sigs.append(sig[t]); vars_.append(-sig[t] * q); ess.append(-sig[t] * pool.tail_mean(q))
    x, s, var_t, es_t = (np.asarray(a, dtype=float) for a in (xs, sigs, vars_, ess))
    n = x.size
    if n < 20 or len(pool) < min_pool:
        return {"z2": float("nan"), "p": float("nan"), "n": int(n), "alpha": alpha}
    z2 = float(np.sum(x * (x < -var_t) / (n * alpha * es_t)) + 1.0)
    rng = np.random.default_rng(seed)
    z = np.asarray(pool.z)
    sims = np.empty(n_sim)
    chunk = max(1, min(n_sim, int(4e6 // max(n, 1))))
    for a in range(0, n_sim, chunk):
        k = min(chunk, n_sim - a)
        zs = rng.choice(z, size=(k, n), replace=True)
        xs_ = s * zs
        sims[a:a + k] = np.sum(xs_ * (xs_ < -var_t) / (n * alpha * es_t), axis=1) + 1.0
    return {"z2": z2, "p": float(np.mean(sims <= z2)), "n": int(n), "alpha": alpha, "n_sim": int(n_sim), "seed": int(seed)}


def reliability_table(forecast, realised, bins: int = 10) -> list[dict]:
    """Equal-count forecast bins: mean forecast, mean realised and n per bin."""
    f, y = np.asarray(forecast, dtype=float), np.asarray(realised, dtype=float)
    ok = np.isfinite(f) & np.isfinite(y)
    f, y = f[ok], y[ok]
    if f.size < bins:
        return []
    order = np.argsort(f)
    rows = []
    for i, idx in enumerate(np.array_split(order, bins)):
        rows.append({"bin": i, "n": int(idx.size), "forecast_mean": float(f[idx].mean()), "realised_mean": float(y[idx].mean())})
    return rows


# --------------------------------------------------------------------------- #
# Sized books (Stage 3 input; G-EST-04 conventions L5932)
# --------------------------------------------------------------------------- #
def max_drawdown(daily) -> float:
    nav = np.cumprod(1.0 + np.asarray(daily, dtype=float))
    return float(np.min(nav / np.maximum.accumulate(nav) - 1.0)) if nav.size else float("nan")


def vol_of_vol(daily, window: int = 63) -> float:
    """SD of the rolling `window`-session annualised realised vol of the book (L3197)."""
    d = np.asarray(daily, dtype=float)
    if d.size < window + 2:
        return float("nan")
    c = np.concatenate([[0.0], np.cumsum(d)])
    c2 = np.concatenate([[0.0], np.cumsum(d * d)])
    m = (c[window:] - c[:-window]) / window
    v = (c2[window:] - c2[:-window]) / window - m * m
    rv = np.sqrt(np.maximum(v, 0.0) * window / (window - 1) * TRADING_DAYS)
    return float(np.std(rv, ddof=1))


def sized_book(r, var_h, *, h: int = 21, target_ann: float = 0.20, cost_bps: float = 3.0, cap: float = 1.0) -> dict:
    """w[t] = min(cap, target / sqrt(var_h[t] / h x 252)), decided at close t, earning r[t+1]; cost per side x |dw|
    charged on the day the weight earns; the initial entry is free (L5725). `cap` above 1.0 is refused (L1563)."""
    if cap > 1.0:
        raise ValueError("cap above 1.0 is refused in core/ (cap 1.0 permanent, L1563)")
    r = np.asarray(r, dtype=float)
    v = np.asarray(var_h, dtype=float)
    T = r.size
    sig = np.sqrt(np.where(v > 0, v / h * TRADING_DAYS, np.nan))
    w = np.where(np.isfinite(sig), np.minimum(cap, target_ann / sig), np.nan)
    idx = np.flatnonzero(np.isfinite(w))
    if idx.size < 2 or idx[0] + 1 >= T:
        return {"daily": np.array([]), "sharpe": float("nan"), "max_dd": float("nan"), "turnover_per_year": float("nan"),
                "vol_of_vol": float("nan"), "weights": w, "n": 0}
    first = int(idx[0])
    w_use = w[first:T - 1]
    w_use = np.where(np.isfinite(w_use), w_use, np.nan)
    # a NaN weight after the first (forecast failed) holds the previous weight: no stale challenger acts, but the
    # book cannot be unwound by a missing forecast either; the gate's fallback covers the acting path
    for i in range(1, w_use.size):
        if not math.isfinite(w_use[i]):
            w_use[i] = w_use[i - 1]
    dw = np.abs(np.diff(np.concatenate([[w_use[0]], w_use])))
    daily = w_use * r[first + 1:] - cost_bps / 1e4 * dw
    years = daily.size / TRADING_DAYS
    return {"daily": daily, "sharpe": V.sharpe(daily), "max_dd": max_drawdown(daily),
            "turnover_per_year": float(dw.sum() / years) if years else float("nan"), "vol_of_vol": vol_of_vol(daily),
            "weights": w, "n": int(daily.size), "mean_weight": float(np.mean(w_use)), "first_origin": first}


def pc2_tail_ratio(weights, r, q: float = 0.05) -> float:
    """PC-2 tail ratio [R]: mean multiplier on the worst `q` share of underlying days / mean multiplier on all days
    (L2157 "TR <= 0.90 passes"); `weights[t]` is the weight earning r[t]."""
    w, x = np.asarray(weights, dtype=float), np.asarray(r, dtype=float)
    ok = np.isfinite(w) & np.isfinite(x)
    w, x = w[ok], x[ok]
    if w.size < 20:
        return float("nan")
    k = max(1, int(math.floor(q * w.size)))
    worst = np.argsort(x)[:k]
    return float(np.mean(w[worst]) / np.mean(w))


# --------------------------------------------------------------------------- #
# Stages (rules 3-5)
# --------------------------------------------------------------------------- #
def stage1(r, var21, var1=None, *, horizon: int = 21, min_pool: int = MIN_POOL, origins_from: int | None = None,
           seed: int = SEED, n_sim: int = B_RESAMPLES) -> dict:
    """Stage-1 report (config strings of L3218): gated at h = 21 (FHS exceedance, fan PIT, Christoffersen CC);
    printed 1-day Kupiec and CC at 95% / 99% and ES 97.5% Z2; `b5_1d` decides `var_1d_displayable`."""
    r = np.asarray(r, dtype=float)
    ev = fhs_eval(r, var21, horizon, alpha=VAR_LEVEL, min_pool=min_pool, stride=horizon, origins_from=origins_from)
    n = ev["n_origins"]
    cc = ev["christoffersen"]
    rep = {"horizon_days": int(horizon),
           "fhs_var_exceedance_h21": {"n_origins": n, "exceedance": ev["exceedance"], "band": list(ev["band"]),
                                      "in_band": ev["in_band"]},
           "fan_pit_h21": {"n_origins": n, "chi2_p": ev["pit_chi2_p"], "ks_p": ev["pit_ks_p"]},
           "christoffersen_cc": {"p_ind": cc["p_ind"], "p_cc": cc["p_cc"], "lr_cc": cc["lr_cc"]},
           "printed": {}, "b5_1d": None}
    if var1 is not None:
        sig1 = np.sqrt(np.where(np.asarray(var1, dtype=float) > 0, var1, np.nan))
        one = fhs_eval(r, sig1 ** 2, 1, alpha=VAR_LEVEL, min_pool=min_pool, origins_from=origins_from, alphas=(0.01,))
        h99 = one["hits_at"].get(0.01, np.array([], dtype=bool))
        cc95, cc99 = V.christoffersen(one["hits"], 0.05), V.christoffersen(h99, 0.01)
        rep["printed"] = {"kupiec_1d": {"95": one["kupiec"], "99": V.kupiec(h99, 0.01)},
                          "cc_1d_95_99": {"95": {"p_ind": cc95["p_ind"], "p_cc": cc95["p_cc"]},
                                          "99": {"p_ind": cc99["p_ind"], "p_cc": cc99["p_cc"]}},
                          "es975_z2": es_z2(r, sig1, alpha=0.025, min_pool=min_pool, n_sim=n_sim, seed=seed,
                                            origins_from=origins_from)}
        rep["b5_1d"] = b5(r, sig1, form="fhs", min_pool=min_pool, origins_from=origins_from)
    rep["pass"] = bool(n >= MIN_ORIGINS and ev["in_band"] and ev["pit_chi2_p"] >= PIT_P_MIN
                       and math.isfinite(cc["p_cc"]) and cc["p_cc"] >= CC_P_MIN)
    return _jsonable(rep)


def stage2(losses_by_model: dict, *, h: int = 21, B: int = B_RESAMPLES, seed: int = SEED) -> dict:
    """{"qlike_mcs_p", "mse_mcs_p", "in_set"}: membership of the 90% QLIKE MCS at h; the MSE MCS is printed."""
    q = mcs({k: v["qlike"] for k, v in losses_by_model.items()}, h=h, B=B, seed=seed)
    m = mcs({k: v["mse"] for k, v in losses_by_model.items()}, h=h, B=B, seed=seed)
    return {"qlike_mcs_p": q["p"], "mse_mcs_p": m["p"], "in_set": q["in_set"], "h": h, "B": B, "seed": seed}


def stage3(books: dict, r=None, *, delta: float = 0.10, pc2_max: float = 0.90, ci_fn=None,
           order=E.COMPLEXITY_ORDER) -> dict:
    """Point statistics per survivor against the SMA20 book (dSR, dMDD in decimal, PC-2 tail ratio, vol-of-vol) and
    the point eligibility. `ci_fn(daily_a, daily_b) -> (lo, hi)` is the R-24 dSR 90% interval
    (`gate_stats.lw_studentized_boot(a, b, block, B, seed, null=-delta)["ci"]`, bound by the runner); `rank` and
    `winner` stay None: R-30 stage 3 names the tie as "overlapping bootstrap CIs" without naming the statistic
    whose CI is meant (dSR or vol-of-vol); that reading is fixed with the package before any switch (TASK-M7-28)."""
    base = books.get("sma20")
    rows = {}
    for name in order:
        bk = books.get(name)
        if bk is None or base is None:
            continue
        dsr = bk["sharpe"] - base["sharpe"]
        dmdd = bk["max_dd"] - base["max_dd"]
        tr = pc2_tail_ratio(bk["weights"][bk["first_origin"]:-1], r[bk["first_origin"] + 1:]) if (
            r is not None and bk.get("n")) else float("nan")
        ci = tuple(ci_fn(bk["daily"], base["daily"])) if ci_fn is not None else None
        rows[name] = {"sharpe": bk["sharpe"], "max_dd": bk["max_dd"], "turnover_per_year": bk["turnover_per_year"],
                      "vol_of_vol": bk["vol_of_vol"], "dSR_vs_sma20": dsr, "dMDD_vs_sma20": dmdd, "pc2_tail_ratio": tr,
                      "dSR_ci90": ci, "eligible_point": bool(dsr >= -delta and dmdd >= 0 and (not math.isfinite(tr) or tr <= pc2_max))}
    return {"rows": rows, "rank": None, "winner": None, "delta": delta, "pc2_max": pc2_max,
            "note": "rank and winner not computed: the stage-3 tie statistic (overlapping bootstrap CIs) is an open reading (TASK-M7-28)"}


def evaluate_estimators(r, ohlc: E.OHLC | None, market: str | None, *, horizons=(1, 5, 21), names=E.COMPLEXITY_ORDER,
                        oos_start: int | None = None, B: int = B_RESAMPLES, seed: int = SEED, mcs_on: bool = True,
                        **fit_kw) -> dict:
    """Pure research harness: forecasts of every registered estimator at each h, losses on the common out-of-sample
    origins, the QLIKE / MSE MCS and the QLIKE ratio to SMA20. GJR-t and log-HAR-range are fitted once per h and
    COMB is built from them (`comb_from`)."""
    r = np.asarray(r, dtype=float)
    out = {"forecasts": {}, "losses": {}, "mcs": {}, "qlike_ratio": {}, "n": {}}
    for h in horizons:
        fc = {}
        for n in names:
            if n == "comb":
                continue
            f = E.forecast(n, r, h, ohlc=ohlc, market=market, **fit_kw)
            if isinstance(f, P.MissingInput):
                continue
            fc[n] = f
        if "comb" in names and "gjr_t" in fc and "log_har_range" in fc:
            fc["comb"] = E.comb_from(fc["gjr_t"], fc["log_har_range"])
        excluded = {n: f.reason[-1] for n, f in fc.items() if not f.ok.any()}   # never produced a forecast
        fc = {n: f for n, f in fc.items() if n not in excluded}
        y = realised_target(r, h)
        mask = np.isfinite(y)
        if oos_start is not None:
            mask &= np.arange(r.size) >= oos_start
        for f in fc.values():
            mask &= f.ok & np.isfinite(f.var)
        out.setdefault("excluded", {})[h] = excluded
        losses = {n: {"qlike": qlike(y[mask], f.var[mask]), "mse": mse(y[mask], f.var[mask])} for n, f in fc.items()}
        out["forecasts"][h], out["losses"][h], out["n"][h] = fc, losses, int(mask.sum())
        if "sma20" in losses:
            base = float(np.mean(losses["sma20"]["qlike"]))
            out["qlike_ratio"][h] = {n: float(np.mean(v["qlike"])) / base for n, v in losses.items()}
        if mcs_on and len(losses) >= 2 and int(mask.sum()) >= 30:
            out["mcs"][h] = stage2(losses, h=h, B=B, seed=seed)
    return out


# --------------------------------------------------------------------------- #
# The gate (rules 3-8, Fail-closed behaviour; section 6.1 `vol`)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EstimatorSelection:
    estimator: str                       # the ACTING estimator for this decision
    estimator_b5: str                    # PASS | FAIL | NOT_RUN (the incumbent SMA20's B5)
    status: str                          # registered_default | challenger_selected | fallback_to_sma20 | NOT_RUN
    stage1: dict | None
    stage2_mcs_p: float | None
    stage3_rank: int | None
    fallback_used: bool
    reason: str | None
    forecast_eval: dict | None = None
    var_1d_displayable: bool = False     # True only if the acting estimator passes the 1-day B5 (L3193)
    sigma_ann: float | None = None
    b5: dict | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.estimator not in E.ESTIMATORS or self.status not in STATUSES or self.estimator_b5 not in B5_STATUSES:
            raise ValueError("EstimatorSelection outside the section 6.1 enums")

    def gate_dict(self) -> dict:
        """Exactly `macro_state.vol.estimator_gate` (L3231; closed object)."""
        return {"status": self.status, "stage1": self.stage1, "stage2_mcs_p": self.stage2_mcs_p,
                "stage3_rank": self.stage3_rank, "fallback_used": bool(self.fallback_used), "reason": self.reason}

    def vol_fields(self) -> dict:
        return {"estimator": self.estimator, "estimator_b5": self.estimator_b5, "estimator_gate": self.gate_dict()}


GateResult = EstimatorSelection


def _not_run(reason: str, *, b5_status: str = "NOT_RUN") -> EstimatorSelection:
    return EstimatorSelection("sma20", b5_status, "NOT_RUN", None, None, None, False, reason[:500])


def canonical_estimator(declared, spec: dict | None = None) -> str:
    """`{estimator: sma, window: 20}` and `sma` -> sma20; `ewma` with lambda 0.94 / 0.97 -> ewma094 / ewma097;
    `kind: ml` refused (brief F-21)."""
    spec = spec or {}
    if isinstance(declared, dict):
        if declared.get("kind") == "ml":
            raise EstimatorSwitchRefused("kind: ml is refused (DNB items 11a, 29)")
        declared = declared.get("name") or declared.get("estimator")
    params = spec.get("parameters") if isinstance(spec.get("parameters"), dict) else {}
    if declared in (None, "sma", "sma20") and int(params.get("window", 20)) == 20:
        return "sma20"
    if declared == "ewma":
        lam = float(params.get("lambda", params.get("lam", 0.94)))
        declared = {0.94: "ewma094", 0.97: "ewma097"}.get(round(lam, 2), declared)
    if declared not in E.ESTIMATORS:
        raise EstimatorSwitchRefused(f"estimator {declared!r} is not an R-30 estimator {E.ESTIMATORS}")
    return declared


def _gate_config() -> dict:
    from core.rules.macro_rules import load_store                       # shipped store: read-only seed
    return load_store().get("vol_target.estimator_gate")


def check_declaration(declared: str, instrument_book: str | None, card_id: str | None, revision, cfg: dict | None = None) -> str:
    """R-30 rule 6 and Fail-closed behaviour: SMA20 passes; anything else is refused at M3. The order of the
    refusals matters for the message only: the registered R-06 KR card, then a challenger on a book outside
    `books_allowed` (the stock book), then a switch without a counted revision, then the M7 gap (no R-23 ledger,
    no CARD-P yet)."""
    if declared == "sma20":
        return declared
    cfg = cfg or _gate_config()
    if card_id == R06_KR_CARD:
        raise EstimatorSwitchRefused(f"{card_id} keeps SMA20 as its primary configuration (R-30 rule 6); "
                                     f"a {declared} variant is a separate counted revision")
    if declared in ("comb", "log_har_range"):
        allowed = tuple(cfg["challenger"]["books_allowed"])
        if instrument_book not in allowed:
            raise EstimatorSwitchRefused(f"{declared} on {instrument_book!r} is refused: COMB / log-HAR run on ETF and "
                                         f"futures books only {allowed} (R-30 rule 6, L3237; item 33)")
    if revision is None:
        raise EstimatorSwitchRefused(f"an estimator switch to {declared} without a counted revision is refused "
                                     "(R-30 Fail-closed behaviour; T-B5-01; item 25)")
    # The M7 counted-revision proof (item 25; T-EST-05): the R-23 ledger row of the challenger configuration
    # (`params.estimator == declared`, chained `row_md5`; gate_ledger.register_trial), the header revision that names
    # the switch (`revision >= 2`, a `revision_reasons` entry naming the estimator; gate_ledger.bump_revision) and the
    # challenger's full v2 CARD-P with verdict PASS (`results_md5`; cards.write_card). Anything short is refused.
    proof = revision if isinstance(revision, dict) else {}
    row, header, card = proof.get("ledger_row"), proof.get("header"), proof.get("card")
    missing = []
    if not (isinstance(row, dict) and row.get("row_md5") and (row.get("params") or {}).get("estimator") == declared):
        missing.append("ledger_row (the R-23 row of the challenger configuration: params.estimator == declared, row_md5)")
    if not (isinstance(header, dict) and int(header.get("revision") or 1) >= 2
            and any(declared in str(r) for r in (header.get("revision_reasons") or ()))):
        missing.append("header (revision >= 2 whose revision_reasons name the estimator)")
    if not (isinstance(card, dict) and card.get("class") == "CARD-P" and card.get("verdict") == "PASS" and card.get("results_md5")):
        missing.append("card (the challenger's full v2 CARD-P with verdict PASS and results_md5)")
    if missing:
        raise EstimatorSwitchRefused(f"a {declared} challenger needs the M7 counted-revision proof (R-23 ledger row, header "
                                     f"revision, passing v2 CARD-P); missing {missing} (R-30 rule 6; item 25)")
    return declared


def estimator_gate(card_or_spec, registry, store, *, ctx: P.RunContext, market: str | None = None,
                   instrument_book: str | None = None, series_id: str | None = None, horizon: int = 21,
                   declared=None, card_id: str | None = None, revision=None, consumer: str = "R-06",
                   session_date=None, vendor: str | None = None, gate_config: dict | None = None, log=None,
                   with_stage1: bool = True, min_pool: int = MIN_POOL) -> EstimatorSelection:
    """The acting selection for one decision. Reads closes only through `pit_window` (history) after resolving the
    consumer binding, and the decided session's close through `pit_value` (an acting read: official_close or a
    declared vendor in a backtest). Refusals of the declaration raise `EstimatorSwitchRefused` before any read;
    every other outcome is a schema-valid object (acting fields, L3370): insufficient history, a missing or
    provisional close, or an internal error return `status NOT_RUN` with the cause in `reason`."""
    spec = dict(card_or_spec or {})
    declared = canonical_estimator(declared if declared is not None else spec.get("estimator"), spec)
    market = market or spec.get("market")
    instrument_book = instrument_book or spec.get("instrument_book")
    card_id = card_id or spec.get("card_id")
    check_declaration(declared, instrument_book, card_id, revision, gate_config)
    series_id = series_id or spec.get("series_id") or ACTING_CLOSE.get(market or "")
    if not series_id:
        return _not_run(f"no acting close series for market {market!r}")
    try:
        registry.resolve_binding(series_id, consumer)                    # the consumer binding (R-19 rule 5)
        window = P.pit_window(store, series_id, ctx.decision_utc, ctx.knowledge_utc, registry=registry,
                              statuses=P.CLOSE_STATUSES)
        if not window:
            return _not_run(f"missing: no visible close of {series_id} at {P.iso_utc(ctx.decision_utc)}")
        session = session_date or ctx.decision_utc.date()
        head = P.pit_value(store, series_id, ctx.decision_utc, ctx.knowledge_utc, consumer, session,
                           run_mode=ctx.run_mode, vendor=vendor or spec.get("vendor"), registry=registry)
        if isinstance(head, P.MissingInput):
            return _not_run(f"{head.reason}: {series_id} for session {session} {head.detail}".strip())
        from core.quant.risk_layer import _close_ok                     # the vt predicate: live reads official closes only
        usable = [v for v in window if v.obs_date <= session and _close_ok(v, ctx.run_mode, vendor or spec.get("vendor"))]
        rets = P.returns_excluding_rolls(usable, P.roll_days(registry, series_id))
        r = np.asarray([x for _, x in rets], dtype=float)
        dec = E.sigma_for_decision(declared, r, h=horizon, log=log)
        if dec.sigma_ann is None:
            return _not_run(f"{dec.reason}: {r.size} returns of {series_id}")
        var1 = E.sma(r, 1).var
        b5_inc = b5(r, np.sqrt(np.where(var1 > 0, var1, np.nan)), form="fhs", min_pool=min_pool)
        s1 = None
        if with_stage1 and b5_inc["status"] != "NOT_RUN":
            s1 = stage1(r, E.sma(r, horizon).var, var1, horizon=horizon, min_pool=min_pool)
        return EstimatorSelection(dec.estimator_used, b5_inc["status"], dec.status, s1, None, None,
                                  dec.fallback_used, dec.reason, None, b5_inc["status"] == "PASS", dec.sigma_ann, b5_inc)
    except EstimatorSwitchRefused:
        raise
    except Exception as exc:                                             # acting field: never an invalid object
        return _not_run(f"error:{type(exc).__name__}: {exc}")
