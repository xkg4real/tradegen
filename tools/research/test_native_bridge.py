"""Unit tests for _native_bridge and adaptive_bid_gap_preview native/fallback equivalence."""
from __future__ import annotations

import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

from tools.research import _native_bridge as nb
from tools.research import adaptive_bid_gap_preview as preview
from tools.research._study_common import assert_all_isolation_invariants


REPO_ROOT = Path(__file__).resolve().parents[2]


class NativeBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()
        nb.reset_cache()

    def tearDown(self) -> None:
        nb.reset_cache()
        self._net_patch.stop()

    def test_native_loader_and_fallback_when_disabled_or_missing(self) -> None:
        doc = preview.example()

        # When TRADEGEN_DISABLE_NATIVE=1, falls back cleanly to pure Python
        with patch.dict(os.environ, {"TRADEGEN_DISABLE_NATIVE": "1"}):
            nb.reset_cache()
            self.assertFalse(nb.native_available())
            res_py = preview.evaluate(doc)
            self.assertEqual(res_py["status"], "PROPOSAL_ONLY")
            self.assertEqual(res_py["candidate_next_y"], "0.03")

        # When pointing to a missing .so path, returns None cleanly without raising
        self.assertIsNone(nb.sample_direction_native([0.002, 0.003], {"paths": 100, "horizon": 2, "block": 2, "seed": 1, "cost_bps": 10}, 100, so_path=Path("/nonexistent/libtradegen_fast.so")))

        # When native .so exists in repo, verify direct MC call determinism
        nb.reset_cache()
        if nb.DEFAULT_SO_PATH.is_file():
            self.assertTrue(nb.native_available())
            mc1 = nb.run_adaptive_bid_gap_mc([0.002, 0.0025, 0.0018, 0.003], n_paths=500, horizon=2, block_len=2, cost_hurdle=0.001, seed=42)
            mc2 = nb.run_adaptive_bid_gap_mc([0.002, 0.0025, 0.0018, 0.003], n_paths=500, horizon=2, block_len=2, cost_hurdle=0.001, seed=42)
            self.assertIsNotNone(mc1)
            self.assertEqual(mc1, mc2)
            assert mc1 is not None
            self.assertEqual(mc1["favorable_prob"], 1.0)
            res_native = preview.evaluate(doc)
            self.assertEqual(res_native["status"], "PROPOSAL_ONLY")
            self.assertEqual(res_native["candidate_next_y"], "0.03")


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
