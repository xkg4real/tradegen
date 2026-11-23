"""Opt-in outbound notifications. The transports never accept approval responses."""

import base64
import hashlib
import http.client
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils


class ConfigurationError(ValueError):
    pass


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def public_key_bytes(key):
    return key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def write_new(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def setup_vapid(private_key, public_config):
    private_key, public_config = Path(private_key), Path(public_config)
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    write_new(private_key, pem)
    try:
        public_data = {"applicationServerKey": b64(public_key_bytes(key))}
        write_new(public_config, json.dumps(public_data).encode("ascii") + b"\n")
    except BaseException:
        private_key.unlink(missing_ok=True)
        raise


def read_limited(path, limit=16_384):
    with Path(path).open("rb") as file:
        data = file.read(limit + 1)
    if len(data) > limit:
        raise ConfigurationError("private_config_too_large")
    return data


def trusted_origin(value):
    # The operator provisions this exact, verified HTTPS approval origin.
    if not isinstance(value, str) or not re.fullmatch(
        r"https://[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+", value
    ):
        raise ConfigurationError("approval_origin_invalid")
    return value


@dataclass(frozen=True)
class Receipt:
    state: str
    reason: str
    retry_after: int = 0


def request(url, headers, body):
    # Fixed provider hosts only. http.client neither follows redirects nor uses an environment proxy.
    parts = urlsplit(url)
    conn = http.client.HTTPSConnection(parts.hostname, timeout=10)
    try:
        conn.request("POST", parts.path, body=body, headers=headers)
        response = conn.getresponse()
        return response.status, response.getheader("Retry-After"), response.read(16385)
    finally:
        conn.close()


def parse_retry_after(value):
    if value is None:
        return 0
    try:
        if re.fullmatch(r"[0-9]{1,10}", value):
            return int(value)
        when = parsedate_to_datetime(value)
        return max(0, int((when - datetime.now(timezone.utc)).total_seconds()) + 1)
    except (TypeError, ValueError, OverflowError):
        return 0


def post(url, headers, body, send):
    try:
        status, after, payload = send(url, headers, body)
    except (OSError, http.client.HTTPException):
        return Receipt("retry", "transport_unknown"), None
    if status == 429 or status == 408 or 500 <= status <= 599:
        wait = parse_retry_after(after)
        if status == 429 and url.startswith("https://api.telegram.org/"):
            try:
                value = json.loads(payload)["parameters"]["retry_after"]
                if type(value) is int and 0 <= value <= 2**32:
                    wait = max(wait, value)
            except (ValueError, KeyError, TypeError, RecursionError):
                pass
        return Receipt("retry", f"http_{status}", wait), None
    if not 200 <= status <= 299:
        return Receipt("needs_review", f"http_{status}"), None
    if len(payload) > 16384:
        return Receipt("needs_review", "response_too_large"), None
    return status, payload


class Telegram:
    def __init__(self, token, chat_id, origin):
        if not isinstance(token, str) or not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{25,}", token):
            raise ConfigurationError("telegram_token_invalid")
        if not isinstance(chat_id, str) or not re.fullmatch(r"[1-9][0-9]{0,15}", chat_id):
            raise ConfigurationError("private_chat_id_invalid")
        self.token, self.chat_id = token, chat_id
        self.review_url = trusted_origin(origin) + "/approvals/"

    def deliver(self, event_id, send=request):
        data = {
            "chat_id": self.chat_id,
            "text": "TRADEGEN에서 확인할 알림이 있습니다.",
            "protect_content": True,
            "reply_markup": {"inline_keyboard": [[{"text": "알림 확인", "url": self.review_url}]]},
        }
        result, body = post(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            {"Content-Type": "application/json"}, json.dumps(data).encode("utf-8"), send,
        )
        if isinstance(result, Receipt):
            return result
        try:
            reply = json.loads(body)
            msg = reply["result"]
            if (
                reply["ok"] is True and msg["chat"]["type"] == "private"
                and type(msg["chat"]["id"]) is int and str(msg["chat"]["id"]) == self.chat_id
                and type(msg["message_id"]) is int and msg["message_id"] > 0
            ):
                return Receipt("accepted", "provider_accepted")
        except (KeyError, TypeError, ValueError, RecursionError):
            pass
        return Receipt("needs_review", "ack_invalid")


def subscription_value(value, size):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ConfigurationError("subscription_key_invalid")
    raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if len(raw) != size or b64(raw) != value:
        raise ConfigurationError("subscription_key_invalid")
    return raw


class Android:
    def __init__(self, subscription, pem, origin):
        endpoint = subscription["endpoint"]
        if not isinstance(endpoint, str) or not re.fullmatch(
            r"https://fcm\.googleapis\.com/fcm/send/[A-Za-z0-9_:-]{1,4096}", endpoint
        ):
            raise ConfigurationError("push_endpoint_invalid")
        self.endpoint = endpoint
        self.expires = subscription.get("expirationTime")
        if self.expires is not None and (type(self.expires) is not int or not 0 < self.expires < 2**53):
            raise ConfigurationError("subscription_expiry_invalid")
        pub = subscription_value(subscription["keys"]["p256dh"], 65)
        if pub[0] != 4:
            raise ConfigurationError("subscription_key_invalid")
        ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pub)
        subscription_value(subscription["keys"]["auth"], 16)
        self.key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(self.key, ec.EllipticCurvePrivateKey) or not isinstance(self.key.curve, ec.SECP256R1):
            raise ConfigurationError("vapid_key_invalid")
        self.contact = trusted_origin(origin) + "/android/"

    def deliver(self, event_id, send=request):
        now = int(time.time())
        if self.expires is not None and now * 1000 >= self.expires:
            return Receipt("needs_review", "subscription_expired")
        claims = {"aud": "https://fcm.googleapis.com", "exp": now + 3600, "sub": self.contact}
        encoded = b64(b'{"typ":"JWT","alg":"ES256"}') + "." + b64(json.dumps(claims).encode("ascii"))
        r, s = utils.decode_dss_signature(self.key.sign(encoded.encode("ascii"), ec.ECDSA(hashes.SHA256())))
        token = encoded + "." + b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))
        headers = {
            "Authorization": f"vapid t={token}, k={b64(public_key_bytes(self.key))}",
            "TTL": "3600", "Urgency": "high", "Content-Length": "0",
            "Topic": b64(hashlib.sha256(event_id.encode("ascii")).digest())[:32],
        }
        result, _ = post(self.endpoint, headers, b"", send)
        if isinstance(result, Receipt):
            return result
        if result in (201, 202):
            return Receipt("accepted", "provider_accepted")
        return Receipt("needs_review", "ack_invalid")
