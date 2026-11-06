"""Owner-operated public quote timing diagnostics, offline unless capture is explicit.

    python -m execution_launch.quote_diagnostics --help
    python -m execution_launch.quote_diagnostics capture --symbol KRW-BTC --samples 20 --interval-seconds 1

Only capture constructs the existing credential-free E1 quote source. Reports
contain timing and fixed codes, never prices, sizes, raw bodies or owner state.
An apparent book age combines timestamp-to-receipt delay and clock disagreement:
it is not a clock-offset estimate, synchronization proof or execution permission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import sys
import time
from typing import Callable

from execution_accounts import quotes as Q
from execution_accounts.collector import SourceReceipt

_TIME_CODES = frozenset({"QUOTE_RECEIPT_STALE_OR_FUTURE", "QUOTE_SERVER_CLOCK_MISMATCH",
                         "QUOTE_BOOK_STALE_OR_FUTURE"})
_SOURCE_CODES = frozenset({"QUOTE_PUBLIC_INQUIRY_FAILED", "QUOTE_SERVER_TIME_REQUIRED",
                           "QUOTE_RECEIPT_OUTSIDE_REQUEST", "QUOTE_AWARE_TIME_REQUIRED",
                           "QUOTE_TIME_INVALID"})
_DIAGNOSTIC_CODES = frozenset({"QUOTE_DIAGNOSTIC_AWARE_TIME_REQUIRED", "QUOTE_DIAGNOSTIC_TIME_INVALID",
    "QUOTE_DIAGNOSTIC_SYMBOL_INVALID", "QUOTE_DIAGNOSTIC_RECEIPT_REQUIRED",
    "QUOTE_DIAGNOSTIC_MONOTONIC_INVALID", "QUOTE_DIAGNOSTIC_RECEIPT_OUTSIDE_REQUEST",
    "QUOTE_DIAGNOSTIC_SCOPE_MISMATCH", "QUOTE_DIAGNOSTIC_RESPONSE_INVALID",
    "QUOTE_DIAGNOSTIC_TIMESTAMP_INVALID", "QUOTE_DIAGNOSTIC_BOUNDS_INVALID",
    "QUOTE_DIAGNOSTIC_DEPENDENCIES_REQUIRED", "QUOTE_DIAGNOSTIC_MONOTONIC_ROLLBACK",
    "QUOTE_DIAGNOSTIC_WALL_CLOCK_ROLLBACK", "QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID"})
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_LIMITATIONS = (
    "BOOK_AGE_COMBINES_TIMESTAMP_TO_RECEIPT_DELAY_AND_CLOCK_OFFSET",
    "HTTP_DATE_HAS_SECOND_RESOLUTION_AND_MESSAGE_GENERATION_SEMANTICS",
    "REQUEST_DURATION_INCLUDES_TRANSPORT_PACING_AND_POSSIBLE_RETRY",
    "FINITE_SAMPLES_DO_NOT_ESTABLISH_FUTURE_CLOCK_OR_NETWORK_BEHAVIOR",
    "TIME_REFUSED_SAMPLES_DO_NOT_ESTABLISH_FULL_BOOK_STRUCTURE_VALIDITY",
    "NO_CLOCK_ADJUSTMENT_OR_TRADING_PERMISSION",
)


class DiagnosticError(ValueError):
    """Fixed diagnostic codes only; inputs and provider exception text stay private."""


def _require(ok, code):
    if not ok:
        raise DiagnosticError(code)


def _instant(value):
    _require(type(value) is datetime and value.utcoffset() is not None,
             "QUOTE_DIAGNOSTIC_AWARE_TIME_REQUIRED")
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise DiagnosticError("QUOTE_DIAGNOSTIC_TIME_INVALID") from None


def _micros(value):
    return (value.days * 86400 + value.seconds) * 1_000_000 + value.microseconds


def _symbol(value):
    try:
        Q._symbol(value)
    except Q.QuoteError:
        raise DiagnosticError("QUOTE_DIAGNOSTIC_SYMBOL_INVALID") from None


@dataclass(frozen=True, kw_only=True)
class TimingSample:
    requested_at: str
    received_at: str
    checked_at: str
    book_asof: str
    http_date: str
    apparent_book_age_us: int
    received_minus_http_date_us: int
    request_wall_duration_us: int
    request_monotonic_duration_ns: int
    strict_quote_admitted: bool
    book_structure_verified: bool
    strict_quote_reason: str | None
    source_sha256: str


def inspect_read(reading: Q.OrderbookRead, *, symbol: str, monotonic_elapsed_ns: int) -> TimingSample:
    """Pure timing inspection; the normal quote validator still decides admission.

    A negative apparent age is retained as evidence of disagreement; it does not
    admit the quote. HTTP Date is not an independent precision time reference.
    No corrected timestamp or clock offset is computed.
    """
    _symbol(symbol)
    _require(type(reading) is Q.OrderbookRead and type(reading.receipt) is SourceReceipt,
             "QUOTE_DIAGNOSTIC_RECEIPT_REQUIRED")
    _require(type(monotonic_elapsed_ns) is int and 0 <= monotonic_elapsed_ns <= 2**63 - 1,
             "QUOTE_DIAGNOSTIC_MONOTONIC_INVALID")
    receipt = reading.receipt
    start, end = _instant(reading.requested_at), _instant(reading.checked_at)
    received, server = _instant(receipt.received_at), _instant(receipt.server_time)
    _require(start <= received <= end, "QUOTE_DIAGNOSTIC_RECEIPT_OUTSIDE_REQUEST")
    _require(receipt.path == Q.ORDERBOOK_PATH and receipt.account_scope == Q._PUBLIC_SCOPE
             and type(receipt.params) is tuple and receipt.params == Q._params(symbol),
             "QUOTE_DIAGNOSTIC_SCOPE_MISMATCH")
    _require(type(receipt.raw_body) is bytes and 0 < len(receipt.raw_body) <= 131072,
             "QUOTE_DIAGNOSTIC_RESPONSE_INVALID")
    try:
        body = receipt.decode()
    except (ValueError, TypeError, ArithmeticError, RecursionError):
        raise DiagnosticError("QUOTE_DIAGNOSTIC_RESPONSE_INVALID") from None
    _require(type(body) is list and len(body) == 1 and type(body[0]) is dict
             and body[0].get("market") == symbol, "QUOTE_DIAGNOSTIC_RESPONSE_INVALID")
    stamp = body[0].get("timestamp")
    _require(type(stamp) is int and 0 < stamp <= 2**63 - 1, "QUOTE_DIAGNOSTIC_TIMESTAMP_INVALID")
    try:
        asof = _EPOCH + timedelta(milliseconds=stamp)
    except OverflowError:
        raise DiagnosticError("QUOTE_DIAGNOSTIC_TIMESTAMP_INVALID") from None
    reason = None
    try:
        Q.parse_orderbook(receipt, symbol=symbol, now=end)
    except Q.QuoteError as exc:
        # Only clock refusals are informative timing samples. Other malformed
        # books refuse without reproducing source fields or exception text.
        _require(str(exc) in _TIME_CODES, "QUOTE_DIAGNOSTIC_RESPONSE_INVALID")
        reason = str(exc)
    return TimingSample(requested_at=start.isoformat(), received_at=received.isoformat(),
        checked_at=end.isoformat(), book_asof=asof.isoformat(), http_date=server.isoformat(),
        apparent_book_age_us=_micros(received-asof), received_minus_http_date_us=_micros(received-server),
        request_wall_duration_us=_micros(end-start), request_monotonic_duration_ns=monotonic_elapsed_ns,
        strict_quote_admitted=reason is None, book_structure_verified=reason is None,
        strict_quote_reason=reason, source_sha256=receipt.sha256)


def _report(samples, requested, reason=None):
    ages = [sample.apparent_book_age_us for sample in samples]
    return {"diagnostic_complete": len(samples) == requested and reason is None,
            "execution_ready": False, "clock_synchronized": False, "clock_offset_estimate_us": None,
            "requested_samples": requested, "measured_samples": len(samples),
            "strictly_admitted_samples": sum(sample.strict_quote_admitted for sample in samples),
            "minimum_apparent_book_age_us": min(ages) if ages else None,
            "maximum_apparent_book_age_us": max(ages) if ages else None,
            "reason": reason, "limitations": list(_LIMITATIONS),
            "samples": [asdict(sample) for sample in samples]}


def collect_timing(*, source, symbol: str, samples: int, interval_seconds: int,
                   monotonic_ns: Callable[[], int], wait: Callable[[int], None]) -> dict:
    """Bounded owner capture over an explicit source; fake every dependency in tests.

    Stop on the first malformed response, request refusal, clock rollback or
    interruption and retain prior samples. The source owns transport retry and
    pacing; this function adds no retry and does not change local/system clocks.
    """
    _symbol(symbol)
    _require(type(samples) is int and 1 <= samples <= 60
             and type(interval_seconds) is int and 1 <= interval_seconds <= 5,
             "QUOTE_DIAGNOSTIC_BOUNDS_INVALID")
    _require(callable(getattr(source, "read_receipt", None)) and callable(monotonic_ns) and callable(wait),
             "QUOTE_DIAGNOSTIC_DEPENDENCIES_REQUIRED")
    readings, last_wall, last_monotonic = [], None, None
    try:
        for index in range(samples):
            if index:
                wait(interval_seconds)
            before = monotonic_ns()
            _require(type(before) is int and before >= 0
                     and (last_monotonic is None or before >= last_monotonic),
                     "QUOTE_DIAGNOSTIC_MONOTONIC_ROLLBACK")
            reading = source.read_receipt()
            after = monotonic_ns()
            _require(type(after) is int and after >= before, "QUOTE_DIAGNOSTIC_MONOTONIC_ROLLBACK")
            _require(type(reading) is Q.OrderbookRead, "QUOTE_DIAGNOSTIC_RECEIPT_REQUIRED")
            start = _instant(reading.requested_at)
            _require(last_wall is None or start >= last_wall, "QUOTE_DIAGNOSTIC_WALL_CLOCK_ROLLBACK")
            sample = inspect_read(reading, symbol=symbol, monotonic_elapsed_ns=after-before)
            readings.append(sample)
            last_wall, last_monotonic = _instant(reading.checked_at), after
    except DiagnosticError as exc:
        reason = str(exc) if str(exc) in _DIAGNOSTIC_CODES else "QUOTE_DIAGNOSTIC_SOURCE_REFUSED"
        return _report(readings, samples, reason)
    except Q.QuoteError as exc:
        reason = str(exc) if str(exc) in _SOURCE_CODES else "QUOTE_DIAGNOSTIC_SOURCE_REFUSED"
        return _report(readings, samples, reason)
    except KeyboardInterrupt:
        return _report(readings, samples, "QUOTE_DIAGNOSTIC_STOPPED")
    except Exception:
        return _report(readings, samples, "QUOTE_DIAGNOSTIC_SOURCE_FAILED")
    return _report(readings, samples)


def _arguments(argv):
    values = sys.argv[1:] if argv is None else argv
    _require(type(values) in (list, tuple) and all(type(v) is str for v in values),
             "QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID")
    if not values:
        return None
    if values in (["--help"], ["-h"], ("--help",), ("-h",)):
        return {"help": True}
    _require(values[0] == "capture" and len(values) % 2 == 1, "QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID")
    result = {"samples": 20, "interval-seconds": 1}
    seen = set()
    for key, value in zip(values[1::2], values[2::2]):
        _require(key in ("--symbol", "--samples", "--interval-seconds") and key not in seen,
                 "QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID")
        seen.add(key)
        name = key[2:]
        if name == "symbol":
            _symbol(value)
            result[name] = value
        else:
            _require(value.isascii() and value.isdigit() and 1 <= len(value) <= 2,
                     "QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID")
            result[name] = int(value)
    _require("symbol" in result and 1 <= result["samples"] <= 60
             and 1 <= result["interval-seconds"] <= 5, "QUOTE_DIAGNOSTIC_ARGUMENTS_INVALID")
    return result


def _wall_clock():
    return datetime.now(timezone.utc)


def main(argv=None) -> int:
    try:
        args = _arguments(argv)
        if args is None:
            report = _report([], 0, "QUOTE_DIAGNOSTIC_CAPTURE_NOT_REQUESTED")
        elif args.get("help"):
            print(__doc__)
            return 0
        else:
            source = Q.E1UpbitQuoteSource(symbol=args["symbol"], clock=_wall_clock)
            report = collect_timing(source=source, symbol=args["symbol"], samples=args["samples"],
                interval_seconds=args["interval-seconds"], monotonic_ns=time.monotonic_ns, wait=time.sleep)
    except DiagnosticError as exc:
        reason = str(exc) if str(exc) in _DIAGNOSTIC_CODES else "QUOTE_DIAGNOSTIC_FAILED"
        report = _report([], 0, reason)
    except Exception:
        report = _report([], 0, "QUOTE_DIAGNOSTIC_FAILED")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["diagnostic_complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
