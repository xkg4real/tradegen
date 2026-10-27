### Task 5: The signer's ancestor walk fails closed (`tools/signer/sign.py`)

**Files:**
- Modify: `tools/signer/sign.py` (anchors: the module docstring's first paragraph and its "Every time, before you type
  the passphrase" list; `_has_claude_ancestor`; the `_claude_ancestor()` branch of `_refusal`; LF). Repo copy only:
  the owner's own copy changes only by the owner act at the end of this task.
- Test: `tests/compliance_signer.py` (anchors: `test_main_refuses_claude_parent_and_non_tty_stdin`,
  `test_claude_ancestor_walk`, `test_claude_ancestor_check_fails_closed`, `test_help_names_owner_acts_1_and_2`; LF)

**Interfaces:**
- Consumes:
  - `tools/signer/sign.py` as Task 4 leaves it: `_process_table() -> dict[int, tuple[int, str]]` (pid -> (parent pid,
    exe name), unchanged), `_claude_ancestor() -> bool` (unchanged: True on a failed snapshot or a table without our
    own pid, else `_has_claude_ancestor(os.getpid(), table)`), `_refusal() -> str`, `main(argv=None) -> int`,
    `_parser() -> argparse.ArgumentParser` (its description is the module docstring).
  - `tests/compliance_signer.py` as Task 4 leaves it (38 tests): `signer` (the module loaded by
    `spec_from_file_location`), `_patched(obj, name, value)`, `_quiet(fn, *args)`, `_env_without_claude()`, `_Tty`,
    `_never`, `_home()`.
- Produces (`tools/signer/sign.py`):
  - `_SESSION_ROOTS = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})`;
  - `_has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool`, same signature, new rule: True on a
    claude.exe anywhere in the chain (any case), True on a break (a pid missing from `table`, a pid-reuse cycle, 256
    steps) unless a session process was passed first, False only at pid 0 or at such a break after a session process;
  - the `_refusal()` text for that branch, which contains "claude.exe" and "has exited".
  No later task calls these; Task 8 carries the owner act below into the plan's hand-off.

**Plan decisions used:** R5, R11 (and R13 for the drift rule).

Design notes (read before Step 1):
- What changes. Today `_has_claude_ancestor` (sign.py:758-767) ends with `return False` whenever its loop stops, so a
  parent that has exited, a pid-reuse cycle or the 256-step cap all read as "no Claude ancestor": a refusal check
  that fails open (ledger:229 rules that a refusal check fails closed; ledger:233 names this walk). After this task
  the walk goes on until pid 0 or a break, and a break refuses unless the walk has already passed a Windows session
  process (`_SESSION_ROOTS`): a user's chain normally passes one of them before its top parent, which has exited.
- Why the root is not pid 0 alone (R11). Read-only probes of the live process table on 2026-10-24 (the probe behind
  R11 in Appendix A section 1, and this task's re-run through the repo signer's own `_process_table`, 721
  processes): pid 0 is `[System Process]` and no user chain reaches it; every chain ends at a parent that has
  exited. The owner's Windows Terminal chain is `powershell.exe -> WindowsTerminal.exe -> svchost.exe ->
  services.exe -> wininit.exe -> (exited)`, `explorer.exe`'s, `wininit.exe`'s and `winlogon.exe`'s own parents
  have exited (`services.exe`'s parent is the live `wininit.exe`), and 298 processes end at `wininit.exe ->
  (exited)`. A pid-0-only root would refuse the very terminal spec 6.4 says the signer runs in. With this walk that
  chain still passes (it passes `services.exe` and `wininit.exe` before the break), and so does a terminal started
  from `explorer.exe`.
- A session process never stops the walk. A process name is only a file name: a copy of cmd.exe saved as
  winlogon.exe and run under Claude must not end the search before the claude.exe above it (today's walk refuses
  that chain because it walks on; so does this one, test case `renamed`).
- Every chain refused today stays refused. The old walk returned True only on reaching a claude.exe. The new walk
  takes the same steps (same table lookups, same cycle test, same 256-pid cap), so it reaches the same claude.exe;
  the only step it no longer takes is through pid 0, which on Windows is `[System Process]`, its own parent, never
  claude.exe. The re-run above agrees: over the 721 live processes, (old, new) verdicts were (True, True) 169,
  (False, False) 324, (False, True) 228, and never (True, False). The 228 that now refuse are chains that end at a
  launcher that has exited without a session process on the way: VS Code terminals (`powershell.exe -> Code.exe ->
  Code.exe -> (exited)`), a tray app's or a browser's children, a console whose parent exited.
- The refusal text names the new cause and the fix: open Windows Terminal from the Start menu. The help gains the
  same first bullet, and the docstring's refusal sentence names the new rule.
- For the controller, not for this task: sign.py's existing help (sign.py:5-31) gives its commands in Command Prompt
  syntax (`%USERPROFILE%` in the certutil, keygen and code-approve lines; test_help_names_owner_acts_1_and_2 pins the
  certutil one), while the new bullet sends the owner to Windows Terminal, which opens PowerShell (R11's chain), where
  `%USERPROFILE%` is not expanded. This plan does not edit the existing help without a ruling: either the help says
  "Command Prompt", or rewriting it for PowerShell is ruled as a later task. The owner act at the end of this task
  uses PowerShell syntax, as Task 8 Step 9 does.
- Departures from Appendix A (the task wins): Edit 2 adds the `shell` and `service` cases, the `roots` pin of
  `_SESSION_ROOTS`, a docstring and assertion messages to Appendix A section 7.3's test; Edit 3 adds a docstring
  change and an assertion message; Edit 4 adds two needles to test_help_names_owner_acts_1_and_2, which section 7.3
  does not list (section 7.2's "No test pins the help text or the docstring" is wrong: that test already pins help
  needles, and Edit 4 adds the two new ones); Edit 7's comment and docstring differ (Step 3 notes); the owner act
  uses PowerShell syntax where section 7.3's uses Command Prompt syntax.
- Honest limits (R11, spec 6.4): a process started through COM activation or the desktop shell has no claude.exe
  ancestor, so this check stays defence in depth; the passphrase and the typed code are the barrier. A session
  process is recognised by its file name only, so a chain that passes a process carrying one of those names and
  then breaks, with no claude.exe on the way, passes (today any break passed). A reused pid above a session
  process is walked too, so if it now runs claude.exe the signer refuses, as today, until Claude is closed.
- Drift rule (Global Constraints; Appendix A section 0). Task 4 lands first and inserts `_guards` above `_skipped`
  in sign.py, so the sign.py lines cited here sit about 18 lines lower; it adds tests to
  `test_code_files_match_owner` and a new test after it, so `test_help_names_owner_acts_1_and_2`
  (tests/compliance_signer.py:1094) sits lower too. Neither changes any text quoted below. Before each Edit, re-read
  the file and find the anchor; if the quoted old text differs only because an earlier plan changed it, apply the
  same change to the current text, keep that earlier behaviour, and add one line to
  `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`.

- [ ] **Step 1: Write the failing tests**

  Four Edit-tool replacements in `tests/compliance_signer.py` (LF; keep LF).

**Edit 1 of 8** — `tests/compliance_signer.py`, anchor: `test_main_refuses_claude_parent_and_non_tty_stdin` (the
first `with` block and its assertion; tests/compliance_signer.py:222-224). The refusal must name the new cause.

Old text (exact):
```python
        with _patched(signer, "_claude_ancestor", lambda: True), _patched(sys, "stdin", _Tty()):
            code, _, err = _quiet(signer.main, ["keygen"])
        assert code == 2 and "claude.exe" in err, (code, err)
```

New text:
```python
        with _patched(signer, "_claude_ancestor", lambda: True), _patched(sys, "stdin", _Tty()):
            code, _, err = _quiet(signer.main, ["keygen"])
        assert code == 2 and "claude.exe" in err and "has exited" in err, (code, err)
```

**Edit 2 of 8** — `tests/compliance_signer.py`, anchor: `test_claude_ancestor_walk` (the whole function;
tests/compliance_signer.py:285-293). Two assertions flip on purpose: the pid-reuse cycle and the empty table now
refuse.

Old text (exact):
```python
def test_claude_ancestor_walk():
    table = {10: (9, "python.exe"), 9: (8, "cmd.exe"), 8: (7, "Claude.exe"), 7: (0, "explorer.exe")}
    assert signer._has_claude_ancestor(10, table) is True
    assert signer._has_claude_ancestor(9, {**table, 8: (7, "WindowsTerminal.exe")}) is False
    assert signer._has_claude_ancestor(1, {1: (2, "a.exe"), 2: (1, "b.exe")}) is False      # pid-reuse cycle ends
    assert signer._has_claude_ancestor(5, {}) is False
    if os.name == "nt":
        live = signer._process_table()
        assert live[os.getpid()][0] == os.getppid(), live.get(os.getpid())
```

New text:
```python
def test_claude_ancestor_walk():
    """R5, R11: a claude.exe anywhere in the chain refuses, even above a session process, and so does a walk that
    breaks (an exited parent, a pid-reuse cycle, more than 256 steps) before it has passed a session process."""
    table = {10: (9, "python.exe"), 9: (8, "cmd.exe"), 8: (7, "Claude.exe"), 7: (0, "explorer.exe")}
    assert signer._has_claude_ancestor(10, table) is True
    assert signer._has_claude_ancestor(9, {**table, 8: (7, "WindowsTerminal.exe")}) is False
    terminal = {20: (21, "python.exe"), 21: (22, "powershell.exe"), 22: (23, "WindowsTerminal.exe"),
                23: (24, "svchost.exe"), 24: (25, "services.exe"), 25: (99, "wininit.exe")}      # 99 has exited
    assert signer._has_claude_ancestor(20, terminal) is False, "the owner's Windows Terminal chain (R11)"
    shell = {50: (51, "python.exe"), 51: (52, "cmd.exe"), 52: (53, "Explorer.EXE")}             # 53 has exited
    assert signer._has_claude_ancestor(50, shell) is False, "a console started from explorer.exe, any case (R11)"
    renamed = {1: (2, "python.exe"), 2: (3, "winlogon.exe"), 3: (4, "bash.exe"), 4: (5, "claude.exe"),
               5: (0, "explorer.exe")}                       # cmd.exe saved as winlogon.exe, run under Claude
    assert signer._has_claude_ancestor(1, renamed) is True, "a session process name never ends the walk"
    assert signer._has_claude_ancestor(1, {1: (2, "a.exe"), 2: (1, "b.exe")}) is True, "a pid-reuse cycle refuses"
    assert signer._has_claude_ancestor(5, {}) is True, "an empty table refuses"
    exited = {30: (31, "python.exe"), 31: (32, "Code.exe")}                                    # 32 has exited
    assert signer._has_claude_ancestor(30, exited) is True, "an editor terminal whose launcher has exited"
    assert signer._has_claude_ancestor(40, {40: (41, "python.exe"), 41: (0, "CLAUDE.EXE")}) is True, "any case"
    deep = {**{n: (n + 1, "python.exe") for n in range(1, 300)}, 300: (0, "wininit.exe")}
    assert signer._has_claude_ancestor(1, deep) is True, "the 256-step cap refuses"
    service = {60: (61, "python.exe"), 61: (62, "svchost.exe")}                                # 62 has exited
    assert signer._has_claude_ancestor(60, service) is True, "svchost.exe is no session process"
    roots = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})
    assert signer._SESSION_ROOTS == roots, "exactly the four session processes: one more makes the walk looser (R11)"
    if os.name == "nt":
        live = signer._process_table()
        assert live[os.getpid()][0] == os.getppid(), live.get(os.getpid())
```

**Edit 3 of 8** — `tests/compliance_signer.py`, anchor: `test_claude_ancestor_check_fails_closed` (the whole
function; tests/compliance_signer.py:296-311). It gains the exited-parent case; `{me: (0, "python.exe")}` stays
False.

Old text (exact):
```python
def test_claude_ancestor_check_fails_closed():
    """Claude is ruled out only from a process table that holds this very process: a failed snapshot, an empty
    table or a table without our pid all read as "cannot rule it out"."""
    me = os.getpid()

    def broken():
        raise OSError("Process32FirstW failed")

    for table in (lambda: {}, lambda: {me + 1: (0, "python.exe")}, broken,
                  lambda: (_ for _ in ()).throw(TypeError("ctypes")), lambda: (_ for _ in ()).throw(ImportError("x"))):
        with _patched(signer, "_process_table", table):
            assert signer._claude_ancestor() is True, table
    with _patched(signer, "_process_table", lambda: {me: (0, "python.exe")}):
        assert signer._claude_ancestor() is False
    with _patched(signer, "_process_table", lambda: {me: (7, "python.exe"), 7: (0, "Claude.exe")}):
        assert signer._claude_ancestor() is True
```

New text:
```python
def test_claude_ancestor_check_fails_closed():
    """Claude is ruled out only from a process table that holds this very process and whose parent chain reaches
    pid 0 or passes a Windows session process: a failed snapshot, an empty table, a table without our pid or a
    parent that has exited all read as "cannot rule it out" (R5)."""
    me = os.getpid()

    def broken():
        raise OSError("Process32FirstW failed")

    for table in (lambda: {}, lambda: {me + 1: (0, "python.exe")}, broken,
                  lambda: (_ for _ in ()).throw(TypeError("ctypes")), lambda: (_ for _ in ()).throw(ImportError("x"))):
        with _patched(signer, "_process_table", table):
            assert signer._claude_ancestor() is True, table
    with _patched(signer, "_process_table", lambda: {me: (0, "python.exe")}):
        assert signer._claude_ancestor() is False
    with _patched(signer, "_process_table", lambda: {me: (me + 1, "python.exe")}):
        assert signer._claude_ancestor() is True, "a parent that has exited refuses (R5)"
    with _patched(signer, "_process_table", lambda: {me: (7, "python.exe"), 7: (0, "Claude.exe")}):
        assert signer._claude_ancestor() is True
```

**Edit 4 of 8** — `tests/compliance_signer.py`, anchor: `test_help_names_owner_acts_1_and_2` (its `for needle in`
loop; tests/compliance_signer.py:1096-1103 before Task 4). The help (the module docstring) must carry the new
bullet and the new refusal sentence. The other needles stay.

Old text (exact):
```python
    for needle in ("certutil -hashfile %USERPROFILE%\\tradegen-signer\\sign.py SHA256", "away from the PC",
                   "keygen", "code-approve", "owner_pubkey.pem", "at least 20 characters",
                   "at least 5 different words", "python.exe -I", "site-packages\\*.pth",
                   "Claude never runs this file", "from the next Asia/Seoul date", "blanks do not count",
                   "Key rotation", "keygen --key NEW\\owner_key.enc", "event key_rotated", "copy NEW\\owner_key.pem",
                   "owner_pubkey.pem", "pass --key NEW\\owner_key.enc to every command",
                   "reads BROKEN between steps 3 and 4", "write the new fingerprint on paper"):
        assert needle in " ".join(text.split()), needle
```

New text:
```python
    for needle in ("certutil -hashfile %USERPROFILE%\\tradegen-signer\\sign.py SHA256", "away from the PC",
                   "keygen", "code-approve", "owner_pubkey.pem", "at least 20 characters",
                   "at least 5 different words", "python.exe -I", "site-packages\\*.pth",
                   "Claude never runs this file", "from the next Asia/Seoul date", "blanks do not count",
                   "Key rotation", "keygen --key NEW\\owner_key.enc", "event key_rotated", "copy NEW\\owner_key.pem",
                   "owner_pubkey.pem", "pass --key NEW\\owner_key.enc to every command",
                   "reads BROKEN between steps 3 and 4", "write the new fingerprint on paper",
                   "open Windows Terminal yourself from the Start menu",               # R5, R11
                   "when its parent chain stops before a Windows session process"):
        assert needle in " ".join(text.split()), needle
```

- [ ] **Step 2: Run to verify it fails**

  Run from the repo root in Git Bash (the Bash tool), behind the QUANTGEN overlap check. The prefix prints nothing
  and runs the command only when no python `run_all` is running; if the line exits 1 with no output, a run is in
  progress: wait, then run it again.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected: four FAIL lines on stdout (their tracebacks go to stderr, in any interleaving), in this order, and the
  count. The other 34 pass, Task 4's included.

```text
FAIL compliance_signer/test_claude_ancestor_check_fails_closed AssertionError: a parent that has exited refuses (R5)
FAIL compliance_signer/test_claude_ancestor_walk AssertionError: a pid-reuse cycle refuses
FAIL compliance_signer/test_help_names_owner_acts_1_and_2 AssertionError: open Windows Terminal yourself from the Start menu
FAIL compliance_signer/test_main_refuses_claude_parent_and_non_tty_stdin AssertionError: (2, 'sign.py refused: a parent process is claude.exe: run me in your own terminal, never under Claude\n')

34/38 passed, 4 failed, 0 not run
```

  (In the last line `\n` is the two characters of the repr, not a line break.) A `NOT_RUN ... PENDING:
  cryptography not installed` line means the venv lost `cryptography`; stop and report.

- [ ] **Step 3: Implement**

  Four Edit-tool replacements in `tools/signer/sign.py` (LF; keep LF: the owner certutil-hashes these exact bytes).
  Edits 5 and 6 change the module docstring, which is also the `--help` text; they are shown as text, not code.

**Edit 5 of 8** — `tools/signer/sign.py`, anchor: the module docstring's first paragraph (sign.py:2-3, the sentence
"and refuses to run under Claude ..."). Line 3 becomes two lines.

Old text (exact):
```text
Windows Terminal. It uses the standard library and `cryptography`, never imports the TRADEGEN repo, and refuses to
run under Claude, under a claude.exe parent process, without a terminal on stdin, or without python.exe -I.
```

New text:
```text
Windows Terminal. It uses the standard library and `cryptography`, never imports the TRADEGEN repo, and refuses to
run under Claude, under a claude.exe parent process, when its parent chain stops before a Windows session process,
without a terminal on stdin, or without python.exe -I.
```

**Edit 6 of 8** — `tools/signer/sign.py`, anchor: the module docstring's list "Every time, before you type the
passphrase" (sign.py:22-23). A new first bullet.

Old text (exact):
```text
Every time, before you type the passphrase
  - start it with python.exe -I, as above. -I keeps the folder of sign.py, the current folder and PYTHON*
```

New text:
```text
Every time, before you type the passphrase
  - open Windows Terminal yourself from the Start menu (an editor's terminal can be refused: its parent chain may
    stop at a launcher that has exited);
  - start it with python.exe -I, as above. -I keeps the folder of sign.py, the current folder and PYTHON*
```

**Edit 7 of 8** — `tools/signer/sign.py`, anchor: `_has_claude_ancestor` (the whole function, sign.py:758-767,
between `_process_table` and `_claude_ancestor`). The new constant and its comment go right above it.
`_claude_ancestor` below it is unchanged.

Old text (exact):
```python
def _has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool:
    """True when `pid` or any ancestor in `table` runs claude.exe (any version, any case); pid reuse cycles end."""
    seen = set()
    while pid in table and pid not in seen and len(seen) < 256:
        seen.add(pid)
        parent, exe = table[pid]
        if exe.lower() == "claude.exe":
            return True
        pid = parent
    return False
```

New text:
```python
# Windows session processes: a user's chain normally passes one of these before its top parent exits (R11).
_SESSION_ROOTS = frozenset({"explorer.exe", "services.exe", "wininit.exe", "winlogon.exe"})


def _has_claude_ancestor(pid: int, table: dict[int, tuple[int, str]]) -> bool:
    """True when `pid` or any ancestor in `table` runs claude.exe (any version, any case), even above a Windows
    session process (a process name is only a file name). The walk goes on to pid 0 or until it breaks: at a pid
    missing from the table (a parent that has exited), a pid-reuse cycle or 256 steps. A break returns True (Claude
    cannot be ruled out) unless the walk has passed a session process (_SESSION_ROOTS): a user chain's top parent
    has normally exited (explorer.exe's, wininit.exe's), and Windows Terminal runs under svchost.exe, services.exe
    and wininit.exe (R11)."""
    seen, rooted = set(), False
    while pid != 0:
        if pid not in table or pid in seen or len(seen) >= 256:
            return not rooted
        seen.add(pid)
        parent, exe = table[pid]
        if exe.lower() == "claude.exe":
            return True
        rooted = rooted or exe.lower() in _SESSION_ROOTS
        pid = parent
    return False
```

**Edit 8 of 8** — `tools/signer/sign.py`, anchor: `_refusal`, its `if _claude_ancestor():` branch (sign.py:810-811).
The other refusals and their order stay.

Old text (exact):
```python
    if _claude_ancestor():
        return "a parent process is claude.exe: run me in your own terminal, never under Claude"
```

New text:
```python
    if _claude_ancestor():
        return ("a parent process is claude.exe, or the parent chain stops at a process that has exited: open Windows "
                "Terminal yourself from the Start menu and run me there, never under Claude")
```

  Notes:
  - Nothing else in sign.py changes: `_process_table`, `_claude_ancestor` (it already fails closed on a failed
    snapshot or a table without our own pid), `_isolated`, `_stdin_is_terminal`, the Task 4 closure helpers,
    `code_files` and `code_hash` keep their text. sign.py is off the D14 closure (it is not under `core/`), so the
    code hash does not move in this task; the owner's copy is what the owner act below updates.
  - The longest new line is 119 characters (`return ("a parent process ...`); every new line in this task's
    edits is within 120 columns.
  - Dry run (2026-10-24, sandbox copies of both files with Edits 1-8 applied to the tree at `5816d3c`): each quoted
    old text occurs exactly once; the four tests fail before Edits 5-8 with exactly the Step 2 lines and pass after
    them; over 200,000 random process tables (pid 0 never claude.exe, as on Windows, where it is `[System Process]`)
    the old walk's True is always the new walk's True, and every new False reached pid 0 or broke after a session
    process with no claude.exe on the way.
  - Edit 7 differs from Appendix A section 7.1 in its comment and docstring only, and the task wins (header): 7.1
    says the session processes' parents exit, but `services.exe`'s parent is the live `wininit.exe` (read-only
    probe, 2026-10-24). The code and its behaviour are 7.1's. The test's `roots` pin is new too: adding a name to
    `_SESSION_ROOTS` makes the walk looser, and without the pin a mutant adding `svchost.exe` passed every test.

- [ ] **Step 4: Run to verify it passes**

  Each command behind the overlap check, from the repo root in Git Bash:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_signer/
```

  Expected last line: `38/38 passed, 0 failed, 0 not run`.

  Then the compliance suite. Every `--suite` run first imports all ten suites, and the compliance tests alone took
  64 s in the 2026-10-24 record, so give this line `timeout: 300000`; never start a second run meanwhile. If it
  prints only `exit 1` and no test lines, the overlap check found a run_all in progress (the checkout was a harmless
  no-op): wait, then run the line again.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: `323/325 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json`
  then `exit 0`. The two NOT_RUN lines are the `REFDATA: symlink creation needs Developer Mode` tests
  (`compliance_isolation/test_symlinks_are_refused`, `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`);
  with Developer Mode on it ends `325/325 passed, 0 failed, 0 not run`. The run's numbers win over these if an earlier
  task's count differed; what must hold is `0 failed`. Then confirm the results file is restored and only the two
  files are pending:

```bash
git status --short
```

  Expected: these two lines,

```text
 M tests/compliance_signer.py
 M tools/signer/sign.py
```

  plus, if the executor keeps its ledger in the repo,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` (untracked until Task 8 Step 8
  commits it). Anything else, `qa/acceptance_results.json` included, is restored or removed before the commit.

- [ ] **Step 5: Commit**

  Both files must stay LF (the owner hashes the exact bytes of sign.py). This prints `[0, 0]`:

```bash
.venv/Scripts/python.exe -I -c "print([open(p, 'rb').read().count(b'\r\n') for p in ('tools/signer/sign.py', 'tests/compliance_signer.py')])"
```

  Then:

```bash
git add tools/signer/sign.py tests/compliance_signer.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -m "fix(signer): the ancestor walk refuses when the chain breaks before a session process" -m "An exited parent, a pid-reuse cycle or 256 steps now refuse unless the walk passed explorer, services, wininit or winlogon; a claude.exe anywhere still refuses (R5, R11; ledger:229, :233)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  The two `--stat` outputs must be identical (2 files changed).

**Owner act (for the plan's hand-off list; Claude never does it).** `tools/signer/sign.py` changed in Tasks 4 and 5.
Every command below is for Windows Terminal (PowerShell), as in Task 8 Step 9.
- Owner act 1 (spec 11) is not done yet, so when you do it, copy the merged `tools/signer/sign.py` (from `main` after
  this plan merges) to your folder `$env:USERPROFILE\tradegen-signer\`, read all of it, and in Windows Terminal
  (PowerShell) hash that copy with `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, then
  finish act 1 as spec section 11 lists it.
- If you already copied an earlier version to `$env:USERPROFILE\tradegen-signer\sign.py`: in Windows Terminal
  (PowerShell) compare it with the repo file while `main` is checked out after this plan merges (`git switch main`
  first; another branch may hold unreviewed, unmerged changes to sign.py):
  `fc.exe /n "$env:USERPROFILE\tradegen-signer\sign.py" "C:\Users\whydi\OneDrive\Desktop\TRADEGEN\tools\signer\sign.py"`
  (`fc.exe`, because in PowerShell `fc` is Format-Custom). Read every changed line, copy the repo file over your
  copy, run `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, and write the new hash on the
  paper, crossing out the old one.
- From then on, open Windows Terminal from the Start menu to sign: a terminal inside an editor (VS Code) can be
  refused, because its parent chain may stop at a launcher that has exited.
