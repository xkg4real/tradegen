"""Upbit KRW universe, pure compliance code (universe spec sections 4 and 5; plan PR 1): the flag classes, the
request set, finality from content, the medians, and the snapshot file with its verification. Every body is an
inline fixture; nothing reads the network, the clock or a file."""
from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from core.compliance import rules

CAUTIONS = ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING", "GLOBAL_PRICE_DIFFERENCES",
            "CONCENTRATION_OF_SMALL_ACCOUNTS")


def _entry(market: str, *, warning=False, **caution) -> dict:
    """One market object of market/all?is_details=true; every known caution key is false unless given."""
    return {"market": market, "korean_name": "x", "english_name": market.split("-")[-1],
            "market_event": {"warning": warning, "caution": {**{key: False for key in CAUTIONS}, **caution}}}


def _body(value) -> bytes:
    return json.dumps(value).encode("utf-8")


def _code(call) -> str:
    """The refusal code of the UniverseError that `call()` raises."""
    try:
        call()
    except rules.UniverseError as exc:
        return str(exc)
    raise AssertionError("accepted; expected UniverseError")


# -- flag classes (spec section 4) ---------------------------------------------------------------------------------
def test_flag_classes_follow_spec_4_exactly():
    assert rules.FLAG_CLASSES == ("unflagged", "warning", "caution", "unknown", "absent")
    assert rules.flag_class(_entry("KRW-BTC")) == "unflagged"
    assert rules.flag_class(None) == "absent"                                        # a missing coin
    assert rules.flag_class(_entry("KRW-BTC", warning=True)) == "warning"
    assert rules.flag_class(_entry("KRW-BTC", warning=True, PRICE_FLUCTUATIONS=True)) == "warning"
    for key in CAUTIONS:
        assert rules.flag_class(_entry("KRW-BTC", **{key: True})) == "caution", key
    assert rules.flag_class(_entry("KRW-BTC", NEW_CAUTION_KEY=True)) == "caution"   # an unknown key included
    assert rules.flag_class(_entry("KRW-BTC", NEW_CAUTION_KEY=False)) == "unflagged"


def test_flag_class_unknown_for_a_missing_or_malformed_field():
    no_event = _entry("KRW-BTC")
    del no_event["market_event"]
    assert rules.flag_class(no_event) == "unknown"                                   # a missing market_event
    calm = {key: False for key in CAUTIONS}
    for event in (None, [], "warning", {"caution": calm}, {"warning": None, "caution": calm},
                  {"warning": 0, "caution": calm}, {"warning": "false", "caution": calm}, {"warning": False},
                  {"warning": False, "caution": None}, {"warning": False, "caution": []}):
        assert rules.flag_class({"market": "KRW-BTC", "market_event": event}) == "unknown", event
    for key in CAUTIONS:
        missing = _entry("KRW-BTC")
        del missing["market_event"]["caution"][key]
        assert rules.flag_class(missing) == "unknown", key                           # a missing key
        for bad in (None, 0, 1, "false", "true"):
            assert rules.flag_class(_entry("KRW-BTC", **{key: bad})) == "unknown", (key, bad)   # not a boolean
    assert rules.flag_class([]) == rules.flag_class("KRW-BTC") == "unknown"         # not a market object


def test_flag_class_overlap_rulings_are_pinned():
    # 1. a warning that is exactly true gives "warning" whatever the caution object looks like
    for caution in (None, [], "x", 1, {}):
        entry = {"market": "KRW-BTC", "market_event": {"warning": True, "caution": caution}}
        assert rules.flag_class(entry) == "warning", caution
    missing = {"market": "KRW-BTC", "market_event": {"warning": True}}
    assert rules.flag_class(missing) == "warning"
    # 2. a missing or non-boolean known key gives "unknown" even when another known key is true
    for key in CAUTIONS:
        other = next(k for k in CAUTIONS if k != key)
        gone = _entry("KRW-BTC", **{other: True})
        del gone["market_event"]["caution"][key]
        assert rules.flag_class(gone) == "unknown", key
        assert rules.flag_class(_entry("KRW-BTC", **{key: 1, other: True})) == "unknown", key
    # 3. an unknown key is ignored unless exactly true
    for value in ("yes", 1, None, "true", [True]):
        assert rules.flag_class(_entry("KRW-BTC", NEW=value)) == "unflagged", value
    assert rules.flag_class(_entry("KRW-BTC", NEW=True)) == "caution"


def test_market_flags_reads_krw_markets_and_refuses_a_bad_body():
    assert issubclass(rules.UniverseError, ValueError)
    assert str(rules.UniverseError("UNIVERSE_BODY_INVALID")) == "UNIVERSE_BODY_INVALID"
    body = _body([_entry("KRW-BTC"), _entry("KRW-ADA", warning=True), _entry("KRW-DOGE", TRADING_VOLUME_SOARING=True),
                  {"market": "KRW-ETH"}, _entry("BTC-ETH"), _entry("USDT-BTC"), _entry("KRW-btc"),
                  _entry("KRW-ABCDEFGHIJKLM"), {"market": 1}, {"korean_name": "x"}])
    assert rules.market_flags(body) == {"KRW-BTC": "unflagged", "KRW-ADA": "warning", "KRW-DOGE": "caution",
                                        "KRW-ETH": "unknown"}
    assert rules.market_flags(b"[]") == {}
    for bad in (b"", b"{}", b"null", b'"KRW-BTC"', b"[1]", b'[["KRW-BTC"]]', b"[", b"\xff",
                b'[{"market": "KRW-BTC", "market": "KRW-ETH"}]', b'[{"market": "KRW-BTC", "x": NaN}]',
                b"[" * 100_000 + b"]" * 100_000, _body([_entry("KRW-BTC"), _entry("KRW-BTC")])):
        assert _code(lambda: rules.market_flags(bad)) == "UNIVERSE_BODY_INVALID", bad[:40]
    assert _code(lambda: rules.market_flags("[]")) == "UNIVERSE_BODY_INVALID"       # bytes only


# -- request set, receipts, finality and medians (spec section 5 "Requests", "Finality from content") -------------
D = date(2026, 11, 11)                                         # candle day D (UTC)
AT = datetime(2026, 11, 11, 0, 11, tzinfo=timezone.utc)        # every fixture receipt's server time: after D 00:10
SOURCE = "https://docs.upbit.com/kr/reference/list-trading-pairs"
RULE = rules.UniverseRule(source=SOURCE, quote="KRW", exclude=("USDC", "USDT"), min_listing_days=5, median_days=4,
                          min_median_value_krw=100)
RULE_SHA = rules.universe_rule_sha256(RULE)
AGE_TO, VALUE_TO = "2026-11-06T00:00:00Z", "2026-11-11T00:00:00Z"   # D - min_listing_days, and D
MARKETS = (_entry("KRW-BTC"), _entry("KRW-ETH"), _entry("KRW-SOL"), _entry("KRW-XRP"),
           _entry("KRW-ADA", warning=True), _entry("KRW-DOGE", TRADING_VOLUME_SOARING=True), _entry("KRW-USDT"),
           _entry("BTC-ETH"))                                  # KRW-BTC first: MARKETS[1:] drops a candidate
MENU = _body(MARKETS)
CANDIDATES = ("KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP")      # unflagged KRW markets that are not excluded
VALUES = {"KRW-BTC": {1: 400, 2: 300, 3: 200, 4: 100},         # n -> the value of day D-n; a missing n has no candle
          "KRW-ETH": {1: 50.5, 3: 1000, 4: 10},
          "KRW-SOL": {1: 150, 2: 150.5, 3: 99, 4: 151},
          "KRW-XRP": {1: 5000, 2: 5000, 3: 5000, 4: 5000}}
OLD = ("KRW-BTC", "KRW-ETH", "KRW-SOL")                         # KRW-XRP's age read comes back empty
LISTED = ("KRW-ADA", "KRW-BTC", "KRW-DOGE", "KRW-ETH", "KRW-SOL", "KRW-USDT", "KRW-XRP")
ELIGIBLE = (("KRW-BTC", Decimal(250)), ("KRW-SOL", Decimal("150.25")))   # KRW-ETH's median is 30.25 < 100


def _candle(market: str, day: date, value) -> dict:
    """One /v1/candles/days row: the fields the universe reads, plus one it ignores."""
    return {"market": market, "candle_date_time_utc": f"{day.isoformat()}T00:00:00", "candle_acc_trade_price": value,
            "candle_acc_trade_volume": 1.5}


def _stamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _receipt(path: str, params, body: bytes, server: datetime = AT) -> dict:
    """A plain receipt in live_history's 7-key shape."""
    return {"path": path, "params": [[k, v] for k, v in params], "account_scope": "public",
            "received_at": _stamp(server + timedelta(milliseconds=5)), "server_time": _stamp(server),
            "raw_body_b64": base64.b64encode(body).decode("ascii"), "sha256": hashlib.sha256(body).hexdigest()}


def _receipts(*, markets=MARKETS, values=VALUES, old=OLD, old_day=date(2026, 11, 5), server=AT, count=4) -> list:
    """market/all, then each candidate's age and value reads (newest candle first), as plain receipts."""
    out = [_receipt("/v1/market/all", [("is_details", "true")], _body(markets), server)]
    for market in CANDIDATES:
        age = [_candle(market, old_day, 1)] if market in old else []
        value = [_candle(market, D - timedelta(days=n), v) for n, v in sorted(values.get(market, {}).items())]
        out.append(_receipt("/v1/candles/days", [("market", market), ("to", AGE_TO), ("count", "1")], _body(age),
                            server))
        out.append(_receipt("/v1/candles/days", [("market", market), ("to", VALUE_TO), ("count", str(count))],
                            _body(value), server))
    return out


def _key(receipt: dict) -> tuple:
    return receipt["path"], tuple(tuple(pair) for pair in receipt["params"])


def _index(receipts: list, market: str, to: str) -> int:
    return next(i for i, r in enumerate(receipts) if ["market", market] in r["params"] and ["to", to] in r["params"])


def _value_error(call) -> None:
    """Asserts `call()` raises a plain ValueError: a caller's mistake, not a refusal code."""
    try:
        call()
    except rules.UniverseError as exc:
        raise AssertionError(f"a refusal code, not a caller error: {exc}") from None
    except ValueError:
        return
    raise AssertionError("accepted; expected ValueError")


def test_universe_requests_are_exactly_what_the_rule_implies():
    want = tuple(("/v1/candles/days", (("market", m), ("to", to), ("count", n)))
                 for m in CANDIDATES for to, n in ((AGE_TO, "1"), (VALUE_TO, "4")))
    want += (("/v1/market/all", (("is_details", "true"),)),)
    assert rules.universe_requests(RULE, MENU, D) == want
    assert tuple(sorted(_key(r) for r in _receipts())) == want
    spec = dataclasses.replace(RULE, min_listing_days=250, median_days=30, min_median_value_krw=1_000_000_000)
    assert rules.universe_requests(spec, _body([_entry("KRW-BTC")]), D) == (
        ("/v1/candles/days", (("market", "KRW-BTC"), ("to", "2026-03-06T00:00:00Z"), ("count", "1"))),
        ("/v1/candles/days", (("market", "KRW-BTC"), ("to", "2026-11-11T00:00:00Z"), ("count", "30"))),
        ("/v1/market/all", (("is_details", "true"),)))
    assert rules.universe_requests(dataclasses.replace(RULE, exclude=("BTC", "USDC", "USDT")), MENU, D) == want[2:]
    assert rules.universe_requests(RULE, b"[]", D) == want[-1:]
    assert rules.universe_requests(RULE, _body([_entry("KRW-BTC", PRICE_FLUCTUATIONS=None)]), D) == want[-1:]
    assert _code(lambda: rules.universe_requests(RULE, b"{}", D)) == "UNIVERSE_BODY_INVALID"
    _value_error(lambda: rules.universe_requests(RULE, MENU, datetime(2026, 11, 11, tzinfo=timezone.utc)))
    _value_error(lambda: rules.universe_requests(RULE, MENU, "2026-11-11"))
    _value_error(lambda: rules.universe_requests(dataclasses.asdict(RULE), MENU, D))
    for bad in ({"median_days": 0}, {"min_listing_days": 3651}, {"quote": "USDT"}, {"exclude": ("usdt",)},
                {"source": " "}, {"min_median_value_krw": True}):           # built in code, refused by the parser
        _value_error(lambda: rules.universe_requests(dataclasses.replace(RULE, **bad), MENU, D))
        _value_error(lambda: rules.universe_eligible(dataclasses.replace(RULE, **bad), _receipts(), D))


def test_universe_eligible_lists_krw_markets_and_takes_medians():
    listed, eligible = rules.universe_eligible(RULE, _receipts(), D)
    assert listed == LISTED and eligible == ELIGIBLE, (listed, eligible)
    assert all(type(median) is Decimal for _, median in eligible)

    def medians(values, rule=RULE, count=4):
        return rules.universe_eligible(rule, _receipts(values=values, count=count), D)[1]

    traded = {**VALUES, "KRW-ETH": {1: 50.5, 2: 300, 3: 1000, 4: 10}}          # [10, 50.5, 300, 1000]
    assert medians(traded) == (("KRW-BTC", Decimal(250)), ("KRW-ETH", Decimal("175.25")),
                               ("KRW-SOL", Decimal("150.25")))
    gaps = {**VALUES, "KRW-SOL": {1: 200, 4: 200}}                             # D-2, D-3 count as zero: [0, 0, 200, 200]
    assert medians(gaps) == (("KRW-BTC", Decimal(250)), ("KRW-SOL", Decimal(100)))   # 100 is not below 100
    older = {**VALUES, "KRW-BTC": {1: 400, 3: 200, 4: 100, 5: 10 ** 12}}        # D-5 is outside: [0, 100, 200, 400]
    assert medians(older)[0] == ("KRW-BTC", Decimal(150))
    odd = {m: {n: v for n, v in days.items() if n <= 3} for m, days in VALUES.items()}
    assert medians(odd, dataclasses.replace(RULE, median_days=3), 3) == (("KRW-BTC", Decimal(300)),
                                                                          ("KRW-SOL", Decimal(150)))
    assert rules.universe_eligible(dataclasses.replace(RULE, min_median_value_krw=251), _receipts(), D) == (LISTED, ())
    assert rules.universe_eligible(dataclasses.replace(RULE, min_median_value_krw=250), _receipts(), D) == (
        LISTED, (("KRW-BTC", Decimal(250)),))
    assert rules.universe_eligible(RULE, _receipts(old_day=date(2026, 11, 6)), D) == (LISTED, ())   # dated `to`
    assert rules.universe_eligible(RULE, _receipts(old=()), D) == (LISTED, ())
    _value_error(lambda: rules.universe_eligible(RULE, _receipts(), datetime(2026, 11, 11, tzinfo=timezone.utc)))


def test_finality_comes_from_content():
    utc = timezone.utc
    assert rules.universe_eligible(RULE, _receipts(server=datetime(2026, 11, 11, 0, 10, tzinfo=utc)), D) == (
        LISTED, ELIGIBLE)                                                       # built at D 00:10 exactly
    early = _receipts(server=datetime(2026, 11, 11, 0, 9, 59, 999999, tzinfo=utc))
    assert _code(lambda: rules.universe_eligible(RULE, early, D)) == "UNIVERSE_NOT_FINAL"

    def with_menu_at(moment: datetime) -> list:
        receipts = _receipts()
        receipts[0] = _receipt("/v1/market/all", [("is_details", "true")], MENU, moment)
        return receipts

    def with_value_read_at(moment: datetime) -> list:                          # one candle read stamped at `moment`
        receipts = _receipts()
        i = _index(receipts, "KRW-BTC", VALUE_TO)
        receipts[i] = _receipt("/v1/candles/days", [("market", "KRW-BTC"), ("to", VALUE_TO), ("count", "4")],
                               base64.b64decode(receipts[i]["raw_body_b64"]), moment)
        return receipts

    open_read = with_value_read_at(datetime(2026, 11, 10, 23, 59, 59, tzinfo=utc))   # the still-open D-1 candle
    assert _code(lambda: rules.universe_eligible(RULE, open_read, D)) == "UNIVERSE_NOT_FINAL"
    assert rules.universe_eligible(RULE, with_value_read_at(datetime(2026, 11, 11, tzinfo=utc)), D) == (
        LISTED, ELIGIBLE)
    stale = with_menu_at(datetime(2026, 11, 10, 23, 59, 59, tzinfo=utc))      # the list read before D 00:00
    assert _code(lambda: rules.universe_eligible(RULE, stale, D)) == "UNIVERSE_NOT_FINAL"
    assert rules.universe_eligible(RULE, with_menu_at(datetime(2026, 11, 11, tzinfo=utc)), D) == (LISTED, ELIGIBLE)
    for n in (0, -1):                                                          # a value candle dated D or D+1
        values = {**VALUES, "KRW-BTC": {n: 1, 1: 400, 2: 300, 3: 200}}
        assert _code(lambda: rules.universe_eligible(RULE, _receipts(values=values), D)) == "UNIVERSE_NOT_FINAL", n
    for day in (D, D + timedelta(days=1)):                                     # an age candle dated D or later
        assert _code(lambda: rules.universe_eligible(RULE, _receipts(old_day=day), D)) == "UNIVERSE_NOT_FINAL", day


def test_a_snapshot_cannot_add_drop_or_swap_a_receipt():
    good, mismatch = _receipts(), "UNIVERSE_REQUEST_SET_MISMATCH"

    def code(receipts) -> str:
        return _code(lambda: rules.universe_eligible(RULE, receipts, D))

    for i in range(len(good)):
        assert code(good[:i] + good[i + 1:]) == mismatch, i                   # any one dropped, market/all included
    assert code(good + [good[3]]) == mismatch                                  # one repeated
    assert code(good + [good[0]]) == mismatch                                  # two market/all reads
    ada = _receipt("/v1/candles/days", [("market", "KRW-ADA"), ("to", VALUE_TO), ("count", "4")], b"[]")
    assert code(good + [ada]) == mismatch                                      # a warning coin's read added
    i = _index(good, "KRW-XRP", VALUE_TO)
    swapped = list(good)
    swapped[i] = _receipt("/v1/candles/days", [("market", "KRW-XRP"), ("to", VALUE_TO), ("count", "30")], b"[]")
    assert code(swapped) == mismatch                                           # another count
    swapped[i] = {**good[i], "params": list(reversed(good[i]["params"]))}
    assert code(swapped) == mismatch                                           # the same pairs in another order
    swapped[i] = {**good[i], "path": "/v1/candles/minutes/1"}
    assert code(swapped) == mismatch                                           # another path
    menu = _receipt("/v1/market/all", [("is_details", "true")], _body(MARKETS[1:]))
    assert code([menu] + good[1:]) == mismatch                                 # KRW-BTC left the list
    flagged = (_entry("KRW-BTC", warning=True),) + MARKETS[1:]
    assert code(_receipts(markets=flagged)) == mismatch                        # KRW-BTC is now warning
    assert code(_receipts(markets=MARKETS + (_entry("KRW-TRX"),))) == mismatch    # a new candidate without its reads
    assert rules.universe_eligible(RULE, list(reversed(good)), D) == (LISTED, ELIGIBLE)    # the order is free


def test_a_tampered_or_malformed_receipt_is_refused():
    good, invalid = _receipts(), "UNIVERSE_RECEIPT_INVALID"
    i = _index(good, "KRW-XRP", AGE_TO)
    assert good[i]["raw_body_b64"] == "W10=" and base64.b64decode("W11=", validate=True) == b"[]"

    def refused(receipt) -> str:
        changed = list(good)
        changed[i] = receipt
        return _code(lambda: rules.universe_eligible(RULE, changed, D))

    for change in ({"raw_body_b64": base64.b64encode(b"[ ]").decode("ascii")},     # another body, the old hash
                   {"sha256": "0" * 64}, {"sha256": good[i]["sha256"].upper()}, {"sha256": 1},
                   {"raw_body_b64": "W11="}, {"raw_body_b64": "W10=="}, {"raw_body_b64": "W1 0="},
                   {"raw_body_b64": "W10"}, {"raw_body_b64": "W10=!"}, {"raw_body_b64": None},
                   {"account_scope": "account"}, {"path": None}, {"params": "market=KRW-XRP"},
                   {"params": [["market", "KRW-XRP", "x"]]}, {"params": [[1, 2]]},
                   {"received_at": "2026-11-11T00:11:00Z"}, {"server_time": "2026-11-11T00:11:00.000000+00:00"},
                   {"server_time": "2026-13-11T00:11:00.000000Z"}, {"server_time": None}):
        assert refused({**good[i], **change}) == invalid, change
    assert refused({**good[i], "note": "x"}) == invalid                        # an eighth key
    assert refused({k: v for k, v in good[i].items() if k != "received_at"}) == invalid
    for receipts in ("receipts", b"receipts", {"path": "/v1/market/all"}, [None], [1], [good[0], "x"]):
        assert _code(lambda: rules.universe_eligible(RULE, receipts, D)) == invalid, receipts


def test_candle_bodies_are_checked():
    receipts = _receipts()
    i = _index(receipts, "KRW-BTC", VALUE_TO)

    def code(body: bytes) -> str:
        changed = list(receipts)
        changed[i] = _receipt("/v1/candles/days", [("market", "KRW-BTC"), ("to", VALUE_TO), ("count", "4")], body)
        return _code(lambda: rules.universe_eligible(RULE, changed, D))

    day1, bad = D - timedelta(days=1), "UNIVERSE_BODY_INVALID"
    assert code(_body([_candle("KRW-BTC", D - timedelta(days=n), 1) for n in range(1, 6)])) == bad   # 5 rows, count 4
    assert code(_body([_candle("KRW-ETH", day1, 1)])) == bad                                         # another market
    assert code(_body([_candle("KRW-BTC", day1, 1), _candle("KRW-BTC", day1, 2)])) == bad            # a repeated day
    for start in ("2026-11-10T09:00:00", "2026-11-10", "2026-11-31T00:00:00", "2026-11-10T00:00:00Z", None):
        assert code(_body([{**_candle("KRW-BTC", day1, 1), "candle_date_time_utc": start}])) == bad, start
    for value in (-1, -0.5, True, "1000", None, [1]):
        assert code(_body([_candle("KRW-BTC", day1, value)])) == bad, value
    no_value = _candle("KRW-BTC", day1, 1)
    del no_value["candle_acc_trade_price"]
    assert code(_body([no_value])) == bad
    for raw in (b"{}", b"[1]", b"[", b"\xff", b"", b'[{"market": "KRW-BTC", "market": "KRW-BTC"}]',
                b'[{"market": "KRW-BTC", "candle_date_time_utc": "2026-11-10T00:00:00", '
                b'"candle_acc_trade_price": NaN}]'):
        assert code(raw) == bad, raw
    assert rules.universe_eligible(RULE, receipts, D) == (LISTED, ELIGIBLE)    # the untouched receipts still pass
