"""Odds suite aggregator (odds plan Task 1; contract section 3.1; RULINGS O13).

`tests()` imports each module of MODULES that exists, wraps each `test_*` function defined in it and returns
`("<module>/<name>", wrapped)` pairs; `tests/run_all.py` prefixes them with `odds/`. A wrapped test runs inside
`tests.macro_acceptance.hermetic()` (every network touchpoint raises) and `tests.compliance_fixtures.temp_home()`
(TRADEGEN_HOME is a fresh temp dir), and, once `core/oddsdata/bars.py` exists, with its four data seams set to
`tests.macro_acceptance._boom`; the real seam functions are kept in REAL_SEAMS for the seam-body tests. It fails
afterwards if the REAL `~/.tradegen/odds` or `~/.tradegen/compliance` changed at all, or if a repo file the suite
only reads (`_REPO_FILES`) changed.

    .venv/Scripts/python.exe -m tests.odds_acceptance [substring]

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
MODULES = ("odds_guards", "odds_plan", "odds_costs", "odds_models", "odds_garch", "odds_simulate", "odds_locks",
           "odds_bold", "odds_report", "odds_pipeline", "odds_columns", "odds_bars", "odds_inputs", "odds_replay",
           "odds_cli")
_REAL_HOMES = (Path.home() / ".tradegen" / "odds", Path.home() / ".tradegen" / "compliance")   # fixed at import
_REPO_FILES = ("core/odds/venues.yaml", "docs/asset_expansion/cache/upbit_KRW-BTC.csv",
               "docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json", "docs/asset_expansion/results.csv")
_BARS = TESTS.parent / "core" / "oddsdata" / "bars.py"   # the seams are patched once this file exists (Task 15)
SEAMS = ("_kis_daily", "_upbit_daily", "_binance_daily", "_yf_download")
REAL_SEAMS: dict[str, Callable] = {}    # the real seam functions, filled from vars(bars) the first time _wrap patches


def _real_listing() -> tuple:
    """(root index, relative path, size, mtime_ns) of every folder and file under every _REAL_HOMES entry."""
    rows = []
    for i, root in enumerate(_REAL_HOMES):
        rows += [(i, ".", 0, 0)] if root.exists() else []
        for dirpath, dirnames, filenames in os.walk(root):
            here = Path(dirpath)
            rows += [(i, (here / n).relative_to(root).as_posix() + "/", 0, 0) for n in dirnames]
            for name in filenames:
                st = (here / name).stat()
                rows.append((i, (here / name).relative_to(root).as_posix(), st.st_size, st.st_mtime_ns))
    return tuple(sorted(rows))


def _repo_listing() -> tuple:
    """(path, size, mtime_ns) of every _REPO_FILES entry; (path, -1, -1) for a missing one."""
    rows = []
    for rel in _REPO_FILES:
        path = TESTS.parent / rel
        st = path.stat() if path.is_file() else None
        rows.append((rel, st.st_size, st.st_mtime_ns) if st else (rel, -1, -1))
    return tuple(rows)


def _patch_seams() -> tuple:
    """Set every SEAMS name of core.oddsdata.bars to macro_acceptance._boom, recording each real function in
    REAL_SEAMS the first time; returns (bars, [(name, saved value)]) for _restore_seams, (None, []) before Task 15."""
    if not _BARS.is_file():
        return None, []
    from tests.macro_acceptance import _MISSING, _boom
    bars = importlib.import_module("core.oddsdata.bars")
    saved = []
    for name in SEAMS:
        current = vars(bars).get(name, _MISSING)
        saved.append((name, current))
        if current is not _MISSING and current is not _boom:
            REAL_SEAMS.setdefault(name, current)
        setattr(bars, name, _boom)
    return bars, saved


def _restore_seams(patched: tuple) -> None:
    """Undo _patch_seams in reverse order; a name that was missing is deleted again."""
    from tests.macro_acceptance import _MISSING
    bars, saved = patched
    for name, original in reversed(saved):
        if original is _MISSING:
            delattr(bars, name)
        else:
            setattr(bars, name, original)


def _wrap(fn: Callable[[], None]) -> Callable[[], None]:
    @functools.wraps(fn)
    def run() -> None:
        from tests.compliance_fixtures import temp_home
        homes, files = _real_listing(), _repo_listing()
        try:
            with hermetic(), temp_home():
                patched = _patch_seams()
                try:
                    fn()
                finally:
                    _restore_seams(patched)
        finally:
            for before, after, what in ((homes, _real_listing(), "touched the real ~/.tradegen/odds or compliance"),
                                        (files, _repo_listing(), "changed a repo file it may only read")):
                if after != before:
                    changed = sorted(set(before) ^ set(after))
                    raise AssertionError(f"the test {what}: {changed[:5]}")
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
            # defined in the module: an imported helper whose name starts with test_ is not a test
            if name.startswith("test_") and callable(fn) and getattr(fn, "__module__", None) == module.__name__:
                found.append((f"{stem}/{name}", _wrap(fn)))
    return found


def _main(argv: list[str]) -> int:
    # Under `-m` this file runs as __main__, a second copy of the module. The tests read REAL_SEAMS and patch
    # _REAL_HOMES on the imported tests.odds_acceptance, so the entries come from that copy.
    from tests import odds_acceptance as suite
    from tests.run_all import run                      # imports every suite, as `--suite` does
    pattern = argv[0] if argv else ""
    results = run([(n, f) for n, f in suite.tests() if pattern in n])
    passed = sum(r["status"] == "PASS" for r in results)
    failed = sum(r["status"] == "FAIL" for r in results)
    not_run = sum(r["status"] == "NOT_RUN" for r in results)
    print(f"\n{passed}/{len(results)} passed, {failed} failed, {not_run} not run")
    return 0 if results and failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
