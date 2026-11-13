"""Closed metadata for retained guard inputs and completion observations.

Capture payloads are referenced, never re-encoded here. Historical owner/source
claims, receipt fields and their hashes are inert data, not proof of a current
account, durable commit, source completeness or execution permission. No I/O,
clock reads, arbitrary class loading or capture registry mutation occurs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from functools import wraps
import hashlib
import json
import re

from execution_control.risk import RiskPolicy, RecoveryCondition, validate_recovery_condition
from execution_launch.continuous_guard import OwnerContextClaim, _owner, _instant
from execution_launch.continuous_guard_commit import GuardCommitReceipt
from execution_launch import guard_capture_format as C

SCHEMA_VERSION = 1
INPUT_DOMAIN = b'tradegen-guard-generation-input/1\n'
COMPLETION_DOMAIN = b'tradegen-guard-generation-completion/1\n'
_CEILINGS = dict(max_record_bytes=65536, max_nodes=2048, max_text_bytes=16384, max_depth=12)
_QUANTA = tuple(Decimal((0, (1,), exponent)) for exponent in range(-512, 513))
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_IDENTIFIER = re.compile(r'[A-Za-z0-9_.:/-]{1,128}\Z')
_POLICY_NUMBERS = ('initial_equity', 'drawdown_activation_equity', 'positive_profit_loss_fraction',
                   'peak_drawdown_fraction', 'zero_profit_day_target_fraction')
_POLICY_OPTIONAL = ('first_day_loss_budget', 'zero_profit_day_loss_budget')
_POLICY_TEXT = ('version', 'valuation_convention', 'daily_loss_convention')
_POLICY_FIELDS = ('version',) + _POLICY_NUMBERS + _POLICY_OPTIONAL + (
    'valuation_convention', 'daily_loss_convention', 'recovery_condition')
_CONDITION_FIELDS = ('cutoff_seconds', 'timezone', 'reference')
_OWNER_HASHES = ('owner_head_sha256', 'code_sha256', 'code_approval_sha256', 'source_sha256')
_OWNER_FIELDS = ('owner_head_sha256', 'code_sha256', 'code_approval_sha256',
                 'signed_floor_krw', 'signed_daily_loss_krw', 'observed_at', 'source_sha256')
_RECEIPT_HASHES = ('transaction_id', 'guard_head', 'baseline_head', 'control_head')
_RECEIPT_FIELDS = _RECEIPT_HASHES + ('permanently_halted', 'replayed')
_INPUT_HASHES = ('capture_archive_digest', 'capture_packet_sha256', 'capture_material_sha256',
    'previous_state_sha256', 'expected_guard_head', 'expected_baseline_head',
    'expected_control_head', 'package_sha256', 'input_sha256')
_INPUT_FIELDS = ('schema_version', 'kind', 'replay_revision') + _INPUT_HASHES + (
    'policy', 'owner_before', 'owner_after', 'evaluated_at')
_COMPLETION_HASHES = ('input_archive_digest', 'input_record_sha256', 'package_sha256',
                     'input_sha256', 'completion_head', 'observed_control_head')
_COMPLETION_FIELDS = ('schema_version', 'kind', 'input_archive_digest', 'input_record_sha256',
    'package_sha256', 'input_sha256', 'receipt', 'completion_head', 'observed_control_head', 'recorded_at')
# Only fixed Decimal/datetime scalar specs are used; no class is added to _SCHEMAS.
_SCALAR_LIMITS = C.CaptureFormatLimits(max_packet_bytes=65536, max_nodes=2048,
                                      max_text_bytes=16384, max_depth=12)


class GuardGenerationFormatError(ValueError):
    """Fixed diagnostics; never private values or underlying exception strings."""


def _need(ok, code='GENERATION_FORMAT_INVALID'):
    if not ok:
        raise GuardGenerationFormatError(code)


def _fixed(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except GuardGenerationFormatError:
            raise
        except C.GuardCaptureFormatError as exc:
            code = 'GENERATION_RESOURCE_LIMIT' if str(exc) == 'CAPTURE_RESOURCE_LIMIT' else 'GENERATION_FORMAT_INVALID'
            raise GuardGenerationFormatError(code) from None
        except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError, RecursionError):
            raise GuardGenerationFormatError('GENERATION_FORMAT_INVALID') from None
    return checked


@dataclass(frozen=True, kw_only=True, slots=True)
class GenerationFormatLimits:
    max_record_bytes: int = 65536
    max_nodes: int = 2048
    max_text_bytes: int = 16384
    max_depth: int = 12

    def __post_init__(self):
        try:
            for name, maximum in _CEILINGS.items():
                value = getattr(self, name)
                _need(type(value) is int and 0 < value <= maximum, 'GENERATION_LIMITS_INVALID')
        except (AttributeError, TypeError):
            raise GuardGenerationFormatError('GENERATION_LIMITS_INVALID') from None


DEFAULT_LIMITS = GenerationFormatLimits()


def _limits(value):
    _need(type(value) is GenerationFormatLimits, 'GENERATION_LIMITS_INVALID')
    value.__post_init__()
    return value


def _keys(value, names):
    _need(type(value) is dict and len(value) == len(names)
          and all(type(name) is str for name in value) and set(value) == set(names))
    return value


def _attributes(value, cls, names, *, slotted=False):
    _need(type(value) is cls)
    if not slotted:
        actual = vars(value)
        _need(type(actual) is dict and len(actual) == len(names)
              and all(type(name) is str for name in actual) and set(actual) == set(names))
    return {name:getattr(value, name) for name in names}


def _hash(value):
    _need(type(value) is str and len(value) == 64 and _HASH.fullmatch(value) is not None)
    return value


def _scalar(value, spec, *, decode=False):
    # The spec is selected only by the closed field schema below.
    if spec == 'Decimal' and not decode:
        _need(type(value) is Decimal and value.is_finite())
        # as_tuple() allocates the entire coefficient, so bound it first with
        # constant-space Decimal operations and a fixed finite exponent table.
        exponent = next((index-512 for index, quantum in enumerate(_QUANTA)
                         if value.same_quantum(quantum)), None)
        _need(exponent is not None and value.adjusted()-exponent+1 <= 512,
              'GENERATION_RESOURCE_LIMIT')
    result = C._Codec(_SCALAR_LIMITS, {}).value(value, spec, decode=decode)
    if spec == 'datetime':
        _instant(result if decode else value)
    return result


def _policy(value, *, decode=False):
    body = _keys(value, _POLICY_FIELDS) if decode else _attributes(value, RiskPolicy, _POLICY_FIELDS)
    values = {}
    for name in _POLICY_TEXT:
        item = body[name]
        _need(type(item) is str and _IDENTIFIER.fullmatch(item) is not None)
        values[name] = item
    for name in _POLICY_NUMBERS + _POLICY_OPTIONAL:
        item = body[name]
        values[name] = None if name in _POLICY_OPTIONAL and item is None else _scalar(item, 'Decimal', decode=decode)
    condition = body['recovery_condition']
    if condition is not None:
        nested = (_keys(condition, _CONDITION_FIELDS) if decode else
                  _attributes(condition, RecoveryCondition, _CONDITION_FIELDS))
        # Validate actual exact class/fields without evaluating or changing policy.
        actual = RecoveryCondition(**nested)
        validate_recovery_condition(actual)
        condition = actual if decode else dict(nested)
    values['recovery_condition'] = condition
    result = RiskPolicy(**values) if decode else values
    # Existing optional-budget semantics are narrower than a finite Decimal.
    for name in _POLICY_OPTIONAL:
        number = getattr(result, name) if decode else body[name]
        _need(number is None or number >= 0)
    return result


def _owner_value(value, *, decode=False):
    body = _keys(value, _OWNER_FIELDS) if decode else _attributes(value, OwnerContextClaim, _OWNER_FIELDS)
    values = {name:_hash(body[name]) for name in _OWNER_HASHES}
    for name in ('signed_floor_krw', 'signed_daily_loss_krw'):
        values[name] = _scalar(body[name], 'Decimal', decode=decode)
    values['observed_at'] = _scalar(body['observed_at'], 'datetime', decode=decode)
    if decode:
        result = OwnerContextClaim(**values)
        _owner(result)
        return result
    _owner(value)
    return values


def _receipt(value, *, decode=False):
    body = _keys(value, _RECEIPT_FIELDS) if decode else _attributes(value, GuardCommitReceipt, _RECEIPT_FIELDS)
    values = {name:_hash(body[name]) for name in _RECEIPT_HASHES}
    for name in ('permanently_halted', 'replayed'):
        _need(type(body[name]) is bool)
        values[name] = body[name]
    return GuardCommitReceipt(**values) if decode else values


def _admit_document(document, limits):
    """Bound the already closed JSON tree; key strings count toward both budgets."""
    nodes, text = 0, 0
    def visit(value, depth):
        nonlocal nodes, text
        nodes += 1
        _need(nodes <= limits.max_nodes, 'GENERATION_RESOURCE_LIMIT')
        if type(value) is str:
            _need(value.isascii())
            text += len(value)
            _need(text <= limits.max_text_bytes, 'GENERATION_RESOURCE_LIMIT')
        elif type(value) in (dict, list):
            depth += 1
            _need(depth <= limits.max_depth, 'GENERATION_RESOURCE_LIMIT')
            if type(value) is dict:
                for key, item in value.items():
                    _need(type(key) is str)
                    visit(key, depth); visit(item, depth)
            else:
                for item in value:
                    visit(item, depth)
        else:
            _need(value is None or type(value) is bool or type(value) is int and value.bit_length() <= 256)
    visit(document, 0)


def _json_bytes(document, limits):
    _admit_document(document, limits)
    pieces, count = [], 0
    for piece in json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                                  allow_nan=False).iterencode(document):
        raw = piece.encode('ascii'); count += len(raw)
        _need(count <= limits.max_record_bytes, 'GENERATION_RESOURCE_LIMIT')
        pieces.append(raw)
    return b''.join(pieces)


def _scan(raw, limits):
    """Metadata-specific preallocation bounds, not the larger capture scanner."""
    _need(type(raw) is bytes)
    _need(0 < len(raw) <= limits.max_record_bytes, 'GENERATION_RESOURCE_LIMIT')
    _need(raw.isascii())
    depth, nodes, text = 0, 0, 0
    quoted = escaped = bare = False
    for byte in raw:
        if quoted:
            if not escaped and byte == 34:
                quoted = False
            else:
                text += 1
                _need(text <= limits.max_text_bytes, 'GENERATION_RESOURCE_LIMIT')
                if escaped:
                    escaped = False
                elif byte == 92:
                    escaped = True
        elif byte == 34:
            quoted = True; bare = False; nodes += 1
        elif byte in (123, 91):
            depth += 1; nodes += 1; bare = False
            _need(depth <= limits.max_depth, 'GENERATION_RESOURCE_LIMIT')
        elif byte in (125, 93):
            depth -= 1; bare = False
            _need(depth >= 0)
        elif byte in (9, 10, 13, 32, 44, 58):
            bare = False
        elif not bare:
            bare = True; nodes += 1
        _need(nodes <= limits.max_nodes, 'GENERATION_RESOURCE_LIMIT')
    _need(not quoted and depth == 0)


def _pairs(values):
    result = {}
    for key, value in values:
        _need(type(key) is str and key not in result)
        result[key] = value
    return result


def _integer(value):
    _need(len(value) <= 80, 'GENERATION_RESOURCE_LIMIT')
    result = int(value)
    _need(result.bit_length() <= 256, 'GENERATION_RESOURCE_LIMIT')
    return result


def _no_number(_value):
    raise GuardGenerationFormatError('GENERATION_FORMAT_INVALID')


def _decode(raw, limits):
    _scan(raw, limits)
    result = json.loads(raw.decode('ascii'), object_pairs_hook=_pairs,
        parse_int=_integer, parse_float=_no_number, parse_constant=_no_number)
    _need(_json_bytes(result, limits) == raw)
    return result


@dataclass(frozen=True, kw_only=True, slots=True)
class GuardInputRecord:
    schema_version: int
    kind: str
    replay_revision: str
    capture_archive_digest: str
    capture_packet_sha256: str
    capture_material_sha256: str
    previous_state_sha256: str
    expected_guard_head: str
    expected_baseline_head: str
    expected_control_head: str
    package_sha256: str
    input_sha256: str
    policy: RiskPolicy = field(repr=False)
    owner_before: OwnerContextClaim = field(repr=False)
    owner_after: OwnerContextClaim = field(repr=False)
    evaluated_at: datetime

    @_fixed
    def __post_init__(self):
        body = _input_document(self)
        # Explicit reconstruction detaches all mutable-instance references. It
        # invokes no arbitrary deepcopy hook and preserves exact Decimal scale.
        object.__setattr__(self, 'policy', _policy(body['policy'], decode=True))
        object.__setattr__(self, 'owner_before', _owner_value(body['owner_before'], decode=True))
        object.__setattr__(self, 'owner_after', _owner_value(body['owner_after'], decode=True))
        object.__setattr__(self, 'evaluated_at', _scalar(body['evaluated_at'], 'datetime', decode=True))


@dataclass(frozen=True, kw_only=True, slots=True)
class GuardCompletionRecord:
    schema_version: int
    kind: str
    input_archive_digest: str
    input_record_sha256: str
    package_sha256: str
    input_sha256: str
    receipt: GuardCommitReceipt
    completion_head: str
    observed_control_head: str
    recorded_at: datetime

    @_fixed
    def __post_init__(self):
        body = _completion_document(self)
        object.__setattr__(self, 'receipt', _receipt(body['receipt'], decode=True))
        object.__setattr__(self, 'recorded_at', _scalar(body['recorded_at'], 'datetime', decode=True))


def _input_document(value, *, limits=DEFAULT_LIMITS):
    body = _attributes(value, GuardInputRecord, _INPUT_FIELDS, slotted=True)
    _need(type(body['schema_version']) is int and body['schema_version'] == SCHEMA_VERSION)
    _need(type(body['kind']) is str and body['kind'] == 'GUARD_INPUT')
    _need(type(body['replay_revision']) is str and body['replay_revision'] == C.REPLAY_REVISION)
    result = {name:body[name] for name in ('schema_version', 'kind', 'replay_revision')}
    result.update({name:_hash(body[name]) for name in _INPUT_HASHES})
    result['policy'] = _policy(body['policy'])
    result['owner_before'] = _owner_value(body['owner_before'])
    result['owner_after'] = _owner_value(body['owner_after'])
    result['evaluated_at'] = _scalar(body['evaluated_at'], 'datetime')
    _json_bytes(result, limits)
    return result


def _completion_document(value, *, limits=DEFAULT_LIMITS):
    body = _attributes(value, GuardCompletionRecord, _COMPLETION_FIELDS, slotted=True)
    _need(type(body['schema_version']) is int and body['schema_version'] == SCHEMA_VERSION)
    _need(type(body['kind']) is str and body['kind'] == 'GUARD_COMPLETION')
    result = {name:body[name] for name in ('schema_version', 'kind')}
    result.update({name:_hash(body[name]) for name in _COMPLETION_HASHES})
    result['receipt'] = _receipt(body['receipt'])
    result['recorded_at'] = _scalar(body['recorded_at'], 'datetime')
    _json_bytes(result, limits)
    return result


@_fixed
def input_bytes(record, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    return _json_bytes(_input_document(record, limits=limits), limits)


@_fixed
def completion_bytes(record, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    return _json_bytes(_completion_document(record, limits=limits), limits)


@_fixed
def parse_input(raw: bytes, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    body = _keys(_decode(raw, limits), _INPUT_FIELDS)
    values = dict(body)
    values.update(policy=_policy(body['policy'], decode=True),
        owner_before=_owner_value(body['owner_before'], decode=True),
        owner_after=_owner_value(body['owner_after'], decode=True),
        evaluated_at=_scalar(body['evaluated_at'], 'datetime', decode=True))
    result = GuardInputRecord(**values)
    _need(input_bytes(result, limits=limits) == raw)
    return result


@_fixed
def parse_completion(raw: bytes, *, limits=DEFAULT_LIMITS):
    limits = _limits(limits)
    body = _keys(_decode(raw, limits), _COMPLETION_FIELDS)
    values = dict(body)
    values.update(receipt=_receipt(body['receipt'], decode=True),
                  recorded_at=_scalar(body['recorded_at'], 'datetime', decode=True))
    result = GuardCompletionRecord(**values)
    _need(completion_bytes(result, limits=limits) == raw)
    return result


@_fixed
def input_digest(record, *, limits=DEFAULT_LIMITS):
    return hashlib.sha256(INPUT_DOMAIN+input_bytes(record, limits=limits)).hexdigest()


@_fixed
def completion_digest(record, *, limits=DEFAULT_LIMITS):
    return hashlib.sha256(COMPLETION_DOMAIN+completion_bytes(record, limits=limits)).hexdigest()
