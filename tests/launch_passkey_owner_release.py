"""Actual disposable signed logs/anchors and installed-byte checks; no app imports."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tools.signer import sign as S
from tools.approval_broker import authority_contract as A, contract as C, owner_view as O, release as R
from tests.launch_passkey_contract import NOW, refused


def _pem(key):
    return key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)


def _environment(root, *, marker='target'):
    site=root/'lib'/'python3.13'/'site-packages'
    site.mkdir(parents=True)
    for name in ('cryptography','PyYAML'):
        directory=site/(name+'-1.0.dist-info'); directory.mkdir()
        (directory/'METADATA').write_text('Name: '+name+'\nVersion: 1.0\n')
        (directory/'RECORD').write_text(marker+','+name+',1\n')
    return root


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory(prefix='passkey-owner-disposable-') as temp:
        base=Path(temp); repo=base/'repo'; repo.mkdir()
        for path in ('core/compliance','core/odds','execution','execution_control','execution_orders',
                     'execution_accounts','execution_network','execution_launch','tools/owner'):
            (repo/path).mkdir(parents=True,exist_ok=True)
        (repo/'execution'/'sample.py').write_text('VALUE = 1\n')
        environment=_environment(base/'app-env')
        home=base/'owner'; home.mkdir(); (home/'snapshots').mkdir(); (home/'approved').mkdir()
        key=Ed25519PrivateKey.generate(); recovery=Ed25519PrivateKey.generate()
        public=key.public_key().public_bytes_raw(); pem=base/'owner.pem'; pem.write_bytes(_pem(key))
        code=R.target_deployment_code_hash(repo,environment)
        files=R._target_files(repo,environment)
        line,digest=S.entry_line(key,1,S.GENESIS_PREV,'code_approved',
            {'sha256':code,'files':[list(item) for item in files]},'2026-11-13T11:59:00Z')
        (home/'owner.jsonl').write_bytes(line)
        (home/'snapshots'/'initial.json').write_text(json.dumps({'head':[1,digest]}))
        roots=O.TrustRoots(initial_public_key_raw=public,initial_owner_head=A.Head(sequence=1,sha256=digest),
                           recovery_public_key_raw=recovery.public_key().public_bytes_raw())
        locations=O.OwnerLocations(app_repo=repo,app_environment=environment,compliance_root=home,public_key_path=pem)
        cell=[NOW]
        clock=lambda:cell[0]
        e=SimpleNamespace(base=base,repo=repo,environment=environment,home=home,key=key,public=public,pem=pem,
            roots=roots,locations=locations,cell=cell,clock=clock,code=code,files=files)
        e.reader=O.OwnerReader(locations=locations,roots=roots,clock=clock)
        yield e


def append(e,kind,data,*,key=None):
    raw=(e.home/'owner.jsonl').read_bytes()
    seq,digest=S._head(raw.splitlines(keepends=True))
    line,new=S.entry_line(key or e.key,seq+1,digest,kind,data,'2026-11-13T12:00:00Z')
    (e.home/'owner.jsonl').write_bytes(raw+line)
    return A.Head(sequence=seq+1,sha256=new)


def test_target_environment_record_bytes_never_use_ambient_broker_metadata():
    with fixture() as e, patch('importlib.metadata.distribution',side_effect=AssertionError('ambient forbidden')):
        assert R.target_deployment_code_hash(e.repo,e.environment)==e.code
        other=_environment(e.base/'other-env',marker='different-installed-record')
        assert R.target_deployment_code_hash(e.repo,other)!=e.code


def test_actual_target_d14_matches_existing_signer_in_its_own_real_environment():
    with fixture() as e:
        actual=Path(sys.prefix).resolve(strict=True)
        assert R.target_deployment_code_hash(e.repo,actual)==S.code_hash(e.repo)


def test_actual_log_signatures_initial_root_snapshot_and_current_code_are_observed():
    with fixture() as e:
        observed=e.reader.observe(retained=None)
        assert observed.evidence.head==e.roots.initial_owner_head
        assert observed.deployment_code_sha256==e.code and observed.deployment_problem is None
        assert observed.evidence.anchors==(e.roots.initial_owner_head,)
        O.verify_owner_evidence(observed.evidence,roots=e.roots,previous=None)
        assert observed.evidence.observed_at==observed.completed_at==NOW


def test_authentic_restrictive_new_head_survives_current_deployment_failure():
    with fixture() as e:
        old=e.reader.observe(retained=None)
        head=append(e,'limit_set',{'total_loss_floor_krw':1.0,'daily_loss_krw':1.0})
        shutil.rmtree(e.environment/'lib'/'python3.13'/'site-packages'/'PyYAML-1.0.dist-info')
        current=e.reader.observe(retained=old.evidence)
        assert current.evidence.head==head
        assert current.deployment_code_sha256 is None and current.deployment_problem=='PASSKEY_DEPLOYMENT_REFUSED'
        O.verify_owner_evidence(current.evidence,roots=e.roots,previous=old.evidence)


def test_log_only_rollback_is_refused_with_fresh_reader_and_retained_verified_prefix():
    with fixture() as e:
        first=(e.home/'owner.jsonl').read_bytes()
        append(e,'limit_set',{'total_loss_floor_krw':1.0,'daily_loss_krw':1.0})
        observed=e.reader.observe(retained=None)
        (e.home/'owner.jsonl').write_bytes(first)
        fresh=O.OwnerReader(locations=e.locations,roots=e.roots,clock=e.clock)
        refused(lambda:fresh.observe(retained=observed.evidence),'PASSKEY_OWNER_PREFIX_INVALID')


def test_actual_signed_rotation_requires_initial_root_chain_and_matching_current_pem():
    with fixture() as e:
        old=e.reader.observe(retained=None)
        replacement=Ed25519PrivateKey.generate()
        import base64
        append(e,'key_rotated',{'old_pubkey_b64':base64.b64encode(e.public).decode(),
            'new_pubkey_b64':base64.b64encode(replacement.public_key().public_bytes_raw()).decode()})
        refused(lambda:e.reader.observe(retained=old.evidence),'PASSKEY_OWNER_KEY_CHANGED')
        e.pem.write_bytes(_pem(replacement))
        observed=e.reader.observe(retained=old.evidence)
        assert observed.evidence.public_key_raw==replacement.public_key().public_bytes_raw()
        O.verify_owner_evidence(observed.evidence,roots=e.roots,previous=old.evidence)
        other=O.TrustRoots(initial_public_key_raw=replacement.public_key().public_bytes_raw(),
            initial_owner_head=e.roots.initial_owner_head,recovery_public_key_raw=e.roots.recovery_public_key_raw)
        refused(lambda:O.verify_owner_evidence(observed.evidence,roots=other,previous=None))


def test_external_anchor_missing_changed_or_research_unknown_entry_is_not_silently_dropped():
    with fixture() as e:
        first=e.reader.observe(retained=None)
        (e.home/'snapshots'/'initial.json').unlink()
        refused(lambda:e.reader.observe(retained=first.evidence),'PASSKEY_OWNER_PREFIX_INVALID')
        (e.home/'snapshots'/'initial.json').write_text(json.dumps({'head':[1,'f'*64]}))
        refused(lambda:e.reader.observe(retained=None),'PASSKEY_OWNER_PREFIX_INVALID')
        (e.home/'snapshots'/'initial.json').unlink()
        folder=e.home/'approved'/'research-attestations';folder.mkdir()
        (folder/'hidden-anchor').write_bytes(b'{}')
        refused(lambda:e.reader.observe(retained=None),'PASSKEY_OWNER_ANCHOR_INVALID')


def test_initial_key_is_not_replaced_by_public_key_claim_in_forged_evidence():
    with fixture() as e:
        genuine=e.reader.observe(retained=None)
        key=Ed25519PrivateKey.generate()
        line,digest=S.entry_line(key,1,S.GENESIS_PREV,'session_armed',{'session_id':'synthetic'},'2026-11-13T12:00:00Z')
        forged=replace(genuine.evidence,log_bytes=line,public_key_raw=key.public_key().public_bytes_raw(),
            head=A.Head(sequence=1,sha256=digest),anchors=())
        refused(lambda:O.verify_owner_evidence(forged,roots=e.roots,previous=None),'PASSKEY_OWNER_LOG_INVALID')


def test_owner_read_final_clock_rollback_and_inflight_log_change_are_refused():
    with fixture() as e:
        values=iter((NOW,NOW-timedelta(microseconds=1)))
        reader=O.OwnerReader(locations=e.locations,roots=e.roots,clock=lambda:next(values))
        refused(lambda:reader.observe(retained=None),'PASSKEY_CLOCK_ROLLBACK')
        actual=O.target_deployment_code_hash
        def changed(*args):
            digest=actual(*args)
            append(e,'limit_set',{'total_loss_floor_krw':1.0,'daily_loss_krw':1.0})
            return digest
        with patch.object(O,'target_deployment_code_hash',side_effect=changed):
            refused(lambda:e.reader.observe(retained=None),'PASSKEY_OWNER_CHANGED')


def test_mutating_frozen_operator_roots_cannot_repin_reader():
    with fixture() as e:
        object.__setattr__(e.roots,'initial_public_key_raw',b'x'*32)
        refused(lambda:e.reader.observe(retained=None),'PASSKEY_OWNER_LOCATION_INVALID')


def test_log_row_limit_precedes_signer_structure_and_line_materialization():
    with fixture() as e:
        (e.home/'owner.jsonl').write_bytes(b'\n'*32769)
        with patch.object(S,'_head',side_effect=AssertionError('must not parse')):
            refused(lambda:e.reader.observe(retained=None),'PASSKEY_RESOURCE_LIMIT')


def test_rp_actual_whole_inventory_and_original_bytes_are_verified():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); (root/'index.html').write_bytes(b'<!doctype html><title>synthetic RP assets only</title>')
        manifest=R._release_inventory(root,role='RP',dependency_roots=())
        R.verify_release(root,manifest,dependency_roots=())
        (root/'index.html').write_bytes(b'changed')
        refused(lambda:R.verify_release(root,manifest,dependency_roots=()),'PASSKEY_RELEASE_CHANGED')


def test_manifest_cannot_omit_a_real_file_or_substitute_tiny_broker_package():
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); (root/'tiny.txt').write_bytes(b'x')
        manifest=R._release_inventory(root,role='RP',dependency_roots=())
        (root/'extra.txt').write_bytes(b'extra')
        refused(lambda:R.verify_release(root,manifest,dependency_roots=()),'PASSKEY_RELEASE_CHANGED')
        refused(lambda:R._release_inventory(root,role='BROKER',dependency_roots=()),'PASSKEY_RELEASE_INCOMPLETE')


def test_source_and_target_environment_symlinks_hardlinks_and_duplicate_dist_refuse():
    with fixture() as e:
        directory=e.environment/'lib'/'python3.13'/'site-packages'
        duplicate=directory/'cryptography-2.0.dist-info'
        shutil.copytree(directory/'cryptography-1.0.dist-info',duplicate)
        (duplicate/'METADATA').write_bytes(b'Name: cryptography\nVersion: 2.0\n')
        refused(lambda:R.target_deployment_code_hash(e.repo,e.environment),'PASSKEY_DEPLOYMENT_REFUSED')
        shutil.rmtree(duplicate)
        path=e.repo/'execution'/'sample.py'; path.unlink(); path.symlink_to(e.pem)
        refused(lambda:R.target_deployment_code_hash(e.repo,e.environment))


def test_bounded_source_bytes_feed_ast_without_a_second_unbounded_path_read():
    with fixture() as e, patch.object(S,'_repo_imports',side_effect=AssertionError('unbounded reread forbidden')):
        assert R.target_deployment_code_hash(e.repo,e.environment)==e.code


def test_authentic_changed_code_head_is_returned_before_original_grant_eligibility_refusal():
    from tools.approval_broker import bootstrap as B
    from tests.launch_passkey_bootstrap import proposal,config
    with fixture() as e:
        observation=e.reader.observe(retained=None)
        checkpoint=A.OwnerCheckpoint(fingerprint=S.fingerprint(e.public),code_sha256=e.code,
            owner_head=observation.evidence.head,observed_at=NOW)
        # Inert release builder inputs only; this test authenticates owner/grant,
        # not a release installation or operational channel.
        assets=e.base/'assets';assets.mkdir();(assets/'x.txt').write_bytes(b'x')
        rp=R._release_inventory(assets,role='RP',dependency_roots=())
        body=B.build_grant_body(proposal(),config=config(),broker_release=replace(rp,role='BROKER'),
            rp_release=rp,owner=checkpoint,recovery_fingerprint=S.fingerprint(e.roots.recovery_public_key_raw),
            issued_at=NOW,expires_at=NOW+timedelta(minutes=5))
        grant=A.GrantDocument(body_bytes=body,signature=e.key.sign(A.grant_signing_bytes(body)))
        B.verify_grant_document(grant,signer_public_key_raw=e.public)
        assert O.require_grant_eligibility(grant,observation,at=NOW).owner_head==observation.evidence.head
        (e.repo/'execution'/'sample.py').write_text('VALUE = 2\n')
        current_files=R._target_files(e.repo,e.environment)
        code=R.target_deployment_code_hash(e.repo,e.environment)
        head=append(e,'code_approved',{'sha256':code,'files':[list(row) for row in current_files]})
        changed=e.reader.observe(retained=observation.evidence)
        assert changed.evidence.head==head and changed.deployment_code_sha256==code
        refused(lambda:O.require_grant_eligibility(grant,changed,at=NOW),'PASSKEY_DEPLOYMENT_CHANGED')
        refused(lambda:O.require_grant_eligibility(grant,observation,at=NOW+timedelta(seconds=31)),
                'PASSKEY_OWNER_STALE')


@contextmanager
def dependency_files():
    """Synthetic local installation only, exercising bytes; no engine acceptance."""
    import base64
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);site=root/'lib';site.mkdir();dist=site/'example-1.dist-info';dist.mkdir()
        (dist/'METADATA').write_bytes(b'Name: example\nVersion: 1\n')
        payload=site/'example.py';payload.write_bytes(b'VALUE = 1\n')
        rows=[]
        for path in (dist/'METADATA',payload):
            raw=path.read_bytes()
            digest=base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode()
            rows.append(path.relative_to(site).as_posix()+',sha256='+digest+','+str(len(raw)))
        rows.append('example-1.dist-info/RECORD,,')
        (dist/'RECORD').write_text('\n'.join(rows)+'\n')
        with patch.object(R.sys,'prefix',str(root)),patch.object(R.sysconfig,'get_path',return_value=str(site)):
            yield site,dist,payload


def test_dependency_payload_changed_after_first_read_is_rejected_even_when_record_unchanged():
    with dependency_files() as (site,dist,payload):
        actual=R._read; seen=[]
        def changing(path,*args,**kwargs):
            result=actual(path,*args,**kwargs)
            if path==dist/'RECORD':
                seen.append(True)
                if len(seen)==2:
                    payload.write_bytes(b'VALUE = 2\n')
            return result
        original=(dist/'RECORD').read_bytes()
        with patch.object(R,'_read',side_effect=changing):
            refused(lambda:R._dependency_inventory((site,)),'PASSKEY_RELEASE_CHANGED')
        assert (dist/'RECORD').read_bytes()==original


def test_metadata_size_admission_precedes_actual_content_read():
    with dependency_files() as (site,dist,payload):
        with (dist/'METADATA').open('r+b') as stream:
            stream.truncate(2*1024*1024+1)
        with patch.object(R,'_read',side_effect=AssertionError('oversize must refuse before reading')):
            refused(lambda:R._distributions(site),'PASSKEY_RESOURCE_LIMIT')


def test_actual_dependency_record_and_all_file_bytes_determine_artifact_commitment():
    with dependency_files() as (site,dist,payload):
        result=R._dependency_inventory((site,))
        assert len(result)==1 and result[0].distribution=='example'
        rows=[{'name':path.relative_to(site).as_posix(),'byte_count':len(path.read_bytes()),
               'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for path in (payload,dist/'METADATA',dist/'RECORD')]
        assert result[0].artifact_sha256==A.record_digest('dependency-artifacts',C.encoded(sorted(rows,key=lambda x:x['name'])))
        (site/'unrecorded.py').write_bytes(b'UNREVIEWED = True\n')
        refused(lambda:R._dependency_inventory((site,)),'PASSKEY_RELEASE_INVENTORY_CHANGED')


def test_shared_runtime_library_is_closed_and_missing_configured_file_refuses():
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp); library=root/'libpython3.13.so'
        actual=R._shared_runtime_library()
        if actual is not None:
            shutil.copyfile(actual,library)
        else:
            # Static-host negative fixture; never claimed to be executable code.
            library.write_bytes(b'not a verified runtime')
        values={'Py_ENABLE_SHARED':1,'LIBDIR':str(root),'LDLIBRARY':library.name,'PYTHONFRAMEWORK':''}
        with patch.object(R.os,'name','posix'),patch.object(R.sysconfig,'get_config_var',side_effect=values.get):
            pinned=R._shared_runtime_library()
            original=R._read(pinned)
            library.write_bytes(b'changed actual bytes')
            assert R._read(pinned)!=original
            library.unlink()
            refused(R._shared_runtime_library,'PASSKEY_RUNTIME_UNSUPPORTED')


def test_target_d14_ignores_unrelated_metadata_but_broker_inventory_still_checks_it():
    with fixture() as e:
        site=e.environment/'lib'/'python3.13'/'site-packages'
        unrelated=site/'aenum-1.0.dist-info';unrelated.mkdir()
        (unrelated/'METADATA').write_bytes(b'Name: aenum\nVersion: 1.0\n')
        original=R._read
        def refuse_unrelated(path,*args,**kwargs):
            if path == unrelated/'METADATA':
                raise C.PasskeyError('PASSKEY_RELEASE_READ_REFUSED')
            return original(path,*args,**kwargs)
        with patch.object(R,'_read',side_effect=refuse_unrelated):
            assert R.target_deployment_code_hash(e.repo,e.environment)==e.code
            refused(lambda:R._distributions(site),'PASSKEY_RELEASE_READ_REFUSED')


def test_required_distribution_metadata_name_and_version_must_match_selected_directory():
    with fixture() as e:
        path=e.environment/'lib'/'python3.13'/'site-packages'/'cryptography-1.0.dist-info'/'METADATA'
        for raw in (b'Name: aenum\nVersion: 1.0\n',b'Name: cryptography\nVersion: 2.0\n'):
            path.write_bytes(raw)
            refused(lambda:R.target_deployment_code_hash(e.repo,e.environment),'PASSKEY_DEPLOYMENT_REFUSED')


def test_required_metadata_hardlinks_are_still_refused_with_fixed_diagnostic():
    import os
    with fixture() as e:
        path=e.environment/'lib'/'python3.13'/'site-packages'/'cryptography-1.0.dist-info'/'METADATA'
        os.link(path,e.base/'cache-metadata')
        assert path.stat().st_nlink == 2
        refused(lambda:R.target_deployment_code_hash(e.repo,e.environment),'PASSKEY_RELEASE_READ_REFUSED')


def test_public_owner_and_release_boundaries_sanitize_legacy_runtime_errors():
    with fixture() as e:
        with patch.object(S,'_bundle_read',side_effect=RuntimeError('PRIVATE_PATH_MARKER')):
            refused(lambda:R._read(e.pem),'PASSKEY_RELEASE_READ_REFUSED')
            refused(lambda:e.reader.observe(retained=None),'PASSKEY_OWNER_READ_REFUSED')
        with patch.object(R,'_target_files',side_effect=RuntimeError('PRIVATE_PATH_MARKER')):
            refused(lambda:R.target_deployment_code_hash(e.repo,e.environment),'PASSKEY_DEPLOYMENT_REFUSED')
        def broken_clock():
            raise RuntimeError('PRIVATE_CLOCK_MARKER')
        reader=O.OwnerReader(locations=e.locations,roots=e.roots,clock=broken_clock)
        refused(lambda:reader.observe(retained=None),'PASSKEY_CLOCK_INVALID')
        assets=e.base/'assets';assets.mkdir();(assets/'x.txt').write_bytes(b'x')
        manifest=R._release_inventory(assets,role='RP',dependency_roots=())
        with patch.object(R,'_release_inventory',side_effect=RuntimeError('PRIVATE_PATH_MARKER')):
            refused(lambda:R.verify_release(assets,manifest,dependency_roots=()),'PASSKEY_RELEASE_READ_REFUSED')
