"""KIS KRX/US cash limit codecs, with explicit broker references.

Official cash order, cancellation and inquiry example sources
were checked on 2026-10-31. No account data belongs in prepared requests.
US terminal cancellation and paginated status are deliberately unsupported:
they remain UNKNOWN until independently authoritative reconciliation exists.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from decimal import Decimal
from fractions import Fraction
import re

from execution_control.model import InstrumentRules, Order, decimal_text, order_digest, validate_order
from execution_orders.model import (AdapterResult, PreparedRequest, bound_order, identity,
                                    make_request, mapping, number, unknown)

_KRX_CREATE = "/uapi/domestic-stock/v1/trading/order-cash"
_KRX_CANCEL = "/uapi/domestic-stock/v1/trading/order-rvsecncl"
_KRX_STATUS = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
_US_CREATE = "/uapi/overseas-stock/v1/trading/order"
_US_CANCEL = "/uapi/overseas-stock/v1/trading/order-rvsecncl"
_US_STATUS = "/uapi/overseas-stock/v1/trading/inquire-ccnl"


def _broker(value: object, *, optional: bool = False) -> str:
    identity(value, optional=optional)
    if value and re.fullmatch(r"[0-9]{1,20}", value) is None:
        raise ValueError("invalid KIS broker identity")
    return value


def _date(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9]{8}", value) is None:
        raise ValueError("missing venue trading date")
    try:
        date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        raise ValueError("invalid venue trading date") from None
    return value


def _shares(value: object) -> Decimal:
    result = number(value)
    if Fraction(result).denominator != 1:
        raise ValueError("fractional share response")
    return result


def _build(order: Order, operation: str, venue_order_id: str = "", *, broker_org_id: str = "",
           order_date: str = "", remaining_quantity: Decimal | None = None) -> PreparedRequest:
    order_digest(order)
    if order.venue != "kis":
        raise ValueError("wrong venue")
    domestic = order.market == "krx"
    if operation == "create":
        if domestic:
            tr_id = "TTTC0012U" if order.side == "buy" else "TTTC0011U"
            body = (("PDNO", order.symbol), ("ORD_DVSN", "00"), ("ORD_QTY", decimal_text(order.quantity)),
                    ("ORD_UNPR", decimal_text(order.limit_price)), ("EXCG_ID_DVSN_CD", "KRX"),
                    ("SLL_TYPE", "" if order.side == "buy" else "01"), ("CNDT_PRIC", ""))
        else:
            tr_id = "TTTT1002U" if order.side == "buy" else "TTTT1006U"
            body = (("OVRS_EXCG_CD", order.market.upper()), ("PDNO", order.symbol),
                    ("ORD_QTY", decimal_text(order.quantity)), ("OVRS_ORD_UNPR", decimal_text(order.limit_price)),
                    ("CTAC_TLNO", ""), ("MGCO_APTM_ODNO", ""), ("SLL_TYPE", "" if order.side == "buy" else "00"),
                    ("ORD_SVR_DVSN_CD", "0"), ("ORD_DVSN", "00"))
        return make_request(order, operation=operation, method="POST",
                            path=_KRX_CREATE if domestic else _US_CREATE,
                            body=body, headers=(("tr_id", tr_id),))
    _broker(venue_order_id)
    _broker(broker_org_id, optional=not domestic)
    if operation == "cancel":
        if type(remaining_quantity) is not Decimal:
            raise ValueError("missing cancellable quantity")
        text = decimal_text(remaining_quantity)
        if not 0 < remaining_quantity <= order.quantity or Fraction(remaining_quantity).denominator != 1:
            raise ValueError("invalid cancellable quantity")
        metadata = (("venue_order_id", venue_order_id), ("broker_org_id", broker_org_id),
                    ("remaining_quantity", text))
        if domestic:
            body = (("KRX_FWDG_ORD_ORGNO", broker_org_id), ("ORGN_ODNO", venue_order_id),
                    ("ORD_DVSN", "00"), ("RVSE_CNCL_DVSN_CD", "02"), ("ORD_QTY", text), ("ORD_UNPR", "0"),
                    ("QTY_ALL_ORD_YN", "N"), ("EXCG_ID_DVSN_CD", "KRX"), ("CNDT_PRIC", ""))
        else:
            body = (("OVRS_EXCG_CD", order.market.upper()), ("PDNO", order.symbol), ("ORGN_ODNO", venue_order_id),
                    ("RVSE_CNCL_DVSN_CD", "02"), ("ORD_QTY", text), ("OVRS_ORD_UNPR", "0"),
                    ("MGCO_APTM_ODNO", ""), ("ORD_SVR_DVSN_CD", "0"))
        return make_request(order, operation=operation, method="POST",
                            path=_KRX_CANCEL if domestic else _US_CANCEL, body=body,
                            headers=(("tr_id", "TTTC0013U" if domestic else "TTTT1004U"),), metadata=metadata)
    order_date = _date(order_date)
    metadata = (("venue_order_id", venue_order_id), ("broker_org_id", broker_org_id), ("order_date", order_date))
    side = "02" if order.side == "buy" else "01"
    if domestic:
        params = (("INQR_STRT_DT", order_date), ("INQR_END_DT", order_date), ("SLL_BUY_DVSN_CD", side),
                  ("PDNO", order.symbol), ("CCLD_DVSN", "00"), ("INQR_DVSN", "00"), ("INQR_DVSN_3", "01"),
                  ("ORD_GNO_BRNO", ""), ("ODNO", venue_order_id), ("INQR_DVSN_1", ""),
                  ("CTX_AREA_FK100", ""), ("CTX_AREA_NK100", ""), ("EXCG_ID_DVSN_CD", "KRX"))
    else:
        # The official endpoint forbids order-number filtering. Match the
        # returned broker identity locally, only after a complete response.
        params = (("PDNO", order.symbol), ("ORD_STRT_DT", order_date), ("ORD_END_DT", order_date),
                  ("SLL_BUY_DVSN", side), ("CCLD_NCCS_DVSN", "00"), ("OVRS_EXCG_CD", order.market.upper()),
                  ("SORT_SQN", "DS"), ("ORD_DT", ""), ("ORD_GNO_BRNO", ""), ("ODNO", ""),
                  ("CTX_AREA_NK200", ""), ("CTX_AREA_FK200", ""))
    return make_request(order, operation=operation, method="GET",
                        path=_KRX_STATUS if domestic else _US_STATUS,
                        params=params, headers=(("tr_id", "TTTC0081R" if domestic else "TTTS3035R"),),
                        metadata=metadata)


def prepare(order: Order, rules: InstrumentRules) -> PreparedRequest:
    validate_order(order, rules)
    return _build(order, "create")


def prepare_cancel(order: Order, venue_order_id: str, *, broker_org_id: str = "",
                   remaining_quantity: Decimal | None = None) -> PreparedRequest:
    return _build(order, "cancel", venue_order_id, broker_org_id=broker_org_id,
                  remaining_quantity=remaining_quantity)


def prepare_status(order: Order, venue_order_id: str, *, order_date: str = "",
                   broker_org_id: str = "") -> PreparedRequest:
    return _build(order, "status", venue_order_id, broker_org_id=broker_org_id, order_date=order_date)


def validate_request(request: PreparedRequest) -> None:
    order = bound_order(request)
    meta = dict(request.metadata)
    if request.operation == "create":
        expected = _build(order, "create")
    elif request.operation == "cancel":
        if tuple(meta) != ("venue_order_id", "broker_org_id", "remaining_quantity"):
            raise ValueError("invalid cancel reference")
        expected = _build(order, "cancel", meta["venue_order_id"], broker_org_id=meta["broker_org_id"],
                          remaining_quantity=number(meta["remaining_quantity"], positive=True))
    else:
        if tuple(meta) != ("venue_order_id", "broker_org_id", "order_date"):
            raise ValueError("invalid status reference")
        expected = _build(order, "status", meta["venue_order_id"], broker_org_id=meta["broker_org_id"],
                          order_date=meta["order_date"])
    if request != expected:
        raise ValueError("request payload mismatch")


def _ack(data: Mapping, request: PreparedRequest, order: Order) -> AdapterResult:
    output = mapping(data["output"])
    # Most ACKs contain broker IDs only. Any supplied order echo must agree.
    for key, value in request.body:
        if key in output and output[key] != value:
            return unknown(request, "identity_mismatch")
    broker_id = _broker(output["ODNO"])
    org = _broker(output.get("KRX_FWDG_ORD_ORGNO", ""), optional=order.market != "krx")
    metadata = (("broker_org_id", org),) if org else ()
    if request.operation == "cancel":
        reference = dict(request.metadata)
        original = reference["venue_order_id"]
        if "ORGN_ODNO" in output and output["ORGN_ODNO"] != original:
            return unknown(request, "identity_mismatch")
        # KIS assigns a separate order number to the cancellation request.
        metadata = (("broker_org_id", reference["broker_org_id"]), ("cancel_order_id", broker_id))
        broker_id = original
    return AdapterResult(status="accepted", code="acknowledged", venue_order_id=broker_id,
                         client_id=order.client_id, metadata=metadata)


def _status(data: Mapping, request: PreparedRequest, order: Order) -> AdapterResult:
    continuation = data.get("_tr_cont")  # Transport overwrites from real response headers.
    if continuation in ("M", "F"):
        return unknown(request, "pagination_required")
    if continuation not in ("", "D", "E"):
        return unknown(request, "incomplete_response")
    domestic = order.market == "krx"
    rows = data.get("output1" if domestic else "output")
    if type(rows) is not list:
        return unknown(request)
    meta = dict(request.metadata)
    matches = [mapping(row) for row in rows if mapping(row).get("odno") == meta["venue_order_id"]]
    if len(matches) != 1:
        return unknown(request, "ambiguous_response")
    row = matches[0]
    if (row.get("pdno") != order.symbol or row.get("ord_dt") != meta["order_date"]
            or row.get("sll_buy_dvsn_cd") != ("02" if order.side == "buy" else "01")):
        return unknown(request, "identity_mismatch")
    if meta["broker_org_id"] and "ord_gno_brno" in row and row["ord_gno_brno"] != meta["broker_org_id"]:
        return unknown(request, "identity_mismatch")
    qty_key, price_key = ("ord_qty", "ord_unpr") if domestic else ("ft_ord_qty", "ft_ord_unpr3")
    if number(row[qty_key], positive=True) != order.quantity or number(row[price_key], positive=True) != order.limit_price:
        return unknown(request, "identity_mismatch")
    if domestic:
        # Current sample's exchange-ID output has a capital C. Accept either
        # documented spelling only when all supplied spellings agree on KRX.
        exchanges = [row[key] for key in ("excg_id_dvsn_cd", "excg_id_dvsn_Cd") if key in row]
        if not exchanges or any(value != "KRX" for value in exchanges) or row.get("ord_dvsn_cd") != "00":
            return unknown(request, "identity_mismatch")
        filled, remaining = _shares(row["tot_ccld_qty"]), _shares(row["rmn_qty"])
        canceled, refused = _shares(row["cnc_cfrm_qty"]), _shares(row["rjct_qty"])
        if refused != 0 or Fraction(filled) + Fraction(remaining) + Fraction(canceled) != Fraction(order.quantity):
            return unknown(request, "quantity_mismatch")
        if row.get("cncl_yn") not in ("Y", "N") or (canceled > 0 and row["cncl_yn"] != "Y"):
            return unknown(request, "unsupported_state")
        state = ("filled" if filled == order.quantity else "canceled" if canceled > 0 and remaining == 0 else
                 "partial" if filled > 0 else "open")
        average = number(row["avg_prvs"], positive=True) if filled > 0 else None
    else:
        if row.get("ovrs_excg_cd") != order.market.upper():
            return unknown(request, "identity_mismatch")
        filled, remaining = _shares(row["ft_ccld_qty"]), _shares(row["nccs_qty"])
        if Fraction(filled) + Fraction(remaining) != Fraction(order.quantity):
            return unknown(request, "unverified_cancel_state")
        # No unverified translated status label is treated as final cancellation.
        state = "filled" if filled == order.quantity else "partial" if filled > 0 else "open"
        average = number(row["ft_ccld_unpr3"], positive=True) if filled > 0 else None
    result_meta = tuple((key, meta[key]) for key in ("broker_org_id", "order_date"))
    return AdapterResult(status=state, code="order_observed", venue_order_id=meta["venue_order_id"],
                         client_id=order.client_id, metadata=result_meta, filled_quantity=filled,
                         average_price=average)


def parse(response: Mapping, request: PreparedRequest) -> AdapterResult:
    validate_request(request)
    order = bound_order(request)
    try:
        data = mapping(response)
        if data.get("rt_cd") != "0":
            # No exhaustive official error-code classification is pinned here.
            return unknown(request, "venue_error")
        return _status(data, request, order) if request.operation == "status" else _ack(data, request, order)
    except (ValueError, KeyError, TypeError):
        return unknown(request)
