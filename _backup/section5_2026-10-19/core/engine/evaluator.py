"""Decide whether a rule fires, and record why when it does not (§3, §5).

The guard order is deliberate and is the safety design of the product:

    engine armed?  →  rule evaluable?  →  rule window open?  →  venue trading?
        →  data present and fresh?  →  conditions met?  →  caps clear?
        →  not a duplicate?  →  place

Cheap structural checks run before anything that touches a quote, and every
cap is checked *before* an order exists rather than after. A rejected order is
still written to the book with its reason, because §3 requires the operator to
be able to see why a rule did not act — an empty screen is the failure mode
this product is meant to eliminate.

Freshness is a halt condition, not a skip. §5 says "데이터가 없거나 오래된
경우 처리 중단": acting on a stale quote is worse than not acting, so the whole
engine halts rather than quietly passing over one rule.

One bounded exception: a quote that is merely *missing* for a reason that can
clear by itself. The runtime may pass `quote_grace` for the first few
misses of a symbol; the rule is then skipped, with the miss count
in the decision log, and the halt comes when the window runs out. No rule can
fire without a quote, so nothing is ever placed on missing data either way —
the exception only stops a three-second network hiccup from costing the rest
of the session. A *stale* quote gets no grace at all.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Optional

from core import markets
from core.engine.orders import (OrderBook, OrderStatus, SimulatedOrder,
                                order_id)
from core.engine.state import EngineState, HaltReason
from core.rules.model import (Comparator, EVALUABLE, OrderKind, Rule,
                              RuleStatus, SizeMode)


class Outcome(str, Enum):
    FIRED = "fired"
    SKIPPED = "skipped"           # legitimately not this rule's moment
    REJECTED = "rejected"         # conditions met but a guard stopped it
    HALTED = "halted"             # data problem; the engine was stopped
    BLOCKED = "blocked"           # v2 (M5): a new entry inside an R-10 window or the R-31 -12% step; nothing written


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: Decimal
    previous: Optional[Decimal]
    as_of: datetime
    source: str

    def age_seconds(self, *, now: Optional[datetime] = None) -> float:
        now = now or datetime.now(timezone.utc)
        stamp = self.as_of
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return (now - stamp).total_seconds()


@dataclass(frozen=True)
class Decision:
    rule_id: str
    rule_name: str
    outcome: Outcome
    reason: str
    at: datetime
    order: Optional[SimulatedOrder] = None
    quote_price: Optional[Decimal] = None

    @property
    def fired(self) -> bool:
        return self.outcome is Outcome.FIRED


def _met(condition, quote: Quote) -> bool:
    level = condition.level
    price = quote.price
    previous = quote.previous
    if condition.comparator is Comparator.AT_OR_BELOW:
        return price <= level
    if condition.comparator is Comparator.AT_OR_ABOVE:
        return price >= level
    # Crossing needs a prior observation; without one it has not crossed.
    if previous is None:
        return False
    if condition.comparator is Comparator.CROSSES_DOWN:
        return previous > level >= price
    if condition.comparator is Comparator.CROSSES_UP:
        return previous < level <= price
    return False


def conditions_met(rule: Rule, quote: Quote) -> tuple[bool, str]:
    """(met, human explanation). The explanation is shown either way."""
    if not rule.conditions:
        return False, "the rule has no condition"
    results = [(c, _met(c, quote)) for c in rule.conditions]
    if rule.require_all_conditions:
        unmet = [c for c, ok in results if not ok]
        if unmet:
            return False, "not met: " + "; ".join(c.describe() for c in unmet)
        return True, "all conditions met"
    if any(ok for _, ok in results):
        met = next(c for c, ok in results if ok)
        return True, f"met: {met.describe()}"
    return False, "no condition met: " + "; ".join(c.describe() for c, _ in results)


def _order_notional(rule: Rule, quote: Quote) -> tuple[Decimal, Decimal]:
    """(quantity, notional) for this trigger, from the operator's own size."""
    if rule.size_value is None:
        return Decimal(0), Decimal(0)
    reference = (rule.limit_price if rule.order_kind is OrderKind.LIMIT
                 and rule.limit_price is not None else quote.price)
    if rule.size_mode is SizeMode.QUANTITY:
        quantity = rule.size_value
        return quantity, quantity * reference
    if reference <= 0:
        return Decimal(0), Decimal(0)
    try:
        quantity = (rule.size_value / reference).to_integral_value(rounding="ROUND_DOWN")
    except (InvalidOperation, ZeroDivisionError):
        return Decimal(0), Decimal(0)
    return quantity, quantity * reference


class Evaluator:
    """Stateless apart from the collaborators handed to it."""

    def __init__(self, state: EngineState, book: OrderBook, *,
                 max_quote_age_s: float = 120.0):
        self.state = state
        self.book = book
        self.max_quote_age_s = max_quote_age_s

    def evaluate(self, rule: Rule, quote: Optional[Quote], *,
                 now: Optional[datetime] = None,
                 quote_error: str = "",
                 quote_grace: str = "") -> Decision:
        now = now or datetime.now(timezone.utc)

        def decide(outcome: Outcome, reason: str,
                   order: Optional[SimulatedOrder] = None) -> Decision:
            return Decision(rule.id, rule.name, outcome, reason, now, order,
                            quote.price if quote else None)

        # 1. engine armed
        if not self.state.is_armed:
            return decide(Outcome.SKIPPED,
                          f"engine is {self.state.mode.value}, not ARMED")

        # 2. rule evaluable
        if rule.status not in EVALUABLE:
            return decide(Outcome.SKIPPED, f"rule is {rule.status.value}")

        # 3. validity window
        if rule.valid_from and now < rule.valid_from:
            return decide(Outcome.SKIPPED,
                          f"window opens at {rule.valid_from.isoformat(timespec='seconds')}")
        if rule.valid_to and now > rule.valid_to:
            return decide(Outcome.SKIPPED, "validity window has closed")

        # 4. is the venue even trading? This precedes the missing-data check:
        #    a closed market has no fresh quote *by definition*, and halting on
        #    that is the overnight failure this ordering exists to prevent.
        market = markets.get(rule.market)
        if market is not None and market.session is not None:
            state, why = market.trading_state(now)
            if state != "open":
                return decide(Outcome.SKIPPED, f"{rule.market} is {state}: {why}")

        # 5. data present, and fresh for this venue right now
        if quote is None:
            detail = (f"no quote for {rule.symbol}"
                      + (f": {quote_error}" if quote_error else ""))
            if quote_grace:
                return decide(Outcome.SKIPPED,
                              f"{detail} — miss {quote_grace}, not evaluated; "
                              f"the engine halts if this continues")
            self.state.halt(HaltReason.NO_DATA, detail)
            return decide(Outcome.HALTED, detail)
        verdict, detail = self._freshness(rule, quote, now)
        if verdict is Outcome.HALTED:
            self.state.halt(HaltReason.STALE_DATA, detail)
            return decide(Outcome.HALTED, detail)
        if verdict is Outcome.SKIPPED:
            return decide(Outcome.SKIPPED, detail)

        # 6. the operator's own conditions
        met, explanation = conditions_met(rule, quote)
        if not met:
            return decide(Outcome.SKIPPED, explanation)

        # From here the rule wants to act, so every refusal is a REJECTED order
        # rather than a silent skip.
        sequence = rule.trigger_count + 1
        oid = order_id(rule.id, rule.revision, sequence)
        quantity, notional = _order_notional(rule, quote)

        candidate = SimulatedOrder(
            id=oid, rule_id=rule.id, rule_revision=rule.revision,
            rule_name=rule.name, symbol=rule.symbol, market=rule.market,
            side=rule.side, kind=rule.order_kind, quantity=quantity,
            limit_price=rule.limit_price, notional=notional,
            trigger_price=quote.price, created_at=now,
        )

        # 7. idempotency — cheap pre-check, so a duplicate does not even get
        #    written as a rejection. The authoritative guard is `place()`,
        #    which refuses a duplicate id atomically under the book's lock.
        if self.book.exists(oid):
            return decide(Outcome.SKIPPED,
                          f"trigger {sequence} already placed as {oid}")

        # 8. the operator's caps
        refusal = self._cap_refusal(rule, quantity, notional, now)
        if refusal:
            return decide(Outcome.REJECTED, refusal,
                          self.book.reject(candidate, refusal))

        placed = self.book.place(candidate)
        if placed is None:
            return decide(Outcome.SKIPPED,
                          f"trigger {sequence} already placed as {oid}")
        return decide(Outcome.FIRED, explanation, placed)

    def _freshness(self, rule: Rule, quote: Quote,
                   now: datetime) -> tuple[Optional[Outcome], str]:
        """Is this quote usable? Returns (None, "") when it is.

        Called only when the venue is open — `evaluate` skips a closed market
        before reaching here, because a single global age bound halted the
        engine every night: a US quote while New York is shut is hours old and
        entirely correct. Freshness only means something during a session.

            open, data from this session   -> apply the tight bound
            open, no print from today      -> skip (see below)
            older than the hard ceiling    -> halt regardless of the calendar

        Holidays no longer reach here: `evaluate` consults `core.calendars`
        first, so a public holiday is reported as closed by name. What remains
        in "open but nothing printed today" is an exchange outage, a trading
        suspension in that symbol, or our own feed being broken. This skips
        rather than halts, because a halt is global while the problem is one
        venue — a suspended US ticker must not stop Korean rules. Nothing
        executes either way, and the decision log records it. The hard ceiling
        below still catches a feed that is simply dead.
        """
        age = quote.age_seconds(now=now)
        market = markets.get(rule.market)
        session = market.session if market is not None else None

        if session is None:
            # No session defined for this venue: fall back to the global bound.
            if age > self.max_quote_age_s:
                return Outcome.HALTED, (
                    f"{rule.symbol} quote is {age:.0f}s old "
                    f"(limit {self.max_quote_age_s:.0f}s)")
            return None, ""

        if age > session.max_age_hard_s:
            return Outcome.HALTED, (
                f"{rule.symbol} quote is {age / 86400:.1f} days old — far past "
                f"anything the {rule.market} calendar explains")

        started = market.session_start(now)
        if started is not None and quote.as_of < started:
            # State the fact rather than guessing the cause. Calling this a
            # holiday would be a claim the program cannot support.
            local = quote.as_of.astimezone(session._zone())
            return Outcome.SKIPPED, (
                f"{rule.market} is open, but the newest {rule.symbol} price is "
                f"from {local:%Y-%m-%d %H:%M} {local.tzname()}, before today's "
                f"open. No trade has printed this session.")

        if age > session.max_age_open_s:
            return Outcome.HALTED, (
                f"{rule.market} is open but the {rule.symbol} quote is "
                f"{age:.0f}s old (limit {session.max_age_open_s:.0f}s)")

        return None, ""

    def _cap_refusal(self, rule: Rule, quantity: Decimal, notional: Decimal,
                     now: datetime) -> str:
        if quantity <= 0:
            return ("computed quantity is zero — the cash amount is smaller "
                    "than one share at the trigger price")
        limits = rule.limits
        if (limits.max_triggers is not None
                and rule.trigger_count >= limits.max_triggers):
            return (f"rule has already fired {rule.trigger_count} times "
                    f"(maximum {limits.max_triggers})")
        if (limits.max_order_amount is not None
                and notional > limits.max_order_amount):
            return (f"order amount {notional:,.0f} exceeds this rule's "
                    f"maximum {limits.max_order_amount:,.0f}")
        if limits.max_daily_amount is not None:
            already = self.book.notional_today(now=now)
            if already + notional > limits.max_daily_amount:
                return (f"order would take today's total to "
                        f"{already + notional:,.0f}, over the daily maximum "
                        f"{limits.max_daily_amount:,.0f}")
        return ""

    def sweep_cancellations(self, rules: dict[str, Rule], quotes: dict[str, Quote],
                            *, now: Optional[datetime] = None) -> list[Decision]:
        """Apply each rule's cancel condition to its still-open orders."""
        now = now or datetime.now(timezone.utc)
        out: list[Decision] = []
        for order in self.book.open_orders():
            rule = rules.get(order.rule_id)
            if rule is None or rule.cancel.empty:
                continue
            reason = ""
            if (rule.cancel.after_seconds is not None
                    and order.age_seconds >= rule.cancel.after_seconds):
                reason = f"unfilled for {rule.cancel.after_seconds}s"
            elif rule.cancel.if_price_beyond is not None:
                quote = quotes.get(order.symbol)
                if quote is not None and _met(rule.cancel.if_price_beyond, quote):
                    reason = f"cancel condition: {rule.cancel.if_price_beyond.describe()}"
            if reason:
                ok, _ = self.book.cancel(order.id, reason)
                if ok:
                    out.append(Decision(order.rule_id, order.rule_name,
                                        Outcome.SKIPPED, f"cancelled — {reason}",
                                        now, self.book.get(order.id)))
        return out


# --------------------------------------------------------------------------- #
# v2 hooks (M5; TASK-M5-06, M5-07; spec L1079-1080, L1183, R-08, R-10): module-level pure functions. The guard
# chain above is untouched; the operator engine never calls these. `evaluator_block` maps a would-act decision
# to BLOCKED for a NEW ENTRY only (rulings 3.6: BUY-side orders for operator rules; a decided target weight above
# the held weight for weight books); holds, decreases and exits are never blocked, and nothing is written to the
# book for a block. `evaluator_annotate` is R-08: an annotation plus a KIS spread-snapshot request record,
# changing no weight.
# --------------------------------------------------------------------------- #
BLOCK_RULES = ("R-10", "R-31")
BLOCKING_WINDOW_ACTIONS = ("evaluator_block_new_intraday_entries", "evaluator_block_new_futures_entries")


@dataclass(frozen=True)
class BlockState:
    """What the evaluator reads from `macro_state` / the event calendar at the decision instant.

    `windows`: the active event windows for the decision's market (`core.calendars.events.active_windows`);
    `block_new_entries`: `macro_state.flags.block_new_entries` of the book where the R-31 steps act;
    `is_new_entry`: the caller's statement (A-8); None derives it from the decision's order side (BUY) or from
    `w_held` / `w_target` when both are given.
    """
    windows: tuple[dict, ...] = ()
    block_new_entries: bool = False
    market: str = ""
    is_new_entry: Optional[bool] = None
    w_held: Optional[float] = None
    w_target: Optional[float] = None


def is_new_entry(side=None, *, w_held: Optional[float] = None, w_target: Optional[float] = None) -> bool:
    """Rulings 3.6: weight books -> target above held (decreases and exits never); operator rules -> BUY side."""
    if w_held is not None and w_target is not None:
        return float(w_target) > float(w_held)
    if side is None:
        return False
    value = getattr(side, "value", side)
    return str(value).upper() == "BUY"


def _new_entry(decision: Decision, state: BlockState) -> bool:
    if state.is_new_entry is not None:
        return bool(state.is_new_entry)
    if state.w_held is not None and state.w_target is not None:
        return is_new_entry(w_held=state.w_held, w_target=state.w_target)
    return is_new_entry(decision.order.side if decision.order is not None else None)


def _window_hit(window: dict, at: datetime) -> bool:
    start = datetime.fromisoformat(str(window["start_utc"]).replace("Z", "+00:00"))
    end = datetime.fromisoformat(str(window["end_utc"]).replace("Z", "+00:00"))
    stamp = at if at.tzinfo is not None else at.replace(tzinfo=timezone.utc)
    return start <= stamp < end


def evaluator_block(rule_id: str, decision: Decision, state: BlockState, *, log: Optional[list] = None) -> Decision:
    """BLOCKED(rule_id, reason) for a new-entry decision while an R-10 window (rule_id "R-10") or the -12% step
    (rule_id "R-31") is active; every other decision is returned unchanged. `reason` carries the macro rule id as
    its prefix because `Decision.rule_id` stays the operator rule's id. Every hit is appended to `log`."""
    if rule_id not in BLOCK_RULES:
        raise ValueError(f"evaluator_block: rule_id {rule_id!r} not in {BLOCK_RULES}")
    if decision.outcome is not Outcome.FIRED or not _new_entry(decision, state):
        return decision                                   # holds, decreases and exits are never blocked
    reason = ""
    if rule_id == "R-10":
        hits = [w for w in state.windows if w.get("action") in BLOCKING_WINDOW_ACTIONS
                and (not state.market or w.get("market") == state.market) and _window_hit(w, decision.at)]
        if hits:
            w = hits[0]
            reason = (f"R-10: {w.get('event_id', 'window')} {w.get('market', '')} {w['action']} "
                      f"{w['start_utc']}-{w['end_utc']}")
    elif state.block_new_entries:
        reason = "R-31: -12% step block_new_entries (specification book) — new entry blocked"
    if not reason:
        return decision
    blocked = Decision(decision.rule_id, decision.rule_name, Outcome.BLOCKED, reason, decision.at, None,
                       decision.quote_price)
    if log is not None:
        log.append({"kind": "evaluator_blocked", "macro_rule": rule_id, "rule_id": decision.rule_id,
                    "at": decision.at.isoformat(), "reason": reason})
    return blocked


def evaluator_annotate(rule_id: str, state, **kw):
    """R-08: `Annotation` from `core.ficc.annotations.annotate(...)`. `state` is a mapping with `vix`, `vix3m`,
    `input_date` (+ optional `lines`, `requested_utc`, `kis_verified`, `history`, `status`). No weight changes."""
    if rule_id != "R-08":
        raise ValueError(f"evaluator_annotate: only R-08 is an annotation rule, got {rule_id!r}")
    from core.ficc.annotations import annotate            # lazy: keeps the operator engine free of core.ficc
    get = state.get if hasattr(state, "get") else lambda k, d=None: getattr(state, k, d)
    args = {k: get(k) for k in ("lines", "requested_utc", "kis_verified", "history", "status", "budget_per_year")
            if get(k) is not None}
    args.update(kw)
    return annotate(get("vix"), get("vix3m"), get("input_date"), **args)
