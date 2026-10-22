"""M2 package A tests: the risk layer (core/quant/risk_layer.py; TASK-M2-01..05).

Spec tests: T-CAP-02 (stack-card clause M7), T-CAP-01 ("cannot emit 0" clause), T-VT-01, T-LABEL-01, T-HEDGE-01,
T-CORR-01, T-ROLE-01 / T-ROLE-02 / T-MISS-02 (M2 clauses), T-LAG-02 (vt clause), I-02, G-KR-01..04 / 02b / 02c,
G-KR-06, G-US-01 / 01b / 01c. Every golden that needs absent reference data raises NotRun("REFDATA: <file>").

Hermetic: every PIT store and book registry lives in a tempfile directory; the calendars are the M1 StubClocks;
every instant is pinned; no module global is patched.
"""
from __future__ import annotations

import json
import math
import tempfile
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from core.engine import books as B
from core.engine.state import EngineMode
from core.ficc import contracts as C
from core.ficc import lag_audit as L
from core.ficc import pit as P
from core.quant import risk_layer as R
from core.rules import macro_rules as MR
from tests.macro_m1_fixtures import _refdata
from tests.macro_m1_pit import CLK, REG, StubClocks, U, _raises
from tests.notrun import NotRun

UTC = timezone.utc
OCT2 = date(2026, 10, 2)
DECISION = U(2026, 10, 2, 6, 30, 30)          # close_print_bound_utc(KR, 2026-10-02)
KNOWLEDGE = U(2026, 10, 2, 7, 0)
SCHEMA = json.loads((Path(__file__).resolve().parents[1] / "core" / "ficc" / "schemas" / "macro_state.v2.0.json").read_text(encoding="utf-8"))
INPUT_KEYS = set(SCHEMA["$defs"]["input"]["required"]) | set(SCHEMA["$defs"]["input"]["properties"])


# --------------------------------------------------------------------------- #
# Store builders
# --------------------------------------------------------------------------- #
def _tmp(prefix="m2risk_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))


def _store(clocks=CLK) -> P.PITStore:
    return P.PITStore(_tmp() / "store", registry=REG, clocks=clocks)


def _sessions(market: str, end: date, n: int, clocks=CLK) -> list[date]:
    """The last `n` sessions of `market` ending at `end` (ascending)."""
    out, d = [], end
    while len(out) < n:
        if clocks.is_session(market, d):
            out.append(d)
        d -= timedelta(days=1)
    return out[::-1]


def _close_row(sid: str, d: date, value: float, *, market: str, source="KRX", status="official_close", clocks=CLK,
               available=None, retrieved=None, obs_date=None, session=None) -> dict:
    bound = clocks.close_print_bound_utc(market, d)
    return P.make_row(series_id=sid, value=float(value), obs_date=obs_date or d, session_date=session or obs_date or d,
                      obs_utc=bound, obs_kind="close", value_status=status, available_at_utc=available or bound,
                      available_at_source="calendar_bound", retrieved_at_utc=retrieved or bound + timedelta(minutes=11),
                      vintage=None, source=source, channel=None, provider_mode="explicit", synthetic=False)


def _gbm(n: int, seed: int, start=2500.0, mu=0.0003, sigma=0.012) -> list[float]:
    """n + 1 prices: `start` followed by n seeded simple returns."""
    r = np.random.default_rng(seed).normal(mu, sigma, size=n)
    return list(start * np.cumprod(np.concatenate([[1.0], 1.0 + r])))


def _kospi_store(n_closes: int, *, seed=11, end=OCT2, scale_sigma_to: float | None = None) -> tuple[P.PITStore, list[date], list[float]]:
    """A KR store of `n_closes` official KOSPI closes ending at `end`; optionally rescaled so that the SMA20 of the
    last 20 simple returns equals `scale_sigma_to` (annualised)."""
    days = _sessions("KR", end, n_closes)
    px = _gbm(n_closes - 1, seed)
    if scale_sigma_to is not None and n_closes >= 21:
        r = np.array(px[1:]) / np.array(px[:-1]) - 1.0
        tail = r[-20:]
        r[-20:] = tail * (scale_sigma_to / math.sqrt(252) / np.std(tail, ddof=1))
        px = list(px[0] * np.cumprod(np.concatenate([[1.0], 1.0 + r])))
    store = _store()
    store.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR") for d, v in zip(days, px)])
    return store, days, px


def _vt(store, *, armed=False, decision=DECISION, knowledge=KNOWLEDGE, **kw):
    return R.market_vol_target(store, REG, CLK, "KR", decision, knowledge, book_ever_armed=armed, **kw)


def _registry(tmp) -> B.BookRegistry:
    cal = [d for d in (date(2026, 9, 1) + timedelta(days=i) for i in range(90)) if d.weekday() < 5]
    reg = B.BookRegistry(Path(tmp), clock=lambda: U(2026, 10, 2, 7), sessions=lambda m: cal)
    B.create_default_books(reg, ["KR", "US"])
    for bid in reg.ids():
        B.arm(reg, bid, U(2026, 9, 1, 6, 30, 30))
    return reg


# --------------------------------------------------------------------------- #
# T-CAP-02 / T-CAP-01: composition by min(), the floor, the binding log, the product path
# --------------------------------------------------------------------------- #
def test_cap_02_min_composition_10000_seeded_draws():
    rng = np.random.default_rng(11)
    checked = 0
    for i in range(10_000):
        k = int(rng.integers(0, 6))
        overlays = list(rng.uniform(0.5, 1.0, size=k))
        vt = float(rng.uniform(0.0, 1.0))
        if i % 7 == 0 and k:                                   # force the endpoints explicitly (L5627)
            overlays[0] = 0.5
        if i % 11 == 0 and k:
            overlays[-1] = 1.0
        if i % 13 == 0:
            vt = 0.0
        if i % 17 == 0:
            vt = 1.0
        ladder = 1.0 if rng.random() < 0.5 else 0.5
        cap = 1.0 if rng.random() < 0.5 else 0.5
        composed = R.compose(vt, overlays, ladder, cap)
        assert composed == vt * min([1.0] + overlays + [ladder, cap])
        assert composed >= 0.5 * vt and 0.0 <= composed <= 1.0
        checked += 1
    assert checked == 10_000
    # 0.75 and 0.5 compose to 0.5, never 0.375; the binding factor is logged (F-9, F-10)
    d = R.compose_detail(1.0, {"R-31": 0.75, "R-28": 0.5}, 1.0, 1.0)
    assert d.composed == 0.5 and d.overlay_min == 0.5 and d.binding == ("R-28",) and "R-28" in d.reasons[0]
    assert R.compose(1.0, [0.75, 0.5], 1.0, 1.0) == 0.5 != 0.375
    assert R.compose(1.0, [], 1.0, 1.0) == 1.0 and R.compose_detail(0.7, [], 1.0, 1.0).binding == ()
    tie = R.compose_detail(0.9, {"a": 0.5}, 0.5, 1.0)
    assert tie.binding == ("a", "ladder") and tie.composed == 0.45
    assert R.compose_detail(1.0, [0.9], 1.0, 0.5).binding == ("post_rearm_cap",)
    # a product-composed path raises; bounds_ok recomputes from the recorded factors (L881)
    _raises(lambda: R.compose(1.0, [0.75, 0.5], 1.0, 1.0, combine="product"), R.CompositionError, "product")
    _raises(lambda: R.verify_composition(1.0, [0.75, 0.5], 1.0, 1.0, 0.375), R.CompositionError, "product")
    R.verify_composition(1.0, [0.75, 0.5], 1.0, 1.0, 0.5)
    _raises(lambda: R.verify_composition(1.0, [0.75], 1.0, 1.0, None), R.CompositionError, "no composed")
    # every out-of-bound argument raises (R-02 rule 1): overlays [0.5, 1], vt [0, 1], ladder / cap in {1.0, 0.5}
    for bad in (lambda: R.compose(1.0, [0.4], 1.0, 1.0), lambda: R.compose(1.0, [1.1], 1.0, 1.0),
                lambda: R.compose(1.2, [], 1.0, 1.0), lambda: R.compose(-0.1, [], 1.0, 1.0),
                lambda: R.compose(1.0, [], 0.7, 1.0), lambda: R.compose(1.0, [], 1.0, 0.0),
                lambda: R.compose(float("nan"), [], 1.0, 1.0), lambda: R.compose(1.0, [float("inf")], 1.0, 1.0),
                lambda: R.compose(1.0, [0.75, 0.5], 1.0, 1.0, combine="sum")):
        _raises(bad, R.CompositionError)
    assert issubclass(R.CompositionError, ValueError)
    # the floor is on composed: a concentration bound may take gross lower without a bounds failure (L881)
    line = R.risk_layer(0.694, {"R-31": 1.0}, 1.0, 1.0, 0.3, bound_factor="active_single_name")
    assert line == {"composed": 0.694, "gross": 0.3, "binding_factor": "active_single_name"}
    assert line["gross"] < 0.5 * 0.694


test_cap_02_min_composition_10000_seeded_draws.test_ids = ["T-CAP-02"]


def test_cap_02_stack_card_clause_refdata():
    raise NotRun("REFDATA: F13 yahoo_KS11_1996-12_2026-10-02.csv absent: the stack card's share of days at <= 0.25x total "
                 "exposure (31.0%) and rebound capture (11.2%) are M7 clauses on KOSPI history (section 9.0b)")


test_cap_02_stack_card_clause_refdata.test_ids = ["T-CAP-02"]


def test_cap_01_overlay_layer_cannot_emit_zero():
    """0x exists only in the risk layer and in HALTED (R-02 rule 4): the overlay layer refuses 0 and anything below 0.5."""
    for zero in (0.0, 0.25, 0.49, -1.0):
        _raises(lambda z=zero: R.compose(1.0, [z], 1.0, 1.0), R.CompositionError, "overlay")
        _raises(lambda z=zero: MR.assert_overlay(z), ValueError, "overlay")
    _raises(lambda: R.compose(1.0, [], 0.0, 1.0), R.CompositionError)
    _raises(lambda: R.compose(1.0, [], 1.0, 0.0), R.CompositionError)
    assert R.risk_layer(1.0, [0.5], 0.5, 0.5, halted=True) == {"composed": 0.0, "gross": 0.0, "binding_factor": "none"}
    assert R.risk_layer(0.0, [0.5], 1.0, 1.0)["composed"] == 0.0                 # vt = 0 is the risk layer, not an overlay
    bound = R.ConcentrationBound(0.755, 0.685, None, None, 0.685, "active_single_name")
    assert R.risk_layer(0.694, [], 1.0, 1.0, bound) == {"composed": 0.694, "gross": 0.685, "binding_factor": "active_single_name"}
    assert R.risk_layer(1.0, [], 0.5, 1.0, bound) == {"composed": 0.5, "gross": 0.5, "binding_factor": "none"}
    _raises(lambda: R.risk_layer(1.0, [], 1.0, 1.0, 0.6), ValueError, "binding_factor")
    _raises(lambda: R.risk_layer(1.0, [], 1.0, 1.0, 0.6, bound_factor="pair"), ValueError, "binding_factor")


test_cap_01_overlay_layer_cannot_emit_zero.test_ids = ["T-CAP-01"]


# --------------------------------------------------------------------------- #
# T-VT-01: estimator, warm-up, stale carry, degenerate sigma, ARMED mapping
# --------------------------------------------------------------------------- #
def test_vt_01_sma20_simple_returns_ddof1_and_the_formula():
    store, days, px = _kospi_store(40, scale_sigma_to=0.2882)
    res = _vt(store)
    assert isinstance(res, R.VTResult) and res.status == "ok" and res.n_valid_returns == 20
    r = np.array(px[1:]) / np.array(px[:-1]) - 1.0                                 # simple returns, ddof 1
    want = float(np.std(r[-20:], ddof=1)) * math.sqrt(252)
    assert abs(res.sigma_ann - want) < 1e-12 and abs(res.sigma_ann - 0.2882) < 1e-9
    assert abs(res.weight - min(1.0, 0.20 / 0.2882)) < 1e-12 and abs(res.weight - 0.694) < 0.002   # L5673 identity
    assert res.market == "KR" and res.estimator == "sma20" and res.target_ann == 0.20 and res.exposure_basis == "total"
    assert res.series_id == "KOSPI_OFFICIAL_CLOSE" and res.books == ("specification:KR",)
    assert R.sma_vol(r[-20:]) == want and R.sma_vol(r[-25:]) == want and R.sma_vol(r[-19:]) is None
    log_want = float(np.std(np.diff(np.log(px[-21:])), ddof=1)) * math.sqrt(252)
    assert abs(log_want - want) > 1e-9, "log and simple returns differ: the vt uses simple returns"
    assert res.display_label_rel is None and res.display_label_abs is None and "rel:" in res.label_status
    assert [i["name"] for i in res.inputs] == ["close_t", "close_window_start"]
    assert set(res.inputs[0]) == INPUT_KEYS and res.inputs[0]["obs_date"] == "2026-10-02" and res.inputs[0]["status"] == "ok"
    assert res.inputs[0]["books"] == ["specification:KR"] and res.inputs[1]["obs_date"] == days[-21].isoformat()
    # cap 1.0 permanent, no floor: a calm market caps at 1.0, a wild one goes well below 0.5
    calm, _, _ = _kospi_store(40, scale_sigma_to=0.10)
    assert _vt(calm).weight == 1.0
    wild, _, _ = _kospi_store(40, scale_sigma_to=0.80)
    assert abs(_vt(wild).weight - 0.25) < 1e-9
    # ewma_vol exists for the M3 race only; the acting estimator is sma20 (section 10 item 25)
    assert R.ewma_vol(r, 0.94) is not None and R.ewma_vol(r[:10], 0.94) is None and R.ewma_vol(r, 1.0) is None
    from core.quant import vol_estimators as VE                      # one EWMA: the value the M3 race grades
    for lam in (0.94, 0.97):
        assert R.ewma_vol(r, lam) == math.sqrt(VE.ewma(np.asarray(r, dtype=float), 1, lam).var[-1] * 252)
    _raises(lambda: _vt(store, estimator="ewma094"), ValueError, "R-30")
    # the decision instant must be the close-print bound of a session (time.decision_instant)
    _raises(lambda: _vt(store, decision=U(2026, 10, 2, 6, 30, 0)), ValueError, "close_print_bound")
    _raises(lambda: _vt(store, decision=U(2026, 10, 3, 6, 30, 30), knowledge=U(2026, 10, 3, 7)), ValueError, "session")
    # other markets must pre-register a target; no default is invented (F-7)
    _raises(lambda: R.market_vol_target(store, REG, CLK, "JP", U(2026, 10, 2, 6, 30), KNOWLEDGE), ValueError, "pre-register")
    rules = json.loads(json.dumps({"vol_target": MR.load_store().get("vol_target")}))
    rules["vol_target"]["KR"]["cap"] = 1.5
    _raises(lambda: _vt(store, rules=rules), ValueError, "permanent")


test_vt_01_sma20_simple_returns_ddof1_and_the_formula.test_ids = ["T-VT-01"]


def test_vt_01_warmup_stale_carry_degenerate_and_armed_mapping():
    # (a) fewer than 20 valid returns -> insufficient_history; before the first ARMED decision 1.0 "warmup", no failure
    short, _, _ = _kospi_store(16)                                                  # 15 returns
    res = _vt(short)
    assert isinstance(res, R.VTResult) and res.status == "insufficient_history" and res.sigma_ann is None and res.weight is None
    assert res.n_valid_returns == 15 and res.display_label_rel is None and "insufficient_history" in res.label_status
    bv = R.vt_for_book(res, "specification:KR", ever_armed=False)
    assert bv == R.BookVT("specification:KR", 1.0, "warmup", False, None)
    # (d) on a book that has been ARMED the same store is MissingInput("missing"): never weight 1.0
    bv = R.vt_for_book(res, "specification:KR", ever_armed=True, prev_weight=0.61)
    assert bv.vt_status == "fail_closed" and bv.fail_closed and bv.weight == 0.61 and bv.missing.reason == "missing"
    miss = _vt(short, armed=True)
    assert isinstance(miss, P.MissingInput) and miss.reason == "missing" and miss.books == ("specification",)
    act = C.on_input_failure(miss.series_id, miss, REG.resolve_binding(miss.series_id, "R-06"))
    assert act.fail_closed and act.alert and act.counts and act.halt == "bound_books"                # counts toward the HALT limit
    assert R.vt_for_book(miss, "specification:KR", ever_armed=True, prev_weight=0.61).weight == 0.61
    assert R.vt_for_book(miss, "specification:KR", ever_armed=False).fail_closed                     # cannot ARM (F-6)
    # (b) a flagged stale-carry session is excluded and the window extends to the last 20 valid returns (F-2)
    full, days, px = _kospi_store(30)
    skip = days[-5]
    res = _vt(full, stale_carry={skip})
    kept = [v for d, v in zip(days, px) if d != skip]
    r = np.array(kept[1:]) / np.array(kept[:-1]) - 1.0
    assert res.status == "ok" and abs(res.sigma_ann - float(np.std(r[-20:], ddof=1)) * math.sqrt(252)) < 1e-12
    assert res.inputs[1]["obs_date"] == [d for d in days if d != skip][-21].isoformat()
    assert res.sigma_ann != _vt(full).sigma_ann
    # (F-3) an unflagged gap inside the window fails closed; the same gap flagged is skipped
    gap = _store()
    gap.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR") for d, v in zip(days, px) if d != skip])
    bad = _vt(gap)
    assert isinstance(bad, P.MissingInput) and bad.reason == "missing" and skip.isoformat() in bad.detail
    assert _vt(gap, stale_carry={skip}).sigma_ann == res.sigma_ann
    # a gap before the history's first close is warm-up, not a failure
    assert _vt(gap, stale_carry={skip, days[0]}).status == "ok"
    # (c) sigma = 0 with 20 valid returns -> MissingInput("missing") (degenerate), armed or not (F-5, F-6)
    flat = _store()
    flat.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, 3000.0, market="KR") for d in _sessions("KR", OCT2, 25)])
    for armed in (False, True):
        deg = _vt(flat, armed=armed)
        assert isinstance(deg, P.MissingInput) and deg.reason == "missing" and "degenerate" in deg.detail
    # the decided session's close itself missing / provisional is returned unchanged (reason preserved)
    assert _vt(full, knowledge=U(2026, 10, 2, 6, 35)).reason == "missing"
    prov = _store()
    prov.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR") for d, v in zip(days[:-1], px[:-1])])
    prov.append([P.make_row(series_id="KOSPI_OFFICIAL_CLOSE", value=px[-1], obs_date=OCT2, session_date=OCT2, obs_utc=U(2026, 10, 2, 1, 30),
                            obs_kind="quote_snapshot", value_status="provisional_intraday", available_at_utc=U(2026, 10, 2, 1, 30),
                            available_at_source="inferred_from_retrieval", retrieved_at_utc=U(2026, 10, 2, 1, 56), vintage=None,
                            source="Yahoo", channel=None, provider_mode="explicit", synthetic=False)])
    assert _vt(prov).reason == "provisional_intraday"
    # a vendor close sizes a book only in a backtest whose header declares that vendor (section 4.1)
    vend = _store()
    vend.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR", source="Yahoo", status="vendor_close") for d, v in zip(days, px)])
    assert _vt(vend).reason == "provisional_intraday"
    assert _vt(vend, run_mode="backtest", vendor="Yahoo").status == "ok"


test_vt_01_warmup_stale_carry_degenerate_and_armed_mapping.test_ids = ["T-VT-01"]


def test_vt_01_rv20_28_82_and_vt_0_694_on_2_oct_refdata():
    _refdata(["F13"])
    raise NotRun("REFDATA: F13 present but the KRX official-close replay of rv20 28.82% / vt 0.694 is pinned to the frozen "
                 "fixture ingest (G-POST-01 rows); run after docs/macro_fixtures.py has frozen F13")


test_vt_01_rv20_28_82_and_vt_0_694_on_2_oct_refdata.test_ids = ["T-VT-01", "G-POST-01"]


# --------------------------------------------------------------------------- #
# T-LABEL-01: causal display labels
# --------------------------------------------------------------------------- #
def test_label_01_causal_boundary_and_null_safe():
    rng = np.random.default_rng(11)
    sig = list(0.15 + 0.10 * rng.random(2000))
    # relative: the trailing 756 values ending at t, t included; appending future data never changes a past label
    past = [R.display_label_rel(sig[: i + 1]) for i in range(755, 1500)]
    assert all(x in R.LABELS for x in past)
    sig2 = sig + list(2.0 + rng.random(300))                                      # a wild future
    assert [R.display_label_rel(sig2[: i + 1]) for i in range(755, 1500)] == past
    assert R.display_label_rel(sig[:755]) is None and R.display_label_rel(sig[:756]) is not None
    # absolute: the expanding history, from 10 calendar years after the first sigma date
    first = date(2015, 10, 2)
    assert R.display_label_abs(sig, first, date(2025, 10, 1)) is None
    assert R.display_label_abs(sig, first, date(2025, 10, 2)) in R.LABELS
    assert R.display_label_abs(sig[:900], first, OCT2) == R.display_label_abs(sig[:900], first, OCT2)
    assert R.display_label_abs([], first, OCT2) is None and R.display_label_abs(sig, None, OCT2) is None
    hist_a = [R.display_label_abs(sig[: i + 1], first, OCT2) for i in range(100, 400)]
    assert [R.display_label_abs(sig2[: i + 1], first, OCT2) for i in range(100, 400)] == hist_a
    # a value exactly on a quartile boundary takes the higher label (L5643)
    h = [0.10, 0.20, 0.30, 0.40]                                                     # Q1 0.175, Q2 0.25, Q3 0.325 (linear)
    q1, q2, q3 = np.quantile(h, (0.25, 0.5, 0.75))
    assert [R.label_of(x, h) for x in (q1 - 1e-9, q1, q2 - 1e-9, q2, q3 - 1e-9, q3)] == ["calm", "normal", "normal", "elevated", "elevated", "stressed"]
    assert R.label_of(0.0, h) == "calm" and R.label_of(9.0, h) == "stressed"
    # sigma_history is causal and filtered (never smoothed): appending closes changes no earlier sigma
    days = _sessions("KR", OCT2, 120)
    px = _gbm(119, 3)
    hist = R.sigma_history(list(zip(days, px)))
    more = R.sigma_history(list(zip(days + [OCT2 + timedelta(days=4)], px + [px[-1] * 1.3])))
    assert len(hist) == 100 and more[:100] == hist and hist[0][0] == days[20] and hist[-1][0] == OCT2
    assert abs(hist[-1][1] - R.sma_vol(np.array(px[1:]) / np.array(px[:-1]) - 1.0)) < 1e-12
    # through market_vol_target: a 13-year store gives both labels; the function reports why when it cannot
    long_store, ldays, lpx = _kospi_store(13 * 252)
    res = _vt(long_store)
    assert res.display_label_rel in R.LABELS and res.display_label_abs in R.LABELS and res.label_status == "ok"
    values = [s for _, s in R.sigma_history(list(zip(ldays, lpx)))]
    assert res.display_label_rel == R.display_label_rel(values) and res.display_label_abs == R.display_label_abs(values, ldays[20], OCT2)
    assert R.LABEL_METHOD_REL == "trailing756_quartiles_causal_filtered" and R.LABEL_METHOD_ABS == "expanding_full_history_quartiles_causal_filtered"


test_label_01_causal_boundary_and_null_safe.test_ids = ["T-LABEL-01"]


def test_label_01_kospi_elevated_stressed_and_us_normal_refdata():
    _refdata(["F13", "F14"])
    raise NotRun("REFDATA: F13 / F14 present but the 2026-10-02 KOSPI (elevated / stressed; quartiles 15.7 / 18.55 / 33.6%) "
                 "and 2026-10-01 US (normal) label replay runs on the frozen fixture ingest")


test_label_01_kospi_elevated_stressed_and_us_normal_refdata.test_ids = ["T-LABEL-01", "G-POST-01"]


# --------------------------------------------------------------------------- #
# T-CORR-01: date-aligned corr63 vs the series-lag reading
# --------------------------------------------------------------------------- #
def _corr_series_lag(eq: dict, y10: dict, lag: int, window: int = 63) -> float:
    """The v1.2 literal reading (negative control, test only): the 10y leg shifted `lag` observations against
    unshifted equity returns, positional, no date alignment."""
    ed, yd = sorted(eq), sorted(y10)
    r_eq = [eq[b] / eq[a] - 1.0 for a, b in zip(ed, ed[1:])]
    dy = [-(y10[b] - y10[a]) for a, b in zip(yd, yd[1:])]
    n = min(len(r_eq), len(dy) - lag)
    x, y = np.array(r_eq[-n:]), np.array(dy[len(dy) - lag - n: len(dy) - lag])
    x, y = x[-window:], y[-window:]
    return float(np.corrcoef(x, y)[0, 1])


def test_corr_01_date_aligned_pairs_synthetic():
    rng = np.random.default_rng(11)
    us = _sessions("US", date(2026, 9, 30), 140)
    eq_px = list(2500.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, size=140)))
    dy = rng.normal(0.0, 0.05, size=140)
    y_px = list(4.0 + np.cumsum(dy))
    eq = dict(zip(us, eq_px))
    bond_holidays = {date(2026, 10, 12) - timedelta(days=7 * k) for k in range(1, 6)}   # bond-market closures, NYSE open
    y10 = {d: y for d, y in zip(us, y_px) if d not in bond_holidays}
    got = R.corr63(eq, y10, date(2026, 9, 30))
    # independent recomputation: inner join on dates, both changes over the same consecutive joined dates (F-13)
    common = sorted(d for d in eq if d in y10)
    pairs = np.array([(eq[b] / eq[a] - 1.0, -(y10[b] - y10[a])) for a, b in zip(common, common[1:])][-63:])
    want = float(np.corrcoef(pairs[:, 0], pairs[:, 1])[0, 1])
    assert got is not None and abs(got - want) < 1e-12
    # the 10y leg is used only through its last usable date; the statistic, not a leg, is lagged
    assert R.corr63(eq, y10, date(2026, 9, 25)) != got and R.corr63(eq, y10, None) is None
    assert R.corr63(eq, {d: y10[d] for d in list(y10)[-60:]}, date(2026, 9, 30)) is None     # fewer than 63 pairs
    # the series-lag implementation gives a different number and must not be the one used
    lagged = _corr_series_lag(eq, y10, 2)
    assert abs(lagged - got) > 0.02, (lagged, got)
    # a constant leg has no correlation
    assert R.corr63(eq, {d: 4.0 for d in us}, date(2026, 9, 30)) is None


test_corr_01_date_aligned_pairs_synthetic.test_ids = ["T-CORR-01"]


def test_corr_01_plus_0_53_at_2026_09_30_refdata():
    _refdata(["F14", "F18"])
    raise NotRun("REFDATA: F14 yahoo_GSPC_1990_2026-10-01.csv / F18 fred_snapshot_2026-10-02/DGS10.csv present but the "
                 "+0.53 +/- 0.01 replay (series-lag control -0.094) runs on the frozen fixture ingest")


test_corr_01_plus_0_53_at_2026_09_30_refdata.test_ids = ["T-CORR-01"]


# --------------------------------------------------------------------------- #
# T-HEDGE-01 / T-ROLE-01 / T-ROLE-02 / T-MISS-02 (risk-model clauses): the hedge state never HALTs
# --------------------------------------------------------------------------- #
def _hedge_store(*, pce_months=14, pce_last=date(2026, 9, 1), pce_yoy=0.03008, spx_days=140, y10_mode="backtest",
                 usd=True, usd_last=None, eq_1d=None, usd_1d=None, dy_last=None, seed=11, kospi_weeks=0,
                 fx_corr_sign=-1.0) -> P.PITStore:
    rng = np.random.default_rng(seed)
    store = _store()
    retrieved = U(2026, 10, 1, 23, 0)
    # core PCE levels: monthly, first_release vintages, the last YoY pinned to pce_yoy
    months = [P.add_months(pce_last, -i) for i in range(pce_months)][::-1]
    base = {m: 100.0 * (1.003 ** i) for i, m in enumerate(months)}
    base[pce_last] = base[P.add_months(pce_last, -12)] * (1.0 + pce_yoy)
    rows = [P.stamp_release("PCEPILFE", m, base[m], retrieved_at_utc=retrieved, source="ALFRED", registry=REG, clocks=CLK,
                            vintage=P.add_months(m, 1) + timedelta(days=27)) for m in months]
    store.append(rows)
    us = _sessions("US", date(2026, 10, 1), spx_days)
    r = rng.normal(0.0, 0.01, size=spx_days - 1)
    if eq_1d is not None:
        r[-1] = eq_1d
    eq = list(5000.0 * np.cumprod(np.concatenate([[1.0], 1.0 + r])))
    store.append([_close_row("SPX_OFFICIAL_CLOSE", d, v, market="US", source="KIS") for d, v in zip(us, eq)])
    dy = rng.normal(0.0, 0.03, size=spx_days)
    if dy_last is not None:
        dy[-1] = dy_last                                                       # the 1 Oct change (usable live via the KIS quote)
    y = list(4.0 + np.cumsum(dy))
    if y10_mode == "backtest":                                                  # H.15 rows retrieved after they post
        store.append([P.stamp_release("DGS10", d, v, retrieved_at_utc=max(retrieved, CLK.publication_instant("DGS10", d) + timedelta(minutes=5)),
                                      source="FRED", registry=REG, clocks=CLK) for d, v in zip(us, y)])
    else:
        store.append([P.stamp_quote("US10Y_KIS_QUOTE", d, v, quote_utc=CLK.close_print_bound_utc("US", d) - timedelta(minutes=1),
                                    retrieved_at_utc=CLK.close_print_bound_utc("US", d), source="KIS") for d, v in zip(us, y)])
    if usd:
        ru = rng.normal(0.0, 0.004, size=spx_days - 1)
        if usd_1d is not None:
            ru[-1] = usd_1d
        ux = list(100.0 * np.cumprod(np.concatenate([[1.0], 1.0 + ru])))
        days = us if usd_last is None else [d for d in us if d <= usd_last]
        store.append([P.stamp_quote("USD_LIVE_PROXY", d, v, quote_utc=CLK.close_print_bound_utc("US", d) - timedelta(minutes=1),
                                    retrieved_at_utc=CLK.close_print_bound_utc("US", d), source="Yahoo") for d, v in zip(days, ux)])
    if kospi_weeks:
        kr = _sessions("KR", OCT2, kospi_weeks * 5)
        kpx = list(3000.0 * np.cumprod(np.concatenate([[1.0], 1.0 + rng.normal(0.0, 0.01, size=len(kr) - 1)])))
        store.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR") for d, v in zip(kr, kpx)])
        krw = [1350.0]
        for a, b in zip(kpx, kpx[1:]):
            krw.append(krw[-1] * (1.0 + fx_corr_sign * (b / a - 1.0) * 0.5 + rng.normal(0.0, 0.001)))
        store.append([P.stamp_release("ECOS_1530_CLOSE", d, v, retrieved_at_utc=CLK.publication_instant("ECOS_1530_CLOSE", d) + timedelta(minutes=5),
                                      source="ECOS", registry=REG, clocks=CLK) for d, v in zip(kr, krw)])
    return store


def _hs(store, **kw):
    kw.setdefault("clocks", CLK)
    kw.setdefault("run_mode", "backtest")
    return R.hedge_state(store, REG, DECISION, KNOWLEDGE, **kw)


def test_hedge_01_reasons_failure_flags_and_fx_credit():
    store = _hedge_store(kospi_weeks=30)
    h = _hs(store)
    assert isinstance(h, R.HedgeState) and h.hedge_stale_inputs == () and not h.alerts
    assert abs(h.core_pce_yoy - 0.03008) < 1e-9 and "core_pce_ge_3" in h.hedge_reasons and h.hedge_credit_off
    assert h.corr63 is not None and ("corr_positive" in h.hedge_reasons) == (h.corr63 > 0.0)
    assert set(h.hedge_reasons) <= set(R.HEDGE_REASONS) and "ok" not in h.hedge_reasons
    assert [i["name"] for i in h.inputs] == ["core_pce", "equity_close", "us10y", "usd_live_proxy"]
    assert all(set(i) == INPUT_KEYS and i["role"] == "risk_model" for i in h.inputs)
    assert h.inputs[2]["series_id"] == "DGS10" and h.inputs[2]["obs_date"] == "2026-09-30"        # strict H.15: 1 Oct not usable
    assert h.inputs[1]["obs_date"] == "2026-10-01" and h.inputs[0]["vintage"] is not None
    assert h.fx_hedge_credit is True                                                               # KOSPI up, won strong: corr < 0
    assert _hs(_hedge_store(kospi_weeks=30, fx_corr_sign=1.0)).fx_hedge_credit is False
    assert _hs(_hedge_store(kospi_weeks=10)).fx_hedge_credit is None                             # fewer than 26 weeks
    # core PCE below 3.0% and a negative corr63: hedge credit on, reasons ["ok"]
    calm = _hedge_store(pce_yoy=0.025, seed=5)
    hc = _hs(calm)
    if hc.corr63 <= 0.0:
        assert not hc.hedge_credit_off and hc.hedge_reasons == ("ok",)
    else:
        assert hc.hedge_reasons == ("corr_positive",)
    assert "core_pce_ge_3" not in hc.hedge_reasons
    # 2.999% is below the threshold, 3.000% is on it (decimals in the core: 0.030)
    assert "core_pce_ge_3" not in _hs(_hedge_store(pce_yoy=0.02999)).hedge_reasons
    assert "core_pce_ge_3" in _hs(_hedge_store(pce_yoy=0.030)).hedge_reasons
    # hedge_failure: equity_1d < -1.5% and USD_proxy_1d < 0 on the same US session (from the live proxy, F-16)
    assert _hs(_hedge_store(eq_1d=-0.02, usd_1d=-0.003)).hedge_failure is True
    assert _hs(_hedge_store(eq_1d=-0.02, usd_1d=+0.003)).hedge_failure is False
    assert _hs(_hedge_store(eq_1d=-0.01, usd_1d=-0.003)).hedge_failure is False
    # classic_risk_off: equity down, USD up, 10y yield down on the same session (F-27); live: the KIS quote of 1 Oct
    live = lambda **kw: _hs(_hedge_store(y10_mode="live", **kw), run_mode="live")   # noqa: E731
    assert live(eq_1d=-0.02, usd_1d=+0.003, dy_last=-0.10).classic_risk_off is True
    assert live(eq_1d=-0.02, usd_1d=+0.003, dy_last=+0.10).classic_risk_off is False
    assert live(eq_1d=-0.02, usd_1d=-0.003, dy_last=-0.10).classic_risk_off is False
    assert live(eq_1d=-0.01, usd_1d=+0.003, dy_last=-0.10).classic_risk_off is False
    # in a backtest the strict-H.15 10y leg lags: the triple is evaluated on 30 Sep, so the 1 Oct legs decide nothing
    assert _hs(_hedge_store(eq_1d=-0.02, usd_1d=+0.003, dy_last=-0.10)).classic_risk_off is False
    # production channel: the KIS 10y quote stamped at the US close (live run_mode)
    lv = live()
    assert lv.inputs[2]["series_id"] == "US10Y_KIS_QUOTE" and lv.inputs[2]["obs_date"] == "2026-10-01" and lv.corr63 is not None


test_hedge_01_reasons_failure_flags_and_fx_credit.test_ids = ["T-HEDGE-01"]


def test_hedge_01_stale_inputs_never_halt_and_change_no_exposure():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        kstore, _, _ = _kospi_store(40, scale_sigma_to=0.2882)
        vt_before = _vt(kstore)
        # (1) a risk-model input missing two expected releases: hedge_credit_off, operator alert, no book HALTs
        store = _hedge_store(pce_last=date(2026, 7, 1))
        h = _hs(store)
        assert h.hedge_credit_off and "risk_model_input_stale" in h.hedge_reasons and h.hedge_stale_inputs == ("PCEPILFE",)
        a = h.alerts[0]
        assert a["code"] == "RISK_MODEL_INPUT_STALE" and a["series_id"] == "PCEPILFE" and a["escalated"] and a["severity"] == "page"
        assert set(a) == set(SCHEMA["properties"]["alerts"]["items"]["properties"]) and a["count"] == 1
        assert R.missed_releases(REG, "PCEPILFE", date(2026, 7, 1), DECISION, CLK) == 2
        assert R.missed_releases(REG, "PCEPILFE", date(2026, 8, 1), DECISION, CLK) == 1
        one = _hs(_hedge_store(pce_last=date(2026, 8, 1)))
        assert one.hedge_stale_inputs == ("PCEPILFE",) and not one.alerts[0]["escalated"] and one.alerts[0]["severity"] == "warn"
        assert all(reg.get(b).mode is EngineMode.ARMED for b in reg.ids())                        # never HALTED
        # (2) stale DTWEXBGS alone (context) changes no hedge flag: it is never an input
        assert "DTWEXBGS" not in {i["series_id"] for i in _hs(_hedge_store()).inputs}
        # (3) live USD proxy and DTWEXBGS both stale: hedge_credit_off, vt unchanged, no acting component fails closed
        base = _hs(_hedge_store())
        stale = _hs(_hedge_store(usd_last=date(2026, 9, 25)))
        assert stale.hedge_credit_off and "USD_LIVE_PROXY" in stale.hedge_stale_inputs
        assert stale.hedge_failure is False and stale.classic_risk_off is False                  # no event fabricated (F-17)
        assert stale.core_pce_yoy == base.core_pce_yoy and stale.corr63 == base.corr63
        none = _hs(_hedge_store(usd=False))
        assert none.hedge_credit_off and none.hedge_stale_inputs == ("USD_LIVE_PROXY",)
        after = _vt(kstore)
        assert after == vt_before and after.weight == vt_before.weight
        assert all(reg.get(b).mode is EngineMode.ARMED for b in reg.ids())
        # (4) fx_hedge_credit changes no exposure: with or without the fx inputs vt and the flags are the same
        with_fx, without_fx = _hs(_hedge_store(kospi_weeks=30)), _hs(_hedge_store())
        assert with_fx.fx_hedge_credit is not None and without_fx.fx_hedge_credit is None
        assert (with_fx.hedge_credit_off, with_fx.hedge_failure, with_fx.hedge_reasons) == (without_fx.hedge_credit_off, without_fx.hedge_failure, without_fx.hedge_reasons)
        assert _vt(kstore) == vt_before
        # (5) replay: a later core-PCE revision loaded after the decision leaves that decision's hedge_reasons unchanged
        store = _hedge_store()
        before = _hs(store)
        store.append([P.stamp_release("PCEPILFE", date(2026, 9, 1), 100.0, retrieved_at_utc=U(2026, 10, 30, 13), source="ALFRED",
                                      registry=REG, clocks=CLK, vintage=date(2026, 10, 30), value_status="revised")])
        replay = _hs(store)
        assert replay.hedge_reasons == before.hedge_reasons and replay.core_pce_yoy == before.core_pce_yoy
        later = R.hedge_state(store, REG, DECISION, U(2026, 10, 31), clocks=CLK, run_mode="backtest")
        assert later.core_pce_yoy != before.core_pce_yoy                                           # the revision is seen only later
        # (6) an unreadable publication calendar sets every risk-model default (T-ROLE-01, L1956)
        broken = _hs(_hedge_store(), clocks=StubClocks(unreadable=True))
        assert broken.hedge_credit_off and set(broken.hedge_stale_inputs) >= {"PCEPILFE", "SPX_OFFICIAL_CLOSE", "DGS10", "USD_LIVE_PROXY"}
        assert all("calendar" in n for n in broken.notes)
        nocal = _hs(_hedge_store(), clocks=None)
        assert nocal.hedge_credit_off and len(nocal.hedge_stale_inputs) == 4
        assert all(reg.get(b).mode is EngineMode.ARMED for b in reg.ids())


test_hedge_01_stale_inputs_never_halt_and_change_no_exposure.test_ids = ["T-HEDGE-01", "T-ROLE-01"]


def test_role_02_spx_failing_sets_hedge_credit_off_through_corr63():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        store = _hedge_store()
        gone = _store()
        for sid in ("PCEPILFE", "DGS10", "USD_LIVE_PROXY"):
            gone.append(store.rows(sid))
        for i in range(3):                                                        # three decisions, the S&P close absent
            dec = DECISION - timedelta(days=i)
            h = R.hedge_state(gone, REG, dec, dec + timedelta(minutes=30), clocks=CLK, run_mode="backtest")
            assert h.hedge_credit_off and "SPX_OFFICIAL_CLOSE" in h.hedge_stale_inputs and h.corr63 is None
            assert REG.resolve_binding("SPX_OFFICIAL_CLOSE", "corr63").role == "risk_model"
        assert reg.get("recommended:KR").mode is EngineMode.ARMED and reg.get("recommended:US").mode is EngineMode.ARMED
        # an S&P close whose daily return violates its contract (30%) is a failing input, not a value
        bad = _hedge_store()
        last = max(r["obs_date"] for r in bad.rows("SPX_OFFICIAL_CLOSE"))
        wild = _store()
        for sid in ("PCEPILFE", "DGS10", "USD_LIVE_PROXY"):
            wild.append(bad.rows(sid))
        wild.append([dict(r) for r in bad.rows("SPX_OFFICIAL_CLOSE") if r["obs_date"] != last])
        wild.append([_close_row("SPX_OFFICIAL_CLOSE", last, 9.0, market="US", source="KIS")])
        hw = R.hedge_state(wild, REG, DECISION, KNOWLEDGE, clocks=CLK, run_mode="backtest")
        assert "SPX_OFFICIAL_CLOSE" in hw.hedge_stale_inputs and hw.hedge_credit_off


test_role_02_spx_failing_sets_hedge_credit_off_through_corr63.test_ids = ["T-ROLE-02"]


def test_miss_02_exception_scope_vt_and_compose_halt_ops_hedge_state_never():
    with tempfile.TemporaryDirectory() as tmp:
        reg = _registry(tmp)
        # an exception inside hedge_state -> hedge_credit_off, reason risk_model_exception, an alert, never HALTED
        class Broken:
            def rows(self, sid):
                raise RuntimeError("store exploded")
        h = R.hedge_state(Broken(), REG, DECISION, KNOWLEDGE, clocks=CLK)
        assert h.hedge_credit_off and h.hedge_reasons == ("risk_model_exception",) and h.alerts[0]["code"] == "HEDGE_STATE_EXCEPTION"
        assert "store exploded" in h.notes[0] and not h.hedge_failure and h.fx_hedge_credit is None
        assert all(reg.get(b).mode is EngineMode.ARMED for b in reg.ids())
        # an exception inside market_vol_target -> HALTED (OPS, acting_risk_layer_exception) for the books it feeds only
        kstore, _, _ = _kospi_store(40)
        books = REG.book_ids(REG.resolve_binding("KOSPI_OFFICIAL_CLOSE", "R-06"))
        assert books == ("specification:KR",)
        out = R.guard_acting("market_vol_target", books, reg, DECISION, R.market_vol_target, Broken(), REG, CLK, "KR", DECISION, KNOWLEDGE)
        assert isinstance(out, R.ActingFailure) and out.fail_closed and "store exploded" in out.error
        assert out.alert["code"] == "ACTING_RISK_LAYER_EXCEPTION" and out.alert["severity"] == "page" and out.alert["books"] == ["specification:KR"]
        spec = reg.get("specification:KR")
        assert spec.halted and spec.halt["class"] == "OPS" and spec.halt["reason_code"] == "acting_risk_layer_exception"
        assert spec.halt["component"] == "market_vol_target" and spec.halt["rearm_mode"] == "auto"
        assert reg.get("recommended:KR").mode is EngineMode.ARMED and reg.get("specification:US").mode is EngineMode.ARMED
        # the happy path passes the result through untouched
        ok = R.guard_acting("market_vol_target", books, reg, DECISION, R.market_vol_target, kstore, REG, CLK, "KR", DECISION, KNOWLEDGE)
        assert isinstance(ok, R.VTResult)
        # an exception inside compose HALTs the book being composed (a product request is such an exception)
        out = R.guard_acting("compose", ("recommended:KR",), reg, DECISION, R.compose, 1.0, [0.75, 0.5], 1.0, 1.0, combine="product")
        assert isinstance(out, R.ActingFailure) and reg.get("recommended:KR").halted
        assert reg.get("recommended:KR").halt["reason_code"] == "acting_risk_layer_exception"
        assert reg.get("recommended:US").mode is EngineMode.ARMED
        # OPS re-arm when the cause clears: automatic, no reference reset, no cap
        b = B.runtime_rearm(reg, "recommended:KR", "auto", DECISION + timedelta(days=1))
        assert b.mode is EngineMode.ARMED and b.post_rearm_left == 0


test_miss_02_exception_scope_vt_and_compose_halt_ops_hedge_state_never.test_ids = ["T-MISS-02"]


# --------------------------------------------------------------------------- #
# T-LAG-02 (vt clause): a look-ahead shift changes vt and the lag audit names it
# --------------------------------------------------------------------------- #
def test_lag_02_shifted_input_changes_vt_and_trips_lag_audit():
    next_kr = min(d for d in (OCT2 + timedelta(days=i) for i in range(1, 10)) if CLK.is_session("KR", d))   # 6 Oct
    days = _sessions("KR", next_kr, 41)                                              # ... 2 Oct, 6 Oct
    px = _gbm(40, 11, sigma=0.02)                                                    # ~32% annualised: below the cap
    store = _store()
    store.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR") for d, v in zip(days[:-1], px[:-1])])
    honest = _vt(store)
    # (a) the look-ahead bug: every close relabelled one session earlier (C_{s+1} filed as the close of s)
    shifted = _store()
    shifted.append([_close_row("KOSPI_OFFICIAL_CLOSE", d, v, market="KR") for d, v in zip(days[:-1], px[1:])])
    res = _vt(shifted)
    assert isinstance(res, R.VTResult) and res.sigma_ann != honest.sigma_ann and res.weight != honest.weight
    # (b) the datum the shift smuggled in, audited independently of pit_value at the decision of t: unusable
    true_row = _close_row("KOSPI_OFFICIAL_CLOSE", next_kr, px[-1], market="KR")
    v = P.to_value(true_row, role="acting_exposure", books=("specification:KR",))
    audit = L.lag_audit([v], P.RunContext(DECISION, KNOWLEDGE), "KR", REG, CLK)
    assert audit["books"] == ["specification:KR"] and any(x["check"] == "available_at_utc <= decision_utc" for x in audit["violations"])
    _raises(lambda: L.lag_audit([v], P.RunContext(DECISION, KNOWLEDGE, "backtest"), "KR", REG, CLK), L.LookAheadError)
    # (c) the same datum stamped available one session early reaches the store but never the rule: vt unchanged, audit trips
    early = _close_row("KOSPI_OFFICIAL_CLOSE", next_kr, px[-1], market="KR", available=DECISION, retrieved=DECISION + timedelta(minutes=11))
    store.append([early])
    assert _vt(store) == honest
    ev = P.to_value(early, role="acting_exposure", books=("specification:KR",))
    assert any(x["check"] == "usable_at <= decision_utc" for x in L.lag_audit([ev], P.RunContext(DECISION, KNOWLEDGE), "KR", REG, CLK)["violations"])
    # a positional shift on the window dates is rejected by the M1 linter (the window walks sessions, never positions)
    _raises(lambda: L.assert_no_positional_shift(days, 1, expected_step=timedelta(days=1)), L.PositionalShiftRejected)


test_lag_02_shifted_input_changes_vt_and_trips_lag_audit.test_ids = ["T-LAG-02"]


# --------------------------------------------------------------------------- #
# Hedge-adjusted covariance inputs and the carry-then-drop status (TASK-M2-05)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _Stats:                              # the BasketStats shape (core/quant/risk.py) without importing gs_quant
    symbols: tuple
    sessions: int
    mean_returns: np.ndarray
    cov: np.ndarray
    corr: np.ndarray
    returns: np.ndarray


def _basket():
    corr = np.array([[1.0, -0.4, -0.3, 0.2], [-0.4, 1.0, 0.1, 0.0], [-0.3, 0.1, 1.0, 0.0], [0.2, 0.0, 0.0, 1.0]])
    sd = np.array([0.20, 0.08, 0.10, 0.12])
    return _Stats(("KODEX", "TLT", "USD", "GOLD"), 300, np.zeros(4), corr * np.outer(sd, sd), corr, np.zeros((299, 4)))


def test_apply_hedge_state_clamps_only_the_hedge_legs():
    cls = {"KODEX": "equity", "TLT": "duration", "USD": "usd_hedge", "GOLD": "other"}
    on = R.HedgeState(False, False, False, None, ("ok",), (), 0.025, -0.2, (), ())
    s = _basket()
    assert R.apply_hedge_state(s, cls, on) is s
    off = replace(on, hedge_credit_off=True, hedge_reasons=("core_pce_ge_3",))
    a = R.apply_hedge_state(s, cls, off)
    assert a.corr[0, 1] == a.corr[1, 0] == 0.0 and a.corr[0, 2] == -0.3 and a.corr[0, 3] == 0.2   # duration only
    neg = replace(s, corr=np.array([[1.0, -0.95, -0.95], [-0.95, 1.0, -0.95], [-0.95, -0.95, 1.0]]),
                  cov=np.array([[1.0, -0.95, -0.95], [-0.95, 1.0, -0.95], [-0.95, -0.95, 1.0]]) * 0.04, symbols=("A", "B", "C"))
    rep = R.apply_hedge_state(neg, {"A": "equity", "B": "duration", "C": "other"}, off)
    assert np.all(np.linalg.eigvalsh(rep.corr) >= -1e-12) and np.allclose(np.diag(rep.corr), 1.0) and rep.corr[0, 1] >= -1e-12
    assert np.allclose(np.diag(a.cov), np.diag(s.cov)) and np.allclose(np.diag(a.corr), 1.0)
    assert np.all(np.linalg.eigvalsh(a.corr) >= -1e-12) and a.symbols == s.symbols
    fail = replace(off, hedge_failure=True)
    b = R.apply_hedge_state(s, cls, fail)
    assert b.corr[0, 1] == 0.0 and b.corr[0, 2] == 0.0 and b.corr[0, 3] == 0.2
    stale = replace(on, hedge_credit_off=True, hedge_stale_inputs=("USD_LIVE_PROXY",), hedge_reasons=("risk_model_input_stale",))
    c = R.apply_hedge_state(s, cls, stale)
    assert c.corr[0, 2] == 0.0 and c.corr[0, 1] == 0.0                                                # F-17: no credit while stale
    only_fx = replace(on, hedge_failure=True)
    d = R.apply_hedge_state(s, cls, only_fx)
    assert d.corr[0, 2] == 0.0 and d.corr[0, 1] == -0.4
    assert np.allclose(a.cov, a.corr * np.outer(np.sqrt(np.diag(s.cov)), np.sqrt(np.diag(s.cov))))
    # Korea covariance: carry a failing series' last valid terms for 5 decisions, then drop; never hedge_credit_off
    sids = ("SOX_CLOSE", "NIKKEI225_CLOSE")
    state = {}
    for n in range(1, 8):
        status, state = R.covariance_carry(state, {"SOX_CLOSE"}, sids)
        assert status["NIKKEI225_CLOSE"] == "ok" and status["SOX_CLOSE"] == (f"stale_carried:{n}" if n <= 5 else "dropped")
    status, state = R.covariance_carry(state, set(), sids)
    assert status == {"SOX_CLOSE": "ok", "NIKKEI225_CLOSE": "ok"} and state["SOX_CLOSE"] == 0
    act = C.on_input_failure("SOX_CLOSE", C.Stale("missed_release"), REG.resolve_binding("SOX_CLOSE", "korea_covariance"))
    assert act.sets["sets_hedge_credit_off"] is False and act.halt == "never"


test_apply_hedge_state_clamps_only_the_hedge_legs.test_ids = ["T-HEDGE-01"]


# --------------------------------------------------------------------------- #
# Goldens and integration rows (REFDATA; one function per registry id)
# --------------------------------------------------------------------------- #
def _golden_refdata(gid: str, fids, note: str):
    _refdata(fids)          # NotRun while a fixture is absent; once all are listed the missing replay is a FAIL
    raise AssertionError(f"{gid}: fixtures listed but the golden replay (core/quant/costed.py) is not implemented; {note}")


def test_g_kr_01_buy_and_hold_refdata():
    _golden_refdata("G-KR-01", ["F13"], "buy-and-hold Sharpe 0.637, max DD -43.9%")


test_g_kr_01_buy_and_hold_refdata.test_ids = ["G-KR-01"]


def test_g_kr_02_vt20_gross_and_net_refdata():
    _golden_refdata("G-KR-02", ["F13"], "VT20 Sharpe 0.641 / 0.638 (3 bp) / 0.609 (35 bp) / 0.635 (6 bp) / 0.576 (70 bp); max DD -36.8% gross")


test_g_kr_02_vt20_gross_and_net_refdata.test_ids = ["G-KR-02"]


def test_g_kr_02b_delta_sharpe_shares_refdata():
    _golden_refdata("G-KR-02b", ["F13"], "dSR +0.004 (0.45) / -0.077 (0.06) / -0.123 (0.03) gross; -0.029 (0.36) at 35 bp; the 70 bp row is pre-patch R4b")


test_g_kr_02b_delta_sharpe_shares_refdata.test_ids = ["G-KR-02b"]


def test_g_kr_02c_static_book_refdata():
    _golden_refdata("G-KR-02c", ["F13"], "static book at 0.925: max DD -41.3%; dMDD +4.5 pp gross, +4.4 / +4.1 pp at 3 / 35 bp")


test_g_kr_02c_static_book_refdata.test_ids = ["G-KR-02c"]


def test_g_kr_03_window_returns_refdata():
    _golden_refdata("G-KR-03", ["F13"], "Jul-2026 crash -12.2% vs -38.6%; 2020 crash -25.8% vs -34.1%; H1-2026 +51.7% vs +101.1% (section 8.6 dates)")


test_g_kr_03_window_returns_refdata.test_ids = ["G-KR-03"]


def test_g_kr_04_weights_refdata():
    _golden_refdata("G-KR-04", ["F13"], "weights 0.30 / 0.33 / 0.25 on 22 Jun / 23 Jun / 30 Jul 2026; 0.61 earning on 2 Oct; 0.694 decided at the 2-Oct close (F-15 convention resolved on the fixture)")


test_g_kr_04_weights_refdata.test_ids = ["G-KR-04"]


def test_g_kr_06_cap_1_5_reference_mode_refdata():
    _refdata(["F13"])
    raise NotRun("REFDATA: G-KR-06 (reference mode): the cap-1.5 line 0.534 / -46.2% is pre-patch R4 and joins M2's exit only "
                 "once section 9.4 item 2's rerun on the 2-Oct official close is md5-frozen (TASK-M2-09); no number is invented")


test_g_kr_06_cap_1_5_reference_mode_refdata.test_ids = ["G-KR-06"]


def test_g_us_01_vt15_refdata():
    _golden_refdata("G-US-01", ["F10", "F14"], "U1 (French Mkt-RF to 2026-08 + ^GSPC Sep-2026): B&H 0.534 / -59.2% vs VT15 0.602 / -49.9% gross; 0.505 / -53.8% at 50 bp")


test_g_us_01_vt15_refdata.test_ids = ["G-US-01"]


def test_g_us_01b_static_book_refdata():
    _golden_refdata("G-US-01b", ["F10", "F14"], "static book at 0.890: max DD -54.0%; dMDD +4.1 / +0.2 / -3.4 pp gross / 50 / 100 bp")


test_g_us_01b_static_book_refdata.test_ids = ["G-US-01b"]


def test_g_us_01c_ewma_challenger_deferred_to_m3():
    _refdata(["F10", "F14"])
    raise NotRun("REFDATA: G-US-01c: the row's only content is the EWMA(0.94) challenger 0.605 / 0.520 / 0.434, which joins at M3 "
                 "(section 9.0b, F-18); nothing is asserted at M2")


test_g_us_01c_ewma_challenger_deferred_to_m3.test_ids = ["G-US-01c"]


def test_i_02_korea_window_replays_refdata():
    _golden_refdata("I-02", ["F13"], "Korea vt weights and window returns over 2024-07-31 -> 2024-08-09 and 2026-06-22 -> 2026-07-30, gross and net, match G-KR-03 / G-KR-04")


test_i_02_korea_window_replays_refdata.test_ids = ["I-02"]


# --------------------------------------------------------------------------- #
# Re-export and static guards
# --------------------------------------------------------------------------- #
def test_risk_module_reexports_and_no_wall_clock():
    import core.quant.risk as K
    for name in ("market_vol_target", "compose", "risk_layer", "hedge_state", "VTResult", "HedgeState", "ConcentrationBound", "LadderState", "VSResult"):
        assert getattr(K, name) is getattr(R, name), name
    src = Path(R.__file__).read_text(encoding="utf-8")
    assert "datetime.now(" not in src and "time.time(" not in src and "utcnow(" not in src
    for needle in ("order_" + "cash", "place_" + "order", "submit_" + "order", "/trad" + "ing/", "import " + "ccxt"):
        assert needle not in src, needle                                                        # P0: no order path (T-RO-01)
    assert K.analyze_history.__doc__ is None or "log" in K.__doc__                                 # the legacy statistics are untouched


test_risk_module_reexports_and_no_wall_clock.test_ids = []


def tests():
    return [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
