"""Offline tests for the research-only direction forecast adapter (M11-T3). Synthetic data only."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import direction_forecast_adapter as adapter

ROOT = Path(__file__).resolve().parents[2]


def seal(snapshot):
    snapshot["snapshot_sha256"] = preview.model_id({k: v for k, v in snapshot.items() if k != "snapshot_sha256"})
    return snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.replay, self.snapshot = adapter.example()

    def test_example_snapshot_is_valid(self):
        self.assertEqual(adapter.check_snapshot(self.snapshot), self.snapshot)

    def test_bad_content_refuses_whole_file(self):
        cases = [
            (lambda s: s.update(format="other"), "SNAPSHOT_FORMAT"),
            (lambda s: s["forecasts"][0]["probabilities"].update(up="0.96"), "PROBABILITIES_NOT_ONE"),
            (lambda s: s["forecasts"][0].update(direction="down"), "DIRECTION_NOT_ARGMAX"),
            (lambda s: s["forecasts"][0].update(extra=1), "FORECAST_FORMAT"),
            (lambda s: s["forecasts"][0].update(issued_at=s["forecasts"][0]["as_of"] - 1), "FORECAST_TIME_ORDER"),
            (lambda s: s.update(generated_at=s["forecasts"][-1]["issued_at"] - 1), "FORECAST_TIME_ORDER"),
            (lambda s: s["model"].update(training_cutoff=s["model"]["frozen_at"] + 1), "MODEL_TIME_ORDER"),
            (lambda s: s["forecasts"][0].update(market="BTC"), "FORECAST_MARKET"),
            (lambda s: s["model"].pop("version"), "MODEL_FORMAT"),
        ]
        for change, reason in cases:
            with self.subTest(reason=reason):
                snapshot = copy.deepcopy(self.snapshot)
                change(snapshot)
                with self.assertRaisesRegex(preview.Invalid, reason):
                    adapter.check_snapshot(seal(snapshot))

    def test_hash_must_match_content_and_interface_note(self):
        edited = copy.deepcopy(self.snapshot)
        edited["forecasts"][0]["issued_at"] += 1
        with self.assertRaisesRegex(preview.Invalid, "SNAPSHOT_SHA256_MISMATCH"):
            adapter.check_snapshot(edited)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "forecasts.json"
            path.write_text(json.dumps(self.snapshot), encoding="utf-8")
            self.assertEqual(adapter.read_snapshot(path, self.snapshot["snapshot_sha256"]), self.snapshot)
            with self.assertRaisesRegex(preview.Invalid, "SNAPSHOT_SHA256_MISMATCH"):
                adapter.read_snapshot(path, "0" * 64)
            for bad in ('{"format":1,"format":2}', '{"format":NaN}'):
                path.write_text(bad, encoding="utf-8")
                with self.assertRaises(preview.Invalid):
                    adapter.read_snapshot(path, "0" * 64)

    def test_revision_and_mixed_model_versions_are_refused(self):
        self.assertEqual(len(adapter.merge([self.snapshot, copy.deepcopy(self.snapshot)])[1]),
                         len(self.snapshot["forecasts"]))
        revised = copy.deepcopy(self.snapshot)
        revised["forecasts"][0]["probabilities"] = {"up": "0.90", "down": "0.05", "neutral": "0.05"}
        with self.assertRaisesRegex(preview.Invalid, "FORECAST_REVISED"):
            adapter.merge([self.snapshot, seal(revised)])
        other = copy.deepcopy(self.snapshot)
        other["model"]["version"] = "0.0.2"
        with self.assertRaisesRegex(preview.Invalid, "MODEL_VERSION_MIXED"):
            adapter.merge([self.snapshot, seal(other)])

    def test_forecast_count_is_bounded_before_parsing_and_across_files(self):
        with unittest.mock.patch.object(adapter, "MAX_FORECASTS", len(self.snapshot["forecasts"])):
            adapter.merge([self.snapshot])
            with self.assertRaisesRegex(preview.Invalid, "SNAPSHOT_SIZE"):
                adapter.merge([self.snapshot, copy.deepcopy(self.snapshot)])
        with tempfile.TemporaryDirectory() as directory, \
                unittest.mock.patch.object(adapter, "MAX_FORECASTS", 2), \
                unittest.mock.patch.object(adapter.json, "loads", side_effect=AssertionError("parsed")):
            path = Path(directory) / "forecasts.json"
            path.write_text('{"forecasts":[' + ",".join(["{}"] * 1100) + "]}", encoding="utf-8")
            with self.assertRaisesRegex(preview.Invalid, "SNAPSHOT_SIZE"):
                adapter.read_snapshot(path, "0" * 64)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.replay, self.snapshot = adapter.example()
        self.config = self.replay["model"]
        self.live = self.snapshot["forecasts"][-1]

    def run_replay(self):
        seal(self.snapshot)
        self.replay["terms"]["model_sha256"] = preview.model_id(self.config)
        report = adapter.run(self.replay, [self.snapshot])
        for key, value in adapter.RESEARCH_FLAGS.items():
            self.assertEqual(report[key], value)
        return report

    def test_validated_up_forecast_widens_only_after_confirmation(self):
        report = self.run_replay()
        self.assertEqual(report["status"], "REPLAYED")
        events = report["events"]
        self.assertEqual([e["transition"] for e in events], ["AWAIT_WIDEN_CONFIRMATION", "WIDEN_FOR_NEXT"])
        self.assertEqual([e["used_y"] for e in events], ["0.02", "0.02"])
        self.assertEqual(events[0]["feature_cutoff"], self.live["as_of"])
        self.assertEqual(events[0]["model_sha256"], self.replay["terms"]["model_sha256"])

    def test_overlapping_forecasts_count_once_per_outcome_window(self):
        # 188 forecasts have matured, but their two-hour windows overlap hour by hour.
        holdout = self.run_replay()["events"][0]["holdout"]
        self.assertEqual((holdout["calls"], holdout["hits"]), (94, 94))

    def test_down_forecasts_tighten_for_next_observation(self):
        for bar in self.replay["history"]["bars"]:
            bar["return_bps"] *= -1
        for forecast in self.snapshot["forecasts"]:
            forecast.update(direction="down", probabilities={"up": "0.02", "down": "0.95", "neutral": "0.03"})
        event = self.run_replay()["events"][0]
        self.assertEqual((event["transition"], event["next_y"]), ("TIGHTEN_FOR_NEXT", "0.01"))

    def test_forecast_is_visible_only_from_issued_at(self):
        self.live["issued_at"] = self.replay["observations"][-1]["as_of"] + 1
        self.snapshot["generated_at"] = self.live["issued_at"]
        events = self.run_replay()["events"]
        self.assertEqual({e["feature_cutoff"] for e in events}, {self.live["as_of"] - 3600})

    def test_outcome_bars_published_after_the_observation_are_not_scored(self):
        # Bar 150 is published after both quotes, so the record known then stops at bar 149.
        self.replay["history"]["bars"][150]["known_at"] = self.replay["observations"][-1]["as_of"] + 1
        holdout = self.run_replay()["events"][0]["holdout"]
        self.assertEqual(holdout["calls"], 69)   # even as_of 10..146, windows ending by bar 148

    def test_expired_forecasts_are_not_used(self):
        later = self.live["as_of"] + 7200
        for i, observation in enumerate(self.replay["observations"]):
            now = later + i
            observation.update(as_of=now, bid_at=now, last_trade_at=now - 45)
        events = self.run_replay()["events"]
        self.assertEqual({e["snapshot_reason"] for e in events}, {"NO_LIVE_FORECAST"})
        self.assertEqual({e["transition"] for e in events}, {"KEEP"})

    def test_only_preregistered_window_counts_as_evidence(self):
        self.config["evaluation_start"] = self.live["as_of"] - 20 * 3600
        event = self.run_replay()["events"][0]
        self.assertLess(event["holdout"]["calls"], self.config["min_validation_calls"])
        self.assertEqual(event["snapshot_reason"], "DIRECTION_NOT_VALIDATED")
        self.config["evaluation_start"] = self.snapshot["model"]["frozen_at"]
        self.assertEqual(self.run_replay()["events"][0]["snapshot_reason"], "MODEL_NOT_FROZEN_BEFORE_EVALUATION")

    def test_study_pins_model_terms_and_envelope(self):
        self.config["forecast_model"]["version"] = "0.0.2"
        self.assertEqual(self.run_replay()["events"][0]["snapshot_reason"], "FORECAST_MODEL_NOT_PINNED")
        self.config["forecast_model"]["version"] = self.snapshot["model"]["version"]
        self.config["up_y"] = "0.06"
        self.assertEqual(self.run_replay()["events"][0]["snapshot_reason"], "DECIMAL_OUT_OF_RANGE")
        self.config["up_y"] = "0.03"
        seal(self.snapshot)
        self.replay["terms"]["model_sha256"] = "0" * 64
        report = adapter.run(self.replay, [self.snapshot])
        self.assertEqual(report["events"][0]["snapshot_reason"], "MODEL_NOT_BOUND")

    def test_existing_gap_and_block_rules_still_apply(self):
        self.replay["observations"][0]["bid"] = "9800"
        events = self.run_replay()["events"]
        self.assertEqual(events[0]["quote_state"], "BID_GAP_TRIGGERED")
        self.assertTrue(all(e["entry_block_latched"] and e["candidate_next_y"] is None for e in events))

    def test_forecast_off_the_bar_grid_refuses_the_study(self):
        # Main review PIT-1: as_of 1800 s into a bar with a two-bar horizon was scored on one bar
        # while its window was still open, and could be the live forecast at the same time.
        forecast = self.snapshot["forecasts"][-3]
        forecast.update(as_of=forecast["as_of"] + 1800, issued_at=forecast["as_of"] + 1860)
        events = self.run_replay()["events"]
        self.assertEqual({e["snapshot_reason"] for e in events}, {"FORECAST_OFF_BAR_GRID"})
        self.assertEqual({e["transition"] for e in events}, {"KEEP"})

    def test_horizon_must_be_whole_bars(self):
        self.config["horizon_seconds"] = 7300
        for forecast in self.snapshot["forecasts"]:
            forecast["horizon_seconds"] = 7300
        self.assertEqual(self.run_replay()["events"][0]["snapshot_reason"], "HORIZON_NOT_WHOLE_BARS")

    def test_bad_snapshot_rejects_the_replay(self):
        self.snapshot["forecasts"][0]["direction"] = "down"
        report = self.run_replay()
        self.assertEqual((report["status"], report["reason"], report["events"]), ("REJECTED", "DIRECTION_NOT_ARGMAX", []))


class BoundaryTests(unittest.TestCase):
    def test_cli_prints_research_flags_and_refuses_unannounced_hash(self):
        replay, snapshot = adapter.example()
        command = [sys.executable, "-B", "-m", "tools.research.direction_forecast_adapter"]
        with tempfile.TemporaryDirectory() as directory:
            replay_path, snapshot_path = Path(directory) / "study.json", Path(directory) / "forecasts.json"
            replay_path.write_text(json.dumps(replay), encoding="utf-8")
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            args = ["--replay", str(replay_path), "--snapshot"]
            done = subprocess.run(command + args + [f"{snapshot_path}={snapshot['snapshot_sha256']}"],
                                  cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            report = json.loads(done.stdout)
            self.assertEqual({k: report[k] for k in adapter.RESEARCH_FLAGS}, adapter.RESEARCH_FLAGS)
            refused = subprocess.run(command + args + [f"{snapshot_path}={'0' * 64}"],
                                     cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "core.compliance needs the app's PyYAML install")
    def test_d14_code_closure_does_not_include_research_tools(self):
        from core.compliance.owner import code_files
        self.assertEqual([path for path, _ in code_files(ROOT) if path.startswith("tools/research/")], [])


if __name__ == "__main__":
    unittest.main()
