### Task 1: Branch, packages, odds suite, odds guards, registration

**Files:**
- Create: `core/odds/__init__.py` (0 bytes; joins the D14 closure)
- Create: `core/oddsdata/__init__.py` (0 bytes; unsigned)
- Create: `tests/odds_acceptance.py` (LF, UTF-8, no BOM)
- Create: `tests/odds_fixtures.py` (LF, UTF-8, no BOM; in Step 3, so its test is seen failing first)
- Create: `tests/odds_guards.py` (LF, UTF-8, no BOM)
- Create, untracked until Task 19: `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` (LF)
- Modify: `tests/run_all.py` (CRLF, kept; anchors: the suite import block, its `compliance_acceptance` line; the
  function `tests()`; the function `main()`, its `--suite` argument line)
- Modify: `README.md` (CRLF, kept; anchor: the `## Verification` code block, its `--suite macro` line, the
  "one suite:" list, README.md:816 at `5816d3c`)
- Test: `tests/odds_guards.py` (18 tests)

`core/odds/__init__.py` joins the D14 code closure, so the code hash moves. No `code_approved` exists yet (owner act 1
is not done), so nothing is re-signed. `tests/` is outside the closure and outside every repo-wide scan.

**Interfaces:**
- Consumes (repo, verified on `5816d3c` and on a sandbox copy with the follow-up's Task 1 edits applied):
  - `tests.macro_acceptance`: `hermetic()` (re-entrant context manager; every network touchpoint raises),
    `_boom(*a, **k)` (raises `HermeticViolation`), `_MISSING` (sentinel object), `_DEPTH: int`.
  - `tests.compliance_fixtures.temp_home() -> Iterator[Path]` (a fresh `TRADEGEN_HOME`, removed afterwards).
  - `tests.compliance_guards` as merged by the follow-up (names reused under the DRIFT RULE, none renamed by the
    follow-up): `_sources(*bases) -> dict[str, str]`, `_walk(node, funcs=())` (yields `(node, enclosing function
    names)`), `_imports(rel, tree)` (yields `(node, absolute module, imported names, enclosing functions)`),
    `_raw_hits(rel, src, ci=RAW_CI, cs=RAW_CS)`, `_dynamic_hits(rel, src)`, `_dynamic_module(target) -> bool`
    (follow-up F1/R9), `_init_hits(path) -> list[str]`, `_suite_names(text) -> list[str]` (follow-up R7; its name and
    signature are fixed, E1 imports it too), and the lists `RAW_CI`, `RAW_CS`, `CLOCKS`, `NETWORK_MODULES`,
    `DYNAMIC_MODULES`, `FORBIDDEN_MODULES`, read at test time with no entry count pinned.
  - `tests.run_all.run(entries) -> list[dict]`, `tests.run_all.tests()`, `tests.run_all.select(entries, *,
    milestone=None, suite=None)`.
  - `core.compliance.owner.code_files(repo_root) -> list[tuple[str, str]]` (seeds `core/compliance/*.py` and
    `core/odds/*.py` with a non-recursive glob, follows every in-repo import at any depth, adds ancestor
    `__init__.py` files and `venv:` RECORD rows).
- Produces (later tasks rely on these exact names):
  - `core/odds/__init__.py`, `core/oddsdata/__init__.py`: 0 bytes, forever.
  - `tests/odds_acceptance.py` (contract 3.1): `TESTS: Path`, `MODULES` (the 15 stems of contract 3.1),
    `_REAL_HOMES: tuple[Path, Path]`, `_REPO_FILES: tuple[str, ...]`, `_BARS: Path` (private: the
    `core/oddsdata/bars.py` path whose existence turns the seam patch on; the self-test swaps it), `SEAMS`,
    `REAL_SEAMS: dict[str, Callable]`, `_real_listing() -> tuple`, `_repo_listing() -> tuple`, `_patch_seams() ->
    tuple`, `_restore_seams(patched) -> None`, `_wrap(fn) -> Callable[[], None]`, `tests() -> list[tuple[str,
    Callable[[], None]]]`, `_main(argv: list[str]) -> int`; the command `.venv/Scripts/python.exe -m
    tests.odds_acceptance [substring]`. Task 15's seam-body tests call `tests.odds_acceptance.REAL_SEAMS[name]`.
  - `tests/odds_fixtures.py` (contract 3.2): `chunk(n: int = 2_000) -> Iterator[None]` (swaps
    `core.odds.simulate.CHUNK`, `DEFAULT_PATHS` (a dict track -> paths) and `GARCH_SUB`) and `pilots(n: int = 2_000,
    nodes: int = 64) -> Iterator[None]` (swaps `core.odds.models.PILOT_PATHS`, `core.odds.simulate.TILT_PILOT` and
    `core.odds.models.PILOT_NODES`). Both look the module up with `importlib.import_module` when entered, so this
    file imports nothing from `core/odds` at load. Contract sections 7.4 and 8.1 define those six names (the tasks
    that create `models.py` and `simulate.py`); Tasks 5, 9 and 13 append fixtures to this file.
  - `tests/odds_guards.py` (contract 15): the checkers `_core_import_hits(rel, src, root=ROOT)`,
    `_core_io_hits(rel, src)`, `_clock_hits_in(rel, src, allowed=())`, `_main_hits(rel, src, allowed=())`,
    `_reexport_hits(rel, src, root=ROOT)`, `_data_import_hits(rel, src)`, `_unchecked_write_hits(rel, src)`; the
    private helpers `_files`, `_under`, `_targets`, `_is_module_file(dotted, root=ROOT) -> bool` (not
    `owner._module_file(root, dotted) -> Path | None`), `_imported_names(dotted, root) -> set[str]`,
    `_core_allowed`, `_aliases(tree) -> dict[str, str]`, `_write_kind(node, alias) -> str`, `_own_nodes`,
    `_is_checked_target`, `_end`, `_layout_hits`, `_closure_hits`, `_probe_tree`; the constants `X`, `XD`, `RUN`,
    `_CORE_FILES`, `_CORE_OTHER`, `_COMPLIANCE_MODULES`, `_FILE_MODULES`, `_CORE_ALSO_BANNED`, `_IO_ATTRS`,
    `_MORE_CLOCKS`, `_ODDSDATA_BANNED`, `_WRITE_ATTRS`, `_MODULE_WRITES`, `_DATA_LAYER`; and 18 `test_*` functions.
    Every later task's code must pass them (Tasks 5 to 18 run `odds_guards/`).
  - The `odds/` prefix in `tests/run_all.py` (`--suite odds`) and "odds" in both hand-written suite lists.
  - The local branch `odds-engine`, cut from the merged main in Step 1b; every later task commits on it. No task
    pushes: the controller pushes after each review (G3-3).
  - The execution ledger with its sections `## Base`, `## Merged line numbers ...`, `## Drift rulings`,
    `## Deferred minors`, `## Runs`; later tasks append to the last three, and Task 2's Step 4 compares its scan
    counts with the `## Runs` lines written here.

**Plan decisions used:** Q1 (O1: flat signed core, 0-byte inits, the closure holds no data layer), Q2 (O2: odds-own
guards with a positive control each), Q13 and Q40 (O13: the suite, `_wrap`, the seams and `REAL_SEAMS`, the
watches, registration, budgets), Q16 (the follow-up runs first; R2-11), R2-6 (the oddsdata import ban on
`gate_ledger` and `macro_artifacts`), R2-10 (`pstats` and `tracemalloc` bind `core/odds` through the merged lists),
R2-13 (the DRIFT RULE, the ledger and its drift list), RULINGS_ROUND3 G3-3 (the controller pushes; no subagent
pushes). Spec 8.o: setup ("Existing guards stay in force").

Notes for the implementer (read before Step 1):
- Every command runs from the repo root `C:/Users/whydi/OneDrive/Desktop/TRADEGEN` in Git Bash (the Bash tool). Run
  the overlap check before EVERY Python command (Global Constraints). It must print nothing; otherwise wait and run it
  again. With the PowerShell tool:
  `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
  or as a Git Bash prefix:
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`
- Create the three test files with the Write tool (it writes LF; `.gitattributes` is `* -text`, so git converts
  nothing). Edit `tests/run_all.py` and `README.md` with the Edit tool only, never `sed -i` (it strips CRLF here).
  Write the Step 1c script to a file outside the repo with the Write tool and run it from there: this Bash tool turns
  a `\\` inside a heredoc into `\`, so never paste Python into a heredoc.
- What binds what. The compliance guards keep their scopes: `test_raw_text_has_no_forbidden_words` and
  `test_no_forbidden_module_import` already scan `core/odds` (raw words, forbidden, star and dynamic imports, bare
  `compile`, `importlib.<attr>`), and `test_package_init_is_empty` checks `core/odds/__init__.py` once it exists. The
  odds guards add, over `core/odds/*.py`: the O1 import allowlist, no clock, no `__main__` test, no file I/O, no
  package re-export, the Q1 file set and no subfolder; over `core/oddsdata/*.py`: the raw words, the import ban, the
  clock only in `run.py`'s `main()`, the one exact `__main__` block in `run.py`, every write after
  `checked_target`; and the D14 closure check. They read the compliance lists at test time, so the follow-up's
  merged `NETWORK_MODULES` (26 entries, `xml.dom` and `ctypes` among them) and `DYNAMIC_MODULES` (29 entries,
  `importlib`, `pstats` and `tracemalloc` among them) bind `core/odds` with no change here. Every DYNAMIC test goes
  through `CG._dynamic_module`, never a raw prefix match, because the merged list holds the entry `importlib` and
  `importlib.metadata` must stay legal.
- Eight readings this task makes where the contract's text is open; each only refuses more, and the coordinator may
  strip any of them. A cross-scan of every drafted product block of Tasks 5 to 18 (sandbox) found no planned code
  that any of them refuses:
  1. `_CORE_ALSO_BANNED` keeps `subprocess`, `_winapi`, `nt`, `posix`, `_io` (a process, or the `os` and `io` file
     API under its C name), `numpy.ctypeslib` (native code) and `codeop`, `dis`, `_frozen_importlib`,
     `_frozen_importlib_external`, `_imp`, `_interpreters` (the follow-up's "left to review" string-exec routes) out
     of `core/odds`. No planned core module needs any of them.
  2. `core.compliance` imports are limited to the four modules O1 names (`model`, `rules`, `gate`, `owner`); an
     import of `core.compliance.alerts` is refused. A name taken from an allowed repo module (`core.isolation`, those
     four, a `core.odds` module) must be its own: one that module binds by an import statement is refused
     (`from core.isolation import os`, `from core.compliance.rules import yaml`, `from core.compliance.owner import
     _dt`), since through it the core would reach a module the allowlist refuses.
  3. `test_core_odds_is_flat` also checks that `core/odds` holds only the Q1 files (`__init__.py`, `plan.py`,
     `costs.py`, `models.py`, `simulate.py`, `bold.py`, `report.py`, `venues.yaml`, plus `__pycache__`).
  4. The name `open` counts as file I/O only when it is read (a call or a reference such as `g = open`), so the
     field `Series.open` of contract 5.2 (`open: tuple[float, ...]`, a store) stays legal. A later task that wants a
     local variable for the opens must not call it `open`.
  5. Two tests beyond the list of contract 15: `test_oddsdata_main_block_only_in_run` (the section 0 rule "the only
     `__main__` block is run.py's") and `test_chunk_and_pilots_swap_their_sizes_and_restore_them` (the contract 3.2
     swaps, on stand-in modules, since `simulate.py` and `models.py` come later).
  6. No file I/O by an import route: `_FILE_MODULES` adds `builtins` (its `open`), `scipy.io`, `numpy.lib.npyio`,
     `numpy.lib.format` and their private homes `numpy.lib._npyio_impl` and `numpy.lib._format_impl` (numpy 2.3.5)
     to the sixteen of section 0; `_core_io_hits` also refuses an `_IO_ATTRS` name imported from any module
     (`from numpy import load`, `from json import load`) and any read of the name `__builtins__`; `_IO_ATTRS` adds
     `fromregex` and `open_memmap`.
  7. More clock readers (spec 7.3), for `core/odds` and for `core/oddsdata` outside `run.py`'s `main()`:
     `_MORE_CLOCKS` (`email.utils.localtime` and `formatdate`, `uuid.uuid1`, pandas `Timestamp.now`, `today`,
     `utcnow`, also imported by name) and a `datetime64` or `Timestamp` call whose first argument is `'now'` or
     `'today'`.
  8. More write forms for `core/oddsdata` (O2): the methods `.touch`, `.unlink`, `.rmdir`, `.symlink_to`,
     `.hardlink_to`, `.tofile`; `.replace(t)` and `.rename(t)` with one positional argument and no keyword (Path's,
     never `dataclasses.replace(c)` on an imported name); and `_MODULE_WRITES`, the `os`, `shutil` and `numpy`
     functions that write, rename or delete, resolved through the file's own import aliases (`import os as o`,
     `from os import replace`). zipfile, tarfile, tempfile, sqlite3 and dbm writers stay left to review.
- `tests/odds_acceptance._main` differs from the compliance one in one line: it takes the entries from the imported
  `tests.odds_acceptance`, not from the `__main__` copy that `-m` runs, so `REAL_SEAMS` and the watch lists the
  self-tests read are the ones the wrapper uses.
- The wrapper watches the real `~/.tradegen/compliance` as the compliance wrapper does. If a FAIL reads
  `the test touched the real ~/.tradegen/odds or compliance: [(1, 'alerts.jsonl', ...` and the run spanned 09:00 KST,
  the daily alert job wrote during the run (compliance ledger:67, a deferred minor): write one ledger line and run
  again outside that time. Any other real-home or repo-file FAIL is a bug: stop and report.

- [ ] **Step 1: Check the base, create the branch, start the ledger, then write the failing tests**

  **1a. The base (R2-11, Q16).** The follow-up has merged into `main`, and this plan's files do not exist yet. The
  controller brings local `main` to the merged state before Task 1 (G3-3); this task makes no network call and runs
  no `git fetch`, `git pull`, `git merge` or `git push`. Switch to it:

```bash
git switch main
git status --short
```

  Expected: `Switched to branch 'main'` (or `Already on 'main'`), then nothing. Stop and report to the controller if
  any file is listed. Then:

```bash
git log --oneline -1
git ls-files --error-unmatch docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md
git grep -n -F "paper, grokteam or compliance" -- tests/compliance_guards.py; echo "grep exit $?"
git ls-files core/odds core/oddsdata 'tests/odds_*'
test ! -e core/odds/__init__.py && test ! -e core/oddsdata && echo "no odds package yet"
git ls-files --eol tests/run_all.py README.md
```

  Expected: the follow-up's merge as the last commit (a merge made by pull request reads `Merge pull request #<n>
  from ...`; stop and report to the controller if `main` does not hold the follow-up merge); the follow-up ledger's
  path (it is tracked, so the merge holds the follow-up's last commit); `grep exit 1`
  (F7 replaced the literal with `_suite_names`); exactly `core/odds/venues.yaml`; `no odds package yet`; and two
  lines starting `i/crlf  w/crlf`. Overlap check, then (the Python line checks every merged list entry that a
  positive control of Step 1d relies on: `xml.dom` and `ctypes` in `NETWORK_MODULES`; `importlib`, its submodules
  but `importlib.metadata`, `pickle`, `pstats` and `tracemalloc` through `_dynamic_module`):

```bash
.venv/Scripts/python.exe -c "from tests import compliance_guards as CG; ok = all(CG._dynamic_module(m) for m in ('importlib', 'importlib.resources', 'pickle', 'pstats', 'tracemalloc')) and not CG._dynamic_module('importlib.metadata') and {'xml.dom', 'ctypes'} <= set(CG.NETWORK_MODULES) and CG._suite_names('# one suite: a or b') == ['a', 'b']; print('follow-up guards merged' if ok else 'STOP: the follow-up guards are not on main'); raise SystemExit(0 if ok else 1)"
git diff --stat 5816d3c HEAD -- . ':!docs'
```

  Expected: `follow-up guards merged`, then a stat list of the files the follow-up changed outside docs/ (followup
  CONTRACT section 12: `core/compliance/rules.py`, `owner.py`, `alerts.py`, `kr_rules.yaml`,
  `tests/compliance_guards.py`, `tests/compliance_tables.py`, `tests/compliance_store.py`,
  `tests/compliance_signer.py`, `tests/compliance_cli.py`, `tests/compliance_isolation.py`, `tools/signer/sign.py`,
  `data/krx/kis_client.py`, `core/ficc/data.py`, `README.md`, and `qa/acceptance_results.json` from its full run). A
  file outside that list is not an error: the ledger records it and the DRIFT RULE covers it. Stop and report to the
  controller if any check above fails (an `AttributeError` from the Python line counts as a failure), or if the
  stat names a path under `core/odds/`, `core/oddsdata/` or `tests/odds_`: then the base is not the merged
  follow-up, or another run has started building this plan.

  **1b. The branch.** No `odds-engine` branch may exist yet, local or remote-tracking (read from the local
  repository; nothing is fetched):

```bash
git branch -a --list '*odds-engine'
```

  Expected: nothing. If it prints `odds-engine` or `remotes/origin/odds-engine`, stop and report; never
  `git switch -C`, never delete a branch, local or remote. Otherwise:

```bash
git switch -c odds-engine
git branch --show-current
```

  Expected: `Switched to a new branch 'odds-engine'`, then `odds-engine`.

  **1c. The execution ledger (R2-13).** Save this script with the Write tool as `odds_start_ledger.py` in a scratch
  folder outside the repo (your session scratchpad), then, overlap check, run it from the repo root with
  `.venv/Scripts/python.exe -I <that folder>/odds_start_ledger.py` (`-I` keeps a stray `ast.py` or `subprocess.py`
  in that folder from shadowing the stdlib; the relative paths still resolve against the repo root). It reads the
  tree and git (read-only), writes the ledger once (LF) and prints it; it refuses to overwrite an existing ledger.

```python
"""Odds plan Task 1: start the execution ledger (LF) from the merged main, with the drift list and the merged line
numbers of every name the contract cites by line. Run once from the repo root; it refuses to overwrite."""
import ast
import datetime
import subprocess
from pathlib import Path

LEDGER = Path("docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md")
FENCE = "`" * 3                      # a markdown code fence, spelled so this script can sit inside one
if LEDGER.exists():
    raise SystemExit(f"STOP: {LEDGER} exists already: continue it, never overwrite it")


def git(*args: str) -> str:
    out = subprocess.run(["git", *args], check=True, capture_output=True, text=True, encoding="utf-8").stdout
    return out.rstrip("\n")


def top(rel: str, name: str):
    """(first, last) line of the top-level def, class or assignment `name` in `rel`; None when it is gone."""
    for n in ast.parse(Path(rel).read_bytes()).body:
        names = [n.name] if isinstance(n, (ast.FunctionDef, ast.ClassDef)) else [
            t.id for t in getattr(n, "targets", []) if isinstance(t, ast.Name)]
        if name in names:
            return n.lineno, n.end_lineno
    return None


def find(rel: str, text: str, within=None):
    """The line number of the one line of `rel` holding `text` (inside the span `within`); None unless exactly one."""
    lines = Path(rel).read_bytes().decode("utf-8").splitlines()
    lo, hi = within or (1, len(lines))
    hits = [i for i in range(lo, hi + 1) if text in lines[i - 1]]
    return hits[0] if len(hits) == 1 else None


def at(value) -> str:
    if value is None:
        return "MISSING"
    if isinstance(value, tuple):
        return str(value[0]) if value[0] == value[1] else f"{value[0]}-{value[1]}"
    return str(value)


OW, TB, ST = "core/compliance/owner.py", "tests/compliance_tables.py", "tests/compliance_store.py"
GD, GT, RA = "tests/compliance_guards.py", "core/compliance/gate.py", "tests/run_all.py"
seed = 'for sub in ("compliance", "odds")'
shape, screen, now, full = top(TB, "test_venue_shape_rules"), top(GT, "_screen"), top(ST, "NOW"), top(ST, "_full_home")
flags = find(GT, "flags = []", screen) if screen else None
flags_end = find(GT, "tuple(sorted(flags))", screen) if screen else None
rows = [
    f"- `{OW}`: `_module_file` {at(top(OW, '_module_file'))}; `code_files` {at(top(OW, 'code_files'))}, its glob "
    f"seed {at(find(OW, seed, top(OW, 'code_files')))}",
    f"- `{TB}`: `test_venue_shape_rules` {at(shape)}, its `minimum_krw` line {at(find(TB, 'minimum_krw', shape))}",
    f"- `{ST}`: `TABLES` {at(top(ST, 'TABLES'))}; `NOW` .. `_full_home` "
    f"{at((now[0], full[1]) if now and full else None)}; `test_code_files_is_the_import_closure` "
    f"{at(top(ST, 'test_code_files_is_the_import_closure'))}",
    f"- `{GD}`: `test_suite_is_registered_in_run_all_and_readme` "
    f"{at(top(GD, 'test_suite_is_registered_in_run_all_and_readme'))}; `_suite_names` {at(top(GD, '_suite_names'))}; "
    f"`_dynamic_module` {at(top(GD, '_dynamic_module'))}",
    f"- `{GT}`: `_screen` {at(screen)}, its start check {at(find(GT, 'if start != ctx.date:', screen))}, "
    f"`Screening.flags` {at((flags, flags_end) if flags and flags_end else None)}",
    f"- `{RA}`: the stdout reconfigure {at(find(RA, 'for stream in (sys.stdout, sys.stderr):'))}, the `--suite` "
    f"help {at(find(RA, 'one suite: '))}; `README.md`: the suite list {at(find('README.md', 'one suite: '))}",
]
drift = git("diff", "--stat", "5816d3c", "HEAD", "--", ".", ":!docs")
text = "\n".join([
    "# Odds engine plan: execution ledger",
    "",
    "The executor's record of the TRADEGEN odds engine plan (LF). Task 1 started it; every task adds its drift",
    "rulings, deferred minors and runs here. It stays untracked until Task 19 commits it.",
    "",
    "## Base",
    f"- Branch `{git('branch', '--show-current')}`, cut from main `{git('rev-parse', '--short', 'main')}` "
    f"({git('log', '-1', '--format=%s', 'main')}) on {datetime.date.today().isoformat()}.",
    "- The plan was written against main `5816d3c` (equal to `995534b` outside docs/).",
    "- Files changed outside docs/ since `5816d3c` (`git diff --stat 5816d3c HEAD -- . ':!docs'`), where the DRIFT",
    "  RULE can apply:",
    "",
    FENCE + "text",
    drift or "(none)",
    FENCE,
    "",
    "## Merged line numbers (Task 1; cited by line in the contract as of 995534b)",
    *rows,
    "",
    "## Drift rulings",
    *[f"- open: {r[2:].split(':', 1)[0]} has a MISSING anchor; rule before the task that edits or reuses it runs"
      for r in rows if "MISSING" in r],
    "",
    "## Deferred minors",
    "",
    "## Runs",
    "",
])
LEDGER.write_bytes(text.encode("utf-8"))
print(text)
```

  Expected: the printed ledger names branch `odds-engine` and the merged main, holds the stat list of 1a in its
  `text` block, and has six "Merged line numbers" rows with no `MISSING`. As of 995534b the rows read `_module_file`
  739-747, `code_files` 767-793 with its seed 773, `test_venue_shape_rules` 604-642 with `minimum_krw` 633, `TABLES`
  21, `NOW` .. `_full_home` 242-299, the closure test 130-150, `_screen` 622-651 with the start check 638 and the
  flags 644-651, the stdout reconfigure 35, the help 113 and the README list 816; after the follow-up, the
  `tests/compliance_guards.py` row reads about `_dynamic_module` 163-167, `_suite_names` 542-546 and the
  registration test 549-558, and the other numbers are whatever the merge left. If a row says `MISSING`, the
  script has already written an `open:` line under "Drift rulings": finish this task (it edits none of those
  files) and report the row to the controller before Task 2. `git status --short` now prints exactly
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.

  **1d. The suite and the guards.** (`tests/odds_fixtures.py` waits for Step 3b, so its test is seen failing.)
  Create `tests/odds_acceptance.py` (LF) with exactly:

```python
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
```

  Create `tests/odds_guards.py` (LF) with exactly:

```python
"""Static guards over core/odds and core/oddsdata, the D14 closure check, the suite registration and the harness
self-tests: odds plan Task 1 (contract sections 0, 3 and 15; RULINGS O1, O2, O13; RULINGS_ROUND2 R2-6, R2-10).

Each guard is a pure checker `(rel, source) -> [hit, ...]`. Every test first proves its checker catches a synthetic
offender under `core/odds/x.py` (X) or `core/oddsdata/x.py` (XD), the positive control, then asserts the shipped files
are clean. The compliance guards keep their own scopes (they already scan core/odds for raw words, forbidden and
dynamic imports); these add the O1 import allowlist of the signed core, its purity (no clock, no `__main__` block, no
file I/O, no package re-export, no subfolder) and the rules of the unsigned loaders. The lists come from
tests/compliance_guards.py at test time, so the follow-up's additions (pstats and tracemalloc, R2-10) bind core/odds
with no change here. Every import statement is checked, including a name taken from an allowed repo module that it
only imports itself (`from core.isolation import os`). Like every guard here, a denylist read by a scan, not a proof:
an attribute route through an allowed module (`isolation.os.remove(p)`, `scipy.io.loadmat(p)`), `getattr(module,
"name")`, a name assigned from an import (`_os = os` in an allowed module), a clock or a write reached any other way
than the forms listed in each checker, and code run by injected objects are left to review.
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import sys
import types
from pathlib import Path

from tests import compliance_guards as CG

ROOT = Path(__file__).resolve().parents[1]
ODDS, ODDSDATA = ROOT / "core" / "odds", ROOT / "core" / "oddsdata"
X, XD = "core/odds/x.py", "core/oddsdata/x.py"          # the names a synthetic offender is checked under
RUN = "core/oddsdata/run.py"                            # the one file whose main() may read the clock (O15)
# Q1: everything core/odds may hold (a __pycache__ folder appears when it is imported)
_CORE_FILES = ("__init__.py", "plan.py", "costs.py", "models.py", "simulate.py", "bold.py", "report.py")
_CORE_OTHER = ("venues.yaml", "__pycache__")
_COMPLIANCE_MODULES = ("model", "rules", "gate", "owner")   # O1: the compliance modules the core may import
# The file-I/O modules the signed core never imports: the sixteen of contract section 0, builtins (its open), scipy.io
# and the public and private numpy homes of np.load and open_memmap.
_FILE_MODULES = ("io", "os", "pathlib", "shutil", "tempfile", "glob", "fileinput", "mmap", "sqlite3", "dbm", "csv",
                 "zipfile", "tarfile", "gzip", "bz2", "lzma", "builtins", "scipy.io", "numpy.lib.npyio",
                 "numpy.lib.format", "numpy.lib._npyio_impl", "numpy.lib._format_impl")
# The modules that run a process or native code, reach the OS file API under another name or compile a string, which
# no core/odds file needs either.
_CORE_ALSO_BANNED = ("subprocess", "_winapi", "nt", "posix", "_io", "codeop", "dis", "_frozen_importlib",
                     "_frozen_importlib_external", "_imp", "_interpreters", "numpy.ctypeslib")
# names that read or write a file, called as an attribute (np.load, Path.read_text) or imported by name (from numpy
# import load); `.replace` only on the name os
_IO_ATTRS = frozenset({"open", "read_text", "read_bytes", "write_text", "write_bytes", "mkdir", "unlink", "rename",
                       "load", "save", "savez", "savez_compressed", "loadtxt", "savetxt", "genfromtxt", "fromregex",
                       "fromfile", "tofile", "memmap", "open_memmap"})
# clock readers beyond compliance_guards.CLOCKS (spec 7.3), keyed like it by the name before the dot
_MORE_CLOCKS = {"utils": {"localtime", "formatdate"}, "uuid": {"uuid1"}, "Timestamp": {"now", "today", "utcnow"}}
# what core/oddsdata never imports, beyond compliance_guards.FORBIDDEN_MODULES (O1, O2, R2-6)
_ODDSDATA_BANNED = ("core.engine", "docs.asset_expansion_study", "asset_expansion_study", "core.quant.gate_ledger",
                    "core.ficc.macro_artifacts")
# what writes, renames or deletes a file in core/oddsdata: methods on any object, and module functions
_WRITE_ATTRS = frozenset({"write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir", "symlink_to",
                          "hardlink_to", "tofile"})
_MODULE_WRITES = {"os": frozenset({"replace", "rename", "renames", "makedirs", "mkdir", "remove", "removedirs",
                                   "unlink", "rmdir", "link", "symlink", "truncate"}),
                  "shutil": frozenset({"copy", "copy2", "copyfile", "copytree", "copymode", "copystat", "move",
                                       "rmtree"}),
                  "numpy": frozenset({"save", "savez", "savez_compressed", "savetxt"})}
_DATA_LAYER = ("core/oddsdata/", "data/", "config.py", "core/quant/", "core/calendars/", "core/engine/")


# --------------------------------------------------------------------------- #
# Scope and helpers
# --------------------------------------------------------------------------- #
def _files(base: Path) -> dict[str, str]:
    """rel path -> source of every .py file under `base`; its __init__.py must be among them, so a moved or renamed
    package cannot empty the scan."""
    files = CG._sources(base)
    init = (base / "__init__.py").relative_to(ROOT).as_posix()
    assert init in files, f"scan scope: {init} missing"
    return files


def _under(target: str, banned: tuple[str, ...]) -> bool:
    """A dotted name equal to, or below, an entry of `banned` (`os.path` is below `os`; `iox` is not)."""
    return any(target == m or target.startswith(m + ".") for m in banned)


def _targets(module: str, names: tuple[str, ...]) -> list[str]:
    """The dotted names one import binds: `from a import b` is `a.b`, `import a.b` is `a.b`."""
    return [f"{module}.{n}" for n in names] or [module]


def _is_module_file(dotted: str, root: Path = ROOT) -> bool:
    """`dotted` names a module FILE under `root` (core.compliance.rules), never a package (core.odds) or a name.
    (Not owner._module_file, which takes (root, dotted) and returns the path.)"""
    parts = dotted.split(".")
    return all(p.isidentifier() for p in parts) and root.joinpath(*parts[:-1], parts[-1] + ".py").is_file()


def _imported_names(dotted: str, root: Path) -> set[str]:
    """Every name the module file `dotted` binds by an import statement, at any depth (core.isolation: os, Path)."""
    tree = ast.parse(root.joinpath(*dotted.split(".")).with_suffix(".py").read_bytes())
    return {a.asname or a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
            for a in n.names}


def _core_allowed(target: str, root: Path) -> bool:
    """O1: the stdlib minus the network, dynamic, file-I/O and process modules; numpy and scipy minus their file
    modules; core.isolation; an existing module file of core.odds; core.compliance's model, rules, gate and owner. A
    name taken from one of those repo modules must be its own, not a module or name it imports (`from core.isolation
    import os`, `from core.compliance.rules import yaml`)."""
    parts = target.split(".")
    if _under(target, _FILE_MODULES + _CORE_ALSO_BANNED):
        return False
    if parts[0] in ("numpy", "scipy"):
        return True
    if parts[0] == "core":
        n = 2 if parts[1:2] == ["isolation"] else 3     # the module file: core.isolation or core.<pkg>.<mod>
        mine = len(parts) >= n and (n == 2 or parts[1] == "odds"
                                    or (parts[1] == "compliance" and parts[2] in _COMPLIANCE_MODULES))
        module, name = ".".join(parts[:n]), ".".join(parts[n:n + 1])
        return (mine and _is_module_file(module, root)
                and not (name and name in _imported_names(module, root)))
    return (parts[0] in sys.stdlib_module_names and not _under(target, tuple(CG.NETWORK_MODULES))
            and not CG._dynamic_module(target))


def _aliases(tree: ast.AST) -> dict[str, str]:
    """Name -> what it stands for, from every import of a file: `import os as o` o -> os, `import os.path` os -> os,
    `from os import replace as r` r -> os.replace."""
    out = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update({a.asname or a.name.split(".")[0]: a.name if a.asname else a.name.split(".")[0]
                        for a in n.names})
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.update({a.asname or a.name: f"{n.module}.{a.name}" for a in n.names})
    return out


def _write_kind(node: ast.AST, alias: dict[str, str]) -> str:
    """What file write a call makes ("" for none), names resolved through `alias` (_aliases): `open` (or `.open`)
    with a mode holding w, a, x or +, or a mode that is not a string constant; a _WRITE_ATTRS method; a
    _MODULE_WRITES function of os, shutil or numpy; `.replace(t)` or `.rename(t)` with one positional argument and no
    keyword on anything but an imported name (Path.replace). zipfile, tarfile, tempfile, sqlite3 and dbm writers are
    left to review."""
    if not isinstance(node, ast.Call):
        return ""
    f = node.func
    if isinstance(f, ast.Name):
        dotted = alias.get(f.id, f.id)
    elif isinstance(f, ast.Attribute):
        dotted = f"{alias.get(f.value.id, f.value.id) if isinstance(f.value, ast.Name) else '?'}.{f.attr}"
    else:
        return ""
    module, _, name = dotted.rpartition(".")
    if isinstance(f, ast.Attribute) and f.attr in _WRITE_ATTRS:
        return f".{f.attr}()"
    if name in _MODULE_WRITES.get(module, ()):
        return f"{dotted}()"
    if (isinstance(f, ast.Attribute) and f.attr in ("replace", "rename") and len(node.args) == 1 and not node.keywords
            and not (isinstance(f.value, ast.Name) and f.value.id in alias)):
        return f".{f.attr}(target)"
    if name != "open":
        return ""
    # open(file, mode) and io.open / os.open / gzip.open (file, mode); path.open(mode)
    at = 1 if module in ("", "io", "os", "builtins", "codecs", "gzip", "bz2", "lzma") else 0
    mode = next((k.value for k in node.keywords if k.arg in ("mode", "flags")),
                node.args[at] if len(node.args) > at else None)
    if mode is None:
        return ""                                       # the default mode "r" reads
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and not set(mode.value) & set("wax+"):
        return ""
    return "open() for writing"


def _own_nodes(fn: ast.AST):
    """Every node of a function's body, the bodies of nested functions and classes excluded."""
    stack = list(fn.body)
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))


def _is_checked_target(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (
        (isinstance(node.func, ast.Name) and node.func.id == "checked_target")
        or (isinstance(node.func, ast.Attribute) and node.func.attr == "checked_target"))


def _end(node: ast.AST) -> tuple[int, int]:
    return node.end_lineno, node.end_col_offset


# --------------------------------------------------------------------------- #
# Checkers: (rel, source) -> hits
# --------------------------------------------------------------------------- #
def _core_import_hits(rel: str, src: str, root: Path = ROOT) -> list[str]:
    """Every import of a core/odds file outside the O1 allowlist (`root` locates the module files)."""
    hits = []
    for node, module, names, _f in CG._imports(rel, ast.parse(src)):
        bad = [t for t in _targets(module, names) if "*" in names or not _core_allowed(t, root)]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}: outside the O1 allowlist (stdlib minus network, "
                        "dynamic and file modules; numpy; scipy; core.isolation; core.compliance and core.odds "
                        "modules; never a name such a module only imports)")
    return hits


def _core_io_hits(rel: str, src: str) -> list[str]:
    """File I/O in a core/odds file: a file-I/O module imported, an _IO_ATTRS name imported from any module (`from
    numpy import load`), the name `open` or `__builtins__` read (a call or a reference; the field `Series.open` is a
    store and stays legal), an _IO_ATTRS attribute call, os.replace."""
    tree, hits = ast.parse(src), []
    for node, module, names, _f in CG._imports(rel, tree):
        bad = [t for t in _targets(module, names) if _under(t, _FILE_MODULES)]
        bad += [f"{module}.{n}" for n in names if n in _IO_ATTRS]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}: the core reads and writes no file")
    for node, _f in CG._walk(tree):
        if isinstance(node, ast.Name) and node.id in ("open", "__builtins__") and isinstance(node.ctx, ast.Load):
            hits.append(f"{rel}:{node.lineno}: {node.id}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr, base = node.func.attr, node.func.value
            if attr in _IO_ATTRS or (attr == "replace" and isinstance(base, ast.Name) and base.id == "os"):
                hits.append(f"{rel}:{node.lineno}: .{attr}()")
    return hits


def _clock_hits_in(rel: str, src: str, allowed: tuple[str, ...] = ()) -> list[str]:
    """compliance_guards._clock_hits with its exemption moved to `allowed`: only the BODY of a function named main
    in an allowed file may read the clock (CLOCKS and _MORE_CLOCKS, `from time import ...`, a clock imported by name,
    `datetime64('now')`, `Timestamp('today')`)."""
    clocks = {k: set(CG.CLOCKS.get(k, ())) | _MORE_CLOCKS.get(k, set()) for k in {*CG.CLOCKS, *_MORE_CLOCKS}}
    tree, hits, alias = ast.parse(src), [], {}
    for n in ast.walk(tree):                            # `import time as t`, `from datetime import date as D`
        if isinstance(n, ast.Import):
            alias.update({a.asname or a.name: a.name.rpartition(".")[2] for a in n.names
                          if a.name.rpartition(".")[2] in clocks})
        elif isinstance(n, ast.ImportFrom) and n.module == "datetime":
            alias.update({a.asname or a.name: a.name for a in n.names if a.name in clocks})
    for node, funcs in CG._walk(tree):
        if rel in allowed and "main" in funcs:
            continue
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                base = alias.get(node.value.id, node.value.id)
            else:
                base = getattr(node.value, "attr", None)
            if node.attr in clocks.get(base, ()):
                hits.append(f"{rel}:{node.lineno}: {base}.{node.attr}")
        elif isinstance(node, ast.ImportFrom) and (node.module == "time" or any(
                a.name in clocks.get((node.module or "").rpartition(".")[2], ()) for a in node.names)):
            hits.append(f"{rel}:{node.lineno}: from {node.module} import ...")
        elif (isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", None))
              in ("datetime64", "Timestamp") and node.args and isinstance(node.args[0], ast.Constant)
              and node.args[0].value in ("now", "today")):
            hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
    return hits


def _main_hits(rel: str, src: str, allowed: tuple[str, ...] = ()) -> list[str]:
    """Every comparison with `__name__` (a `__main__` test in either operand order, `!=` included), except, in an
    allowed file, one top-level block that is exactly `if __name__ == "__main__":` / `raise SystemExit(main())`."""
    tree = ast.parse(src)
    exact = {id(n.test) for n in tree.body if rel in allowed and isinstance(n, ast.If) and not n.orelse
             and ast.unparse(n.test) == "__name__ == '__main__'"
             and [ast.unparse(s) for s in n.body] == ["raise SystemExit(main())"]}
    return [f"{rel}:{n.lineno}: a __main__ test; only {allowed or 'no file'} may hold one, exactly "
            "`raise SystemExit(main())`"
            for n in ast.walk(tree) if isinstance(n, ast.Compare) and id(n) not in exact
            and any(isinstance(s, ast.Name) and s.id == "__name__" for s in (n.left, *n.comparators))]


def _reexport_hits(rel: str, src: str, root: Path = ROOT) -> list[str]:
    """An import of a core package itself (`import core.odds`), or `from core.<pkg> import <name>` where <name> is not
    a module file of that package: a package re-export hides the file it loads from the D14 seeds."""
    hits = []
    for node, module, names, _f in CG._imports(rel, ast.parse(src)):
        if module != "core" and not module.startswith("core."):
            continue
        if _is_module_file(module, root):
            continue                                    # import core.compliance.rules / from core.isolation import x
        bad = [module] if isinstance(node, ast.Import) else [
            f"{module}.{n}" for n in names if not _is_module_file(f"{module}.{n}", root)]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}, which is not a module file: import the module")
    return hits


def _layout_hits(base: Path) -> list[str]:
    """Q1: every entry of `base` that is not one of _CORE_FILES or _CORE_OTHER, and every .py file in a subfolder
    (relative to `base`): the D14 seed glob is not recursive, so a nested file would run unsigned."""
    stray = [p.name for p in base.iterdir() if p.name not in _CORE_FILES + _CORE_OTHER]
    nested = [p.relative_to(base).as_posix() for p in base.rglob("*.py") if p.parent != base]
    return sorted(stray + nested)


def _data_import_hits(rel: str, src: str) -> list[str]:
    """core/oddsdata imports: compliance_guards.FORBIDDEN_MODULES, any core.engine module, the study runner, the two
    provenance modules (R2-6) and every star or dynamic import (compliance_guards._dynamic_hits)."""
    banned, hits = tuple(CG.FORBIDDEN_MODULES) + _ODDSDATA_BANNED, []
    for node, module, names, _f in CG._imports(rel, ast.parse(src)):
        bad = [t for t in [module] + [f"{module}.{n}" for n in names] if _under(t, banned)]
        if bad:
            hits.append(f"{rel}:{node.lineno}: imports {bad[0]}")
    return hits + CG._dynamic_hits(rel, src)


def _unchecked_write_hits(rel: str, src: str) -> list[str]:
    """Every file write (see _write_kind) not preceded, in the same function, by a call to checked_target; a write
    outside any function always counts. A scan of the source order, not a proof of the path checked."""
    tree, covered = ast.parse(src), set()
    alias = _aliases(tree)
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            own = list(_own_nodes(fn))
            checks = [_end(n) for n in own if _is_checked_target(n)]
            covered |= {id(n) for n in own if _write_kind(n, alias) and checks and min(checks) < _end(n)}
    return [f"{rel}:{n.lineno}: {_write_kind(n, alias)} with no checked_target before it in the same function"
            for n in ast.walk(tree) if _write_kind(n, alias) and id(n) not in covered]


def _closure_hits(names: list[str]) -> list[str]:
    """The D14 closure entries that belong to the data layer (O1)."""
    return [n for n in names if any(n == p or n.startswith(p) for p in _DATA_LAYER)]


def _probe_tree(name: str, files: dict[str, str]) -> Path:
    """A synthetic tree under the per-test temp home (removed with it): rel path -> text."""
    root = Path(os.environ["TRADEGEN_HOME"]) / name
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(text.encode("utf-8"))
    return root


# --------------------------------------------------------------------------- #
# core/odds: the signed core
# --------------------------------------------------------------------------- #
def test_core_odds_imports_only_the_allowlist():
    """O1: the stdlib minus compliance_guards.NETWORK_MODULES and DYNAMIC_MODULES (membership through
    compliance_guards._dynamic_module, so importlib.metadata stays legal) and minus the file-I/O and process modules;
    numpy and scipy minus their file modules; core.isolation; existing module files of core.odds; core.compliance's
    model, rules, gate and owner, never a name one of them only imports. Nothing else of the repo."""
    for src in ("import config\n", "from core.quant import garch\n", "import core.oddsdata.bars\n",
                "from core.oddsdata import bars\n", "from core.calendars.store import CalendarSet\n",
                "from core.engine import books\n", "import data.krx.kis_client\n",
                "from core.ficc import macro_schema\n", "import yfinance\n", "import pandas as pd\n",
                "def f():\n    import yaml\n", "import socket\n",
                "from urllib import request\n", "from xml.dom import minidom\n", "import ctypes\n", "import os\n",
                "from pathlib import Path\n", "import csv\n", "from io import StringIO\n", "import importlib\n",
                "import importlib.util\n", "from importlib import resources\n", "import pickle\n", "import pstats\n",
                "from tracemalloc import Snapshot\n", "import subprocess\n", "import nt\n", "import dis\n",
                "from math import *\n", "import core\n", "import core.compliance\n", "from core import compliance\n",
                "import core.compliance.nosuch\n", "from core.compliance import alerts\n",
                "from core.odds import nosuch\n", "from ... import config\n",
                "from core.isolation import os\n", "from core.isolation import Path\n",
                "from core.compliance.owner import os\n", "from core.compliance.rules import yaml\n",
                "from core.compliance.owner import _dt\n", "from ..compliance.rules import Path as P\n",
                "import builtins\n", "from builtins import open as o\n", "import scipy.io\n",
                "from scipy.io import loadmat\n", "from scipy import io\n", "import numpy.lib.format as F\n",
                "from numpy.lib import npyio\n", "from numpy.lib._npyio_impl import load\n",
                "from numpy import ctypeslib\n"):
        assert _core_import_hits(X, src), src
    for banned in tuple(CG.NETWORK_MODULES) + tuple(CG.DYNAMIC_MODULES) + _FILE_MODULES + _CORE_ALSO_BANNED:
        for src in (f"import {banned}\n", f"import {banned}.x\n", f"from {banned} import x\n"):
            assert _core_import_hits(X, src), src
    ok = ("from __future__ import annotations\nimport dataclasses, functools, hashlib, json, math\n"
          "from datetime import date, timedelta\nimport fractions\nimport numpy as np\nimport numpy.random\n"
          "from scipy import stats\nfrom scipy.integrate import quad\nimport importlib.metadata\n"
          "from importlib import metadata\nimport logging\nfrom core import isolation\n"
          "from core.isolation import checked_target\nfrom core.compliance import gate, model, owner, rules\n"
          "from core.compliance.model import KST\nimport core.compliance.rules\nfrom ..compliance import model as M\n"
          "from core.compliance.rules import Venue\nimport scipy\nfrom numpy.lib import stride_tricks\n"
          "def f():\n    from core.compliance import owner\n")
    assert not _core_import_hits(X, ok), _core_import_hits(X, ok)
    tree = _probe_tree("odds_tree", {"core/odds/plan.py": "from core.compliance import model\n"})
    mine = ("from . import plan\nfrom core.odds import plan as P\nfrom core.odds.plan import Plan\n"
            "import core.odds.plan\n")
    assert not _core_import_hits(X, mine, root=tree), _core_import_hits(X, mine, root=tree)
    assert _core_import_hits(X, "from core.odds import costs\n", root=tree)
    assert _core_import_hits(X, "from core.odds.plan import model\n", root=tree)      # plan's import, not its own
    hits = [h for rel, src in _files(ODDS).items() for h in _core_import_hits(rel, src)]
    assert not hits, hits


def test_core_odds_reads_no_clock():
    """Seeds and odds never depend on time (spec 7.3): no core/odds file reads the wall clock (compliance_guards.CLOCKS,
    `from time import ...`, email.utils.localtime and formatdate, uuid.uuid1, datetime64('now'), Timestamp.now), not
    even in a main(); the time comes in as `Inputs.now`."""
    for src in ("datetime.now(timezone.utc)\n", "datetime.datetime.utcnow()\n", "date.today()\n", "time.time()\n",
                "time.perf_counter()\n", "time.monotonic_ns()\n", "from time import time\n",
                "import time as t\nx = t.time()\n", "from datetime import datetime as dt\nx = dt.now()\n",
                "def main():\n    return datetime.now()\n", "def f(clock=date.today()):\n    pass\n",
                "x = np.datetime64('now')\n", "x = numpy.datetime64('today', 'D')\n", "from uuid import uuid1\n",
                "from numpy import datetime64\nx = datetime64('now')\n", "import uuid\nx = uuid.uuid1()\n",
                "import email.utils\nx = email.utils.localtime()\n", "import uuid as u\nx = u.uuid1()\n",
                "from email import utils\nx = utils.formatdate()\n", "import email.utils as eu\nx = eu.localtime()\n",
                "from email.utils import formatdate\n", "x = pd.Timestamp.now()\n", "x = pd.Timestamp('today')\n"):
        assert _clock_hits_in(X, src), src
    main = "def main():\n    return datetime.now(timezone.utc)\n"
    assert _clock_hits_in(XD, main, allowed=(RUN,)) and not _clock_hits_in(RUN, main, allowed=(RUN,))
    assert _clock_hits_in(RUN, "def main(today=date.today()):\n    pass\n", allowed=(RUN,))   # a default runs at import
    assert not _clock_hits_in(X, "d = now.astimezone(KST).date()\nt = datetime.fromisoformat(s)\nimport time\n"
                                 "e = np.datetime64('2026-10-23')\nu = uuid.uuid4()\nfrom uuid import uuid4\n"
                                 "from datetime import datetime, date\nw = email.utils.parsedate_to_datetime(s)\n")
    hits = [h for rel, src in _files(ODDS).items() for h in _clock_hits_in(rel, src)]
    assert not hits, hits


def test_core_odds_has_no_main_block():
    """No core/odds file holds a `__main__` test in either operand order (T-CTX-01 skips such bodies, and the core is
    run only through core.oddsdata.run); the one exact block allowed elsewhere is checked by the same checker."""
    exact = 'if __name__ == "__main__":\n    raise SystemExit(main())\n'
    for src in (exact, "if '__main__' == __name__:\n    main()\n", 'if __name__ != "__main__":\n    pass\n',
                'def f():\n    if __name__ == "__main__":\n        pass\n', 'x = __name__ == "__main__"\n'):
        assert _main_hits(X, src), src
    assert not _main_hits(RUN, exact, allowed=(RUN,))
    assert not _main_hits(X, "name = __name__\nmain = '__main__'\n")
    hits = [h for rel, src in _files(ODDS).items() for h in _main_hits(rel, src)]
    assert not hits, hits


def test_core_odds_does_no_file_io():
    """Every table reaches the core only through the sealed Context of owner.load_context (O2): no file-I/O module
    (builtins, scipy.io and numpy's npyio and format among them), no _IO_ATTRS name imported from any module, no
    `open` (bare, io.open, os.open, Path.open) and no `__builtins__`, no Path read or write call, no numpy file call,
    no os.replace. The only I/O the core reaches is through owner.calendar_in_force (Q19, Q42)."""
    for src in ("f = open(p)\n", "with open(p, 'w') as fh:\n    pass\n", "g = open\n", "io.open(p)\n",
                "os.open(p, 0)\n", "p.open()\n", "p.read_text(encoding='utf-8')\n", "p.read_bytes()\n",
                "p.write_text(s, encoding='utf-8')\n", "p.write_bytes(b)\n", "p.mkdir()\n", "p.unlink()\n",
                "p.rename(q)\n", "os.replace(a, b)\n", "np.load(p)\n", "np.save(p, a)\n", "np.savez(p, a=a)\n",
                "np.savez_compressed(p, a=a)\n", "np.loadtxt(p)\n", "np.savetxt(p, a)\n", "np.genfromtxt(p)\n",
                "np.fromregex(p, r, d)\n", "np.fromfile(p)\n", "a.tofile(p)\n", "np.memmap(p)\n",
                "np.lib.format.open_memmap(p)\n", "def f():\n    import lzma\n", "import os.path\n",
                "from io import BytesIO\n", "from numpy import load\nx = load(p)\n",
                "from numpy import fromfile, memmap\n", "from builtins import open as o\n",
                "import builtins\nf = builtins.open\n", "f = __builtins__.open\n", "from scipy.io import loadmat\n",
                "import scipy.io\n", "import numpy.lib.format as F\nF.open_memmap(p)\n",
                "from numpy.lib._format_impl import open_memmap\n", "from json import load\n"):
        assert _core_io_hits(X, src), src
    for module in _FILE_MODULES:
        for src in (f"import {module}\n", f"from {module} import x\n"):
            assert _core_io_hits(X, src), src
    assert not _core_io_hits(X, "s = t.replace('a', 'b')\nd = dataclasses.replace(c, n=1)\nj = json.loads(s)\n"
                                "x = np.asarray(v)\nimport json, hashlib\nimport iox_notes\nr = report.render(x)\n"
                                "from json import loads\nfrom core.compliance.owner import load_context\n"
                                "import scipy\nfrom scipy import stats\n")
    assert not _core_io_hits(X, "class Series:\n    open: tuple[float, ...]\n"      # plan.Series (contract 5.2)
                                "s = Series(open=(1.0,))\nfirst = s.open[0]\nm = np.log(s.close) - np.log(s.open)\n")
    hits = [h for rel, src in _files(ODDS).items() for h in _core_io_hits(rel, src)]
    assert not hits, hits


def test_core_odds_imports_no_package_reexport():
    """Concrete submodules only (O2): a name taken from a package (`import core.odds`, `from core.compliance import
    <a name that is no module file>`) is whatever that package's __init__ makes of it (core/engine/__init__.py hands
    out orders' OrderBook, core/calendars/__init__.py holds code), so no scan can tell which file it comes from."""
    for src in ("import core\n", "import core.odds\n", "import core.compliance\n", "import core.oddsdata\n",
                "import core.compliance as C\n", "from core import odds\n", "from core import compliance\n",
                "from core.compliance import approved_state\n", "from core.odds import nosuch\n",
                "from . import nosuch\n", "from core.calendars import is_trading_day\n",
                "from core.engine import OrderBook\n"):
        assert _reexport_hits(X, src), src
    assert not _reexport_hits(X, "from core import isolation\nfrom core.compliance import gate, model, owner, rules\n"
                                 "from core.compliance.rules import Venue\nimport core.compliance.rules\n"
                                 "import core.isolation\nfrom ..compliance import model\nimport numpy\n"
                                 "from scipy import stats\n")
    tree = _probe_tree("odds_tree", {"core/odds/plan.py": ""})
    assert not _reexport_hits(X, "from . import plan\nfrom core.odds import plan\n", root=tree)
    hits = [h for rel, src in _files(ODDS).items() for h in _reexport_hits(rel, src)]
    assert not hits, hits


def test_core_odds_is_flat():
    """Q1 and O1: core/odds holds only __init__.py, plan, costs, models, simulate, bold and report, venues.yaml and
    __pycache__, and no subfolder holds a .py file: owner.code_files seeds core/odds/*.py with a non-recursive glob
    (the `for sub in ("compliance", "odds")` seed), so a nested file would run unsigned."""
    probe = _probe_tree("flat_probe", {"plan.py": "", "venues.yaml": "", "notes.txt": "", "sub/b.py": ""})
    assert _layout_hits(probe) == ["notes.txt", "sub", "sub/b.py"], _layout_hits(probe)
    assert (ODDS / "__init__.py").is_file(), "core/odds/__init__.py missing"
    assert not _layout_hits(ODDS), _layout_hits(ODDS)


def test_package_inits_are_empty():
    """core/odds/__init__.py and core/oddsdata/__init__.py exist and are 0 bytes (O1, O13): under the trailing-dot
    acting prefix the package module itself is not acting, so it may hold no code."""
    probe = _probe_tree("init_probe", {"__init__.py": "\n"})
    assert CG._init_hits(probe / "__init__.py") and CG._init_hits(probe / "missing.py")
    for init in (ODDS / "__init__.py", ODDSDATA / "__init__.py"):
        assert not CG._init_hits(init), f"{init.relative_to(ROOT).as_posix()} must exist and be 0 bytes"


# --------------------------------------------------------------------------- #
# core/oddsdata: the unsigned loaders and the CLI
# --------------------------------------------------------------------------- #
def test_oddsdata_raw_words():
    """compliance_guards._raw_hits over core/oddsdata, docstrings and comments included (the compliance raw-word test
    scans core/compliance and core/odds only; core/oddsdata is a sibling)."""
    for needle in tuple(CG.RAW_CI) + tuple(CG.RAW_CS):
        assert CG._raw_hits(XD, f'"""{needle}"""\n'), needle
    assert not CG._raw_hits(XD, "canonical_json, cache_dir, checked_target, transfer_out\n")
    hits = [h for rel, src in _files(ODDSDATA).items() for h in CG._raw_hits(rel, src)]
    assert not hits, hits


def test_oddsdata_never_imports_orders_or_the_study():
    """O1, O2, R2-6: no core.engine module in any form (core/engine/__init__.py imports orders), no forward_sim,
    refusal or context-log module (compliance_guards.FORBIDDEN_MODULES), never the study runner, never
    core.quant.gate_ledger or core.ficc.macro_artifacts (their repo_anchor and tree_hash are copied into
    core/oddsdata/inputs.py), and no star or dynamic import. A direct-import scan: what an allowed module imports in
    turn is not seen here."""
    for src in ("from core.engine import orders\n", "import core.engine.orders as o\n",
                "from core.engine import books\n", "import core.engine\n", "from core import engine\n",
                "def f():\n    from core.engine.risk import x\n",
                "from core.quant import forward_sim\n", "from core.quant.refusal import y\n",
                "from core.ficc import context_log\n", "import core.ficc.flows_log\n", "from core.ficc import macro\n",
                "import core.skills.macro_daily\n", "import docs.asset_expansion_study\n",
                "from docs import asset_expansion_study\n", "import asset_expansion_study\n",
                "from core.quant import gate_ledger\n", "import core.ficc.macro_artifacts\n",
                "from core.ficc.macro_artifacts import tree_hash\n", "from ..quant import gate_ledger\n",
                "import importlib\n", "m = __import__('x')\n", "exec(s)\n", "from math import *\n", "import pickle\n",
                "import pstats\n"):
        assert _data_import_hits(XD, src), src
    assert not _data_import_hits(XD, "from core.quant import garch, instruments, validate, strategies\n"
                                     "from core.calendars import clocks, regime, store\n"
                                     "from data.krx import kis_client\n"
                                     "from data.crypto import crypto_client\nimport yfinance\n"
                                     "from core.ficc import macro_schema\nfrom core.compliance import model, owner\n"
                                     "import core.enginex\nimport importlib.metadata\nimport csv, json, os\n")
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _data_import_hits(rel, src)]
    assert not hits, hits


def test_oddsdata_clock_only_in_run_main():
    """O15: the wall clock is read only in the body of core/oddsdata/run.py's main(); bars, inputs and replay take
    `now` as an argument."""
    main = "def main(argv=None, *, now=None):\n    now = now or datetime.now(timezone.utc)\n"
    assert _clock_hits_in(XD, main, allowed=(RUN,)) and not _clock_hits_in(RUN, main, allowed=(RUN,))
    for src in ("def load(now=datetime.now()):\n    pass\n", "def other():\n    return time.time()\n",
                "STARTED = datetime.now()\n", "from time import monotonic\n",
                "def other():\n    return pd.Timestamp.now(tz='UTC')\n", "def other():\n    return uuid.uuid1()\n"):
        assert _clock_hits_in(RUN, src, allowed=(RUN,)), src
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _clock_hits_in(rel, src, allowed=(RUN,))]
    assert not hits, hits


def test_oddsdata_main_block_only_in_run():
    """The only `__main__` block in core/oddsdata is run.py's, exactly `raise SystemExit(main())` at the top level
    (contract section 0; T-CTX-01 skips such bodies)."""
    exact = 'if __name__ == "__main__":\n    raise SystemExit(main())\n'
    assert _main_hits(XD, exact, allowed=(RUN,)) and not _main_hits(RUN, exact, allowed=(RUN,))
    for src in ('if __name__ == "__main__":\n    main()\n',
                'if __name__ == "__main__":\n    import sys\n    raise SystemExit(main())\n',
                exact + "else:\n    pass\n", "if '__main__' == __name__:\n    raise SystemExit(main())\n",
                'def g():\n    if __name__ == "__main__":\n        raise SystemExit(main())\n'):
        assert _main_hits(RUN, src, allowed=(RUN,)), src
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _main_hits(rel, src, allowed=(RUN,))]
    assert not hits, hits


def test_oddsdata_writes_only_checked_targets():
    """O2: every file write in core/oddsdata (open with a mode holding w, a, x or +, or a mode that is not a constant;
    .write_text, .write_bytes, .mkdir, .touch, .unlink, .rmdir, .symlink_to, .hardlink_to, .tofile; Path.replace(t)
    and Path.rename(t); the os, shutil and numpy functions that write, rename or delete, under any import alias)
    comes after a call to checked_target in the same function (core.isolation.checked_target refuses QUANTGEN, links
    and files that would change another file)."""
    for src in ("def f(p):\n    p.write_text('x', encoding='utf-8')\n",
                "def f(p):\n    p.write_bytes(b'')\n    checked_target(p, 'x')\n",
                "def f(p):\n    with open(p, 'w', encoding='utf-8') as fh:\n        fh.write('x')\n",
                "def f(p):\n    open(p, 'a', encoding='utf-8')\n", "def f(p):\n    open(p, mode='x')\n",
                "def f(p):\n    open(p, 'r+b')\n", "def f(p, m):\n    open(p, m)\n", "def f(p):\n    p.open('wb')\n",
                "def f(a, b):\n    os.replace(a, b)\n", "def f(a, b):\n    os.rename(a, b)\n",
                "def f(p):\n    p.mkdir(parents=True, exist_ok=True)\n", "Path('x').write_text('y')\n",
                "def f(p):\n    checked_target(p, 'x')\n    def g():\n        p.write_text('y')\n    g()\n",
                "def f(p, t):\n    p.replace(t)\n", "def f(p, t):\n    p.rename(t)\n", "def f(p):\n    p.touch()\n",
                "def f(p):\n    p.unlink(missing_ok=True)\n", "def f(p):\n    p.rmdir()\n",
                "def f(p, t):\n    p.symlink_to(t)\n", "def f(p, t):\n    p.hardlink_to(t)\n",
                "def f(d):\n    os.makedirs(d, exist_ok=True)\n", "def f(p):\n    os.remove(p)\n",
                "def f(a, b):\n    os.link(a, b)\n", "import shutil\ndef f(a, b):\n    shutil.copyfile(a, b)\n",
                "import shutil as sh\ndef f(d):\n    sh.rmtree(d)\n",
                "from shutil import move\ndef f(a, b):\n    move(a, b)\n",
                "import numpy as np\ndef f(p, a):\n    np.save(p, a)\n", "def f(p, a):\n    a.tofile(p)\n",
                "import os as o\ndef f(a, b):\n    o.replace(a, b)\n",
                "from os import replace\ndef f(a, b):\n    replace(a, b)\n",
                "from io import open as o\ndef f(p):\n    o(p, 'w')\n",
                "def f(p):\n    Path(p).open('a', encoding='utf-8')\n"):
        assert _unchecked_write_hits(XD, src), src
    for src in ("def f(p, d):\n    checked_target(p, 'x', within=d)\n    p.write_text('y', encoding='utf-8')\n",
                "def f(p):\n    with open(checked_target(p, 'x'), 'w', encoding='utf-8') as fh:\n"
                "        fh.write('y')\n",
                "def f(p):\n    isolation.checked_target(p, 'x').write_bytes(b'')\n",
                "def f(p, t):\n    checked_target(p, 'x')\n    checked_target(t, 'x')\n    t.write_bytes(b'')\n"
                "    os.replace(t, p)\n",
                "def f(p):\n    a = open(p, encoding='utf-8')\n    b = open(p, 'rb')\n    c = p.open()\n"
                "    d = p.read_text(encoding='utf-8')\n    return s.replace('a', 'b'), now.replace(tzinfo=None)\n",
                "import dataclasses\nfrom dataclasses import replace\nimport numpy as np\n"
                "c2, c3 = dataclasses.replace(c), replace(c)\nx = np.load(p)\nq = os.path.join(a, b)\n"):
        assert not _unchecked_write_hits(XD, src), src
    hits = [h for rel, src in _files(ODDSDATA).items() for h in _unchecked_write_hits(rel, src)]
    assert not hits, hits


# --------------------------------------------------------------------------- #
# The D14 closure (O1)
# --------------------------------------------------------------------------- #
def test_code_closure_holds_no_data_layer():
    """O1: the D14 closure (owner.code_files: core/compliance/*.py, core/odds/*.py and every in-repo file they import
    at any depth) holds no file under core/oddsdata/, data/, core/quant/, core/calendars/ or core/engine/, and not
    config.py. A seeded core/odds file that imports core.oddsdata, even inside a function, pulls it and what it imports
    in (the positive control, on a synthetic tree)."""
    from core.compliance import owner
    root = _probe_tree("code_tree", {
        "config.py": "", "core/__init__.py": "", "core/odds/__init__.py": "",
        "core/odds/x.py": "def f():\n    from core.oddsdata import bars\n    return bars\n",
        "core/oddsdata/__init__.py": "", "core/oddsdata/bars.py": "import config\nfrom core.quant import garch\n",
        "core/quant/__init__.py": "", "core/quant/garch.py": ""})
    names = [n for n, _ in owner.code_files(root)]
    assert _closure_hits(names) == ["config.py", "core/oddsdata/__init__.py", "core/oddsdata/bars.py",
                                    "core/quant/__init__.py", "core/quant/garch.py"], names
    real = [n for n, _ in owner.code_files(ROOT)]
    assert "core/odds/__init__.py" in real, "core/odds/__init__.py is not in the closure: is the odds seed gone?"
    assert not _closure_hits(real), _closure_hits(real)


# --------------------------------------------------------------------------- #
# Registration (the odds twin of compliance_guards.test_suite_is_registered_in_run_all_and_readme)
# --------------------------------------------------------------------------- #
def test_suite_is_registered_in_run_all_and_readme():
    """`tests/run_all.py --suite odds` selects this suite, and both hand-written suite lists (the --suite help text and
    the README verification block) name it; compliance_guards._suite_names reads the lists (follow-up R7)."""
    from tests import run_all
    names = [n for n, _f in run_all.select(run_all.tests(), suite="odds")]
    assert any(n.startswith("odds/odds_guards/") for n in names), names
    assert "odds" not in CG._suite_names("x  # one suite: grokteam or compliance\n")
    for path in (ROOT / "tests" / "run_all.py", ROOT / "README.md"):
        assert "odds" in CG._suite_names(path.read_text(encoding="utf-8")), path.name


# --------------------------------------------------------------------------- #
# The harness itself (the odds twins of the three compliance self-tests)
# --------------------------------------------------------------------------- #
def test_suite_runs_hermetic_in_a_temp_home_with_the_seams_patched():
    """The wrapper arms the hermetic guard and points TRADEGEN_HOME at a fresh temp dir; a nested wrapped call arms
    one more level, moves the home and undoes both. Once core/oddsdata/bars.py exists every seam is the raising stub
    inside a test and REAL_SEAMS holds the real functions. The patch itself is checked on a stand-in bars module with
    one seam missing: inside, every seam raises; afterwards each is back and the missing one is gone again."""
    from tests import macro_acceptance as MA
    from tests import odds_acceptance as OA
    home = Path(os.environ["TRADEGEN_HOME"])
    assert MA._DEPTH > 0, "the hermetic guard is not armed"
    assert home.is_dir() and home.name.startswith("tradegen_home_"), home
    assert not home.resolve().is_relative_to((Path.home() / ".tradegen").resolve()), home
    seen = []
    OA._wrap(lambda: seen.append((MA._DEPTH, Path(os.environ["TRADEGEN_HOME"]))))()
    depth, inner = seen[0]
    assert depth == MA._DEPTH + 1 and inner != home and inner.name.startswith("tradegen_home_"), seen
    assert Path(os.environ["TRADEGEN_HOME"]) == home and not inner.exists(), seen
    if OA._BARS.is_file():                              # Task 15 on: this very test runs with the real seams patched
        bars = sys.modules["core.oddsdata.bars"]
        assert all(vars(bars)[s] is MA._boom for s in OA.SEAMS), "a bars seam is not patched"
        assert sorted(OA.REAL_SEAMS) == sorted(OA.SEAMS), OA.REAL_SEAMS
        assert all(f is not MA._boom for f in OA.REAL_SEAMS.values()), OA.REAL_SEAMS

    def real(*_a, **_k):
        return "real"
    fake = types.ModuleType("core.oddsdata.bars")
    for name in OA.SEAMS[:-1]:
        setattr(fake, name, real)
    probe = home / "bars.py"
    probe.write_bytes(b"")
    keep = OA._BARS, dict(OA.REAL_SEAMS), sys.modules.get("core.oddsdata.bars", MA._MISSING)
    inside = {}
    try:
        OA._BARS = probe
        OA.REAL_SEAMS.clear()
        sys.modules["core.oddsdata.bars"] = fake
        OA._wrap(lambda: inside.update(vars(fake)))()
        recorded = dict(OA.REAL_SEAMS)
    finally:
        OA._BARS = keep[0]
        OA.REAL_SEAMS.clear()
        OA.REAL_SEAMS.update(keep[1])
        if keep[2] is MA._MISSING:
            sys.modules.pop("core.oddsdata.bars", None)
        else:
            sys.modules["core.oddsdata.bars"] = keep[2]
    assert all(inside[name] is MA._boom for name in OA.SEAMS), inside
    assert all(vars(fake)[name] is real for name in OA.SEAMS[:-1]) and OA.SEAMS[-1] not in vars(fake), vars(fake)
    assert recorded == {name: real for name in OA.SEAMS[:-1]}, recorded


def test_harness_flags_a_change_to_the_real_homes_and_the_read_only_repo_files():
    """The wrapper fails a test that changes the real ~/.tradegen/odds or ~/.tradegen/compliance (a new file or folder
    in either) or a repo file the suite only reads (venues.yaml, the S_C3 cache, card and results.csv); stand-ins in
    the temp home take their place here."""
    from tests import odds_acceptance as OA
    base = _probe_tree("watch", {"real_odds/.keep": "", "real_compliance/.keep": "", "card.json": "{}"})
    odds, comp, card = base / "real_odds", base / "real_compliance", base / "card.json"
    keep, flagged = (OA._REAL_HOMES, OA._REPO_FILES), []
    try:
        OA._REAL_HOMES, OA._REPO_FILES = (odds, comp), (card.as_posix(),)   # absolute: TESTS.parent / it is itself
        OA._wrap(lambda: None)()                                            # nothing changed: passes
        for change in (lambda: (odds / "state.json").write_bytes(b"{}\n"),
                       lambda: (comp / "owner.jsonl").write_bytes(b"{}\n"),
                       lambda: (comp / "store").mkdir(),
                       lambda: card.write_bytes(b'{"edited": true}')):
            try:
                OA._wrap(change)()
            except AssertionError as exc:
                flagged.append(str(exc).split(":", 1)[0])
            else:
                flagged.append("not flagged")
    finally:
        OA._REAL_HOMES, OA._REPO_FILES = keep
    assert flagged == ["the test touched the real ~/.tradegen/odds or compliance"] * 3 + [
        "the test changed a repo file it may only read"], flagged


def test_aggregator_skips_missing_and_isolates_broken_modules():
    """Contract section 3.1: an absent module is skipped, one that fails to import becomes a single `<module>/import`
    entry that re-raises, a `test_*` name imported from elsewhere is not collected, and an empty run exits 1."""
    from tests import odds_acceptance as OA
    from tests.compliance_fixtures import temp_home as imported
    probe = _probe_tree("probe", {"odds_broken.py": "", "odds_mixed.py": ""})

    def own():
        pass
    mixed = types.ModuleType("tests.odds_mixed")
    own.__module__ = mixed.__name__
    mixed.test_own, mixed.test_imported = own, imported
    keep = OA.TESTS, OA.MODULES
    sys.modules.update({"tests.odds_broken": None, "tests.odds_mixed": mixed})   # None: the import raises
    try:
        OA.TESTS, OA.MODULES = probe, ("odds_broken", "odds_absent", "odds_mixed")
        found = OA.tests()
    finally:
        OA.TESTS, OA.MODULES = keep
        for stem in ("odds_broken", "odds_mixed"):
            sys.modules.pop(f"tests.{stem}", None)
    assert [n for n, _f in found] == ["odds_broken/import", "odds_mixed/test_own"], found
    try:
        found[0][1]()
    except ImportError:
        pass
    else:
        raise AssertionError("the broken module's entry did not re-raise its import error")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = OA._main(["no such test"])
    assert code == 1 and out.getvalue().strip() == "0/0 passed, 0 failed, 0 not run", (code, out.getvalue())


def test_chunk_and_pilots_swap_their_sizes_and_restore_them():
    """tests/odds_fixtures (contract 3.2): chunk() sets simulate.CHUNK, every DEFAULT_PATHS track and GARCH_SUB (never
    above its own value); pilots() sets models.PILOT_PATHS, simulate.TILT_PILOT and models.PILOT_NODES; both put every
    value back, after an exception too. Run on stand-in modules, so it holds before simulate.py exists and leaves the
    real modules alone after."""
    from tests import odds_fixtures as OF
    sim, mod = types.ModuleType("core.odds.simulate"), types.ModuleType("core.odds.models")
    defaults = {"moonshot": 1_000_000, "compounding": 200_000}
    sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB, sim.TILT_PILOT = 200_000, defaults, 20_000, 20_000
    mod.PILOT_PATHS, mod.PILOT_NODES = 20_000, 512
    missing = object()
    keep = {name: sys.modules.get(name, missing) for name in (sim.__name__, mod.__name__)}
    seen = []
    try:
        sys.modules.update({sim.__name__: sim, mod.__name__: mod})
        with OF.chunk():
            seen.append((sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB))
        with OF.chunk(50_000):
            seen.append((sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB))
        with OF.pilots():
            seen.append((mod.PILOT_PATHS, sim.TILT_PILOT, mod.PILOT_NODES))
        try:
            with OF.chunk(), OF.pilots(500, 16):
                seen.append((sim.CHUNK, mod.PILOT_PATHS, sim.TILT_PILOT, mod.PILOT_NODES))
                raise KeyError("inside")
        except KeyError:
            pass
        after = (sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB, mod.PILOT_PATHS, sim.TILT_PILOT, mod.PILOT_NODES)
    finally:
        for name, module in keep.items():
            if module is missing:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    assert seen == [(2_000, {"moonshot": 2_000, "compounding": 2_000}, 2_000),
                    (50_000, {"moonshot": 50_000, "compounding": 50_000}, 20_000),
                    (2_000, 2_000, 64), (2_000, 500, 500, 16)], seen
    assert after == (200_000, defaults, 20_000, 20_000, 20_000, 512) and after[1] is defaults, after
    assert defaults == {"moonshot": 1_000_000, "compounding": 200_000}, defaults
```

- [ ] **Step 2: Run to verify it fails**

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/; echo "exit $?"
```

  Expected: fifteen tracebacks, then these lines (the runner sorts by test name), then `exit 1`:

```
PASS odds_guards/test_aggregator_skips_missing_and_isolates_broken_modules
FAIL odds_guards/test_chunk_and_pilots_swap_their_sizes_and_restore_them ImportError: cannot import name 'odds_fixtures' from 'tests' (C:\Users\whydi\OneDrive\Desktop\TRADEGEN\tests\__init__.py)
FAIL odds_guards/test_code_closure_holds_no_data_layer AssertionError: core/odds/__init__.py is not in the closure: is the odds seed gone?
FAIL odds_guards/test_core_odds_does_no_file_io AssertionError: scan scope: core/odds/__init__.py missing
FAIL odds_guards/test_core_odds_has_no_main_block AssertionError: scan scope: core/odds/__init__.py missing
FAIL odds_guards/test_core_odds_imports_no_package_reexport AssertionError: scan scope: core/odds/__init__.py missing
FAIL odds_guards/test_core_odds_imports_only_the_allowlist AssertionError: scan scope: core/odds/__init__.py missing
FAIL odds_guards/test_core_odds_is_flat AssertionError: core/odds/__init__.py missing
FAIL odds_guards/test_core_odds_reads_no_clock AssertionError: scan scope: core/odds/__init__.py missing
PASS odds_guards/test_harness_flags_a_change_to_the_real_homes_and_the_read_only_repo_files
FAIL odds_guards/test_oddsdata_clock_only_in_run_main AssertionError: scan scope: core/oddsdata/__init__.py missing
FAIL odds_guards/test_oddsdata_main_block_only_in_run AssertionError: scan scope: core/oddsdata/__init__.py missing
FAIL odds_guards/test_oddsdata_never_imports_orders_or_the_study AssertionError: scan scope: core/oddsdata/__init__.py missing
FAIL odds_guards/test_oddsdata_raw_words AssertionError: scan scope: core/oddsdata/__init__.py missing
FAIL odds_guards/test_oddsdata_writes_only_checked_targets AssertionError: scan scope: core/oddsdata/__init__.py missing
FAIL odds_guards/test_package_inits_are_empty AssertionError: core/odds/__init__.py must exist and be 0 bytes
FAIL odds_guards/test_suite_is_registered_in_run_all_and_readme AssertionError: []
PASS odds_guards/test_suite_runs_hermetic_in_a_temp_home_with_the_seams_patched
3/18 passed, 15 failed, 0 not run
```

  Every FAIL is a missing package, the missing fixtures file or the missing registration; each positive control
  above its scope line already passed. The three PASS lines are the harness self-tests: they test
  `tests/odds_acceptance.py`, which is the runner itself, so they have no red state (a missing runner runs nothing).
  The path in the `ImportError` line is the repo's own `tests\__init__.py`. Any other FAIL means a file of Step 1d
  differs from the text above or the follow-up's lists differ from the ones 1a checked: fix the file, or stop and
  report a list change, never the expectation.

  Overlap check, then confirm the runner does not know the suite yet (the `--suite` run imports every suite; give the
  Bash tool `timeout: 300000`):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected last lines: `0/0 passed, 0 failed, 0 not run; ` followed by the path of `qa\acceptance_results.json`, then
  `exit 1`.

- [ ] **Step 3: Implement**

  **3a. The two packages, 0 bytes each:**

```bash
test ! -e core/odds/__init__.py && test ! -e core/oddsdata && mkdir core/oddsdata && : > core/odds/__init__.py && : > core/oddsdata/__init__.py
wc -c core/odds/__init__.py core/oddsdata/__init__.py
```

  Expected: `0 core/odds/__init__.py`, `0 core/oddsdata/__init__.py`, `0 total`.

  **3b. `tests/odds_fixtures.py`.** Create it (LF) with the Write tool, exactly:

```python
"""Fixtures for the odds suite (odds plan, contract section 3.2). Task 1 adds the CHUNK and pilot swaps; Tasks 5, 9
and 13 add the venue, series, plan, context and input fixtures. Not in MODULES, and no name here starts with test_.
Each swap imports its modules when entered, so this file imports nothing from core/odds at load."""
from __future__ import annotations

import contextlib
import importlib
from typing import Iterator


@contextlib.contextmanager
def chunk(n: int = 2_000) -> Iterator[None]:
    """core.odds.simulate runs n paths per chunk: CHUNK = n, every DEFAULT_PATHS track = n and GARCH_SUB =
    min(GARCH_SUB, n), all three put back in finally; so a pipeline or CLI test that passes no path count runs one
    small chunk. import_module reads sys.modules, so the swap reaches the module that is loaded there."""
    sim = importlib.import_module("core.odds.simulate")
    saved = sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB
    sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB = n, {track: n for track in saved[1]}, min(saved[2], n)
    try:
        yield
    finally:
        sim.CHUNK, sim.DEFAULT_PATHS, sim.GARCH_SUB = saved


@contextlib.contextmanager
def pilots(n: int = 2_000, nodes: int = 64) -> Iterator[None]:
    """The GARCH pilot and the tilt pilot run n paths and check 1 uses `nodes` quantile nodes: models.PILOT_PATHS,
    simulate.TILT_PILOT and models.PILOT_NODES, all three put back in finally. Task 8's pilot tests run without it,
    at 20,000 paths and 512 nodes."""
    models = importlib.import_module("core.odds.models")
    sim = importlib.import_module("core.odds.simulate")
    saved = models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES
    models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = n, n, nodes
    try:
        yield
    finally:
        models.PILOT_PATHS, sim.TILT_PILOT, models.PILOT_NODES = saved
```

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/test_chunk_and_pilots; echo "exit $?"
```

  Expected: `PASS odds_guards/test_chunk_and_pilots_swap_their_sizes_and_restore_them`, then
  `1/1 passed, 0 failed, 0 not run` and `exit 0`.

  **3c. `tests/run_all.py` (CRLF; Edit tool only).** Re-read the file first (DRIFT RULE). The follow-up does not
  change it, so each old text below is found exactly once; if one is not, apply the same change to the current text
  and write one ledger line under "Drift rulings".

  Edit 1. Anchor: the suite import block, the `compliance_acceptance` line (run_all.py:49-51 at `5816d3c`). The odds
  import goes right after it; its `# noqa` lines up with the compliance line's. Old text:

```python
from grokteam.selfcheck import tests as grokteam_tests             # noqa: E402
from tests.compliance_acceptance import tests as compliance_tests  # noqa: E402
from tests.notrun import NotRun                             # noqa: E402
```

  New text:

```python
from grokteam.selfcheck import tests as grokteam_tests             # noqa: E402
from tests.compliance_acceptance import tests as compliance_tests  # noqa: E402
from tests.odds_acceptance import tests as odds_tests              # noqa: E402
from tests.notrun import NotRun                             # noqa: E402
```

  Edit 2. Anchor: the function `tests()` (run_all.py:57-67 at `5816d3c`), quoted whole so the text is unique and
  parses; only its last line changes and one line is added. Old text:

```python
def tests():
    return ([(f"cockpit/{n}", f) for n, f in cockpit_tests()] +
            [(f"engine/{n}", f) for n, f in engine_tests()] +
            [(f"ui/{n}", f) for n, f in ui_tests()] +
            [(f"quant/{n}", f) for n, f in quant_tests()] +
            [(f"ficc/{n}", f) for n, f in ficc_tests()] +
            [(f"expansion/{n}", f) for n, f in expansion_tests()] +
            [(f"macro/{n}", f) for n, f in macro_tests()] +
            [(f"paper/{n}", f) for n, f in paper_tests()] +
            [(f"grokteam/{n}", f) for n, f in grokteam_tests()] +
            [(f"compliance/{n}", f) for n, f in compliance_tests()])
```

  New text:

```python
def tests():
    return ([(f"cockpit/{n}", f) for n, f in cockpit_tests()] +
            [(f"engine/{n}", f) for n, f in engine_tests()] +
            [(f"ui/{n}", f) for n, f in ui_tests()] +
            [(f"quant/{n}", f) for n, f in quant_tests()] +
            [(f"ficc/{n}", f) for n, f in ficc_tests()] +
            [(f"expansion/{n}", f) for n, f in expansion_tests()] +
            [(f"macro/{n}", f) for n, f in macro_tests()] +
            [(f"paper/{n}", f) for n, f in paper_tests()] +
            [(f"grokteam/{n}", f) for n, f in grokteam_tests()] +
            [(f"compliance/{n}", f) for n, f in compliance_tests()] +
            [(f"odds/{n}", f) for n, f in odds_tests()])
```

  Edit 3. Anchor: `main()`, its `--suite` argument line (run_all.py:113 at `5816d3c`). The help stays one line;
  `compliance_guards._suite_names` reads it. Old text:

```python
    parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance")
```

  New text:

```python
    parser.add_argument("--suite", help="run one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance or odds")
```

  **3d. `README.md` (CRLF; Edit tool only).** Re-read the file first (DRIFT RULE): the follow-up's Task 8 changed the
  compliance row and the Total line of the suite table, not this line. Anchor: the `## Verification` code block, its
  `--suite macro` line with the "one suite:" list (README.md:816 at `5816d3c`). Old text:

```
.venv/Scripts/python tests/run_all.py --suite macro    # one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance
```

  New text:

```
.venv/Scripts/python tests/run_all.py --suite macro    # one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam, compliance or odds
```

  Leave the suite table and its Total line alone: Task 19 adds the `odds` row from the full run.

  Line-ending check right after the edits:

```bash
git diff --stat
git diff --stat --ignore-cr-at-eol
```

  The two outputs must be identical: `README.md | 2 +-`, `tests/run_all.py | 6 ++++--`, `2 files changed, 5
  insertions(+), 3 deletions(-)`. If they differ, an edit converted line endings: `git checkout -- <file>` and redo
  its edits with the Edit tool.

- [ ] **Step 4: Run to verify it passes**

  Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/; echo "exit $?"
```

  Expected:

```
PASS odds_guards/test_aggregator_skips_missing_and_isolates_broken_modules
PASS odds_guards/test_chunk_and_pilots_swap_their_sizes_and_restore_them
PASS odds_guards/test_code_closure_holds_no_data_layer
PASS odds_guards/test_core_odds_does_no_file_io
PASS odds_guards/test_core_odds_has_no_main_block
PASS odds_guards/test_core_odds_imports_no_package_reexport
PASS odds_guards/test_core_odds_imports_only_the_allowlist
PASS odds_guards/test_core_odds_is_flat
PASS odds_guards/test_core_odds_reads_no_clock
PASS odds_guards/test_harness_flags_a_change_to_the_real_homes_and_the_read_only_repo_files
PASS odds_guards/test_oddsdata_clock_only_in_run_main
PASS odds_guards/test_oddsdata_main_block_only_in_run
PASS odds_guards/test_oddsdata_never_imports_orders_or_the_study
PASS odds_guards/test_oddsdata_raw_words
PASS odds_guards/test_oddsdata_writes_only_checked_targets
PASS odds_guards/test_package_inits_are_empty
PASS odds_guards/test_suite_is_registered_in_run_all_and_readme
PASS odds_guards/test_suite_runs_hermetic_in_a_temp_home_with_the_seams_patched
18/18 passed, 0 failed, 0 not run
```

  then `exit 0` (about 2 s of tests after about 7 s of imports; budget 5 s for the module, contract 3.4). Overlap
  check, then the whole odds suite through its own runner (only `odds_guards` exists yet):

```bash
.venv/Scripts/python.exe -m tests.odds_acceptance; echo "exit $?"
```

  Expected last line `18/18 passed, 0 failed, 0 not run`, then `exit 0`. Overlap check, then the suite through the
  real runner (it rewrites the tracked `qa/acceptance_results.json`, restored at once; `timeout: 300000`):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: 18 lines `PASS odds/odds_guards/...`, then `18/18 passed, 0 failed, 0 not run; ` followed by the path of
  `qa\acceptance_results.json`, then `exit 0`.

  The compliance guards and store (Global Constraints: this task touches `core/odds`). Overlap check before each:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/; echo "exit $?"
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_store/; echo "exit $?"
```

  Expected: `16/16 passed, 0 failed, 0 not run` and `exit 0` (`test_package_init_is_empty` now checks the real
  `core/odds/__init__.py`; the raw-word and dynamic-import scans now see it; the compliance registration test still
  finds `compliance` in both lists), then `29/29 passed, 0 failed, 0 not run` and `exit 0`
  (`test_code_files_is_the_import_closure` now expects and finds `core/odds/__init__.py` in the closure). A fix wave
  of the follow-up may have changed these counts: the merged counts with `0 failed` are right.

  The signer's copy of the closure (`tools/signer/sign.py` seeds `("compliance", "odds")` too, sign.py:693 at
  `5816d3c`), so the new `core/odds/__init__.py` must join both lists alike. Overlap check, then:

```bash
.venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/test_code_files_match_owner; echo "exit $?"
```

  Expected: `PASS compliance_signer/test_code_files_match_owner`, then `1/1 passed, 0 failed, 0 not run` and
  `exit 0`. A FAIL here means the owner and signer seeds drifted apart: stop and report, never edit either.

  The core-wide scans (Global Constraints: this task adds files under `core/`), one at a time, overlap check before
  each:

```bash
.venv/Scripts/python.exe -m tests.macro_m0_harness; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_tf_gov; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m7_ledger; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m8_forward; echo "exit $?"
.venv/Scripts/python.exe -m tests.macro_m6_context; echo "exit $?"
```

  Expected, with no FAIL line and `exit 0` each (the counts of the committed record; the follow-up changes no
  `tests/macro_*.py` file): `11/11 passed, 0 failed, 0 not run` (T-RO-01), `20/22 passed, 0 failed, 2 not run`,
  `14/18 passed, 0 failed, 4 not run`, `17/23 passed, 0 failed, 6 not run`, `14/16 passed, 0 failed, 2 not run`
  (T-CTX-01: `core.oddsdata.` does not match the acting prefix `core.odds.`, and the two inits hold no code).

  Overlap check, then the cockpit suite (test_08, test_09, test_16, test_18 scan every `core/**/*.py`;
  `timeout: 300000`):

```bash
KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py --suite cockpit; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: `47/47 passed, 0 failed, 0 not run; ` followed by the path, then `exit 0`. Any FAIL that names
  `core/odds` or `core/oddsdata` means a new file is not empty: fix the file, never a guard.

  Record the runs. With the Edit tool, replace the ledger's line `## Runs` with that line followed by one line per
  run above, each `- Task 1: <the command after .venv/Scripts/python.exe>: <its summary line>`, in the order run;
  for example `- Task 1: -m tests.odds_acceptance odds_guards/: 18/18 passed, 0 failed, 0 not run` and
  `- Task 1: tests/run_all.py --suite cockpit: 47/47 passed, 0 failed, 0 not run` (the path after `;` left out).
  Later tasks compare their scan and cockpit counts with these lines.

- [ ] **Step 5: Commit**

```bash
git status --short
```

  Expected exactly these eight lines (`qa/acceptance_results.json` must not be among them):

```
 M README.md
 M tests/run_all.py
?? core/odds/__init__.py
?? core/oddsdata/
?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
?? tests/odds_acceptance.py
?? tests/odds_fixtures.py
?? tests/odds_guards.py
```

  The stat comparison cannot see CRLF or a BOM in a NEW file, so check the new files directly first (overlap check
  first):

```bash
.venv/Scripts/python.exe -c "import pathlib; [print(p, len(pathlib.Path(p).read_bytes()), pathlib.Path(p).read_bytes().count(b'\r'), pathlib.Path(p).read_bytes()[:3] == b'\xef\xbb\xbf') for p in ('core/odds/__init__.py', 'core/oddsdata/__init__.py', 'tests/odds_acceptance.py', 'tests/odds_fixtures.py', 'tests/odds_guards.py', 'docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md')]"
```

  Expected: the two inits print `0 0 False`; every other line ends `0 False` (no carriage return, no BOM). Otherwise
  rewrite that file with LF endings and no BOM before staging. Then (the ledger stays untracked):

```bash
git add core/odds/__init__.py core/oddsdata/__init__.py tests/odds_acceptance.py tests/odds_fixtures.py tests/odds_guards.py tests/run_all.py README.md
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical: `README.md | 2 +-`, `core/odds/__init__.py | 0`,
  `core/oddsdata/__init__.py | 0`, `tests/odds_acceptance.py | 146 +`, `tests/odds_fixtures.py | 37 +`,
  `tests/odds_guards.py | 790 +`, `tests/run_all.py | 6 +-` (each with its bar), and
  `7 files changed, 978 insertions(+), 3 deletions(-)`. If they differ, `git restore --staged <file>` and fix its
  line endings first. Then, with the `Co-Authored-By:` line of the model that writes the commit (this controller's
  is shown):

```bash
git commit -m "feat(odds): empty odds packages, the odds suite and its guards" -m "Odds plan Task 1 (Q1, Q2, Q13, Q40; R2-6, R2-10): 0-byte core/odds and core/oddsdata, the hermetic odds suite with seam patches and watches, the O1/O2 guards with positive controls, the closure check, and the run_all and README registration." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

  Expected: the new commit, then exactly `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
  Never push: the controller pushes `odds-engine` after this task's review passes (G3-3).
