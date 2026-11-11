"""Offline workflow tests use invented prices, private temporary files and no owner state."""
from contextlib import ExitStack, redirect_stdout
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from execution_launch import workflow as W, program, paper_capture
from execution_launch.profile import profile_body, profile_contract_digest
from execution_launch.strategy import protocol_json, register_protocol
from tests import compliance_fixtures as F
from tests.launch_profile import fixture_profile
from tests.launch_strategy import START, fixture_capture
from tests.notrun import NotRun
from tools.research import prepare_launch_example as example

D = Decimal


def invoke(*argv):
    output = StringIO()
    with redirect_stdout(output):
        code = W.main(list(argv))
    return code, json.loads(output.getvalue()), output.getvalue()


def _plain(value):
    from execution_launch.strategy import _plain as plain
    return plain(value)


def fixture(*, source_kind='synthetic'):
    profile = fixture_profile(START)
    profile = replace(profile, policy=replace(profile.policy, initial_equity=D('1000')))
    p, bars, decisions, rules, registry, result, now = fixture_capture(
        source_kind=source_kind, profile_digest=profile_contract_digest(profile),
        code_digest=profile.strategy_code_sha256, rules=profile.instrument_rules)
    body = dict(registry=_plain(registry), source_kind=source_kind,
                bars=_plain(bars), decisions=_plain(decisions))
    return profile, p, body, now


def files(root, profile, protocol, capture):
    root = Path(root)
    paths = [root / name for name in ('private-profile.json', 'protocol.json', 'capture.json')]
    for path, raw in zip(paths, (json.dumps(profile_body(profile)), protocol_json(protocol), json.dumps(capture))):
        path.write_text(raw)
    return tuple(map(str, paths))


def test_default_and_argument_errors_never_read_environment_clock_or_files():
    with ExitStack() as stack:
        for name in ('execution_launch.workflow._read_file', 'execution_launch.workflow._artifact',
                     'os.getenv', 'pathlib.Path.home', 'socket.create_connection'):
            stack.enter_context(patch(name, side_effect=AssertionError('unexpected effect')))
        stack.enter_context(patch.object(os._Environ, '__getitem__', side_effect=AssertionError('environment read')))
        code, report, _ = invoke()
        assert code == 2 and report['reasons'] == ['WORKFLOW_INPUT_REQUIRED']
        for args in (('activate',), ('record', '--source-kind', 'prospective_paper_capture'),
                     ('evaluate', '--profile', 'secret-path'),
                     ('inspect-program', '--program', 'one.json', '--program', 'two.json')):
            code, report, raw = invoke(*args)
            assert code == 2 and not report['execution_ready']
            assert 'secret-path' not in raw


def test_evaluation_recomputes_metrics_but_never_authenticates_claimed_prospective_files():
    profile, protocol, body, now = fixture(source_kind='prospective_paper_capture')
    with tempfile.TemporaryDirectory() as root:
        p, t, c = files(root, profile, protocol, body)
        code, report, raw = invoke('evaluate', '--profile', p, '--protocol', t, '--capture', c, '--now', now.isoformat())
        assert code == 0 and report['workflow_complete'] and report['math_qualified']
        assert report['source_kind'] == 'retrospective_replay'
        assert not report['source_authenticated'] and not report['research_review_ready']
        assert not report['execution_ready'] and not report['owner_approval_verified']
        assert 'STRATEGY_NONPROSPECTIVE_SOURCE' in report['reasons']
        assert report['primary']['completed_roundtrips'] == 25
        for value in (p, t, c, profile.account_scope, profile.profile_id, protocol.study_id,
                      'total_fees_quote', 'turnover_quote', 'initial_equity'):
            assert value not in raw


def test_binding_and_capital_mismatch_refuse_before_evaluation_and_do_not_echo_inputs():
    profile, protocol, body, now = fixture()
    for changed in (replace(profile, account_scope='private-changed-scope'),
                    replace(profile, policy=replace(profile.policy, initial_equity=D('1100')))):
        with tempfile.TemporaryDirectory() as root:
            p, t, c = files(root, changed, protocol, body)
            with patch.object(W, 'evaluate_capture_json', side_effect=AssertionError('unbound evaluation')):
                code, report, raw = invoke('evaluate', '--profile', p, '--protocol', t, '--capture', c, '--now', now.isoformat())
            assert code == 2 and report['reasons'] == ['WORKFLOW_PROFILE_PROTOCOL_MISMATCH']
            assert 'private-changed-scope' not in raw and p not in raw


def test_unknown_loss_budgets_do_not_block_offline_arithmetic_or_become_approved():
    profile, protocol, body, now = fixture()
    profile = replace(profile, policy=replace(profile.policy, first_day_loss_budget=None,
                                              zero_profit_day_loss_budget=None))
    protocol = replace(protocol, profile_contract_digest=profile_contract_digest(profile))
    body['registry'] = _plain(register_protocol(protocol))
    report = W.evaluate_files(profile, protocol, json.dumps(body), now=now)
    assert report['workflow_complete'] and report['math_qualified']
    assert not report['owner_approval_verified'] and not report['execution_ready']


def test_invalid_time_refuses_before_file_access_and_strict_capture_does_not_accept_pass_claims():
    with patch.object(W, '_read_file', side_effect=AssertionError('must not open')):
        code, report, raw = invoke('evaluate', '--profile', 'private.json', '--protocol', 'protocol.json',
            '--capture', 'capture.json', '--now', 'not-an-actual-secret-time')
        assert code == 2 and report['reasons'] == ['WORKFLOW_EXPLICIT_TIME_REQUIRED']
        assert 'not-an-actual-secret-time' not in raw
    profile, protocol, body, now = fixture()
    body['eligible'] = True
    with tempfile.TemporaryDirectory() as root:
        p, t, c = files(root, profile, protocol, body)
        code, report, _ = invoke('evaluate', '--profile', p, '--protocol', t, '--capture', c, '--now', now.isoformat())
        assert code == 2 and report['reasons'] == ['STRATEGY_CAPTURE_JSON_SCHEMA_INVALID']


def test_reader_refuses_private_paths_links_nonregular_files_and_bounds_even_stale_stat():
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        source = root / 'data.json'; source.write_text('{}')
        linked = root / 'link.json'; linked.symlink_to(source)
        directory = root / 'dirlink'; directory.symlink_to(root, target_is_directory=True)
        denied = [linked, directory / 'data.json', root / '.env.json',
                  root / '.tradegen' / 'profile.json', root / '..' / 'escape.json']
        if os.name != 'nt':
            fifo = root / 'pipe.json'; os.mkfifo(fifo); denied.append(fifo)
        for path in denied:
            try:
                W._read_file(str(path), 16)
            except W.WorkflowError:
                pass
            else:
                raise AssertionError('unsafe file read accepted')
        hardlink = root / 'hard.json'; os.link(source, hardlink)
        try:
            W._read_file(str(hardlink), 16)
        except W.WorkflowError:
            pass
        else:
            raise AssertionError('hard link accepted')
        if os.name == 'nt':
            raise NotRun('REFDATA: the descriptor fstat seam and os.mkfifo need POSIX; '
                         'Windows cases run in launch_private_input T7/T8/T11')
        oversized = root / 'oversize.json'; oversized.write_text(' ' * 17)
        with patch.object(W.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_size=0, st_nlink=1)):
            try:
                W._read_file(str(oversized), 16)
            except W.WorkflowError as exc:
                assert str(exc) == 'WORKFLOW_FILE_TOO_LARGE'
            else:
                raise AssertionError('bounded reader accepted oversized input')


def test_inspect_program_hashes_actual_source_bytes_and_never_emits_program_parameters():
    spec = program.ProgramSpec(schema_version=1, strategy_id='private-research-id', kind='cash',
                               fast_window=0, slow_window=0, exposure_fraction=D('0'))
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / 'program.json'; path.write_text(program.program_json(spec))
        code, report, raw = invoke('inspect-program', '--program', str(path))
        assert code == 0 and report['workflow_complete'] and not report['execution_ready']
        assert report['program_digest'] == program.program_digest(spec, W._artifact('program.py'))
        assert report['capture_source_code_sha256'] == hashlib.sha256(W._artifact('paper_capture.py')).hexdigest()
        assert str(path) not in raw and spec.strategy_id not in raw and 'exposure_fraction' not in raw


def test_record_emits_only_on_explicit_request_and_archive_remains_synthetic():
    profile, protocol, body, now = fixture()
    spec = program.ProgramSpec(schema_version=1, strategy_id=protocol.strategy_id, kind='cash',
                               fast_window=0, slow_window=0, exposure_fraction=D('0'))
    code_digest = program.program_digest(spec, W._artifact('program.py'))
    profile = replace(profile, strategy_code_sha256=code_digest)
    protocol = replace(protocol, strategy_code_sha256=code_digest,
        profile_contract_digest=profile_contract_digest(profile),
        capture_source_code_sha256=hashlib.sha256(W._artifact('paper_capture.py')).hexdigest())
    body['registry'] = _plain(register_protocol(protocol)); del body['decisions']
    with tempfile.TemporaryDirectory() as root:
        p, t, b = files(root, profile, protocol, body)
        g = str(Path(root) / 'program.json'); Path(g).write_text(program.program_json(spec))
        args = ('record', '--profile', p, '--protocol', t, '--program', g, '--bars', b, '--now', now.isoformat())
        code, report, raw = invoke(*args)
        assert code == 0 and report['source_kind'] == 'synthetic' and report['workflow_complete']
        assert report['observations'] == 251 and report['decisions'] == 250
        assert 'bars' not in report and 'registry' not in report and not report['execution_ready']
        code, archive, serialized = invoke(*args, '--emit-capture')
        assert code == 0 and archive['source_kind'] == 'synthetic'
        assert len(archive['decisions']) == 250 and all(row['target_fraction'] == '0' for row in archive['decisions'])
        assert hashlib.sha256(serialized.encode()).hexdigest() == report['capture_sha256']
        evaluation = W.evaluate_files(profile, protocol, serialized, now=now)
        assert evaluation['workflow_complete'] and not evaluation['math_qualified']
        body['source_kind'] = 'prospective_paper_capture'; Path(b).write_text(json.dumps(body))
        code, rejected, _ = invoke(*args)
        assert code == 2 and rejected['reasons'] == ['CAPTURE_BATCH_NOT_PROSPECTIVE']


def test_parser_errors_never_leak_raw_provider_text_or_values():
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / 'bad.json'; path.write_text('{"private-secret-value":NaN}')
        code, report, raw = invoke('inspect-program', '--program', str(path))
        assert code == 2 and not report['execution_ready']
        assert 'private-secret-value' not in raw and str(path) not in raw
        with patch.object(program, 'parse_program', side_effect=ValueError('private-provider-response')):
            code, report, raw = invoke('inspect-program', '--program', str(path))
        assert code == 2 and report['reasons'] == ['WORKFLOW_INPUT_REFUSED']
        assert 'private-provider-response' not in raw


def test_generated_example_records_evaluates_and_creates_only_unsigned_review_request():
    now = START + timedelta(hours=2)
    with tempfile.TemporaryDirectory() as root:
        destination = str(Path(root) / 'new-synthetic-example')
        output = StringIO()
        with redirect_stdout(output):
            code = example.main(['--directory', destination, '--now', now.isoformat()])
        assert code == 0 and json.loads(output.getvalue())['source_kind'] == 'synthetic'
        assert destination not in output.getvalue()
        paths = {name: str(Path(destination) / (name+'.json')) for name in ('profile', 'protocol', 'program', 'bars')}
        assert set(p.name for p in Path(destination).iterdir()) == {name+'.json' for name in paths}
        shared = ('--profile', paths['profile'], '--protocol', paths['protocol'])
        code, archive, serialized = invoke('record', *shared, '--program', paths['program'],
            '--bars', paths['bars'], '--now', now.isoformat(), '--emit-capture')
        assert code == 0 and archive['source_kind'] == 'synthetic' and len(archive['decisions']) == 60
        capture = str(Path(destination) / 'capture.json'); Path(capture).write_text(serialized)
        code, evaluated, _ = invoke('evaluate', *shared, '--capture', capture, '--now', now.isoformat())
        assert code == 0 and not evaluated['math_qualified'] and not evaluated['execution_ready']
        assert evaluated['primary']['completed_roundtrips'] == 0
        # A malicious label can only survive as an explicit unverified review claim.
        archive['source_kind'] = 'prospective_paper_capture'; Path(capture).write_text(json.dumps(archive))
        code, request, serialized_request = invoke('request-review', *shared, '--program', paths['program'],
            '--capture', capture, '--now', now.isoformat())
        assert code == 0 and request['artifact_kind'] == 'unsigned_strategy_review_request'
        assert request['source_kind_claim'] == 'prospective_paper_capture'
        assert all(value is False for value in request['authority'].values())
        assert all(request[name] is None for name in ('reviewer_id', 'review_public_key', 'review_signature'))
        assert W.review_request.parse_review_request(serialized_request) == request
        spec = program.parse_program(Path(paths['program']).read_bytes())
        changed = replace(spec, strategy_id='different-program')
        Path(paths['program']).write_text(program.program_json(changed))
        with patch.object(W, 'evaluate_capture_json', side_effect=AssertionError('unbound program evaluated')):
            code, rejected, _ = invoke('request-review', *shared, '--program', paths['program'],
                '--capture', capture, '--now', now.isoformat())
        assert code == 2 and rejected['reasons'] == ['WORKFLOW_PROGRAM_BINDING_MISMATCH']


def test_example_writer_allows_windows_scratch_only_while_temp_lies_under_localappdata():
    """On nt the profile is refused except the interpreter's temporary directory, and only while that directory and
    the destination, both resolved, lie under %LOCALAPPDATA%: a TEMP that is a junction leaving LocalAppData, or a
    destination that leaves TEMP through one, keeps the home refusal before any write. Everything is built inside
    this test's own temporary directory, so a regression could write nowhere else. POSIX never has the allowance:
    the linked-destination test below refuses Path.home() outright there."""
    scratch = Path(tempfile.gettempdir()).resolve()
    if os.name != 'nt' or len(scratch.parts) < 2 or scratch.parts[1].casefold() != 'users':
        raise NotRun('REFDATA: the LocalAppData scratch allowance needs Windows with TEMP inside the profile')
    contents = {name: '{}' for name in ('profile.json', 'protocol.json', 'program.json', 'bars.json')}
    with tempfile.TemporaryDirectory() as root:
        local, elsewhere = Path(root) / 'local', Path(root) / 'elsewhere'
        for directory in (local, local / 'temp', elsewhere):
            directory.mkdir()
        F.directory_link(local / 'temp-link', elsewhere)        # TEMP itself leaves LocalAppData through a junction
        F.directory_link(local / 'temp' / 'link', elsewhere)    # TEMP is real; the destination leaves it through one
        with patch.dict(os.environ, {'LOCALAPPDATA': str(local)}):
            for temp, destination in ((local / 'temp-link', local / 'temp-link' / 'child'),
                                      (local / 'temp', local / 'temp' / 'link' / 'child')):
                with patch.object(example.tempfile, 'gettempdir', return_value=str(temp)):
                    try:
                        example.write_new_directory(str(destination), contents)
                    except W.WorkflowError as exc:
                        assert str(exc) == 'EXAMPLE_HOME_DIRECTORY_REFUSED', (temp.name, exc)
                    else:
                        raise AssertionError('a junction out of LocalAppData was accepted under the profile')
            assert not any(elsewhere.iterdir()) and not any((local / 'temp').glob('child'))
            with patch.object(example.tempfile, 'gettempdir', return_value=str(local / 'temp')):
                example.write_new_directory(str(local / 'temp' / 'fresh'), contents)   # the real TEMP is allowed
        assert {p.name for p in (local / 'temp' / 'fresh').iterdir()} == set(contents)


def test_example_writer_never_overwrites_or_follows_private_or_linked_destinations():
    contents = {name: '{}' for name in ('profile.json', 'protocol.json', 'program.json', 'bars.json')}
    with tempfile.TemporaryDirectory() as root:
        root = Path(root)
        existing = root / 'existing'; existing.mkdir()
        marker = existing / 'keep.txt'; marker.write_text('keep')
        linked = root / 'linked'; linked.symlink_to(root, target_is_directory=True)
        real = root / 'real'; real.mkdir()
        F.directory_link(root / 'junction', real)       # a junction on Windows, a symlink elsewhere
        for path in (existing, linked / 'child', root / 'junction' / 'child', root / '.tradegen' / 'child',
                     root / '..' / 'child', Path('/home/owner/child'), Path('/root/child'),
                     Path('/Users/owner/child'), Path.home() / 'child'):
            try:
                example.write_new_directory(str(path), contents)
            except W.WorkflowError:
                pass
            else:
                raise AssertionError('unsafe destination accepted')
        assert marker.read_text() == 'keep' and set(p.name for p in existing.iterdir()) == {'keep.txt'}
        assert not (root / 'child').exists() and not any(real.iterdir())
        fresh = root / 'fresh'
        example.write_new_directory(str(fresh), contents)
        assert {p.name: p.read_text(encoding='utf-8') for p in fresh.iterdir()} == contents
        assert all(os.lstat(p).st_nlink == 1 and not p.is_symlink() for p in fresh.iterdir())
        try:
            example.write_new_directory(str(fresh), contents)
        except W.WorkflowError:
            pass
        else:
            raise AssertionError('existing destination written twice')
        assert {p.name: p.read_text(encoding='utf-8') for p in fresh.iterdir()} == contents
        try:
            example.example_files(now=START.replace(tzinfo=None))
        except W.WorkflowError as exc:
            assert str(exc) == 'EXAMPLE_AWARE_TIME_REQUIRED'
        else:
            raise AssertionError('implicit local clock accepted')


def test_universe_protocol_binds_the_rule_instead_of_the_trade_coin():
    from execution_launch.profile import rule_terms_digest
    from execution_launch.strategy import UNIVERSE_EVALUATOR_REVISION
    profile, protocol, _, _ = fixture()
    rule = hashlib.sha256(b'fixture-universe-rule').hexdigest()
    universe = replace(profile, universe_rule_sha256=rule)
    bound = replace(protocol, evaluator_revision=UNIVERSE_EVALUATOR_REVISION, universe_rule_sha256=rule,
                    profile_contract_digest=profile_contract_digest(universe),
                    rule_terms_digest=rule_terms_digest(universe.instrument_rules, universe_rule_sha256=rule))
    moved = replace(universe, symbol='KRW-ETH',
                    instrument_rules=replace(universe.instrument_rules, symbol='KRW-ETH', tick_size=D('5')))
    for accepted in ((universe, bound), (moved, bound), (profile, protocol)):
        W._bound_profile(*accepted)
    fee = replace(moved, instrument_rules=replace(moved.instrument_rules, fee_fraction=D('0.0005')))
    fixed_moved = replace(profile, symbol='KRW-ETH',
                          instrument_rules=replace(profile.instrument_rules, symbol='KRW-ETH'))
    for refused in ((replace(moved, universe_rule_sha256='f'*64), bound), (fee, bound),
                    (universe, protocol), (profile, bound), (fixed_moved, protocol)):
        try:
            W._bound_profile(*refused)
        except W.WorkflowError as exc:
            assert str(exc) == 'WORKFLOW_PROFILE_PROTOCOL_MISMATCH'
        else:
            raise AssertionError('mismatched profile and protocol accepted')
