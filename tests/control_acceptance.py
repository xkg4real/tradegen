"""Isolated E2/E3 function-test runner; never writes the shared QA result file.

    python -m tests.control_acceptance [substring]

E1's existing wrapper supplies a temporary TRADEGEN_HOME, empty inquiry key
source, no-network data seams and actual-home watches. This wrapper adds the E3
HTTP refusal seams and watches the new actual control directories as well.
"""
from __future__ import annotations

import functools
import importlib
import os
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
MODULES = ("control_guards", "control_model", "control_store", "control_risk", "control_session",
           "control_controller", "orders_codecs", "orders_transport", "orders_lifecycle")
_REAL = (Path.home() / ".tradegen" / "execution-control",
         Path.home() / ".tradegen" / "execution_orders")


def _listing() -> tuple:
    rows = []
    for root in _REAL:
        if root.exists():
            rows.append((str(root), 0, 0))
        for folder, dirs, files in os.walk(root):
            here = Path(folder)
            rows.extend((str(here / name) + "/", 0, 0) for name in dirs)
            for name in files:
                path = here / name
                stat = path.stat()
                rows.append((str(path), stat.st_size, stat.st_mtime_ns))
    return tuple(sorted(rows))


def _wrap(fn):
    from tests.execution_acceptance import _wrap as inquiry_wrap

    @functools.wraps(fn)
    def inner():
        from tests.control_fixtures import isolated
        before = _listing()
        try:
            with isolated(Path(os.environ["TRADEGEN_HOME"])):
                fn()
        finally:
            assert _listing() == before, "test changed a real execution-control home"
    return inquiry_wrap(inner)


def tests():
    found = []
    for stem in MODULES:
        if not (TESTS / (stem + ".py")).is_file():
            continue
        try:
            module = importlib.import_module("tests." + stem)
        except Exception as exc:
            def broken(exc=exc):
                raise exc
            found.append((stem + "/import", _wrap(broken)))
            continue
        for name, fn in sorted(vars(module).items()):
            if name.startswith("test_") and callable(fn) and getattr(fn, "__module__", None) == module.__name__:
                found.append((stem + "/" + name, _wrap(fn)))
    return found


def _main(argv):
    from tests.run_all import run
    pattern = argv[0] if argv else ""
    results = run([(name, fn) for name, fn in tests() if pattern in name])
    counts = {status: sum(row["status"] == status for row in results) for status in ("PASS", "FAIL", "NOT_RUN")}
    print(f"\n{counts['PASS']}/{len(results)} passed, {counts['FAIL']} failed, {counts['NOT_RUN']} not run")
    return 0 if results and counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
