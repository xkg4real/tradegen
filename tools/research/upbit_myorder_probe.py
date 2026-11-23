"""OQ18 opt-in private myOrder observation. Never places or cancels an order.

Standalone research tool; no app imports, environment/key-file reads, raw account
logging, reconnect loop, or production authority. Import performs no I/O.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import getpass
import hashlib
import hmac
from importlib.metadata import PackageNotFoundError, version
import json
import logging
import os
from pathlib import Path
import re
import ssl
import stat
import sys
import time
import uuid
import warnings


ENDPOINT = "wss://api.upbit.com/websocket/v1/private"
SCHEMA = "tradegen-myorder-observation-v1"
MAX_MESSAGE = 64 * 1024
PINNED_WEBSOCKETS = "16.0"
STATES = frozenset(("wait", "watch", "trade", "done", "cancel", "prevented"))
SERVER_ERRORS = frozenset(("INVALID_AUTH", "WRONG_FORMAT", "NO_TICKET", "NO_TYPE", "NO_CODES", "INVALID_PARAM"))
SENSITIVE_FIELDS = ("uuid", "trade_uuid", "price", "volume", "trade_fee", "is_maker")


class ProbeError(Exception):
    """Fixed diagnostics only; raw exceptions and provider messages stay private."""


def encoded(document):
    return json.dumps(document, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Config:
    duration_seconds: int = 120
    max_events: int = 100

    def validate(self):
        if type(self.duration_seconds) is not int or not 1 <= self.duration_seconds <= 3600:
            raise ProbeError("DURATION_INVALID")
        if type(self.max_events) is not int or not 1 <= self.max_events <= 1000:
            raise ProbeError("EVENT_LIMIT_INVALID")
        return self


@dataclass(frozen=True, repr=False)
class Credentials:
    access_key: str
    secret_key: str

    def validate(self):
        for value in (self.access_key, self.secret_key):
            if type(value) is not str or not 8 <= len(value) <= 512 or not value.isascii() or any(ord(x) <= 32 or ord(x) >= 127 for x in value):
                raise ProbeError("CREDENTIAL_FORMAT_INVALID")
        return self

    def __repr__(self):
        return "Credentials(<redacted>)"


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def authorization(credentials):
    """Same no-query HS512 scheme as execution.transport, without importing it."""
    credentials.validate()
    parts = ({"alg": "HS512", "typ": "JWT"}, {"access_key": credentials.access_key, "nonce": str(uuid.uuid4())})
    content = ".".join(_b64(encoded(part)) for part in parts)
    signature = hmac.new(credentials.secret_key.encode("ascii"), content.encode("ascii"), hashlib.sha512).digest()
    return "Bearer " + content + "." + _b64(signature)


def subscription():
    # No codes => observe this key's own orders across its available markets.
    # The only application message sent by this program is this subscription.
    return encoded([{"ticket": str(uuid.uuid4())}, {"type": "myOrder"}, {"format": "DEFAULT"}]).decode("ascii")


def require_dependencies():
    try:
        installed = version("websockets")
    except PackageNotFoundError:
        raise ProbeError("DEPENDENCY_MISSING") from None
    if installed != PINNED_WEBSOCKETS:
        raise ProbeError("DEPENDENCY_VERSION_MISMATCH")
    return installed


def private_connector():
    require_dependencies()
    from websockets.asyncio.client import connect

    class NoRedirectConnect(connect):
        def process_redirect(self, exc):
            return exc

    return NoRedirectConnect


def read_credentials():
    # Never fall back to echoed stdin, a command-line argument, or environment.
    if not sys.stdin.isatty():
        raise ProbeError("PRIVATE_TERMINAL_REQUIRED")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            access = getpass.getpass("Separate observation Access Key (hidden): ")
            secret = getpass.getpass("Separate observation Secret Key (hidden): ")
        except (getpass.GetPassWarning, EOFError):
            raise ProbeError("PRIVATE_TERMINAL_REQUIRED") from None
    return Credentials(access, secret).validate()


def _ordinary_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ProbeError("OUTPUT_PATH_REFUSED")


class ObservationLog:
    """Exclusive new metadata file; no raw payloads, identifiers, keys or hashes."""
    def __init__(self, path):
        self.path = Path(path).absolute()
        if any(part.casefold() in (".tradegen", ".nextgen") for part in self.path.parts):
            raise ProbeError("OUTPUT_PATH_REFUSED")
        for parent in reversed(self.path.parents):
            if parent.exists() or parent.is_symlink():
                _ordinary_directory(parent)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        self.stream = os.fdopen(fd, "wb")

    def emit(self, row):
        raw = encoded(row) + b"\n"
        if len(raw) > 8192:
            raise ProbeError("METADATA_RESOURCE_LIMIT")
        self.stream.write(raw)
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.stream.close()


def _parse_message(message):
    if type(message) not in (bytes, str):
        raise ProbeError("MESSAGE_FORMAT_INVALID")
    raw = message if type(message) is bytes else message.encode("utf-8")
    if len(raw) > MAX_MESSAGE:
        raise ProbeError("MESSAGE_TOO_LARGE")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ProbeError("MESSAGE_FORMAT_INVALID")
            result[key] = value
        return result

    try:
        document = json.loads(raw, object_pairs_hook=pairs,
                              parse_constant=lambda _: (_ for _ in ()).throw(ProbeError("MESSAGE_FORMAT_INVALID")))
    except (ValueError, UnicodeError, RecursionError):
        raise ProbeError("MESSAGE_FORMAT_INVALID") from None
    if type(document) is not dict:
        raise ProbeError("MESSAGE_FORMAT_INVALID")
    if "error" in document:
        error = document["error"]
        name = error.get("name") if type(error) is dict else None
        if type(name) is not str or name not in SERVER_ERRORS:
            name = "OTHER"
        return {"kind": "server_error", "name": name, "message_bytes": len(raw)}
    if document.get("type") != "myOrder":
        raise ProbeError("UNEXPECTED_STREAM_MESSAGE")
    if document.get("state") not in STATES or type(document.get("uuid")) is not str or not 1 <= len(document["uuid"]) <= 128:
        raise ProbeError("MYORDER_SCHEMA_UNRECOGNIZED")
    # Values and arbitrary field names are never forwarded. Presence is a schema
    # observation, not proof of a fill, fee, participant side, or data completeness.
    return {"kind": "myorder_metadata", "message_bytes": len(raw), "state": document["state"],
            "expected_fields_present": {key: key in document for key in SENSITIVE_FIELDS}}


def _failure(exc, phase):
    """Classify without str/repr(exc), raw response bodies or close reasons."""
    from websockets.exceptions import ConnectionClosed, InvalidStatus, WebSocketException
    if isinstance(exc, InvalidStatus):
        status = exc.response.status_code
        status = status if type(status) is int and 100 <= status <= 599 else None
        details = {"http_status": status}
        if status in (418, 429):
            try:
                retry = exc.response.headers.get("Retry-After")
            except Exception:
                retry = None
            details["retry_after_seconds"] = int(retry) if type(retry) is str and re.fullmatch(r"[0-9]{1,5}", retry) else None
            return "RATE_LIMITED_STOP", details
        if status in (401, 403):
            return "AUTH_OR_PERMISSION_REJECTED", details
        if status in (300, 301, 302, 303, 307, 308):
            return "REDIRECT_REFUSED", details
        return "HANDSHAKE_REJECTED", details
    if isinstance(exc, ConnectionClosed):
        frame = exc.rcvd
        code = None if frame is None else frame.code
        return "CONNECTION_CLOSED", {"close_code": code if type(code) is int and 1000 <= code <= 4999 else None}
    if isinstance(exc, TimeoutError):
        return ("CONNECT_TIMEOUT" if phase == "connect" else "SUBSCRIPTION_SEND_TIMEOUT"), {}
    if isinstance(exc, (OSError, WebSocketException)):
        return "TRANSPORT_FAILED", {}
    return "PROBE_INTERNAL_REFUSED", {}


async def observe(config, credentials, emit, *, connector=None, monotonic=time.monotonic, now=utc_now):
    config.validate()
    credentials.validate()
    if connector is None:
        connector = private_connector()
    start = monotonic()
    deadline = start + config.duration_seconds
    result = {"schema": SCHEMA, "connection_status": "NOT_CONNECTED", "subscription_status": "NOT_SENT",
              "subscription_request_locally_valid": True, "server_subscription_acknowledged": False,
              "myorder_event_count": 0, "provider_permission_state": "UNKNOWN",
              "entitlement_confirmed": False, "source_complete": False, "fill_authority": False,
              "execution_ready": False, "status": "NOT_STARTED"}
    emit({"kind": "session_start", "schema": SCHEMA, "at": now(), "duration_seconds": config.duration_seconds,
          "max_events": config.max_events, "public_probe_changed": False, "private_observation_only": True})
    connection = None
    phase = "connect"
    # A private unregistered disabled logger prevents inherited DEBUG handlers
    # from printing the Authorization handshake or received account messages.
    logger = logging.Logger("tradegen-myorder-private", level=logging.CRITICAL + 1)
    logger.disabled = True
    logger.propagate = False
    try:
        connection = await asyncio.wait_for(connector(ENDPOINT, additional_headers={"Authorization": authorization(credentials)},
                                                       ssl=ssl.create_default_context(), proxy=None, origin=None, compression=None,
                                                       open_timeout=min(10, config.duration_seconds), close_timeout=2,
                                                       ping_interval=20, ping_timeout=10, max_size=MAX_MESSAGE, max_queue=8,
                                                       logger=logger), timeout=min(10, config.duration_seconds))
        result["connection_status"] = "CONNECTED"
        emit({"kind": "connected", "at": now(), "subscription_acknowledged": False})
        phase = "send"
        remaining = deadline - monotonic()
        if remaining <= 0:
            result["status"] = "DURATION_EXPIRED_BEFORE_SUBSCRIPTION"
        else:
            await asyncio.wait_for(connection.send(subscription()), timeout=min(5, remaining))
            result["subscription_status"] = "SENT_UNCONFIRMED"
            emit({"kind": "subscription_sent", "at": now(), "type": "myOrder", "server_acknowledged": False})
            phase = "receive"
            while result["myorder_event_count"] < config.max_events:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    break
                try:
                    message = await asyncio.wait_for(connection.recv(), timeout=remaining)
                except TimeoutError:
                    break
                metadata = _parse_message(message)
                emit({**metadata, "at": now()})
                if metadata["kind"] == "server_error":
                    result["subscription_status"] = "REJECTED"
                    result["status"] = "AUTH_REJECTED" if metadata["name"] == "INVALID_AUTH" else "SUBSCRIPTION_REJECTED"
                    break
                result["myorder_event_count"] += 1
                result["subscription_status"] = "MYORDER_EVENT_OBSERVED"
            if result["status"] == "NOT_STARTED":
                result["status"] = "MYORDER_EVENT_OBSERVED" if result["myorder_event_count"] else "SILENT_ENTITLEMENT_UNPROVEN"
                result["stop_reason"] = "EVENT_LIMIT" if result["myorder_event_count"] >= config.max_events else "OBSERVATION_WINDOW_ENDED"
    except ProbeError as exc:
        result["status"] = str(exc)
    except (KeyboardInterrupt, asyncio.CancelledError):
        result["status"] = "INTERRUPTED"
    except Exception as exc:
        result["status"], details = _failure(exc, phase)
        result.update(details)
    finally:
        if connection is not None:
            try:
                await asyncio.wait_for(connection.close(), timeout=2)
                result["close_status"] = "CLOSED"
            except (Exception, asyncio.CancelledError):
                # Abort a stuck transport instead of leaving an authenticated
                # background connection alive after the bounded observation.
                transport = getattr(connection, "transport", None)
                if transport is not None:
                    transport.abort()
                result["close_status"] = "CLOSE_ABORTED"
        result["elapsed_seconds"] = max(0.0, monotonic() - start)
        result["automatic_reconnect"] = False
        emit({"kind": "session_end", "at": now(), **result})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="OQ18 private myOrder observation; no orders, raw account export or authority.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--duration-seconds", type=int, default=120)
    parser.add_argument("--max-events", type=int, default=100)
    parser.add_argument("--allow-private-network", action="store_true")
    parser.add_argument("--check-dependencies", action="store_true")
    args = parser.parse_args(argv)
    if not args.check_dependencies and (not args.allow_private_network or args.output is None):
        parser.error("--allow-private-network and a new --output file are required; no credentials or network used")
    try:
        installed = require_dependencies()
        if args.check_dependencies:
            print(json.dumps({"status": "DEPENDENCIES_READY", "websockets": installed, "private_network_used": False}))
            return 0
        config = Config(args.duration_seconds, args.max_events).validate()
        with ObservationLog(args.output) as log:
            # Refuse an unsafe/existing output before asking for credentials.
            credentials = read_credentials()
            result = asyncio.run(observe(config, credentials, log.emit))
        print(json.dumps(result, sort_keys=True))
        return 0 if result["status"] in ("MYORDER_EVENT_OBSERVED", "SILENT_ENTITLEMENT_UNPROVEN") else 2
    except ProbeError as exc:
        print(json.dumps({"status": str(exc), "execution_ready": False}))
        return 2
    except KeyboardInterrupt:
        print(json.dumps({"status": "INTERRUPTED", "execution_ready": False}))
        return 2
    except Exception:
        print(json.dumps({"status": "LOCAL_OR_RUNTIME_REFUSED", "execution_ready": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
