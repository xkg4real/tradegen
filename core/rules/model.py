"""The user-authored rule — the thing this whole product exists to execute.

The service contract is specific about where the logic comes from: the operator
supplies every condition, quantity, price and limit, and the program never
proposes one. That constraint shapes this module in two visible ways.

  * **No defaults with financial meaning.** A rule is constructed with every
    decision field empty. There is no default side, no default quantity, no
    suggested price offset, no standard validity window. A blank field stays
    blank and fails validation; it is never quietly filled in, because a filled
    default is a recommendation wearing a different hat.

  * **Conditions are declarative data, not code.** A rule says "trigger when
    last price is at or below 68000", as a `PriceCondition` the operator built
    from a fixed vocabulary. Nothing here evaluates an expression the operator
    typed, so there is no path by which the program authors part of the rule.

`Rule` is immutable. Editing produces a new revision, which is what makes the
edit history in §7 and the re-confirmation requirement in §2 implementable —
you cannot compare "before and after" if the object mutates in place.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class Comparator(str, Enum):
    """The fixed vocabulary of price comparisons an operator may choose from."""
    AT_OR_BELOW = "AT_OR_BELOW"
    AT_OR_ABOVE = "AT_OR_ABOVE"
    CROSSES_DOWN = "CROSSES_DOWN"      # previous > level and current <= level
    CROSSES_UP = "CROSSES_UP"          # previous < level and current >= level


class SizeMode(str, Enum):
    QUANTITY = "QUANTITY"              # a share count
    NOTIONAL = "NOTIONAL"              # a cash amount, converted at trigger time


class OrderKind(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class RuleStatus(str, Enum):
    DRAFT = "DRAFT"            # being written; never evaluated
    CONFIRMED = "CONFIRMED"    # operator reviewed the summary; may be armed
    ACTIVE = "ACTIVE"          # armed and evaluating
    PAUSED = "PAUSED"          # armed engine, but this rule is held
    EXHAUSTED = "EXHAUSTED"    # hit max_triggers
    EXPIRED = "EXPIRED"        # past valid_to
    CANCELLED = "CANCELLED"    # operator withdrew it


# Statuses from which the engine may fire a rule.
EVALUABLE = frozenset({RuleStatus.ACTIVE})


@dataclass(frozen=True)
class PriceCondition:
    """One comparison against a quoted price. `level` is operator-supplied."""
    comparator: Comparator
    level: Decimal

    def describe(self) -> str:
        words = {
            Comparator.AT_OR_BELOW: "last price is at or below",
            Comparator.AT_OR_ABOVE: "last price is at or above",
            Comparator.CROSSES_DOWN: "last price crosses down through",
            Comparator.CROSSES_UP: "last price crosses up through",
        }
        return f"{words[self.comparator]} {self.level:,}"


@dataclass(frozen=True)
class CancelCondition:
    """Withdraws a still-open simulated order. Optional; blank means never."""
    after_seconds: Optional[int] = None
    if_price_beyond: Optional[PriceCondition] = None

    @property
    def empty(self) -> bool:
        return self.after_seconds is None and self.if_price_beyond is None

    def describe(self) -> str:
        parts = []
        if self.after_seconds is not None:
            parts.append(f"unfilled after {self.after_seconds}s")
        if self.if_price_beyond is not None:
            parts.append(self.if_price_beyond.describe())
        return " or ".join(parts) if parts else "never"


@dataclass(frozen=True)
class Limits:
    """§5 safety caps. Every field is operator-supplied; none has a default."""
    max_triggers: Optional[int] = None          # lifetime firings for this rule
    max_order_amount: Optional[Decimal] = None  # per-order notional ceiling
    max_daily_amount: Optional[Decimal] = None  # per-day notional ceiling

    @property
    def empty(self) -> bool:
        return (self.max_triggers is None and self.max_order_amount is None
                and self.max_daily_amount is None)


@dataclass(frozen=True)
class Rule:
    """One executable instruction, exactly as the operator wrote it."""
    # identity
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    revision: int = 1
    name: str = ""

    # instrument and market
    symbol: str = ""
    market: str = ""                      # KRX | US | ... routes the quote lookup

    # the decision — all blank until the operator fills them
    side: Optional[Side] = None
    size_mode: Optional[SizeMode] = None
    size_value: Optional[Decimal] = None
    order_kind: Optional[OrderKind] = None
    limit_price: Optional[Decimal] = None
    conditions: tuple[PriceCondition, ...] = ()
    require_all_conditions: bool = True    # AND when true, OR when false

    # window and caps
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    limits: Limits = field(default_factory=Limits)
    cancel: CancelCondition = field(default_factory=CancelCondition)

    # bookkeeping
    status: RuleStatus = RuleStatus.DRAFT
    trigger_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    notes: str = ""

    # -- revisions -----------------------------------------------------------
    def edit(self, **changes) -> "Rule":
        """Produce the next revision.

        Any change to a decision field drops the rule back to DRAFT and clears
        the confirmation, which is §2's "주요 조건 변경 시 기존 확인 취소 후
        재확인". Renaming or annotating does not, because re-confirming a
        typo fix trains the operator to click through confirmations.
        """
        decision_fields = {
            "symbol", "market", "side", "size_mode", "size_value", "order_kind",
            "limit_price", "conditions", "require_all_conditions",
            "valid_from", "valid_to", "limits", "cancel",
        }
        touched_decision = any(
            key in decision_fields and changes[key] != getattr(self, key)
            for key in changes
        )
        base = dict(changes)
        base["revision"] = self.revision + 1
        base["updated_at"] = datetime.now(timezone.utc)
        if touched_decision:
            base["status"] = RuleStatus.DRAFT
            base["confirmed_at"] = None
        return replace(self, **base)

    def confirm(self) -> "Rule":
        return replace(self, status=RuleStatus.CONFIRMED,
                       confirmed_at=datetime.now(timezone.utc),
                       updated_at=datetime.now(timezone.utc))

    def activate(self) -> "Rule":
        return replace(self, status=RuleStatus.ACTIVE,
                       updated_at=datetime.now(timezone.utc))

    def with_status(self, status: RuleStatus) -> "Rule":
        return replace(self, status=status, updated_at=datetime.now(timezone.utc))

    def record_trigger(self) -> "Rule":
        count = self.trigger_count + 1
        exhausted = (self.limits.max_triggers is not None
                     and count >= self.limits.max_triggers)
        return replace(
            self, trigger_count=count,
            status=RuleStatus.EXHAUSTED if exhausted else self.status,
            updated_at=datetime.now(timezone.utc),
        )

    # -- presentation --------------------------------------------------------
    def summary(self) -> str:
        """The one-line preview shown before confirmation (§2).

        Reads back exactly what was entered, with no rounding and no
        interpretation, so the operator is checking their own words. Unset
        parts render as bracketed gaps rather than being omitted — a sentence
        that silently skips the missing quantity reads as complete.
        """
        symbol = self.symbol or "(no instrument)"

        if not self.conditions:
            condition = "(no condition set)"
        else:
            joiner = " and " if self.require_all_conditions else " or "
            condition = joiner.join(c.describe() for c in self.conditions)

        side = self.side.value if self.side else "(direction not set)"

        if self.size_value is None or self.size_mode is None:
            size = "(size not set)"
        elif self.size_mode is SizeMode.QUANTITY:
            size = f"{self.size_value:,} shares"
        else:
            size = f"{self.size_value:,} worth"

        if self.order_kind is OrderKind.MARKET:
            kind = "a market order"
        elif self.order_kind is OrderKind.LIMIT:
            kind = (f"a limit order at {self.limit_price:,}"
                    if self.limit_price is not None
                    else "a limit order at (no limit price)")
        else:
            kind = "(order type not set)"

        return (f"On {symbol}: when {condition}, "
                f"place {kind} to {side} {size}.")

    @property
    def is_confirmed(self) -> bool:
        return self.status in (RuleStatus.CONFIRMED, RuleStatus.ACTIVE,
                               RuleStatus.PAUSED)
