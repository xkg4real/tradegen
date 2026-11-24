"""Offline tests for probability estimation, as-of evidence, and BR-26 proposal isolation."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.research import adaptive_bid_gap_preview as y


class AdaptiveBidGapTests(unittest.TestCase):
    def setUp(self):
        self.doc = y.example()
        self.terms = self.doc["terms"]
        self.obs = self.doc["observation"]
        self.model = self.doc["model"]
        self.bars = self.doc["history"]["bars"]

    def run_preview(self):
        result = y.evaluate(self.doc)
        self.assertFalse(result["execution_ready"])
        return result

    def pin(self, **changes):
        self.model.update(changes)
        self.terms["model_sha256"] = y.model_id(self.model)

    def test_rising_synthetic_history_can_stage_wider_value(self):
        out = self.run_preview()
        self.assertEqual(out["current_y"], "0.02")
        self.assertEqual(out["candidate_next_y"], "0.03")
        self.assertEqual(out["applies_after"], self.obs["as_of"])
        self.assertEqual(out["holdout"]["hits"], 24)

    def test_falling_synthetic_history_can_stage_tighter_value(self):
        for bar in self.bars:
            bar["return_bps"] *= -1
        self.assertEqual(self.run_preview()["candidate_next_y"], "0.01")
        self.terms["current_y"] = "0.005"
        self.obs["bid"] = "10000"
        self.assertEqual(self.run_preview()["reason"], "AT_DIRECTIONAL_TARGET")

    def test_equal_gap_boundary_checked_before_model_with_stale_trade(self):
        self.obs["bid"] = "9800"
        self.doc.pop("model")
        out = self.run_preview()
        self.assertEqual(out["quote_state"], "BID_GAP_TRIGGERED")
        self.assertTrue(out["new_buys_blocked"])
        self.assertIsNone(out["candidate_next_y"])

    def test_fresh_trade_never_widens_over_price_already_across_threshold(self):
        self.obs.update(last_trade_at=self.obs["as_of"]-30, bid="9750")
        out = self.run_preview()
        self.assertEqual(out["quote_state"], "NO_STALE_BID_GAP")
        self.assertEqual(out["reason"], "OBSERVED_BID_PRECLUDES_WIDENING")

    def test_existing_block_and_unusable_book_suppress_proposals(self):
        self.obs["prior_block_active"] = True
        self.assertEqual(self.run_preview()["reason"], "PRIOR_BLOCK")
        self.obs["prior_block_active"] = False
        for field, val in (("bid", None), ("bid_at", self.obs["as_of"]-1)):
            with self.subTest(field=field):
                orig = self.obs[field]
                self.obs[field] = val
                out = self.run_preview()
                self.assertTrue(out["new_buys_blocked"])
                self.assertEqual(out["quote_state"], "BID_UNAVAILABLE")
                self.obs[field] = orig

    def test_unavailable_bid_on_fresh_mark_keeps_existing_stop(self):
        self.obs.update(last_trade_at=self.obs["as_of"], prior_block_active=True, bid=None)
        out = self.run_preview()
        self.assertTrue(out["new_buys_blocked"])
        self.assertIsNone(out["candidate_next_y"])

    def test_malformed_quote_or_unknown_prior_stop_blocks_new_buys(self):
        for key, value in (("bid", "0"), ("bid", "oops"), ("prior_block_active", None)):
            with self.subTest(key=key, value=value):
                origin = self.obs[key]
                self.obs[key] = value
                out = self.run_preview()
                self.assertTrue(out["new_buys_blocked"])
                self.assertIsNone(out["candidate_next_y"])
                self.obs[key] = origin

    def test_no_signed_y_no_buys_and_zero_monitoring(self):
        self.doc["terms"] = None
        out = self.run_preview()
        self.assertEqual((out["status"], out["current_y"], out["quote_state"]),
                         ("NO_SIGNED_Y", "0", "BID_GAP_TRIGGERED"))
        self.obs["bid"] = "10100"
        self.assertTrue(self.run_preview()["new_buys_blocked"])

    def test_over_cap_current_and_ceiling_are_not_repaired(self):
        for key in ("current_y", "ceiling_y"):
            with self.subTest(key=key):
                self.doc["terms"] = {**self.terms, key:"0.0500000000000001"}
                out = self.run_preview()
                self.assertEqual(out["status"], "REVIEW")
                self.assertIsNone(out["candidate_next_y"])
                self.assertIsNone(out["current_y"])

    def test_private_cap_and_global_max_inclusive(self):
        self.pin(up_y="0.05")
        self.assertEqual(self.run_preview()["candidate_next_y"], "0.05")
        self.terms["ceiling_y"] = "0.025"
        out = self.run_preview()
        self.assertEqual(out["reason"], "MODEL_TARGET_OUTSIDE_ENVELOPE")
        self.assertIsNone(out["candidate_next_y"])

    def test_unchanged_prior_tighter_value_with_lost_qualification(self):
        self.terms["current_y"] = "0.015"
        self.model["up_y"] = "0.05"
        out = self.run_preview()
        self.assertEqual((out["current_y"], out["candidate_next_y"], out["reason"]),
                         ("0.015", None, "MODEL_NOT_BOUND"))

    def test_scope_mismatch_cannot_reuse_evidence(self):
        self.doc["history"]["scope"] = "another-market"
        self.assertEqual(self.run_preview()["reason"], "MODEL_OR_HISTORY_SCOPE_MISMATCH")
        self.obs["scope"] = "another-market"
        self.assertEqual(self.run_preview()["reason"], "OBSERVATION_SCOPE_MISMATCH")

    def test_neutral_forecast_neither_direction(self):
        for bar in self.bars:
            bar["return_bps"] = 0
        self.terms["current_y"] = "0.015"
        out = self.run_preview()
        self.assertEqual(out["probabilities"], {"up":0.0, "down":0.0, "neutral":1.0})
        self.assertEqual(out["reason"], "MODEL_UNCERTAIN")
        self.assertIsNone(out["candidate_next_y"])

    def test_bad_history_is_not_silently_dropped(self):
        for key, value, reason in [
            ("end", self.obs["as_of"], "INTEGER_OUT_OF_RANGE"),
            ("end", self.bars[-2]["end"], "MISSING_OR_DUPLICATE_BAR"),
            ("known_at", self.obs["as_of"], "INTEGER_OUT_OF_RANGE"),
        ]:
            with self.subTest(key=key, value=value):
                orig = self.bars[-1][key]
                self.bars[-1][key] = value
                self.assertEqual(self.run_preview()["reason"], reason)
                self.bars[-1][key] = orig

    def test_origin_without_asof_inputs_invalidates_all_holdout_evidence(self):
        self.bars[11]["known_at"] += 60
        self.assertEqual(self.run_preview()["reason"], "HOLDOUT_FEATURE_NOT_YET_KNOWN")

    def test_holdout_accepts_publication_after_bar_close(self):
        # Real bars are published after they close. A lag under one bar is what the live check allows.
        for bar in self.bars:
            bar["known_at"] = bar["end"] + 2
        self.obs.update(as_of=self.obs["as_of"] + 2, bid_at=self.obs["bid_at"] + 2,
                        last_trade_at=self.obs["last_trade_at"] + 2)
        out = self.run_preview()
        self.assertEqual(out["status"], "PROPOSAL_ONLY")
        self.assertEqual(out["holdout"]["hits"], 24)

    def test_recovery_unknown_threshold_does_not_revert_to_positive_ceiling(self):
        self.terms["current_y"] = None
        out = self.run_preview()
        self.assertEqual((out["status"], out["current_y"]), ("RECOVERY_REQUIRED", "0"))
        self.assertTrue(out["new_buys_blocked"])
        self.assertEqual(out["quote_state"], "BID_GAP_TRIGGERED")

    def test_data_source_and_holdout_start_bound_to_model(self):
        self.doc["history"]["source_id"] = "another-source"
        self.assertEqual(self.run_preview()["reason"], "EVIDENCE_SOURCE_MISMATCH")
        self.doc["history"]["source_id"] = self.model["source_id"]
        self.bars.pop(0)
        self.assertEqual(self.run_preview()["reason"], "HOLDOUT_WINDOW_MISMATCH")

    def test_model_freeze_before_first_fold_and_stale_feature_checks(self):
        self.pin(frozen_at=self.bars[11]["end"])
        self.assertEqual(self.run_preview()["reason"], "MODEL_NOT_FROZEN_BEFORE_HOLDOUT")
        self.obs["as_of"] += 60
        self.obs["bid_at"] = self.obs["as_of"]
        self.assertEqual(self.run_preview()["reason"], "STALE_FEATURES")

    def test_validation_must_support_same_direction(self):
        for bar in self.bars[:-12]:
            bar["return_bps"] = -50
        out = self.run_preview()
        self.assertEqual(out["probabilities"]["up"], 1.0)
        self.assertLess(out["holdout"]["calls"], 16)
        self.assertEqual(out["reason"], "DIRECTION_NOT_VALIDATED")
        self.assertIsNone(out["candidate_next_y"])

    def test_unknown_model_is_static_only(self):
        self.terms["model_sha256"] = None
        self.assertEqual(self.run_preview()["reason"], "MODEL_NOT_BOUND")

    def test_paths_and_preregistered_limits_are_bounded(self):
        self.pin(paths=10001)
        self.assertEqual(self.run_preview()["reason"], "INTEGER_OUT_OF_RANGE")
        self.pin(paths=400, down_y="0.06")
        self.assertEqual(self.run_preview()["reason"], "DECIMAL_OUT_OF_RANGE")

    def test_generated_probabilities_are_repeatable_without_mutating_data(self):
        for i, bar in enumerate(self.bars):
            bar["return_bps"] = [-25, 7, 4, 30][i % 4]
        before = deepcopy(self.doc)
        self.assertEqual(self.run_preview(), self.run_preview())
        self.assertEqual(before, self.doc)

    def test_reject_duplicate_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"input.json"
            for bad in ('{"terms":null,"terms":null}', '{"terms":NaN}'):
                p.write_text(bad)
                with self.assertRaises(y.Invalid):
                    y.read_input(p)

    def test_cli_deterministic_fixture_and_no_private_authority(self):
        root = Path(__file__).resolve().parents[2]
        command = [sys.executable, "-B", "-m", "tools.research.adaptive_bid_gap_preview"]
        raw = subprocess.check_output(command + ["--example"], cwd=root)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"fixture.json"
            p.write_bytes(raw)
            result = json.loads(subprocess.check_output(command + ["--input", str(p)], cwd=root))
        self.assertEqual(result["status"], "PROPOSAL_ONLY")
        self.assertFalse(result["execution_ready"])


if __name__ == "__main__":
    unittest.main()
