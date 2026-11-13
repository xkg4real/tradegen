"""Explicit research incident monitoring and held-evidence selection checks.

python -m execution_launch.research_incident_cli inspect --incident-root ROOT --incident-backup-root ROOT --incident-head-root ROOT --incident-head-name NAME --incident-limits LIMITS.json

Commands: register, check, inspect, list-pending, incident-aware-select. Register
and check additionally require --sealed-root, --backup-root, --head-name, --limits
and --digest. Selection adds the explicit sealed-study CLI inputs. No command
initializes a store/head, repairs evidence, releases a hold, records a successful
delivery, sends a message, signs an approval or activates trading. Status is a
finite observation of the configured incident namespace, never a reusable permit.
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
from execution_launch.incident_aware_selection import (IncidentAwareSelectionAssessment,
                                                        authenticate_incident_aware_selection)
from execution_launch.profile import ProfileError, parse_profile_json
from execution_launch.research_bundle import open_explicit_store
from execution_launch.research_incident_monitor import register_target, check_target
from execution_launch.research_incident_store import IncidentStore, parse_limits
from execution_launch.review_auth import MAX_DOCUMENT_BYTES, parse_review_document
from execution_launch.sealed_study_cli import _audits
from execution_launch.strategy import _plain
from execution_launch.workflow import MAX_CONFIG_BYTES, _CODE, read_file
from tools.owner.launch import read_window

INCIDENT_OPTIONS = frozenset({'incident-root','incident-backup-root','incident-head-root',
                             'incident-head-name','incident-limits'})
_BUNDLE = frozenset({'sealed-root','backup-root','head-name','limits','digest'})
_SELECTION = frozenset({'archive-attestation','profile','window','head-root'})
_REPEATED = frozenset({'source-review','audit'})
_HASH = re.compile(r'[0-9a-f]{64}')
_LIMITS_BYTES = 65536


class IncidentCLIError(ValueError):
    """Fixed public codes, never source bytes, private paths or exception text."""


def _need(condition, code):
    if not condition:
        raise IncidentCLIError(code)


def parse_options(values, *, required, optional=frozenset(), repeated=frozenset()):
    """Pure exact option parser shared with the separate operator utility."""
    _need(type(values) in (list,tuple) and len(values)%2==0
          and all(type(value) is str for value in values), 'INCIDENT_CLI_ARGUMENTS_INVALID')
    result={name:[] for name in repeated}
    for key,value in zip(values[::2],values[1::2]):
        _need(key.startswith('--') and key[2:] in required|optional|repeated and value
              and not value.startswith('--') and '\x00' not in value, 'INCIDENT_CLI_ARGUMENTS_INVALID')
        name=key[2:]
        if name in repeated:
            _need(len(result[name])<128, 'INCIDENT_CLI_ARGUMENTS_INVALID')
            result[name].append(value)
        else:
            _need(name not in result, 'INCIDENT_CLI_ARGUMENTS_INVALID')
            result[name]=value
    _need(required<=set(result), 'INCIDENT_CLI_ARGUMENTS_REQUIRED')
    return result


def _arguments(argv):
    _need(type(argv) in (list,tuple) and argv and all(type(value) is str for value in argv),
          'INCIDENT_CLI_ARGUMENTS_INVALID')
    if tuple(argv) in (('--help',),('-h',)):
        return 'help',{}
    command=argv[0]
    _need(command!='provision', 'INCIDENT_OPERATOR_PROVISION_REQUIRED')
    _need(command in ('register','check','inspect','list-pending','incident-aware-select'),
          'INCIDENT_CLI_ARGUMENTS_INVALID')
    required=INCIDENT_OPTIONS
    if command in ('register','check','incident-aware-select'):
        required=required|_BUNDLE
    if command=='incident-aware-select':
        required=required|_SELECTION
    args=parse_options(argv[1:],required=required,
        optional=frozenset({'history-storage'}) if command=='incident-aware-select' else frozenset(),
        repeated=_REPEATED if command=='incident-aware-select' else frozenset())
    if 'digest' in args:
        _need(_HASH.fullmatch(args['digest']) is not None, 'INCIDENT_CLI_DIGEST_INVALID')
    return command,args


def open_incident_store(args):
    """Only explicit caller configuration; construction never provisions a head."""
    limits=parse_limits(read_file(args['incident-limits'],_LIMITS_BYTES))
    return IncidentStore(root=Path(args['incident-root']),backup_root=Path(args['incident-backup-root']),
        head_root=Path(args['incident-head-root']),head_name=args['incident-head-name'],limits=limits)


def diagnostic(exc):
    value=(exc.code if type(exc) is ProfileError else str(exc)
           if isinstance(exc,ValueError) and type(exc) is not ValueError else None)
    return value if type(value) is str and _CODE.fullmatch(value) else 'INCIDENT_CLI_INPUT_REFUSED'


def base_output():
    return {'status':'REFUSED','scope':'research_incident_observation','reasons':[],
        'execution_ready':False,'current_operational_use':False,'automatic_recovery_supported':False}


def _selection_inputs(args):
    audits=_audits(args['audit'])
    archive=read_file(args['archive-attestation'],bundle_attestation.MAX_DOCUMENT_BYTES)
    bundle_attestation.parse_attestation_document(archive)
    profile=parse_profile_json(read_file(args['profile'],MAX_CONFIG_BYTES))
    window=read_window(args['window'])
    storage=parse_policy(read_file(args['history-storage'],MAX_POLICY_BYTES)) if 'history-storage' in args else None
    reviews={}
    for path in args['source-review']:
        raw=read_file(path,MAX_DOCUMENT_BYTES)
        identifier=parse_review_document(raw)['body']['request']['study_id']
        _need(identifier not in reviews, 'INCIDENT_CLI_DUPLICATE_REVIEW')
        reviews[identifier]=raw
    return dict(archive_attestation=archive,source_reviews=reviews,audit_logical_ids=audits,
        current_profile=profile,window=window,history_head_root=Path(args['head-root']),history_storage_policy=storage)


def main(argv=None):
    try:
        command,args=_arguments(sys.argv[1:] if argv is None else argv)
        if command=='help':
            print(__doc__)
            return 0
        inputs=_selection_inputs(args) if command=='incident-aware-select' else None
        incidents=open_incident_store(args)
        output=base_output()
        def clock():
            return datetime.now(timezone.utc)
        if command in ('inspect','list-pending'):
            snapshot=incidents.inspect()
            output.update(incident_context_sha256=incidents.context_sha256,incident_head=snapshot.head,
                          incident_sequence=snapshot.sequence)
            if command=='inspect':
                output.update(status='INCIDENT_STORE_VERIFIED',registrations=[{
                    'store_binding_sha256':row.store_binding_sha256,'bundle_digest':row.bundle_digest,
                    'input_archive_digest':row.input_archive_digest,'bundle_kind':row.bundle_kind}
                    for row in snapshot.state.registrations],incident_count=len(snapshot.state.incidents),
                    pending_count=len(snapshot.state.pending_notifications),receipt_count=len(snapshot.state.receipts))
            else:
                output.update(status='NOTIFICATIONS_PENDING',pending_notifications=_plain(snapshot.state.pending_notifications),
                              network_delivery_performed=False)
        else:
            bundle=open_explicit_store(args['sealed-root'],args['backup-root'],args['head-name'],args['limits'])
            if command=='register':
                registration=register_target(incidents,bundle,args['digest'],clock=clock)
                output.update(status='TARGET_REGISTERED',**{name:getattr(registration,name) for name in
                    ('store_binding_sha256','bundle_digest','input_archive_digest','bundle_kind','graph_sha256',
                     'catalog_head_sha256','catalog_sequence')},dependency_count=len(registration.objects))
            elif command=='check':
                check=check_target(incidents,bundle,args['digest'],clock=clock)
                output.update(_plain(check))
                output['status']='TARGET_HELD' if check.held else 'TARGET_CHECKED'
            else:
                assessment=authenticate_incident_aware_selection(bundle,args['digest'],incident_store=incidents,
                    **inputs,clock=clock,authority_provider=CurrentOwnerAuthority(clock=clock))
                _need(type(assessment) is IncidentAwareSelectionAssessment
                      and assessment.execution_ready is False and assessment.current_operational_use is False
                      and assessment.automatic_recovery_supported is False, 'INCIDENT_CLI_RESULT_INVALID')
                output.update(_plain(assessment),scope='incident_aware_research_selection',
                              status=assessment.selection_assessment.selection.status)
        print(json.dumps(output,sort_keys=True,allow_nan=False))
        return 0
    except KeyboardInterrupt:
        code='INCIDENT_CLI_STOPPED'
    except (ValueError,OSError,RuntimeError,TypeError,AttributeError,ArithmeticError,RecursionError,KeyError) as exc:
        code=diagnostic(exc)
    output=base_output();output['reasons']=[code]
    print(json.dumps(output,sort_keys=True,allow_nan=False))
    return 2


if __name__=='__main__':
    raise SystemExit(main())
