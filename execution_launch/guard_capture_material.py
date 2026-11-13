"""Bounded original-receipt replay and inert continuous guard input material.

The real collector parses a finite in-memory sequence, never a network source.
An existing coverage receipt is checked as an external claim, not freshly issued
or authenticated. Self-consistent audit data do not prove venue completeness.
Nothing here reads a clock, owner state or file, commits, publishes or orders.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, Inexact, localcontext
import hashlib

from core.compliance.model import KST
from execution_accounts.baseline import BaselineConventions, BaselineInterval, BaselineState, risk_baseline
from execution_accounts.baseline_bridge import advance_account_baseline
from execution_accounts.collector import (CoverageEvidence, OpeningAnchor, SourceReceipt,
    TradeFeeEvidence, digest, identifier, instant)
from execution_accounts.continuous import (MAX_EVENTS, MAX_SYMBOLS, ContinuousPath, EquityEvent,
    EquityPoint, PathValuation, PriceMark, VerifiedCoverage)
from execution_accounts.model import (AccountEvidence, AccountRestrictions, BrokerOrder, CashAmount,
    CashBalance, EvidencePage, ExternalFlow, FxRate, MarketTradeDate, Position, content_digest)
from execution_accounts.provider import EvidenceError
from execution_accounts.upbit_collector import CollectionResult, collect_upbit
from execution_control.risk import Fill, RecoveryCheckpoint, account_fills
from execution_launch import account_interval as A
from execution_launch.continuous_guard import AccountCaptureInputs, ValuationInputs

MAX_CAPTURE_RECEIPTS = 2000
MAX_CAPTURE_ROWS = 100000
MAX_CAPTURE_BODY_BYTES = 8 * 1024 * 1024
MAX_CAPTURE_TOTAL_BYTES = 64 * 1024 * 1024
_DOMAIN = b'tradegen-guard-capture-material/1\x00'
_FRESH = timedelta(seconds=30)
_TREE_TYPES = frozenset((BaselineConventions, BaselineInterval, BaselineState, OpeningAnchor,
    CoverageEvidence, SourceReceipt, TradeFeeEvidence, ContinuousPath, EquityEvent, EquityPoint,
    PathValuation, PriceMark, VerifiedCoverage, AccountEvidence, AccountRestrictions, BrokerOrder,
    CashAmount, CashBalance, EvidencePage, ExternalFlow, FxRate, MarketTradeDate, Position,
    Fill, RecoveryCheckpoint, A.StagedContinuousCandidate, A.ContinuousCapture, A.ContinuousIntervalPreview))


class GuardCaptureMaterialError(EvidenceError):
    """Fixed public codes only, without private source data or exception text."""


def _need(condition, code):
    if not condition:
        raise GuardCaptureMaterialError(code)


def _admit_receipts(receipts):
    _need(type(receipts) is tuple and bool(receipts), 'GUARD_CAPTURE_INPUT_REQUIRED')
    _need(len(receipts) <= MAX_CAPTURE_RECEIPTS, 'GUARD_CAPTURE_RESOURCE_LIMIT')
    total = 0
    for receipt in receipts:
        _need(type(receipt) is SourceReceipt and type(receipt.raw_body) is bytes,
              'GUARD_CAPTURE_INPUT_REQUIRED')
        _need(0 < len(receipt.raw_body) <= MAX_CAPTURE_BODY_BYTES, 'GUARD_CAPTURE_RESOURCE_LIMIT')
        total += len(receipt.raw_body)
        _need(total <= MAX_CAPTURE_TOTAL_BYTES, 'GUARD_CAPTURE_RESOURCE_LIMIT')
        _need(type(receipt.path) is str and type(receipt.account_scope) is str
              and type(receipt.params) is tuple, 'GUARD_CAPTURE_INPUT_REQUIRED')
        _need(len(receipt.path) <= 128 and len(receipt.account_scope) <= 128
              and len(receipt.params) <= 16, 'GUARD_CAPTURE_RESOURCE_LIMIT')
        for pair in receipt.params:
            _need(type(pair) is tuple and len(pair) == 2 and all(type(value) is str for value in pair),
                  'GUARD_CAPTURE_INPUT_REQUIRED')
            _need(len(pair[0]) <= 128 and len(pair[1]) <= 65536, 'GUARD_CAPTURE_RESOURCE_LIMIT')
    return total


def _admit_tree(value):
    """Finite typed traversal before any deepcopy, JSON replay or digest work."""
    nodes, text_bytes, raw_bytes = 0, 0, 0
    def visit(item, depth):
        nonlocal nodes, text_bytes, raw_bytes
        nodes += 1
        _need(depth <= 24 and nodes <= 2000000, 'GUARD_CAPTURE_RESOURCE_LIMIT')
        kind = type(item)
        if kind in _TREE_TYPES:
            declared = fields(item)
            # Frozen dataclasses are not slotted: deepcopy would also traverse
            # undeclared attributes unless their exact inventory is checked.
            _need(type(vars(item)) is dict and len(vars(item)) == len(declared)
                  and set(vars(item)) == {field.name for field in declared},
                  'GUARD_CAPTURE_INPUT_REQUIRED')
            for field in declared:
                visit(getattr(item, field.name), depth+1)
        elif kind is tuple:
            _need(len(item) <= MAX_CAPTURE_ROWS, 'GUARD_CAPTURE_RESOURCE_LIMIT')
            for child in item:
                visit(child, depth+1)
        elif kind is str:
            _need(len(item) <= 65536, 'GUARD_CAPTURE_RESOURCE_LIMIT')
            text_bytes += len(item)
            _need(text_bytes <= 16*1024*1024, 'GUARD_CAPTURE_RESOURCE_LIMIT')
        elif kind is bytes:
            _need(len(item) <= MAX_CAPTURE_BODY_BYTES, 'GUARD_CAPTURE_RESOURCE_LIMIT')
            raw_bytes += len(item)
            _need(raw_bytes <= MAX_CAPTURE_TOTAL_BYTES, 'GUARD_CAPTURE_RESOURCE_LIMIT')
        elif kind is Decimal:
            digits = item.as_tuple()
            _need(item.is_finite() and len(digits.digits) <= 512 and -512 <= digits.exponent <= 512,
                  'GUARD_CAPTURE_INPUT_REQUIRED')
        elif kind is int:
            _need(item.bit_length() <= 256, 'GUARD_CAPTURE_RESOURCE_LIMIT')
        else:
            _need(item is None or kind in (datetime, date, bool), 'GUARD_CAPTURE_INPUT_REQUIRED')
    visit(value, 0)


def _admit_accounts(accounts):
    _need(type(accounts) is tuple and len(accounts) == 1 and type(accounts[0]) is AccountEvidence,
          'GUARD_CAPTURE_INPUT_REQUIRED')
    account = accounts[0]
    for name, limit in (('opening_cash', 1), ('balances', 1), ('positions', MAX_SYMBOLS),
                        ('fx', 1), ('pages', 3), ('trade_dates', 1)):
        value = getattr(account, name)
        _need(type(value) is tuple, 'GUARD_CAPTURE_INPUT_REQUIRED')
        _need(len(value) <= limit, 'GUARD_CAPTURE_RESOURCE_LIMIT')
    rows = 0
    for page in account.pages:
        _need(type(page) is EvidencePage and type(page.rows) is tuple, 'GUARD_CAPTURE_INPUT_REQUIRED')
        rows += len(page.rows)
        _need(rows <= MAX_CAPTURE_ROWS, 'GUARD_CAPTURE_RESOURCE_LIMIT')


def _admit_preview(preview):
    _need(type(preview) is A.ContinuousIntervalPreview and type(preview.path) is ContinuousPath
          and type(preview.coverage) is VerifiedCoverage and type(preview.interval) is BaselineInterval
          and type(preview.valuation) is PathValuation, 'GUARD_CAPTURE_INPUT_REQUIRED')
    for value, cap in ((preview.path.events, MAX_EVENTS), (preview.path.opening_marks, MAX_SYMBOLS),
            (preview.valuation.points, MAX_EVENTS+2), (preview.valuation.closing_units, MAX_SYMBOLS),
            (preview.valuation.closing_marks, MAX_SYMBOLS)):
        _need(type(value) is tuple, 'GUARD_CAPTURE_INPUT_REQUIRED')
        _need(len(value) <= cap, 'GUARD_CAPTURE_RESOURCE_LIMIT')
    _admit_accounts(preview.accounts)


def _snapshot_inputs(anchor, coverage, fees):
    _need(type(anchor) is OpeningAnchor and type(coverage) is CoverageEvidence and type(fees) is tuple,
          'GUARD_CAPTURE_INPUT_REQUIRED')
    _need(len(fees) <= MAX_CAPTURE_ROWS, 'GUARD_CAPTURE_RESOURCE_LIMIT')
    _admit_tree((anchor, coverage, fees))
    identifier(anchor.account_scope); identifier(coverage.account_scope)
    digest(anchor.source_sha256); digest(coverage.source_sha256)
    for fee in fees:
        _need(type(fee) is TradeFeeEvidence, 'GUARD_CAPTURE_INPUT_REQUIRED')
        identifier(fee.order_id); identifier(fee.fill_id); digest(fee.source_sha256)
        _need(type(fee.fee_krw) is Decimal, 'GUARD_CAPTURE_INPUT_REQUIRED')
    return deepcopy((anchor, coverage, fees))


def _retain_capture(collection):
    _need(type(collection) is CollectionResult, 'GUARD_CAPTURE_INPUT_REQUIRED')
    _admit_receipts(collection.receipts)
    _admit_accounts(collection.bundle.accounts)
    _admit_tree((collection.bundle.accounts, collection.receipts))
    # Deliberately excludes the collector's temporary midnight self-check baseline.
    return A.ContinuousCapture(accounts=deepcopy(collection.bundle.accounts),
        receipts=deepcopy(collection.receipts), manifest_sha256=collection.manifest_sha256,
        observed_at=collection.bundle.accounts[0].observed_at)


def _same(left, right, depth=0):
    """Type-sensitive value equality, including Decimal's canonical precision.

    Dataclass equality alone accepts True == 1 == Decimal('1'). Canonical hashes
    alone do not distinguish Decimal('1') from a substituted string '1'.
    """
    if depth > 32 or type(left) is not type(right):
        return False
    if is_dataclass(left) and not isinstance(left, type):
        return all(_same(getattr(left, field.name), getattr(right, field.name), depth+1)
                   for field in fields(left))
    if type(left) is tuple:
        return len(left) == len(right) and all(_same(a, b, depth+1) for a,b in zip(left,right))
    if type(left) is Decimal:
        if not left.is_finite() or not right.is_finite():
            return False
        for value in (left, right):
            parts = value.as_tuple()
            if len(parts.digits) > 512 or not -512 <= parts.exponent <= 512:
                return False
        return format(left, 'f') == format(right, 'f')
    if type(left) is datetime:
        return left.utcoffset() is not None and right.utcoffset() is not None and left == right
    if left is None or type(left) in (date, str, bytes, int, bool):
        return left == right
    return False


class _ReplaySource:
    def __init__(self, scope, receipts):
        self.account_scope, self._receipts, self._index = scope, receipts, 0

    def fetch(self, path, params):
        _need(self._index < len(self._receipts), 'GUARD_CAPTURE_RECEIPT_REPLAY_MISMATCH')
        receipt = self._receipts[self._index]
        _need(receipt.path == path and _same(receipt.params, tuple(params))
              and receipt.account_scope == self.account_scope, 'GUARD_CAPTURE_RECEIPT_REPLAY_MISMATCH')
        self._index += 1
        return receipt


class _ReplayClock:
    def __init__(self, values):
        self._values, self._index = values, 0

    def __call__(self):
        _need(self._index < len(self._values), 'GUARD_CAPTURE_CLOCK_BINDING_INVALID')
        value = self._values[self._index]
        self._index += 1
        return value


@dataclass(frozen=True, kw_only=True)
class GuardCaptureMaterial:
    account_capture: AccountCaptureInputs
    valuation_inputs: ValuationInputs
    path: ContinuousPath
    coverage: VerifiedCoverage
    interval: BaselineInterval
    capture_material_sha256: str

    @property
    def execution_ready(self):
        return False

    @property
    def source_authenticated(self):
        return False


def _replay(staged, previous, now):
    _need(type(staged) is A.StagedContinuousCandidate and type(previous) is BaselineState
          and type(staged.capture) is A.ContinuousCapture
          and type(staged.preview) is A.ContinuousIntervalPreview,
          'GUARD_CAPTURE_INPUT_REQUIRED')
    capture = staged.capture
    _admit_receipts(capture.receipts)  # before deepcopy, JSON, replay or material hashing
    _admit_accounts(capture.accounts)
    _admit_preview(staged.preview)
    _admit_tree((previous, staged))
    risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
    _need(type(staged.collection_clock) is tuple and len(staged.collection_clock) == 2,
          'GUARD_CAPTURE_CLOCK_BINDING_INVALID')
    requested, start, finish, preview_at, now = (instant(value) for value in (
        staged.collection_requested_at, *staged.collection_clock, staged.observed_at, now))
    observed, first = instant(capture.observed_at), instant(capture.receipts[0].received_at)
    _need(requested <= start <= first <= observed == finish <= preview_at <= now
          and timedelta(0) <= now-observed <= _FRESH,
          'GUARD_CAPTURE_CLOCK_BINDING_INVALID')
    anchor, coverage, fees = _snapshot_inputs(staged.anchor, staged.collection_coverage, staged.trade_fees)
    previous, staged = deepcopy(previous), deepcopy(staged)
    capture = staged.capture
    exported = risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
    boundary, midnight = A._pending_boundary(previous)
    _need(requested <= boundary, 'GUARD_CAPTURE_CLOCK_BINDING_INVALID')
    in_window = boundary-requested <= timedelta(seconds=A.BOUNDARY_LEAD_SECONDS)
    baseline = A._opening_collection_baseline(previous, boundary) if in_window and midnight else exported
    _need(content_digest(baseline) == staged.collection_baseline_sha256,
          'GUARD_CAPTURE_BASELINE_BINDING_MISMATCH')
    replay_source = _ReplaySource(previous.account_scope, capture.receipts)
    replay_clock = _ReplayClock(staged.collection_clock)
    replayed = collect_upbit(replay_source, anchor=anchor, coverage=coverage, risk_baseline=baseline,
        clock=replay_clock, trade_fees=fees, max_requests=MAX_CAPTURE_RECEIPTS, max_rows=MAX_CAPTURE_ROWS)
    _need(replay_source._index == len(capture.receipts), 'GUARD_CAPTURE_RECEIPT_REPLAY_MISMATCH')
    _need(replay_clock._index == 2, 'GUARD_CAPTURE_CLOCK_BINDING_INVALID')
    _need(_same(replayed.receipts, capture.receipts)
          and _same(replayed.bundle.accounts, capture.accounts)
          and replayed.manifest_sha256 == capture.manifest_sha256 == staged.manifest_sha256
          and _same(replayed.bundle.accounts[0].observed_at, capture.observed_at),
          'GUARD_CAPTURE_COLLECTION_REPLAY_MISMATCH')
    _need(content_digest(staged.preview.path) == staged.path_sha256,
          'GUARD_CAPTURE_PREVIEW_REPLAY_MISMATCH')
    # This branch only binds an already retained external claim. It deliberately
    # invokes no source verifier and does not refresh that claim's verified_at.
    preview = A._preview_continuous_upbit_interval(previous, replayed, staged.preview.path,
        coverage_verifier=None, now=preview_at, retained_coverage=staged.preview.coverage)
    _need(_same(preview, staged.preview), 'GUARD_CAPTURE_PREVIEW_REPLAY_MISMATCH')
    _need(not in_window or preview.interval.end == boundary, 'ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED')
    _need(timedelta(0) <= now-preview.interval.end <= _FRESH
          and now.astimezone(KST).date() == preview.interval.end.astimezone(KST).date(),
          'GUARD_CAPTURE_CLOCK_BINDING_INVALID')
    return staged, previous, replayed, preview


def _valuation_inputs(previous, preview, preview_at):
    update = advance_account_baseline(previous, preview.interval, preview.accounts, now=preview_at)
    fills = update.observation.fills
    start, end = preview.path.start, preview.path.end
    historical = tuple(fill for fill in fills if fill.executed_at < start)
    inside = tuple(fill for fill in fills if start <= fill.executed_at < end)
    _need(len(historical)+len(inside) == len(fills), 'GUARD_CAPTURE_PREVIEW_REPLAY_MISMATCH')
    prior = account_fills(historical)
    _need(prior.ok and prior.duplicate_count == 0, 'GUARD_CAPTURE_PREVIEW_REPLAY_MISMATCH')
    account = preview.accounts[0]
    cash = account.opening_cash[0].amount + sum((amount for venue, scope, amount
        in prior.cash_deltas_by_account_krw if venue == 'upbit' and scope == previous.account_scope), Decimal(0))
    flows = {}
    for page in account.pages:
        if page.kind != 'flows':
            continue
        for flow in page.rows:
            _need(flow.effective_at < start and flow.currency == 'KRW'
                  and flow.kind in ('deposit', 'withdrawal')
                  and (flow.flow_id not in flows or _same(flows[flow.flow_id], flow)),
                  'GUARD_CAPTURE_PREVIEW_REPLAY_MISMATCH')
            flows[flow.flow_id] = flow
    cash += sum((flow.amount if flow.kind == 'deposit' else -flow.amount for flow in flows.values()), Decimal(0))
    return ValuationInputs(opening_cash_krw=cash,
        opening_units=tuple(sorted((row[3], row[4]) for row in prior.inventory if row[4] != 0)),
        historical_fills=historical, interval_fills=inside)


def prepare_guard_capture_material(staged, previous, *, now):
    """Reparse retained source bytes and derive exact, non-operational inputs.

    A self-consistent constructed packet may pass this audit. No source/owner
    authentication is manufactured; consumers cannot treat the result as a live
    account provider, authenticated coverage, guard receipt or approval.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            staged, previous, collection, preview = _replay(staged, previous, now)
            capture = AccountCaptureInputs(manifest_sha256=collection.manifest_sha256,
                captured_accounts=collection.bundle.accounts, endpoint_accounts=preview.accounts,
                first_received_at=collection.receipts[0].received_at)
            inputs = _valuation_inputs(previous, preview, staged.observed_at)
            receipts = tuple((receipt.path, receipt.params, receipt.account_scope, receipt.received_at,
                receipt.server_time, len(receipt.raw_body), receipt.sha256) for receipt in collection.receipts)
            body = (staged.anchor, staged.collection_coverage, staged.trade_fees,
                staged.collection_requested_at, staged.collection_clock, staged.collection_baseline_sha256,
                staged.observed_at, receipts, capture, inputs, preview.path, preview.coverage, preview.interval)
            material_sha = hashlib.sha256(_DOMAIN+content_digest(body).encode('ascii')).hexdigest()
            return GuardCaptureMaterial(account_capture=deepcopy(capture), valuation_inputs=deepcopy(inputs),
                path=deepcopy(preview.path), coverage=deepcopy(preview.coverage), interval=deepcopy(preview.interval),
                capture_material_sha256=material_sha)
    except EvidenceError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, IndexError, ArithmeticError, OverflowError, RecursionError):
        raise GuardCaptureMaterialError('GUARD_CAPTURE_EVIDENCE_REFUSED') from None
