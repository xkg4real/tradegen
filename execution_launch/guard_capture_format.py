"""Closed, lossless capture-packet codec; no source or current-use authority.

The predecessor is checked for integrity against an explicit expected digest.
That digest is not an independently retained current head. Retained coverage is
an archived claim, never a fresh verifier issuance. No files, clocks, source
callbacks, baseline advancement, publication or trading occur here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from types import MappingProxyType

from execution_accounts import baseline as B
from execution_accounts import collector as C
from execution_accounts import continuous as P
from execution_accounts import model as M
from execution_control.risk import Fill, RecoveryCheckpoint
from execution_launch import account_interval as A

SCHEMA_VERSION = 1
REPLAY_REVISION = 'guard-capture-material-v1'
PACKET_DOMAIN = b'tradegen-continuous-capture-packet/1\n'
_SHA = re.compile(r'[0-9a-f]{64}')


class GuardCaptureFormatError(ValueError):
    """Fixed diagnostic codes only; no private values or source exception text."""


def _need(ok, code='CAPTURE_FORMAT_INVALID'):
    if not ok:
        raise GuardCaptureFormatError(code)


def _hash(value):
    return type(value) is str and len(value) == 64 and _SHA.fullmatch(value) is not None


@dataclass(frozen=True, kw_only=True, slots=True)
class CaptureFormatLimits:
    max_packet_bytes: int = 64 * 1024 * 1024
    max_baseline_bytes: int = 65536
    max_receipts: int = 2000
    max_receipt_bytes: int = 8 * 1024 * 1024
    max_total_receipt_bytes: int = 64 * 1024 * 1024
    max_total_bytes: int = 128 * 1024 * 1024 + 65536
    max_nodes: int = 2000000
    max_text_bytes: int = 16 * 1024 * 1024
    max_depth: int = 24
    max_rows: int = 100000

    def __post_init__(self):
        for name, maximum in _LIMIT_CEILINGS:
            value = getattr(self, name)
            _need(type(value) is int and 0 < value <= maximum, 'CAPTURE_LIMITS_INVALID')


_LIMIT_CEILINGS = (
    ('max_packet_bytes', 64*1024*1024), ('max_baseline_bytes', 65536),
    ('max_receipts', 2000), ('max_receipt_bytes', 8*1024*1024),
    ('max_total_receipt_bytes', 64*1024*1024), ('max_total_bytes', 128*1024*1024+65536),
    ('max_nodes', 2000000), ('max_text_bytes', 16*1024*1024), ('max_depth', 24),
    ('max_rows', 100000))
DEFAULT_LIMITS = CaptureFormatLimits()


def _limits(value):
    try:
        _need(type(value) is CaptureFormatLimits, 'CAPTURE_LIMITS_INVALID')
        value.__post_init__()
    except (AttributeError, TypeError):
        raise GuardCaptureFormatError('CAPTURE_LIMITS_INVALID') from None
    return value


@dataclass(frozen=True, kw_only=True, slots=True)
class CapturePayload:
    logical_id: str
    original_name: str
    byte_count: int
    sha256: str


@dataclass(frozen=True, kw_only=True, slots=True)
class EncodedCaptureArchive:
    packet_sha256: str
    previous_state_sha256: str
    path_sha256: str
    manifest_sha256: str
    observed_at: datetime
    inventory: tuple[CapturePayload, ...]
    payloads: Mapping[str, bytes] = field(repr=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class RetainedCapturePacket:
    packet_sha256: str
    previous_state_sha256: str
    staged: A.StagedContinuousCandidate = field(repr=False)
    previous: B.BaselineState = field(repr=False)
    inventory: tuple[CapturePayload, ...]

    @property
    def source_authenticated(self):
        return False

    @property
    def current_freshness_verified(self):
        return False

    @property
    def guard_committed(self):
        return False

    @property
    def execution_ready(self):
        return False


# This registry is code-owned, never resolved from Python module/class strings.
# Every field and nested container kind is explicit; dataclass normalization is
# additionally rejected by an exact post-construction wire comparison.
def _optional(spec):
    return ('optional', spec)


def _tuple(spec, maximum=100000):
    return ('tuple', spec, maximum)


def _pair(left, right):
    return ('pair', left, right)


_SCHEMAS = {
    'BaselineConventions': (B.BaselineConventions, {
        'daily_loss': 'str', 'external_flows': 'str', 'max_interval_seconds': 'int',
        'recovery_cutoff_seconds': _optional('int')}),
    'RecoveryCheckpoint': (RecoveryCheckpoint, {'cutoff_at': 'datetime', 'equity_krw': 'Decimal', 'source_sha256': 'str'}),
    'BaselineState': (B.BaselineState, {
        'schema_version': 'int', 'account_scope': 'str', 'conventions': 'BaselineConventions',
        'first_trading_day': 'date', 'asof': 'datetime', 'sequence': 'int', 'equity_krw': 'Decimal',
        'day_start_equity': 'Decimal', 'high_watermark': 'Decimal', 'observed_daily_loss': 'Decimal',
        'realized_net_total_krw': 'Decimal', 'day_open_realized_net_total_krw': 'Decimal',
        'previous_day_realized_net_krw': _optional('Decimal'), 'approved_effective_floor': _optional('Decimal'),
        'anchor_sha256': 'str', 'previous_state_digest': 'str', 'last_interval_digest': 'str',
        'state_digest': 'str', 'recovery_checkpoint': _optional('RecoveryCheckpoint')}),
    'BaselineInterval': (B.BaselineInterval, {
        'account_scope': 'str', 'sequence': 'int', 'previous_state_digest': 'str', 'start': 'datetime',
        'end': 'datetime', 'equity_krw': 'Decimal', 'minimum_equity_krw': 'Decimal', 'maximum_equity_krw': 'Decimal',
        'realized_net_total_krw': 'Decimal', 'gross_external_inflows_krw': _optional('Decimal'),
        'gross_external_outflows_krw': _optional('Decimal'), 'source_sha256': 'str', 'coverage_sha256': 'str'}),
    'OpeningAnchor': (C.OpeningAnchor, {'account_scope': 'str', 'origin': 'datetime', 'cash_krw': 'Decimal',
        'source_sha256': 'str', 'inventory_and_open_orders': 'str'}),
    'CoverageEvidence': (C.CoverageEvidence, {'account_scope': 'str', 'source_sha256': 'str',
        'history_from': 'datetime', 'history_through': 'datetime', 'quiescent_from': 'datetime',
        'quiescent_until': 'datetime', 'identity_binding': 'str', 'history_retention': 'str',
        'transfer_scope': 'str', 'account_mode': 'str'}),
    'TradeFeeEvidence': (C.TradeFeeEvidence, {'order_id': 'str', 'fill_id': 'str', 'fee_krw': 'Decimal', 'source_sha256': 'str'}),
    'SourceReceipt': (C.SourceReceipt, {'path': 'str', 'params': _tuple(_pair('str', 'str'), 16),
        'account_scope': 'str', 'received_at': 'datetime', 'server_time': 'datetime', 'raw_body': 'raw', 'sha256': 'str'}),
    'CashAmount': (M.CashAmount, {'currency': 'str', 'amount': 'Decimal'}),
    'CashBalance': (M.CashBalance, {'currency': 'str', 'total': 'Decimal', 'settled': 'Decimal'}),
    'FxRate': (M.FxRate, {'currency': 'str', 'krw': 'Decimal', 'asof': 'datetime', 'source_sha256': 'str'}),
    'Position': (M.Position, {'market': 'str', 'symbol': 'str', 'base_currency': 'str', 'quote_currency': 'str',
        'units': 'Decimal', 'price': 'Decimal', 'asof': 'datetime', 'unlisted': _optional('bool')}),
    'ExternalFlow': (M.ExternalFlow, {'flow_id': 'str', 'currency': 'str', 'kind': 'str', 'amount': 'Decimal', 'effective_at': 'datetime'}),
    'BrokerOrder': (M.BrokerOrder, {'client_id': 'str', 'order_id': 'str', 'market': 'str', 'symbol': 'str',
        'side': 'str', 'quote_currency': 'str', 'quantity': 'Decimal', 'filled_quantity': 'Decimal',
        'remaining_quantity': 'Decimal', 'limit_price': 'Decimal', 'reserved_cash': 'Decimal', 'status': 'str',
        'cancelable_quantity': _optional('Decimal'), 'order_date': 'str', 'broker_org_id': 'str'}),
    'Fill': (Fill, {'venue': 'str', 'account_scope': 'str', 'order_id': 'str', 'fill_id': 'str', 'market': 'str',
        'symbol': 'str', 'side': 'str', 'quantity': 'Decimal', 'price': 'Decimal', 'quote_currency': 'str',
        'quote_krw': _optional('Decimal'), 'fee_amount': _optional('Decimal'), 'fee_currency': _optional('str'),
        'executed_at': 'datetime', 'base_currency': 'str', 'order_date': 'str', 'broker_org_id': 'str'}),
    'EvidencePage': (M.EvidencePage, {'kind': 'str', 'cursor': _optional('str'), 'next_cursor': _optional('str'),
        'start': 'datetime', 'end': 'datetime', 'rows': _tuple(('union', 'Fill', 'BrokerOrder', 'ExternalFlow')),
        'source_sha256': 'str', 'page_sha256': 'str'}),
    'AccountRestrictions': (M.AccountRestrictions, {'cash_mode': 'str', 'borrowing_enabled': 'bool',
        'auto_loan': 'bool', 'liabilities': _tuple('CashAmount'), 'asof': 'datetime', 'source_sha256': 'str'}),
    'MarketTradeDate': (M.MarketTradeDate, {'market': 'str', 'trade_date': 'str', 'asof': 'datetime', 'source_sha256': 'str'}),
    'AccountEvidence': (M.AccountEvidence, {'venue': 'str', 'account_scope': 'str', 'execution_quote': 'str',
        'origin': 'datetime', 'opening_cash': _tuple('CashAmount', 1), 'opening_source_sha256': 'str',
        'balances': _tuple('CashBalance', 1), 'positions': _tuple('Position', 64), 'fx': _tuple('FxRate', 1),
        'pages': _tuple('EvidencePage', 3), 'restrictions': 'AccountRestrictions', 'observed_at': 'datetime',
        'server_time': 'datetime', 'trade_dates': _tuple('MarketTradeDate', 1)}),
    'PriceMark': (P.PriceMark, {'symbol': 'str', 'price': 'Decimal', 'asof': 'datetime'}),
    'EquityEvent': (P.EquityEvent, {'sequence': 'int', 'at': 'datetime', 'received_at': 'datetime',
        'source_sha256': 'str', 'mark': _optional('PriceMark'), 'fill': _optional('Fill')}),
    'ContinuousPath': (P.ContinuousPath, {'account_scope': 'str', 'stream_epoch': 'str', 'previous_state_digest': 'str',
        'start': 'datetime', 'end': 'datetime', 'opening_marks': _tuple('PriceMark', 64), 'first_sequence': 'int',
        'events': _tuple('EquityEvent', 20000), 'watermark_sequence': 'int', 'watermark_received_at': 'datetime',
        'watermark_source_sha256': 'str'}),
    'VerifiedCoverage': (P.VerifiedCoverage, {'request_sha256': 'str', 'contract': 'str', 'authority_sha256': 'str',
        'source_proof_sha256': 'str', 'verified_at': 'datetime'}),
    'EquityPoint': (P.EquityPoint, {'at': 'datetime', 'equity_krw': 'Decimal', 'realized_net_total_krw': 'Decimal'}),
    'PathValuation': (P.PathValuation, {'equity_krw': 'Decimal', 'minimum_equity_krw': 'Decimal',
        'maximum_equity_krw': 'Decimal', 'realized_net_total_krw': 'Decimal', 'closing_cash_krw': 'Decimal',
        'closing_units': _tuple(_pair('str', 'Decimal'), 64), 'closing_marks': _tuple('PriceMark', 64),
        'points': _tuple('EquityPoint', 20002)}),
    'ContinuousCapture': (A.ContinuousCapture, {'accounts': _tuple('AccountEvidence', 1),
        'receipts': _tuple('SourceReceipt', 2000), 'manifest_sha256': 'str', 'observed_at': 'datetime'}),
    'ContinuousIntervalPreview': (A.ContinuousIntervalPreview, {'interval': 'BaselineInterval',
        'accounts': _tuple('AccountEvidence', 1), 'path': 'ContinuousPath', 'coverage': 'VerifiedCoverage', 'valuation': 'PathValuation'}),
    'StagedContinuousCandidate': (A.StagedContinuousCandidate, {'preview': 'ContinuousIntervalPreview',
        'path_sha256': 'str', 'manifest_sha256': 'str', 'observed_at': 'datetime', 'capture': 'ContinuousCapture',
        'anchor': 'OpeningAnchor', 'collection_coverage': 'CoverageEvidence', 'trade_fees': _tuple('TradeFeeEvidence'),
        'collection_requested_at': 'datetime', 'collection_clock': _pair('datetime', 'datetime'), 'collection_baseline_sha256': 'str'})}


def _tag(kind, value):
    return {'$': kind, 'v': value}


def _untag(value, expected):
    _need(type(value) is dict and len(value) == 2 and set(value) == {'$', 'v'} and type(value['$']) is str and value['$'] == expected)
    return value['v']


class _Codec:
    def __init__(self, limits, payloads):
        self.limits, self.payloads = limits, payloads
        self.nodes, self.text, self.receipt_index = 0, 0, 0

    def _visit(self, depth):
        self.nodes += 1
        _need(depth <= self.limits.max_depth and self.nodes <= self.limits.max_nodes, 'CAPTURE_RESOURCE_LIMIT')

    def _text(self, value):
        _need(type(value) is str)
        _need(len(value) <= 65536, 'CAPTURE_RESOURCE_LIMIT')
        # UTF-8 count is bounded before encoding any possibly large string.
        encoded = value.encode('utf-8')
        self.text += len(encoded)
        _need(self.text <= self.limits.max_text_bytes, 'CAPTURE_RESOURCE_LIMIT')
        return value

    def value(self, item, spec, *, decode=False, depth=0, raw_id=None):
        self._visit(depth)
        if type(spec) is tuple:
            kind = spec[0]
            if kind == 'optional':
                return None if item is None else self.value(item, spec[1], decode=decode, depth=depth+1)
            if kind == 'union':
                choices = spec[1:]
                name = item.get('$') if decode and type(item) is dict else next(
                    (name for name in choices if type(item) is _SCHEMAS[name][0]), None)
                _need(type(name) is str and name in choices)
                return self.value(item, name, decode=decode, depth=depth+1)
            values = _untag(item, 'tuple') if decode else item
            _need(type(values) is (list if decode else tuple))
            maximum = min(spec[2], self.limits.max_rows) if kind == 'tuple' else 2
            _need(len(values) <= maximum, 'CAPTURE_RESOURCE_LIMIT')
            if kind == 'pair':
                _need(len(values) == 2)
            children = [self.value(value, spec[1] if kind == 'tuple' else spec[index+1],
                decode=decode, depth=depth+1) for index, value in enumerate(values)]
            return tuple(children) if decode else _tag('tuple', children)
        if spec == 'str':
            return self._text(item)
        if spec in ('int', 'bool'):
            _need(type(item) is (int if spec == 'int' else bool))
            _need(spec == 'bool' or item.bit_length() <= 256, 'CAPTURE_RESOURCE_LIMIT')
            return item
        if spec == 'Decimal':
            if decode:
                parts = _untag(item, 'decimal')
                _need(type(parts) is list and len(parts) == 3 and type(parts[0]) is int and parts[0] in (0, 1)
                      and type(parts[1]) is str and 1 <= len(parts[1]) <= 512
                      and parts[1].isascii() and parts[1].isdigit() and type(parts[2]) is int
                      and -512 <= parts[2] <= 512)
                value = Decimal((parts[0], tuple(int(d) for d in parts[1]), parts[2]))
                _need(value.as_tuple().digits == tuple(int(d) for d in parts[1]))
                return value
            _need(type(item) is Decimal and item.is_finite())
            parts = item.as_tuple()
            _need(len(parts.digits) <= 512 and -512 <= parts.exponent <= 512)
            return _tag('decimal', [parts.sign, ''.join(str(d) for d in parts.digits), parts.exponent])
        if spec in ('datetime', 'date'):
            if decode:
                raw = _untag(item, spec)
                _need(type(raw) is str and len(raw) <= 40)
                value = datetime.fromisoformat(raw) if spec == 'datetime' else date.fromisoformat(raw)
                _need(spec != 'datetime' or value.utcoffset() is not None)
                _need((value.astimezone(timezone.utc).isoformat() if spec == 'datetime' else value.isoformat()) == raw)
                return value
            _need(type(item) is (datetime if spec == 'datetime' else date))
            _need(spec != 'datetime' or item.utcoffset() is not None)
            return _tag(spec, item.astimezone(timezone.utc).isoformat() if spec == 'datetime' else item.isoformat())
        if spec == 'raw':
            _need(type(raw_id) is str and raw_id in self.payloads)
            if decode:
                _need(_untag(item, 'receipt') == raw_id)
                return self.payloads[raw_id]
            _need(type(item) is bytes and item == self.payloads[raw_id], 'CAPTURE_PAYLOAD_MISMATCH')
            return _tag('receipt', raw_id)
        cls, schema = _SCHEMAS[spec]
        if decode:
            values = _untag(item, spec)
            _need(type(values) is dict and len(values) == len(schema) and set(values) == set(schema))
        else:
            _need(type(item) is cls and type(vars(item)) is dict and len(vars(item)) == len(schema)
                  and set(vars(item)) == set(schema))
            values = vars(item)
        if spec == 'AccountEvidence':
            pages = _untag(values['pages'], 'tuple') if decode else values['pages']
            _need(type(pages) is (list if decode else tuple))
            _need(len(pages) <= 3, 'CAPTURE_RESOURCE_LIMIT')
            rows = 0
            for page in pages:
                if decode:
                    body = _untag(page, 'EvidencePage')
                    _need(type(body) is dict and 'rows' in body)
                    contents = _untag(body['rows'], 'tuple')
                else:
                    _need(type(page) is M.EvidencePage)
                    contents = page.rows
                _need(type(contents) is (list if decode else tuple))
                rows += len(contents)
                _need(rows <= self.limits.max_rows, 'CAPTURE_RESOURCE_LIMIT')
        if spec == 'SourceReceipt':
            _need(type(values['path']) is str and type(values['account_scope']) is str)
            _need(len(values['path']) <= 128 and len(values['account_scope']) <= 128,
                  'CAPTURE_RESOURCE_LIMIT')
            params = _untag(values['params'], 'tuple') if decode else values['params']
            _need(type(params) is (list if decode else tuple))
            _need(len(params) <= 16, 'CAPTURE_RESOURCE_LIMIT')
            for pair in params:
                pair = _untag(pair, 'tuple') if decode else pair
                _need(type(pair) is (list if decode else tuple) and len(pair) == 2
                      and type(pair[0]) is str and type(pair[1]) is str)
                _need(len(pair[0]) <= 128 and len(pair[1]) <= 65536, 'CAPTURE_RESOURCE_LIMIT')
            raw_id = f'receipt-{self.receipt_index:06d}'
            self.receipt_index += 1
            _need(self.receipt_index <= self.limits.max_receipts, 'CAPTURE_RESOURCE_LIMIT')
        result = {name: self.value(values[name], child, decode=decode, depth=depth+1, raw_id=raw_id)
                  for name, child in schema.items()}
        return cls(**result) if decode else _tag(spec, result)


def _json_bytes(value, maximum):
    chunks, size = [], 0
    for chunk in json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).iterencode(value):
        raw = chunk.encode('ascii')
        size += len(raw)
        _need(size <= maximum, 'CAPTURE_RESOURCE_LIMIT')
        chunks.append(raw)
    return b''.join(chunks)


def _scan(raw, limits):
    # Admission before json.loads: semantic wrappers can triple tree depth.
    _need(type(raw) is bytes and 0 < len(raw) <= limits.max_packet_bytes, 'CAPTURE_RESOURCE_LIMIT')
    depth, tokens, quoted, escaped, scalar = 0, 0, False, False, 0
    for byte in raw:
        if quoted:
            scalar += 1
            _need(scalar <= 12*65536+2, 'CAPTURE_RESOURCE_LIMIT')
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted, scalar = True, 0
            tokens += 1
        elif byte in (123, 91):
            depth += 1
            tokens += 1
            _need(depth <= 3*limits.max_depth+8, 'CAPTURE_RESOURCE_LIMIT')
        elif byte in (125, 93):
            depth -= 1
            _need(depth >= 0)
        elif byte in (44, 58):
            tokens += 1
        _need(tokens <= 12*limits.max_nodes+64, 'CAPTURE_RESOURCE_LIMIT')
    _need(not quoted and depth == 0)


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result)
        result[key] = value
    return result


def _integer(raw):
    _need(len(raw) <= 79, 'CAPTURE_RESOURCE_LIMIT')
    value = int(raw)
    _need(value.bit_length() <= 256, 'CAPTURE_RESOURCE_LIMIT')
    return value


def _bad_number(_raw):
    raise GuardCaptureFormatError('CAPTURE_FORMAT_INVALID')


def _name(logical):
    return logical+'.json' if logical in ('baseline', 'packet') else logical+'.bin'


def _inventory(payloads):
    return tuple(CapturePayload(logical_id=key, original_name=_name(key), byte_count=len(payloads[key]),
        sha256=hashlib.sha256(payloads[key]).hexdigest()) for key in sorted(payloads))


def _row(value):
    return {'logical_id': value.logical_id, 'original_name': value.original_name,
            'byte_count': value.byte_count, 'sha256': value.sha256}


def _payloads(values, limits, *, packet_required):
    _need(isinstance(values, Mapping))
    _need(len(values) <= limits.max_receipts+2, 'CAPTURE_RESOURCE_LIMIT')
    copied = {}
    total, receipt_total = 0, 0
    for index, (key, raw) in enumerate(values.items(), 1):
        _need(index <= limits.max_receipts+2, 'CAPTURE_RESOURCE_LIMIT')
        _need(type(key) is str and len(key) <= 32 and type(raw) is bytes)
        _need(key not in copied)
        if key == 'packet':
            maximum = limits.max_packet_bytes
        elif key == 'baseline':
            maximum = limits.max_baseline_bytes
        else:
            _need(re.fullmatch(r'receipt-[0-9]{6}', key) is not None)
            maximum = limits.max_receipt_bytes
            receipt_total += len(raw)
            _need(receipt_total <= limits.max_total_receipt_bytes, 'CAPTURE_RESOURCE_LIMIT')
        _need(0 < len(raw) <= maximum, 'CAPTURE_RESOURCE_LIMIT')
        total += len(raw)
        _need(total <= limits.max_total_bytes, 'CAPTURE_RESOURCE_LIMIT')
        copied[key] = raw
    receipt_count = len(copied)-(2 if packet_required else 1)
    _need(1 <= receipt_count <= limits.max_receipts, 'CAPTURE_RESOURCE_LIMIT')
    expected = {'baseline'} | ({'packet'} if packet_required else set()) | {
        f'receipt-{index:06d}' for index in range(receipt_count)}
    _need(set(copied) == expected, 'CAPTURE_PAYLOAD_MISMATCH')
    return copied


def _root(previous, staged, payloads, limits):
    codec = _Codec(limits, payloads)
    encoded_previous = codec.value(previous, 'BaselineState')
    encoded_stage = codec.value(staged, 'StagedContinuousCandidate')
    _need(codec.receipt_index == len(payloads)-1, 'CAPTURE_PAYLOAD_MISMATCH')
    _need(_hash(previous.state_digest) and _hash(staged.path_sha256) and _hash(staged.manifest_sha256))
    return {'schema_version': SCHEMA_VERSION, 'replay_revision': REPLAY_REVISION,
        'previous_state_sha256': previous.state_digest, 'previous': encoded_previous,
        'staged': encoded_stage, 'payloads': [_row(value) for value in _inventory(payloads)]}


def _baseline(previous, raw, expected, limits):
    _need(type(previous) is B.BaselineState and _hash(expected), 'CAPTURE_BASELINE_MISMATCH')
    _need(previous.state_digest == expected, 'CAPTURE_BASELINE_MISMATCH')
    _need(type(raw) is bytes and 0 < len(raw) <= limits.max_baseline_bytes, 'CAPTURE_RESOURCE_LIMIT')
    try:
        restored = B.restore_state(raw, expected_head=expected)
        _need(B.state_json(previous).encode('utf-8') == raw, 'CAPTURE_BASELINE_MISMATCH')
        B.risk_baseline(previous, now=previous.asof, expected_head=restored.state_digest)
    except B.BaselineError:
        raise GuardCaptureFormatError('CAPTURE_BASELINE_MISMATCH') from None


def build_capture_archive(staged, previous, *, limits=DEFAULT_LIMITS):
    """Represent and detach originals; do not run/issue a successful material audit."""
    limits = _limits(limits)
    try:
        _need(type(staged) is A.StagedContinuousCandidate and type(previous) is B.BaselineState)
        _need(type(staged.capture) is A.ContinuousCapture and type(staged.capture.receipts) is tuple)
        receipts = staged.capture.receipts
        _need(1 <= len(receipts) <= limits.max_receipts, 'CAPTURE_RESOURCE_LIMIT')
        values, total = {}, 0
        for index, receipt in enumerate(receipts):
            _need(type(receipt) is C.SourceReceipt and type(receipt.raw_body) is bytes)
            raw = receipt.raw_body
            _need(0 < len(raw) <= limits.max_receipt_bytes, 'CAPTURE_RESOURCE_LIMIT')
            total += len(raw)
            _need(total <= limits.max_total_receipt_bytes, 'CAPTURE_RESOURCE_LIMIT')
            values[f'receipt-{index:06d}'] = raw
        # Closed typed admission precedes the legacy baseline serializer, whose
        # json output is not itself a typed admission mechanism.
        _Codec(limits, values).value(previous, 'BaselineState')
        values['baseline'] = B.state_json(previous).encode('utf-8')
        values = _payloads(values, limits, packet_required=False)
        document = _root(previous, staged, values, limits)
        _baseline(previous, values['baseline'], previous.state_digest, limits)
        values['packet'] = _json_bytes(document, limits.max_packet_bytes)
        # Actual decoder enforces constructor non-repair and the complete map.
        retained = parse_capture_archive(values, expected_previous_state_sha256=previous.state_digest, limits=limits)
        return EncodedCaptureArchive(packet_sha256=retained.packet_sha256,
            previous_state_sha256=retained.previous_state_sha256, path_sha256=retained.staged.path_sha256,
            manifest_sha256=retained.staged.manifest_sha256, observed_at=retained.staged.observed_at,
            inventory=retained.inventory, payloads=MappingProxyType(dict(values)))
    except GuardCaptureFormatError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError, OverflowError, RecursionError):
        raise GuardCaptureFormatError('CAPTURE_FORMAT_INVALID') from None


def parse_capture_archive(payloads, *, expected_previous_state_sha256, limits=DEFAULT_LIMITS):
    """Decode an entire exact packet; self hashes never authenticate its issuer."""
    limits = _limits(limits)
    try:
        _need(_hash(expected_previous_state_sha256), 'CAPTURE_BASELINE_MISMATCH')
        values = _payloads(payloads, limits, packet_required=True)
        raw = values.pop('packet')
        _scan(raw, limits)
        body = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_int=_integer, parse_float=_bad_number, parse_constant=_bad_number)
        _need(type(body) is dict and len(body) == 6 and set(body) == {'schema_version', 'replay_revision',
            'previous_state_sha256', 'previous', 'staged', 'payloads'})
        _need(type(body['schema_version']) is int and body['schema_version'] == SCHEMA_VERSION
              and type(body['replay_revision']) is str and body['replay_revision'] == REPLAY_REVISION)
        _need(type(body['previous_state_sha256']) is str
              and body['previous_state_sha256'] == expected_previous_state_sha256, 'CAPTURE_BASELINE_MISMATCH')
        _need(type(body['payloads']) is list and len(body['payloads']) == len(values), 'CAPTURE_PAYLOAD_MISMATCH')
        # Canonical byte equality is type-sensitive, unlike Python dict equality.
        inventory = [_row(value) for value in _inventory(values)]
        _need(_json_bytes(body['payloads'], limits.max_packet_bytes) == _json_bytes(inventory, limits.max_packet_bytes),
              'CAPTURE_PAYLOAD_MISMATCH')
        codec = _Codec(limits, values)
        previous = codec.value(body['previous'], 'BaselineState', decode=True)
        staged = codec.value(body['staged'], 'StagedContinuousCandidate', decode=True)
        _need(codec.receipt_index == len(values)-1, 'CAPTURE_PAYLOAD_MISMATCH')
        _baseline(previous, values['baseline'], expected_previous_state_sha256, limits)
        _need(_json_bytes(_root(previous, staged, values, limits), limits.max_packet_bytes) == raw)
        values['packet'] = raw
        return RetainedCapturePacket(packet_sha256=hashlib.sha256(PACKET_DOMAIN+raw).hexdigest(),
            previous_state_sha256=expected_previous_state_sha256, staged=staged, previous=previous,
            inventory=_inventory(values))
    except GuardCaptureFormatError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, ArithmeticError, OverflowError, RecursionError):
        raise GuardCaptureFormatError('CAPTURE_FORMAT_INVALID') from None
