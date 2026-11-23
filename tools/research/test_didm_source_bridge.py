"""Offline boundary tests using temporary, actual-shaped QUANTGEN stores only."""
from contextlib import redirect_stdout
import copy
import io
import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import didm_source_bridge as bridge

# Literal producer SQL from QG 9067a117, independent of the bridge's accepted SQL.
QG_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    published_at TEXT NOT NULL,
    valid_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    UNIQUE (source_id, item_id, received_at, payload_sha256)
);
CREATE INDEX IF NOT EXISTS items_received ON items (received_at);
CREATE INDEX IF NOT EXISTS items_key ON items (source_id, item_id, received_at);
"""
AS_OF = "2026-11-22T12:00:00Z"


def row(seq=1, *, received="2026-11-22T10:00:00.000000+00:00", value=2.5,
        item="CPIAUCSL:2026-10-01:2026-11-10", published="2026-11-10T00:00:00.000000+00:00"):
    payload = json.dumps({"series_id": "CPIAUCSL", "date": "2026-10-01",
        "realtime_start": "2026-11-10", "realtime_end": "9999-12-31", "value": value},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"seq": seq, "source_id": "alfred", "item_id": item, "kind": "alfred_vintage",
        "published_at": published, "valid_at": "2026-10-01T00:00:00.000000+00:00",
        "received_at": received, "payload": payload,
        "payload_sha256": bridge.sha256(payload.encode())}


def exchange(rows, scores=None):
    return json.dumps({"format": bridge.EXPORT_FORMAT, "contract": bridge.CONTRACT,
                       "rows": rows, "scores": scores or []}, ensure_ascii=False).encode()


def score(source_row):
    probs = [.6, .2, .2]
    return {"record_id": "score-1", "source_id": "alfred", "target_kind": "macro",
        "entity_id": "CPI", "published_at": source_row["published_at"],
        "received_at": source_row["received_at"], "relevance_0_100": 85,
        "ess_like_0_100": 70, "novelty_0_100": 80, "origin_cluster_id": "cpi-202610",
        "event_type": "inflation", "direction_probs": probs,
        "uncertainty_entropy": -sum(p * math.log(p) for p in probs), "p_credibility": .9,
        "market_confirmation": "PENDING", "model_version": "synthetic-model-only",
        "prompt_sha256": "a" * 64, "schema_version": "didm-score-v0"}


def linked(source_row, score_record=None):
    return {"source_record_sha256": bridge.sha256(bridge.canonical(source_row).encode()),
            "score": score_record or score(source_row)}


def make_database(path, rows):
    connection = sqlite3.connect(path)
    connection.executescript(QG_SCHEMA)
    columns = ("seq", "source_id", "item_id", "kind", "published_at", "valid_at",
               "received_at", "payload", "payload_sha256")
    connection.executemany("INSERT INTO items VALUES (?,?,?,?,?,?,?,?,?)",
                           [tuple(r[k] for k in columns) for r in rows])
    connection.commit()
    connection.close()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="didm-bridge-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def inspect(self, rows, scores=None, *, as_of=AS_OF):
        return bridge.inspect_snapshot(exchange(rows, scores), input_kind="export", as_of=as_of)

    def refuse(self, raw, reason=None):
        with self.assertRaises(bridge.BridgeError) as ctx:
            bridge.inspect_snapshot(raw, input_kind="export", as_of=AS_OF)
        if reason:
            self.assertEqual(str(ctx.exception), reason)

    def test_actual_shape_sqlite_cli_preserves_bytes_and_creates_private_report(self):
        source, output = self.root / "qg.sqlite", self.root / "report.json"
        make_database(source, [row()])
        before = source.read_bytes()
        with redirect_stdout(io.StringIO()) as stdout:
            result = bridge.main(["--database", str(source), "--as-of", AS_OF, "--output", str(output)])
        self.assertEqual(result, 0)
        self.assertEqual(source.read_bytes(), before)
        self.assertFalse(any(self.root.glob("qg.sqlite-*")))
        report = json.loads(output.read_text())
        self.assertEqual(report["records"][0]["row"], row())
        self.assertEqual(report["input_sha256"], bridge.sha256(before))
        self.assertFalse(report["live_eligible"])
        self.assertFalse(report["source_authenticated"])
        self.assertIn("V0_MODEL_SCORES_MISSING", report["gaps"])
        self.assertNotIn("CPIAUCSL", stdout.getvalue())
        self.assertNotIn(str(source), stdout.getvalue())

    def test_future_versions_are_preserved_and_do_not_change_as_of_selection(self):
        past = row()
        future = row(2, received="2026-11-23T10:00:00+00:00", value=3.9)
        one, two = self.inspect([past]), self.inspect([past, future])
        self.assertEqual(one["selected_record_sha256"], two["selected_record_sha256"])
        self.assertEqual(two["future_received_count"], 1)
        self.assertEqual(two["record_count"], 2)
        self.assertEqual(two["records"][1]["row"], future)

    def test_later_correction_is_selected_only_after_receipt(self):
        original = row()
        revision = row(2, received="2026-11-22T11:00:00Z", value=3.5)
        before = self.inspect([original, revision], as_of="2026-11-22T10:30:00Z")
        after = self.inspect([original, revision])
        self.assertEqual(before["selected_record_sha256"], [before["records"][0]["record_sha256"]])
        self.assertEqual(after["selected_record_sha256"], [after["records"][1]["record_sha256"]])

    def test_distinct_alfred_vintages_remain_distinct_items(self):
        rows = [row(), row(2, item="CPIAUCSL:2026-10-01:2026-11-20",
                          published="2026-11-20T00:00:00Z", value=3.5)]
        self.assertEqual(self.inspect(rows)["selected_count"], 2)

    def test_tied_receipts_match_producer_hash_tiebreak(self):
        rows = [row(), row(2, value=4.0)]
        result = self.inspect(rows)
        expected = max(rows, key=lambda r: r["payload_sha256"])
        self.assertEqual(result["selected_record_sha256"], [bridge.sha256(bridge.canonical(expected).encode())])

    def test_utc_equivalent_receipts_are_duplicate_versions(self):
        rows = [row(), row(2, received="2026-11-22T19:00:00+09:00")]
        self.refuse(exchange(rows), "DIDM_DUPLICATE_VERSION")

    def test_future_corrupt_record_refuses_whole_input(self):
        future = row(2, received="2026-11-23T00:00:00Z")
        future["payload_sha256"] = "0" * 64
        self.refuse(exchange([row(), future]), "DIDM_PAYLOAD_HASH_MISMATCH")

    def test_missing_extra_and_wrong_container_fields_refuse(self):
        for changes in ("missing", "extra", "payload_type"):
            bad = row()
            if changes == "missing":
                del bad["received_at"]
            elif changes == "extra":
                bad["approved"] = True
            else:
                bad["payload"] = {}
            with self.subTest(changes=changes):
                self.refuse(exchange([bad]))

    def test_unknown_source_kind_and_contract_refuse(self):
        for key, value in (("source_id", "eodhd"), ("kind", "didm_score_v0")):
            bad = row(); bad[key] = value
            self.refuse(exchange([bad]), "DIDM_SOURCE_KIND_UNSUPPORTED")
        data = json.loads(exchange([row()])); data["contract"]["commit"] = "0" * 40
        self.refuse(json.dumps(data).encode(), "DIDM_EXCHANGE_CONTRACT_MISMATCH")

    def test_nonfinite_payload_including_overflow_json_is_refused(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e10000"):
            bad = row(); bad["payload"] = '{"value":' + token + '}'
            bad["payload_sha256"] = bridge.sha256(bad["payload"].encode())
            with self.subTest(token=token):
                self.refuse(exchange([bad]), "DIDM_NONFINITE_VALUE")

    def test_duplicate_json_keys_and_noncanonical_payload_refuse(self):
        for payload in ('{"value":1,"value":2}', '{ "value": 2 }'):
            bad = row(); bad["payload"] = payload
            bad["payload_sha256"] = bridge.sha256(payload.encode())
            self.refuse(exchange([bad]))
        self.refuse(b'{"format":1,"format":2}', "DIDM_DUPLICATE_JSON_KEY")

    def test_empty_data_is_reported_without_fake_rows_or_scores(self):
        result = self.inspect([])
        self.assertEqual(result["records"], [])
        self.assertIn("SOURCE_DATA_EMPTY", result["gaps"])
        self.assertIn("NO_RECORDS_KNOWN_AT_AS_OF", result["gaps"])

    def test_pub_after_receipt_preserved_with_clock_anomaly(self):
        source = row(published="2026-11-22T11:00:00Z")
        result = self.inspect([source])
        self.assertEqual(result["records"][0]["row"], source)
        self.assertIn("SOURCE_CLOCK_ORDER_ANOMALY", result["gaps"])

    def test_timezone_missing_and_invalid_clock_refuse(self):
        for stamp in ("2026-11-22T10:00:00", "not-a-time", None):
            bad = row(); bad["received_at"] = stamp
            self.refuse(exchange([bad]))

    def test_valid_v0_scores_are_research_only_and_optional_version_is_preserved(self):
        source = row(); raw_score = score(source)
        del raw_score["schema_version"]  # upstream's documented V0 default
        result = self.inspect([source], [linked(source, raw_score)])
        self.assertEqual(result["scores"][0]["score"], raw_score)
        self.assertTrue(result["scores"][0]["known_at_as_of"])
        self.assertFalse(result["live_eligible"])
        self.assertFalse(result["owner_approval_verified"])
        self.assertIn("MODEL_APPROVAL_UNVERIFIED", result["gaps"])
        self.assertIn("EXPIRY_POLICY_UNCONFIGURED", result["gaps"])
        self.assertNotIn("expires_at", result["scores"][0]["score"])

    def test_score_receipt_after_cutoff_never_known_at_as_of(self):
        source = row(); raw_score = score(source)
        raw_score["received_at"] = "2026-11-23T00:00:00Z"
        result = self.inspect([source], [linked(source, raw_score)])
        self.assertFalse(result["scores"][0]["known_at_as_of"])
        self.assertEqual(result["known_score_count"], 0)
        self.assertIn("NO_V0_SCORES_KNOWN_AT_AS_OF", result["gaps"])

    def test_superseded_source_score_is_retained_but_not_counted_as_current(self):
        original = row()
        revision = row(2, received="2026-11-22T11:00:00Z", value=3.5)
        result = self.inspect([original, revision], [linked(original)])
        self.assertEqual(result["score_count"], 1)
        self.assertEqual(result["known_score_count"], 0)
        self.assertIn("NO_V0_SCORES_KNOWN_AT_AS_OF", result["gaps"])
        self.assertEqual(result["scores"][0]["score"], score(original))

    def test_v0_score_bounds_fields_and_algebra_are_not_coerced(self):
        source = row()
        failures = {"schema_version": "didm-score-v1", "event_type": "stocks_up",
                    "relevance_0_100": True, "novelty_0_100": 101,
                    "ess_like_0_100": 50, "uncertainty_entropy": 0,
                    "direction_probs": [.7, .2, .2], "p_credibility": -1,
                    "prompt_sha256": "A" * 64, "model_version": " ",
                    "entity_id": None, "future_unknown_field": True}
        for key, value in failures.items():
            bad = score(source); bad[key] = value
            with self.subTest(field=key):
                self.refuse(exchange([source], [linked(source, bad)]))

    def test_score_provenance_link_and_receipt_must_match_source(self):
        source = row()
        for key, value in (("source_id", "gdelt-gkg2"), ("published_at", "2026-11-11T00:00:00Z"),
                           ("received_at", "2026-11-21T00:00:00Z")):
            bad = score(source); bad[key] = value
            self.refuse(exchange([source], [linked(source, bad)]), "DIDM_SCORE_PROVENANCE_MISMATCH")
        item = linked(source); item["source_record_sha256"] = "0" * 64
        self.refuse(exchange([source], [item]), "DIDM_SCORE_SOURCE_LINK_MISSING")

    def test_duplicate_scores_refuse_rather_than_select_one(self):
        source = row(); item = linked(source)
        self.refuse(exchange([source], [item, copy.deepcopy(item)]), "DIDM_DUPLICATE_SCORE")

    def test_source_sidecars_all_refuse_without_change(self):
        source = self.root / "source.sqlite"; make_database(source, [row()])
        original = source.read_bytes()
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(source) + suffix); sidecar.write_bytes(b"untouched")
            with self.assertRaisesRegex(bridge.BridgeError, "OFFLINE_SQLITE_SNAPSHOT_REQUIRED"):
                bridge.read_snapshot(source, database=True)
            self.assertEqual(sidecar.read_bytes(), b"untouched")
            sidecar.unlink()
        self.assertEqual(source.read_bytes(), original)

    def test_source_change_during_read_is_refused(self):
        source = self.root / "source.sqlite"; make_database(source, [row()])
        original = Path.lstat
        calls = [0]
        def changed(path, *args, **kwargs):
            calls[0] += 1
            if calls[0] == 2:
                path.write_bytes(path.read_bytes() + b"changed")
            return original(path, *args, **kwargs)
        with patch.object(Path, "lstat", changed):
            with self.assertRaisesRegex(bridge.BridgeError, "INPUT_CHANGED"):
                bridge.read_snapshot(source)

    def test_windows_identity_uses_birthtime_not_inconsistent_ctime(self):
        base = dict(st_dev=3, st_ino=17, st_size=400, st_mtime_ns=2000,
                    st_ctime_ns=1000, st_birthtime_ns=800)
        by_path = SimpleNamespace(**base)
        by_handle = SimpleNamespace(**dict(base, st_ctime_ns=1500))
        with patch.object(bridge.os, "name", "nt"):
            self.assertEqual(bridge._metadata(by_path), bridge._metadata(by_handle))
            for field in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_birthtime_ns"):
                changed = SimpleNamespace(**dict(base, **{field: base[field] + 1}))
                with self.subTest(field=field):
                    self.assertNotEqual(bridge._metadata(by_path), bridge._metadata(changed))
            del by_handle.st_birthtime_ns
            with self.assertRaisesRegex(bridge.BridgeError, "FILE_IDENTITY_UNSUPPORTED"):
                bridge._metadata(by_handle)

    def test_views_triggers_extra_tables_and_changed_sql_refuse(self):
        for sql in ("CREATE VIEW extra AS SELECT * FROM items",
                    "CREATE TRIGGER extra AFTER INSERT ON items BEGIN SELECT 1; END",
                    "CREATE TABLE extra (secret TEXT)", "DROP INDEX items_received"):
            source = self.root / "test.sqlite"
            if source.exists():
                source.unlink()
            make_database(source, [row()])
            connection = sqlite3.connect(source); connection.execute(sql); connection.commit(); connection.close()
            with self.subTest(sql=sql), self.assertRaisesRegex(bridge.BridgeError, "SCHEMA_MISMATCH"):
                bridge.inspect_snapshot(source.read_bytes(), input_kind="sqlite", as_of=AS_OF)

    def test_corrupt_and_non_sqlite_inputs_refuse(self):
        for raw in (b"not-sqlite", b"SQLite format 3\x00" + b"\x00" * 100):
            with self.assertRaises(bridge.BridgeError):
                bridge.inspect_snapshot(raw, input_kind="sqlite", as_of=AS_OF)

    def test_payload_and_row_limits_do_not_return_partial_success(self):
        with patch.object(bridge, "MAX_ROWS", 1):
            self.refuse(exchange([row(), row(2, item="other")]), "DIDM_RECORD_LIMIT")
        with patch.object(bridge, "MAX_PAYLOAD_BYTES", 8):
            self.refuse(exchange([row()]), "DIDM_PAYLOAD_LIMIT")
        with patch.object(bridge, "MAX_INPUT_BYTES", 8):
            self.refuse(exchange([row()]), "DIDM_INPUT_SIZE_LIMIT")

    def test_cli_bad_last_record_leaves_no_output_or_temp(self):
        source, output = self.root / "exchange.json", self.root / "report.json"
        bad = row(2); bad["payload_sha256"] = "0" * 64
        source.write_bytes(exchange([row(), bad]))
        with redirect_stdout(io.StringIO()) as stdout:
            result = bridge.main(["--export", str(source), "--as-of", AS_OF, "--output", str(output)])
        self.assertEqual(result, 2)
        self.assertFalse(output.exists())
        self.assertEqual(list(self.root.iterdir()), [source])
        self.assertNotIn(str(source), stdout.getvalue())

    def test_publication_never_overwrites_and_cleans_temp_on_failure(self):
        output = self.root / "report.json"; output.write_bytes(b"old")
        with self.assertRaisesRegex(bridge.BridgeError, "OUTPUT_EXISTS"):
            bridge.publish_report(self.inspect([]), output)
        self.assertEqual(output.read_bytes(), b"old")
        output.unlink()
        with patch.object(bridge.os, "link", side_effect=OSError("unsupported")):
            with self.assertRaises(OSError):
                bridge.publish_report(self.inspect([]), output)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_publication_competing_writer_is_not_overwritten(self):
        output = self.root / "report.json"
        real_link = bridge.os.link
        def competing(source, destination):
            Path(destination).write_bytes(b"other writer")
            return real_link(source, destination)
        with patch.object(bridge.os, "link", side_effect=competing):
            with self.assertRaises(FileExistsError):
                bridge.publish_report(self.inspect([]), output)
        self.assertEqual(output.read_bytes(), b"other writer")
        self.assertEqual(list(self.root.iterdir()), [output])


if __name__ == "__main__":
    unittest.main()
