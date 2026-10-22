"""GJR-GARCH(1,1) with Student-t innovations — the leverage-term challenger
(architecture review B8), fitted for out-of-sample SCORING only.

    sigma^2_t = omega + (alpha + gamma * 1{eps_{t-1} < 0}) eps^2_{t-1} + beta sigma^2_{t-1}

Glosten, Jagannathan & Runkle (1993): a negative shock raises next-day variance
by gamma more than a positive one of the same size. With symmetric innovations
E[1{eps<0}] = ½, so the persistence is alpha + beta + gamma/2 and the
unconditional variance omega / (1 - alpha - beta - gamma/2).

This module deliberately stops at the fit and the one-day-ahead variance: the
Quant Lab's simulation, martingale correction, standard errors and profile
interval live in `core.quant.garch` and are not duplicated here. The point is
to let the validation gate decide whether asymmetry repairs the left-tail
under-coverage the study found for the symmetric GARCH-t on SPY and KODEX 200
(`docs/asset_expansion/results.md`); if it does, wiring gamma through the
simulator is the next, separately documented step. Same conventions as
`garch.py`: mu fixed at the sample mean, tail fitted as eta = 1/nu on [0, 0.4]
(eta = 0 is the normal), sigma^2_1 at the sample variance, L-BFGS-B from
deterministic starts, every bound hit reported.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats as sps
from scipy.optimize import minimize
from scipy.signal import lfilter
from scipy.special import gammaln

from core.quant.garch import BOUNDS, STATIONARITY_MAX, _t_const, _ETA_EPS, _PENALTY, _OMEGA_SCALE

GAMMA_BOUNDS = (0.0, 0.5)
LAMBDA_BOUNDS = (-0.9, 0.9)                # Hansen's skew parameter; 0 is the symmetric t
_ETA_MIN_SKEW = 1.0 / 50.0                 # skew-t keeps nu <= 50: Hansen's density needs a finite nu
_MIN_OBS = 100


# --------------------------------------------------------------------------- #
# Hansen (1994, IER 35) skewed t, zero mean and unit variance
# --------------------------------------------------------------------------- #
def _skewt_consts(nu: float, lam: float) -> tuple[float, float, float]:
    c = math.exp(gammaln((nu + 1) / 2) - gammaln(nu / 2)) / math.sqrt(math.pi * (nu - 2))
    a = 4 * lam * c * (nu - 2) / (nu - 1)
    b = math.sqrt(1 + 3 * lam ** 2 - a ** 2)
    return a, b, c


def skewt_logpdf(z: np.ndarray, nu: float, lam: float) -> np.ndarray:
    a, b, c = _skewt_consts(nu, lam)
    z = np.asarray(z, dtype=float)
    s = np.where(z < -a / b, 1 - lam, 1 + lam)
    return math.log(b * c) - ((nu + 1) / 2) * np.log1p(((b * z + a) / s) ** 2 / (nu - 2))


def skewt_cdf(z, nu: float, lam: float):
    a, b, _ = _skewt_consts(nu, lam)
    k = math.sqrt(nu / (nu - 2))
    z = np.asarray(z, dtype=float)
    lo = (1 - lam) * sps.t.cdf((b * z + a) / (1 - lam) * k, nu)
    hi = (1 - lam) / 2 + (1 + lam) * (sps.t.cdf((b * z + a) / (1 + lam) * k, nu) - 0.5)
    return np.where(z < -a / b, lo, hi)


def skewt_ppf(u, nu: float, lam: float):
    a, b, _ = _skewt_consts(nu, lam)
    k = math.sqrt((nu - 2) / nu)
    u = np.asarray(u, dtype=float)
    lo = ((1 - lam) * sps.t.ppf(np.clip(u / (1 - lam), 0, 1), nu) * k - a) / b
    hi = ((1 + lam) * sps.t.ppf(np.clip((u - (1 - lam) / 2) / (1 + lam) + 0.5, 0, 1), nu) * k - a) / b
    return np.where(u < (1 - lam) / 2, lo, hi)


@dataclass(frozen=True)
class GJRFit:
    omega: float
    alpha: float
    gamma: float
    beta: float
    nu: float                              # inf when eta = 0
    mean_daily: float
    n_obs: int
    persistence: float                     # alpha + beta + gamma/2
    loglik: float
    loglik_symmetric: float                # the same fit with gamma fixed at 0 (nested)
    converged: bool
    at_bound: tuple[str, ...]
    cond_vol: np.ndarray = field(repr=False)   # daily sigma_t aligned with the returns
    next_var: float = 0.0                  # sigma^2_{T+1}
    lam: float = 0.0                       # Hansen skew (dist="skewt"); negative = longer left tail

    @property
    def lr_asymmetry(self) -> float:
        """2(lnL_GJR − lnL_symmetric); the null gamma = 0 is on the boundary, so the
        5 % point is 2.706 (the same ½δ₀ + ½χ²₁ mixture as the eta test)."""
        return max(0.0, 2.0 * (self.loglik - self.loglik_symmetric))

    @property
    def effectively_normal(self) -> bool:
        return not math.isfinite(self.nu) or self.nu > 100.0


def _variance_path(eps2: np.ndarray, neg: np.ndarray, omega: float, alpha: float, gamma: float,
                   beta: float, s2_init: float) -> np.ndarray:
    x = np.empty(eps2.size + 1)
    x[0] = s2_init
    x[1:] = omega + (alpha + gamma * neg) * eps2
    return lfilter([1.0], [1.0, -beta], x)


def _loglik(p: np.ndarray, eps: np.ndarray, eps2: np.ndarray, neg: np.ndarray, s2_init: float) -> float:
    omega, alpha, gamma, beta, eta, lam = p
    if alpha + beta + 0.5 * gamma > STATIONARITY_MAX:
        return -_PENALTY
    s2 = _variance_path(eps2, neg, omega, alpha, gamma, beta, s2_init)[:-1]
    if not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        return -_PENALTY
    if lam != 0.0:
        ll = skewt_logpdf(eps / np.sqrt(s2), 1.0 / eta, lam) - 0.5 * np.log(s2)
    elif eta >= _ETA_EPS:
        nu = 1.0 / eta
        ll = _t_const(nu) - 0.5 * np.log(s2) - ((nu + 1) / 2) * np.log1p(eps2 / ((nu - 2) * s2))
    else:
        ll = -0.5 * math.log(2 * math.pi) - 0.5 * np.log(s2) - eps2 / (2 * s2)
    return float(np.sum(ll))


def fit_gjr(returns: np.ndarray, *, dist: str = "t") -> GJRFit:
    """Fit GJR-GARCH(1,1) on daily log returns with Student-t (dist="t"),
    normal ("normal") or Hansen skewed-t ("skewt") innovations."""
    if dist not in ("t", "normal", "skewt"):
        raise ValueError("dist must be 't', 'normal' or 'skewt'")
    r = np.asarray(returns, dtype=float)
    if r.size < _MIN_OBS:
        raise ValueError(f"Need at least {_MIN_OBS} observations, got {r.size}.")
    mu = float(np.mean(r))
    eps = r - mu
    eps2 = eps ** 2
    neg = (eps < 0).astype(float)
    var = float(np.var(eps))
    scale = np.array([_OMEGA_SCALE, 1.0, 1.0, 1.0, 1.0, 1.0])
    eta_hi = BOUNDS["eta"][1] if dist != "normal" else 0.0
    eta_lo = _ETA_MIN_SKEW if dist == "skewt" else 0.0
    lam_b = LAMBDA_BOUNDS if dist == "skewt" else (0.0, 0.0)
    bounds = [(BOUNDS["omega"][0] * _OMEGA_SCALE, None), BOUNDS["alpha"], GAMMA_BOUNDS, BOUNDS["beta"], (eta_lo, eta_hi), lam_b]
    eta0 = 1.0 / 8.0 if dist != "normal" else 0.0
    lam0 = -0.1 if dist == "skewt" else 0.0

    def solve(starts, fix_gamma: bool):
        best = None
        for x0 in starts:
            b = list(bounds)
            if fix_gamma:
                b[2] = (0.0, 0.0)
            res = minimize(lambda q: -_loglik(q / scale, eps, eps2, neg, var), np.asarray(x0) * scale,
                           method="L-BFGS-B", bounds=b)
            if best is None or res.fun < best.fun:
                best = res
        return best.x / scale, float(-best.fun), bool(best.success)

    starts = [[var * (1 - 0.05 - b0), 0.03, 0.05, b0, eta0, lam0] for b0 in (0.80, 0.88, 0.93)]
    p_sym, ll_sym, _ = solve([[s[0], s[1] + 0.02, 0.0, s[3], s[4], s[5]] for s in starts], fix_gamma=True)
    p, ll, ok = solve(starts + [[*p_sym[:2], 0.02, *p_sym[3:]]], fix_gamma=False)
    if ll < ll_sym:                                   # the nested model must not lose to its own special case
        p, ll = p_sym, ll_sym
    at = []
    for name, val, (lo, hi) in (("alpha", p[1], BOUNDS["alpha"]), ("gamma", p[2], GAMMA_BOUNDS), ("beta", p[3], BOUNDS["beta"])):
        if abs(val - lo) <= 1e-4 or (math.isfinite(hi) and abs(val - hi) <= 1e-4 * abs(hi)):
            at.append(name)
    if dist != "normal" and abs(p[4] - eta_hi) <= 1e-4 * eta_hi:
        at.append("nu")
    if dist == "skewt" and abs(abs(p[5]) - LAMBDA_BOUNDS[1]) <= 1e-4:
        at.append("lambda")
    pers = p[1] + p[3] + 0.5 * p[2]
    if pers > 0.995:
        at.append("stationarity")
    s2 = _variance_path(eps2, neg, p[0], p[1], p[2], p[3], var)
    nu = (1.0 / p[4]) if p[4] >= _ETA_EPS else math.inf
    return GJRFit(omega=float(p[0]), alpha=float(p[1]), gamma=float(p[2]), beta=float(p[3]), nu=nu, mean_daily=mu,
                  n_obs=int(r.size), persistence=float(pers), loglik=ll, loglik_symmetric=ll_sym, converged=ok,
                  at_bound=tuple(at), cond_vol=np.sqrt(s2[:-1]), next_var=float(s2[-1]), lam=float(p[5]))


def next_variance(fit: GJRFit, eps_prev: float, s2_prev: float) -> float:
    """One step of the recursion from an observed shock and the previous variance."""
    return fit.omega + (fit.alpha + fit.gamma * (1.0 if eps_prev < 0 else 0.0)) * eps_prev ** 2 + fit.beta * s2_prev


def simulate_gjr_series(omega: float, alpha: float, gamma: float, beta: float, nu: float, *, n: int,
                        seed: int = 1) -> np.ndarray:
    """A GJR-t return series for tests (unit-variance t innovations)."""
    rng = np.random.default_rng(seed)
    z = rng.standard_t(nu, size=n) * math.sqrt((nu - 2) / nu)
    r = np.empty(n)
    s2 = omega / (1 - alpha - beta - gamma / 2)
    e_prev = 0.0
    for t in range(n):
        s2 = omega + (alpha + gamma * (e_prev < 0)) * e_prev ** 2 + beta * s2
        e_prev = math.sqrt(s2) * z[t]
        r[t] = e_prev
    return r


if __name__ == "__main__":
    r = simulate_gjr_series(2e-6, 0.03, 0.10, 0.90, 6.0, n=3000, seed=4)
    f = fit_gjr(r)
    assert abs(f.alpha - 0.03) < 0.04 and abs(f.gamma - 0.10) < 0.06 and abs(f.beta - 0.90) < 0.05, (f.alpha, f.gamma, f.beta)
    assert 3.5 < f.nu < 12 and f.lr_asymmetry > 2.706 and f.persistence < 1.0, (f.nu, f.lr_asymmetry)
    assert f.cond_vol.size == r.size and f.next_var > 0
    # symmetric data: gamma near zero and the LR small
    from core.quant.garch import simulate_garch_series
    rs = simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=3000, seed=2)
    fs = fit_gjr(rs)
    assert fs.gamma < 0.06 and fs.loglik >= fs.loglik_symmetric - 1e-6, (fs.gamma, fs.lr_asymmetry)
    e_prev, s2_prev = -0.02, 1e-4
    assert abs(next_variance(f, e_prev, s2_prev) - (f.omega + (f.alpha + f.gamma) * 4e-4 + f.beta * 1e-4)) < 1e-15
    # Hansen skew-t: unit variance, zero mean, CDF/quantile round trip, lambda recovered from a skewed series
    rng = np.random.default_rng(5)
    z = skewt_ppf(rng.random(400_000), 6.0, -0.3)
    assert abs(z.mean()) < 0.01 and abs(z.var() - 1.0) < 0.02 and sps.skew(z) < -0.3, (z.mean(), z.var(), sps.skew(z))
    u = np.linspace(0.001, 0.999, 999)
    assert np.max(np.abs(skewt_cdf(skewt_ppf(u, 5.0, 0.4), 5.0, 0.4) - u)) < 1e-9
    assert np.allclose(skewt_cdf([-1.0, 0.0, 2.0], 7.0, 0.0), sps.t.cdf(np.array([-1.0, 0.0, 2.0]) / math.sqrt(5 / 7), 7.0))
    zs = skewt_ppf(rng.random(3000), 6.0, -0.3)
    rs, s2, e_prev = np.empty(3000), 2e-6 / (1 - 0.03 - 0.90 - 0.05), 0.0
    for t in range(3000):
        s2 = 2e-6 + (0.03 + 0.10 * (e_prev < 0)) * e_prev ** 2 + 0.90 * s2
        e_prev = math.sqrt(s2) * zs[t]
        rs[t] = e_prev
    fk = fit_gjr(rs, dist="skewt")
    assert abs(fk.lam + 0.3) < 0.1 and 3.5 < fk.nu < 12 and fk.loglik > fit_gjr(rs, dist="t").loglik, (fk.lam, fk.nu)
    assert fit_gjr(rs, dist="t").lam == 0.0
    print("ok", f"gamma {f.gamma:.3f} LR {f.lr_asymmetry:.1f} skew-t lambda {fk.lam:+.2f}")
