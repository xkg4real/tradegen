"""Synthetic OQ18 observations; no keys, account state, or live network used."""
import asyncio
import base64
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import hmac
import io
import json
from pathlib import Path
import socket
import ssl
import tempfile
import unittest
from unittest.mock import patch

from websockets.datastructures import Headers
from websockets.exceptions import InvalidStatus, ConnectionClosedOK
from websockets.frames import Close
from websockets.http11 import Response

from tools.research import upbit_myorder_probe as P


PRIVATE = "private-owner-order-id-or-sensitive-value"
DUMMY = P.Credentials("synthetic-access-key", "synthetic-secret-key")


def event(state="trade"):
    return json.dumps({"type": "myOrder", "state": state, "uuid": PRIVATE, "trade_uuid": PRIVATE,
                       "price": PRIVATE, "volume": PRIVATE, "trade_fee": PRIVATE, "is_maker": True,
                       "code": "KRW-PRIVATE", "unknown_private_field": PRIVATE})


class FakeConnection:
    def __init__(self, messages=()):
        self.messages = list(messages)
        self.sent = []
        self.closed = False
        self.aborted = False
        self.transport = self

    async def send(self, message):
        self.sent.append(message)

    async def recv(self):
        if not self.messages:
            raise TimeoutError()
        item = self.messages.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    async def close(self):
        self.closed = True

    def abort(self):
        self.aborted = True


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.rows = []
        self.calls = []
        self.connection = FakeConnection()
        self.guard = patch.object(socket.socket, "connect", side_effect=AssertionError("LIVE_NETWORK_FORBIDDEN"))
        self.guard.start()
        self.temporary = tempfile.TemporaryDirectory()
        self.output = Path(self.temporary.name) / "observation.jsonl"

    def tearDown(self):
        self.guard.stop()
        self.temporary.cleanup()

    async def connector(self, uri, **kwargs):
        self.calls.append((uri, kwargs))
        return self.connection

    def observe(self, messages=(), **kwargs):
        self.connection = FakeConnection(messages)
        return asyncio.run(P.observe(P.Config(1, kwargs.pop("max_events", 10)), DUMMY, self.rows.append,
                                     connector=kwargs.pop("connector", self.connector), now=lambda: "2026-11-23T00:00:00+00:00", **kwargs))

    def assert_private_values_absent(self, result):
        encoded = json.dumps([self.rows, result])
        for forbidden in (PRIVATE, DUMMY.access_key, DUMMY.secret_key, "KRW-PRIVATE", "unknown_private_field", "Authorization", "Bearer "):
            self.assertNotIn(forbidden, encoded)

    def test_silent_connection_never_confirms_subscription_or_permission(self):
        result = self.observe()
        self.assertEqual(result["status"], "SILENT_ENTITLEMENT_UNPROVEN")
        self.assertEqual(result["connection_status"], "CONNECTED")
        self.assertEqual(result["subscription_status"], "SENT_UNCONFIRMED")
        self.assertFalse(result["server_subscription_acknowledged"])
        self.assertFalse(result["entitlement_confirmed"])
        self.assertEqual(result["provider_permission_state"], "UNKNOWN")
        self.assertEqual(result["myorder_event_count"], 0)
        self.assertTrue(self.connection.closed)
        self.assert_private_values_absent(result)

    def test_observed_event_keeps_metadata_only_and_no_fill_authority(self):
        result = self.observe([event()])
        self.assertEqual(result["status"], "MYORDER_EVENT_OBSERVED")
        self.assertEqual(result["subscription_status"], "MYORDER_EVENT_OBSERVED")
        self.assertEqual(result["myorder_event_count"], 1)
        self.assertEqual(result["provider_permission_state"], "UNKNOWN")
        self.assertFalse(result["fill_authority"])
        self.assertFalse(result["source_complete"])
        self.assertFalse(result["execution_ready"])
        row = next(x for x in self.rows if x["kind"] == "myorder_metadata")
        self.assertEqual(row["state"], "trade")
        self.assertTrue(row["expected_fields_present"]["is_maker"])
        self.assertNotIn("is_maker", row)
        self.assert_private_values_absent(result)

    def test_only_one_myorder_subscription_with_no_codes_or_order_command(self):
        self.observe([event("wait"), event("done")])
        self.assertEqual(len(self.connection.sent), 1)
        message = json.loads(self.connection.sent[0])
        self.assertEqual(message[1:], [{"type": "myOrder"}, {"format": "DEFAULT"}])
        self.assertEqual(set(message[0]), {"ticket"})
        self.assertEqual(len(self.calls), 1)

    def test_fixed_endpoint_tls_no_proxy_origin_or_compression_logging(self):
        self.observe()
        uri, kwargs = self.calls[0]
        self.assertEqual(uri, "wss://api.upbit.com/websocket/v1/private")
        self.assertIsNone(kwargs["proxy"])
        self.assertIsNone(kwargs["origin"])
        self.assertIsNone(kwargs["compression"])
        self.assertTrue(kwargs["ssl"].check_hostname)
        self.assertEqual(kwargs["ssl"].verify_mode, ssl.CERT_REQUIRED)
        self.assertEqual(kwargs["max_size"], 65536)
        self.assertEqual(kwargs["max_queue"], 8)
        self.assertTrue(kwargs["logger"].disabled)
        self.assertFalse(kwargs["logger"].propagate)
        self.assertEqual(set(kwargs["additional_headers"]), {"Authorization"})

    def test_jwt_raw_secret_hs512_fresh_nonce_and_no_query_or_order_claim(self):
        def decode(part):
            return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))
        one = P.authorization(DUMMY)[7:]
        two = P.authorization(DUMMY)[7:]
        a, b, signature = one.split(".")
        self.assertEqual(json.loads(decode(a)), {"alg": "HS512", "typ": "JWT"})
        payload = json.loads(decode(b))
        self.assertEqual(set(payload), {"access_key", "nonce"})
        self.assertEqual(payload["access_key"], DUMMY.access_key)
        self.assertNotEqual(payload["nonce"], json.loads(decode(two.split(".")[1]))["nonce"])
        expected = hmac.new(DUMMY.secret_key.encode(), (a + "." + b).encode(), hashlib.sha512).digest()
        self.assertEqual(decode(signature), expected)
        self.assertNotIn(DUMMY.secret_key, repr(DUMMY))
        self.assertNotIn(DUMMY.access_key, repr(DUMMY))

    def test_event_limit_stops_without_consuming_remaining_events(self):
        result = self.observe([event(), event(), event()], max_events=2)
        self.assertEqual(result["stop_reason"], "EVENT_LIMIT")
        self.assertEqual(result["myorder_event_count"], 2)
        self.assertEqual(len(self.connection.messages), 1)
        self.assertTrue(self.connection.closed)

    def test_schema_failures_never_log_payloads(self):
        for raw, expected in (("broken-" + PRIVATE, "MESSAGE_FORMAT_INVALID"),
                              ('{"type":"myOrder","state":"trade","state":"done"}', "MESSAGE_FORMAT_INVALID"),
                              (json.dumps({"type": "myAsset", "uuid": PRIVATE}), "UNEXPECTED_STREAM_MESSAGE"),
                              (json.dumps({"type": "myOrder", "state": "trade"}), "MYORDER_SCHEMA_UNRECOGNIZED"),
                              (b"x" * (P.MAX_MESSAGE + 1), "MESSAGE_TOO_LARGE")):
            with self.subTest(expected=expected):
                result = self.observe([raw])
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["myorder_event_count"], 0)
                self.assertTrue(self.connection.closed)
                self.assert_private_values_absent(result)

    def test_server_error_name_allowlist_does_not_forward_message_or_unknown_name(self):
        result = self.observe([json.dumps({"error": {"name": "INVALID_AUTH", "message": PRIVATE}})])
        self.assertEqual(result["status"], "AUTH_REJECTED")
        self.assertEqual(result["subscription_status"], "REJECTED")
        self.assert_private_values_absent(result)
        result = self.observe([json.dumps({"error": {"name": PRIVATE, "message": PRIVATE}})])
        self.assertEqual(result["status"], "SUBSCRIPTION_REJECTED")
        self.assert_private_values_absent(result)

    def test_401_403_do_not_guess_specific_permission(self):
        for code in (401, 403):
            async def denied(*args, **kwargs):
                raise InvalidStatus(Response(code, PRIVATE, Headers(), body=PRIVATE.encode()))
            result = self.observe(connector=denied)
            self.assertEqual(result["status"], "AUTH_OR_PERMISSION_REJECTED")
            self.assertEqual(result["provider_permission_state"], "UNKNOWN")
            self.assertEqual(result["subscription_status"], "NOT_SENT")
            self.assert_private_values_absent(result)

    def test_429_418_forward_numeric_wait_only_no_reconnect(self):
        for code in (429, 418):
            calls = []
            async def limited(*args, **kwargs):
                calls.append(1)
                raise InvalidStatus(Response(code, PRIVATE, Headers({"Retry-After": "30", "Set-Cookie": PRIVATE}), body=PRIVATE.encode()))
            result = self.observe(connector=limited)
            self.assertEqual(result["status"], "RATE_LIMITED_STOP")
            self.assertEqual(result["retry_after_seconds"], 30)
            self.assertFalse(result["automatic_reconnect"])
            self.assertEqual(calls, [1])
            self.assert_private_values_absent(result)

    def test_redirect_is_refused_by_actual_pinned_connector(self):
        cls = P.private_connector()
        redirect = InvalidStatus(Response(302, "Found", Headers({"Location": "wss://other.invalid/"})))
        self.assertIs(cls.process_redirect(None, redirect), redirect)
        async def redirected(*args, **kwargs):
            raise redirect
        result = self.observe(connector=redirected)
        self.assertEqual(result["status"], "REDIRECT_REFUSED")
        self.assertEqual(result["subscription_status"], "NOT_SENT")

    def test_connection_error_does_not_echo_exception(self):
        async def failed(*args, **kwargs):
            raise OSError(PRIVATE)
        result = self.observe(connector=failed)
        self.assertEqual(result["status"], "TRANSPORT_FAILED")
        self.assert_private_values_absent(result)

    def test_closed_stream_preserves_observation_and_excludes_close_reason(self):
        result = self.observe([event(), ConnectionClosedOK(Close(1000, PRIVATE), Close(1000, PRIVATE), True)])
        self.assertEqual(result["status"], "CONNECTION_CLOSED")
        self.assertEqual(result["myorder_event_count"], 1)
        self.assert_private_values_absent(result)

    def test_duration_budget_prevents_subscription_if_connect_used_it(self):
        ticks = iter([0, 2, 2])
        result = self.observe(monotonic=lambda: next(ticks))
        self.assertEqual(result["status"], "DURATION_EXPIRED_BEFORE_SUBSCRIPTION")
        self.assertEqual(self.connection.sent, [])

    def test_send_timeout_is_terminal_and_closes_connection(self):
        class FailingSend(FakeConnection):
            async def send(self, message):
                raise TimeoutError(PRIVATE)
        self.connection = FailingSend()
        result = asyncio.run(P.observe(P.Config(1, 10), DUMMY, self.rows.append, connector=self.connector))
        self.assertEqual(result["status"], "SUBSCRIPTION_SEND_TIMEOUT")
        self.assertEqual(result["subscription_status"], "NOT_SENT")
        self.assertTrue(self.connection.closed)
        self.assert_private_values_absent(result)

    def test_real_async_receive_deadline_cancels_wait_and_closes(self):
        class QuietConnection(FakeConnection):
            cancelled = False
            async def recv(self):
                try:
                    await asyncio.Future()
                except asyncio.CancelledError:
                    self.cancelled = True
                    raise
        self.connection = QuietConnection()
        result = asyncio.run(P.observe(P.Config(1, 10), DUMMY, self.rows.append, connector=self.connector))
        self.assertEqual(result["status"], "SILENT_ENTITLEMENT_UNPROVEN")
        self.assertTrue(self.connection.cancelled)
        self.assertTrue(self.connection.closed)
        self.assertGreaterEqual(result["elapsed_seconds"], .9)
        self.assertLess(result["elapsed_seconds"], 3)

    def test_real_async_connect_deadline_does_not_send_subscription(self):
        cancelled = []
        async def blocked_connector(*args, **kwargs):
            try:
                await asyncio.Future()
            except asyncio.CancelledError:
                cancelled.append(True)
                raise
        result = self.observe(connector=blocked_connector)
        self.assertEqual(result["status"], "CONNECT_TIMEOUT")
        self.assertEqual(result["subscription_status"], "NOT_SENT")
        self.assertEqual(cancelled, [True])
        self.assertEqual(self.connection.sent, [])

    def test_failed_close_aborts_transport(self):
        class FailedClose(FakeConnection):
            async def close(self):
                raise OSError(PRIVATE)
        self.connection = FailedClose()
        result = asyncio.run(P.observe(P.Config(1, 10), DUMMY, self.rows.append, connector=self.connector))
        self.assertEqual(result["close_status"], "CLOSE_ABORTED")
        self.assertTrue(self.connection.aborted)
        self.assert_private_values_absent(result)

    def test_no_private_default_or_credential_prompt(self):
        with patch.object(P, "read_credentials", side_effect=AssertionError("credential access forbidden")):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                P.main(["--output", str(self.output)])
        self.assertEqual(caught.exception.code, 2)
        self.assertFalse(self.output.exists())

    def test_dependency_check_never_asks_for_keys_or_connects(self):
        with patch.object(P, "read_credentials", side_effect=AssertionError("key access")), patch.object(P, "private_connector", side_effect=AssertionError("network")):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(P.main(["--check-dependencies"]), 0)
        self.assertEqual(json.loads(output.getvalue())["websockets"], "16.0")

    def test_existing_output_refused_before_credential_prompt(self):
        self.output.write_bytes(b"existing evidence")
        with patch.object(P, "read_credentials", side_effect=AssertionError("must not ask for keys")):
            with redirect_stdout(io.StringIO()):
                result = P.main(["--output", str(self.output), "--allow-private-network"])
        self.assertEqual(result, 2)
        self.assertEqual(self.output.read_bytes(), b"existing evidence")

    def test_nonterminal_and_getpass_fallback_refused(self):
        with patch.object(P.sys.stdin, "isatty", return_value=False), patch.object(P.getpass, "getpass", side_effect=AssertionError("prompt")):
            with self.assertRaisesRegex(P.ProbeError, "PRIVATE_TERMINAL_REQUIRED"):
                P.read_credentials()
        with patch.object(P.sys.stdin, "isatty", return_value=True), patch.object(P.getpass, "getpass", side_effect=P.getpass.GetPassWarning(PRIVATE)):
            with self.assertRaisesRegex(P.ProbeError, "PRIVATE_TERMINAL_REQUIRED"):
                P.read_credentials()

    def test_output_file_is_exclusive_and_contains_redacted_metadata(self):
        with P.ObservationLog(self.output) as log:
            result = asyncio.run(P.observe(P.Config(1, 10), DUMMY, log.emit, connector=self.connector))
        self.assertEqual(result["status"], "SILENT_ENTITLEMENT_UNPROVEN")
        before = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            P.ObservationLog(self.output)
        self.assertEqual(self.output.read_bytes(), before)
        self.assertNotIn(DUMMY.access_key.encode(), before)
        self.assertNotIn(DUMMY.secret_key.encode(), before)
        self.assertEqual(json.loads(before.splitlines()[-1])["kind"], "session_end")

    def test_home_paths_and_symlinks_refused(self):
        for label in (".tradegen", ".nextgen"):
            with self.assertRaisesRegex(P.ProbeError, "OUTPUT_PATH_REFUSED"):
                P.ObservationLog(self.output.parent / label / "probe.jsonl")
        target = self.output.parent / "target"
        target.mkdir()
        alias = self.output.parent / "alias"
        try:
            alias.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("symlink privilege unavailable")
        with self.assertRaisesRegex(P.ProbeError, "OUTPUT_PATH_REFUSED"):
            P.ObservationLog(alias / "probe.jsonl")

    def test_config_and_credentials_validation(self):
        for config in (P.Config(0), P.Config(3601), P.Config(True), P.Config(10, 1001)):
            with self.assertRaises(P.ProbeError):
                config.validate()
        for key in ("short", "has whitespace", "has\nnewline", "x" * 513):
            with self.assertRaises(P.ProbeError):
                P.Credentials(key, "synthetic-secret").validate()


if __name__ == "__main__":
    unittest.main()
