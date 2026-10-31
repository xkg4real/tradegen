"""Pure, offline diagnostics for a proposed marked-equity policy.

This research preview reads no account, file, clock, or network and produces no
order, permit, signature, or owner-log entry. A diagnostic without blocking
reasons is NOT permission to trade. It does not size positions or predict profit.

The floor is a marked-equity monitoring threshold, not the existing odds
engine's ``floor_safe`` cash reserve. Equality is not a floor breach. Neither
monitoring nor an eventual liquidation request guarantees a real-market floor.
The caller must independently establish approved inputs, complete accounting,
and any future reviewed integration. No missing approval or loss budget is
invented here, and a lower proposed floor never relaxes the supplied floor.
"""

from dataclasses import dataclass
from decimal import Decimal, DecimalException, Inexact, localcontext


@dataclass(frozen=True, kw_only=True)
class Policy:
    initial_equity: Decimal
    drawdown_activation_equity: Decimal
    positive_profit_loss_fraction: Decimal
    peak_drawdown_fraction: Decimal
    zero_profit_day_target_fraction: Decimal


@dataclass(frozen=True, kw_only=True)
class Observation:
    equity: Decimal
    prior_high_watermark: Decimal
    day_start_equity: Decimal
    current_day_realized_net_profit: Decimal
    prior_day_realized_net_profit: Decimal | None
    is_first_trading_day: bool
    approved_effective_floor: Decimal | None
    first_or_zero_day_loss_budget: Decimal | None
    observed_daily_loss: Decimal
    data_complete: bool = True
    external_flows_known: bool = True


@dataclass(frozen=True, kw_only=True)
class Diagnostic:
    """A research result, never an entry or exit permit.

    ``exits_allowed`` only says this policy does not impose an exit prohibition;
    it cannot override conduct rules, corrupt state, or execution authorization.
    """

    new_entry_blocked: bool
    reasons: tuple[str, ...]
    high_watermark: Decimal | None = None
    calculated_floor: Decimal | None = None
    effective_floor: Decimal | None = None
    relaxation_pending: bool = False
    daily_loss_budget: Decimal | None = None
    daily_profit_target: Decimal | None = None
    daily_profit_target_met: bool | None = None
    exits_allowed: bool = True


def _finite_decimal(value: object) -> bool:
    return type(value) is Decimal and value.is_finite()


def _invalid_fields(policy: Policy, observation: Observation) -> tuple[str, ...]:
    reasons = []
    for name in Policy.__dataclass_fields__:
        if not _finite_decimal(getattr(policy, name)):
            reasons.append("INVALID_POLICY_" + name.upper())
    optional = {"prior_day_realized_net_profit", "approved_effective_floor",
                "first_or_zero_day_loss_budget"}
    flags = {"is_first_trading_day", "data_complete", "external_flows_known"}
    for name in Observation.__dataclass_fields__:
        value = getattr(observation, name)
        valid = (type(value) is bool if name in flags else
                 value is None if name in optional and value is None else
                 _finite_decimal(value))
        if not valid:
            reasons.append("INVALID_OBSERVATION_" + name.upper())
    if reasons:
        return tuple(reasons)
    if policy.initial_equity <= 0:
        reasons.append("INITIAL_EQUITY_NOT_POSITIVE")
    if policy.drawdown_activation_equity < policy.initial_equity:
        reasons.append("ACTIVATION_BELOW_INITIAL_EQUITY")
    if not 0 <= policy.positive_profit_loss_fraction <= 1:
        reasons.append("INVALID_POLICY_POSITIVE_PROFIT_LOSS_FRACTION")
    if not 0 <= policy.peak_drawdown_fraction < 1:
        reasons.append("INVALID_POLICY_PEAK_DRAWDOWN_FRACTION")
    if policy.zero_profit_day_target_fraction < 0:
        reasons.append("NEGATIVE_PROFIT_TARGET_FRACTION")
    if observation.day_start_equity <= 0:
        reasons.append("DAY_START_EQUITY_NOT_POSITIVE")
    if observation.prior_high_watermark < policy.initial_equity:
        reasons.append("HIGH_WATERMARK_BELOW_INITIAL_EQUITY")
    if observation.prior_high_watermark < observation.day_start_equity:
        reasons.append("HIGH_WATERMARK_BELOW_DAY_START_EQUITY")
    for name in ("equity", "observed_daily_loss", "approved_effective_floor",
                 "first_or_zero_day_loss_budget"):
        value = getattr(observation, name)
        if value is not None and value < 0:
            reasons.append("NEGATIVE_OBSERVATION_" + name.upper())
    if not observation.data_complete:
        reasons.append("INCOMPLETE_ACCOUNTING_DATA")
    if not observation.external_flows_known:
        reasons.append("EXTERNAL_FLOWS_UNKNOWN")
    return tuple(reasons)


def evaluate(policy: Policy, observation: Observation) -> Diagnostic:
    """Return diagnostics from supplied Decimal values, without any side effects.

    ``observed_daily_loss`` is an externally established loss measure; it is
    deliberately not inferred from realized profit, unrealized profit, or equity.
    External flows must be reconciled by the caller before this function is used.
    The loss budget is exhausted at equality; the equity floor is breached only
    strictly below it. Profit targets are retrospective diagnostics and never
    change the budget or, by themselves, block entry.

    A known previous-day result takes precedence over the first-day flag. Missing
    previous-day history is distinct from a known zero result. A first-day flag
    waives neither a known previous loss nor the equity floor. An explicit budget
    is consumed only for the first day with missing history or a known zero day.

    Exact Decimal arithmetic is required; arithmetic overflow or inexact results
    produce a blocked diagnostic instead of rounded authorization-like output.
    """
    if type(policy) is not Policy or type(observation) is not Observation:
        return Diagnostic(new_entry_blocked=True, reasons=("INVALID_ARGUMENT_TYPE",))
    invalid = _invalid_fields(policy, observation)
    if invalid:
        return Diagnostic(new_entry_blocked=True, reasons=invalid)
    try:
        with localcontext() as context:
            context.prec = max(64, sum(len(value.as_tuple().digits)
                               for obj in (policy, observation)
                               for value in vars(obj).values() if type(value) is Decimal) + 16)
            context.traps[Inexact] = True
            return _evaluate_exact(policy, observation)
    except (DecimalException, OverflowError, ValueError):
        return Diagnostic(new_entry_blocked=True, reasons=("ARITHMETIC_NOT_EXACT_OR_FINITE",))


def _evaluate_exact(policy: Policy, observation: Observation) -> Diagnostic:
    reasons = []
    high = max(observation.prior_high_watermark, observation.equity)
    proposed = (high if high < policy.drawdown_activation_equity else
                max(policy.initial_equity, (Decimal(1) - policy.peak_drawdown_fraction) * high))
    prior_floor = observation.approved_effective_floor
    pending = prior_floor is not None and proposed < prior_floor
    if prior_floor is None:
        effective = None
        reasons.append("EFFECTIVE_FLOOR_UNCONFIGURED")
    else:
        effective = max(prior_floor, proposed)
        if observation.equity < effective:
            reasons.append("EQUITY_BELOW_EFFECTIVE_FLOOR")

    previous = observation.prior_day_realized_net_profit
    target = None
    target_met = None
    if previous is None:
        if observation.is_first_trading_day:
            budget = observation.first_or_zero_day_loss_budget
            if budget is None:
                reasons.append("FIRST_DAY_LOSS_BUDGET_UNCONFIGURED")
        else:
            budget = None
            reasons.append("PREVIOUS_DAY_RESULT_MISSING")
    elif previous < 0:
        budget = Decimal(0)
        reasons.append("PREVIOUS_DAY_LOSS")
    elif previous > 0:
        budget = policy.positive_profit_loss_fraction * previous
    else:
        budget = observation.first_or_zero_day_loss_budget
        target = policy.zero_profit_day_target_fraction * observation.day_start_equity
        target_met = observation.current_day_realized_net_profit >= target
        if budget is None:
            reasons.append("ZERO_PROFIT_DAY_LOSS_BUDGET_UNCONFIGURED")
    if budget is not None and observation.observed_daily_loss >= budget:
        reasons.append("DAILY_LOSS_BUDGET_REACHED")

    return Diagnostic(
        new_entry_blocked=bool(reasons), reasons=tuple(reasons), high_watermark=high,
        calculated_floor=proposed, effective_floor=effective, relaxation_pending=pending,
        daily_loss_budget=budget, daily_profit_target=target, daily_profit_target_met=target_met,
    )
