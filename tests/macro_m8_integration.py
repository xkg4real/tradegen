"""Sprint 6 integration: the production hooks of `core.skills.macro_daily.default_services` (the FORWARD-SIM and
refusal display legs, the forward books, the R-25 monitor -> demotion -> lockout chain) and the gate-package state
read by verdict_filter (I-03 runtime, I-12 / I-13 display clauses, I-14 pipeline side, T-REF-01 / T-REF-02 display
clauses, T-CARD-03 package state). Hermetic: synthetic stores, temp macro dirs; nothing under ~/.nextgen.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from core.engine.state import EngineMode
from core.ficc import pit as P
from core.quant import cards as CARDS
from core.quant import forward as FWD
from core.quant import gate_package as GP
from core.quant import risk_layer as RL
from core.rules import governance as G
from core.skills import macro_daily as MD
from tests.macro_m1_pit import CLK, REG
from tests.macro_m2_risk import OCT2, _close_row, _sessions
from tests.macro_m7_cards import _store as _frozen_store
from tests.macro_m8_pipeline import REC, SPEC, UREC, USPEC, _tmp, artifacts, kr_store, run, services, state_of, step

OCT1 = date(2026, 10, 1)
WEIGHT_BOOKS = ("recommended", "specification")


def _gross(tmp, rec) -> dict:
    return next(v for k, v in artifacts(tmp, rec).items() if k.endswith("market_gross.json"))


def _krw_rows(krw) -> list[dict]:
    days = _sessions("KR", OCT2, len(krw))
    return [P.stamp_release("ECOS_1530_CLOSE", d, v, retrieved_at_utc=CLK.publication_instant("ECOS_1530_CLOSE", d) + timedelta(minutes=5),
                            source="ECOS", registry=REG, clocks=CLK) for d, v in zip(days, krw)]


def _month_ends(n: int, last: date) -> list[date]:
    out, y, m = [], last.year, last.month
    while len(out) < n:
        d = date(y, m, 28) + timedelta(days=4)
        d = d - timedelta(days=d.day)                                          # the calendar month end
        while not CLK.is_session("US", d):
            d -= timedelta(days=1)
        out.append(d)
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return out[::-1]


def test_default_hooks_display_refusal_and_forward_sim_and_never_feed_a_weight_book():
    """KR: R-11 reads the ECOS 15:30 close (+5 % over 20 obs -> 0.75) into `refusal_books` / `overlay_decision.refusal[]`
    and `refusal:R-11` only; US: R-28 (month-end close below SMA10m -> 0.5) and R-29 (SPX SMA20 vt) into `forward_sim`
    and their own books (R-28 = vt x min(1, trend)); the recommended line stays 1.0, engine_feed and the run row carry
    weight books only, a replay reproduces the display byte for byte."""
    tmp = _tmp()
    store = kr_store()
    store.append(_krw_rows([1350.0] * 21 + [1350.0 * math.exp(0.05)]))
    store.append([_close_row("SPX_MONTH_END_CLOSE", d, v, market="US", source="KIS")
                  for d, v in zip(_month_ends(10, date(2026, 9, 30)), [5000.0] * 9 + [4500.0])])
    s = services(tmp, store, None)
    kr = run(s, "KR", OCT2)
    assert kr["status"] == "ok" and not kr["acting_error"]
    state, gross = state_of(tmp, kr), _gross(tmp, kr)
    assert state["refusal_books"] == {"S1_krw_flag": True, "S2_rates_flag": None}
    assert state["forward_sim"] == {"R28_below_sma10m": None, "R29_vt_weight_next": None}
    assert [(x["rule_id"], x["value"]) for x in gross["refusal"]] == [("R-11-S1", 0.75)] and gross["forward_sim"] == []
    assert gross["refusal"][0]["card"]["displayed_as"] == "refusal" and gross["multipliers"] == [] and gross["overlay_min"] == 1.0
    assert state["concentration"]["by_book"][REC]["composed"] == 1.0
    fb = step(kr, "macro.forward_books")
    assert fb["status"] == "ok" and fb["result"]["books"] == {"refusal:R-11": 0.75} and "not started" in fb["result"]["records"]
    feed = step(kr, "macro.engine_feed")["result"]["books"]
    assert set(feed) == {REC, SPEC} and all(MD.B.parse_book_id(b)[0] in WEIGHT_BOOKS for b in kr["books"])
    assert step(kr, "macro.forward_monitor")["result"]["status"] == "ok"
    us = run(s, "US", OCT1)
    assert us["status"] == "ok" and not us["acting_error"]
    ustate, ugross = state_of(tmp, us), _gross(tmp, us)
    vt = ustate["forward_sim"]["R29_vt_weight_next"]
    assert ustate["forward_sim"]["R28_below_sma10m"] is True and 0.0 < vt <= 1.0
    assert ustate["refusal_books"] == {"S1_krw_flag": None, "S2_rates_flag": None}           # live: the KIS 10y quote is absent
    assert [x["rule_id"] for x in ugross["forward_sim"]] == ["R-28", "R-29"] and [x["rule_id"] for x in ugross["refusal"]] == ["R-12-S2"]
    assert all(x["card"]["displayed_as"] != "recommendation" for x in ugross["forward_sim"] + ugross["refusal"])
    books = step(us, "macro.forward_books")["result"]["books"]
    assert books == {"forward_sim:R-28": RL.compose(vt, [0.5], 1.0, 1.0), "forward_sim:R-29": vt, "refusal:R-12": 1.0}
    assert ustate["concentration"]["by_book"].get(UREC, {}).get("composed", 1.0) == 1.0 and ustate["vol"]["vt_weight_recommended_book"] == 1.0
    assert all(MD.B.parse_book_id(b)[0] in WEIGHT_BOOKS for b in step(us, "macro.engine_feed")["result"]["books"])
    again = MD.replay(s, "KR", OCT2)                                          # the display legs are as-of reads: byte-identical
    assert again["match"], again["diffs"]


test_default_hooks_display_refusal_and_forward_sim_and_never_feed_a_weight_book.test_ids = ["I-03", "I-12", "I-13", "T-REF-01", "T-REF-02"]


def _thresholds() -> FWD.AlarmThresholds:
    return FWD.AlarmThresholds("CARD-P", -1.0, None, 0.0, 1.0, FWD.CUSUM_K, 5.0, "poisson", 50.0, 0.05, 20, 0.02)


def test_forward_monitor_hook_demotes_locks_out_and_admissions_refuse():
    """A started record whose forward books were killed: the default monitor demotes at the next live decision
    (governance `demotion` event with the 6-month lockout, the record's demotion row, a FORWARD_DEMOTION page); the
    default `lockouts` hook then refuses the family x market in admissions; the record is demoted once; a replay
    never monitors."""
    tmp = _tmp()
    s = services(tmp, kr_store(extra_sessions=_sessions("KR", date(2026, 10, 6), 1)), None)
    path = tmp / MD.FORWARD_DIR / "MACRO-R06-KR-ETF.jsonl"
    rec = FWD.ForwardRecord(path)
    start = MD.P.parse_utc("2026-09-30T06:30:30Z")
    rec.start("MACRO-R06-KR-ETF", first_registered_utc=start, decision_utc=start, session_date=date(2026, 9, 30),
              thresholds=_thresholds(), split=0.05, revision=1, market="KR", family="R-06")
    rec.mark_kill(decision_utc=start, operator="owner", books=["card:MACRO-R06-KR-ETF:on", "card:MACRO-R06-KR-ETF:off", "card:MACRO-R06-KR-ETF:S"])
    dec = CLK.close_print_bound_utc("KR", OCT2)
    assert not s.lockouts("R-06", "KR", dec)
    out = run(s, "KR", OCT2)
    assert step(out, "macro.forward_monitor")["status"] == "ok"
    ev = [e for e in G.read_events(s.governance_log) if e["kind"] == "demotion"]
    assert len(ev) == 1 and "family:R-06" in ev[0]["refs"] and "market:KR" in ev[0]["refs"] and ev[0]["old"] == ev[0]["new"] == "NOT_RUN"
    assert rec.demoted is not None and G.verify_chain(s.governance_log).ok
    assert any(a["code"] == "FORWARD_DEMOTION" for a in s.alerts.open("page"))
    assert s.lockouts("R-06", "KR", dec) and not s.lockouts("R-06", "US", dec) and not s.lockouts("R-03", "KR", dec)
    nxt = run(s, "KR", date(2026, 10, 6))
    assert nxt["status"] == "ok" and len([e for e in G.read_events(s.governance_log) if e["kind"] == "demotion"]) == 1
    MD.replay(s, "KR", OCT2)
    assert len([e for e in G.read_events(s.governance_log) if e["kind"] == "demotion"]) == 1
    assert s.book_registry.get(REC).mode is EngineMode.ARMED                 # a demotion never touches the risk-layer books


test_forward_monitor_hook_demotes_locks_out_and_admissions_refuse.test_ids = ["I-14", "T-CARD-03"]


def test_verdict_filter_reads_the_package_state_and_app_start_never_raises():
    """`package_of` carries `gate_package.package_state` (NOT_FROZEN on the shipped store; FROZEN on a synthetic
    frozen store; BLOCKED after two failed acceptance attempts, refusing check (ii)); `on_app_start` swallows a
    failing clock (it never raises into main.py)."""
    tmp = _tmp()
    assert MD.package_of(MD.load_store(), tmp)["status"] == "NOT_FROZEN"
    frozen, _ = _frozen_store(tmp, frozen=True)
    assert MD.package_of(frozen, tmp)["status"] == "FROZEN"
    for i in (1, 2):
        CARDS.chain_append(GP.attempts_path(tmp), {"attempt_no": i, "package_version": "2.0.0", "outcome": "fail"})
    pkg = MD.package_of(frozen, tmp)
    assert pkg["status"] == "BLOCKED"
    card = {"card_id": "MACRO-R06-KR-ETF", "verdict": "PASS", "disposition": "BUILD_AS_INSURANCE"}
    out = MD.admissions({"MACRO-R06-KR-ETF": card}, [], pkg, snapshot_id_at=lambda k: None, harness_hashes_at=lambda h: None,
                        lockouts=lambda f, m, t: False, decision_utc=CLK.close_print_bound_utc("KR", OCT2))
    assert out.admitted == {} and "(ii) gate.package is not FROZEN" in out.refused["R-06-KR-VT20"]
    MD._STARTED["done"] = False

    def broken():
        raise RuntimeError("clock unavailable")
    assert MD.on_app_start(tmp, broken, clocks=CLK)["error"].startswith("RuntimeError")
    MD._STARTED["done"] = False


test_verdict_filter_reads_the_package_state_and_app_start_never_raises.test_ids = ["T-CARD-03", "T-OBS-02"]


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
