"""Live positions (E1 spec 6 "Positions (P19)"; plan decision E17): the latest snapshot of each venue ->
model.Positions, or None.

Pure: no clock (the caller passes `now`), no file, no network. Fail closed: one missing, misfiled, failed, stale or
unpriced venue (a price of 0 or below is no price), a holding below 0 units, a venue worth less than nothing, or a
total that is not a finite number gives None for the whole set, never partial positions. Every price is the
snapshot's own `prices_krw`, set by its venue parser (spec 6): KIS domestic at `prpr`, KIS overseas at `now_pric2`
times the inquire-present-balance rate, Upbit at its ticker, OKX BTC at OKX BTC-USDT times Upbit KRW-USDT, OKX USDT
and USDC at Upbit KRW-USDT.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timedelta

from core.compliance import model
from execution.snapshot import STALE_AFTER, VENUES, Snapshot


def venue_value_krw(snap: Snapshot) -> float | None:
    """Cash plus holdings at `snap.prices_krw` (KRW cash at 1.0); None when a currency or symbol has no price above 0
    or a holding has fewer than 0 units."""
    total = 0.0
    for currency, amount in snap.cash.items():
        price = 1.0 if currency == "KRW" else snap.prices_krw.get(currency)
        if price is None or not price > 0:          # a 0 price is an empty field (`_num` reads "" as 0.0): no price
            return None
        total += amount * price
    for symbol, holding in snap.holdings.items():
        price = snap.prices_krw.get(symbol)
        if price is None or not price > 0 or holding.units < 0:
            return None
        total += holding.units * price
    return total


def _fresh(snap: Snapshot, now: datetime) -> bool:
    """0 <= now - snap.utc <= STALE_AFTER; a stamp that does not parse, or a stamp or `now` with no offset, is not
    fresh."""
    try:
        stamp = datetime.fromisoformat(snap.utc)
    except (TypeError, ValueError):
        return False
    return (stamp.utcoffset() is not None and now.utcoffset() is not None
            and timedelta(0) <= now - stamp <= STALE_AFTER)


def live_positions(snapshots: Mapping[str, Snapshot], now: datetime) -> model.Positions | None:
    """model.Positions from one ok, fresh, fully priced snapshot per venue of VENUES, each under its own venue's key,
    none worth less than 0 and the total finite; else None (E17). `reservations` and `promised_sell_units` stay empty
    (E2 adds them)."""
    values = {}
    for venue in VENUES:
        snap = snapshots.get(venue)
        if snap is None or snap.venue != venue or snap.ok is not True or not _fresh(snap, now):
            return None
        value = venue_value_krw(snap)
        if value is None or value < 0:
            return None
        values[venue] = value
    equity = sum(values.values())
    if not math.isfinite(equity):          # an overflow: inf, or nan from inf - inf inside one venue
        return None
    return model.Positions(
        equity_krw=equity,
        holdings={(venue, symbol): holding.units
                  for venue in VENUES for symbol, holding in snapshots[venue].holdings.items()},
        shorts={},
        exposure={venue: model.Exposure(held_krw=value) for venue, value in values.items()})
