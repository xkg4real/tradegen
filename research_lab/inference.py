"""Prespecified dependence-aware exploratory inference; no data loading or selection.

Candidate columns share each bootstrap draw. The primary reality check centers
every strategy-minus-benchmark series and compares the maximum sample mean with
its joint circular moving-block null distribution. P values include the observed
sample through the finite Monte Carlo +1 correction; they are never zero.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm


def _vector(value, name):
    array = np.asarray(value, dtype=float)
    if array.ndim != 1 or array.size < 31 or not np.isfinite(array).all():
        raise ValueError(f"{name} requires at least 31 finite observations")
    return array


def _bootstrap_counts(n, replications, block_length, rng):
    """Joint circular block draws as empirical frequencies, preserving dependence."""
    if (type(replications) is not int or replications < 99 or type(block_length) is not int
            or not 1 <= block_length < n):
        raise ValueError("invalid bootstrap settings")
    blocks = math.ceil(n / block_length)
    starts = rng.integers(0, n, size=(replications, blocks))
    indices = ((starts[:, :, None] + np.arange(block_length)) % n).reshape(replications, -1)[:, :n]
    counts = np.empty((replications, n), dtype=float)
    for row in range(replications):
        counts[row] = np.bincount(indices[row], minlength=n)
    return counts / n


def reality_check(matrix, benchmark, *, block_length=20, replications=1999, seed=20261031):
    """One-sided White-style max-mean test against one costed benchmark.

This deliberately centers all alternatives, including poor ones; that can be
conservative. It is not Hansen's SPA, an effective-trials approximation, or a
claim that historically inspected prices became an untouched confirmation set.
"""
    bench = _vector(benchmark, "benchmark")
    matrix = np.asarray(matrix, dtype=float)
    if (matrix.ndim != 2 or matrix.shape[0] != bench.size or matrix.shape[1] == 0
            or not np.isfinite(matrix).all()):
        raise ValueError("candidate matrix must be finite, aligned and nonempty")
    differences = matrix - bench[:, None]
    means = differences.mean(axis=0)
    n = bench.size
    statistic = max(0.0, math.sqrt(n) * float(means.max()))
    frequencies = _bootstrap_counts(n, replications, block_length, np.random.default_rng(seed))
    null = np.zeros(replications)
    # Bound temporary memory while retaining every declared candidate in the max.
    for first in range(0, matrix.shape[1], 256):
        centered = differences[:, first:first + 256] - means[first:first + 256]
        null = np.maximum(null, math.sqrt(n) * np.max(frequencies @ centered, axis=1))
    p = (1 + int(np.count_nonzero(null >= statistic))) / (replications + 1)
    return {"statistic": statistic, "p_value": p, "nobs": n, "n_candidates": matrix.shape[1],
            "block_length": block_length, "replications": replications,
            "critical_value_95": float(np.quantile(null, 0.95)),
            "method": "centered_circular_moving_block_max_mean", "benchmark": "costed_buy_and_hold"}


def evaluate_validation(matrix, benchmark, annualization, *, seed=20261031):
    if annualization not in (252, 365):
        raise ValueError("explicit equity/crypto annualization required")
    primary = reality_check(matrix, benchmark, block_length=20, replications=1999, seed=seed)
    sensitivity = {str(block): reality_check(matrix, benchmark, block_length=block,
                    replications=999, seed=seed + block) for block in (5, 60)}
    return {"nobs": primary["nobs"], "n_candidates": primary["n_candidates"],
            "primary": primary, "sensitivity": sensitivity}


def holm_adjust(p_values):
    """Strong familywise adjustment without independence assumptions."""
    values = np.asarray(p_values, dtype=float)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("finite probabilities in [0,1] required")
    order = np.argsort(values, kind="stable")
    result = np.empty_like(values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(values) - rank) * values[index])
        result[index] = min(1.0, running)
    return result.tolist()


def _sharpe(array, annualization):
    deviation = float(np.std(array, ddof=1))
    return float(np.mean(array) / deviation * math.sqrt(annualization)) if deviation > 0 else None


def _interval(samples):
    samples = np.asarray(samples, dtype=float)
    good = samples[np.isfinite(samples)]
    if good.size < 0.9 * samples.size:
        return None
    return [float(value) for value in np.quantile(good, (0.025, 0.975))]


def _hac_market_model(strategy, benchmark, lags=20):
    """OLS market-model intercept with Bartlett Newey-West covariance (diagnostic)."""
    n = len(strategy)
    x = np.column_stack((np.ones(n), benchmark))
    if np.linalg.matrix_rank(x) != 2:
        return {"available": False, "reason": "benchmark_has_no_variation"}
    inverse = np.linalg.inv(x.T @ x)
    coefficients = inverse @ x.T @ strategy
    residual = strategy - x @ coefficients
    moments = x * residual[:, None]
    meat = moments.T @ moments
    for lag in range(1, min(lags, n - 1) + 1):
        covariance = moments[lag:].T @ moments[:-lag]
        meat += (1.0 - lag / (lags + 1)) * (covariance + covariance.T)
    covariance = inverse @ meat @ inverse * (n / (n - 2))
    se = math.sqrt(max(0.0, float(covariance[0, 0])))
    if se <= np.finfo(float).eps:
        return {"available": False, "reason": "degenerate_residual_variance",
                "alpha_daily": float(coefficients[0]), "beta": float(coefficients[1])}
    z = float(coefficients[0]) / se
    log_p = float(norm.logsf(z))
    bounded = log_p < math.log(1e-300)
    return {"available": True, "alpha_daily": float(coefficients[0]), "beta": float(coefficients[1]),
            "alpha_se_hac": se, "alpha_p_one_sided": 1e-300 if bounded else math.exp(log_p),
            "p_value_is_upper_bound": bounded, "hac_lags": lags, "small_sample_factor": n / (n - 2),
            "interpretation": "diagnostic market-model intercept, not causal or independent confirmation"}


def holdout_diagnostics(strategy_returns, benchmark_returns, annualization, *, seed=20261031,
                        block_length=20, replications=1999):
    """Paired retrospective holdout summaries for an already frozen candidate."""
    strategy = _vector(strategy_returns, "strategy")
    benchmark = _vector(benchmark_returns, "benchmark")
    if strategy.shape != benchmark.shape or (strategy <= -1).any() or (benchmark <= -1).any():
        raise ValueError("aligned non-ruined return paths required")
    if annualization not in (252, 365):
        raise ValueError("explicit equity/crypto annualization required")
    n = len(strategy)
    frequencies = _bootstrap_counts(n, replications, block_length, np.random.default_rng(seed))
    mean = float(strategy.mean())
    mean_diff = float((strategy - benchmark).mean())
    bootstrap_means = frequencies @ strategy
    bootstrap_bench = frequencies @ benchmark
    bootstrap_diff = bootstrap_means - bootstrap_bench
    variance = np.maximum(0, (frequencies @ (strategy ** 2) - bootstrap_means ** 2) * n / (n - 1))
    bench_variance = np.maximum(0, (frequencies @ (benchmark ** 2) - bootstrap_bench ** 2) * n / (n - 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        sharpe_diff = math.sqrt(annualization) * (bootstrap_means / np.sqrt(variance) - bootstrap_bench / np.sqrt(bench_variance))
    equity = np.r_[1.0, np.cumprod(1 + strategy)]
    return {"nobs": n, "mean": mean, "annualized_mean": mean * annualization,
            "cagr": float(equity[-1] ** (annualization / n) - 1),
            "sharpe": _sharpe(strategy, annualization), "benchmark_sharpe": _sharpe(benchmark, annualization),
            "max_drawdown": float(np.min(equity / np.maximum.accumulate(equity) - 1)),
            "mean_diff": mean_diff, "mean_ci": _interval(bootstrap_means),
            "mean_diff_ci": _interval(bootstrap_diff), "sharpe_diff_ci": _interval(sharpe_diff),
            "mean_p_value": (1 + int(np.count_nonzero(bootstrap_means - mean >= mean))) / (replications + 1),
            "mean_diff_p_value": (1 + int(np.count_nonzero(bootstrap_diff - mean_diff >= mean_diff))) / (replications + 1),
            "block_length": block_length, "replications": replications,
            "market_model": _hac_market_model(strategy, benchmark),
            "interpretation": "retrospective internal holdout; previous research contamination remains"}
