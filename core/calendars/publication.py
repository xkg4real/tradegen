"""Publication calendars, separate holiday sets, source exceptions and `usable_at` (R-19 rule 2, R-20 rule 2;
TASK-M1-06, TASK-M1-18; T-H15-01, T-H10-02, T-VIX-01, T-AVAIL-01, T-TZ-01, T-XMKT-01 calendar clauses).

The eleven holiday sets (KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS) stay separate: on
Columbus and Veterans Day the NYSE is open and the Fed is closed (spec L2024). Publication business days come
from the publisher's calendar, decision business days from the exchange calendar (L541, L4166).

A series' schedule is `{rule, calendar, time, tz, obs_calendar, grace_publication_bdays, ...}`: a dict passed by
the caller, a `schedule_id` resolved through the signed `publication_schedules` file (effective-dated rows), or a
series id resolved through the series registry (lazy import; the registry is package A's).

Rules (spec L1297-L1305, L1847-L1852, L4167-L4173):
  next_bday_after_obs    H.15: `time` on the next business day of `calendar` after D
  monday_after_week      H.10: Monday after D's week; the next business day when that Monday is closed
  same_day               Treasury par (18:00 ET), BLS (08:30 ET), VIX official close (16:15 ET), ECOS 15:30 KST
  channel_posting_time   FRED re-posting: the logged `posting_utc`, else the declared lag (OWNER measurement)
  market_close           a close of `market`: `close_print_bound_utc(market, D)`
  release_calendar       BLS / BEA release dates (owner-supplied list in the schedule; the M5 event store later)
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from core.calendars import clocks
from core.calendars.store import (HOLIDAY_SETS, MARKET_HOLIDAY_SET, MARKET_TZ, CalendarSet, CalendarUnsigned,
                                  default, effective_rows)

SET_TO_MARKET = {v: k for k, v in MARKET_HOLIDAY_SET.items()}
RULES = ("next_bday_after_obs", "monday_after_week", "same_day", "channel_posting_time", "market_close",
         "release_calendar")
UTC = timezone.utc


class NoExpectedObservation(Exception):
    """The release event is cancelled: no expected instant (spec L1367; the Oct-2025 CPI)."""


class ReleaseDelayed(Exception):
    """The release event is delayed with no released instant yet."""


# --------------------------------------------------------------------------- #
# Holiday sets
# --------------------------------------------------------------------------- #
def business_day(calendar_id: str, d: date, *, cal: CalendarSet | None = None) -> bool:
    """Business day of a holiday set or market id: exchange sets use `is_session`; FED, SIFMA, CBOE, CME, ECOS are
    Monday-Friday minus their closed dates (plus any recorded weekend open). `WEEKDAYS` = Mon-Fri."""
    cal = cal or default()
    if calendar_id == "WEEKDAYS":
        return d.weekday() < 5
    market = calendar_id if calendar_id in MARKET_HOLIDAY_SET else SET_TO_MARKET.get(calendar_id)
    if market is not None:
        return clocks.is_session(market, d, cal=cal)
    if calendar_id not in HOLIDAY_SETS:
        raise KeyError(f"{calendar_id!r}: not a holiday set ({', '.join(HOLIDAY_SETS)}) or market")
    cal.require_covered(f"holidays_{calendar_id}", d)
    closed, _early, extra = cal.holiday_set(calendar_id)
    return d not in closed and (d.weekday() < 5 or d in extra)


def fed_business_day(d: date, *, cal: CalendarSet | None = None) -> bool:
    return business_day("FED", d, cal=cal)


def nyse_holiday(d: date, *, cal: CalendarSet | None = None) -> bool:
    """Membership in the NYSE closed set only (weekends are not holidays)."""
    cal = cal or default()
    cal.require_covered("holidays_NYSE", d)
    return d in cal.holiday_set("NYSE")[0]


def sifma_status(d: date, *, cal: CalendarSet | None = None) -> str:
    """'open' | 'early_close' | 'closed' per the SIFMA recommendations."""
    cal = cal or default()
    cal.require_covered("holidays_SIFMA", d)
    closed, early, extra = cal.holiday_set("SIFMA")
    if d in closed or (d.weekday() >= 5 and d not in extra):
        return "closed"
    return "early_close" if d in early else "open"


def _step_bdays(calendar_id: str, d: date, n: int, cal: CalendarSet) -> date:
    step = 1 if n >= 0 else -1
    for _ in range(abs(n)):
        d += timedelta(days=step)
        while not business_day(calendar_id, d, cal=cal):
            d += timedelta(days=step)
    return d


# --------------------------------------------------------------------------- #
# Schedules
# --------------------------------------------------------------------------- #
def _registry_schedule(series_id: str) -> dict:
    """A bare series id resolves through the shipped registry (core.calendars.adapter.registry_schedule): the
    registry names the schedule id, the signed publication_schedules row supplies rule, time and tz."""
    try:
        from core.calendars.adapter import registry_schedule
        from core.ficc import contracts
        sched = registry_schedule(contracts.default_registry(), series_id)
    except Exception as exc:      # no registry on this path: the caller passes the schedule dict
        raise KeyError(f"{series_id}: schedule not resolvable through core.ficc.contracts ({exc}); "
                       "pass the schedule dict") from None
    if sched is None:
        raise KeyError(f"{series_id}: no scheduled publication instant (LIVE_QUOTE / AS_POSTED / DERIVED)")
    return sched


def schedule_of(series, obs_date: date, *, cal: CalendarSet | None = None) -> dict:
    """The resolved schedule dict for `series` (str id or dict) effective on `obs_date`."""
    cal = cal or default()
    sched = dict(series) if isinstance(series, dict) else _registry_schedule(str(series))
    sid = sched.get("schedule_id")
    if sid:
        rows = [r for r in effective_rows(cal.file("publication_schedules").rows, obs_date) if r.get("schedule_id") == sid]
        if len(rows) != 1:
            raise CalendarUnsigned(f"publication_schedules: {len(rows)} rows for {sid!r} effective on "
                                   f"{obs_date.isoformat()} (exactly one signed row required)")
        merged = {k: v for k, v in rows[0].items() if k not in ("kind",)}
        merged.update({k: v for k, v in sched.items() if v is not None})
        sched = merged
    if sched.get("rule") not in RULES:
        raise KeyError(f"schedule rule {sched.get('rule')!r} unknown; one of {RULES}")
    return sched


def _instant(d: date, hhmm: str, tz: str) -> datetime:
    h, m = hhmm.split(":")[:2]
    return datetime.combine(d, time(int(h), int(m)), tzinfo=ZoneInfo(tz)).astimezone(UTC)


def _parse_utc(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"{text}: instants must be tz-aware")
    return dt.astimezone(UTC)


def publication_instant(series, obs_date: date, *, cal: CalendarSet | None = None,
                        events: Iterable = ()) -> datetime:
    """UTC instant at which the observation dated `obs_date` is published (R-19 step 2)."""
    cal = cal or default()
    s = schedule_of(series, obs_date, cal=cal)
    rule, tz, t = s["rule"], s.get("tz"), s.get("time")
    if rule == "market_close":
        return clocks.close_print_bound_utc(s["market"], obs_date, cal=cal)
    if rule == "next_bday_after_obs":
        instant = _instant(_step_bdays(s["calendar"], obs_date, 1, cal), t, tz)
    elif rule == "monday_after_week":
        monday = obs_date + timedelta(days=7 - obs_date.weekday())
        while not business_day(s["calendar"], monday, cal=cal):
            monday += timedelta(days=1)
        instant = _instant(monday, t, tz)
    elif rule == "same_day":
        instant = _instant(obs_date, t, tz)
    elif rule == "channel_posting_time":
        if s.get("posting_utc"):
            instant = _parse_utc(s["posting_utc"])            # logged (live): FRED last_updated
        else:                                                   # declared (history): OWNER measurement (L1426)
            lag = int(s.get("declared_lag_bdays", 1))
            instant = _instant(_step_bdays(s["calendar"], obs_date, lag, cal), s.get("declared_time", t), tz)
    else:                                                       # release_calendar
        dates = s.get("release_dates") or {}
        rel = dates.get(obs_date.isoformat()) if isinstance(dates, dict) else None
        if rel is None:
            raise KeyError(f"{s.get('series_id') or s.get('schedule_id')}: no release date for {obs_date} "
                           "(BLS/BEA release calendar: owner input; the M5 event store)")
        instant = _instant(date.fromisoformat(rel), t, tz)
    et = s.get("release_event_type")
    if et and events:
        local_day = instant.astimezone(ZoneInfo(tz)).date() if tz else instant.date()
        status, released = release_status(events, et, local_day, tz or "UTC")
        if status == "cancelled":
            raise NoExpectedObservation(f"{et} on {local_day}: cancelled, no expected observation")
        if status == "delayed":
            if released is None:
                raise ReleaseDelayed(f"{et} on {local_day}: delayed, not yet released")
            instant = released
    return instant


def release_status(events: Iterable, event_type: str, scheduled_local_date: date, tz: str):
    """(status, released_utc) of the event of `event_type` scheduled on that local date; ('scheduled', None) if none."""
    for ev in events:
        get = ev.get if isinstance(ev, dict) else lambda k, _ev=ev: getattr(_ev, k, None)
        if get("type") != event_type:
            continue
        sched = get("scheduled_utc")
        sched = _parse_utc(sched) if isinstance(sched, str) else sched
        if sched.astimezone(ZoneInfo(tz)).date() == scheduled_local_date:
            rel = get("released_utc")
            return get("status"), (_parse_utc(rel) if isinstance(rel, str) else rel)
    return "scheduled", None


def source_skipped(series, *, cal: CalendarSet | None = None) -> frozenset[date]:
    """Dates the source legitimately skipped for this series or channel (signed list; spec L1854)."""
    cal = cal or default()
    sid = series.get("series_id") if isinstance(series, dict) else str(series)
    channel = series.get("channel") if isinstance(series, dict) else None
    out = set()
    for row in cal.file("source_skipped").rows:
        if row.get("series") == sid or (channel and row.get("series") == channel):
            out.add(date.fromisoformat(row["date"]))
    return frozenset(out)


def next_expected_obs(series, obs_date: date, *, cal: CalendarSet | None = None) -> date:
    """The next date of the series' `obs_calendar` after `obs_date`, skipping source-exception dates."""
    cal = cal or default()
    s = schedule_of(series, obs_date, cal=cal)
    oc = s.get("obs_calendar")
    if not oc:
        raise KeyError(f"{s.get('series_id') or s.get('schedule_id')}: obs_calendar not declared")
    skipped = source_skipped(s if "series_id" in s else {"series_id": None, "channel": s.get("channel")}, cal=cal)
    d = obs_date + timedelta(days=1)
    while not business_day(oc, d, cal=cal) or d in skipped:
        d += timedelta(days=1)
    return d


def add_publication_bdays(series, instant: datetime, n: int, *, cal: CalendarSet | None = None) -> datetime:
    """`instant` moved n business days of the series' publication calendar, same local wall time (DST-aware)."""
    cal = cal or default()
    if instant.tzinfo is None:
        raise ValueError("instant must be tz-aware")
    s = schedule_of(series, instant.astimezone(UTC).date(), cal=cal)
    tz = ZoneInfo(s.get("tz") or "UTC")
    local = instant.astimezone(tz)
    d = _step_bdays(s["calendar"], local.date(), n, cal)
    return datetime.combine(d, local.timetz().replace(tzinfo=None), tzinfo=tz).astimezone(UTC)


# --------------------------------------------------------------------------- #
# usable_at (R-01 rule 1, cross-market and cross-time-zone rules; spec L1333-L1336, L1892)
# --------------------------------------------------------------------------- #
def usable_at(series, obs_date: date, market: str, *, cal: CalendarSet | None = None) -> datetime:
    """The first `close_print_bound_utc(market, s)` at which the datum dated `obs_date` may be read.

    A close of another market M: the first session s with `bound(M, D) + buffer < bound(market, s)` (strict);
    a market's own close is usable at its own decision. A publication-timed series: the first session with
    `bound(market, s) >= publication_instant`. A US/NY-dated datum at a KRX decision additionally needs
    `D <= K - 1` (never the US session dated K for the KRX return dated K).
    """
    cal = cal or default()
    s = schedule_of(series, obs_date, cal=cal)
    us_dated = market == "KR" and (s.get("tz") == "America/New_York" or s.get("market") == "US")
    if s["rule"] == "market_close":
        other = s["market"]
        if other == market:
            return clocks.close_print_bound_utc(market, obs_date, cal=cal)
        probe = obs_date
        for _ in range(60):
            if clocks.is_session(market, probe, cal=cal) and not (us_dated and obs_date > probe - timedelta(days=1)):
                bound = clocks.close_print_bound_utc(market, probe, cal=cal)
                if clocks.cross_market_usable(other, obs_date, bound, cal=cal):
                    return bound
            probe += timedelta(days=1)
        raise ValueError(f"no {market} decision within 60 days admits the {other} close of {obs_date}")
    instant = publication_instant(s, obs_date, cal=cal)
    probe = obs_date
    for _ in range(60):
        if clocks.is_session(market, probe, cal=cal) and not (us_dated and obs_date > probe - timedelta(days=1)):
            bound = clocks.close_print_bound_utc(market, probe, cal=cal)
            if bound >= instant:
                return bound
        probe += timedelta(days=1)
    raise ValueError(f"no {market} decision within 60 days after the publication of {obs_date}")


def latest_usable_obs(series, market: str, session_date: date, *, cal: CalendarSet | None = None) -> date:
    """The latest observation date (on the series' obs_calendar) usable at the decision of `market` on `session_date`."""
    cal = cal or default()
    decision = clocks.close_print_bound_utc(market, session_date, cal=cal)
    s = schedule_of(series, session_date, cal=cal)
    oc = s.get("obs_calendar") or "WEEKDAYS"
    probe = session_date
    for _ in range(60):
        if business_day(oc, probe, cal=cal) and usable_at(s, probe, market, cal=cal) <= decision:
            return probe
        probe -= timedelta(days=1)
    raise ValueError(f"no usable observation within 60 days before {session_date}")


def tz_of(market: str) -> str:
    return MARKET_TZ[market]
