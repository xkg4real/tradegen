"""Actual private selection/held-graph boundaries, with disposable signed homes.

Research prices and minimal graph inputs are synthetic. The recorder, evaluator,
signature checks, factory, history, stores and incident paths execute normally.
Hook spies exercise ordering and refusal, not a fabricated release authority;
the separate recovered consumer suite tests actual release persistence.
"""
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
import hashlib
from unittest.mock import patch

from execution_control.capability import digest
from execution_launch import sealed_study_review as S
from execution_launch import research_incident_monitor as M
from execution_launch import research_incident_store as J
from execution_launch import research_incidents as I
from execution_launch.live_history import LiveHistory
from tests import launch_research_incident_monitor as MF
from tests import launch_sealed_study_review as SF


def recovery_check(e, *, clock=None):
    return M._check_recovered_target(e.incident_store, e.store, e.digest, clock=clock or e.clock)


def held_repaired(e):
    registration = MF.register(e)
    path, original = MF.damage(e)
    checked = MF.check(e)
    assert checked.held and not checked.graph_checked
    path.write_bytes(original)
    return registration, checked


def private_select(e, **changes):
    args = dict(archive_attestation=e.archive, source_reviews=e.reviews, audit_logical_ids=e.audits,
        current_profile=e.profile, window=e.window, history_head_root=e.history_head_root,
        clock=e.clock, authority_provider=e.provider)
    return S._authenticate_sealed_study_selection(e.store, e.digest, **(args | changes))


def test_recovered_actual_held_graph_is_read_without_changing_general_hold_or_any_bytes():
    with MF.fixture(verified=True) as e:
        registration, held = held_repaired(e)
        before = MF.BF.files(e.base)
        with patch.object(M, '_complete_graph', side_effect=AssertionError('general held read')):
            general = MF.check(e)
        assert general.held and not general.graph_checked
        with patch.object(M, '_complete_graph', wraps=M._complete_graph) as actual:
            checked = recovery_check(e)
        assert actual.call_count == 1 and checked.held and checked.graph_checked
        assert checked.incident_ids == held.incident_ids and checked.checked_at == MF.NOW
        assert checked.store_binding_sha256 == registration.store_binding_sha256
        assert I.blocked_incidents(e.incident_store.inspect().state, registration)
        assert MF.check(e).held and not MF.check(e).graph_checked
        assert MF.BF.files(e.base) == before


def test_new_actual_backup_damage_is_recorded_even_when_registration_already_held():
    with MF.fixture(verified=True) as e:
        registration, first = held_repaired(e)
        path, original = MF.damage(e, backup=True)
        checked = recovery_check(e, clock=lambda: MF.NOW+timedelta(seconds=1))
        state = e.incident_store.inspect().state
        assert checked.held and not checked.graph_checked
        assert set(first.incident_ids) < set(checked.incident_ids)
        assert len(state.incidents) == 2 and state.incidents[-1].scope == 'OBJECTS'
        assert state.incidents[-1].failed_objects
        assert I.blocked_incidents(state, registration)
        path.write_bytes(original)
        repaired = recovery_check(e, clock=lambda: MF.NOW+timedelta(seconds=1))
        assert repaired.held and repaired.graph_checked and repaired.incident_ids == checked.incident_ids


def test_recovered_graph_record_failure_remains_latched_after_actual_repair_and_reopen():
    with MF.fixture() as e:
        held_repaired(e)
        path, original = MF.damage(e, backup=True)
        with patch.object(e.incident_store, 'commit',
                          side_effect=J.IncidentStoreError('INCIDENT_STORE_WRITE_REFUSED')):
            MF.refused(lambda: recovery_check(e, clock=lambda:MF.NOW+timedelta(seconds=1)),
                       'INCIDENT_RECORD_UNCONFIRMED')
        path.write_bytes(original)
        e.incident_store = e.reopen_incidents()
        assert e.store.read_raw(e.digest, require_backup=True).backup_verified
        with patch.object(M, '_complete_graph', side_effect=AssertionError('latched graph read')):
            MF.refused(lambda: recovery_check(e), 'INCIDENT_RECORD_UNCONFIRMED')
        assert len(e.incident_store.inspect().state.incidents) == 1


def test_unknown_clock_cannot_claim_healthy_recovered_graph_or_remove_hold():
    with MF.fixture() as e:
        _, first = held_repaired(e)
        before = MF.BF.files(e.base)
        MF.refused(lambda: recovery_check(e, clock=lambda:None), 'INCIDENT_CLOCK_INVALID')
        assert MF.check(e).incident_ids == first.incident_ids
        assert MF.BF.files(e.base) == before


def test_record_hook_uses_actual_detached_family_documents_and_runs_before_final_checks():
    with SF.fixture() as e:
        originals, audits = dict(e.reviews), dict(e.audits)
        events, bases, compositions, evaluations, authorities = [], [], [], {}, []
        actual_eval, actual_compose = SF.E.evaluate_capture_json, SF.C._compose_driver
        actual_impl, actual_graph, actual_history = S._implementation, S.U._graph, LiveHistory._replay
        actual_authority = type(e.provider).__call__
        def evaluate(protocol, *args, **kwargs):
            result = actual_eval(protocol, *args, **kwargs)
            assert protocol.study_id not in evaluations
            evaluations[protocol.study_id] = result
            return result
        def compose(**kwargs):
            result = actual_compose(**kwargs); compositions.append(result); return result
        def implementation(*args, **kwargs):
            result = actual_impl(*args, **kwargs); events.append('implementation'); return result
        def graph(*args, **kwargs):
            result = actual_graph(*args, **kwargs); events.append('graph'); return result
        def history(self, *args, **kwargs):
            result = actual_history(self, *args, **kwargs); events.append('history'); return result
        def authority(self, now):
            result = actual_authority(self, now); authorities.append(result); return result
        def record(basis):
            assert events.count('graph') == 2 and events[-1] == 'history'
            assert events.count('implementation') == 1
            bases.append(basis); events.append('record')
            # The already checked snapshot must survive later caller mutation.
            e.reviews.clear(); e.audits.clear()
        def final(): events.append('final_dependency')
        def completion(): events.append('completion'); return e.cell[0]
        with patch.object(SF.E, 'evaluate_capture_json', evaluate), \
             patch.object(SF.C, '_compose_driver', compose), patch.object(S, '_implementation', implementation), \
             patch.object(S.U, '_graph', graph), patch.object(LiveHistory, '_replay', history), \
             patch.object(type(e.provider), '__call__', authority):
            result = private_select(e, selection_record_guard=record, final_dependency_guard=final,
                                    completion_dependency_guard=completion)
        assert result.research_selection_ready and not result.execution_ready
        assert len(evaluations) == len(e.research.family.rows) == 3 and len(bases) == len(compositions) == 1
        basis, identity = bases[0], compositions[0].identity
        assert type(basis) is S._SelectionRecordBasis
        assert basis.first_authority is authorities[0]
        assert any(basis.selected_authority is value for value in authorities)
        assert basis.bundle_digest == e.digest and basis.input_archive_digest == e.stored.manifest.input_archive_digest
        assert basis.attestation_sha256 == S.A.attestation_document_digest(e.archive)
        assert basis.revocation_target_sha256 == S.revocation_target(e.archive, purpose=S.A.PURPOSE)
        assert basis.family_sha256 == e.bodies[basis.selected_study_id]['request']['family_commitment']['family_sha256']
        assert basis.evidence_sha256 == SF.E.evidence_digest(evaluations[basis.selected_study_id])
        assert basis.program_sha256 == identity.program_digest and basis.protocol_sha256 == identity.protocol_digest
        assert basis.profile_contract_sha256 == identity.profile_contract_digest
        assert basis.rule_terms_sha256 == identity.rule_terms_digest
        assert basis.window_sha256 == identity.deployment_window_digest and basis.driver_identity_sha256 == digest(identity)
        assert tuple(row.study_id for row in basis.source_reviews) == result.authenticated_study_ids == tuple(sorted(originals))
        for row in basis.source_reviews:
            body = e.bodies[row.study_id]
            assert type(row) is S._SourceReviewRecordBasis
            assert row.document_sha256 == hashlib.sha256(originals[row.study_id]).hexdigest()
            assert row.purpose == body['purpose'] and row.audit_logical_id == audits[row.study_id]
            assert row.audit_sha256 == body['audit_sha256']
            assert row.revocation_target_sha256 == S.revocation_target(originals[row.study_id], purpose=row.purpose)
        assert basis.evaluated_at == e.at and basis.started_at == basis.first_authority.observed_at
        assert basis.observed_at == basis.selected_authority.observed_at
        assert basis.approval_expires_at == min(datetime.fromisoformat(body['expires_at']) for body in e.bodies.values())
        assert events.index('record') < events.index('final_dependency') < events.index('completion')
        assert events[events.index('final_dependency')+1] == 'history'
        assert events.count('implementation') == 2
        try:
            basis.family_sha256 = '0'*64
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError('record basis was mutable')


def test_no_selection_skips_record_hook_but_keeps_final_dependencies_and_actual_archive_checks():
    with SF.fixture(count=60, provision=False) as e:
        calls = []
        with patch.object(SF.C, '_compose_driver', side_effect=AssertionError('NO_SELECTION factory')):
            result = private_select(e,
                selection_record_guard=lambda _: (_ for _ in ()).throw(AssertionError('NO_SELECTION release')),
                final_dependency_guard=lambda:calls.append('final'),
                completion_dependency_guard=lambda:calls.append('completion'))
        assert result.selection.status == 'NO_QUALIFIED_MARKET' and not result.research_selection_ready
        assert result.archive_identity_authenticated and calls == ['final', 'completion']
        assert not list(e.history_head_root.iterdir())


def test_private_record_failure_cannot_return_a_precomputed_selected_result():
    with SF.fixture() as e:
        called = []
        def record(_basis):
            called.append('record')
            raise ValueError('RECOVERED_SELECTION_RECORD_UNCONFIRMED')
        SF.refused(lambda: private_select(e, selection_record_guard=record,
            final_dependency_guard=lambda:called.append('final')), 'RECOVERED_SELECTION_RECORD_UNCONFIRMED')
        assert called == ['record']


def test_actual_history_changed_by_record_or_final_dependency_refuses_after_recording():
    for phase in ('record', 'final'):
        with SF.fixture() as e:
            head = e.history_head_root/SF.C.history_head_name(e.window)/'head.json'
            original_head = head.read_bytes()
            called = []
            def damage():
                if phase == 'record':
                    journals = [p for p in e.home.rglob('*.jsonl') if 'history' in str(p)]
                    assert len(journals) == 1
                    raw = journals[0].read_bytes()
                    changed = raw.replace(b'"', b"'", 1)
                    assert changed != raw and len(changed) == len(raw)
                    journals[0].write_bytes(changed)
                else:
                    assert head.read_bytes() != original_head
                    head.write_bytes(original_head)
            def record(_basis):
                called.append('record')
                if phase == 'record': damage()
            def final():
                called.append('final')
                if phase == 'final': damage()
            SF.refused(lambda: private_select(e, selection_record_guard=record, final_dependency_guard=final))
            assert called == ['record', 'final']


def test_private_completion_watermark_requires_aware_time_and_precedes_final_clock():
    # Synthetic lower-bound values test the private callback contract, not an
    # issued checkpoint. All archive/current-owner checks are still actual.
    for kind in ('future', 'naive', 'boolean'):
        with SF.fixture(count=60, provision=False) as e:
            value = (e.cell[0]+timedelta(microseconds=1) if kind == 'future' else
                     e.cell[0].replace(tzinfo=None) if kind == 'naive' else True)
            code = 'SEALED_SELECTION_CLOCK_ROLLBACK' if kind == 'future' else 'SEALED_SELECTION_TIME_INVALID'
            SF.refused(lambda: private_select(e, completion_dependency_guard=lambda:value), code)


def test_legacy_public_selection_checks_the_actual_checkpoint_completion_watermark():
    """Shared final-clock hardening also applies without any recovery callback."""
    with SF.fixture() as e:
        actual, calls, completed = S.verify_implementation_review, [], []
        def verify(*args, **kwargs):
            result = actual(*args, **kwargs)
            calls.append(1)
            if len(calls) == 2:
                authority = kwargs['authority']
                requested = e.cell[0]
                e.cell[0] = requested + timedelta(seconds=1)
                # Real current key/code/log prefix observation completes later
                # than the caller's final clock, without a fabricated authority.
                e.provider.observe_checkpoint(requested,
                    key_fingerprint=authority.context.owner.fingerprint,
                    code_hash=authority.context.code_hash, owner_head=authority.context.owner.head)
                completed.append(e.provider._last)
                e.cell[0] = requested
            return result
        with patch.object(S, 'verify_implementation_review', verify):
            SF.refused(lambda:SF.select(e), 'SEALED_SELECTION_CLOCK_ROLLBACK')
        assert len(calls) == 2 and completed == [e.cell[0]+timedelta(seconds=1)]


def test_recovered_final_actual_owner_completion_cannot_be_hidden_by_a_later_clock_rollback():
    for count in (60, 500):
        with SF.fixture(count=count, provision=count == 500) as e:
            initial, armed, completed = e.cell[0], [], []
            actual_load = SF.owner.load_context
            actual_checkpoint = type(e.provider).observe_checkpoint
            def load(*args, **kwargs):
                context = actual_load(*args, **kwargs)
                if armed:
                    e.cell[0] = initial + timedelta(seconds=5)
                return context
            def checkpoint(provider, now, **kwargs):
                authority = actual_checkpoint(provider, now, **kwargs)
                completed.append(provider._last)
                e.cell[0] = initial + timedelta(seconds=1)
                return authority
            with patch.object(SF.owner, 'load_context', load), \
                 patch.object(type(e.provider), 'observe_checkpoint', checkpoint):
                SF.refused(lambda:private_select(e, selection_record_guard=lambda _:None,
                    final_dependency_guard=lambda:armed.append(True)), 'SEALED_SELECTION_CLOCK_ROLLBACK')
            assert completed == [initial+timedelta(seconds=5)]
            assert e.cell[0] == initial+timedelta(seconds=1)


def test_public_sealed_api_does_not_accept_any_release_callback_or_cached_basis():
    with SF.fixture(count=60, provision=False) as e:
        called = []
        try:
            SF.select(e, selection_record_guard=lambda basis:called.append(basis))
        except TypeError:
            pass
        else:
            raise AssertionError('public API accepted private release callback')
        assert not called and not list(e.history_head_root.iterdir())
