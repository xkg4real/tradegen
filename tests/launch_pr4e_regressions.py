"""Independent PR4e orchestration regressions over invented isolated fixtures.

These check the coordinator boundaries and ordering, not real account evidence,
live orders, strategy performance or a completed protective-management revision.
"""
from dataclasses import replace
from datetime import timedelta
import base64
from types import SimpleNamespace
import threading
from unittest.mock import patch

from execution_launch import coordinator as C
from tests import launch_coordinator_universe as U


def test_prior_terms_failure_then_inactive_records_before_one_disarm_and_never_ticks():
    for recorded, raising in ((True, False), (False, False), (False, True)):
        with U.universe_fixture() as env, U.renewals(env):
            c = U.build_universe(env)
            c.bootstrap()
            assert c._held == (U.BTC,)
            env.terms.fail = U.FixtureRefusal("TERMS_INQUIRY_FAILED")
            U.refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
            assert c._terms_blocked and not c._vanished
            env.terms.fail = U.FixtureRefusal("TERMS_MARKET_INACTIVE")
            U.refused(c.refresh_instrument_rules, "TERMS_MARKET_INACTIVE")
            assert c._vanished and c._terms_blocked
            assert c._latest_frame.accounts[0].positions[0].price > 0
            kills = U.stub_kill(c, recorded)
            original_kill, at_kill, published = c._controller.kill, [], c._published

            def kill(session_id, *, reason, now):
                at_kill.append((len(env.history.rows), c._published, c._stopping.is_set()))
                if raising:
                    kills.append(reason)
                    raise U.FixtureRefusal("FIXTURE_KILL_FAILED")
                return original_kill(session_id, reason=reason, now=now)

            c._controller.kill = kill
            ticks = U.allow_seen(c)
            U.run_slot(env, c, env.window.start)
            (_, options), = env.history.rows
            assert options["universe"].events == ("UNIVERSE_MARKET_VANISHED",)
            assert at_kill == [(1, published + 1, True)]
            assert kills == ["market_vanished"] and ticks == [] and env.adapter.requests == []
            status = c.status()
            assert status.strategy_stopped and c._disarmed and status.last_tick is None
            assert not status.window_ended_missed_slot and c._terms_blocked
            assert "COORDINATOR_UNIVERSE_DISARM" in status.reasons
            assert status.disarm_failed is (recorded is not True or raising)
            assert c._toasted == ({"vanished"} if recorded and not raising else {"disarm-failed"})
            U.run_slot(env, c, env.window.start + U.seconds(60))
            with c._work:
                assert c._vanish() == ()
            assert kills == ["market_vanished"] and len(env.history.rows) == 1
            assert ticks == [] and env.adapter.requests == []


def test_odds_reads_one_observation_without_work_lock_or_account_provider_calls():
    with U.universe_fixture() as env:
        c = U.build_universe(env)
        c.bootstrap()
        captured = c._observation
        observation_reads, batch_calls, outcomes, failures = [], [], [], []

        def observation(instance):
            assert instance is c
            observation_reads.append(captured)
            return captured

        def no_provider(*args, **kwargs):
            raise AssertionError("odds must use the last published observation")

        def read_bars(markets, *, now, clock):
            assert markets == (U.BTC, U.XRP)
            return {"bars": markets}

        def run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof):
            assert controller is c._controller and template == "TEMPLATE" and n == 2
            assert positions is captured.positions and positions_asof == captured.asof
            batch_calls.append((bars, now))
            return "BATCH"

        def worker_call():
            try:
                outcomes.append(c.odds_batch("TEMPLATE", read_bars))
            except BaseException as exc:
                failures.append(exc)

        with patch.object(C, "run_batch", run_batch), patch.object(c, "_provider", no_provider), \
             patch.object(c, "_publish", no_provider), patch.object(c._controller, "account_provider", no_provider), \
             patch.object(C.Coordinator, "_observation", property(observation), create=True):
            with c._work:
                worker = threading.Thread(target=worker_call)
                worker.start()
                worker.join(5)
                finished_while_work_locked = not worker.is_alive()
            worker.join(5)
        assert not worker.is_alive() and finished_while_work_locked
        assert failures == [] and outcomes == ["BATCH"]
        assert len(observation_reads) == len(batch_calls) == 1


def test_odds_requires_current_aware_observation_with_exact_thirty_second_boundary():
    cases = ((None, False), (U.seconds(30), True),
             (U.seconds(30) + timedelta(microseconds=1), False), (-timedelta(microseconds=1), False),
             ("naive", False))
    for age, allowed in cases:
        with U.universe_fixture() as env:
            c = U.build_universe(env)
            c.bootstrap()
            at = env.fake.now
            if age is None:
                c._observation = None
            else:
                asof = at.replace(tzinfo=None) if age == "naive" else at - age
                c._observation = replace(c._observation, asof=asof)
            calls = []

            def run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof):
                calls.append((positions, positions_asof, now))
                assert timedelta(0) <= now - positions_asof <= U.seconds(30)
                return "BATCH"

            with patch.object(C, "run_batch", run_batch), patch.object(c, "_clock", lambda: at):
                call = lambda: c.odds_batch("TEMPLATE", lambda markets, **kwargs: {"bars": markets})
                if allowed:
                    assert call() == "BATCH" and len(calls) == 1
                else:
                    U.refused(call, "COORDINATOR_ODDS_ACCOUNT_NOT_CURRENT")
                    assert calls == []


def test_odds_slow_bars_use_later_observation_then_fresh_clock_without_mixing_fields():
    with U.universe_fixture() as env:
        c = U.build_universe(env)
        c.bootstrap()
        moments, latest, trace = [env.fake.now], [c._observation], []
        start = moments[0]

        def clock():
            trace.append("clock")
            return moments[0]

        def read_bars(markets, *, now, clock):
            assert now == start and markets == (U.BTC, U.XRP)
            trace.append("bars-start")
            moments[0] += U.seconds(45)
            latest[0] = replace(latest[0], asof=moments[0])
            trace.append("bars-done")
            return {"bars": markets}

        def observation(instance):
            assert instance is c and trace[-1] == "bars-done"
            trace.append("observation")
            return latest[0]

        def run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof):
            trace.append("batch")
            assert now == start + U.seconds(45) == positions_asof
            assert positions is latest[0].positions
            return "BATCH"

        with patch.object(C, "run_batch", run_batch), patch.object(c, "_clock", clock), \
             patch.object(C.Coordinator, "_observation", property(observation), create=True):
            assert c.odds_batch("TEMPLATE", read_bars) == "BATCH"
        assert trace == ["clock", "bars-start", "bars-done", "observation", "clock", "batch"]


def test_odds_refuses_seoul_midnight_or_same_day_clock_rollback_after_bars():
    for midnight, code in ((True, "COORDINATOR_ODDS_DAY_CHANGED"), (False, "COORDINATOR_CLOCK_ROLLBACK")):
        with U.universe_fixture() as env:
            c = U.build_universe(env)
            c.bootstrap()
            moments = [env.fake.now.astimezone(C.KST)]
            if midnight:
                moments[0] = moments[0].replace(hour=23, minute=59, second=50, microsecond=0)
            c._observation = replace(c._observation, asof=moments[0])
            batch_calls = []

            def read_bars(markets, *, now, clock):
                assert now == moments[0]
                moments[0] += U.seconds(20 if midnight else -1)
                c._observation = replace(c._observation, asof=moments[0])
                return {"bars": markets}

            def run_batch(*args, **kwargs):
                batch_calls.append(kwargs)
                raise AssertionError("invalid clock must be refused before the batch")

            with patch.object(C, "run_batch", run_batch), patch.object(c, "_clock", lambda: moments[0]):
                U.refused(lambda: c.odds_batch("TEMPLATE", read_bars), code)
            assert batch_calls == []


def test_odds_reader_exception_is_redacted_and_never_calls_batch():
    with U.universe_fixture() as env:
        c = U.build_universe(env)
        c.bootstrap()

        def failed_bars(*args, **kwargs):
            raise RuntimeError("private account and provider failure details")

        with patch.object(C, "run_batch", side_effect=AssertionError("batch must not run")) as batch:
            exc = U.refused(lambda: c.odds_batch("TEMPLATE", failed_bars), "COORDINATOR_ODDS_BATCH_FAILED")
        assert "private" not in str(exc) and batch.call_count == 0


def test_storage_refusal_never_retries_as_missing_book_and_still_runs_events():
    for code in ("HISTORY_STORAGE_LIMIT_EXCEEDED", "HISTORY_STORAGE_UNAVAILABLE", "HISTORY_STORE_IO_REFUSED"):
        with U.universe_fixture() as env:
            c = U.build_universe(env)
            c.bootstrap()
            attempted, events = [], []
            before_rows = tuple(env.history.rows)

            def failed_record(book, account, **options):
                attempted.append((book, options))
                raise U.FixtureRefusal(code)

            def event():
                events.append((len(attempted), c._published))

            c._events = lambda flags, account, day: [("FIXTURE_STORAGE_EVENT", event)]
            env.history.record_slot = failed_record
            ticks, published = U.allow_seen(c), c._published
            U.run_slot(env, c, env.window.start)
            assert len(attempted) == 1 and attempted[0][0] is not None
            assert attempted[0][1]["universe"].allow == frozenset({U.BTC, U.XRP})
            assert events == [(1, published + 1)]
            assert tuple(env.history.rows) == before_rows and ticks == [] and env.adapter.requests == []
            status = c.status()
            assert code in status.reasons and status.window_ended_missed_slot and status.new_entry_blocked
            assert status.last_tick is None and not c._runner.stopped
            U.run_slot(env, c, env.window.start + U.seconds(60))
            assert len(attempted) == 1 and len(events) == 1 and ticks == []


def test_known_vanished_market_never_ticks_even_if_its_event_action_raises_before_stop():
    with U.universe_fixture() as env:
        c = U.build_universe(env)
        c.bootstrap()
        c._vanished = True

        def failing_vanish():
            raise U.FixtureRefusal("FIXTURE_VANISH_FAILED")

        c._vanish = failing_vanish
        ticks = U.allow_seen(c)
        U.run_slot(env, c, env.window.start)
        assert len(env.history.rows) == 1
        assert env.history.rows[0][1]["universe"].events == ("UNIVERSE_MARKET_VANISHED",)
        assert "COORDINATOR_EVENT_FAILED" in c.status().reasons
        assert ticks == [] and c.status().last_tick is None and env.adapter.requests == []


def test_large_collector_evidence_crosses_coordinator_into_real_v3_history_without_losing_allow():
    """Real collector parser/history/object graph/head; fake account-interval,
    research and order-execution seams. This proves storage handoff, not an
    approved account baseline, strategy or order capability.
    """
    from core.isolation import state_root
    from execution_accounts.provider import build_observation
    from execution_control.store import GENESIS, MAX_ROW_BYTES, _canonical, _utc
    from execution_launch.baseline_head import BaselineHead
    from execution_launch.driver import make_fixed_driver
    from execution_launch.live_history import HistoryChain, LiveHistory, _row
    from execution_launch.profile import profile_contract_digest, rule_terms_digest
    from execution_launch.program import program_digest
    from execution_launch.runner import TickResult
    from tests import accounts_collector as A
    from tests import launch_live_history as LH
    from tests import launch_lossless_history as L
    from tests import launch_universe_history as H

    with U.universe_fixture() as env, H.head_root() as hroot:
        storage = H.policy()
        base = H.universe_env(storage)
        program = replace(base.program, universe_rule_sha256=env.profile.universe_rule_sha256)
        profile = replace(env.profile, strategy_id=program.strategy_id,
                          strategy_code_sha256=program_digest(program, base.artifact))
        env.profile = profile
        protocol = replace(base.protocol, strategy_id=program.strategy_id,
                           strategy_code_sha256=profile.strategy_code_sha256,
                           universe_rule_sha256=profile.universe_rule_sha256,
                           initial_cash_quote=profile.policy.initial_equity,
                           fee_fraction=max(base.protocol.fee_fraction, profile.instrument_rules.fee_fraction),
                           profile_contract_digest=profile_contract_digest(profile),
                           rule_terms_digest=rule_terms_digest(profile.instrument_rules,
                                                              universe_rule_sha256=profile.universe_rule_sha256))
        root, name = state_root().absolute(), "pr4e-large-history"

        def new_history():
            head = BaselineHead(root=hroot, name=name,
                                chain=HistoryChain(root=root, window=env.window, storage_policy=storage))
            history = LiveHistory(program, protocol, profile, root=root, window=env.window,
                                  clock=env.fake.clock, trusted_head=head, storage_policy=storage)
            driver = make_fixed_driver(program, protocol, profile, window=env.window,
                                       history_provider=history.provider, history_verifier=history.verifier,
                                       program_artifact=base.artifact)
            return head, history, driver

        head, history, driver = new_history()
        head.initialize_reviewed_head(GENESIS)  # Synthetic fixture provisioning only.
        identity = history.bind(driver)
        actual = SimpleNamespace(window=env.window, storage_policy=storage, identity=identity,
                                 profile=profile, hroot=hroot, name=name,
                                 T=lambda index: env.window.start + U.seconds(60 * index))
        # Match the independently captured synthetic listing in ManyDustSource.
        env.universe = replace(env.universe, listed=(U.BTC, U.ETH),
                               eligible=((U.BTC, U.D("900000000000")), (U.ETH, U.D("100000000000"))))
        env.slots.flags = {U.BTC: "unflagged", U.ETH: "unflagged"}
        c = U.build_universe(env, history=history, program=program)
        c.bootstrap()
        slot = env.window.start
        with patch.object(A, "NOW", slot), patch.object(A, "ORIGIN", slot - timedelta(days=1)), \
             patch.object(A, "SCOPE", profile.account_scope):
            source = L.ManyDustSource(1500)
            source.account_scope = profile.account_scope
            collection = A.collect(source)
            observation = build_observation(collection.bundle, now=slot)
        account = collection.bundle.accounts[0]
        assert len(account.positions) == 1500 and len(source.calls) < 2000
        assert all(item.units == 1 and item.price == 0 and item.unlisted for item in account.positions)
        large = L.padded_book(actual)
        assert len(large.receipt.raw_body) == 131072
        captured = []

        def read_book(symbol):
            assert symbol == U.BTC
            env.fake.now = large.received_at
            return large

        # The account-interval/checkpoint contract is deliberately a seam here.
        # The real coordinator publishes one matching frame and observation;
        # collector build_observation, live-history validation and all history
        # storage/head operations remain real. No controller order tick runs.
        def account_frame(previous, now):
            return replace(c._latest_frame, accounts=(account,),
                           interval=replace(c._latest_frame.interval, end=slot))

        def capture_tick(timestamps, *, max_steps, should_stop, entry_allow):
            assert max_steps == 1 and not should_stop()
            assert c._board._frame.accounts == (account,) and c._board._book is large
            assert c._observation is observation
            captured.append(entry_allow)
            return (TickResult(mode="rehearsal", status="hold"),)

        before_head = head.read()
        with patch.object(c, "_account_source", account_frame), \
             patch.object(c, "_provider", lambda now: observation), \
             patch.object(env.books, "read", read_book), \
             patch.object(c._runner, "run", capture_tick), \
             patch.object(history, "record_slot", wraps=history.record_slot) as recorded, \
             patch.object(head, "compare_and_set", wraps=head.compare_and_set) as cas:
            U.run_slot(env, c, slot)
        assert recorded.call_count == cas.call_count == 1
        assert recorded.call_args.args == (large, observation)
        assert recorded.call_args.kwargs["positions"] == account.positions
        allow = frozenset({U.BTC, U.ETH})
        assert captured == [allow] and captured[0] is history.recorded_allow
        assert c.status().allow_count == 2 and not c.status().window_ended_missed_slot
        assert c.status().last_tick.status == "hold" and env.adapter.requests == []
        outer = LH.rows(actual)[1]
        logical = H.logical_rows(actual)[1]["data"]
        assert head.read() == outer["row_sha256"] and LH.sequence(actual) == 2
        cas.assert_called_once_with(before_head, outer["row_sha256"])
        assert len(_canonical(outer) + b"\n") < 2048
        assert len(_canonical(_row(outer["seq"], before_head, "slot", logical,
                                   U.datetime.fromisoformat(outer["utc"]))) + b"\n") > MAX_ROW_BYTES
        assert base64.b64decode(logical["receipt"]["raw_body_b64"]) == large.receipt.raw_body
        assert logical["holdings"] == sorted(
            [item.symbol, "1", "0", _utc(item.asof), True, True] for item in account.positions)
        assert logical["universe"]["flags"] == {"sha256": "f" * 64, "exceptions": []}
        assert logical["universe"]["tickers"]["sha256"] == "7" * 64
        assert [row[0] for row in logical["universe"]["tickers"]["prices"]] == [U.BTC, U.ETH]
        assert logical["universe"]["allow"] == sorted(allow)
        assert "HISTORY_ROW_SIZE_FALLBACK" not in logical["universe"]["reasons"]
        now = env.fake.clock()
        frame = history.provider(LH.obs(actual, now))
        receipt = history.verifier(frame, identity, now)
        old_files = L.files(LH.directory(env.window)), L.files(hroot)
        _, replayed, restored_driver = new_history()
        assert replayed.bind(restored_driver) == identity
        assert replayed.provider(LH.obs(actual, now)) == frame
        assert replayed.verifier(frame, identity, now) == receipt
        assert replayed.recorded_allow == allow
        assert (L.files(LH.directory(env.window)), L.files(hroot)) == old_files
