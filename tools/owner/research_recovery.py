"""Explicit one-time provisioning of independent recovery attempt storage.

python -m tools.owner.research_recovery provision --attempt-root ROOT --attempt-backup-root ROOT --attempt-head-root ROOT --attempt-head-name NAME --attempt-limits LIMITS.json

All roots must already exist, be separate and empty. Existing or interrupted
records are preserved and refused. This initializes only storage genesis, never
owner approval, recovery-route adoption, quarantine release or trading authority.
"""
from __future__ import annotations

import json
import sys

from execution_launch.research_recovery_cli import (ATTEMPT_OPTIONS,RecoveryCLIError,
    parse_options,open_attempt_store,diagnostic,base_output)
from execution_launch.research_recovery_store import RecoveryAttemptStore


def provision_recovery_attempt_store(store):
    if type(store) is not RecoveryAttemptStore:
        raise RecoveryCLIError('RECOVERY_ATTEMPT_STORE_REQUIRED')
    store.provision_empty()
    # The sole explicit operator boundary; runtime routes never call this helper.
    store.head.initialize_reviewed_head(store.genesis_digest)
    snapshot=store.inspect()
    if (store.head.read()!=store.genesis_digest or snapshot.head!=store.genesis_digest
            or snapshot.sequence!=0 or snapshot.state.events):
        raise RecoveryCLIError('RECOVERY_PROVISION_READBACK_FAILED')
    return store.genesis_digest


def main(argv=None):
    try:
        values=sys.argv[1:] if argv is None else argv
        if not (type(values) in (list,tuple) and values and all(type(value) is str for value in values)
                and values[0]=='provision'):
            raise RecoveryCLIError('RECOVERY_OPERATOR_ARGUMENTS_INVALID')
        args=parse_options(values[1:],required=ATTEMPT_OPTIONS)
        store=open_attempt_store(args)
        genesis=provision_recovery_attempt_store(store)
        output=base_output()
        output.update(status='EMPTY_RECOVERY_STORE_PROVISIONED',genesis_digest=genesis,
                      attempt_context_sha256=store.context_sha256)
        print(json.dumps(output,sort_keys=True,allow_nan=False))
        return 0
    except KeyboardInterrupt:
        code='RECOVERY_OPERATOR_STOPPED'
    except (ValueError,OSError,RuntimeError,TypeError,AttributeError,ArithmeticError,RecursionError,KeyError) as exc:
        code=diagnostic(exc)
    output=base_output();output['reasons']=[code]
    print(json.dumps(output,sort_keys=True,allow_nan=False))
    return 2


if __name__=='__main__':
    raise SystemExit(main())
