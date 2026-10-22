"""B2 evidence: standard errors and confidence intervals for the GARCH(1,1)-t fit,
prototyped OUTSIDE the app on top of the shipped estimator (core.quant.garch).

Three interval methods on the fitted parameters theta = (omega, alpha, beta, eta), eta = 1/nu:
  wald_hess  observed-information (negative numerical Hessian) inverse; the classic MLE result
             (STAT248 21.2.3: sqrt(n)(theta_hat - theta) -> N(0, I^-1), I = -E[Hessian]).
  wald_sand  sandwich H^-1 S H^-1 with S the outer product of per-observation scores; the
             misspecified-model result of the same section (Bollerslev-Wooldridge in GARCH terms).
  profile    profile-likelihood interval for eta: {eta : l_profile(eta) >= l_max - 1.92},
             refitting (omega, alpha, beta) at each eta on a grid; respects eta >= 0 and the
             boundary, and maps to nu by 1/eta (upper end "normal" when the interval reaches 0).
Derived quantities by the delta method from the Wald covariance: persistence alpha + beta,
unconditional vol sqrt(252 omega / (1 - alpha - beta)).

Experiments
  1. coverage under a correctly specified t-GARCH (true omega 2e-6, alpha .08, beta .90, nu 6)
     at T = 500 (200 seeds) and T = 2000 (100 seeds): coverage of 95% intervals per parameter,
     median interval widths, share of fits with a parameter at a bound (no Wald interval there).
  2. coverage under misspecification: same recursion, innovations from a skewed normal mixture
     (the t is the wrong family): Hessian vs sandwich coverage of alpha and beta, T = 1000.
  3. the app's own reference series: the recovery series (3000 obs), the GBM demo (alpha at 0,
     eta at 0), and a 500-session t(3) series: what the tiles would show.
  4. cost: milliseconds per Hessian, per sandwich, per profile.
Writes b2_results.json next to this file.
"""
from __future__ import annotations

import json, math, sys, time
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.quant.garch import (BOUNDS, STATIONARITY_MAX, TRADING_DAYS, _ETA_EPS, _OMEGA_SCALE, _PENALTY,  # noqa: E402
                              _t_const, _variance_path, fit_garch, simulate_garch_series)
from core.quant.history import synthetic_history  # noqa: E402

HERE = Path(__file__).resolve().parent
Z95 = 1.959964
PROFILE_CUT = 1.920729          # chi-square(1) 95% point / 2


# --------------------------------------------------------------------------- #
# Per-observation log-likelihood in the fitted parameterisation (omega, alpha, beta, eta)
# --------------------------------------------------------------------------- #
def loglik_vec(theta, eps, eps2, s2_init):
    omega, alpha, beta, eta = theta
    if alpha + beta > STATIONARITY_MAX or omega <= 0 or alpha < 0 or beta < 0 or eta < 0:
        return None
    s2 = _variance_path(eps2, omega, alpha, beta, s2_init)[:-1]
    if not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        return None
    if eta >= _ETA_EPS:
        nu = 1.0 / eta
        return _t_const(nu) - 0.5 * np.log(s2) - ((nu + 1) / 2) * np.log1p(eps2 / ((nu - 2) * s2))
    return -0.5 * math.log(2 * math.pi) - 0.5 * np.log(s2) - eps2 / (2 * s2)


def loglik(theta, eps, eps2, s2_init):
    v = loglik_vec(theta, eps, eps2, s2_init)
    return -math.inf if v is None else float(v.sum())


def theta_of(fit):
    eta = 0.0 if math.isinf(fit.nu) else 1.0 / fit.nu
    return np.array([fit.omega, fit.alpha, fit.beta, eta])


def at_lower_bound(theta, tol=1e-6):
    """Which parameters sit on a bound where a symmetric step is impossible.
    omega is judged relative to its floor (1e-12): the first run used an absolute
    1e-6, which counted every small omega as 'at bound' (the 6.5 % share_any_bound
    in b2_results.json is that artefact; no fit in that run had omega on its floor)."""
    lo = np.array([BOUNDS["omega"][0], 0.0, 0.0, 0.0])
    out = theta - lo < tol
    out[0] = theta[0] < 2.0 * BOUNDS["omega"][0]
    return out


# --------------------------------------------------------------------------- #
# Numerical derivatives
# --------------------------------------------------------------------------- #
def steps(theta):
    return np.array([1e-3 * max(theta[0], 1e-8), 1e-4, 1e-4, 1e-4])


def hessian(theta, eps, eps2, s2_init):
    """Central-difference Hessian of the summed log-likelihood; one-sided (forward) in any
    coordinate that sits on a lower bound. Returns None if a step lands outside the domain."""
    h = steps(theta); k = theta.size
    lower = at_lower_bound(theta)
    def f(t):
        return loglik(t, eps, eps2, s2_init)
    f0 = f(theta)
    H = np.empty((k, k))
    for i in range(k):
        for j in range(i, k):
            ei = np.zeros(k); ei[i] = h[i]
            ej = np.zeros(k); ej[j] = h[j]
            if not lower[i] and not lower[j]:
                val = (f(theta + ei + ej) - f(theta + ei - ej) - f(theta - ei + ej) + f(theta - ei - ej)) / (4 * h[i] * h[j])
            else:                       # forward differences where a bound blocks the symmetric step
                si = 1.0; sj = 1.0
                val = (f(theta + si * ei + sj * ej) - f(theta + si * ei) - f(theta + sj * ej) + f0) / (si * sj * h[i] * h[j])
            if not math.isfinite(val):
                return None
            H[i, j] = H[j, i] = val
    return H


def scores(theta, eps, eps2, s2_init):
    """Per-observation score matrix (T x k) by central (or forward at a bound) differences."""
    h = steps(theta); k = theta.size
    lower = at_lower_bound(theta)
    base = loglik_vec(theta, eps, eps2, s2_init)
    S = np.empty((base.size, k))
    for i in range(k):
        e = np.zeros(k); e[i] = h[i]
        up = loglik_vec(theta + e, eps, eps2, s2_init)
        if lower[i]:
            S[:, i] = (up - base) / h[i]
        else:
            dn = loglik_vec(theta - e, eps, eps2, s2_init)
            if up is None or dn is None:
                return None
            S[:, i] = (up - dn) / (2 * h[i])
    return S


def covariances(theta, eps, eps2, s2_init):
    """(Wald covariance from the observed information, sandwich covariance) or (None, None)."""
    H = hessian(theta, eps, eps2, s2_init)
    if H is None:
        return None, None
    info = -H
    try:
        cov_h = np.linalg.inv(info)
    except np.linalg.LinAlgError:
        return None, None
    if np.any(np.diag(cov_h) <= 0):
        return None, None
    S = scores(theta, eps, eps2, s2_init)
    if S is None:
        return cov_h, None
    B = S.T @ S
    cov_s = cov_h @ B @ cov_h
    return cov_h, (cov_s if np.all(np.diag(cov_s) > 0) else None)


# --------------------------------------------------------------------------- #
# Profile likelihood in eta
# --------------------------------------------------------------------------- #
def fit_fixed_eta(eps, eps2, s2_init, eta, start):
    scale = np.array([_OMEGA_SCALE, 1.0, 1.0])
    bounds = [(BOUNDS["omega"][0] * _OMEGA_SCALE, None), BOUNDS["alpha"], BOUNDS["beta"]]
    def obj(p):
        t = np.array([p[0] / scale[0], p[1], p[2], eta])
        v = loglik(t, eps, eps2, s2_init)
        return _PENALTY if not math.isfinite(v) else -v
    res = minimize(obj, np.array(start) * scale, method="L-BFGS-B", bounds=bounds)
    return -res.fun, res.x / scale


def profile_interval(theta_hat, ll_max, eps, eps2, s2_init, grid=None):
    """Profile 95% interval for eta as (lo, hi); hi = 0.4 or lo = 0 when the interval
    reaches the bound. Grid is scanned outward from the MLE with warm starts."""
    if grid is None:
        grid = np.linspace(0.0, BOUNDS["eta"][1], 41)
    eta_hat = theta_hat[3]
    prof = {}
    # scan up
    start = theta_hat[:3].copy()
    for g in grid[grid > eta_hat]:
        ll, start = fit_fixed_eta(eps, eps2, s2_init, float(g), start)
        prof[float(g)] = ll
        if ll < ll_max - PROFILE_CUT - 1.0:
            break
    start = theta_hat[:3].copy()
    for g in grid[grid < eta_hat][::-1]:
        ll, start = fit_fixed_eta(eps, eps2, s2_init, float(g), start)
        prof[float(g)] = ll
        if ll < ll_max - PROFILE_CUT - 1.0:
            break
    prof[float(eta_hat)] = ll_max
    xs = np.array(sorted(prof)); ys = np.array([prof[x] for x in xs])
    inside = ys >= ll_max - PROFILE_CUT
    lo = float(xs[inside].min()); hi = float(xs[inside].max())
    # refine each end by linear interpolation between the last inside and first outside point
    def refine(a, b):
        if a is None or b is None:
            return None
        fa, fb = prof[a], prof[b]
        cut = ll_max - PROFILE_CUT
        return float(a + (b - a) * (fa - cut) / (fa - fb)) if fa != fb else a
    i_lo = np.where(xs == lo)[0][0]; i_hi = np.where(xs == hi)[0][0]
    lo_r = refine(lo, float(xs[i_lo - 1])) if i_lo > 0 else 0.0
    hi_r = refine(hi, float(xs[i_hi + 1])) if i_hi < xs.size - 1 else float(BOUNDS["eta"][1])
    return max(0.0, lo_r if lo_r is not None else lo), min(BOUNDS["eta"][1], hi_r if hi_r is not None else hi)


# --------------------------------------------------------------------------- #
# One full analysis of a return series
# --------------------------------------------------------------------------- #
def analyse(r):
    fit = fit_garch(r, dist="t")
    eps = r - r.mean(); eps2 = eps ** 2; s2_init = float(np.var(eps))
    theta = theta_of(fit)
    t0 = time.perf_counter(); cov_h, cov_s = covariances(theta, eps, eps2, s2_init); t_cov = time.perf_counter() - t0
    t0 = time.perf_counter(); prof = profile_interval(theta, fit.loglik, eps, eps2, s2_init); t_prof = time.perf_counter() - t0
    out = {"theta": theta.tolist(), "nu": fit.nu, "loglik": fit.loglik, "at_bound": list(fit.at_bound),
           "bound_mask": at_lower_bound(theta).tolist(), "profile_eta": list(prof),
           "t_cov_ms": t_cov * 1000, "t_profile_ms": t_prof * 1000}
    for name, cov in (("hess", cov_h), ("sand", cov_s)):
        if cov is None:
            out[f"se_{name}"] = None
            continue
        se = np.sqrt(np.diag(cov))
        g = np.array([0.0, 1.0, 1.0, 0.0])                       # persistence = alpha + beta
        out[f"se_{name}"] = se.tolist()
        out[f"se_{name}_persistence"] = float(math.sqrt(g @ cov @ g))
        p = theta[1] + theta[2]
        if p < 1:                                                  # uncond var = 252 omega / (1 - p)
            u = TRADING_DAYS * theta[0] / (1 - p)
            gu = np.array([TRADING_DAYS / (1 - p), u / (1 - p), u / (1 - p), 0.0])
            var_u = float(gu @ cov @ gu)
            out[f"se_{name}_uncond_vol"] = float(0.5 / math.sqrt(u) * math.sqrt(var_u)) if var_u > 0 else None
    return out


def wald_covers(theta_true_i, est, se):
    return abs(est - theta_true_i) <= Z95 * se


def coverage_study(T, n_seeds, true, innovations="t", label=""):
    om, al, be, nu = true["omega"], true["alpha"], true["beta"], true["nu"]
    eta_true = 1.0 / nu
    rows = []
    for seed in range(n_seeds):
        if innovations == "t":
            r = simulate_garch_series(om, al, be, nu, n=T, seed=7000 + seed)
        else:                                                      # skewed normal mixture, unit variance
            rng = np.random.default_rng(7000 + seed)
            burn = 500
            comp = rng.random(T + burn) < 0.9
            z = np.where(comp, rng.normal(0.1, 0.8, T + burn), rng.normal(-0.9, 1.5, T + burn))
            z = (z - z.mean()) / z.std()
            e = np.empty(T + burn); s2 = om / (1 - al - be)
            for t in range(T + burn):
                e[t] = math.sqrt(s2) * z[t]; s2 = om + al * e[t] ** 2 + be * s2
            r = e[burn:]
        a = analyse(r)
        rows.append(a)
    # aggregate
    names = ["omega", "alpha", "beta", "eta"]
    truth = [om, al, be, eta_true]
    agg = {"label": label, "T": T, "n": n_seeds, "innovations": innovations}
    usable_h = [a for a in rows if a["se_hess"] is not None]
    usable_s = [a for a in rows if a["se_sand"] is not None]
    agg["share_any_bound"] = float(np.mean([any(a["bound_mask"]) for a in rows]))
    agg["share_hess_available"] = len(usable_h) / n_seeds
    agg["share_sand_available"] = len(usable_s) / n_seeds
    for i, nm in enumerate(names):
        agg[f"cov_hess_{nm}"] = float(np.mean([wald_covers(truth[i], a["theta"][i], a["se_hess"][i]) for a in usable_h])) if usable_h else None
        agg[f"cov_sand_{nm}"] = float(np.mean([wald_covers(truth[i], a["theta"][i], a["se_sand"][i]) for a in usable_s])) if usable_s else None
        agg[f"median_se_hess_{nm}"] = float(np.median([a["se_hess"][i] for a in usable_h])) if usable_h else None
        agg[f"median_se_sand_{nm}"] = float(np.median([a["se_sand"][i] for a in usable_s])) if usable_s else None
        agg[f"sd_estimates_{nm}"] = float(np.std([a["theta"][i] for a in rows], ddof=1))
    agg["cov_profile_eta"] = float(np.mean([a["profile_eta"][0] <= eta_true <= a["profile_eta"][1] for a in rows]))
    agg["median_profile_width_eta"] = float(np.median([a["profile_eta"][1] - a["profile_eta"][0] for a in rows]))
    agg["share_profile_reaches_zero"] = float(np.mean([a["profile_eta"][0] <= 1e-9 for a in rows]))
    p_true = al + be
    agg["cov_hess_persistence"] = float(np.mean([wald_covers(p_true, a["theta"][1] + a["theta"][2], a["se_hess_persistence"]) for a in usable_h])) if usable_h else None
    agg["cov_sand_persistence"] = float(np.mean([wald_covers(p_true, a["theta"][1] + a["theta"][2], a["se_sand_persistence"]) for a in usable_s])) if usable_s else None
    # nu interval by transforming the eta interval (profile) and by Wald on eta
    nu_ok_prof = [(1.0 / a["profile_eta"][1] <= nu <= (math.inf if a["profile_eta"][0] <= 1e-9 else 1.0 / a["profile_eta"][0])) for a in rows]
    agg["cov_profile_nu"] = float(np.mean(nu_ok_prof))
    agg["t_cov_ms_median"] = float(np.median([a["t_cov_ms"] for a in rows]))
    agg["t_profile_ms_median"] = float(np.median([a["t_profile_ms"] for a in rows]))
    return agg, rows


def main():
    out = {}
    t0 = time.time()
    true = dict(omega=2e-6, alpha=0.08, beta=0.90, nu=6.0)
    agg500, rows500 = coverage_study(500, 200, true, "t", "t-GARCH, T=500")
    print("coverage T=500:", json.dumps(agg500, indent=1), f"({time.time()-t0:.0f}s)", flush=True)
    agg2000, _ = coverage_study(2000, 100, true, "t", "t-GARCH, T=2000")
    print("coverage T=2000:", json.dumps(agg2000, indent=1), f"({time.time()-t0:.0f}s)", flush=True)
    aggmis, _ = coverage_study(1000, 150, true, "skewmix", "skewed-mixture innovations, T=1000")
    print("misspecified:", json.dumps(aggmis, indent=1), f"({time.time()-t0:.0f}s)", flush=True)
    out["coverage"] = {"t500": agg500, "t2000": agg2000, "misspecified": aggmis}

    # 3. reference series
    ref = {}
    ref["recovery_3000"] = analyse(simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=3000, seed=1))
    ref["gbm_demo"] = analyse(synthetic_history("AAPL").log_returns())
    ref["t3_500"] = analyse(simulate_garch_series(2e-6, 0.10, 0.80, 3.0, n=500, seed=9))
    ref["t6_500"] = analyse(rows500 and simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=500, seed=7000))
    out["reference"] = ref
    for k, v in ref.items():
        print(k, json.dumps({kk: vv for kk, vv in v.items()}, indent=None)[:900], flush=True)
    out["elapsed_s"] = time.time() - t0
    json.dump(out, open(HERE / "b2_results.json", "w"), indent=1)
    print("done", f"{time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
