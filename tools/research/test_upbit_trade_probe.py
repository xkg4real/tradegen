"""Offline A0 tests. Run from repo root with python -B -m unittest ..."""
import base64
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from email.utils import formatdate
import io
from http import client as http_client
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from tools.research import upbit_trade_probe as P


class FakeClock:
    def __init__(self, wall=1795132810.0):
        self.value = wall
        self.tick = 0.0
        self.sleeps = []

    def wall(self):
        return self.value

    def monotonic(self):
        return self.tick

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.value += seconds
        self.tick += seconds


def trade(timestamp, identity, price=100, side="ASK"):
    return {"market": "KRW-BTC", "sequential_id": identity, "timestamp": timestamp,
            "trade_price": price, "trade_volume": 0.25, "ask_bid": side}


def read_rows(root):
    return [json.loads(line)["data"] for line in (root / "observations.jsonl").read_text().splitlines()]


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "measurements"
        self.clock = FakeClock()
        self.config = P.Config("KRW-BTC")
        self.calls = []
        self.socket_guard = patch.object(socket.socket, "connect", side_effect=AssertionError("LIVE_NETWORK_FORBIDDEN"))
        self.socket_guard.start()

    def tearDown(self):
        self.socket_guard.stop()
        self.temporary.cleanup()

    def response(self, body, status=200, date=True, truncated=False):
        headers = {"Date": formatdate(self.clock.wall(), usegmt=True)} if date else {}
        headers["Remaining-Req"] = "group=trade; min=1800; sec=9"
        return P.Reply(status, headers, json.dumps(body).encode(), truncated)

    def transport(self, path, params):
        self.calls.append((path, dict(params), self.clock.monotonic()))
        self.clock.sleep(0.02)
        end = int(1795132810 * 1000)
        if path == "/v1/ticker":
            return self.response([{"market": "KRW-BTC", "trade_timestamp": end - 1000, "trade_price": 101}])
        if path == "/v1/trades/ticks":
            return self.response([trade(end - 1000, 7, 101), trade(end - 1000, 1, 100, "BID"), trade(end - 6000, 3)])
        if path == "/v1/candles/minutes/1":
            return self.response([{"market": "KRW-BTC", "candle_date_time_utc": "2026-11-20T00:00:00", "high_price": 102, "low_price": 100}])
        return self.response({"error": "not_found"}, status=404)

    def test_full_six_sample_measurement_preserves_raw_and_no_authority(self):
        with P.Archive(self.root, self.config) as archive:
            result = P.Probe(self.config, self.transport, archive, self.clock).run()
        self.assertEqual(result, {"completed_cycles": 1, "status": "REVIEW_REQUIRED", "execution_ready": False})
        rows = read_rows(self.root)
        samples = [x for x in rows if x["kind"] == "sample"]
        self.assertEqual(len(samples), 6)
        self.assertEqual([x["target_settle_seconds"] for x in samples], [.5, .5, 1, 1, 2, 2])
        self.assertEqual(samples[0]["same_ms_multi_price"], {str(1795132809000): ["100", "101"]})
        self.assertTrue(samples[0]["ticker_match"])
        self.assertTrue(all(x["ask_bid_semantics"] == "UNRESOLVED_WITH_PUBLIC_ONLY_DATA" for x in samples))
        report = next(x for x in rows if x["kind"] == "cycle_report")
        self.assertTrue(all(x["equal"] for x in report["pairs"]))
        self.assertFalse(report["candle_finality_proven"])
        self.assertFalse(report["source_complete"])
        self.assertEqual(report["cross_settle_comparison"], "INDEPENDENT_WINDOWS_NOT_COMPARED")
        self.assertEqual(report["whole_account_unit_timing"], "NOT_MEASURED")
        raw = next(x for x in rows if x["kind"] == "response")
        self.assertEqual(P.hashlib.sha256(base64.b64decode(raw["body_base64"])).hexdigest(), raw["body_sha256"])

    def test_start_to_start_rate_ceiling_and_actual_settle_are_recorded(self):
        config = P.Config("KRW-BTC", requests_per_second=2)
        with P.Archive(self.root, config) as archive:
            P.Probe(config, self.transport, archive, self.clock).run()
        self.assertTrue(all(b[2] - a[2] >= .499999 for a, b in zip(self.calls, self.calls[1:])))
        samples = [x for x in read_rows(self.root) if x["kind"] == "sample"]
        self.assertAlmostEqual(samples[0]["actual_trade_settle_seconds"], .5)
        self.assertTrue(samples[0]["trade_settle_target_met"])
        self.assertGreater(samples[-1]["actual_trade_settle_seconds"], samples[-1]["target_settle_seconds"])
        self.assertFalse(samples[-1]["trade_settle_target_met"])
        report = next(x for x in read_rows(self.root) if x["kind"] == "cycle_report")
        self.assertTrue(report["all_first_trade_settle_targets_met"])
        self.assertEqual(len({x["end_ms"] for x in report["pairs"]}), 3)
        self.assertEqual([round(x["actual_trade_settle_seconds"], 3) for x in samples[::2]], [.5, 1.0, 2.0])

    def test_ticker_mismatch_is_a_no_go_in_the_returned_summary(self):
        def transport(path, params):
            if path == "/v1/ticker":
                return self.response([{"market": "KRW-BTC", "trade_timestamp": 1795132809000, "trade_price": 999}])
            return self.transport(path, params)
        with P.Archive(self.root, self.config) as archive:
            result = P.Probe(self.config, transport, archive, self.clock).run()
        self.assertEqual(result["status"], "NO_GO_OBSERVED")
        report = next(x for x in read_rows(self.root) if x["kind"] == "cycle_report")
        self.assertIn("TICKER_MISMATCH", report["observed_blockers"])

    def test_resume_keeps_prefix_including_decimal_timing(self):
        with P.Archive(self.root, self.config) as archive:
            P.Probe(self.config, self.transport, archive, self.clock).run()
        before = (self.root / "observations.jsonl").read_bytes()
        with P.Archive(self.root, self.config) as archive:
            archive.append({"kind": "resume_check"})
        self.assertTrue((self.root / "observations.jsonl").read_bytes().startswith(before))

    def test_resume_configuration_change_refused(self):
        with P.Archive(self.root, self.config):
            pass
        with self.assertRaisesRegex(P.ProbeError, "ARCHIVE_CONFIG_MISMATCH"):
            P.Archive(self.root, P.Config("KRW-ETH"))

    def test_second_writer_refused_without_removing_first_lock(self):
        with P.Archive(self.root, self.config):
            with self.assertRaises(FileExistsError):
                P.Archive(self.root, self.config)
            self.assertTrue((self.root / ".probe.lock").exists())

    def test_torn_row_is_preserved_and_not_resumed(self):
        with P.Archive(self.root, self.config):
            pass
        path = self.root / "observations.jsonl"
        with path.open("ab") as stream:
            stream.write(b'{"partial":')
        before = path.read_bytes()
        with self.assertRaisesRegex(P.ProbeError, "ARCHIVE_INCOMPLETE"):
            P.Archive(self.root, self.config)
        self.assertEqual(path.read_bytes(), before)

    def test_corrupted_hash_refused(self):
        with P.Archive(self.root, self.config):
            pass
        path = self.root / "observations.jsonl"
        path.write_bytes(path.read_bytes().replace(b"KRW-BTC", b"KRW-ETH"))
        with self.assertRaisesRegex(P.ProbeError, "ARCHIVE_INVALID"):
            P.Archive(self.root, self.config)

    def test_real_owner_home_paths_refused_without_creation(self):
        for label in (".tradegen", ".nextgen"):
            target = self.root / label / "probe"
            with self.assertRaisesRegex(P.ProbeError, "ARCHIVE_PATH_REFUSED"):
                P.Archive(target, self.config)
            self.assertFalse(target.exists())

    def test_symlink_output_refused(self):
        target = Path(self.temporary.name) / "real"
        target.mkdir()
        try:
            self.root.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(P.ProbeError, "ARCHIVE_PATH_REFUSED"):
            P.Archive(self.root, self.config)

    def test_429_and_418_stop_after_one_request_and_retain_retry_after(self):
        for status in (429, 418):
            root = self.root / str(status)
            calls = []
            def transport(path, params):
                calls.append(path)
                return P.Reply(status, {"Retry-After": "30"}, b'{"error":"limited"}')
            with P.Archive(root, self.config) as archive:
                with self.assertRaisesRegex(P.ProbeStop, "RATE_LIMIT_STOP_" + str(status)):
                    P.Probe(self.config, transport, archive, self.clock).run()
            self.assertEqual(len(calls), 1)
            rows = read_rows(root)
            self.assertEqual(rows[-1]["code"], "RATE_LIMIT_STOP_" + str(status))
            self.assertEqual(rows[-2]["headers"]["retry-after"], "30")

    def test_network_exception_retained_without_sensitive_exception_text(self):
        def fail(*args):
            raise OSError("private_path_or_token")
        with P.Archive(self.root, self.config) as archive:
            with self.assertRaisesRegex(P.ProbeStop, "TRANSPORT_FAILED"):
                P.Probe(self.config, fail, archive, self.clock).run()
        self.assertNotIn("private_path_or_token", (self.root / "observations.jsonl").read_text())
        self.assertEqual(read_rows(self.root)[-2]["error"], "TRANSPORT_FAILED")

    def test_bounded_page_limit_never_means_complete(self):
        config = P.Config("KRW-BTC", max_pages=1)
        end = int(self.clock.wall() * 1000)
        def transport(*args):
            return self.response([trade(end - 100, 7)])
        with P.Archive(self.root, config) as archive:
            walked = P.Probe(config, transport, archive, self.clock).walk(end - 5000, end, "test")
        self.assertFalse(walked["range_walk_bounded"])
        self.assertFalse(walked["source_complete"])

    def test_pagination_uses_received_last_id_not_numeric_order_and_deduplicates(self):
        end = int(self.clock.wall() * 1000)
        pages = [[trade(end - 1000, 800), trade(end - 2000, 999)],
                 [trade(end - 2000, 999), trade(end - 6000, 1)]]
        calls = []
        def transport(path, params):
            calls.append(dict(params))
            return self.response(pages[len(calls) - 1])
        with P.Archive(self.root, self.config) as archive:
            walked = P.Probe(self.config, transport, archive, self.clock).walk(end - 5000, end, "test")
        self.assertEqual(calls[1]["cursor"], "999")
        self.assertEqual(len(walked["rows"]), 2)
        self.assertTrue(walked["range_walk_bounded"])

    def test_cursor_loop_refused_after_retaining_responses(self):
        end = int(self.clock.wall() * 1000)
        with P.Archive(self.root, self.config) as archive:
            probe = P.Probe(self.config, lambda *_: self.response([trade(end - 1000, 4)]), archive, self.clock)
            with self.assertRaisesRegex(P.ProbeStop, "CURSOR_NOT_PROGRESSING"):
                probe.walk(end - 5000, end, "test")
        self.assertEqual(sum(x["kind"] == "response" for x in read_rows(self.root)), 2)

    def test_same_id_changed_is_refused(self):
        end = int(self.clock.wall() * 1000)
        count = 0
        def transport(*args):
            nonlocal count
            count += 1
            return self.response([trade(end - 1000, 4, 100 + count)])
        with P.Archive(self.root, self.config) as archive:
            with self.assertRaisesRegex(P.ProbeStop, "TRADE_ID_CHANGED"):
                P.Probe(self.config, transport, archive, self.clock).walk(end - 5000, end, "test")

    def test_0900_kst_uses_both_utc_days_and_omits_ambiguous_to_at_midnight(self):
        midnight = datetime(2026, 11, 20, tzinfo=timezone.utc).timestamp()
        self.clock = FakeClock(midnight + 2)
        calls = []
        def transport(path, params):
            calls.append(dict(params))
            stamp = int((midnight - 10 if params.get("days_ago", 0) == 1 else midnight - 1) * 1000)
            return self.response([trade(stamp, len(calls))])
        with P.Archive(self.root, self.config) as archive:
            P.Probe(self.config, transport, archive, self.clock).walk(int((midnight - 3) * 1000), int((midnight + 2) * 1000), "test")
        self.assertEqual([x.get("days_ago") for x in calls], [1, None])
        self.assertNotIn("to", calls[0])
        self.assertEqual(calls[1]["to"], "00:00:03")

    def test_server_day_mismatch_refused(self):
        def transport(*args):
            return P.Reply(200, {"Date": formatdate(self.clock.wall() + 86400, usegmt=True)}, b"[]")
        end = int(self.clock.wall() * 1000)
        with P.Archive(self.root, self.config) as archive:
            with self.assertRaisesRegex(P.ProbeStop, "SERVER_DAY_MISMATCH"):
                P.Probe(self.config, transport, archive, self.clock).walk(end - 5000, end, "test")

    def test_missing_date_cannot_support_day_walk(self):
        end = int(self.clock.wall() * 1000)
        with P.Archive(self.root, self.config) as archive:
            with self.assertRaisesRegex(P.ProbeStop, "DATE_HEADER_REQUIRED"):
                P.Probe(self.config, lambda *_: self.response([], date=False), archive, self.clock).walk(end - 5000, end, "test")

    def test_trailing_slash_is_opt_in_and_observed_refusal_preserved(self):
        config = P.Config("KRW-BTC", trailing_slash=True)
        with P.Archive(self.root, config) as archive:
            P.Probe(config, self.transport, archive, self.clock).run()
        self.assertEqual(self.calls[0][0], "/v1/trades/ticks/")
        result = next(x for x in read_rows(self.root) if x["kind"] == "slash_result")
        self.assertEqual(result, {"kind": "slash_result", "status": 404, "refused": True})

    def test_oversize_and_malformed_responses_leave_raw_observations(self):
        for label, reply, code in (("large", P.Reply(200, {}, b"[]", True), "RESPONSE_TOO_LARGE"),
                                   ("json", P.Reply(200, {}, b"{broken"), "MALFORMED_RESPONSE")):
            root = self.root / label
            with P.Archive(root, self.config) as archive:
                with self.assertRaisesRegex(P.ProbeError, code):
                    P.Probe(self.config, lambda *_: reply, archive, self.clock).run()
            self.assertTrue(any(x["kind"] == "response" for x in read_rows(root)))

    def test_timestamp_boundaries_are_half_open(self):
        end = int(self.clock.wall() * 1000)
        rows = [trade(end, 1), trade(end - 1, 2), trade(end - 5000, 3), trade(end - 5001, 4)]
        with P.Archive(self.root, self.config) as archive:
            result = P.Probe(self.config, lambda *_: self.response(rows), archive, self.clock).walk(end - 5000, end, "test")
        self.assertEqual({x["id"] for x in result["rows"]}, {2, 3})

    def test_config_numeric_and_market_boundaries(self):
        for config in (P.Config("KRW-BTC?evil"), P.Config("BTC-ETH"), P.Config("KRW-BTC", requests_per_second=5.01),
                       P.Config("KRW-BTC", requests_per_second=float("nan")), P.Config("KRW-BTC", max_pages=True)):
            with self.assertRaises(P.ProbeError):
                config.validate()

    def test_wire_parser_refuses_duplicates_nan_bool_and_wrong_market(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(P.ProbeError):
                P._json(raw)
        for row in ({**trade(1, 1), "timestamp": True}, {**trade(1, 1), "market": "KRW-ETH"},
                    {**trade(1, 1), "trade_price": "Infinity"}):
            with self.assertRaises(P.ProbeError):
                P.parse_trades([row], "KRW-BTC")

    def test_numeric_exactness_is_independent_of_decimal_context(self):
        precise = "12345.123456789012345678901234567890123456789"
        self.assertEqual(P._number(precise), precise)
        self.assertEqual(P._number("100.000"), "100")
        for invalid in ("1e1000000000", "1e-1000000000", "1" * 129):
            with self.assertRaisesRegex(P.ProbeError, "MALFORMED_RESPONSE"):
                P._number(invalid)

    def test_first_seen_uses_network_receipt_not_storage_latency(self):
        class SlowArchive:
            def append(inner, _):
                self.clock.sleep(3)
        end = int(self.clock.wall() * 1000)
        probe = P.Probe(self.config, lambda *_: self.response([trade(end - 6000, 1)]), SlowArchive(), self.clock)
        probe.walk(end - 5000, end, "test")
        self.assertEqual(probe.first_seen[1], 1795132810.0)

    def test_previous_candle_does_not_claim_target_minute_stability(self):
        with P.Archive(self.root, self.config) as archive:
            P.Probe(self.config, self.transport, archive, self.clock).run()
        report = next(x for x in read_rows(self.root) if x["kind"] == "cycle_report")
        self.assertTrue(all(not x["candle_target_match"] for x in report["pairs"]))
        self.assertTrue(all(x["candle_stable_in_observation_window"] is None for x in report["pairs"]))

    def test_no_cli_network_without_explicit_option(self):
        with patch.object(P, "public_request", side_effect=AssertionError("should not call")):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                P.main(["--market", "KRW-BTC", "--output", str(self.root)])
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(self.root.exists())

    def test_transport_rejects_arbitrary_paths_or_query_credentials(self):
        with patch.object(P.request, "build_opener", side_effect=AssertionError("network constructed")):
            for path, params in (("https://evil.test", {}), ("/v1/orders", {}), ("/v1/ticker", {"api_key": "x"})):
                with self.assertRaises(P.ProbeError):
                    P.public_request(path, params)

    def test_no_redirect_and_no_proxy_are_installed(self):
        class Response:
            status = 200
            headers = {"Date": "Fri, 20 Nov 2026 00:00:10 GMT", "Authorization": "discard"}
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def read(self, count): return b"[]"
        class Opener:
            def open(self, req, timeout):
                self_req.append(req)
                return Response()
        self_req = []
        with patch.object(P.request, "build_opener", return_value=Opener()) as make:
            reply = P.public_request("/v1/ticker", {"markets": "KRW-BTC"})
        handlers = make.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], P._NoRedirect)
        self.assertEqual(self_req[0].method, "GET")
        self.assertEqual(self_req[0].full_url, "https://api.upbit.com/v1/ticker?markets=KRW-BTC")
        self.assertFalse(self_req[0].has_header("Origin"))
        self.assertNotIn("authorization", reply.headers)

    def memory_http_response(self, wire):
        class MemorySocket:
            def makefile(self, mode):
                return io.BytesIO(wire)
        response = http_client.HTTPResponse(MemorySocket())
        response.begin()
        return response

    def test_short_content_length_body_rejected_even_when_json_is_valid(self):
        response = self.memory_http_response(b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n[]")
        with patch.object(P.request, "build_opener") as make:
            make.return_value.open.return_value = response
            with P.Archive(self.root, self.config) as archive:
                with self.assertRaisesRegex(P.ProbeStop, "HTTP_BODY_INCOMPLETE"):
                    P.Probe(self.config, P.public_request, archive, self.clock).run()
        rows = read_rows(self.root)
        observation = next(x for x in rows if x["kind"] == "response")
        self.assertEqual(base64.b64decode(observation["body_base64"]), b"[]")
        self.assertEqual(observation["headers"]["content-length"], "10")
        self.assertEqual(observation["error"], "HTTP_BODY_INCOMPLETE")
        self.assertEqual(rows[-1]["code"], "HTTP_BODY_INCOMPLETE")
        self.assertFalse(any(x["kind"] == "sample" for x in rows))

    def test_incomplete_chunked_body_keeps_available_prefix_and_cli_stops(self):
        response = self.memory_http_response(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n[]\r\n4\r\na")
        output = io.StringIO()
        with patch.object(P.request, "build_opener") as make:
            make.return_value.open.return_value = response
            with redirect_stdout(output):
                code = P.main(["--market", "KRW-BTC", "--output", str(self.root), "--allow-public-network"])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "HTTP_BODY_INCOMPLETE")
        rows = read_rows(self.root)
        observation = next(x for x in rows if x["kind"] == "response")
        self.assertEqual(base64.b64decode(observation["body_base64"]), b"[]")
        self.assertEqual(observation["error"], "HTTP_BODY_INCOMPLETE")
        self.assertEqual(rows[-1]["kind"], "session_stop")
        self.assertEqual(rows[-1]["code"], "HTTP_BODY_INCOMPLETE")
        self.assertFalse((self.root / ".probe.lock").exists())

    def test_protocol_failure_before_headers_is_sanitized_and_logged(self):
        with patch.object(P.request, "build_opener") as make:
            make.return_value.open.side_effect = http_client.BadStatusLine("private_exception_detail")
            with P.Archive(self.root, self.config) as archive:
                with self.assertRaisesRegex(P.ProbeStop, "TRANSPORT_FAILED"):
                    P.Probe(self.config, P.public_request, archive, self.clock).run()
        rows = read_rows(self.root)
        self.assertEqual(rows[-2]["error"], "TRANSPORT_FAILED")
        self.assertEqual(rows[-1]["code"], "TRANSPORT_FAILED")
        self.assertNotIn("private_exception_detail", (self.root / "observations.jsonl").read_text())

    def test_transport_incomplete_read_exposes_only_available_prefix(self):
        def transport(*_):
            raise http_client.IncompleteRead(b"partial", 20)
        with P.Archive(self.root, self.config) as archive:
            with self.assertRaisesRegex(P.ProbeStop, "HTTP_BODY_INCOMPLETE"):
                P.Probe(self.config, transport, archive, self.clock).run()
        rows = read_rows(self.root)
        self.assertEqual(base64.b64decode(rows[-2]["body_base64"]), b"partial")
        self.assertNotIn("status", rows[-2])
        self.assertNotIn("headers", rows[-2])
        self.assertEqual(rows[-1]["code"], "HTTP_BODY_INCOMPLETE")

    def test_body_read_failure_preserves_headers_without_claiming_complete_bytes(self):
        response = self.memory_http_response(b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\n[]")
        with patch.object(P.request, "build_opener") as make, patch.object(response, "read", side_effect=OSError("private_detail")):
            make.return_value.open.return_value = response
            with P.Archive(self.root, self.config) as archive:
                with self.assertRaisesRegex(P.ProbeStop, "HTTP_RESPONSE_FAILED"):
                    P.Probe(self.config, P.public_request, archive, self.clock).run()
        rows = read_rows(self.root)
        observation = next(x for x in rows if x["kind"] == "response")
        self.assertEqual(observation["headers"]["content-length"], "10")
        self.assertEqual(observation["body_base64"], "")
        self.assertEqual(observation["error"], "HTTP_RESPONSE_FAILED")
        self.assertEqual(rows[-1]["code"], "HTTP_RESPONSE_FAILED")
        self.assertNotIn("private_detail", (self.root / "observations.jsonl").read_text())

    def test_partial_prefix_is_bounded_and_its_hash_covers_only_saved_bytes(self):
        response = self.memory_http_response(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")
        with patch.object(P.request, "build_opener") as make, patch.object(response, "read", side_effect=http_client.IncompleteRead(b"x" * (P.MAX_BODY + 32))):
            make.return_value.open.return_value = response
            with P.Archive(self.root, self.config) as archive:
                with self.assertRaisesRegex(P.ProbeStop, "HTTP_BODY_INCOMPLETE"):
                    P.Probe(self.config, P.public_request, archive, self.clock).run()
        observation = next(x for x in read_rows(self.root) if x["kind"] == "response")
        self.assertTrue(observation["body_truncated"])
        raw = base64.b64decode(observation["body_base64"])
        self.assertEqual(len(raw), P.MAX_BODY)
        self.assertEqual(P.hashlib.sha256(raw).hexdigest(), observation["body_sha256"])

    def test_complete_content_length_and_chunked_responses_still_parse(self):
        for wire in (b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n[]",
                     b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n2\r\n[]\r\n0\r\n\r\n"):
            response = self.memory_http_response(wire)
            with patch.object(P.request, "build_opener") as make:
                make.return_value.open.return_value = response
                reply = P.public_request("/v1/ticker", {"markets": "KRW-BTC"})
            self.assertIsNone(reply.error)
            self.assertEqual(reply.body, b"[]")
            self.assertFalse(reply.truncated)

    def test_invalid_content_length_has_fixed_refusal(self):
        response = self.memory_http_response(b"HTTP/1.1 200 OK\r\nContent-Length: bad\r\n\r\n[]")
        with patch.object(P.request, "build_opener") as make:
            make.return_value.open.return_value = response
            with P.Archive(self.root, self.config) as archive:
                with self.assertRaisesRegex(P.ProbeStop, "HTTP_LENGTH_INVALID"):
                    P.Probe(self.config, P.public_request, archive, self.clock).run()
        self.assertEqual(read_rows(self.root)[-1]["code"], "HTTP_LENGTH_INVALID")


if __name__ == "__main__":
    unittest.main()
