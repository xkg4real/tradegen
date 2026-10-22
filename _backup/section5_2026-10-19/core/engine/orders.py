"""Simulated order lifecycle: OPEN → FILLED / CANCELLED / REJECTED (§3).

Everything here is a simulation. There is no broker client in this package and
no code path that reaches a real venue — the service contract treats live
integration as a separately negotiated scope, so the default build practises
the workflow without risking anything.

Two behaviours are modelled carefully because they are what an operator has to
rehearse:

  * **Manual fill and cancel** (§3 "모의주문 수동 체결과 취소"). A simulated
    order does not fill itself on a timer. The operator fills it, which forces
    them to see the order sitting open and decide — the same decision a real
    resting order demands.

  * **Rejection carries a reason** (§3 "조건이 실행되지 않은 이유 표시").
    A rejected order records which guard stopped it, so "nothing happened" is
    never the whole story.

Order ids are deterministic per (rule, revision, trigger sequence) so the
idempotency guard in `guards.py` can recognise a duplicate submission of the
same logical trigger after a restart.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from core.rules.model import OrderKind, Side


class OrderStatus(str, Enum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

    @property
    def terminal(self) -> bool:
        return self is not OrderStatus.OPEN


@dataclass(frozen=True)
class SimulatedOrder:
    id: str
    rule_id: str
    rule_revision: int
    rule_name: str
    symbol: str
    market: str
    side: Side
    kind: OrderKind
    quantity: Decimal
    limit_price: Optional[Decimal]
    notional: Optional[Decimal]
    trigger_price: Decimal
    status: OrderStatus = OrderStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    settled_at: Optional[datetime] = None
    fill_price: Optional[Decimal] = None
    reason: str = ""                    # why rejected, or why cancelled
    as_of: Optional[datetime] = None    # R-27 rule 7 (M5): the triggering quote's own timestamp for an intraday entry

    @property
    def open(self) -> bool:
        return self.status is OrderStatus.OPEN

    @property
    def age_seconds(self) -> float:
        end = self.settled_at or datetime.now(timezone.utc)
        return (end - self.created_at).total_seconds()

    def describe(self) -> str:
        price = (f"limit {self.limit_price:,}" if self.kind is OrderKind.LIMIT
                 and self.limit_price is not None else "market")
        return (f"{self.side.value} {self.quantity:,} {self.symbol} "
                f"({price}) — {self.status.value}")


def order_id(rule_id: str, revision: int, sequence: int) -> str:
    """Deterministic, so the same logical trigger cannot be submitted twice."""
    return f"{rule_id}-r{revision}-t{sequence}"


class OrderBook:
    """In-memory book of simulated orders. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._orders: dict[str, SimulatedOrder] = {}

    # -- reads ---------------------------------------------------------------
    def get(self, oid: str) -> Optional[SimulatedOrder]:
        with self._lock:
            return self._orders.get(oid)

    def all(self) -> tuple[SimulatedOrder, ...]:
        with self._lock:
            return tuple(sorted(self._orders.values(),
                                key=lambda o: o.created_at, reverse=True))

    def open_orders(self) -> tuple[SimulatedOrder, ...]:
        return tuple(o for o in self.all() if o.open)

    def for_rule(self, rule_id: str) -> tuple[SimulatedOrder, ...]:
        return tuple(o for o in self.all() if o.rule_id == rule_id)

    def exists(self, oid: str) -> bool:
        with self._lock:
            return oid in self._orders

    def counts_today(self, *, now: Optional[datetime] = None) -> dict[str, int]:
        now = now or datetime.now(timezone.utc)
        today = now.date()
        tally = {s.value: 0 for s in OrderStatus}
        for order in self.all():
            if order.created_at.date() == today:
                tally[order.status.value] += 1
        return tally

    def notional_today(self, *, now: Optional[datetime] = None) -> Decimal:
        """Cash committed today, counting everything that was not rejected."""
        now = now or datetime.now(timezone.utc)
        today = now.date()
        total = Decimal(0)
        for order in self.all():
            if order.created_at.date() != today:
                continue
            if order.status is OrderStatus.REJECTED:
                continue
            total += order.notional or Decimal(0)
        return total

    # -- writes --------------------------------------------------------------
    def place(self, order: SimulatedOrder) -> Optional[SimulatedOrder]:
        """Insert, or return None if this id is already present.

        The duplicate check lives inside the lock rather than in a separate
        `exists()` call by the caller: two evaluation passes overlapping on the
        same rule would both pass a check-then-place and place the same logical
        trigger twice. Returning None makes the guard atomic.
        """
        with self._lock:
            if order.id in self._orders:
                return None
            self._orders[order.id] = order
            return order

    def _settle(self, oid: str, status: OrderStatus, *,
                fill_price: Optional[Decimal] = None,
                reason: str = "") -> tuple[bool, str]:
        with self._lock:
            order = self._orders.get(oid)
            if order is None:
                return False, "No such order."
            if order.status.terminal:
                return False, f"Order is already {order.status.value.lower()}."
            self._orders[oid] = replace(
                order, status=status, settled_at=datetime.now(timezone.utc),
                fill_price=fill_price, reason=reason,
            )
            return True, ""

    def fill(self, oid: str, price: Decimal) -> tuple[bool, str]:
        """Operator-initiated fill (§3). Never happens on its own."""
        return self._settle(oid, OrderStatus.FILLED, fill_price=price)

    def cancel(self, oid: str, reason: str = "cancelled by operator") -> tuple[bool, str]:
        return self._settle(oid, OrderStatus.CANCELLED, reason=reason)

    def reject(self, order: SimulatedOrder, reason: str) -> SimulatedOrder:
        """Record a trigger that a guard stopped, so the refusal is visible."""
        rejected = replace(order, status=OrderStatus.REJECTED,
                           settled_at=datetime.now(timezone.utc), reason=reason)
        with self._lock:
            self._orders[rejected.id] = rejected
        return rejected

    def cancel_all_open(self, reason: str) -> int:
        count = 0
        for order in self.open_orders():
            ok, _ = self.cancel(order.id, reason)
            count += int(ok)
        return count

    def reset(self) -> None:
        """§3 "연습 시나리오 초기화" — clear the practice book."""
        with self._lock:
            self._orders.clear()

    def snapshot(self) -> list[dict]:
        return [
            {
                "id": o.id, "rule_id": o.rule_id, "rule_revision": o.rule_revision,
                "rule_name": o.rule_name, "symbol": o.symbol, "market": o.market,
                "side": o.side.value, "kind": o.kind.value,
                "quantity": str(o.quantity),
                "limit_price": str(o.limit_price) if o.limit_price is not None else None,
                "notional": str(o.notional) if o.notional is not None else None,
                "trigger_price": str(o.trigger_price), "status": o.status.value,
                "created_at": o.created_at.isoformat(),
                "settled_at": o.settled_at.isoformat() if o.settled_at else None,
                "fill_price": str(o.fill_price) if o.fill_price is not None else None,
                "reason": o.reason,
                "as_of": o.as_of.isoformat() if o.as_of else None,
            }
            for o in self.all()
        ]

    def restore(self, rows: list[dict]) -> None:
        with self._lock:
            self._orders.clear()
            for raw in rows or []:
                try:
                    self._orders[raw["id"]] = SimulatedOrder(
                        id=raw["id"], rule_id=raw["rule_id"],
                        rule_revision=int(raw.get("rule_revision") or 1),
                        rule_name=raw.get("rule_name", ""), symbol=raw["symbol"],
                        market=raw.get("market", ""), side=Side(raw["side"]),
                        kind=OrderKind(raw["kind"]),
                        quantity=Decimal(raw["quantity"]),
                        limit_price=Decimal(raw["limit_price"]) if raw.get("limit_price") else None,
                        notional=Decimal(raw["notional"]) if raw.get("notional") else None,
                        trigger_price=Decimal(raw.get("trigger_price") or 0),
                        status=OrderStatus(raw["status"]),
                        created_at=datetime.fromisoformat(raw["created_at"]),
                        settled_at=datetime.fromisoformat(raw["settled_at"]) if raw.get("settled_at") else None,
                        fill_price=Decimal(raw["fill_price"]) if raw.get("fill_price") else None,
                        reason=raw.get("reason", ""),
                        as_of=datetime.fromisoformat(raw["as_of"]) if raw.get("as_of") else None,
                    )
                except Exception:
                    continue          # one malformed row must not lose the book


# --------------------------------------------------------------------------- #
# R-27 simulated fill model (M5; TASK-M5-10, M5-11) with the tech-fund execution invariants INV-1 / INV-2
# folded in. Everything below is pure: `simulate_fill` computes a `Fill` or a `NonFillable` from PIT inputs
# and never touches a book; the book runner applies a Fill through `OrderBook.fill` (the one mutation path,
# T-RO-01) and leaves a NonFillable order OPEN, carried to the next session and logged. The manual contract
# of `OrderBook.fill` above is untouched. No stop path exists here (INV-5): exits come from the signal.
# --------------------------------------------------------------------------- #
VENUES = ("KRX", "NYSE", "KOSPI200_futures")
INSTRUMENT_KINDS = ("stock", "etf", "futures")
FILL_STATUSES = ("filled", "non_fillable_limit_lock", "carried")                 # spec L2940
DECISION_PRICE_SOURCES = ("snapshot_1519", "official_close")                     # spec L2940
FILL_FLAGS = ("LP_exempt_auction", "inav_residual_gt_30bp")                      # spec L2940
# NonFillable.reason vocabulary: R-27 rule 3 and its fail-closed rows (L2913-2946) plus tech-fund INV-1 / INV-2
# (never NXT or after-hours prints; VI, circuit-breaker and halt days unfillable). Deliberately no stop reason.
NONFILL_REASONS = ("limit_up_locked", "limit_down_locked", "halt_day", "no_official_close",
                   "nxt_or_after_hours_print", "bar_derived_close", "print_outside_random_end", "intraday_print",
                   "expiry_day_no_trading", "not_tradable")
LOCK_REASONS = ("limit_up_locked", "limit_down_locked")
CARRY_LABELS = ("carried_limit_up_entry", "carried_limit_down_exit_2x", "carried")
OFFICIAL_PRINT_SOURCES = ("regular_session", "closing_auction", "moc")           # INV-1: the KRX / NYSE official close
REFUSED_PRINT_SOURCES = {"NXT": "nxt_or_after_hours_print", "after_hours": "nxt_or_after_hours_print",
                         "KRX_after_market": "nxt_or_after_hours_print", "post_close_session": "nxt_or_after_hours_print",
                         "bar": "bar_derived_close"}
LIMIT_DOWN_CARRY_COST_MULTIPLIER = 2.0        # INV-2: "an assumption, not measured" (R3:802)
_EPS = 1e-9


class BarDerivedClose(ValueError):
    """A daily close offered from intraday bars (R-27 rule 6: forbidden; the loader refuses it)."""


@dataclass(frozen=True)
class FillModel:
    """The rules-store `fill_model.<venue>` block (spec L2930-2936), read-only."""
    venue: str
    fill: str
    snapshot: Optional[str] = None
    snapshot_local: Optional[str] = None          # "15:19" KST since 2016-08-01 (KRX) / "15:50" ET (NYSE)
    random_end_max_s: Optional[int] = None
    fallback: Optional[str] = None
    limit_price: Optional[str] = None
    limit_lock: Optional[str] = None
    etf_flag: Optional[str] = None
    inav_residual_flag_bp: Optional[float] = None
    trades_until_local: Optional[str] = None
    expiry_day_stop_local: Optional[str] = None
    bars: dict = field(default_factory=dict)


def _shipped_fill_model() -> dict:
    from core.rules.macro_rules import load_store     # lazy: scipy-heavy, never needed by the operator engine
    return load_store().get("fill_model")


def fill_model(venue: str, *, config: Optional[dict] = None) -> FillModel:
    """`fill_model(venue) -> FillModel` (spec L2893). `config` is the store's `fill_model` block; default shipped."""
    cfg = config if config is not None else _shipped_fill_model()
    if venue not in VENUES or venue not in cfg:
        raise KeyError(f"fill_model: venue {venue!r} not in {VENUES}")
    v = cfg[venue]
    etf = v.get("etf") or {}
    return FillModel(
        venue=venue, fill=v.get("fill", "official_close"), snapshot=v.get("snapshot"),
        snapshot_local=v.get("snapshot_kst_since_2016-08-01") or v.get("snapshot_et"),
        random_end_max_s=v.get("random_end_max_s"), fallback=v.get("fallback"), limit_price=v.get("limit_price"),
        limit_lock=v.get("limit_lock"), etf_flag=etf.get("flag"), inav_residual_flag_bp=etf.get("inav_residual_flag_bp"),
        trades_until_local=v.get("trades_until_kst"), expiry_day_stop_local=v.get("expiry_day_stop_kst"),
        bars=dict(cfg.get("bars") or {}))


@dataclass(frozen=True)
class FillSession:
    """The PIT inputs of one (line, session) handed to `simulate_fill` (spec L2897-2902). `official_close` must
    carry `value_status == "official_close"` and come from the regular session / closing auction (INV-1); the
    tick is the effective-dated tick at the limit price (a stock tick table is an owner input, F-18)."""
    venue: str
    session_date: date
    instrument: str = "stock"                    # stock | etf | futures
    official_close: Optional[float] = None
    value_status: str = "official_close"
    print_source: str = "closing_auction"        # closing_auction | regular_session | moc | NXT | after_hours | bar
    prev_close: Optional[float] = None
    price_limit: Optional[float] = None          # regime_tags("KR", d)["price_limit"], a fraction (0.30)
    tick: Optional[float] = None
    inav: Optional[float] = None
    halted: bool = False                         # VI / circuit breaker / trading halt day (INV-2)
    halt_kind: str = ""
    close_utc: Optional[datetime] = None         # scheduled close (clocks.decision_time_utc)
    print_utc: Optional[datetime] = None         # the logged closing print, when known
    random_end_max_s: Optional[int] = None       # calendars.KR.random_end max_s (30 since 2015-06-15)
    expiry_day: bool = False                     # futures: the expiring contract stops at 15:20 KST (rule 5)
    snapshot_verified: bool = False              # the KIS quote field (QF1-A25); False -> official-close decision, labelled

    def __post_init__(self) -> None:
        if self.venue not in VENUES:
            raise ValueError(f"venue {self.venue!r} not in {VENUES}")
        if self.instrument not in INSTRUMENT_KINDS:
            raise ValueError(f"instrument {self.instrument!r} not in {INSTRUMENT_KINDS}")


@dataclass(frozen=True)
class Fill:
    price: float
    session_date: date
    fill_status: str = "filled"
    decision_price_source: str = "official_close"
    flags: tuple[str, ...] = ()
    cost_multiplier: float = 1.0                 # 2.0 on a carried limit-down exit (INV-2)
    reason: str = ""
    inav_residual_bp: Optional[float] = None
    carried_from: Optional[date] = None
    labels: tuple[str, ...] = ()                 # e.g. "snapshot_fallback_official_close_UNVERIFIED"

    def extras(self) -> dict:
        """The `overlay_decision.extras` R-27 fields (spec L2940)."""
        return {"fill_model": "R-27", "decision_price_source": self.decision_price_source,
                "fill_status": self.fill_status, "flags": list(self.flags), "cost_multiplier": self.cost_multiplier,
                "labels": list(self.labels)}


@dataclass(frozen=True)
class NonFillable:
    reason: str
    session_date: date
    carry: bool = True                           # the order carries to the next session and is logged (rule 3)
    detail: str = ""
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.reason not in NONFILL_REASONS:
            raise ValueError(f"NonFillable.reason {self.reason!r} not in {NONFILL_REASONS}")

    @property
    def fill_status(self) -> str:
        return "non_fillable_limit_lock" if self.reason in LOCK_REASONS else "carried"

    @property
    def alert(self) -> bool:
        """No official close for the session: carried and alerted (spec L2944)."""
        return self.reason == "no_official_close"

    def extras(self) -> dict:
        return {"fill_model": "R-27", "decision_price_source": "official_close", "fill_status": self.fill_status,
                "flags": list(self.flags), "reason": self.reason, "detail": self.detail}


def _side(order) -> str:
    side = getattr(order, "side", order)
    value = getattr(side, "value", side)
    text = str(value).upper()
    if text not in ("BUY", "SELL"):
        raise ValueError(f"order side {side!r} is not BUY or SELL")
    return text


def _round_toward(x: float, tick: float, prev_close: float) -> float:
    """Round x to the tick toward prev_close (floor above it, ceil below it)."""
    if x >= prev_close:
        return math.floor(x / tick + _EPS) * tick
    return math.ceil(x / tick - _EPS) * tick


def limit_prices(prev_close: float, price_limit: float, tick: float) -> tuple[float, float]:
    """(limit_down, limit_up) = prev_close x (1 -/+ price_limit) rounded to the tick toward prev_close (L2915)."""
    if not (prev_close > 0 and 0 < price_limit < 1 and tick > 0):
        raise ValueError(f"prev_close {prev_close}, price_limit {price_limit}, tick {tick} out of range")
    return (_round_toward(prev_close * (1.0 - price_limit), tick, prev_close),
            _round_toward(prev_close * (1.0 + price_limit), tick, prev_close))


def limit_lock(official_close: float, prev_close: float, price_limit: float, tick: float) -> Optional[str]:
    """"up" | "down" | None: the official close EQUALS the tick-rounded limit price. A |r| >= limit test is never
    used (L2915: a tick-rounded limit print is below the nominal limit; SK hynix +29.95%)."""
    down, up = limit_prices(prev_close, price_limit, tick)
    tol = tick * 1e-6
    if abs(official_close - up) <= tol:
        return "up"
    if abs(official_close - down) <= tol:
        return "down"
    return None


def inav_check(close: float, inav: Optional[float], *, flag_bp: float = 30.0) -> tuple[Optional[float], tuple[str, ...]]:
    """R-27 rule 2: every ETF close is `LP_exempt_auction`; |close / iNAV - 1| > flag_bp is `inav_residual_gt_30bp`."""
    flags = ["LP_exempt_auction"]
    if inav is None or inav <= 0:
        return None, tuple(flags)
    residual_bp = (close / inav - 1.0) * 1e4
    if abs(residual_bp) > flag_bp + _EPS:
        flags.append("inav_residual_gt_30bp")
    return residual_bp, tuple(flags)


def _official_close_ok(s: FillSession) -> Optional[NonFillable]:
    """The fail-closed rows (L2943-2946) and INV-1: only an official close of the regular session fills."""
    if s.halted:
        return NonFillable("halt_day", s.session_date, detail=s.halt_kind or "VI / circuit breaker / trading halt")
    if s.print_source in REFUSED_PRINT_SOURCES:
        return NonFillable(REFUSED_PRINT_SOURCES[s.print_source], s.session_date, detail=f"print_source={s.print_source}")
    if s.print_source not in OFFICIAL_PRINT_SOURCES:
        return NonFillable("no_official_close", s.session_date, detail=f"unknown print_source {s.print_source!r}")
    if s.official_close is None or not math.isfinite(s.official_close) or s.official_close <= 0:
        return NonFillable("no_official_close", s.session_date, detail="no official close for the session; alert")
    if s.value_status != "official_close":
        return NonFillable("no_official_close", s.session_date, detail=f"value_status={s.value_status}")
    if s.print_utc is not None and s.close_utc is not None:
        if s.print_utc < s.close_utc:
            return NonFillable("intraday_print", s.session_date, detail="print precedes the scheduled close")
        bound = s.random_end_max_s if s.random_end_max_s is not None else 0
        if (s.print_utc - s.close_utc).total_seconds() > bound + _EPS:
            return NonFillable("print_outside_random_end", s.session_date,
                               detail=f"print {(s.print_utc - s.close_utc).total_seconds():.0f}s after the close > {bound}s")
    return None


def simulate_fill(order, session: FillSession, *, model: Optional[FillModel] = None,
                  carried: Optional[NonFillable] = None) -> "Fill | NonFillable":
    """`simulate_fill(order, session) -> Fill | NonFillable(reason)` (spec L2893). Pure.

    Rule 1 / INV-1: fill at the official close of the session (closing-call print under the random end); rule 2:
    ETF flags; rule 3 / INV-2: a stock at its tick-rounded limit is non-fillable at the close (limit-up for buys,
    limit-down for sells), carried and logged; a carried limit-down exit fills at the first unlocked session at
    2x cost; VI / circuit-breaker / halt days are unfillable; rule 4: NYSE MOC-equivalent; rule 5: the expiring
    futures contract stops at 15:20 KST. `carried` is the NonFillable the order carries from the prior session.
    """
    side = _side(order)
    refused = _official_close_ok(session)
    if refused is not None:
        return refused
    if session.instrument == "futures" and session.expiry_day:
        return NonFillable("expiry_day_no_trading", session.session_date,
                           detail="expiring contract stops at 15:20 KST; books roll before expiry (R-26)")
    flags: tuple[str, ...] = ()
    residual = None
    if session.instrument == "etf":
        bp = model.inav_residual_flag_bp if model and model.inav_residual_flag_bp is not None else 30.0
        residual, flags = inav_check(session.official_close, session.inav, flag_bp=bp)
    if session.prev_close is not None and session.price_limit is not None:
        if session.tick is None:
            # an instrument whose tick table cannot be read for the date is not tradable (L2863)
            return NonFillable("not_tradable", session.session_date,
                               detail="tick table unreadable for the date; not tradable in the simulated book")
        lock = limit_lock(session.official_close, session.prev_close, session.price_limit, session.tick)
        if lock == "up" and side == "BUY":
            return NonFillable("limit_up_locked", session.session_date, flags=flags,
                               detail="close equals the tick-rounded limit-up price; no entry (INV-2); carried")
        if lock == "down" and side == "SELL":
            return NonFillable("limit_down_locked", session.session_date, flags=flags,
                               detail="close equals the tick-rounded limit-down price; exit carried at 2x cost (INV-2)")
    labels = () if session.snapshot_verified else ("snapshot_fallback_official_close_UNVERIFIED",)
    mult, reason, carried_from = 1.0, "", None
    if carried is not None:
        carried_from = carried.session_date
        if carried.reason == "limit_down_locked" and side == "SELL":
            mult, reason = LIMIT_DOWN_CARRY_COST_MULTIPLIER, "carried_limit_down_exit_2x"
        elif carried.reason == "limit_up_locked" and side == "BUY":
            reason = "carried_limit_up_entry"
        else:
            reason = "carried"
    return Fill(price=float(session.official_close), session_date=session.session_date, flags=flags,
                cost_multiplier=mult, reason=reason, inav_residual_bp=residual, carried_from=carried_from,
                labels=labels)


simulated_fill = simulate_fill          # the section 3.5 name (spec L1087)


def snapshot_time_local(closing_call_start: time) -> time:
    """R-27 rule 1: the snapshot is one minute before the closing call opens (15:19 KST since 2016-08-01)."""
    stamp = datetime.combine(date(2000, 1, 3), closing_call_start) - timedelta(minutes=1)
    return stamp.time()


def fill_tracking_error(weights_snapshot, weights_close, returns) -> dict:
    """The printed snapshot-vs-close line (rule 1): te_ann = std(r_snap - r_close) x sqrt(252), mean |dw|."""
    ws, wc, r = (list(map(float, x)) for x in (weights_snapshot, weights_close, returns))
    if not (len(ws) == len(wc) == len(r)) or len(r) < 2:
        raise ValueError("weights and returns must be equal-length series of at least two points")
    diff = [a * x - b * x for a, b, x in zip(ws, wc, r)]
    mean = sum(diff) / len(diff)
    var = sum((d - mean) ** 2 for d in diff) / (len(diff) - 1)
    return {"te_ann": math.sqrt(var * 252.0), "mean_abs_dw": sum(abs(a - b) for a, b in zip(ws, wc)) / len(ws)}


# --------------------------------------------------------------------------- #
# Bar convention (R-27 rule 6; TASK-M5-11): bar_end stamps, the closing auction as its own bar, available_at =
# bar_end + latency, and a daily close NEVER derived from bars. `refuse_bar_close` is the only function that
# takes bars and asks for a close: it raises, always.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Bar:
    symbol: str
    bar_end_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    is_closing_auction: bool = False
    source: str = ""
    latency: Optional[timedelta] = None          # declared per source (F-20); None -> not usable at all

    def __post_init__(self) -> None:
        if self.bar_end_utc.tzinfo is None:
            raise ValueError("bar_end_utc must be tz-aware UTC")

    @property
    def available_at_utc(self) -> Optional[datetime]:
        return None if self.latency is None else self.bar_end_utc + self.latency


def refuse_bar_close(bars) -> None:
    """Raise BarDerivedClose for any bar input offered as a close source, whatever its last bar_end (L2925)."""
    bars = tuple(bars)
    last = max((b.bar_end_utc for b in bars), default=None)
    raise BarDerivedClose("a daily close is never derived from intraday bars (fill_model.bars.daily_close_from_bars: "
                          f"forbidden); {len(bars)} bars offered, last bar_end {last.isoformat() if last else None}")
