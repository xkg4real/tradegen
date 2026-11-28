"""End-to-end synthetic integration test chaining Modules 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> adapter -> 7 -> 8."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import random
import socket
import tempfile
import unittest
from unittest.mock import patch

from tools.research import adaptive_bid_gap_preview as preview
from tools.research import didm_run_log as rl
from tools.research import didm_source_bridge as bridge
from tools.research import direction_feature_builder as dfb
from tools.research import direction_forecast_adapter as adapter
from tools.research import direction_forecast_writer as dfw
from tools.research import direction_model_fit as dmf
from tools.research import direction_stage1_evaluator as s1e
from tools.research import direction_stage2_replay as s2r
from tools.research import quantgpt_feature_bridge as qfb
from tools.research import upbit_price_recorder as upr
from tools.research import upbit_quote_recorder as uqr
from tools.research.test_didm_run_log import _insert_didm_row
from tools.research.test_upbit_price_recorder import FakeClock, _candle_json, _reply
from tools.research._study_common import (
    RESEARCH_FLAGS,
    UTC,
    assert_all_isolation_invariants,
    kst_date_iso,
    kst_day_str,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class EndToEndDirectionPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_full_pipeline_modules_0_through_8_and_adapter_parity(self) -> None:
        # Timeline (hourly bars, step = 3600):
        # - 7 days warmup (168 bars) so 672 GDELT 15-min slots exist
        # - 144 training bars (6 days)
        # - 216 Stage 1 evaluation bars (9 days; total = 528 bars <= 1024!)
        step = 3600
        horizon = 7200
        t0 = 1_764_000_000  # divisible by 3600
        n_bars = 528
        rng = random.Random(20261127)

        # Pseudo-random 24-hour news regimes (balanced in both halves, non-periodic so P3 cannot cheat),
        # plus zero-sum +-90 bps 1-bar chop so P1..P4 are noisy while 2-bar outcome + DIDM/QuantGPT news are clean!
        n_days = (n_bars // 24) + 2
        day_regimes = [rng.choice([True, False]) for _ in range(n_days)]
        # Ensure balanced up/down days in training and evaluation
        day_regimes[7:13] = [True, True, False, True, False, False]
        day_regimes[13:23] = [True, False, False, True, True, False, True, False, False, True]

        bar_bps = [0] * n_bars
        for m in range(n_bars // 2):
            origin_idx = 2 * m
            day_idx = origin_idx // 24
            true_bull = day_regimes[day_idx]
            realized_up = true_bull if (rng.random() < 0.96) else (not true_bull)
            per_bar = 28 if realized_up else -28
            chop = rng.choice([-85, 85])
            if origin_idx + 1 < n_bars:
                bar_bps[origin_idx + 1] = per_bar + chop
            if origin_idx + 2 < n_bars:
                bar_bps[origin_idx + 2] = per_bar - chop

        candles_by_end: dict[int, dict] = {}
        price_level = 100_000_000
        candles_by_end[t0 - step] = _candle_json(t0 - step, str(price_level), str(price_level), step=step)
        for i in range(n_bars):
            end_ts = t0 + i * step
            next_price = max(1000, int(round(price_level * (1.0 + bar_bps[i] / 10000.0))))
            candles_by_end[end_ts] = _candle_json(end_ts, str(price_level), str(next_price), step=step)
            price_level = next_price

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            price_arc = root / "price_arc"
            log_dir = root / "didm_logs"
            stores_root = root / "didm_stores"
            reports_dir = root / "didm_reports"
            reports_dir.mkdir(parents=True, exist_ok=True)

            # 1. Module 2: Poll bar 0 live, backfill warmup bars 1..167 before train_start, then poll 168..n_bars-1 live hourly!
            p_clock = FakeClock(t0 + 5.0)

            def price_transport(path: str, params: dict) -> upr.HttpReply:
                if path == "/v1/candles/minutes/60":
                    to_ts = int(datetime.fromisoformat(params["to"].replace("Z", "+00:00")).timestamp())
                    cnt = int(params["count"])
                    avail = [c for e, c in sorted(candles_by_end.items(), reverse=True) if e <= to_ts][:cnt]
                    return _reply(avail)
                return _reply([{"market": "KRW-BTC", "orderbook_units": [{"bid_price": 99_995_000, "ask_price": 100_005_000}]}])

            p_rec = upr.UpbitPriceRecorder(price_arc, upr.PriceRecorderConfig("KRW-BTC", step), transport=price_transport, clock=p_clock)
            with patch("os.fsync", return_value=None):
                p_clock._wall = t0 + 5.0
                p_rec.poll_once()
                p_clock._wall = t0 + 167 * step + 5.0
                p_rec.poll_once()
                for i in range(168, n_bars):
                    p_clock._wall = t0 + i * step + 5.0
                    p_rec.poll_once()

            _, recorded_bars, _ = upr.read_recorded_bars(price_arc)
            self.assertEqual(len(recorded_bars), n_bars)
            hurdle_bps = upr.compute_warmup_hurdle_bps(recorded_bars[:168])
            self.assertIn(hurdle_bps, (16, 17))

            hist_path = root / "stage1_history.json"
            upr.export_history(
                price_arc, hist_path, scope="upbit-krw-spot", source_id="upbit-hourly-v1", max_bars=1024, exported_at=t0 + n_bars * step + 10
            )
            history_doc = json.loads(hist_path.read_text(encoding="utf-8"))

            # 2. Module 0 + Module 3: DIDM SQLite store, bridge snapshot, and DIDM V0 score exports
            all_slots = list(range(t0 - 900, t0 + n_bars * step, 900))
            slot_known_epoch = {s: s + 60 for s in all_slots}

            sample_store = stores_root / f"kst_{kst_day_str(t0)}" / "didm_store.sqlite"
            for d in range(6, n_days):
                day_start_ts = t0 + d * 24 * step
                if day_regimes[d] and day_start_ts < t0 + n_bars * step:
                    slot_s = max(t0, day_start_ts - 900)
                    stamp = rl.slot_epoch_to_stamp(slot_s)
                    ts_iso = datetime.fromtimestamp(slot_s, UTC).isoformat()
                    recv_iso = datetime.fromtimestamp(slot_s + 60, UTC).isoformat()
                    _insert_didm_row(sample_store, item_id=f"{stamp}:day{d}", published_at=ts_iso, valid_at=ts_iso, received_at=recv_iso)

            rep_path = reports_dir / "didm_inspection.json"
            rl.take_bridge_snapshot(
                log_dir,
                sample_store,
                rep_path,
                as_of_iso=datetime.fromtimestamp(t0 + n_bars * step, UTC).isoformat(),
                captured_at=t0 + n_bars * step + 20,
            )
            didm_report = json.loads(rep_path.read_text(encoding="utf-8"))

            # Build daily DIDM V0 score exports (D3) & Module 1 QuantGPT snapshots (Q1) at the start of each 24h regime!
            pinned_didm_v0 = {"model_version": "didm-v0.1", "prompt_sha256": "d" * 64}
            pinned_qgpt_sha = qfb.quantgpt_model_sha256("qwen2.5-7b", "lora-1", "p1", {"temperature": 0.0})
            pinned_qgpt_model = {
                "name": "qgpt-judge",
                "version": "0.2.0",
                "sha256": pinned_qgpt_sha,
                "training_cutoff": t0 - 100_000,
                "frozen_at": t0 - 50_000,
            }

            didm_v0_exports: list[tuple[dict, int]] = []
            q_records: list[dict] = []
            for d in range(6, n_days):
                day_ts = t0 + d * 24 * step - 600  # 10 minutes before bar d*24 so known at bar d*24!
                if day_ts <= t0:
                    continue
                bull = day_regimes[d]
                p_pos, p_neg = (0.90, 0.05) if bull else (0.05, 0.90)
                probs_f = [p_pos, p_neg, 0.05]
                score_obj = {
                    "record_id": f"v0-day-{d}",
                    "source_id": "gdelt-events2",
                    "target_kind": "macro",
                    "entity_id": "CRYPTO_MACRO",
                    "published_at": datetime.fromtimestamp(day_ts - 60, UTC).isoformat(),
                    "received_at": datetime.fromtimestamp(day_ts, UTC).isoformat(),
                    "relevance_0_100": 90.0,
                    "ess_like_0_100": qfb.ess_like(p_pos, p_neg),
                    "novelty_0_100": 80.0,
                    "origin_cluster_id": f"cl-v0-{d}",
                    "event_type": "monetary_policy",
                    "direction_probs": probs_f,
                    "uncertainty_entropy": qfb.shannon_entropy(probs_f),
                    "p_credibility": 0.95,
                    "market_confirmation": "PENDING",
                    "model_version": "didm-v0.1",
                    "prompt_sha256": "d" * 64,
                }
                exp_doc = {
                    "format": bridge.EXPORT_FORMAT,
                    "contract": dict(bridge.CONTRACT),
                    "rows": [],
                    "scores": [{"source_record_sha256": "e" * 64, "score": score_obj}],
                }
                didm_v0_exports.append((exp_doc, day_ts + 30))

                q_records.append({
                    "record_id": f"qrec-{d}",
                    "source_id": "gdelt-events2",
                    "as_of": day_ts,
                    "issued_at": day_ts + 20,
                    "published_at": day_ts - 60,
                    "target_kind": "macro",
                    "entity_id": "MACRO_NEWS",
                    "event_type": "monetary_policy" if bull else "earnings",
                    "direction_probs": ["0.600000", "0.200000", "0.200000"],
                    "relevance_0_100": 80.0,
                    "novelty_0_100": 75.0,
                    "ess_like_0_100": 70.0,
                    "uncertainty_entropy": qfb.shannon_entropy([0.6, 0.2, 0.2]),
                    "p_credibility": "0.900000",
                    "market_confirmation": "PENDING",
                    "origin_cluster_id": f"cl-q-{d}",
                })

            q_snap = qfb.seal_feature_snapshot({
                "format": qfb.FEATURE_SNAPSHOT_FORMAT,
                "producer": "quantgpt",
                "model": pinned_qgpt_model,
                "generated_at": max(r["issued_at"] for r in q_records) + 60,
                "records": q_records,
            })
            q_snap_path = root / "qgpt_features.json"
            q_snap_path.write_text(json.dumps(q_snap), encoding="utf-8")
            rl.record_quantgpt_receipt(log_dir, q_snap_path, received_at=t0 + 60)

            # 3. Module 4: Build point-in-time feature table (P1..P4, D2, D3, Q1)
            ftable = dfb.build_feature_table(
                market="KRW-BTC",
                step_seconds=step,
                bars=history_doc["bars"],
                target_as_of_times=[b["end"] for b in history_doc["bars"][168:]],
                feature_names=("P1", "P2", "P3", "P4", "D2", "D3", "Q1"),
                didm_reports=[didm_report],
                run_log_summary={"slot_known_epoch": slot_known_epoch, "source_runs": {}},
                didm_v0_exports=didm_v0_exports,
                quantgpt_snapshots=[(q_snap, t0 + 60)],
                d3_cadence_seconds=48 * 3600,
                q1_cadence_seconds=n_bars * step,
                pinned_didm_v0=pinned_didm_v0,
                pinned_quantgpt_model=pinned_qgpt_model,
                feature_builder_commit="a" * 40,
            )
            self.assertEqual(ftable["missing_row_count"], 0)

            # 4. Module 5: Fit and freeze M, B1, and B0 on training bars [168 .. 310]
            train_start = history_doc["bars"][168]["end"]
            train_end = history_doc["bars"][310]["end"]
            frozen_at = train_end + 300
            eval_start = history_doc["bars"][312]["end"]
            eval_end = history_doc["bars"][-1]["end"]

            fitted = dmf.fit_and_freeze_models(
                feature_table=ftable,
                bars=history_doc["bars"],
                train_start=train_start,
                train_end=train_end,
                frozen_at=frozen_at,
                horizon_seconds=horizon,
                hurdle_bps=hurdle_bps,
                l2_penalty=1.0,
                heldout_seconds=48 * 3600,
            )

            # 5. Module 6: Write Stage 1 batch snapshots + sidecar manifests for M, B1, B0
            s1_write_at = eval_end + 60
            idx_dir = root / "forecast_idx"
            m_snap, m_man, m_file, _ = dfw.write_forecast_snapshot(
                root / "m_stage1.json", artifact=fitted["M"], feature_table=ftable, issued_at=s1_write_at, index_dir=idx_dir
            )
            b1_snap, b1_man, b1_file, _ = dfw.write_forecast_snapshot(
                root / "b1_stage1.json", artifact=fitted["B1"], feature_table=ftable, issued_at=s1_write_at, index_dir=idx_dir
            )
            b0_snap, _, b0_file, _ = dfw.write_forecast_snapshot(
                root / "b0_stage1.json", artifact=fitted["B0"], feature_table=ftable, issued_at=s1_write_at, index_dir=idx_dir
            )
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(m_man[k], v)
                self.assertEqual(b1_man[k], v)

            m_loaded = adapter.read_snapshot(m_file, m_snap["snapshot_sha256"])
            b1_loaded = adapter.read_snapshot(b1_file, b1_snap["snapshot_sha256"])
            b0_loaded = adapter.read_snapshot(b0_file, b0_snap["snapshot_sha256"])

            # 6. Module 7: Evaluate Stage 1 & verify bit-identical parity with direction_forecast_adapter!
            study = {
                "scope": "upbit-krw-spot",
                "rule_version": adapter.RULE,
                "source_id": "upbit-hourly-v1",
                "market": "KRW-BTC",
                "forecast_model": {k: m_loaded["model"][k] for k in ("name", "version", "sha256")},
                "b1_forecast_model": {k: b1_loaded["model"][k] for k in ("name", "version", "sha256")},
                "b0_forecast_model": {k: b0_loaded["model"][k] for k in ("name", "version", "sha256")},
                "evaluation_start": eval_start,
                "evaluation_end": eval_end,
                "step_seconds": step,
                "horizon_seconds": horizon,
                "hurdle_bps": hurdle_bps,
                "confidence": "0.60",
                "min_validation_calls": 20,
                "max_calibration_gap": "0.20",
                "up_y": "0.04",
                "down_y": "0.02",
                "ceiling_y": "0.04",
                "criterion2_margin": 0.0,
                "bootstrap_replications": 2000,
                "bootstrap_seed": 101,
                "b2_paths": 100,
            }
            s1_report = s1e.evaluate_stage1(
                study=study,
                history=history_doc,
                m_snapshots=[m_loaded],
                b1_snapshots=[b1_loaded],
                b0_snapshots=[b0_loaded],
                feature_table=ftable,
                evaluated_at=s1_write_at + 10,
            )
            self.assertEqual(s1_report["outcome"], "PASS", s1_report)
            self.assertTrue(len(s1_report["passing_directions"]) >= 1)

            # Bit-identical Criterion 1 counting parity check against direction_forecast_adapter.run()
            probe_now = s1_write_at + 10
            adapter_study = {k: study[k] for k in adapter.STUDY_KEYS}
            adapter_doc = {
                "schema": "tradegen-adaptive-bid-gap-replay-v1",
                "model": adapter_study,
                "terms": {
                    "scope": study["scope"],
                    "ceiling_y": "0.04",
                    "current_y": "0.03",
                    "model_sha256": preview.model_id(adapter_study),
                },
                "history": history_doc,
                "observations": [{
                    "sequence": 1,
                    "as_of": probe_now,
                    "scope": study["scope"],
                    "last_trade_at": probe_now - 45,
                    "last_trade": "10000",
                    "bid_at": probe_now,
                    "bid": "9900",
                    "prior_block_active": False,
                    "floor_halt": False,
                    "daily_stop": False,
                }],
            }
            adapter_out = adapter.run(adapter_doc, [m_loaded])
            self.assertEqual(adapter_out["status"], "REPLAYED")
            h_out = adapter_out["events"][0]["holdout"]
            self.assertIsNotNone(h_out)
            d_called = h_out["direction"]
            s1_d = s1_report["criterion1_M"]["directions"][d_called]
            self.assertEqual(s1_d["calls"], h_out["calls"])
            self.assertEqual(s1_d["hits"], h_out["hits"])
            self.assertEqual(s1_d["hit_lower_95"], h_out["hit_lower_95"])
            self.assertEqual(s1_d["directional_calibration_gap"], h_out["directional_calibration_gap"])

            # 7. Module 8: Capture Stage 2 quotes via UpbitQuoteRecorder & run 3-arm Stage 2 replay!
            q_arc = root / "quote_arc"
            q_clock = FakeClock(float(probe_now + 10))
            q_cfg = uqr.QuoteRecorderConfig("KRW-BTC", "upbit-krw-spot", interval_seconds=10, app_running=False)

            def quote_transport(path: str, _params: dict) -> upr.HttpReply:
                now_i = int(q_clock.wall())
                if path == "/v1/ticker":
                    return _reply([{"market": "KRW-BTC", "trade_price": 10000, "trade_timestamp": (now_i - 45) * 1000}])
                return _reply([{"market": "KRW-BTC", "orderbook_units": [{"bid_price": 9950, "ask_price": 10010}]}])

            q_rec = uqr.UpbitQuoteRecorder(q_arc, q_cfg, transport=quote_transport, clock=q_clock)
            for k in range(5):
                q_clock._wall = float(probe_now + (k + 1) * 10) + 0.1
                q_rec.capture_once()

            kdate = kst_date_iso(probe_now + 10)
            q_day_path = root / "stage2_day1.json"
            uqr.export_daily_quotes(q_arc, q_day_path, kst_date=kdate, expected_observations=5, exported_at=probe_now + 100)
            q_day_doc = uqr.read_daily_quotes(q_day_path)

            s2_report = s2r.run_stage2_replay(
                study={**study, "min_stage2_days": 1, "min_early_warnings": 0},
                stage1_report=s1_report,
                stage1_history=history_doc,
                daily_quote_records=[q_day_doc],
                m_snapshots=[m_loaded],
                b1_snapshots=[b1_loaded],
            )
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(s2_report[k], v)
            self.assertIn(s2_report["outcome"], ("PASS", "NOT SHOWN"))


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
