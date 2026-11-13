"""Actual temporary owner/collector/archive/commit producer integration.

Market GET replies and complete-path coverage are explicitly synthetic. Owner
contexts come from real signed disposable logs at the actual injected clock;
there is no Context/permit/verifier-success patch or retrospective owner read.
Operator setup is separate from producer calls. No real home, key or API is used.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import model as CM, owner
from execution_accounts.baseline import risk_baseline
from execution_accounts.baseline_store import CheckpointStore
from execution_accounts.continuous import COVERAGE_CONTRACT, ContinuousPriceRecorder, PriceMark, VerifiedCoverage
from execution_accounts.model import RiskBaseline, content_digest
from execution_control.dry_run import DryRunAdapter
from execution_control.risk import RecoveryCondition
from execution_control.store import GENESIS, Journal
from execution_launch import committed_producer as P
from execution_launch import guard_generation_archive as A
from execution_launch import continuous_guard_commit as GC
from execution_launch.account_interval import ContinuousUpbitCandidateSource
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard import GuardAnchor, reviewed_guard_anchor
from execution_launch.profile import PolicyInputs, risk_policy
from execution_orders import upbit
from tests import compliance_fixtures as CF
from tests import launch_account_interval as I
from tests import launch_guard_capture_archive as CA
from tests import launch_research_bundle_store as B
from tests.launch_baseline_head import head_root
from tests.launch_profile import fixture_profile

D = Decimal
START = I.at(26, 20)


def default_profile(start=START):
    return replace(fixture_profile(start), profile_id='producer-fixture', account_scope=I.SCOPE,
        policy=PolicyInputs(version='producer-synthetic-v1', source_sha256='a'*64,
            initial_equity=D('70000'), drawdown_activation_equity=D('6000000'),
            positive_profit_loss_fraction=D('.35'), peak_drawdown_fraction=D('.35'),
            zero_profit_day_target_fraction=D('.3'), first_day_loss_budget=D('10000'),
            zero_profit_day_loss_budget=D('10000'), recovery_condition=RecoveryCondition(
                cutoff_seconds=79200, timezone='Asia/Seoul', reference='day_start_marked_equity')))


@contextmanager
def fixture(*, held=False, start=START, auto_setup=True, bind_startup=True,
            profile=None, profile_transform=None, clock_step=timedelta(0), configure=None):
    with B.fixture(storage_limits=CA.limits()) as storage, CF.temp_home() as home, head_root() as hroot:
        with CF.pubkey_at(home/'fixture-owner.pem'):
            key = CF.full_home(home, limits={'total_loss_floor_krw':70000.0, 'daily_loss_krw':10000.0})
            if configure is not None:
                configure(home, key, start)
            profile = default_profile(start) if profile is None else profile
            if profile_transform is not None:
                profile = profile_transform(profile)
            clock_cell = [start-timedelta(seconds=5)]
            def clock():
                now = clock_cell[0]
                clock_cell[0] += clock_step
                return now
            exchange = I.FakeUpbit(cash='89995', btc='1', orders=(I.BUY,)) if held else I.FakeUpbit()
            exchange.clock = clock
            e = SimpleNamespace(home=home, hroot=hroot, head_root=hroot, storage=storage,
                archive_store=storage.store, store=storage.store, key=key, profile=profile,
                policy=risk_policy(profile), clock=clock, clock_cell=clock_cell, clock_step=clock_step,
                exchange=exchange, anchor=replace(I.ANCHOR), coverage=replace(I.COVERAGE),
                trade_fees=() if held else I.FEES, start=start, held=held, recorder=None,
                supplier_calls=[], raw_receipts=[], owner_calls=[], unit=None)
            class Source:
                account_scope = I.SCOPE
                def fetch(self, path, params):
                    receipt = exchange.fetch(path, params)
                    e.raw_receipts.append(receipt)
                    return receipt
            def path_source(previous, capture, end):
                assert e.recorder is not None and previous.state_digest == e.recorder._args['previous_state_digest']
                return e.recorder.seal(end=end, watermark_sequence=e.next_sequence,
                    watermark_received_at=capture.observed_at, watermark_source_sha256='a'*64)
            def synthetic_coverage(request, path):
                return VerifiedCoverage(request_sha256=content_digest(request), contract=COVERAGE_CONTRACT,
                    authority_sha256='b'*64, source_proof_sha256='c'*64, verified_at=path.watermark_received_at)
            def inputs(*, previous, now):
                e.supplier_calls.append((previous, now))
                return P.ProducerCaptureInputs(anchor=e.anchor, coverage=e.coverage, trade_fees=e.trade_fees)
            e.capture_inputs_source = inputs
            e.collector = Source()
            e.source = ContinuousUpbitCandidateSource(path_source=path_source,
                coverage_verifier=synthetic_coverage, archive_root=home)
            legacy = Journal()
            with legacy.transaction():  # explicit test operator setup, never a producer default
                pass
            e.journal = Journal(root=legacy._root, require_existing=True)
            e.baseline_store, e.guard_store = CheckpointStore(root=home), GC.GuardCheckpointStore(root=home)
            e.baseline_head = BaselineHead(root=hroot, name='producer-baseline', chain=CheckpointChain(e.baseline_store))
            e.guard_head = BaselineHead(root=hroot, name='producer-guard', chain=GC.GuardChain(e.guard_store))
            e.adapter = DryRunAdapter(upbit)
            e.args = dict(archive_store=e.store, journal=e.journal, guard_store=e.guard_store,
                guard_head=e.guard_head, baseline_store=e.baseline_store, baseline_head=e.baseline_head,
                profile=profile, adapters={'upbit':e.adapter}, isolated_state_root=home, clock=clock,
                candidate_source=e.source, collector_source=e.collector, capture_inputs_source=inputs)
            e.producer = P.CommittedAccountProducer(**e.args)
            if bind_startup:
                e.producer._bind_startup(session_provider=lambda _:None)
            equity = D('100045') if held else D('100090')
            e.probe = RiskBaseline(day_start_equity=equity, prior_high_watermark=equity,
                observed_daily_loss=D(0), approved_effective_floor=D('70000'), first_trading_day=I.FIRST_DAY,
                asof=clock_cell[0], source_sha256='b'*64)
            actual_owner = owner.load_context
            def observed(now, positions, **kwargs):
                e.owner_calls.append((now, deepcopy(positions), kwargs.get('session_id')))
                return actual_owner(now, positions, **kwargs)
            with patch.object(owner, 'load_context', side_effect=observed), \
                 patch('execution_accounts.upbit_collector.request', side_effect=AssertionError('network forbidden')):
                e.opening = e.producer.observe_opening(risk_baseline=e.probe)
                if auto_setup:
                    seed_setup(e)
                yield e


def seed_setup(e):
    """Explicit operator: a separate real collection AFTER actual opening owner completion."""
    e.clock_cell[0] = e.start
    assert e.opening.completed_at <= e.start
    equity = D('100045') if e.held else D('100090')
    state, _, _, collection = I.seed(e.home, e.exchange, e.trade_fees, e.start,
        day_start=equity, high=equity, loss=D(0), realized=D(0) if e.held else D('90'),
        day_open=D(0), previous=None)
    e.exchange.clock = e.clock
    e.setup_collection, e.state = collection, state
    e.baseline_head.initialize_reviewed_head(state.state_digest)
    rows = e.journal.snapshot()
    anchor = GuardAnchor(baseline_state_sha256=state.state_digest,
        control_journal_head_sha256=rows[-1]['row_sha256'] if rows else GENESIS,
        high_watermark=state.high_watermark, day_start_equity=state.day_start_equity,
        observed_daily_loss=state.observed_daily_loss, applied_floor_krw=state.high_watermark,
        daily_stopped=False, permanently_halted=False, recorded_at=e.start, source_sha256='7'*64)
    guarded = reviewed_guard_anchor(anchor, baseline=state, policy=e.policy, owner=e.opening.owner_claim)
    e.guard_store.seed(guarded, expected_head=guarded.state_sha256)
    e.guard_head.initialize_reviewed_head(guarded.state_sha256)
    e.initial_guard = guarded


def arm_interval(e, *, end=None, events=()):
    """Prepare a real recorder before production; no collector/publisher return is patched."""
    previous = e.baseline_store.load(expected_head=e.baseline_head.read())
    guarded = e.guard_store.load(expected_head=e.guard_head.read())
    end = previous.asof+timedelta(seconds=5) if end is None else end
    e.clock_cell[0] = end
    sequence = guarded.next_sequence if guarded.next_sequence is not None else 10
    e.recorder = ContinuousPriceRecorder(account_scope=I.SCOPE, stream_epoch='producer-synthetic-epoch',
        previous_state_digest=previous.state_digest, start=previous.asof,
        opening_marks=(PriceMark(symbol='KRW-BTC', price=D(e.exchange.ticker), asof=previous.asof),),
        first_sequence=sequence)
    for event in events:
        e.recorder.append(event)
    e.next_sequence = sequence+len(events)
    e.now, e.rules = end, e.profile.instrument_rules
    return previous


def advance(e, *, end=None, events=()):
    arm_interval(e, end=end, events=events)
    e.unit = e.producer._collect_current()
    e.now = e.unit.completed_at
    return e.unit


def refused(call, code=None):
    try:
        call()
    except P.CommittedProducerError as exc:
        if code is not None:
            assert str(exc) == 'COMMITTED_PRODUCER_'+code, (str(exc), code)
        return str(exc)
    raise AssertionError('expected producer refusal')


def durable(e):
    return B.files(e.home), B.files(e.hroot), B.files(e.storage.base)


def test_actual_opening_precedes_separate_setup_and_two_committed_intervals_keep_runtime_identity():
    with fixture(clock_step=timedelta(microseconds=1)) as e:
        assert e.opening.observed_at <= e.opening.completed_at < e.state.asof
        first = advance(e)
        provider, controller, journal = e.producer._runtime_components()
        second = advance(e)
        assert e.producer._runtime_components() == (provider, controller, journal)
        assert first.transaction_id != second.transaction_id
        assert first.account.observed_at < second.account.observed_at
        assert second.reconciliation.status == 'RECONCILED'
        assert all(x.execution_ready is False and x.source_authenticated is False for x in (e.opening, first, second))
        kinds = [r['kind'] for r in e.journal.snapshot()]
        assert kinds.count(GC.PREPARE) == kinds.count(GC.COMPLETE) == 2
        assert e.baseline_store.load(expected_head=e.baseline_head.read()).sequence == 2
        assert e.owner_calls and all(a[0] <= b[0] for a,b in zip(e.owner_calls,e.owner_calls[1:]))


def test_actual_held_owner_positions_and_original_endpoint_survive_publication():
    with fixture(held=True) as e:
        unit = advance(e)
        assert unit.account.positions[0].units == D(1)
        assert e.owner_calls[0][1].holdings[('upbit','BTC')] == 1.0
        paired, endpoint, reconciled = e.producer._current_unit(unit, now=e.clock())
        assert endpoint == unit.account and paired.account.holdings[('upbit',I.SCOPE,'spot','KRW-BTC')] == D(1)
        assert paired.committed.transaction_id == unit.transaction_id and paired.risk is None


def test_opening_does_not_seed_any_guard_baseline_or_head():
    with fixture(auto_setup=False) as e:
        assert e.producer.status().phase == 'OPENING_OBSERVED'
        assert not (e.baseline_store._root/'checkpoint.json').exists()
        assert not (e.guard_store._root/'checkpoint.json').exists()
        assert e.journal.snapshot() == ()


def test_existing_mode_and_source_scope_are_checked_before_observation():
    with fixture() as e:
        before = durable(e)
        refused(lambda:P.CommittedAccountProducer(**(e.args|{'journal':Journal(root=e.journal._root)})), 'REHEARSAL_REQUIRED')
        e.collector.account_scope = 'other'
        refused(lambda:e.producer._collect_current(), 'DEPENDENCY_CHANGED')
        assert durable(e) == before


def test_missing_private_opening_cannot_be_reconstructed_from_public_owner_claim():
    with fixture() as e:
        app = P.CommittedAccountProducer(**e.args)
        app._bind_startup(session_provider=lambda _:None)
        before = durable(e)
        refused(app._collect_current, 'OPENING_REQUIRED')
        assert durable(e) == before


def test_post_start_real_owner_observation_is_not_backdated_to_old_baseline():
    with fixture() as e:
        app = P.CommittedAccountProducer(**e.args)
        app._bind_startup(session_provider=lambda _:None)
        e.clock_cell[0] = e.start+timedelta(seconds=1)
        app.observe_opening(risk_baseline=replace(e.probe, asof=e.start))
        before = durable(e)
        refused(app._collect_current, 'OWNER_INTERVAL_NOT_BRACKETED')
        assert durable(e) == before


def test_supplier_wrong_type_and_original_configuration_mutation_refuse_before_collection():
    for kind in ('type', 'scope', 'rollback'):
        with fixture() as e:
            actual = e.capture_inputs_source
            def bad(*, previous, now):
                if previous is not None:
                    if kind == 'type': return {'anchor':e.anchor}
                    if kind == 'scope': e.collector.account_scope = 'other'
                    if kind == 'rollback': e.clock_cell[0] = now-timedelta(seconds=1)
                return actual(previous=previous, now=now)
            # Construct a real new producer before its real opening; no private issuer insertion.
            app = P.CommittedAccountProducer(**(e.args|{'capture_inputs_source':bad}))
            app._bind_startup(session_provider=lambda _:None)
            # Its opening is at the existing asof, so no retrospective observation.
            e.clock_cell[0] = e.start
            app.observe_opening(risk_baseline=replace(e.probe, asof=e.start))
            before_count = len(e.exchange.calls)
            refused(app._collect_current)
            assert len(e.exchange.calls) == before_count


def test_capture_inputs_are_detached_and_supplier_called_once_per_unit():
    with fixture() as e:
        unit = advance(e)
        assert len(e.supplier_calls) == 2 and e.supplier_calls[0][0] is None
        previous = e.supplier_calls[1][0]
        assert previous == e.state and previous is not e.state
        assert unit.account.account_scope == I.SCOPE


def test_copied_descriptive_unit_cannot_replace_actual_current_generation():
    with fixture() as e:
        unit = advance(e)
        refused(lambda:e.producer._current_unit(replace(unit), now=e.clock()), 'DEPENDENCY_CHANGED')
        second = advance(e)
        refused(lambda:e.producer._current_unit(unit, now=e.clock()), 'DEPENDENCY_CHANGED')
        assert second.transaction_id != unit.transaction_id


def test_old_source_after_slow_input_retention_does_not_gain_fresh_time_or_commit():
    with fixture() as e:
        actual = A.retain_guard_input
        def slow(*args, **kwargs):
            result = actual(*args, **kwargs)
            e.clock_cell[0] += timedelta(seconds=31)
            return result
        with patch.object(A,'retain_guard_input',side_effect=slow):
            refused(lambda:advance(e), 'STALE')
        assert not any(r['kind']==GC.PREPARE for r in e.journal.snapshot())
        assert e.producer.status().input_archive_digest is not None


def test_completion_retention_failure_keeps_actual_commit_and_never_reuses_old_account():
    with fixture() as e:
        old_guard = e.guard_head.read()
        with patch.object(A,'record_guard_completion',side_effect=OSError('private failure text')):
            refused(lambda:advance(e), 'COMMIT_UNCONFIRMED')
        assert e.guard_head.read() != old_guard
        assert [r['kind'] for r in e.journal.snapshot()].count(GC.COMPLETE) == 1
        assert e.producer.status().completion_archive_digest is None
        refused(e.producer._collect_current, 'OPENING_REQUIRED')


def test_actual_current_owner_change_between_intervals_refuses_before_second_commit():
    with fixture() as e:
        advance(e)
        CF.sign(e.key,'limit_set',{'total_loss_floor_krw':100080.0,'daily_loss_krw':9000.0},
                utc=CM.iso_utc(e.clock()))
        refused(lambda:advance(e))
        assert [r['kind'] for r in e.journal.snapshot()].count(GC.COMPLETE) == 1


def test_original_claim_and_capture_timestamp_are_distinct_from_completion():
    with fixture(clock_step=timedelta(microseconds=1)) as e:
        unit = advance(e)
        saved = A.read_guard_completion(e.store,unit.completion_archive_digest,
            expected_input_archive_digest=unit.input_archive_digest)
        package = saved.retained_input.package
        assert package['owner_before'].observed_at == e.opening.observed_at
        assert package['path'].end <= package['owner_after'].observed_at <= package['now']
        assert package['now'] <= saved.record.recorded_at <= unit.completed_at
        assert package['account_capture'].endpoint_accounts[0].observed_at == unit.account.observed_at


def test_public_opening_mutation_does_not_change_private_owner_provenance():
    with fixture() as e:
        object.__setattr__(e.opening.owner_claim,'owner_head_sha256','f'*64)
        result = advance(e)
        saved = A.read_guard_input(e.store,result.input_archive_digest)
        assert saved.package['owner_before'].owner_head_sha256 != 'f'*64


def test_legacy_continuous_provider_is_never_called_by_committed_production():
    from execution_accounts.baseline_bridge import ContinuousAccountProvider
    with fixture() as e, patch.object(ContinuousAccountProvider,'__call__',side_effect=AssertionError('legacy advance forbidden')):
        one = advance(e)
        two = advance(e)
        assert one.transaction_id != two.transaction_id


def test_changed_actual_control_prefix_gets_one_genuine_reconciliation_not_old_readiness():
    with fixture() as e:
        unit = advance(e)
        _, controller, _ = e.producer._runtime_components()
        controller.observe(now=e.clock())  # actual harmless durable risk suffix
        assert e.journal.snapshot()[-1]['row_sha256'] != unit.reconciliation.final_control_head
        actual = e.producer._startup._reconcile_runtime
        calls = []
        def counted(*args, **kwargs):
            calls.append(True)
            return actual(*args, **kwargs)
        with patch.object(e.producer._startup,'_reconcile_runtime',side_effect=counted):
            paired, endpoint, reconciled = e.producer._current_unit(unit, now=e.clock())
        assert len(calls) == 1 and reconciled.status == 'RECONCILED'
        assert paired.committed.observed_control_head == reconciled.final_control_head
        assert reconciled.final_control_head != unit.reconciliation.final_control_head
        assert endpoint == unit.account


def test_final_current_read_checks_required_cutoff_after_actual_owner_completion():
    from execution_control.controller import Controller
    with fixture(start=I.at(26,21,59,40)) as e:
        unit = advance(e)
        e.clock_cell[0] = I.at(26,21,59,59)
        actual_read = Controller.read_committed_account
        actual_configuration = e.producer._configuration
        completed = []
        def read(*args, **kwargs):
            result = actual_read(*args, **kwargs)
            completed.append(True)
            return result
        def delayed_configuration():
            actual_configuration()
            if completed:
                e.clock_cell[0] = I.at(26,22)
        with patch.object(Controller,'read_committed_account',side_effect=read), \
             patch.object(e.producer,'_configuration',side_effect=delayed_configuration):
            refused(lambda:e.producer._current_unit(unit,now=e.clock()), 'STALE')
        assert completed and unit.account.observed_at == I.at(26,21,59,45)
        assert I.at(26,22)-unit.account.observed_at < timedelta(seconds=30)


def test_invalid_opening_baseline_refuses_before_supplier_or_collector():
    with fixture() as e:
        def forbidden(**kwargs):
            raise AssertionError('supplier must not run')
        app = P.CommittedAccountProducer(**(e.args|{'capture_inputs_source':forbidden}))
        calls = len(e.exchange.calls)
        huge = replace(e.probe, prior_high_watermark=D('1E+1000000000'))
        refused(lambda:app.observe_opening(risk_baseline=huge), 'INPUT_INVALID')
        extra = replace(e.probe)
        object.__setattr__(extra,'unknown','bad')
        refused(lambda:app.observe_opening(risk_baseline=extra), 'INPUT_INVALID')
        assert len(e.exchange.calls) == calls


def test_supplier_cannot_mutate_the_original_already_admitted_opening_baseline():
    with fixture() as e:
        original = replace(e.probe)
        def changing(*, previous, now):
            object.__setattr__(original,'source_sha256','bad')
            return e.capture_inputs_source(previous=previous,now=now)
        app = P.CommittedAccountProducer(**(e.args|{'capture_inputs_source':changing}))
        observed = app.observe_opening(risk_baseline=original)
        assert original.source_sha256 == 'bad'
        assert observed.source_authenticated is False and observed.account_asof >= e.probe.asof
