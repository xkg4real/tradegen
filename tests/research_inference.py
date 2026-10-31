"""Synthetic inferential checks; no historical prices, selection or live inputs."""
from __future__ import annotations

import math

import numpy as np

from research_lab.inference import holdout_diagnostics, holm_adjust, reality_check


def _refused(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError("malformed inference input accepted")


def test_exact_benchmark_and_uniform_underperformance_never_claim_superiority():
    benchmark = np.tile([0.01, -0.009, 0.003, -0.002], 100)
    for matrix in (benchmark[:, None], np.column_stack((benchmark - 0.001, benchmark - 0.002))):
        result = reality_check(matrix, benchmark, replications=199, seed=47)
        assert result["statistic"] == 0 and result["p_value"] == 1


def test_joint_draws_preserve_identical_candidate_dependence_and_nonzero_monte_carlo_floor():
    rng = np.random.default_rng(51)
    benchmark = rng.normal(0, 0.01, 600)
    candidate = benchmark + 0.003 + rng.normal(0, 0.002, 600)
    one = reality_check(candidate[:, None], benchmark, replications=199, seed=97)
    many = reality_check(np.tile(candidate[:, None], (1, 40)), benchmark, replications=199, seed=97)
    assert one["p_value"] == many["p_value"] == 1 / 200
    assert math.isclose(one["statistic"], many["statistic"], rel_tol=1e-12)
    assert many["n_candidates"] == 40


def test_block_resampling_exposes_persistent_return_uncertainty():
    # Long runs have few independent observations despite a large daily row count.
    persistent = np.tile(np.r_[np.full(50, 0.008), np.full(50, -0.006)], 6)
    benchmark = np.tile([0.003, -0.003], 300)
    daily = holdout_diagnostics(persistent, benchmark, 252, block_length=1, replications=399, seed=71)
    blocks = holdout_diagnostics(persistent, benchmark, 252, block_length=20, replications=399, seed=71)
    daily_width = daily["mean_ci"][1] - daily["mean_ci"][0]
    block_width = blocks["mean_ci"][1] - blocks["mean_ci"][0]
    assert block_width > 2 * daily_width


def test_paired_holdout_identical_series_and_annualization_are_coherent():
    returns = np.tile([0.006, -0.004, 0.001, -0.001], 100)
    stocks = holdout_diagnostics(returns, returns, 252, replications=199, seed=16)
    crypto = holdout_diagnostics(returns, returns, 365, replications=199, seed=16)
    assert stocks["mean_diff"] == 0 and stocks["mean_diff_p_value"] == 1
    assert stocks["mean_diff_ci"] == [0, 0] and stocks["sharpe_diff_ci"] == [0, 0]
    assert math.isclose(crypto["sharpe"] / stocks["sharpe"], math.sqrt(365 / 252), rel_tol=1e-12)
    assert stocks["max_drawdown"] < 0


def test_hac_market_model_recovers_planted_beta_without_treating_zero_benchmark_as_identified():
    rng = np.random.default_rng(808)
    benchmark = rng.normal(0.0002, 0.015, 1200)
    strategy = 0.001 + 0.4 * benchmark + rng.normal(0, 0.001, 1200)
    result = holdout_diagnostics(strategy, benchmark, 252, replications=199, seed=22)
    market = result["market_model"]
    assert market["available"] and abs(market["beta"] - 0.4) < 0.02
    assert abs(market["alpha_daily"] - 0.001) < 0.0001
    assert 0 < market["alpha_p_one_sided"] < 0.01
    absent = holdout_diagnostics(strategy, np.zeros_like(strategy), 252, replications=199, seed=22)
    assert not absent["market_model"]["available"]


def test_holm_preserves_order_and_controls_all_declared_hypotheses():
    assert np.allclose(holm_adjust([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
    assert holm_adjust([0.2, 0.2, 1.0]) == [0.6000000000000001, 0.6000000000000001, 1.0]
    # Missing/insufficient assets count as p=1, not a smaller opportunistic family.
    assert holm_adjust([0.01] + [1.0] * 7)[0] == 0.08


def test_inference_rejects_misaligned_nonfinite_short_or_ruined_inputs():
    good = np.full(100, 0.001)
    for value in (good[:30], np.r_[good[:-1], np.nan], np.ones((10, 10))):
        _refused(lambda value=value: holdout_diagnostics(value, good, 252))
    _refused(lambda: reality_check(np.ones((99, 3)), good))
    _refused(lambda: reality_check(np.ones((100, 0)), good))
    _refused(lambda: reality_check(good[:, None], good, block_length=100))
    _refused(lambda: holdout_diagnostics(np.r_[-1, good[:-1]], good, 252))
    _refused(lambda: holdout_diagnostics(good, good, 360))
    for values in ([], [np.nan], [-0.1], [1.1]):
        _refused(lambda values=values: holm_adjust(values))
