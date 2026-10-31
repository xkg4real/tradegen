"""Offline account-connection diagnostics; no probe, credentials, owner log or order.

    python -m execution_accounts.cli
    python -m execution_accounts.cli --configuration-manifest

The optional JSON paths must be non-secret metadata snapshots. This command never
loads .env, imports the owner signer or starts an E1 poll. The library's explicit
inquiry adapter is separate from this zero-side-effect status command.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path

from execution_accounts.readiness import configuration_manifest, inspect_configuration

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_POLICY = Path("/etc/codex/network-policy.json")
_MAX_METADATA_BYTES = 131072


def _metadata(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    if (path.suffix != ".json" or any(p.is_symlink() or p.is_junction() for p in (path, *path.parents))
            or not path.is_file()
            or path.stat().st_size > _MAX_METADATA_BYTES
            or any(path.resolve().is_relative_to((Path.home() / name).resolve())
                   for name in (".tradegen", ".nextgen"))):
        raise ValueError("METADATA_FILE_REFUSED")
    raw = path.read_bytes()
    if len(raw) > _MAX_METADATA_BYTES:
        raise ValueError("METADATA_FILE_REFUSED")
    def pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise ValueError("METADATA_JSON_REFUSED")
            output[key] = value
        return output
    parsed = json.loads(raw, object_pairs_hook=pairs,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("METADATA_JSON_REFUSED")))
    if type(parsed) is not dict:
        raise ValueError("METADATA_JSON_REFUSED")
    return parsed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configuration-manifest", action="store_true")
    parser.add_argument("--runtime-status", type=Path, help="non-secret current Cloud runtime-status JSON")
    parser.add_argument("--network-policy", type=Path, default=_DEFAULT_POLICY, help="non-secret network-policy JSON")
    args = parser.parse_args(argv)
    try:
        if args.configuration_manifest:
            print(json.dumps(configuration_manifest(), sort_keys=True))
            return 0
        report = inspect_configuration(present_names=os.environ,
            owner_public_key_present=(_ROOT / "core/compliance/owner_pubkey.pem").is_file(),
            runtime_status=_metadata(args.runtime_status), policy_snapshot=_metadata(args.network_policy))
        print(json.dumps(asdict(report), sort_keys=True))
        return 2  # Status is diagnostic only and never establishes execution readiness.
    except (OSError, ValueError, TypeError, RecursionError):
        print(json.dumps({"error": "READINESS_METADATA_UNAVAILABLE", "execution_ready": False}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
