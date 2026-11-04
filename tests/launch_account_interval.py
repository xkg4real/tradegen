"""Flat-only authentic Upbit interval producer over invented receipts: no network, credentials, signing, arming
or real home. Every instant is Seoul time; the fake exchange answers from the clock each capture gives it."""
import ast
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import fields, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import gc
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import weakref

from core.compliance.model import KST
from execution_accounts.baseline import BaselineAnchor, BaselineConventions, risk_baseline
from execution_accounts.baseline_bridge import (
    ContinuousAccountProvider, advance_account_baseline, initialize_account_baseline,
)
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.collector import CoverageEvidence, OpeningAnchor, SourceReceipt, TradeFeeEvidence
from execution_accounts.model import RiskBaseline, content_digest, page_digest
from execution_accounts.provider import build_observation
from execution_accounts.upbit_collector import collect_upbit
from execution_control.risk import RecoveryCheckpoint
from execution_launch import account_interval as AI
from execution_launch.account_interval import StagedInterval, UpbitIntervalSource, upbit_interval_frame
from tests import compliance_fixtures as F
from tests.accounts_baseline_integration import Head

D = Decimal
SCOPE = "interval-fixture"
FIRST_DAY = date(2026, 10, 26)
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def at(day, hour, minute=0, second=0, millisecond=0):
    return datetime(2026, 10, day, hour, minute, second, millisecond * 1000, tzinfo=KST)


ORIGIN = at(25, 10)
ANCHOR = OpeningAnchor(account_scope=SCOPE, origin=ORIGIN, cash_krw=D("100000"), source_sha256="a" * 64,
                       inventory_and_open_orders="verified-zero")
COVERAGE = CoverageEvidence(account_scope=SCOPE, source_sha256="c" * 64, history_from=ORIGIN,
    history_through=ORIGIN + timedelta(days=5), quiescent_from=ORIGIN, quiescent_until=ORIGIN + timedelta(days=5),
    identity_binding="reviewed-credential-to-main-pocket", history_retention="reviewed-complete-since-origin",
    transfer_scope="reviewed-no-unreported-flows-or-pocket-transfers", account_mode="reviewed-krw-spot-cash-only")
FEES = (TradeFeeEvidence(order_id="sell-1", fill_id="sell-fill-a", fee_krw=D("2"), source_sha256="f" * 64),
        TradeFeeEvidence(order_id="sell-1", fill_id="sell-fill-b", fee_krw=D("3"), source_sha256="f" * 64))
# The reducer's conventions are keyword-only (ruling R6).
CONVENTIONS = BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
    external_flows="no_external_flows", max_interval_seconds=30, recovery_cutoff_seconds=79200)
WIDE = replace(CONVENTIONS, max_interval_seconds=300)   # the reducer's widest bound, as the coordinator tests use


def order(uuid, side, created, price, trades, *, paid_fee="0"):
    """A done limit order as Upbit lists it, with its trade details; every trade at the order's instant."""
    volume = sum((D(units) for _, units, _ in trades), D(0))
    return dict(uuid=uuid, market="KRW-BTC", side=side, ord_type="limit", state="done",
        created_at=created.isoformat(), volume=str(volume), remaining_volume="0", executed_volume=str(volume),
        price=price, locked="0", paid_fee=paid_fee, trades_count=len(trades),
        trades=[dict(uuid=fill_id, market="KRW-BTC", side=side, price=price, volume=units, funds=funds,
                     created_at=created.isoformat()) for fill_id, units, funds in trades])


BUY = order("buy-1", "bid", at(26, 10), "10000", [("buy-fill", "1", "10000")], paid_fee="5")
SELL = order("sell-1", "ask", at(26, 11), "10100", [("sell-fill-a", "0.4", "4040"), ("sell-fill-b", "0.6", "6060")],
             paid_fee="5")


def deposit(uuid, amount, done):
    return dict(type="deposit", uuid=uuid, currency="KRW", state="ACCEPTED", fee="0", transaction_type="default",
                amount=amount, created_at=(done - timedelta(seconds=1)).isoformat(), done_at=done.isoformat())


def _ms(value):
    return (value - EPOCH) // timedelta(milliseconds=1)


class FakeClock:
    """Returns its instant and then advances by ``step_ms``; 0 makes a capture instantaneous."""
    def __init__(self, start, step_ms=0):
        self.now, self.step = start, timedelta(milliseconds=step_ms)

    def __call__(self):
        value = self.now
        self.now = value + self.step
        return value


class FakeUpbit:
    """Invented exchange answers stamped from the clock of the current capture; no transport is ever reached."""
    def __init__(self, *, account_scope=SCOPE, cash="100090", btc=None, orders=(BUY, SELL), ticker="10050"):
        self.account_scope, self.clock, self.calls = account_scope, None, []
        self.balances = [dict(currency="KRW", balance=cash, locked="0")]
        if btc is not None:
            self.balances.append(dict(currency="BTC", balance=btc, locked="0"))
        self.orders = [deepcopy(row) for row in orders]
        self.deposits, self.withdrawals, self.ticker = [], [], ticker

    def fetch(self, path, params):
        self.calls.append((path, params))
        query, now = dict(params), self.clock()
        listed = lambda row: {key: value for key, value in row.items() if key != "trades"}
        if path == "/v1/accounts":
            body = self.balances
        elif path == "/v1/orders/open":
            body = [listed(row) for row in self.orders if row["state"] == "wait"]
        elif path == "/v1/orders/closed":
            lo, hi = int(query["start_time"]), int(query["end_time"])
            body = [listed(row) for row in self.orders
                    if row["state"] != "wait" and lo <= _ms(datetime.fromisoformat(row["created_at"])) <= hi]
        elif path == "/v1/order":
            body = next(row for row in self.orders if row["uuid"] == query["uuid"])
        elif path == "/v1/deposits":
            body = self.deposits
        elif path == "/v1/withdraws":
            body = self.withdrawals
        elif path == "/v1/ticker":
            body = [dict(market=market, trade_price=self.ticker, timestamp=_ms(now), trade_timestamp=_ms(now))
                    for market in query["markets"].split(",")]
        else:
            raise AssertionError("unexpected synthetic route")
        raw = json.dumps(body, separators=(",", ":")).encode()
        return SourceReceipt(path=path, params=tuple(params), account_scope=self.account_scope, received_at=now,
                             server_time=now, raw_body=raw, sha256=hashlib.sha256(raw).hexdigest())


class Env:
    def __init__(self, home, exchange, fees, state, store, head, anchor_collection):
        self.home, self.exchange, self.fees = home, exchange, fees
        self.state, self.store, self.head, self.anchor_collection = state, store, head, anchor_collection
        self.source = UpbitIntervalSource()

    def current(self):
        return self.store.load(expected_head=self.head.value)

    def provider(self):
        return ContinuousAccountProvider(source=self.source, store=self.store, trusted_head=self.head)

    def collect(self, start, step_ms=0, *, previous=None, exchange=None, fees=None):
        exchange = self.exchange if exchange is None else exchange
        exchange.clock = clock = FakeClock(start, step_ms)
        return self.source.collect(exchange, previous=self.current() if previous is None else previous,
                                   anchor=ANCHOR, coverage=COVERAGE, clock=clock,
                                   trade_fees=self.fees if fees is None else fees)

    def capture(self, start, step_ms=0, *, previous=None, exchange=None, anchor=ANCHOR, coverage=COVERAGE):
        """collect_upbit directly, with the reducer's own export of ``previous`` as the collector baseline."""
        previous = self.current() if previous is None else previous
        exchange = self.exchange if exchange is None else exchange
        exchange.clock = clock = FakeClock(start, step_ms)
        baseline = risk_baseline(previous, now=previous.asof, expected_head=previous.state_digest)
        return collect_upbit(exchange, anchor=anchor, coverage=coverage, risk_baseline=baseline, clock=clock,
                             trade_fees=self.fees)


def seed(home, exchange, fees, start, *, day_start, high, loss, realized, day_open, previous, conventions=None):
    """Anchor the chain from one instantaneous capture at ``start``; the reviewed anchor binds those exact accounts."""
    exchange.clock = clock = FakeClock(start)
    probe = RiskBaseline(day_start_equity=day_start, prior_high_watermark=high, observed_daily_loss=loss,
                         approved_effective_floor=D("70000"), first_trading_day=FIRST_DAY, asof=start,
                         source_sha256="b" * 64)
    collection = collect_upbit(exchange, anchor=ANCHOR, coverage=COVERAGE, risk_baseline=probe, clock=clock,
                               trade_fees=fees)
    accounts = collection.bundle.accounts
    anchor = BaselineAnchor(account_scope=SCOPE, baseline=replace(probe, source_sha256=content_digest(accounts)),
        equity_krw=build_observation(collection.bundle, now=start).risk.equity, realized_net_total_krw=realized,
        day_open_realized_net_total_krw=day_open, previous_day_realized_net_krw=previous, sequence=0)
    state = initialize_account_baseline(conventions or CONVENTIONS, anchor, accounts, now=start).state
    store = CheckpointStore(root=home)
    store.seed(state, expected_head=state.state_digest)
    return state, store, Head(state.state_digest), collection


@contextmanager
def series(start, *, exchange=None, fees=FEES, day_start=D("100000"), high=D("100100"), loss=D("10"),
           realized=D("90"), day_open=D("0"), previous=None, conventions=None):
    """The first-trading-day series (10-26, 22:00 cutoff required) unless the anchor values say otherwise."""
    with F.temp_home() as home, patch("execution_accounts.upbit_collector.request",
                                      side_effect=AssertionError("network forbidden")):
        exchange = FakeUpbit() if exchange is None else exchange
        state, store, head, collection = seed(home, exchange, fees, start, day_start=day_start, high=high,
                                              loss=loss, realized=realized, day_open=day_open, previous=previous,
                                              conventions=conventions)
        yield Env(home, exchange, fees, state, store, head, collection)


def midnight_series(start=at(27, 23, 59, 40), *, conventions=None):
    """10-27 23:59:40 unless given, second trading day, 90 KRW prior-day profit: no cutoff pending, midnight next."""
    return series(start, day_start=D("100090"), high=D("100100"), loss=D("0"), realized=D("90"),
                  day_open=D("90"), previous=D("90"), conventions=conventions)


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return exc
    raise AssertionError("expected refusal " + code)


def test_flat_intervals_reconcile_cash_fifo_fees_cumulative_and_day_profit():
    with series(at(26, 20)) as env:
        staged = env.collect(at(26, 20, 0, 5), 100)
        frame, interval = staged.frame, staged.frame.interval
        assert type(staged) is StagedInterval and len(staged.receipts) == 11
        # collect() and collect_upbit() each read the clock once before the first balance read.
        assert staged.receipts[0].received_at == at(26, 20, 0, 5, 200) and staged.observed_at == at(26, 20, 0, 6, 300)
        assert interval.start == env.state.asof and interval.end == staged.observed_at == frame.accounts[0].observed_at
        observation = env.provider()(staged.observed_at + timedelta(milliseconds=100))
        assert observation.risk.equity == D("100090") and observation.risk.current_day_realized_net_profit == D("90")
        assert observation.risk.is_first_trading_day and observation.risk.prior_day_realized_net_profit is None
        assert tuple(fill.fee_amount for fill in observation.fills) == (D("5"), D("2"), D("3"))
        state = env.current()
        assert state.sequence == 1 and state.asof == interval.end and state.realized_net_total_krw == D("90")
        assert state.equity_krw == interval.equity_krw == interval.minimum_equity_krw == interval.maximum_equity_krw == D("100090")
        assert interval.gross_external_inflows_krw == 0 and interval.gross_external_outflows_krw == 0
        assert interval.source_sha256 == content_digest(frame.accounts)
        assert interval.coverage_sha256 == staged.manifest_sha256 == frame.accounts[0].pages[0].source_sha256
        assert state.high_watermark == D("100100") and state.observed_daily_loss == D("10")
        assert state.first_trading_day == FIRST_DAY and state.recovery_checkpoint is None
        assert len(env.head.commits) == 1 and env.head.value == state.state_digest
        assert not any(path == "/v1/ticker" for path, _ in env.exchange.calls)


def test_repeated_same_tick_calls_redeliver_identical_frame_and_advance_head_once():
    with series(at(26, 20)) as env:
        state0 = env.state
        staged = env.collect(at(26, 20, 0, 5), 100)
        now = staged.observed_at + timedelta(milliseconds=100)
        provider = env.provider()
        first = provider(now)
        for _ in range(3):
            assert provider(now) == first
        state1 = env.current()
        assert len(env.head.commits) == 1 and state1.sequence == 1
        assert env.source(state1, now) is staged.frame and env.source(state0, now) is staged.frame
        stale = env.collect(at(26, 20, 0, 10), 100, previous=state0)
        assert stale.frame.interval.previous_state_digest == state0.state_digest and stale.frame.interval.sequence == 1
        now2 = stale.observed_at + timedelta(milliseconds=100)
        refused(lambda: provider(now2), "BASELINE_INTERVAL_SOURCE_FAILED")
        refused(lambda: env.source(state1, now2), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        assert env.current() == state1 and env.head.value == state1.state_digest and len(env.head.commits) == 1


def test_round_trip_inside_interval_refuses_even_with_equal_endpoints():
    with series(at(26, 20)) as env:
        env.exchange.orders += [order("rt-buy", "bid", at(26, 20, 0, 2), "10000", [("rt-buy-fill", "1", "10000")]),
                                order("rt-sell", "ask", at(26, 20, 0, 3), "10000", [("rt-sell-fill", "1", "10000")])]
        refused(lambda: env.collect(at(26, 20, 0, 5), 100), "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
        assert any(path == "/v1/order" and dict(params)["uuid"] == "rt-sell" for path, params in env.exchange.calls)
        refused(lambda: env.source(env.state, at(26, 20, 0, 7)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        # The capture itself reconciles (cash is back at 100090); only the unknown path inside the interval refuses.
        collection = env.capture(at(26, 20, 0, 5))
        assert build_observation(collection.bundle, now=at(26, 20, 0, 5)).risk.equity == D("100090")
        refused(lambda: upbit_interval_frame(env.state, collection), "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
        assert env.current() == env.state and env.head.commits == []


def test_held_inventory_interval_refuses_without_price_path():
    exchange = FakeUpbit(cash="89995", btc="1", orders=(BUY,))
    with series(at(26, 20), exchange=exchange, fees=(), realized=D("0")) as env:
        assert env.state.equity_krw == D("100045") and env.state.realized_net_total_krw == 0
        refused(lambda: env.collect(at(26, 20, 0, 5), 100), "ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED")
        assert any(path == "/v1/ticker" for path, _ in env.exchange.calls)
        refused(lambda: env.source(env.state, at(26, 20, 0, 10)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        assert env.current() == env.state and env.head.commits == []


def test_flow_and_fee_coverage_refuse():
    with series(at(26, 20)) as env:
        env.exchange.deposits.append(deposit("dep-1", "1000", at(26, 20, 0, 2)))
        env.exchange.balances[0]["balance"] = "101090"
        refused(lambda: env.collect(at(26, 20, 0, 5), 100), "ACCOUNT_INTERVAL_EXTERNAL_FLOW_UNSUPPORTED")
        refused(lambda: env.source(env.state, at(26, 20, 0, 10)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
    with series(at(26, 20)) as env:
        refused(lambda: env.collect(at(26, 20, 0, 5), 100, fees=()), "COLLECTOR_PER_TRADE_FEE_EVIDENCE_REQUIRED")
        refused(lambda: env.source(env.state, at(26, 20, 0, 10)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        assert env.current() == env.state and env.head.commits == []


def test_wrong_scope_refuses_before_authenticated_read():
    with series(at(26, 20)) as env:
        other = FakeUpbit(account_scope="other-fixture")
        refused(lambda: env.collect(at(26, 20, 0, 5), 100, exchange=other), "ACCOUNT_INTERVAL_SCOPE_MISMATCH")
        assert other.calls == []
        foreign = env.capture(at(26, 20, 0, 5), exchange=other, anchor=replace(ANCHOR, account_scope="other-fixture"),
                              coverage=replace(COVERAGE, account_scope="other-fixture"))
        frame = upbit_interval_frame(env.state, foreign)
        assert frame.interval.account_scope == SCOPE and frame.accounts[0].account_scope == "other-fixture"
        refused(lambda: advance_account_baseline(env.state, frame.interval, frame.accounts, now=frame.interval.end),
                "BASELINE_BRIDGE_ACCOUNT_BINDING_MISMATCH")


def _pre_cutoff_commit(env):
    """7's state: a direct 21:59:59 capture committed through a lambda source at 21:59:59 (no checkpoint)."""
    frame = upbit_interval_frame(env.state, env.capture(at(26, 21, 59, 59)))
    provider = ContinuousAccountProvider(source=lambda previous, now: frame, store=env.store, trusted_head=env.head)
    return frame, provider, provider(at(26, 21, 59, 59))


def test_pre_cutoff_2159_59_cannot_extend_and_capture_must_bracket():
    with series(at(26, 21, 59, 40)) as env:
        state0 = env.state
        frame, provider, observation = _pre_cutoff_commit(env)
        assert frame.interval.end == at(26, 21, 59, 59) == frame.accounts[0].observed_at
        state1 = env.current()
        assert state1.sequence == 1 and state1.recovery_checkpoint is None and observation.risk.recovery_checkpoint is None
        refused(lambda: provider(at(26, 22)), "BASELINE_BRIDGE_EVIDENCE_REFUSED")
        refused(lambda: risk_baseline(state1, now=at(26, 22), expected_head=state1.state_digest),
                "BASELINE_RECOVERY_BOUNDARY_REQUIRED")
        refused(lambda: env.collect(at(26, 21, 59, 59), previous=state0), "ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED")
        refused(lambda: env.source(state0, at(26, 22)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        assert env.current() == state1 and len(env.head.commits) == 1


def test_exactly_2200_boundary_captures_real_equity_and_survives_restart():
    with series(at(26, 21, 59, 40)) as env:
        _pre_cutoff_commit(env)
        state1 = env.current()
        staged = env.collect(at(26, 22))
        assert staged.frame.interval.end == at(26, 22) == staged.observed_at == staged.receipts[0].received_at
        observation = env.provider()(at(26, 22, 0, 0, 500))
        checkpoint = RecoveryCheckpoint(cutoff_at=at(26, 22), equity_krw=D("100090"),
                                        source_sha256=staged.frame.interval.source_sha256)
        assert observation.risk.recovery_checkpoint == checkpoint
        state2 = env.current()
        assert state2.recovery_checkpoint == checkpoint and state2.asof == at(26, 22) and state2.sequence == 2
        assert state2.high_watermark == D("100100") and state2.observed_daily_loss == D("10")
        assert state2.first_trading_day == FIRST_DAY and state2.equity_krw == D("100090")
        later = env.collect(at(26, 22, 0, 5), 100)
        env.provider()(later.observed_at + timedelta(milliseconds=100))
        state3 = env.current()
        assert state3.recovery_checkpoint == checkpoint and state3.sequence == 3
        env.source, env.store = UpbitIntervalSource(), CheckpointStore(root=env.home)
        refused(lambda: env.provider()(at(26, 22, 0, 10)), "BASELINE_INTERVAL_SOURCE_FAILED")
        again = env.collect(at(26, 22, 0, 15), 100)
        env.provider()(again.observed_at + timedelta(milliseconds=100))
        state4 = env.current()
        assert state4.recovery_checkpoint == checkpoint and state4.sequence == 4
        assert [new for _, new in env.head.commits] == [s.state_digest for s in (state1, state2, state3, state4)]


def test_bracketing_capture_is_stamped_at_boundary_without_relabelling():
    with series(at(26, 21, 59, 50)) as env:
        staged = env.collect(at(26, 21, 59, 59, 500), 100)
        frame, account = staged.frame, staged.frame.accounts[0]
        assert staged.receipts[0].received_at == at(26, 21, 59, 59, 700) and staged.observed_at == at(26, 22, 0, 0, 800)
        assert account.observed_at == at(26, 22) == frame.interval.end and account.observed_at < staged.observed_at
        assert all(page.end == at(26, 22) and page.start == ORIGIN and page.page_sha256 == page_digest(page)
                   for page in account.pages)
        assert account.restrictions.asof == at(26, 22) and all(rate.asof == at(26, 22) for rate in account.fx)
        assert account.server_time == staged.receipts[-1].server_time == at(26, 22, 0, 0, 700)
        # The same capture taken directly (one clock read fewer, so it starts 100 ms later): identical receipts and
        # manifest, only the stamping differs.
        unstamped = env.capture(at(26, 21, 59, 59, 600), 100).bundle.accounts
        assert unstamped[0].observed_at == staged.observed_at
        assert frame.interval.source_sha256 == content_digest(frame.accounts) != content_digest(unstamped)
        assert [page.rows for page in account.pages] == [page.rows for page in unstamped[0].pages]
        assert frame.interval.coverage_sha256 == staged.manifest_sha256 == unstamped[0].pages[0].source_sha256
        observation = env.provider()(staged.observed_at + timedelta(milliseconds=100))
        assert observation.risk.recovery_checkpoint.equity_krw == D("100090")
        assert env.current().recovery_checkpoint == RecoveryCheckpoint(cutoff_at=at(26, 22), equity_krw=D("100090"),
                                                                       source_sha256=frame.interval.source_sha256)


def test_after_2200_late_capture_never_becomes_boundary():
    with series(at(26, 21, 59, 50)) as env:
        seeded = len(env.exchange.calls)
        refused(lambda: env.collect(at(26, 22, 0, 0, 100)), "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
        assert len(env.exchange.calls) == seeded
        collection = env.capture(at(26, 22, 0, 0, 100))
        refused(lambda: upbit_interval_frame(env.state, collection), "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
        fetched = len(env.exchange.calls)
        refused(lambda: env.collect(at(26, 22, 5)), "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
        assert len(env.exchange.calls) == fetched
        refused(lambda: env.source(env.state, at(26, 22, 5)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        assert env.current() == env.state and env.head.commits == []


def test_true_seoul_midnight_opening_boundary():
    with midnight_series() as env:
        staged = env.collect(at(27, 23, 59, 59, 500), 100)
        assert staged.frame.interval.end == at(28, 0) == staged.frame.accounts[0].observed_at
        assert staged.receipts[0].received_at == at(27, 23, 59, 59, 700) and staged.observed_at == at(28, 0, 0, 0, 800)
        observation = env.provider()(staged.observed_at + timedelta(milliseconds=100))
        state = env.current()
        assert state.asof == at(28, 0) and state.sequence == 1
        assert state.day_start_equity == D("100090") and state.observed_daily_loss == 0
        assert state.previous_day_realized_net_krw == 0 and state.day_open_realized_net_total_krw == D("90")
        assert state.high_watermark == D("100100") and state.first_trading_day == FIRST_DAY
        assert state.recovery_checkpoint is None
        assert observation.risk.prior_day_realized_net_profit == 0 and not observation.risk.is_first_trading_day
        assert observation.risk.day_start_equity == D("100090") and observation.risk.current_day_realized_net_profit == 0


def test_midnight_early_late_and_unbracketed_captures_refuse():
    with midnight_series() as env:
        refused(lambda: env.collect(at(27, 23, 59, 55), 10), "EVIDENCE_STALE_OR_FUTURE")
        fetched = len(env.exchange.calls)
        refused(lambda: env.collect(at(28, 0, 0, 0, 300)), "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
        assert len(env.exchange.calls) == fetched
        refused(lambda: env.collect(at(27, 23, 59, 45), 1500), "RISK_DAY_MISMATCH")
        refused(lambda: env.source(env.state, at(28, 0, 0, 5)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        assert env.current() == env.state and env.head.commits == []


def test_midnight_capture_after_a_gap_over_30s_refuses_and_a_later_capture_misses_the_boundary():
    """R17 (docs review C, M2, the reviewer's probe): the capture bracketing midnight is collected against the
    midnight opening and must also observe within 30 s of the last committed end, as every capture does, so even
    the reducer's widest bound never heals the gap. Once midnight passes every capture misses the boundary, so
    only the reviewed re-anchor (not run here) can recover."""
    with midnight_series(at(27, 23, 59), conventions=WIDE) as env:
        gap = refused(lambda: env.collect(at(27, 23, 59, 40), 10), "EVIDENCE_STALE_OR_FUTURE")          # 40 s gap
        boundary = refused(lambda: env.collect(at(27, 23, 59, 59, 500), 100), "EVIDENCE_STALE_OR_FUTURE")  # 60.8 s
        assert type(boundary) is type(gap)
        refused(lambda: env.source(env.state, at(28, 0, 0, 1)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        refused(lambda: env.provider()(at(28, 0, 0, 1)), "BASELINE_INTERVAL_SOURCE_FAILED")
        fetched = len(env.exchange.calls)
        refused(lambda: env.collect(at(28, 0, 0, 5), 100), "ACCOUNT_INTERVAL_BOUNDARY_MISSED")
        assert len(env.exchange.calls) == fetched
        assert env.current() == env.state and env.head.commits == []


def test_old_coherent_rollback_restored_before_midnight_refuses_at_the_midnight_capture():
    """R17 with ruling R5: both roots restored (and the process restarted) to an older coherent state of this
    chain, committed 39.5 s before the midnight observation, refuse at the bracketing capture as at any other
    capture; nothing is staged and nothing commits, even under the reducer's widest bound."""
    with midnight_series(at(27, 23, 59), conventions=WIDE) as env:
        checkpoint = env.home / "execution-baseline" / "checkpoint.json"
        first = env.collect(at(27, 23, 59, 20), 100)
        env.provider()(first.observed_at + timedelta(milliseconds=100))
        state1, c1 = env.current(), checkpoint.read_bytes()
        second = env.collect(at(27, 23, 59, 40), 100)
        env.provider()(second.observed_at + timedelta(milliseconds=100))
        assert env.current().sequence == 2 and state1.asof == at(27, 23, 59, 21, 300)
        checkpoint.write_bytes(c1); env.head = Head(state1.state_digest)       # the coherent rollback of both roots
        env.source, env.store = UpbitIntervalSource(), CheckpointStore(root=env.home)              # and a restart
        assert env.current() == state1
        refused(lambda: env.collect(at(27, 23, 59, 59, 500), 100), "EVIDENCE_STALE_OR_FUTURE")
        refused(lambda: env.source(state1, at(28, 0, 0, 1)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        refused(lambda: env.provider()(at(28, 0, 0, 1)), "BASELINE_INTERVAL_SOURCE_FAILED")
        assert env.current() == state1 and env.head.commits == []


def test_midnight_capture_one_millisecond_over_30s_refuses_inside_the_default_reducer_bound():
    """R17 at the edge: observing at 00:00:00.800, 30.001 s after the committed end, refuses although the interval
    to midnight (29.201 s) fits the default 30 s reducer bound: the threshold is the freshness rule's, read from
    the collector's single ``_STALE`` (set to 20 s, a 25 s gap refuses the same way)."""
    with midnight_series(at(27, 23, 59, 30, 799)) as env:
        refused(lambda: env.collect(at(27, 23, 59, 59, 500), 100), "EVIDENCE_STALE_OR_FUTURE")
        refused(lambda: env.source(env.state, at(28, 0, 0, 1)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")
        assert env.current() == env.state and env.head.commits == []
    with midnight_series(at(27, 23, 59, 35, 800)) as env, patch("execution_accounts.provider._STALE",
                                                                timedelta(seconds=20)):
        refused(lambda: env.collect(at(27, 23, 59, 59, 500), 100), "EVIDENCE_STALE_OR_FUTURE")    # 25 s gap
        refused(lambda: env.source(env.state, at(28, 0, 0, 1)), "ACCOUNT_INTERVAL_PREFETCH_REQUIRED")


def test_midnight_capture_exactly_30s_after_the_committed_end_commits_the_opening():
    """The good path at the edge: an observation exactly 30 s after the committed end is fresh (the rule is
    inclusive), so the bracketing capture is staged and commits the midnight opening."""
    with midnight_series(at(27, 23, 59, 30, 800)) as env:
        staged = env.collect(at(27, 23, 59, 59, 500), 100)
        assert staged.observed_at == at(28, 0, 0, 0, 800) == env.state.asof + timedelta(seconds=30)
        assert staged.frame.interval.end == at(28, 0) == staged.frame.accounts[0].observed_at
        env.provider()(staged.observed_at + timedelta(milliseconds=100))
        state = env.current()
        assert state.asof == at(28, 0) and state.sequence == 1 and state.day_start_equity == D("100090")
        assert len(env.head.commits) == 1 and env.head.value == state.state_digest


def test_tick_before_capture_gap_and_reused_capture_refuse():
    with series(at(26, 20)) as env:
        staged = env.collect(at(26, 20, 0, 5), 100)
        early = staged.observed_at - timedelta(milliseconds=100)
        refused(lambda: env.provider()(early), "BASELINE_INTERVAL_SOURCE_FAILED")
        refused(lambda: env.source(env.state, early), "ACCOUNT_INTERVAL_EVIDENCE_AFTER_TICK")
        assert env.head.commits == [] and env.current() == env.state
        refused(lambda: env.collect(at(26, 20, 0, 40)), "EVIDENCE_STALE_OR_FUTURE")
        refused(lambda: upbit_interval_frame(env.state, env.anchor_collection),
                "ACCOUNT_INTERVAL_CAPTURE_NOT_AFTER_PREVIOUS")
        # A refused prefetch leaves the earlier staged frame as it was.
        assert env.source(env.state, staged.observed_at) is staged.frame


def test_refusals_are_fixed_codes_without_private_values():
    class Leaky:
        account_scope = SCOPE

        def fetch(self, path, params):
            raise RuntimeError("private account detail 100090")

    with series(at(26, 20)) as env:
        fetched = len(env.exchange.calls)
        exc = refused(lambda: env.collect(at(26, 20, 0, 5), exchange=Leaky()), "ACCOUNT_INTERVAL_COLLECTION_FAILED")
        assert exc.__cause__ is None and "100090" not in str(exc) and "private" not in str(exc)
        naive = datetime(2026, 10, 26, 11)
        refused(lambda: env.source.collect(env.exchange, previous=env.state, anchor=ANCHOR, coverage=COVERAGE,
                                           clock=lambda: naive, trade_fees=FEES), "COLLECTOR_AWARE_TIME_REQUIRED")

        def broken_clock():
            raise RuntimeError("secret clock 100090")
        exc = refused(lambda: env.source.collect(env.exchange, previous=env.state, anchor=ANCHOR, coverage=COVERAGE,
                                                 clock=broken_clock, trade_fees=FEES),
                      "ACCOUNT_INTERVAL_COLLECTION_FAILED")
        assert "100090" not in str(exc)
        assert len(env.exchange.calls) == fetched
        for kwargs in (dict(previous="state"), dict(clock=None), dict(trade_fees=list(FEES))):
            values = dict(previous=env.state, anchor=ANCHOR, coverage=COVERAGE, clock=FakeClock(at(26, 20, 0, 5)),
                          trade_fees=FEES) | kwargs
            refused(lambda: env.source.collect(env.exchange, **values), "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        refused(lambda: env.source(env.state, naive), "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        refused(lambda: env.source("state", at(26, 20, 0, 5)), "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        refused(lambda: upbit_interval_frame(env.state, "collection"), "ACCOUNT_INTERVAL_INPUT_REQUIRED")
        collection = env.capture(at(26, 20, 0, 5))
        bundle = collection.bundle
        for broken in (replace(collection, receipts=()), replace(collection, manifest_sha256="0" * 64),
                       replace(collection, bundle=replace(bundle, accounts=bundle.accounts * 2)),
                       replace(collection, bundle=replace(bundle, risk_baseline=replace(
                           bundle.risk_baseline, first_trading_day=FIRST_DAY - timedelta(days=1))))):
            refused(lambda: upbit_interval_frame(env.state, broken), "ACCOUNT_INTERVAL_COLLECTION_BINDING_INVALID")
        assert upbit_interval_frame(env.state, collection).interval.end == at(26, 20, 0, 5)
        assert env.exchange.calls[fetched][0] == "/v1/accounts"


def test_opening_collection_baseline_never_leaves_the_module_and_is_discarded_before_export():
    """Ruling R6: the midnight collector baseline is built by one private helper, called once from ``collect``,
    is unreachable once ``collect`` returns, and the bridge exports the reducer's own baseline afterwards."""
    tree = ast.parse(Path(AI.__file__).read_text(encoding="utf-8"))
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    builders = [function for function in functions if any(
        isinstance(node, ast.Call) and ast.unparse(node.func) == "RiskBaseline" for node in ast.walk(function))]
    assert len(builders) == 1 and builders[0].name.startswith("_"), [function.name for function in builders]
    helper = builders[0].name
    callers = [function.name for function in functions if function is not builders[0]
               and any(isinstance(node, ast.Name) and node.id == helper for node in ast.walk(function))]
    assert callers == ["collect"]
    assert sum(isinstance(node, ast.Name) and node.id == helper for node in ast.walk(tree)) == 1
    assert {field.name for field in fields(StagedInterval)} == {"frame", "receipts", "manifest_sha256", "observed_at"}
    with midnight_series() as env:
        handed, real = [], AI.collect_upbit

        def spy(source, **kwargs):
            baseline = kwargs["risk_baseline"]
            handed.append((weakref.ref(baseline), baseline.asof, baseline.source_sha256, baseline.day_start_equity,
                           baseline.observed_daily_loss))
            return real(source, **kwargs)
        with patch.object(AI, "collect_upbit", spy):
            staged = env.collect(at(27, 23, 59, 59, 500), 100)
        gc.collect()
        (ref, asof, digest, opening, loss), = handed
        assert ref() is None, "the opening collection baseline outlived collect()"
        assert asof == at(28, 0) and digest == env.state.state_digest
        assert opening == env.state.equity_krw and loss == 0 and staged.frame.interval.end == at(28, 0)
        env.provider()(staged.observed_at + timedelta(milliseconds=100))
        state = env.current()
        exported = risk_baseline(state, now=state.asof, expected_head=state.state_digest)
        assert exported.asof == at(28, 0) and exported.source_sha256 == state.state_digest != digest
        assert exported.day_start_equity == opening and exported.observed_daily_loss == 0
        with patch.object(AI, "collect_upbit", spy):
            env.collect(at(28, 0, 0, 5), 100)
        assert handed[1][1:3] == (state.asof, state.state_digest)
