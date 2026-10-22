"""Monte Carlo simulation of forward price paths.

Four models, all calibrated from the supplied history's daily log returns:

  * **GARCH_T** (default) — GARCH(1,1) with Student-t innovations, fitted by
    `core.quant.garch`. Volatility clusters and the tails are fat; the fan
    starts from today's conditional vol, not the sample average. Every
    guardrail the fit hit is carried on `MCResult.garch`.
  * **GBM** — geometric Brownian motion with the sample drift and volatility.
  * **JUMP** — Merton jump-diffusion. Jumps are calibrated by splitting the
    return sample at 3σ: the outlier frequency sets the jump intensity, the
    outliers themselves set the jump size distribution. With no outliers in
    the sample it degrades to GBM, which is the honest answer.
  * **BOOTSTRAP** — stationary block bootstrap of the actual return sample.
    No distributional assumption: fat tails and volatility clustering survive
    exactly as far as they exist in the data.

DRIFT — every model draws zero-mean shocks; `drift` chooses what is added:

  * **premium** (default) — an arithmetic expected return rf + ERP: the
    risk-free rate plus an equity-risk-premium assumption. The out-of-sample
    study in `docs/drift_study/` found this the only centre that is never the
    worst in any asset class and statistically ties a flat zero.
  * **rf** — the arithmetic rate rf: the risk-neutral (pricing) measure, not
    a forecast; it exists so the fan can show what the structuring pages
    assume.
  * **zero** — log drift 0: the stress view; nothing in that study beats it
    significantly.
  * **sample** — log drift = the trailing-window mean of daily log returns
    × 252: the old default, kept for transparency. Its standard error is
    σ/√years (about 18% a year on a 25%-vol name over two years) and its
    correlation with the next year's return in the study was −0.01.

An arithmetic rate is turned into a log drift STEP BY STEP with each model's
own exact convexity correction c_t = ln E[exp(shock_t)], so that
E[P_T] = spot · exp(rate · T) for every model, not only GBM: GBM subtracts
½σ² of the sample variance (the lognormal correction); the jump model its
diffusion half-variance plus the jump compensator; the bootstrap the
increments of the empirical block log-MGF; GARCH-t subtracts c(σ_t) from
each path's own conditional variance, which exists only because its t
innovations are bounded (`core.quant.garch.Z_BOUND`). `mu_annual` reports
the effective annualised log drift (rate − the horizon-average correction),
`correction_annual` that correction, and `drift_note` spells out the
arithmetic.

Every run is seeded, so the same inputs draw the same paths — a simulation
that repaints on every refresh cannot be reasoned about, and cannot be tested.

The result object carries the percentile fan (not the raw path matrix — 10,000
paths × 252 steps is ~20 MB nobody reads), the terminal distribution, and the
risk numbers read off it: VaR, CVaR, probability of loss, probability of
reaching a target.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.special import gammaln

from core.quant.garch import (Z_BOUND, GarchFit, bounded_t_stats, fit_garch, horizon_vol,
                              simulate_returns)
from core.quant.history import History, TRADING_DAYS

MODELS = ("garch_t", "gbm", "jump", "bootstrap")
DRIFTS = ("premium", "zero", "rf", "sample")
FAN_PERCENTILES = (5, 25, 50, 75, 95)


@dataclass(frozen=True)
class MCResult:
    symbol: str
    model: str
    n_paths: int
    horizon_days: int
    spot: float
    mu_annual: float                  # calibrated drift (log, annualized)
    sigma_annual: float               # calibrated volatility (annualized)
    # Percentile fan: dict percentile -> array of length horizon_days+1 (incl. spot)
    fan: dict[int, np.ndarray] = field(repr=False, default_factory=dict)
    sample_paths: np.ndarray = field(repr=False, default=None)  # small set for plotting
    terminal: np.ndarray = field(repr=False, default=None)      # all terminal prices
    # Terminal statistics
    mean_terminal: float = 0.0
    median_terminal: float = 0.0
    p05: float = 0.0
    p95: float = 0.0
    prob_loss: float = 0.0            # P(terminal < spot)
    prob_target: float | None = None  # P(terminal >= target), if target given
    target: float | None = None
    var_pct: float = 0.0              # horizon VaR at `var_level`, as +fraction of spot
    cvar_pct: float = 0.0             # horizon CVaR (expected shortfall beyond VaR)
    var_level: float = 0.95
    jump_note: str = ""
    garch: GarchFit | None = field(repr=False, default=None)
    drift_mode: str = "premium"
    garch_horizon_vol: float = 0.0    # annualised average vol over the horizon (GARCH only)
    rf_rate: float = 0.0              # risk-free rate the drift used (premium / rf modes)
    erp: float = 0.0                  # equity risk premium the drift used (premium mode)
    drift_note: str = ""              # the drift arithmetic in words, for the UI and narrative
    correction_annual: float = 0.0    # horizon-average convexity correction (annualised), rate modes
    z_bound: float | None = None      # |z| cap on the t innovations (GARCH-t only)
    bound_note: str = ""              # what the cap removes, in words (GARCH-t only, every drift mode)

    @property
    def expected_return_pct(self) -> float:
        return self.mean_terminal / self.spot - 1.0


def _calibrate(history: History) -> tuple[float, float, np.ndarray]:
    r = history.log_returns()
    if r.size < 20:
        raise ValueError("Need at least 21 sessions of history to calibrate.")
    mu = float(np.mean(r)) * TRADING_DAYS
    sigma = float(np.std(r, ddof=1)) * math.sqrt(TRADING_DAYS)
    return mu, sigma, r


def _simulate_gbm(rng, sigma, n_paths, horizon) -> np.ndarray:
    """Zero-mean lognormal shocks; the caller adds the drift."""
    dt = 1.0 / TRADING_DAYS
    return rng.normal(0.0, sigma * math.sqrt(dt), size=(n_paths, horizon))


def _simulate_jump(rng, r, sigma, n_paths, horizon) -> tuple[np.ndarray, str, float]:
    """Zero-mean Merton shocks: diffusion plus Poisson jumps, less the compound
    process mean. The caller adds the log drift. Also returns the exact daily
    convexity correction ln E[exp(shock)] for this construction."""
    # Split the sample at 3σ (daily) to separate diffusion from jumps.
    daily_sig = float(np.std(r, ddof=1))
    mask = np.abs(r - np.mean(r)) > 3.0 * daily_sig
    jumps = r[mask]
    diffusion = r[~mask]
    if jumps.size == 0:
        note = "No >3σ daily moves in the sample — jump model degrades to GBM."
        return _simulate_gbm(rng, sigma, n_paths, horizon), note, 0.5 * daily_sig ** 2
    lam = jumps.size / r.size                                   # jumps per day
    jump_mu = float(np.mean(jumps))
    jump_sig = float(np.std(jumps, ddof=1)) if jumps.size > 1 else abs(jump_mu) * 0.5
    d_sig = float(np.std(diffusion, ddof=1)) if diffusion.size > 1 else daily_sig
    d_mu = float(np.mean(diffusion))
    # Compensate the diffusion drift so total expected return matches the sample.
    shocks = rng.normal(d_mu, d_sig, size=(n_paths, horizon))
    n_jumps = rng.poisson(lam, size=(n_paths, horizon))
    jump_shocks = np.where(
        n_jumps > 0,
        rng.normal(jump_mu, jump_sig, size=(n_paths, horizon)) * n_jumps,
        0.0,
    )
    note = (f"Calibrated {jumps.size} jump days out of {r.size} "
            f"(λ={lam * TRADING_DAYS:.1f}/yr, mean jump {jump_mu:+.1%}).")
    total = shocks + jump_shocks - (d_mu + lam * jump_mu)   # the compound mean, not the sample mean
    # ln E[exp(total)] for this construction (one N(jump_mu, jump_sig^2) draw times
    # the Poisson count n): exp(d_sig^2/2 - lam*jump_mu) * sum_n P(n) exp(n*jump_mu + n^2*jump_sig^2/2).
    # The full series diverges (n^2 jump_sig^2/2 outgrows n ln n), so the partial
    # sum to n = 15 is the value for every count Monte Carlo will draw: P(n > 15)
    # is ~1e-35 at any daily intensity a 3-sigma split can produce.
    n = np.arange(0, 16)
    log_pn = -lam + n * math.log(lam) - gammaln(n + 1)
    corr = (0.5 * d_sig ** 2 - lam * jump_mu
            + float(np.log(np.sum(np.exp(log_pn + n * jump_mu + 0.5 * n * n * jump_sig ** 2)))))
    return total, note, corr


def _simulate_bootstrap(rng, r, n_paths, horizon, block: int = 5) -> np.ndarray:
    # Circular block bootstrap: sample fixed blocks of consecutive returns,
    # wrapping the sample, so short-run autocorrelation survives.
    n = r.size
    n_blocks = math.ceil(horizon / block)
    starts = rng.integers(0, n, size=(n_paths, n_blocks))
    offsets = np.arange(block)
    idx = (starts[:, :, None] + offsets[None, None, :]) % n     # (paths, blocks, block)
    return r[idx].reshape(n_paths, n_blocks * block)[:, :horizon]


def _bootstrap_correction(r, horizon, block: int = 5) -> np.ndarray:
    """Per-step convexity corrections for `_simulate_bootstrap`: with
    M_L = mean_i exp(sum of the L returns starting at i, wrapped) the block
    sums have E[exp] = M_L, so step p inside a block subtracts
    ln M_{p+1} - ln M_p. Exact for full and partial blocks alike."""
    n = r.size
    idx = (np.arange(n)[:, None] + np.arange(block)[None, :]) % n
    csum = np.cumsum(r[idx], axis=1)                           # (n, block) partial block sums
    log_m = np.concatenate([[0.0], np.log(np.mean(np.exp(csum), axis=0))])
    return np.diff(log_m)[np.arange(horizon) % block]


def resolve_drift(mode: str, *, sample_mu: float, rf_rate: float, erp: float) -> tuple[str, float]:
    """What a drift mode asks for: ("rate", annual arithmetic rate) for premium
    and rf — each model then subtracts its own exact per-step convexity
    correction — or ("log", annual log drift) for zero and sample, added as is.
    `sample_mu` is the sample mean of daily log returns × 252."""
    mode = (mode or "premium").lower()
    if mode not in DRIFTS:
        raise ValueError(f"Unknown drift {mode!r}. One of {DRIFTS}.")
    if mode == "premium":
        return "rate", float(rf_rate + erp)
    if mode == "rf":
        return "rate", float(rf_rate)
    if mode == "zero":
        return "log", 0.0
    return "log", float(sample_mu)


def _drift_note(mode: str, *, rf_rate: float, erp: float, sigma: float, mu: float,
                corr: float, how: str) -> str:
    """The drift arithmetic in words. `mu` is the effective annual log drift,
    `corr` the horizon-average convexity correction (annualised), `how` where
    the correction came from."""
    if mode == "premium":
        rate = rf_rate + erp
        note = (f"risk premium: rf {rf_rate:.2%} + ERP {erp:.2%} = expected (arithmetic) "
                f"return {rate:.2%}; log drift = that - convexity correction {corr:.2%} "
                f"({how}) = {mu:+.2%}")
        if mu < 0 < rate:
            note += (" - the median sits below spot only because the variance is large; "
                     "the mean path still earns the premium")
        return note
    if mode == "rf":
        return (f"risk-neutral: rf {rf_rate:.2%} - convexity correction {corr:.2%} ({how}) "
                f"= {mu:+.2%}; a pricing measure, not a forecast")
    if mode == "zero":
        return "zero: the cone centres on spot (stress view)"
    return (f"sample mean {mu:+.2%}: noisy, standard error about "
            f"{sigma / math.sqrt(2):.1%} on two years of data")


def run_monte_carlo(history: History, *, model: str = "garch_t", n_paths: int = 5000,
                    horizon_days: int = 126, target: float | None = None,
                    var_level: float = 0.95, seed: int = 7,
                    n_sample_paths: int = 40, drift: str = "premium",
                    rf_rate: float = 0.03, erp: float = 0.04) -> MCResult:
    model = (model or "garch_t").lower()
    if model not in MODELS:
        raise ValueError(f"Unknown model {model!r}. One of {MODELS}.")
    drift = (drift or "premium").lower()
    n_paths = int(max(200, min(n_paths, 100_000)))
    horizon_days = int(max(5, min(horizon_days, TRADING_DAYS * 5)))

    sample_mu, sigma, r = _calibrate(history)
    kind, value = resolve_drift(drift, sample_mu=sample_mu, rf_rate=rf_rate, erp=erp)
    rate_daily = value / TRADING_DAYS if kind == "rate" else None
    drift_daily = value / TRADING_DAYS if kind == "log" else None
    rng = np.random.default_rng(seed)
    jump_note = ""
    fit = None
    g_hvol = 0.0
    corr_daily = 0.0                                     # horizon-average c_t, daily
    z_bound = None
    bound_note = ""
    if model == "garch_t":
        fit = fit_garch(r, dist="t")
        shocks, corr_daily = simulate_returns(fit, n_paths=n_paths, horizon=horizon_days,
                                              seed=seed, drift_daily=drift_daily,
                                              rate_daily=rate_daily)
        sigma_report = fit.cond_vol_last
        mass, v_in = bounded_t_stats(fit.nu, Z_BOUND)
        g_hvol = horizon_vol(fit, horizon_days, var_in=v_in)      # the vol of the paths drawn
        if fit.innovation == "t":
            z_bound = Z_BOUND
            how = (f"per step from each path's conditional variance, horizon average; "
                   f"t innovations bounded at ±{Z_BOUND:g}")
            out_per_yr = (1.0 - mass) * TRADING_DAYS
            expect = (f"once per {1.0 / out_per_yr:,.0f} years" if out_per_yr > 1e-9
                      else "never in practice")
            ratio = g_hvol / horizon_vol(fit, horizon_days)   # bounded vs the fit's own forecast
            bound_note = (f"t innovations are capped at ±{Z_BOUND:g}: this fit expects a larger day "
                          f"{expect} (P {1.0 - mass ** horizon_days:.1%} within the horizon); the cap "
                          f"drops {1.0 - v_in:.2%} of innovation variance, so the fan's vol over this "
                          f"horizon runs {1.0 - ratio:.1%} below the fit's own forecast and VaR/CVaR "
                          f"exclude those days.")
        else:                                            # eta = 0 or nu > NU_NORMAL: drawn as normal
            how = "per step from each path's conditional variance, horizon average; normal innovations"
            bound_note = ("Innovations are effectively normal (the t fit found no heavier tail), so "
                          "they are drawn unbounded and no cap applies.")
    else:
        sig_daily = sigma / math.sqrt(TRADING_DAYS)
        if model == "gbm":
            shocks = _simulate_gbm(rng, sigma, n_paths, horizon_days)
            corr = 0.5 * sig_daily ** 2
            how = f"half the sample variance, sigma {sigma:.1%}"
        elif model == "jump":
            shocks, jump_note, corr = _simulate_jump(rng, r, sigma, n_paths, horizon_days)
            how = ("half the diffusion variance plus the jump compensator"
                   if "degrades" not in jump_note else f"half the sample variance, sigma {sigma:.1%}")
        else:
            r_dm = r - float(np.mean(r))
            shocks = _simulate_bootstrap(rng, r_dm, n_paths, horizon_days)
            corr = _bootstrap_correction(r_dm, horizon_days)         # one value per step
            how = "the empirical block log-MGF of the demeaned sample"
        if rate_daily is None:
            shocks = shocks + drift_daily                # zero-mean shocks + μ
        else:
            shocks = shocks + (rate_daily - corr)        # zero-mean shocks + rate − c_t
            corr_daily = float(np.mean(corr))
        sigma_report = sigma
    mu = value if kind == "log" else value - corr_daily * TRADING_DAYS   # effective log drift
    drift_note = _drift_note(drift, rf_rate=rf_rate, erp=erp, sigma=sigma, mu=mu,
                             corr=corr_daily * TRADING_DAYS, how=how if kind == "rate" else "")

    spot = history.last
    log_paths = np.cumsum(shocks, axis=1)
    paths = spot * np.exp(np.hstack([np.zeros((n_paths, 1)), log_paths]))

    fan = {p: np.percentile(paths, p, axis=0) for p in FAN_PERCENTILES}
    terminal = paths[:, -1].copy()
    sample = paths[:: max(1, n_paths // n_sample_paths)][:n_sample_paths].copy()

    losses = 1.0 - terminal / spot                       # +ve = loss fraction
    var = float(np.percentile(losses, var_level * 100))
    tail = losses[losses >= var]
    cvar = float(np.mean(tail)) if tail.size else var

    return MCResult(
        symbol=history.symbol, model=model, n_paths=n_paths,
        horizon_days=horizon_days, spot=spot,
        mu_annual=mu, sigma_annual=sigma_report,
        fan=fan, sample_paths=sample, terminal=terminal,
        mean_terminal=float(np.mean(terminal)),
        median_terminal=float(np.median(terminal)),
        p05=float(np.percentile(terminal, 5)),
        p95=float(np.percentile(terminal, 95)),
        prob_loss=float(np.mean(terminal < spot)),
        prob_target=(float(np.mean(terminal >= target)) if target else None),
        target=target,
        var_pct=max(0.0, var), cvar_pct=max(0.0, cvar), var_level=var_level,
        jump_note=jump_note, garch=fit, drift_mode=drift, garch_horizon_vol=g_hvol,
        rf_rate=rf_rate if drift in ("premium", "rf") else 0.0,
        erp=erp if drift == "premium" else 0.0, drift_note=drift_note,
        correction_annual=corr_daily * TRADING_DAYS, z_bound=z_bound, bound_note=bound_note,
    )
