"""Unit tests for upbit_quote_recorder. Synthetic data only; network patched."""
from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.research import upbit_price_recorder as upr
from tools.research import upbit_quote_recorder as uqr
from tools.research.test_upbit_price_recorder import FakeClock, _reply
from tools.research._study_common import (
    RESEARCH_FLAGS,
    assert_all_isolation_invariants,
    kst_date_iso,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class UpbitQuoteRecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_same_second_vs_crossed_second_and_bid_gap_status_stripping(self) -> None:
        t0 = 1_764_000_100
        clock = FakeClock(t0 + 0.1)
        cross_second_mode = [False]

        def fake_transport(path: str, _params: dict) -> upr.HttpReply:
            if path == "/v1/ticker":
                return _reply([{"market": "KRW-BTC", "trade_price": 100000000, "trade_timestamp": (t0 - 40) * 1000}])
            if path == "/v1/orderbook":
                if cross_second_mode[0]:
                    clock.advance(1.2)  # Cross into next integer second!
                return _reply([{"market": "KRW-BTC", "orderbook_units": [{"bid_price": 99900000, "ask_price": 100010000}]}])
            raise AssertionError(path)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arc = root / "quotes_arc"
            status_path = root / "runtime_status.json"

            # Poll 1: same-second capture; status has ONLY BID_GAP_TRIGGERED -> stripped to prior_block_active=False!
            status_path.write_text(json.dumps({
                "as_of": t0,
                "floor_halt": False,
                "daily_stop": False,
                "block_causes": ["BID_GAP_TRIGGERED"],
            }), encoding="utf-8")

            cfg = uqr.QuoteRecorderConfig(market="KRW-BTC", scope="upbit-krw-spot", interval_seconds=10, app_running=True)
            rec = uqr.UpbitQuoteRecorder(arc, cfg, transport=fake_transport, status_file=status_path, clock=clock)
            r1 = rec.capture_once()
            self.assertTrue(r1["same_second"])
            self.assertEqual(r1["stripped_causes"], ["BID_GAP_TRIGGERED"])

            # Poll 2: status has BID_GAP_TRIGGERED + MANUAL_HOLD -> prior_block_active=True!
            clock._wall = t0 + 10.1
            status_path.write_text(json.dumps({
                "as_of": t0 + 10,
                "floor_halt": False,
                "daily_stop": False,
                "block_causes": ["BID_GAP_TRIGGERED", "MANUAL_HOLD"],
            }), encoding="utf-8")
            r2 = rec.capture_once()
            self.assertTrue(r2["same_second"])

            # Poll 3: crosses second boundary -> same_second=False, bid_at < as_of!
            clock._wall = t0 + 20.4
            cross_second_mode[0] = True
            status_path.write_text(json.dumps({
                "as_of": t0 + 21,
                "floor_halt": False,
                "daily_stop": False,
                "block_causes": [],
            }), encoding="utf-8")
            r3 = rec.capture_once()
            self.assertFalse(r3["same_second"])

            kdate = kst_date_iso(t0)
            out_day = root / "day_quotes.json"
            manifest = uqr.export_daily_quotes(arc, out_day, kst_date=kdate, expected_observations=3, exported_at=t0 + 60)
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(manifest[k], v)
            self.assertEqual(manifest["observation_count"], 3)
            self.assertEqual(manifest["valid_same_second_count"], 2)

            day_doc = uqr.read_daily_quotes(out_day, manifest["quote_sha256"])
            obs0, obs1, obs2 = day_doc["observations"]
            self.assertFalse(obs0["prior_block_active"])
            self.assertTrue(obs1["prior_block_active"])
            self.assertEqual(obs0["bid_at"], obs0["as_of"])
            self.assertLess(obs2["bid_at"], obs2["as_of"])

    def test_app_not_running_and_cli_network_gate(self) -> None:
        t0 = 1_764_000_200
        clock = FakeClock(t0 + 0.1)

        def fake_transport(path: str, _params: dict) -> upr.HttpReply:
            if path == "/v1/ticker":
                return _reply([{"market": "KRW-BTC", "trade_price": 50000, "trade_timestamp": (t0 - 10) * 1000}])
            return _reply([{"market": "KRW-BTC", "orderbook_units": [{"bid_price": 49990, "ask_price": 50010}]}])

        with tempfile.TemporaryDirectory() as tmp:
            arc = Path(tmp) / "arc_norun"
            cfg = uqr.QuoteRecorderConfig(market="KRW-BTC", scope="upbit-krw-spot", app_running=False)
            rec = uqr.UpbitQuoteRecorder(arc, cfg, transport=fake_transport, clock=clock)
            res = rec.capture_once()
            self.assertFalse(res["app_running"])

        cmd = [
            sys.executable, "-B", "-m", "tools.research.upbit_quote_recorder",
            "capture", "--market", "KRW-BTC", "--scope", "s",
            "--archive-dir", "/tmp/unused", "--app-not-running",
        ]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--allow-public-network", proc.stderr)


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
