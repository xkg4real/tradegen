"""Effective-dated market clocks (R-20 rules 1-3; TASK-M1-03; T-CLOSE-01, T-CLOSE-02, T-SAT-01, T-TZ-01,
T-TZ-02, T-XMKT-01, T-PRINT-01 calendar clauses; `gap_sessions` for R-10).

`decision_time_utc(market, d)` is the scheduled official close of session d (the v1.2 meaning);
`close_print_bound_utc(market, d)` is the decision instant: the scheduled close plus the market's print bound
(KR: the random-end bound of `calendars.KR.random_end`, 30 s since 2015-06-15, 30 s print tolerance plus the
notice's extension before; US: `calendars.US.close_print_bound_s`; JP, CN, HK, TW: 0 s). Every value is a
lookup over the rules-store `calendars` block and the owner-signed files of `core/calendars/data/`; no close
time or bound is a constant here (spec L1285, L4160). A non-session raises `NotASession` and never rolls.

Local-to-UTC conversion uses `zoneinfo` (Asia/Seoul has no DST; America/New_York DST is never a month rule).
`cal` is injected everywhere (tests pin a temp-dir `CalendarSet`); the default is the shipped, unsigned set,
which refuses every clock until the owner signs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from core.calendars.store import (CalendarSet, CalendarUnsigned, MARKET_HOLIDAY_SET, MARKET_TZ, NotASession,
                                  default, effective_config, effective_rows)

M1_MARKETS = ("KR", "US", "JP", "CN", "HK", "TW")
UTC = timezone.utc
# R-17 CRYPTO clock (M10, deferred; T-CRYPTO-01; store `time.markets.CRYPTO` L4163): the venue's daily bar dated d
# closes at 00:00:00Z on d+1, 24/7, declared per venue; 365-day annualisation. No calendar file, no print bound (F-21).
CRYPTO_VENUES = ("UPBIT", "BINANCE", "COINGECKO")
ANNUALISATION_DAYS = {"CRYPTO": 365}          # every other market: 252 (vol_target.annualisation_days L4309)


def annualisation_days(market: str) -> int:
    return ANNUALISATION_DAYS.get(market, 252)


class CloseAfterBound(ValueError):
    """A logged print time later than the close-print bound: fails closed, calendar-review alert, never re-stamped."""


class IntradayPrint(ValueError):
    """A print before the scheduled close is never a close (T-PRINT-01: the -8.11% print of 2026-03-09)."""


@dataclass(frozen=True)
class SessionInfo:
    market: str
    session_date: date
    tz: str
    open_local: Optional[time]
    close_local: time
    open_utc: Optional[datetime]
    close_utc: datetime
    close_print_bound_utc: datetime
    closing_call_local: Optional[tuple[time, time]]
    lunch_break_local: Optional[tuple[time, time]]
    flags: frozenset[str]
    random_end: Optional[dict]
    calendar_version: str


@dataclass(frozen=True)
class CloseStamp:
    obs_utc: datetime
    available_at_utc: datetime
    available_at_source: str          # "exchange_print" | "calendar_bound"


@dataclass(frozen=True)
class CompletenessReport:
    missing: tuple[date, ...]         # sessions without a close row
    duplicates: tuple[date, ...]      # sessions with more than one close row
    extra: tuple[date, ...]           # close rows on non-sessions

    @property
    def ok(self) -> bool:
        return not (self.missing or self.duplicates or self.extra)


def _hhmm(text, what: str) -> time:
    if not isinstance(text, str):
        raise ValueError(f"{what}: time must be a quoted 'HH:MM' string, got {text!r}")
    h, m = text.split(":")[:2]
    return time(int(h), int(m))


def _date(d) -> date:
    if not isinstance(d, date) or isinstance(d, datetime):
        raise TypeError(f"session_date must be a datetime.date, got {type(d).__name__}")
    return d


def _utc(d: date, t: time, tz: str) -> datetime:
    return datetime.combine(d, t, tzinfo=ZoneInfo(tz)).astimezone(UTC)


def _market(market: str) -> str:
    if market not in M1_MARKETS:
        raise KeyError(f"{market!r}: not an M1 market ({', '.join(M1_MARKETS)}); CRYPTO is M10 (R-17)")
    return market


def _rows(cal: CalendarSet, file_id: str, kind: str, d: date | None = None) -> list[dict]:
    rows = [r for r in cal.file(file_id).rows if r.get("kind") == kind]
    return effective_rows(rows, d) if d is not None else rows


def _kr_sessions_row(cal: CalendarSet, kind: str, d: date, what: str) -> dict:
    found = _rows(cal, "kr_sessions", kind, d)
    if len(found) != 1:
        raise CalendarUnsigned(f"kr_sessions: {what} for {d.isoformat()} not in the signed file "
                               f"({len(found)} rows); the value comes from the KRX notice at the owner's sign-off")
    return found[0]


def _close_time_of(cal: CalendarSet, market: str, d: date) -> tuple[time, str, frozenset[str]]:
    """(local scheduled close, tz, flags) after coverage and session checks."""
    cfg = cal.market_config(market)
    flags: set[str] = set()
    if market == "KR":
        tz = MARKET_TZ["KR"]
        if d.weekday() == 5:
            flags.add("saturday")
            close = _hhmm(_kr_sessions_row(cal, "saturday_close", d, "saturday_session_close_kst")["close_kst"],
                          "saturday_close")
        elif _is_csat(cal, d):
            flags.add("csat")
            close = _kr_csat_window(cal, d)[1]
        else:
            close = _hhmm(effective_config(cfg["close_kst"], d, "calendars.KR.close_kst")["time"], "close_kst")
        if _is_first_trading_day(cal, d):
            flags.add("first_trading_day")
        return close, tz, frozenset(flags)
    closed, early, _extra = cal.holiday_set(MARKET_HOLIDAY_SET[market])
    if d in early:
        flags.add("early_close")
        if market == "US":
            tz = cfg["tz"]
        else:
            tz = _other_close_row(cal, market, d)["tz"] if market in ("CN", "HK", "TW") else MARKET_TZ[market]
        return _hhmm(early[d], f"holidays_{MARKET_HOLIDAY_SET[market]} early close"), tz, frozenset(flags)
    if market == "US":
        return _hhmm(cfg["close_et"], "close_et"), cfg["tz"], frozenset(flags)
    if market == "JP":
        return (_hhmm(effective_config(cfg["close_jst"], d, "calendars.JP.close_jst")["time"], "close_jst"),
                MARKET_TZ["JP"], frozenset(flags))
    row = _other_close_row(cal, market, d)
    return _hhmm(row["close_local"], f"market_closes.{market}"), row["tz"], frozenset(flags)


def _other_close_row(cal: CalendarSet, market: str, d: date) -> dict:
    rows = [r for r in _rows(cal, "market_closes", "close", d) if r.get("market") == market]
    if len(rows) != 1:
        raise CalendarUnsigned(f"market_closes: {len(rows)} close rows for {market} on {d.isoformat()} "
                               "(exactly one signed row from the exchange notice required)")
    return rows[0]


def _is_csat(cal: CalendarSet, d: date) -> bool:
    return any(r["date"] == d.isoformat() for r in _rows(cal, "kr_sessions", "csat_day"))


def _kr_csat_window(cal: CalendarSet, d: date) -> tuple[time, time]:
    """The CSAT session window: a signed `csat_window` row governs; else the config entry (pre-2016 UNVERIFIED)."""
    rows = _rows(cal, "kr_sessions", "csat_window", d)
    if len(rows) > 1:
        raise CalendarUnsigned(f"kr_sessions: {len(rows)} csat_window rows effective on {d.isoformat()}")
    window = rows[0]["window_kst"] if rows else effective_config(
        cal.market_config("KR")["csat_session_kst"], d, "calendars.KR.csat_session_kst")["window"]
    if not isinstance(window, list) or len(window) != 2:
        raise CalendarUnsigned(f"kr_sessions: CSAT window for {d.isoformat()} is {window!r}, not a signed [open, close]")
    return _hhmm(window[0], "csat open"), _hhmm(window[1], "csat close")


def _is_first_trading_day(cal: CalendarSet, d: date) -> bool:
    probe = date(d.year, 1, 1)
    while probe < d:
        if is_session("KR", probe, cal=cal):
            return False
        probe += timedelta(days=1)
    return True


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
def is_session(market: str, d: date, *, cal: CalendarSet | None = None) -> bool:
    """True/False inside coverage; raises `CalendarCoverageError` outside and `CalendarUnsigned` when unsigned."""
    if market == "CRYPTO":
        _date(d)
        return True                                    # 24/7 (R-17): NotASession is never raised
    cal, d = cal or default(), _date(d)
    set_id = MARKET_HOLIDAY_SET[_market(market)]
    if market == "KR":
        cal.require_covered("kr_sessions", d)
    cal.require_covered(f"holidays_{set_id}", d)
    closed, _early, extra = cal.holiday_set(set_id)
    if d in closed:
        return False
    if d.weekday() < 5 or d in extra:
        return True
    if market == "KR" and d.weekday() == 5:
        before = date.fromisoformat(cal.market_config("KR")["saturday_sessions_before"])
        return d < before
    return False


def next_session(market: str, d: date, *, cal: CalendarSet | None = None) -> date:
    """The first session strictly after d (raises CalendarCoverageError when coverage runs out)."""
    probe = _date(d) + timedelta(days=1)
    while not is_session(market, probe, cal=cal):
        probe += timedelta(days=1)
    return probe


def prev_session(market: str, d: date, *, cal: CalendarSet | None = None) -> date:
    probe = _date(d) - timedelta(days=1)
    while not is_session(market, probe, cal=cal):
        probe -= timedelta(days=1)
    return probe


def sessions_between(market: str, lo: date, hi: date, *, cal: CalendarSet | None = None) -> list[date]:
    out, probe = [], _date(lo)
    while probe <= hi:
        if is_session(market, probe, cal=cal):
            out.append(probe)
        probe += timedelta(days=1)
    return out


# --------------------------------------------------------------------------- #
# Clocks
# --------------------------------------------------------------------------- #
def decision_time_utc(market: str, session_date: date, *, cal: CalendarSet | None = None) -> datetime:
    """The scheduled official close of `session_date`, tz-aware UTC. Raises NotASession on a non-session.
    CRYPTO: 00:00:00Z of d+1, the close of the venue's daily bar dated d (R-17; T-CRYPTO-01)."""
    if market == "CRYPTO":
        d = _date(session_date)
        return datetime(d.year, d.month, d.day, tzinfo=UTC) + timedelta(days=1)
    cal, d = cal or default(), _date(session_date)
    if not is_session(market, d, cal=cal):
        raise NotASession(f"{market} {d.isoformat()} is not a session; decision_time_utc never rolls forward")
    close, tz, _flags = _close_time_of(cal, market, d)
    return _utc(d, close, tz)


def _bound_seconds(cal: CalendarSet, market: str, d: date) -> tuple[int, Optional[dict]]:
    cfg = cal.market_config(market)
    if market != "KR":
        return int(cfg["close_print_bound_s"]), None
    rule = effective_config(cfg["random_end"], d, "calendars.KR.random_end")
    if rule.get("kind") == "unconditional":
        return int(rule["max_s"]), rule
    ext = [r for r in _rows(cal, "kr_sessions", "random_end_extension") if r.get("session_date") == d.isoformat()]
    if len(ext) > 1:
        raise CalendarUnsigned(f"kr_sessions: {len(ext)} random_end_extension rows for {d.isoformat()}")
    return int(rule["print_tolerance_s"]) + (int(ext[0]["extension_s"]) if ext else 0), rule


def close_print_bound_utc(market: str, session_date: date, *, cal: CalendarSet | None = None) -> datetime:
    """The decision instant: scheduled close + the print bound (spec L1308-L1310, L2029); CRYPTO: 0 s (F-21)."""
    if market == "CRYPTO":
        return decision_time_utc(market, session_date)
    cal = cal or default()
    seconds, _rule = _bound_seconds(cal, market, _date(session_date))
    return decision_time_utc(market, session_date, cal=cal) + timedelta(seconds=seconds)


def session(market: str, session_date: date, *, cal: CalendarSet | None = None) -> SessionInfo:
    cal, d = cal or default(), _date(session_date)
    close_utc = decision_time_utc(market, d, cal=cal)
    close, tz, flags = _close_time_of(cal, market, d)
    seconds, random_end = _bound_seconds(cal, market, d)
    cfg = cal.market_config(market)
    open_local: Optional[time] = None
    call: Optional[tuple[time, time]] = None
    lunch: Optional[tuple[time, time]] = None
    if market == "KR":
        if "csat" in flags:
            open_local = _kr_csat_window(cal, d)[0]
            w = effective_config(cfg["csat_closing_call_kst"], d, "calendars.KR.csat_closing_call_kst")["window"]
            rows = _rows(cal, "kr_sessions", "csat_closing_call", d)
            w = rows[0]["window_kst"] if rows else w
            call = (_hhmm(w[0], "csat call"), _hhmm(w[1], "csat call")) if isinstance(w, list) else None
        else:
            if "first_trading_day" in flags:
                open_local = _hhmm(cfg["first_trading_day_open_kst"], "first_trading_day_open_kst")
            else:
                open_local = _hhmm(_kr_sessions_row(cal, "regular_open", d, "regular open")["open_kst"], "open")
            if "saturday" not in flags:
                w = effective_config(cfg["closing_call_kst"], d, "calendars.KR.closing_call_kst")["window"]
                call = (_hhmm(w[0], "closing call"), _hhmm(w[1], "closing call"))
        lunch_rows = _rows(cal, "kr_sessions", "lunch_break", d)
        if lunch_rows:
            w = lunch_rows[0]["window_kst"]
            lunch = (_hhmm(w[0], "lunch"), _hhmm(w[1], "lunch"))
    elif market == "US":
        open_local = time(9, 30)   # the US session of the rules store `time.markets.US.session` (display only)
    elif market in ("CN", "HK", "TW"):
        row = _other_close_row(cal, market, d)
        open_local = _hhmm(row["open_local"], "open") if row.get("open_local") else None
    open_utc = _utc(d, open_local, tz) if open_local else None
    return SessionInfo(market=market, session_date=d, tz=tz, open_local=open_local, close_local=close,
                       open_utc=open_utc, close_utc=close_utc,
                       close_print_bound_utc=close_utc + timedelta(seconds=seconds),
                       closing_call_local=call, lunch_break_local=lunch, flags=flags,
                       random_end=dict(random_end) if random_end else None, calendar_version=cal.version)


def close_stamp(market: str, session_date: date, print_utc: datetime | None = None, *,
                cal: CalendarSet | None = None) -> CloseStamp:
    """How an official close of `session_date` is stamped (spec L2025-L2031): `obs_utc` = the scheduled close;
    `available_at_utc` = the logged exchange print time, else the bound (`calendar_bound`). A print after the
    bound raises `CloseAfterBound` (fail closed, calendar-review alert, never re-stamped); a print before the
    scheduled close raises `IntradayPrint` (an intraday print is never a close). A receipt time is never given here.
    """
    cal = cal or default()
    obs = decision_time_utc(market, session_date, cal=cal)
    bound = close_print_bound_utc(market, session_date, cal=cal)
    if print_utc is None:
        return CloseStamp(obs, bound, "calendar_bound")
    if print_utc.tzinfo is None:
        raise ValueError("print_utc must be tz-aware")
    if print_utc < obs:
        raise IntradayPrint(f"{market} {session_date}: print at {print_utc.isoformat()} precedes the scheduled "
                            f"close {obs.isoformat()}; an intraday print is never stored as a close")
    if print_utc > bound:
        raise CloseAfterBound(f"{market} {session_date}: print at {print_utc.isoformat()} exceeds the close-print "
                              f"bound {bound.isoformat()}; fails closed (calendar-review alert), never re-stamped")
    return CloseStamp(obs, print_utc.astimezone(UTC), "exchange_print")


# --------------------------------------------------------------------------- #
# Cross-market availability (R-19 rule 6; T-XMKT-01, T-TZ-01)
# --------------------------------------------------------------------------- #
def cross_market_usable(other: str, obs_date: date, decision_utc: datetime, *,
                        cal: CalendarSet | None = None) -> bool:
    """A close of market `other` dated D is usable at `decision_utc` iff bound(other, D) + buffer < decision_utc."""
    cal = cal or default()
    if other == "HK":
        return False        # spec L1967: a same-date HKEX close never enters; brief F-20 (one day of lag, no look-ahead)
    bound = close_print_bound_utc(other, obs_date, cal=cal)
    return bound + timedelta(seconds=cal.buffer_s) < decision_utc


def latest_usable_close(other: str, market: str, session_date: date, *, cal: CalendarSet | None = None) -> date:
    """The latest session of `other` whose close is usable at the decision of `market` on `session_date`."""
    cal = cal or default()
    decision = close_print_bound_utc(market, session_date, cal=cal)
    probe = session_date
    for _ in range(40):
        if is_session(other, probe, cal=cal) and cross_market_usable(other, probe, decision, cal=cal):
            return probe
        probe -= timedelta(days=1)
    raise ValueError(f"no usable {other} close within 40 days before {session_date}")


# --------------------------------------------------------------------------- #
# Event-time mapping and gap tags (R-10 data; T-TZ-02, I-06b)
# --------------------------------------------------------------------------- #
def kr_open_gap_session(event_utc: datetime, *, cal: CalendarSet | None = None) -> date:
    """The first KRX session whose open is later than `event_utc` (FOMC 2026-09-16 18:00Z -> 2026-09-17)."""
    cal = cal or default()
    if event_utc.tzinfo is None:
        raise ValueError("event_utc must be tz-aware")
    probe = event_utc.astimezone(ZoneInfo(MARKET_TZ["KR"])).date()
    for _ in range(30):
        if is_session("KR", probe, cal=cal):
            info = session("KR", probe, cal=cal)
            if info.open_utc is not None and info.open_utc > event_utc:
                return probe
        probe += timedelta(days=1)
    raise ValueError(f"no KRX open within 30 days after {event_utc.isoformat()}")


def gap_sessions(market: str, session_date: date, *, other: str = "US", cal: CalendarSet | None = None) -> int:
    """n_US >= 0: sessions of `other` whose close falls after the previous `market` close and before this one."""
    cal = cal or default()
    prev = prev_session(market, session_date, cal=cal)
    lo, hi = decision_time_utc(market, prev, cal=cal), decision_time_utc(market, session_date, cal=cal)
    n = 0
    for d in sessions_between(other, prev - timedelta(days=1), session_date, cal=cal):
        if lo < decision_time_utc(other, d, cal=cal) < hi:
            n += 1
    return n


def completeness_check(market: str, close_dates, start: date, end: date, *,
                       cal: CalendarSet | None = None) -> CompletenessReport:
    """Every session in [start, end] has exactly one close row (T-SAT-01: a KOSPI file lacking the pre-1998-12-12
    Saturdays fails). `close_dates` is any iterable of dates (duplicates count)."""
    cal = cal or default()
    counts: dict[date, int] = {}
    for d in close_dates:
        counts[d] = counts.get(d, 0) + 1
    sessions = sessions_between(market, start, end, cal=cal)
    missing = tuple(d for d in sessions if counts.get(d, 0) == 0)
    dup = tuple(d for d in sessions if counts.get(d, 0) > 1)
    extra = tuple(sorted(d for d in counts if start <= d <= end and not is_session(market, d, cal=cal)))
    return CompletenessReport(missing, dup, extra)
