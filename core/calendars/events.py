"""`event_calendar` store shape and loader (section 6.3; M1 builds the shape and the read path only; the event
windows, the R-10 logic and the daily artifact are M5, TASK-M5-08/-09).

An event store file is a YAML/JSON list of event objects shaped exactly as the `quantgen/event_calendar.v2.0`
schema's `$defs/event`; `event_calendar()` wraps a list in the envelope and validates it with the registry
validator. A validation failure is refused (ValueError) and never HALTs anything (spec L1178, L1226).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from core.ficc.macro_schema import load_schema, validate

_EVENT = load_schema("event_calendar")["$defs"]["event"]
EVENT_TYPES = tuple(_EVENT["properties"]["type"]["enum"])
EVENT_STATUSES = tuple(_EVENT["properties"]["status"]["enum"])
WINDOW_ACTIONS = tuple(_EVENT["properties"]["windows"]["items"]["properties"]["action"]["enum"])
REQUIRED = tuple(_EVENT["required"])


@dataclass(frozen=True)
class Event:
    event_id: str
    type: str
    region: str
    scheduled_utc: str
    status: str
    source: str
    windows: tuple[dict, ...] = ()
    released_utc: Optional[str] = None
    kr_open_gap_session: Optional[str] = None
    gap_sessions: Optional[int] = None
    var_display_scale: Optional[float] = None
    scenario_tag: Optional[str] = None
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        missing = [k for k in REQUIRED if k not in d]
        if missing:
            raise ValueError(f"event {d.get('event_id')!r} lacks {missing}")
        if d["type"] not in EVENT_TYPES:
            raise ValueError(f"event {d['event_id']!r}: type {d['type']!r} not in {EVENT_TYPES}")
        if d["status"] not in EVENT_STATUSES:
            raise ValueError(f"event {d['event_id']!r}: status {d['status']!r} not in {EVENT_STATUSES}")
        for w in d.get("windows") or ():
            if w.get("action") not in WINDOW_ACTIONS:
                raise ValueError(f"event {d['event_id']!r}: window action {w.get('action')!r} not in {WINDOW_ACTIONS}")
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        known["windows"] = tuple(dict(w) for w in d.get("windows") or ())
        return cls(**known)

    def to_dict(self) -> dict:
        out = asdict(self)
        out["windows"] = [dict(w) for w in self.windows]
        return out


def load_events(path: Path) -> tuple[Event, ...]:
    """Events from a YAML or JSON list file (dates and instants are quoted ISO strings)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    raw = json.loads(text) if path.suffix == ".json" else yaml.safe_load(text)
    if raw is None:
        return ()
    if isinstance(raw, dict):
        raw = raw.get("events", [])
    if not isinstance(raw, list):
        raise ValueError(f"{path.name}: expected a list of events")
    return tuple(Event.from_dict(e) for e in raw)


def _envelope(events, provenance: dict, calendar_version: str) -> dict:
    obj = dict(provenance)
    obj.update({"schema": "quantgen.event_calendar", "schema_version": "2.0", "read_only": True,
                "calendar_version": calendar_version,
                "events": [e.to_dict() if isinstance(e, Event) else dict(e) for e in events]})
    return obj


def event_calendar(events, *, provenance: dict, calendar_version: str) -> dict:
    """The section 6.3 artifact: provenance (from `core.ficc.macro_artifacts.provenance`) + the signed data version
    + the events. Validated; refused with every issue on failure (never a HALT)."""
    obj = _envelope(events, provenance, calendar_version)
    issues = validate("event_calendar", obj)
    if issues:
        raise ValueError("event_calendar refused: " + "; ".join(issues))
    return obj


def release_status(events, event_type: str, scheduled_local_date, tz: str):
    """Thin alias of `core.calendars.publication.release_status` (the R-19 delayed/cancelled read path)."""
    from core.calendars.publication import release_status as _rs
    return _rs(events, event_type, scheduled_local_date, tz)


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


# --------------------------------------------------------------------------- #
# M5 (TASK-M5-08, M5-09; R-10 L1618-1637; section 6.3): entry windows, opening-gap nights, multi-session gaps and
# the `event_calendar` artifact builder. Every window is a no-NEW-ENTRY window on simulated intraday / futures
# entries only; tags and gap flags are annotations and display inputs. **No event tag changes any weight**
# (`events.tags_change_weights: false`); no 24-hour or daily-book blackout is ever generated (section 10 item 12).
# Config = the rules-store `events` block (injected as `cfg`; default shipped). Clocks come from `cal`.
# --------------------------------------------------------------------------- #
from datetime import date, time, timedelta, timezone      # noqa: E402  (M5 block; the M1 head is unchanged above)
from zoneinfo import ZoneInfo                              # noqa: E402

from core.calendars import clocks as _clocks               # noqa: E402

UTC = timezone.utc
ET, KST = "America/New_York", "Asia/Seoul"
BLOCK_INTRADAY, BLOCK_FUTURES, ANNOTATE = WINDOW_ACTIONS
KR_FUT, KR_FUT_NIGHT = "KR_FUT", "KR_FUT_NIGHT"           # the futures "markets" of a window (section 6.3 example)
GAP_EVENT_TYPE = "KRX_HOLIDAY_GAP"
CPI_NFP_TYPES = ("US_CPI", "US_NFP")
GAP_SESSIONS_MIN_FOR_EVENT = 2                             # n_US >= 2 -> KRX_HOLIDAY_GAP (L1631)


def _shipped_events_cfg() -> dict:
    from core.rules.macro_rules import load_store          # lazy: the store loader is scipy-heavy
    return load_store().get("events")


def _cfg(cfg: dict | None) -> dict:
    return cfg if cfg is not None else _shipped_events_cfg()


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hhmm(text: str) -> time:
    h, m = text.split(":")[:2]
    return time(int(h), int(m))


def _local(d: date, hhmm: str, tz: str) -> datetime:
    return datetime.combine(d, _hhmm(hhmm), tzinfo=ZoneInfo(tz)).astimezone(UTC)


def _window(market: str, action: str, start: datetime, end: datetime, resume=None) -> dict:
    """A schema-shaped window (section 6.3 `windows[]` item); nothing else is stored in the artifact."""
    return {"market": market, "action": action, "start_utc": _iso(start), "end_utc": _iso(end), "resume_condition": resume}


def var_display_scale(n_us: int) -> float:
    """sqrt(max(n_US, 1)): >= 1, display only (R-10; `multi_session_gap.var_display_scale`)."""
    n = int(n_us)
    if n < 0:
        raise ValueError("gap_sessions is n_US >= 0")
    return float(max(n, 1)) ** 0.5


def event_windows(event, *, cfg: dict | None = None, vix_pre14: float | None = None,
                  vix_at_resume: float | None = None, missing_vix_resume_late: bool = False) -> tuple[dict, ...]:
    """The no-new-entry windows of one event (R-10 rows). A cancelled event has none (windows expire); a delayed
    event's window moves with its (re-stored) `scheduled_utc`. US CPI / NFP 08:25-10:00 ET; other US releases
    start 30 min before (end as CPI/NFP, F-14); FOMC 13:45-15:00 ET, resume at 15:00 if VIX < its pre-14:00
    level else 15:30 (the stored window ends 15:00 with the resume condition, as the section 6.3 example; with
    both VIX reads given the end is resolved; `missing_vix_resume_late` applies F-17's 15:30 when they are
    missing), the same instants on KOSPI200 night futures; BoK decision 09:45-10:15 KST and press conference
    11:00-11:45 KST on KOSPI200 futures, two events. Tag-only types get no window."""
    e = event if isinstance(event, Event) else Event.from_dict(dict(event))
    if e.status == "cancelled":
        return ()
    c = _cfg(cfg)
    sched = utc(e.scheduled_utc)
    if e.type in CPI_NFP_TYPES or e.type == "US_OTHER_RELEASE":
        lo, hi = c["us_cpi_nfp"]["block_new_intraday_entries_et"]
        pre = (timedelta(minutes=int(c["us_leaky_releases_pre_minutes"])) if e.type == "US_OTHER_RELEASE"
               else _dt_minutes(lo, "08:30"))
        return (_window("US", BLOCK_INTRADAY, sched - pre, sched + _dt_minutes("08:30", hi),
                        f"{c['us_cpi_nfp']['resume_et']} ET"),)
    if e.type == "FOMC":
        lo, hi = c["fomc"]["block_new_intraday_entries_et"]
        start, end = sched - _dt_minutes(lo, "14:00"), sched + _dt_minutes("14:00", hi)
        late = sched + timedelta(minutes=90)                      # 15:30 ET
        if vix_pre14 is not None and vix_at_resume is not None:
            end = end if vix_at_resume < vix_pre14 else late
        elif missing_vix_resume_late:
            end = late
        resume = f"VIX < pre-14:00 ET level else {late.astimezone(UTC):%H:%MZ}"      # the L3845 form
        return (_window("US", BLOCK_INTRADAY, start, end, resume),
                _window(KR_FUT_NIGHT, BLOCK_FUTURES, start, end, None))
    if e.type in ("BOK_DECISION", "BOK_PRESS_CONFERENCE"):
        key = "bok_decision" if e.type == "BOK_DECISION" else "bok_press_conference"
        lo, hi = c[key]["kospi200_futures_block_kst"]
        d = sched.astimezone(ZoneInfo(KST)).date()
        return (_window(KR_FUT, BLOCK_FUTURES, _local(d, lo, KST), _local(d, hi, KST), None),)
    if e.type == GAP_EVENT_TYPE and e.windows:
        return tuple(dict(w) for w in e.windows)
    return ()


def _dt_minutes(a: str, b: str) -> timedelta:
    """b - a as a timedelta of clock minutes (same day)."""
    ta, tb = _hhmm(a), _hhmm(b)
    return timedelta(minutes=(tb.hour * 60 + tb.minute) - (ta.hour * 60 + ta.minute))


def kr_open_window(session_date: date, *, cal=None, cfg: dict | None = None) -> dict:
    """The first `block_first_session_minutes` of every KRX session (09:00-09:30; 10:00-10:30 on 10:00-open
    days: the first trading day of the year and CSAT days), generated from the session calendar (F-16)."""
    c = _cfg(cfg)
    info = _clocks.session("KR", session_date, cal=cal)
    if info.open_utc is None:
        raise ValueError(f"KR {session_date}: no open time in the signed calendar")
    minutes = int(c["kr_open"]["block_first_session_minutes"])
    return dict(_window("KR", BLOCK_INTRADAY, info.open_utc, info.open_utc + timedelta(minutes=minutes), None),
                event_id=f"KR-OPEN-{session_date.isoformat()}")


def cb_reopen_window(reopen_utc: datetime, *, cfg: dict | None = None) -> dict:
    """No new simulated entries for 30 minutes after a circuit-breaker reopening (no gross cut)."""
    c = _cfg(cfg)
    minutes = int(c["sidecar_cb"]["block_new_entries_minutes_after_cb_reopen"])
    return dict(_window("KR", BLOCK_INTRADAY, reopen_utc, reopen_utc + timedelta(minutes=minutes), None),
                event_id=f"KR-CB-REOPEN-{_iso(reopen_utc)}")


def active_windows(events, market: str, at_utc: datetime, *, cal=None, cfg: dict | None = None,
                   cb_reopen_utc: datetime | None = None, include_generated: bool = True) -> tuple[dict, ...]:
    """Every window of `market` containing `at_utc` (start <= at < end): the stored events' windows (generated
    when an event carries none) plus, for KR, the generated open window of that session and a circuit-breaker
    window. Each hit is what the evaluator logs (L1637)."""
    if at_utc.tzinfo is None:
        raise ValueError("at_utc must be tz-aware")
    out = []
    for e in events:
        ev = e if isinstance(e, Event) else Event.from_dict(dict(e))
        wins = ev.windows if ev.windows and ev.status != "cancelled" else event_windows(ev, cfg=cfg)
        for w in wins:
            if w.get("market") == market and utc(w["start_utc"]) <= at_utc < utc(w["end_utc"]):
                out.append(dict(w, event_id=ev.event_id))
    if include_generated and market == "KR" and cal is not None:
        d = at_utc.astimezone(ZoneInfo(KST)).date()
        if _clocks.is_session("KR", d, cal=cal):
            w = kr_open_window(d, cal=cal, cfg=cfg)
            if utc(w["start_utc"]) <= at_utc < utc(w["end_utc"]):
                out.append(w)
    if cb_reopen_utc is not None and market == "KR":
        w = cb_reopen_window(cb_reopen_utc, cfg=cfg)
        if utc(w["start_utc"]) <= at_utc < utc(w["end_utc"]):
            out.append(w)
    return tuple(out)


def kr_open_gap_session_of(event, *, cal=None, cfg: dict | None = None):
    """The KRX session tagged by an opening-gap night (types `kr_open_gap_event_types`), else None."""
    e = event if isinstance(event, Event) else Event.from_dict(dict(event))
    if e.status == "cancelled" or e.type not in _cfg(cfg)["kr_open_gap_event_types"]:
        return None
    return _clocks.kr_open_gap_session(utc(e.scheduled_utc), cal=cal)


def holiday_gap_event(session_date: date, *, cal=None) -> Event | None:
    """`KRX_HOLIDAY_GAP` for a KRX session following n_US >= 2 US sessions since the previous KRX close (F-26:
    scheduled_utc = the session open, region KR, source core/calendars, one annotate_only window over the session)."""
    n = _clocks.gap_sessions("KR", session_date, cal=cal)
    if n < GAP_SESSIONS_MIN_FOR_EVENT:
        return None
    info = _clocks.session("KR", session_date, cal=cal)
    start = info.open_utc or info.close_utc
    return Event(event_id=f"KRX-HOLIDAY-GAP-{session_date.isoformat()}", type=GAP_EVENT_TYPE, region="KR",
                 scheduled_utc=_iso(start), status="scheduled", source="core/calendars",
                 windows=(_window("KR", ANNOTATE, start, info.close_utc, None),),
                 kr_open_gap_session=session_date.isoformat(), gap_sessions=n, var_display_scale=var_display_scale(n),
                 notes=f"multi-session gap: {n} US sessions since the previous KRX close; displayed 1-day VaR x "
                       f"{var_display_scale(n):.4f}; no gross rule")


def kr_open_gap_event(session_date: date, events, *, cal=None, cfg: dict | None = None) -> bool:
    """True iff gap_sessions("KR", d) >= 2, or a non-cancelled opening-gap-night event maps to session d."""
    if _clocks.gap_sessions("KR", session_date, cal=cal) >= GAP_SESSIONS_MIN_FOR_EVENT:
        return True
    return any(kr_open_gap_session_of(e, cal=cal, cfg=cfg) == session_date for e in events)


def gap_tags(session_date: date, events, *, cal=None, cfg: dict | None = None) -> dict:
    """`macro_state.flags` R-10 fields for the EFFECTIVE session: kr_open_gap_event, gap_sessions,
    var_display_scale (display only). The 2026-10-02 KR decision carries {true, 2, 1.4142} for 2026-10-06."""
    n = _clocks.gap_sessions("KR", session_date, cal=cal)
    return {"kr_open_gap_event": kr_open_gap_event(session_date, events, cal=cal, cfg=cfg),
            "gap_sessions": n, "var_display_scale": var_display_scale(n)}


def with_windows(event, *, cal=None, cfg: dict | None = None, **resume_kw) -> Event:
    """The stored event completed with its generated windows and `kr_open_gap_session` tag."""
    e = event if isinstance(event, Event) else Event.from_dict(dict(event))
    wins = e.windows if e.windows and e.status != "cancelled" else event_windows(e, cfg=cfg, **resume_kw)
    gap = e.kr_open_gap_session
    if gap is None and cal is not None:
        d = kr_open_gap_session_of(e, cal=cal, cfg=cfg)
        gap = d.isoformat() if d else None
    return Event(**{**e.to_dict(), "windows": tuple(dict(w) for w in wins), "kr_open_gap_session": gap})


def build_event_calendar(events, *, provenance: dict, calendar_version: str, cal=None, cfg: dict | None = None,
                         gap_sessions_for=(), **resume_kw) -> dict:
    """One `quantgen/event_calendar.v2.0` file per calendar version: every stored event with its windows and
    tags, plus a `KRX_HOLIDAY_GAP` entry for each KRX session in `gap_sessions_for` with n_US >= 2. Returned
    unvalidated: the caller's writer (`macro_artifacts.write_built`) validates it and quarantines an out-of-schema
    calendar with its issues (L3370), never a HALT (L1178)."""
    done = [with_windows(e, cal=cal, cfg=cfg, **resume_kw) for e in events]
    ids = {e.event_id for e in done}
    for d in gap_sessions_for:
        g = holiday_gap_event(d, cal=cal)
        if g is not None and g.event_id not in ids:
            done.append(g)
    return _envelope(done, provenance, calendar_version)
