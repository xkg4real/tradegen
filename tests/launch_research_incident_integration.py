"""Actual archive/signature/family/history integration with durable incidents.

All roots and signing keys are disposable. Recorded invented prices exercise the
actual evaluator, never demonstrate live profitability or source authenticity.
No actual account, API, order or notification transport is used. Fault injections
damage real temporary bytes or delay actual readers; no positive verifier is
replaced and no caller-created result is promoted to authority.
"""
from contextlib import contextmanager
from datetime import timedelta
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import bundle_attestation as A, bundle_auth as U
from execution_launch import incident_aware_selection as I
from execution_launch import research_bundle as R, research_bundle_store as B
from execution_launch import research_incidents as F, research_incident_monitor as M
from execution_launch import research_incident_store as J, strategy as E
from tests import launch_sealed_study_review as SR
from tests import launch_research_bundle as RF, launch_research_bundle_store as BF
from tests.launch_bundle_auth import document
from tests.launch_study_review import signed
from tools.owner.research_bundle import provision_research_store
from tools.owner.research_incidents import provision_incident_store


@contextmanager
def fixture(*, count=500, carry=False):
    with SR.fixture(count=count, carry=carry) as e:
        roots = tuple(e.base / name for name in ('incidents', 'incident-backups', 'incident-heads'))
        for root in roots:
            root.mkdir()
        args = dict(root=roots[0], backup_root=roots[1], head_root=roots[2], head_name='research-incidents',
            limits=J.IncidentStoreLimits(format_limits=F.IncidentLimits(),
                max_journal_bytes=32*1024*1024, max_records=1024))
        incident_store = J.IncidentStore(**args)
        provision_incident_store(incident_store)
        yield SimpleNamespace(**vars(e), incident_store=incident_store, incident_args=args,
            reopen_incidents=lambda:J.IncidentStore(**args))


def register(e, *, store=None, digest=None):
    return M.register_target(e.incident_store, store or e.store, digest or e.digest, clock=e.clock)


def check(e, *, store=None, digest=None):
    return M.check_target(e.incident_store, store or e.store, digest or e.digest, clock=e.clock)


def select(e, **changes):
    args = dict(incident_store=e.incident_store, archive_attestation=e.archive,
        source_reviews=e.reviews, audit_logical_ids=e.audits, current_profile=e.profile,
        window=e.window, history_head_root=e.history_head_root, clock=e.clock,
        authority_provider=e.provider)
    return I.authenticate_incident_aware_selection(e.store, e.digest, **(args | changes))


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code is not None:
            assert str(exc) == code, (str(exc), code)
        return str(exc)
    raise AssertionError('incident dependency refusal missing')


def new_store(e, name):
    root = e.base / name
    root.mkdir()
    primary, backup = root / 'primary', root / 'backup'
    primary.mkdir(); backup.mkdir()
    store = B.BundleStore(roots=B.BundleRoots(sealed_root=primary, backup_root=backup),
        limits=e.store.limits, head_name='bundle-head')
    provision_research_store(store)
    return store


def exact_copy(e, name):
    """Actual complete copy before corruption; not a fake recovery receipt."""
    source = e.store.read_verified(e.digest, require_backup=True)
    raw = e.store.read_raw(source.manifest.input_archive_digest, require_backup=True)
    store = new_store(e, name)
    archived = store.archive_raw(raw.manifest_bytes, dict(raw.files))
    verified = store.commit_verified(source.manifest_bytes, dict(source.files))
    assert archived.backup_verified and verified.backup_verified and verified.bundle_digest == e.digest
    return SimpleNamespace(**(vars(e) | dict(store=store)))


def distinct_research(e, *, store, name):
    """New actual finalization and temporary signatures, with a distinct report.

    Other source/capture bytes deliberately remain shared: an unrelated physical
    store must not inherit poisoning solely because their code hashes coincide.
    """
    e.paths['report'][0].write_bytes(('Different display report for '+name+'.\n').encode('ascii'))
    result = R.finalize_study_bundle(e.inputs, store, run_id=name, raw_revision_id='raw-v1',
        verified_revision_id='verified-v1', attempt_id='attempt-a', evaluated_at=e.at)
    assert result.status == 'VERIFIED_UNAPPROVED', result.reasons
    saved = store.read_verified(result.bundle_digest, require_backup=True)
    raw = store.read_raw(result.input_archive_digest, require_backup=True)
    prepared = R.evaluate_sealed_study(store, result.bundle_digest)
    assert len(prepared.family.rows) == len(e.research.family.rows)
    request = A.request_from_manifests(raw.manifest_bytes, saved.manifest_bytes,
        requested_at=e.cell[0], expires_at=e.cell[0]+timedelta(hours=1), deployment_code_hash=e.code)
    archive = document(request, e.key, issued_at=e.cell[0])
    report = next(item for item in saved.manifest.files if item.role == 'report')
    audit_sha = hashlib.sha256(saved.files[report.logical_id]).hexdigest()
    bodies = {identifier:dict(body, audit_sha256=audit_sha) for identifier,body in e.bodies.items()}
    reviews = {identifier:signed(body,e.key).encode('ascii') for identifier,body in bodies.items()}
    return SimpleNamespace(**(vars(e) | dict(store=store, digest=result.bundle_digest,
        archive=archive, stored=saved, report=report, research=prepared, bodies=bodies,
        reviews=reviews, audits={identifier:report.logical_id for identifier in reviews})))


def damage_payload(e, logical_id, *, backup=False):
    target = BF.chunk_path(e.store, e.stored.files[logical_id], backup=backup)
    original = target.read_bytes()
    target.write_bytes(bytes([original[0] ^ 1])+original[1:])
    assert target.read_bytes() != original and target.stat().st_size == len(original)
    return target, original


def test_actual_fixed_and_carry_select_registered_graph_once_without_operation_permission():
    for carry in (False, True):
        with fixture(carry=carry) as e:
            registration = register(e)
            assert registration.bundle_digest == e.digest
            healthy = check(e)
            assert healthy.registered and healthy.graph_checked and not healthy.held
            actual, seen = E.evaluate_capture_json, []
            def evaluate(protocol, *args, **kwargs):
                seen.append(protocol.study_id)
                return actual(protocol, *args, **kwargs)
            with patch.object(E, 'evaluate_capture_json', side_effect=evaluate):
                result = select(e)
            assert len(seen) == len(set(seen)) == 3
            assert result.selection_assessment.research_selection_ready
            assert result.selection_assessment.selected_implementation_authenticated
            assert not result.execution_ready and not result.current_operational_use
            assert not result.automatic_recovery_supported
            snapshot = e.incident_store.inspect()
            assert not snapshot.state.incidents and not snapshot.state.outbox
            assert result.incident_head == snapshot.head and result.incident_sequence == snapshot.sequence


def test_actual_report_damage_is_durable_scoped_and_copy_or_delivery_cannot_clear_it():
    with fixture() as e:
        copy = exact_copy(e, 'healthy-copy')
        unrelated = distinct_research(e, store=new_store(e, 'independent-b'), name='independent-b')
        register(e); register(unrelated)
        target, original = damage_payload(e, e.report.logical_id)
        failure = check(e)
        assert failure.held and not failure.graph_checked
        snapshot = e.incident_store.inspect()
        assert len(snapshot.state.incidents) == len(snapshot.state.outbox) == 1
        incident = snapshot.state.incidents[0]
        assert incident.category == 'INTEGRITY_FAILURE' and incident.scope == 'OBJECTS'
        assert e.digest in incident.affected_bundle_digests
        assert unrelated.digest not in incident.affected_bundle_digests
        assert select(unrelated).selection_assessment.research_selection_ready
        assert target.read_bytes() != original, 'monitor silently repaired damaged bytes'
        with patch.object(R, '_evaluate_sealed_study_snapshot', side_effect=AssertionError('held before issuance')):
            refused(lambda:select(e), 'INCIDENT_SELECTION_QUARANTINED')
        e.incident_store = e.reopen_incidents()
        assert check(e).held
        target.write_bytes(original)  # explicit test-only physical repair cannot release the durable incident
        assert e.store.read_verified(e.digest, require_backup=True).backup_verified
        assert check(e).held
        copy.incident_store = e.incident_store
        register(copy)
        assert copy.store.read_verified(copy.digest, require_backup=True).backup_verified and check(copy).held
        refused(lambda:select(copy), 'INCIDENT_SELECTION_QUARANTINED')
        message = e.incident_store.inspect().state.outbox[0]
        for attempt, outcome in (('attempt-one','unknown'), ('attempt-two','failed'), ('attempt-three','delivered')):
            state = e.incident_store.inspect()
            event = F.make_event('DELIVERY', dict(message_id=message.message_id, attempt_id=attempt,
                outcome=outcome), observed_at=e.cell[0])
            committed = e.incident_store.commit(event, expected_head=state.head)
            retried = e.incident_store.commit(event, expected_head=committed.head)
            assert retried.head == committed.head
        assert not e.incident_store.inspect().state.pending_notifications
        assert check(e).held and check(copy).held


def test_actual_shared_source_object_holds_same_store_dependents_only():
    with fixture() as e:
        shared = distinct_research(e, store=e.store, name='same-store-b')
        unrelated = distinct_research(e, store=new_store(e, 'independent-b'), name='independent-b')
        register(e); register(shared); register(unrelated)
        program = next(item for item in e.stored.manifest.files if item.role == 'program_source')
        damage_payload(e, program.logical_id, backup=True)
        assert check(e).held and check(shared).held
        state = e.incident_store.inspect().state
        incident = state.incidents[0]
        assert incident.scope == 'OBJECTS' and incident.category == 'INTEGRITY_FAILURE'
        assert {e.digest,shared.digest} <= set(incident.affected_bundle_digests)
        assert len(incident.affected_raw_digests) == 2
        assert unrelated.digest not in incident.affected_bundle_digests
        assert check(unrelated).graph_checked and select(unrelated).selection_assessment.research_selection_ready


def test_later_same_store_dependent_and_its_exact_new_copy_inherit_existing_incident():
    with fixture(count=60) as e:
        register(e)
        program = next(item for item in e.stored.manifest.files if item.role == 'program_source')
        target, original = damage_payload(e, program.logical_id, backup=True)
        assert check(e).held
        incident_id = e.incident_store.inspect().state.incidents[0].incident_id
        target.write_bytes(original)  # physical repair does not clear the journal's restrictive scope
        later = distinct_research(e, store=e.store, name='later-dependent-c')
        register(later)
        assert check(later).held
        copied = exact_copy(later, 'later-copy')
        register(copied)
        copied.incident_store = e.reopen_incidents()
        result = check(copied)
        assert result.held and incident_id in result.incident_ids
        with patch.object(R, '_evaluate_sealed_study_snapshot', side_effect=AssertionError('copy must remain held')):
            refused(lambda:select(copied), 'INCIDENT_SELECTION_QUARANTINED')
        state = copied.incident_store.inspect().state
        assert len(state.incidents) == len(state.outbox) == 1


def test_actual_catalog_head_and_root_failures_hold_registered_store_scope():
    for mode in ('catalog', 'head', 'root'):
        with fixture(count=60) as e:
            shared = distinct_research(e, store=e.store, name='same-store-b')
            unrelated = distinct_research(e, store=new_store(e, 'independent-b'), name='independent-b')
            register(e); register(shared); register(unrelated)
            if mode == 'catalog':
                target = e.store.roots.sealed_root/'catalog.jsonl'
                original = target.read_bytes()
                target.write_bytes(original.replace(b'"schema":', b'"schXma":', 1))
            elif mode == 'head':
                target = e.store.head._dir/'head.json'
                target.write_bytes(b'{broken head')
            else:
                original_root = e.store.roots.sealed_root
                original_root.rename(e.base/'displaced-primary')
                original_root.mkdir()
            assert check(e).held and check(shared).held
            incident = e.incident_store.inspect().state.incidents[0]
            assert incident.scope == 'STORE'
            assert {e.digest,shared.digest} <= set(incident.affected_bundle_digests)
            assert check(unrelated).graph_checked
            assert select(unrelated).selection_assessment.selection.status == 'NO_QUALIFIED_MARKET'


def test_missing_registration_and_broken_incident_head_refuse_before_evaluation():
    with fixture() as e:
        with patch.object(R, '_evaluate_sealed_study_snapshot', side_effect=AssertionError('unexpected issuance')):
            refused(lambda:select(e), 'INCIDENT_TARGET_UNREGISTERED')
            refused(lambda:select(e, incident_store=None))
        register(e)
        head = e.incident_store.head._dir/'head.json'
        head.write_bytes(b'{broken incident head')
        with patch.object(R, '_evaluate_sealed_study_snapshot', side_effect=AssertionError('unexpected issuance')):
            refused(lambda:select(e))
        assert head.read_bytes() == b'{broken incident head'


def test_final_actual_object_incident_prevents_result_after_real_family_evaluation():
    with fixture() as e:
        register(e)
        actual, calls = U._graph, []
        def graph(*args, **kwargs):
            result = actual(*args, **kwargs)
            calls.append(result)
            if len(calls) == 2:
                damage_payload(e, e.report.logical_id)
                assert check(e).held
            return result
        with patch.object(U, '_graph', side_effect=graph):
            refused(lambda:select(e), 'INCIDENT_SELECTION_QUARANTINED')
        assert len(calls) == 2 and len(e.incident_store.inspect().state.incidents) == 1


def test_real_graph_failure_inside_selection_is_persisted_without_manual_detector_call():
    with fixture() as e:
        register(e)
        actual, calls = E.evaluate_capture_json, []
        def evaluate(protocol, *args, **kwargs):
            result = actual(protocol, *args, **kwargs)
            calls.append(protocol.study_id)
            if len(calls) == 3:
                damage_payload(e, e.report.logical_id)
            return result
        with patch.object(E, 'evaluate_capture_json', side_effect=evaluate):
            refused(lambda:select(e))
        assert len(calls) == len(set(calls)) == 3
        state = e.incident_store.inspect().state
        assert len(state.incidents) == len(state.outbox) == 1
        assert state.incidents[0].category == 'INTEGRITY_FAILURE'
        assert check(e).held


def test_final_incident_head_damage_refuses_instead_of_returning_cached_initial_state():
    with fixture() as e:
        register(e)
        actual, calls = U._graph, []
        target = e.incident_store.head._dir/'head.json'
        def graph(*args, **kwargs):
            result = actual(*args, **kwargs)
            calls.append(result)
            if len(calls) == 2:
                target.write_bytes(b'{broken final incident head')
            return result
        with patch.object(U, '_graph', side_effect=graph):
            refused(lambda:select(e))
        assert len(calls) == 2 and target.read_bytes() == b'{broken final incident head'


def test_real_incident_appended_during_final_owner_crypto_refuses_completion():
    with fixture() as e:
        register(e)
        actual, calls = U._authority, []
        def authority(*args, **kwargs):
            result = actual(*args, **kwargs)
            calls.append(result)
            if len(calls) == 3:
                # First archive observation, selected factory observation, then
                # final actual owner/signature check. The full incident guard
                # has already returned clear before this real new observation.
                damage_payload(e, e.report.logical_id)
                assert check(e).held
            return result
        with patch.object(U, '_authority', side_effect=authority):
            refused(lambda:select(e), 'INCIDENT_FINAL_HEAD_CHANGED')
        # Completion checks latest AND the retained original owner observation;
        # their two real verifications follow the first/factory observations.
        assert len(calls) == 4
        state = e.incident_store.inspect().state
        assert len(state.incidents) == len(state.outbox) == 1
        assert state.incidents[0].category == 'INTEGRITY_FAILURE'


def test_actual_store_lock_unavailable_is_distinct_durable_hold_without_damage_claim():
    with fixture(count=60) as e:
        register(e)
        assert B._LOCK.acquire(blocking=False)
        try:
            result = check(e)
        finally:
            B._LOCK.release()
        assert result.held and not result.graph_checked
        incident = e.incident_store.inspect().state.incidents[0]
        assert incident.category == 'READ_UNAVAILABLE' and incident.reason_code == 'BUNDLE_STORE_LOCKED'
        assert e.store.read_verified(e.digest, require_backup=True).backup_verified
        assert check(e).held, 'v1 has no implicit release after transient recovery'


def test_actual_evaluation_registry_admission_failure_does_not_claim_graph_corruption():
    with fixture(count=60) as e:
        register(e)
        size = len(e.research.family.rows)
        while len(E._EVALUATED)+size <= 128:
            actual = R.evaluate_sealed_study(e.store, e.digest)
            assert len(actual.family.rows) == size
        assert len(E._EVALUATED)+size > 128
        refused(lambda:select(e), 'STUDY_EVIDENCE_RESOURCE_LIMIT')
        state = e.incident_store.inspect().state
        assert not state.incidents and not state.outbox
        assert check(e).graph_checked and not check(e).held


def test_no_qualified_and_normally_recorded_aborted_raw_are_not_integrity_incidents():
    with fixture(count=60) as e:
        register(e)
        result = select(e)
        assert result.selection_assessment.selection.status == 'NO_QUALIFIED_MARKET'
        assert not e.incident_store.inspect().state.incidents
        with RF.fixture(aborted=True) as raw:
            saved = RF.finalize(raw)
            assert saved.status == 'RAW_ARCHIVED'
            registration = M.register_target(e.incident_store, raw.store, saved.input_archive_digest, clock=e.clock)
            assert registration.bundle_kind == 'RAW_ARCHIVED'
            checked = M.check_target(e.incident_store, raw.store, saved.input_archive_digest, clock=e.clock)
            assert checked.graph_checked and not checked.held
            assert not e.incident_store.inspect().state.incidents


def test_final_incident_guard_duration_and_late_actual_owner_revocation_are_rechecked():
    for mode in ('delay', 'revocation'):
        with fixture() as e:
            register(e)
            actual, calls = M.check_target, []
            def checked(*args, **kwargs):
                result = actual(*args, **kwargs)
                calls.append(result)
                if len(calls) == 2:
                    if mode == 'delay':
                        e.cell[0] += timedelta(seconds=31)
                    else:
                        identifier = sorted(e.reviews)[-1]
                        SR.revoke(e, e.reviews[identifier], e.bodies[identifier]['purpose'])
                return result
            with patch.object(M, 'check_target', side_effect=checked):
                code = refused(lambda:select(e))
            assert len(calls) >= 2
            assert ('STALE' in code if mode == 'delay' else 'REVOKED' in code), code
            assert not e.incident_store.inspect().state.incidents
