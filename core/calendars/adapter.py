"""The clocks adapter: the five calendar methods the data layer consumes (M1 integration; R-19 rule 2, R-20).

`core.ficc.pit`, `core.ficc.contracts` and `core.ficc.lag_audit` take a `clocks` object with
`close_print_bound_utc(market, session_date)`, `publication_instant(series_id, obs_date)`,
`next_expected_obs(series_id, obs_date)`, `add_publication_bdays(series_id, instant, n)` and `is_session(market, d)`
(tests use `StubClocks`). `CalendarClocks` is that object over the owner-signed files of `core.calendars.store` and
the series registry: the registry names each series' schedule id, obs calendar and channel; the signed
`publication_schedules` file governs the rule, time and tz of that schedule (effective-dated rows). A schedule with
no scheduled instant (LIVE_QUOTE, AS_POSTED, DERIVED) answers None. Unsigned or uncovered calendars raise
`CalendarUnsigned` / `CalendarCoverageError`; `core.ficc.contracts` turns either into `CalendarUnavailable`
(every acting input fails closed, brief F-5).
"""
from __future__ import annotations

from datetime import date, datetime

from core.calendars import clocks as _clocks
from core.calendars import publication as _pub
from core.calendars.store import CalendarSet

# registry `schedules` id -> signed publication_schedules `schedule_id` (None: no scheduled instant)
SCHEDULE_IDS = {
    "KRX_CLOSE": "MARKET_CLOSE_KR", "NYSE_CLOSE": "MARKET_CLOSE_US", "JP_CLOSE": "MARKET_CLOSE_JP",
    "CN_CLOSE": "MARKET_CLOSE_CN", "HK_CLOSE": "MARKET_CLOSE_HK", "TW_CLOSE": "MARKET_CLOSE_TW",
    "FRED_H15": "H15", "H10": "H10", "TREASURY_PAR": "TREASURY_PAR", "VIXCLS": "VIXCLS_CBOE",
    "BLS": "BLS", "BEA": "BEA", "ECOS_1530": "ECOS_USDKRW", "KODEX_PDF": "KODEX200_PDF",
    "LIVE_QUOTE": None, "AS_POSTED": None, "DERIVED": None,
}
_SERIES_KEYS = ("channel", "obs_calendar", "release_event_type", "grace_publication_bdays", "market", "frequency")


def registry_schedule(registry, series_id: str) -> dict | None:
    """The `core.calendars.publication` schedule dict of a registered series (None = no scheduled instant). The
    rule/time/tz come from the signed publication_schedules row named by `schedule_id`; the registry adds the
    series' own keys (obs_calendar, channel, release_event_type, grace, market, frequency)."""
    s = registry.series[series_id]
    try:
        sid = SCHEDULE_IDS[s["schedule"]]
    except KeyError:
        raise KeyError(f"{series_id}: registry schedule {s['schedule']!r} has no publication_schedules id") from None
    if sid is None:
        return None
    out = {"schedule_id": sid, "series_id": series_id}
    out.update({k: s[k] for k in _SERIES_KEYS if s.get(k) is not None})
    return out


class CalendarClocks:
    """`clocks` for the data layer over a `CalendarSet` (default: the shipped set) and a registry (default: the
    shipped registry). `events` (an iterable of release events) moves or removes publication instants."""

    def __init__(self, registry=None, *, cal: CalendarSet | None = None, events=()) -> None:
        self._registry, self.cal, self.events = registry, cal, tuple(events)

    @property
    def registry(self):
        if self._registry is None:
            from core.ficc import contracts
            self._registry = contracts.default_registry()
        return self._registry

    def schedule(self, series_id: str) -> dict | None:
        return registry_schedule(self.registry, series_id)

    # -- the five methods -------------------------------------------------------
    def is_session(self, market: str, d: date) -> bool:
        return _clocks.is_session(market, d, cal=self.cal)

    def close_print_bound_utc(self, market: str, session_date: date) -> datetime:
        return _clocks.close_print_bound_utc(market, session_date, cal=self.cal)

    def publication_instant(self, series_id: str, obs_date: date) -> datetime | None:
        s = self.schedule(series_id)
        return None if s is None else _pub.publication_instant(s, obs_date, cal=self.cal, events=self.events)

    def next_expected_obs(self, series_id: str, obs_date: date) -> date | None:
        s = self.schedule(series_id)
        if s is None:
            return None
        if s.get("frequency") == "monthly":          # keyed on the first day of the reference month (L1341)
            from core.ficc.pit import add_months
            return add_months(obs_date, 1)
        return _pub.next_expected_obs(s, obs_date, cal=self.cal)

    def add_publication_bdays(self, series_id: str, instant: datetime, n: int) -> datetime:
        s = self.schedule(series_id)
        if s is None or instant is None:
            return instant
        resolved = _pub.schedule_of(s, instant.date(), cal=self.cal)
        if resolved["rule"] == "market_close":      # a close's publication days are its market's sessions
            market, d = resolved["market"], instant.date()
            for _ in range(int(n)):
                d = _clocks.next_session(market, d, cal=self.cal)
            return _clocks.close_print_bound_utc(market, d, cal=self.cal)
        return _pub.add_publication_bdays(resolved, instant, int(n), cal=self.cal)

    # -- pass-throughs the rulings list under core/calendars/clocks ---------------
    def decision_time_utc(self, market: str, session_date: date) -> datetime:
        return _clocks.decision_time_utc(market, session_date, cal=self.cal)

    def usable_at(self, series_id: str, obs_date: date, market: str) -> datetime | None:
        """The first decision of `market` that may read the datum dated `obs_date` (None: live quote / as posted)."""
        s = self.schedule(series_id)
        return None if s is None else _pub.usable_at(s, obs_date, market, cal=self.cal)


__all__ = ["CalendarClocks", "SCHEDULE_IDS", "registry_schedule"]
