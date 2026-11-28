"""Hermetic acceptance suite aggregator for `qlib_lab/` (Goal 3 Continuous Model Factory).

Aggregates:
- `qlib_lab_guards`
- `qlib_lab_expression_pit`
- `qlib_lab_data_handler`
- `qlib_lab_models`
- `qlib_lab_workflow_online`

Runs every test inside `tests.macro_acceptance.hermetic()` (blocking all network touchpoints) and
`tests.compliance_fixtures.temp_home()`, asserting before and after every test that neither real
`~/.tradegen` nor `~/.nextgen` was created or modified. Never writes `qa/acceptance_results.json`.
"""
from __future__ import annotations

import functools
import importlib
import os
from pathlib import Path
import sys
import time
import traceback
from typing import Callable

from tests.macro_acceptance import hermetic
from tests.notrun import NotRun

TESTS_DIR = Path(__file__).resolve().parent
MODULES = (
    "qlib_lab_guards",
    "qlib_lab_expression_pit",
    "qlib_lab_data_handler",
    "qlib_lab_models",
    "qlib_lab_workflow_online",
)

_REAL_TRADEGEN = Path.home() / ".tradegen"
_REAL_NEXTGEN = Path.home() / ".nextgen"


def _dir_snapshot(root: Path) -> tuple:
    if not root.exists():
        return ()
    rows = [(".", 0, 0)]
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        rows.extend(((here / d).relative_to(root).as_posix() + "/", 0, 0) for d in dirnames)
        for fname in filenames:
            st = (here / fname).stat()
            rows.append(((here / fname).relative_to(root).as_posix(), st.st_size, st.st_mtime_ns))
    return tuple(sorted(rows))


def _wrap(fn: Callable[[], None]) -> Callable[[], None]:
    @functools.wraps(fn)
    def _runner() -> None:
        from tests.compliance_fixtures import temp_home

        tg_before = _dir_snapshot(_REAL_TRADEGEN)
        ng_before = _dir_snapshot(_REAL_NEXTGEN)
        try:
            with hermetic(), temp_home():
                fn()
        finally:
            tg_after = _dir_snapshot(_REAL_TRADEGEN)
            ng_after = _dir_snapshot(_REAL_NEXTGEN)
            if tg_after != tg_before:
                raise AssertionError(f"Test touched real ~/.tradegen: {sorted(set(tg_before) ^ set(tg_after))[:5]}")
            if ng_after != ng_before:
                raise AssertionError(f"Test touched real ~/.nextgen: {sorted(set(ng_before) ^ set(ng_after))[:5]}")

    return _runner


def tests() -> list[tuple[str, Callable[[], None]]]:
    found: list[tuple[str, Callable[[], None]]] = []
    for stem in MODULES:
        try:
            module = importlib.import_module(f"tests.{stem}")
        except Exception as exc:
            def _broken(exc: Exception = exc) -> None:
                raise exc
            found.append((f"{stem}/import", _broken))
            continue

        for name, fn in sorted(vars(module).items()):
            if name.startswith("test_") and callable(fn) and getattr(fn, "__module__", None) == module.__name__:
                found.append((f"{stem}/{name}", _wrap(fn)))
    return found


def _run_entries(entries: list[tuple[str, Callable[[], None]]]) -> list[dict]:
    results = []
    for name, fn in entries:
        started = time.perf_counter()
        row = {"test": name, "status": "PASS", "seconds": 0.0, "detail": ""}
        try:
            fn()
        except NotRun as exc:
            row["status"], row["reason"] = "NOT_RUN", exc.reason
        except Exception as exc:
            row["status"], row["detail"] = "FAIL", f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
        row["seconds"] = round(time.perf_counter() - started, 4)
        results.append(row)
        print(f"{row['status']} {name} ({row['seconds']:.3f}s) {row['detail'] or row.get('reason', '')}".rstrip(), flush=True)
    return results


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    pattern = args[0] if args else ""
    selected = [(n, f) for n, f in tests() if pattern in n]
    results = _run_entries(selected)
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    not_run = sum(r["status"] == "NOT_RUN" for r in results)
    print(f"\n{passed}/{len(results)} passed, {failed} failed, {not_run} not run", flush=True)
    return 0 if results and failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
