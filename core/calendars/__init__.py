"""Exchange holiday and special-session data, loaded from static JSON.

The files under `data/calendars/` are generated offline by
`pkg_tools/generate_calendars.py` from the `exchange_calendars` library, which
is not a runtime dependency. That keeps the deliverable lean and the lookup
fast — the whole table is a few dictionaries of date strings, resolved in
constant time — while the dates themselves come from a maintained source rather
than being typed by hand.

THE RULE THAT MATTERS
---------------------
`is_trading_day` returns `True`, `False`, or **`None` for a date outside the
generated coverage**. `None` is not "probably open". Every caller must treat it
as "unknown" and fall back to the conservative weekday behaviour, because
silently assuming a venue is open on an uncovered date is precisely the failure
this module exists to prevent.

Coverage is finite by construction — `exchange_calendars` itself only records
some venues a year or two ahead (Shanghai stops at 2026). `stale_markets()`
reports which calendars are close to running out so the operator can regenerate
before it matters, rather than discovering it on a holiday.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "calendars"

# Warn when a calendar has less than this left to run.
STALE_WITHIN = timedelta(days=60)


def _parse_hhmm(text: Optional[str]) -> Optional[time]:
    if not text:
        return None
    try:
        hour, minute = text.split(":")
        return time(int(hour), int(minute))
    except (ValueError, AttributeError):
        return None


@dataclass(frozen=True)
class SpecialSession:
    """A day whose hours differ from the venue's regular pattern."""
    open: Optional[time]
    close: Optional[time]
    break_start: Optional[time] = None
    break_end: Optional[time] = None

    def windows(self) -> tuple[tuple[time, time], ...]:
        if self.open is None or self.close is None:
            return ()
        if self.break_start and self.break_end:
            return ((self.open, self.break_start), (self.break_end, self.close))
        return ((self.open, self.close),)


@dataclass(frozen=True)
class MarketCalendar:
    market: str
    timezone: str
    source: dict
    covers_from: date
    covers_to: date
    holidays: frozenset[str]
    special: dict[str, SpecialSession]

    def covers(self, day: date) -> bool:
        return self.covers_from <= day <= self.covers_to

    def days_remaining(self, today: date) -> int:
        return (self.covers_to - today).days

    def describe_source(self) -> str:
        src = self.source or {}
        return (f"{src.get('calendar', '?')} via "
                f"{src.get('library', '?')} {src.get('version', '?')}, "
                f"generated {src.get('generated', '?')}")


_LOCK = threading.RLock()
_CACHE: Optional[dict[str, MarketCalendar]] = None


def _load() -> dict[str, MarketCalendar]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    with _LOCK:
        if _CACHE is not None:
            return _CACHE
        loaded: dict[str, MarketCalendar] = {}
        if DATA_DIR.is_dir():
            for path in sorted(DATA_DIR.glob("*.json")):
                if path.name == "index.json":
                    continue
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    special = {
                        day: SpecialSession(
                            open=_parse_hhmm(entry.get("open")),
                            close=_parse_hhmm(entry.get("close")),
                            break_start=_parse_hhmm(entry.get("break_start")),
                            break_end=_parse_hhmm(entry.get("break_end")),
                        )
                        for day, entry in (raw.get("special_sessions") or {}).items()
                    }
                    loaded[raw["market"]] = MarketCalendar(
                        market=raw["market"],
                        timezone=raw.get("timezone", ""),
                        source=raw.get("source") or {},
                        covers_from=date.fromisoformat(raw["covers"]["from"]),
                        covers_to=date.fromisoformat(raw["covers"]["to"]),
                        holidays=frozenset(raw.get("holidays") or ()),
                        special=special,
                    )
                except Exception:
                    continue      # one malformed file must not blind the rest
        _CACHE = loaded
        return _CACHE


def reload() -> None:
    """Drop the cache; used after regenerating the data."""
    global _CACHE
    with _LOCK:
        _CACHE = None


def get(market: str) -> Optional[MarketCalendar]:
    return _load().get((market or "").strip().upper())


def loaded_markets() -> tuple[str, ...]:
    return tuple(sorted(_load()))


def is_trading_day(market: str, day: date) -> Optional[bool]:
    """True, False, or None when the date is outside the generated coverage.

    None must never be read as "open".
    """
    calendar = get(market)
    if calendar is None or not calendar.covers(day):
        return None
    if day.weekday() >= 5:
        return False
    return day.isoformat() not in calendar.holidays


def special_session(market: str, day: date) -> Optional[SpecialSession]:
    """Hours for a half-day or late open, when this date has them."""
    calendar = get(market)
    if calendar is None:
        return None
    return calendar.special.get(day.isoformat())


def coverage(market: str) -> Optional[tuple[date, date]]:
    calendar = get(market)
    return None if calendar is None else (calendar.covers_from, calendar.covers_to)


def stale_markets(today: Optional[date] = None,
                  within: timedelta = STALE_WITHIN) -> list[dict]:
    """Calendars that have run out, or are about to.

    Surfaced in the UI: a calendar that expires quietly turns every future
    holiday into an unknown, which is the state this module exists to avoid.
    """
    today = today or datetime.now().date()
    out = []
    for market, calendar in sorted(_load().items()):
        remaining = calendar.days_remaining(today)
        if remaining <= within.days:
            out.append({
                "market": market,
                "covers_to": calendar.covers_to.isoformat(),
                "days_remaining": remaining,
                "expired": remaining < 0,
            })
    return out


def summary() -> dict:
    """Counts for the Settings page."""
    calendars = _load()
    return {
        "markets": len(calendars),
        "holidays": sum(len(c.holidays) for c in calendars.values()),
        "special_sessions": sum(len(c.special) for c in calendars.values()),
        "stale": stale_markets(),
    }


# --------------------------------------------------------------------------- #
# v2.0 (R-20): the effective-dated calendars live in the sibling modules of this
# package and read the owner-signed files under core/calendars/data/. They are
# re-exported lazily so importing the legacy API never loads them (and so
# core.markets, which imports this package, never forms a cycle).
# --------------------------------------------------------------------------- #
_V2_EXPORTS = {
    "clocks": ("NotASession", "SessionInfo", "CloseStamp", "CloseAfterBound", "decision_time_utc",
               "close_print_bound_utc", "is_session", "session", "close_stamp", "next_session",
               "prev_session", "sessions_between", "gap_sessions", "kr_open_gap_session",
               "latest_usable_close", "cross_market_usable", "completeness_check"),
    "publication": ("publication_instant", "next_expected_obs", "add_publication_bdays", "source_skipped",
                    "fed_business_day", "sifma_status", "nyse_holiday", "business_day", "usable_at"),
    "regime": ("regime_tags", "regime_span_covered", "require_regime_span", "TAGS"),
    "store": ("CalendarUnsigned", "CalendarCoverageError", "CalendarFile", "CalendarSet", "default",
              "status", "check_coverage", "content_md5", "record_calendar_changes"),
    "events": ("Event", "load_events", "event_calendar", "release_status"),
    "adapter": ("CalendarClocks", "registry_schedule"),
}
_V2_INDEX = {name: module for module, names in _V2_EXPORTS.items() for name in names}


def __getattr__(name: str):
    module = _V2_INDEX.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib
    return getattr(importlib.import_module(f"{__name__}.{module}"), name)
