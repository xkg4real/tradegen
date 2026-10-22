"""R-30 estimator family (rule 2) and the fail-closed fallback to SMA20 (rule 7, "Fail-closed behaviour"); R-16 (2);
the R-06 estimator row. TASK-M3-01, TASK-M3-05. DO-NOT-BUILD items 11a / 29 (no ML vol-state classifier: `kind: ml`
is not an estimator here), 25 (no estimator outside the staged gate), 30 (no max(SMA20, implied)); the skewed-t stays
out of the menu (L482).

Conventions (binding, L1561, L3179-3190):
- `r` is a 1-D array of simple daily close-to-close returns indexed by session `t`; `ohlc` (when needed) is aligned
  row for row with `r` (row `t` is the session on which `r[t]` was realised).
- Every estimator emits `VarForecast.var[t]` = forecast of y[t, h] = sum_{j=1..h} r^2_{t+j}, made at the close of `t`
  from data through `t`, in daily variance units summed over h; NaN before warm-up; `ok[t] = False` with a `reason`
  where the challenger path failed at that origin (fallback applies, rule 7).
- SMA20 = h x sample variance (ddof = 1, mean-adjusted) of the last 20 valid returns; a stale-carry day is excluded and
  the window extends (L1561). The acting sigma is sqrt(var_1 x 252), which reproduces rv20 28.82% / vt 0.694 on 2 Oct;
  `sigma_for_decision` takes it from `core.quant.risk_layer.sma_vol` (M2, the acting path) so the harness baseline and
  the acting estimator cannot diverge (tests/macro_m4_integration.py asserts bit-identity at every origin).
- GARCH-t / GJR-t wrap `core.quant.garch.fit_garch` / `core.quant.gjr.fit_gjr` unchanged (expanding windows of >= 10
  years, refit every 21 origins, parameters held and the recursion filtered daily between refits). The optimiser's own
  persistence cap (0.9995) is tighter than the rule's 0.9999, so the rule's region is never exceeded by a fit; the R-30
  bounds (omega > 0, alpha >= 0, alpha + gamma >= 0, beta >= 0, alpha + beta + gamma/2 <= 0.9999, nu in (2, 100],
  converged) are checked on every fit object by `fit_ok`, so an injected or effectively-normal fit falls back.
- No `datetime.now()`; no I/O; pure functions on arrays.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from core.ficc.pit import MissingInput
from core.quant.garch import TRADING_DAYS, fit_garch
from core.quant.gjr import fit_gjr

ESTIMATORS = ("sma20", "ewma094", "ewma097", "garch_t", "gjr_t", "log_har_range", "comb")   # complexity order (L3222)
COMPLEXITY_ORDER = ESTIMATORS
KIND_OF = {"sma20": "sma", "ewma094": "ewma", "ewma097": "ewma", "garch_t": "garch", "gjr_t": "garch",
           "log_har_range": "har", "comb": "comb"}
RANGE_PROXY = {"KR": "overnight_sq_plus_garman_klass", "US": "parkinson"}        # L3217
PERSISTENCE_MAX = 0.9999                                                        # L3224 gjr_bounds.persistence_max
NU_BOUNDS = (2.0, 100.0)                                                        # L3224 gjr_bounds.nu
OPEN_QUALITY_MAX_SHARE = 0.05                                                   # L3225
FLAT_RANGE_MAX_SHARE = 0.05
WINDOW_SESSIONS = 252
MIN_YEARS = 10                                                                  # L3216 fit.min_years
REFIT_EVERY = 21                                                                # L3216 fit.refit_every_origins
SMA_WINDOW = 20
_LN2 = math.log(2.0)
_MIN_OLS_ROWS = 30


@dataclass(frozen=True)
class OHLC:
    """Regular-session OHLC aligned with `r`; `prev_close[t]` = close of the session before row t (the overnight leg);
    `open_equals_prior_close` is M1's per-row open-quality flag (L4212), derived from the prices when not supplied."""
    dates: tuple
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    prev_close: np.ndarray | None = None
    open_equals_prior_close: np.ndarray | None = None

    def __post_init__(self) -> None:
        n = self.close.size
        for name in ("open", "high", "low"):
            if getattr(self, name).size != n:
                raise ValueError(f"OHLC.{name} has {getattr(self, name).size} rows, close has {n}")
        if self.prev_close is None:
            object.__setattr__(self, "prev_close", np.r_[np.nan, self.close[:-1]].astype(float))
        if self.open_equals_prior_close is None:
            object.__setattr__(self, "open_equals_prior_close", self.open == self.prev_close)


@dataclass(frozen=True)
class VarForecast:
    name: str
    h: int
    var: np.ndarray            # len T; NaN before warm-up or where ok is False
    ok: np.ndarray             # bool per origin
    reason: tuple              # per origin: None | "insufficient_history" | "gjr_bounds:..." | "gjr_not_converged" |
    #                            "open_quality" | "flat_range" | "proxy_nonpositive" | "no_proxy" | "error:<type>"


@dataclass(frozen=True)
class SigmaDecision:
    """The sigma actually used for one decision (rule 7): on fallback `sigma_ann` IS SMA20's sigma, never a blend."""
    sigma_ann: float | None
    estimator_used: str
    fallback_used: bool
    reason: str | None
    status: str                # registered_default | challenger_selected | fallback_to_sma20 | NOT_RUN
    declared: str
    sigma_sma20_ann: float | None


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=float).reshape(-1)


def _empty(name: str, h: int, T: int, reason: str = "insufficient_history"):
    return np.full(T, np.nan), np.zeros(T, dtype=bool), [reason] * T


def _pack(name, h, var, ok, reason) -> VarForecast:
    return VarForecast(name, int(h), var, ok, tuple(reason))


# --------------------------------------------------------------------------- #
# SMA20 and EWMA (L3185-3186, L1561)
# --------------------------------------------------------------------------- #
def sma(r, h: int, *, window: int = SMA_WINDOW, valid=None) -> VarForecast:
    """h x the sample variance (ddof 1) of the last `window` valid returns through t; a stale-carry day (`valid`
    False) is excluded and the window extends to the last `window` valid returns (L1561)."""
    r = _arr(r)
    T = r.size
    mask = np.isfinite(r) if valid is None else (np.asarray(valid, dtype=bool) & np.isfinite(r))
    var, ok, reason = _empty("sma20", h, T)
    vidx = np.flatnonzero(mask)
    for k in range(window, vidx.size + 1):
        lo, hi = vidx[k - 1], (vidx[k] if k < vidx.size else T)
        v = float(np.var(r[vidx[k - window:k]], ddof=1)) * h
        if math.isfinite(v) and v > 0:
            var[lo:hi], ok[lo:hi] = v, True
            reason[lo:hi] = [None] * (hi - lo)
        else:
            reason[lo:hi] = ["sigma_nonpositive"] * (hi - lo)
    return _pack("sma20", h, var, ok, reason)


def ewma(r, h: int, lam: float, *, init_window: int = SMA_WINDOW) -> VarForecast:
    """RiskMetrics recursion s2[t+1] = lam s2[t] + (1 - lam) r[t]^2 (zero mean), seeded with the sample variance of
    the first `init_window` returns; first usable origin after `init_window` returns; var = h x s2[t+1] (brief F-3)."""
    r = _arr(r)
    T = r.size
    if not np.all(np.isfinite(r)):
        raise ValueError("ewma needs finite returns (stale-carry days are excluded upstream)")
    name = {0.94: "ewma094", 0.97: "ewma097"}.get(round(lam, 2), f"ewma{lam}")
    var, ok, reason = _empty(name, h, T)
    if T < init_window:
        return _pack(name, h, var, ok, reason)
    s2 = float(np.var(r[:init_window], ddof=1))
    var[init_window - 1], ok[init_window - 1], reason[init_window - 1] = h * s2, True, None
    for t in range(init_window, T):
        s2 = lam * s2 + (1.0 - lam) * r[t] * r[t]
        var[t], ok[t], reason[t] = h * s2, True, None
    return _pack(name, h, var, ok, reason)


# --------------------------------------------------------------------------- #
# GARCH-t and GJR-t on expanding windows (L3167, L3187, L3203)
# --------------------------------------------------------------------------- #
def fit_ok(fit, *, persistence_max: float = PERSISTENCE_MAX, nu_bounds=NU_BOUNDS) -> tuple[bool, str | None]:
    """R-30 rule 7 bounds on a GarchFit (gamma = 0) or GJRFit. `(False, reason)` for anything outside them,
    including a fit that converged to effectively normal innovations (nu = inf or nu > 100; brief F-6)."""
    if fit is None:
        return False, "gjr_not_converged"
    if not bool(getattr(fit, "converged", False)):
        return False, "gjr_not_converged"
    omega, alpha, beta = float(fit.omega), float(fit.alpha), float(fit.beta)
    gamma = float(getattr(fit, "gamma", 0.0))
    nu = float(fit.nu)
    pers = max(alpha + beta + 0.5 * gamma, float(getattr(fit, "persistence", 0.0)))
    lo, hi = nu_bounds
    checks = (("omega>0", omega > 0), ("alpha>=0", alpha >= 0), ("alpha+gamma>=0", alpha + gamma >= 0),
              ("beta>=0", beta >= 0), (f"persistence<={persistence_max}", pers <= persistence_max),
              (f"nu in ({lo:g},{hi:g}]", math.isfinite(nu) and lo < nu <= hi))
    bad = [n for n, c in checks if not c]
    return (True, None) if not bad else (False, "gjr_bounds:" + ",".join(bad))


gjr_fit_ok = fit_ok


def _next_var(fit) -> float:
    nv = getattr(fit, "next_var", None)
    return float(nv) if nv is not None else float(fit.cond_vol_last) ** 2 / TRADING_DAYS


def _multi_step(fit, s2_next: float, h: int) -> float:
    """sum_{j=1..h} E[s2_{t+j}] with E[s2_{t+j}] = s2bar + p^(j-1) (s2_{t+1} - s2bar), p = alpha + beta + gamma/2."""
    p = float(fit.alpha) + float(fit.beta) + 0.5 * float(getattr(fit, "gamma", 0.0))
    s2bar = float(fit.omega) / (1.0 - p)
    return h * s2bar + (s2_next - s2bar) * (1.0 - p ** h) / (1.0 - p)


def _fitted(name: str, fitter, r, h: int, *, min_years, refit_every, persistence_max, nu_bounds) -> VarForecast:
    r = _arr(r)
    T = r.size
    var, ok, reason = _empty(name, h, T)
    min_obs = max(int(round(min_years * TRADING_DAYS)), 100)
    fit, okf, why, s2_next, since = None, False, None, math.nan, refit_every
    for t in range(T):
        if t + 1 < min_obs or not np.all(np.isfinite(r[:t + 1])):
            continue
        if since >= refit_every:                       # scheduled refit on the expanding window r[:t+1]
            since = 0
            try:
                fit = fitter(r[:t + 1])
                okf, why = fit_ok(fit, persistence_max=persistence_max, nu_bounds=nu_bounds)
            except Exception as exc:                   # a failed refit never keeps old parameters (brief F-7)
                fit, okf, why = None, False, f"error:{type(exc).__name__}"
            s2_next = _next_var(fit) if okf else math.nan
        elif okf:
            eps = r[t] - float(fit.mean_daily)
            s2_next = (float(fit.omega) + (float(fit.alpha) + float(getattr(fit, "gamma", 0.0)) * (eps < 0)) * eps * eps
                       + float(fit.beta) * s2_next)
        since += 1
        if okf and math.isfinite(s2_next) and s2_next > 0:
            var[t], ok[t], reason[t] = _multi_step(fit, s2_next, h), True, None
        else:
            reason[t] = why or "gjr_not_converged"
    return _pack(name, h, var, ok, reason)


def _garch_fitter(w):
    return fit_garch(w, dist="t", profile=False)


def _gjr_fitter(w):
    return fit_gjr(w, dist="t")


def garch_t(r, h: int, *, min_years: float = MIN_YEARS, refit_every: int = REFIT_EVERY,
            persistence_max: float = PERSISTENCE_MAX, nu_bounds=NU_BOUNDS, fitter=None) -> VarForecast:
    return _fitted("garch_t", fitter or _garch_fitter, r, h, min_years=min_years, refit_every=refit_every,
                   persistence_max=persistence_max, nu_bounds=nu_bounds)


def gjr_t(r, h: int, *, min_years: float = MIN_YEARS, refit_every: int = REFIT_EVERY,
          persistence_max: float = PERSISTENCE_MAX, nu_bounds=NU_BOUNDS, fitter=None) -> VarForecast:
    return _fitted("gjr_t", fitter or _gjr_fitter, r, h, min_years=min_years, refit_every=refit_every,
                   persistence_max=persistence_max, nu_bounds=nu_bounds)


# --------------------------------------------------------------------------- #
# Range proxy, quality flag, log-HAR-range, COMB (L3188-3189, L3204)
# --------------------------------------------------------------------------- #
def range_proxy(ohlc: OHLC, market: str) -> np.ndarray:
    """Daily variance proxy p_t: KR = overnight^2 + Garman-Klass; US = Parkinson (L3188, L3217). ValueError for a
    market with no registered proxy."""
    kind = RANGE_PROXY.get(market)
    if kind is None:
        raise ValueError(f"no range proxy registered for market {market!r} (vol_target.estimator_gate.range_proxy)")
    with np.errstate(divide="ignore", invalid="ignore"):
        hl = np.log(ohlc.high / ohlc.low)
        if kind == "parkinson":
            return hl * hl / (4.0 * _LN2)
        on = np.log(ohlc.open / ohlc.prev_close)
        co = np.log(ohlc.close / ohlc.open)
        return on * on + 0.5 * hl * hl - (2.0 * _LN2 - 1.0) * co * co


def range_quality_flag(ohlc: OHLC, market: str, *, max_share: float | None = None,
                       window_sessions: int = WINDOW_SESSIONS) -> np.ndarray:
    """True at session t when the trailing `window_sessions` share of bad rows exceeds `max_share` (strictly, "> 5%"):
    KR (Garman-Klass + overnight leg) counts opens equal to the prior close; US (Parkinson) counts high == low."""
    kind = RANGE_PROXY.get(market)
    if kind is None:
        raise ValueError(f"no range proxy registered for market {market!r}")
    if kind == "parkinson":
        bad = ohlc.high == ohlc.low
        max_share = FLAT_RANGE_MAX_SHARE if max_share is None else max_share
    else:
        bad = np.asarray(ohlc.open_equals_prior_close, dtype=bool)
        max_share = OPEN_QUALITY_MAX_SHARE if max_share is None else max_share
    cs = np.concatenate([[0], np.cumsum(bad.astype(int))])
    t = np.arange(bad.size)
    lo = np.maximum(0, t + 1 - window_sessions)
    share = (cs[t + 1] - cs[lo]) / (t + 1 - lo)
    return share > max_share


def _rolling_mean(x: np.ndarray, n: int) -> np.ndarray:
    """Trailing mean over n rows; NaN until n rows exist and wherever the window holds a non-finite value."""
    out = np.full(x.size, np.nan)
    if x.size >= n:
        bad = ~np.isfinite(x)
        c = np.concatenate([[0.0], np.cumsum(np.where(bad, 0.0, x))])
        cb = np.concatenate([[0], np.cumsum(bad.astype(int))])
        m = (c[n:] - c[:-n]) / n
        out[n - 1:] = np.where((cb[n:] - cb[:-n]) > 0, np.nan, m)
    return out


def log_har_range(r, ohlc: OHLC, market: str, h: int, *, min_years: float = MIN_YEARS, refit_every: int = REFIT_EVERY,
                  max_share: float | None = None, window_sessions: int = WINDOW_SESSIONS) -> VarForecast:
    """Direct h-step OLS of log(mean p over the next h) on [1, log p_t, log mean p_{t-4..t}, log mean p_{t-21..t}],
    expanding window, refit every `refit_every` origins, trained only on rows whose target is fully realised
    (s + h <= t), rescaled to r^2 units by the expanding ratio sum r^2 / sum p (L3188)."""
    r = _arr(r)
    T = r.size
    if ohlc.close.size != T:
        raise ValueError(f"ohlc has {ohlc.close.size} rows, r has {T}")
    try:
        p = range_proxy(ohlc, market)
        tripped = range_quality_flag(ohlc, market, max_share=max_share, window_sessions=window_sessions)
    except ValueError:
        var, ok, reason = _empty("log_har_range", h, T, "no_proxy")
        return _pack("log_har_range", h, var, ok, reason)
    flag_reason = "flat_range" if RANGE_PROXY[market] == "parkinson" else "open_quality"
    pos = np.isfinite(p) & (p > 0)
    pc = np.where(pos, p, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        X = np.column_stack([np.ones(T), np.log(pc), np.log(_rolling_mean(pc, 5)), np.log(_rolling_mean(pc, 22))])
        fwd = np.full(T, np.nan)                       # mean p over t+1..t+h
        if T > h:
            fwd[:T - h] = _rolling_mean(pc, h)[h:]
        y = np.log(fwd)
    row_ok = np.all(np.isfinite(X), axis=1)
    train_ok = row_ok & np.isfinite(y)
    use = pos & np.isfinite(r)
    cum_r2 = np.cumsum(np.where(use, r * r, 0.0))
    cum_p = np.cumsum(np.where(use, p, 0.0))
    var, ok, reason = _empty("log_har_range", h, T)
    min_obs = max(int(round(min_years * TRADING_DAYS)), 100)
    beta, since = None, refit_every
    for t in range(T):
        if t + 1 < min_obs:
            continue
        if since >= refit_every:
            since = 0
            rows = np.flatnonzero(train_ok[:t - h + 1]) if t - h + 1 > 0 else np.array([], dtype=int)
            beta = np.linalg.lstsq(X[rows], y[rows], rcond=None)[0] if rows.size >= _MIN_OLS_ROWS else None
        since += 1
        if beta is None:
            reason[t] = "insufficient_history"
        elif tripped[t]:
            reason[t] = flag_reason
        elif not row_ok[t] or cum_p[t] <= 0:
            reason[t] = "proxy_nonpositive"
        else:
            m_hat = math.exp(float(X[t] @ beta))
            v = h * m_hat * (cum_r2[t] / cum_p[t])
            if math.isfinite(v) and v > 0:
                var[t], ok[t], reason[t] = v, True, None
            else:
                reason[t] = "proxy_nonpositive"
    return _pack("log_har_range", h, var, ok, reason)


def comb_from(g: VarForecast, har: VarForecast) -> VarForecast:
    """COMB = 0.5 (GJR-t + log-HAR-range) in variance units where both legs are ok; a one-legged COMB is a failure
    (fallback to SMA20, never a blend; L3189, L3206)."""
    if g.h != har.h or g.var.size != har.var.size:
        raise ValueError("comb legs must share h and length")
    ok = g.ok & har.ok
    var = np.where(ok, 0.5 * (g.var + har.var), np.nan)
    reason = tuple(None if o else (g.reason[i] if not g.ok[i] else har.reason[i]) for i, o in enumerate(ok))
    return VarForecast("comb", g.h, var, ok, reason)


_FIT_KEYS = ("min_years", "refit_every", "persistence_max", "nu_bounds", "fitter")
_HAR_KEYS = ("min_years", "refit_every", "max_share", "window_sessions")


def comb(r, ohlc: OHLC, market: str, h: int, **kw) -> VarForecast:
    g = gjr_t(r, h, **{k: v for k, v in kw.items() if k in _FIT_KEYS})
    har = log_har_range(r, ohlc, market, h, **{k: v for k, v in kw.items() if k in _HAR_KEYS})
    return comb_from(g, har)


# --------------------------------------------------------------------------- #
# Registry dispatch and the per-decision sigma (rule 7)
# --------------------------------------------------------------------------- #
def forecast(name: str, r, h: int, *, ohlc: OHLC | None = None, market: str | None = None, valid=None,
             **kw) -> VarForecast | MissingInput:
    """Dispatch by estimator name. `log_har_range` and `comb` need daily OHLC with the open-quality flag: without it
    the typed null `MissingInput(reason="missing")` is returned (never a silent one-legged result)."""
    if name not in ESTIMATORS:
        raise ValueError(f"unknown estimator {name!r}; R-30 estimators are {ESTIMATORS}")
    if name == "sma20":
        return sma(r, h, valid=valid)
    if name in ("ewma094", "ewma097"):
        return ewma(r, h, 0.94 if name == "ewma094" else 0.97)
    if name in ("garch_t", "gjr_t"):
        fn = garch_t if name == "garch_t" else gjr_t
        return fn(r, h, **{k: v for k, v in kw.items() if k in _FIT_KEYS})
    if ohlc is None or market is None:
        return MissingInput(f"{market or 'UNKNOWN'}_OHLC", "missing", "acting_exposure", (),
                            detail=f"{name} needs daily OHLC with the open-quality flag (R-30 inputs, L3178)")
    if name == "log_har_range":
        return log_har_range(r, ohlc, market, h, **{k: v for k, v in kw.items() if k in _HAR_KEYS})
    return comb(r, ohlc, market, h, **kw)


def _emit(log, record: dict) -> None:
    if log is None:
        return
    if callable(log):
        log(record)
    else:
        log.append(record)


def sigma_for_decision(declared: str, r, *, ohlc: OHLC | None = None, market: str | None = None, h: int = 21,
                       valid=None, log=None, **fit_kw) -> SigmaDecision:
    """The annualised sigma for the last origin of `r`. SMA20 is the acting default; a challenger is used only when
    its path succeeded at this origin, else SMA20 exactly, logged to `log` (a list or a callable; brief F-14).
    With fewer than 20 valid returns the M2 contract applies: sigma None, status NOT_RUN (insufficient_history)."""
    from core.quant.risk_layer import sma_vol                   # the acting SMA20 (M2); one definition, one way
    r = _arr(r)
    t = r.size - 1
    mask = np.isfinite(r) if valid is None else (np.asarray(valid, dtype=bool) & np.isfinite(r))
    sig_sma = sma_vol(r[mask], SMA_WINDOW, TRADING_DAYS)        # the last 20 valid returns; stale-carry days excluded
    if sig_sma is None or not math.isfinite(sig_sma) or sig_sma <= 0.0:
        why = "insufficient_history" if sig_sma is None else "sigma_nonpositive"
        return SigmaDecision(None, "sma20", False, why, "NOT_RUN", declared, None)
    if declared == "sma20":
        return SigmaDecision(sig_sma, "sma20", False, None, "registered_default", declared, sig_sma)
    fc = forecast(declared, r, h, ohlc=ohlc, market=market, valid=valid, **fit_kw)
    if isinstance(fc, MissingInput):
        why = f"ohlc_missing: {fc.detail}"
    elif fc.ok[t] and math.isfinite(fc.var[t]) and fc.var[t] > 0:
        return SigmaDecision(math.sqrt(fc.var[t] / h * TRADING_DAYS), declared, False, None, "challenger_selected",
                             declared, sig_sma)
    else:
        why = fc.reason[t] or "challenger_failed"
    _emit(log, {"event": "estimator_fallback", "declared": declared, "estimator_used": "sma20", "reason": why,
                "origin": int(t), "sigma_ann": sig_sma})
    return SigmaDecision(sig_sma, "sma20", True, why, "fallback_to_sma20", declared, sig_sma)
