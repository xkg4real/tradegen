"""Actual paired Controller reads with disposable signed owners and stores.

Prices, account pages and coverage are synthetic. Actual local owner folds,
guard commits, retained heads and Controller transactions are exercised; a
returned descriptive view is never substituted for an authorization result.
"""
from contextlib import ExitStack
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
from unittest.mock import patch

from core.compliance import model as M, owner
from execution_accounts.baseline_store import CheckpointStore
from execution_control import controller as C
from execution_control.controller import CommittedControllerObservation, Controller
from execution_control.store import Journal, Transaction
from execution_control.capability import digest
from execution_launch.baseline_head import BaselineHead
from execution_launch.continuous_guard_commit import GuardCheckpointStore
from tests import compliance_fixtures as CF, control_committed_account as F
from tests import control_continuous_guard as GF
from tests.control_committed_completion import guard_files


def risk_rows(e):
    return tuple(row for row in F.rows(e) if row['kind'] in ('risk_snapshot', 'halt'))


def prior_stricter_floor(home, key, start):
    """Actual precommit control fact; no synthetic current owner context."""
    data = dict(policy_digest=digest(GF.policy()), day=start.astimezone(M.KST).date().isoformat(),
        high_watermark='120', day_start_equity='100', effective_floor='120',
        calculated_floor='120', daily_stopped=False, floor_relaxation_approved=False)
    with Journal().transaction() as tx:
        tx.append('risk_snapshot', data, now=start)


def test_observe_pairs_final_actual_read_with_one_snapshot_and_original_timestamps():
    with F.fixture() as e:
        before = guard_files(e)
        actual_read, reads = e.provider.read, []
        def recording(**kwargs):
            result = actual_read(**kwargs)
            reads.append(result)
            return result
        e.clock_cell[0] = e.now + timedelta(seconds=1)
        with patch.object(e.provider, 'read', recording), ExitStack() as stack:
            for cls, name in ((CheckpointStore, 'commit'), (GuardCheckpointStore, 'commit'),
                              (BaselineHead, 'compare_and_set'), (Journal, 'snapshot')):
                stack.enter_context(patch.object(cls, name, side_effect=AssertionError('unexpected advancement')))
            with patch.object(e.s.journal, 'transaction', wraps=e.s.journal.transaction) as tx:
                view = e.controller.observe_committed(now=e.now)
                assert tx.call_count == 1
        assert type(view) is CommittedControllerObservation and len(reads) >= 2
        assert view.committed is reads[-1] and view.account is reads[-1].observation
        assert view.account.asof == view.account.risk.asof == e.now
        assert view.completed_at == e.clock_cell[0] and view.completed_at > view.account.asof
        assert not view.execution_ready and not view.committed.execution_ready
        assert view.risk.high_watermark == view.account.risk.prior_high_watermark == F.D(101)
        assert view.committed.completion_head == e.receipt.control_head
        assert view.committed.observed_control_head != e.receipt.control_head
        assert len(risk_rows(e)) == 1 and guard_files(e) == before and not e.adapter.requests
        assert 'synthetic-guard-account' not in repr(view) and 'AccountObservation' not in repr(view)


def test_observe_retains_daily_stop_and_recovered_peak_halt_without_advancing_stores():
    for options, reason, high in (({'daily_stopped': True}, 'PERSISTENT_DAILY_STOP', F.D(101)),
                                 ({'prices': ('110', '105', '115')}, 'PERSISTENT_HALT', F.D(115))):
        with F.fixture(**options) as e:
            before = guard_files(e)
            first = e.controller.observe_committed(now=e.now)
            second = e.controller.observe_committed(now=e.now)
            assert first.risk == second.risk and reason in first.risk.reasons
            assert first.risk.new_entry_blocked and first.risk.protective_action_needed
            assert first.risk.high_watermark == first.account.risk.prior_high_watermark == high
            assert first.risk.effective_floor == high
            if reason == 'PERSISTENT_DAILY_STOP':
                assert first.committed.daily_stopped and first.account.risk.observed_daily_loss == 0
                assert not first.account.risk.halted
            else:
                assert first.account.risk.halted
            assert guard_files(e) == before and not e.adapter.requests


def test_account_only_read_has_no_risk_evaluation_or_control_writes():
    with F.fixture(daily_stopped=True) as e:
        before, protected = F.rows(e), guard_files(e)
        with patch.object(Controller, '_snapshot_risk', side_effect=AssertionError('entry-risk write')), \
             patch.object(Controller, '_risk_view', side_effect=AssertionError('entry-risk equality')), \
             patch.object(Transaction, 'append', side_effect=AssertionError('account-read append')), \
             patch.object(Journal, 'snapshot', side_effect=AssertionError('nested snapshot')):
            view = e.controller.read_committed_account(now=e.now, session_id='explicit-exit')
        assert view.risk is None and view.committed.daily_stopped and not view.execution_ready
        assert view.account.asof == e.now and view.completed_at == e.now
        assert F.rows(e) == before and guard_files(e) == protected and not e.adapter.requests


def test_account_only_read_retains_prior_stricter_floor_without_creating_owner_halt():
    with F.fixture(configure=prior_stricter_floor, control_prefix=True) as e:
        before, owner_log = F.rows(e), owner.log_path().read_bytes()
        view = e.controller.read_committed_account(now=e.now, session_id='explicit-exit')
        assert view.risk is None and view.account.risk.equity == F.D(101)
        assert view.account.risk.approved_effective_floor == F.D(120)
        assert view.account.risk.prior_high_watermark == F.D(120) and not view.account.risk.halted
        assert not any(row['kind'] == 'halt' for row in before)
        assert F.rows(e) == before and owner.log_path().read_bytes() == owner_log


def test_account_read_accepts_valid_conservative_suffix_without_observe_result_gate():
    with F.fixture() as e:
        inserted = []
        actual_read = e.provider.read
        def suffix(**kwargs):
            result = actual_read(**kwargs)
            if not inserted:
                kwargs['transaction'].append('risk_snapshot', dict(policy_digest=digest(e.s.policy),
                    day=e.now.astimezone(M.KST).date().isoformat(), high_watermark='120',
                    day_start_equity='100', effective_floor='120', calculated_floor='120',
                    daily_stopped=True, floor_relaxation_approved=False), now=e.now)
                inserted.append(True)
            return result
        with patch.object(e.provider, 'read', suffix):
            view = e.controller.read_committed_account(now=e.now)
        assert inserted and view.risk is None and view.committed.daily_stopped
        assert view.account.risk.approved_effective_floor == F.D(120)
        assert len(risk_rows(e)) == 1 and not any(row['kind'] == 'halt' for row in F.rows(e))


def test_actual_operation_session_reaches_all_initial_and_final_owner_reads():
    for method in ('observe_committed', 'read_committed_account'):
        with F.fixture() as e:
            actual, sessions = owner.load_context, []
            def current(*args, **kwargs):
                result = actual(*args, **kwargs)
                sessions.append(kwargs.get('session_id'))
                return result
            with patch.object(owner, 'load_context', current):
                getattr(e.controller, method)(now=e.now, session_id='paired-actual-session')
            assert len(sessions) >= 2 and set(sessions) == {'paired-actual-session'}


def test_session_scoped_actual_effective_limits_cannot_be_replaced_by_unscoped_view():
    start = datetime(2026, 11, 7, 20, tzinfo=M.KST)
    def configure(home, key, at):
        CF.sign(key, 'session_armed', {'session_id': 'previously-armed'}, M.iso_utc(at-timedelta(days=2)))
        CF.sign(key, 'limit_set', {'total_loss_floor_krw': 90.0, 'daily_loss_krw': 20.0},
                M.iso_utc(at-timedelta(days=1)))
    with F.fixture(start=start, configure=configure, pol=GF.policy(initial='50', activation='50')) as e:
        assert e.controller.read_committed_account(now=e.now).risk is None
        before = F.rows(e)
        for method in ('observe_committed', 'read_committed_account'):
            F.refused(lambda method=method: getattr(e.controller, method)(now=e.now,
                session_id='previously-armed'), 'COMMITTED_ACCOUNT_EFFECTIVE_LIMITS_CHANGED')
        assert F.rows(e) == before and not e.adapter.requests


def test_legacy_callable_and_replaced_committed_provider_cannot_issue_paired_views():
    with F.fixture() as e:
        account = F.PF.read(e.s, e.provider, e.now).observation
        legacy = Controller(journal=e.s.journal, account_provider=lambda _: account, policy=e.s.policy,
            adapters={'upbit': e.adapter}, session_provider=lambda _: None)
        e.controller.account_provider = lambda _: account
        before = F.rows(e)
        for controller in (legacy, e.controller):
            for method in ('observe_committed', 'read_committed_account'):
                F.refused(lambda controller=controller, method=method:
                    getattr(controller, method)(now=e.now), 'COMMITTED_OBSERVATION_PROVIDER_REQUIRED')
        assert F.rows(e) == before and not e.adapter.requests


def test_legacy_constructed_controller_cannot_gain_paired_reads_by_provider_substitution():
    with F.fixture() as e:
        account = F.PF.read(e.s, e.provider, e.now).observation
        before = F.rows(e)
        for clock in (None, e.clock):
            legacy = Controller(journal=e.s.journal, account_provider=lambda _: account, policy=e.s.policy,
                adapters={'upbit': e.adapter}, session_provider=lambda _: None, clock=clock)
            legacy.account_provider = e.provider
            with patch.object(e.provider, 'read', side_effect=AssertionError('unbound provider read')), \
                 patch.object(owner, 'load_context', side_effect=AssertionError('unbound owner read')):
                for method in ('observe_committed', 'read_committed_account'):
                    F.refused(lambda method=method: getattr(legacy, method)(now=e.now),
                              'COMMITTED_OBSERVATION_PROVIDER_REQUIRED')
        assert F.rows(e) == before and not e.adapter.requests


def test_mutated_returned_view_is_not_reused_as_holdings_or_order_authority():
    with F.fixture() as e:
        view = e.controller.read_committed_account(now=e.now)
        try:
            view.completed_at = e.now + timedelta(days=1)
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError('paired value must be frozen')
        enlarged = replace(view.account, holdings={key: F.D(1000) for key in view.account.holdings})
        object.__setattr__(view, 'account', enlarged)
        again = e.controller.read_committed_account(now=e.now)
        assert again.account.holdings != view.account.holdings
        assert tuple(again.account.holdings.values()) == (F.D(1),)
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            F.refused(lambda: e.controller.reserve(replace(e.order, quantity=F.D(2)), e.rules,
                session_id='explicit-exit', now=e.now))
            assert issued.call_count == 0
        assert not e.adapter.requests and not any(row['kind'] == 'reserved' for row in F.rows(e))


def test_completed_view_cannot_hide_later_actual_owner_change():
    with F.fixture() as e:
        view = e.controller.read_committed_account(now=e.now)
        CF.sign(e.key, 'age_of_majority', {'birth_date': '2000-01-01', 'evidence': 'fixture'})
        before = F.rows(e)
        with patch.object(C, '_issue', wraps=C._issue) as issued:
            F.refused(lambda: e.controller.reserve(e.order, e.rules, session_id='explicit-exit', now=e.now),
                      'COMMITTED_ACCOUNT_OWNER_EPOCH_CHANGED')
            assert issued.call_count == 0
        assert not view.execution_ready and F.rows(e) == before and not e.adapter.requests


def test_account_only_completion_counts_actual_owner_delay_without_restamping():
    with F.fixture() as e:
        actual, observed = owner.load_context, []
        def slow(*args, **kwargs):
            result = actual(*args, **kwargs)
            observed.append(result.owner.head)
            e.clock_cell[0] = e.now + timedelta(seconds=30, microseconds=1)
            return result
        before = F.rows(e)
        with patch.object(owner, 'load_context', slow):
            F.refused(lambda: e.controller.read_committed_account(now=e.now), 'COMMITTED_COMPLETION_STALE')
        assert observed and F.rows(e) == before and not e.adapter.requests
