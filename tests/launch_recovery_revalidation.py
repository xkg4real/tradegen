"""Destination-only revalidation over actual restored archives and owner logs.

All signatures are disposable Ed25519 keys over the actual full code digest.
Small verified fixtures deliberately contain unissued numerical claims: archive
identity never makes them research approvals. A separate actual-recorder case
covers genuine fixed/carry bundle production without reissuing an evaluation.
No real account, credential, network, notification or order transport is used.
"""
from contextlib import contextmanager
from datetime import timedelta
import base64
import json
import shutil
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_recovery as R, bundle_attestation as A, bundle_auth as U
from execution_launch import research_bundle_format as F, research_bundle_store as B
from execution_launch import research_revocation as V, research_bundle as RB, strategy as E
from execution_launch.recovery_artifact import build_recovery_artifact
from tests import compliance_fixtures as CF
from tests import launch_bundle_recovery as BR, launch_bundle_auth as AF
from tests import launch_research_bundle_store as BF, launch_research_bundle as RF


@contextmanager
def restored(*, verified=False, at=None):
    with BR.fixture(verified=verified) as e:
        if at is not None:
            e.cell[0]=at
            e.request=A.request_from_manifests(e.raw_bytes,e.verified_bytes,requested_at=at,
                expires_at=at+timedelta(hours=1),deployment_code_hash=e.signer.code)
            e.document=AF.document(e.request,e.signer.key,issued_at=at)
        target=BR.destination(e)
        result=BR.restore(e,target)
        yield SimpleNamespace(**vars(e),target=target,restored=result)


def verify(e, **changes):
    args=dict(destination=e.target,bundle_digest=e.digest,attestation_bytes=e.document,
              incident_id='incident-a',authority_provider=e.provider,clock=e.clock)
    return R.verify_restored_archive(**(args|changes))


def refused(call, code=None):
    return AF.refused(call,code)


def archive_bytes(target):
    return BF.files(target.roots.sealed_root),BF.files(target.roots.backup_root)


def no_operation(value, *, status='NOT_REVOKED_AT_HEAD'):
    assert type(value) is R.RestoredArchiveVerification
    assert value.status=='RESTORED_ARCHIVE_REVERIFIED' and value.scope=='archive_identity_only'
    assert value.revocation_status==status
    assert value.destination_backup_verified and value.signature_backup_verified
    for name in ('archive_storage_modified','source_authenticated','research_selection_ready',
                 'current_use_eligible','execution_ready','automatic_operational_recovery_supported',
                 'quarantine_release_supported'):
        assert getattr(value,name) is False,(name,getattr(value,name))


def revoke(e, *, document=None, target=None):
    raw=e.document if document is None else document
    digest=V.revocation_target(raw,purpose=A.PURPOSE) if target is None else target
    CF.sign(e.signer.key,V.EVENT_KIND,dict(purpose=A.PURPOSE,target_sha256=digest,reason_code='OWNER_WITHDRAWN'),
            utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ'))
    return digest


def test_raw_and_complete_verified_restored_graphs_verify_after_source_roots_disappear():
    for verified in (False,True):
        with restored(verified=verified) as e:
            shutil.rmtree(e.source.roots.sealed_root)
            shutil.rmtree(e.source.roots.backup_root)
            before=archive_bytes(e.target);issued=dict(E._EVALUATED)
            with (patch.object(R,'_source_configuration',side_effect=AssertionError('source dependency')),
                  patch.object(R,'_read_graph',side_effect=AssertionError('source graph read')),
                  patch.object(R,'restore_signed_backup',side_effect=AssertionError('second copy')),
                  patch.object(B.BundleStore,'archive_raw',side_effect=AssertionError('archive mutation')),
                  patch.object(B.BundleStore,'commit_verified',side_effect=AssertionError('verified mutation')),
                  patch.object(e.target.head,'initialize_reviewed_head',side_effect=AssertionError('head seed')),
                  patch.object(e.target.head,'compare_and_set',side_effect=AssertionError('head CAS')),
                  patch.object(E,'evaluate_capture_json',side_effect=AssertionError('new numerical issuance'))):
                result=verify(e)
            no_operation(result)
            assert result.bundle_digest==e.digest and result.verified_at==e.cell[0]
            assert result.recovery_artifact_digest==e.restored.recovery_artifact_digest
            assert result.request_sha256==e.request['request_sha256']
            assert result.attestation_sha256==A.attestation_document_digest(e.document)
            assert result.revocation_target_sha256==V.revocation_target(e.document,purpose=A.PURPOSE)
            assert result.revocation_owner_head==e.provider(e.cell[0]).context.owner.head
            assert archive_bytes(e.target)==before and E._EVALUATED==issued
            if verified:
                read=e.target.read_verified(e.digest,require_backup=True)
                assert tuple(row.study_id for row in read.manifest.candidates)==('study-a','study-b')
                assert b'losing result retained' in read.files['capture_a']
                assert b'not an issued evaluation' in read.files['evaluation']
            else:
                read=e.target.read_raw(e.digest,require_backup=True)
                assert read.files['bad']==b'{broken JSON' and read.files['empty']==b''


def test_actual_fixed_and_carry_recorder_bundles_reverify_without_new_evaluation_or_source():
    for carry in (False,True):
        with RF.fixture(carry=carry) as original:
            final=RF.finalize(original)
            assert final.status=='VERIFIED_UNAPPROVED',final.reasons
            saved=original.store.read_verified(final.bundle_digest,require_backup=True)
            raw=original.store.read_raw(final.input_archive_digest,require_backup=True)
            with AF.signed_owner() as signer:
                cell=[AF.NOW];clock=lambda:cell[0]
                request=A.request_from_manifests(raw.manifest_bytes,saved.manifest_bytes,
                    requested_at=AF.NOW,expires_at=AF.NOW+timedelta(hours=1),deployment_code_hash=signer.code)
                e=SimpleNamespace(root=original.base,store=original.store,digest=final.bundle_digest,
                    document=AF.document(request,signer.key),source=R.SignedBackupSource(
                        roots=original.store.roots,limits=original.store.limits),clock=clock,
                    provider=CurrentOwnerAuthority(clock=clock))
                e.target=BR.destination(e)
                result=BR.restore(e,e.target)
                issued=dict(E._EVALUATED)
                shutil.rmtree(original.work)
                shutil.rmtree(original.store.roots.sealed_root)
                shutil.rmtree(original.store.roots.backup_root)
                before=archive_bytes(e.target)
                with patch.object(E,'evaluate_capture_json',side_effect=AssertionError('re-evaluation')):
                    observed=verify(e)
                no_operation(observed)
                assert observed.recovery_artifact_digest==result.recovery_artifact_digest
                assert E._EVALUATED==issued and archive_bytes(e.target)==before
                retained=e.target.read_verified(final.bundle_digest,require_backup=True)
                assert retained.manifest_bytes==saved.manifest_bytes and dict(retained.files)==dict(saved.files)


def test_actual_target_without_signature_artifact_cannot_be_called_restored():
    with BR.fixture(verified=True) as e:
        target=BR.destination(e)
        raw=e.store.read_raw(F.raw_archive_digest(e.raw),require_backup=True)
        saved=e.store.read_verified(e.digest,require_backup=True)
        target.archive_raw(raw.manifest_bytes,dict(raw.files))
        target.commit_verified(saved.manifest_bytes,dict(saved.files))
        before=archive_bytes(target)
        refused(lambda:R.verify_restored_archive(target,e.digest,e.document,incident_id='incident-a',
            authority_provider=e.provider,clock=e.clock),'BUNDLE_STORE_NOT_PUBLISHED')
        assert archive_bytes(target)==before


def test_missing_or_changed_signature_artifact_primary_and_backup_are_never_repaired():
    for name,backup,missing in (('attestation',False,True),('attestation',True,False),('record',False,False),('record',True,True)):
        with restored() as e:
            artifact=e.target.read_raw(e.restored.recovery_artifact_digest,require_backup=True)
            path=BF.chunk_path(e.target,artifact.files[name],backup)
            if missing:
                path.unlink()
            else:
                raw=path.read_bytes();path.write_bytes(bytes([raw[0]^1])+raw[1:])
            before=archive_bytes(e.target)
            refused(lambda:verify(e))
            assert archive_bytes(e.target)==before


def test_one_original_candidate_or_linked_raw_manifest_missing_refuses_whole_verification():
    for which,backup in (('capture_b',False),('capture_a',True),('raw-manifest',True)):
        with restored(verified=True) as e:
            value=e.raw_bytes if which=='raw-manifest' else e.payloads[which]
            path=BF.chunk_path(e.target,value,backup)
            path.unlink()
            before=archive_bytes(e.target)
            refused(lambda:verify(e))
            assert not path.exists() and archive_bytes(e.target)==before


def test_wrong_incident_document_target_or_counterfeit_inputs_are_not_trust():
    with restored() as e:
        baseline=archive_bytes(e.target)
        observed=e.provider(e.cell[0]);saved=e.target.read_raw(e.digest)
        for provider in (True,e.restored,observed,lambda _:observed):
            refused(lambda provider=provider:verify(e,authority_provider=provider),
                    'BUNDLE_RECOVERY_ACTUAL_PROVIDER_REQUIRED')
        for target in (True,e.restored,saved):
            refused(lambda target=target:verify(e,destination=target),'BUNDLE_RECOVERY_DESTINATION_REQUIRED')
        refused(lambda:verify(e,clock=lambda:e.cell[0]),'BUNDLE_RECOVERY_ACTUAL_PROVIDER_REQUIRED')
        refused(lambda:verify(e,incident_id='different-incident'),'BUNDLE_STORE_NOT_PUBLISHED')
        refused(lambda:verify(e,bundle_digest='f'*64),'BUNDLE_RECOVERY_TARGET_MISMATCH')
        pretty=json.dumps(json.loads(e.document),indent=2).encode('ascii')
        refused(lambda:verify(e,attestation_bytes=pretty),'ARCHIVE_ATTESTATION_FORMAT_INVALID')
        assert archive_bytes(e.target)==baseline


def test_uninitialized_destination_is_not_seeded_or_adopted():
    with BR.fixture() as e:
        target=BR.destination(e,initialize=False)
        before=archive_bytes(target)
        with patch.object(target.head,'initialize_reviewed_head',side_effect=AssertionError('implicit adoption')):
            refused(lambda:R.verify_restored_archive(target,e.digest,e.document,incident_id='incident-a',
                authority_provider=e.provider,clock=e.clock))
        assert not target.head._dir.exists() and archive_bytes(target)==before


def test_actual_destination_head_corruption_lock_contention_and_root_alias_refuse():
    for mode in ('head','lock','root-alias'):
        with restored() as e:
            if mode=='head':
                (e.target.head._dir/'head.json').write_bytes(b'{broken current destination head')
            elif mode=='root-alias':
                original=e.target.roots.sealed_root
                displaced=original.with_name(original.name+'-original')
                original.rename(displaced)
                CF.directory_link(original,displaced)
            before=archive_bytes(e.target)
            locked=False
            try:
                if mode=='lock':
                    locked=B._LOCK.acquire(blocking=False);assert locked
                refused(lambda:verify(e))
            finally:
                if locked:B._LOCK.release()
            assert archive_bytes(e.target)==before


def test_real_final_owner_revocation_is_reported_without_grant_or_deleting_archives():
    with restored() as e:
        before=archive_bytes(e.target)
        original=verify(e);no_operation(original)
        revoke(e,target='f'*64)
        unrelated=verify(e);no_operation(unrelated)
        assert unrelated.revocation_owner_head[0]>original.revocation_owner_head[0]
        target=revoke(e)
        result=verify(e);no_operation(result,status='REVOKED')
        assert result.revocation_target_sha256==target
        assert result.revocation_owner_head==e.provider(e.cell[0]).context.owner.head
        assert result.revocation_owner_head[0]>unrelated.revocation_owner_head[0]
        assert archive_bytes(e.target)==before


def test_noncanonical_archive_json_is_refused_and_canonical_roundtrip_retains_exact_target():
    with restored() as e:
        parsed=json.loads(e.document)
        canonical=A.attestation_document_bytes(parsed['body'],base64.b64decode(parsed['signature_b64']))
        assert canonical==e.document
        target=revoke(e,document=canonical)
        result=verify(e);no_operation(result,status='REVOKED')
        assert result.revocation_target_sha256==target
        pretty=json.dumps(parsed,indent=2).encode('ascii')
        assert pretty!=canonical
        before=archive_bytes(e.target)
        refused(lambda:verify(e,attestation_bytes=pretty),'ARCHIVE_ATTESTATION_FORMAT_INVALID')
        assert archive_bytes(e.target)==before


def test_revocation_after_nested_authentication_comes_from_outer_final_actual_owner():
    with restored() as e:
        actual=e.target.read_raw;actual_owner=owner.load_context;reads=[];changed=[]
        def read(digest,**kwargs):
            value=actual(digest,**kwargs)
            if digest==e.restored.recovery_artifact_digest:reads.append(digest)
            return value
        def observe(*args,**kwargs):
            if len(reads)==2 and not changed:
                changed.append(revoke(e))
            return actual_owner(*args,**kwargs)
        with patch.object(e.target,'read_raw',side_effect=read),patch.object(owner,'load_context',side_effect=observe):
            result=verify(e)
        no_operation(result,status='REVOKED')
        assert len(reads)==2 and changed==[result.revocation_target_sha256]
        assert result.revocation_owner_head==e.provider(e.cell[0]).context.owner.head


def test_expired_or_future_original_signature_cannot_be_refreshed_by_revalidation():
    for delta in (timedelta(hours=1),-timedelta(microseconds=1)):
        with restored() as e:
            e.cell[0]=AF.NOW+delta
            e.provider=CurrentOwnerAuthority(clock=e.clock)
            before=archive_bytes(e.target)
            refused(lambda:verify(e),'ARCHIVE_AUTH_EXPIRED_OR_FUTURE')
            assert archive_bytes(e.target)==before


def test_slow_final_artifact_does_not_refresh_original_owner_age_or_cross_expiry():
    for delta in (timedelta(seconds=31),timedelta(hours=1),-timedelta(microseconds=1)):
        with restored() as e:
            actual=e.target.read_raw;reads=[]
            def slow(digest,**kwargs):
                value=actual(digest,**kwargs)
                if digest==e.restored.recovery_artifact_digest:
                    reads.append(digest)
                    if len(reads)==2:e.cell[0]+=delta
                return value
            with patch.object(e.target,'read_raw',side_effect=slow):
                code=refused(lambda:verify(e))
            expected='STALE' if delta==timedelta(seconds=31) else 'EXPIRED_OR_FUTURE' if delta>timedelta(0) else 'CLOCK_ROLLBACK'
            assert expected in code,(code,expected)
            assert len(reads)==2


def test_exact_thirty_second_final_observation_bound_accepts_boundary_only():
    for delay,accepted in ((timedelta(seconds=30),True),(timedelta(seconds=30,microseconds=1),False)):
        with restored() as e:
            actual=e.target.read_raw;reads=[]
            def slow(digest,**kwargs):
                value=actual(digest,**kwargs)
                if digest==e.restored.recovery_artifact_digest:
                    reads.append(digest)
                    if len(reads)==2:e.cell[0]+=delay
                return value
            with patch.object(e.target,'read_raw',side_effect=slow):
                if accepted:
                    result=verify(e);no_operation(result)
                    assert result.verified_at==AF.NOW+delay
                else:
                    assert 'STALE' in refused(lambda:verify(e))
            assert len(reads)==2


def test_slow_actual_owner_loader_is_not_relabelled_with_a_fresh_timestamp():
    with restored() as e:
        actual=owner.load_context;seen=[]
        def slow(*args,**kwargs):
            value=actual(*args,**kwargs)
            if not seen:
                seen.append(True);e.cell[0]+=timedelta(seconds=31)
            return value
        with patch.object(owner,'load_context',side_effect=slow):
            refused(lambda:verify(e),'OWNER_AUTHORITY_OBSERVATION_LATE')
        assert seen


def test_current_code_approval_and_key_changes_during_last_artifact_read_refuse():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    for mode in ('code','key'):
        with restored() as e:
            actual=e.target.read_raw;reads=[]
            def read(digest,**kwargs):
                value=actual(digest,**kwargs)
                if digest==e.restored.recovery_artifact_digest:
                    reads.append(digest)
                    if len(reads)==2:
                        utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ')
                        if mode=='code':CF.other_code(e.signer.key,utc=utc)
                        else:
                            new=Ed25519PrivateKey.from_private_bytes(bytes(range(1,33)))
                            encode=lambda key:base64.b64encode(key.public_key().public_bytes_raw()).decode('ascii')
                            CF.sign(e.signer.key,'key_rotated',dict(old_pubkey_b64=encode(e.signer.key),
                                new_pubkey_b64=encode(new)),utc=utc)
                            CF.write_pubkey(owner.PUBKEY_PATH,new)
                return value
            before=archive_bytes(e.target)
            with patch.object(e.target,'read_raw',side_effect=read):
                code=refused(lambda:verify(e))
            assert code==('OWNER_AUTHORITY_CODE_NOT_SIGNED' if mode=='code' else 'OWNER_AUTHORITY_KEY_CHANGED'),code
            assert len(reads)==2 and archive_bytes(e.target)==before


def test_actual_owner_prefix_rollback_is_rejected_and_latched():
    with restored() as e:
        before=owner.log_path().read_bytes()
        CF.sign(e.signer.key,'age_of_majority',dict(birth_date='2000-01-01',evidence='fixture only'),
                utc=e.cell[0].strftime('%Y-%m-%dT%H:%M:%SZ'))
        e.provider(e.cell[0])
        owner.log_path().write_bytes(before)
        code=refused(lambda:verify(e))
        assert code in ('OWNER_AUTHORITY_OWNER_STATE_BROKEN','OWNER_AUTHORITY_LOG_REWRITTEN'),code
        with patch.object(owner,'load_context',side_effect=AssertionError('latched provider reloaded')):
            refused(lambda:verify(e),code)


def test_artifact_mutation_between_actual_reads_refuses_without_repair():
    with restored() as e:
        actual=e.target.read_raw;reads=[]
        path=BF.chunk_path(e.target,e.document,True)
        original=path.read_bytes()
        def read(digest,**kwargs):
            if digest==e.restored.recovery_artifact_digest:
                reads.append(digest)
                if len(reads)==2:path.write_bytes(bytes([original[0]^1])+original[1:])
            return actual(digest,**kwargs)
        with patch.object(e.target,'read_raw',side_effect=read):
            refused(lambda:verify(e))
        assert len(reads)==2 and path.read_bytes()!=original
        assert e.target.read_raw(e.digest,require_backup=True).backup_verified


def test_legacy_restore_and_inspection_keep_their_existing_unsupported_status_and_bytes():
    with restored() as e:
        assert e.restored.revocation_status=='UNSUPPORTED'
        prior=archive_bytes(e.target)
        fresh=verify(e);no_operation(fresh)
        inspected=BR.inspect(e)
        assert inspected.revocation_status=='UNSUPPORTED'
        retried=BR.restore(e,e.target)
        assert retried==e.restored and archive_bytes(e.target)==prior
        assert e.target.read_raw(fresh.recovery_artifact_digest).files['attestation']==e.document


def test_final_canonical_revocation_computation_is_inside_original_freshness_and_expiry_window():
    for delta,code in ((timedelta(seconds=31),'BUNDLE_RECOVERY_AUTHORITY_STALE'),
                       (timedelta(hours=1),'BUNDLE_RECOVERY_EXPIRED_OR_FUTURE')):
        with restored() as e:
            actual=R.revocation_target;seen=[]
            def slow(*args,**kwargs):
                value=actual(*args,**kwargs)
                seen.append(value);e.cell[0]+=delta
                return value
            with patch.object(R,'revocation_target',side_effect=slow):
                refused(lambda:verify(e),code)
            assert seen==[V.revocation_target(e.document,purpose=A.PURPOSE)]


def test_original_seoul_day_is_not_refreshed_across_final_artifact_read():
    at=AF.NOW+timedelta(hours=14,minutes=59,seconds=59)
    with restored(at=at) as e:
        actual=e.target.read_raw;reads=[]
        def read(digest,**kwargs):
            value=actual(digest,**kwargs)
            if digest==e.restored.recovery_artifact_digest:
                reads.append(digest)
                if len(reads)==2:e.cell[0]+=timedelta(seconds=2)
            return value
        with patch.object(e.target,'read_raw',side_effect=read):
            refused(lambda:verify(e),'ARCHIVE_AUTH_OWNER_APPROVAL_REQUIRED')
        assert len(reads)==2
