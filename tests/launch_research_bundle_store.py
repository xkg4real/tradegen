"""Actual immutable-object/catalog/head/backup tests using invented research bytes.

Store fixtures deliberately do not claim a real evaluator or approval issuer.
All roots are temporary; no key, source API, account or order transport is used.
"""
from contextlib import contextmanager
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import evidence_objects as E
from execution_launch import research_bundle_format as F
from execution_launch import research_bundle_store as S
from execution_launch.baseline_head import BaselineHeadError
from tests import compliance_fixtures as CF


def limits(**changes):
    return S.BundleStoreLimits(**(dict(format_limits=F.BundleLimits(max_manifest_bytes=65536, max_files=64,
        max_file_bytes=65536, max_total_bytes=1024*1024, max_candidates=8, max_name_bytes=256),
        object_limits=E.ObjectLimits(chunk_bytes=4096, max_payload_bytes=65536, max_chunks=16, max_manifest_bytes=4096),
        primary_budget=E.StoreBudget(max_bytes=4*1024*1024, max_objects=512),
        backup_budget=E.StoreBudget(max_bytes=4*1024*1024, max_objects=512),
        max_catalog_bytes=1024*1024, max_catalog_records=128) | changes))


@contextmanager
def fixture(*, provision=True, initialize=True, storage_limits=None):
    with CF.temp_home(), tempfile.TemporaryDirectory(prefix='tradegen_bundle_') as raw:
        root = Path(raw)
        roots = S.BundleRoots(sealed_root=root/'primary', backup_root=root/'backup')
        roots.sealed_root.mkdir(); roots.backup_root.mkdir()
        args = dict(roots=roots, limits=limits() if storage_limits is None else storage_limits, head_name='bundle-head')
        store = S.BundleStore(**args)
        if provision:
            store.provision_empty()
        if initialize:
            store.head.initialize_reviewed_head(store.genesis_digest)  # explicit fixture operator step
        yield SimpleNamespace(store=store, roots=roots, base=root, args=args,
                              reopen=lambda **changes: S.BundleStore(**(args | changes)))


def files(root):
    return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}


def refused(call, *codes):
    try:
        call()
    except (S.BundleStoreError, F.BundleFormatError, E.EvidenceObjectError, BaselineHeadError) as exc:
        assert re.fullmatch(r'[A-Z][A-Z0-9_]+', str(exc)), 'non-code diagnostic'
        if codes:
            assert str(exc) in codes, (str(exc), codes)
        return str(exc)
    raise AssertionError('expected storage refusal')


def file_record(store, logical, payload, role='other_input', study=None, name=None):
    return F.BundleFile(logical_id=logical, original_name=name or logical+'.json', source_name='engine.py' if role=='source_file' else None,
        role=role, study_id=study, required=True, byte_count=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
        payload_ref=store.preview_payload(payload))


def raw_archive(store, payloads=None, *, run='run-a', revision='raw-v1', complete=False, full=False):
    if full:
        roles = ('plan','profile','registration_commitment','source_receipts','program_source',
                 'capture_source_manifest','source_file','prior_research')
        payloads = {role:('invented-'+role).encode() for role in roles}
        payloads.update(capture_a=b'candidate A losing result retained', capture_b=b'candidate B observed')
        records = tuple(sorted((file_record(store,k,v,role='capture' if k in ('capture_a','capture_b') else k,
                    study='study-a' if k=='capture_a' else 'study-b' if k=='capture_b' else None)
                    for k,v in payloads.items()), key=lambda r:r.logical_id))
    else:
        payloads = {'bad':b'{broken JSON', 'empty':b''} if payloads is None else payloads
        records = tuple(file_record(store,k,v,name='CON:bad' if k=='bad' else None) for k,v in sorted(payloads.items()))
    observations = tuple(F.InputObservation(observation_id='o-'+r.logical_id, original_name=r.original_name,
        source_name=r.source_name, role=r.role, study_id=r.study_id, required=r.required,
        status='COLLECTED', logical_id=r.logical_id) for r in records)
    manifest = F.RawArchiveManifest(schema_version=1, kind='RAW_ARCHIVED', run_id=run, revision_id=revision,
        attempt_id='attempt-a', parent_bundle_sha256=None, storage_policy_sha256=store.limits.policy_sha256,
        object_policy_sha256=store.limits.object_limits.policy_sha256,
        expected_candidates=('study-a','study-b') if full else None, inventory_complete=complete or full,
        observed_inputs=observations, files=records)
    return manifest, F.raw_archive_bytes(manifest, limits=store.limits.format_limits), payloads


def verified_bundle(store, raw, payloads):
    payloads = dict(payloads, evaluation=b'invented representation; not an issued evaluation')
    extra = file_record(store,'evaluation',payloads['evaluation'],role='evaluation_record')
    instant = datetime(2031,1,1,tzinfo=timezone.utc)
    manifest = F.VerifiedBundleManifest(schema_version=1, kind='VERIFIED_UNAPPROVED',run_id=raw.run_id,
        revision_id='verified-v1',attempt_id=raw.attempt_id,parent_bundle_sha256=None,
        storage_policy_sha256=store.limits.policy_sha256, object_policy_sha256=store.limits.object_limits.policy_sha256,
        input_archive_digest=F.raw_archive_digest(raw), plan_digest='1'*64,profile_digest='2'*64,
        rules_digest='3'*64,registry_digest='4'*64,source_digest='5'*64,family_digest='6'*64,
        receipt_audit_digest='7'*64,evaluator_revision='forward-paper-v1',source_kind_claim='synthetic',
        capture_start=instant,capture_end=instant+timedelta(minutes=1),evaluated_at=instant+timedelta(minutes=2),
        candidates=tuple(F.CandidateEvidence(study_id='study-'+c,protocol_digest=c*64,
            capture_logical_id='capture_'+c,result_digest=c*64) for c in ('a','b')),
        files=tuple(sorted((*raw.files,extra),key=lambda r:r.logical_id)))
    return manifest, F.verified_bundle_bytes(manifest), payloads


def chunk_path(store, value, backup=False):
    descriptor=E.preview_payload(value,limits=store.limits.object_limits).objects[0]
    return store._objects(backup).root/'objects'/(descriptor.sha256+'.blob')


def test_storage_provision_is_separate_from_operator_head_initialization():
    with fixture(provision=False,initialize=False) as e:
        assert files(e.base)=={}
        m,raw,p=raw_archive(e.store)
        refused(lambda:e.store.archive_raw(raw,p))
        assert files(e.base)=={}
        e.store.provision_empty()
        before=files(e.base)
        assert not e.store.head._dir.exists()
        refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_HEAD_REFUSED')
        assert files(e.base)==before
        e.store.head.initialize_reviewed_head(e.store.genesis_digest)
        result=e.store.archive_raw(raw,p)
        assert result.backup_verified and result.kind=='RAW_ARCHIVED'
        refused(e.store.provision_empty,'BUNDLE_STORE_ALREADY_PROVISIONED')


def test_malformed_and_empty_originals_round_trip_as_independent_copies_without_authority():
    with fixture() as e:
        m,raw,p=raw_archive(e.store)
        result=e.store.archive_raw(raw,p)
        restored=e.reopen().read_raw(result.bundle_digest)
        assert restored.manifest_bytes==raw and dict(restored.files)==p and restored.backup_verified
        assert restored.manifest.expected_candidates is None and not restored.manifest.inventory_complete
        try: restored.files['bad']=b'changed'
        except TypeError: pass
        else: raise AssertionError('mutable snapshot')
        a,b=chunk_path(e.store,p['bad']),chunk_path(e.store,p['bad'],True)
        assert a.read_bytes()==b.read_bytes()==p['bad'] and os.stat(a).st_ino!=os.stat(b).st_ino
        assert os.stat(a).st_nlink==os.stat(b).st_nlink==1
        assert not hasattr(result,'execution_ready') and not hasattr(result,'authenticated')
        refused(lambda:e.store.read_verified(result.bundle_digest),'BUNDLE_STORE_KIND_MISMATCH')


def test_verified_is_separate_immutable_derivation_retaining_every_input_and_candidate():
    with fixture() as e:
        m,raw,p=raw_archive(e.store,full=True)
        archived=e.store.archive_raw(raw,p)
        v,vraw,vp=verified_bundle(e.store,m,p)
        result=e.store.commit_verified(vraw,vp)
        assert result.bundle_digest!=archived.bundle_digest and result.kind=='VERIFIED_UNAPPROVED'
        read=e.reopen().read_verified(result.bundle_digest)
        assert dict(read.files)==vp and read.manifest.input_archive_digest==archived.bundle_digest
        assert e.store.read_raw(archived.bundle_digest).manifest_bytes==raw
        assert tuple(c.study_id for c in read.manifest.candidates)==('study-a','study-b')
        before=files(e.base)
        changed=replace(v,files=tuple(r for r in v.files if r.logical_id!='capture_b'),candidates=v.candidates[:1])
        refused(lambda:e.store.commit_verified(F.verified_bundle_bytes(changed),{k:x for k,x in vp.items() if k!='capture_b'}))
        assert files(e.base)==before
        _,reused_raw,reused_payloads=raw_archive(e.store,{'extra':b'raw cannot reuse verified revision'},revision='verified-v1')
        refused(lambda:e.store.archive_raw(reused_raw,reused_payloads),'BUNDLE_STORE_ID_REUSED')
        assert files(e.base)==before


def test_exact_retry_is_read_only_and_same_id_different_bytes_is_refused():
    with fixture() as e:
        m,raw,p=raw_archive(e.store)
        r=e.store.archive_raw(raw,p); before=files(e.base)
        assert e.reopen().archive_raw(raw,dict(p))==r and files(e.base)==before
        _,newraw,newp=raw_archive(e.store,{'bad':b'different'})
        refused(lambda:e.store.archive_raw(newraw,newp),'BUNDLE_STORE_ID_REUSED')
        assert files(e.base)==before
        _,next_raw,next_p=raw_archive(e.store,{'bad':b'different'},revision='raw-v2')
        assert e.store.archive_raw(next_raw,next_p).bundle_digest!=r.bundle_digest
        assert dict(e.store.read_raw(r.bundle_digest).files)==p


def test_backup_failure_retains_unbacked_primary_and_exact_retry_only_copies_backup():
    with fixture() as e:
        m,raw,p=raw_archive(e.store)
        real=E.EvidenceObjectStore.stage
        def failed(self,*args,**kw):
            if self.root.is_relative_to(e.roots.backup_root):
                raise E.EvidenceObjectError('EVIDENCE_OBJECT_IO_REFUSED')
            return real(self,*args,**kw)
        with patch.object(E.EvidenceObjectStore,'stage',failed):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_IO_REFUSED')
        digest=F.raw_archive_digest(m)
        assert not e.store.inspect(digest).backup_verified
        assert dict(e.store.read_raw(digest,require_backup=False).files)==p
        refused(lambda:e.store.read_raw(digest),'BUNDLE_STORE_BACKUP_REQUIRED')
        destinations=[]
        def watched(self,*args,**kw):
            destinations.append(self.root); return real(self,*args,**kw)
        with patch.object(E.EvidenceObjectStore,'stage',watched):
            assert e.reopen().archive_raw(raw,p).backup_verified
        assert destinations and all(x.is_relative_to(e.roots.backup_root) for x in destinations)
        assert e.store._catalog().sequence==2


def test_cas_response_loss_is_resolved_by_exact_catalog_query_without_duplicate_rows():
    for fail_on in (1,2):
        with fixture() as e:
            m,raw,p=raw_archive(e.store)
            real=e.store.head.compare_and_set; count=[0]
            def lost(old,new):
                value=real(old,new); count[0]+=1
                if count[0]==fail_on: raise RuntimeError('private response detail')
                return value
            with patch.object(e.store.head,'compare_and_set',lost):
                refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_IO_REFUSED')
            assert e.store._catalog().sequence==fail_on
            assert e.store.archive_raw(raw,p).backup_verified
            assert e.store._catalog().sequence==2


def test_catalog_ahead_of_head_is_preserved_and_never_adopted_or_truncated():
    with fixture() as e:
        m,raw,p=raw_archive(e.store)
        with patch.object(e.store.head,'compare_and_set',lambda old,new:False):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_HEAD_UPDATE_REFUSED')
        before=files(e.base)
        assert e.store.head.read()==e.store.genesis_digest and e.store._catalog().sequence==1
        refused(lambda:e.store.read_raw(F.raw_archive_digest(m)),'BUNDLE_STORE_HEAD_MISMATCH')
        refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_HEAD_MISMATCH')
        assert files(e.base)==before


def test_partial_final_and_pending_objects_never_become_a_published_archive():
    with fixture() as e:
        m,raw,p=raw_archive(e.store,{'original':b'complete original bytes'})
        real=E.EvidenceObjectStore._publish; done=[False]
        def interrupted(self,kind,value):
            if not done[0]:
                done[0]=True
                (self.root/'objects'/'pending.blob').write_bytes(value)
                (self.root/'objects'/(E._object_digest(kind,value)+'.blob')).write_bytes(value[:1])
                raise E.EvidenceObjectError('EVIDENCE_OBJECT_IO_REFUSED')
            return real(self,kind,value)
        with patch.object(E.EvidenceObjectStore,'_publish',interrupted):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_IO_REFUSED')
        before=files(e.base)
        assert e.store._catalog().sequence==0 and e.store.head.read()==e.store.genesis_digest
        refused(lambda:e.store.read_raw(F.raw_archive_digest(m)),'BUNDLE_STORE_NOT_PUBLISHED')
        refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_OBJECT_REFUSED')
        assert files(e.base)==before


def test_unrelated_object_corruption_does_not_block_sound_read_or_new_commit():
    with fixture() as e:
        a,ar,ap=raw_archive(e.store,{'a':b'only archive A owns these bytes'},run='run-a')
        b,br,bp=raw_archive(e.store,{'b':b'only archive B owns these bytes'},run='run-b')
        ra=e.store.archive_raw(ar,ap); rb=e.store.archive_raw(br,bp)
        path=chunk_path(e.store,ap['a']); path.write_bytes(b'X'*len(ap['a']))
        assert e.store.inspect(ra.bundle_digest).backup_verified  # historical metadata, not usable evidence
        refused(lambda:e.store.read_raw(ra.bundle_digest),'BUNDLE_STORE_OBJECT_REFUSED')
        assert dict(e.store.read_raw(rb.bundle_digest).files)==bp
        c,cr,cp=raw_archive(e.store,{'c':b'new unrelated archive C'},run='run-c')
        assert e.store.archive_raw(cr,cp).backup_verified
        assert dict(e.store.read_raw(rb.bundle_digest).files)==bp
        e.store.record_diagnostic(ra.bundle_digest,'SOURCE_OBJECT_DAMAGED')
        assert e.store._catalog().entries[ra.bundle_digest].diagnostics==('SOURCE_OBJECT_DAMAGED',)


def test_raw_dependency_and_backup_corruption_refuse_verified_use_without_global_hold():
    with fixture() as e:
        m,raw,p=raw_archive(e.store,full=True); a=e.store.archive_raw(raw,p)
        v,vr,vp=verified_bundle(e.store,m,p); verified=e.store.commit_verified(vr,vp)
        _,other,op=raw_archive(e.store,{'other':b'independent'},run='run-other'); r=e.store.archive_raw(other,op)
        chunk_path(e.store,raw,True).write_bytes(b'X'*min(len(raw),e.store.limits.object_limits.chunk_bytes))
        refused(lambda:e.store.read_verified(verified.bundle_digest),'BUNDLE_STORE_OBJECT_REFUSED')
        assert dict(e.store.read_raw(r.bundle_digest).files)==op
        assert e.store.read_raw(a.bundle_digest,require_backup=False).manifest.inventory_complete


def test_single_root_catalog_or_head_rollback_is_refused():
    for rollback in ('catalog','head'):
        with fixture() as e:
            old_catalog=(e.roots.sealed_root/'catalog.jsonl').read_bytes()
            old_head=(e.store.head._dir/'head.json').read_bytes()
            m,raw,p=raw_archive(e.store); result=e.store.archive_raw(raw,p)
            target=e.roots.sealed_root/'catalog.jsonl' if rollback=='catalog' else e.store.head._dir/'head.json'
            target.write_bytes(old_catalog if rollback=='catalog' else old_head)
            before=files(e.base)
            refused(lambda:e.store.read_raw(result.bundle_digest),'BUNDLE_STORE_HEAD_MISMATCH')
            assert files(e.base)==before


def test_roots_names_links_and_runtime_configuration_are_rejected_before_publication():
    with fixture() as e:
        refused(lambda:e.reopen(head_name='payload-objects'),'BUNDLE_STORE_HEAD_NAME_INVALID')
        refused(lambda:S.BundleRoots(sealed_root=e.roots.sealed_root,backup_root=e.roots.sealed_root/'child'),
                'BUNDLE_STORE_ROOT_OVERLAP')
        m,raw,p=raw_archive(e.store); before=files(e.base)
        with patch.object(e.store.head,'_chain',SimpleNamespace(seed=lambda d:0,successor=lambda a,b:1)):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_CONTEXT_CHANGED')
        assert files(e.base)==before
        (e.roots.sealed_root/'unexpected').write_bytes(b'x')
        refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_PATH_REFUSED')
    with fixture() as e:
        m,raw,p=raw_archive(e.store); lock=e.roots.sealed_root/'session.lock'
        os.link(lock,e.base/'lock-link')
        refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_FILE_REFUSED')
    with fixture() as e:
        alias=e.base/'alias'; alias.symlink_to(e.roots.backup_root,target_is_directory=True)
        refused(lambda:S.BundleStore(roots=S.BundleRoots(sealed_root=e.roots.sealed_root,backup_root=alias),
            limits=e.store.limits,head_name='head'),'BUNDLE_STORE_PATH_REFUSED')


def test_session_lock_or_root_replacement_during_stage_is_not_committed():
    for change in ('lock','root'):
        with fixture() as e:
            m,raw,p=raw_archive(e.store); real=E.EvidenceObjectStore.stage; changed=[False]
            def swap(self,*args,**kw):
                result=real(self,*args,**kw)
                if not changed[0]:
                    changed[0]=True
                    if change=='lock':
                        lock=e.roots.sealed_root/'session.lock'; lock.rename(e.base/'old-lock'); lock.write_bytes(b'0')
                    else:
                        old=e.base/'old-root'; e.roots.sealed_root.rename(old); shutil.copytree(old,e.roots.sealed_root)
                return result
            with patch.object(E.EvidenceObjectStore,'stage',swap):
                refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_STORAGE_CHANGED','BUNDLE_STORE_ROOT_CHANGED')
            assert (e.roots.sealed_root/'catalog.jsonl').read_bytes()==b''


def test_catalog_and_backup_quota_admission_happen_before_any_staging():
    policies=(limits(max_catalog_records=1),limits(max_catalog_bytes=1),
              limits(backup_budget=E.StoreBudget(max_bytes=1,max_objects=1)))
    for policy in policies:
        with fixture(storage_limits=policy) as e:
            _,raw,p=raw_archive(e.store); before=files(e.base)
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_RESOURCE_LIMIT')
            assert files(e.base)==before


def test_catalog_trailing_partial_or_unknown_row_is_never_read_as_complete():
    for suffix in (b'{',b'{}\n',b'\n'*129):
        with fixture() as e:
            _,raw,p=raw_archive(e.store); r=e.store.archive_raw(raw,p)
            with (e.roots.sealed_root/'catalog.jsonl').open('ab') as out:out.write(suffix)
            refused(lambda:e.store.read_raw(r.bundle_digest),'BUNDLE_STORE_CATALOG_TRUNCATED',
                    'BUNDLE_STORE_CATALOG_INVALID','BUNDLE_STORE_RESOURCE_LIMIT')


def test_diagnostics_are_idempotent_bounded_metadata_and_never_modify_originals():
    with fixture() as e:
        m,raw,p=raw_archive(e.store); r=e.store.archive_raw(raw,p)
        e.store.record_diagnostic(r.bundle_digest,'CAPTURE_ABORTED')
        before=files(e.base)
        e.store.record_diagnostic(r.bundle_digest,'CAPTURE_ABORTED')
        assert files(e.base)==before and dict(e.store.read_raw(r.bundle_digest).files)==p
        refused(lambda:e.store.record_diagnostic(r.bundle_digest,'private /path'), 'BUNDLE_STORE_DIAGNOSTIC_INVALID')


def test_temporary_copy_peak_is_enforced_at_minus_one_exact_and_plus_one():
    # One 4096-byte chunk needs both the temporary and exclusive final copies.
    # The complete final graph itself is smaller than that 8192-byte peak.
    for budget in (8191,8192,8193):
        with fixture(storage_limits=limits(primary_budget=E.StoreBudget(max_bytes=budget,max_objects=512))) as e:
            m,raw,p=raw_archive(e.store,{'original':b'm'*4096})
            before=files(e.base)
            if budget<8192:
                refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_RESOURCE_LIMIT')
                assert files(e.base)==before
            else:
                r=e.store.archive_raw(raw,p)
                assert dict(e.store.read_raw(r.bundle_digest).files)==p
                inventory=e.store._objects().inventory(budget=e.store.limits.primary_budget)
                assert inventory.byte_count<8192


def test_two_catalog_events_require_exact_record_capacity_without_partial_publication():
    for cap in (1,2,3):
        with fixture(storage_limits=limits(max_catalog_records=cap)) as e:
            _,raw,p=raw_archive(e.store)
            before=files(e.base)
            if cap==1:
                refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_RESOURCE_LIMIT')
                assert files(e.base)==before
            else:
                assert e.store.archive_raw(raw,p).backup_verified and e.store._catalog().sequence==2


def test_competing_os_writer_and_zero_lock_identity_never_stage():
    with fixture() as e:
        _,raw,p=raw_archive(e.store); before=files(e.base)
        with (e.roots.sealed_root/'session.lock').open('r+b') as handle:
            if os.name=='nt':
                import msvcrt
                handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            try: refused(lambda:e.reopen().archive_raw(raw,p),'BUNDLE_STORE_LOCKED')
            finally:
                if os.name=='nt': handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else: fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        assert files(e.base)==before
        real=S.os.lstat
        target=e.roots.sealed_root/'session.lock'
        def no_identity(path,*args,**kw):
            info=real(path,*args,**kw)
            if Path(path)==target:
                return SimpleNamespace(st_ino=0,st_dev=info.st_dev,st_mode=info.st_mode,st_nlink=info.st_nlink,
                    st_size=info.st_size,st_file_attributes=0)
            return info
        with patch.object(S.os,'lstat',no_identity):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_IDENTITY_UNAVAILABLE')
        assert files(e.base)==before


def test_backup_readback_damage_cannot_be_reported_as_backed_and_is_preserved():
    with fixture() as e:
        m,raw,p=raw_archive(e.store,{'input':b'exact-original'})
        real=e.store._graph; changed=[False]
        def damaged(entry,backup):
            if backup and not changed[0]:
                changed[0]=True
                chunk_path(e.store,p['input'],True).write_bytes(b'X'*len(p['input']))
            return real(entry,backup)
        with patch.object(e.store,'_graph',damaged):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_OBJECT_REFUSED')
        digest=F.raw_archive_digest(m)
        assert e.store._catalog().sequence==1 and not e.store.inspect(digest).backup_verified
        assert dict(e.store.read_raw(digest,require_backup=False).files)==p
        before=files(e.base)
        refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_OBJECT_REFUSED')
        assert files(e.base)==before


def test_successor_rechecks_backup_graph_after_catalog_append_before_head_advance():
    with fixture() as e:
        m,raw,p=raw_archive(e.store,{'input':b'original-between-checks'})
        real=e.store.head.compare_and_set; count=[0]; kept=[]
        def damage(old,new):
            count[0]+=1
            if count[0]==2:
                kept.append(old)
                chunk_path(e.store,p['input'],True).write_bytes(b'X'*len(p['input']))
            return real(old,new)
        with patch.object(e.store.head,'compare_and_set',damage):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_HEAD_REFUSED')
        assert kept and e.store.head.read()==kept[0] and e.store._catalog().sequence==2
        before=files(e.base)
        refused(lambda:e.store.read_raw(F.raw_archive_digest(m)),'BUNDLE_STORE_HEAD_MISMATCH')
        assert files(e.base)==before


def test_head_readback_response_loss_does_not_duplicate_a_successful_commit():
    with fixture() as e:
        m,raw,p=raw_archive(e.store); cas=e.store.head.compare_and_set; read=e.store.head.read
        fail=[False]
        def confirmed(old,new):
            value=cas(old,new);fail[0]=True;return value
        def lost():
            if fail[0]:fail[0]=False;raise RuntimeError('private readback detail')
            return read()
        with patch.object(e.store.head,'compare_and_set',confirmed),patch.object(e.store.head,'read',lost):
            refused(lambda:e.store.archive_raw(raw,p),'BUNDLE_STORE_IO_REFUSED')
        assert e.store._catalog().sequence==1
        assert e.store.archive_raw(raw,p).backup_verified and e.store._catalog().sequence==2


def test_empty_observed_inventory_is_archived_but_cannot_be_a_verified_research():
    with fixture() as e:
        m,raw,p=raw_archive(e.store,{})
        r=e.store.archive_raw(raw,p)
        restored=e.store.read_raw(r.bundle_digest)
        assert not restored.files and restored.manifest.expected_candidates is None
        assert restored.manifest.inventory_complete is False and r.backup_verified
        refused(lambda:e.store.read_verified(r.bundle_digest),'BUNDLE_STORE_KIND_MISMATCH')
