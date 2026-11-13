"""Actual committed Runner consumer with temporary signatures and DryRunAdapter.

Continuous source/coverage is explicitly synthetic. Explicit reducing orders
use actual owner/gate/capability code and require no research issuer. A newly
evaluated and actually signed synthetic study reaches the actual fixed callback
through LiveHistory; other ticks retain the real missing-research refusal.
No fake verifier or registry entry manufactures an automatic-entry success.
"""
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, fields, replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_accounts.baseline_store import CheckpointStore
from execution_control import controller as C
from execution_control.controller import Controller
from execution_control.store import Journal
from execution_launch import runner as R
from execution_launch.baseline_head import BaselineHead
from execution_launch.continuous_guard_commit import GuardCheckpointStore
from execution_launch.profile import PolicyInputs, profile_contract_digest
from execution_launch.runner import EvidencePackage, Quote, Runner, Signal
from tests import compliance_fixtures as CF, control_committed_account as F
from tests.control_committed_completion import after_append, guard_files, restart as restart_controller
from tests.control_committed_observation import prior_stricter_floor, risk_rows
from tests.launch_profile import fixture_profile


def profile(e):
    values = {field.name: getattr(e.s.policy, field.name) for field in fields(PolicyInputs)
              if field.name != 'source_sha256'}
    return replace(fixture_profile(e.now), account_scope=F.GF.SCOPE,
                   policy=PolicyInputs(source_sha256='a' * 64, **values), instrument_rules=e.rules)


def build(e, **changes):
    args = dict(profile=e.profile, quote_provider=lambda _: e.quote, account_provider=e.provider,
                controller=e.controller, mode='rehearsal', isolated_state_root=e.home)
    return Runner(**(args | changes))


@contextmanager
def fixture(**kwargs):
    with F.fixture(**kwargs) as e:
        e.profile = profile(e)
        e.quote = Quote(venue='upbit', market='spot', symbol='KRW-BTC', bid=F.D(100), ask=F.D(101),
                        asof=e.now, source_sha256='c' * 64)
        e.signal = Signal(signal_id='explicit-reducing-fixture', action='exit',
                          quantity=F.D('0.1'), limit_price=F.D(100))
        e.runner = build(e)
        yield e


def creates(e):
    return tuple(request for request in e.adapter.requests if request.operation == 'create')


def exit_order(e):
    account = F.PF.read(e.s, e.provider, e.now).observation
    return e.runner._order(e.signal, account, e.now)


def prior_recorded_kill(home, key, start):
    """Retain actual kill/disarm records before the guard's owner observation.

    This fixture exercises replay of an already recorded restriction, not the
    Controller.kill command. The separate postcommit test exercises that command
    and confirms that its new owner epoch invalidates the old committed package.
    """
    rules = F.InstrumentRules(venue='upbit', market='spot', symbol='KRW-BTC',
        lot_size=F.D('0.1'), tick_size=F.D(1), min_quantity=F.D('0.1'), min_notional_krw=F.D(1),
        fee_fraction=F.D(0), asof=start, source_digest='a' * 64)
    configured = profile(SimpleNamespace(now=start, rules=rules, s=SimpleNamespace(policy=F.GF.policy())))
    session = 'launch-exit-' + profile_contract_digest(configured)[:24]
    with Journal().transaction() as tx:
        tx.append('kill', {'session_id': session, 'reason': 'fixture retained restriction'}, now=start)
    owner.append_system_entry('system_disarm', {'session_id': session,
        'reason': 'fixture retained restriction'}, start)


@contextmanager
def actual_reviewed_warmup_fixture():
    """New 100-unit study and real local history, with an actually signed review.

    The study's triangle and original orderbook receipts are deliberately
    synthetic. All evaluation, signing, verification, history issuance and
    callback execution remain actual implementations. No existing research
    result is retargeted to this account's capital, rules or scope.
    """
    import base64
    import hashlib
    import json
    from execution_accounts.quotes import to_runner_quote
    from execution_control.owner_authority import CurrentOwnerAuthority
    from execution_control.store import GENESIS
    from execution_launch import managed_behavior as B, strategy as E, study as S
    from execution_launch.capture_v2 import capture_json_v2
    from execution_launch.driver import DeploymentWindow, describe_fixed_driver, make_fixed_carry_driver
    from execution_launch.live_history import HistoryChain, LiveHistory
    from execution_launch.program import parameters_json
    from execution_launch.review_auth import ReviewVerifiers, review_body, review_signing_bytes
    from execution_launch.review_request import build_review_request
    from tests import launch_study as SF
    from tests.launch_capture import book

    with fixture(flat_cash=True) as e:
        capture_end = e.now - timedelta(seconds=60)
        capture_start = capture_end - SF.BAR * 500
        preregistered_at = capture_start - timedelta(days=1)
        template = SF.template(500, schema_version=2, preregistered_at=preregistered_at,
            capture_start=capture_start, capture_end=capture_end,
            evaluator_revision=B.CARRY_EVALUATOR_REVISION, behavior_revision=B.BEHAVIOR_REVISION,
            terminal_accounting=B.TERMINAL_ACCOUNTING, management_behavior_sha256=B.behavior_digest())
        # Rules are observed at registration for plan preflight, then genuinely
        # current fixture rules are used for evaluation/runtime. Terms are exact.
        historical_profile = replace(e.profile, instrument_rules=replace(e.rules, asof=preregistered_at))
        plan = S.build_study_plan(historical_profile, (SF.A,), template=template,
            plan_id='committed-runner-actual-study', asset='BTC', risk_group='crypto-btc')
        source = SF.Driver(plan)
        def capture_clock():
            elapsed = source.clock[0] - source.start
            if elapsed >= timedelta(0) and elapsed % SF.BAR < timedelta(seconds=1):
                source.clock[0] += timedelta(microseconds=1000)
            return source.clock[0]
        capture = S.run_capture(plan, book_source=source.read, clock=capture_clock,
            wait_until=source.wait_until, record=source.lines.append)
        assert capture.complete and capture.slots_recorded == 501, capture.reason
        candidate = plan.candidates[0]
        protocol, program = candidate.protocol, candidate.program
        raw = capture_json_v2(capture.archives[0]).encode('ascii')
        result = E.evaluate_capture_json(protocol, raw, e.rules, now=e.now)
        e.profile = replace(e.profile, strategy_id=program.strategy_id,
                            strategy_code_sha256=protocol.strategy_code_sha256)
        assert protocol.initial_cash_quote == e.profile.policy.initial_equity == F.D(100)
        assert protocol.profile_contract_digest == profile_contract_digest(e.profile)
        artifact = S._fixed_file(S.PROGRAM_SOURCE)
        window = DeploymentWindow(deployment_id='committed-runner-actual-history',
                                  start=e.now, end=e.now+SF.BAR*3)
        history_head = BaselineHead(root=e.s.bhead._root, name='committed-runner-history',
                                    chain=HistoryChain(root=e.home, window=window))
        history_head.initialize_reviewed_head(GENESIS)
        history_clock = [e.now-timedelta(seconds=1)]
        history = LiveHistory(program, protocol, e.profile, window=window, root=e.home,
                              clock=lambda: history_clock[0], trusted_head=history_head)
        driver = make_fixed_carry_driver(program, protocol, e.profile, window=window,
            history_provider=history.provider, history_verifier=history.verifier, program_artifact=artifact)
        identity = history.bind(driver)
        authority = CurrentOwnerAuthority(clock=e.clock)
        actual_owner = authority(e.now)
        request = build_review_request(e.profile, protocol, result, now=e.now,
                                      program_artifact=artifact, parameters_json=parameters_json(program))
        body = review_body(request, asdict(identity), deployment_code_hash=actual_owner.context.code_hash,
            audit_sha256=hashlib.sha256(b'synthetic committed-runner study; no production profitability claim').hexdigest(),
            owner_fingerprint=actual_owner.context.owner.fingerprint, issued_at=e.now,
            expires_at=e.now+timedelta(hours=1))
        document = json.dumps({'body': body, 'signature_b64':
            base64.b64encode(e.key.sign(review_signing_bytes(body))).decode('ascii')})
        verifiers = ReviewVerifiers(document, clock=e.clock, authority_provider=authority,
            approved_history_provider=history.provider, approved_history_verifier=history.verifier)
        account = F.PF.read(e.s, e.provider, e.now).observation
        assert not account.holdings and account.settled_cash_krw[('upbit', F.GF.SCOPE)] == F.D(100)
        original_book = book(e.now, received_delta=0, asof_delta=-1, bid=100, ask=102)
        history_clock[0] = e.now
        recorded_head = history.record_slot(original_book, account)
        assert history_head.read() == recorded_head
        e.quote = to_runner_quote(original_book, now=e.now)
        e.evidence = EvidencePackage(protocol=protocol, result=result, review_verifier=verifiers.source)
        e.driver, e.history, e.history_head, e.review = driver, history, history_head, verifiers
        e.research_capture, e.research_plan = capture, plan
        e.runner = build(e, evidence=e.evidence, driver=driver,
                        implementation_verifier=verifiers.implementation, clock=e.clock)
        assert describe_fixed_driver(driver) == identity
        yield e


def test_constructor_requires_exact_committed_rehearsal_without_touching_control():
    with fixture() as e:
        before = F.rows(e)
        for mode in ('observe', 'controlled'):
            F.refused(lambda mode=mode: build(e, mode=mode), 'RUNNER_COMMITTED_REHEARSAL_REQUIRED')
        F.refused(lambda: build(e, account_provider=SimpleNamespace(read=e.provider.read)),
                  'RUNNER_PROVIDERS_REQUIRED')
        F.refused(lambda: build(e, isolated_state_root=None), 'RUNNER_ISOLATED_STATE_REQUIRED')
        F.refused(lambda: build(e, isolated_state_root=e.home/'different'), 'RUNNER_REHEARSAL_STATE_MISMATCH')
        F.refused(lambda: build(e, profile=replace(e.profile, policy=replace(e.profile.policy,
            first_day_loss_budget=F.D(9)))), 'RUNNER_CONTROLLER_POLICY_MISMATCH')
        different = F.PF.provider(e.s, e.package, e.receipt)
        F.refused(lambda: build(e, account_provider=different), 'RUNNER_CONTROLLER_PROVIDER_MISMATCH')
        real_adapter = e.controller.adapters['upbit']
        e.controller.adapters['upbit'] = SimpleNamespace(dispatch=real_adapter.dispatch)
        F.refused(lambda: build(e), 'RUNNER_REHEARSAL_REQUIRES_DRY_ADAPTERS')
        e.controller.adapters['upbit'] = real_adapter
        assert F.rows(e) == before and not e.adapter.requests


def test_tick_consumes_one_actual_pair_preserves_daily_stop_and_real_research_refusal():
    with fixture(daily_stopped=True) as e:
        actual, pairs, consumed = Controller.observe_committed, [], []
        def paired(controller, **kwargs):
            value = actual(controller, **kwargs)
            pairs.append(value)
            return value
        original = e.runner._observations
        def observations(*args, **kwargs):
            value = original(*args, **kwargs)
            consumed.append((kwargs['committed'], value[1]))
            return value
        before = guard_files(e)
        with patch.object(Controller, 'observe_committed', paired), \
             patch.object(e.controller, 'observe_committed', side_effect=AssertionError('instance replacement')), \
             patch.object(e.controller, 'observe', side_effect=AssertionError('second risk observe')), \
             patch.object(e.controller, 'read_committed_account', side_effect=AssertionError('second account route')), \
             patch.object(e.runner, '_observations', observations):
            report = e.runner.tick(now=e.now)
        assert report.status == 'blocked' and report.reasons == ('RUNNER_STRATEGY_EVIDENCE_REQUIRED',)
        assert len(pairs) == len(consumed) == 1 and consumed[0][0] is pairs[0]
        assert consumed[0][1] is pairs[0].account is pairs[0].committed.observation
        assert pairs[0].committed.daily_stopped and pairs[0].risk.new_entry_blocked
        assert 'PERSISTENT_DAILY_STOP' in pairs[0].risk.reasons
        assert pairs[0].account.asof == e.now and len(risk_rows(e)) == 1
        assert guard_files(e) == before and not e.adapter.requests


def test_explicit_exit_consumes_one_actual_capability_and_duplicate_restart_never_resends():
    with fixture() as e:
        before, risk_before = guard_files(e), risk_rows(e)
        actual_read = Controller.read_committed_account
        with patch.object(C, '_issue', wraps=C._issue) as issued, \
             patch.object(Controller, 'read_committed_account', wraps=actual_read) as read, \
             patch.object(e.controller, 'read_committed_account', side_effect=AssertionError('instance replacement')), \
             patch.object(e.controller, 'observe_committed', side_effect=AssertionError('entry observation')), \
             patch.object(Controller, '_snapshot_risk', side_effect=AssertionError('new risk write')), \
             patch.object(Controller, '_risk_view', side_effect=AssertionError('new risk gate')):
            first = e.runner.submit_exit(e.signal, now=e.now)
            assert first.status == 'ACKNOWLEDGED' and issued.call_count == 1 and read.call_count == 1
            assert read.call_args.kwargs['session_id'] == e.runner._exit_session_id()
            again = e.runner.submit_exit(e.signal, now=e.now)
            assert again == first and issued.call_count == 1
        e.controller = restart_controller(e)
        e.runner = build(e)
        assert e.runner.submit_exit(e.signal, now=e.now) == first
        assert len(creates(e)) == 1 and risk_rows(e) == risk_before and guard_files(e) == before


def test_daily_stop_permanent_halt_kill_and_stopped_runner_preserve_independent_exit():
    for options in ({'daily_stopped': True}, {'prices': ('110', '105', '115')}):
        with fixture(**options, configure=prior_recorded_kill, control_prefix=True) as e:
            kills = [row for row in F.rows(e) if row['kind'] == 'kill']
            assert len(kills) == 1 and kills[0]['data']['session_id'] == e.runner._exit_session_id()
            e.runner.stop()
            # Expired/unusable research is not examined by the independent exit.
            e.runner.evidence = EvidencePackage(protocol=SimpleNamespace(capture_end=e.now-timedelta(days=2)),
                                                result=None)
            before = risk_rows(e)
            with patch.object(R, '_assess', side_effect=AssertionError('research exit gate')), \
                 patch.object(Controller, '_snapshot_risk', side_effect=AssertionError('entry risk write')), \
                 patch.object(C, '_issue', wraps=C._issue) as issued:
                state = e.runner.submit_exit(e.signal, now=e.now)
                assert state.status == 'ACKNOWLEDGED' and issued.call_count == 1
            assert e.runner.stopped and risk_rows(e) == before and len(creates(e)) == 1


def test_actual_kill_after_commit_requires_a_fresh_owner_epoch_before_reducing_exit():
    with fixture(daily_stopped=True) as e:
        old_head = e.package['owner_after'].owner_head_sha256
        assert e.controller.kill(e.runner._exit_session_id(), reason='fixture safety stop', now=e.now)
        observation = F.PF.read(e.s, e.provider, e.now).observation
        current = owner.load_context(e.now, observation.positions, session_id=e.runner._exit_session_id())
        assert current.owner.head[1] != old_head
        before = F.rows(e)
        assert any(row['kind'] == 'kill' for row in before)
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            F.refused(lambda: e.runner.submit_exit(e.signal, now=e.now),
                      'COMMITTED_ACCOUNT_OWNER_EPOCH_CHANGED')
            assert issued.call_count == 0
        assert F.rows(e) == before and not creates(e)


def test_precommit_floor_above_endpoint_does_not_create_an_exit_blocking_owner_halt():
    with fixture(configure=prior_stricter_floor, control_prefix=True) as e:
        before, owner_before = risk_rows(e), owner.log_path().read_bytes()
        actual = Controller.read_committed_account
        observations = []
        def paired(controller, **kwargs):
            value = actual(controller, **kwargs)
            observations.append(value)
            return value
        with patch.object(Controller, 'read_committed_account', paired), \
             patch.object(Controller, '_snapshot_risk', side_effect=AssertionError('new floor halt')):
            state = e.runner.submit_exit(e.signal, now=e.now)
        assert state.status == 'ACKNOWLEDGED' and len(creates(e)) == 1
        assert len(observations) == 1 and observations[0].risk is None
        assert observations[0].account.risk.approved_effective_floor == F.D(120)
        assert observations[0].account.risk.equity == F.D(101)
        assert risk_rows(e) == before and owner.log_path().read_bytes() == owner_before
        assert not any(row['kind'] == 'halt' for row in F.rows(e))


def test_quote_delay_cannot_retimestamp_original_account_or_create_after_freshness_expires():
    with fixture() as e:
        actual, reads = Controller.read_committed_account, []
        def paired(controller, **kwargs):
            view = actual(controller, **kwargs)
            reads.append(view)
            return view
        def slow_quote(_):
            e.clock_cell[0] = e.now + timedelta(seconds=31)
            return e.quote
        e.runner.quote_provider = slow_quote
        with patch.object(Controller, 'read_committed_account', paired), \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            F.refused(lambda: e.runner.submit_exit(e.signal, now=e.now))
            assert issued.call_count == 0
        assert len(reads) == 1 and reads[0].account.asof == reads[0].completed_at == e.now
        assert not creates(e) and not any(row['kind'] == 'reserved' for row in F.rows(e))


def test_quote_age_is_checked_at_actual_completed_read_time_without_retimestamping():
    with fixture() as e:
        e.quote = replace(e.quote, asof=e.now-timedelta(seconds=5))
        actual, loaded = owner.load_context, []
        def slow(*args, **kwargs):
            value = actual(*args, **kwargs)
            loaded.append(value.owner.head)
            e.clock_cell[0] = e.now + timedelta(seconds=20)
            return value
        before = F.rows(e)
        with patch.object(owner, 'load_context', slow), patch.object(C, '_issue', wraps=C._issue) as issued:
            F.refused(lambda: e.runner.submit_exit(e.signal, now=e.now), 'RUNNER_QUOTE_STALE_OR_FUTURE')
            assert issued.call_count == 0
        assert len(loaded) >= 2 and e.quote.asof == e.now-timedelta(seconds=5)
        assert F.rows(e) == before and not creates(e)


def test_owner_or_guard_head_change_after_paired_read_is_rechecked_before_reservation():
    for change in ('owner', 'guard'):
        with fixture() as e:
            def changed(_):
                if change == 'owner':
                    CF.sign(e.key, 'age_of_majority', {'birth_date': '2000-01-01', 'evidence': 'fixture'},
                            M.iso_utc(e.now))
                else:
                    (e.s.ghead._dir/'head.json').write_bytes(b'{invalid fixture head')
                return e.quote
            e.runner.quote_provider = changed
            with patch.object(C, '_issue', wraps=C._issue) as issued:
                F.refused(lambda: e.runner.submit_exit(e.signal, now=e.now))
                assert issued.call_count == 0
            assert not creates(e) and not any(row['kind'] == 'reserved' for row in F.rows(e))


def test_quote_callback_cannot_swap_provider_controller_or_mode_after_actual_read():
    for change in ('provider', 'controller', 'mode'):
        with fixture() as e:
            def changed(_):
                if change == 'provider':
                    e.runner.account_provider = lambda _: None
                elif change == 'controller':
                    e.runner.controller = restart_controller(e)
                else:
                    e.runner.mode = 'controlled'
                return e.quote
            e.runner.quote_provider = changed
            with patch.object(C, '_issue', wraps=C._issue) as issued:
                code = ('RUNNER_COMMITTED_REHEARSAL_REQUIRED' if change == 'mode'
                        else 'RUNNER_CONTROLLER_PROVIDER_MISMATCH')
                F.refused(lambda: e.runner.submit_exit(e.signal, now=e.now), code)
                assert issued.call_count == 0
            assert not creates(e) and not any(row['kind'] == 'reserved' for row in F.rows(e))


def test_oversized_or_nonexit_signal_never_turns_account_view_into_permission():
    with fixture() as e:
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            F.refused(lambda: e.runner.submit_exit(replace(e.signal, action='entry'), now=e.now),
                      'RUNNER_EXIT_REQUIRED')
            F.refused(lambda: e.runner.submit_exit(replace(e.signal, quantity=F.D(2)), now=e.now))
            assert issued.call_count == 0
        assert not creates(e) and not any(row['kind'] == 'reserved' for row in F.rows(e))


def test_reserved_crash_reconciles_local_cancel_before_new_tick_observation():
    with fixture() as e:
        order = exit_order(e)
        e.controller.reserve(order, e.rules, session_id=e.runner._exit_session_id(), now=e.now)
        e.controller = restart_controller(e)
        e.runner = build(e)
        events, actual = [], Controller.observe_committed
        def paired(controller, **kwargs):
            events.append(e.controller.states()[0].status)
            return actual(controller, **kwargs)
        with patch.object(Controller, 'observe_committed', paired):
            report = e.runner.tick(now=e.now)
        assert events == ['CANCELLED_LOCAL'] and e.controller.states()[0].status == 'CANCELLED_LOCAL'
        assert report.reasons == ('RUNNER_STRATEGY_EVIDENCE_REQUIRED',) and not creates(e)
        assert e.runner.submit_exit(e.signal, now=e.now).status == 'CANCELLED_LOCAL'


def test_uncertain_send_restart_uses_status_only_and_another_exit_cannot_retry_create():
    with fixture() as e:
        e.adapter.results.append(TimeoutError('private fixture transport failure'))
        first = e.runner.submit_exit(e.signal, now=e.now)
        assert first.status == 'UNKNOWN' and len(creates(e)) == 1
        e.controller = restart_controller(e)
        e.runner = build(e)
        report = e.runner.tick(now=e.now)
        assert report.status == 'blocked' and e.adapter.requests[-1].operation == 'status'
        assert len(creates(e)) == 1
        assert e.runner.submit_exit(e.signal, now=e.now).client_id == first.client_id
        F.refused(lambda: e.runner.submit_exit(replace(e.signal, signal_id='different-exit'), now=e.now),
                  'RUNNER_OUTSTANDING_ORDERS')
        assert len(creates(e)) == 1


def test_missing_research_bad_quote_and_source_corruption_do_not_generate_an_emergency_sell():
    for fault in ('research', 'quote', 'source'):
        with fixture() as e:
            if fault == 'quote':
                e.quote = replace(e.quote, asof=e.now-timedelta(seconds=11))
            elif fault == 'source':
                (e.s.ghead._dir/'head.json').write_bytes(b'{invalid fixture head')
            with patch.object(C, '_issue', wraps=C._issue) as issued:
                result = e.runner.tick(now=e.now)
                assert result.status == 'blocked' and issued.call_count == 0
            assert not creates(e) and not any(row['kind'] == 'reserved' for row in F.rows(e))


def test_committed_exit_does_not_commit_advance_or_open_nested_journal_transactions():
    with fixture() as e:
        before = guard_files(e)
        with ExitStack() as stack:
            for cls, name in ((CheckpointStore, 'commit'), (GuardCheckpointStore, 'commit'),
                              (BaselineHead, 'compare_and_set'), (BaselineHead, 'initialize_reviewed_head')):
                stack.enter_context(patch.object(cls, name, side_effect=AssertionError('unexpected advancement')))
            state = e.runner.submit_exit(e.signal, now=e.now)
        assert state.status == 'ACKNOWLEDGED' and len(creates(e)) == 1 and guard_files(e) == before


def test_existing_callable_provider_still_has_independent_legacy_exit_route():
    with fixture() as e:
        observation = F.PF.read(e.s, e.provider, e.now).observation
        provider = lambda _: observation
        controller = Controller(journal=e.s.journal, account_provider=provider, policy=e.s.policy,
            adapters={'upbit': e.adapter}, session_provider=lambda _: None)
        legacy = build(e, account_provider=provider, controller=controller)
        with patch.object(controller, 'read_committed_account', side_effect=AssertionError('legacy paired read')):
            state = legacy.submit_exit(e.signal, now=e.now)
        assert state.status == 'ACKNOWLEDGED' and len(creates(e)) == 1


def test_actual_delayed_committed_reservation_stops_with_local_cancel_at_its_real_row_time():
    """Actual reserve -> stopped cleanup seam; not a fabricated strategy SELL tick."""
    with fixture() as e:
        order = exit_order(e)
        execution_now = e.now + timedelta(seconds=1)
        e.clock_cell[0] = execution_now
        actual_prepare = e.adapter.prepare
        def delayed(*args, **kwargs):
            request = actual_prepare(*args, **kwargs)
            e.clock_cell[0] = e.now + timedelta(seconds=2)
            return request
        before = guard_files(e)
        with patch.object(e.adapter, 'prepare', delayed), patch.object(C, '_issue', wraps=C._issue) as issued:
            reserved = e.controller.reserve(order, e.rules, session_id=e.runner._exit_session_id(),
                                            now=execution_now)
            assert reserved.status == 'RESERVED' and reserved.updated_at > execution_now > e.now
            e.runner.stop()
            with patch.object(e.controller, 'cancel', wraps=e.controller.cancel) as cancel:
                state = e.runner._cancel_stopped_reservation(reserved, requested_now=e.now,
                                                            execution_now=execution_now)
                assert cancel.call_args.kwargs['now'] == reserved.updated_at
            assert state.status == 'CANCELLED_LOCAL' and state.updated_at == reserved.updated_at
            assert e.controller.dispatch(order.client_id, now=state.updated_at).status == 'CANCELLED_LOCAL'
            assert issued.call_count == 0
        order_rows = [row for row in F.rows(e) if row['data'].get('client_id') == order.client_id]
        assert [row['kind'] for row in order_rows] == ['reserved', 'cancelled_local']
        assert e.runner.stopped and not e.adapter.requests and guard_files(e) == before


def test_stopped_cleanup_keeps_actual_legacy_requested_timestamp_semantics():
    """The extracted cleanup helper does not move legacy cancel to another clock."""
    with fixture() as e:
        observation = F.PF.read(e.s, e.provider, e.now).observation
        provider = lambda _: observation
        controller = Controller(journal=e.s.journal, account_provider=provider, policy=e.s.policy,
            adapters={'upbit': e.adapter}, session_provider=lambda _: None)
        legacy = build(e, account_provider=provider, controller=controller)
        order = legacy._order(e.signal, observation, e.now)
        reserved = controller.reserve(order, e.rules, session_id=legacy._exit_session_id(), now=e.now)
        requested, execution = e.now+timedelta(seconds=1), e.now+timedelta(seconds=2)
        legacy.stop()
        with patch.object(controller, 'cancel', wraps=controller.cancel) as cancel, \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            state = legacy._cancel_stopped_reservation(reserved, requested_now=requested,
                                                       execution_now=execution)
            assert cancel.call_args.kwargs['now'] == requested
            assert state.status == 'CANCELLED_LOCAL' and state.updated_at == requested
            assert issued.call_count == 0
        assert not e.adapter.requests


def test_actual_signed_research_history_and_fixed_driver_reach_warmup_hold_with_paired_account():
    with actual_reviewed_warmup_fixture() as e:
        actual, pairs = Controller.observe_committed, []
        def paired(controller, **kwargs):
            value = actual(controller, **kwargs)
            pairs.append(value)
            return value
        before, history_before = guard_files(e), e.history_head.read()
        assert e.driver.callback.seen == {}
        with patch.object(Controller, 'observe_committed', paired), \
             patch.object(R, 'DecisionInput', wraps=R.DecisionInput) as inputs, \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            result = e.runner.tick(now=e.now)
            assert result.status == 'hold' and result.reasons == (), result
            assert inputs.call_count == 1 and issued.call_count == 0
        assert result.decision_state == 'warmup' and result.decision_cause == 'insufficient_history'
        assert len(pairs) == 1 and inputs.call_args.kwargs['account'] is pairs[0].account
        assert inputs.call_args.kwargs['now'] == pairs[0].completed_at == e.now
        assert inputs.call_args.kwargs['quote'] is e.quote
        assert e.driver.callback.seen[e.now][1] == 1
        assert e.research_capture.complete and len(e.research_plan.candidates) == 1
        assert e.history_head.read() == history_before and guard_files(e) == before
        assert len(risk_rows(e)) == 1 and not creates(e)


def test_actual_local_no_send_rejection_maps_to_neutral_blocked_without_a_strategy_tick_claim():
    """Real late dispatch rejection -> pure display mapper, not a fabricated SELL callback."""
    with fixture() as e:
        with after_append(e, 'dispatching', lambda *_: e.clock_cell.__setitem__(
                0, e.now+timedelta(seconds=31))) as dispatch_rows, \
             patch.object(C, '_issue', wraps=C._issue) as issued:
            state = e.runner.submit_exit(e.signal, now=e.now)
            assert state.status == 'REJECTED' and issued.call_count == 0
        assert len(dispatch_rows) == 1 and not creates(e)
        rejected = [row for row in F.rows(e) if row['kind'] == 'rejected']
        assert len(rejected) == 1
        assert dict(rejected[0]['data']['metadata']) == {
            'tg_local_pre_send': 'not_called',
            'tg_local_reason': 'COMMITTED_COMPLETION_STALE',
            'tg_dispatch_row': dispatch_rows[0]['row_sha256'],
        }
        before = F.rows(e)
        report = e.runner._dispatch_tick_result(state, reconciled_orders=0,
            protective_action_needed=True, metadata=R._signal_metadata(e.signal))
        assert report.status == 'blocked' and report.reasons == ('RUNNER_ORDER_REJECTED',)
        assert report.order_status == 'REJECTED' and report.client_id == state.client_id
        assert report.protective_action_needed and report.reconciled_orders == 0
        assert report.decision_state is None and report.execution_block_reasons == ()
        assert F.rows(e) == before and not creates(e)


def test_actual_dry_rejection_is_neutral_but_ack_and_uncertain_dispatch_remain_submitted():
    from execution_orders.model import AdapterResult
    for response in ('rejected', 'acknowledged', 'unknown'):
        with fixture() as e:
            order = exit_order(e)
            if response == 'rejected':
                e.adapter.results.append(AdapterResult(status='rejected', code='fixture_rejection',
                                                       client_id=order.client_id))
            elif response == 'unknown':
                e.adapter.results.append(TimeoutError('fixture ambiguous transport outcome'))
            with patch.object(C, '_issue', wraps=C._issue) as issued:
                state = e.runner.submit_exit(e.signal, now=e.now)
                assert state.status == response.upper() and issued.call_count == 1
            assert len(creates(e)) == 1
            before = F.rows(e)
            report = e.runner._dispatch_tick_result(state, reconciled_orders=0,
                protective_action_needed=False, metadata=R._signal_metadata(e.signal))
            assert report.client_id == state.client_id and report.order_status == state.status
            expected = ('blocked', ('RUNNER_ORDER_REJECTED',)) if response == 'rejected' else ('submitted', ())
            assert (report.status, report.reasons) == expected
            assert F.rows(e) == before and len(creates(e)) == 1


def test_actual_legacy_rejection_keeps_existing_submitted_display_semantics():
    from execution_orders.model import AdapterResult
    with fixture() as e:
        observation = F.PF.read(e.s, e.provider, e.now).observation
        provider = lambda _: observation
        controller = Controller(journal=e.s.journal, account_provider=provider, policy=e.s.policy,
            adapters={'upbit': e.adapter}, session_provider=lambda _: None)
        legacy = build(e, account_provider=provider, controller=controller)
        order = legacy._order(e.signal, observation, e.now)
        e.adapter.results.append(AdapterResult(status='rejected', code='fixture_rejection',
                                               client_id=order.client_id))
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            state = legacy.submit_exit(e.signal, now=e.now)
            assert state.status == 'REJECTED' and issued.call_count == 1
        report = legacy._dispatch_tick_result(state, reconciled_orders=0,
            protective_action_needed=False, metadata=R._signal_metadata(e.signal))
        assert report.status == 'submitted' and report.reasons == ()
        assert report.order_status == 'REJECTED' and report.client_id == state.client_id
        assert len(creates(e)) == 1
