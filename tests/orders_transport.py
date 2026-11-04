"""Trading transport checks with only synthetic providers and in-memory sends.

Golden authentication constants are derived from explicit protocol bytes, not
from the implementation's signing helpers. No test reads environment credentials.
"""
from __future__ import annotations

import base64
import contextlib
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

from execution_control.capability import _issue
from execution_control.model import InstrumentRules, Order, decimal_text
from execution_orders import kis, okx, transport as T, upbit
from tests import control_fixtures as F

NOW = datetime(2026, 10, 31, 1, 2, 3, 456789, tzinfo=timezone.utc)
D = Decimal


def _order(venue="upbit", market=None):
    market = market or ("krx" if venue == "kis" else "spot")
    symbol = "KRW-BTC" if venue == "upbit" else "BTC-USDT" if venue == "okx" else "005930" if market == "krx" else "AAPL"
    return Order(client_id="order01", account_scope="tradingA", venue=venue, market=market, symbol=symbol,
                 side="buy", quantity=D("1"), limit_price=D("2500") if venue == "upbit" else D("25"),
                 quote_krw=D("1") if venue == "upbit" or market == "krx" else D("1400"),
                 time_in_force="day" if venue == "kis" else "gtc")


def _rules(order):
    return InstrumentRules(venue=order.venue, market=order.market, symbol=order.symbol,
                           lot_size=D("1"), tick_size=D("1"), min_quantity=D("1"), min_notional_krw=D("1"),
                           fee_fraction=D("0.001"), asof=NOW, source_digest="a" * 64)


def _request(venue="upbit", market=None):
    order = _order(venue, market)
    return {"upbit": upbit, "okx": okx, "kis": kis}[venue].prepare(order, _rules(order))


def _provider(venue, scope):
    return T.Credentials(venue=venue, account_scope=scope, access_key="test-access", secret_key="test-secret",
                         passphrase="test-passphrase", bearer_token="test-token", account_number="12345678",
                         account_product="01")


@contextlib.contextmanager
def _seam(*, response=None, status=200, headers=None, error=None):
    calls = []
    raw = response if type(response) is bytes else json.dumps(response or {}).encode("utf-8")

    def send(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if error is not None:
            raise error
        return status, {} if headers is None else headers, raw

    old = T._send
    T._send = send
    try:
        yield calls
    finally:
        T._send = old


def _refused(call):
    try:
        call()
    except ValueError as exc:
        assert "test-secret" not in str(exc) and "12345678" not in str(exc)
    else:
        raise AssertionError("request was not refused")


def _jwt_parts(token):
    parts = token.split(".")
    return [json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))) for part in parts[:2]], parts[2]


def test_upbit_authentication_uses_ordered_body_query_and_independent_golden_signature():
    request = _request()
    old = T.uuid.uuid4
    T.uuid.uuid4 = lambda: "00000000-0000-0000-0000-000000000001"
    try:
        with _seam() as calls:
            T.dispatch(request, _issue(request), credentials=_provider, now=NOW)
    finally:
        T.uuid.uuid4 = old
    assert len(calls) == 1
    method, url, wire = calls[0]
    assert method == "POST" and url == "https://api.upbit.com/v1/orders"
    assert wire["body"] == (b'{"market":"KRW-BTC","side":"bid","volume":"1","price":"2500",'
                            b'"ord_type":"limit","identifier":"order01"}')
    parts, signature = _jwt_parts(wire["headers"]["Authorization"].removeprefix("Bearer "))
    assert parts[0] == {"alg": "HS512", "typ": "JWT"}
    assert parts[1] == {"access_key": "test-access", "nonce": "00000000-0000-0000-0000-000000000001",
                        "query_hash": "ded70c24c463bcf2998dffe3abb7a6dbcf8ed32d77314625b596ad921db9cc15bf859cc74ae20dee765ee8256c2098a79b9546319e02e63eb3db8cb279ad4d9e",
                        "query_hash_alg": "SHA512"}
    assert signature == "hW44S1mQ3Z2-BKigekd8Bq_JMV3NMatD0-G_uamQnP6c6XbqZEasE0tgjnmPjT-a9TjcrVn7LLeyVaOlHsxgLg"


def test_upbit_nonce_is_fresh_and_decoded_query_keeps_order_unicode_and_escaping():
    credential = _provider("upbit", "tradingA")
    pairs = (("note", "한글 +&"), ("name", "A/B"))
    first, _ = _jwt_parts(T._upbit_jwt(credential, pairs))
    second, _ = _jwt_parts(T._upbit_jwt(credential, pairs))
    reversed_parts, _ = _jwt_parts(T._upbit_jwt(credential, tuple(reversed(pairs))))
    assert first[1]["nonce"] != second[1]["nonce"]
    assert first[1]["query_hash"] == hashlib.sha512("note=한글++&&name=A/B".encode()).hexdigest()
    assert reversed_parts[1]["query_hash"] != first[1]["query_hash"]


def test_okx_authentication_binds_exact_body_and_get_query_golden_vectors():
    order = _order("okx")
    requests = [(_request("okx"), "tGs97Pbe3JjR9Uzl85rvuHfwP/gIgn05r9twJ+xiMEU="),
                (okx.prepare_status(order, "123"), "td0B0XB4ndAlWCaJF6zfycyTFoShHMA5p988HhinJgw=")]
    for request, wanted in requests:
        with _seam() as calls:
            T.dispatch(request, _issue(request), credentials=_provider, now=NOW)
        assert len(calls) == 1
        wire = calls[0][2]
        assert wire["headers"]["OK-ACCESS-SIGN"] == wanted
        assert wire["headers"]["OK-ACCESS-TIMESTAMP"] == "2026-10-31T01:02:03.456Z"
        assert wire["headers"]["OK-ACCESS-PASSPHRASE"] == "test-passphrase"
        if request.method == "GET":
            assert calls[0][1].endswith("?instId=BTC-USDT&ordId=123") and wire["body"] == b""
        else:
            assert wire["body"] == (b'{"instId":"BTC-USDT","tdMode":"cash","side":"buy","ordType":"limit",'
                                    b'"sz":"1","px":"25","clOrdId":"order01"}')


def test_kis_scope_provider_injects_account_only_after_capability_validation():
    events = []

    def provider(venue, scope):
        events.append((venue, scope))
        return _provider(venue, scope)

    for market, wanted_tr in (("krx", "TTTC0012U"), ("nasd", "TTTT1002U")):
        request = _request("kis", market)
        assert "CANO" not in dict(request.body) and "ACNT_PRDT_CD" not in dict(request.body)
        assert "12345678" not in repr(request)
        with _seam() as calls:
            _refused(lambda: T.dispatch(request, object(), credentials=provider, now=NOW))
            assert not calls
            T.dispatch(request, _issue(request), credentials=provider, now=NOW)
        body = json.loads(calls[0][2]["body"])
        assert body["CANO"] == "12345678" and body["ACNT_PRDT_CD"] == "01"
        headers = calls[0][2]["headers"]
        assert headers["tr_id"] == wanted_tr and headers["authorization"] == "Bearer test-token"
        assert headers["appkey"] == "test-access" and headers["appsecret"] == "test-secret"
        assert headers["custtype"] == "P"
    assert events == [("kis", "tradingA"), ("kis", "tradingA")]


def test_capability_is_one_use_and_bound_to_exact_request_operation_and_scope():
    request = _request()
    token = _issue(request)
    observed = []

    def provider(venue, scope):
        observed.append(1)
        return _provider(venue, scope)

    with _seam() as calls:
        T.dispatch(request, token, credentials=provider, now=NOW)
        _refused(lambda: T.dispatch(request, token, credentials=provider, now=NOW))
        assert len(calls) == 1 and len(observed) == 1
    for other in (upbit.prepare_status(_order(), "broker01"),
                  upbit.prepare(replace(_order(), account_scope="tradingB"), _rules(_order()))):
        token = _issue(request)
        with _seam() as calls:
            _refused(lambda: T.dispatch(other, token, credentials=provider, now=NOW))
            _refused(lambda: T.dispatch(request, token, credentials=provider, now=NOW))
            assert not calls and len(observed) == 1
    token = _issue(request)
    object.__setattr__(token, "request_digest", "b" * 64)
    with _seam() as calls:
        _refused(lambda: T.dispatch(request, token, credentials=provider, now=NOW))
        assert not calls and len(observed) == 1


def test_arbitrary_route_extra_fields_and_tr_id_tampering_refuse_before_provider():
    for request, changes in (( _request(), {"path": "https://elsewhere.invalid/v1/orders"}),
                             (_request(), {"path": "/v1/withdraws/coin"}),
                             (_request(), {"method": "PUT"}),
                             (_request(), {"body": _request().body + (("leverage", "10"),)}),
                             (_request("kis"), {"headers": (("tr_id", "TTTC0011U"),)})):
        changed = replace(request, **changes)
        observed = []
        with _seam() as calls:
            _refused(lambda: T.dispatch(changed, object(), credentials=lambda *args: observed.append(1), now=NOW))
        assert not observed and not calls


def test_wrong_provider_scope_and_malformed_credentials_never_send_or_expose_values():
    request = _request()
    candidates = [None, {"secret": "test-secret"}, replace(_provider("upbit", "tradingA"), account_scope="tradingB"),
                  replace(_provider("upbit", "tradingA"), venue="okx"),
                  replace(_provider("upbit", "tradingA"), access_key="bad\nheader"),
                  replace(_provider("upbit", "tradingA"), secret_key=4)]
    for value in candidates:
        with _seam() as calls:
            result = T.dispatch(request, _issue(request), credentials=lambda *args: value, now=NOW)
        assert result.status == "unknown" and result.code == "credential_scope_or_format" and not calls
        assert "test-secret" not in repr(result)
    value = _provider("kis", "tradingA")
    assert repr(value) == str(value) == "Credentials(<redacted>)"


def test_provider_failure_and_provider_time_mutation_are_sanitized_and_not_sent():
    request = _request()

    def failed(*args):
        raise RuntimeError("test-secret account 12345678")

    with _seam() as calls:
        result = T.dispatch(request, _issue(request), credentials=failed, now=NOW)
    assert result.code == "credentials_unavailable" and not calls and "test-secret" not in repr(result)

    def mutate(venue, scope):
        object.__setattr__(request, "body", request.body + (("unexpected", "value"),))
        return _provider(venue, scope)

    with _seam() as calls:
        result = T.dispatch(request, _issue(request), credentials=mutate, now=NOW)
    assert result.status == "unknown" and result.code == "request_changed" and not calls


def test_timeout_http_failure_and_malformed_response_stay_unknown_without_retry():
    request = _request("okx")
    for options in ({"error": TimeoutError("test-secret")}, {"status": 500}, {"status": 302},
                    {"response": b"not JSON test-secret"}, {"response": b"[]"},
                    {"response": b'{"code":"0","code":"51008","data":[]}'},
                    {"response": b'{"code":"0","data":[],"bad":NaN}'},
                    {"response": b"x" * (T.MAX_RESPONSE_BYTES + 1)},
                    {"response": {"code": "50004", "data": []}}):
        token = _issue(request)
        with _seam(**options) as calls:
            result = T.dispatch(request, token, credentials=_provider, now=NOW)
            _refused(lambda: T.dispatch(request, token, credentials=_provider, now=NOW))
        assert result.status == "unknown" and len(calls) == 1
        assert "test-secret" not in repr(result)


def test_okx_cancel_acknowledgment_is_not_terminal_cancellation():
    request = okx.prepare_cancel(_order("okx"), "123")
    response = {"code": "0", "data": [{"ordId": "123", "clOrdId": "order01", "sCode": "0"}]}
    with _seam(response=response) as calls:
        result = T.dispatch(request, _issue(request), credentials=_provider, now=NOW)
    assert result.status == "accepted" and result.venue_order_id == "123" and len(calls) == 1
    assert calls[0][1] == "https://www.okx.com/api/v5/trade/cancel-order"


def test_kis_status_header_completeness_cannot_be_forged_by_the_response_body():
    request = kis.prepare_status(_order("kis"), "456", order_date="20261031", broker_org_id="123")
    response = {"rt_cd": "0", "_tr_cont": "", "output1": [{
        "odno": "456", "pdno": "005930", "ord_dt": "20261031", "sll_buy_dvsn_cd": "02",
        "ord_qty": "1", "ord_unpr": "25", "excg_id_dvsn_cd": "KRX", "ord_dvsn_cd": "00",
        "tot_ccld_qty": "0", "rmn_qty": "1", "cnc_cfrm_qty": "0", "rjct_qty": "0", "cncl_yn": "N"}]}
    for headers, wanted in (({}, "unknown"), ({"Tr_Cont": "M"}, "unknown"),
                            ({"tr_cont": "", "Tr_Cont": "M"}, "unknown"), ({"Tr_Cont": ""}, "open")):
        with _seam(response=response, headers=headers) as calls:
            result = T.dispatch(request, _issue(request), credentials=_provider, now=NOW)
        assert result.status == wanted and len(calls) == 1
        assert calls[0][0] == "GET" and calls[0][2]["body"] == b""
        query = parse_qs(urlsplit(calls[0][1]).query)
        assert query["CANO"] == ["12345678"] and query["ACNT_PRDT_CD"] == ["01"]


def test_kis_optional_account_echo_must_match_the_scoped_credentials():
    request = _request("kis")
    base = {"rt_cd": "0", "output": {"ODNO": "456", "KRX_FWDG_ORD_ORGNO": "123"}}
    for field, bad in (("CANO", "87654321"), ("cano", "87654321"),
                       ("ACNT_PRDT_CD", "02"), ("acnt_prdt_cd", 1)):
        response = {**base, "output": {**base["output"], field: bad}}
        with _seam(response=response) as calls:
            result = T.dispatch(request, _issue(request), credentials=_provider, now=NOW)
        assert len(calls) == 1 and result.status == "unknown" and result.code == "account_identity_mismatch"
        assert "87654321" not in repr(result) and "12345678" not in repr(result)
    for response in (base, {**base, "output": {**base["output"], "CANO": "12345678", "ACNT_PRDT_CD": "01"}}):
        with _seam(response=response):
            result = T.dispatch(request, _issue(request), credentials=_provider, now=NOW)
        assert result.status == "accepted"


def test_signed_controller_dispatches_through_authenticated_adapter_exactly_once():
    # This exercises the actual controller adapter protocol, including now=,
    # rather than calling transport directly and hiding a wrapper mismatch.
    from tests.control_session import signed_control

    with signed_control() as env:
        provider_calls = []

        def provider(venue, scope):
            provider_calls.append((venue, scope))
            return _provider(venue, scope)

        env.controller.adapters["upbit"] = T.AuthenticatedTransport(credentials=provider)
        order = env.order
        response = {"uuid": "broker01", "identifier": order.client_id, "market": order.symbol,
                    "side": "bid" if order.side == "buy" else "ask", "ord_type": "limit",
                    "price": decimal_text(order.limit_price), "volume": decimal_text(order.quantity),
                    "executed_volume": "0", "remaining_volume": decimal_text(order.quantity), "state": "wait"}
        with _seam(response=response) as calls:
            reserved = env.controller.reserve(order, env.rules, session_id=env.session_id, now=env.now)
            assert reserved.status == "RESERVED" and not calls and not provider_calls
            result = env.controller.dispatch(order.client_id, now=env.now)
            assert result.status == "ACKNOWLEDGED" and result.venue_order_id == "broker01"
            assert env.controller.dispatch(order.client_id, now=env.now) == result
            assert len(calls) == 1 and calls[0][0] == "POST"
            assert provider_calls == [(order.venue, order.account_scope)]


def test_one_send_seam_disables_environment_redirects_and_keeps_tls_verification():
    events = []

    class Session:
        trust_env = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append("closed")

        def request(self, method, url, **kwargs):
            assert self.trust_env is False
            events.append((method, url, kwargs))
            return SimpleNamespace(status_code=200, headers={}, content=b"{}")

    old = T.requests
    T.requests = SimpleNamespace(Session=Session)
    try:
        assert callable(F.REAL_SEND) and T._send is F._refuse
        assert F.REAL_SEND("POST", "https://api.upbit.com/v1/orders", headers={}, body=b"{}", timeout=10.0) == (200, {}, b"{}")
    finally:
        T.requests = old
    assert len(events) == 2 and events[1] == "closed"
    options = events[0][2]
    assert options == {"headers": {}, "data": b"{}", "timeout": 10.0, "allow_redirects": False, "proxies": {}, "verify": True}


def test_managed_order_send_uses_explicit_proxy_ca_once_and_does_not_fallback():
    from execution_network.route import ManagedRoute, managed_route
    route = ManagedRoute(proxy_url="http://proxy:8080", ca_bundle="/etc/ssl/certs/ca-certificates.crt",
                         permitted_hosts=frozenset({"api.upbit.com"}))
    events = []

    class Session:
        trust_env = True

        def __enter__(self):
            events.append("opened")
            return self

        def __exit__(self, *args):
            events.append("closed")

        def request(self, method, url, **kwargs):
            assert self.trust_env is False
            events.append((method, url, kwargs))
            raise OSError("synthetic proxy failure")

    old = T.requests
    T.requests = SimpleNamespace(Session=Session)
    try:
        with managed_route(route):
            try:
                F.REAL_SEND("POST", "https://api.upbit.com/v1/orders", headers={}, body=b"{}", timeout=10.0)
            except OSError:
                pass
            else:
                raise AssertionError("proxy failure disappeared")
            try:
                F.REAL_SEND("POST", "https://www.okx.com/api/v5/trade/order", headers={}, body=b"{}", timeout=10.0)
            except ValueError as exc:
                assert str(exc) == "MANAGED_DESTINATION_BLOCKED"
            else:
                raise AssertionError("blocked destination opened a session")
    finally:
        T.requests = old
    assert len(events) == 3 and events[0] == "opened" and events[-1] == "closed", events
    assert events[1][2] == {"headers": {}, "data": b"{}", "timeout": 10.0, "allow_redirects": False,
                            "proxies": {"http": "http://proxy:8080", "https": "http://proxy:8080"},
                            "verify": "/etc/ssl/certs/ca-certificates.crt"}


def test_dispatch_requires_aware_explicit_clock_before_any_provider_or_send():
    request = _request()
    for now in (None, datetime(2026, 10, 31), "2026-10-31"):
        observed = []
        with _seam() as calls:
            _refused(lambda: T.dispatch(request, object(), credentials=lambda *args: observed.append(1), now=now))
        assert not calls and not observed
