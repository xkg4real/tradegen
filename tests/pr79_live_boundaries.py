"""Held interval and committed guard boundary regressions. All sources and homes are synthetic."""
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from decimal import Decimal
import unittest
from unittest.mock import patch

from execution_accounts.baseline_bridge import BidGapObservation, advance_account_baseline
from execution_accounts.continuous import PriceMark
from execution_accounts.model import Position
from execution_launch import guard_capture_format as fmt
from execution_launch import account_interval as interval
from execution_launch.committed_startup import CommittedStartup
from tests import launch_account_interval as fixture
from tests import launch_committed_producer as producer
from tests import launch_coordinator_committed as coordinator
from tests.control_acceptance import _wrap


class TestLiveBoundaries(unittest.TestCase):
    def test_capture_codec_preserves_historical_position_and_fresh_bid_exactly(self):
        mark = Position(market="spot", symbol="KRW-BTC", base_currency="BTC", quote_currency="KRW",
                        units=Decimal(1), price=Decimal(99), asof=producer.START)
        def encode(pos):
            return fmt._Codec(fmt.DEFAULT_LIMITS, {}).value(pos, "Position", decode=False)
        def decode(wire):
            return fmt._Codec(fmt.DEFAULT_LIMITS, {}).value(wire, "Position", decode=True)
        legacy = encode(mark)
        self.assertEqual(set(legacy["v"]), {"market", "symbol", "base_currency", "quote_currency",
                                            "units", "price", "asof", "unlisted"})
        self.assertEqual(encode(decode(legacy)), legacy)
        with_bid = replace(mark, best_bid=Decimal("92.50"), best_bid_asof=producer.START)
        wire = encode(with_bid)
        self.assertEqual(encode(decode(wire)), wire)
        self.assertEqual(decode(wire).best_bid.as_tuple(), with_bid.best_bid.as_tuple())
        incomplete = {"$": "Position", "v": dict(wire["v"])}
        del incomplete["v"]["best_bid_asof"]
        with self.assertRaises(fmt.GuardCaptureFormatError):
            decode(incomplete)

    def test_cutoff_orders_require_evidence_of_completion_before_cutoff(self):
        fill = SimpleNamespace(order_id="order-1", quantity=Decimal(2))
        order = SimpleNamespace(order_id="order-1", quantity=Decimal(2), status="filled")
        self.assertEqual(interval._closed_orders_at_cutoff((order,), (fill,)), (order,))
        for status in ("open", "partial", "canceled"):
            row = SimpleNamespace(order_id="order-1", quantity=Decimal(2), status=status)
            with self.assertRaisesRegex(ValueError, "ACCOUNT_INTERVAL_BOUNDARY_ORDER_EVIDENCE_REQUIRED"):
                interval._closed_orders_at_cutoff((row,), (fill,))
        with self.assertRaisesRegex(ValueError, "ACCOUNT_INTERVAL_BOUNDARY_ORDER_EVIDENCE_REQUIRED"):
            interval._closed_orders_at_cutoff((order,), ())

    def test_opening_valuation_requires_evidence_for_each_price(self):
        start = producer.START
        symbols = ("KRW-AAA", "KRW-BBB")
        units = ((symbols[0], Decimal(2)), (symbols[1], Decimal(1)))
        args = dict(start=start, equity=Decimal(25), cash=Decimal(5))
        with self.assertRaisesRegex(interval.AccountIntervalError, "ACCOUNT_INTERVAL_OPENING_MARK_REQUIRED"):
            interval._opening_trade_marks({}, {}, symbols, units, **args)
        committed = PriceMark(symbol=symbols[0], price=Decimal(6), asof=start)
        marks = interval._opening_trade_marks({committed.symbol: committed}, {}, symbols, units, **args)
        self.assertEqual(marks[symbols[1]], PriceMark(symbol=symbols[1], price=Decimal(8), asof=start))
        future = PriceMark(symbol=symbols[0], price=Decimal(6), asof=start + timedelta(milliseconds=1))
        with self.assertRaisesRegex(interval.AccountIntervalError, "ACCOUNT_INTERVAL_OPENING_MARK_INVALID"):
            interval._opening_trade_marks({future.symbol: future}, {}, symbols, units, **args)

    def test_held_preview_carries_the_scope_and_policy_observed_at_the_endpoint(self):
        def check():
            exchange = fixture.FakeUpbit(cash="89995", btc="1", orders=(fixture.BUY,))
            with fixture.series(producer.START, exchange=exchange, fees=(), realized=Decimal(0)) as env:
                end = producer.START + timedelta(seconds=5)
                capture = env.capture(end)
                with self.assertRaisesRegex(ValueError, "ACCOUNT_INTERVAL_TRADE_WINDOW_REQUIRED"):
                    interval.upbit_held_interval_frames(env.state, capture, trade_path={})
                with self.assertRaisesRegex(ValueError, "ACCOUNT_INTERVAL_TICKER_CHECK_BLOCK_ALERT_REQUIRED"):
                    interval.upbit_held_interval_frames(env.state, capture, trade_path={
                        "KRW-BTC": SimpleNamespace(ticker_discrepancy=("raw-ticker",))})
                reads = []
                def scope_policy(stamp, scope):
                    reads.append((stamp, scope))
                    return None
                (frame,) = interval.upbit_held_interval_frames(
                    env.state, capture, trade_path={"KRW-BTC": ()}, bid_gap_y=scope_policy)
                self.assertEqual(reads, [(end, fixture.SCOPE)])
                self.assertEqual(frame.bid_gap, BidGapObservation(account_scope=fixture.SCOPE, asof=end, threshold=None))
                current = advance_account_baseline(env.state, frame.interval, frame.accounts, now=end,
                                                   bid_gap=frame.bid_gap)
                self.assertTrue(current.observation.risk.bid_gap_policy_missing)
                foreign = BidGapObservation(account_scope="other-scope", asof=end, threshold=Decimal(".01"))
                with self.assertRaisesRegex(ValueError, "BASELINE_BRIDGE_BID_GAP_BINDING_MISMATCH"):
                    advance_account_baseline(env.state, frame.interval, frame.accounts, now=end, bid_gap=foreign)
        _wrap(check)()

    def test_flat_held_capable_source_does_not_lose_missing_y_on_first_buy(self):
        def check():
            with fixture.series(producer.START) as env:
                env.source = interval.UpbitIntervalSource(trade_window_collector=lambda *_: self.fail("flat account"))
                end = producer.START + timedelta(seconds=5)
                staged = env.collect(end)
                self.assertIsNone(staged.frame.bid_gap.threshold)
                self.assertTrue(env.provider()(end).risk.bid_gap_policy_missing)
        _wrap(check)()

    def test_lost_commit_acknowledgment_blocks_held_coordinator(self):
        # The actual guard and baseline commit completes, but its caller loses the reply.
        # Re-reading this account must not dispatch against the previous committed head.
        def check():
            with producer.fixture(bind_startup=False, held=True) as env:
                runtime = coordinator.build(env)
                producer.arm_interval(env)
                self.assertFalse(runtime.bootstrap().account_source)
                previous = runtime._committed_account
                producer.arm_interval(env)
                real_commit = CommittedStartup.commit_input
                def lose_acknowledgment(startup, input_digest):
                    real_commit(startup, input_digest)
                    raise OSError("synthetic acknowledgment loss")
                with patch.object(CommittedStartup, "commit_input", lose_acknowledgment):
                    result = runtime.bootstrap()
                self.assertEqual(result.account_source, "COMMITTED_PRODUCER_COMMIT_UNCONFIRMED")
                self.assertTrue(result.new_entry_blocked)
                self.assertFalse(runtime._ready)
                self.assertIs(runtime._committed_account, previous)
                self.assertEqual(coordinator.counts(env), (2, 2))
                retry = runtime.bootstrap()
                self.assertTrue(retry.new_entry_blocked)
                self.assertFalse(runtime._ready)
                self.assertEqual(coordinator.counts(env), (2, 2))
                self.assertEqual(coordinator.creates(env), ())
        _wrap(check)()
