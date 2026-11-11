"""Public Upbit universe reads (spec sections 5, 7 and 9): the daily snapshot builder, the odds candles and the
per-slot flag and ticker source. Every read is a fixed public GET of execution.upbit_inquiry under an explicit
inquiry_clock. Nothing here reads a key, writes a file or imports owner; only execution_launch/universe_store.py
writes the snapshot file."""
from __future__ import annotations

import base64
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import math

from core.compliance import rules
from core.compliance.model import KST
from execution.transport import Answer, inquiry_clock
from execution.upbit_inquiry import (CANDLE_COUNT_MAX, CANDLES_DAYS_PATH, MARKET_ALL_PATH, candle_params,
                                     daily_candles, market_all)
from execution_accounts.collector import SourceReceipt

PUBLIC_SCOPE = "public"                    # the plain receipt's account_scope (index contract, PR 1)
# ponytail: provisional body caps until the spec section 17 measurement sizes them from real answers
MAX_MARKET_ALL_BODY = 1024 * 1024
MAX_CANDLE_BODY = 256 * 1024
_MARKET_ALL_PARAMS = (("is_details", "true"),)
HISTORY_DAYS = 3650                        # core/oddsdata/bars.py HISTORY_DAYS, written out: no core.oddsdata import
_MAX_PAGES = HISTORY_DAYS // CANDLE_COUNT_MAX + 2


class UniverseReadError(ValueError):
    """A fixed refusal code; no body, market or provider text is quoted."""


def _require(condition, code):
    if not condition:
        raise UniverseReadError(code)


def _inquire(helper, *args):
    """One public helper call; any failure, after the transport's own single retry, is UNIVERSE_INQUIRY_FAILED."""
    try:
        return helper(*args)
    except Exception:
        raise UniverseReadError("UNIVERSE_INQUIRY_FAILED") from None


def _receipt(answer, path, params, cap):
    """(SourceReceipt, decoded body) of one public answer: the server time is required, the body is 1 to `cap` bytes
    and SourceReceipt.decode checks its sha256."""
    _require(type(answer) is Answer and answer.server_utc is not None, "UNIVERSE_SERVER_TIME_REQUIRED")
    _require(type(answer.raw_body) is bytes and 0 < len(answer.raw_body) <= cap, "UNIVERSE_BODY_EMPTY_OR_OVERSIZED")
    try:
        receipt = SourceReceipt(path=path, params=params, account_scope=PUBLIC_SCOPE,
                                received_at=answer.received_utc, server_time=answer.server_utc,
                                raw_body=answer.raw_body, sha256=answer.sha256)
        return receipt, receipt.decode()
    except (ValueError, TypeError, ArithmeticError, RecursionError):
        raise UniverseReadError("UNIVERSE_RECEIPT_INVALID") from None


def _stamp(moment):
    """ISO 8601 UTC with microseconds and Z, the text execution_control.store._utc writes."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _plain(receipt):
    """The 7-key plain receipt of core.compliance.rules (live_history's receipt shape)."""
    return {"path": receipt.path, "params": [[key, value] for key, value in receipt.params],
            "account_scope": receipt.account_scope, "received_at": _stamp(receipt.received_at),
            "server_time": _stamp(receipt.server_time),
            "raw_body_b64": base64.b64encode(receipt.raw_body).decode("ascii"), "sha256": receipt.sha256}


def _candle_request(path, params):
    """(market, to, count) of one candle request the rule implies, refused unless daily_candles sends exactly it."""
    try:
        market, to, count = params[0][1], datetime.fromisoformat(params[1][1]), int(params[2][1])
        exact = path == CANDLES_DAYS_PATH and candle_params(market, to, count) == params
    except Exception:
        exact = False
    _require(exact, "UNIVERSE_REQUEST_INVALID")
    return market, to, count


def build_universe_snapshot(rule: rules.UniverseRule, day: date, *, clock) -> tuple[bytes, str]:
    """The snapshot of candle day `day` (UTC) under `rule`: one market/all read, then exactly the candle reads that
    rules.universe_requests implies for that body, in its order, all under `clock`. The receipts go to
    rules.encode_universe_snapshot in that same order, market/all at its sorted place. Returns the canonical file
    bytes and the manifest sha256 once rules.verify_universe_snapshot accepts them. Any failed read raises and nothing
    is returned; nothing is written here."""
    _require(type(rule) is rules.UniverseRule and type(day) is date and callable(clock), "UNIVERSE_INPUT_INVALID")
    with inquiry_clock(clock):
        first = _inquire(market_all)
        listing = _receipt(first, MARKET_ALL_PATH, _MARKET_ALL_PARAMS, MAX_MARKET_ALL_BODY)[0]
        receipts = []
        for path, params in rules.universe_requests(rule, first.raw_body, day):
            if (path, params) == (MARKET_ALL_PATH, _MARKET_ALL_PARAMS):
                receipts.append(listing)
                continue
            market, to, count = _candle_request(path, params)
            receipts.append(_receipt(_inquire(daily_candles, market, to, count), path, params, MAX_CANDLE_BODY)[0])
    raw, sha256 = rules.encode_universe_snapshot(rule, day, [_plain(receipt) for receipt in receipts])
    universe = rules.verify_universe_snapshot(raw, rules.universe_rule_sha256(rule))
    _require(universe.snapshot_sha256 == sha256, "UNIVERSE_SNAPSHOT_MISMATCH")
    return raw, sha256


@dataclass(frozen=True)
class UniverseBars:
    """One market's final daily bars, oldest first, as load_leg's upbit_daily rows: (UTC candle date ISO, open KRW,
    close KRW), both prices finite and above 0, one per date; and the sha256 of every candle page read, in order."""
    market: str
    bars: tuple[tuple[str, float, float], ...]
    receipt_sha256: tuple[str, ...]


def daily_bars(markets: Sequence[str], *, now: datetime, clock) -> dict[str, UniverseBars]:
    """Final daily bars of each market over [Seoul date of `now` - HISTORY_DAYS, UTC date of `now`): load_leg's
    window for a plan starting on that Seoul date, where a bar dated d is final at 00:00 UTC of d + 1. Pages
    daily_candles backwards under `clock`, CANDLE_COUNT_MAX rows at most a page, until a short page, a page with no
    new date or the window start."""
    _require(type(markets) in (list, tuple) and len(markets) > 0
             and all(type(m) is str and rules.UNIVERSE_MARKET.fullmatch(m) is not None and m != "KRW-KRW"
                     for m in markets)
             and len(set(markets)) == len(markets)
             and type(now) is datetime and now.utcoffset() is not None and callable(clock), "UNIVERSE_INPUT_INVALID")
    start = now.astimezone(KST).date() - timedelta(days=HISTORY_DAYS)
    end = now.astimezone(timezone.utc).date()
    with inquiry_clock(clock):
        return {market: _market_bars(market, start, end) for market in markets}


def _market_bars(market, start, end):
    seen, digests, before = {}, [], end
    for _ in range(_MAX_PAGES):
        count = min(CANDLE_COUNT_MAX, (before - start).days)
        if count < 1:
            break
        to = datetime(before.year, before.month, before.day, tzinfo=timezone.utc)
        params = candle_params(market, to, count)
        receipt, page = _receipt(_inquire(daily_candles, market, to, count), CANDLES_DAYS_PATH, params,
                                 MAX_CANDLE_BODY)
        _require(type(page) is list, "UNIVERSE_CANDLES_INVALID")
        digests.append(receipt.sha256)
        fresh = []
        for row in page:
            _require(type(row) is dict and row.get("market") == market, "UNIVERSE_CANDLES_INVALID")
            day, opening, closing = _candle(row)
            if day is None or day in seen:
                continue
            seen[day] = (day, opening, closing) if opening and closing else None
            fresh.append(day)
        if not fresh or len(page) < count:
            break
        before = date.fromisoformat(min(fresh))
    low, high = start.isoformat(), end.isoformat()
    bars = tuple(seen[day] for day in sorted(seen) if seen[day] is not None and low <= day < high)
    return UniverseBars(market=market, bars=bars, receipt_sha256=tuple(digests))


def _candle(row):
    """(date, open, close) of one candle row: the date None unless candle_date_time_utc starts with an ISO day, a
    price None unless it is a finite JSON number above 0 (core/oddsdata/bars.py _make_part)."""
    _require(type(row) is dict, "UNIVERSE_CANDLES_INVALID")
    return _day(row.get("candle_date_time_utc")), _price(row.get("opening_price")), _price(row.get("trade_price"))


def _day(stamp):
    text = stamp[:10] if type(stamp) is str else ""
    try:
        return text if date.fromisoformat(text).isoformat() == text else None
    except ValueError:
        return None


def _price(value):
    if type(value) not in (int, Decimal):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if math.isfinite(result) and result > 0 else None
