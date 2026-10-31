"""Execution suite aggregator (E1 plan Task 1; E1 spec 9; contract section 3.1).

`tests()` imports each module of MODULES that exists, wraps each `test_*` function defined in it and returns
`("<module>/<name>", wrapped)` pairs; `tests/run_all.py` prefixes them with `execution/`. A wrapped test runs inside
`tests.macro_acceptance.hermetic()` (every network touchpoint raises), `tests.compliance_fixtures.temp_home()`
(TRADEGEN_HOME is a fresh temp dir) and `tests.execution_fixtures.isolated()` (no E1 key name in the environment, the
toast recorder, and from Task 2 the refusing transport send). It fails afterwards if the REAL `~/.tradegen/execution`,
`~/.tradegen/compliance` or `~/.tradegen/kis_token.json` changed; while another process holds the real
`execution/poll.lock` (the owner's poller, which appends and refreshes the token), only the set of paths under
`execution/` and the token file counts, and the poller's daily `inquiry-YYYYMMDD.jsonl` files are left out.

    .venv/Scripts/python.exe -m tests.execution_acceptance [substring]

runs the entries whose name contains the substring (every entry without one). It never writes
qa/acceptance_results.json. Nothing from `execution` or `tests.execution_fixtures` is imported at module level, so a
half-built module is one `<module>/import` entry, never a broken `tests/run_all.py`.
"""
from __future__ import annotations

import functools
import importlib
import os
import re
import sys
from pathlib import Path
from typing import Callable

from tests.macro_acceptance import hermetic

TESTS = Path(__file__).resolve().parent
MODULES = ("execution_guards", "execution_keys", "execution_transport", "execution_snapshot", "execution_kis",
           "execution_upbit", "execution_okx", "execution_positions", "execution_evidence", "execution_checks",
           "execution_poll")
_REAL = (Path.home() / ".tradegen" / "execution", Path.home() / ".tradegen" / "compliance",
         Path.home() / ".tradegen" / "kis_token.json")      # fixed at import: a test's TRADEGEN_HOME never moves it
_DAILY = re.compile(r"inquiry-\d{8}\.jsonl")                    # the poller starts one each Seoul midnight (E30)


def _poller_running() -> bool:
    """True when another handle holds `_REAL[0] / "poll.lock"`. A read-only probe: it opens the lock only when it
    exists (never creating it) and releases its own lock at once. On Windows it holds byte 0 for a moment, so
    poll.held_lock tries 5 times, 0.2 s apart (Task 12), and a poller starting in that instant still takes it."""
    lock = _REAL[0] / "poll.lock"
    if not lock.is_file():
        return False
    with open(lock, "rb") as fh:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBRLCK, 1)
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_SH | fcntl.LOCK_NB)
                fcntl.flock(fh, fcntl.LOCK_UN)
        except OSError:                                 # PermissionError (msvcrt) or BlockingIOError (fcntl): held
            return True
    return False


def _real_listing(paths_only: bool) -> tuple:
    """(path, size, mtime_ns) of every folder and file under the real execution and compliance homes, and of the real
    KIS token file; an absent entry, or a file gone between the walk and its stat, adds nothing. With `paths_only`,
    the execution home and the token file give (path, 0, 0) rows and leave the daily inquiry files out; the
    compliance home is always listed in full."""
    rows = []
    for entry in _REAL:
        loose = paths_only and entry != _REAL[1]
        files = [entry] if entry.is_file() else []
        if entry.is_dir():
            rows.append((entry.as_posix() + "/", 0, 0))
            for dirpath, dirnames, filenames in os.walk(entry):
                here = Path(dirpath)
                rows += [((here / n).as_posix() + "/", 0, 0) for n in dirnames]
                files += [here / n for n in filenames if not (loose and _DAILY.fullmatch(n))]
        for path in files:
            if loose:
                rows.append((path.as_posix(), 0, 0))
            else:
                try:
                    st = path.stat()
                except FileNotFoundError:               # replaced away since the walk (a --mark-sent temp file)
                    continue
                rows.append((path.as_posix(), st.st_size, st.st_mtime_ns))
    return tuple(sorted(rows))


def _wrap(fn: Callable[[], None]) -> Callable[[], None]:
    @functools.wraps(fn)
    def run() -> None:
        from tests.compliance_fixtures import temp_home
        from tests.execution_fixtures import isolated
        running = _poller_running()
        before = _real_listing(False), _real_listing(True)
        try:
            with hermetic(), temp_home() as home, isolated(home):
                fn()
        finally:
            pick = 1 if running or _poller_running() else 0
            after = _real_listing(False), _real_listing(True)
            if after[pick] != before[pick]:
                changed = sorted(set(before[pick]) ^ set(after[pick]))
                raise AssertionError(f"the test touched the real ~/.tradegen: {changed[:5]}")
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
            # defined in the module: an imported helper is not a test
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
