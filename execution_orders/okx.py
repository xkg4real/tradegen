"""OKX cash SPOT limit protocol; acknowledgments are never final fill evidence.

Source: https://www.okx.com/docs-v5/en/ (trade/order and cancel-order).
Client IDs are locally never reused; the venue only guarantees pending uniqueness.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
import re

from execution_control.model import InstrumentRules, Order, decimal_text, order_digest, validate_order
from execution_orders.model import (AdapterResult, PreparedRequest, bound_order, identity,
                                    make_request, mapping, number, rejected, unknown)

# Definite input/funding refusals only. Unlisted venue codes remain ambiguous.
_REJECTIONS = frozenset({"51000", "51001", "51006", "51007", "51008", "51020"})


def _build(order: Order, operation: str, venue_order_id: str = "") -> PreparedRequest:
    order_digest(order)
    if order.venue != "okx" or re.fullmatch(r"[A-Za-z0-9]{1,32}", order.client_id) is None:
        raise ValueError("invalid OKX order identity")
    if operation == "create":
        body = (("instId", order.symbol), ("tdMode", "cash"), ("side", order.side), ("ordType", "limit"),
                ("sz", decimal_text(order.quantity)), ("px", decimal_text(order.limit_price)),
                ("clOrdId", order.client_id))
        return make_request(order, operation=operation, method="POST", path="/api/v5/trade/order", body=body)
    identity(venue_order_id, optional=operation == "status")
    if venue_order_id and re.fullmatch(r"[0-9]{1,32}", venue_order_id) is None:
        raise ValueError("invalid OKX broker identity")
    selected = (("instId", order.symbol), ("ordId", venue_order_id)) if venue_order_id else (
        ("instId", order.symbol), ("clOrdId", order.client_id))
    return make_request(order, operation=operation, method="POST" if operation == "cancel" else "GET",
                        path="/api/v5/trade/cancel-order" if operation == "cancel" else "/api/v5/trade/order",
                        body=selected if operation == "cancel" else (), params=selected if operation == "status" else (),
                        metadata=(("venue_order_id", venue_order_id),))


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


def _failure(code: object, request: PreparedRequest) -> AdapterResult:
    if type(code) is not str:
        return unknown(request)
    if code in _REJECTIONS:
        return rejected(request)
    return unknown(request, "venue_error")


def parse(response: Mapping, request: PreparedRequest) -> AdapterResult:
    validate_request(request)
    order = bound_order(request)
    try:
        data = mapping(response)
        if data.get("code") != "0":
            return _failure(data.get("code"), request)
        rows = data.get("data")
        if type(rows) is not list or len(rows) != 1:
            return unknown(request, "ambiguous_response")
        row = mapping(rows[0])
        if request.operation != "status" and row.get("sCode") != "0":
            return _failure(row.get("sCode"), request)
        if request.operation == "status" and "sCode" in row and row["sCode"] != "0":
            return _failure(row["sCode"], request)
        broker_id = identity(row["ordId"])
        if re.fullmatch(r"[0-9]{1,32}", broker_id) is None:
            return unknown(request, "identity_mismatch")
        wanted = dict(request.metadata).get("venue_order_id", "")
        if wanted and wanted != broker_id:
            return unknown(request, "identity_mismatch")
        # Cancel by ordId may omit clOrdId, but must never echo a conflicting one.
        client = row.get("clOrdId")
        if client != order.client_id and not (request.operation == "cancel" and client in (None, "") and wanted):
            return unknown(request, "identity_mismatch")
        for key, value in (("instId", order.symbol), ("instType", "SPOT"), ("tdMode", "cash"),
                           ("side", order.side), ("ordType", "limit")):
            if key in row and row[key] != value:
                return unknown(request, "identity_mismatch")
        for key, value in (("px", order.limit_price), ("sz", order.quantity)):
            if key in row and number(row[key], positive=True) != value:
                return unknown(request, "identity_mismatch")
        if request.operation != "status":
            return AdapterResult(status="accepted", code="acknowledged", venue_order_id=broker_id,
                                 client_id=order.client_id)
        if (row.get("instId") != order.symbol or row.get("instType") != "SPOT" or row.get("tdMode") != "cash"
                or row.get("side") != order.side or row.get("ordType") != "limit"
                or number(row["sz"], positive=True) != order.quantity
                or number(row["px"], positive=True) != order.limit_price):
            return unknown(request, "identity_mismatch")
        filled = number(row["accFillSz"])
        if filled > order.quantity:
            return unknown(request, "quantity_mismatch")
        state = row.get("state")
        states = {"live": "open", "partially_filled": "partial", "filled": "filled", "canceled": "canceled"}
        if type(state) is not str or state not in states:
            return unknown(request, "unsupported_state")
        if ((state == "live" and filled != 0) or (state == "partially_filled" and not 0 < filled < order.quantity)
                or (state == "filled" and filled != order.quantity)):
            return unknown(request, "quantity_mismatch")
        average = number(row["avgPx"], positive=True) if filled > 0 else None
        # Fee sign on OKX: negative is charged, positive is rebate. A rebate
        # cannot be converted into a zero expense; leave it to full fill history.
        fee = None
        currency = ""
        if type(row.get("fee")) is str and row["fee"].startswith("-"):
            fee = number(row["fee"][1:])
        elif row.get("fee") == "0":
            fee = Decimal("0")
        if fee is not None:
            currency = row.get("feeCcy")
            if type(currency) is not str or re.fullmatch(r"[A-Z0-9]{1,20}", currency) is None:
                return unknown(request, "fee_incomplete")
        return AdapterResult(status=states[state], code="order_observed", venue_order_id=broker_id,
                             client_id=order.client_id, filled_quantity=filled, average_price=average,
                             fee=fee, fee_currency=currency)
    except (ValueError, KeyError, TypeError):
        return unknown(request)
