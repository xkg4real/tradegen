"""OKX inquiry and its read-only self-check (E1 Task 7; contract C11; spec 5 OKX, 6; E25, E26, E32, E37, E38, E39).

Every send goes to `EF.serve` (the OKX answers of contract 3.2, never a live one); the suite's wrapper refuses any
other send. OKX answers its errors on HTTP 200 with a code; transport turns 50120 and 50123 into AuthError.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from urllib.parse import parse_qsl, urlsplit

from execution import keys, okx_inquiry, transport
from execution.snapshot import Holding, Move, Order
from tests import execution_fixtures as EF

PATH = {name: route[1] for name, route in EF.OKX_ROUTES.items()}
SIGNED_BEFORE_ALGO = ("balance", "asset_balances", "positions", "asset_valuation", "savings", "flexible_loan",
                      "orders_pending")
AFTER_ALGO = ("fills", "deposit_history", "withdrawal_history", "ticker")
OKX_KEYS = ("OKX_API_KEY", "OKX_API_SECRET", "OKX_API_PASSPHRASE")
GOOD = EF.OKX_BODIES["config"]["data"][0]
ALGO = "/api/v5/trade/orders-algo-pending"


def _path(call: dict) -> str:
    return urlsplit(call["url"]).path


def _query(call: dict) -> str:
    return urlsplit(call["url"]).query


def _run(routes: dict, usdt_krw: float | None = 1400.0, **key_changes):
    """One snapshot at EF.NOW under the fake keys (a keyword changes one; None removes it); (snapshot, calls)."""
    with EF.fake_keys(**key_changes), EF.serve(routes) as calls:
        snap = okx_inquiry.snapshot(EF.NOW, usdt_krw)
    return snap, calls


def _time(offset_ms: int) -> dict:
    return {"code": "0", "msg": "", "data": [{"ts": str(EF.NOW_MS + offset_ms)}]}


def _config(**changes) -> dict:
    return {"code": "0", "msg": "", "data": [dict(GOOD, **changes)]}


def _algo(answers: dict):
    """An orders-algo-pending route that answers each ordType from `answers` (default: no rows)."""
    def answer(call):
        kind = dict(parse_qsl(_query(call)))["ordType"]
        body = answers.get(kind, {"code": "0", "msg": "", "data": []})
        return 200, {"Date": EF.DATE_HEADER}, json.dumps(body).encode("utf-8")
    return answer


def _rows(name: str, *rows) -> dict:
    return {"code": "0", "msg": "", "data": list(rows) if rows else [dict(EF.OKX_ROWS[name])]}


def test_self_check_passes_only_exact_read_only_spot_without_borrow_and_with_an_ip():
    assert okx_inquiry.SELF_CHECK == ("perm", "acctLv", "enableSpotBorrow", "autoLoan", "ip")
    assert okx_inquiry.self_check(GOOD) == frozenset()
    for perm in ("read_only,trade", "trade", "", "read_only,transfer", "read_only,withdraw", "Read_only", "readonly",
                 " read_only", None, ["read_only"]):
        assert okx_inquiry.self_check(dict(GOOD, perm=perm)) == frozenset({"okx_perm"}), perm
    missing = dict(GOOD)
    del missing["perm"]
    assert okx_inquiry.self_check(missing) == frozenset({"okx_perm"})
    for value in ("2", "3", "4", 1, ""):
        assert okx_inquiry.self_check(dict(GOOD, acctLv=value)) == frozenset({"okx_acct_lv"}), value
    for value in (True, "false", 0, None):
        assert okx_inquiry.self_check(dict(GOOD, enableSpotBorrow=value)) == frozenset({"okx_spot_borrow"}), value
        assert okx_inquiry.self_check(dict(GOOD, autoLoan=value)) == frozenset({"okx_auto_loan"}), value
    for value in ("", None, ["203.0.113.7"]):
        assert okx_inquiry.self_check(dict(GOOD, ip=value)) == frozenset({"okx_no_ip"}), value
    assert okx_inquiry.self_check({}) == frozenset({"okx_perm", "okx_acct_lv", "okx_spot_borrow", "okx_auto_loan",
                                                    "okx_no_ip"})


def test_no_keys_means_no_call_at_all():
    for name in OKX_KEYS:
        snap, calls = _run(EF.okx_routes(), **{name: None})
        assert calls == [], [_path(c) for c in calls]           # not even the public time (E32)
        assert not snap.ok and snap.flags == frozenset({"keys_missing"}) and snap.error == f"keys missing: {name}"
        assert transport._okx_offset_s is None


def test_a_failed_self_check_stops_after_account_config():
    for changes, flags, names in (({"perm": "read_only,trade"}, {"okx_perm"}, "perm"),
                                  ({"acctLv": "2", "autoLoan": True}, {"okx_acct_lv", "okx_auto_loan"},
                                   "acctLv, autoLoan"),
                                  ({"perm": "trade", "acctLv": "2"}, {"okx_perm", "okx_acct_lv"},
                                   "perm, acctLv"),                    # SELF_CHECK order, not sorted
                                  ({"enableSpotBorrow": True, "ip": ""}, {"okx_spot_borrow", "okx_no_ip"},
                                   "enableSpotBorrow, ip")):
        snap, calls = _run(EF.okx_routes(config=_config(**changes)))
        assert [_path(c) for c in calls] == [PATH["time"], PATH["config"]]     # nothing after the self-check
        assert not snap.ok and snap.flags == frozenset(flags), snap.flags
        assert snap.error == f"okx self-check failed: {names}", snap.error
        assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
        assert snap.holdings == {} and snap.response_sha256 == {}


def test_public_time_comes_first_and_sets_the_offset():
    snap, calls = _run(EF.okx_routes(time=_time(3000)))
    assert snap.ok, snap.error
    assert [_path(c) for c in calls[:2]] == [PATH["time"], PATH["config"]]
    assert snap.server_utc == "2026-10-24T00:00:03Z" and snap.clock_offset_s == 3.0
    assert transport._okx_offset_s == 3.0                        # transport's own copy gates every signed call


def test_an_offset_above_25_s_refuses_every_signed_call_with_no_key_read():
    reads, saved = [], keys.read

    def recording(names):
        reads.append(tuple(names))
        return saved(names)
    for offset_ms in (25001, -25001, 120000, -120000):
        reads.clear()
        keys.read = recording
        try:
            snap, calls = _run(EF.okx_routes(time=_time(offset_ms)))
        finally:
            keys.read = saved
        assert [_path(c) for c in calls] == [PATH["time"]], [_path(c) for c in calls]   # no signed call sent
        assert reads == [OKX_KEYS], reads                        # require_keys only: no key read after the time
        assert not snap.ok and snap.flags == frozenset() and "above 25 s; OKX requests not sent" in snap.error
        assert round(snap.clock_offset_s, 3) == offset_ms / 1000   # kept, so CLOCK_SKEW sees it (E39)
    for offset_ms in (25000, -25000):                             # exactly 25 s either way is still within the limit
        snap, _calls = _run(EF.okx_routes(time=_time(offset_ms)))
        assert snap.ok, (offset_ms, snap.error)


def test_an_absurd_server_time_fails_okx_closed():
    snap, calls = _run(EF.okx_routes(time={"code": "0", "msg": "", "data": [{"ts": "1000000000000000"}]}))
    assert [_path(c) for c in calls] == [PATH["time"]]           # year 33658: no signed call follows
    assert not snap.ok and snap.error == "okx: /api/v5/public/time: OverflowError", snap.error   # contained


def test_the_call_order_and_one_algo_call_per_ordtype():
    snap, calls = _run(EF.okx_routes())
    assert snap.ok, snap.error
    algo = [(PATH["orders_algo_pending"], f"ordType={t}") for t in okx_inquiry.ALGO_TYPES]
    assert [(_path(c), _query(c)) for c in calls] == (
        [(PATH["time"], ""), (PATH["config"], "")]
        + [(PATH[n], "ccy=USDT" if n == "asset_valuation" else "") for n in SIGNED_BEFORE_ALGO] + algo
        + [(PATH[n], "instId=BTC-USDT" if n == "ticker" else "") for n in AFTER_ALGO])
    assert len(okx_inquiry.ALGO_TYPES) == 7
    assert all("," not in _query(c) for c in calls if _path(c) == ALGO)   # never a comma list (E25)
    keyed = {f"{ALGO}?ordType={t}" for t in okx_inquiry.ALGO_TYPES}
    plain = {PATH[n] for n in ("time", "config") + SIGNED_BEFORE_ALGO + AFTER_ALGO}
    assert set(snap.response_sha256) == keyed | plain, sorted(snap.response_sha256)   # each algo call its own key
    raw = {f"{ALGO}?ordType=oco": b'{"code": "0", "msg": "", "data": []} '}

    def answer(call):
        key = f"{_path(call)}?{_query(call)}"
        return 200, {"Date": EF.DATE_HEADER}, raw.get(key, b'{"code": "0", "msg": "", "data": []}')
    snap, _calls = _run(EF.okx_routes(orders_algo_pending=answer))
    hashes = snap.response_sha256
    assert hashes[f"{ALGO}?ordType=oco"] == hashlib.sha256(raw[f"{ALGO}?ordType=oco"]).hexdigest()
    assert hashes[f"{ALGO}?ordType=oco"] != hashes[f"{ALGO}?ordType=twap"]


def test_signed_calls_carry_the_okx_headers_and_no_demo_header():
    snap, calls = _run(EF.okx_routes())
    assert snap.ok, snap.error
    public = {PATH["time"], PATH["ticker"]}
    for call in calls:
        names = {k.lower() for k in call["headers"]}
        assert not any("simulated" in n for n in names), names   # never the demo header, on any call
        if _path(call) in public:
            assert not any(n.startswith("ok-access") for n in names), names
            continue
        head = call["headers"]
        assert head["OK-ACCESS-KEY"] == EF.FAKE_KEYS["OKX_API_KEY"]
        assert head["OK-ACCESS-PASSPHRASE"] == EF.FAKE_KEYS["OKX_API_PASSPHRASE"]
        assert head["OK-ACCESS-TIMESTAMP"] == "2026-10-24T00:00:00.000Z"
        target = _path(call) + (f"?{_query(call)}" if _query(call) else "")
        want = base64.b64encode(hmac.new(EF.FAKE_KEYS["OKX_API_SECRET"].encode(),
                                         f"2026-10-24T00:00:00.000ZGET{target}".encode(), hashlib.sha256).digest())
        assert head["OK-ACCESS-SIGN"] == want.decode("ascii"), target


def test_the_full_fixture_gives_every_field():
    fill, algo = EF.OKX_BODIES["fills"]["data"][0], EF.OKX_ROWS["orders_algo_pending"]
    snap, _calls = _run(EF.okx_routes(
        withdrawal_history=_rows("withdrawal_history", dict(EF.OKX_ROWS["withdrawal_history"], fee="0.00002")),
        orders_pending=_rows("orders_pending", dict(EF.OKX_ROWS["orders_pending"], side="sell")),
        orders_algo_pending=_algo({"conditional": _rows("orders_algo_pending"),
                                   "trigger": _rows("orders_algo_pending", dict(algo, algoId="a2", px=""))}),
        fills=_rows("fills", fill, dict(fill, tradeId="f2", side="sell", fillSz="0.00005"))))
    assert snap.ok and snap.error is None and snap.flags == frozenset(), snap.error
    assert snap.venue == "okx" and snap.utc == "2026-10-24T00:00:00Z"
    assert snap.server_utc == "2026-10-24T00:00:00Z" and snap.clock_offset_s == 0.0
    assert dict(snap.holdings) == {"USDT": Holding(units=10.0, locked=0.0), "BTC": Holding(units=0.0001, locked=0.0)}
    assert dict(snap.cash) == {} and snap.deposit_krw is None    # coins, USDT included, are holdings (E16)
    assert dict(snap.prices_krw) == {"USDT": 1400.0, "USDC": 1400.0, "BTC": 70000.0 * 1400.0}
    assert snap.open_orders == (Order(id="o1", symbol="BTC", side="sell", units=0.0001, price=60000.0),
                                Order(id="a1", symbol="BTC", side="buy", units=0.0001, price=60000.0),
                                Order(id="a2", symbol="BTC", side="buy", units=0.0001, price=None))   # px "": None
    assert snap.fills == (Move(id="f1", symbol="BTC", counter="USDT", side="buy", units=0.0001),
                          Move(id="f2", symbol="BTC", counter="USDT", side="sell", units=0.00005))
    assert snap.deposits == (Move(id="d1", symbol="USDT", side="in", units=10.0),)
    assert snap.withdrawals == (Move(id="w1", symbol="BTC", side="out", units=0.0001),)   # amt, never the fee
    assert dict(snap.loans) == {"liab:USDT": 0.0} and dict(snap.earn) == {"asset_valuation": 0.0}
    assert snap.withdrawal_addresses == () and snap.key_expiry is None   # OKX lists no address book


def test_holdings_merge_trading_and_funding():
    routes = EF.okx_routes()
    routes[EF.OKX_ROUTES["balance"]]["data"][0]["details"][0] |= {"cashBal": "10", "frozenBal": "4"}
    routes[EF.OKX_ROUTES["asset_balances"]]["data"] += [
        {"ccy": "USDT", "bal": "2.5", "frozenBal": "0.5", "availBal": "2"},
        {"ccy": "ETH", "bal": "0", "frozenBal": "0", "availBal": "0"}]
    snap, _calls = _run(routes)
    assert snap.ok, snap.error
    assert dict(snap.holdings) == {"USDT": Holding(units=12.5, locked=4.5), "BTC": Holding(units=0.0001, locked=0.0)}


def test_prices_come_from_the_upbit_usdt_price():
    for usdt_krw in (None, 0.0, -1.0, float("nan"), float("inf")):
        snap, _calls = _run(EF.okx_routes(), usdt_krw=usdt_krw)
        assert snap.ok and dict(snap.prices_krw) == {}, (usdt_krw, snap.prices_krw)   # positions then fail closed
    routes = EF.okx_routes()
    routes[EF.OKX_ROUTES["ticker"]]["data"][0]["last"] = "65000.5"
    snap, _calls = _run(routes, usdt_krw=1350.0)
    assert dict(snap.prices_krw) == {"USDT": 1350.0, "USDC": 1350.0, "BTC": 65000.5 * 1350.0}


def test_events_from_a_position_an_order_or_a_fill():
    events = {"instType": "EVENTS", "instId": "EV-1"}
    cases = (EF.okx_routes(positions=_rows("positions", dict(EF.OKX_ROWS["positions"], **events, pos="0"))),
             EF.okx_routes(orders_pending=_rows("orders_pending", dict(EF.OKX_ROWS["orders_pending"], **events))),
             EF.okx_routes(orders_algo_pending=_algo({"trigger": _rows(
                 "orders_algo_pending", dict(EF.OKX_ROWS["orders_algo_pending"], **events))})),
             EF.okx_routes(fills=_rows("fills", dict(EF.OKX_BODIES["fills"]["data"][0], **events))))
    for routes in cases:
        snap, _calls = _run(routes)
        assert snap.ok and snap.flags == frozenset({"EVENTS"}), (snap.error, snap.flags)


def test_derivative_position_only_from_a_nonzero_position():
    swap = dict(EF.OKX_ROWS["positions"])
    for row, flags in ((swap, {"derivative_position"}),
                       (dict(swap, pos="-2"), {"derivative_position"}),
                       (dict(swap, instType="FUTURES", instId="BTC-USD-261225"), {"derivative_position"}),
                       (dict(swap, instType="OPTION", instId="BTC-USD-261225-70000-C"), {"derivative_position"}),
                       (dict(swap, pos="0"), set())):
        snap, _calls = _run(EF.okx_routes(positions=_rows("positions", row)))
        assert snap.ok and snap.flags == frozenset(flags), (row["instType"], row["pos"], snap.flags)
        assert dict(snap.loans) == {"liab:USDT": 0.0}            # a derivative is no loan
    for kind in ("SWAP", "MARGIN"):                              # a size OKX left blank fails closed (E25)
        snap, _calls = _run(EF.okx_routes(positions=_rows("positions", dict(swap, instType=kind, pos=""))))
        assert not snap.ok and snap.error == f"okx: {PATH['positions']}: field pos", (kind, snap.error)


def test_loans_and_earn():
    routes = EF.okx_routes(
        positions=_rows("positions", dict(EF.OKX_ROWS["positions"], instType="MARGIN", instId="BTC-USDT",
                                          pos="-0.5"), dict(EF.OKX_ROWS["positions"], instType="MARGIN",
                                                            instId="ETH-USDT", pos="0")),
        savings=_rows("savings"),
        flexible_loan={"code": "0", "msg": "", "data": [{"loanData": [{"ccy": "USDT", "amt": "3"}],
                                                         "collateralData": [], "loanNotionalUsd": "3"}]})
    details = routes[EF.OKX_ROUTES["balance"]]["data"][0]["details"]
    details[0] |= {"liab": "1.5", "autoLendStatus": "active", "autoLendMtAmt": "2"}
    details.append(dict(details[0], ccy="USDC", cashBal="1", liab="", autoLendStatus="pending", autoLendMtAmt="0"))
    routes[EF.OKX_ROUTES["asset_valuation"]]["data"][0]["details"]["earn"] = "6"
    snap, _calls = _run(routes)
    assert snap.ok and snap.flags == frozenset(), (snap.error, snap.flags)   # MARGIN is a loan, not a derivative
    assert dict(snap.loans) == {"liab:USDT": 1.5, "liab:USDC": 0.0, "margin:BTC-USDT": 0.5,
                                "flexible_loan:USDT": 3.0}, snap.loans
    assert dict(snap.earn) == {"auto_lend:USDT": 2.0, "auto_lend:USDC": 1.0, "asset_valuation": 6.0,
                               "savings:USDT": 5.0}, snap.earn   # pending auto-lend with no matched amount: 1.0


def test_permission_codes_give_auth_error():
    for code in ("50120", "50123"):
        for name in ("config", "balance", "withdrawal_history"):
            body = dict(EF.OKX_ROWS["no_permission"], code=code)
            snap, calls = _run(EF.okx_routes(**{name: body}))
            assert not snap.ok and snap.flags == frozenset({"auth_error"}) and snap.error, (code, name, snap)
            assert _path(calls[-1]) == PATH[name]                # it stopped at the refused call
            assert "permission to use" not in snap.error         # the venue's message text never travels


def test_another_okx_code_fails_closed_without_auth_error():
    for name in ("config", "balance", "ticker"):
        snap, calls = _run(EF.okx_routes(**{name: {"code": "50011", "msg": "fixture text", "data": []}}))
        assert not snap.ok and snap.flags == frozenset() and "50011" in snap.error, (name, snap.error)   # E15
        assert _path(calls[-1]) == PATH[name] and "fixture text" not in snap.error


def test_a_malformed_field_fails_closed_with_names_only():
    cases = (("balance", {"code": "0", "msg": "", "data": [{"details": [{"ccy": "USDT", "cashBal": "1e999",
                                                                          "frozenBal": "0", "liab": "",
                                                                          "autoLendStatus": "off",
                                                                          "autoLendMtAmt": "0"}]}]},
              PATH["balance"], "field cashBal"),
             ("asset_balances", {"code": "0", "msg": "", "data": [{"ccy": "BTC", "bal": 0.0001, "frozenBal": "0"}]},
              PATH["asset_balances"], "field bal"),
             ("fills", _rows("fills", dict(EF.OKX_BODIES["fills"]["data"][0], instId="BTCUSDT")), PATH["fills"],
              "field instId"),
             ("asset_valuation", {"code": "0", "msg": "", "data": [{"details": {"funding": "7"}}]},
              PATH["asset_valuation"], "field earn"),
             ("flexible_loan", {"code": "0", "msg": "", "data": [{"loanData": "none"}]}, PATH["flexible_loan"],
              "field loanData"),
             ("ticker", {"code": "0", "msg": "", "data": []}, PATH["ticker"], "field data"))
    for name, body, path, tail in cases:
        snap, _calls = _run(EF.okx_routes(**{name: body}))
        assert not snap.ok and snap.flags == frozenset(), name
        assert snap.error == f"okx: {path}: {tail}", snap.error
        assert "1e999" not in snap.error and "0.0001" not in snap.error


def test_a_refused_send_propagates():
    with EF.fake_keys():
        try:
            okx_inquiry.snapshot(EF.NOW, 1400.0)                 # no serve(): the suite's refusing stub answers
        except EF.Refused:
            pass
        else:
            raise AssertionError("a refused send became a snapshot")
    assert len(EF.STRAYS) == 1 and EF.STRAYS[0].endswith(PATH["time"]), EF.STRAYS   # the public time, refused
    EF.STRAYS.clear()
