"""Pillar 3 tests: FrozenModelSpec, Ridge/Huber, Multinomial/B0/B2, HistGBDT, DoubleEnsemble, RegimeKernelReweighter & OnlineHedgeCombiner."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from qlib_lab import RESEARCH_FLAGS, _accel
from qlib_lab.data import (
    DataHandlerLP,
    DatasetH,
    DropnaLabelProcessor,
    ExpressionDataLoader,
    PurgedHorizonReturnLabel,
    StaticDataLoader,
    authorized_eval_context,
)
from qlib_lab.exceptions import SecurityRefusalError, SparseEventRefusalError
from qlib_lab.models import (
    DoubleEnsembleModel,
    FrozenModelSpec,
    HistGBDTModel,
    Model,
    MovingBlockBootstrapModel,
    MultinomialDirectionModel,
    OnlineHedgeCombiner,
    PriorFrequencyBaselineModel,
    RegimeKernelReweighter,
    RidgeLinearModel,
)


def _make_synthetic_signal_dataset(n_bars: int = 220, seed: int = 42) -> DatasetH:
    rng = np.random.default_rng(seed)
    t0 = 1_700_000_000
    step = 3600

    sig_prev = 0.0
    rows = []
    px = 1000.0
    for i in range(n_bars):
        # True causal alpha signal observed at bar i-1 predicting bars i+1, i+2
        noise = rng.normal(0.0, 18.0)
        rbps = int(round(22.0 * sig_prev + noise))
        px *= 1.0 + rbps / 10000.0
        sig_cur = float(rng.normal(0.0, 1.0))
        sig_prev = sig_cur
        end = t0 + i * step
        rows.append(
            {
                "datetime": end,
                "instrument": "KRW-BTC",
                "close": px,
                "return_bps": rbps,
                "alpha_sig": sig_cur,
                "noise_1": float(rng.normal(0.0, 1.0)),
                "noise_2": float(rng.normal(0.0, 1.0)),
                "rare_d1": 1.0 if i in (25, 60) else 0.0,  # Only 2 events (< 8)
                "known_at": end,
            }
        )
    raw = pd.DataFrame(rows)
    loader = ExpressionDataLoader(
        raw,
        feature_expressions={
            "f_sig": "$alpha_sig",
            "f_roc1": "ROC($close, 1)",
            "f_n1": "$noise_1",
            "f_n2": "$noise_2",
            "f_d1": "$rare_d1",
        },
        label_config=PurgedHorizonReturnLabel(horizon_bars=2, hurdle_bps=10, step_seconds=step),
        bar_lag=0,
    )
    dh = DataHandlerLP(data_loader=loader, learn_processors=[DropnaLabelProcessor()])
    return DatasetH(
        handler=dh,
        segments={
            "train": (t0 + 4 * step, t0 + 120 * step),
            "valid": (t0 + 123 * step, t0 + 165 * step),
            "test": (t0 + 168 * step, t0 + (n_bars - 1) * step),
        },
        embargo_bars=2,
    )


def test_frozen_model_spec_tamper_refusal_and_flags() -> None:
    ds = _make_synthetic_signal_dataset(190)
    m = RidgeLinearModel(alpha=1.0).fit(ds)
    spec = m.to_frozen_spec(model_name="ridge-alpha", model_version="1.0.0")
    for k, v in RESEARCH_FLAGS.items():
        assert spec.to_dict()[k] is v
    assert spec.research_flags == RESEARCH_FLAGS

    with tempfile.TemporaryDirectory() as tmp:
        p = spec.save(Path(tmp) / "ridge.json")
        reloaded = Model.from_frozen_spec(p)
        np.testing.assert_allclose(m.predict(ds, "test").to_numpy(), reloaded.predict(ds, "test").to_numpy())

        # Tamper weight -> must raise SecurityRefusalError
        d_bad = json.loads(p.read_text(encoding="utf-8"))
        d_bad["weights"]["intercept"] += 0.01
        p.write_text(json.dumps(d_bad), encoding="utf-8")
        try:
            FrozenModelSpec.load(p)
            raise AssertionError("Expected SecurityRefusalError on tampered FrozenModelSpec")
        except SecurityRefusalError:
            pass


def test_ridge_linear_l2_huber_and_finetune_lineage() -> None:
    ds = _make_synthetic_signal_dataset(200)
    m_l2 = RidgeLinearModel(alpha=0.5, loss="l2").fit(ds)
    m_hub = RidgeLinearModel(alpha=0.5, loss="huber", huber_delta=0.01).fit(ds)

    # Signal coefficient on f_sig (index 0) must be positive in both L2 and Huber
    assert m_l2.coef_[0] > 0.0 and m_hub.coef_[0] > 0.0

    spec0 = m_hub.to_frozen_spec(model_name="huber-ft", model_version="0.1.0")
    m_hub.finetune(ds, finetune_alpha=10.0)
    spec1 = m_hub.to_frozen_spec(model_name="huber-ft", model_version="0.1.1")
    assert spec1.parent_model_sha256 == spec0.model_sha256


def test_direction_models_sparse_floor_calibration_b0_and_b2() -> None:
    ds = _make_synthetic_signal_dataset(210)

    # 1. Sparse event floor (< 8 events on f_d1) must raise SparseEventRefusalError!
    try:
        MultinomialDirectionModel(event_features=["f_d1"], min_event_count=8).fit(ds)
        raise AssertionError("Expected SparseEventRefusalError when f_d1 has < 8 events")
    except SparseEventRefusalError:
        pass

    # 2. Multinomial fit + valid temperature calibration + finetune
    mlogit = MultinomialDirectionModel(reg_lambda=1.0, calibrate_temperature=True).fit(ds)
    assert 0.25 <= mlogit.temperature_ <= 4.0
    p_m = mlogit.predict_proba(ds, "test")
    np.testing.assert_allclose(p_m.dropna().sum(axis=1).to_numpy(), 1.0, atol=1e-12)

    s0 = mlogit.to_frozen_spec(model_name="dir-mlogit", model_version="0.1.0")
    mlogit.finetune(ds, finetune_lambda=8.0)
    assert mlogit.parent_model_sha256_ == s0.model_sha256

    # 3. PriorFrequencyBaselineModel (B0) & MovingBlockBootstrapModel (B2)
    b0 = PriorFrequencyBaselineModel().fit(ds)
    p_b0 = b0.predict_proba(ds, "test")
    np.testing.assert_allclose(p_b0.dropna().sum(axis=1).to_numpy(), 1.0, atol=1e-12)

    b2 = MovingBlockBootstrapModel(
        lookback=16, block=2, horizon=2, paths=128, hurdle_bps=10, log_return_feature="f_roc1"
    ).fit(ds)
    p_b2 = b2.predict_proba(ds, "test")
    np.testing.assert_allclose(p_b2.dropna().sum(axis=1).to_numpy(), 1.0, atol=1e-12)


def test_hist_gbdt_nan_routing_multiclass_regression_and_cpp_parity() -> None:
    rng = np.random.default_rng(99)
    t0 = 1_700_000_000
    step = 3600
    n = 240
    x1 = rng.normal(0.0, 1.0, n)
    x2 = rng.normal(0.0, 1.0, n)
    # Make NaN on x1 strongly predictive of positive return so tree learns explicit NaN routing!
    nan_idx = np.arange(5, n, 7)
    x1_with_nan = x1.copy()
    x1_with_nan[nan_idx] = np.nan
    y_reg = np.where(np.isnan(x1_with_nan), 0.05, -0.02 * (x1 > 0.0) + 0.02 * (x2 > 0.0))
    y_cls = np.where(y_reg > 0.01, 0.0, np.where(y_reg < -0.01, 1.0, 2.0))

    idx = pd.MultiIndex.from_arrays(
        [[t0 + i * step for i in range(n)], ["KRW-BTC"] * n], names=["datetime", "instrument"]
    )
    cols = pd.MultiIndex.from_tuples(
        [
            ("feature", "x1"),
            ("feature", "x2"),
            ("label", "net_excess_return"),
            ("label", "direction_class"),
            ("meta", "label_end_utc"),
        ]
    )
    end_utc = np.array([float(t0 + (i + 1) * step) for i in range(n)])
    panel = pd.DataFrame(np.column_stack([x1_with_nan, x2, y_reg, y_cls, end_utc]), index=idx, columns=cols)
    dh = DataHandlerLP(data_loader=StaticDataLoader(panel), learn_processors=[DropnaLabelProcessor()])
    ds = DatasetH(
        handler=dh,
        segments={
            "train": (t0, t0 + 140 * step),
            "valid": (t0 + 142 * step, t0 + 185 * step),
            "test": (t0 + 187 * step, t0 + 238 * step),
        },
        embargo_bars=1,
    )

    prev_env = os.environ.get("QLIB_LAB_DISABLE_ACCEL")
    try:
        os.environ["QLIB_LAB_DISABLE_ACCEL"] = "0"
        _accel.verify_and_load_accel(force_reload=True)
        reg_cpp = HistGBDTModel(loss="regression", num_boost_round=25, max_depth=3, min_samples_leaf=5).fit(ds)
        cls_cpp = HistGBDTModel(loss="multiclass", num_boost_round=25, max_depth=3, min_samples_leaf=5).fit(ds)
        pred_reg_cpp = reg_cpp.predict(ds, "test")
        pred_cls_cpp = cls_cpp.predict_proba(ds, "test")

        os.environ["QLIB_LAB_DISABLE_ACCEL"] = "1"
        reg_np = HistGBDTModel(loss="regression", num_boost_round=25, max_depth=3, min_samples_leaf=5).fit(ds)
        cls_np = HistGBDTModel(loss="multiclass", num_boost_round=25, max_depth=3, min_samples_leaf=5).fit(ds)
        pred_reg_np = reg_np.predict(ds, "test")
        pred_cls_np = cls_np.predict_proba(ds, "test")

        np.testing.assert_allclose(pred_reg_cpp.to_numpy(), pred_reg_np.to_numpy(), rtol=1e-11, atol=1e-11)
        np.testing.assert_allclose(pred_cls_cpp.to_numpy(), pred_cls_np.to_numpy(), rtol=1e-11, atol=1e-11)

        # Verify NaN test rows received positive predictions without imputation!
        te_x = ds.prepare("test", col_set="feature", data_key=DataHandlerLP.DK_I)
        nan_te_mask = te_x["x1"].isna().to_numpy()
        assert np.any(nan_te_mask)
        assert float(pred_reg_cpp.to_numpy()[nan_te_mask].mean()) > 0.02

        # Verify FrozenModelSpec roundtrip & finetune
        spec = cls_cpp.to_frozen_spec(model_name="gbdt-nan", model_version="0.2.0")
        cls_loaded = Model.from_frozen_spec(spec)
        np.testing.assert_allclose(pred_cls_cpp.to_numpy(), cls_loaded.predict_proba(ds, "test").to_numpy())
        cls_loaded.finetune(ds, num_boost_round=6, leaf_shrinkage=0.85)
        assert cls_loaded.parent_model_sha256_ == spec.model_sha256
    finally:
        if prev_env is None:
            os.environ.pop("QLIB_LAB_DISABLE_ACCEL", None)
        else:
            os.environ["QLIB_LAB_DISABLE_ACCEL"] = prev_env
        _accel.verify_and_load_accel(force_reload=True)


def test_double_ensemble_and_causal_online_hedge_combiner() -> None:
    ds = _make_synthetic_signal_dataset(220)
    de = DoubleEnsembleModel(
        base_model_config={
            "class": "HistGBDTModel",
            "kwargs": {"loss": "multiclass", "num_boost_round": 15, "max_depth": 3, "min_samples_leaf": 5},
        },
        num_models=3,
        enable_sr=True,
        enable_fs=True,
        sample_ratios=(0.8, 0.6),
    ).fit(ds, reweighter=RegimeKernelReweighter(halflife_bars=50, anchor_bars=12))

    # Feature shrinkage must shrink sub_features across rounds!
    assert len(de.sub_features_[-1]) < len(de.sub_features_[0])
    spec = de.to_frozen_spec(model_name="double-ens", model_version="0.1.0")
    de_reloaded = Model.from_frozen_spec(spec)
    p_de = de.predict_proba(ds, "test")
    np.testing.assert_allclose(p_de.to_numpy(), de_reloaded.predict_proba(ds, "test").to_numpy())

    # Causal OnlineHedgeCombiner: verify open outcome windows (label_end_utc > as_of) NEVER affect weights at as_of!
    b0 = PriorFrequencyBaselineModel().fit(ds)
    p_b0 = b0.predict_proba(ds, "test")
    with authorized_eval_context("hedge_test"):
        raw_te = ds.handler.fetch(
            slice(ds.segments["test"][0], ds.segments["test"][1]),
            col_set=DataHandlerLP.CS_RAW,
            data_key=DataHandlerLP.DK_R,
        )
    y_cls = raw_te[("label", "direction_class")]
    # Set label_end_utc to 10 hours (~10 bars) after each bar so adjacent windows are still open!
    dts_ep = pd.Series(
        [float(ts.timestamp()) + 10 * 3600.0 for ts in raw_te.index.get_level_values("datetime")],
        index=raw_te.index,
    )

    hedge1 = OnlineHedgeCombiner(["de", "b0"], learning_rate=0.8, task_type="direction")
    _comb1, w_df1 = hedge1.combine({"de": p_de, "b0": p_b0}, y_cls, dts_ep)

    # Corrupt all labels whose label_end_utc > midpoint timestamp!
    mid_ts = w_df1.index[len(w_df1) // 2]
    mid_ep = float(mid_ts.timestamp())
    y_corrupted = y_cls.copy()
    open_at_mid = dts_ep > mid_ep
    y_corrupted.loc[open_at_mid] = 1.0 - np.minimum(y_corrupted.loc[open_at_mid].fillna(0.0), 1.0)

    hedge2 = OnlineHedgeCombiner(["de", "b0"], learning_rate=0.8, task_type="direction")
    _comb2, w_df2 = hedge2.combine({"de": p_de, "b0": p_b0}, y_corrupted, dts_ep)

    # Every Hedge weight up to and including mid_ts MUST be bit-for-bit identical!
    np.testing.assert_allclose(
        w_df1.loc[:mid_ts].to_numpy(),
        w_df2.loc[:mid_ts].to_numpy(),
        rtol=0.0,
        atol=0.0,
    )
