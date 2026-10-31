"""Immutable credential-free wire contracts and exact request identity.

Only the separate transport resolves account credentials. Codec response details
are reduced to fixed diagnostics; raw venue messages never enter these objects.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from execution_control.model import Order, decimal_text, order_digest

Pairs = tuple[tuple[str, str], ...]
_EXPECTED = ("market", "symbol", "side", "quantity", "limit_price", "quote_krw", "time_in_force")
_STATES = frozenset({"accepted", "rejected", "unknown", "open", "partial", "filled", "canceled"})


def pairs(value: object) -> None:
    if type(value) is not tuple:
        raise ValueError("invalid request fields")
    names = set()
    for pair in value:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError("invalid request fields")
        key, item = pair
        if type(key) is not str or type(item) is not str or not key or key in names:
            raise ValueError("invalid request fields")
        if len(key) > 64 or len(item) > 512 or any(ord(c) < 32 for c in key + item):
            raise ValueError("invalid request fields")
        names.add(key)


@dataclass(frozen=True, kw_only=True)
class PreparedRequest:
    venue: str
    operation: str
    method: str
    path: str
    params: Pairs
    body: Pairs
    order_digest: str
    client_id: str
    account_scope: str
    headers: Pairs = ()
    expected: Pairs = ()
    metadata: Pairs = ()

    def __post_init__(self) -> None:
        _shape(self)


@dataclass(frozen=True, kw_only=True)
class AdapterResult:
    status: str
    code: str
    venue_order_id: str = ""
    client_id: str = ""
    metadata: Pairs = ()
    filled_quantity: Decimal | None = None
    average_price: Decimal | None = None
    fee: Decimal | None = None
    fee_currency: str = ""

    def __post_init__(self) -> None:
        if type(self.status) is not str or self.status not in _STATES:
            raise ValueError("invalid adapter status")
        if type(self.code) is not str or re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.code) is None:
            raise ValueError("invalid adapter code")
        for value in (self.venue_order_id, self.client_id, self.fee_currency):
            if type(value) is not str or len(value) > 128 or any(ord(c) < 32 for c in value):
                raise ValueError("invalid adapter identity")
        pairs(self.metadata)
        for value in (self.filled_quantity, self.average_price, self.fee):
            if value is not None:
                decimal_text(value)


def _shape(request: PreparedRequest) -> None:
    if type(request) is not PreparedRequest:
        raise ValueError("invalid prepared request")
    for field in fields(request):
        value = getattr(request, field.name)
        if field.name in ("params", "body", "headers", "expected", "metadata"):
            pairs(value)
        elif type(value) is not str or len(value) > 256 or any(ord(c) < 32 for c in value):
            raise ValueError("invalid prepared request")
    if request.venue not in ("upbit", "kis", "okx") or request.operation not in ("create", "cancel", "status"):
        raise ValueError("unsupported prepared request")
    if re.fullmatch(r"[0-9a-f]{64}", request.order_digest) is None:
        raise ValueError("invalid order digest")


def bound_order(request: PreparedRequest) -> Order:
    _shape(request)
    if tuple(key for key, _ in request.expected) != _EXPECTED:
        raise ValueError("incomplete request identity")
    values = dict(request.expected)
    for key in ("quantity", "limit_price", "quote_krw"):
        values[key] = number(values[key], positive=True)
    order = Order(client_id=request.client_id, account_scope=request.account_scope,
                  venue=request.venue, **values)
    if order_digest(order) != request.order_digest:
        raise ValueError("request order mismatch")
    return order


def make_request(order: Order, *, operation: str, method: str, path: str,
                 params: Pairs = (), body: Pairs = (), headers: Pairs = (),
                 metadata: Pairs = ()) -> PreparedRequest:
    digest = order_digest(order)
    expected = tuple((name, decimal_text(value) if type(value := getattr(order, name)) is Decimal else value)
                     for name in _EXPECTED)
    return PreparedRequest(venue=order.venue, operation=operation, method=method, path=path,
                           params=params, body=body, order_digest=digest, client_id=order.client_id,
                           account_scope=order.account_scope, headers=headers, expected=expected,
                           metadata=metadata)


def validate_request(request: PreparedRequest) -> None:
    """Validate every wire field before capability consumption or credential use."""
    bound_order(request)
    # Explicit imports; no arbitrary module lookup or alternate transport path.
    from execution_orders import kis, okx, upbit
    {"upbit": upbit, "kis": kis, "okx": okx}[request.venue].validate_request(request)


def request_digest(request: PreparedRequest) -> str:
    _shape(request)
    body = {field.name: getattr(request, field.name) for field in fields(request)}
    encoded = json.dumps(body, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def number(value: object, *, positive: bool = False) -> Decimal:
    """Read bounded plain decimal protocol strings; reject coercion and nonfinite."""
    if type(value) is not str or len(value) > 128 or re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is None:
        raise ValueError("invalid response number")
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError("invalid response number") from None
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError("invalid response number")
    return result


def identity(value: object, *, optional: bool = False) -> str:
    if optional and value == "" and type(value) is str:
        return value
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", value) is None:
        raise ValueError("invalid broker identity")
    return value


def unknown(request: PreparedRequest, code: str = "malformed_response") -> AdapterResult:
    return AdapterResult(status="unknown", code=code, client_id=request.client_id)


def rejected(request: PreparedRequest, code: str = "venue_rejected") -> AdapterResult:
    return AdapterResult(status="rejected", code=code, client_id=request.client_id)


def mapping(value: object) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValueError("invalid response shape")
    return value
