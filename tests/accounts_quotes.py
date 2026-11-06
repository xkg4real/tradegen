"""Synthetic public book receipts and fake E1 HTTP only; no venue calls or keys."""
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal, localcontext
import hashlib
import json
from unittest.mock import patch

from execution import keys, transport
from execution_accounts.collector import SourceReceipt
from execution_accounts.quotes import E1UpbitQuoteSource, QuoteError, parse_orderbook, to_runner_quote
from execution_network.route import ManagedRoute, route_options
from tests import execution_fixtures as F

D = Decimal
NOW = F.NOW
PARAMS = (("markets", "KRW-BTC"), ("level", "0"), ("count", "30"))


def body():
    return [dict(market="KRW-BTC", timestamp=int(NOW.timestamp()) * 1000, level=0,
        total_ask_size=10, total_bid_size=12, orderbook_units=[
            dict(ask_price=101, bid_price=99, ask_size=2, bid_size=3),
            dict(ask_price=102, bid_price=98, ask_size=4, bid_size=5)])]


def receipt(value=None, *, raw=None, **changes):
    raw = json.dumps(body() if value is None else value, separators=(",", ":")).encode() if raw is None else raw
    return SourceReceipt(**(dict(path="/v1/orderbook", params=PARAMS, account_scope="public-upbit-orderbook",
        received_at=NOW, server_time=NOW, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest()) | changes))


def parse(value=None, **kwargs):
    return parse_orderbook(receipt(value), symbol="KRW-BTC", now=kwargs.get("now", NOW))


def refusal(call, code):
    try:
        call()
    except QuoteError as exc:
        assert str(exc) == code, (str(exc), code)
        return
    raise AssertionError("expected quote refusal")


def test_native_book_retains_best_prices_sizes_depth_and_raw_receipt():
    book = parse()
    assert (book.bid, book.ask, book.bid_size, book.ask_size) == (D(99), D(101), D(3), D(2))
    assert book.midpoint == D(100) and len(book.levels) == 2
    assert book.total_ask_size == 10 and book.total_bid_size == 12
    assert book.asof == NOW and book.received_at == NOW and book.server_time == NOW
    assert book.source_sha256 == hashlib.sha256(book.receipt.raw_body).hexdigest()
    assert "raw_body" not in repr(book) and "orderbook_units" not in repr(book.receipt)


def test_wire_decimal_precision_survives_small_ambient_context():
    raw = json.dumps(body(), separators=(",", ":")).encode().replace(
        b'"ask_price":101', b'"ask_price":100.123456789012345678901234567890').replace(
        b'"bid_price":99', b'"bid_price":99.123456789012345678901234567890')
    with localcontext() as numeric:
        numeric.prec = 6
        book = parse_orderbook(receipt(raw=raw), symbol="KRW-BTC", now=NOW)
        assert book.ask == D("100.123456789012345678901234567890")
        assert book.bid == D("99.123456789012345678901234567890")
        assert book.midpoint == D("99.623456789012345678901234567890")


def test_construction_is_inert_and_requires_one_fixed_krw_market_and_explicit_clock():
    with patch("execution_accounts.quotes.request") as send:
        source = E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW)
        assert source.symbol == "KRW-BTC" and not send.called
        for symbol in ("BTC-KRW", "USDT-BTC", "krw-btc", "KRW-KRW", "KRW-BTC,KRW-ETH", "KRW-BTC/x", "https://x"):
            refusal(lambda: E1UpbitQuoteSource(symbol=symbol, clock=lambda: NOW), "QUOTE_KRW_SYMBOL_REQUIRED")
        refusal(lambda: E1UpbitQuoteSource(symbol="KRW-BTC", clock=None), "QUOTE_CLOCK_REQUIRED")
        refusal(lambda: E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW, route={}), "QUOTE_ROUTE_INVALID")
        assert not send.called


def test_receipt_requires_exact_scope_path_parameters_digest_and_unique_json():
    good = receipt()
    for changed in (replace(good, path="/v1/ticker"), replace(good, account_scope="other"),
                    replace(good, params=(("markets", "KRW-ETH"), ("level", "0"), ("count", "30"))),
                    replace(good, params=PARAMS + (("level", "0"),)), replace(good, params=list(PARAMS))):
        refusal(lambda: parse_orderbook(changed, symbol="KRW-BTC", now=NOW), "QUOTE_RECEIPT_SCOPE_MISMATCH")
    for changed in (replace(good, sha256="a"*64), receipt(raw=b'[{"market":"KRW-BTC","market":"KRW-ETH"}]'),
                    receipt(raw=b'[NaN]'), receipt(raw=b'[Infinity]'), receipt(raw=b'\xff')):
        refusal(lambda: parse_orderbook(changed, symbol="KRW-BTC", now=NOW), "QUOTE_RECEIPT_INVALID")
    for raw in (b"", b" "*131073):
        refusal(lambda: parse_orderbook(receipt(raw=raw), symbol="KRW-BTC", now=NOW),
                "QUOTE_BODY_TOO_LARGE_OR_EMPTY")


def test_market_cardinality_and_native_level_are_required():
    for value in ([], body()*2, {}, [None]):
        refusal(lambda: parse(value), "QUOTE_SINGLE_BOOK_REQUIRED")
    value = body(); value[0]["market"] = "KRW-ETH"
    refusal(lambda: parse(value), "QUOTE_MARKET_MISMATCH")
    value = body(); value[0]["level"] = 1000
    refusal(lambda: parse(value), "QUOTE_AGGREGATED_DEPTH_REFUSED")
    for level in ("0", False, None):
        value = body(); value[0]["level"] = level
        refusal(lambda: parse(value), "QUOTE_EXACT_NUMBER_REQUIRED")


def test_quote_and_receipt_freshness_do_not_relabel_exchange_time():
    for delta in (-10001, 1):
        value = body(); value[0]["timestamp"] += delta
        refusal(lambda: parse(value), "QUOTE_BOOK_STALE_OR_FUTURE")
    value = body(); value[0]["timestamp"] -= 10000
    assert parse(value).asof == NOW-timedelta(seconds=10)
    refusal(lambda: parse(value, now=NOW+timedelta(milliseconds=1)), "QUOTE_BOOK_STALE_OR_FUTURE")
    refusal(lambda: parse(now=NOW+timedelta(seconds=11)), "QUOTE_RECEIPT_STALE_OR_FUTURE")
    refusal(lambda: parse(now=NOW-timedelta(microseconds=1)), "QUOTE_RECEIPT_STALE_OR_FUTURE")


def test_timestamp_and_server_clock_require_aware_supported_values():
    for stamp in (True, "1", 0, -1, 2**63, 2**63-1):
        value = body(); value[0]["timestamp"] = stamp
        refusal(lambda: parse(value), "QUOTE_TIMESTAMP_INVALID")
    for changes in ({"received_at": NOW.replace(tzinfo=None)}, {"server_time": None}):
        refusal(lambda: parse_orderbook(receipt(**changes), symbol="KRW-BTC", now=NOW), "QUOTE_AWARE_TIME_REQUIRED")
    for delta in (-61, 61):
        refusal(lambda: parse_orderbook(receipt(server_time=NOW+timedelta(seconds=delta)),
                                        symbol="KRW-BTC", now=NOW), "QUOTE_SERVER_CLOCK_MISMATCH")


def test_empty_oversized_unordered_duplicate_locked_and_crossed_depth_refuse():
    for units in ([], body()[0]["orderbook_units"] * 16):
        value = body(); value[0]["orderbook_units"] = units
        refusal(lambda: parse(value), "QUOTE_DEPTH_EMPTY_OR_OVERSIZED")
    for key, amount in (("ask_price", 101), ("ask_price", 100), ("bid_price", 99), ("bid_price", 100)):
        value = body(); value[0]["orderbook_units"][1][key] = amount
        refusal(lambda: parse(value), "QUOTE_DEPTH_NOT_STRICTLY_ORDERED")
    for amount in (101, 102):
        value = body(); value[0]["orderbook_units"][0]["bid_price"] = amount
        refusal(lambda: parse(value), "QUOTE_LOCKED_OR_CROSSED_BOOK")
    value = body(); value[0]["orderbook_units"] = [None]
    refusal(lambda: parse(value), "QUOTE_LEVEL_INVALID")


def test_nonpositive_non_numeric_and_unbounded_amounts_refuse():
    for amount, code in ((0, "QUOTE_AMOUNT_INVALID"), (-1, "QUOTE_AMOUNT_INVALID"),
                         (True, "QUOTE_EXACT_NUMBER_REQUIRED"), ("2", "QUOTE_EXACT_NUMBER_REQUIRED"),
                         (None, "QUOTE_EXACT_NUMBER_REQUIRED"), (10**61, "QUOTE_NUMBER_RANGE")):
        value = body(); value[0]["orderbook_units"][0]["ask_size"] = amount
        refusal(lambda: parse(value), code)
    raw = receipt().raw_body.replace(b'"ask_size":2', b'"ask_size":1e-41')
    refusal(lambda: parse_orderbook(receipt(raw=raw), symbol="KRW-BTC", now=NOW), "QUOTE_NUMBER_RANGE")


def test_total_depth_cannot_be_less_than_displayed_liquidity():
    for key, amount in (("total_ask_size", 5), ("total_bid_size", 7)):
        value = body(); value[0][key] = amount
        refusal(lambda: parse(value), "QUOTE_DEPTH_TOTAL_CONTRADICTION")


def test_e1_source_uses_public_fixed_get_and_explicit_clock_without_credential_reads():
    raw = receipt().raw_body
    with patch.object(keys, "read", side_effect=AssertionError("credential read forbidden")) as key_read, \
            patch.object(transport, "_clock", lambda: NOW-timedelta(days=1)), \
            F.serve({("GET", "/v1/orderbook"): lambda call: (200, {"Date": F.DATE_HEADER}, raw)}) as calls:
        book = E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW).read()
    assert book.asof == NOW and book.received_at == NOW and book.receipt.raw_body == raw
    assert not key_read.called and len(calls) == 1
    assert calls[0]["url"] == "https://api.upbit.com/v1/orderbook?markets=KRW-BTC&level=0&count=30"
    assert calls[0]["method"] == "GET" and calls[0]["json_body"] is None
    assert "Authorization" not in calls[0]["headers"]


def test_source_decodes_raw_body_not_lossy_answer_body_and_requires_date_header():
    good = receipt()
    answer = transport.Answer(body={"fake": "ignored"}, server_utc=NOW, received_utc=NOW,
                              raw_body=good.raw_body, sha256=good.sha256)
    with patch("execution_accounts.quotes.request", return_value=answer) as send:
        assert E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW).read().bid == 99
        send.assert_called_once_with("upbit", "GET", "/v1/orderbook", PARAMS)
    with patch("execution_accounts.quotes.request", return_value=replace(answer, server_utc=None)):
        refusal(lambda: E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW).read(), "QUOTE_SERVER_TIME_REQUIRED")
    with patch("execution_accounts.quotes.request", return_value=replace(answer, received_utc=NOW+timedelta(seconds=1))):
        refusal(lambda: E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW).read(), "QUOTE_RECEIPT_OUTSIDE_REQUEST")


def test_inquiry_errors_are_fixed_codes_and_do_not_include_raw_provider_details():
    with patch("execution_accounts.quotes.request", side_effect=RuntimeError("private provider response")):
        refusal(lambda: E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW).read(), "QUOTE_PUBLIC_INQUIRY_FAILED")
    with F.serve({("GET", "/v1/orderbook"): lambda call: (200, {}, receipt().raw_body)}):
        refusal(lambda: E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW).read(), "QUOTE_SERVER_TIME_REQUIRED")


def test_managed_route_is_explicit_and_restored_after_success_or_failure():
    url = "https://api.upbit.com/v1/orderbook"
    route = ManagedRoute(proxy_url="http://proxy:8080", ca_bundle="/etc/ssl/certs/ca-certificates.crt",
                         permitted_hosts=frozenset({"api.upbit.com"}))
    original = route_options(url)
    for fail in (False, True):
        def send(*args):
            options = route_options(url)
            assert options.proxies["https"] == route.proxy_url and options.verify == route.ca_bundle
            if fail:
                raise ValueError("synthetic route failure")
            good = receipt()
            return transport.Answer(body=None, server_utc=NOW, received_utc=NOW,
                                    raw_body=good.raw_body, sha256=good.sha256)
        with patch("execution_accounts.quotes.request", side_effect=send):
            source = E1UpbitQuoteSource(symbol="KRW-BTC", clock=lambda: NOW, route=route)
            if fail:
                refusal(source.read, "QUOTE_PUBLIC_INQUIRY_FAILED")
            else:
                assert source.read().bid == 99
        assert route_options(url) == original


def test_runner_bridge_preserves_source_timestamp_and_refuses_future_stale_or_changed_book():
    book = parse()
    quote = to_runner_quote(book, now=NOW+timedelta(seconds=1))
    assert (quote.venue, quote.market, quote.symbol) == ("upbit", "spot", "KRW-BTC")
    assert quote.asof == book.asof and quote.bid == 99 and quote.ask == 101
    assert quote.source_sha256 == book.source_sha256
    equal_float = replace(book, levels=(replace(book.levels[0], bid=99.0),) + book.levels[1:])
    assert type(to_runner_quote(equal_float, now=NOW).bid) is D
    refusal(lambda: to_runner_quote(book, now=NOW-timedelta(microseconds=1)), "QUOTE_RECEIPT_STALE_OR_FUTURE")
    refusal(lambda: to_runner_quote(book, now=NOW+timedelta(seconds=11)), "QUOTE_RECEIPT_STALE_OR_FUTURE")
    changed = replace(book, levels=(replace(book.levels[0], bid=D(100)),) + book.levels[1:])
    refusal(lambda: to_runner_quote(changed, now=NOW), "QUOTE_RECORD_CHANGED")
    refusal(lambda: to_runner_quote(replace(book, source_sha256="a"*64), now=NOW), "QUOTE_RECORD_CHANGED")


def test_only_exact_get_orderbook_route_is_allowed_before_keys_or_send():
    # The separate exact instruments GET is now approved for term renewal; its
    # neighboring routes and every write method remain outside the E1 contract.
    with patch.object(keys, "read", side_effect=AssertionError("credential read forbidden")) as key_read, \
            patch.object(transport, "_send", side_effect=AssertionError("send forbidden")) as send:
        for method, path in (("POST", "/v1/orderbook"), ("DELETE", "/v1/orderbook"),
                             ("GET", "/v1/orderbooks"), ("GET", "/v1/orderbook/instruments/new"),
                             ("POST", "/v1/orderbook/instruments"), ("DELETE", "/v1/orderbook/instruments"),
                             ("GET", "/v1/orderbook/new"), ("GET", "/v1/orderbook/")):
            try:
                transport.request("upbit", method, path, PARAMS)
            except transport.InquiryRefused:
                continue
            raise AssertionError("nonexact public inquiry was accepted")
        assert not key_read.called and not send.called
