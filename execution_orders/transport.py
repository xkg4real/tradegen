"""One capability-bound HTTP attempt for a strictly prepared cash order.

Pure codecs validate every route and field before a one-use capability is
consumed. Only then may the explicitly supplied provider resolve trading
credentials for the bound opaque account scope. There is no environment reader,
token refresh, default account, retry, redirect, or alternate send path here.
An acknowledgment is not a fill; ambiguous delivery or parsing stays unknown.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from types import MappingProxyType
from urllib.parse import unquote, urlencode

import requests

from execution_control.capability import consume_capability
from execution_network.route import route_options
from execution_orders.model import AdapterResult, PreparedRequest, request_digest, validate_request


HOSTS = MappingProxyType({
    "upbit": "https://api.upbit.com",
    "kis": "https://openapi.koreainvestment.com:9443",
    "okx": "https://www.okx.com",
})
TIMEOUT_S = 10.0
MAX_RESPONSE_BYTES = 1_048_576


@dataclass(frozen=True, kw_only=True, repr=False)
class Credentials:
    """Explicit provider result. Secret values never appear in repr or str.

    ``access_key``/``secret_key`` mean the venue's API/app key and secret.
    KIS additionally needs a previously issued token and its account components;
    OKX needs its API passphrase. The opaque scope is a configuration binding,
    not an assertion independently verified against the broker's live account.
    """

    venue: str
    account_scope: str
    access_key: str = ""
    secret_key: str = ""
    passphrase: str = ""
    bearer_token: str = ""
    account_number: str = ""
    account_product: str = ""

    def __repr__(self) -> str:
        return "Credentials(<redacted>)"


def unconfigured_credentials(venue: str, account_scope: str) -> Credentials:
    """The shipped default has no source of live credentials."""
    raise ValueError("trading credentials are not configured")


def _valid_now(now: datetime) -> None:
    if type(now) is not datetime or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("an aware dispatch instant is required")


def _credentials_match(value: Credentials, request: PreparedRequest) -> bool:
    if type(value) is not Credentials:
        return False
    if (type(value.venue) is not str or type(value.account_scope) is not str
            or value.venue != request.venue or value.account_scope != request.account_scope):
        return False
    names = ["access_key", "secret_key"]
    if request.venue == "okx":
        names.append("passphrase")
    if request.venue == "kis":
        names.extend(("bearer_token", "account_number", "account_product"))
    for name in names:
        item = getattr(value, name)
        if type(item) is not str or not item or len(item) > 16384 or any(ord(ch) < 32 or ord(ch) == 127 for ch in item):
            return False
    if request.venue == "kis":
        return (len(value.account_number) == 8 and value.account_number.isascii() and value.account_number.isdigit()
                and len(value.account_product) == 2 and value.account_product.isascii()
                and value.account_product.isdigit())
    return True


def _timestamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _upbit_jwt(credentials: Credentials, pairs: tuple[tuple[str, str], ...]) -> str:
    payload = {"access_key": credentials.access_key, "nonce": str(uuid.uuid4())}
    if pairs:
        # Official Upbit convention: unquote(urlencode(pairs)), preserving order.
        query = unquote(urlencode(pairs))
        payload["query_hash"] = hashlib.sha512(query.encode("utf-8")).hexdigest()
        payload["query_hash_alg"] = "SHA512"
    message = ".".join(_b64url(json.dumps(part, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
                       for part in ({"alg": "HS512", "typ": "JWT"}, payload))
    signature = hmac.new(credentials.secret_key.encode("utf-8"), message.encode("ascii"), hashlib.sha512).digest()
    return message + "." + _b64url(signature)


def _wire(request: PreparedRequest, credentials: Credentials, now: datetime) -> tuple[str, dict, bytes]:
    """Transient authenticated wire values; callers must never log this tuple."""
    pairs, body_pairs = request.params, request.body
    if request.venue == "kis":
        account = (("CANO", credentials.account_number), ("ACNT_PRDT_CD", credentials.account_product))
        if request.method == "GET":
            pairs = account + pairs
        else:
            body_pairs = account + body_pairs
    query = urlencode(pairs)
    request_path = request.path + ("?" + query if query else "")
    body = json.dumps(dict(body_pairs), ensure_ascii=False, separators=(",", ":")).encode("utf-8") if body_pairs else b""
    headers = {"Accept": "application/json", "Content-Type": "application/json; charset=utf-8"}
    if request.venue == "upbit":
        headers["Authorization"] = "Bearer " + _upbit_jwt(credentials, body_pairs if body_pairs else pairs)
    elif request.venue == "okx":
        stamp = _timestamp(now)
        prehash = stamp.encode("ascii") + request.method.encode("ascii") + request_path.encode("ascii") + body
        signature = base64.b64encode(hmac.new(credentials.secret_key.encode("utf-8"), prehash, hashlib.sha256).digest())
        headers.update({"OK-ACCESS-KEY": credentials.access_key, "OK-ACCESS-SIGN": signature.decode("ascii"),
                        "OK-ACCESS-TIMESTAMP": stamp, "OK-ACCESS-PASSPHRASE": credentials.passphrase})
    else:
        headers.update({"authorization": "Bearer " + credentials.bearer_token,
                        "appkey": credentials.access_key, "appsecret": credentials.secret_key,
                        "custtype": "P", **dict(request.headers)})
    return HOSTS[request.venue] + request_path, headers, body


def _send(method: str, url: str, *, headers: dict, body: bytes, timeout: float):
    """Only HTTP seam: one attempt, verified TLS and explicit reviewed routing."""
    options = route_options(url)
    with requests.Session() as session:
        session.trust_env = False
        response = session.request(method, url, headers=headers, data=body or None, timeout=timeout,
                                   allow_redirects=False, proxies=options.proxies, verify=options.verify)
        return response.status_code, response.headers, response.content


def _unknown(request: PreparedRequest, code: str) -> AdapterResult:
    return AdapterResult(status="unknown", code=code, client_id=request.client_id)


def _json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate response field")
        value[key] = item
    return value


def _json_constant(value):
    raise ValueError("nonfinite JSON constant")


def _codec(venue: str):
    if type(venue) is not str or venue not in HOSTS:
        raise ValueError("unsupported execution venue")
    from execution_orders import kis, okx, upbit
    return {"kis": kis, "okx": okx, "upbit": upbit}[venue]


def _kis_account_echo_matches(response: dict, credentials: Credentials) -> bool:
    """Reject contradictory optional account echoes without recording the value."""
    expected = {"CANO": credentials.account_number, "cano": credentials.account_number,
                "ACNT_PRDT_CD": credentials.account_product, "acnt_prdt_cd": credentials.account_product}
    pending = [response]
    while pending:
        value = pending.pop()
        if type(value) is dict:
            for key, item in value.items():
                if key in expected and (type(item) is not str or item != expected[key]):
                    return False
                if type(item) in (dict, list):
                    pending.append(item)
        elif type(value) is list:
            pending.extend(value)
    return True


def dispatch(request: PreparedRequest, capability, *, credentials=unconfigured_credentials,
             now: datetime) -> AdapterResult:
    """Dispatch once after immutable request and capability checks.

    Invalid requests/capabilities raise sanitized ValueError before provider use.
    Every failure after consumption is conservative UNKNOWN; no mutation retry is
    attempted and the controller retains its reservation pending reconciliation.
    A cancel acknowledgment also retains that reservation until terminal proof.
    """
    try:
        _valid_now(now)
        validate_request(request)
        original = request
        original_digest = request_digest(request)
        request = replace(request)  # a private copy; all nested fields are tuples of strings
    except Exception:
        raise ValueError("invalid prepared execution request") from None
    consume_capability(capability, request)
    try:
        selected = credentials(request.venue, request.account_scope)
    except Exception:
        return _unknown(request, "credentials_unavailable")
    if not _credentials_match(selected, request):
        return _unknown(request, "credential_scope_or_format")
    try:
        if request_digest(original) != original_digest:
            return _unknown(request, "request_changed")
        url, headers, body = _wire(request, selected, now)
    except Exception:
        return _unknown(request, "authentication_input")
    try:
        status, response_headers, content = _send(request.method, url, headers=headers, body=body, timeout=TIMEOUT_S)
    except Exception:
        return _unknown(request, "delivery_uncertain")
    if type(status) is not int or not 200 <= status < 300:
        return _unknown(request, "http_uncertain")
    if type(content) is not bytes or len(content) > MAX_RESPONSE_BYTES:
        return _unknown(request, "response_uncertain")
    try:
        response = json.loads(content, object_pairs_hook=_json_object, parse_constant=_json_constant)
        if type(response) is not dict:
            return _unknown(request, "response_uncertain")
        if request.venue == "kis" and not _kis_account_echo_matches(response, selected):
            return _unknown(request, "account_identity_mismatch")
        # Pagination/partial responses cannot establish a complete reconciliation.
        if request.venue == "kis" and request.operation == "status":
            if not hasattr(response_headers, "items"):
                return _unknown(request, "response_uncertain")
            values = [v for k, v in response_headers.items() if k.lower() == "tr_cont"]
            continuation = values[0] if values else None
            if any(value != continuation for value in values):
                return _unknown(request, "response_uncertain")
            response = {**response, "_tr_cont": continuation}  # body content cannot forge header completeness
        result = _codec(request.venue).parse(response, request)
        if type(result) is not AdapterResult:
            return _unknown(request, "response_uncertain")
        return result
    except Exception:
        return _unknown(request, "response_uncertain")


@dataclass(frozen=True, kw_only=True, repr=False)
class AuthenticatedTransport:
    """Controller-compatible adapter; time and trading credentials stay explicit."""

    credentials: Callable[[str, str], Credentials] = unconfigured_credentials

    def prepare(self, order, rules) -> PreparedRequest:
        return _codec(order.venue).prepare(order, rules)

    def prepare_cancel(self, order, venue_order_id: str, **kwargs) -> PreparedRequest:
        return _codec(order.venue).prepare_cancel(order, venue_order_id, **kwargs)

    def prepare_status(self, order, venue_order_id: str = "", **kwargs) -> PreparedRequest:
        return _codec(order.venue).prepare_status(order, venue_order_id, **kwargs)

    def dispatch(self, request: PreparedRequest, capability, *, now: datetime) -> AdapterResult:
        return dispatch(request, capability, credentials=self.credentials, now=now)
