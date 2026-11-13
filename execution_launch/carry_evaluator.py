"""Fixed carry-v2 paper arithmetic, not an issued evaluation or trading authority.

The issuer validates the registered protocol, complete capture, causal program
decisions and observation provenance before calling this module. These functions
only calculate hypothetical fills at the supplied prices. They neither establish
real liquidity/GTC completion nor grant approval. Terminal marks are valuations,
never invented sale proceeds. All four scenarios use the shared behavior policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math
import re

from execution_launch.managed_behavior import (
    BEHAVIOR_REVISION, FixedDecisionV2, benchmark_fixed_decision_v2,
    decision_digest, derive_fixed_intent_v2, resolve_behavior,
)

_ZERO = Fraction(0)
_LIMIT = Fraction(10**100)
_SCALE = 10**18
_DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?')
_SHA = re.compile(r'[0-9a-f]{64}')
_MAX_TEXT = 4096


class CarryArithmeticError(ValueError):
    """Fixed reason codes only; arithmetic refusal is not a HOLD decision."""


def _require(condition, code):
    if not condition:
        raise CarryArithmeticError(code)


def _amount(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite()
             and len(value.as_tuple().digits) <= 2048
             and abs(value.as_tuple().exponent) <= 2048,
             'CARRY_AMOUNT_INVALID')
    value = Fraction(value)
    _require((value > 0 if positive else value >= 0) and value <= _LIMIT,
             'CARRY_AMOUNT_INVALID')
    return value


def _decimal(value: Fraction) -> Decimal:
    """Exact terminating conversion independent of the ambient decimal context."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    _require(denominator == 1, 'CARRY_NONTERMINATING_AMOUNT')
    scale = max(twos, fives)
    _require(scale <= 2048, 'CARRY_AMOUNT_INVALID')
    coefficient = abs(value.numerator) * 2**(scale-twos) * 5**(scale-fives)
    digits = tuple(int(c) for c in str(coefficient))
    _require(len(digits) <= 2048, 'CARRY_AMOUNT_INVALID')
    return Decimal((int(value < 0), digits, -scale))


def decimal_text(value: Decimal) -> str:
    """Bounded signed money codec; legacy strategy decimal encoding is unchanged."""
    _require(type(value) is Decimal and value.is_finite()
             and len(value.as_tuple().digits) <= 2048
             and abs(value.as_tuple().exponent) <= 2048
             and abs(Fraction(value)) <= _LIMIT, 'CARRY_DECIMAL_INVALID')
    text = format(value, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    if not value:
        text = '0'
    _require(len(text) <= _MAX_TEXT, 'CARRY_DECIMAL_INVALID')
    return text


def parse_decimal_text(value: str) -> Decimal:
    _require(type(value) is str and 0 < len(value) <= _MAX_TEXT
             and _DECIMAL.fullmatch(value) is not None and value != '-0',
             'CARRY_DECIMAL_INVALID')
    result = Decimal(value)
    _require(decimal_text(result) == value, 'CARRY_DECIMAL_INVALID')
    return result


def _text(value):
    return decimal_text(_decimal(value))


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


@dataclass(frozen=True, kw_only=True)
class FifoLot:
    quantity: Decimal
    cost_quote: Decimal

    def __post_init__(self):
        _amount(self.quantity, positive=True)
        _amount(self.cost_quote)


def release_fifo_cost(lots: tuple[FifoLot, ...], quantity: Decimal
                      ) -> tuple[tuple[FifoLot, ...], Decimal]:
    """Release acquisition-fee-inclusive cost, preserving the last exact residue.

    A partial lot's cost share is rounded DOWN to 18 decimal places. Closing the
    remaining quantity consumes its entire remaining basis, including sub-18dp
    residuals. This accepts hypothetical ledger inputs, not verified account data.
    """
    _require(type(lots) is tuple and len(lots) <= 20000
             and all(type(lot) is FifoLot for lot in lots), 'CARRY_FIFO_INVALID')
    needed = _amount(quantity, positive=True)
    for lot in lots:
        lot.__post_init__()
    _require(sum((Fraction(lot.quantity) for lot in lots), _ZERO) >= needed,
             'CARRY_FIFO_INCOMPLETE')
    remaining, cost = [], _ZERO
    for lot in lots:
        held, basis = Fraction(lot.quantity), Fraction(lot.cost_quote)
        taken = min(needed, held)
        if not taken:
            remaining.append(lot)
            continue
        if taken == held:
            allocation = basis
        else:
            share = basis*taken/held
            allocation = Fraction((share*_SCALE).__floor__(), _SCALE)
            remaining.append(FifoLot(quantity=_decimal(held-taken),
                                     cost_quote=_decimal(basis-allocation)))
        cost += allocation
        needed -= taken
    _require(needed == 0, 'CARRY_FIFO_INCOMPLETE')
    return tuple(remaining), _decimal(cost)


@dataclass(frozen=True, kw_only=True)
class CarryMetricsV2:
    observations: int
    completed_roundtrips: int
    rejected_small_orders: int
    total_return: float
    mean_return: float
    max_drawdown: float
    total_fees_quote: float
    turnover_quote: float
    terminal_units: str
    cash_nonnegative: bool
    terminal_cash_quote: str
    terminal_mark_quote: str
    terminal_marked_equity_quote: str
    terminal_inventory_cost_quote: str
    realized_net_profit_quote: str
    unrealized_net_profit_quote: str
    total_fees_quote_exact: str
    turnover_quote_exact: str
    terminal_observed_at: datetime
    terminal_source_sha256: str
    terminal_decision_state: str
    terminal_decision_cause: str
    terminal_execution_block_reasons: tuple[str, ...]
    fills_sha256: str
    lots_sha256: str


def _floor(value, unit):
    return (value/unit).__floor__()*unit


def _ceil(value, unit):
    return -(-value/unit).__floor__()*unit


def simulate_carry(protocol, bars, decisions, rules, *, cost_multiple=1, lag=1,
                   buy_hold=False) -> tuple[CarryMetricsV2, tuple[float, ...]]:
    """Unissued scenario arithmetic using complete, separately validated V2 inputs.

    ``lag`` is an execution delay, never permission to use a future decision.
    At E the initial study has no new management issuer: every candidate remains
    blocked. A valid cash/SELL verdict remains visible even when blocked. No
    terminal order, cancellation, spread deduction or hypothetical liquidation
    fee is invented. The terminal equity includes unrealized mark changes.
    """
    _require(resolve_behavior(protocol) == BEHAVIOR_REVISION, 'CARRY_PROTOCOL_REQUIRED')
    _require(type(cost_multiple) is int and cost_multiple in (1, 2)
             and type(lag) is int and lag in (1, 2) and type(buy_hold) is bool,
             'CARRY_SCENARIO_INVALID')
    _require(type(bars) is tuple and 2 <= len(bars) <= 20000
             and type(decisions) is tuple and len(decisions) == len(bars),
             'CARRY_CAPTURE_INVALID')
    _require(protocol.venue == rules.venue == 'upbit'
             and protocol.market == rules.market == 'spot'
             and protocol.quote_currency == 'KRW' and protocol.symbol == rules.symbol,
             'CARRY_SCOPE_INVALID')
    initial = cash = _amount(protocol.initial_cash_quote, positive=True)
    fee = _amount(protocol.fee_fraction)*cost_multiple
    slip = _amount(protocol.slippage_bps)*cost_multiple/10000
    _require(fee <= Fraction(1, 5) and slip < 1, 'CARRY_COST_INVALID')
    lot, tick = _amount(rules.lot_size, positive=True), _amount(rules.tick_size, positive=True)
    min_qty, min_notional = _amount(rules.min_quantity), _amount(rules.min_notional_krw)
    _require(type(protocol.capture_end) is datetime and protocol.capture_end.utcoffset() is not None,
             'CARRY_TIME_INVALID')
    previous_time = None
    for i, (row, decision) in enumerate(zip(bars, decisions)):
        _require(type(row.observed_at) is datetime and row.observed_at.utcoffset() is not None
                 and (previous_time is None or row.observed_at > previous_time), 'CARRY_TIME_INVALID')
        bid, ask, mark = (_amount(getattr(row, name), positive=True) for name in ('bid', 'ask', 'mark'))
        _require(bid <= mark <= ask and _amount(row.quote_krw, positive=True) == 1,
                 'CARRY_BAR_INVALID')
        _require(type(row.source_sha256) is str and _SHA.fullmatch(row.source_sha256) is not None,
                 'CARRY_SOURCE_INVALID')
        _require(type(decision) is FixedDecisionV2 and decision.bar_index == i,
                 'CARRY_DECISION_INVALID')
        decision_digest(decision)
        _require(decision.cause != 'benchmark_buy_hold', 'CARRY_BENCHMARK_NOT_STRATEGY')
        previous_time = row.observed_at
    _require(bars[-1].observed_at == protocol.capture_end, 'CARRY_TERMINAL_TIME_INVALID')
    units = fees = turnover = realized = basis = _ZERO
    lots, navs, fills = (), [cash], []
    trips = rejected = 0
    final_state, final_cause, final_blocks = 'not_yet_available', 'fill_delay', ()
    for i, row in enumerate(bars[1:], start=1):
        mark = Fraction(row.mark)
        _require(0 < cash+units*mark <= _LIMIT, 'CARRY_EQUITY_INVALID')
        quantity, action = _ZERO, 'hold'
        if i >= lag:
            decision = decisions[i-lag]
            if buy_hold:
                decision = benchmark_fixed_decision_v2(bar_index=decision.bar_index,
                    decided_at=decision.decided_at, history_sha256=decision.history_sha256)
            intent = derive_fixed_intent_v2(decision, cash_quote=_decimal(cash),
                units=_decimal(units), mark=row.mark, slot=row.observed_at,
                deadline=protocol.capture_end)
            final_state, final_cause = intent.decision_state, intent.decision_cause
            final_blocks = intent.execution_block_reasons
            action = intent.action
            # The real carry callback does not size a blocked/HOLD candidate.
            # A hypothetical stressed bid rounding to zero cannot invalidate an
            # observed terminal mark when no execution is even contemplated.
            if not final_blocks and action in ('entry', 'exit'):
                ask = _ceil(Fraction(row.ask)*(1+slip), tick)
                bid = _floor(Fraction(row.bid)*(1-slip), tick)
                _require(bid > 0 and ask > 0, 'CARRY_EXECUTION_PRICE_INVALID')
            if not final_blocks and action == 'entry':
                target = Fraction(intent.target_fraction)
                gap = target*(cash+units*mark)-units*mark
                denominator = ask*(1+fee)-target*(ask*(1+fee)-mark)
                _require(gap > 0 and denominator > 0, 'CARRY_ENTRY_INVALID')
                quantity = min(_floor(gap/denominator, lot), _floor(cash/(ask*(1+fee)), lot))
            elif not final_blocks and action == 'exit':
                quantity = units
        else:
            final_state, final_cause = 'not_yet_available', 'fill_delay'
            final_blocks = ('MANAGED_FILL_DELAY',)
            if row.observed_at >= protocol.capture_end:
                final_blocks += ('MANAGED_DEADLINE_REACHED',)
        if quantity:
            price = ask if action == 'entry' else bid
            notional = quantity*price
            if quantity < min_qty or notional < min_notional:
                rejected += 1
            else:
                charge = notional*fee
                if action == 'entry':
                    cash -= notional+charge
                    units += quantity
                    basis += notional+charge
                    lots += (FifoLot(quantity=_decimal(quantity), cost_quote=_decimal(notional+charge)),)
                else:
                    lots, released = release_fifo_cost(lots, _decimal(quantity))
                    cash += notional-charge
                    units -= quantity
                    basis -= Fraction(released)
                    realized += notional-charge-Fraction(released)
                    if not units:
                        trips += 1
                fees += charge
                turnover += notional
                fills.append({'bar_index': i, 'action': action, 'quantity': _text(quantity),
                    'price_quote': _text(price), 'fee_quote': _text(charge),
                    'source_sha256': row.source_sha256, 'decision_sha256': decision.decision_sha256})
        nav = cash+units*mark
        _require(cash >= 0 and units >= 0 and 0 < nav <= _LIMIT, 'CARRY_EQUITY_INVALID')
        _require(nav-initial == realized+(units*mark-basis), 'CARRY_ACCOUNTING_IDENTITY')
        navs.append(nav)
    net_returns = tuple(float(after/before-1) for before, after in zip(navs, navs[1:]))
    _require(all(math.isfinite(value) and value > -1 for value in net_returns), 'CARRY_RETURN_INVALID')
    peak, drawdown = navs[0], _ZERO
    for nav in navs:
        peak = max(peak, nav)
        drawdown = max(drawdown, 1-nav/peak)
    last = bars[-1]
    _require(basis == sum((Fraction(item.cost_quote) for item in lots), _ZERO)
             and units == sum((Fraction(item.quantity) for item in lots), _ZERO),
             'CARRY_ACCOUNTING_IDENTITY')
    metrics = CarryMetricsV2(observations=len(net_returns), completed_roundtrips=trips,
        rejected_small_orders=rejected, total_return=float(navs[-1]/initial-1),
        mean_return=math.fsum(net_returns)/len(net_returns), max_drawdown=float(drawdown),
        total_fees_quote=float(fees), turnover_quote=float(turnover), terminal_units=_text(units),
        cash_nonnegative=True, terminal_cash_quote=_text(cash), terminal_mark_quote=decimal_text(last.mark),
        terminal_marked_equity_quote=_text(navs[-1]), terminal_inventory_cost_quote=_text(basis),
        realized_net_profit_quote=_text(realized), unrealized_net_profit_quote=_text(units*Fraction(last.mark)-basis),
        total_fees_quote_exact=_text(fees), turnover_quote_exact=_text(turnover),
        terminal_observed_at=last.observed_at, terminal_source_sha256=last.source_sha256,
        terminal_decision_state=final_state, terminal_decision_cause=final_cause,
        terminal_execution_block_reasons=final_blocks, fills_sha256=_digest(fills),
        lots_sha256=_digest([{'quantity': decimal_text(item.quantity),
                            'cost_quote': decimal_text(item.cost_quote)} for item in lots]))
    return metrics, net_returns
