"""Portable conformance vector for normalized DIDM upside-event metrics."""
import importlib.util
from pathlib import Path
import unittest


class UpsideCoreConformance(unittest.TestCase):
    def test_receipt_entry_costs_first_cross_and_missing_book(self):
        # Load only the adjacent module. This test also runs with python -I -S.
        spec = importlib.util.spec_from_file_location("didm_upside_core", Path(__file__).with_name("didm_upside_core.py"))
        core = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(core)
        market, scope, pin = "KRW-BTC", "synthetic-conformance", "a" * 64
        terms = dict(format="tradegen-upside-terms-v1", market=market, scope=scope, registered_at=80,
                     start=100, end=220, horizon_seconds=60, max_gap_seconds=10, early_seconds=10,
                     move_bps="300", fee_bps="10", slippage_bps="20", fixed_y_bps="200",
                     confidence="0.75", models={"example": pin}, binary_arms=[])
        quotes = []
        for i, ask in enumerate([102, 100, 102, 107, 110, 108] + [100] * 6):
            at = 100 + 10 * i
            quotes.append(dict(market=market, scope=scope, at=at, bid_at=at, last_trade_at=at,
                               same_second=(at != 180), blocked=False, bid=str(ask - 1), ask=str(ask),
                               last_trade=str(ask)))
        signal = dict(arm="example", market=market, model_sha256=pin, as_of=100, issued_at=101,
                      received_at=111, expires_at=155, direction="up", p_up="0.80")
        report = core.evaluate(terms, quotes, [signal])
        window, = report["windows"]
        self.assertEqual((window["onset_at"], window["crossed_at"], window["exit_at"]), (110, 130, 150))
        arm = window["arms"]["example"]
        self.assertEqual((arm["signal_at"], arm["entry_at"], arm["net_bps"]), (111, 120, "427.44328584"))
        # Round-trip fees/slippage and actual sides: 107/102 * .999*.998/(1.001*1.002).
        self.assertEqual(window["arms"]["fixed"]["net_bps"], "635.99215156")
        self.assertEqual(report["excluded_windows"], {"UNAVAILABLE_BOOK": 1})
        self.assertEqual(report["scheduled_windows"], 2)
        self.assertIsNone(report["actual_realized_pnl"])


if __name__ == "__main__":
    unittest.main()
