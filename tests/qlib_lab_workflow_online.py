"""Pillar 4 & Pillar 5 tests: Recorder (R), FamilyLedger N_eff, Gate Records, RollingGen/Trainer, Drift/Proposer, OnlineManager, Exporter & BR-26 Replay."""
from __future__ import annotations

import contextlib
import io
import json
import math
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from qlib_lab import RESEARCH_FLAGS, SecurityRefusalError
from qlib_lab.cli import main as cli_main
from qlib_lab.data import (
    DataHandlerLP,
    DatasetH,
    DropnaLabelProcessor,
    ExpressionDataLoader,
    PurgedHorizonReturnLabel,
    StandardZScoreNorm,
)
from qlib_lab.exceptions import PromotionGateRefusedError, SnapshotContractError
from qlib_lab.models import (
    FrozenModelSpec,
    HistGBDTModel,
    MovingBlockBootstrapModel,
    MultinomialDirectionModel,
    PriorFrequencyBaselineModel,
    RidgeLinearModel,
)
from qlib_lab.online import (
    DISCLAIMER_KO,
    DriftMonitor,
    OnlineManager,
    RevisionProposer,
    RollingGen,
    RollingTrainer,
    SnapshotExporter,
)
from qlib_lab.workflow import (
    DirectionGateRecord,
    PortfolioGateRecord,
    R,
    SignalRecord,
    register_trial_and_compute_neff,
)
from tools.research import adaptive_bid_gap_preview as br26_preview
from tools.research import adaptive_bid_gap_replay as br26_replay
from tools.research import direction_forecast_adapter as br26_adapter


def _run_cli_json(argv: list[str]) -> dict:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli_main(argv)
    assert rc == 0, f"cli_main({argv}) returned {rc}; stdout={buf.getvalue()}"
    out = json.loads(buf.getvalue())
    for k, v in RESEARCH_FLAGS.items():
        assert out[k] is v
    return out


def _build_strong_direction_study_data(n_bars: int = 260, step: int = 3600) -> tuple[pd.DataFrame, DatasetH, DatasetH]:
    """Build synthetic bar + news feature panel where Model M (prices + news) strongly beats B1 (prices only)."""
    rng = np.random.default_rng(777)
    t0 = 1_700_000_000
    rows = []
    px = 10000.0
    news_prev = 0.0
    for i in range(n_bars):
        # Outcome over next bar is strongly driven by news_prev, while i.i.d. news leaves price-only B1 uninformative
        rbps = int(round(65.0 * news_prev + rng.normal(0.0, 6.0)))
        px *= 1.0 + rbps / 10000.0
        # Generate next bar's news pulse (known at bar end)
        news_cur = float(rng.choice([-1.2, 0.0, 1.2], p=[0.28, 0.44, 0.28]))
        news_prev = news_cur
        end = t0 + i * step
        rows.append(
            {
                "datetime": end,
                "instrument": "KRW-BTC",
                "close": px,
                "return_bps": rbps,
                "news_pulse": news_cur,
                "known_at": end,
            }
        )
    raw = pd.DataFrame(rows)

    # Full dataset M (price + news)
    loader_m = ExpressionDataLoader(
        raw,
        feature_expressions={"p1": "ROC($close, 1)", "p4": "Std(ROC($close, 1), 6)", "d_news": "$news_pulse"},
        label_config=PurgedHorizonReturnLabel(horizon_bars=2, hurdle_bps=10, step_seconds=step),
        bar_lag=0,
    )
    dh_m = DataHandlerLP(data_loader=loader_m, learn_processors=[DropnaLabelProcessor()])
    segs = {
        "train": (t0 + 8 * step, t0 + 110 * step),
        "valid": (t0 + 113 * step, t0 + 145 * step),
        "test": (t0 + 148 * step, t0 + (n_bars - 3) * step),
    }
    ds_m = DatasetH(handler=dh_m, segments=segs, embargo_bars=2)

    # Price-only dataset B1
    loader_b1 = ExpressionDataLoader(
        raw,
        feature_expressions={"p1": "ROC($close, 1)", "p4": "Std(ROC($close, 1), 6)"},
        label_config=PurgedHorizonReturnLabel(horizon_bars=2, hurdle_bps=10, step_seconds=step),
        bar_lag=0,
    )
    dh_b1 = DataHandlerLP(data_loader=loader_b1, learn_processors=[DropnaLabelProcessor()])
    ds_b1 = DatasetH(handler=dh_b1, segments=segs, embargo_bars=2)
    return raw, ds_m, ds_b1


def test_recorder_zero_pickle_roundtrip_and_trusted_refusal() -> None:
    _raw, ds_m, _ds_b1 = _build_strong_direction_study_data(180)
    m = RidgeLinearModel(alpha=1.0).fit(ds_m)
    pred = m.predict(ds_m, "test")
    df_sample = pred.to_frame(name="alpha")
    arr_sample = np.arange(12, dtype=np.float64).reshape(3, 4)

    with tempfile.TemporaryDirectory() as tmp:
        uri = Path(tmp) / "mlruns_safe"
        with R.start(experiment_name="exp_unit", recorder_name="r1", uri=uri, run_utc="2026-11-27T00:00:00Z") as rec:
            rec.log_params(alpha=1.0, model="RidgeLinearModel")
            rec.log_metrics(ic=0.12)
            rec.set_tags(stage="research")
            rec.save_objects(
                model_art=m,
                pred_ser=pred,
                pred_df=df_sample,
                raw_arr=arr_sample,
                summary={"note": "clean"},
            )
            rid = rec.id

        loaded_rec = R.get_recorder(recorder_id=rid, experiment_name="exp_unit", uri=uri)
        meta = json.loads((loaded_rec.run_dir / "meta.json").read_text(encoding="utf-8"))
        for k, v in RESEARCH_FLAGS.items():
            assert meta[k] is v
        assert meta["status"] == "FINISHED"

        # Verify trusted=True is permanently refused!
        try:
            loaded_rec.load_object("model_art", trusted=True)
            raise AssertionError("Expected SecurityRefusalError when trusted=True")
        except SecurityRefusalError:
            pass

        m2 = loaded_rec.load_object("model_art")
        ser2 = loaded_rec.load_object("pred_ser")
        df2 = loaded_rec.load_object("pred_df")
        arr2 = loaded_rec.load_object("raw_arr")
        sum2 = loaded_rec.load_object("summary")

        np.testing.assert_allclose(m.predict(ds_m, "test").to_numpy(), m2.predict(ds_m, "test").to_numpy())
        np.testing.assert_allclose(pred.to_numpy(), ser2.to_numpy())
        np.testing.assert_allclose(df_sample.to_numpy(), df2.to_numpy())
        np.testing.assert_allclose(arr_sample, arr2)
        assert sum2["research_only"] is True and sum2["live_eligible"] is False


def test_family_ledger_bridge_hash_chain_and_cumulative_neff() -> None:
    rng = np.random.default_rng(321)
    dates = pd.date_range("2025-01-01", periods=60, freq="D", tz="UTC").strftime("%Y-%m-%d")
    s1 = pd.Series(rng.normal(0.001, 0.01, 60), index=dates)
    s1_dup = s1 * 1.0 + rng.normal(0.0, 1e-5, 60)  # Nearly identical -> 1 cluster
    s2_indep = pd.Series(rng.normal(0.0005, 0.01, 60), index=dates)  # Independent -> 2nd cluster!

    with tempfile.TemporaryDirectory() as tmp:
        ldir = Path(tmp) / "ledgers"
        m1 = register_trial_and_compute_neff(
            ledger_dir=ldir,
            family_id="FAM-TEST",
            rule="QLIB-R1",
            params={"lookback": 10},
            span=(dates[0], dates[-1]),
            market="KR",
            run_utc="2026-11-27T00:00:00Z",
            diff_series=s1,
            delta_sr=0.8,
        )
        assert m1.appended is True and m1.n_raw == 1 and m1.n_eff == 1.0

        # Duplicate configuration appends nothing (idempotent)
        m1_again = register_trial_and_compute_neff(
            ledger_dir=ldir,
            family_id="FAM-TEST",
            rule="QLIB-R1",
            params={"lookback": 10},
            span=(dates[0], dates[-1]),
            market="KR",
            run_utc="2026-11-27T01:00:00Z",
            diff_series=s1,
            delta_sr=0.8,
        )
        assert m1_again.appended is False and m1_again.n_raw == 1

        m2 = register_trial_and_compute_neff(
            ledger_dir=ldir,
            family_id="FAM-TEST",
            rule="QLIB-R1",
            params={"lookback": 11},
            span=(dates[0], dates[-1]),
            market="KR",
            run_utc="2026-11-27T02:00:00Z",
            diff_series=s1_dup,
            delta_sr=0.79,
        )
        assert m2.n_raw == 2 and m2.n_clusters == 1

        m3 = register_trial_and_compute_neff(
            ledger_dir=ldir,
            family_id="FAM-TEST",
            rule="QLIB-R1",
            params={"lookback": 50},
            span=(dates[0], dates[-1]),
            market="KR",
            run_utc="2026-11-27T03:00:00Z",
            diff_series=s2_indep,
            delta_sr=0.4,
        )
        assert m3.n_raw == 3 and m3.n_clusters == 2 and m3.n_eff >= 2.0


def test_signal_direction_and_portfolio_gate_records() -> None:
    _raw, ds_m, ds_b1 = _build_strong_direction_study_data(420)
    m = MultinomialDirectionModel(reg_lambda=0.5, calibrate_temperature=True).fit(ds_m)
    b1 = MultinomialDirectionModel(reg_lambda=0.5, calibrate_temperature=True).fit(ds_b1)
    b0 = PriorFrequencyBaselineModel().fit(ds_m)
    b2 = MovingBlockBootstrapModel(lookback=16, block=2, horizon=2, paths=100, hurdle_bps=10, log_return_feature="p1").fit(ds_b1)

    with tempfile.TemporaryDirectory() as tmp:
        uri = Path(tmp) / "gate_runs"
        with R.start(experiment_name="gates", uri=uri, run_utc="2026-11-27T00:00:00Z") as rec:
            sig_rep = SignalRecord(model=m, dataset=ds_m, recorder=rec).generate()
            assert sig_rep["IC"] > 0.3 and sig_rep["Q5_minus_Q1_spread"] > 0.0
            assert sig_rep["research_only"] is True

            dir_rep = DirectionGateRecord(
                model=m,
                baseline_b1=b1,
                baseline_b0=b0,
                baseline_b2=b2,
                dataset=ds_m,
                recorder=rec,
                horizon_bars=2,
                step_seconds=3600,
                hurdle_bps=10,
                confidence=0.58,
                min_validation_calls=12,
                max_calibration_gap=0.25,
                bootstrap_B=500,
                mcs_B=300,
            ).generate(proba_b1=b1.predict_proba(ds_b1, "test"), proba_b2=b2.predict_proba(ds_b1, "test"))
            assert dir_rep["outcome"] == "PASS", dir_rep
            assert dir_rep["criterion_2"]["passes"] is True
            assert dir_rep["criterion_2"]["dm_test"]["t"] < 0.0
            assert dir_rep["criterion_2"]["mcs"]["in_set"]["M"] is True
            assert dir_rep["criterion_4_passes"] is True

            port_card = PortfolioGateRecord(
                model=m,
                dataset=ds_m,
                recorder=rec,
                ledger_dir=Path(tmp) / "port_ledgers",
                family_id="FAM-PORT",
                market="KRW-BTC",
                cost_bps=10.0,
                w_is=80,
                w_oos=30,
                min_is=60,
                run_utc="2026-11-27T00:00:00Z",
            ).generate()
            assert port_card["decision"] in ("PASS", "REVISE", "REJECT", "INSUFFICIENT_DATA")
            assert "sr_stress_3x" in port_card["stats"]
            assert port_card["trials"]["ledger"]["n_raw"] == 1
            for k, v in RESEARCH_FLAGS.items():
                assert port_card[k] is v


def test_rolling_gen_rebinds_fit_windows_and_rolling_trainer_finetune_lineage() -> None:
    raw, _ds_m, _ds_b1 = _build_strong_direction_study_data(160)
    t0 = 1_700_000_000
    step = 3600

    loader = ExpressionDataLoader(
        raw,
        feature_expressions={"p1": "ROC($close, 1)", "d_news": "$news_pulse"},
        label_config=PurgedHorizonReturnLabel(horizon_bars=2, hurdle_bps=10, step_seconds=step),
        bar_lag=0,
    )
    dh = DataHandlerLP(
        data_loader=loader,
        infer_processors=[StandardZScoreNorm(fit_start_time=t0 + 5 * step, fit_end_time=t0 + 60 * step)],
        learn_processors=[DropnaLabelProcessor()],
    )
    cal = sorted(dh.fetch(col_set=DataHandlerLP.CS_RAW, data_key=DataHandlerLP.DK_I).index.get_level_values("datetime").unique())

    template = {
        "model": {"class": "HistGBDTModel", "kwargs": {"loss": "multiclass", "num_boost_round": 12, "max_depth": 3, "min_samples_leaf": 5}},
        "dataset": {
            "class": "DatasetH",
            "kwargs": {
                "handler": {
                    "class": "DataHandlerLP",
                    "kwargs": {
                        "infer_processors": [
                            {"class": "StandardZScoreNorm", "kwargs": {"fit_start_time": t0 + 5 * step, "fit_end_time": t0 + 60 * step}}
                        ],
                        "learn_processors": [{"class": "DropnaLabelProcessor", "kwargs": {}}],
                    },
                },
                "segments": {
                    "train": (t0 + 5 * step, t0 + 60 * step),
                    "valid": (t0 + 64 * step, t0 + 85 * step),
                    "test": (t0 + 90 * step, t0 + 150 * step),
                },
            },
        },
    }

    rgen = RollingGen(calendar=cal, step=20, rtype=RollingGen.ROLL_EX, embargo_bars=1, horizon_bars=2)
    tasks = rgen.generate(template)
    assert len(tasks) >= 3

    # Verify each rolling task rebound processor [fit_start_time, fit_end_time] strictly to its own train segment!
    prev_until = None
    for tk in tasks:
        tr_s, tr_e = tk["dataset"]["kwargs"]["segments"]["train"]
        proc_kw = tk["dataset"]["kwargs"]["handler"]["kwargs"]["infer_processors"][0]["kwargs"]
        assert proc_kw["fit_start_time"] == tr_s and proc_kw["fit_end_time"] == tr_e
        if prev_until is not None:
            assert prev_until <= tk["rolling_meta"]["active_from"]
        prev_until = tk["rolling_meta"]["active_until"]

    with tempfile.TemporaryDirectory() as tmp:
        trainer = RollingTrainer(
            uri=Path(tmp) / "rolling_runs",
            experiment_name="roll_ft",
            train_mode="finetune",
            run_utc="2026-11-27T00:00:00Z",
        )
        res = trainer.run(tasks, shared_handler=dh, finetune_kwargs={"num_boost_round": 6, "leaf_shrinkage": 0.9})
        assert len(res.frozen_specs) == len(tasks)
        assert res.frozen_specs[0].parent_model_sha256 is None
        for i in range(1, len(res.frozen_specs)):
            assert res.frozen_specs[i].parent_model_sha256 == res.frozen_specs[i - 1].model_sha256
        assert not res.oos_predictions.index.has_duplicates
        assert res.oos_probabilities is not None and len(res.oos_probabilities) == len(res.oos_predictions)


def test_drift_monitor_revision_proposer_and_online_manager_dossier() -> None:
    _raw, ds_m, _ds_b1 = _build_strong_direction_study_data(380)

    # Weak champion (extreme regularization -> near uniform) vs strong challenger
    champ_m = MultinomialDirectionModel(reg_lambda=5000.0, calibrate_temperature=False).fit(ds_m)
    chall_m = MultinomialDirectionModel(reg_lambda=0.2, calibrate_temperature=True).fit(ds_m)

    tc = ds_m.effective_training_cutoff(include_valid=True)
    champ_spec = champ_m.to_frozen_spec(model_name="champ-dir", model_version="0.1.0", training_cutoff=tc, frozen_at=tc + 60)
    chall_spec = chall_m.to_frozen_spec(model_name="chall-dir", model_version="0.2.0", training_cutoff=tc, frozen_at=tc + 60)

    tr_feat = ds_m.prepare("train", col_set="feature", data_key=DataHandlerLP.DK_I)
    dm = DriftMonitor(cusum_logloss_threshold=0.5).fit_reference(tr_feat, baseline_cond_logloss=0.35)

    # Verify PSI alert on shifted covariates
    shifted_feat = tr_feat.copy() + 5.0
    psi_rep = dm.evaluate(ds_m.segments["test"][1], current_features=shifted_feat)
    assert "covariate_shift_severe" in psi_rep["alerts"]

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # RevisionProposer writes .json and .yaml without auto_apply
        proposer = RevisionProposer(drift_report=psi_rep, gate_report={"revise_target": "execution"})
        base_task = {"model": {"class": "MultinomialDirectionModel", "kwargs": {"reg_lambda": 1.0}}, "dataset": {"kwargs": {}}}
        written = proposer.write_proposals(base_task, root / "proposals")
        assert len(written) >= 2
        for w in written:
            assert Path(w["json_path"]).is_file() and Path(w["yaml_path"]).is_file()
            assert w["proposal"]["auto_apply"] is False
            assert w["proposal"]["requires_owner_review"] is True

        # OnlineManager routine: Challenger beats Champion -> emits dossier WITHOUT silently replacing Champion!
        mgr = OnlineManager(
            state_dir=root / "online_mgr",
            champion_spec=champ_spec,
            challengers={"strong_chall": chall_spec},
            drift_monitor=dm,
            market="KRW-BTC",
            horizon_bars=2,
            step_seconds=3600,
            hurdle_bps=10,
        )
        as_of_end = ds_m.segments["test"][1]
        rout = mgr.routine(
            as_of_end,
            ds_m,
            evaluation_start=ds_m.segments["test"][0],
            run_utc="2026-11-27T00:00:00Z",
            confidence=0.58,
            min_validation_calls=10,
            max_calibration_gap=0.25,
            dsr_min=0.80,
            dm_p_max=0.10,
        )
        assert rout["n_open_windows_held_back"] >= 1, "Last bars whose label_end_utc > as_of must be held back!"
        assert len(rout["promotion_candidates"]) == 1
        assert mgr.champion_spec.model_sha256 == champ_spec.model_sha256, "Active Champion must NEVER swap silently!"

        dossier_path = Path(rout["promotion_dossier_paths"][0])
        try:
            mgr.apply_reviewed_promotion(dossier_path, explicit_offline_review_ack=False)
            raise AssertionError("Promotion without explicit_offline_review_ack must raise PromotionGateRefusedError")
        except PromotionGateRefusedError:
            pass

        promoted = mgr.apply_reviewed_promotion(dossier_path, explicit_offline_review_ack=True)
        assert promoted.model_sha256 == chall_spec.model_sha256


def test_snapshot_exporter_and_end_to_end_br26_adapter_replay_and_cli() -> None:
    step = 3600
    horizon_sec = 7200
    t0 = 1_700_000_000
    scope = "synthetic-qlib-upbit-krw-spot"

    # Build 180 contiguous bars where return_bps > +10 bps consistently so trained model confidently calls "up"
    bars = []
    panel_rows = []
    px = 50000.0
    for i in range(180):
        rbps = 22 + (i % 5) if (i % 9 != 0) else -18
        px *= 1.0 + rbps / 10000.0
        end = t0 + i * step
        ka = end + 20
        bars.append({"end": end, "known_at": ka, "return_bps": rbps})
        panel_rows.append(
            {
                "datetime": end,
                "instrument": "KRW-BTC",
                "close": px,
                "return_bps": rbps,
                "known_at": ka,
            }
        )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        panel_path = root / "bars_panel.json"
        panel_path.write_text(json.dumps(panel_rows), encoding="utf-8")

        task_cfg = {
            "model_name": "qlib-mlogit-btc",
            "model_version": "0.1.0",
            "model": {
                "class": "MultinomialDirectionModel",
                "kwargs": {"reg_lambda": 0.5, "calibrate_temperature": False},
            },
            "dataset": {
                "class": "DatasetH",
                "kwargs": {
                    "handler": {
                        "class": "DataHandlerLP",
                        "kwargs": {
                            "data_loader": {
                                "class": "ExpressionDataLoader",
                                "kwargs": {
                                    "feature_expressions": {
                                        "p1": "ROC($close, 1)",
                                        "p2": "ROC($close, 4)",
                                    },
                                    "label_config": {
                                        "class": "PurgedHorizonReturnLabel",
                                        "kwargs": {"horizon_bars": 2, "hurdle_bps": 10, "step_seconds": step},
                                    },
                                    "bar_lag": 1,
                                    "on_lag_violation": "nan",
                                },
                            },
                            "learn_processors": [{"class": "DropnaLabelProcessor", "kwargs": {}}],
                        },
                    },
                    "segments": {
                        "train": [t0 + 6 * step, t0 + 70 * step],
                        "test": [t0 + 75 * step, t0 + 179 * step],
                    },
                    "embargo_bars": 2,
                },
            },
            "record": [{"class": "SignalRecord", "kwargs": {}}],
        }
        cfg_path = root / "task.json"
        cfg_path.write_text(json.dumps(task_cfg), encoding="utf-8")

        # 1. Run CLI `qrun`
        state_dir = root / "state"
        qrun_out = _run_cli_json(
            [
                "qrun",
                "--config",
                str(cfg_path),
                "--panel",
                str(panel_path),
                "--state-dir",
                str(state_dir),
                "--run-utc",
                "2026-11-27T00:00:00Z",
            ]
        )
        assert qrun_out["schema"] == "tradegen-qlib-cli-qrun-v1"
        exp_runs = sorted((state_dir / "experiments" / "qrun_exp").iterdir())
        frozen_model_file = exp_runs[0] / "artifacts" / "frozen_model.model.json"
        spec = FrozenModelSpec.load(frozen_model_file)

        # 2. Run CLI `export-snapshot` -> writes .json + .manifest.json + .interface_note.md
        snap_path = root / "exports" / "forecasts-001.json"
        exp_out = _run_cli_json(
            [
                "export-snapshot",
                "--frozen-model",
                str(frozen_model_file),
                "--config",
                str(cfg_path),
                "--panel",
                str(panel_path),
                "--output",
                str(snap_path),
                "--producer",
                "qlib-lab",
                "--horizon-seconds",
                str(horizon_sec),
                "--hurdle-bps",
                "10",
            ]
        )
        assert exp_out["schema"] == "tradegen-qlib-cli-export-v1"
        manifest = json.loads(snap_path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
        note_md = snap_path.with_suffix(".interface_note.md").read_text(encoding="utf-8")
        assert note_md.strip().endswith(DISCLAIMER_KO)
        for k, v in RESEARCH_FLAGS.items():
            assert manifest[k] is v
        snap_sha = manifest["snapshot_sha256"]

        # 3. Verify non-revision index: identical re-export succeeds; conflicting probability raises SnapshotContractError!
        loaded_snap = br26_adapter.read_snapshot(snap_path, snap_sha)
        exporter = SnapshotExporter(
            producer="qlib-lab",
            horizon_seconds=horizon_sec,
            hurdle_bps=10,
            index_path=snap_path.parent / "non_revision_index.jsonl",
        )
        # Conflicting probability for an existing (model_sha256, market, as_of, horizon_seconds) key -> refused!
        bad_idx = pd.MultiIndex.from_tuples(
            [(loaded_snap["forecasts"][0]["as_of"], "KRW-BTC")], names=["datetime", "instrument"]
        )
        bad_proba = pd.DataFrame([[0.10, 0.80, 0.10]], index=bad_idx, columns=["up", "down", "neutral"])
        try:
            exporter.export(frozen_spec=spec, probabilities=bad_proba, output_path=root / "exports" / "bad_rev.json")
            raise AssertionError("Expected SnapshotContractError on revised forecast")
        except SnapshotContractError as exc:
            assert "FORECAST_REVISED" in str(exc)

        # Also verify exact tie omission (0.40, 0.40, 0.20 -> omitted_ties == 1)
        tie_idx = pd.MultiIndex.from_tuples([(t0 + 250 * step, "KRW-BTC")], names=["datetime", "instrument"])
        tie_proba = pd.DataFrame([[0.40, 0.40, 0.20]], index=tie_idx, columns=["up", "down", "neutral"])
        tie_res = exporter.export(frozen_spec=spec, probabilities=tie_proba, output_path=root / "exports" / "tie.json")
        assert tie_res["manifest"]["counts"]["omitted_ties"] == 1
        assert len(tie_res["snapshot"]["forecasts"]) == 0

        # 4. Feed exported snapshot DIRECTLY through `tools.research.direction_forecast_adapter.run()` AND CLI `replay-br26`!
        study = {
            "scope": scope,
            "rule_version": br26_adapter.RULE,
            "source_id": "synthetic-qlib-hourly-v1",
            "market": "KRW-BTC",
            "forecast_model": {"name": spec.model_name, "version": spec.model_version, "sha256": spec.model_sha256},
            "evaluation_start": t0 + 75 * step,
            "step_seconds": step,
            "horizon_seconds": horizon_sec,
            "hurdle_bps": 10,
            "confidence": "0.65",
            "min_validation_calls": 16,
            "max_calibration_gap": "0.20",
            "up_y": "0.03",
            "down_y": "0.01",
        }
        obs_times = (bars[-1]["end"] + 120, bars[-1]["end"] + 600)
        observations = [
            {
                "sequence": i + 1,
                "as_of": now_t,
                "scope": scope,
                "last_trade_at": now_t - 20,
                "last_trade": "10000",
                "bid_at": now_t,
                "bid": "9950",
                "prior_block_active": False,
                "floor_halt": False,
                "daily_stop": False,
            }
            for i, now_t in enumerate(obs_times)
        ]
        study_doc = {
            "schema": br26_replay.SCHEMA,
            "model": study,
            "observations": observations,
            "terms": {
                "scope": scope,
                "ceiling_y": "0.05",
                "current_y": "0.02",
                "model_sha256": br26_preview.model_id(study),
            },
            "history": {"scope": scope, "source_id": study["source_id"], "bars": bars},
        }
        study_path = root / "study.json"
        study_path.write_text(json.dumps(study_doc), encoding="utf-8")

        replay_report = br26_adapter.run(study_doc, [loaded_snap])
        assert replay_report["status"] == "REPLAYED", replay_report
        assert replay_report["final_working_y"] == "0.03"
        assert [ev["transition"] for ev in replay_report["events"]] == ["AWAIT_WIDEN_CONFIRMATION", "WIDEN_FOR_NEXT"]
        for k, v in RESEARCH_FLAGS.items():
            assert replay_report[k] is v

        cli_replay = _run_cli_json(
            [
                "replay-br26",
                "--replay",
                str(study_path),
                "--snapshot",
                f"{snap_path}={snap_sha}",
            ]
        )
        assert cli_replay["status"] == "REPLAYED" and cli_replay["final_working_y"] == "0.03"

        # 5. Also verify CLI `propose-revision`, `rolling`, and `routine` exit 0 cleanly
        cli_prop = _run_cli_json(["propose-revision", "--task", str(cfg_path), "--output-dir", str(root / "cli_props")])
        assert cli_prop["schema"] == "tradegen-qlib-cli-proposals-v1" and cli_prop["n_proposals"] >= 1
        cli_roll = _run_cli_json(
            [
                "rolling",
                "--config",
                str(cfg_path),
                "--panel",
                str(panel_path),
                "--state-dir",
                str(state_dir),
                "--step",
                "40",
                "--run-utc",
                "2026-11-27T00:00:00Z",
            ]
        )
        assert cli_roll["n_windows"] >= 1
        cli_rout = _run_cli_json(
            [
                "routine",
                "--config",
                str(cfg_path),
                "--panel",
                str(panel_path),
                "--champion",
                str(frozen_model_file),
                "--state-dir",
                str(root / "cli_routine"),
                "--as-of",
                str(t0 + 170 * step),
                "--run-utc",
                "2026-11-27T00:00:00Z",
            ]
        )
        assert (
            cli_rout["schema"] == "tradegen-qlib-online-routine-v1"
            and cli_rout["active_champion_sha256"] == spec.model_sha256
        )
