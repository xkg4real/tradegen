"""Unit tests for direction_model_fit. Synthetic data only; network patched."""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import random
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.research import direction_feature_builder as dfb
from tools.research import direction_model_fit as dmf
from tools.research._study_common import (
    RESEARCH_FLAGS,
    StudyError,
    assert_all_isolation_invariants,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_synthetic_dataset(
    n_bars: int = 800,
    *,
    include_d1: bool = False,
    d1_events_count: int = 0,
    missing_indices: set[int] = frozenset(),
) -> tuple[list[dict], dict]:
    step = 3600
    t0 = 1_764_000_000
    rng = random.Random(12345)
    signals = [rng.gauss(0.0, 1.0) for _ in range(n_bars)]

    bars = []
    for i in range(n_bars):
        # Future 2-bar return correlates with earlier signal so M has genuine directional skill over B1
        prev_sig = signals[max(0, i - 1)]
        ret_bps = int(round(20.0 * prev_sig + rng.gauss(0.0, 15.0)))
        bars.append({"end": t0 + i * step, "known_at": t0 + i * step + 5, "return_bps": ret_bps})

    fnames = ["P1", "P2", "P3", "P4", "D2"] + (["D1"] if include_d1 else [])
    rows = []
    for i in range(25, n_bars):
        as_of = bars[i]["end"]
        p_feats = dfb.compute_price_features_at({b["end"]: b for b in bars}, as_of, step)
        if i in missing_indices:
            feat = {f: None for f in fnames}
            complete = False
        else:
            feat = {
                **p_feats,
                "D2": 1.0 + 0.5 * signals[i],
            }
            if include_d1:
                feat["D1"] = 0.0
            complete = all(feat[f] is not None for f in fnames)
        rows.append({"as_of": as_of, "features": feat, "complete": complete})

    d1_ev_list = [
        {"series": "alfred:CPIAUCSL", "source_id": "alfred", "item_id": f"ev-{k}", "payload_sha256": "a" * 64,
         "received_utc": "2026-11-24T00:00:00+00:00", "event_epoch": t0 + (40 + k * 50) * step, "is_revision": False}
        for k in range(d1_events_count)
    ]

    ftable = {
        "format": dfb.FEATURE_TABLE_FORMAT,
        **RESEARCH_FLAGS,
        "market": "KRW-BTC",
        "step_seconds": step,
        "feature_names": fnames,
        "feature_definitions": {
            "d1_series": list(dfb.DEFAULT_D1_SERIES) if include_d1 else [],
            "d3_event_types": [],
            "q1_event_types": [],
            "d1_schedule_window_seconds": 3600,
            "d3_cadence_seconds": 0,
            "q1_cadence_seconds": 0,
        },
        "upstream_identities": {"didm_v0": None, "quantgpt": None},
        "feature_builder_commit": "1" * 40,
        "unpinned_didm_score_count": 0,
        "d1_events": d1_ev_list,
        "row_count": len(rows),
        "complete_row_count": sum(1 for r in rows if r["complete"]),
        "missing_row_count": sum(1 for r in rows if not r["complete"]),
        "rows": rows,
    }
    ftable["table_sha256"] = dmf.sha256_ascii(ftable)
    return bars, ftable


class DirectionModelFitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_fit_m_b1_b0_purging_and_m11_t4_heldout_estimator(self) -> None:
        bars, ftable = _make_synthetic_dataset(750)
        train_start = bars[30]["end"]
        train_end = bars[710]["end"]
        frozen_at = train_end + 600

        res1 = dmf.fit_and_freeze_models(
            feature_table=ftable,
            bars=bars,
            train_start=train_start,
            train_end=train_end,
            frozen_at=frozen_at,
            horizon_seconds=7200,
            hurdle_bps=15,
            l2_penalty=1.0,
        )
        for role in ("M", "B1", "B0"):
            art = res1[role]
            self.assertEqual(dmf.verify_model_artifact(art), art)
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(art[k], v)
            self.assertEqual(art["training_cutoff"], train_end)
            self.assertLess(art["training_cutoff"], art["frozen_at"])

        # Purging check: mutating bars strictly AFTER train_end must NOT alter M, B1, or B0 sha256!
        bars_mut = copy.deepcopy(bars)
        for b in bars_mut:
            if b["end"] > train_end:
                b["return_bps"] = 9999
        res2 = dmf.fit_and_freeze_models(
            feature_table=ftable,
            bars=bars_mut,
            train_start=train_start,
            train_end=train_end,
            frozen_at=frozen_at,
            horizon_seconds=7200,
            hurdle_bps=15,
            l2_penalty=1.0,
        )
        self.assertEqual(res1["M"]["sha256"], res2["M"]["sha256"])
        self.assertEqual(res1["B1"]["sha256"], res2["B1"]["sha256"])
        self.assertEqual(res1["B0"]["sha256"], res2["B0"]["sha256"])

        # M11-T4 call-count estimator ran on held-out final week (~168 bars -> ~84 non-overlapping 2h windows)
        est = res1["report"]["m11_t4_call_estimate"]
        self.assertTrue(est["available"])
        self.assertGreater(est["nonoverlap_windows"], 70)
        self.assertLessEqual(est["nonoverlap_windows"], 85)
        self.assertIn("0.60", est["by_confidence"])

    def test_s1_missing_threshold_and_d1_minimum_events_gate(self) -> None:
        # > 5% missing rows in [train_start, train_end - horizon] -> S1_MISSING_FEATURES_EXCEED_5PCT
        missing_set = set(range(40, 65))  # 25 missing out of ~300 rows > 8%
        bars, ftable_miss = _make_synthetic_dataset(360, missing_indices=missing_set)
        with self.assertRaisesRegex(StudyError, "S1_MISSING_FEATURES_EXCEED_5PCT"):
            dmf.fit_and_freeze_models(
                feature_table=ftable_miss,
                bars=bars,
                train_start=bars[30]["end"],
                train_end=bars[330]["end"],
                frozen_at=bars[330]["end"] + 60,
            )

        # D1 with 7 events (< 8) -> D1_INSUFFICIENT_EVENTS
        bars7, ftable_d1_7 = _make_synthetic_dataset(600, include_d1=True, d1_events_count=7)
        with self.assertRaisesRegex(StudyError, "D1_INSUFFICIENT_EVENTS"):
            dmf.fit_and_freeze_models(
                feature_table=ftable_d1_7,
                bars=bars7,
                train_start=bars7[30]["end"],
                train_end=bars7[550]["end"],
                frozen_at=bars7[550]["end"] + 60,
            )

        # D1 with 8 events -> succeeds!
        bars8, ftable_d1_8 = _make_synthetic_dataset(600, include_d1=True, d1_events_count=8)
        ok_fit = dmf.fit_and_freeze_models(
            feature_table=ftable_d1_8,
            bars=bars8,
            train_start=bars8[30]["end"],
            train_end=bars8[550]["end"],
            frozen_at=bars8[550]["end"] + 60,
        )
        self.assertEqual(ok_fit["report"]["d1_event_count"], 8)

    def test_cli_publishes_frozen_artifacts_atomically(self) -> None:
        bars, ftable = _make_synthetic_dataset(300)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f_path = root / "features.json"
            h_path = root / "history.json"
            out_dir = root / "frozen"
            f_path.write_text(json.dumps(ftable), encoding="utf-8")
            h_path.write_text(json.dumps({"bars": bars}), encoding="utf-8")

            cmd = [
                sys.executable, "-B", "-m", "tools.research.direction_model_fit",
                "--features", str(f_path),
                "--history", str(h_path),
                "--train-start", str(bars[30]["end"]),
                "--train-end", str(bars[280]["end"]),
                "--frozen-at", str(bars[280]["end"] + 120),
                "--output-dir", str(out_dir),
            ]
            proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            for fname in ("model_M.json", "model_B1.json", "model_B0.json", "fit_report.json"):
                self.assertTrue((out_dir / fname).is_file())


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
