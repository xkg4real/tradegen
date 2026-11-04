"""Full runner lifecycle with invented paper data and temporary test signatures.

No credentials, real source review, live adapters, or real owner authorization.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from core.compliance import model as M
from execution_control.capability import digest
from execution_control.controller import Controller
from execution_control.risk import RiskPolicy
from execution_control.store import JournalError
from execution_launch.profile import profile_contract_digest, rule_terms_digest
from execution_launch.runner import (EvidencePackage, ImplementationReceipt, Quote, Runner,
    RunnerError, Signal, StrategyDriver, prepare_launch_session, program_digest)
from execution_launch.strategy import (capture_history_digests, register_protocol, run_paper_validation)
from execution_orders.model import AdapterResult
from tests import compliance_fixtures as F
from tests.control_session import signed_control, selected
from tests.launch_profile import fixture_profile
from tests.launch_strategy import fixture_capture, fixture_review

D = Decimal
_EVIDENCE = {}


def evidence_for(profile, now):
    key = (profile_contract_digest(profile), now)
    if key not in _EVIDENCE:
        p, bars, decisions, _, _, _, end = fixture_capture()
        delta = now-end
        p = replace(p, profile_contract_digest=key[0], strategy_code_sha256=profile.strategy_code_sha256,
            rule_terms_digest=rule_terms_digest(profile.instrument_rules), initial_cash_quote=profile.policy.initial_equity,
            preregistered_at=p.preregistered_at+delta, capture_start=p.capture_start+delta,
            capture_end=p.capture_end+delta)
        bars = tuple(replace(b, observed_at=b.observed_at+delta, received_at=b.received_at+delta,
            bid=b.bid*1000000, ask=b.ask*1000000, mark=b.mark*1000000) for b in bars)
        prefixes = capture_history_digests(bars)
        decisions = tuple(replace(d, decided_at=d.decided_at+delta,
                                  history_sha256=prefixes[d.bar_index]) for d in decisions)
        result = run_paper_validation(p, bars, decisions, profile.instrument_rules,
            registry=register_protocol(p), source_kind='prospective_paper_capture', now=now)
        _EVIDENCE[key] = EvidencePackage(protocol=p, result=result, review_verifier=fixture_review(now))
    return _EVIDENCE[key]


def implementation_review(now):
    def verify(binding, driver):
        return ImplementationReceipt(binding_digest=digest(binding), callback=driver.callback,
            audit_sha256='f'*64, reviewed_at=now, expires_at=now+timedelta(hours=1))
    return verify


def reject(call):
    try:
        call()
    except (ValueError, JournalError):
        return
    raise AssertionError('expected refusal')


@contextmanager
def runner_fixture(*, arm=True, prepare=True, mode='rehearsal', results=()):
    policy = RiskPolicy(version='fixture-v1', initial_equity=D('100000'),
        drawdown_activation_equity=D('800000'), positive_profit_loss_fraction=D('0.2'),
        peak_drawdown_fraction=D('0.25'), zero_profit_day_target_fraction=D('0.1'),
        first_day_loss_budget=D('10'), zero_profit_day_loss_budget=D('10'))
    with signed_control(prepare=False, arm=False, results=results, policy=policy) as env:
        env.signal = Signal(signal_id='fixed-decision', action='entry', quantity=env.order.quantity,
                            limit_price=env.order.limit_price)
        env.driver = StrategyDriver(callback=lambda observation, parameters:env.signal,
            artifact=b'fixture strategy artifact; synthetic audit only', parameters_json='{"window":20}')
        base = fixture_profile(env.now)
        env.profile = replace(base, account_scope='fixture-account', instrument_rules=env.rules,
            strategy_code_sha256=program_digest(env.driver),
            policy=replace(base.policy, initial_equity=policy.initial_equity,
                drawdown_activation_equity=policy.drawdown_activation_equity,
                zero_profit_day_loss_budget=policy.zero_profit_day_loss_budget))
        env.evidence = evidence_for(env.profile, env.now)
        env.review = implementation_review(env.now)
        env.launch = None
        if prepare:
            plan, inputs, seed = selected(env.now)
            env.launch = prepare_launch_session(profile=env.profile, evidence=env.evidence,
                driver=env.driver, implementation_verifier=env.review, journal=env.journal,
                selected_plan=plan, inputs=inputs, positions=env.observation.positions,
                now=env.now, selection_seed_hex=seed)
            env.prepared = env.launch.prepared
            env.session_id = env.prepared.session_id
            if arm:
                F.sign(env.key, 'session_armed', {'session_id':env.session_id}, M.iso_utc(env.now))
        env.quote = Quote(venue='upbit', market='spot', symbol='KRW-BTC', bid=D('99999999'),
                          ask=D('100000000'), asof=env.now, source_sha256='c'*64)
        env.runner = Runner(profile=env.profile, quote_provider=lambda now:env.quote,
            account_provider=env.controller.account_provider, evidence=env.evidence, driver=env.driver,
            implementation_verifier=env.review, mode=mode, controller=env.controller,
            launch_session=env.launch, isolated_state_root=env.home)
        yield env


def restart(env):
    provider = env.controller.account_provider
    env.controller = Controller(journal=env.journal, account_provider=provider, policy=env.policy,
        adapters={'upbit':env.adapter}, session_provider=lambda sid:env.prepared)
    return Runner(profile=env.profile, quote_provider=lambda now:env.quote, account_provider=provider,
        evidence=env.evidence, driver=env.driver, implementation_verifier=env.review,
        mode='rehearsal', controller=env.controller, launch_session=env.launch, isolated_state_root=env.home)


def creates(env):
    return [r for r in env.adapter.requests if r.operation == 'create']


def test_default_observation_and_missing_evidence_never_initialize_or_touch_control():
    with runner_fixture(mode='observe', prepare=False) as env:
        control = env.home/'execution-control'
        assert not control.exists()
        first = env.runner.tick(now=env.now)
        assert first.status == 'observed', first
        assert not control.exists() and not env.adapter.requests
        env.runner.evidence = None
        report = env.runner.tick(now=env.now)
        assert report.reasons == ('RUNNER_STRATEGY_EVIDENCE_REQUIRED',)
        assert not control.exists() and not env.adapter.requests


def test_bound_preparation_requires_real_owner_arm_and_runtime_object():
    with runner_fixture(arm=False) as env:
        report = env.runner.tick(now=env.now)
        assert report.status == 'blocked' and not creates(env)
    with runner_fixture() as env:
        env.prepared = replace(env.prepared)
        report = env.runner.tick(now=env.now)
        assert report.reasons == ('RUNNER_SESSION_BINDING_MISMATCH',) and not creates(env)
    with runner_fixture() as env:
        env.runner.launch_session = replace(env.launch, binding=replace(env.launch.binding,evidence_digest='1'*64))
        assert env.runner.tick(now=env.now).reasons == ('RUNNER_SESSION_BINDING_MISMATCH',)
        assert not creates(env)


def test_automatic_entry_duplicate_and_restart_never_repeat_create():
    with runner_fixture() as env:
        first = env.runner.tick(now=env.now)
        assert first.status == 'submitted' and first.order_status == 'ACKNOWLEDGED', first
        assert len(creates(env)) == 1
        repeat = env.runner.tick(now=env.now)
        assert repeat.status == 'existing' and len(creates(env)) == 1, repeat
        again = restart(env).tick(now=env.now)
        assert again.status == 'existing' and len(creates(env)) == 1, again
        env.signal = replace(env.signal, limit_price=D('100000001'))
        assert env.runner.tick(now=env.now).reasons == ('RUNNER_DECISION_CHANGED',)
        assert len(creates(env)) == 1


def test_unknown_send_restarts_with_status_only_and_never_retries_or_releases():
    with runner_fixture(results=(TimeoutError('private-wire-detail'),)) as env:
        first = env.runner.tick(now=env.now)
        assert first.order_status == 'UNKNOWN' and len(creates(env)) == 1, first
        again = restart(env).tick(now=env.now)
        assert again.order_status == 'UNKNOWN' and len(creates(env)) == 1, again
        env.signal = replace(env.signal, signal_id='another-decision')
        blocked = env.runner.tick(now=env.now)
        assert blocked.reasons == ('RUNNER_OUTSTANDING_ORDERS',), blocked
        assert 'private-wire-detail' not in repr(blocked) and len(creates(env)) == 1


def test_reserved_before_crash_is_cancelled_locally_and_not_dispatched():
    with runner_fixture() as env:
        order = env.runner._order(env.signal, env.observation)
        env.controller.reserve(order, env.rules, session_id=env.session_id, now=env.now)
        report = restart(env).tick(now=env.now)
        assert report.status == 'existing' and report.order_status == 'CANCELLED_LOCAL', report
        assert not env.adapter.requests


def test_partial_fill_reconciliation_keeps_residual_and_cancel_ack_is_not_terminal():
    from tests.control_controller import fill
    with runner_fixture() as env:
        first = env.runner.tick(now=env.now)
        state = env.controller.states()[0]
        partial = env.order.quantity/2
        env.observation = replace(env.observation, fills=(fill(env, order_id=state.venue_order_id, quantity=partial,
            fee_amount=D('5')),), reconciled_client_ids={first.client_id})
        env.adapter.results.append(AdapterResult(status='partial', code='fixture', client_id=first.client_id,
            venue_order_id=state.venue_order_id, filled_quantity=partial))
        report = env.runner.tick(now=env.now)
        assert report.order_status == 'PARTIAL', report
        env.runner.stop()
        env.runner.evidence = None
        canceled = env.runner.cancel(first.client_id, now=env.now)
        assert canceled.status in ('ACKNOWLEDGED', 'CANCEL_REQUESTED', 'PARTIAL')
        assert canceled.filled_quantity == partial and len(creates(env)) == 1
        assert env.controller.states()[0].status not in ('CANCELED', 'FILLED')


def test_expired_research_and_stop_preserve_explicit_verified_exit():
    for fallback in (False, True):
        with runner_fixture() as env:
            env.runner.stop(); env.runner.evidence = None
            if fallback:
                env.runner.launch_session = None
            env.observation = replace(env.observation,
                positions=replace(env.observation.positions, holdings={('upbit','BTC'):0.001}),
                holdings={('upbit','fixture-account','spot','KRW-BTC'):D('0.001')})
            signal = replace(env.signal, action='exit')
            state = env.runner.submit_exit(signal, now=env.now)
            assert state.status == 'ACKNOWLEDGED' and len(creates(env)) == 1
            assert env.runner.submit_exit(signal, now=env.now) == state
            assert len(creates(env)) == 1


def test_strategy_exit_tick_keeps_nonempty_owner_context_without_launch_session():
    with runner_fixture() as env:
        env.runner.launch_session = None
        env.observation = replace(env.observation,
            positions=replace(env.observation.positions, holdings={('upbit','BTC'):0.001}),
            holdings={('upbit','fixture-account','spot','KRW-BTC'):D('0.001')})
        env.signal = replace(env.signal, action='exit')
        report = env.runner.tick(now=env.now)
        assert report.status == 'submitted' and report.order_status == 'ACKNOWLEDGED', report
        assert len(creates(env)) == 1


def test_strategy_receipt_quote_staleness_and_provider_errors_fail_closed():
    with runner_fixture(mode='observe', prepare=False) as env:
        env.runner.implementation_verifier = lambda binding, driver:True
        assert env.runner.tick(now=env.now).reasons == ('RUNNER_IMPLEMENTATION_REVIEW_UNVERIFIED',)
        env.runner.implementation_verifier = env.review
        env.quote = replace(env.quote, asof=env.now-timedelta(seconds=11))
        assert env.runner.tick(now=env.now).reasons == ('RUNNER_QUOTE_STALE_OR_FUTURE',)
        def unavailable(now):
            raise RuntimeError('private-account-response')
        env.runner.quote_provider = unavailable
        report = env.runner.tick(now=env.now)
        assert report.reasons == ('RUNNER_DEPENDENCY_REFUSED',)
        assert 'private-account-response' not in repr(report) and not env.adapter.requests


def test_explicit_rehearsal_rejects_non_dry_adapter_and_wrong_isolation():
    with runner_fixture() as env:
        env.controller.adapters['upbit'] = object()
        reject(env.runner._controller_boundary)
    with runner_fixture() as env:
        reject(lambda:Runner(profile=env.profile, quote_provider=lambda now:env.quote,
            account_provider=env.controller.account_provider, mode='rehearsal', controller=env.controller,
            isolated_state_root=env.home/'different'))


def test_scheduler_is_bounded_stoppable_and_clock_rollback_blocks():
    with runner_fixture(mode='observe', prepare=False) as env:
        consumed = []
        def stamps():
            for _ in range(5):
                consumed.append(1)
                yield env.now
        assert len(env.runner.run(stamps(), max_steps=2)) == 2 and len(consumed) == 2
        assert env.runner.tick(now=env.now-timedelta(seconds=1)).reasons == ('RUNNER_CLOCK_ROLLBACK',)
        env.runner.stop()
        assert env.runner.run(stamps(), max_steps=2) == () and len(consumed) == 2
        assert env.runner.tick(now=env.now).status == 'stopped'
        assert not env.adapter.requests


def test_research_starting_capital_cannot_be_changed_by_matching_profile_hash():
    with runner_fixture(mode='observe', prepare=False) as env:
        env.runner.evidence = replace(env.evidence,
            protocol=replace(env.evidence.protocol, initial_cash_quote=D('1000000')))
        assert env.runner.tick(now=env.now).reasons == ('RUNNER_RESEARCH_CAPITAL_MISMATCH',)
        assert not env.adapter.requests


def test_read_only_states_never_initialize_repair_or_mutate_journal():
    with signed_control(prepare=False) as env:
        reject(env.controller.states)
        assert not (env.home/'execution-control').exists()
    with signed_control() as env:
        root = env.home/'execution-control'
        paths = tuple(root.iterdir())
        before = {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
        assert env.controller.states() == ()
        assert before == {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in paths}
        journal = root/'journal.jsonl'
        journal.write_bytes(journal.read_bytes()+b'torn')
        damaged = journal.read_bytes()
        reject(env.controller.states)
        assert journal.read_bytes() == damaged
