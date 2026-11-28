"""Unit tests for didm_run_log. Synthetic data only; network patched."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.research import didm_run_log as rl
from tools.research import didm_source_bridge as bridge
from tools.research import quantgpt_feature_bridge as qfb
from tools.research._study_common import (
    RESEARCH_FLAGS,
    StudyError,
    assert_all_isolation_invariants,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _init_didm_sqlite(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(bridge.ITEMS_SQL)
        conn.execute("CREATE INDEX items_received ON items (received_at)")
        conn.execute("CREATE INDEX items_key ON items (source_id, item_id, received_at)")
        conn.commit()
    finally:
        conn.close()


def _insert_didm_row(
    db_path: Path,
    *,
    source_id: str = "gdelt-events2",
    item_id: str = "20261124120000:ev1",
    kind: str = "gdelt_event",
    published_at: str = "2026-11-24T12:00:00+00:00",
    valid_at: str = "2026-11-24T12:00:00+00:00",
    received_at: str = "2026-11-24T12:02:00+00:00",
    payload_obj: dict | None = None,
) -> dict:
    if not db_path.exists():
        _init_didm_sqlite(db_path)
    payload_str = bridge.canonical(payload_obj or {"slot": item_id[:14], "tone": -1.5})
    payload_sha = bridge.sha256(payload_str.encode("utf-8"))
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO items (source_id,item_id,kind,published_at,valid_at,received_at,payload,payload_sha256) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (source_id, item_id, kind, published_at, valid_at, received_at, payload_str, payload_sha),
        )
        seq = cur.lastrowid
        conn.commit()
    finally:
        conn.close()
    row = {
        "seq": seq,
        "source_id": source_id,
        "item_id": item_id,
        "kind": kind,
        "published_at": published_at,
        "valid_at": valid_at,
        "received_at": received_at,
        "payload": payload_str,
        "payload_sha256": payload_sha,
    }
    return row


class DidmRunLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_collector_slot_tracking_exit0_source_failure_and_backfill(self) -> None:
        # 2026-11-24T12:02:00Z -> slot 20261124120000 (epoch 1763985600)
        slot1_ep = rl.stamp_to_slot_epoch("20261124120000")
        slot2_ep = slot1_ep + 900  # 20261124121500
        slot1_stamp = rl.slot_epoch_to_stamp(slot1_ep)
        slot2_stamp = rl.slot_epoch_to_stamp(slot2_ep)

        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "logs"
            stores = Path(tmp) / "stores"

            # Run 1: collector exits 0, but GDELT fails and ECOS fails! Only ALFRED succeeds.
            def runner_1(store_path: Path, target_stamp: str, backfills: list[str]) -> rl.CollectorExecResult:
                self.assertEqual(target_stamp, slot1_stamp)
                self.assertEqual(list(backfills), [])
                _insert_didm_row(
                    store_path,
                    source_id="alfred",
                    item_id="CPIAUCSL:2026-10",
                    kind="alfred_vintage",
                    payload_obj={"series_id": "CPIAUCSL", "value": "315.2"},
                )
                stdout = ("GDELT failed at lastupdate: TimeoutError\n"
                          "ALFRED CPIAUCSL: vintage rows 1, new 1\n"
                          "ECOS failed: TimeoutError")
                return rl.CollectorExecResult(0, stdout)

            r1 = rl.run_collector_once(
                log_dir,
                stores,
                started_at=slot1_ep + 120,
                finished_at=slot1_ep + 135,
                collector_runner=runner_1,
            )
            self.assertEqual(r1["sources_ok"], {"gdelt": False, "alfred": True, "ecos": False})
            self.assertEqual(r1["missing_slots"], [slot1_stamp])
            self.assertEqual(r1["fetched_slots"], [])

            # Run 2 (15m later): fetches slot2 AND backfills slot1!
            def runner_2(store_path: Path, target_stamp: str, backfills: list[str]) -> rl.CollectorExecResult:
                self.assertEqual(target_stamp, slot2_stamp)
                self.assertEqual(list(backfills), [slot1_stamp])
                _insert_didm_row(store_path, item_id=f"{slot1_stamp}:ev1", received_at="2026-11-24T12:17:10+00:00")
                _insert_didm_row(store_path, item_id=f"{slot2_stamp}:ev2", received_at="2026-11-24T12:17:10+00:00")
                stdout = (f"GDELT files 2 ({slot2_stamp}:events, {slot2_stamp}:gkg), rows 7, new 1\n"
                          f"GDELT backfill files 2 ({slot1_stamp}:events, {slot1_stamp}:gkg), rows 1, new 1")
                return rl.CollectorExecResult(0, stdout)

            r2 = rl.run_collector_once(
                log_dir,
                stores,
                started_at=slot2_ep + 120,
                finished_at=slot2_ep + 140,
                collector_runner=runner_2,
            )
            self.assertEqual(r2["fetched_slots"], [slot2_stamp])
            self.assertEqual(r2["backfilled_slots"], [slot1_stamp])
            self.assertEqual(r2["missing_slots"], [])

            summary = rl.summarize_run_log(log_dir)
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(summary[k], v)
            # Backfilled slot1 has honest late known_at == slot2_ep + 140!
            self.assertEqual(summary["slot_known_at"][slot1_stamp], slot2_ep + 140)
            self.assertEqual(summary["slot_known_at"][slot2_stamp], slot2_ep + 140)
            self.assertEqual(summary["unresolved_missing_slots"], [])

    def test_no_partial_file_pair_database_row_or_exit_zero_claims_a_slot(self):
        stamp = "20261124120000"
        other = "20261124121500"
        lookalikes = [
            "SLOT_OK slot=" + stamp, json.dumps({"sources": {"gdelt": {"ok": True, "fetched_slots": [stamp]}}}),
            f"GDELT files 1 ({stamp}:events), rows 5, new 1",
            f"GDELT files 2 ({stamp}:events, {other}:gkg), rows 5, new 1",
            f"GDELT files 2 ({stamp}:events, {stamp}:events), rows 5, new 1",
            f"GDELT fallback {stamp}..{other}: files 3, missing 1, rows 1, new 0 (zip CRC checked, md5 not published for these)",
            "GDELT day 20261124 UTC (events+gkg): files 191, missing 1, rows 100, new 0",
            "GDELT day 20261124 UTC (events): files 96, missing 0, rows 100, new 0",
        ]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            def run(db, target, backfills):
                _insert_didm_row(db)
                return rl.CollectorExecResult(0, "\n".join(lookalikes + [
                    "ALFRED CPIAUCSL: vintage rows 5, new 4", "ALFRED failed: TimeoutError",
                    "ECOS 722Y001 M 202401-202610: observations 0, new 0 (ECOS ERROR: message)",
                ]))
            r = rl.run_collector_once(root/"logs", root/"stores", started_at=rl.stamp_to_slot_epoch(stamp),
                                      collector_runner=run, target_slot_stamp=stamp, finished_at=rl.stamp_to_slot_epoch(stamp)+1)
            self.assertEqual(r["sources_ok"], {"gdelt": False, "alfred": False, "ecos": False})
            self.assertEqual(r["new_row_count"], 1)
            self.assertEqual(r["missing_slots"], [stamp])

    def test_all_files_in_bounded_date_or_adjacent_fallback_can_identify_requested_pairs(self):
        wanted = {"20261124120000", "20261124121500", "20261124123000", "20261125120000"}
        good = ("GDELT fallback 20261124120000..20261124121500: files 4, missing 0, rows 0, new 0 "
                "(zip CRC checked, md5 not published for these)")
        self.assertEqual(set(rl._slot_receipts(good, wanted)), {"20261124120000", "20261124121500"})
        self.assertFalse(rl._slot_receipts(good.replace("121500", "123000"), wanted))
        day = "GDELT day 20261124 UTC (events+gkg): files 192, missing 0, rows 100, new 0"
        self.assertEqual(set(rl._slot_receipts(day, wanted)), wanted-{"20261125120000"})

    def test_legacy_claims_are_retained_but_need_independent_slot_evidence(self):
        stamp = "20261124120000"
        with tempfile.TemporaryDirectory() as td:
            with rl.HashChainedLog(td, rl.RUN_LOG_FILENAME) as log:
                log.append({"kind": "collector_run", "started_at": 2, "finished_at": 3, "returncode": 0,
                            "fetched_slots": [stamp], "sources_ok": {"gdelt": True}})
            result = rl.summarize_run_log(td)
            self.assertEqual(result["slot_known_at"], {})
            self.assertEqual(result["unresolved_missing_slots"], [stamp])
            self.assertFalse(result["source_runs"]["gdelt"][0]["succeeded"])

    def test_official_module_subprocess_and_bounded_backfill_with_offline_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            temp = Path(td)
            repo = temp / "fixture provider checkout"
            for part in ("tools", "tools/didm", "data", "data/didm"):
                (repo/part).mkdir(parents=True, exist_ok=True)
                (repo/part/"__init__.py").touch()
            (repo/"data/didm/gdelt.py").write_text("fetch_bytes_optional = None\n", encoding="utf-8")
            (repo/"tools/didm/collect_daily.py").write_text("""import argparse, sys
from contextlib import nullcontext
from types import SimpleNamespace
def offline(event, args):
    if event.startswith("socket."):
        raise AssertionError("offline")
sys.addaudithook(offline)
def _now(): return 0
def _stamp_completed_batch(rows): pass
def PointInTimeStore(path):
    return nullcontext(SimpleNamespace(append_many=lambda rows: 0))
def ingest_stamps(fetch, stamps, at, kinds):
    [stamp] = stamps
    assert kinds == ("events", "gkg")
    first = stamp + ".export.CSV.zip"
    second = stamp + ".gkg.csv.zip"
    if stamp.endswith("114500"):
        return [], [first], [second]
    return [], [first, second], []
gdelt_ingest = SimpleNamespace(ingest_stamps=ingest_stamps)
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.parse_args()
    print("GDELT files 2 (20261124121500:events, 20261124121500:gkg), rows 0, new 0")
""", encoding="utf-8")
            stamps = ("20261124114500", "20261124120000", "20261124121500")
            stores = temp/"stores"
            _init_didm_sqlite(stores/"kst_20261124"/"didm_store.sqlite")
            for stamp in stamps:
                ep = rl.stamp_to_slot_epoch(stamp)
                result = rl.run_collector_once(temp/"logs", stores, collector_cwd=repo,
                    collector_cmd=[sys.executable, "-m", "tools.didm.collect_daily"], sources=("gdelt",),
                    target_slot_stamp=stamp, started_at=ep+5, finished_at=ep+15)
            self.assertEqual(result["fetched_slots"], [stamps[2]])
            self.assertEqual(result["backfilled_slots"], [stamps[1]])
            self.assertEqual(result["missing_slots"], [stamps[0]])
            summary = rl.summarize_run_log(temp/"logs")
            self.assertEqual(summary["slot_known_at"], {s: ep+15 for s in stamps[1:]})

    def test_reported_new_rows_must_exist_in_that_source_in_the_inspected_store(self):
        stamp = "20261124120000"
        ep = rl.stamp_to_slot_epoch(stamp)
        def run(db, *_):
            _insert_didm_row(db, source_id="alfred", item_id="fixture", kind="alfred_vintage")
            return rl.CollectorExecResult(0,
                f"GDELT files 2 ({stamp}:events, {stamp}:gkg), rows 1, new 1\n"
                "ALFRED CPIAUCSL: vintage rows 2, new 2\n")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            result = rl.run_collector_once(root/"log", root/"stores", started_at=ep+1, finished_at=ep+2,
                                           target_slot_stamp=stamp, collector_runner=run, sources=("gdelt","alfred"))
            self.assertEqual(result["sources_ok"], {"gdelt":False,"alfred":False})
            self.assertEqual(result["missing_slots"], [stamp])

    def test_cli_incomplete_run_is_recorded_and_returns_three(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch.object(rl, "_default_subprocess_runner", return_value=rl.CollectorExecResult(0, "")), \
                    patch("builtins.print"):
                code = rl.main(["run-collector", "--log-dir", str(root/"logs"),
                                "--stores-root", str(root/"stores"), "--collector-arg=python",
                                "--collector-arg=-m", "--collector-arg=tools.didm.collect_daily"])
            self.assertEqual(code, 3)
            summary = rl.summarize_run_log(root/"logs")
            self.assertEqual(set(summary["source_runs"]), {"gdelt"})
            self.assertEqual(len(summary["unresolved_missing_slots"]), 1)

    def test_snapshot_backup_retention_and_receipt_logging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_dir = root / "logs"
            store_path = root / "stores" / "kst_20261124" / "didm_store.sqlite"
            raw_row = _insert_didm_row(store_path)

            rep1 = root / "reports" / "rep1.json"
            rep2 = root / "reports" / "rep2.json"
            rep1.parent.mkdir(parents=True, exist_ok=True)

            s1 = rl.take_bridge_snapshot(
                log_dir, store_path, rep1,
                as_of_iso="2026-11-24T12:05:00+00:00",
                captured_at=1_763_985_900,
                kst_day="20261124",
            )
            self.assertTrue(rep1.is_file())
            self.assertEqual(s1["record_count"], 1)

            # Taking second snapshot for same KST day deletes superseded rep1 while keeping store_path and rep2
            s2 = rl.take_bridge_snapshot(
                log_dir, store_path, rep2,
                as_of_iso="2026-11-24T13:05:00+00:00",
                captured_at=1_763_989_500,
                kst_day="20261124",
            )
            self.assertFalse(rep1.exists())
            self.assertTrue(rep2.is_file())
            self.assertTrue(store_path.is_file())
            self.assertEqual(s2["deleted_superseded_reports"], [str(rep1)])

            # Record a tradegen-didm-exchange-v1 receipt via CLI
            rec_sha = bridge.check_row(raw_row)["record_sha256"]
            score_obj = {
                "record_id": "sc-1",
                "source_id": raw_row["source_id"],
                "target_kind": "macro",
                "entity_id": "CRYPTO",
                "published_at": raw_row["published_at"],
                "received_at": "2026-11-24T12:10:00+00:00",
                "relevance_0_100": 80.0,
                "ess_like_0_100": 70.0,
                "novelty_0_100": 60.0,
                "origin_cluster_id": "cl-1",
                "event_type": "crypto_regulation_hack",
                "direction_probs": [0.6, 0.2, 0.2],
                "uncertainty_entropy": qfb.shannon_entropy([0.6, 0.2, 0.2]),
                "p_credibility": 0.9,
                "market_confirmation": "PENDING",
                "model_version": "didm-v0.1",
                "prompt_sha256": "b" * 64,
            }
            export_doc = {
                "format": bridge.EXPORT_FORMAT,
                "contract": dict(bridge.CONTRACT),
                "rows": [raw_row],
                "scores": [{"source_record_sha256": rec_sha, "score": score_obj}],
            }
            exp_path = root / "didm_export.json"
            exp_path.write_text(bridge.canonical(export_doc), encoding="utf-8")

            cmd_exp = [
                sys.executable, "-B", "-m", "tools.research.didm_run_log",
                "record-didm-export", "--log-dir", str(log_dir),
                "--export", str(exp_path), "--received-at", "1763986500",
            ]
            proc = subprocess.run(cmd_exp, cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)

            # Record a QuantGPT feature snapshot receipt
            q_snap = qfb.seal_feature_snapshot({
                "format": qfb.FEATURE_SNAPSHOT_FORMAT,
                "producer": "quantgpt",
                "model": {
                    "name": "qgpt", "version": "0.2",
                    "sha256": "c" * 64,
                    "training_cutoff": 1_763_000_000,
                    "frozen_at": 1_763_500_000,
                },
                "generated_at": 1_763_986_600,
                "records": [],
            })
            q_path = root / "qgpt_snap.json"
            q_path.write_text(json.dumps(q_snap), encoding="utf-8")
            q_res = rl.record_quantgpt_receipt(log_dir, q_path, received_at=1_763_986_700)
            self.assertEqual(q_res["snapshot_sha256"], q_snap["snapshot_sha256"])

            summary = rl.summarize_run_log(log_dir)
            self.assertEqual(len(summary["didm_export_receipts"]), 1)
            self.assertEqual(len(summary["quantgpt_receipts"]), 1)

            # Tampering with run_log.jsonl is caught
            log_file = log_dir / rl.RUN_LOG_FILENAME
            log_file.write_bytes(log_file.read_bytes().replace(b"1763986700", b"1763986701"))
            with self.assertRaisesRegex(StudyError, "ARCHIVE_CHAIN_BROKEN"):
                rl.summarize_run_log(log_dir)


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
