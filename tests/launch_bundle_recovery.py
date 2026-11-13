"""Real signed temporary archives and heads; no operational approval or real API.

The intentionally unissued verified fixture tests archival identity only. Every
successful result uses actual CurrentOwnerAuthority/Ed25519 and complete backup
graphs; fault injections preserve evidence and never initialize runtime trust.
"""
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import timedelta
import json
import os
import shutil
from types import SimpleNamespace
from unittest.mock import patch

from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_recovery as R, bundle_attestation as A, bundle_auth as U
from execution_launch import research_bundle_format as F, research_bundle_store as S
from execution_launch import evidence_objects as O, strategy as E
from execution_launch.baseline_head import BaselineHead
from execution_launch.recovery_artifact import build_recovery_artifact
from tests import launch_bundle_auth as AF, launch_research_bundle_store as SF


@contextmanager
def fixture(*, verified=False, storage_limits=None):
    with SF.fixture(storage_limits=storage_limits) as storage:
        raw, raw_bytes, payloads = SF.raw_archive(storage.store, full=verified)
        receipt = storage.store.archive_raw(raw_bytes, payloads)
        verified_bytes = None
        if verified:
            _, verified_bytes, payloads = SF.verified_bundle(storage.store, raw, payloads)
            receipt = storage.store.commit_verified(verified_bytes, payloads)
        with AF.signed_owner() as signer:
            cell = [AF.NOW]
            clock = lambda:cell[0]
            request = A.request_from_manifests(raw_bytes, verified_bytes, requested_at=AF.NOW,
                expires_at=AF.NOW+timedelta(hours=1), deployment_code_hash=signer.code)
            yield SimpleNamespace(store=storage.store, root=storage.base, raw=raw, raw_bytes=raw_bytes,
                verified_bytes=verified_bytes, payloads=payloads, digest=receipt.bundle_digest,
                request=request, document=AF.document(request, signer.key), signer=signer,
                cell=cell, clock=clock, provider=CurrentOwnerAuthority(clock=clock),
                source=R.SignedBackupSource(roots=storage.roots, limits=storage.store.limits))


def destination(e, *, provision=True, initialize=True, storage_limits=None, name='destination'):
    roots = S.BundleRoots(sealed_root=e.root/(name+'-primary'), backup_root=e.root/(name+'-backup'))
    roots.sealed_root.mkdir(); roots.backup_root.mkdir()
    store = S.BundleStore(roots=roots, limits=e.store.limits if storage_limits is None else storage_limits,
                          head_name='recovered-head')
    if provision:
        store.provision_empty()
    if initialize:
        store.head.initialize_reviewed_head(store.genesis_digest)  # Explicit test operator action only.
    return store


def restore(e, target, **changes):
    args = dict(source=e.source, destination=target, bundle_digest=e.digest, attestation_bytes=e.document,
                incident_id='incident-a', authority_provider=e.provider, clock=e.clock)
    return R.restore_signed_backup(**(args | changes))


def inspect(e, **changes):
    args = dict(source=e.source, bundle_digest=e.digest, attestation_bytes=e.document,
                authority_provider=e.provider, clock=e.clock)
    return R.inspect_signed_backup(**(args | changes))


def unchanged_original(e):
    return SF.files(e.store.roots.sealed_root), SF.files(e.store.roots.backup_root)


def no_operation(result):
    assert result.scope == 'archive_identity_only' and result.revocation_status == 'UNSUPPORTED'
    assert not result.source_authenticated and not result.research_selection_ready
    assert not result.current_use_eligible and not result.execution_ready
    assert not getattr(result, 'automatic_operational_recovery_supported', False)


def test_damaged_primary_catalog_and_old_head_restore_exact_failed_raw_and_signature_backup():
    with fixture() as e:
        target = destination(e)
        (e.store.roots.sealed_root/'catalog.jsonl').write_bytes(b'corrupted primary catalog\n')
        (e.store.head._dir/'head.json').write_bytes(b'corrupted old independent head')
        original = unchanged_original(e)
        before_registry = dict(E._EVALUATED)
        with (patch.object(S.BundleStore, 'provision_empty', side_effect=AssertionError('runtime provision')),
             patch.object(BaselineHead, 'initialize_reviewed_head', side_effect=AssertionError('head adoption')),
             patch.object(e.store, '_catalog', side_effect=AssertionError('damaged catalog trust')),
             patch.object(E, 'evaluate_capture_json', side_effect=AssertionError('not research verification'))):
            result = restore(e, target)
        no_operation(result)
        assert result.status == 'EXACT_ARCHIVE_RESTORED'
        assert result.destination_backup_verified and result.signature_backup_verified
        assert not result.original_store_modified and result.bundle_digest == e.digest
        recovered = target.read_raw(e.digest, require_backup=True)
        assert recovered.manifest_bytes == e.raw_bytes and dict(recovered.files) == e.payloads
        assert recovered.files['bad'] == b'{broken JSON' and recovered.files['empty'] == b''
        artifact = target.read_raw(result.recovery_artifact_digest, require_backup=True)
        assert artifact.files['attestation'] == e.document
        record = json.loads(artifact.files['record'])
        assert record['attestation_sha256'] == A.attestation_document_digest(e.document)
        assert record['bundle_digest'] == e.digest and record['scope'] == 'archive_identity_only'
        assert unchanged_original(e) == original and E._EVALUATED == before_registry
        assert SF.chunk_path(target,e.document).stat().st_ino != SF.chunk_path(target,e.document,True).stat().st_ino


def test_verified_restoration_includes_linked_raw_all_candidates_without_issuing_research():
    with fixture(verified=True) as e:
        target = destination(e)
        original, issued = unchanged_original(e), dict(E._EVALUATED)
        result = restore(e, target)
        no_operation(result)
        recovered = target.read_verified(e.digest, require_backup=True)
        assert recovered.manifest_bytes == e.verified_bytes and dict(recovered.files) == e.payloads
        archived = target.read_raw(result.input_archive_digest, require_backup=True)
        assert archived.manifest_bytes == e.raw_bytes
        assert tuple(c.study_id for c in recovered.manifest.candidates) == ('study-a','study-b')
        assert b'losing result retained' in recovered.files['capture_a']
        assert b'not an issued evaluation' in recovered.files['evaluation']
        assert E._EVALUATED == issued and unchanged_original(e) == original


def test_missing_primary_and_old_head_do_not_prevent_signed_backup_inspection_or_copy():
    with fixture() as e:
        target = destination(e)
        shutil.rmtree(e.store.roots.sealed_root)
        shutil.rmtree(e.store.head._dir)
        original_backup = SF.files(e.store.roots.backup_root)
        report = inspect(e)
        no_operation(report)
        assert report.source_backup_exact and report.attestation_sha256 == A.attestation_document_digest(e.document)
        result = restore(e, target)
        no_operation(result)
        assert not e.store.roots.sealed_root.exists() and not e.store.head._dir.exists()
        assert SF.files(e.store.roots.backup_root) == original_backup


def test_exact_retry_is_idempotent_and_new_incident_is_separate_evidence():
    with fixture() as e:
        target = destination(e)
        first = restore(e, target)
        before = SF.files(target.roots.sealed_root), SF.files(target.roots.backup_root)
        second = restore(e, target)
        assert first == second
        assert (SF.files(target.roots.sealed_root),SF.files(target.roots.backup_root)) == before
        third = restore(e, target, incident_id='incident-b')
        assert third.recovery_artifact_digest != first.recovery_artifact_digest
        assert target.read_raw(first.recovery_artifact_digest).files['attestation'] == e.document
        assert target.read_raw(third.recovery_artifact_digest).files['attestation'] == e.document


def test_missing_or_changed_backup_payload_or_manifest_prevents_any_destination_write():
    for which in ('payload','manifest','missing'):
        with fixture() as e:
            target = destination(e)
            value = e.raw_bytes if which == 'manifest' else e.payloads['bad']
            path = SF.chunk_path(e.store,value,True)
            if which == 'missing': path.unlink()
            else: path.write_bytes(path.read_bytes()+b'changed')
            before = SF.files(e.root)
            AF.refused(lambda:restore(e,target))
            assert SF.files(e.root) == before


def test_verified_linked_raw_manifest_damage_refuses_even_when_target_files_are_intact():
    with fixture(verified=True) as e:
        target = destination(e)
        SF.chunk_path(e.store,e.raw_bytes,True).unlink()
        before = SF.files(e.root)
        AF.refused(lambda:restore(e,target))
        assert SF.files(e.root) == before


def test_counterfeit_provider_store_and_reused_inspection_are_not_authority_inputs():
    with fixture() as e:
        target = destination(e)
        report = inspect(e)
        observed = e.provider(AF.NOW)
        before = SF.files(e.root)
        for provider in (lambda _:observed, observed, report, True):
            AF.refused(lambda provider=provider:restore(e,target,authority_provider=provider),
                       'BUNDLE_RECOVERY_ACTUAL_PROVIDER_REQUIRED')
        AF.refused(lambda:restore(e,target,clock=lambda:AF.NOW),'BUNDLE_RECOVERY_ACTUAL_PROVIDER_REQUIRED')
        AF.refused(lambda:restore(e,report),'BUNDLE_RECOVERY_DESTINATION_REQUIRED')
        AF.refused(lambda:restore(e,target,source=report),'BUNDLE_RECOVERY_SOURCE_REQUIRED')
        assert SF.files(e.root) == before


def test_wrong_signature_target_deployment_or_expiry_refuses_before_mutation():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    with fixture() as e:
        target = destination(e)
        other = Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
        wrong = A.request_from_manifests(e.raw_bytes,None,requested_at=AF.NOW,
            expires_at=AF.NOW+timedelta(hours=1),deployment_code_hash='f'*64)
        before = SF.files(e.root)
        AF.refused(lambda:restore(e,target,bundle_digest='f'*64),'BUNDLE_RECOVERY_TARGET_MISMATCH')
        for document in (AF.document(e.request,other), AF.document(wrong,e.signer.key),
                         AF.document(e.request,e.signer.key,domain=b'another-signing-domain/1\n')):
            AF.refused(lambda document=document:restore(e,target,attestation_bytes=document))
        e.cell[0] += timedelta(hours=1)
        AF.refused(lambda:restore(e,target),'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
        assert SF.files(e.root) == before


def test_policy_mismatch_and_unprovisioned_destination_cannot_auto_seed():
    for provision in (False, True):
        with fixture() as e:
            target = destination(e,provision=provision,initialize=False)
            before = SF.files(e.root)
            with (patch.object(S.BundleStore,'provision_empty',side_effect=AssertionError('auto provision')),
                  patch.object(BaselineHead,'initialize_reviewed_head',side_effect=AssertionError('auto seed'))):
                AF.refused(lambda:restore(e,target))
            assert SF.files(e.root) == before
    with fixture() as e:
        target = destination(e,storage_limits=replace(e.store.limits,max_catalog_records=127))
        before = SF.files(e.root)
        AF.refused(lambda:restore(e,target),'BUNDLE_RECOVERY_POLICY_MISMATCH')
        assert SF.files(e.root) == before


def test_overlapping_original_or_destination_roots_are_refused_without_writes():
    with fixture() as e:
        before = unchanged_original(e)
        AF.refused(lambda:restore(e,e.store),'BUNDLE_RECOVERY_ROOT_OVERLAP')
        assert unchanged_original(e) == before
        target = destination(e)
        overlap = R.SignedBackupSource(roots=S.BundleRoots(sealed_root=target.roots.sealed_root,
            backup_root=e.store.roots.backup_root),limits=e.store.limits)
        before = SF.files(e.root)
        AF.refused(lambda:restore(e,target,source=overlap),'BUNDLE_RECOVERY_ROOT_OVERLAP')
        nested = R.SignedBackupSource(roots=S.BundleRoots(sealed_root=target.roots.sealed_root/'missing',
            backup_root=e.store.roots.backup_root),limits=e.store.limits)
        AF.refused(lambda:restore(e,target,source=nested),'BUNDLE_RECOVERY_ROOT_OVERLAP')
        assert SF.files(e.root) == before


def test_source_backup_symlink_and_hardlink_payload_are_refused():
    for kind in ('symlink','hardlink'):
        with fixture() as e:
            target = destination(e)
            if kind == 'symlink':
                root = e.store.roots.backup_root
                moved = e.root/'actual-backup'
                root.rename(moved); root.symlink_to(moved,target_is_directory=True)
            else:
                path = SF.chunk_path(e.store,e.payloads['bad'],True)
                os.link(path,e.root/'linked-original')
            before = SF.files(e.root)
            AF.refused(lambda:restore(e,target))
            assert SF.files(e.root) == before


def test_source_lock_replacement_between_actual_reads_is_detected():
    with fixture() as e:
        target = destination(e)
        lock = e.store.roots.backup_root/'payload-objects'/'objects.lock'
        displaced = e.root/'displaced-lock'
        before = SF.files(target.roots.sealed_root),SF.files(target.roots.backup_root)
        actual, count = O.EvidenceObjectStore.read, [0]
        def replace_lock(store,reference):
            result = actual(store,reference)
            if store.root == e.store.roots.backup_root/'payload-objects' and count[0] == 0:
                count[0] += 1
                lock.rename(displaced); lock.write_bytes(b'0')
            return result
        with patch.object(O.EvidenceObjectStore,'read',replace_lock):
            AF.refused(lambda:restore(e,target),'BUNDLE_RECOVERY_SOURCE_CHANGED')
        assert count[0] == 1
        assert (SF.files(target.roots.sealed_root),SF.files(target.roots.backup_root)) == before


def test_whole_batch_catalog_quota_is_refused_before_staging_any_part():
    for verified,records in ((False,2),(True,4)):
        with fixture(verified=verified,storage_limits=SF.limits(max_catalog_records=records)) as e:
            target = destination(e)
            before = SF.files(e.root)
            with patch.object(O.EvidenceObjectStore,'stage',side_effect=AssertionError('partial admission')):
                AF.refused(lambda:restore(e,target),'BUNDLE_STORE_RESOURCE_LIMIT')
            assert SF.files(e.root) == before


def test_signature_artifact_file_limit_refuses_before_copy_and_preserves_source_policy():
    base = SF.limits()
    small = replace(base,format_limits=replace(base.format_limits,max_file_bytes=1024))
    with fixture(storage_limits=small) as e:
        assert len(e.document) > 1024
        target = destination(e)
        before = SF.files(e.root)
        with patch.object(O.EvidenceObjectStore,'stage',side_effect=AssertionError('partial admission')):
            AF.refused(lambda:restore(e,target))
        assert SF.files(e.root) == before
        assert target.limits == e.store.limits == small


def test_destination_id_collision_refuses_before_any_recovery_stage():
    with fixture() as e:
        target = destination(e)
        _,raw,payloads = SF.raw_archive(target,{'different':b'other evidence'})
        target.archive_raw(raw,payloads)
        before = SF.files(e.root)
        with patch.object(O.EvidenceObjectStore,'stage',side_effect=AssertionError('collision after stage')):
            AF.refused(lambda:restore(e,target),'BUNDLE_STORE_ID_REUSED')
        assert SF.files(e.root) == before


def test_interruption_after_raw_commit_preserves_it_and_exact_retry_finishes():
    with fixture(verified=True) as e:
        target = destination(e)
        original = unchanged_original(e)
        def interrupted(*args,**kwargs):
            raise S.BundleStoreError('BUNDLE_STORE_IO_REFUSED')
        with patch.object(target,'commit_verified',side_effect=interrupted):
            AF.refused(lambda:restore(e,target),'BUNDLE_STORE_IO_REFUSED')
        raw_digest = F.raw_archive_digest(e.raw)
        assert target.read_raw(raw_digest).manifest_bytes == e.raw_bytes
        AF.refused(lambda:target.read_verified(e.digest),'BUNDLE_STORE_NOT_PUBLISHED')
        result = restore(e,target)
        assert result.bundle_digest == e.digest and result.signature_backup_verified
        assert unchanged_original(e) == original


def test_cas_failure_preserves_unconfirmed_evidence_and_never_reanchors():
    with fixture() as e:
        target = destination(e)
        initial_head, original = target.head.read(), unchanged_original(e)
        with patch.object(target.head,'compare_and_set',return_value=False):
            AF.refused(lambda:restore(e,target),'BUNDLE_STORE_HEAD_UPDATE_REFUSED')
        assert target.head.read() == initial_head
        assert (target.roots.sealed_root/'catalog.jsonl').stat().st_size > 0
        evidence = SF.files(target.roots.sealed_root),SF.files(target.roots.backup_root)
        with patch.object(BaselineHead,'initialize_reviewed_head',side_effect=AssertionError('reanchor')):
            AF.refused(lambda:restore(e,target))
        assert (SF.files(target.roots.sealed_root),SF.files(target.roots.backup_root)) == evidence
        assert unchanged_original(e) == original


def test_failed_final_real_authentication_preserves_committed_exact_copies_without_success():
    with fixture() as e:
        target = destination(e)
        actual = U.authenticate_bundle_attestation
        calls = []
        def expired(*args,**kwargs):
            calls.append(True)
            e.cell[0] += timedelta(hours=1)
            return actual(*args,**kwargs)
        with patch.object(U,'authenticate_bundle_attestation',side_effect=expired):
            AF.refused(lambda:restore(e,target),'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
        assert calls == [True] and target.read_raw(e.digest).manifest_bytes == e.raw_bytes
        artifact,_,_ = build_recovery_artifact(e.document,incident_id='incident-a',limits=target.limits)
        assert target.read_raw(F.raw_archive_digest(artifact)).files['attestation'] == e.document


def test_long_exact_copy_requires_fresh_final_transaction_and_real_destination_authentication():
    with fixture() as e:
        target = destination(e)
        actual, count = target.archive_raw, [0]
        def slow(*args,**kwargs):
            result = actual(*args,**kwargs)
            count[0] += 1
            if count[0] == 1: e.cell[0] += timedelta(seconds=31)
            return result
        with patch.object(target,'archive_raw',side_effect=slow):
            result = restore(e,target)
        assert result.verified_at == AF.NOW+timedelta(seconds=31)
        assert result.signature_backup_verified and result.destination_backup_verified
        assert target.read_raw(e.digest).manifest_bytes == e.raw_bytes


def test_final_validation_initial_observation_cannot_be_refreshed_after_slow_auxiliary_read():
    with fixture() as e:
        target = destination(e)
        artifact,_,_ = build_recovery_artifact(e.document,incident_id='incident-a',limits=target.limits)
        digest = F.raw_archive_digest(artifact)
        actual, reads = target.read_raw, [0]
        def slow(digest_arg,**kwargs):
            result = actual(digest_arg,**kwargs)
            if digest_arg == digest:
                reads[0] += 1
                if reads[0] == 2: e.cell[0] += timedelta(seconds=31)
            return result
        with patch.object(target,'read_raw',side_effect=slow):
            AF.refused(lambda:restore(e,target),'ARCHIVE_AUTH_OWNER_AUTHORITY_STALE')
        assert reads[0] == 2
        assert target.read_raw(e.digest).manifest_bytes == e.raw_bytes


def test_source_graph_read_clock_rollback_or_staleness_refuses_without_destination_writes():
    for delta in (-1,31):
        with fixture() as e:
            target = destination(e)
            before = SF.files(e.root)
            actual, count = O.EvidenceObjectStore.read, [0]
            def slow(store,reference):
                result = actual(store,reference)
                if store.root == e.store.roots.backup_root/'payload-objects' and count[0] == 0:
                    count[0] += 1; e.cell[0] += timedelta(seconds=delta)
                return result
            with patch.object(O.EvidenceObjectStore,'read',slow):
                AF.refused(lambda:restore(e,target))
            assert SF.files(e.root) == before


def test_final_auxiliary_backup_is_rechecked_and_failure_cannot_return_complete():
    with fixture() as e:
        target = destination(e)
        artifact,_,_ = build_recovery_artifact(e.document,incident_id='incident-a',limits=target.limits)
        digest = F.raw_archive_digest(artifact)
        actual, reads = target.read_raw, [0]
        def corrupt(digest_arg,**kwargs):
            if digest_arg == digest:
                reads[0] += 1
                if reads[0] == 2:
                    path = SF.chunk_path(target,e.document,True)
                    path.write_bytes(path.read_bytes()+b'damage')
            return actual(digest_arg,**kwargs)
        with patch.object(target,'read_raw',side_effect=corrupt):
            AF.refused(lambda:restore(e,target))
        assert reads[0] == 2 and target.read_raw(e.digest).manifest_bytes == e.raw_bytes


def test_frozen_source_configuration_tampering_and_unavailable_inode_are_rejected():
    with fixture() as e:
        target = destination(e)
        invalid = R.SignedBackupSource(roots=e.source.roots,limits=e.source.limits)
        object.__delattr__(invalid,'limits')
        AF.refused(lambda:restore(e,target,source=invalid),'BUNDLE_RECOVERY_SOURCE_CHANGED')
        actual = R.os.lstat
        def unknown(path,*args,**kwargs):
            info = actual(path,*args,**kwargs)
            if path == e.source.roots.backup_root:
                return SimpleNamespace(st_dev=info.st_dev,st_ino=0,st_mode=info.st_mode,st_file_attributes=0)
            return info
        before = SF.files(e.root)
        with patch.object(R.os,'lstat',side_effect=unknown):
            AF.refused(lambda:restore(e,target),'BUNDLE_RECOVERY_IDENTITY_UNAVAILABLE')
        assert SF.files(e.root) == before


def test_windows_pin_adapter_passes_exact_strings_and_holds_all_source_directory_pins():
    """Fake native-contract check only; this is not a Windows execution claim."""
    with fixture() as e:
        events = []
        class Pin:
            def __init__(self,path):
                assert type(path) is str
                self.path = path
            def __enter__(self): events.append(('enter',self.path)); return self
            def check(self): events.append(('check',self.path))
            def __exit__(self,*args): events.append(('exit',self.path))
        # Patch only this module's namespace, not global os.name/Path dispatch.
        windows = SimpleNamespace(name='nt',lstat=os.lstat,fstat=os.fstat,close=os.close)
        with patch.object(R,'os',windows), patch.object(R,'pin_windows_directory',side_effect=Pin):
            with R._SourcePin(e.source) as pin:
                pin.check()
                assert len([row for row in events if row[0] == 'enter']) == 3
                assert not any(row[0] == 'exit' for row in events)
        entered = [path for kind,path in events if kind == 'enter']
        exited = [path for kind,path in events if kind == 'exit']
        assert exited == list(reversed(entered))


def test_source_directory_open_failure_closes_prior_handles_and_returns_fixed_diagnostic():
    with fixture() as e:
        target = destination(e)
        before = SF.files(e.root)
        actual, handles = R._open_posix_directory, []
        def failed(path):
            if handles: raise OSError('private directory failure must not escape')
            handle = actual(path); handles.append(handle); return handle
        with patch.object(R,'_open_posix_directory',side_effect=failed):
            AF.refused(lambda:restore(e,target),'BUNDLE_RECOVERY_IO_REFUSED')
        assert len(handles) == 1
        try: os.fstat(handles[0])
        except OSError: pass
        else: raise AssertionError('source directory handle leaked')
        with patch.object(R,'_open_posix_directory',side_effect=OSError('private inspect path')):
            AF.refused(lambda:inspect(e),'BUNDLE_RECOVERY_IO_REFUSED')
        assert SF.files(e.root) == before
