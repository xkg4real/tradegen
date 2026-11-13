"""Closed fixed carry behavior and causal decisions; no approval or I/O.

These pure values describe a model verdict and execution candidates. They never
prove source completeness, issue management authority, or authorize an order.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re

from execution_launch.program import ProgramSpec, parameters_json, target_fraction

CARRY_EVALUATOR_REVISION = 'forward-paper-carry-v2'
BEHAVIOR_REVISION = 'protective-carry-v2'
TERMINAL_ACCOUNTING = 'mark_open_positions'
CARRY_FACTORY_ID = 'tradegen-fixed-carry-v2'
_HASH = re.compile(r'[0-9a-f]{64}')
_DECIMAL = re.compile(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?')
_DECISION_KEYS = frozenset({'schema_version', 'bar_index', 'decided_at', 'history_sha256',
    'behavior_sha256', 'state', 'cause', 'target_fraction', 'decision_sha256'})


class ManagedBehaviorError(ValueError):
    """Stable errors; invalid evidence is not a recorded unavailable observation."""


def _require(value, code):
    if not value:
        raise ManagedBehaviorError(code)


def _instant(value):
    _require(type(value) is datetime and value.utcoffset() is not None, 'MANAGED_TIME_INVALID')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds')


def _hash(value):
    _require(type(value) is str and _HASH.fullmatch(value) is not None, 'MANAGED_DIGEST_INVALID')
    return value


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode('ascii')).hexdigest()


def behavior_document() -> dict:
    """Fresh copy of the exact closed document bound by every carry protocol."""
    return {'schema_version': 2, 'behavior_revision': BEHAVIOR_REVISION,
        'evaluator_revision': CARRY_EVALUATOR_REVISION, 'factory_id': CARRY_FACTORY_ID,
        'scope': ['upbit', 'spot', 'KRW', 'fixed', 'gtc'], 'initial_condition': 'flat_start',
        'entry_interval': '[start,deadline)', 'deadline_action': 'request_management_approval',
        'post_deadline_automatic_action': 'blocked_without_separate_authority',
        'hold_rebalance_reduction': False, 'failure_action': 'block_dependent_action',
        'terminal_accounting': TERMINAL_ACCOUNTING,
        'fifo_cost_allocation': '18dp_down_final_residual', 'buy_fees': 'included_in_cost',
        'sell_fees': 'deducted_from_proceeds'}


def behavior_digest() -> str:
    return _digest(behavior_document())


def resolve_behavior(protocol) -> str:
    """Strict revision dispatch only; this is not full protocol validation."""
    version = getattr(protocol, 'schema_version', None)
    evaluator = getattr(protocol, 'evaluator_revision', None)
    revision = getattr(protocol, 'behavior_revision', None)
    terminal = getattr(protocol, 'terminal_accounting', None)
    commitment = getattr(protocol, 'management_behavior_sha256', None)
    universe = getattr(protocol, 'universe_rule_sha256', None)
    _require(type(version) is int, 'MANAGED_BEHAVIOR_REVISION_REQUIRED')
    if version == 1:
        _require((revision, terminal, commitment) == (None, None, None), 'MANAGED_BEHAVIOR_REVISION_REQUIRED')
        if evaluator == 'forward-paper-v1' and universe is None:
            return 'legacy-fixed-v1'
        if evaluator == 'forward-universe-v1' and universe is not None:
            return 'legacy-universe-v1'
        raise ManagedBehaviorError('MANAGED_BEHAVIOR_REVISION_REQUIRED')
    _require(version == 2 and evaluator == CARRY_EVALUATOR_REVISION and universe is None
             and revision == BEHAVIOR_REVISION and terminal == TERMINAL_ACCOUNTING
             and commitment == behavior_digest(), 'MANAGED_BEHAVIOR_REVISION_REQUIRED')
    return BEHAVIOR_REVISION


@dataclass(frozen=True, kw_only=True)
class FixedDecisionV2:
    schema_version: int
    bar_index: int
    decided_at: datetime
    history_sha256: str
    behavior_sha256: str
    state: str
    cause: str
    target_fraction: Decimal | None
    decision_sha256: str


def _fraction_text(value):
    _require(type(value) is Decimal and value.is_finite() and 0 <= value <= 1
             and len(value.as_tuple().digits) <= 40 and abs(value.as_tuple().exponent) <= 30,
             'MANAGED_DECISION_TARGET_INVALID')
    text = format(value, 'f')
    return (text.rstrip('0').rstrip('.') if '.' in text else text) if value else '0'


def _decision_body(value):
    _require(type(value) is FixedDecisionV2 and type(value.schema_version) is int
             and value.schema_version == 2 and type(value.bar_index) is int and 0 <= value.bar_index < 20000,
             'MANAGED_DECISION_SCHEMA_INVALID')
    _require(value.behavior_sha256 == behavior_digest(), 'MANAGED_BEHAVIOR_DIGEST_MISMATCH')
    target = None if value.target_fraction is None else _fraction_text(value.target_fraction)
    combinations = {'long_target': ('trend_above', 'benchmark_buy_hold'),
                    'cash_target': ('trend_not_above', 'always_cash'),
                    'warmup': ('insufficient_history',), 'unavailable': ('input_unavailable',)}
    _require(type(value.state) is str and type(value.cause) is str
             and value.cause in combinations.get(value.state, ()), 'MANAGED_DECISION_CAUSE_INVALID')
    _require((value.state == 'long_target' and target is not None and value.target_fraction > 0)
             or (value.state == 'cash_target' and target == '0')
             or (value.state in ('warmup', 'unavailable') and target is None),
             'MANAGED_DECISION_TARGET_INVALID')
    _require(value.cause != 'benchmark_buy_hold' or target == '1', 'MANAGED_DECISION_TARGET_INVALID')
    return {'schema_version': 2, 'bar_index': value.bar_index, 'decided_at': _instant(value.decided_at),
            'history_sha256': _hash(value.history_sha256), 'behavior_sha256': value.behavior_sha256,
            'state': value.state, 'cause': value.cause, 'target_fraction': target}


def decision_digest(value: FixedDecisionV2) -> str:
    """Validate all semantic fields and the stored digest, then return that digest."""
    expected = _digest(_decision_body(value))
    _require(_hash(value.decision_sha256) == expected, 'MANAGED_DECISION_DIGEST_MISMATCH')
    return expected


def decision_document(value: FixedDecisionV2) -> dict:
    body = _decision_body(value)
    return body | {'decision_sha256': decision_digest(value)}


def parse_decision_document(body: dict) -> FixedDecisionV2:
    _require(type(body) is dict and set(body) == _DECISION_KEYS, 'MANAGED_DECISION_SCHEMA_INVALID')
    try:
        value = dict(body)
        stamp = value['decided_at']
        _require(type(stamp) is str and len(stamp) <= 40, 'MANAGED_TIME_INVALID')
        value['decided_at'] = datetime.fromisoformat(stamp)
        _require(_instant(value['decided_at']) == stamp, 'MANAGED_TIME_INVALID')
        target = value['target_fraction']
        if target is not None:
            _require(type(target) is str and len(target) <= 72 and _DECIMAL.fullmatch(target) is not None,
                     'MANAGED_DECISION_TARGET_INVALID')
            value['target_fraction'] = Decimal(target)
            _require(_fraction_text(value['target_fraction']) == target, 'MANAGED_DECISION_TARGET_INVALID')
        decision = FixedDecisionV2(**value)
        decision_digest(decision)
        return decision
    except ManagedBehaviorError:
        raise
    except (ValueError, TypeError, ArithmeticError, OverflowError):
        raise ManagedBehaviorError('MANAGED_DECISION_SCHEMA_INVALID') from None


def _make(*, bar_index, decided_at, history_sha256, state, cause, target):
    value = FixedDecisionV2(schema_version=2, bar_index=bar_index, decided_at=decided_at,
        history_sha256=history_sha256, behavior_sha256=behavior_digest(), state=state,
        cause=cause, target_fraction=target, decision_sha256='0' * 64)
    body = _decision_body(value)
    return FixedDecisionV2(**{**vars(value), 'decision_sha256': _digest(body)})


def derive_fixed_decision_v2(program: ProgramSpec, marks: tuple[Decimal, ...], *, bar_index: int,
                             decided_at: datetime, history_sha256: str,
                             input_status: str = 'available') -> FixedDecisionV2:
    """Derive a causal fixed verdict; supplied unavailable is never an exception fallback.

    The capture issuer must establish an actual recorded lookup failure before
    supplying unavailable. The current complete-bar capture path uses available
    only. A malformed program, mark or prefix is always refused.
    """
    _require(type(program) is ProgramSpec and program.kind != 'universe_top1_momentum',
             'MANAGED_FIXED_PROGRAM_REQUIRED')
    _require(type(input_status) is str and input_status in ('available', 'unavailable'),
             'MANAGED_INPUT_STATUS_INVALID')
    _require(type(bar_index) is int and 0 <= bar_index < 20000 and type(marks) is tuple
             and (len(marks) == bar_index + 1 if input_status == 'available' else len(marks) <= bar_index + 1),
             'MANAGED_PREFIX_INVALID')
    # These existing pure validators preserve the exact original trend formula.
    parameters_json(program)
    target = target_fraction(program, marks)
    if input_status == 'unavailable':
        state, cause, target = 'unavailable', 'input_unavailable', None
    elif program.kind == 'cash':
        state, cause = 'cash_target', 'always_cash'
    elif len(marks) < program.slow_window:
        state, cause, target = 'warmup', 'insufficient_history', None
    elif target > 0:
        state, cause = 'long_target', 'trend_above'
    else:
        state, cause = 'cash_target', 'trend_not_above'
    return _make(bar_index=bar_index, decided_at=decided_at, history_sha256=history_sha256,
                 state=state, cause=cause, target=target)


def benchmark_fixed_decision_v2(*, bar_index: int, decided_at: datetime,
                                 history_sha256: str) -> FixedDecisionV2:
    """Explicit buy-and-hold counterfactual, never a strategy's authenticated verdict."""
    return _make(bar_index=bar_index, decided_at=decided_at, history_sha256=history_sha256,
                 state='long_target', cause='benchmark_buy_hold', target=Decimal(1))


@dataclass(frozen=True, kw_only=True)
class FixedIntentV2:
    action: str
    target_fraction: Decimal | None
    decision_state: str
    decision_cause: str
    execution_block_reasons: tuple[str, ...] = ()


def _ledger_amount(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite() and (value > 0 if positive else value >= 0)
             and value <= Decimal('1e100') and len(value.as_tuple().digits) <= 2048
             and abs(value.as_tuple().exponent) <= 2048, 'MANAGED_ACCOUNT_AMOUNT_INVALID')
    return Fraction(value)


def derive_fixed_intent_v2(decision: FixedDecisionV2, *, cash_quote: Decimal, units: Decimal,
                           mark: Decimal, slot: datetime, deadline: datetime) -> FixedIntentV2:
    """Pure model candidate plus independent lifecycle blocks; grants no permission."""
    decision_digest(decision)
    _instant(slot); _instant(deadline)
    _require(decision.decided_at <= slot, 'MANAGED_DECISION_IN_FUTURE')
    cash = _ledger_amount(cash_quote)
    held = _ledger_amount(units)
    price = _ledger_amount(mark, positive=True)
    action, reasons = 'hold', ()
    if decision.state == 'long_target':
        gap = Fraction(decision.target_fraction) * (cash + held * price) - held * price
        if gap > 0:
            action = 'entry'        # a negative allocation gap is a HOLD, never an implicit SELL
    elif decision.state == 'cash_target' and held > 0:
        action = 'exit'
    elif decision.state == 'unavailable':
        reasons = ('MANAGED_DECISION_UNAVAILABLE',)
    if slot >= deadline:
        reasons += ('MANAGED_DEADLINE_REACHED',)
        if action == 'exit':
            reasons += ('MANAGED_AUTHORITY_UNAVAILABLE',)
    return FixedIntentV2(action=action, target_fraction=decision.target_fraction,
        decision_state=decision.state, decision_cause=decision.cause, execution_block_reasons=reasons)
