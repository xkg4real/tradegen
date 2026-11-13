# Prepared regression fragments — not implemented or executed

These are source-reading worksheets for the existing approved plans. Reconcile helper contracts and review each assertion after dependencies merge. AST syntax checks are not RED/GREEN test results. No production source or policy was changed.

## pr4e-required-regressions.py

````python
# Scratch-only proposed tests for tests/launch_coordinator_universe.py after PR4e Tasks5-12 exist.
# Reuses the exact plan's helpers/imports. Not imported, executed or integrated during PR4d verification.
# Account/day error codes below are proposed reuse of existing contracts, as documented in the companion md.


def test_terms_failure_then_inactive_reaches_one_disarm_after_fresh_record_without_a_tick():
    for recorded, raising in ((True, False), (False, False), (False, True)):
        with universe_fixture() as env, renewals(env):
            c = build_universe(env)
            c.bootstrap()
            assert c._held == (BTC,)
            env.terms.fail = FixtureRefusal("TERMS_INQUIRY_FAILED")
            refused(c.refresh_instrument_rules, "TERMS_INQUIRY_FAILED")
            assert c._terms_blocked and not c._vanished
            env.terms.fail = FixtureRefusal("TERMS_MARKET_INACTIVE")
            refused(c.refresh_instrument_rules, "TERMS_MARKET_INACTIVE")
            assert c._vanished
            # Keep the existing positive held mark: a newly zero-valued holding must not be needed to unstick it.
            assert c._latest_frame.accounts[0].positions[0].price > 0
            kills = stub_kill(c, recorded)
            original_kill, at_kill = c._controller.kill, []
            published = c._published

            def kill(session_id, *, reason, now):
                at_kill.append((len(env.history.rows), c._published, c._stopping.is_set()))
                if raising:
                    kills.append(reason)
                    raise FixtureRefusal("FIXTURE_KILL_FAILED")
                return original_kill(session_id, reason=reason, now=now)

            c._controller.kill = kill
            seen = allow_seen(c)
            run_slot(env, c, env.window.start)
            (_, options), = env.history.rows
            assert options["universe"].events == ("UNIVERSE_MARKET_VANISHED",)
            assert at_kill == [(1, published + 1, True)]    # fresh publish, record, stop, then kill
            assert kills == ["market_vanished"] and seen == [] and env.adapter.requests == []
            status = c.status()
            assert status.strategy_stopped and c._disarmed and status.last_tick is None
            assert not status.window_ended_missed_slot
            assert "COORDINATOR_UNIVERSE_DISARM" in status.reasons
            assert status.disarm_failed is (recorded is not True or raising)
            assert c._toasted == ({"vanished"} if recorded and not raising else {"disarm-failed"})
            # A repeated slot and direct replay of the event cannot issue another kill or enter the order tick.
            run_slot(env, c, env.window.start + seconds(60))
            with c._work:
                assert c._vanish() == ()
            assert kills == ["market_vanished"] and len(env.history.rows) == 1
            assert seen == [] and env.adapter.requests == []


def test_odds_uses_one_observation_without_the_work_lock_or_an_account_provider_call():
    with universe_fixture() as env:
        c = build_universe(env)
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
            assert markets == (BTC, XRP)
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

        with patch.object(C, "run_batch", run_batch), \
                patch.object(c, "_provider", no_provider), \
                patch.object(c._controller, "account_provider", no_provider), \
                patch.object(C.Coordinator, "_observation", property(observation), create=True):
            with c._work:
                worker = threading.Thread(target=worker_call)
                worker.start()
                worker.join(5)
                finished_while_work_locked = not worker.is_alive()
            worker.join(5)                  # clean up an incorrect lock-taking implementation before asserting
        assert not worker.is_alive() and finished_while_work_locked
        assert failures == [] and outcomes == ["BATCH"]
        assert len(observation_reads) == len(batch_calls) == 1


def test_odds_rejects_missing_stale_or_future_observation_before_the_batch():
    for age, allowed in ((None, False), (seconds(30), True),
                         (seconds(30) + timedelta(microseconds=1), False),
                         (-timedelta(microseconds=1), False)):
        with universe_fixture() as env:
            c = build_universe(env)
            c.bootstrap()
            at = env.fake.now
            c._observation = None if age is None else replace(c._observation, asof=at - age)
            calls = []

            def run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof):
                calls.append((positions, positions_asof, now))
                assert timedelta(0) <= now - positions_asof <= seconds(30)
                return "BATCH"

            with patch.object(C, "run_batch", run_batch), patch.object(c, "_clock", lambda: at):
                call = lambda: c.odds_batch("TEMPLATE", lambda markets, **kwargs: {"bars": markets})
                if allowed:
                    assert call() == "BATCH" and len(calls) == 1
                else:
                    refused(call, "COORDINATOR_PREPARATION_ACCOUNT_NOT_CURRENT")
                    assert calls == []


def test_odds_reads_bars_then_one_fresh_observation_then_the_batch_clock():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        moments, latest, trace = [env.fake.now], [c._observation], []
        start = moments[0]

        def clock():
            trace.append("clock")
            return moments[0]

        def read_bars(markets, *, now, clock):
            assert now == start and markets == (BTC, XRP)
            trace.append("bars-start")
            moments[0] += seconds(45)        # ordinary multi-coin paging can exceed the 30-second account window
            latest[0] = replace(latest[0], asof=moments[0])  # another monitor publishes during the slow read
            trace.append("bars-done")
            return {"bars": markets}

        def observation(instance):
            assert instance is c and trace[-1] == "bars-done"
            trace.append("observation")
            return latest[0]

        def run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof):
            trace.append("batch")
            assert now == start + seconds(45) == positions_asof
            assert positions is latest[0].positions
            return "BATCH"

        with patch.object(C, "run_batch", run_batch), patch.object(c, "_clock", clock), \
                patch.object(C.Coordinator, "_observation", property(observation), create=True):
            assert c.odds_batch("TEMPLATE", read_bars) == "BATCH"
        assert trace == ["clock", "bars-start", "bars-done", "observation", "clock", "batch"]


def test_odds_refuses_a_seoul_day_change_during_bars_even_with_fresh_positions():
    with universe_fixture() as env:
        c = build_universe(env)
        c.bootstrap()
        moments = [env.fake.now.astimezone(C.KST).replace(hour=23, minute=59, second=50, microsecond=0)]
        c._observation = replace(c._observation, asof=moments[0])
        batch_calls = []

        def read_bars(markets, *, now, clock):
            assert now == moments[0]
            moments[0] += seconds(20)
            c._observation = replace(c._observation, asof=moments[0])
            return {"bars": markets}

        def run_batch(*args, **kwargs):
            batch_calls.append(kwargs)
            raise AssertionError("daily bars crossed the selection date")

        with patch.object(C, "run_batch", run_batch), patch.object(c, "_clock", lambda: moments[0]):
            refused(lambda: c.odds_batch("TEMPLATE", read_bars), "UNIVERSE_BATCH_CLOCK_INVALID")
        assert batch_calls == []
````
