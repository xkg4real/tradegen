"""Exact public Upbit orderbook quotes through the existing E1 GET seam.

No request happens on import or construction. Explicit owner integration may
call read(); development uses synthetic responses. A quotation receipt is public
market data, never authenticated account evidence or an execution permission.
"""
from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
import re
from typing import Callable

from execution.transport import Answer, inquiry_clock, request
from execution_accounts.collector import SourceReceipt
from execution_network.route import ManagedRoute, managed_route

_SYMBOL = re.compile(r"KRW-[A-Z][A-Z0-9]{0,11}")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_PUBLIC_SCOPE = "public-upbit-orderbook"
_MAX_BYTES = 131072
_MAX_AGE = timedelta(seconds=10)


class QuoteError(ValueError):
    """Fixed diagnostic codes only; raw response and provider errors stay private."""


def _require(condition, code):
    if not condition:
        raise QuoteError(code)


def _symbol(value):
    _require(type(value) is str and _SYMBOL.fullmatch(value) is not None
             and value != "KRW-KRW", "QUOTE_KRW_SYMBOL_REQUIRED")
    return value


def _instant(value):
    _require(type(value) is datetime and value.utcoffset() is not None,
             "QUOTE_AWARE_TIME_REQUIRED")
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise QuoteError("QUOTE_TIME_INVALID") from None


def _amount(value, *, positive=True):
    # Wire numeric tokens become int/Decimal, never binary floats or strings.
    _require(type(value) in (int, Decimal), "QUOTE_EXACT_NUMBER_REQUIRED")
    result = Decimal(value)
    _require(result.is_finite() and len(result.as_tuple().digits) <= 60
             and -40 <= result.as_tuple().exponent <= 40, "QUOTE_NUMBER_RANGE")
    _require(result > 0 if positive else result >= 0, "QUOTE_AMOUNT_INVALID")
    return result


def _params(symbol):
    return (("markets", _symbol(symbol)), ("level", "0"), ("count", "30"))


@dataclass(frozen=True, kw_only=True)
class BookLevel:
    ask: Decimal
    bid: Decimal
    ask_size: Decimal
    bid_size: Decimal


@dataclass(frozen=True, kw_only=True)
class OrderbookQuote:
    symbol: str
    asof: datetime
    received_at: datetime
    server_time: datetime
    levels: tuple[BookLevel, ...]
    total_ask_size: Decimal
    total_bid_size: Decimal
    source_sha256: str
    receipt: SourceReceipt = field(repr=False)

    @property
    def bid(self):
        return self.levels[0].bid

    @property
    def ask(self):
        return self.levels[0].ask

    @property
    def bid_size(self):
        return self.levels[0].bid_size

    @property
    def ask_size(self):
        return self.levels[0].ask_size

    @property
    def midpoint(self):
        """Derived midpoint; not a last trade or guaranteed executable mark."""
        with localcontext() as numeric:
            numeric.prec = 256
            numeric.traps[Inexact] = True
            return (self.bid + self.ask) / 2


def parse_orderbook(receipt: SourceReceipt, *, symbol: str, now: datetime) -> OrderbookQuote:
    """Validate exact bytes, selected market, native depth, clocks and spread.

    Up to 30 displayed price levels are retained. Totals may include depth not
    displayed; this does not claim an entire venue book or fill availability.
    The strict local freshness policy permits no future-dated quote or receipt.
    """
    _symbol(symbol); now = _instant(now)
    _require(type(receipt) is SourceReceipt and receipt.path == "/v1/orderbook"
             and receipt.params == _params(symbol) and type(receipt.params) is tuple
             and receipt.account_scope == _PUBLIC_SCOPE, "QUOTE_RECEIPT_SCOPE_MISMATCH")
    received = _instant(receipt.received_at); server = _instant(receipt.server_time)
    _require(timedelta(0) <= now-received <= _MAX_AGE, "QUOTE_RECEIPT_STALE_OR_FUTURE")
    _require(abs(received-server) <= timedelta(seconds=60), "QUOTE_SERVER_CLOCK_MISMATCH")
    _require(type(receipt.raw_body) is bytes and 0 < len(receipt.raw_body) <= _MAX_BYTES,
             "QUOTE_BODY_TOO_LARGE_OR_EMPTY")
    try:
        body = receipt.decode()
    except (ValueError, TypeError, ArithmeticError):
        raise QuoteError("QUOTE_RECEIPT_INVALID") from None
    _require(type(body) is list and len(body) == 1 and type(body[0]) is dict,
             "QUOTE_SINGLE_BOOK_REQUIRED")
    row = body[0]
    _require(row.get("market") == symbol, "QUOTE_MARKET_MISMATCH")
    level = _amount(row.get("level"), positive=False)
    _require(level == 0, "QUOTE_AGGREGATED_DEPTH_REFUSED")
    stamp = row.get("timestamp")
    _require(type(stamp) is int and 0 < stamp <= 2**63-1, "QUOTE_TIMESTAMP_INVALID")
    try:
        asof = _EPOCH + timedelta(milliseconds=stamp)
    except OverflowError:
        raise QuoteError("QUOTE_TIMESTAMP_INVALID") from None
    _require(timedelta(0) <= received-asof <= _MAX_AGE and now-asof <= _MAX_AGE,
             "QUOTE_BOOK_STALE_OR_FUTURE")
    units = row.get("orderbook_units")
    _require(type(units) is list and 1 <= len(units) <= 30,
             "QUOTE_DEPTH_EMPTY_OR_OVERSIZED")
    levels = []
    for unit in units:
        _require(type(unit) is dict, "QUOTE_LEVEL_INVALID")
        item = BookLevel(ask=_amount(unit.get("ask_price")), bid=_amount(unit.get("bid_price")),
            ask_size=_amount(unit.get("ask_size")), bid_size=_amount(unit.get("bid_size")))
        _require(item.bid < item.ask, "QUOTE_LOCKED_OR_CROSSED_BOOK")
        _require(not levels or item.ask > levels[-1].ask and item.bid < levels[-1].bid,
                 "QUOTE_DEPTH_NOT_STRICTLY_ORDERED")
        levels.append(item)
    total_ask = _amount(row.get("total_ask_size")); total_bid = _amount(row.get("total_bid_size"))
    with localcontext() as numeric:
        numeric.prec = 256
        numeric.traps[Inexact] = True
        _require(total_ask >= sum((v.ask_size for v in levels), Decimal(0))
                 and total_bid >= sum((v.bid_size for v in levels), Decimal(0)),
                 "QUOTE_DEPTH_TOTAL_CONTRADICTION")
    return OrderbookQuote(symbol=symbol, asof=asof, received_at=received, server_time=server,
        levels=tuple(levels), total_ask_size=total_ask, total_bid_size=total_bid,
        source_sha256=receipt.sha256, receipt=receipt)


@dataclass(frozen=True, kw_only=True)
class E1UpbitQuoteSource:
    """Owner-operated public source, requiring an explicit clock and optional route.

    Fetch before choosing the runner's tick time. A newly received snapshot is
    not stamped with an earlier scheduling time. No account keys/home are read.
    """
    symbol: str
    clock: Callable = field(repr=False)
    route: ManagedRoute | None = None

    def __post_init__(self):
        _symbol(self.symbol)
        _require(callable(self.clock), "QUOTE_CLOCK_REQUIRED")
        _require(self.route is None or type(self.route) is ManagedRoute, "QUOTE_ROUTE_INVALID")

    def read(self) -> OrderbookQuote:
        _symbol(self.symbol)
        _require(callable(self.clock), "QUOTE_CLOCK_REQUIRED")
        params = _params(self.symbol)
        try:
            before = _instant(self.clock())
            with ExitStack() as stack:
                stack.enter_context(inquiry_clock(self.clock))
                if self.route is not None:
                    stack.enter_context(managed_route(self.route))
                answer = request("upbit", "GET", "/v1/orderbook", params)
            after = _instant(self.clock())
        except Exception:
            raise QuoteError("QUOTE_PUBLIC_INQUIRY_FAILED") from None
        _require(type(answer) is Answer and answer.server_utc is not None,
                 "QUOTE_SERVER_TIME_REQUIRED")
        received = _instant(answer.received_utc)
        _require(before <= received <= after, "QUOTE_RECEIPT_OUTSIDE_REQUEST")
        receipt = SourceReceipt(path="/v1/orderbook", params=params, account_scope=_PUBLIC_SCOPE,
            received_at=received, server_time=answer.server_utc,
            raw_body=answer.raw_body, sha256=answer.sha256)
        return parse_orderbook(receipt, symbol=self.symbol, now=after)


def to_runner_quote(book: OrderbookQuote, *, now: datetime):
    """Pure bridge over a prefetched quote; no refresh or timestamp relabeling."""
    _require(type(book) is OrderbookQuote, "QUOTE_RECORD_REQUIRED")
    checked = parse_orderbook(book.receipt, symbol=book.symbol, now=now)
    _require(book == checked, "QUOTE_RECORD_CHANGED")
    from execution_launch.runner import Quote
    # Return canonical redecoded fields: Python equality alone also equates
    # some floats/ints to Decimal values in manually constructed records.
    return Quote(venue="upbit", market="spot", symbol=checked.symbol, bid=checked.bid, ask=checked.ask,
                 asof=checked.asof, source_sha256=checked.source_sha256)
