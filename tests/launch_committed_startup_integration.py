"""Offline startup vertical over actual retained bytes and durable integrations.

The shared fixture creates disposable signed owner logs, exact capture archives,
collector/material replay, Journal/checkpoints and independent heads. GET replies,
prices, coverage and explicitly marked old lifecycle traces are synthetic. No
source verifier, owner verdict, session registry or issued capability is replaced.
DryRunAdapter is the only adapter; reconstruction models a new object lifetime,
not a native process/power-failure test or a deployment/source-authenticity claim.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import re
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_accounts import baseline_bridge as BB
from execution_accounts.baseline_store import CheckpointStore
from execution_control.capability import plain
from execution_control.controller import Controller, _fold
from execution_control.dry_run import DryRunAdapter
from execution_control.model import Order, order_digest
from execution_control.risk import Fill
from execution_control.store import Journal, Transaction
from execution_launch import committed_account as CA
from execution_launch import committed_startup as S
from execution_launch import guard_generation_archive as A
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard_commit import COMPLETE, PREPARE, GuardChain, GuardCheckpointStore
from execution_launch.profile import profile_contract_digest
from execution_launch.runner import Runner
from execution_orders import upbit
from execution_orders.model import AdapterResult
from tests import compliance_fixtures as CF
from tests import launch_guard_generation_archive as F
from tests.accounts_continuous import fill_event, mark_event
from tests.launch_account_interval import FakeUpbit, SCOPE, at, order as broker_order
from tests.launch_guard_capture_material import START

D = Decimal


def refused(call, expected=None):
    try:
        call()
    except (ValueError, RuntimeError) as exc:
        code = str(exc)
        assert re.fullmatch(r'[A-Z][A-Z0-9_]+', code), 'non-code/private diagnostic'
        if expected is not None:
            assert code in ((expected,) if isinstance(expected, str) else expected), (code, expected)
        return code
    raise AssertionError('expected refusal')


def inert(value):
    assert value.execution_ready is False and value.source_authenticated is False


def rows(e):
    return e.journal.snapshot()


def states(e):
    with e.journal.transaction() as tx:
        return _fold(tx.events)[0]


def checkpoints(e):
    return (e.guard_head.read(), e.baseline_head.read(),
        e.guard_store.load(expected_head=e.guard_head.read()),
        e.baseline_store.load(expected_head=e.baseline_head.read()))


def namespace(e):
    return 'lr' + profile_contract_digest(e.profile)[:24] + '-'


def build(e, *, fresh_dependencies=False, adapter=None, **changes):
    """Reopen actual roots without seed/adoption; the clock remains explicit."""
    if fresh_dependencies:
        baseline_store = CheckpointStore(root=e.home)
        guard_store = GuardCheckpointStore(root=e.home)
        baseline_head = BaselineHead(root=e.baseline_head._root,
            name=e.baseline_head._dir.name, chain=CheckpointChain(baseline_store))
        guard_head = BaselineHead(root=e.guard_head._root,
            name=e.guard_head._dir.name, chain=GuardChain(guard_store))
        journal = Journal(root=e.journal._root, require_existing=True)
    else:
        journal, baseline_store, guard_store = e.journal, e.baseline_store, e.guard_store
        baseline_head, guard_head = e.baseline_head, e.guard_head
    adapter = DryRunAdapter(upbit) if adapter is None else adapter
    args = dict(archive_store=e.reopen_archive(), journal=journal,
        guard_store=guard_store, guard_head=guard_head,
        baseline_store=baseline_store, baseline_head=baseline_head,
        profile=e.profile, adapters={'upbit': adapter}, isolated_state_root=e.home,
        clock=e.clock, session_provider=lambda _: None)
    return S.CommittedStartup(**(args | changes)), adapter


def complete(e):
    startup, adapter = build(e)
    result = startup.commit_input(e.input.archive_digest)
    assert not adapter.requests
    inert(result)
    e.receipt, e.completion = result.record.receipt, result
    return result


def reconcile(e, completion, *, startup=None, adapter=None):
    if startup is None:
        startup, adapter = build(e, fresh_dependencies=True, adapter=adapter)
    result = startup.reconcile(e.input.archive_digest, completion.archive_digest)
    inert(result); inert(result.inspection)
    return result, startup, adapter


@contextmanager
def flat(**options):
    env_options = dict(exchange=FakeUpbit(cash='100000', orders=()), fees=(),
        realized=D(0), high=D('100000'), day_start=D('100000'), loss=D(0))
    env_options.update(options.pop('env_options', {}))
    with F.fixture(env_options=env_options, **options) as e:
        yield e


def history(e, client_id, *, status='ACKNOWLEDGED', broker_id='integration-broker',
            side='buy', quantity=D(2), price=D('10000')):
    """Synthetic old lifecycle trace written through the actual Journal.

    The digest strings are inert retained trace data. This helper issues no
    session, permit or capability and never claims the old send was authorized.
    Positive reconciliation still requires the actual current Controller path.
    """
    obj = Order(client_id=client_id, account_scope=SCOPE, venue='upbit', market='spot',
        symbol='KRW-BTC', side=side, quantity=quantity, limit_price=price, quote_krw=D(1))
    pair = dict(client_id=client_id, order_digest=order_digest(obj))
    rules = replace(e.profile.instrument_rules, asof=e.package['now'])
    with e.journal.transaction() as tx:
        tx.append('reserved', pair | dict(order=plain(obj), rules=plain(rules),
            session_id='synthetic-prior-startup', request_digest='a'*64,
            permit_digest='b'*64, trade_date=''), now=e.package['now'])
        if status != 'RESERVED':
            tx.append('dispatching', pair | dict(request_digest='a'*64, permit_digest='b'*64),
                now=e.package['now'])
        if status in ('ACKNOWLEDGED', 'UNKNOWN'):
            tx.append(status.lower(), pair | dict(venue_order_id=broker_id, metadata=[]),
                now=e.package['now'])
    assert states(e)[client_id]['status'] == status
    return obj


@contextmanager
def broker_fixture(*, kind='partial', client_id='integration-sent'):
    """Exact raw broker order, FIFO fee and recorded fill for a synthetic buy."""
    filled = {'open': D(0), 'partial': D(1), 'filled': D(2)}[kind]
    fee = filled * D(5)
    trades = [] if not filled else [('integration-fill', str(filled), str(filled*D('10000')))]
    raw = broker_order('integration-broker', 'bid', START+timedelta(seconds=1),
        '10000', trades, paid_fee=str(fee))
    remaining = D(2)-filled
    locked = remaining*D('10005') if remaining else D(0)
    raw.update(identifier=client_id, state='wait' if remaining else 'done', volume='2',
        remaining_volume=str(remaining), locked=str(locked))
    total_cash = D('100000')-filled*D('10005')
    exchange = FakeUpbit(cash=str(total_cash-locked), btc=str(filled) if filled else None,
        orders=(raw,), ticker='10000')
    exchange.balances[0]['locked'] = str(locked)
    events = ()
    if filled:
        fill = Fill(venue='upbit', account_scope=SCOPE, order_id='integration-broker',
            fill_id='integration-fill', market='spot', symbol='KRW-BTC', side='buy',
            quantity=filled, price=D('10000'), quote_currency='KRW', quote_krw=D(1),
            fee_amount=fee, fee_currency='KRW', executed_at=START+timedelta(seconds=1), base_currency='BTC')
        events = (fill_event(10, fill),)
    with flat(capture_options=dict(exchange=exchange, events=events, opening='10000', fees=())) as e:
        e.expected_filled, e.expected_fee = filled, fee
        yield e


def status_result(e, **changes):
    filled = e.expected_filled
    return AdapterResult(**(dict(status='filled' if filled == 2 else 'partial' if filled else 'open',
        code='synthetic_status', venue_order_id='integration-broker', client_id='integration-sent',
        filled_quantity=filled, average_price=D('10000') if filled else None,
        fee=e.expected_fee, fee_currency='KRW') | changes))


@contextmanager
def read_only_boundaries():
    """Fail on a second advance/CAS and on any nested actual Journal use."""
    active = set()
    real, real_snapshot = Journal.transaction, Journal.snapshot
    @contextmanager
    def transaction(journal):
        key = str(journal._base)
        assert key not in active, 'nested Journal transaction'
        active.add(key)
        try:
            with real(journal) as tx:
                yield tx
        finally:
            active.remove(key)
    def snapshot(journal):
        assert str(journal._base) not in active, 'snapshot inside active Journal transaction'
        return real_snapshot(journal)
    with ExitStack() as stack:
        stack.enter_context(patch.object(Journal, 'transaction', transaction))
        stack.enter_context(patch.object(Journal, 'snapshot', snapshot))
        for target, name in ((BB, 'advance_account_baseline'), (CheckpointStore, 'commit'),
                (GuardCheckpointStore, 'commit'), (BaselineHead, 'compare_and_set'),
                (BaselineHead, 'initialize_reviewed_head')):
            stack.enter_context(patch.object(target, name, side_effect=AssertionError('unexpected advance/CAS')))
        yield


def test_retained_input_actual_commit_new_integrations_and_true_empty_reconciliation():
    with flat() as e:
        before = checkpoints(e)
        uncommitted, adapter = build(e)
        classified = uncommitted.inspect(e.input.archive_digest)
        assert (classified.durable_status, classified.current_status) == ('FRESH', 'NOT_CHECKED')
        assert checkpoints(e) == before and not adapter.requests
        completion = uncommitted.commit_input(e.input.archive_digest)
        saved, events = checkpoints(e), rows(e)
        assert saved[3].sequence == before[3].sequence+1
        assert sum(row['kind'] == PREPARE for row in events) == 1
        assert sum(row['kind'] == COMPLETE for row in events) == 1
        assert completion.record.receipt.replayed is False
        constructed = {'provider': [], 'controller': [], 'runner': []}
        with ExitStack() as spies:
            for key, cls in (('provider', CA.CommittedAccountProvider), ('controller', Controller), ('runner', Runner)):
                original = cls.__init__
                def init(obj, *args, _original=original, _key=key, **kwargs):
                    _original(obj, *args, **kwargs)
                    constructed[_key].append(obj)
                spies.enter_context(patch.object(cls, '__init__', init))
            restart, dry = build(e, fresh_dependencies=True)
            with read_only_boundaries(), patch.object(Runner, 'tick', side_effect=AssertionError('strategy tick')):
                result, _, _ = reconcile(e, completion, startup=restart, adapter=dry)
                again, _, _ = reconcile(e, completion, startup=restart, adapter=dry)
        assert result.status == again.status == 'RECONCILED'
        assert result.inspection.current_status == 'FRESH' and result.inspection.durable_status == 'CONSISTENT'
        assert result.inspection.asof == e.package['interval'].end
        assert completion.retained_input.record.evaluated_at == e.package['now']
        assert result.attempted_reconciliations == 0
        assert result.unresolved_client_ids == result.external_order_ids == result.open_client_ids == result.holdings == ()
        assert result.final_control_head == events[-1]['row_sha256']
        assert len(constructed['controller']) == len(constructed['runner']) == 1
        controller, runner = constructed['controller'][0], constructed['runner'][0]
        assert runner.controller is controller and runner.account_provider is controller.account_provider
        assert type(controller.account_provider) is CA.CommittedAccountProvider
        assert controller.journal is not e.journal and controller.adapters['upbit'] is dry
        assert runner.mode == 'rehearsal' and runner.evidence is None and runner.driver is None
        assert controller.account_provider in constructed['provider']
        assert rows(e) == events and checkpoints(e) == saved and dry.requests == []


def test_complete_without_retained_result_is_read_only_until_explicit_actual_replay_receipt():
    with flat() as e:
        first = complete(e)
        with e.journal.transaction() as tx:
            suffix = tx.append('kill', {'session_id': 'unrelated-fixture', 'reason': 'retained restriction'},
                now=e.clock_cell[0])
        saved, events = checkpoints(e), rows(e)
        startup, dry = build(e, fresh_dependencies=True)
        with read_only_boundaries(), patch.object(S, 'commit_continuous_guard',
                side_effect=AssertionError('inspection resumed commit')):
            inspected = startup.inspect(e.input.archive_digest)
        assert (inspected.durable_status, inspected.current_status, inspected.reason) == (
            'CONSISTENT', 'NOT_CHECKED', 'STARTUP_COMPLETION_RECORD_REQUIRED')
        replayed = startup.commit_input(e.input.archive_digest)
        assert replayed.record.receipt.replayed and replayed.record.receipt.control_head == suffix['row_sha256']
        assert replayed.record.completion_head == first.record.completion_head
        assert replayed.archive_digest != first.archive_digest
        assert first.record.receipt.control_head != replayed.record.receipt.control_head
        assert rows(e) == events and checkpoints(e) == saved and not dry.requests
        original = A.read_guard_completion(e.reopen_archive(), first.archive_digest,
            expected_input_archive_digest=e.input.archive_digest)
        assert original.record == first.record


def test_each_pending_durable_phase_is_inspected_without_resuming_then_exactly_retried():
    for phase, expected in (('prepare', 'PENDING_GUARD_BEFORE_BASELINE'),
                           ('baseline', 'PENDING_CROSS_STORE'), ('guard', 'PENDING_FINALIZATION')):
        with flat() as e:
            startup, dry = build(e)
            actual_append, actual_cas = Transaction.append, BaselineHead.compare_and_set
            def append(tx, kind, data, *, now):
                result = actual_append(tx, kind, data, now=now)
                if phase == 'prepare' and kind == PREPARE:
                    raise ValueError('SYNTHETIC_INTERRUPTION')
                return result
            def cas(head, old, new):
                result = actual_cas(head, old, new)
                if (phase == 'baseline' and head is e.baseline_head
                        or phase == 'guard' and head is e.guard_head):
                    raise ValueError('SYNTHETIC_INTERRUPTION')
                return result
            with patch.object(Transaction, 'append', append), patch.object(BaselineHead, 'compare_and_set', cas):
                refused(lambda: startup.commit_input(e.input.archive_digest))
            events, saved = rows(e), checkpoints(e)
            reopened, _ = build(e, fresh_dependencies=True)
            with read_only_boundaries(), patch.object(S, 'commit_continuous_guard',
                    side_effect=AssertionError('pending inspection mutated state')):
                inspected = reopened.inspect(e.input.archive_digest)
            assert inspected.durable_status == expected and inspected.current_status == 'NOT_CHECKED'
            assert rows(e) == events and checkpoints(e) == saved and not dry.requests
            completion = reopened.commit_input(e.input.archive_digest)
            assert completion.record.receipt.replayed
            final = rows(e)
            assert sum(row['kind'] == PREPARE for row in final) == 1
            assert sum(row['kind'] == COMPLETE for row in final) == 1
            assert reconcile(e, completion)[0].status == 'RECONCILED'


def test_stale_boundary_preserves_original_times_and_never_calls_status_cancel_or_strategy():
    with flat() as e:
        completion = complete(e)
        saved, events = checkpoints(e), rows(e)
        endpoint = e.package['interval'].end
        e.clock_cell[0] = endpoint+timedelta(seconds=30)
        startup, dry = build(e, fresh_dependencies=True)
        assert startup.inspect(e.input.archive_digest, completion.archive_digest).current_status == 'FRESH'
        e.clock_cell[0] += timedelta(microseconds=1)
        with (read_only_boundaries(), patch.object(Controller, 'reconcile', side_effect=AssertionError('stale status')),
                patch.object(Controller, 'cancel', side_effect=AssertionError('stale cancel')),
                patch.object(Runner, 'tick', side_effect=AssertionError('stale sell/strategy'))):
            result, _, _ = reconcile(e, completion, startup=startup, adapter=dry)
        assert result.status == 'BLOCKED' and result.inspection.current_status == 'STALE'
        assert result.inspection.reason == 'STARTUP_STALE'
        assert result.inspection.asof == endpoint and completion.retained_input.record.evaluated_at == e.package['now']
        assert result.attempted_reconciliations == 0 and not dry.requests
        assert rows(e) == events and checkpoints(e) == saved


def test_actual_owner_epoch_or_code_change_blocks_before_any_adapter_operation():
    for mutation in ('owner', 'code'):
        with flat() as e:
            completion = complete(e)
            if mutation == 'owner':
                CF.sign(e.key, 'age_of_majority', {'birth_date': '2000-01-01', 'evidence': 'new fixture row'},
                    M.iso_utc(e.clock_cell[0]))
            else:
                CF.other_code(e.key, M.iso_utc(e.clock_cell[0]))
            events, saved = rows(e), checkpoints(e)
            startup, dry = build(e, fresh_dependencies=True)
            assert startup.inspect(e.input.archive_digest, completion.archive_digest).durable_status == 'CONSISTENT'
            refused(lambda: reconcile(e, completion, startup=startup, adapter=dry),
                'STARTUP_CURRENT_AUTHORITY_REFUSED')
            assert not dry.requests
            assert rows(e) == events and checkpoints(e) == saved


def test_actual_reserved_namespace_cancel_has_no_remote_request_or_risk_snapshot():
    with F.fixture(held=True) as e:
        completion = complete(e)
        provider = F.provider(e)
        dry = DryRunAdapter(upbit)
        controller = Controller(journal=e.journal, account_provider=provider, policy=e.policy,
            adapters={'upbit': dry}, session_provider=lambda _: None, clock=e.clock)
        obj = Order(client_id=namespace(e)+'reserved', account_scope=SCOPE, venue='upbit', market='spot',
            symbol='KRW-BTC', side='sell', quantity=D('.5'), limit_price=D('10050'), quote_krw=D(1))
        assert controller.reserve(obj, e.profile.instrument_rules, session_id='startup-exit',
            now=e.clock_cell[0]).status == 'RESERVED'
        saved = checkpoints(e)
        result, _, _ = reconcile(e, completion, adapter=dry)
        assert result.status == 'RECONCILED' and states(e)[obj.client_id]['status'] == 'CANCELLED_LOCAL'
        assert result.attempted_reconciliations == 0 and dry.requests == []
        assert result.holdings == (('upbit', 'BTC', D(1)),)
        assert not any(row['kind'] == 'risk_snapshot' for row in rows(e))
        assert checkpoints(e) == saved


def test_foreign_reserved_namespace_remains_unresolved_without_remote_or_local_cancel():
    with flat() as e:
        completion = complete(e)
        obj = history(e, 'foreign-reserved', status='RESERVED')
        events = rows(e)
        result, _, dry = reconcile(e, completion)
        assert result.status == 'BLOCKED' and obj.client_id in result.unresolved_client_ids
        assert states(e)[obj.client_id]['status'] == 'RESERVED'
        assert result.attempted_reconciliations == 0 and not dry.requests and rows(e) == events


def test_captured_broker_evidence_conflicts_with_own_never_sent_reservation():
    with flat() as probe:
        client_id = namespace(probe)+'reserved-conflict'
    with broker_fixture(kind='open', client_id=client_id) as e:
        assert client_id.startswith(namespace(e))
        completion = complete(e)
        history(e, client_id, status='RESERVED')
        events = rows(e)
        result, _, dry = reconcile(e, completion)
        assert result.status == 'BLOCKED' and result.reason == 'STARTUP_ORDER_CONFLICT'
        assert client_id in result.unresolved_client_ids and states(e)[client_id]['status'] == 'RESERVED'
        assert rows(e) == events and dry.requests == []


def test_unknown_and_interrupted_dispatch_remain_uncertain_and_never_resend():
    for state in ('UNKNOWN', 'DISPATCHING'):
        with flat() as e:
            completion = complete(e)
            obj = history(e, 'uncertain-'+state.lower(), status=state, broker_id='')
            dry = DryRunAdapter(upbit, results=(AdapterResult(status='unknown', code='synthetic_unavailable'),)*2)
            result, startup, _ = reconcile(e, completion, adapter=dry)
            again, _, _ = reconcile(e, completion, startup=startup, adapter=dry)
            assert result.status == again.status == 'BLOCKED'
            assert obj.client_id in result.unresolved_client_ids and states(e)[obj.client_id]['status'] == state
            assert result.attempted_reconciliations == again.attempted_reconciliations == 1
            assert [request.operation for request in dry.requests] == ['status', 'status']
            assert not any(row['kind'] in ('cancelled_local', 'reconciled', 'fill') for row in rows(e))


def test_actual_endpoint_partial_fill_fee_and_open_residual_are_reconciled_not_counted_as_flat():
    with broker_fixture() as e:
        completion = complete(e)
        history(e, 'integration-sent')
        dry = DryRunAdapter(upbit, results=(status_result(e), status_result(e)))
        saved = checkpoints(e)
        result, startup, _ = reconcile(e, completion, adapter=dry)
        assert result.status == 'RECONCILED_OPEN' and result.open_client_ids == ('integration-sent',)
        assert result.unresolved_client_ids == result.external_order_ids == ()
        assert result.holdings == (('upbit', 'BTC', D(1)),)
        actual = states(e)['integration-sent']
        assert actual['status'] == 'PARTIAL' and actual['filled'] == D(1)
        assert actual['order'].quantity-actual['filled'] == D(1)
        fills = [row for row in rows(e) if row['kind'] == 'fill']
        assert len(fills) == 1 and D(fills[0]['data']['fill']['fee_amount']) == D(5)
        assert rows(e)[-1]['kind'] == 'reconciled' and result.final_control_head == rows(e)[-1]['row_sha256']
        again, _, _ = reconcile(e, completion, startup=startup, adapter=dry)
        assert again.status == 'RECONCILED_OPEN' and len([row for row in rows(e) if row['kind'] == 'fill']) == 1
        assert [request.operation for request in dry.requests] == ['status', 'status']
        assert checkpoints(e) == saved and result.inspection.asof == e.package['interval'].end


def test_actual_open_zero_fill_status_requires_new_reconciled_row_and_keeps_residual():
    with broker_fixture(kind='open') as e:
        completion = complete(e)
        history(e, 'integration-sent')
        dry = DryRunAdapter(upbit, results=(status_result(e),))
        result, _, _ = reconcile(e, completion, adapter=dry)
        assert result.status == 'RECONCILED_OPEN' and result.open_client_ids == ('integration-sent',)
        assert result.unresolved_client_ids == result.external_order_ids == result.holdings == ()
        actual = states(e)['integration-sent']
        assert actual['status'] == 'ACKNOWLEDGED' and actual['filled'] == 0
        assert actual['order'].quantity-actual['filled'] == D(2)
        assert rows(e)[-1]['kind'] == 'reconciled'
        assert result.final_control_head == rows(e)[-1]['row_sha256']
        assert not any(row['kind'] == 'fill' for row in rows(e))
        assert [request.operation for request in dry.requests] == ['status']


def test_actual_endpoint_terminal_fill_reconciles_exact_quantity_and_cumulative_fee():
    with broker_fixture(kind='filled') as e:
        completion = complete(e)
        history(e, 'integration-sent')
        dry = DryRunAdapter(upbit, results=(status_result(e),))
        result, _, _ = reconcile(e, completion, adapter=dry)
        assert result.status == 'RECONCILED' and result.open_client_ids == result.unresolved_client_ids == ()
        assert result.holdings == (('upbit', 'BTC', D(2)),)
        actual = states(e)['integration-sent']
        assert actual['status'] == 'FILLED' and actual['filled'] == D(2)
        fills = [row for row in rows(e) if row['kind'] == 'fill']
        assert len(fills) == 1 and D(fills[0]['data']['fill']['fee_amount']) == D(10)
        assert [request.operation for request in dry.requests] == ['status']


def test_mismatched_cumulative_status_fee_or_broker_identity_cannot_claim_reconciliation():
    for changes in ({'filled_quantity': D('1.5')}, {'fee': D(6)}, {'venue_order_id': 'another-broker'},
                    {'average_price': D('10001')}):
        with broker_fixture() as e:
            completion = complete(e)
            history(e, 'integration-sent')
            dry = DryRunAdapter(upbit, results=(status_result(e, **changes),))
            result, _, _ = reconcile(e, completion, adapter=dry)
            assert result.status == 'BLOCKED' and result.attempted_reconciliations == 1
            assert 'integration-sent' in result.unresolved_client_ids
            assert states(e)['integration-sent']['filled'] == 0
            assert not any(row['kind'] in ('fill', 'reconciled') for row in rows(e))
            assert [request.operation for request in dry.requests] == ['status']


def test_empty_local_orders_do_not_hide_external_open_broker_order():
    with broker_fixture(kind='open', client_id='external-client') as e:
        completion = complete(e)
        result, _, dry = reconcile(e, completion)
        assert result.status == 'BLOCKED' and result.external_order_ids == ('integration-broker',)
        assert result.attempted_reconciliations == 0 and states(e) == {} and dry.requests == []


def test_status_fill_missing_from_retained_endpoint_needs_next_real_generation():
    with broker_fixture(kind='open') as e:
        completion = complete(e)
        history(e, 'integration-sent')
        dry = DryRunAdapter(upbit, results=(status_result(e, status='partial', filled_quantity=D(1),
            average_price=D('10000'), fee=D(5)),))
        original = checkpoints(e)
        result, _, _ = reconcile(e, completion, adapter=dry)
        assert result.status == 'BLOCKED' and 'integration-sent' in result.unresolved_client_ids
        assert states(e)['integration-sent']['filled'] == 0
        assert not any(row['kind'] in ('fill', 'reconciled') for row in rows(e))
        assert checkpoints(e) == original and result.inspection.asof == e.package['interval'].end


def test_heavy_final_durable_read_expiry_never_returns_success_or_changes_original_checkpoint():
    with flat() as e:
        completion = complete(e)
        real = CA.CommittedAccountProvider.inspect_committed
        calls = []
        def delayed(provider, **kwargs):
            result = real(provider, **kwargs)
            calls.append(result)
            e.clock_cell[0] = e.package['interval'].end+timedelta(seconds=30, microseconds=1)
            return result
        saved = checkpoints(e)
        with patch.object(CA.CommittedAccountProvider, 'inspect_committed', delayed):
            result, _, dry = reconcile(e, completion)
        assert calls and result.status == 'BLOCKED'
        assert result.completed_at >= e.clock_cell[0]
        assert result.inspection.asof == e.package['interval'].end
        assert checkpoints(e) == saved and not dry.requests


def test_current_owner_mutation_after_actual_status_is_rechecked_before_success():
    with broker_fixture() as e:
        completion = complete(e)
        history(e, 'integration-sent')
        dry = DryRunAdapter(upbit, results=(status_result(e),))
        real = DryRunAdapter.dispatch
        reached = []
        def changed(adapter, request, capability, *, now):
            result = real(adapter, request, capability, now=now)
            if request.operation == 'status':
                reached.append(request)
                CF.sign(e.key, 'age_of_majority', {'birth_date': '2000-01-01', 'evidence': 'during-status'},
                    M.iso_utc(e.clock_cell[0]))
            return result
        with patch.object(DryRunAdapter, 'dispatch', changed):
            refused(lambda: reconcile(e, completion, adapter=dry), 'STARTUP_CURRENT_AUTHORITY_REFUSED')
        assert reached
        assert [request.operation for request in dry.requests] == ['status']


def test_actual_hidden_trough_halt_and_floors_survive_restore_without_liquidation():
    events = (mark_event(10, '10200', START+timedelta(seconds=1)),
        mark_event(11, '9900', START+timedelta(seconds=2)),
        mark_event(12, '10050', START+timedelta(seconds=3)))
    with F.fixture(held=True, env_options=dict(high=D('100045'), day_start=D('100045')),
            capture_options=dict(events=events)) as e:
        completion = complete(e)
        saved = checkpoints(e)
        assert saved[2].permanently_halted and completion.record.receipt.permanently_halted
        assert saved[2].high_watermark >= D('100195')
        result, _, dry = reconcile(e, completion)
        assert result.status == 'RECONCILED' and result.holdings == (('upbit', 'BTC', D(1)),)
        assert checkpoints(e) == saved and not dry.requests
        assert any(row['kind'] == 'halt' for row in rows(e))
        assert not any(row['kind'] in ('reserved', 'dispatching', 'cancel_requested') for row in rows(e))


def test_original_source_gap_refusal_and_controlled_runner_boundary_remain_closed():
    with flat() as e:
        completion = complete(e)
        refused(lambda: e.captured.source(e.package['baseline_before'], e.package['now']),
            'CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED')
        provider = F.provider(e)
        dry = DryRunAdapter(upbit)
        controller = Controller(journal=e.journal, account_provider=provider, policy=e.policy,
            adapters={'upbit': dry}, session_provider=lambda _: None, clock=e.clock)
        refused(lambda: Runner(profile=e.profile, quote_provider=lambda _: None,
            account_provider=provider, controller=controller, mode='controlled',
            isolated_state_root=e.home, clock=e.clock), 'RUNNER_COMMITTED_REHEARSAL_REQUIRED')
        assert completion.execution_ready is False and not dry.requests


def test_actual_reducing_reserve_dispatch_unknown_then_restart_status_never_retransmits():
    with F.fixture(held=True) as e:
        completion = complete(e)
        provider = F.provider(e)
        dry = DryRunAdapter(upbit, results=(AdapterResult(status='unknown', code='synthetic_timeout'),
            AdapterResult(status='unknown', code='synthetic_status_timeout')))
        controller = Controller(journal=e.journal, account_provider=provider, policy=e.policy,
            adapters={'upbit': dry}, session_provider=lambda _: None, clock=e.clock)
        obj = Order(client_id=namespace(e)+'actual-unknown', account_scope=SCOPE, venue='upbit', market='spot',
            symbol='KRW-BTC', side='sell', quantity=D('.5'), limit_price=D('10050'), quote_krw=D(1))
        assert controller.reserve(obj, e.profile.instrument_rules, session_id='startup-actual-exit',
            now=e.clock_cell[0]).status == 'RESERVED'
        assert controller.dispatch(obj.client_id, now=e.clock_cell[0]).status == 'UNKNOWN'
        assert [request.operation for request in dry.requests] == ['create']
        saved = checkpoints(e)
        result, _, _ = reconcile(e, completion, adapter=dry)
        assert result.status == 'BLOCKED' and obj.client_id in result.unresolved_client_ids
        assert states(e)[obj.client_id]['status'] == 'UNKNOWN'
        assert [request.operation for request in dry.requests] == ['create', 'status']
        assert checkpoints(e) == saved


def test_required_cutoff_and_new_seoul_day_are_policy_refusals_not_fresh_or_generic_stale():
    for start, final_time in ((at(26, 21, 59, 45), at(26, 22)), (START, at(27, 0))):
        with flat(start=start) as e:
            completion = complete(e)
            e.clock_cell[0] = final_time
            saved, events = checkpoints(e), rows(e)
            result, _, dry = reconcile(e, completion)
            assert result.status == 'BLOCKED'
            assert (result.inspection.durable_status, result.inspection.current_status,
                result.inspection.reason) == ('CONSISTENT', 'REFUSED', 'STARTUP_POLICY_BOUNDARY')
            assert result.attempted_reconciliations == 0 and not dry.requests
            assert checkpoints(e) == saved and rows(e) == events


def test_old_uncommitted_source_interval_cannot_be_backfilled_by_relabeling_startup_time():
    with flat() as e:
        retained, saved, events = e.input.record, checkpoints(e), rows(e)
        e.clock_cell[0] = e.package['now']+timedelta(days=2)
        startup, dry = build(e)
        refused(lambda: startup.commit_input(e.input.archive_digest))
        original = A.read_guard_input(e.reopen_archive(), e.input.archive_digest)
        assert original.record == retained and original.package['now'] == e.package['now']
        assert checkpoints(e) == saved and rows(e) == events and not dry.requests


def test_actual_status_then_heavy_final_durable_read_expiry_or_clock_rollback_refuses_success():
    for change in ('expired', 'rollback'):
        with broker_fixture() as e:
            completion = complete(e)
            history(e, 'integration-sent')
            dry = DryRunAdapter(upbit, results=(status_result(e),))
            actual_dispatch = DryRunAdapter.dispatch
            actual_inspect = CA.CommittedAccountProvider.inspect_committed
            sent, late = [], []
            def dispatch(adapter, request, capability, *, now):
                result = actual_dispatch(adapter, request, capability, now=now)
                if request.operation == 'status':
                    sent.append(request)
                return result
            def final_read(provider, **kwargs):
                result = actual_inspect(provider, **kwargs)
                if sent:
                    late.append(result)
                    e.clock_cell[0] = (e.package['interval'].end+timedelta(seconds=30, microseconds=1)
                        if change == 'expired' else e.package['now']-timedelta(microseconds=1))
                return result
            saved = checkpoints(e)
            with patch.object(DryRunAdapter, 'dispatch', dispatch), \
                    patch.object(CA.CommittedAccountProvider, 'inspect_committed', final_read):
                refused(lambda: reconcile(e, completion, adapter=dry),
                    ('STARTUP_STALE', 'STARTUP_CLOCK_ROLLBACK', 'STARTUP_CURRENT_AUTHORITY_REFUSED'))
            assert sent and late and [request.operation for request in dry.requests] == ['status']
            assert checkpoints(e) == saved
            assert states(e)['integration-sent']['filled'] == D(1)


def test_local_order_limit_is_preflighted_before_any_cancellation_or_status_dispatch():
    with flat() as e:
        completion = complete(e)
        rules = replace(e.profile.instrument_rules, asof=e.package['now'])
        with e.journal.transaction() as tx:
            for index in range(1025):
                obj = Order(client_id=namespace(e)+str(index), account_scope=SCOPE, venue='upbit', market='spot',
                    symbol='KRW-BTC', side='buy', quantity=D(2), limit_price=D('10000'), quote_krw=D(1))
                tx.append('reserved', dict(client_id=obj.client_id, order_digest=order_digest(obj),
                    order=plain(obj), rules=plain(rules), session_id='synthetic-prior-startup',
                    request_digest='a'*64, permit_digest='b'*64, trade_date=''), now=e.package['now'])
        events = rows(e)
        startup, dry = build(e)
        with (patch.object(Controller, 'cancel', side_effect=AssertionError('partial cancellation before bounds')),
                patch.object(Controller, 'reconcile', side_effect=AssertionError('partial status before bounds'))):
            refused(lambda: reconcile(e, completion, startup=startup, adapter=dry), 'STARTUP_RESOURCE_LIMIT')
        assert rows(e) == events and len(states(e)) == 1025 and not dry.requests


def test_same_actual_owner_head_does_not_override_changed_session_effective_limits():
    """Only a negative historical owner-log fixture; no operational arm/session.

    The temporary signed row changes the real loader's limit scope. It creates
    no PreparedSession, no session registry entry and no positive authority.
    """
    def configure(home, key, start):
        CF.sign(key, 'session_armed', {'session_id': 'synthetic-prior-startup'},
            M.iso_utc(start-timedelta(days=2)))
        CF.sign(key, 'limit_set', {'total_loss_floor_krw': 60000.0, 'daily_loss_krw': 20000.0},
            M.iso_utc(start-timedelta(days=1)))
    with flat(configure=configure) as e:
        completion = complete(e)
        provider = F.provider(e)
        with e.journal.transaction() as tx:
            projected = provider.read(now=e.clock_cell[0], transaction=tx)
        unscoped = owner.load_context(e.clock_cell[0], projected.observation.positions)
        scoped = owner.load_context(e.clock_cell[0], projected.observation.positions,
            session_id='synthetic-prior-startup')
        assert M.is_sealed(unscoped) and M.is_sealed(scoped)
        assert unscoped.owner.head == scoped.owner.head
        assert e.package['owner_after'].owner_head_sha256 == scoped.owner.head[1]
        assert e.package['owner_after'].signed_floor_krw == D(60000)
        assert scoped.owner.limits['total_loss_floor_krw'] == 70000.0
        assert scoped.owner.limits['daily_loss_krw'] == 10000.0
        history(e, 'same-head-effective-limits', status='UNKNOWN', broker_id='')
        saved, events = checkpoints(e), rows(e)
        startup, dry = build(e, fresh_dependencies=True)
        refused(lambda: reconcile(e, completion, startup=startup, adapter=dry),
            'STARTUP_CURRENT_AUTHORITY_REFUSED')
        assert states(e)['same-head-effective-limits']['status'] == 'UNKNOWN'
        assert not dry.requests and checkpoints(e) == saved and rows(e) == events


def test_last_inspection_and_reconciliation_clock_follows_actual_heavy_dependency_work():
    with flat() as e:
        completion = complete(e)
        trace = []
        def clock():
            trace.append('clock')
            return e.clock()
        actual_configuration = S.CommittedStartup._configuration
        actual_inspect = CA.CommittedAccountProvider.inspect_committed
        actual_owner = owner.load_context
        def configuration(startup):
            result = actual_configuration(startup)
            trace.append('configuration')
            return result
        def inspection(provider, **kwargs):
            result = actual_inspect(provider, **kwargs)
            trace.append('durable-inspection')
            return result
        def current_owner(*args, **kwargs):
            result = actual_owner(*args, **kwargs)
            trace.append('owner')
            return result
        startup, dry = build(e, fresh_dependencies=True, clock=clock)
        with patch.object(S.CommittedStartup, '_configuration', configuration), \
                patch.object(CA.CommittedAccountProvider, 'inspect_committed', inspection), \
                patch.object(owner, 'load_context', current_owner):
            inspected = startup.inspect(e.input.archive_digest, completion.archive_digest)
            assert inspected.current_status == 'FRESH'
            assert 'durable-inspection' in trace and 'configuration' in trace
            assert trace[-1] == 'clock', trace[-6:]
            trace.clear()
            result, _, _ = reconcile(e, completion, startup=startup, adapter=dry)
            assert result.status == 'RECONCILED'
            assert 'owner' in trace and 'durable-inspection' in trace and 'configuration' in trace
            assert trace[-1] == 'clock', trace[-6:]
        assert not dry.requests


def test_actual_controller_completion_clock_is_retained_before_cancel_or_status():
    for status in ('RESERVED', 'UNKNOWN'):
        with flat() as e:
            completion = complete(e)
            client_id = namespace(e)+'completion-watermark'
            history(e, client_id, status=status, broker_id='')
            startup, dry = build(e, fresh_dependencies=True)
            initial = e.clock_cell[0]
            actual_read = Controller.read_committed_account
            completed = []
            def slow_actual_read(controller, **kwargs):
                assert not completed, 'startup continued after clock rollback'
                e.clock_cell[0] = initial+timedelta(seconds=5)
                result = actual_read(controller, **kwargs)
                assert result.completed_at == e.clock_cell[0]
                completed.append(result)
                # Actual Controller work finished later than the initial startup
                # request; a still-later sample must retain that real watermark.
                e.clock_cell[0] = initial+timedelta(seconds=1)
                return result
            saved, events = checkpoints(e), rows(e)
            with (patch.object(Controller, 'read_committed_account', slow_actual_read),
                    patch.object(Controller, 'cancel', side_effect=AssertionError('cancel after clock rollback')),
                    patch.object(Controller, 'reconcile', side_effect=AssertionError('status after clock rollback'))):
                refused(lambda: reconcile(e, completion, startup=startup, adapter=dry), 'STARTUP_CLOCK_ROLLBACK')
            assert len(completed) == 1 and completed[0].completed_at == initial+timedelta(seconds=5)
            assert states(e)[client_id]['status'] == status
            assert checkpoints(e) == saved and rows(e) == events and not dry.requests


def test_startup_missing_strict_journal_refuses_without_creating_an_empty_replacement():
    with flat() as e:
        missing = e.home/'missing-startup-control'
        assert not missing.exists()
        strict = Journal(root=missing, require_existing=True)
        startup, dry = build(e, journal=strict)
        saved, events = checkpoints(e), rows(e)
        refused(lambda: startup.inspect(e.input.archive_digest), 'STARTUP_DURABLE_REFUSED')
        assert not missing.exists()
        assert checkpoints(e) == saved and rows(e) == events and not dry.requests
