"""Per-coin fresh odds for the top-N coins of the Upbit KRW universe snapshot in force (spec section 9).

One batch simulates the reviewed template plan once per coin with a fresh comparison seed, journals one inert
``universe_odds_batch`` control row and registers the result in this process by identity, like
``session._PREPARED``. It never prepares, signs or arms a session and reads no market data: the caller supplies the
plain final daily bars and their receipt digests. Only an object returned here can be bound by prepare_session.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, replace
from datetime import date, datetime, timedelta
from decimal import Inexact, localcontext
import hashlib
import re
from uuid import uuid4

from core.compliance import model, owner, rules
from core.odds import models, plan as odds_plan, report, simulate
from execution_control.capability import digest, plain
from execution_control.store import guard_pending

# ponytail: a fixed cap keeps one batch row far under store.MAX_ROW_BYTES; raise it together with the row-size test.
MAX_COINS = 64
_CLOCK_AGE = timedelta(seconds=30)
_HEX = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True, kw_only=True)
class CoinOdds:
    market: str              # "KRW-<coin>"
    plan_hash: str           # the template with this coin and the batch's Seoul date as its start
    seed_hex: str            # the market seed of this coin's fresh comparison
    inputs_digest: str       # digest of the coin's candle receipt sha256 list
    report_digest: str       # sha256 of the rendered card
    passed: bool


@dataclass(frozen=True, kw_only=True)
class UniverseBatch:
    batch_digest: str        # digest of every other field
    seoul_date: date
    template_plan_hash: str
    code_hash: str
    state_hash: str
    owner_head: str          # sha256 of the last owner-log row
    rule_sha256: str
    snapshot_sha256: str
    n: int
    coins: tuple[CoinOdds, ...]
    started_at: datetime
    finished_at: datetime
    prior_batches: int       # batches already journaled for this snapshot and Seoul date


_BATCHES: dict[int, tuple[UniverseBatch, str]] = {}


class UniverseOddsError(ValueError):
    """Fixed refusal codes; no planner or provider text is exposed."""


def _require(condition, code):
    if not condition:
        raise UniverseOddsError(code)


def _body(batch):
    return {f.name: getattr(batch, f.name) for f in fields(UniverseBatch) if f.name != "batch_digest"}


def registered_batch(batch_digest):
    """The batch this process issued under `batch_digest`, unchanged since; else None."""
    for batch, recorded in tuple(_BATCHES.values()):  # one-step snapshot: run_batch may register concurrently
        if recorded == batch_digest == batch.batch_digest == digest(_body(batch)):
            return batch
    return None


def _instant(value):
    return type(value) is datetime and value.utcoffset() is not None


def _read(clock):
    try:
        stamp = clock()
    except Exception:
        raise UniverseOddsError("UNIVERSE_BATCH_CLOCK_INVALID") from None
    _require(_instant(stamp), "UNIVERSE_BATCH_CLOCK_INVALID")
    return stamp


def _template_ok(template):
    leg = getattr(template, "leg", None)
    return (type(template) is odds_plan.Plan and type(leg) is odds_plan.Leg and leg.venue == "upbit"
            and leg.edge_source != odds_plan.REPLAY_SOURCE      # the replay edge is a KRW-BTC card (plan.py)
            and type(template.horizon_days) is int and 1 <= template.horizon_days <= odds_plan.MAX_HORIZON_DAYS)


def _bars_ok(market, item):
    receipts = getattr(item, "receipt_sha256", None)
    return (getattr(item, "market", None) == market and type(getattr(item, "bars", None)) is tuple
            and len(item.bars) > 0 and type(receipts) is tuple and len(receipts) > 0
            and all(type(value) is str and _HEX.fullmatch(value) for value in receipts))


def _series(market, rows):
    """The plan.Series that load_leg's upbit_daily path builds from the same final rows (bars.py:400-402), without
    part components: the receipts are bound through inputs_digest instead."""
    dates = tuple(str(day) for day, _, _ in rows)
    opens = tuple(float(value) for _, value, _ in rows)
    closes = tuple(float(value) for _, _, value in rows)
    return odds_plan.Series(symbol=market, source="UPBIT", dates=dates, open=opens, close=closes, adjustment="",
                            status="final",
                            md5=odds_plan.series_md5(market, "UPBIT", dates, opens, closes, "", "final"))


def _context(now, positions):
    """The owner context at `now` over the caller's positions, in the numeric context Controller.observe uses."""
    with localcontext() as numeric:
        numeric.prec = 2048
        numeric.traps[Inexact] = True
        return owner.load_context(now, positions)


def _coin(template, ctx, now, market, series, receipts):
    coin_plan = replace(template, start=now.astimezone(model.KST).date(),
                        leg=replace(template.leg, symbol=market.split("-", 1)[1]))
    inputs = odds_plan.Inputs(
        now=now, series=series,
        sessions=tuple((coin_plan.start + timedelta(days=i)).isoformat() for i in range(coin_plan.horizon_days)),
        price_limits=(), calendar_sha256="", calendar_version="", calendar_md5s=(), calendar_error="", replay=None,
        comparison_id=uuid4().hex, run_counter=1, comparison_plans=1,
        comparison_typed=int(coin_plan.leg.edge_source == "assumed"), plan_runs=1,
        # No repository read here: the signed code hash stands in for the tree hash.
        provenance=odds_plan.Provenance(repo_anchor="UNVERSIONED", tree_hash=ctx.code_hash, cryptography="unrecorded"))
    seed = models.market_seed(models.data_hashes(series, None), "", inputs.comparison_id, 1).hex()
    result = simulate.simulate(coin_plan, ctx, inputs)
    plan_hash = odds_plan.plan_hash(coin_plan)
    return CoinOdds(market=market, plan_hash=plan_hash, seed_hex=seed, inputs_digest=digest(list(receipts)),
                    report_digest=hashlib.sha256(report.render(result).encode("utf-8")).hexdigest(),
                    passed=(result.refused is None and not any(flag.level == "red" for flag in result.flags)
                            and result.plan_hash == plan_hash and result.provenance.get("seed_hex") == seed))


def run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof):
    """Simulate `template` once per top-N coin of the snapshot in force and journal one batch row (spec section 9).

    `bars` maps each market to PR 2's UniverseBars, read by attribute: `market`, `bars` as (ISO date, open, close)
    rows and `receipt_sha256`. `now` is the inputs' time; the first `clock` read must lie within 30 seconds after
    it. Callers take now after the bars are read. `positions` is the model.Positions the owner context is loaded
    over, and `positions_asof` its aware reconciliation time: at or before `now` and at most 30 seconds before the
    first clock read. Callers pass the positions they last reconciled; the batch never calls the account provider.
    Refuses while any session is armed, with no snapshot in force, or inside a pending continuous-guard
    transaction. A refusal writes nothing and registers nothing.
    """
    from execution_control.controller import _event_data
    _require(callable(clock) and _instant(now), "UNIVERSE_BATCH_CLOCK_INVALID")
    _require(not owner._positions_problem(positions), "UNIVERSE_BATCH_POSITIONS_INVALID")  # load_context's check
    started = _read(clock)
    _require(timedelta(0) <= started - now <= _CLOCK_AGE, "UNIVERSE_BATCH_CLOCK_INVALID")
    # prepare_session's account rule, checked once before any context load or simulation
    _require(_instant(positions_asof) and positions_asof <= now
             and timedelta(0) <= started - positions_asof <= _CLOCK_AGE, "UNIVERSE_BATCH_POSITIONS_STALE")
    _require(type(n) is int and 1 <= n <= MAX_COINS, "UNIVERSE_BATCH_N_INVALID")
    _require(_template_ok(template), "UNIVERSE_BATCH_TEMPLATE_INVALID")
    ctx = _context(now, positions)
    _require(model.is_sealed(ctx) and ctx.owner.ok and ctx.code_signed and ctx.active.valid,
             "UNIVERSE_BATCH_STATE_UNUSABLE")
    _require(not ctx.session.armed and not ctx.owner.armed_sessions, "UNIVERSE_BATCH_SESSION_ARMED")
    universe = ctx.universe
    markets = rules.universe_top_n(universe, n) if universe is not None else ()
    _require(len(markets) > 0, "UNIVERSE_BATCH_NO_SNAPSHOT")
    _require(isinstance(bars, Mapping) and all(_bars_ok(market, bars.get(market)) for market in markets),
             "UNIVERSE_BATCH_BARS_MISSING")
    try:
        series = {market: _series(market, bars[market].bars) for market in markets}
    except (TypeError, ValueError):
        raise UniverseOddsError("UNIVERSE_BATCH_BARS_MISSING") from None
    coins = tuple(_coin(template, ctx, now, market, series[market], bars[market].receipt_sha256)
                  for market in markets)
    day = now.astimezone(model.KST).date()
    with controller.journal.transaction() as tx:
        events = tx.events
        # A row inside a pending guard transaction would leave it unresumable.
        _require(not guard_pending(events), "UNIVERSE_BATCH_GUARD_PENDING")
        finished = _read(clock)
        _require(started <= finished and finished.astimezone(model.KST).date() == day
                 and (not events or datetime.fromisoformat(events[-1]["utc"]) <= finished),
                 "UNIVERSE_BATCH_CLOCK_INVALID")
        body = dict(seoul_date=day, template_plan_hash=odds_plan.plan_hash(replace(template, start=day)),
                    code_hash=ctx.code_hash, state_hash=ctx.active.state_hash, owner_head=ctx.owner.head[1],
                    rule_sha256=universe.rule_sha256, snapshot_sha256=universe.snapshot_sha256, n=n, coins=coins,
                    started_at=started, finished_at=finished,
                    prior_batches=sum(1 for row in events if row["kind"] == "universe_odds_batch"
                                      and row["data"]["snapshot_sha256"] == universe.snapshot_sha256
                                      and row["data"]["seoul_date"] == day.isoformat()))
        batch = UniverseBatch(batch_digest=digest(body), **body)
        payload = plain(batch)
        _event_data("universe_odds_batch", payload)   # never write a row the controller could not fold
        tx.append("universe_odds_batch", payload, now=finished)
    _BATCHES[id(batch)] = (batch, batch.batch_digest)
    return batch
