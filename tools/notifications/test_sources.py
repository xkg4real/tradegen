from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from core import isolation
from core.compliance import alerts, model
from execution import checks
from execution_control.store import Journal
from tools.notifications import sources


class DurableSourcesTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(patch.dict(os.environ, {"TRADEGEN_HOME": str(self.root / "state")}))
        self.enterContext(patch.object(isolation, "QUANTGEN_STATE", self.root / "unrelated-state"))
        self.control = self.root / "state" / "execution-control"
        self.compliance = self.root / "state" / "compliance" / "alerts.jsonl"
        self.execution = self.root / "state" / "execution" / "alerts.jsonl"
        self.now = datetime(2026, 1, 1, 15, tzinfo=timezone.utc)

    def test_initial_missing_inputs_do_not_create_any_state(self):
        for scan, path in [(sources.scan_control, self.control), (sources.scan_compliance, self.compliance),
                           (sources.scan_execution, self.execution)]:
            with self.subTest(scan=scan), self.assertRaises(sources.SourceError):
                scan(path)
        self.assertEqual([], list(self.root.iterdir()))

    def test_control_halt_and_first_stop_each_kst_day_after_full_verification(self):
        def risk(stopped, when):
            return {"day": when.astimezone(model.KST).date().isoformat(), "daily_stopped": stopped,
                    "policy_digest": "0" * 64, "high_watermark": "2", "day_start_equity": "1",
                    "effective_floor": "1", "calculated_floor": "1", "floor_relaxation_approved": False}

        journal = Journal(self.control)
        tomorrow = self.now + timedelta(days=1)
        with journal.transaction() as tx:
            tx.append("risk_snapshot", risk(False, self.now), now=self.now)
            tx.append("risk_snapshot", risk(True, self.now), now=self.now)
            tx.append("risk_snapshot", risk(True, self.now), now=self.now)
            tx.append("halt", {"floor": "1"}, now=self.now)
            tx.append("risk_snapshot", risk(True, tomorrow), now=tomorrow)
        files = {p: p.read_bytes() for p in self.control.iterdir()}
        ids = sources.scan_control(self.control)
        self.assertEqual(3, len(set(ids)))
        self.assertEqual(ids, sources.scan_control(self.control))
        for identifier in ids:
            self.assertRegex(identifier, r"^[a-f0-9]{64}$")
        self.assertEqual(files, {p: p.read_bytes() for p in self.control.iterdir()})
        # A structurally damaged suffix invalidates the entire snapshot, with no earlier events emitted.
        with (self.control / "journal.jsonl").open("ab") as f:
            f.write(b"{")
        with self.assertRaisesRegex(sources.SourceError, "^control source unavailable$"):
            sources.scan_control(self.control)

    def test_compliance_uses_real_writer_including_failed_toast(self):
        summary = {"code": 4, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}
        alerts.log("toast", "fail", summary, self.now)
        alerts.log("email", "ok", summary, self.now)
        alerts.log("push", "ok", summary, self.now)
        first = sources.scan_compliance(self.compliance)
        self.assertEqual(1, len(first))
        self.assertRegex(first[0], r"^[0-9a-f]{64}$")
        alerts.log("toast", "ok", summary, self.now + timedelta(days=1))
        before = self.compliance.read_bytes()
        both = sources.scan_compliance(self.compliance)
        self.assertEqual(2, len(set(both)))
        self.assertEqual(first, both[:1])
        self.assertEqual(before, self.compliance.read_bytes())

    def test_execution_uses_catalogue_survives_digest_mark_and_skips_local_info_and_clear(self):
        self.execution.parent.mkdir(parents=True)

        def record(venue, kind, level, text_key, **slots):
            alert = checks.Alert(venue=venue, kind=kind, level=level, text_key=text_key, slots=slots)
            return checks.row(alert, model.iso_utc(self.now))

        red = record("upbit", "ADDRESS_LIST", "red", "ADDRESS_CHANGED", added=2, removed=1)
        amber = record("upbit", "KEY_HEALTH", "amber", "KEY_MISSING")
        clear = record("upbit", "ADDRESS_LIST", "clear", "ADDRESS_CHANGED")
        info = record("all", "NOT_SET", "info", "NOT_SET", skipped="FLOOR: not set")

        def write(*rows):
            self.execution.write_bytes(("".join(model.canonical_json(row) + "\n" for row in rows)).encode())

        write(red, amber, clear, info)
        ids = sources.scan_execution(self.execution)
        self.assertEqual(2, len(set(ids)))
        write({**red, "sent": True}, {**amber, "sent": True}, clear, info)
        self.assertEqual(ids, sources.scan_execution(self.execution))
        write(red, {**amber, "text_key": "not in catalogue"})
        with self.assertRaisesRegex(sources.SourceError, "^execution source unavailable$"):
            sources.scan_execution(self.execution)

    def test_torn_duplicate_and_wrong_source_fail_without_repair(self):
        self.compliance.parent.mkdir(parents=True)
        for data in (b'{"some":"private bytes"', b'{"utc":1,"utc":1}\n', b"not json\n", b"[]\n"):
            with self.subTest(data=data):
                self.compliance.write_bytes(data)
                with self.assertRaisesRegex(sources.SourceError, "^compliance source unavailable$"):
                    sources.scan_compliance(self.compliance)
                self.assertEqual(data, self.compliance.read_bytes())
        with self.assertRaises(sources.SourceError):
            sources.scan_execution(self.root / "different-name")

    def test_bounded_read_and_torn_suffix(self):
        summary = {"code": 4, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}
        alerts.log("toast", "fail", summary, self.now)
        size = self.compliance.stat().st_size
        for limit, maximum in [("MAX_LOG_BYTES", size - 1), ("MAX_LINE_BYTES", size - 1), ("MAX_ROWS", 0)]:
            with self.subTest(limit=limit), patch.object(sources, limit, maximum), self.assertRaises(sources.SourceError):
                sources.scan_compliance(self.compliance)
        with patch.object(sources, "MAX_LOG_BYTES", size), patch.object(sources, "MAX_LINE_BYTES", size):
            self.assertEqual(1, len(sources.scan_compliance(self.compliance)))
        with self.compliance.open("ab") as f:
            f.write(b"{")
        with self.assertRaises(sources.SourceError):
            sources.scan_compliance(self.compliance)

    def test_link_to_wrong_file_rejected(self):
        target = self.root / "other"
        target.write_bytes(b"")
        self.execution.parent.mkdir(parents=True)
        try:
            os.link(target, self.execution)
        except OSError as exc:
            self.skipTest(type(exc).__name__)
        with self.assertRaises(sources.SourceError):
            sources.scan_execution(self.execution)
        self.assertEqual(b"", target.read_bytes())


if __name__ == "__main__":
    unittest.main()
