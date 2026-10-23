"""Compliance suite aggregator (compliance plan Task 1; spec 8 "Setup").

`tests()` imports each module of MODULES that exists, wraps each `test_*` function defined in it and returns
`("<module>/<name>", wrapped)` pairs; `tests/run_all.py` prefixes them with `compliance/`. A wrapped test runs inside
`tests.macro_acceptance.hermetic()` (every network touchpoint raises) and `tests.compliance_fixtures.temp_home()`
(TRADEGEN_HOME is a fresh temp dir), and fails afterwards if the REAL `~/.tradegen/compliance` changed at all.

    .venv/Scripts/python.exe -m tests.compliance_acceptance [substring]

runs the entries whose name contains the substring (every entry without one). It never writes
qa/acceptance_results.json.
"""
from __future__ import annotations

import functools
import importlib
import os
import sys
from pathlib import Path
from typing import Callable

from tests.macro_acceptance import hermetic

TESTS = Path(__file__).resolve().parent
MODULES = ("compliance_guards", "compliance_isolation", "compliance_loader", "compliance_tables",
           "compliance_model", "compliance_gate", "compliance_owner", "compliance_store", "compliance_cli",
           "compliance_signer")
_REAL_HOME = Path.home() / ".tradegen" / "compliance"      # fixed at import: a test's TRADEGEN_HOME never moves it


def _real_listing() -> tuple:
    """(relative path, size, mtime_ns) of every folder and file under the real compliance home."""
    rows = [(".", 0, 0)] if _REAL_HOME.exists() else []
    for dirpath, dirnames, filenames in os.walk(_REAL_HOME):
        here = Path(dirpath)
        rows += [((here / n).relative_to(_REAL_HOME).as_posix() + "/", 0, 0) for n in dirnames]
        for name in filenames:
            st = (here / name).stat()
            rows.append(((here / name).relative_to(_REAL_HOME).as_posix(), st.st_size, st.st_mtime_ns))
    return tuple(sorted(rows))


def _wrap(fn: Callable[[], None]) -> Callable[[], None]:
    @functools.wraps(fn)
    def run() -> None:
        from tests.compliance_fixtures import temp_home
        before = _real_listing()
        try:
            with hermetic(), temp_home():
                fn()
        finally:
            after = _real_listing()
            if after != before:
                changed = sorted(set(before) ^ set(after))
                raise AssertionError(f"the test touched the real ~/.tradegen/compliance: {changed[:5]}")
    return run


def tests() -> list[tuple[str, Callable[[], None]]]:
    found = []
    for stem in MODULES:
        if not (TESTS / f"{stem}.py").is_file():
            continue                                   # a later task creates it
        try:
            module = importlib.import_module(f"tests.{stem}")
        except Exception as exc:                       # one broken module must not take down run_all
            def broken(exc=exc):
                raise exc
            found.append((f"{stem}/import", broken))
            continue
        for name, fn in sorted(vars(module).items()):
            # defined in the module: an imported helper such as the fixture `test_key` is not a test
            if name.startswith("test_") and callable(fn) and getattr(fn, "__module__", None) == module.__name__:
                found.append((f"{stem}/{name}", _wrap(fn)))
    return found


def _main(argv: list[str]) -> int:
    from tests.run_all import run                      # imports every suite, as `--suite` does
    pattern = argv[0] if argv else ""
    results = run([(n, f) for n, f in tests() if pattern in n])
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    not_run = sum(r["status"] == "NOT_RUN" for r in results)
    print(f"\n{passed}/{len(results)} passed, {failed} failed, {not_run} not run")
    return 0 if results and failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
