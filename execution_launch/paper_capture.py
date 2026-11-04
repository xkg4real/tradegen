"""Bounded deterministic paper records with explicit clocks and provenance labels.

No provider, network, file writer, wall clock, reviewer or order sender is chosen
here. Batch playback is always retrospective or synthetic. The streaming class
must exist before the registered window and records each decision as it arrives;
its clock and source remain trusted injected dependencies, not authenticated by
a local hash or the resulting prospective label.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import re

from execution_launch.program import ProgramSpec, program_digest, target_fraction
from execution_launch.strategy import (
    ForwardProtocol, PaperBar, PaperDecision, Registration, evidence_digest,
    parse_protocol, protocol_json, validate_registry,
)

MAX_CAPTURE_BYTES = 16 * 1024 * 1024
_HASH = re.compile(r"[0-9a-f]{64}")
_DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
_MAX_ROWS = 20000


class CaptureError(ValueError):
    """Fixed codes; private quote/input text is never included."""


def _require(condition, code):
    if not condition:
        raise CaptureError(code)


def _instant(value):
    try:
        _require(type(value) is datetime and value.utcoffset() is not None, "CAPTURE_TIME_INVALID")
        value.astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError):
        raise CaptureError("CAPTURE_TIME_INVALID") from None
    return value


def _sha(value):
    _require(type(value) is str and _HASH.fullmatch(value) is not None, "CAPTURE_DIGEST_INVALID")


def _amount(value):
    _require(type(value) is Decimal and value.is_finite() and value > 0,
             "CAPTURE_POSITIVE_DECIMAL_REQUIRED")
    _require(len(value.as_tuple().digits) <= 40 and abs(value.as_tuple().exponent) <= 30,
             "CAPTURE_DECIMAL_RANGE")


@dataclass(frozen=True, kw_only=True)
class CaptureArchive:
    registry: tuple[Registration, ...]
    source_kind: str
    bars: tuple[PaperBar, ...]
    decisions: tuple[PaperDecision, ...]


def _bindings(protocol, registry, program, program_artifact, capture_source_artifact):
    _require(type(protocol) is ForwardProtocol and type(program) is ProgramSpec,
             "CAPTURE_PROTOCOL_OR_PROGRAM_REQUIRED")
    # Reuse the public strict protocol boundary instead of accepting an unchecked
    # dataclass or a caller's claimed protocol digest.
    parse_protocol(protocol_json(protocol))
    span = protocol.capture_end-protocol.capture_start
    spacing = timedelta(seconds=protocol.bar_seconds)
    _require(span % spacing == timedelta(0) and 2 <= span // spacing + 1 <= _MAX_ROWS,
             "CAPTURE_WINDOW_GRID_INVALID")
    validate_registry(registry)
    _require(any(row.study_id == protocol.study_id and row.protocol_digest == evidence_digest(protocol)
                 and row.registered_at == protocol.preregistered_at for row in registry),
             "CAPTURE_PROTOCOL_NOT_REGISTERED")
    _require(program.strategy_id == protocol.strategy_id
             and program_digest(program, program_artifact) == protocol.strategy_code_sha256,
             "CAPTURE_PROGRAM_BINDING_MISMATCH")
    _require(type(capture_source_artifact) is bytes and 0 < len(capture_source_artifact) <= 1048576,
             "CAPTURE_SOURCE_ARTIFACT_REQUIRED")
    _require(hashlib.sha256(capture_source_artifact).hexdigest() == protocol.capture_source_code_sha256,
             "CAPTURE_SOURCE_BINDING_MISMATCH")


def _bar(protocol, row, index, now):
    _require(type(row) is PaperBar, "CAPTURE_BAR_REQUIRED")
    _instant(row.observed_at); _instant(row.received_at); _instant(now); _sha(row.source_sha256)
    try:
        expected = protocol.capture_start+timedelta(seconds=index*protocol.bar_seconds)
    except (ValueError, OverflowError):
        raise CaptureError("CAPTURE_TIME_INVALID") from None
    _require(row.observed_at == expected and expected <= protocol.capture_end, "CAPTURE_SLOT_GAP_OR_DUPLICATE")
    _require(row.observed_at <= row.received_at <= now
             and row.received_at-row.observed_at < timedelta(seconds=protocol.bar_seconds),
             "CAPTURE_RECEIPT_TIME_INVALID")
    for value in (row.bid, row.ask, row.mark, row.quote_krw):
        _amount(value)
    _require(row.bid <= row.mark <= row.ask and row.quote_krw == 1, "CAPTURE_QUOTE_INVALID")
    if expected < protocol.capture_end:
        _require(now+timedelta(seconds=protocol.minimum_fill_delay_seconds)
                 <= expected+timedelta(seconds=protocol.bar_seconds), "CAPTURE_DECISION_TOO_LATE")


def _decision(program, row, index, now, prior_chain, marks):
    chain = evidence_digest((prior_chain, row))
    decision = PaperDecision(bar_index=index, decided_at=now, history_sha256=chain,
                             target_fraction=target_fraction(program, marks))
    return chain, decision


def _clock_value(clock):
    try:
        return _instant(clock())
    except Exception:
        raise CaptureError("CAPTURE_CLOCK_FAILED") from None


def sample_prefetched_book(book, *, slot: datetime, sampled_at: datetime) -> PaperBar:
    """Sample an already-received fresh book at an explicit observation slot.

    These are sampling-record times, not renamed exchange/HTTP timestamps. The
    original immutable receipt retains both source times and exact bytes. A book
    arriving after the slot cannot be substituted into that historical slot.
    """
    from execution_accounts.quotes import OrderbookQuote, to_runner_quote
    _instant(slot); _instant(sampled_at)
    _require(type(book) is OrderbookQuote, "CAPTURE_BOOK_REQUIRED")
    # Both checks reparse the original bytes, validate source identity/integrity,
    # and impose the quote source's ten-second freshness boundary.
    to_runner_quote(book, now=sampled_at)
    _require(book.received_at <= slot <= sampled_at, "CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT")
    to_runner_quote(book, now=slot)
    return PaperBar(observed_at=slot, received_at=sampled_at, bid=book.bid, ask=book.ask,
                    mark=book.midpoint, quote_krw=Decimal(1), source_sha256=book.receipt.sha256)


class PaperCapture:
    """An explicit streaming recorder; constructing it does not contact a source.

    The caller obtains fresh quote slots and retains their raw records. Append
    uses the injected clock at the actual decision call, never a bar's historical
    receipt timestamp. Local clocks or records can still be fabricated by an
    untrusted caller; independent source/publication review remains mandatory.
    """
    def __init__(self, protocol, registry, program, *, program_artifact, capture_source_artifact, clock):
        _bindings(protocol, registry, program, program_artifact, capture_source_artifact)
        _require(callable(clock), "CAPTURE_CLOCK_REQUIRED")
        now = _clock_value(clock)
        _require(protocol.preregistered_at <= now < protocol.capture_start, "CAPTURE_MUST_START_BEFORE_WINDOW")
        self._protocol, self._registry, self._program = protocol, registry, program
        self._program_artifact, self._source_artifact = program_artifact, capture_source_artifact
        self._clock = clock
        self._binding = evidence_digest((protocol, registry, program_digest(program, program_artifact)))
        self._last_clock, self._closed = now, False
        self._bars, self._decisions, self._marks = (), (), ()
        self._chain = ""
        self._decision_chain = ""
        self._sampled_receipts = ()

    def _time(self):
        now = _clock_value(self._clock)
        _require(now >= self._last_clock, "CAPTURE_CLOCK_ROLLBACK")
        self._last_clock = now
        return now

    def _intact(self):
        _bindings(self._protocol, self._registry, self._program, self._program_artifact, self._source_artifact)
        _require(evidence_digest((self._protocol, self._registry,
                 program_digest(self._program, self._program_artifact))) == self._binding,
                 "CAPTURE_CONFIGURATION_CHANGED")

    def append(self, bar: PaperBar) -> PaperDecision | None:
        _require(not self._closed, "CAPTURE_ALREADY_CLOSED")
        self._intact()
        now = self._time()
        return self._append(bar, now)

    def append_book(self, book) -> PaperDecision | None:
        """Sample the next exact slot from a previously received original book.

        No fetch, sleep, slot backfill, or clock default is performed. The caller
        must prefetch through its approved source and invoke this at the slot.
        """
        _require(not self._closed, "CAPTURE_ALREADY_CLOSED")
        self._intact()
        now = self._time()
        index = len(self._bars)
        _require(index < _MAX_ROWS, "CAPTURE_ROW_LIMIT")
        slot = self._protocol.capture_start+timedelta(seconds=index*self._protocol.bar_seconds)
        bar = sample_prefetched_book(book, slot=slot, sampled_at=now)
        _require(book.symbol == self._protocol.symbol, "CAPTURE_BOOK_MARKET_MISMATCH")
        decision = self._append(bar, now)
        self._sampled_receipts += ((index, book.receipt),)
        return decision

    @property
    def sampled_receipts(self):
        """Original (bar index, receipt) pairs from append_book for separate archival."""
        return self._sampled_receipts

    def _append(self, bar, now):
        index = len(self._bars)
        _require(index < _MAX_ROWS, "CAPTURE_ROW_LIMIT")
        _bar(self._protocol, bar, index, now)
        marks = self._marks+(bar.mark,)
        if self._program.kind != "cash":
            marks = marks[-self._program.slow_window:]
        else:
            marks = marks[-1:]
        chain = evidence_digest((self._chain, bar))
        decision = None
        if bar.observed_at < self._protocol.capture_end:
            chain, decision = _decision(self._program, bar, index, now, self._chain, marks)
        # Refused input never appends a partial bar/decision or changes the chain.
        self._bars += (bar,)
        if decision is not None:
            self._decisions += (decision,)
            self._decision_chain = evidence_digest((self._decision_chain, decision))
        self._marks, self._chain, self._last_clock = marks, chain, now
        return decision

    def snapshot(self) -> CaptureArchive:
        """Archive even an incomplete/failed trial; evaluator completeness still applies."""
        self._intact()
        chain, decisions = "", ""
        for row in self._bars:
            chain = evidence_digest((chain, row))
        for row in self._decisions:
            decisions = evidence_digest((decisions, row))
        _require(chain == self._chain and decisions == self._decision_chain,
                 "CAPTURE_HISTORY_CHANGED")
        return CaptureArchive(registry=self._registry, source_kind="prospective_paper_capture",
                              bars=self._bars, decisions=self._decisions)

    def finish(self) -> CaptureArchive:
        _require(not self._closed, "CAPTURE_ALREADY_CLOSED")
        self._intact()
        now = self._time()
        _require(len(self._bars) >= 2 and self._bars[-1].observed_at == self._protocol.capture_end
                 and now >= self._bars[-1].received_at, "CAPTURE_WINDOW_INCOMPLETE")
        result = self.snapshot()
        self._last_clock, self._closed = now, True
        return result


def replay_capture(protocol, registry, program, bars, *, program_artifact,
                   capture_source_artifact, source_kind, now) -> CaptureArchive:
    """Generate causal decisions from imported observations without claiming live capture.

    Decision times are reconstructed from supplied receipt times. Only the two
    nonprospective labels are accepted, irrespective of matching hashes/dates.
    """
    _require(source_kind in ("retrospective_replay", "synthetic"), "CAPTURE_BATCH_NOT_PROSPECTIVE")
    _bindings(protocol, registry, program, program_artifact, capture_source_artifact)
    _instant(now)
    _require(type(bars) is tuple and 2 <= len(bars) <= _MAX_ROWS, "CAPTURE_ROWS_INVALID")
    decisions, marks, chain = [], (), ""
    for index, bar in enumerate(bars):
        _require(type(bar) is PaperBar, "CAPTURE_BAR_REQUIRED")
        _bar(protocol, bar, index, bar.received_at)
        _require(bar.received_at <= now, "CAPTURE_FUTURE_RECEIPT")
        marks += (bar.mark,)
        marks = marks[-program.slow_window:] if program.kind != "cash" else marks[-1:]
        if bar.observed_at < protocol.capture_end:
            chain, decision = _decision(program, bar, index, bar.received_at, chain, marks)
            decisions.append(decision)
    _require(bars[-1].observed_at == protocol.capture_end, "CAPTURE_WINDOW_INCOMPLETE")
    return CaptureArchive(registry=registry, source_kind=source_kind, bars=bars, decisions=tuple(decisions))


def _plain(value):
    if type(value) in (CaptureArchive, Registration, PaperBar, PaperDecision):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value)}
    if type(value) is Decimal:
        _require(value.is_finite() and value >= 0 and len(value.as_tuple().digits) <= 40
                 and abs(value.as_tuple().exponent) <= 30, "CAPTURE_DECIMAL_INVALID")
        text = format(value, "f")
        return (text.rstrip("0").rstrip(".") if "." in text else text) if value else "0"
    if type(value) is datetime:
        return _instant(value).astimezone(timezone.utc).isoformat(timespec="microseconds")
    if type(value) is tuple:
        return [_plain(row) for row in value]
    if type(value) in (str, int) or value is None:
        return value
    raise CaptureError("CAPTURE_ARCHIVE_SCHEMA_INVALID")


def capture_json(archive: CaptureArchive) -> str:
    _require(type(archive) is CaptureArchive and archive.source_kind in
             ("prospective_paper_capture", "retrospective_replay", "synthetic"), "CAPTURE_ARCHIVE_REQUIRED")
    validate_registry(archive.registry)
    _require(type(archive.bars) is tuple and type(archive.decisions) is tuple
             and len(archive.bars) <= _MAX_ROWS and len(archive.decisions) <= _MAX_ROWS
             and all(type(row) is PaperBar for row in archive.bars)
             and all(type(row) is PaperDecision for row in archive.decisions),
             "CAPTURE_ROWS_INVALID")
    raw = json.dumps(_plain(archive), sort_keys=True, separators=(",", ":"), ensure_ascii=True)+"\n"
    _require(len(raw.encode("utf-8")) <= MAX_CAPTURE_BYTES, "CAPTURE_JSON_TOO_LARGE")
    return raw


def _object(value, cls):
    _require(type(value) is dict and set(value) == {item.name for item in fields(cls)}, "CAPTURE_JSON_SCHEMA_INVALID")
    return dict(value)


def _date(value):
    _require(type(value) is str, "CAPTURE_TIME_INVALID")
    return _instant(datetime.fromisoformat(value))


def parse_replay_input(raw: str | bytes):
    """Parse {registry,bars,source_kind}; never accepts decisions or a PASS summary."""
    _require(type(raw) in (str, bytes) and len(raw) <= MAX_CAPTURE_BYTES, "CAPTURE_JSON_SIZE_OR_TYPE")
    def unique(pairs):
        body = {}
        for key, value in pairs:
            _require(key not in body, "CAPTURE_JSON_DUPLICATE_KEY")
            body[key] = value
        return body
    def invalid(value):
        raise CaptureError("CAPTURE_JSON_NUMBER_INVALID")
    try:
        body = json.loads(raw, object_pairs_hook=unique, parse_float=invalid, parse_constant=invalid)
        _require(type(body) is dict and set(body) == {"registry", "bars", "source_kind"},
                 "CAPTURE_JSON_SCHEMA_INVALID")
        _require(body["source_kind"] in ("retrospective_replay", "synthetic"), "CAPTURE_BATCH_NOT_PROSPECTIVE")
        _require(type(body["registry"]) is list and len(body["registry"]) <= 1000
                 and type(body["bars"]) is list and 2 <= len(body["bars"]) <= _MAX_ROWS,
                 "CAPTURE_ROWS_INVALID")
        registry, bars = [], []
        for row in body["registry"]:
            value = _object(row, Registration)
            value["registered_at"] = _date(value["registered_at"])
            registry.append(Registration(**value))
        validate_registry(tuple(registry))
        for row in body["bars"]:
            value = _object(row, PaperBar)
            for key in ("observed_at", "received_at"):
                value[key] = _date(value[key])
            for key in ("bid", "ask", "mark", "quote_krw"):
                amount = value[key]
                _require(type(amount) is str and len(amount) <= 72 and _DECIMAL.fullmatch(amount) is not None,
                         "CAPTURE_DECIMAL_STRING_REQUIRED")
                value[key] = Decimal(amount)
                _amount(value[key])
            _sha(value["source_sha256"])
            bars.append(PaperBar(**value))
        return tuple(registry), tuple(bars), body["source_kind"]
    except CaptureError:
        raise
    except (ValueError, TypeError, UnicodeError, RecursionError, ArithmeticError):
        raise CaptureError("CAPTURE_JSON_INVALID") from None
