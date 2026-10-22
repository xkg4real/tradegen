"""M1 package B - effective-dated calendars, clocks, publication schedules, regime tags, signed-file store
(T-CLOSE-01, T-CLOSE-02, T-TZ-01, T-TZ-02, T-PRINT-01, T-CAL-01, T-CAL-02, T-REGIME-01, T-SAT-01, T-XMKT-01 and the
calendar halves of T-H15-01, T-H10-02, T-VIX-01, T-AVAIL-01, I-06b).

Hermetic: every calendar file is a synthetic fixture written into a tempfile directory and signed there by the
test itself (signer "TEST-FIXTURE (not an owner sign-off)"); the library never writes a signature. The shipped
drafts under core/calendars/data/ are read only to assert that they are refused. No module global is patched.
"""
from __future__ import annotations

import tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from core.calendars import clocks, events, publication, regime, store
from core.calendars.store import CalendarCoverageError, CalendarSet, CalendarUnsigned, NotASession, content_md5
from tests.notrun import NotRun, require_fixture

SIGNER = "TEST-FIXTURE (not an owner sign-off)"
SIGNED_UTC = "2026-10-06T00:00:00Z"
NY, KST = "America/New_York", "Asia/Seoul"
UTC = timezone.utc
_CACHE: dict[str, tuple[tempfile.TemporaryDirectory, CalendarSet]] = {}


def U(y, m, d, hh=0, mm=0, ss=0) -> datetime:
    return datetime(y, m, d, hh, mm, ss, tzinfo=UTC)


# --------------------------------------------------------------------------- #
# Fixture calendars (synthetic; signed in the temp dir by the test)
# --------------------------------------------------------------------------- #
def _row(**kw) -> dict:
    base = {"effective_from": None, "effective_to": None, "source_url": "fixture", "retrieved_at_utc": SIGNED_UTC,
            "signed_off_by": SIGNER}
    base.update(kw)
    return base


def _hol(d: date, kind="closed", close_local=None, name="fixture") -> dict:
    r = _row(date=d.isoformat(), kind=kind, name=name, effective_from=d.isoformat(), effective_to=d.isoformat())
    if close_local:
        r["close_local"] = close_local
    return r


def _nth(year, month, weekday, n):
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d + timedelta(days=7 * (n - 1))


def _last(year, month, weekday):
    d = date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e, f = b // 4, b % 4, (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return date(year, (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1)


def _observed(d, sat_to_fri=True):
    if d.weekday() == 5 and sat_to_fri:
        return d - timedelta(days=1)
    return d + timedelta(days=1) if d.weekday() == 6 else d


def _federal(year) -> set[date]:
    out = {_observed(date(year, 1, 1)), _nth(year, 1, 0, 3), _nth(year, 2, 0, 3), _last(year, 5, 0),
           _observed(date(year, 7, 4)), _nth(year, 9, 0, 1), _nth(year, 10, 0, 2), _observed(date(year, 11, 11)),
           _nth(year, 11, 3, 4), _observed(date(year, 12, 25))}
    if year >= 2021:
        out.add(_observed(date(year, 6, 19)))
    return out


def _nyse(year) -> tuple[set[date], dict[date, str]]:
    ny = date(year, 1, 1)
    closed = {_nth(year, 1, 0, 3), _nth(year, 2, 0, 3), _easter(year) - timedelta(days=2), _last(year, 5, 0),
              _observed(date(year, 7, 4)), _nth(year, 9, 0, 1), _nth(year, 11, 3, 4), _observed(date(year, 12, 25))}
    if ny.weekday() < 5:
        closed.add(ny)
    elif ny.weekday() == 6:
        closed.add(ny + timedelta(days=1))
    if year >= 2022:
        closed.add(_observed(date(year, 6, 19)))
    early = {_nth(year, 11, 3, 4) + timedelta(days=1): "13:00"}
    if date(year, 7, 3).weekday() < 4 and date(year, 7, 4).weekday() < 5:
        early[date(year, 7, 3)] = "13:00"
    if date(year, 12, 24).weekday() < 4:
        early[date(year, 12, 24)] = "13:00"
    return closed, early


# KRX fixture: fixed-date holidays every year (closed on Saturdays too), Dec 31, plus the real 2015/16/25/26/27 lists.
_KRX_EXTRA = {
    2015: ["02-18", "02-19", "02-20", "05-01", "05-25", "08-14", "09-28", "09-29", "10-09"],
    2016: ["02-08", "02-09", "02-10", "04-13", "05-06", "09-14", "09-15", "09-16"],
    2025: ["01-27", "01-28", "01-29", "01-30", "03-03", "05-01", "05-06", "06-03", "10-06", "10-07", "10-08", "10-09"],
    2026: ["02-16", "02-17", "02-18", "03-02", "05-01", "05-25", "08-17", "09-24", "09-25", "10-05", "10-09"],
    2027: ["02-08", "02-09", "05-13", "08-16", "09-14", "09-15", "09-16", "10-04", "10-11", "12-27"],
}


def _krx_closed() -> set[date]:
    out = set()
    for y in range(1995, 2028):
        for md in ((1, 1), (3, 1), (5, 5), (6, 6), (8, 15), (10, 3), (12, 25), (12, 31)):
            out.add(date(y, *md))
        for md in _KRX_EXTRA.get(y, ()):
            out.add(date.fromisoformat(f"{y}-{md}"))
    return out


def _doc(file_id, covers, calendar, rows, version="1.0.0-fixture") -> dict:
    return {"file_id": file_id, "version": version, "covers": {"from": covers[0], "to": covers[1]},
            "coverage_calendar": calendar, "signed_off_by": SIGNER, "signed_utc": SIGNED_UTC, "md5": None, "rows": rows}


def _sign(doc: dict) -> dict:
    doc["md5"] = content_md5(doc)
    return doc


def _write_set(root: Path, docs: dict[str, dict], *, manifest_version="1.0.0-fixture", unsigned_manifest=False) -> None:
    rows = []
    for name, doc in docs.items():
        _sign(doc)
        (root / f"{name}.yaml").write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        rows.append({"file": f"{name}.yaml", "version": doc["version"], "md5": doc["md5"],
                     "signed_off_by": None if unsigned_manifest else doc["signed_off_by"], "test_ids": ["T-CAL-01"]})
    manifest = {"version": manifest_version, "signed_off_by": SIGNER, "signed_utc": SIGNED_UTC, "rows": rows}
    (root / "MANIFEST.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


def fixture_docs() -> dict[str, dict]:
    docs = {}
    span = ("1995-01-01", "2027-12-31")
    docs["holidays_KRX"] = _doc("holidays_KRX", span, "KRX", [_hol(d) for d in sorted(_krx_closed())])
    docs["holidays_ECOS"] = _doc("holidays_ECOS", span, "ECOS", [_hol(d) for d in sorted(_krx_closed()) if d.weekday() < 5])
    closed, early = set(), {}
    for y in range(2006, 2028):
        c, e = _nyse(y)
        closed |= c
        early.update(e)
    closed.add(date(2025, 1, 9))
    nyse_rows = [_hol(d) for d in sorted(closed)] + [_hol(d, "early_close", t) for d, t in sorted(early.items())]
    docs["holidays_NYSE"] = _doc("holidays_NYSE", ("2006-01-01", "2027-12-31"), "NYSE", nyse_rows)
    docs["holidays_CBOE"] = _doc("holidays_CBOE", ("2006-01-01", "2027-12-31"), "CBOE", [_hol(d) for d in sorted(closed)])
    fed = set()
    for y in range(2015, 2028):
        fed |= _federal(y)
    docs["holidays_FED"] = _doc("holidays_FED", ("2015-01-01", "2027-12-31"), "FED", [_hol(d) for d in sorted(fed)])
    sifma = {d for d in fed} | {_easter(y) - timedelta(days=2) for y in range(2015, 2028)}
    sifma_rows = [_hol(d) for d in sorted(sifma)] + [_hol(_nth(y, 11, 3, 4) + timedelta(days=1), "early_close", "14:00")
                                                     for y in range(2015, 2028)]
    docs["holidays_SIFMA"] = _doc("holidays_SIFMA", ("2015-01-01", "2027-12-31"), "SIFMA", sifma_rows)
    docs["holidays_CME"] = _doc("holidays_CME", ("2015-01-01", "2027-12-31"), "CME", [_hol(d) for d in sorted(fed)])
    asia = ("2015-01-01", "2027-12-31")
    jpx = [_hol(date(y, m, d)) for y in range(2015, 2028) for m, d in ((1, 1), (1, 2), (1, 3), (2, 11), (4, 29), (5, 3), (5, 4), (5, 5),
                                                                       (8, 11), (11, 3), (11, 23), (12, 31))]
    docs["holidays_JPX"] = _doc("holidays_JPX", asia, "JPX", jpx)
    sse = [_hol(date(y, m, d)) for y in range(2015, 2028) for m, d in ((1, 1), (5, 1), (5, 2), (10, 1), (10, 2), (10, 3), (10, 6), (10, 7))]
    docs["holidays_SSE"] = _doc("holidays_SSE", asia, "SSE", sse)
    hk = [_hol(date(y, m, d)) for y in range(2015, 2028) for m, d in ((1, 1), (7, 1), (10, 1), (12, 25), (12, 26))]
    docs["holidays_HKEX"] = _doc("holidays_HKEX", asia, "HKEX", hk)
    tw = [_hol(date(y, m, d)) for y in range(2015, 2028) for m, d in ((1, 1), (2, 28), (4, 4), (4, 5), (10, 10))]
    docs["holidays_TWSE"] = _doc("holidays_TWSE", asia, "TWSE", tw)
    docs["market_closes"] = _doc("market_closes", asia, "WEEKDAYS", [
        _row(kind="close", market="CN", open_local="09:30", close_local="15:00", tz="Asia/Shanghai"),
        _row(kind="close", market="HK", open_local="09:30", close_local="16:00", tz="Asia/Hong_Kong"),
        _row(kind="close", market="TW", open_local="09:00", close_local="13:30", tz="Asia/Taipei")])
    docs["kr_sessions"] = _doc("kr_sessions", span, "KRX", [
        _row(kind="regular_open", open_kst="09:00"),
        _row(kind="lunch_break", window_kst=["12:00", "13:00"], effective_to="2000-05-21"),
        _row(kind="csat_day", date="2015-11-12", effective_from="2015-11-12", effective_to="2015-11-12"),
        _row(kind="csat_day", date="2025-11-13", effective_from="2025-11-13", effective_to="2025-11-13"),
        _row(kind="saturday_close", close_kst="11:30", effective_to="1998-12-11"),
        _row(kind="random_end_extension", session_date="2014-06-02", extension_s=45)])
    docs["publication_schedules"] = _doc("publication_schedules", span, "WEEKDAYS", [
        _row(schedule_id="H15", rule="next_bday_after_obs", calendar="FED", time="16:15", tz=NY),
        _row(schedule_id="H10", rule="monday_after_week", calendar="FED", time="16:15", tz=NY),
        _row(schedule_id="TREASURY_PAR", rule="same_day", calendar="SIFMA", time="18:00", tz=NY),
        _row(schedule_id="BLS", rule="release_calendar", calendar="FED", time="08:30", tz=NY),
        _row(schedule_id="VIXCLS_CBOE", rule="same_day", calendar="CBOE", time="16:15", tz=NY),
        _row(schedule_id="VIXCLS_FRED", rule="channel_posting_time", calendar="NYSE", time="16:15", tz=NY,
             declared_lag_bdays=1, declared_time="09:00"),
        _row(schedule_id="ECOS_USDKRW", rule="same_day", calendar="ECOS", time="15:00", tz=KST, effective_to="2016-07-31"),
        _row(schedule_id="ECOS_USDKRW", rule="same_day", calendar="ECOS", time="15:30", tz=KST, effective_from="2016-08-01"),
        _row(schedule_id="KODEX200_PDF", rule="next_bday_after_obs", calendar="KRX", time="08:00", tz=KST),
    ] + [_row(schedule_id=f"MARKET_CLOSE_{m}", rule="market_close", market=m) for m in clocks.M1_MARKETS])
    docs["source_skipped"] = _doc("source_skipped", span, "WEEKDAYS", [
        _row(series="DEXKOUS", date=d, effective_from=d, effective_to=d, reason="H.10 not published")
        for d in ("2017-01-20", "2018-12-05", "2020-11-27", "2020-12-24")
    ] + [_row(series="DTWEXBGS", date=d, effective_from=d, effective_to=d, reason="DC storm") for d in ("2016-01-22", "2018-03-02")])
    docs["kr_regime_tags"] = _doc("kr_regime_tags", span, "KRX", _regime_rows())
    return docs


def _regime_rows() -> list[dict]:
    spans = {
        "price_limit": [("1995-01-01", "1995-03-31", 0.046), ("1995-04-01", "1996-11-24", 0.06), ("1996-11-25", "1998-03-01", 0.08),
                        ("1998-03-02", "1998-12-06", 0.12), ("1998-12-07", "2015-06-14", 0.15), ("2015-06-15", None, 0.30)],
        "saturday_session": [("1995-01-01", "1998-12-11", True), ("1998-12-12", None, False)],
        "close_time_kst": [("1995-01-01", "2016-07-31", "15:00"), ("2016-08-01", None, "15:30")],
        "closing_call": [("1995-01-01", "2016-07-31", "14:50-15:00"), ("2016-08-01", None, "15:20-15:30")],
        "random_end": [("1995-01-01", "2015-06-14", "conditional"), ("2015-06-15", None, "unconditional_le_30s")],
        "lunch_break": [("1995-01-01", "2000-05-21", "12:00-13:00"), ("2000-05-22", None, "none")],
        "fx_regime": [("1995-01-01", "1997-09-21", "market_average_rate"), ("1997-09-22", "1997-10-17", "peg_1997"),
                      ("1997-10-18", None, "free_float")],
        "etf_available": [("1995-01-01", "2002-10-13", False), ("2002-10-14", None, True)],
        "short_sale_ban": [("1995-01-01", "2008-09-30", False), ("2008-10-01", "2009-05-31", True), ("2009-06-01", "2011-08-10", False),
                           ("2011-08-11", "2011-11-09", True), ("2011-11-10", "2020-03-15", False), ("2020-03-16", "2021-05-02", True),
                           ("2021-05-03", "2023-11-05", False), ("2023-11-06", "2025-03-30", True), ("2025-03-31", None, False)],
        "short_sale_regime": [("1995-01-01", "2020-03-15", "none"), ("2020-03-16", "2021-05-02", "full_ban"),
                              ("2021-05-03", "2023-11-05", "partial_ban_non_index"), ("2023-11-06", "2025-03-30", "full_ban"),
                              ("2025-03-31", None, "none")],
        "sell_tax_pct": [("1995-01-01", "2019-05-29", 0.30), ("2019-05-30", "2020-12-31", 0.25), ("2021-01-01", "2022-12-31", 0.23),
                         ("2023-01-01", "2023-12-31", 0.20), ("2024-01-01", "2024-12-31", 0.18), ("2025-01-01", "2025-12-31", 0.15),
                         ("2026-01-01", None, 0.20)],
        "tick_regime": [("1995-01-01", "2023-01-24", "pre_2023"), ("2023-01-25", "2023-12-10", "stocks_2023_01_25"),
                        ("2023-12-11", None, "etf_w1_2023_12_11")],
        "letf_rules": [("1995-01-01", "2026-05-26", "none"), ("2026-05-27", "2026-07-15", "rule_2026_05_27"), ("2026-07-16", None, "rule_2026_07_16")],
        "usdkrw_onshore_hours": [("1995-01-01", "2016-07-31", "close_15:00"), ("2016-08-01", "2024-06-30", "close_15:30"),
                                 ("2024-07-01", "2026-07-05", "close_02:00_next_day"), ("2026-07-06", None, "24h")],
        "value_up": [("1995-01-01", "2024-02-25", "pre"), ("2024-02-26", None, "post_2024_02_26")],
    }
    assert set(spans) == set(regime.TAGS)
    return [_row(tag=t, value=v, effective_from=lo, effective_to=hi) for t, s in spans.items() for lo, hi, v in s]


def fixture_set(key: str = "main", docs: dict | None = None) -> CalendarSet:
    """A signed temp-dir calendar set (cached per key for the process; the temp dir lives with the cache)."""
    if key not in _CACHE:
        tmp = tempfile.TemporaryDirectory(prefix="quantgen_cal_")
        _write_set(Path(tmp.name), docs if docs is not None else fixture_docs())
        _CACHE[key] = (tmp, CalendarSet(Path(tmp.name)))
    return _CACHE[key][1]


def _raises(fn, exc) -> Exception:
    try:
        fn()
    except exc as e:
        return e
    raise AssertionError(f"expected {exc.__name__}")


# --------------------------------------------------------------------------- #
# T-CLOSE-01 / T-CLOSE-02 / T-PRINT-01
# --------------------------------------------------------------------------- #
def test_close01_decision_time_and_bound():
    """KR 2026-10-02: 06:30Z / 06:30:30Z; a print at 06:30:20Z accepted, one at 06:31Z rejected; US 2026-10-01 20:00Z /
    20:00:30Z (EDT); US 2026-01-15 21:00Z (EST); the legacy v1.2 API still answers."""
    cal = fixture_set()
    d = date(2026, 10, 2)
    assert clocks.decision_time_utc("KR", d, cal=cal) == U(2026, 10, 2, 6, 30)
    assert clocks.close_print_bound_utc("KR", d, cal=cal) == U(2026, 10, 2, 6, 30, 30)
    ok = clocks.close_stamp("KR", d, U(2026, 10, 2, 6, 30, 20), cal=cal)
    assert ok.available_at_utc == U(2026, 10, 2, 6, 30, 20) and ok.available_at_source == "exchange_print"
    assert ok.obs_utc == U(2026, 10, 2, 6, 30)
    _raises(lambda: clocks.close_stamp("KR", d, U(2026, 10, 2, 6, 31), cal=cal), clocks.CloseAfterBound)
    bound = clocks.close_stamp("KR", d, None, cal=cal)
    assert bound.available_at_utc == U(2026, 10, 2, 6, 30, 30) and bound.available_at_source == "calendar_bound"
    assert clocks.decision_time_utc("US", date(2026, 10, 1), cal=cal) == U(2026, 10, 1, 20, 0)
    assert clocks.close_print_bound_utc("US", date(2026, 10, 1), cal=cal) == U(2026, 10, 1, 20, 0, 30)
    assert clocks.close_stamp("US", date(2026, 10, 1), U(2026, 10, 1, 20, 0, 2), cal=cal).available_at_source == "exchange_print"
    assert clocks.decision_time_utc("US", date(2026, 1, 15), cal=cal) == U(2026, 1, 15, 21, 0)
    # quarantine anchor used by the data layer: bound + 10 min
    assert clocks.close_print_bound_utc("KR", d, cal=cal) + timedelta(minutes=10) == U(2026, 10, 2, 6, 40, 30)
    # the legacy API is unchanged by the package conversion (spec L1991 "API unchanged from v1.2")
    from core import calendars as legacy
    assert legacy.is_trading_day("US", date(2026, 11, 26)) is False and legacy.get("KRX").source["library"] == "exchange_calendars"
    covers = legacy.coverage("US")
    assert legacy.is_trading_day("US", date(covers[1].year + 5, 6, 15)) is None
    assert legacy.decision_time_utc is clocks.decision_time_utc        # lazy re-export


test_close01_decision_time_and_bound.test_ids = ["T-CLOSE-01"]


def test_close02_effective_dated_clocks():
    cal = fixture_set()
    D = clocks.decision_time_utc
    B = clocks.close_print_bound_utc
    assert D("KR", date(2016, 7, 29), cal=cal) == U(2016, 7, 29, 6, 0)
    assert D("KR", date(2016, 8, 1), cal=cal) == U(2016, 8, 1, 6, 30)
    assert B("KR", date(2016, 7, 29), cal=cal) == U(2016, 7, 29, 6, 0, 30)
    assert B("KR", date(2016, 8, 1), cal=cal) == U(2016, 8, 1, 6, 30, 30)
    assert B("KR", date(2015, 6, 15), cal=cal) == U(2015, 6, 15, 6, 0, 30)      # first unconditional day
    assert B("KR", date(2015, 6, 12), cal=cal) == U(2015, 6, 12, 6, 0, 30)      # conditional era: + 30 s tolerance, no extension row
    assert B("KR", date(2014, 6, 2), cal=cal) == U(2014, 6, 2, 6, 1, 15)        # + 30 s + the signed 45 s extension
    assert D("KR", date(2025, 11, 13), cal=cal) == U(2025, 11, 13, 7, 30) and B("KR", date(2025, 11, 13), cal=cal) == U(2025, 11, 13, 7, 30, 30)
    # pre-2016 CSAT and a pre-1998-12-12 Saturday: assert against the fixture file, not a hard-coded hour
    kr = cal.file("kr_sessions")
    csat_cfg = store.effective_config(cal.market_config("KR")["csat_session_kst"], date(2015, 11, 12), "csat")["window"][1]
    hh, mm = map(int, csat_cfg.split(":"))
    want = datetime.combine(date(2015, 11, 12), time(hh, mm), tzinfo=ZoneInfo(KST)).astimezone(UTC)
    assert D("KR", date(2015, 11, 12), cal=cal) == want and B("KR", date(2015, 11, 12), cal=cal) == want + timedelta(seconds=30)
    sat = date(1997, 6, 7)
    assert sat.weekday() == 5 and clocks.is_session("KR", sat, cal=cal)
    sat_close = next(r["close_kst"] for r in kr.rows if r["kind"] == "saturday_close")
    hh, mm = map(int, sat_close.split(":"))
    want = datetime.combine(sat, time(hh, mm), tzinfo=ZoneInfo(KST)).astimezone(UTC)
    assert D("KR", sat, cal=cal) == want and B("KR", sat, cal=cal) == want + timedelta(seconds=30)
    assert "saturday" in clocks.session("KR", sat, cal=cal).flags
    _raises(lambda: D("KR", date(2026, 10, 5), cal=cal), NotASession)
    _raises(lambda: D("KR", date(2026, 10, 4), cal=cal), NotASession)                   # Sunday
    assert D("US", date(2026, 11, 27), cal=cal) == U(2026, 11, 27, 18, 0)
    assert D("US", date(2025, 7, 3), cal=cal) == U(2025, 7, 3, 17, 0)
    assert B("US", date(2026, 10, 1), cal=cal) == U(2026, 10, 1, 20, 0, 30)
    _raises(lambda: D("US", date(2026, 11, 26), cal=cal), NotASession)
    assert clocks.regime_tags if False else regime.regime_tags("KR", date(1997, 6, 7), cal=cal)["saturday_session"] is True
    # a Saturday without a signed close never falls back to the weekday close
    docs = fixture_docs()
    docs["kr_sessions"]["rows"] = [r for r in docs["kr_sessions"]["rows"] if r["kind"] != "saturday_close"]
    bare = fixture_set("no_saturday_close", docs)
    assert clocks.is_session("KR", sat, cal=bare)
    _raises(lambda: D("KR", sat, cal=bare), CalendarUnsigned)
    # session() content
    s = clocks.session("KR", date(2026, 10, 2), cal=cal)
    assert s.open_local == time(9, 0) and s.close_local == time(15, 30) and s.closing_call_local == (time(15, 20), time(15, 30))
    assert s.lunch_break_local is None and s.random_end["kind"] == "unconditional" and s.open_utc == U(2026, 10, 2, 0, 0)
    first = clocks.session("KR", date(2026, 1, 2), cal=cal)
    assert "first_trading_day" in first.flags and first.open_local == time(10, 0)
    old = clocks.session("KR", date(1999, 3, 2), cal=cal)
    assert old.lunch_break_local == (time(12, 0), time(13, 0)) and old.closing_call_local == (time(14, 50), time(15, 0))
    csat = clocks.session("KR", date(2025, 11, 13), cal=cal)
    assert "csat" in csat.flags and csat.open_local == time(10, 0) and csat.closing_call_local == (time(16, 20), time(16, 30))
    assert clocks.session("US", date(2026, 11, 27), cal=cal).flags == frozenset({"early_close"})
    # other markets' scheduled closes (today's hours)
    assert D("JP", date(2024, 11, 4), cal=cal) == U(2024, 11, 4, 6, 0) and D("JP", date(2024, 11, 5), cal=cal) == U(2024, 11, 5, 6, 30)
    assert D("CN", date(2026, 10, 8), cal=cal) == U(2026, 10, 8, 7, 0) and D("HK", date(2026, 10, 8), cal=cal) == U(2026, 10, 8, 8, 0)
    assert D("TW", date(2026, 10, 8), cal=cal) == U(2026, 10, 8, 5, 30)
    assert B("JP", date(2026, 10, 8), cal=cal) == D("JP", date(2026, 10, 8), cal=cal)       # close_print_bound_s 0
    _raises(lambda: D("KR", date(1990, 1, 2), cal=cal), CalendarCoverageError)
    assert D("CRYPTO", date(2026, 10, 2), cal=cal) == U(2026, 10, 3, 0, 0)     # M10 R-17 branch (T-CRYPTO-01, tests/macro_m9_lab.py)
    _raises(lambda: D("EU", date(2026, 10, 2), cal=cal), KeyError)


test_close02_effective_dated_clocks.test_ids = ["T-CLOSE-02"]


def test_close02_on_the_real_signed_files_is_owner_input():
    """The same assertions on the shipped files need the owner's signature; the drafts are unsigned."""
    refused = store.describe()
    assert refused and all(r["status"] == "REFUSED" for r in refused)
    raise NotRun("OWNER: core/calendars/data/*.yaml are unsigned drafts; T-CLOSE-02 on the real KRX/NYSE files waits for "
                 "the owner's sign-off (Saturday closes, pre-2016 CSAT window, CSAT dates, random-end extensions)")


test_close02_on_the_real_signed_files_is_owner_input.test_ids = ["T-CLOSE-02"]


def test_print01_intraday_print_is_never_a_close():
    """2026-03-09: a 10:31 KST print (01:31Z) precedes the scheduled close and is refused as a close; the official close
    is stamped obs_utc 06:30Z with available_at <= 06:30:30Z."""
    cal = fixture_set()
    d = date(2026, 3, 9)
    _raises(lambda: clocks.close_stamp("KR", d, U(2026, 3, 9, 1, 31), cal=cal), clocks.IntradayPrint)
    stamp = clocks.close_stamp("KR", d, U(2026, 3, 9, 6, 30, 12), cal=cal)
    assert stamp.obs_utc == U(2026, 3, 9, 6, 30) and stamp.available_at_utc <= U(2026, 3, 9, 6, 30, 30)
    _raises(lambda: clocks.close_stamp("KR", d, datetime(2026, 3, 9, 6, 30), cal=cal), ValueError)   # naive instant


test_print01_intraday_print_is_never_a_close.test_ids = ["T-PRINT-01"]


def test_print01_real_kospi_close_2026_03_09():
    require_fixture("krx_kospi_official_close_1997-01-03_2026-10-02.csv")
    raise AssertionError("unreachable: the fixture is not listed")


test_print01_real_kospi_close_2026_03_09.test_ids = ["T-PRINT-01"]


# --------------------------------------------------------------------------- #
# T-TZ-01 / T-TZ-02
# --------------------------------------------------------------------------- #
def test_tz01_cross_time_zone():
    cal = fixture_set()
    assert clocks.latest_usable_close("US", "KR", date(2026, 10, 1), cal=cal) == date(2026, 9, 30)
    assert clocks.latest_usable_close("US", "KR", date(2026, 9, 30), cal=cal) == date(2026, 9, 29)
    kst = ZoneInfo(KST)
    assert clocks.decision_time_utc("US", date(2026, 1, 15), cal=cal).astimezone(kst) == datetime(2026, 1, 16, 6, 0, tzinfo=kst)
    assert clocks.decision_time_utc("US", date(2026, 7, 15), cal=cal).astimezone(kst) == datetime(2026, 7, 16, 5, 0, tzinfo=kst)
    assert clocks.decision_time_utc("US", date(2006, 3, 20), cal=cal) == U(2006, 3, 20, 21, 0)
    assert clocks.decision_time_utc("US", date(2006, 4, 3), cal=cal) == U(2006, 4, 3, 20, 0)
    bound = clocks.close_print_bound_utc("KR", date(2026, 10, 8), cal=cal)
    assert not clocks.cross_market_usable("CN", date(2026, 10, 8), bound, cal=cal)
    assert not clocks.cross_market_usable("HK", date(2026, 10, 8), bound, cal=cal)
    assert not clocks.cross_market_usable("JP", date(2026, 10, 8), bound, cal=cal)
    assert clocks.cross_market_usable("TW", date(2026, 10, 8), bound, cal=cal)
    assert clocks.cross_market_usable("JP", date(2020, 6, 1), clocks.close_print_bound_utc("KR", date(2020, 6, 1), cal=cal), cal=cal)
    # the US session dated K never enters the KRX decision of K (usable_at of a US close at a KR decision)
    us_close = {"schedule_id": "MARKET_CLOSE_US"}
    assert publication.usable_at(us_close, date(2026, 10, 1), "KR", cal=cal) == clocks.close_print_bound_utc("KR", date(2026, 10, 2), cal=cal)
    assert publication.usable_at(us_close, date(2026, 10, 2), "KR", cal=cal) == clocks.close_print_bound_utc("KR", date(2026, 10, 6), cal=cal)
    assert publication.usable_at(us_close, date(2026, 10, 2), "US", cal=cal) == U(2026, 10, 2, 20, 0, 30)


test_tz01_cross_time_zone.test_ids = ["T-TZ-01"]


def test_tz02_event_to_kr_open_gap_session():
    cal = fixture_set()
    fomc = datetime(2026, 9, 16, 14, 0, tzinfo=ZoneInfo(NY))
    assert fomc.astimezone(UTC) == U(2026, 9, 16, 18, 0)
    assert fomc.astimezone(ZoneInfo(KST)) == datetime(2026, 9, 17, 3, 0, tzinfo=ZoneInfo(KST))
    assert clocks.kr_open_gap_session(fomc, cal=cal) == date(2026, 9, 17)
    nfp = datetime(2026, 10, 2, 8, 30, tzinfo=ZoneInfo(NY))
    assert nfp.astimezone(UTC) == U(2026, 10, 2, 12, 30)
    assert clocks.kr_open_gap_session(nfp, cal=cal) == date(2026, 10, 6)
    assert clocks.kr_open_gap_session(datetime(2026, 10, 28, 14, 0, tzinfo=ZoneInfo(NY)), cal=cal) == date(2026, 10, 29)
    # effective_session (t+1) and the next/prev helpers
    assert clocks.next_session("KR", date(2026, 10, 2), cal=cal) == date(2026, 10, 6)
    assert clocks.prev_session("KR", date(2026, 10, 12), cal=cal) == date(2026, 10, 8)


test_tz02_event_to_kr_open_gap_session.test_ids = ["T-TZ-02"]


def test_gap_sessions_values():
    cal = fixture_set()
    assert clocks.gap_sessions("KR", date(2026, 10, 6), cal=cal) == 2
    assert clocks.gap_sessions("KR", date(2026, 10, 12), cal=cal) == 2
    assert clocks.gap_sessions("KR", date(2026, 11, 27), cal=cal) == 0
    assert clocks.gap_sessions("KR", date(2026, 10, 8), cal=cal) == 1


test_gap_sessions_values.test_ids = ["I-06b"]


# --------------------------------------------------------------------------- #
# T-CAL-01 / T-CAL-02
# --------------------------------------------------------------------------- #
def test_cal01_unsigned_refused_signed_accepted():
    cal = fixture_set()
    assert cal.file("kr_sessions").signed_off_by == SIGNER and cal.version == "1.0.0-fixture"
    base = fixture_docs()

    def variant(key, mutate, unsigned_manifest=False):
        docs = {k: v for k, v in fixture_docs().items() if k in ("kr_sessions", "holidays_KRX")}
        mutate(docs)
        return fixture_set(key, docs) if not unsigned_manifest else _unsigned_manifest_set(key, docs)

    def set_unsigned(docs):
        docs["kr_sessions"]["signed_off_by"] = None

    def set_empty(docs):
        docs["holidays_KRX"]["signed_off_by"] = "   "

    def row_unsigned(docs):
        docs["kr_sessions"]["rows"][0]["signed_off_by"] = ""

    def no_signed_utc(docs):
        docs["kr_sessions"]["signed_utc"] = None

    for key, mut in (("u1", set_unsigned), ("u2", set_empty), ("u3", row_unsigned), ("u4", no_signed_utc)):
        bad = variant(key, mut)
        exc = _raises(lambda: clocks.decision_time_utc("KR", date(2026, 10, 2), cal=bad), CalendarUnsigned)
        assert "sign" in str(exc).lower(), exc
    # an unquoted date scalar (PyYAML 1.1 reads it as a date object) is refused before any signature check
    unq = variant("u5", lambda d: None)
    path = unq.data_dir / "holidays_KRX.yaml"
    text = path.read_text(encoding="utf-8")
    assert "date: '1995-01-01'" in text
    path.write_text(text.replace("date: '1995-01-01'", "date: 1995-01-01", 1), encoding="utf-8")
    assert "quote" in str(_raises(lambda: CalendarSet(unq.data_dir).file("holidays_KRX"), CalendarUnsigned))
    # an edit under an old signature (md5 mismatch) and a manifest that names no test are unsigned changes
    tampered = variant("u6", lambda d: None)
    path = tampered.data_dir / "kr_sessions.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["rows"].append(_row(kind="csat_day", date="2026-11-19", effective_from="2026-11-19", effective_to="2026-11-19"))
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    fresh = CalendarSet(tampered.data_dir)
    assert "md5" in str(_raises(lambda: fresh.file("kr_sessions"), CalendarUnsigned))
    assert fresh.file("holidays_KRX").version == "1.0.0-fixture"            # the other file still loads
    m = tampered.data_dir / "MANIFEST.yaml"
    mdoc = yaml.safe_load(m.read_text(encoding="utf-8"))
    for r in mdoc["rows"]:
        r["test_ids"] = []
    m.write_text(yaml.safe_dump(mdoc, sort_keys=False), encoding="utf-8")
    assert "test id" in str(_raises(lambda: CalendarSet(tampered.data_dir).file("holidays_KRX"), CalendarUnsigned))
    m.unlink()
    assert "MANIFEST" in str(_raises(lambda: CalendarSet(tampered.data_dir).file("holidays_KRX"), CalendarUnsigned))
    unsigned_m = variant("u7", lambda d: None, unsigned_manifest=True)
    assert "signer" in str(_raises(lambda: unsigned_m.file("holidays_KRX"), CalendarUnsigned))
    # the fail-closed consequence: status and the ARM precondition say so; the regime file is independent
    bad = variant("u8", set_unsigned)
    st = store.status("KR", date(2026, 10, 2), cal=bad)
    assert st["signed"] is False and "kr_sessions" in st["refused"]
    assert store.arm_precondition(date(2026, 10, 2), "KR", cal=bad) is False
    assert store.arm_precondition(date(2026, 10, 2), "KR", cal=cal) is True
    assert base["kr_sessions"]["md5"] is None            # the fixture builder, not the library, signs


test_cal01_unsigned_refused_signed_accepted.test_ids = ["T-CAL-01"]


def _unsigned_manifest_set(key, docs):
    tmp = tempfile.TemporaryDirectory(prefix="quantgen_cal_")
    _write_set(Path(tmp.name), docs, unsigned_manifest=True)
    _CACHE[key] = (tmp, CalendarSet(Path(tmp.name)))
    return _CACHE[key][1]


def test_cal01_shipped_drafts_are_refused_and_acting_inputs_fail_closed():
    """The shipped drafts carry signed_off_by: null -> refused; every KR and US clock raises CalendarUnsigned, which the
    data layer maps to MissingInput('missing') with fail_closed (brief F-5); no book can ARM."""
    live = store.default()
    assert live.data_dir == store.DATA_DIR
    for fid in live.file_ids():
        assert live.refusal(fid), fid
        raw = store.read_yaml(live.data_dir / f"{fid}.yaml")
        assert raw.get("signed_off_by") is None and raw.get("md5") is None, fid       # never signed by the build
        assert raw.get("unverified") and raw.get("owner_must_sign"), fid
    for market in ("KR", "US", "JP", "CN", "HK", "TW"):
        _raises(lambda: clocks.decision_time_utc(market, date(2026, 10, 2), cal=live), CalendarUnsigned)
        _raises(lambda: clocks.is_session(market, date(2026, 10, 2), cal=live), CalendarUnsigned)
        assert store.arm_precondition(date(2026, 10, 2), market, cal=live) is False
    _raises(lambda: regime.regime_tags("KR", date(2026, 10, 2), cal=live), CalendarUnsigned)
    _raises(lambda: publication.publication_instant({"schedule_id": "H15"}, date(2026, 10, 2), cal=live), CalendarUnsigned)
    assert store.status("KR", date(2026, 10, 2), cal=live)["signed"] is False
    assert live.version == "unsigned"
    manifest = store.read_yaml(store.DATA_DIR / "MANIFEST.yaml")
    assert all(r["md5"] is None and r["signed_off_by"] is None for r in manifest["rows"])
    assert {r["file"] for r in manifest["rows"]} == {f"{f}.yaml" for f in live.file_ids()}
    # the rules-store paths of section 7 resolve to these files
    from core.rules.macro_rules import load_store
    s = load_store()
    assert s.get("calendars.regime_tags_file") == "core/calendars/data/kr_regime_tags.yaml"
    assert s.get("data_contracts.source_exceptions") == "core/calendars/data/source_skipped.yaml"
    assert (store.DATA_DIR.parents[2] / s.get("calendars.regime_tags_file")).is_file()


test_cal01_shipped_drafts_are_refused_and_acting_inputs_fail_closed.test_ids = ["T-CAL-01"]


def test_cal01_calendar_change_governance_event():
    from core.rules.governance import read_events, verify_chain
    cal = fixture_set()
    clock = lambda: U(2026, 10, 6, 7, 0)
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "governance_events.jsonl"
        first = store.record_calendar_changes(log, ("kr_sessions", "holidays_KRX"), clock, cal=cal)
        assert len(first) == 2 and verify_chain(log).ok
        assert store.record_calendar_changes(log, ("kr_sessions", "holidays_KRX"), clock, cal=cal) == []
        docs = fixture_docs()
        docs["kr_sessions"]["version"] = "1.0.1-fixture"
        docs["kr_sessions"]["rows"].append(_row(kind="csat_day", date="2026-11-19", effective_from="2026-11-19", effective_to="2026-11-19"))
        revised = fixture_set("revised", docs)
        again = store.record_calendar_changes(log, ("kr_sessions", "holidays_KRX"), clock, cal=revised)
        assert len(again) == 1
        ev = read_events(log)[-1]
        assert ev["kind"] == "calendar_change" and ev["key"] == "kr_sessions" and ev["rule_id"] == "R-20"
        assert ev["old"]["version"] == "1.0.0-fixture" and ev["new"]["version"] == "1.0.1-fixture" and ev["actor"] == "owner"
        unsigned = {k: v for k, v in fixture_docs().items() if k in ("kr_sessions", "holidays_KRX")}
        unsigned["kr_sessions"]["signed_off_by"] = None
        assert store.record_calendar_changes(log, ("kr_sessions",), clock, cal=fixture_set("gov_unsigned", unsigned)) == []


test_cal01_calendar_change_governance_event.test_ids = ["T-CAL-01"]


def test_cal02_coverage_warn_page_halt():
    """A file ending N sessions after the decision date: N=61 no alert, 60 warn, 20 page, 0 page; outside -> OPS HALT
    calendar_coverage through the injected runtime hook, never a NotASession."""
    base = fixture_set()
    decision = date(2026, 10, 6)
    sessions = clocks.sessions_between("KR", decision + timedelta(days=1), date(2027, 6, 30), cal=base)
    halts: list[tuple] = []

    def halt(book_id, cls, reason):
        halts.append((book_id, cls, reason))

    for n, severity in ((61, None), (60, "warn"), (20, "page"), (0, "page")):
        hi = sessions[n - 1] if n else decision
        docs = fixture_docs()
        docs["holidays_KRX"]["covers"]["to"] = hi.isoformat()
        cal = fixture_set(f"cov{n}", docs)
        assert store.sessions_left(cal, cal.file("holidays_KRX"), decision) == n
        alerts = store.check_coverage(decision, ("holidays_KRX",), cal=cal, now_utc=U(2026, 10, 6, 6, 41))
        if severity is None:
            assert alerts == []
        else:
            assert len(alerts) == 1 and alerts[0]["severity"] == severity and alerts[0]["code"] == "calendar_coverage"
            assert alerts[0]["component"] == "core/calendars" and alerts[0]["count"] == 1 and alerts[0]["first_seen_utc"] == "2026-10-06T06:41:00Z"
        st = store.status("KR", decision, cal=cal)
        assert st["sessions_left"] == n and st["signed"] is True
        assert store.arm_precondition(decision, "KR", cal=cal) is (n >= 60)
    cal = fixture_set("cov0")
    beyond = decision + timedelta(days=1)
    exc = _raises(lambda: store.check_coverage(beyond, ("holidays_KRX",), cal=cal, now_utc=U(2026, 10, 7),
                                               book_ids=("recommended:KR", "specification:KR"), halt=halt), CalendarCoverageError)
    assert "calendar_coverage" in str(exc) or "outside" in str(exc)
    assert halts == [("recommended:KR", "OPS", "calendar_coverage"), ("specification:KR", "OPS", "calendar_coverage")]
    _raises(lambda: clocks.decision_time_utc("KR", beyond, cal=cal), CalendarCoverageError)      # never NotASession
    assert store.status("KR", beyond, cal=cal)["alerts"][0]["severity"] == "page"
    # the shipped config values drive the thresholds
    cov = base.config["coverage"]
    assert (cov["min_sessions_ahead"], cov["warn_at_sessions_left"], cov["page_at_sessions_left"], cov["outside_coverage"]) == (60, 60, 20, "OPS_HALT")


test_cal02_coverage_warn_page_halt.test_ids = ["T-CAL-02"]


def test_cal02_2027_files_signed_before_2026_11_01():
    raise NotRun("OWNER: the 2027 KRX, NYSE, Fed and SIFMA files must be signed before 2026-11-01 (spec L2101); "
                 "core/calendars/data/holidays_{KRX,NYSE,FED,SIFMA}.yaml are unsigned drafts")


test_cal02_2027_files_signed_before_2026_11_01.test_ids = ["T-CAL-02"]


# --------------------------------------------------------------------------- #
# T-REGIME-01
# --------------------------------------------------------------------------- #
def test_regime01_point_clauses_and_fail_closed():
    cal = fixture_set()
    R = lambda d: regime.regime_tags("KR", d, cal=cal)
    assert R(date(1997, 6, 2))["price_limit"] == 0.08 and R(date(1998, 6, 1))["price_limit"] == 0.12
    assert R(date(1999, 6, 1))["price_limit"] == 0.15 and R(date(2015, 6, 15))["price_limit"] == 0.30
    assert R(date(2015, 6, 14))["price_limit"] == 0.15
    assert R(date(1997, 10, 1))["fx_regime"] == "peg_1997" and R(date(1997, 9, 21))["fx_regime"] != "peg_1997"
    assert R(date(2002, 1, 2))["etf_available"] is False and R(date(2003, 1, 2))["etf_available"] is True
    assert R(date(2024, 6, 3))["short_sale_ban"] is True and R(date(2022, 6, 3))["short_sale_ban"] is False
    assert R(date(2022, 6, 3))["short_sale_regime"] == "partial_ban_non_index"
    assert R(date(2026, 10, 2))["sell_tax_pct"] == 0.20 and R(date(2025, 6, 2))["sell_tax_pct"] == 0.15
    assert R(date(2024, 2, 26))["value_up"] == "post_2024_02_26" and R(date(2024, 2, 25))["value_up"] == "pre"
    assert R(date(1997, 6, 7))["saturday_session"] is True and R(date(1998, 12, 12))["saturday_session"] is False
    tags = R(date(2026, 10, 2))
    assert tuple(tags) == regime.TAGS and all(v is not None for v in tags.values())
    assert tags["close_time_kst"] == "15:30" and tags["random_end"] == "unconditional_le_30s" and tags["usdkrw_onshore_hours"] == "24h"
    # every date of the fixture span returns a full tag set (the committed expected-values comparison is OWNER)
    d = date(1995, 1, 1)
    while d <= date(2026, 12, 31):
        assert tuple(R(d)) == regime.TAGS
        d += timedelta(days=37)
    _raises(lambda: R(date(1994, 12, 31)), CalendarCoverageError)
    _raises(lambda: R(date(2028, 1, 1)), CalendarCoverageError)
    _raises(lambda: regime.regime_tags("US", date(2026, 10, 2), cal=cal), KeyError)
    assert regime.regime_span_covered(date(1997, 1, 3), date(2026, 10, 2), cal=cal)
    _raises(lambda: regime.require_regime_span(date(1997, 1, 3), date(2028, 3, 1), cal=cal), CalendarCoverageError)
    # a gap or an overlap in one tag is a load-time error
    docs = {k: v for k, v in fixture_docs().items() if k == "kr_regime_tags"}
    docs["kr_regime_tags"]["rows"] = [r for r in docs["kr_regime_tags"]["rows"] if not (r["tag"] == "etf_available" and r["value"] is True)]
    _raises(lambda: regime.regime_tags("KR", date(2026, 10, 2), cal=fixture_set("regime_gap", docs)), CalendarUnsigned)
    docs = {k: v for k, v in fixture_docs().items() if k == "kr_regime_tags"}
    docs["kr_regime_tags"]["rows"].append(_row(tag="etf_available", value=True, effective_from="2010-01-01", effective_to=None))
    _raises(lambda: regime.regime_tags("KR", date(2026, 10, 2), cal=fixture_set("regime_overlap", docs)), CalendarUnsigned)


test_regime01_point_clauses_and_fail_closed.test_ids = ["T-REGIME-01"]


def test_regime01_full_range_expected_values_file():
    raise NotRun("OWNER: tests/fixtures/macro/kr_regime_tags_expected.csv (1995-01-01..2026-12-31, built from the official "
                 "notices incl. the pre-Apr-1995 price limit, sell-tax steps, BoK fx regimes) is an owner deliverable; "
                 "the shipped kr_regime_tags.yaml is an unsigned draft")


test_regime01_full_range_expected_values_file.test_ids = ["T-REGIME-01"]


# --------------------------------------------------------------------------- #
# T-SAT-01
# --------------------------------------------------------------------------- #
def test_sat01_saturday_sessions_and_completeness():
    cal = fixture_set()
    closed = cal.holiday_set("KRX")[0]
    d, n_before, n_after = date(1995, 1, 7), 0, 0
    assert d.weekday() == 5
    while d <= date(2001, 12, 29):
        want = d < date(1998, 12, 12) and d not in closed
        assert clocks.is_session("KR", d, cal=cal) is want, d
        n_before += want
        n_after += d >= date(1998, 12, 12)
        d += timedelta(days=7)
    assert n_before > 150 and n_after > 150
    assert clocks.is_session("KR", date(1997, 3, 1), cal=cal) is False          # a Saturday holiday
    assert clocks.is_session("KR", date(1997, 6, 8), cal=cal) is False          # Sunday never
    # completeness: a close list without the Saturdays fails; one with every session passes
    start, end = date(1997, 1, 3), date(1998, 12, 31)
    sessions = clocks.sessions_between("KR", start, end, cal=cal)
    weekdays_only = [s for s in sessions if s.weekday() < 5]
    rep = clocks.completeness_check("KR", weekdays_only, start, end, cal=cal)
    assert not rep.ok and rep.missing and all(m.weekday() == 5 for m in rep.missing) and not rep.extra
    assert clocks.completeness_check("KR", sessions, start, end, cal=cal).ok
    dup = clocks.completeness_check("KR", sessions + [sessions[0]], start, end, cal=cal)
    assert dup.duplicates == (sessions[0],)
    extra = clocks.completeness_check("KR", sessions + [date(1997, 6, 8)], start, end, cal=cal)
    assert extra.extra == (date(1997, 6, 8),)


test_sat01_saturday_sessions_and_completeness.test_ids = ["T-SAT-01"]


def test_sat01_real_kospi_completeness_and_variance_ratio():
    require_fixture("krx_kospi_official_close_1997-01-03_2026-10-02.csv")
    raise AssertionError("unreachable")


test_sat01_real_kospi_completeness_and_variance_ratio.test_ids = ["T-SAT-01"]


# --------------------------------------------------------------------------- #
# T-XMKT-01
# --------------------------------------------------------------------------- #
def test_xmkt01_same_instant_closes():
    cal = fixture_set()
    csat = {date(2015, 11, 12), date(2025, 11, 13)}
    checked = {"jp_late": 0, "jp_mid": 0, "jp_early": 0, "tw": 0, "hk": 0}
    d = date(2015, 1, 5)
    while d <= date(2027, 6, 30):
        if clocks.is_session("KR", d, cal=cal) and d not in csat:
            bound = clocks.close_print_bound_utc("KR", d, cal=cal)
            if clocks.is_session("JP", d, cal=cal):
                usable = clocks.cross_market_usable("JP", d, bound, cal=cal)
                if d >= date(2024, 11, 5):
                    assert not usable, d
                    checked["jp_late"] += 1
                elif d >= date(2016, 8, 1):
                    assert usable, d
                    checked["jp_mid"] += 1
                else:
                    assert not usable, d
                    checked["jp_early"] += 1
            if d.weekday() < 5 and clocks.is_session("TW", d, cal=cal):
                assert clocks.cross_market_usable("TW", d, bound, cal=cal), d
                checked["tw"] += 1
            if clocks.is_session("HK", d, cal=cal):
                assert not clocks.cross_market_usable("HK", d, bound, cal=cal), d
                checked["hk"] += 1
            if clocks.is_session("CN", d, cal=cal):
                assert not clocks.cross_market_usable("CN", d, bound, cal=cal), d
        d += timedelta(days=1)
    assert all(v > 100 for v in checked.values()), checked
    b = clocks.close_print_bound_utc("KR", date(2025, 11, 13), cal=cal)
    assert b == U(2025, 11, 13, 7, 30, 30)
    assert clocks.cross_market_usable("JP", date(2025, 11, 13), b, cal=cal) and clocks.cross_market_usable("CN", date(2025, 11, 13), b, cal=cal)
    assert not clocks.cross_market_usable("HK", date(2025, 11, 13), b, cal=cal)
    b15 = clocks.close_print_bound_utc("KR", date(2015, 11, 12), cal=cal)      # configured 16:00 KST close -> 07:00:30Z
    assert b15 == U(2015, 11, 12, 7, 0, 30)
    assert clocks.cross_market_usable("JP", date(2015, 11, 12), b15, cal=cal) and not clocks.cross_market_usable("CN", date(2015, 11, 12), b15, cal=cal)
    # the worked boundary: 06:00Z + 60 s vs the 06:00:30Z bound before 2016-08-01
    assert clocks.close_print_bound_utc("JP", date(2016, 7, 29), cal=cal) + timedelta(seconds=cal.buffer_s) == U(2016, 7, 29, 6, 1)
    assert cal.buffer_s == 60
    # a Saturday session follows its signed close: the TW close is a weekday-only fact, the JP market is closed
    sat = date(1997, 6, 7)
    _raises(lambda: clocks.is_session("JP", sat, cal=cal), CalendarCoverageError)      # JPX fixture starts 2015


test_xmkt01_same_instant_closes.test_ids = ["T-XMKT-01"]


# --------------------------------------------------------------------------- #
# Publication calendars: T-H15-01, T-H10-02, T-VIX-01, T-AVAIL-01 (calendar halves)
# --------------------------------------------------------------------------- #
def test_publication_h15_h10_vix_avail_timing():
    cal = fixture_set()
    H15 = {"series_id": "DGS10", "schedule_id": "H15", "obs_calendar": "SIFMA"}
    H10 = {"series_id": "DEXKOUS", "schedule_id": "H10", "obs_calendar": "WEEKDAYS"}
    PI, UA = publication.publication_instant, publication.usable_at
    ny = ZoneInfo(NY)
    # separate sets: Columbus Day 2026-10-12 is a NYSE session and a Fed holiday
    assert clocks.is_session("US", date(2026, 10, 12), cal=cal) and not publication.fed_business_day(date(2026, 10, 12), cal=cal)
    assert not publication.nyse_holiday(date(2026, 10, 12), cal=cal) and publication.nyse_holiday(date(2026, 11, 26), cal=cal)
    assert publication.sifma_status(date(2026, 11, 27), cal=cal) == "early_close" and publication.sifma_status(date(2026, 4, 3), cal=cal) == "closed"
    assert publication.sifma_status(date(2026, 10, 8), cal=cal) == "open" and publication.sifma_status(date(2026, 10, 10), cal=cal) == "closed"
    # H.15: DGS10 Fri 2015-01-02 -> posted Mon 2015-01-05 16:15 ET -> KRX Tue 2015-01-06, not Mon
    assert PI(H15, date(2015, 1, 2), cal=cal) == datetime(2015, 1, 5, 16, 15, tzinfo=ny).astimezone(UTC)
    assert UA(H15, date(2015, 1, 2), "KR", cal=cal) == clocks.close_print_bound_utc("KR", date(2015, 1, 6), cal=cal)
    assert UA(H15, date(2015, 1, 2), "KR", cal=cal) != clocks.close_print_bound_utc("KR", date(2015, 1, 5), cal=cal)
    assert UA(H15, date(2026, 10, 9), "US", cal=cal) == clocks.close_print_bound_utc("US", date(2026, 10, 14), cal=cal)
    assert UA(H15, date(2026, 10, 8), "US", cal=cal) == clocks.close_print_bound_utc("US", date(2026, 10, 12), cal=cal)
    # R4b state row timing: data dated 2026-09-23 -> posted 09-24 16:15 ET -> first US close 09-25 -> earns from 09-28
    first_us = UA(H15, date(2026, 9, 23), "US", cal=cal)
    assert first_us == clocks.close_print_bound_utc("US", date(2026, 9, 25), cal=cal)
    assert clocks.next_session("US", date(2026, 9, 25), cal=cal) == date(2026, 9, 28)
    # Treasury par channel with a logged posting time: usable + 1 business day at a US close
    par = {"series_id": "TREASURY_PAR_10Y", "schedule_id": "TREASURY_PAR", "obs_calendar": "SIFMA"}
    assert UA(par, date(2026, 9, 23), "US", cal=cal) == clocks.close_print_bound_utc("US", date(2026, 9, 24), cal=cal)
    # H.10: DEXKOUS Fri 2026-09-25 -> Mon 09-28 16:15 ET -> KRX Tue 09-29 and not before
    assert UA(H10, date(2026, 9, 25), "KR", cal=cal) == clocks.close_print_bound_utc("KR", date(2026, 9, 29), cal=cal)
    assert publication.latest_usable_obs(H10, "KR", date(2026, 10, 2), cal=cal) == date(2026, 9, 25)
    assert publication.latest_usable_obs(H10, "KR", date(2026, 9, 28), cal=cal) == date(2026, 9, 18)
    for d in (date(2026, 10, 5), date(2026, 10, 9)):
        assert PI(H10, d, cal=cal) == datetime(2026, 10, 13, 16, 15, tzinfo=ny).astimezone(UTC)
        assert UA(H10, d, "KR", cal=cal) == clocks.close_print_bound_utc("KR", date(2026, 10, 14), cal=cal)
    # VIX: official close 16:15 ET on D is not usable at the US close of D; usable at D+1 and at KRX K >= D+1
    vix = {"series_id": "VIXCLS", "schedule_id": "VIXCLS_CBOE", "obs_calendar": "CBOE"}
    D = date(2026, 9, 23)
    assert PI(vix, D, cal=cal) > clocks.close_print_bound_utc("US", D, cal=cal)
    assert UA(vix, D, "US", cal=cal) == clocks.close_print_bound_utc("US", date(2026, 9, 24), cal=cal)
    assert UA(vix, D, "KR", cal=cal) == clocks.close_print_bound_utc("KR", clocks.next_session("KR", D, cal=cal), cal=cal)
    assert clocks.next_session("KR", D, cal=cal) == date(2026, 9, 28)                       # Chuseok in the fixture
    assert UA(vix, date(2026, 9, 21), "KR", cal=cal) == clocks.close_print_bound_utc("KR", date(2026, 9, 22), cal=cal)
    assert UA(vix, date(2026, 9, 21), "KR", cal=cal) != clocks.close_print_bound_utc("KR", date(2026, 9, 21), cal=cal)
    fred = {"series_id": "VIXCLS", "schedule_id": "VIXCLS_FRED", "obs_calendar": "CBOE", "channel": "FRED"}
    assert UA(fred, D, "US", cal=cal) == clocks.close_print_bound_utc("US", date(2026, 9, 24), cal=cal)       # declared lag
    logged = dict(fred, posting_utc="2026-09-24T21:05:00Z")
    assert PI(logged, D, cal=cal) == U(2026, 9, 24, 21, 5)
    assert UA(logged, D, "US", cal=cal) == clocks.close_print_bound_utc("US", date(2026, 9, 25), cal=cal)
    # T-AVAIL-01 rows + the injected registry error (H.15 posted at D) changes the KRX answer -> the golden would fail
    assert clocks.decision_time_utc("KR", date(2025, 11, 13), cal=cal) == U(2025, 11, 13, 7, 30)
    wrong = dict(H15, rule="same_day")
    assert UA(wrong, date(2015, 1, 2), "KR", cal=cal) == clocks.close_print_bound_utc("KR", date(2015, 1, 5), cal=cal)
    assert UA(wrong, date(2015, 1, 2), "KR", cal=cal) != UA(H15, date(2015, 1, 2), "KR", cal=cal)
    # next_expected_obs skips source-exception dates; add_publication_bdays keeps the wall time across DST
    assert publication.next_expected_obs(H10, date(2017, 1, 19), cal=cal) == date(2017, 1, 23)
    assert publication.next_expected_obs(H10, date(2017, 1, 18), cal=cal) == date(2017, 1, 19)
    assert publication.next_expected_obs(H15, date(2026, 4, 2), cal=cal) == date(2026, 4, 6)       # Good Friday on SIFMA
    assert publication.source_skipped("DEXKOUS", cal=cal) >= {date(2017, 1, 20), date(2020, 12, 24)}
    due = PI(H15, date(2026, 3, 6), cal=cal)                                     # Mon 2026-03-09 16:15 EDT (DST started 03-08)
    assert due == U(2026, 3, 9, 20, 15)
    assert publication.add_publication_bdays(H15, due, 1, cal=cal) == U(2026, 3, 10, 20, 15)
    before = PI(H15, date(2026, 3, 5), cal=cal)                                  # Fri 2026-03-06 16:15 EST
    assert before == U(2026, 3, 6, 21, 15) and publication.add_publication_bdays(H15, before, 1, cal=cal) == U(2026, 3, 9, 20, 15)
    # ECOS USD/KRW effective-dated same-day close; KODEX 200 basket next KRX session 08:00 KST
    ecos = {"series_id": "ECOS_USDKRW", "schedule_id": "ECOS_USDKRW", "obs_calendar": "ECOS"}
    assert PI(ecos, date(2016, 7, 29), cal=cal) == U(2016, 7, 29, 6, 0) and PI(ecos, date(2016, 8, 1), cal=cal) == U(2016, 8, 1, 6, 30)
    assert PI({"schedule_id": "KODEX200_PDF"}, date(2026, 10, 2), cal=cal) == U(2026, 10, 5, 23, 0)
    # a release event that is cancelled removes the expected instant; a delayed one moves it
    bls = {"series_id": "CPIAUCSL", "schedule_id": "BLS", "release_event_type": "US_CPI", "obs_calendar": "WEEKDAYS",
           "release_dates": {"2025-10-01": "2025-11-13"}}
    cancelled = [{"type": "US_CPI", "scheduled_utc": "2025-11-13T13:30:00Z", "status": "cancelled", "released_utc": None}]
    _raises(lambda: PI(bls, date(2025, 10, 1), cal=cal, events=cancelled), publication.NoExpectedObservation)
    delayed = [{"type": "US_CPI", "scheduled_utc": "2025-11-13T13:30:00Z", "status": "delayed", "released_utc": "2025-11-20T13:30:00Z"}]
    assert PI(bls, date(2025, 10, 1), cal=cal, events=delayed) == U(2025, 11, 20, 13, 30)
    assert PI(bls, date(2025, 10, 1), cal=cal) == U(2025, 11, 13, 13, 30)
    _raises(lambda: PI({"schedule_id": "BLS"}, date(2025, 10, 1), cal=cal), KeyError)
    # a bare series id resolves through the registry (core.calendars.adapter, integration): H.15 of Fri 2026-01-02 posts Mon 16:15 ET
    assert PI("DGS10", date(2026, 1, 2), cal=cal) == U(2026, 1, 5, 21, 15)
    _raises(lambda: PI("NO_SUCH_SERIES", date(2026, 1, 2), cal=cal), KeyError)


test_publication_h15_h10_vix_avail_timing.test_ids = ["T-H15-01", "T-H10-02", "T-VIX-01", "T-AVAIL-01"]


# --------------------------------------------------------------------------- #
# Section 6.3 event store shape (M1: shape and loader only)
# --------------------------------------------------------------------------- #
def test_event_store_shape_and_artifact():
    from core.ficc.macro_artifacts import provenance
    cal = fixture_set()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "events.yaml"
        path.write_text(yaml.safe_dump([{
            "event_id": "FOMC-2026-10-28", "type": "FOMC", "region": "US", "scheduled_utc": "2026-10-28T18:00:00Z",
            "status": "scheduled", "released_utc": None, "source": "federalreserve.gov FOMC calendar",
            "windows": [{"market": "US", "action": "evaluator_block_new_intraday_entries", "start_utc": "2026-10-28T17:45:00Z",
                         "end_utc": "2026-10-28T19:00:00Z", "resume_condition": "VIX < pre-14:00 ET level else 19:30Z"}],
            "kr_open_gap_session": "2026-10-29", "gap_sessions": None, "var_display_scale": None, "scenario_tag": None,
            "notes": "KR opening-gap event night"}], sort_keys=False), encoding="utf-8")
        loaded = events.load_events(path)
    assert len(loaded) == 1 and loaded[0].type == "FOMC" and loaded[0].kr_open_gap_session == "2026-10-29"
    assert clocks.kr_open_gap_session(events.utc(loaded[0].scheduled_utc), cal=cal).isoformat() == loaded[0].kr_open_gap_session
    prov = provenance(clock=lambda: U(2026, 10, 2, 6, 41, 7), knowledge_utc="2026-10-02T06:40:50Z", config_hash="c" * 32,
                      data_snapshot_id="d" * 32)
    art = events.event_calendar(loaded, provenance=prov, calendar_version=cal.version)
    assert art["schema"] == "quantgen.event_calendar" and art["read_only"] is True and art["calendar_version"] == "1.0.0-fixture"
    assert art["events"][0]["windows"][0]["action"] == "evaluator_block_new_intraday_entries"
    bad = dict(loaded[0].to_dict(), type="FOMC", status="done")
    _raises(lambda: events.Event.from_dict(bad), ValueError)
    _raises(lambda: events.event_calendar([dict(loaded[0].to_dict(), gap_sessions=-1)], provenance=prov, calendar_version="x"), ValueError)
    assert "KRX_HOLIDAY_GAP" in events.EVENT_TYPES and "annotate_only" in events.WINDOW_ACTIONS


test_event_store_shape_and_artifact.test_ids = ["I-06"]


# --------------------------------------------------------------------------- #
# Market ids
# --------------------------------------------------------------------------- #
def test_market_ids_and_venue_maps():
    from core import markets
    from core.ficc.macro_schema import enum_of
    assert markets.MACRO_MARKETS == enum_of("macro_state", "/market")
    assert markets.market_to_venue("KR") == "KRX" and markets.market_to_venue("JP") == "TSE" and markets.venue_to_market("HKEX") == "HK"
    assert markets.venue_to_market("SZSE") == "CN" and markets.venue_to_market(markets.market_to_venue("TW")) == "TW"
    _raises(lambda: markets.market_to_venue("CRYPTO"), KeyError)
    _raises(lambda: markets.market_to_venue("KRX"), KeyError)
    assert all(markets.market_to_venue(m) in markets.codes() for m in clocks.M1_MARKETS)
    assert set(clocks.M1_MARKETS) == set(store.MARKET_FILES) == set(store.MARKET_HOLIDAY_SET)


test_market_ids_and_venue_maps.test_ids = ["T-XMKT-01"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
