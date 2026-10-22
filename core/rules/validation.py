"""Field-level rule validation (§2).

Returns every problem at once, each bound to the field that caused it, because
the requirement is "입력 중 필드별 오류 표시" — errors shown next to the field
— not a single message at the top of the form. A validator that stops at the
first failure cannot drive that UI.

Two categories, and the difference matters:

  * **Errors** block confirmation. Something required is missing or impossible.
  * **Warnings** do not block, but are surfaced in the preview. A rule that can
    never fire because its window has already closed is legal; the operator may
    be writing it for tomorrow. Silently arming it would be worse than saying so.

Nothing here suggests a value. A missing quantity produces "quantity is
required", never "try 10". That line is the product's core constraint.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Iterable

from core.rules.model import (Comparator, OrderKind, Rule, RuleStatus, Side,
                              SizeMode)


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Issue:
    field: str
    message: str
    severity: Severity = Severity.ERROR

    @property
    def blocking(self) -> bool:
        return self.severity is Severity.ERROR


@dataclass(frozen=True)
class Report:
    issues: tuple[Issue, ...] = ()

    @property
    def errors(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.severity is Severity.WARNING)

    @property
    def ok(self) -> bool:
        return not self.errors

    def for_field(self, name: str) -> tuple[Issue, ...]:
        return tuple(i for i in self.issues if i.field == name)

    def __bool__(self) -> bool:
        return self.ok


_MAX_CONDITIONS = 8


def validate(rule: Rule, *, now: datetime | None = None) -> Report:
    now = now or datetime.now(timezone.utc)
    issues: list[Issue] = []

    def error(field: str, message: str) -> None:
        issues.append(Issue(field, message, Severity.ERROR))

    def warn(field: str, message: str) -> None:
        issues.append(Issue(field, message, Severity.WARNING))

    # -- identity ------------------------------------------------------------
    if not rule.name.strip():
        error("name", "Give the rule a name so you can find it later.")
    if not rule.symbol.strip():
        error("symbol", "Enter the instrument code this rule applies to.")
    if not rule.market.strip():
        error("market", "Choose the market so quotes resolve to the right provider.")

    # -- the decision --------------------------------------------------------
    if rule.side is None:
        error("side", "Choose buy or sell.")

    if rule.size_mode is None:
        error("size_mode", "Choose whether the size is a share count or a cash amount.")
    if rule.size_value is None:
        error("size_value", "Enter the size. This program does not choose one for you.")
    elif rule.size_value <= 0:
        error("size_value", "Size must be greater than zero.")
    elif rule.size_mode is SizeMode.QUANTITY and rule.size_value != rule.size_value.to_integral_value():
        error("size_value", "A share count must be a whole number.")

    if rule.order_kind is None:
        error("order_kind", "Choose market or limit.")
    elif rule.order_kind is OrderKind.LIMIT:
        if rule.limit_price is None:
            error("limit_price", "A limit order needs a limit price.")
        elif rule.limit_price <= 0:
            error("limit_price", "Limit price must be greater than zero.")
    elif rule.order_kind is OrderKind.MARKET and rule.limit_price is not None:
        warn("limit_price", "Limit price is ignored for a market order.")

    # -- conditions ----------------------------------------------------------
    if not rule.conditions:
        error("conditions", "Add at least one trigger condition.")
    if len(rule.conditions) > _MAX_CONDITIONS:
        error("conditions", f"A rule may hold at most {_MAX_CONDITIONS} conditions.")
    for index, condition in enumerate(rule.conditions):
        if condition.level is None or condition.level <= 0:
            error(f"conditions[{index}]", "Condition price must be greater than zero.")
    issues.extend(_contradictions(rule))

    # -- window --------------------------------------------------------------
    if rule.valid_from and rule.valid_to and rule.valid_from >= rule.valid_to:
        error("valid_to", "The end of the window must come after its start.")
    if rule.valid_to and rule.valid_to <= now:
        warn("valid_to", "This window has already closed, so the rule cannot fire.")
    if rule.valid_from is None and rule.valid_to is None:
        warn("valid_from", "No validity window: this rule stays live until you stop it.")

    # -- limits --------------------------------------------------------------
    limits = rule.limits
    if limits.max_triggers is not None and limits.max_triggers <= 0:
        error("limits.max_triggers", "Maximum trigger count must be at least one.")
    if limits.max_order_amount is not None and limits.max_order_amount <= 0:
        error("limits.max_order_amount", "Maximum order amount must be greater than zero.")
    if limits.max_daily_amount is not None and limits.max_daily_amount <= 0:
        error("limits.max_daily_amount", "Maximum daily amount must be greater than zero.")
    if (limits.max_order_amount is not None and limits.max_daily_amount is not None
            and limits.max_order_amount > limits.max_daily_amount):
        error("limits.max_daily_amount",
              "The daily cap is below the per-order cap, so no order can pass both.")
    if limits.empty:
        warn("limits", "No caps set: this rule has no ceiling on how much it can order.")

    # A notional order whose size already exceeds its own per-order cap can
    # never pass the guard, so it is an error rather than a warning.
    if (rule.size_mode is SizeMode.NOTIONAL and rule.size_value is not None
            and limits.max_order_amount is not None
            and rule.size_value > limits.max_order_amount):
        error("size_value",
              "The order amount is above this rule's own maximum order amount.")

    # -- cancel condition ----------------------------------------------------
    if rule.cancel.after_seconds is not None and rule.cancel.after_seconds <= 0:
        error("cancel.after_seconds", "Cancel delay must be greater than zero seconds.")

    return Report(tuple(issues))


def _contradictions(rule: Rule) -> Iterable[Issue]:
    """Catch AND-ed conditions that cannot hold at the same time.

    Arming a rule that is arithmetically incapable of firing is a silent
    failure: it sits in the dashboard looking healthy forever. Only checked
    for AND, since OR conditions are meant to be mutually exclusive.
    """
    if not rule.require_all_conditions or len(rule.conditions) < 2:
        return ()
    ceilings = [c.level for c in rule.conditions
                if c.comparator in (Comparator.AT_OR_BELOW, Comparator.CROSSES_DOWN)]
    floors = [c.level for c in rule.conditions
              if c.comparator in (Comparator.AT_OR_ABOVE, Comparator.CROSSES_UP)]
    if ceilings and floors and min(ceilings) < max(floors):
        return (Issue(
            "conditions",
            f"These conditions cannot all be true: price must be at or below "
            f"{min(ceilings):,} and at or above {max(floors):,} at once.",
            Severity.ERROR,
        ),)
    return ()


def can_confirm(rule: Rule) -> Report:
    """Validation plus the state check §2 requires before arming."""
    report = validate(rule)
    if rule.status in (RuleStatus.CANCELLED, RuleStatus.EXPIRED):
        return Report(report.issues + (
            Issue("status", f"A {rule.status.value.lower()} rule cannot be confirmed."),
        ))
    return report
