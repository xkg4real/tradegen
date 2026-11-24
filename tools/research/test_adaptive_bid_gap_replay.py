"""Offline BR-26 temporal transition and failure cases."""
import copy
import unittest

from tools.research import adaptive_bid_gap_replay as module


class ReplayTest(unittest.TestCase):
    def test_widen_is_confirmed_with_old_threshold_then_effective(self):
        report = module.replay(module.example())
        self.assertEqual(report["status"], "REPLAYED")
        self.assertFalse(report["execution_ready"])
        self.assertEqual([r["transition"] for r in report["events"]],
                         ["AWAIT_WIDEN_CONFIRMATION", "WIDEN_FOR_NEXT", "KEEP"])
        self.assertEqual([r["used_y"] for r in report["events"]], ["0.02", "0.02", "0.03"])
        self.assertEqual(len({r["feature_cutoff"] for r in report["events"]}), 3)
        self.assertEqual(report["events"][1]["confirmed_sequence"], 1)

    def test_gap_at_exact_old_limit_during_confirmation_remains_latched(self):
        data = module.example()
        data["observations"][1]["bid"] = "9800"
        events = module.replay(data)["events"]
        self.assertEqual(events[1]["quote_state"], "BID_GAP_TRIGGERED")
        self.assertEqual(events[1]["next_y"], "0.02")
        self.assertTrue(all(e["entry_block_latched"] for e in events[1:]))
        self.assertIsNone(events[2]["candidate_next_y"])

    def test_downside_tightens_for_following_observation(self):
        data = module.example()
        for bar in data["history"]["bars"]:
            bar["return_bps"] = -20
        data["observations"][1]["bid"] = "9900"
        events = module.replay(data)["events"]
        self.assertEqual((events[0]["used_y"], events[0]["next_y"], events[0]["transition"]),
                         ("0.02", "0.01", "TIGHTEN_FOR_NEXT"))
        self.assertEqual(events[1]["quote_state"], "BID_GAP_TRIGGERED")

    def test_confirmation_stops_on_independent_flags(self):
        for flag in ("prior_block_active", "daily_stop", "floor_halt"):
            with self.subTest(flag=flag):
                data = module.example()
                data["observations"][1][flag] = True
                events = module.replay(data)["events"]
                self.assertEqual(events[1]["next_y"], "0.02")
                self.assertTrue(events[2]["entry_block_latched"])

    def test_first_forecast_expiry_requires_a_new_widening_proposal(self):
        data = module.example()
        del data["observations"][1]
        data["observations"][-1]["sequence"] = 2
        events = module.replay(data)["events"]
        self.assertEqual(events[1]["transition"], "AWAIT_WIDEN_CONFIRMATION")
        self.assertIsNone(events[1]["confirmed_sequence"])
        self.assertEqual(events[1]["next_y"], "0.02")

    def test_missing_book_then_recovery_does_not_reopen(self):
        data = module.example()
        data["observations"][1].update(bid=None, bid_at=None)
        report = module.replay(data)
        self.assertEqual(report["events"][1]["quote_state"], "BID_UNAVAILABLE")
        self.assertTrue(report["entry_block_latched"])
        self.assertEqual(report["final_working_y"], "0.02")

    def test_duplicate_quotes_are_idempotent_and_cannot_supply_confirmation(self):
        data = module.example()
        data["observations"] = [data["observations"][0], copy.deepcopy(data["observations"][0])]
        report = module.replay(data)
        self.assertEqual((len(report["events"]), report["duplicates_ignored"]), (1, 1))
        self.assertEqual(report["final_working_y"], "0.02")

    def test_unresolved_timeline_refuses_entire_series(self):
        for change, reason in [({"sequence": 1, "bid": "9990"}, "CONFLICTING_REPEAT"),
                               ({"sequence": 4}, "CHRONOLOGY_UNRESOLVED"),
                               ({"as_of": 1}, "CHRONOLOGY_UNRESOLVED")]:
            with self.subTest(change=change):
                data = module.example()
                data["observations"][1].update(change)
                report = module.replay(data)
                self.assertEqual((report["reason"], report["events"]), (reason, []))
                self.assertTrue(report["entry_block_latched"])

    def test_event_cannot_replace_cap_or_working_threshold_or_scope(self):
        for change in ({"terms": {"current_y": "0.05"}}, {"current_y": "0.05"}, {"scope": "other"},
                       {"daily_stop": 0}):
            with self.subTest(change=change):
                data = module.example()
                data["observations"][1].update(change)
                self.assertEqual(module.replay(data)["status"], "REJECTED")

    def test_missing_or_invalid_initial_limits(self):
        for no_terms in (True, False):
            data = module.example()
            if no_terms:
                data["terms"] = None
            else:
                data["terms"]["current_y"] = None
            events = module.replay(data)["events"]
            self.assertTrue(all(r["used_y"] == "0" and r["entry_block_latched"] for r in events))
        data = module.example()
        data["terms"]["ceiling_y"] = "0.05001"
        self.assertEqual(module.replay(data)["status"], "REJECTED")

    def test_late_receipt_and_future_bar_not_used_for_confirmation(self):
        data = module.example()
        initial, confirm, last = data["observations"]
        # The next completed bar's publication is later than both subsequent quotes.
        data["history"]["bars"][-2]["known_at"] = last["as_of"] + 1
        events = module.replay(data)["events"]
        self.assertEqual(events[0]["feature_cutoff"], initial["as_of"] - 1)
        self.assertEqual(events[1]["feature_cutoff"], events[0]["feature_cutoff"])
        self.assertLess(events[1]["feature_cutoff"], confirm["as_of"])
        self.assertEqual(events[1]["snapshot_reason"], "STALE_FEATURES")
        self.assertEqual(events[2]["next_y"], "0.02")

    def test_series_bounds(self):
        data = module.example()
        data["observations"] *= 43
        self.assertEqual(module.replay(data)["reason"], "REPLAY_SIZE")
        data = module.example()
        data["model"]["paths"] = 1_000_000
        self.assertEqual(module.replay(data)["reason"], "REPLAY_SIMULATION_BUDGET")


if __name__ == "__main__":
    unittest.main()
