"""D14-clean current odds planner for owner-prepared sessions; no legacy research imports.

Consumes only current Upbit daily bars from execution_accounts.universe, sealed
owner compliance context from core.compliance, and pure Monte Carlo simulation
from core.odds. Never signs, activates or caches an execution session.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
import json
import math
import re
from typing import Callable

from core.compliance import model, owner
from core.odds import models, plan as odds_plan, report as odds_report, simulate
from core.odds_plan_file import load_plans
from core.odds_registry import begin_run
from execution_accounts.universe import daily_bars
from execution_control.universe_odds import _series as _bars_to_series
from tools.owner.launch import OwnerOperationError, PreparationInputs

MAX_PLAN_BYTES = 16384
_MARKET = re.compile(r"KRW-[A-Z0-9]{1,20}")
_MONEY = re.compile(r"(?:0|[1-9][0-9]{0,18})(?:\.[0-9]{1,12})?")
_PLAN_KEYS = frozenset({
    "schema_version", "kind", "name", "track", "stake_krw", "target_krw",
    "fx_krw_per_usd", "horizon_days", "model", "fraction_kind", "fraction_value",
    "edge_source", "assumed_p", "bracket", "sizing",
})


class PlannerError(OwnerOperationError):
    """Fixed diagnostic codes only; never echoes market/account payloads."""


def _need(condition: bool, code: str) -> None:
    if not condition:
        raise PlannerError(code)


def _aware(value: object) -> bool:
    return type(value) is datetime and value.utcoffset() is not None


def _num(value: object, *, allow_none: bool = False, positive: bool = True) -> float | None:
    if value is None and allow_none:
        return None
    _need(type(value) is str and _MONEY.fullmatch(value) is not None, "PLANNER_TEMPLATE_AMOUNT_INVALID")
    dec = Decimal(value)
    _need(dec > 0 if positive else dec >= 0, "PLANNER_TEMPLATE_AMOUNT_INVALID")
    value = float(dec)
    _need(math.isfinite(value) and Decimal(str(value)) == dec, "PLANNER_TEMPLATE_AMOUNT_INVALID")
    return value


def parse_plan_template(raw: bytes, *, default_symbol: str = "BTC") -> odds_plan.Plan:
    """Parse a strict JSON odds template without floats or extra keys."""
    _need(type(raw) is bytes and 0 < len(raw) <= MAX_PLAN_BYTES, "PLANNER_TEMPLATE_SIZE_INVALID")

    def _pairs(rows):
        out = {}
        for k, v in rows:
            _need(k not in out, "PLANNER_JSON_DUPLICATE_KEY")
            out[k] = v
        return out

    def _bad(_):
        raise PlannerError("PLANNER_JSON_NUMBER_INVALID")

    def exact_decimal(token):
        amount = Decimal(token)
        parsed = float(amount)
        _need(math.isfinite(parsed) and Decimal(str(parsed)) == amount, "PLANNER_TEMPLATE_AMOUNT_INVALID")
        return amount

    try:
        body = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_float=exact_decimal,
                          parse_constant=_bad)
    except PlannerError:
        raise
    except Exception:
        raise PlannerError("PLANNER_JSON_INVALID") from None

    if type(body) is dict and body.get("schema") == "tradegen.odds_plan/1":
        standard = load_plans(raw)
        _need(len(standard) == 1 and type(standard[0]) is odds_plan.Plan, "PLANNER_TEMPLATE_SCHEMA_INVALID")
        plan = standard[0]
        _need(type(plan.leg) is odds_plan.Leg and plan.leg.venue == "upbit"
              and plan.leg.sizing == "floor_safe" and plan.leg.edge_source != odds_plan.REPLAY_SOURCE,
              "PLANNER_TEMPLATE_INVALID")
        original = body["plans"][0]
        _need(type(plan.start) is date and all(math.isfinite(val) and val > 0 and Decimal(str(val)) == original[key]
              for key, val in (("stake_krw", plan.stake_krw), ("target_krw", plan.target_krw),
                               ("fx_krw_per_usd", plan.fx_krw_per_usd))), "PLANNER_TEMPLATE_AMOUNT_INVALID")
        return plan

    _need(type(body) is dict and set(body) == _PLAN_KEYS, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(type(body["schema_version"]) is int and body["schema_version"] == 1
          and body["kind"] == "tradegen-live-odds-template/1", "PLANNER_TEMPLATE_KIND_INVALID")
    _need(type(body["name"]) is str and 0 < len(body["name"]) <= 128, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["track"] in odds_plan.TRACKS, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(type(body["horizon_days"]) is int and 1 <= body["horizon_days"] <= odds_plan.MAX_HORIZON_DAYS,
          "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["model"] in odds_plan.MODELS, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["edge_source"] in ("none", "assumed"), "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["sizing"] == "floor_safe", "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["fraction_kind"] in odds_plan.FRACTION_KINDS, "PLANNER_TEMPLATE_SCHEMA_INVALID")

    f_kind = body["fraction_kind"]
    f_val = _num(body["fraction_value"], allow_none=(f_kind == "bold"), positive=True)
    if f_kind == "bold":
        _need(f_val is None, "PLANNER_TEMPLATE_SCHEMA_INVALID")
        frac = odds_plan.bold()
    else:
        _need(f_val is not None and 0.0 < f_val <= 1.0, "PLANNER_TEMPLATE_AMOUNT_INVALID")
        frac = odds_plan.Fraction(kind=f_kind, value=f_val)

    assumed_p = _num(body["assumed_p"], allow_none=(body["edge_source"] != "assumed"), positive=True)
    if body["edge_source"] == "assumed":
        _need(assumed_p is not None and 0.0 < assumed_p < 1.0, "PLANNER_TEMPLATE_AMOUNT_INVALID")
    else:
        _need(assumed_p is None, "PLANNER_TEMPLATE_SCHEMA_INVALID")

    bracket_raw = body["bracket"]
    bracket = None
    if bracket_raw is not None:
        _need(type(bracket_raw) is dict and set(bracket_raw) == {"take_profit", "stop"},
              "PLANNER_TEMPLATE_SCHEMA_INVALID")
        tp = _num(bracket_raw["take_profit"], positive=True)
        st = _num(bracket_raw["stop"], positive=True)
        _need(tp is not None and st is not None and 0.0 < st < 1.0 and tp <= 1000.0,
              "PLANNER_TEMPLATE_AMOUNT_INVALID")
        bracket = odds_plan.Bracket(take_profit=tp, stop=st)

    stake = _num(body["stake_krw"], positive=True)
    target = _num(body["target_krw"], positive=True)
    fx = _num(body["fx_krw_per_usd"], positive=True)
    return odds_plan.Plan(
        name=body["name"],
        track=body["track"],
        stake_krw=stake,
        target_krw=target,
        fx_krw_per_usd=fx,
        start=date(2026, 1, 1),
        horizon_days=body["horizon_days"],
        leg=odds_plan.Leg(
            venue="upbit",
            symbol=default_symbol,
            model=body["model"],
            bracket=bracket,
            sizing=body["sizing"],
            edge_source=body["edge_source"],
            assumed_p=assumed_p,
        ),
        fraction=frac,
    )


@dataclass(frozen=True, kw_only=True)
class Selection:
    value: PreparationInputs
    market: str
    universe: bool
    bar_receipts: tuple[str, ...]
    rendered_card: str
    plan_hash: str
    passed: bool


@dataclass(frozen=True, kw_only=True)
class CurrentPlanner:
    """Keep the odds run separate from its subsequent two-phase preparation."""
    template: odds_plan.Plan
    symbol_provider: Callable[[], str]
    observation_provider: Callable[[], object]
    clock: Callable[[], datetime]
    bars_reader: Callable[..., Mapping] = daily_bars
    session_ttl: timedelta | None = None

    def __post_init__(self):
        leg = getattr(self.template, "leg", None)
        _need(type(self.template) is odds_plan.Plan and type(leg) is odds_plan.Leg and leg.venue == "upbit"
              and leg.sizing == "floor_safe" and leg.edge_source != odds_plan.REPLAY_SOURCE,
              "PLANNER_TEMPLATE_INVALID")
        _need(all(callable(x) for x in (self.symbol_provider, self.observation_provider, self.clock, self.bars_reader)),
              "PLANNER_DEPENDENCIES_REQUIRED")
        if self.session_ttl is not None:
            _need(type(self.session_ttl) is timedelta and timedelta(0) < self.session_ttl <= timedelta(hours=24),
                  "PLANNER_TTL_INVALID")

    def __call__(self):
        raise PlannerError("PLANNER_ODDS_SELECTION_REQUIRED")

    def _bars(self, market, at):
        _need(_aware(at), "PLANNER_CLOCK_INVALID")
        results = self.bars_reader((market,), now=at, clock=self.clock)
        _need(isinstance(results, Mapping) and set(results) == {market}, "PLANNER_BARS_UNAVAILABLE")
        item = results[market]
        receipts = getattr(item, "receipt_sha256", None)
        _need(getattr(item, "market", None) == market and type(receipts) is tuple and receipts
              and all(type(v) is str and re.fullmatch(r"[0-9a-f]{64}", v) for v in receipts),
              "PLANNER_BAR_RECEIPTS_REQUIRED")
        _need(type(getattr(item, "bars", None)) is tuple and len(item.bars) >= odds_plan.MIN_BARS,
              "PLANNER_BARS_INSUFFICIENT")
        _need(all(type(row) is tuple and len(row) == 3 and type(row[0]) is str and
                  all(type(v) is float and math.isfinite(v) and v > 0 for v in row[1:]) for row in item.bars),
              "PLANNER_BAR_SERIES_INVALID")
        try:
            series = _bars_to_series(market, item.bars)
        except (TypeError, ValueError, OverflowError):
            raise PlannerError("PLANNER_BAR_SERIES_INVALID") from None
        _need(not odds_plan._series_problem(series, at.astimezone(timezone.utc).date()), "PLANNER_BAR_SERIES_INVALID")
        return series, receipts

    def _plan(self, at, scope):
        market, cap, window_end, universe = scope(at)
        _need(type(market) is str and _MARKET.fullmatch(market) and market != "KRW-KRW", "PLANNER_SYMBOL_INVALID")
        symbol = market.split("-", 1)[1]
        _need(type(universe) is bool, "PLANNER_PROFILE_REQUIRED")
        _need(universe or (market == self.symbol_provider() and symbol == self.template.leg.symbol),
              "PLANNER_FIXED_SYMBOL_MISMATCH")
        _need(type(cap) is Decimal and cap.is_finite() and cap > 0, "PLANNER_STAKE_CAP_REQUIRED")
        amount = min(Decimal(str(self.template.stake_krw)), cap)
        stake = float(amount)
        _need(math.isfinite(stake) and stake > 0 and Decimal(str(stake)) == amount, "PLANNER_STAKE_PRECISION")
        day = at.astimezone(model.KST).date()
        end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=model.KST) - timedelta(seconds=60)
        _need(_aware(window_end), "PLANNER_WINDOW_REQUIRED")
        end = min(end, window_end)
        if self.session_ttl is not None:
            end = min(end, at + self.session_ttl)
        _need(at < end, "PLANNER_WINDOW_EXPIRED")
        plan = replace(self.template, start=day, leg=replace(self.template.leg, symbol=symbol), stake_krw=stake)
        return market, plan, end, universe

    def select(self, scope):
        started = self.clock()
        _need(_aware(started), "PLANNER_CLOCK_INVALID")
        market, plan, _, universe = self._plan(started, scope)
        series, receipts = self._bars(market, started)
        now = self.clock()
        _need(_aware(now) and now >= started and started.astimezone(timezone.utc).date() == now.astimezone(timezone.utc).date(),
              "PLANNER_BARS_DAY_CHANGED")
        checked_market, selected, end, checked_universe = self._plan(now, scope)
        _need((checked_market, selected, checked_universe) == (market, plan, universe), "PLANNER_SELECTION_CHANGED")
        observation = self.observation_provider()
        _need(_aware(getattr(observation, "asof", None)) and timedelta(0) <= now-observation.asof <= timedelta(seconds=30),
              "PLANNER_ACCOUNT_NOT_CURRENT")
        with localcontext() as numeric:
            numeric.prec = 2048
            numeric.traps[Inexact] = True
            ctx = owner.load_context(now, observation.positions)
        _need(model.is_sealed(ctx) and ctx.owner.ok and ctx.code_signed and ctx.active.valid,
              "PLANNER_OWNER_CONTEXT_UNUSABLE")
        plan_hash = odds_plan.plan_hash(plan)
        typed = [plan.leg.assumed_p] if plan.leg.edge_source == "assumed" else []
        comparison, counter, count, rates, runs = begin_run(None, [plan_hash], typed)
        inputs = odds_plan.Inputs(now=now, series=series,
            sessions=tuple((plan.start + timedelta(days=i)).isoformat() for i in range(plan.horizon_days)),
            price_limits=(), calendar_sha256="", calendar_version="", calendar_md5s=(), calendar_error="", replay=None,
            comparison_id=comparison, run_counter=counter, comparison_plans=count, comparison_typed=rates,
            plan_runs=runs[plan_hash], provenance=odds_plan.Provenance(repo_anchor="UNVERSIONED",
            tree_hash=ctx.code_hash, cryptography="unrecorded"))
        result = simulate.simulate(plan, ctx, inputs)
        seed = models.market_seed(models.data_hashes(series, None), "", comparison, counter).hex()
        passed = (result.refused is None and not any(flag.level == "red" for flag in result.flags)
                  and result.plan_hash == plan_hash and result.provenance.get("seed_hex") == seed)
        return Selection(value=PreparationInputs(selected_plan=plan, inputs=inputs, selection_seed_hex=seed,
            expires_at=end), market=market, universe=universe, bar_receipts=receipts, plan_hash=plan_hash, rendered_card=odds_report.render(result), passed=passed)

    def prepare_builder(self, selection, scope):
        _need(type(selection) is Selection and selection.passed, "PLANNER_ODDS_SELECTION_REQUIRED")
        value = selection.value
        started = self.clock()
        _need(_aware(started) and started >= value.inputs.now, "PLANNER_CLOCK_ROLLBACK")
        series, receipts = self._bars(selection.market, started)
        _need(receipts == selection.bar_receipts and series == value.inputs.series, "PLANNER_BARS_CHANGED")

        def build(now):
            _need(_aware(now) and now >= started, "PLANNER_CLOCK_ROLLBACK")
            _need(now.astimezone(timezone.utc).date() == started.astimezone(timezone.utc).date()
                  and now.astimezone(model.KST).date() == value.selected_plan.start, "PLANNER_BARS_DAY_CHANGED")
            market, plan, end, universe = self._plan(now, scope)
            _need((market, universe) == (selection.market, selection.universe), "PLANNER_SELECTION_CHANGED")
            _need(plan.stake_krw >= value.selected_plan.stake_krw, "PLANNER_STAKE_CHANGED")
            return PreparationInputs(selected_plan=value.selected_plan, inputs=replace(value.inputs, now=now, series=series),
                selection_seed_hex=value.selection_seed_hex, expires_at=min(end, value.expires_at))
        return build
