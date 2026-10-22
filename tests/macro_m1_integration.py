"""M1 integration: the four Sprint-2 packages wired together.

Package A (core/ficc/pit, contracts, lag_audit) consumes the five calendar methods through
`core.calendars.adapter.CalendarClocks` (package B's signed files + the series registry); a refused or uncovered
calendar reaches the data layer as `CalendarUnavailable` -> MissingInput('missing', detail=<the calendar>) with
fail_closed (brief F-5). Package B's `check_coverage` HALT hook is `core.engine.books.coverage_halt` (package C).
The KIS allowlist is frozen in `config.KIS_QUOTATION_ALLOWLIST` and covers package D's quote-check paths. The
fixture generator (package D) takes its instants from the calendars and its post-close check from `pit.check_fixture`.

Hermetic: signed calendar fixtures come from `tests.macro_m1_calendars.fixture_set()` (a temp dir signed by the
test); stores and book registries are tempfile directories; nothing is written under ~/.nextgen; no wall clock.
"""
from __future__ import annotations

import csv
import inspect
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import config
from core.calendars import publication, store
from core.calendars.adapter import SCHEDULE_IDS, CalendarClocks, registry_schedule
from core.engine import books as B
from core.engine.state import EngineMode
from core.ficc import contracts as C
from core.ficc import lag_audit as L
from core.ficc import macro_schema as S
from core.ficc import pit as P
from core.rules import governance as G
from tests.macro_m1_calendars import fixture_docs, fixture_set
from tests.macro_m1_pit import CLK, REG, SOURCE_SKIPPED, StubClocks, _raises

UTC = timezone.utc
OCT2 = date(2026, 10, 2)
DECISION = datetime(2026, 10, 2, 6, 30, 30, tzinfo=UTC)


def U(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=UTC)


def _tmp(prefix="m1int_"):
    return Path(tempfile.mkdtemp(prefix=prefix))


def _row(sid, value, obs, *, status="official_close", kind="close", avail, retrieved, source="KRX", src="calendar_bound"):
    return P.make_row(series_id=sid, value=value, obs_date=obs, session_date=obs if kind == "close" else None,
                      obs_utc=avail, obs_kind=kind, value_status=status, available_at_utc=avail,
                      available_at_source=src, retrieved_at_utc=retrieved, vintage=None, source=source, channel=None)


# --------------------------------------------------------------------------- #
# A <- B: the clocks adapter over signed calendars answers what the stub answered (T-AVAIL-01 golden rows)
# --------------------------------------------------------------------------- #
def test_clocks_adapter_resolves_registry_schedules_on_signed_calendars():
    cal = fixture_set()
    clk = CalendarClocks(REG, cal=cal)
    stub = StubClocks(skipped=SOURCE_SKIPPED)
    # every registry schedule id maps to a schedule of the shipped publication_schedules draft (or to no instant)
    assert set(SCHEDULE_IDS) == set(REG.schedules)
    shipped = {r["schedule_id"] for r in store.read_yaml(store.DATA_DIR / "publication_schedules.yaml")["rows"]}
    assert {v for v in SCHEDULE_IDS.values() if v} <= shipped
    for sid in ("USD_LIVE_PROXY", "BOK_CALL_RATE", "MOM_PAPER_LS_SERIES"):           # LIVE_QUOTE / AS_POSTED / DERIVED
        assert registry_schedule(REG, sid) is None and clk.publication_instant(sid, OCT2) is None
        assert clk.next_expected_obs(sid, OCT2) is None and clk.usable_at(sid, OCT2, "KR") is None
        assert clk.add_publication_bdays(sid, DECISION, 1) == DECISION
    # the golden availability table (T-AVAIL-01) on the signed set, equal to the stub's answers
    assert clk.publication_instant("DGS10", date(2015, 1, 2)) == stub.publication_instant("DGS10", date(2015, 1, 2)) == U(2015, 1, 5, 21, 15)
    assert clk.usable_at("DGS10", date(2015, 1, 2), "KR") == U(2015, 1, 6, 6, 0, 30)          # KRX Tue, not Mon
    assert clk.publication_instant("DEXKOUS", date(2026, 10, 9)) == stub.publication_instant("DEXKOUS", date(2026, 10, 9)) == U(2026, 10, 13, 20, 15)
    assert clk.usable_at("DEXKOUS", date(2026, 10, 9), "KR") == U(2026, 10, 14, 6, 30, 30)    # Columbus Day -> Wed
    assert clk.usable_at("DGS10", date(2026, 10, 9), "US") == U(2026, 10, 14, 20, 0, 30)
    assert clk.close_print_bound_utc("KR", date(2025, 11, 13)) == stub.close_print_bound_utc("KR", date(2025, 11, 13)) == U(2025, 11, 13, 7, 30, 30)
    assert clk.publication_instant("VIXCLS", date(2026, 9, 24)) == stub.publication_instant("VIXCLS", date(2026, 9, 24)) == U(2026, 9, 24, 20, 15)
    assert clk.publication_instant("UST_PAR_10Y", date(2026, 9, 23)) == stub.publication_instant("UST_PAR_10Y", date(2026, 9, 23)) == U(2026, 9, 23, 22, 0)
    assert clk.publication_instant("KOSPI_OFFICIAL_CLOSE", OCT2) == clk.close_print_bound_utc("KR", OCT2) == DECISION
    assert clk.publication_instant("KODEX200_PDF", OCT2) == stub.publication_instant("KODEX200_PDF", OCT2)
    assert clk.publication_instant("ECOS_1530_CLOSE", date(2016, 7, 29)) == U(2016, 7, 29, 6, 0)       # 15:00 KST before 2016-08-01
    assert clk.publication_instant("ECOS_1530_CLOSE", date(2016, 8, 1)) == U(2016, 8, 1, 6, 30)
    assert clk.next_expected_obs("CPIAUCSL", date(2026, 8, 1)) == date(2026, 9, 1)                  # monthly: calendar offset
    for d in (date(2026, 9, 28), date(2026, 10, 2), date(2026, 10, 9)):
        assert clk.is_session("KR", d) == stub.is_session("KR", d) and clk.is_session("US", d) == stub.is_session("US", d)
        assert clk.next_expected_obs("DGS10", d) == stub.next_expected_obs("DGS10", d)
        assert clk.next_expected_obs("KOSPI_OFFICIAL_CLOSE", d) == stub.next_expected_obs("KOSPI_OFFICIAL_CLOSE", d)
    due = clk.publication_instant("DGS10", date(2015, 1, 2))
    assert clk.add_publication_bdays("DGS10", due, 1) == stub.add_publication_bdays("DGS10", due, 1) == U(2015, 1, 6, 21, 15)
    assert clk.add_publication_bdays("KOSPI_OFFICIAL_CLOSE", DECISION, 1) == stub.add_publication_bdays("KOSPI_OFFICIAL_CLOSE", DECISION, 1)
    # package B's bare-series-id path resolves through the registry (publication._registry_schedule)
    assert publication.usable_at("DGS10", date(2015, 1, 2), "KR", cal=cal) == U(2015, 1, 6, 6, 0, 30)
    assert publication.publication_instant("VIXCLS", date(2026, 9, 24), cal=cal) == U(2026, 9, 24, 20, 15)
    _raises(lambda: publication.publication_instant("USD_LIVE_PROXY", OCT2, cal=cal), KeyError, "no scheduled")
    _raises(lambda: publication.publication_instant("Brent", OCT2, cal=cal), KeyError)
    # the staleness rule through the adapter: the source-skipped list moves d_next (T-STALE-01 b)
    assert C.expected_available_utc(REG, "DEXKOUS", date(2017, 1, 19), clk) == \
        C.expected_available_utc(REG, "DEXKOUS", date(2017, 1, 19), stub) == U(2017, 1, 30, 21, 15)
    docs = fixture_docs()
    docs["source_skipped"]["rows"] = [r for r in docs["source_skipped"]["rows"] if r["series"] != "DEXKOUS"]
    noskip = CalendarClocks(REG, cal=fixture_set("integration_noskip", docs))
    assert C.expected_available_utc(REG, "DEXKOUS", date(2017, 1, 19), noskip) == U(2017, 1, 23, 21, 15)
    st = P.PITStore(_tmp(), registry=REG, clocks=clk)
    st.append([_row("DEXKOUS", 1180.5, date(2017, 1, 19), status="first_release", kind="release",
                    avail=U(2017, 1, 23, 21, 15), retrieved=U(2017, 1, 23, 21, 20), source="FRED")])
    dec = U(2017, 1, 25, 6, 30, 30)
    assert not C.is_stale(st, REG, "DEXKOUS", dec, dec, clk).stale
    assert C.is_stale(st, REG, "DEXKOUS", dec, dec, noskip).reason == "missed_release"
    # outside coverage is a calendar failure, never age-based staleness
    _raises(lambda: C.expected_available_utc(REG, "DGS10", date(2027, 12, 31), clk), C.CalendarUnavailable, "outside")


test_clocks_adapter_resolves_registry_schedules_on_signed_calendars.test_ids = ["T-AVAIL-01", "T-H15-01", "T-H10-02", "T-VIX-01", "T-STALE-01"]


# --------------------------------------------------------------------------- #
# A <- B: stamping and the lag audit on the adapter (T-CLOSE-01 quarantine, T-LAG-01)
# --------------------------------------------------------------------------- #
def test_stamping_and_lag_audit_on_the_calendar_adapter():
    clk = CalendarClocks(REG, cal=fixture_set())
    kw = dict(source="KRX", registry=REG, clocks=clk)
    early = P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, retrieved_at_utc=U(2026, 10, 2, 6, 40, 29), **kw)
    assert early["value_status"] == "provisional_intraday" and early["obs_kind"] == "quote_snapshot"
    row = P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, retrieved_at_utc=U(2026, 10, 2, 6, 40, 30), **kw)
    assert row["value_status"] == "official_close" and row["available_at_utc"] == DECISION
    assert row["available_at_source"] == "calendar_bound" and row["obs_utc"] == DECISION
    printed = P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, retrieved_at_utc=U(2026, 10, 2, 6, 45),
                            print_time_utc=U(2026, 10, 2, 6, 30, 20), **kw)
    assert printed["available_at_utc"] == U(2026, 10, 2, 6, 30, 20) and printed["available_at_source"] == "published"
    late = P.stamp_close("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, retrieved_at_utc=U(2026, 10, 2, 6, 45),
                         print_time_utc=U(2026, 10, 2, 6, 31), **kw)
    assert isinstance(late, P.Flag) and late.code == "print_after_bound"
    st = P.PITStore(_tmp(), registry=REG, clocks=clk)
    rep = P.ingest(st, "KOSPI_OFFICIAL_CLOSE", [(OCT2, 7003.74), (date(2026, 10, 3), 7000.0)], retrieved_at_utc=U(2026, 10, 2, 7), **kw)
    assert rep.appended == 1 and rep.flags[0].code == "not_a_session"            # Saturday: no vendor row is a close
    ctx = P.RunContext(DECISION, U(2026, 10, 2, 7))
    v = C.read_input(st, REG, "KOSPI_OFFICIAL_CLOSE", ctx, "R-06", clk, require_session=OCT2)
    assert isinstance(v, P.PITValue) and v.value == 7003.74 and v.status == "ok"
    audit = L.lag_audit([v], ctx, "KR", REG, clk)
    assert audit == {"checked": 1, "violations": [], "books": []}
    assert L.usable_at(REG, "KOSPI_OFFICIAL_CLOSE", OCT2, clk) == DECISION
    assert L.usable_at(REG, "DGS10", date(2015, 1, 2), clk) == U(2015, 1, 5, 21, 15)
    peek = P.to_value(_row("KOSPI_OFFICIAL_CLOSE", 6943.66, OCT2, avail=U(2026, 10, 2, 1, 56), retrieved=U(2026, 10, 2, 1, 56)),
                      role="acting_exposure", books=("specification:KR",))
    bt = P.RunContext(DECISION, U(2026, 10, 2, 7), "backtest")
    _raises(lambda: L.lag_audit([peek], bt, "KR", REG, clk), L.LookAheadError, "publication_instant")
    live = L.lag_audit([peek], ctx, "KR", REG, clk)
    assert live["books"] == ["specification:KR"] and live["violations"][0]["expected_usable_at_utc"] == "2026-10-02T06:30:30Z"


test_stamping_and_lag_audit_on_the_calendar_adapter.test_ids = ["T-CLOSE-01", "T-LAG-01"]


# --------------------------------------------------------------------------- #
# T-CAL-01: the shipped drafts are unsigned -> every acting read fails closed, the alert names the calendar
# --------------------------------------------------------------------------- #
def test_unsigned_shipped_calendars_fail_acting_inputs_closed():
    unsigned = CalendarClocks(REG, cal=store.CalendarSet())              # the shipped drafts, refused at load
    st = P.PITStore(_tmp(), registry=REG, clocks=unsigned)
    st.append([_row("KOSPI_OFFICIAL_CLOSE", 7003.74, OCT2, avail=DECISION, retrieved=U(2026, 10, 2, 6, 41))])
    ctx = P.RunContext(DECISION, U(2026, 10, 2, 7))
    v = C.read_input(st, REG, "KOSPI_OFFICIAL_CLOSE", ctx, "R-06", unsigned, require_session=OCT2)
    assert isinstance(v, P.MissingInput) and v.reason == "missing" and v.role == "acting_exposure"
    assert ".yaml" in v.detail and "unsigned" in v.detail.lower() and "CalendarUnsigned" in v.detail
    fa = C.on_input_failure("KOSPI_OFFICIAL_CLOSE", v, REG.resolve_binding("KOSPI_OFFICIAL_CLOSE", "R-06"))
    assert fa.fail_closed and fa.alert and fa.status == "missing" and fa.halt == "bound_books" and fa.counts
    assert fa.sets["detail"] == v.detail and fa.books == ("specification",)
    _raises(lambda: C.is_stale(st, REG, "KOSPI_OFFICIAL_CLOSE", DECISION, ctx.knowledge_utc, unsigned), C.CalendarUnavailable, "unsigned")
    # a context read is labelled, never a calendar failure; an ingest or audit through the unsigned set refuses
    st.append([_row("DGS2", 3.55, date(2026, 10, 1), status="first_release", kind="release",
                    avail=U(2026, 10, 2, 20, 15), retrieved=U(2026, 10, 2, 20, 20), source="FRED")])
    ctx_v = C.read_input(st, REG, "DGS2", P.RunContext(U(2026, 10, 5, 6, 30, 30), U(2026, 10, 5, 7)), "display", unsigned)
    assert isinstance(ctx_v, P.PITValue) and ctx_v.role == "context" and ctx_v.value == 3.55
    _raises(lambda: P.ingest(st, "KOSPI_OFFICIAL_CLOSE", [(OCT2, 7003.74)], source="KRX", retrieved_at_utc=U(2026, 10, 2, 7),
                             registry=REG, clocks=unsigned), store.CalendarUnsigned)
    acting = P.to_value(st.rows("KOSPI_OFFICIAL_CLOSE")[0], role="acting_exposure", books=("specification:KR",))
    _raises(lambda: L.lag_audit([acting], ctx, "KR", REG, unsigned), store.CalendarUnsigned)
    assert not store.arm_precondition(OCT2, "KR", cal=store.CalendarSet())    # no book can ARM


test_unsigned_shipped_calendars_fail_acting_inputs_closed.test_ids = ["T-CAL-01"]


# --------------------------------------------------------------------------- #
# B -> C: a decision date outside calendar coverage HALTs (OPS, calendar_coverage) through books.coverage_halt
# --------------------------------------------------------------------------- #
def test_calendar_coverage_halt_through_the_book_runtime():
    from tests.macro_m0_schemas import filled
    cal = fixture_set()
    with tempfile.TemporaryDirectory() as tmp:
        reg = B.BookRegistry(Path(tmp), clock=lambda: U(2028, 1, 4, 7))
        B.create_default_books(reg, ["KR", "US"])
        for bid in ("recommended:KR", "specification:KR"):
            B.arm(reg, bid, DECISION)
        dec, books = U(2028, 1, 4, 6, 30, 30), ["recommended:KR", "specification:KR", "recommended:US"]
        for _ in range(2):                                                   # idempotent per cause
            _raises(lambda: store.check_coverage(date(2028, 1, 4), ("holidays_KRX", "kr_sessions"), cal=cal, now_utc=dec,
                                                 book_ids=books, halt=B.coverage_halt(reg, dec)),
                    store.CalendarCoverageError, "outside")
        for bid in ("recommended:KR", "specification:KR"):
            bk = reg.get(bid)
            assert bk.halted and bk.halt["class"] == "OPS" and bk.halt["reason_code"] == "calendar_coverage"
            assert bk.halt["rearm_mode"] == "auto" and bk.halt["component"] == "core/calendars" and len(bk.halt["causes"]) == 1
        assert reg.get("recommended:US").mode is EngineMode.DISARMED       # a DISARMED book holds nothing
        # back inside coverage: the file pages (<= 20 sessions left), the OPS re-arm is automatic, no cap, no reset
        inside = U(2027, 12, 30, 6, 30, 30)
        alerts = store.check_coverage(date(2027, 12, 30), ("holidays_KRX",), cal=cal, now_utc=inside, book_ids=books,
                                      halt=B.coverage_halt(reg, inside))
        assert alerts and alerts[0]["code"] == "calendar_coverage" and alerts[0]["severity"] == "page"
        for bid in ("recommended:KR", "specification:KR"):
            bk = B.runtime_rearm(reg, bid, "auto", inside, cleared=[store.ALERT_CODE])
            assert bk.mode is EngineMode.ARMED and bk.halt is None and B.post_rearm_cap(bk) == 1.0 and bk.post_rearm_left == 0
        kinds = [(e["kind"], e["book_id"]) for e in G.read_events(reg.log)]
        assert kinds.count(("halt", "recommended:KR")) == 1 and kinds.count(("rearm", "recommended:KR")) == 1
        assert all("calendar_coverage" in e["reason"] for e in G.read_events(reg.log) if e["kind"] in ("halt", "rearm"))
        ms = filled()["macro_state"]
        ms["runtime"] = reg.runtime_entries()
        ms["flags"]["engine_state"] = ms["runtime"][0]["engine_state"]
        assert S.validate("macro_state", ms) == []


test_calendar_coverage_halt_through_the_book_runtime.test_ids = ["T-CAL-02"]


# --------------------------------------------------------------------------- #
# T-RO-02: the allowlist is frozen in config.py and covers the owner-run quote-field check
# --------------------------------------------------------------------------- #
def test_kis_allowlist_frozen_in_config_covers_the_quote_check():
    from data.krx import kis_client as K
    import docs.kis_quote_check as Q
    allow = config.KIS_QUOTATION_ALLOWLIST
    assert isinstance(allow, frozenset) and K.QUOTATION_ALLOWLIST is allow
    assert set(Q.PATHS.values()) <= allow and all(K.check_quotation_path(p) == p for p in Q.PATHS.values())
    assert all(p.startswith("/uapi/") and "/quotations/" in p for p in allow)
    assert not any(("/trading/" in p) or ("/oauth2/" in p) or ("account" in p) for p in allow)
    _raises(lambda: K.check_quotation_path("/uapi/domestic-stock/v1/" + "trading/" + "order-cash"), K.KISError, "not an allowlisted")
    _raises(lambda: K.check_quotation_path("/uapi/etfetn/v1/quotations/not-listed"), K.KISError, "not an allowlisted")


test_kis_allowlist_frozen_in_config_covers_the_quote_check.test_ids = ["T-RO-02"]


# --------------------------------------------------------------------------- #
# A <-> legacy: the data.py ingest hook, History.status and NotTradable agree with pit's vocabularies
# --------------------------------------------------------------------------- #
def test_data_hook_history_status_and_instruments_agree_with_pit():
    from core.ficc import data as D
    from core.quant import history as H
    from core.quant import instruments as I
    params = inspect.signature(D._provider_rows).parameters
    assert {"not_before", "pit_store", "retrieved_at_utc"} <= set(params) and params["pit_store"].default is None
    assert H.History.__dataclass_fields__["status"].default == "" and "provisional_intraday" in P.VALUE_STATUS_RANK
    assert set(__import__("re").findall(r'status="([a-z_]+)"', inspect.getsource(H))) <= set(P.VALUE_STATUS_RANK)
    assert I.NotTradable.status in P.REASONS
    st = P.PITStore(_tmp(), registry=REG, clocks=CLK)
    assert st.ingest_rows("KRX", "KOSPI_OFFICIAL_CLOSE", [("2026-10-02", 7003.74)], U(2026, 10, 2, 6, 41)) == 1
    assert st.ingest_rows("YFINANCE", "KOSPI_OFFICIAL_CLOSE", [("2026-10-02", 6943.66)], U(2026, 10, 2, 1, 56)) == 1
    rows = st.rows("KOSPI_OFFICIAL_CLOSE")
    assert [(r["source"], r["value_status"], r["obs_kind"]) for r in rows] == \
        [("KRX", "official_close", "close"), ("Yahoo", "provisional_intraday", "quote_snapshot")]
    assert st.ingest_rows("FRED", "NOT_A_SERIES", [("2026-10-02", 1.0)], U(2026, 10, 2, 7)) == 0
    assert P.PITStore(_tmp()).ingest_rows("KRX", "KOSPI_OFFICIAL_CLOSE", [("2026-10-02", 1.0)], U(2026, 10, 2, 7)) == 0
    v = P.pit_value(st, "KOSPI_OFFICIAL_CLOSE", DECISION, U(2026, 10, 2, 7), "R-06", OCT2, registry=REG)
    assert v.value == 7003.74 and v.value_status == "official_close"


test_data_hook_history_status_and_instruments_agree_with_pit.test_ids = ["T-PROV-01"]


# --------------------------------------------------------------------------- #
# D <- A, B: the fixture generator's instants come from the calendars; its output passes pit.check_fixture
# --------------------------------------------------------------------------- #
def test_fixture_generator_instants_from_calendars_and_check_fixture_on_csv():
    import docs.macro_fixtures as MF
    clk = CalendarClocks(REG, cal=fixture_set())
    available_at = MF.calendar_available_at(REG, clk)
    assert available_at("KOSPI_OFFICIAL_CLOSE", date(2026, 9, 30), "official_close") == (U(2026, 9, 30, 6, 30), U(2026, 9, 30, 6, 30, 30))
    assert available_at("DGS10", date(2015, 1, 2), "first_release") == (U(2015, 1, 5, 21, 15), U(2015, 1, 5, 21, 15))
    _raises(lambda: available_at("USD_LIVE_PROXY", OCT2, "live_snapshot"), ValueError, "never infers")
    _raises(lambda: available_at("KS11", OCT2, "vendor_close"), KeyError, "named")
    _raises(lambda: available_at("KOSPI_OFFICIAL_CLOSE", date(2026, 10, 3), "official_close"), store.NotASession)
    tmp = _tmp()
    src = tmp / "ref.csv"
    src.write_text("Date,Close\n2026-09-30,7000.1\n2026-10-01,6971.6\n", encoding="utf-8")
    fields, rows = MF.fixture_rows(src, series_id="KOSPI_OFFICIAL_CLOSE", value_status="official_close",
                                   available_at_source="calendar_bound", retrieved_at_utc=U(2026, 10, 2, 9), available_at=available_at)
    assert fields[:2] == ["Date", "Close"] and fields[2] == "series_id" and rows[0]["series_id"] == "KOSPI_OFFICIAL_CLOSE"
    assert rows[1]["available_at_utc"] == "2026-10-01T06:30:30Z" and rows[1]["obs_utc"] == "2026-10-01T06:30:00Z"
    out = tmp / "fixture.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    assert P.check_fixture(out, registry=REG, clocks=clk) == 2
    rows[1]["retrieved_at_utc"] = "2026-10-01T06:35:00Z"                     # before close + 10 min: refused
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    _raises(lambda: P.check_fixture(out, registry=REG, clocks=clk), P.FixtureRefused, "close + 10 min")
    (tmp / "noid.csv").write_text("Date,Close,obs_date\n2026-09-30,1,2026-09-30\n", encoding="utf-8")
    _raises(lambda: P.check_fixture(tmp / "noid.csv", registry=REG, clocks=clk), P.FixtureRefused, "series_id")


test_fixture_generator_instants_from_calendars_and_check_fixture_on_csv.test_ids = ["T-FIX-01"]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
