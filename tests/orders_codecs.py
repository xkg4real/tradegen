"""Independent protocol fixtures for E3; pure code, no network or credentials.

Sources: official Upbit REST references, KIS open-trading-api examples_llm
order/check scripts, and OKX v5 trade documentation checked 2026-10-31.
The expected payloads below are literal fixtures, not computed by the codecs.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext

from execution_control.model import InstrumentRules, Order
from execution_orders import kis, okx, upbit
from execution_orders.model import AdapterResult, PreparedRequest, request_digest, validate_request

D = Decimal
NOW = datetime(2026, 10, 31, 1, 0, tzinfo=timezone.utc)
UUID = "d4ad1460-bf5d-4492-98e6-c42a67b1f8c1"


def _order(venue="upbit", *, side="buy", market=None, **changes):
    values = dict(client_id="fixtureOrderA", account_scope="fixtureAccount", venue=venue,
                  market=market or ("krx" if venue == "kis" else "spot"),
                  symbol="005930" if venue == "kis" and market in (None, "krx") else
                  "AAPL" if venue == "kis" else "KRW-BTC" if venue == "upbit" else "BTC-USDT",
                  side=side, quantity=D("2"), limit_price=D("100"),
                  time_in_force="day" if venue == "kis" else "gtc",
                  quote_krw=D("1") if venue == "upbit" or venue == "kis" and market in (None, "krx") else D("1400"))
    values.update(changes)
    return Order(**values)


def _rules(order, **changes):
    values = dict(venue=order.venue, market=order.market, symbol=order.symbol, lot_size=D("1"),
                  tick_size=D("0.01"), min_quantity=D("1"), min_notional_krw=D("1"),
                  fee_fraction=D("0.001"), asof=NOW, source_digest="a" * 64)
    values.update(changes)
    return InstrumentRules(**values)


def _refused(fn):
    try:
        fn()
    except ValueError as exc:
        assert "fixture-secret" not in str(exc)
    else:
        raise AssertionError("expected refusal")


def _upbit_response(**changes):
    result = dict(uuid=UUID, identifier="fixtureOrderA", market="KRW-BTC", side="bid", ord_type="limit",
                  price="100", volume="2", executed_volume="0", remaining_volume="2", state="wait", paid_fee="0")
    result.update(changes)
    return result


def _okx_status(**changes):
    row = dict(ordId="123456", clOrdId="fixtureOrderA", instId="BTC-USDT", instType="SPOT", tdMode="cash",
               side="buy", ordType="limit", sz="2", px="100", accFillSz="0", avgPx="", state="live",
               fee="0", feeCcy="USDT")
    row.update(changes)
    return {"code": "0", "data": [row]}


def _kis_krx_status(**changes):
    row = dict(odno="123456", ord_dt="20261031", pdno="005930", sll_buy_dvsn_cd="02",
               ord_qty="2", ord_unpr="100", ord_dvsn_cd="00", excg_id_dvsn_cd="KRX", tot_ccld_qty="0",
               rmn_qty="2", cnc_cfrm_qty="0", rjct_qty="0", cncl_yn="N", avg_prvs="0")
    row.update(changes)
    return {"rt_cd": "0", "output1": [row], "_tr_cont": "D"}


def _kis_us_status(**changes):
    row = dict(odno="123456", ord_dt="20261030", pdno="AAPL", sll_buy_dvsn_cd="02",
               ft_ord_qty="2", ft_ord_unpr3="100", ovrs_excg_cd="NASD", ft_ccld_qty="0",
               nccs_qty="2", ft_ccld_unpr3="0")
    row.update(changes)
    return {"rt_cd": "0", "output": [row], "_tr_cont": "D"}


def test_prepared_request_is_deeply_immutable_and_credentials_free():
    order = _order()
    request = upbit.prepare(order, _rules(order))
    assert isinstance(request.body, tuple) and all(type(pair) is tuple for pair in request.body)
    try:
        request.path = "/evil"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("mutable request")
    _refused(lambda: replace(request, body=list(request.body)))
    _refused(lambda: replace(request, body=(("price", "100"), ("price", "101"))))
    assert not {"CANO", "ACNT_PRDT_CD", "authorization", "secret_key"} & set(dict(request.body))


def test_all_request_fields_are_bound_and_mutation_refused():
    for codec, order in ((upbit, _order()), (okx, _order("okx")), (kis, _order("kis"))):
        request = codec.prepare(order, _rules(order))
        validate_request(request)
        original = request_digest(request)
        alterations = ({"path": "https://other.invalid/order"}, {"method": "GET"},
                       {"body": request.body + (("extra", "fixture-secret"),)},
                       {"account_scope": "anotherAccount"}, {"client_id": "different"},
                       {"headers": request.headers + (("authorization", "fixture-secret"),)},
                       {"order_digest": "0" * 64})
        for changes in alterations:
            changed = replace(request, **changes)
            assert request_digest(changed) != original
            _refused(lambda: validate_request(changed))
        altered = deepcopy(request)
        object.__setattr__(altered, "body", (("bad", "mutable"),))
        _refused(lambda: validate_request(altered))


def test_order_bound_payload_cannot_disagree_on_price_side_or_quantity():
    order = _order()
    request = upbit.prepare(order, _rules(order))
    for key, value in (("price", "101"), ("volume", "3"), ("side", "ask"), ("market", "KRW-ETH")):
        body = tuple((k, value if k == key else v) for k, v in request.body)
        _refused(lambda: validate_request(replace(request, body=body)))


def test_invalid_numeric_types_and_nonfinite_inputs_are_refused():
    for value in (True, 1.0, "1", D("NaN"), D("Infinity"), D("-1"), D("0")):
        _refused(lambda: _order(quantity=value))
        _refused(lambda: _order(limit_price=value))
    for codec in (upbit, kis, okx):
        _refused(lambda: codec.prepare_cancel(None, "123456"))


def test_rules_no_rounding_or_fractional_kis_shares():
    order = _order(quantity=D("1.5"))
    _refused(lambda: upbit.prepare(order, _rules(order)))
    order = _order(limit_price=D("100.005"))
    _refused(lambda: upbit.prepare(order, _rules(order)))
    _refused(lambda: _order("kis", quantity=D("1.5")))
    order = _order(quantity=D("2.0000"), limit_price=D("100.00"))
    with localcontext() as context:
        context.prec = 2
        request = upbit.prepare(order, _rules(order))
    assert dict(request.body)["volume"] == "2" and dict(request.body)["price"] == "100"


def test_upbit_create_golden_payload_and_identifiers():
    order = _order()
    request = upbit.prepare(order, _rules(order))
    assert (request.method, request.path, request.params, request.headers) == ("POST", "/v1/orders", (), ())
    assert request.body == (("market", "KRW-BTC"), ("side", "bid"), ("volume", "2"), ("price", "100"),
                            ("ord_type", "limit"), ("identifier", "fixtureOrderA"))
    sell = replace(order, side="sell")
    assert dict(upbit.prepare(sell, _rules(sell)).body)["side"] == "ask"
    longest = replace(order, client_id="a" * 64)
    assert dict(upbit.prepare(longest, _rules(longest)).body)["identifier"] == "a" * 64
    _refused(lambda: replace(order, client_id="a" * 65))


def test_upbit_cancel_status_and_identifier_lookup_golden():
    order = _order()
    cancel = upbit.prepare_cancel(order, UUID)
    assert (cancel.method, cancel.path, cancel.params, cancel.body) == ("DELETE", "/v1/order", (("uuid", UUID),), ())
    assert upbit.prepare_status(order, UUID).params == (("uuid", UUID),)
    assert upbit.prepare_status(order).params == (("identifier", "fixtureOrderA"),)
    _refused(lambda: upbit.prepare_cancel(order, ""))
    for request in (cancel, upbit.prepare_status(order), upbit.prepare_status(order, UUID)):
        validate_request(request)


def test_upbit_acknowledgment_never_claims_final_fill_or_cancel():
    order = _order()
    create = upbit.prepare(order, _rules(order))
    assert upbit.parse(_upbit_response(), create).status == "accepted"
    cancel = upbit.prepare_cancel(order, UUID)
    result = upbit.parse(_upbit_response(state="cancel", executed_volume="1", remaining_volume="1"), cancel)
    assert result.status == "accepted" and result.filled_quantity == D("1")
    result = upbit.parse(_upbit_response(state="done", executed_volume="2", remaining_volume="0"), create)
    assert result.status == "accepted"


def test_upbit_partial_final_and_canceled_partial_cumulative():
    request = upbit.prepare_status(_order(), UUID)
    assert upbit.parse(_upbit_response(), request).status == "open"
    partial = upbit.parse(_upbit_response(executed_volume="1", remaining_volume="1", paid_fee="0.1"), request)
    assert (partial.status, partial.filled_quantity, partial.fee, partial.fee_currency) == ("partial", D("1"), D("0.1"), "KRW")
    result = upbit.parse(_upbit_response(state="cancel", executed_volume="1", remaining_volume="1"), request)
    assert result.status == "canceled" and result.filled_quantity == D("1")
    result = upbit.parse(_upbit_response(state="done", executed_volume="2", remaining_volume="0"), request)
    assert result.status == "filled" and result.filled_quantity == D("2")


def test_upbit_identity_quantity_state_and_malformed_responses_fail_closed():
    request = upbit.prepare_status(_order(), UUID)
    for field, value in (("uuid", "different"), ("identifier", "wrong"), ("side", "ask"), ("market", "KRW-ETH"),
                         ("price", "101"), ("volume", "3"), ("ord_type", "market"), ("state", "watch"),
                         ("executed_volume", "NaN"), ("remaining_volume", "3"), ("paid_fee", True)):
        assert upbit.parse(_upbit_response(**{field: value}), request).status == "unknown"
    for data in ({}, [], None, {"error": {"name": "order_not_found", "message": "fixture-secret"}}):
        result = upbit.parse(data, request)
        assert result.status == "unknown" and "fixture-secret" not in repr(result)


def test_upbit_missing_fee_is_not_inferred_zero_and_errors_sanitized():
    request = upbit.prepare(_order(), _rules(_order()))
    response = _upbit_response()
    del response["paid_fee"]
    assert upbit.parse(response, request).fee is None
    result = upbit.parse({"error": {"name": "insufficient_funds_bid", "message": "fixture-secret"}}, request)
    assert result.status == "rejected" and "fixture-secret" not in repr(result)


def test_okx_create_golden_and_client_id_constraints():
    order = _order("okx")
    request = okx.prepare(order, _rules(order))
    assert (request.method, request.path) == ("POST", "/api/v5/trade/order")
    assert request.body == (("instId", "BTC-USDT"), ("tdMode", "cash"), ("side", "buy"), ("ordType", "limit"),
                            ("sz", "2"), ("px", "100"), ("clOrdId", "fixtureOrderA"))
    for client in ("with_dash", "a" * 33):
        bad = replace(order, client_id=client)
        _refused(lambda: okx.prepare(bad, _rules(bad)))
    good = replace(order, client_id="a" * 32)
    validate_request(okx.prepare(good, _rules(good)))


def test_okx_cancel_status_golden_and_forbidden_extra_fields():
    order = _order("okx")
    cancel = okx.prepare_cancel(order, "123456")
    assert (cancel.method, cancel.path, cancel.body) == ("POST", "/api/v5/trade/cancel-order", (("instId", "BTC-USDT"), ("ordId", "123456")))
    status = okx.prepare_status(order)
    assert status.params == (("instId", "BTC-USDT"), ("clOrdId", "fixtureOrderA"))
    for request in (cancel, status, okx.prepare_status(order, "123456")):
        validate_request(request)
    request = okx.prepare(order, _rules(order))
    for key, value in (("posSide", "long"), ("reduceOnly", "true"), ("lever", "2"), ("tgtCcy", "quote_ccy")):
        _refused(lambda: validate_request(replace(request, body=request.body + ((key, value),))))


def test_okx_top_and_row_failures_and_timeout_code_never_success():
    request = okx.prepare(_order("okx"), _rules(_order("okx")))
    for response, status in (({"code": "51008", "msg": "fixture-secret"}, "rejected"),
                             ({"code": "50004", "msg": "fixture-secret"}, "unknown"),
                             ({"code": "0", "data": [{"sCode": "51008", "sMsg": "fixture-secret"}]}, "rejected"),
                             ({"code": "0", "data": [{"sCode": "50004", "sMsg": "fixture-secret"}]}, "unknown")):
        result = okx.parse(response, request)
        assert result.status == status and "fixture-secret" not in repr(result)


def test_okx_ack_cancel_race_and_response_identity():
    order = _order("okx")
    ack = {"code": "0", "data": [{"sCode": "0", "ordId": "123456", "clOrdId": "fixtureOrderA"}]}
    assert okx.parse(ack, okx.prepare(order, _rules(order))).status == "accepted"
    cancel = okx.prepare_cancel(order, "123456")
    assert okx.parse(ack, cancel).status == "accepted"
    for key, value in (("ordId", "654321"), ("clOrdId", "wrong"), ("instId", "ETH-USDT"), ("px", "101")):
        changed = deepcopy(ack)
        changed["data"][0][key] = value
        assert okx.parse(changed, cancel).status == "unknown"
    ack["data"][0]["state"] = "canceled"
    assert okx.parse(ack, cancel).status == "accepted"


def test_okx_partial_final_and_canceled_quantity_fee_currency():
    request = okx.prepare_status(_order("okx"), "123456")
    assert okx.parse(_okx_status(), request).status == "open"
    result = okx.parse(_okx_status(state="partially_filled", accFillSz="1", avgPx="99", fee="-0.001", feeCcy="BTC"), request)
    assert (result.status, result.filled_quantity, result.average_price, result.fee, result.fee_currency) == ("partial", D("1"), D("99"), D("0.001"), "BTC")
    result = okx.parse(_okx_status(state="canceled", accFillSz="1", avgPx="99"), request)
    assert result.status == "canceled" and result.filled_quantity == D("1")
    result = okx.parse(_okx_status(state="filled", accFillSz="2", avgPx="99"), request)
    assert result.status == "filled" and result.filled_quantity == D("2")


def test_okx_malformed_state_identity_and_rebate_not_zero_fee():
    request = okx.prepare_status(_order("okx"), "123456")
    for key, value in (("instType", "SWAP"), ("tdMode", "cross"), ("side", "sell"), ("sz", "3"),
                       ("px", "99"), ("state", "unknown"), ("accFillSz", "3"), ("accFillSz", True)):
        assert okx.parse(_okx_status(**{key: value}), request).status == "unknown"
    assert okx.parse({"code": "0", "data": []}, request).status == "unknown"
    response = _okx_status()
    response["data"] *= 2
    assert okx.parse(response, request).status == "unknown"
    assert okx.parse(_okx_status(fee="0.1"), request).fee is None
    assert okx.parse(_okx_status(state="filled", accFillSz="1", avgPx="99"), request).status == "unknown"


def test_kis_krx_create_golden_side_tr_and_no_account_fields():
    order = _order("kis")
    request = kis.prepare(order, _rules(order))
    assert (request.method, request.path, request.headers) == ("POST", "/uapi/domestic-stock/v1/trading/order-cash", (("tr_id", "TTTC0012U"),))
    assert request.body == (("PDNO", "005930"), ("ORD_DVSN", "00"), ("ORD_QTY", "2"), ("ORD_UNPR", "100"),
                            ("EXCG_ID_DVSN_CD", "KRX"), ("SLL_TYPE", ""), ("CNDT_PRIC", ""))
    sell = replace(order, side="sell")
    sell_request = kis.prepare(sell, _rules(sell))
    assert sell_request.headers == (("tr_id", "TTTC0011U"),) and dict(sell_request.body)["SLL_TYPE"] == "01"
    assert "CANO" not in dict(request.body) and "ACNT_PRDT_CD" not in dict(request.body)
    _refused(lambda: validate_request(replace(request, headers=sell_request.headers)))


def test_kis_us_create_golden_market_side_tr_and_sale_type():
    for market in ("nasd", "nyse", "amex"):
        order = _order("kis", market=market)
        request = kis.prepare(order, _rules(order))
        assert (request.method, request.path, request.headers) == ("POST", "/uapi/overseas-stock/v1/trading/order", (("tr_id", "TTTT1002U"),))
        assert request.body == (("OVRS_EXCG_CD", market.upper()), ("PDNO", "AAPL"), ("ORD_QTY", "2"),
                                ("OVRS_ORD_UNPR", "100"), ("CTAC_TLNO", ""), ("MGCO_APTM_ODNO", ""),
                                ("SLL_TYPE", ""), ("ORD_SVR_DVSN_CD", "0"), ("ORD_DVSN", "00"))
        sell = replace(order, side="sell")
        request = kis.prepare(sell, _rules(sell))
        assert request.headers == (("tr_id", "TTTT1006U"),) and dict(request.body)["SLL_TYPE"] == "00"
        validate_request(request)


def test_kis_cancel_requires_explicit_broker_org_and_cancellable_units():
    order = _order("kis")
    _refused(lambda: kis.prepare_cancel(order, "123456", remaining_quantity=D("1")))
    _refused(lambda: kis.prepare_cancel(order, "123456", broker_org_id="00123"))
    for quantity in (D("0"), D("3"), D("1.5"), True, "1", D("NaN")):
        _refused(lambda: kis.prepare_cancel(order, "123456", broker_org_id="00123", remaining_quantity=quantity))
    request = kis.prepare_cancel(order, "123456", broker_org_id="00123", remaining_quantity=D("1"))
    assert request.headers == (("tr_id", "TTTC0013U"),)
    assert request.body == (("KRX_FWDG_ORD_ORGNO", "00123"), ("ORGN_ODNO", "123456"), ("ORD_DVSN", "00"),
                            ("RVSE_CNCL_DVSN_CD", "02"), ("ORD_QTY", "1"), ("ORD_UNPR", "0"),
                            ("QTY_ALL_ORD_YN", "N"), ("EXCG_ID_DVSN_CD", "KRX"), ("CNDT_PRIC", ""))
    validate_request(request)


def test_kis_us_cancel_golden_no_borrow_or_idempotency_invention():
    order = _order("kis", market="nasd")
    request = kis.prepare_cancel(order, "123456", remaining_quantity=D("1"))
    assert request.path == "/uapi/overseas-stock/v1/trading/order-rvsecncl"
    assert request.headers == (("tr_id", "TTTT1004U"),)
    assert request.body == (("OVRS_EXCG_CD", "NASD"), ("PDNO", "AAPL"), ("ORGN_ODNO", "123456"),
                            ("RVSE_CNCL_DVSN_CD", "02"), ("ORD_QTY", "1"), ("OVRS_ORD_UNPR", "0"),
                            ("MGCO_APTM_ODNO", ""), ("ORD_SVR_DVSN_CD", "0"))
    validate_request(request)


def test_kis_status_dates_explicit_and_us_number_filter_forbidden():
    krx = _order("kis")
    _refused(lambda: kis.prepare_status(krx, "123456", broker_org_id="00123"))
    for invalid in ("20260230", "2026-10-31", True, ""):
        _refused(lambda: kis.prepare_status(krx, "123456", broker_org_id="00123", order_date=invalid))
    request = kis.prepare_status(krx, "123456", broker_org_id="00123", order_date="20261031")
    assert request.headers == (("tr_id", "TTTC0081R"),)
    assert dict(request.params)["ODNO"] == "123456" and dict(request.params)["INQR_DVSN_3"] == "01"
    us = kis.prepare_status(_order("kis", market="nasd"), "123456", order_date="20261030")
    assert us.headers == (("tr_id", "TTTS3035R"),)
    assert dict(us.params)["ODNO"] == dict(us.params)["ORD_DT"] == dict(us.params)["ORD_GNO_BRNO"] == ""
    assert dict(us.params)["ORD_STRT_DT"] == "20261030"
    validate_request(request)
    validate_request(us)


def test_kis_ack_broker_reference_preserved_cancel_not_terminal():
    order = _order("kis")
    ack = {"rt_cd": "0", "output": {"ODNO": "123456", "KRX_FWDG_ORD_ORGNO": "00123", "ORD_TMD": "100001"}}
    result = kis.parse(ack, kis.prepare(order, _rules(order)))
    assert result.status == "accepted" and result.venue_order_id == "123456"
    assert dict(result.metadata)["broker_org_id"] == "00123" and result.filled_quantity is None
    cancel = kis.prepare_cancel(order, "123456", broker_org_id="00123", remaining_quantity=D("1"))
    ack["output"]["ODNO"] = "123457"
    result = kis.parse(ack, cancel)
    assert result.status == "accepted" and result.venue_order_id == "123456"
    assert dict(result.metadata)["cancel_order_id"] == "123457"


def test_kis_missing_org_malformed_success_and_errors_unknown_sanitized():
    order = _order("kis")
    request = kis.prepare(order, _rules(order))
    for response in ({"rt_cd": "0", "output": {"ODNO": "123456"}},
                     {"rt_cd": "1", "msg1": "fixture-secret"}, {}, [],
                     {"rt_cd": "0", "output": {"ODNO": "123456", "KRX_FWDG_ORD_ORGNO": "00123", "PDNO": "bad"}}):
        result = kis.parse(response, request)
        assert result.status == "unknown" and "fixture-secret" not in repr(result)


def test_kis_krx_partial_filled_canceled_partial_and_fee_absence():
    request = kis.prepare_status(_order("kis"), "123456", broker_org_id="00123", order_date="20261031")
    assert kis.parse(_kis_krx_status(), request).status == "open"
    result = kis.parse(_kis_krx_status(tot_ccld_qty="1", rmn_qty="1", avg_prvs="99"), request)
    assert result.status == "partial" and result.filled_quantity == D("1") and result.fee is None
    result = kis.parse(_kis_krx_status(tot_ccld_qty="1", rmn_qty="0", cnc_cfrm_qty="1", cncl_yn="Y", avg_prvs="99"), request)
    assert result.status == "canceled" and result.filled_quantity == D("1")
    result = kis.parse(_kis_krx_status(tot_ccld_qty="2", rmn_qty="0", avg_prvs="99"), request)
    assert result.status == "filled" and result.filled_quantity == D("2")


def test_kis_incomplete_pages_duplicate_matches_and_missing_match_are_unknown():
    request = kis.prepare_status(_order("kis"), "123456", broker_org_id="00123", order_date="20261031")
    for marker in ("M", "F", None, "unexpected"):
        response = _kis_krx_status()
        response["_tr_cont"] = marker
        assert kis.parse(response, request).status == "unknown"
    response = _kis_krx_status()
    response["output1"] *= 2
    assert kis.parse(response, request).status == "unknown"
    response["output1"] = []
    assert kis.parse(response, request).status == "unknown"


def test_kis_status_all_order_fields_must_match_and_quantities_consistent():
    request = kis.prepare_status(_order("kis"), "123456", broker_org_id="00123", order_date="20261031")
    for key, value in (("odno", "wrong"), ("ord_dt", "20261030"), ("pdno", "000000"), ("sll_buy_dvsn_cd", "01"),
                       ("ord_qty", "3"), ("ord_unpr", "101"), ("ord_dvsn_cd", "01"), ("excg_id_dvsn_cd", "NXT"),
                       ("rmn_qty", "3"), ("rjct_qty", "1"), ("cncl_yn", "unknown"), ("tot_ccld_qty", True)):
        assert kis.parse(_kis_krx_status(**{key: value}), request).status == "unknown"
    assert kis.parse(_kis_krx_status(tot_ccld_qty="0.5", rmn_qty="1.5", avg_prvs="99"), request).status == "unknown"
    assert kis.parse(_kis_krx_status(ord_gno_brno="99999"), request).status == "unknown"


def test_kis_us_status_exact_local_match_and_unverified_cancel_retained():
    order = _order("kis", market="nasd")
    request = kis.prepare_status(order, "123456", order_date="20261030")
    response = _kis_us_status()
    other = deepcopy(response["output"][0])
    other["odno"] = "other"
    response["output"].insert(0, other)
    assert kis.parse(response, request).status == "open"
    result = kis.parse(_kis_us_status(ft_ccld_qty="1", nccs_qty="1", ft_ccld_unpr3="99"), request)
    assert result.status == "partial" and result.filled_quantity == D("1")
    result = kis.parse(_kis_us_status(ft_ccld_qty="2", nccs_qty="0", ft_ccld_unpr3="99"), request)
    assert result.status == "filled" and result.fee is None
    result = kis.parse(_kis_us_status(ft_ccld_qty="1", nccs_qty="0", ft_ccld_unpr3="99", prcs_stat_name="취소완료"), request)
    assert result.status == "unknown" and result.code == "unverified_cancel_state"
    assert kis.parse(_kis_us_status(ovrs_excg_cd="NYSE"), request).status == "unknown"


def test_adapter_result_rejects_arbitrary_codes_mutable_metadata_and_bad_numbers():
    _refused(lambda: AdapterResult(status="success", code="ok"))
    _refused(lambda: AdapterResult(status="unknown", code="fixture-secret raw response"))
    _refused(lambda: AdapterResult(status="unknown", code="bad", metadata=[]))
    _refused(lambda: AdapterResult(status="open", code="ok", filled_quantity=True))
    _refused(lambda: AdapterResult(status="open", code="ok", fee=D("NaN")))
