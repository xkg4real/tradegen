"""Controlled live acceptance suite (Part A + Part B): Blocker 1 Approach A, Bid-Gap Y,
Standing Amendment A2 Protective Hold, CurrentPlanner, and tools/owner/live.py.

Hermetic only: temporary TRADEGEN_HOME, synthetic test keys, mocked HTTP seams,
zero real network calls, zero subprocesses, zero live order placement.
"""
from __future__ import annotations

import ast
from collections import deque
from dataclasses import asdict, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from email.utils import format_datetime
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit

from core.compliance import model as CM, owner
from core.odds import plan as odds_plan
from execution import keys
from execution_accounts import continuous, provider
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.collector import EvidenceError, SourceReceipt
from execution_accounts.universe import FlagRead, UniverseBars
from execution_accounts.upbit_collector import (
    TradePrint, collect_order_fills, collect_trade_window,
)
from execution_control.capability import consume_capability, digest
from execution_control.risk import Fill
from execution_launch import protective_state as P, protective_store as PS
from execution_launch.account_interval import split_boundary_intervals
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.coordinator import Coordinator, history_head_name
from execution_launch.driver import DeploymentWindow
from execution_launch.live_history import HistoryChain
from execution_launch.profile import risk_policy
from execution_launch.runner import (
    Runner, Signal, make_controller_order_boundary,
)
from execution_launch.strategy import evidence_digest
from execution_orders.model import AdapterResult, validate_request
from execution_orders.transport import Credentials, VenueOrderTransport
from execution_orders import upbit as upbit_codec
from tests import compliance_fixtures as CF
from tests.launch_account_interval import CONVENTIONS, FEES, FakeUpbit, at, seed as seed_account
from tests.launch_baseline_head import head_root
from tests.launch_coordinator import (
    EXIT, HOLD, PRICE, FakeTime, fill as make_fill, fixture as coord_fixture,
    memoized_pure_loads, order as make_broker_order, reviewed, seconds,
)
from tests.launch_owner_rehearsal import isolated_evaluations, plain, write_audit
from tests.launch_protective_store import limits as ps_limits
from tests.launch_review_auth import document
from tests.launch_runner import evidence_for
from tests.launch_windows_owner_authority import signed_home
from tools.owner import launch as O, live as L, planner as PL
from tools.signer import sign as S

D = Decimal
KST = CM.KST


class MockLiveVenueAdapter:
    """Non-DryRunAdapter test double implementing VenueOrderTransport's exact contract."""

    def __init__(self, *, results=()):
        self.results = deque(results)
        self.requests = []
        self.identities = {}

    def prepare(self, order, rules):
        return upbit_codec.prepare(order, rules)

    def prepare_cancel(self, order, venue_order_id, **kwargs):
        return upbit_codec.prepare_cancel(order, venue_order_id, **kwargs)

    def prepare_status(self, order, venue_order_id="", **kwargs):
        return upbit_codec.prepare_status(order, venue_order_id, **kwargs)

    def dispatch(self, request, capability, *, now):
        validate_request(request)
        consume_capability(capability, request)
        self.requests.append(request)
        if self.results:
            res = self.results.popleft()
            if isinstance(res, Exception):
                raise res
            return res
        vid = self.identities.setdefault(request.client_id, "live-uuid-" + request.client_id[-20:])
        return AdapterResult(
            status="accepted" if request.operation != "status" else "open",
            code="order_observed",
            venue_order_id=vid,
            client_id=request.client_id,
            filled_quantity=D("0"),
        )


def _make_protective_store(home: Path, hroot: Path, env) -> PS.ProtectiveStore:
    pol = P.ManagementPolicy(
        management_id=env.window.deployment_id,
        account_scope=env.profile.account_scope,
        venue="upbit",
        market="spot",
        quote_currency="KRW",
        symbol=env.profile.symbol,
        code_sha256="a" * 64,
        strategy_sha256=env.evidence.protocol.strategy_code_sha256,
        risk_policy_sha256=digest(risk_policy(env.profile)),
        holding_deadline=env.window.end,
        monitor_until=env.t0 + seconds(200),
    )
    store = PS.ProtectiveStore(
        root=home / "protective-a2",
        head_root=hroot,
        head_name="protective-a2",
        policy=pol,
        binding=PS.StoreBinding(
            driver_identity_sha256="1" * 64,
            research_sha256=evidence_digest(env.evidence.result),
            source_sha256=env.evidence.result.inputs_digest,
        ),
        limits=ps_limits(),
    )
    store.provision_empty()
    store.head.initialize_reviewed_head(store.genesis_digest)
    return store


def test_live_credentials_and_lock_exclusivity():
    # 1. Missing order keys, missing inquiry keys, and order==inquiry key collision
    def missing_order(names):
        if "UPBIT_ORDER_ACCESS_KEY" in names:
            raise keys.KeyMissing("UPBIT_ORDER_ACCESS_KEY")
        return ("inq-ak", "inq-sk")

    try:
        L.load_live_credentials("acct-live", key_reader=missing_order)
        raise AssertionError("expected LIVE_ORDER_CREDENTIALS_REQUIRED")
    except L.LiveError as exc:
        assert str(exc) == "LIVE_ORDER_CREDENTIALS_REQUIRED"

    def missing_inquiry(names):
        raise keys.KeyMissing("UPBIT_ACCESS_KEY")

    try:
        L.load_live_credentials("acct-live", key_reader=missing_inquiry)
        raise AssertionError("expected LIVE_INQUIRY_CREDENTIALS_REQUIRED")
    except L.LiveError as exc:
        assert str(exc) == "LIVE_INQUIRY_CREDENTIALS_REQUIRED"

    for bad_pair in (("inq-ak", "ord-sk"), ("ord-ak", "inq-sk"), ("same", "same")):
        def colliding(names, bp=bad_pair):
            return ("inq-ak", "inq-sk") if names[0] == "UPBIT_ACCESS_KEY" else bp

        try:
            L.load_live_credentials("acct-live", key_reader=colliding)
            raise AssertionError("expected LIVE_ORDER_INQUIRY_KEY_COLLISION")
        except L.LiveError as exc:
            assert str(exc) == "LIVE_ORDER_INQUIRY_KEY_COLLISION"

    def distinct(names):
        return ("inq-ak-1", "inq-sk-1") if names[0] == "UPBIT_ACCESS_KEY" else ("ord-ak-2", "ord-sk-2")

    resolver = L.load_live_credentials("acct-live", key_reader=distinct)
    creds = resolver("upbit", "acct-live")
    assert type(creds) is Credentials and creds.access_key == "ord-ak-2"
    assert "ord-ak-2" not in repr(creds) and "ord-sk-2" not in str(creds)

    # 2. Exclusive non-blocking live.lock
    with CF.temp_home() as home:
        lock1 = L._LiveLock(home)
        try:
            try:
                L._LiveLock(home)
                raise AssertionError("expected LIVE_LOCK_ALREADY_HELD")
            except L.LiveError as exc:
                assert str(exc) == "LIVE_LOCK_ALREADY_HELD"
        finally:
            lock1.release()
        lock2 = L._LiveLock(home)
        lock2.release()


def test_blocker1_approach_a_collector_bid_gap_and_boundary_splits():
    t0 = datetime(2026, 11, 10, 12, 59, 50, tzinfo=timezone.utc)  # 21:59:50 KST
    t1 = t0 + timedelta(seconds=25)                               # 22:00:15 KST (crosses 22:00 KST!)
    splits = split_boundary_intervals(
        t0, t1, recovery_cutoff_seconds=22 * 3600,
        first_trading_day=date(2026, 11, 1), previous_day_realized_net_krw=D(0),
    )
    assert len(splits) == 2
    assert splits[0] == (t0, datetime(2026, 11, 10, 13, 0, 0, tzinfo=timezone.utc))
    assert splits[1] == (datetime(2026, 11, 10, 13, 0, 0, tzinfo=timezone.utc), t1)

    # Straddling 00:00 KST midnight
    m0 = datetime(2026, 11, 10, 14, 59, 50, tzinfo=timezone.utc)  # 23:59:50 KST
    m1 = m0 + timedelta(seconds=20)                               # 00:00:10 KST
    msplits = split_boundary_intervals(
        m0, m1, recovery_cutoff_seconds=22 * 3600,
        first_trading_day=date(2026, 11, 1), previous_day_realized_net_krw=D(0),
    )
    assert len(msplits) == 2
    assert msplits[0][1] == datetime(2026, 11, 10, 15, 0, 0, tzinfo=timezone.utc)

    # Backward pagination & coverage refusal on /v1/trades/ticks
    start_ms = int(t0.timestamp() * 1000)
    end_ms = start_ms + 5000

    class FakeTickSource:
        account_scope = "acct-1"

        def __init__(self, rows_by_cursor):
            self.rows_by_cursor = rows_by_cursor

        def fetch(self, path, params):
            assert path == "/v1/trades/ticks"
            q = dict(params)
            cur = q.get("cursor", "")
            raw = json.dumps(self.rows_by_cursor[cur]).encode("utf-8")
            return SourceReceipt(
                path=path, params=tuple(params), account_scope="acct-1",
                received_at=t1, server_time=t1, raw_body=raw,
                sha256=hashlib.sha256(raw).hexdigest(),
            )

    page1 = [
        {"market": "KRW-BTC", "sequential_id": 103, "timestamp": end_ms - 100,
         "trade_price": 100000000, "trade_volume": "0.01", "ask_bid": "BID"},
        {"market": "KRW-BTC", "sequential_id": 102, "timestamp": start_ms + 500,
         "trade_price": 99900000, "trade_volume": "0.02", "ask_bid": "ASK"},
    ]
    page2 = [
        {"market": "KRW-BTC", "sequential_id": 102, "timestamp": start_ms + 500,
         "trade_price": 99900000, "trade_volume": "0.02", "ask_bid": "ASK"},
        {"market": "KRW-BTC", "sequential_id": 101, "timestamp": start_ms - 200,
         "trade_price": 99800000, "trade_volume": "0.01", "ask_bid": "BID"},
    ]
    src = FakeTickSource({"": page1, "101": page2})
    tw = collect_trade_window(src, "KRW-BTC", start=t0, end=t0 + timedelta(seconds=5))
    assert [tk.sequential_id for tk in tw.prints] == [102, 103] and len(tw.receipts) == 2

    # Incomplete coverage fails closed with UPBIT_TRADE_COVERAGE_INCOMPLETE
    incomplete_src = FakeTickSource({"": page1, "101": [page1[1]]})
    try:
        collect_trade_window(
            incomplete_src, "KRW-BTC", start=t0, end=t0 + timedelta(seconds=5), max_pages=1,
        )
        raise AssertionError("expected UPBIT_TRADE_COVERAGE_INCOMPLETE")
    except EvidenceError as exc:
        assert str(exc) == "UPBIT_TRADE_COVERAGE_INCOMPLETE"

    # collect_order_fills exact 18dp ROUND_DOWN + residual fee allocation
    class FakeOrderDetailSource:
        account_scope = "acct-1"

        def fetch(self, path, params):
            assert path == "/v1/order"
            body = {
                "uuid": "ord-uuid-1",
                "market": "KRW-BTC",
                "side": "bid",
                "ord_type": "limit",
                "state": "done",
                "volume": "0.03",
                "remaining_volume": "0",
                "price": "100000000",
                "locked": "0",
                "executed_volume": "0.03",
                "paid_fee": "10",
                "trades_count": 2,
                "created_at": "2026-11-10T21:59:50+09:00",
                "trades": [
                    {"uuid": "tr-1", "market": "KRW-BTC", "side": "bid", "volume": "0.01",
                     "price": "100000000", "funds": "1000000",
                     "created_at": "2026-11-10T21:59:51+09:00"},
                    {"uuid": "tr-2", "market": "KRW-BTC", "side": "bid", "volume": "0.02",
                     "price": "100000000", "funds": "2000000",
                     "created_at": "2026-11-10T21:59:52+09:00"},
                ],
            }
            raw = json.dumps(body).encode("utf-8")
            return SourceReceipt(
                path=path, params=tuple(params), account_scope="acct-1",
                received_at=t1, server_time=t1, raw_body=raw,
                sha256=hashlib.sha256(raw).hexdigest(),
            )

    of_res = collect_order_fills(FakeOrderDetailSource(), "ord-uuid-1")
    assert len(of_res.fills) == 2
    assert of_res.fills[0].fee_amount + of_res.fills[1].fee_amount == D("10")
    assert of_res.fills[0].fee_amount == D("3.333333333333333333")
    assert of_res.fills[1].fee_amount == D("6.666666666666666667")

    # Multi-coin continuous valuation across 3 held KRW coins
    h_fills = (
        Fill(venue="upbit", account_scope="acct-1", order_id="ho-1", fill_id="hf-1",
             market="spot", symbol="KRW-BTC", base_currency="BTC", quote_currency="KRW",
             side="buy", quantity=D("0.01"), price=D("100000000"), quote_krw=D(1),
             fee_amount=D(0), fee_currency="KRW", executed_at=t0 - timedelta(minutes=5)),
        Fill(venue="upbit", account_scope="acct-1", order_id="ho-2", fill_id="hf-2",
             market="spot", symbol="KRW-ETH", base_currency="ETH", quote_currency="KRW",
             side="buy", quantity=D("0.1"), price=D("4000000"), quote_krw=D(1),
             fee_amount=D(0), fee_currency="KRW", executed_at=t0 - timedelta(minutes=5)),
        Fill(venue="upbit", account_scope="acct-1", order_id="ho-3", fill_id="hf-3",
             market="spot", symbol="KRW-SOL", base_currency="SOL", quote_currency="KRW",
             side="buy", quantity=D("2"), price=D("250000"), quote_krw=D(1),
             fee_amount=D(0), fee_currency="KRW", executed_at=t0 - timedelta(minutes=5)),
    )
    mc = continuous.value_trade_paths(
        {
            "KRW-BTC": (TradePrint(
                market="KRW-BTC", sequential_id=1, timestamp_ms=start_ms + 1000,
                at=t0 + timedelta(seconds=1), price=D("98000000"), volume=D("0.1"),
                ask_bid="ASK", source_sha256="1" * 64,
            ),),
        },
        opening_marks={"KRW-BTC": D("100000000"), "KRW-ETH": D("4000000"), "KRW-SOL": D("250000")},
        opening_cash_krw=D("5000000"),
        opening_units=(("KRW-BTC", D("0.01")), ("KRW-ETH", D("0.1")), ("KRW-SOL", D("2"))),
        historical_fills=h_fills,
        interval_fills=(),
        previous_equity_krw=D("6900000"),
        previous_realized_net_krw=D(0),
        start=t0,
        end=t0 + timedelta(seconds=10),
        account_scope="acct-1",
    )
    assert mc.minimum_equity_krw == D("6880000")
    assert mc.equity_krw == D("6880000")


def test_d12_owner_snapshot_bid_gap_and_protective_terms_and_signer():
    with CF.temp_home() as home, CF.pubkey_at(home / "test-anchor.pem"):
        key = CF.full_home(home)
        t_day1 = datetime(2026, 11, 10, 2, 0, 0, tzinfo=timezone.utc)  # 11:00 KST on 2026-11-10
        t_day2 = datetime(2026, 11, 10, 16, 0, 0, tzinfo=timezone.utc) # 01:00 KST on 2026-11-11

        # sign.py main() enforces its interactive anti-automation refusal (returns 2)
        with patch("sys.stderr", new=StringIO()):
            assert S.main([
                "bid-gap-set", "--scope", "acct-live", "--y", "0.03",
                "--effective-from", "2026-11-10T02:00:00Z",
            ]) == 2

        def cli_sign(argv: list[str], *, utc: str) -> None:
            args = S._parser().parse_args(argv)

            def fake_sign(_args, kind, data):
                assert S._data_problem(kind, data) == ""
                CF.sign(key, kind, data, utc=utc)
                return 0

            with patch.object(S, "_sign", side_effect=fake_sign):
                assert args.run(args) == 0

        cli_sign([
            "bid-gap-set", "--scope", "acct-live", "--y", "0.03",
            "--effective-from", "2026-11-10T02:00:00Z",
        ], utc="2026-11-10T02:00:00Z")
        cli_sign([
            "protective-terms-set", "--scope", "acct-live",
            "--trailing-stop-x", "0.05",
            "--halt-margin-krw", "50000",
            "--daily-margin-krw", "25000",
        ], utc="2026-11-10T02:00:00Z")

        # Initial bid-gap setting is delayed until next Seoul date (D12 loosening/initial rule);
        # initial protective_terms_set activates immediately once utc <= now_utc!
        snap_d1 = owner.load_owner_snapshot(t_day1)
        assert snap_d1.ok and snap_d1.bid_gap_for("acct-live") is None
        assert snap_d1.protective_for("acct-live") == CM.ProtectiveTerms(
            trailing_stop_x=D("0.05"), halt_margin_krw=D("50000"), daily_margin_krw=D("25000"),
        )

        snap_d2 = owner.load_owner_snapshot(t_day2)
        assert snap_d2.ok and snap_d2.bid_gap_for("acct-live") == D("0.03")
        p_terms = snap_d2.protective_for("acct-live")
        assert p_terms is not None and p_terms.trailing_stop_x == D("0.05")
        assert p_terms.halt_margin_krw == D("50000") and p_terms.daily_margin_krw == D("25000")

        # Tightening (smaller y: 0.015 < 0.03; tighter trailing stop 0.03 < 0.05; larger margin 70000 > 50000)
        # takes effect IMMEDIATELY at effective_from on the same Seoul day!
        cli_sign([
            "bid-gap-set", "--scope", "acct-live", "--y", "0.015",
            "--effective-from", "2026-11-10T16:05:00Z",
        ], utc="2026-11-10T16:05:00Z")
        cli_sign([
            "protective-terms-set", "--scope", "acct-live",
            "--trailing-stop-x", "0.03",
            "--halt-margin-krw", "70000",
            "--daily-margin-krw", "30000",
        ], utc="2026-11-10T16:05:00Z")

        t_tight = t_day2 + timedelta(minutes=6)
        snap_tight = owner.load_owner_snapshot(t_tight)
        assert snap_tight.bid_gap_for("acct-live") == D("0.015")
        assert snap_tight.protective_for("acct-live").trailing_stop_x == D("0.03")
        assert snap_tight.protective_for("acct-live").halt_margin_krw == D("70000")

        # Signer's standalone snapshot fold matches owner.load_owner_snapshot identically
        log_rows = [json.loads(line.decode("utf-8")) for line in owner.log_path().read_bytes().splitlines()]
        s_snap = S.fold_owner_snapshot(log_rows, now=t_tight)
        assert s_snap.ok and s_snap.bid_gaps == dict(snap_tight.bid_gaps)

        # bid-gap-clear clears immediately
        cli_sign(["bid-gap-clear", "--scope", "acct-live", "--reason", "operator clear"], utc="2026-11-10T16:07:00Z")
        assert owner.load_owner_snapshot(t_day2 + timedelta(minutes=8)).bid_gap_for("acct-live") is None


def test_d14_clean_current_planner_and_controlled_runner():
    # Static check: tools/owner/planner.py must not import legacy research modules
    src = Path(PL.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    banned = {"core.oddsdata", "data", "core.quant", "config", "core.ficc.context_log"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert not any(a.name == b or a.name.startswith(b + ".") for b in banned), a.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert not any(node.module == b or node.module.startswith(b + ".") for b in banned), node.module

    with memoized_pure_loads(), coord_fixture() as env, head_root() as hroot:
        live_adapter = MockLiveVenueAdapter()
        pstore = _make_protective_store(env.home, hroot, env)
        env.signal[0] = HOLD

        c = Coordinator(
            mode="controlled",
            profile=env.profile,
            evidence=env.evidence,
            driver=env.driver,
            implementation_verifier=env.review,
            adapters={"upbit": live_adapter},
            account_source=env.producer,
            account_prefetch=env.producer.prefetch,
            trusted_head=env.head,
            quote_source=env.books,
            window=env.window,
            bar_seconds=60,
            monitor_until=env.t0 + seconds(200),
            clock=env.fake.clock,
            monitor_seconds=20,
            prefetch_lead_seconds=3,
            wait=env.fake.wait,
            protective_store=pstore,
            allow_held_account=True,
        )

        # Build 260 synthetic final daily bars ending yesterday in KST
        seoul_today = env.t0.astimezone(KST).date()
        bars_rows = tuple(
            (
                (seoul_today - timedelta(days=260 - i)).isoformat(),
                90000000.0 + i * 100000.0,
                90100000.0 + i * 100000.0,
            )
            for i in range(260)
        )
        fake_bars = {
            "KRW-BTC": UniverseBars(market="KRW-BTC", bars=bars_rows, receipt_sha256=("d" * 64,))
        }
        template = odds_plan.Plan(
            name="live-btc-plan",
            track="compounding",
            stake_krw=100_000.0,
            target_krw=105_000.0,
            fx_krw_per_usd=1400.0,
            start=seoul_today,
            horizon_days=3,
            leg=odds_plan.Leg(venue="upbit", symbol="BTC", model="bootstrap", edge_source="none"),
            fraction=odds_plan.fixed(0.1),
        )
        planner = PL.CurrentPlanner(
            template=template,
            symbol_provider=lambda: c._profile.symbol,
            observation_provider=lambda: c._observation,
            clock=env.fake.clock,
            bars_reader=lambda markets, **kw: fake_bars,
        )
        runtime = O.OwnerRuntime(c, preparation_provider=planner)
        boot = runtime.bootstrap()
        assert boot["published_units"] == 1
        prep = runtime.prepare()
        assert prep["session_id"].startswith("L") and not prep["execution_ready"]


def test_standing_amendment_a2_zero_auto_sale_and_swtb_app_only_sells():
    with memoized_pure_loads(), coord_fixture() as env, head_root() as hroot:
        env.profile = replace(env.profile, policy=replace(env.profile.policy, initial_equity=D("500000")))
        env.evidence = evidence_for(env.profile, env.t0)
        live_adapter = MockLiveVenueAdapter()
        pstore = _make_protective_store(env.home, hroot, env)
        # coord_fixture() seeds 0.001 BTC pre-existing manual coins BEFORE deployment (cash=900,000, equity=1,000,000)!
        assert env.producer.units == D("0.001") and env.producer.cash == D("900000")
        env.signal[0] = HOLD

        terms_holder = [CM.ProtectiveTerms(
            trailing_stop_x=D("0.04"),
            halt_margin_krw=D("50000"),
            daily_margin_krw=D("2"),
        )]

        class FakeSnap:
            ok = True
            def protective_for(self, scope):
                return terms_holder[0]

        c = Coordinator(
            mode="controlled",
            profile=env.profile,
            evidence=env.evidence,
            driver=env.driver,
            implementation_verifier=env.review,
            adapters={"upbit": live_adapter},
            account_source=env.producer,
            account_prefetch=env.producer.prefetch,
            trusted_head=env.head,
            quote_source=env.books,
            window=env.window,
            bar_seconds=60,
            monitor_until=env.t0 + seconds(200),
            clock=env.fake.clock,
            monitor_seconds=20,
            prefetch_lead_seconds=3,
            wait=env.fake.wait,
            protective_store=pstore,
            owner_snapshot_provider=lambda now: FakeSnap(),
            allow_held_account=True,
        )
        c.bootstrap()
        assert c.status().account_source == ""

        # 1. Faults / missed_slot / restart with ONLY pre-existing manual 0.001 BTC -> ZERO sales!
        c._commit_protective_fault("inputs_missing", env.fake.now)
        c._commit_protective_fault("clock_unreliable", env.fake.now)
        assert [r for r in live_adapter.requests if r.operation == "create"] == []
        assert c.status().protective_hold_active is True

        # 2. Simulate app buying 0.0002 BTC during deployment (total = 0.0012 BTC: 0.001 manual + 0.0002 app)
        from tests.control_session import selected
        plan, inputs, seed_hex = selected(env.fake.now)
        plan = replace(plan, stake_krw=300000.0, target_krw=330000.0)
        prepared = c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed_hex)
        CF.sign(env.key, "session_armed", {"session_id": prepared.session_id}, utc=CM.iso_utc(env.fake.now))
        env.signal[0] = Signal(signal_id="buy-app-1", action="entry", quantity=D("0.0002"), limit_price=PRICE)
        env.fake.now = env.window.start
        c._slot(env.window.start)
        creates = [r for r in live_adapter.requests if r.operation == "create"]
        assert len(creates) == 1 and dict(creates[0].body)["side"] == "bid"
        buy_cid = c.status().last_tick.client_id
        buy_vid = "live-uuid-" + buy_cid[-20:]

        # Reconcile app buy fill of 0.0002 BTC -> total account BTC = 0.0012, app-owned q_app = 0.0002!
        env.producer.units = D("0.0012")
        env.producer.cash = D("880000")
        env.producer.fills += (make_fill(
            side="buy", quantity=D("0.0002"), price=PRICE, fee=D("0"),
            order=buy_vid, fid="fill-app-1", at=env.fake.now,
        ),)
        env.producer.orders += (make_broker_order(
            side="buy", quantity=D("0.0002"), filled=D("0.0002"), price=PRICE,
            oid=buy_vid, client=buy_cid, status="filled",
        ),)
        live_adapter.results.append(AdapterResult(
            status="filled", code="order_observed", venue_order_id=buy_vid,
            client_id=buy_cid, filled_quantity=D("0.0002"), fee=D("0"), fee_currency="KRW",
        ))
        env.signal[0] = HOLD
        env.fake.now += seconds(5)
        c._monitor("monitor")
        assert c._app_units.get("KRW-BTC") == D("0.0002")
        assert len([r for r in live_adapter.requests if r.operation == "create"]) == 1

        # 3. Missing inputs fault while holding app coins -> ZERO automatic sales!
        c._commit_protective_fault("inputs_missing", env.fake.now)
        assert len([r for r in live_adapter.requests if r.operation == "create"]) == 1

        # 4. Trigger T on next slot (trailing stop X = 4% from post-stop high PRICE=100,000,000 -> bid drops 5% to 95,000,000):
        # Must sell ONLY q_app = 0.0002 BTC, NEVER the 0.0010 manual BTC!
        slot2 = env.window.start + seconds(60)
        env.books.bid = 95000000
        env.books.ask = 95001000
        env.fake.now = slot2
        c._slot(slot2)
        sells = [r for r in live_adapter.requests if r.operation == "create" and dict(r.body)["side"] == "ask"]
        assert len(sells) == 1
        assert dict(sells[0].body)["volume"] == "0.0002"
        assert "T" in c.status().protective_triggers

        # 5. Window end (deadline) never triggers an extra automatic sale
        env.fake.now = env.window.end + seconds(1)
        c._commit_protective_fault("deadline", env.fake.now)
        sells_after = [r for r in live_adapter.requests if r.operation == "create" and dict(r.body)["side"] == "ask"]
        assert len(sells_after) == 1


def test_persistent_halt_a2_n2_cancels_app_orders_and_preserves_owner_exit():
    with memoized_pure_loads(), coord_fixture() as env, head_root() as hroot:
        env.profile = replace(env.profile, policy=replace(env.profile.policy, initial_equity=D("500000")))
        env.evidence = evidence_for(env.profile, env.t0)
        live_adapter = MockLiveVenueAdapter()
        pstore = _make_protective_store(env.home, hroot, env)
        env.signal[0] = HOLD

        c = Coordinator(
            mode="controlled",
            profile=env.profile,
            evidence=env.evidence,
            driver=env.driver,
            implementation_verifier=env.review,
            adapters={"upbit": live_adapter},
            account_source=env.producer,
            account_prefetch=env.producer.prefetch,
            trusted_head=env.head,
            quote_source=env.books,
            window=env.window,
            bar_seconds=60,
            monitor_until=env.t0 + seconds(200),
            clock=env.fake.clock,
            monitor_seconds=20,
            prefetch_lead_seconds=3,
            wait=env.fake.wait,
            protective_store=pstore,
            allow_held_account=True,
        )
        runtime = O.OwnerRuntime(c)
        boot = runtime.bootstrap()
        assert boot["account_source"] == ""

        # Place an app buy order (0.0001 BTC) AND an explicit owner-tagged exit order (0.0005 BTC <= 0.001 held)
        from tests.control_session import selected
        plan, inputs, seed_hex = selected(env.fake.now)
        plan = replace(plan, stake_krw=300000.0, target_krw=330000.0)
        prepared = c.prepare(selected_plan=plan, inputs=inputs, selection_seed_hex=seed_hex)
        CF.sign(env.key, "session_armed", {"session_id": prepared.session_id}, utc=CM.iso_utc(env.fake.now))
        env.signal[0] = Signal(signal_id="app-buy-open", action="entry", quantity=D("0.0001"), limit_price=PRICE)
        env.fake.now = env.window.start
        c._slot(env.window.start)
        app_buy_cid = c.status().last_tick.client_id
        assert app_buy_cid

        env.fake.now += seconds(2)
        exit_rep = runtime.command(f"exit 0.0005 {PRICE}")
        owner_exit_cid = exit_rep["client_id"]
        assert exit_rep["owner_tagged"] is True and owner_exit_cid in c._owner_exit_client_ids

        # Keep both orders open on broker snapshot (plus the seeded pre-buy order) so reconciliation keeps them ACKNOWLEDGED
        env.producer.orders = env.producer.orders + (
            make_broker_order(
                side="buy", quantity=D("0.0001"), filled=D("0"), price=PRICE,
                oid="live-uuid-" + app_buy_cid[-20:], client=app_buy_cid, status="open",
            ),
            make_broker_order(
                side="sell", quantity=D("0.0005"), filled=D("0"), price=PRICE,
                oid="live-uuid-" + owner_exit_cid[-20:], client=owner_exit_cid, status="open",
            ),
        )

        # Append a persistent system_halt to owner_log -> PERSISTENT_HALT must cancel app_buy_cid
        # while sparing owner_exit_cid (A2 N2)!
        env.fake.now += seconds(3)
        owner.append_system_entry(
            "system_halt", {"floor_krw": 750000.0},
            now=env.fake.now,
        )
        env.fake.now += seconds(1)
        c._monitor("monitor")

        cancels = [r for r in live_adapter.requests if r.operation == "cancel"]
        cancelled_cids = {r.client_id for r in cancels}
        assert app_buy_cid in cancelled_cids
        assert owner_exit_cid not in cancelled_cids

        # Explicit operator cancel-all cancels the remaining active owner exit when requested
        env.fake.now += seconds(2)
        ca_rep = runtime.command("cancel-all")
        assert owner_exit_cid in ca_rep["client_ids"]


def test_build_live_end_to_end_composition_and_startup_disarm():
    t0 = at(26, 20)
    with isolated_evaluations(), memoized_pure_loads(), \
            signed_home() as home, head_root() as heads, tempfile.TemporaryDirectory() as path:
        folder = Path(path).resolve()
        window = DeploymentWindow(
            deployment_id="controlled-live-1",
            start=t0 + timedelta(seconds=60),
            end=t0 + timedelta(seconds=180),
        )
        current = reviewed(t0, window)
        exchange = FakeUpbit()
        state, store, _, _ = seed_account(
            home, exchange, FEES, t0 - timedelta(seconds=15),
            day_start=D("100000"), high=D("100100"), loss=D(0), realized=D(90), day_open=D(0), previous=None,
            conventions=replace(CONVENTIONS, recovery_cutoff_seconds=None),
        )
        BaselineHead(root=heads, name="account-baseline", chain=CheckpointChain(store)).initialize_reviewed_head(
            state.state_digest
        )
        BaselineHead(
            root=heads, name=history_head_name(window), chain=HistoryChain(root=home, window=window)
        ).initialize_reviewed_head("0" * 64)

        audit = write_audit(folder, state, window)
        audit["kind"] = "tradegen-controlled-live-audit/1"
        raw_audit = json.dumps(audit, sort_keys=True).encode("utf-8")
        (folder / "account-audit.json").write_bytes(raw_audit)

        review = json.loads(current.files["review.json"])["body"]
        review["audit_sha256"] = hashlib.sha256(raw_audit).hexdigest()
        current.files["review.json"] = document(review)
        for name, text in current.files.items():
            (folder / name).write_text(text, encoding="utf-8")
        (folder / "window.json").write_text(json.dumps(plain(asdict(window))), encoding="utf-8")

        odds_tpl = {
            "schema_version": 1,
            "kind": "tradegen-live-odds-template/1",
            "name": "btc-live-template",
            "track": "compounding",
            "stake_krw": "50000",
            "target_krw": "55000",
            "fx_krw_per_usd": "1400",
            "horizon_days": 2,
            "model": "bootstrap",
            "fraction_kind": "fixed",
            "fraction_value": "0.1",
            "edge_source": "none",
            "assumed_p": None,
            "bracket": None,
            "sizing": "floor_safe",
        }
        (folder / "odds-template.json").write_text(json.dumps(odds_tpl), encoding="utf-8")

        monitor_until = t0 + timedelta(seconds=210)
        config = {
            "schema_version": 1,
            "kind": "tradegen-controlled-live/1",
            **{key: str(folder / (key + ".json"))
               for key in ("profile", "program", "protocol", "capture", "review", "window")},
            "account_audit": str(folder / "account-audit.json"),
            "odds_template": str(folder / "odds-template.json"),
            "evaluated_at": current.evaluated_at.isoformat(),
            "monitor_until": monitor_until.isoformat(),
            "state_root": str(home),
            "head_root": str(heads),
        }
        cfg_path = folder / "live.json"
        cfg_path.write_text(json.dumps(config), encoding="utf-8")

        # Provision deployment ProtectiveStore head explicitly (operator step)
        fake = FakeTime(t0)
        from execution_launch.coordinator import compose as compose_window
        comp_preview = compose_window(
            profile_path=config["profile"], program_path=config["program"], protocol_path=config["protocol"],
            capture_path=config["capture"], review_path=config["review"],
            evaluated_at=current.evaluated_at, window=window, clock=fake.clock, head_root=heads,
        )
        pstore = L.protective_store_for_deployment(
            root=home, head_root=heads, window=window, profile=comp_preview.profile,
            driver=comp_preview.driver, identity=comp_preview.identity, evidence=comp_preview.evidence,
            audit_sha256=hashlib.sha256(raw_audit).hexdigest(), monitor_until=monitor_until,
        )
        pstore.provision_empty()
        pstore.head.initialize_reviewed_head(pstore.genesis_digest)

        # Arm a stale session before build_live to prove startup recovery disarms it
        CF.sign(CF.test_key(), "session_armed", {"session_id": "StaleLiveSession1"}, utc=CM.iso_utc(t0 - timedelta(seconds=10)))
        assert "StaleLiveSession1" in owner.load_owner_snapshot(t0).armed_sessions

        def key_reader(names):
            return ("inq-live-ak", "inq-live-sk") if names[0] == "UPBIT_ACCESS_KEY" else ("ord-live-ak", "ord-live-sk")

        exchange.clock = fake.clock

        def fake_inquiry_send(method, url, **kwargs):
            parsed = urlsplit(url)
            assert method == "GET" and parsed.netloc == "api.upbit.com"
            receipt = exchange.fetch(parsed.path, tuple(parse_qsl(parsed.query)))
            return (
                200,
                {"Date": format_datetime(receipt.server_time.astimezone(timezone.utc), usegmt=True)},
                receipt.raw_body,
            )

        with patch.dict(os.environ, {
            "UPBIT_ACCESS_KEY": "inq-live-ak",
            "UPBIT_SECRET_KEY": "inq-live-sk",
            "UPBIT_ORDER_ACCESS_KEY": "ord-live-ak",
            "UPBIT_ORDER_SECRET_KEY": "ord-live-sk",
        }), \
                patch("execution.transport._send", side_effect=fake_inquiry_send), \
                patch("execution.transport._headers", return_value=({}, None, None)), \
                patch("execution.transport._sleep", side_effect=lambda s: None), \
                patch("execution.transport._clock", side_effect=fake.clock), \
                patch("execution_orders.transport._send", side_effect=AssertionError("no live order expected")):
            runtime = L.build_live(str(cfg_path), clock=fake.clock, key_reader=key_reader)
            try:
                # Startup recovery disarmed StaleLiveSession1!
                assert owner.load_owner_snapshot(fake.now).armed_sessions == frozenset()

                # Concurrent second build_live must fail closed on live.lock!
                try:
                    L.build_live(str(cfg_path), clock=fake.clock, key_reader=key_reader)
                    raise AssertionError("expected LIVE_LOCK_ALREADY_HELD")
                except L.LiveError as exc:
                    assert str(exc) == "LIVE_LOCK_ALREADY_HELD"

                out = []
                O.serve(runtime, stream=StringIO("bootstrap\nstatus\ncancel-all\ndisarm\nclose\n"), emit=out.append)
                assert out[0]["command"] == "bootstrap" and out[0]["published_units"] == 1
                assert out[1]["command"] == "status"
                assert out[2]["command"] == "cancel-all" and out[2]["cancelled_requested"] == 0
                assert out[3]["command"] == "disarm"
                assert out[4]["command"] == "close" and out[4]["closed"] is True
            finally:
                runtime.close()


def tests():
    module = sys.modules[__name__]
    from tests.control_acceptance import _wrap
    return [
        ("live_controlled_acceptance/" + name, _wrap(fn))
        for name, fn in sorted(vars(module).items())
        if name.startswith("test_") and callable(fn)
    ]


def main(argv=None) -> int:
    from tests.run_all import run
    args = list(sys.argv[1:] if argv is None else argv)
    rows = run([(n, fn) for n, fn in tests() if not args or args[0] in n])
    counts = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL", "NOT_RUN")}
    print(counts)
    return 0 if rows and counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
