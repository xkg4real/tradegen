"""execution/transport.py (E1 Tasks 2 and 3; spec 5 "The choke point", the three endpoint tables, Upbit and OKX
signing, KIS "Token"; contract sections 3.2, 6 and 7; E3, E11, E12, E13, E15, E37, E39, E1R2-11).

Task 2's tests check the refusals with keys.read and transport._send both replaced by a function that raises
AssertionError, so a refusal provably comes before any key is read and any send; `_t2_passes` treats a key read and
a send attempt alike as "got past every check". Task 3's tests (prefixed `_t3_`) send through
tests.execution_fixtures.serve, which records every call and answers from synthetic bodies shaped like the venue
docs (never a live answer); the probe at the end sends with no serve() and is refused by the suite's stub. Every
clock is transport._clock patched to a fixed or scripted moment, and every file is in the suite's temp home.
"""
from __future__ import annotations

import ast
import base64
import contextlib
import dataclasses
import hashlib
import hmac
import json
import math
import os
import re
import time
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

from execution import keys, kis_inquiry, upbit_inquiry
from execution import transport as T
from tests import execution_fixtures as F

ROOT = Path(__file__).resolve().parents[1]
_T2_BALANCE = "/uapi/domestic-stock/v1/trading/inquire-balance"
_T2_CCNL = "/uapi/overseas-stock/v1/trading/inquire-ccnl"
_T2_ORDER = "/uapi/domestic-stock/v1/trading/order-cash"
_T2_MOCK = "https://openapivts.koreainvestment.com:29443"
_T2_SKEW = "okx: the PC clock offset from OKX time is unknown or above 25 s; OKX requests not sent"


class _T2Reached(Exception):
    """Raised by the seams `_t2_passes` installs: request got past every check."""


@contextlib.contextmanager
def _t2_seams(read, send):
    """keys.read and transport._send replaced for one block, restored on exit."""
    keep = keys.read, T._send
    keys.read, T._send = read, send
    try:
        yield
    finally:
        keys.read, T._send = keep


def _t2_boom(*_a, **_k):
    raise AssertionError("a key was read or a send was made before the checks finished")


def _t2_reached(*_a, **_k):
    raise _T2Reached


def _t2_refused(venue, method, path, params=None, *, tr_id=None) -> str:
    """The reason of the InquiryRefused that request(...) raises while keys.read and _send both fail the test."""
    with _t2_seams(_t2_boom, _t2_boom):
        try:
            T.request(venue, method, path, params, tr_id=tr_id)
        except T.InquiryRefused as exc:
            assert exc.args == (exc.reason,), exc.args
            return exc.reason
        except T.InquiryError:
            pass
    raise AssertionError(f"not refused: {venue} {method} {path} tr_id={tr_id!r}")


def _t2_passes(venue, method, path, params=None, *, tr_id=None) -> bool:
    """True when request(...) gets past every check: Task 2 then fails closed with InquiryError; from Task 3 on it
    reads a key or tries to send, which the seams installed here turn into _T2Reached (no stray is recorded)."""
    with _t2_seams(_t2_reached, _t2_reached):
        try:
            T.request(venue, method, path, params, tr_id=tr_id)
        except T.InquiryRefused:
            return False
        except (T.InquiryError, _T2Reached):
            return True
    return True


@contextlib.contextmanager
def _t2_patched(module, name, value):
    """module.name = value for one block, restored on exit."""
    keep = getattr(module, name)
    setattr(module, name, value)
    try:
        yield
    finally:
        setattr(module, name, keep)


def test_constants_errors_and_answer_have_the_contract_shape():
    """Contract section 6: the constants Task 3 sends with, the three errors, the frozen keyword-only Answer whose
    repr never shows the body, and the module defaults the suite replaces, read from the source because isolated()
    has replaced them: _clock raises until poll.main binds one, _sleep is time.sleep, no token gap, no OKX offset,
    no bad token."""
    assert (T.TIMEOUT_S, T.RETRY_AFTER_S, T.PACE_S, T.OKX_SKEW_LIMIT_S) == (10.0, 2.0, 0.2, 25.0)
    assert (T.TOKEN_REUSE_MARGIN_S, T.TOKEN_MIN_GAP_S, T.TOKEN_REISSUE_BLOCK_S) == (120.0, 70.0, 21600.0)
    assert T.KIS_TOKEN_CODES == frozenset({"EGW00121", "EGW00122", "EGW00123"})
    assert type(T.AUTH_CODES) is types.MappingProxyType and dict(T.AUTH_CODES) == {
        "kis": frozenset({"EGW00103", "EGW00105", "EGW00205", "EGW00206", "EGW00304"}),
        "upbit": frozenset({"invalid_query_payload", "jwt_verification", "expired_access_key", "nonce_used",
                            "no_authorization_ip", "no_authorization_token", "out_of_scope"}),
        "okx": frozenset({"50030", "50035", "50100", "50101", "50103", "50104", "50105", "50106", "50107", "50110",
                          "50111", "50112", "50113", "50114", "50119", "50120", "50121", "50123"})}
    assert issubclass(T.AuthError, T.InquiryError) and not issubclass(T.InquiryRefused, T.InquiryError)
    exc = T.InquiryRefused("upbit: GET /x is not on the E1 allowlist")
    assert exc.reason == str(exc) == "upbit: GET /x is not on the E1 allowlist"
    answer = T.Answer(body={"access_token": "test-token-1"}, server_utc=None, received_utc=F.NOW, sha256="0" * 64)
    assert "test-token-1" not in repr(answer) and "body" not in repr(answer), repr(answer)
    try:
        answer.sha256 = "1" * 64
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Answer is not frozen")
    try:
        T.Answer({"a": 1}, None, F.NOW, "0" * 64)
    except TypeError:
        pass
    else:
        raise AssertionError("Answer takes positional arguments")
    tree = ast.parse((ROOT / "execution" / "transport.py").read_text(encoding="utf-8"))
    defaults = {ast.unparse(n.targets[0] if isinstance(n, ast.Assign) else n.target): ast.unparse(n.value)
                for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None}
    assert [defaults[k] for k in ("_sleep", "_next_issue_at", "_okx_offset_s", "_bad_tokens")] == [
        "time.sleep", "None", "None", "set()"], defaults
    clock = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_clock"]
    assert len(clock) == 1 and ast.unparse(clock[0].body[-1]) == (
        "raise RuntimeError('transport: no clock; poll.main sets one')"), ast.dump(clock[0])


def test_every_refusal_comes_before_any_key_is_read():
    """Spec 9 "Transport": an unknown venue, a pair off the allowlist (order paths, a POST to an inquiry path, the
    mock host, a lowercase method), the token POST with parameters, a KIS TR that is an order TR, a mock TR, pinned
    to another path or missing, a TR id outside KIS, and a parameter that is not plain, each refused with its exact
    reason while reading a key or sending would fail the test."""
    not_listed = "is not on the E1 allowlist"
    cases = [
        (("binance", "GET", "/api/v3/account"), "unknown venue 'binance'"),
        (("KIS", "GET", _T2_BALANCE, None, "TTTC8434R"), "unknown venue 'KIS'"),
        (("kis", "POST", _T2_ORDER, None, "TTTC0802U"), f"kis: POST {_T2_ORDER} {not_listed}"),
        (("kis", "GET", _T2_ORDER, None, "TTTC0802U"), f"kis: GET {_T2_ORDER} {not_listed}"),
        (("kis", "POST", _T2_BALANCE, None, "TTTC8434R"), f"kis: POST {_T2_BALANCE} {not_listed}"),
        (("kis", "GET", "/oauth2/tokenP"), f"kis: GET /oauth2/tokenP {not_listed}"),
        (("kis", "POST", "/oauth2/tokenP", [("grant_type", "client_credentials")]),
         "kis: the token POST takes no parameters"),
        (("kis", "POST", "/oauth2/tokenP", []), "kis: the token POST takes no parameters"),
        (("kis", "POST", "/oauth2/tokenP", None, "TTTC8434R"), "kis: a TR id belongs only to a KIS inquiry"),
        (("kis", "GET", _T2_BALANCE, None, "TTTC0802U"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'TTTC0802U'"),
        (("kis", "GET", _T2_BALANCE, None, "VTTC8434R"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'VTTC8434R'"),
        (("kis", "GET", _T2_BALANCE, None, "TTTC0084R"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'TTTC0084R'"),
        (("kis", "GET", _T2_BALANCE, None, "tttc8434r"),
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'tttc8434r'"),
        (("kis", "GET", _T2_BALANCE, None, "tttc8434R"),                       # no case folding before the lookup
         f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'tttc8434R'"),
        (("kis", "GET", _T2_BALANCE), f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got None"),
        (("kis", "GET", _T2_MOCK + _T2_BALANCE, None, "TTTC8434R"), f"kis: GET {_T2_MOCK}{_T2_BALANCE} {not_listed}"),
        (("kis", "get", _T2_BALANCE, None, "TTTC8434R"), f"kis: get {_T2_BALANCE} {not_listed}"),
        (("upbit", "POST", "/v1/orders"), f"upbit: POST /v1/orders {not_listed}"),
        (("upbit", "DELETE", "/v1/orders/open"), f"upbit: DELETE /v1/orders/open {not_listed}"),
        (("upbit", "GET", "/v1/orders"), f"upbit: GET /v1/orders {not_listed}"),
        (("upbit", "GET", "/v1/order"), f"upbit: GET /v1/order {not_listed}"),
        (("upbit", "GET", "/v1/deposits/generate_coin_address"),
         f"upbit: GET /v1/deposits/generate_coin_address {not_listed}"),
        (("upbit", "GET", "/v1/withdraws/coin"), f"upbit: GET /v1/withdraws/coin {not_listed}"),
        (("upbit", "get", "/v1/accounts"), f"upbit: get /v1/accounts {not_listed}"),
        (("upbit", "GET", "/v1/accounts", None, "TTTC8434R"), "upbit: a TR id belongs only to a KIS inquiry"),
        (("okx", "GET", "/api/v5/trade/order"), f"okx: GET /api/v5/trade/order {not_listed}"),
        (("okx", "POST", "/api/v5/trade/order"), f"okx: POST /api/v5/trade/order {not_listed}"),
        (("okx", "GET", "/api/v5/asset/deposit-address"), f"okx: GET /api/v5/asset/deposit-address {not_listed}"),
        (("okx", "GET", "/api/v5/public/time", None, "TTTC8434R"), "okx: a TR id belongs only to a KIS inquiry"),
        (("upbit", "GET", "/v1/withdraws", [("limit ", "100")]), "upbit: parameter 'limit ' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit=1&x", "100")]), "upbit: parameter 'limit=1&x' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("ord-type", "1")]), "upbit: parameter 'ord-type' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("a.b", "1")]), "upbit: parameter 'a.b' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("a%41", "1")]), "upbit: parameter 'a%41' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit", 100)]), "upbit: parameter 'limit' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit",)]), "upbit: parameters must be (key, value) pairs"),
        (("upbit", "GET", "/v1/withdraws", {"limit": "100"}), "upbit: parameters must be (key, value) pairs"),
        (("upbit", "GET", "/v1/withdraws", "limit=100"), "upbit: parameters must be (key, value) pairs"),
        (("kis", "GET", _T2_BALANCE, [["PDNO", "005930"]], "TTTC8434R"), "kis: parameters must be (key, value) pairs"),
        (("kis", "GET", _T2_BALANCE, [(12345678, "01")], "TTTC8434R"), "kis: parameters must be (key, value) pairs"),
        (("kis", "GET", _T2_BALANCE, [("PDNO", None)], "TTTC8434R"), "kis: parameter 'PDNO' is not plain"),
        (("upbit", "GET", "/v1/withdraws", [("limit", "1 0")]), "upbit: parameter 'limit' is not plain"),
        (("upbit", "GET", "/v1/orders/closed", [("states[]", "done&cancel")]),
         "upbit: parameter 'states[]' is not plain"),
        (("upbit", "GET", "/v1/deposits", [("limit", "100%")]), "upbit: parameter 'limit' is not plain"),
        (("okx", "GET", "/api/v5/asset/asset-valuation", [("ccy", "US DT")]), "okx: parameter 'ccy' is not plain"),
        (("okx", "GET", "/api/v5/account/config"), _T2_SKEW),
    ]
    for args, reason in cases:
        assert T._okx_offset_s is None
        got = _t2_refused(*args[:4], tr_id=args[4] if len(args) > 4 else None)
        assert got == reason, (args, got)


def test_a_signed_okx_request_needs_a_known_offset_within_25_s():
    """Step 6 (E3): no offset, 26 s either way or NaN refuse every signed OKX request before any key is read; 25 s
    passes; the two public paths need no offset."""
    for offset in (None, 26.0, -26.0, 25.001, math.inf, math.nan):
        with _t2_patched(T, "_okx_offset_s", offset):
            assert _t2_refused("okx", "GET", "/api/v5/account/balance") == _T2_SKEW, offset
            assert _t2_refused("okx", "GET", "/api/v5/trade/orders-algo-pending",
                               [("ordType", "conditional")]) == _T2_SKEW, offset
            assert _t2_passes("okx", "GET", "/api/v5/public/time"), offset
            assert _t2_passes("okx", "GET", "/api/v5/market/ticker", [("instId", "BTC-USDT")]), offset
    for offset in (0.0, 25.0, -25.0):
        with _t2_patched(T, "_okx_offset_s", offset):
            assert _t2_passes("okx", "GET", "/api/v5/account/config"), offset
    assert T._okx_offset_s is None


def test_the_not_get_rule_holds_on_its_own():
    """Step 3 refuses a non-GET pair even when an edit puts it on a venue's allowlist."""
    with _t2_patched(upbit_inquiry, "ENDPOINTS", upbit_inquiry.ENDPOINTS | {("DELETE", "/v1/orders/open")}):
        assert _t2_refused("upbit", "DELETE", "/v1/orders/open") == "upbit: DELETE is not GET"
    with _t2_patched(kis_inquiry, "ENDPOINTS", kis_inquiry.ENDPOINTS | {("POST", _T2_BALANCE)}):
        assert _t2_refused("kis", "POST", _T2_BALANCE, tr_id="TTTC8434R") == "kis: POST is not GET"
    with _t2_patched(upbit_inquiry, "ENDPOINTS", upbit_inquiry.ENDPOINTS | {("POST", "/oauth2/tokenP")}):
        assert _t2_refused("upbit", "POST", "/oauth2/tokenP") == "upbit: POST is not GET"   # the exception is KIS's
    assert ("DELETE", "/v1/orders/open") not in upbit_inquiry.ENDPOINTS


def test_the_r_rule_holds_on_its_own():
    """Step 4 refuses a TR id that does not end in R even when an edit pins it to the path."""
    with _t2_patched(kis_inquiry, "TR_IDS", kis_inquiry.TR_IDS | {(_T2_BALANCE, "TTTC8434U")}):
        assert _t2_refused("kis", "GET", _T2_BALANCE, tr_id="TTTC8434U") == (
            f"kis: {_T2_BALANCE} needs its pinned TR id ending in R, got 'TTTC8434U'")
    assert all(tr.endswith("R") for _p, tr in kis_inquiry.TR_IDS)


def test_every_allowlisted_request_passes_the_checks():
    """The positive side: each pinned KIS pair, the token POST without parameters, every Upbit pair (signed values
    that quoting leaves alone), and every OKX pair once an offset is known. KIS values may need quoting."""
    for path, tr in sorted(kis_inquiry.TR_IDS):
        assert _t2_passes("kis", "GET", path, [("PDNO", "%"), ("INQR_DVSN", "01"), ("CTX_AREA_FK100", "")],
                          tr_id=tr), path
    assert _t2_passes("kis", "POST", "/oauth2/tokenP")
    for method, path in sorted(upbit_inquiry.ENDPOINTS):
        assert _t2_passes("upbit", method, path, [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")])
    assert _t2_passes("upbit", "GET", "/v1/ticker", [("markets", "KRW BTC")])       # public: quoted, not refused
    from execution import okx_inquiry
    with _t2_patched(T, "_okx_offset_s", 0.0):
        for method, path in sorted(okx_inquiry.ENDPOINTS):
            assert _t2_passes("okx", method, path, [("ordType", "move_order_stop"), ("ccy", "USDT")]), path


def test_the_query_is_built_once_and_sent_as_built():
    """E12: ordered pairs, array keys repeated and unencoded, values quoted with safe=",", nothing reordered."""
    assert T._query("upbit", "/v1/orders/open", [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")]) == (
        "states[]=wait&states[]=watch&limit=100")
    assert T._query("kis", _T2_CCNL, [("PDNO", "%"), ("ORD_DT", ""), ("X", "a/b c")]) == "PDNO=%25&ORD_DT=&X=a%2Fb%20c"
    assert T._query("upbit", "/v1/ticker", [("markets", "KRW-BTC,KRW-USDT")]) == "markets=KRW-BTC,KRW-USDT"
    assert T._query("upbit", "/v1/ticker", [("markets", "KRW BTC")]) == "markets=KRW%20BTC"
    assert T._query("okx", "/api/v5/trade/orders-algo-pending", [("ordType", "move_order_stop")]) == (
        "ordType=move_order_stop")
    assert T._query("okx", "/api/v5/account/balance", [("b", "2"), ("a", "1")]) == "b=2&a=1"
    assert T._query("kis", _T2_BALANCE, None) == "" and T._query("kis", _T2_BALANCE, []) == ""


def test_require_keys_names_the_first_missing_key_and_returns_nothing():
    for venue, first in (("kis", "KIS_APP_KEY"), ("upbit", "UPBIT_ACCESS_KEY"), ("okx", "OKX_API_KEY")):
        try:
            T.require_keys(venue)
        except T.KeyMissing as exc:
            assert exc.name == first, exc.name
        else:
            raise AssertionError(f"require_keys({venue!r}) passed with no keys")
    for venue, override, name in (("okx", {"OKX_API_SECRET": None}, "OKX_API_SECRET"),
                                  ("okx", {"OKX_API_PASSPHRASE": "<unset>"}, "OKX_API_PASSPHRASE"),
                                  ("upbit", {"UPBIT_SECRET_KEY": ""}, "UPBIT_SECRET_KEY"),
                                  ("kis", {"KIS_APP_SECRET": "  "}, "KIS_APP_SECRET")):
        with F.fake_keys(**override):
            try:
                T.require_keys(venue)
            except T.KeyMissing as exc:
                assert exc.name == name and "test-" not in str(exc), str(exc)
            else:
                raise AssertionError(f"require_keys({venue!r}) passed without {name}")
    seen = []
    real_read = keys.read
    with F.fake_keys():
        with _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)):
            assert [T.require_keys(v) for v in ("kis", "upbit", "okx")] == [None, None, None]
    assert seen == [("KIS_APP_KEY", "KIS_APP_SECRET"), ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"),
                    ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")], seen
    assert T.KeyMissing is keys.KeyMissing
    assert not any(name in os.environ for name in F.KEY_NAMES)                  # fake_keys restored every name


def test_send_opens_one_session_with_trust_env_off_and_no_redirects():
    """E1R2-11: the real _send runs against a recorder standing in for `requests` (no socket): one Session per
    call, trust_env already False when request runs, redirects off, the arguments passed through unchanged, the
    body read before the session closes, and (status, headers, content) returned."""
    calls = []

    class FakeResponse:
        status_code = 200
        headers = {"Date": F.DATE_HEADER}

        @property
        def content(self):
            calls.append(("content",))
            return b'{"ok": true}'

    class FakeSession:
        trust_env = True

        def __init__(self):
            calls.append(("session",))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            calls.append(("closed",))
            return False

        def request(self, method, url, **kw):
            calls.append(("request", method, url, self.trust_env, kw))
            return FakeResponse()

    assert F.REAL_SEND is not None and F.REAL_SEND is not T._send
    headers = {"Accept": "application/json"}
    body = {"grant_type": "client_credentials"}
    with _t2_patched(T, "requests", types.SimpleNamespace(Session=FakeSession, exceptions=requests.exceptions)):
        got = F.REAL_SEND("POST", "https://openapi.koreainvestment.com:9443/oauth2/tokenP", headers=headers,
                          params=None, json_body=body, timeout=10.0)
        got_get = F.REAL_SEND("GET", "https://api.upbit.com/v1/accounts", headers=headers, params=None,
                              json_body=None, timeout=10.0)
    assert T.requests is requests
    assert got == (200, {"Date": F.DATE_HEADER}, b'{"ok": true}') and got_get == got, (got, got_get)
    want = [("session",),
            ("request", "POST", "https://openapi.koreainvestment.com:9443/oauth2/tokenP", False,
             {"headers": headers, "params": None, "json": body, "timeout": 10.0, "allow_redirects": False}),
            ("content",), ("closed",),
            ("session",),
            ("request", "GET", "https://api.upbit.com/v1/accounts", False,
             {"headers": headers, "params": None, "json": None, "timeout": 10.0, "allow_redirects": False}),
            ("content",), ("closed",)]
    assert calls == want, calls


def test_trust_env_off_ignores_proxy_ca_bundle_and_netrc_settings():
    """What trust_env = False buys, checked offline on a real requests.Session (nothing is sent): with HTTPS_PROXY,
    REQUESTS_CA_BUNDLE, CURL_CA_BUNDLE and a NETRC file entry for the host in the environment, the settings a request
    would use hold no proxy, verify=True and no Authorization header; the same session with trust_env on picks
    each of them up (the control)."""
    home = Path(os.environ["TRADEGEN_HOME"])
    netrc = home / "netrc"
    netrc.write_text("machine api.upbit.com login someone password not-a-key\n", encoding="utf-8")
    url = "https://api.upbit.com/v1/accounts"
    names = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY",
             "no_proxy", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "NETRC")
    saved = {n: os.environ.get(n) for n in names}
    try:
        for n in names:
            os.environ.pop(n, None)
        os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9"
        os.environ["REQUESTS_CA_BUNDLE"] = os.environ["CURL_CA_BUNDLE"] = str(home / "no-such-bundle.pem")
        os.environ["NETRC"] = str(netrc)
        seen = {}
        for trust in (False, True):
            with requests.Session() as session:
                session.trust_env = trust
                settings = session.merge_environment_settings(url, {}, None, None, None)
                prepared = session.prepare_request(requests.Request("GET", url))
            seen[trust] = (settings["proxies"], settings["verify"], "Authorization" in prepared.headers)
    finally:
        for n, v in saved.items():
            if v is None:
                os.environ.pop(n, None)
            else:
                os.environ[n] = v
    assert seen[False] == ({}, True, False), seen
    proxies, verify, auth = seen[True]
    assert (proxies.get("https"), verify, auth) == ("http://127.0.0.1:9", str(home / "no-such-bundle.pem"), True), seen


def test_unpatched_send_is_refused_under_the_suite():
    """The probe of spec 9: under the suite, transport._send itself (not patched by this test) refuses and records
    one stray. The test asserts the stray and clears it, so the wrapper passes."""
    assert F.REAL_SEND is not None and T._send is not F.REAL_SEND, "the suite did not patch transport._send"
    try:
        T._send("GET", "https://api.upbit.com/v1/ticker?markets=KRW-BTC", headers={}, params=None, json_body=None,
                timeout=10.0)
    except F.Refused as exc:
        assert str(exc) == "E1 transport send inside the execution suite", str(exc)
    else:
        raise AssertionError("an unpatched transport._send was not refused under the suite")
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()


# --------------------------------------------------------------------------- #
# Task 3: signing, sending, answers and the KIS token cache (spec 5 steps 3-5, Upbit and OKX signing, KIS "Token";
# contract 3.2 serve(), 6; E3, E11, E12, E15, E37, E39). Every send goes to F.serve, the probe's to the suite's stub.
# --------------------------------------------------------------------------- #
_T3_TOKEN = {"access_token": "test-token-1", "token_type": "Bearer", "expires_in": 86400,
             "access_token_token_expired": "2026-10-25 09:00:00"}       # contract 3.2's KIS token answer
_T3_OK = {"rt_cd": "0", "msg_cd": "KIOK0510", "msg1": "", "output1": [], "output2": []}
_T3_OKX_OK = {"code": "0", "msg": "", "data": []}
_T3_POST = ("POST", "/oauth2/tokenP")
_T3_GET = ("GET", _T2_BALANCE)
_T3_TICKER = ("GET", "/v1/ticker")
_T3_ACCOUNTS = ("GET", "/v1/accounts")
_T3_TIME = "/api/v5/public/time"
_T3_KIS_HOST = "https://openapi.koreainvestment.com:9443"
_T3_TS = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z")
_T3_TMP = re.compile(r"\.kis_token\.[0-9a-f]{12}\.tmp")
_T3_WAIT = "kis: no token may be issued yet; KIS skipped this poll"
_T3_BLOCK = "kis: KIS issued a token it had called invalid; no token for 6 hours"


def _t3_token(name: str) -> dict:
    """The KIS token answer with another token."""
    return dict(_T3_TOKEN, access_token=name)


def _t3_kis():
    """One KIS balance inquiry (TTTC8434R, two parameters); its parsed body."""
    return T.request("kis", "GET", _T2_BALANCE, [("INQR_DVSN", "01"), ("PDNO", "%")], tr_id="TTTC8434R").body


def _t3_raises(kind, fn, *args, **kwargs):
    """The `kind` exception fn(*args, **kwargs) raises; anything else it raises propagates."""
    try:
        fn(*args, **kwargs)
    except kind as exc:
        return exc
    raise AssertionError(f"{getattr(fn, '__name__', fn)} did not raise {kind.__name__}")


def _t3_raise(exc):
    """A serve() route that raises `exc` where _send would."""
    def answer(call):
        raise exc
    return answer


def _t3_raw(status: int, raw: bytes, headers=None):
    """A serve() route answering `raw` bytes with `status` (the Date header unless `headers` are given)."""
    def answer(call):
        return status, {"Date": F.DATE_HEADER} if headers is None else headers, raw
    return answer


def _t3_b64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _t3_jwt(call: dict) -> tuple[dict, dict]:
    """(header, payload) of the Upbit JWT a recorded call carried, once its HS512 signature over the base64url
    header and payload has been checked with the fake secret."""
    scheme, token = call["headers"]["Authorization"].split(" ")
    head, payload, signature = token.split(".")
    want = hmac.new(F.FAKE_KEYS["UPBIT_SECRET_KEY"].encode(), f"{head}.{payload}".encode(), hashlib.sha512).digest()
    assert scheme == "Bearer" and "=" not in token and _t3_b64(signature) == want, token
    return json.loads(_t3_b64(head)), json.loads(_t3_b64(payload))


def _t3_home() -> Path:
    return Path(os.environ["TRADEGEN_HOME"])


def test_serve_answers_records_and_refuses_strays():
    """The Task 3 fixture (contract 3.2), used through request: a body with HTTP 200 and the Date header, Seq answers
    in order, every call recorded with its params and timeout; a call with params, another timeout, no route or a
    used-up Seq is a stray, recorded and refused; afterwards transport._send is the suite's refusing stub again."""
    stub = T._send
    ticker = [{"market": "KRW-BTC", "trade_price": 100000000.0}]
    with F.fake_keys(), F.serve({_T3_TICKER: ticker, _T3_ACCOUNTS: F.Seq((503, {}), [])}) as calls:
        answer = T.request("upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC")])
        assert answer.body == ticker and answer.server_utc == F.NOW, answer
        assert T.request("upbit", "GET", "/v1/accounts").body == []
        rows = [(c["method"], c["url"], c["path"], c["query"], c["params"], c["timeout"], c["json_body"])
                for c in calls]
        first = ("GET", "https://api.upbit.com/v1/ticker?markets=KRW-BTC", "/v1/ticker", "markets=KRW-BTC", None,
                 10.0, None)
        retried = ("GET", "https://api.upbit.com/v1/accounts", "/v1/accounts", "", None, 10.0, None)
        assert rows == [first, retried, retried], rows
        assert calls[0]["headers"] == {"Accept": "application/json"}, calls[0]["headers"]
        for url, params, timeout, why in (("https://api.upbit.com/v1/ticker", {"markets": "KRW-BTC"}, 10.0,
                                           ": params/timeout"),
                                          ("https://api.upbit.com/v1/ticker", None, 30.0, ": params/timeout"),
                                          ("https://api.upbit.com/v1/deposits", None, 10.0, ""),
                                          ("https://api.upbit.com/v1/accounts", None, 10.0, "")):   # Seq used up
            exc = _t3_raises(AssertionError, T._send, "GET", url, headers={}, params=params, json_body=None,
                             timeout=timeout)
            assert str(exc) == f"unrouted GET {urlsplit(url).path}{why}", str(exc)
        assert F.STRAYS == ["GET /v1/ticker", "GET /v1/ticker", "GET /v1/deposits", "GET /v1/accounts"], F.STRAYS
        F.STRAYS.clear()
    assert T._send is stub


def test_upbit_jwt_is_hs512_with_the_exact_query_hash_and_a_fresh_nonce():
    """Spec 5 Upbit (research upbit.md 2): HS512 over the base64url header and payload, checked here with the fake
    secret; query_hash is the SHA512 of the query exactly as it rides in the URL (states[] repeated, brackets not
    encoded) with query_hash_alg SHA512; no query_hash without parameters; no exp; a fresh uuid4 nonce on every
    attempt, a retried one included; keys.read names the two Upbit keys only."""
    seen, real_read = [], keys.read
    routes = {("GET", "/v1/orders/open"): [], _T3_ACCOUNTS: F.Seq((503, {}), [])}
    with (F.fake_keys(), _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)),
          F.serve(routes) as calls):
        T.request("upbit", "GET", "/v1/orders/open", [("states[]", "wait"), ("states[]", "watch"), ("limit", "100")])
        T.request("upbit", "GET", "/v1/accounts")
    query = urlsplit(calls[0]["url"]).query
    assert query == "states[]=wait&states[]=watch&limit=100", query
    head, payload = _t3_jwt(calls[0])
    assert head == {"alg": "HS512", "typ": "JWT"}, head
    assert payload == {"access_key": "test-upbit-access", "nonce": payload["nonce"],
                       "query_hash": hashlib.sha512(query.encode()).hexdigest(), "query_hash_alg": "SHA512"}, payload
    assert set(calls[0]["headers"]) == {"Authorization", "Accept"}, calls[0]["headers"]
    assert calls[0]["headers"]["Accept"] == "application/json"
    nonces = [payload["nonce"]]
    for call in calls[1:]:
        head, plain = _t3_jwt(call)
        assert head == {"alg": "HS512", "typ": "JWT"} and plain == {"access_key": "test-upbit-access",
                                                                   "nonce": plain["nonce"]}, plain
        nonces.append(plain["nonce"])
    assert len(calls) == 3 and len(set(nonces)) == 3, nonces
    assert all(uuid.UUID(n).version == 4 and str(uuid.UUID(n)) == n for n in nonces), nonces
    assert seen == [T.CREDENTIALS["upbit"]] * 3, seen


def test_okx_signs_the_timestamp_get_and_the_path_with_its_query():
    """Spec 5 OKX (research okx.md 2): the four OK-ACCESS headers and Content-Type and nothing else (never the demo
    header); OK-ACCESS-TIMESTAMP is ISO 8601 UTC with milliseconds and Z, from transport._clock; OK-ACCESS-SIGN is
    re-derived here as Base64(HMAC-SHA256(secret, timestamp + "GET" + path?query)); keys.read names the three OKX
    keys only."""
    seen, real_read = [], keys.read
    at = F.NOW + timedelta(microseconds=123987)
    algo = "/api/v5/trade/orders-algo-pending"
    with (_t2_patched(T, "_okx_offset_s", 0.0), _t2_patched(T, "_clock", lambda: at), F.fake_keys(),
          _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)),
          F.serve({("GET", algo): _T3_OKX_OK, ("GET", "/api/v5/account/balance"): _T3_OKX_OK}) as calls):
        T.request("okx", "GET", algo, [("ordType", "conditional")])
        T.request("okx", "GET", "/api/v5/account/balance")
    assert len(calls) == 2 and seen == [T.CREDENTIALS["okx"]] * 2, seen
    for call, request_path in zip(calls, (algo + "?ordType=conditional", "/api/v5/account/balance")):
        head = call["headers"]
        assert set(head) == {"OK-ACCESS-KEY", "OK-ACCESS-SIGN", "OK-ACCESS-TIMESTAMP", "OK-ACCESS-PASSPHRASE",
                             "Content-Type"}, head
        stamp = head["OK-ACCESS-TIMESTAMP"]
        assert stamp == "2026-10-24T00:00:00.123Z" and _T3_TS.fullmatch(stamp), stamp
        sign = hmac.new(b"test-okx-secret", (stamp + "GET" + request_path).encode(), hashlib.sha256).digest()
        assert head["OK-ACCESS-SIGN"] == base64.b64encode(sign).decode(), request_path
        assert (head["OK-ACCESS-KEY"], head["OK-ACCESS-PASSPHRASE"], head["Content-Type"]) == (
            "test-okx-key", "test-okx-pass", "application/json")
        assert call["url"] == "https://www.okx.com" + request_path and call["json_body"] is None, call["url"]
    kst = timezone(timedelta(hours=9))
    assert T._okx_timestamp(datetime(2026, 10, 24, 9, 0, 0, 999999, tzinfo=kst)) == "2026-10-24T00:00:00.999Z"
    assert T._okx_sign("s", "t", "/p?q=1") == base64.b64encode(hmac.new(b"s", b"tGET/p?q=1",
                                                                        hashlib.sha256).digest()).decode()


def test_the_okx_offset_comes_from_public_time_at_receipt():
    """E3, E39: a good public/time answer sets _okx_offset_s = ts / 1000 - received_utc, received_utc being the one
    clock read made right after _send returned; an answer 30 s off makes every signed request refused before any
    key is read; a malformed answer leaves no offset behind."""
    base_ms = 1792800000000                                          # F.NOW in milliseconds
    assert F.NOW.timestamp() * 1000 == base_ms
    reads, now = [], [F.NOW]

    def clock():
        reads.append(now[0])
        return now[0]

    def time_answer(ms):
        def answer(call):
            now[0] += timedelta(seconds=1)                           # the answer arrives a second later
            body = {"code": "0", "msg": "", "data": [{"ts": str(ms)}]}
            return 200, {"Date": F.DATE_HEADER}, json.dumps(body).encode("utf-8")
        return answer
    routes = {("GET", _T3_TIME): F.Seq(time_answer(base_ms + 3000), time_answer(base_ms + 32000), _T3_OKX_OK)}
    with _t2_patched(T, "_clock", clock), F.serve(routes):
        assert T._okx_offset_s is None
        answer = T.request("okx", "GET", _T3_TIME)
        assert answer.received_utc == F.NOW + timedelta(seconds=1) and reads == [answer.received_utc], reads
        assert T._okx_offset_s == 2.0, T._okx_offset_s
        assert _t2_passes("okx", "GET", "/api/v5/account/config")
        T.request("okx", "GET", _T3_TIME)
        assert T._okx_offset_s == 30.0, T._okx_offset_s
        assert _t2_refused("okx", "GET", "/api/v5/account/config") == _T2_SKEW
        _t3_raises(IndexError, T.request, "okx", "GET", _T3_TIME)    # "data": []
        assert T._okx_offset_s is None


def test_public_endpoints_read_no_key():
    """Spec 5: the Upbit ticker and the OKX public time and ticker carry only Accept; keys.read fails the test."""
    routes = {_T3_TICKER: [], ("GET", _T3_TIME): {"code": "0", "msg": "", "data": [{"ts": "1792800000000"}]},
              ("GET", "/api/v5/market/ticker"): _T3_OKX_OK}
    with _t2_patched(keys, "read", _t2_boom), F.serve(routes) as calls:
        T.request("upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC,KRW-USDT")])
        T.request("okx", "GET", _T3_TIME)
        T.request("okx", "GET", "/api/v5/market/ticker", [("instId", "BTC-USDT")])
    assert [c["url"] for c in calls] == ["https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-USDT",
                                         "https://www.okx.com/api/v5/public/time",
                                         "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"], calls
    assert [c["headers"] for c in calls] == [{"Accept": "application/json"}] * 3, calls


def test_kis_inquiry_headers_carry_the_token_tr_id_and_app_key():
    """Spec 5 KIS: the token comes from the POST (content-type only, the client_credentials body, no parameters);
    the GET carries content-type, the bearer token, appkey, appsecret, the pinned tr_id and custtype P, with the
    query in the URL (PDNO=% as %25); each keys.read names the two KIS credentials only; the token POST's Answer
    shows no token in its repr."""
    seen, real_read = [], keys.read
    with (F.fake_keys(), _t2_patched(keys, "read", lambda names: seen.append(tuple(names)) or real_read(names)),
          F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _T3_OK}) as calls):
        assert _t3_kis() == _T3_OK
        assert "test-token-1" not in repr(T.request("kis", "POST", "/oauth2/tokenP"))
    post, get = calls[:2]
    assert (post["method"], post["url"], post["headers"], post["json_body"]) == (
        "POST", _T3_KIS_HOST + "/oauth2/tokenP", {"content-type": "application/json; charset=utf-8"},
        {"grant_type": "client_credentials", "appkey": "test-kis-appkey", "appsecret": "test-kis-appsecret"}), post
    assert get["url"] == _T3_KIS_HOST + _T2_BALANCE + "?INQR_DVSN=01&PDNO=%25", get["url"]
    assert get["headers"] == {"content-type": "application/json; charset=utf-8", "authorization": "Bearer test-token-1",
                              "appkey": "test-kis-appkey", "appsecret": "test-kis-appsecret", "tr_id": "TTTC8434R",
                              "custtype": "P"}, get["headers"]
    assert get["json_body"] is None and len(calls) == 3
    assert seen == [T.CREDENTIALS["kis"]] * 3, seen


def test_a_get_is_retried_once_on_connection_errors_429_and_5xx():
    """Spec 5 step 4: a GET goes once more, after _sleep(2.0), on HTTP 503, 429, requests' ConnectionError and its
    subclass ConnectTimeout; every attempt is followed by _sleep(0.2); a second failure is final."""
    errors = requests.exceptions
    for first in ((503, {}), (429, {}), _t3_raise(errors.ConnectionError("x")), _t3_raise(errors.ConnectTimeout("x"))):
        F.SLEEPS.clear()
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: F.Seq(first, [{"currency": "KRW"}])}) as calls:
            assert T.request("upbit", "GET", "/v1/accounts").body == [{"currency": "KRW"}]
        assert len(calls) == 2 and F.SLEEPS == [0.2, 2.0, 0.2], (first, F.SLEEPS)
    for twice, text in (((503, {}), "upbit /v1/accounts: HTTP 503"),
                        (_t3_raise(errors.ConnectionError("x")), "upbit /v1/accounts: ConnectionError")):
        F.SLEEPS.clear()
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: F.Seq(twice, twice)}) as calls:
            assert str(_t3_raises(T.InquiryError, T.request, "upbit", "GET", "/v1/accounts")) == text
        assert len(calls) == 2 and F.SLEEPS == [0.2, 2.0, 0.2], (text, F.SLEEPS)


def test_no_retry_on_400_a_read_timeout_or_any_token_post():
    """A 400, a ReadTimeout (not a connection error: spec 5 names one) and every failure of the KIS token POST go
    out once, followed by the one _sleep(0.2)."""
    errors = requests.exceptions
    cases = ((("upbit", "GET", "/v1/accounts"), _T3_ACCOUNTS, (400, {"error": {"name": "validation_error"}}),
              "upbit /v1/accounts: HTTP 400 validation_error"),
             (("upbit", "GET", "/v1/accounts"), _T3_ACCOUNTS, _t3_raise(errors.ReadTimeout("x")),
              "upbit /v1/accounts: ReadTimeout"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, _t3_raise(errors.ConnectionError("x")),
              "kis /oauth2/tokenP: ConnectionError"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, _t3_raise(errors.ConnectTimeout("x")),
              "kis /oauth2/tokenP: ConnectTimeout"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, (503, {}), "kis /oauth2/tokenP: HTTP 503"),
             (("kis", "POST", "/oauth2/tokenP"), _T3_POST, (429, {}), "kis /oauth2/tokenP: HTTP 429"))
    for args, route, answer, text in cases:
        F.SLEEPS.clear()
        with F.fake_keys(), F.serve({route: answer}) as calls:
            exc = _t3_raises(T.InquiryError, T.request, *args)
        assert (type(exc), str(exc), len(calls), F.SLEEPS) == (T.InquiryError, text, 1, [0.2]), (text, str(exc))


def test_send_errors_become_type_names_and_suite_errors_propagate():
    """E15, E37: a ValueError or OSError out of _send (every requests exception is an OSError; http.client's latin-1
    UnicodeEncodeError on a header quotes the value) becomes InquiryError "<venue> <path>: <TypeName>" from None:
    no URL, no query, no exception text. The suite's Refused and the router's AssertionError propagate unchanged."""
    secret = F.FAKE_KEYS["KIS_APP_SECRET"]
    errors = requests.exceptions
    raised = (errors.ReadTimeout(f"https://api.upbit.com/v1/accounts?x={secret}"), errors.InvalidHeader(secret),
              UnicodeEncodeError("latin-1", secret + "\u20ac", len(secret), len(secret) + 1, "ordinal not in range"),
              OSError(secret), ValueError(secret))
    for exc in raised:
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: _t3_raise(exc)}) as calls:
            got = _t3_raises(T.InquiryError, T.request, "upbit", "GET", "/v1/accounts")
        assert str(got) == f"upbit /v1/accounts: {type(exc).__name__}" and got.args == (str(got),), str(got)
        assert type(got) is T.InquiryError and got.__cause__ is None and got.__suppress_context__, repr(got)
        assert len(calls) == 1, type(exc).__name__
    with F.fake_keys(), F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _t3_raise(raised[2])}):
        got = _t3_raises(T.InquiryError, _t3_kis)
    assert str(got) == f"kis {_T2_BALANCE}: UnicodeEncodeError", str(got)                 # no query, no value
    for exc in (F.Refused("E1 transport send inside the execution suite"), AssertionError("unrouted GET /x")):
        with F.fake_keys(), F.serve({_T3_ACCOUNTS: _t3_raise(exc)}) as calls:
            assert _t3_raises(type(exc), T.request, "upbit", "GET", "/v1/accounts") is exc
        assert len(calls) == 1


def test_answers_give_auth_errors_codes_and_no_text():
    """E15: HTTP 401 and 403, a code in AUTH_CODES (Upbit out_of_scope on any status, OKX 50120 and 50123 on HTTP
    200, KIS EGW00103) are AuthError; a KIS rt_cd or OKX code other than "0", an Upbit error body, a 3xx, a body
    that is not JSON and a token answer whose access_token is missing, empty or not a string are InquiryError. Each
    text is the venue, the path, the HTTP status and the venue's code: never a message, a header or an unplain
    code."""
    def upbit_error(name):
        return {"error": {"name": name, "message": "fixture text"}}

    def kis(code, rt_cd="1"):
        return {"rt_cd": rt_cd, "msg_cd": code, "msg1": "fixture text"}

    redirect = _t3_raw(302, b"[]", {"Date": F.DATE_HEADER, "Location": "https://elsewhere.example/v1/accounts?k=1"})
    cases = [
        ("upbit", "/v1/accounts", (401, upbit_error("out_of_scope")), T.AuthError, "HTTP 401 out_of_scope", 1),
        ("upbit", "/v1/accounts", (400, upbit_error("out_of_scope")), T.AuthError, "HTTP 400 out_of_scope", 1),
        ("upbit", "/v1/accounts", _t3_raw(403, b"<html>fixture text</html>"), T.AuthError, "HTTP 403", 1),
        ("upbit", "/v1/accounts", (400, upbit_error("validation_error")), T.InquiryError,
         "HTTP 400 validation_error", 1),
        ("upbit", "/v1/accounts", upbit_error("server_error"), T.InquiryError, "HTTP 200 server_error", 1),
        ("upbit", "/v1/accounts", redirect, T.InquiryError, "HTTP 302", 1),
        ("okx", "/api/v5/account/balance", (304, _T3_OKX_OK), T.InquiryError, "HTTP 304 0", 1),
        ("upbit", "/v1/accounts", _t3_raw(200, b"fixture text"), T.InquiryError, "HTTP 200: not JSON", 1),
        ("okx", "/api/v5/account/balance", {"code": "50120", "msg": "fixture text", "data": []}, T.AuthError,
         "HTTP 200 50120", 1),
        ("okx", "/api/v5/account/balance", {"code": "50123", "msg": "fixture text", "data": []}, T.AuthError,
         "HTTP 200 50123", 1),
        ("okx", "/api/v5/account/balance", (401, {"code": "50113", "msg": "fixture text"}), T.AuthError,
         "HTTP 401 50113", 1),
        ("okx", "/api/v5/account/balance", {"code": "51000", "msg": "fixture text", "data": []}, T.InquiryError,
         "HTTP 200 51000", 1),
        ("okx", "/api/v5/account/balance", {"code": "fixture text 12345678", "data": []}, T.InquiryError,
         "HTTP 200", 1),
        ("kis", _T2_BALANCE, kis("EGW00103"), T.AuthError, "HTTP 200 EGW00103", 1),
        ("kis", _T2_BALANCE, kis("APBK0013"), T.InquiryError, "HTTP 200 APBK0013", 1),
        ("kis", _T2_BALANCE, (500, kis("EGW00201")), T.InquiryError, "HTTP 500 EGW00201", 2),
        ("kis", _T2_BALANCE, {"msg_cd": "", "msg1": "fixture text"}, T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", {"token_type": "Bearer", "expires_in": 86400}, T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", dict(_T3_TOKEN, access_token=""), T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", dict(_T3_TOKEN, access_token=7), T.InquiryError, "HTTP 200", 1),
        ("kis", "/oauth2/tokenP", (403, {"error_description": "fixture text", "error_code": "EGW00133"}),
         T.AuthError, "HTTP 403 EGW00133", 1),
        ("kis", "/oauth2/tokenP", (500, {"error_description": "fixture text", "error_code": "EGW00133"}),
         T.InquiryError, "HTTP 500 EGW00133", 1),
    ]
    for venue, path, answer, kind, tail, sent in cases:
        method = "POST" if path == "/oauth2/tokenP" else "GET"
        routes = {(method, path): answer} | ({_T3_POST: _T3_TOKEN} if venue == "kis" and method == "GET" else {})
        tr_id = "TTTC8434R" if method == "GET" and venue == "kis" else None
        with _t2_patched(T, "_okx_offset_s", 0.0), F.fake_keys(), F.serve(routes) as calls:
            exc = _t3_raises(T.InquiryError, T.request, venue, method, path, tr_id=tr_id)
        assert (type(exc), str(exc)) == (kind, f"{venue} {path}: {tail}"), (venue, path, tail, str(exc))
        assert len([c for c in calls if c["path"] == path]) == sent, (tail, calls)
        assert "fixture" not in str(exc) and "elsewhere" not in str(exc) and "test-" not in str(exc), str(exc)
    assert T._check_answer("upbit", "/v1/accounts", 200, b"[]") == []
    assert T._check_answer("okx", "/api/v5/account/balance", 200, b'{"code": "0", "data": []}') == {"code": "0",
                                                                                                  "data": []}


def test_the_answer_carries_body_server_time_receipt_and_sha256():
    """E3, E39: Answer.body is the parsed JSON, server_utc the Date header as aware UTC (the name in any case, an
    offset converted, -0000 read as UTC, None when absent or unreadable), received_utc the clock read after _send
    returned, sha256 the hex digest of the raw bytes; repr(answer) holds no body."""
    raw = b'[{"market": "KRW-BTC", "trade_price": 100000000.0}]'
    when = datetime(2026, 10, 24, 0, 0, 30, tzinfo=timezone.utc)
    for headers, want in (({"Date": "Sat, 24 Oct 2026 00:00:30 GMT"}, when),
                          ({"date": "Sat, 24 Oct 2026 09:00:30 +0900"}, when),
                          ({"DATE": "Sat, 24 Oct 2026 00:00:30 -0000"}, when),
                          ({"Date": "not a date"}, None), ({"Date": ""}, None), ({}, None)):
        now = [F.NOW]

        def answer(call, headers=headers, now=now):
            now[0] = F.NOW + timedelta(seconds=2)                    # the clock moves while the answer travels
            return 200, headers, raw
        with _t2_patched(T, "_clock", lambda now=now: now[0]), F.serve({_T3_TICKER: answer}):
            got = T.request("upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC")])
        assert got.body == [{"market": "KRW-BTC", "trade_price": 100000000.0}], got.body
        assert got.server_utc == want and (want is None or got.server_utc.tzinfo == timezone.utc), (headers, got)
        assert got.received_utc == F.NOW + timedelta(seconds=2) and got.sha256 == hashlib.sha256(raw).hexdigest()
        assert "KRW-BTC" not in repr(got) and "trade_price" not in repr(got), repr(got)


def test_a_cached_token_is_reused_until_120_s_before_it_expires():
    """Spec 5 "Token": state_root()/kis_token.json is read first; its token is reused, with no POST, while now <
    expires_at - 120 and issued anew from there on; a missing, unreadable or malformed cache reads as none.
    _write_token opens its temp file exclusively: an existing one is FileExistsError, and the cache is untouched."""
    path = _t3_home() / "kis_token.json"
    now = F.NOW.timestamp()
    for expires_at, reused in ((now + 121, True), (now + 120.5, True), (now + 120, False), (now - 1, False)):
        path.write_text(json.dumps({"access_token": "test-token-0", "expires_at": expires_at}), encoding="utf-8")
        with (_t2_patched(T, "_next_issue_at", None), F.fake_keys(),
              F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _T3_OK}) as calls):
            _t3_kis()
        assert [c["method"] for c in calls] == (["GET"] if reused else ["POST", "GET"]), (expires_at, calls)
        token = "test-token-0" if reused else "test-token-1"
        assert calls[-1]["headers"]["authorization"] == f"Bearer {token}", expires_at
    for text in ("", "not json", "[]", '{"access_token": "t"}', '{"access_token": "", "expires_at": 1e12}',
                 '{"access_token": 7, "expires_at": 1e12}', '{"access_token": "t", "expires_at": "x"}',
                 '{"access_token": "t", "expires_at": null}', '{"expires_at": 1e12}',
                 '{"access_token": "t", "expires_at": Infinity}',
                 '{"access_token": "t", "expires_at": 1e999}',
                 '{"access_token": "t", "expires_at": NaN}',
                 '{"access_token": "t", "expires_at": -Infinity}',
                 '{"access_token": "t", "expires_at": true}',
                 '{"access_token": "t", "expires_at": 0}'):
        path.write_text(text, encoding="utf-8")
        assert T._read_token(path, now) is None, text
    assert T._read_token(_t3_home() / "no-such.json", now) is None and T._read_token(_t3_home(), now) is None
    path.write_text(json.dumps({"access_token": "t", "expires_at": now + 121}), encoding="utf-8")
    assert T._read_token(path, now) == "t" and T._read_token(path, now + 1) is None
    cache, tmp = path.read_text(encoding="utf-8"), _t3_home() / ".kis_token.0123456789ab.tmp"
    tmp.write_text("x", encoding="utf-8")
    _t3_raises(FileExistsError, T._write_token, path, tmp, "test-token-2", now + 3600)
    assert path.read_text(encoding="utf-8") == cache and tmp.read_text(encoding="utf-8") == "x"


def test_the_token_targets_are_checked_before_the_post_and_the_write_is_atomic():
    """The ledger's "KIS token burnt on refusal" (spec 5 "Token"): with no cache, the folder, the cache and the
    temp file pass checked_target BEFORE the token POST; the temp name checked then is the one written, fsynced and
    moved onto the cache by os.replace, each target checked again just before use; no temp file is left; the cache
    holds exactly {"access_token", "expires_at"} (epoch seconds, now + expires_in). The exclusive open is checked in
    test_a_cached_token_is_reused_until_120_s_before_it_expires."""
    home = _t3_home()
    path = home / "kis_token.json"
    events, real_check, real_replace, real_fsync = [], T.checked_target, os.replace, os.fsync

    def check(target, what="path", **kwargs):
        events.append(("check", Path(target), what))
        return real_check(target, what, **kwargs)

    def replace(src, dst):
        events.append(("replace", Path(src), Path(dst)))
        return real_replace(src, dst)

    def fsync(fd):
        events.append(("fsync",))
        return real_fsync(fd)

    def post(call):
        events.append(("POST",))
        return 200, {"Date": F.DATE_HEADER}, json.dumps(_t3_token("test-token-1") | {"expires_in": 600}).encode()
    os.replace, os.fsync = replace, fsync
    try:
        with (_t2_patched(T, "checked_target", check), F.fake_keys(),
              F.serve({_T3_POST: post, _T3_GET: _T3_OK}) as calls):
            assert _t3_kis() == _T3_OK
    finally:
        os.replace, os.fsync = real_replace, real_fsync
    tmp = events[2][1]
    assert _T3_TMP.fullmatch(tmp.name) and tmp.parent == home, tmp
    assert events == [("check", home, "KIS token folder"), ("check", path, "KIS token cache"),
                      ("check", tmp, "KIS token temp"), ("POST",),
                      ("check", home, "KIS token folder"), ("check", tmp, "KIS token temp"), ("fsync",),
                      ("check", tmp, "KIS token temp"), ("check", path, "KIS token cache"),
                      ("replace", tmp, path)], events
    assert [c["method"] for c in calls] == ["POST", "GET"]
    assert json.loads(path.read_text(encoding="utf-8")) == {"access_token": "test-token-1",
                                                            "expires_at": F.NOW.timestamp() + 600}
    assert sorted(p.name for p in home.iterdir()) == ["kis_token.json"], sorted(p.name for p in home.iterdir())
    assert T._next_issue_at == F.NOW.timestamp() + 70.0

    # A malformed lifetime must never become an indefinitely reusable token cache.
    for lifetime in (float("inf"), float("-inf"), float("nan"), "1e999", "bad", None, True, 0, -1):
        expired = json.dumps({"access_token": "test-token-old", "expires_at": F.NOW.timestamp()})
        path.write_text(expired, encoding="utf-8")
        reply = _t3_token("test-token-new") | {"expires_in": lifetime}
        with (_t2_patched(T, "_next_issue_at", None), F.fake_keys(), F.serve({_T3_POST: reply}) as calls):
            exc = _t3_raises(T.InquiryError, T._kis_token)
        assert str(exc) == "kis: token expiry is invalid", type(lifetime).__name__
        assert [c["method"] for c in calls] == ["POST"]
        assert path.read_text(encoding="utf-8") == expired
        assert sorted(p.name for p in home.iterdir()) == ["kis_token.json"]


def test_a_refused_token_target_sends_nothing_and_burns_no_issue():
    """A checked_target refusal of the folder, the cache or the temp file propagates as its RuntimeError (a crash,
    E33), before any send: no POST, no GET, no 70 s gap started, nothing written."""
    real = T.checked_target
    for refused in ("KIS token folder", "KIS token cache", "KIS token temp"):
        def check(target, what="path", refused=refused, **kwargs):
            if what == refused:
                raise RuntimeError(f"{what} refused (test)")
            return real(target, what, **kwargs)
        with (_t2_patched(T, "checked_target", check), F.fake_keys(),
              F.serve({_T3_POST: _T3_TOKEN, _T3_GET: _T3_OK}) as calls):
            exc = _t3_raises(RuntimeError, _t3_kis)
        assert str(exc) == f"{refused} refused (test)" and calls == [], (refused, calls)
        assert T._next_issue_at is None and list(_t3_home().iterdir()) == [], refused


def test_at_most_one_token_issue_per_70_s_and_the_post_is_never_retried():
    """E3: a second issue inside 70 s of the first is InquiryError with no POST; at 70 s it goes out. A token POST
    that fails to connect goes out once (never retried) and still starts the 70 s."""
    now = [F.NOW]
    path = _t3_home() / "kis_token.json"
    expired = json.dumps({"access_token": "test-token-0", "expires_at": F.NOW.timestamp()})
    routes = {_T3_POST: F.Seq(_T3_TOKEN, _t3_token("test-token-2")), _T3_GET: _T3_OK}
    with _t2_patched(T, "_clock", lambda: now[0]), F.fake_keys(), F.serve(routes) as calls:
        _t3_kis()
        path.write_text(expired, encoding="utf-8")                  # the cache ran out (or was replaced)
        now[0] = F.NOW + timedelta(seconds=69.999)
        exc = _t3_raises(T.InquiryError, _t3_kis)
        assert (type(exc), str(exc), len(calls)) == (T.InquiryError, _T3_WAIT, 2), str(exc)
        now[0] = F.NOW + timedelta(seconds=70)
        _t3_kis()
    assert [(c["method"], c["headers"].get("authorization")) for c in calls] == [
        ("POST", None), ("GET", "Bearer test-token-1"), ("POST", None), ("GET", "Bearer test-token-2")], calls
    path.write_text(expired, encoding="utf-8")
    F.SLEEPS.clear()
    connect = _t3_raise(requests.exceptions.ConnectionError("x"))
    with _t2_patched(T, "_next_issue_at", None), F.fake_keys(), F.serve({_T3_POST: connect, _T3_GET: _T3_OK}) as calls:
        assert str(_t3_raises(T.InquiryError, _t3_kis)) == "kis /oauth2/tokenP: ConnectionError"
        assert [c["method"] for c in calls] == ["POST"] and F.SLEEPS == [0.2], (calls, F.SLEEPS)
        assert T._next_issue_at == F.NOW.timestamp() + 70.0
        assert str(_t3_raises(T.InquiryError, _t3_kis)) == _T3_WAIT and len(calls) == 1


def test_a_token_code_marks_the_token_bad_and_the_next_issue_waits_70_s():
    """E15: EGW00121, EGW00122 and EGW00123 on a KIS inquiry, on any status, are InquiryError (never AuthError) and
    mark the token sent bad for this process: the cache holding it is not reused, and the next issue waits for the
    70 s rule. On the token POST itself such a code is a plain InquiryError. HTTP 500 with EGW00123 (how KIS answers
    an expired token) is retried once, 2 s later, with the same token, which is marked bad when the second answer is
    judged. The token never appears in an error text."""
    for code in sorted(T.KIS_TOKEN_CODES):
        for status in (200, 401, 500):
            body = json.dumps({"rt_cd": "1", "msg_cd": code, "msg1": "fixture text"}).encode()
            exc = _t3_raises(T.InquiryError, T._check_answer, "kis", _T2_BALANCE, status, body)
            assert isinstance(exc, T._TokenRejected) and not isinstance(exc, T.AuthError), (code, status)
            assert str(exc) == f"kis {_T2_BALANCE}: HTTP {status} {code}", str(exc)
        exc = _t3_raises(T.InquiryError, T._check_answer, "kis", "/oauth2/tokenP", 200,
                         json.dumps({"error_code": code}).encode())
        assert type(exc) is T.InquiryError and str(exc) == f"kis /oauth2/tokenP: HTTP 200 {code}", str(exc)
    now = [F.NOW]
    bad = {"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "fixture text"}
    routes = {_T3_POST: F.Seq(_T3_TOKEN, _t3_token("test-token-2")), _T3_GET: F.Seq(bad, _T3_OK)}
    with _t2_patched(T, "_clock", lambda: now[0]), F.fake_keys(), F.serve(routes) as calls:
        exc = _t3_raises(T.InquiryError, _t3_kis)
        assert str(exc) == f"kis {_T2_BALANCE}: HTTP 200 EGW00123" and T._bad_tokens == {"test-token-1"}, str(exc)
        now[0] = F.NOW + timedelta(seconds=69)
        wait = _t3_raises(T.InquiryError, _t3_kis)
        assert str(wait) == _T3_WAIT and len(calls) == 2, str(wait)            # the bad cached token is not reused
        now[0] = F.NOW + timedelta(seconds=70)
        assert _t3_kis() == _T3_OK
    assert [(c["method"], c["headers"].get("authorization")) for c in calls] == [
        ("POST", None), ("GET", "Bearer test-token-1"), ("POST", None), ("GET", "Bearer test-token-2")], calls
    cache = json.loads((_t3_home() / "kis_token.json").read_text(encoding="utf-8"))
    assert cache["access_token"] == "test-token-2" and "test-token" not in str(exc) + str(wait)
    F.SLEEPS.clear()
    expired = (500, {"rt_cd": "1", "msg_cd": "EGW00123", "msg1": "fixture text"})
    with _t2_patched(T, "_bad_tokens", set()), F.fake_keys(), F.serve({_T3_GET: expired}) as calls:
        exc = _t3_raises(T._TokenRejected, _t3_kis)                  # the cached test-token-2, sent twice
        assert T._bad_tokens == {"test-token-2"}, T._bad_tokens
    assert str(exc) == f"kis {_T2_BALANCE}: HTTP 500 EGW00123" and F.SLEEPS == [0.2, 2.0, 0.2], (str(exc), F.SLEEPS)
    assert [(c["method"], c["headers"]["authorization"]) for c in calls] == [("GET", "Bearer test-token-2")] * 2


def test_a_reissued_bad_token_is_auth_error_and_blocks_issuing_for_6_hours():
    """E15: KIS hands back the same token for 6 hours, so a bad token that the POST returns again is AuthError, and
    no POST goes out for 6 hours after that issue (6 h - 1 s: none; 6 h: one)."""
    now = [F.NOW]
    bad = {"rt_cd": "1", "msg_cd": "EGW00121", "msg1": "fixture text"}
    routes = {_T3_POST: F.Seq(_T3_TOKEN, _T3_TOKEN, _t3_token("test-token-2")), _T3_GET: F.Seq(bad, _T3_OK)}
    with _t2_patched(T, "_clock", lambda: now[0]), F.fake_keys(), F.serve(routes) as calls:
        _t3_raises(T.InquiryError, _t3_kis)
        again = now[0] = F.NOW + timedelta(seconds=70)
        exc = _t3_raises(T.AuthError, _t3_kis)
        assert str(exc) == _T3_BLOCK and T._next_issue_at == again.timestamp() + 6 * 3600, str(exc)
        now[0] = again + timedelta(hours=6, seconds=-1)
        wait = _t3_raises(T.InquiryError, _t3_kis)
        assert (type(wait), str(wait)) == (T.InquiryError, _T3_WAIT), str(wait)
        assert [c["method"] for c in calls] == ["POST", "GET", "POST"], calls
        now[0] = again + timedelta(hours=6)
        assert _t3_kis() == _T3_OK
    assert [c["method"] for c in calls] == ["POST", "GET", "POST", "POST", "GET"], calls
    assert calls[-1]["headers"]["authorization"] == "Bearer test-token-2" and "test-token" not in str(exc)


def test_the_token_cache_is_shared_with_the_kis_quote_client_both_ways():
    """Spec 5 "Token" (E3): the same file and format as data.krx.kis_client. Its _TOKEN_PATH, fixed when kis_client
    was first imported, is pointed into the temp home and back: what its _store_token writes, E1's _read_token
    reads (with the same 120 s margin); what E1's _write_token writes, its _cached_token reads. Neither KISClient()
    nor .token() is used, and no file in execution/ imports data.* or config (the import guard, here directly)."""
    from data.krx import kis_client
    home = _t3_home()
    path = T.isolation.state_root() / "kis_token.json"
    assert path == home / "kis_token.json", path
    keep = kis_client._TOKEN_PATH
    try:
        kis_client._TOKEN_PATH = path
        client = object.__new__(kis_client.KISClient)                # no __init__: no config read, no session
        assert kis_client._TOKEN_PATH.is_relative_to(home)
        client._store_token("test-token-9", 3600.0)
        assert set(json.loads(path.read_text(encoding="utf-8"))) == {"access_token", "expires_at"}
        assert T._read_token(path, time.time()) == "test-token-9"
        assert T._read_token(path, time.time() + 3600 - 120) is None
        T._write_token(path, path.with_name(".kis_token.0123456789ab.tmp"), "test-token-8", time.time() + 3600)
        assert set(json.loads(path.read_text(encoding="utf-8"))) == {"access_token", "expires_at"}
        assert kis_client._TOKEN_PATH.is_relative_to(home)
        assert client._cached_token() == "test-token-8"
        T._write_token(path, path.with_name(".kis_token.0123456789ac.tmp"), "test-token-7", time.time() + 100)
        assert kis_client._TOKEN_PATH.is_relative_to(home)
        assert client._cached_token() is None                                # inside its 120 s margin too
    finally:
        kis_client._TOKEN_PATH = keep
    assert sorted(p.name for p in home.iterdir()) == ["kis_token.json"]
    for py in sorted((ROOT / "execution").glob("*.py")):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            assert not [n for n in names if n.split(".")[0] in ("data", "config")], (py.name, names)


def test_a_public_send_through_request_is_refused_under_the_suite():
    """The probe of spec 9, through request: with no serve() a public Upbit ticker reaches the suite's refusing
    _send, whose Refused propagates (it is never wrapped as an InquiryError); one stray, asserted and cleared."""
    exc = _t3_raises(F.Refused, T.request, "upbit", "GET", "/v1/ticker", [("markets", "KRW-BTC")])
    assert str(exc) == "E1 transport send inside the execution suite", str(exc)
    assert F.STRAYS == ["GET /v1/ticker"], F.STRAYS
    F.STRAYS.clear()
