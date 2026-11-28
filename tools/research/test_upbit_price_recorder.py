"""Unit tests for upbit_price_recorder. Synthetic data only; network patched."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.research import upbit_price_recorder as upr
from tools.research._study_common import (
    RESEARCH_FLAGS,
    StudyError,
    UTC,
    assert_all_isolation_invariants,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


class FakeClock(upr.Clock):
    def __init__(self, initial_wall: float) -> None:
        self._wall = float(initial_wall)
        self._mono = 100.0

    def wall(self) -> float:
        return self._wall

    def monotonic(self) -> float:
        return self._mono

    def sleep(self, seconds: float) -> None:
        self._wall += max(0.0, seconds)
        self._mono += max(0.0, seconds)

    def advance(self, seconds: float) -> None:
        self._wall += seconds
        self._mono += seconds


def _candle_json(end_ts: int, open_p: str, close_p: str, *, step: int = 3600, market: str = "KRW-BTC") -> dict:
    open_ts = end_ts - step
    hi = str(max(Decimal(open_p), Decimal(close_p)))
    lo = str(min(Decimal(open_p), Decimal(close_p)))
    return {
        "market": market,
        "candle_date_time_utc": datetime.fromtimestamp(open_ts, UTC).strftime("%Y-%m-%dT%H:%M:%S"),
        "opening_price": Decimal(open_p),
        "high_price": Decimal(hi),
        "low_price": Decimal(lo),
        "trade_price": Decimal(close_p),
    }


def _reply(obj: object, status: int = 200, headers: dict[str, str] | None = None) -> upr.HttpReply:
    body = json.dumps(obj, default=str).encode("utf-8")
    hdrs = {"content-type": "application/json", "content-length": str(len(body))}
    if headers:
        hdrs.update(headers)
    return upr.HttpReply(status=status, headers=hdrs, body=body)


class UpbitPriceRecorderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._net_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden"))
        self._net_patch.start()

    def tearDown(self) -> None:
        self._net_patch.stop()

    def test_live_capture_known_at_strictly_after_end_and_row6_hurdle(self) -> None:
        t0 = 1_764_000_000  # divisible by 3600
        # Even if wall clock is exact bar close t0 + 0.0, known_at must be >= end + 1
        clock = FakeClock(float(t0))

        def fake_transport(path: str, params: dict) -> upr.HttpReply:
            if path == "/v1/candles/minutes/60":
                return _reply([
                    _candle_json(t0, "100000000", "100250000"),
                    _candle_json(t0 - 3600, "100000000", "100000000"),
                ])
            if path == "/v1/orderbook":
                return _reply([{
                    "market": "KRW-BTC",
                    "orderbook_units": [{"bid_price": 100240000, "ask_price": 100260000}],
                }])
            raise AssertionError(f"unexpected path {path}")

        with tempfile.TemporaryDirectory() as tmp:
            arc = Path(tmp) / "price_arc"
            coord = Path(tmp) / "coord"
            cfg = upr.PriceRecorderConfig(market="KRW-BTC", step_seconds=3600)
            rec = upr.UpbitPriceRecorder(arc, cfg, transport=fake_transport, coordination_dir=coord, clock=clock)
            res = rec.poll_once()
            self.assertEqual(res["status"], "RECORDED")
            self.assertEqual(res["appended_bars"], 1)
            # Transient lock released immediately after poll
            self.assertFalse((coord / "upbit-public-session.lock").exists())

            _, bars, _ = upr.read_recorded_bars(arc)
            self.assertEqual(len(bars), 1)
            b0 = bars[0]
            self.assertEqual(b0["end"], t0)
            self.assertEqual(b0["known_at"], t0 + 1)
            self.assertGreater(b0["known_at"], b0["end"])
            self.assertEqual(b0["return_bps"], 25)
            self.assertFalse(b0["backfilled"])
            self.assertIsNotNone(b0["spread_bps"])

            # Row 6 hurdle_bps: 10 bps fee + ~1.995 bps spread + 5 bps slippage -> ceil = 17 bps
            hurdle = upr.compute_warmup_hurdle_bps(bars)
            self.assertEqual(hurdle, 17)

            # Export history.json + manifest
            hist_path = Path(tmp) / "history.json"
            manifest = upr.export_history(arc, hist_path, scope="upbit-krw-spot", source_id="price-rec-v1", exported_at=t0 + 10)
            for k, v in RESEARCH_FLAGS.items():
                self.assertEqual(manifest[k], v)
            self.assertTrue(hist_path.is_file())
            self.assertTrue((Path(tmp) / "history.manifest.json").is_file())

    def test_missed_bar_backfill_uses_honest_late_known_at_and_s1_on_missing_candle(self) -> None:
        t0 = 1_764_000_000
        clock = FakeClock(t0 + 5.2)
        candles_db = {
            t0 - 3600: _candle_json(t0 - 3600, "10000", "10000"),
            t0: _candle_json(t0, "10000", "10010"),
            t0 + 3600: _candle_json(t0 + 3600, "10010", "10030"),
            t0 + 7200: _candle_json(t0 + 7200, "10030", "10020"),
            t0 + 10800: _candle_json(t0 + 10800, "10020", "10050"),
        }

        def fake_transport(path: str, params: dict) -> upr.HttpReply:
            if path == "/v1/candles/minutes/60":
                to_dt = datetime.fromisoformat(params["to"].replace("Z", "+00:00"))
                to_ts = int(to_dt.timestamp())
                avail = [c for e, c in sorted(candles_db.items(), reverse=True) if e <= to_ts][: int(params["count"])]
                return _reply(avail)
            return _reply([{"market": "KRW-BTC", "orderbook_units": [{"bid_price": 10049, "ask_price": 10051}]}])

        with tempfile.TemporaryDirectory() as tmp:
            arc = Path(tmp) / "arc"
            cfg = upr.PriceRecorderConfig(market="KRW-BTC", step_seconds=3600)
            rec = upr.UpbitPriceRecorder(arc, cfg, transport=fake_transport, clock=clock)
            rec.poll_once()

            # Pause recorder for 3 hours, resume at t0 + 10812.4
            clock._wall = t0 + 10812.4
            res = rec.poll_once()
            self.assertEqual(res["appended_bars"], 3)
            self.assertEqual(res["backfilled_bars"], 2)

            _, bars, _ = upr.read_recorded_bars(arc)
            self.assertEqual([b["end"] for b in bars], [t0, t0 + 3600, t0 + 7200, t0 + 10800])
            # Backfilled bars (t0+3600 and t0+7200) carry late known_at >= t0 + 10813 and no close orderbook
            self.assertTrue(bars[1]["backfilled"])
            self.assertIsNone(bars[1]["bid"])
            self.assertGreaterEqual(bars[1]["known_at"], t0 + 10813)
            self.assertFalse(bars[3]["backfilled"])
            self.assertEqual(bars[3]["bid"], "10049")

            # Advance 2 more hours where t0 + 14400 is missing on venue -> S1_UNBACKFILLABLE_BAR
            candles_db[t0 + 18000] = _candle_json(t0 + 18000, "10050", "10060")
            clock._wall = t0 + 18005.0
            with self.assertRaisesRegex(StudyError, "S1_UNBACKFILLABLE_BAR"):
                rec.poll_once()
            with self.assertRaisesRegex(StudyError, "S1_UNBACKFILLABLE_BAR"):
                upr.read_recorded_bars(arc)

    def test_rate_limit_records_cooldown_and_never_unlinks_hold_file(self) -> None:
        t0 = 1_764_000_000
        clock = FakeClock(t0 + 2.0)

        def rate_limited_transport(_path: str, _params: dict) -> upr.HttpReply:
            return upr.HttpReply(status=429, headers={"retry-after": "60"}, body=b"{}")

        with tempfile.TemporaryDirectory() as tmp:
            arc = Path(tmp) / "arc"
            coord = Path(tmp) / "coord"
            cfg = upr.PriceRecorderConfig(market="KRW-BTC", step_seconds=3600)
            rec = upr.UpbitPriceRecorder(arc, cfg, transport=rate_limited_transport, coordination_dir=coord, clock=clock)
            with self.assertRaisesRegex(StudyError, "RATE_LIMIT_STOP_429"):
                rec.poll_once()

            hold_file = coord / "upbit-public-cooldown.json"
            self.assertTrue(hold_file.is_file())

            # Poll during cooldown refuses immediately before touching transport
            rec2 = upr.UpbitPriceRecorder(
                arc, cfg,
                transport=lambda *_: (_ for _ in ()).throw(AssertionError("transport called during cooldown")),
                coordination_dir=coord,
                clock=clock,
            )
            with self.assertRaisesRegex(StudyError, "PUBLIC_BUDGET_COOLDOWN"):
                rec2.poll_once()

            # Even after cooldown elapses, TransientPublicBudget NEVER deletes upbit-public-cooldown.json
            clock.advance(120.0)
            with upr.TransientPublicBudget(coord, clock=clock):
                pass
            self.assertTrue(hold_file.is_file())

    def test_cli_requires_allow_public_network(self) -> None:
        cmd = [sys.executable, "-B", "-m", "tools.research.upbit_price_recorder",
               "poll", "--market", "KRW-BTC", "--archive-dir", "/tmp/never-used"]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--allow-public-network", proc.stderr)


class IsolationTests(unittest.TestCase):
    def test_d14_and_research_ast_isolation(self) -> None:
        assert_all_isolation_invariants(self, REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
