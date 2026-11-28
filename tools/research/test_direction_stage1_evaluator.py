"""Unit tests for direction_stage1_evaluator. Synthetic data only; network patched."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import random
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import direction_forecast_adapter as adapter
from tools.research.direction_feature_builder import build_feature_table
from tools.research import direction_stage1_evaluator as s1e
from tools.research._study_common import (
    RESEARCH_FLAGS,
    assert_all_isolation_invariants,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _seal_snap(snap: dict) -> dict:
    body = {k: v for k, v in snap.items() if k != "snapshot_sha256"}
    snap["snapshot_sha256"] = preview.model_id(body)
    return snap


def _coverage_table(study, history):
    return build_feature_table(market=study["market"], step_seconds=study["step_seconds"],
                               bars=history["bars"], feature_names=("P1",))


def _build_stage1_scenario(
    n_bars: int = 300,
    *,
    m_skill: bool = True,
    high_prob: str = "0.820000",
    low_prob: str = "0.080000",
) -> tuple[dict, dict, dict, dict, dict]:
    """Build synthetic Stage 1 bars, study config, and M / B1 / B0 snapshots."""
    step = 3600
    horizon = 7200
    t0 = 1_764_000_000
    scope = "synthetic-upbit-krw-spot"
    rng = random.Random(999)

    bars = []
    for i in range(n_bars):
        # 4-bar alternating regimes across both halves so 2-bar windows realize both up and down outcomes
        ret_bps = 35 if ((i - 1) // 4) % 2 == 0 else -35
        bars.append({"end": t0 + i * step, "known_at": t0 + i * step + 10, "return_bps": ret_bps})

    eval_start = bars[26]["end"]
    eval_end = bars[-1]["end"]
    frozen_at = eval_start - 600

    m_model = {"name": "dir-m", "version": "0.1.0", "sha256": "aa" * 32, "training_cutoff": frozen_at - 600, "frozen_at": frozen_at}
    b1_model = {"name": "dir-b1", "version": "0.1.0", "sha256": "bb" * 32, "training_cutoff": frozen_at - 600, "frozen_at": frozen_at}
    b0_model = {"name": "dir-b0", "version": "0.1.0", "sha256": "cc" * 32, "training_cutoff": frozen_at - 600, "frozen_at": frozen_at}

    neu_prob = f"{1.0 - float(high_prob) - float(low_prob):.6f}"
    m_forecasts = []
    b1_forecasts = []
    b0_forecasts = []

    for idx in range(26, n_bars - 2):
        as_of = bars[idx]["end"]
        issued = as_of + 30
        true_up = (bars[idx + 1]["return_bps"] + bars[idx + 2]["return_bps"]) > 20
        if m_skill:
            # ~82% calibrated accuracy matching high_prob = 0.82
            correct = rng.random() < 0.84
            call_up = true_up if correct else (not true_up)
        else:
            # Worse than B1
            call_up = not true_up

        m_probs = (
            {"up": high_prob, "down": low_prob, "neutral": neu_prob}
            if call_up
            else {"up": low_prob, "down": high_prob, "neutral": neu_prob}
        )
        m_forecasts.append({
            "market": "KRW-BTC",
            "as_of": as_of,
            "issued_at": issued,
            "horizon_seconds": horizon,
            "hurdle_bps": 15,
            "probabilities": m_probs,
            "direction": "up" if call_up else "down",
        })

        # B1: near-coin-flip directional calls
        b1_up = (idx % 3) == 0
        b1_probs = (
            {"up": "0.520000", "down": "0.440000", "neutral": "0.040000"}
            if b1_up
            else {"up": "0.440000", "down": "0.520000", "neutral": "0.040000"}
        )
        b1_forecasts.append({
            "market": "KRW-BTC",
            "as_of": as_of,
            "issued_at": issued,
            "horizon_seconds": horizon,
            "hurdle_bps": 15,
            "probabilities": b1_probs,
            "direction": "up" if b1_up else "down",
        })

        # B0: constant prior
        b0_forecasts.append({
            "market": "KRW-BTC",
            "as_of": as_of,
            "issued_at": issued,
            "horizon_seconds": horizon,
            "hurdle_bps": 15,
            "probabilities": {"up": "0.480000", "down": "0.470000", "neutral": "0.050000"},
            "direction": "up",
        })

    gen_at = bars[-1]["end"] + 60
    m_snap = _seal_snap({"format": adapter.FORMAT, "producer": "tradegen", "model": m_model, "generated_at": gen_at, "forecasts": m_forecasts})
    b1_snap = _seal_snap({"format": adapter.FORMAT, "producer": "tradegen", "model": b1_model, "generated_at": gen_at, "forecasts": b1_forecasts})
    b0_snap = _seal_snap({"format": adapter.FORMAT, "producer": "tradegen", "model": b0_model, "generated_at": gen_at, "forecasts": b0_forecasts})

    study = {
        "scope": scope,
        "rule_version": adapter.RULE,
        "source_id": "price-rec-v1",
        "market": "KRW-BTC",
        "forecast_model": {k: m_model[k] for k in ("name", "version", "sha256")},
        "b1_forecast_model": {k: b1_model[k] for k in ("name", "version", "sha256")},
        "b0_forecast_model": {k: b0_model[k] for k in ("name", "version", "sha256")},
        "evaluation_start": eval_start,
        "evaluation_end": eval_end,
        "step_seconds": step,
        "horizon_seconds": horizon,
        "hurdle_bps": 15,
        "confidence": "0.60",
        "min_validation_calls": 30,
        "max_calibration_gap": "0.15",
        "up_y": "0.04",
        "down_y": "0.02",
        "ceiling_y": "0.04",
        "criterion2_margin": 0.0,
        "bootstrap_replications": 2000,
        "bootstrap_seed": 777,
        "b2_seed": 42,
        "b2_paths": 200,
    }
    history = {"scope": scope, "source_id": "price-rec-v1", "bars": bars}
    return study, history, m_snap, b1_snap, b0_snap


class DirectionStage1EvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_bit_identical_criterion1_parity_with_direction_forecast_adapter(self) -> None:
        study, history, m_snap, b1_snap, b0_snap = _build_stage1_scenario(260, m_skill=True)
        # Drop a few forecasts so grid gaps & overlapping windows are exercised identically
        del m_snap["forecasts"][5]
        del m_snap["forecasts"][18]
        # Append two live post-window forecasts (one calling "up", one calling "down") so adapter reports holdout for each
        last_bar_end = history["bars"][-1]["end"]
        obs_up_now = last_bar_end + 100
        obs_down_now = last_bar_end + 200

        snap_up_probe = copy.deepcopy(m_snap)
        snap_up_probe["forecasts"].append({
            "market": "KRW-BTC",
            "as_of": last_bar_end,
            "issued_at": last_bar_end + 50,
            "horizon_seconds": 7200,
            "hurdle_bps": 15,
            "probabilities": {"up": "0.850000", "down": "0.050000", "neutral": "0.100000"},
            "direction": "up",
        })
        snap_up_probe["generated_at"] = last_bar_end + 60
        _seal_snap(snap_up_probe)

        snap_down_probe = copy.deepcopy(m_snap)
        snap_down_probe["forecasts"].append({
            "market": "KRW-BTC",
            "as_of": last_bar_end,
            "issued_at": last_bar_end + 50,
            "horizon_seconds": 7200,
            "hurdle_bps": 15,
            "probabilities": {"up": "0.050000", "down": "0.850000", "neutral": "0.100000"},
            "direction": "down",
        })
        snap_down_probe["generated_at"] = last_bar_end + 60
        _seal_snap(snap_down_probe)

        adapter_study = {
            k: study[k]
            for k in adapter.STUDY_KEYS
        }
        for direction, probe_snap, now_ts in (("up", snap_up_probe, obs_up_now), ("down", snap_down_probe, obs_down_now)):
            doc = {
                "schema": "tradegen-adaptive-bid-gap-replay-v1",
                "model": adapter_study,
                "terms": {
                    "scope": study["scope"],
                    "ceiling_y": "0.04",
                    "current_y": "0.03",
                    "model_sha256": preview.model_id(adapter_study),
                },
                "history": history,
                "observations": [{
                    "sequence": 1,
                    "as_of": now_ts,
                    "scope": study["scope"],
                    "last_trade_at": now_ts - 45,
                    "last_trade": "10000",
                    "bid_at": now_ts,
                    "bid": "9900",
                    "prior_block_active": False,
                    "floor_halt": False,
                    "daily_stop": False,
                }],
            }
            adapter_rep = adapter.run(doc, [probe_snap])
            self.assertEqual(adapter_rep["status"], "REPLAYED")
            adapter_holdout = adapter_rep["events"][0]["holdout"]

            _seal_snap(m_snap)
            s1_rep = s1e.evaluate_stage1(
                study=study,
                feature_table=_coverage_table(study, history),
                history=history,
                m_snapshots=[m_snap],
                b1_snapshots=[b1_snap],
                b0_snapshots=[b0_snap],
                evaluated_at=now_ts,
            )
            s1_dir = s1_rep["criterion1_M"]["directions"][direction]
            # Bit-for-bit equality across calls, hits, Wilson lower bound, and calibration gap!
            self.assertEqual(s1_dir["calls"], adapter_holdout["calls"])
            self.assertEqual(s1_dir["hits"], adapter_holdout["hits"])
            self.assertEqual(s1_dir["hit_lower_95"], adapter_holdout["hit_lower_95"])
            self.assertEqual(s1_dir["directional_calibration_gap"], adapter_holdout["directional_calibration_gap"])

    def test_pass_not_shown_inconclusive_interim_s2_and_void_outcomes(self) -> None:
        # 1. PASS outcome
        study, history, m_snap, b1_snap, b0_snap = _build_stage1_scenario(300, m_skill=True)
        rep_pass = s1e.evaluate_stage1(
            study=study,
            feature_table=_coverage_table(study, history),
            history=history,
            m_snapshots=[m_snap],
            b1_snapshots=[b1_snap],
            b0_snapshots=[b0_snap],
        )
        for k, v in RESEARCH_FLAGS.items():
            self.assertEqual(rep_pass[k], v)
        self.assertEqual(rep_pass["outcome"], "PASS")
        self.assertTrue(len(rep_pass["passing_directions"]) >= 1)
        self.assertFalse(rep_pass["b2_report"]["like_for_like_with_m"])

        # 2. --mode interim on skilled model -> CONTINUE (never spends alpha for PASS)
        rep_cont = s1e.evaluate_stage1(
            study=study,
            feature_table=_coverage_table(study, history),
            history=history,
            m_snapshots=[m_snap],
            b1_snapshots=[b1_snap],
            mode="interim",
        )
        self.assertEqual(rep_cont["outcome"], "CONTINUE")

        # 3. Unskilled M -> STOPPED (S2) in interim mode, NOT SHOWN in final mode
        study_bad, hist_bad, m_bad, b1_bad, b0_bad = _build_stage1_scenario(300, m_skill=False)
        rep_s2 = s1e.evaluate_stage1(
            study=study_bad,
            feature_table=_coverage_table(study, hist_bad),
            history=hist_bad,
            m_snapshots=[m_bad],
            b1_snapshots=[b1_bad],
            mode="interim",
        )
        self.assertEqual((rep_s2["outcome"], rep_s2["stop_rule"]), ("STOPPED", "S2"))

        rep_not_shown = s1e.evaluate_stage1(
            study=study_bad,
            feature_table=_coverage_table(study, hist_bad),
            history=hist_bad,
            m_snapshots=[m_bad],
            b1_snapshots=[b1_bad],
            b0_snapshots=[b0_bad],
            mode="final",
        )
        self.assertEqual(rep_not_shown["outcome"], "NOT SHOWN")

        # 4. S3 INCONCLUSIVE when min_validation_calls is unachievable
        study_s3 = dict(study, min_validation_calls=500)
        rep_s3 = s1e.evaluate_stage1(
            study=study_s3,
            feature_table=_coverage_table(study, history),
            history=history,
            m_snapshots=[m_snap],
            b1_snapshots=[b1_snap],
        )
        self.assertEqual((rep_s3["outcome"], rep_s3["stop_rule"]), ("INCONCLUSIVE", "S3"))

        # 5. S1 VOID when price bar has a gap
        hist_gap = copy.deepcopy(history)
        del hist_gap["bars"][50]
        rep_void = s1e.evaluate_stage1(
            study=study,
            history=hist_gap,
            m_snapshots=[m_snap],
            b1_snapshots=[b1_snap],
        )
        self.assertEqual((rep_void["outcome"], rep_void["stop_rule"]), ("VOID", "S1"))

        # 6. S4 STOPPED when model is unpinned
        study_s4 = copy.deepcopy(study)
        study_s4["forecast_model"]["version"] = "9.9.9"
        rep_s4 = s1e.evaluate_stage1(
            study=study_s4,
            feature_table=_coverage_table(study, history),
            history=history,
            m_snapshots=[m_snap],
            b1_snapshots=[b1_snap],
        )
        self.assertEqual((rep_s4["outcome"], rep_s4["stop_rule"]), ("STOPPED", "S4"))

    def test_cli_execution(self) -> None:
        study, history, m_snap, b1_snap, b0_snap = _build_stage1_scenario(260, m_skill=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            s_p = root / "study.json"
            h_p = root / "history.json"
            m_p = root / "m.json"
            b1_p = root / "b1.json"
            out_p = root / "stage1_report.json"
            s_p.write_text(json.dumps(study), encoding="utf-8")
            h_p.write_text(json.dumps(history), encoding="utf-8")
            m_p.write_text(json.dumps(m_snap), encoding="utf-8")
            b1_p.write_text(json.dumps(b1_snap), encoding="utf-8")

            cmd = [
                sys.executable, "-B", "-m", "tools.research.direction_stage1_evaluator",
                "--study", str(s_p),
                "--history", str(h_p),
                "--m-snapshot", f"{m_p}={m_snap['snapshot_sha256']}",
                "--b1-snapshot", f"{b1_p}={b1_snap['snapshot_sha256']}",
                "--output", str(out_p),
            ]
            proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out_p.is_file())


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
