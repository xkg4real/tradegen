"""Focused startup boundaries over actual disposable archived/committed data.

The account/path/coverage source is explicitly synthetic; all archive reads,
Journal/checkpoint validation and owner signatures use actual implementations.
No real credentials, broker calls, issued-session insertion or positive verifier.
"""
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch

from execution_control import controller as C
from execution_control.dry_run import DryRunAdapter
from execution_control.store import Journal
from execution_launch import committed_startup as S
from execution_launch import guard_generation_archive as A
from execution_launch import guard_generation_format as G
from execution_orders import upbit
from tests import launch_guard_generation_archive as F
from tests.launch_research_bundle_store import files


def startup(e, **changes):
    args = dict(archive_store=e.store, journal=e.journal, guard_store=e.guard_store,
        guard_head=e.guard_head, baseline_store=e.baseline_store, baseline_head=e.baseline_head,
        profile=e.profile, adapters={'upbit': DryRunAdapter(upbit)}, isolated_state_root=e.home,
        clock=e.clock)
    return S.CommittedStartup(**(args | changes))


def refused(call, code=None):
    try:
        call()
    except S.CommittedStartupError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('expected fixed startup refusal')


def snapshot(e):
    return files(e.home), files(e.head_root), files(e.storage.base)


def publish_claim(e, record):
    """Write a real, format-valid untrusted claim; never fake commit authority."""
    raw = G.completion_bytes(record)
    manifest, digest, payloads = A._manifest(e.store, raw, G.completion_digest(record),
                                            e.input.archive_digest, 'completion')
    e.store.archive_raw(manifest, payloads)
    return digest


def test_constructor_rejects_nonactual_archive_before_its_configuration_hook():
    with F.fixture() as e:
        called = []
        class Trap:
            def _configuration(self):
                called.append(True)
                raise AssertionError('must not invoke a foreign object')
        refused(lambda: startup(e, archive_store=Trap()), 'STARTUP_INPUT_INVALID')
        assert called == []


def test_constructor_rejects_non_dry_adapter_before_any_adapter_operation():
    with F.fixture() as e:
        called = []
        class Trap:
            def prepare_status(self, *args, **kwargs):
                called.append(True)
        refused(lambda: startup(e, adapters={'upbit': Trap()}), 'STARTUP_REHEARSAL_REQUIRED')
        assert called == []


def test_startup_requires_actual_existing_only_journal_configuration():
    with F.fixture() as e:
        legacy = Journal(root=e.journal._root)
        before = snapshot(e)
        refused(lambda: startup(e, journal=legacy), 'STARTUP_REHEARSAL_REQUIRED')
        assert snapshot(e) == before


def test_completed_historical_inspection_does_not_authenticate_current_owner():
    with F.fixture(completed=True) as e:
        app = startup(e)
        before = snapshot(e)
        with patch.object(C.owner, 'load_context', side_effect=AssertionError('historical inspect must not authorize')):
            result = app.inspect(e.input.archive_digest, e.completion.archive_digest)
        assert result.durable_status == 'CONSISTENT' and result.current_status == 'FRESH'
        assert result.execution_ready is False and result.source_authenticated is False
        assert result.asof == e.package['interval'].end and app.provider is None
        assert snapshot(e) == before


def test_valid_receipt_does_not_authenticate_forged_completion_row_hash():
    with F.fixture(completed=True) as e:
        forged = publish_claim(e, replace(e.completion.record, completion_head='f'*64))
        before = snapshot(e)
        refused(lambda: startup(e).inspect(e.input.archive_digest, forged), 'STARTUP_BINDING_CHANGED')
        assert snapshot(e) == before


def test_saved_tail_must_be_an_actual_post_receipt_prefix():
    with F.fixture(completed=True) as e:
        forged = publish_claim(e, replace(e.completion.record, observed_control_head=e.expected_control_head))
        before = snapshot(e)
        refused(lambda: startup(e).inspect(e.input.archive_digest, forged), 'STARTUP_BINDING_CHANGED')
        assert snapshot(e) == before


def test_benign_actual_suffix_does_not_require_saved_tail_equal_current_tail():
    with F.fixture(completed=True) as e:
        at = e.clock()+timedelta(seconds=1)
        with e.journal.transaction() as tx:
            tx.append('halt', {'floor':str(e.package['owner_after'].signed_floor_krw)}, now=at)
        e.clock_cell[0] = at
        before = snapshot(e)
        result = startup(e).inspect(e.input.archive_digest, e.completion.archive_digest)
        assert result.durable_status == 'CONSISTENT'
        assert result.observed_control_head != e.completion.record.observed_control_head
        assert snapshot(e) == before


def test_saved_recording_time_cannot_precede_its_real_observed_prefix():
    with F.fixture(completed=True) as e:
        at = e.clock()+timedelta(seconds=1)
        with e.journal.transaction() as tx:
            tx.append('halt', {'floor':str(e.package['owner_after'].signed_floor_krw)}, now=at)
            tail = tx.events[-1]['row_sha256']
        e.clock_cell[0] = at
        forged = publish_claim(e, replace(e.completion.record, observed_control_head=tail))
        before = snapshot(e)
        refused(lambda: startup(e).inspect(e.input.archive_digest, forged), 'STARTUP_BINDING_CHANGED')
        assert snapshot(e) == before


def test_saved_recording_time_cannot_be_a_future_current_observation():
    with F.fixture(completed=True) as e:
        forged = publish_claim(e, replace(e.completion.record, recorded_at=e.clock()+timedelta(seconds=1)))
        before = snapshot(e)
        refused(lambda: startup(e).inspect(e.input.archive_digest, forged), 'STARTUP_BINDING_CHANGED')
        assert snapshot(e) == before


def test_clock_rollback_and_invalid_clock_do_not_mutate_archived_or_control_state():
    with F.fixture(completed=True) as e:
        app = startup(e)
        app.inspect(e.input.archive_digest, e.completion.archive_digest)
        before = snapshot(e)
        e.clock_cell[0] -= timedelta(microseconds=1)
        refused(lambda: app.inspect(e.input.archive_digest, e.completion.archive_digest), 'STARTUP_CLOCK_ROLLBACK')
        e.clock_cell[0] = None
        refused(lambda: app.inspect(e.input.archive_digest, e.completion.archive_digest), 'STARTUP_CLOCK_INVALID')
        assert snapshot(e) == before


def test_mutated_runtime_tuple_and_new_result_binding_are_not_accepted_as_same_startup():
    with F.fixture(completed=True) as e:
        app = startup(e)
        result = app.reconcile(e.input.archive_digest, e.completion.archive_digest)
        assert result.status == 'RECONCILED'
        before = snapshot(e)
        app.provider = F.provider(e)
        refused(lambda: app.reconcile(e.input.archive_digest, e.completion.archive_digest),
                'STARTUP_DEPENDENCY_CHANGED')
        assert snapshot(e) == before


def test_exact_missing_control_history_is_not_initialized_by_inspection():
    with F.fixture(completed=True) as e:
        app = startup(e)
        for name in ('control.lock', 'journal.jsonl', 'checkpoint.json'):
            (e.journal._root/name).unlink()
        before = snapshot(e)
        refused(lambda: app.inspect(e.input.archive_digest, e.completion.archive_digest),
                'STARTUP_DURABLE_REFUSED')
        assert snapshot(e) == before


def test_removal_between_snapshot_and_actual_transaction_cannot_bootstrap_new_history():
    with F.fixture(completed=True) as e:
        app = startup(e)
        original = Journal.snapshot
        removed = []
        def read_then_remove(journal):
            result = original(journal)
            if journal is e.journal and not removed:
                for name in ('control.lock', 'journal.jsonl', 'checkpoint.json'):
                    (journal._root/name).unlink()
                removed.append(snapshot(e))
            return result
        with patch.object(Journal, 'snapshot', read_then_remove):
            refused(lambda: app.inspect(e.input.archive_digest, e.completion.archive_digest),
                    'STARTUP_DURABLE_REFUSED')
        assert len(removed) == 1 and snapshot(e) == removed[0]


def test_changed_actual_store_head_during_inspection_refuses_without_adoption():
    with F.fixture(completed=True) as e:
        app = startup(e)
        original = S.CommittedAccountProvider.read
        changed = []
        def read_then_change(provider, **kwargs):
            result = original(provider, **kwargs)
            if not changed:
                changed.append(True)
                # Corrupt actual retained anchor bytes; no success verifier is substituted.
                target = e.baseline_head._dir/'head.json'
                target.write_bytes(b'{}')
            return result
        with patch.object(S.CommittedAccountProvider, 'read', read_then_change):
            refused(lambda: app.inspect(e.input.archive_digest, e.completion.archive_digest))
        assert changed == [True]
