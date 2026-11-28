"""Coverage reads synthetic local hash chains; no feeds or user accounts are needed."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.research import didm_coverage as diag
from tools.research import didm_run_log as rl
from tools.research import direction_feature_builder as features
from tools.research._study_common import HashChainedLog, StudyError, UTC


CUT = int(datetime(2026, 11, 24, 12, tzinfo=UTC).timestamp())
AS_OF = "2026-11-24T12:00:00Z"


def add_receipts(log, offsets, known):
    for i in range(0, len(offsets), 8):
        stamps = [rl.slot_epoch_to_stamp(CUT - m*900) for m in offsets[i:i+8]]
        receipts = {s: f"GDELT files 2 ({s}:events, {s}:gkg), rows 0, new 0" for s in stamps}
        log.append({"kind": "collector_run", "collector_evidence": rl.COLLECTOR_EVIDENCE,
                    "started_at": known-1, "finished_at": known, "returncode": 0,
                    "slot_receipts": receipts, "target_slot": stamps[-1], "fetched_slots": [stamps[-1]],
                    "backfilled_slots": stamps[:-1], "sources_ok": {"gdelt": True}})


class CoverageTests(unittest.TestCase):
    def test_exact_639_including_all_96_can_cross_the_gate_before_7_days(self):
        with tempfile.TemporaryDirectory() as td:
            with HashChainedLog(td,rl.RUN_LOG_FILENAME) as log:
                add_receipts(log, list(range(1,639)), CUT-1)
                add_receipts(log, [639], CUT)
                head = log.head_sha256
            v=diag.coverage_report(td,as_of=AS_OF,pinned_head=head)
            self.assertTrue(v["slot_coverage_eligible"])
            self.assertEqual(v["last_24h"]["verified_by_cutoff"],96)
            self.assertEqual(v["last_7d"]["deficit_to_required"],0)
            self.assertEqual(v["last_7d"]["unresolved_at_cutoff"],33)
            self.assertEqual(v["last_7d"]["oldest_verified_slot_utc"],diag._utc(CUT-639*900))
            self.assertIsNone(v["d2_value"])
            self.assertIsNone(features.compute_d2_at([],rl.summarize_run_log(td)["slot_known_epoch"],CUT))
            self.assertEqual(v["price_features"]["status"],"NOT_SUPPLIED")
            self.assertFalse(v["live_eligible"])

    def test_638_even_with_a_full_day_does_not_meet_the_seven_day_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            with HashChainedLog(td, rl.RUN_LOG_FILENAME) as log:
                add_receipts(log, list(range(1, 639)), CUT)
            report = diag.coverage_report(td, as_of=AS_OF)
            self.assertEqual(report["last_7d"]["deficit_to_required"], 1)
            self.assertEqual(report["last_24h"]["deficit_to_required"], 0)
            self.assertFalse(report["slot_coverage_eligible"])

    def test_late_repair_and_one_missing_recent_slot_even_with_671_other_slots(self):
        with tempfile.TemporaryDirectory() as td:
            with HashChainedLog(td,rl.RUN_LOG_FILENAME) as log:
                add_receipts(log,list(range(2,673)),CUT)
                add_receipts(log,[1],CUT+1)
            v=diag.coverage_report(td,as_of="2026-11-24T12:49:59+00:00")
            self.assertEqual(v["hourly_decision_as_of"],diag._utc(CUT))
            self.assertFalse(v["slot_coverage_eligible"])
            self.assertEqual(v["last_7d"]["verified_by_cutoff"],671)
            self.assertEqual(v["last_24h"]["deficit_to_required"],1)
            later=diag.coverage_report(td,as_of="2026-11-24T13:00:00Z")
            self.assertEqual(later["last_24h"]["deficit_to_required"],4)

    def test_24h_by_itself_leaves_543_missing_and_empty_archive_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            v=diag.coverage_report(root,as_of=AS_OF)
            self.assertEqual(v["last_7d"]["deficit_to_required"],639)
            self.assertEqual(list(root.iterdir()),[])
            with HashChainedLog(root,rl.RUN_LOG_FILENAME) as log:
                add_receipts(log,list(range(1,97)),CUT)
            v=diag.coverage_report(root,as_of=AS_OF)
            self.assertFalse(v["slot_coverage_eligible"])
            self.assertEqual(v["last_24h"]["deficit_to_required"],0)
            self.assertEqual(v["last_7d"]["deficit_to_required"],543)
            with self.assertRaisesRegex(StudyError, "ARCHIVE_HEAD_MISMATCH"):
                diag.coverage_report(root,as_of=AS_OF,pinned_head="0"*64)

    def test_price_window_is_independent_and_only_includes_bars_known_by_decision(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with HashChainedLog(root,'bars.jsonl') as log:
                log.append({"kind":"config","schema":diag.prices.RECORDER_SCHEMA,
                            "config":{"market":"KRW-BTC","step_seconds":3600,"requests_per_second":2}})
                for m in range(24,0,-1):
                    t=CUT-m*3600
                    log.append({"kind":"bar","end":t,"known_at":t+1 if m!=24 else CUT+1,"return_bps":12})
                head=log.head_sha256
            p=subprocess.run([sys.executable,"-m","tools.research.didm_coverage","--log-dir",str(root),
                              "--as-of",AS_OF,"--price-archive",str(root),"--price-head",head],
                             capture_output=True,text=True,check=True)
            v=json.loads(p.stdout)
            self.assertEqual(v["price_features"]["verified_bars_by_cutoff"],23)
            self.assertEqual(v["price_features"]["available"],["P1","P2"])
            self.assertEqual(v["price_features"]["status"],"MISSING")
            self.assertFalse(v["slot_coverage_eligible"])


if __name__ == "__main__":
    unittest.main()
