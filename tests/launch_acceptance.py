"""First-trade foundation tests; hermetic E1/E3 seams and temporary state."""
from __future__ import annotations

import importlib
import sys

from tests.control_acceptance import _wrap

MODULES = ("launch_guards", "network_route", "accounts_collector", "launch_profile",
           "launch_strategy", "launch_runner", "launch_cli")


def tests():
    found = []
    for stem in MODULES:
        try:
            module = importlib.import_module("tests." + stem)
        except Exception as exc:
            def broken(exc=exc):
                raise exc
            found.append((stem + "/import", _wrap(broken)))
            continue
        for name, function in sorted(vars(module).items()):
            if name.startswith("test_") and callable(function) and getattr(function, "__module__", None) == module.__name__:
                found.append((stem + "/" + name, _wrap(function)))
    return found


def main(argv=None):
    from tests.run_all import run
    args = list(sys.argv[1:] if argv is None else argv)
    rows = run([(name, fn) for name, fn in tests() if not args or args[0] in name])
    counts = {status: sum(row["status"] == status for row in rows) for status in ("PASS", "FAIL", "NOT_RUN")}
    print(counts)
    return 0 if rows and counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
