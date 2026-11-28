"""D14-clean current odds planner for owner-prepared sessions; no legacy research imports.

Consumes only current Upbit daily bars from execution_accounts.universe, sealed
owner compliance context from core.compliance, and pure Monte Carlo simulation
from core.odds. Never signs, activates or caches an execution session.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, Inexact, localcontext
import json
import re
from typing import Callable
from uuid import uuid4

from core.compliance import model, owner
from core.odds import models, plan as odds_plan, simulate
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
    return float(dec)


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

    try:
        body = json.loads(raw, object_pairs_hook=_pairs, parse_float=_bad, parse_constant=_bad)
    except PlannerError:
        raise
    except Exception:
        raise PlannerError("PLANNER_JSON_INVALID") from None

    _need(type(body) is dict and set(body) == _PLAN_KEYS, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(type(body["schema_version"]) is int and body["schema_version"] == 1
          and body["kind"] == "tradegen-live-odds-template/1", "PLANNER_TEMPLATE_KIND_INVALID")
    _need(type(body["name"]) is str and 0 < len(body["name"]) <= 128, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["track"] in odds_plan.TRACKS, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(type(body["horizon_days"]) is int and 1 <= body["horizon_days"] <= odds_plan.MAX_HORIZON_DAYS,
          "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["model"] in odds_plan.MODELS, "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["edge_source"] in ("none", "assumed"), "PLANNER_TEMPLATE_SCHEMA_INVALID")
    _need(body["sizing"] in odds_plan.SIZINGS, "PLANNER_TEMPLATE_SCHEMA_INVALID")
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
class CurrentPlanner:
    """Build fresh PreparationInputs from reconciled account state and live daily bars."""
    template: odds_plan.Plan
    symbol_provider: Callable[[], str]
    observation_provider: Callable[[], object]
    clock: Callable[[], datetime]
    bars_reader: Callable[..., Mapping] | Callable = daily_bars
    session_ttl: timedelta | None = None

    def __post_init__(self) -> None:
        _need(type(self.template) is odds_plan.Plan and type(self.template.leg) is odds_plan.Leg
              and self.template.leg.venue == "upbit"
              and self.template.leg.edge_source != odds_plan.REPLAY_SOURCE,
              "PLANNER_TEMPLATE_INVALID")
        _need(callable(self.symbol_provider) and callable(self.observation_provider)
              and callable(self.clock) and callable(self.bars_reader),
              "PLANNER_DEPENDENCIES_REQUIRED")
        if self.session_ttl is not None:
            _need(type(self.session_ttl) is timedelta
                  and timedelta(0) < self.session_ttl <= timedelta(hours=24),
                  "PLANNER_TTL_INVALID")

    def __call__(self) -> PreparationInputs:
        started = self.clock()
        _need(_aware(started), "PLANNER_CLOCK_INVALID")
        market = self.symbol_provider()
        _need(type(market) is str and _MARKET.fullmatch(market) is not None, "PLANNER_SYMBOL_INVALID")
        bars_by_market = self.bars_reader((market,), now=started, clock=self.clock)
        _need(isinstance(bars_by_market, dict) and market in bars_by_market, "PLANNER_BARS_UNAVAILABLE")
        bar_item = bars_by_market[market]
        _need(getattr(bar_item, "market", None) == market and type(getattr(bar_item, "bars", None)) is tuple
              and len(bar_item.bars) >= odds_plan.MIN_BARS, "PLANNER_BARS_INSUFFICIENT")

        observation = self.observation_provider()
        now = self.clock()
        _need(_aware(now) and now >= started, "PLANNER_CLOCK_ROLLBACK")
        _need(observation is not None and _aware(getattr(observation, "asof", None))
              and observation.asof <= now and now - observation.asof <= timedelta(seconds=30),
              "PLANNER_ACCOUNT_NOT_CURRENT")

        series = _bars_to_series(market, bar_item.bars)
        seoul_day = now.astimezone(model.KST).date()
        selected_plan = replace(
            self.template,
            start=seoul_day,
            leg=replace(self.template.leg, venue="upbit", symbol=market.split("-", 1)[1]),
        )
        with localcontext() as numeric:
            numeric.prec = 2048
            numeric.traps[Inexact] = True
            ctx = owner.load_context(now, observation.positions)
        _need(model.is_sealed(ctx) and ctx.owner.ok and ctx.code_signed and ctx.active.valid,
              "PLANNER_OWNER_CONTEXT_UNUSABLE")

        inputs = odds_plan.Inputs(
            now=now,
            series=series,
            sessions=tuple((seoul_day + timedelta(days=i)).isoformat()
                           for i in range(selected_plan.horizon_days)),
            price_limits=(),
            calendar_sha256="",
            calendar_version="",
            calendar_md5s=(),
            calendar_error="",
            replay=None,
            comparison_id=uuid4().hex,
            run_counter=1,
            comparison_plans=1,
            comparison_typed=int(selected_plan.leg.edge_source == "assumed"),
            plan_runs=1,
            provenance=odds_plan.Provenance(
                repo_anchor="UNVERSIONED",
                tree_hash=ctx.code_hash,
                cryptography="unrecorded",
            ),
        )
        report = simulate.simulate(selected_plan, ctx, inputs)
        _need(report.refused is None and not any(flag.level == "red" for flag in report.flags),
              "PLANNER_ODDS_REFUSED")
        seed_hex = models.market_seed(
            models.data_hashes(series, None),
            inputs.calendar_sha256,
            inputs.comparison_id,
            inputs.run_counter,
        ).hex()
        expires_at = None if self.session_ttl is None else now + self.session_ttl
        return PreparationInputs(
            selected_plan=selected_plan,
            inputs=inputs,
            selection_seed_hex=seed_hex,
            expires_at=expires_at,
        )
