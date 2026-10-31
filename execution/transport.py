"""The only network path of execution/ (E1 spec 5 "The choke point"; contract section 6; E3, E10, E12, E13, E36).

`request` refuses, before any key is read, everything outside the venue's frozen allowlist, which it reads at call
time from the venue module (E10): an unknown venue, a (method, path) pair not listed, any method but GET except the
one KIS token POST, a KIS inquiry without its pinned TR id ending in R, a TR id anywhere else, a parameter that is
not plain, and a signed OKX request without a known clock offset within 25 s. Only then are credentials read and one
request sent through the seam `_send`, which ignores the environment's proxy, CA-bundle and .netrc settings and
never follows a redirect (E1R2-11). The hosts are the real ones; no mock host is listed. Nothing here logs, prints or
returns a key, and every error text holds names, paths, TR ids and venue codes only (E37).

Each attempt builds its headers afresh (the KIS bearer token, an Upbit HS512 JWT with a new nonce, an OKX
HMAC-SHA256 signature over a new timestamp), sends once with a 10 s timeout and pauses 0.2 s (at most 5 requests a
second); a GET goes once more, 2 s later, after a connection error, HTTP 429 or 5xx, a POST never. `_check_answer`
turns each answer into its parsed body, AuthError or InquiryError (E15). The KIS token lives in
state_root()/kis_token.json, the file and format the KIS quote client uses: reused until 120 s before it expires,
issued at most once per 70 s per process with its targets checked before the token POST (the ledger's "KIS token
burnt on refusal"), and not issued for 6 hours after KIS hands back a token it had called bad."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import re
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from types import MappingProxyType
from urllib.parse import quote

import requests

from core import isolation
from core.isolation import checked_target
from execution import keys
from execution.keys import KeyMissing  # noqa: F401  (re-exported: the venue modules import it from here, E36)

HOSTS = MappingProxyType({"kis": "https://openapi.koreainvestment.com:9443",
                          "upbit": "https://api.upbit.com",
                          "okx": "https://www.okx.com"})
CREDENTIALS = MappingProxyType({"kis": ("KIS_APP_KEY", "KIS_APP_SECRET"),
                                "upbit": ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
                                "okx": ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")})
KIS_TOKEN_PATH = "/oauth2/tokenP"
TIMEOUT_S = 10.0
RETRY_AFTER_S = 2.0
PACE_S = 0.2                          # sleep after every attempt: at most 5 requests a second
OKX_SKEW_LIMIT_S = 25.0
TOKEN_REUSE_MARGIN_S = 120.0
TOKEN_MIN_GAP_S = 70.0
TOKEN_REISSUE_BLOCK_S = 6 * 3600.0    # KIS returned a token it had called bad: issue nothing for 6 hours
KIS_TOKEN_CODES = frozenset({"EGW00121", "EGW00122", "EGW00123"})
AUTH_CODES = MappingProxyType({
    "kis": frozenset({"EGW00103", "EGW00105", "EGW00205", "EGW00206", "EGW00304"}),
    "upbit": frozenset({"invalid_query_payload", "jwt_verification", "expired_access_key", "nonce_used",
                        "no_authorization_ip", "no_authorization_token", "out_of_scope"}),
    "okx": frozenset({"50030", "50035", "50100", "50101", "50103", "50104", "50105", "50106", "50107", "50110",
                      "50111", "50112", "50113", "50114", "50119", "50120", "50121", "50123"})})
_KEY = re.compile(r"[A-Za-z0-9_\[\]]+")


class InquiryRefused(Exception):
    """A request E1 may not make, refused before any key is read (spec 5 steps 1-3). `reason` names the venue,
    method, path, TR id or parameter key, never a value."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class InquiryError(Exception):
    """The venue or the network failed after the checks; the text holds names, paths and venue codes only."""


class AuthError(InquiryError):
    """An authentication or permission answer (KEY_HEALTH)."""


@dataclass(frozen=True, kw_only=True)
class Answer:
    """One checked answer (E3, E39)."""
    body: object = field(repr=False)  # the parsed JSON (a token, balances or addresses: never in a repr)
    server_utc: datetime | None       # from the Date header, aware UTC; None when absent or unreadable
    received_utc: datetime            # _clock() right after _send returned (E39)
    sha256: str                       # hex over the raw body bytes


def request(venue: str, method: str, path: str, params: Sequence[tuple[str, str]] | None = None, *,
            tr_id: str | None = None) -> Answer:
    """One allowlisted request (spec 5). Steps 1-6 of contract section 6 run first, in order, and each refusal is
    InquiryRefused before any key is read. Then each attempt builds its credentials and headers afresh (`_headers`)
    and goes out through `_send` with the query in the URL; `received_utc` is the clock read right after `_send`
    returns (E39), and every attempt is followed by `_sleep(PACE_S)`. A GET goes once more, after
    `_sleep(RETRY_AFTER_S)`, on requests' ConnectionError (ConnectTimeout included; a ReadTimeout is not one), HTTP
    429 or 5xx; a POST never. A ValueError or OSError out of `_send` becomes InquiryError naming the venue, the path
    and the exception type only (E15, E37); anything else propagates. `_check_answer` judges the last answer; a KIS
    token the venue calls invalid or expired goes into `_bad_tokens`; a good OKX public/time answer sets
    `_okx_offset_s` (its `ts` minus `received_utc`)."""
    global _okx_offset_s
    if venue not in HOSTS:
        raise InquiryRefused(f"unknown venue {venue!r}")
    endpoints, tr_ids, public = _rules(venue)
    if (method, path) not in endpoints:
        raise InquiryRefused(f"{venue}: {method} {path} is not on the E1 allowlist")
    if method != "GET":
        if (venue, method, path) != ("kis", "POST", KIS_TOKEN_PATH):
            raise InquiryRefused(f"{venue}: {method} is not GET")
        if params is not None:
            raise InquiryRefused("kis: the token POST takes no parameters")
    if venue == "kis" and method == "GET":
        if tr_id not in {t for p, t in tr_ids if p == path} or not tr_id.endswith("R"):
            raise InquiryRefused(f"kis: {path} needs its pinned TR id ending in R, got {tr_id!r}")
    elif tr_id is not None:
        raise InquiryRefused(f"{venue}: a TR id belongs only to a KIS inquiry")
    query = _query(venue, path, params)
    if venue == "okx" and path not in public and not (
            _okx_offset_s is not None and abs(_okx_offset_s) <= OKX_SKEW_LIMIT_S):
        raise InquiryRefused("okx: the PC clock offset from OKX time is unknown or above 25 s; OKX requests not sent")
    url = HOSTS[venue] + path + ("?" + query if query else "")
    for attempt in (1, 2):
        headers, json_body, token = _headers(venue, method, path, query, tr_id, path in public)
        try:
            status, answer_headers, content = _send(method, url, headers=headers, params=None, json_body=json_body,
                                                    timeout=TIMEOUT_S)
        except (ValueError, OSError) as exc:
            _sleep(PACE_S)
            if attempt == 1 and method == "GET" and isinstance(exc, requests.exceptions.ConnectionError):
                _sleep(RETRY_AFTER_S)
                continue
            raise InquiryError(f"{venue} {path}: {type(exc).__name__}") from None
        received_utc = _clock()
        _sleep(PACE_S)
        if attempt == 1 and method == "GET" and (status == 429 or status >= 500):
            _sleep(RETRY_AFTER_S)
            continue
        break
    try:
        body = _check_answer(venue, path, status, content)
    except _TokenRejected:
        _bad_tokens.add(token)
        raise
    if (venue, path) == ("okx", "/api/v5/public/time"):
        _okx_offset_s = None                          # a malformed answer leaves no stale offset behind
        _okx_offset_s = int(body["data"][0]["ts"]) / 1000 - received_utc.timestamp()
    return Answer(body=body, server_utc=_date(answer_headers), received_utc=received_utc,
                  sha256=hashlib.sha256(content).hexdigest())


def require_keys(venue: str) -> None:
    """KeyMissing (names only) unless every credential of `venue` is set; the values are read and dropped, never
    returned (E32)."""
    keys.read(CREDENTIALS[venue])


def _send(method, url, *, headers, params, json_body, timeout):
    with requests.Session() as session:
        session.trust_env = False                  # no proxy, CA bundle or .netrc from the environment
        resp = session.request(method, url, headers=headers, params=params, json=json_body, timeout=timeout,
                               allow_redirects=False)
        return resp.status_code, resp.headers, resp.content


_sleep = time.sleep                   # seam: pacing and retry wait through it; it reads no clock


def _clock() -> datetime:
    """The send-time clock (E11): poll.main binds one; until then nothing in E1 reads the time."""
    raise RuntimeError("transport: no clock; poll.main sets one")


_next_issue_at: float | None = None   # epoch seconds before which this process issues no KIS token
_okx_offset_s: float | None = None    # OKX server time minus the PC clock at the last public/time answer
_bad_tokens: set[str] = set()         # KIS tokens the venue called invalid or expired in this process


def _rules(venue: str) -> tuple[frozenset, frozenset, frozenset]:
    """(ENDPOINTS, TR_IDS or frozenset(), PUBLIC) of `venue`, read from its module at call time (E10). The venue
    modules import this one, so the import waits until a request is made."""
    from execution import kis_inquiry, okx_inquiry, upbit_inquiry
    module = {"kis": kis_inquiry, "upbit": upbit_inquiry, "okx": okx_inquiry}[venue]
    return module.ENDPOINTS, (kis_inquiry.TR_IDS if module is kis_inquiry else frozenset()), module.PUBLIC


def _query(venue: str, path: str, params) -> str:
    """The query string, built once and sent as built (E12): ordered (key, value) tuples joined as
    key=quote(value, safe=","). A key must fully match _KEY (`states[]` included) and a value must be a str; for a
    signed Upbit or OKX request a value that quoting would change is refused, so the hashed or signed string is
    byte for byte the one sent. A KIS value is quoted (PDNO=% goes out as %25). Anything but a sequence of 2-tuples
    with a str key is refused with a fixed text, so a stray value never reaches the reason."""
    if params is None:
        return ""
    signed = venue != "kis" and path not in _rules(venue)[2]
    parts = []
    for pair in params:
        if not (isinstance(pair, tuple) and len(pair) == 2 and isinstance(pair[0], str)):
            raise InquiryRefused(f"{venue}: parameters must be (key, value) pairs")
        key, value = pair
        if not (_KEY.fullmatch(key) and isinstance(value, str)) or (
                signed and quote(value, safe=",") != value):
            raise InquiryRefused(f"{venue}: parameter {key!r} is not plain")
        parts.append(f"{key}={quote(value, safe=',')}")
    return "&".join(parts)


def _headers(venue: str, method: str, path: str, query: str, tr_id: str | None,
             public: bool) -> tuple[dict, dict | None, str | None]:
    """(headers, json_body, token) for one attempt, built afresh each time; each keys.read names exactly
    CREDENTIALS[venue], and a public path reads no key. Never the demo-trading header (E3)."""
    if public:
        return {"Accept": "application/json"}, None, None
    if venue == "kis" and method == "POST":
        app_key, app_secret = keys.read(CREDENTIALS["kis"])
        return ({"content-type": "application/json; charset=utf-8"},
                {"grant_type": "client_credentials", "appkey": app_key, "appsecret": app_secret}, None)
    if venue == "kis":
        token = _kis_token()
        app_key, app_secret = keys.read(CREDENTIALS["kis"])
        return ({"content-type": "application/json; charset=utf-8", "authorization": f"Bearer {token}",
                 "appkey": app_key, "appsecret": app_secret, "tr_id": tr_id, "custtype": "P"}, None, token)
    if venue == "upbit":
        access_key, secret_key = keys.read(CREDENTIALS["upbit"])
        return ({"Authorization": f"Bearer {_upbit_jwt(access_key, secret_key, query)}",
                 "Accept": "application/json"}, None, None)
    api_key, secret, passphrase = keys.read(CREDENTIALS["okx"])
    timestamp = _okx_timestamp(_clock())
    return ({"OK-ACCESS-KEY": api_key,
             "OK-ACCESS-SIGN": _okx_sign(secret, timestamp, path + ("?" + query if query else "")),
             "OK-ACCESS-TIMESTAMP": timestamp, "OK-ACCESS-PASSPHRASE": passphrase,
             "Content-Type": "application/json"}, None, None)


def _date(headers) -> datetime | None:
    """The answer's Date header (its name in any case) as an aware UTC datetime; None when absent or unreadable."""
    value = next((v for k, v in headers.items() if k.lower() == "date"), None)
    try:
        moment = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:                         # "-0000": UTC with no local zone given (RFC 5322)
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


class _TokenRejected(InquiryError):
    """A KIS inquiry answered with one of KIS_TOKEN_CODES: request marks the token it sent bad."""


_CODE = re.compile(r"[A-Za-z0-9_]{1,40}")           # a venue code worth naming in an error text; nothing else is


def _check_answer(venue: str, path: str, status: int, body_bytes: bytes) -> object:
    """E15: the parsed body of an HTTP 200 answer that carries the venue's success marker (KIS rt_cd "0", or a
    non-empty access_token from the token POST; OKX code "0"; Upbit no error key). A KIS inquiry answered with a
    token code (on any status) raises _TokenRejected; HTTP 401 or 403, or a code in AUTH_CODES[venue], AuthError;
    anything else, a 3xx included, InquiryError. Each text names the venue, the path, the HTTP status and the
    venue's code only: never a message, a header or the body (E37)."""
    try:
        body, parsed = json.loads(body_bytes), True
    except ValueError:                                # not JSON, or not UTF-8: the bytes are never quoted
        body, parsed = None, False
    code = _code(venue, body)
    text = f"{venue} {path}: HTTP {status}" + (f" {code}" if code else "")
    if venue == "kis" and path != KIS_TOKEN_PATH and code in KIS_TOKEN_CODES:
        raise _TokenRejected(text)
    if status in (401, 403) or code in AUTH_CODES[venue]:
        raise AuthError(text)
    if status == 200 and parsed and _succeeded(venue, path, body):
        return body
    raise InquiryError(text if parsed else f"{text}: not JSON")


def _code(venue: str, body: object) -> str:
    """The venue's own code in a parsed body (KIS msg_cd, or the token answer's error_code; OKX code; Upbit
    error.name); "" when there is none or it is not a short plain word."""
    if not isinstance(body, dict):
        return ""
    if venue == "kis":
        raw = body.get("msg_cd") or body.get("error_code")
    elif venue == "okx":
        raw = body.get("code")
    else:
        raw = body["error"].get("name") if isinstance(body.get("error"), dict) else None
    return str(raw) if raw is not None and _CODE.fullmatch(str(raw)) else ""


def _succeeded(venue: str, path: str, body: object) -> bool:
    """The venue's success marker in a parsed HTTP 200 body (E15)."""
    if venue == "upbit":
        return not (isinstance(body, dict) and "error" in body)
    if not isinstance(body, dict):
        return False
    if venue == "okx":
        return body.get("code") == "0"
    if path == KIS_TOKEN_PATH:
        return isinstance(body.get("access_token"), str) and body["access_token"] != ""
    return body.get("rt_cd") == "0"


def _b64url(raw: bytes) -> str:
    """base64url without padding, as a JWT part."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _upbit_jwt(access_key: str, secret_key: str, query: str) -> str:
    """The Upbit JWT (research upbit.md 2): HS512 over the base64url header and payload with the secret used raw;
    the payload holds access_key and a fresh uuid4 nonce, plus query_hash (the SHA512 hex of `query`, the exact
    string sent in the URL) and query_hash_alg when there is a query. No exp claim."""
    payload = {"access_key": access_key, "nonce": str(uuid.uuid4())}
    if query:
        payload |= {"query_hash": hashlib.sha512(query.encode("utf-8")).hexdigest(), "query_hash_alg": "SHA512"}
    signing_input = ".".join(_b64url(json.dumps(part, separators=(",", ":")).encode("utf-8"))
                             for part in ({"alg": "HS512", "typ": "JWT"}, payload))
    signature = hmac.new(secret_key.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha512).digest()
    return f"{signing_input}.{_b64url(signature)}"


def _okx_timestamp(moment: datetime) -> str:
    """OK-ACCESS-TIMESTAMP: ISO 8601 UTC with milliseconds (truncated) and Z, for example 2026-10-24T00:00:00.000Z."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _okx_sign(secret: str, timestamp: str, request_path: str) -> str:
    """OK-ACCESS-SIGN (research okx.md 2): Base64 of HMAC-SHA256(secret, timestamp + "GET" + the request path with
    its query + an empty body)."""
    message = (timestamp + "GET" + request_path).encode("utf-8")
    return base64.b64encode(hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()).decode("ascii")


def _kis_token() -> str:
    """The KIS bearer token for one GET attempt (spec 5 "Token"): the cached one while it is not bad and now <
    expires_at - 120 s; else one issue through the token POST, at most once per 70 s per process. The folder, the
    cache and the temp file pass checked_target BEFORE the POST and before the 70 s starts, so a refused target
    sends nothing and burns no issuance (a refusal propagates: a crash, E33). KIS answers the same token for 6
    hours, so a token it had called bad that the POST hands back is AuthError and blocks issuing for 6 hours."""
    global _next_issue_at
    path = isolation.state_root() / "kis_token.json"
    now = _clock().timestamp()
    cached = _read_token(path, now)
    if cached is not None and cached not in _bad_tokens:
        return cached
    if _next_issue_at is not None and now < _next_issue_at:
        raise InquiryError("kis: no token may be issued yet; KIS skipped this poll")
    checked_target(path.parent, "KIS token folder")
    checked_target(path, "KIS token cache")
    tmp = checked_target(path.with_name(f".kis_token.{os.urandom(6).hex()}.tmp"), "KIS token temp")
    _next_issue_at = now + TOKEN_MIN_GAP_S
    answer = request("kis", "POST", KIS_TOKEN_PATH)
    token = answer.body["access_token"]
    if token in _bad_tokens:
        _next_issue_at = now + TOKEN_REISSUE_BLOCK_S
        raise AuthError("kis: KIS issued a token it had called invalid; no token for 6 hours")
    lifetime = answer.body.get("expires_in", 86400)
    try:
        if isinstance(lifetime, bool):
            raise ValueError
        lifetime = float(lifetime)
        expires_at = now + lifetime
        if not (math.isfinite(lifetime) and lifetime > 0 and math.isfinite(expires_at) and expires_at > now):
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise InquiryError("kis: token expiry is invalid") from None
    _write_token(path, tmp, token, expires_at)
    return token


def _read_token(path: Path, now_epoch: float) -> str | None:
    """The cached token when `path` holds a non-empty access_token and now_epoch < expires_at - 120 s (the quote
    client's reuse rule); None for a missing, unreadable or malformed file or a token that is about to expire."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        token, raw_expiry = data["access_token"], data["expires_at"]
        if isinstance(raw_expiry, bool):
            return None
        expires_at = float(raw_expiry)
    except (OSError, ValueError, TypeError, LookupError, OverflowError):
        return None
    return token if (isinstance(token, str) and token and math.isfinite(expires_at) and expires_at > 0
                     and now_epoch < expires_at - TOKEN_REUSE_MARGIN_S) else None


def _write_token(path: Path, tmp: Path, token: str, expires_at: float) -> None:
    """{"access_token", "expires_at"} (epoch seconds; the quote client's format) written atomically: to `tmp`, the
    temp name checked before the POST, opened exclusively and fsynced, then os.replace onto `path`, each target
    checked again just before it is used. An OSError propagates (a crash, E33): the next poll finds the old cache,
    or none, and may issue once the 70 s have passed. A write that fails after the open leaves its uniquely named
    temp file behind (nothing here deletes a file); it is never read or reused, and the next issue (KIS hands back
    the same token within 6 hours) writes a fresh one."""
    checked_target(path.parent, "KIS token folder").mkdir(parents=True, exist_ok=True)
    with open(checked_target(tmp, "KIS token temp"), "x", encoding="utf-8") as fh:
        fh.write(json.dumps({"access_token": token, "expires_at": expires_at}))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(checked_target(tmp, "KIS token temp"), checked_target(path, "KIS token cache"))
