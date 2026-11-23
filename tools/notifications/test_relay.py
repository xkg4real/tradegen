"""Offline provider-protocol, source integration and crash/retry tests."""
import base64
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

from . import providers, relay


EVENT = "1" * 64
ORIGIN = "https://approval.example.org"
TOKEN = "123456:" + "a" * 32


def decoded(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class ProvidersTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.key, self.config = root / "vapid.pem", root / "push-config.json"
        providers.setup_vapid(self.key, self.config)
        self.pub = json.loads(self.config.read_bytes())["applicationServerKey"]
        self.endpoint = "https://fcm.googleapis.com/fcm/send/dev:ice-1"
        self.subscription = {"endpoint": self.endpoint, "expirationTime": None, "keys": {
            "auth": providers.b64(bytes(range(16))),
            "p256dh": providers.b64(providers.public_key_bytes(ec.generate_private_key(ec.SECP256R1())))}
        }

    def test_android_signed_vapid_audience_expiry_and_empty_body(self):
        calls = []
        def capture(url, headers, body):
            calls.append((url, headers, body))
            return 201, None, b""
        provider = providers.Android(self.subscription, self.key.read_bytes(), ORIGIN)
        with patch.object(providers.time, "time", return_value=1000):
            receipt = provider.deliver(EVENT, capture)
        self.assertEqual(receipt, providers.Receipt("accepted", "provider_accepted"))
        url, headers, body = calls[0]
        self.assertEqual((url, body, headers["Content-Length"]), (self.endpoint, b"", "0"))
        self.assertNotIn("Content-Encoding", headers)
        self.assertEqual(len(headers["Topic"]), 32)
        auth, key = headers["Authorization"][8:].split(", k=")
        self.assertEqual(key, self.pub)
        header, body, signature = auth.split(".")
        self.assertEqual(json.loads(decoded(header)), {"alg": "ES256", "typ": "JWT"})
        claims = json.loads(decoded(body))
        self.assertEqual(claims, {"aud": "https://fcm.googleapis.com", "exp": 4600, "sub": ORIGIN + "/android/"})
        signature = decoded(signature)
        self.assertEqual(len(signature), 64)
        der = utils.encode_dss_signature(int.from_bytes(signature[:32], "big"), int.from_bytes(signature[32:], "big"))
        public = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), decoded(key))
        public.verify(der, (header + "." + body).encode("ascii"), ec.ECDSA(hashes.SHA256()))

    def test_invalid_endpoint_expired_subscription_no_traffic(self):
        for endpoint in ("http://fcm.googleapis.com/fcm/send/x", self.endpoint + "?foo", self.endpoint + "/foo",
                         self.endpoint.replace("googleapis.com", "googleapis.com.evil.example"),
                         self.endpoint.replace("fcm.googleapis.com", "a@fcm.googleapis.com")):
            with self.subTest(endpoint=endpoint), self.assertRaises(providers.ConfigurationError):
                providers.Android({**self.subscription, "endpoint": endpoint}, self.key.read_bytes(), ORIGIN)
        expired = providers.Android({**self.subscription, "expirationTime": 1}, self.key.read_bytes(), ORIGIN)
        self.assertEqual(expired.deliver(EVENT, lambda *_: self.fail()).reason, "subscription_expired")

    def test_vapid_setup_refuses_existing_private_or_public_files(self):
        key, config = self.key.read_bytes(), self.config.read_bytes()
        with self.assertRaises(FileExistsError):
            providers.setup_vapid(self.key, self.config)
        other = self.key.with_name("other.key")
        with self.assertRaises(FileExistsError):
            providers.setup_vapid(other, self.config)
        self.assertFalse(other.exists())
        self.assertEqual((self.key.read_bytes(), self.config.read_bytes()), (key, config))

    def test_telegram_private_ack_and_generic_button_only(self):
        provider = providers.Telegram(TOKEN, "42", ORIGIN)
        calls = []
        def success(url, headers, data):
            calls.append((url, json.loads(data)))
            return 200, None, b'{"ok":true,"result":{"message_id":2,"chat":{"type":"private","id":42}}}'
        self.assertEqual(provider.deliver(EVENT, success).state, "accepted")
        url, data = calls[0]
        self.assertEqual(url, f"https://api.telegram.org/bot{TOKEN}/sendMessage")
        self.assertNotIn(EVENT, json.dumps(data))
        self.assertNotIn("callback_data", json.dumps(data))
        self.assertEqual(data["reply_markup"]["inline_keyboard"][0][0]["url"], ORIGIN + "/approvals/")
        for chat in ({"type": "group", "id": 42}, {"type": "private", "id": 43}):
            def wrong(*args):
                return 200, None, json.dumps({"ok": True, "result": {"message_id": 1, "chat": chat}}).encode()
            self.assertEqual(provider.deliver(EVENT, wrong).state, "needs_review")
        for origin in ("http://example.org", ORIGIN + "/next", ORIGIN + ":443@attacker.example"):
            with self.assertRaises(providers.ConfigurationError):
                providers.Telegram(TOKEN, "42", origin)
        with self.assertRaises(providers.ConfigurationError):
            providers.Telegram(TOKEN, "-100", ORIGIN)

    def test_retry_and_permanent_classes_no_secret_material(self):
        provider = providers.Telegram(TOKEN, "42", ORIGIN)
        responses = [
            ((429, "7", b'{"parameters":{"retry_after":48}}'), providers.Receipt("retry", "http_429", 48)),
            ((502, None, b""), providers.Receipt("retry", "http_502")),
            ((302, None, b""), providers.Receipt("needs_review", "http_302")),
            ((401, None, TOKEN.encode()), providers.Receipt("needs_review", "http_401")),
            ((200, None, b"invalid json"), providers.Receipt("needs_review", "ack_invalid")),
        ]
        for response, expected in responses:
            self.assertEqual(provider.deliver(EVENT, lambda *_: response), expected)
        def timeout(*_):
            raise TimeoutError(TOKEN)
        self.assertEqual(provider.deliver(EVENT, timeout), providers.Receipt("retry", "transport_unknown"))


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.dbfile = Path(self.directory.name) / "receipts.sqlite"
        self.db = relay.open_db(self.dbfile)
        self.addCleanup(self.db.close)
        self.channels = ("android", "telegram")

    def new_event(self, value=EVENT):
        with relay.transaction(self.db):
            relay.record(self.db, self.channels, (value,))

    def test_crash_two_workers_and_late_receipt(self):
        self.new_event()
        self.new_event()
        worker = relay.open_db(self.dbfile)
        self.addCleanup(worker.close)
        self.assertEqual(relay.claim(self.db, "android", 0), (EVENT, 1))
        self.assertIsNone(relay.claim(worker, "android", 119))
        self.assertEqual(relay.claim(worker, "android", 120), (EVENT, 2))
        relay.finish(self.db, "android", EVENT, 1, providers.Receipt("accepted", "provider_accepted"), 121)
        self.assertEqual(worker.execute("SELECT state FROM jobs WHERE channel='android'").fetchone()[0], "sending")
        relay.finish(worker, "android", EVENT, 2, providers.Receipt("accepted", "provider_accepted"), 122)
        self.assertIsNone(relay.claim(self.db, "android", 500))
        self.assertEqual(relay.claim(self.db, "telegram", 0), (EVENT, 1))
        self.assertEqual(worker.execute("SELECT result FROM attempts WHERE channel='android' ORDER BY serial").fetchall(),
                         [("outcome_unknown",), ("provider_accepted",)])

    def test_provider_cooldown_and_bounded_attempts(self):
        self.new_event()
        self.new_event("2" * 64)
        event, n = relay.claim(self.db, "telegram", 0)
        relay.finish(self.db, "telegram", event, n, providers.Receipt("retry", "http_429", 120), 1)
        self.assertIsNone(relay.claim(self.db, "telegram", 120))
        self.assertEqual(relay.claim(self.db, "telegram", 121), ("2" * 64, 1))
        relay.finish(self.db, "telegram", "2" * 64, 1, providers.Receipt("accepted", "provider_accepted"), 121)
        for n in range(2, 6):
            self.assertEqual(relay.claim(self.db, "telegram", 400 * n), (event, n))
            relay.finish(self.db, "telegram", event, n, providers.Receipt("retry", "http_503"), 400 * n)
        self.assertIsNone(relay.claim(self.db, "telegram", 5000))
        self.assertIn({"channel": "telegram", "reason": "http_503", "count": 1}, relay.summary(self.db)["held"])
        self.assertEqual(relay.retry(self.db, "telegram"), 1)
        self.assertEqual(relay.claim(self.db, "telegram", 5100), (event, 6))

    def test_baseline_stable_and_single_outage_per_incident(self):
        args = self.db, self.channels, {"control_root": self.dbfile}
        with patch.dict(relay.READERS, {"control_root": lambda _: (EVENT,)}):
            relay.observe(*args, baseline=True)
            relay.observe(*args)
        self.assertIsNone(relay.claim(self.db, "android", 250))
        def broken(_):
            raise relay.sources.SourceError()
        for _ in range(2):
            with patch.dict(relay.READERS, {"control_root": broken}):
                relay.observe(*args)
        self.assertEqual(relay.summary(self.db)["source_errors"], ["control_root"])
        with patch.dict(relay.READERS, {"control_root": lambda _: (EVENT,)}):
            relay.observe(*args)
        with patch.dict(relay.READERS, {"control_root": broken}):
            relay.observe(*args)
        self.assertEqual(self.db.execute("SELECT count(*) FROM jobs WHERE channel='android' AND state='pending'").fetchone()[0], 2)

    def test_cli_queue_test_baseline_and_existing_status(self):
        root = Path(self.directory.name)
        (root / "token").write_text(TOKEN)
        (root / "alerts.jsonl").touch()
        config = root / "relay.json"
        config.write_text(json.dumps({"origin": ORIGIN, "telegram": {"token_file": "token", "chat_id": "42"},
                                      "sources": {"execution_alerts": "alerts.jsonl"}}))
        flags = ["--config", str(config), "--db", str(self.dbfile)]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(relay.main(["baseline", *flags]), 0)
            self.assertEqual(relay.main(["queue-test", *flags]), 0)
            with patch.object(providers.Telegram, "deliver", return_value=providers.Receipt("accepted", "provider_accepted")) as call:
                self.assertEqual(relay.main(["run", *flags, "--deliver", "--once"]), 0)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(relay.main(["status", "--db", str(self.dbfile)]), 0)
        self.assertEqual(relay.summary(self.db)["queues"], [{"channel": "telegram", "state": "accepted", "count": 1}])


if __name__ == "__main__":
    unittest.main()
