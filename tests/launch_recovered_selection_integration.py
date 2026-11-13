"""Actual restored research, original signatures and current selection checks.

All observations, keys and roots are disposable. Recorded invented prices pass
through the real recorder, complete-family evaluator, registered factory, owner
signatures, recovery controller and backed journals. They prove integration,
not market provenance or profitability. Fault spies invoke the real operation
before changing temporary bytes/time or appending a genuinely signed revocation.
No positive authority/result is fabricated; no API, order or notification runs.
"""
from datetime import timedelta
from unittest.mock import patch

from core.compliance import owner
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation as A, bundle_recovery as B
from execution_launch import incident_aware_selection as I
from execution_launch import research_bundle as R, research_incident_monitor as M
from execution_launch import research_incidents as F, research_recovery as RC
from execution_launch import sealed_study_review as S, strategy as E
from tests import launch_recovered_selection as V
from tests import launch_research_bundle_store as BF
from tests import launch_research_recovery_integration as RR
from tests import launch_sealed_study_review as SR
from tests.launch_study_review import signed


def releases(e):
    return F.research_route_releases(e.incident_store.inspect().state,
        route_id=e.route.route_id, incident_id=e.incident_id,
        limits=e.incident_store.limits.format_limits)


def no_operation(result):
    assert result.scope == 'recovered_research_selection'
    assert result.current_operational_use is False and result.execution_ready is False
    assert result.automatic_operational_recovery_supported is False
    nested = result.selection_assessment
    assert nested.current_operational_use is False and nested.execution_ready is False
    assert nested.automatic_recovery_supported is False


def held(e):
    checked = M.check_target(e.incident_store, e.destination, e.digest, clock=e.clock)
    assert checked.held and e.incident_id in checked.incident_ids
    return checked


def ordinary_selection(e):
    return I.authenticate_incident_aware_selection(e.destination, e.digest,
        incident_store=e.incident_store, archive_attestation=e.archive,
        source_reviews=e.reviews, audit_logical_ids=e.audits,
        current_profile=e.profile, window=e.window, history_head_root=e.history_head_root,
        clock=e.clock, authority_provider=e.provider)


def artifact_path(e, *, backup=False):
    artifact = e.destination.read_raw(e.recovery.recovery_artifact_digest, require_backup=True)
    assert artifact.files['attestation'] == e.archive
    return BF.chunk_path(e.destination, artifact.files['attestation'], backup=backup)


def observed_evaluation(calls):
    actual = E.evaluate_capture_json
    def evaluate(protocol, *args, **kwargs):
        result = actual(protocol, *args, **kwargs)
        assert E._EVALUATED.get(id(result)) == (result, E.evidence_digest(result))
        calls.append(protocol.study_id)
        return result
    return evaluate


def after_release(e, effect):
    actual = e.incident_store.commit
    def commit(event, **kwargs):
        snapshot = actual(event, **kwargs)
        if event.kind == 'RESEARCH_ROUTE_RELEASE':
            effect(event, snapshot)
        return snapshot
    return commit


def test_actual_fixed_and_carry_source_gone_select_once_with_original_evidence_and_general_hold():
    for carry in (False, True):
        with V.fixture(carry=carry, source_removed=True) as e:
            assert not e.store.roots.sealed_root.exists() and not e.store.roots.backup_root.exists()
            original = e.archive, dict(e.reviews), RR.archive_bytes(e.destination)
            owner_before = owner.log_path().read_bytes()
            attempts_before = e.attempts.inspect()
            notices = e.incident_store.inspect().state.outbox
            calls = []
            with (patch.object(E, 'evaluate_capture_json', side_effect=observed_evaluation(calls)),
                  patch.object(e.store, 'read_raw', side_effect=AssertionError('lost source reopened')),
                  patch.object(e.store, 'read_verified', side_effect=AssertionError('lost source reopened')),
                  patch.object(B, 'restore_signed_backup', side_effect=AssertionError('second restoration')),
                  patch.object(RC, 'run_recovery_once', side_effect=AssertionError('recovery reissued'))):
                result = V.select(e)
            no_operation(result)
            nested = result.selection_assessment
            assert result.research_selection_ready and nested.research_selection_ready
            assert nested.selection.status == 'SELECTED' and nested.selected_implementation_authenticated
            assert len(calls) == len(set(calls)) == len(e.research.family.rows) == 3
            assert len(nested.selection.rows) == 3 and len(e.reviews) == 2
            record, = releases(e)
            assert result.release_record_id == record.event_id
            assert record.payload['binding']['selection']['selected_study_id'] == nested.selection.selected_study_id
            assert len(record.payload['binding']['selection']['source_reviews']) == len(e.reviews)
            assert result.recovery_artifact_digest == e.recovery.recovery_artifact_digest
            assert result.attempt_id == e.recovery.attempt_id and result.outcome_event_id == e.recovery.outcome_event_id
            assert (e.archive, dict(e.reviews), RR.archive_bytes(e.destination)) == original
            assert owner.log_path().read_bytes() == owner_before and e.attempts.inspect() == attempts_before
            assert e.incident_store.inspect().state.outbox == notices
            held(e)
            with patch.object(R, '_evaluate_sealed_study_snapshot', side_effect=AssertionError('ordinary held issuance')):
                V.refused(lambda:ordinary_selection(e), 'INCIDENT_SELECTION_QUARANTINED')


def test_actual_numerical_no_selection_retains_all_candidates_without_release_or_new_incident():
    with V.fixture(count=60, source_removed=True) as e:
        assert not e.reviews
        original = e.destination.read_verified(e.digest, require_backup=True)
        before = e.incident_store.inspect().state
        calls = []
        with patch.object(E, 'evaluate_capture_json', side_effect=observed_evaluation(calls)):
            result = V.select(e)
        no_operation(result)
        assert result.selection_assessment.selection.status == 'NO_QUALIFIED_MARKET'
        assert result.release_record_id is None and result.research_selection_ready is False
        assert not releases(e) and len(calls) == len(set(calls)) == 3
        after = e.incident_store.inspect().state
        assert after.incidents == before.incidents and after.outbox == before.outbox
        saved = e.destination.read_verified(e.digest, require_backup=True)
        assert saved.manifest_bytes == original.manifest_bytes and dict(saved.files) == dict(original.files)
        assert len(saved.manifest.candidates) == 3
        held(e)


def test_late_actual_signature_artifact_damage_is_recorded_and_physical_repair_does_not_clear_hold():
    for backup in (False, True):
        with V.fixture(source_removed=True) as e:
            path = artifact_path(e, backup=backup)
            original = path.read_bytes()
            damaged = bytes([original[0] ^ 1])+original[1:]
            seen = []
            def damage(event, snapshot):
                seen.append(event.event_id)
                path.write_bytes(damaged)
            with patch.object(e.incident_store, 'commit', side_effect=after_release(e, damage)):
                V.refused(lambda:V.select(e), 'RECOVERED_SELECTION_DEPENDENCY_CHANGED')
            assert seen == [releases(e)[0].event_id] and path.read_bytes() == damaged
            state = e.incident_store.inspect().state
            assert len(state.incidents) == len(state.outbox) == 2
            original_incident = next(item for item in state.incidents if item.incident_id == e.incident_id)
            artifact_incident = next(item for item in state.incidents if item.incident_id != e.incident_id)
            assert original_incident.scope == 'STORE' and original_incident.category == 'INTEGRITY_FAILURE'
            assert original_incident.failed_objects == ()
            # The separate artifact is not in the target's registered object
            # inventory. Preserve the actual reader's ambiguous fixed diagnosis;
            # do not invent a localized object hash or promote it to proof.
            assert artifact_incident.scope == 'TARGET' and artifact_incident.category == 'READ_UNAVAILABLE'
            assert artifact_incident.reason_code == 'BUNDLE_STORE_OBJECT_REFUSED'
            assert artifact_incident.failed_objects == ()
            path.write_bytes(original)  # Test-only repair is not an incident release.
            with patch.object(R, '_evaluate_sealed_study_snapshot', side_effect=AssertionError('additional incident issuance')):
                V.refused(lambda:V.select(e), 'RECOVERED_SELECTION_ADDITIONAL_INCIDENT')
            assert len(releases(e)) == 1 and held(e).held


def test_actual_archive_or_nonselected_source_revocation_after_record_refuses_and_keeps_evidence():
    for archive in (True, False):
        with V.fixture(source_removed=True) as e:
            identifier = next(identifier for identifier, body in e.bodies.items()
                              if body['request']['strategy_id'] == 'fixture-ma-1-2-b')
            raw = e.archive if archive else e.reviews[identifier]
            purpose = A.PURPOSE if archive else e.bodies[identifier]['purpose']
            before = RR.archive_bytes(e.destination)
            seen = []
            def revoke(event, snapshot):
                seen.append(event.event_id)
                SR.revoke(e, raw, purpose)
            with patch.object(e.incident_store, 'commit', side_effect=after_release(e, revoke)):
                code = V.refused(lambda:V.select(e))
            assert code in ('RECOVERED_SELECTION_ATTESTATION_REVOKED', 'SEALED_SELECTION_ARCHIVE_REVOKED',
                            'REVIEW_ATTESTATION_REVOKED'), code
            assert len(seen) == len(releases(e)) == 1
            assert RR.archive_bytes(e.destination) == before
            assert len(e.incident_store.inspect().state.incidents) == 1
            e.provider = CurrentOwnerAuthority(clock=e.clock)
            V.refused(lambda:V.select(e))
            assert len(releases(e)) == 1 and held(e).held


def test_final_crypto_delay_rejects_stale_result_then_fresh_call_rechecks_and_reuses_original_record():
    with V.fixture(source_removed=True) as e:
        actual = S.verify_implementation_review
        checked = []
        def slow(*args, **kwargs):
            result = actual(*args, **kwargs)
            checked.append(1)
            if len(checked) == 2:
                assert len(releases(e)) == 1
                e.cell[0] += timedelta(seconds=31)
            return result
        with patch.object(S, 'verify_implementation_review', side_effect=slow):
            V.refused(lambda:V.select(e), 'SEALED_SELECTION_OWNER_AUTHORITY_STALE')
        assert len(checked) == 2
        original, = releases(e)
        original_bytes = F.event_bytes(original)
        snapshot = e.incident_store.inspect()
        e.provider = CurrentOwnerAuthority(clock=e.clock)
        calls = []
        with patch.object(E, 'evaluate_capture_json', side_effect=observed_evaluation(calls)):
            result = V.select(e)
        no_operation(result)
        assert result.research_selection_ready and result.release_record_id == original.event_id
        assert len(calls) == len(set(calls)) == 3
        assert e.incident_store.inspect() == snapshot and F.event_bytes(releases(e)[0]) == original_bytes
        assert result.selection_assessment.verified_at == e.cell[0]
        held(e)


def test_actual_short_source_approval_expires_during_final_crypto_after_release_commit():
    with V.fixture(source_removed=True) as e:
        expires = e.cell[0]+timedelta(seconds=5)
        # Genuine disposable signatures are prepared before the selection call.
        e.reviews = {identifier:signed(dict(body, expires_at=expires.isoformat(timespec='microseconds')),
            e.key).encode('ascii') for identifier, body in e.bodies.items()}
        actual, checked = S.verify_implementation_review, []
        def slow(*args, **kwargs):
            result = actual(*args, **kwargs)
            checked.append(1)
            if len(checked) == 2:
                e.cell[0] += timedelta(seconds=6)
            return result
        with patch.object(S, 'verify_implementation_review', side_effect=slow):
            V.refused(lambda:V.select(e), 'SEALED_SELECTION_EXPIRED_OR_FUTURE')
        assert len(checked) == 2 and len(releases(e)) == 1
        assert len(e.incident_store.inspect().state.incidents) == 1
        held(e)


def test_actual_incident_append_after_final_crypto_cannot_return_a_prior_head():
    with V.fixture(source_removed=True) as e:
        actual, checked, appended = S.verify_implementation_review, [], []
        def append(*args, **kwargs):
            result = actual(*args, **kwargs)
            checked.append(1)
            if len(checked) == 2:
                state = e.incident_store.inspect()
                notice = state.state.outbox[0]
                event = F.make_event('DELIVERY', dict(message_id=notice.message_id,
                    attempt_id='during-final-crypto', outcome='unknown'), observed_at=e.cell[0])
                appended.append(e.incident_store.commit(event, expected_head=state.head))
            return result
        with patch.object(S, 'verify_implementation_review', side_effect=append):
            V.refused(lambda:V.select(e), 'RECOVERED_SELECTION_DEPENDENCY_CHANGED')
        assert len(checked) == 2 and len(appended) == len(releases(e)) == 1
        assert e.incident_store.inspect().head == appended[0].head
        assert len(e.incident_store.inspect().state.incidents) == 1
        held(e)


def test_final_actual_clock_rollback_after_record_does_not_return_research_readiness():
    with V.fixture(source_removed=True) as e:
        actual, checked = S.verify_implementation_review, []
        def rollback(*args, **kwargs):
            result = actual(*args, **kwargs)
            checked.append(1)
            if len(checked) == 2:
                e.cell[0] -= timedelta(microseconds=1)
            return result
        with patch.object(S, 'verify_implementation_review', side_effect=rollback):
            V.refused(lambda:V.select(e), 'SEALED_SELECTION_CLOCK_ROLLBACK')
        assert len(checked) == 2 and len(releases(e)) == 1
        assert len(e.incident_store.inspect().state.incidents) == 1


def test_prior_record_is_not_a_permit_after_late_refusal_and_actual_current_revocation():
    with V.fixture(source_removed=True) as e:
        actual, checked = S.verify_implementation_review, []
        def slow(*args, **kwargs):
            result = actual(*args, **kwargs)
            checked.append(1)
            if len(checked) == 2:
                e.cell[0] += timedelta(seconds=31)
            return result
        with patch.object(S, 'verify_implementation_review', side_effect=slow):
            V.refused(lambda:V.select(e), 'SEALED_SELECTION_OWNER_AUTHORITY_STALE')
        record, = releases(e)
        before = RR.archive_bytes(e.destination)
        SR.revoke(e, e.archive, A.PURPOSE)
        e.provider = CurrentOwnerAuthority(clock=e.clock)
        V.refused(lambda:V.select(e), 'SEALED_SELECTION_ARCHIVE_REVOKED')
        assert releases(e) == (record,) and RR.archive_bytes(e.destination) == before
        assert len(e.incident_store.inspect().state.incidents) == 1 and held(e).held
