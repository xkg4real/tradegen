"""Unit tests for quantgpt_feature_bridge (Surface A & Surface B). Synthetic data only."""
from __future__ import annotations

import copy
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.research import quantgpt_feature_bridge as qfb
from tools.research._study_common import (
    RESEARCH_FLAGS,
    StudyError,
    assert_all_isolation_invariants,
    canonical_utf8_bytes,
    sha256_raw,
    sha256_utf8,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_record(record_id: str = "rec-001", *, as_of: int = 1_764_000_000, issued_at: int = 1_764_000_120) -> dict:
    probs = ["0.700000", "0.100000", "0.200000"]
    fprobs = [0.7, 0.1, 0.2]
    return {
        "record_id": record_id,
        "source_id": "gdelt-events2",
        "as_of": as_of,
        "issued_at": issued_at,
        "published_at": as_of - 300,
        "target_kind": "macro",
        "entity_id": "US_CPI",
        "event_type": "crypto_regulation_hack",
        "direction_probs": probs,
        "relevance_0_100": 85.0,
        "novelty_0_100": 70.0,
        "ess_like_0_100": 50.0 + 50.0 * (fprobs[0] - fprobs[1]),
        "uncertainty_entropy": -sum(p * math.log(p) for p in fprobs if p > 0),
        "p_credibility": "0.900000",
        "market_confirmation": "PENDING",
        "origin_cluster_id": "cluster-01",
    }


def _make_snapshot(records: list[dict] | None = None, *, producer: str = "quantgpt") -> dict:
    recs = [_make_record()] if records is None else records
    gen_at = max([r["issued_at"] for r in recs], default=1_764_000_300) + 60
    model_sha = qfb.quantgpt_model_sha256("qwen2.5-7b-q4", "lora-v1", "p1", {"temperature": 0.0, "seed": 42})
    raw = {
        "format": qfb.FEATURE_SNAPSHOT_FORMAT,
        "producer": producer,
        "model": {
            "name": "quantgpt-news-judge",
            "version": "0.2.0",
            "sha256": model_sha,
            "training_cutoff": 1_763_000_000,
            "frozen_at": 1_763_500_000,
        },
        "generated_at": gen_at,
        "records": recs,
    }
    return qfb.seal_feature_snapshot(raw)


def _make_envelope(
    *,
    task: str = "T-EXPLAIN",
    mode: str = "tool",
    status: str = "ok",
    body: dict | None = None,
    payload: dict | None = None,
    numbers: list[dict] | None = None,
    citations: list[dict] | None = None,
    violations: list[str] | None = None,
    reason_code: str | None = None,
    latency_ms: int = 120,
) -> tuple[dict, dict]:
    if payload is None:
        payload = {"report": {"sharpe": 1.25, "drawdown_pct": -0.084}, "language": "ko"}
    if status == "ok" and body is None:
        body = {
            "summary": "보고된 샤프 비율은 1.25이며 최대 낙폭은 8.4%입니다.",
            "points": ["샤프 비율 1.25 기록", "낙폭 8.4% 수준"],
        }
    req_hash = qfb.request_sha256(task, mode, payload, "qwen2.5-7b", "adapter-0", "p0")
    env: dict = {
        "envelope_version": "qgpt-env-v1",
        "task": task,
        "mode": mode,
        "status": status,
        "body": body if status == "ok" else None,
        "numbers": numbers if numbers is not None else (
            list(qfb.cited_entries(qfb.text_of(body), payload.get("report", {})))
            if status == "ok" and task == "T-EXPLAIN" else []
        ),
        "citations": citations if citations is not None else [],
        "policy": {"violations": list(violations or []), "rules_version": "pf-seed-0"},
        "model": {"id": "qwen2.5-7b", "adapter": "adapter-0", "prompt_version": "p0"},
        "label_ko": "AI 해설 · 검증 안 됨.",
        "latency_ms": latency_ms,
        "request_sha256": req_hash,
    }
    if reason_code is not None:
        env["reason_code"] = reason_code
    return env, payload


class SurfaceAFeatureSnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_valid_16_and_17_key_records_pass(self) -> None:
        snap16 = _make_snapshot()
        self.assertEqual(len(snap16["records"][0]), 16)
        self.assertEqual(qfb.check_feature_snapshot(snap16), snap16)

        rec17 = _make_record("rec-017")
        rec17["calibration_version"] = None
        snap17 = _make_snapshot([rec17])
        self.assertEqual(len(snap17["records"][0]), 17)
        self.assertEqual(qfb.check_feature_snapshot(snap17), snap17)

    def test_rejects_forbidden_text_fields_and_bad_invariants(self) -> None:
        for bad_field in ("title", "body", "prompt"):
            with self.subTest(bad_field=bad_field):
                rec = _make_record()
                rec[bad_field] = "leaked article text"
                with self.assertRaisesRegex(StudyError, "QGPT_FORBIDDEN_TEXT_FIELD"):
                    _make_snapshot([rec])

        cases = [
            (lambda r: r.update(issued_at=r["as_of"] - 1), "QGPT_RECORD_TIME_ORDER"),
            (lambda r: r.update(direction_probs=["0.700000", "0.200000", "0.200000"]), "QGPT_PROBABILITIES_INVALID"),
            (lambda r: r.update(ess_like_0_100=51.0), "QGPT_ESS_MISMATCH"),
            (lambda r: r.update(uncertainty_entropy=0.123), "QGPT_ENTROPY_MISMATCH"),
            (lambda r: r.update(extra_unknown=1), "QGPT_RECORD_SCHEMA_MISMATCH"),
        ]
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                rec = _make_record()
                mutate(rec)
                with self.assertRaisesRegex(StudyError, expected):
                    _make_snapshot([rec])

    def test_file_hardening_bom_surrogates_symlinks_hardlinks_and_token_caps(self) -> None:
        snap = _make_snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "snap.json"
            p.write_bytes(json.dumps(snap).encode("utf-8"))
            loaded = qfb.read_feature_snapshot(p, snap["snapshot_sha256"])
            self.assertEqual(loaded, snap)

            # BOM rejected
            p_bom = root / "bom.json"
            p_bom.write_bytes(b"\xef\xbb\xbf" + json.dumps(snap).encode("utf-8"))
            with self.assertRaisesRegex(StudyError, "UTF8_BOM_REFUSED"):
                qfb.read_feature_snapshot(p_bom, snap["snapshot_sha256"])

            # JSON lone surrogate rejected
            p_sur = root / "surrogate.json"
            p_sur.write_bytes(b'{"a":"\\ud800"}')
            with self.assertRaises(StudyError):
                qfb.read_feature_snapshot(p_sur, snap["snapshot_sha256"])

            # Symlink rejected
            sym = root / "link.json"
            sym.symlink_to(p)
            with self.assertRaisesRegex(StudyError, "QGPT_SNAPSHOT_FILE"):
                qfb.read_feature_snapshot(sym, snap["snapshot_sha256"])

            # Hardlink (st_nlink != 1) rejected
            hl = root / "hardlink.json"
            os.link(p, hl)
            try:
                with self.assertRaisesRegex(StudyError, "QGPT_SNAPSHOT_FILE"):
                    qfb.read_feature_snapshot(hl, snap["snapshot_sha256"])
            finally:
                hl.unlink()

            # .tradegen path rejected
            tg_dir = root / ".tradegen"
            tg_dir.mkdir()
            tg_file = tg_dir / "snap.json"
            tg_file.write_bytes(json.dumps(snap).encode("utf-8"))
            with self.assertRaisesRegex(StudyError, "QGPT_SNAPSHOT_FILE"):
                qfb.read_feature_snapshot(tg_file, snap["snapshot_sha256"])

            # Pre-parse token cap rejected before json.loads
            p_many = root / "many.json"
            p_many.write_text('{"records":[' + ",".join(["{}"] * 1200) + "]}", encoding="utf-8")
            with patch.object(qfb.json, "loads", side_effect=AssertionError("json.loads called")), \
                    self.assertRaisesRegex(StudyError, "QGPT_SNAPSHOT_SIZE"):
                qfb.read_feature_snapshot(p_many, snap["snapshot_sha256"], budget=2)

    def test_merge_non_revision_known_at_and_s4_pin(self) -> None:
        r1 = _make_record("rec-1", as_of=1_764_000_000, issued_at=1_764_000_100)
        r2 = _make_record("rec-2", as_of=1_764_003_600, issued_at=1_764_003_700)
        s1 = _make_snapshot([r1])
        s2 = _make_snapshot([copy.deepcopy(r1), r2])

        merged = qfb.merge_feature_snapshots([s1, s2], receipt_times=[1_764_000_500, 1_764_004_000])
        for k, v in RESEARCH_FLAGS.items():
            self.assertEqual(merged[k], v)
        by_id = {item["record"]["record_id"]: item["known_at"] for item in merged["items"]}
        # First receipt for rec-1 was 1_764_000_500 (> issued_at 100), preserved across duplicate delivery
        self.assertEqual(by_id["rec-1"], 1_764_000_500)
        self.assertEqual(by_id["rec-2"], 1_764_004_000)

        # Revision of rec-1 is refused
        r1_rev = _make_record("rec-1", as_of=1_764_000_000, issued_at=1_764_000_100)
        r1_rev["relevance_0_100"] = 90.0
        s_rev = _make_snapshot([r1_rev])
        with self.assertRaisesRegex(StudyError, "QGPT_RECORD_REVISED"):
            qfb.merge_feature_snapshots([s1, s_rev])

        # S4 upstream model change refused
        s_other = copy.deepcopy(s1)
        s_other["model"]["version"] = "0.2.1"
        s_other = qfb.seal_feature_snapshot(s_other)
        with self.assertRaisesRegex(StudyError, "S4_UPSTREAM_IDENTITY_CHANGED"):
            qfb.merge_feature_snapshots([s1, s_other])


class SurfaceBEnvelopeAndCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_tool_vs_owner_mode_and_extract_ok_body(self) -> None:
        env_ok, payload = _make_envelope(mode="tool")
        self.assertIsNotNone(qfb.extract_ok_body(env_ok))
        res = qfb.recheck_envelope(env_ok, payload=payload, as_of="2026-11-24")
        self.assertTrue(res["envelope_ok"])

        # Unfound number in tool mode ok envelope is refused by validate_envelope
        bad_tool, _ = _make_envelope(
            mode="tool",
            numbers=[{"text": "99.9%", "found_in_payload": False}],
        )
        self.assertIsNone(qfb.extract_ok_body(bad_tool))
        with self.assertRaises(qfb.SchemaError):
            qfb.validate_envelope(bad_tool)

        # In owner mode, policy violations and unfound numbers are recorded without blocking schema
        owner_env, _ = _make_envelope(
            mode="owner",
            numbers=[{"text": "99.9%", "found_in_payload": False}],
            violations=["PF-1"],
        )
        self.assertIsNotNone(qfb.extract_ok_body(owner_env))

        # Abstain / blocked carry no display body
        abstain_env, _ = _make_envelope(status="abstain", body=None, numbers=[], reason_code="no_evidence")
        self.assertIsNone(qfb.extract_ok_body(abstain_env))

        # T-RESEARCH allowed in owner mode only
        with self.assertRaises(qfb.SchemaError):
            t_res_bad, _ = _make_envelope(
                task="T-RESEARCH",
                mode="tool",
                body={
                    "prereg": {
                        "title": "t", "hypothesis": "h", "null_hypothesis": "nh",
                        "data": {"sources": ["s"], "start": "2026-01-01", "end": "2026-06-01"},
                        "primary_metric": "m", "test": "w", "n_trials_planned": 1,
                        "stop_rule": "s", "as_of": "2026-06-01",
                    }
                },
                numbers=[],
            )
            qfb.validate_envelope(t_res_bad, validate_task_contract=True)

    def test_t_news_and_t_card_contracts(self) -> None:
        news_payload = {
            "article": {"source_id": "gdelt-events2", "title": "Hack news", "published_at": "2026-11-24T10:00:00Z"},
            "candidates": [{"target_kind": "macro", "entity_id": "CRYPTO_MKT"}],
        }
        judgment = {
            "target_kind": "macro",
            "entity_id": "CRYPTO_MKT",
            "relevance_0_100": 88.0,
            "event_type": "crypto_regulation_hack",
            "direction_probs": [0.1, 0.7, 0.2],
        }
        news_env, _ = _make_envelope(
            task="T-NEWS",
            mode="owner",
            payload=news_payload,
            body={"judgments": [judgment]},
            numbers=[],
        )
        qfb.recheck_envelope(news_env, payload=news_payload, as_of="2026-11-24T10:05:00Z")

        # Duplicate target in T-NEWS is refused
        with self.assertRaises(qfb.SchemaError):
            qfb.validate_t_news_output({"judgments": [judgment, copy.deepcopy(judgment)]})

        # Assemble didm-score-v0
        assembled = qfb.assemble_score_record(
            judgment,
            {
                "record_id": "score-1",
                "source_id": "gdelt-events2",
                "published_at": "2026-11-24T10:00:00Z",
                "received_at": "2026-11-24T10:05:00Z",
                "novelty_0_100": 80.0,
                "origin_cluster_id": "cl-1",
                "p_credibility": 0.85,
                "market_confirmation": "PENDING",
                "model_version": "qgpt-0.2",
                "prompt_sha256": "a" * 64,
            },
        )
        self.assertAlmostEqual(assembled["ess_like_0_100"], 20.0)

        # T-CARD accepts draft QSS v0 and refuses recorded QSS v0
        draft_card = {
            "qss_version": "qss-v0",
            "stage": "draft",
            "card_id": "strat_alpha",
            "kind": "strategy",
            "hypothesis": "Test hypothesis",
            "rules": {"entry": "none"},
            "market": {"venue": "KRW"},
            "data": {"source": "synthetic"},
            "costs": {"bps": 15},
            "protocol": {"wf": 1},
            "trials": {"n_planned": 2},
            "seed": 7,
        }
        qfb.validate_task_output("T-CARD", {"card": draft_card, "open_fields": ["costs.slippage"]})
        recorded_attempt = dict(draft_card, stage="recorded")
        with self.assertRaises(qfb.SchemaError):
            qfb.validate_task_output("T-CARD", {"card": recorded_attempt, "open_fields": []})

    def test_policy_numbers_citations_leakage_and_s4_rechecks(self) -> None:
        # Policy PF-1..PF-5 detection
        self.assertIn("PF-1", qfb.scan_policy("지금 당장 매수하세요"))
        self.assertIn("PF-5", qfb.scan_policy("원금 보장 수익"))

        # Number check: % / bp scaling and Korean date/span masking
        chk = qfb.number_check(
            "2026년 11월 24일 52주 기준 수익률 1.25% 및 비용 15bp (S&P 500 대비)",
            {"ret": 0.0125, "cost": 0.0015},
        )
        self.assertEqual(chk.not_found, ())
        self.assertEqual(chk.checked, 2)

        # Look-ahead date leakage -> S1_QGPT_LOOKAHEAD_LEAKAGE
        leak_env, leak_payload = _make_envelope(
            task="T-QA",
            mode="owner",
            payload={"question": "현황은?", "as_of": "2026-11-24", "language": "ko"},
            body={"answer": "2027년 3월에 발표된 정책에 따르면 변동성이 확대되었습니다."},
            citations=[{"source_id": "doc-1", "as_of": "2026-11-20"}],
            numbers=[],
        )
        with self.assertRaisesRegex(StudyError, "S1_QGPT_LOOKAHEAD_LEAKAGE"):
            qfb.recheck_envelope(
                leak_env,
                payload=leak_payload,
                evidence={"doc-1": "2026-11-20"},
            )

        # Citation dated after as_of -> S1_QGPT_LOOKAHEAD_LEAKAGE
        late_cit_env, late_cit_payload = _make_envelope(
            task="T-QA",
            mode="owner",
            payload={"question": "현황은?", "as_of": "2026-11-24", "language": "ko"},
            body={"answer": "변동성이 확대되었습니다."},
            citations=[{"source_id": "doc-late", "as_of": "2026-11-25"}],
            numbers=[],
        )
        with self.assertRaisesRegex(StudyError, "S1_QGPT_LOOKAHEAD_LEAKAGE"):
            qfb.recheck_envelope(
                late_cit_env,
                payload=late_cit_payload,
                evidence={"doc-late": "2026-11-25"},
            )

        # Upstream identity change -> S4_UPSTREAM_IDENTITY_CHANGED
        ok_env, ok_payload = _make_envelope(mode="owner")
        with self.assertRaisesRegex(StudyError, "S4_UPSTREAM_IDENTITY_CHANGED"):
            qfb.recheck_envelope(
                ok_env,
                payload=ok_payload,
                pinned_model={"id": "qwen2.5-7b", "adapter": "adapter-NEW", "prompt_version": "p0"},
            )

    def test_attempt_ledger_regime_b_chain_and_batch_scorer(self) -> None:
        # Build a valid Regime B UTF-8 AttemptLedger with Korean note
        att = {
            "kind": "attempt",
            "family": "qgpt-news-v0",
            "objective": "f1_macro",
            "data_version": "didm-20261124",
            "hyperparameters": {"lr": 0.0001},
            "seed": 42,
            "model_version": "qwen2.5-7b",
            "run_utc": "2026-11-24T12:00:00Z",
            "note": "첫 번째 기준선 시도",
        }
        att["attempt_id"] = qfb.attempt_id(att)
        att["prev_sha256"] = None
        att["row_sha256"] = sha256_utf8({k: v for k, v in att.items() if k not in ("prev_sha256", "row_sha256")})
        line1 = canonical_utf8_bytes(att)

        res_row = {
            "kind": "result",
            "attempt_id": att["attempt_id"],
            "metrics": {"f1": 0.74},
            "run_utc": "2026-11-24T12:30:00Z",
            "prev_sha256": sha256_raw(line1),
        }
        res_row["row_sha256"] = sha256_utf8({k: v for k, v in res_row.items() if k not in ("prev_sha256", "row_sha256")})
        line2 = canonical_utf8_bytes(res_row)
        head = sha256_raw(line2)

        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "attempts.jsonl"
            ledger_path.write_bytes(line1 + b"\n" + line2 + b"\n")
            chk = qfb.verify_attempt_ledger(ledger_path, pinned_head=head)
            self.assertTrue(chk.ok)
            self.assertEqual(chk.n_rows, 2)
            self.assertFalse(qfb.verify_attempt_ledger(ledger_path, pinned_head="0" * 64).ok)

            # Tampered line breaks chain
            ledger_path.write_bytes(line1 + b"\n" + line2.replace(b"0.74", b"0.99") + b"\n")
            self.assertFalse(qfb.verify_attempt_ledger(ledger_path).ok)

            # Batch scorer CLI & API test
            e1, _ = _make_envelope(mode="tool", latency_ms=100)
            e2, _ = _make_envelope(mode="tool", status="abstain", body=None, numbers=[], reason_code="after_as_of", latency_ms=250)
            e3, _ = _make_envelope(mode="tool", status="blocked", body=None, numbers=[], violations=["PF-1"], reason_code="policy", latency_ms=50)
            eval_items = [
                {"id": "i1", "expect": {"answerable": True, "policy_trap": False}, "envelope": e1},
                {"id": "i2", "expect": {"answerable": False, "policy_trap": False}, "envelope": e2},
                {"id": "i3", "expect": {"answerable": True, "policy_trap": True}, "envelope": e3},
            ]
            scored = qfb.score_envelopes(eval_items)
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(scored[k], v)
            self.assertEqual(scored["n_items"], 3)
            self.assertEqual(scored["hallucination_rate"]["rate"], 0.0)
            self.assertEqual(scored["abstain_recall"]["rate"], 1.0)
            self.assertEqual(scored["policy_miss_rate"]["rate"], 0.0)
            self.assertEqual(scored["leakage_rate"]["hits"], 1)
            self.assertEqual(scored["latency_ms"], {"p50": 100.0, "p95": 250.0})

            jsonl_path = Path(tmp) / "eval.jsonl"
            out_path = Path(tmp) / "score_report.json"
            jsonl_path.write_bytes(b"\n".join(canonical_utf8_bytes(i) for i in eval_items) + b"\n")
            cmd = [sys.executable, "-B", "-m", "tools.research.quantgpt_feature_bridge",
                   "--score-envelopes", str(jsonl_path), "--output", str(out_path)]
            proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out_path.is_file())


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
