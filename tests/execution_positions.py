"""Live positions (E1 Task 8; contract section 12; E17): three venue snapshots -> model.Positions, fail closed.

Pure: no network, no clock, no file. Every snapshot is built in memory with `EF.snap`, its holdings, cash and prices
always given in full, at the prices the venue parsers derive from the contract 3.2 fixtures (spec 6).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta

from core.compliance import model, owner
from execution import positions
from execution import snapshot as S
from tests import execution_fixtures as EF

# Spec 6 prices from the 3.2 fixtures: KIS 005930 at prpr 61000; KIS AAPL at now_pric2 210 times frst_bltn_exrt
# 1390.50, and USD cash at 1390.50; Upbit BTC at its KRW-BTC ticker 100,000,000; OKX BTC at OKX BTC-USDT 70000 times
# Upbit KRW-USDT 1400; OKX USDT and USDC at Upbit KRW-USDT 1400. The 3 USDC on OKX are added here (the fixtures hold
# none) so the test sees USDC counted.
USD_KRW = 1390.5
USDT_KRW = 1400.0
KIS_KRW = 20000.0 + 5.0 * USD_KRW + 1.0 * 61000.0 + 1.0 * (210.0 * USD_KRW)       # 379,957.5
UPBIT_KRW = 20000.0 + 0.0001 * 100000000.0                                          # 30,000
OKX_KRW = 10.0 * USDT_KRW + 3.0 * USDT_KRW + 0.0001 * (70000.0 * USDT_KRW)         # 28,000


def _kis(**changes) -> S.Snapshot:
    fields = {"holdings": {"005930": S.Holding(units=1.0, locked=0.0, avg_cost=60000.0),
                           "AAPL": S.Holding(units=1.0, locked=0.0, avg_cost=200.0)},
              "cash": {"KRW": 20000.0, "USD": 5.0},
              "prices_krw": {"005930": 61000.0, "AAPL": 210.0 * USD_KRW, "USD": USD_KRW}}
    return EF.snap("kis", **(fields | changes))


def _upbit(**changes) -> S.Snapshot:
    fields = {"holdings": {"BTC": S.Holding(units=0.0001, locked=0.0, avg_cost=100000000.0)},
              "cash": {"KRW": 20000.0},
              "prices_krw": {"BTC": 100000000.0, "USDT": USDT_KRW}}
    return EF.snap("upbit", **(fields | changes))


def _okx(**changes) -> S.Snapshot:
    fields = {"holdings": {"USDT": S.Holding(units=10.0), "USDC": S.Holding(units=3.0),
                           "BTC": S.Holding(units=0.0001)},
              "cash": {},
              "prices_krw": {"USDT": USDT_KRW, "USDC": USDT_KRW, "BTC": 70000.0 * USDT_KRW}}
    return EF.snap("okx", **(fields | changes))


def _three(**venues) -> dict:
    """The three fixture snapshots keyed by venue; a keyword replaces that venue's snapshot."""
    return {"kis": _kis(), "upbit": _upbit(), "okx": _okx()} | venues


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-9)


def _stamped(make, moment) -> S.Snapshot:
    return make(utc=model.iso_utc(moment))


def _drop(mapping, key) -> dict:
    return {k: v for k, v in mapping.items() if k != key}


def test_venue_value_prices_cash_and_holdings():
    assert _close(positions.venue_value_krw(_kis()), KIS_KRW), positions.venue_value_krw(_kis())
    assert _close(positions.venue_value_krw(_upbit()), UPBIT_KRW)
    assert _close(positions.venue_value_krw(_okx()), OKX_KRW)
    # KRW cash is valued at 1.0 with no "KRW" price; a "KRW" price never changes that
    assert positions.venue_value_krw(_upbit(holdings={}, prices_krw={})) == 20000.0
    assert positions.venue_value_krw(_upbit(holdings={}, prices_krw={"KRW": 2.0})) == 20000.0
    assert positions.venue_value_krw(_upbit(holdings={}, prices_krw={"KRW": 0.0})) == 20000.0
    assert positions.venue_value_krw(_okx(holdings={}, prices_krw={})) == 0.0
    # a price for a symbol that is not held is not counted
    assert _close(positions.venue_value_krw(_okx(prices_krw=dict(_okx().prices_krw, ETH=5000000.0))), OKX_KRW)


def test_venue_value_is_none_for_an_unpriced_symbol_or_currency():
    assert positions.venue_value_krw(_kis(prices_krw=_drop(_kis().prices_krw, "AAPL"))) is None
    assert positions.venue_value_krw(_kis(prices_krw=_drop(_kis().prices_krw, "USD"))) is None
    assert positions.venue_value_krw(_upbit(prices_krw={"USDT": USDT_KRW})) is None
    assert positions.venue_value_krw(_okx(prices_krw={})) is None          # Upbit failed: OKX has no usdt_krw
    # a price of 0 (contract 9 `_num` reads an empty field as 0.0) or below 0 is no price
    assert positions.venue_value_krw(_kis(prices_krw=dict(_kis().prices_krw, USD=0.0))) is None
    assert positions.venue_value_krw(_kis(prices_krw=dict(_kis().prices_krw, AAPL=0.0))) is None
    assert positions.venue_value_krw(_okx(prices_krw=dict(_okx().prices_krw, USDT=-1.0))) is None
    # a holding of fewer than 0 units is refused, whatever its price
    assert positions.venue_value_krw(_okx(holdings=dict(_okx().holdings, BTC=S.Holding(units=-0.0001)))) is None


def test_equity_is_the_sum_of_the_three_venue_values():
    live = positions.live_positions(_three(), EF.NOW)
    assert isinstance(live, model.Positions), live
    assert _close(live.equity_krw, KIS_KRW + UPBIT_KRW + OKX_KRW), live.equity_krw
    assert _close(live.equity_krw, sum(positions.venue_value_krw(s) for s in _three().values()))


def test_held_krw_per_venue_includes_okx_usdt_and_usdc_and_nothing_is_reserved():
    live = positions.live_positions(_three(), EF.NOW)
    assert set(live.exposure) == {"kis", "upbit", "okx"}, live.exposure
    for venue, want in (("kis", KIS_KRW), ("upbit", UPBIT_KRW), ("okx", OKX_KRW)):
        exposure = live.exposure[venue]
        assert isinstance(exposure, model.Exposure), exposure
        assert _close(exposure.held_krw, want), (venue, exposure.held_krw)
        assert dict(exposure.reservations) == {} and dict(exposure.promised_sell_units) == {}, exposure
    assert _close(live.exposure["okx"].held_krw - 0.0001 * 70000.0 * USDT_KRW, 13.0 * USDT_KRW)
    assert dict(live.shorts) == {}, live.shorts


def test_holdings_are_keyed_by_venue_and_symbol():
    live = positions.live_positions(_three(), EF.NOW)
    assert dict(live.holdings) == {("kis", "005930"): 1.0, ("kis", "AAPL"): 1.0, ("upbit", "BTC"): 0.0001,
                                   ("okx", "USDT"): 10.0, ("okx", "USDC"): 3.0, ("okx", "BTC"): 0.0001}, live.holdings
    # locked units are part of units (Holding.units is the total held); cash currencies are not holdings
    locked_btc = _upbit(holdings={"BTC": S.Holding(units=0.0003, locked=0.0002)})
    locked = positions.live_positions(_three(upbit=locked_btc), EF.NOW)
    assert locked.holdings[("upbit", "BTC")] == 0.0003, locked.holdings
    assert _close(locked.exposure["upbit"].held_krw, 20000.0 + 0.0003 * 100000000.0), locked.exposure
    assert not {k for k in live.holdings if k[1] in ("KRW", "USD")}, live.holdings


def test_a_missing_or_failed_venue_gives_none():
    assert positions.live_positions({}, EF.NOW) is None
    for venue in S.VENUES:
        assert positions.live_positions(_drop(_three(), venue), EF.NOW) is None, venue
        down = S.failed(venue, model.iso_utc(EF.NOW), f"{venue}: test")
        assert positions.live_positions(_three(**{venue: down}), EF.NOW) is None, venue
    # a snapshot filed under another venue's key is refused, not valued as that venue
    assert positions.live_positions(_three(kis=_upbit()), EF.NOW) is None
    assert positions.live_positions(_three(upbit=_okx(), okx=_upbit()), EF.NOW) is None
    # an extra key is ignored; the three venues decide
    assert positions.live_positions(_three() | {"binance": _upbit()}, EF.NOW) == positions.live_positions(
        _three(), EF.NOW)


def test_a_stale_or_future_snapshot_gives_none_and_15_minutes_still_counts():
    makers = {"kis": _kis, "upbit": _upbit, "okx": _okx}
    for venue, make in makers.items():
        edge = _stamped(make, EF.NOW - timedelta(minutes=15))
        stale = _stamped(make, EF.NOW - timedelta(minutes=15, seconds=1))
        future = _stamped(make, EF.NOW + timedelta(seconds=1))
        assert positions.live_positions(_three(**{venue: edge}), EF.NOW) is not None, venue
        assert positions.live_positions(_three(**{venue: stale}), EF.NOW) is None, venue
        assert positions.live_positions(_three(**{venue: future}), EF.NOW) is None, venue
    # the same rule seen from `now`: all three stamped at NOW
    assert positions.live_positions(_three(), EF.NOW + timedelta(minutes=15)) is not None
    assert positions.live_positions(_three(), EF.NOW + timedelta(minutes=15, seconds=1)) is None
    assert positions.live_positions(_three(), EF.NOW - timedelta(seconds=1)) is None


def test_an_unreadable_or_offset_less_time_gives_none():
    for utc in ("", "not a time", "2026-10-24T00:00:00"):
        assert positions.live_positions(_three(upbit=_upbit(utc=utc)), EF.NOW) is None, utc
    # a `now` without an offset gives None, never a TypeError from comparing it with an aware stamp
    assert positions.live_positions(_three(), datetime(2026, 10, 24)) is None


def test_an_unpriced_holding_or_currency_gives_none():
    eth = dict(_okx().holdings, ETH=S.Holding(units=0.01))                 # OKX prices BTC, USDT and USDC only
    for case in (_three(kis=_kis(prices_krw=_drop(_kis().prices_krw, "AAPL"))),
                 _three(kis=_kis(prices_krw=_drop(_kis().prices_krw, "USD"))),
                 _three(upbit=_upbit(prices_krw={"USDT": USDT_KRW})), _three(okx=_okx(holdings=eth)),
                 _three(okx=_okx(prices_krw={})),
                 # an empty KIS frst_bltn_exrt, now_pric2 or prpr reads as 0.0; an OKX `last` of 0 prices BTC at 0
                 _three(kis=_kis(prices_krw=dict(_kis().prices_krw, USD=0.0))),
                 _three(kis=_kis(prices_krw=dict(_kis().prices_krw, AAPL=0.0))),
                 _three(kis=_kis(prices_krw=dict(_kis().prices_krw, **{"005930": 0.0}))),
                 _three(okx=_okx(prices_krw=dict(_okx().prices_krw, BTC=0.0))),
                 _three(okx=_okx(prices_krw=dict(_okx().prices_krw, USDT=-1.0)))):
        assert positions.live_positions(case, EF.NOW) is None, case


def test_a_negative_venue_value_gives_none_and_zero_counts():
    assert positions.live_positions(_three(upbit=_upbit(holdings={}, cash={"KRW": -1.0})), EF.NOW) is None
    # a negative cash line inside a venue worth more than 0 still counts: the rule is the venue's value
    owed = positions.live_positions(_three(kis=_kis(cash={"KRW": -1000.0, "USD": 5.0})), EF.NOW)
    assert owed is not None and _close(owed.exposure["kis"].held_krw, KIS_KRW - 21000.0), owed
    # a holding of fewer than 0 units never counts, even in a venue worth more than 0
    short_btc = dict(_okx().holdings, BTC=S.Holding(units=-0.0001))
    assert positions.live_positions(_three(okx=_okx(holdings=short_btc)), EF.NOW) is None
    empty = positions.live_positions(_three(okx=_okx(holdings={}, prices_krw={})), EF.NOW)
    assert empty is not None and empty.exposure["okx"].held_krw == 0.0, empty
    assert not {k for k in empty.holdings if k[0] == "okx"}, empty.holdings


def test_a_value_that_is_not_a_finite_number_gives_none():
    # every input is finite (a Snapshot refuses NaN and inf), but a product or a sum can overflow
    huge = _okx(holdings={"BTC": S.Holding(units=1e200)}, prices_krw={"BTC": 1e200})
    assert positions.venue_value_krw(huge) == math.inf
    assert positions.live_positions(_three(okx=huge), EF.NOW) is None
    nan = _kis(holdings={"AAPL": S.Holding(units=1e200)}, cash={"USD": -1e200},
               prices_krw={"AAPL": 1e200, "USD": 1e200})
    assert math.isnan(positions.venue_value_krw(nan))
    assert positions.live_positions(_three(kis=nan), EF.NOW) is None
    # three finite venue values whose sum overflows
    big = {"kis": _kis(holdings={}, cash={"KRW": 1e308}, prices_krw={}),
           "upbit": _upbit(holdings={}, cash={"KRW": 1e308}, prices_krw={}),
           "okx": _okx(holdings={"USDT": S.Holding(units=1e305)}, prices_krw={"USDT": 1000.0})}
    assert all(math.isfinite(positions.venue_value_krw(s)) for s in big.values())
    assert positions.live_positions(big, EF.NOW) is None


def test_snapshots_read_back_from_the_inquiry_log_give_the_same_positions():
    back = {venue: S.load(json.loads(S.dump(snap))) for venue, snap in _three().items()}
    assert positions.live_positions(back, EF.NOW) == positions.live_positions(_three(), EF.NOW)
    # E34: checks.day_start values a poll read back later at that poll's own stamp, never at the current now
    earlier = EF.NOW - timedelta(hours=3)
    old = {venue: _stamped(make, earlier) for venue, make in (("kis", _kis), ("upbit", _upbit), ("okx", _okx))}
    back = {venue: S.load(json.loads(S.dump(snap))) for venue, snap in old.items()}
    at = datetime.fromisoformat(back["kis"].utc)
    assert at == earlier and positions.live_positions(back, at) == positions.live_positions(old, earlier)
    assert positions.live_positions(back, at) is not None and positions.live_positions(back, EF.NOW) is None


def test_live_positions_pass_the_gate_positions_check():
    live = positions.live_positions(_three(), EF.NOW)
    assert owner._positions_problem(live) == "", owner._positions_problem(live)
