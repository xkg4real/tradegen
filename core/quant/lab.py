"""Quant Lab calibration, tails, self-grading and replays — R-16 rules (1), (2) label, (3), (5), (6); TASK-M9-01,
M9-02, M9-04; I-11, T-REPRO-01c. CONTEXT (L1747 (6)): "No lab output is read by a sizing module" — every result
carries `acts = False`, and tests/macro_m9_lab.py scans the sizing modules for an import of this module.

Pure functions on numpy arrays: no I/O, no clock, no provider import. The page and `docs/quant_lab_grading.py`
load the series; `grade_lab(market, series, ctx)` grades it.

Conventions (binding where cited):
- `r` are daily log returns of the series (F-30; the lab's own fits are log-return fits); `sigma_next[t]` is the
  1-day sigma forecast for t+1 made at close t; a tail line's `var*[t]` / `es975[t]` is the positive loss fraction
  forecast for t+1, aligned to origin t (brief B.2). The realisation graded against `line[t]` is `r[t+1]`.
- FHS (L1747 (1)): `z_s = r_s / sigma_next[s-1]`, expanding pool, first origin once 252 residuals exist (M3's
  convention); `VaR_a = -sigma * q_{1-a}(pool)`, `ES_a = -sigma * mean(z | z <= q)`. "fast FHS" = FHS with the
  SMA20 sigma on simple returns (M2 `risk_layer.sma_vol` == `vol_estimators.sma`; F-6).
- GJR-EVT (McNeil-Frey, L1747 (1); F-7): sigma from M3 `vol_estimators.gjr_t` (expanding >= 10-year fits, refit
  every 21 origins, R-30 bounds); losses `x = -z`; `k = floor(0.10 n)`; `u` = the (k+1)-th largest loss; GPD(xi, beta)
  by ML on the exceedances (`scipy.stats.genpareto.fit(..., floc=0)`); `x_q = u + beta/xi ((1-q)/(k/n))^(-xi) - 1)`,
  `ES_q = x_q/(1-xi) + (beta - xi u)/(1-xi)`; refit every 21 origins on the pool through t. Fail closed: xi >= 1,
  k < 50, a non-finite fit -> `evt_fit_failed`, and the envelope is withheld (fast FHS shown alone with the reason).
- Envelope (L1747 (3)): `max(fast FHS, GJR-EVT)` elementwise in loss units; `ok = a.ok & b.ok`. It is a graded
  VaR/ES line, never a fifth fan model (`montecarlo.MODELS` is untouched).
- Fan PIT (L1747 (3); brief B.3, F-11): the lab's default fan model, montecarlo's `garch_t` paths (GARCH(1,1)-t
  fitted on r[:t+1], the expanding window; `garch.simulate_returns` seeded; drift "premium" rf 3 % + ERP 4 %, the
  page default), deciles of the h-day log return, non-overlapping origins (every h sessions) inside 2016-26 with
  >= 10 years behind them; chi-square on 10 equal bins. h = 21 gated, h = 126 reported.
- Displayed 1-day VaR after multi-session gaps: `x sqrt(max(n_US, 1))` (R-10 L1631; F-28); the gated series is
  the displayed (scaled) one, the unscaled breach rates are printed beside it (F-29). The latest 1-day number is
  displayable only when every component passes 1-day B5 (`forecast_eval.b5`, FHS form; L1747 (2), F-8).
- The M9 gate (I-11, L5701) on the out-of-sample "2016-26" period: 99% VaR Kupiec p >= 0.05 and Christoffersen CC
  p >= 0.05, ES 97.5% Z2 not rejected at 5% (simulated critical values), fan PIT chi-square p >= 0.01 at h = 21.
  "2026" and h = 126 are reported, not gated (section 12 L6371). A FAIL changes no exposure and re-tunes nothing.
- Section 7 has no `quant_lab` block (F-14): the rule's numbers live in `LAB_CONFIG` below, read from this module
  constant, not from the store; `fit` mirrors `vol_target.estimator_gate.fit`.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

import numpy as np
import scipy.stats as sps

from core.quant import validate as V
from core.quant import vol_estimators as E
from core.quant.forecast_eval import _Pool, _jsonable, b5, tick_loss

GIT_HASH = "UNVERSIONED"                       # rulings 3.1
SEED = 11                                      # reproducibility.seed_study (L4680); F-17
B_SIM = 2000                                   # simulated critical values for Z2
MIN_YEARS = 10                                 # L1747 (1); = vol_target.estimator_gate.fit.min_years
REFIT_EVERY = 21                               # fit.refit_every_origins
MIN_POOL = 252                                 # residuals before the first FHS / EVT origin (M3 convention)
THRESHOLD_SHARE = 0.10                         # GPD on the lower 10 % of standardised residuals
MIN_EXCEEDANCES = 50                           # fail closed below (brief B.2)
VAR_LEVELS = (0.95, 0.99)
ES_LEVEL = 0.975
FAN_H = (21, 126)
FAN_PATHS = 2000
FAN_DRIFT = {"drift": "premium", "rf_rate": 0.03, "erp": 0.04}   # the page default view (run_monte_carlo defaults)
BASEL_WINDOW = 250
DECILES = tuple(k / 10.0 for k in range(1, 10))
PATH_COLOUR_LABEL = "path-vol quartile"        # L1747 (3): the only caption for a conditional-vol path colouring
R06_LABELS = ("calm", "normal", "elevated", "stressed")   # reserved for the R-06 display labels, never on lab paths
PERIODS: Mapping[str, tuple[str, Optional[str]]] = {"2016-26": ("2016-01-01", None), "2026": ("2026-01-01", None)}  # F-13
GATE = {"var99_kupiec_p_min": 0.05, "var99_cc_p_min": 0.05, "es975_z2_reject_level": 0.05,
        "fan_pit_h21_chi2_p_min": 0.01, "min_origins": 200, "min_fan_origins": 20}   # I-11 (thresholds: default, judgment)
REPORTED_NOT_GATED = ("fan_pit_h126", "period_2026")
LAB_CONFIG = {                                 # proposed quant_lab block (brief C.2); NOT in the store, spec silent
    "fit": {"window": "expanding", "min_years": MIN_YEARS, "refit_every_origins": REFIT_EVERY},
    "tails": {"fhs": True, "evt": {"dist": "gpd", "side": "lower", "threshold_share": THRESHOLD_SHARE, "method": "mcneil_frey"}},
    "envelope": "max(fast_fhs, gjr_evt)",
    "lines": {"var_levels": list(VAR_LEVELS), "es_level": ES_LEVEL, "es_test": "z2_simulated_critical_values",
              "basel_zones": True, "fan_pit_h": list(FAN_H),
              "fan_model": {"model": "garch_t", "fit": "expanding", "n_paths": FAN_PATHS, **FAN_DRIFT}},
    "report_periods": list(PERIODS), "post_holiday": {"reported_separately": True, "var_display_scale": "sqrt(max(n_US, 1))"},
    "acceptance": {"sample": "oos_2016_26", **{k: v for k, v in GATE.items() if k.endswith(("_min", "_level"))},
                   "reported_not_gated": list(REPORTED_NOT_GATED)},
    "path_colour_label": PATH_COLOUR_LABEL, "outputs": "descriptive", "source": "core.quant.lab.LAB_CONFIG (module constant)",
}


# --------------------------------------------------------------------------- #
# Result types (every one carries acts = False)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LabFit:
    model: str
    fit: Any
    n_obs: int
    first_date: Optional[str]
    last_date: Optional[str]
    status: str                      # ok | insufficient_history | fit_failed
    reason: Optional[str] = None
    acts: bool = False


@dataclass(frozen=True)
class GpdFit:
    xi: float
    beta: float
    u: float
    k: int
    n: int
    ok: bool
    reason: str = ""
    acts: bool = False


@dataclass(frozen=True)
class TailLine:
    model: str                       # fast_fhs | gjr_evt | envelope | ...
    var95: np.ndarray = field(repr=False)
    var99: np.ndarray = field(repr=False)
    var975: np.ndarray = field(repr=False)
    es975: np.ndarray = field(repr=False)
    ok: np.ndarray = field(repr=False)
    status: str = "ok"               # ok | insufficient_history | evt_fit_failed
    reason: str = ""
    sigma: Optional[np.ndarray] = field(default=None, repr=False)     # the model's sigma_next (Z2 simulation scale)
    fit: Any = None                  # the final GpdFit of an EVT line
    acts: bool = False


@dataclass(frozen=True)
class Replay:
    replay_id: str
    market: str
    start: str                       # return dates, inclusive (F-19)
    end: str


@dataclass(frozen=True)
class ReplayResult:
    replay_id: str
    dates: tuple
    n_sessions: int
    index_return: float
    index_path: np.ndarray = field(repr=False)
    book_return: Optional[float] = None
    book_path: Optional[np.ndarray] = field(default=None, repr=False)
    max_dd: float = float("nan")
    worst_day: tuple = ()
    regime: dict = field(default_factory=dict)      # {"at_start": tags, "changes": [...]}; never a "current regime"
    unmapped: tuple = ()
    status: str = "ok"               # ok | missing_input
    reason: str = ""
    repro: dict = field(default_factory=dict)
    acts: bool = False


@dataclass(frozen=True)
class LabContext:
    """Everything `grade_lab` needs besides the series; no clock is read anywhere (T-REPRO-01c)."""
    seed: int = SEED
    knowledge_utc: Optional[str] = None
    config_hash: Optional[str] = None
    package_version: str = ""
    git_hash: str = GIT_HASH
    min_years: float = MIN_YEARS
    refit_every: int = REFIT_EVERY
    B: int = B_SIM
    periods: Mapping[str, tuple[str, Optional[str]]] = field(default_factory=lambda: dict(PERIODS))
    fan_h: tuple = FAN_H
    gap_sessions: Optional[np.ndarray] = field(default=None, repr=False)   # n_US per close, aligned with the closes
    labels: Optional[np.ndarray] = field(default=None, repr=False)         # R-06 display_label_rel per close (causal)
    gjr_fitter: Optional[Callable] = None     # test hook, as vol_estimators.gjr_t allows
    gpd_fitter: Optional[Callable] = None     # test hook (an injected GpdFit)
    label: str = ""                           # "SMOKE: ..." / "FIXTURE: ..." (rulings section 1)
    fan_paths: int = FAN_PATHS


@dataclass(frozen=True)
class LabGrade:
    market: str
    model: str                       # envelope, or fast_fhs when the envelope is withheld
    components: tuple
    var99: dict
    es975: dict
    fan_pit_h21: dict
    h126_reported: dict
    y2026_reported: dict
    verdict: str                     # PASS | FAIL | NOT_RUN
    lines: tuple
    var95: dict = field(default_factory=dict)
    basel: dict = field(default_factory=dict)
    post_holiday: dict = field(default_factory=dict)
    per_label: dict = field(default_factory=dict)
    gate: dict = field(default_factory=dict)
    report: dict = field(default_factory=dict, repr=False)
    repro: dict = field(default_factory=dict)
    note: str = ""
    acts: bool = False
    var_1d: dict = field(default_factory=dict)   # the latest 1-day line; numbers None unless every component passes B5


RESULT_TYPES = (LabFit, GpdFit, TailLine, ReplayResult, LabGrade)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float).reshape(-1)


def _nan(T: int) -> np.ndarray:
    return np.full(T, np.nan)


def data_snapshot_md5(dates: Sequence[str], values) -> str:
    """md5 of the input arrays (brief B.6: the snapshot id of a lab run on a loaded series)."""
    h = hashlib.md5()
    h.update("\n".join(str(d) for d in dates).encode("utf-8"))
    h.update(np.ascontiguousarray(_arr(values)).tobytes())
    return h.hexdigest()


def repro_record(ctx: LabContext, dates, values) -> dict:
    return {"seed": int(ctx.seed), "config_hash": ctx.config_hash, "data_snapshot_id": data_snapshot_md5(dates, values),
            "package_version": ctx.package_version, "git_hash": ctx.git_hash, "knowledge_utc": ctx.knowledge_utc}


def has_min_history(dates: Sequence[str], t: int, *, min_years: float = MIN_YEARS) -> bool:
    """True iff dates[0]..dates[t] spans at least `min_years` calendar years (F-3) AND holds at least
    `min_years` x 252 observations (M3 `vol_estimators` floor): the stricter reading on gappy vendor series."""
    if t < 0 or t >= len(dates) or t + 1 < round(min_years * E.TRADING_DAYS):
        return False
    y0, m0, d0 = (int(p) for p in str(dates[0])[:10].split("-"))
    y1, m1, d1 = (int(p) for p in str(dates[t])[:10].split("-"))
    return (y1 - y0) + ((m1, d1) >= (m0, d0)) - 1 >= min_years


# --------------------------------------------------------------------------- #
# Rule (1): expanding fits
# --------------------------------------------------------------------------- #
def lab_fit(returns, dates: Sequence[str], *, model: str = "gjr_t", min_years: float = MIN_YEARS) -> LabFit:
    """The interactive fit on ALL returns through the last date (expanding, never a trailing 504 window).
    Fewer than `min_years` calendar years -> `insufficient_history` (never presented as calibrated; F-4)."""
    if model not in ("garch_t", "gjr_t"):
        raise ValueError("model must be 'garch_t' or 'gjr_t'")
    r = _arr(returns)
    n = int(r.size)
    first, last = (str(dates[0]), str(dates[-1])) if len(dates) else (None, None)
    if n != len(dates):
        raise ValueError(f"{n} returns but {len(dates)} dates")
    if n == 0 or not has_min_history(dates, n - 1, min_years=min_years):
        return LabFit(model, None, n, first, last, "insufficient_history",
                      f"fit window {n} sessions < {min_years:g} years (R-16): regime-captured, not graded")
    try:
        if model == "garch_t":
            from core.quant.garch import fit_garch
            fit = fit_garch(r, dist="t")
        else:
            from core.quant.gjr import fit_gjr
            fit = fit_gjr(r, dist="t")
    except Exception as exc:                                     # a failed fit is reported, never substituted
        return LabFit(model, None, n, first, last, "fit_failed", f"{type(exc).__name__}: {exc}")
    ok, why = E.fit_ok(fit)
    return LabFit(model, fit, n, first, last, "ok" if ok else "fit_failed", why)


def sma20_sigma(r_simple) -> np.ndarray:
    """fast-FHS sigma_next[t]: SMA20 on simple returns (M2 `sma_vol` == `vol_estimators.sma`), daily units."""
    fc = E.sma(_arr(r_simple), 1)
    return np.sqrt(np.where(fc.ok & (fc.var > 0), fc.var, np.nan))


def gjr_sigma(r, h: int = 1, *, min_years: float = MIN_YEARS, refit_every: int = REFIT_EVERY, fitter=None) -> np.ndarray:
    """sqrt of M3's expanding GJR-t h-day variance forecast (NaN where the fit is absent or outside R-30 bounds)."""
    fc = E.gjr_t(_arr(r), h, min_years=min_years, refit_every=refit_every, fitter=fitter)
    return np.sqrt(np.where(fc.ok & (fc.var > 0), fc.var, np.nan))


# --------------------------------------------------------------------------- #
# Rule (1), (3): tails and the envelope
# --------------------------------------------------------------------------- #
def fhs_tail(r, sigma_next, *, min_pool: int = MIN_POOL, model: str = "fast_fhs", pool_sigma=None) -> TailLine:
    """Filtered historical simulation, 1-day ahead, expanding residual pool (docstring conventions). `pool_sigma`
    (default `sigma_next`) standardises the pool, so a test can mis-specify the out-of-sample forecast alone (M3 F-16)."""
    r, sig = _arr(r), _arr(sigma_next)
    psig = sig if pool_sigma is None else _arr(pool_sigma)
    T = r.size
    if sig.size != T or psig.size != T:
        raise ValueError("sigma_next must align with r")
    v95, v99, v975, es = _nan(T), _nan(T), _nan(T), _nan(T)
    ok = np.zeros(T, dtype=bool)
    pool = _Pool()
    for t in range(T):
        if t >= 1 and math.isfinite(r[t]) and psig[t - 1] > 0:
            pool.add(r[t] / psig[t - 1])
        if len(pool) < min_pool or not (sig[t] > 0):
            continue
        q05, q01, q025 = pool.quantile(0.05), pool.quantile(0.01), pool.quantile(0.025)
        v95[t], v99[t], v975[t] = -sig[t] * q05, -sig[t] * q01, -sig[t] * q025
        es[t], ok[t] = -sig[t] * pool.tail_mean(q025), True
    status = "ok" if ok.any() else "insufficient_history"
    return TailLine(model, v95, v99, v975, es, ok, status, "" if ok.any() else f"fewer than {min_pool} residuals", sig)


def gpd_tail(z, *, threshold_share: float = THRESHOLD_SHARE, min_exceedances: int = MIN_EXCEEDANCES) -> GpdFit:
    """McNeil-Frey step 2 on the lower tail of standardised residuals: losses x = -z, k = floor(share n),
    u = the (k+1)-th largest loss, GPD(xi, beta) by ML on the exceedances. Fails closed (ok = False) on k < 50,
    a non-finite fit, beta <= 0 or xi >= 1 (infinite mean)."""
    x = -_arr(z)
    x = x[np.isfinite(x)]
    n = int(x.size)
    k = int(math.floor(threshold_share * n))
    if k < min_exceedances:
        return GpdFit(math.nan, math.nan, math.nan, k, n, False, f"k={k} exceedances < {min_exceedances}")
    xs = np.sort(x)[::-1]
    u = float(xs[k])
    y = xs[:k] - u
    y = y[y > 0]
    if y.size < min_exceedances:
        return GpdFit(math.nan, math.nan, u, k, n, False, f"{y.size} positive exceedances < {min_exceedances} (ties at u)")
    try:
        xi, _loc, beta = sps.genpareto.fit(y, floc=0)
    except Exception as exc:
        return GpdFit(math.nan, math.nan, u, k, n, False, f"gpd fit error: {type(exc).__name__}")
    xi, beta = float(xi), float(beta)
    if not (math.isfinite(xi) and math.isfinite(beta)) or beta <= 0:
        return GpdFit(xi, beta, u, k, n, False, "non-finite GPD fit")
    if xi >= 1.0:
        return GpdFit(xi, beta, u, k, n, False, f"xi={xi:.3f} >= 1: infinite tail mean")
    return GpdFit(xi, beta, u, k, n, True)


def gpd_quantile(f: GpdFit, q: float) -> float:
    """Loss quantile at level q (q > 1 - k/n) in standardised units."""
    p = (1.0 - q) / (f.k / f.n)
    if abs(f.xi) < 1e-8:
        return f.u - f.beta * math.log(p)
    return f.u + f.beta / f.xi * (p ** (-f.xi) - 1.0)


def gpd_es(f: GpdFit, q: float) -> float:
    xq = gpd_quantile(f, q)
    return xq / (1.0 - f.xi) + (f.beta - f.xi * f.u) / (1.0 - f.xi)


def evt_tail(r, sigma_next, mu: float = 0.0, *, threshold_share: float = THRESHOLD_SHARE, refit_every: int = REFIT_EVERY,
             min_pool: int = MIN_POOL, gpd_fitter: Optional[Callable] = None, model: str = "gjr_evt") -> TailLine:
    """McNeil-Frey two-step line: `sigma_next` from the expanding GJR-t fit (`gjr_sigma`), GPD refit every
    `refit_every` origins on the residual pool through t. `gpd_fitter(z) -> GpdFit` is a test hook."""
    r, sig = _arr(r), _arr(sigma_next)
    T = r.size
    if sig.size != T:
        raise ValueError("sigma_next must align with r")
    fitter = gpd_fitter or (lambda z: gpd_tail(z, threshold_share=threshold_share))
    v95, v99, v975, es = _nan(T), _nan(T), _nan(T), _nan(T)
    ok = np.zeros(T, dtype=bool)
    pool: list = []
    fit: Optional[GpdFit] = None
    since, reason = refit_every, ""
    for t in range(T):
        if t >= 1 and math.isfinite(r[t]) and sig[t - 1] > 0:
            pool.append(r[t] / sig[t - 1])
        if len(pool) < min_pool or not (sig[t] > 0):
            continue
        if since >= refit_every:
            fit, since = fitter(np.asarray(pool)), 0
        since += 1
        if fit is not None and fit.ok:
            v95[t], v99[t], v975[t] = (sig[t] * gpd_quantile(fit, q) - mu for q in (0.95, 0.99, 0.975))
            es[t], ok[t] = sig[t] * gpd_es(fit, 0.975) - mu, True
        else:
            reason = fit.reason if fit is not None else "no fit"
    if ok.any():
        status, reason = "ok", ""
    else:
        status = "evt_fit_failed" if fit is not None else "insufficient_history"
        reason = reason or f"fewer than {min_pool} residuals"
    return TailLine(model, v95, v99, v975, es, ok, status, reason, sig, fit)


def envelope(a: TailLine, b: TailLine) -> TailLine:
    """max(fast FHS, GJR-EVT) elementwise in loss units; ok where both legs are ok (L1747 (3)). The caller withholds
    the envelope when a leg has no ok origin (`status` != ok) and shows the other leg alone, labelled."""
    ok = a.ok & b.ok
    mx = lambda x, y: np.where(ok, np.maximum(x, y), np.nan)      # noqa: E731
    status = "ok" if ok.any() else (b.status if b.status != "ok" else a.status)
    reason = "" if ok.any() else (b.reason or a.reason)
    return TailLine("envelope", mx(a.var95, b.var95), mx(a.var99, b.var99), mx(a.var975, b.var975), mx(a.es975, b.es975),
                    ok, status, reason, b.sigma if b.sigma is not None else a.sigma, b.fit)


def display_scale(gap_sessions) -> np.ndarray:
    """sqrt(max(n_US, 1)) per session (R-10 L1631; F-28); None -> ones."""
    g = _arr(gap_sessions)
    return np.sqrt(np.maximum(np.where(np.isfinite(g), g, 0.0), 1.0))


# --------------------------------------------------------------------------- #
# Rule (3): grading lines
# --------------------------------------------------------------------------- #
def grade_var(returns, forecasts, q: float = 0.99) -> dict:
    """Kupiec and Christoffersen (validate.kupiec / christoffersen) on `hit = returns < -forecasts`, plus the mean
    tick loss at alpha = 1 - q. `returns[i]` is the realisation `forecasts[i]` was made for; NaN forecasts drop."""
    x, v = _arr(returns), _arr(forecasts)
    if x.size != v.size:
        raise ValueError("returns and forecasts must align")
    m = np.isfinite(x) & np.isfinite(v)
    x, v = x[m], v[m]
    alpha = 1.0 - q
    hits = x < -v
    k, c = V.kupiec(hits, alpha), V.christoffersen(hits, alpha)
    tl = float(np.mean(tick_loss(x, -v, alpha))) if x.size else math.nan
    return {"q": q, "n": k["n"], "x": k["x"], "rate": k["rate"], "kupiec_p": k["p"], "ind_p": c["p_ind"], "cc_p": c["p_cc"],
            "tick_loss": tl}


def es_z2(returns, es_forecasts, q: float = 0.975, B: int = B_SIM, seed: int = SEED, *, var_forecasts, scale=None,
          z_pool=None, gpd: Optional[GpdFit] = None) -> dict:
    """Acerbi-Szekely Z2 = sum_t x_t I_t / (n alpha ES_t) + 1, I_t = 1{x_t < -VaR_t}, alpha = 1 - q (negative = risk
    understated). Simulated critical values: p = share of `B` simulated Z2 at or below the observed one.
    Simulation law (stated; F-31), under H0 "the model's predictive law is right": x*_t = scale_t z*, z* iid from
    `z_pool`, where `scale` is the MODEL's own sigma_next (the line's, never the true or another model's) and
    `z_pool` the model's standardised-residual pool (default: {x_s / scale_s} of the graded sample; `scale` defaults
    to the ES forecasts, a scale-free fallback). With `gpd` (the line's final GpdFit), every draw whose loss -z*
    exceeds the threshold u is replaced by u + a GPD(xi, beta) exceedance: the McNeil-Frey predictive law (empirical
    body, GPD lower tail). `seed` -> numpy PCG64 through default_rng; never the clock."""
    alpha = 1.0 - q
    x, es, var = _arr(returns), _arr(es_forecasts), _arr(var_forecasts)
    sc = es if scale is None else _arr(scale)
    if not (x.size == es.size == var.size == sc.size):
        raise ValueError("returns, es_forecasts, var_forecasts and scale must align")
    m = np.isfinite(x) & np.isfinite(es) & np.isfinite(var) & np.isfinite(sc) & (es > 0) & (var > 0) & (sc > 0)
    x, es, var, sc = x[m], es[m], var[m], sc[m]
    n = int(x.size)
    law = "x*_t = scale_t z*, z* iid from the residual pool" + ("; losses beyond u redrawn from GPD(xi, beta)" if gpd and gpd.ok else "")
    out = {"q": q, "alpha": alpha, "n": n, "B": int(B), "seed": int(seed), "law": law, "z2": math.nan, "p": math.nan,
           "rejected_5pct": None}
    if n < 20:
        return out
    z2 = float(np.sum(x * (x < -var) / (n * alpha * es)) + 1.0)
    z = _arr(z_pool) if z_pool is not None else x / sc
    z = z[np.isfinite(z)]
    if z.size < 20:
        return out
    rng = np.random.default_rng(seed)
    sims = np.empty(B)
    chunk = max(1, min(B, int(4e6 // max(n, 1))))
    for a in range(0, B, chunk):
        k = min(chunk, B - a)
        zs = rng.choice(z, size=(k, n), replace=True)
        if gpd is not None and gpd.ok:
            tail = -zs > gpd.u
            cnt = int(tail.sum())
            if cnt:
                zs[tail] = -(gpd.u + sps.genpareto.rvs(gpd.xi, scale=gpd.beta, size=cnt, random_state=rng))
        xs = sc * zs
        sims[a:a + k] = np.sum(xs * (xs < -var) / (n * alpha * es), axis=1) + 1.0
    p = float(np.mean(sims <= z2))
    out.update(z2=z2, p=p, rejected_5pct=bool(p < GATE["es975_z2_reject_level"]))
    return out


def basel_zone(breaches: int, n: int, *, window: int = BASEL_WINDOW) -> str:
    """Basel traffic-light zone of `breaches` 99 % exceptions over `n` origins: green <= 4, yellow <= 9, red above,
    the counts of a 250-origin window (validate.traffic_light); another n scales the thresholds by n/250 (reading)."""
    if n <= 0:
        return "NOT_RUN"
    x = breaches * window / n
    return "green" if x <= 4 else "yellow" if x <= 9 else "red"


def basel_windows(hits99, *, window: int = BASEL_WINDOW) -> dict:
    """Last-250-origin zone (validate.traffic_light) plus the zone counts over non-overlapping 250-origin windows
    (F-10: the pilot's "Basel red 0 / yellow 2" is a count of windows)."""
    h = np.asarray(hits99, dtype=bool)
    n = int(h.size)
    counts = {"green": 0, "yellow": 0, "red": 0}
    for a in range(0, n - window + 1, window):
        counts[basel_zone(int(h[a:a + window].sum()), window)] += 1
    return {"last_250": V.traffic_light(h, window) if n >= window else None, "windows": counts, "n_windows": n // window}


def fan_origins(dates: Sequence[str], h: int, *, start: Optional[str] = None, min_years: float = MIN_YEARS) -> list[int]:
    """Non-overlapping origins (every h sessions) from the first origin on or after `start` with `min_years` of
    history behind it, while R_{t->t+h} is still realised."""
    out: list[int] = []
    nxt = 0
    for t in range(len(dates) - h):
        if t >= nxt and (start is None or str(dates[t]) >= start) and has_min_history(dates, t, min_years=min_years):
            out.append(t)
            nxt = t + h
    return out


def garch_fan_quantiles(r, h: int, origins: Sequence[int], *, n_paths: int = FAN_PATHS, seed: int = SEED,
                        drift: str = FAN_DRIFT["drift"], rf_rate: float = FAN_DRIFT["rf_rate"],
                        erp: float = FAN_DRIFT["erp"], levels: tuple = DECILES, fits: Optional[dict] = None) -> np.ndarray:
    """(T, 9) deciles of the h-day forward log return of the lab's default fan model at each origin t (NaN rows
    elsewhere): montecarlo's `garch_t` paths, i.e. GARCH(1,1)-t fitted on r[:t+1] (expanding) and
    `garch.simulate_returns(fit, seed=seed)` with the drift resolved as `run_monte_carlo` does. A fit that raises
    leaves its row NaN (no fan there). `fits` caches the fit per origin across horizons."""
    from core.quant.garch import fit_garch, simulate_returns
    from core.quant.montecarlo import TRADING_DAYS, resolve_drift
    r = _arr(r)
    Q = np.full((r.size, len(levels)), np.nan)
    fits = {} if fits is None else fits
    for t in origins:
        x = r[:t + 1]
        if t not in fits:
            try:
                fits[t] = fit_garch(x, dist="t")                       # the exact run_monte_carlo call
            except ValueError:
                fits[t] = None
        if fits[t] is None:
            continue
        kind, value = resolve_drift(drift, sample_mu=float(np.mean(x)) * TRADING_DAYS, rf_rate=rf_rate, erp=erp)
        daily = value / TRADING_DAYS
        ret, _ = simulate_returns(fits[t], n_paths=n_paths, horizon=h, seed=seed,
                                  drift_daily=daily if kind == "log" else None, rate_daily=daily if kind == "rate" else None)
        Q[t] = np.quantile(ret.sum(axis=1), levels)
    return Q


def fan_pit(returns, fan_quantiles, h: int, *, levels: tuple = DECILES) -> dict:
    """Fan PIT at horizon h, chi-square on 10 equal bins at non-overlapping origins (every h sessions): the bin of
    the realised h-day log return R_{t->t+h} is the number of decile quantiles below it. `fan_quantiles[t]` are the
    nine deciles of the fan at origin t (NaN rows carry no fan)."""
    r, Q = _arr(returns), np.asarray(fan_quantiles, dtype=float)
    T = r.size
    if Q.shape != (T, len(levels)):
        raise ValueError(f"fan_quantiles must be ({T}, {len(levels)})")
    if not np.all(np.diff(levels) > 0) or len(levels) != 9:
        raise ValueError("levels must be the nine deciles")
    cum = np.concatenate([[0.0], np.cumsum(r)])
    bins, origins, nxt = [], [], None
    for t in range(T - h):
        if not np.all(np.isfinite(Q[t])):
            continue
        if nxt is not None and t < nxt:
            continue
        nxt = t + h
        R = cum[t + h + 1] - cum[t + 1]
        bins.append(int(np.sum(R > Q[t])))
        origins.append(t)
    n = len(bins)
    counts = np.bincount(np.asarray(bins, dtype=int), minlength=10) if n else np.zeros(10, dtype=int)
    p = float(sps.chisquare(counts).pvalue) if n >= GATE["min_fan_origins"] else math.nan
    return {"h": int(h), "n_origins": n, "chi2_p": p, "counts": counts.tolist(), "overlap": False,
            "origins": np.asarray(origins, dtype=int)}


def _period_mask(dates: np.ndarray, lo: Optional[str], hi: Optional[str]) -> np.ndarray:
    m = np.ones(dates.size, dtype=bool)
    if lo:
        m &= dates >= lo
    if hi:
        m &= dates <= hi
    return m


def grade_line(r, dates: Sequence[str], line: TailLine, *, periods: Mapping = PERIODS, gap_sessions=None, labels=None,
               B: int = B_SIM, seed: int = SEED, fans: Optional[Mapping[int, dict]] = None, z_pool=None,
               gpd: Optional[GpdFit] = None, scale=None) -> dict:
    """The self-grading report of one tail line (brief B.3 shape): per period Kupiec / Christoffersen at 95 % and
    99 %, ES 97.5 % Z2, Basel zones, tick loss; post-holiday buckets (n_US 1 / 2 / >= 3) unscaled and scaled;
    per-R-06-label coverage; the fan PIT lines passed in `fans`; and the M9 gate. The 99 % / 97.5 % series graded
    are the displayed ones (x sqrt(max(n_US, 1)); F-29); the unscaled breach rates are printed beside them."""
    r = _arr(r)
    T = r.size
    d = np.asarray([str(x)[:10] for x in dates])
    if d.size != T:
        raise ValueError("dates must align with r")
    x, dd = r[1:], d[1:]                                           # the realisation of origin t is r[t+1]
    ok = line.ok[:-1] & np.isfinite(x)
    g = display_scale(gap_sessions[1:]) if gap_sessions is not None else np.ones(T - 1)
    nus = _arr(gap_sessions)[1:] if gap_sessions is not None else None
    v95, v99, v975, es = (a[:-1] * g for a in (line.var95, line.var99, line.var975, line.es975))
    sc = (scale if scale is not None else line.sigma)
    sc = _arr(sc)[:-1] if sc is not None else None

    def _period(m) -> dict:
        n = int(m.sum())
        out = {"n": n, "var95": grade_var(x[m], v95[m], 0.95), "var99": grade_var(x[m], v99[m], 0.99),
               "es975": es_z2(x[m], es[m], ES_LEVEL, B, seed, var_forecasts=v975[m], scale=None if sc is None else sc[m],
                              z_pool=z_pool, gpd=gpd)}
        out["basel"] = basel_windows(x[m] < -v99[m])
        out["tick_loss"] = {"var95": out["var95"]["tick_loss"], "var99": out["var99"]["tick_loss"]}
        out["unscaled"] = {"var95_rate": grade_var(x[m], (line.var95[:-1])[m], 0.95)["rate"],
                           "var99_rate": grade_var(x[m], (line.var99[:-1])[m], 0.99)["rate"]}
        return out

    report: dict[str, Any] = {"model": line.model, "status": line.status, "reason": line.reason, "returns": "log",
                              "acts": False, "n_ok": int(ok.sum()), "periods": {}}
    for name, (lo, hi) in periods.items():
        report["periods"][name] = _period(ok & _period_mask(dd, lo, hi))
    post = {}
    if nus is not None:
        for key, m in (("n_us_1", nus == 1), ("n_us_2", nus == 2), ("n_us_ge3", nus >= 3)):
            mm = ok & m
            post[key] = {"n": int(mm.sum()),
                         "var95_rate_unscaled": grade_var(x[mm], (line.var95[:-1])[mm], 0.95)["rate"],
                         "var95_rate_scaled": grade_var(x[mm], v95[mm], 0.95)["rate"],
                         "var99_rate_unscaled": grade_var(x[mm], (line.var99[:-1])[mm], 0.99)["rate"],
                         "var99_rate_scaled": grade_var(x[mm], v99[mm], 0.99)["rate"]}
    report["post_holiday"] = post
    per = {}
    if labels is not None:
        lab = np.asarray(labels, dtype=object)[1:]
        for name in R06_LABELS:
            mm = ok & (lab == name)
            gv = grade_var(x[mm], v95[mm], 0.95)
            per[name] = {"n": gv["n"], "var95_rate": gv["rate"], "kupiec_p": gv["kupiec_p"], "tick_loss": gv["tick_loss"]}
    report["per_label"] = per
    fans = dict(fans or {})
    report["fan_pit"] = {"h21": fans.get(21), "h126": fans.get(126)}
    report["gate"] = m9_gate(report)
    return report


def m9_gate(report: Mapping, *, period: str = "2016-26") -> dict:
    """I-11 (L5701): PASS iff 2016-26 99 % VaR Kupiec p >= 0.05 and CC p >= 0.05, ES 97.5 % Z2 p >= 0.05 and fan PIT
    chi-square p >= 0.01 at h = 21; NOT_RUN when any line is missing / NaN or n < 200 (never a pass); else FAIL.
    "2026" and h = 126 are never read here (reported, not gated)."""
    L = (report.get("periods") or {}).get(period)
    Fh = (report.get("fan_pit") or {}).get("h21")
    lines = {"var99_kupiec_p": None, "var99_cc_p": None, "es975_z2_p": None, "fan_pit_h21_chi2_p": None}
    n = n_fan = 0
    if L:
        lines["var99_kupiec_p"] = L["var99"]["kupiec_p"]
        lines["var99_cc_p"] = L["var99"]["cc_p"]
        lines["es975_z2_p"] = L["es975"]["p"]
        n = int(L["n"])
    if Fh:
        lines["fan_pit_h21_chi2_p"] = Fh.get("chi2_p")
        n_fan = int(Fh.get("n_origins") or 0)
    out = {"period": period, "lines": lines, "thresholds": dict(GATE), "reported_not_gated": list(REPORTED_NOT_GATED),
           "n": n, "n_fan_origins": n_fan}
    vals = list(lines.values())
    if any(v is None or not (isinstance(v, (int, float)) and math.isfinite(v)) for v in vals) \
            or n < GATE["min_origins"] or n_fan < GATE["min_fan_origins"]:
        out["status"] = "NOT_RUN"
        return out
    ok = (lines["var99_kupiec_p"] >= GATE["var99_kupiec_p_min"] and lines["var99_cc_p"] >= GATE["var99_cc_p_min"]
          and lines["es975_z2_p"] >= GATE["es975_z2_reject_level"]
          and lines["fan_pit_h21_chi2_p"] >= GATE["fan_pit_h21_chi2_p_min"])
    out["status"] = "PASS" if ok else "FAIL"
    return out


# --------------------------------------------------------------------------- #
# grade_lab: the whole lab line on one series
# --------------------------------------------------------------------------- #
def _series(series) -> tuple[list[str], np.ndarray]:
    if hasattr(series, "dates") and hasattr(series, "closes"):
        return [str(x)[:10] for x in series.dates], _arr(series.closes)
    dates, closes = series
    return [str(x)[:10] for x in dates], _arr(closes)


def _line_text(name: str, P: dict, gated: bool) -> list[str]:
    tag = "gated" if gated else "reported, not gated"
    v99, v95, z = P["var99"], P["var95"], P["es975"]
    return [f"{name} ({tag}; n {P['n']}): 95% VaR breaches {v95['rate']:.2%} Kupiec p {v95['kupiec_p']:.3f} CC p {v95['cc_p']:.3f}",
            f"{name} ({tag}): 99% VaR breaches {v99['rate']:.2%} Kupiec p {v99['kupiec_p']:.3f} CC p {v99['cc_p']:.3f}",
            f"{name} ({tag}): ES 97.5% Z2 {z['z2']:+.3f} p {z['p']:.3f} ({ {True: 'rejected', False: 'not rejected'}.get(z['rejected_5pct'], 'not computed') } at 5%; {z['B']} simulated)",
            f"{name}: Basel last 250 {P['basel']['last_250']}; windows green {P['basel']['windows']['green']} / "
            f"yellow {P['basel']['windows']['yellow']} / red {P['basel']['windows']['red']}"]


def grade_lab(market: str, series, ctx: LabContext = LabContext()) -> LabGrade:
    """fast FHS + GJR-EVT -> envelope -> grading report -> M9 gate on one close series `(dates, closes)` (or an object
    with `.dates` / `.closes`). Components are graded beside the envelope. An EVT leg with no ok origin withholds the
    envelope: fast FHS is graded alone and the reason is recorded (never a one-legged "envelope")."""
    dates, closes = _series(series)
    if closes.size < 2:
        raise ValueError("a series needs at least two closes")
    r_log = np.diff(np.log(closes))
    r_simple = closes[1:] / closes[:-1] - 1.0
    rdates = dates[1:]
    gaps = None if ctx.gap_sessions is None else _arr(ctx.gap_sessions)[1:]
    labels = None if ctx.labels is None else np.asarray(ctx.labels, dtype=object)[1:]
    fast = fhs_tail(r_log, sma20_sigma(r_simple), model="fast_fhs")
    sig_gjr = gjr_sigma(r_log, 1, min_years=ctx.min_years, refit_every=ctx.refit_every, fitter=ctx.gjr_fitter)
    evt = evt_tail(r_log, sig_gjr, refit_every=ctx.refit_every, gpd_fitter=ctx.gpd_fitter)
    note = ""
    if evt.ok.any():
        line, components = envelope(fast, evt), ("fast_fhs", "gjr_evt")
        z_pool = (r_log[1:] / sig_gjr[:-1])
        z_pool = z_pool[np.isfinite(z_pool)]
        scale, gpd = sig_gjr, evt.fit
    else:
        line, components = fast, ("fast_fhs",)
        note = f"envelope withheld: GJR-EVT {evt.status} ({evt.reason}); fast FHS shown alone"
        z_pool, scale, gpd = None, None, None
    fans, fits = {}, {}
    first, _ = ctx.periods.get("2016-26", ("2016-01-01", None))
    for h in ctx.fan_h:
        origins = fan_origins(rdates, h, start=first, min_years=ctx.min_years)
        Q = garch_fan_quantiles(r_log, h, origins, n_paths=ctx.fan_paths, seed=ctx.seed, fits=fits)
        fans[h] = fan_pit(r_log, Q, h)
        fans[h].update(period="2016-26", model="garch_t", n_paths=ctx.fan_paths, **FAN_DRIFT)
        fans[h].pop("origins", None)
    common = dict(periods=ctx.periods, gap_sessions=gaps, labels=labels, B=ctx.B, seed=ctx.seed)
    report = grade_line(r_log, rdates, line, fans=fans, z_pool=z_pool, gpd=gpd, scale=scale, **common)
    if note:                                    # the gate's subject is the envelope: withheld -> no verdict
        report["gate"] = dict(report["gate"], status="NOT_RUN", reason=note)
    b5s = {"fast_fhs": b5(r_log, fast.sigma, form="fhs")["status"],
           "gjr_evt": b5(r_log, sig_gjr, form="fhs")["status"] if evt.ok.any() else "NOT_RUN"}
    sc = float(display_scale(gaps)[-1]) if gaps is not None else 1.0
    shown = bool(line.ok[-1]) and not note and all(s == "PASS" for s in b5s.values())
    var_1d = {"origin": rdates[-1], "model": line.model, "scale": sc, "b5": b5s, "displayable": shown,
              **{k: float(getattr(line, k)[-1] * sc) if shown else None for k in ("var95", "var99", "es975")},
              "reason": "" if shown else "withheld: 1-day VaR only from components that pass 1-day B5 (L1747 (2))"
              + (f"; {note}" if note else "")}
    report["var_1d"] = var_1d
    report["components_lines"] = {"fast_fhs": grade_line(r_log, rdates, fast, **common)["periods"]}
    if evt.ok.any():
        report["components_lines"]["gjr_evt"] = grade_line(r_log, rdates, evt, z_pool=z_pool, gpd=gpd, scale=scale,
                                                           **common)["periods"]
    else:
        report["components_lines"]["gjr_evt"] = {"status": evt.status, "reason": evt.reason}
    report.update(market=market, components=list(components), note=note, label=ctx.label, config=LAB_CONFIG,
                  repro=repro_record(ctx, dates, closes), path_colour_label=PATH_COLOUR_LABEL)
    gate = report["gate"]
    P16, P26 = report["periods"].get("2016-26"), report["periods"].get("2026")
    lines: list[str] = [f"model {line.model} = {' / '.join(components)}; expanding GJR fit >= {ctx.min_years:g} years, "
                        f"refit every {ctx.refit_every} origins; returns log" + (f"; {note}" if note else "")]
    if P16:
        lines += _line_text("2016-26", P16, True)
    if fans.get(21):
        lines.append(f"fan PIT h21 (gated; garch_t fan, 2016-26 origins, non-overlapping): chi2 p {fans[21]['chi2_p']:.3f} n {fans[21]['n_origins']}")
    if fans.get(126):
        lines.append(f"fan PIT h126 (reported, not gated; garch_t fan): chi2 p {fans[126]['chi2_p']:.3f} n {fans[126]['n_origins']}")
    if P26:
        lines += _line_text("2026", P26, False)
    if gaps is None:
        lines.append("post-holiday buckets: not run (gap_sessions not supplied: KR/US calendars)")
    lines.append(f"1-day VaR ({line.model}): " + (f"95% {var_1d['var95']:.2%} / 99% {var_1d['var99']:.2%} at x{sc:.3f}"
                 if var_1d["displayable"] else var_1d["reason"]) + f"; B5 {b5s}")
    lines.append(f"M9 gate: {gate['status']} " + ", ".join(f"{k} {v if v is None else round(v, 4)}" for k, v in gate["lines"].items()))
    if ctx.label:
        lines.append(ctx.label)
    return LabGrade(market, line.model, components, (P16 or {}).get("var99", {}), (P16 or {}).get("es975", {}),
                    fans.get(21) or {}, fans.get(126) or {}, P26 or {}, gate["status"], tuple(lines),
                    var95=(P16 or {}).get("var95", {}), basel=(P16 or {}).get("basel", {}), post_holiday=report["post_holiday"],
                    per_label=report["per_label"], gate=gate, report=report, repro=report["repro"], note=note,
                    var_1d=var_1d)


def grade_to_json(g: LabGrade) -> dict:
    """The plain-JSON report (`docs/quant_lab/<symbol>.json`); arrays unboxed, non-finite -> null."""
    return _jsonable({"market": g.market, "model": g.model, "components": list(g.components), "verdict": g.verdict,
                      "lines": list(g.lines), "note": g.note, "acts": False, **g.report})


# --------------------------------------------------------------------------- #
# Rule (5): historical replays (regime metadata attached; GMM regimes NOT built, P19)
# --------------------------------------------------------------------------- #
REPLAYS = (Replay("KR-1997-11_12", "KR", "1997-11-01", "1997-12-31"),
           Replay("KR-1998-03_06", "KR", "1998-03-01", "1998-06-30"),
           Replay("KR-2000-04-17", "KR", "2000-04-17", "2000-04-17"),
           Replay("KR-2001-09-12", "KR", "2001-09-12", "2001-09-12"),
           Replay("KR-2008-10", "KR", "2008-10-01", "2008-10-31"),
           Replay("KR-2020-03", "KR", "2020-03-01", "2020-03-31"),
           Replay("KR-2026-03-04", "KR", "2026-03-04", "2026-03-04"),
           Replay("KR-2026-06-23_07-30", "KR", "2026-06-23", "2026-07-30"))   # peak 9,114.55 on 2026-06-22 (L6441)
REPLAY_BY_ID = {rp.replay_id: rp for rp in REPLAYS}


def letf_path_return(R: float, sum_r2: float, L: float, carry: float = 0.0) -> float:
    """R-26 rule 2 (L2806): ln(1 + R_L) = L ln(1 + R) - 1/2 (L^2 - L) sum r^2 - carry; `carry` >= 0 is the cumulative
    financing-plus-fee drag over the path (an input; no default is printed)."""
    return math.exp(L * math.log1p(R) - 0.5 * (L * L - L) * sum_r2 - carry) - 1.0


def replay(rp: Replay, dates: Sequence[str], closes, *, book: Optional[Mapping[str, float]] = None,
           instrument_closes: Optional[Mapping[str, tuple]] = None, regime_tags: Optional[Callable] = None,
           repro: Optional[dict] = None) -> ReplayResult:
    """Replay `rp` on the index closes (`dates`, `closes`) and, when given, on a static book `{instrument: weight}`
    (F-20: current weights held through the window; an instrument absent from `instrument_closes` is listed in
    `unmapped` at zero return, never proxied silently). `regime_tags(market, date) -> dict` (M1) supplies the
    metadata at the window start and every in-window change; a raising callable -> `missing_input`."""
    d = [str(x)[:10] for x in dates]
    px = _arr(closes)
    idx = [i for i, x in enumerate(d) if rp.start <= x <= rp.end]
    rep = dict(repro or {})
    if not idx or idx[0] == 0:
        why = "no sessions in the window" if not idx else f"no close before {d[idx[0]]} (the window's first return needs the prior close)"
        return ReplayResult(rp.replay_id, (), 0, math.nan, np.array([]), status="missing_input", reason=why, repro=rep)
    i0, i1 = idx[0], idx[-1]
    r = px[i0:i1 + 1] / px[i0 - 1:i1] - 1.0
    path = np.cumprod(1.0 + r)
    peak = np.maximum.accumulate(np.concatenate([[1.0], path]))
    max_dd = float(np.min(np.concatenate([[1.0], path]) / peak - 1.0))
    worst = int(np.argmin(r))
    wdates = tuple(d[i0:i1 + 1])
    book_ret = book_path = None
    unmapped: list[str] = []
    if book:
        total = np.zeros(r.size)
        for inst, w in book.items():
            src = (instrument_closes or {}).get(inst)
            if src is None:
                unmapped.append(inst)
                continue
            sd, sp = [str(x)[:10] for x in src[0]], _arr(src[1])
            pos = {x: i for i, x in enumerate(sd)}
            ri = np.zeros(r.size)
            for j, x in enumerate(wdates):
                i = pos.get(x)
                if i is None or i == 0:
                    unmapped.append(f"{inst}@{x}")
                    continue
                ri[j] = sp[i] / sp[i - 1] - 1.0
            total += float(w) * ri
        book_path = np.cumprod(1.0 + total)
        book_ret = float(book_path[-1] - 1.0)
    regime: dict = {}
    status, reason = "ok", ""
    if regime_tags is not None:
        try:
            start = dict(regime_tags(rp.market, _to_date(wdates[0])))
            changes, prev = [], start
            for x in wdates[1:]:
                cur = dict(regime_tags(rp.market, _to_date(x)))
                for k in sorted(set(prev) | set(cur)):
                    if prev.get(k) != cur.get(k):
                        changes.append((x, k, prev.get(k), cur.get(k)))
                prev = cur
            regime = {"at_start": start, "changes": changes}
        except Exception as exc:
            status, reason = "missing_input", f"regime_tags: {type(exc).__name__}: {exc}"
    return ReplayResult(rp.replay_id, wdates, int(r.size), float(path[-1] - 1.0), path, book_ret, book_path, max_dd,
                        (wdates[worst], float(r[worst])), regime, tuple(unmapped), status, reason, rep)


def _to_date(s: str):
    from datetime import date
    return date.fromisoformat(s[:10])
