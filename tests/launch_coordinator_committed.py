"""Explicit committed scheduler with actual isolated producer/store/owner checks.

Market receipts and complete paths are synthetic. Scheduler-only cases deliberately
have no reviewed strategy and a rejecting implementation verifier; they cannot
manufacture research approval. Carry/history cases use the independently evaluated,
actually signed study fixture and the existing issued driver. No live service,
real owner home, positive authority patch or executable entry is used.
"""
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from execution_accounts.baseline_bridge import ContinuousAccountProvider
from execution_control.controller import Controller
from execution_launch import coordinator as C
from execution_launch.continuous_guard_commit import COMPLETE, PREPARE
from execution_launch.driver import DeploymentWindow
from execution_launch.runner import EvidencePackage, Signal, StrategyDriver
from tests import launch_committed_producer as F
from tests.launch_capture import book


def refuse(call, expected):
    try:
        call()
    except ValueError as exc:
        assert str(exc) in ((expected,) if isinstance(expected, str) else expected), (str(exc), expected)
        return str(exc)
    raise AssertionError('expected refusal')


def reject_implementation(*args):
    return False


def hold_without_research(*args):
    return Signal(signal_id='unreviewed-scheduler-hold', action='hold')


class Books:
    def __init__(self, e):
        self.e = e
        self.value = None
        self.failure = False
        self.calls = 0

    def read(self):
        self.calls += 1
        if self.failure:
            raise RuntimeError('private quote failure must not escape')
        return self.value if self.value is not None else book(self.e.clock_cell[0], bid=10000, ask=10010)


def arguments(e, **changes):
    """No successful research verifier exists in this control-only fixture."""
    evidence = EvidencePackage(protocol=SimpleNamespace(schema_version=1, evaluator_revision='forward-paper-v1'),
                               result=None, review_verifier=None)
    driver = StrategyDriver(callback=hold_without_research, artifact=b'unreviewed scheduler HOLD', parameters_json='{}')
    window = DeploymentWindow(deployment_id='committed-scheduler-control',
                              start=e.start+timedelta(seconds=20), end=e.start+timedelta(seconds=80))
    args = dict(mode='rehearsal', profile=e.profile, evidence=evidence, driver=driver,
        implementation_verifier=reject_implementation, adapters={'upbit':e.adapter}, account_source=None,
        account_prefetch=None, committed_producer=e.producer, trusted_head=e.baseline_head,
        quote_source=Books(e), window=window, bar_seconds=20,
        monitor_until=e.start+timedelta(hours=2, seconds=10), clock=e.clock,
        toast=lambda *_:False)
    return args | changes


def build(e, **changes):
    return C.Coordinator(**arguments(e, **changes))


def counts(e):
    rows = e.journal.snapshot()
    return tuple(sum(row['kind'] == kind for row in rows) for kind in (PREPARE, COMPLETE))


def creates(e):
    return tuple(request for request in e.adapter.requests if request.operation == 'create')


def test_constructor_rejects_legacy_mixing_or_wrong_actual_bindings_without_effects():
    with F.fixture(bind_startup=False) as e:
        before = F.durable(e)
        cases = (
            ({'account_source': lambda *_:None}, 'COORDINATOR_INTEGRATIONS_REQUIRED'),
            ({'account_prefetch': lambda *_:None}, 'COORDINATOR_COMMITTED_INTEGRATIONS_REQUIRED'),
            ({'committed_producer': object()}, 'COORDINATOR_COMMITTED_INTEGRATIONS_REQUIRED'),
            ({'mode':'controlled'}, 'COORDINATOR_MODE_UNSUPPORTED'),
            ({'clock':lambda:e.clock()}, 'COORDINATOR_COMMITTED_BINDING_CHANGED'),
            ({'trusted_head':SimpleNamespace(read=e.baseline_head.read)}, 'COORDINATOR_COMMITTED_BINDING_CHANGED'),
            ({'adapters':{'upbit':object()}}, 'COORDINATOR_COMMITTED_REHEARSAL_REQUIRED'),
            ({'profile':replace(e.profile, profile_id='different-economic-contract')},
             'COORDINATOR_COMMITTED_BINDING_CHANGED'),
            ({'profile':replace(e.profile, universe_rule_sha256='a'*64)}, 'COORDINATOR_COMMITTED_FIXED_REQUIRED'),
        )
        for changes, code in cases:
            refuse(lambda changes=changes:build(e, **changes), code)
            assert e.producer._startup is None and F.durable(e) == before
        assert not creates(e)


def test_stop_close_disarm_before_runtime_never_construct_or_claim_a_kill():
    with F.fixture(bind_startup=False) as e:
        coordinator = build(e)
        before = F.durable(e)
        assert coordinator._provider is coordinator._controller is coordinator._runner is None
        assert coordinator.status().new_entry_blocked and not coordinator._ready
        result = coordinator.disarm()
        assert result.local_strategy_stopped and not result.session_prepared
        assert not result.journal_kill_written and not result.owner_disarm_recorded
        assert not result.venue_orders_cancelled and not result.positions_liquidated
        assert coordinator.close() and coordinator.status().strategy_stopped
        assert coordinator._provider is coordinator._controller is coordinator._runner is None
        assert F.durable(e) == before and not creates(e)
        refuse(coordinator.bootstrap, 'COORDINATOR_STOPPED')


def test_two_actual_bootstraps_adopt_once_keep_startup_binding_and_advance_once_each():
    from tests.launch_committed_producer_integration import durable_trace
    with F.fixture(bind_startup=False) as e:
        coordinator = build(e)
        with durable_trace(e) as writes:
            F.arm_interval(e)
            first_status = coordinator.bootstrap()
            assert not first_status.account_source, first_status.account_source
            assert coordinator._ready and coordinator._latest_frame is None
            provider, controller, journal = e.producer._runtime_components()
            startup = e.producer._startup
            initial_binding, startup_runner = startup._binding, startup.runner
            assert coordinator._provider is provider and coordinator._controller is controller
            assert coordinator._journal is journal and coordinator._runner is not startup_runner
            assert controller.session_provider is coordinator._committed_session_provider
            assert first_status.risk_reasons == () and first_status.recovery_status is None
            assert first_status.new_entry_blocked  # no risk authorization is implied by reconciliation
            first_unit = coordinator._committed_unit
            F.arm_interval(e)
            second_status = coordinator.bootstrap()
            assert not second_status.account_source and coordinator._ready
            assert e.producer._runtime_components() == (provider, controller, journal)
            assert startup._binding == initial_binding and startup.runner is startup_runner
            assert coordinator._committed_unit.transaction_id != first_unit.transaction_id
            assert writes == {'baseline':2, 'guard':2, 'baseline_cas':2, 'guard_cas':2}
            before = dict(writes)
            coordinator._publish(None, coordinator._time(), None)
            assert writes == before  # current read/publication itself has no baseline transition
        assert counts(e) == (2, 2) and coordinator.status().published_units == 3
        assert len(e.supplier_calls) == 3  # opening, first interval, successor; no publication callback
        assert e.baseline_store.load(expected_head=e.baseline_head.read()).sequence == 2
        assert not creates(e)


def test_committed_monitor_uses_account_only_and_exact_endpoint_holdings():
    with F.fixture(bind_startup=False, held=True) as e:
        coordinator = build(e)
        F.arm_interval(e)
        with (patch.object(Controller, 'observe', side_effect=AssertionError('legacy risk projection')),
              patch.object(Controller, 'observe_committed', side_effect=AssertionError('entry risk projection')),
              patch.object(ContinuousAccountProvider, '__call__', side_effect=AssertionError('legacy durable advance'))):
            status = coordinator.bootstrap()
        assert not status.account_source and coordinator._ready, status
        assert coordinator._committed_account == coordinator._committed_unit.account
        assert status.held_symbol == status.trade_symbol == 'KRW-BTC'
        assert coordinator._committed_account.positions[0].units == F.D(1)
        assert counts(e) == (1, 1) and not creates(e)


def test_copied_public_unit_and_changed_runtime_cannot_republish_or_supply_readiness():
    with F.fixture(bind_startup=False) as e:
        coordinator = build(e)
        F.arm_interval(e)
        coordinator.bootstrap()
        assert coordinator._ready
        coordinator._committed_unit = replace(coordinator._committed_unit)
        refuse(lambda:coordinator._publish(None, coordinator._time(), None),
               'COMMITTED_PRODUCER_DEPENDENCY_CHANGED')
        assert counts(e) == (1, 1)
        coordinator._runner.account_provider = object()
        F.arm_interval(e)
        status = coordinator.bootstrap()
        assert status.account_source == 'COORDINATOR_COMMITTED_BINDING_CHANGED'
        assert not coordinator._ready and counts(e) == (1, 1) and not creates(e)


def test_account_failure_clears_readiness_without_liquidation_or_new_commit():
    with F.fixture(bind_startup=False, held=True) as e:
        coordinator = build(e)
        F.arm_interval(e)
        coordinator.bootstrap()
        assert coordinator._ready
        previous = coordinator._committed_account
        e.collector.account_scope = 'foreign'
        status = coordinator.bootstrap()
        assert status.account_source == 'COMMITTED_PRODUCER_DEPENDENCY_CHANGED'
        assert not coordinator._ready and status.new_entry_blocked
        assert coordinator._committed_account == previous and counts(e) == (1, 1)
        assert not creates(e)


def test_quote_and_terms_errors_before_runtime_are_sanitized_without_readiness():
    class BrokenTerms:
        def read(self):
            raise RuntimeError('private terms failure must not escape')
    with F.fixture(bind_startup=False) as e:
        books = Books(e)
        books.failure = True
        coordinator = build(e, terms_source=BrokenTerms(), quote_source=books)
        before = F.durable(e)
        refuse(coordinator._read_book, 'COORDINATOR_QUOTE_SOURCE_FAILED')
        refuse(coordinator.refresh_instrument_rules, 'COORDINATOR_TERMS_SOURCE_FAILED')
        assert coordinator._runner is None and not coordinator._ready
        assert coordinator.status().instrument_source == 'COORDINATOR_TERMS_SOURCE_FAILED'
        assert F.durable(e) == before and not creates(e)


def test_new_branch_requires_explicit_producer_when_legacy_source_is_none():
    with F.fixture(bind_startup=False) as e:
        before = F.durable(e)
        refuse(lambda:build(e, committed_producer=None), 'COORDINATOR_INTEGRATIONS_REQUIRED')
        assert F.durable(e) == before


def test_issued_terms_wait_for_runtime_then_use_retained_endpoint_without_a_legacy_frame():
    from execution_accounts import instrument_terms as T
    from execution_launch.runner import Runner
    from tests import launch_instrument_refresh as TF
    holder = {}
    def profile_transform(profile):
        rules = profile.instrument_rules
        authority = TF.authority(account_scope=profile.account_scope, symbol=profile.symbol,
            lot_size=rules.lot_size, min_quantity=rules.min_quantity,
            provenance_sha256='9'*64, identity_binding_sha256='8'*64,
            valid_from=rules.asof-timedelta(days=1), valid_until=rules.asof+timedelta(days=1))
        holder['authority'] = authority
        return replace(profile, instrument_rules=replace(rules, source_digest=T.authority_digest(authority)))
    with F.fixture(bind_startup=False, held=True, profile_transform=profile_transform) as e:
        class Terms:
            def read(self):
                return TF.observed(now=e.clock_cell[0], auth=holder['authority'])
        coordinator = build(e, terms_source=Terms())
        e.clock_cell[0] += timedelta(seconds=1)
        refuse(coordinator.refresh_instrument_rules, 'COORDINATOR_STARTUP_RECONCILE_REQUIRED')
        assert coordinator._pending_terms is not None and coordinator._runner is None
        F.arm_interval(e)
        coordinator.bootstrap()
        assert coordinator._runner is not None and coordinator._latest_frame is None
        actual_refresh = Runner.refresh_instrument_rules
        accounts = []
        def refresh(runner, renewal, *, now, account=None):
            accounts.append(account)
            return actual_refresh(runner, renewal, now=now, account=account)
        before = counts(e)
        with patch.object(Runner, 'refresh_instrument_rules', refresh):
            stamp = coordinator.refresh_instrument_rules()
        assert accounts == [coordinator._committed_account]
        assert stamp == coordinator._profile.instrument_rules.asof
        assert not coordinator._terms_blocked and coordinator._pending_terms is None
        assert counts(e) == before and not creates(e)


def test_genuine_foreign_open_order_blocks_readiness_but_preserves_endpoint_inventory():
    with F.fixture(bind_startup=False, held=True) as e:
        coordinator = build(e)
        foreign = dict(uuid='foreign-open-ask', identifier='foreign-unmanaged-client', market='KRW-BTC',
            side='ask', ord_type='limit', state='wait', created_at=(e.start+timedelta(seconds=1)).isoformat(),
            volume='0.1', remaining_volume='0.1', executed_volume='0', price='10050',
            locked='0.1', paid_fee='0', trades_count=0, trades=[])
        e.exchange.orders.append(foreign)
        e.exchange.balances[1].update(balance='0.9', locked='0.1')
        F.arm_interval(e)
        status = coordinator.bootstrap()
        assert not status.account_source, status.account_source
        result = coordinator._committed_reconciliation
        assert result.status == 'BLOCKED' and result.external_order_ids == ('foreign-open-ask',)
        assert not coordinator._ready and status.new_entry_blocked
        assert coordinator._committed_account.positions[0].units == F.D(1)
        assert coordinator.status().held_symbol == 'KRW-BTC' and not creates(e)


def reviewed_build(e):
    return build(e, evidence=e.evidence, driver=e.driver, implementation_verifier=e.review.implementation,
                 history=e.history, window=e.window, bar_seconds=e.research.protocol.bar_seconds,
                 protective_store=e.protective_store, monitor_until=e.monitor_until)


def test_actual_reviewed_history_and_scheduler_reach_warmup_hold_without_extra_baseline_advance():
    from tests.launch_committed_producer_integration import actual_reviewed_producer_fixture, durable_trace
    with actual_reviewed_producer_fixture(bind_startup=False) as e:
        coordinator = reviewed_build(e)
        F.arm_interval(e)
        coordinator.bootstrap()
        assert coordinator._ready, coordinator.status()
        provider, controller, journal = e.producer._runtime_components()
        startup_runner, binding = e.producer._startup.runner, e.producer._startup._binding
        F.arm_interval(e, end=e.window.start)
        coordinator._quote_source.value = book(e.window.start, received_delta=0, asof_delta=-1,
                                               bid=10000, ask=10010)
        with durable_trace(e) as writes:
            coordinator._slot(e.window.start)
        status = coordinator.status()
        assert status.last_tick is not None, status
        assert status.last_tick.status == 'hold' and status.last_tick.decision_state == 'warmup', status
        assert status.last_tick.decision_cause == 'insufficient_history'
        assert len(e.history._slots) == 1
        assert writes == {'baseline':1, 'guard':1, 'baseline_cas':1, 'guard_cas':1}
        assert e.producer._runtime_components() == (provider, controller, journal)
        assert e.producer._startup.runner is startup_runner and e.producer._startup._binding == binding
        assert coordinator._latest_frame is None and counts(e) == (2, 2) and not creates(e)


def test_slow_actual_current_read_misses_slot_before_history_and_keeps_original_receipt_time():
    from execution_launch.committed_producer import CommittedAccountProducer
    from tests.launch_committed_producer_integration import actual_reviewed_producer_fixture
    with actual_reviewed_producer_fixture(bind_startup=False) as e:
        coordinator = reviewed_build(e)
        F.arm_interval(e)
        coordinator.bootstrap()
        assert coordinator._ready
        F.arm_interval(e, end=e.window.start)
        coordinator._quote_source.value = book(e.window.start, received_delta=0, asof_delta=-1,
                                               bid=10000, ask=10010)
        original = CommittedAccountProducer._current_unit
        def delayed(producer, unit, *, now):
            actual = original(producer, unit, now=now)
            if producer is e.producer:
                e.clock_cell[0] += C.SLOT_WINDOW+timedelta(microseconds=1)
            return actual
        with patch.object(CommittedAccountProducer, '_current_unit', delayed):
            coordinator._slot(e.window.start)
        status = coordinator.status()
        assert status.reasons == ('COORDINATOR_SLOT_WINDOW_MISSED',), status
        assert not e.history._slots and status.last_tick is None
        assert status.account_asof == coordinator._committed_unit.account.observed_at == e.window.start
        assert counts(e) == (2, 2) and not creates(e)


def test_deadline_before_first_runtime_records_real_management_request_without_sale_or_runtime_claim():
    from tests.launch_committed_producer_integration import actual_reviewed_producer_fixture
    with actual_reviewed_producer_fixture(bind_startup=False) as e:
        coordinator = reviewed_build(e)
        e.clock_cell[0] = e.window.end
        coordinator._monitor('monitor')
        status = coordinator.status()
        snapshot = e.protective_store.inspect()
        requests = tuple(item for item in snapshot.outbox if item.kind == 'request_management_approval')
        assert len(requests) == 1 and status.management_request_id == requests[0].intent_id
        assert status.management_deadline_recorded and not status.management_source
        assert coordinator._runner is None and coordinator._provider is None and not coordinator._ready
        assert status.account_source and counts(e) == (0, 0) and not creates(e)
        head = snapshot.head
        assert coordinator._management_deadline(e.clock())
        assert e.protective_store.inspect().head == head
        assert not snapshot.state.can_reduce  # the management request itself grants no sell authority


def test_deadline_storage_failure_never_claims_request_success_or_forces_sale():
    from tests.launch_committed_producer_integration import actual_reviewed_producer_fixture
    with actual_reviewed_producer_fixture(bind_startup=False) as e:
        coordinator = reviewed_build(e)
        e.clock_cell[0] = e.window.end
        def failed_head(*args):
            raise RuntimeError('private management storage detail')
        with patch.object(e.protective_store.head, 'compare_and_set', failed_head):
            coordinator._monitor('monitor')
        status = coordinator.status()
        assert not status.management_deadline_recorded and status.management_request_id is None
        assert status.management_source and status.new_entry_blocked
        assert 'private' not in repr(status)
        assert coordinator._runner is None and not coordinator._ready
        assert counts(e) == (0, 0) and not creates(e)
