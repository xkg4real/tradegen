"""Sprint 3 integration (M2 risk layer, M3 estimator harness, M4 factor sleeves): the seams between the four
packages, asserted end to end on the S2 fixtures and stubs. Hermetic: synthetic stores in tempdirs, no reference
data, nothing written under ~/.nextgen.

1. `sleeves.apply_overlays` composes the market gross through `risk_layer.compose` (one min(), one bound check).
2. The harness SMA20 (`vol_estimators.sigma_for_decision`, `forecast_eval.estimator_gate`) is `risk_layer.sma_vol`,
   bit for bit, at every origin and under stale-carry exclusion; a failed challenger falls back to the same number.
3. `VSResult` has one home (`core.quant.sleeves`); `risk_layer` and `risk` re-export it.
4. `risk_layer.vol_state` assembles `macro_state.vol` from `market_vol_target` + `vt_for_book` + the gate's
   `vol_fields()` and validates against the schema (the warm-up label gap is documented, S3 log).
5. `costed.py` takes its bootstrap indices and PW block from `gate_stats`; the rulings' static checks on the six
   Sprint 3 modules (no wall clock, no raw-frame read in acting code, no new dependency, no cap above 1.0, dm_gate
   refused outside the specification book).
"""
from __future__ import annotations

import ast
import math
import re
from pathlib import Path

import numpy as np

from core.ficc import macro_schema as MS
from core.ficc import pit as P
from core.quant import costed
from core.quant import forecast_eval as F
from core.quant import gate_stats as GS
from core.quant import risk
from core.quant import risk_layer as R
from core.quant import sleeves as S
from core.quant import vol_estimators as E
from tests.macro_m1_pit import REG, _raises
from tests.macro_m2_risk import DECISION, KNOWLEDGE, _kospi_store, _vt
from tests.macro_m4_sleeves import DEC, IV, _dm, _sleeves, _vs
from tests.notrun import NotRun

ROOT = Path(__file__).resolve().parents[1]
MODULES = ("risk_layer", "sleeves", "vol_estimators", "forecast_eval", "costed", "gate_stats")
ACTING = ("risk_layer", "sleeves", "vol_estimators", "forecast_eval")   # never a raw frame
READERS = ("risk_layer", "sleeves", "forecast_eval")                     # read through pit_* only
SPEC = {"card_id": "MACRO-R06-KR-ETF", "estimator": "sma", "market": "KR", "instrument_book": "KRX_ETF_line"}


def _overlay(rule_id: str, value: float) -> S.Multiplier:
    return S.Multiplier(rule_id, value, "total", "market_gross")


# --------------------------------------------------------------------------- #
# 1. apply_overlays -> risk_layer.compose
# --------------------------------------------------------------------------- #
def test_apply_overlays_composes_through_risk_layer_compose():
    calls = []
    orig = R.compose

    def spy(vt, overlays, ladder, post_rearm_cap, **kw):
        calls.append((vt, tuple(overlays), ladder, post_rearm_cap))
        return orig(vt, overlays, ladder, post_rearm_cap, **kw)

    sleeves = _sleeves()
    base = S.base_weights(None, DEC, sleeves=sleeves, iv=IV)
    book = S.build_specification_book(sleeves, base, {("US", "momentum"): _vs("US", 0.8), ("KR", "momentum"): _vs("KR", 0.6)},
                                      {"US": _dm(0.5)}, decision_utc=DEC)
    R.compose = spy
    try:
        out = S.apply_market_gross(book, 0.8, overlays=[_overlay("R-28", 0.75), _overlay("R-29", 0.5)])
    finally:
        R.compose = orig
    long_keys = [(w.market, w.family) for w in book.sleeves if w.kind == "long_only" and w.family != "ts_trend"]
    assert long_keys and len(calls) == len(long_keys) and all(c == (0.8, (0.75, 0.5), 1.0, 1.0) for c in calls)
    before = {(w.market, w.family): w for w in book.sleeves}
    after = {(w.market, w.family): w for w in out.sleeves}
    for key in long_keys:
        for i, w in before[key].weights.items():
            assert abs(after[key].weights[i] - 0.4 * w) < 1e-15      # 0.8 x min(1, 0.75, 0.5) = 0.4, never 0.3
        assert "R-29" in after[key].binding and "R-06-VT" in after[key].binding
    # the bound checks are risk_layer's (CompositionError, a ValueError): nothing local survives
    assert S._compose(0.8, [0.75, 0.5], 0.5, 1.0) == R.compose(0.8, [0.75, 0.5], 0.5, 1.0) == 0.4
    _raises(lambda: S._compose(0.8, [0.375]), R.CompositionError)
    _raises(lambda: S._compose(1.2, [0.75]), R.CompositionError)
    _raises(lambda: S._compose(0.8, [0.75], 0.75, 1.0), R.CompositionError)


test_apply_overlays_composes_through_risk_layer_compose.test_ids = ["T-CAP-02", "T-BASIS-01"]


# --------------------------------------------------------------------------- #
# 2. one SMA20: harness baseline == acting estimator
# --------------------------------------------------------------------------- #
def test_estimator_harness_sma20_is_risk_layer_sma_vol():
    r = np.random.default_rng(11).standard_t(5, 400) * 0.01
    path = E.sma(r, 1).var
    for t in range(19, r.size):
        assert math.sqrt(path[t] * 252) == R.sma_vol(r[t - 19:t + 1]) == R.ESTIMATORS["sma20"](r[t - 19:t + 1], 20, 252)
    dec = E.sigma_for_decision("sma20", r)
    assert dec.status == "registered_default" and dec.sigma_ann == dec.sigma_sma20_ann == R.sma_vol(r[-20:])
    # stale-carry days excluded on both sides: the window extends to the last 20 valid returns
    valid = np.ones(r.size, dtype=bool)
    valid[-3] = valid[-7] = False
    masked = E.sigma_for_decision("sma20", r, valid=valid).sigma_ann
    assert masked == R.sma_vol(r[valid][-20:]) == math.sqrt(E.sma(r, 1, valid=valid).var[-1] * 252) != dec.sigma_ann
    # a challenger that fails at this origin falls back to the same number (T-EST-04), never a blend

    def boom(w):
        raise RuntimeError("no fit")
    fb = E.sigma_for_decision("gjr_t", r, min_years=1, refit_every=42, fitter=boom)
    assert fb.fallback_used and fb.status == "fallback_to_sma20" and fb.sigma_ann == R.sma_vol(r[-20:])
    # too few returns / flat closes: the same typed outcome on both sides
    assert E.sigma_for_decision("sma20", r[:15]).reason == "insufficient_history" and R.sma_vol(r[:15]) is None
    assert E.sigma_for_decision("sma20", np.zeros(30)).reason == "sigma_nonpositive" and R.sma_vol(np.zeros(30)) == 0.0
    assert set(R.ESTIMATORS) == {"sma20"} and set(E.ESTIMATORS) > {"sma20"}      # challengers stay in M3 (item 25)
    # on a PIT store: the gate's sigma for the decided session == market_vol_target's sigma on the same closes
    store, _, px = _kospi_store(60)
    vt = _vt(store)
    sel = F.estimator_gate(SPEC, REG, store, ctx=P.RunContext(DECISION, KNOWLEDGE), with_stage1=False)
    assert isinstance(vt, R.VTResult) and vt.status == "ok" and sel.status == "registered_default"
    assert sel.sigma_ann == vt.sigma_ann == R.sma_vol([b / a - 1.0 for a, b in zip(px, px[1:])])


test_estimator_harness_sma20_is_risk_layer_sma_vol.test_ids = ["T-VT-01", "T-EST-04"]


# --------------------------------------------------------------------------- #
# 3. VSResult: one home
# --------------------------------------------------------------------------- #
def test_vsresult_has_one_home():
    assert R.VSResult is S.VSResult is risk.VSResult and not hasattr(S.VSResult, "to_risk_layer")
    vs = _vs("US", 0.8)
    assert isinstance(vs, R.VSResult) and vs.factor == "vs" and vs.exposure_basis == "active"
    _raises(lambda: R.NoSuchName, AttributeError, "NoSuchName")


test_vsresult_has_one_home.test_ids = ["T-R03-01"]


# --------------------------------------------------------------------------- #
# 4. macro_state.vol from the vt / estimator code validates
# --------------------------------------------------------------------------- #
def test_vol_state_from_vt_and_gate_validates_against_the_schema():
    from tests.macro_m0_schemas import filled
    store, _, _ = _kospi_store(13 * 252)                      # 13 years: both display labels exist (T-LABEL-01)
    vt = _vt(store)
    assert isinstance(vt, R.VTResult) and vt.status == "ok"
    assert vt.display_label_rel in R.LABELS and vt.display_label_abs in R.LABELS and vt.label_status == "ok"
    book = R.vt_for_book(vt, "specification:KR", ever_armed=True)
    sel = F.estimator_gate(SPEC, REG, store, ctx=P.RunContext(DECISION, KNOWLEDGE), with_stage1=False)
    assert sel.status == "registered_default" and sel.sigma_ann == vt.sigma_ann
    state = filled()["macro_state"]
    state["vol"] = vol = R.vol_state(vt, book, sel.vol_fields(), instrument_book="KRX_ETF_line", rebalance="daily",
                                     no_trade_band=0.0)
    assert MS.validate("macro_state", state) == []
    assert vol["vt_status"] == "ok" and vol["vt_weight_next"] == vt.weight == book.weight <= 1.0
    assert vol["vt_weight_recommended_book"] == 1.0                         # R-06 card NOT_RUN: 1.0 (rulings 1)
    assert vol["estimator"] == "sma20" and vol["estimator_gate"] == sel.gate_dict() and vol["sigma_ann"] == vt.sigma_ann
    assert vol["label_method_rel"] == R.LABEL_METHOD_REL and vol["label_method_abs"] == R.LABEL_METHOD_ABS
    assert vol["target_ann"] == vt.target_ann and vol["alt_sigma_logged"] is None
    rec = R.vol_state(vt, book, sel.vol_fields(), instrument_book="KRX_ETF_line", recommended_pass=True)
    assert rec["vt_weight_recommended_book"] == vt.weight
    # the gate not run: NOT_RUN on sma20, still schema-valid
    state["vol"] = R.vol_state(vt, book, None, instrument_book="KRX_ETF_line")
    assert MS.validate("macro_state", state) == [] and state["vol"]["estimator_b5"] == "NOT_RUN"
    assert state["vol"]["estimator_gate"]["status"] == "NOT_RUN"
    # warm-up (15 closes): vt 1.0 / warmup; the display labels are undefined before 756 sigma values / 10 years
    # (F-11): written null with vol.label_status naming why, and schema-valid (coordinator ruling (a), S9)
    short, _, _ = _kospi_store(15)
    warm = _vt(short)
    wbook = R.vt_for_book(warm, "specification:KR", ever_armed=False)
    state["vol"] = R.vol_state(warm, wbook, None, instrument_book="KRX_ETF_line")
    assert state["vol"]["vt_status"] == "warmup" and state["vol"]["vt_weight_next"] == 1.0 and state["vol"]["sigma_ann"] is None
    assert state["vol"]["display_label_rel"] is None and state["vol"]["display_label_abs"] is None
    assert "insufficient_history" in state["vol"]["label_status"]
    assert MS.validate("macro_state", state) == [] and MS.field_class("macro_state", "/vol/label_status", state) == "display"
    state["vol"]["display_label_rel"] = "unknown"                       # the enum values are unchanged
    assert MS.validate("macro_state", state)
    state["vol"]["display_label_rel"] = None
    for key in ("vt_status", "estimator_b5"):                           # null stays an error outside the two labels
        assert MS.validate("macro_state", dict(state, vol=dict(state["vol"], **{key: None}))), key
    # fail closed with no previous state: nothing to publish (M6 carries the previous artifact)
    miss = P.MissingInput("KOSPI_OFFICIAL_CLOSE", "missing", "acting_exposure", ("specification:KR",))
    fc = R.vt_for_book(miss, "specification:KR", ever_armed=True)
    assert fc.vt_status == "fail_closed" and fc.weight is None
    _raises(lambda: R.vol_state(vt, fc, None, instrument_book="KRX_ETF_line"), ValueError, "no vt weight")


test_vol_state_from_vt_and_gate_validates_against_the_schema.test_ids = ["T-VT-01", "T-LABEL-01"]


# --------------------------------------------------------------------------- #
# 5. costed -> gate_stats; the rulings' static checks on the Sprint 3 modules
# --------------------------------------------------------------------------- #
def test_s3_rulings_static_and_costed_uses_gate_stats():
    src = {m: (ROOT / "core" / "quant" / f"{m}.py").read_text(encoding="utf-8") for m in MODULES}
    for m, text in src.items():
        tree = ast.parse(text)
        calls = {ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        assert not {c for c in calls if c.endswith(("datetime.now", "datetime.utcnow", "time.time", "date.today"))}, m
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        imported |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        assert not {i for i in imported if i.split(".")[0] in ("arch", "jsonschema", "pyarrow", "yfinance", "requests")}, m
    for m in ACTING:
        assert not re.search(r"read_csv|load_history|read_parquet|urlopen|_yf_fetch|_fred_fetch", src[m]), m
    for m in READERS:
        assert re.search(r"pit_value\(|pit_window\(|read_input\(", src[m]), m
    assert "GS.block_indices(" in src["costed"] and "GS.pw_block(" in src["costed"]
    assert not re.search(r"^def (block_indices|pw_block|optimal_block_length)\(", src["costed"], re.M)
    idx = GS.block_indices(500, 63, 20, 7, "circular")
    assert idx.shape == (20, 500) and (GS.block_indices(500, 63, 20, 7, "circular") == idx).all()
    assert GS.pw_block_floor(np.random.default_rng(3).normal(size=400)) >= GS.PC3_BLOCK_FLOOR == 10
    # nothing above 1.0 anywhere: every cap / factor entry refuses
    r = np.full(300, 0.01)
    for bad in (1.0001, 1.5, 2.0):
        _raises(lambda: R.compose(bad, [], 1.0, 1.0), ValueError)
        _raises(lambda: R.compose(0.8, [bad], 1.0, 1.0), ValueError)
        _raises(lambda: S.vol_scale_from_returns(r, cap=bad), ValueError)
        _raises(lambda: costed.vt_weights(r, 0.2, cap=bad), ValueError)
        _raises(lambda: F.sized_book(r, np.full(300, 1e-4), cap=bad), ValueError)
        _raises(lambda: R.market_vol_target(None, REG, None, "KR", DECISION, KNOWLEDGE, rules={"vol_target": {
            "KR": {"target_ann": 0.2, "cap": bad, "window": 20}, "annualisation_days": 252}}), ValueError, "cap")
    # dm_gate acts in the specification book only (item 22): refused before any read
    for book in ("recommended", "forward_sim", "card"):
        _raises(lambda: S.dm_gate(None, REG, "US", DEC, DEC, book=book), S.MacroRefusal, "specification")


test_s3_rulings_static_and_costed_uses_gate_stats.test_ids = ["T-COST-01"]


def tests():
    return [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]


if __name__ == "__main__":
    from tests.macro_acceptance import run_module
    raise SystemExit(run_module(globals()))
