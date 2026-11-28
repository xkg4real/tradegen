"""Unit tests for direction_stage2_replay. Synthetic data only; network patched."""
from __future__ import annotations

import copy
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from tools.research import adaptive_bid_gap_replay as replay_tool
from tools.research import direction_stage1_evaluator as s1e
from tools.research import direction_stage2_replay as s2r
from tools.research.test_direction_stage1_evaluator import _build_stage1_scenario, _coverage_table, _seal_snap
from tools.research._study_common import (
    RESEARCH_FLAGS,
    StudyError,
    assert_all_isolation_invariants,
    kst_date_iso,
    sha256_ascii,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _make_obs(seq: int, as_of: int, scope: str, *, mark: str = "10000", bid: str | None = "9900", stale: bool = False) -> dict:
    return {
        "sequence": seq,
        "as_of": as_of,
        "scope": scope,
        "last_trade_at": (as_of - 45) if stale else (as_of - 5),
        "last_trade": mark,
        "bid_at": as_of if bid is not None else None,
        "bid": bid,
        "prior_block_active": False,
        "floor_halt": False,
        "daily_stop": False,
    }


def _make_daily_quote_doc(kst_date: str, scope: str, obs_list: list[dict], *, expected_obs: int | None = None) -> dict:
    exp_n = len(obs_list) if expected_obs is None else expected_obs
    valid_cnt = sum(1 for o in obs_list if o["bid"] is not None and o["bid_at"] == o["as_of"])
    doc = {
        "format": "tradegen-stage2-daily-quotes-v1",
        **RESEARCH_FLAGS,
        "market": "KRW-BTC",
        "scope": scope,
        "kst_date": kst_date,
        "interval_seconds": 10,
        "expected_observations": exp_n,
        "app_running": False,
        "observation_count": len(obs_list),
        "valid_same_second_count": valid_cnt,
        "quote_coverage": round(valid_cnt / float(max(1, exp_n)), 6),
        "observations": obs_list,
    }
    doc["quote_sha256"] = sha256_ascii(doc)
    return doc


class DirectionStage2ReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_3arm_chunk_carryover_early_warning_row17a_and_dropped_widening(self) -> None:
        study, s1_hist, m_s1_snap, b1_s1_snap, b0_s1_snap = _build_stage1_scenario(300, m_skill=True)
        s1_rep = s1e.evaluate_stage1(
            study=study,
            feature_table=_coverage_table(study, s1_hist),
            history=s1_hist,
            m_snapshots=[m_s1_snap],
            b1_snapshots=[b1_s1_snap],
            b0_snapshots=[b0_s1_snap],
        )
        self.assertEqual(s1_rep["outcome"], "PASS")

        scope = study["scope"]
        # Start Stage 2 on a clean KST midnight boundary after Stage 1 evaluation_end
        # KST = UTC + 9h, so (ts + 32400) % 86400 == 0 -> ts = k * 86400 - 32400
        raw_after = study["evaluation_end"] + 7200
        day1_start = ((raw_after + 32400) // 86400 + 1) * 86400 - 32400
        day2_start = day1_start + 86400

        # Live Stage 2 forecasts:
        # On Day 1, M calls "down" (tightening M's Y from ceiling 0.04 -> down_y 0.02), then later calls "up" right at obs 128!
        # B1 fails Stage 1 gate so B1 stays at ceiling 0.04 like static.
        m_live_forecasts = [
            {
                "market": "KRW-BTC",
                "as_of": day1_start,
                "issued_at": day1_start + 5,
                "horizon_seconds": 7200,
                "hurdle_bps": 15,
                "probabilities": {"up": "0.050000", "down": "0.850000", "neutral": "0.100000"},
                "direction": "down",
            },
            {
                "market": "KRW-BTC",
                "as_of": day2_start - 3600,
                "issued_at": day2_start - 3590,
                "horizon_seconds": 7200,
                "hurdle_bps": 15,
                "probabilities": {"up": "0.300000", "down": "0.300000", "neutral": "0.400000"},
                "direction": "neutral",
            },
            {
                # Global obs 256 (1-indexed) = Day 2 obs 116 (140 + 116 = 256, end of chunk 2!):
                # Issue Day 2 "up" forecast right at Day 2 obs 116 so chunk 2 ends on AWAIT_WIDEN_CONFIRMATION!
                "market": "KRW-BTC",
                "as_of": day2_start,
                "issued_at": day2_start + 116 * 10,
                "horizon_seconds": 7200,
                "hurdle_bps": 15,
                "probabilities": {"up": "0.850000", "down": "0.050000", "neutral": "0.100000"},
                "direction": "up",
            },
        ]
        b1_live_forecasts = [
            {
                "market": "KRW-BTC",
                "as_of": t_bar,
                "issued_at": t_bar + 5,
                "horizon_seconds": 7200,
                "hurdle_bps": 15,
                "probabilities": {"up": "0.520000", "down": "0.440000", "neutral": "0.040000"},
                "direction": "up",
            }
            for t_bar in (day1_start, day2_start)
        ]

        m_live_snap = _seal_snap({
            "format": "tradegen-direction-forecast-v1",
            "producer": "tradegen",
            "model": copy.deepcopy(m_s1_snap["model"]),
            "generated_at": day2_start + 2000,
            "forecasts": m_live_forecasts,
        })
        b1_live_snap = _seal_snap({
            "format": "tradegen-direction-forecast-v1",
            "producer": "tradegen",
            "model": copy.deepcopy(b1_s1_snap["model"]),
            "generated_at": day2_start + 2000,
            "forecasts": b1_live_forecasts,
        })

        day1_obs = []
        for k in range(140):
            ts = day1_start + (k + 1) * 10
            if 10 <= k <= 12:
                day1_obs.append(_make_obs(k + 1, ts, scope, mark="10000", bid="9780", stale=True))
            elif k == 20:
                day1_obs.append(_make_obs(k + 1, ts, scope, mark="10000", bid="9550", stale=True))
            else:
                day1_obs.append(_make_obs(k + 1, ts, scope, mark="10000", bid="9950", stale=False))

        day2_obs = [_make_obs(k + 1, day2_start + (k + 1) * 10, scope, mark="10000", bid="9950", stale=False) for k in range(140)]

        d1_doc = _make_daily_quote_doc(kst_date_iso(day1_obs[0]["as_of"]), scope, day1_obs, expected_obs=140)
        d2_doc = _make_daily_quote_doc(kst_date_iso(day2_obs[0]["as_of"]), scope, day2_obs, expected_obs=140)

        s2_study = {
            **study,
            "min_stage2_days": 2,
            "min_daily_quote_coverage": 0.95,
            "min_daily_live_forecast_coverage": 0.95,
            "latch_convention": "17a",
        }
        rep = s2r.run_stage2_replay(
            study=s2_study,
            stage1_report=s1_rep,
            stage1_history=s1_hist,
            daily_quote_records=[d1_doc, d2_doc],
            m_snapshots=[m_s1_snap, m_live_snap],
            b1_snapshots=[b1_s1_snap, b1_live_snap],
        )
        for k, v in RESEARCH_FLAGS.items():
            self.assertEqual(rep[k], v)
        self.assertEqual(rep["outcome"], "PASS")
        self.assertTrue(rep["passed_criterion3"])
        self.assertEqual(rep["criterion3"]["M"]["early_warnings"], 1)
        self.assertEqual(rep["criterion3"]["M"]["excess_alerts"], 0)
        self.assertEqual(rep["criterion3"]["B1"]["early_warnings"], 0)
        # Verify Row 17(a) boundary latch release, lenient_unblocked_seconds > 0, and dropped pending widening at chunk 2 boundary!
        self.assertGreaterEqual(rep["arms"]["M"]["boundary_latch_releases"], 1)
        self.assertGreater(rep["arms"]["M"]["lenient_unblocked_seconds"], 0)
        self.assertEqual(rep["arms"]["M"]["dropped_pending_widenings"], 1)

    def test_s5_illegal_widening_s6_truncation_and_s7_voided_day_state_carry(self) -> None:
        study, s1_hist, m_s1_snap, b1_s1_snap, b0_s1_snap = _build_stage1_scenario(300, m_skill=True)
        s1_rep = s1e.evaluate_stage1(study=study, feature_table=_coverage_table(study, s1_hist), history=s1_hist, m_snapshots=[m_s1_snap], b1_snapshots=[b1_s1_snap], b0_snapshots=[b0_s1_snap])
        scope = study["scope"]
        raw_after = study["evaluation_end"] + 7200
        day1_start = ((raw_after + 32400) // 86400 + 1) * 86400 - 32400
        day2_start = day1_start + 86400

        m_live = _seal_snap({
            "format": "tradegen-direction-forecast-v1",
            "producer": "tradegen",
            "model": copy.deepcopy(m_s1_snap["model"]),
            "generated_at": day2_start + 100,
            "forecasts": [
                {
                    "market": "KRW-BTC", "as_of": day1_start, "issued_at": day1_start + 1,
                    "horizon_seconds": 7200, "hurdle_bps": 15,
                    "probabilities": {"up": "0.050000", "down": "0.850000", "neutral": "0.100000"},
                    "direction": "down",
                },
                {
                    "market": "KRW-BTC", "as_of": day2_start, "issued_at": day2_start + 1,
                    "horizon_seconds": 7200, "hurdle_bps": 15,
                    "probabilities": {"up": "0.510000", "down": "0.450000", "neutral": "0.040000"},
                    "direction": "up",
                },
            ],
        })
        b1_live = _seal_snap({
            "format": "tradegen-direction-forecast-v1",
            "producer": "tradegen",
            "model": copy.deepcopy(b1_s1_snap["model"]),
            "generated_at": day2_start + 100,
            "forecasts": [],
        })

        # Day 1 is VOIDED under S7 (expected_obs=100, only 20 obs -> 20% < 95%), yet M tightens Y from 0.04 -> 0.02 on Day 1!
        # Day 2 is VALID under S7 (20/20 = 100%), and has NO new call from M -> Day 2 MUST inherit current_y == "0.02" from voided Day 1!
        d1_obs = [_make_obs(i + 1, day1_start + (i + 1) * 10, scope) for i in range(20)]
        d2_obs = [_make_obs(i + 1, day2_start + (i + 1) * 10, scope) for i in range(20)]
        d1_void_doc = _make_daily_quote_doc(kst_date_iso(d1_obs[0]["as_of"]), scope, d1_obs, expected_obs=100)
        d2_valid_doc = _make_daily_quote_doc(kst_date_iso(d2_obs[0]["as_of"]), scope, d2_obs, expected_obs=20)

        rep_s7 = s2r.run_stage2_replay(
            study={**study, "min_stage2_days": 1},
            stage1_report=s1_rep,
            stage1_history=s1_hist,
            daily_quote_records=[d1_void_doc, d2_valid_doc],
            m_snapshots=[m_s1_snap, m_live],
            b1_snapshots=[b1_s1_snap, b1_live],
        )
        self.assertIn(d1_void_doc["kst_date"], rep_s7["voided_days_s7"])
        self.assertEqual(rep_s7["valid_day_count"], 1)
        # Tightening from voided Day 1 carried cleanly into valid Day 2!
        self.assertEqual(rep_s7["arms"]["M"]["final_working_y"], "0.02")

        # S6 before start -> STOPPED_S6_BEFORE_START
        rep_s6 = s2r.run_stage2_replay(
            study={**study, "min_stage2_days": 1},
            stage1_report=s1_rep,
            stage1_history=s1_hist,
            daily_quote_records=[d2_valid_doc],
            m_snapshots=[m_s1_snap, m_live],
            b1_snapshots=[b1_s1_snap, b1_live],
            ceiling_events=[{"at": d2_obs[0]["as_of"] - 10, "signed_y": "0.03"}],
        )
        self.assertEqual((rep_s6["outcome"], rep_s6["stop_rule"]), ("STOPPED_S6_BEFORE_START", "S6"))

        # S5 illegal widening bug trap
        def buggy_replay(doc: dict, direction_source: object) -> dict:
            res = replay_tool.replay(doc, direction_source)
            if res["status"] == "REPLAYED" and res["events"]:
                res["events"][0]["entry_block_latched"] = True
                res["events"][0]["used_y"] = "0.02"
                res["events"][0]["next_y"] = "0.04"
                res["events"][0]["transition"] = "WIDEN_FOR_NEXT"
            return res

        rep_s5 = s2r.run_stage2_replay(
            study={**study, "min_stage2_days": 1},
            stage1_report=s1_rep,
            stage1_history=s1_hist,
            daily_quote_records=[d2_valid_doc],
            m_snapshots=[m_s1_snap, m_live],
            b1_snapshots=[b1_s1_snap, b1_live],
            replay_fn=buggy_replay,
        )
        self.assertEqual((rep_s5["outcome"], rep_s5["stop_rule"]), ("BUG_S5_ILLEGAL_WIDENING", "S5"))


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
