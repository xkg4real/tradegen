### Task 6: alerts.jsonl records a fingerprint only from codes 0 to 2 (`core/compliance/alerts.py`)

**Files:**
- Modify: `core/compliance/alerts.py` (anchor: `log()`, its docstring and the lines from the row build to the
  `_in_log` check; LF). A D14 closure file: the code hash moves (no `code_approved` exists yet, so nothing is
  re-signed now).
- Test: `tests/compliance_cli.py` (anchor: a new test inserted right above `test_log_refuses_bad_input_and_writes_nothing`,
  that is after `test_log_rows_carry_anchor_and_fingerprint` and its helper `_canonical_line`; LF)

**Interfaces:**
- Consumes:
  - `core.compliance.alerts`: `log(channel: str, result: str, summary: dict, now: datetime) -> None` (raises
    ValueError before writing for a bad channel, result, summary, naive `now` or head), `_first(history) -> dict |
    None`, `_history() -> list[dict]`, `due(summary, history, today) -> list[dict]`; `rules._SUMMARY_KEYS` (`code,
    due, overdue, head_seq, head_sha256, fingerprint`); `owner._first_recorded() -> tuple[str, str] | None`
    (owner.py:913-918, the first alerts.jsonl row with a non-empty fingerprint, P20).
  - `tests/compliance_cli.py`: `_sample(**over)` (code 0, nothing due, head (0, ""), fingerprint `FP`),
    `_alerts_lines() -> list[dict]`, `FP = "SHA256:" + "f" * 64`, and the module imports `date`, `datetime`,
    `timezone`, `alerts`, `owner`, `rules`.
- Produces: `log()` writes `row["fingerprint"] == ""` whenever `summary["code"] > 2` (codes 3 and 4); codes 0, 1 and
  2 keep the summary's fingerprint; every row keeps all nine keys. New test
  `test_log_records_a_fingerprint_only_from_codes_0_to_2`. No later task calls anything new.

**Plan decisions used:** R6; the DRIFT RULE (Global Constraints).

Design notes (read before Step 1):
- Why. The key is held to the first fingerprint alerts.jsonl records (P20; `owner._first_recorded`, owner.py:913-918,
  and `alerts._first`, alerts.py:97-100). Today `log()` copies the summary's `fingerprint` into every row
  (alerts.py:253-254), whatever the code, so the first recorded one can come from a code 3 summary (a broken log,
  KEY CHANGED, unsigned code, an unapproved table; ledger:219). R6 blanks code 4 too: rules.main and `_MISSING`
  already write `""` there (rules.py:962, alerts.py:24), so only a hand-written `--summary` could give a code 4 row a
  fingerprint. A code 3 summary carries the fingerprint of whatever `owner_pubkey.pem` holds even when the log does
  not verify against it (owner.py `_owner_now` passes `fingerprint_now` into the BROKEN state; a swapped key file
  reads as a broken log). Recorded first, that fingerprint becomes the P20 reference: `owner_state` then reads the owner's real key as KEY CHANGED
  from then on (owner.py:470-474), and `due()` raises no KEY CHANGED headline for a later check with the unverified
  key (alerts.py:128-131; the last assertion of the new test). After this task a code 3 or 4 row records `""`, which
  both readers already skip, so the first recorded fingerprint always comes from a check that verified the log
  (exit 0, 1 or 2).
- Where. One `if` in `log()` after the row is built and before the `_in_log` check, so every caller (the toast row of
  `main()`, `--log CHANNEL RESULT`, the daily task) goes through it. `_valid_summary`, `due()`, `render()` and
  `_footer` are unchanged: the footer still prints the summary's current fingerprint as "Key now ...", and `due()`
  still compares a code 3 summary's fingerprint with the first recorded one. `_MISSING` (code 4) already carries
  `""`.
- What stays green. `test_log_rows_carry_anchor_and_fingerprint` logs code 1 rows and still reads `FP` back;
  `test_check_code_3_key_changed` logs a code 0 summary; `test_alerts_main_send_toasts_once_and_logs` logs a code 3
  toast row after a code 1 row and asserts only its channel and result, and its footer reads the code 1 row; the
  hand-built histories of `test_due_key_changed` and `test_render_fixed_template_and_sanitises` never pass through
  `log()`.
- Departures from Appendix A (the task wins). Appendix A section 8's test logs codes 3, 4 and 0 and checks the two
  blank fingerprints and the first recorded one. This task's test also logs a code 2 row (an overdue date, the other
  fingerprint) and checks that it keeps that fingerprint, checks every row's code and fingerprint and its nine keys,
  and calls `due()` to show that a later code 3 check with the unverified key still owes KEY CHANGED; its docstring
  says so. `log()` and its docstring are as in section 8.
- A consequence the owner should know (it follows from R6, not a new rule). Between owner act 1 and the first alert
  sent from a check that exits 1 or 2 (a row date within 14 days, or overdue), alerts.jsonl records no fingerprint.
  An exit-0 check owes no alert and writes no row (`due()` returns `[]` for code 0 and `main()` returns before
  `log()`, alerts.py:329-331; the daily prompt stops on `"send": false`, compliance plan :16676). Every check exits 3
  until owner acts 2 and 3 (unsigned code, an unapproved table). After them, a `review_by` is at most 31 days after
  its review (rules.py:524), so the first 14-day alert comes at most about 17 days after the reviewed table is
  approved, and sooner when a date is closer. Until then the alert footer reads "first recorded none yet", and the
  fingerprint written on paper at owner act 1 is the only reference, including against a swap of key and log
  together. Throughout, a check exits 0 to 2 only when the owner log verifies against the key file; what the window
  lacks is the alerts.jsonl reference for the key itself. The controller accepts this window as a stated limit (the
  plan header's "Spec" list): new exposure stays blocked until a check exits 0, 1 or 2.
- Drift rule. Task 2 lands first and rewrites tests/compliance_cli.py:576-577 inside `test_render_has_no_rule_free_text`
  (above this task's anchor), two lines for two, so the tests/compliance_cli.py line numbers cited here do not move;
  no earlier task of this plan touches alerts.py. Before each Edit, re-read the file
  and find the anchor; if the quoted old text differs only because an earlier plan changed it, apply the same change
  to the current text, keep that earlier behaviour, and add one line to
  `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`.

- [ ] **Step 1: Write the failing test**

**Edit 1 of 2** — `tests/compliance_cli.py`, anchor: `test_log_refuses_bad_input_and_writes_nothing` (its first two
lines, tests/compliance_cli.py:631-632). The new test goes right above it, after `_canonical_line`.

Old text (exact):
```python
def test_log_refuses_bad_input_and_writes_nothing():
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
```

New text:
```python
def test_log_records_a_fingerprint_only_from_codes_0_to_2():
    """R6 (ledger:219): the key is held to the first fingerprint alerts.jsonl records (P20), so a code 3 or 4
    summary, which can come from a key the log does not verify, records "" and never becomes that first one, and a
    later check with that key still owes KEY CHANGED. Codes 0 and 2 keep theirs here (code 1 in
    test_log_rows_carry_anchor_and_fingerprint)."""
    now = datetime(2026, 10, 23, 0, 0, tzinfo=timezone.utc)
    other = "SHA256:" + "0" * 64
    late = [{"row": "KR-X", "field": "review_by", "date": "2026-11-22", "days_late": 1}]
    alerts.log("email", "ok", _sample(code=3, fingerprint=other), now)
    alerts.log("push", "ok", _sample(code=4, fingerprint=other), now)
    fingerprints = [r["fingerprint"] for r in _alerts_lines()]
    assert fingerprints == ["", ""], fingerprints
    assert owner._first_recorded() is None and alerts._first(alerts._history()) is None
    alerts.log("email", "ok", _sample(code=0), now)
    alerts.log("push", "ok", _sample(code=2, overdue=late, fingerprint=other), now)
    rows = _alerts_lines()
    assert [(r["code"], r["fingerprint"]) for r in rows] == [(3, ""), (4, ""), (0, FP), (2, other)], rows
    assert all(set(r) == {"utc", "channel", "result", *rules._SUMMARY_KEYS} for r in rows), rows
    assert owner._first_recorded() == (FP, "2026-10-23T00:00:00Z"), owner._first_recorded()
    owed = alerts.due(_sample(code=3, fingerprint=other), rows, date(2026, 10, 24))
    assert owed == [{"kind": "key_changed", "since": "2026-10-23"}, {"kind": "state"}], owed


def test_log_refuses_bad_input_and_writes_nothing():
    now = datetime(2026, 10, 23, tzinfo=timezone.utc)
```

- [ ] **Step 2: Run to verify it fails**

  Run from the repo root in Git Bash (the Bash tool), behind the QUANTGEN overlap check. The prefix prints nothing
  and runs the command only when no python `run_all` is running; if the line exits 1 with no output, a run is in
  progress: wait, then run it again.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected: one FAIL line (its traceback printed above it, on stderr) and the count; the other 35 pass, Task 2's
  rewritten `test_render_has_no_rule_free_text` included. The FAIL line and the last line (35 PASS lines are printed
  too):

```text
FAIL compliance_cli/test_log_records_a_fingerprint_only_from_codes_0_to_2 AssertionError: ['SHA256:0000000000000000000000000000000000000000000000000000000000000000', 'SHA256:0000000000000000000000000000000000000000000000000000000000000000']

35/36 passed, 1 failed, 0 not run
```

  A `NOT_RUN ... PENDING: cryptography not installed` line means the venv lost `cryptography`; stop and report.

- [ ] **Step 3: Implement**

**Edit 2 of 2** — `core/compliance/alerts.py`, anchor: `log()` (from its `def` line to the `_in_log` check and its
raise, alerts.py:242-256). The docstring gains the R6 sentence; two lines go between the row build and the `_in_log`
check. The lock, the `checked_target` open and the write below stay as they are.

Old text (exact):
```python
def log(channel: str, result: str, summary: dict, now: datetime) -> None:
    """Append one alerts.jsonl row, canonical JSON {utc, channel, result, code, due, overdue, head_seq,
    head_sha256, fingerprint}. Its head is an owner-log anchor (spec 6.4) and the first fingerprint recorded is the
    one the key is held to (P20). ValueError before anything is written for an unknown channel or result, a
    malformed summary, a naive `now`, or a head that is not that line of owner.jsonl (append-only, so the check
    holds under the lock too). The append takes the owner-log sidecar lock: a torn line would be BROKEN for good."""
    from core.compliance import owner
    if channel not in _CHANNELS or result not in _RESULTS:
        raise ValueError(f"log: channel must be one of {_CHANNELS} and result one of {_RESULTS}")
    if not _valid_summary(summary):
        raise ValueError("log: not a --check summary")
    row = {"utc": model.iso_utc(now), "channel": channel, "result": result,
           **{k: summary[k] for k in rules._SUMMARY_KEYS}}
    if not _in_log(summary["head_seq"], summary["head_sha256"]):
        raise ValueError(f"log: owner log entry #{summary['head_seq']} does not have that row_sha256")
```

New text:
```python
def log(channel: str, result: str, summary: dict, now: datetime) -> None:
    """Append one alerts.jsonl row, canonical JSON {utc, channel, result, code, due, overdue, head_seq,
    head_sha256, fingerprint}. Its head is an owner-log anchor (spec 6.4) and the first fingerprint recorded is the
    one the key is held to (P20), so a row keeps the summary's fingerprint only when its code is 0, 1 or 2; a code 3
    or 4 summary (a broken log, KEY CHANGED, a failed check) can come from a key the log does not verify, and its
    row records an empty fingerprint. ValueError before anything is written for an unknown channel or result, a
    malformed summary, a naive `now`, or a head that is not that line of owner.jsonl (append-only, so the check
    holds under the lock too). The append takes the owner-log sidecar lock: a torn line would be BROKEN for good."""
    from core.compliance import owner
    if channel not in _CHANNELS or result not in _RESULTS:
        raise ValueError(f"log: channel must be one of {_CHANNELS} and result one of {_RESULTS}")
    if not _valid_summary(summary):
        raise ValueError("log: not a --check summary")
    row = {"utc": model.iso_utc(now), "channel": channel, "result": result,
           **{k: summary[k] for k in rules._SUMMARY_KEYS}}
    if summary["code"] > 2:                     # R6: a code 3 or 4 summary may name a key the log does not verify
        row["fingerprint"] = ""
    if not _in_log(summary["head_seq"], summary["head_sha256"]):
        raise ValueError(f"log: owner log entry #{summary['head_seq']} does not have that row_sha256")
```

  Notes:
  - `summary["code"]` is an int from 0 to 4 here: `_valid_summary` has already accepted the summary (alerts.py:88).
  - The new lines pass every guard of the compliance plan: no wall-clock call, no network or dynamic import, no
    `.post/.put/.delete/.patch/.request`, none of the banned strings; the longest new line is 116 characters.
  - Dry run (2026-10-24, sandbox copies of both files with Edits 1-2 applied to the tree at `5816d3c`, each test in
    a temp TRADEGEN_HOME): each quoted old text occurs exactly once; the new test fails before Edit 2 with exactly
    the Step 2 line and passes after it; with the new `log()` the eight other compliance_cli tests that reach
    `alerts.log` or `alerts.main` without a signed home pass (`test_log_rows_carry_anchor_and_fingerprint`,
    `test_log_refuses_bad_input_and_writes_nothing`, the six `test_alerts_main_*`/`test_alerts_runs_as_main_module`
    tests). The three that build a signed home (`test_check_code_0_and_alert_rows_are_accepted`,
    `test_check_code_3_key_changed`, `test_render_has_no_rule_free_text`) log only code 0 or 1 summaries, which R6
    leaves as they are; Step 4's module run covers them.

- [ ] **Step 4: Run to verify it passes**

  Each command behind the overlap check, from the repo root in Git Bash:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_cli/
```

  Expected last line: `36/36 passed, 0 failed, 0 not run`.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/
```

  Expected last line: `16/16 passed, 0 failed, 0 not run` (alerts.py is scanned by the import, clock, verb and
  banned-string guards).

  The suite line: every `--suite` run first imports all ten suites (run_all.py:41-50), and the compliance tests alone
  took 64 s in the 2026-10-24 record, so give this line `timeout: 300000`; never start a second run meanwhile.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
```

  Expected: `324/326 passed, 0 failed, 2 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json`
  then `exit 0`. If it prints only `exit 1` and no test lines, the overlap check found a run_all in progress (the
  checkout was a harmless no-op): wait, then run the line again. The two NOT_RUN lines are the `REFDATA: symlink creation needs Developer Mode` tests
  (`compliance_isolation/test_symlinks_are_refused`, `compliance_tables/test_calendar_sha256_refuses_a_file_symlink`);
  with Developer Mode on it ends `326/326 passed, 0 failed, 0 not run`. The run's numbers win over these if an earlier
  task's count differed; what must hold is `0 failed`. Then:

```bash
git status --short
```

  Expected exactly:

```text
 M core/compliance/alerts.py
 M tests/compliance_cli.py
```

  plus, if the executor keeps its ledger in the repo and has not committed it,
  `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`; nothing else.

- [ ] **Step 5: Commit**

  Both files must stay LF. This prints `[0, 0]`:

```bash
.venv/Scripts/python.exe -I -c "print([open(p, 'rb').read().count(b'\r\n') for p in ('core/compliance/alerts.py', 'tests/compliance_cli.py')])"
```

  Then:

```bash
git add core/compliance/alerts.py tests/compliance_cli.py
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git commit -m "fix(alerts): record a key fingerprint only from a check that verified the log" -m "log() writes an empty fingerprint for a code 3 or 4 summary, so the first recorded fingerprint the key is held to comes from exit 0, 1 or 2 (R6, P20; ledger:219)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

  The two `--stat` outputs must be identical (2 files changed). alerts.py is a D14 closure file, so the code hash on
  disk moves; no `code_approved` exists yet (owner act 2 signs once, after the odds plan lands).
