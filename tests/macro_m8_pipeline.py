"""M8 package A tests: the macro_daily pipeline, its three gates, the verdict filter, the run log, missed decisions,
alerts, replay, the app-start hook and the labelled dry run (core/skills/{pipeline,macro_daily,alerts}.py,
core/skills/macro_workflows/macro_daily.yaml, main.py hook; TASK-M8-01..07, the pipeline side of M8-08/12/13).

Spec tests: I-01 (mechanics; the golden clauses NOT_RUN REFDATA), I-03, I-06c (bounds_ok clause), T-SCOPE-01 (a)-(h),
T-ROLE-02 (M8 clause), T-OBS-01..05, T-CARD-03, T-REPLAY-01, T-CLOSE-01 (workflow clause), T-RO-02 (I-01 clause).
Hermetic: synthetic PIT stores (the S2 StubClocks and the shipped registry), the signed fixture calendar, temp
registries, macro dirs and card roots; nothing under ~/.nextgen; the local vendor cache is read, never written.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import tempfile
import time
from dataclasses import replace
from types import SimpleNamespace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.engine import books as B
from core.engine.state import EngineMode
from core.ficc import macro_schema as MS
from core.ficc import pit as P
from core.quant import cards as CARDS
from core.quant import risk_layer as R
from core.rules import governance as G
from core.rules import macro_rules as M
from core.skills import alerts as AL
from core.skills import macro_daily as MD
from core.skills import pipeline as PL
from tests.macro_m0_schemas import synthetic_card
from tests.macro_m1_calendars import fixture_set
from tests.macro_m1_pit import CLK, REG
from tests.macro_m2_risk import OCT2, _close_row, _hedge_store, _kospi_store, _sessions
from tests.macro_m5_books import BASKET, LINE, _raises, _registry
from tests.macro_m5_fills_events import _event
from tests.macro_m7_cards import _store as _frozen_store
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
REC, SPEC = "recommended:KR", "specification:KR"
UREC, USPEC = "recommended:US", "specification:US"
NFP = _event("US-NFP-2026-10-02", "US_NFP", "2026-10-02T12:30:00Z")
M8_MODULES = ("core/skills/pipeline.py", "core/skills/macro_daily.py", "core/skills/alerts.py")
CAPS = (("KRX_005930_MARKET_CAP", 5.0e14), ("KRX_000660_MARKET_CAP", 2.0e14), ("KOSPI_TOTAL_MARKET_CAP", 2.9e15))


def U(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=UTC)


def _tmp(prefix="m8_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _dec(market: str, d: date) -> datetime:
    return CLK.close_print_bound_utc(market, d)


# --------------------------------------------------------------------------- #
# Fixtures: a KR store with every acting input the KR books read, the hedge rows, the signed calendar
# --------------------------------------------------------------------------- #
def kr_rows(days, px=None, *, caps=True, kodex=True, nav=True) -> list[dict]:
    rows = []
    for i, d in enumerate(days):
        v = (px[i] if px is not None else 3000.0) * 10.0
        if nav:
            rows.append(_close_row("KRX_069500_OFFICIAL_CLOSE", d, v, market="KR"))
        if caps:
            for sid, val in CAPS:
                rows.append(_close_row(sid, d, val, market="KR"))
        if kodex:
            due = CLK.publication_instant("KODEX200_PDF", d)
            rows.append(P.stamp_release("KODEX200_PDF", d, 1.0, retrieved_at_utc=due + timedelta(minutes=5), source="KIS",
                                        registry=REG, clocks=CLK))
    return rows


def kr_store(n: int = 40, *, hedge=True, spx=True, extra_sessions=()):
    """KOSPI closes (rv20 28.82%) + the NAV line, the market caps and the KODEX basket row on every session
    (and on `extra_sessions` without a KOSPI close), plus the risk-model rows of the hedge store."""
    store, days, px = _kospi_store(n, scale_sigma_to=0.2882)
    rows = kr_rows(days, px) + kr_rows(list(extra_sessions), [px[-1]] * len(extra_sessions))
    if hedge:
        hs = _hedge_store()
        for sid in hs.series_ids():
            if sid == "SPX_OFFICIAL_CLOSE" and not spx:
                continue
            rows += hs.rows(sid)
    store.append(rows)
    return store


def services(tmp: Path, store, clock, *, reg=None, cal=None, events=(), nav=None, **hooks) -> MD.Services:
    reg = reg or _registry(tmp)
    clock = clock or (lambda: _dec("KR", OCT2) + timedelta(minutes=30))      # `run` pins the decision's clock
    return MD.default_services(tmp, clock, store=store, registry=REG, clocks=CLK, cal=cal, events=events, book_registry=reg,
                               baskets={LINE: R.Basket(LINE, date(2026, 10, 1), BASKET)},
                               nav=nav or (lambda ctx, b: 100.0), **hooks)


def run(s: MD.Services, market: str, d: date, **kw) -> dict:
    s.clock = lambda: _dec(market, d) + timedelta(minutes=30)      # noqa: E731
    return MD.run_decision(s, market, d, **kw)


def step(rec: dict, name: str) -> dict:
    return next(x for x in rec["steps"] if x["name"] == name)


def artifacts(tmp: Path, rec: dict) -> dict[str, dict]:
    return {rel: json.loads((tmp / rel).read_text(encoding="utf-8")) for rel in rec["artifacts"]}


def state_of(tmp: Path, rec: dict) -> dict:
    return next(v for k, v in artifacts(tmp, rec).items() if k.startswith("macro_state/"))


# --------------------------------------------------------------------------- #
# The YAML, the strict loader, the legacy parser untouched, no wall clock in the M8 modules
# --------------------------------------------------------------------------- #
def test_yaml_loads_with_the_strict_runner_and_the_legacy_parser_is_untouched():
    p = MD.load_macro_pipeline()
    assert p.name == "macro_daily" and p.run_mode == "live" and p.runs == (("after_close", "KRX"), ("after_close", "NYSE"))
    assert p.step_names == ("macro.pit_snapshot", "data_ok", "macro.lag_audit", "macro.vol_and_overlays", "macro.build_artifacts",
                            "bounds_ok", "verdict_filter", "macro.engine_feed", "macro.forward_books", "macro.forward_monitor",
                            "macro.brief", "macro.run_record")
    assert [s.kind for s in p.steps].count("gate") == 3 and PL.ACTING_STEPS == p.step_names[:7]
    assert not (MD.YAML_PATH.parent / "__init__.py").exists()            # a data directory, never a package (F-3)
    import core.skills.workflows as W
    assert W.__file__.endswith("workflows.py") and callable(W.all_workflows) and hasattr(W, "Step")
    tmp = _tmp()
    bad = {"unknown key": "name: x\nruns: []\nrun_mode: live\nextra: 1\nsteps:\n  - skill: macro.brief\n",
           "unregistered step": "name: x\nrun_mode: live\nsteps:\n  - skill: macro.nope\n",
           "gate named as skill": "name: x\nrun_mode: live\nsteps:\n  - gate: macro.brief\n",
           "run_mode": "name: x\nrun_mode: paper\nsteps:\n  - skill: macro.brief\n",
           "two keys": "name: x\nrun_mode: live\nsteps:\n  - {skill: macro.brief, gate: data_ok}\n"}
    for label, text in bad.items():
        path = tmp / f"{label.replace(' ', '_')}.yaml"
        path.write_text(text, encoding="utf-8")
        _raises(lambda: PL.load_pipeline(path, known_steps=MD.STEPS, known_gates=MD.GATES), PL.PipelineLoadError)
    # rulings 3.11: the only wall clocks are the CLI entry and the app-start default (never a library function)
    for rel in M8_MODULES:
        src = (ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        allowed = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in ("main", "on_app_start"):
                allowed |= set(range(node.lineno, node.end_lineno + 1))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                owner = node.func.value
                name = owner.id if isinstance(owner, ast.Name) else owner.attr if isinstance(owner, ast.Attribute) else ""
                hit = (name in ("datetime", "date") and node.func.attr in ("now", "utcnow", "today")) or (name == "time" and node.func.attr == "time")
                assert not hit or node.lineno in allowed, f"{rel}:{node.lineno}: wall clock in library code"
    assert "anthropic" not in (ROOT / "core/skills/macro_daily.py").read_text(encoding="utf-8").lower()


test_yaml_loads_with_the_strict_runner_and_the_legacy_parser_is_untouched.test_ids = ["T-RO-01"]


# --------------------------------------------------------------------------- #
# T-CLOSE-01 workflow clause: 06:40:29Z refused, 06:40:30Z starts; one artifact per decision
# --------------------------------------------------------------------------- #
def test_close_01_workflow_never_starts_before_06_40_30z_and_one_artifact_per_decision():
    tmp = _tmp()
    s = services(tmp, kr_store(), lambda: U(2026, 10, 2, 6, 40, 29))
    _raises(lambda: MD.run_decision(s, "KR", OCT2), PL.TooEarly, "06:40:30Z")
    assert not (tmp / "run_log.jsonl").exists() and not (tmp / "macro_state").exists()
    s.clock = lambda: U(2026, 10, 2, 6, 40, 30)
    rec = MD.run_decision(s, "KR", OCT2)
    assert rec["status"] == "ok" and rec["run_mode"] == "live" and rec["decision_utc"] == "2026-10-02T06:30:30Z"
    assert rec["knowledge_utc"] == "2026-10-02T06:40:30Z" and (tmp / "macro_state" / "KR" / "2026-10-02.json").exists()
    again = MD.run_decision(s, "KR", OCT2)                                    # a later run of the same decision is a replay (L1199)
    assert again["run_mode"] == "replay" and step(again, "macro.engine_feed")["status"] == "blocked"
    assert len(PL.read_run_log(tmp / "run_log.jsonl")) == 1 and (tmp / "replay" / "KR-2026-10-02" / "run_log.jsonl").is_file()   # audit on scratch state
    _raises(lambda: MD.run_decision(s, "KR", date(2026, 10, 3)), Exception, "2026-10-03")        # NotASession propagates


test_close_01_workflow_never_starts_before_06_40_30z_and_one_artifact_per_decision.test_ids = ["T-CLOSE-01"]


# --------------------------------------------------------------------------- #
# I-01 mechanics (+ the T-RO-02 I-01 clause): five artifacts, gates by role, verdict_filter, engine_feed scope
# --------------------------------------------------------------------------- #
def test_i01_mechanics_five_artifacts_gates_by_role_and_feed_scope():
    from data.krx import kis_client
    calls = []
    saved = kis_client.KISClient._get

    def recorder(self, path, *a, **k):
        calls.append(path)
        raise RuntimeError("transport patched (T-RO-02)")
    kis_client.KISClient._get = recorder
    try:
        tmp = _tmp()
        s = services(tmp, kr_store(), None, cal=fixture_set(), events=(NFP,))
        rec = run(s, "KR", OCT2)
    finally:
        kis_client.KISClient._get = saved
    assert calls == [] and rec["status"] == "ok" and not rec["acting_error"]
    arts = artifacts(tmp, rec)
    kinds = sorted({k.split("/")[0] for k in arts})
    assert kinds == ["context_log", "event_calendar", "macro_state", "overlay_decision"] and sum(k.startswith("overlay_decision/") for k in arts) == 6
    for rel, obj in arts.items():
        kind = rel.split("/")[0]
        ok, issues, acting = MS.check_artifact(kind, obj)
        assert ok and not acting and not issues, (rel, issues)        # null warm-up labels validate (S9 ruling (a))
        assert obj["read_only"] is True and obj["git_hash"] == "UNVERSIONED" and obj["knowledge_utc"] == rec["knowledge_utc"]
    # the cards the artifacts cite: every macro card NOT_RUN today (the registered US card REJECT), display invariant held
    for spec in CARDS.REGISTRY:
        st = CARDS.card_status(MD.CARDS_ROOT, spec.card_id, s.rules)
        assert st["verdict"] in ("NOT_RUN", "REJECT") and not CARDS.check_display_invariant(st["verdict"], st["disposition"], st["displayed_as"])
    state = state_of(tmp, rec)
    gross = next(v for k, v in arts.items() if k.endswith("market_gross.json"))
    # data_ok: a stale risk-model input passes the gate with hedge_credit_off; the acting KOSPI close is fresh
    d_ok = step(rec, "data_ok")
    assert d_ok["status"] == "ok" and d_ok["result"]["status"] in ("pass", "fail_closed") and state["flags"]["hedge_credit_off"] is True
    assert "KOSPI_OFFICIAL_CLOSE" not in [c["series_id"] for c in d_ok["result"]["fail_closed"]]
    assert state["vol"]["vt_status"] == "ok" and abs(state["vol"]["vt_weight_next"] - 0.694) < 0.01
    # verdict_filter: nothing admitted, R-06 KR refused as NOT_RUN; the recommended line stays neutral
    vf = step(rec, "verdict_filter")["result"]
    assert vf["admitted"] == {} and "NOT_RUN" in vf["refused"]["R-06-KR-VT20"] and vf["chain_ok"] and vf["status"] == "pass"
    assert state["vol"]["vt_weight_recommended_book"] == 1.0 and gross["vol_scale_recommended_book"] == 1.0
    assert state["concentration"]["by_book"][REC]["composed"] == 1.0 and abs(state["concentration"]["by_book"][SPEC]["composed"] - 0.694) < 0.01
    assert state["concentration"]["by_book"][REC]["binding_factor"] == "active_single_name" and round(state["concentration"]["by_book"][REC]["gross"], 3) == 0.685
    assert state["flags"]["kr_open_gap_event"] is True and state["flags"]["gap_sessions"] == 2 and state["effective_session"] == "2026-10-06"
    # engine_feed: recommended and specification books only, delivered atomically, never a FORWARD-SIM or refusal book
    feed = step(rec, "macro.engine_feed")["result"]["books"]
    assert set(feed) == {REC, SPEC} and all(v["delivered"] for v in feed.values())
    assert sorted(p.name for p in (tmp / "engine_feed").iterdir()) == ["recommended%3AKR", "specification%3AKR"]
    fb, fm = step(rec, "macro.forward_books")["result"], step(rec, "macro.forward_monitor")["result"]   # the wired hooks (S6): display only
    assert fb["status"] == "ok" and fb["books"] == {"refusal:R-11": 1.0} and "not started" in fb["records"] and fm["status"] == "ok"
    assert state["refusal_books"] == {"S1_krw_flag": None, "S2_rates_flag": None} and [x["rule_id"] for x in gross["refusal"]] == ["R-11-S1"]
    assert B.ledger(s.book_registry, REC)[-1]["post_action"] == {LINE: feed[REC]["post_action"][LINE]}
    # the run row and the brief
    row = PL.read_run_log(tmp / "run_log.jsonl")[-1]
    assert row["run_id"] == rec["run_id"] and row["git_hash"] == "UNVERSIONED" and row["tree_hash"] and row["data_snapshot_id"] == state["data_snapshot_id"]
    assert [x["name"] for x in row["steps"]] == list(MD.load_macro_pipeline().step_names)
    b = step(rec, "macro.brief")["result"]
    assert b["owner_decisions_pending"] == ["D5"] and any("git" in a for a in b["owner_actions"]) and "not called" in b["claude"]


test_i01_mechanics_five_artifacts_gates_by_role_and_feed_scope.test_ids = ["I-01", "T-RO-02"]


def test_i01_golden_clauses_refdata():
    raise NotRun("REFDATA: I-01 golden clauses (L5688): KRX official KOSPI closes incl. 7,003.74 on 2026-10-02 (F01), the KODEX 200 PDF, "
                 "the pair and KOSPI market caps, S&P / DGS10 / core PCE vintages / USD proxy and the signed event calendar are absent; "
                 "vt 0.694 / rv20 28.82% / hedge reasons / gap 2 / bounds 0.755 and 0.685 / vt 0.25 on 2026-07-30 never asserted here")


test_i01_golden_clauses_refdata.test_ids = ["I-01"]


# --------------------------------------------------------------------------- #
# I-03: book separation, static (the assertion) and runtime (the pipeline)
# --------------------------------------------------------------------------- #
def test_i03_book_separation_static_and_runtime():
    FR = MD.FactorRead
    bad_rec = [FR("R-28-US-SMA10M", "NOT_RUN", "FORWARD_SIM", "forward_sim"), FR("R-11-S1", "REJECT", "REFUSAL_BOOK", "refusal"),
               FR("R-03-US-VS12", "INSUFFICIENT_DATA", "SPECIFICATION_ONLY", "recommended"), FR("R-04-DM", "PASS", "RECOMMENDATION", "recommended"),
               FR("R-06-KR-VT20", "NOT_RUN", "SPECIFICATION_ONLY", "recommended"), FR("R-31-KR-STEP", "NOT_RUN", "SPECIFICATION_ONLY", "recommended"),
               FR("R-03-US-VS12", "PASS", "RECOMMENDATION", "specification")]
    for r in bad_rec:
        _raises(lambda r=r: MD.assert_book_separation(REC, [r]), MD.BookSeparationError, "never read")
    MD.assert_book_separation(REC, [FR("R-03-US-VS12", "PASS", "RECOMMENDATION", "recommended"), FR("R-31-KR-STEP", "NOT_RUN", "INVARIANT_STEP", "recommended")])
    for r in (FR("R-11-S1", "REJECT", "REFUSAL_BOOK", "refusal"), FR("R-12-S2", "REJECT", "REFUSAL_BOOK", "specification"),
              FR("R-28-US-SMA10M", "NOT_RUN", "FORWARD_SIM", "forward_sim")):
        _raises(lambda r=r: MD.assert_book_separation(SPEC, [r]), MD.BookSeparationError)
    MD.assert_book_separation(SPEC, [FR("R-04-DM", "NOT_RUN", "SPECIFICATION_ONLY", "specification")])
    _raises(lambda: MD.assert_book_separation("forward_sim:R-28", [FR("R-11-S1", "REJECT", "REFUSAL_BOOK", "refusal")]), MD.BookSeparationError)
    _raises(lambda: MD.assert_book_separation("refusal:R-11", [FR("R-28-US-SMA10M", "NOT_RUN", "FORWARD_SIM", "forward_sim")]), MD.BookSeparationError)
    # runtime: FORWARD-SIM and refusal values enter the artifacts as display entries only; the composed line and the
    # fed weights never see them; a forward evaluator naming a recommended book is refused
    entries = {"forward_sim": {"R28_below_sma10m": True, "R29_vt_weight_next": 0.5}, "refusal_books": {"S1_krw_flag": True, "S2_rates_flag": True},
               "forward_entries": [{"rule_id": "R-28", "value": 0.5, "would_apply_to": "US market gross (forward book)",
                                    "card": {"card_id": "MACRO-R28-US-TREND", "class": "CARD-P", "verdict": "NOT_RUN", "disposition": "FORWARD_SIM"}}],
               "refusal_entries": [{"rule_id": "R-11-S1", "value": 0.75, "would_apply_to": "KR market gross (refusal book)",
                                    "card": {"card_id": "MACRO-R11-KR-KRW", "class": "CARD-P", "verdict": "REJECT", "disposition": "REFUSAL_BOOK"}}]}
    tmp = _tmp()
    s = services(tmp, kr_store(), None, forward_display=lambda ctx, m: entries,
                 forward_books=lambda ctx: {"books": {"forward_sim:R-28": {"weight": 0.5}, REC: {"weight": 0.1}}})
    rec = run(s, "KR", OCT2)
    arts = artifacts(tmp, rec)
    state, gross = state_of(tmp, rec), next(v for k, v in arts.items() if k.endswith("market_gross.json"))
    assert state["refusal_books"] == entries["refusal_books"] and state["forward_sim"] == entries["forward_sim"]
    assert [x["rule_id"] for x in gross["forward_sim"]] == ["R-28"] and [x["rule_id"] for x in gross["refusal"]] == ["R-11-S1"]
    assert gross["forward_sim"][0]["card"]["displayed_as"] == "descriptive" and gross["refusal"][0]["card"]["displayed_as"] == "refusal"
    assert gross["multipliers"] == [] and gross["overlay_min"] == 1.0 and gross["overlay_applied_recommended_book"] == 1.0
    assert state["concentration"]["by_book"][REC]["composed"] == 1.0                 # 0.5 / 0.75 never composed anywhere
    fb = step(rec, "macro.forward_books")
    assert fb["status"] == "error" and "BookSeparationError" in fb["error"] and "never writes a recommended" in fb["error"]
    feed = step(rec, "macro.engine_feed")["result"]["books"]
    assert set(feed) == {REC, SPEC} and feed[REC]["post_action"][LINE] == state["concentration"]["by_book"][REC]["gross"]
    # the static half: the book builder refuses the same reads (M4) and the rules-store shape 22 exists (M0)
    from core.quant import sleeves as SL
    from core.rules.macro_rules import load_store
    bad = SL.Multiplier("R-28", 0.5, "total", "market_gross", card={"card_id": "x", "verdict": "NOT_RUN", "disposition": "FORWARD_SIM"})
    _raises(lambda: SL.build_recommended_book((), SL.BaseWeights("recommended", {}, {}, {}), {}, decision_utc=_dec("KR", OCT2), multipliers=[bad]), Exception, "never reaches")
    assert load_store().get("do_not_build.refused_shapes.recommended_book_reads_non_pass_multiplier") == 22


test_i03_book_separation_static_and_runtime.test_ids = ["I-03"]


# --------------------------------------------------------------------------- #
# T-SCOPE-01 (a)-(h) and the T-ROLE-02 M8 clause: a trigger HALTs only the books it belongs to
# --------------------------------------------------------------------------- #
def _modes(reg) -> dict:
    return {b: reg.get(b).mode.value for b in reg.ids()}


def test_scope_01_h_and_a_input_failures_halt_the_specification_book_only():
    # (h) R-06 KR NOT_RUN; the KOSPI close missing on 3 consecutive decisions, every other input fresh
    tmp = _tmp()
    later = _sessions("KR", date(2026, 10, 8), 3)
    s = services(tmp, kr_store(extra_sessions=later), None)
    for d in later:
        rec = run(s, "KR", d)
    reg = s.book_registry
    assert reg.get(SPEC).halted and reg.get(SPEC).halt["class"] == "OPS" and reg.get(SPEC).halt["reason_code"] == "acting_input_stale:KOSPI_OFFICIAL_CLOSE"
    assert reg.get(REC).mode is EngineMode.ARMED and _modes(reg)[UREC] == "ARMED"
    state = state_of(tmp, rec)
    assert state["vol"]["vt_status"] == "fail_closed" and state["vol"]["vt_weight_recommended_book"] == 1.0 and state["fail_closed"] is True
    assert rec["halts"] == [] and any(h["book_id"] == SPEC for h in PL.read_run_log(tmp / "run_log.jsonl")[1]["halts"])
    # (a) US: R-04 inputs and the R-03 paper series failing on 3 decisions: specification:US HALTED only
    tmp = _tmp()
    s = services(tmp, kr_store(), None)
    for d in _sessions("US", date(2026, 10, 1), 3):
        rec = run(s, "US", d)
    reg = s.book_registry
    assert reg.get(USPEC).halted and reg.get(USPEC).halt["reason_code"].startswith("acting_input_stale:") and reg.get(UREC).mode is EngineMode.ARMED
    failed = {c["series_id"] for c in step(rec, "data_ok")["result"]["fail_closed"]}
    assert {"MOM_PAPER_LS_SERIES", "DM_MKT_RET_24M", "DM_MKT_VOL_126"} <= failed and _modes(reg)[REC] == "ARMED"
    assert all(c["books"] == [USPEC] for c in step(rec, "data_ok")["result"]["fail_closed"] if c["series_id"] in ("MOM_PAPER_LS_SERIES", "DM_MKT_RET_24M"))
    assert state_of(tmp, rec)["fail_closed"] is True                         # T-MISS-02: an acting input failed closed -> the artifact says so


test_scope_01_h_and_a_input_failures_halt_the_specification_book_only.test_ids = ["T-SCOPE-01"]


def test_scope_01_b_forward_books_fail_closed_never_halt_and_hedge_credit_off():
    tmp = _tmp()
    s = services(tmp, kr_store(spx=False), None)
    reg = s.book_registry
    for bid in ("forward_sim:R-28", "forward_sim:R-29"):
        reg.register(B.BookRuntime(bid))
        B.arm(reg, bid, _dec("KR", date(2026, 9, 1)))
    for d in _sessions("KR", OCT2, 3):
        rec = run(s, "KR", d)
    assert reg.get("forward_sim:R-28").mode is EngineMode.ARMED and reg.get("forward_sim:R-29").mode is EngineMode.ARMED
    assert set(rec["forward_failed"]) == {"forward_sim:R-28", "forward_sim:R-29"} and all("SPX_OFFICIAL_CLOSE" in v for v in rec["forward_failed"].values())
    assert reg.get(REC).mode is EngineMode.ARMED and reg.get(SPEC).mode is EngineMode.ARMED
    state = state_of(tmp, rec)
    assert state["flags"]["hedge_credit_off"] is True and "risk_model_input_stale" in state["flags"]["hedge_reasons"]
    assert "SPX_OFFICIAL_CLOSE" in state["flags"]["hedge_stale_inputs"] and state["fail_closed"] is False
    assert all(e["halt"] is None for e in state["runtime"])


test_scope_01_b_forward_books_fail_closed_never_halt_and_hedge_credit_off.test_ids = ["T-SCOPE-01", "T-ROLE-02"]


def test_scope_01_c_d_nav_minus_16_halts_its_own_book_risk():
    tmp = _tmp()
    days = _sessions("KR", OCT2, 3)
    nav = {SPEC: {days[1]: 84.0, days[2]: 84.0}, REC: {days[2]: 84.0}}
    s = services(tmp, kr_store(), None, nav=lambda ctx, b: nav.get(b, {}).get(ctx.session_date, 100.0))
    reg = s.book_registry
    rec1 = run(s, "KR", days[0])
    assert _modes(reg)[REC] == _modes(reg)[SPEC] == "ARMED"
    rec2 = run(s, "KR", days[1])                                               # (c) specification NAV -16%
    assert reg.get(SPEC).halted and reg.get(SPEC).halt["class"] == "RISK" and reg.get(SPEC).halt["reason_code"] == "hard_stop"
    assert reg.get(REC).mode is EngineMode.ARMED and rec2["halts"] == [{"book_id": SPEC, "class": "RISK", "reason_code": "hard_stop"}]
    st2 = state_of(tmp, rec2)
    assert st2["concentration"]["by_book"][SPEC] == {"composed": 0.0, "gross": 0.0, "binding_factor": "none"} and st2["flags"]["hard_stop"] == "armed"
    rec3 = run(s, "KR", days[2])                                               # (d) recommended NAV -16%
    assert reg.get(REC).halted and reg.get(REC).halt["class"] == "RISK" and reg.get(REC).halt["reason_code"] == "hard_stop"
    st3 = state_of(tmp, rec3)
    assert st3["flags"]["hard_stop"] == "rearm_refused" and st3["flags"]["engine_state"] == "HALTED"
    assert step(rec3, "macro.engine_feed")["result"]["books"][REC]["post_action"] == {LINE: 0.0}    # HALTED: 0x outside min()
    assert _modes(reg)[UREC] == _modes(reg)[USPEC] == "ARMED"
    # T-OBS-01: each HALT class writes its book's runtime[].halt block and a governance event
    rt = {e["book_id"]: e for e in st3["runtime"]}
    assert rt[REC]["halt"]["class"] == "RISK" and rt[REC]["halt"]["rearm_mode"] == "auto" and rt[REC]["halt"]["causes"][0]["reason_code"] == "hard_stop"
    events = [e for e in G.read_events(reg.log) if e["kind"] == "halt"]
    assert {e["book_id"] for e in events} == {REC, SPEC} and G.verify_chain(reg.log).ok
    assert {a["code"] for a in s.alerts.open("page")} >= {"HALT_RISK"}


test_scope_01_c_d_nav_minus_16_halts_its_own_book_risk.test_ids = ["T-SCOPE-01", "T-OBS-01"]


def test_scope_01_e_f_hedge_exception_and_context_log_failure_halt_nothing():
    tmp = _tmp()

    def boom(*a, **k):
        raise RuntimeError("injected hedge_state failure")
    s = services(tmp, kr_store(), None, hedge_state=boom, context_log_builder=lambda *a, **k: {"schema": "quantgen.context_log", "items": "not a list"})
    rec = run(s, "KR", OCT2)
    reg = s.book_registry
    assert rec["status"] == "ok" and all(m == "ARMED" for m in _modes(reg).values())
    state = state_of(tmp, rec)
    assert state["flags"]["hedge_credit_off"] is True and "risk_model_exception" in state["flags"]["hedge_reasons"] and state["fail_closed"] is False
    assert abs(state["vol"]["vt_weight_next"] - 0.694) < 0.01                 # vt unchanged by the hedge exception
    ctx_out = step(rec, "macro.build_artifacts")["result"]["context_log"]
    assert ctx_out["status"] == "quarantined" and "quarantine" in ctx_out["path"] and not (tmp / "context_log").exists()
    assert "CONTEXT_LOG_INVALID" in {a["code"] for a in s.alerts.open()} and not any(a["code"].startswith("HALT") for a in s.alerts.open())
    assert all(e["halt"] is None for e in state["runtime"]) and step(rec, "bounds_ok")["result"]["status"] == "pass"
    # T-OBS-01 OPS half: an OPS HALT (lag-audit violation) writes the block with rearm_mode operator and its event
    tmp = _tmp()
    store = kr_store()
    late = _close_row("KOSPI_OFFICIAL_CLOSE", OCT2, 7003.74, market="KR", available=_dec("KR", OCT2) + timedelta(minutes=5))
    store.append([late])                                                       # a close stamped after its bound (ignored by the read)
    s = services(tmp, store, None)
    saved = MD.STEPS["macro.lag_audit"]

    def injected(ctx):
        ctx.state["inputs"][("KOSPI_OFFICIAL_CLOSE", None)] = P.to_value(late, role="acting_exposure", books=("specification",))
        return saved(ctx)
    MD.STEPS["macro.lag_audit"] = injected
    try:
        rec = run(s, "KR", OCT2)
    finally:
        MD.STEPS["macro.lag_audit"] = saved
    reg = s.book_registry
    assert reg.get(SPEC).halted and reg.get(SPEC).halt == {**reg.get(SPEC).halt, "class": "OPS", "reason_code": "lag_audit_violation", "rearm_mode": "operator"}
    assert reg.get(REC).mode is EngineMode.ARMED and state_of(tmp, rec)["lag_audit"]["violations"]
    assert any(e["kind"] == "halt" and e["book_id"] == SPEC and "lag_audit_violation" in e["reason"] for e in G.read_events(reg.log))
    _raises(lambda: B.runtime_rearm(reg, SPEC, "auto", _dec("KR", date(2026, 10, 6))), B.RearmRefused, "operator")


test_scope_01_e_f_hedge_exception_and_context_log_failure_halt_nothing.test_ids = ["T-SCOPE-01", "T-OBS-01"]


def _snapshot_rows(store, knowledge: datetime) -> list[dict]:
    return [r for sid in store.series_ids() for r in store.rows(sid) if r["retrieved_at_utc"] <= knowledge]


def _pass_card(tmp: Path, store, *, card_id="MACRO-R03-US-MOM", knowledge="2026-10-02T07:00:00Z", snapshot="0" * 32,
               git_hash="c" * 40, package_md5=None, archive_rows=None) -> tuple[Path, dict]:
    """A synthetic PASS card file, its chained verdict row and (given the store rows) its archive under a temp cards root."""
    root = tmp / "cards_root"
    card = synthetic_card()
    card.update({"card_id": card_id, "revision": 1, "verdict": "PASS", "disposition": "RECOMMENDATION", "displayed_as": "recommendation",
                 "gate_package_md5": package_md5 or store.get("gate.package.definitions_md5"), "git_hash": git_hash,
                 "knowledge_utc": knowledge, "data_snapshot_id": snapshot})
    card["results_md5"] = MS.results_md5(card)
    path = CARDS.card_path(root, card_id, 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MS.canonical_json(card), encoding="utf-8")
    CARDS.append_verdict(root, card)
    if archive_rows is not None:
        CARDS.archive_snapshot(root, card, [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in r.items()} for r in archive_rows])
    return root, card


def test_scope_01_g_admission_binds_the_series_to_the_recommended_book_and_its_failure_halts_it():
    tmp = _tmp()
    store = kr_store()
    rules, _ = _frozen_store(tmp, frozen=True)
    knowledge = _dec("US", date(2026, 10, 1)) + timedelta(minutes=30)
    root, card = _pass_card(tmp, rules, knowledge=P.iso_utc(knowledge), snapshot=P.data_snapshot_id(store, knowledge), archive_rows=_snapshot_rows(store, knowledge))
    pkg = MD.package_of(rules)
    s = services(tmp, store, None, rules=rules, cards_root=root, harness_hashes_at=lambda h: pkg["harness_sources"] if h == "c" * 40 else None)
    days = _sessions("US", date(2026, 10, 1), 3)
    rec = run(s, "US", days[0])
    vf = step(rec, "verdict_filter")["result"]
    assert vf["admitted"] == {UREC: ("R-03-US-VS12",)} and vf["status"] == "pass" and vf["integrity_failures"] == []
    assert "MOM_PAPER_LS_SERIES|*" in vf["binding_changes"]
    ev = [e for e in G.read_events(s.book_registry.log) if e["kind"] == "binding_change"]
    assert len(ev) == 1 and ev[0]["key"] == "MOM_PAPER_LS_SERIES|*" and ev[0]["new"] == [USPEC, UREC] and ev[0]["book_id"] == UREC
    assert state_of(tmp, rec)["extras"]["derived_bindings"]["MOM_PAPER_LS_SERIES|*"] == [USPEC, UREC]
    for d in days[1:]:
        rec = run(s, "US", d)
    reg = s.book_registry
    assert reg.get(UREC).halted and reg.get(UREC).halt["reason_code"] == "acting_input_stale:MOM_PAPER_LS_SERIES" and reg.get(USPEC).halted
    assert _modes(reg)[REC] == "ARMED" and step(rec, "verdict_filter")["result"]["binding_changes"] == []   # no second event
    # a book that reads a factor whose acting inputs are not bound to it is refused at load (US_SLEEVE: books [])
    adm = MD.AdmissionResult({UREC: ("R-06-US-VT15",)}, {}, (), True, {"US_SLEEVE_OFFICIAL_CLOSE": True})
    from core.ficc import contracts as C
    _raises(lambda: MD.check_bindings(REG, adm, C.derive_bindings(REG, adm.series)), MD.BookSeparationError, "not bound")


test_scope_01_g_admission_binds_the_series_to_the_recommended_book_and_its_failure_halts_it.test_ids = ["T-SCOPE-01", "T-CARD-03"]


# --------------------------------------------------------------------------- #
# T-OBS-02 / T-OBS-05: the app-start hook (missed decisions, governance chain), once per process
# --------------------------------------------------------------------------- #
def test_obs_02_missed_decisions_paged_at_app_start_and_books_carry_weights():
    tmp = _tmp()
    s = services(tmp, kr_store(), None)
    run(s, "KR", OCT2)
    held = dict(s.book_registry.get(REC).held)
    rows = PL.read_run_log(tmp / "run_log.jsonl")
    expected = MD.expected_decisions(CLK, "KR", OCT2, date(2026, 10, 8))
    assert [d for _, d, _ in expected] == [date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8)]
    missed = PL.missed_decisions(expected, rows)
    assert [m["session_date"] for m in missed] == ["2026-10-06", "2026-10-07", "2026-10-08"] and all(m["reason"] == "no_run" for m in missed)
    out = MD.app_start(tmp, lambda: U(2026, 10, 8, 7, 0), clocks=CLK)
    assert out["governance_chain_ok"] and [m["session_date"] for m in out["missed"]] == ["2026-10-06", "2026-10-07", "2026-10-08"]
    pages = [a for a in s.alerts.open("page") if a["code"] == "MISSED_DECISION"]
    assert len(pages) == 3 and all(a["books"] == [REC, SPEC] for a in pages) and pages[0]["first_seen_utc"] == "2026-10-06T06:30:30Z"
    assert dict(s.book_registry.get(REC).held) == held and _modes(s.book_registry)[REC] == "ARMED"   # weights carried
    # before 06:40:30Z of the 8th the decision of the 8th is not yet expected; an errored acting step counts as missed
    out = MD.app_start(tmp, lambda: U(2026, 10, 8, 6, 40, 29), clocks=CLK, markets=("KR",))
    assert [m["session_date"] for m in out["missed"]] == ["2026-10-06", "2026-10-07"]
    rows.append({"run_id": "x", "market": "KR", "session_date": "2026-10-06", "run_mode": "live", "status": "error", "acting_error": True})
    assert [m["reason"] for m in PL.missed_decisions(expected, rows)] == ["acting_step_error", "no_run", "no_run"]
    rows.append({"run_id": "y", "market": "KR", "session_date": "2026-10-06", "run_mode": "replay", "status": "ok", "acting_error": False})
    assert PL.missed_decisions(expected, rows)[0]["reason"] == "acting_step_error"                         # a replay never cures it (F-12)
    # the process guard: a second on_app_start is a no-op unless forced; the wired main.py call is guarded
    MD._STARTED["done"] = False
    assert MD.on_app_start(tmp, lambda: U(2026, 10, 8, 7, 0), clocks=CLK) is not None and MD.on_app_start(tmp, lambda: U(2026, 10, 8, 7, 0), clocks=CLK) is None
    src = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "on_app_start(background=True)" in src and src.count("core.skills.macro_daily") == 1 and "except Exception:" in src.split("on_app_start")[-1]


test_obs_02_missed_decisions_paged_at_app_start_and_books_carry_weights.test_ids = ["T-OBS-02"]


def test_obs_05_governance_chain_verified_at_app_start():
    tmp = _tmp()
    s = services(tmp, kr_store(), None)
    run(s, "KR", OCT2)
    log = s.book_registry.log
    assert G.verify_chain(log).ok and MD.app_start(tmp, lambda: U(2026, 10, 2, 8, 0), clocks=CLK)["governance_chain_ok"]
    assert not [a for a in s.alerts.open() if a["code"] == "GOVERNANCE_LOG_BROKEN"]
    raw = log.read_bytes()
    i = raw.index(b'"actor":"runtime"')
    log.write_bytes(raw[:i] + b'"actor":"owner__"' + raw[i + len(b'"actor":"runtime"'):])          # one hand edit
    assert not G.verify_chain(log).ok
    out = MD.app_start(tmp, lambda: U(2026, 10, 2, 8, 0), clocks=CLK)
    broken = [a for a in s.alerts.open("page") if a["code"] == "GOVERNANCE_LOG_BROKEN"]
    assert not out["governance_chain_ok"] and len(broken) == 1 and "chain broken at line" in broken[0]["detail"]


test_obs_05_governance_chain_verified_at_app_start.test_ids = ["T-OBS-05"]


# --------------------------------------------------------------------------- #
# T-OBS-03: page alerts persist until acknowledged
# --------------------------------------------------------------------------- #
def test_obs_03_page_alerts_persist_until_acknowledged():
    tmp = _tmp()
    store = AL.AlertStore(tmp)
    a = store.raise_alert("RUN_ERROR", "page", "macro.pit_snapshot", when=U(2026, 10, 2, 6, 30, 30), books=(REC, SPEC), detail="boom")
    assert a["count"] == 1 and a["first_seen_utc"] == "2026-10-02T06:30:30Z" and a["sinks"] == AL.SINKS and a["ack_utc"] is None
    again = AL.AlertStore(tmp)                                                 # reloaded from disk: still open
    assert [x["alert_id"] for x in again.open("page")] == [a["alert_id"]]
    b = again.raise_alert("RUN_ERROR", "page", "macro.pit_snapshot", when=U(2026, 10, 6, 6, 30, 30), books=(REC, SPEC))
    assert b["alert_id"] == a["alert_id"] and b["count"] == 2 and b["first_seen_utc"] == a["first_seen_utc"] and b["last_seen_utc"] == "2026-10-06T06:30:30Z"
    ack = again.acknowledge(a["alert_id"], "operator", U(2026, 10, 6, 9, 0))
    assert ack["ack_utc"] == "2026-10-06T09:00:00Z" and ack["ack_by"] == "operator" and AL.AlertStore(tmp).open() == []
    c = again.raise_alert("RUN_ERROR", "page", "macro.pit_snapshot", when=U(2026, 10, 7, 6, 30, 30), books=(REC, SPEC))
    assert c["count"] == 1 and c["first_seen_utc"] == "2026-10-07T06:30:30Z"              # a new episode after the acknowledgement
    assert AL.as_artifact(c).keys() == set(AL.ARTIFACT_KEYS) and MS.validate("macro_state", {}) != []
    _raises(lambda: store.raise_alert("X", "critical", "c", when=U(2026, 1, 1)), ValueError, "severity")
    _raises(lambda: store.raise_alert("MISSED_DECISION", "warn", "c", when=U(2026, 1, 1)), ValueError, "page-severity")
    _raises(lambda: store.acknowledge("nope", "operator", U(2026, 1, 1)), KeyError)
    _raises(lambda: store.acknowledge(c["alert_id"], "", U(2026, 1, 1)), ValueError, "names")
    assert AL.SINKS["os_notification"] == "unavailable" and AL.SINKS["email"] == "unavailable"


test_obs_03_page_alerts_persist_until_acknowledged.test_ids = ["T-OBS-03"]


# --------------------------------------------------------------------------- #
# T-OBS-04: an exception in each acting step; the forward_monitor queue
# --------------------------------------------------------------------------- #
def test_obs_04_acting_step_errors_block_feed_count_and_halt_at_the_limit():
    def boom(ctx):
        raise RuntimeError("injected")
    days = _sessions("KR", OCT2, 2)
    for name in PL.ACTING_STEPS:
        table = MD.STEPS if name in MD.STEPS else MD.GATES
        saved = table[name]
        table[name] = boom
        try:
            tmp = _tmp()
            s = services(tmp, kr_store(), None)
            rec = run(s, "KR", days[0])
        finally:
            table[name] = saved
        reg = s.book_registry
        assert rec["status"] == "error" and rec["acting_error"] and step(rec, name)["status"] == "error" and "injected" in step(rec, name)["error"]
        assert step(rec, "macro.engine_feed")["status"] == "blocked" and B.ledger(reg, REC) == []
        assert [a["code"] for a in s.alerts.open("page")] == ["RUN_ERROR"] and s.alerts.open("page")[0]["component"] == name
        later = [x["status"] for x in rec["steps"] if x["name"] in PL.ACTING_STEPS and x["name"] != name]
        before = [x["name"] for x in rec["steps"] if x["status"] == "ok"][: PL.ACTING_STEPS.index(name)]
        assert all(st == "skipped" for st in later[len(before):] if st != "ok") or name == "verdict_filter"
        if PL.ACTING_STEPS.index(name) < PL.ACTING_STEPS.index("macro.build_artifacts"):
            assert step(rec, "macro.build_artifacts")["status"] == "ok" and state_of(tmp, rec)["fail_closed"] is True   # fail_closed artifact
            ran = PL.ACTING_STEPS.index(name) > PL.ACTING_STEPS.index("macro.lag_audit")
            assert ("lag_audit_status" in state_of(tmp, rec)["extras"]) is not ran      # an audit that did not run says so
        elif name != "macro.build_artifacts":                                  # the written artifact is not marked by the later error:
            st = state_of(tmp, rec)                                            # only the day's own unusable basket (10-01) fails it closed
            assert st["fail_closed"] is bool((st["extras"]["concentration_note"] or {}).get("fail_closed")) and step(rec, "macro.engine_feed")["status"] == "blocked"
        assert rec["books"][REC]["book_counter"] == rec["books"][SPEC]["book_counter"] == 1 and _modes(reg)[REC] == "ARMED"
        assert [m["reason"] for m in PL.missed_decisions([("KR", days[0], _dec("KR", days[0]))], PL.read_run_log(tmp / "run_log.jsonl"))] == ["acting_step_error"]
        table[name] = boom
        try:
            rec2 = run(s, "KR", days[1])                                       # the limit: OPS HALT of every served book
        finally:
            table[name] = saved
        assert reg.get(REC).halted and reg.get(SPEC).halted and reg.get(REC).halt["reason_code"] == B.STEP_ERROR_REASON
        assert _modes(reg)[UREC] == "ARMED" and rec2["halts"] and {a["code"] for a in s.alerts.open("page")} >= {"RUN_ERROR", "HALT_OPS"}
    # a non-acting step error is recorded and paged, counts nothing and does not block the feed
    saved = MD.STEPS["macro.brief"]
    MD.STEPS["macro.brief"] = boom
    try:
        tmp = _tmp()
        s = services(tmp, kr_store(), None)
        rec = run(s, "KR", days[0])
    finally:
        MD.STEPS["macro.brief"] = saved
    assert rec["status"] == "error" and not rec["acting_error"] and step(rec, "macro.engine_feed")["status"] == "ok"
    assert rec["books"][REC]["book_counter"] == 0 and _modes(s.book_registry)[REC] == "ARMED"
    # forward_monitor: an exception queues the decision; the next successful run re-runs it for every queued decision
    seen = []

    def monitor(ctx, decision):
        if decision["session_date"] == days[0].isoformat() and not seen:
            seen.append("first failure")
            raise RuntimeError("monitor down")
        seen.append(decision["session_date"])
    tmp = _tmp()
    s = services(tmp, kr_store(), None, forward_monitor=monitor)
    rec = run(s, "KR", days[0])
    assert step(rec, "macro.forward_monitor")["status"] == "error" and MD.read_monitor_queue(tmp) == [
        {"market": "KR", "session_date": days[0].isoformat(), "decision_utc": P.iso_utc(_dec("KR", days[0]))}]
    assert step(rec, "macro.engine_feed")["status"] == "ok"                     # not an acting step: the feed ran
    rec2 = run(s, "KR", days[1])
    assert step(rec2, "macro.forward_monitor")["result"]["monitored"] == [
        {"market": "KR", "session_date": days[0].isoformat(), "decision_utc": P.iso_utc(_dec("KR", days[0]))},
        {"market": "KR", "session_date": days[1].isoformat(), "decision_utc": P.iso_utc(_dec("KR", days[1]))}]
    assert MD.read_monitor_queue(tmp) == [] and seen == ["first failure", days[0].isoformat(), days[1].isoformat()]


test_obs_04_acting_step_errors_block_feed_count_and_halt_at_the_limit.test_ids = ["T-OBS-04"]


# --------------------------------------------------------------------------- #
# T-CARD-03: verdict integrity (i)-(iii); the UNVERSIONED refusal of today
# --------------------------------------------------------------------------- #
def test_card_03_verdict_integrity_refuses_edits_broken_chains_and_mismatches():
    tmp = _tmp()
    rules, _ = _frozen_store(tmp, frozen=True)
    root, card = _pass_card(tmp, rules)
    pkg = MD.package_of(rules)
    dec = _dec("US", date(2026, 10, 1))
    kw = dict(snapshot_id_at=lambda k: "0" * 32, harness_hashes_at=lambda h: pkg["harness_sources"], lockouts=lambda f, m, t: False, decision_utc=dec)
    rows, ok = MD.verdict_rows(root)
    good = MD.admissions(MD.load_cards(root), rows, pkg, chain_ok=ok, **kw)
    assert good.admitted == {UREC: ("R-03-US-VS12",)} and good.integrity_failures == () and good.series == {"MOM_PAPER_LS_SERIES": True}
    assert "NOT_RUN" in good.refused["R-06-KR-VT20"] and "REJECT" in good.refused["R-06-US-VT15"]
    # a card edited to PASS after its run: the file no longer re-hashes -> specification book + integrity failure
    edited = dict(card, verdict="PASS", verdict_reason="edited after the run")
    out = MD.admissions({**MD.load_cards(root), card["card_id"]: edited}, rows, pkg, chain_ok=ok, **kw)
    assert out.admitted == {} and out.integrity_failures == ("R-03-US-VS12",) and "(i)" in out.refused["R-03-US-VS12"]
    # a hand-edited verdicts.jsonl row breaks the chain and blocks every admission until restored
    path = CARDS.verdicts_path(root)
    raw = path.read_bytes()
    path.write_bytes(raw.replace(b'"verdict":"PASS"', b'"verdict": "PASS"'))       # a hand edit (even a reformat) breaks the chain
    rows2, ok2 = MD.verdict_rows(root)
    out = MD.admissions(MD.load_cards(root), rows2, pkg, chain_ok=ok2, **kw)
    assert not ok2 and out.admitted == {} and not out.chain_ok and "chain broken" in out.refused["R-03-US-VS12"]
    path.write_bytes(raw)
    assert MD.verdict_rows(root)[1]
    # (ii) a gate_package_md5 that differs from the frozen package; (iii) a non-reproducible data_snapshot_id
    out = MD.admissions(MD.load_cards(root), rows, {**pkg, "definitions_md5": "f" * 32}, chain_ok=True, **kw)
    assert "(ii)" in out.refused["R-03-US-VS12"] and out.integrity_failures == ("R-03-US-VS12",)
    out = MD.admissions(MD.load_cards(root), rows, pkg, chain_ok=True, **{**kw, "snapshot_id_at": lambda k: "9" * 32})
    assert "(iii) data_snapshot_id" in out.refused["R-03-US-VS12"]
    out = MD.admissions(MD.load_cards(root), rows, pkg, chain_ok=True, **{**kw, "harness_hashes_at": lambda h: None})
    assert "harness sources" in out.refused["R-03-US-VS12"]
    unf = MD.admissions(MD.load_cards(root), rows, {**pkg, "status": "NOT_FROZEN", "definitions_md5": "written_at_freeze"}, chain_ok=True, **kw)
    assert "not FROZEN" in unf.refused["R-03-US-VS12"]
    # through the pipeline: the admitted card, then the same card edited -> VERDICT_INTEGRITY page + governance event
    store = kr_store()
    knowledge = dec + timedelta(minutes=30)
    root2, card2 = _pass_card(tmp / "b", rules, knowledge=P.iso_utc(knowledge), snapshot=P.data_snapshot_id(store, knowledge), archive_rows=_snapshot_rows(store, knowledge))
    s = services(tmp / "b", store, None, rules=rules, cards_root=root2, harness_hashes_at=lambda h: pkg["harness_sources"])
    rec = run(s, "US", date(2026, 10, 1))
    assert step(rec, "verdict_filter")["result"]["admitted"] == {UREC: ("R-03-US-VS12",)}
    p = CARDS.card_path(root2, card2["card_id"], 1)
    p.write_text(MS.canonical_json(dict(card2, verdict_reason="edited after the run")), encoding="utf-8")
    rec = run(s, "US", date(2026, 10, 2))                                       # the next decision: the factor leaves the recommended book
    vf = step(rec, "verdict_filter")["result"]
    assert vf["admitted"] == {} and vf["integrity_failures"] == ["R-03-US-VS12"] and vf["status"] == "fail"
    assert "VERDICT_INTEGRITY" in {a["code"] for a in s.alerts.open("page")}
    assert any(e["kind"] == "verdict_integrity" and e["rule_id"] == "R-03-US-VS12" for e in G.read_events(s.governance_log))
    assert state_of(tmp / "b", rec)["extras"]["derived_bindings"]["MOM_PAPER_LS_SERIES|*"] == [USPEC]   # the derived binding follows
    again = run(s, "US", date(2026, 10, 2))                                     # a second live run of a decision is an audit on scratch state
    assert again["run_mode"] == "replay" and step(again, "verdict_filter")["result"]["integrity_failures"] == ["R-03-US-VS12"]


test_card_03_verdict_integrity_refuses_edits_broken_chains_and_mismatches.test_ids = ["T-CARD-03"]


def test_verdict_filter_refuses_unversioned_and_admits_nothing_today():
    tmp = _tmp()
    s = services(tmp, kr_store(), None)
    ctx = PL.RunContext("KR", OCT2, _dec("KR", OCT2), "live", "r", _dec("KR", OCT2), s.clock, s, knowledge_utc=_dec("KR", OCT2))
    adm = MD.compute_admissions(s, ctx)
    assert adm.admitted == {} and adm.chain_ok and adm.integrity_failures == () and set(adm.refused) == {c.rule_id for c in CARDS.REGISTRY}
    assert all(("NOT_RUN" in r) or ("REJECT" in r) for r in adm.refused.values())
    # a PASS card on a frozen store with git_hash UNVERSIONED: refused with the owner action (rulings 3.1; F-4)
    rules, _ = _frozen_store(tmp, frozen=True)
    root, card = _pass_card(tmp, rules, git_hash="UNVERSIONED")
    rows, ok = MD.verdict_rows(root)
    out = MD.admissions(MD.load_cards(root), rows, MD.package_of(rules), chain_ok=ok, snapshot_id_at=lambda k: "0" * 32,
                        harness_hashes_at=lambda h: None, lockouts=lambda f, m, t: False, decision_utc=_dec("US", date(2026, 10, 1)))
    assert out.admitted == {} and "owner must place the repository under git" in out.refused["R-03-US-VS12"]
    assert out.integrity_failures == ("R-03-US-VS12",)
    # a lockout refuses without an integrity failure; a BUILD_AS_INSURANCE card that is NOT_RUN is refused on sight
    out = MD.admissions(MD.load_cards(root), rows, MD.package_of(rules), chain_ok=ok, snapshot_id_at=lambda k: "0" * 32,
                        harness_hashes_at=lambda h: None, lockouts=lambda f, m, t: True, decision_utc=_dec("US", date(2026, 10, 1)))
    assert out.admitted == {}
    ins = dict(card, card_id="MACRO-R06-KR-ETF", verdict="NOT_RUN", build_status_on_pass="BUILD_AS_INSURANCE")
    out = MD.admissions({"MACRO-R06-KR-ETF": ins}, [], MD.package_of(rules), chain_ok=True, snapshot_id_at=lambda k: "0" * 32,
                        harness_hashes_at=lambda h: None, lockouts=lambda f, m, t: False, decision_utc=_dec("KR", OCT2))
    assert "BUILD_AS_INSURANCE while NOT_RUN" in out.refused["R-06-KR-VT20"] and out.integrity_failures == ()


test_verdict_filter_refuses_unversioned_and_admits_nothing_today.test_ids = ["T-CARD-03"]


# --------------------------------------------------------------------------- #
# T-REPLAY-01: byte-for-byte after canonicalisation; data_snapshot_id order-invariant and stable under a correction
# --------------------------------------------------------------------------- #
def test_replay_01_reproduces_the_artifacts_byte_for_byte():
    tmp = _tmp()
    days = _sessions("KR", OCT2, 2)
    store = kr_store()
    s = services(tmp, store, None, cal=fixture_set(), events=(NFP,))
    recs = [run(s, "KR", d) for d in days]
    knowledge = P.parse_utc(recs[1]["knowledge_utc"])
    snap = P.data_snapshot_id(store, knowledge)
    assert state_of(tmp, recs[1])["data_snapshot_id"] == snap
    # a later correction row (retrieved after knowledge_utc) changes nothing at that knowledge instant
    store.append([_close_row("KOSPI_OFFICIAL_CLOSE", days[1], 7003.74, market="KR", retrieved=knowledge + timedelta(hours=2))])
    assert P.data_snapshot_id(store, knowledge) == snap and P.data_snapshot_id(store, knowledge + timedelta(hours=3)) != snap
    rows_before = len(PL.read_run_log(tmp / "run_log.jsonl"))
    live = {b: s.book_registry.get(b) for b in s.book_registry.ids()}
    for i, d in enumerate(days):
        rep = MD.replay(s, "KR", d)
        assert rep["match"], (d, rep["diffs"])
        assert rep["run"]["run_mode"] == "replay" and step(rep["run"], "macro.engine_feed")["status"] == "blocked"
        assert rep["artifact"]["run_mode"] == "replay" and rep["artifact"]["knowledge_utc"] == recs[i]["knowledge_utc"]
        assert PL.canonical_bytes(rep["artifact"], MD.REPLAY_IGNORE) == PL.canonical_bytes(state_of(tmp, recs[i]), MD.REPLAY_IGNORE)
    assert len(PL.read_run_log(tmp / "run_log.jsonl")) == rows_before                 # audits only: the live log and books untouched
    assert all(s.book_registry.get(b) == live[b] for b in live) and not (tmp / "replay" / f"KR-{days[1].isoformat()}" / "engine_feed").exists()
    # the canonical form: sorted keys, repr floats, no insignificant whitespace, generated_at_utc / git_hash / tree_hash excluded
    a = {"b": 1.5, "a": [1, 2], "generated_at_utc": "x", "git_hash": "y", "tree_hash": "z"}
    assert PL.canonical_bytes(a) == b'{"a":[1,2],"b":1.5}' and PL.compare_artifacts(a, dict(a, generated_at_utc="q")) == []
    assert PL.compare_artifacts(a, dict(a, b=1.5000000001)) == ["b"]


test_replay_01_reproduces_the_artifacts_byte_for_byte.test_ids = ["T-REPLAY-01"]


# --------------------------------------------------------------------------- #
# I-06c (bounds_ok): an acting-field failure HALTs the described books; a display-field failure never does
# --------------------------------------------------------------------------- #
def test_i06c_acting_field_failure_halts_described_books_display_failure_never():
    def corrupt_acting(kind, obj):
        if kind == "macro_state":
            obj = dict(obj, vol=dict(obj["vol"], vt_weight_next=1.5))                # above 1.0: an acting field (P2)
        return obj
    tmp = _tmp()
    s = services(tmp, kr_store(), None, before_write=corrupt_acting)
    rec = run(s, "KR", OCT2)
    reg = s.book_registry
    assert rec["status"] == "ok" and step(rec, "bounds_ok")["result"]["status"] == "fail"
    for b in (REC, SPEC):
        assert reg.get(b).halted and reg.get(b).halt["class"] == "OPS" and reg.get(b).halt["reason_code"] == "acting_field_schema_or_bounds_failure"
        assert reg.get(b).halt["rearm_mode"] == "operator"
    assert _modes(reg)[UREC] == "ARMED" and not (tmp / "macro_state").exists() and list((tmp / "quarantine").glob("macro_state__*.json"))
    assert step(rec, "macro.engine_feed")["result"]["books"][REC]["post_action"] == {LINE: 0.0}    # HALTED: nothing earns
    assert {a["code"] for a in s.alerts.open("page")} >= {"SCHEMA_ACTING_FIELD", "HALT_OPS"}
    # a display / context field out of schema: written with extras.validation_errors, alert, no HALT
    tmp = _tmp()
    s = services(tmp, kr_store(), None, before_write=lambda k, o: dict(o, annotations=dict(o["annotations"], notes="not a list")) if k == "macro_state" else o)
    rec = run(s, "KR", OCT2)
    state = state_of(tmp, rec)
    assert any("/annotations/notes" in e for e in state["extras"]["validation_errors"]) and all(m == "ARMED" for m in _modes(s.book_registry).values())
    assert step(rec, "bounds_ok")["result"]["status"] == "pass" and "SCHEMA_DISPLAY_FIELD" in {a["code"] for a in s.alerts.open("warn")}
    # a product-composed record is caught by the recomputation (L881): quarantined, HALT (OPS), page
    tmp = _tmp()

    def product(kind, obj):
        if kind == "macro_state":
            bb = json.loads(json.dumps(obj["concentration"]["by_book"]))
            bb[SPEC]["composed"] = bb[SPEC]["composed"] * 0.75 * 0.5
            obj = dict(obj, concentration=dict(obj["concentration"], by_book=bb))
        return obj
    s = services(tmp, kr_store(), None, before_write=product)
    rec = run(s, "KR", OCT2)
    issues = step(rec, "bounds_ok")["result"]["issues"]
    assert any(i["kind"] == "composition" for i in issues) and s.book_registry.get(SPEC).halted and not list((tmp / "macro_state").rglob("*.json"))


test_i06c_acting_field_failure_halts_described_books_display_failure_never.test_ids = ["I-06c"]


# --------------------------------------------------------------------------- #
# NAV_LINE_CLOSES: the whole-book NAV reads official closes only (the declared vendor's in a backtest; L1181, L1319)
# --------------------------------------------------------------------------- #
def test_default_nav_values_the_book_on_official_closes_only():
    tmp = _tmp()
    d1, d2 = _sessions("KR", OCT2, 2)
    store = P.PITStore(tmp / "pit", registry=REG, clocks=CLK)
    store.append([_close_row(MD.NAV_SERIES["KR"], d1, 40000.0, market="KR"),
                  _close_row(MD.NAV_SERIES["KR"], d2, 36000.0, market="KR", source="KIS", status="vendor_close")])
    s = services(tmp, store, None)
    B.record_decision(s.book_registry, SPEC, _dec("KR", d1), {LINE: 1.0})
    ctx = SimpleNamespace(services=s, market="KR", decision_utc=_dec("KR", d2), knowledge_utc=_dec("KR", d2) + timedelta(minutes=30),
                          session_date=d2, run_mode="live")
    assert MD._default_nav(ctx, SPEC) is None                                   # live: a KIS vendor print never values the book
    ctx.run_mode, s.vendor = "backtest", "KIS"
    assert abs(MD._default_nav(ctx, SPEC) - 0.9) < 1e-12                        # the declared vendor of a backtest does


test_default_nav_values_the_book_on_official_closes_only.test_ids = ["T-ROLE-01"]


def test_default_services_reads_the_effective_store_with_owner_rulings():
    """S1: the runtime store is load_store(SHIPPED_STORE_PATH, rulings_log=<macro_dir>/governance_events.jsonl)."""
    tmp, clock = _tmp(), (lambda: U(2026, 10, 6, 7))
    M.apply_owner_ruling(M.SHIPPED_STORE_PATH, tmp / MD.GOVERNANCE_LOG, "D1", "pair_35", "owner", clock)
    s = MD.default_services(tmp, clock, registry=REG, clocks=CLK)
    assert M.owner_decision(s.rules, "D1")["status"] == "owner_set"
    assert s.rules.config_hash == M.load_store(rulings_log=tmp / MD.GOVERNANCE_LOG).config_hash != M.load_store().config_hash


test_default_services_reads_the_effective_store_with_owner_rulings.test_ids = ["T-OWNER-01"]


# --------------------------------------------------------------------------- #
# The labelled dry run on the local vendor cache (rulings 1): offline, under two minutes, books DISARMED
# --------------------------------------------------------------------------- #
def test_dry_run_end_to_end_on_the_local_cache():
    tmp = _tmp()
    # Git checkout time is not the retrieval time of this historical test fixture.
    # Copy the unchanged vendor bytes into a temp cache and pin its retrieval before the test's clock.
    cache = tmp / "cache"
    cache.mkdir()
    fetched = U(2026, 10, 6, 22)
    for name in {name for name, _source in MD.DRY_RUN_CACHE.values()}:
        source = MD.CACHE_DIR / name
        if source.is_file():
            target = cache / name
            shutil.copyfile(source, target)
            os.utime(target, (fetched.timestamp(), fetched.timestamp()))
    t0 = time.perf_counter()
    out = MD.dry_run(tmp, clock=lambda: U(2026, 10, 7, 9, 0), cache_dir=cache)
    assert time.perf_counter() - t0 < 120.0
    root = tmp / "dry_run"
    assert out["root"] == str(root) and all(v.get("appended", 0) > 0 for v in out["ingested"].values())
    for m in ("KR", "US"):
        rec = out["runs"][m]
        assert rec["status"] == "ok" and rec["run_mode"] == "backtest" and not rec["acting_error"]
        assert step(rec, "macro.engine_feed")["status"] == "blocked" and step(rec, "macro.engine_feed")["reason"].startswith("run_mode backtest")
        arts = {rel: json.loads((root / rel).read_text(encoding="utf-8")) for rel in rec["artifacts"]}
        assert any(k.startswith("macro_state/") for k in arts) and sum(k.startswith("overlay_decision/") for k in arts) == 6 and any(k.startswith("context_log/") for k in arts)
        for rel, obj in arts.items():
            kind = rel.split("/")[0]
            ok, issues, acting = MS.check_artifact(kind, obj)
            assert not acting, (rel, issues)
            assert obj["extras"]["dry_run"]["chip"] == MD.DRY_RUN_MARKER["chip"] and obj["extras"]["dry_run"]["run_mode"] == "backtest"
            assert obj.get("run_mode", obj["extras"].get("run_mode", "backtest")) == "backtest"
        state = next(v for k, v in arts.items() if k.startswith("macro_state/"))
        assert all(e["engine_state"] == "DISARMED" for e in state["runtime"]) and state["vol"]["vt_weight_recommended_book"] == 1.0
        assert all(i["value_status"] in ("vendor_close", "first_release") for i in state["inputs"])
        assert all(i["retrieved_at_utc"] != "2026-10-07T09:00:00Z" for i in state["inputs"])     # the file's mtime (L1283), never the clock
        assert all(i["retrieved_at_utc"] == "2026-10-06T22:00:00Z" for i in state["inputs"])
    assert all(m == "DISARMED" for m in out["books"].values()) and not (root / "engine_feed").exists()
    us = next(v for k, v in {rel: json.loads((root / rel).read_text(encoding="utf-8")) for rel in out["runs"]["US"]["artifacts"]}.items() if k.startswith("macro_state/"))
    assert us["vol"]["vt_status"] == "ok" and 0.0 < us["vol"]["vt_weight_next"] <= 1.0           # SPY vendor rows size the US vt (labelled)
    assert us["extras"]["fail_closed_inputs"] and us["fail_closed"] is True                       # vt ok, the R-03 / R-04 acting inputs failed closed (T-MISS-02)
    kr = next(v for k, v in {rel: json.loads((root / rel).read_text(encoding="utf-8")) for rel in out["runs"]["KR"]["artifacts"]}.items() if k.startswith("macro_state/"))
    assert kr["vol"]["vt_status"] == "fail_closed" and kr["fail_closed"] is True                 # no KOSPI series in the cache: honest
    assert not any(p.name.startswith("yf_") for p in (root / "pit").iterdir()) and (ROOT / "docs/asset_expansion/cache/yf_SPY.csv").is_file()
    # The same rows must remain invisible when the knowledge time precedes retrieval.
    early = MD.dry_run(tmp / "early", clock=lambda: fetched - timedelta(hours=1), cache_dir=cache)
    early_state = state_of(Path(early["root"]), early["runs"]["US"])
    assert early_state["vol"]["vt_status"] == "fail_closed" and early_state["fail_closed"]


test_dry_run_end_to_end_on_the_local_cache.test_ids = ["I-01"]


def tests():
    return [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
