"""Explicit one-time research-store provisioning; no signing, recovery or orders.

python -m tools.owner.research_bundle provision --sealed-root ROOT --backup-root ROOT --head-name NAME --limits FILE.json

Both roots must already be empty local directories. An existing or interrupted
store is preserved and refused. This initializes a storage genesis only, never
owner approval of research evidence or trust in a source.
"""
from __future__ import annotations

import json
import sys

from execution_launch.research_bundle import ResearchBundleError, _code, open_explicit_store
from execution_launch.research_bundle_store import BundleStore


def provision_research_store(store):
    if type(store) is not BundleStore:
        raise ResearchBundleError("BUNDLE_STORE_REQUIRED")
    store.provision_empty()
    # This is the explicit operator boundary. Runtime finalize/read/evaluate
    # never call initialization, adoption or head repair.
    store.head.initialize_reviewed_head(store.genesis_digest)
    if store.head.read() != store.genesis_digest:
        raise ResearchBundleError("BUNDLE_PROVISION_READBACK_FAILED")
    return store.genesis_digest


def main(argv=None):
    try:
        argv = sys.argv[1:] if argv is None else argv
        required = {"sealed-root", "backup-root", "head-name", "limits"}
        if not (type(argv) in (list, tuple) and len(argv) == 9 and argv[0] == "provision"
                and all(type(value) is str for value in argv)):
            raise ResearchBundleError("BUNDLE_OPERATOR_ARGUMENTS_INVALID")
        args = {}
        for key, value in zip(argv[1::2], argv[2::2]):
            if not (key.startswith("--") and key[2:] in required and key[2:] not in args
                    and value and not value.startswith("--")):
                raise ResearchBundleError("BUNDLE_OPERATOR_ARGUMENTS_INVALID")
            args[key[2:]] = value
        store = open_explicit_store(args["sealed-root"], args["backup-root"], args["head-name"], args["limits"])
        genesis = provision_research_store(store)
        print(json.dumps({"status": "EMPTY_STORE_PROVISIONED", "genesis_digest": genesis,
            "manifest_authenticated": False, "execution_ready": False}, sort_keys=True))
        return 0
    except (ValueError, OSError, TypeError, AttributeError, ArithmeticError, RecursionError) as exc:
        print(json.dumps({"status": "REFUSED", "reasons": [_code(exc)],
                          "manifest_authenticated": False, "execution_ready": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
