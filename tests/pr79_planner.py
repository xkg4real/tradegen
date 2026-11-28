"""Offline regressions for the selection/prepare split and the shared comparison registry."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import patch

from core import odds_registry
from core.odds import models, plan
from core.oddsdata import inputs as cli_inputs
from execution_accounts.universe import UniverseBars
from tools.owner import planner


NOW = datetime(2030, 1, 5, 4, tzinfo=timezone.utc)


def _file(symbol="BTC", sizing="floor_safe"):
    return {"schema": "tradegen.odds_plan/1", "plans": [{
        "name": "synthetic", "track": "compounding", "stake_krw": 120, "target_krw": 150,
        "fx_krw_per_usd": 1000, "start": "2026-01-01", "horizon_days": 3,
        "leg": {"venue": "upbit", "symbol": symbol, "model": "bootstrap", "bracket": None,
                "sizing": sizing, "edge_source": "none", "assumed_p": None},
        "fraction": {"kind": "fixed", "value": 0.1},
    }]}


def _refuses(call, code):
    try:
        call()
    except planner.PlannerError as exc:
        assert exc.args == (code,), (exc.args, code)
    else:
        raise AssertionError(code)


@contextmanager
def scenario():
    market = "KRW-BTC"
    item = UniverseBars(market=market, bars=tuple(
        ((NOW.date() - timedelta(days=250 - i)).isoformat(), 10.0 + i, 11.0 + i)
        for i in range(250)), receipt_sha256=("a" * 64,))
    state = SimpleNamespace(now=NOW, bars=item, cap=Decimal(100), market=market, limit=NOW + timedelta(hours=22),
                            universe=False)
    def scope(_):
        return state.market, state.cap, state.limit, state.universe
    def evaluate(selected, _ctx, inputs):
        seed = models.market_seed(models.data_hashes(inputs.series, None), "", inputs.comparison_id, inputs.run_counter)
        return SimpleNamespace(flags=(), refused=None, plan_hash=plan.plan_hash(selected), provenance={"seed_hex": seed.hex()})
    current = planner.CurrentPlanner(template=planner.parse_plan_template(json.dumps(_file()).encode()),
        clock=lambda: state.now, symbol_provider=lambda: market, observation_provider=lambda: SimpleNamespace(
        asof=state.now, positions=None), bars_reader=lambda markets, **kw: {state.market:state.bars})
    with ExitStack() as callbacks:
        ctx = SimpleNamespace(owner=SimpleNamespace(ok=True), code_signed=True, active=SimpleNamespace(valid=True),
                              code_hash="c" * 64)
        callbacks.enter_context(patch.object(planner.owner, "load_context", return_value=ctx))
        callbacks.enter_context(patch.object(planner.model, "is_sealed", return_value=True))
        callbacks.enter_context(patch.object(planner.simulate, "simulate", side_effect=evaluate))
        callbacks.enter_context(patch.object(planner.odds_report, "render", return_value="fixture card"))
        yield current, state, scope


def test_shared_cli_registry_preserves_comparison_counts_and_concurrent_issues():
    with scenario() as (p, state, scope):
        first = p.select(scope)
        result = cli_inputs.begin_run(None, [first.plan_hash], [])
        with ThreadPoolExecutor(max_workers=4) as pool:
            rows = list(pool.map(lambda _: odds_registry.begin_run(None, [first.plan_hash], []), range(4)))
        again = p.select(scope)
        assert len({r[0] for r in rows}) == 4
        assert result[4][first.plan_hash] == first.value.inputs.plan_runs + 1
        assert again.value.inputs.plan_runs == first.value.inputs.plan_runs + 6
        assert again.value.selection_seed_hex != first.value.selection_seed_hex


def test_rehearsal_selection_caps_stake_reuses_run_and_refreshes_under_lock_time():
    with scenario() as (p, state, scope):
        selection = p.select(scope)
        assert selection.passed and selection.value.selected_plan.stake_krw == 100
        before = odds_registry.state_path().read_bytes()
        state.now += timedelta(seconds=1)
        build = p.prepare_builder(selection, scope)
        checked = state.now + timedelta(seconds=2)
        inputs = build(checked)
        assert inputs.inputs.now == checked and inputs.inputs.comparison_id == selection.value.inputs.comparison_id
        assert inputs.selection_seed_hex == selection.value.selection_seed_hex
        assert inputs.expires_at.astimezone(planner.model.KST).strftime("%H:%M:%S") == "23:59:00"
        assert odds_registry.state_path().read_bytes() == before
        state.cap -= 1
        _refuses(lambda: build(checked), "PLANNER_STAKE_CHANGED")


def test_changed_candle_or_receipt_cannot_replace_odds_observation():
    with scenario() as (p, state, scope):
        selection = p.select(scope)
        original = state.bars
        state.bars = replace(original, receipt_sha256=("b" * 64,))
        _refuses(lambda: p.prepare_builder(selection, scope), "PLANNER_BARS_CHANGED")
        day, opening, closing = original.bars[-1]
        state.bars = replace(original, bars=(*original.bars[:-1], (day, opening, closing + 1)))
        _refuses(lambda: p.prepare_builder(selection, scope), "PLANNER_BARS_CHANGED")
        state.bars = replace(original, receipt_sha256=())
        _refuses(lambda: p.select(scope), "PLANNER_BAR_RECEIPTS_REQUIRED")


def test_nonfinal_or_short_history_and_mismatched_fixed_symbol_refused():
    with scenario() as (p, state, scope):
        original = state.bars
        state.bars = replace(original, bars=original.bars[1:])
        _refuses(lambda: p.select(scope), "PLANNER_BARS_INSUFFICIENT")
        state.bars = replace(original, bars=(*original.bars[:-1], (NOW.date().isoformat(), 2.0, 3.0)))
        _refuses(lambda: p.select(scope), "PLANNER_BAR_SERIES_INVALID")
        state.market = "KRW-ETH"
        _refuses(lambda: p.select(scope), "PLANNER_FIXED_SYMBOL_MISMATCH")
        _refuses(lambda: p.prepare_builder(None, scope), "PLANNER_ODDS_SELECTION_REQUIRED")


def test_canonical_plan_requires_one_floor_safe_nonreplay_upbit_leg():
    _refuses(lambda: planner.parse_plan_template(json.dumps(_file("BTC", "stop_based")).encode()),
             "PLANNER_TEMPLATE_INVALID")
    f = _file()
    f["plans"] *= 2
    _refuses(lambda: planner.parse_plan_template(json.dumps(f).encode()), "PLANNER_TEMPLATE_SCHEMA_INVALID")


def test_universe_selects_snapshot_market_and_caps_stake_to_settled_cash():
    with scenario() as (p, state, scope):
        state.market, state.universe, state.cap = "KRW-ETH", True, Decimal(46)
        state.bars = replace(state.bars, market=state.market)
        selection = p.select(scope)
        assert selection.market == state.market and selection.value.selected_plan.leg.symbol == "ETH"
        assert selection.value.selected_plan.stake_krw == 46
        build = p.prepare_builder(selection, scope)
        state.market = "KRW-ADA"
        _refuses(lambda: build(state.now), "PLANNER_SELECTION_CHANGED")
