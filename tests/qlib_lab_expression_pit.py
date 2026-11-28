"""Pillar 1 tests: Formulaic Alpha/Feature DSL, Static Future-Shift Ban, CSE DAG, and Bitemporal PIT Engine."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from core.ficc import pit as core_pit
from qlib_lab.exceptions import CausalLagViolationError, LookAheadSyntaxError, SecurityRefusalError
from qlib_lab.expression import (
    BitemporalPITProvider,
    DIDMEventRecord,
    LabelContext,
    PinnedScoreRecord,
    SlotObservation,
    compile_expressions,
    evaluate_expressions,
    parse_expression,
)


def _make_multi_asset_panel(T: int = 50) -> pd.DataFrame:
    rng = np.random.default_rng(101)
    t0 = 1_700_000_000
    step = 3600
    rows = []
    for inst_idx, inst in enumerate(("KRW-BTC", "KRW-ETH", "KRW-XRP")):
        px = 100.0 * (inst_idx + 1)
        for i in range(T):
            ret = rng.normal(0.0005 * (inst_idx + 1), 0.01)
            px *= 1.0 + ret
            hi = px * (1.0 + abs(rng.normal(0.003, 0.001)))
            lo = px * (1.0 - abs(rng.normal(0.003, 0.001)))
            vol = 1000.0 + 100.0 * abs(rng.normal(0.0, 2.0))
            end = t0 + i * step
            rows.append(
                {
                    "datetime": end,
                    "instrument": inst,
                    "open": px * 0.999,
                    "high": hi,
                    "low": lo,
                    "close": px,
                    "volume": vol,
                    "known_at": end,
                }
            )
    return pd.DataFrame(rows).set_index(["datetime", "instrument"]).sort_index()


def test_static_future_shift_ban_and_label_context() -> None:
    for bad_expr in (
        "Ref($close, -1)",
        "Ref(Ref($close, -2), 5)",
        "Delta($close, -1)",
        "ROC($close, -3)",
        "Mean($close, 0)",
        "Std($close, -5)",
        "PRef($$cpi, -1)",
    ):
        try:
            parse_expression(bad_expr)
            raise AssertionError(f"Expected LookAheadSyntaxError for {bad_expr!r}")
        except LookAheadSyntaxError:
            pass

    with LabelContext():
        lbl_node = parse_expression("Ref($close, -2) / $close - 1")
        assert lbl_node.max_forward_bars() == 2
        # PRef($$series, -1) is STILL banned even inside LabelContext!
        try:
            parse_expression("PRef($$cpi, -1)")
            raise AssertionError("PRef with negative k must always raise LookAheadSyntaxError")
        except LookAheadSyntaxError:
            pass


def test_ast_whitelist_refuses_injection_and_dunders() -> None:
    for bad_expr in (
        "__import__('os').system('echo pwn')",
        "$close.__class__",
        "open('/etc/hosts')",
        "(lambda x: x)($close)",
        "[$close for _ in (1, 2)]",
        "Mean($close, d=True)",
    ):
        try:
            parse_expression(bad_expr)
            raise AssertionError(f"Expected SecurityRefusalError for {bad_expr!r}")
        except SecurityRefusalError:
            pass


def test_cse_dag_deduplicates_common_subexpressions() -> None:
    panel = _make_multi_asset_panel(40)
    exprs = {
        "alpha_1": "(Mean($close, 10) - EMA($close, 10)) / Std($close, 10)",
        "alpha_2": "(Mean($close, 10) + EMA($close, 10)) / Std($close, 10)",
        "alpha_3": "CSRank(Mean($close, 10) / Std($close, 10))",
    }
    dag = compile_expressions(exprs)
    out = dag.evaluate(panel)
    assert list(out.columns) == ["alpha_1", "alpha_2", "alpha_3"]
    # Shared nodes Field($close), Mean($close, 10), EMA($close, 10), Std($close, 10) must each evaluate ONCE!
    for key, count in dag.last_eval_counts.items():
        assert count == 1, f"Node {key} evaluated {count} times instead of 1"


def test_all_39_operators_and_strict_future_invariance() -> None:
    panel = _make_multi_asset_panel(45)
    exprs = {
        "op_add": "Add($close, $open)",
        "op_sub": "Sub($high, $low)",
        "op_mul": "Mul($close, $volume)",
        "op_div": "Div($close, $open)",
        "op_log": "Log($close)",
        "op_abs": "Abs($close - $open)",
        "op_sign": "Sign($close - Ref($close, 1))",
        "op_clip": "Clip(ROC($close, 1), -0.02, 0.02)",
        "op_if": "If($close > Ref($close, 1), 1.0, -1.0)",
        "op_ref": "Ref($close, 3)",
        "op_delta": "Delta($close, 2)",
        "op_roc": "ROC($close, 4)",
        "op_mean": "Mean($close, 8)",
        "op_sum": "Sum($volume, 6)",
        "op_std": "Std($close, 8)",
        "op_var": "Var($close, 8)",
        "op_skew": "Skew($close, 10)",
        "op_kurt": "Kurt($close, 10)",
        "op_max": "Max($high, 8)",
        "op_min": "Min($low, 8)",
        "op_med": "Med($close, 7)",
        "op_quant": "Quantile($close, 9, 0.75)",
        "op_tsrank": "TSRank($close, 8)",
        "op_idxmax": "IdxMax($high, 8)",
        "op_idxmin": "IdxMin($low, 8)",
        "op_ema": "EMA($close, 10)",
        "op_wma": "WMA($close, 6)",
        "op_rsi": "RSI($close, 14)",
        "op_atr1": "ATR(14)",
        "op_atr4": "ATR($high, $low, $close, 14)",
        "op_cov": "Cov($close, $volume, 10)",
        "op_corr": "Corr($close, $volume, 10)",
        "op_slope": "Slope($close, 10)",
        "op_rsqr": "Rsquare($close, 10)",
        "op_resi": "Resi($close, 10)",
        "op_zscore": "ZScore($close, 10)",
        "op_robz": "RobustZScore($close, 10)",
        "op_csrank": "CSRank(ROC($close, 1))",
        "op_csz": "CSZScore(ROC($close, 1))",
        "op_csdemean": "CSDemean(ROC($close, 1))",
    }
    res1 = evaluate_expressions(panel, exprs)
    assert not res1.iloc[-5:].isna().any().any(), "Tail rows after warmup should be completely finite"
    np.testing.assert_allclose(res1["op_atr1"].to_numpy(), res1["op_atr4"].to_numpy(), equal_nan=True)

    # Mutate all future bars after index 25 -> bars <= 25 MUST stay bit-for-bit identical!
    dts = sorted(panel.index.get_level_values("datetime").unique())
    cutoff_dt = dts[25]
    mutated = panel.copy()
    future_mask = mutated.index.get_level_values("datetime") > cutoff_dt
    mutated.loc[future_mask, "close"] *= 50.0
    mutated.loc[future_mask, "high"] *= 60.0
    mutated.loc[future_mask, "volume"] *= 100.0
    res2 = evaluate_expressions(mutated, exprs)

    past1 = res1.loc[res1.index.get_level_values("datetime") <= cutoff_dt]
    past2 = res2.loc[res2.index.get_level_values("datetime") <= cutoff_dt]
    np.testing.assert_allclose(past1.to_numpy(), past2.to_numpy(), rtol=0.0, atol=0.0, equal_nan=True)


def test_bar_grid_known_at_causal_lag_and_late_backfill() -> None:
    t0 = 1_700_000_000
    step = 3600
    rows = []
    for i in range(15):
        end = t0 + i * step
        # Bar 4 was missed live and backfilled late at t0 + 7 * step + 100!
        ka = (t0 + 7 * step + 100) if i == 4 else (end + 20)
        rows.append({"datetime": end, "instrument": "KRW-BTC", "close": 100.0 + i, "known_at": ka})
    panel = pd.DataFrame(rows).set_index(["datetime", "instrument"])

    # 1. With bar_lag=0 and on_lag_violation='raise', known_at > as_of raises CausalLagViolationError!
    try:
        evaluate_expressions(panel, {"c": "$close"}, bar_lag=0, on_lag_violation="raise")
        raise AssertionError("Expected CausalLagViolationError when known_at > as_of")
    except CausalLagViolationError:
        pass

    # 2. With bar_lag=1 and on_lag_violation='nan' (BR-26 Upbit convention):
    # At i=5 (as_of = t0+5*step), latest bar slot is i=4, whose known_at is t0+7*step+100 > as_of -> NaN!
    # At i=6 (as_of = t0+6*step), Mean($close, 3) needs slots [3, 4, 5], and slot 4 is STILL unknown -> NaN!
    # At i=7 (as_of = t0+7*step), slot 4 known_at is t0+7*step+100 > t0+7*step -> STILL NaN!
    # At i=8 (as_of = t0+8*step >= t0+7*step+100), slot 4 IS KNOWN -> Mean($close, 3) over [5,6,7] and Mean($close, 5) over [3..7] are FINITE!
    out = evaluate_expressions(
        panel,
        {"c": "$close", "m5": "Mean($close, 5)"},
        bar_lag=1,
        on_lag_violation="nan",
    )
    c_vals = out["c"].to_numpy()
    m5_vals = out["m5"].to_numpy()
    assert np.isnan(c_vals[5]) and np.isfinite(c_vals[6])  # slot 5 was timely at i=6!
    assert np.isnan(m5_vals[5]) and np.isnan(m5_vals[6]) and np.isnan(m5_vals[7])
    assert np.isfinite(m5_vals[8]) and abs(m5_vals[8] - np.mean([103, 104, 105, 106, 107])) < 1e-12


def test_bitemporal_pit_store_yoy_mom_and_pref() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = core_pit.PITStore(Path(tmp) / "pit_store")
        prov = BitemporalPITProvider(pit_store=store)

        # Populate monthly CPI observations: Jan 2025 (100.0) and Jan 2026 first release (103.0) + late revision (104.0)
        # Deliberately omit Feb 2025 so Feb 2026 YoY has a missing calendar endpoint -> MUST return NaN, not Jan 2025!
        prov.add_series_row(
            "USCPI",
            "2025-01-01",
            100.0,
            available_at_utc="2025-02-12T13:30:00Z",
            retrieved_at_utc="2025-02-12T13:35:00Z",
            value_status="first_release",
        )
        prov.add_series_row(
            "USCPI",
            "2025-12-01",
            102.0,
            available_at_utc="2026-01-14T13:30:00Z",
            retrieved_at_utc="2026-01-14T13:35:00Z",
            value_status="first_release",
        )
        prov.add_series_row(
            "USCPI",
            "2026-01-01",
            103.0,
            available_at_utc="2026-02-12T13:30:00Z",
            retrieved_at_utc="2026-02-12T13:35:00Z",
            value_status="first_release",
        )
        # Revision published/retrieved later on 2026-03-12
        prov.add_series_row(
            "USCPI",
            "2026-01-01",
            104.0,
            available_at_utc="2026-03-12T13:30:00Z",
            retrieved_at_utc="2026-03-12T13:35:00Z",
            value_status="revised",
        )
        # Feb 2026 released on 2026-03-15, while Feb 2025 is missing!
        prov.add_series_row(
            "USCPI",
            "2026-02-01",
            105.0,
            available_at_utc="2026-03-15T13:30:00Z",
            retrieved_at_utc="2026-03-15T13:35:00Z",
            value_status="first_release",
        )

        dts = [
            "2026-02-01T00:00:00Z",  # Jan 2026 not released yet! Latest visible is Dec 2025 (102.0)
            "2026-02-13T00:00:00Z",  # Jan 2026 first_release (103.0) visible; YoY vs Jan 2025 = +3%, MoM vs Dec 2025 = 103/102-1
            "2026-03-13T00:00:00Z",  # Jan 2026 revised (104.0) visible; YoY = +4%
            "2026-03-16T00:00:00Z",  # Feb 2026 (105.0) visible; MoM = 105/104-1, YoY = NaN (Feb 2025 missing!)
        ]
        panel = pd.DataFrame(
            [{"datetime": t, "instrument": "KRW-BTC", "close": 100.0} for t in dts]
        ).set_index(["datetime", "instrument"])

        out = evaluate_expressions(
            panel,
            {
                "cur": "PIT($$USCPI)",
                "prev": "PRef($$USCPI, 1)",
                "yoy": "PITYoY($$USCPI)",
                "mom": "PITMoM($$USCPI)",
            },
            pit_provider=prov,
        )
        np.testing.assert_allclose(out["cur"].to_numpy(), [102.0, 103.0, 104.0, 105.0])
        np.testing.assert_allclose(out["prev"].to_numpy(), [100.0, 102.0, 102.0, 104.0])
        assert np.isnan(out["yoy"].iloc[0])
        assert abs(out["yoy"].iloc[1] - 0.03) < 1e-12
        assert abs(out["yoy"].iloc[2] - 0.04) < 1e-12
        assert np.isnan(out["yoy"].iloc[3]), "Missing calendar endpoint Feb 2025 must produce NaN, not positional shift"
        assert abs(out["mom"].iloc[3] - (105.0 / 104.0 - 1.0)) < 1e-12


def test_pit_d1_d2_d3_q1_bitemporal_operators() -> None:
    t0 = datetime(2026, 5, 1, 0, 0, tzinfo=timezone.utc)
    prov = BitemporalPITProvider()

    # --- D1: PITNewEventFlag ---
    # Event 1 first received at t0 + 2h; re-fetched UNCHANGED at t0 + 30h -> must NOT re-trigger D1 at t0 + 31h!
    prov.event_streams["D1_ECON"] = [
        DIDMEventRecord("ALFRED", "CPIAUCSL_202604", "sha_v1", t0 + timedelta(hours=2)),
        DIDMEventRecord("ALFRED", "CPIAUCSL_202604", "sha_v1", t0 + timedelta(hours=30)),  # unchanged re-fetch!
        DIDMEventRecord("ALFRED", "CPIAUCSL_202604", "sha_v2", t0 + timedelta(hours=40)),  # changed payload!
    ]
    # Heartbeat runs every hour except a gap around t0 + 50h
    hb_times = [t0 + timedelta(hours=h) for h in range(0, 48)]
    prov.register_heartbeat("D1_ECON", hb_times, max_stale_seconds=3600.0)

    # --- D2: PITSlotRatio ---
    # Populate 672 15-min slots (7 days) up to t0 + 45h, with baseline count=2 and last 96 slots count=4 -> ratio = 2 / ((576*2 + 96*4)/672)
    end_anchor = t0 + timedelta(hours=45)
    slots: list[SlotObservation] = []
    for k in range(672):
        se = end_anchor - timedelta(minutes=15 * k)
        cnt = 4 if k < 96 else 2
        # Make slot k=0 backfilled late at end_anchor + 2h so at end_anchor D2 is NaN, and at end_anchor + 2h (with new slots) finite!
        fetched = (end_anchor + timedelta(hours=2)) if k == 10 else se
        slots.append(SlotObservation(slot_end_utc=se, item_count=cnt, fetched_at_utc=fetched))
    # Also add slots up to end_anchor + 2h
    for m in range(1, 9):
        se2 = end_anchor + timedelta(minutes=15 * m)
        slots.append(SlotObservation(slot_end_utc=se2, item_count=4, fetched_at_utc=se2))
    prov.slot_streams["GDELT_SLOTS"] = slots

    # --- D3 & Q1: PITPinnedScoreMean ---
    prov.score_streams["DIDM_V0"] = [
        # Pinned version, received at t0+1h, but export receipt on PC at t0+5h -> known_at = t0+5h!
        PinnedScoreRecord("s1", 80.0, t0 + timedelta(hours=1), t0 + timedelta(hours=5), "v0.1", "prompt_ok"),
        PinnedScoreRecord("s2", 60.0, t0 + timedelta(hours=6), t0 + timedelta(hours=6), "v0.1", "prompt_ok"),
        # Unpinned version -> must be ignored and counted in diagnostics!
        PinnedScoreRecord("s_bad_ver", 999.0, t0 + timedelta(hours=6), t0 + timedelta(hours=6), "v0.2_unpinned", "prompt_ok"),
    ]

    eval_dts = [
        t0 + timedelta(hours=3),   # D1=1 (from +2h); D3: s1 export not received yet (receipt=+5h) -> NaN!
        t0 + timedelta(hours=7),   # D1=1; D3: both s1(80) and s2(60) known -> mean = 70.0!
        t0 + timedelta(hours=31),  # D1=0 (>24h after +2h, and +30h re-fetch had unchanged sha_v1!)
        t0 + timedelta(hours=41),  # D1=1 (changed payload sha_v2 at +40h!)
        t0 + timedelta(hours=45),  # D2: slot k=10 not backfilled yet (fetched at +47h) -> NaN!
        t0 + timedelta(hours=47),  # D2: backfill arrived -> all 96 numerator slots present -> finite > 1.0!
        t0 + timedelta(hours=50),  # D1: heartbeat stale (> 1h after last hb at +47h) -> NaN!
    ]
    panel = pd.DataFrame(
        [{"datetime": dt, "instrument": "KRW-BTC", "close": 100.0} for dt in eval_dts]
    ).set_index(["datetime", "instrument"])

    out = evaluate_expressions(
        panel,
        {
            "d1": "PITNewEventFlag($$D1_ECON, 24)",
            "d2": "PITSlotRatio($$GDELT_SLOTS, 96, 672, 900, 0.95)",
            "d3": "PITPinnedScoreMean($$DIDM_V0, 24, 'v0.1', 'prompt_ok', 'mean')",
        },
        pit_provider=prov,
    )

    d1_v = out["d1"].to_numpy()
    assert d1_v[0] == 1.0 and d1_v[1] == 1.0
    assert d1_v[2] == 0.0, "Unchanged vintage re-fetch must NOT trigger D1"
    assert d1_v[3] == 1.0, "Changed payload hash must trigger D1"
    assert np.isnan(d1_v[6]), "Missing source heartbeat must make D1 NaN (never 0)"

    d2_v = out["d2"].to_numpy()
    assert np.isnan(d2_v[4]), "Un-backfilled numerator slot must make D2 NaN"
    assert np.isfinite(d2_v[5]) and d2_v[5] > 1.5

    d3_v = out["d3"].to_numpy()
    assert np.isnan(d3_v[0]), "Late export receipt must delay D3 visibility"
    assert abs(d3_v[1] - 70.0) < 1e-12
    assert prov.diagnostics["DIDM_V0_ignored_unpinned"] == 1

    # Retroactive record must fail closed with CausalLagViolationError!
    prov.score_streams["DIDM_V0"].append(
        PinnedScoreRecord("s_retro", 50.0, t0, t0, "v0.1", "prompt_ok", retroactive=True)
    )
    try:
        evaluate_expressions(
            panel,
            {"d3": "PITPinnedScoreMean($$DIDM_V0, 24, 'v0.1', 'prompt_ok', 'mean')"},
            pit_provider=prov,
        )
        raise AssertionError("Expected CausalLagViolationError on retroactive=True score record")
    except CausalLagViolationError:
        pass
