"""Offline synthetic source receipts and price exports; this suite measures software behavior."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import random
import socket
import tempfile
import unittest
from unittest.mock import patch

from tools.research import direction_feature_builder as features
from tools.research import direction_model_fit as fit
from tools.research import prospective_direction_inputs as inputs
from tools.research import prospective_direction_study as workflow
from tools.research._study_common import (
    RESEARCH_FLAGS, HashChainedLog, StudyError, atomic_publish_json_ascii, kst_date_iso,
    read_verified_chained_log, sha256_ascii,
)
from tools.research.test_direction_stage1_evaluator import _build_stage1_scenario, _coverage_table, _seal_snap
from tools.research.test_quantgpt_feature_bridge import _make_record, _make_snapshot
from tools.research.test_direction_stage2_replay import _make_daily_quote_doc, _make_obs


class ProspectiveWorkflowTests(unittest.TestCase):
    def setUp(self):
        blocker = patch.object(socket.socket, "connect", side_effect=AssertionError("offline only"))
        blocker.start()
        self.addCleanup(blocker.stop)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.src = Path(tmp.name)
        self.root = self.src / "new-study"
        self.step = 3600
        t0 = 1764000000
        rng = random.Random(71)
        self.bars = [{"end": t0 + i * self.step, "known_at": t0 + i * self.step + 1,
                      "return_bps": rng.randint(-80, 80)} for i in range(450)]
        self.start = self.bars[290]["end"]
        self.end = self.bars[410]["end"]
        self.mid = (self.start + self.end) // 2
        s2 = ((self.end + 9 * 3600) // 86400 + 1) * 86400 - 9 * 3600
        self.study = {"scope": "synthetic-upbit-krw-spot", "market": "KRW-BTC", "source_id": "test-prices",
            "rule_version": "external-forecast-v1", "step_seconds": self.step, "horizon_seconds": 7200,
            "hurdle_bps": 15, "confidence": "0.6", "max_calibration_gap": "0.10", "min_validation_calls": 100,
            "up_y": "0.04", "down_y": "0.02", "ceiling_y": "0.04", "ceiling_mode": "7a",
            "criterion2_margin": 0.0, "bootstrap_seed": 19, "b2_seed": 42,
            "stage1_writer_mode": "batch", "evaluation_start": self.start, "interim_at": self.mid,
            "evaluation_end": self.end, "stage2_start": s2, "stage2_end": s2 + 86400,
            "min_daily_quote_coverage": 0.95, "min_daily_live_forecast_coverage": 0.95,
            "quote_interval_seconds": 10, "min_stage2_days": 1, "max_excess_alerts_per_day": 1,
            "min_early_warnings": 1, "early_warning_window_seconds": 1800,
            "latch_convention": "17a", "attempt_number": 1, "attempt_budget": 1}
        self.bar_heads = {}
        with HashChainedLog(self.src / "prices", "bars.jsonl") as log:
            log.append({"kind": "config", "schema": inputs.upbit_price_recorder.RECORDER_SCHEMA,
                        "config": {"market": "KRW-BTC", "step_seconds": self.step}})
            for bar in self.bars:
                self.bar_heads[bar["end"]] = log.append({"kind": "bar", **bar})["sha256"]
        self.snap = _make_snapshot([_make_record(as_of=t0, issued_at=t0 + 5)])
        self.qtime = self.snap["generated_at"]
        self.dump("qgpt", self.snap)
        with HashChainedLog(self.src / "receipts", "run_log.jsonl") as log:
            log.append({"kind": "quantgpt_receipt", "surface": "feature_snapshot",
                        "received_at": self.qtime, "snapshot_sha256": self.snap["snapshot_sha256"]})
        self.names = ["P1", "P2", "P3", "P4", "Q1"]
        train = self.bars[:281]
        self.train_path = self.source("train", train)
        training_table = features.build_feature_table(market="KRW-BTC", step_seconds=3600, bars=train,
            feature_names=self.names, quantgpt_snapshots=[(self.snap, self.qtime)],
            pinned_quantgpt_model=self.snap["model"], q1_cadence_seconds=3600 * 500, feature_builder_commit="1" * 40)
        result = fit.fit_and_freeze_models(feature_table=training_table, bars=train, train_start=train[30]["end"],
            train_end=train[-1]["end"], frozen_at=train[-1]["end"] + 20, horizon_seconds=7200, hurdle_bps=15)
        self.fit_dir = self.src / "fit"
        self.fit_dir.mkdir()
        for role in workflow.ROLES:
            atomic_publish_json_ascii(self.fit_dir / f"model_{role}.json", result[role])
        atomic_publish_json_ascii(self.fit_dir / "fit_report.json", result["report"])
        self.terms = self.dump("terms", self.study)
        self.prereqs = self.dump("refs", {k: "a" * 64 for k in ("O28", "O38", "M9-T4", "section10")})

    def dump(self, name, value):
        path = self.src / (name + ".json")
        atomic_publish_json_ascii(path, value)
        return path

    def source(self, name, bars):
        hist = {"source_id": self.study["source_id"], "scope": self.study["scope"], "bars": bars}
        path = self.dump(name + "-price", hist)
        man = {"format": "tradegen-price-history-manifest-v1", **RESEARCH_FLAGS,
               **{k: self.study[k] for k in ("market", "scope", "source_id", "step_seconds")},
               "exported_at": bars[-1]["known_at"], "bar_count": len(bars), "history_sha256": sha256_ascii(hist),
               "history_file": path.name, "archive_head_sha256": self.bar_heads[bars[-1]["end"]]}
        self.dump(name + "-price.manifest", dict(man, manifest_sha256=sha256_ascii(man)))
        return self.dump(name, {"history": path.name, "price_log": "prices", "run_log": "receipts", "didm_reports": [],
                                "didm_exports": [], "quantgpt_snapshots": ["qgpt.json"]})

    def cmd(self, now, *argv):
        output = io.StringIO()
        if argv[0] in ("final", "interim"):
            argv = (*argv, "--price-log", self.src / "prices")
        with patch.object(workflow.time, "time", return_value=now), contextlib.redirect_stdout(output):
            result = workflow.main(["--archive", str(self.root), *map(str, argv)])
        return result, json.loads(output.getvalue())

    def register(self, now=None):
        return self.cmd(self.start - 1 if now is None else now, "register", "--terms", self.terms, "--prerequisites",
                        self.prereqs, "--fit-dir", self.fit_dir, "--inputs", self.train_path)

    def test_rebuild_uses_each_delivered_export_and_only_receipts_known_to_last_bar(self):
        from tools.research import didm_source_bridge as bridge
        doc = {"format": bridge.EXPORT_FORMAT, "contract": bridge.CONTRACT, "rows": [], "scores": []}
        current = self.dump("current-didm", doc)
        earliest = self.bars[0]["end"]
        boundary = self.bars[280]["end"]
        log_dir = self.src / "receipts"
        inputs.didm_run_log.record_didm_export(log_dir, current, received_at=earliest)
        inputs.didm_run_log.record_didm_export(log_dir, current, received_at=boundary)
        # A distinct receipt after the final requested bar must not be required to replay it.
        future = self.src / "later-didm.json"
        future.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        inputs.didm_run_log.record_didm_export(log_dir, future, received_at=boundary+1)
        plan = json.loads(self.train_path.read_text())
        plan.update(didm_exports=[current.name], quantgpt_snapshots=[])
        model = json.loads((self.fit_dir / "model_M.json").read_text())
        model.update(feature_names=["D3"], upstream_identities={"didm_v0": {
            "model_version": "research-v0", "prompt_sha256": "f"*64}, "quantgpt": None})
        table, _, hashes = inputs.rebuild(self.dump("replay", plan), model, self.study, boundary+5)
        self.assertEqual(len(hashes["didm_exports"]), 1)
        self.assertEqual(table["rows"][-1]["features"]["D3"], 50.0)
        self.assertIsNone(table["rows"][-2]["features"]["D3"])

    def test_registered_fit_forward_capture_interim_and_pinned_status(self):
        rc, registration = self.register()
        self.assertEqual(rc, 0, registration)
        self.assertEqual(self.register()[1]["reason"], "STUDY_ALREADY_REGISTERED")
        selected = self.source("interim", self.bars[:351])
        now = self.mid + 5
        rc, result = self.cmd(now, "forecast", "--inputs", selected)
        self.assertEqual(rc, 0, result)
        self.assertEqual(self.cmd(now, "forecast", "--inputs", selected)[1]["reason"], "NO_NEW_GRID_ROWS")
        rc, interim = self.cmd(now + 1, "interim", "--history", self.src / "interim-price.json")
        self.assertEqual(rc, 0, interim)
        self.assertIn(interim["outcome"], ("CONTINUE", "STOPPED"))
        rc, result = self.cmd(now + 1, "status", "--pinned-head", registration["journal_head"])
        self.assertEqual(rc, 0, result)
        self.assertFalse(result["source_authenticated"])
        self.assertFalse(result["execution_ready"])
        rows, _ = read_verified_chained_log(self.root, workflow.JOURNAL)
        capture = rows[1]["data"]
        for role in workflow.ROLES:
            snap = workflow.load(self.root, capture["models"][role]["forecast"])
            self.assertEqual(capture["at"], now)
            self.assertTrue(all(f["issued_at"] == now for f in snap["forecasts"]))
        if interim["outcome"] == "CONTINUE":
            selected = self.source("final", self.bars[:411])
            end = self.end + 5
            self.assertEqual(self.cmd(end, "forecast", "--inputs", selected)[0], 0)
            rc, final = self.cmd(end + 1, "final", "--history", self.src / "final-price.json")
            self.assertEqual(rc, 0, final)
            self.assertEqual(final["outcome"], "INCONCLUSIVE")
            self.assertEqual(self.cmd(end + 2, "review")[1]["reason"], "STAGE2_GATE_CLOSED")
        else:
            self.assertEqual(self.cmd(now + 2, "forecast", "--inputs", selected)[1]["reason"], "STUDY_CLOSED")
        (self.root / (capture["features"] + ".json")).write_text("{}", encoding="ascii")
        self.assertEqual(self.cmd(now, "status")[1]["reason"], "EVIDENCE_HASH_MISMATCH")

    def test_late_register_unrecorded_inputs_and_missing_receipts(self):
        self.assertNotEqual(self.register(self.start)[0], 0)
        self.assertFalse((self.root / workflow.JOURNAL).exists())
        config = json.loads(self.train_path.read_text())
        config["quantgpt_snapshots"] = []
        self.train_path = self.dump("missing-q1", config)
        self.assertEqual(self.register()[1]["reason"], "LIVE_PINNED_QUANTGPT_REQUIRED")
        config["history"] = "../outside.json"
        self.train_path = self.dump("outside", config)
        self.assertEqual(self.register()[1]["reason"], "INPUT_PATH_NOT_RELATIVE")
        self.assertFalse((self.root / workflow.JOURNAL).exists())

    def test_clock_grid_and_refusal_before_forward_gate(self):
        self.assertEqual(self.register()[0], 0)
        selected = self.source("early", self.bars[:293])
        self.assertEqual(self.cmd(self.start - 10, "forecast", "--inputs", selected)[1]["reason"],
                         "CLOCK_WENT_BACKWARDS")
        self.assertEqual(self.cmd(self.start, "forecast", "--inputs", selected)[1]["reason"],
                         "PRICE_EXPORT_RECEIPT_MISMATCH")
        self.assertEqual(self.cmd(self.start, "review")[1]["reason"], "STAGE1_PASS_REQUIRED")
        self.assertEqual(self.cmd(self.end + 5, "forecast", "--inputs", selected)[1]["reason"], "MISSED_INTERIM")

    def test_quote_coverage_preserves_failure_and_denominator(self):
        self.root.mkdir()
        start = self.study["stage2_start"]
        day = kst_date_iso(start)
        obs = [_make_obs(as_of=start + 10, seq=1, scope=self.study["scope"], bid=None)]
        record = _make_daily_quote_doc(day, self.study["scope"], obs, expected_obs=8640)
        ceiling = {"kst_date": day, "events": [], "initial_signed_y": "0.04", "source_sha256": "c" * 64}
        event = workflow.record_day(self.root, [], self.study, record, ceiling, start + 86400)
        self.assertIsNone(workflow.load(self.root, event["quotes"])["observations"][0]["bid"])
        with self.assertRaisesRegex(StudyError, "DAY_ALREADY_CAPTURED"):
            workflow.record_day(self.root, [event], self.study, record, ceiling, start + 86400)
        low = _make_daily_quote_doc(day, self.study["scope"], obs, expected_obs=1)
        with self.assertRaisesRegex(StudyError, "QUOTE_STUDY_MISMATCH"):
            workflow.record_day(self.root, [], self.study, low, ceiling, start + 86400)
        closed = workflow.score_stage2(self.root, [], self.study, start + 86400)
        self.assertEqual(closed["outcome"], "INCONCLUSIVE")
        self.assertEqual(workflow.load(self.root, closed["report"])["missing_quote_or_ceiling_days"], [day])

    def test_existing_positive_stage1_and_timestamped_live_snapshot_feed_quote_review(self):
        # Exercise the Stage 2 CLI against a deterministic passing synthetic Stage 1 gate.
        study, hist, m, b1, b0 = _build_stage1_scenario()
        end = study["evaluation_end"]
        start = ((end + 9 * 3600) // 86400 + 1) * 86400 - 9 * 3600
        study.update(stage2_start=start, stage2_end=start + 86400, min_stage2_days=1, quote_interval_seconds=10)
        issued = m["generated_at"]
        report = workflow.stage1.evaluate_stage1(study=study, history=hist, feature_table=_coverage_table(study, hist),
            m_snapshots=[m], b1_snapshots=[b1], b0_snapshots=[b0],
            m_receipt_times=[issued], b1_receipt_times=[issued], b0_receipt_times=[issued], evaluated_at=issued + 1)
        self.assertEqual(report["outcome"], "PASS")
        day = kst_date_iso(start)
        self.root.mkdir()
        with HashChainedLog(self.root, workflow.JOURNAL) as log:
            log.append({"kind": "registered", "at": study["evaluation_start"] - 5, "terms": workflow.seal(self.root, study)})
            snaps = {"M": m, "B1": b1, "B0": b0}
            log.append({"kind": "stage1_forecast", "at": issued,
                        "models": {r: {"forecast": workflow.seal(self.root, snap)} for r, snap in snaps.items()}})
            log.append({"kind": "final", "at": issued + 1, "outcome": "PASS", "history": workflow.seal(self.root, hist),
                        "report": workflow.seal(self.root, report)})
            live = {}
            for role, snap in (("M", m), ("B1", b1)):
                live_row = {**snap["forecasts"][0], "as_of": start, "issued_at": start + 1}
                current = _seal_snap({**snap, "generated_at": start + 1, "forecasts": [live_row]})
                live[role] = {"forecast": workflow.seal(self.root, current)}
            log.append({"kind": "stage2_forecast", "at": start + 2, "models": live})
        quote_log = self.src / "quotes"
        quote_path = self.src / "day.json"
        with HashChainedLog(quote_log, "quotes.jsonl") as log:
            cfg = inputs.upbit_quote_recorder.QuoteRecorderConfig(market=study["market"], scope=study["scope"])
            log.append({"kind": "config", "schema": inputs.upbit_quote_recorder.QUOTE_RECORDER_SCHEMA, "config": cfg.document()})
            log.append({"kind": "quote", "kst_date": day, "observation": _make_obs(1, start + 10, study["scope"])})
        finished = start + 86400
        inputs.upbit_quote_recorder.export_daily_quotes(quote_log, quote_path, kst_date=day, exported_at=finished)
        limits = self.dump("signed-ceiling-reference", {"kst_date": day, "events": [], "initial_signed_y": "0.04",
                                                       "source_sha256": "e" * 64})
        rc, event = self.cmd(finished, "quote-day", "--quotes", quote_path, "--ceiling", limits, "--quote-log", quote_log)
        self.assertEqual(rc, 0, event)
        rc, event = self.cmd(finished + 1, "review")
        self.assertEqual(rc, 0, event)
        self.assertEqual(event["outcome"], "INCONCLUSIVE")
        judged = workflow.load(self.root, event["report"])
        self.assertEqual(judged["stop_rule"], "S7")
        self.assertFalse(judged["execution_costs_measured"])
        self.assertFalse(judged["m11_t5_fill_check_closed"])
        self.assertEqual(self.cmd(finished + 2, "review")[1]["reason"], "STUDY_CLOSED")

    def test_price_manifest_matching_rewritten_prices_refused_against_recorder(self):
        other = [dict(r) for r in self.bars[:281]]
        other[150]["return_bps"] += 1
        self.train_path = self.source("rewritten", other)
        self.assertEqual(self.register()[1]["reason"], "RECORDED_BARS_CHANGED")

    def test_source_eligibility_needs_entire_training_period(self):
        rows = [{"end": t} for t in (100, 200, 300)]
        self.assertFalse(inputs._covered([99, 250], rows, 100))
        self.assertTrue(inputs._covered([1, 101, 250], rows, 100))


if __name__ == "__main__":
    unittest.main()
