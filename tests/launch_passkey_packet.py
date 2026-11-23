"""Actual temporary packet reads via the standalone checker; no source authority.

The RAW metadata is deliberately synthetic, including object references. Tests
bind actual files and preserve incomplete evidence; app BundleStore integration
is exercised separately by the complete engine fixture.
"""
from dataclasses import replace
from datetime import timedelta
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools.signer import sign as S
from tools.approval_broker import authority_contract as A
from tools.approval_broker import contract as C
from tools.approval_broker import packet as P
from tests.launch_passkey_contract import NOW, refused
from tests.launch_passkey_authority_contract import request


def make_packet(directory,*,payloads=None,count=None):
    if payloads is None:
        payloads={'con':b'{ malformed original\n','empty':b''} if count is None else {
            'f%04d'%i:('raw input %d'%i).encode() for i in range(count)}
    files=[];observations=[]
    for identifier,raw in sorted(payloads.items()):
        digest=hashlib.sha256(raw).hexdigest()
        ref=None if not raw else S._bf_PayloadReference(schema=1,manifest_sha256='a'*64,manifest_bytes=2,
            payload_sha256=digest,payload_bytes=len(raw),policy_sha256='b'*64)
        metadata=dict(original_name='original-'+identifier+'.json',source_name=None,role='other_input',study_id=None,required=False)
        files.append(S._bf_BundleFile(logical_id=identifier,byte_count=len(raw),sha256=digest,payload_ref=ref,**metadata))
        observations.append(S._bf_InputObservation(observation_id=identifier,status='COLLECTED',logical_id=identifier,**metadata))
    raw=S._bf_RawArchiveManifest(schema_version=1,kind='RAW_ARCHIVED',run_id='synthetic-raw',revision_id='v1',attempt_id='one',
        parent_bundle_sha256=None,storage_policy_sha256='c'*64,object_policy_sha256='b'*64,expected_candidates=None,
        inventory_complete=False,observed_inputs=tuple(observations),files=tuple(files))
    body=S._ba_request_from_manifests(S._bf_raw_archive_bytes(raw),None,requested_at=NOW,
        expires_at=NOW+timedelta(hours=1),deployment_code_hash='d'*64)
    directory.mkdir();(directory/'payloads').mkdir()
    encoded=S._ba_archive_request_bytes(body);(directory/'request.json').write_bytes(encoded)
    for identifier,data in payloads.items():
        (directory/'payloads'/S._ba_payload_filename(identifier)).write_bytes(data)
    return body,encoded


def test_actual_complete_file_inventory_includes_failed_empty_and_safe_generated_names():
    with TemporaryDirectory() as temp:
        directory=Path(temp)/'packet';body,raw=make_packet(directory)
        observed=P.read_packet(directory)
        assert observed.archive_request_bytes==raw
        assert tuple(f.name for f in observed.files)==('payloads/p-con.bin','payloads/p-empty.bin','request.json')
        assert observed.files[1].byte_count==0
        assert observed.packet_sha256==A.record_digest('packet',A.canonical([A.file_document(f) for f in observed.files]))
        target=A.decode(P.archive_target(observed))
        assert target['archive_request']==body and target['scope']=='archive_manifest_identity'
        assert target['archive_request']['bundle_kind']=='RAW_ARCHIVED'
        assert not target['archive_request']['raw_manifest']['inventory_complete']
        assert target['packet_sha256']==observed.packet_sha256
        assert P.recheck_packet(directory,observed)==observed
        assert 'malformed' not in repr(observed) and str(directory) not in repr(observed)


def test_packet_identity_rebinds_changed_actual_bytes_even_with_consistent_new_manifest():
    with TemporaryDirectory() as temp:
        first=Path(temp)/'first';second=Path(temp)/'second'
        make_packet(first,payloads={'data':b'original'});make_packet(second,payloads={'data':b'changed'})
        a,b=P.read_packet(first),P.read_packet(second)
        assert a.packet_sha256!=b.packet_sha256
        refused(lambda:P.recheck_packet(second,a),'PASSKEY_TARGET_CHANGED')
        assert P.recheck_packet(first,a)==a


def test_actual_missing_extra_and_changed_payloads_refuse_full_graph():
    for change in ('missing','extra','changed','requestextra'):
        with TemporaryDirectory() as temp:
            directory=Path(temp)/'packet';make_packet(directory)
            path=directory/'payloads'/'p-con.bin'
            if change=='missing':path.unlink()
            elif change=='extra':(directory/'payloads'/'extra.bin').write_bytes(b'not declared')
            elif change=='changed':path.write_bytes(b'changed')
            else:(directory/'undeclared.json').write_bytes(b'{}')
            refused(lambda:P.read_packet(directory),'PASSKEY_PACKET_INVALID')


def test_actual_duplicate_json_request_and_trailing_data_refuse_before_target():
    for suffix in (b'{}',b',"schema_version":1}'):
        with TemporaryDirectory() as temp:
            directory=Path(temp)/'packet';_,raw=make_packet(directory)
            malformed=raw+suffix if suffix==b'{}' else raw[:-1]+suffix
            (directory/'request.json').write_bytes(malformed)
            refused(lambda:P.read_packet(directory),'PASSKEY_PACKET_INVALID')


def test_actual_symlink_file_and_root_alias_refuse_without_following():
    with TemporaryDirectory() as temp:
        directory=Path(temp)/'packet';make_packet(directory)
        path=directory/'payloads'/'p-con.bin';saved=Path(temp)/'saved';path.rename(saved);path.symlink_to(saved)
        refused(lambda:P.read_packet(directory),'PASSKEY_PACKET_INVALID')
        path.unlink();saved.rename(path)
        alias=Path(temp)/'alias';alias.symlink_to(directory,target_is_directory=True)
        refused(lambda:P.read_packet(alias),'PASSKEY_PACKET_INVALID')


def test_changed_file_between_actual_passes_is_not_a_cached_snapshot():
    with TemporaryDirectory() as temp:
        directory=Path(temp)/'packet';make_packet(directory)
        actual=S._bundle_packet;calls=[]
        def changed(*args,**kwargs):
            result=actual(*args,**kwargs);calls.append(1)
            if len(calls)==1:(directory/'payloads'/'p-con.bin').write_bytes(b'changed after read')
            return result
        with patch.object(S,'_bundle_packet',side_effect=changed):
            refused(lambda:P.read_packet(directory),'PASSKEY_PACKET_INVALID')
        assert len(calls)==1  # second real checker fails before returning


def test_constructed_snapshot_cannot_hide_or_rehash_missing_file_and_no_app_imports():
    with TemporaryDirectory() as temp:
        directory=Path(temp)/'packet';make_packet(directory);s=P.read_packet(directory)
        missing=s.files[1:]
        digest=A.record_digest('packet',A.canonical([A.file_document(f) for f in missing]))
        refused(lambda:replace(s,files=missing,packet_sha256=digest),'PASSKEY_TARGET_CHANGED')
        changed=replace(s.files[0],sha256='f'*64)
        refused(lambda:replace(s,files=(changed,*s.files[1:])), 'PASSKEY_TARGET_CHANGED')
        fake=replace(s);object.__delattr__(fake,'files')
        refused(lambda:P.archive_target(fake))
    import ast
    for filename in ('packet.py','authority_contract.py'):
        tree=ast.parse((Path(P.__file__).parent/filename).read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                assert not (node.module or '').startswith(('execution_launch','core.','execution_accounts'))
            elif isinstance(node,ast.Import):
                assert all(not n.name.startswith(('execution_launch','core.','execution_accounts')) for n in node.names)


def test_actual_large_archive_packet_crosses_foundation_limits_without_loosening_them():
    with TemporaryDirectory() as temp:
        directory=Path(temp)/'packet';body,raw=make_packet(directory,count=1200)
        assert len(raw)>90000
        snapshot=P.read_packet(directory)
        assert len(snapshot.files)==1201
        target=A.decode(P.archive_target(snapshot));asked=request('ARCHIVE_CONFIRM',target)
        assert A.parse_request(A.request_bytes(asked))==asked
        assert asked.body['target']['archive_request']['payload_files']==body['payload_files']
        refused(lambda:C.decode(asked.raw))
        for change in ('payload_files','scope'):
            tampered=asked.body
            if change=='scope':tampered['target']['scope']='strategy_selection'
            else:tampered['target']['archive_request']['payload_files'].pop()
            refused(lambda:A.parse_request(A.canonical(tampered)))


def test_read_rechecks_exact_regular_file_identity_not_only_equal_hash():
    with TemporaryDirectory() as temp:
        directory=Path(temp)/'packet';make_packet(directory)
        actual=S._bundle_packet;calls=[]
        def swapped(*args,**kwargs):
            result=actual(*args,**kwargs);calls.append(1)
            if len(calls)==1:
                source=directory/'payloads'/'p-con.bin';old=directory/'payloads'/'old'
                source.rename(old);source.write_bytes(old.read_bytes());old.unlink()
            return result
        with patch.object(S,'_bundle_packet',side_effect=swapped):
            refused(lambda:P.read_packet(directory),'PASSKEY_TARGET_CHANGED')
        assert len(calls)==2
