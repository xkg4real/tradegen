"""Actual temporary incident CLI stores; no transmission or live authority.

Positive selection cases retain actual archive/evaluator/signature/history and
owner boundaries. Only their external wall clock is fixed. All file damage and
operator provisioning use disposable directories; no user home or real keys.
"""
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
from datetime import datetime,timezone
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from core.compliance import owner
from execution_launch import research_incident_cli as C
from execution_launch import research_incident_store as J
from execution_launch import research_incidents as F
from tests import launch_sealed_study_cli as SEALED_CLI
from tools.owner import research_incidents as OP

AT=datetime(2031,1,6,tzinfo=timezone.utc)


def invoke(module,args):
    stream=StringIO()
    with redirect_stdout(stream):code=module.main(args)
    text=stream.getvalue()
    return code,json.loads(text),text


def false_operations(result):
    assert all(result[name] is False for name in
               ('execution_ready','current_operational_use','automatic_recovery_supported'))


def refused(module,args,code=None):
    status,result,text=invoke(module,args)
    assert status==2 and result['status']=='REFUSED',result
    false_operations(result)
    if code is not None:assert result['reasons']==[code],result
    return result,text


def incident_arguments(configuration,limits_path):
    return ['--incident-root',str(configuration['root']),
        '--incident-backup-root',str(configuration['backup_root']),
        '--incident-head-root',str(configuration['head_root']),
        '--incident-head-name',configuration['head_name'],'--incident-limits',str(limits_path)]


def basic_args(command='inspect'):
    return [command,'--incident-root','incident','--incident-backup-root','backup',
        '--incident-head-root','heads','--incident-head-name','synthetic','--incident-limits','limits.json']


@contextmanager
def empty_configuration():
    with tempfile.TemporaryDirectory(prefix='tradegen_incident_cli_') as temp:
        base=Path(temp)
        roots=tuple(base/name for name in ('incident','backup','heads'))
        for root in roots:root.mkdir()
        limits=J.IncidentStoreLimits(format_limits=F.IncidentLimits(),max_journal_bytes=32*1024*1024,max_records=1024)
        arguments=dict(root=roots[0],backup_root=roots[1],head_root=roots[2],head_name='synthetic',limits=limits)
        limits_path=base/'limits.json';limits_path.write_bytes(J.limits_bytes(limits))
        yield SimpleNamespace(base=base,arguments=arguments,limits_path=limits_path,
            cli=incident_arguments(arguments,limits_path),store=J.IncidentStore(**arguments))


def tree(root):
    return {path.relative_to(root).as_posix():path.read_bytes() for path in root.rglob('*') if path.is_file()}


def test_exact_runtime_arguments_exclude_delivery_recovery_authority_and_provision():
    bad=[[],['provision'],basic_args()+['--now',AT.isoformat()],basic_args()+['--key','key.pem'],
         basic_args()+['--provider','caller'],basic_args()+['--quarantined','false'],
         basic_args()+['--send','telegram'],basic_args()+['--outcome','delivered']]
    for command in ('delivery','record-delivery','release','restore','adopt-head','resume','arm'):
        bad.append(basic_args(command))
    with patch.object(C,'read_file') as reader,patch.object(C,'CurrentOwnerAuthority') as authority:
        for args in bad:refused(C,args)
        assert not reader.called and not authority.called


def test_missing_duplicate_mistyped_and_unknown_incident_options_refuse_before_files():
    original=basic_args()
    cases=[None,False,'inspect',[1],original[:-1],original+original[1:3],original+['--other','value'],
           original+['--source-review','source.json']]
    for index in range(1,len(original),2):cases.append(original[:index]+original[index+2:])
    with patch.object(C,'read_file') as reader:
        for args in cases:refused(C,args)
        assert not reader.called


def test_registration_and_selection_configuration_requires_explicit_bundle_and_history_roots():
    for command in ('register','check','incident-aware-select'):
        with patch.object(C,'read_file') as reader,patch.object(C,'CurrentOwnerAuthority') as authority:
            refused(C,basic_args(command),'INCIDENT_CLI_ARGUMENTS_REQUIRED')
            assert not reader.called and not authority.called
    assert C._arguments(basic_args())[0]=='inspect'
    assert C._arguments(basic_args('list-pending'))[0]=='list-pending'


def test_operator_requires_only_explicit_provision_configuration_and_redacts_generic_errors():
    with patch.object(OP,'open_incident_store') as opened:
        for args in ([],['inspect'],basic_args('provision')+['--now',AT.isoformat()],basic_args('provision')[:-2]):
            refused(OP,args)
        assert not opened.called
    for error in (OSError('UPPERCASE_PRIVATE'),ValueError('UPPERCASE_PRIVATE')):
        with patch.object(OP,'open_incident_store',side_effect=error):
            _,text=refused(OP,basic_args('provision'),'INCIDENT_CLI_INPUT_REFUSED')
            assert 'UPPERCASE_PRIVATE' not in text


def test_actual_operator_provisions_empty_independent_roots_then_status_and_pending_need_no_owner():
    with empty_configuration() as e:
        with patch.object(C,'CurrentOwnerAuthority') as authority,patch.object(owner,'load_context') as loader:
            code,result,text=invoke(OP,['provision',*e.cli])
            assert code==0 and result['status']=='EMPTY_INCIDENT_STORE_PROVISIONED',result
            false_operations(result)
            assert e.store.inspect().sequence==0 and e.store.head.read()==result['genesis_digest']
            code,status,_=invoke(C,['inspect',*e.cli])
            assert code==0 and status['registrations']==[] and status['incident_count']==0
            code,pending,_=invoke(C,['list-pending',*e.cli])
            assert code==0 and pending['pending_notifications']==[]
            assert pending['network_delivery_performed'] is False
            false_operations(status);false_operations(pending)
            assert not authority.called and not loader.called and str(e.base) not in text


def test_existing_or_interrupted_operator_storage_is_preserved_and_never_adopted():
    for completed in (False,True):
        with empty_configuration() as e:
            if completed:OP.provision_incident_store(e.store)
            else:e.store.provision_empty()
            before=tree(e.base)
            refused(OP,['provision',*e.cli])
            assert tree(e.base)==before
            if not completed:
                refused(C,['inspect',*e.cli])
                assert not list(e.arguments['head_root'].rglob('head.json'))
                assert tree(e.base)==before


def test_runtime_empty_or_missing_head_never_initializes_storage():
    with empty_configuration() as e:
        before=tree(e.base)
        refused(C,['inspect',*e.cli])
        assert tree(e.base)==before
        OP.provision_incident_store(e.store)
        heads=list(e.arguments['head_root'].rglob('head.json'));assert len(heads)==1
        heads[0].unlink()
        before=tree(e.base)
        refused(C,['inspect',*e.cli])
        assert tree(e.base)==before and not heads[0].exists()


def test_malformed_oversized_and_private_limits_refuse_without_any_store_creation():
    with empty_configuration() as e:
        original=e.limits_path.read_bytes()
        for raw in (b'{}',b'{"max_records":1,"max_records":2}',b'x'*65537):
            e.limits_path.write_bytes(raw)
            with patch.object(C,'IncidentStore') as constructor:
                refused(C,['inspect',*e.cli])
                assert not constructor.called
        e.limits_path.write_bytes(original)
        args=e.cli.copy();args[-1]=str(e.base/'.env'/'limits.json')
        with patch.object(C,'IncidentStore') as constructor:
            refused(C,['inspect',*args],'WORKFLOW_FILE_REFUSED')
            assert not constructor.called


def actual_arguments(e):
    limits=e.base/'incident-limits-cli.json';limits.write_bytes(J.limits_bytes(e.incident_store.limits))
    incident=incident_arguments(e.incident_args,limits)
    bundle_limits=e.base/'bundle-limits-cli.json';bundle_limits.write_text(json.dumps(asdict(e.store.limits)))
    bundle=['--sealed-root',str(e.store.roots.sealed_root),'--backup-root',str(e.store.roots.backup_root),
        '--head-name','bundle-head','--limits',str(bundle_limits),'--digest',e.digest]
    return incident,bundle


def test_actual_cli_registration_and_check_are_graph_facts_without_owner_or_research_approval():
    from tests import launch_research_incident_integration as REAL
    with REAL.fixture(count=60) as e:
        incident,bundle=actual_arguments(e)
        with patch.object(C,'datetime',SEALED_CLI.fixture_clock(e)), \
                patch.object(C,'CurrentOwnerAuthority') as authority,patch.object(owner,'load_context') as loader:
            code,result,text=invoke(C,['register',*incident,*bundle])
            assert code==0 and result['status']=='TARGET_REGISTERED' and result['dependency_count']>0,result
            false_operations(result)
            code,checked,_=invoke(C,['check',*incident,*bundle])
            assert code==0 and checked['registered'] and checked['graph_checked'] and not checked['held'],checked
            assert not authority.called and not loader.called
            false_operations(checked)
            assert str(e.base) not in text
        assert e.incident_store.inspect().sequence==1


def test_actual_unregistered_target_is_not_enrolled_by_check():
    from tests import launch_research_incident_integration as REAL
    with REAL.fixture(count=60) as e:
        incident,bundle=actual_arguments(e)
        with patch.object(C,'datetime',SEALED_CLI.fixture_clock(e)):
            refused(C,['check',*incident,*bundle],'INCIDENT_TARGET_UNREGISTERED')
        assert e.incident_store.inspect().sequence==0


def test_actual_damage_creates_durable_hold_and_pending_message_without_transmission_or_auto_release():
    from tests import launch_research_incident_integration as REAL
    with REAL.fixture(count=60) as e:
        incident,bundle=actual_arguments(e)
        with patch.object(C,'datetime',SEALED_CLI.fixture_clock(e)), \
                patch.object(C,'CurrentOwnerAuthority') as authority,patch.object(owner,'load_context') as loader:
            code,_,_=invoke(C,['register',*incident,*bundle]);assert code==0
            damaged,original=REAL.damage_payload(e,e.report.logical_id)
            code,held,_=invoke(C,['check',*incident,*bundle])
            assert code==0 and held['held'] and held['incident_ids'],held
            assert damaged.read_bytes()!=original
            code,pending,text=invoke(C,['list-pending',*incident])
            assert code==0 and len(pending['pending_notifications'])==1,pending
            assert pending['network_delivery_performed'] is False
            assert pending['pending_notifications'][0]['incident_id'] in held['incident_ids']
            false_operations(held);false_operations(pending)
            assert not authority.called and not loader.called and str(e.base) not in text
            damaged.write_bytes(original)  # Exact temporary repair does not release the durable hold.
            code,still,_=invoke(C,['check',*incident,*bundle])
            assert code==0 and still['held'] and still['graph_checked'] is False
            assert still['incident_ids']==held['incident_ids']
        assert len(e.reopen_incidents().inspect().state.incidents)==1


def test_actual_incident_aware_cli_selection_keeps_current_use_and_execution_separate():
    from tests import launch_research_incident_integration as REAL
    with REAL.fixture() as e:
        incident,bundle=actual_arguments(e)
        selection,_=SEALED_CLI.sealed_arguments(e)
        with patch.object(C,'datetime',SEALED_CLI.fixture_clock(e)):
            code,_,_=invoke(C,['register',*incident,*bundle]);assert code==0
            code,result,text=invoke(C,['incident-aware-select',*incident,*selection[1:]])
        assert code==0 and result['status']=='SELECTED',result
        assert result['selection_assessment']['research_selection_ready']
        assert result['selection_assessment']['selected_implementation_authenticated']
        assert result['incident_context_sha256']==e.incident_store.context_sha256
        false_operations(result);false_operations(result['selection_assessment'])
        assert str(e.base) not in text and str(e.home) not in text


def test_actual_held_cli_selection_refuses_before_evaluator_or_owner_loading():
    from tests import launch_research_incident_integration as REAL
    from execution_launch import strategy
    with REAL.fixture(count=60) as e:
        incident,bundle=actual_arguments(e)
        selection,_=SEALED_CLI.sealed_arguments(e)
        with patch.object(C,'datetime',SEALED_CLI.fixture_clock(e)):
            code,_,_=invoke(C,['register',*incident,*bundle]);assert code==0
            REAL.damage_payload(e,e.report.logical_id)
            code,held,_=invoke(C,['check',*incident,*bundle]);assert code==0 and held['held']
            with patch.object(strategy,'evaluate_capture_json') as evaluator,patch.object(owner,'load_context') as loader:
                refused(C,['incident-aware-select',*incident,*selection[1:]],'INCIDENT_SELECTION_QUARANTINED')
                assert not evaluator.called and not loader.called


def test_runtime_errors_are_sanitized_and_interruption_never_creates_approval():
    for error in (OSError('UPPERCASE_PRIVATE'),ValueError('UPPERCASE_PRIVATE'),RuntimeError('private path')):
        with patch.object(C,'read_file',side_effect=error):
            _,text=refused(C,basic_args(),'INCIDENT_CLI_INPUT_REFUSED')
            assert 'UPPERCASE_PRIVATE' not in text and 'private path' not in text
    with patch.object(C,'read_file',side_effect=KeyboardInterrupt):
        refused(C,basic_args(),'INCIDENT_CLI_STOPPED')
