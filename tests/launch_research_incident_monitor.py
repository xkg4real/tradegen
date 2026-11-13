"""Actual temporary backed graph/incident I/O; no account or notification calls.

Minimal graph fixtures contain invented malformed inputs and metadata, not an
issued research verdict. Full recorder/evaluator/owner integration lives in the
separate launch_research_incident_integration module.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import research_bundle_store as B
from execution_launch import research_incidents as F
from execution_launch import research_incident_monitor as M
from execution_launch import research_incident_store as J
from tests import launch_research_bundle_store as BF

NOW = datetime(2026, 11, 13, 10, tzinfo=timezone.utc)


@contextmanager
def fixture(*, verified=False, limits=None):
    with BF.fixture() as e:
        roots = tuple(e.base/name for name in ('incidents','incident-backups','incident-heads'))
        for root in roots:
            root.mkdir()
        args = dict(root=roots[0],backup_root=roots[1],head_root=roots[2],head_name='incidents',
                    limits=limits or J.IncidentStoreLimits(format_limits=F.DEFAULT_LIMITS))
        incident_store = J.IncidentStore(**args)
        incident_store.provision_empty()
        incident_store.head.initialize_reviewed_head(incident_store.genesis_digest)
        manifest, raw, payloads = BF.raw_archive(e.store, full=verified)
        receipt = e.store.archive_raw(raw,payloads)
        if verified:
            _, raw, payloads = BF.verified_bundle(e.store,manifest,payloads)
            receipt = e.store.commit_verified(raw,payloads)
        yield SimpleNamespace(**vars(e), incident_store=incident_store, incident_args=args,
            digest=receipt.bundle_digest, payloads=payloads, clock=lambda:NOW,
            reopen_incidents=lambda:J.IncidentStore(**args))


def register(e):
    return M.register_target(e.incident_store,e.store,e.digest,clock=e.clock)


def check(e, **kwargs):
    return M.check_target(e.incident_store,e.store,e.digest,clock=kwargs.get('clock',e.clock))


def refused(call, code=None):
    try:
        call()
    except ValueError as exc:
        if code:
            assert str(exc)==code,(str(exc),code)
        return str(exc)
    raise AssertionError('required refusal missing')


def damage(e, logical=None, *, backup=False):
    payload=e.payloads[logical or next(k for k,v in e.payloads.items() if v)]
    path=BF.chunk_path(e.store,payload,backup)
    original=path.read_bytes()
    path.write_bytes(bytes([original[0]^1])+original[1:])
    return path,original


def test_actual_malformed_and_empty_raw_inputs_register_without_promoting_success():
    with fixture() as e:
        before=BF.files(e.base)
        registration=register(e)
        assert registration.bundle_kind=='RAW_ARCHIVED'
        assert registration.input_archive_digest==e.digest and registration.verified_manifest_sha256 is None
        assert all(item.from_raw for item in registration.objects)
        assert len({item.sha256 for item in registration.objects})==len(registration.objects)
        assert not hasattr(registration,'research_selection_ready')
        result=check(e)
        assert result.graph_checked and not result.held and result.registered
        assert not e.incident_store.inspect().state.incidents
        after=BF.files(e.base)
        assert all(after[path]==raw for path,raw in before.items() if not path.startswith('incident'))


def test_registration_requires_actual_store_and_does_not_trust_constructed_graph_verdict():
    with fixture() as e:
        before=BF.files(e.base)
        refused(lambda:M.register_target(e.incident_store,SimpleNamespace(backup_verified=True),e.digest,
                    clock=e.clock),'INCIDENT_ACTUAL_STORE_REQUIRED')
        refused(lambda:M.check_target(e.incident_store,e.store,e.digest,clock=e.clock),'INCIDENT_TARGET_UNREGISTERED')
        assert BF.files(e.base)==before
        damage(e)
        refused(lambda:register(e))
        assert not e.incident_store.inspect().state.registrations


def test_actual_complete_verified_dependency_inventory_preserves_raw_and_derived_objects():
    with fixture(verified=True) as e:
        registration=register(e)
        assert registration.bundle_kind=='VERIFIED_UNAPPROVED' and registration.input_archive_digest!=e.digest
        assert any(item.from_raw for item in registration.objects)
        assert any(not item.from_raw for item in registration.objects)
        assert check(e).graph_checked
        path,original=damage(e,'evaluation',backup=True)
        result=check(e)
        assert result.held and not result.graph_checked
        incident=e.incident_store.inspect().state.incidents[0]
        assert incident.scope=='OBJECTS' and incident.category=='INTEGRITY_FAILURE'
        assert not incident.affected_raw_digests, 'derived-only damage cannot claim raw bytes failed'
        assert path.read_bytes()!=original


def test_registration_is_idempotent_across_benign_actual_catalog_growth():
    with fixture() as e:
        original=register(e)
        before=e.incident_store.inspect()
        _,raw,payloads=BF.raw_archive(e.store,{'other':b'new unrelated input'},run='different-run')
        e.store.archive_raw(raw,payloads)
        assert register(e)==original
        assert e.incident_store.inspect()==before
        assert check(e).graph_checked


def test_dependency_admission_refuses_without_truncating_or_partially_registering():
    limits=J.IncidentStoreLimits(format_limits=replace(F.DEFAULT_LIMITS,max_dependencies_per_target=1))
    with fixture(limits=limits) as e:
        before=BF.files(e.base)
        refused(lambda:register(e),'INCIDENT_RESOURCE_LIMIT')
        assert BF.files(e.base)==before and not e.incident_store.inspect().state.registrations


def test_record_capacity_full_refuses_healthy_result_and_reopen_cannot_clear_quota():
    limits=J.IncidentStoreLimits(format_limits=F.DEFAULT_LIMITS,max_records=1)
    with fixture(limits=limits) as e:
        register(e)
        before=BF.files(e.base)
        refused(lambda:check(e),'INCIDENT_STORE_LIMIT_EXCEEDED')
        e.incident_store=e.reopen_incidents()
        refused(lambda:check(e),'INCIDENT_STORE_LIMIT_EXCEEDED')
        assert BF.files(e.base)==before and e.store.read_raw(e.digest).backup_verified


def test_unconfirmed_failed_publication_stays_process_latched_after_graph_repair_and_reopen():
    with fixture() as e:
        register(e)
        path,original=damage(e)
        with patch.object(e.incident_store,'commit',side_effect=J.IncidentStoreError('INCIDENT_STORE_WRITE_REFUSED')):
            refused(lambda:check(e),'INCIDENT_RECORD_UNCONFIRMED')
        assert not e.incident_store.inspect().state.incidents
        path.write_bytes(original)
        assert e.store.read_raw(e.digest,require_backup=True).backup_verified
        e.incident_store=e.reopen_incidents()
        refused(lambda:check(e),'INCIDENT_RECORD_UNCONFIRMED')


def test_original_store_binding_survives_actual_root_replacement_and_records_store_hold():
    with fixture() as e:
        registration=register(e)
        original=e.roots.sealed_root
        original.rename(e.base/'displaced-primary')
        original.mkdir()
        result=check(e)
        assert result.held and result.store_binding_sha256==registration.store_binding_sha256
        state=e.incident_store.inspect().state
        assert len(state.incidents)==1 and state.incidents[0].scope=='STORE'
        assert e.digest in state.incidents[0].affected_bundle_digests
        assert list(original.iterdir())==[], 'monitor recreated the missing source store'


def test_unknown_or_rolled_back_clock_can_record_failure_but_cannot_claim_healthy_observation():
    with fixture() as e:
        register(e)
        refused(lambda:check(e,clock=lambda:None),'INCIDENT_CLOCK_INVALID')
        damage(e)
        result=check(e,clock=lambda:NOW-timedelta(days=1))
        assert result.held and result.checked_at is None
        snapshot=e.incident_store.inspect()
        assert snapshot.state.last_trusted_at==NOW and snapshot.state.incidents[0].observed_at is None


def test_actual_transient_lock_failure_is_reported_unavailable_and_not_silently_released():
    with fixture() as e:
        register(e)
        assert B._LOCK.acquire(blocking=False)
        try:
            result=check(e)
        finally:
            B._LOCK.release()
        assert result.held
        incident=e.incident_store.inspect().state.incidents[0]
        assert incident.category=='READ_UNAVAILABLE' and incident.reason_code=='BUNDLE_STORE_LOCKED'
        assert e.store.read_raw(e.digest).backup_verified
        assert check(e).held and not check(e).graph_checked


def test_incident_roots_cannot_be_nested_under_monitored_research_roots():
    with fixture() as e:
        root=e.roots.sealed_root/'independent-in-name-only'
        root.mkdir()
        separate=e.base/'elsewhere-incidents'
        separate.mkdir()
        head=e.base/'elsewhere-heads'
        head.mkdir()
        incidents=J.IncidentStore(root=root,backup_root=separate,head_root=head,
            head_name='incidents',limits=J.IncidentStoreLimits(format_limits=F.DEFAULT_LIMITS))
        refused(lambda:M.register_target(incidents,e.store,e.digest,clock=e.clock),
                'INCIDENT_RESEARCH_ROOT_OVERLAP')
        assert list(root.iterdir())==[]


def test_reregistering_existing_damaged_target_records_failure_before_any_later_repair():
    with fixture() as e:
        original=register(e)
        path,raw=damage(e)
        assert register(e)==original
        assert len(e.incident_store.inspect().state.incidents)==1
        path.write_bytes(raw)
        assert e.store.read_raw(e.digest).backup_verified
        assert check(e).held


def test_missing_exact_leaf_is_identified_without_blame_on_other_objects():
    with fixture(verified=True) as e:
        registration=register(e)
        path=BF.chunk_path(e.store,e.payloads['evaluation'])
        digest=path.stem
        path.unlink()
        assert check(e).held
        incident=e.incident_store.inspect().state.incidents[0]
        assert incident.scope=='OBJECTS' and incident.failed_objects==(digest,)
        assert incident.category=='INTEGRITY_FAILURE' and not incident.affected_raw_digests
        assert len(registration.objects)>1


def test_diagnostic_object_store_failure_does_not_lose_original_observation():
    with fixture() as e:
        register(e)
        original=e.store._objects
        def inaccessible(backup=False):
            raise M.E.EvidenceObjectError('EVIDENCE_OBJECT_PATH_REFUSED')
        with patch.object(e.store,'_objects',side_effect=inaccessible):
            assert check(e).held
        incident=e.incident_store.inspect().state.incidents[0]
        assert incident.scope=='TARGET' and not incident.failed_objects
        assert incident.category=='READ_UNAVAILABLE'
        assert e.store.read_raw(e.digest).backup_verified and check(e).held


def test_clock_io_failure_preserves_restrictive_observation_without_advancing_time():
    with fixture() as e:
        register(e)
        def broken_clock():
            raise OSError('simulated unavailable time source')
        refused(lambda:check(e,clock=broken_clock),'INCIDENT_CLOCK_INVALID')
        damage(e)
        assert check(e,clock=broken_clock).held
        state=e.incident_store.inspect().state
        assert state.last_trusted_at==NOW and state.incidents[0].observed_at is None


def test_ambiguous_path_refusal_is_unavailable_not_proof_of_integrity_damage():
    with fixture() as e:
        register(e)
        with patch.object(e.store,'_paths',side_effect=B.BundleStoreError('BUNDLE_STORE_PATH_REFUSED')):
            assert check(e).held
        incident=e.incident_store.inspect().state.incidents[0]
        assert incident.category=='READ_UNAVAILABLE' and incident.scope=='STORE'
        assert not incident.failed_objects


def test_missing_parent_during_leaf_diagnosis_does_not_blame_every_registered_leaf():
    with fixture() as e:
        registration=register(e)
        objects=e.store._objects()
        parent=objects._objects
        replacement=parent.with_name('displaced-objects')
        actual=M.E.EvidenceObjectStore._read_object
        calls=[]
        def missing_parent(value,*args):
            if value.root==objects.root and not calls:
                calls.append(True)
                parent.rename(replacement)
                raise FileNotFoundError('fixture parent disappeared')
            return actual(value,*args)
        try:
            with patch.object(M.E.EvidenceObjectStore,'_read_object',new=missing_parent):
                assert M._bad_objects(e.store,registration)==()
        finally:
            replacement.rename(parent)
        assert calls and not e.incident_store.inspect().state.incidents


def test_source_root_link_replacement_is_durable_unavailable_not_unrecorded_input_refusal():
    with fixture() as e:
        registration=register(e)
        original=e.roots.sealed_root
        displaced=e.base/'displaced-primary'
        original.rename(displaced)
        original.symlink_to(displaced,target_is_directory=True)
        try:
            result=check(e)
            assert result.held and result.store_binding_sha256==registration.store_binding_sha256
            incident=e.incident_store.inspect().state.incidents[0]
            assert incident.scope=='STORE' and incident.category=='READ_UNAVAILABLE'
            assert incident.reason_code=='BUNDLE_STORE_PATH_REFUSED'
        finally:
            original.unlink()
            displaced.rename(original)
        assert e.store.read_raw(e.digest,require_backup=True).backup_verified
        assert check(e).held, 'restoring the path cannot release the recorded incident'
