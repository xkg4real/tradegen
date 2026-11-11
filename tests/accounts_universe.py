"""Upbit universe reads (spec sections 5, 7 and 9): synthetic public answers through the fake transport._send only;
no venue call, key or file write."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json
from unittest.mock import patch
from urllib.parse import parse_qsl

from core.compliance import rules
from execution_accounts import universe as U
from tests import execution_fixtures as F

DAY = date(2026, 11, 11)                                    # candle day D, a Wednesday
BUILT = datetime(2026, 11, 11, 0, 12, tzinfo=timezone.utc)  # 09:12 KST, the scheduled build
BUILT_HEADER = "Wed, 11 Nov 2026 00:12:00 GMT"
LISTED = date(2020, 1, 1)
RULE = rules.UniverseRule(source="https://docs.upbit.com/kr/reference/list-trading-pairs", quote="KRW",
                          exclude=("USDT", "USDC"), min_listing_days=250, median_days=30,
                          min_median_value_krw=1_000_000_000)
CAUTION_KEYS = ("PRICE_FLUCTUATIONS", "TRADING_VOLUME_SOARING", "DEPOSIT_AMOUNT_SOARING",
                "GLOBAL_PRICE_DIFFERENCES", "CONCENTRATION_OF_SMALL_ACCOUNTS")


def market(name, *, warning=False, caution=()):
    """One market/all?is_details=true row."""
    return {"market": name, "korean_name": name, "english_name": name,
            "market_event": {"warning": warning, "caution": {key: key in caution for key in CAUTION_KEYS}}}


MARKETS = (market("KRW-BTC"), market("KRW-ETH"), market("KRW-USDT"),
           market("KRW-XYZ", caution=("PRICE_FLUCTUATIONS",)), market("BTC-ETH"))
MARKET_ALL_RAW = json.dumps(list(MARKETS)).encode("utf-8")


def candle(name, day, *, value=2_000_000_000.0, opening=100, closing=101):
    """One daily-candle row dated `day` (UTC), with Upbit's field names."""
    return {"market": name, "candle_date_time_utc": day.isoformat() + "T00:00:00",
            "candle_date_time_kst": day.isoformat() + "T09:00:00", "opening_price": opening,
            "high_price": max(opening, closing), "low_price": min(opening, closing), "trade_price": closing,
            "timestamp": int(datetime(day.year, day.month, day.day, 23, 59, tzinfo=timezone.utc).timestamp()) * 1000,
            "candle_acc_trade_price": value, "candle_acc_trade_volume": 1.0}


def candle_server(listed_since, *, header=BUILT_HEADER, last=DAY - timedelta(days=1)):
    """A serve() callable for daily candles like Upbit: the `count` newest candles dated before `to` (exclusive),
    newest first, of a market whose candles run from `listed_since` to `last`; `header` None sends no Date."""
    def answer(call):
        query = dict(parse_qsl(call["query"]))
        newest = min(last, datetime.fromisoformat(query["to"]).date() - timedelta(days=1))
        days = [newest - timedelta(days=n) for n in range(int(query["count"]))]
        body = [candle(query["market"], day) for day in days if day >= listed_since]
        return 200, ({} if header is None else {"Date": header}), json.dumps(body).encode("utf-8")
    return answer


def routes(candles=None):
    """serve() routes of one healthy build at BUILT."""
    return {("GET", "/v1/market/all"): lambda call: (200, {"Date": BUILT_HEADER}, MARKET_ALL_RAW),
            ("GET", "/v1/candles/days"): candles or candle_server(LISTED)}


def refused(call, code):
    try:
        call()
    except U.UniverseReadError as exc:
        assert str(exc) == code, (str(exc), code)
    else:
        raise AssertionError(f"not refused: {code}")


def build():
    return U.build_universe_snapshot(RULE, DAY, clock=lambda: BUILT)


def test_builder_sends_exactly_the_rule_requests_and_returns_verified_bytes():
    with F.serve(routes()) as calls:
        raw, sha256 = build()
    expected = rules.universe_requests(RULE, MARKET_ALL_RAW, DAY)
    assert calls[0]["url"] == "https://api.upbit.com/v1/market/all?is_details=true"
    assert sorted((c["path"], tuple(parse_qsl(c["query"]))) for c in calls) == sorted(expected)
    assert len(calls) == len(expected) == 5          # market/all, then the age and value reads of KRW-BTC and KRW-ETH
    assert all(c["method"] == "GET" and "authorization" not in {k.lower() for k in c["headers"]} for c in calls)
    universe = rules.verify_universe_snapshot(raw, rules.universe_rule_sha256(RULE))
    assert universe.snapshot_sha256 == sha256 and universe.day == DAY
    assert universe.listed == ("KRW-BTC", "KRW-ETH", "KRW-USDT", "KRW-XYZ")
    assert universe.eligible == (("KRW-BTC", Decimal(2_000_000_000)), ("KRW-ETH", Decimal(2_000_000_000)))


def test_a_failed_read_fails_the_build_after_the_transport_retry_only():
    error = lambda call: (500, {"Date": BUILT_HEADER}, b'{"error":{"name":"server_error"}}')
    with F.serve(routes(error)) as calls:
        refused(build, "UNIVERSE_INQUIRY_FAILED")
    assert [c["path"] for c in calls] == ["/v1/market/all", "/v1/candles/days", "/v1/candles/days"]
    with F.serve({("GET", "/v1/market/all"): error}) as calls:
        refused(build, "UNIVERSE_INQUIRY_FAILED")
    assert [c["path"] for c in calls] == ["/v1/market/all", "/v1/market/all"]


def test_answers_without_server_time_or_over_the_body_cap_and_bad_inputs_are_refused():
    with F.serve(routes(candle_server(LISTED, header=None))):
        refused(build, "UNIVERSE_SERVER_TIME_REQUIRED")
    with F.serve(routes()), patch.object(U, "MAX_CANDLE_BODY", 64):
        refused(build, "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
    with F.serve(routes()), patch.object(U, "MAX_MARKET_ALL_BODY", len(MARKET_ALL_RAW) - 1):
        refused(build, "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
    for changes in ({"clock": None}, {"day": "2026-11-11"}, {"rule": None}):
        args = {"rule": RULE, "day": DAY, "clock": lambda: BUILT} | changes
        refused(lambda: U.build_universe_snapshot(args["rule"], args["day"], clock=args["clock"]),
                "UNIVERSE_INPUT_INVALID")
