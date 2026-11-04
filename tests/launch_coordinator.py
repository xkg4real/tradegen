"""Windows coordinator over doubles and, in two tests, the real interval/head/history/authority adapters over fake
transports: invented data, temporary state and head roots, fixture signatures; nothing arms, orders, reads a
credential, opens a socket or touches a real home."""
from __future__ import annotations

import ast
from contextlib import contextmanager, nullcontext
import copy
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner, rules
from core.compliance.model import KST
from core.isolation import state_root
from execution_accounts.baseline import BaselineAnchor, BaselineConventions, BaselineInterval
from execution_accounts.baseline_bridge import BaselineFrame, initialize_account_baseline
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.model import RiskBaseline, content_digest
from execution_control.capability import digest
from execution_control.dry_run import DryRunAdapter
from execution_control.risk import RecoveryCondition
from execution_control.store import GENESIS
from execution_launch import coordinator as C
from execution_launch.account_interval import UpbitIntervalSource, _pending_boundary
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.coordinator import (CancellableTimer, Coordinator, CoordinatorError, compose,
                                          history_head_name, schedule)
from execution_launch.driver import DeploymentWindow, describe_fixed_driver, make_fixed_driver
from execution_launch.live_history import STORE_DIRECTORY, HistoryChain
from execution_launch.paper_capture import CaptureArchive, capture_json
from execution_launch.profile import profile_body, profile_contract_digest, rule_terms_digest
from execution_launch.program import ProgramSpec, parameters_json, program_digest, program_json
from execution_launch.review_auth import review_body
from execution_launch.review_request import build_review_request
from execution_launch.runner import EvidencePackage, ImplementationBinding, Signal, StrategyDriver
from execution_launch.strategy import (assess_strategy, capture_history_digests, protocol_json, register_protocol,
                                       run_paper_validation)
from execution_orders import upbit
from execution_orders.model import AdapterResult
from tests import compliance_fixtures as F
from tests import launch_driver as LD
from tests.accounts_baseline_integration import Head
from tests.accounts_provider import SCOPE, bundle, fill, order
from tests.control_session import selected
from tests.launch_account_interval import ANCHOR, COVERAGE, FEES, SCOPE as INTERVAL_SCOPE, FakeUpbit, at
from tests.launch_account_interval import seed as seed_interval_chain
from tests.launch_baseline_head import head_root
from tests.launch_capture import book
from tests.launch_guards import problems
from tests.launch_profile import fixture_profile
from tests.launch_review_auth import document, invented_provider, invented_verifier
from tests.launch_runner import creates, evidence_for, runner_fixture
from tests.launch_strategy import fixture_capture
from tests.launch_windows_owner_authority import keys, raw, real_code_hash, signed_home

D = Decimal
ROOT = Path(__file__).resolve().parents[1]
MODULE = "execution_launch/coordinator.py"
PRICE = D("100000000")
EQUITY = D("1000000")
EXIT = Signal(signal_id="fixed-exit", action="exit", quantity=D("0.0001"), limit_price=PRICE)
HOLD = Signal(signal_id="fixed-hold", action="hold")
CUTOFF_NOW = datetime(2026, 10, 24, 21, 58, tzinfo=KST)
SAME = object()                      # fixture(chain_cutoff=SAME): the chain carries the profile's cutoff


def seconds(value):
    return timedelta(seconds=value)


def refused(call, code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == code, (str(exc), code)
        return exc
    raise AssertionError("expected refusal " + code)


@contextmanager
def memoized_pure_loads():
    """Two pure functions of unchanging inputs computed once for the block, so every load_context behind
    Controller.observe costs a fraction of a second instead of 1.5 s: owner.code_files (the closure on disk does
    not change inside a test; the signed hash is still compared with the real value) and rules.load_strict (the
    strict YAML parse of approved table bytes; every hash is still computed over the raw bytes). Nothing checked
    changes. The real-adapter tests do not use it."""
    real_files, real_load, files, tables = owner.code_files, rules.load_strict, {}, {}

    def memo_files(root):
        key = Path(root).resolve()
        if key not in files:
            files[key] = real_files(root)
        return list(files[key])

    def memo_load(raw, what):
        key = (bytes(raw), what)
        if key not in tables:
            tables[key] = real_load(raw, what)
        return copy.deepcopy(tables[key])
    with patch.object(owner, "code_files", memo_files), patch.object(rules, "load_strict", memo_load):
        yield


class FakeTime:
    """clock() returns now and then advances it by 1 ms, so readings stay strictly increasing; wait() runs the hooks
    due before its target (a hook may jump time or call stop/close), then advances to the target unless the event
    is set."""
    def __init__(self, start):
        self.now, self.hooks, self.reads = start, [], 0

    def clock(self):
        value = self.now
        self.now, self.reads = value + timedelta(milliseconds=1), self.reads + 1
        return value

    def at(self, when, fn):
        self.hooks.append((when, fn))
        self.hooks.sort(key=lambda hook: hook[0])

    def wait(self, event, interval):
        target = self.now + seconds(interval)
        while self.hooks and self.hooks[0][0] <= target and not event.is_set():
            when, fn = self.hooks.pop(0)
            self.now = max(self.now, when)
            fn()
        if not event.is_set() and self.now < target:
            self.now = target
        return event.is_set()


class CountingHead(Head):
    """The test double head with a read counter and a one-shot compare-and-set failure."""
    def __init__(self, value):
        super().__init__(value)
        self.reads, self.fail_next = 0, False

    def read(self):
        self.reads += 1
        return self.value

    def compare_and_set(self, previous, new):
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("HEAD-SECRET")
        return super().compare_and_set(previous, new)


class Producer:
    """The interval producer contract over invented flat evidence: prefetch(previous) does the fetching (fake
    latency, an optional hang or failure) and __call__(previous, now) returns the frame without I/O. A pending 22:00
    cutoff or Seoul midnight is bracketed only when the prefetch started at or before it; a later prefetch refuses
    with a non-fixed text standing in for the real producer's refusal, unless `crossing` makes it dishonest."""
    def __init__(self, fake, fills, orders):
        self.fake, self.calls, self.prefetches, self.states = fake, [], [], []
        self.fills, self.orders, self.cash, self.units = fills, orders, D("900000"), D("0.001")
        self.latency, self.crossing, self.fail, self.block, self.jump_once = 0, False, None, None, 0

    def prefetch(self, previous):
        self.prefetches.append((self.fake.now, previous.state_digest))
        self.states.append(previous)
        if self.block is not None and len(self.prefetches) == 2:
            entered, release = self.block
            entered.set()
            release.wait(5)
        if self.latency:
            self.fake.now += seconds(self.latency)
        if self.jump_once:
            self.fake.now, self.jump_once = self.fake.now + seconds(self.jump_once), 0
        if self.fail is not None:
            raise self.fail

    def __call__(self, previous, now):
        self.calls.append(now)
        boundary, _ = _pending_boundary(previous)
        end = now
        if previous.asof < boundary <= now and not self.crossing:
            started = self.prefetches[-1][0] if self.prefetches else now
            if started > boundary:
                raise RuntimeError("ACCOUNT-SECRET-77")
            end = boundary
        accounts = bundle(now=end, fills=self.fills, orders=self.orders, cash=self.cash, units=self.units,
                          price=PRICE).accounts
        interval = BaselineInterval(account_scope=SCOPE, sequence=previous.sequence + 1,
            previous_state_digest=previous.state_digest, start=previous.asof, end=end, equity_krw=EQUITY,
            minimum_equity_krw=EQUITY, maximum_equity_krw=EQUITY, realized_net_total_krw=D("0"),
            gross_external_inflows_krw=D("0"), gross_external_outflows_krw=D("0"),
            source_sha256=content_digest(accounts), coverage_sha256="c" * 64)
        return BaselineFrame(interval=interval, accounts=accounts)


class Books:
    """A quote source double: the book is received at the read time with a one-second-old orderbook stamp;
    `delay` seconds pass before the receipt (a slow request), `jump_once` seconds after it."""
    def __init__(self, fake, *, bid=99999999, ask=100000000):
        self.fake, self.reads, self.jump_once, self.bid, self.ask = fake, 0, 0, bid, ask
        self.received, self.delay = [], 0

    def read(self):
        self.reads += 1
        if self.delay:
            self.fake.now += seconds(self.delay)
        received = self.fake.clock()
        self.received.append(received)
        if self.jump_once:
            self.fake.now, self.jump_once = self.fake.now + seconds(self.jump_once), 0
        return book(received, received_delta=0, asof_delta=-1, bid=self.bid, ask=self.ask)


def chain_state(t0, *, cutoff=None):
    """The reviewed anchor five seconds before t0: 0.001 BTC bought a day earlier at PRICE with no fee, 900000 KRW
    cash, equity 1000000 (day start, peak), floor 750000, not the first trading day, zero prior-day profit."""
    anchored = t0 - seconds(5)
    bought = fill(side="buy", quantity=D("0.001"), price=PRICE, fee=D("0"), order="pre-buy", fid="pre-fill",
                  at=anchored - timedelta(days=1))
    listed = order(side="buy", quantity=D("0.001"), filled=D("0.001"), price=PRICE, oid="pre-buy",
                   client="pre-client", status="filled")
    accounts = bundle(now=anchored, fills=(bought,), orders=(listed,), cash=D("900000"), units=D("0.001"),
                      price=PRICE).accounts
    baseline = RiskBaseline(day_start_equity=EQUITY, prior_high_watermark=EQUITY, observed_daily_loss=D("0"),
        approved_effective_floor=D("750000"), first_trading_day=anchored.astimezone(KST).date() - timedelta(days=5),
        asof=anchored, source_sha256=content_digest(accounts))
    anchor = BaselineAnchor(account_scope=SCOPE, baseline=baseline, equity_krw=EQUITY, realized_net_total_krw=D("0"),
        day_open_realized_net_total_krw=D("0"), previous_day_realized_net_krw=D("0"), sequence=0)
    conventions = BaselineConventions(daily_loss="maximum_net_equity_loss_from_day_open",
        external_flows="no_external_flows", max_interval_seconds=300, recovery_cutoff_seconds=cutoff)
    return initialize_account_baseline(conventions, anchor, accounts, now=anchored).state, (bought,), (listed,)


def driver_for(env):
    """The fixture's reviewed artifact and parameters with a recording callback, so program_digest is unchanged."""
    decisions = []

    def callback(observation, parameters):
        decisions.append(observation)
        return env.signal[0]
    return StrategyDriver(callback=callback, artifact=env.driver.artifact,
                          parameters_json=env.driver.parameters_json), decisions


@contextmanager
def fixture(*, now=None, cutoff=None, chain_cutoff=SAME):
    """runner_fixture (temporary signed home, DryRunAdapter, policy: initial equity 100000, activation 800000,
    budgets 10) plus the seeded flat account chain, the fake clock, the producer and book doubles and a recording
    driver whose default decision is the exit signal. `cutoff` is the profile's recovery condition and, unless
    `chain_cutoff` says otherwise, the chain's recovery_cutoff_seconds."""
    with memoized_pure_loads(), (nullcontext() if now is None else patch.object(F, "NOW", now)), \
            runner_fixture(prepare=False, arm=False) as env:
        t0 = env.now
        profile = replace(env.profile, account_scope=SCOPE)
        if cutoff is not None:
            profile = replace(profile, policy=replace(profile.policy, recovery_condition=RecoveryCondition(
                cutoff_seconds=cutoff, timezone="Asia/Seoul", reference="day_start_marked_equity")))
        env.profile, env.evidence, env.t0 = profile, evidence_for(profile, t0), t0
        env.state, fills, orders = chain_state(t0, cutoff=cutoff if chain_cutoff is SAME else chain_cutoff)
        CheckpointStore(root=env.home).seed(env.state, expected_head=env.state.state_digest)
        env.fake = FakeTime(t0)
        env.head, env.books = CountingHead(env.state.state_digest), Books(env.fake)
        env.producer = Producer(env.fake, fills, orders)      # every capture carries the complete history
        env.signal = [EXIT]
        env.driver, env.decisions = driver_for(env)
        env.window = DeploymentWindow(deployment_id="coord-fixture", start=t0 + seconds(60), end=t0 + seconds(180))
        yield env


def build(env, **changes):
    options = dict(mode="rehearsal", profile=env.profile, evidence=env.evidence, driver=env.driver,
        implementation_verifier=env.review, adapters={"upbit": env.adapter}, account_source=env.producer,
        account_prefetch=env.producer.prefetch, trusted_head=env.head, quote_source=env.books, window=env.window,
        bar_seconds=60, monitor_until=env.t0 + seconds(200), clock=env.fake.clock, monitor_seconds=20,
        prefetch_lead_seconds=3, wait=env.fake.wait)
    return Coordinator(**(options | changes))


def observe_at(env, c, *offsets):
    """status() snapshots taken by hooks at t0 + offset seconds (in timer waits, between units)."""
    seen = {}
    for offset in offsets:
        env.fake.at(env.t0 + seconds(offset), lambda offset=offset: seen.__setitem__(offset, c.status()))
    return seen


def venue_order(cid, *, filled, status):
    return order(side="sell", quantity=D("0.0001"), filled=filled, price=PRICE, oid="dry-" + cid, client=cid,
                 status=status)


def venue_result(cid, *, status, filled):
    return AdapterResult(status=status, code="fixture", client_id=cid, venue_order_id="dry-" + cid,
                         filled_quantity=filled)


# -- acceptance cases owned by the coordinator row --------------------------------------------------------------

def test_partial_fill_reconciles_residual_without_second_create():
    with fixture() as env:
        c = build(env)
        seen = observe_at(env, c, 110, 130)

        def venue_fills_half():
            tick = c.status().last_tick
            assert tick.status == "submitted" and tick.order_status == "ACKNOWLEDGED", tick
            cid, p = tick.client_id, env.producer
            p.fills += (fill(side="sell", quantity=D("0.00005"), price=PRICE, fee=D("0"), order="dry-" + cid,
                             fid="part-1", at=env.fake.now),)
            p.orders += (venue_order(cid, filled=D("0.00005"), status="partial"),)
            p.cash, p.units = D("905000"), D("0.00095")
            env.adapter.results.append(venue_result(cid, status="partial", filled=D("0.00005")))
        env.fake.at(env.t0 + seconds(70), venue_fills_half)
        c.run()
        (state,) = seen[110].orders
        assert state.status == "PARTIAL" and state.filled_quantity == D("0.00005"), state
        tick = seen[130].last_tick
        assert tick.status == "existing" and tick.order_status == "PARTIAL", tick
        assert len(creates(env)) == 1


def test_cancel_acknowledgement_is_not_confirmed_cancellation():
    with fixture() as env:
        c = build(env)
        seen, marks = observe_at(env, c, 130, 150), {}

        def operator_cancels_then_prepares():
            cid = c.status().last_tick.client_id
            marks["cancel"] = state = c.cancel(cid)
            assert state.status in ("ACKNOWLEDGED", "CANCEL_REQUESTED"), state
            assert [r.operation for r in env.adapter.requests if r.operation == "cancel"] == ["cancel"]
            env.signal[0] = Signal(signal_id="entry-1", action="entry", quantity=D("0.0001"), limit_price=PRICE)
            plan, inputs, seed = selected(env.fake.now)
            marks["prepared"] = c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed)
        env.fake.at(env.t0 + seconds(100), operator_cancels_then_prepares)

        def venue_confirms_cancellation():
            cid = marks["cancel"].client_id
            env.producer.orders += (venue_order(cid, filled=D("0"), status="canceled"),)
            env.adapter.results.append(venue_result(cid, status="canceled", filled=D("0")))
        env.fake.at(env.t0 + seconds(135), venue_confirms_cancellation)
        env.fake.at(env.t0 + seconds(155), lambda: env.signal.__setitem__(0, HOLD))
        c.run()
        assert seen[130].last_tick.reasons == ("RUNNER_OUTSTANDING_ORDERS",), seen[130].last_tick
        assert seen[130].orders[0].status in ("ACKNOWLEDGED", "CANCEL_REQUESTED")
        assert marks["prepared"].session_id and c.status().orders[0].status == "CANCELED"
        assert [r.operation for r in env.adapter.requests if r.operation == "cancel"] == ["cancel"]
        assert len(creates(env)) == 1


def test_unknown_create_is_reconciled_never_retried():
    with fixture() as env:
        env.adapter.results.append(TimeoutError("private-wire-detail"))
        c = build(env)
        seen = observe_at(env, c, 70, 130, 150, 190)

        def venue_lists_it_open():
            cid = seen[70].last_tick.client_id
            env.producer.orders += (venue_order(cid, filled=D("0"), status="open"),)
            env.adapter.results.append(venue_result(cid, status="open", filled=D("0")))
        env.fake.at(env.t0 + seconds(135), venue_lists_it_open)
        c.run()
        assert seen[70].last_tick.order_status == "UNKNOWN", seen[70].last_tick
        assert (seen[130].last_tick.status, seen[130].last_tick.order_status) == ("existing", "UNKNOWN")
        assert seen[150].orders[0].status == "ACKNOWLEDGED", seen[150].orders
        assert (seen[190].last_tick.status, seen[190].last_tick.order_status) == ("existing", "ACKNOWLEDGED")
        assert len(creates(env)) == 1 and "private-wire-detail" not in repr(c.status())


def test_restart_restores_chain_and_journal_and_demands_fresh_preparation():
    with fixture() as env:
        a = build(env)
        env.fake.at(env.t0 + seconds(70), a.close)
        a.run()
        tick, status = a.status().last_tick, a.status()
        assert tick.status == "submitted" and tick.order_status == "ACKNOWLEDGED" and status.phase == "closed"
        cid, last_head, before = tick.client_id, env.head.commits[-1][1], len(env.producer.states)
        env.producer.orders += (venue_order(cid, filled=D("0"), status="open"),)
        adapter = DryRunAdapter(upbit, results=(venue_result(cid, status="open", filled=D("0")),))
        env.signal[0] = Signal(signal_id="entry-2", action="entry", quantity=D("0.0001"), limit_price=PRICE)
        b = build(env, adapters={"upbit": adapter})
        seen, prepared = observe_at(env, b, 130, 190), []

        def prepare_b():
            plan, inputs, seed = selected(env.fake.now)
            prepared.append(b.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed))
        env.fake.at(env.t0 + seconds(150), prepare_b)
        b.run()
        first, second = env.producer.states[before], env.producer.states[before + 1]
        assert first.state_digest == last_head
        assert second.previous_state_digest == last_head and second.sequence == first.sequence + 1
        assert adapter.requests[0].operation == "status" and seen[130].orders[0].status == "ACKNOWLEDGED"
        assert seen[130].last_tick.reasons == ("RUNNER_ACTUAL_PREPARED_SESSION_REQUIRED",), seen[130].last_tick
        assert seen[190].last_tick.reasons == ("RUNNER_OUTSTANDING_ORDERS",), seen[190].last_tick
        assert b._controller.session_provider(prepared[0].session_id) is b._launch.prepared
        assert len(creates(env)) + len([r for r in adapter.requests if r.operation == "create"]) == 1


def test_restart_after_commit_without_head_advance_refuses():
    with fixture() as env:
        a = build(env)
        env.fake.at(env.t0 + seconds(30), lambda: setattr(env.head, "fail_next", True))
        seen = observe_at(env, a, 50)
        env.fake.at(env.t0 + seconds(90), a.close)
        a.run()
        assert seen[50].account_source == "BASELINE_TRUSTED_HEAD_UPDATE_FAILED", seen[50]
        assert a.status().account_source == "COORDINATOR_CHECKPOINT_REFUSED"
        assert a.status().reasons == ("COORDINATOR_CHECKPOINT_REFUSED",)
        assert env.decisions == [] and env.adapter.requests == [] and len(env.head.commits) == 2
        calls = len(env.producer.calls)
        with patch.object(CheckpointStore, "seed", side_effect=AssertionError("reseed")):
            b = build(env)
            env.fake.at(env.fake.now + seconds(60), b.close)
            status = b.run()
        assert status.account_source == "COORDINATOR_CHECKPOINT_REFUSED" and status.published_units == 0
        assert len(env.producer.calls) == calls and env.decisions == [] and env.adapter.requests == []


def test_one_frame_per_unit_advances_head_once_and_decisions_deduplicate():
    with fixture() as env:
        c = build(env)
        marks, seen = {}, observe_at(env, c, 70, 130, 190)
        env.fake.at(env.t0 + seconds(50), lambda: marks.update(reads=env.head.reads, commits=len(env.head.commits)))
        env.fake.at(env.t0 + seconds(70), lambda: marks.update(reads_after=env.head.reads,
                                                               commits_after=len(env.head.commits)))
        env.fake.at(env.t0 + seconds(195), lambda: marks.update(repeat=c.submit_exit(EXIT)))
        status = c.run()
        # Between the two marks the slot unit (prefetch, publish, observe, reconcile, observations, reserve and
        # dispatch all redeliver the one frame) and one monitor unit ran: two commits, many reads.
        assert marks["commits_after"] - marks["commits"] == 2
        assert marks["reads_after"] - marks["reads"] >= (1 + 2 * 5) + (1 + 2 * 2)
        assert len(env.head.commits) == status.published_units
        assert all(env.head.commits[i][1] == env.head.commits[i + 1][0] for i in range(len(env.head.commits) - 1))
        assert seen[70].last_tick.status == "submitted"
        assert [seen[t].last_tick.status for t in (130, 190)] == ["existing"] * 2
        assert len(env.decisions) == 3 and len(creates(env)) == 1
        assert marks["repeat"].status == "ACKNOWLEDGED" and len(creates(env)) == 1


def test_explicit_exit_after_stop_is_sent_once():
    with fixture() as env:
        c = build(env, monitor_until=env.t0 + seconds(300))
        env.fake.at(env.t0 + seconds(30), c.stop)
        manual, sent = Signal(signal_id="manual-exit", action="exit", quantity=D("0.0001"), limit_price=PRICE), []
        env.fake.at(env.t0 + seconds(100), lambda: sent.append(c.submit_exit(manual)))
        env.fake.at(env.t0 + seconds(150), lambda: sent.append(c.submit_exit(manual)))
        status = c.run()
        assert sent[0].status == "ACKNOWLEDGED" and sent[1] == sent[0] and len(creates(env)) == 1
        assert env.decisions == [] and status.strategy_stopped and status.phase == "closed"
        assert sum(1 for when in env.producer.calls if when > env.t0 + seconds(30)) > 12
        assert status.missed_slots == 0 and status.orders[0].status == "ACKNOWLEDGED"


def test_close_while_awaiting_timer_returns_promptly():
    with fixture() as env:
        c = build(env, clock=lambda: env.t0, wait=threading.Event.wait)
        worker = threading.Thread(target=c.run, name="coordinator-run", daemon=True)
        worker.start()
        deadline = time.monotonic() + 20
        while c.status().published_units < 1 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert c.status().published_units == 1
        started = time.monotonic()
        assert c.close(timeout=2.0) is True
        worker.join(1.5)
        assert not worker.is_alive() and time.monotonic() - started < 1.5
        assert env.adapter.requests == [] and c.status().phase == "closed"
    with fixture() as env:
        c = build(env)
        marks = {}
        env.fake.at(env.t0 + seconds(50), lambda: marks.update(commits=len(env.head.commits)))
        env.fake.at(env.t0 + seconds(58), lambda: (marks.update(prefetches=len(env.producer.prefetches)), c.stop()))
        env.fake.at(env.t0 + seconds(70), lambda: marks.update(commits_after=len(env.head.commits)))
        status = c.run()
        assert marks["prefetches"] == 4                      # startup, two monitors and the abandoned slot unit
        assert marks["commits_after"] - marks["commits"] == 1  # the monitor at t0 + 60 only
        assert env.decisions == [] and creates(env) == [] and status.strategy_stopped
        assert sum(1 for when in env.producer.calls if when > env.t0 + seconds(60)) > 5


def test_close_while_provider_hangs_is_bounded_and_commits_nothing():
    with fixture() as env:
        entered, release = threading.Event(), threading.Event()
        env.producer.block = (entered, release)            # the second prefetch: the first monitor unit
        c = build(env)
        worker = threading.Thread(target=c.run, name="coordinator-run", daemon=True)
        worker.start()
        assert entered.wait(20)
        commits = len(env.head.commits)
        assert c.close(timeout=0.1) is False and c.status().in_flight == "account_source"
        release.set()
        worker.join(20)
        assert not worker.is_alive()
        status = c.status()
        assert len(env.head.commits) == commits == 1 and status.last_tick is None and status.phase == "closed"
        assert status.published_units == 1 and env.adapter.requests == [] and status.in_flight == ""


def test_suspend_resume_skips_slots_reconciles_first_and_never_sends_late():
    with fixture() as env:
        c = build(env)
        env.fake.at(env.t0 + seconds(50), lambda: setattr(env.fake, "now", env.fake.now + seconds(120)))
        status = c.run()
        assert status.missed_slots == 2
        assert env.t0 + seconds(170) <= status.data_gap_at < env.t0 + seconds(177)
        gap = [when for when in env.producer.calls if env.t0 + seconds(170) <= when < env.t0 + seconds(177)]
        assert gap and gap[0] < env.decisions[0].now
        slots = [env.t0 + seconds(180)]
        assert len(env.decisions) == 1
        assert all(slot <= d.now <= slot + seconds(10) for slot, d in zip(slots, env.decisions))
        assert len(creates(env)) == 1 and env.producer.calls[-1] > slots[-1]


def test_mid_unit_suspend_refuses_the_slot_without_publishing():
    """A 15 s suspend inside slot 1's unit, during the account capture (which follows the book read and may end
    inside the slot window) or during the book read itself: the slot is refused by its window, nothing is
    published or committed for it, the book was read at the prefetch lead, and the next slots run."""
    for step in ("account", "book"):
        with fixture() as env:
            c = build(env)
            if step == "book":
                env.books.jump_once = 15
            else:
                env.fake.at(env.t0 + seconds(56), lambda: setattr(env.producer, "jump_once", 15))
            marks, seen = {}, observe_at(env, c, 75)
            env.fake.at(env.t0 + seconds(50), lambda: marks.update(commits=len(env.head.commits),
                                                                   calls=len(env.producer.calls)))
            env.fake.at(env.t0 + seconds(75), lambda: marks.update(commits_after=len(env.head.commits),
                                                                   calls_after=len(env.producer.calls)))
            c.run()
            assert seen[75].reasons == ("COORDINATOR_SLOT_WINDOW_MISSED",), (step, seen[75])
            assert seen[75].account_source == "" and seen[75].published_units == 4     # startup, three monitors
            assert env.t0 + seconds(57) <= env.books.received[0] < env.t0 + seconds(58), (step, env.books.received)
            assert marks["commits_after"] - marks["commits"] == 1 and marks["calls_after"] - marks["calls"] == 1
            assert all(d.now >= env.t0 + seconds(120) for d in env.decisions) and len(env.decisions) == 2
            assert len(creates(env)) == 1 and env.books.reads == 3


def test_long_suspend_stops_the_account_chain_without_a_tick():
    with fixture() as env:
        c = build(env, monitor_until=env.t0 + seconds(900))
        env.fake.at(env.t0 + seconds(50), lambda: setattr(env.fake, "now", env.fake.now + seconds(600)))
        seen = observe_at(env, c, 700)
        status = c.run()
        assert status.missed_slots == 3 and seen[700].account_source == "BASELINE_BRIDGE_EVIDENCE_REFUSED"
        assert status.account_source == "BASELINE_BRIDGE_EVIDENCE_REFUSED" and status.new_entry_blocked
        assert len(env.head.commits) == 3 and env.decisions == [] and env.adapter.requests == []
        assert sum(1 for when in env.producer.calls if when > env.t0 + seconds(600)) >= 10


# -- row contract tests ----------------------------------------------------------------------------------------

def test_cutoff_is_monitored_after_strategy_stop():
    with fixture(now=CUTOFF_NOW, cutoff=79200) as env:
        env.signal[0] = HOLD
        env.producer.latency = 3                          # the boundary capture spans 22:00:00
        b = env.t0 + seconds(120)
        window = DeploymentWindow(deployment_id="coord-cutoff", start=env.t0 + seconds(20), end=env.t0 + seconds(80))
        refused(lambda: build(env, window=window, monitor_until=env.t0 + seconds(100), monitor_seconds=10),
                "COORDINATOR_MONITOR_ENDS_BEFORE_CUTOFF")
        c = build(env, window=window, monitor_until=env.t0 + seconds(150), monitor_seconds=10,
                  boundary_lead_seconds=2, prefetch_lead_seconds=5)     # slots: book before the slot; boundary: spanned
        env.fake.at(env.t0 + seconds(90), c.stop)
        status = c.run()
        assert any(b - seconds(2) <= when <= b - seconds(1) for when, _ in env.producer.prefetches)
        boundary = [state for state in env.producer.states if state.asof == b]
        assert boundary and boundary[0].recovery_checkpoint.cutoff_at == b
        assert boundary[0].recovery_checkpoint.equity_krw == EQUITY
        assert status.recovery_status == "satisfied" and status.recovery_deadline == b and status.strategy_stopped
        assert status.missed_boundaries == 0 and any(when > env.t0 + seconds(90) for when in env.producer.calls)
        assert status.last_tick.status == "hold" and len(env.decisions) == 2 and status.phase == "closed"


def test_suspend_across_cutoff_never_fabricates_a_boundary():
    b = CUTOFF_NOW + seconds(120)
    for crossing, code in ((False, "COORDINATOR_ACCOUNT_SOURCE_FAILED"), (True, "BASELINE_BRIDGE_EVIDENCE_REFUSED")):
        with fixture(now=CUTOFF_NOW, cutoff=79200) as env:
            env.signal[0], env.producer.crossing = HOLD, crossing
            window = DeploymentWindow(deployment_id="coord-cutoff", start=env.t0 + seconds(20),
                                      end=env.t0 + seconds(80))
            c = build(env, window=window, monitor_until=env.t0 + seconds(210), monitor_seconds=10,
                      boundary_lead_seconds=2)
            env.fake.at(env.t0 + seconds(110), lambda: setattr(env.fake, "now", env.fake.now + seconds(60)))
            seen = observe_at(env, c, 175)
            status = c.run()
            assert status.missed_boundaries == 1 and seen[175].account_source == code, seen[175]
            assert status.account_source == code and "ACCOUNT-SECRET-77" not in repr(status)
            assert not any(state.asof == b for state in env.producer.states)
            assert status.recovery_status != "satisfied" and status.new_entry_blocked


def test_construction_is_inert_and_mode_is_explicit():
    with fixture() as env:
        def listing():
            return sorted(p.relative_to(env.home).as_posix() for p in env.home.rglob("*"))
        before, threads = listing(), threading.active_count()
        c = build(env)
        assert listing() == before and threading.active_count() == threads
        assert env.fake.reads == 0 and env.producer.calls == [] and env.producer.prefetches == []
        assert env.books.reads == 0 and env.head.reads == 0
        for mode in (None, "observe", "controlled"):
            refused(lambda mode=mode: build(env, mode=mode), "COORDINATOR_MODE_UNSUPPORTED")
        refused(lambda: build(env, profile=replace(env.profile, quote_currency="USD")), "COORDINATOR_VENUE_UNSUPPORTED")
        for change in (dict(clock=None), dict(quote_source=object()), dict(trusted_head=object()),
                       dict(history=object()), dict(evidence=None), dict(account_prefetch=7), dict(wait=None)):
            refused(lambda change=change: build(env, **change), "COORDINATOR_INTEGRATIONS_REQUIRED")
        refused(lambda: build(env, adapters={"upbit": object()}), "RUNNER_REHEARSAL_REQUIRES_DRY_ADAPTERS")
        for until in (env.window.end - seconds(1), env.window.end + timedelta(days=1, seconds=1)):
            refused(lambda until=until: build(env, monitor_until=until), "COORDINATOR_MONITOR_SPAN_UNSUPPORTED")
        for change in (dict(bar_seconds=7), dict(prefetch_lead_seconds=9), dict(monitor_seconds=4),
                       dict(boundary_lead_seconds=0), dict(monitor_seconds=20.0), dict(monitor_until=None)):
            refused(lambda change=change: build(env, **change), "COORDINATOR_SCHEDULE_INVALID")
        for change in (dict(bar_seconds=50), dict(window=replace(env.window, end=env.window.start)),
                       dict(window=object())):
            refused(lambda change=change: build(env, **change), "COORDINATOR_WINDOW_INVALID")
        c.close()
        assert c.run().phase == "closed" and env.producer.calls == []
        refused(c.run, "COORDINATOR_ALREADY_RUN")
        plan, inputs, seed = selected(env.t0)
        stopped = build(env)
        stopped.stop()
        refused(lambda: stopped.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed),
                "COORDINATOR_STOPPED")
        refused(lambda: build(env).prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed),
                "COORDINATOR_PREPARATION_ACCOUNT_NOT_CURRENT")
        assert listing() == before and env.adapter.requests == []


def test_fixed_driver_requires_history_and_its_window():
    e = LD.fixture()
    fake = FakeTime(e.window.start - seconds(60))
    options = dict(mode="rehearsal", profile=e.profile, evidence=EvidencePackage(protocol=e.protocol, result=None),
        driver=e.driver, implementation_verifier=lambda binding, driver: None, adapters={"upbit": DryRunAdapter(upbit)},
        account_source=lambda previous, now: None, trusted_head=Head("0" * 64), quote_source=Books(fake),
        window=e.window, bar_seconds=60, monitor_until=e.window.end, clock=fake.clock, wait=fake.wait)
    refused(lambda: Coordinator(**options), "COORDINATOR_HISTORY_REQUIRED")
    history = SimpleNamespace(record_slot=lambda book, account: None)
    shifted = replace(e.window, start=e.window.start + seconds(60), end=e.window.end + seconds(60))
    refused(lambda: Coordinator(**(options | dict(history=history, window=shifted))),
            "COORDINATOR_WINDOW_BINDING_MISMATCH")
    refused(lambda: Coordinator(**(options | dict(history=history, bar_seconds=120))),
            "COORDINATOR_WINDOW_BINDING_MISMATCH")
    other = LD.construct(e)
    object.__setattr__(other, "callback", lambda *args: None)
    refused(lambda: Coordinator(**(options | dict(history=history, driver=other))), "FIXED_DRIVER_CALLBACK_CHANGED")
    assert fake.reads == 0


def test_status_is_sanitized():
    with fixture() as env:
        env.adapter.results.append(TimeoutError("private-wire-detail"))
        c = build(env)
        errors = []

        def unknown_order():
            try:
                c.cancel("x")
            except CoordinatorError as exc:
                errors.append(exc)
        env.fake.at(env.t0 + seconds(30), unknown_order)

        def poison_the_producer():
            env.producer.fail = RuntimeError("ACCOUNT-SECRET-77 /c/Users/x")
            try:
                c.cancel("y")
            except CoordinatorError as exc:
                errors.append(exc)
        env.fake.at(env.t0 + seconds(70), poison_the_producer)
        status = c.run()
        assert [str(exc) for exc in errors] == ["RUNNER_ORDER_SCOPE_MISMATCH", "COORDINATOR_ACCOUNT_SOURCE_FAILED"]
        assert all(exc.__cause__ is None and exc.__suppress_context__ for exc in errors)
        assert status.account_source == "COORDINATOR_ACCOUNT_SOURCE_FAILED"
        assert status.reasons == ("COORDINATOR_ACCOUNT_SOURCE_FAILED",) and status.new_entry_blocked
        assert status.last_tick.order_status == "UNKNOWN" and status.orders[0].status == "UNKNOWN"
        text = repr(status)
        for secret in ("ACCOUNT-SECRET-77", "private-wire-detail", "/c/Users", SCOPE, "1000000", "900000", "HEAD-SECRET"):
            assert secret not in text, secret
        for code in (*status.reasons, *status.risk_reasons, status.account_source):
            assert C._CODE.fullmatch(code) is not None, code


def test_coordinator_source_static_contract():
    source = (ROOT / MODULE).read_bytes()
    source.decode("ascii")
    text = source.decode("utf-8")
    assert problems(text, MODULE) == [], problems(text, MODULE)
    tree = ast.parse(text)
    names = ({node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
             | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)})
    assert not names & {"Thread", "sleep", "signal", "atexit", "environ", "compare_and_set", "initialize_reviewed_head"}
    for node in tree.body:
        assert isinstance(node, (ast.Expr, ast.Import, ast.ImportFrom, ast.Assign, ast.FunctionDef, ast.ClassDef)), node
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            assert not any(m.startswith(("execution_accounts.quotes", "execution.transport",
                                         "execution_orders.transport", "execution_orders.upbit")) for m in modules), modules
    assert isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant)
    assert not any(isinstance(node, ast.Expr) for node in tree.body[1:])
    # K9: compose reaches the loader through workflow's public aliases; neither module is a fixed-driver source.
    from execution_launch import driver as fixed, workflow as W
    assert W.read_file is W._read_file and W.artifact is W._artifact
    assert MODULE not in fixed._SOURCE_FILES and "execution_launch/workflow.py" not in fixed._SOURCE_FILES
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "execution_launch.workflow":
            assert not any(alias.name.startswith("_") for alias in node.names), [alias.name for alias in node.names]
    assert "CoordinatorStatus" in text and "Controller's order states" in ast.get_docstring(
        next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "CoordinatorStatus"))
    # K11: every read and write of `_started` in run() and close() sits under the status lock (test-and-set).
    coordinator = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Coordinator")
    for name in ("run", "close"):
        function = next(node for node in coordinator.body if isinstance(node, ast.FunctionDef) and node.name == name)
        locked = {id(inner) for node in ast.walk(function) if isinstance(node, ast.With)
                  and [ast.unparse(item.context_expr) for item in node.items] == ["self._status_lock"]
                  for inner in ast.walk(node)}
        uses = [node for node in ast.walk(function) if isinstance(node, ast.Attribute) and node.attr == "_started"]
        assert uses and all(id(node) in locked for node in uses), (name, len(uses))


# -- K11: the refusal codes no test named, the timer's clock and the gate stage --------------------------------

def test_untested_refusal_codes_publish_no_frame():
    """K11: COORDINATOR_ACCOUNT_FRAME_INVALID (a non-frame, or a frame ending after the unit time),
    COORDINATOR_STARTUP_RECONCILE_REQUIRED (a slot before the first successful observe: carried in `reasons`, never
    in `account_source`, and refused before the book is read), COORDINATOR_NO_PUBLISHED_TICK (the board outside a
    unit) and COORDINATOR_CLOCK_ROLLBACK (a unit time earlier than the previous unit's): none publishes a frame,
    commits a checkpoint or reaches the driver."""
    for invalid in (lambda previous, now: "not-a-frame",
                    lambda previous, now: env.producer(previous, now + seconds(1))):
        with fixture() as env:
            c = build(env, account_source=invalid)
            seen = observe_at(env, c, 58, 75)
            env.fake.at(env.t0 + seconds(30),
                        lambda: refused(lambda: c._board.quote(env.fake.now), "COORDINATOR_NO_PUBLISHED_TICK"))
            status = c.run()
            assert status.account_source == "COORDINATOR_ACCOUNT_FRAME_INVALID" and status.published_units == 0
            assert seen[58].reasons == ("COORDINATOR_STARTUP_RECONCILE_REQUIRED",), seen[58]
            assert seen[58].account_source == "COORDINATOR_ACCOUNT_FRAME_INVALID", seen[58]   # the gate: no account step
            assert seen[75].reasons == ("COORDINATOR_STARTUP_RECONCILE_REQUIRED",) and status.new_entry_blocked
            assert env.books.reads == 0 and env.head.commits == [] and env.decisions == [] and env.adapter.requests == []
            assert len(env.producer.prefetches) == 11                       # startup and ten monitors, never a slot
            refused(lambda: c._board.quote(env.fake.now), "COORDINATOR_NO_PUBLISHED_TICK")
            refused(lambda: c._board.account_frame(env.state, env.fake.now), "COORDINATOR_NO_PUBLISHED_TICK")
    with fixture() as env:
        c = build(env)
        marks, seen = {}, observe_at(env, c, 82)
        env.fake.at(env.t0 + seconds(70), lambda: (marks.update(published=c.status().published_units),
                                                   setattr(env.producer, "latency", -30)))   # the monitor at 80 reads 50
        env.fake.at(env.t0 + seconds(85), lambda: setattr(env.producer, "latency", 0))
        status = c.run()
        assert seen[82].account_source == "COORDINATOR_CLOCK_ROLLBACK", seen[82]
        assert seen[82].published_units == marks["published"] == 5          # startup, three monitors, one slot
        assert status.account_source == "" and status.published_units == len(env.head.commits)
        assert len(env.decisions) == 3 and len(creates(env)) == 1 and status.reasons == ()


def test_timer_clock_failure_is_a_fixed_code():
    """K11: a clock that raises while the timer waits ends run() with COORDINATOR_CLOCK_INVALID from the
    coordinator's own clock wrapper, never the raw exception or its text; the finally still closes the run."""
    with fixture() as env:
        def clock():
            if env.fake.now >= env.t0 + seconds(5):
                raise RuntimeError("CLOCK-SECRET /c/Users/x")
            return env.fake.clock()
        c = build(env, clock=clock)
        exc = refused(c.run, "COORDINATOR_CLOCK_INVALID")
        assert exc.__cause__ is None and exc.__suppress_context__ and "CLOCK-SECRET" not in repr(exc)
        assert c.status().phase == "closed" and c.status().published_units == 1 and env.decisions == []


# -- ruling R8: the timing budget, the schedule and the timer -----------------------------------------------------

def test_timing_budget_fits_slot_and_account_windows_at_worst_case_latency():
    """The slot envelope at prefetch lead 3 s with a book stamped one second before its receipt (R12): the book
    is read at slot - 3 s, then the account capture runs and may end inside [slot, slot + 10 s]. A capture of
    8.5 s (lead + 5.5 s) holds the slot: sampled, recorded and ticked at slot + 5.5 s, the book 8.5 s old at
    sampling (its stamp 9.5 s, inside the 10 s quote bound), the account as old as the capture's end. A capture of
    9.5 s refuses the slot through the quote bound (the stamp is 10.5 s old: QUOTE_BOOK_STALE_OR_FUTURE); one of
    14 s leaves the window (slot + 11 s: COORDINATOR_SLOT_WINDOW_MISSED). A refused slot publishes nothing and
    monitoring continues."""
    with fixture() as env:
        recorded = []
        history = SimpleNamespace(record_slot=lambda book, account: recorded.append(
            (env.fake.now, account.asof, book.received_at)))
        c = build(env, history=history)
        for offset, latency in ((50, 8.5), (100, 9.5), (160, 14)):
            env.fake.at(env.t0 + seconds(offset), lambda latency=latency: setattr(env.producer, "latency", latency))
        seen = observe_at(env, c, 75, 135)
        status = c.run()
        slot = env.t0 + seconds(60)
        ((sampled_at, asof, received),) = recorded
        assert slot - seconds(3) <= received < slot - seconds(2.9), received          # the book: read at the lead
        assert slot + seconds(5.5) <= sampled_at < slot + seconds(5.6), sampled_at    # the capture ended in the window
        assert slot + seconds(5.5) <= asof <= sampled_at and sampled_at - asof < seconds(0.1), asof
        (decision,) = env.decisions
        assert slot + seconds(5.5) <= decision.now <= slot + seconds(10)
        assert seconds(0) <= decision.now - decision.account.asof <= seconds(30)
        assert seconds(9.5) <= decision.now - decision.quote.asof <= seconds(10), decision.quote.asof
        assert decision.account.asof == asof and seen[75].last_tick.status == "submitted"
        assert seen[135].reasons == ("QUOTE_BOOK_STALE_OR_FUTURE",), seen[135]      # 9.5 s: the stamp is 10.5 s old
        assert status.reasons == ("COORDINATOR_SLOT_WINDOW_MISSED",), status        # 14 s: slot + 11 s
        assert all(seen[t].account_source == "" for t in (75, 135)) and status.account_source == ""
        assert len(creates(env)) == 1 and len(recorded) == 1 and len(env.decisions) == 1
        assert status.missed_slots == 0 and status.published_units == len(env.head.commits)
    with fixture() as env:
        env.producer.latency = 30                         # the collector's worst case: every slot is lost, the chain lives
        status = build(env).run()
        assert status.missed_slots == 3 and status.account_source == "" and status.data_gap_at is not None
        assert env.decisions == [] and env.adapter.requests == [] and env.books.reads == 0
        assert len(env.head.commits) == status.published_units >= 6


def test_a_book_received_after_the_slot_is_refused_without_a_record_or_a_decision():
    """R12: a quote read that takes longer than the prefetch lead (4 s at lead 3) delivers the book about 1 s
    after the slot. sample_prefetched_book still binds in the new order: every slot is refused with
    CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT in `reasons` only (a quote-stage failure never sets account_source or
    flips new_entry_blocked), nothing is recorded, decided or sent, and the account chain keeps publishing."""
    with fixture() as env:
        recorded = []
        env.books.delay = 4
        c = build(env, history=SimpleNamespace(record_slot=lambda book, account: recorded.append(book)))
        seen = observe_at(env, c, 50, 75)
        status = c.run()
        slot = env.window.start
        assert slot + seconds(1) <= env.books.received[0] < slot + seconds(1.1), env.books.received
        assert seen[75].reasons == status.reasons == ("CAPTURE_BOOK_NOT_AVAILABLE_AT_SLOT",), seen[75]
        assert seen[75].account_source == status.account_source == ""
        assert seen[75].new_entry_blocked == seen[50].new_entry_blocked and seen[75].last_tick is None
        assert recorded == [] and env.decisions == [] and env.adapter.requests == [] and env.books.reads == 3
        assert status.missed_slots == 0 and status.published_units == len(env.head.commits) == 11
        assert len(env.producer.prefetches) == 14                        # startup, ten monitors, three slot captures


def test_schedule_and_timer_order_skip_and_cancel():
    start = datetime(2026, 10, 24, 21, 59, 50, tzinfo=KST)
    window = DeploymentWindow(deployment_id="timer", start=start + seconds(10), end=start + seconds(130))
    items = list(schedule(window=window, bar_seconds=60, start=start, monitor_until=start + seconds(140),
                          monitor_seconds=10, prefetch_lead_seconds=3, boundary_lead_seconds=3, cutoff_seconds=79200))
    offsets = [(due.kind, (due.at - start).total_seconds()) for due in items]
    assert offsets[:3] == [("boundary", 7.0), ("slot", 7.0), ("monitor", 10.0)]     # equal start: boundary, slot, monitor
    tied = [(due.kind, (due.at - start).total_seconds()) for due in schedule(window=window, bar_seconds=60,
            start=start, monitor_until=start + seconds(140), monitor_seconds=10, prefetch_lead_seconds=10,
            boundary_lead_seconds=3, cutoff_seconds=79200)]
    assert tied.index(("slot", 60.0)) == tied.index(("monitor", 60.0)) - 1           # equal start: slot before monitor
    assert [due.slot for due in items if due.kind == "boundary"] == [start + seconds(10)]   # 22:00:00 KST only
    assert all(due.deadline == due.slot for due in items if due.kind != "monitor")
    assert all(due.deadline == due.at + seconds(10) for due in items if due.kind == "monitor")
    assert len([due for due in items if due.kind == "slot"]) == 3 and items[-1].at == start + seconds(140)
    late = list(schedule(window=window, bar_seconds=60, start=start + seconds(65), monitor_until=start + seconds(140),
                         monitor_seconds=10, prefetch_lead_seconds=3, boundary_lead_seconds=2, cutoff_seconds=None))
    assert [due.slot for due in late if due.kind == "slot"] == [start + seconds(70), start + seconds(130)]
    assert not [due for due in late if due.kind == "boundary"]
    night = datetime(2026, 10, 24, 23, 59, tzinfo=KST)
    midnight = list(schedule(window=replace(window, start=night, end=night + seconds(120)), bar_seconds=60, start=night,
                             monitor_until=night + seconds(300), monitor_seconds=20, prefetch_lead_seconds=3,
                             boundary_lead_seconds=2, cutoff_seconds=None))
    assert [due.slot for due in midnight if due.kind == "boundary"] == [datetime(2026, 10, 25, tzinfo=KST)]
    # R14: monitors sit on the slot grid (window.start + k * monitor_seconds), strictly after the run start.
    phased = list(schedule(window=window, bar_seconds=60, start=start + seconds(4), monitor_until=start + seconds(140),
                           monitor_seconds=10, prefetch_lead_seconds=3, boundary_lead_seconds=2, cutoff_seconds=None))
    grid = [(due.at - window.start).total_seconds() for due in phased if due.kind == "monitor"]
    assert grid == [10.0 * k for k in range(14)] and grid[0] == 0.0 and window.start > start + seconds(4)
    on_grid = [(due.at - window.start).total_seconds() for due in schedule(window=window, bar_seconds=60,
               start=window.start, monitor_until=start + seconds(140), monitor_seconds=10, prefetch_lead_seconds=3,
               boundary_lead_seconds=2, cutoff_seconds=None) if due.kind == "monitor"]
    assert on_grid[0] == 10.0                                       # a start on the grid: the next point, never itself
    cancel, fake = threading.Event(), FakeTime(start)
    timer = CancellableTimer(items, clock=fake.clock, cancel=cancel, wait=fake.wait)
    first = next(timer)
    assert first.kind == "boundary" and start + seconds(7) <= fake.now < start + seconds(8)
    assert next(timer).kind == "slot"
    fake.now = start + seconds(25)                                       # a suspend past two deadlines
    due = next(timer)
    assert (due.kind, due.at) == ("monitor", start + seconds(20)) and timer.missed == {"boundary": 0, "slot": 0, "monitor": 1}
    fake.now = start + seconds(75)
    assert next(timer).kind == "monitor" and timer.missed == {"boundary": 0, "slot": 1, "monitor": 5}
    cancel.set()
    try:
        next(timer)
    except StopIteration:
        pass
    else:
        raise AssertionError("a cancelled timer yielded an item")
    assert next(iter(CancellableTimer((), clock=fake.clock, cancel=threading.Event(), wait=fake.wait)), None) is None
    naive = CancellableTimer(items, clock=lambda: datetime(2026, 1, 1), cancel=threading.Event(), wait=fake.wait)
    refused(lambda: next(naive), "COORDINATOR_CLOCK_INVALID")


# -- rulings R13-R15: the boundary band, the monitor grid, the startup budget and the cutoff agreement ----------

def test_slots_near_a_boundary_are_refused_at_construction():
    """R13: construction refuses any slot within BOUNDARY_BAND (20 s) of a Seoul midnight or, with a recovery
    condition, of 22:00 KST, including a boundary just past the window's last slot; the boundary unit alone handles
    the boundary instant. A grid offset by 30 s (hh:mm:30 for 60 s bars) is accepted."""
    with fixture(now=CUTOFF_NOW, cutoff=79200) as env:            # t0 is 21:58:00 KST: 22:00 is a boundary
        until = env.t0 + seconds(400)

        def window(start, span=120):
            return DeploymentWindow(deployment_id="coord-band", start=env.t0 + seconds(start),
                                    end=env.t0 + seconds(start + span))
        for start in (60, 75, 100, 110):          # a slot on 22:00, 15 s after, 20 s before and 10 s before it
            refused(lambda start=start: build(env, window=window(start), monitor_until=until),
                    "COORDINATOR_SLOT_NEAR_BOUNDARY")
        refused(lambda: build(env, window=window(50, 60), monitor_until=until), "COORDINATOR_SLOT_NEAR_BOUNDARY")
        assert build(env, window=window(90), monitor_until=until).status().phase == "new"      # slots at :30
        assert build(env, window=window(30, 60), monitor_until=until).status().phase == "new"  # last slot 21:59:30
        # the band is inclusive at exactly 20 s on the slot grid too: with 20 s bars the last slot 21:59:40
        refused(lambda: build(env, window=window(60, 40), bar_seconds=20, monitor_seconds=10, monitor_until=until),
                "COORDINATOR_SLOT_NEAR_BOUNDARY")
        assert build(env, window=window(59, 40), bar_seconds=20, monitor_seconds=10,
                     monitor_until=until).status().phase == "new"                              # last slot 21:59:39
        assert env.fake.reads == 0 and env.head.reads == 0 and env.producer.prefetches == []
    with fixture(now=CUTOFF_NOW) as env:                           # no recovery condition: 22:00 is no boundary
        on_cutoff = DeploymentWindow(deployment_id="coord-band", start=env.t0 + seconds(60), end=env.t0 + seconds(180))
        assert build(env, window=on_cutoff, monitor_until=env.t0 + seconds(200)).status().phase == "new"
        midnight = datetime(2026, 10, 25, tzinfo=KST)
        for offset in (0, 10, -15):
            night = DeploymentWindow(deployment_id="coord-band", start=midnight + seconds(offset - 60),
                                     end=midnight + seconds(offset + 60))
            refused(lambda night=night: build(env, window=night, monitor_until=night.end + seconds(20)),
                    "COORDINATOR_SLOT_NEAR_BOUNDARY")
        before = DeploymentWindow(deployment_id="coord-band", start=midnight - seconds(130), end=midnight - seconds(10))
        refused(lambda: build(env, window=before, monitor_until=before.end + seconds(20)), "COORDINATOR_SLOT_NEAR_BOUNDARY")
        offset = DeploymentWindow(deployment_id="coord-band", start=midnight - seconds(30), end=midnight + seconds(90))
        assert build(env, window=offset, monitor_until=offset.end + seconds(20)).status().phase == "new"
        dawn = DeploymentWindow(deployment_id="coord-band", start=midnight + seconds(20), end=midnight + seconds(80))
        refused(lambda: build(env, window=dawn, monitor_until=dawn.end + seconds(20)), "COORDINATOR_SLOT_NEAR_BOUNDARY")
        later = replace(dawn, start=dawn.start + seconds(1), end=dawn.end + seconds(1))   # first slot 21 s past midnight
        assert build(env, window=later, monitor_until=later.end + seconds(20)).status().phase == "new"


def test_monitors_sit_on_the_slot_grid_so_the_reviews_bad_phases_hold_every_slot():
    """R14 (review RT-C): with monitors phased from the run start, a run started 4 s or 3.1 s before a 10 s grid
    point put a monitor's 2.2 s capture inside the slot's 3 s prefetch lead and lost every slot. Monitors now sit
    on window.start + k * monitor_seconds, strictly after the run start, so no monitor unit starts inside a lead."""
    for phase in (6, 6.9):
        with fixture() as env:
            env.fake.now = env.t0 - seconds(10 - phase)
            env.producer.latency = 2.2                    # the fixture's 11-read capture at the 0.2 s pace
            c = build(env, monitor_seconds=10)
            status = c.run()
            offsets = [round((when - env.window.start).total_seconds(), 1) for when, _ in env.producer.prefetches]
            assert offsets[0] == round(phase - 70, 1), offsets[0]                      # the startup unit
            monitors = [offset for offset in offsets[1:] if offset % 60 != 57.0]
            assert len(monitors) >= 20 and all(offset % 10 == 0 for offset in monitors), (phase, monitors)
            assert [offset for offset in offsets[1:] if offset % 60 == 57.0] == [-3.0, 57.0, 117.0], offsets
            slots = [env.t0 + seconds(60 * k) for k in (1, 2, 3)]
            assert len(env.decisions) == 3, [d.now for d in env.decisions]
            assert all(slot <= d.now <= slot + seconds(10) for slot, d in zip(slots, env.decisions))
            assert status.reasons == () and status.last_tick.status == "existing" and status.missed_slots == 0
            assert len(creates(env)) == 1 and status.account_source == ""


def test_late_start_and_knob_floors_are_refused_before_any_unit():
    """R14: run() refuses COORDINATOR_START_TOO_LATE, before any unit, when the first slot's prefetch comes less
    than STARTUP_BUDGET (15 s) after the start; a restart between slots with that budget runs, and a start after
    the last slot only monitors. Construction requires bar_seconds % monitor_seconds == 0 and
    monitor_seconds - prefetch_lead_seconds >= 5 (one monitor unit between a monitor and the next prefetch)."""
    with fixture() as env:
        c = build(env)
        env.fake.now = env.t0 + seconds(42.5)             # 14.5 s before the first prefetch at t0 + 57
        refused(c.run, "COORDINATOR_START_TOO_LATE")
        assert c.status().phase == "closed" and env.producer.prefetches == [] and env.producer.calls == []
        assert env.head.reads == 0 and env.books.reads == 0 and env.decisions == []
        refused(c.run, "COORDINATOR_ALREADY_RUN")
        env.fake.now = env.t0 + seconds(42)               # exactly the budget
        status = build(env).run()
        assert len(env.decisions) == 3 and status.reasons == () and status.missed_slots == 0
    with fixture() as env:
        env.fake.now = env.t0 + seconds(100)              # a restart between slots, 17 s before the next prefetch
        status = build(env).run()
        assert [d.now >= env.t0 + seconds(120) for d in env.decisions] == [True, True] and status.missed_slots == 0
        assert status.published_units == len(env.head.commits) and status.reasons == ()
    with fixture() as env:
        env.fake.now = env.t0 + seconds(185)              # after the last slot: monitoring only
        status = build(env).run()
        assert env.decisions == [] and env.books.reads == 0 and status.missed_slots == 0
        assert status.published_units == 2 and status.phase == "closed"
    with fixture() as env:
        for change in (dict(monitor_seconds=7), dict(monitor_seconds=10, prefetch_lead_seconds=6),
                       dict(bar_seconds=40, monitor_seconds=15), dict(monitor_seconds=8, prefetch_lead_seconds=4)):
            refused(lambda change=change: build(env, **change), "COORDINATOR_SCHEDULE_INVALID")
        for change in (dict(monitor_seconds=10, prefetch_lead_seconds=5), dict(monitor_seconds=15, prefetch_lead_seconds=8),
                       dict(monitor_seconds=12, prefetch_lead_seconds=7)):
            assert build(env, **change).status().phase == "new"


def test_cutoff_mismatch_is_refused_before_the_startup_unit():
    """R15: the chain's recovery_cutoff_seconds and the profile's recovery condition must be both set or both
    absent; otherwise run() refuses COORDINATOR_CUTOFF_MISMATCH before any unit. Construction stays inert."""
    for cutoff, chain_cutoff in ((None, 79200), (79200, None)):
        with fixture(now=CUTOFF_NOW, cutoff=cutoff, chain_cutoff=chain_cutoff) as env:
            window = DeploymentWindow(deployment_id="coord-cutoff", start=env.t0 + seconds(20), end=env.t0 + seconds(80))
            c = build(env, window=window, monitor_until=env.t0 + seconds(150), monitor_seconds=10)
            assert env.head.reads == 0
            refused(c.run, "COORDINATOR_CUTOFF_MISMATCH")
            assert c.status().phase == "closed" and env.producer.prefetches == [] and env.producer.calls == []
            assert env.head.commits == [] and env.books.reads == 0 and env.decisions == [] and env.head.reads == 1
    with fixture(now=CUTOFF_NOW, cutoff=79200) as env:                 # matched: the startup unit runs
        window = DeploymentWindow(deployment_id="coord-cutoff", start=env.t0 + seconds(20), end=env.t0 + seconds(80))
        c = build(env, window=window, monitor_until=env.t0 + seconds(150), monitor_seconds=10)
        env.fake.at(env.t0 + seconds(5), c.close)
        assert c.run().published_units == 1
    with fixture(now=CUTOFF_NOW, cutoff=79200, chain_cutoff=None) as env:   # the pre-start load fails once (a head
        window = DeploymentWindow(deployment_id="coord-cutoff", start=env.t0 + seconds(20), end=env.t0 + seconds(80))
        c = build(env, window=window, monitor_until=env.t0 + seconds(150), monitor_seconds=10)
        real = env.head.read                                                 # read error): every unit's own load

        def once():
            env.head.read = real
            raise RuntimeError("HEAD-SECRET")
        env.head.read = once                                                 # still enforces the agreement
        status = c.run()
        assert status.account_source == "COORDINATOR_CUTOFF_MISMATCH" and status.new_entry_blocked, status
        assert status.published_units == 0 and env.producer.prefetches == [] and env.head.commits == []
        assert env.decisions == [] and env.books.reads == 0 and status.phase == "closed"


# -- ruling R8: compose() and the real adapters over fake transports ---------------------------------------------

def reviewed(t0, window, *, cutoff=False):
    """The reviewed artifacts for one window: a moving-average program over the installed program.py, a profile
    bound to the interval fixture's account with its 100090 KRW anchor cash (with the 22:00 recovery condition
    when `cutoff`, matching the interval fixture's chain), a minute-bar prospective capture that qualifies, the
    unsigned request and a review document signed by the fixture owner key (K1) over the real D14 hash and the
    actual fixed-driver identity."""
    artifact = (ROOT / "execution_launch" / "program.py").read_bytes()
    spec = ProgramSpec(schema_version=1, strategy_id="test-strategy", kind="moving_average_trend", fast_window=2,
                       slow_window=3, exposure_fraction=D("1"))
    base = fixture_profile(t0)
    if cutoff:
        base = replace(base, policy=replace(base.policy, recovery_condition=RecoveryCondition(
            cutoff_seconds=79200, timezone="Asia/Seoul", reference="day_start_marked_equity")))
    profile = replace(base, account_scope=INTERVAL_SCOPE, strategy_code_sha256=program_digest(spec, artifact),
        instrument_rules=replace(base.instrument_rules, asof=t0 - seconds(60)),
        policy=replace(base.policy, initial_equity=D("100090"), drawdown_activation_equity=D("100090")))
    p, bars, decisions, rules, _, _, _ = fixture_capture(profile_digest=profile_contract_digest(profile),
        code_digest=profile.strategy_code_sha256, rules=profile.instrument_rules)
    count, end = len(bars), t0 - timedelta(minutes=2)
    protocol = replace(p, bar_seconds=60, preregistered_at=end - timedelta(minutes=count + 5),
        capture_start=end - timedelta(minutes=count - 1), capture_end=end, initial_cash_quote=D("100090"))
    bars = tuple(replace(row, observed_at=protocol.capture_start + timedelta(minutes=i),
                         received_at=protocol.capture_start + timedelta(minutes=i, seconds=1))
                 for i, row in enumerate(bars))
    prefixes = capture_history_digests(bars)
    decisions = tuple(replace(d, decided_at=bars[d.bar_index].received_at, history_sha256=prefixes[d.bar_index])
                      for d in decisions)
    registry, evaluated_at = register_protocol(protocol), t0 - seconds(50)
    result = run_paper_validation(protocol, bars, decisions, profile.instrument_rules, registry=registry,
                                  source_kind="prospective_paper_capture", now=evaluated_at)
    probe = make_fixed_driver(spec, protocol, profile, window=window, history_provider=invented_provider,
                              history_verifier=invented_verifier, program_artifact=artifact)
    identity = describe_fixed_driver(probe)
    request = build_review_request(profile, protocol, result, now=evaluated_at, program_artifact=artifact,
                                   parameters_json=parameters_json(spec))
    K1, _ = keys()
    body = review_body(request, asdict(identity), deployment_code_hash=real_code_hash(),
        audit_sha256=hashlib.sha256(b"invented composition audit, never an owner approval").hexdigest(),
        owner_fingerprint="SHA256:" + hashlib.sha256(raw(K1)).hexdigest(), issued_at=t0 - seconds(40),
        expires_at=t0 + timedelta(hours=1))
    files = {"profile.json": json.dumps(profile_body(profile)), "program.json": program_json(spec),
             "protocol.json": protocol_json(protocol),
             "capture.json": capture_json(CaptureArchive(registry=registry, source_kind="prospective_paper_capture",
                                                         bars=bars, decisions=decisions)),
             "review.json": document(body)}
    return SimpleNamespace(profile=profile, spec=spec, protocol=protocol, evaluated_at=evaluated_at,
                           identity=identity, files=files)


@contextmanager
def private_inputs(files):
    """The reviewed artifacts as plain local files (a realpath'd temporary folder, never the state root)."""
    folder = Path(os.path.realpath(tempfile.mkdtemp(prefix="tradegen_inputs_")))
    try:
        for name, text in files.items():
            (folder / name).write_text(text, encoding="utf-8")
        yield {name: str(folder / name) for name in files}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def compose_args(paths, evaluated_at, window, clock, hroot):
    return dict(profile_path=paths["profile.json"], program_path=paths["program.json"],
                protocol_path=paths["protocol.json"], capture_path=paths["capture.json"],
                review_path=paths["review.json"], evaluated_at=evaluated_at, window=window, clock=clock,
                head_root=hroot)


def history_journal(home, window):
    return home / STORE_DIRECTORY / digest(window) / "history.jsonl"


def test_compose_wires_loader_driver_history_reviews_and_evidence():
    t0 = at(26, 20, 0)
    with signed_home() as home, head_root() as hroot:
        window = DeploymentWindow(deployment_id="compose-fixture", start=t0 + seconds(60), end=t0 + seconds(180))
        reviewed_set, fake = reviewed(t0, window), FakeTime(t0)
        with private_inputs(reviewed_set.files) as paths:
            args = compose_args(paths, reviewed_set.evaluated_at, window, fake.clock, hroot)
            # The operator has not initialized the history head: the bind refuses before any file is created.
            refused(lambda: compose(**args), "HISTORY_HEAD_NOT_INITIALIZED")
            assert not (home / STORE_DIRECTORY).exists()
            BaselineHead(root=hroot, name=history_head_name(window),
                         chain=HistoryChain(root=state_root().absolute(), window=window)).initialize_reviewed_head(GENESIS)
            comp = compose(**args)
            assert comp.identity == reviewed_set.identity and comp.profile == reviewed_set.profile
            assert comp.protocol == reviewed_set.protocol and comp.program == reviewed_set.spec
            assert comp.evidence.protocol is comp.protocol and comp.evidence.review_verifier == comp.verifiers.source
            assert type(comp.driver) is StrategyDriver and describe_fixed_driver(comp.driver) == comp.identity
            assert len(history_journal(home, window).read_bytes().splitlines()) == 1
            assessment = assess_strategy(comp.protocol, comp.evidence.result,
                profile_contract_digest=profile_contract_digest(comp.profile),
                rule_terms_digest=rule_terms_digest(comp.profile.instrument_rules),
                strategy_code_sha256=comp.profile.strategy_code_sha256, now=fake.now,
                review_verifier=comp.evidence.review_verifier)
            assert assessment.research_review_ready and not assessment.execution_ready, assessment.reasons
            binding = ImplementationBinding(program_digest=comp.profile.strategy_code_sha256,
                protocol_digest=assessment.protocol_digest, evidence_digest=assessment.evidence_digest,
                profile_contract_digest=assessment.profile_contract_digest, rule_terms_digest=assessment.rule_terms_digest)
            assert comp.verifiers.implementation(binding, comp.driver).callback is comp.driver.callback
            again = compose(**args)                      # a restart replays the journal and binds the same identity
            assert again.identity == comp.identity and again.history is not comp.history
            refused(lambda: compose(**(args | {"review_path": paths["review.json"][:-5] + ".txt"})),
                    "WORKFLOW_FILE_REFUSED")
            refused(lambda: compose(**(args | {"capture_path": paths["capture.json"][:-12] + "missing.json"})),
                    "WORKFLOW_FILE_UNAVAILABLE_OR_REFUSED")
            assert len(history_journal(home, window).read_bytes().splitlines()) == 1


def test_real_adapters_run_under_the_coordinator_over_fake_transports():
    """The interval fixture's first trading day, so the chain requires 22:00 and the profile carries the matching
    recovery condition (R15). The window sits on the :30 grid across 22:00 (R13) and every authenticated read is
    charged the 0.2 s pace, so the 11-read capture lasts 2.2 s: the boundary unit at 21:59:58 brackets 22:00 and
    the chain commits the cutoff checkpoint, the one monitor inside the producer's 10 s boundary window refuses
    (cosmetic, by R8's single attempt), the book is read before each capture (R12) and every slot holds (R14)."""
    t0 = at(26, 21, 58)
    b = t0 + seconds(120)                                # 22:00:00 KST
    with signed_home() as home, head_root() as hroot, \
            patch("execution_accounts.upbit_collector.request", side_effect=AssertionError("network forbidden")):
        window = DeploymentWindow(deployment_id="compose-fixture", start=t0 + seconds(90), end=t0 + seconds(210))
        reviewed_set = reviewed(t0, window, cutoff=True)
        exchange = FakeUpbit()
        state, store, _, _ = seed_interval_chain(home, exchange, FEES, t0 - seconds(20), day_start=D("100000"),
            high=D("100100"), loss=D("0"), realized=D("90"), day_open=D("0"), previous=None)
        assert state.conventions.recovery_cutoff_seconds == 79200
        baseline_head = BaselineHead(root=hroot, name="baseline-head", chain=CheckpointChain(store))
        baseline_head.initialize_reviewed_head(state.state_digest)
        BaselineHead(root=hroot, name=history_head_name(window),
                     chain=HistoryChain(root=state_root().absolute(), window=window)).initialize_reviewed_head(GENESIS)
        fake = FakeTime(t0 - seconds(10))
        exchange.clock = fake.clock
        fetch, reads = exchange.fetch, []

        def paced_fetch(path, params):
            fake.now += seconds(0.2)                      # the E1 pace per authenticated read
            reads.append(fake.now)
            return fetch(path, params)
        exchange.fetch = paced_fetch
        source, states = UpbitIntervalSource(), []

        def prefetch(previous):
            states.append(previous)
            source.collect(exchange, previous=previous, anchor=ANCHOR, coverage=COVERAGE, clock=fake.clock,
                           trade_fees=FEES)
        with private_inputs(reviewed_set.files) as paths:
            comp = compose(**compose_args(paths, reviewed_set.evaluated_at, window, fake.clock, hroot))
            adapter = DryRunAdapter(upbit)
            c = Coordinator(mode="rehearsal", profile=comp.profile, evidence=comp.evidence, driver=comp.driver,
                implementation_verifier=comp.verifiers.implementation, adapters={"upbit": adapter},
                account_source=source, account_prefetch=prefetch, trusted_head=baseline_head,
                quote_source=Books(fake, bid=100, ask=102), window=window, bar_seconds=60,
                monitor_until=t0 + seconds(230), clock=fake.clock, history=comp.history, monitor_seconds=20,
                prefetch_lead_seconds=3, wait=fake.wait)
            seen = {}
            for offset in (95, 115, 125, 155, 215):
                fake.at(t0 + seconds(offset), lambda offset=offset: seen.__setitem__(offset, c.status()))
            status = c.run()
            assert status.phase == "closed" and status.account_source == "" and status.reasons == ()
            assert status.missed_slots == 0 and status.missed_boundaries == 0 and status.data_gap_at is None
            assert [seen[t].last_tick.status for t in (95, 155, 215)] == ["hold"] * 3
            assert all(seen[t].last_tick.reasons == () for t in (95, 155, 215))
            assert seen[115].account_source == "ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED"   # the monitor at 21:59:50
            assert seen[125].account_source == "" and seen[125].recovery_status == "satisfied"
            assert any(previous.asof == b and previous.recovery_checkpoint.cutoff_at == b for previous in states)
            assert status.recovery_status == "satisfied" and status.recovery_deadline == b
            # startup, 12 grid monitors (21:58:10 .. 22:01:50) less the refused one, the boundary and three slots
            assert status.published_units == 16 and adapter.requests == [] and not status.new_entry_blocked
            assert len(reads) == 11 * (status.published_units + 1)
            record = json.loads((hroot / "baseline-head" / "head.json").read_bytes())
            assert record["baseline_sequence"] == 16 and record["head"] == baseline_head.read()
            assert len(history_journal(home, window).read_bytes().splitlines()) == 4     # bound + three slots
            assert status.account_asof is not None and status.orders == ()
            again = compose(**compose_args(paths, reviewed_set.evaluated_at, window, fake.clock, hroot))
            assert again.identity == comp.identity
