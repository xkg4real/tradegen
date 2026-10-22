"""M8 package B: R-25 forward records and demotion (core/quant/forward.py), R-28 / R-29 FORWARD-SIM books
(core/quant/forward_sim.py), R-11 / R-12 refusal books (core/quant/refusal.py).

Spec tests: T-DEMOTE-01..05, I-14, T-TREND-01/03/04 (+ I-12 mechanics), T-USFUT-01/03/04 (+ I-13 logic), T-REF-01/02,
T-BASIS-01 (S2 clause); REFDATA / OWNER: T-TREND-02, G-TR-01..05, T-USFUT-02 (fixture clause, TASK-M8-11), T-USFUT-05,
G-REF-01/02, G-KR-05/05s, G-US-02a, G-POST-01 (M8 rows). Hermetic: every record, ledger, registry and governance log
lives in a tempfile directory; the PIT stores are synthetic on the M1 StubClocks; seed 11; nothing under ~/.nextgen.
"""
from __future__ import annotations

import ast
import functools
import json
import math
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from core.engine import books as B
from core.ficc import context_log as CL
from core.ficc import macro_artifacts as MA
from core.ficc import macro_schema as S
from core.ficc import pit as P
from core.quant import cardp
from core.quant import cards
from core.quant import costed as C
from core.quant import forward as F
from core.quant import forward_sim as FS
from core.quant import gate_ledger as GL
from core.quant import refusal as RF
from core.quant import risk_layer as RL
from core.rules import governance as G
from core.rules import macro_rules as M
from tests.macro_m0_schemas import synthetic_card
from tests.macro_m1_pit import CLK, REG, U
from tests.macro_m2_risk import _sessions
from tests.notrun import NotRun, require_fixture, require_owner

ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT / "docs" / "macro_overlay" / "headers"
UTC = timezone.utc
STORE = M.load_store()
MON = STORE.get("monitoring")
FIRST_REGISTERED = U(2026, 12, 1, 0, 0)
SCHEDULED_12M = 250


def _tmp(prefix="m8fwd_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle in str(e), f"{needle!r} not in {e}"
        return e
    raise AssertionError(f"did not raise {exc.__name__} ({needle!r})")


# --------------------------------------------------------------------------- #
# Synthetic books (seed 11): a vol-clustered market, VT(20, 0.15) decided at t earning t+1, a rest-of-book sleeve
# --------------------------------------------------------------------------- #
def _market(rng, T: int):
    sig, s = np.empty(T), 0.009
    for t in range(T):
        if rng.random() < 0.02:
            s = rng.choice([0.007, 0.010, 0.018, 0.028])
        sig[t] = s
    return rng.standard_t(5, T) * sig / math.sqrt(5 / 3) + 0.0003


def _bdays(start: date, n: int) -> tuple:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return tuple(out)


def synth_design(seed: int, *, T: int = 5300, w: float = 0.2, cls: str = "CARD-P") -> F.DesignSample:
    rng = np.random.default_rng(seed)
    r = _market(rng, T)
    vt = np.full(T, np.nan)
    for t in range(20, T):
        sd = float(np.std(r[t - 20:t], ddof=1)) * math.sqrt(252)
        vt[t] = min(1.0, 0.15 / sd) if sd > 0 else 1.0
    return F.DesignSample(_bdays(date(2000, 1, 3), T), C.earning_weights(vt), r, rng.normal(0.0002, 0.008, T), w, 5.0, cls)


@functools.lru_cache(maxsize=None)
def _calibrated(seed: int, cls: str = "CARD-P", split: float | None = 0.05, T: int = 5300):
    return calibrate(synth_design(seed, T=T, cls=cls), split)


def calibrate(design, split):
    return F.calibrate_alarms(design, split=split)


def forward_rows(seed: int, n: int, *, w: float = 0.2, start: date = date(2027, 1, 4), on_scale=None, drag: float = 0.0):
    """Decision rows of a forward path from the same generator: (session_date, decision_utc, w, r_on, r_cmp, r_rest, m)."""
    d = synth_design(seed, T=n + 40, w=w)
    books = cardp.build_books(d.m, d.off, 5.0, d.dates, stress_2x=False)
    ok = np.isfinite(books.on)
    on, cmp_, rest, m = books.on[ok][-n:], books.S[ok][-n:], d.rest[ok][-n:], books.m[ok][-n:]
    if on_scale is not None:
        on = on_scale(on, cmp_)
    on = on - drag
    dates = _bdays(start, n)
    return [dict(session_date=dd, decision_utc=datetime(dd.year, dd.month, dd.day, 21, 0, 30, tzinfo=UTC), w_card=w,
                 r_on=float(a), r_cmp=float(b), r_rest=float(c), m=float(mm)) for dd, a, b, c, mm in zip(dates, on, cmp_, rest, m)]


def _record(tmp: Path, th, rows, *, card_id="MACRO-SYN-P", market="US", family="R-06", flags=None) -> F.ForwardRecord:
    rec = F.ForwardRecord(tmp / "forward" / f"{card_id}.jsonl")
    first = rows[0]
    rec.start(card_id, first_registered_utc=FIRST_REGISTERED, decision_utc=first["decision_utc"], session_date=first["session_date"],
              thresholds=th, split=th.split_per_year, revision=1, market=market, family=family)
    rec.extend([{**r, **((flags or (lambda i, r: {}))(i, r))} for i, r in enumerate(rows)])
    return rec


def _th(cls="CARD-P", **over) -> F.AlarmThresholds:
    """Hand-built thresholds for sign / logic tests (no calibration)."""
    base = dict(cls=cls, dsr12_p2_5=-0.39, gap6m_sigma=0.02, cusum_mu=0.0, cusum_sigma=0.01, cusum_k=0.25, cusum_h=12.0,
                switch_model="poisson", switch_p99=400.0, split_per_year=0.05, panel_offsets=20, panel_alarms_per_year=0.0)
    base.update(over)
    return F.AlarmThresholds(**base)


# --------------------------------------------------------------------------- #
# R-25: T-DEMOTE-01 .. 05, I-14
# --------------------------------------------------------------------------- #
def test_demote_01_trigger_text_and_a_protective_record_never_demotes():
    """The CARD-P trigger text reads "forward dMDD vs S <= 0 = no protection" (the corrected sign; the store's all_of
    block says the same); a record with dMDD > 0 and ES protection never demotes even when dSR sits below the 2.5 %
    threshold, because all three must hold; the mirror record (no protection) fires."""
    assert F.CARD_P_TRIGGER_TEXT == "forward ΔMDD vs S ≤ 0 = no protection"
    assert "≤ 0" in F.CARD_P_TRIGGER_TEXT and "≥" not in F.CARD_P_TRIGGER_TEXT
    assert MON["catastrophic"]["card_p"]["all_of"] == list(F.CATASTROPHIC_P) and MON["catastrophic"]["card_p"]["window_months"] == 12
    assert MON["catastrophic"]["card_o"]["any_of"] == list(F.CATASTROPHIC_O)
    th = _th(dsr12_p2_5=10.0)                                        # dSR is always "below": only the signs decide
    protect = lambda on, cm: np.where(cm < np.quantile(cm, 0.05), 0.5 * cm, cm)       # noqa: E731  halves the worst days: better MDD and ES
    expose = lambda on, cm: np.where(cm < np.quantile(cm, 0.05), 1.6 * cm, cm)        # noqa: E731  worse MDD and ES: no protection
    with tempfile.TemporaryDirectory() as tmp:
        rec = _record(Path(tmp), th, forward_rows(21, 300, on_scale=protect))
        res = F.forward_monitor(rec, th, as_of=rec.last_session(), scheduled_12m=SCHEDULED_12M)
        st = res.statistics
        assert st["dMDD"] > 0 and st["dES21"] > 0 and st["dSR_vs_S"] < th.dsr12_p2_5, st
        assert res.demotion is None and not [a for a in res.alarms if a.kind == "catastrophic"]
        rec2 = _record(Path(tmp) / "b", th, forward_rows(21, 300, on_scale=expose))
        res2 = F.forward_monitor(rec2, th, as_of=rec2.last_session(), scheduled_12m=SCHEDULED_12M)
        assert res2.statistics["dMDD"] <= 0 and res2.statistics["dES21"] <= 0
        fired = [a for a in res2.alarms if a.kind == "catastrophic"]
        assert fired and fired[0].trigger == F.CARD_P_TRIGGER_TEXT and fired[0].demotion_kind == "catastrophic_or_cusum"
        # dMDD > 0 with dES <= 0 (or the reverse) never fires either: all three, not any
        half = lambda on, cm: np.where(cm < np.quantile(cm, 0.01), 0.5 * cm, np.where(cm < np.quantile(cm, 0.05), 1.4 * cm, cm))   # noqa: E731
        rec3 = _record(Path(tmp) / "c", th, forward_rows(21, 300, on_scale=half))
        res3 = F.forward_monitor(rec3, th, as_of=rec3.last_session(), scheduled_12m=SCHEDULED_12M)
        s3 = res3.statistics
        fired3 = bool([a for a in res3.alarms if a.kind == "catastrophic"])
        assert fired3 == (s3["dMDD"] <= 0 and s3["dES21"] <= 0 and s3["dSR_vs_S"] < th.dsr12_p2_5)


test_demote_01_trigger_text_and_a_protective_record_never_demotes.test_ids = ["T-DEMOTE-01", "I-14"]


def test_demote_02_every_statistical_trigger_reads_whole_book_nav():
    """`monitoring.denominator` is whole_book_nav; the paired series is w x (r_on - r_cmp) on the whole book (the rest
    cancels); a card at 20 % of the book with sleeve-level noise does not fire on the seeded fixture (seed 11
    thresholds, seed 21 forward path); sleeve-level windows are noisier than the whole-book ones."""
    assert MON["denominator"] == "whole_book_nav"
    th = _calibrated(11)
    design = synth_design(11)
    on, cm, d, dates = F.whole_book(design)
    w = design.w_card
    books = cardp.build_books(design.m, design.off, 5.0, design.dates, stress_2x=False)
    ok = np.isfinite(books.on)
    np.testing.assert_allclose(on, w * books.on[ok] + (1 - w) * design.rest[ok], rtol=0, atol=1e-15)
    np.testing.assert_allclose(cm, w * books.S[ok] + (1 - w) * design.rest[ok], rtol=0, atol=1e-15)
    np.testing.assert_allclose(d, on - cm, rtol=0, atol=1e-15)
    sleeve = F.card_p_lines(books.on[ok], books.S[ok])["dSR12"]
    book = F.card_p_lines(on, cm)["dSR12"]
    assert np.std(sleeve) > np.std(book)                                    # the 20 % share dilutes sleeve noise
    with tempfile.TemporaryDirectory() as tmp:
        rows = forward_rows(21, 300)
        rec = _record(Path(tmp), th, rows)
        b_on, b_cm, dd, _ = F.paired_series(rec.decisions())
        r = rows[0]
        assert abs(b_on[0] - (0.2 * r["r_on"] + 0.8 * r["r_rest"])) < 1e-15 and abs(dd[0] - 0.2 * (r["r_on"] - r["r_cmp"])) < 1e-15
        res = F.forward_monitor(rec, th, as_of=rec.last_session(), scheduled_12m=SCHEDULED_12M)
        assert res.demotion is None and res.alarms == () and not res.suspended, res
        assert res.statistics["window_sessions"] == 252 and res.statistics["attribution_sum"] is not None
        # NAV unavailable: statistical triggers suspended, operational ones live; the gap is marked
        rec.append(session_date=date(2028, 3, 1), decision_utc=U(2028, 3, 1, 21, 0, 30), w_card=0.2, r_on=None, r_cmp=None, r_rest=None, m=1.0)
        res2 = F.forward_monitor(rec, th, as_of=date(2028, 3, 1), scheduled_12m=SCHEDULED_12M)
        assert res2.suspended and res2.statistics["dMDD"] is None and rec.decisions()[-1]["gap"]


test_demote_02_every_statistical_trigger_reads_whole_book_nav.test_ids = ["T-DEMOTE-02", "I-14"]


def test_demote_03_false_demotion_budget_on_the_20_shift_panel():
    """Two active cards split D4 equally (0.05 each, nothing unallocated); each calibrated card's placebo panel
    (20 evenly spaced circular offsets >= 252 sessions apart) gives alarms per record-year <= its split, so the
    book-level rate is <= the budget; zero active cards leave the budget unallocated and reported; the owner may
    only tighten; the CUSUM h is the smallest with an in-control ARL >= 20 years, never the naive 8."""
    split = F.budget_split(["MACRO-A", "MACRO-B"])
    assert split.per_card == 0.05 and split.unallocated == 0.0 and split.n_active == 2 and split.as_dict()["book_level_total"] == 0.10
    none = F.budget_split([])
    assert none.per_card is None and none.unallocated == 0.10 and none.allocated == {}
    _raises(lambda: F.budget_split(["A"], budget=0.11), ValueError, "tighten")
    assert F.budget_split(["A"], budget=0.08).per_card == 0.08
    assert MON["false_demotion_budget_per_year"] == 0.10 and STORE.get("owner_decisions.D4.options") == ["tighten_only_le_0p10"]
    total = 0.0
    for seed in (11, 12):
        design, th = synth_design(seed), _calibrated(seed)
        panel = F.false_demotion_rate(design, th)
        assert panel.n_offsets == 20 == th.panel_offsets and panel.alarms_per_year <= 0.05 + 1e-12, (seed, panel)
        assert abs(panel.alarms_per_year - th.panel_alarms_per_year) < 1e-12 and th.split_per_year == 0.05
        offs = np.array(panel.offsets)
        assert np.all(np.diff(offs) >= 252) and 0 < offs[0] and offs[-1] < len(design.dates)
        assert th.label in ("default", "judgment") and (th.label == "judgment") == bool(th.tightened)
        on_, cm_, d_, dates_ = F.whole_book(design)
        z = (F.monthly_paired(dates_, d_)[1] - th.cusum_mu) / th.cusum_sigma
        assert F.in_control_arl(z, th.cusum_h) >= F.ARL_MIN_MONTHS
        h0 = F.calibrate_h(z)
        assert h0 <= th.cusum_h and F.in_control_arl(z, h0 - 0.05) < F.ARL_MIN_MONTHS and h0 != 8.0
        total += panel.alarms_per_year
    assert total <= 0.10 + 1e-12
    # a short design sample: floor(T / 252) offsets, printed
    short = synth_design(13, T=1300)
    assert F.panel_offsets(1300) == [int(round((k + 0.5) * 1300 / 5)) for k in range(5)]
    th_s = F.calibrate_alarms(short, split=0.05)
    assert th_s.panel_offsets == 5
    # CARD-O: the 6-month gap sigma is pre-registered and the either-of rule applies
    th_o = _calibrated(13, "CARD-O", T=2600)
    assert th_o.gap6m_sigma is not None and th_o.gap6m_sigma > 0 and th_o.panel_alarms_per_year <= 0.05 + 1e-12
    assert MON["budget_check"] == {"panel": "circular_shift", "shifts": 20, "min_offset_sessions": 252, "short_sample": "floor_T_over_252_offsets", "seed": 11}


test_demote_03_false_demotion_budget_on_the_20_shift_panel.test_ids = ["T-DEMOTE-03", "I-14"]


def test_demote_04_operational_triggers_demote_immediately():
    """A lag-audit violation, an acting-parameter edit outside a revision, an operator kill of a card's forward
    books (gap excluded) and 26 HALTED decisions in 12 months each demote at once with the budget unused: the
    governance event is written, the lockout runs 6 months, the verdict moves PASS -> REVISE."""
    th = _th()
    card = {"card_id": "MACRO-SYN-P", "verdict": "PASS", "rule_id": "R-06-US-SYN", "family_id": "R-06", "market": "US"}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        log = tmp / "governance_events.jsonl"
        # (a) lag-audit violation in the record
        rec = _record(tmp / "a", th, forward_rows(21, 60), flags=lambda i, r: {"lag_audit_violation": i == 40})
        res = F.forward_monitor(rec, th, as_of=rec.last_session(), scheduled_12m=SCHEDULED_12M)
        assert res.demotion is not None and res.demotion.trigger == "lag_audit_violation" and res.statistics["dMDD"] is None
        assert all(a.kind == "operational" for a in res.alarms)                      # budget untouched: no statistical alarm
        dem = F.demote(card, rec, res.demotion, governance_log=log, decision_utc=U(2027, 4, 1, 21, 0, 30))
        assert dem.old == "PASS" and dem.new == "REVISE" and dem.changed and dem.kind == "operational_or_integrity"
        ev = G.read_events(log)[-1]
        assert G.verify_chain(log) and ev["kind"] == "demotion" and ev["old"] == "PASS" and ev["new"] == "REVISE"
        assert ev["book_id"] == "recommended:US" and ev["actor"] == "runtime" and "lockout_until:2027-10-01" in " ".join(ev["refs"])
        assert rec.demoted["reason"] == "lag_audit_violation"
        assert F.locked_out(log, "R-06", "US", U(2027, 9, 30)) and not F.locked_out(log, "R-06", "US", U(2027, 10, 2))
        assert not F.locked_out(log, "R-06", "KR", U(2027, 5, 1)) and not F.locked_out(log, "R-03", "US", U(2027, 5, 1))
        # (b) acting-parameter edit outside a revision; an edit inside a revision is not a trigger
        rec_b = _record(tmp / "b", th, forward_rows(21, 60))
        edit = F.Integrity(acting_param_edits=({"key": "vol_target.US.target_ann", "revision": None},))
        res = F.forward_monitor(rec_b, th, as_of=rec_b.last_session(), scheduled_12m=SCHEDULED_12M, integrity=edit)
        assert res.demotion.trigger == "acting_param_edit_outside_revision"
        inside = F.Integrity(acting_param_edits=({"key": "vol_target.US.target_ann", "revision": 2},))
        assert F.forward_monitor(rec_b, th, as_of=rec_b.last_session(), scheduled_12m=SCHEDULED_12M, integrity=inside).demotion is None
        # (c) operator kill of a card's forward books through the per-book runtime: all three HALT, integrity trigger
        reg = B.BookRegistry(tmp / "books", clock=lambda: U(2027, 3, 1), sessions=lambda m: list(_bdays(date(2027, 1, 4), 200)))
        trio = tuple(f"card:MACRO-SYN-P:{s}" for s in ("on", "off", "S"))
        for bid in trio:
            reg.register(B.BookRuntime(bid))
            B.arm(reg, bid, U(2027, 1, 4, 21, 0, 30))
        kill = B.operator_kill(reg, trio[0], "kim", U(2027, 3, 1, 21, 0, 30))
        assert kill.integrity_trigger and all(reg.get(b).halted for b in trio)
        rec_c = _record(tmp / "c", th, forward_rows(21, 60), flags=lambda i, r: {"halted": i >= 40})
        rec_c.mark_kill(decision_utc=U(2027, 3, 1, 21, 0, 30), operator="kim", books=trio)
        res = F.forward_monitor(rec_c, th, as_of=rec_c.last_session(), scheduled_12m=SCHEDULED_12M,
                                integrity=F.Integrity(operator_kill=kill.integrity_trigger))
        assert res.demotion.trigger == "operator_kill_of_forward_books"
        assert len(F.paired_series(rec_c.decisions())[0]) == 40 and len(rec_c.active_decisions()) == 40   # the gap excluded
        # (d) 26 HALTED decisions in 12 months trip the 10 % budget (strict >); 25 do not
        for n_halt, want in ((26, True), (25, False)):
            rec_d = _record(tmp / f"d{n_halt}", th, forward_rows(21, 300), flags=lambda i, r, n=n_halt: {"halted": i >= 300 - n})
            share, tripped = F.decision_gaps(rec_d.rows(), rec_d.last_session(), SCHEDULED_12M)
            assert tripped is want and abs(share - n_halt / SCHEDULED_12M) < 1e-12, (n_halt, share)
            res = F.forward_monitor(rec_d, th, as_of=rec_d.last_session(), scheduled_12m=SCHEDULED_12M)
            assert (res.demotion is not None and res.demotion.trigger == "decision_gaps_gt_10pct_rolling_12m") is want
        # (e) a provisional / stale input reaching an acting decision; switches above the design p99
        rec_e = _record(tmp / "e", th, forward_rows(21, 60), flags=lambda i, r: {"provisional_or_stale": i == 10})
        assert F.forward_monitor(rec_e, th, as_of=rec_e.last_session(), scheduled_12m=SCHEDULED_12M).demotion.trigger == \
            "provisional_or_stale_input_reached_acting_decision"
        res = F.forward_monitor(rec_b, th, as_of=rec_b.last_session(), scheduled_12m=SCHEDULED_12M, integrity=F.Integrity(switches_12m=401))
        assert res.demotion.trigger == "switches_gt_p99_poisson_negbin"
        assert list(MON["operational_triggers"]) == list(F.OPERATIONAL_TRIGGERS)
        assert MON["lockout_months_after_demotion"] == 6 and MON["lockout_scope"] == "family_x_market"
        assert MON["demotion_verdict"] == F.DEMOTION_VERDICT and MON["bull_lag_alone_demotes"] is False


test_demote_04_operational_triggers_demote_immediately.test_ids = ["T-DEMOTE-04", "I-14"]


def test_demote_05_no_forward_record_raises_a_verdict():
    """Every upward route raises; an INSUFFICIENT card with 12 strong forward months stays INSUFFICIENT (the operational
    demotion verdict REVISE would read as a raise and is not applied; a catastrophic trigger still lowers to REJECT);
    the store says `forward_record_can_raise_verdict: false` and item 35 refuses a forward record cited as validation."""
    assert MON["forward_record_can_raise_verdict"] is False
    assert MON["regate_up_only_on_new_history"] == {"continuous": "new_objective_episode", "discrete": "tier_onset_count"}
    for old, new in (("INSUFFICIENT_DATA", "PASS"), ("INSUFFICIENT_DATA", "REVISE"), ("REJECT", "INSUFFICIENT_DATA"), ("REVISE", "PASS"), ("NOT_RUN", "PASS")):
        _raises(lambda: F.verdict_after_forward(old, new), F.ForwardRecordCannotRaise, "cannot raise")
        _raises(lambda: F.raise_verdict({"verdict": old}, new), F.ForwardRecordCannotRaise, "no forward record raises")
    _raises(lambda: F.raise_verdict({"verdict": "PASS"}, "PASS"), F.ForwardRecordCannotRaise)   # even a no-op goes through the refusal
    assert F.demotion_verdict("INSUFFICIENT_DATA", "operational_or_integrity") == "INSUFFICIENT_DATA"
    assert F.demotion_verdict("INSUFFICIENT_DATA", "catastrophic_or_cusum") == "REJECT"
    assert F.demotion_verdict("NOT_RUN", "operational_or_integrity") == "NOT_RUN"
    assert F.demotion_verdict("PASS", "operational_or_integrity") == "REVISE" and F.demotion_verdict("PASS", "catastrophic_or_cusum") == "REJECT"
    assert F.demotion_verdict("REJECT", "catastrophic_or_cusum") == "REJECT"
    th = _th()
    strong = lambda on, cm: cm + 0.004                                   # noqa: E731  12 strong months vs S
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        rec = _record(tmp, th, forward_rows(21, 300, on_scale=strong))
        res = F.forward_monitor(rec, th, as_of=rec.last_session(), scheduled_12m=SCHEDULED_12M)
        assert res.statistics["dSR_vs_S"] > 1.0 and res.statistics["dMDD"] > 0 and res.demotion is None
        card = {"card_id": "MACRO-SYN-P", "verdict": "INSUFFICIENT_DATA", "rule_id": "R-06-US-SYN", "family_id": "R-06", "market": "US"}
        assert F.verdict_after_forward(card["verdict"], card["verdict"]) == "INSUFFICIENT_DATA"
        alarm = F.Alarm("operational", "lag_audit_violation", "operational_or_integrity")
        dem = F.demote(card, rec, alarm, governance_log=tmp / "gov.jsonl", decision_utc=U(2028, 2, 1, 21, 0, 30))
        assert dem.old == dem.new == "INSUFFICIENT_DATA" and not dem.changed and G.read_events(tmp / "gov.jsonl")[-1]["kind"] == "demotion"
        block = F.forward_record_block(rec, th, res, as_of=rec.last_session())
        assert block["honesty_line"] == F.HONESTY_LINE == "12 months of forward record can only detect catastrophic decay."
        assert block["demoted"] and block["demotion_reason"] == "lag_audit_violation" and res.statistics["threshold_2_5pct"] == -0.39 == th.dsr12_p2_5
        assert res.statistics["trigger_text"] == F.CARD_P_TRIGGER_TEXT
        card_doc = synthetic_card()
        card_doc["forward_record"] = block
        assert S.validate("model_card.macro", card_doc) == []
    # item 35: evidence citing a forward book as validation is refused by the rules-store validator
    obj = cards.rule_object("MACRO-R06-KR-ETF")
    hit = M.dnb_violations(M.RuleObject(**{**vars(obj), "extras": {**obj.extras, "validation": "forward_sim:R-29 record of 12 months"}}))
    assert any("forward_record_cited_as_validation" in str(i) for i in hit)


test_demote_05_no_forward_record_raises_a_verdict.test_ids = ["T-DEMOTE-05", "I-14"]


def test_record_append_only_no_backfill_live_only():
    """8.8 (a): the record starts at a live decision after the header commit, never before it, never from a replay
    or backtest; a row dated at or before the last recorded session is refused (no backfill); a second start is
    refused; a new revision resets the alarm scope while the age counts from first_registered_utc."""
    th = _th()
    with tempfile.TemporaryDirectory() as tmp:
        rec = F.ForwardRecord(Path(tmp) / "r.jsonl")
        _raises(lambda: rec.append(session_date=date(2027, 1, 4), decision_utc=U(2027, 1, 4), w_card=0.2, r_on=0.0, r_cmp=0.0, r_rest=0.0, m=1.0),
                F.RecordRefused, "not started")
        _raises(lambda: rec.start("X", first_registered_utc=FIRST_REGISTERED, decision_utc=U(2027, 1, 4), session_date=date(2027, 1, 4),
                                  thresholds=th, split=0.05, revision=1, run_mode="replay"), F.RecordRefused, "live workflow")
        _raises(lambda: rec.start("X", first_registered_utc=FIRST_REGISTERED, decision_utc=U(2026, 11, 30), session_date=date(2026, 11, 30),
                                  thresholds=th, split=0.05, revision=1), F.RecordRefused, "no backfill")
        rec.start("X", first_registered_utc=FIRST_REGISTERED, decision_utc=U(2027, 1, 4, 21), session_date=date(2027, 1, 4), thresholds=th, split=0.05, revision=1)
        _raises(lambda: rec.start("X", first_registered_utc=FIRST_REGISTERED, decision_utc=U(2027, 1, 5, 21), session_date=date(2027, 1, 5),
                                  thresholds=th, split=0.05, revision=1), F.RecordRefused, "already started")
        row = lambda d, **kw: rec.append(session_date=d, decision_utc=U(d.year, d.month, d.day, 21), w_card=0.2, r_on=0.001, r_cmp=0.0, r_rest=0.0, m=1.0, **kw)   # noqa: E731
        row(date(2027, 1, 4))
        row(date(2027, 1, 6))
        _raises(lambda: row(date(2027, 1, 5)), F.RecordRefused, "no backfill")        # earlier than the last
        _raises(lambda: row(date(2027, 1, 6)), F.RecordRefused, "no backfill")        # the same session twice
        _raises(lambda: row(date(2027, 1, 7), run_mode="replay"), F.RecordRefused, "audits only")
        _raises(lambda: row(date(2027, 1, 7), run_mode="backtest"), F.RecordRefused, "audits only")
        assert [r["session_date"] for r in rec.decisions()] == ["2027-01-04", "2027-01-06"] and rec.meta["start_utc"] == "2027-01-04T21:00:00Z"
        assert rec.meta["first_registered_utc"] == "2026-12-01T00:00:00Z" and rec.meta["honesty_line"] == F.HONESTY_LINE
        bad = [dict(session_date=date(2027, 1, 8), decision_utc=U(2027, 1, 8, 21), w_card=0.2, r_on=0.0, r_cmp=0.0, r_rest=0.0, m=1.0),
               dict(session_date=date(2027, 1, 8), decision_utc=U(2027, 1, 8, 21), w_card=0.2, r_on=0.0, r_cmp=0.0, r_rest=0.0, m=1.0)]
        _raises(lambda: rec.extend(bad), F.RecordRefused, "no backfill")
        assert len(rec.decisions()) == 2                                                  # nothing of the refused batch was written
        rec.reset(revision=2, decision_utc=U(2027, 1, 7, 21), reason="new revision r2")
        row(date(2027, 1, 7))
        assert len(rec.active_decisions()) == 1 and len(rec.decisions()) == 3
        res = F.forward_monitor(rec, th, as_of=date(2027, 1, 7), scheduled_12m=SCHEDULED_12M)
        assert F.forward_record_block(rec, th, res, as_of=date(2027, 1, 7))["first_registered_utc"] == "2026-12-01T00:00:00Z"
        assert MON["nav_unavailable_ops_halt_after_decisions"] == 2


test_record_append_only_no_backfill_live_only.test_ids = ["I-14"]


def test_i14_calibrate_record_monitor_demote_end_to_end():
    """I-14 seam: calibrated thresholds (seed 11) fixed at record start, a live record of 260 decisions, no alarm on
    the seeded fixture, an injected lag-audit violation demotes immediately, the governance chain verifies and the
    next admission is locked out; budget split printed; the card block validates."""
    th = _calibrated(11)
    card = {"card_id": "MACRO-SYN-P", "verdict": "PASS", "rule_id": "R-06-US-SYN", "family_id": "R-06", "market": "US"}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        rows = forward_rows(23, 260)
        rec = _record(tmp, th, rows)
        assert rec.meta["thresholds"]["cusum_h"] == th.cusum_h and rec.meta["split_per_year"] == 0.05
        res = F.forward_monitor(rec, th, as_of=rec.last_session(), scheduled_12m=SCHEDULED_12M)
        assert res.demotion is None and res.months >= 12
        d = date(2028, 1, 10)
        rec.append(session_date=d, decision_utc=U(2028, 1, 10, 21, 0, 30), w_card=0.2, r_on=0.0, r_cmp=0.0, r_rest=0.0, m=1.0, lag_audit_violation=True)
        res = F.forward_monitor(rec, th, as_of=d, scheduled_12m=SCHEDULED_12M)
        assert res.demotion.trigger == "lag_audit_violation"
        dem = F.demote(card, rec, res.demotion, governance_log=tmp / "gov.jsonl", decision_utc=U(2028, 1, 10, 21, 0, 30))
        assert dem.new == "REVISE" and G.verify_chain(tmp / "gov.jsonl").ok and F.locked_out(tmp / "gov.jsonl", "R-06", "US", U(2028, 3, 1))
        block = F.forward_record_block(rec, th, res, as_of=d)
        card_doc = synthetic_card()
        card_doc["forward_record"] = block
        assert S.validate("model_card.macro", card_doc) == [] and block["lag_audit_violations"] == 1 and block["demoted"]
        assert F.budget_split(["MACRO-SYN-P", "MACRO-OTHER"]).as_dict()["allocated"] == {"MACRO-SYN-P": 0.05, "MACRO-OTHER": 0.05}


test_i14_calibrate_record_monitor_demote_end_to_end.test_ids = ["I-14"]


# --------------------------------------------------------------------------- #
# R-28: T-TREND-01 / 03 / 04, I-12 mechanics, T-TREND-02 + G-TR-* REFDATA
# --------------------------------------------------------------------------- #
def _r28_header() -> dict:
    return json.loads((DRAFTS / "MACRO-R28-US-TREND.r1.draft.json").read_text(encoding="utf-8"))


def test_trend_01_header_declares_everything_before_the_run():
    """The shipped R-28 draft declares monthly SMA10m, 0.5x below trend, min() composition, the claim verbatim and a
    pooled-onset rule; a header missing any one of them, or carrying a Sharpe claim, is refused."""
    h = _r28_header()
    assert FS.check_trend_header(h) == [] and h["claim"] == FS.CLAIM_R28 == STORE.get("cards.R-28_trend_axis.claim")
    assert STORE.get("cards.R-28_trend_axis.status") == "FORWARD_SIM" and STORE.get("cards.R-28_trend_axis.markets_refused") == ["KR"]
    muts = {
        "monthly SMA10m": lambda d: d["parameters"].update(signal="close_below_sma200"),
        "0.5x below trend": lambda d: d["parameters"].update(multiplier_below=0.75),
        "min() composition": lambda d: d["parameters"].update(composition="product"),
        "claim must read": lambda d: d.update(claim="slow-bear protection"),
        "pooled-onset rule": lambda d: d.update(pooling_rule=None),
        "Sharpe": lambda d: d.update(claim="slow-bear protection via the volatility state and a Sharpe gain"),
        "claim line": lambda d: d.update(claim_lines=[]),
        "Korean index": lambda d: d["pooling_rule"].update(indices=["SPX", "KOSPI"]),
    }
    for needle, mut in muts.items():
        d = _r28_header()
        mut(d)
        reasons = FS.check_trend_header(d)
        assert any(needle in r for r in reasons), (needle, reasons)
        _raises(lambda: FS.register_trend_card(d, "US"), FS.MacroRefused, needle)
    reg = FS.register_trend_card(h, "US")
    assert reg["status"] == "FORWARD_SIM" and reg["book"] == FS.BOOK_R28 and reg["pooling_rule"]["indices"] == list(FS.POOLING_INDICES)


test_trend_01_header_declares_everything_before_the_run.test_ids = ["T-TREND-01", "I-12"]


def test_trend_03_korea_instance_refused_kospi_trend_context_only():
    """Registering R-28 for KR raises (item 37) before any read; the rules-store validator refuses the KR rule
    object; the KOSPI trend state is a context_log item and forward_sim never imports context_log."""
    _raises(lambda: FS.trend_axis("KR", U(2026, 10, 2, 6, 30, 30), closes_monthly=[1.0] * 12), M.MacroRefusal, "item 37")
    _raises(lambda: FS.register_trend_card(_r28_header(), "KR"), M.MacroRefusal, "r28_instance_market_kr")
    obj = cards.rule_object("MACRO-R28-US-TREND")
    hit = M.dnb_violations(M.RuleObject(**{**vars(obj), "market": "KR"}))
    assert any("r28_instance_market_kr" in str(i) for i in hit) and not any("r28_instance_market_kr" in str(i) for i in M.dnb_violations(obj))
    assert CL.trend_state_sma10m([1.0] * 9 + [0.5]) == "below" and CL.trend_state_sma10m([1.0] * 10) == "above"   # the context function
    src = (ROOT / "core" / "quant" / "forward_sim.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("context_log" in (m or "") or "ficc.macro" == (m or "") for m in imported), imported
    assert "KOSPI_OFFICIAL_CLOSE" not in src and "trend_state_sma10m" not in src
    assert CL.scan_isolation({"core.quant.forward_sim": src}) == []


test_trend_03_korea_instance_refused_kospi_trend_context_only.test_ids = ["T-TREND-03", "I-12"]


def test_trend_04_multiplier_only_in_its_forward_sim_book():
    """Until a US sleeve exists (D5 pending) the R-28 multiplier is produced for forward_sim:R-28 only: any other
    book raises; it is an `overlay_decision.forward_sim[]` record, never `multipliers[]`; no acting module
    imports forward_sim or refusal and neither names an engine feed or order path."""
    assert STORE.get("sleeves.US.line") == "none" and STORE.get("owner_decisions.D5.status") == "pending"
    closes = [100, 101, 99, 98, 97, 96, 95, 94, 93, 92, 80]
    for book in ("recommended:US", "specification:US", "forward_sim:R-29", "refusal:R-11", "card:MACRO-R28-US-TREND:on"):
        _raises(lambda b=book: FS.trend_axis("US", U(2026, 10, 1, 20, 0, 30), closes_monthly=closes, book=b), M.MacroRefusal, "forward_sim:R-28 only")
    m = FS.trend_axis("US", U(2026, 10, 1, 20, 0, 30), closes_monthly=closes)
    assert m.book == FS.BOOK_R28 and m.value == 0.5 and m.card["disposition"] == "FORWARD_SIM" and m.card["verdict"] == "NOT_RUN"
    entry = FS.overlay_forward_sim_entry(m)
    assert set(entry) == {"rule_id", "value", "would_apply_to", "card"} and entry["rule_id"] == "R-28"
    c = MA.card_of(entry["card"])
    assert c["displayed_as"] == "descriptive" and not cards.check_display_invariant(c["verdict"], c["disposition"], c["displayed_as"])
    assert not MA.acts_in_recommended(entry["card"])
    state = FS.macro_state_forward_sim(m, None)
    assert state == {"R28_below_sma10m": True, "R29_vt_weight_next": None}
    acting = {}
    for p in sorted((ROOT / "core").rglob("*.py")):
        name = ".".join(p.relative_to(ROOT).with_suffix("").parts)
        if name.endswith("__init__"):
            name = name[: -len(".__init__")]
        src = p.read_text(encoding="utf-8")
        if name in ("core.quant.forward_sim", "core.quant.refusal", "core.quant.forward"):
            assert not any(n in src for n in ("core.engine.orders", "core.engine.feed", "engine_feed(", "place_order", "order_cash")), name
            continue
        if CL.is_acting_module(name) or name.startswith("core.ficc.") or name.startswith("core.skills."):
            acting[name] = src
    importers = [n for n, s in acting.items() if not n.startswith("core.skills.")
                 and any(i in ("core.quant.forward_sim", "core.quant.refusal", "core.quant.forward_sim.trend_axis") or i.startswith(("core.quant.forward_sim.", "core.quant.refusal."))
                         for i in CL.imports_of(n, s)[0])]
    assert importers == [], importers


test_trend_04_multiplier_only_in_its_forward_sim_book.test_ids = ["T-TREND-04", "I-12"]


def test_trend_mechanics_sma10m_onsets_composition():
    """SMA10m over the last 10 month-end closes including t_m; 0.5 below, 1.0 above (never 0.75); fewer than 10
    closes carry the previous value fail-closed; onsets de-clustered at 10 months; min() composition with vt."""
    assert FS.below_sma10m([100] * 9 + [99]) is True and FS.below_sma10m([100] * 9 + [100]) is False and FS.below_sma10m([100] * 9) is None
    assert FS.below_sma10m([200] * 5 + [100] * 9 + [101]) is False               # only the last 10 count (all 15 would flag)
    assert FS.below_sma10m([50] * 5 + [100] * 9 + [99]) is True
    assert FS.trend_multiplier([100] * 9 + [99]) == (0.5, True, "ok") and FS.trend_multiplier([100] * 9 + [101]) == (1.0, False, "ok")
    assert FS.trend_multiplier([100] * 3, previous=0.5) == (0.5, None, "fail_closed")
    m = FS.trend_axis("US", U(2026, 10, 1, 20, 0, 30), closes_monthly=[100] * 3, previous=0.5)
    assert m.status == "fail_closed" and m.value == 0.5 and m.flags["R28_below_sma10m"] is None and m.exposure_basis == "total"
    for vt in (1.0, 0.8, 0.25):
        assert RL.compose(vt, [0.5], 1.0, 1.0) == 0.5 * vt and RL.compose(vt, [1.0], 1.0, 1.0) == vt
    _raises(lambda: RL.compose(0.8, [0.5], 1.0, 1.0, combine="product"), Exception)
    flags = [0, 1, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1]
    assert FS.declustered_onsets_monthly(flags) == 2 and FS.declustered_onsets_monthly(flags, gap_months=1) == 4
    assert STORE.get("cards.R-28_trend_axis.pooling.decluster_gap_months") == 10


test_trend_mechanics_sma10m_onsets_composition.test_ids = ["I-12"]


def test_trend_02_french_monthly_and_us_vt15_goldens_refdata():
    """T-TREND-02 / G-TR-01..05 / I-12 numbers need the French monthly 1927-2026 file, the daily US VT15 fixture (U1)
    and the six trend indices; none is on this machine."""
    require_fixture("french_monthly_ff_1926-07_2026-08.csv")
    require_fixture("french_daily_5f_2x3.csv")
    raise NotRun("REFDATA: french_monthly_ff_1926-07_2026-08.csv listed but the stacked dMDD on VT, the DLB-T3a lines and the "
                 "GJR-null percentile run under the frozen package (P11) with the six trend indices and yahoo_KS11 absent")


test_trend_02_french_monthly_and_us_vt15_goldens_refdata.test_ids = ["T-TREND-02", "G-TR-01", "G-TR-02", "G-TR-03", "G-TR-04", "G-TR-05"]


# --------------------------------------------------------------------------- #
# R-29: T-USFUT-01 / 03 / 04, I-13 logic, T-USFUT-02 + T-USFUT-05 REFDATA / OWNER
# --------------------------------------------------------------------------- #
def _r29_header() -> dict:
    return json.loads((DRAFTS / "MACRO-R06-US-FUT.r1.draft.json").read_text(encoding="utf-8"))


def test_usfut_01_registered_once_second_50bp_book_raises():
    """MACRO-R06-US-FUT is one new trial in the R-06 ledger with a Micro ES 5 bp book and a notional field; a second
    registration with a 50 bp book, another instrument book, the same header again, or a header without the
    notional field raises (DNB 23 / 32)."""
    h = _r29_header()
    assert h["card_id"] == FS.US_FUT_CARD and h["family_id"] == "R-06" and h["instrument_book"] == "CME_micro_ES" and "notional_nav" in h
    assert h["notional_nav"] is None and h["notional_nav"] == STORE.get("sleeves.US.notional_nav")        # typed owner null, never invented
    with tempfile.TemporaryDirectory() as tmp:
        led = GL.family_ledger("R-06", Path(tmp))
        row = FS.register_us_fut(led, h, run_utc="2026-10-07T00:00:00Z")
        assert row["instrument_book"] == "CME_micro_ES" and row["cost"] == 5.0 and row["card_id"] == FS.US_FUT_CARD and led.n_raw == 1
        _raises(lambda: FS.register_us_fut(led, {**h, "costs": {**h["costs"], "cost_bp": 50}}, run_utc="2026-10-07T00:00:01Z"), M.MacroRefusal, "item 23")
        _raises(lambda: FS.register_us_fut(led, h, run_utc="2026-10-07T00:00:02Z"), M.MacroRefusal, "already registered")
        _raises(lambda: FS.register_us_fut(led, {**h, "instrument_book": "US_shares_KIS"}, run_utc="2026-10-07T00:00:03Z"), M.MacroRefusal, "CME_micro_ES")
        no_notional = {k: v for k, v in h.items() if k != "notional_nav"}
        _raises(lambda: FS.register_us_fut(led, no_notional, run_utc="2026-10-07T00:00:04Z"), M.MacroRefusal, "notional_nav")
        assert led.n_raw == 1 and led.verify_chain().ok
    assert GL.RULE_FAMILY["R-29"] == "R-06" and cards.registered_reject()["rerun"] is False      # the 50 bp card is never re-run


test_usfut_01_registered_once_second_50bp_book_raises.test_ids = ["T-USFUT-01", "I-13"]


def test_usfut_02_settling_run_logic_and_the_1926_fixture_refdata():
    """PASS only if PC-1' holds at 1x and 2x, >= 8 of 10 decade-spaced starts PASS with no REJECT at any start or
    in either half and the full span PASSes; 7 of 10 and 9 of 10 with one REJECT return no PASS; without the frozen
    1926 fixture the run is unavailable and never falls back to the 1990 file."""
    ok = ["PASS"] * 8 + ["REVISE"] * 2
    assert FS.settling_pass(True, True, ok, "PASS", "REVISE", "PASS")
    assert not FS.settling_pass(True, True, ["PASS"] * 7 + ["REVISE"] * 3, "PASS", "PASS", "PASS")          # 70 %
    assert not FS.settling_pass(True, True, ["PASS"] * 9 + ["REJECT"], "PASS", "PASS", "PASS")              # one REJECT start
    assert not FS.settling_pass(False, True, ok, "PASS", "PASS", "PASS") and not FS.settling_pass(True, False, ok, "PASS", "PASS", "PASS")
    assert not FS.settling_pass(True, True, ok, "REJECT", "PASS", "PASS") and not FS.settling_pass(True, True, ok, "PASS", "PASS", "INSUFFICIENT_DATA")
    assert not FS.settling_pass(True, True, ["PASS"] * 9, "PASS", "PASS", "PASS")                           # ten starts, integer counts
    starts = ["1926-08-02"] + [f"{y}-01-02" for y in range(1930, 2020, 10)]
    r = FS.settling_result(span="1926-07-01..2026-08-31", pc1p_1x=True, pc1p_2x=True, starts=starts, start_verdicts=["PASS"] * 9 + ["REJECT"], h1="PASS", h2="PASS", full_span="PASS")
    assert r["verdict"] != "PASS" and r["n_reject"] == 1 and r["n_pass"] == 9 and not r["settling_pass"]
    r2 = FS.settling_result(span="x", pc1p_1x=True, pc1p_2x=True, starts=starts, start_verdicts=ok, h1="PASS", h2="PASS", full_span="PASS")
    assert r2["verdict"] == "PASS" and r2["settling_pass"] and set(r2) >= {"span", "verdict", "pc1_prime_1x", "pc1_prime_2x", "starts", "n_pass", "n_starts", "n_reject", "midpoint_halves"}
    card_doc = synthetic_card()
    card_doc["settling_run"] = {k: v for k, v in r2.items() if k != "settling_pass"}
    assert S.validate("model_card.macro", card_doc) == []
    _raises(lambda: FS.settling_run(None), FS.SettlingRunUnavailable, FS.SETTLING_FIXTURE)
    _raises(lambda: FS.settling_run(ROOT / "tests" / "fixtures" / "macro" / FS.NEVER_FALLBACK), FS.SettlingRunUnavailable, "never falls back")
    assert STORE.get("cards.R-29_US_FUT.settling_run.full_span_must_pass") is True
    require_fixture(FS.SETTLING_FIXTURE)
    raise NotRun(f"REFDATA: {FS.SETTLING_FIXTURE} listed but the settling run needs the frozen gate package (P11)")


test_usfut_02_settling_run_logic_and_the_1926_fixture_refdata.test_ids = ["T-USFUT-02", "I-13"]


def test_task_m8_11_french_1926_daily_file_owner():
    """TASK-M8-11: the French daily Mkt-RF and RF from 1926-07 (DL-A fetch HTTP 403) with licence, owner and md5
    recorded in the manifest; a file without them is not a fixture."""
    raise require_owner("French Data Library daily Mkt-RF / RF 1926-07 -> 2026-08 "
                        f"({FS.SETTLING_FIXTURE}): acquire (HTTP 403), record licence, owner and md5 in MANIFEST.csv")


test_task_m8_11_french_1926_daily_file_owner.test_ids = ["T-USFUT-02"]


def test_usfut_03_promotion_guard_truth_table():
    """FORWARD-SIM unless the settling run passes and a US sleeve with notional >= ~KRW 1bn (one Micro ES <= 5 %)
    or another D5 line exists, and the v2 full-span verdict is PASS; today D5 is pending and the notional null."""
    today = FS.promotion_ok(settling_pass=True, v2_full_span="PASS", us_line=STORE.get("sleeves.US.line"), notional_nav_krw=STORE.get("sleeves.US.notional_nav"))
    assert not today.ok and FS.card_status(today) == "FORWARD_SIM" and any("D5" in r for r in today.reasons)
    assert FS.promotion_ok(settling_pass=True, v2_full_span="PASS", us_line="CME_micro_ES", notional_nav_krw=1.04e9).ok
    assert FS.promotion_ok(settling_pass=True, v2_full_span="PASS", us_line="CME_micro_ES", notional_nav_krw=52e6 / 0.05).ok
    r = FS.promotion_ok(settling_pass=True, v2_full_span="PASS", us_line="CME_micro_ES", notional_nav_krw=1.0e9)
    assert not r.ok and any("Micro ES" in x for x in r.reasons)
    r = FS.promotion_ok(settling_pass=True, v2_full_span="PASS", us_line="CME_micro_ES", notional_nav_krw=None)
    assert not r.ok and any("null" in x for x in r.reasons)
    assert FS.promotion_ok(settling_pass=True, v2_full_span="PASS", us_line="KRX_listed_SP500_ETF", notional_nav_krw=None).ok
    assert not FS.promotion_ok(settling_pass=False, v2_full_span="PASS", us_line="CME_micro_ES", notional_nav_krw=1.04e9).ok
    assert not FS.promotion_ok(settling_pass=True, v2_full_span="INSUFFICIENT_DATA", us_line="CME_micro_ES", notional_nav_krw=1.04e9).ok
    assert STORE.get("cards.R-29_US_FUT.promotion.requires") == ["us_sleeve_or_owner_line", "settling_run_pass", "v2_package_pass"]
    assert STORE.get("instruments.futures_granularity.contract_notional_krw.CME_micro_ES") == FS.CONTRACT_NOTIONAL_KRW
    assert cards.disposition_for({"card_id": FS.US_FUT_CARD, "family_id": "R-06"}, "NOT_RUN") == ("FORWARD_SIM", "descriptive")


test_usfut_03_promotion_guard_truth_table.test_ids = ["T-USFUT-03", "I-13"]


def test_usfut_04_monthly_and_banded_50bp_are_logged_trials_never_a_revision():
    h = _r29_header()
    with tempfile.TemporaryDirectory() as tmp:
        led = GL.family_ledger("R-06", Path(tmp))
        FS.register_us_fut(led, h, run_utc="2026-10-07T00:00:00Z")
        rows = FS.log_variant_trials(led, h, run_utc="2026-10-07T00:00:05Z")
        assert [r["params"]["variant"] for r in rows] == list(FS.LOGGED_TRIALS) == STORE.get("cards.R-29_US_FUT.logged_trials")
        assert all(r["run_kind"] == "variant" and r["card_id"] is None and r["cost"] == 50.0 and r["rule"] == "R-29" for r in rows)
        assert rows[0]["rebalance"] == "monthly" and rows[1]["params"]["no_trade_band"] == 0.10
        own = [r for r in led.rows() if r.get("card_id") == FS.US_FUT_CARD]
        assert len(own) == 1 and own[0]["cost"] == 5.0 and led.n_raw == 3 and led.verify_chain().ok
        assert len(FS.log_variant_trials(led, h, run_utc="2026-10-07T00:00:05Z")) == 2 and led.n_raw == 3      # the same configuration is the same trial


test_usfut_04_monthly_and_banded_50bp_are_logged_trials_never_a_revision.test_ids = ["T-USFUT-04", "I-13"]


def test_usfut_mechanics_vt_contracts_and_nav_fx_fail_closed():
    """vt_US = min(1, 0.15 / sigma_SMA20) on the futures line (cap 1.0, no floor; the R-06 formula on risk_layer.sma_vol);
    contracts round half away from zero and are None while the notional, the contract multiplier or the nav_fx read
    is missing; a book below the granularity floor is refused; the multiplier exists for forward_sim:R-29 only."""
    rng = np.random.default_rng(11)
    closes = list(5000.0 * np.cumprod(1 + rng.normal(0, 0.012, 60)))
    vt, sigma = FS.vt_us(closes)
    r = np.asarray(closes[1:]) / np.asarray(closes[:-1]) - 1
    assert abs(sigma - RL.sma_vol(r, 20)) < 1e-15 and abs(vt - min(1.0, 0.15 / sigma)) < 1e-15 and 0 < vt <= 1.0
    assert FS.vt_us(closes[:15]) == (None, None)
    _raises(lambda: FS.vt_us(closes, cap=1.5), M.MacroRefusal, "cap")
    calm = list(5000.0 * np.cumprod(1 + rng.normal(0, 0.001, 60)))
    assert FS.vt_us(calm)[0] == 1.0
    m = FS.vt_futures_multiplier(U(2026, 10, 1, 20, 0, 30), closes_daily=closes)
    assert m.factor == "vt" and m.book == FS.BOOK_R29 and abs(m.value - vt) < 1e-15 and m.card["disposition"] == "FORWARD_SIM"
    _raises(lambda: FS.vt_futures_multiplier(U(2026, 10, 1, 20, 0, 30), closes_daily=closes, book="recommended:US"), M.MacroRefusal, "forward_sim:R-29 only")
    carried = FS.vt_futures_multiplier(U(2026, 10, 1, 20, 0, 30), closes_daily=closes[:5], previous=0.6)
    assert carried.status == "fail_closed" and carried.value == 0.6
    assert FS.macro_state_forward_sim(None, m)["R29_vt_weight_next"] == m.value and FS.macro_state_forward_sim(None, carried)["R29_vt_weight_next"] is None
    assert FS.round_half_away_from_zero(2.5) == 3 and FS.round_half_away_from_zero(-2.5) == -3 and FS.round_half_away_from_zero(2.4) == 2 and round(2.5) == 2
    fx = P.to_value(P.stamp_quote("USDKRW_1530_SNAPSHOT", date(2026, 10, 1), 1400.0, quote_utc=U(2026, 10, 1, 6, 30), retrieved_at_utc=U(2026, 10, 1, 6, 31), source="KIS"),
                    role="forward_sim", books=("forward_sim:R-29",))
    c = FS.micro_es_contracts(0.8, 1.04e9, 5000.0, fx, multiplier_usd=5.0)
    assert c["contracts"] == FS.round_half_away_from_zero(0.8 * 1.04e9 / (5.0 * 5000.0 * 1400.0)) == 24 and c["usdkrw"] == 1400.0 and c["status"] == "ok"
    assert FS.micro_es_contracts(0.8, None, 5000.0, fx, multiplier_usd=5.0)["contracts"] is None               # notional null (owner)
    assert FS.micro_es_contracts(0.8, 1.04e9, 5000.0, fx)["status"] == "fail_closed"                               # contract multiplier OWNER_INPUT
    assert FS.micro_es_contracts(0.8, 1.0e9, 5000.0, fx, multiplier_usd=5.0)["status"] == "refused"               # granularity floor
    miss = P.MissingInput("USDKRW_1530_SNAPSHOT", "missing", "forward_sim", ("forward_sim:R-29",))
    assert FS.micro_es_contracts(0.8, 1.04e9, 5000.0, miss, multiplier_usd=5.0)["status"] == "fail_closed"
    store = P.PITStore(_tmp() / "store", registry=REG, clocks=CLK)
    got = FS.nav_fx_rate(store, U(2026, 10, 1, 20, 0, 30), U(2026, 10, 1, 21, 0), run_mode="live")
    assert isinstance(got, P.MissingInput) and got.series_id == "USDKRW_1530_SNAPSHOT" and got.role == "forward_sim"
    assert FS.NAV_FX["backtest"][0] == "ECOS_1530_CLOSE" and "DEXKOUS" not in str(FS.NAV_FX)
    assert STORE.get("cards.R-29_US_FUT.nav_fx") == {"series": "USDKRW_1530_SNAPSHOT", "history": "ECOS_1530_CLOSE"}


test_usfut_mechanics_vt_contracts_and_nav_fx_fail_closed.test_ids = ["I-13"]


def test_usfut_05_dla_u2_reproduction_refdata():
    require_fixture("french_daily_5f_2x3.csv")
    raise NotRun("REFDATA: U1 (French daily Mkt-RF 1990-02 -> 2026-08 + ^GSPC Sep-2026) loader not written; v1.2-check mode after the freeze")


test_usfut_05_dla_u2_reproduction_refdata.test_ids = ["T-USFUT-05"]


# --------------------------------------------------------------------------- #
# R-11 / R-12 refusal books: T-REF-01 / 02, T-BASIS-01 S2 clause, goldens REFDATA
# --------------------------------------------------------------------------- #
DEC_KR, KNW_KR = U(2026, 10, 2, 6, 30, 30), U(2026, 10, 2, 7, 0)
DEC_US, KNW_US = CLK.close_print_bound_utc("US", date(2026, 10, 1)), U(2026, 10, 1, 21, 0)


def _krw_store(path, krw) -> P.PITStore:
    store = P.PITStore(path, registry=REG, clocks=CLK)
    kr = _sessions("KR", date(2026, 10, 2), len(krw))
    store.append([P.stamp_release("ECOS_1530_CLOSE", d, v, retrieved_at_utc=CLK.publication_instant("ECOS_1530_CLOSE", d) + timedelta(minutes=5),
                                  source="ECOS", registry=REG, clocks=CLK) for d, v in zip(kr, krw)])
    return store


def _y10_store(path, y, *, live=True) -> P.PITStore:
    store = P.PITStore(path, registry=REG, clocks=CLK)
    us = _sessions("US", date(2026, 10, 1), len(y))
    if live:
        store.append([P.stamp_quote("US10Y_KIS_QUOTE", d, v, quote_utc=CLK.close_print_bound_utc("US", d) - timedelta(minutes=1),
                                    retrieved_at_utc=CLK.close_print_bound_utc("US", d), source="KIS") for d, v in zip(us, y)])
    else:
        store.append([P.stamp_release("DGS10", d, v, retrieved_at_utc=CLK.publication_instant("DGS10", d) + timedelta(minutes=5),
                                      source="FRED", registry=REG, clocks=CLK) for d, v in zip(us, y)])
    return store


def _is_static_isolated() -> None:
    assert CL.static_isolation_report() == []
    assert "core.quant.refusal" in CL.PROTECTED_MODULES and RF.__refusal_book__ is True and RF.BOOK_KIND == "refusal"
    for src in ("from core.quant import refusal\n", "import core.quant.refusal as r\n", "def f():\n    from core.quant.refusal import refusal_krw_leg\n"):
        for mod in ("core.quant.sleeves", "core.quant.risk_layer", "core.engine.books", "core.quant.signals"):
            hit = CL.scan_isolation({mod: src})
            assert hit and hit[0].kind == "import", (mod, src, hit)
    assert CL.scan_isolation({"core.skills.macro_daily": "from core.quant import refusal\n"}) == []   # the orchestrator may call it
    via = CL.scan_isolation({"core.quant.risk": "import core.quant.helper\n", "core.quant.helper": "from core.quant import refusal\n"})
    assert {v.module for v in via} >= {"core.quant.risk", "core.quant.helper"} and all(v.kind == "import" for v in via)


def test_ref_01_s1_retired_refusal_book_display_only():
    """S1 is absent from the FORWARD-SIM re-gate queue (regate_queue false; BL-S01 closed, BL-G04 / BL-D13 at P3);
    its archived record is REJECT (54 strict-H.10 onsets, dMDD -1.3 pp, tail 1.00; DL-A, not reproduced here);
    the leg reads the ECOS 15:30 close / 15:30 KST snapshot only (never DEXKOUS), gives {0.75, 1.0} with status
    REFUSAL for refusal:R-11 only, a null flag with the inputs absent, and no acting module can import or call it."""
    q = RF.regate_queue(STORE.doc)
    assert q == {"S1_krw": False, "S2_rates": False} and STORE.get("refusal_books.S1_krw.regate_queue") is False
    rec = RF.REFUSAL_RECORDS["R-11"]
    assert rec["verdict"] == "REJECT" and rec["backlog"] == {"BL-S01": "closed", "BL-G04": "P3", "BL-D13": "P3"} and rec["source"] == RF.RECORD_SOURCE
    s = rec["timings"]["strict_H10"]
    assert (s["onsets"], s["dMDD_pp"], s["tail"], s["tail_label"]) == (54, -1.3, 1.004, "tail 1.00")
    assert STORE.get("refusal_books.S1_krw") == {**RF.S1, "one_sided": True} and RF.S1_SERIES == ("USDKRW_1530_SNAPSHOT", "ECOS_1530_CLOSE")
    assert "DEXKOUS" not in RF.S1_SERIES and RF.NEVER_READ == ("DEXKOUS",)
    tmp = _tmp()
    empty = P.PITStore(tmp / "empty", registry=REG, clocks=CLK)
    m0 = RF.refusal_krw_leg(empty, DEC_KR, KNW_KR)
    assert m0.value == 1.0 and m0.status == "REFUSAL" and m0.flags["S1_krw_flag"] is None and m0.book == "refusal:R-11" and "absent" in m0.reasons[0]
    krw = [1350.0] * 21 + [1350.0 * math.exp(0.05)]          # +5 % log over 20 obs on the last day
    m1 = RF.refusal_krw_leg(_krw_store(tmp / "s1", krw), DEC_KR, KNW_KR)
    assert m1.value == 0.75 and m1.flags["S1_krw_flag"] is True and abs(m1.flags["krw20"] - 0.05) < 1e-12 and m1.flags["series"] == "ECOS_1530_CLOSE"
    assert m1.exposure_basis == "total" and m1.applies_to == "market_gross" and m1.factor == "overlay" and m1.status == RF.STATUS
    assert [i["name"] for i in m1.inputs] == ["usdkrw", "usdkrw"] and m1.inputs[-1]["role"] == "context"
    m2 = RF.refusal_krw_leg(_krw_store(tmp / "s2", [1350.0] * 21 + [1350.0 * math.exp(-0.05)]), DEC_KR, KNW_KR)    # won strengthens: one-sided
    assert m2.value == 1.0 and m2.flags["S1_krw_flag"] is False
    m3 = RF.refusal_krw_leg(_krw_store(tmp / "s3", [1350.0] * 21 + [1350.0 * math.exp(0.029)]), DEC_KR, KNW_KR)    # below the strict > 0.03
    assert m3.value == 1.0 and m3.flags["S1_krw_flag"] is False
    assert {m0.value, m1.value, m2.value} <= {0.75, 1.0}
    e = RF.overlay_refusal_entry(m1)
    assert e["card"]["verdict"] == "REJECT" and e["card"]["disposition"] == "REFUSAL_BOOK" and e["card"]["displayed_as"] == "refusal"
    assert not cards.check_display_invariant("REJECT", "REFUSAL_BOOK", "refusal") and not MA.acts_in_recommended(e["card"])
    assert RF.macro_state_flags(m1, None) == {"S1_krw_flag": True, "S2_rates_flag": None}
    assert cards.disposition_for({"family_id": "R-11"}, "REJECT") == ("REFUSAL_BOOK", "refusal")
    # the runtime guard: a call from an acting frame raises before any read
    ns = {"__name__": "core.quant.sleeves", "RF": RF, "empty": empty, "DEC": DEC_KR, "KNW": KNW_KR}
    exec("def call():\n    return RF.refusal_krw_leg(empty, DEC, KNW)\n", ns)
    _raises(ns["call"], CL.ContextIsolationError, "core.quant.sleeves")
    _is_static_isolated()


test_ref_01_s1_retired_refusal_book_display_only.test_ids = ["T-REF-01"]


def test_ref_02_s2_retired_refusal_book_and_the_s2_momentum_clause():
    """S2 is absent from the queue (BL-S02 closed); its record is REJECT with 71 onsets incl. the compliant Treasury
    +1 bd timing (-3.1 pp at 50 bp) and strict +2 bd (-3.5 pp); G-US-02a reads "compliant via Treasury with logged
    posting time"; the leg reads the KIS US 10y quote live (DGS10 only in a backtest), gives {0.5, 1.0} for
    refusal:R-12 only, and S2 applied to momentum (or any L/S sleeve, or Korea) raises."""
    rec = RF.REFUSAL_RECORDS["R-12"]
    assert rec["verdict"] == "REJECT" and rec["onsets"] == 71 and rec["onsets_split"] == {"1990-2007": 39, "2008-2026": 32} and rec["backlog"] == {"BL-S02": "closed"}
    assert rec["timings"]["treasury_plus_1bd"]["dMDD_pp_50bp"] == -3.1 and rec["timings"]["strict_H15_plus_2bd"]["dMDD_pp_50bp"] == -3.5
    assert rec["timings"]["treasury_plus_1bd"]["label"] == RF.G_US_02A_LABEL == "compliant via Treasury with logged posting time"
    assert rec["timing_fragile"] and rec["fragility_ratio"] == 0.75 > 0.5
    assert STORE.get("refusal_books.S2_rates.excludes") == ["momentum", "ls_factor_sleeves", "KR"] and STORE.get("refusal_books.S2_rates.regate_queue") is False
    tmp = _tmp()
    empty = P.PITStore(tmp / "empty", registry=REG, clocks=CLK)
    for bad in ("momentum", "reversal", "quality", "flow", "ls_factor_sleeves", "ts_trend"):
        _raises(lambda b=bad: RF.refusal_rates_leg(empty, DEC_US, KNW_US, applies_to=b), M.MacroRefusal, "T-BASIS-01")
    _raises(lambda: RF.refusal_rates_leg(empty, DEC_US, KNW_US, market="KR"), M.MacroRefusal, "US leg")
    m0 = RF.refusal_rates_leg(empty, DEC_US, KNW_US)
    assert m0.value == 1.0 and m0.status == "REFUSAL" and m0.flags["S2_rates_flag"] is None and m0.book == "refusal:R-12"
    y = [4.0] * 21 + [4.45]                                                              # +45 bp over 20 obs
    m1 = RF.refusal_rates_leg(_y10_store(tmp / "l1", y), DEC_US, KNW_US)
    assert m1.value == 0.5 and m1.flags["S2_rates_flag"] is True and abs(m1.flags["d10_pp"] - 0.45) < 1e-12 and m1.flags["series"] == "US10Y_KIS_QUOTE"
    assert "display only" in m1.reasons[0] and "data date 2026-10-01" in m1.reasons[0] and m1.flags["treasury_channel"] == RF.G_US_02A_LABEL
    m2 = RF.refusal_rates_leg(_y10_store(tmp / "l2", [4.0] * 21 + [4.39]), DEC_US, KNW_US)             # below the strict > 0.40
    assert m2.value == 1.0 and m2.flags["S2_rates_flag"] is False
    m3 = RF.refusal_rates_leg(_y10_store(tmp / "l3", [4.0] * 21 + [3.40]), DEC_US, KNW_US)             # falling yields: no action
    assert m3.value == 1.0 and m3.flags["S2_rates_flag"] is False
    # live never reads DGS10 (null flag with only H.15 rows); a backtest reads it at its strict H.15 availability
    only_h15 = _y10_store(tmp / "h15", y, live=False)
    assert RF.refusal_rates_leg(only_h15, DEC_US, KNW_US).flags["S2_rates_flag"] is None
    mb = RF.refusal_rates_leg(only_h15, DEC_US + timedelta(days=6), KNW_US + timedelta(days=6), run_mode="backtest")
    assert mb.flags["series"] == "DGS10" and mb.flags["timing"] == "strict_H15_plus_2bd" and mb.flags["S2_rates_flag"] is True
    assert {m0.value, m1.value, m2.value, mb.value} <= {0.5, 1.0}
    e = RF.overlay_refusal_entry(m1)
    assert e["would_apply_to"].startswith("US duration-sensitive gross") and e["card"]["card_id"] == "MACRO-R12-US-RATES" and e["card"]["verdict"] == "REJECT"
    assert RF.macro_state_flags(None, m1) == {"S1_krw_flag": None, "S2_rates_flag": True}
    assert RF.S2_STATE_REASON == "S2 refusal book: strict-H.15 flag on from the close of 2026-09-25 (data date 2026-09-23); display only"
    _is_static_isolated()


test_ref_02_s2_retired_refusal_book_and_the_s2_momentum_clause.test_ids = ["T-REF-02", "T-BASIS-01"]


def test_g_ref_01_s1_goldens_refdata():
    for f in ("yahoo_KS11_1996-12_2026-10-02.csv", "DEXKOUS.csv"):                  # F13; F18 FRED snapshot
        require_fixture(f)
    raise NotRun("REFDATA: G-KR-05 / G-KR-05s / G-REF-01 / G-POST-01 M8 rows need ^KS11 1997+, the FRED DEXKOUS snapshot of "
                 "2026-10-02, KRW=X 2004+ and QX_DLA_postpatch.csv; the record is archived council evidence (DL-A)")


test_g_ref_01_s1_goldens_refdata.test_ids = ["G-REF-01", "G-KR-05", "G-KR-05s", "G-POST-01"]


def test_g_ref_02_s2_goldens_refdata():
    for f in ("french_daily_5f_2x3.csv", "yahoo_GSPC_1990_2026-10-01.csv"):
        require_fixture(f)
    raise NotRun("REFDATA: G-REF-02 / G-US-02 / G-US-02a / G-US-02s / G-US-03 / G-US-04 need French Mkt-RF 1990-02 -> 2026-08 + "
                 "^GSPC, DGS10, Treasury par yields with posting times, ^TNX and the NDX / Russell 2000 duration proxies; the R-12 "
                 "record is archived council evidence (DL-A)")


test_g_ref_02_s2_goldens_refdata.test_ids = ["G-REF-02", "G-US-02", "G-US-02a", "G-US-02s", "G-US-03", "G-US-04"]


def tests():
    return [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
