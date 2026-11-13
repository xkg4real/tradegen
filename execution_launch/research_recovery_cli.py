"""Explicit archive recovery observations; never current trading eligibility.

python -m execution_launch.research_recovery_cli inspect --attempt-root ROOT --attempt-backup-root ROOT --attempt-head-root ROOT --attempt-head-name NAME --attempt-limits LIMITS.json

Commands: route-register, run-once, inspect, list-pending. Registration and run
require explicit incident, source and destination storage configuration plus the
original --archive-attestation file. Registration additionally requires --digest
and --source-head-name; run requires --route-id and --incident-id. Stores and
heads must already be provisioned. A completed record is historical evidence,
not a new check that its destination is still present or currently eligible.
No command signs, releases quarantine, sends a notification or activates orders.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from execution_control.owner_authority import CurrentOwnerAuthority
from execution_launch import bundle_attestation
from execution_launch.bundle_recovery import SignedBackupSource
from execution_launch.research_bundle import open_explicit_store, read_store_limits
from execution_launch.research_bundle_store import BundleRoots
from execution_launch.research_incident_cli import INCIDENT_OPTIONS, open_incident_store
from execution_launch.research_recovery import (RecoveryRouteConfig, RecoveryRouteObservation,
    RecoveryControllerObservation, register_recovery_route, run_recovery_once)
from execution_launch.research_recovery_store import RecoveryAttemptStore, parse_limits
from execution_launch.strategy import _plain
from execution_launch.workflow import _CODE, read_file

ATTEMPT_OPTIONS = frozenset({'attempt-root','attempt-backup-root','attempt-head-root',
                            'attempt-head-name','attempt-limits'})
_SOURCE = frozenset({'source-root','source-backup-root','source-limits'})
_DESTINATION = frozenset({'destination-root','destination-backup-root','destination-head-name','destination-limits'})
_HASH = re.compile(r'[0-9a-f]{64}')
_LIMITS_BYTES = 65536


class RecoveryCLIError(ValueError):
    """Fixed public diagnostics, without private paths, document bytes or OS text."""


def _need(condition, code):
    if not condition:
        raise RecoveryCLIError(code)


def parse_options(values, *, required):
    """Exact non-repeated explicit configuration; shared only with owner setup."""
    _need(type(values) in (list,tuple) and len(values)%2==0
          and all(type(value) is str for value in values), 'RECOVERY_CLI_ARGUMENTS_INVALID')
    result={}
    for key,value in zip(values[::2],values[1::2]):
        _need(key.startswith('--') and key[2:] in required and key[2:] not in result
              and value and not value.startswith('--') and '\x00' not in value,
              'RECOVERY_CLI_ARGUMENTS_INVALID')
        result[key[2:]]=value
    _need(set(result)==required, 'RECOVERY_CLI_ARGUMENTS_REQUIRED')
    return result


def _arguments(argv):
    _need(type(argv) in (list,tuple) and argv and all(type(value) is str for value in argv),
          'RECOVERY_CLI_ARGUMENTS_INVALID')
    if tuple(argv) in (('--help',),('-h',)):
        return 'help',{}
    command=argv[0]
    _need(command!='provision', 'RECOVERY_OPERATOR_PROVISION_REQUIRED')
    _need(command in ('route-register','run-once','inspect','list-pending'), 'RECOVERY_CLI_ARGUMENTS_INVALID')
    required=ATTEMPT_OPTIONS
    if command in ('route-register','run-once'):
        required=required|INCIDENT_OPTIONS|_SOURCE|_DESTINATION|{'archive-attestation'}
        required=required|({'digest','source-head-name'} if command=='route-register' else {'route-id','incident-id'})
    args=parse_options(argv[1:],required=required)
    for name in ('digest','route-id','incident-id'):
        if name in args:
            _need(_HASH.fullmatch(args[name]) is not None, 'RECOVERY_CLI_IDENTIFIER_INVALID')
    return command,args


def open_attempt_store(args):
    """Construction only, with no default root or genesis adoption."""
    limits=parse_limits(read_file(args['attempt-limits'],_LIMITS_BYTES))
    return RecoveryAttemptStore(root=Path(args['attempt-root']),backup_root=Path(args['attempt-backup-root']),
        head_root=Path(args['attempt-head-root']),head_name=args['attempt-head-name'],limits=limits)


def diagnostic(exc):
    value=str(exc) if isinstance(exc,ValueError) and type(exc) is not ValueError else None
    return value if type(value) is str and _CODE.fullmatch(value) else 'RECOVERY_CLI_INPUT_REFUSED'


def base_output():
    return {'status':'REFUSED','scope':'archive_recovery_observation','reasons':[],
        'source_authenticated':False,'research_selection_ready':False,'current_use_eligible':False,
        'execution_ready':False,'automatic_operational_recovery_supported':False,
        'quarantine_released':False,'quarantine_release_supported':False,
        'current_operational_eligibility_assessed':False,'network_delivery_performed':False,
        'record_semantics':'historical_observation_not_current_eligibility'}


def _archive(args):
    raw=read_file(args['archive-attestation'],bundle_attestation.MAX_DOCUMENT_BYTES)
    bundle_attestation.parse_attestation_document(raw)
    return raw


def _destination(args):
    return open_explicit_store(args['destination-root'],args['destination-backup-root'],
                               args['destination-head-name'],args['destination-limits'])


def main(argv=None):
    try:
        command,args=_arguments(sys.argv[1:] if argv is None else argv)
        if command=='help':
            print(__doc__)
            return 0
        # Original bounded document is required before any route/run work.
        document=_archive(args) if command in ('route-register','run-once') else None
        attempts=open_attempt_store(args)
        output=base_output()
        if command in ('inspect','list-pending'):
            snapshot=attempts.inspect()
            output.update(attempt_context_sha256=attempts.context_sha256,
                          attempt_head=snapshot.head,attempt_sequence=snapshot.sequence)
            if command=='inspect':
                output.update(status='RECOVERY_STORE_VERIFIED',route_count=len(snapshot.state.routes),
                    attempt_count=len(snapshot.state.attempts),receipt_count=len(snapshot.state.receipts),
                    pending_count=len(snapshot.state.pending_notifications),
                    routes=[{'route_id':row.route_id,'bundle_digest':row.registration.bundle_digest}
                            for row in snapshot.state.routes],
                    attempts=[{'attempt_id':row.attempt_id,'route_id':row.route_id,'incident_id':row.incident_id,
                               'phase':row.phase,'execution_count':row.execution_count,'terminal':row.terminal}
                              for row in snapshot.state.attempts])
            else:
                output.update(status='RECOVERY_NOTIFICATIONS_PENDING',
                              pending_notifications=_plain(snapshot.state.pending_notifications))
        else:
            incidents=open_incident_store(args)
            destination=_destination(args)
            def clock():
                return datetime.now(timezone.utc)
            authority=CurrentOwnerAuthority(clock=clock)
            if command=='route-register':
                source=open_explicit_store(args['source-root'],args['source-backup-root'],
                                           args['source-head-name'],args['source-limits'])
                observed=register_recovery_route(incidents,attempts,source,destination,args['digest'],document,
                    clock=clock,authority_provider=authority)
                _need(type(observed) is RecoveryRouteObservation, 'RECOVERY_CLI_RESULT_INVALID')
                output.update(_plain(observed),status='RECOVERY_ROUTE_REGISTERED')
            else:
                # The original primary can be absent. Never construct a replacement
                # BundleStore or obtain a new source identity to continue a route.
                source=SignedBackupSource(roots=BundleRoots(sealed_root=Path(args['source-root']),
                    backup_root=Path(args['source-backup-root'])),limits=read_store_limits(args['source-limits']))
                route=RecoveryRouteConfig(source=source,destination=destination)
                observed=run_recovery_once(incidents,attempts,route,route_id=args['route-id'],
                    incident_id=args['incident-id'],attestation_bytes=document,clock=clock,authority_provider=authority)
                _need(type(observed) is RecoveryControllerObservation
                    and all(getattr(observed,name) is False for name in
                        ('quarantine_released','current_use_eligible','research_selection_ready',
                         'execution_ready','automatic_operational_recovery_supported')),
                    'RECOVERY_CLI_RESULT_INVALID')
                output.update(_plain(observed),status='RECOVERY_ATTEMPT_OBSERVED')
        print(json.dumps(output,sort_keys=True,allow_nan=False))
        return 0
    except KeyboardInterrupt:
        code='RECOVERY_CLI_STOPPED'
    except (ValueError,OSError,RuntimeError,TypeError,AttributeError,ArithmeticError,RecursionError,KeyError) as exc:
        code=diagnostic(exc)
    output=base_output();output['reasons']=[code]
    print(json.dumps(output,sort_keys=True,allow_nan=False))
    return 2


if __name__=='__main__':
    raise SystemExit(main())
