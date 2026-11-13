"""Bounded inert Upbit read records; hashes never authenticate source or coverage.

Response bytes are separate payloads. Paths receive structural validation here;
the actual archive/transport also enforce their shared nine-endpoint allowlist.
This codec performs no I/O and issues no collector result or execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import json
import re
from types import MappingProxyType

_DOMAIN = b'tradegen-upbit-read-batch-record/1\x00'
_LIMIT_DOMAIN = b'tradegen-upbit-read-batch-limits/1\x00'
_HASH = re.compile(r'[0-9a-f]{64}')
_ID = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}')
_SCOPE = re.compile(r'[A-Za-z0-9_.:/-]{1,128}')
_PATH = re.compile(r'/[A-Za-z0-9_/-]{1,127}')
CLOCKS = frozenset(('OK', 'INVALID', 'RAISED', 'ROLLBACK'))
CAPTURE_CODES = frozenset('READ_CAPTURE_'+name for name in (
    'SINK_REFUSED', 'CONTEXT_REFUSED', 'SCOPE_REFUSED', 'CLOCK_REFUSED', 'RESOURCE_LIMIT',
    'RESPONSE_INVALID', 'TRANSPORT_ERROR'))
BATCH_CODES = frozenset('READ_BATCH_'+name for name in (
    'INPUT_INVALID', 'LIMITS_INVALID', 'RESOURCE_LIMIT', 'SOURCE_REQUIRED', 'STORE_REQUIRED',
    'SOURCE_CHANGED', 'CLOCK_REFUSED', 'ID_REUSED', 'ARCHIVE_REFUSED', 'COLLECTOR_REFUSED',
    'TRANSPORT_REFUSED', 'FORMAT_INVALID', 'CHAIN_INVALID'))
ERROR_CODES = BATCH_CODES | CAPTURE_CODES
_ATTEMPT_ERRORS = frozenset(('CONNECTION_ERROR', 'READ_TIMEOUT', 'TIMEOUT', 'OS_ERROR',
                           'VALUE_ERROR', 'OTHER_EXCEPTION'))
_CEILINGS = (2000, 4000, 12002, 8*1024*1024, 64*1024*1024, 2*1024*1024, 64*1024*1024)
_HEADERS = ('schema_version', 'batch_id', 'ordinal', 'previous_archive_digest', 'kind')


class ReadBatchFormatError(ValueError):
    """Fixed READ_BATCH_* diagnostics, never supplied values or exception text."""


def _need(condition, code='READ_BATCH_FORMAT_INVALID'):
    if not condition:
        raise ReadBatchFormatError(code)


@dataclass(frozen=True, kw_only=True, slots=True)
class ReadBatchLimits:
    max_calls: int = 2000
    max_attempts: int = 4000
    max_records: int = 12002
    max_body_bytes: int = 8*1024*1024
    max_total_body_bytes: int = 64*1024*1024
    max_record_bytes: int = 2*1024*1024
    max_total_record_bytes: int = 64*1024*1024

    def __post_init__(self):
        try:
            for item, ceiling in zip(fields(type(self)), _CEILINGS):
                value = getattr(self, item.name)
                _need(type(value) is int and 0 < value <= ceiling, 'READ_BATCH_LIMITS_INVALID')
        except (AttributeError, TypeError):
            raise ReadBatchFormatError('READ_BATCH_LIMITS_INVALID') from None


DEFAULT_LIMITS = ReadBatchLimits()


def checked_limits(limits):
    _need(type(limits) is ReadBatchLimits, 'READ_BATCH_LIMITS_INVALID')
    limits.__post_init__()
    return limits


def _hash(value):
    return type(value) is str and _HASH.fullmatch(value) is not None


def _int(value, lo, hi):
    return type(value) is int and lo <= value <= hi


def stamp(value):
    _need(type(value) is datetime)
    try:
        _need(value.utcoffset() is not None and 2 <= value.year <= 9998)
        result = value.astimezone(timezone.utc).isoformat(timespec='microseconds')
        _need(len(result) == 32)
        return result
    except (ValueError, OverflowError, TypeError):
        raise ReadBatchFormatError('READ_BATCH_FORMAT_INVALID') from None


def time_value(value):
    _need(type(value) is str and len(value) == 32)
    try:
        result = datetime.fromisoformat(value)
        _need(stamp(result) == value)
        return result
    except (ValueError, OverflowError, TypeError):
        raise ReadBatchFormatError('READ_BATCH_FORMAT_INVALID') from None


def _tree(value, *, limit):
    """Build one bounded detached snapshot; never revisit a caller container."""
    nodes, size = 0, 0
    def charge(amount):
        nonlocal size
        size += amount
        _need(size <= limit, 'READ_BATCH_RESOURCE_LIMIT')
    def text_size(item):
        _need(len(item) <= min(65536, limit), 'READ_BATCH_RESOURCE_LIMIT')
        return 2 + sum(12 if ord(char)>65535 else 6 if ord(char)<32 or ord(char)>126
                       else 2 if char in ('"', '\\') else 1 for char in item)
    def visit(item, depth):
        nonlocal nodes
        nodes += 1
        _need(depth <= 12 and nodes <= 250000, 'READ_BATCH_RESOURCE_LIMIT')
        kind = type(item)
        if kind is str:
            charge(text_size(item)); return item
        if item is None:
            charge(4); return None
        if kind is int:
            _need(-(2**63) <= item < 2**63)
            charge(20); return item
        if kind is datetime:
            charge(34); return stamp(item)
        if kind in (tuple, list):
            _need(len(item) <= 250000-nodes, 'READ_BATCH_RESOURCE_LIMIT')
            charge(2)
            result = []
            for child in item:
                charge(1); result.append(visit(child, depth+1))
            return tuple(result)
        if kind in (dict, MappingProxyType):
            # A proxy can wrap a user mapping. Every yielded entry is admitted
            # once, including an items() iterator that lies about its length.
            _need(len(item) <= 250000-nodes, 'READ_BATCH_RESOURCE_LIMIT')
            charge(2); result = {}
            for key, child in item.items():
                _need(type(key) is str and len(key) <= 128 and key not in result)
                charge(text_size(key)+2)
                result[key] = visit(child, depth+1)
            return MappingProxyType(result)
        raise ReadBatchFormatError('READ_BATCH_FORMAT_INVALID')
    return visit(value, 0)


def _keys(value, expected):
    _need(type(value) in (dict, MappingProxyType) and set(value) == set(expected.split()))


def _params(value):
    _need(type(value) is tuple and len(value) <= 16)
    for pair in value:
        _need(type(pair) is tuple and len(pair) == 2 and type(pair[0]) is str
              and type(pair[1]) is str and len(pair[0]) <= 128 and len(pair[1]) <= 65536)


def _request(body, limits):
    _need(_int(body['call_ordinal'], 1, limits.max_calls)
          and type(body['path']) is str and _PATH.fullmatch(body['path']) is not None)
    _params(body['params'])


def _clock(body, field):
    _need(body['clock_status'] in CLOCKS)
    if body['clock_status'] == 'OK':
        time_value(body[field])
    else:
        _need(body[field] is None)


def _validate(record, limits, *, selected_limits=True):
    _need(type(record) is ReadBatchRecord)
    try:
        headers = tuple(getattr(record, name) for name in _HEADERS)
        schema_version, batch_id, ordinal, previous_archive_digest, kind = headers
        _need(type(schema_version) is int and schema_version == 1
              and type(batch_id) is str and _ID.fullmatch(batch_id) is not None
              and _int(ordinal, 0, limits.max_records-1)
              and type(kind) is str)
        body = _tree(record.body, limit=limits.max_record_bytes)
        if kind == 'OPEN':
            _need(ordinal == 0 and previous_archive_digest is None)
            _keys(body, 'account_scope started_at limits_sha256 anchor_sha256 coverage_sha256 baseline_sha256 trade_fees_sha256')
            _need(type(body['account_scope']) is str and _SCOPE.fullmatch(body['account_scope']) is not None)
            time_value(body['started_at'])
            _need(all(_hash(body[name]) for name in ('limits_sha256', 'anchor_sha256', 'coverage_sha256',
                                                   'baseline_sha256', 'trade_fees_sha256')))
        else:
            _need(ordinal > 0 and _hash(previous_archive_digest))
            if kind == 'FETCH_BEGIN':
                _keys(body, 'call_ordinal path params requested_at')
                _request(body, limits); time_value(body['requested_at'])
            elif kind == 'ATTEMPT':
                _keys(body, 'call_ordinal attempt phase path params observed_at clock_status status_code '
                            'body_status body_bytes body_sha256 error_code')
                _request(body, limits)
                _need(_int(body['attempt'], 1, 2))
                _clock(body, 'observed_at')
                if body['phase'] == 'RESPONSE':
                    _need(body['status_code'] is None or _int(body['status_code'], 100, 999))
                    _need(body['error_code'] in (None, 'INVALID_RESPONSE'))
                    if body['body_status'] == 'PRESENT':
                        _need(_int(body['body_bytes'], 0, limits.max_body_bytes) and _hash(body['body_sha256']))
                    elif body['body_status'] == 'LIMIT_EXCEEDED':
                        # Constructors retain an inert fact without knowing the
                        # chosen batch limit. Every wire/read operation supplies
                        # that limit and verifies the actual overflow relation.
                        _need(_int(body['body_bytes'], limits.max_body_bytes+1 if selected_limits else 1, 2**63-1)
                              and body['body_sha256'] is None)
                    else:
                        _need(body['body_status'] == 'INVALID' and body['body_bytes'] is None
                              and body['body_sha256'] is None)
                    _need((body['status_code'] is None or body['body_status'] == 'INVALID')
                          == (body['error_code'] == 'INVALID_RESPONSE'))
                else:
                    _need(body['phase'] in ('BEFORE_SEND', 'TRANSPORT_ERROR')
                          and body['body_status'] == 'NOT_RECEIVED'
                          and body['body_bytes'] is None and body['body_sha256'] is None
                          and body['status_code'] is None)
                    _need(body['error_code'] is None if body['phase'] == 'BEFORE_SEND'
                          else body['error_code'] in _ATTEMPT_ERRORS)
            elif kind == 'FETCH_END':
                _keys(body, 'call_ordinal status receipt error_code')
                _need(_int(body['call_ordinal'], 1, limits.max_calls))
                if body['status'] == 'RETURNED':
                    _need(body['error_code'] is None)
                    receipt = body['receipt']
                    _keys(receipt, 'path params account_scope received_at server_time sha256')
                    _need(type(receipt['path']) is str and _PATH.fullmatch(receipt['path']) is not None
                          and type(receipt['account_scope']) is str
                          and _SCOPE.fullmatch(receipt['account_scope']) is not None and _hash(receipt['sha256']))
                    _params(receipt['params']); time_value(receipt['received_at']); time_value(receipt['server_time'])
                else:
                    _need(body['status'] == 'REFUSED' and body['receipt'] is None and body['error_code'] in ERROR_CODES)
            elif kind == 'CLOSE':
                _keys(body, 'status error_code collection_manifest_sha256 records calls attempts finished_at clock_status')
                _clock(body, 'finished_at')
                _need(_int(body['calls'], 0, limits.max_calls) and _int(body['attempts'], 0, limits.max_attempts)
                      and type(body['records']) is tuple and len(body['records']) == ordinal)
                for index, item in enumerate(body['records']):
                    _need(type(item) is tuple and len(item) == 2 and type(item[0]) is int
                          and item[0] == index and _hash(item[1]))
                if body['status'] == 'COLLECTED':
                    _need(body['error_code'] is None and _hash(body['collection_manifest_sha256'])
                          and body['clock_status'] == 'OK')
                else:
                    _need(body['status'] == 'REFUSED' and body['collection_manifest_sha256'] is None
                          and body['error_code'] in ERROR_CODES)
            else:
                raise ReadBatchFormatError('READ_BATCH_FORMAT_INVALID')
        current = tuple(getattr(record, name) for name in _HEADERS)
        _need(all(type(actual) is type(expected) and actual == expected
                  for actual, expected in zip(current, headers)))
        return body, headers
    except (AttributeError, KeyError, TypeError, OverflowError, RecursionError, RuntimeError):
        raise ReadBatchFormatError('READ_BATCH_FORMAT_INVALID') from None


@dataclass(frozen=True, kw_only=True, slots=True)
class ReadBatchRecord:
    schema_version: int
    batch_id: str
    ordinal: int
    previous_archive_digest: str | None
    kind: str
    body: object

    def __post_init__(self):
        object.__setattr__(self, 'body', _validate(self, DEFAULT_LIMITS, selected_limits=False)[0])


def _plain(value):
    if type(value) is MappingProxyType:
        return {key:_plain(child) for key, child in value.items()}
    if type(value) is tuple:
        return [_plain(child) for child in value]
    return value


def record_bytes(record, *, limits=DEFAULT_LIMITS):
    limits = checked_limits(limits)
    body, headers = _validate(record, limits)
    document = dict(zip(_HEADERS, headers))
    document['body'] = _plain(body)
    raw = json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
    _need(len(raw) <= limits.max_record_bytes, 'READ_BATCH_RESOURCE_LIMIT')
    return raw


def _admit_json(raw, maximum):
    _need(type(raw) is bytes and 0 < len(raw) <= maximum, 'READ_BATCH_RESOURCE_LIMIT')
    depth, count, quoted, escaped = 0, 0, False, False
    for char in raw:
        if quoted:
            if escaped: escaped = False
            elif char == 92: escaped = True
            elif char == 34: quoted = False
        elif char == 34: quoted = True
        elif char in (91, 123):
            depth += 1; count += 1
            _need(depth <= 12, 'READ_BATCH_RESOURCE_LIMIT')
        elif char in (93, 125): depth -= 1
        elif char in (44, 58): count += 1
        _need(count <= 250000, 'READ_BATCH_RESOURCE_LIMIT')


def parse_record(raw, *, limits=DEFAULT_LIMITS):
    limits = checked_limits(limits); _admit_json(raw, limits.max_record_bytes)
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result)
            result[key] = value
        return result
    def invalid(_): raise ReadBatchFormatError('READ_BATCH_FORMAT_INVALID')
    def integer(value):
        _need(len(value) <= 20)
        result = int(value); _need(-(2**63) <= result < 2**63)
        return result
    try:
        body = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_int=integer,
                          parse_float=invalid, parse_constant=invalid)
        _keys(body, 'schema_version batch_id ordinal previous_archive_digest kind body')
        result = ReadBatchRecord(**body)
        _need(record_bytes(result, limits=limits) == raw)
        return result
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        if type(exc) is ReadBatchFormatError: raise
        raise ReadBatchFormatError('READ_BATCH_FORMAT_INVALID') from None


def record_digest(record, *, limits=DEFAULT_LIMITS):
    return hashlib.sha256(_DOMAIN + record_bytes(record, limits=limits)).hexdigest()


def limits_digest(limits=DEFAULT_LIMITS):
    checked_limits(limits)
    body = {item.name:getattr(limits, item.name) for item in fields(ReadBatchLimits)}
    return hashlib.sha256(_LIMIT_DOMAIN + json.dumps(body, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
