"""Actual offline v2 record/import/evaluation paths over temporary invented input."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from execution_launch import capture_v2 as C, managed_behavior as M, program, review_request, workflow as W
from execution_launch.profile import profile_body, profile_contract_digest
from execution_launch.strategy import protocol_json, register_protocol
from tests import launch_capture_v2 as F, launch_capture as CF, launch_workflow as WF
from tests.launch_profile import fixture_profile


def fixture():
    spec, protocol, _, bars, rules = F.fixture()
    profile = fixture_profile(CF.START)
    code = program.program_digest(spec, W.artifact('program.py'))
    profile = replace(profile, strategy_id=spec.strategy_id, strategy_code_sha256=code,
                      instrument_rules=rules, policy=replace(profile.policy, initial_equity=protocol.initial_cash_quote,
                          drawdown_activation_equity=protocol.initial_cash_quote*4))
    protocol = replace(protocol, strategy_code_sha256=code, profile_contract_digest=profile_contract_digest(profile),
        capture_source_code_sha256=hashlib.sha256(W.carry_capture_source_artifact()).hexdigest())
    body = {'registry': WF._plain(register_protocol(protocol)), 'bars': WF._plain(bars), 'source_kind': 'synthetic'}
    return spec, profile, protocol, body, bars[-1].received_at


def write_inputs(root):
    spec, profile, protocol, body, now = fixture()
    paths = {name: str(Path(root)/(name+'.json')) for name in ('program', 'profile', 'protocol', 'bars', 'capture')}
    Path(paths['program']).write_text(program.program_json(spec))
    Path(paths['profile']).write_text(json.dumps(profile_body(profile)))
    Path(paths['protocol']).write_text(protocol_json(protocol))
    Path(paths['bars']).write_text(json.dumps(body))
    args = ('record', '--profile', paths['profile'], '--protocol', paths['protocol'],
            '--program', paths['program'], '--bars', paths['bars'], '--now', now.isoformat())
    return paths, args, profile, protocol, now


def test_actual_record_import_evaluate_preserves_typed_final_decisions_and_valuation_labels():
    with tempfile.TemporaryDirectory(prefix='tradegen_carry_workflow_') as root:
        paths, args, profile, protocol, now = write_inputs(root)
        code, report, _ = WF.invoke(*args)
        assert code == 0 and report['observations'] == report['decisions'] == 61
        assert report['workflow_complete'] and not report['execution_ready']
        code, body, raw = WF.invoke(*args, '--emit-capture')
        assert code == 0 and body['schema_version'] == 2
        assert body['decisions'][-1]['state'] == 'long_target'
        assert C.parse_capture_v2(protocol, raw).program.strategy_id == protocol.strategy_id
        assert hashlib.sha256(raw.encode()).hexdigest() == report['capture_sha256']
        Path(paths['capture']).write_text(raw)
        code, evaluation, output = WF.invoke('evaluate', '--profile', paths['profile'],
            '--protocol', paths['protocol'], '--capture', paths['capture'], '--now', now.isoformat())
        assert code == 0 and evaluation['workflow_complete']
        assert evaluation['terminal_accounting'] == M.TERMINAL_ACCOUNTING
        assert evaluation['valuation_is_realized_profit'] is False
        assert 'valuation_return' in evaluation['primary'] and 'total_return' not in evaluation['primary']
        assert evaluation['primary']['completed_roundtrips'] == 0
        assert not evaluation['source_authenticated'] and not evaluation['execution_ready']
        assert not evaluation['owner_approval_verified'] and not evaluation['research_review_ready']
        assert 'terminal_cash_quote' not in output and profile.account_scope not in output


def test_evaluate_downgrades_a_prospective_claim_and_refuses_a_forged_unavailable_decision():
    with tempfile.TemporaryDirectory(prefix='tradegen_carry_workflow_') as root:
        paths, args, profile, protocol, now = write_inputs(root)
        code, body, _ = WF.invoke(*args, '--emit-capture')
        assert code == 0
        body['source_kind'] = 'prospective_paper_capture'
        report = W.evaluate_files(profile, protocol, json.dumps(body), now=now)
        assert report['source_kind'] == 'retrospective_replay' and not report['source_authenticated']
        body['decisions'][-1] = F.rewrite_decision(body['decisions'][-1], state='unavailable',
            cause='input_unavailable', target_fraction=None)
        Path(paths['capture']).write_text(json.dumps(body))
        code, report, _ = WF.invoke('evaluate', '--profile', paths['profile'], '--protocol', paths['protocol'],
            '--capture', paths['capture'], '--now', now.isoformat())
        assert code == 2 and not report['workflow_complete'] and not report['execution_ready']


def test_actual_review_request_binds_carry_result_and_remains_unsigned_without_order_authority():
    with tempfile.TemporaryDirectory(prefix='tradegen_carry_workflow_') as root:
        paths, args, _, protocol, now = write_inputs(root)
        code, _, raw = WF.invoke(*args, '--emit-capture')
        assert code == 0
        Path(paths['capture']).write_text(raw)
        code, request, raw = WF.invoke('request-review', '--profile', paths['profile'],
            '--protocol', paths['protocol'], '--program', paths['program'],
            '--capture', paths['capture'], '--now', now.isoformat())
        assert code == 0 and review_request.parse_review_request(raw) == request
        assert request['evaluator_revision'] == M.CARRY_EVALUATOR_REVISION
        assert request['terminal_accounting'] == M.TERMINAL_ACCOUNTING
        assert request['management_behavior_sha256'] == protocol.management_behavior_sha256
        assert request['review_signature'] is None and all(value is False for value in request['authority'].values())
        assert request['computed_summary']['mathematical_criteria_met'] is False


def test_v2_producer_manifest_commits_actual_branch_and_codec_files_and_changed_source_refuses():
    artifact = W.carry_capture_source_artifact()
    manifest = json.loads(artifact)
    assert set(manifest) == {'schema_version', 'capture_revision', 'files'}
    assert set(manifest['files']) == set(W.CARRY_CAPTURE_FILES)
    for name in ('execution_launch/capture_v2.py', 'execution_launch/managed_behavior.py',
                 'execution_launch/paper_capture.py', 'execution_launch/workflow.py'):
        source = Path(W.__file__).absolute().parent.parent / name
        assert manifest['files'][name] == hashlib.sha256(source.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='tradegen_carry_workflow_') as root:
        _, args, _, _, _ = write_inputs(root)
        with patch.object(W, 'carry_capture_source_artifact', return_value=artifact+b' '):
            code, report, _ = WF.invoke(*args)
        assert code == 2 and report['reasons'] == ['CAPTURE_SOURCE_BINDING_MISMATCH']


def test_v2_record_never_accepts_old_single_file_source_binding_or_prospective_replay_input():
    with tempfile.TemporaryDirectory(prefix='tradegen_carry_workflow_') as root:
        paths, args, _, protocol, _ = write_inputs(root)
        legacy_source = hashlib.sha256(W.artifact('paper_capture.py')).hexdigest()
        changed = replace(protocol, capture_source_code_sha256=legacy_source)
        body = json.loads(Path(paths['bars']).read_text())
        body['registry'] = WF._plain(register_protocol(changed))
        Path(paths['protocol']).write_text(protocol_json(changed))
        Path(paths['bars']).write_text(json.dumps(body))
        code, report, _ = WF.invoke(*args)
        assert code == 2 and report['reasons'] == ['CAPTURE_SOURCE_BINDING_MISMATCH']
        Path(paths['protocol']).write_text(protocol_json(protocol))
        body['registry'] = WF._plain(register_protocol(protocol))
        body['source_kind'] = 'prospective_paper_capture'
        Path(paths['bars']).write_text(json.dumps(body))
        code, report, _ = WF.invoke(*args)
        assert code == 2 and report['reasons'] == ['CAPTURE_BATCH_NOT_PROSPECTIVE']
