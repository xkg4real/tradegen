"""Actual disposable recovery CLI stores and signatures; no real credential/API.

Only CLI wall-clock reads are replaced in positive integration cases. Actual
owner loading, signatures, route registration, backup recovery, attempt journals
and incident holds remain real. Historical outcomes never become current use.
"""
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution_launch import bundle_attestation as A
from execution_launch import research_incident_store as IJ
from execution_launch import research_recovery_cli as C
from execution_launch import research_recovery_attempts as F
from execution_launch import research_recovery_store as J
from execution_launch.baseline_head import BaselineHead
from tools.owner import research_recovery as OP

AT=datetime(2031,1,7,tzinfo=timezone.utc)


def invoke(module,args):
    stream=StringIO()
    with redirect_stdout(stream):
        code=module.main(args)
    text=stream.getvalue()
    return code,json.loads(text),text


def no_operations(result):
    for name in ('source_authenticated','research_selection_ready','current_use_eligible','execution_ready',
                 'automatic_operational_recovery_supported','quarantine_released','quarantine_release_supported',
                 'current_operational_eligibility_assessed','network_delivery_performed'):
        assert result[name] is False,(name,result)
    assert result['record_semantics']=='historical_observation_not_current_eligibility'


def refused(module,args,code=None):
    status,result,text=invoke(module,args)
    assert status==2 and result['status']=='REFUSED',result
    no_operations(result)
    if code is not None:
        assert result['reasons']==[code],result
    return result,text


def attempt_args(config,limits):
    return ['--attempt-root',str(config['root']),'--attempt-backup-root',str(config['backup_root']),
        '--attempt-head-root',str(config['head_root']),'--attempt-head-name',config['head_name'],
        '--attempt-limits',str(limits)]


def incident_args(config,limits):
    return ['--incident-root',str(config['root']),'--incident-backup-root',str(config['backup_root']),
        '--incident-head-root',str(config['head_root']),'--incident-head-name',config['head_name'],
        '--incident-limits',str(limits)]


def basic(command='inspect'):
    return [command,'--attempt-root','attempts','--attempt-backup-root','backup',
        '--attempt-head-root','heads','--attempt-head-name','synthetic','--attempt-limits','limits.json']


def action_args(command='route-register'):
    result=basic(command)+['--incident-root','incidents','--incident-backup-root','incident-backup',
        '--incident-head-root','incident-heads','--incident-head-name','synthetic','--incident-limits','incidents.json',
        '--source-root','source','--source-backup-root','source-backup','--source-limits','source.json',
        '--destination-root','destination','--destination-backup-root','destination-backup',
        '--destination-head-name','target','--destination-limits','destination.json',
        '--archive-attestation','original.json']
    if command=='route-register':
        result+=['--digest','a'*64,'--source-head-name','source-head']
    else:
        result+=['--route-id','a'*64,'--incident-id','b'*64]
    return result


def files(root):
    return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}


@contextmanager
def empty_configuration():
    with tempfile.TemporaryDirectory(prefix='tradegen_recovery_cli_') as temporary:
        base=Path(temporary)
        roots=tuple(base/name for name in ('attempts','backups','heads'))
        for root in roots:root.mkdir()
        limits=J.RecoveryStoreLimits(format_limits=F.RecoveryAttemptLimits(),
                                    max_journal_bytes=32*1024*1024,max_records=1024)
        config=dict(root=roots[0],backup_root=roots[1],head_root=roots[2],head_name='recovery',limits=limits)
        path=base/'limits.json';path.write_bytes(J.limits_bytes(limits))
        yield SimpleNamespace(base=base,config=config,path=path,cli=attempt_args(config,path),
                              store=J.RecoveryAttemptStore(**config))


@contextmanager
def wall_clock(e):
    class FixedDateTime:
        @classmethod
        def now(cls,zone=None):
            return e.cell[0].astimezone(zone or timezone.utc)
    with patch.object(C,'datetime',FixedDateTime):
        yield


def configuration(e):
    """Write only explicit input files outside all actual journal/object roots."""
    folder=e.root/'cli-inputs';folder.mkdir()
    attempt_limits=folder/'attempts.json';attempt_limits.write_bytes(J.limits_bytes(e.attempts.limits))
    incident_limits=folder/'incidents.json';incident_limits.write_bytes(IJ.limits_bytes(e.incident_store.limits))
    source_limits=folder/'source.json';source_limits.write_text(json.dumps(asdict(e.store.limits)),encoding='utf-8')
    destination_limits=folder/'destination.json'
    destination_limits.write_text(json.dumps(asdict(e.destination.limits)),encoding='utf-8')
    document=folder/'original-attestation.json';document.write_bytes(e.document)
    attempts=attempt_args(e.attempt_args,attempt_limits)
    common=attempts+incident_args(e.incident_args,incident_limits)+[
        '--source-root',str(e.source.roots.sealed_root),'--source-backup-root',str(e.source.roots.backup_root),
        '--source-limits',str(source_limits),'--destination-root',str(e.destination.roots.sealed_root),
        '--destination-backup-root',str(e.destination.roots.backup_root),
        '--destination-head-name',e.destination._head_name,'--destination-limits',str(destination_limits),
        '--archive-attestation',str(document)]
    return SimpleNamespace(folder=folder,attempts=attempts,common=common,document=document,
        register=['route-register',*common,'--digest',e.digest,'--source-head-name',e.store._head_name],
        run=lambda route,incident:['run-once',*common,'--route-id',route,'--incident-id',incident])


def test_exact_cli_options_exclude_authority_delivery_signing_release_and_runtime_provision():
    cases=[[],['provision'],basic()+['--now',AT.isoformat()],basic()+['--provider','caller'],
        basic()+['--key','owner.pem'],basic()+['--approved','true'],basic()+['--revoked','false'],
        basic()+['--success','true'],basic()+['--outcome','delivered'],basic()+['--send','telegram']]
    cases += [basic(command) for command in ('daemon','delivery','record-delivery','release','restore','arm','sign','adopt-head')]
    with patch.object(C,'read_file') as reader,patch.object(C,'CurrentOwnerAuthority') as authority:
        for args in cases:refused(C,args)
        assert not reader.called and not authority.called


def test_missing_duplicate_unknown_and_mistyped_options_refuse_before_any_file():
    args=basic()
    cases=[False,'inspect',[1],args[:-1],args+args[1:3],args+['--unknown','x'],args+['--route-id','a'*64]]
    cases += [args[:i]+args[i+2:] for i in range(1,len(args),2)]
    with patch.object(C,'read_file') as reader:
        for value in cases:refused(C,value)
        assert not reader.called


def test_action_configuration_requires_original_document_and_registration_only_source_head():
    with patch.object(C,'read_file') as reader:
        for command in ('route-register','run-once'):
            refused(C,basic(command),'RECOVERY_CLI_ARGUMENTS_REQUIRED')
            args=action_args(command)
            index=args.index('--archive-attestation')
            refused(C,args[:index]+args[index+2:],'RECOVERY_CLI_ARGUMENTS_REQUIRED')
        refused(C,action_args('run-once')+['--source-head-name','unused'],'RECOVERY_CLI_ARGUMENTS_INVALID')
        for name in ('--route-id','--incident-id'):
            args=action_args('run-once');args[args.index(name)+1]='invalid'
            refused(C,args,'RECOVERY_CLI_IDENTIFIER_INVALID')
        assert not reader.called
    assert C._arguments(action_args())[0]=='route-register'
    assert C._arguments(action_args('run-once'))[0]=='run-once'


def test_operator_only_provision_requires_explicit_options_and_redacts_generic_errors():
    with patch.object(OP,'open_attempt_store') as opened:
        for args in ([],basic('inspect'),basic('provision')[:-2],basic('provision')+['--now',AT.isoformat()]):
            refused(OP,args)
        assert not opened.called
    for error in (OSError('PRIVATE_ROOT'),ValueError('PRIVATE_ROOT')):
        with patch.object(OP,'open_attempt_store',side_effect=error):
            _,text=refused(OP,basic('provision'),'RECOVERY_CLI_INPUT_REFUSED')
            assert 'PRIVATE_ROOT' not in text


def test_actual_empty_operator_provision_status_and_pending_require_no_owner_or_signature():
    with empty_configuration() as e:
        with patch.object(C,'CurrentOwnerAuthority') as authority,patch.object(owner,'load_context') as loader:
            code,result,text=invoke(OP,['provision',*e.cli])
            assert code==0 and result['status']=='EMPTY_RECOVERY_STORE_PROVISIONED',result
            no_operations(result)
            assert e.store.head.read()==result['genesis_digest']==e.store.inspect().head
            for command in ('inspect','list-pending'):
                code,result,text=invoke(C,[command,*e.cli])
                assert code==0,result
                no_operations(result)
                assert result['attempt_sequence']==0
                if command=='inspect':
                    assert result['routes']==[] and result['attempts']==[] and result['pending_count']==0
                else:
                    assert result['pending_notifications']==[]
                assert str(e.base) not in text
            assert not authority.called and not loader.called


def test_existing_and_partial_operator_records_are_preserved_without_head_adoption():
    for complete in (False,True):
        with empty_configuration() as e:
            if complete:OP.provision_recovery_attempt_store(e.store)
            else:e.store.provision_empty()
            before=files(e.base)
            refused(OP,['provision',*e.cli])
            assert files(e.base)==before


def test_runtime_unprepared_or_missing_head_never_provisions_or_repairs():
    with empty_configuration() as e:
        before=files(e.base)
        with patch.object(J.RecoveryAttemptStore,'provision_empty',side_effect=AssertionError('runtime provision')), \
                patch.object(BaselineHead,'initialize_reviewed_head',side_effect=AssertionError('head adoption')):
            refused(C,['inspect',*e.cli])
        assert files(e.base)==before
        OP.provision_recovery_attempt_store(e.store)
        (e.store.head._dir/'head.json').unlink()
        before=files(e.base)
        refused(C,['inspect',*e.cli])
        assert files(e.base)==before


def test_malformed_oversized_limits_and_signature_refuse_without_store_mutation():
    with empty_configuration() as e:
        for raw in (b'{}',b'{"schema":1,"schema":1}',b'x'*65537):
            e.path.write_bytes(raw);before=files(e.base)
            refused(C,['inspect',*e.cli]);assert files(e.base)==before
        for raw in (b'{}',b'{invalid',b'x'*(A.MAX_DOCUMENT_BYTES+1)):
            document=e.base/'signature.json';document.write_bytes(raw)
            args=action_args();args[args.index('--archive-attestation')+1]=str(document)
            with patch.object(C,'open_attempt_store',side_effect=AssertionError('invalid signature admitted')):
                refused(C,args)


def test_runtime_diagnostics_and_interruption_never_echo_private_values_or_operation_true():
    for error in (OSError('PRIVATE_PATH'),ValueError('PRIVATE_PATH'),RuntimeError('/private/account')):
        with patch.object(C,'open_attempt_store',side_effect=error):
            _,text=refused(C,basic(),'RECOVERY_CLI_INPUT_REFUSED')
            assert 'PRIVATE_PATH' not in text and '/private/account' not in text
    with patch.object(C,'open_attempt_store',side_effect=KeyboardInterrupt):
        refused(C,basic(),'RECOVERY_CLI_STOPPED')


def register_cli(e,args):
    with wall_clock(e):
        code,result,text=invoke(C,args.register)
    assert code==0 and result['status']=='RECOVERY_ROUTE_REGISTERED',result
    no_operations(result)
    assert str(e.root) not in text and 'signature_b64' not in text
    return result


def test_actual_route_registration_binds_original_signature_without_copy_or_operational_approval():
    from tests import launch_research_recovery_integration as V
    with V.fixture(registered=False) as e:
        args=configuration(e)
        original=files(e.store.roots.sealed_root)
        target=(files(e.destination.roots.sealed_root),files(e.destination.roots.backup_root))
        before_incidents=e.incident_store.inspect()
        result=register_cli(e,args)
        snapshot=e.attempts.inspect()
        assert snapshot.sequence==1 and len(snapshot.state.routes)==1 and not snapshot.state.attempts
        assert snapshot.state.routes[0].route_id==result['route_id']
        assert snapshot.state.routes[0].attestation_sha256==A.attestation_document_digest(e.document)
        assert e.incident_store.inspect()==before_incidents
        assert files(e.store.roots.sealed_root)==original
        assert (files(e.destination.roots.sealed_root),files(e.destination.roots.backup_root))==target


def test_actual_run_restores_failed_raw_exact_signature_artifact_and_keeps_incident_hold():
    from tests import launch_research_recovery_integration as V
    with V.fixture(registered=False) as e:
        args=configuration(e);route=register_cli(e,args)
        incident=V.damage(e)
        original=files(e.store.roots.sealed_root);incident_state=e.incident_store.inspect()
        with wall_clock(e):
            code,result,text=invoke(C,args.run(route['route_id'],incident))
        assert code==0 and result['phase']=='EXACT_ARCHIVE_RESTORED',result
        no_operations(result)
        restored=e.destination.read_raw(e.digest,require_backup=True)
        assert restored.manifest_bytes==e.raw_bytes and dict(restored.files)==e.payloads
        assert restored.files['bad']==b'{broken JSON' and restored.files['empty']==b''
        artifact=e.destination.read_raw(result['recovery_artifact_digest'],require_backup=True)
        assert artifact.files['attestation']==e.document
        assert e.incident_store.inspect()==incident_state and files(e.store.roots.sealed_root)==original
        state=e.attempts.inspect().state
        assert len(state.attempts)==1 and len(state.pending_notifications)==1
        notice=state.pending_notifications[0]
        assert notice.quarantine=='REMAINS' and notice.current_use=='NOT_GRANTED'
        assert str(e.root) not in text and 'signature_b64' not in text


def test_missing_original_primary_uses_signed_backup_configuration_without_source_store_recreation():
    from tests import launch_research_recovery_integration as V
    with V.fixture(registered=False) as e:
        args=configuration(e);route=register_cli(e,args);incident=V.damage(e)
        shutil.rmtree(e.source.roots.sealed_root)
        original_open=C.open_explicit_store
        calls=[]
        def destination_only(root,*remaining):
            assert Path(root)==e.destination.roots.sealed_root,'source BundleStore must not be reconstructed'
            calls.append(root)
            return original_open(root,*remaining)
        with wall_clock(e),patch.object(C,'open_explicit_store',side_effect=destination_only):
            code,result,_=invoke(C,args.run(route['route_id'],incident))
        assert code==0 and result['phase']=='EXACT_ARCHIVE_RESTORED',result
        no_operations(result)
        assert len(calls)==1 and not e.source.roots.sealed_root.exists()
        assert e.destination.read_raw(e.digest,require_backup=True).files['bad']==b'{broken JSON'


def test_completed_records_and_pending_results_remain_historical_after_destination_damage():
    from tests import launch_research_recovery_integration as V
    from tests.launch_research_bundle_store import chunk_path
    with V.fixture(registered=False) as e:
        args=configuration(e);route=register_cli(e,args);incident=V.damage(e)
        with wall_clock(e):
            code,completed,_=invoke(C,args.run(route['route_id'],incident))
        assert code==0 and completed['phase']=='EXACT_ARCHIVE_RESTORED',completed
        # A historical ledger entry must not be relabelled as a new actual graph
        # observation after the previously restored signature artifact is damaged.
        path=chunk_path(e.destination,e.document)
        raw=path.read_bytes();path.write_bytes(bytes([raw[0]^1])+raw[1:])
        before=e.attempts.inspect()
        with patch.object(owner,'load_context',side_effect=AssertionError('no fresh authority for historical status')):
            for command in ('inspect','list-pending'):
                code,result,text=invoke(C,[command,*args.attempts])
                assert code==0,result
                no_operations(result)
                if command=='inspect':
                    assert result['attempts'][0]['phase']=='EXACT_ARCHIVE_RESTORED'
                else:
                    assert len(result['pending_notifications'])==1
                    assert result['pending_notifications'][0]['current_use']=='NOT_GRANTED'
                assert str(e.root) not in text
            with wall_clock(e):
                code,repeated,_=invoke(C,args.run(route['route_id'],incident))
            assert code==0 and repeated['phase']=='EXACT_ARCHIVE_RESTORED',repeated
            no_operations(repeated)
            assert repeated['observed_at']==completed['observed_at']
        assert e.attempts.inspect()==before


def test_missing_or_different_original_signature_cannot_start_copy_or_create_success_outbox():
    from tests import launch_research_recovery_integration as V
    from tests.launch_bundle_auth import document
    from datetime import timedelta
    with V.fixture(registered=False) as e:
        args=configuration(e);route=register_cli(e,args);incident=V.damage(e)
        before=e.attempts.inspect()
        target=(files(e.destination.roots.sealed_root),files(e.destination.roots.backup_root))
        args.document.unlink()
        with wall_clock(e):refused(C,args.run(route['route_id'],incident))
        assert e.attempts.inspect()==before
        original=A.parse_attestation_document(e.document)['body']['request']
        # An actual temporary-key signature on a different valid request is not
        # the exact original document committed by this route.
        changed=A.request_from_manifests(e.raw_bytes,None,requested_at=e.cell[0],
            expires_at=e.cell[0]+timedelta(minutes=30),deployment_code_hash=original['deployment_code_hash'])
        args.document.write_bytes(document(changed,e.signer.key,issued_at=e.cell[0]))
        with wall_clock(e):refused(C,args.run(route['route_id'],incident))
        assert e.attempts.inspect()==before
        assert (files(e.destination.roots.sealed_root),files(e.destination.roots.backup_root))==target
