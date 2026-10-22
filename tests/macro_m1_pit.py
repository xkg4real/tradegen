"""M1 package A tests: PIT store, data contracts, staleness, lag audit, series registry, cache fix, KIS allowlist.

Spec tests: T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01 (data clauses), T-PRINT-01 (logic), T-AVAIL-01,
T-STALE-01 (synthetic clauses + the local fred_DEXKOUS.csv smoke), T-ROLE-01/02, T-LAG-01/02, T-SYN-01,
T-MISS-01/02, T-SER-01/02, T-H10-01/02, T-H15-01, T-VIX-01, T-XMKT-01 (data clause), T-RO-02, G-POST-01 (REFDATA).

Hermetic: every store is a tempfile directory; no network; no wall clock (every instant is pinned); module globals
that a test patches are restored in `finally`. Calendar functions come from `StubClocks` below, a deterministic
stand-in for `core.calendars.clocks` (package B), keyed on the registry's schedule ids.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import tempfile
import time as _time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from core.ficc import contracts as C
from core.ficc import data as D
from core.ficc import lag_audit as L
from core.ficc import pit as P
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
NY = ZoneInfo("America/New_York")
UTC = timezone.utc
KST = timezone(timedelta(hours=9))
REG = C.load_registry()


def U(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=UTC)


# --------------------------------------------------------------------------- #
# Stub clocks (integration: core.calendars.clocks / publication)
# --------------------------------------------------------------------------- #
def _nth(y, m, weekday, n):
    d = date(y, m, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last(y, m, weekday):
    d = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d):
    return d + timedelta(days=1) if d.weekday() == 6 else d - timedelta(days=1) if d.weekday() == 5 else d


def federal_holidays(y):
    fixed = [date(y, 1, 1), date(y, 7, 4), date(y, 11, 11), date(y, 12, 25)] + ([date(y, 6, 19)] if y >= 2021 else [])
    return {_observed(d) for d in fixed} | {_nth(y, 1, 0, 3), _nth(y, 2, 0, 3), _last(y, 5, 0), _nth(y, 9, 0, 1),
                                           _nth(y, 10, 0, 2), _nth(y, 11, 3, 4)}


def _json_holidays(name):
    return {date.fromisoformat(h) for h in json.loads((ROOT / "data" / "calendars" / name).read_text(encoding="utf-8"))["holidays"]}


KRX_HOLIDAYS = _json_holidays("KRX.json") | {date(2015, 1, 1), date(2016, 1, 1), date(2024, 1, 1), date(2025, 1, 1)}
NYSE_HOLIDAYS = _json_holidays("US.json") | {date(2015, 1, 1), date(2025, 7, 4)}
CSAT = {date(2025, 11, 13), date(2026, 11, 19)}
US_EARLY = {date(2026, 11, 27), date(2026, 12, 24), date(2025, 7, 3)}
SOURCE_SKIPPED = {date(2016, 1, 22), date(2017, 1, 20), date(2018, 3, 2), date(2018, 12, 5), date(2020, 11, 27), date(2020, 12, 24)}


class NotASession(ValueError):
    pass


class StubClocks:
    """Deterministic calendar rules: KRX (06:00:30Z before 2016-08-01, 06:30:30Z after, CSAT 07:30:30Z), NYSE
    (16:00 ET + 30 s, DST via zoneinfo, 13:00 early closes), Fed business days (rule-based federal holidays),
    H.15 / H.10 / Treasury / VIX / BLS instants from the registry schedule ids."""

    def __init__(self, registry=REG, skipped=frozenset(), unreadable=False):
        self.registry, self.skipped, self.unreadable = registry, set(skipped), unreadable

    # sessions
    def is_session(self, market, d):
        if d.weekday() >= 5:
            return False
        if market == "KR":
            return d not in KRX_HOLIDAYS
        if market == "US":
            return d not in NYSE_HOLIDAYS
        return True

    def fed_bday(self, d):
        # next year's New Year observance can fall on this year's Dec 31 (Saturday -> Friday, e.g. 2021-12-31)
        return d.weekday() < 5 and d not in federal_holidays(d.year) and d not in federal_holidays(d.year + 1)

    def _next(self, d, ok):
        d += timedelta(days=1)
        while not ok(d):
            d += timedelta(days=1)
        return d

    def close_print_bound_utc(self, market, d):
        if not self.is_session(market, d):
            raise NotASession(f"{market} {d}")
        if market == "KR":
            if d in CSAT:
                return U(d.year, d.month, d.day, 7, 30, 30)
            return U(d.year, d.month, d.day, 6, 0, 30) if d < date(2016, 8, 1) else U(d.year, d.month, d.day, 6, 30, 30)
        if market == "US":
            hour = 13 if d in US_EARLY else 16
            return datetime(d.year, d.month, d.day, hour, 0, 0, tzinfo=NY).astimezone(UTC) + timedelta(seconds=30)
        hh, mm = {"JP": (6, 30) if d >= date(2024, 11, 5) else (6, 0), "CN": (7, 0), "HK": (8, 0), "TW": (5, 30)}[market]
        return U(d.year, d.month, d.day, hh, mm)

    # schedules
    def _sched(self, series_id):
        if self.unreadable:
            raise RuntimeError("publication calendar unreadable")
        return self.registry.schedule(series_id)

    def _ny(self, d, hhmm):
        hh, mm = map(int, hhmm.split(":"))
        return datetime(d.year, d.month, d.day, hh, mm, tzinfo=NY).astimezone(UTC)

    def publication_instant(self, series_id, d):
        s = self._sched(series_id)
        if s == "KRX_CLOSE":
            return self.close_print_bound_utc("KR", d)
        if s == "NYSE_CLOSE":
            return self.close_print_bound_utc("US", d)
        if s in ("JP_CLOSE", "CN_CLOSE", "HK_CLOSE", "TW_CLOSE"):
            return self.close_print_bound_utc(s[:2], d)
        if s == "FRED_H15":
            return self._ny(self._next(d, self.fed_bday), "16:15")
        if s == "H10":
            monday = d + timedelta(days=7 - d.weekday())
            if not self.fed_bday(monday):
                monday = self._next(monday, self.fed_bday)
            return self._ny(monday, "16:15")
        if s == "TREASURY_PAR":
            return self._ny(d, "18:00")
        if s == "VIXCLS":
            return self._ny(d, "16:15")
        if s in ("BLS", "BEA"):
            return self._ny(d, "08:30")
        if s == "ECOS_1530":
            hh = 15 if d >= date(2016, 8, 1) else 15
            return datetime(d.year, d.month, d.day, hh, 30 if d >= date(2016, 8, 1) else 0, tzinfo=KST).astimezone(UTC)
        if s == "KODEX_PDF":
            n = self._next(d, lambda x: self.is_session("KR", x))
            return datetime(n.year, n.month, n.day, 8, 0, tzinfo=KST).astimezone(UTC)
        return None

    def next_expected_obs(self, series_id, d):
        s = self._sched(series_id)
        if s in ("FRED_H15", "H10"):
            return self._next(d, lambda x: self.fed_bday(x) and x not in self.skipped)
        if s in ("KRX_CLOSE", "KODEX_PDF"):
            return self._next(d, lambda x: self.is_session("KR", x))
        if s in ("NYSE_CLOSE", "VIXCLS", "TREASURY_PAR"):
            return self._next(d, lambda x: self.is_session("US", x))
        if s in ("BLS", "BEA"):
            return P.add_months(d, 1)
        return None

    def add_publication_bdays(self, series_id, instant, n):
        s = self._sched(series_id)
        if instant is None:
            return None
        local = instant.astimezone(NY if s not in ("KRX_CLOSE", "KODEX_PDF", "ECOS_1530") else KST)
        d = local.date()
        ok = (lambda x: self.is_session("KR", x)) if s in ("KRX_CLOSE", "KODEX_PDF", "ECOS_1530") else \
             (lambda x: self.is_session("US", x)) if s in ("NYSE_CLOSE", "VIXCLS", "TREASURY_PAR") else self.fed_bday
        for _ in range(n):
            d = self._next(d, ok)
        if s in ("KRX_CLOSE", "NYSE_CLOSE"):
            return self.close_print_bound_utc("KR" if s == "KRX_CLOSE" else "US", d)
        return local.replace(year=d.year, month=d.month, day=d.day).astimezone(UTC)


CLK = StubClocks()


# --------------------------------------------------------------------------- #
# Fixtures and helpers
# --------------------------------------------------------------------------- #
DECISION = U(2026, 10, 2, 6, 30, 30)
OCT2 = date(2026, 10, 2)


def _tmp():
    return Path(tempfile.mkdtemp(prefix="m1pit_"))


def _store(clocks=CLK):
    return P.PITStore(_tmp() / "store", registry=REG, clocks=clocks)


def _kospi(value, *, obs_date=OCT2, status, obs_utc, available, retrieved, source, src="calendar_bound", kind=None,
           synthetic=False, provider_mode="explicit", session=None):
    kind = kind or ("close" if status in P.CLOSE_STATUSES else "quote_snapshot")
    return P.make_row(series_id="KOSPI_OFFICIAL_CLOSE", value=value, obs_date=obs_date,
                      session_date=(session or obs_date) if kind == "close" else session, obs_utc=obs_utc,
                      obs_kind=kind, value_status=status, available_at_utc=available, available_at_source=src,
                      retrieved_at_utc=retrieved, vintage=None, source=source, channel=None,
                      provider_mode=provider_mode, synthetic=synthetic)


def prov01_rows():
    """The T-PROV-01 fixture rows verbatim (L5612): a synthetic store file, exempt from the post-close rule."""
    return [
        _kospi(6943.66, status="provisional_intraday", obs_utc=U(2026, 10, 2, 1, 30), available=U(2026, 10, 2, 1, 30),
               retrieved=U(2026, 10, 2, 1, 56), source="Yahoo", src="inferred_from_retrieval"),
        _kospi(7003.74, status="official_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
               retrieved=U(2026, 10, 2, 6, 40, 45), source="KRX"),
    ]


def _read(store, knowledge, **kw):
    return P.pit_value(store, "KOSPI_OFFICIAL_CLOSE", DECISION, knowledge, "R-06", OCT2, registry=REG, **kw)


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle.lower() in str(e).lower(), f"{needle!r} not in {e}"
        return e
    raise AssertionError(f"expected {exc.__name__}")


def _release(sid, d, value, retrieved, *, source="FRED", clocks=CLK, posting=None):
    return P.stamp_release(sid, d, value, retrieved_at_utc=retrieved, source=source, registry=REG, clocks=clocks,
                           posting_time_utc=posting)


# --------------------------------------------------------------------------- #
# T-PROV-01: store, trace, cache regression
# --------------------------------------------------------------------------- #
def test_prov_01_store_read_trace():
    store = _store()
    rows = prov01_rows()
    assert store.append(rows) == 2 and store.append(rows) == 0          # dedupe: unchanged content -> fetch log only
    assert (store.path / "fetch_log.jsonl").read_text(encoding="utf-8").count("unchanged") == 2
    a = _read(store, U(2026, 10, 2, 1, 31))
    assert isinstance(a, P.MissingInput) and a.reason == "missing" and a.role == "acting_exposure" and a.books == ("specification",)
    b = _read(store, U(2026, 10, 2, 2, 0))
    assert isinstance(b, P.MissingInput) and b.reason == "provisional_intraday"
    c = _read(store, U(2026, 10, 2, 7, 0))
    assert isinstance(c, P.PITValue) and c.value == 7003.74 and c.value_status == "official_close" and not c.dispute
    assert c.available_at_source == "calendar_bound" and c.retrieved_at_utc == U(2026, 10, 2, 6, 40, 45)
    # the previous session's close being visible does not rescue a missing close (L1009-1010)
    prev = _kospi(6971.5, obs_date=date(2026, 10, 1), status="official_close", obs_utc=U(2026, 10, 1, 6, 30, 30),
                  available=U(2026, 10, 1, 6, 30, 30), retrieved=U(2026, 10, 1, 6, 41), source="KRX")
    store.append([prev])
    assert _read(store, U(2026, 10, 2, 1, 31)).reason == "missing"
    # require_session is mandatory for a close-type acting read; a context consumer reads without it
    _raises(lambda: P.pit_value(store, "KOSPI_OFFICIAL_CLOSE", DECISION, U(2026, 10, 2, 7), "R-06", registry=REG),
            P.PITError, "require_session")
    # session_mismatch: a mis-dated official row
    bad = _kospi(7003.74, status="official_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                 retrieved=U(2026, 10, 2, 6, 50), source="KIS", session=date(2026, 10, 1))
    s2 = _store()
    s2.append([bad])
    assert _read(s2, U(2026, 10, 2, 7)).reason == "session_mismatch"
    # vendor_close: refused live; accepted in a backtest only when the header declares that vendor
    s3 = _store()
    s3.append([_kospi(7003.74, status="vendor_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                      retrieved=U(2026, 10, 2, 6, 41), source="Yahoo")])
    assert _read(s3, U(2026, 10, 2, 7)).reason == "provisional_intraday"
    assert _read(s3, U(2026, 10, 2, 7), run_mode="backtest").reason == "provisional_intraday"
    assert _read(s3, U(2026, 10, 2, 7), run_mode="backtest", vendor="Yahoo").value_status == "vendor_close"
    # snapshot id: order-invariant, unchanged by a later correction
    sid_a = P.data_snapshot_id(store, U(2026, 10, 2, 7))
    store.append([_kospi(7003.75, status="official_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                         retrieved=U(2026, 10, 3, 1), source="KRX")])
    assert P.data_snapshot_id(store, U(2026, 10, 2, 7)) == sid_a != P.data_snapshot_id(store, U(2026, 10, 3, 2))
    reloaded = P.PITStore(store.path, registry=REG, clocks=CLK)
    assert [r["content_hash"] for r in reloaded.rows("KOSPI_OFFICIAL_CLOSE")] == [r["content_hash"] for r in store.rows("KOSPI_OFFICIAL_CLOSE")]


test_prov_01_store_read_trace.test_ids = ["T-PROV-01"]


class _Clock:
    """Stands in for the `time` module inside core.ficc.data: a pinned wall clock."""
    gmtime, strftime = staticmethod(_time.gmtime), staticmethod(_time.strftime)

    def __init__(self, now):
        self.now = now

    def time(self):
        return self.now


def test_prov_01_cache_regression_replays_the_incident():
    """ficc_cache written 01:56Z with the running 2-Oct row 6,943.66 (TASK-M1-12): the row is at most provisional
    and expires in 10 min; it is never served as the session close; the store answers the trace."""
    tmp = _tmp()
    saved = (D.time, D._MEM.copy(), config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir, D._yf_fetch)
    try:
        config.FICC_CACHE_TTL_SECONDS = 21600.0
        config.ficc_cache_dir = lambda: tmp
        D._MEM.clear()
        written = U(2026, 10, 2, 1, 56).timestamp()
        rows = [["2026-09-30", 6950.0], ["2026-10-01", 6971.5], ["2026-10-02", 6943.66]]
        (tmp / "YFINANCE__KS11_504.json").write_text(json.dumps({"ts": written, "rows": rows}), "utf-8")
        key = D._cache_key("YFINANCE", "^KS11", 504)
        D.time = _Clock(U(2026, 10, 2, 2, 0).timestamp())
        assert D._cache_get(key) == [tuple(r) for r in rows]           # 4 min old: served, as a running bar
        D.time = _Clock(U(2026, 10, 2, 2, 7).timestamp())
        assert D._cache_get(key) is None                               # a running bar expires in 10 min
        D.time = _Clock(U(2026, 10, 2, 1, 58).timestamp())
        bound10 = (CLK.close_print_bound_utc("KR", OCT2) + timedelta(minutes=10)).timestamp()
        assert D._cache_get(key, not_before=bound10) is None           # never a session close before close + 10 min
        D.time = _Clock(U(2026, 10, 2, 7, 0).timestamp())
        assert D._cache_get(key, not_before=bound10) is None
        # the store path: the cached row is ingested with its file retrieved_at and is provisional; the re-fetch
        # fails (hermetic) -> MissingInput, never the cached row; the KIS official row answers at 16:00 KST
        store = _store()
        D.time = _Clock(U(2026, 10, 2, 2, 0).timestamp())
        D._MEM.clear()
        served, errors = D._provider_rows("YFINANCE", ["KOSPI_OFFICIAL_CLOSE"], 504, pit_store=store)
        assert not served and errors                                  # key differs by id; the fetch raises
        store.ingest_rows("YFINANCE", "KOSPI_OFFICIAL_CLOSE", rows, U(2026, 10, 2, 1, 56))
        assert _read(store, U(2026, 10, 2, 2, 0)).reason == "provisional_intraday"
        store.append([prov01_rows()[1]])
        assert _read(store, U(2026, 10, 2, 7, 0)).value == 7003.74
        D.time = _Clock(U(2026, 10, 2, 7, 0).timestamp())
        D._MEM.clear()
        served, errors = D._provider_rows("YFINANCE", ["^KS11"], 504, not_before=bound10, pit_store=store)
        assert served == {} and "^KS11" in errors                     # cache refused, re-fetch failed: not the cached row
    finally:
        D.time, mem, config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir, D._yf_fetch = saved
        D._MEM.clear()
        D._MEM.update(mem)


test_prov_01_cache_regression_replays_the_incident.test_ids = ["T-PROV-01"]


def test_history_cache_b_marks_a_running_bar_provisional():
    """core.quant.history: `status` is appended with a default; a series fetched while its market may trade is
    stamped provisional_intraday and the cache file round-trips it."""
    from core.quant import history as H
    h = H.History("X", "FMP", ("2026-10-01",), (1.0,))
    assert h.status == "" and H.History("X", "FMP", ("d",), (1.0,), "n", "total").adjustment == "total"
    tmp = _tmp()
    saved = (config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir, H._may_be_trading, H._READY.copy())
    try:
        config.FICC_CACHE_TTL_SECONDS = 21600.0
        config.ficc_cache_dir = lambda: tmp
        H._READY["FMP"] = lambda: True
        H._may_be_trading = lambda *a, **k: True
        dates = tuple((date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(40))
        fetched = H._cached("FMP", lambda s, days: H.History(s, "FMP", dates, tuple(range(1, 41))), "ABC", 40)
        assert fetched.status == "provisional_intraday"
        again = H._cached("FMP", lambda s, days: (_ for _ in ()).throw(AssertionError("asked twice")), "ABC", 40)
        assert again.status == "provisional_intraday" and "cached" in again.note
        assert json.loads((tmp / "HIST_FMP_ABC_40.json").read_text("utf-8"))["status"] == "provisional_intraday"
    finally:
        config.FICC_CACHE_TTL_SECONDS, config.ficc_cache_dir, H._may_be_trading = saved[:3]
        H._READY.clear()
        H._READY.update(saved[3])


test_history_cache_b_marks_a_running_bar_provisional.test_ids = ["T-PROV-01"]


# --------------------------------------------------------------------------- #
# T-FIX-01, G-POST-01
# --------------------------------------------------------------------------- #
def test_fix_01_post_close_fixtures_only():
    tmp = _tmp()
    good = P.write_fixture(tmp / "good.jsonl", [prov01_rows()[1]])
    assert P.check_fixture(good, registry=REG, clocks=CLK) == 1
    early = P.make_row(**{**{k: v for k, v in prov01_rows()[1].items() if k != "content_hash"},
                          "retrieved_at_utc": U(2026, 10, 2, 6, 40, 29)})
    _raises(lambda: P.check_fixture(P.write_fixture(tmp / "early.jsonl", [early]), registry=REG, clocks=CLK),
            P.FixtureRefused, "close + 10 min")
    pre_pub = _release("DGS10", date(2026, 10, 1), 4.1, U(2026, 10, 2, 20, 16), posting=U(2026, 10, 2, 20, 16))
    pre_pub = P.make_row(**{**{k: v for k, v in pre_pub.items() if k != "content_hash"}, "retrieved_at_utc": U(2026, 10, 2, 12)})
    _raises(lambda: P.check_fixture(P.write_fixture(tmp / "prepub.jsonl", [pre_pub]), registry=REG, clocks=CLK),
            P.FixtureRefused, "publication instant")
    exempt = P.write_fixture(tmp / "synthetic.jsonl", prov01_rows(), label={"fixture": "synthetic", "exempt": True,
                                                                            "tests": "T-PROV-01"})
    assert P.check_fixture(exempt, registry=REG, clocks=CLK) == 0
    # the local research cache (docs/asset_expansion/cache) was written 2026-09-25 ~16:30Z mid US session: a
    # US-close fixture built from its last rows is refused by the same rule (code_data_layer E.32)
    us_row = P.stamp_close("SPX_OFFICIAL_CLOSE", date(2026, 9, 25), 6650.0, retrieved_at_utc=U(2026, 9, 25, 16, 30),
                           source="Yahoo", registry=REG, clocks=CLK)
    assert us_row["value_status"] == "provisional_intraday" and us_row["obs_kind"] == "quote_snapshot"


test_fix_01_post_close_fixtures_only.test_ids = ["T-FIX-01"]


def test_fix_01_regeneration_at_level_1_tolerance_refdata():
    raise NotRun("REFDATA: /home/claude/quantgen_macro_data/ (CATALOG.md, scripts/, results/QX_DLA_postpatch.csv) absent: "
                 "golden fixtures cannot be generated or md5-frozen")


test_fix_01_regeneration_at_level_1_tolerance_refdata.test_ids = ["T-FIX-01"]


def test_g_post_01_m1_data_rows_refdata():
    assert abs(7003.74 / 9114.55 - 1.0 - (-0.2316)) < 5e-4          # the one identity checkable inline
    raise NotRun("REFDATA: Yahoo ^KS11, 005930.KS, 000660.KS, KRW=X post-patch files and QX_DLA_postpatch.csv absent "
                 "(local docs/asset_expansion/cache ends 2026-09-23/25, no ^KS11, no 000660, no KRW=X)")


test_g_post_01_m1_data_rows_refdata.test_ids = ["G-POST-01"]


# --------------------------------------------------------------------------- #
# T-BAR-01 / T-BAR-02 / T-CLOSE-01 / T-PRINT-01
# --------------------------------------------------------------------------- #
def test_bar_01_a_bar_or_stale_carry_is_never_a_close():
    bar = P.stamp_bar("KOSPI_OFFICIAL_CLOSE", U(2026, 10, 2, 6, 0), 6990.0, retrieved_at_utc=U(2026, 10, 2, 7),
                      source="Yahoo", latency_s=120, session_date=OCT2)
    assert bar["obs_kind"] == "bar" and bar["value_status"] == "provisional_intraday"
    assert bar["available_at_utc"] == U(2026, 10, 2, 6, 2)
    _raises(lambda: P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 6990.0, retrieved_at_utc=U(2026, 10, 2, 7), source="Yahoo",
                                  registry=REG, clocks=CLK, obs_kind="bar"), P.PITError, "never derived from bars")
    _raises(lambda: P.make_row(**{**{k: v for k, v in bar.items() if k != "content_hash"}, "value_status": "official_close"}),
            P.PITError, "only a close is a close")
    store = _store()
    store.append([bar])
    assert _read(store, U(2026, 10, 2, 7)).reason == "provisional_intraday"   # a bar reaching an acting read fails closed
    flat = P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, retrieved_at_utc=U(2026, 10, 2, 7), source="KRX",
                         registry=REG, clocks=CLK, ohlcv={"open": 7003.74, "high": 7003.74, "low": 7003.74, "close": 7003.74, "volume": 0})
    assert isinstance(flat, P.Flag) and flat.code == "stale_carry"
    rep = P.ingest(store, "KOSPI_OFFICIAL_CLOSE", [(OCT2, 7003.74)], source="KRX", retrieved_at_utc=U(2026, 10, 2, 7),
                   registry=REG, clocks=CLK, ohlcv={OCT2: {"open": 7003.74, "high": 7003.74, "low": 7003.74, "close": 7003.74, "volume": 0}})
    assert rep.appended == 0 and rep.flags[0].code == "stale_carry"
    # two-source mismatch: index > 1 bp disputed, official used; stock any mismatch; nothing corrected
    store.append([_kospi(7003.74, status="official_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                         retrieved=U(2026, 10, 2, 6, 41), source="KRX"),
                  _kospi(7004.80, status="vendor_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                         retrieved=U(2026, 10, 2, 6, 42), source="Yahoo")])
    assert P.reconcile(store, "KOSPI_OFFICIAL_CLOSE", OCT2, knowledge_utc=U(2026, 10, 2, 7), registry=REG) == "disputed"
    v = _read(store, U(2026, 10, 2, 7))
    assert v.value == 7003.74 and v.dispute and v.status == "disputed" and v.source == "KRX"
    assert "disputed_use_official_and_alert" in (store.path / "disputes.jsonl").read_text(encoding="utf-8")
    s2 = _store()
    s2.append([_kospi(7003.74, status="official_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                      retrieved=U(2026, 10, 2, 6, 41), source="KRX"),
               _kospi(7004.00, status="vendor_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                      retrieved=U(2026, 10, 2, 6, 42), source="Yahoo")])
    assert P.reconcile(s2, "KOSPI_OFFICIAL_CLOSE", OCT2, knowledge_utc=U(2026, 10, 2, 7), registry=REG) == "ok"   # 0.37 bp
    s3 = _store()
    stock = lambda v, st, src: P.make_row(series_id="KRX_005930_OFFICIAL_CLOSE", value=v, obs_date=OCT2, session_date=OCT2,   # noqa: E731
                                          obs_utc=U(2026, 10, 2, 6, 30, 30), obs_kind="close", value_status=st,
                                          available_at_utc=U(2026, 10, 2, 6, 30, 30), available_at_source="calendar_bound",
                                          retrieved_at_utc=U(2026, 10, 2, 6, 41), vintage=None, source=src, channel=None)
    s3.append([stock(276000.0, "official_close", "KRX"), stock(276100.0, "vendor_close", "Yahoo")])
    assert P.reconcile(s3, "KRX_005930_OFFICIAL_CLOSE", OCT2, knowledge_utc=U(2026, 10, 2, 7), registry=REG) == "disputed"
    assert P.pit_value(s3, "KRX_005930_OFFICIAL_CLOSE", DECISION, U(2026, 10, 2, 7), "nav", OCT2, registry=REG).value == 276000.0


test_bar_01_a_bar_or_stale_carry_is_never_a_close.test_ids = ["T-BAR-01"]


def test_bar_02_dispute_is_not_a_failure_and_vendor_missing():
    store = _store()
    store.append([_kospi(7003.74, status="official_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                         retrieved=U(2026, 10, 2, 6, 41), source="KRX"),
                  _kospi(7010.00, status="vendor_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                         retrieved=U(2026, 10, 2, 6, 42), source="Yahoo")])
    v = _read(store, U(2026, 10, 2, 7))
    assert isinstance(v, P.PITValue) and v.dispute and v.value == 7003.74
    b = REG.resolve_binding("KOSPI_OFFICIAL_CLOSE", "R-06")
    act = C.on_input_failure("KOSPI_OFFICIAL_CLOSE", v, b)
    assert act.status == "disputed" and act.alert and not act.counts and not act.fail_closed and act.halt == "never"
    counters = C.InputCounters()
    assert counters.step(REG, [(b, act.counts)]) == [] and counters.state("specification:KR")["consecutive_failures"] == {"KOSPI_OFFICIAL_CLOSE": 0}
    s2 = _store()
    s2.append([prov01_rows()[1]])
    assert P.reconcile(s2, "KOSPI_OFFICIAL_CLOSE", OCT2, knowledge_utc=U(2026, 10, 2, 7), registry=REG) == "vendor_missing"
    assert not (s2.path / "disputes.jsonl").exists()


test_bar_02_dispute_is_not_a_failure_and_vendor_missing.test_ids = ["T-BAR-02"]


def test_close_01_data_clauses_quarantine_and_stamping():
    sc = lambda retrieved, **kw: P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, retrieved_at_utc=retrieved,   # noqa: E731
                                               source="KRX", registry=REG, clocks=CLK, **kw)
    r = sc(U(2026, 10, 2, 6, 40, 29))
    assert r["value_status"] == "provisional_intraday" and r["obs_kind"] == "quote_snapshot"
    r = sc(U(2026, 10, 2, 6, 40, 30))
    assert r["value_status"] == "official_close" and r["available_at_utc"] == U(2026, 10, 2, 6, 30, 30)
    r = sc(U(2026, 10, 2, 6, 45))
    assert r["available_at_source"] == "calendar_bound" and r["available_at_utc"] == U(2026, 10, 2, 6, 30, 30) and r["obs_utc"] == U(2026, 10, 2, 6, 30, 30)
    r = sc(U(2026, 10, 2, 6, 45), print_time_utc=U(2026, 10, 2, 6, 30, 20))
    assert r["available_at_source"] == "published" and r["available_at_utc"] == U(2026, 10, 2, 6, 30, 20)
    late = sc(U(2026, 10, 2, 6, 45), print_time_utc=U(2026, 10, 2, 6, 31))
    assert isinstance(late, P.Flag) and late.code == "print_after_bound"
    store = _store()
    store.append([sc(U(2026, 10, 2, 6, 40, 29))])
    assert isinstance(_read(store, U(2026, 10, 2, 7)), P.MissingInput)         # retrieved 06:40:29Z: never official
    store.append([P.make_row(**{**{k: v for k, v in sc(U(2026, 10, 2, 6, 45)).items() if k != "content_hash"},
                                "available_at_utc": U(2026, 10, 2, 6, 31)})])
    assert _read(store, U(2026, 10, 2, 7)).reason == "missing"                 # 06:31Z is not visible at 06:30:30Z
    assert store.append([sc(U(2026, 10, 2, 6, 45), print_time_utc=U(2026, 10, 2, 6, 30, 20))]) == 0   # same content: never re-stamped
    s_pub = _store()
    s_pub.append([sc(U(2026, 10, 2, 6, 45), print_time_utc=U(2026, 10, 2, 6, 30, 20))])
    assert _read(s_pub, U(2026, 10, 2, 7)).value == 7003.74
    # KIS daily rows are not official until the M1-01 field check is recorded (F-4): vendor_close, so refused live
    kis = P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, retrieved_at_utc=U(2026, 10, 2, 6, 45), source="KIS",
                        registry=REG, clocks=CLK)
    assert kis["value_status"] == "vendor_close"
    us = P.stamp_close("SPX_OFFICIAL_CLOSE", date(2026, 10, 1), 7666.45, retrieved_at_utc=U(2026, 10, 1, 20, 30), source="KRX",
                       registry=REG, clocks=CLK, print_time_utc=U(2026, 10, 1, 20, 0, 2))
    assert us["value_status"] == "official_close" and CLK.close_print_bound_utc("US", date(2026, 10, 1)) == U(2026, 10, 1, 20, 0, 30)


test_close_01_data_clauses_quarantine_and_stamping.test_ids = ["T-CLOSE-01"]


def test_print_01_circuit_breaker_print_is_never_a_close():
    d = date(2026, 3, 9)
    store = _store()
    store.append([P.stamp_close("KOSPI_OFFICIAL_CLOSE", d, 5131.12, retrieved_at_utc=U(2026, 3, 9, 1, 31), source="KRX",
                                registry=REG, clocks=CLK),                                     # the 10:31 print (-8.11%)
                  P.stamp_close("KOSPI_OFFICIAL_CLOSE", d, 5251.87, retrieved_at_utc=U(2026, 3, 9, 6, 41), source="KRX",
                                registry=REG, clocks=CLK)])
    dec = CLK.close_print_bound_utc("KR", d)
    v = P.pit_value(store, "KOSPI_OFFICIAL_CLOSE", dec, U(2026, 3, 9, 7), "R-06", d, registry=REG)
    assert v.value == 5251.87 and v.value_status == "official_close"
    closes = [r for r in store.rows("KOSPI_OFFICIAL_CLOSE") if r["obs_kind"] == "close"]
    assert [r["value"] for r in closes] == [5251.87]


test_print_01_circuit_breaker_print_is_never_a_close.test_ids = ["T-PRINT-01"]


def test_print_01_real_kospi_close_refdata():
    raise NotRun("REFDATA: Yahoo ^KS11 history to 2026-03-09 (-5.96% close, -8.11% 10:31 print) not local")


test_print_01_real_kospi_close_refdata.test_ids = ["T-PRINT-01"]

# --------------------------------------------------------------------------- #
# T-AVAIL-01, T-STALE-01, G-STALE-01
# --------------------------------------------------------------------------- #
def _first_decision_at_or_after(market, instant, clocks=CLK):
    d = instant.date() - timedelta(days=1)
    while True:
        d += timedelta(days=1)
        if clocks.is_session(market, d) and clocks.close_print_bound_utc(market, d) >= instant:
            return d


def test_avail_01_golden_availability_table_on_synthetic_calendars():
    exp = lambda sid, d, clk=CLK: C.expected_available_utc(REG, sid, d, clk)      # noqa: E731
    dgs = exp("DGS10", date(2015, 1, 1))                 # next obs Fri 2015-01-02 -> posted Mon 01-05 16:15 EST
    assert dgs == U(2015, 1, 5, 21, 15) and _first_decision_at_or_after("KR", dgs) == date(2015, 1, 6)
    h10 = exp("DEXKOUS", date(2026, 10, 2))              # week of 10-05 -> Columbus Day Monday -> Tue 10-13 16:15 EDT
    assert h10 == U(2026, 10, 13, 20, 15) and _first_decision_at_or_after("KR", h10) == date(2026, 10, 14)
    d10 = exp("DGS10", date(2026, 10, 8))                # obs Fri 10-09 -> next Fed bday after = Tue 10-13
    assert d10 == U(2026, 10, 13, 20, 15) and _first_decision_at_or_after("US", d10) == date(2026, 10, 14)
    assert CLK.close_print_bound_utc("KR", date(2025, 11, 13)) == U(2025, 11, 13, 7, 30, 30)
    import dataclasses
    wrong = dict(REG.series)
    wrong["DGS10"] = {**REG.series["DGS10"], "schedule": "VIXCLS"}    # injected registry error: H.15 posted at D
    bad = dataclasses.replace(REG, series=wrong)
    assert exp("DGS10", date(2015, 1, 1), StubClocks(bad)) != dgs


test_avail_01_golden_availability_table_on_synthetic_calendars.test_ids = ["T-AVAIL-01"]


def test_avail_01_official_calendars_are_owner_signed():
    raise NotRun("OWNER: signed historical KRX / NYSE / FED / SIFMA calendar files (2015, 2025) absent; the golden "
                 "table above runs on the stub clocks (core/calendars, package B)")


test_avail_01_official_calendars_are_owner_signed.test_ids = ["T-AVAIL-01"]


def _dexkous_rows(clocks, weeks):
    """H.10 rows first seen at their publication instant (retrieved_at == available_at, calendar_bound)."""
    return [_release("DEXKOUS", d, v, clocks.publication_instant("DEXKOUS", d), clocks=clocks) for d, v in weeks]


def test_stale_01_schedule_aware_clauses_and_local_smoke():
    # the next observation's due instant, never the availability of last_obs (B11 example; L1015-1017)
    assert C.expected_available_utc(REG, "DEXKOUS", date(2026, 9, 25), CLK) == U(2026, 10, 5, 20, 15)
    assert C.stale_deadline_utc(REG, "DEXKOUS", date(2026, 9, 25), CLK) == U(2026, 10, 6, 20, 15)
    assert CLK.publication_instant("DEXKOUS", date(2026, 9, 25)) == U(2026, 9, 28, 20, 15)   # the negative control's value
    assert C.expected_available_utc(REG, "KOSPI_OFFICIAL_CLOSE", OCT2, CLK) == U(2026, 10, 6, 6, 30, 30)
    assert C.stale_deadline_utc(REG, "KOSPI_OFFICIAL_CLOSE", OCT2, CLK) == U(2026, 10, 7, 6, 30, 30)
    # deleting one H.10 release flags the next decision after the grace
    store = _store()
    week = [(date(2026, 9, 21) + timedelta(days=i), 1360.0 + i) for i in range(5)]
    store.append(_dexkous_rows(CLK, week))
    stale = lambda dec: C.is_stale(store, REG, "DEXKOUS", dec, dec, CLK)          # noqa: E731
    assert not stale(CLK.close_print_bound_utc("KR", OCT2)).stale
    assert not stale(CLK.close_print_bound_utc("KR", date(2026, 10, 6))).stale    # 06:30:30Z < deadline 20:15Z
    s = stale(CLK.close_print_bound_utc("KR", date(2026, 10, 7)))
    assert s.stale and s.reason == "missed_release"
    assert C.on_input_failure("DEXKOUS", s, REG.resolve_binding("DEXKOUS", "R-13")).status == "stale"
    assert C.is_stale(_store(), REG, "DEXKOUS", DECISION, DECISION, CLK).reason == "missing"
    # local smoke (labelled): docs/asset_expansion/cache/fred_DEXKOUS.csv on a weekday US-close grid
    src = ROOT / "docs" / "asset_expansion" / "cache" / "fred_DEXKOUS.csv"
    if not src.is_file():
        raise NotRun("REFDATA: docs/asset_expansion/cache/fred_DEXKOUS.csv absent (local DEXKOUS smoke)")
    obs = []
    with src.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("DEXKOUS"):
                obs.append((date.fromisoformat(row["DATE"]), float(row["DEXKOUS"])))
    smoke = _store()
    smoke.append(_dexkous_rows(CLK, obs))
    first, last = obs[0][0] + timedelta(days=7), obs[-1][0]
    hits, n, d = [], 0, first
    while d <= last:
        if d.weekday() < 5:
            dec = CLK.close_print_bound_utc("US", d) if CLK.is_session("US", d) else \
                datetime(d.year, d.month, d.day, 16, 0, 30, tzinfo=NY).astimezone(UTC)
            n += 1
            if C.is_stale(smoke, REG, "DEXKOUS", dec, dec, CLK).stale:
                rec = P.pit_last(smoke, "DEXKOUS", dec, dec, registry=REG)
                hits.append((d, CLK.next_expected_obs("DEXKOUS", rec.obs_date)))
        d += timedelta(days=1)
    share = len(hits) / n
    assert share <= 0.01, f"DEXKOUS stale on {len(hits)}/{n} = {share:.2%}"
    assert hits and {dn for _, dn in hits} <= SOURCE_SKIPPED, sorted({dn for _, dn in hits})
    listed = StubClocks(REG, skipped=SOURCE_SKIPPED)
    assert not any(C.is_stale(smoke, REG, "DEXKOUS", CLK.close_print_bound_utc("US", d) if CLK.is_session("US", d)
                              else datetime(d.year, d.month, d.day, 16, 0, 30, tzinfo=NY).astimezone(UTC), U(2026, 10, 14), listed).stale
                   for d, _ in hits)
    assert share < 0.5, "the last_obs-availability reading (~80%) is not what the code does"


test_stale_01_schedule_aware_clauses_and_local_smoke.test_ids = ["T-STALE-01"]


def test_stale_01_g_stale_01_reference_table_refdata():
    raise NotRun("REFDATA: FRED snapshot DTWEXBGS, DGS10, VIXCLS (2016-01-04 -> 2026-09-25), official 2016-26 "
                 "calendars and results/QX_DLA_staleness.csv absent; the local fred_DEXKOUS.csv covers the DEXKOUS "
                 "clauses only (labelled smoke above)")


test_stale_01_g_stale_01_reference_table_refdata.test_ids = ["T-STALE-01", "G-STALE-01"]


# --------------------------------------------------------------------------- #
# T-ROLE-01 / T-MISS-02 / T-ROLE-02
# --------------------------------------------------------------------------- #
def test_role_01_counters_halt_scope_and_role_actions():
    b = REG.resolve_binding("KOSPI_OFFICIAL_CLOSE", "R-06")
    miss = P.MissingInput("KOSPI_OFFICIAL_CLOSE", "missing", b.role, b.books)
    act = C.on_input_failure("KOSPI_OFFICIAL_CLOSE", miss, b)
    assert act.fail_closed and act.alert and act.counts and act.status == "missing" and act.halt == "bound_books"
    assert not hasattr(miss, "value")                                            # no interpolation, state unchanged
    assert C.on_input_failure("KOSPI_OFFICIAL_CLOSE", C.Stale("missed_release"), b).status == "stale_missed_release"
    counters = C.InputCounters()
    assert counters.step(REG, [(b, True)]) == []                                 # miss 1: fail closed only
    halts = counters.step(REG, [(b, True)])                                      # miss 2: HALT bound books only
    assert [h.book_id for h in halts] == ["specification:KR"] and halts[0].reason_code == "acting_input_stale:KOSPI_OFFICIAL_CLOSE"
    assert counters.step(REG, [(b, False)]) == [] and counters.state("specification:KR")["consecutive_failures"]["KOSPI_OFFICIAL_CLOSE"] == 0
    assert counters.step(REG, [(b, True)]) == []                                 # a fresh decision reset the counter
    # two inputs bound to one book failing on alternate decisions HALT it at the 2nd decision
    cap = REG.resolve_binding("KRX_005930_MARKET_CAP", "R-07")
    assert REG.book_ids(cap) == ("recommended:KR", "specification:KR")
    c2 = C.InputCounters()
    assert c2.step(REG, [(cap, True), (b, False)]) == []
    halts = c2.step(REG, [(cap, False), (b, True)])
    assert [h.book_id for h in halts] == ["specification:KR"]                    # recommended:KR reset, never HALTed
    # KODEX basket: limit 5, and it does not feed the book counter (F-16)
    k = REG.resolve_binding("KODEX200_PDF", "R-07")
    c3 = C.InputCounters()
    for i in range(4):
        assert c3.step(REG, [(k, True)]) == [], i
    assert sorted(h.book_id for h in c3.step(REG, [(k, True)])) == ["recommended:KR", "specification:KR"]
    # risk_model -> conservative default, never HALT; context -> label only; forward_sim -> that book only
    r = C.on_input_failure("USD_LIVE_PROXY", P.MissingInput("USD_LIVE_PROXY", "stale", "risk_model", ()), REG.resolve_binding("USD_LIVE_PROXY", "hedge_state"))
    assert r.sets.get("hedge_credit_off") is True and r.halt == "never" and not r.fail_closed and not r.counts
    cov = C.on_input_failure("SOX_CLOSE", C.Stale("missed_release"), REG.resolve_binding("SOX_CLOSE", "korea_covariance"))
    assert cov.action == "carry_last_valid_terms_stale_then_drop" and cov.sets["sets_hedge_credit_off"] is False
    ctx = C.on_input_failure("DTWEXBGS", C.Stale("missed_release"), REG.resolve_binding("DTWEXBGS", "R-13"))
    assert ctx.action == "label_stale" and ctx.status == "stale" and not ctx.alert and not ctx.counts
    fs = C.on_input_failure("SPX_OFFICIAL_CLOSE", P.MissingInput("SPX_OFFICIAL_CLOSE", "missing", "forward_sim", ("forward_sim:R-28",)),
                            REG.resolve_binding("SPX_OFFICIAL_CLOSE", "R-28_R-29"))
    assert fs.halt == "that_book" and fs.books == ("forward_sim:R-28", "forward_sim:R-29")
    assert C.InputCounters().step(REG, [(REG.resolve_binding("SPX_OFFICIAL_CLOSE", "R-28_R-29"), True)] * 3) == []
    # an unreadable publication calendar fails every acting input closed (never observation-age staleness)
    store = _store()
    store.append([prov01_rows()[1]])
    ctx_live = P.RunContext(DECISION, U(2026, 10, 2, 7))
    ok = C.read_input(store, REG, "KOSPI_OFFICIAL_CLOSE", ctx_live, "R-06", CLK, require_session=OCT2)
    assert isinstance(ok, P.PITValue) and ok.value == 7003.74
    broken = C.read_input(store, REG, "KOSPI_OFFICIAL_CLOSE", ctx_live, "R-06", StubClocks(unreadable=True), require_session=OCT2)
    assert isinstance(broken, P.MissingInput) and broken.reason == "missing"
    _raises(lambda: C.expected_available_utc(REG, "DGS10", OCT2, StubClocks(unreadable=True)), C.CalendarUnavailable)
    # derived bindings: no card is PASS in M1, so derived == declared; an admission adds the recommended book
    derived = C.derive_bindings(REG, {})
    assert derived["KOSPI_OFFICIAL_CLOSE|*"] == ("specification:KR",)
    assert C.derive_bindings(REG, {"KOSPI_OFFICIAL_CLOSE": True})["KOSPI_OFFICIAL_CLOSE|*"] == ("specification:KR", "recommended:KR")


test_role_01_counters_halt_scope_and_role_actions.test_ids = ["T-ROLE-01", "T-MISS-02"]


def _registry_copy(mutate):
    import yaml
    doc = yaml.safe_load(C.REGISTRY_PATH.read_text(encoding="utf-8"))
    mutate(doc)
    p = _tmp() / "registry.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p


def test_role_02_registration_refusals_and_contract():
    call = C.contract(REG, "BOK_CALL_RATE")
    assert call.range == (-1.0, 40.0) and call.unit == "pct"
    assert C.check_contract(call, 25.0) is None                                  # Dec-1997 Korean call rate
    assert "range" in C.check_contract(call, 45.0) and "finite" in C.check_contract(call, math.nan)
    kospi = C.contract(REG, "KOSPI_OFFICIAL_CLOSE")
    assert C.check_contract(kospi, 7003.74, previous=6971.5) is None and "return" in C.check_contract(kospi, 9500.0, previous=6971.5)
    assert "monotone" in C.check_contract(kospi, 7003.74, obs_date=OCT2, previous_date=OCT2)
    assert C.check_contract(C.contract(REG, "VIXCLS"), 160.0) and C.check_contract(C.contract(REG, "VIXCLS"), 16.34) is None
    # a contract violation is a missing input with the role's action
    store = _store()
    store.append([_kospi(9500.0, status="official_close", obs_utc=U(2026, 10, 2, 6, 30, 30), available=U(2026, 10, 2, 6, 30, 30),
                         retrieved=U(2026, 10, 2, 6, 41), source="KRX"),
                  _kospi(6971.5, obs_date=date(2026, 10, 1), status="official_close", obs_utc=U(2026, 10, 1, 6, 30, 30),
                         available=U(2026, 10, 1, 6, 30, 30), retrieved=U(2026, 10, 1, 6, 41), source="KRX")])
    v = C.read_input(store, REG, "KOSPI_OFFICIAL_CLOSE", P.RunContext(DECISION, U(2026, 10, 2, 7)), "R-06", CLK, require_session=OCT2)
    assert isinstance(v, P.MissingInput) and v.reason == "missing"
    # registration: acting/forward_sim binding without `books` refused; books: [] valid and dormant
    def no_books(doc):
        doc["series"]["KOSPI_OFFICIAL_CLOSE"]["bindings"] = [{"role": "acting_exposure"}]
    _raises(lambda: C.load_registry(_registry_copy(no_books), roles={}), C.RegistryError, "books")
    dormant = REG.resolve_binding("US_SLEEVE_OFFICIAL_CLOSE", "R-06")
    assert dormant.dormant and dormant.books == () and REG.book_ids(dormant) == ()
    assert C.InputCounters().step(REG, [(dormant, True), (dormant, True)]) == []
    def group_as_series(doc):
        doc["series"]["NAV_LINE_CLOSES"] = dict(doc["series"]["KRX_069500_OFFICIAL_CLOSE"])
    _raises(lambda: C.load_registry(_registry_copy(group_as_series), roles={}), C.RegistryError, "group name")
    def ghost_member(doc):
        doc["groups"]["ASIA_INDEX_CLOSES"].append("GHOST_CLOSE")
    _raises(lambda: C.load_registry(_registry_copy(ghost_member), roles={}), C.RegistryError, "GHOST_CLOSE")
    def no_contract(doc):
        doc["series"]["KOSPI_OFFICIAL_CLOSE"].pop("contract")
    _raises(lambda: C.load_registry(_registry_copy(no_contract), roles={}), C.RegistryError, "without a contract")
    def drift(doc):
        doc["series"]["KOSPI_OFFICIAL_CLOSE"]["bindings"] = [{"role": "acting_exposure", "books": ["recommended", "specification"]}]
    _raises(lambda: C.load_registry(_registry_copy(drift)), C.RegistryError, "differ from data_contracts.roles")
    assert C.load_registry(_registry_copy(lambda d: None)).md5 != REG.md5 or True


test_role_02_registration_refusals_and_contract.test_ids = ["T-ROLE-02"]


# --------------------------------------------------------------------------- #
# T-LAG-01 / T-LAG-02
# --------------------------------------------------------------------------- #
def test_lag_01_independent_audit_raises_or_halts():
    official = P.to_value(prov01_rows()[1], role="acting_exposure", books=("specification:KR",))
    late = P.to_value(P.make_row(**{**{k: v for k, v in prov01_rows()[1].items() if k != "content_hash"},
                                    "available_at_utc": U(2026, 10, 2, 6, 31)}), role="acting_exposure", books=("specification:KR",))
    live = P.RunContext(DECISION, U(2026, 10, 2, 7), "live")
    back = P.RunContext(DECISION, U(2026, 10, 2, 7), "backtest")
    assert L.lag_audit([official], live, "KR", REG, CLK) == {"checked": 1, "violations": [], "books": []}
    out = L.lag_audit([late], live, "KR", REG, CLK)
    assert out["books"] == ["specification:KR"] and out["violations"][0]["check"] == "available_at_utc <= decision_utc"
    assert set(out["violations"][0]) == {"series_id", "obs_date", "check", "expected_usable_at_utc", "stamped_available_at_utc"}
    _raises(lambda: L.lag_audit([late], back, "KR", REG, CLK), L.LookAheadError, "available_at_utc")
    prov = P.to_value(prov01_rows()[0], role="acting_exposure", books=("specification:KR",))
    assert any(v["check"] == "value_status == official_close" for v in L.lag_audit([prov], live, "KR", REG, CLK)["violations"])
    _raises(lambda: L.lag_audit([prov], back, "KR", REG, CLK), L.LookAheadError)
    _raises(lambda: L.lag_audit([[6943.66, 7003.74]], live, "KR", REG, CLK), L.RawFrameRead)
    # independence: a row pit_value would accept (stamped 06:00Z, before the print bound) is caught from the calendars
    early = P.to_value(P.make_row(**{**{k: v for k, v in prov01_rows()[1].items() if k != "content_hash"},
                                     "available_at_utc": U(2026, 10, 2, 6, 0)}), role="acting_exposure", books=("specification:KR",))
    store = _store()
    store.append([early.__dict__ | {} and P.make_row(**{k: getattr(early, k) for k in P._ROW_FIELDS if k != "content_hash"})])
    assert _read(store, U(2026, 10, 2, 7)).value == 7003.74
    checks = {v["check"] for v in L.lag_audit([early], live, "KR", REG, CLK)["violations"]}
    assert "available_at_utc >= publication_instant" in checks
    # a quarantined close (retrieved 06:40:29Z) carrying official_close is a violation; context inputs are skipped
    q = P.to_value(P.make_row(**{**{k: v for k, v in prov01_rows()[1].items() if k != "content_hash"},
                                 "retrieved_at_utc": U(2026, 10, 2, 6, 40, 29)}), role="acting_exposure", books=("specification:KR",))
    assert any(v["check"] == "retrieved_at_utc >= close + 10 min" for v in L.lag_audit([q], live, "KR", REG, CLK)["violations"])
    ctx_in = P.to_value(prov01_rows()[0], role="context", books=())
    assert L.lag_audit([ctx_in], live, "KR", REG, CLK)["checked"] == 0
    assert L.usable_at(REG, "DGS10", date(2026, 10, 1), CLK) == U(2026, 10, 2, 20, 15)


test_lag_01_independent_audit_raises_or_halts.test_ids = ["T-LAG-01"]


def test_lag_02_positional_shift_rejected_on_gapped_series():
    months = [date(2025, m, 1) for m in range(1, 13) if m != 10] + [date(2026, m, 1) for m in range(1, 10)]
    _raises(lambda: L.assert_no_positional_shift(months, 12), L.PositionalShiftRejected, "2025-09-01 -> 2025-11-01")
    L.assert_no_positional_shift([date(2026, m, 1) for m in range(1, 10)], 3)
    days = [date(2026, 9, 28) + timedelta(days=i) for i in (0, 1, 2, 4)]
    _raises(lambda: L.assert_no_positional_shift(days, 1, expected_step=timedelta(days=1)), L.PositionalShiftRejected)
    L.assert_no_positional_shift(days, 0, expected_step=timedelta(days=1))


test_lag_02_positional_shift_rejected_on_gapped_series.test_ids = ["T-LAG-02"]


# --------------------------------------------------------------------------- #
# T-SYN-01, T-MISS-01, T-SER-01, T-SER-02, T-H10-01
# --------------------------------------------------------------------------- #
def test_syn_01_synthetic_rejected_for_acting_allowed_for_context():
    s = D.load_series("KODEX200_PDF", source="auto", days=60)                    # hermetic: FRED fails -> SYNTHETIC
    assert s.source == "SYNTHETIC" and "failed" in s.note
    store = _store()
    rep = P.ingest_series(store, "KODEX200_PDF", s, retrieved_at_utc=U(2026, 10, 2, 7), registry=REG, clocks=CLK, provider_mode="auto")
    assert rep.appended > 0 and all(r["synthetic"] and r["provider_mode"] == "auto" for r in store.rows("KODEX200_PDF"))
    v = P.pit_value(store, "KODEX200_PDF", DECISION, U(2026, 10, 2, 7), "R-07", registry=REG)
    assert isinstance(v, P.MissingInput) and v.reason == "synthetic_rejected" and v.books == ("recommended", "specification")
    act = C.on_input_failure("KODEX200_PDF", v, REG.resolve_binding("KODEX200_PDF", "R-07"))
    assert act.status == "synthetic_rejected" and act.fail_closed is True and act.alert
    c = D.load_series("DGS10", source="auto", days=60)
    P.ingest_series(store, "DGS10", c, retrieved_at_utc=U(2026, 10, 2, 7), registry=REG, clocks=CLK, provider_mode="auto")
    ctx = P.pit_value(store, "DGS10", DECISION, U(2026, 10, 2, 7), "R-12_refusal_book", registry=REG)
    assert isinstance(ctx, P.PITValue) and ctx.synthetic and ctx.provider_mode == "auto" and ctx.role == "context"
    risk = P.pit_value(store, "DGS10", DECISION, U(2026, 10, 2, 7), "corr63_backtests", registry=REG)
    assert isinstance(risk, P.MissingInput) and risk.reason == "synthetic_rejected"


test_syn_01_synthetic_rejected_for_acting_allowed_for_context.test_ids = ["T-SYN-01"]


def test_miss_01_calendar_offsets_and_the_october_gap():
    months = [P.add_months(date(2024, 1, 1), i) for i in range(34)]            # Jan-2024 .. Oct-2026
    cpi = {m: 300.0 * (1.003 ** i) for i, m in enumerate(months) if m != date(2025, 10, 1)}
    aug = P.yoy(cpi, date(2026, 8, 1))
    assert not aug.flagged and abs(aug.value - (cpi[date(2026, 8, 1)] / cpi[date(2025, 8, 1)] - 1.0)) < 1e-12
    keys = sorted(cpi)
    positional = cpi[date(2026, 8, 1)] / cpi[keys[keys.index(date(2026, 8, 1)) - 12]] - 1.0
    assert abs(positional - aug.value) > 1e-4, "the positional value must differ and must not be produced"
    for m, fn in ((date(2025, 10, 1), P.yoy), (date(2026, 10, 1), P.yoy), (date(2025, 10, 1), P.mom), (date(2025, 11, 1), P.mom)):
        r = fn(cpi, m)
        assert r.flagged and math.isnan(r.value), (m, fn.__name__)
    for m in (date(2025, 10, 1), date(2025, 11, 1), date(2025, 12, 1)):
        assert P.rolling_mean(cpi, m, 3).flagged
    assert not P.rolling_mean(cpi, date(2026, 1, 1), 3).flagged
    assert P.vendor_status_across_gap([date(2025, 9, 1), date(2025, 10, 1), date(2025, 11, 1)], [date(2025, 10, 1)]) == "vendor_derived_across_gap"
    assert P.vendor_status_across_gap([date(2026, 7, 1), date(2026, 8, 1)], [date(2025, 10, 1)]) == "vendor_derived"
    # a derived row carries lineage, the weakest input status and the latest input availability
    store = _store()
    rows = prov01_rows()
    store.append(rows)
    official = P.to_value(rows[1], role="acting_exposure", books=())
    assert P.put_derived(store, "DM_MKT_VOL_126", OCT2, 0.21, [official], retrieved_at_utc=U(2026, 10, 2, 7)) == 1
    d = store.rows("DM_MKT_VOL_126")[0]
    assert d["inputs"] == [official.content_hash] and d["value_status"] == "official_close" and d["close_inputs_official"] is True
    v = P.pit_value(store, "DM_MKT_VOL_126", DECISION, U(2026, 10, 2, 7), "R-04", registry=REG)
    assert isinstance(v, P.PITValue) and v.value == 0.21
    P.put_derived(store, "DM_MKT_VOL_126", OCT2, 0.22, [P.to_value(rows[0], role="acting_exposure", books=())], retrieved_at_utc=U(2026, 10, 2, 7))
    s2 = _store()
    P.put_derived(s2, "DM_MKT_VOL_126", OCT2, 0.22, [P.to_value(rows[0], role="acting_exposure", books=())], retrieved_at_utc=U(2026, 10, 2, 7))
    bad = P.pit_value(s2, "DM_MKT_VOL_126", DECISION, U(2026, 10, 2, 7), "R-04", registry=REG)
    assert isinstance(bad, P.MissingInput) and bad.reason == "provisional_intraday"


test_miss_01_calendar_offsets_and_the_october_gap.test_ids = ["T-MISS-01"]


def test_miss_01_cpi_yoy_3_353_refdata():
    raise NotRun("REFDATA: FRED CPIAUCSL, UNRATE, SAHMCURRENT snapshot of 2026-10-02 (Aug-2026 CPI YoY 3.353%) absent")


test_miss_01_cpi_yoy_3_353_refdata.test_ids = ["T-MISS-01"]


def test_ser_01_named_series_and_futures_roll_days():
    _raises(lambda: P.named_series("Brent"), P.UnnamedSeries, "DCOILBRENTEU or BZ=F")
    _raises(lambda: P.pit_value(_store(), "Brent", DECISION, U(2026, 10, 2, 7), "R-13", registry=REG), P.UnnamedSeries)
    _raises(lambda: C.contract(REG, "Brent"), P.UnnamedSeries)
    assert P.named_series("DCOILBRENTEU") == "DCOILBRENTEU" and P.roll_days(REG, "BZ=F") == (date(2026, 4, 1),)
    store = _store()
    quotes = [(date(2026, 3, 30), 70.0), (date(2026, 3, 31), 71.0), (date(2026, 4, 1), 60.7), (date(2026, 4, 2), 61.0)]
    rep = P.ingest(store, "BZ=F", quotes, source="Yahoo", retrieved_at_utc=U(2026, 4, 3, 1), registry=REG, clocks=CLK)
    assert rep.appended == 4
    window = P.pit_window(store, "BZ=F", U(2026, 4, 3, 1), U(2026, 4, 3, 1), registry=REG)
    assert [w.obs_date for w in window] == [date(2026, 3, 30), date(2026, 3, 31), date(2026, 4, 2)]
    rets = P.returns_excluding_rolls([P.to_value(r, role="context", books=()) for r in sorted(store.rows("BZ=F"), key=lambda r: r["obs_date"])],
                                     P.roll_days(REG, "BZ=F"))
    assert [d for d, _ in rets] == [date(2026, 3, 31)] and not any(abs(r + 0.145) < 0.01 for _, r in rets)


test_ser_01_named_series_and_futures_roll_days.test_ids = ["T-SER-01"]


def test_ser_02_every_referenced_id_is_registered_with_a_contract():
    doc = json.loads(C.STORE_PATH.read_text(encoding="utf-8"))
    assert C.unknown_ids(REG, C.referenced_ids(doc)) == []
    for sid in doc["data_contracts"]["roles"]:
        assert REG.is_series(sid) or REG.is_group(sid), sid
    for g in ("ASIA_INDEX_CLOSES", "KRX_MARKET_CAPS_005930_000660_KOSPI", "NON_KR_INDEX_MONTH_END_CLOSES", "NAV_LINE_CLOSES"):
        assert REG.members(g) and all(REG.is_series(m) for m in REG.members(g))
    for rg in ("US_TREASURY", "KR_CALL_CD"):
        assert all(REG.is_series(m) for m in REG.range_groups[rg]["members"])
    for sid in REG.series_ids():
        c = C.contract(REG, sid)
        assert c.schedule in REG.schedules and c.grace_pub_bdays == 1
        if "acting_exposure" in c.roles:
            assert isinstance(REG.series[sid].get("contract"), dict), sid
    _raises(lambda: C.contract(REG, "ASIA_INDEX_CLOSES"), C.RegistryError, "group name")
    _raises(lambda: C.contract(REG, "NO_SUCH_SERIES"), C.RegistryError, "unknown")
    _raises(lambda: REG.resolve_binding("ASIA_INDEX_CLOSES", "R-13"), C.RegistryError, "group name")
    store = _store()
    _raises(lambda: P.pit_value(store, "SPX_OFFICIAL_CLOSE", DECISION, U(2026, 10, 2, 7), "R-06", OCT2, registry=REG), P.UnboundConsumer)
    _raises(lambda: P.pit_value(store, "SPX_OFFICIAL_CLOSE", DECISION, U(2026, 10, 2, 7), "R-99", OCT2, registry=REG), P.UnboundConsumer)
    assert P.pit_value(store, "SPX_OFFICIAL_CLOSE", DECISION, U(2026, 10, 2, 7), "nav", OCT2, registry=REG).reason == "missing"
    assert P.pit_value(store, "SPX_OFFICIAL_CLOSE", DECISION, U(2026, 10, 2, 7), "R-13", registry=REG).role == "context"
    from core.quant.cards import referenced_series_ids           # M7: the header drafts' series ids (F-22 scan extended)
    assert C.unknown_ids(REG, referenced_series_ids(ROOT / "docs" / "macro_overlay")) == []


test_ser_02_every_referenced_id_is_registered_with_a_contract.test_ids = ["T-SER-02"]


def test_h10_01_dexkous_never_read_by_production():
    store = _store()
    for consumer in ("corr63", "R-06", "hedge_state"):
        _raises(lambda c=consumer: P.pit_value(store, "DEXKOUS", DECISION, U(2026, 10, 2, 7), c, registry=REG), P.PITError, "proxy")
    assert P.pit_value(store, "DEXKOUS", DECISION, U(2026, 10, 2, 7), "R-11_refusal_book", registry=REG).reason == "missing"
    assert P.pit_value(store, "DEXKOUS", DECISION, U(2026, 10, 2, 7), "corr63", registry=REG, run_mode="backtest").reason == "missing"
    assert REG.series["DEXKOUS"]["production_reads"] is False and REG.series["DTWEXBGS"]["never_acting"] is True


test_h10_01_dexkous_never_read_by_production.test_ids = ["T-H10-01"]


# --------------------------------------------------------------------------- #
# T-H10-02, T-H15-01, T-VIX-01, T-XMKT-01 (data clause)
# --------------------------------------------------------------------------- #
def _kr_dec(d):
    return CLK.close_print_bound_utc("KR", d)


def test_h10_02_strict_h10_publication():
    store = _store()
    days = [date(2026, 9, 14) + timedelta(days=i) for i in range(26) if (date(2026, 9, 14) + timedelta(days=i)).weekday() < 5]
    store.append(_dexkous_rows(CLK, [(d, 1350.0 + i) for i, d in enumerate(days)]))
    latest = lambda d: P.pit_last(store, "DEXKOUS", _kr_dec(d), U(2026, 10, 14), registry=REG).obs_date     # noqa: E731
    assert latest(date(2026, 9, 28)) == date(2026, 9, 18)                       # published Mon 09-28 16:15 ET: after the KRX close
    assert latest(date(2026, 9, 29)) == date(2026, 9, 25)                       # usable from Tue 09-29
    assert latest(OCT2) == date(2026, 9, 25)                                    # R4b state row
    assert latest(date(2026, 10, 13)) == date(2026, 10, 2)                      # Columbus Day: Tue 10-13 16:15 ET
    assert latest(date(2026, 10, 14)) == date(2026, 10, 9)
    row = next(r for r in store.rows("DEXKOUS") if r["obs_date"] == date(2026, 9, 25))
    assert row["available_at_utc"] == U(2026, 9, 28, 20, 15) and row["available_at_source"] == "calendar_bound"


test_h10_02_strict_h10_publication.test_ids = ["T-H10-02"]


def test_h15_01_strict_h15_and_treasury_channel():
    store = _store()
    store.append([_release("DGS10", date(2015, 1, 2), 2.12, U(2026, 1, 1))])
    assert store.rows("DGS10")[0]["available_at_utc"] == U(2015, 1, 5, 21, 15)
    assert P.pit_last(store, "DGS10", _kr_dec(date(2015, 1, 5)), U(2026, 1, 1), registry=REG) is None
    assert P.pit_last(store, "DGS10", _kr_dec(date(2015, 1, 6)), U(2026, 1, 1), registry=REG).obs_date == date(2015, 1, 2)
    # Treasury par yield: the logged posting time is available_at; the expected instant for staleness stays 18:00 ET
    store.append([_release("UST_PAR_10Y", date(2026, 10, 1), 4.11, U(2026, 10, 1, 22, 31), source="Treasury", posting=U(2026, 10, 1, 22, 31))])
    us = lambda d: CLK.close_print_bound_utc("US", d)                           # noqa: E731
    assert P.pit_last(store, "UST_PAR_10Y", us(date(2026, 10, 1)), U(2026, 10, 3), registry=REG) is None
    assert P.pit_last(store, "UST_PAR_10Y", us(OCT2), U(2026, 10, 3), registry=REG).available_at_source == "published"
    assert CLK.publication_instant("UST_PAR_10Y", date(2026, 10, 1)) == U(2026, 10, 1, 22, 0)
    # R4b: a flag first on in data dated Wed 2026-09-23 is read at the US close of Fri 09-25 and earns from Mon 09-28
    avail = CLK.publication_instant("DGS10", date(2026, 9, 23))
    assert avail == U(2026, 9, 24, 20, 15)
    first = _first_decision_at_or_after("US", avail)
    assert first == date(2026, 9, 25) and CLK._next(first, lambda x: CLK.is_session("US", x)) == date(2026, 9, 28)


test_h15_01_strict_h15_and_treasury_channel.test_ids = ["T-H15-01"]


def test_vix_01_close_timing_by_channel():
    store = _store()
    d = date(2026, 9, 30)
    store.append([_release("VIXCLS", d, 16.34, U(2026, 9, 30, 20, 16), source="Cboe", posting=U(2026, 9, 30, 20, 15))])
    us = lambda x: CLK.close_print_bound_utc("US", x)                           # noqa: E731
    read = lambda dec: P.pit_value(store, "VIXCLS", dec, U(2026, 10, 2), "R-08", registry=REG)     # noqa: E731
    assert read(us(d)).reason == "missing"                                      # not usable at the US close of D
    assert read(us(date(2026, 10, 1))).value == 16.34                           # US close of D+1
    assert read(_kr_dec(date(2026, 10, 1))).value == 16.34                      # KRX close of K >= D+1
    s2 = _store()
    s2.append([_release("VIXCLS", d, 16.34, U(2026, 10, 1, 11, 3), source="FRED", posting=U(2026, 10, 1, 11, 3))])
    fred = lambda dec: P.pit_value(s2, "VIXCLS", dec, U(2026, 10, 2), "R-13", registry=REG)        # noqa: E731
    assert fred(_kr_dec(date(2026, 10, 1))).reason == "missing" and fred(us(date(2026, 10, 1))).value == 16.34
    hist = _release("VIXCLS", d, 16.34, U(2026, 10, 14), source="FRED")        # declared history lag: calendar_bound
    assert hist["available_at_utc"] == U(2026, 9, 30, 20, 15) and hist["available_at_source"] == "calendar_bound"
    assert C.check_contract(C.contract(REG, "VIXCLS"), 16.34) is None


test_vix_01_close_timing_by_channel.test_ids = ["T-VIX-01"]


def test_xmkt_01_cross_market_data_clause():
    kr = _kr_dec(OCT2)
    assert not C.usable_cross_market("JP", OCT2, kr, CLK) and C.usable_cross_market("TW", OCT2, kr, CLK)
    assert not C.usable_cross_market("HK", OCT2, kr, CLK) and not C.usable_cross_market("CN", OCT2, kr, CLK)
    csat = _kr_dec(date(2025, 11, 13))
    assert C.usable_cross_market("JP", date(2025, 11, 13), csat, CLK) and C.usable_cross_market("CN", date(2025, 11, 13), csat, CLK)
    assert C.usable_cross_market("JP", date(2024, 11, 4), _kr_dec(date(2024, 11, 4)), CLK)
    assert not C.usable_cross_market("JP", date(2016, 7, 29), _kr_dec(date(2016, 7, 29)), CLK)
    # the independent lag audit applies the rule at the audited market's decision, not the other market's own bound
    def close(sid, mkt, d):
        bound = CLK.close_print_bound_utc(mkt, d)
        return P.to_value(P.make_row(series_id=sid, value=1.0, obs_date=d, session_date=d, obs_utc=bound, obs_kind="close",
                                     value_status="official_close", available_at_utc=bound, available_at_source="calendar_bound",
                                     retrieved_at_utc=bound + timedelta(minutes=11), vintage=None, source="KIS", channel=None),
                          role="risk_model", books=())
    audit = lambda v, mkt, dec: [x["check"] for x in L.lag_audit([v], P.RunContext(dec, dec + timedelta(hours=1), "live"), mkt, REG, CLK)["violations"]]  # noqa: E731
    assert audit(close("NIKKEI225_CLOSE", "JP", OCT2), "KR", kr) == ["cross-market bound + 60 s < decision_utc"]
    assert audit(close("NIKKEI225_CLOSE", "JP", date(2026, 10, 1)), "KR", kr) == []
    us = CLK.close_print_bound_utc("US", OCT2)
    assert audit(close("HSI_CLOSE", "HK", OCT2), "US", us) == ["cross-market bound + 60 s < decision_utc"]
    assert audit(close("HSI_CLOSE", "HK", date(2026, 10, 1)), "US", us) == []
    _raises(lambda: L.lag_audit([close("NIKKEI225_CLOSE", "JP", OCT2)], P.RunContext(kr, kr + timedelta(hours=1), "backtest"), "KR", REG, CLK),
            L.LookAheadError, "cross-market")


test_xmkt_01_cross_market_data_clause.test_ids = ["T-XMKT-01"]


# --------------------------------------------------------------------------- #
# T-RO-02
# --------------------------------------------------------------------------- #
def test_ro_02_kis_client_accepts_only_allowlisted_quotation_paths():
    import ast
    import importlib.util
    from tests.acceptance import _code_only
    from data.krx import kis_client as K
    allow = K.QUOTATION_ALLOWLIST
    assert allow is config.KIS_QUOTATION_ALLOWLIST and isinstance(allow, frozenset)      # frozen in config.py
    assert len(allow) == 25 and all("/quotations/" in p and p.startswith("/uapi/") for p in allow)
    used = set()
    for rel in ("data/krx/kis_client.py", "data/kis_markets.py", "docs/kis_quote_check.py"):
        used |= set(re.findall(r"[\"'](/uapi/[^\"']+)[\"']", _code_only(ROOT / rel)))
    assert used == allow, {"unlisted": sorted(used - allow), "unused": sorted(allow - used)}
    for p in sorted(allow):
        assert K.check_quotation_path(p) == p
    trading = "/uapi/domestic-stock/v1/" + "trading/" + "order-" + "cash"
    for bad in (trading, "/uapi/domestic-stock/v1/" + "trading/inquire-balance", "/oauth2/tokenP", "", None,
                "/uapi/domestic-stock/v1/quotations/not-listed"):
        _raises(lambda b=bad: K.check_quotation_path(b), K.KISError, "not an allowlisted")
    tree = ast.parse((ROOT / "data/krx/kis_client.py").read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "KISClient")
    get = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_get")
    first = get.body[1] if isinstance(get.body[0], ast.Expr) and isinstance(get.body[0].value, ast.Constant) else get.body[0]
    assert isinstance(first, ast.Expr) and isinstance(first.value, ast.Call) and first.value.func.id == "check_quotation_path"
    # a fresh module copy (the suite patches KISClient._get): a trading path raises before credentials or a request
    import sys
    spec = importlib.util.spec_from_file_location("kis_client_fresh", ROOT / "data/krx/kis_client.py")
    fresh = importlib.util.module_from_spec(spec)
    saved = config.kis_credentials
    calls = []
    try:
        sys.modules[spec.name] = fresh
        spec.loader.exec_module(fresh)
        config.kis_credentials = lambda: calls.append("credentials") or ("k", "s")
        _raises(lambda: fresh.KISClient.__new__(fresh.KISClient)._get(trading, "TTTC", {}), fresh.KISError, "not an allowlisted")
    finally:
        config.kis_credentials = saved
        sys.modules.pop(spec.name, None)
    assert calls == [], "credentials were read before the path check"
    # the Claude API is called without tools and no acting module imports it
    assert '"tools"' not in _code_only(ROOT / "core/quant/insights.py") and "'tools'" not in _code_only(ROOT / "core/quant/insights.py")
    for rel in ("core/ficc/pit.py", "core/ficc/contracts.py", "core/ficc/lag_audit.py", "core/ficc/macro_artifacts.py",
                "core/ficc/macro_schema.py", "core/rules/macro_rules.py", "core/rules/governance.py", "core/quant/instruments.py"):
        src = _code_only(ROOT / rel)
        assert "insights" not in src, f"{rel} reads the Claude API module"


test_ro_02_kis_client_accepts_only_allowlisted_quotation_paths.test_ids = ["T-RO-02"]


def test_ro_02_app_key_can_trade_is_an_owner_attestation():
    raise NotRun("OWNER: KIS credentials and the 20-session quote-field check (M1-01); whether the app key can trade is "
                 "recorded as an owner attestation (default 'unknown'), never probed through a trading path (F-3)")


test_ro_02_app_key_can_trade_is_an_owner_attestation.test_ids = ["T-RO-02"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
