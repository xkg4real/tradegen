"""Unit tests for direction_forecast_writer. Synthetic data only; network patched."""
from __future__ import annotations

import copy
from decimal import Decimal
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.research import direction_forecast_adapter as adapter
from tools.research import direction_forecast_writer as dfw
from tools.research import direction_model_fit as dmf
from tools.research.test_direction_model_fit import _make_synthetic_dataset
from tools.research._study_common import (
    RESEARCH_FLAGS,
    StudyError,
    assert_all_isolation_invariants,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class DirectionForecastWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_batch_and_live_writer_adapter_compatibility_omissions_and_non_revision(self) -> None:
        bars, ftable = _make_synthetic_dataset(320)
        train_start = bars[30]["end"]
        train_end = bars[220]["end"]
        frozen_at = train_end + 60

        fitted = dmf.fit_and_freeze_models(
            feature_table=ftable,
            bars=bars,
            train_start=train_start,
            train_end=train_end,
            frozen_at=frozen_at,
            horizon_seconds=7200,
            hurdle_bps=15,
        )
        model_m = fitted["M"]

        # Introduce 2 missing-feature bars in the evaluation portion (> frozen_at)
        eval_rows = [r for r in ftable["rows"] if r["as_of"] > frozen_at]
        eval_rows[3]["features"]["D2"] = None
        eval_rows[3]["complete"] = False
        eval_rows[7]["features"]["P1"] = None
        eval_rows[7]["complete"] = False
        ftable["table_sha256"] = dmf.sha256_ascii({k: v for k, v in ftable.items() if k != "table_sha256"})

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            idx_dir = root / "index"
            snap_path = root / "forecasts-001.json"
            write_ts = bars[-1]["end"] + 120

            snap, manifest, s_file, m_file = dfw.write_forecast_snapshot(
                snap_path,
                artifact=model_m,
                feature_table=ftable,
                issued_at=write_ts,
                mode="batch",
                index_dir=idx_dir,
            )
            self.assertTrue(s_file.is_file())
            self.assertTrue(m_file.is_file())
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(manifest[k], v)
            self.assertEqual(manifest["omitted_missing_features"], 2)

            # Verify adapter.read_snapshot accepts the published file & hash!
            read_back = adapter.read_snapshot(s_file, snap["snapshot_sha256"])
            self.assertEqual(read_back, snap)
            for f in snap["forecasts"]:
                probs = {k: Decimal(v) for k, v in f["probabilities"].items()}
                self.assertEqual(sum(probs.values()), Decimal("1"))

            # Live mode with skip_already_indexed=True skips already-emitted bars
            snap_live, man_live, _, _ = dfw.write_forecast_snapshot(
                root / "live-001.json",
                artifact=model_m,
                feature_table=ftable,
                issued_at=write_ts + 10,
                mode="live",
                index_dir=idx_dir,
                skip_already_indexed=True,
            )
            self.assertEqual(len(snap_live["forecasts"]), 0)
            self.assertEqual(man_live["skipped_already_indexed"], 1)

            # Attempting to revise an indexed forecast by changing features for the same (model, market, as_of, horizon) -> FORECAST_REVISED!
            ftable_tampered = copy.deepcopy(ftable)
            for r in ftable_tampered["rows"]:
                if r["as_of"] > frozen_at and r["complete"]:
                    r["features"]["D2"] = 999.0
                    break
            ftable_tampered["table_sha256"] = dmf.sha256_ascii({k: v for k, v in ftable_tampered.items() if k != "table_sha256"})
            with self.assertRaisesRegex(StudyError, "FORECAST_REVISED"):
                dfw.build_forecasts_from_model(
                    artifact=model_m,
                    feature_table=ftable_tampered,
                    issued_at=write_ts + 20,
                    index_dir=idx_dir,
                )

    def test_rounded_tie_omission_and_s4_definition_lock(self) -> None:
        bars, ftable = _make_synthetic_dataset(120)
        # Construct a B0 artifact with an exact rounded tie: up=0.400000, down=0.400000, neutral=0.200000
        b0_tie = dmf.seal_model_artifact({
            "format": dmf.MODEL_ARTIFACT_FORMAT,
            **RESEARCH_FLAGS,
            "name": "tie-b0",
            "version": "0.1.0",
            "role": "B0",
            "market": "KRW-BTC",
            "step_seconds": 3600,
            "horizon_seconds": 7200,
            "hurdle_bps": 15,
            "l2_penalty": 1.0,
            "classes": ["up", "down", "neutral"],
            "training_start": bars[26]["end"],
            "training_cutoff": bars[80]["end"],
            "frozen_at": bars[80]["end"] + 60,
            "n_training_rows": 50,
            "feature_builder_commit": ftable["feature_builder_commit"],
            "feature_names": [],
            "feature_definitions": ftable["feature_definitions"],
            "upstream_identities": ftable["upstream_identities"],
            "standardization": {"means": [], "deviations": []},
            "weights": {"prior_probabilities": {"up": 0.4, "down": 0.4, "neutral": 0.2}},
        })
        snap, manifest = dfw.build_forecasts_from_model(
            artifact=b0_tie,
            feature_table=ftable,
            issued_at=bars[-1]["end"] + 60,
        )
        self.assertEqual(snap["forecasts"], [])
        self.assertGreater(manifest["omitted_rounded_ties"], 0)

        # S4 check: changing feature_builder_commit in feature_table refuses forecast generation
        ftable_s4 = copy.deepcopy(ftable)
        ftable_s4["feature_builder_commit"] = "f" * 40
        ftable_s4["table_sha256"] = dmf.sha256_ascii({k: v for k, v in ftable_s4.items() if k != "table_sha256"})
        with self.assertRaisesRegex(StudyError, "S4_FROZEN_DEFINITION_CHANGED"):
            dfw.build_forecasts_from_model(
                artifact=b0_tie,
                feature_table=ftable_s4,
                issued_at=bars[-1]["end"] + 60,
            )

    def test_cli_end_to_end(self) -> None:
        bars, ftable = _make_synthetic_dataset(150)
        fitted = dmf.fit_and_freeze_models(
            feature_table=ftable,
            bars=bars,
            train_start=bars[26]["end"],
            train_end=bars[100]["end"],
            frozen_at=bars[100]["end"] + 30,
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            m_path = root / "model.json"
            f_path = root / "features.json"
            out_path = root / "snap.json"
            m_path.write_text(json.dumps(fitted["M"]), encoding="utf-8")
            f_path.write_text(json.dumps(ftable), encoding="utf-8")
            cmd = [
                sys.executable, "-B", "-m", "tools.research.direction_forecast_writer",
                "--model", str(m_path),
                "--expected-model-sha256", fitted["M"]["sha256"],
                "--features", str(f_path),
                "--issued-at", str(bars[-1]["end"] + 100),
                "--output", str(out_path),
            ]
            proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out_path.is_file())
            self.assertTrue((root / "snap.manifest.json").is_file())


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
