"""GARCH(1,1) with Student-t innovations — the Quant Lab's baseline vol model.

    r_t = mu + eps_t,   eps_t = sigma_t z_t,   sigma^2_t = omega + alpha eps^2_{t-1} + beta sigma^2_{t-1}

`z_t` is Student-t(nu) scaled to unit variance (dist="t") or N(0,1)
(dist="normal"). `mu` is the sample mean of daily log returns and is FIXED,
not estimated jointly: a 500-session sample cannot pin the mean down anyway,
and letting the optimiser chase it only makes the vol parameters noisier.
The recursion starts at sigma^2_1 = sample variance of eps, i.e. at the
unconditional level. Everything inside is in daily units; TRADING_DAYS
annualises at the edges.

Estimation is L-BFGS-B on (omega, alpha, beta, eta = 1/nu) inside `BOUNDS`,
from three deterministic starts (beta in 0.80/0.90/0.95); stationarity
alpha + beta <= STATIONARITY_MAX is enforced by returning a large penalty
from the objective. Every guardrail the optimiser hit is reported in
`at_bound` and spelled out in `note`, because a fit that quietly sits on a
bound is the failure mode the operator cannot see.

PRECISION (docs/B2_FIX_BULLETIN.md). Every fit carries the observed-information
covariance: the inverse of minus the numerical Hessian of the log-likelihood at
the optimum, in the fitted coordinates (omega, alpha, beta[, eta]); `se` holds
the Wald standard errors and the delta-method standard error of the persistence,
and is EMPTY, with the reason in `se_note`, when a finite-difference step leaves
the domain (near-integrated fits) or the information matrix is not positive
definite (effectively-normal fits). The tail's interval is not a Wald one: the
profile likelihood in eta, re-maximised over (omega, alpha, beta) on a grid, is
cut at 1.92 (half the chi-square(1) 95 % point) inside the domain and at 1.353
(half of LR_5PCT) at eta = 0, where the null is the boundary mixture, so the
interval reaches "normal" exactly when the LR tile says the t did not beat the
normal (inside the first grid cell the cut ramps between the two values so the
lower end is continuous in the data). The half-life interval is the persistence
interval mapped through the half-life. The unconditional vol gets no interval:
the delta method was measured to cover 42 % to 100 % depending on the fitted
persistence. `fit_garch(profile=False)` skips the profile (90 to 150 ms on 500
sessions) for callers that fit in loops.

SIMULATION draws bounded innovations: a t draw with |z| > Z_BOUND is replaced
by a draw from the same t restricted to [-Z_BOUND, Z_BOUND]. Nothing is
rescaled, so inside the bound the law is exactly the fitted density; the
innovations are identical to unbounded ones except on the replaced days (a
path diverges from its unbounded twin from its first replaced day on, because
the variance recursion sees the replaced shock). The bound exists because
under an unbounded t exp(sigma z) has no finite expectation (a polynomial
tail cannot pay for an exponential), so no risk-neutral drift can exist; with
the bound the exact per-step correction c(sigma_t) = ln E[exp(sigma_t z)] is
a one-dimensional integral, tabulated once per (nu, bound) by
`martingale_correction` and subtracted step by step in `simulate_returns`
when an arithmetic rate is requested. Two consequences are reported rather
than hidden: the bounded innovation carries a variance v < 1 (the tail's
share is gone), so the simulated variance mean-reverts to
omega / (1 - alpha v - beta) instead of the fit's omega / (1 - alpha - beta);
`forecast_variance` and `horizon_vol` take `var_in` so the horizon-vol tile
describes the paths actually drawn, and the Quant Lab's bound note states
what the cap removes. The value of Z_BOUND was chosen by
docs/bounded_innovation_sweep.py (results in docs/bounded_innovation_sweep.md).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from scipy import stats
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import gammaln

TRADING_DAYS = 252
Z_BOUND = 22                          # |z| cap on simulated t innovations; see module docstring
_SIG_LO, _SIG_HI = 1e-6, 0.25         # daily-sigma grid of the correction table; direct sum beyond
BOUNDS: dict[str, tuple[float, float]] = {
    "omega": (1e-12, math.inf),       # daily variance units
    "alpha": (0.0, 0.5),
    "beta": (0.0, 0.999),
    "eta": (0.0, 0.4),                # the tail is fitted as eta = 1/nu; eta = 0 IS the normal
    "nu": (2.5, math.inf),            # the same range in nu, for display and validation
}
STATIONARITY_MAX = 0.9995
# 5% point of the LR test's null distribution. The null (eta = 0, normal
# innovations) lies on the boundary of the parameter space, so the statistic is
# asymptotically the mixture 1/2 delta_0 + 1/2 chi-square(1) (Self & Liang 1987),
# not chi-square(1): its 5% point is 2.706, and 3.841 is its 2.5% point.
LR_5PCT = 2.706
NU_NORMAL = 100.0                     # above this nu the t is treated as normal (excess kurtosis < 0.07)
Z95 = 1.959964                        # a 95 % Wald interval is estimate +/- Z95 * se
_PROFILE_CUT = 1.920729               # chi-square(1) 95 % point / 2: profile-interval cut inside the domain
_PROFILE_CUT0 = LR_5PCT / 2           # the cut at eta = 0, where the null is the boundary mixture
_PROFILE_GRID = np.linspace(0.0, 0.4, 41)
_ETA_EPS = 1e-10                      # below this eta the density IS the normal to double precision
_PENALTY = 1e10
_MIN_OBS = 100
_OMEGA_SCALE = 1e6


@dataclass(frozen=True)
class GarchFit:
    dist: str                         # "t" | "normal"
    omega: float
    alpha: float
    beta: float
    nu: float                         # inf when dist == "normal"
    mean_daily: float                 # mu used (sample mean of log returns)
    n_obs: int
    persistence: float                # alpha + beta
    half_life: float                  # sessions for a variance shock to halve; inf if persistence >= 1
    uncond_vol: float                 # annualised sqrt(omega / (1 - persistence) * 252); nan if persistence >= 1
    cond_vol_last: float              # annualised sqrt(sigma^2_{T+1} * 252): next-session forecast
    cond_vol: np.ndarray = field(repr=False)   # daily sigma_t, length T, aligned with the returns
    loglik: float = 0.0
    loglik_normal: float = 0.0        # GARCH-normal fit on the same data
    loglik_gbm: float = 0.0           # iid-normal benchmark
    aic: float = 0.0
    bic: float = 0.0
    lr_t_vs_normal: float = 0.0       # 2 (loglik_t - loglik_normal); compare to LR_5PCT
    delta_aic_vs_gbm: float = 0.0     # aic_gbm - aic; positive = GARCH preferred
    converged: bool = False
    at_bound: tuple[str, ...] = ()
    note: str = ""
    # Precision (B2). `se`: Wald standard errors keyed omega/alpha/beta[/eta] plus
    # "persistence" (delta method); EMPTY when undefined, `se_note` says why.
    # `eta_interval`: 95 % profile-likelihood interval for eta = 1/nu (t only;
    # lo = 0 means the interval reaches the normal). `interval_at_bound`: which of
    # alpha, beta, nu (bounds of BOUNDS) and the persistence (1) have a 95 %
    # interval crossing their bound: indicative only. omega is left out: it has
    # no tile, and on real series its interval reaches 0 more often than not.
    se: dict[str, float] = field(default_factory=dict)
    se_note: str = ""
    eta_interval: tuple[float, float] | None = None
    interval_at_bound: tuple[str, ...] = ()

    def interval(self, name: str) -> tuple[float, float] | None:
        """95 % Wald interval of a fitted or derived parameter, or None."""
        se = self.se.get(name)
        if se is None:
            return None
        v = (0.0 if math.isinf(self.nu) else 1.0 / self.nu) if name == "eta" else getattr(self, name)
        return v - Z95 * se, v + Z95 * se

    @property
    def nu_interval(self) -> tuple[float, float] | None:
        """The profile interval in nu = 1/eta: (low, high), high = inf when the
        interval reaches the normal. None for a normal fit or without a profile."""
        if self.eta_interval is None:
            return None
        lo, hi = self.eta_interval
        return 1.0 / hi, (math.inf if lo <= 0.0 else 1.0 / lo)

    @property
    def half_life_interval(self) -> tuple[float, float] | None:
        """The persistence interval mapped through the half-life (monotone), so
        it inherits the persistence coverage; inf where the interval reaches 1."""
        iv = self.interval("persistence")
        return None if iv is None else (_half_life(iv[0]), _half_life(iv[1]))

    @property
    def kurtosis_excess(self) -> float:
        """Innovation (not return) excess kurtosis: 6/(nu-4), inf at nu <= 4, 0 for normal."""
        if self.dist == "normal":
            return 0.0
        return 6.0 / (self.nu - 4.0) if self.nu > 4.0 else math.inf

    @property
    def effectively_normal(self) -> bool:
        """True when the innovations are normal or the fitted nu is above NU_NORMAL
        (eta at or near 0): simulation then draws normal innovations."""
        return self.dist == "normal" or self.nu > NU_NORMAL

    @property
    def innovation(self) -> str:
        """The innovation law actually simulated: "t" or "normal"."""
        return "normal" if self.effectively_normal else "t"


# --------------------------------------------------------------------------- #
# Likelihood
# --------------------------------------------------------------------------- #
def _variance_path(eps2: np.ndarray, omega: float, alpha: float, beta: float,
                   s2_init: float) -> np.ndarray:
    """sigma^2_1..sigma^2_{T+1} (length T+1). IIR filter y_t = x_t + beta y_{t-1}
    with x_1 = s2_init and x_t = omega + alpha eps^2_{t-1}."""
    x = np.empty(eps2.size + 1)
    x[0] = s2_init
    x[1:] = omega + alpha * eps2
    return lfilter([1.0], [1.0, -beta], x)


def _t_const(nu: float) -> float:
    """ln of the unit-variance t density's normalising constant. Beyond nu = 1e4
    the two gammaln terms cancel catastrophically (each ~1e8 at nu = 1e8, the
    finite-difference step from eta = 0), so the Stirling expansion
    lnG(x+1/2) - lnG(x) = ln(x)/2 - 1/(8x) + O(x^-3), x = nu/2, is used there."""
    if nu > 1e4:
        return 0.5 * math.log(nu / (2.0 * math.pi * (nu - 2.0))) - 1.0 / (4.0 * nu)
    return gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * math.log(math.pi * (nu - 2))


def _loglik(params: np.ndarray, eps: np.ndarray, eps2: np.ndarray, s2_init: float,
            dist: str) -> float:
    omega, alpha, beta = params[:3]
    if alpha + beta > STATIONARITY_MAX:
        return -_PENALTY
    s2 = _variance_path(eps2, omega, alpha, beta, s2_init)[:-1]
    if not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        return -_PENALTY
    if dist == "t" and params[3] >= _ETA_EPS:
        nu = 1.0 / params[3]
        ll = _t_const(nu) - 0.5 * np.log(s2) - ((nu + 1) / 2) * np.log1p(eps2 / ((nu - 2) * s2))
    else:                                               # normal, or a t with eta = 0
        ll = -0.5 * math.log(2 * math.pi) - 0.5 * np.log(s2) - eps2 / (2 * s2)
    return float(np.sum(ll))


def loglik_iid_normal(returns: np.ndarray) -> float:
    """The GBM benchmark: iid normal with the sample mean and std (ddof=1)."""
    r = np.asarray(returns, dtype=float)
    s2 = float(np.var(r, ddof=1))
    return float(np.sum(-0.5 * math.log(2 * math.pi * s2) - (r - r.mean()) ** 2 / (2 * s2)))


def _fit(eps: np.ndarray, dist: str, extra_starts=(), default_starts: bool = True):
    """Maximise the log-likelihood over (omega, alpha, beta[, eta]) from the
    three deterministic starts (unless `default_starts` is False) plus
    `extra_starts` (parameter vectors in natural units). The t model is fitted
    in eta = 1/nu, so eta = 0 is the normal model and the t contains it;
    `fit_garch` seeds each model from the other's optimum, which is what makes
    the likelihood-ratio statistic non-negative."""
    eps2 = eps ** 2
    var = float(np.var(eps))
    names = ("omega", "alpha", "beta") + (("eta",) if dist == "t" else ())
    # omega is optimised in units of 1e-6 (daily variance is ~1e-4): at its
    # natural scale the finite-difference gradient in omega swamps the others
    # and L-BFGS-B stops after a handful of iterations with alpha still at x0.
    scale = np.ones(len(names)); scale[0] = _OMEGA_SCALE
    bounds = [(BOUNDS["omega"][0] * _OMEGA_SCALE, None)] + [BOUNDS[n] for n in names[1:]]
    # beta0 = 0.94, not 0.95: with alpha0 = 0.05 the latter starts ON the
    # stationarity penalty (and at omega0 = 0), so that start was dead and the
    # optimiser could stall short of the maximum on some 500-session series.
    starts = ([[var * (1 - 0.05 - beta0), 0.05, beta0] + ([1.0 / 8.0] if dist == "t" else [])
               for beta0 in (0.80, 0.90, 0.94)] if default_starts else []) + [list(s) for s in extra_starts]
    best = None
    for x0 in starts:
        res = minimize(lambda p: -_loglik(p / scale, eps, eps2, var, dist), np.array(x0) * scale,
                       method="L-BFGS-B", bounds=bounds)
        if best is None or res.fun < best.fun:
            best = res
    p = best.x / scale
    at = []
    for name, val in zip(names, p):
        lo, hi = BOUNDS[name]
        tol = 1e-4
        if name == "eta":                               # eta = 0 is the normal, not a failure
            if abs(val - hi) <= tol * abs(hi):
                at.append("nu")                         # nu at its lower bound 2.5
            continue
        if abs(val - lo) <= (tol if lo == 0 else tol * abs(lo)):
            at.append(name)
        elif math.isfinite(hi) and abs(val - hi) <= tol * abs(hi):
            at.append(name)
    if p[1] + p[2] > 0.995:
        at.append("stationarity")
    s2_path = _variance_path(eps2, p[0], p[1], p[2], var)
    return p, float(-best.fun), bool(best.success), tuple(at), s2_path


def _half_life(p: float) -> float:
    """Sessions for a variance shock to halve at persistence p (inf at p >= 1)."""
    if p >= 1.0:
        return math.inf
    return 0.0 if p <= 0.0 else math.log(0.5) / math.log(p)


# --------------------------------------------------------------------------- #
# Precision: observed information and the profile interval for eta (B2)
# --------------------------------------------------------------------------- #
def _ll_or_none(p: np.ndarray, eps, eps2, var, dist: str) -> float | None:
    """The log-likelihood, or None when `p` is outside the domain: a coordinate
    beyond its bound, or the stationarity penalty (which `_loglik` returns as a
    finite -_PENALTY that a difference quotient must never see)."""
    if p[0] <= 0.0 or p[1] < 0.0 or p[2] < 0.0 or (dist == "t" and not 0.0 <= p[3] <= BOUNDS["eta"][1]):
        return None
    v = _loglik(p, eps, eps2, var, dist)
    return None if v <= -_PENALTY / 2 else v


def _hessian(theta: np.ndarray, eps, eps2, var, dist: str) -> tuple[np.ndarray | None, np.ndarray]:
    """(numerical Hessian of the log-likelihood at `theta` in the optimiser's
    scaled coordinates (omega x 1e6), the scale vector). Central differences,
    except one-sided (away from the bound) in a coordinate that sits on a bound
    of BOUNDS. The Hessian is None if any evaluation leaves the domain."""
    k = theta.size
    scale = np.ones(k); scale[0] = _OMEGA_SCALE
    ts = theta * scale
    h = np.full(k, 1e-4); h[0] = 1e-3 * max(ts[0], 1e-2)
    names = ("omega", "alpha", "beta", "eta")[:k]
    side = np.zeros(k)                                   # +1 forward, -1 backward, 0 central
    for i, n in enumerate(names):
        lo, hi = BOUNDS[n]
        if ts[i] - lo * scale[i] <= 1e-6:
            side[i] = 1.0
        elif math.isfinite(hi) and hi * scale[i] - ts[i] <= 1e-6:
            side[i] = -1.0
    f = lambda t: _ll_or_none(t / scale, eps, eps2, var, dist)
    f0 = f(ts)
    if f0 is None:
        return None, scale
    H = np.empty((k, k))
    for i in range(k):
        ei = np.zeros(k); ei[i] = h[i]
        for j in range(i, k):
            ej = np.zeros(k); ej[j] = h[j]
            if side[i] == 0 and side[j] == 0:
                vals = (f(ts + ei + ej), f(ts + ei - ej), f(ts - ei + ej), f(ts - ei - ej))
                if any(v is None for v in vals):
                    return None, scale
                val = (vals[0] - vals[1] - vals[2] + vals[3]) / (4 * h[i] * h[j])
            else:                                        # one-sided where a bound blocks the step
                # O(h) rather than O(h^2): both steps of the term are 10x smaller
                # (at 1e-4 the SEs of a fit on the nu floor came out ~6 % too large)
                si = side[i] or 1.0; sj = side[j] or 1.0
                ei_, ej_ = 0.1 * ei, 0.1 * ej
                vals = (f(ts + si * ei_ + sj * ej_), f(ts + si * ei_), f(ts + sj * ej_))
                if any(v is None for v in vals):
                    return None, scale
                val = (vals[0] - vals[1] - vals[2] + f0) / (si * sj * 0.01 * h[i] * h[j])
            H[i, j] = H[j, i] = val
    return H, scale


def _covariance(theta: np.ndarray, eps, eps2, var, dist: str) -> tuple[np.ndarray | None, str]:
    """(inverse observed information in natural units, "") or (None, why). The
    information matrix must be positive definite (Cholesky) for the estimate to
    be an interior maximum whose curvature means anything. The inverse is taken
    in the scaled coordinates, where the matrix is well conditioned, and mapped
    back: cov(omega, .) = cov_scaled / (scale_omega * scale_.)."""
    H, scale = _hessian(theta, eps, eps2, var, dist)
    if H is None:
        return None, "a finite-difference step leaves the domain (stationarity cap or a bound)"
    info = -H
    if not np.all(np.isfinite(info)):
        return None, "the Hessian is not finite at the optimum"
    try:
        np.linalg.cholesky(info)
    except np.linalg.LinAlgError:
        return None, "the information matrix is not positive definite at the optimum"
    return np.linalg.inv(info) / np.outer(scale, scale), ""


def _fit_fixed_eta(eps, eps2, var, eta: float, starts) -> tuple[float, np.ndarray]:
    """Maximise the t log-likelihood over (omega, alpha, beta) at a fixed eta
    from each of `starts`, keeping the best. The profile scan warm-starts from
    the previous grid point and, where that lands outside the cut (the points
    that decide an end), retries from the joint optimum: along a flat ridge
    (alpha = 0 on iid data) a single warm-started run can stall, which dents
    the profile and would narrow the interval or stop the scan early."""
    scale = np.array([_OMEGA_SCALE, 1.0, 1.0])
    bounds = [(BOUNDS["omega"][0] * _OMEGA_SCALE, None), BOUNDS["alpha"], BOUNDS["beta"]]
    best = None
    for s in starts:
        res = minimize(lambda q: -_loglik(np.append(q / scale, eta), eps, eps2, var, "t"),
                       np.asarray(s, dtype=float) * scale, method="L-BFGS-B", bounds=bounds)
        if best is None or res.fun < best.fun:
            best = res
    return float(-best.fun), best.x / scale


def _profile_eta(eps, eps2, var, theta: np.ndarray, ll_max: float,
                 ll_normal: float) -> tuple[tuple[float, float], tuple | None]:
    """((lo, hi), better): the 95 % profile-likelihood interval for eta, i.e.
    the eta at which the log-likelihood, re-maximised over (omega, alpha, beta),
    stays within _PROFILE_CUT of the maximum, scanned outward from the estimate
    on _PROFILE_GRID with warm starts and the ends refined linearly. The point
    eta = 0 is the best normal fit (`ll_normal`, no refit) and is judged by the
    boundary cut _PROFILE_CUT0 through the very expression the LR chip uses, so
    the interval reaches 0 iff lr_t_vs_normal <= LR_5PCT; in the first grid cell
    the cut ramps linearly between the two values so the lower end is continuous
    in the data. hi = 0.4 when the interval reaches nu's lower bound 2.5.
    `better` is (loglik, [omega, alpha, beta, eta]) of a refit that beat
    `ll_max`, which happens when the joint optimiser stalled; None otherwise."""
    eta_hat = float(theta[3])
    cut = ll_max - _PROFILE_CUT
    prof = {eta_hat: ll_max, 0.0: ll_normal}
    better = None
    for pts in (_PROFILE_GRID[_PROFILE_GRID > eta_hat],
                _PROFILE_GRID[(_PROFILE_GRID < eta_hat) & (_PROFILE_GRID > 0.0)][::-1]):
        start = theta[:3].copy()
        for g in pts:
            ll, start = _fit_fixed_eta(eps, eps2, var, float(g), (start,))
            if ll < cut:                                  # decides an end: guard against a stalled refit
                ll2, s2 = _fit_fixed_eta(eps, eps2, var, float(g), (theta[:3],))
                if ll2 > ll:
                    ll, start = ll2, s2
            prof[float(g)] = ll
            if ll > ll_max + 1e-6 and (better is None or ll > better[0]):
                better = (ll, [*start.tolist(), float(g)])
            if ll < cut - 1.0:                            # clearly outside: stop the scan
                break
    xs = np.array(sorted(prof)); ys = np.array([prof[x] for x in xs])
    i_hat = int(np.searchsorted(xs, eta_hat))

    def cross(a: float, b: float) -> float:              # where the line through (a, f(a)), (b, f(b)) meets the cut
        fa, fb = prof[a], prof[b]
        return a if fa == fb else a + (b - a) * (fa - cut) / (fa - fb)

    # upper end: last inside point at or above the estimate, refined against the next point
    i_hi = i_hat
    while i_hi + 1 < xs.size and ys[i_hi + 1] >= cut:
        i_hi += 1
    hi = float(xs[i_hi]) if i_hi + 1 >= xs.size else cross(float(xs[i_hi]), float(xs[i_hi + 1]))
    # lower end: eta = 0 is judged by the boundary cut, written as the chip writes it;
    # the ramp below reuses `lr` so its numerator is > 0 exactly when this test fails
    lr = max(0.0, 2.0 * (ll_max - ll_normal))
    if lr <= LR_5PCT:
        return (0.0, min(hi, BOUNDS["eta"][1])), better
    i_lo = i_hat
    while i_lo - 1 >= 1 and ys[i_lo - 1] >= cut:        # never past index 0 (eta = 0)
        i_lo -= 1
    a = float(xs[i_lo])
    if i_lo - 1 >= 1:                                    # first outside point is interior: plain crossing
        lo = cross(a, float(xs[i_lo - 1]))
    else:                                                # ramped cut between eta = 0 and the first inside point
        fa = prof[a]
        s = (0.5 * (lr - LR_5PCT)) / (fa - ll_normal + _PROFILE_CUT - _PROFILE_CUT0)
        lo = a * min(max(s, 1e-12), 1.0)                 # strictly inside: the chip says the t won
    return (max(lo, 0.0), min(hi, BOUNDS["eta"][1])), better


def _fit_t(eps: np.ndarray, extra_starts=()):
    """The t fit with the normal as its anchor: normal first; the t from the
    normal's optimum (eta = 0) plus `extra_starts`, so the t can never do worse
    than the normal; the normal re-fitted from the t's (omega, alpha, beta) so
    the reference likelihood is the best normal reachable through the same code
    path, with one more t pass if that normal climbs past the t. Returns
    (p, ll, converged, at_bound, s2_path, ll_normal)."""
    p_n, ll_n, _, _, _ = _fit(eps, "normal")
    p, ll, converged, at_bound, s2_path = _fit(eps, "t", extra_starts=[[*p_n[:3], 0.0], *extra_starts])
    p_n2, ll_n2, _, _, _ = _fit(eps, "normal", extra_starts=[list(p[:3])], default_starts=False)
    if ll_n2 > ll:
        t2 = _fit(eps, "t", extra_starts=[[*p_n2[:3], 0.0]], default_starts=False)
        if t2[1] >= ll:
            p, ll, converged, at_bound, s2_path = t2
    return p, ll, converged, at_bound, s2_path, max(ll_n, ll_n2)


def fit_garch(returns: np.ndarray, *, dist: str = "t", profile: bool = True) -> GarchFit:
    """Fit GARCH(1,1) on daily log returns. Raises on < 100 obs or unknown dist.
    `profile=False` skips the profile interval for eta (90 to 150 ms on top of
    a fit of 60 to 90 ms at 500 sessions), for callers that fit in loops."""
    if dist not in ("t", "normal"):
        raise ValueError(f"Unknown dist {dist!r}. One of ('t', 'normal').")
    r = np.asarray(returns, dtype=float)
    if r.size < _MIN_OBS:
        raise ValueError(f"Need at least {_MIN_OBS} observations to fit GARCH; got {r.size}.")
    mu = float(np.mean(r))
    eps = r - mu
    eps2, var = eps ** 2, float(np.var(eps))
    eta_interval = None
    if dist == "t":
        # The profile scan re-maximises at fixed eta all along the grid, so it
        # is also a check on the joint fit: if it finds a higher likelihood the
        # optimiser stalled, and the fit is re-seeded from that point.
        extra: list = []
        for _ in range(3):
            p, ll, converged, at_bound, s2_path, ll_normal = _fit_t(eps, extra)
            if not profile:
                break
            eta_interval, better = _profile_eta(eps, eps2, var, np.asarray(p, dtype=float), ll, ll_normal)
            if better is None:
                break
            extra = [better[1]]
        eta = float(p[3])
        nu = math.inf if eta < _ETA_EPS else 1.0 / eta
    else:
        p, ll, converged, at_bound, s2_path = _fit(eps, dist)
        ll_normal, nu = ll, math.inf
    omega, alpha, beta = (float(v) for v in p[:3])
    k = 4 if dist == "t" else 3
    T = r.size
    ll_gbm = loglik_iid_normal(r)
    aic = 2 * k - 2 * ll
    persistence = alpha + beta
    half_life = _half_life(persistence)
    uncond = (math.nan if persistence >= 1 else math.sqrt(omega / (1 - persistence) * TRADING_DAYS))

    # Precision: Wald standard errors from the observed information, the
    # persistence by the delta method (gradient (0, 1, 1[, 0])); the profile
    # interval of eta was computed with the fit. The unconditional vol gets none
    # on purpose.
    names = ("omega", "alpha", "beta") + (("eta",) if dist == "t" else ())
    cov, se_note = _covariance(np.asarray(p[:k], dtype=float), eps, eps2, var, dist)
    se: dict[str, float] = {}
    interval_at_bound: list[str] = []
    if cov is not None:
        se = {n: float(math.sqrt(cov[i, i])) for i, n in enumerate(names)}
        g = np.array([0.0, 1.0, 1.0, 0.0][:k])
        se["persistence"] = float(math.sqrt(g @ cov @ g))
        for n, v in (("alpha", alpha), ("beta", beta)):
            lo, hi = BOUNDS[n]
            if v - Z95 * se[n] < lo or v + Z95 * se[n] > hi:
                interval_at_bound.append(n)
        if persistence + Z95 * se["persistence"] >= 1.0:
            interval_at_bound.append("persistence")
    if eta_interval is not None and eta_interval[1] >= BOUNDS["eta"][1] - 1e-9:
        interval_at_bound.append("nu")

    flags = []
    if not converged:
        flags.append("solver did not converge")
    if "stationarity" in at_bound:
        flags.append("near-integrated (alpha+beta > 0.995)")
    if "nu" in at_bound:
        flags.append("nu at lower bound: tails heavier than the model allows")
    if dist == "t" and nu > NU_NORMAL:
        flags.append("normal innovations" + (" (eta = 0)" if math.isinf(nu)
                                             else f" (nu = {nu:.0f} > {NU_NORMAL:.0f})"))
    if "omega" in at_bound:
        flags.append("omega at bound: unconditional vol undefined")
    for n in ("alpha", "beta"):
        if n in at_bound:
            flags.append(f"{n} at bound")
    if not se:
        flags.append(f"standard errors undefined: {se_note}")
    at_bound_iv = [n for n in interval_at_bound if n != "persistence"]
    if at_bound_iv:
        flags.append("95% interval reaches a bound: " + ", ".join(at_bound_iv))
    if "persistence" in interval_at_bound:
        flags.append("persistence interval reaches 1")
    tail = ("; ".join(flags)) if flags else "no guardrail hit"
    pm = lambda n: f"±{se[n]:.3f}" if n in se else ""
    nu_txt = ""
    if dist == "t":
        nu_txt = f" nu={nu:.1f}"
        if eta_interval is not None:
            lo_nu, hi_nu = 1.0 / eta_interval[1], (math.inf if eta_interval[0] <= 0 else 1.0 / eta_interval[0])
            nu_txt += f" ({lo_nu:.1f} to " + ("normal" if math.isinf(hi_nu) else f"{hi_nu:.1f}") + ")"
    note = (f"GARCH(1,1)-{dist} on {T} sessions, mu fixed at {mu * 100:+.3f}%/day: "
            f"alpha={alpha:.3f}{pm('alpha')} beta={beta:.3f}{pm('beta')} "
            f"persistence={persistence:.3f}{pm('persistence')}" + nu_txt + f"; {tail}.")
    return GarchFit(
        dist=dist, omega=omega, alpha=alpha, beta=beta, nu=nu, mean_daily=mu, n_obs=T,
        persistence=persistence, half_life=half_life, uncond_vol=uncond,
        cond_vol_last=math.sqrt(s2_path[-1] * TRADING_DAYS),
        cond_vol=np.sqrt(s2_path[:-1]),
        loglik=ll, loglik_normal=ll_normal, loglik_gbm=ll_gbm,
        aic=aic, bic=k * math.log(T) - 2 * ll,
        lr_t_vs_normal=max(0.0, 2 * (ll - ll_normal)),   # nested: negative only by optimiser tolerance
        delta_aic_vs_gbm=(4 - 2 * ll_gbm) - aic,
        converged=converged, at_bound=at_bound, note=note,
        se=se, se_note=se_note, eta_interval=eta_interval,
        interval_at_bound=tuple(interval_at_bound),
    )


# --------------------------------------------------------------------------- #
# Forecast and simulation
# --------------------------------------------------------------------------- #
def forecast_variance(fit: GarchFit, horizon: int, var_in: float = 1.0) -> np.ndarray:
    """Daily variance of the returns at T+1..T+H: var_in * sigma^2_t, with
    sigma^2_{T+1} as fitted and then omega + (alpha var_in + beta) sigma^2.
    `var_in` is the variance of the innovation actually simulated: 1 for the
    fitted model (the classic forecast), `bounded_t_stats`'s value for the
    bounded t the fan is drawn with, in which case both the level the
    recursion decays to and the returns' share of it are lower."""
    out = np.empty(int(horizon))
    s2 = fit.cond_vol_last ** 2 / TRADING_DAYS
    p = fit.alpha * var_in + fit.beta
    for h in range(out.size):
        out[h] = var_in * s2
        s2 = fit.omega + p * s2
    return out


def horizon_vol(fit: GarchFit, horizon: int, var_in: float = 1.0) -> float:
    """Annualised average vol over the horizon (see `forecast_variance`)."""
    return math.sqrt(float(np.mean(forecast_variance(fit, horizon, var_in))) * TRADING_DAYS)


def _t_scale(nu: float) -> float:
    """Unit-variance scaling of a standard t draw."""
    return math.sqrt((nu - 2.0) / nu)


def t_density(z, nu: float) -> np.ndarray:
    """Density of the unit-variance Student-t: exp of the per-observation
    log-likelihood in `_loglik` with sigma = 1. Above NU_NORMAL the normal
    density is returned (the t formula loses precision as nu grows)."""
    z = np.asarray(z, dtype=float)
    if nu > NU_NORMAL:
        return np.exp(-0.5 * z ** 2) / math.sqrt(2 * math.pi)
    return math.exp(_t_const(nu)) * (1.0 + z ** 2 / (nu - 2.0)) ** (-(nu + 1) / 2)


def _draw_z(rng, nu: float, dist: str, size, bound: float | None = Z_BOUND) -> np.ndarray:
    """Unit-variance innovations. With a `bound` (t only) every draw beyond it is
    replaced by one from the t restricted to [-bound, bound] via the inverse CDF,
    so the law inside the bound is the fitted t's and the innovations differ
    from an unbounded draw with the same seed only on the replaced days. A t
    with nu above NU_NORMAL is drawn as a normal."""
    if dist != "t" or nu > NU_NORMAL:
        return rng.standard_normal(size=size)
    s = _t_scale(nu)
    z = rng.standard_t(nu, size=size) * s
    if bound is None:
        return z
    out = np.abs(z) > bound
    n_out = int(np.count_nonzero(out))
    if n_out:
        d = stats.t(nu)
        lo, hi = d.cdf(-bound / s), d.cdf(bound / s)
        z[out] = s * d.ppf(lo + rng.random(n_out) * (hi - lo))
    return z


def _log_mgf(sig: np.ndarray, z: np.ndarray, wt: np.ndarray) -> np.ndarray:
    """ln sum_i wt_i exp(sig z_i) for each sig, computed stably."""
    e = np.outer(sig, z)
    m = e.max(axis=1, keepdims=True)
    return m[:, 0] + np.log((wt[None, :] * np.exp(e - m)).sum(axis=1))


@lru_cache(maxsize=32)
def _correction_table(nu: float, bound: float):
    """Gauss-Legendre nodes and normalised weights of the t restricted to
    [-bound, bound] (three panels so the peak is resolved), and c(sigma)/sigma^2
    on a geometric daily-sigma grid up to _SIG_HI. The ratio is nearly constant
    (E[z^2]/2 as sigma -> 0), so linear interpolation of it is accurate to
    ~3e-8 at the top of the grid and better below; above the grid
    `martingale_correction` sums the nodes directly. The grid is evaluated in
    chunks: one outer product over 4000 x 1800 would need ~170 MB of
    temporaries, and the cache key is the fitted nu, so every fit builds a table."""
    x, w = np.polynomial.legendre.leggauss(600)
    edges = (-bound, -1.0, 1.0, bound) if bound > 1.0 else (-bound, bound)
    z = np.concatenate([0.5 * (b - a) * x + 0.5 * (b + a) for a, b in zip(edges[:-1], edges[1:])])
    wt = np.concatenate([0.5 * (b - a) * w for a, b in zip(edges[:-1], edges[1:])]) * t_density(z, nu)
    wt = wt / wt.sum()
    sig = np.geomspace(_SIG_LO, _SIG_HI, 4000)
    c = np.concatenate([_log_mgf(s, z, wt) for s in np.array_split(sig, 16)])
    return z, wt, sig, c / sig ** 2


def bounded_t_stats(nu: float, bound: float) -> tuple[float, float]:
    """(probability the unbounded t lands inside the bound, variance of the
    bounded innovation). The second is what the variance recursion sees in
    simulation; it is below 1 by the variance the tail beyond the bound carried.
    (1, 1) for a t above NU_NORMAL, which is drawn as a normal."""
    if nu > NU_NORMAL:
        return 1.0, 1.0
    z, wt, _, _ = _correction_table(float(nu), float(bound))
    d, s = stats.t(nu), _t_scale(nu)
    return float(d.cdf(bound / s) - d.cdf(-bound / s)), float((wt * z * z).sum())


def martingale_correction(sigma_daily, nu: float, dist: str,
                          bound: float | None = Z_BOUND) -> np.ndarray:
    """c(sigma) = ln E[exp(sigma z)] per step, exact for the innovation law that
    is simulated: sigma^2/2 for a normal z; for a bounded t the tabulated log-MGF
    of the truncated t, interpolated on the sigma grid (direct quadrature beyond
    it). Subtracting it from an arithmetic rate makes exp(return) average
    exp(rate) exactly. An unbounded t has no such correction and raises."""
    sig = np.atleast_1d(np.asarray(sigma_daily, dtype=float))
    if dist != "t" or nu > NU_NORMAL:                   # normal, or a t drawn as one
        return 0.5 * sig ** 2
    if bound is None:
        raise ValueError("exp(sigma z) has no finite expectation under an unbounded t; no correction exists")
    z, wt, grid, ratio = _correction_table(float(nu), float(bound))
    out = np.interp(sig, grid, ratio) * sig ** 2
    big = sig > grid[-1]
    if np.any(big):
        out[big] = _log_mgf(sig[big], z, wt)
    return out


def simulate_returns(fit: GarchFit, *, n_paths: int, horizon: int, seed: int = 7,
                     drift_daily: float | None = None, rate_daily: float | None = None,
                     bound: float | None = Z_BOUND) -> tuple[np.ndarray, float]:
    """(n_paths, horizon) daily log returns, and the horizon-average daily
    convexity correction. The recursion starts at sigma^2_{T+1}.

    * `rate_daily` given (an arithmetic rate such as rf/252): each step adds
      rate_daily - c(sigma_t) with that path's own conditional vol, so
      exp(sum) has expectation exp(rate * T) and the discounted price is a
      martingale to Monte Carlo precision.
    * otherwise the constant log drift `drift_daily` (default: the sample
      mean) is added and the correction is 0."""
    rng = np.random.default_rng(seed)
    z = _draw_z(rng, fit.nu, fit.dist, (n_paths, horizon), bound)
    ret = np.empty((n_paths, horizon))
    s2 = np.full(n_paths, fit.cond_vol_last ** 2 / TRADING_DAYS)
    drift = fit.mean_daily if drift_daily is None else float(drift_daily)
    corr = 0.0
    for h in range(horizon):
        sig = np.sqrt(s2)
        eps = sig * z[:, h]
        if rate_daily is None:
            ret[:, h] = drift + eps
        else:
            c = martingale_correction(sig, fit.nu, fit.dist, bound)
            ret[:, h] = float(rate_daily) - c + eps
            corr += float(c.mean())
        s2 = fit.omega + fit.alpha * eps ** 2 + fit.beta * s2
    return ret, (corr / horizon if rate_daily is not None else 0.0)


def simulate_garch_series(omega: float, alpha: float, beta: float, nu: float, *,
                          n: int, seed: int, dist: str = "t") -> np.ndarray:
    """Zero-mean synthetic GARCH(1,1) returns (for tests and the primer), 500-session burn-in."""
    rng = np.random.default_rng(seed)
    burn = 500
    z = _draw_z(rng, nu, dist, n + burn, bound=None)     # the "true" model keeps its full tail
    eps = np.empty(n + burn)
    s2 = omega / (1 - alpha - beta) if alpha + beta < 1 else omega * 100
    for t in range(n + burn):
        eps[t] = math.sqrt(s2) * z[t]
        s2 = omega + alpha * eps[t] ** 2 + beta * s2
    return eps[burn:]


if __name__ == "__main__":
    r = simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=3000, seed=1)
    f = fit_garch(r)
    print(f.note)
    assert abs(f.alpha - 0.08) < 0.05, f.alpha
    assert abs(f.beta - 0.90) < 0.06, f.beta
    assert 4 < f.nu < 10, f.nu
    assert f.converged
    z = _draw_z(np.random.default_rng(0), 6.0, "t", 200_000)
    assert abs(float(np.var(z)) - 1.0) < 0.03, np.var(z)
    assert float(np.abs(z).max()) <= Z_BOUND, "simulated innovations must respect the bound"
    from scipy.integrate import quad
    for nu_, sig_ in ((3.1, 0.018), (6.0, 0.05)):
        num = sum(quad(lambda x: math.exp(sig_ * x) * t_density(x, nu_), a, b, limit=400)[0]
                  for a, b in ((-Z_BOUND, -1), (-1, 1), (1, Z_BOUND)))
        den = sum(quad(lambda x: t_density(x, nu_), a, b, limit=400)[0]
                  for a, b in ((-Z_BOUND, -1), (-1, 1), (1, Z_BOUND)))
        assert abs(float(martingale_correction(sig_, nu_, "t")[0]) - math.log(num / den)) < 1e-7
    fv = forecast_variance(f, 5000)
    assert abs(fv[-1] / (f.omega / (1 - f.persistence)) - 1) < 0.01
    assert f.loglik >= f.loglik_normal - 1e-6
    # B2: intervals exist on the recovery series and contain the truth
    assert set(f.se) == {"omega", "alpha", "beta", "eta", "persistence"}, f.se_note
    for name, truth in (("alpha", 0.08), ("beta", 0.90), ("persistence", 0.98)):
        lo, hi = f.interval(name)
        assert lo <= truth <= hi, (name, lo, hi)
    lo, hi = f.eta_interval
    assert lo <= 1 / 6 <= hi and (lo == 0.0) == (f.lr_t_vs_normal <= LR_5PCT), f.eta_interval
    g = fit_garch(np.random.default_rng(2).normal(0.0004, 0.012, 500))
    assert g.note and isinstance(g.at_bound, tuple)
    assert g.lr_t_vs_normal >= 0.0 and g.effectively_normal, g.note   # the t contains the normal
    assert g.nu_interval is not None and math.isinf(g.nu_interval[1]), g.nu_interval
    assert bool(g.se) != bool(g.se_note)                                # one or the other, never neither
    print(g.note)
    print("ok")
