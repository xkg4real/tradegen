"""Explicit offline paper workflow; no account access, signing or live execution.

    python -m execution_launch.workflow inspect-program --program PROGRAM.json
    python -m execution_launch.workflow evaluate --profile PROFILE.json --protocol PROTOCOL.json --capture CAPTURE.json --now AWARE_ISO_TIME
    python -m execution_launch.workflow record --profile PROFILE.json --protocol PROTOCOL.json --program PROGRAM.json --bars BARS.json --now AWARE_ISO_TIME [--emit-capture]
    python -m execution_launch.workflow request-review --profile PROFILE.json --protocol PROTOCOL.json --program PROGRAM.json --capture CAPTURE.json --now AWARE_ISO_TIME

Default output is a redacted diagnostic. --emit-capture prints the complete
replay archive and request-review prints an unsigned review request to stdout.
Redirect either artifact to an appropriate private path if needed.
No command writes a file, invents a review receipt or claims execution readiness.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from core.compliance.model import KST
from execution_launch.profile import (
    ProfileError, parse_profile_json, profile_contract_digest, rule_terms_digest,
)
from execution_launch.strategy import (
    StrategyEvidenceError, assess_strategy, evaluate_capture_json, parse_protocol,
)
from execution_launch import program, paper_capture, review_request, private_input, capture_v2, managed_behavior

MAX_CONFIG_BYTES = 65536
MAX_CAPTURE_BYTES = 16 * 1024 * 1024
MAX_ARTIFACT_BYTES = 1024 * 1024
_PRIVATE = frozenset({".tradegen", ".nextgen", ".ssh", ".aws", ".gnupg", ".azure", ".kube", ".git"})
_WINDOWS_CODES = {'PRIVATE_INPUT_PLATFORM_UNSUPPORTED': 'WORKFLOW_FILE_PLATFORM_UNSUPPORTED',
                  'PRIVATE_INPUT_PATH_REFUSED': 'WORKFLOW_FILE_REFUSED',
                  'PRIVATE_INPUT_FILE_REFUSED': 'WORKFLOW_FILE_REFUSED',
                  'PRIVATE_INPUT_TOO_LARGE': 'WORKFLOW_FILE_TOO_LARGE'}
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,95}")
CARRY_CAPTURE_FILES = (
    'execution_launch/workflow.py', 'execution_launch/paper_capture.py',
    'execution_launch/capture_v2.py', 'execution_launch/managed_behavior.py',
    'execution_launch/program.py', 'execution_launch/strategy.py',
    'execution_launch/review_request.py',
    'execution_control/capability.py',
)


class WorkflowError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise WorkflowError(code)


def _arguments(argv):
    values = sys.argv[1:] if argv is None else argv
    _require(type(values) in (list, tuple) and all(type(v) is str for v in values),
             'WORKFLOW_ARGUMENTS_INVALID')
    if not values:
        return None, {}
    if tuple(values) in (('--help',), ('-h',)):
        return 'help', {}
    command = values[0]
    allowed = {
        'inspect-program': {'program'},
        'evaluate': {'profile', 'protocol', 'capture', 'now'},
        'record': {'profile', 'protocol', 'program', 'bars', 'now', 'emit-capture'},
        'request-review': {'profile', 'protocol', 'program', 'capture', 'now'},
    }
    _require(command in allowed, 'WORKFLOW_ARGUMENTS_INVALID')
    output, index = {}, 1
    while index < len(values):
        key = values[index]
        index += 1
        _require(key.startswith('--') and key[2:] in allowed[command]
                 and key[2:] not in output, 'WORKFLOW_ARGUMENTS_INVALID')
        key = key[2:]
        if key == 'emit-capture':
            output[key] = True
        else:
            _require(index < len(values) and values[index] and not values[index].startswith('--'),
                     'WORKFLOW_ARGUMENTS_INVALID')
            output[key] = values[index]
            index += 1
    _require(set(output) >= allowed[command]-{'emit-capture'}, 'WORKFLOW_ARGUMENTS_REQUIRED')
    return command, output


def _time(raw):
    try:
        now = datetime.fromisoformat(raw)
        _require(now.utcoffset() is not None, 'WORKFLOW_EXPLICIT_TIME_REQUIRED')
        now.astimezone(timezone.utc); now.astimezone(KST)
        return now
    except (ValueError, TypeError, OverflowError):
        raise WorkflowError('WORKFLOW_EXPLICIT_TIME_REQUIRED') from None


def _read_file(path, maximum, *, suffix='.json'):
    """Bounded no-follow read of one explicit regular file, without home/env lookup.

    Windows uses execution_launch.private_input.
    """
    _require(type(path) is str and path and '\x00' not in path, 'WORKFLOW_FILE_REFUSED')
    candidate = Path(path)
    parts = candidate.parts
    _require(candidate.suffix == suffix and '..' not in parts, 'WORKFLOW_FILE_REFUSED')
    absolute = Path(os.path.abspath(candidate))
    _require(not any(part.casefold() in _PRIVATE or part.casefold() == '.env'
                     or part.casefold().startswith('.env.') for part in absolute.parts),
             'WORKFLOW_FILE_REFUSED')
    if os.name == 'nt':
        try:
            return private_input.read_private_file(path, maximum=maximum, suffix=suffix, private=_PRIVATE)
        except private_input.PrivateInputError as exc:
            raise WorkflowError(_WINDOWS_CODES.get(str(exc), 'WORKFLOW_FILE_UNAVAILABLE_OR_REFUSED')) from None
    _require(os.open in os.supports_dir_fd and hasattr(os, 'O_NOFOLLOW')
             and hasattr(os, 'O_DIRECTORY'), 'WORKFLOW_FILE_PLATFORM_UNSUPPORTED')
    directory_fd = file_fd = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
        directory_fd = os.open(absolute.anchor, flags)
        for component in absolute.parts[1:-1]:
            next_fd = os.open(component, flags, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(absolute.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                          | getattr(os, 'O_CLOEXEC', 0), dir_fd=directory_fd)
        info = os.fstat(file_fd)
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                 and info.st_size <= maximum, 'WORKFLOW_FILE_REFUSED')
        chunks, remaining = [], maximum + 1
        while remaining:
            chunk = os.read(file_fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        result = b''.join(chunks)
        _require(len(result) <= maximum, 'WORKFLOW_FILE_TOO_LARGE')
        return result
    except OSError:
        raise WorkflowError('WORKFLOW_FILE_UNAVAILABLE_OR_REFUSED') from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def _artifact(name):
    _require(name in ('program.py', 'paper_capture.py'), 'WORKFLOW_ARTIFACT_REFUSED')
    return _read_file(str(Path(__file__).absolute().with_name(name)), MAX_ARTIFACT_BYTES, suffix='.py')


read_file = _read_file      # the public names other modules in the closure use (coordinator.compose)
artifact = _artifact


def carry_capture_source_artifact() -> bytes:
    """Actual bounded producer manifest for v2; legacy single-file artifacts stay separate."""
    root = Path(__file__).absolute().parent.parent
    files = {name: hashlib.sha256(_read_file(str(root / name), MAX_ARTIFACT_BYTES, suffix='.py')).hexdigest()
             for name in CARRY_CAPTURE_FILES}
    return json.dumps({'schema_version': 2, 'capture_revision': 'fixed-carry-capture-v2', 'files': files},
                      sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def _json(raw):
    def pairs(rows):
        output = {}
        for key, value in rows:
            _require(key not in output, 'WORKFLOW_JSON_DUPLICATE_KEY')
            output[key] = value
        return output
    def invalid(value):
        raise WorkflowError('WORKFLOW_JSON_NUMBER_INVALID')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_float=invalid, parse_constant=invalid)
    except (ValueError, TypeError, RecursionError, UnicodeError):
        raise WorkflowError('WORKFLOW_JSON_INVALID') from None


def _bound_profile(profile, protocol):
    """A universe protocol binds the signed rule instead of a coin: the profile's symbol is its current trade coin
    and the protocol's symbol is the KRW-BTC benchmark (spec sections 10 and 12)."""
    _require(profile.instrument_rules is not None, 'WORKFLOW_INSTRUMENT_RULES_REQUIRED')
    universe = protocol.universe_rule_sha256 is not None
    _require((profile.venue, profile.market, profile.quote_currency, profile.strategy_id,
              profile.universe_rule_sha256)
             == (protocol.venue, protocol.market, protocol.quote_currency, protocol.strategy_id,
                 protocol.universe_rule_sha256)
             and (universe or profile.symbol == protocol.symbol)
             and profile.strategy_code_sha256 == protocol.strategy_code_sha256
             and profile_contract_digest(profile) == protocol.profile_contract_digest
             and rule_terms_digest(profile.instrument_rules, universe_rule_sha256=profile.universe_rule_sha256)
             == protocol.rule_terms_digest
             and profile.policy.initial_equity == protocol.initial_cash_quote,
             'WORKFLOW_PROFILE_PROTOCOL_MISMATCH')


def _base(command):
    return {'command': command, 'workflow_complete': False, 'account_connected': False,
            'research_review_ready': False, 'owner_approval_verified': False,
            'execution_ready': False, 'reasons': []}


def _metrics(value):
    # Deliberately omit absolute cash, fees, turnover, private scope and record IDs.
    return {name: getattr(value, name) for name in ('observations', 'completed_roundtrips',
        'rejected_small_orders', 'total_return', 'mean_return', 'max_drawdown')}


def evaluate_files(profile, protocol, capture_raw, *, now):
    """Recompute an explicit file capture; claimed prospective labels are not authenticated."""
    _bound_profile(profile, protocol)
    body = _json(capture_raw)
    _require(type(body) is dict and body.get('source_kind') in
             ('synthetic', 'retrospective_replay', 'prospective_paper_capture'),
             'WORKFLOW_CAPTURE_SOURCE_REQUIRED')
    # This command proves arithmetic on supplied files, never original capture origin.
    body['source_kind'] = 'synthetic' if body['source_kind'] == 'synthetic' else 'retrospective_replay'
    result = evaluate_capture_json(protocol, json.dumps(body), profile.instrument_rules, now=now)
    assessment = assess_strategy(protocol, result,
        profile_contract_digest=profile_contract_digest(profile),
        rule_terms_digest=rule_terms_digest(profile.instrument_rules,
                                            universe_rule_sha256=profile.universe_rule_sha256),
        strategy_code_sha256=profile.strategy_code_sha256, now=now)
    output = _base('evaluate')
    output.update(workflow_complete=True, source_kind=result.source_kind,
        source_authenticated=False, math_qualified=assessment.math_qualified,
        reasons=list(assessment.reasons), protocol_digest=assessment.protocol_digest,
        evidence_digest=assessment.evidence_digest,
        primary=_metrics(result.primary), double_cost=_metrics(result.double_cost),
        extra_bar_delay=_metrics(result.extra_bar_delay),
        benchmark=_metrics(result.benchmark), benchmark_excess_mean=result.benchmark_excess_mean,
        family_adjusted_p=result.family_adjusted_p)
    if managed_behavior.resolve_behavior(protocol) == managed_behavior.BEHAVIOR_REVISION:
        output.update(terminal_accounting=managed_behavior.TERMINAL_ACCOUNTING,
                      valuation_is_realized_profit=False)
        for name in ('primary', 'double_cost', 'extra_bar_delay', 'benchmark'):
            output[name]['valuation_return'] = output[name].pop('total_return')
    return output


def main(argv=None):
    command = None
    try:
        command, args = _arguments(argv)
        if command == 'help':
            print(__doc__)
            return 0
        _require(command is not None, 'WORKFLOW_INPUT_REQUIRED')
        if command == 'inspect-program':
            spec = program.parse_program(_read_file(args['program'], MAX_CONFIG_BYTES))
            artifact, capture_artifact = _artifact('program.py'), _artifact('paper_capture.py')
            output = _base(command)
            output.update(workflow_complete=True, program_digest=program.program_digest(spec, artifact),
                program_artifact_sha256=hashlib.sha256(artifact).hexdigest(),
                capture_source_code_sha256=hashlib.sha256(capture_artifact).hexdigest(),
                carry_capture_source_code_sha256=hashlib.sha256(carry_capture_source_artifact()).hexdigest(),
                reasons=['WORKFLOW_HASHES_ARE_NOT_SOURCE_AUTHENTICATION'])
        else:
            now = _time(args['now'])  # Refuse invalid/missing time before any file is read.
            profile = parse_profile_json(_read_file(args['profile'], MAX_CONFIG_BYTES))
            protocol = parse_protocol(_read_file(args['protocol'], MAX_CONFIG_BYTES))
            _bound_profile(profile, protocol)
            if command == 'evaluate':
                output = evaluate_files(profile, protocol,
                    _read_file(args['capture'], MAX_CAPTURE_BYTES), now=now)
            elif command == 'request-review':
                spec = program.parse_program(_read_file(args['program'], MAX_CONFIG_BYTES))
                artifact = _artifact('program.py')
                _require(program.program_digest(spec, artifact) == profile.strategy_code_sha256,
                         'WORKFLOW_PROGRAM_BINDING_MISMATCH')
                # Preserve the original source claim only inside an explicitly
                # unsigned/unverified review request. It is not an authenticated label.
                result = evaluate_capture_json(protocol, _read_file(args['capture'], MAX_CAPTURE_BYTES),
                                               profile.instrument_rules, now=now)
                request = review_request.build_review_request(profile, protocol, result, now=now,
                    program_artifact=artifact, parameters_json=program.parameters_json(spec))
                raw = review_request.review_request_json(request)
                print(raw, end='' if raw.endswith('\n') else '\n')
                return 0
            else:
                spec = program.parse_program(_read_file(args['program'], MAX_CONFIG_BYTES))
                registry, bars, source_kind = paper_capture.parse_replay_input(
                    _read_file(args['bars'], MAX_CAPTURE_BYTES))
                carry = managed_behavior.resolve_behavior(protocol) == managed_behavior.BEHAVIOR_REVISION
                replay = paper_capture.replay_capture_v2 if carry else paper_capture.replay_capture
                archive = replay(protocol, registry, spec, bars,
                    program_artifact=_artifact('program.py'),
                    capture_source_artifact=carry_capture_source_artifact() if carry else _artifact('paper_capture.py'),
                    source_kind=source_kind, now=now)
                raw = capture_v2.capture_json_v2(archive) if carry else paper_capture.capture_json(archive)
                if args.get('emit-capture'):
                    print(raw, end='' if raw.endswith('\n') else '\n')
                    return 0
                output = _base(command)
                output.update(workflow_complete=True, source_kind=archive.source_kind,
                    source_authenticated=False, observations=len(archive.bars), decisions=len(archive.decisions),
                    capture_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest(),
                    reasons=['WORKFLOW_FILE_REPLAY_ONLY', 'WORKFLOW_CAPTURE_EMISSION_NOT_REQUESTED'])
        print(json.dumps(output, sort_keys=True, allow_nan=False))
        return 0  # Completed an offline operation, not permission to trade.
    except (WorkflowError, ProfileError, StrategyEvidenceError, program.ProgramError,
            paper_capture.CaptureError, capture_v2.CaptureV2Error, managed_behavior.ManagedBehaviorError,
            review_request.ReviewRequestError) as exc:
        code = exc.code if type(exc) is ProfileError else str(exc)
        if _CODE.fullmatch(code) is None:
            code = 'WORKFLOW_EVIDENCE_REFUSED'
    except (OSError, ValueError, TypeError, AttributeError, ArithmeticError, RecursionError):
        code = 'WORKFLOW_INPUT_REFUSED'
    output = _base(command if command in ('evaluate', 'record', 'inspect-program', 'request-review') else None)
    output['reasons'] = [code]
    print(json.dumps(output, sort_keys=True))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
