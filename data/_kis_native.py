"""Tier A native bridge for KIS market-data frame scanning and sliding-window metrics.

Delegates to the verified ``core.compliance.native_accel`` C++20 engine when
available and enabled; returns ``None`` whenever native execution is disabled or
precision falls outside ``1e-18`` so ``data/kis_live.py`` executes its pure-Python
reference implementation transparently.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, localcontext

from core.compliance import native_accel

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_STATE_CODES = {
    "reported": 0,
    "indicator": 1,
    "delayed": 2,
    "indicative": 3,
    "unknown": 3,
}


def _to_us(moment: datetime) -> int:
    delta = moment.astimezone(timezone.utc) - _EPOCH
    return (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds


def _ratio_int(num: int, den: int) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 34
        return Decimal(num) / Decimal(den)


def parse_caret_fields(payload: str, expected_fields: int, max_field_len: int = 128) -> tuple[str, ...] | bool | None:
    """Return tuple of decoded fields, False if invalid frame, or None to use Python fallback."""
    encoded = payload.encode("utf-8")
    return native_accel.kis_parse_caret_fields(encoded, expected_fields, max_field_len)


def validate_book_levels(
    raw_levels: list[tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]],
    *,
    allow_crossed: bool,
) -> bool | None:
    """Return True if valid, False if invalid, or None if native unavailable/fallback."""
    res = native_accel.validate_book_levels(tuple(raw_levels), allow_crossed=allow_crossed)
    if res is None:
        return None
    return bool(res["valid"])


def compute_metrics(
    trades: tuple,
    book,
    *,
    now: datetime,
    window_seconds: int,
    trade_fresh: bool,
    book_fresh: bool,
) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None, int] | None:
    """Compute (spread, imbalance, window_return, vwap, sample_count) via C++20 HP-4/HP-5, or None."""
    spread = None
    imbalance = None
    if book_fresh and book is not None and book.levels:
        raw_levels = tuple((lv.bid, lv.bid_size, lv.ask, lv.ask_size) for lv in book.levels)
        book_res = native_accel.validate_book_levels(
            raw_levels,
            allow_crossed=(book.state == "indicative"),
        )
        if book_res is None or not book_res["valid"]:
            return None
        if book_res["spread"] is not None:
            with localcontext() as ctx:
                ctx.prec = 34
                spread = +book_res["spread"]
        if book_res["imbalance_num"] is not None and book_res["imbalance_den"]:
            imbalance = _ratio_int(book_res["imbalance_num"], book_res["imbalance_den"])

    ticks_data = [
        (
            _to_us(t.observed_at),
            _to_us(t.received_at),
            int(t.delay_seconds),
            0 if t.state == "reported" else (3 if t.state in ("indicative", "unknown") else 1),
            t.price,
            t.size,
        )
        for t in trades
    ]
    win_res = native_accel.kis_window_metrics(
        ticks_data,
        now_us=_to_us(now),
        window_us=int(window_seconds) * 1_000_000,
        trade_fresh=bool(trade_fresh),
    )
    if win_res is None:
        return None

    window_return = None
    if win_res["ret_num"] is not None and win_res["ret_den"]:
        window_return = _ratio_int(win_res["ret_num"], win_res["ret_den"])

    vwap = None
    if win_res["vwap_num"] is not None and win_res["vwap_den"]:
        vwap = _ratio_int(win_res["vwap_num"], win_res["vwap_den"])

    return spread, imbalance, window_return, vwap, int(win_res["sample_count"])
