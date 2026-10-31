"""Upbit KRW cash limit order protocol; no I/O, credentials or rounding.

Sources: docs.upbit.com/kr/reference/{new-order,get-order,cancel-order}.
A DELETE acknowledgment never establishes a final cancellation.
"""
from __future__ import annotations

from collections.abc import Mapping
from fractions import Fraction

from execution_control.model import InstrumentRules, Order, decimal_text, order_digest, validate_order
from execution_orders.model import (AdapterResult, PreparedRequest, bound_order, identity,
                                    make_request, mapping, number, rejected, unknown)

_REJECTIONS = frozenset({"validation_error", "insufficient_funds_bid", "insufficient_funds_ask",
                         "under_min_total_bid", "under_min_total_ask", "create_bid_error", "create_ask_error"})


def _build(order: Order, operation: str, venue_order_id: str = "") -> PreparedRequest:
    order_digest(order)
    if order.venue != "upbit":
        raise ValueError("wrong venue")
    if operation == "create":
        body = (("market", order.symbol), ("side", "bid" if order.side == "buy" else "ask"),
                ("volume", decimal_text(order.quantity)), ("price", decimal_text(order.limit_price)),
                ("ord_type", "limit"), ("identifier", order.client_id))
        return make_request(order, operation=operation, method="POST", path="/v1/orders", body=body)
    identity(venue_order_id, optional=operation == "status")
    params = (("uuid", venue_order_id),) if venue_order_id else (("identifier", order.client_id),)
    return make_request(order, operation=operation, method="DELETE" if operation == "cancel" else "GET",
                        path="/v1/order", params=params, metadata=(("venue_order_id", venue_order_id),))


def prepare(order: Order, rules: InstrumentRules) -> PreparedRequest:
    validate_order(order, rules)
    return _build(order, "create")


def prepare_cancel(order: Order, venue_order_id: str) -> PreparedRequest:
    return _build(order, "cancel", venue_order_id)


def prepare_status(order: Order, venue_order_id: str = "") -> PreparedRequest:
    return _build(order, "status", venue_order_id)


def validate_request(request: PreparedRequest) -> None:
    order = bound_order(request)
    if request.operation == "create":
        expected = _build(order, "create")
    else:
        if tuple(key for key, _ in request.metadata) != ("venue_order_id",):
            raise ValueError("invalid response identity")
        expected = _build(order, request.operation, dict(request.metadata)["venue_order_id"])
    if request != expected:
        raise ValueError("request payload mismatch")


def parse(response: Mapping, request: PreparedRequest) -> AdapterResult:
    validate_request(request)
    order = bound_order(request)
    try:
        data = mapping(response)
        if "error" in data:
            name = mapping(data["error"]).get("name")
            return rejected(request) if type(name) is str and name in _REJECTIONS else unknown(request, "venue_error")
        broker_id = identity(data["uuid"])
        expected_id = dict(request.metadata).get("venue_order_id", "")
        if expected_id and broker_id != expected_id:
            return unknown(request, "identity_mismatch")
        if (data.get("identifier") != order.client_id or data.get("market") != order.symbol
                or data.get("side") != ("bid" if order.side == "buy" else "ask")
                or data.get("ord_type") != "limit" or number(data["price"], positive=True) != order.limit_price
                or number(data["volume"], positive=True) != order.quantity):
            return unknown(request, "identity_mismatch")
        filled = number(data["executed_volume"])
        remaining = number(data["remaining_volume"])
        if Fraction(filled) + Fraction(remaining) != Fraction(order.quantity):
            return unknown(request, "quantity_mismatch")
        state = data.get("state")
        if state not in ("wait", "done", "cancel"):
            return unknown(request, "unsupported_state")
        if (state == "done" and remaining != 0) or (state == "wait" and remaining == 0):
            return unknown(request, "quantity_mismatch")
        fee = number(data["paid_fee"]) if "paid_fee" in data else None
        # Only the status endpoint can establish a reconciled terminal label.
        status = ("accepted" if request.operation != "status" else "filled" if state == "done" else
                  "canceled" if state == "cancel" else "partial" if filled > 0 else "open")
        return AdapterResult(status=status, code="order_observed", venue_order_id=broker_id,
                             client_id=order.client_id, filled_quantity=filled,
                             fee=fee, fee_currency="KRW" if fee is not None else "")
    except (ValueError, KeyError, TypeError):
        return unknown(request)
