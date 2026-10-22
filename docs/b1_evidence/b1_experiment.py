"""B1 evidence: eta = 1/nu reparameterisation of the GARCH-t fit, prototyped OUTSIDE the app.

Experiments
  1. nesting: LR on series where the current fit reports LR < 0
  2. null distribution of LR under normal innovations (size at 2.706 and 3.841)
  3. power on t innovations for several nu (rejection at 2.706 vs 3.841, eta fit vs current fit)
  4. point-estimate equivalence on an interior-nu series
  5. numerical stability of the eta density at eta -> 0
Outputs a JSON with everything the bulletin quotes.
"""
import json, math, sys, time
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # this repo (TRADEGEN), never QUANTGEN
from core.quant.garch import (BOUNDS, STATIONARITY_MAX, _OMEGA_SCALE, _PENALTY, _variance_path,
                              fit_garch, simulate_garch_series)
from core.quant.history import synthetic_history

ETA_MAX = 0.4                     # nu >= 2.5, the current lower bound
ETA_EPS = 1e-8                    # below this the t is the normal to double precision


def loglik_eta(params, eps, eps2, s2_init):
    omega, alpha, beta, eta = params
    if alpha + beta > STATIONARITY_MAX:
        return -_PENALTY
    s2 = _variance_path(eps2, omega, alpha, beta, s2_init)[:-1]
    if not np.all(np.isfinite(s2)) or np.any(s2 <= 0):
        return -_PENALTY
    if eta < ETA_EPS:                                   # eta = 0 IS the normal
        return float(np.sum(-0.5 * math.log(2 * math.pi) - 0.5 * np.log(s2) - eps2 / (2 * s2)))
    nu = 1.0 / eta
    c = gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * math.log(math.pi * (nu - 2))
    return float(np.sum(c - 0.5 * np.log(s2) - ((nu + 1) / 2) * np.log1p(eps2 / ((nu - 2) * s2))))


def fit_eta(r):
    """Same estimator as the app, but nu enters as eta = 1/nu in [0, 0.4]; the
    normal-GARCH optimum (eta = 0) is one of the starts, so LR >= 0 by construction."""
    r = np.asarray(r, float)
    eps = r - r.mean(); eps2 = eps ** 2; var = float(np.var(eps))
    scale = np.array([_OMEGA_SCALE, 1.0, 1.0, 1.0])
    bounds = [(BOUNDS["omega"][0] * _OMEGA_SCALE, None), BOUNDS["alpha"], BOUNDS["beta"], (0.0, ETA_MAX)]
    normal = fit_garch(r, dist="normal")
    starts = [[normal.omega, normal.alpha, normal.beta, 0.0]]
    for beta0 in (0.80, 0.90, 0.95):
        starts.append([var * (1 - 0.05 - beta0), 0.05, beta0, 1.0 / 8.0])
    best = None
    for x0 in starts:
        res = minimize(lambda p: -loglik_eta(p / scale, eps, eps2, var), np.array(x0) * scale,
                       method="L-BFGS-B", bounds=bounds)
        if best is None or res.fun < best.fun:
            best = res
    p = best.x / scale
    ll_t = float(-best.fun)
    return dict(omega=p[0], alpha=p[1], beta=p[2], eta=p[3], nu=(math.inf if p[3] < ETA_EPS else 1.0 / p[3]),
                loglik=ll_t, loglik_normal=normal.loglik, lr=2.0 * (ll_t - normal.loglik),
                converged=bool(best.success))


out = {}
t0 = time.time()

# 1. nesting on the two series the primer / self-check use
cases = {"iid_normal_500": np.random.default_rng(2).normal(0.0004, 0.012, 500),
         "gbm_demo_AAPL": synthetic_history("AAPL").log_returns()}
out["nesting"] = {}
for name, r in cases.items():
    cur = fit_garch(r, dist="t"); new = fit_eta(r)
    out["nesting"][name] = {"current_lr": cur.lr_t_vs_normal, "current_nu": cur.nu, "current_at_bound": list(cur.at_bound),
                            "eta_lr": new["lr"], "eta_eta": new["eta"], "eta_nu": new["nu"]}
print("1. nesting", json.dumps(out["nesting"], indent=1), f"({time.time()-t0:.0f}s)", flush=True)

# 2. null distribution: normal-GARCH innovations, 500 obs, 300 seeds
n_null, T = 300, 500
lr_cur, lr_eta = [], []
for seed in range(n_null):
    r = simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=T, seed=1000 + seed, dist="normal")
    lr_cur.append(fit_garch(r, dist="t").lr_t_vs_normal)
    lr_eta.append(fit_eta(r)["lr"])
lr_cur, lr_eta = np.array(lr_cur), np.array(lr_eta)
out["null"] = {"n": n_null, "T": T,
               "current": {"frac_negative": float(np.mean(lr_cur < -1e-9)), "min": float(lr_cur.min()),
                           "size_at_3.841": float(np.mean(lr_cur > 3.841)), "size_at_2.706": float(np.mean(lr_cur > 2.706)),
                           "q95": float(np.quantile(lr_cur, 0.95))},
               "eta": {"frac_negative": float(np.mean(lr_eta < -1e-9)), "min": float(lr_eta.min()),
                       "frac_zero": float(np.mean(lr_eta < 1e-6)),
                       "size_at_3.841": float(np.mean(lr_eta > 3.841)), "size_at_2.706": float(np.mean(lr_eta > 2.706)),
                       "q95": float(np.quantile(lr_eta, 0.95)), "q90": float(np.quantile(lr_eta, 0.90))},
               "theory": {"mixture_q95": 2.706, "chi2_q95": 3.841, "mixture_frac_zero": 0.5,
                          "chi2_threshold_true_size_under_mixture": 0.025}}
print("2. null", json.dumps(out["null"], indent=1), f"({time.time()-t0:.0f}s)", flush=True)

# 3. power on t innovations, 500 obs, 150 seeds per nu
out["power"] = {}
for nu_true in (5.0, 8.0, 12.0, 20.0):
    rej = {"current_3.841": 0, "eta_3.841": 0, "eta_2.706": 0}
    n_pow = 150
    for seed in range(n_pow):
        r = simulate_garch_series(2e-6, 0.08, 0.90, nu_true, n=T, seed=5000 + seed, dist="t")
        rej["current_3.841"] += fit_garch(r, dist="t").lr_t_vs_normal > 3.841
        lr = fit_eta(r)["lr"]
        rej["eta_3.841"] += lr > 3.841
        rej["eta_2.706"] += lr > 2.706
    out["power"][str(nu_true)] = {k: v / n_pow for k, v in rej.items()}
    print(f"3. power nu={nu_true}", out["power"][str(nu_true)], f"({time.time()-t0:.0f}s)", flush=True)

# 4. point-estimate equivalence on an interior-nu series (the app's own recovery test series)
r = simulate_garch_series(2e-6, 0.08, 0.90, 6.0, n=3000, seed=1)
cur = fit_garch(r, dist="t"); new = fit_eta(r)
out["equivalence"] = {"current": {"alpha": cur.alpha, "beta": cur.beta, "nu": cur.nu, "loglik": cur.loglik},
                      "eta": {"alpha": new["alpha"], "beta": new["beta"], "nu": new["nu"], "loglik": new["loglik"]}}
print("4. equivalence", json.dumps(out["equivalence"], indent=1), flush=True)

# 5. numerical stability: the eta density approaches the normal smoothly
r = cases["iid_normal_500"]; eps = r - r.mean(); eps2 = eps ** 2; var = float(np.var(eps))
ll_n = loglik_eta(np.array([var * 0.1, 0.05, 0.85, 0.0]), eps, eps2, var)
out["stability"] = {f"eta={e:g}": loglik_eta(np.array([var * 0.1, 0.05, 0.85, e]), eps, eps2, var) - ll_n
                    for e in (1e-7, 1e-5, 1e-3, 1e-2)}
print("5. stability (loglik(eta) - loglik(normal)):", out["stability"], flush=True)
out["elapsed_s"] = time.time() - t0
json.dump(out, open(Path(__file__).with_name("b1_results.json"), "w"), indent=1)   # was a QUANTGEN session scratchpad
print("done", f"{time.time()-t0:.0f}s")
