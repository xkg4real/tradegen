"""Which venue a rule trades on, who can quote it, and when it is open.

A `Rule` stores a market code. This table is the only place that knows what a
code means: which provider answers for it, what suffix that provider expects on
the symbol, what currency prices come back in, and the venue's trading session.

Keeping it in one table rather than in `if` branches inside the feed matters for
two reasons. Adding a venue is a row, not a code change. And the rule builder
populates its dropdown from here, so the operator can never select a market the
feed cannot actually route.

WHY SESSIONS ARE HERE
---------------------
Quote freshness is meaningless without knowing whether the venue is trading. A
US quote at 02:00 KST is thirteen hours old and perfectly correct — the market
closed. Judging it against a single global bound halted the engine every night.

So each venue carries its trading windows in its own timezone, and the evaluator
asks several questions instead of one:

  * closed right now                  -> skip; a rule cannot execute anyway
  * open, and data is from this session -> apply the tight freshness bound
  * open, but nothing has printed today -> skip; a venue outage, not our own

Windows are a tuple per day, which is what makes lunch breaks expressible: Tokyo
and Hong Kong stop trading for an hour, and treating that gap as "open with
frozen data" would halt the engine every lunchtime.

HOLIDAYS
--------
An earlier build did not enumerate holidays, on the argument that a holiday and
a venue outage are indistinguishable and both skip. That is no longer good
enough: with a real-time feed, an unrecognised holiday means the engine spends
the day reporting "no trade printed" for a market it should have known was
shut, and any freshness reasoning on that day is guesswork.

`core.calendars` therefore carries generated holiday and special-session data
for every venue here, from `exchange_calendars`. `Session` still describes the
regular weekly pattern; `Market.trading_state` combines it with the calendar and
is what callers should use. `Session.is_open` alone would report a public
holiday as open.

Coverage is finite, and a date beyond it reports "unknown" rather than "open".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from core import calendars

KRX = "krx"
FMP = "fmp"

# Weekdays a venue trades. Every venue here is Monday-Friday.
_WEEKDAYS = frozenset({0, 1, 2, 3, 4})

# Beyond this, data is wrong no matter what the calendar says, and the engine
# halts rather than skipping forever. Long enough to span a holiday weekend.
DEFAULT_HARD_AGE_S = 5 * 24 * 3600


@dataclass(frozen=True)
class Session:
    tz: str
    windows: tuple[tuple[time, time], ...]
    days: frozenset[int] = _WEEKDAYS
    # Freshness bound while the venue is actually trading.
    max_age_open_s: float = 120.0
    # Absolute ceiling. Past this the engine halts regardless of the calendar,
    # so a dead feed cannot hide behind "the market must be closed".
    max_age_hard_s: float = DEFAULT_HARD_AGE_S

    def _zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    def local(self, moment: datetime) -> datetime:
        return moment.astimezone(self._zone())

    def is_open(self, moment: datetime) -> bool:
        here = self.local(moment)
        if here.weekday() not in self.days:
            return False
        clock = here.timetz().replace(tzinfo=None)
        return any(start <= clock < end for start, end in self.windows)

    def session_start(self, moment: datetime) -> Optional[datetime]:
        """When today's first window opened, in UTC. None on a non-trading day."""
        here = self.local(moment)
        if here.weekday() not in self.days or not self.windows:
            return None
        first = min(start for start, _ in self.windows)
        return here.replace(hour=first.hour, minute=first.minute,
                            second=0, microsecond=0)

    def previous_close(self, moment: datetime) -> Optional[datetime]:
        """End of the most recent completed trading day, in the venue's zone."""
        here = self.local(moment)
        last = max(end for _, end in self.windows) if self.windows else None
        if last is None:
            return None
        for back in range(0, 10):
            day: date = (here - timedelta(days=back)).date()
            if day.weekday() not in self.days:
                continue
            candidate = datetime.combine(day, last, tzinfo=self._zone())
            if candidate <= here:
                return candidate
        return None

    def describe(self, moment: datetime) -> str:
        here = self.local(moment)
        spans = ", ".join(f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"
                          for s, e in self.windows)
        state = "open" if self.is_open(moment) else "closed"
        return f"{state} · {spans} {here.tzname()}"


@dataclass(frozen=True)
class Market:
    code: str            # what a Rule stores, and what the operator picks
    label: str           # what the dropdown shows
    provider: str        # who answers a quote request
    suffix: str = ""     # appended to the symbol for the provider
    currency: str = ""   # informational; prices are not converted
    example: str = ""    # a real symbol, shown as the field hint
    session: Optional[Session] = None
    # True when FMP answers HTTP 402 without an international plan. Probed
    # against the live API on 2026-08-18: US tickers resolve, every suffixed
    # symbol is refused. Surfaced while authoring a rule so the operator learns
    # this at the form, not from a halted engine.
    needs_intl_plan: bool = False

    # -- calendar-aware trading state ----------------------------------------
    # `Session` knows the regular weekly pattern; the calendar knows which
    # dates are actually sessions and which have unusual hours. These methods
    # combine them, and are what the evaluator should call — `Session` alone
    # would happily report a public holiday as open.

    def local_date(self, moment: datetime) -> Optional[date]:
        return self.session.local(moment).date() if self.session else None

    def windows_for(self, moment: datetime) -> tuple[tuple[time, time], ...]:
        """Trading windows for this date, honouring half-days and late opens."""
        if self.session is None:
            return ()
        day = self.local_date(moment)
        special = calendars.special_session(self.code, day) if day else None
        if special is not None:
            replacement = special.windows()
            if replacement:
                return replacement
        return self.session.windows

    def trading_state(self, moment: datetime) -> tuple[str, str]:
        """(state, why) where state is "open", "closed" or "unknown".

        "unknown" means the date lies outside the generated calendar coverage.
        It is deliberately not folded into "open": the caller decides how to
        treat an unknown, and every caller here treats it conservatively.
        """
        if self.session is None:
            return "unknown", "no session defined"
        here = self.session.local(moment)
        day = here.date()

        trading = calendars.is_trading_day(self.code, day)
        if trading is False:
            if day.weekday() >= 5:
                return "closed", "weekend"
            return "closed", f"exchange holiday ({day.isoformat()})"

        if trading is None:
            # Outside coverage: fall back to the weekly pattern, and say so.
            if here.weekday() not in self.session.days:
                return "closed", "weekend"
            note = "outside calendar coverage; using regular weekly hours"
            clock = here.timetz().replace(tzinfo=None)
            inside = any(s <= clock < e for s, e in self.session.windows)
            return ("open" if inside else "closed"), note

        clock = here.timetz().replace(tzinfo=None)
        windows = self.windows_for(moment)
        if any(s <= clock < e for s, e in windows):
            special = calendars.special_session(self.code, day)
            return "open", ("special session hours" if special else "regular session")
        special = calendars.special_session(self.code, day)
        if special is not None:
            return "closed", f"outside today's special hours ({day.isoformat()})"
        return "closed", "outside trading hours"

    def is_open(self, moment: datetime) -> bool:
        return self.trading_state(moment)[0] == "open"

    def session_start(self, moment: datetime) -> Optional[datetime]:
        """When today's first window opened, using this date's actual hours."""
        if self.session is None:
            return None
        here = self.session.local(moment)
        windows = self.windows_for(moment)
        if not windows:
            return None
        first = min(start for start, _ in windows)
        return here.replace(hour=first.hour, minute=first.minute,
                            second=0, microsecond=0)

    def describe(self, moment: datetime) -> str:
        if self.session is None:
            return "no session defined"
        state, why = self.trading_state(moment)
        spans = ", ".join(f"{s.strftime('%H:%M')}-{e.strftime('%H:%M')}"
                          for s, e in self.windows_for(moment))
        zone = self.session.local(moment).tzname()
        return f"{state} · {why} · {spans} {zone}" if spans else f"{state} · {why}"


def _max_age(code: str, default: float) -> float:
    """Per-venue override, for a book of unusually illiquid names."""
    import os
    raw = (os.getenv(f"NEXTGEN_MAX_AGE_{code}") or "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _s(tz: str, *windows: tuple[str, str], max_age_open_s: float = 120.0) -> Session:
    def parse(text: str) -> time:
        hour, minute = text.split(":")
        return time(int(hour), int(minute))
    return Session(tz=tz,
                   windows=tuple((parse(a), parse(b)) for a, b in windows),
                   max_age_open_s=max_age_open_s)


# The operator's FMP plan is real-time, so the bound is tight enough to catch a
# frozen feed within a few minutes. It is not tighter than that because
# `timestamp` is the last *trade* time: a thinly-traded name can legitimately go
# minutes without printing while the venue is open, and a false halt is
# expensive — it stops every venue and needs a manual re-arm.
#
# Override per venue with NEXTGEN_MAX_AGE_<MARKET>, e.g. NEXTGEN_MAX_AGE_US=600.
_RT_MAX_AGE = 180.0

_MARKETS: tuple[Market, ...] = (
    Market("KRX", "KRX — KOSPI / KOSDAQ", KRX, "", "KRW", "005930",
           _s("Asia/Seoul", ("09:00", "15:30"))),

    Market("US", "United States — NASDAQ / NYSE / AMEX", FMP, "", "USD", "AAPL",
           _s("America/New_York", ("09:30", "16:00"), max_age_open_s=_RT_MAX_AGE)),

    Market("LSE", "United Kingdom — London", FMP, ".L", "GBX", "VOD.L",
           _s("Europe/London", ("08:00", "16:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("XETRA", "Germany — XETRA", FMP, ".DE", "EUR", "SAP.DE",
           _s("Europe/Berlin", ("09:00", "17:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("EURONEXT_PA", "France — Euronext Paris", FMP, ".PA", "EUR", "MC.PA",
           _s("Europe/Paris", ("09:00", "17:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("EURONEXT_AS", "Netherlands — Euronext Amsterdam", FMP, ".AS", "EUR",
           "ASML.AS",
           _s("Europe/Amsterdam", ("09:00", "17:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("BIT", "Italy — Borsa Italiana", FMP, ".MI", "EUR", "ENI.MI",
           _s("Europe/Rome", ("09:00", "17:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("BME", "Spain — BME Madrid", FMP, ".MC", "EUR", "SAN.MC",
           _s("Europe/Madrid", ("09:00", "17:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("SIX", "Switzerland — SIX Swiss", FMP, ".SW", "CHF", "NESN.SW",
           _s("Europe/Zurich", ("09:00", "17:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("OMX_ST", "Sweden — Nasdaq Stockholm", FMP, ".ST", "SEK", "VOLV-B.ST",
           _s("Europe/Stockholm", ("09:00", "17:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("OSE", "Norway — Oslo Børs", FMP, ".OL", "NOK", "EQNR.OL",
           _s("Europe/Oslo", ("09:00", "16:20"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),

    # Tokyo, Hong Kong and the mainland Chinese venues break for lunch. The gap
    # is expressed as two windows so the engine does not read a quiet hour as a
    # frozen feed.
    Market("TSE", "Japan — Tokyo", FMP, ".T", "JPY", "7203.T",
           _s("Asia/Tokyo", ("09:00", "11:30"), ("12:30", "15:30"),
              max_age_open_s=_RT_MAX_AGE), needs_intl_plan=True),
    Market("HKEX", "Hong Kong", FMP, ".HK", "HKD", "0700.HK",
           _s("Asia/Hong_Kong", ("09:30", "12:00"), ("13:00", "16:00"),
              max_age_open_s=_RT_MAX_AGE), needs_intl_plan=True),
    Market("SSE", "China — Shanghai", FMP, ".SS", "CNY", "600519.SS",
           _s("Asia/Shanghai", ("09:30", "11:30"), ("13:00", "15:00"),
              max_age_open_s=_RT_MAX_AGE), needs_intl_plan=True),
    Market("SZSE", "China — Shenzhen", FMP, ".SZ", "CNY", "000001.SZ",
           _s("Asia/Shanghai", ("09:30", "11:30"), ("13:00", "15:00"),
              max_age_open_s=_RT_MAX_AGE), needs_intl_plan=True),
    Market("TWSE", "Taiwan", FMP, ".TW", "TWD", "2330.TW",
           _s("Asia/Taipei", ("09:00", "13:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("SGX", "Singapore", FMP, ".SI", "SGD", "D05.SI",
           _s("Asia/Singapore", ("09:00", "12:00"), ("13:00", "17:00"),
              max_age_open_s=_RT_MAX_AGE), needs_intl_plan=True),
    Market("NSE", "India — NSE", FMP, ".NS", "INR", "RELIANCE.NS",
           _s("Asia/Kolkata", ("09:15", "15:30"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("ASX", "Australia", FMP, ".AX", "AUD", "BHP.AX",
           _s("Australia/Sydney", ("10:00", "16:00"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),

    Market("TSX", "Canada — Toronto", FMP, ".TO", "CAD", "RY.TO",
           _s("America/Toronto", ("09:30", "16:00"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("B3", "Brazil — B3", FMP, ".SA", "BRL", "PETR4.SA",
           _s("America/Sao_Paulo", ("10:00", "18:00"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
    Market("BMV", "Mexico", FMP, ".MX", "MXN", "WALMEX.MX",
           _s("America/Mexico_City", ("08:30", "15:00"), max_age_open_s=_RT_MAX_AGE),
           needs_intl_plan=True),
)

def _with_overrides(markets: tuple[Market, ...]) -> tuple[Market, ...]:
    """Apply NEXTGEN_MAX_AGE_<MARKET> once the codes are known."""
    from dataclasses import replace
    out = []
    for market in markets:
        session = market.session
        if session is not None:
            tuned = _max_age(market.code, session.max_age_open_s)
            if tuned != session.max_age_open_s:
                session = replace(session, max_age_open_s=tuned)
                market = replace(market, session=session)
        out.append(market)
    return tuple(out)


_MARKETS = _with_overrides(_MARKETS)

BY_CODE: dict[str, Market] = {m.code: m for m in _MARKETS}


def all_markets() -> tuple[Market, ...]:
    return _MARKETS


def get(code: str) -> Optional[Market]:
    return BY_CODE.get((code or "").strip().upper())


def codes() -> tuple[str, ...]:
    return tuple(m.code for m in _MARKETS)


def options() -> tuple[tuple[str, str], ...]:
    """(code, label) pairs for the rule builder dropdown."""
    return tuple((m.code, m.label) for m in _MARKETS)


def provider_for(code: str) -> str:
    market = get(code)
    return market.provider if market else ""


def session_for(code: str) -> Optional[Session]:
    market = get(code)
    return market.session if market else None


def is_open(code: str, moment: datetime) -> Optional[bool]:
    """True/False, or None when the venue is unknown to this build."""
    market = get(code)
    if market is None or market.session is None:
        return None
    return market.is_open(moment)


def trading_state(code: str, moment: datetime) -> tuple[str, str]:
    market = get(code)
    if market is None:
        return "unknown", f"{code or '(blank)'} is not a known venue"
    return market.trading_state(moment)


def provider_symbol(code: str, symbol: str) -> str:
    """The symbol as the provider expects it.

    Idempotent: an operator who already typed `VOD.L` gets `VOD.L`, not
    `VOD.L.L`.
    """
    symbol = (symbol or "").strip()
    market = get(code)
    if market is None or not market.suffix or not symbol:
        return symbol
    if symbol.upper().endswith(market.suffix.upper()):
        return symbol
    return f"{symbol}{market.suffix}"


def currency_for(code: str) -> str:
    market = get(code)
    return market.currency if market else ""


def example_for(code: str) -> str:
    market = get(code)
    return market.example if market else ""


# --------------------------------------------------------------------------- #
# v2.0 market ids (spec section 6.1; rulings section 3.4). The macro layer speaks
# market ids; venue codes stay inside this module.
# --------------------------------------------------------------------------- #
MACRO_MARKETS: tuple[str, ...] = ("KR", "US", "JP", "EU", "TW", "CN", "HK", "IN", "EM", "CRYPTO", "FX")
_MARKET_VENUE: dict[str, str] = {"KR": "KRX", "US": "US", "JP": "TSE", "CN": "SSE", "HK": "HKEX", "TW": "TWSE"}
_VENUE_MARKET: dict[str, str] = {v: k for k, v in _MARKET_VENUE.items()}
_VENUE_MARKET["SZSE"] = "CN"


def market_to_venue(market: str) -> str:
    """Section 6.1 market id -> the venue code of this table; KeyError for a market with no single venue."""
    key = (market or "").strip().upper()
    if key not in MACRO_MARKETS:
        raise KeyError(f"{market!r}: not a section 6.1 market id {MACRO_MARKETS}")
    if key not in _MARKET_VENUE:
        raise KeyError(f"{market!r}: no venue mapped in M1 (EU, IN, EM, CRYPTO, FX are later milestones)")
    return _MARKET_VENUE[key]


def venue_to_market(venue: str) -> str:
    key = (venue or "").strip().upper()
    if key not in _VENUE_MARKET:
        raise KeyError(f"{venue!r}: venue has no section 6.1 market id")
    return _VENUE_MARKET[key]
