"""Actual recovered selection CLI; disposable owners, invented market data.

Positive cases use the real recovery controller, signatures, full evaluator,
factory/history and destination stores. Only CLI wall-clock reads are replaced.
No real account, private key, network, message or order is used.
"""
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import bundle_attestation as A
from execution_launch import research_incident_monitor as M, research_incidents as I
from execution_launch import research_incident_store as IJ, research_recovery_store as RJ
from execution_launch import research_recovery_cli as C
from execution_launch.profile import profile_body
from execution_launch.strategy import _plain
from tests import launch_research_recovery_cli as OLD
from tests import launch_recovered_selection as REAL
from tests import launch_sealed_study_cli as SEALED


def basic():
    args=['select-recovered']
    for name in sorted(C.ATTEMPT_OPTIONS|C.INCIDENT_OPTIONS|C._DESTINATION|C._SELECTION):
        args+=['--'+name,'a'*64 if name in ('digest','route-id','incident-id') else 'fixture-'+name]
    return args


def replace_option(args,name,value):
    result=list(args);result[result.index('--'+name)+1]=value
    return result


def invoke(args):
    stream=StringIO()
    with redirect_stdout(stream):
        status=C.main(args)
    text=stream.getvalue()
    return status,json.loads(text),text


def inert(value):
    assert value['scope']=='recovered_research_selection'
    for field in ('current_operational_use','execution_ready',
                  'automatic_operational_recovery_supported','network_delivery_performed'):
        assert value[field] is False,(field,value)
    assert 'quarantine_released' not in value


def refused(args,expected=None):
    code,result,text=invoke(args)
    assert code==2 and result['status']=='REFUSED',result
    inert(result)
    assert result['release_record_id'] is None and result['research_selection_ready'] is False
    if expected is not None:
        assert result['reasons']==[expected],result
    return result,text


def configuration(e):
    """Explicit files outside all retained graph/journal/head roots."""
    folder=e.base/'recovered-cli-inputs';folder.mkdir()
    paths={name:folder/(name+'.json') for name in ('attempts','incidents','destination','archive','profile','window')}
    paths['attempts'].write_bytes(RJ.limits_bytes(e.attempts.limits))
    paths['incidents'].write_bytes(IJ.limits_bytes(e.incident_store.limits))
    paths['destination'].write_text(json.dumps(asdict(e.destination.limits)),encoding='utf-8')
    paths['archive'].write_bytes(e.archive)
    paths['profile'].write_text(json.dumps(profile_body(e.profile)),encoding='utf-8')
    paths['window'].write_text(json.dumps(_plain(e.window)),encoding='utf-8')
    args=['select-recovered',*OLD.attempt_args(e.attempt_args,paths['attempts']),
        *OLD.incident_args(e.incident_args,paths['incidents']),
        '--destination-root',str(e.destination.roots.sealed_root),
        '--destination-backup-root',str(e.destination.roots.backup_root),
        '--destination-head-name',e.destination._head_name,'--destination-limits',str(paths['destination']),
        '--digest',e.digest,'--route-id',e.route.route_id,'--incident-id',e.incident_id,
        '--archive-attestation',str(paths['archive']),'--profile',str(paths['profile']),
        '--window',str(paths['window']),'--head-root',str(e.history_head_root)]
    for index,(identifier,document) in enumerate(sorted(e.reviews.items())):
        path=folder/('source-review-'+str(index)+'.json');path.write_bytes(document)
        args+=['--source-review',str(path),'--audit',identifier+'='+e.audits[identifier]]
    return args,paths


def test_new_command_has_exact_destination_only_options_and_preserves_legacy_parsing():
    command,args=C._arguments(basic())
    assert command=='select-recovered' and args['source-review']==args['audit']==[]
    _,rich=C._arguments(basic()+['--source-review','r1.json','--source-review','r2.json',
        '--audit','Study1=report','--history-storage','history.json'])
    assert rich['source-review']==['r1.json','r2.json'] and rich['audit']==['Study1=report']
    for original in (OLD.basic(),OLD.action_args(),OLD.action_args('run-once')):
        command,args=C._arguments(original)
        assert command==original[0] and 'source-review' not in args


def test_source_authority_clock_keys_and_activation_options_refuse_before_io():
    with patch.object(C,'_selection_inputs') as inputs,patch.object(C,'open_attempt_store') as opened, \
         patch.object(C,'CurrentOwnerAuthority') as authority:
        for name in ('source-root','source-backup-root','source-head-name','source-limits',
                     'now','clock','provider','context','key','password','approved','revoked',
                     'activate','arm','send','outcome','provision','release'):
            refused(basic()+['--'+name,'private-input'])
        assert not inputs.called and not opened.called and not authority.called


def test_missing_duplicate_unknown_identifiers_and_excess_repeats_refuse_before_io():
    original=basic()
    cases=[original[:-2],original+original[1:3],original+['--unknown','value'],
           original+['--profile','duplicate.json'],original+['--audit','nul\x00value'],
           original+sum((['--source-review','r.json'] for _ in range(129)),[])]
    cases += [replace_option(original,name,bad) for name in ('digest','route-id','incident-id')
              for bad in ('','A'*64,'a'*63,'../private')]
    with patch.object(C,'_selection_inputs') as inputs,patch.object(C,'open_attempt_store') as opened:
        for args in cases:refused(args)
        assert not inputs.called and not opened.called


def test_help_describes_scoped_recording_without_owner_or_file_io():
    stream=StringIO()
    with patch.object(C,'_selection_inputs') as inputs,patch.object(C,'open_attempt_store') as opened, \
         patch.object(C,'CurrentOwnerAuthority') as authority,redirect_stdout(stream):
        assert C.main(['--help'])==0
    assert 'select-recovered' in stream.getvalue() and 'requires no source options' in stream.getvalue()
    assert not inputs.called and not opened.called and not authority.called


def test_actual_bounded_archive_loader_refuses_bad_or_oversized_original_before_stores():
    with tempfile.TemporaryDirectory(prefix='tradegen_recovered_cli_inputs_') as temporary:
        path=Path(temporary)/'archive.json'
        args=replace_option(basic(),'archive-attestation',str(path))
        with patch.object(C,'open_attempt_store') as opened,patch.object(C,'CurrentOwnerAuthority') as authority:
            for raw in (b'{malformed',b' '* (A.MAX_DOCUMENT_BYTES+1)):
                path.write_bytes(raw)
                refused(args)
            assert not opened.called and not authority.called


def test_duplicate_or_path_audit_mapping_is_rejected_before_original_read():
    with patch.object(C,'open_attempt_store') as opened,patch.object(C,'CurrentOwnerAuthority') as authority:
        for extra in (['--audit','Study1=report','--audit','Study1=other'],
                      ['--audit','Study1=../private'],['--audit','not-a-mapping']):
            refused(basic()+extra)
        assert not opened.called and not authority.called


def test_private_exception_text_and_interrupt_never_become_success_or_output():
    for failure in (OSError('PRIVATE_FILE_VALUE'),RuntimeError('/private/example'),
                    ValueError('PRIVATE_GENERIC_VALUE'),KeyboardInterrupt()):
        with patch.object(C,'_selection_inputs',side_effect=failure):
            result,text=refused(basic())
        assert 'PRIVATE_' not in text and '/private/' not in text
        assert result['reasons']==['RECOVERY_CLI_STOPPED' if isinstance(failure,KeyboardInterrupt)
                                  else 'RECOVERY_CLI_INPUT_REFUSED']


def test_untrusted_display_object_is_not_serialized_as_research_success():
    try:
        C._selection_output(SimpleNamespace(scope='recovered_research_selection',execution_ready=True),{})
    except C.RecoveryCLIError as exc:
        assert str(exc)=='RECOVERY_CLI_RESULT_INVALID'
    else:
        raise AssertionError('untrusted display object was serialized')


def test_actual_fixed_and_carry_cli_use_one_real_clock_provider_without_source_or_signing():
    for carry in (False,True):
        with REAL.fixture(carry=carry,source_removed=True) as e:
            args,paths=configuration(e)
            original_document=paths['archive'].read_bytes()
            attempts_before=e.attempts.inspect()
            with patch.object(C,'datetime',SEALED.fixture_clock(e)), \
                 patch.object(C,'CurrentOwnerAuthority',wraps=C.CurrentOwnerAuthority) as providers, \
                 patch.object(C,'authenticate_recovered_study_selection',
                              wraps=C.authenticate_recovered_study_selection) as consumer, \
                 patch.object(C,'SignedBackupSource',side_effect=AssertionError('source reopened')), \
                 patch.object(C,'run_recovery_once',side_effect=AssertionError('recovery repeated')):
                status,result,text=invoke(args)
            assert status==0 and result['status']=='SELECTED',result
            inert(result)
            assert result['research_selection_ready'] and result['release_record_id']
            assert result['selected_study_id'] in e.reviews
            assert providers.call_count==consumer.call_count==1
            invocation=consumer.call_args.kwargs
            assert invocation['clock'] is providers.call_args.kwargs['clock']
            assert invocation['authority_provider']._clock is invocation['clock']
            assert invocation['archive_attestation']==original_document==e.archive
            assert 'source' not in invocation and e.attempts.inspect()==attempts_before
            held=M.check_target(e.incident_store,e.destination,e.digest,clock=e.clock)
            assert held.held and held.incident_ids==(e.incident_id,)
            assert len(I.research_route_releases(e.incident_store.inspect().state))==1
            assert str(e.base) not in text and 'signature_b64' not in text and 'profile' not in result
            assert not e.store.roots.sealed_root.exists() and not e.store.roots.backup_root.exists()


def test_actual_no_qualified_research_returns_no_release_and_preserves_hold():
    with REAL.fixture(count=60,source_removed=True) as e:
        args,_=configuration(e)
        assert not e.reviews
        with patch.object(C,'datetime',SEALED.fixture_clock(e)):
            status,result,_=invoke(args)
        assert status==0 and result['status']=='NO_QUALIFIED_MARKET',result
        inert(result)
        assert not result['research_selection_ready'] and result['release_record_id'] is None
        assert not I.research_route_releases(e.incident_store.inspect().state)
        assert M.check_target(e.incident_store,e.destination,e.digest,clock=e.clock).held


def test_actual_repeat_rechecks_and_reuses_record_then_signed_revocation_refuses():
    from tests import launch_sealed_study_review as SR
    with REAL.fixture(source_removed=True) as e:
        args,_=configuration(e)
        with patch.object(C,'datetime',SEALED.fixture_clock(e)):
            status,first,_=invoke(args)
            assert status==0 and first['status']=='SELECTED',first
            status,again,_=invoke(args)
            assert status==0 and again['release_record_id']==first['release_record_id'],again
            identifier=next(iter(e.reviews))
            SR.revoke(e,e.reviews[identifier],e.bodies[identifier]['purpose'])
            refused(args,'REVIEW_ATTESTATION_REVOKED')
        assert len(I.research_route_releases(e.incident_store.inspect().state))==1
        assert M.check_target(e.incident_store,e.destination,e.digest,clock=e.clock).held


def test_actual_missing_restored_attempt_refuses_without_starting_recovery():
    with REAL.fixture(restored=False) as e:
        args,_=configuration(e)
        before=e.attempts.inspect()
        with patch.object(C,'datetime',SEALED.fixture_clock(e)), \
             patch.object(C,'run_recovery_once',side_effect=AssertionError('implicit recovery')):
            refused(args,'RECOVERED_SELECTION_RESTORED_ATTEMPT_REQUIRED')
        assert e.attempts.inspect()==before and not I.research_route_releases(e.incident_store.inspect().state)


def test_closed_output_refuses_inconsistent_real_result_without_echoing_private_fields():
    with REAL.fixture() as e:
        actual=REAL.select(e)
        args={'route-id':e.route.route_id,'incident-id':e.incident_id,'digest':e.digest}
        cases=(replace(actual,execution_ready=True),replace(actual,release_record_id=None),
               replace(actual,route_id='/private/supplied-path'),
               replace(actual,selection_assessment=replace(actual.selection_assessment,
                   selection=replace(actual.selection_assessment.selection,reasons=('private value',)))))
        for value in cases:
            try:
                C._selection_output(value,args)
            except C.RecoveryCLIError as exc:
                assert str(exc)=='RECOVERY_CLI_RESULT_INVALID'
            else:
                raise AssertionError('inconsistent display result accepted')
