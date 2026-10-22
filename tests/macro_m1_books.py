"""M1 package C tests: per-book runtime (core/engine/books.py; TASK-M1-20, TASK-M1-17).

Spec tests: T-ROLE-01 and T-MISS-02 (HALT clauses), T-LAG-01 (runtime clause). The RISK cycle, causes[] merge,
persistence and governance tests are the carrier that M5 (T-HALT-01, I-04b, T-STEP-05) and M8 (T-OBS-01,
T-SCOPE-01) hook into; they carry no M5/M8 id here.
Hermetic: every registry lives in a tempfile directory; the session calendar is a weekday stub; the clock is pinned.
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from core.engine import books as B
from core.engine.state import EngineMode
from core.ficc import macro_schema as S
from core.rules import governance as G

_CLOCK = lambda: datetime(2026, 10, 6, 7, 0, 0, tzinfo=timezone.utc)   # noqa: E731
CAL = [d for d in (date(2026, 9, 1) + timedelta(days=i) for i in range(120)) if d.weekday() < 5]   # weekday stub
SID = "KOSPI_OFFICIAL_CLOSE"
REC, SPEC = "recommended:KR", "specification:KR"


def _dec(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 6, 30, 30, tzinfo=timezone.utc)


def _registry(tmp, **kw) -> B.BookRegistry:
    reg = B.BookRegistry(Path(tmp), clock=_CLOCK, sessions=lambda m: CAL, **kw)
    B.create_default_books(reg, ["KR", "US"])
    for bid in (REC, SPEC, "recommended:US", "specification:US"):
        B.arm(reg, bid, _dec(CAL[0]))
    return reg


def _kinds(reg, bid=None):
    return [e["kind"] for e in G.read_events(reg.log) if bid is None or e["book_id"] == bid]


# --------------------------------------------------------------------------- #
# book ids and defaults
# --------------------------------------------------------------------------- #
def test_book_ids_and_default_books():
    assert B.parse_book_id("recommended:KR") == ("recommended", "KR")
    assert B.parse_book_id("specification:CRYPTO") == ("specification", "CRYPTO")
    assert B.parse_book_id("forward_sim:R-28") == ("forward_sim", None)
    assert B.parse_book_id("refusal:R-11") == ("refusal", None)
    assert B.parse_book_id("card:MACRO-R06-KR-ETF:S") == ("card", None)
    for bad in ("recommended:KRX", "engine", "card:X:maybe", "forward_sim:", "recommended:kr", ""):
        try:
            B.parse_book_id(bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    assert B.BookRuntime("recommended:KR").market == "KR" and B.BookRuntime("forward_sim:R-28").market is None
    try:
        B.BookRuntime("recommended:KR", market="US")
        raise AssertionError("market mismatch accepted")
    except ValueError:
        pass
    with tempfile.TemporaryDirectory() as tmp:
        reg = B.BookRegistry(Path(tmp))
        made = B.create_default_books(reg, ["KR", "US"])
        assert [b.book_id for b in made] == [REC, SPEC, "recommended:US", "specification:US"]
        assert all(b.mode is EngineMode.DISARMED and not b.ever_armed and b.halt is None for b in made)
        assert B.create_default_books(reg, ["KR"]) == made[:2]            # idempotent
        assert sorted(p.name for p in (Path(tmp) / "books").iterdir()) == sorted(
            B._file_name(b.book_id) for b in made)
        assert not reg.log.exists()                                        # registration is not an event


test_book_ids_and_default_books.test_ids = []


# --------------------------------------------------------------------------- #
# RISK cycle carrier: HALT -> refused re-arm -> auto re-arm at t+10 -> cap for 10 decisions -> normal
# --------------------------------------------------------------------------- #
def test_risk_cycle_refusal_window_rearm_and_cap():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        reg.save(replace(reg.get(REC), nav=100.0, hwm_hard=120.0, ref_step=110.0))
        t = CAL[5]
        b = B.runtime_halt(reg, REC, "RISK", "hard_stop", _dec(t), component="drawdown_ladder")
        assert b.halted and b.halt["class"] == "RISK" and b.halt["reason_code"] == "hard_stop"
        assert b.halt["rearm_mode"] == "auto" and b.halt["rearm_not_before"] == CAL[15].isoformat()
        assert b.halt["since_utc"] == "2026-09-08T06:30:30Z" and b.halt["component"] == "drawdown_ladder"
        assert b.hwm_hard == 120.0 and b.ref_step == 110.0                 # a HALT never resets a reference
        n_events = len(G.read_events(reg.log))
        assert B.runtime_halt(reg, REC, "RISK", "hard_stop", _dec(CAL[7])) == b     # idempotent: no extension
        assert len(G.read_events(reg.log)) == n_events
        for i in range(6, 15):                                             # t+1 .. t+9: refused
            res = B.step_decision(reg, REC, _dec(CAL[i]), ok=True)
            assert res.book.halted and res.post_rearm_cap == 1.0
        try:
            B.runtime_rearm(reg, REC, "operator", _dec(CAL[14]), operator="kim")   # the window binds the operator too
            raise AssertionError("re-arm inside the refusal window")
        except B.RearmRefused as exc:
            assert "refused before 2026-09-22" in str(exc)
        assert reg.get(REC).halted
        res = B.step_decision(reg, REC, _dec(CAL[15]), ok=True)            # t+10: automatic re-arm
        b = res.book
        assert b.mode is EngineMode.ARMED and b.halt is None and res.post_rearm_cap == 0.5
        assert b.hwm_hard == b.ref_step == b.nav == 100.0                  # hard stop: references reset to NAV
        assert b.post_rearm_cap_until == CAL[24] and b.post_rearm_left == 9
        for i in range(16, 25):                                            # t+11 .. t+19 still capped
            assert B.step_decision(reg, REC, _dec(CAL[i]), ok=True).post_rearm_cap == 0.5
        res = B.step_decision(reg, REC, _dec(CAL[25]), ok=True)            # t+20: normal running
        assert res.post_rearm_cap == 1.0 and res.book.post_rearm_left == 0
        assert _kinds(reg, REC) == ["book_state", "halt", "rearm"]
        # a risk-limit breach resets no reference; a RISK reason outside the list is refused
        reg.save(replace(reg.get(REC), nav=90.0, hwm_hard=100.0, ref_step=95.0))
        B.runtime_halt(reg, REC, "RISK", "risk_limit_breach", _dec(CAL[26]))
        b = B.runtime_rearm(reg, REC, "auto", _dec(CAL[36]))
        assert b.mode is EngineMode.ARMED and (b.hwm_hard, b.ref_step) == (100.0, 95.0) and b.post_rearm_left == 10
        for bad in (("RISK", "calendar_coverage"), ("DANGER", "hard_stop"), ("OPS", "")):
            try:
                B.runtime_halt(reg, REC, bad[0], bad[1], _dec(CAL[37]))
                raise AssertionError(bad)
            except ValueError:
                pass
        # a RISK HALT without a session calendar or a primary market fails closed
        reg.register(B.BookRuntime("forward_sim:R-28"))
        B.arm(reg, "forward_sim:R-28", _dec(CAL[0]))
        try:
            B.runtime_halt(reg, "forward_sim:R-28", "RISK", "hard_stop", _dec(CAL[37]))
            raise AssertionError("RISK without a market")
        except ValueError:
            pass
        assert B.runtime_halt(reg, "forward_sim:R-28", "OPS", "calendar_coverage", _dec(CAL[37])).halted


test_risk_cycle_refusal_window_rearm_and_cap.test_ids = []


# --------------------------------------------------------------------------- #
# T-ROLE-01 / T-MISS-02: OPS HALT at the counter limit, scope, automatic re-arm when fresh
# --------------------------------------------------------------------------- #
def test_ops_halt_counters_scope_and_auto_rearm():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        res = B.step_decision(reg, SPEC, _dec(CAL[1]), ok=False, failed=[SID])      # miss 1: fail closed only
        assert res.book.mode is EngineMode.ARMED and res.book.consecutive_failures == {SID: 1} and res.book.book_counter == 1
        res = B.step_decision(reg, SPEC, _dec(CAL[2]), ok=False, failed=[SID])      # miss 2: HALTED (OPS)
        b = res.book
        assert b.halted and b.halt["class"] == "OPS" and b.halt["reason_code"] == "acting_input_stale:" + SID
        assert b.halt["series_id"] == SID and b.halt["rearm_mode"] == "auto" and b.halt["rearm_not_before"] is None
        assert b.consecutive_failures == {SID: 2} and b.book_counter == 2
        assert reg.get(REC).mode is EngineMode.ARMED and reg.get("recommended:US").mode is EngineMode.ARMED   # scope
        assert reg.get(REC).consecutive_failures == {} and reg.get(REC).book_counter == 0
        assert B.step_decision(reg, SPEC, _dec(CAL[3]), ok=False, failed=[SID]).book.halt["causes"].__len__() == 1
        res = B.step_decision(reg, SPEC, _dec(CAL[4]), ok=True)                      # fresh: counters reset, re-armed
        b = res.book
        assert b.mode is EngineMode.ARMED and b.halt is None and b.consecutive_failures == {} and b.book_counter == 0
        assert res.post_rearm_cap == 1.0 and b.post_rearm_cap_until is None          # OPS: no cap, no reset
        assert _kinds(reg, SPEC) == ["book_state", "halt", "rearm"] and _kinds(reg, REC) == ["book_state"]
        # two inputs failing on alternate decisions HALT at the 2nd (book counter)
        B.step_decision(reg, SPEC, _dec(CAL[5]), ok=False, failed=["A"])
        b = B.step_decision(reg, SPEC, _dec(CAL[6]), ok=False, failed=["B"]).book
        assert b.halted and b.halt["reason_code"] == B.BOOK_COUNTER_REASON and b.halt["series_id"] == "B"
        assert b.consecutive_failures == {"B": 1} and b.book_counter == 2
        assert B.step_decision(reg, SPEC, _dec(CAL[7]), ok=True).book.mode is EngineMode.ARMED
        # a declared limit of 5 (KODEX basket) counts neither on the book counter nor as a HALT at 2
        for i in range(8, 12):
            b = B.step_decision(reg, SPEC, _dec(CAL[i]), ok=False, failed=["KODEX200_PDF"], limits={"KODEX200_PDF": 5}).book
            assert b.mode is EngineMode.ARMED and b.book_counter == 0, i
        b = B.step_decision(reg, SPEC, _dec(CAL[12]), ok=False, failed=["KODEX200_PDF"], limits={"KODEX200_PDF": 5}).book
        assert b.halted and b.halt["reason_code"] == "acting_input_stale:KODEX200_PDF" and b.consecutive_failures == {"KODEX200_PDF": 5}
        B.step_decision(reg, SPEC, _dec(CAL[13]), ok=True)
        # an acting step error with no named series counts on the book counter (run_error)
        B.step_decision(reg, SPEC, _dec(CAL[14]), ok=False)
        b = B.step_decision(reg, SPEC, _dec(CAL[15]), ok=False).book
        assert b.halted and b.halt["reason_code"] == B.STEP_ERROR_REASON and b.halt["series_id"] is None
        # a fresh decision clears only input causes: another OPS cause keeps the book HALTED
        B.runtime_halt(reg, SPEC, "OPS", "calendar_coverage", _dec(CAL[15]))
        b = B.step_decision(reg, SPEC, _dec(CAL[16]), ok=True).book
        assert b.halted and [c["reason_code"] for c in b.halt["causes"] if c["cleared_utc"]] == [B.STEP_ERROR_REASON]
        assert b.halt["reason_code"] == B.STEP_ERROR_REASON                       # top level restates causes[0]
        b = B.runtime_rearm(reg, SPEC, "auto", _dec(CAL[16]), cleared=["calendar_coverage"])
        assert b.mode is EngineMode.ARMED
        try:
            B.step_decision(reg, SPEC, _dec(CAL[17]), ok=True, failed=[SID])
            raise AssertionError("ok=True with failed inputs")
        except ValueError:
            pass


test_ops_halt_counters_scope_and_auto_rearm.test_ids = ["T-ROLE-01", "T-MISS-02"]


# --------------------------------------------------------------------------- #
# T-LAG-01 runtime clause: lag-audit and acting-schema causes need an operator re-arm
# --------------------------------------------------------------------------- #
def test_lag_audit_and_schema_failure_need_operator_rearm():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        b = B.runtime_halt(reg, REC, "OPS", "lag_audit_violation", _dec(CAL[1]), component="lag_audit", series_id=SID)
        assert b.halted and b.halt["rearm_mode"] == "operator" and b.halt["causes"][0]["rearm_mode"] == "operator"
        assert reg.get(SPEC).mode is EngineMode.ARMED                               # only the books the input feeds
        assert B.step_decision(reg, REC, _dec(CAL[2]), ok=True).book.halted         # a fresh decision does not re-arm
        for kw in (dict(mode="auto"), dict(mode="operator")):                       # auto refused; operator unnamed refused
            try:
                B.runtime_rearm(reg, REC, kw["mode"], _dec(CAL[2]))
                raise AssertionError(kw)
            except (B.RearmRefused, ValueError):
                pass
        assert reg.get(REC).halted
        b = B.runtime_rearm(reg, REC, "operator", _dec(CAL[3]), operator="kim")
        assert b.mode is EngineMode.ARMED and b.post_rearm_left == 0 and b.hwm_hard is None
        events = [e for e in G.read_events(reg.log) if e["book_id"] == REC]
        assert events[-1]["kind"] == "rearm" and events[-1]["actor"] == "operator" and "kim" in events[-1]["reason"]
        for code in ("acting_field_schema_or_bounds_failure", "operator_kill"):
            b = B.runtime_halt(reg, REC, "OPS", code, _dec(CAL[4]))
            assert b.halt["rearm_mode"] == "operator", code
            B.runtime_rearm(reg, REC, "operator", _dec(CAL[5]), operator="kim")
        for code in ("calendar_coverage", "feed_heartbeat_loss_60s", "whole_book_nav_unavailable_gt_2_decisions"):
            assert B.runtime_halt(reg, REC, "OPS", code, _dec(CAL[6])).halt["rearm_mode"] == "auto", code
            B.runtime_rearm(reg, REC, "auto", _dec(CAL[7]))


test_lag_audit_and_schema_failure_need_operator_rearm.test_ids = ["T-LAG-01"]


# --------------------------------------------------------------------------- #
# causes[] merge, acknowledgement
# --------------------------------------------------------------------------- #
def test_causes_merge_and_acknowledge():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        b = B.runtime_halt(reg, REC, "OPS", "acting_input_stale:" + SID, _dec(CAL[2]), series_id=SID)
        b = B.runtime_halt(reg, REC, "RISK", "hard_stop", _dec(CAL[3]))
        assert [c["reason_code"] for c in b.halt["causes"]] == ["acting_input_stale:" + SID, "hard_stop"]
        assert b.halt["class"] == "OPS" and b.halt["since_utc"] == "2026-09-03T06:30:30Z"     # restates causes[0]
        assert b.halt["rearm_mode"] == "auto" and b.halt["causes"][1]["rearm_not_before"] == CAL[13].isoformat()
        assert b.halt["series_id"] == SID
        b = B.runtime_halt(reg, REC, "OPS", "lag_audit_violation", _dec(CAL[4]))
        assert b.halt["rearm_mode"] == "operator" and len(b.halt["causes"]) == 3
        assert B.runtime_halt(reg, REC, "RISK", "hard_stop", _dec(CAL[5])).halt == b.halt   # idempotent per cause
        assert len(_kinds(reg, REC)) == 4                                            # book_state + 3 halts
        b = B.acknowledge(reg, REC, "kim", _dec(CAL[5]))
        assert b.halt["ack_by"] == "kim" and b.halt["ack_utc"] == "2026-09-08T06:30:30Z" and b.halted
        # fresh inputs clear the input cause only; the operator clears the lag cause; RISK waits for t+10
        b = B.step_decision(reg, REC, _dec(CAL[6]), ok=True).book
        assert b.halted and b.halt["causes"][0]["cleared_utc"] == "2026-09-09T06:30:30Z"
        assert b.halt["causes"][1]["cleared_utc"] is None and b.halt["rearm_mode"] == "operator"
        try:
            B.runtime_rearm(reg, REC, "operator", _dec(CAL[7]), operator="kim")
            raise AssertionError("RISK window ignored")
        except B.RearmRefused:
            pass
        b = reg.get(REC)
        assert b.halt["causes"][2]["cleared_utc"] is not None and b.halt["rearm_mode"] == "auto"   # partial clear kept
        b = B.runtime_rearm(reg, REC, "auto", _dec(CAL[13]))
        assert b.mode is EngineMode.ARMED and b.post_rearm_left == 10 and b.halt is None
        assert _kinds(reg, REC)[-2:] == ["book_state", "rearm"]
        # acknowledging a book that is not HALTED is refused; a HALT on a DISARMED book is a no-op
        try:
            B.acknowledge(reg, REC, "kim", _dec(CAL[14]))
            raise AssertionError("ack on an ARMED book")
        except ValueError:
            pass
        B.retire(reg, REC, _dec(CAL[14]), by="owner")
        assert B.runtime_halt(reg, REC, "OPS", "operator_kill", _dec(CAL[15])).mode is EngineMode.DISARMED


test_causes_merge_and_acknowledge.test_ids = []


# --------------------------------------------------------------------------- #
# persistence round trip, governance chain
# --------------------------------------------------------------------------- #
def test_persistence_round_trip_and_governance_chain():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        B.runtime_halt(reg, SPEC, "RISK", "hard_stop", _dec(CAL[2]))
        B.runtime_halt(reg, SPEC, "OPS", "lag_audit_violation", _dec(CAL[3]), series_id=SID)
        B.acknowledge(reg, SPEC, "kim", _dec(CAL[3]))
        B.step_decision(reg, REC, _dec(CAL[3]), ok=False, failed=["A"], limits={"A": 5})
        B.runtime_halt(reg, "recommended:US", "RISK", "hard_stop", _dec(CAL[4]))
        B.runtime_rearm(reg, "recommended:US", "auto", _dec(CAL[14]))
        before = reg.all()
        again = B.BookRegistry(Path(tmp), clock=_CLOCK, sessions=lambda m: CAL)
        assert again.all() == before and again.ids() == reg.ids()
        us = again.get("recommended:US")
        assert us.post_rearm_cap_until == CAL[23] and us.post_rearm_left == 10 and us.switch_counts == {
            "DISARMED->ARMED": 1, "ARMED->HALTED": 1, "HALTED->ARMED": 1}
        raw = json.loads((Path(tmp) / "books" / B._file_name(SPEC)).read_text(encoding="utf-8"))
        assert raw["version"] == 1 and raw["mode"] == "HALTED" and raw["halt"]["ack_by"] == "kim" and raw["ever_armed"]
        assert not list((Path(tmp) / "books").glob("*.tmp"))
        # the log: every HALT, re-arm, arm and acknowledgement is one chained, schema-valid line
        assert G.verify_chain(reg.log).ok
        events = G.read_events(reg.log)
        assert [e["kind"] for e in events if e["book_id"] == SPEC] == ["book_state", "halt", "halt", "book_state"]
        assert [e["kind"] for e in events if e["book_id"] == "recommended:US"] == ["book_state", "halt", "rearm"]
        assert all(e["utc"] == "2026-10-06T07:00:00Z" and e["schema"] == "quantgen.governance_event" for e in events)
        assert {e["actor"] for e in events} == {"runtime", "operator"}
        # without a clock the decision instant stamps the event
        other = B.BookRegistry(Path(tmp) / "other", sessions=lambda m: CAL)
        B.create_default_books(other, ["KR"])
        B.arm(other, REC, _dec(CAL[0]))
        assert G.read_events(other.log)[0]["utc"] == "2026-09-01T06:30:30Z"
        # a corrupt book file is refused at load, never dropped
        (Path(tmp) / "books" / B._file_name(REC)).write_text("{not json", encoding="utf-8")
        try:
            B.BookRegistry(Path(tmp))
            raise AssertionError("corrupt book file loaded")
        except ValueError:
            pass


test_persistence_round_trip_and_governance_chain.test_ids = []


# --------------------------------------------------------------------------- #
# runtime[] entries validate against the section 6.1 schema
# --------------------------------------------------------------------------- #
def test_runtime_entry_validates_against_macro_state_schema():
    from tests.macro_m0_schemas import filled
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        reg.save(replace(reg.get(SPEC), nav=1.0e9, hwm_hard=1.1e9, ref_step=1.05e9))
        B.runtime_halt(reg, REC, "OPS", "acting_input_stale:" + SID, _dec(CAL[2]), component="pit_value", series_id=SID)
        B.runtime_halt(reg, REC, "RISK", "hard_stop", _dec(CAL[3]))
        B.acknowledge(reg, REC, "kim", _dec(CAL[3]))
        B.step_decision(reg, REC, _dec(CAL[4]), ok=True)                            # one cause cleared
        B.step_decision(reg, SPEC, _dec(CAL[4]), ok=False, failed=[SID, "A"], limits={"A": 5})
        B.retire(reg, "specification:US", _dec(CAL[4]), by="owner")
        ms = filled()["macro_state"]
        ms["runtime"] = reg.runtime_entries()
        assert [e["book_id"] for e in ms["runtime"]] == [REC, "recommended:US", SPEC, "specification:US"]
        assert set(ms["runtime"][0]) == {"book_id", "engine_state", "halt", "post_rearm_cap_until", "nav", "hwm_hard",
                                         "ref_step", "consecutive_failures", "book_counter"}
        ms["flags"]["engine_state"] = ms["runtime"][0]["engine_state"]             # S6: the market's recommended book
        assert S.validate("macro_state", ms) == []
        ok, issues, acting = S.check_artifact("macro_state", ms)
        assert ok and issues == [] and not acting
        rec = ms["runtime"][0]
        assert rec["engine_state"] == "HALTED" and rec["halt"]["ack_by"] == "kim" and len(rec["halt"]["causes"]) == 2
        assert rec["halt"]["causes"][0]["cleared_utc"] == "2026-09-07T06:30:30Z"    # CAL[4]
        spec = ms["runtime"][2]
        assert spec == {"book_id": SPEC, "engine_state": "ARMED", "halt": None, "post_rearm_cap_until": None,
                        "nav": 1.0e9, "hwm_hard": 1.1e9, "ref_step": 1.05e9,
                        "consecutive_failures": {SID: 1, "A": 1}, "book_counter": 1}
        assert ms["runtime"][3]["engine_state"] == "DISARMED"
        # the object is closed: a carrier-only field never leaks into the artifact
        ms["runtime"][2]["post_rearm_left"] = 0
        assert S.validate("macro_state", ms) == ["/runtime/2/post_rearm_left: undeclared"]


test_runtime_entry_validates_against_macro_state_schema.test_ids = []


# --------------------------------------------------------------------------- #
# ever_armed / warm-up semantics; retire
# --------------------------------------------------------------------------- #
def test_ever_armed_warmup_and_retire():
    with tempfile.TemporaryDirectory() as tmp:
        reg = B.BookRegistry(Path(tmp), clock=_CLOCK, sessions=lambda m: CAL)
        B.create_default_books(reg, ["KR"])
        assert not B.ever_armed(reg, REC)
        for i in range(1, 5):                                                       # warm-up: never a HALT
            b = B.step_decision(reg, REC, _dec(CAL[i]), ok=False, failed=[SID]).book
            assert b.mode is EngineMode.DISARMED and b.halt is None
        assert b.consecutive_failures == {SID: 4} and not reg.log.exists()
        b = B.arm(reg, REC, _dec(CAL[5]))
        assert b.mode is EngineMode.ARMED and B.ever_armed(reg, REC) and b.consecutive_failures == {} and b.book_counter == 0
        assert B.arm(reg, REC, _dec(CAL[6])) == b                                   # already ARMED: no-op
        assert _kinds(reg, REC) == ["book_state"]
        b = B.step_decision(reg, REC, _dec(CAL[6]), ok=False, failed=[SID]).book    # after ARMED a shortfall is a failure
        b = B.step_decision(reg, REC, _dec(CAL[7]), ok=False, failed=[SID]).book
        assert b.halted
        try:
            B.arm(reg, REC, _dec(CAL[8]))
            raise AssertionError("arm() on a HALTED book")
        except ValueError:
            pass
        b = B.retire(reg, REC, _dec(CAL[8]), by="owner")
        assert b.mode is EngineMode.DISARMED and b.halt is None and b.ever_armed
        try:
            B.arm(reg, REC, _dec(CAL[9]))
            raise AssertionError("a retired book re-armed")
        except ValueError as exc:
            assert "retired" in str(exc)
        events = [e for e in G.read_events(reg.log) if e["book_id"] == REC]
        assert [(e["kind"], e["actor"], e["new"]) for e in events] == [
            ("book_state", "runtime", "ARMED"), ("halt", "runtime", "HALTED"), ("book_state", "owner", "DISARMED")]
        try:
            B.runtime_rearm(reg, REC, "auto", _dec(CAL[9]))
            raise AssertionError("re-arm of a DISARMED book")
        except B.RearmRefused:
            pass
        try:
            reg.get("recommended:JP")
            raise AssertionError("unregistered book")
        except KeyError:
            pass


test_ever_armed_warmup_and_retire.test_ids = []


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
