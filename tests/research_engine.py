"""Synthetic identities and causal counterexamples; never market-data evaluation."""
from dataclasses import replace
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np

from research_lab.backtest import buy_hold, select_validation, simulate_window
from research_lab.candidates import Candidate, annual_volatility, catalogue, raw_rules, signal_matrix


def _candidate(**kwargs):
    fields = dict(candidate_id="synthetic", raw_index=0, family="synthetic", parameters=(),
                  rebalance_bars=1, target_cap=1.0, volatility_target=None)
    return Candidate(**(fields | kwargs))


def _simulate(price, signals=None, candidate=None, *, cost=0.0, lag=1, indices=None):
    p = np.array(price, dtype=float)
    signals = np.ones((len(p), 1), dtype=bool) if signals is None else np.asarray(signals, dtype=bool)[:, None]
    return simulate_window(p, signals, np.zeros(len(p)), (candidate or _candidate(),),
                           np.arange(2, len(p)) if indices is None else np.asarray(indices),
                           annualization=365, cost_per_side=cost, lag=lag, capture=True)


def test_finite_catalogue_has_exact_economic_families_and_unique_parameter_variants():
    raw = raw_rules()
    assert len(raw) == 223 and len({r.family for r in raw}) == 8
    candidates = catalogue()
    assert len(candidates) == 2676 and len({c.candidate_id for c in candidates}) == 2676
    assert all(c.target_cap <= 1 and c.rebalance_bars in (1, 5, 21) for c in candidates)
    assert catalogue() == candidates


def test_all_signals_ignore_every_future_price_change():
    rng = np.random.default_rng(283)
    p = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, 700)))
    changed = p.copy()
    changed[551:] *= np.exp(np.linspace(-2, 3, len(changed) - 551))
    a, b = signal_matrix(p), signal_matrix(changed)
    assert a.shape == (700, 223)
    assert np.array_equal(a[:551], b[:551])
    assert np.array_equal(annual_volatility(p, 365)[:551], annual_volatility(changed, 365)[:551], equal_nan=True)


def test_next_close_fill_cannot_earn_the_move_that_precedes_execution():
    result = _simulate([100, 100, 200, 200, 100, 100], [False, True, True, False, False, False],
                       indices=np.arange(1, 6))
    assert np.allclose(result.returns[:, 0], [0, 0, 0, -0.5, 0])
    assert result.trace["position"][0, 0] == 0
    assert result.trace["position"][1, 0] == 1
    assert result.metrics[0]["completed_trades"] == 1


def test_entry_and_terminal_liquidation_costs_match_exact_cash_identity():
    c = 0.01
    result = _simulate([100] * 8, cost=c)
    assert np.isclose(result.metrics[0]["total_return"] + 1, (1 - c) / (1 + c), rtol=0, atol=2e-14)
    assert np.isclose(result.returns[0, 0], -c / (1 + c))
    assert np.isclose(result.returns[-1, 0], -c)
    assert result.metrics[0]["completed_trades"] == result.metrics[0]["entries"] == 1
    assert result.trace["position"][-1, 0] == 0


def test_rebalance_target_solves_post_fee_weight_and_charges_drift_turnover():
    result = _simulate([100, 100, 100, 200, 200, 200], candidate=_candidate(target_cap=0.5), cost=0.01)
    assert np.allclose(result.trace["position"][:-1, 0], 0.5)
    assert result.trace["turnover"][1, 0] > 0.15
    assert result.trace["cost"][1, 0] > 0
    assert np.all(result.trace["position"] <= 1)


def test_between_scheduled_rebalances_shares_stay_fixed_and_weights_drift():
    result = _simulate([100, 100, 100, 200, 200, 200], candidate=_candidate(target_cap=0.5, rebalance_bars=21))
    assert result.trace["turnover"][1, 0] == 0
    assert np.isclose(result.trace["position"][1, 0], 2 / 3)
    assert result.metrics[0]["total_return"] == 0.5


def test_each_phase_starts_cash_and_terminal_close_never_opens_an_unearned_trade():
    p = [1, 1, 100, 100, 100, 100, 100]
    result = _simulate(p, cost=0, indices=np.arange(2, 7))
    assert np.array_equal(result.returns[:, 0], np.zeros(5))
    sig = [False] * 7
    sig[5] = True
    last_only = _simulate(p, sig, cost=0.01, indices=np.arange(2, 7))
    assert last_only.metrics[0]["entries"] == 0
    assert last_only.metrics[0]["total_return"] == 0


def test_constant_cash_and_costed_buy_hold_are_explicit_benchmarks():
    p = np.array([100, 100, 100, 110, 121, 121], dtype=float)
    result = _simulate(p, [False] * len(p), cost=0.01)
    assert result.metrics[0]["total_return"] == 0 and result.metrics[0]["sharpe"] is None
    bh = buy_hold(p, np.arange(2, 6), annualization=365, cost_per_side=0.01)
    assert np.isclose(1 + bh.metrics[0]["total_return"], 1.21 * 0.99 / 1.01)


def test_volatility_target_cannot_borrow_or_multiply_the_target_cap_twice():
    p = np.array([100] * 8, dtype=float)
    result = simulate_window(p, np.ones((8, 1), dtype=bool), np.full(8, 0.5),
                             (_candidate(target_cap=0.5, volatility_target=0.15),), np.arange(2, 8),
                             annualization=365, cost_per_side=0, capture=True)
    assert np.allclose(result.trace["position"][:-1, 0], 0.3)
    result = simulate_window(p, np.ones((8, 1), dtype=bool), np.full(8, 0.01),
                             (_candidate(target_cap=0.5, volatility_target=0.15),), np.arange(2, 8),
                             annualization=365, cost_per_side=0, capture=True)
    assert np.allclose(result.trace["position"][:-1, 0], 0.5)
    result = simulate_window(p, np.ones((8, 1), dtype=bool), np.zeros(8),
                             (_candidate(target_cap=0.5, volatility_target=0.15),), np.arange(2, 8),
                             annualization=365, cost_per_side=0, capture=True)
    assert not result.trace["position"].any()


def test_extra_execution_lag_delays_position_without_using_new_information():
    sig = [False, True, False, False, False, False, False]
    base = _simulate([100] * 7, sig, lag=1)
    delayed = _simulate([100] * 7, sig, lag=2)
    assert base.trace["position"][0, 0] == 1
    assert delayed.trace["position"][0, 0] == 0
    assert delayed.trace["position"][1, 0] == 1


def test_validation_choice_uses_only_predeclared_eligibility_and_ties():
    candidates = (_candidate(candidate_id="a"), _candidate(candidate_id="b"), _candidate(candidate_id="c"))
    metrics = [dict(mean_daily=0.001, completed_trades=25, sharpe=1.0, turnover=10),
               dict(mean_daily=0.001, completed_trades=25, sharpe=1.0 + 5e-13, turnover=9),
               dict(mean_daily=0.01, completed_trades=19, sharpe=20.0, turnover=2)]
    assert select_validation(candidates, metrics) == 1
    assert select_validation(candidates, [m | {"mean_daily": -1} for m in metrics]) is None


def test_invalid_arrays_noncontiguous_windows_and_costs_refuse():
    for change in (dict(cost_per_side=-0.1), dict(cost_per_side=0.1), dict(lag=0),
                   dict(indices=[2, 4, 5]), dict(close=[1, 1, 0, 1, 1, 1])):
        args = dict(close=np.ones(6), raw_signals=np.ones((6, 1), dtype=bool), annual_vol=np.zeros(6),
                    candidates=(_candidate(),), indices=np.arange(2, 6), annualization=365, cost_per_side=0.001)
        try:
            simulate_window(**(args | change))
        except ValueError:
            continue
        raise AssertionError("invalid research arithmetic accepted")


def test_changed_frozen_source_refuses_before_any_market_data_load_or_output():
    from research_lab import run
    blobs = {relative: (run.ROOT / relative).read_bytes() for relative in run.FROZEN_FILES}
    with tempfile.TemporaryDirectory(prefix="research-freeze-test-") as folder:
        root = Path(folder)
        for relative, raw in blobs.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        changed = root / "research_lab/backtest.py"
        changed.write_bytes(changed.read_bytes() + b"\n# changed after preregistration\n")
        output = root / "docs/research/result"

        def committed(command, *, cwd):
            assert command[:2] == ["git", "show"] and cwd == root
            return blobs[command[2].split(":", 1)[1]]

        with patch.object(run.subprocess, "check_output", committed), \
                patch.object(run.data, "load_assets", side_effect=AssertionError("market data must not be loaded")):
            try:
                run.run_study(freeze_commit="a" * 40, output=output, root=root)
            except ValueError as exc:
                assert "changed after computation preregistration" in str(exc)
            else:
                raise AssertionError("changed source was evaluated")
        assert not output.exists()


def test_fixed_phase_windows_are_disjoint_and_respect_warmup_without_retuning():
    from research_lab.run import phase_indices
    dates = ("2019-12-29", "2019-12-30", "2019-12-31", "2020-12-31", "2021-01-01",
             "2022-12-31", "2023-01-01", "2026-09-24", "2026-09-25")
    protocol = dict(warmup_bars=2, splits={
        "train": dict(start=None, end="2020-12-31"),
        "validation": dict(start="2021-01-01", end="2022-12-31"),
        "holdout": dict(start="2023-01-01", end="2026-09-24")})
    windows = phase_indices(dates, protocol)
    assert np.array_equal(windows["train"], [2, 3])
    assert np.array_equal(windows["validation"], [4, 5])
    assert np.array_equal(windows["holdout"], [6, 7])
    assert len(set(np.concatenate(list(windows.values())))) == 6
