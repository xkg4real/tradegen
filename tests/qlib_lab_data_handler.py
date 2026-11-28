"""Pillar 2 tests: DataHandlerLP, StatefulProcessors, S1 FailClosedDropna, PurgedHorizonReturnLabel, DatasetH & TSDatasetH."""
from __future__ import annotations

import math
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from qlib_lab.data import (
    CSRankNorm,
    CSZScoreNorm,
    DataHandlerLP,
    DatasetH,
    DropnaLabelProcessor,
    ExplicitFillnaProcessor,
    ExpressionDataLoader,
    FailClosedDropnaProcessor,
    PurgedHorizonReturnLabel,
    RobustZScoreNorm,
    StandardZScoreNorm,
    TSDatasetH,
    WinsorizeClip,
    authorized_eval_context,
)
from qlib_lab.exceptions import (
    FitLeakageError,
    LookAheadSyntaxError,
    MissingFeatureVoidError,
    TestLabelLeakageError,
)


def _make_bar_panel(n_bars: int = 80, step: int = 3600) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    t0 = 1_700_000_000
    rows = []
    for inst_idx, inst in enumerate(("KRW-BTC", "KRW-ETH")):
        px = 1000.0 * (inst_idx + 1)
        for i in range(n_bars):
            rbps = int(rng.integers(-40, 45))
            px *= 1.0 + rbps / 10000.0
            end = t0 + i * step
            rows.append(
                {
                    "datetime": end,
                    "instrument": inst,
                    "close": px,
                    "return_bps": rbps,
                    "known_at": end + 15,
                }
            )
    return pd.DataFrame(rows)


def test_stateful_processors_require_fit_bounds_and_ignore_test_outliers() -> None:
    for cls in (WinsorizeClip, RobustZScoreNorm, StandardZScoreNorm):
        try:
            cls()
            raise AssertionError(f"{cls.__name__}() without fit bounds must raise FitLeakageError")
        except FitLeakageError:
            pass

    t0 = 1_700_000_000
    step = 3600
    df1 = _make_bar_panel(50, step)
    df2 = df1.copy()
    # Inject massive 1,000,000x shock in the test window (bars >= 35)
    df2.loc[df2["datetime"] >= t0 + 35 * step, "close"] *= 1_000_000.0

    fit_s, fit_e = t0 + 5 * step, t0 + 25 * step
    procs1 = [
        WinsorizeClip(fit_start_time=fit_s, fit_end_time=fit_e),
        RobustZScoreNorm(fit_start_time=fit_s, fit_end_time=fit_e, clip_outlier=False),
        StandardZScoreNorm(fit_start_time=fit_s, fit_end_time=fit_e),
    ]
    procs2 = [
        WinsorizeClip(fit_start_time=fit_s, fit_end_time=fit_e),
        RobustZScoreNorm(fit_start_time=fit_s, fit_end_time=fit_e, clip_outlier=False),
        StandardZScoreNorm(fit_start_time=fit_s, fit_end_time=fit_e),
    ]
    dh1 = DataHandlerLP.from_df(df1[["datetime", "instrument", "close"]], infer_processors=procs1)
    dh2 = DataHandlerLP.from_df(df2[["datetime", "instrument", "close"]], infer_processors=procs2)

    assert dh1.export_processor_states()["infer_processors"] == dh2.export_processor_states()["infer_processors"]
    pre_shock_1 = dh1.fetch(slice(fit_s, fit_e), data_key=DataHandlerLP.DK_I)
    pre_shock_2 = dh2.fetch(slice(fit_s, fit_e), data_key=DataHandlerLP.DK_I)
    np.testing.assert_allclose(pre_shock_1.to_numpy(), pre_shock_2.to_numpy(), rtol=0.0, atol=0.0)


def test_datahandler_lp_dual_chains_and_json_state_roundtrip() -> None:
    raw = _make_bar_panel(60)
    t0 = 1_700_000_000
    step = 3600

    # DropnaLabelProcessor must be refused in infer_processors!
    try:
        DataHandlerLP.from_df(raw, infer_processors=[DropnaLabelProcessor()])
        raise AssertionError("DropnaLabelProcessor in infer_processors must raise TypeError")
    except TypeError:
        pass

    loader = ExpressionDataLoader(
        raw,
        feature_expressions={"f1": "ROC($close, 1)", "f2": "Mean(ROC($close, 1), 4)"},
        label_config=PurgedHorizonReturnLabel(horizon_bars=2, hurdle_bps=10, step_seconds=step),
        bar_lag=1,
        on_lag_violation="nan",
    )
    dh = DataHandlerLP(
        data_loader=loader,
        infer_processors=[
            StandardZScoreNorm(fit_start_time=t0 + 6 * step, fit_end_time=t0 + 30 * step),
            CSRankNorm(),
            CSZScoreNorm(),
        ],
        learn_processors=[DropnaLabelProcessor()],
    )

    # DK_I keeps the final 2 bars (where future outcome labels are NaN!), while DK_L drops them!
    dk_i = dh.fetch(col_set="feature", data_key=DataHandlerLP.DK_I)
    dk_l = dh.fetch(col_set="feature", data_key=DataHandlerLP.DK_L)
    assert len(dk_i) == len(dk_l) + 4  # 2 instruments * 2 unlabeled tail bars

    # Zero-pickle JSON processor state save & IT_LS reload
    with tempfile.TemporaryDirectory() as tmp:
        st_path = Path(tmp) / "proc_states.json"
        dh.save_processor_states(st_path)
        dh_reloaded = DataHandlerLP(data_loader=loader, init_data=False)
        dh_reloaded.load_processor_states(st_path, reprocess=False)
        dh_reloaded.setup_data(init_type=DataHandlerLP.IT_LS)
        np.testing.assert_allclose(
            dk_i.to_numpy(),
            dh_reloaded.fetch(col_set="feature", data_key=DataHandlerLP.DK_I).to_numpy(),
            rtol=1e-13,
            atol=1e-13,
            equal_nan=True,
        )


def test_fail_closed_dropna_s1_and_explicit_fillna_indicators() -> None:
    t0 = 1_700_000_000
    rows = [
        {"datetime": t0 + i * 3600, "instrument": "KRW-BTC", "f1": float(i), "f2": float(i * 2)}
        for i in range(100)
    ]
    df = pd.DataFrame(rows)
    # 3% missing after 10-bar warmup -> passes S1 (<= 5%) and drops those 2 rows cleanly without imputation
    df_ok = df.copy()
    df_ok.loc[[20, 40], "f1"] = np.nan
    dh_ok = DataHandlerLP.from_df(
        df_ok, infer_processors=[FailClosedDropnaProcessor(warmup_bars=10, max_post_warmup_missing=0.05)]
    )
    assert len(dh_ok.fetch(data_key=DataHandlerLP.DK_I)) == 98

    # 8% missing after 10-bar warmup -> exceeds 5% S1 limit -> raises MissingFeatureVoidError!
    df_bad = df.copy()
    df_bad.loc[list(range(20, 28)), "f1"] = np.nan
    try:
        DataHandlerLP.from_df(
            df_bad, infer_processors=[FailClosedDropnaProcessor(warmup_bars=10, max_post_warmup_missing=0.05)]
        )
        raise AssertionError("Expected MissingFeatureVoidError when post-warmup missing > 5%")
    except MissingFeatureVoidError:
        pass

    # ExplicitFillnaProcessor stamps `<col>__isna` flags
    dh_fill = DataHandlerLP.from_df(
        df_bad, infer_processors=[ExplicitFillnaProcessor(fill_value=-99.0, add_indicator=True)]
    )
    filled = dh_fill.fetch(col_set="feature", data_key=DataHandlerLP.DK_I)
    assert "f1__isna" in filled.columns and "f2__isna" in filled.columns
    assert int(filled["f1__isna"].sum()) == 8
    assert (filled.loc[filled["f1__isna"] == 1.0, "f1"] == -99.0).all()


def test_purged_horizon_return_label_matches_br26_adapter_math() -> None:
    t0 = 1_700_000_000
    step = 3600
    # Construct exact return_bps cases around hurdle_bps = 10:
    # i=0 -> bars 1,2 have +6, +5 bps -> log1p(0.0006)+log1p(0.0005) > log1p(0.0010) -> "up" (0)
    # i=1 -> bars 2,3 have +5, +4 bps -> ~9 bps <= 10 bps -> "neutral" (2)
    # i=2 -> bars 3,4 have +4, -15 bps -> < log1p(-0.0010) -> "down" (1)
    rbps_seq = [0, 6, 5, 4, -15, 0]
    raw = pd.DataFrame(
        [
            {"datetime": t0 + i * step, "instrument": "KRW-BTC", "return_bps": r, "close": 100.0}
            for i, r in enumerate(rbps_seq)
        ]
    ).set_index(["datetime", "instrument"])

    lbl = PurgedHorizonReturnLabel(horizon_bars=2, hurdle_bps=10, step_seconds=step).compute(raw)
    cls_vals = lbl[("label", "direction_class")].to_numpy()
    end_vals = lbl[("meta", "label_end_utc")].to_numpy()
    assert cls_vals[0] == 0.0  # up
    assert cls_vals[1] == 2.0  # neutral
    assert cls_vals[2] == 1.0  # down
    assert np.isnan(cls_vals[4]) and np.isnan(cls_vals[5])
    assert end_vals[0] == float(t0 + 2 * step)
    expected_r0 = math.fsum([math.log1p(6 / 10000), math.log1p(5 / 10000)])
    assert abs(float(lbl[("label", "realized_log_return")].iloc[0]) - expected_r0) < 1e-15


def test_dataseth_fit_leakage_purging_embargo_and_test_label_lock() -> None:
    raw = _make_bar_panel(70)
    t0 = 1_700_000_000
    step = 3600

    loader = ExpressionDataLoader(
        raw,
        feature_expressions={"f1": "ROC($close, 1)"},
        label_config=PurgedHorizonReturnLabel(horizon_bars=3, hurdle_bps=10, step_seconds=step),
        bar_lag=1,
        on_lag_violation="nan",
    )
    # 1. fit_end_time > train_end must raise FitLeakageError!
    dh_leak = DataHandlerLP(
        data_loader=loader,
        infer_processors=[StandardZScoreNorm(fit_start_time=t0 + 4 * step, fit_end_time=t0 + 35 * step)],
        learn_processors=[DropnaLabelProcessor()],
    )
    try:
        DatasetH(
            handler=dh_leak,
            segments={"train": (t0 + 4 * step, t0 + 30 * step), "test": (t0 + 36 * step, t0 + 69 * step)},
        )
        raise AssertionError("Expected FitLeakageError when fit_end_time > train_end")
    except FitLeakageError:
        pass

    # 2. Valid DatasetH with embargo_bars=2 and horizon_bars=3 purging
    dh_clean = DataHandlerLP(
        data_loader=loader,
        infer_processors=[StandardZScoreNorm(fit_start_time=t0 + 4 * step, fit_end_time=t0 + 25 * step)],
        learn_processors=[DropnaLabelProcessor()],
    )
    ds = DatasetH(
        handler=dh_clean,
        segments={
            "train": (t0 + 4 * step, t0 + 30 * step),
            "valid": (t0 + 31 * step, t0 + 48 * step),
            "test": (t0 + 49 * step, t0 + 69 * step),
        },
        embargo_bars=2,
    )
    # The embargo ends training at close 28; the bar closing there arrives 15 seconds later.
    tr_df = ds.prepare("train", col_set=["feature", "label"], data_key=DataHandlerLP.DK_L)
    max_tr_ep = int(tr_df.index.get_level_values("datetime").max().timestamp())
    assert max_tr_ep == t0 + 24 * step

    # Likewise the last available validation outcome is from bar 45, received 15 seconds later.
    va_df = ds.prepare("valid", col_set=["feature", "label"], data_key=DataHandlerLP.DK_L)
    max_va_ep = int(va_df.index.get_level_values("datetime").max().timestamp())
    assert max_va_ep == t0 + 42 * step
    assert ds.effective_training_cutoff(include_valid=True) == t0 + 45 * step + 15

    # 3. Blocking test label access outside authorized_eval_context
    for bad_kwargs in (
        {"col_set": ["feature", "label"], "data_key": DataHandlerLP.DK_L},
        {"col_set": "label", "data_key": DataHandlerLP.DK_I},
        {"col_set": DataHandlerLP.CS_RAW, "data_key": DataHandlerLP.DK_I},
    ):
        try:
            ds.prepare("test", **bad_kwargs)
            raise AssertionError(f"Expected TestLabelLeakageError for {bad_kwargs}")
        except TestLabelLeakageError:
            pass

    # Default prepare("test") returns features ONLY (labels automatically stripped!)
    te_infer = ds.prepare("test")
    assert list(te_infer.columns) == ["f1"]

    with authorized_eval_context("unit_test_gate"):
        te_lbl = ds.prepare("test", col_set="label", data_key=DataHandlerLP.DK_L)
        assert "direction_class" in te_lbl.columns


def test_tsdataseth_causal_lookbacks_and_bfill_ban() -> None:
    raw = _make_bar_panel(40)
    t0 = 1_700_000_000
    step = 3600
    dh = DataHandlerLP.from_df(raw[["datetime", "instrument", "close"]])

    try:
        TSDatasetH(
            handler=dh,
            segments={"train": (t0, t0 + 20 * step), "test": (t0 + 21 * step, t0 + 39 * step)},
            step_len=5,
            fillna_type="ffill+bfill",
        )
        raise AssertionError("Expected LookAheadSyntaxError on fillna_type='ffill+bfill'")
    except LookAheadSyntaxError:
        pass

    ts_ds = TSDatasetH(
        handler=dh,
        segments={"train": (t0, t0 + 20 * step), "test": (t0 + 21 * step, t0 + 39 * step)},
        step_len=6,
        fillna_type="ffill",
    )
    sampler = ts_ds.prepare("test", col_set="feature", data_key=DataHandlerLP.DK_I)
    assert len(sampler) == 19 * 2
    win0 = sampler[(t0 + 21 * step, "KRW-BTC")]
    assert win0.shape == (6, 1)
    # Verify window matches bars 16..21 of KRW-BTC
    expected = (
        raw.loc[(raw["instrument"] == "KRW-BTC") & (raw["datetime"].between(t0 + 16 * step, t0 + 21 * step)), "close"]
        .to_numpy(dtype=np.float64)[:, None]
    )
    np.testing.assert_allclose(win0, expected)
