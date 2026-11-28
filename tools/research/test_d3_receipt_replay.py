"""Exercise D3 delivery evidence and S4 through the actual research CLIs."""
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.research import didm_run_log, didm_source_bridge as bridge
from tools.research import direction_feature_builder as features
from tools.research._study_common import StudyError
from tools.research.test_didm_source_bridge import linked, row, score
from tools.research.test_direction_stage1_evaluator import _build_stage1_scenario


ROOT = Path(__file__).resolve().parents[2]


class D3ReceiptReplayTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.log = self.root / "log"
        self.src = row()
        self.clock = bridge.timestamp(self.src["received_at"])
        self.t = int(self.clock.timestamp())
        self.score = dict(score(self.src), event_type="monetary_policy")
        self.pin = {k: self.score[k] for k in ("model_version", "prompt_sha256")}

    def write(self, name, doc):
        path = self.root / (name + ".json")
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path

    def cli(self, module, args, status):
        p = subprocess.run([sys.executable, "-B", "-m", "tools.research." + module,
                            *[str(arg) for arg in args]], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(p.returncode, status, p.stdout + p.stderr)
        return json.loads(p.stdout)

    def iso(self, seconds):
        return (self.clock + timedelta(seconds=seconds)).isoformat()

    def export(self, source, *scores):
        return {"format": bridge.EXPORT_FORMAT, "contract": bridge.CONTRACT, "rows": [source],
                "scores": [linked(source, s) for s in scores]}

    def receipt(self, name, doc, when):
        path = self.write(name, doc)
        self.cli("didm_run_log", ["record-didm-export", "--log-dir", self.log, "--export", path,
                                  "--received-at", self.t + when], 0)
        return path

    def build(self, when, name, reason=None, log=None):
        end = self.t + when
        hist = self.write("price", [{"end": end, "known_at": end, "return_bps": 1}])
        out = self.root / (name + ".json")
        result = self.cli("direction_feature_builder",
                          ["--features", "D3", "--market", "KRW-BTC", "--step-seconds", "3600", "--history", hist,
                           "--didm-score-model", self.pin["model_version"], "--didm-score-prompt-sha256",
                           self.pin["prompt_sha256"], "--run-log-dir", log or self.log, "--output", out],
                          2 if reason else 0)
        if reason:
            self.assertEqual(result["reason"], reason)
            self.assertFalse(out.exists())
            return
        return json.loads(out.read_text())["rows"][0]["features"]["D3"]

    def test_strict_identity_drift_starts_at_effective_receipt_and_future_file_is_never_read(self):
        self.receipt("first", self.export(self.src, self.score), 0)
        foreign = dict(self.score, record_id="next", prompt_sha256="b" * 64, received_at=self.iso(8))
        second = self.receipt("second", self.export(self.src, foreign), 5)
        self.assertEqual(self.build(7, "known"), 70)
        self.build(8, "drift", "S4_UPSTREAM_IDENTITY_CHANGED")
        second.unlink()
        self.assertEqual(self.build(4, "before-delivery"), 70)

    def test_conflicting_source_metadata_in_both_orders_and_daily_resequencing(self):
        drift = dict(self.src, seq=77, valid_at=self.iso(-86400))
        for reverse in (False, True):
            self.log = self.root / ("log-" + str(reverse))
            a, b = (drift, self.src) if reverse else (self.src, drift)
            self.receipt("a", self.export(a, self.score), 0)
            self.receipt("b", self.export(b, self.score), 1)
            self.assertEqual(self.build(0, "past-" + str(reverse)), 70)
            self.build(1, "bad-" + str(reverse), "DIDM_CONFLICTING_DUPLICATE_VERSION")
        self.log = self.root / "resequence"
        self.receipt("seq-one", self.export(self.src, self.score), 0)
        self.receipt("seq-two", self.export(dict(self.src, seq=77), self.score), 1)
        self.assertEqual(self.build(2, "result"), 70)

    def test_late_score_for_retired_source_keeps_current_score(self):
        new = row(2, received=self.iso(2), value=90)
        self.receipt("old", self.export(self.src, self.score), 0)
        self.receipt("new", self.export(new, dict(self.score, received_at=self.iso(3))), 3)
        self.receipt("late", self.export(self.src, dict(self.score, received_at=self.iso(5))), 5)
        self.assertEqual(self.build(5, "latest"), 70)

    def test_audited_redelivery_refreshes_cadence_only_and_its_bytes_are_checked(self):
        doc = self.export(self.src, self.score)
        self.receipt("initial", doc, 0)
        self.write("unlogged-copy", doc)
        self.assertIsNone(self.build(90_001, "not-delivered"))
        second = self.receipt("next", doc, 90_000)
        self.assertIsNone(self.build(89_999, "before"))
        self.assertEqual(self.build(90_000, "after"), 50)
        self.assertEqual(self.build(0, "original"), 70)
        second.write_text(json.dumps(self.export(self.src)), encoding="utf-8")
        self.build(90_001, "changed", "DIDM_EXPORT_RECEIPT_HASH_MISMATCH")
        self.assertEqual(self.build(0, "past-safe"), 70)

    def test_late_first_delivery_does_not_backfill_earlier_bars(self):
        self.receipt("copy", self.export(self.src, self.score), 4)
        self.assertIsNone(self.build(3, "no-backfill"))
        self.assertEqual(self.build(4, "arrived"), 70)

    def test_prefix_pin_and_cutoff_exclude_later_chain_entries_independently(self):
        empty = self.export(self.src)
        self.receipt("first", empty, 1)
        summary = didm_run_log.summarize_run_log(self.log)
        self.receipt("second", empty, 2)
        self.assertEqual([r["received_at"] for r in features.logged_d3_receipts(self.log, summary, self.t + 2)],
                         [self.t + 1])
        with self.assertRaisesRegex(StudyError, "ARCHIVE_HEAD_MISMATCH"):
            features.logged_d3_receipts(self.log, dict(summary, entry_count=2), self.t + 2)
        current = didm_run_log.summarize_run_log(self.log)
        self.assertEqual(features.logged_d3_receipts(self.log, current, self.t), [])

    def test_repeated_delivery_of_foreign_model_still_stops_its_new_study_window(self):
        foreign = self.export(self.src, dict(self.score, model_version="foreign"))
        self.receipt("original", foreign, 0)
        self.assertIsNone(self.build(90_000, "before"))
        self.receipt("same-bytes", foreign, 90_001)
        self.build(90_002, "repeated", "S4_UPSTREAM_IDENTITY_CHANGED")

    def test_permissive_diagnostic_table_cannot_be_used_for_fit_or_scored_as_s1(self):
        diag = features.build_feature_table(
            market="KRW-BTC", step_seconds=3600, bars=[{"end": self.t, "known_at": self.t, "return_bps": 1}],
            feature_names=["D3"], didm_v0_exports=[(self.export(self.src, dict(self.score, model_version="other")), self.t)],
            pinned_didm_v0=self.pin, strict_s4=False)
        self.assertEqual(diag["unpinned_didm_score_count"], 1)
        with self.assertRaisesRegex(StudyError, "S4_UPSTREAM_IDENTITY_CHANGED"):
            features.verify_feature_table(diag)
        study, hist, m, b1, _ = _build_stage1_scenario(80, m_skill=True)
        output = self.root / "report.json"
        self.cli("direction_stage1_evaluator", [
            "--study", self.write("study", study), "--history", self.write("stage-bars", hist),
            "--features", self.write("diagnostic", diag),
            "--m-snapshot", str(self.write("m", m)) + "=" + m["snapshot_sha256"],
            "--b1-snapshot", str(self.write("b1", b1)) + "=" + b1["snapshot_sha256"], "--output", output], 0)
        result = json.loads(output.read_text())
        self.assertEqual((result["outcome"], result["stop_rule"], result["reason"]),
                         ("STOPPED", "S4", "S4_UPSTREAM_IDENTITY_CHANGED"))


if __name__ == "__main__":
    unittest.main()
