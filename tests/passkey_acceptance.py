"""Run the independent passkey package tests with its own pinned environment.

    <broker-venv>/bin/python -m tests.passkey_acceptance

This does not import the app's acceptance registry or write its shared QA file.
It verifies pure registration/assertion primitives, not operating authority.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import socket
import time
from unittest.mock import patch


MODULES = ("launch_passkey_contract", "launch_passkey_webauthn")
KEYS = """KIS_APP_KEY KIS_APP_SECRET KIS_ACCOUNT_8 KIS_ACCOUNT_PD UPBIT_ACCESS_KEY
UPBIT_SECRET_KEY OKX_API_KEY OKX_API_SECRET OKX_API_PASSPHRASE OPENDART_API_KEY KRX_API_KEY
FMP_API_KEY ANTHROPIC_API_KEY GS_CLIENT_ID GS_CLIENT_SECRET FINVIZ_API_KEY ALPACA_API_KEY
ALPACA_SECRET_KEY FXMACRODATA_API_KEY""".split()


def _metadata():
    result = []
    for name in (".tradegen", ".nextgen"):
        root = Path.home() / name
        rows = [(p.relative_to(root).as_posix(), p.stat().st_size, p.stat().st_mtime_ns)
                for p in sorted(root.rglob("*")) if p.is_file()] if root.exists() else []
        result.append(rows)
    return result


def _no_network(*args, **kwargs):
    raise AssertionError("PASSKEY_TEST_NETWORK_FORBIDDEN")


def tests():
    entries = []
    for stem in MODULES:
        module = importlib.import_module("tests." + stem)
        entries.extend((stem + "/" + name, function)
                       for name, function in sorted(vars(module).items())
                       if name.startswith("test_") and callable(function)
                       and getattr(function, "__module__", None) == module.__name__)
    return entries


def run_entries():
    for key in KEYS:
        os.environ[key] = "<unset>"
    before = _metadata()  # No file contents, before test imports/discovery.
    rows = []
    try:
        with patch.object(socket.socket, "connect", _no_network), \
                patch.object(socket.socket, "connect_ex", _no_network), \
                patch.object(socket, "create_connection", _no_network):
            for name, function in tests():
                started = time.perf_counter()
                row = dict(test=name, status="PASS", seconds=0.0, detail="")
                try:
                    function()
                except Exception as exc:
                    row.update(status="FAIL", detail=type(exc).__name__ + ": " + str(exc))
                row["seconds"] = round(time.perf_counter() - started, 6)
                rows.append(row)
    finally:
        if before != _metadata():
            raise AssertionError("PASSKEY_TEST_REAL_HOME_METADATA_CHANGED")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, help="explicit development result file")
    args = parser.parse_args(argv)
    rows = run_entries()
    if not rows:
        raise AssertionError("PASSKEY_TEST_REGISTRY_EMPTY")
    if args.results is not None:
        args.results.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ("PASS", "FAIL", "NOT_RUN")}
    print(json.dumps(dict(total=len(rows), counts=counts,
                         failures=[row for row in rows if row["status"] == "FAIL"])))
    return int(bool(counts["FAIL"]))


if __name__ == "__main__":
    raise SystemExit(main())
