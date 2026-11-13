"""Explicit one-time creation of an independent research incident namespace.

python -m tools.owner.research_incidents provision --incident-root ROOT --incident-backup-root ROOT --incident-head-root ROOT --incident-head-name NAME --incident-limits LIMITS.json

All three directories must be explicit, separate and empty under the store's
policy. Existing or interrupted records are preserved and refused. This creates
storage genesis only, never research approval, recovery adoption or a release of
earlier holds. Replacing an entire namespace is not protected continuation.
"""
from __future__ import annotations

import json
import sys

from execution_launch.research_incident_cli import (INCIDENT_OPTIONS,IncidentCLIError,
    parse_options,open_incident_store,diagnostic,base_output)
from execution_launch.research_incident_store import IncidentStore


def provision_incident_store(store):
    if type(store) is not IncidentStore:
        raise IncidentCLIError('INCIDENT_STORE_REQUIRED')
    store.provision_empty()
    # Explicit operator boundary only; never called by the runtime monitor.
    store.head.initialize_reviewed_head(store.genesis_digest)
    snapshot=store.inspect()
    if (store.head.read()!=store.genesis_digest or snapshot.head!=store.genesis_digest
            or snapshot.sequence!=0 or snapshot.state.events):
        raise IncidentCLIError('INCIDENT_PROVISION_READBACK_FAILED')
    return store.genesis_digest


def main(argv=None):
    try:
        values=sys.argv[1:] if argv is None else argv
        if not (type(values) in (list,tuple) and values and all(type(value) is str for value in values)
                and values[0]=='provision'):
            raise IncidentCLIError('INCIDENT_OPERATOR_ARGUMENTS_INVALID')
        args=parse_options(values[1:],required=INCIDENT_OPTIONS)
        store=open_incident_store(args)
        genesis=provision_incident_store(store)
        output=base_output()
        output.update(status='EMPTY_INCIDENT_STORE_PROVISIONED',genesis_digest=genesis,
                      incident_context_sha256=store.context_sha256)
        print(json.dumps(output,sort_keys=True,allow_nan=False))
        return 0
    except KeyboardInterrupt:
        code='INCIDENT_OPERATOR_STOPPED'
    except (ValueError,OSError,RuntimeError,TypeError,AttributeError,ArithmeticError,RecursionError,KeyError) as exc:
        code=diagnostic(exc)
    output=base_output();output['reasons']=[code]
    print(json.dumps(output,sort_keys=True,allow_nan=False))
    return 2


if __name__=='__main__':
    raise SystemExit(main())
