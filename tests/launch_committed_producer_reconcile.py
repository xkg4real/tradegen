"""Actual retained successor reconciliation in an isolated DryRun composition.

GET replies, recorder coverage and the initial account anchor are synthetic.
Capture parsing, archive/backup reads, signed temporary owner logs, guard math,
Journal/heads, publication and Controller status capabilities are real. These
tests do not prove a production source issuer, native restart or live trading.
"""
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as M
from execution_control import controller as C
from execution_launch import committed_account as P
from execution_launch import committed_startup as S
from execution_launch import guard_capture_archive as CA
from execution_launch import guard_generation_archive as A
from tests import compliance_fixtures as CF
from tests import launch_guard_capture_material as I
from tests import launch_guard_generation_archive as F
from tests import launch_committed_startup as T
from tests import launch_committed_startup_integration as V


def initialized(e):
    app = T.startup(e)
    result = app.reconcile(e.input.archive_digest, e.completion.archive_digest)
    assert result.status == 'RECONCILED' and result.execution_ready is False
    return app


def observed(app, retained, completed):
    return app._inspect(retained.archive_digest, completed.archive_digest)[0]


def durable(e):
    return (e.guard_head.read(), e.baseline_head.read(),
            e.guard_store.load(expected_head=e.guard_head.read()),
            e.baseline_store.load(expected_head=e.baseline_head.read()),
            e.journal.snapshot())


def successor(e, app, *, publish=True):
    """Collect/retain/commit a real second interval; never rewrite issued data.

The first fixture uses a stationary clock so its actual owner-after observation
is also an eligible original observation at the next interval's opening. The
new source remains explicitly synthetic and its path starts at the actual
committed predecessor. No callback returns an invented successful projection.
"""
    old = e.package
    guard_head, baseline_head = e.guard_head.read(), e.baseline_head.read()
    previous = e.baseline_store.load(expected_head=baseline_head)
    guard = e.guard_store.load(expected_head=guard_head)
    rows = e.journal.snapshot()
    control_head = rows[-1]['row_sha256']
    assert old['owner_after'].observed_at == previous.asof
    env = SimpleNamespace(state=previous, home=e.home, exchange=e.env.exchange, fees=e.env.fees)
    captured = I.capture(env, step_ms=0, stream_epoch=old['path'].stream_epoch,
                         first_sequence=guard.next_sequence)
    archive = CA.archive_guard_capture_packet(e.store, captured.staged, previous)
    replay = CA.replay_guard_capture_archive(e.store, archive.archive_digest,
        expected_previous_state_sha256=previous.state_digest)
    material = replay.material
    now = captured.staged.observed_at
    e.clock_cell[0] = now
    after = F._claim(material.account_capture.endpoint_accounts[0],
                     material.interval.equity_krw, now, e.contexts)
    package = dict(baseline_before=previous, policy=e.policy,
        owner_before=old['owner_after'], owner_after=after, path=material.path,
        valuation_inputs=material.valuation_inputs, account_capture=material.account_capture,
        coverage=material.coverage, interval=material.interval, now=now)
    retained = A.retain_guard_input(e.store, archive.archive_digest, package,
        expected_guard_head=guard_head, expected_baseline_head=baseline_head,
        expected_control_head=control_head)
    completed = app.commit_input(retained.archive_digest)
    projection = None
    if publish:
        with e.journal.transaction() as tx:
            projection = P.CommittedAccountProvider.publish_committed(app.provider, package,
                completed.record.receipt, expected_guard_head=guard_head,
                expected_baseline_head=baseline_head, expected_control_head=control_head,
                now=now, transaction=tx)
    return SimpleNamespace(input=retained, completion=completed, package=package,
        inspection=observed(app, retained, completed), projection=projection, now=now)


def test_actual_same_generation_private_reconciliation_preserves_runtime_and_durable_state():
    with F.fixture(completed=True) as e:
        app = initialized(e)
        pins, binding = app._runtime_pins, app._binding
        actual = observed(app, e.input, e.completion)
        before = durable(e)
        with V.read_only_boundaries():
            result = app._reconcile_runtime(actual, e.input, e.completion)
        assert result.status == 'RECONCILED' and result.attempted_reconciliations == 0
        assert durable(e) == before and app._binding == binding
        assert all(left is right for left, right in zip(app._runtime_pins, pins))
        assert app.runner.quote_provider is S._no_quote
        assert result.inspection.asof == e.package['interval'].end
        assert not result.execution_ready and not result.source_authenticated


def test_actual_published_successor_reuses_runtime_without_retargeting_initial_binding():
    with F.fixture(completed=True, capture_options={'step_ms': 0}) as e:
        app = initialized(e)
        pins, binding = app._runtime_pins, app._binding
        next_unit = successor(e, app)
        assert next_unit.projection.transaction_id != e.receipt.transaction_id
        before = durable(e)
        with V.read_only_boundaries():
            result = app._reconcile_runtime(next_unit.inspection, next_unit.input, next_unit.completion)
        assert result.status == 'RECONCILED'
        assert result.inspection.transaction_id == next_unit.completion.record.receipt.transaction_id
        assert result.inspection.asof == next_unit.package['interval'].end
        assert next_unit.projection.observation.asof == next_unit.package['interval'].end
        assert result.inspection.asof > e.package['interval'].end
        assert app._binding == binding and app.runner.quote_provider is S._no_quote
        assert all(left is right for left, right in zip(app._runtime_pins, pins))
        assert durable(e) == before
        # The original public entry still cannot bind itself to different IDs.
        T.refused(lambda: app.reconcile(next_unit.input.archive_digest,
            next_unit.completion.archive_digest), 'STARTUP_BINDING_CHANGED')
        assert app._binding == binding and durable(e) == before


def test_committed_but_unpublished_successor_cannot_substitute_a_restored_candidate():
    with F.fixture(completed=True, capture_options={'step_ms': 0}) as e:
        app = initialized(e)
        pins, binding = app._runtime_pins, app._binding
        next_unit = successor(e, app, publish=False)
        before = durable(e)
        with (patch.object(C.Controller, 'cancel', side_effect=AssertionError('premature cancellation')),
              patch.object(C.Controller, 'reconcile', side_effect=AssertionError('premature status'))):
            T.refused(lambda: app._reconcile_runtime(next_unit.inspection, next_unit.input,
                next_unit.completion), 'STARTUP_CURRENT_AUTHORITY_REFUSED')
        assert durable(e) == before and app._binding == binding
        assert all(left is right for left, right in zip(app._runtime_pins, pins))
        assert not app.controller.adapters['upbit'].requests


def test_caller_fresh_flag_cannot_refresh_actual_stale_endpoint():
    with F.fixture(completed=True) as e:
        app = initialized(e)
        actual = observed(app, e.input, e.completion)
        e.clock_cell[0] = e.package['interval'].end + timedelta(seconds=30, microseconds=1)
        claimed = replace(actual, current_status='FRESH', inspected_at=e.clock(), asof=e.clock())
        before = durable(e)
        with patch.object(C.Controller, 'read_committed_account',
                          side_effect=AssertionError('stale data must not authorize')):
            result = app._reconcile_runtime(claimed, e.input, e.completion)
        assert result.status == 'BLOCKED' and result.reason == 'STARTUP_STALE'
        assert result.inspection.asof == e.package['interval'].end
        assert durable(e) == before


def test_caller_record_contents_are_discarded_and_actual_archives_supply_the_facts():
    with F.fixture(completed=True) as e:
        app = initialized(e)
        actual = observed(app, e.input, e.completion)
        calls = []
        class Trap:
            def __getattr__(self, name):
                calls.append(name)
                raise AssertionError('caller contents are not authority')
        passed_input = replace(e.input, package=Trap(), record=Trap())
        passed_completion = replace(e.completion, record=Trap(), retained_input=Trap())
        result = app._reconcile_runtime(replace(actual, current_status='REFUSED',
            reason='invented caller refusal'), passed_input, passed_completion)
        assert result.status == 'RECONCILED' and result.inspection.current_status == 'FRESH'
        assert result.inspection.reason == '' and calls == []


def test_wrong_caller_transaction_or_record_digest_is_only_a_restrictive_mismatch():
    with F.fixture(completed=True) as e:
        app = initialized(e)
        actual = observed(app, e.input, e.completion)
        before = durable(e)
        for args in ((replace(actual, transaction_id='f'*64), e.input, e.completion),
                     (actual, replace(e.input, record_sha256='f'*64), e.completion),
                     (actual, e.input, replace(e.completion, record_sha256='f'*64))):
            with patch.object(C.Controller, 'read_committed_account',
                              side_effect=AssertionError('mismatch before current-owner work')):
                T.refused(lambda: app._reconcile_runtime(*args), 'STARTUP_BINDING_CHANGED')
        assert durable(e) == before


def test_exact_input_type_is_checked_before_accessing_foreign_properties():
    with F.fixture(completed=True) as e:
        app = initialized(e)
        called = []
        class Trap:
            @property
            def input_archive_digest(self):
                called.append(True)
                raise AssertionError('foreign input must not be read')
        T.refused(lambda: app._reconcile_runtime(Trap(), e.input, e.completion), 'STARTUP_INPUT_INVALID')
        assert called == []


def test_private_entry_requires_existing_runtime_and_serializes_with_public_operations():
    with F.fixture(completed=True) as e:
        app = T.startup(e)
        actual = observed(app, e.input, e.completion)
        T.refused(lambda: app._reconcile_runtime(actual, e.input, e.completion), 'STARTUP_DEPENDENCY_CHANGED')
        app.reconcile(e.input.archive_digest, e.completion.archive_digest)
        before = durable(e)
        assert app._work.acquire(blocking=False)
        try:
            with patch.object(app, '_inspect', side_effect=AssertionError('contending operation must not read')):
                T.refused(lambda: app._reconcile_runtime(actual, e.input, e.completion),
                          'STARTUP_DEPENDENCY_CHANGED')
                T.refused(lambda: app.reconcile(e.input.archive_digest, e.completion.archive_digest),
                          'STARTUP_DEPENDENCY_CHANGED')
        finally:
            app._work.release()
        assert app._reconcile_runtime(actual, e.input, e.completion).status == 'RECONCILED'
        assert durable(e) == before


def test_actual_archive_damage_after_inspection_cannot_be_hidden_by_passed_records():
    with F.fixture(completed=True) as e:
        app = initialized(e)
        actual = observed(app, e.input, e.completion)
        target = e.store.roots.sealed_root/'catalog.jsonl'
        raw = target.read_bytes()
        target.write_bytes(raw[:-1])  # actual torn catalog, preserved until explicit test cleanup
        before = durable(e)
        with patch.object(C.Controller, 'read_committed_account',
                          side_effect=AssertionError('damaged dependency before authority')):
            T.refused(lambda: app._reconcile_runtime(actual, e.input, e.completion),
                      'STARTUP_CURRENT_AUTHORITY_REFUSED')
        assert target.read_bytes() == raw[:-1] and durable(e) == before


def test_all_account_only_reads_receive_the_requested_session_on_both_entries():
    with F.fixture(completed=True) as e:
        app = T.startup(e)
        real, calls = C.Controller.read_committed_account, []
        def reading(controller, **kwargs):
            calls.append((controller, kwargs.get('session_id')))
            return real(controller, **kwargs)
        with patch.object(C.Controller, 'read_committed_account', reading):
            result = app.reconcile(e.input.archive_digest, e.completion.archive_digest,
                                   session_id='rehearsal-observer')
            actual = observed(app, e.input, e.completion)
            again = app._reconcile_runtime(actual, e.input, e.completion,
                                           session_id='rehearsal-observer')
        assert result.status == again.status == 'RECONCILED'
        assert calls == [(app.controller, 'rehearsal-observer')]*6


def test_actual_status_reconciliation_keeps_the_recorded_order_session():
    with V.broker_fixture(kind='partial') as e:
        V.complete(e)
        app, dry = V.build(e)
        # Initial external open order blocks readiness but creates the genuine runtime.
        assert app.reconcile(e.input.archive_digest, e.completion.archive_digest).status == 'BLOCKED'
        V.history(e, 'integration-sent')
        dry.results.append(V.status_result(e))
        actual = observed(app, e.input, e.completion)
        account_sessions, owner_sessions = [], []
        original_read, original_owner = C.Controller.read_committed_account, C.owner.load_context
        def reading(controller, **kwargs):
            account_sessions.append(kwargs.get('session_id'))
            return original_read(controller, **kwargs)
        def owner_read(*args, **kwargs):
            owner_sessions.append(kwargs.get('session_id'))
            return original_owner(*args, **kwargs)
        before = (e.guard_head.read(), e.baseline_head.read())
        with (patch.object(C.Controller, 'read_committed_account', reading),
              patch.object(C.owner, 'load_context', owner_read), V.read_only_boundaries()):
            result = app._reconcile_runtime(actual, e.input, e.completion,
                                            session_id='rehearsal-observer')
        assert result.status == 'RECONCILED_OPEN' and result.attempted_reconciliations == 1
        assert account_sessions == ['rehearsal-observer']*3
        assert 'synthetic-prior-startup' in owner_sessions and 'rehearsal-observer' in owner_sessions
        assert len(dry.requests) == 1 and dry.requests[0].operation == 'status'
        assert V.states(e)['integration-sent']['status'] == 'PARTIAL'
        assert (e.guard_head.read(), e.baseline_head.read()) == before


def test_same_owner_head_with_different_session_effective_limits_refuses_before_status():
    def configure(home, key, start):
        CF.sign(key, 'session_armed', {'session_id': 'synthetic-prior-startup'},
                M.iso_utc(start-timedelta(days=2)))
        CF.sign(key, 'limit_set', {'total_loss_floor_krw': 60000.0, 'daily_loss_krw': 20000.0},
                M.iso_utc(start-timedelta(days=1)))
    with F.fixture(completed=True, configure=configure) as e:
        app = initialized(e)
        actual = observed(app, e.input, e.completion)
        before = durable(e)
        with (patch.object(C.Controller, 'cancel', side_effect=AssertionError('wrong scoped authority')),
              patch.object(C.Controller, 'reconcile', side_effect=AssertionError('wrong scoped authority'))):
            T.refused(lambda: app._reconcile_runtime(actual, e.input, e.completion,
                session_id='synthetic-prior-startup'), 'STARTUP_CURRENT_AUTHORITY_REFUSED')
        assert durable(e) == before and not app.controller.adapters['upbit'].requests


def test_invalid_session_does_not_reach_actual_owner_or_order_work():
    with F.fixture(completed=True) as e:
        app = initialized(e)
        actual = observed(app, e.input, e.completion)
        before = durable(e)
        with patch.object(C.Controller, 'read_committed_account', side_effect=AssertionError('invalid scope')):
            for value in ('', 's'*129, False, 4, object()):
                T.refused(lambda: app._reconcile_runtime(actual, e.input, e.completion,
                    session_id=value), 'STARTUP_INPUT_INVALID')
        assert durable(e) == before
