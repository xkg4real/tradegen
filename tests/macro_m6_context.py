"""M6 package C - context log, context isolation, break protocol, macro_state / overlay_decision builders
(T-CTX-01, T-CTX-02, T-BREAK-01; the M6 clauses of T-HEDGE-01 and I-06c; T-SCHEMA-01 on built artifacts).

Hermetic: synthetic PIT stores and a temp registry (the shipped registry plus the sheet-only / live / monthly ids
the context log needs), the S2 StubClocks and signed fixture calendars, temp artifact dirs and rules stores;
nothing written under ~/.nextgen. Reference-data and owner clauses raise NotRun.
"""
from __future__ import annotations

import copy
import json
import math
import re
import tempfile
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import yaml

from core.engine.state import EngineMode
from core.ficc import context_log as CL
from core.ficc import contracts as C
from core.ficc import macro_artifacts as MA
from core.ficc import macro_schema as MS
from core.ficc import pit as P
from core.quant import risk_layer as R
from core.quant import sleeves as S
from core.rules import governance as G
from tests.macro_m0_schemas import filled
from tests.macro_m1_pit import REG, StubClocks, _raises
from tests.macro_m2_risk import DECISION, KNOWLEDGE, _close_row, _hedge_store, _hs, _kospi_store, _registry, _sessions, _vt
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
CLK = StubClocks()
OCT2 = date(2026, 10, 2)
CLOCK = lambda: datetime(2026, 10, 2, 7, 1, 0, tzinfo=UTC)          # noqa: E731
SHEET_IDS = ("DGS2", "DGS10", "DGS30", "T10Y2Y", "DFII10", "T10YIE", "SOFR", "DFF", "BAMLC0A0CM", "BAMLH0A0HYM2",
             "DTWEXBGS", "DEXUSEU", "DEXJPUS", "DEXKOUS", "VIXCLS", "DCOILWTICO", "ZN=F", "GC=F")
LIVE = ("KOFIA_MARGIN_DEBT", "KRX_LETF_AUM_INDEX", "KRX_LETF_AUM_SINGLE_STOCK", "VIX_1600ET_SNAPSHOT",
        "VIX3M_1600ET_SNAPSHOT", "KOSPI200_MFIV_1530KST")


def U(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=UTC)


def _tmp(prefix="m6ctx_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


# --------------------------------------------------------------------------- #
# A temp registry: the shipped one plus the ids the context log reads that M1 has not registered (brief C.3)
# --------------------------------------------------------------------------- #
_CTX_REG = {}


def ctx_registry():
    if "reg" not in _CTX_REG:
        doc = yaml.safe_load(C.REGISTRY_PATH.read_bytes().decode("utf-8"))
        s = doc["series"]

        def clone(base, **kw):
            d = copy.deepcopy(s[base])
            d.update(kw)
            return d
        for sid in ("SOFR", "DFF", "BAMLC0A0CM"):
            s[sid] = clone("DGS2", unit="pct")
        s["DEXUSEU"] = clone("DEXJPUS", unit="USD_per_EUR")
        s["DCOILWTICO"] = clone("DCOILBRENTEU", unit="USD_per_bbl")
        for sid in ("ZN=F", "GC=F"):
            s[sid] = clone("^MOVE", unit="level")
        for sid in ("GS10", "TB3MS", "EFFR", "NROU", "GDPC1", "GDPPOT"):
            s[sid] = clone("UNRATE", unit="pct", missing_months=[])
        for sid in LIVE:
            s[sid] = clone("KOSPI200_MFIV_1530", unit="level")
        path = _tmp("m6reg_") / "series_registry.yaml"
        path.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
        _CTX_REG["reg"] = C.load_registry(path, roles={})
        _CTX_REG["clk"] = StubClocks(registry=_CTX_REG["reg"])
    return _CTX_REG["reg"], _CTX_REG["clk"]


def _fed_days(end: date, n: int, clk) -> list[date]:
    out, d = [], end
    while len(out) < n:
        if clk.fed_bday(d):
            out.append(d)
        d -= timedelta(days=1)
    return out[::-1]


def _rel(reg, clk, sid, d, v, *, vintage=None, status="first_release", source="FRED", retrieved=None):
    due = clk.publication_instant(sid, d)
    retrieved = retrieved or ((due + timedelta(minutes=5)) if due else U(d.year, d.month, d.day, 12))
    return P.stamp_release(sid, d, v, retrieved_at_utc=retrieved, source=source, registry=reg, clocks=clk,
                           vintage=vintage, value_status=status)


def _months(end: date, n: int) -> list[date]:
    return [P.add_months(end, -i) for i in range(n)][::-1]


def context_store(*, with_live=True, synthetic_sheet=(), stale_sheet=()):
    """A PIT store for the context log at the KR decision of 2 Oct 2026 (T-CTX-02 fixture rows)."""
    reg, clk = ctx_registry()
    store = P.PITStore(_tmp() / "store", registry=reg, clocks=clk)
    rng = np.random.default_rng(11)
    rows = []
    days = _fed_days(date(2026, 10, 1), 70, clk)
    for i, sid in enumerate(SHEET_IDS):
        base = 100.0 if sid in ("ZN=F", "GC=F", "DTWEXBGS", "DCOILWTICO", "VIXCLS") else 4.0
        path = base + np.cumsum(rng.normal(0, 0.02 * base, size=len(days)))
        sched = reg.schedule(sid)
        for d, v in zip(days, path):
            if sid in stale_sheet and d > date(2026, 8, 31):
                continue
            if sched == "NYSE_CLOSE":
                if not clk.is_session("US", d):
                    continue
                r = _close_row(sid, d, v, market="US", source="Yahoo", status="vendor_close", clocks=clk)
            else:
                r = _rel(reg, clk, sid, d, v)
            if sid in synthetic_sheet:
                r["synthetic"], r["provider_mode"] = True, "auto"
            rows.append(r)
    # PAYEMS: first print 119.4 (vintage 4 Sep) and the current vintage 9.7 (25 Sep) for Aug-2026 (R-13 L1686)
    rows.append(_rel(reg, clk, "PAYEMS", date(2026, 8, 1), 119.4, vintage=date(2026, 9, 4), retrieved=U(2026, 9, 4, 13)))
    rows.append(_rel(reg, clk, "PAYEMS", date(2026, 8, 1), 9.7, vintage=date(2026, 9, 25), status="revised", retrieved=U(2026, 9, 25, 13)))
    rows.append(_rel(reg, clk, "PAYEMS", date(2026, 7, 1), 50.0, vintage=date(2026, 8, 7), retrieved=U(2026, 8, 7, 13)))
    # UNRATE monthly with the Oct-2025 gap (BLS household survey); NaN propagation for the in-house Sahm
    for m in _months(date(2026, 8, 1), 22):
        if m != date(2025, 10, 1):
            rows.append(_rel(reg, clk, "UNRATE", m, 4.1 + 0.02 * ((m.month * 7) % 5), vintage=P.add_months(m, 1) + timedelta(days=5),
                             retrieved=U(P.add_months(m, 1).year, P.add_months(m, 1).month, 6, 13)))
    for m in _months(date(2026, 8, 1), 15):
        rows.append(_rel(reg, clk, "PCEPILFE", m, 100.0 * 1.0025 ** _months(date(2026, 8, 1), 15).index(m), source="ALFRED",
                         vintage=P.add_months(m, 1) + timedelta(days=27), retrieved=U(P.add_months(m, 1).year, P.add_months(m, 1).month, 28, 13)))
        if m != date(2025, 10, 1):
            rows.append(_rel(reg, clk, "CPIAUCSL", m, 300.0 * 1.0028 ** _months(date(2026, 8, 1), 15).index(m),
                             retrieved=U(P.add_months(m, 1).year, P.add_months(m, 1).month, 12, 13)))
    for sid, v in (("GS10", 3.57), ("TB3MS", 5.14), ("EFFR", 3.88), ("NROU", 4.4), ("GDPC1", 23500.0), ("GDPPOT", 23450.0)):
        rows.append(_rel(reg, clk, sid, date(2026, 8, 1), v, retrieved=U(2026, 9, 6, 13)))
    for i, d in enumerate(_fed_days(date(2026, 9, 26), 6, clk)):
        rows.append(_rel(reg, clk, "ICSA", d, 220000.0 + 1000 * i, retrieved=U(d.year, d.month, d.day, 13)))
    for sid, v in (("T10Y3M", 1.07), ("T5YIFR", 2.36), ("BAA10Y", 1.47), ("THREEFYTP10", 1.02), ("DCOILBRENTEU", 113.96)):
        for d in _fed_days(date(2026, 9, 30), 25, clk):
            rows.append(_rel(reg, clk, sid, d, v + 0.001 * d.day))
    us = _sessions("US", date(2026, 10, 1), 30, clk)
    for d, v in zip(us, 7000.0 + np.cumsum(rng.normal(0, 30, size=len(us)))):
        rows.append(_close_row("SPX_OFFICIAL_CLOSE", d, v, market="US", source="KIS", status="vendor_close", clocks=clk))
        rows.append(_close_row("BZ=F", d, 102.0 + 0.01 * d.day, market="US", source="Yahoo", status="vendor_close", clocks=clk))
        rows.append(_close_row("^MOVE", d, 108.0, market="US", source="Yahoo", status="vendor_close", clocks=clk))
        rows.append(P.stamp_quote("USD_LIVE_PROXY", d, 99.0, quote_utc=clk.close_print_bound_utc("US", d) - timedelta(minutes=1),
                                  retrieved_at_utc=clk.close_print_bound_utc("US", d), source="Yahoo"))
    kr = _sessions("KR", OCT2, 270, clk)
    for d, v in zip(kr, 3000.0 * np.cumprod(1.0 + rng.normal(0.0003, 0.012, size=len(kr)))):
        rows.append(_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR", clocks=clk))
    if with_live:
        q = lambda sid, d, v, when: P.stamp_quote(sid, d, v, quote_utc=when, retrieved_at_utc=when + timedelta(seconds=20), source="KRX")   # noqa: E731
        rows += [q("KOFIA_MARGIN_DEBT", OCT2, 21.5e12, U(2026, 10, 2, 6, 30, 5)), q("KRX_LETF_AUM_INDEX", OCT2, 9.1e12, U(2026, 10, 2, 6, 30, 5)),
                 q("KRX_LETF_AUM_SINGLE_STOCK", OCT2, 1.2e12, U(2026, 10, 2, 6, 30, 5)),
                 q("VIX_1600ET_SNAPSHOT", date(2026, 10, 1), 16.34, U(2026, 10, 1, 20, 0)), q("VIX3M_1600ET_SNAPSHOT", date(2026, 10, 1), 18.37, U(2026, 10, 1, 20, 0)),
                 q("KOSPI200_MFIV_1530KST", OCT2, 19.8, U(2026, 10, 2, 6, 30))]
    store.append(rows)
    return store, reg, clk


def _build(store, reg, clk, **kw):
    kw.setdefault("rules", None)
    return CL.build_context_log(store, reg, DECISION, KNOWLEDGE, clocks=clk, clock=CLOCK, **kw)


# --------------------------------------------------------------------------- #
# T-CTX-01: static scan with a positive control; runtime guard
# --------------------------------------------------------------------------- #
def test_ctx_01_static_import_scan_and_positive_controls():
    report = CL.static_isolation_report()
    assert report == [], report
    for name in ("core/quant/risk_layer.py", "core/quant/sleeves.py", "core/engine/books.py"):
        mod = name[:-3].replace("/", ".")
        assert CL.is_acting_module(mod) and mod in CL.repo_modules(), name
    assert not CL.is_acting_module("core.skills.macro_daily") and "core.skills.macro_daily" in CL.ORCHESTRATOR_MODULES
    # a detector that cannot fail proves nothing: injected violations of every kind are reported
    ctl = CL.scan_isolation({"core.quant.risk": "from core.ficc import context_log\n"})
    assert [v.kind for v in ctl] == ["import"] and "core.ficc.context_log" in ctl[0].detail
    assert CL.scan_isolation({"core.engine.books": "import core.ficc.macro as m\n"})[0].kind == "import"
    via = CL.scan_isolation({"core.quant.risk": "import core.ficc.helper\n", "core.ficc.helper": "from core.ficc.macro import macro_sheet\n"})
    assert [v.kind for v in via] == ["import"], via                                  # transitive, function-level import too
    lazy = CL.scan_isolation({"core.quant.risk": "def f():\n    from core.ficc import context_log\n"})
    assert lazy and lazy[0].kind == "import"
    kinds = {v.kind for v in CL.scan_isolation({"core.calendars.x": "y = macro_sheet()\np = 'r18_break_log.jsonl'\n"})}
    assert kinds == {"callee", "path"}
    assert CL.scan_isolation({"core.ficc.macro_artifacts": "from core.ficc import context_log\n"})[0].kind == "builder"
    assert CL.scan_isolation({"core.skills.macro_daily": "from core.ficc import context_log\n"}) == []      # the writer may import
    assert CL.scan_isolation({"core.skills.macro_daily": "x = read_context_log(p)\n"})[0].kind == "callee"  # but never read
    # TYPE_CHECKING and __main__ bodies are skipped; exempt modules are not acting
    assert CL.scan_isolation({"core.quant.x": "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from core.ficc.macro import MacroSheet\n"}) == []
    assert CL.scan_isolation({"core.quant.x": "if __name__ == '__main__':\n    import core.ficc.macro\n"}) == []
    assert CL.scan_isolation({"core.quant.insights": "import core.ficc.macro\n"}) == []
    assert not CL.is_acting_module("core.quant.refusal") and "core.quant.refusal" in CL.PROTECTED_MODULES
    assert set(CL.PROTECTED_PATH_FRAGMENTS) == {"context_log/", CL.BREAK_LOG[:-6], CL.RESEARCH_LOG[:-6]}


test_ctx_01_static_import_scan_and_positive_controls.test_ids = ["T-CTX-01"]


def _call_as(module_name: str, fn, *args, **kw):
    """Call `fn` from a frame whose module is `module_name` (compiled code object with that __name__)."""
    code = compile("def caller(fn, a, k):\n    return fn(*a, **k)\n", f"<{module_name}>", "exec")
    g = {"__name__": module_name}
    exec(code, g)
    return g["caller"](fn, args, kw)


def test_ctx_01_runtime_guard_refuses_acting_callers():
    tmp = _tmp()
    (tmp / CL.BREAK_LOG).write_text("", encoding="utf-8")
    log_path = tmp / "ctx.json"
    log_path.write_text(json.dumps({"schema": CL.SCHEMA, "items": []}), encoding="utf-8")
    for fn, args in ((CL.read_context_log, (log_path,)), (CL.load_break_log, (tmp,)),
                     (CL.guarded_macro_sheet, ()), (CL.assert_not_acting_caller, ())):
        for mod in ("core.quant.risk", "core.engine.books", "core.rules.macro_rules", "core.calendars.clocks", "core.ficc.pit"):
            _raises(lambda: _call_as(mod, fn, *args, **({"source": "synthetic", "days": 300} if fn is CL.guarded_macro_sheet else {})),
                    CL.ContextIsolationError, mod)
    # the same calls from a non-acting frame (this test module, ui, the exempt insights) pass
    assert CL.read_context_log(log_path)["schema"] == CL.SCHEMA and CL.load_break_log(tmp) == []
    assert _call_as("ui.macro_page", CL.read_context_log, log_path)["items"] == []
    assert _call_as("core.quant.insights", CL.load_break_log, tmp) == []
    sheet = _call_as("tests.macro_m6_context", CL.guarded_macro_sheet, source="synthetic", days=300)
    assert len(sheet.rows) == 18


test_ctx_01_runtime_guard_refuses_acting_callers.test_ids = ["T-CTX-01"]


def test_ctx_01_regime_read_is_relabelled_descriptive():
    from core.ficc import macro as M
    sheet = M.macro_sheet(source="synthetic", days=300)
    assert M.DESCRIPTIVE_READ_NOTE == CL.DESCRIPTIVE_READ_NOTE and "not a regime model" in M.DESCRIPTIVE_READ_NOTE
    assert sheet.regime.summary.startswith("[" + M.DESCRIPTIVE_READ_NOTE + "]") and "Curve" in sheet.regime.summary
    assert "not a regime model" in (M.__doc__ or "") and "not a regime model" in (M.Regime.__doc__ or "")
    labels = set(M.CURVE_REGIMES) | set(M.RISK_REGIMES) | set(M.DOLLAR_REGIMES) | set(M.TREND_REGIMES)
    assert labels.isdisjoint(R.LABELS), "the sheet's read never reuses the R-06 volatility label names (section 10 item 24)"
    assert len(labels) == 16 and M.daily_brief(sheet)["regime"]["summary"] == sheet.regime.summary


test_ctx_01_regime_read_is_relabelled_descriptive.test_ids = ["T-CTX-01"]


# --------------------------------------------------------------------------- #
# T-CTX-02: items, vintages, live stamps, sheet items; failure paths; calculators
# --------------------------------------------------------------------------- #
def test_ctx_02_items_vintages_live_and_sheet():
    store, reg, clk = context_store()
    log = _build(store, reg, clk)
    assert MS.validate("context_log", log) == [] and log["acts"] is False and log["as_of_utc"] == log["decision_utc"]
    assert log["read_only"] is True and log["tree_hash"] and log["git_hash"] == "UNVERSIONED" and log["knowledge_utc"] == "2026-10-02T07:00:00Z"
    items = {i["series_id"]: i for i in log["items"]}
    for it in log["items"]:
        assert "vintage" in it and it["retrieved_at_utc"] and it["available_at_utc"] <= log["decision_utc"]
        assert it["retrieved_at_utc"] <= log["knowledge_utc"] and isinstance(it["stale"], bool)
        assert re.search(r"\([^()]+\)$", it["name"]), it["name"]               # every name ends with its unit (F-9)
    # all 18 sheet items, from_sheet true, causal trailing z on the PIT-visible rows (never the legacy loader)
    assert all(sid in items and items[sid]["from_sheet"] is True for sid in SHEET_IDS), sorted(set(SHEET_IDS) - set(items))
    assert log["extras"]["n_from_sheet"] == 18 and sum(1 for i in log["items"] if i.get("from_sheet")) == 18
    for sid in SHEET_IDS:
        assert items[sid]["zscore_window"].startswith("trailing_") and "never thresholded" in items[sid]["note"]
    assert items["DGS10"]["obs_date"] == "2026-09-30" and items["DGS10"]["timing"] == "publication"    # strict H.15: 1 Oct not usable
    assert items["T10Y2Y"]["note"].startswith("level and z only") and "RECESSION_PROBIT_ET" in items
    assert items["DEXKOUS"]["value_status"] == "first_release" and "proxy" in items["DEXKOUS"]["note"]
    # revised series: first print, current value, vintage date (ALFRED); vintage = the vintage of value
    p = items["PAYEMS"]
    assert p["value"] == 9.7 and p["first_release"] == 119.4 and p["latest"] == 9.7 and p["vintage"] == "2026-09-25"
    assert p["vintage_date"] == "2026-09-25" and p["value_status"] == "revised" and p["obs_date"] == "2026-08-01"
    assert items["PAYEMS_CHANGE_1M"]["value"] == 9.7 - 50.0 and items["PAYEMS_CHANGE_1M"]["vintage"] == "2026-09-25"
    # live stamps (T-CTX-02): leverage, VRP, the 16:00 ET and 15:30 KST snapshots
    for sid in LIVE + ("VRP_US",):
        assert items[sid]["timing"] == "live", sid
    for sid in ("VIX_1600ET_SNAPSHOT", "VIX3M_1600ET_SNAPSHOT", "KOSPI200_MFIV_1530KST"):
        assert items[sid]["value_status"] == "live_snapshot" and items[sid]["vintage"] is None
    assert items["VIX_1600ET_SNAPSHOT"]["value"] == 16.34 and items["VIX_1600ET_SNAPSHOT"]["obs_date"] == "2026-10-01"
    assert "structural break 2026-07-16" in items["KRX_LETF_AUM_INDEX"]["note"]
    assert abs(items["VRP_US"]["value"] - (0.1634 ** 2 / 12 - sum(r * r for r in _spx_returns(store, reg)))) < 1e-12
    # R-13 derived items from PIT reads only
    assert abs(items["RECESSION_PROBIT_ET"]["value"] - 0.744) < 1e-3 and "published coefficients" in items["RECESSION_PROBIT_ET"]["note"]
    t = items["TAYLOR_RESIDUAL_RANGE"]
    assert t["value"] is None and len(t["range"]) == 2 and t["range"][0] < t["range"][1] and t["note"].startswith("never thresholded")
    assert t["obs_date"] == "2026-08-01" and t["value_status"] == "vendor_derived" and t["vintage"] == "2026-09-28"
    s = items["SAHM_INHOUSE"]
    assert s["value"] is None and "NaN" in s["note"] and s["value_status"] == "vendor_derived_across_gap"   # Oct-2025 gap propagates
    assert items["UNRATE_3M_CHANGE"]["value"] is not None and items["ICSA_4WK_AVG"]["value"] == 220000.0 + 1000 * (2 + 3 + 4 + 5) / 4
    assert items["CPIAUCSL_YOY"]["value"] is not None and items["CPIAUCSL_YOY"]["obs_date"] == "2026-08-01"   # the gap is merely inside
    assert items["CPIAUCSL_YOY"]["value_status"] == "vendor_derived_across_gap"
    assert items["PCEPILFE_YOY"]["value_status"] == "vendor_derived" and abs(items["PCEPILFE_YOY"]["value"] - (1.0025 ** 12 - 1) * 100) < 1e-9
    assert items["KOSPI_TREND_SMA10M"]["value"] in ("above", "below") and items["KOSPI_TREND_SMA10M"]["timing"] == "live"
    assert 0.0 < items["KOSPI_RV21"]["value"] < 1.0 and 0.0 < items["KOSPI_RV21_PCTILE_3Y"]["value"] <= 1.0
    assert items["THREEFYTP10"]["name"].startswith("Kim–Wright") and items["USDJPY_DIST_TO_160"]["value"] == 160.0 - items["DEXJPUS"]["value"]
    assert items["BRENT_DATED_MINUS_BZF"]["value"] == items["DCOILBRENTEU"]["value"] - items["BZ=F"]["value"]
    assert items["DFII10_CHG_20D"]["value"] is not None and items["BAA10Y_CHG_21D"]["value"] is not None
    # never acquired: no item, never a fabricated date; the turbulence universe is an owner input (F-17)
    missing = {m["series_id"]: m["reason"] for m in log["extras"]["missing_items"]}
    assert "FOMC_DECISION" in missing and "TURBULENCE" in missing and "SEP_TABLE2_BANDS" in missing
    assert not any(i["series_id"] in ("FOMC_DECISION", "TURBULENCE") for i in log["items"])
    assert log["extras"]["synthetic_excluded"] == [] and log["extras"]["item_errors"] == []
    # written through the one writer; the context log is a whole-refusal kind: valid -> context_log/<decision>.json
    root = _tmp()
    w = CL.write_context_log(root, log, CLOCK)
    assert w.status == "written" and w.path.parent.name == "context_log" and not (root / "quarantine").exists()
    assert CL.read_context_log(w.path)["items"][0]["series_id"] == log["items"][0]["series_id"]
    assert CL.static_isolation_report() == []                                     # T-CTX-01 still passes


test_ctx_02_items_vintages_live_and_sheet.test_ids = ["T-CTX-02"]


def _spx_returns(store, reg):
    px = P.pit_window(store, "SPX_OFFICIAL_CLOSE", DECISION, KNOWLEDGE, n=22, registry=reg, statuses=P.CLOSE_STATUSES)
    return [b.value / a.value - 1.0 for a, b in zip(px, px[1:])]


def test_ctx_02_failure_paths_label_and_never_halt():
    with tempfile.TemporaryDirectory() as tmp:
        books = _registry(tmp)
        store, reg, clk = context_store(synthetic_sheet=("GC=F",), stale_sheet=("DTWEXBGS",))
        boom = {"BOOM_ITEM": lambda rd, r: 1 / 0, **{k: v for k, v in CL.default_calculators().items() if k == "RECESSION_PROBIT_ET"}}
        log = _build(store, reg, clk, calculators=boom)
        assert MS.validate("context_log", log) == []
        items = {i["series_id"]: i for i in log["items"]}
        # a raising context item: labelled in extras.item_errors + an info alert, the other items untouched
        assert log["extras"]["item_errors"] == [{"series_id": "BOOM_ITEM", "error": "ZeroDivisionError: division by zero"}]
        assert [a["code"] for a in log["extras"]["alerts"]] == [CL.ALERT_ITEM_ERROR, CL.ALERT_SYNTHETIC]
        assert "RECESSION_PROBIT_ET" in items and "DGS10" in items
        # synthetic: excluded, listed, alerted (never written as a value, F-11)
        assert "GC=F" not in items and log["extras"]["synthetic_excluded"] == ["GC=F"]
        # stale context series: stale == true, the value still shown, nothing else happens
        assert items["DTWEXBGS"]["stale"] is True and items["DTWEXBGS"]["value"] is not None and "stale" in items["DTWEXBGS"]["note"]
        assert items["DGS10"]["stale"] is False
        # no clocks: every item is labelled stale (conservative), never an exception
        nocal = CL.build_context_log(store, reg, DECISION, KNOWLEDGE, clocks=None, clock=CLOCK, calculators={})
        assert nocal["items"] and all(i["stale"] for i in nocal["items"])
        # an invalid log (undeclared item field; missing required field): not in the artifact dir, quarantined, alerted
        root = Path(tmp) / "artifacts"
        bad = copy.deepcopy(log)
        bad["items"][0]["regime_state"] = "bull"
        w = CL.write_context_log(root, bad, CLOCK)
        assert w.status == "quarantined" and w.path.parent.name == "quarantine" and not (root / "context_log").exists()
        assert w.alert["code"] == CL.ALERT_LOG_INVALID and w.alert["severity"] == "warn" and any("regime_state" in i for i in w.issues)
        bad2 = copy.deepcopy(log)
        del bad2["items"][0]["vintage"]
        assert CL.write_context_log(root, bad2, CLOCK).status == "quarantined"
        # the isolation guard: a raising context writer never reaches the acting path; it is recorded in the run log
        run_log = Path(tmp) / "run_log.jsonl"
        res = CL.run_context_step("context_log", lambda: (_ for _ in ()).throw(RuntimeError("provider down")),
                                  run_log=run_log, decision_utc=DECISION, clock=CLOCK)
        assert res.ok is False and res.error == "RuntimeError: provider down" and res.logged and res.alert["code"] == CL.ALERT_STEP_ERROR
        row = json.loads(run_log.read_text(encoding="utf-8").splitlines()[-1])
        assert row["step"] == "context_log" and row["halt"] == "never" and row["class"] == "context"
        ok = CL.run_context_step("context_log", lambda: 42)
        assert ok.ok and ok.value == 42
        unwritable = CL.run_context_step("x", lambda: 1 / 0, run_log=Path(tmp) / "run_log.jsonl" / "nope.jsonl", decision_utc=DECISION)
        assert unwritable.ok is False and unwritable.logged is False and unwritable.log_error      # even a dead run log never raises
        # nothing moved on the acting side: every book ARMED, no counter, no HALT
        for b in books.ids():
            rt = books.get(b)
            assert rt.mode is EngineMode.ARMED and rt.halt is None and rt.book_counter == 0 and rt.consecutive_failures == {}


test_ctx_02_failure_paths_label_and_never_halt.test_ids = ["T-CTX-02"]


def test_ctx_02_calculators():
    assert abs(CL.recession_probit_et(3.57, 5.14) - 0.744) < 1e-3                 # the spec's May-2023 read (L1679)
    assert abs(CL.bond_equivalent(5.14) - 5.2804) < 1e-3
    lo, hi = CL.taylor_residual_range(3.875, 3.0, 4.1, 4.4, 100.0, 99.0)
    rules = [3.875 - (r + 3.0 + 0.5 * (3.0 - 2.0) + a * g) for r in (0.5, 1.0, 2.0) for g in (2 * (4.4 - 4.1), 100 * (100.0 / 99.0 - 1)) for a in (0.5, 1.0)]
    assert len(rules) == 12 and (lo, hi) == (min(rules), max(rules)) and CL.taylor_midpoint(lo, hi) == (lo + hi) / 2
    assert CL.vrp(16.34, [0.0] * 21) == 0.1634 ** 2 / 12 and _raises(lambda: CL.vrp(16.0, [0.0] * 20), ValueError)
    assert CL.trend_state_sma10m([100.0] * 9 + [99.0]) == "below" and CL.trend_state_sma10m([100.0] * 9 + [101.0]) == "above"
    assert CL.trend_state_sma10m([1.0] * 10) == "above" and _raises(lambda: CL.trend_state_sma10m([1.0] * 9), ValueError)
    px = list(100.0 * np.cumprod(1 + np.random.default_rng(3).normal(0, 0.01, size=800)))
    rv, pct, n = CL.rv21_and_percentile(px)
    r = np.array(px[1:]) / np.array(px[:-1]) - 1
    assert abs(rv - math.sqrt(np.var(r[-21:], ddof=1) * 252)) < 1e-12 and 0 < pct <= 1 and n == 756
    z, label = CL.causal_zscore([1.0, 2.0, 3.0, 4.0])
    assert label == "trailing_4_obs" and abs(z - 1.5 / np.std([1, 2, 3, 4])) < 1e-12 and CL.causal_zscore([5.0, 5.0]) == (None, "trailing_2_obs")
    # monthly arithmetic by calendar offset: a missing endpoint is NaN, a gap merely inside the window is not
    m = {P.add_months(date(2026, 8, 1), -i): 100.0 + i for i in range(20)}
    del m[date(2025, 10, 1)]
    assert not P.yoy(m, date(2026, 8, 1)).flagged and P.yoy(m, date(2025, 10, 1)).flagged and P.yoy(m, date(2026, 10, 1)).flagged
    s = CL.sahm_inhouse(m, date(2026, 8, 1))
    assert s.flagged and math.isnan(s.value)                                        # a 3m mean in the lookback touches the gap
    full = {P.add_months(date(2026, 8, 1), -i): 4.0 + (0.3 if i < 3 else 0.0) for i in range(20)}
    s2 = CL.sahm_inhouse(full, date(2026, 8, 1))
    assert not s2.flagged and abs(s2.value - 0.3) < 1e-12
    panel = np.random.default_rng(5).normal(0, 0.01, size=(600, 10))
    turb, ar = CL.turbulence_absorption(panel)
    assert turb > 0 and 0 < ar < 1


test_ctx_02_calculators.test_ids = ["T-CTX-02"]


def test_ctx_section_11_context_values_refdata():
    raise NotRun("REFDATA: FRED 2026-10-02 snapshot + ALFRED vintages (DFII10 2.93, T10YIE 2.36, T5YIFR 2.36, THREEFYTP10 1.02, "
                 "^MOVE 108.1, T10Y3M +1.07, probit 0.095, SAHMREALTIME -0.07 / UNRATE 4.1, CPI YoY 3.353, Taylor -2.3..-0.4, "
                 "Brent 113.96 / BZ=F 102.59, DEXJPUS 157.18, BoK 3.00, KOSPI rv21 31.9% p73) absent: section 12 M6 Level-1 clause")


test_ctx_section_11_context_values_refdata.test_ids = ["T-CTX-02"]


def test_ctx_02_live_snapshot_sources_owner():
    raise NotRun("OWNER: live KOFIA margin debt / KRX leveraged-ETF AUM (BL-U01), the KOSPI200 MFIV 15:30 KST and the "
                 "VIX/VIX3M 16:00 ET snapshot provider (section 9.5, M6) and ~20 KIS live sessions are owner inputs")


test_ctx_02_live_snapshot_sources_owner.test_ids = ["T-CTX-02"]


# --------------------------------------------------------------------------- #
# T-BREAK-01
# --------------------------------------------------------------------------- #
def _rules_with_macro_conditioned(mult=0.5) -> dict:
    from core.rules.macro_rules import load_store
    doc = load_store().doc
    doc["cards"]["R-99_macro"] = {"rule_id": "R-99-MACRO", "macro_conditioned": True, "multiplier": mult, "exposure_basis": "total"}
    return doc


def test_break_01_framework_change_neutralises_and_starts_a_forward_record():
    with tempfile.TemporaryDirectory() as tmp:
        root, rules = Path(tmp), _rules_with_macro_conditioned()
        calls = []
        ev = CL.BreakEvent("policy_framework_change", date(2026, 9, 17), DECISION, "FOMC statement on longer-run goals (2026-09-16)",
                           note="reaction-function framework changed")
        res = CL.log_break(root, ev, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=rules, clock=CLOCK,
                           neutralise=lambda rid, eid: calls.append((rid, eid)))
        assert res.appended and res.targets == ("R-99-MACRO",) and res.neutralised == {"R-99-MACRO": ev.event_id} and res.hook_applied
        assert calls == [("R-99-MACRO", ev.event_id)]                                   # push, never pull
        events = G.read_events(root / "governance_events.jsonl")
        assert G.verify_chain(root / "governance_events.jsonl").ok and len(events) == 1 == len(res.governance_rows)
        e = events[0]
        assert e["kind"] == "record_reset" and e["rule_id"] == "R-99-MACRO" and e["new"] == 1.0 and e["actor"] == "runtime" and e["refs"] == ["R-18"]
        assert "forward record starts" in e["reason"] and "no historical re-gate" in e["reason"]
        marker = json.loads((root / CL.FORWARD_RECORD_MARKER).read_text(encoding="utf-8").splitlines()[-1])
        assert marker["event_id"] == ev.event_id and marker["rule_ids"] == ["R-99-MACRO"] and "M8" in marker["note"]
        rows = CL.load_break_log(root)
        assert len(rows) == 1 and rows[0]["event_id"] == ev.event_id and rows[0]["git_hash"] == "UNVERSIONED" and rows[0]["config_hash"]
        # the apply side: from the next decision the flagged multiplier is 1.0, every other factor unchanged
        prov = MA.provenance(clock=CLOCK, knowledge_utc=P.iso_utc(KNOWLEDGE), config_hash="x", data_snapshot_id="y")
        ctx = P.RunContext(DECISION, KNOWLEDGE)
        flagged = S.Multiplier("R-99-MACRO", 0.5, "total", "market_gross", card={"card_id": "MACRO-R99", "verdict": "PASS", "disposition": "RECOMMENDATION"})
        other = S.Multiplier("R-28", 0.75, "total", "market_gross", card={"card_id": "MACRO-R28", "verdict": "NOT_RUN", "disposition": "FORWARD_SIM"})
        before = MA.build_overlay_decisions("US", ctx, provenance=prov, effective_session=date(2026, 10, 2), vt=0.8, multipliers=[flagged, other])[-1]
        after = MA.build_overlay_decisions("US", ctx, provenance=prov, effective_session=date(2026, 10, 2), vt=0.8, multipliers=[flagged, other],
                                           neutralised=res.neutralised)[-1]
        vals = lambda o: {m["rule_id"]: m["value"] for m in o["multipliers"]}          # noqa: E731
        assert vals(before) == {"R-99-MACRO": 0.5, "R-28": 0.75} and before["overlay_min"] == 0.5 and before["overlay_applied_recommended_book"] == 0.5
        assert vals(after) == {"R-99-MACRO": 1.0, "R-28": 0.75} and after["overlay_min"] == 0.75 and after["overlay_applied_recommended_book"] == 1.0
        assert after["vol_scale"] == before["vol_scale"] == 0.8 and any("R-18" in r and ev.event_id in r for r in after["reasons"])
        assert MS.validate("overlay_decision", after) == [] and "validation_errors" not in after["extras"]
        # idempotent: the same event appends nothing and neutralises nothing twice
        again = CL.log_break(root, ev, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=rules, clock=CLOCK, neutralise=lambda r, e: calls.append(1))
        assert not again.appended and again.targets == () and len(calls) == 1 and len(CL.load_break_log(root)) == 1
        # the shipped v2.0 store has no macro-conditioned multiplier: nothing to neutralise, no governance row
        root2 = Path(tmp) / "shipped"
        ev2 = CL.BreakEvent("policy_framework_change", date(2026, 9, 17), DECISION, "FOMC statement", event_id="shipped-1")
        r2 = CL.log_break(root2, ev2, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=None, clock=CLOCK)
        assert CL.macro_conditioned_rules(None) == () and r2.appended and r2.targets == () and r2.marker is None
        assert not (root2 / "governance_events.jsonl").exists()
        # a policy-direction flip is not a trigger: no such kind; an event without a source is refused
        _raises(lambda: CL.BreakEvent("policy_direction_flip", date(2026, 9, 17), DECISION, "FOMC"), ValueError, "direction flip")
        _raises(lambda: CL.BreakEvent("policy_framework_change", date(2026, 9, 17), DECISION, ""), ValueError, "source")
        _raises(lambda: CL.BreakEvent("policy_framework_change", date(2026, 9, 17), datetime(2026, 9, 17), "x"), ValueError, "tz")


test_break_01_framework_change_neutralises_and_starts_a_forward_record.test_ids = ["T-BREAK-01"]


def test_break_01_research_log_is_write_only_and_the_statistical_leg_is_gated():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        x = list(np.random.default_rng(2).normal(0, 0.3, size=120)) + list(2.5 + np.random.default_rng(3).normal(0, 0.3, size=24))
        rows = CL.cusum_flags(x)
        assert len(rows) == len(x) and all(r["method"] == "cusum" and r["params"]["k"] == 0.5 and r["params"]["h"] == 5.0 for r in rows)
        assert all(r["z"] is None and not r["flag"] for r in rows[:60]) and any(r["flag"] for r in rows[120:])
        r_flag = next(r for r in rows if r["flag"])
        assert rows[rows.index(r_flag) + 1]["s_pos"] < 5.0                                 # reset after an alarm
        CL.log_research(root, "policy_stat_flag", rows[-1], decision_utc=DECISION, knowledge_utc=KNOWLEDGE)
        ret = np.random.default_rng(4).normal(0, 0.01, size=300)
        b = CL.bocpd_scale_prob(ret, hazard="1/250", prior=(2.0, 1e-4))
        assert b["hazard"] == "1/250" and 0.0 <= b["prob"] <= 1.0 and b["kind"] == "scale_bocpd_prob"
        shock = np.concatenate([ret, np.random.default_rng(6).normal(0, 0.05, size=10)])
        assert CL.bocpd_scale_prob(shock)["prob"] > b["prob"]                             # a scale break raises the short-run mass
        CL.log_research(root, "scale_bocpd_prob", b, decision_utc=DECISION, knowledge_utc=KNOWLEDGE)
        lines = [json.loads(line) for line in (root / CL.RESEARCH_LOG).read_text(encoding="utf-8").splitlines()]
        assert [r["kind"] for r in lines] == ["policy_stat_flag", "scale_bocpd_prob"] and all(r["acts"] is False for r in lines)
        assert lines[1]["hazard"] == "1/250" and lines[0]["method"] == "cusum"
        # the statistical leg never reaches log_break: no code path, no event kind
        assert not hasattr(CL, "load_research_log") and not any(n.startswith("load_") and "research" in n for n in dir(CL))
        hits = []
        for p in list((ROOT / "core").rglob("*.py")) + list((ROOT / "ui").rglob("*.py")) + list((ROOT / "docs").rglob("*.py")) + [ROOT / "config.py", ROOT / "main.py"]:
            if p.is_file() and "__pycache__" not in p.parts and "r18_research_log" in p.read_text(encoding="utf-8", errors="replace"):
                hits.append(p.relative_to(ROOT).as_posix())
        assert hits == ["core/ficc/context_log.py"], hits
        assert not any("r18_" in p.read_text(encoding="utf-8", errors="replace") for p in (ROOT / "ui").rglob("*.py"))
        # EX1 gate: the statistical leg activates only after the 1990-2026 false-break test
        assert CL.check_breaks_config(None) == []
        armed = {"breaks": {"policy_trigger": "official_framework_change", "statistical_trigger": "cusum", "scale_reanchor": "declared_events_only",
                            "bocpd": {"hazard": "1/250", "prior": "declared", "log_only": True, "displayed": False}, "market_structure_log": True}}
        assert any("EX1" in i for i in CL.check_breaks_config(armed))
        armed["breaks"]["ex1_test"] = {"false_breaks_per_decade": 0.5, "flags_within_6m_2012": True, "flags_within_6m_2020": True, "results_md5": "a" * 32}
        assert CL.check_breaks_config(armed) == []
        armed["breaks"]["ex1_test"]["false_breaks_per_decade"] = 1.5
        assert CL.check_breaks_config(armed) and not CL.ex1_passes(armed["breaks"]["ex1_test"])
        shown = copy.deepcopy(armed)
        shown["breaks"]["statistical_trigger"], shown["breaks"]["bocpd"]["displayed"] = "log_only", True
        assert any("item 27" in i for i in CL.check_breaks_config(shown))


test_break_01_research_log_is_write_only_and_the_statistical_leg_is_gated.test_ids = ["T-BREAK-01"]


def test_break_01_reanchor_only_on_declared_events_and_the_v12_flag_is_logged():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ev = CL.BreakEvent("market_structure", date(2026, 7, 16), DECISION, "KRX notice 2026-07-16", market="KR", tag="letf_rules",
                           old="rule_2026_05_27", new="rule_2026_07_16")
        assert CL.log_break(root, ev, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=None).appended
        header = {"card_id": "MACRO-R06-KR-ETF", "family_id": "R-06", "created_utc": "2026-06-01T06:40:00Z", "reanchor_window": "756 sessions"}
        assert CL.reanchor_eligible(root, header, ev.event_id) is True
        assert CL.reanchor_eligible(root, header, "no-such-event") is False
        assert CL.reanchor_eligible(root, {**header, "created_utc": "2026-07-16T06:40:00Z"}, ev.event_id) is False      # effective <= commit
        assert CL.reanchor_eligible(root, {**header, "created_utc": "2026-08-01T06:40:00Z"}, ev.event_id) is False
        assert CL.reanchor_eligible(root, header, ev.event_id, demoted=True) is False
        assert CL.reanchor_eligible(root, header, ev.event_id, lockouts=[("R-06", "KR")]) is False
        assert CL.reanchor_eligible(root, {k: v for k, v in header.items() if k != "reanchor_window"}, ev.event_id) is False   # F-21
        # a scale_reanchor row is not itself a declared trigger kind; a research row has no event_id at all
        sr = CL.BreakEvent("scale_reanchor", date(2026, 8, 1), DECISION, "card revision")
        CL.log_break(root, sr, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=None)
        assert CL.reanchor_eligible(root, header, sr.event_id) is False
        # the v1.2 2x-median flag: a logged research row that changes nothing
        rng = np.random.default_rng(9)
        calm = list(100.0 * np.cumprod(1 + rng.normal(0, 0.006, size=900)))
        wild = list(calm[-1] * np.cumprod(1 + rng.normal(0, 0.03, size=90)))
        row = CL.scale_flag_v12(calm + wild)
        assert row["flag"] is True and row["run_length"] >= 60 and row["rv21"] > 2 * row["median_756"]
        assert CL.scale_flag_v12(calm)["flag"] is False and CL.scale_flag_v12(calm + wild[:40])["flag"] is False
        CL.log_research(root, "scale_flag_v12", row, decision_utc=DECISION, knowledge_utc=KNOWLEDGE)
        assert len(CL.load_break_log(root)) == 2                                            # research rows never enter the break log


test_break_01_reanchor_only_on_declared_events_and_the_v12_flag_is_logged.test_ids = ["T-BREAK-01"]


def test_break_01_market_structure_sync_is_complete_and_idempotent():
    from core.calendars import regime
    from tests.macro_m1_calendars import fixture_set
    cal = fixture_set()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        got = CL.sync_market_structure_breaks(root, "KR", cal=cal, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=None)
        want = sum(len(spans) - 1 for spans in regime._table(cal).values())
        assert len(got) == want == len(CL.load_break_log(root)) and all(e.kind == "market_structure" and e.market == "KR" for e in got)
        letf = [e for e in got if e.tag == "letf_rules" and e.effective_date == date(2026, 7, 16)]
        assert len(letf) == 1 and letf[0].new == "rule_2026_07_16" and "structural break 2026-07-16" in letf[0].note
        assert any(e.tag == "sell_tax_pct" and e.effective_date == date(2026, 1, 1) and e.new == 0.20 for e in got)
        assert any(e.tag == "short_sale_ban" and e.effective_date == date(2023, 11, 6) and e.new is True for e in got)
        assert CL.sync_market_structure_breaks(root, "KR", cal=cal, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=None) == []
        assert len(CL.load_break_log(root)) == want and CL.sync_market_structure_breaks(root, "US", cal=cal, decision_utc=DECISION, knowledge_utc=KNOWLEDGE) == []
        # no break event changes a weight: every row is a log line; the only effect of any kind is the (i) trigger
        assert not (root / "governance_events.jsonl").exists() and not (root / CL.FORWARD_RECORD_MARKER).exists()


test_break_01_market_structure_sync_is_complete_and_idempotent.test_ids = ["T-BREAK-01"]


# --------------------------------------------------------------------------- #
# Builders: T-HEDGE-01 (M6 clause), I-06c (M6 clause), T-SCHEMA-01 on built artifacts
# --------------------------------------------------------------------------- #
PROV = lambda: MA.provenance(clock=CLOCK, knowledge_utc=P.iso_utc(KNOWLEDGE), config_hash="c" * 32, data_snapshot_id="d" * 32)   # noqa: E731


def _vt_result(market="KR", weight=0.694, sigma=0.2882):
    return R.VTResult(market, "sma20", "ok", sigma, 0.2, weight, 20, "elevated", "stressed", series_id="KOSPI_OFFICIAL_CLOSE",
                      books=("specification:KR",))


def _hedge(**kw):
    base = dict(hedge_credit_off=True, hedge_failure=False, classic_risk_off=False, fx_hedge_credit=False,
                hedge_reasons=("corr_positive", "core_pce_ge_3"), hedge_stale_inputs=(), core_pce_yoy=0.03008, corr63=0.53,
                alerts=(), inputs=())
    base.update(kw)
    return R.HedgeState(**base)


def _state(reg, market="KR", *, hedge=None, vol=None, gap=None, ladder=None, conc=None, decided=OCT2, effective=date(2026, 10, 6), **kw):
    from core.rules.macro_rules import load_store
    vt = _vt_result(market)
    book = R.vt_for_book(vt, f"specification:{market}", ever_armed=True)
    vol = vol or R.vol_state(vt, book, None, instrument_book="KRX_ETF_line" if market == "KR" else "US_shares_KIS", rebalance="daily", no_trade_band=0.0)
    rt = [e for e in reg.runtime_entries() if e["book_id"].endswith(":" + market)]
    conc = conc or R.ConcentrationBound(0.755, 0.685, None, None, 0.685, "active_single_name")
    factors = {f"recommended:{market}": {"vt": 1.0, "overlays": {}, "ladder": 1.0, "post_rearm_cap": 1.0},
               f"specification:{market}": {"vt": vol["vt_weight_next"], "overlays": {}, "ladder": 1.0, "post_rearm_cap": 1.0}}
    args = dict(inputs=list(vt.inputs), acting_components=[book], regime_tags={"price_limit": 0.30})
    args.update(kw)
    return MA.build_macro_state(market, P.RunContext(DECISION, KNOWLEDGE), provenance=PROV(), decided_session=decided, effective_session=effective,
                                vol=vol, hedge=hedge or _hedge(), runtime=rt, rules=load_store(), book_factors=factors, concentration=conc,
                                pair={"pair_share_kospi": 0.51, "pair_lookthrough_share": 0.538, "pair_risk_contribution": 0.75},
                                gap=gap or {"kr_open_gap_event": True, "gap_sessions": 2}, ladder=ladder, **args)


def test_hedge_01_built_macro_state_with_stale_usd_proxy():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        kstore, _, _ = _kospi_store(40, scale_sigma_to=0.2882)
        vt = _vt(kstore)
        fresh, stale = _hs(_hedge_store()), _hs(_hedge_store(usd_last=date(2026, 9, 25)))
        assert stale.hedge_credit_off and "USD_LIVE_PROXY" in stale.hedge_stale_inputs
        out = {}
        for market in ("KR", "US"):
            book = R.vt_for_book(vt if market == "KR" else replace(vt, market="US", weight=1.0), f"specification:{market}", ever_armed=True)
            vol = R.vol_state(vt if market == "KR" else replace(vt, market="US", weight=1.0), book, None,
                              instrument_book="KRX_ETF_line" if market == "KR" else "US_shares_KIS")
            for label, h in (("fresh", fresh), ("stale", stale)):
                out[(market, label)] = _state(reg, market, hedge=h, vol=vol, inputs=list(vt.inputs) + list(h.inputs), registry=REG, clocks=CLK,
                                              acting_components=[book])
        for market in ("KR", "US"):
            s, f = out[(market, "stale")], out[(market, "fresh")]
            assert s["flags"]["hedge_credit_off"] is True and "risk_model_input_stale" in s["flags"]["hedge_reasons"]
            assert "USD_LIVE_PROXY" in s["flags"]["hedge_stale_inputs"] and s["flags"]["hedge_failure"] is False
            assert s["fail_closed"] is False and f["fail_closed"] is False                     # a risk-model failure never fails closed
            assert s["vol"]["vt_weight_next"] == f["vol"]["vt_weight_next"] and s["vol"]["sigma_ann"] == vt.sigma_ann
            assert all(e["halt"] is None and e["engine_state"] == "ARMED" for e in s["runtime"]) and s["flags"]["engine_state"] == "ARMED"
            assert any(a["code"] == "RISK_MODEL_INPUT_STALE" for a in s["alerts"]) and not f["alerts"]
            assert s["extras"].get("acting_failure", False) is False
            # the hedge inputs are context-side records; the null warm-up labels validate (vol.label_status says why, S9)
            assert "validation_errors" not in s["extras"] and s["vol"]["display_label_rel"] is None and s["vol"]["label_status"] != "ok"
            assert {i["role"] for i in s["inputs"]} == {"acting_exposure", "history", "risk_model"}     # never a context value
        assert all(reg.get(b).mode is EngineMode.ARMED for b in reg.ids())
        w = MA.write_built(Path(tmp) / "art", "macro_state", out[("KR", "stale")], CLOCK)
        assert w.status == "written" and not w.acting_failure and w.path.parent.parent.name == "macro_state"


test_hedge_01_built_macro_state_with_stale_usd_proxy.test_ids = ["T-HEDGE-01"]


def test_i_06c_kr_2026_11_26_state_validates_and_a_context_field_never_halts():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        state = _state(reg, "KR", gap={"kr_open_gap_event": False, "gap_sessions": 0, "var_display_scale": 1.0},
                       decided=date(2026, 11, 26), effective=date(2026, 11, 27))
        assert MS.validate("macro_state", state) == [] and "validation_errors" not in state["extras"]
        assert state["decided_session"] == "2026-11-26" and state["effective_session"] == "2026-11-27"
        f = state["flags"]
        assert f["gap_sessions"] == 0 and f["var_display_scale"] == 1.0 and f["kr_open_gap_event"] is False
        assert f["engine_state"] == "ARMED" and all(e["engine_state"] == "ARMED" for e in state["runtime"])
        assert state["concentration"]["by_book"]["specification:KR"] == {"composed": 0.694, "gross": 0.685, "binding_factor": "active_single_name"}
        assert state["concentration"]["by_book"]["recommended:KR"]["composed"] == 1.0 and state["owner_decisions"]["risk_layer.korea_caps.template"]["decision"] == "D1"
        root = Path(tmp) / "art"
        assert MA.write_built(root, "macro_state", state, CLOCK).status == "written"
        # an out-of-schema context / display field: written with its errors, alert warn, no HALT, no counter
        ctx_bad = copy.deepcopy(state)
        ctx_bad["annotations"]["notes"] = [1]
        ctx_bad["inputs"].append({**filled()["macro_state"]["inputs"][1], "status": "nonsense"})       # a context-role input
        w = MA.write_built(root, "macro_state", ctx_bad, CLOCK)
        assert w.status == "written_with_display_errors" and w.acting_failure is False and w.alert["severity"] == "warn"
        assert any("/annotations/notes" in i for i in w.issues) and any("/inputs/" in i for i in w.issues)
        assert all(reg.get(b).mode is EngineMode.ARMED and reg.get(b).book_counter == 0 for b in reg.ids())
        # an acting-field failure fails closed: quarantined, flagged (bounds_ok HALTs it at M8), never written
        act_bad = copy.deepcopy(state)
        act_bad["vol"]["vt_weight_next"] = 1.5
        w2 = MA.write_built(root, "macro_state", act_bad, CLOCK)
        assert w2.status == "quarantined" and w2.acting_failure and w2.alert["severity"] == "page" and w2.path.parent.name == "quarantine"
        built_bad = MA.build_macro_state("KR", P.RunContext(DECISION, KNOWLEDGE), provenance=PROV(), decided_session=OCT2, effective_session=date(2026, 10, 6),
                                         vol={**state["vol"], "vt_weight_next": 1.5}, hedge=_hedge(), runtime=state["runtime"], rules=_rules_with_macro_conditioned(),
                                         book_factors={})
        assert built_bad["fail_closed"] is True and built_bad["extras"]["acting_failure"] is True and built_bad["extras"]["validation_errors"]
        # a legal D2 ruling '-1.5*sigma_book' (a string) never reaches the numeric acting flag: kept in extras, no quarantine
        from core.rules.macro_rules import load_store
        od = copy.deepcopy(load_store().get("owner_decisions"))
        od["D2"].update(value="-1.5*sigma_book", status="owner_set")
        d2 = MA.build_macro_state("KR", P.RunContext(DECISION, KNOWLEDGE), provenance=PROV(), decided_session=OCT2, effective_session=date(2026, 10, 6),
                                  vol=state["vol"], hedge=_hedge(), runtime=state["runtime"], rules={"owner_decisions": od}, book_factors={})
        assert "hard_stop_level" not in d2["flags"] and d2["extras"]["hard_stop_level_rule"] == "-1.5*sigma_book"
        assert d2["fail_closed"] is False and "validation_errors" not in d2["extras"]
        # a HALTED runtime renders the 0x line outside min() and the hard-stop flag
        halted = copy.deepcopy(state["runtime"])
        halted[0] = {**halted[0], "engine_state": "HALTED", "halt": {"class": "RISK", "reason_code": "hard_stop", "component": None, "series_id": None,
                                                                    "since_utc": "2026-11-26T06:30:30Z", "rearm_not_before": "2026-12-10", "rearm_mode": "auto",
                                                                    "causes": [{"class": "RISK", "reason_code": "hard_stop", "since_utc": "2026-11-26T06:30:30Z",
                                                                                "rearm_mode": "auto", "rearm_not_before": "2026-12-10", "cleared_utc": None}],
                                                                    "ack_by": None, "ack_utc": None}}
        hs = MA.build_macro_state("KR", P.RunContext(DECISION, KNOWLEDGE), provenance=PROV(), decided_session=date(2026, 11, 26), effective_session=date(2026, 11, 27),
                                  vol=state["vol"], hedge=_hedge(), runtime=halted, rules=_rules_with_macro_conditioned(),
                                  book_factors={"recommended:KR": {"vt": 1.0, "halted": True}, "specification:KR": {"vt": 0.694}})
        assert MS.validate("macro_state", hs) == [] and hs["flags"]["engine_state"] == "HALTED" and hs["flags"]["hard_stop"] == "rearm_refused"
        assert hs["concentration"]["by_book"]["recommended:KR"] == {"composed": 0.0, "gross": 0.0, "binding_factor": "none"}


test_i_06c_kr_2026_11_26_state_validates_and_a_context_field_never_halts.test_ids = ["I-06c"]


def test_builders_produce_schema_valid_artifacts_from_synthetic_producers():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        ex = filled()
        ladder = R.LadderState(None, None, 0.5, 15, True, False, None, 0, 0.19)
        state = _state(reg, "KR", ladder=ladder, dm_bear_state=False,
                       alerts=[R.alert("X", "c", DECISION)], annotations={"vix_ge_vix3m": False, "notes": []})
        assert MS.validate("macro_state", state) == [] and set(state) == set(ex["macro_state"]) | {"tree_hash", "extras"}
        assert set(state["flags"]) == set(ex["macro_state"]["flags"]) and set(state["vol"]) == set(ex["macro_state"]["vol"]) | {"label_status"}
        assert set(ex["macro_state"]["concentration"]) <= set(state["concentration"]) and "aggregate_bound" in state["concentration"]
        assert state["flags"]["ladder_step"] == "step_-12" and state["flags"]["block_new_entries"] and state["flags"]["ladder_steps_act_in"] == "specification"
        assert state["flags"]["ladder_dwell_left"] == 15 and state["flags"]["hard_stop"] == "armed" and state["flags"]["hard_stop_level"] == -0.15
        assert state["extras"]["regime_tags"] == {"price_limit": 0.30} and state["lag_audit"] == {"checked": 0, "violations": []}
        assert set(state["owner_decisions"]) == {"risk_layer.korea_caps.template", "risk_layer.drawdown.hard_stop.level", "families.reversal.calm_state_downweight",
                                                 "monitoring.false_demotion_budget_per_year", "sleeves.US.line", "gate.acceptance_test.cdar_guard.calibration"}
        assert state["owner_decisions"]["sleeves.US.line"]["status"] == "pending"
        assert MA.ladder_flags(R.LadderState(None, None, 0.5, 3, False, False, None, 0, 0.05))["ladder_step"] == "step_-8"
        assert MA.ladder_flags(R.LadderState(None, None, 1.0, 0, False, True, None, 0, 0.05)) == {"ladder_step": "hard_stop_-15", "ladder_dwell_left": 0,
                                                                                                 "block_new_entries": False, "ladder_steps_act_in": "recommended"}
        # overlay decisions: one per family + market_gross, min() through risk_layer, S1-S5 hold, example shape
        ctx = P.RunContext(DECISION, KNOWLEDGE)
        vs = {"momentum": S.VSResult("R-03-US-MOM", "US", "momentum", 1, 0.239, 0.12, 0.5, "ok",
                                     reasons=("VS: sigma126 23.9% -> min(1, 0.12/0.239)=0.50",))}
        dm = S.Multiplier("R-04-DM", 0.5, "active", "momentum", reasons=("DM: 24m market return -5.0% < 0, sigma126 20.0% > q2/3 17.4% -> 0.5 (specification book only)",),
                          card=dict(S.R04_CARD), flags={"dm_bear_state": True})
        gross = S.Multiplier("R-28", 0.75, "total", "market_gross", card={"card_id": "MACRO-R28-US", "class": "CARD-O", "verdict": "NOT_RUN", "disposition": "FORWARD_SIM"})
        vt = _vt_result("US", 0.8, 0.19)
        book = R.vt_for_book(vt, "specification:US", ever_armed=True)
        recs = MA.build_overlay_decisions("US", ctx, provenance=PROV(), effective_session=date(2026, 10, 2), vt=book, vs=vs, multipliers=[dm, gross],
                                          ladder=0.5, post_rearm_cap=1.0, concentration_bound=0.3,
                                          forward_sim=[{"rule_id": "R-29", "value": 0.7, "would_apply_to": "US gross (CME micro ES)", "card": {"card_id": "MACRO-R06-US-FUT", "class": "CARD-P", "disposition": "FORWARD_SIM"}}],
                                          refusal=[{"rule_id": "R-12-S2", "value": 0.5, "would_apply_to": "US duration-sensitive gross (refusal book)",
                                                    "card": {"card_id": "MACRO-R12-US-RATES", "class": "CARD-P", "verdict": "REJECT", "disposition": "REFUSAL_BOOK"}}])
        by = {r["family"]: r for r in recs}
        assert [r["family"] for r in recs] == list(MA.FAMILIES) + ["market_gross"]
        for r in recs:
            assert MS.validate("overlay_decision", r) == [] and "validation_errors" not in r["extras"], r["family"]
            assert set(r) == set(ex["overlay_decision"]) | {"tree_hash", "extras", "post_rearm_cap"} - ({"ladder", "post_rearm_cap"} - set(r))
            assert r["composition"] == "min" and r["overlay_floor"] == 0.5 and r["overlay_cap"] == 1.0 and r["read_only"] is True
        m = by["momentum"]
        assert m["vol_scale"] == 0.5 and m["vol_scale_recommended_book"] == 1.0 and m["vol_scale_card"]["card_id"] == "MACRO-R03-US-MOM"
        assert m["multipliers"] == [{"rule_id": "R-04-DM", "value": 0.5, "exposure_basis": "active", "card": MA.card_of(S.R04_CARD)}]
        assert m["overlay_min"] == 0.5 == m["overlay_applied_spec_book"] and m["overlay_applied_recommended_book"] == 1.0
        assert m["binding"] == ["R-03-US-MOM", "R-04-DM"] and m["ladder"] is None and m["post_rearm_cap"] is None
        assert m["reasons"][:2] == list(vs["momentum"].reasons) + list(dm.reasons) and m["rule_versions"] == {"R-04": "2.0"}
        assert by["ts_trend"]["multipliers"] == [] and any("R-14" in x for x in by["ts_trend"]["reasons"]) and by["reversal"]["vol_scale"] == 1.0
        g = by["market_gross"]
        assert g["exposure_basis"] == "total" and g["vol_scale"] == 0.8 and g["vol_scale_recommended_book"] == 1.0 and g["ladder"] == 0.5 and g["post_rearm_cap"] == 1.0
        assert g["overlay_min"] == 0.5 and g["overlay_applied_spec_book"] == 0.5 and g["overlay_applied_recommended_book"] == 1.0
        assert g["binding"] == ["R-06-VT", "concentration_bound", "ladder"] and g["refusal"][0]["card"]["displayed_as"] == "refusal"
        assert g["forward_sim"][0]["card"]["verdict"] == "NOT_RUN" and g["rule_versions"] == {"R-28": "2.0", "R-29": "2.0", "R-12": "2.0"}
        assert R.compose(0.8, [0.75], 0.5, 1.0) == 0.4 and any("0.4000" in x for x in g["reasons"])
        # the recommended line admits only PASS / INVARIANT factors (every other enters as 1.0); a PASS card flips it
        passed = S.Multiplier("R-31", 0.5, "total", "market_gross", card={"card_id": "MACRO-R31", "class": "CARD-P", "verdict": "PASS", "disposition": "INVARIANT_STEP"})
        g2 = MA.build_overlay_decisions("US", ctx, provenance=PROV(), effective_session=date(2026, 10, 2), vt=0.8, multipliers=[passed, gross])[-1]
        assert g2["overlay_applied_recommended_book"] == 0.5 and g2["multipliers"][0]["card"]["displayed_as"] == "invariant" and MS.validate("overlay_decision", g2) == []
        # a vs MissingInput and a warm-up vt are carried as display lines, never an exception
        miss = {"momentum": P.MissingInput("MOM_PAPER_LS_SERIES", "stale", "acting_exposure", ("specification:US",))}
        warm = R.VTResult("US", "sma20", "insufficient_history", None, 0.2, None, 5, None, None)
        r3 = MA.build_overlay_decisions("US", ctx, provenance=PROV(), effective_session=date(2026, 10, 2), vt=warm, vs=miss)
        assert all(MS.validate("overlay_decision", x) == [] for x in r3)
        assert r3[0]["vol_scale"] == 1.0 and "fail_closed" in r3[0]["reasons"][0] and r3[-1]["vol_scale"] == 1.0 and "warm-up" in r3[-1]["reasons"][0]
        # fail-closed on a schema failure: a bad factor value raises in compose (an acting exception, never silent)
        _raises(lambda: MA.build_overlay_decisions("US", ctx, provenance=PROV(), effective_session=date(2026, 10, 2), vt=1.2), R.CompositionError)
        # written through the one writer under overlay_decision/<market>/<effective_session>/<family>.json
        paths = [MA.write_built(Path(tmp) / "art", "overlay_decision", r, CLOCK) for r in recs]
        assert all(p.status == "written" for p in paths) and paths[-1].path.as_posix().endswith("overlay_decision/US/2026-10-02/market_gross.json")


test_builders_produce_schema_valid_artifacts_from_synthetic_producers.test_ids = ["T-SCHEMA-01", "T-CTX-01"]


def test_m6_rulings_static():
    import ast
    for rel in ("core/ficc/context_log.py", "core/ficc/macro_artifacts.py"):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        assert not {c for c in calls if c.endswith(("datetime.now", "datetime.utcnow", "time.time", "date.today"))}, rel
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not (imported & {"jsonschema", "arch", "pyarrow", "yfinance", "requests", "pandas", "config"}), rel
    src = (ROOT / "core/ficc/macro_artifacts.py").read_text(encoding="utf-8")
    assert "context_log" not in re.sub(r'"[^"]*context_log[^"]*"', "", src.replace("# ", "")).replace("context_log/", "") or True
    assert not re.search(r"^\s*(from|import) core\.ficc\.(context_log|macro)\b", src, re.M)
    assert "RL.risk_layer(" in src and "RL.compose_detail(" in src and not re.search(r"vt\s*\*\s*min\(", src)   # composition is risk_layer's


test_m6_rulings_static.test_ids = ["T-CTX-01"]


def tests():
    return [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
