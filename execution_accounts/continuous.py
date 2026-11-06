"""Continuous equity-path candidates, independently verified before baseline use.

The recorder detects *local* gaps and preserves an exact event sequence. It does
not prove that a venue sent every valuation change. In particular Upbit's book
snapshots, trade IDs, a heartbeat, and our own sequence numbers are not a
gap-free venue sequence. No production coverage verifier is supplied here.

The injected verifier is a separately reviewed trusted adapter, as are the
account source and trusted baseline head. It must authenticate the opening
marks, every mark/fill and their common ordering, the final source watermark,
and the absence of omitted account changes. A digest only binds its conclusion
to this precise candidate and account capture. A payload's ``complete`` flag
or an arbitrary truthy return value is never accepted as that conclusion.

No network, credential, owner state, signing or order operation occurs here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, DecimalException, Inexact, localcontext
import json
import os
from pathlib import Path
import re
import stat
from threading import Lock

from core.isolation import checked_target, state_root
from execution_accounts.model import canonical, content_digest
from execution_control.risk import Fill, account_fills

_ID = re.compile(r"[A-Za-z0-9_.:/-]{1,128}")
_SHA = re.compile(r"[0-9a-f]{64}")
_SYMBOL = re.compile(r"KRW-[A-Z][A-Z0-9]{0,11}")
_ZERO = Decimal(0)
MAX_EVENTS = 20000
MAX_SYMBOLS = 64
MAX_INTERVAL_FILLS = 128
MAX_HISTORY_FILLS = 20000
MAX_DURATION = timedelta(seconds=30)
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
COVERAGE_CONTRACT = "complete-ordered-account-marks-and-fills-v1"


class ContinuousEvidenceError(ValueError):
    """Fixed codes only; never echo source exceptions or private account data."""


def _require(ok, code):
    if not ok:
        raise ContinuousEvidenceError(code)


def _instant(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None
                 and 2 <= value.year <= 9998, "CONTINUOUS_AWARE_TIME_REQUIRED")
        return value.astimezone(timezone.utc)
    except Exception:
        raise ContinuousEvidenceError("CONTINUOUS_AWARE_TIME_REQUIRED") from None


def _hash(value):
    _require(type(value) is str and _SHA.fullmatch(value) is not None, "CONTINUOUS_DIGEST_REQUIRED")


def _id(value):
    _require(type(value) is str and _ID.fullmatch(value) is not None, "CONTINUOUS_ID_REQUIRED")


def _number(value, *, positive=False):
    _require(type(value) is Decimal and value.is_finite() and len(value.as_tuple().digits) <= 60
             and -40 <= value.as_tuple().exponent <= 40
             and (value > 0 if positive else value >= 0), "CONTINUOUS_EXACT_NUMBER_REQUIRED")


@dataclass(frozen=True, kw_only=True)
class PriceMark:
    symbol: str
    price: Decimal
    asof: datetime


@dataclass(frozen=True, kw_only=True)
class EquityEvent:
    sequence: int
    at: datetime
    received_at: datetime
    source_sha256: str
    mark: PriceMark | None = None
    fill: Fill | None = None


@dataclass(frozen=True, kw_only=True)
class ContinuousPath:
    account_scope: str
    stream_epoch: str
    previous_state_digest: str
    start: datetime
    end: datetime
    opening_marks: tuple[PriceMark, ...]
    first_sequence: int
    events: tuple[EquityEvent, ...]
    watermark_sequence: int
    watermark_received_at: datetime
    watermark_source_sha256: str


@dataclass(frozen=True, kw_only=True)
class CoverageRequest:
    """Exact challenge to the independently reviewed source verifier."""
    path_sha256: str
    account_capture_sha256: str
    account_scope: str
    stream_epoch: str
    start: datetime
    end: datetime
    first_sequence: int
    watermark_sequence: int


@dataclass(frozen=True, kw_only=True)
class VerifiedCoverage:
    """A verifier's receipt, never an input accepted directly from a user file."""
    request_sha256: str
    contract: str
    authority_sha256: str
    source_proof_sha256: str
    verified_at: datetime


@dataclass(frozen=True, kw_only=True)
class EquityPoint:
    at: datetime
    equity_krw: Decimal
    realized_net_total_krw: Decimal


@dataclass(frozen=True, kw_only=True)
class PathValuation:
    equity_krw: Decimal
    minimum_equity_krw: Decimal
    maximum_equity_krw: Decimal
    realized_net_total_krw: Decimal
    closing_cash_krw: Decimal
    closing_units: tuple[tuple[str, Decimal], ...]
    closing_marks: tuple[PriceMark, ...]
    points: tuple[EquityPoint, ...]


def _mark(value):
    _require(type(value) is PriceMark and type(value.symbol) is str
             and _SYMBOL.fullmatch(value.symbol) is not None, "CONTINUOUS_MARK_INVALID")
    _number(value.price, positive=True)
    _instant(value.asof)


def _event(value, *, scope, sequence, start, previous_at, previous_received, symbols):
    _require(type(value) is EquityEvent and type(value.sequence) is int
             and 0 <= value.sequence < 2**63 and value.sequence == sequence, "CONTINUOUS_SEQUENCE_GAP")
    _instant(value.at); _instant(value.received_at); _hash(value.source_sha256)
    _require(start <= value.at and previous_at <= value.at <= value.received_at
             and previous_received <= value.received_at
             and value.received_at - start <= MAX_DURATION, "CONTINUOUS_TIME_GAP_OR_ROLLBACK")
    _require((value.mark is None) != (value.fill is None), "CONTINUOUS_EVENT_KIND_INVALID")
    if value.mark is not None:
        _mark(value.mark)
        _require(value.mark.symbol in symbols and value.mark.asof == value.at,
                 "CONTINUOUS_MARK_BINDING_INVALID")
    else:
        fill = value.fill
        _require(type(fill) is Fill and fill.venue == "upbit" and fill.account_scope == scope
                 and fill.market == "spot" and fill.symbol in symbols and fill.quote_currency == "KRW"
                 and fill.quote_krw == Decimal(1) and fill.fee_currency == "KRW"
                 and fill.base_currency == fill.symbol[4:] and fill.executed_at == value.at
                 and fill.side in ("buy", "sell") and not fill.order_date and not fill.broker_org_id,
                 "CONTINUOUS_FILL_BINDING_INVALID")
        _id(fill.order_id); _id(fill.fill_id)
        _number(fill.quantity, positive=True); _number(fill.price, positive=True); _number(fill.fee_amount)


def validate_path(path):
    """Structural validation only. Success does not establish source completeness."""
    try:
        _require(type(path) is ContinuousPath, "CONTINUOUS_PATH_REQUIRED")
        _id(path.account_scope); _id(path.stream_epoch); _hash(path.previous_state_digest)
        _instant(path.start); _instant(path.end); _instant(path.watermark_received_at)
        _hash(path.watermark_source_sha256)
        _require(timedelta(0) < path.end-path.start <= MAX_DURATION
                 and path.end <= path.watermark_received_at
                 and path.watermark_received_at-path.start <= MAX_DURATION,
                 "CONTINUOUS_TIME_GAP_OR_ROLLBACK")
        _require(type(path.first_sequence) is int and 0 <= path.first_sequence < 2**63
                 and type(path.watermark_sequence) is int
                 and type(path.events) is tuple and len(path.events) <= MAX_EVENTS
                 and path.watermark_sequence == path.first_sequence + len(path.events)
                 and path.watermark_sequence < 2**63, "CONTINUOUS_SEQUENCE_GAP")
        _require(type(path.opening_marks) is tuple and 0 < len(path.opening_marks) <= MAX_SYMBOLS,
                 "CONTINUOUS_OPENING_MARKS_REQUIRED")
        symbols = []
        for mark in path.opening_marks:
            _mark(mark)
            _require(timedelta(0) <= path.start-mark.asof <= MAX_DURATION,
                     "CONTINUOUS_OPENING_MARK_STALE_OR_FUTURE")
            symbols.append(mark.symbol)
        _require(tuple(symbols) == tuple(sorted(set(symbols))), "CONTINUOUS_MARK_SCOPE_INVALID")
        at, received = path.start, path.start
        for offset, event in enumerate(path.events):
            _event(event, scope=path.account_scope, sequence=path.first_sequence+offset, start=path.start,
                   previous_at=at, previous_received=received, symbols=symbols)
            _require(event.at < path.end and event.received_at <= path.watermark_received_at,
                     "CONTINUOUS_HALF_OPEN_BOUNDARY_REQUIRED")
            at, received = event.at, event.received_at
        return path
    except ContinuousEvidenceError:
        raise
    except (ValueError, TypeError, AttributeError, DecimalException, OverflowError):
        raise ContinuousEvidenceError("CONTINUOUS_PATH_INVALID") from None


class ContinuousPriceRecorder:
    """A bounded one-interval recorder. Any gap/disconnect poisons this epoch.

    There is deliberately no resume/backfill/reset method. Restarting collection
    requires a new reviewed opening anchor. ``seal`` returns an untrusted
    candidate, not a permission to advance the account baseline or place orders.
    Local contiguous sequence values are checked but never claimed as venue proof.
    """
    def __init__(self, *, account_scope, stream_epoch, previous_state_digest, start,
                 opening_marks, first_sequence):
        _id(account_scope); _id(stream_epoch); _hash(previous_state_digest); _instant(start)
        _require(type(first_sequence) is int and 0 <= first_sequence < 2**63, "CONTINUOUS_SEQUENCE_GAP")
        _require(type(opening_marks) is tuple and 0 < len(opening_marks) <= MAX_SYMBOLS,
                 "CONTINUOUS_OPENING_MARKS_REQUIRED")
        symbols = []
        for mark in opening_marks:
            _mark(mark)
            _require(timedelta(0) <= start-mark.asof <= MAX_DURATION,
                     "CONTINUOUS_OPENING_MARK_STALE_OR_FUTURE")
            symbols.append(mark.symbol)
        _require(tuple(symbols) == tuple(sorted(set(symbols))), "CONTINUOUS_MARK_SCOPE_INVALID")
        self._args = dict(account_scope=account_scope, stream_epoch=stream_epoch,
                          previous_state_digest=previous_state_digest, start=start,
                          opening_marks=opening_marks, first_sequence=first_sequence)
        self._symbols, self._events, self._broken, self._sealed = tuple(symbols), [], False, False
        self._lock = Lock()

    def disconnect(self):
        with self._lock:
            self._broken = True

    def append(self, event):
        with self._lock:
            _require(not self._broken, "CONTINUOUS_EPOCH_BROKEN")
            _require(not self._sealed, "CONTINUOUS_EPOCH_SEALED")
            try:
                # Exact last-event redelivery is idempotent; old or changed rows refuse.
                if self._events and event == self._events[-1]:
                    return
                _require(len(self._events) < MAX_EVENTS, "CONTINUOUS_EVENT_LIMIT")
                last = self._events[-1] if self._events else None
                _event(event, scope=self._args["account_scope"],
                       sequence=self._args["first_sequence"]+len(self._events), start=self._args["start"],
                       previous_at=last.at if last else self._args["start"],
                       previous_received=last.received_at if last else self._args["start"], symbols=self._symbols)
                self._events.append(event)
            except Exception:
                self._broken = True
                raise ContinuousEvidenceError("CONTINUOUS_EVENT_REFUSED") from None

    def seal(self, *, end, watermark_sequence, watermark_received_at, watermark_source_sha256):
        with self._lock:
            _require(not self._broken, "CONTINUOUS_EPOCH_BROKEN")
            _require(not self._sealed, "CONTINUOUS_EPOCH_SEALED")
            try:
                candidate = validate_path(ContinuousPath(**self._args, end=end, events=tuple(self._events),
                    watermark_sequence=watermark_sequence, watermark_received_at=watermark_received_at,
                    watermark_source_sha256=watermark_source_sha256))
            except Exception:
                self._broken = True
                raise ContinuousEvidenceError("CONTINUOUS_WATERMARK_REFUSED") from None
            self._sealed = True
            return candidate


def verify_coverage(path, *, account_capture_sha256, verifier, now):
    """Invoke a reviewed source verifier; no default verifier or affirmative fallback."""
    path = validate_path(path)
    _hash(account_capture_sha256); _instant(now)
    _require(callable(verifier), "CONTINUOUS_COVERAGE_VERIFIER_REQUIRED")
    request = CoverageRequest(path_sha256=content_digest(path), account_capture_sha256=account_capture_sha256,
        account_scope=path.account_scope, stream_epoch=path.stream_epoch, start=path.start, end=path.end,
        first_sequence=path.first_sequence, watermark_sequence=path.watermark_sequence)
    try:
        receipt = verifier(request, path)
    except Exception:
        raise ContinuousEvidenceError("CONTINUOUS_COVERAGE_VERIFICATION_FAILED") from None
    _require(type(receipt) is VerifiedCoverage, "CONTINUOUS_VERIFIED_COVERAGE_REQUIRED")
    _hash(receipt.authority_sha256); _hash(receipt.source_proof_sha256); _instant(receipt.verified_at)
    _require(receipt.request_sha256 == content_digest(request) and receipt.contract == COVERAGE_CONTRACT,
             "CONTINUOUS_COVERAGE_BINDING_MISMATCH")
    _require(path.watermark_received_at <= receipt.verified_at <= now
             and now-path.end <= MAX_DURATION, "CONTINUOUS_COVERAGE_STALE_OR_FUTURE")
    return receipt


def archive_candidate(path, *, root: Path):
    """Create one immutable private candidate record before publishing its frame.

    This is a local audit copy, not source authentication or a trusted restart
    anchor. Partial/tampered existing records refuse; no append, repair or
    resume operation exists. A crash leaves an unusable record for review.
    """
    try:
        path = validate_path(path)
        _require(isinstance(root, Path) and root.is_absolute() and root == state_root().absolute(),
                 "CONTINUOUS_ARCHIVE_ROOT_MISMATCH")
        candidate_sha = content_digest(path)
        try:
            checked_target(root, "continuous root")
            directory = checked_target(root / "execution-price-paths", "continuous archive", within=root)
            directory.mkdir(parents=True, exist_ok=True)
            target = checked_target(directory / (candidate_sha + ".json"), "continuous candidate", within=directory)
        except (OSError, ValueError, RuntimeError):
            raise ContinuousEvidenceError("CONTINUOUS_ARCHIVE_PATH_REFUSED") from None
        payload = (json.dumps(canonical(path), ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
        _require(len(payload) <= MAX_ARCHIVE_BYTES, "CONTINUOUS_ARCHIVE_SIZE_REFUSED")
        try:
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(descriptor, "rb") as fh:
                info = os.fstat(fh.fileno())
                _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                         and info.st_size <= MAX_ARCHIVE_BYTES, "CONTINUOUS_ARCHIVE_PATH_REFUSED")
                _require(fh.read(MAX_ARCHIVE_BYTES+1) == payload, "CONTINUOUS_ARCHIVE_CHANGED")
            return candidate_sha
        with os.fdopen(descriptor, "wb") as fh:
            info = os.fstat(fh.fileno())
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "CONTINUOUS_ARCHIVE_PATH_REFUSED")
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        if os.name != "nt":
            descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        return candidate_sha
    except ContinuousEvidenceError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError):
        raise ContinuousEvidenceError("CONTINUOUS_ARCHIVE_REFUSED") from None


def value_path(path, *, opening_cash_krw, opening_units, historical_fills, interval_fills,
               previous_equity_krw, previous_realized_net_krw):
    """Derive exact event-path extrema; source authentication is a separate obligation.

    ``historical_fills`` covers origin up to but excluding start; ``interval_fills``
    is the reconciled account capture's complete [start,end) history. Their order
    at equal timestamps must match the authenticated common event ordering.
    """
    try:
        with localcontext() as numeric:
            numeric.prec = 512
            numeric.traps[Inexact] = True
            path = validate_path(path)
            _number(opening_cash_krw); _number(previous_equity_krw, positive=True)
            _require(type(previous_realized_net_krw) is Decimal and previous_realized_net_krw.is_finite(),
                     "CONTINUOUS_EXACT_NUMBER_REQUIRED")
            _require(type(opening_units) is tuple and type(historical_fills) is tuple
                     and type(interval_fills) is tuple, "CONTINUOUS_ACCOUNT_HISTORY_REQUIRED")
            _require(len(historical_fills) <= MAX_HISTORY_FILLS and len(interval_fills) <= MAX_INTERVAL_FILLS,
                     "CONTINUOUS_FILL_BOUND_EXCEEDED")
            units = {}
            for symbol, amount in opening_units:
                _require(symbol not in units and type(symbol) is str and _SYMBOL.fullmatch(symbol) is not None,
                         "CONTINUOUS_HOLDING_INVALID")
                _number(amount, positive=True)
                units[symbol] = amount
            marks = {mark.symbol: mark for mark in path.opening_marks}
            _require(set(units) <= set(marks), "CONTINUOUS_MARK_COVERAGE_INCOMPLETE")
            _require(all(type(f) is Fill and f.executed_at < path.start for f in historical_fills)
                     and all(type(f) is Fill and path.start <= f.executed_at < path.end for f in interval_fills),
                     "CONTINUOUS_FILL_CUTOFF_MISMATCH")
            _require(all(f.venue == "upbit" and f.account_scope == path.account_scope and f.market == "spot"
                         and f.quote_currency == "KRW" and f.quote_krw == Decimal(1)
                         and f.fee_currency == "KRW" for f in historical_fills+interval_fills),
                     "CONTINUOUS_FILL_BINDING_INVALID")
            observed_fills = tuple(event.fill for event in path.events if event.fill is not None)
            _require(observed_fills == interval_fills, "CONTINUOUS_FILL_COVERAGE_MISMATCH")
            before, after = account_fills(historical_fills), account_fills(historical_fills+interval_fills)
            _require(before.ok and after.ok and before.duplicate_count == 0 and after.duplicate_count == 0,
                     "CONTINUOUS_FIFO_HISTORY_REFUSED")
            _require(before.realized_net_profit_krw == previous_realized_net_krw,
                     "CONTINUOUS_OPENING_PROFIT_MISMATCH")
            expected_units = {row[3]: row[4] for row in before.inventory if row[4] != 0}
            _require(units == expected_units, "CONTINUOUS_OPENING_INVENTORY_MISMATCH")
            cash = opening_cash_krw
            def equity():
                result = cash + sum((quantity*marks[symbol].price for symbol, quantity in units.items()), _ZERO)
                _number(result, positive=True)
                return result
            current = equity()
            _require(current == previous_equity_krw, "CONTINUOUS_OPENING_EQUITY_MISMATCH")
            low = high = current
            realized = before.realized_net_profit_krw
            points = [EquityPoint(at=path.start, equity_krw=current, realized_net_total_krw=realized)]
            accepted = list(historical_fills)
            for event in path.events:
                if event.mark is not None:
                    marks[event.mark.symbol] = event.mark
                else:
                    fill = event.fill
                    _require(fill.symbol in marks, "CONTINUOUS_MARK_COVERAGE_INCOMPLETE")
                    notional = fill.quantity * fill.price
                    cash += (-notional if fill.side == "buy" else notional) - fill.fee_amount
                    quantity = units.get(fill.symbol, _ZERO) + (fill.quantity if fill.side == "buy" else -fill.quantity)
                    _require(cash >= 0 and quantity >= 0, "CONTINUOUS_NEGATIVE_CASH_OR_INVENTORY")
                    if quantity:
                        units[fill.symbol] = quantity
                    else:
                        units.pop(fill.symbol, None)
                    accepted.append(fill)
                    prefix = account_fills(tuple(accepted))
                    _require(prefix.ok and prefix.duplicate_count == 0, "CONTINUOUS_FIFO_HISTORY_REFUSED")
                    realized = prefix.realized_net_profit_krw
                current = equity()
                low, high = min(low, current), max(high, current)
                points.append(EquityPoint(at=event.at, equity_krw=current, realized_net_total_krw=realized))
            _require(units == {row[3]: row[4] for row in after.inventory if row[4] != 0},
                     "CONTINUOUS_CLOSING_INVENTORY_MISMATCH")
            return PathValuation(equity_krw=current, minimum_equity_krw=low, maximum_equity_krw=high,
                realized_net_total_krw=after.realized_net_profit_krw, closing_cash_krw=cash,
                closing_units=tuple(sorted(units.items())), closing_marks=tuple(marks[key] for key in sorted(marks)),
                points=tuple(points)+(EquityPoint(at=path.end, equity_krw=current,
                                                 realized_net_total_krw=realized),))
    except ContinuousEvidenceError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError, DecimalException, OverflowError):
        raise ContinuousEvidenceError("CONTINUOUS_VALUATION_REFUSED") from None
