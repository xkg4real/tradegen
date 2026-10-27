### Task 1: Branch, ledger, package skeleton, execution suite, guard widening

**Files:**
- Create: `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (LF, UTF-8, no BOM)
- Create: `execution/__init__.py` (0 bytes)
- Create: `tests/execution_acceptance.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_fixtures.py` (LF, UTF-8, no BOM)
- Create: `tests/execution_guards.py` (LF, UTF-8, no BOM)
- Modify: `tests/acceptance.py` (anchors: the head of `runtime_py()`; the head of `test_09_no_account_credentials_requested`; CRLF, keep CRLF)
- Modify: `tests/macro_m0_harness.py` (anchors: the `FORBIDDEN_TEXT_CS` / `FORBIDDEN_PATH_RE` pair; the three `hits` lines of `_offences`; LF)
- Modify: `core/ficc/context_log.py` (anchor: the `ACTING_MODULE_PREFIXES` tuple; LF)
- Modify: `tests/run_all.py` (anchors: the `from tests.notrun import NotRun` import; the last term of `tests()`; the `--suite` line of `main()`; CRLF, keep CRLF)
- Modify: `README.md` (anchor: the `--suite macro` line of the Verification block, hint :816; CRLF, keep CRLF)
- Test: `tests/execution_guards.py`

**Interfaces:**
- Consumes (repo, read at `5816d3c`; `_suite_names`, `pubkey_at` and `full_home` arrive with the earlier plans; the
  DRIFT RULE of contract 0.6 covers every name here):
  - `tests.macro_acceptance.hermetic()` (re-entrant context manager, tests/macro_acceptance.py:74-98) and
    `tests.macro_acceptance._DEPTH: int`.
  - `tests.compliance_fixtures.temp_home() -> Iterator[Path]` (tests/compliance_fixtures.py:15-31: a fresh
    `tradegen_home_*` dir as TRADEGEN_HOME; clears `isolation._LINK_SCAN` on the way in and out).
  - `tests.compliance_guards` as `CG`: `_sources(*bases: Path) -> dict[str, str]`, `_walk(node, funcs=())` (yields
    `(node, names of the functions whose BODY encloses it)`), `_imports(rel, tree)` (yields `(node, absolute module,
    imported names, funcs)`), `_raw_hits(rel, src, ci, cs)`, `_def_hits(rel, src)`, `_dynamic_hits(rel, src)` (the
    follow-up's rewrite), `_main_block_hits(rel, src)`, `_init_hits(path)`, `CLOCKS`, and the follow-up's
    `_suite_names(text: str) -> list[str]` (the names of the first `one suite: a, b or c` line).
  - `tests.run_all.run(entries) -> list[dict]`, `tests.run_all.tests()`, `tests.run_all.select(entries, *,
    milestone=None, suite=None)`.
  - `tests.acceptance.ROOT`, `runtime_py() -> list[Path]`, `test_08_no_broker_order_path()`,
    `test_09_no_account_credentials_requested()`; each reads the module global `ROOT` at call time, so swapping
    `tests.acceptance.ROOT` moves them to a fake root.
  - `tests.macro_m0_harness.ROOT`, `_offences(path: Path) -> list[str]` (text hits read `"<rel>: '<needle>'"`, an
    import hit `"<rel>:<line>: import <name>"`), `FORBIDDEN_PATH_RE`.
  - `core.ficc.context_log`: `ACTING_MODULE_PREFIXES`, `is_acting_module(name) -> bool`,
    `assert_not_acting_caller()` (walks every frame and raises on an acting module's frame), `ContextIsolationError`,
    `static_isolation_report() -> list`.
  - `core.compliance.alerts._toast(title: str, body: str) -> bool` (the P26 seam, core/compliance/alerts.py:216).
- Produces (later tasks rely on these exact names):
  - `execution/__init__.py`, 0 bytes.
  - `tests/execution_acceptance.py`: `TESTS: Path`, `MODULES` (the eleven stems of contract 3.1, `execution_guards`
    first), `_REAL` (the real execution home, compliance home and `kis_token.json`, fixed at import), `_DAILY`,
    `_poller_running() -> bool`, `_real_listing(paths_only: bool) -> tuple`, `_wrap(fn)`, `tests()`,
    `_main(argv: list[str]) -> int`; the command `.venv/Scripts/python.exe -m tests.execution_acceptance <substring>`.
  - `tests/execution_fixtures.py`: `NOW`, `DATE_HEADER`, `FAKE_KEYS`, `KEY_NAMES`, `_MISSING`,
    `class Refused(RuntimeError)`, `TOASTS`, `SLEEPS`, `STRAYS`, `REAL_SEND = None`, `_record_toast(title, body)`,
    and `isolated(home: Path)` (context manager). Task 2 extends `isolated()` at two anchors: the line
    `from core.compliance import alerts` (its lazy `execution.transport` and `execution.keys` imports go beside it)
    and the line `patches = [(alerts, "_toast", _record_toast)]` (its seams join that list, so the same loop saves
    them, `vars(obj).get(name, _MISSING)`, and restores them in reverse order).
  - `tests/execution_guards.py`: `ROOT`, `EXECUTION`, `INIT`, `X`, `RAW_BANNED`, `STDLIB`, `VERBS`, `CLOCK_MAIN`,
    `TRANSPORT`, `EVIDENCE_WRITER`, `CG`, `A` (tests.acceptance), `H` (tests.macro_m0_harness), and the helpers
    `_sources()`, `_test_sources()`, `_raw_hits`, `_allowlist_hits`, `_verb_hits`, `_clock_hits`, `_write_hits`,
    `_evidence_hits`, `_process_hits` (private: `_os_process`, `_modules`, `_checked`, `_writes`, `_allowed`,
    `_probe_root`, `_swapped_root`, `_passes`, `_verdicts`, `_flagged`, `_append`, `_held`, `_top_imports`); 18 tests.
    Task 2 appends its own constants of contract 4.5 (`KIS_ORDER_WORDS`, `UPBIT_EXACT`, `UPBIT_TOKEN`, `KIS_TOKEN`,
    `KIS_GET_PATHS`, `KIS_TRS`, `TR_SHAPE`, `ORDER_TR`, `TRANSPORT_NAMES`, `CREDENTIAL_NAMES`, `SEND_SOURCE`), its
    `_token_hits` and `_path_hits` and its six tests; it also adds its transport and keys checks after the last line
    of `test_suite_runs_hermetic_in_a_temp_home_with_seams` (`assert alerts._toast("after", "the nested call") ...`).
  - `tests.macro_m0_harness.TEXT_EXCEPTIONS: dict[str, frozenset[str]]`.
  - `core.ficc.context_log.ACTING_MODULE_PREFIXES` ends with `"execution."`.
  - `tests.acceptance.runtime_py()` scans `execution/**/*.py`; test_09 skips exactly `execution/kis_inquiry.py`.
  - The `execution/` suite prefix in `tests/run_all.py` (`--suite execution`), named in both hand-written suite lists.
  - The E1 execution ledger with its three empty sections: "Drift rulings", "Deferred minors", "Runs".

**Plan decisions used:** E1 (order and drift; the follow-up loosened the registration literal), E2 (package and
import allowlist), E6 (runtime_py, the file-exact exceptions, the guard list), E8 (the suite mirrors compliance), E28
(the key scrub, the toast recorder, STRAYS, the real-home watch with the poller probe), E29 (only the prefix), E35
(the ledger); and for the guards that later files meet: E11 (the clock only in `poll.main`), E30 / E1R2-4 (the daily
inquiry files left out of the paths-only watch), E36 / E1R2-11 (`session.request` in `_send` is the one verb call).
Contract sections 0.2 to 0.6, 3.1, 3.2 (the Task 1 part), 4.1 to 4.5 (the Task 1 part) and 17 (the Task 1 line).

Notes for the implementer (read before starting):
- Owner gate 1 (ruling X1): this task runs only on a main that already holds the compliance follow-up plan and the
  odds plan. Step 1a checks it; if a check prints anything other than the expected value, stop and report it (a
  ruling, not a fix).
- Run every command from the repo root `C:/Users/whydi/OneDrive/Desktop/TRADEGEN` in Git Bash (the Bash tool).
- `tests/acceptance.py`, `tests/run_all.py` and `README.md` are CRLF: edit them with the Edit tool only (it keeps CRLF),
  never `sed -i`. `tests/macro_m0_harness.py` and `core/ficc/context_log.py` are LF. Add no wall-clock call to
  `core/ficc/context_log.py` (test_s4 and test_m6_rulings_static read it).
- `tests/` is outside every repo-wide scan (T-RO-01, test_08, test_09, T-CTX-01), so `tests/execution_guards.py` and
  the new `TEXT_EXCEPTIONS` may spell the words they look for (`CANO`, `order-cash`, `private_key`, ...). Never copy
  them into `execution/` or `core/`.
- The DRIFT RULE (contract 0.6) binds every Edit below: re-read the file first; the quoted old text is the anchor and
  a line number only a hint. Two anchors WILL have drifted, because the odds plan registered its own suite: the last
  term of `tests()` in `tests/run_all.py` and the two `one suite:` lists (tests/run_all.py and README.md). Step 3b
  gives both the old text at `5816d3c` and the expected text after the odds plan; apply the matching pair and record
  the ruling in the ledger.
- QUANTGEN overlap check before EVERY test command (contract 0.3). Every test command below is written as one Git Bash
  command that starts with the check, so nothing runs while a `run_all` process is alive:
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`.
  When the check finds a process, the command prints no summary line (only `exit 1`): wait, then run it again. The
  same check in the PowerShell tool, when needed alone:
  `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`.
- Every `--suite` run carries the KEYLESS prefix of contract 0.2 (written out below) and is followed by
  `git checkout -- qa/acceptance_results.json` (a suite run rewrites that tracked CRLF file; only Task 13 commits it).
  Never run two suites at once, never `tests/run_all.py` without `--suite` here, never `python -m tests.macro_acceptance`.
- No test in this task starts a process, reloads a module or makes a network call (contract 0.2); the tests that
  need a second lock holder use a second in-process handle.

- [ ] **Step 1a: Pre-flight, branch, ledger, line endings; then write the failing tests**

1. Pre-flight (owner gate 1, contract 0.6). From the repo root:

```bash
git switch main
git status --short
git log --oneline -1
grep -c "^def _suite_names" tests/compliance_guards.py
grep -c "paper, grokteam or compliance" tests/compliance_guards.py
grep -cE "^def (pubkey_at|full_home)\(" tests/compliance_fixtures.py
grep -c "odds_acceptance" tests/run_all.py
```

Expected: `git status --short` prints nothing (the only line allowed is an untracked
`docs/superpowers/plans/2026-10-24-e1-account-inquiry.md` if the coordinator has not committed the plan; it is never
staged here); then the four counts `1`, `0`, `2`, `1`. A `0` for `_suite_names`, a `1` for the old literal, a count
other than `2` for `pubkey_at`/`full_home` (the odds plan's public signed-home helpers, which Tasks 5 and 12 need) or
`0` for `odds_acceptance` means an earlier plan has not merged: stop and rule.

2. Branch:

```bash
git switch -c e1-account-inquiry
git branch --show-current          # prints: e1-account-inquiry
```

3. Create the execution ledger (E35; LF, a new file, so a heredoc is safe). The backslashes keep the backticks
literal; `${base}` is filled in from git:

```bash
base=$(git rev-parse --short main)
cat > docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md <<EOF
# E1 account inquiry: execution ledger

The execution record of \`docs/superpowers/plans/2026-10-24-e1-account-inquiry.md\` (contract decision E35): every
DRIFT RULE ruling (contract 0.6), every deferred minor and the totals of the runs Task 13 records, one line each.

Branch \`e1-account-inquiry\`, cut from \`main\` at \`${base}\`, after the compliance follow-up and the odds plan
merged (ruling X1).

## Drift rulings

## Deferred minors

## Runs
EOF
cat docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
wc -l docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
```

Expected: the file as written, with backticks (no backslashes) and the short sha of main on the "Branch" line;
`13 docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`.

4. Line endings of the five files this task edits (contract 0.4):

```bash
git ls-files --eol tests/acceptance.py tests/run_all.py README.md tests/macro_m0_harness.py core/ficc/context_log.py
```

Expected: `i/crlf  w/crlf` for `README.md`, `tests/acceptance.py` and `tests/run_all.py`; `i/lf    w/lf` for
`core/ficc/context_log.py` and `tests/macro_m0_harness.py`. A different answer is a drift ruling: stop and rule.

5. Create `tests/execution_fixtures.py` (LF) with exactly:

```python
"""Fixtures for the execution suite (E1 plan; contract section 3.2). Task 1 adds the constants, the recorders and the
first part of `isolated()`; Task 2 adds the transport seams and `fake_keys()`, Task 3 `serve()`, Task 4 `snap()` and
Tasks 5 to 7 the venue answers. Nothing here imports `execution` at module level, so a broken or missing module fails
only the tests that use it."""
from __future__ import annotations

import contextlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

NOW = datetime(2026, 10, 24, 0, 0, 0, tzinfo=timezone.utc)      # 09:00 KST, a Saturday
DATE_HEADER = "Sat, 24 Oct 2026 00:00:00 GMT"
FAKE_KEYS = {"KIS_APP_KEY": "test-kis-appkey", "KIS_APP_SECRET": "test-kis-appsecret",
             "KIS_ACCOUNT_8": "12345678", "KIS_ACCOUNT_PD": "01",
             "UPBIT_ACCESS_KEY": "test-upbit-access", "UPBIT_SECRET_KEY": "test-upbit-secret",
             "OKX_API_KEY": "test-okx-key", "OKX_API_SECRET": "test-okx-secret", "OKX_API_PASSPHRASE": "test-okx-pass"}
KEY_NAMES = tuple(FAKE_KEYS) + ("KIS_BASE_URL",)
_MISSING = object()


class Refused(RuntimeError):
    """What the suite's stubs raise: an E1 send that no test routed."""


TOASTS: list[tuple[str, str]] = []      # (title, body) of every patched alerts._toast call; cleared by isolated()
SLEEPS: list[float] = []                # seconds of every patched transport._sleep call (Task 2); cleared by isolated()
STRAYS: list[str] = []                  # every refused or unrouted send ("METHOD url-path"); cleared by isolated();
                                        # a test that expects one asserts on it and then clears it
REAL_SEND = None                        # Task 2: the unpatched transport._send while isolated() is active


def _record_toast(title: str, body: str) -> bool:
    """Stands in for core.compliance.alerts._toast: records the toast, shows nothing and reports it shown."""
    TOASTS.append((title, body))
    return True


@contextlib.contextmanager
def isolated(home: Path) -> Iterator[None]:
    """The E1 seams for one test (E28), inside the wrapper's temp home `home` (Task 2 points keys._ENV_FILE there):
    the recorders are cleared, every name of KEY_NAMES leaves os.environ (config's load_dotenv put the real values
    there) and alerts._toast is the recorder. On the way out each patch is undone in reverse order and each key name
    gets its value from before the test back (one that was absent is removed again, whatever the test set). A test
    that returns normally with an entry left in STRAYS fails here."""
    from core.compliance import alerts
    patches = [(alerts, "_toast", _record_toast)]
    TOASTS.clear()
    SLEEPS.clear()
    STRAYS.clear()
    env = {name: os.environ.pop(name, None) for name in KEY_NAMES}
    saved = []
    try:
        for obj, name, value in patches:
            saved.append((obj, name, vars(obj).get(name, _MISSING)))
            setattr(obj, name, value)
        yield
        assert not STRAYS, f"a refused or unrouted E1 send in a test that passed: {STRAYS}"
    finally:
        for obj, name, original in reversed(saved):
            if original is _MISSING:
                delattr(obj, name)
            else:
                setattr(obj, name, original)
        for name, value in env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
```

6. Create `tests/execution_acceptance.py` (LF) with exactly:

```python
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
    exists (never creating it) and releases its own lock at once. ponytail: on Windows the probe holds byte 0 for a
    moment, so a poller starting in that instant sees it held and exits 0 (E1R2-1); it starts again at next logon."""
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
    KIS token file; an absent entry adds nothing. With `paths_only`, the execution home and the token file give
    (path, 0, 0) rows and leave the daily inquiry files out; the compliance home is always listed in full."""
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
                st = path.stat()
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
```

7. Create `tests/execution_guards.py` (LF) with exactly (Step 1b appends the registration test; Task 2 appends more):

```python
"""Static guards over execution/ and the execution suite's own harness (E1 plan Tasks 1 and 2; E1 spec 8 "Read-only
guards", 9 "Guards"; contract sections 0.2, 0.5 and 4.5).

Each guard is a pure checker `(rel, source) -> [hit, ...]`. Every test first proves its checker catches a synthetic
offender (the positive control), then asserts the shipped files are clean. The repo-wide guards (T-RO-01, test_08,
test_09, test_16, test_18, T-CTX-01) scan execution/ too, with two file-exact text exceptions: execution/kis_inquiry.py
and execution/upbit_inquiry.py. These add what they miss: docstrings and comments, `def` names, the explicit import
allowlist, every HTTP verb and process call, star and dynamic imports, the wall clock outside poll.main(), writes
that skip checked_target, the one writer of evidence.jsonl, and the never-live harness itself. Task 2 appends the
pinned allowlists and the exactness, transport-only and pinned-send guards.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import re
import sys
import tempfile
import types
from pathlib import Path

from tests import acceptance as A
from tests import compliance_guards as CG
from tests import macro_m0_harness as H

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ROOT / "execution"
INIT = "execution/__init__.py"
X = "execution/x.py"                       # the name a synthetic offender is checked under
RAW_BANNED = ("private_key", "seed_phrase", "append_system_entry", "system_halt", "system_disarm",
              "x-simulated-trading", "openapivts")          # any case
STDLIB = frozenset({"__future__", "argparse", "base64", "collections.abc", "contextlib", "dataclasses", "datetime",
                    "email.utils", "fcntl", "hashlib", "hmac", "json", "math", "msvcrt", "os", "pathlib", "re", "sys",
                    "threading", "time", "traceback", "types", "typing", "uuid", "zoneinfo"})
VERBS = frozenset({"post", "put", "patch", "delete", "request", "send", "urlopen", "getresponse", "connect",
                   "create_connection"})
CLOCK_MAIN = "execution/poll.py"           # only the body of its main() reads the clock (E11)
TRANSPORT = "execution/transport.py"       # the only user of requests and urllib.parse
EVIDENCE_WRITER = "execution/evidence.py"  # the one writer of evidence.jsonl (spec 6)
OS_PROCESS = ("system", "popen", "startfile")
OS_PROCESS_PREFIXES = ("fork", "exec", "spawn", "posix_spawn")
WRITE_MODE = re.compile(r"[wax+]")
WRITE_METHODS = frozenset({"write_text", "write_bytes", "touch", "unlink", "rename", "rmdir", "symlink_to",
                           "hardlink_to"})
OS_WRITES = frozenset({"remove", "unlink", "rename", "renames", "removedirs", "rmdir", "open", "fdopen", "mkdir",
                       "makedirs", "link", "symlink", "truncate"})


# --------------------------------------------------------------------------- #
# Scope and AST helpers
# --------------------------------------------------------------------------- #
def _sources() -> dict[str, str]:
    """rel path -> raw text of every execution/**/*.py (no __pycache__); execution/__init__.py must be among them."""
    files = CG._sources(EXECUTION)
    assert INIT in files, f"scan scope: {INIT} missing"
    return files


def _test_sources() -> dict[str, str]:
    """rel path -> raw text of every tests/execution_*.py."""
    return {f"tests/{p.name}": p.read_text(encoding="utf-8") for p in sorted((ROOT / "tests").glob("execution_*.py"))}


def _os_process(node: ast.AST) -> bool:
    """`os.<name>` (called or not) or `from os import <name>` for a name that starts a process."""
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os":
        names = [node.attr]
    elif isinstance(node, ast.ImportFrom) and node.module == "os":
        names = [a.name for a in node.names]
    else:
        return False
    return any(n in OS_PROCESS or n.startswith(OS_PROCESS_PREFIXES) for n in names)


def _modules(node: ast.AST) -> list[str]:
    """The modules an import statement names ([] for any other node)."""
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    return [node.module or ""] if isinstance(node, ast.ImportFrom) else []


def _checked(node: ast.AST | None) -> bool:
    """A `checked_target(...)` call, bare or as `isolation.checked_target(...)`."""
    return isinstance(node, ast.Call) and "checked_target" in (getattr(node.func, "id", None),
                                                               getattr(node.func, "attr", None))


def _writes(call: ast.Call, at: int) -> bool:
    """The call's mode (positional `at` or keyword `mode`) can write: it holds w, a, x or +, or is not a constant."""
    mode = call.args[at] if len(call.args) > at else next((k.value for k in call.keywords if k.arg == "mode"), None)
    if mode is None:
        return False
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return bool(WRITE_MODE.search(mode.value))
    return True


# --------------------------------------------------------------------------- #
# Checkers: (rel, source) -> hits
# --------------------------------------------------------------------------- #
def _raw_hits(rel: str, src: str) -> list[str]:
    """RAW_BANNED anywhere in the raw text, in any case."""
    return CG._raw_hits(rel, src, RAW_BANNED, ())


def _allowed(rel: str, name: str) -> bool:
    """One dotted import target on the E1 allowlist (E2): STDLIB exactly, core.isolation, core.compliance.*,
    execution.*, and requests and urllib.parse in transport.py only."""
    if name in STDLIB or name == "core.isolation":
        return True
    if name in ("requests", "urllib.parse"):
        return rel == TRANSPORT
    return any(name == p or name.startswith(p + ".") for p in ("core.compliance", "execution"))


def _allowlist_hits(rel: str, src: str) -> list[str]:
    return [f"{rel}:{node.lineno}: imports {module}: not on the E1 allowlist (contract 0.5)"
            for node, module, names, _f in CG._imports(rel, ast.parse(src))
            if not (_allowed(rel, module) or (names and all(_allowed(rel, f"{module}.{n}") for n in names)))]


def _verb_hits(rel: str, src: str) -> list[str]:
    """A VERBS attribute call anywhere but the one `session.request(...)` in the body of transport._send (E1R2-11);
    os.system, os.popen, os.startfile, os.fork*, os.exec*, os.spawn* and os.posix_spawn*, named or imported; a
    subscript of sys.modules."""
    hits = []
    for node, funcs in CG._walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in VERBS:
            if not (rel == TRANSPORT and funcs == ("_send",) and ast.unparse(node.func) == "session.request"):
                hits.append(f"{rel}:{node.lineno}: .{node.func.attr}()")
        elif _os_process(node):
            hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
        elif isinstance(node, ast.Subscript) and ast.unparse(node.value) == "sys.modules":
            hits.append(f"{rel}:{node.lineno}: sys.modules[...]")
    return hits


def _clock_hits(rel: str, src: str) -> list[str]:
    """CG.CLOCKS reads and any `from time import ...`, except in the BODY of the top-level main() of
    execution/poll.py (E11); a def's defaults and decorators run where the def runs, so they count."""
    tree, hits, alias = ast.parse(src), [], {}
    for n in ast.walk(tree):                            # `import time as t`, `from datetime import date as D`
        if isinstance(n, ast.Import) or (isinstance(n, ast.ImportFrom) and n.module == "datetime"):
            alias.update({a.asname or a.name: a.name for a in n.names if a.name in CG.CLOCKS})
    for node, funcs in CG._walk(tree):
        if rel == CLOCK_MAIN and funcs[:1] == ("main",):
            continue
        if isinstance(node, ast.Attribute):
            value = node.value
            base = alias.get(value.id, value.id) if isinstance(value, ast.Name) else getattr(value, "attr", None)
            if node.attr in CG.CLOCKS.get(base, ()):
                hits.append(f"{rel}:{node.lineno}: {base}.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and node.module == "time":
            hits.append(f"{rel}:{node.lineno}: from time import ...")
    return hits


def _write_hits(rel: str, src: str) -> list[str]:
    """Spec 4 "State files": open() for writing only on a checked_target(...) call, no writing `.open(...)`, both
    os.replace arguments and every .mkdir() receiver checked_target(...) calls; write_text, write_bytes, touch,
    unlink, rename, rmdir, the link makers, a one-argument .replace() (Path.replace: str.replace takes two), the os
    file writers of OS_WRITES and any shutil use banned outright."""
    hits = []
    for node, _f in CG._walk(ast.parse(src)):
        bad = ""
        if (isinstance(node, ast.Name) and node.id == "shutil") or any(
                m.split(".")[0] == "shutil" for m in _modules(node)):
            bad = "shutil"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
            first = node.args[0] if node.args else next((k.value for k in node.keywords if k.arg == "file"), None)
            if _writes(node, 1) and not _checked(first):
                bad = "open() for writing without checked_target"
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            name, owner = node.func.attr, ast.unparse(node.func.value)
            if owner == "os" and name == "replace":
                if not (len(node.args) == 2 and all(_checked(a) for a in node.args)):
                    bad = "os.replace() of an unchecked path"
            elif owner == "os" and name in OS_WRITES:
                bad = f"os.{name}()"
            elif name == "open":
                bad = ".open() for writing" if _writes(node, 0) else ""
            elif name == "mkdir":
                bad = "" if _checked(node.func.value) else ".mkdir() on an unchecked path"
            elif name in WRITE_METHODS or (name == "replace" and len(node.args) == 1 and not node.keywords):
                bad = f".{name}()"
        if bad:
            hits.append(f"{rel}:{node.lineno}: {bad}")
    return hits


def _evidence_hits(rel: str, src: str) -> list[str]:
    """Raw text: only execution/evidence.py names evidence_path (spec 6: the one writer of evidence.jsonl)."""
    return [] if rel == EVIDENCE_WRITER or "evidence_path" not in src else [f"{rel}: names evidence_path"]


def _process_hits(rel: str, src: str) -> list[str]:
    """A test that would start a process or reload a module (contract 0.2): an import of subprocess, multiprocessing
    or runpy, sys.executable, an os process name, importlib.reload or `from importlib import reload`."""
    hits = []
    for node, _f in CG._walk(ast.parse(src)):
        mods = _modules(node)
        reload = isinstance(node, ast.ImportFrom) and node.module == "importlib" and any(
            a.name == "reload" for a in node.names)
        attr = isinstance(node, ast.Attribute) and ast.unparse(node) in ("sys.executable", "importlib.reload")
        if (reload or attr or _os_process(node)
                or any(m.split(".")[0] in ("subprocess", "multiprocessing", "runpy") for m in mods)):
            hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
    return hits


# --------------------------------------------------------------------------- #
# Fake repo roots for the repo-wide guards
# --------------------------------------------------------------------------- #
def _probe_root(files: dict[str, str]) -> Path:
    """A fresh fake repo root inside the per-test temp home, holding `files` (rel path -> text)."""
    root = Path(tempfile.mkdtemp(prefix="root_", dir=os.environ["TRADEGEN_HOME"]))
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


@contextlib.contextmanager
def _swapped_root(root: Path):
    """tests.acceptance.ROOT and tests.macro_m0_harness.ROOT pointed at `root`; both come back afterwards."""
    keep = A.ROOT, H.ROOT
    A.ROOT = H.ROOT = root
    try:
        yield
    finally:
        A.ROOT, H.ROOT = keep


def _passes(test) -> bool:
    try:
        test()
    except AssertionError:
        return False
    return True


def _verdicts(rel: str, text: str) -> tuple[list[str], bool, bool]:
    """In a fake root holding only `rel` with `text`: T-RO-01's offences for it, and whether test_08 and test_09
    pass."""
    root = _probe_root({rel: text})
    with _swapped_root(root):
        return (H._offences(root / rel), _passes(A.test_08_no_broker_order_path),
                _passes(A.test_09_no_account_credentials_requested))


# --------------------------------------------------------------------------- #
# The repo-wide guards see execution/, with file-exact exceptions
# --------------------------------------------------------------------------- #
def test_runtime_py_scans_execution():
    """E1 spec 8: runtime_py() (test_08, test_09, test_16, test_18 and T-RO-01 through _scan_files) scans execution/,
    and an order string in a synthetic execution/ file fails test_08 and T-RO-01."""
    assert EXECUTION / "__init__.py" in A.runtime_py(), "runtime_py() does not scan execution/"
    root = _probe_root({"execution/probe.py": 'X = "order-cash"\n'})
    with _swapped_root(root):
        assert A.runtime_py() == [root / "execution" / "probe.py"], A.runtime_py()
        assert not _passes(A.test_08_no_broker_order_path), "test_08 missed an order string in execution/"
        hits = H._offences(root / "execution" / "probe.py")
    assert hits == ["execution/probe.py: 'order-cash'"], hits


def test_kis_and_upbit_exceptions_are_file_exact():
    """E6: the text exceptions hold for exactly execution/kis_inquiry.py (KIS_ACCOUNT, CANO, ACNT_PRDT_CD and the
    /uapi/.../trading/ paths; test_09 too) and execution/upbit_inquiry.py (/v1/orders, /v1/withdraws). Every other
    check still runs on both files, and test_08 has no exception at all."""
    kis = 'CANO = "x"\nP = "/uapi/domestic-stock/v1/trading/inquire-balance"\n'
    verdict = _verdicts("execution/kis_inquiry.py", kis)
    assert verdict == ([], True, True), verdict
    hits, _ok8, ok9 = _verdicts("execution/other.py", kis)
    assert hits == ["execution/other.py: 'CANO'", "execution/other.py: '/uapi/domestic-stock/v1/trading/'"], hits
    assert not ok9, "test_09 passed CANO outside execution/kis_inquiry.py"
    hits, ok8, _ok9 = _verdicts("execution/kis_inquiry.py", 'X = "order-cash"\n')
    assert hits == ["execution/kis_inquiry.py: 'order-cash'"] and not ok8, (hits, ok8)
    hits, _ok8, _ok9 = _verdicts("execution/kis_inquiry.py", "import ccxt\n")
    assert hits == ["execution/kis_inquiry.py:1: import ccxt"], hits
    hits, _ok8, _ok9 = _verdicts("execution/kis_inquiry.py", 'P = "/v1/orders/open"\n')
    assert hits == ["execution/kis_inquiry.py: '/v1/orders'"], hits          # the Upbit exception is Upbit's alone
    verdict = _verdicts("execution/upbit_inquiry.py", 'P = "/v1/orders/open"\nW = "/v1/withdraws"\n')
    assert verdict == ([], True, True), verdict
    hits, _ok8, ok9 = _verdicts("execution/upbit_inquiry.py", 'P = "/v1/orders/open"\nCANO = 1\n')
    assert hits == ["execution/upbit_inquiry.py: 'CANO'"] and not ok9, (hits, ok9)


# --------------------------------------------------------------------------- #
# Guards over every execution/**/*.py
# --------------------------------------------------------------------------- #
def test_no_raw_banned_words():
    """Raw text in any case, docstrings and comments included: no private_key or seed_phrase (the core-wide ban),
    none of owner.py's system-entry writers (E1 only alerts), neither the KIS demo header nor its mock host."""
    for needle in RAW_BANNED:
        assert _raw_hits(X, f'"""the {needle.upper()}"""\n'), needle
        assert _raw_hits(X, f"x = 1  # {needle}\n"), needle
    assert not _raw_hits(X, "signing_key, system_state, simulated, openapi, seed, private\n")
    hits = [h for rel, src in _sources().items() for h in _raw_hits(rel, src)]
    assert not hits, hits


def test_no_def_named_transfer_withdraw_or_deposit_address():
    """The compliance guards' core-wide def-name ban extends to execution/ (spec 8)."""
    sample = ("def transfer():\n    pass\nasync def withdraw():\n    pass\n"
              "class A:\n    def deposit_address(self):\n        pass\n")
    assert len(CG._def_hits(X, sample)) == 3
    assert not CG._def_hits(X, "def transfer_out():\n    pass\ndef withdrawals():\n    pass\n")
    hits = [h for rel, src in _sources().items() for h in CG._def_hits(rel, src)]
    assert not hits, hits


def test_imports_stay_on_the_allowlist():
    """E2 and spec 4 "Imports": exactly the STDLIB modules, core.isolation, core.compliance.*, execution.*, and
    requests and urllib.parse in transport.py only (Task 2 narrows execution.* further). Never config, data.*,
    core.engine.*, core.quant.*, core.calendars.*, core.ficc.*, core.rules.*, subprocess, ctypes, socket or
    shutil, so the signed closure stays small and the toast reaches subprocess only through alerts._toast."""
    for src in ("import config\n", "from data.krx import kis_client\n", "import data.krx.kis_client\n",
                "from core.engine import orders\n", "from core.quant import garch\n", "import urllib.request\n",
                "import socket\n", "import subprocess\n", "import ctypes\n", "import shutil\n", "import requests\n",
                "from urllib.parse import quote\n", "from core import isolation, quant\n",
                "from core.calendars import store\n", "import core.ficc.context_log\n",
                "def f():\n    import core.rules.governance\n", "import collections\n", "import os.path\n"):
        assert _allowlist_hits(X, src), src
    for src in ("import requests\n", "from urllib.parse import quote\n", "from urllib import parse\n"):
        assert not _allowlist_hits(TRANSPORT, src), src
        assert _allowlist_hits(X, src), src
    for module in sorted(STDLIB):
        assert not _allowlist_hits(X, f"import {module}\n"), module
    ok = ("from __future__ import annotations\nfrom collections.abc import Iterator\nfrom datetime import datetime\n"
          "from email.utils import parsedate_to_datetime\nfrom core import isolation\n"
          "from core.isolation import checked_target\nfrom core.compliance import alerts, model\n"
          "import core.compliance.owner\nfrom execution import snapshot\nfrom execution.transport import request\n"
          "from . import checks\n")
    assert not _allowlist_hits(X, ok), _allowlist_hits(X, ok)
    hits = [h for rel, src in _sources().items() for h in _allowlist_hits(rel, src)]
    assert not hits, hits


def test_no_dynamic_import():
    """No star or dynamic import (CG._dynamic_hits): either would hide a module from the allowlist and from the D14
    closure."""
    for src in ("from execution.transport import *\n", "m = __import__('requests')\n",
                "import importlib\nm = importlib.import_module('requests')\n", "exec(src)\n", "eval(src)\n",
                "import runpy\n"):
        assert CG._dynamic_hits(X, src), src
    assert not CG._dynamic_hits(X, "import json\npattern = re.compile('a')\nfrom execution import snapshot\n")
    hits = [h for rel, src in _sources().items() for h in CG._dynamic_hits(rel, src)]
    assert not hits, hits


def test_only_transport_send_calls_requests_request():
    """Spec 8, E36: no post, put, patch, delete, request, send, urlopen, getresponse, connect or create_connection
    attribute call anywhere in execution/ but the single `session.request(...)` in the body of transport._send
    (E1R2-11), no process started through os, no reach into sys.modules. The bare `request(...)` the venue modules
    import from transport is not an attribute call."""
    for src in ("requests.post(u)\n", "s.request('GET', u)\n", "x.delete()\n", "requests.Session().send(p)\n",
                "c.getresponse()\n", "s.connect(a)\n", "store.put(k, v)\n", "y.patch(z)\n",
                "urllib.request.urlopen(u)\n", "socket.create_connection(a)\n", "os.system('curl')\n",
                "os.popen(c)\n", "os.startfile(p)\n", "os.execv(a, b)\n", "os.spawnl(0, a)\n", "os.fork()\n",
                "os.posix_spawn(p, a, e)\n", "from os import system\n", "run = os.system\n",
                "m = sys.modules['requests']\n"):
        assert _verb_hits(X, src), src
    send = ("def _send(method, url, *, headers, params, json_body, timeout):\n"
            "    with requests.Session() as session:\n"
            "        return session.request(method, url, headers=headers)\n")
    assert not _verb_hits(TRANSPORT, send), _verb_hits(TRANSPORT, send)
    assert _verb_hits(X, send)
    assert _verb_hits(TRANSPORT, "def other(session):\n    return session.request('GET', u)\n")
    assert _verb_hits(TRANSPORT, "def _send(method, url):\n    return requests.request(method, url)\n")
    assert not _verb_hits(X, "d.get(k)\nlines.append(x)\nanswer = request('kis', 'GET', p)\ntime.sleep(1)\n"
                             "os.fsync(fd)\nn = os.urandom(6)\nkind = os.name\n")
    hits = [h for rel, src in _sources().items() for h in _verb_hits(rel, src)]
    assert not hits, hits


def test_no_wall_clock_outside_poll_main():
    """E11: only the BODY of main() in execution/poll.py reads the wall clock (CG.CLOCKS or any `from time import`);
    every other function takes `now` as an argument or calls transport._clock, which main() sets."""
    for src in ("x = datetime.now(timezone.utc)\n", "x = time.time()\n", "x = time.monotonic()\n",
                "from time import time\n", "import time as t\nx = t.time()\n", "x = date.today()\n",
                "x = datetime.datetime.utcnow()\n", "def main():\n    return datetime.now(timezone.utc)\n"):
        assert _clock_hits(X, src), src
    for src in ("def main(at=datetime.now(timezone.utc)):\n    pass\n",
                "def poll_once():\n    return datetime.now(timezone.utc)\n",
                "def helper():\n    def main():\n        return time.time()\n"):
        assert _clock_hits(CLOCK_MAIN, src), src
    main = ("def main(argv=None):\n    now = datetime.now(timezone.utc)\n"
            "    transport._clock = lambda: datetime.now(timezone.utc)\n    return now\n")
    assert not _clock_hits(CLOCK_MAIN, main), _clock_hits(CLOCK_MAIN, main)
    assert _clock_hits(X, main)
    assert not _clock_hits(X, "time.sleep(1)\n_sleep = time.sleep\nx = datetime.fromisoformat(s)\n")
    hits = [h for rel, src in _sources().items() for h in _clock_hits(rel, src)]
    assert not hits, hits


def test_every_write_goes_through_checked_target():
    """Spec 4 "State files": every write opens a path checked_target judged immediately before (temp files
    included), folders are made only on a checked path, and nothing is deleted, renamed or copied any other way."""
    for src in ("open(p, 'ab')\n", "open(p, mode='w')\n", "open(p, 'r+')\n", "open(p, m)\n", "open(file=p, mode='x')\n",
                "p.open('a')\n", "p.open(mode='xb')\n", "os.replace(a, checked_target(b))\n",
                "os.replace(checked_target(a))\n", "p.mkdir()\n", "os.mkdir(p)\n", "os.makedirs(p)\n",
                "p.write_bytes(b'')\n", "p.write_text(s)\n", "p.touch()\n", "p.unlink()\n", "p.rename(q)\n",
                "p.rmdir()\n", "p.replace(q)\n", "p.symlink_to(q)\n", "os.remove(p)\n", "os.unlink(p)\n",
                "os.rename(a, b)\n", "fd = os.open(p, flags)\n", "shutil.copy(a, b)\n", "import shutil\n",
                "from shutil import copyfile\n"):
        assert _write_hits(X, src), src
    ok = ("with open(checked_target(p, 'x'), 'ab') as fh:\n    fh.write(b'1')\n"
          "with open(p, 'rb') as fh:\n    data = fh.read()\n"
          "text = p.read_text(encoding='utf-8')\nwith p.open(encoding='utf-8') as fh:\n    pass\n"
          "checked_target(p.parent, 'folder').mkdir(parents=True, exist_ok=True)\n"
          "isolation.checked_target(q, 'folder').mkdir()\n"
          "os.replace(checked_target(a, 'tmp'), checked_target(b, 'file'))\n"
          "s = s.replace('a', 'b')\nos.fsync(fh.fileno())\n")
    assert not _write_hits(X, ok), _write_hits(X, ok)
    hits = [h for rel, src in _sources().items() for h in _write_hits(rel, src)]
    assert not hits, hits


def test_init_is_empty_and_main_blocks_are_one_line():
    """execution/__init__.py exists and is 0 bytes (under the trailing-dot prefix the package itself is not acting,
    so it may hold no code), and a __main__ block is exactly `raise SystemExit(main())` (T-CTX-01 skips those
    bodies)."""
    probe = Path(os.environ["TRADEGEN_HOME"]) / "init_probe"        # the per-test temp home; removed with it
    probe.mkdir()
    (probe / "__init__.py").write_bytes(b"x = 1\n")
    assert CG._init_hits(probe / "__init__.py") and CG._init_hits(probe / "missing.py")
    assert not CG._init_hits(EXECUTION / "__init__.py"), f"{INIT} must exist and be 0 bytes"
    assert CG._main_block_hits(X, 'if __name__ == "__main__":\n    main()\n')
    assert CG._main_block_hits(X, 'if __name__ == "__main__":\n    import sys\n    raise SystemExit(main())\n')
    assert not CG._main_block_hits(X, 'if __name__ == "__main__":\n    raise SystemExit(main())\n')
    hits = [h for rel, src in _sources().items() for h in CG._main_block_hits(rel, src)]
    assert not hits, hits


def test_acting_prefix_covers_execution():
    """E1 spec 8, E29: every execution module is acting (T-CTX-01), the package itself is not, the runtime guard
    refuses a frame of an execution module, and the static scan of the real tree reports nothing."""
    from core.ficc import context_log as CL
    assert CL.is_acting_module("execution.poll") and CL.is_acting_module("execution.kis_inquiry"), \
        "execution.* is not an acting prefix"
    assert not CL.is_acting_module("execution") and not CL.is_acting_module("executions.x")
    frame = {"__name__": "execution.probe", "CL": CL}
    exec("def read():\n    CL.assert_not_acting_caller()\n", frame)
    try:
        frame["read"]()
    except CL.ContextIsolationError as exc:
        assert "execution.probe" in str(exc), exc
    else:
        raise AssertionError("a frame of execution.probe read a context surface")
    assert CL.static_isolation_report() == []


def test_only_evidence_names_evidence_path():
    """Spec 6: execution/evidence.py is the one writer of evidence.jsonl, so no other execution file even names
    owner.evidence_path (raw text)."""
    assert _evidence_hits(X, "path = owner.evidence_path()\n")
    assert _evidence_hits(X, "# owner.evidence_path() is the file\n")
    assert not _evidence_hits(EVIDENCE_WRITER, "path = owner.evidence_path()\n")
    assert not _evidence_hits(X, "path = owner.log_path()\nevidence = 1\n")
    hits = [h for rel, src in _sources().items() for h in _evidence_hits(rel, src)]
    assert not hits, hits


# --------------------------------------------------------------------------- #
# The harness itself
# --------------------------------------------------------------------------- #
def test_tests_start_no_process():
    """Contract 0.2: no execution test starts a process (a child has none of the wrapper's patches, and OKX
    public/time needs no key) or reloads a module (a reload points keys._ENV_FILE back at the real .env)."""
    for src in ("import subprocess\n", "from subprocess import run\n", "import multiprocessing\n",
                "from multiprocessing import Process\n", "import multiprocessing.pool\n", "import runpy\n",
                "x = sys.executable\n", "os.system(c)\n", "os.popen(c)\n", "os.startfile(p)\n", "os.execv(a, b)\n",
                "os.spawnv(0, a, b)\n", "importlib.reload(m)\n", "from importlib import reload\n"):
        assert _process_hits("tests/execution_x.py", src), src
    assert not _process_hits("tests/execution_x.py", 'a = "subprocess"\nb = "execution.poll"\nimport importlib\n'
                                                     'm = importlib.import_module("tests.execution_guards")\n')
    files = _test_sources()
    assert {"tests/execution_acceptance.py", "tests/execution_fixtures.py", "tests/execution_guards.py"} <= set(files)
    hits = [h for rel, src in files.items() for h in _process_hits(rel, src)]
    assert not hits, hits


def test_suite_runs_hermetic_in_a_temp_home_with_seams():
    """Every E1 test runs inside hermetic(), a fresh TRADEGEN_HOME and isolated(): no E1 key name in os.environ, the
    toast recorder in place of alerts._toast, no stray send. A nested wrapped call arms one more level, moves the
    home and clears the recorders, and afterwards removes a key name the inner test set."""
    from core.compliance import alerts
    from tests import execution_acceptance as EA
    from tests import execution_fixtures as F
    from tests import macro_acceptance as MA
    home = Path(os.environ["TRADEGEN_HOME"])
    assert MA._DEPTH > 0, "the hermetic guard is not armed"
    assert home.is_dir() and home.name.startswith("tradegen_home_"), home
    assert not home.resolve().is_relative_to((Path.home() / ".tradegen").resolve()), home
    assert not [n for n in F.KEY_NAMES if n in os.environ], "an E1 key name reached the test"
    assert alerts._toast("probe title", "probe body") is True and F.TOASTS[-1] == ("probe title", "probe body")
    assert F.STRAYS == [], F.STRAYS
    seen = []

    def inner():
        os.environ["KIS_APP_KEY"] = "set-by-the-inner-test"
        seen.append((MA._DEPTH, Path(os.environ["TRADEGEN_HOME"]), list(F.TOASTS)))

    EA._wrap(inner)()
    depth, inner_home, toasts = seen[0]
    assert depth == MA._DEPTH + 1 and inner_home != home and inner_home.name.startswith("tradegen_home_"), seen
    assert toasts == [], "isolated() did not clear the toast recorder"
    assert Path(os.environ["TRADEGEN_HOME"]) == home and not inner_home.exists(), seen
    assert "KIS_APP_KEY" not in os.environ, "a key name the inner test set survived it"
    assert alerts._toast("after", "the nested call") is True and F.TOASTS[-1] == ("after", "the nested call")


def _flagged(run) -> None:
    """`run()` (a wrapped test) fails with the wrapper's real-home message."""
    try:
        run()
    except AssertionError as exc:
        assert "the test touched the real ~/.tradegen" in str(exc), exc
    else:
        raise AssertionError("a change under a real home was not flagged")


def _append(path: Path) -> None:
    with open(path, "ab") as fh:
        fh.write(b"{}\n")


@contextlib.contextmanager
def _held(path: Path):
    """`path` locked by a second in-process handle, as the owner's poller holds poll.lock (contract 0.2)."""
    with open(path, "a+b") as fh:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fh.seek(0)
            if os.name == "nt":
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fh, fcntl.LOCK_UN)


def test_harness_flags_a_change_to_the_real_homes():
    """The wrapper fails a test that changes the real ~/.tradegen/execution, ~/.tradegen/compliance or
    ~/.tradegen/kis_token.json (stand-ins here). While another handle holds execution/poll.lock (the owner's
    running poller), only the set of paths under execution/ and of the token file counts there, the daily inquiry
    files are left out, and the compliance home is still watched in full."""
    from tests import execution_acceptance as EA
    fake = Path(os.environ["TRADEGEN_HOME"]) / "fake_real"        # the per-test temp home; removed with it
    execution, compliance, token = fake / "execution", fake / "compliance", fake / "kis_token.json"
    execution.mkdir(parents=True)
    compliance.mkdir()
    token.write_bytes(b"{}")
    (execution / "inquiry-20261024.jsonl").write_bytes(b"{}\n")
    (execution / "alerts.jsonl").write_bytes(b"{}\n")
    keep = EA._REAL
    try:
        EA._REAL = (execution, compliance, token)
        assert not EA._poller_running()
        EA._wrap(lambda: None)()                                    # nothing changed: passes
        _flagged(EA._wrap(lambda: (compliance / "owner.jsonl").write_bytes(b"{}\n")))
        _flagged(EA._wrap(lambda: _append(execution / "alerts.jsonl")))
        _flagged(EA._wrap(lambda: _append(execution / "inquiry-20261024.jsonl")))
        _flagged(EA._wrap(lambda: token.write_bytes(b'{"access_token": "x"}')))
        with _held(execution / "poll.lock"):
            assert EA._poller_running(), "a held poll.lock was not seen"
            EA._wrap(lambda: (_append(execution / "inquiry-20261024.jsonl"), _append(execution / "alerts.jsonl"),
                              (execution / "inquiry-20261025.jsonl").write_bytes(b"{}\n"),
                              token.write_bytes(b'{"access_token": "refreshed"}')))()
            _flagged(EA._wrap(lambda: (execution / "other.jsonl").write_bytes(b"{}\n")))
            _flagged(EA._wrap(lambda: (compliance / "alerts.jsonl").write_bytes(b"{}\n")))
        assert not EA._poller_running(), "the probe still sees poll.lock held"
    finally:
        EA._REAL = keep


def test_a_stray_send_fails_a_passing_test():
    """isolated() fails a test that returns normally after a refused or unrouted send (E28): the venue snapshots let
    Refused and AssertionError propagate, and STRAYS catches a send whose error was swallowed anyway."""
    from tests import execution_acceptance as EA
    from tests import execution_fixtures as F
    try:
        EA._wrap(lambda: F.STRAYS.append("GET /v1/ticker"))()
    except AssertionError as exc:
        assert "GET /v1/ticker" in str(exc), exc
    else:
        raise AssertionError("a test that left a stray send passed")
    finally:
        F.STRAYS.clear()                                            # the inner test's stray, not this test's
    EA._wrap(lambda: (F.STRAYS.append("GET /v1/ticker"), F.STRAYS.clear()))()


def _top_imports(rel: str) -> list[str]:
    """The modules `rel` imports at module level (not inside a function)."""
    return [m for node in ast.parse((ROOT / rel).read_text(encoding="utf-8")).body for m in _modules(node)]


def test_aggregator_skips_missing_and_isolates_broken_modules():
    """Contract 3.1: an absent module is skipped, one that fails to import becomes a single `<module>/import` entry
    that re-raises, a `test_*` name imported from elsewhere is not collected, an empty run exits 1, and neither the
    aggregator nor the fixtures import execution or the fixtures at module level (E28)."""
    from tests import execution_acceptance as EA
    probe = Path(os.environ["TRADEGEN_HOME"]) / "probe"
    probe.mkdir()
    mixed = types.ModuleType("tests.execution_mixed")
    exec("from tests.execution_fixtures import isolated as test_imported\ndef test_own():\n    pass\n", vars(mixed))
    for stem in ("execution_broken", "execution_mixed"):
        (probe / f"{stem}.py").write_bytes(b"")
    keep = EA.TESTS, EA.MODULES
    sys.modules.update({"tests.execution_broken": None, "tests.execution_mixed": mixed})   # None: import raises
    try:
        EA.TESTS, EA.MODULES = probe, ("execution_broken", "execution_absent", "execution_mixed")
        found = EA.tests()
    finally:
        EA.TESTS, EA.MODULES = keep
        for stem in ("execution_broken", "execution_mixed"):
            sys.modules.pop(f"tests.{stem}", None)
    assert [n for n, _f in found] == ["execution_broken/import", "execution_mixed/test_own"], found
    try:
        found[0][1]()
    except ImportError:
        pass
    else:
        raise AssertionError("the broken module's entry did not re-raise its import error")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = EA._main(["no such test"])
    assert code == 1 and out.getvalue().strip() == "0/0 passed, 0 failed, 0 not run", (code, out.getvalue())
    for rel in ("tests/execution_acceptance.py", "tests/execution_fixtures.py"):
        eager = [m for m in _top_imports(rel) if m.split(".")[0] == "execution" or m == "tests.execution_fixtures"]
        assert not eager, (rel, eager)
```

- [ ] **Step 2a: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

Expected (`exit 1`; the tracebacks on stderr omitted; the runner sorts by test name):

```
PASS execution_guards/test_a_stray_send_fails_a_passing_test
FAIL execution_guards/test_acting_prefix_covers_execution AssertionError: execution.* is not an acting prefix
PASS execution_guards/test_aggregator_skips_missing_and_isolates_broken_modules
FAIL execution_guards/test_every_write_goes_through_checked_target AssertionError: scan scope: execution/__init__.py missing
PASS execution_guards/test_harness_flags_a_change_to_the_real_homes
FAIL execution_guards/test_imports_stay_on_the_allowlist AssertionError: scan scope: execution/__init__.py missing
FAIL execution_guards/test_init_is_empty_and_main_blocks_are_one_line AssertionError: execution/__init__.py must exist and be 0 bytes
FAIL execution_guards/test_kis_and_upbit_exceptions_are_file_exact AssertionError: (["execution/kis_inquiry.py: 'CANO'", "execution/kis_inquiry.py: '/uapi/domestic-stock/v1/trading/'"], True, True)
FAIL execution_guards/test_no_def_named_transfer_withdraw_or_deposit_address AssertionError: scan scope: execution/__init__.py missing
FAIL execution_guards/test_no_dynamic_import AssertionError: scan scope: execution/__init__.py missing
FAIL execution_guards/test_no_raw_banned_words AssertionError: scan scope: execution/__init__.py missing
FAIL execution_guards/test_no_wall_clock_outside_poll_main AssertionError: scan scope: execution/__init__.py missing
FAIL execution_guards/test_only_evidence_names_evidence_path AssertionError: scan scope: execution/__init__.py missing
FAIL execution_guards/test_only_transport_send_calls_requests_request AssertionError: scan scope: execution/__init__.py missing
FAIL execution_guards/test_runtime_py_scans_execution AssertionError: runtime_py() does not scan execution/
PASS execution_guards/test_suite_runs_hermetic_in_a_temp_home_with_seams
PASS execution_guards/test_tests_start_no_process

5/17 passed, 12 failed, 0 not run
exit 1
```

The five harness tests pass already (they need no product change); every other test fails on the missing package,
the unwidened `runtime_py()`, the missing T-RO-01 exceptions or the missing prefix. If a test fails instead on an
`AssertionError` whose message is a synthetic source string (a positive control), the checker was mistyped: fix the
copy, never weaken the control.

- [ ] **Step 3a: Implement (package, runtime_py, T-RO-01 exceptions, acting prefix)**

1. The empty package marker:

```bash
mkdir -p execution && : > execution/__init__.py && wc -c execution/__init__.py
# prints: 0 execution/__init__.py
```

2. `tests/acceptance.py` (CRLF; Edit tool). Edit 1, anchor: the head of `runtime_py()` (hint :48-50). Old text:

```python
def runtime_py() -> list[Path]:
    files: list[Path] = []
    for base in (ROOT / "core", ROOT / "data", ROOT / "ui"):
```

New text (only the tuple gains `ROOT / "execution"`):

```python
def runtime_py() -> list[Path]:
    files: list[Path] = []
    for base in (ROOT / "core", ROOT / "data", ROOT / "ui", ROOT / "execution"):
```

Edit 2, anchor: the head of `test_09_no_account_credentials_requested` (hint :178-180; the `for name in ...` loop
below it is unchanged). Old text:

```python
def test_09_no_account_credentials_requested():
    """Order submission needs an account number. Never ask for one."""
    blob = "\n".join(_read(p) for p in runtime_py())
```

New text:

```python
def test_09_no_account_credentials_requested():
    """Order submission needs an account number. Never ask for one. E1's balance inquiry,
    execution/kis_inquiry.py, is the one file that names one; tests/execution_guards.py pins its paths and TR ids."""
    blob = "\n".join(_read(p) for p in runtime_py() if p.relative_to(ROOT).as_posix() != "execution/kis_inquiry.py")
```

Every caller of `runtime_py()` now sees `execution/`: test_08 (raw text, no exception), test_09 (one file skipped),
test_16 (UTF-8), test_18 (code-only text) and T-RO-01 through `_scan_files` (tests/macro_m0_harness.py:63-65).

3. `tests/macro_m0_harness.py` (LF). Edit 1, anchor: the `FORBIDDEN_TEXT_CS` / `FORBIDDEN_PATH_RE` pair (hint :35-36).
Old text:

```python
FORBIDDEN_TEXT_CS = ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD")           # an account number implies an order path
FORBIDDEN_PATH_RE = re.compile(r"/uapi/[^\s'\"]*/trading/")           # every KIS trading domain
```

New text (the map follows the pair; contract 4.2):

```python
FORBIDDEN_TEXT_CS = ("KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD")           # an account number implies an order path
FORBIDDEN_PATH_RE = re.compile(r"/uapi/[^\s'\"]*/trading/")           # every KIS trading domain
# E1 (execution spec 8; ruling X6): file-exact exceptions to the TEXT checks only. Every other check (imports, calls,
# mutating HTTP) still runs on these files, and tests/execution_guards.py pins what each may hold.
TEXT_EXCEPTIONS = {
    "execution/kis_inquiry.py": frozenset({"KIS_ACCOUNT", "CANO", "ACNT_PRDT_CD", FORBIDDEN_PATH_RE.pattern}),
    "execution/upbit_inquiry.py": frozenset({"/v1/orders", "/v1/withdraws"}),
}
```

Edit 2, anchor: the three `hits` lines of `_offences` (hint :80-82). Old text:

```python
    hits = [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CI if n in low]
    hits += [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CS if n in code]
    hits += [f"{rel}: {m.group(0)!r}" for m in FORBIDDEN_PATH_RE.finditer(code)]
```

New text (the import, call and mutating-HTTP checks below it still run on both files; `_yaml_offences` is unchanged):

```python
    skip = TEXT_EXCEPTIONS.get(rel, frozenset())
    hits = [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CI if n in low and n not in skip]
    hits += [f"{rel}: {n!r}" for n in FORBIDDEN_TEXT_CS if n in code and n not in skip]
    if FORBIDDEN_PATH_RE.pattern not in skip:
        hits += [f"{rel}: {m.group(0)!r}" for m in FORBIDDEN_PATH_RE.finditer(code)]
```

4. `core/ficc/context_log.py` (LF). Edit, anchor: the `ACTING_MODULE_PREFIXES` tuple (hint :71-73). Old text:

```python
ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",
                          "core.ficc.pit", "core.ficc.contracts", "core.ficc.lag_audit",
                          "core.compliance.", "core.odds.")             # spec 4: the gate and the odds engine act
```

New text:

```python
ACTING_MODULE_PREFIXES = ("core.quant.", "core.engine.", "core.rules.", "core.calendars", "core.markets",
                          "core.ficc.pit", "core.ficc.contracts", "core.ficc.lag_audit",
                          "core.compliance.", "core.odds.",             # spec 4: the gate and the odds engine act
                          "execution.")                                 # E1 spec 8: account inquiry acts too
```

Nothing else in `context_log.py` changes. `repo_modules` still scans `core/` and `data/` only (E29): the import
allowlist already bans every `core.ficc` import from `execution/`, and `assert_not_acting_caller` now refuses a frame
of an `execution.*` module.

- [ ] **Step 4a: Run to verify it passes**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

Expected, ending: `17/17 passed, 0 failed, 0 not run` and `exit 0`.

Then T-RO-01 alone on the real tree (it now scans `execution/__init__.py`; no results file is written):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

Expected: `T-RO-01 ok`.

- [ ] **Step 1b: Write the failing test (suite registration)**

Append to the END of `tests/execution_guards.py` (after `test_aggregator_skips_missing_and_isolates_broken_modules`),
exactly:

```python


# --------------------------------------------------------------------------- #
# Registration
# --------------------------------------------------------------------------- #
def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite execution` selects this suite, and both hand-written suite lists name it, read
    through CG._suite_names (README.md:12 already says "execution", so a substring check would prove nothing)."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="execution")]
    assert any(n.startswith("execution/execution_guards/") for n in names), names
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "execution" in CG._suite_names(path.read_text(encoding="utf-8")), path.name
```

`run_all.tests()` runs the real discovery of every suite (it imports their modules and runs none; about 2 s), so a
commented-out or unreachable registration line fails the first assertion.

- [ ] **Step 2b: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

Expected (`exit 1`): the 17 PASS lines of Step 4a, plus

```
FAIL execution_guards/test_suite_is_registered_in_run_all_and_readme AssertionError: []
```

sorted between `test_runtime_py_scans_execution` and `test_suite_runs_hermetic_in_a_temp_home_with_seams`, and the
summary `17/18 passed, 1 failed, 0 not run`.

Also confirm the runner does not know the suite yet (an empty run exits 1):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite execution; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected last lines: `0/0 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` and `exit 1`.

- [ ] **Step 3b: Implement (register the suite)**

All four edits are in CRLF files: the Edit tool only. Re-read each file first (DRIFT RULE).

`tests/run_all.py`, edit 1, anchor: the `NotRun` import that follows the suite imports (hint :51; no earlier plan
changes this line, so the new import lands after the last suite import, the odds one included). Old text:

```python
from tests.notrun import NotRun                             # noqa: E402
```

New text:

```python
from tests.execution_acceptance import tests as execution_tests  # noqa: E402
from tests.notrun import NotRun                             # noqa: E402
```

`tests/run_all.py`, edit 2, anchor: the last term of `tests()`, the line that closes its `return (...)`. At `5816d3c`
that is the compliance term (hint :67). Old text:

```python
            [(f"compliance/{n}", f) for n, f in compliance_tests()])
```

New text:

```python
            [(f"compliance/{n}", f) for n, f in compliance_tests()] +
            [(f"execution/{n}", f) for n, f in execution_tests()])
```

Expected drift: the odds plan appended its term after the compliance one, so the closing line is the odds term.
Then the old text is (re-read the file and use the line as it stands, if the odds plan spelled it differently):

```python
            [(f"odds/{n}", f) for n, f in odds_tests()])
```

and the new text:

```python
            [(f"odds/{n}", f) for n, f in odds_tests()] +
            [(f"execution/{n}", f) for n, f in execution_tests()])
```

`tests/run_all.py`, edit 3, anchor: the `--suite` line of `main()` (hint :113). At `5816d3c` the old text is:

```python
    parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance")
```

and the new text:

```python
    parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance or execution")
```

Expected drift: after the odds plan (its Task 1: "..., grokteam, compliance or odds") the old text is:

```python
    parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance or odds")
```

and the new text (`execution` last, the `or` moved; the help stays one line, which `CG._suite_names` reads):

```python
    parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance, odds or execution")
```

`README.md`, anchor: the `--suite macro` line of the Verification block (hint :816; contract 17). At `5816d3c` the old
text is:

```text
.venv/Scripts/python tests/run_all.py --suite macro    # one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance
```

and the new text:

```text
.venv/Scripts/python tests/run_all.py --suite macro    # one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance or execution
```

Expected drift: after the odds plan the old text is:

```text
.venv/Scripts/python tests/run_all.py --suite macro    # one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance or odds
```

and the new text:

```text
.venv/Scripts/python tests/run_all.py --suite macro    # one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance, odds or execution
```

Do not touch the README suite table or its **Total** line here: Task 13 adds the execution row.

For each anchor that had drifted, add one line under "## Drift rulings" of the ledger, with the Edit tool (the ledger
is LF), for example:

```text
- Task 1: tests/run_all.py tests() and --suite help, README.md:816: the odds plan had appended odds after compliance;
  execution was appended after odds (the same change on the current text).
```

Line-ending check right after the edits:

```bash
git diff --stat
git diff --stat --ignore-cr-at-eol
```

The two outputs must be identical, with these counts (git aligns the columns; the new files are untracked, so they
are not counted here):

```
 README.md                 |  2 +-
 core/ficc/context_log.py  |  3 ++-
 tests/acceptance.py       |  7 ++++---
 tests/macro_m0_harness.py | 14 +++++++++++---
 tests/run_all.py          |  6 ++++--
 5 files changed, 22 insertions(+), 10 deletions(-)
```

If they differ, an edit converted line endings: `git checkout -- <file>` and redo that file's edits with the Edit
tool.

- [ ] **Step 4b: Run to verify it passes**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/; echo "exit $?"
```

Expected, ending: `18/18 passed, 0 failed, 0 not run` and `exit 0`.

The suite through the real runner (KEYLESS; restore the results file):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite execution; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected last lines: `18/18 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` and `exit 0`.

Regression: every caller of `runtime_py()` and the earlier suites' registration checks. The cockpit suite holds
test_08, test_09, test_16 and test_18:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected last lines: `47/47 passed, 0 failed, 0 not run; ...qa\acceptance_results.json` and `exit 0` (README's cockpit
row says 47 PASS; no earlier plan adds a cockpit test).

The compliance suite (its `test_suite_is_registered_in_run_all_and_readme` reads both suite lists through
`_suite_names`, and its `test_isolation_report_clean_and_prefixes_active` runs the static T-CTX-01 scan):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

Expected: `0 failed` and `exit 0`; the PASS and NOT_RUN counts equal those of README's compliance row (the merged
follow-up and odds plans set them).

The odds suite's registration twin alone (the odds suite as a whole takes about 3 minutes and is not needed here):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/test_suite_is_registered_in_run_all_and_readme; echo "exit $?"
```

Expected, ending: `1/1 passed, 0 failed, 0 not run` and `exit 0`. If it reports `0/0` (the odds plan named the test
differently), find it with `grep -n "def test_suite_is_registered" tests/odds_*.py` and run that name. If it FAILS
because it pins a literal such as `compliance or odds` instead of reading the list with `_suite_names`, stop and rule:
the edits above are right, and loosening an odds test is a change to another plan's file.

T-RO-01 once more on the final tree:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_m0_harness import test_t_ro_01_no_order_cancel_withdrawal_or_transfer_path as t, test_t_ro_01_orders_module_reached_only_through_the_engine as u; t(); u(); print('T-RO-01 ok')"
```

Expected: `T-RO-01 ok`.

- [ ] **Step 5: Commit**

```bash
git status --short
```

Expected exactly these ten entries, in any order (`qa/acceptance_results.json` must NOT be among them; an untracked
plan file under `docs/superpowers/plans/` is allowed and is not staged):

```
 M README.md
 M core/ficc/context_log.py
 M tests/acceptance.py
 M tests/macro_m0_harness.py
 M tests/run_all.py
?? docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
?? execution/
?? tests/execution_acceptance.py
?? tests/execution_fixtures.py
?? tests/execution_guards.py
```

The stat comparison cannot see a CRLF or a BOM in a NEW file, so check the four new text files directly first:

```bash
.venv/Scripts/python.exe -c "import pathlib; [print(p, pathlib.Path(p).read_bytes().count(b'\r'), pathlib.Path(p).read_bytes()[:3] == b'\xef\xbb\xbf') for p in ('tests/execution_acceptance.py', 'tests/execution_fixtures.py', 'tests/execution_guards.py', 'docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md')]"
```

Expected, one line per file, each ending `0 False` (no carriage return, no BOM). Otherwise rewrite that file with LF
endings and no BOM before staging.

```bash
git add execution/__init__.py tests/execution_acceptance.py tests/execution_fixtures.py tests/execution_guards.py docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md tests/acceptance.py tests/macro_m0_harness.py core/ficc/context_log.py tests/run_all.py README.md
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

The two stat outputs must be identical, with these counts (git scales the +/- bars to the terminal; compare the counts. The ledger
gains one line, and the total one insertion, per drift-ruling line recorded):

```
 README.md                                                                |   2 +-
 core/ficc/context_log.py                                                 |   3 ++-
 docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md |  13 +
 execution/__init__.py                                                    |   0
 tests/acceptance.py                                                      |   7 ++++---
 tests/execution_acceptance.py                                            | 135 +
 tests/execution_fixtures.py                                              |  70 +
 tests/execution_guards.py                                                | 652 +
 tests/macro_m0_harness.py                                                |  14 +++++++++++---
 tests/run_all.py                                                         |   6 ++++--
 10 files changed, 892 insertions(+), 10 deletions(-)
```

Then commit (the trailer names the model that actually writes the commit, for example Claude Sonnet 5.5):

```bash
git commit -m "feat(execution): package skeleton, execution suite and file-exact guard widening" -m "Adds the empty execution package, the never-live execution suite with its static guards, runtime_py over execution/ with file-exact T-RO-01 and test_09 exceptions, the execution. acting prefix, the run_all and README registration and the E1 execution ledger." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

Expected: the new commit on `e1-account-inquiry`, and `git status --short` prints nothing (or only the untracked plan
file).
