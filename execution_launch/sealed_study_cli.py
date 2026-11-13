"""Explicit sealed research selection; no account access, signing or activation.

python -m execution_launch.sealed_study_cli select-sealed --sealed-root ROOT --backup-root ROOT --head-name NAME --limits LIMITS.json --digest SHA --archive-attestation FILE.json --profile PROFILE.json --window WINDOW.json --head-root ROOT [--history-storage POLICY.json] [--source-review FILE.json ...] [--audit STUDY_ID=LOGICAL_ID ...]

The command verifies actual stored evidence and current owner signatures through
one orchestration path. It may bind history beneath an existing independent head;
it never provisions a head or store. Audit IDs refer to already sealed reports,
not arbitrary report paths. Source IDs come from the signed documents themselves.
The displayed assessment is not a reusable authorization or operational permit.
No caller-supplied clock, key, callback, evaluation result or approval is accepted.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation
from execution_launch.history_storage import MAX_POLICY_BYTES, parse_policy
from execution_launch.profile import ProfileError, parse_profile_json
from execution_launch.research_bundle import open_explicit_store
from execution_launch.review_auth import MAX_DOCUMENT_BYTES, parse_review_document
from execution_launch.sealed_study_review import (SealedSelectionAssessment,
                                                  authenticate_sealed_study_selection)
from execution_launch.strategy import _plain
from execution_launch.workflow import MAX_CONFIG_BYTES, _CODE, _read_file
from tools.owner.launch import read_window

_REQUIRED = frozenset({'sealed-root', 'backup-root', 'head-name', 'limits', 'digest',
    'archive-attestation', 'profile', 'window', 'head-root'})
_REPEATED = frozenset({'source-review', 'audit'})
_OPTIONAL = frozenset({'history-storage'})
_MAX_DOCUMENTS = 128
_IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_.:-]{0,95}')
_LOGICAL = re.compile(r'[a-z][a-z0-9_-]{0,63}')
_HASH = re.compile(r'[0-9a-f]{64}')


class SealedStudyCLIError(ValueError):
    """Fixed public diagnostics; never private paths or document content."""


def _need(condition, code):
    if not condition:
        raise SealedStudyCLIError(code)


def _arguments(argv):
    _need(type(argv) in (list, tuple) and all(type(value) is str for value in argv),
          'SEALED_STUDY_CLI_ARGUMENTS_INVALID')
    if tuple(argv) in (('--help',), ('-h',)):
        return 'help', {}
    _need(bool(argv) and argv[0] == 'select-sealed' and len(argv) % 2 == 1,
          'SEALED_STUDY_CLI_ARGUMENTS_INVALID')
    result = {name: [] for name in _REPEATED}
    for option, value in zip(argv[1::2], argv[2::2]):
        _need(option.startswith('--') and option[2:] in _REQUIRED | _REPEATED | _OPTIONAL
              and bool(value) and not value.startswith('--') and '\x00' not in value,
              'SEALED_STUDY_CLI_ARGUMENTS_INVALID')
        name = option[2:]
        if name in _REPEATED:
            _need(len(result[name]) < _MAX_DOCUMENTS, 'SEALED_STUDY_CLI_ARGUMENTS_INVALID')
            result[name].append(value)
        else:
            _need(name not in result, 'SEALED_STUDY_CLI_ARGUMENTS_INVALID')
            result[name] = value
    _need(_REQUIRED <= set(result), 'SEALED_STUDY_CLI_ARGUMENTS_REQUIRED')
    _need(_HASH.fullmatch(result['digest']) is not None, 'SEALED_STUDY_CLI_DIGEST_INVALID')
    return argv[0], result


def _audits(values):
    result = {}
    for value in values:
        _need(value.count('=') == 1, 'SEALED_STUDY_CLI_AUDIT_INVALID')
        identifier, logical = value.split('=')
        _need(_IDENTIFIER.fullmatch(identifier) is not None and _LOGICAL.fullmatch(logical) is not None,
              'SEALED_STUDY_CLI_AUDIT_INVALID')
        _need(identifier not in result, 'SEALED_STUDY_CLI_DUPLICATE_AUDIT')
        result[identifier] = logical
    return result


def _base():
    return {'status': 'REFUSED', 'scope': 'sealed_research_selection', 'reasons': [],
        'archive_identity_authenticated': False, 'source_reviews_authenticated': False,
        'selected_implementation_authenticated': False, 'research_selection_ready': False,
        'execution_ready': False, 'current_operational_use': False, 'automatic_recovery_supported': False}


def main(argv=None):
    output = _base()
    try:
        command, args = _arguments(sys.argv[1:] if argv is None else argv)
        if command == 'help':
            print(__doc__)
            return 0
        audits = _audits(args['audit'])
        document = _read_file(args['archive-attestation'], bundle_attestation.MAX_DOCUMENT_BYTES)
        bundle_attestation.parse_attestation_document(document)
        profile = parse_profile_json(_read_file(args['profile'], MAX_CONFIG_BYTES))
        window = read_window(args['window'])  # Explicit fixed-market 24-hour bound.
        storage = (parse_policy(_read_file(args['history-storage'], MAX_POLICY_BYTES))
                   if 'history-storage' in args else None)
        reviews = {}
        for path in args['source-review']:
            raw = _read_file(path, MAX_DOCUMENT_BYTES)
            identifier = parse_review_document(raw)['body']['request']['study_id']
            _need(identifier not in reviews, 'SEALED_STUDY_CLI_DUPLICATE_DOCUMENT')
            reviews[identifier] = raw
        store = open_explicit_store(args['sealed-root'], args['backup-root'], args['head-name'], args['limits'])

        def clock():
            return datetime.now(timezone.utc)

        result = authenticate_sealed_study_selection(store, args['digest'],
            archive_attestation=document, source_reviews=reviews, audit_logical_ids=audits,
            current_profile=profile, window=window, history_head_root=Path(args['head-root']),
            history_storage_policy=storage, clock=clock, authority_provider=CurrentOwnerAuthority(clock=clock))
        _need(type(result) is SealedSelectionAssessment and result.scope == 'sealed_research_selection'
              and result.execution_ready is False and result.current_operational_use is False
              and result.automatic_recovery_supported is False,
              'SEALED_STUDY_CLI_RESULT_INVALID')
        output.update(_plain(result))
        output['status'] = result.selection.status
        output['reasons'] = list(result.selection.reasons)
        print(json.dumps(output, sort_keys=True, allow_nan=False))
        return 0
    except KeyboardInterrupt:
        code = 'SEALED_STUDY_CLI_STOPPED'
    except (ValueError, OSError, RuntimeError, TypeError, AttributeError, ArithmeticError, RecursionError, KeyError) as exc:
        # A generic OS/runtime error may itself be uppercase private text.
        # Only domain-specific ValueError subclasses carry public diagnostics.
        code = (exc.code if type(exc) is ProfileError else str(exc)
                if isinstance(exc, ValueError) and type(exc) is not ValueError else None)
        if type(code) is not str or _CODE.fullmatch(code) is None:
            code = 'SEALED_STUDY_CLI_INPUT_REFUSED'
    output = _base()
    output['reasons'] = [code]
    print(json.dumps(output, sort_keys=True, allow_nan=False))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
