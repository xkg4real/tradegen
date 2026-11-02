"""Keyless KIS market-data tests; no shared QA write or real network attempt."""
from __future__ import annotations

import functools
import importlib
import sys
import threading
from unittest.mock import patch

from tests.control_acceptance import _wrap as isolated

MODULES = ("kis_live_catalog", "kis_live", "kis_live_ui", "kis_live_guards")


def _wrap(function):
    @functools.wraps(function)
    def run():
        attempts = []
        before = {id(t) for t in threading.enumerate() if t.name == "tradegen-kis-market"}
        def refused(*args, **kwargs):
            attempts.append("unexpected transport")
            raise AssertionError("KIS test attempted an unfaked transport")
        try:
            with patch("requests.sessions.Session.request", refused), \
                    patch("websockets.sync.client.connect", refused):
                function()
        finally:
            remaining = [t for t in threading.enumerate()
                         if t.name == "tradegen-kis-market" and id(t) not in before]
            assert not attempts, "KIS test swallowed an unfaked transport attempt"
            assert not remaining, "KIS test leaked a market-data worker"
    return isolated(run)


def tests():
    result = []
    for stem in MODULES:
        try:
            module = importlib.import_module("tests." + stem)
        except Exception as exc:
            def broken(exc=exc):
                raise exc
            result.append((stem + "/import", _wrap(broken)))
            continue
        for name, function in sorted(vars(module).items()):
            if name.startswith("test_") and callable(function) and getattr(function, "__module__", None) == module.__name__:
                result.append((stem + "/" + name, _wrap(function)))
    return result


def main(argv=None):
    from tests.run_all import run
    args = list(sys.argv[1:] if argv is None else argv)
    rows = run([(name, fn) for name, fn in tests() if not args or args[0] in name])
    counts = {status: sum(row["status"] == status for row in rows) for status in ("PASS", "FAIL", "NOT_RUN")}
    print(counts)
    return 0 if rows and counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
