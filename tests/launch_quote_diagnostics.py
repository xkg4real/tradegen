"""Timing diagnostics use invented receipts and the hermetic E1 HTTP seam only."""
from contextlib import ExitStack, redirect_stdout
from dataclasses import replace
from datetime import timedelta
from io import StringIO
import json
import os
from unittest.mock import patch

from execution import keys, transport
from execution_accounts import quotes as Q
from execution_launch import quote_diagnostics as D
from tests import accounts_quotes as B, execution_fixtures as F

NOW = F.NOW
SYMBOL = "KRW-BTC"


def reading(*, shifted=0, age_ms=20, **receipt_changes):
    receive = NOW + timedelta(seconds=shifted)
    body = B.body()
    body[0]["timestamp"] = int(receive.timestamp()) * 1000 - age_ms
    receipt = B.receipt(body, **(dict(received_at=receive, server_time=receive) | receipt_changes))
    return Q.OrderbookRead(requested_at=receive-timedelta(milliseconds=40),
                           checked_at=receive+timedelta(milliseconds=200), receipt=receipt)


class Source:
    def __init__(self, values):
        self.values, self.calls = iter(values), 0

    def read_receipt(self):
        self.calls += 1
        value = next(self.values)
        if isinstance(value, BaseException):
            raise value
        return value


def collect(values, **changes):
    values = list(values)
    counter = iter(range(0, 100_000_000_000, 240_000_000))
    source = Source(values)
    waits = []
    kwargs = dict(source=source, symbol=SYMBOL, samples=len(values), interval_seconds=1,
                  monotonic_ns=lambda: next(counter), wait=waits.append)
    report = D.collect_timing(**(kwargs | changes))
    return report, source, waits


def invoke(*args):
    output = StringIO()
    with redirect_stdout(output):
        code = D.main(list(args))
    raw = output.getvalue()
    return code, json.loads(raw), raw


def refused(call, code):
    try:
        call()
    except D.DiagnosticError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected " + code)


def test_default_help_and_invalid_args_are_offline_and_redacted():
    with ExitStack() as stack:
        for name in ("execution_accounts.quotes.E1UpbitQuoteSource", "time.monotonic_ns", "time.sleep",
                     "execution_launch.quote_diagnostics._wall_clock",
                     "os.getenv", "pathlib.Path.home", "socket.create_connection"):
            stack.enter_context(patch(name, side_effect=AssertionError("unexpected effect")))
        stack.enter_context(patch.object(os._Environ, "__getitem__", side_effect=AssertionError("environment read")))
        code, report, _ = invoke()
        assert code == 2 and report["reason"] == "QUOTE_DIAGNOSTIC_CAPTURE_NOT_REQUESTED"
        with redirect_stdout(StringIO()) as help_text:
            assert D.main(["--help"]) == 0
        assert "capture" in help_text.getvalue()
        for args in (("secret-value",), ("capture",), ("capture", "--symbol", "secret-value"),
                     ("capture", "--symbol", SYMBOL, "--url", "secret-value"),
                     ("capture", "--symbol", SYMBOL, "--samples", "61"),
                     ("capture", "--symbol", SYMBOL, "--interval-seconds", "0"),
                     ("capture", "--symbol", SYMBOL, "--samples", "1", "--samples", "2"),
                     ("capture", "--symbol", SYMBOL, "--samples", "１"),
                     ("capture", "--symbol", SYMBOL, "--samples", "100000000000")):
            code, report, raw = invoke(*args)
            assert code == 2 and not report["execution_ready"] and "secret-value" not in raw


def test_normal_measurements_are_exact_and_do_not_estimate_clock_offset():
    report, source, waits = collect([reading(), reading(shifted=1, age_ms=35)])
    assert report["diagnostic_complete"] and report["measured_samples"] == 2
    assert report["strictly_admitted_samples"] == 2 and source.calls == 2 and waits == [1]
    assert report["minimum_apparent_book_age_us"] == 20_000
    assert report["maximum_apparent_book_age_us"] == 35_000
    first = report["samples"][0]
    assert first["request_wall_duration_us"] == 240_000
    assert first["request_monotonic_duration_ns"] == 240_000_000
    assert first["received_minus_http_date_us"] == 0 and first["strict_quote_reason"] is None
    assert first["book_structure_verified"]
    assert report["clock_offset_estimate_us"] is None
    assert not report["execution_ready"] and not report["clock_synchronized"]
    assert "CLOCK_OFFSET" in report["limitations"][0]


def test_future_book_is_measured_without_relaxing_normal_quote_admission():
    sample = reading(age_ms=-2)
    report, _, _ = collect([sample])
    assert report["diagnostic_complete"] and report["minimum_apparent_book_age_us"] == -2000
    assert report["strictly_admitted_samples"] == 0
    assert report["samples"][0]["strict_quote_reason"] == "QUOTE_BOOK_STALE_OR_FUTURE"
    assert not report["execution_ready"] and report["clock_offset_estimate_us"] is None
    B.refusal(lambda: Q.parse_orderbook(sample.receipt, symbol=SYMBOL, now=sample.checked_at),
              "QUOTE_BOOK_STALE_OR_FUTURE")


def test_stale_book_and_http_date_disagreement_remain_rejected_samples():
    for sample, reason in ((reading(age_ms=10_001), "QUOTE_BOOK_STALE_OR_FUTURE"),
                          (reading(server_time=NOW-timedelta(seconds=61)), "QUOTE_SERVER_CLOCK_MISMATCH")):
        report, _, _ = collect([sample])
        assert report["diagnostic_complete"] and report["strictly_admitted_samples"] == 0
        assert report["samples"][0]["strict_quote_reason"] == reason
        assert report["clock_offset_estimate_us"] is None and not report["clock_synchronized"]


def test_future_stamp_with_bad_depth_is_not_misreported_as_structurally_valid():
    body = B.body()
    body[0]["timestamp"] += 1
    body[0]["orderbook_units"] = []
    report, _, _ = collect([replace(reading(), receipt=B.receipt(body))])
    assert report["diagnostic_complete"]
    sample = report["samples"][0]
    assert sample["apparent_book_age_us"] == -1000
    assert sample["strict_quote_reason"] == "QUOTE_BOOK_STALE_OR_FUTURE"
    assert not sample["strict_quote_admitted"] and not sample["book_structure_verified"]
    assert "TIME_REFUSED_SAMPLES_DO_NOT_ESTABLISH_FULL_BOOK_STRUCTURE_VALIDITY" in report["limitations"]


def test_fractional_receive_time_is_preserved_and_http_date_is_not_submillisecond_clock():
    sample = reading(received_at=NOW+timedelta(microseconds=123456))
    inspected = D.inspect_read(sample, symbol=SYMBOL, monotonic_elapsed_ns=240_123_456)
    assert inspected.apparent_book_age_us == 143456
    assert inspected.received_minus_http_date_us == 123456
    report, _, _ = collect([sample])
    assert "HTTP_DATE_HAS_SECOND_RESOLUTION_AND_MESSAGE_GENERATION_SEMANTICS" in report["limitations"]
    assert report["clock_offset_estimate_us"] is None


def test_malformed_digest_json_depth_and_oversized_body_refuse_without_echo():
    base = reading()
    bad_depth = B.body(); bad_depth[0]["orderbook_units"] = []
    bad = [replace(base.receipt, sha256="0"*64), B.receipt(raw=b'[{"market":"private-response"}]'),
           B.receipt(raw=b'[{"timestamp":1,"timestamp":2}]'), B.receipt(raw=b'[NaN]'),
           B.receipt(raw=b'\xff'), B.receipt(raw=b" "*131073), B.receipt(raw=b""), B.receipt(bad_depth)]
    for receipt in bad:
        report, _, _ = collect([replace(base, receipt=receipt)])
        assert not report["diagnostic_complete"] and report["measured_samples"] == 0
        assert report["reason"] == "QUOTE_DIAGNOSTIC_RESPONSE_INVALID"
        assert "private-response" not in json.dumps(report)


def test_wrong_scope_market_params_and_body_cardinality_refuse():
    base = reading()
    for receipt in (replace(base.receipt, path="wrong"), replace(base.receipt, account_scope="private-account"),
                    replace(base.receipt, params=()), replace(base.receipt, params=list(base.receipt.params))):
        report, _, _ = collect([replace(base, receipt=receipt)])
        assert report["reason"] == "QUOTE_DIAGNOSTIC_SCOPE_MISMATCH"
        assert "private-account" not in json.dumps(report)
    for body in ({}, [], B.body()*2, [None]):
        report, _, _ = collect([replace(base, receipt=B.receipt(body))])
        assert report["reason"] == "QUOTE_DIAGNOSTIC_RESPONSE_INVALID"


def test_timestamp_types_and_overflow_are_bounded():
    for stamp in (True, "1", 0, -1, 2**63, 2**63-1):
        body = B.body(); body[0]["timestamp"] = stamp
        report, _, _ = collect([replace(reading(), receipt=B.receipt(body))])
        assert report["reason"] == "QUOTE_DIAGNOSTIC_TIMESTAMP_INVALID"


def test_aware_time_and_receipt_envelope_are_required():
    base = reading()
    for sample in (replace(base, requested_at=NOW.replace(tzinfo=None)),
                   replace(base, receipt=replace(base.receipt, server_time=None))):
        report, _, _ = collect([sample])
        assert report["reason"] == "QUOTE_DIAGNOSTIC_AWARE_TIME_REQUIRED"
    for sample in (replace(base, requested_at=NOW+timedelta(seconds=1)),
                   replace(base, checked_at=NOW-timedelta(seconds=1))):
        report, _, _ = collect([sample])
        assert report["reason"] == "QUOTE_DIAGNOSTIC_RECEIPT_OUTSIDE_REQUEST"


def test_wall_clock_rollback_stops_and_preserves_prior_sample():
    report, source, waits = collect([reading(), reading(shifted=-1), reading(shifted=2)])
    assert not report["diagnostic_complete"] and report["measured_samples"] == 1
    assert report["reason"] == "QUOTE_DIAGNOSTIC_WALL_CLOCK_ROLLBACK"
    assert source.calls == 2 and waits == [1]


def test_monotonic_rollback_or_wrong_clock_type_stops():
    for values in ((2, 1), (False,), (-1,)):
        stamps = iter(values)
        report, _, _ = collect([reading()], monotonic_ns=lambda: next(stamps))
        assert report["reason"] == "QUOTE_DIAGNOSTIC_MONOTONIC_ROLLBACK"
    stamps = iter((10, 20, 19))
    report, source, _ = collect([reading(), reading(shifted=1)], monotonic_ns=lambda: next(stamps))
    assert report["reason"] == "QUOTE_DIAGNOSTIC_MONOTONIC_ROLLBACK" and source.calls == 1
    refused(lambda: D.inspect_read(reading(), symbol=SYMBOL, monotonic_elapsed_ns=True),
            "QUOTE_DIAGNOSTIC_MONOTONIC_INVALID")


def test_request_errors_are_redacted_and_no_new_retry_is_added():
    for error, expected in ((RuntimeError("private-provider-secret"), "QUOTE_DIAGNOSTIC_SOURCE_FAILED"),
                            (Q.QuoteError("private-provider-secret"), "QUOTE_DIAGNOSTIC_SOURCE_REFUSED"),
                            (D.DiagnosticError("private-provider-secret"), "QUOTE_DIAGNOSTIC_SOURCE_REFUSED"),
                            (Q.QuoteError("QUOTE_SERVER_TIME_REQUIRED"), "QUOTE_SERVER_TIME_REQUIRED")):
        report, source, _ = collect([reading(), error, reading(shifted=2)])
        assert report["measured_samples"] == 1 and report["reason"] == expected and source.calls == 2
        assert "private-provider-secret" not in json.dumps(report)


def test_interrupt_during_wait_retains_prior_samples():
    def interrupted(_):
        raise KeyboardInterrupt
    report, source, _ = collect([reading(), reading(shifted=1)], wait=interrupted)
    assert report["reason"] == "QUOTE_DIAGNOSTIC_STOPPED" and report["measured_samples"] == 1
    assert source.calls == 1


def test_capture_bounds_and_dependencies_refuse_before_source_use():
    source = Source([reading()])
    kwargs = dict(source=source, symbol=SYMBOL, samples=1, interval_seconds=1,
                  monotonic_ns=lambda: 1, wait=lambda _: None)
    for changes in ({"samples": 0}, {"samples": 61}, {"samples": True},
                    {"interval_seconds": 0}, {"interval_seconds": 6}, {"interval_seconds": 1.0}):
        refused(lambda: D.collect_timing(**(kwargs | changes)), "QUOTE_DIAGNOSTIC_BOUNDS_INVALID")
    for changes in ({"source": None}, {"wait": None}, {"monotonic_ns": None}):
        refused(lambda: D.collect_timing(**(kwargs | changes)), "QUOTE_DIAGNOSTIC_DEPENDENCIES_REQUIRED")
    assert source.calls == 0


def test_capture_cli_uses_only_public_e1_get_and_no_credential_reads():
    raw = B.receipt().raw_body
    with patch.object(keys, "read", side_effect=AssertionError("credentials forbidden")) as credentials, \
            patch.object(D, "_wall_clock", return_value=NOW), \
            F.serve({("GET", Q.ORDERBOOK_PATH): lambda call: (200, {"Date": F.DATE_HEADER}, raw)}) as calls:
        code, report, text = invoke("capture", "--symbol", SYMBOL, "--samples", "1")
    assert code == 0 and report["diagnostic_complete"] and not report["execution_ready"]
    assert len(calls) == 1 and calls[0]["method"] == "GET" and calls[0]["json_body"] is None
    assert calls[0]["url"] == "https://api.upbit.com/v1/orderbook?markets=KRW-BTC&level=0&count=30"
    assert "Authorization" not in calls[0]["headers"] and not credentials.called
    for sensitive in ("ask_price", "bid_price", "orderbook_units", "account_scope", "raw_body"):
        assert sensitive not in text


def test_raw_receipt_seam_keeps_future_stamp_and_normal_read_still_refuses():
    body = B.body(); body[0]["timestamp"] += 1
    raw = B.receipt(body).raw_body
    with F.serve({("GET", Q.ORDERBOOK_PATH): lambda call: (200, {"Date": F.DATE_HEADER}, raw)}):
        source = Q.E1UpbitQuoteSource(symbol=SYMBOL, clock=lambda: NOW)
        captured = source.read_receipt()
        assert captured.receipt.raw_body == raw and captured.requested_at == NOW and captured.checked_at == NOW
        assert "raw_body" not in repr(captured)
        B.refusal(source.read, "QUOTE_BOOK_STALE_OR_FUTURE")


def test_raw_receipt_seam_keeps_request_envelope_and_fixed_error_contract():
    receipt = B.receipt()
    answer = transport.Answer(body={}, server_utc=NOW, received_utc=NOW,
                              raw_body=receipt.raw_body, sha256=receipt.sha256)
    clock = iter((NOW-timedelta(milliseconds=40), NOW+timedelta(milliseconds=200)))
    with patch("execution_accounts.quotes.request", return_value=answer):
        captured = Q.E1UpbitQuoteSource(symbol=SYMBOL, clock=lambda: next(clock)).read_receipt()
    assert captured.requested_at == NOW-timedelta(milliseconds=40)
    assert captured.checked_at == NOW+timedelta(milliseconds=200) and captured.receipt.received_at == NOW
    for changed, code in ((replace(answer, server_utc=None), "QUOTE_SERVER_TIME_REQUIRED"),
                          (replace(answer, received_utc=NOW+timedelta(seconds=1)), "QUOTE_RECEIPT_OUTSIDE_REQUEST")):
        with patch("execution_accounts.quotes.request", return_value=changed):
            B.refusal(lambda: Q.E1UpbitQuoteSource(symbol=SYMBOL, clock=lambda: NOW).read_receipt(), code)
