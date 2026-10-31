"""Pure risk diagnostics and FIFO fill accounting; never an execution permit.

The caller supplies reconciled account data, the policy and aware instants. This
module performs no I/O, credential access, clock read or transport operation.
FIFO costs include acquisition fees; partial allocations round down at 18 KRW
decimal places and the final consumption receives the entire remaining cost.
This is an accounting convention, not a tax calculation or a floor guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Context, Decimal, DecimalException, Inexact, ROUND_DOWN, ROUND_HALF_EVEN, localcontext
import re
from zoneinfo import ZoneInfo

_ZERO = Decimal(0)
_ONE = Decimal(1)
_COST_QUANTUM = Decimal("1e-18")
_SEOUL = ZoneInfo("Asia/Seoul")
_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
_CURRENCY = re.compile(r"[A-Z][A-Z0-9]{0,11}")
_ORDER_DATE = re.compile(r"[0-9]{8}")
_BROKER_ID = re.compile(r"[0-9]{1,20}")


@dataclass(frozen=True, kw_only=True)
class RiskPolicy:
    version: str
    initial_equity: Decimal
    drawdown_activation_equity: Decimal
    positive_profit_loss_fraction: Decimal
    peak_drawdown_fraction: Decimal
    zero_profit_day_target_fraction: Decimal
    first_day_loss_budget: Decimal | None = None
    zero_profit_day_loss_budget: Decimal | None = None
    valuation_convention: str = "marked_equity"
    daily_loss_convention: str = "externally_reconciled"


@dataclass(frozen=True, kw_only=True)
class RiskObservation:
    equity: Decimal
    prior_high_watermark: Decimal
    day_start_equity: Decimal
    current_day_realized_net_profit: Decimal
    prior_day_realized_net_profit: Decimal | None
    observed_daily_loss: Decimal
    approved_effective_floor: Decimal | None
    is_first_trading_day: bool
    asof: datetime
    data_complete: bool = True
    external_flows_known: bool = True
    legacy_floor_conflict: bool = False
    halted: bool = False


@dataclass(frozen=True, kw_only=True)
class RiskResult:
    new_entry_blocked: bool
    reasons: tuple[str, ...]
    high_watermark: Decimal | None = None
    calculated_floor: Decimal | None = None
    effective_floor: Decimal | None = None
    relaxation_pending: bool = False
    daily_loss_budget: Decimal | None = None
    daily_profit_target: Decimal | None = None
    daily_profit_target_met: bool | None = None
    protective_action_needed: bool = False
    exits_allowed: bool = True  # No risk-policy veto; all execution/conduct checks still apply.


@dataclass(frozen=True, kw_only=True)
class Fill:
    venue: str
    account_scope: str
    order_id: str
    fill_id: str
    market: str
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    quote_currency: str
    quote_krw: Decimal | None
    fee_amount: Decimal | None
    fee_currency: str | None
    executed_at: datetime
    base_currency: str = ""
    order_date: str = ""  # KIS venue-local YYYYMMDD from authoritative records; empty for crypto.
    broker_org_id: str = ""  # KRX original broker org; US may authoritatively omit it; empty for crypto.


@dataclass(frozen=True, kw_only=True)
class AccountingResult:
    ok: bool
    reasons: tuple[str, ...]
    realized_net_profit_krw: Decimal | None = None
    inventory: tuple[tuple[str, str, str, str, Decimal, Decimal], ...] = ()
    cash_deltas_by_account_krw: tuple[tuple[str, str, Decimal], ...] = ()
    cash_deltas_by_currency: tuple[tuple[str, str, str, Decimal], ...] = ()
    order_quantities: tuple[tuple[str, str, str, str, str, str, Decimal], ...] = ()
    realized_by_account_day_krw: tuple[tuple[str, str, date, Decimal], ...] = ()
    accepted_fills: tuple[Fill, ...] = ()
    duplicate_count: int = 0


def _decimal(value: object) -> bool:
    return type(value) is Decimal and value.is_finite()


def _stamp(value: object) -> bool:
    if type(value) is not datetime:
        return False
    try:
        return value.tzinfo is not None and value.utcoffset() is not None
    except (TypeError, ValueError, OverflowError):
        return False


def _identifier(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _context() -> Context:
    ctx = Context(prec=80, rounding=ROUND_HALF_EVEN)
    ctx.traps[Inexact] = True
    return ctx


def _risk_errors(policy: RiskPolicy, observation: RiskObservation) -> tuple[str, ...]:
    reasons = []
    for name in ("version", "valuation_convention", "daily_loss_convention"):
        if not _identifier(getattr(policy, name)):
            reasons.append("INVALID_POLICY_" + name.upper())
    for name in ("initial_equity", "drawdown_activation_equity", "positive_profit_loss_fraction",
                 "peak_drawdown_fraction", "zero_profit_day_target_fraction"):
        if not _decimal(getattr(policy, name)):
            reasons.append("INVALID_POLICY_" + name.upper())
    for name in ("first_day_loss_budget", "zero_profit_day_loss_budget"):
        value = getattr(policy, name)
        if value is not None and (not _decimal(value) or value < 0):
            reasons.append("INVALID_POLICY_" + name.upper())
    for name in ("equity", "prior_high_watermark", "day_start_equity",
                 "current_day_realized_net_profit", "observed_daily_loss"):
        if not _decimal(getattr(observation, name)):
            reasons.append("INVALID_OBSERVATION_" + name.upper())
    for name in ("prior_day_realized_net_profit", "approved_effective_floor"):
        value = getattr(observation, name)
        if value is not None and not _decimal(value):
            reasons.append("INVALID_OBSERVATION_" + name.upper())
    for name in ("is_first_trading_day", "data_complete", "external_flows_known",
                 "legacy_floor_conflict", "halted"):
        if type(getattr(observation, name)) is not bool:
            reasons.append("INVALID_OBSERVATION_" + name.upper())
    if not _stamp(observation.asof):
        reasons.append("INVALID_OBSERVATION_ASOF")
    if reasons:
        return tuple(reasons)
    if policy.initial_equity <= 0 or policy.drawdown_activation_equity < policy.initial_equity:
        reasons.append("INVALID_PRINCIPAL_OR_ACTIVATION")
    if not 0 <= policy.positive_profit_loss_fraction <= 1:
        reasons.append("INVALID_PROFIT_LOSS_FRACTION")
    if not 0 <= policy.peak_drawdown_fraction < 1:
        reasons.append("INVALID_PEAK_DRAWDOWN_FRACTION")
    if policy.zero_profit_day_target_fraction < 0:
        reasons.append("INVALID_TARGET_FRACTION")
    if observation.day_start_equity <= 0 or observation.observed_daily_loss < 0:
        reasons.append("INVALID_DAY_START_OR_LOSS")
    if observation.prior_high_watermark < max(policy.initial_equity, observation.day_start_equity):
        reasons.append("INCONSISTENT_HIGH_WATERMARK")
    if observation.approved_effective_floor is not None and observation.approved_effective_floor < 0:
        reasons.append("INVALID_EFFECTIVE_FLOOR")
    return tuple(reasons)


def evaluate(policy: RiskPolicy, observation: RiskObservation) -> RiskResult:
    """Evaluate supplied aggregates; equality alone is not a monitor breach.

    Persistent first-session/day/peak state, input freshness and any D12 approval
    are established by the controller. This function never lowers a supplied
    effective floor. The externally chosen daily-loss measure is not inferred
    from a profit target or a marked value. Invalid input yields no eligibility.
    """
    if type(policy) is not RiskPolicy or type(observation) is not RiskObservation:
        return RiskResult(new_entry_blocked=True, reasons=("INVALID_ARGUMENT_TYPE",))
    errors = _risk_errors(policy, observation)
    if errors:
        return RiskResult(new_entry_blocked=True, reasons=errors)
    try:
        with localcontext(_context()):
            return _evaluate(policy, observation)
    except (DecimalException, ValueError, OverflowError):
        return RiskResult(new_entry_blocked=True, reasons=("ARITHMETIC_NOT_EXACT_OR_FINITE",))


def _evaluate(policy: RiskPolicy, observation: RiskObservation) -> RiskResult:
    reasons = []
    high = max(observation.prior_high_watermark, observation.equity)
    requested = (high if high < policy.drawdown_activation_equity else
                 max(policy.initial_equity, (_ONE - policy.peak_drawdown_fraction) * high))
    prior_floor = observation.approved_effective_floor
    effective = max(prior_floor, requested) if prior_floor is not None else None
    pending = prior_floor is not None and requested < prior_floor
    breach = effective is not None and observation.equity < effective
    if effective is None:
        reasons.append("EFFECTIVE_FLOOR_UNCONFIGURED")
    if breach:
        reasons.append("EQUITY_BELOW_EFFECTIVE_FLOOR")
    for name, reason in (("data_complete", "INCOMPLETE_ACCOUNTING_DATA"),
                         ("external_flows_known", "EXTERNAL_FLOWS_UNKNOWN")):
        if not getattr(observation, name):
            reasons.append(reason)
    if observation.legacy_floor_conflict:
        reasons.append("LEGACY_FLOOR_POLICY_CONFLICT")
    if observation.halted:
        reasons.append("PERSISTENT_HALT")
    previous = observation.prior_day_realized_net_profit
    budget = target = target_met = None
    if previous is None:
        if observation.is_first_trading_day:
            budget = policy.first_day_loss_budget
            if budget is None:
                reasons.append("FIRST_DAY_LOSS_BUDGET_UNCONFIGURED")
        else:
            reasons.append("PREVIOUS_DAY_RESULT_MISSING")
    elif previous < 0:
        budget = _ZERO
        reasons.append("PREVIOUS_DAY_LOSS")
    elif previous > 0:
        budget = policy.positive_profit_loss_fraction * previous
    else:
        budget = policy.zero_profit_day_loss_budget
        target = policy.zero_profit_day_target_fraction * observation.day_start_equity
        target_met = observation.current_day_realized_net_profit >= target
        if budget is None:
            reasons.append("ZERO_PROFIT_DAY_LOSS_BUDGET_UNCONFIGURED")
    exhausted = budget is not None and observation.observed_daily_loss >= budget
    if exhausted:
        reasons.append("DAILY_LOSS_BUDGET_REACHED")
    return RiskResult(new_entry_blocked=bool(reasons), reasons=tuple(reasons), high_watermark=high,
                      calculated_floor=requested, effective_floor=effective, relaxation_pending=pending,
                      daily_loss_budget=budget, daily_profit_target=target, daily_profit_target_met=target_met,
                      protective_action_needed=breach or exhausted or observation.halted)


def _fill_error(fill: Fill) -> str | None:
    if type(fill) is not Fill:
        return "INVALID_FILL_TYPE"
    if fill.venue not in ("kis", "upbit", "okx"):
        return "INVALID_FILL_VENUE"
    for name in ("account_scope", "order_id", "fill_id", "market", "symbol"):
        if not _identifier(getattr(fill, name)):
            return "INVALID_FILL_" + name.upper()
    if fill.venue == "kis":
        if fill.market not in ("krx", "nasd", "nyse", "amex"):
            return "INVALID_KIS_FILL_MARKET"
        if type(fill.order_date) is not str or not _ORDER_DATE.fullmatch(fill.order_date):
            return "MISSING_OR_INVALID_KIS_ORDER_DATE"
        try:
            date(int(fill.order_date[:4]), int(fill.order_date[4:6]), int(fill.order_date[6:]))
        except ValueError:
            return "MISSING_OR_INVALID_KIS_ORDER_DATE"
        if not _BROKER_ID.fullmatch(fill.order_id):
            return "INVALID_KIS_ORDER_ID"
        if type(fill.broker_org_id) is not str or (fill.broker_org_id and not _BROKER_ID.fullmatch(fill.broker_org_id)):
            return "INVALID_KIS_BROKER_ORG_ID"
        if fill.market == "krx" and not fill.broker_org_id:
            return "MISSING_KIS_BROKER_ORG_ID"
    elif type(fill.order_date) is not str or fill.order_date != "":
        return "UNEXPECTED_CRYPTO_ORDER_DATE"
    elif type(fill.broker_org_id) is not str or fill.broker_org_id != "":
        return "UNEXPECTED_CRYPTO_BROKER_ORG_ID"
    if fill.side not in ("buy", "sell") or type(fill.side) is not str:
        return "INVALID_FILL_SIDE"
    if not _stamp(fill.executed_at):
        return "INVALID_FILL_TIME"
    if type(fill.quote_currency) is not str or not _CURRENCY.fullmatch(fill.quote_currency):
        return "INVALID_QUOTE_CURRENCY"
    if type(fill.base_currency) is not str or (fill.base_currency and not _CURRENCY.fullmatch(fill.base_currency)):
        return "INVALID_BASE_CURRENCY"
    if fill.base_currency == fill.quote_currency:
        return "AMBIGUOUS_FILL_CURRENCY"
    for name in ("quantity", "price", "quote_krw"):
        value = getattr(fill, name)
        if not _decimal(value) or value <= 0:
            return "MISSING_OR_INVALID_" + name.upper()
    if fill.quote_currency == "KRW" and fill.quote_krw != _ONE:
        return "INCONSISTENT_KRW_RATE"
    if not _decimal(fill.fee_amount) or fill.fee_amount < 0:
        return "MISSING_OR_INVALID_FEE"
    if type(fill.fee_currency) is not str or not _CURRENCY.fullmatch(fill.fee_currency):
        return "MISSING_OR_INVALID_FEE_CURRENCY"
    if fill.fee_currency not in (fill.quote_currency, fill.base_currency, "KRW"):
        return "UNSUPPORTED_FEE_CURRENCY"
    if fill.side == "buy" and fill.fee_currency == fill.base_currency and fill.fee_amount >= fill.quantity:
        return "BASE_FEE_EXHAUSTS_BUY_QUANTITY"
    return None


def _allocate_cost(cost: Decimal, taken: Decimal, quantity: Decimal) -> Decimal:
    if taken == quantity:
        return cost
    with localcontext(_context()) as ctx:
        ctx.traps[Inexact] = False
        allocated = (cost * taken / quantity).quantize(_COST_QUANTUM, rounding=ROUND_DOWN)
    if not allocated.is_finite() or allocated < 0 or allocated > cost:
        raise ValueError("invalid allocated cost")
    return allocated


def _order_identity(fill: Fill) -> tuple[str, ...]:
    # KIS raw numbers may repeat across dates or markets. Crypto identity never
    # gains a caller-chosen date or market component that could hide duplicates.
    if fill.venue == "kis":
        return fill.venue, fill.account_scope, fill.market, fill.order_date, fill.broker_org_id, fill.order_id
    return fill.venue, fill.account_scope, fill.order_id


def account_fills(fills: tuple[Fill, ...]) -> AccountingResult:
    """Rebuild cash movements, FIFO inventory and realized P&L from full history.

    No opening balance is guessed, and an empty tuple is not evidence that the
    caller has complete account history. KIS raw ``order_id`` is scoped by venue,
    account, market, original broker org and authoritative venue-local ``order_date``. That date is
    never guessed from execution UTC; crypto requires empty date/org and retains
    venue/account/order identity. Identical duplicates are idempotent,
    contradictory ones refuse.
    Chronological sorting is deterministic; at equal instants the caller's
    reconciled event sequence is retained. Quote/base/KRW fees are supported;
    fees in another token need explicit reconciliation and are refused.

    Cash deltas are historical movements, not current settled balances, and must
    not be applied twice to an already reconciled broker snapshot. Fees paid in
    the base asset reduce units, never fictitiously reduce quote cash. Acquisition
    cost includes them through the reduced received inventory. Selling a base
    fee consumes additional FIFO units. All results are account/venue scoped.
    """
    if type(fills) is not tuple:
        return AccountingResult(ok=False, reasons=("INVALID_FILL_COLLECTION",))
    seen = {}
    unique = []
    duplicates = 0
    order_shapes = {}
    for fill in fills:
        error = _fill_error(fill)
        if error:
            return AccountingResult(ok=False, reasons=(error,))
        order_key = _order_identity(fill)
        key = (*order_key, fill.fill_id)
        if key in seen:
            if seen[key] != fill:
                return AccountingResult(ok=False, reasons=("CONTRADICTORY_DUPLICATE_FILL",))
            duplicates += 1
            continue
        shape = (fill.market, fill.symbol, fill.side, fill.quote_currency, fill.base_currency)
        if order_key in order_shapes and order_shapes[order_key] != shape:
            return AccountingResult(ok=False, reasons=("INCONSISTENT_ORDER_FILL_IDENTITY",))
        order_shapes[order_key] = shape
        seen[key] = fill
        unique.append(fill)
    try:
        unique.sort(key=lambda f: f.executed_at.astimezone(timezone.utc))
        with localcontext(_context()):
            return _account(tuple(unique), duplicates)
    except (DecimalException, ValueError, OverflowError):
        return AccountingResult(ok=False, reasons=("ACCOUNTING_ARITHMETIC_NOT_EXACT_OR_FINITE",))


def _account(fills: tuple[Fill, ...], duplicates: int) -> AccountingResult:
    lots: dict[tuple, list[list[Decimal]]] = {}
    currencies = {}
    cash_krw = {}
    cash_currency = {}
    order_quantities = {}
    daily = {}
    realized = _ZERO
    for fill in fills:
        account = (fill.venue, fill.account_scope)
        instrument = (*account, fill.market, fill.symbol)
        identity = (fill.quote_currency, fill.base_currency)
        if instrument in currencies and currencies[instrument] != identity:
            return AccountingResult(ok=False, reasons=("INCONSISTENT_INSTRUMENT_CURRENCY",))
        currencies[instrument] = identity
        current_lots = lots.setdefault(instrument, [])
        notional = fill.quantity * fill.price
        quote_fee = fill.fee_amount if fill.fee_currency == fill.quote_currency else _ZERO
        base_fee = fill.fee_amount if fill.base_currency and fill.fee_currency == fill.base_currency else _ZERO
        krw_fee = fill.fee_amount if fill.fee_currency == "KRW" and fill.quote_currency != "KRW" else _ZERO
        signed_notional = -notional if fill.side == "buy" else notional
        movement_quote = signed_notional - quote_fee
        movement_krw = movement_quote * fill.quote_krw - krw_fee
        currency_key = (*account, fill.quote_currency)
        cash_currency[currency_key] = cash_currency.get(currency_key, _ZERO) + movement_quote
        if krw_fee:
            krw_key = (*account, "KRW")
            cash_currency[krw_key] = cash_currency.get(krw_key, _ZERO) - krw_fee
        cash_krw[account] = cash_krw.get(account, _ZERO) + movement_krw
        order_key = (*account, fill.market, fill.order_date, fill.broker_org_id, fill.order_id)
        order_quantities[order_key] = order_quantities.get(order_key, _ZERO) + fill.quantity
        if fill.side == "buy":
            current_lots.append([fill.quantity - base_fee, -movement_krw])
            continue
        needed = fill.quantity + base_fee
        if sum((lot[0] for lot in current_lots), _ZERO) < needed:
            return AccountingResult(ok=False, reasons=("INCOMPLETE_ACQUISITION_HISTORY",))
        cost = _ZERO
        while needed:
            quantity, basis = current_lots[0]
            taken = min(needed, quantity)
            allocation = _allocate_cost(basis, taken, quantity)
            cost += allocation
            needed -= taken
            if taken == quantity:
                current_lots.pop(0)
            else:
                current_lots[0] = [quantity - taken, basis - allocation]
        profit = movement_krw - cost
        realized += profit
        day_key = (*account, fill.executed_at.astimezone(_SEOUL).date())
        daily[day_key] = daily.get(day_key, _ZERO) + profit
    inventory = tuple((*key, sum((lot[0] for lot in rows), _ZERO), sum((lot[1] for lot in rows), _ZERO))
                      for key, rows in sorted(lots.items()) if rows)
    return AccountingResult(ok=True, reasons=(), realized_net_profit_krw=realized, inventory=inventory,
                            cash_deltas_by_account_krw=tuple((*key, value) for key, value in sorted(cash_krw.items())),
                            cash_deltas_by_currency=tuple((*key, value) for key, value in sorted(cash_currency.items())),
                            order_quantities=tuple((*key, value) for key, value in sorted(order_quantities.items())),
                            realized_by_account_day_krw=tuple((*key, value) for key, value in sorted(daily.items())),
                            accepted_fills=fills, duplicate_count=duplicates)
