"""Upbit universe reads (spec sections 5, 7 and 9): synthetic public answers through the fake transport._send only;
no venue call, key or file write."""
from __future__ import annotations

import ast
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl

from core.compliance import rules
from execution import transport
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


NOW = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)       # 10:00 KST: bars through 2026-11-10 are final


def bars(markets, now, server):
    with F.serve({("GET", "/v1/candles/days"): server}) as calls:
        result = U.daily_bars(markets, now=now, clock=lambda: now)
    return result, calls


def test_daily_bars_pages_back_to_the_listing_and_returns_plain_final_bars():
    server = candle_server(date(2025, 8, 18))
    result, calls = bars(["KRW-BTC"], NOW, server)
    assert [tuple(parse_qsl(c["query"])) for c in calls] == [
        (("market", "KRW-BTC"), ("to", "2026-11-11T00:00:00Z"), ("count", "200")),
        (("market", "KRW-BTC"), ("to", "2026-04-25T00:00:00Z"), ("count", "200")),
        (("market", "KRW-BTC"), ("to", "2025-10-07T00:00:00Z"), ("count", "200"))]
    got = result["KRW-BTC"]
    assert list(result) == ["KRW-BTC"] and got.market == "KRW-BTC" and len(got.bars) == 450
    assert got.bars[0] == ("2025-08-18", 100.0, 101.0) and got.bars[-1] == ("2026-11-10", 100.0, 101.0)
    assert all(type(d) is str and type(o) is float and type(c) is float for d, o, c in got.bars)
    assert got.receipt_sha256 == tuple(hashlib.sha256(server(c)[2]).hexdigest() for c in calls)


def test_daily_bars_window_ends_at_the_last_final_utc_day_and_starts_3650_days_before_the_seoul_date():
    late = datetime(2026, 11, 10, 16, 0, tzinfo=timezone.utc)   # 01:00 KST on 2026-11-11
    result, calls = bars(("KRW-ETH",), late, candle_server(date(2026, 11, 1)))
    assert [dict(parse_qsl(c["query"]))["to"] for c in calls] == ["2026-11-10T00:00:00Z"]
    assert [bar[0] for bar in result["KRW-ETH"].bars] == [
        (date(2026, 11, 1) + timedelta(days=n)).isoformat() for n in range(9)]
    result, calls = bars(["KRW-BTC"], NOW, candle_server(date(2010, 1, 1)))
    assert len(calls) == 19 and dict(parse_qsl(calls[-1]["query"]))["count"] == "50"
    assert len(result["KRW-BTC"].bars) == 3650 and result["KRW-BTC"].bars[0][0] == "2016-11-13"


def test_daily_bars_drops_the_rows_the_odds_loader_drops():
    rows = [candle("KRW-BTC", date(2026, 11, 11)),                       # not final at NOW: outside the window
            candle("KRW-BTC", date(2026, 11, 10)),
            candle("KRW-BTC", date(2026, 11, 10), opening=7),             # a repeated date: the first row wins
            candle("KRW-BTC", date(2026, 11, 9), opening=0),              # a price not above 0
            candle("KRW-BTC", date(2026, 11, 8), closing=-1),
            candle("KRW-BTC", date(2026, 11, 7)) | {"candle_date_time_utc": "2026-11-31T00:00:00"},
            candle("KRW-BTC", date(2026, 11, 6))]
    raw = json.dumps(rows).encode("utf-8")
    result, calls = bars(["KRW-BTC"], NOW, lambda call: (200, {"Date": BUILT_HEADER}, raw))
    assert len(calls) == 1                                                # 7 rows < 200: a short page ends paging
    assert result["KRW-BTC"].bars == (("2026-11-06", 100.0, 101.0), ("2026-11-10", 100.0, 101.0))


def test_daily_bars_refuses_a_row_of_another_market():
    raw = json.dumps([candle("KRW-ETH", date(2026, 11, 10))]).encode("utf-8")
    page = lambda call: (200, {"Date": BUILT_HEADER}, raw)
    with F.serve({("GET", "/v1/candles/days"): page}) as calls:
        refused(lambda: U.daily_bars(["KRW-BTC"], now=NOW, clock=lambda: NOW), "UNIVERSE_CANDLES_INVALID")
    assert len(calls) == 1                                                # no stray call after the refusal


def test_daily_bars_refuses_malformed_pages_forged_receipts_and_bad_inputs():
    for raw in (b'{"not": "a list"}', b"[1]"):
        page = lambda call, raw=raw: (200, {"Date": BUILT_HEADER}, raw)
        with F.serve({("GET", "/v1/candles/days"): page}):
            refused(lambda: U.daily_bars(["KRW-BTC"], now=NOW, clock=lambda: NOW), "UNIVERSE_CANDLES_INVALID")
    forged = transport.Answer(body=[], server_utc=NOW, received_utc=NOW, sha256="0" * 64, raw_body=b"[]")
    with patch.object(U, "daily_candles", return_value=forged):
        refused(lambda: U.daily_bars(["KRW-BTC"], now=NOW, clock=lambda: NOW), "UNIVERSE_RECEIPT_INVALID")
    for call in (lambda: U.daily_bars([], now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-BTC", "KRW-BTC"], now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-KRW"], now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars("KRW-BTC", now=NOW, clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-BTC"], now=NOW.replace(tzinfo=None), clock=lambda: NOW),
                 lambda: U.daily_bars(["KRW-BTC"], now=NOW, clock=None)):
        refused(call, "UNIVERSE_INPUT_INVALID")


def test_universe_module_imports_only_public_helpers_and_no_odds_loader_data_or_config():
    """Spec 9: no core.oddsdata, data.* or config import. Spec 7: the source is keyless, so from the execution
    package it takes only the transport's Answer and inquiry_clock and the public upbit_inquiry helpers, never the
    keyed snapshot or current_terms."""
    tree = ast.parse(Path(U.__file__).read_text(encoding="utf-8"))
    plain = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    named = {(node.module or "", alias.name) for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
             for alias in node.names}
    modules = plain | {module for module, _name in named}
    assert not {m for m in modules if m.split(".")[0] in ("data", "config") or m.startswith("core.oddsdata")}, modules
    public = {("execution.transport", "Answer"), ("execution.transport", "inquiry_clock")} | {
        ("execution.upbit_inquiry", name) for name in ("CANDLE_COUNT_MAX", "CANDLES_DAYS_PATH", "MARKET_ALL_PATH",
                                                        "candle_params", "daily_candles", "market_all", "tickers")}
    assert {pair for pair in named if pair[0].split(".")[0] == "execution"} <= public, named
    assert not {m for m in plain if m.split(".")[0] == "execution"}, plain


TRADE_MS = int(BUILT.timestamp()) * 1000


def ticker(name, price):
    """One ticker row."""
    return {"market": name, "trade_price": price, "trade_timestamp": TRADE_MS, "timestamp": TRADE_MS}


def answered(raw):
    return lambda call: (200, {"Date": BUILT_HEADER}, raw)


def unavailable(read):
    mapping = read.flags if type(read) is U.FlagRead else read.prices
    return read.ok is False and read.received_at is None and read.sha256 is None and dict(mapping) == {}


def test_slot_source_reads_flags_and_prices_with_one_public_get_each():
    ticker_raw = json.dumps([ticker("KRW-BTC", 101), ticker("KRW-ETH", 2.5)]).encode("utf-8")
    source = U.UniverseSlotSource(clock=lambda: BUILT)
    with F.serve({("GET", "/v1/market/all"): answered(MARKET_ALL_RAW),
                  ("GET", "/v1/ticker"): answered(ticker_raw)}) as calls:
        flags, prices = source.read_flags(), source.read_tickers(("KRW-BTC", "KRW-ETH"))
    assert [c["url"] for c in calls] == ["https://api.upbit.com/v1/market/all?is_details=true",
                                         "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH"]
    assert all("authorization" not in {k.lower() for k in c["headers"]} for c in calls)
    assert flags.ok and flags.received_at == BUILT and flags.sha256 == hashlib.sha256(MARKET_ALL_RAW).hexdigest()
    assert dict(flags.flags) == {"KRW-BTC": "unflagged", "KRW-ETH": "unflagged", "KRW-USDT": "unflagged",
                                 "KRW-XYZ": "caution"}
    assert prices.ok and prices.received_at == BUILT and prices.sha256 == hashlib.sha256(ticker_raw).hexdigest()
    assert dict(prices.prices) == {"KRW-BTC": (Decimal(101), BUILT), "KRW-ETH": (Decimal("2.5"), BUILT)}


def test_slot_source_failures_are_unavailable_reads_never_exceptions():
    source = U.UniverseSlotSource(clock=lambda: BUILT)
    error = lambda call: (500, {"Date": BUILT_HEADER}, b'{"error":{"name":"server_error"}}')
    with F.serve({("GET", "/v1/market/all"): error, ("GET", "/v1/ticker"): error}) as calls:
        assert unavailable(source.read_flags()) and unavailable(source.read_tickers(["KRW-BTC"]))
    assert len(calls) == 4                                    # each GET once more after the 5xx, nothing else
    with F.serve({("GET", "/v1/market/all"): answered(b'{"market": "KRW-BTC"}')}):
        assert unavailable(source.read_flags())
    for markets in ([], ["KRW-BTC", "KRW-BTC"], ["KRW-btc"], "KRW-BTC"):
        assert unavailable(source.read_tickers(markets))      # refused before any send
    for rows in ([ticker("KRW-ETH", 1)], [ticker("KRW-BTC", 1), ticker("KRW-BTC", 1)], [ticker("KRW-BTC", 0)],
                 [ticker("KRW-BTC", 1) | {"trade_timestamp": "1"}], [{"market": "KRW-BTC"}], {"KRW-BTC": 1}, ["row"]):
        with F.serve({("GET", "/v1/ticker"): answered(json.dumps(rows).encode("utf-8"))}):
            assert unavailable(source.read_tickers(["KRW-BTC"])), rows
    with F.serve({("GET", "/v1/ticker"): answered(json.dumps([ticker("KRW-BTC", 1)]).encode("utf-8"))}),             patch.object(U, "MAX_TICKER_BODY", 8):
        assert unavailable(source.read_tickers(["KRW-BTC"]))
    with F.serve({("GET", "/v1/market/all"): answered(MARKET_ALL_RAW)}), patch.object(U, "MAX_MARKET_ALL_BODY", 8):
        assert unavailable(source.read_flags())
    refused(lambda: U.UniverseSlotSource(clock=None), "UNIVERSE_CLOCK_REQUIRED")
