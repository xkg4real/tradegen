"""Actual local commits inspected historically, without current account authority.

Temporary Journal/checkpoint/head objects perform real verification. The base
fixture's market, coverage and owner claims are explicitly synthetic. The one
publication fixture uses actual disposable owner signatures; none of these tests
establishes a production source proof or calls an exchange or an actual home.
"""
from contextlib import ExitStack
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta
import threading
from unittest.mock import patch

from execution_accounts import baseline_bridge as B
from execution_accounts.baseline_store import CheckpointStore
from execution_control.store import Journal, Transaction
from execution_launch import committed_account as C
from execution_launch.baseline_head import BaselineHead, CheckpointChain
from execution_launch.continuous_guard_commit import (
    COMPLETE, GuardChain, GuardCheckpointStore, GuardCommitReceipt,
)
from tests import control_continuous_guard_commit as G
from tests import launch_committed_account as F
from tests import launch_committed_generation as S
from tests.control_continuous_guard import build


def inspect(s, provider, now):
    with s.journal.transaction() as tx:
        return provider.inspect_committed(now=now, transaction=tx)


def test_stale_actual_commit_returns_only_original_metadata_without_reconciliation_or_writes():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        now = package['now'] + timedelta(days=2)
        F.refused(lambda: F.read(s, provider, now))
        before = F.files(s)
        with s.journal.transaction() as tx, ExitStack() as blocked:
            for obj, name in ((C, 'reconcile_committed_baseline'),
                              (C.CommittedAccountProvider, 'read'),
                              (Journal, 'transaction'), (Journal, 'snapshot'),
                              (Transaction, 'append'), (CheckpointStore, 'commit'),
                              (CheckpointStore, 'seed'), (GuardCheckpointStore, 'commit'),
                              (GuardCheckpointStore, 'seed'), (BaselineHead, 'compare_and_set'),
                              (BaselineHead, 'initialize_reviewed_head'),
                              (B, 'advance_baseline'), (B, 'initialize_baseline')):
                blocked.enter_context(patch.object(obj, name, side_effect=AssertionError('unexpected operation')))
            result = provider.inspect_committed(now=now, transaction=tx)
            assert provider.inspect_committed(now=now, transaction=tx) == result
        assert F.files(s) == before
        assert type(result) is C.CommittedGenerationInspection and result.execution_ready is False
        assert {field.name for field in fields(result)} == {
            'transaction_id', 'guard_head', 'baseline_head', 'completion_head',
            'receipt_control_head', 'observed_control_head', 'package_sha256',
            'input_sha256', 'asof', 'evaluated_at'}
        assert not any(hasattr(result, name) for name in ('observation', 'risk', 'owner_claim', 'permit'))
        assert result.transaction_id == receipt.transaction_id
        assert result.guard_head == receipt.guard_head and result.baseline_head == receipt.baseline_head
        assert result.completion_head == result.receipt_control_head == result.observed_control_head
        assert result.asof == package['interval'].end and result.evaluated_at == package['now'] < now
        assert result.package_sha256 == C._package_digest(package)
        assert result.input_sha256 == G.rows(s)[0]['data']['input_sha256']
        try:
            result.execution_ready = True
        except (FrozenInstanceError, AttributeError):
            pass
        else:
            raise AssertionError('historical metadata became writable authority')


def test_fresh_account_read_still_returns_original_projection_and_same_durable_bindings():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        current = F.read(s, provider, package['now'])
        historical = inspect(s, provider, package['now'])
        assert type(current) is C.CommittedAccountProjection
        assert current.observation.asof == historical.asof
        for name in ('transaction_id', 'guard_head', 'baseline_head', 'completion_head',
                     'receipt_control_head', 'observed_control_head'):
            assert getattr(current, name) == getattr(historical, name)
        F.refused(lambda: F.read(s, provider, package['now'] + timedelta(seconds=30, microseconds=1)))


def test_restart_new_store_and_head_objects_inspect_without_refreshing_original_time():
    with F.committed() as (s, package, receipt):
        now = package['now'] + timedelta(days=1)
        first = inspect(s, F.provider(s, package, receipt), now)
        before = F.files(s)
        baseline = CheckpointStore(root=s.bstore._root.parent)
        guard = GuardCheckpointStore(root=s.gstore._root.parent)
        restarted = F.provider(s, package, receipt, baseline_store=baseline, guard_store=guard,
            baseline_head=BaselineHead(root=s.bhead._root, name=s.bhead._dir.name,
                                       chain=CheckpointChain(baseline)),
            guard_head=BaselineHead(root=s.ghead._root, name=s.ghead._dir.name, chain=GuardChain(guard)))
        assert inspect(s, restarted, now) == first
        assert F.files(s) == before


def test_only_actual_active_exact_same_journal_thread_bound_transaction_is_accepted():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        now = package['now'] + timedelta(days=1)
        fake = Transaction(s.journal, [], 0)
        F.refused(lambda: provider.inspect_committed(now=now, transaction=fake),
                  'COMMITTED_ACCOUNT_TRANSACTION_REQUIRED')
        with s.journal.transaction() as tx:
            outcomes = []
            thread = threading.Thread(target=lambda: outcomes.append(F.refused(
                lambda: provider.inspect_committed(now=now, transaction=tx),
                'COMMITTED_ACCOUNT_TRANSACTION_REQUIRED')))
            thread.start(); thread.join(timeout=5)
            assert not thread.is_alive() and len(outcomes) == 1
        F.refused(lambda: provider.inspect_committed(now=now, transaction=tx),
                  'COMMITTED_ACCOUNT_TRANSACTION_REQUIRED')
        other = Journal(root=s.journal._root.parent / 'other-control')
        with other.transaction() as tx:
            F.refused(lambda: provider.inspect_committed(now=now, transaction=tx),
                      'COMMITTED_ACCOUNT_TRANSACTION_REQUIRED')


def test_completion_receipt_prefix_and_later_observed_tail_remain_distinct():
    with F.committed() as (s, package, receipt):
        completion = receipt.control_head
        F.risk_row(s, at=package['now'])
        replayed = G.commit(s, package)
        with s.journal.transaction() as tx:
            tail = tx.append('kill', {'session_id': 'fixture-session', 'reason': 'owner_requested'},
                             now=package['now'] + timedelta(seconds=1))
        result = inspect(s, F.provider(s, package, replayed), package['now'] + timedelta(days=1))
        assert result.completion_head == completion
        assert result.receipt_control_head == replayed.control_head != completion
        assert result.observed_control_head == tail['row_sha256'] != replayed.control_head
        assert result.evaluated_at == package['now']


def test_invalid_or_rolled_back_clock_and_future_journal_prefix_are_refused():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        for now in (None, package['now'].replace(tzinfo=None),
                    package['now'] - timedelta(microseconds=1)):
            F.refused(lambda: inspect(s, provider, now))
        with s.journal.transaction() as tx:
            tx.append('kill', {'session_id': 'fixture-session', 'reason': 'owner_requested'},
                      now=package['now'] + timedelta(days=2))
        F.refused(lambda: inspect(s, provider, package['now'] + timedelta(days=1)),
                  'COMMITTED_ACCOUNT_CLOCK_ROLLBACK')


def test_rehashed_package_time_cannot_replace_actual_guard_recorded_at():
    with F.committed() as (s, package, receipt):
        later = package['now'] + timedelta(days=1)
        F.refused(lambda: inspect(s, F.provider(s, package | {'now': later}, receipt), later),
                  'COMMITTED_ACCOUNT_CLOCK_ROLLBACK')
        replayed = G.commit(s, package, now=package['now'] + timedelta(seconds=1))
        result = inspect(s, F.provider(s, package, replayed), later)
        assert result.evaluated_at == package['now'] != later


def test_changed_receipt_predecessors_or_rehashed_endpoint_never_become_historical_proof():
    with F.committed() as (s, package, receipt):
        now = package['now'] + timedelta(days=1)
        before = F.files(s)
        for name in ('transaction_id', 'guard_head', 'baseline_head', 'control_head'):
            F.refused(lambda: inspect(s, F.provider(s, package, replace(receipt, **{name: 'f' * 64})), now))
        for name in ('expected_guard_head', 'expected_baseline_head', 'expected_control_head'):
            F.refused(lambda: inspect(s, F.provider(s, package, receipt, **{name: 'f' * 64}), now))
        capture = package['account_capture']
        endpoint = replace(capture.endpoint_accounts[0], opening_source_sha256='f' * 64)
        altered = package | {'account_capture': replace(capture, endpoint_accounts=(endpoint,)),
            'interval': replace(package['interval'], source_sha256=C.content_digest((endpoint,)))}
        F.refused(lambda: inspect(s, F.provider(s, altered, receipt), now))
        assert F.files(s) == before


def test_incomplete_actual_commit_is_not_repaired_by_inspection_or_an_invented_receipt():
    with G.stack() as s:
        package = build(s.state, s.policy, s.context, ('101',))
        try:
            with G.crash_on_append(COMPLETE):
                G.commit(s, package)
        except G.Crash:
            pass
        else:
            raise AssertionError('missing completion fault did not fire')
        row = G.rows(s)[0]
        receipt = GuardCommitReceipt(transaction_id=row['data']['transaction_id'],
            guard_head=s.ghead.read(), baseline_head=s.bhead.read(), control_head=row['row_sha256'],
            permanently_halted=False, replayed=False)
        before = F.files(s)
        F.refused(lambda: inspect(s, F.provider(s, package, receipt), package['now'] + timedelta(days=1)),
                  'COMMITTED_ACCOUNT_COMPLETION_REQUIRED')
        assert F.files(s) == before


def test_advanced_head_with_rolled_back_checkpoint_refuses_without_repair():
    for name in ('gstore', 'bstore'):
        with G.stack() as s:
            path = getattr(s, name)._root / 'checkpoint.json'
            original = path.read_bytes()
            package = build(s.state, s.policy, s.context, ('101',))
            receipt = G.commit(s, package)
            path.write_bytes(original)
            before = F.files(s)
            F.refused(lambda: inspect(s, F.provider(s, package, receipt), package['now'] + timedelta(days=1)))
            assert F.files(s) == before


def test_stale_inspection_runs_final_store_verification_after_actual_history_check():
    for name in ('gstore', 'bstore'):
        with F.committed() as (s, package, receipt):
            provider = F.provider(s, package, receipt)
            path = getattr(s, name)._root / 'checkpoint.json'
            actual = provider._history
            called = []
            def damage(*args, **kwargs):
                result = actual(*args, **kwargs)
                path.write_bytes(b'{}')
                called.append(True)
                return result
            with patch.object(provider, '_history', damage):
                F.refused(lambda: inspect(s, provider, package['now'] + timedelta(days=1)),
                          'COMMITTED_ACCOUNT_STORE_REFUSED')
            assert called == [True] and path.read_bytes() == b'{}'


def test_head_replacement_during_final_store_load_is_detected_after_the_load():
    with G.stack() as s:
        head = s.ghead._dir / 'head.json'
        old = head.read_bytes()
        package = build(s.state, s.policy, s.context, ('101',))
        receipt = G.commit(s, package)
        provider = F.provider(s, package, receipt)
        actual = s.bstore.load
        called = []
        def change(*args, **kwargs):
            result = actual(*args, **kwargs)
            called.append(True)
            if len(called) == 2:
                head.write_bytes(old)
            return result
        with patch.object(s.bstore, 'load', change):
            F.refused(lambda: inspect(s, provider, package['now'] + timedelta(days=1)),
                      'COMMITTED_ACCOUNT_HEAD_CHANGED')
        assert len(called) == 2 and head.read_bytes() == old


def test_real_journal_append_after_history_is_refused_by_final_event_recheck():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        actual = provider._history
        with s.journal.transaction() as tx:
            def append(*args, **kwargs):
                result = actual(*args, **kwargs)
                tx.append('kill', {'session_id': 'fixture-session', 'reason': 'owner_requested'},
                          now=package['now'])
                return result
            with patch.object(provider, '_history', append):
                F.refused(lambda: provider.inspect_committed(now=package['now'] + timedelta(days=1), transaction=tx),
                          'COMMITTED_ACCOUNT_CONTROL_CHANGED')
            assert tx.events[-1]['kind'] == 'kill'


def test_actual_journal_damage_is_not_hidden_by_transaction_cached_rows():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        path = s.journal._root / 'journal.jsonl'
        with s.journal.transaction() as tx:
            raw = path.read_bytes()
            changed = raw.replace(receipt.transaction_id.encode(), b'f' * 64, 1)
            assert changed != raw and len(changed) == len(raw)
            path.write_bytes(changed)
            F.refused(lambda: provider.inspect_committed(now=package['now'] + timedelta(days=1), transaction=tx))
        assert path.read_bytes() == changed


def test_integrations_changed_after_history_cannot_return_old_valid_metadata():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        actual = provider._history
        def change(*args, **kwargs):
            result = actual(*args, **kwargs)
            provider._guard_store = GuardCheckpointStore(root=s.gstore._root.parent)
            return result
        with patch.object(provider, '_history', change):
            F.refused(lambda: inspect(s, provider, package['now'] + timedelta(days=1)),
                      'COMMITTED_ACCOUNT_INTEGRATIONS_CHANGED')


def test_one_private_generation_is_pinned_even_if_equivalent_generation_replaces_it():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        actual = provider._history
        def change(*args, **kwargs):
            result = actual(*args, **kwargs)
            previous = provider._CommittedAccountProvider__generation
            equivalent = C._generation(previous.package, previous.receipt, previous.expected_guard,
                                       previous.expected_baseline, previous.expected_control)
            assert equivalent == previous and equivalent is not previous
            object.__setattr__(provider, '_CommittedAccountProvider__generation', equivalent)
            return result
        with patch.object(provider, '_history', change):
            F.refused(lambda: inspect(s, provider, package['now'] + timedelta(days=1)),
                      'COMMITTED_ACCOUNT_GENERATION_CHANGED')


def test_final_still_rejects_captured_package_mutation_after_actual_final_event_read():
    with F.committed() as (s, package, receipt):
        provider = F.provider(s, package, receipt)
        actual = provider._events
        calls = []
        def change(*args, **kwargs):
            result = actual(*args, **kwargs)
            calls.append(True)
            if len(calls) == 2:
                provider._CommittedAccountProvider__generation.package['now'] += timedelta(seconds=1)
            return result
        with patch.object(provider, '_events', change):
            F.refused(lambda: inspect(s, provider, package['now'] + timedelta(days=1)),
                      'COMMITTED_ACCOUNT_PACKAGE_CHANGED')
        assert len(calls) == 2


def test_actual_successor_requires_publication_then_inspects_latest_original_bindings():
    with S.fixture() as e:
        successor = S.advance(e, publish=False)
        F.refused(lambda: inspect(e.s, e.provider, successor.now + timedelta(days=1)),
                  'COMMITTED_ACCOUNT_HEAD_CHANGED')
        S.publish(e, successor)
        before = F.files(e.s)
        result = inspect(e.s, e.provider, successor.now + timedelta(days=1))
        assert result.transaction_id == successor.receipt.transaction_id != e.receipt.transaction_id
        assert result.package_sha256 == C._package_digest(successor.package)
        assert result.evaluated_at == successor.now and result.asof == successor.package['interval'].end
        assert result.execution_ready is False and F.files(e.s) == before


def test_later_invalid_lifecycle_and_foreign_policy_remain_rejected_historically():
    for kind in ('lifecycle', 'policy'):
        with F.committed() as (s, package, receipt):
            provider = F.provider(s, package, receipt)
            with s.journal.transaction() as tx:
                if kind == 'lifecycle':
                    tx.append('acknowledged', {'client_id': 'never-reserved', 'order_digest': 'a' * 64,
                        'venue_order_id': 'unknown', 'metadata': {}}, now=package['now'])
                else:
                    data = dict(policy_digest='f' * 64,
                        day=package['now'].astimezone(C.KST).date().isoformat(),
                        high_watermark='120', day_start_equity='100', effective_floor='118',
                        calculated_floor='118', daily_stopped=True, floor_relaxation_approved=False)
                    tx.append('risk_snapshot', data, now=package['now'])
            F.refused(lambda: inspect(s, provider, package['now'] + timedelta(days=1)))
