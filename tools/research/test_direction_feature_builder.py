"""Unit tests for direction_feature_builder. Synthetic data only; network patched."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
import json
import tempfile
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from tools.research import didm_run_log as rl
from tools.research import didm_source_bridge as bridge
from tools.research import direction_feature_builder as dfb
from tools.research import quantgpt_feature_bridge as qfb
from tools.research._study_common import (
    StudyError,
    RESEARCH_FLAGS,
    UTC,
    assert_all_isolation_invariants,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_didm_row(
    seq: int,
    *,
    source_id: str = "gdelt-events2",
    item_id: str = "20261124120000:ev1",
    kind: str = "gdelt_event",
    published_at: str = "2026-11-24T12:00:00+00:00",
    valid_at: str = "2026-11-24T12:00:00+00:00",
    received_at: str = "2026-11-24T12:02:00+00:00",
    payload_obj: dict | None = None,
) -> dict:
    payload_str = bridge.canonical(payload_obj if payload_obj is not None else {"slot": item_id[:14], "v": 1})
    return {
        "seq": seq,
        "source_id": source_id,
        "item_id": item_id,
        "kind": kind,
        "published_at": published_at,
        "valid_at": valid_at,
        "received_at": received_at,
        "payload": payload_str,
        "payload_sha256": bridge.sha256(payload_str.encode("utf-8")),
    }


def _inspect_rows(rows: list[dict], as_of_iso: str) -> dict:
    export_doc = {
        "format": bridge.EXPORT_FORMAT,
        "contract": dict(bridge.CONTRACT),
        "rows": rows,
        "scores": [],
    }
    raw = bridge.canonical(export_doc).encode("utf-8")
    return bridge.inspect_snapshot(raw, input_kind="export", as_of=as_of_iso)


class DirectionFeatureBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_exact_reselection_parity_with_didm_source_bridge_across_cutoffs_revisions_and_ties(self) -> None:
        rows = [
            # Item A: v1 received at 10:00Z, v2 revised at 12:00Z
            _make_didm_row(1, source_id="alfred", item_id="CPIAUCSL:2026-09", kind="alfred_vintage",
                           valid_at="2026-10-15T00:00:00+00:00", received_at="2026-11-24T10:00:00+00:00",
                           payload_obj={"series_id": "CPIAUCSL", "val": "314.0"}),
            _make_didm_row(2, source_id="alfred", item_id="CPIAUCSL:2026-09", kind="alfred_vintage",
                           valid_at="2026-10-15T00:00:00+00:00", received_at="2026-11-24T12:00:00+00:00",
                           payload_obj={"series_id": "CPIAUCSL", "val": "314.2"}),
            # Item B: tie at exact same received_at (11:00Z) broken by higher payload_sha256!
            _make_didm_row(3, source_id="ecos", item_id="722Y001:0101000:202610", kind="ecos_observation",
                           valid_at="2026-10-10T09:00:00+09:00", received_at="2026-11-24T11:00:00+00:00",
                           payload_obj={"stat_code": "722Y001", "item_code": "0101000", "val": "3.25"}),
            _make_didm_row(4, source_id="ecos", item_id="722Y001:0101000:202610", kind="ecos_observation",
                           valid_at="2026-10-10T09:00:00+09:00", received_at="2026-11-24T11:00:00+00:00",
                           payload_obj={"stat_code": "722Y001", "item_code": "0101000", "val": "3.50"}),
            # Item C: future item received at 15:00Z
            _make_didm_row(5, source_id="gdelt-events2", item_id="20261124150000:ev1", kind="gdelt_event",
                           valid_at="2026-11-24T15:00:00+00:00", received_at="2026-11-24T15:02:00+00:00"),
        ]
        # Split across two daily-style inspection reports (captured at 23:59Z) and merge
        rep_part1 = _inspect_rows(rows[:3], "2026-11-24T23:59:59+00:00")
        rep_part2 = _inspect_rows(rows[3:], "2026-11-24T23:59:59+00:00")
        merged = dfb.merge_didm_reports([rep_part1, rep_part2])

        cutoffs = [
            "2026-11-24T09:30:00+00:00",
            "2026-11-24T10:30:00+00:00",
            "2026-11-24T20:00:00+09:00",  # 11:00Z exact tie boundary with +09:00 offset
            "2026-11-24T12:00:00+00:00",
            "2026-11-24T18:00:00+00:00",
        ]
        for cutoff in cutoffs:
            with self.subTest(cutoff=cutoff):
                expected = _inspect_rows(rows, cutoff)["selected_record_sha256"]
                actual = [r["record_sha256"] for r in dfb.reselect_didm_at(merged, cutoff)]
                self.assertEqual(actual, expected)

    def test_price_features_p1_to_p4_and_late_backfill_missingness(self) -> None:
        step = 3600
        t0 = 1_764_000_000
        bars = [
            {"end": t0 + i * step, "known_at": t0 + i * step + 5, "return_bps": 10 + (i % 5)}
            for i in range(30)
        ]
        # Make bar 26 late-backfilled (known only at bar 28 + 10)
        bars[26]["known_at"] = bars[28]["end"] + 10

        table = dfb.build_feature_table(
            market="KRW-BTC",
            step_seconds=step,
            bars=bars,
            target_as_of_times=[bars[25]["end"], bars[27]["end"], bars[29]["end"]],
            feature_names=("P1", "P2", "P3", "P4"),
        )
        for k, v in RESEARCH_FLAGS.items():
            self.assertEqual(table[k], v)

        r25, r27, r29 = table["rows"]
        # At bar 25 end, bars 1..24 are all known on time -> complete!
        self.assertTrue(r25["complete"])
        self.assertAlmostEqual(r25["features"]["P1"], math.log1p(bars[24]["return_bps"] / 10000.0))
        # Bar 25's own return_bps is NOT in P1 at bar 25's as_of (known_at = end + 5 > end)
        self.assertNotAlmostEqual(r25["features"]["P1"], math.log1p(bars[25]["return_bps"] / 10000.0))

        # At bar 27 end, bar 26 (m=1) has known_at > as_of -> P1..P4 are all None!
        self.assertFalse(r27["complete"])
        self.assertEqual(r27["features"], {"P1": None, "P2": None, "P3": None, "P4": None})

        # At bar 29 end, bar 26 is now known (known_at <= bar 29 end) -> complete again!
        self.assertTrue(r29["complete"])

    def test_d1_unchanged_refetch_stays_zero_revision_fires_and_missed_schedule_is_none(self) -> None:
        step = 3600
        day1 = 1_764_000_000  # Day 1 00:00-ish grid
        bars = [{"end": day1 + i * step, "known_at": day1 + i * step + 2, "return_bps": 5} for i in range(100)]

        # Vintage first received at day1 + 2h; re-fetched UNCHANGED at day1 + 50h; revised at day1 + 75h
        t_first = datetime.fromtimestamp(day1 + 2 * step - 600, UTC).isoformat()
        t_refetch = datetime.fromtimestamp(day1 + 50 * step - 600, UTC).isoformat()
        t_revised = datetime.fromtimestamp(day1 + 75 * step - 600, UTC).isoformat()

        didm_rows = [
            _make_didm_row(1, source_id="alfred", item_id="CPIAUCSL:2026-10", kind="alfred_vintage",
                           received_at=t_first, payload_obj={"series_id": "CPIAUCSL", "val": "315.0"}),
            _make_didm_row(2, source_id="alfred", item_id="CPIAUCSL:2026-10", kind="alfred_vintage",
                           received_at=t_refetch, payload_obj={"series_id": "CPIAUCSL", "val": "315.0"}),
            _make_didm_row(3, source_id="alfred", item_id="CPIAUCSL:2026-10", kind="alfred_vintage",
                           received_at=t_revised, payload_obj={"series_id": "CPIAUCSL", "val": "315.4"}),
        ]
        rep = _inspect_rows(didm_rows, datetime.fromtimestamp(day1 + 99 * step, UTC).isoformat())

        # Schedule runs succeed every hour except at hour 90 where ecos fails
        alfred_runs = [{"started_at": day1 + i * step - 300, "finished_at": day1 + i * step - 200, "succeeded": True} for i in range(100)]
        ecos_runs = [
            {"started_at": day1 + i * step - 300, "finished_at": day1 + i * step - 200, "succeeded": (i != 90)}
            for i in range(100)
        ]
        run_log = {"slot_known_epoch": {}, "source_runs": {"alfred": alfred_runs, "ecos": ecos_runs}}

        targets = [
            day1 + 3 * step,   # Within 24h of first receipt -> 1.0
            day1 + 30 * step,  # >24h after first receipt -> 0.0
            day1 + 51 * step,  # 1h after UNCHANGED re-fetch -> MUST stay 0.0!
            day1 + 76 * step,  # 1h after payload revision -> 1.0!
            day1 + 90 * step,  # Scheduled ecos run failed -> None!
        ]
        table = dfb.build_feature_table(
            market="KRW-BTC",
            step_seconds=step,
            bars=bars,
            target_as_of_times=targets,
            feature_names=("D1",),
            didm_reports=[rep],
            run_log_summary=run_log,
        )
        d1_vals = [r["features"]["D1"] for r in table["rows"]]
        self.assertEqual(d1_vals, [1.0, 0.0, 0.0, 1.0, None])

    def test_d2_ratio_and_single_missing_slot_makes_exact_24_bars_missing(self) -> None:
        step = 3600
        # 8 days of 15-minute slots so we have a 7-day lookback + 26 evaluation hours
        t_start = 1_764_000_000
        eval_t0 = t_start + 7 * 86400
        bars = [{"end": eval_t0 + i * step, "known_at": eval_t0 + i * step + 2, "return_bps": 1} for i in range(26)]

        all_slot_epochs = list(range(t_start, eval_t0 + 26 * step, 900))
        missing_slot = eval_t0 - 900  # 11:45-equivalent slot right before eval_t0
        slot_known_epoch = {s: s + 60 for s in all_slot_epochs if s != missing_slot}

        # Put 2 GDELT events per slot in the last 24h after missing_slot clears, 1 event per slot earlier
        didm_rows = []
        seq = 1
        for s in all_slot_epochs:
            if s == missing_slot:
                continue
            stamp = rl.slot_epoch_to_stamp(s)
            ts_iso = datetime.fromtimestamp(s, UTC).isoformat()
            recv_iso = datetime.fromtimestamp(s + 60, UTC).isoformat()
            didm_rows.append(_make_didm_row(seq, item_id=f"{stamp}:a", published_at=ts_iso, valid_at=ts_iso, received_at=recv_iso))
            seq += 1
        rep = _inspect_rows(didm_rows, datetime.fromtimestamp(eval_t0 + 26 * step, UTC).isoformat())

        table = dfb.build_feature_table(
            market="KRW-BTC",
            step_seconds=step,
            bars=bars,
            feature_names=("D2",),
            didm_reports=[rep],
            run_log_summary={"slot_known_epoch": slot_known_epoch, "source_runs": {}},
        )
        d2_vals = [r["features"]["D2"] for r in table["rows"]]
        # Bars 0..23 (exact 24 bars!) have missing_slot in their 96-slot numerator -> None
        self.assertEqual(d2_vals[:24], [None] * 24)
        # Bar 24 & 25 have all 96 numerator slots present and 671/672 >= 95% denominator slots -> 1.0!
        self.assertAlmostEqual(d2_vals[24], 1.0)
        self.assertAlmostEqual(d2_vals[25], 1.0)

    def test_d3_pinned_version_export_receipt_and_q1_categorical(self) -> None:
        step = 3600
        t0 = 1_764_000_000
        bars = [{"end": t0 + i * step, "known_at": t0 + i * step + 2, "return_bps": 2} for i in range(6)]
        pinned_didm = {"model_version": "didm-v0.1", "prompt_sha256": "a" * 64}
        pinned_qgpt = {
            "name": "qgpt", "version": "0.2", "sha256": "b" * 64,
            "training_cutoff": t0 - 100_000, "frozen_at": t0 - 50_000,
        }

        def make_score(rid: str, ev_type: str, p_pos: float, p_neg: float, model_ver: str = "didm-v0.1", recv_ts: int = t0 + step) -> dict:
            p0 = round(1.0 - p_pos - p_neg, 6)
            probs = [p_pos, p_neg, p0]
            return {
                "source_record_sha256": "f" * 64,
                "score": {
                    "record_id": rid,
                    "source_id": "gdelt-events2",
                    "target_kind": "macro",
                    "entity_id": "CRYPTO",
                    "published_at": datetime.fromtimestamp(recv_ts - 60, UTC).isoformat(),
                    "received_at": datetime.fromtimestamp(recv_ts, UTC).isoformat(),
                    "relevance_0_100": 80.0,
                    "ess_like_0_100": qfb.ess_like(p_pos, p_neg),
                    "novelty_0_100": 70.0,
                    "origin_cluster_id": "cl-1",
                    "event_type": ev_type,
                    "direction_probs": probs,
                    "uncertainty_entropy": qfb.shannon_entropy(probs),
                    "p_credibility": 0.9,
                    "market_confirmation": "PENDING",
                    "model_version": model_ver,
                    "prompt_sha256": "a" * 64,
                },
            }

        # Export 1 received at t0 + 1800: 0 matching events -> D3 == 50.0 at t0 + 3600!
        exp1 = {"format": bridge.EXPORT_FORMAT, "contract": dict(bridge.CONTRACT), "rows": [], "scores": []}
        # Export 2: score received_at is t0 + 3700, but export arrives late at t0 + 3*step + 100!
        # Also includes 1 unpinned model_version score that must be counted & excluded.
        exp2 = {
            "format": bridge.EXPORT_FORMAT,
            "contract": dict(bridge.CONTRACT),
            "rows": [],
            "scores": [
                make_score("s-pinned", "monetary_policy", 0.8, 0.1, "didm-v0.1", recv_ts=t0 + 3700),
                make_score("s-unpinned", "monetary_policy", 0.0, 1.0, "didm-v0.2-UNPINNED", recv_ts=t0 + 3700),
            ],
        }

        source_time = exp2["scores"][0]["score"]["published_at"]
        source = _make_didm_row(1, published_at=source_time, valid_at=source_time, received_at=source_time)
        exp2["rows"] = [source]
        for wrapper in exp2["scores"]:
            wrapper["source_record_sha256"] = bridge.check_row(source)["record_sha256"]

        # Q1 snapshot: risk event issued at t0 + 3700, snapshot received at t0 + 2*step + 10
        q_rec = {
            "record_id": "q-1",
            "source_id": "gdelt-events2",
            "as_of": t0 + 3650,
            "issued_at": t0 + 3700,
            "published_at": t0 + 3600,
            "target_kind": "macro",
            "entity_id": "BTC_REG",
            "event_type": "crypto_regulation_hack",
            "direction_probs": ["0.100000", "0.800000", "0.100000"],
            "relevance_0_100": 90.0,
            "novelty_0_100": 80.0,
            "ess_like_0_100": 15.0,
            "uncertainty_entropy": qfb.shannon_entropy([0.1, 0.8, 0.1]),
            "p_credibility": "0.950000",
            "market_confirmation": "PENDING",
            "origin_cluster_id": "cl-q1",
        }
        q_snap0 = qfb.seal_feature_snapshot({
            "format": qfb.FEATURE_SNAPSHOT_FORMAT,
            "producer": "quantgpt",
            "model": pinned_qgpt,
            "generated_at": t0 + 100,
            "records": [],
        })
        q_snap1 = qfb.seal_feature_snapshot({
            "format": qfb.FEATURE_SNAPSHOT_FORMAT,
            "producer": "quantgpt",
            "model": pinned_qgpt,
            "generated_at": t0 + 3800,
            "records": [q_rec],
        })

        table = dfb.build_feature_table(
            market="KRW-BTC",
            step_seconds=step,
            bars=bars,
            target_as_of_times=[t0, t0 + step, t0 + 2 * step, t0 + 3 * step, t0 + 4 * step],
            feature_names=("D3", "Q1"),
            didm_v0_exports=[(exp1, t0 + 1800), (exp2, t0 + 3 * step + 100)],
            quantgpt_snapshots=[(q_snap0, t0 + 1800), (q_snap1, t0 + 2 * step + 10)],
            pinned_didm_v0=pinned_didm,
            pinned_quantgpt_model=pinned_qgpt,
        )
        self.assertEqual(table["unpinned_didm_score_count"], 1)
        rows = table["rows"]
        # At t0: no delivery received yet -> both None
        self.assertEqual(rows[0]["features"], {"D3": None, "Q1": None})
        # At t0 + step: exp1 & q_snap0 delivered with 0 events -> D3=50.0, Q1=0.0
        self.assertEqual(rows[1]["features"], {"D3": 50.0, "Q1": 0.0})
        # At t0 + 2*step: q_snap1 arrived at t0 + 2*step + 10 (> as_of!), so Q1 still 0.0!
        self.assertEqual(rows[2]["features"], {"D3": 50.0, "Q1": 0.0})
        # At t0 + 3*step: q_snap1 is now known -> Q1=1.0; exp2 arrives at t0 + 3*step + 100 -> D3 still 50.0!
        self.assertEqual(rows[3]["features"], {"D3": 50.0, "Q1": 1.0})
        # At t0 + 4*step: exp2 is now known -> D3 = 50 + 50*(0.8 - 0.1) = 85.0 (unpinned score ignored!)
        self.assertEqual(rows[4]["features"], {"D3": 85.0, "Q1": 1.0})


class ScoreEvidenceTests(unittest.TestCase):
    def setUp(self):
        from tools.research.test_didm_source_bridge import row, score, linked
        self.raw = row()
        self.score = score(self.raw)
        self.pin = {k: self.score[k] for k in ("model_version", "prompt_sha256")}
        self.at = int(bridge.timestamp(self.raw["received_at"]).timestamp())
        self.export = {"contract": bridge.CONTRACT, "format": bridge.EXPORT_FORMAT,
                       "rows": [self.raw], "scores": [linked(self.raw, self.score)]}

    def test_unlinked_score_modified_contract_and_absent_score_array_refuse(self):
        for doc, reason in ((dict(self.export, rows=[]), "DIDM_SCORE_SOURCE_LINK_MISSING"),
                            (dict(self.export, contract={}), "DIDM_EXCHANGE_CONTRACT_MISMATCH"),
                            ({"format": bridge.EXPORT_FORMAT}, "DIDM_EXCHANGE_SCHEMA_MISMATCH")):
            with self.subTest(reason=reason), self.assertRaisesRegex(StudyError, reason):
                dfb.prepare_didm_v0_scores([(doc, self.at)], pinned_didm_v0=self.pin)
        with self.assertRaisesRegex(StudyError, "DIDM_SCORE_PIN_REQUIRED"):
            dfb.prepare_didm_v0_scores([(self.export, self.at)])

    def test_first_delivery_and_late_supersession_use_their_actual_availability(self):
        from tools.research.test_didm_source_bridge import row
        later_time = (bridge.timestamp(self.raw["received_at"]) + timedelta(seconds=10)).isoformat()
        update = row(2, received=later_time, value=99)
        refreshed = dict(self.export, rows=[update], scores=[])
        sources = [(refreshed, self.at+90), (self.export, self.at+45), (self.export, self.at+2)]
        scores, arrivals, _ = dfb.prepare_didm_v0_scores(sources, pinned_didm_v0=self.pin)
        def at(when):
            return dfb.compute_d3_at(scores, arrivals, self.at+when, d3_event_types={"inflation"})
        self.assertIsNone(at(1))
        self.assertEqual((at(2), at(89), at(90)), (70, 70, 50))
        changed = dict(self.score, novelty_0_100=54)
        wrapper = dict(self.export["scores"][0], score=changed)
        with self.assertRaisesRegex(StudyError, "DIDM_SCORE_REVISION_CONFLICT"):
            dfb.prepare_didm_v0_scores(sources + [(dict(self.export, scores=[wrapper]), self.at+5)],
                                       pinned_didm_v0=self.pin)

    def test_cli_uses_logged_bytes_and_reports_replaced_export(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            export, history, logs = root/"export.json", root/"bars.json", root/"log"
            export.write_text(json.dumps(self.export))
            rl.record_didm_export(logs, export, received_at=self.at)
            cut = self.at + 5
            history.write_text(json.dumps([{"end": cut, "known_at": cut+1, "return_bps": 1}]))
            args = ["--features", "D3", "--market", "KRW-BTC", "--step-seconds", "3600",
                    "--history", str(history), "--didm-score-model", self.pin["model_version"],
                    "--didm-score-prompt-sha256", self.pin["prompt_sha256"], "--run-log-dir", str(logs)]
            good, bad = root/"features.json", root/"bad.json"
            self.assertEqual(dfb.main([*args, "--output", str(good)]), 0)
            self.assertEqual(json.loads(good.read_text())["rows"][0]["features"]["D3"], 50.0)
            export.write_text(json.dumps(dict(self.export, scores=[])))
            self.assertEqual(dfb.main([*args, "--output", str(bad)]), 2)
            self.assertFalse(bad.exists())


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
