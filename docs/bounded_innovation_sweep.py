"""Choose Z_BOUND: the |z| cap on simulated Student-t innovations.

For every integer bound A the exact per-step martingale correction
c_A(sigma) = ln E[exp(sigma z) | |z| <= A] is computed (core.quant.garch), a
GARCH-t is simulated under the risk-free rate with rate/252 - c_A(sigma_t) per
step, and the bounded run is compared, PAIRED (same seed: only the days whose
|z| exceeded A differ), with an unbounded run that adds the same drift.

Metrics per (parameter set, horizon, nu, A):
  gap_se     |mean(P_T)/spot - exp(rf T)| in Monte Carlo standard errors of the
             bounded run: the correction is exact iff this stays below 3.
  se5k_mean  relative standard error of mean(P_T)/spot at the app's default
             5,000 paths: the precision with which the martingale property can
             be checked; it grows with A (heavier tail inside the bound).
  d_<stat>   paired change vs the unbounded run in the median, q05, q95,
             P(loss), VaR95, CVaR95 of the horizon return, divided by that
             statistic's own 5,000-path standard error (10 groups of 5,000).
             Below 1 the bound is invisible at the resolution the app shows.
  out_per_yr expected number of days per year on which the fitted t would
             exceed the bound: what the bound refuses to reproduce.
  var_in     variance of the bounded innovation (1 - the tail's share).
  ref_gap_se the UNBOUNDED run's own mean gap in its SEs (no correction is
             exact for it; this shows why bounding is needed).

Selection, in two stages.
  Stage 1 (the paired sweep above) sets the FLOOR of the feasible band:
    (a) reproducibility: out_per_yr <= 0.1 at every nu, i.e. an innovation the
        fitted model produces more often than once a decade must remain
        possible (the app calibrates on two years and simulates up to five);
    (b) invisibility where the tail is estimable: every d_<stat> < 1 for
        nu >= 4, the range the primer calls typical for daily equity data.
        Below nu = 4 the unbounded model's CVaR95 is carried by once-a-century
        days that no estimable bound can keep, so the change is reported
        (var_in, d_cvar95) and stated in the Quant Lab's bound note rather
        than required to vanish.
  Stage 2 (multi-seed estimability) sets the TOP: the correction is exact for
    every bound, but the sample mean of a GARCH-t with a huge-but-bounded tail
    falls short of the true mean (one extreme day explodes the variance
    recursion), and the shortfall grows with A. For the heaviest nu, several
    seeds and a coarse A grid, the SIGNED shortfall mean(P_T)/spot - exp(rf T)
    is averaged over seeds and compared with the 5,000-path standard error of
    the mean: the martingale property holds at the app's own resolution while
    |shortfall| < se_app. The top is the largest A for which that holds in
    every configuration (contiguously from the floor). A single-seed max of
    gap_se over 28 cells, the first version of this rule, moved with Monte
    Carlo noise (one cell at 3.01 SE decided it), which is why the top is
    estimated this way.
  Z_BOUND = the midpoint of the band, the integer farthest from both failure
    modes. Both edges are estimates; the tables show the trade-off so the
    choice can be re-run and re-argued.

Run from the project root:  PYTHONPATH=. python docs/bounded_innovation_sweep.py
Writes docs/bounded_innovation_sweep.csv and docs/bounded_innovation_sweep.md.
"""
from __future__ import annotations

import csv
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.quant.garch import TRADING_DAYS, _draw_z, _t_scale, bounded_t_stats, martingale_correction  # noqa: E402

NUS = (2.5, 3.1, 4.0, 6.0, 8.0, 12.0, 30.0)
BOUNDS = [3, 4, 5, 6, 8] + list(range(10, 25)) + [26, 28, 30, 35, 40, 50, 60, 80, 100]
PARAMS = {"worked": dict(alpha=0.176, beta=0.655, uncond=0.333),     # the primer's AAPL fit
          "typical": dict(alpha=0.08, beta=0.90, uncond=0.25)}       # the primer's typical daily-equity values
CONFIGS = (("worked", 126), ("typical", 126), ("worked", 21), ("worked", 252))
N_PATHS = 50_000
N_APP = 5_000                     # the app's default path count
RF = 0.03
SEED = 7
STAGE2_SEEDS = (11, 12, 13, 14, 15)
STAGE2_NUS = (2.5, 3.1)                                  # where estimability fails first
STAGE2_A = (12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 35, 40)
STAGE2_CONFIGS = (("worked", 126), ("typical", 126), ("worked", 252))
OUT = Path(__file__).resolve().parent


def simulate(nu, bound, alpha, beta, uncond, horizon, corr_bound, seed=SEED):
    """Terminal P_T/spot under rate RF with the exact correction for `corr_bound`;
    draws bounded at `bound` (None = unbounded). Same seed => same t draws."""
    rng = np.random.default_rng(seed)
    omega = uncond ** 2 / TRADING_DAYS * (1.0 - alpha - beta)
    z = _draw_z(rng, nu, "t", (N_PATHS, horizon), bound)
    s2 = np.full(N_PATHS, uncond ** 2 / TRADING_DAYS)
    logp = np.zeros(N_PATHS)
    rate = RF / TRADING_DAYS
    for h in range(horizon):
        sig = np.sqrt(s2)
        eps = sig * z[:, h]
        logp += rate - martingale_correction(sig, nu, "t", corr_bound) + eps
        s2 = omega + alpha * eps ** 2 + beta * s2
    return np.exp(logp)


def statistics(x):
    """The numbers the app reports, from terminal P_T/spot."""
    loss = 1.0 - x
    var = float(np.percentile(loss, 95))
    return {"median": float(np.median(x)), "q05": float(np.percentile(x, 5)),
            "q95": float(np.percentile(x, 95)), "ploss": float(np.mean(x < 1.0)),
            "var95": var, "cvar95": float(np.mean(loss[loss >= var]))}


def se_at_app_resolution(x):
    """Standard error of each statistic at N_APP paths: std across disjoint groups."""
    groups = [statistics(g) for g in np.array_split(x, N_PATHS // N_APP)]
    return {k: float(np.std([g[k] for g in groups], ddof=1)) for k in groups[0]}


def stage1():
    rows = []
    t0 = time.time()
    for pname, horizon in CONFIGS:
        p = PARAMS[pname]
        T = horizon / TRADING_DAYS
        target = math.exp(RF * T)
        for nu in NUS:
            s = _t_scale(nu)
            for A in BOUNDS:
                xb = simulate(nu, A, p["alpha"], p["beta"], p["uncond"], horizon, A)
                xu = simulate(nu, None, p["alpha"], p["beta"], p["uncond"], horizon, A)
                sb, su = statistics(xb), statistics(xu)
                se = se_at_app_resolution(xb)
                mass, var_in = bounded_t_stats(nu, A)
                out_per_day = 1.0 - mass
                row = {"params": pname, "horizon": horizon, "nu": nu, "A": A,
                       "gap_se": abs(xb.mean() - target) / (xb.std(ddof=1) / math.sqrt(N_PATHS)),
                       "se5k_mean": xb.std(ddof=1) / math.sqrt(N_APP),
                       "ref_gap_se": abs(xu.mean() - target) / (xu.std(ddof=1) / math.sqrt(N_PATHS)),
                       "out_per_yr": out_per_day * TRADING_DAYS, "var_in": var_in,
                       "max_z_unbounded": float(np.abs(stats.t(nu).ppf(1e-9) * s))}
                for k in sb:
                    row[f"d_{k}"] = abs(sb[k] - su[k]) / se[k] if se[k] > 0 else 0.0
                row["d_max"] = max(row[f"d_{k}"] for k in sb)
                rows.append(row)
            print(f"{pname:8s} h={horizon:4d} nu={nu:5.1f} done  ({time.time() - t0:5.0f} s)", flush=True)
    return rows


def stage2():
    """Signed shortfall of the mean, averaged over seeds, against the 5,000-path SE."""
    rows = []
    t0 = time.time()
    for pname, horizon in STAGE2_CONFIGS:
        p = PARAMS[pname]
        target = math.exp(RF * horizon / TRADING_DAYS)
        for nu in STAGE2_NUS:
            for A in STAGE2_A:
                gaps, sds = [], []
                for seed in STAGE2_SEEDS:
                    x = simulate(nu, A, p["alpha"], p["beta"], p["uncond"], horizon, A, seed=seed)
                    gaps.append(float(x.mean()) - target)
                    sds.append(float(x.std(ddof=1)))
                se_app = float(np.mean(sds)) / math.sqrt(N_APP)
                rows.append({"params": pname, "horizon": horizon, "nu": nu, "A": A,
                             "shortfall": float(np.mean(gaps)),
                             "shortfall_se": float(np.std(gaps, ddof=1)) / math.sqrt(len(gaps)),
                             "se_app": se_app, "ratio": float(np.mean(gaps)) / se_app})
            print(f"stage 2 {pname:8s} h={horizon:4d} nu={nu:5.1f} done  ({time.time() - t0:5.0f} s)", flush=True)
    return rows


def main():
    if "--from-csv" in sys.argv:
        rows = []
        for r in csv.DictReader(open(OUT / "bounded_innovation_sweep.csv")):
            row = {k: (v if k == "params" else float(v)) for k, v in r.items()}
            row["horizon"], row["A"] = int(row["horizon"]), int(row["A"])
            rows.append(row)
    else:
        rows = stage1()
    rows2 = stage2()
    with open(OUT / "bounded_innovation_estimability.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows2[0].keys()))
        w.writeheader()
        w.writerows(rows2)

    if "--from-csv" not in sys.argv:
        with open(OUT / "bounded_innovation_sweep.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    # Stage-1 floor: reproducibility and invisibility for nu >= 4.
    feasible = {}
    for A in BOUNDS:
        rs = [r for r in rows if r["A"] == A]
        feasible[A] = (max(r["out_per_yr"] for r in rs) <= 0.1
                       and max(r["d_max"] for r in rs if r["nu"] >= 4.0) < 1.0)
    floor = next((A for A in BOUNDS if feasible[A]), None)
    # Stage-2 top: the shortfall of the mean stays inside the app's own standard
    # error, contiguously over the stage-2 grid.
    passes = {A: all(abs(r["ratio"]) < 1.0 for r in rows2 if r["A"] == A) for A in STAGE2_A}
    top = None
    for A in STAGE2_A:
        if floor is None or A < floor:
            continue
        if passes[A]:
            top = A
        else:
            break
    chosen = int(round((floor + top) / 2.0)) if (floor is not None and top is not None) else None

    def worst(A, key):
        return max(r[key] for r in rows if r["A"] == A)

    lines = ["# Choosing Z_BOUND: the sweep", "",
             f"{len(rows)} paired simulations: parameter sets {list(PARAMS)} x horizons "
             f"{sorted({h for _, h in CONFIGS})} x nu {list(NUS)} x integer bounds {BOUNDS[0]}..{BOUNDS[-1]}; "
             f"{N_PATHS:,} paths each, rf {RF:.0%}, seed {SEED}. Statistics' standard errors are at the app's "
             f"default {N_APP:,} paths.", "",
             "Selection rule: the floor is the smallest A with at most 0.1 out-of-bound days per year at every nu "
             "(reproducibility) and every paired change below one 5,000-path standard error for nu >= 4 "
             "(invisibility where the tail is estimable); the top is the largest A, contiguously from the floor, at "
             "which the seed-averaged signed shortfall of the mean stays inside the 5,000-path standard error in "
             "every stage-2 configuration (the martingale property holds at the app's resolution). "
             "Z_BOUND = the midpoint of the band.", "",
             (f"**Chosen: Z_BOUND = {chosen}** (band {floor}..{top}: floor from stage 1, top from stage 2)"
              if chosen is not None else "**No bound in the grid satisfies the rule**"), "",
             "## Stage 2: seed-averaged shortfall of the mean, in 5,000-path standard errors", "",
             "| A | " + " | ".join(f"{p} h={h} nu={nu}" for p, h in STAGE2_CONFIGS for nu in STAGE2_NUS) + " | passes |",
             "|---|" + "---|" * (len(STAGE2_CONFIGS) * len(STAGE2_NUS)) + "---|"]
    for A in STAGE2_A:
        cells = []
        for p_, h_ in STAGE2_CONFIGS:
            for nu_ in STAGE2_NUS:
                r = next(r for r in rows2 if r["params"] == p_ and r["horizon"] == h_
                         and r["nu"] == nu_ and r["A"] == A)
                cells.append(f"{r['ratio']:+.2f} (±{r['shortfall_se'] / r['se_app']:.2f})")
        lines.append(f"| {A} | " + " | ".join(cells) + f" | {'yes' if passes[A] else 'no'} |")
    lines += ["", "A cell is (mean over 5 seeds of mean(P_T)/spot - exp(rf T)) / SE_5000, ± its own seed standard "
              "error in the same units; a negative value is the shortfall a heavy right tail produces in a finite "
              "sample. The martingale test holds at the app's resolution while |cell| < 1.", "",
             "## Stage 1: worst case over all configurations, per bound", "",
             "| A | gap_se (max, all nu) | d_max (max, nu >= 4) | d_cvar95 (nu = 3.1) | d_cvar95 (nu = 2.5) | out-of-bound days/yr (nu = 2.5) | var_in (nu = 3.1) | var_in (nu = 2.5) | se5k_mean (max) | ref_gap_se (max) | feasible |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for A in BOUNDS:
        at = lambda nu, key: max(r[key] for r in rows if r["A"] == A and r["nu"] == nu)
        lines.append(f"| {A} | {worst(A, 'gap_se'):.2f} | "
                     f"{max(r['d_max'] for r in rows if r['A'] == A and r['nu'] >= 4.0):.2f} | "
                     f"{at(3.1, 'd_cvar95'):.1f} | {at(2.5, 'd_cvar95'):.1f} | {at(2.5, 'out_per_yr'):.3f} | "
                     f"{at(3.1, 'var_in'):.3f} | {at(2.5, 'var_in'):.3f} | {worst(A, 'se5k_mean'):.4f} | "
                     f"{worst(A, 'ref_gap_se'):.1f} | {'yes' if feasible[A] else 'no'} |")
    lines += ["", "## Per nu at the chosen bound (worked-fit parameters, 126 sessions)", "",
              "| nu | gap_se | d_median | d_q05 | d_q95 | d_ploss | d_var95 | d_cvar95 | out/yr | var_in | se5k_mean | ref_gap_se |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    if chosen is not None:
        for r in rows:
            if r["A"] == chosen and r["params"] == "worked" and r["horizon"] == 126:
                lines.append(f"| {r['nu']} | {r['gap_se']:.2f} | {r['d_median']:.2f} | {r['d_q05']:.2f} | {r['d_q95']:.2f} | "
                             f"{r['d_ploss']:.2f} | {r['d_var95']:.2f} | {r['d_cvar95']:.2f} | {r['out_per_yr']:.3f} | "
                             f"{r['var_in']:.3f} | {r['se5k_mean']:.4f} | {r['ref_gap_se']:.1f} |")
    lines += ["", "Columns: gap_se = |mean(P_T)/spot - exp(rf T)| in MC standard errors with the exact bounded "
              "correction; d_<stat> = paired change versus the unbounded draw, in that statistic's 5,000-path "
              "standard errors; out/yr = expected days per year beyond the bound under the fitted t; var_in = variance "
              "of the bounded innovation; se5k_mean = relative standard error of the mean at 5,000 paths; "
              "ref_gap_se = the unbounded run's own gap (no exact correction exists for it).", "",
              "Reading the tables: stage 2 caps the bound (estimability of the mean at the app's resolution); "
              "reproducibility floors it; for nu >= 4 the bound is invisible inside the band; for nu < 4 the bound "
              "lowers CVaR95 by the once-a-century days it refuses and the fan's long-run vol by "
              "sqrt(var_in (1-alpha-beta)/(1-alpha var_in-beta)), both stated in the Quant Lab's bound note. gap_se "
              "in stage 1 is a single-seed max over 28 cells and is reported, not used: it sits on its noise plateau "
              "(2.3-3.0) up to about A = 23 and rises only beyond."]
    (OUT / "bounded_innovation_sweep.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:8]))
    print(f"chosen Z_BOUND = {chosen}")


if __name__ == "__main__":
    main()
