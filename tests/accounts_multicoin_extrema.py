"""Approach A interval extrema with unordered public prices and simultaneous fills."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from itertools import permutations

from execution_accounts.continuous import ContinuousEvidenceError, PriceMark, value_trade_paths
from execution_accounts.upbit_collector import TradePrint
from execution_control.risk import Fill

START = datetime(2026, 11, 28, 3, tzinfo=timezone.utc)
END = START + timedelta(seconds=4)
A, B = "KRW-AAA", "KRW-BBB"


def at(second, micros=0):
    return START + timedelta(seconds=second, microseconds=micros)


def trade(m, sec, price, seq):
    return TradePrint(market=m, sequential_id=seq, timestamp_ms=int(START.timestamp())*1000 + sec*1000,
                      at=at(sec), price=D(price), volume=D(1), ask_bid="BID", source_sha256="a"*64)


def fill(m, side, price, stamp, identity, *, quantity="1", fee="0"):
    return Fill(venue="upbit", account_scope="fixture", order_id=identity, fill_id=identity, market="spot",
                symbol=m, side=side, quantity=D(quantity), price=D(price), quote_currency="KRW",
                quote_krw=D(1), fee_amount=D(fee), fee_currency="KRW", base_currency=m[4:], executed_at=stamp)


def args(*, cash="10", a=True, b=True):
    units = tuple((m, D(1)) for m, held in ((A, a), (B, b)) if held)
    return dict(opening_marks={A: D(10), B: D(10)}, opening_cash_krw=D(cash), opening_units=units,
                historical_fills=tuple(fill(m, "buy", 10, at(-1), "prior"+m) for m,_ in units),
                interval_fills=(), previous_equity_krw=D(cash)+10*len(units), previous_realized_net_krw=D(0),
                start=START, end=END, account_scope="fixture")


def bounds(result):
    return result.minimum_equity_krw, result.maximum_equity_krw, result.equity_krw


def test_interior_tied_prints_carry_the_price_range_until_another_mark_of_that_coin():
    # A's true closing price in second 1 could be 4 or 22; B changes two seconds before the endpoint.
    for first, second in permutations((4, 22)):
        rows = {A: (trade(A, 1, first, 10), trade(A, 1, second, 11), trade(A, 3, 12, 12)),
                B: (trade(B, 2, 20, 5),)}
        result = value_trade_paths(rows, **args())
        assert bounds(result) == (D(24), D(52), D(42))
        rows[B] = (trade(B, 2, 2, 5),)
        assert bounds(value_trade_paths(rows, **args())) == (D(16), D(42), D(24))


def test_final_tie_requires_matching_time_price_and_scope_and_only_then_collapses_the_mark():
    rows = {A: (trade(A, 1, 4, 1), trade(A, 1, 22, 2)), B: (trade(B, 2, 20, 1),)}
    for hint, reason in ((None, "CONTINUOUS_CLOSING_MARK_AMBIGUOUS"),
                         (PriceMark(symbol=A, price=D(10), asof=at(1)), "CONTINUOUS_CLOSING_MARK_MISMATCH"),
                         (PriceMark(symbol=A, price=D(4), asof=at(2)), "CONTINUOUS_CLOSING_MARK_MISMATCH"),
                         (PriceMark(symbol=B, price=D(4), asof=at(1)), "CONTINUOUS_CLOSING_MARK_MISMATCH")):
        try:
            value_trade_paths(rows, **args(), closing_marks={A:hint} if hint else None)
        except ContinuousEvidenceError as exc:
            assert str(exc) == reason
        else:
            raise AssertionError("Expected a refusal")
    result = value_trade_paths(rows, **args(), closing_marks={A:PriceMark(symbol=A, price=D(4), asof=at(1))})
    assert bounds(result) == (D(24), D(42), D(34))
    assert next(m.price for m in result.closing_marks if m.symbol == A) == 4
    flat = value_trade_paths(rows, **args(a=False, b=True))
    assert all(m.symbol != A for m in flat.closing_marks)


def test_same_timestamp_independent_profitable_and_losing_sides_cover_both_fill_orders():
    # Both orders can be funded in either order. Their impact at the carried marks is +5 and -4.
    orders = (fill(A, "buy", 5, at(1), "buy-a"), fill(B, "buy", 14, at(1), "buy-b"))
    for fills in permutations(orders):
        result = value_trade_paths({A: (), B: ()}, **(args(cash="50", a=False, b=False) | {"interval_fills": fills}))
        assert bounds(result) == (D(46), D(55), D(51))


def test_same_instant_cash_coupled_prefixes_only_count_reachable_states():
    # Buying A would add 8 of mark value but requires selling B first. That +8 peak alone is impossible.
    orders = (fill(B, "sell", 4, at(1), "sell-b"), fill(A, "buy", 2, at(1), "buy-a"))
    result = value_trade_paths({A: (), B: ()}, **(args(cash="1", a=False) | {"interval_fills": orders}))
    assert bounds(result) == (D(5), D(13), D(13)) and result.realized_net_total_krw == -6


def test_submillisecond_fills_follow_actual_execution_time_and_prior_fifo_with_fee():
    # Lexical market order puts the buy before the sale. The two instants settle in the opposite order.
    sale = fill(B, "sell", 4, at(1, 100), "sell-b", fee="1")
    buy = fill(A, "buy", 2, at(1, 900), "buy-a", fee="0.5")
    result = value_trade_paths({A: (), B: ()}, **(args(cash="1", a=False) | {"interval_fills": (buy, sale)}))
    assert bounds(result) == (D(4), D("11.5"), D("11.5"))
    assert result.closing_cash_krw == D("1.5") and result.realized_net_total_krw == -7


def test_future_opening_missing_market_and_inconsistent_print_millisecond_reject():
    cases = (
        ({A: ()}, args(), "CONTINUOUS_TRADE_WINDOW_MISSING"),
        ({A: (), B: ()}, args() | {"opening_marks": {A:PriceMark(symbol=A, price=D(10), asof=at(1)), B:D(10)}},
         "CONTINUOUS_OPENING_MARK_FUTURE"),
        ({A:(replace(trade(A, 1, 10, 1), timestamp_ms=1),), B:()}, args(), "CONTINUOUS_MARK_TIME_MISMATCH"),
    )
    for rows, options, reason in cases:
        try:
            value_trade_paths(rows, **options)
        except ContinuousEvidenceError as exc:
            assert str(exc) == reason, (str(exc), reason)
        else:
            raise AssertionError("Expected " + reason)


def test_locally_solvent_prefix_that_cannot_complete_is_excluded_from_extrema():
    # A buy first would leave 0 cash and 1 equity. It strands the only other
    # purchase, so that low cannot occur on any complete sequence of these fills.
    purchases = (fill(B, "buy", 4, at(1), "buy-b"), fill(B, "sell", 10, at(1), "sell-b"),
                 fill(A, "buy", 5, at(1), "buy-a"))
    options = args(cash="5", a=False, b=False) | {"interval_fills": purchases, "opening_marks": {A:D(1), B:D(1)}}
    result = value_trade_paths({A: (), B: ()}, **options)
    assert bounds(result) == (D(2), D(11), D(7)) and result.realized_net_total_krw == 6


def test_unordered_simultaneous_prices_from_different_markets_need_the_conservative_envelope():
    rows = {A:(trade(A, 1, 11, 1),), B:(trade(B, 1, 9, 1),)}
    assert bounds(value_trade_paths(rows, **args())) == (D(29), D(31), D(30))
    try:
        value_trade_paths(rows, **args(), conservative_ms=False)
    except ContinuousEvidenceError as exc:
        assert str(exc) == "CONTINUOUS_UNORDERED_TRADES_REQUIRE_ENVELOPE"
    else:
        raise AssertionError("An exchange ID cannot establish cross-market order")
