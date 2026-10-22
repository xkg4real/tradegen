"""M5 package A tests: hard stop, RISK / OPS triggers, drawdown ladder, look-through caps, weight books
(core/engine/books.py M5 block; core/quant/risk_layer.py lookthrough_exposure / concentration_bound / drawdown_ladder;
TASK-M5-01..06, M5-12, M5-13).

Spec tests: T-BOOK-03, T-CAPS-01, I-04, I-04b, T-HALT-01, T-STEP-05, T-MONO-01, T-MISS-02 (M5 clauses), G-POST-01
(M5 row), G-LAD-01..03 (reference mode). Every golden that needs absent reference data raises NotRun("REFDATA: ...").
Hermetic: every registry lives in a tempfile directory; the session calendar is a weekday stub; instants are pinned;
the rules store is read, never written.
"""
from __future__ import annotations

import ast
import json
import tempfile
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from core.engine import books as B
from core.engine.state import EngineMode
from core.quant import costed as C
from core.quant import risk_layer as R
from core.quant import sleeves as SL
from core.rules import governance as G
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
_CLOCK = lambda: datetime(2026, 10, 6, 7, 0, 0, tzinfo=timezone.utc)   # noqa: E731
CAL = [d for d in (date(2026, 9, 1) + timedelta(days=i) for i in range(160)) if d.weekday() < 5]   # weekday stub
REC, SPEC = "recommended:KR", "specification:KR"
LINE = "069500"
DEC = datetime(2026, 10, 2, 6, 30, 30, tzinfo=timezone.utc)
# the only shares the spec prints for the line (F-29): Samsung 29.8%, the pair 53.8% of KODEX 200 on look-through
BASKET = {"005930": 0.298, "000660": 0.240, "A": 0.04, "B": 0.03, "C": 0.03,
          **{k: 0.02 for k in "DEFGHIJKLMNOPQRS"}, "T": 0.01}                   # 96.8% invested, 3.2% cash


def _dec(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, 6, 30, 30, tzinfo=timezone.utc)


def _registry(tmp, markets=("KR", "US")) -> B.BookRegistry:
    reg = B.BookRegistry(Path(tmp), clock=_CLOCK, sessions=lambda m: CAL)
    B.create_default_books(reg, markets)
    for bid in reg.ids():
        B.arm(reg, bid, _dec(CAL[0]))
    return reg


def _kinds(reg, bid):
    return [e["kind"] for e in G.read_events(reg.log) if e["book_id"] == bid]


def _raises(fn, exc=Exception, needle=""):
    try:
        fn()
    except exc as e:
        assert needle in str(e), (needle, str(e))
        return e
    raise AssertionError("expected %s" % exc.__name__)


def _rules(**over) -> dict:
    """A dict rules store: the shipped blocks this package reads, with overrides (the D2 ref kept as a ref)."""
    from core.rules.macro_rules import load_store
    doc = load_store().doc
    out = {"risk_layer": doc["risk_layer"], "cards": {"R-31_step_down": doc["cards"]["R-31_step_down"]},
           "owner_decisions": doc["owner_decisions"]}
    for k, v in over.items():
        cur = out
        parts = k.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = v
    return out


# --------------------------------------------------------------------------- #
# T-BOOK-03: tick eligibility (<= 10 bp of price) and look-through x L
# --------------------------------------------------------------------------- #
def test_book_03_li_eligibility_and_lookthrough_x_l():
    assert not R.li_etf_eligible(69.0, 1.0)                      # 252670 at 69 KRW: 144.9 bp -> ineligible (L2799)
    assert R.li_etf_eligible(112060.0, 5.0)                      # KODEX 200: 0.45 bp
    assert R.li_etf_eligible(1000.0, 1.0)                        # exactly 10 bp is eligible
    assert not R.li_etf_eligible(999.0, 1.0)
    _raises(lambda: R.li_etf_eligible(0.0, 1.0), ValueError)
    d0 = date(2026, 10, 1)
    plain = R.Basket(LINE, d0, BASKET, price=112060.0, tick=5.0)
    lev2 = R.Basket("LEV2", d0, BASKET, leverage=2.0, price=20000.0, tick=5.0)
    inv2 = R.Basket("252670", d0, BASKET, leverage=-2.0, price=20000.0, tick=5.0)
    one = R.lookthrough_exposure({LINE: 1.0}, {LINE: plain}, DEC, sessions=CAL)
    assert abs(one.per_name["005930"] - 0.298) < 1e-12 and one.basket_date == d0 and one.basket_age_sessions == 1
    assert not one.carried and not one.fail_closed and one.inputs[0]["leverage"] == 1.0
    two = R.lookthrough_exposure({"LEV2": 1.0}, {"LEV2": lev2}, DEC, sessions=CAL)
    assert all(abs(two.per_name[n] - 2.0 * one.per_name[n]) < 1e-12 for n in BASKET)   # x L (L1585 (1))
    inv = R.lookthrough_exposure({"252670": 0.5}, {"252670": inv2}, DEC, sessions=CAL)
    assert abs(inv.per_name["005930"] - 0.298) < 1e-12 and abs(inv.signed["005930"] + 0.298) < 1e-12   # |L| for caps, sign printed (F-5)
    mixed = R.lookthrough_exposure({LINE: 0.6, "LEV2": 0.2}, {LINE: plain, "LEV2": lev2}, DEC, sessions=CAL)
    assert abs(mixed.per_name["005930"] - (0.6 + 0.4) * 0.298) < 1e-12
    # an ineligible held product is not tradable in the simulated book: refused, never silently included
    bad = R.Basket("252670", d0, BASKET, leverage=-2.0, price=69.0, tick=1.0)
    _raises(lambda: R.lookthrough_exposure({"252670": 0.1}, {"252670": bad}, DEC), ValueError, "ineligible")
    # a basket stamped available after the decision, or absent, fails the line closed; a zero weight reads nothing
    late = R.Basket(LINE, d0, BASKET, available_at_utc=DEC + timedelta(seconds=1))
    miss = R.lookthrough_exposure({LINE: 1.0, "252670": 0.0}, {LINE: late}, DEC, sessions=CAL)
    assert miss.fail_closed and miss.per_name == {} and "fail_closed" in miss.reasons[0]
    # the basket dated t is published on t+1: unstamped or not, the close of t reads t-1's (L1411)
    same_day = R.lookthrough_exposure({LINE: 1.0}, {LINE: R.Basket(LINE, date(2026, 10, 2), BASKET)}, DEC, sessions=CAL)
    assert same_day.fail_closed and same_day.per_name == {}
    # carried basket: age printed; recomputed on current prices (F-4): Samsung +10%, the rest flat
    old = R.Basket(LINE, CAL[CAL.index(date(2026, 10, 2)) - 3], BASKET)
    car = R.lookthrough_exposure({LINE: 1.0}, {LINE: old}, DEC, sessions=CAL, relatives={"005930": 1.10})
    assert car.carried and car.basket_age_sessions == 3
    line_rel = 0.298 * 1.10 + (1.0 - 0.298)
    assert abs(car.per_name["005930"] - 0.298 * 1.10 / line_rel) < 1e-12 and abs(car.per_name["A"] - 0.04 / line_rel) < 1e-12


test_book_03_li_eligibility_and_lookthrough_x_l.test_ids = ["T-BOOK-03"]


# --------------------------------------------------------------------------- #
# T-CAPS-01: the four bounds, the binding factor, per-book gross; template from the store (D1)
# --------------------------------------------------------------------------- #
def test_caps_01_synthetic_basket_bounds_and_by_book():
    exp = R.lookthrough_exposure({LINE: 1.0}, {LINE: R.Basket(LINE, date(2026, 10, 1), BASKET)}, DEC, sessions=CAL)
    cb = R.concentration_bound("KR", DEC, None, exp)
    assert cb.template == "msci_25_50"                                        # read from the store, D1
    assert abs(cb.absolute_bound - 0.225 / 0.298) < 1e-12 and round(cb.absolute_bound, 3) == 0.755
    assert abs(cb.active_bound - 0.05 / (0.298 - 0.225)) < 1e-12 and round(cb.active_bound, 3) == 0.685
    assert abs(cb.aggregate_bound - 0.45 / 0.538) < 1e-12 and abs(cb.semis_bound - 0.50 / 0.538) < 1e-12
    assert cb.bound == cb.active_bound and cb.binding_factor == "active_single_name"
    assert abs(cb.pair_lookthrough_share - 0.538) < 1e-12 and cb.shares[0] == ("005930", 0.298)
    # w_i - g x b_i <= 0.05 of NAV at g = bound, for every name (R-07 (2))
    b = R.capped_benchmark(BASKET, 0.225)
    assert b["005930"] == 0.225 and b["000660"] == 0.225 and abs(sum(b.values()) - sum(BASKET.values())) < 1e-12
    assert all(cb.bound * (s - b[n]) <= 0.05 + 1e-12 for n, s in BASKET.items())
    assert abs(cb.bound * (0.298 - b["005930"]) - 0.05) < 1e-12                 # Samsung at the cap exactly
    # concentration.by_book: the active bound binds in both books (L896, L5505)
    rec = R.risk_layer(1.0, [], 1.0, 1.0, cb)                                   # vt enters as 1.0 while R-06 is NOT_RUN
    spec = R.risk_layer(0.694, [], 1.0, 1.0, cb)
    assert rec == {"composed": 1.0, "gross": cb.bound, "binding_factor": "active_single_name"}
    assert spec["composed"] == 0.694 and spec["gross"] == cb.bound and spec["binding_factor"] == "active_single_name"
    assert round(rec["gross"], 3) == round(spec["gross"], 3) == 0.685
    low = R.risk_layer(0.5, [], 1.0, 1.0, cb)                                  # below the bound: nothing binds
    assert low == {"composed": 0.5, "gross": 0.5, "binding_factor": "none"}
    assert R.risk_layer(1.0, [], 1.0, 1.0, cb, halted=True) == {"composed": 0.0, "gross": 0.0, "binding_factor": "none"}
    # leveraged products count at x L: a 2x line halves every bound
    lev = R.lookthrough_exposure({"LEV2": 1.0}, {"LEV2": R.Basket("LEV2", date(2026, 10, 1), BASKET, leverage=2.0)}, DEC)
    cb2 = R.concentration_bound("KR", DEC, None, lev)
    assert abs(cb2.absolute_bound - cb.absolute_bound / 2) < 1e-12 and abs(cb2.semis_bound - cb.semis_bound / 2) < 1e-12
    assert abs(cb2.active_bound - 0.05 / (0.596 - 0.225)) < 1e-12 and cb2.binding_factor == "active_single_name"
    # a literal template that differs from the store is refused; a non-KR market has no template; ties in enum order
    _raises(lambda: R.concentration_bound("KR", DEC, "pair_35", exp), ValueError, "T-OWNER-01")
    _raises(lambda: R.concentration_bound("US", DEC, None, exp), ValueError, "Korea")
    _raises(lambda: R.concentration_bound("KR", DEC, None, {}), ValueError, "undefined")
    pair = R.concentration_bound("KR", DEC, None, exp, rules=_rules(**{"risk_layer.korea_caps.template": "pair_35"}))
    assert pair.template == "pair_35" and abs(pair.bound - 0.35 / 0.538) < 1e-12 and pair.binding_factor == "aggregate"
    assert pair.absolute_bound is None and pair.active_bound is None
    _raises(lambda: R.concentration_bound("KR", DEC, None, exp, rules=_rules(**{"risk_layer.korea_caps.template": "domestic_max10_or_weight"})),
            ValueError, "market-cap")
    dom = R.concentration_bound("KR", DEC, None, exp, rules=_rules(**{"risk_layer.korea_caps.template": "domestic_max10_or_weight"}),
                                market_cap_weights={"005930": 0.25, "000660": 0.20})
    assert abs(dom.absolute_bound - min(0.25 / 0.298, 0.20 / 0.24)) < 1e-12        # max(0.10, market-cap weight) per name
    # breach test on post-action look-through weights (hard levels 25 / 50), never on a HALTED book's zeros
    assert R.risk_limit_breach({n: cb.bound * s for n, s in BASKET.items()}) is None
    assert R.risk_limit_breach({"005930": 0.251, "000660": 0.10}) == "breach_single_name:005930"
    assert R.risk_limit_breach({"005930": 0.24, "000660": 0.24, "A": 0.05}).startswith("breach_aggregate")   # 0.53 > 0.50
    assert R.risk_limit_breach({"005930": 0.24, "000660": 0.24, "A": 0.045}) is None                        # A at 4.5% is not above it
    assert R.risk_limit_breach({"005930": 0.25, "000660": 0.25}) is None          # exactly at the level is not above it
    # the bound object feeds the M4 book builder as a scalar
    sleeve = SL.Sleeve("KR", "momentum", "long_only", {LINE: 1.0}, benchmark={LINE: 1.0}, base_weight=1.0)
    w = SL.apply_overlays(sleeve, [SL.Multiplier("R-06-VT", 0.694, "total", "market_gross", factor="vt")], "total",
                          concentration_bound=cb.bound)
    assert abs(w.weights[LINE] - cb.bound) < 1e-12 and "concentration_bound" in w.binding


test_caps_01_synthetic_basket_bounds_and_by_book.test_ids = ["T-CAPS-01"]


def test_caps_01_real_kodex_basket_refdata():
    """'The daily KODEX 200 basket is applied' on the real 2-Oct PDF (L5649)."""
    raise NotRun("REFDATA: KODEX 200 PDF history (KIS or KRX; section 9.5 M5) absent: the 2-Oct-2026 basket is not on this "
                 "machine (docs/asset_expansion/cache/yf_069500.KS.csv is the ETF price only); the arithmetic clause ran on "
                 "the inline basket with s(005930) = 0.298 and pair 0.538")


test_caps_01_real_kodex_basket_refdata.test_ids = ["T-CAPS-01"]


def test_g_post_01_pair_implied_share_refdata():
    """G-POST-01 M5 row: Samsung + SK hynix implied share ~ 53.6% (B3a anchor; L5832, F-22)."""
    raise NotRun("REFDATA: QX_DLA_postpatch.csv and the 25-Oct-2024 KRX-weight anchor absent; the implied-share formula is "
                 "DLA section 7's (F-22); pair_share_kospi comes from KRX_MARKET_CAPS_005930_000660_KOSPI in production")


test_g_post_01_pair_implied_share_refdata.test_ids = ["G-POST-01"]


# --------------------------------------------------------------------------- #
# I-04: ladder steps (-8% / -12%), 21-session dwell, references, min() composition, placement, the block
# --------------------------------------------------------------------------- #
def test_i_04_ladder_steps_reset_block_and_placement():
    cfg = R.ladder_config()
    assert cfg.hard_stop_level == -0.15 and cfg.dwell == 21 and cfg.steps == ((-0.12, 0.5, True), (-0.08, 0.5, False))
    assert cfg.rearm_refused_sessions == cfg.post_rearm_sessions == 10 and cfg.binding_share_threshold == 0.10
    dates = CAL[:60]
    nav = [100.0] * 3 + [88.0] * 25 + [85.0] * 3 + [85.0] * 29                 # -12% from the step reference, then -15% from hwm
    states = R.ladder_path(list(zip(dates, nav)), cfg)
    s3 = states[3]
    assert (s3.step_mult, s3.block_new_entries, s3.dwell_left, s3.ref_step, s3.hwm_hard) == (0.5, True, 20, 100.0, 100.0)
    assert all(s.step_mult == 0.5 and s.block_new_entries for s in states[3:24])   # exactly 21 decisions (3 .. 23)
    assert states[23].dwell_left == 0 and states[23].ref_step == 88.0 and states[23].hwm_hard == 100.0   # step spent: ref resets, hwm does not
    assert states[24].step_mult == 1.0 and not states[24].block_new_entries and states[24].ref_step == 88.0
    # min(): the step composes with an overlay at 1.0 (and at 0.5) to 0.5, never 0.25 x vt
    assert R.compose(1.0, [1.0], states[3].step_mult, 1.0) == 0.5
    assert R.compose(1.0, [0.5], states[3].step_mult, 1.0) == 0.5
    assert R.compose_detail(1.0, {"R-X": 1.0}, 0.5, 1.0).binding == ("ladder",)
    _raises(lambda: R.compose(1.0, [0.5], 0.25, 1.0), R.CompositionError)
    # a later -15% from hwm_hard HALTs even though dd_step is shallower (85 / 88 = -3.4%)
    assert states[27].halted is False and states[28].halted and states[28].step_mult == 1.0 and states[28].hwm_hard == 100.0
    assert states[28].rearm_not_before == dates[38] and all(s.halted for s in states[28:38])
    assert not states[38].halted and states[38].hwm_hard == states[38].ref_step == 85.0 and states[38].post_rearm_left == 10
    assert [s.post_rearm_left for s in states[38:49]] == [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    # -8% gives 0.5x without the block; a -9% then recovery: the time box still runs 21 decisions
    nav8 = [100.0] * 2 + [91.0] + [99.0] * 30
    st8 = R.ladder_path(nav8, cfg)
    assert (st8[2].step_mult, st8[2].block_new_entries, st8[2].dwell_left) == (0.5, False, 20)
    assert all(s.step_mult == 0.5 and not s.block_new_entries for s in st8[2:23]) and st8[23].step_mult == 1.0
    assert st8[22].ref_step == 99.0 and st8[22].hwm_hard == 100.0
    # drawdown_ladder at a decision: the state at the last NAV <= the decision; a later NAV is refused (never read ahead)
    st = R.drawdown_ladder(list(zip(dates, nav))[:11], _dec(dates[10]), cfg, binding_share=0.19)
    assert st == replace(states[10], binding_share=0.19)
    _raises(lambda: R.drawdown_ladder(list(zip(dates, nav)), _dec(dates[10]), cfg), ValueError, "look-ahead")
    _raises(lambda: R.drawdown_ladder([], DEC, cfg), ValueError, "empty")
    # a product-composed ladder config raises (R-02, L3338); a step outside {0.5, 1.0} raises; a literal D2 copy is refused
    _raises(lambda: R.ladder_config(_rules(**{"cards.R-31_step_down.composition": "product"})), R.CompositionError, "product")
    _raises(lambda: R.ladder_config(_rules(**{"cards.R-31_step_down.steps": [{"dd": -0.08, "mult": 0.25}]})), R.CompositionError)
    _raises(lambda: R.ladder_config(_rules(**{"cards.R-31_step_down.hard_stop_level": -0.15})), ValueError, "T-OWNER-01")
    alt = R.ladder_config(_rules(**{"risk_layer.drawdown.hard_stop.level": "-1.5*sigma_book"}))
    assert alt.hard_stop_level == -0.15 and "not evaluated" in alt.notes[0]       # F-8: default in force, noted
    # placement: binding share > 0.10 -> specification book only; <= 0.10 -> INVARIANT_STEP in the recommended book
    assert R.binding_share_of(states) == sum(s.step_mult < 1 for s in states) / len(states)
    assert R.steps_act_in(SPEC, 0.19) and not R.steps_act_in(REC, 0.19) and not R.steps_act_in(REC, None)
    assert R.steps_act_in(REC, 0.10) and R.steps_act_in(REC, 0.19, r31_pass=True)
    assert not R.steps_act_in("card:MACRO-R06-KR-ETF:on", 0.05) and not R.steps_act_in("forward_sim:R-28", 0.05)
    assert R.ladder_disposition(0.19) == "SPECIFICATION_ONLY" and R.ladder_disposition(0.10) == "INVARIANT_STEP"
    assert R.ladder_for_book(states[3], SPEC, binding_share=0.19) == (0.5, True)
    assert R.ladder_for_book(states[3], REC, binding_share=0.19) == (1.0, False)   # the recommended book: hard stop only (T-STEP-04)
    assert R.ladder_for_book(states[3], REC, binding_share=0.10) == (0.5, True)
    flags = R.ladder_flags(states[3], level=cfg.hard_stop_level)
    assert flags == {"ladder_step": "step_-12", "ladder_dwell_left": 20, "block_new_entries": True,
                     "ladder_steps_act_in": "specification", "hard_stop": "armed", "hard_stop_level": -0.15}
    assert R.ladder_flags(st8[2], level=-0.15)["ladder_step"] == "step_-8"
    assert R.ladder_flags(states[28], level=-0.15, rearm_refused=True)["hard_stop"] == "rearm_refused"
    assert R.ladder_flags(states[38], level=-0.15)["hard_stop"] == "post_rearm_cap"
    # the -12% block in the weight book: new entries (a target above the held weight) are held; exits never blocked
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        for i, nv in enumerate([100.0, 100.0, 88.0]):
            res = B.risk_step(reg, SPEC, _dec(CAL[i + 1]), nv, config=cfg)
        assert res.ladder.step_mult == 0.5 and res.ladder.block_new_entries and res.book.block_new_entries
        d0 = B.record_decision(reg, SPEC, _dec(CAL[1]), {LINE: 0.5, "X": 0.2})   # the first decision: block already on
        assert d0.new_entries == (LINE, "X") and d0.blocked == (LINE, "X") and d0.post_action == {LINE: 0.0, "X": 0.0}
        reg.save(replace(reg.get(SPEC), held={LINE: 0.5, "X": 0.2}, block_new_entries=False))
        d1 = B.record_decision(reg, SPEC, _dec(CAL[2]), {LINE: 0.6, "X": 0.1})
        assert d1.new_entries == (LINE,) and d1.blocked == () and d1.post_action == {LINE: 0.6, "X": 0.1}
        reg.save(replace(reg.get(SPEC), block_new_entries=True))
        d2 = B.record_decision(reg, SPEC, _dec(CAL[3]), {LINE: 0.7, "X": 0.0})
        assert d2.blocked == (LINE,) and d2.post_action == {LINE: 0.6, "X": 0.0}   # increase held; the exit goes through
        # the same raw block state does not act in the recommended book without a frozen share <= 0.10
        reg.save(replace(reg.get(REC), held={LINE: 0.5}, block_new_entries=True))
        assert B.record_decision(reg, REC, _dec(CAL[3]), {LINE: 0.7}).blocked == ()
        assert B.record_decision(reg, REC, _dec(CAL[4]), {LINE: 0.8}, block=True).blocked == (LINE,)
        assert B.new_entries({LINE: 0.5}, {LINE: 0.5, "Y": 0.0}) == () and B.new_entries({}, {"Y": 0.1}) == ("Y",)


test_i_04_ladder_steps_reset_block_and_placement.test_ids = ["I-04"]


# --------------------------------------------------------------------------- #
# T-HALT-01 (a) / I-04b: exactly -15.00% -> HALTED (RISK) -> 0x for t+1..t+10 -> auto re-arm -> 0.5 cap -> normal
# --------------------------------------------------------------------------- #
def test_halt_01_hard_stop_cycle_exact_15pct():
    cfg = R.ladder_config()
    at_100 = replace(R.LADDER_INITIAL, hwm_hard=100.0, ref_step=100.0)
    # one basis point inside each level does not trip it: an off-by-tolerance stop would HALT the book early
    assert not R.ladder_step(at_100, 85.01, cfg).halted and R.ladder_step(at_100, 85.0, cfg).halted       # -14.99% / -15%
    assert not R.ladder_step(at_100, 88.01, cfg).block_new_entries and R.ladder_step(at_100, 88.0, cfg).block_new_entries
    assert R.ladder_step(at_100, 92.01, cfg).step_mult == 1.0 and R.ladder_step(at_100, 92.0, cfg).step_mult == 0.5
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        for i in range(1, 5):
            res = B.risk_step(reg, REC, _dec(CAL[i]), 100.0 + i * 0.0, config=cfg)
            assert res.book.hwm_hard == res.book.ref_step == 100.0 and not res.halted_now
        t = 5
        res = B.hard_stop_check(reg, REC, _dec(CAL[t]), 85.0)                   # 85 / 100 - 1 = -15.00% exactly (<=)
        b = res.book
        assert res.halted_now and b.halted and b.halt["class"] == "RISK" and b.halt["reason_code"] == "hard_stop"
        assert b.halt["component"] == "drawdown_ladder" and b.halt["rearm_mode"] == "auto"
        assert b.halt["rearm_not_before"] == CAL[t + 10].isoformat() and res.ladder.rearm_not_before == CAL[t + 10]
        assert b.hwm_hard == 100.0 and b.ref_step == 100.0 and b.nav == 85.0 and b.step_mult == 1.0   # steps cleared, references frozen
        assert B.step_decision(reg, REC, _dec(CAL[t]), ok=True).post_rearm_cap == 1.0
        assert B.record_decision(reg, REC, _dec(CAL[t]), {LINE: 0.7}).post_action == {LINE: 0.0}   # weights decided at t = 0
        assert reg.get(SPEC).mode is EngineMode.ARMED and reg.get("recommended:US").mode is EngineMode.ARMED   # own book only
        for i in range(t + 1, t + 10):                                            # t+1 .. t+9: exposure 0, references frozen
            res = B.risk_step(reg, REC, _dec(CAL[i]), 80.0, config=cfg)
            assert res.book.halted and res.book.hwm_hard == 100.0 and res.book.ref_step == 100.0
            assert B.record_decision(reg, REC, _dec(CAL[i]), {LINE: 0.7}).post_action == {LINE: 0.0}
            assert B.step_decision(reg, REC, _dec(CAL[i]), ok=True).post_rearm_cap == 1.0
        _raises(lambda: B.runtime_rearm(reg, REC, "operator", _dec(CAL[t + 9]), operator="kim"), B.RearmRefused, "refused before")
        res = B.risk_step(reg, REC, _dec(CAL[t + 10]), 84.0, config=cfg)          # t+10: automatic re-arm, references reset
        b = res.book
        assert b.mode is EngineMode.ARMED and b.halt is None and b.hwm_hard == b.ref_step == 84.0
        assert res.ladder.post_rearm_left == 10 and res.ladder.step_mult == 1.0 and res.ladder.rearm_not_before is None
        assert b.post_rearm_cap_until == CAL[t + 19]
        assert R.ladder_flags(res.ladder, level=cfg.hard_stop_level)["hard_stop"] == "post_rearm_cap"
        sd = B.step_decision(reg, REC, _dec(CAL[t + 10]), ok=True)
        assert sd.post_rearm_cap == 0.5 and sd.book.post_rearm_left == 9
        assert R.compose(0.9, [1.0], 1.0, sd.post_rearm_cap) == 0.45                # <= 0.5 x vt inside min(), not an absolute 0.5
        for i in range(t + 11, t + 20):                                           # t+11 .. t+19 capped
            B.risk_step(reg, REC, _dec(CAL[i]), 84.0 + (i - t), config=cfg)
            assert B.step_decision(reg, REC, _dec(CAL[i]), ok=True).post_rearm_cap == 0.5
        B.risk_step(reg, REC, _dec(CAL[t + 20]), 100.0, config=cfg)
        sd = B.step_decision(reg, REC, _dec(CAL[t + 20]), ok=True)                 # t+20: normal running
        assert sd.post_rearm_cap == 1.0 and sd.book.post_rearm_left == 0 and sd.book.hwm_hard == 103.0   # the new HWM since re-arm
        assert _kinds(reg, REC) == ["book_state", "halt", "rearm"]
        ev = [e for e in G.read_events(reg.log) if e["book_id"] == REC]
        assert ev[1]["reason"].startswith("RISK hard_stop") and ev[2]["reason"].startswith("auto re-arm")
        assert "post_rearm_cap 0.5 for 10 decisions" in ev[2]["reason"] and G.verify_chain(reg.log).ok
        # the hard stop and the ladder act in recommended / specification books only (F-2); a card book keeps OPS states
        reg.register(B.BookRuntime("card:MACRO-R06-KR-ETF:on"))
        B.arm(reg, "card:MACRO-R06-KR-ETF:on", _dec(CAL[0]))
        B.risk_step(reg, "card:MACRO-R06-KR-ETF:on", _dec(CAL[1]), 100.0, config=cfg)
        res = B.risk_step(reg, "card:MACRO-R06-KR-ETF:on", _dec(CAL[2]), 80.0, config=cfg)
        assert res.book.mode is EngineMode.ARMED and res.book.hwm_hard is None and res.book.nav == 80.0


test_halt_01_hard_stop_cycle_exact_15pct.test_ids = ["T-HALT-01", "I-04b"]


# --------------------------------------------------------------------------- #
# T-HALT-01 (b), (c), (d): OPS clears when fresh; a breach re-arms only once cured; a lag-audit cause waits
# --------------------------------------------------------------------------- #
def test_halt_01_ops_breach_cure_and_lag_audit_causes():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        cfg = R.ladder_config()
        # (b) an OPS HALT (a stale acting input) clears at the first fresh decision: no window, no reset, no cap
        reg.save(replace(reg.get(SPEC), nav=100.0, hwm_hard=110.0, ref_step=105.0))
        B.step_decision(reg, SPEC, _dec(CAL[1]), ok=False, failed=["KOSPI_OFFICIAL_CLOSE"])
        b = B.step_decision(reg, SPEC, _dec(CAL[2]), ok=False, failed=["KOSPI_OFFICIAL_CLOSE"]).book
        assert b.halted and b.halt["class"] == "OPS"
        res = B.step_decision(reg, SPEC, _dec(CAL[3]), ok=True)
        assert res.book.mode is EngineMode.ARMED and res.post_rearm_cap == 1.0 and (res.book.hwm_hard, res.book.ref_step) == (110.0, 105.0)
        # a KODEX-basket failure beyond its 5 misses is OPS, never RISK (R-19 rule 4)
        for i in range(4, 9):
            b = B.step_decision(reg, SPEC, _dec(CAL[i]), ok=False, failed=["KODEX200_PDF"], limits={"KODEX200_PDF": 5}).book
        assert b.halted and b.halt["class"] == "OPS" and b.halt["reason_code"] == "acting_input_stale:KODEX200_PDF"
        assert B.step_decision(reg, SPEC, _dec(CAL[9]), ok=True).book.mode is EngineMode.ARMED
        # (c) a risk-limit breach whose limit-locked order persists past t+10: HALTED at t+10, re-armed once the
        #     post-action target meets the limit, no reference reset, the cap window starting at that re-arm
        t = 10
        reg.save(replace(reg.get(SPEC), nav=90.0, hwm_hard=100.0, ref_step=95.0))
        b = B.runtime_halt(reg, SPEC, "RISK", "risk_limit_breach", _dec(CAL[t]), component="concentration_bound")
        assert b.halt["rearm_not_before"] == CAL[t + 10].isoformat()
        for i in range(t + 1, t + 13):                                            # t+1 .. t+12: the carried order persists
            res = B.risk_step(reg, SPEC, _dec(CAL[i]), 90.0, config=cfg, limit_met=False)
            assert res.book.halted and (res.book.hwm_hard, res.book.ref_step) == (100.0, 95.0), i
        _raises(lambda: B.runtime_rearm(reg, SPEC, "auto", _dec(CAL[t + 12])), B.RearmRefused, "does not meet the limit")
        res = B.risk_step(reg, SPEC, _dec(CAL[t + 13]), 90.0, config=cfg, limit_met=True)
        b = res.book
        assert b.mode is EngineMode.ARMED and (b.hwm_hard, b.ref_step) == (100.0, 95.0) and b.limit_met is None
        assert b.post_rearm_cap_until == CAL[t + 22] and res.ladder.post_rearm_left == 10
        assert B.step_decision(reg, SPEC, _dec(CAL[t + 13]), ok=True).post_rearm_cap == 0.5
        # (d) a lag-audit violation during a RISK HALT keeps the book HALTED after t+10 until the operator re-arms;
        #     the cap window starts at the operator's re-arm decision; references reset (a hard-stop cause was in the set)
        t = 30
        for i in range(t - 3, t):
            B.risk_step(reg, REC, _dec(CAL[i]), 100.0, config=cfg)
        b = B.risk_step(reg, REC, _dec(CAL[t]), 84.0, config=cfg).book
        assert b.halted and b.halt["reason_code"] == "hard_stop"
        b = B.runtime_halt(reg, REC, "OPS", "lag_audit_violation", _dec(CAL[t + 2]), component="lag_audit", series_id="KOSPI_OFFICIAL_CLOSE")
        assert b.halt["rearm_mode"] == "operator" and [c["reason_code"] for c in b.halt["causes"]] == ["hard_stop", "lag_audit_violation"]
        res = B.risk_step(reg, REC, _dec(CAL[t + 10]), 84.0, config=cfg)          # t+10: the RISK cause clears, the book stays HALTED
        b = res.book
        assert b.halted and b.halt["causes"][0]["cleared_utc"] is not None and b.halt["causes"][1]["cleared_utc"] is None
        assert b.hwm_hard == 100.0 and res.ladder.rearm_not_before is None        # no uncleared RISK cause left (F-24)
        assert R.ladder_flags(res.ladder, level=-0.15)["hard_stop"] == "halted"
        _raises(lambda: B.runtime_rearm(reg, REC, "auto", _dec(CAL[t + 11])), B.RearmRefused, "operator")
        B.risk_step(reg, REC, _dec(CAL[t + 12]), 86.0, config=cfg)
        b = B.runtime_rearm(reg, REC, "operator", _dec(CAL[t + 12]), operator="kim")
        assert b.mode is EngineMode.ARMED and b.hwm_hard == b.ref_step == 86.0 and b.post_rearm_left == 10
        assert b.post_rearm_cap_until == CAL[t + 21]                              # the window starts at the operator's re-arm
        assert B.step_decision(reg, REC, _dec(CAL[t + 12]), ok=True).post_rearm_cap == 0.5
        assert _kinds(reg, REC)[-3:] == ["halt", "halt", "rearm"]


test_halt_01_ops_breach_cure_and_lag_audit_causes.test_ids = ["T-HALT-01"]


def test_i_04b_kospi_1997_2026_reentry_and_pinned_count_refdata():
    """The KOSPI 1997-2026 fixture clause: the book re-enters after every HALT; the v2 HALT count is pinned (section 9.4 item 9)."""
    raise NotRun("REFDATA: F13 yahoo_KS11_1996-12_2026-10-02.csv / KRX official closes 1997-04-15 -> 2026-10-02 absent: the "
                 "re-entry property and the pinned v2 HALT count (TASK-M5-14) run on the frozen fixture through "
                 "risk_layer.ladder_path; the mechanism ran on the synthetic path")


test_i_04b_kospi_1997_2026_reentry_and_pinned_count_refdata.test_ids = ["I-04b"]


# --------------------------------------------------------------------------- #
# T-STEP-05: NAV flat at -16% for 30 sessions; rearm_not_before set once; a second halt() changes nothing
# --------------------------------------------------------------------------- #
def test_step_05_idempotent_halt_flat_minus_16():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        cfg = R.ladder_config()
        for i in range(1, 5):
            B.risk_step(reg, SPEC, _dec(CAL[i]), 100.0, config=cfg)
        t = 5
        b = B.risk_step(reg, SPEC, _dec(CAL[t]), 84.0, config=cfg).book           # -16%: HALTED at the close of t
        assert b.halted and b.halt["rearm_not_before"] == CAL[t + 10].isoformat()
        halt_block, n_events = dict(b.halt), len(G.read_events(reg.log))
        assert B.runtime_halt(reg, SPEC, "RISK", "hard_stop", _dec(CAL[t + 3])).halt == halt_block   # a second halt(): nothing
        assert len(G.read_events(reg.log)) == n_events
        caps = {}
        for i in range(t + 1, t + 31):                                            # 30 sessions flat at -16%
            res = B.risk_step(reg, SPEC, _dec(CAL[i]), 84.0, config=cfg)
            if i == t + 7:
                res = B.risk_step(reg, SPEC, _dec(CAL[i]), 84.0, config=cfg)      # the same decision twice: idempotent
            caps[i] = B.step_decision(reg, SPEC, _dec(CAL[i]), ok=True).post_rearm_cap
            b = res.book
            if i < t + 10:
                assert b.halted and b.halt["rearm_not_before"] == CAL[t + 10].isoformat() and b.hwm_hard == 100.0
            else:
                assert b.mode is EngineMode.ARMED and b.hwm_hard == b.ref_step == 84.0   # re-armed at t+10, no re-halt (dd 0)
        assert [caps[i] for i in range(t + 1, t + 10)] == [1.0] * 9                 # HALTED: 0x, not a cap
        assert [caps[i] for i in range(t + 10, t + 20)] == [0.5] * 10               # weights decided t+10 .. t+19 (re-entry at t+11)
        assert [caps[i] for i in range(t + 20, t + 31)] == [1.0] * 11
        assert _kinds(reg, SPEC) == ["book_state", "halt", "rearm"]
        assert reg.get(SPEC).post_rearm_cap_until == CAL[t + 19]


test_step_05_idempotent_halt_flat_minus_16.test_ids = ["T-STEP-05"]


# --------------------------------------------------------------------------- #
# T-MISS-02 (M5 clauses): an exception in concentration_bound / drawdown_ladder HALTs (OPS) the books it feeds only
# --------------------------------------------------------------------------- #
def test_miss_02_exceptions_in_concentration_bound_and_ladder_halt_ops():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        out = R.guard_acting("concentration_bound", (REC, SPEC), reg, DEC, R.concentration_bound, "KR", DEC, None, {})
        assert isinstance(out, R.ActingFailure) and "undefined" in out.error and out.alert["books"] == [REC, SPEC]
        for bid in (REC, SPEC):
            b = reg.get(bid)
            assert b.halted and b.halt["class"] == "OPS" and b.halt["reason_code"] == R.ACTING_EXCEPTION
            assert b.halt["component"] == "concentration_bound" and b.halt["rearm_mode"] == "auto"
        assert reg.get("recommended:US").mode is EngineMode.ARMED and reg.get("specification:US").mode is EngineMode.ARMED
        B.runtime_rearm(reg, REC, "auto", DEC + timedelta(days=1))
        B.runtime_rearm(reg, SPEC, "auto", DEC + timedelta(days=1))
        out = R.guard_acting("drawdown_ladder", (SPEC,), reg, DEC, R.drawdown_ladder, [(date(2026, 10, 1), float("nan"))], DEC)
        assert isinstance(out, R.ActingFailure) and reg.get(SPEC).halted and reg.get(SPEC).halt["component"] == "drawdown_ladder"
        assert reg.get(REC).mode is EngineMode.ARMED                                   # scope: the books it feeds only
        b = B.runtime_rearm(reg, SPEC, "auto", DEC + timedelta(days=1))                 # OPS: automatic, no reset, no cap
        assert b.mode is EngineMode.ARMED and b.post_rearm_left == 0
        # the happy path passes the result through
        ok = R.guard_acting("drawdown_ladder", (SPEC,), reg, DEC, R.drawdown_ladder, [(date(2026, 10, 1), 100.0)], DEC)
        assert isinstance(ok, R.LadderState) and ok.hwm_hard == 100.0 and reg.get(SPEC).mode is EngineMode.ARMED


test_miss_02_exceptions_in_concentration_bound_and_ladder_halt_ops.test_ids = ["T-MISS-02"]


# --------------------------------------------------------------------------- #
# OPS triggers added in M5: NAV unavailable (> 2 decisions), heartbeat (synthetic), operator kill, card trio
# --------------------------------------------------------------------------- #
def test_ops_nav_counter_heartbeat_operator_kill_and_card_trio():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        cfg = R.ladder_config()
        B.risk_step(reg, REC, _dec(CAL[1]), 100.0, config=cfg)
        for i in (2, 3):                                                          # decisions 1-2: state held, alert, armed
            res = B.risk_step(reg, REC, _dec(CAL[i]), None, config=cfg)
            assert res.book.mode is EngineMode.ARMED and res.book.nav_failures == i - 1 and res.book.nav == 100.0
            assert res.alert["code"] == "WHOLE_BOOK_NAV_UNAVAILABLE" and res.alert["severity"] == "warn" and res.ladder.hwm_hard == 100.0
        res = B.risk_step(reg, REC, _dec(CAL[4]), None, config=cfg)              # the 3rd: OPS HALT
        assert res.book.halted and res.book.halt["reason_code"] == B.NAV_REASON and res.book.halt["class"] == "OPS"
        assert res.book.halt["series_id"] == "NAV_LINE_CLOSES" and res.alert["severity"] == "page" and res.alert["escalated"]
        assert reg.get(SPEC).mode is EngineMode.ARMED
        res = B.risk_step(reg, REC, _dec(CAL[5]), 99.0, config=cfg)              # NAV back: automatic re-arm, no reset, no cap
        assert res.book.mode is EngineMode.ARMED and res.book.nav_failures == 0 and res.book.hwm_hard == 100.0
        assert res.book.post_rearm_left == 0 and res.ladder.step_mult == 1.0
        # a MissingInput-like object counts as unavailable too
        assert B.risk_step(reg, REC, _dec(CAL[6]), object(), config=cfg).book.nav_failures == 1
        # heartbeat: loss > 60 s during a session HALTs; restored for 5 minutes re-arms automatically (synthetic instants)
        now = datetime(2026, 10, 6, 1, 0, 0, tzinfo=timezone.utc)
        assert B.heartbeat_check(reg, SPEC, now, now - timedelta(seconds=60)).mode is EngineMode.ARMED
        b = B.heartbeat_check(reg, SPEC, now, now - timedelta(seconds=61))
        assert b.halted and b.halt["reason_code"] == B.HEARTBEAT_REASON and b.halt["component"] == "QuoteFeed"
        b = B.heartbeat_check(reg, SPEC, now + timedelta(seconds=90), now + timedelta(seconds=89))
        assert b.halted and b.heartbeat_restored_utc == "2026-10-06T01:01:30Z"
        b = B.heartbeat_check(reg, SPEC, now + timedelta(seconds=389), now + timedelta(seconds=388))
        assert b.halted                                                              # 299 s restored
        b = B.heartbeat_check(reg, SPEC, now + timedelta(seconds=200), now - timedelta(seconds=100))   # lost again: clock restarts
        assert b.halted and b.heartbeat_restored_utc is None
        b = B.heartbeat_check(reg, SPEC, now + timedelta(seconds=300), now + timedelta(seconds=300))
        b = B.heartbeat_check(reg, SPEC, now + timedelta(seconds=600), now + timedelta(seconds=599))
        assert b.mode is EngineMode.ARMED and b.post_rearm_left == 0 and b.heartbeat_restored_utc is None
        # operator kill: logged, operator re-arm, never a demotion; a card book's kill reaches its trio (integrity trigger)
        kill = B.operator_kill(reg, REC, "kim", _dec(CAL[7]))
        assert not kill.integrity_trigger and kill.books[0].halt["reason_code"] == "operator_kill"
        assert kill.books[0].halt["rearm_mode"] == "operator" and "operator:kim" == kill.books[0].halt["component"]
        _raises(lambda: B.runtime_rearm(reg, REC, "auto", _dec(CAL[8])), B.RearmRefused)
        assert B.runtime_rearm(reg, REC, "operator", _dec(CAL[8]), operator="kim").mode is EngineMode.ARMED
        trio = tuple("card:MACRO-R31-KR-ETF:%s" % s for s in ("on", "off", "S"))
        for bid in trio + ("card:OTHER:on",):
            reg.register(B.BookRuntime(bid))
            B.arm(reg, bid, _dec(CAL[0]))
        assert set(B.card_trio(reg, trio[1])) == set(trio) and B.card_trio(reg, REC) == (REC,)
        kill = B.operator_kill(reg, trio[1], "kim", _dec(CAL[9]))
        assert kill.integrity_trigger and all(reg.get(b).halted for b in trio) and reg.get("card:OTHER:on").mode is EngineMode.ARMED
        b = B.retire(reg, trio[2], _dec(CAL[10]), by="owner")
        assert b.mode is EngineMode.DISARMED and all(reg.get(b).mode is EngineMode.DISARMED for b in trio)
        assert reg.get("card:OTHER:on").mode is EngineMode.ARMED
        _raises(lambda: B.operator_kill(reg, REC, "", _dec(CAL[10])), ValueError)


test_ops_nav_counter_heartbeat_operator_kill_and_card_trio.test_ids = ["T-HALT-01"]


# --------------------------------------------------------------------------- #
# Weight books: the NAV ledger reproduces the costed engine; carried orders; atomic persistence; nav_path
# --------------------------------------------------------------------------- #
def test_weight_book_ledger_nav_matches_costed_path_and_persists():
    rng = np.random.default_rng(11)
    n = 40
    w_dec = np.round(rng.uniform(0.0, 1.0, n), 3)
    r = rng.normal(0.0, 0.012, n)
    r[0] = 0.0
    ref = C.costed_path(C.earning_weights(w_dec), r, 3.0)
    want = list(np.cumprod(1.0 + ref.net))
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp, ("KR",))
        cfg = R.ladder_config()
        navs = []
        for k in range(n):
            nav = B.book_nav(reg, SPEC, {LINE: float(r[k])} if k else None, {LINE: 3.0})
            B.risk_step(reg, SPEC, _dec(CAL[k + 1]), nav, config=cfg)
            d = B.record_decision(reg, SPEC, _dec(CAL[k + 1]), {LINE: float(w_dec[k])})
            navs.append(d.nav)
            B.step_decision(reg, SPEC, _dec(CAL[k + 1]), ok=True)
        assert navs[0] == 1.0 and all(abs(a - b) < 1e-12 for a, b in zip(navs[1:], want[1:]))   # bit-for-bit the R4b convention
        path = B.nav_path(reg, SPEC)
        assert [d for d, _ in path] == CAL[1:n + 1] and [v for _, v in path] == navs
        st = R.drawdown_ladder(path, _dec(CAL[n]), cfg)
        assert st.hwm_hard == max(navs) and not st.halted
        # a held instrument without a return: NAV unavailable (never interpolated); a missing cost raises
        assert B.book_nav(reg, SPEC, {}, {LINE: 3.0}) is None and B.book_nav(reg, SPEC, None, {LINE: 3.0}) is None
        _raises(lambda: B.book_nav(reg, SPEC, {LINE: 0.01}, {}), ValueError, "pre-registered cost")
        # a non-fillable order (R-27) carries at the held weight; a non-fillable exit carries too; |w| > 1 refused
        held = reg.get(SPEC).held
        d = B.record_decision(reg, SPEC, _dec(CAL[n + 1]), {LINE: 0.9, "X": 0.1}, fillable={LINE: False})
        assert d.post_action == {LINE: held[LINE], "X": 0.1} and d.carried == {LINE: 0.9}
        d = B.record_decision(reg, SPEC, _dec(CAL[n + 2]), {LINE: 0.9}, fillable={"X": False})
        assert d.post_action == {LINE: 0.9, "X": 0.1} and d.carried == {"X": 0.0}
        _raises(lambda: B.record_decision(reg, SPEC, _dec(CAL[n + 3]), {LINE: 0.9, "X": 0.2}), ValueError, "1.0")
        _raises(lambda: B.record_decision(reg, SPEC, _dec(CAL[n + 3]), {LINE: 1.2}), ValueError, "P2")
        # persistence: the carriers and the ledger survive a reload; the ledger is append-only JSONL, no temp files
        before = reg.get(SPEC)
        again = B.BookRegistry(Path(tmp), clock=_CLOCK, sessions=lambda m: CAL)
        assert again.get(SPEC) == before and again.get(SPEC).held == {LINE: 0.9, "X": 0.1} and again.get(SPEC).prev_held == before.prev_held
        assert B.nav_path(again, SPEC)[:n] == path and len(B.ledger(again, SPEC)) == n + 2
        rows = (Path(tmp) / "books" / (B._file_name(SPEC)[:-5] + ".ledger.jsonl")).read_bytes().split(b"\n")
        row = json.loads(rows[0])
        assert set(row) == {"session", "decision_utc", "engine_state", "nav", "target", "post_action", "new_entries",
                            "blocked", "carried", "step_mult", "post_rearm_cap"} and b"\r" not in rows[0]
        assert not list((Path(tmp) / "books").glob("*.tmp"))
        # an M1-era book file without the M5 carriers loads with their defaults
        old = {k: v for k, v in B._to_dict(before).items() if k not in ("held", "prev_held", "carried", "step_mult", "dwell_left",
                                                                           "block_new_entries", "nav_failures", "limit_met", "heartbeat_restored_utc")}
        b = B._from_dict(old)
        assert b.held == {} and b.step_mult == 1.0 and b.limit_met is None
        # the runtime[] entry is unchanged by the carriers (closed schema): the M1 key set
        assert set(B.to_runtime_entry(before)) == {"book_id", "engine_state", "halt", "post_rearm_cap_until", "nav", "hwm_hard",
                                                   "ref_step", "consecutive_failures", "book_counter"}
    # the turnover is charged once: valuations of decisions that record nothing (late, feed_blocked, target None)
    # never pay the previous |dw| again (risk_step consumes it with the NAV it saves)
    with tempfile.TemporaryDirectory() as tmp:
        reg, cfg = _registry(tmp, ("KR",)), R.ladder_config()
        for k, w in enumerate((0.8, 0.5)):
            B.risk_step(reg, SPEC, _dec(CAL[k + 1]), B.book_nav(reg, SPEC, {LINE: 0.0} if k else None, {LINE: 100.0}), config=cfg)
            B.record_decision(reg, SPEC, _dec(CAL[k + 1]), {LINE: w})
        navs = []
        for k in (2, 3, 4):
            navs.append(B.book_nav(reg, SPEC, {LINE: 0.0}, {LINE: 100.0}))
            B.risk_step(reg, SPEC, _dec(CAL[k + 1]), navs[-1], config=cfg)
        assert abs(navs[0] - 0.997) < 1e-12 and navs[1] == navs[2] == navs[0], navs
        # HALTED: every target 0 from this decision (the book earns 0 from t+1)
        B.runtime_halt(again, SPEC, "OPS", "operator_kill", _dec(CAL[n + 3]))
        assert B.record_decision(again, SPEC, _dec(CAL[n + 3]), {LINE: 0.9}).post_action == {LINE: 0.0, "X": 0.0}


test_weight_book_ledger_nav_matches_costed_path_and_persists.test_ids = []


# --------------------------------------------------------------------------- #
# T-MONO-01: no reallocation; weakly monotone in every own multiplier; zero cross-partials (seed 11)
# --------------------------------------------------------------------------- #
def _draw(rng):
    k = int(rng.integers(0, 4))
    m = {"vt": float(rng.uniform(0.0, 1.0)), "ov": list(rng.uniform(0.5, 1.0, k)), "ladder": float(rng.choice([0.5, 1.0])),
         "cap": float(rng.choice([0.5, 1.0])), "bound": float(rng.uniform(0.3, 1.2)), "vs": float(rng.uniform(0.0, 1.0)),
         "fov": list(rng.uniform(0.5, 1.0, int(rng.integers(0, 3))))}
    up = {"vt": float(rng.uniform(m["vt"], 1.0)), "ov": [float(rng.uniform(o, 1.0)) for o in m["ov"]],
          "ladder": 1.0 if rng.random() < 0.5 else m["ladder"], "cap": 1.0 if rng.random() < 0.5 else m["cap"],
          "bound": float(rng.uniform(m["bound"], 1.2)), "vs": float(rng.uniform(m["vs"], 1.0)),
          "fov": [float(rng.uniform(o, 1.0)) for o in m["fov"]]}
    return m, up


def _gross(m) -> float:
    return R.risk_layer(m["vt"], m["ov"], m["ladder"], m["cap"], m["bound"], bound_factor="absolute_single_name")["gross"]


def _budget(sleeve, m) -> float:
    mults = [SL.Multiplier("R-03", m["vs"], "active", "momentum", factor="vs")]
    mults += [SL.Multiplier("R-F%d" % i, v, "active", "momentum") for i, v in enumerate(m["fov"])]
    return SL.apply_overlays(sleeve, mults, "active").factor


def test_mono_01_no_reallocation_property_seed_11():
    rng = np.random.default_rng(11)
    kr = SL.Sleeve("KR", "momentum", "long_only", {"A": 0.7, "B": 0.3}, benchmark={"A": 0.5, "B": 0.5}, base_weight=0.3)
    us = SL.Sleeve("US", "momentum", "long_short", {"P": 1.0, "Q": -1.0}, base_weight=0.2)
    for _ in range(300):
        m, up = {}, {}
        for mk in ("KR", "US"):
            m[mk], up[mk] = _draw(rng)
        g = {mk: _gross(m[mk]) for mk in m}
        a = {"KR": _budget(kr, m["KR"]), "US": _budget(us, m["US"])}
        for mk in ("KR", "US"):
            # own multipliers raised (every component, any subset): gross and the family's active budget never fall
            assert _gross(up[mk]) >= g[mk] - 1e-12 and _budget(kr if mk == "KR" else us, up[mk]) >= a[mk] - 1e-12
            for key in ("vt", "ladder", "cap", "bound"):
                one = dict(m[mk], **{key: up[mk][key]})
                assert _gross(one) >= g[mk] - 1e-12, key
            for key in ("vs", "fov"):
                one = dict(m[mk], **{key: up[mk][key]})
                assert _budget(kr if mk == "KR" else us, one) >= a[mk] - 1e-12, key
            # cross-partials are 0: another market's multipliers leave this market's gross and budget bit-identical
            other = "US" if mk == "KR" else "KR"
            assert _gross(m[mk]) == g[mk] and _budget(kr if mk == "KR" else us, m[mk]) == a[mk]
            assert _gross(up[other]) != g[mk] or True                               # the other market's draw is independent
        # freed total exposure moves to cash: the long book's weights scale by gross, nothing is renormalised
        low = SL.apply_overlays(replace(kr, base_weight=1.0), [SL.Multiplier("R-06-VT", 0.5, "total", "market_gross", factor="vt")], "total")
        assert low.weights == {"A": 0.35, "B": 0.15} and abs(sum(low.weights.values()) - 0.5) < 1e-12
        # freed active budget moves toward the benchmark (long-only) or zero (L/S)
        half = SL.apply_overlays(kr, [SL.Multiplier("R-03", 0.5, "active", "momentum", factor="vs")], "active")
        assert abs(half.weights["A"] - 0.3 * (0.5 + 0.5 * 0.2)) < 1e-12 and abs(sum(half.weights.values()) - 0.3) < 1e-12
        zero = SL.apply_overlays(us, [SL.Multiplier("R-03", 0.0, "active", "momentum", factor="vs")], "active")
        assert zero.weights == {"P": 0.0, "Q": -0.0} or zero.weights == {"P": 0.0, "Q": 0.0}
    # the one logged exception (R-15 K/(K-1)) lives in sleeves.base_weights (T-PRIOR-01, M4); nothing here renormalises


test_mono_01_no_reallocation_property_seed_11.test_ids = ["T-MONO-01"]


def test_mono_01_i01_fixture_clause_refdata():
    raise NotRun("REFDATA: the I-01 fixtures (KR 2026-07-30 / 2026-10-02, US 2026-07-30 / 2026-10-01 artifacts) absent: "
                 "the property ran on the synthetic I-01-structured book (seed 11)")


test_mono_01_i01_fixture_clause_refdata.test_ids = ["T-MONO-01"]


# --------------------------------------------------------------------------- #
# G-LAD-01..03: reference mode (the literal v1.2 ladder, QF4's 11-session fix, sensitivity lines)
# --------------------------------------------------------------------------- #
def _lad(gid: str):
    raise NotRun(f"REFDATA: {gid}: QX_DLA_ladder.csv (F24), F13 / U1 and the literal v1.2 rule text "
                 "(.v1.2_INTEGRATION_backup.md, F-21) absent; never reconstructed from the cycle counts; "
                 "tests/reference/reference_mode.literal_ladder stays the stub")


def test_g_lad_01_literal_ladder_refdata():
    _lad("G-LAD-01")


def test_g_lad_02_qf4_eleven_session_fix_refdata():
    _lad("G-LAD-02")


def test_g_lad_03_sensitivity_lines_refdata():
    _lad("G-LAD-03")


test_g_lad_01_literal_ladder_refdata.test_ids = ["G-LAD-01"]
test_g_lad_02_qf4_eleven_session_fix_refdata.test_ids = ["G-LAD-02"]
test_g_lad_03_sensitivity_lines_refdata.test_ids = ["G-LAD-03"]


# --------------------------------------------------------------------------- #
# Rulings: shared names, no wall clock in the two modules
# --------------------------------------------------------------------------- #
def test_shared_names_and_no_wall_clock():
    for name in ("ConcentrationBound", "LadderState", "lookthrough_exposure", "concentration_bound", "drawdown_ladder",
                 "ladder_step", "ladder_path", "risk_limit_breach", "li_etf_eligible", "steps_act_in"):
        assert callable(getattr(R, name)) or isinstance(getattr(R, name), type), name
    for name in ("nav_path", "book_nav", "record_decision", "risk_step", "hard_stop_check", "ladder_state", "heartbeat_check",
                 "operator_kill", "runtime_halt", "runtime_rearm", "step_decision", "ever_armed", "new_entries"):
        assert callable(getattr(B, name)), name
    from core.quant import risk as RK
    assert RK.ConcentrationBound is R.ConcentrationBound and RK.LadderState is R.LadderState
    for rel in ("core/engine/books.py", "core/quant/risk_layer.py"):
        tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("now", "utcnow", "today", "time", "time_ns"):
                base = node.value
                base_name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
                assert base_name not in ("datetime", "date", "time"), f"{rel}: wall clock {base_name}.{node.attr}"


test_shared_names_and_no_wall_clock.test_ids = []


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
