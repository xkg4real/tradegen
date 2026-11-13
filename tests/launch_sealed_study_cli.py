"""Explicit CLI admission and real temporary sealed-selection integration.

All homes, keys, store files and signatures are disposable fixtures. Clock
patches replace the external wall clock only; positive authentication must use
actual CurrentOwnerAuthority and the actual sealed orchestrator. No API/order.
"""
from contextlib import contextmanager, redirect_stdout
from dataclasses import asdict
from datetime import timedelta
from io import StringIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation as A
from execution_launch import sealed_study_cli as C
from execution_launch.profile import profile_body
from execution_launch.sealed_study_review import SealedStudyReviewError
from execution_launch.strategy import _plain
from tests import launch_bundle_auth as ARCHIVE
from tests import launch_study as STUDY
from tests import launch_study_review as SOURCE


def basic_args():
    pairs={'sealed-root':'primary','backup-root':'backup','head-name':'bundle-head','limits':'limits.json',
        'digest':'a'*64,'archive-attestation':'archive.json','profile':'profile.json',
        'window':'window.json','head-root':'heads'}
    return ['select-sealed',*(item for pair in pairs.items() for item in ('--'+pair[0],pair[1]))]


def invoke(arguments):
    stream=StringIO()
    with redirect_stdout(stream):
        code=C.main(arguments)
    text=stream.getvalue()
    return code,json.loads(text),text


def failed(arguments,expected=None):
    code,result,text=invoke(arguments)
    assert code==2 and result['status']=='REFUSED'
    assert all(result[key] is False for key in ('archive_identity_authenticated','source_reviews_authenticated',
        'selected_implementation_authenticated','research_selection_ready','execution_ready',
        'current_operational_use','automatic_recovery_supported'))
    if expected is not None:assert result['reasons']==[expected],result
    return result,text


@contextmanager
def admission_files():
    """Genuine archive bytes for parser tests; RAW is never a qualified study."""
    with ARCHIVE.fixture() as e:
        root=e.root/'cli';root.mkdir()
        paths={name:root/(name+'.json') for name in ('limits','archive','profile','window')}
        paths['limits'].write_text(json.dumps(asdict(e.store.limits)))
        paths['archive'].write_bytes(ARCHIVE.document(e.request,e.signer.key,issued_at=e.clock()))
        paths['profile'].write_text(json.dumps(profile_body(STUDY.profile())))
        paths['window'].write_text(json.dumps({'deployment_id':'synthetic-cli',
            'start':e.clock().isoformat(),'end':(e.clock()+timedelta(hours=1)).isoformat()}))
        args=['select-sealed','--sealed-root',str(e.store.roots.sealed_root),
            '--backup-root',str(e.store.roots.backup_root),'--head-name','bundle-head',
            '--limits',str(paths['limits']),'--digest',e.digest,'--archive-attestation',str(paths['archive']),
            '--profile',str(paths['profile']),'--window',str(paths['window']),'--head-root',str(root/'heads')]
        yield SimpleNamespace(env=e,root=root,paths=paths,args=args)


def test_minimal_and_repeated_explicit_arguments_have_no_implicit_clock_or_authority():
    command,args=C._arguments(basic_args())
    assert command=='select-sealed' and args['source-review']==[] and args['audit']==[]
    command,args=C._arguments(basic_args()+['--source-review','first.json','--source-review','second.json',
        '--audit','Study-A=report_a','--audit','Study-B=report_a','--history-storage','policy.json'])
    assert args['source-review']==['first.json','second.json'] and args['history-storage']=='policy.json'
    assert C._audits(args['audit'])=={'Study-A':'report_a','Study-B':'report_a'}


def test_missing_duplicate_unknown_and_authority_injection_arguments_refuse_before_io():
    baseline=basic_args()
    wrong=[[],['provision'],['select-sealed'],baseline[:-1],baseline+baseline[1:3]]
    for index in range(1,len(baseline),2):wrong.append(baseline[:index]+baseline[index+2:])
    for name in ('now','provider','key','public-key','report','arm','approval','evaluated-result','captures'):
        wrong.append(baseline+['--'+name,'untrusted'])
    with patch.object(C,'_read_file') as reader,patch.object(C,'open_explicit_store') as store, \
            patch.object(C,'CurrentOwnerAuthority') as authority:
        for args in wrong:failed(args)
        assert not reader.called and not store.called and not authority.called


def test_argument_types_nul_digest_and_repeat_count_are_bounded_before_io():
    bad=(None,'select-sealed',[1],basic_args()+['--audit','a\x00=b'],
         [value.upper() if value=='a'*64 else value for value in basic_args()],
         basic_args()+['--source-review','x.json']*129,basic_args()+['--audit','A=a']*129)
    with patch.object(C,'_read_file') as reader,patch.object(C,'CurrentOwnerAuthority') as authority:
        for args in bad:failed(args)
        assert not reader.called and not authority.called


def test_audit_mapping_rejects_duplicates_paths_and_nonlogical_identifiers_before_io():
    values=('=report','Study=','Study=one=two','Study=../report','Study=report.json',
            'Study=C:\\report','Study=REPORT',' Study=report','Study=한글','Study='+'r'*65)
    with patch.object(C,'_read_file') as reader,patch.object(C,'CurrentOwnerAuthority') as authority:
        for value in values:failed(basic_args()+['--audit',value],'SEALED_STUDY_CLI_AUDIT_INVALID')
        failed(basic_args()+['--audit','Study=first','--audit','Study=second'],
               'SEALED_STUDY_CLI_DUPLICATE_AUDIT')
        assert not reader.called and not authority.called


def test_help_performs_no_file_or_owner_io_and_does_not_describe_read_only_operation():
    for args in (['--help'],['-h']):
        stream=StringIO()
        with patch.object(C,'_read_file') as reader,patch.object(C,'CurrentOwnerAuthority') as authority, \
                redirect_stdout(stream):
            assert C.main(args)==0
        assert not reader.called and not authority.called
        assert 'may bind history' in stream.getvalue() and 'never provisions' in stream.getvalue()


def test_private_path_and_malformed_archive_refuse_before_current_owner_construction():
    with admission_files() as e:
        private=e.args.copy();private[private.index('--archive-attestation')+1]=str(e.root/'.env'/'x.json')
        with patch.object(C,'CurrentOwnerAuthority') as authority:
            failed(private,'WORKFLOW_FILE_REFUSED')
            e.paths['archive'].write_bytes(b'{malformed')
            result,text=failed(e.args)
            assert not authority.called and str(e.root) not in text


def test_oversized_archive_is_refused_by_actual_bounded_reader_before_parsing_or_owner():
    with admission_files() as e:
        with e.paths['archive'].open('wb') as stream:stream.truncate(A.MAX_DOCUMENT_BYTES+1)
        with patch.object(C.bundle_attestation,'parse_attestation_document') as parser, \
                patch.object(C,'CurrentOwnerAuthority') as authority:
            result,_=failed(e.args)
            # POSIX refuses at fstat; the Windows bounded reader has its own size code.
            assert result['reasons'] in (['WORKFLOW_FILE_REFUSED'],['WORKFLOW_FILE_TOO_LARGE'])
            assert not parser.called and not authority.called


def test_fixed_window_over_24_hours_and_invalid_history_policy_refuse_before_owner():
    with admission_files() as e:
        original=e.paths['window'].read_bytes()
        body=json.loads(original);body['end']=(e.env.clock()+timedelta(hours=25)).isoformat()
        e.paths['window'].write_text(json.dumps(body))
        with patch.object(C,'CurrentOwnerAuthority') as authority:
            failed(e.args,'OWNER_WINDOW_INVALID')
            assert not authority.called
        e.paths['window'].write_bytes(original)
        policy=e.root/'policy.json';policy.write_bytes(b'{}')
        with patch.object(C,'CurrentOwnerAuthority') as authority:
            failed(e.args+['--history-storage',str(policy)])
            assert not authority.called


def test_bad_profile_and_duplicate_window_fields_are_not_relabelled_as_current_observations():
    with admission_files() as e:
        original=e.paths['profile'].read_bytes();e.paths['profile'].write_bytes(b'{}')
        with patch.object(C,'CurrentOwnerAuthority') as authority:
            failed(e.args)
            assert not authority.called
        e.paths['profile'].write_bytes(original)
        e.paths['window'].write_bytes(b'{"deployment_id":"one","deployment_id":"two"}')
        with patch.object(C,'CurrentOwnerAuthority') as authority:
            failed(e.args,'OWNER_JSON_INVALID')
            assert not authority.called


@SOURCE.isolated_evaluations
def test_signed_review_study_id_is_derived_and_duplicate_document_refuses_before_owner():
    source=SOURCE.fixture()
    with admission_files() as e:
        path=e.root/'source.json';path.write_text(next(iter(source.documents.values())))
        with patch.object(C,'CurrentOwnerAuthority') as authority:
            failed(e.args+['--source-review',str(path),'--source-review',str(path)],
                   'SEALED_STUDY_CLI_DUPLICATE_DOCUMENT')
            assert not authority.called


def test_malformed_or_oversized_source_review_refuses_before_owner_construction():
    with admission_files() as e:
        path=e.root/'source.json'
        for raw in (b'{bad',b'{}',b'x'*(C.MAX_DOCUMENT_BYTES+1)):
            path.write_bytes(raw)
            with patch.object(C,'CurrentOwnerAuthority') as authority:
                result,text=failed(e.args+['--source-review',str(path)])
                assert not authority.called and str(path) not in text


def test_untrusted_exception_text_is_redacted_and_interrupt_is_not_approval():
    for error in (OSError('secret path and document bytes'),OSError('UPPERCASE_SECRET'),
                  ValueError('UPPERCASE_SECRET'),AttributeError('UPPERCASE_SECRET')):
        with patch.object(C,'_read_file',side_effect=error):
            _,text=failed(basic_args(),'SEALED_STUDY_CLI_INPUT_REFUSED')
            assert 'secret' not in text and 'UPPERCASE_SECRET' not in text
    with patch.object(C,'_read_file',side_effect=KeyboardInterrupt):
        failed(basic_args(),'SEALED_STUDY_CLI_STOPPED')


def test_cli_builds_one_actual_provider_with_the_same_real_clock_before_core_refusal():
    # A negative orchestration seam inspects wiring then refuses. It does not
    # replace any authority verification with success or issue a fake approval.
    with admission_files() as e:
        calls=[]
        def refuse_core(store,digest,**kwargs):
            provider=kwargs['authority_provider'];clock=kwargs['clock']
            assert type(provider) is CurrentOwnerAuthority and provider._clock is clock
            assert clock().utcoffset()==timedelta(0)
            assert type(kwargs['archive_attestation']) is bytes
            assert kwargs['source_reviews']=={} and kwargs['audit_logical_ids']=={}
            assert kwargs['history_storage_policy'] is None
            assert isinstance(kwargs['history_head_root'],Path)
            assert digest==e.env.digest and store.roots==e.env.store.roots
            calls.append(True)
            raise SealedStudyReviewError('SEALED_STUDY_SYNTHETIC_TEST_REFUSAL')
        with patch.object(C,'authenticate_sealed_study_selection',side_effect=refuse_core):
            failed(e.args,'SEALED_STUDY_SYNTHETIC_TEST_REFUSAL')
        assert calls==[True]


def test_unexpected_core_display_object_cannot_publish_operational_flags():
    with admission_files() as e:
        forged=SimpleNamespace(scope='sealed_research_selection',execution_ready=True,
                               current_operational_use=True,automatic_recovery_supported=True)
        with patch.object(C,'authenticate_sealed_study_selection',return_value=forged):
            failed(e.args,'SEALED_STUDY_CLI_RESULT_INVALID')


def sealed_arguments(e):
    """Explicit files from the actual signed fixture; no replacement evaluator."""
    root=e.base/'cli-inputs';root.mkdir()
    paths={name:root/(name+'.json') for name in ('limits','archive','profile','window')}
    paths['limits'].write_text(json.dumps(asdict(e.store.limits)))
    paths['archive'].write_bytes(e.archive)
    paths['profile'].write_text(json.dumps(profile_body(e.profile)))
    paths['window'].write_text(json.dumps(_plain(e.window)))
    args=['select-sealed','--sealed-root',str(e.store.roots.sealed_root),
        '--backup-root',str(e.store.roots.backup_root),'--head-name','bundle-head',
        '--limits',str(paths['limits']),'--digest',e.digest,'--archive-attestation',str(paths['archive']),
        '--profile',str(paths['profile']),'--window',str(paths['window']),
        '--head-root',str(e.history_head_root)]
    for index,(identifier,document) in enumerate(sorted(e.reviews.items())):
        path=root/('review-'+str(index)+'.json');path.write_bytes(document)
        args+=['--source-review',str(path),'--audit',identifier+'='+e.audits[identifier]]
    return args,root


def fixture_clock(e):
    class WallClock:
        @staticmethod
        def now(zone):
            assert zone.utcoffset(None)==timedelta(0)
            return e.clock()
    return WallClock


def test_actual_legacy_and_carry_cli_selects_with_real_owner_signatures_factory_and_history():
    from tests import launch_sealed_study_review as REAL
    for carry in (False,True):
        with REAL.fixture(carry=carry) as e:
            args,root=sealed_arguments(e)
            before={p.name:p.read_bytes() for p in root.iterdir()}
            # Only the external wall-clock seam is replaced. Provider, real
            # store graph/evaluator, signatures and factory/history are intact.
            with patch.object(C,'datetime',fixture_clock(e)):
                code,result,text=invoke(args)
            assert code==0 and result['status']=='SELECTED',result
            assert result['scope']=='sealed_research_selection'
            assert result['archive_identity_authenticated'] and result['source_reviews_authenticated']
            assert result['selected_implementation_authenticated'] and result['research_selection_ready']
            assert result['authenticated_study_ids']==sorted(e.reviews)
            assert len(result['selection']['rows'])==3  # Computed rejection is retained.
            assert result['selection']['selected_strategy_id']=='fixture-ma-1-2-a'
            assert all(result[name] is False for name in ('execution_ready','current_operational_use',
                                                          'automatic_recovery_supported'))
            assert result['selection']['execution_ready'] is False
            assert result['verified_at']==e.clock().isoformat(timespec='microseconds')
            assert str(e.base) not in text and str(e.home) not in text
            assert before=={p.name:p.read_bytes() for p in root.iterdir()}


def test_actual_no_qualified_cli_result_authenticates_archive_without_creating_history_head():
    from tests import launch_sealed_study_review as REAL
    with REAL.fixture(count=60,provision=False) as e:
        assert not e.reviews
        args,_=sealed_arguments(e)
        with patch.object(C,'datetime',fixture_clock(e)):
            code,result,_=invoke(args)
        assert code==0 and result['status']=='NO_QUALIFIED_MARKET',result
        assert result['archive_identity_authenticated']
        assert not result['source_reviews_authenticated'] and not result['selected_implementation_authenticated']
        assert not result['research_selection_ready'] and not result['execution_ready']
        assert not result['current_operational_use'] and not result['automatic_recovery_supported']
        assert result['authenticated_study_ids']==[] and not list(e.history_head_root.iterdir())


def test_actual_cli_current_revocation_refuses_complete_research_without_reranking_or_provision():
    from tests import launch_sealed_study_review as REAL
    from tests import compliance_fixtures as CF
    from execution_launch.research_revocation import EVENT_KIND, revocation_target
    with REAL.fixture(provision=False) as e:
        args,_=sealed_arguments(e)
        identifier=next(iter(e.reviews));document=e.reviews[identifier]
        purpose=e.bodies[identifier]['purpose']
        CF.sign(e.key,EVENT_KIND,{'purpose':purpose,
            'target_sha256':revocation_target(document,purpose=purpose),'reason_code':'OWNER_WITHDRAWN'},
            utc=e.clock().strftime('%Y-%m-%dT%H:%M:%SZ'))
        with patch.object(C,'datetime',fixture_clock(e)):
            failed(args,'REVIEW_ATTESTATION_REVOKED')
        assert not list(e.history_head_root.iterdir())
