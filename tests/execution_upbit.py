"""Upbit inquiry (E1 Task 6; contract C10; spec 5 Upbit, 6; E12, E15, E16, E21, E22, E37, E38, E39).

Every send goes to `EF.serve` (the Upbit answers of contract 3.2, never a live one); the suite's wrapper refuses any
other send. The JWT is checked here against the exact query on the wire, with the fake secret.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from urllib.parse import urlsplit

from execution import upbit_inquiry
from execution.snapshot import Address, Holding, Move, Order
from tests import execution_fixtures as EF

PATH = {name: route[1] for name, route in EF.UPBIT_ROUTES.items()}
SIGNED = ("accounts", "orders_open", "orders_closed", "withdraws", "coin_addresses", "deposits", "api_keys")
ADDRESS = "bc1qfixtureaddress000000000000000000000"


def _path(call: dict) -> str:
    return urlsplit(call["url"]).path


def _query(call: dict) -> str:
    return urlsplit(call["url"]).query


def _headers(call: dict) -> dict:
    return {k.lower(): v for k, v in call["headers"].items()}


def _run(routes: dict, **key_changes):
    """One snapshot at EF.NOW under the fake keys (a keyword changes one; None removes it); (snapshot, calls)."""
    with EF.fake_keys(**key_changes), EF.serve(routes) as calls:
        snap = upbit_inquiry.snapshot(EF.NOW)
    return snap, calls


def _b64(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _jwt(call: dict) -> dict:
    """The payload of the call's Bearer JWT, after checking its HS512 signature with the fake secret."""
    scheme, _, token = _headers(call)["authorization"].partition(" ")
    assert scheme == "Bearer", scheme
    head, payload, sig = token.split(".")
    want = hmac.new(EF.FAKE_KEYS["UPBIT_SECRET_KEY"].encode(), f"{head}.{payload}".encode(), hashlib.sha512).digest()
    assert hmac.compare_digest(_b64(sig), want), "the JWT is not signed with the Upbit secret"
    assert json.loads(_b64(head)) == {"alg": "HS512", "typ": "JWT"}
    return json.loads(_b64(payload))


def _dated(name: str, date: str | None):
    """A serve() callable answering the default body of `name` with its own Date header (none for None)."""
    body = json.dumps(EF.UPBIT_BODIES[name]).encode("utf-8")
    return lambda call: (200, {} if date is None else {"Date": date}, body)


def test_every_private_call_carries_a_jwt_over_the_exact_query():
    snap, calls = _run(EF.upbit_routes())
    assert snap.ok, snap.error
    assert [_path(c) for c in calls] == [PATH[n] for n in SIGNED] + [PATH["ticker"]]   # contract C10's order
    assert all(c["method"] == "GET" for c in calls)
    nonces = []
    for call in calls[:-1]:
        claims = _jwt(call)
        nonces.append(claims["nonce"])
        assert claims["access_key"] == EF.FAKE_KEYS["UPBIT_ACCESS_KEY"] and "exp" not in claims, claims
        query = _query(call)
        if query:
            assert claims["query_hash"] == hashlib.sha512(query.encode()).hexdigest(), (_path(call), claims)
            assert claims["query_hash_alg"] == "SHA512"
            assert set(claims) == {"access_key", "nonce", "query_hash", "query_hash_alg"}, claims
        else:
            assert set(claims) == {"access_key", "nonce"}, claims
    assert len(set(nonces)) == len(nonces) == 7                  # a fresh nonce per call
    queries = {_path(c): _query(c) for c in calls}
    assert queries[PATH["orders_open"]] == "states[]=wait&states[]=watch&limit=100"      # brackets unencoded
    assert queries[PATH["orders_closed"]] == "states[]=done&states[]=cancel&limit=1000"  # no time: the last 7 days
    assert queries[PATH["withdraws"]] == queries[PATH["deposits"]] == "limit=100"
    assert queries[PATH["accounts"]] == queries[PATH["coin_addresses"]] == queries[PATH["api_keys"]] == ""


def test_the_ticker_is_public_and_asks_usdt_and_every_held_coin():
    routes = EF.upbit_routes()
    routes[EF.UPBIT_ROUTES["accounts"]] += [
        {"currency": "XRP", "balance": "0", "locked": "3", "avg_buy_price": "700", "avg_buy_price_modified": False,
         "unit_currency": "KRW"},
        {"currency": "ETH", "balance": "0.5", "locked": "0", "avg_buy_price": "0", "avg_buy_price_modified": False,
         "unit_currency": "KRW"},
        {"currency": "DOGE", "balance": "0", "locked": "0", "avg_buy_price": "0", "avg_buy_price_modified": False,
         "unit_currency": "KRW"}]
    snap, calls = _run(routes)
    assert snap.ok, snap.error
    ticker = calls[-1]
    assert _path(ticker) == PATH["ticker"] and "authorization" not in _headers(ticker), _headers(ticker)
    assert _query(ticker) == "markets=KRW-BTC,KRW-ETH,KRW-USDT,KRW-XRP"     # held coins and USDT; DOGE is not held


def test_the_full_fixture_gives_every_field():
    routes = EF.upbit_routes(orders_open=[dict(EF.UPBIT_ROWS["orders_open"])],
                             withdraws=[dict(EF.UPBIT_ROWS["withdraws"])])
    snap, calls = _run(routes)
    assert snap.ok and snap.error is None and snap.flags == frozenset(), snap.error
    assert snap.venue == "upbit" and snap.utc == "2026-10-24T00:00:00Z"
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
    assert dict(snap.cash) == {"KRW": 20000.0}                   # KRW is cash, never a holding
    assert dict(snap.holdings) == {"BTC": Holding(units=0.0001, locked=0.0, avg_cost=100000000.0)}
    assert snap.open_orders == (Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90000000.0),)
    assert snap.fills == (Move(id="u-done-1", symbol="BTC", counter="KRW", side="buy", units=0.0001),)
    assert snap.withdrawals == (Move(id="u-wd-1", symbol="BTC", side="out", units=0.0001),)
    assert snap.deposits == (Move(id="u-dep-1", symbol="KRW", side="in", units=20000.0),)
    assert snap.withdrawal_addresses == (Address(currency="BTC", net_type="BTC", address=ADDRESS),)
    assert snap.key_expiry == "2027-05-27T06:17:51Z"             # 15:17:51 KST
    assert dict(snap.prices_krw) == {"BTC": 100000000.0, "USDT": 1400.0}
    assert snap.deposit_krw is None and dict(snap.loans) == {} and dict(snap.earn) == {}
    assert set(snap.response_sha256) == {PATH[n] for n in SIGNED + ("ticker",)}
    assert all(re.fullmatch(r"[0-9a-f]{64}", v) for v in snap.response_sha256.values())
    assert PATH["status_wallet"] not in {_path(c) for c in calls}    # allowlisted, routed, never asked (E22)


def test_balances_count_locked_units_and_orders_map_sides():
    routes = EF.upbit_routes()
    routes[EF.UPBIT_ROUTES["accounts"]][0] |= {"balance": "15000", "locked": "5000"}
    routes[EF.UPBIT_ROUTES["accounts"]][1] |= {"balance": "0.5", "locked": "0.25"}
    routes[EF.UPBIT_ROUTES["accounts"]].append({"currency": "ETH", "balance": "1", "locked": "0",
                                                "avg_buy_price": "0.05", "avg_buy_price_modified": False,
                                                "unit_currency": "BTC"})
    routes[EF.UPBIT_ROUTES["ticker"]].append({"market": "KRW-ETH", "trade_price": 5000000})
    routes[EF.UPBIT_ROUTES["orders_open"]] = [
        dict(EF.UPBIT_ROWS["orders_open"]),
        dict(EF.UPBIT_ROWS["orders_open"], uuid="u-open-2", side="ask", state="watch", price=None,
             remaining_volume="0.00005"),
        dict(EF.UPBIT_ROWS["orders_open"], uuid="u-open-3", price="0")]        # a zero price: no limit price
    routes[EF.UPBIT_ROUTES["orders_closed"]] += [
        dict(EF.UPBIT_BODIES["orders_closed"][0], uuid="u-done-2", side="ask",
             executed_volume="0.00002"),
        dict(EF.UPBIT_BODIES["orders_closed"][0], uuid="u-cancel-1", state="cancel", executed_volume="0")]
    snap, _calls = _run(routes)
    assert snap.ok, snap.error
    assert dict(snap.cash) == {"KRW": 20000.0}                   # balance + locked
    assert snap.holdings["BTC"] == Holding(units=0.75, locked=0.25, avg_cost=100000000.0)
    assert snap.holdings["ETH"] == Holding(units=1.0, locked=0.0, avg_cost=None)   # bought for BTC: no KRW cost
    assert snap.prices_krw["ETH"] == 5000000.0
    assert snap.open_orders == (Order(id="u-open-1", symbol="BTC", side="buy", units=0.0001, price=90000000.0),
                                Order(id="u-open-2", symbol="BTC", side="sell", units=0.00005, price=None),
                                Order(id="u-open-3", symbol="BTC", side="buy", units=0.0001, price=None))
    assert snap.fills == (Move(id="u-done-1", symbol="BTC", counter="KRW", side="buy", units=0.0001),
                          Move(id="u-done-2", symbol="BTC", counter="KRW", side="sell", units=0.00002))


def test_server_time_and_offset_come_from_the_first_answer_with_a_date_header():
    routes = EF.upbit_routes(accounts=_dated("accounts", None),
                             orders_open=_dated("orders_open", "Fri, 23 Oct 2026 23:59:15 GMT"))
    snap, _calls = _run(routes)                                  # every later answer carries DATE_HEADER (offset 0)
    assert snap.ok and snap.server_utc == "2026-10-23T23:59:15Z" and snap.clock_offset_s == -45.0, snap


def test_key_expiry_is_the_earliest_and_an_offset_less_value_is_seoul():
    later = {"access_key": "other", "expire_at": "2027-09-01T00:00:00+09:00"}
    snap, _calls = _run(EF.upbit_routes(api_keys=[later, dict(EF.UPBIT_ROWS["api_keys_naive"])]))
    assert snap.ok and snap.key_expiry == "2027-05-27T06:17:51Z", snap.key_expiry   # naive 15:17:51 read as KST
    snap, _calls = _run(EF.upbit_routes(api_keys=[later, {"access_key": "x", "expire_at": "2027-01-01T00:00:00Z"}]))
    assert snap.ok and snap.key_expiry == "2027-01-01T00:00:00Z", snap.key_expiry
    snap, _calls = _run(EF.upbit_routes(api_keys=[]))
    assert snap.ok and snap.key_expiry is None


def test_out_of_scope_gives_auth_error():
    for name, status in (("accounts", 401), ("orders_closed", 401), ("coin_addresses", 403)):   # Upbit sends either
        snap, calls = _run(EF.upbit_routes(**{name: (status, dict(EF.UPBIT_ROWS["out_of_scope"]))}))
        assert not snap.ok and snap.flags == frozenset({"auth_error"}) and snap.error, (name, snap)
        assert _path(calls[-1]) == PATH[name]                    # it stopped at the refused call
        assert "fixture:" not in snap.error and EF.FAKE_KEYS["UPBIT_ACCESS_KEY"] not in snap.error
        clock = (None, None) if name == "accounts" else ("2026-10-24T00:00:00Z", 0.0)   # the time read so far (E39)
        assert (snap.server_utc, snap.clock_offset_s) == clock, (name, snap.server_utc, snap.clock_offset_s)


def test_missing_keys_give_keys_missing():
    for name in ("UPBIT_ACCESS_KEY", "UPBIT_SECRET_KEY"):
        snap, calls = _run(EF.upbit_routes(), **{name: None})
        assert calls == [] and not snap.ok, name
        assert snap.flags == frozenset({"keys_missing"}) and snap.error == f"keys missing: {name}", snap.error


def test_a_malformed_field_fails_closed_with_names_only():
    cases = (("accounts", lambda b: b[1].pop("locked"), "field locked"),
             ("accounts", lambda b: b[1].update(balance="0.0001BTC"), "field balance"),
             ("accounts", lambda b: b[1].update(balance=10 ** 400), "field balance"),     # too large for a float
             ("orders_closed", lambda b: b[0].update(market="KRWBTC"), "field market"),
             ("orders_closed", lambda b: b[0].update(executed_volume=None), "field executed_volume"),
             ("coin_addresses", lambda b: b[0].pop("withdraw_address"), "field withdraw_address"),
             ("api_keys", lambda b: b[0].update(expire_at="27 May 2027"), "field expire_at"),
             ("ticker", lambda b: b[0].update(trade_price="nan"), "field trade_price"),
             ("ticker", lambda b: b[0].update(trade_price=True), "field trade_price"),
             ("ticker", lambda b: b[0].update(market="BTC-ETH"), "field market"),         # not a KRW price
             ("deposits", lambda b: b.insert(0, "not a row"), "field uuid"))
    for name, change, tail in cases:
        routes = EF.upbit_routes()
        change(routes[EF.UPBIT_ROUTES[name]])
        snap, _calls = _run(routes)
        assert not snap.ok and snap.flags == frozenset(), name
        assert snap.error == f"upbit: {PATH[name]}: {tail}", snap.error
        assert ADDRESS not in snap.error and "0.0001" not in snap.error and "2027" not in snap.error
    snap, _calls = _run(EF.upbit_routes(withdraws={"not": "a list"}))
    assert not snap.ok and snap.error == f"upbit: {PATH['withdraws']}: field body", snap.error


def test_other_venue_errors_fail_closed_and_an_unrouted_send_propagates():
    bad = {"error": {"name": "validation_error", "message": "fixture: bad"}}
    snap, calls = _run(EF.upbit_routes(deposits=(400, bad)))    # an InquiryError, not an auth answer
    assert not snap.ok and snap.flags == frozenset() and PATH["deposits"] in snap.error, snap.error
    assert "fixture:" not in snap.error and _path(calls[-1]) == PATH["deposits"], snap.error
    routes = EF.upbit_routes()
    routes[EF.UPBIT_ROUTES["accounts"]][1]["currency"] = ["BTC"]        # unhashable: a TypeError, never its text
    snap, _calls = _run(routes)
    assert not snap.ok and snap.flags == frozenset(), snap.error
    assert snap.error == f"upbit: {PATH['accounts']}: TypeError", snap.error
    with EF.fake_keys(), EF.serve(EF.upbit_routes(api_keys=None)):
        try:
            upbit_inquiry.snapshot(EF.NOW)                       # the router refuses the unrouted call (E38)
        except AssertionError:
            pass
        else:
            raise AssertionError("an unrouted send became a snapshot")
    assert len(EF.STRAYS) == 1 and EF.STRAYS[0].endswith(PATH["api_keys"]), EF.STRAYS
    EF.STRAYS.clear()


def test_a_refused_send_propagates():
    with EF.fake_keys():
        try:
            upbit_inquiry.snapshot(EF.NOW)                       # no serve(): the suite's refusing stub answers
        except EF.Refused:
            pass
        else:
            raise AssertionError("a refused send became a snapshot")
    assert len(EF.STRAYS) == 1 and EF.STRAYS[0].endswith(PATH["accounts"]), EF.STRAYS   # the first signed call
    EF.STRAYS.clear()
