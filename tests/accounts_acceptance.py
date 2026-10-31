"""Hermetic account-evidence/readiness function tests; no shared QA writes."""
from __future__ import annotations

import importlib
import sys

from tests.control_acceptance import _wrap

MODULES = ("accounts_guards", "accounts_provider", "accounts_readiness")


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
    selected = [(name, fn) for name, fn in tests() if not args or args[0] in name]
    rows = run(selected)
    counts = {status: sum(row["status"] == status for row in rows) for status in ("PASS", "FAIL", "NOT_RUN")}
    print(counts)
    return 0 if rows and counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
