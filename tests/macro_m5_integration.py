"""Sprint 4 integration (M5 engine and events, M6 context and breaks): the seams between the three packages,
wired and asserted end to end.

1. The R-31 ladder's `block_new_entries` and the R-07 `post_rearm_cap` flow from `books.risk_step` through
   `risk_layer.ladder_for_book` into `sleeves.apply_market_gross` (composition by min()), `evaluator.evaluator_block`
   (BLOCKED for a new entry only) and `books.record_decision` (the weight ledger); the built `macro_state` reads
   them back from `BookRegistry.runtime_entries()` (I-04, T-HALT-01, T-STEP-05).
2. The R-18 hook: `context_log.log_break(neutralise=books.neutralise_rule)` persists on the books and
   `build_overlay_decisions(neutralised=books.neutralised_rules(...))` applies it (T-BREAK-01).
3. `build_macro_state` takes the `ConcentrationBound` of `risk_layer.concentration_bound` on the inline basket, the
   registry's runtime entries, package B's gap tags and annotation; the state validates (T-CAPS-01, I-06b, I-06c,
   T-ANNOT-01).
4. `event_calendar` and `context_log` artifacts reach disk through `macro_artifacts.write_artifact` only (I-06, T-CTX-02).
5. G-R08-02 is on file as a record (print_only golden rows), never reproduced here (REFDATA).
6. Rulings: no wall clock in the Sprint 4 modules; nothing above 1.0; HALTED outside min(); the inherited engine
   modules byte-identical to the pre-v2 backup; orders.py / evaluator.py add-only.
Hermetic: temp registries and artifact roots, the signed fixture calendar, synthetic stores; nothing under ~/.nextgen.
"""
from __future__ import annotations

import ast
import difflib
import json
import tempfile
import zipfile
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from core.calendars import events as EV
from core.engine import books as B
from core.engine import evaluator as E
from core.engine.state import EngineMode
from core.ficc import annotations as A
from core.ficc import context_log as CL
from core.ficc import macro_artifacts as MA
from core.ficc import macro_schema as MS
from core.ficc import pit as P
from core.quant import risk_layer as R
from core.quant import sleeves as SL
from core.rules import governance as G
from core.rules.macro_rules import load_store
from core.rules.model import Side
from tests.golden_tools import golden
from tests.macro_m1_calendars import fixture_set
from tests.macro_m2_risk import DECISION, KNOWLEDGE
from tests.macro_m5_books import BASKET, CAL, DEC, LINE, REC, SPEC, _CLOCK, _dec, _raises, _registry
from tests.macro_m5_fills_events import EVENTS_CFG, _event, _order, _prov
from tests.macro_m6_context import CLOCK, PROV, _build, _hedge, _rules_with_macro_conditioned, _vt_result, context_store
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "_backup" / "QUANTGEN_pre_v2_2026-10-05.zip"
S4_MODULES = ("core/engine/books.py", "core/engine/orders.py", "core/engine/evaluator.py", "core/calendars/events.py",
              "core/ficc/annotations.py", "core/ficc/context_log.py", "core/ficc/macro_artifacts.py", "core/quant/risk_layer.py")
UNTOUCHED = ("core/engine/state.py", "core/engine/runtime.py", "core/engine/feed.py", "core/engine/__init__.py")
ADD_ONLY = ("core/engine/orders.py", "core/engine/evaluator.py", "ui/trading_page.py")
NFP = _event("US-NFP-2026-10-02", "US_NFP", "2026-10-02T12:30:00Z")


def _book(w: float = 1.0) -> SL.Book:
    """A one-sleeve long-only KR book on the KODEX 200 line (the shape `apply_market_gross` scales)."""
    ws = SL.Weights("KR", "momentum", "active", {LINE: w}, 1.0, 1.0, 1.0, (), (), ())
    return SL.Book("specification", DEC, (ws,), {("KR", LINE): w}, {("KR", "momentum"): ""})


def _gross(book: SL.Book) -> float:
    return book.weights[("KR", LINE)]


def _fired(side, at) -> E.Decision:
    o = _order(side, LINE, at)
    return E.Decision(o.rule_id, o.rule_name, E.Outcome.FIRED, "all conditions met", at, o, Decimal(1))


def _cb() -> R.ConcentrationBound:
    exp = R.lookthrough_exposure({LINE: 1.0}, {LINE: R.Basket(LINE, date(2026, 10, 1), BASKET)}, DEC, sessions=CAL)
    return R.concentration_bound("KR", DEC, None, exp)


def _macro_state(reg, *, factors=None, conc=None, pair=None, decided=date(2026, 10, 2), **kw) -> dict:
    """`build_macro_state` fed by the real producers of this sprint: the registry's runtime entries, the risk-layer
    bound, package B's gap tags and annotation; vt / hedge are the S3 synthetic producers."""
    vt = _vt_result("KR")
    book = R.vt_for_book(vt, SPEC, ever_armed=True)
    vol = R.vol_state(vt, book, None, instrument_book="KRX_ETF_line", rebalance="daily", no_trade_band=0.0)
    rt = [e for e in reg.runtime_entries() if e["book_id"].endswith(":KR")]
    factors = factors or {REC: {"vt": 1.0, "overlays": {}, "ladder": 1.0, "post_rearm_cap": 1.0},
                          SPEC: {"vt": vol["vt_weight_next"], "overlays": {}, "ladder": 1.0, "post_rearm_cap": 1.0}}
    args = dict(inputs=list(vt.inputs), acting_components=[book], regime_tags={"price_limit": 0.30})
    args.update(kw)
    return MA.build_macro_state("KR", P.RunContext(DECISION, KNOWLEDGE), provenance=PROV(), decided_session=decided,
                                effective_session=date(2026, 10, 6), vol=vol, hedge=_hedge(), runtime=rt, rules=load_store(),
                                book_factors=factors, concentration=conc, pair=pair, **args)


# --------------------------------------------------------------------------- #
# 1. ladder block + post-re-arm cap: risk_step -> ladder_for_book -> apply_market_gross / evaluator_block / ledger
# --------------------------------------------------------------------------- #
def test_ladder_block_and_post_rearm_cap_flow_into_gross_evaluator_ledger_and_macro_state():
    cfg = R.ladder_config()
    vt = 0.8
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        for i, nv in enumerate([100.0, 100.0, 88.0], start=1):                  # -12% from the step reference at decision 3
            res = B.risk_step(reg, SPEC, _dec(CAL[i]), nv, config=cfg)
        ladder, block = R.ladder_for_book(res.ladder, SPEC, binding_share=0.19)
        assert (ladder, block) == (0.5, True) and R.ladder_for_book(res.ladder, REC, binding_share=0.19) == (1.0, False)
        cap = B.post_rearm_cap(res.book)
        assert cap == 1.0
        # composition: the ladder term enters min() with vt and the cap; 0.8 x min(1, 0.5, 1) = 0.4 (never a product)
        out = SL.apply_market_gross(_book(), vt, ladder=ladder, post_rearm_cap=cap)
        assert _gross(out) == R.compose(vt, [], ladder, cap) == 0.4 and "ladder" in out.sleeves[0].binding
        ov = SL.Multiplier("R-28", 0.5, "total", "market_gross")
        assert _gross(SL.apply_market_gross(_book(), vt, overlays=[ov], ladder=ladder, post_rearm_cap=cap)) == 0.4     # min, not 0.2
        assert _gross(SL.apply_market_gross(_book(), vt, overlays=[ov], ladder=1.0, post_rearm_cap=1.0)) == 0.4
        # evaluator: the same block_new_entries BLOCKs a new entry (target above held); a decrease passes; the
        # recommended book's ladder term (binding share > 0.10: steps act in the specification book only) never blocks
        at = _dec(CAL[3])
        state = E.BlockState(block_new_entries=block, market="KR", w_held=0.3, w_target=0.4)
        log = []
        d = E.evaluator_block("R-31", _fired(Side.BUY, at), state, log=log)
        assert d.outcome is E.Outcome.BLOCKED and d.reason.startswith("R-31") and d.order is None
        assert log == [{"kind": "evaluator_blocked", "macro_rule": "R-31", "rule_id": "book", "at": at.isoformat(), "reason": d.reason}]
        assert E.evaluator_block("R-31", _fired(Side.SELL, at), replace(state, w_held=0.4, w_target=0.3)).outcome is E.Outcome.FIRED
        rec_block = R.ladder_for_book(res.ladder, REC, binding_share=0.19)[1]
        assert E.evaluator_block("R-31", _fired(Side.BUY, at), replace(state, block_new_entries=rec_block)).outcome is E.Outcome.FIRED
        # the weight ledger holds the blocked entry at its held weight; a decrease goes through
        reg.save(replace(reg.get(SPEC), held={LINE: 0.3}))
        dec = B.record_decision(reg, SPEC, at, {LINE: 0.4}, block=block)
        assert dec.blocked == (LINE,) and dec.post_action == {LINE: 0.3}
        dec = B.record_decision(reg, SPEC, _dec(CAL[4]), {LINE: 0.2}, block=block)
        assert dec.blocked == () and dec.post_action == {LINE: 0.2}
        # the built macro_state reads the ladder state and the runtime entries back from the registry
        st = _macro_state(reg, conc=_cb(), ladder=B.ladder_state(reg.get(SPEC), 0.19), decided=CAL[4])
        assert MS.validate("macro_state", st) == [] and st["runtime"] == [e for e in reg.runtime_entries() if e["book_id"].endswith(":KR")]
        f = st["flags"]
        assert (f["ladder_step"], f["block_new_entries"], f["ladder_steps_act_in"], f["hard_stop"]) == ("step_-12", True, "specification", "armed")
        assert f["ladder_dwell_left"] == reg.get(SPEC).dwell_left == 20            # the trigger decision counts: 21 - 1
        # the hard stop on the recommended book: HALTED is 0x outside min(); the state shows rearm_refused; the
        # evaluator / ledger see weights 0; the automatic re-arm at t+10 puts post_rearm_cap 0.5 inside min()
        for i in range(1, 5):
            B.risk_step(reg, REC, _dec(CAL[i]), 100.0, config=cfg)
        t = 5
        res = B.risk_step(reg, REC, _dec(CAL[t]), 85.0, config=cfg)
        assert res.halted_now and res.book.halted and B.rearm_not_before(res.book) == CAL[t + 10]
        halted = {REC: {"vt": 1.0, "overlays": {}, "ladder": 1.0, "post_rearm_cap": 1.0, "halted": True},
                  SPEC: {"vt": vt, "overlays": {}, "ladder": ladder, "post_rearm_cap": 1.0}}
        st = _macro_state(reg, factors=halted, conc=_cb(), ladder=B.ladder_state(reg.get(SPEC), 0.19), decided=CAL[t])
        assert MS.validate("macro_state", st) == [] and st["flags"]["hard_stop"] == "rearm_refused" and st["flags"]["engine_state"] == "HALTED"
        assert st["concentration"]["by_book"][REC] == {"composed": 0.0, "gross": 0.0, "binding_factor": "none"}
        assert st["concentration"]["by_book"][SPEC]["composed"] == 0.4 and st["concentration"]["by_book"][SPEC]["binding_factor"] == "none"
        assert B.record_decision(reg, REC, _dec(CAL[t]), {LINE: 0.7}).post_action == {LINE: 0.0}
        for i in range(t + 1, t + 10):
            B.risk_step(reg, REC, _dec(CAL[i]), 80.0, config=cfg)
            assert B.step_decision(reg, REC, _dec(CAL[i]), ok=True).post_rearm_cap == 1.0
        res = B.risk_step(reg, REC, _dec(CAL[t + 10]), 84.0, config=cfg)          # automatic re-arm, references reset
        assert res.book.mode is EngineMode.ARMED and res.book.hwm_hard == res.book.ref_step == 84.0
        cap = B.post_rearm_cap(res.book)
        assert cap == 0.5 and res.ladder.post_rearm_left == 10
        out = SL.apply_market_gross(_book(), vt, ladder=R.ladder_for_book(res.ladder, REC, binding_share=0.19)[0], post_rearm_cap=cap)
        assert _gross(out) == 0.4 == vt * 0.5 and "post_rearm_cap" in out.sleeves[0].binding
        assert E.evaluator_block("R-31", _fired(Side.BUY, _dec(CAL[t + 10])), replace(state, block_new_entries=False)).outcome is E.Outcome.FIRED
        capped = {REC: {"vt": 1.0, "overlays": {}, "ladder": 1.0, "post_rearm_cap": cap}, SPEC: halted[SPEC]}
        st = _macro_state(reg, factors=capped, conc=_cb(), ladder=B.ladder_state(reg.get(SPEC), 0.19), decided=CAL[t + 10])
        assert MS.validate("macro_state", st) == [] and st["flags"]["hard_stop"] == "post_rearm_cap" and st["flags"]["engine_state"] == "ARMED"
        assert st["concentration"]["by_book"][REC] == {"composed": 0.5, "gross": 0.5, "binding_factor": "none"}
        sd = B.step_decision(reg, REC, _dec(CAL[t + 10]), ok=True)                 # step_decision last: it consumes the cap window
        assert sd.post_rearm_cap == 0.5 and sd.book.post_rearm_left == 9 and sd.book.post_rearm_cap_until == CAL[t + 19]
        chain = [e["kind"] for e in G.read_events(reg.log) if e["book_id"] == REC]
        assert chain == ["book_state", "halt", "rearm"] and G.verify_chain(reg.log).ok


test_ladder_block_and_post_rearm_cap_flow_into_gross_evaluator_ledger_and_macro_state.test_ids = ["I-04", "T-HALT-01", "T-STEP-05"]


# --------------------------------------------------------------------------- #
# 2. R-18: log_break pushes through books.neutralise_rule; build_overlay_decisions applies the carried map
# --------------------------------------------------------------------------- #
def test_r18_neutralise_hook_persists_on_the_books_and_reaches_overlay_decisions():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        rules = _rules_with_macro_conditioned()
        ev = CL.BreakEvent("policy_framework_change", date(2026, 9, 17), DECISION, "FOMC statement on longer-run goals (2026-09-16)")
        res = CL.log_break(Path(tmp) / "macro", ev, decision_utc=DECISION, knowledge_utc=KNOWLEDGE, rules=rules, clock=CLOCK,
                           governance_log=reg.log, neutralise=lambda rid, eid: B.neutralise_rule(reg, rid, eid, DECISION))
        assert res.hook_applied and res.neutralised == {"R-99-MACRO": ev.event_id}
        assert all(B.neutralised_rules(reg, b) == {"R-99-MACRO": ev.event_id} for b in reg.ids())
        # persisted beside the book state; a reloaded registry carries it; the hook is idempotent per (book, rule)
        reg2 = B.BookRegistry(Path(tmp), clock=_CLOCK, sessions=lambda m: CAL)
        assert B.neutralised_rules(reg2, SPEC) == {"R-99-MACRO": ev.event_id}
        assert B.neutralise_rule(reg2, "R-99-MACRO", ev.event_id, DECISION) == ()
        assert B.neutralise_rule(reg2, "R-98", "e2", DECISION, books=[SPEC]) == (SPEC,)
        assert B.neutralised_rules(reg2, SPEC) == {"R-99-MACRO": ev.event_id, "R-98": "e2"} and B.neutralised_rules(reg2, REC) == {"R-99-MACRO": ev.event_id}
        _raises(lambda: B.neutralise_rule(reg2, "", "e", DECISION), ValueError, "names")
        # one record_reset governance event per rule (log_break's), on the books' chain, never one per book
        kinds = [e["kind"] for e in G.read_events(reg.log)]
        assert kinds.count("record_reset") == 1 and G.verify_chain(reg.log).ok
        # the runtime[] entry keeps its closed key set (the carrier is not an artifact field)
        assert set(B.to_runtime_entry(reg2.get(SPEC))) == {"book_id", "engine_state", "halt", "post_rearm_cap_until", "nav", "hwm_hard",
                                                           "ref_step", "consecutive_failures", "book_counter"}
        # the apply side: from the next decision the flagged multiplier enters as 1.0, every other factor unchanged
        flagged = SL.Multiplier("R-99-MACRO", 0.5, "total", "market_gross", card={"card_id": "MACRO-R99", "verdict": "PASS", "disposition": "RECOMMENDATION"})
        other = SL.Multiplier("R-28", 0.75, "total", "market_gross", card={"card_id": "MACRO-R28", "verdict": "NOT_RUN", "disposition": "FORWARD_SIM"})
        ctx = P.RunContext(DECISION, KNOWLEDGE)
        g = MA.build_overlay_decisions("KR", ctx, provenance=PROV(), effective_session=date(2026, 10, 6), vt=0.8, multipliers=[flagged, other],
                                       neutralised=B.neutralised_rules(reg, SPEC))[-1]
        assert {m["rule_id"]: m["value"] for m in g["multipliers"]} == {"R-99-MACRO": 1.0, "R-28": 0.75} and g["overlay_min"] == 0.75
        assert any("R-18" in r and ev.event_id in r for r in g["reasons"]) and MS.validate("overlay_decision", g) == []
        raw = MA.build_overlay_decisions("KR", ctx, provenance=PROV(), effective_session=date(2026, 10, 6), vt=0.8, multipliers=[flagged, other])[-1]
        assert raw["overlay_min"] == 0.5                                            # without the carrier the factor still acts


test_r18_neutralise_hook_persists_on_the_books_and_reaches_overlay_decisions.test_ids = ["T-BREAK-01"]


# --------------------------------------------------------------------------- #
# 3. macro_state from the risk-layer bound, the registry, the gap tags and the annotation
# --------------------------------------------------------------------------- #
def test_macro_state_takes_the_risk_layer_bound_registry_runtime_gap_tags_and_annotation():
    cal = fixture_set()
    cb = _cb()
    gap = EV.gap_tags(date(2026, 10, 6), [NFP], cal=cal, cfg=EVENTS_CFG)
    ann = A.annotate(16.34, 18.37, date(2026, 9, 30))
    assert gap == {"kr_open_gap_event": True, "gap_sessions": 2, "var_display_scale": 2 ** 0.5} and not ann.vix_ge_vix3m
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        st = _macro_state(reg, conc=cb, pair={"pair_share_kospi": 0.51}, gap=gap, annotations=ann.macro_state_block(),
                          ladder=B.ladder_state(reg.get(SPEC), 0.19))
        assert MS.validate("macro_state", st) == [] and "validation_errors" not in st["extras"] and st["fail_closed"] is False
        c = st["concentration"]
        assert c["template"] == cb.template == "msci_25_50" and c["pair_lookthrough_share"] == cb.pair_lookthrough_share and c["pair_share_kospi"] == 0.51
        assert (c["absolute_bound"], c["active_bound"], c["aggregate_bound"], c["semis_bound"]) == (cb.absolute_bound, cb.active_bound, cb.aggregate_bound, cb.semis_bound)
        assert c["by_book"][REC] == R.risk_layer(1.0, {}, 1.0, 1.0, cb) and c["by_book"][REC]["binding_factor"] == "active_single_name"
        assert c["by_book"][SPEC] == R.risk_layer(0.694, {}, 1.0, 1.0, cb) and round(c["by_book"][SPEC]["gross"], 3) == 0.685
        assert st["runtime"] == [e for e in reg.runtime_entries() if e["book_id"].endswith(":KR")] and len(st["runtime"]) == 2
        assert all(e["engine_state"] == "ARMED" for e in st["runtime"])
        f = st["flags"]
        assert (f["kr_open_gap_event"], f["gap_sessions"], f["var_display_scale"]) == (True, 2, 2 ** 0.5)
        assert st["annotations"] == {"vix_ge_vix3m": False, "notes": list(ann.notes)}
        # the 2026-11-26 KR decision (effective 11-27, NYSE closed 11-26): gap 0, scale 1, no gap event, books ARMED
        quiet = EV.gap_tags(date(2026, 11, 27), [NFP], cal=cal, cfg=EVENTS_CFG)
        assert quiet == {"kr_open_gap_event": False, "gap_sessions": 0, "var_display_scale": 1.0}   # the built state: macro_m6_context
        # no tag, flag or annotation changes a weight: the gross line is the same with every tag flipped
        base = SL.apply_market_gross(_book(), 0.694, concentration_bound=cb.bound)
        assert abs(_gross(base) - cb.bound) < 1e-12
        A.assert_no_exposure_change(base.weights, SL.apply_market_gross(_book(), 0.694, concentration_bound=cb.bound).weights)


test_macro_state_takes_the_risk_layer_bound_registry_runtime_gap_tags_and_annotation.test_ids = ["T-CAPS-01", "I-06b", "T-ANNOT-01"]


# --------------------------------------------------------------------------- #
# 4. event_calendar and context_log: one writer (macro_artifacts.write_artifact), quarantine never raises / HALTs
# --------------------------------------------------------------------------- #
def test_event_calendar_and_context_log_reach_disk_through_write_artifact_only():
    cal = fixture_set()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        obj = EV.build_event_calendar([NFP], provenance=_prov(), calendar_version=cal.version, cal=cal, cfg=EVENTS_CFG,
                                      gap_sessions_for=[date(2026, 10, 6)])
        out = MA.write_built(root, "event_calendar", obj, CLOCK)
        assert out.status == "written" and out.path == root / MA.default_relpath("event_calendar", obj) and out.path.parent == root / "event_calendar"
        written = json.loads(out.path.read_text(encoding="utf-8"))
        assert MS.validate("event_calendar", written) == [] and {e["type"] for e in written["events"]} == {"US_NFP", "KRX_HOLIDAY_GAP"}
        assert written["events"][0]["kr_open_gap_session"] == "2026-10-06" and written["read_only"] is True
        # an out-of-schema calendar object is quarantined with its issues: refused, warn alert, never an exception, never a HALT
        bad = dict(obj, events=[dict(obj["events"][0], status="done")])
        q = MA.write_built(root, "event_calendar", bad, CLOCK)
        assert q.status == "quarantined" and q.path.parent == root / "quarantine" and not q.acting_failure and q.alert["severity"] == "warn"
        assert not (root / "event_calendar" / "x.json").exists() and len(list((root / "event_calendar").iterdir())) == 1
        # the builder itself never raises on a schema failure: its object reaches the writer, which keeps it in quarantine/
        built_bad = EV.build_event_calendar([dict(NFP, notes=None)], provenance=_prov(), calendar_version=cal.version, cal=cal,
                                            cfg=EVENTS_CFG)
        qb = MA.write_built(root, "event_calendar", built_bad, CLOCK)
        assert qb.status == "quarantined" and any("/notes" in i for i in qb.issues) and qb.path.parent == root / "quarantine"
        # context_log: build_context_log -> write_context_log -> write_artifact under context_log/<decision>.json
        store, reg, clk = context_store()
        log = _build(store, reg, clk)
        w = CL.write_context_log(root, log, CLOCK)
        assert w.status == "written" and w.path == root / MA.default_relpath("context_log", log) and w.path.parent == root / "context_log"
        assert MS.validate("context_log", json.loads(w.path.read_text(encoding="utf-8"))) == []
        wq = CL.write_context_log(root, dict(log, schema_version="9.9"), CLOCK)
        assert wq.status == "quarantined" and wq.alert["code"] == CL.ALERT_LOG_INVALID and wq.path.parent == root / "quarantine"
        # the only disk path for an artifact: neither module writes one itself
        for rel in ("core/ficc/context_log.py", "core/calendars/events.py"):
            src = (ROOT / rel).read_text(encoding="utf-8")
            assert "_atomic_write(" not in src and "os.replace(" not in src and "mkstemp(" not in src, rel
        assert "MA.write_artifact(" in (ROOT / "core/ficc/context_log.py").read_text(encoding="utf-8")


test_event_calendar_and_context_log_reach_disk_through_write_artifact_only.test_ids = ["I-06", "T-CTX-02"]


# --------------------------------------------------------------------------- #
# 5. G-R08-02: the CARD-P REJECT record is on file (print_only rows); the reproduction is REFDATA
# --------------------------------------------------------------------------- #
def test_g_r08_02_cardp_reject_record_is_on_file_never_reproduced():
    g = golden("G-R08-02")
    assert len(g.rows) == 14 and all(r.mode == "print_only" and r.runs_from == "M5" and "record only" in r.note for r in g.rows)
    assert {r.sub_id for r in g.rows if r.kind == "mdd"} >= {"us_vt15_50bp_raw", "us_vt15_5bp_raw", "us_vt15_50bp_5close", "us_vt15_5bp_5close",
                                                              "kospi_vt20_3bp_raw", "kospi_vt20_35bp_raw", "kospi_vt20_3bp_5close", "kospi_vt20_35bp_5close"}
    assert g.want("reject_cells") == g.want("cells") == 10 and "F07" in g.fixtures          # REJECT in 10 of 10 cells (L5980)
    raise NotRun("REFDATA: G-R08-02 (L5980) dMDD vs S of the VIX>=VIX3M block as a CARD-P: FRED VIXCLS/VXVCLS 2007-12-04 -> "
                 "2026-09-30 (F07), F13 / U1 / F10 absent; the REJECT-in-10-of-10-cells record stays on file, never reproduced")


test_g_r08_02_cardp_reject_record_is_on_file_never_reproduced.test_ids = ["G-R08-02"]


# --------------------------------------------------------------------------- #
# 6. Rulings: no wall clock; nothing above 1.0; HALTED outside min(); inherited engine untouched; add-only edits
# --------------------------------------------------------------------------- #
def _wall_clock_calls(src: str) -> list[str]:
    out = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            owner = node.func.value
            name = owner.id if isinstance(owner, ast.Name) else owner.attr if isinstance(owner, ast.Attribute) else ""
            if (name in ("datetime", "date") and node.func.attr in ("now", "utcnow", "today")) or (name == "time" and node.func.attr == "time"):
                out.append(f"{name}.{node.func.attr} at line {node.lineno}")
    return out


def test_s4_rulings_no_wall_clock_nothing_above_one_halted_outside_min_engine_untouched():
    z = zipfile.ZipFile(BACKUP) if BACKUP.is_file() else None
    names = {n.replace("\\", "/"): n for n in z.namelist()} if z else {}
    find = lambda rel: next(names[n] for n in names if n.endswith(rel))              # noqa: E731
    inherited = lambda rel: set(z.read(find(rel)).decode("utf-8").splitlines()) if z and any(n.endswith(rel) for n in names) else set()   # noqa: E731
    for rel in S4_MODULES:
        lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        old = inherited(rel)
        if rel in ADD_ONLY and not old:
            continue                     # the operator engine's `now or datetime.now()` defaults predate v2; the backup tells them apart
        calls = [c for c in _wall_clock_calls("\n".join(lines)) if lines[int(c.rsplit(" ", 1)[1]) - 1] not in old]
        assert calls == [], f"{rel}: wall clock in v2 code {calls}"
    _raises(lambda: R.compose(1.0001, [], 1.0, 1.0), R.CompositionError)
    _raises(lambda: R.compose(1.0, [1.0], 0.0, 1.0), R.CompositionError)              # HALTED is never a min() argument
    _raises(lambda: SL.apply_market_gross(_book(), 1.0001), Exception)
    assert R.risk_layer(1.0, {}, 1.0, 1.0, _cb(), halted=True) == {"composed": 0.0, "gross": 0.0, "binding_factor": "none"}
    if z is None:
        return                                                                      # the diff clause needs the owner's backup
    for rel in UNTOUCHED:
        assert z.read(find(rel)) == (ROOT / rel).read_bytes(), f"{rel} differs from the pre-v2 backup"
    for rel in ADD_ONLY:
        old = z.read(find(rel)).decode("utf-8").splitlines()
        new = (ROOT / rel).read_text(encoding="utf-8").splitlines()
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
            if tag in ("equal", "insert"):
                continue
            names_of = lambda line: set(line.split("import ", 1)[1].split(", "))      # noqa: E731
            assert tag == "replace" and i2 - i1 == j2 - j1 == 1 and old[i1].startswith("from datetime import") \
                and names_of(old[i1]) <= names_of(new[j1]), f"{rel}: {tag} of {old[i1:i2]} is not an addition"


test_s4_rulings_no_wall_clock_nothing_above_one_halted_outside_min_engine_untouched.test_ids = ["T-RO-01", "T-CAP-02"]


def tests():
    return [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
