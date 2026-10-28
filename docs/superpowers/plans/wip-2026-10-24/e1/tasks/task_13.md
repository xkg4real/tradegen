### Task 13: README, the full run and the ledger

**Files:**
- Modify: `README.md` (anchors: the end of the status bullet that starts
  `- **Status (2026-10-23): no order path exists.**` together with the first line of the next bullet, hint :13-14;
  the cockpit row's scan list, hint :830; the compliance row's `D15 and D16 refusals)` and its last cell, hint :839;
  the `| **Total** |` row, hint :840 at `5816d3c` and one line lower once the odds row is in; Edit R1 adds nine lines
  above them, so when Edits R2 to R5 run the hints are cockpit :839, compliance :848, odds :849 and Total :850;
  CRLF, keep CRLF)
- Modify: `qa/acceptance_results.json` (written by the full run of Step 3a and committed here, once; CRLF, keep CRLF)
- Modify: `docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` (anchors: the
  `## Deferred minors` heading, above which one drift ruling goes; the `## Runs` heading, above which the round-2
  section goes; the end of the file, inside `## Runs`, where the run's line goes; LF)
- Test: none in the repo. The full run is the check, read by two check scripts that read files and git only and are
  saved outside the repo: `C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/run_check.py` (Step 1a) and
  `C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/readme_check.py` (Step 1b).

This task changes no code. It runs the whole repo suite once with the KEYLESS prefix, writes what that run proved
into the README (C17) and the ledger, and commits the run record, the README and the ledger together. It makes no
network call: the KEYLESS prefix keeps every keyed client of the inherited suites off KIS, Upbit and OKX (Global
Constraints 0.2), and Step 3a proves it for the one shared token file.

Notes for the implementer (read before starting):
- Work from the repo root `C:/Users/whydi/OneDrive/Desktop/TRADEGEN` in Git Bash (the Bash tool), on branch
  `e1-account-inquiry`, with Task 12 committed on top.
- QUANTGEN overlap check before every command that runs Python on repo code (Global Constraints 0.3). Every such
  command below starts with the Git Bash form, the PowerShell script in single quotes so Bash leaves `$_` alone:
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`.
  When the check finds a process, nothing after `&&` runs and the line prints only `exit 1` (or nothing): wait, then
  run it again. The two check scripts import no repo code; they carry the prefix anyway, so no reading of
  `qa/acceptance_results.json` ever overlaps a run that is still writing it.
- The full run takes about 15 to 17 minutes (609 s of test time in the 2026-10-24 record, plus the tests the
  follow-up and the odds plan added to compliance, the odds suite's about 3.3 minutes, the E1 suite's under 1 minute
  and the imports of every suite). The Bash tool's foreground limit is `timeout: 600000` (10 minutes), so Step 3a
  starts it with `run_in_background: true` and waits for the exit notification. Do not poll its output file, and
  start no other run until it has exited.
- Every edit of an existing file starts by re-reading it with the Read tool (the Edit tool refuses a file it has not
  read) and applies the DRIFT RULE (Global Constraints 0.6): the quoted old text is the anchor, the line number only
  a hint. In README.md no earlier plan is drafted to touch the status bullets, the cockpit row's scan list or the
  compliance row's description (the odds plan's Task 19 changes the compliance count, adds the odds row and rewrites
  the Total line), so Edits R1 to R3 should match as quoted; if one does not, quote the text as README.md now reads
  and record the drift in Edit L0. The compliance row's last cell and the Total line WILL have drifted: the
  follow-up's Task 8 and the odds plan's Task 19 both rewrote them (and the odds row now sits above the Total line).
  Edits R4 and R5 say how to quote them; Edit L0 records that drift in the ledger.
- `README.md` and `qa/acceptance_results.json` are CRLF: edit README.md only with the Edit tool (it keeps CRLF),
  never `sed -i`; only `tests/run_all.py` writes the record. The ledger is LF.
- The real `~/.tradegen` is read here (file metadata only) and never written. The E1 wrapper watches
  `~/.tradegen/execution`, `~/.tradegen/compliance` and `~/.tradegen/kis_token.json`, and the compliance wrapper
  watches `~/.tradegen/compliance`, around every test. The daily task `tradegen-compliance-daily` appends to
  `~/.tradegen/compliance/alerts.jsonl` at about 09:00 to 09:10 KST (compliance execution ledger:67, a deferred
  minor), so Step 3a starts the run outside 08:30 to 09:15 KST. To wait, use the Monitor tool (an until-loop on
  Step 3a's time line) or start the run later in the session; never a foreground `sleep`, which the Bash tool
  blocks. If a run still spans 09:00 to 09:10 KST, Step 3a's real-home rule (G3-4) applies.
- E8 holds the E1 suite under 60 s; this task measures it from the full run's own rows. Time budgets follow round-3
  ruling G3-2 (E3-8): from 60 s up to 120 s the run passes and the Runs line records the measured time; no test is
  changed. At 120 s or more, stop: the controller rules and may split the module.
- Counts follow G3-1: the drafted counts are 228 E1 tests (Tasks 1 to 12) and one new compliance test (Task 9).
  A run with 0 failed and other counts passes, and the Runs line names the difference and its reason, taken from
  the ledger line of the task that changed the count. A FAIL never passes.

**Interfaces:**
- Consumes:
  - `tests/run_all.py` with no argument (tests/run_all.py:92-123 at `5816d3c`; Task 1 and the odds plan added the
    `execution` and `odds` groups): it runs every suite, writes `qa/acceptance_results.json` even when a test fails
    (rows `{"test": "<group>/...", "status": "PASS" | "FAIL" | "NOT_RUN", "seconds": float, "detail": str}`, plus
    `"reason"` on a NOT_RUN row), and ends with `<passed>/<total> passed, <failed> failed, <not run> not run; <path>`.
  - Task 1: `tests/execution_acceptance.py` (`tests()` names every E1 test `execution_<module>/<test>`, so the
    record holds `execution/execution_<module>/<test>`; it collects the module-level `test_*` functions of the 11
    stems in its `MODULES`; the run check compares them with the `test_*` functions of every `tests/execution_*.py`
    but the two harness files `execution_acceptance.py` and `execution_fixtures.py`, so a test module outside
    `MODULES` fails the check); the ledger with its sections
    `## Drift rulings`, `## Deferred minors` and `## Runs`, every entry a line starting `- Task <n>` (continuation
    lines start with two spaces); the `execution` name in both `one suite:` lists, which this task leaves alone.
  - Task 9: the one compliance test it adds,
    `compliance/compliance_gate/test_d16_rows_lift_only_on_live_deposit_evidence`.
  - The tests named in the round-2 section of Edit L1, each written by the task the line names: Task 2's
    `test_send_is_pinned` (execution_guards) and `test_send_opens_one_session_with_trust_env_off_and_no_redirects`;
    Task 4's `test_two_seoul_days_land_in_two_files_under_one_lock_file`; Task 5's
    `test_a_missing_or_malformed_field_fails_closed_with_its_name` and
    `test_kis_sends_nothing_and_reads_no_key_unless_the_code_is_signed`; Tasks 6 and 7's
    `test_a_malformed_field_fails_closed_with_names_only`; Task 7's
    `test_self_check_passes_only_exact_read_only_spot_without_borrow_and_with_an_ip`; Task 10's
    `test_change_and_heartbeat_records_give_the_same_evidence_as_one_record_per_poll` and
    `test_the_first_poll_of_the_next_seoul_day_is_a_heartbeat_for_every_judged_item`; Task 11's
    `test_due_fires_once_per_venue_and_text_key_per_seoul_day`, `test_due_a_level_rise_fires_at_once`,
    `test_missing_keys_alert_once_a_day_never_as_an_outage_and_clear_when_ok`,
    `test_unsigned_kis_alerts_once_a_day_and_nothing_else` and
    `test_due_writes_the_not_set_row_once_a_day_and_never_clears_it`; Task 12's
    `test_a_second_poller_exits_0_and_polls_nothing`,
    `test_each_seoul_day_has_its_own_inquiry_file_and_a_poll_reads_two`,
    `test_keyless_signed_home_sends_nothing_and_alerts_key_missing`,
    `test_unsigned_code_sends_nothing_to_kis_and_alerts_once_a_day` and
    `test_the_not_set_row_is_written_once_a_day_and_never_sent`. A name the executed task changed is a drift ruling:
    Step 4b names it; write the name as it is in the tree and record the ruling.
  - The README readers, run again in Step 4b: `execution_guards/test_suite_is_registered_in_run_all_and_readme`
    (Task 1), `compliance_guards/test_suite_is_registered_in_run_all_and_readme` (the follow-up),
    `odds_guards/test_suite_is_registered_in_run_all_and_readme` (the odds plan) and
    `tests.macro_ui_components.test_readme_carries_both_disclaimers_and_no_stale_counts` (it needs both disclaimers,
    every `**P<n>.` paragraph and no stale count string).
  - Task 12's CLI `python -m execution.poll` (the README bullet names it).
- Produces:
  - `README.md`: the E1 status bullet, the cockpit and compliance wording, the compliance count, the `execution` row
    and the **Total** line of this run (C17);
  - the committed record `qa/acceptance_results.json` of a KEYLESS full run with 0 failed;
  - the ledger with four sections, in order `## Drift rulings`, `## Deferred minors`, `## Round-2 rulings as applied`
    (E1R2-1 to E1R2-12, one entry each) and `## Runs` (ending with this run's `- Task 13: full run (KEYLESS) ...`
    line). Task 14 adds its own `- Task 14` entries to these sections.

**Plan decisions used:** E1 (order and the DRIFT RULE), E8 (the suite under 60 s), E28 (the real-home watch), E35
(the ledger); E1R2-1 to E1R2-12, recorded as applied (contract section 20); round-3 rulings G3-1 (counts), G3-2
(time budgets; E3-8) and G3-4 (the daily job's window); contract 0.2 (KEYLESS), 0.3, 0.4, 0.6 and 17.

- [ ] **Step 1a: Write the failing test(s): the run check**

  Pre-flight first, from the repo root (git only):

```bash
git branch --show-current
git status --short
git log -1 --format=%s
git ls-files --eol README.md qa/acceptance_results.json docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
grep -c "^## " docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
```

  Expected: `e1-account-inquiry`; `git status --short` prints nothing (an untracked plan file under
  `docs/superpowers/plans/` is allowed and is never staged); the subject
  `feat(execution): the poller, alerts.jsonl and the alert CLI` (Task 12; a later review-fix commit of Task 12 is
  allowed); the two CRLF files start `i/crlf  w/crlf  attr/-text` and the ledger `i/lf    w/lf    attr/-text`;
  and `3` (the ledger's three headings of Task 1). Anything else: stop and rule.

  Then save this script with the Write tool as
  `C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/run_check.py` (outside the repo; this task adds no file to
  the repo). It compares the working-tree record with the previous full run's record, which is the one at `HEAD`:
  every E1 task restored the file after each `--suite` run, so `HEAD` still holds the odds plan's committed run. It
  prints the README cells and the ledger command that Step 3b uses, and its last line is `OK` or `FAIL: ...`.

```python
"""Task 13 run check: the full-run record against the previous full run (HEAD's record); reads only."""
from __future__ import annotations

import collections
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RECORD = Path("qa/acceptance_results.json")
LEDGER = "docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md"
NEW = json.loads(RECORD.read_text(encoding="utf-8"))
OLD = json.loads(subprocess.run(["git", "show", "HEAD:qa/acceptance_results.json"],
                                capture_output=True, check=True).stdout.decode("utf-8"))
KEYISH = re.compile(r"(?i)key|credential|token|\.env")
problems: list[str] = []


def totals(rows: list[dict]) -> str:
    n = collections.Counter(r["status"] for r in rows)
    return f"{n['PASS']}/{len(rows)} passed, {n['FAIL']} failed, {n['NOT_RUN']} not run"


def cell(rows: list[dict], group: str) -> str:
    n = collections.Counter(r["status"] for r in rows if r["test"].split("/", 1)[0] == group)
    return f"{n['PASS']} PASS / {n['NOT_RUN']} NOT_RUN" if n["NOT_RUN"] else f"{n['PASS']} PASS"


def safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9 ._:/,()=+-]", " ", text)[:160].strip()


old = {r["test"]: r for r in OLD}
new = {r["test"]: r for r in NEW}
# G3-1: the drafted counts. Tasks 1 to 12 write 228 E1 tests and Task 9 one compliance test; on a repeat run
# HEAD's record is Task 13's own, so no compliance row is new.
DRAFTED_EXECUTION = 228
DRAFTED_COMPLIANCE_DELTA = 0 if any(t.startswith("execution/") for t in old) else 1
run_date = datetime.date.fromtimestamp(RECORD.stat().st_mtime).isoformat()
problems += [f"FAIL row {r['test']}" for r in NEW if r["status"] == "FAIL"]
gone = [t for t in old if t not in new]
ledger_text = Path(LEDGER).read_text(encoding="utf-8")
problems += [f"a row of the previous run is gone and no ledger line names it: {t}" for t in gone
             if t.rsplit("/", 1)[-1] not in ledger_text]
added = [t for t in new if t not in old and not t.startswith("execution/")]
changes = []
for t in new:
    if t in old and new[t]["status"] != old[t]["status"]:
        before, after, reason = old[t]["status"], new[t]["status"], new[t].get("reason", "")
        changes.append(f"  - {t}: {before} -> {after}" + (f", {safe(reason)}" if safe(reason) else ""))
        if after == "NOT_RUN" and not KEYISH.search(reason):
            problems.append(f"{t} turned NOT_RUN for a reason that names no key: stop and rule")
ex = [r for r in NEW if r["test"].startswith("execution/")]
if not ex:
    problems.append("the record holds no execution rows")
defined = set()
for path in sorted(Path("tests").glob("execution_*.py")):
    if path.stem not in ("execution_acceptance", "execution_fixtures"):
        src = path.read_text(encoding="utf-8")
        defined |= {f"execution/{path.stem}/{n}" for n in re.findall(r"^def (test_\w+)\(", src, re.M)}
if ex and defined != {r["test"] for r in ex}:
    problems.append(f"execution rows differ from the defined tests: {sorted(defined ^ {r['test'] for r in ex})}")
problems += [f"execution row not PASS: {r['test']} {safe(r.get('reason', ''))}" for r in ex
             if r["status"] != "PASS" and not r.get("reason", "").startswith("REFDATA:")]
seconds = round(sum(r["seconds"] for r in ex), 1)
slowest = sorted(ex, key=lambda r: -r["seconds"])[:5]
if seconds >= 120.0:
    problems.append(f"the execution suite took {seconds} s, over twice the 60 s target (E8, G3-2): "
                    "a ruling for the controller")
groups = list(dict.fromkeys(r["test"].split("/", 1)[0] for r in NEW))
comp = sum(t.startswith("compliance/") for t in new) - sum(t.startswith("compliance/") for t in old)
drafted = (len(ex), comp) == (DRAFTED_EXECUTION, DRAFTED_COMPLIANCE_DELTA)
print("previous full run:", totals(OLD))
print("this run:", totals(NEW), "on", run_date)
print("rows added outside execution:", added)
print("rows gone since the previous run:", gone)
print("status changes:", len(changes))
if changes:
    print(*changes, sep="\n")
print("execution:", len(ex), "rows,", seconds, "s; five slowest:", [(r["test"], r["seconds"]) for r in slowest])
print(f"drafted: execution {DRAFTED_EXECUTION} rows, compliance {DRAFTED_COMPLIANCE_DELTA:+d}; "
      f"this run: {len(ex)} rows, {comp:+d}" + ("" if drafted else " (G3-1: fill in <reason>)"))
print("README cells:", "; ".join(f"{g}={cell(NEW, g)}" for g in groups))
print(f"README Total: {totals(NEW)} ({run_date}, TRADEGEN `.venv`)")
line = (f"- Task 13: full run (KEYLESS) {totals(NEW)} on {run_date}; previous full run {totals(OLD)}; "
        f"execution {cell(NEW, 'execution')} in {seconds} s"
        + (" (over the 60 s target, E8, G3-2)" if seconds >= 60.0 else "")
        + f"; compliance {cell(NEW, 'compliance')} ({comp:+d}); status changes {len(changes)}"
        + (" (below)" if changes else "")
        + (f"; rows gone since the previous run (see their ledger lines): {', '.join(gone)}" if gone else "")
        + ("" if drafted else f"; drafted execution {DRAFTED_EXECUTION} / compliance {DRAFTED_COMPLIANCE_DELTA:+d}, "
                              f"this run {len(ex)} / {comp:+d}: <reason>"))
print("APPEND: printf '%s\\n' " + " ".join(f'"{x}"' for x in [line, *changes]) + f" >> {LEDGER}")
print("OK" if not problems else "FAIL: " + "; ".join(problems))
sys.exit(1 if problems else 0)
```

- [ ] **Step 2a: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/run_check.py; echo "exit $?"
```

  Expected: `previous full run:` and `this run:` give the same totals (the working-tree record is still the committed
  one), `execution: 0 rows, 0 s; five slowest: []`,
  `drafted: execution 228 rows, compliance +1; this run: 0 rows, +0 (G3-1: fill in <reason>)` (the record has no E1
  run yet), then the last two lines:

```text
FAIL: the record holds no execution rows
exit 1
```

  Note the `previous full run:` totals: they must equal the README **Total** line as the odds plan left it. If they
  differ, the committed record and the README disagree before this task: stop and rule.

- [ ] **Step 3a: Implement: the full KEYLESS run**

  Before the run, three read-only checks (no repo code):

```bash
.venv/Scripts/python.exe -I -c "import datetime, zoneinfo; t = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Seoul')).time(); print(t.strftime('%H:%M KST'), 'wait until 09:15 KST' if datetime.time(8, 30) <= t < datetime.time(9, 15) else 'ok to start')"
stat -c '%n %s %Y' ~/.tradegen/kis_token.json 2>/dev/null || echo "no kis_token.json"
test -e ~/.tradegen/execution && echo "a real E1 home exists" || echo "no real E1 home"
```

  Expected: `ok to start` (on `wait until 09:15 KST`, wait with the Monitor tool until the line prints `ok to start`,
  or come back to this step later in the session; never a foreground `sleep`); the token line (path, size, mtime),
  or `no kis_token.json`; keep it for after the run; and `no real E1 home` (no live poll has run yet; Task 14 is the
  first). `a real E1 home exists` means something polled live before Task 14: stop and report it.

  Every "stop and report" of this step is reported to the owner in this form, metadata only (paths, sizes and
  mtimes from the `stat` and `git status` lines; never a file's content, a value or a key):

```text
Task 13 stopped before its commit. What changed: <the path, with its size and mtime before and after the run, or
"~/.tradegen/execution exists although no live poll has run", or the FAIL row's test id and the paths it names>.
E1 has no order path, and Task 13 waits here until you rule. The real odds are unchanged by E1: no plan without a
real edge that keeps the floor can beat about 1 in 1,000 (1 in 2,000 with the floor at half the stake), and the
research estimates the practical chance of 1,000x in a month at 0.01% or less. This is not legal or investment
advice; I am not a licensed advisor.
```

  Then the full run, with the Bash tool's `run_in_background: true` (the overlap check gates the whole group, so a
  running `run_all` makes the command exit 1 and print nothing):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && { KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py; echo "exit $?"; date +%F; }
```

  Expected, at the end of its output when the notification arrives:

```text
<passed>/<total> passed, 0 failed, <not run> not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
<the date of the run, YYYY-MM-DD>
```

  where, against the Step 2a `previous full run:` totals, the drafted values (G3-1) are: `<total>` = previous + 229
  (Tasks 1 to 12's 228 E1 tests and Task 9's one compliance test), `<passed>` = previous + 229, and `<not run>`
  unchanged, unless Step 4a lists status changes. A run with 0 failed and other counts still passes: Step 4a's
  `drafted:` line names the difference. If the background command ends with exit code 1 and no output, the overlap
  check found another `run_all.py`: wait and start it again.

  If any test fails or the run is cut short, stop. The runner writes the record even then, so restore it first:

```bash
git checkout -- qa/acceptance_results.json
```

  Then find the task whose change broke the test and fix it there with its own failing test, as a fix commit; never
  edit a guard to make it pass. Stage only the files the fix names (never `qa/acceptance_results.json`, which only
  Step 5 commits because the run check reads the previous run from `HEAD`, and never this task's uncommitted
  `- Task 13` ledger lines), check that `git diff --cached --stat` equals `git diff --cached --stat --ignore-cr-at-eol`,
  and end the message with the model trailer (Global Constraints 0.4); then start Step 3a again.

  A FAIL whose detail starts `the test touched the real ~/.tradegen` names what changed. Three wrappers watch the
  real home, and each prints its own form:
  - E1 (`execution/...` rows):
    `the test touched the real ~/.tradegen: [('<home>/.tradegen/compliance/alerts.jsonl', ...`;
  - compliance (`compliance/...` rows): `the test touched the real ~/.tradegen/compliance: [('alerts.jsonl', ...`;
  - odds (`odds/...` rows): `the test touched the real ~/.tradegen/odds or compliance: [(1, 'alerts.jsonl', ...`.

  When any of these names only `alerts.jsonl` under compliance and the run spanned 09:00 to 09:10 KST, it is the
  daily task, not a bug (G3-4): add one `- Task 13: ...` entry at the end of `## Deferred minors` (Edit tool; anchor:
  the `## Runs` heading, old text `## Runs`, new text the entry, a blank line and `## Runs`) and run again outside
  that time. Any other real-home FAIL is a bug: stop and report.

  After the run, the same two real-home checks, then the tree:

```bash
stat -c '%n %s %Y' ~/.tradegen/kis_token.json 2>/dev/null || echo "no kis_token.json"
test -e ~/.tradegen/execution && echo "a real E1 home exists" || echo "no real E1 home"
git status --short
git ls-files --eol qa/acceptance_results.json
```

  Expected: the token line exactly as before the run (KEYLESS kept cockpit test_21's KIS client from asking for a
  token); `no real E1 home`; ` M qa/acceptance_results.json`, plus
  ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` only when this step's deferred-minor
  entry for the daily task was added before the rerun (and the untracked plan file, if any); and
  `i/crlf  w/crlf  attr/-text` (the runner writes the file in text mode, so it stays CRLF). A changed token line
  means a KIS token was issued during the run: stop and report it. Any other changed or new file means a test wrote
  into the repo: stop and report it.

- [ ] **Step 4a: Run to verify it passes**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/run_check.py; echo "exit $?"
```

  Expected: the last two lines are `OK` and `exit 0`, and above them:
  - `this run:` the totals of Step 3a's summary line, then `on` and the run's date;
  - `rows added outside execution: ['compliance/compliance_gate/test_d16_rows_lift_only_on_live_deposit_evidence']`.
    Another entry is a test some E1 task added outside `tests/execution_*.py`: it needs a ledger line of that task;
    without one, stop and rule;
  - `rows gone since the previous run: []`. An entry means an E1 task renamed or removed an inherited test (for
    example in Task 9's compliance test edits). The check accepts it only when the ledger already names that test
    (the drift ruling of the task that changed it, with the old and new names) and then adds the gone ids to the
    Runs line; a gone row the ledger does not name fails the check
    (`a row of the previous run is gone and no ledger line names it`): stop and rule;
  - `status changes: 0`. This is why NOT_RUN should not move: no inherited test raises NotRun on a missing key (the
    one keyed test, cockpit test_21, passes either way: it only asks a failed answer for a reason), and every
    inherited REFDATA and OWNER NOT_RUN is raised whatever the keys are. When the previous full run had keys and a
    test does turn NOT_RUN under the KEYLESS prefix, the check lists it as `  - <test>: PASS -> NOT_RUN, <reason>`;
    that is the KEYLESS prefix turning a keyed check off, not a failure, and Step 3b writes each such line into the
    ledger with the run's line. `NOT_RUN -> PASS` (for example after Developer Mode was turned on) is listed the same
    way. A test that turned NOT_RUN for a reason that names no key or credential fails the check: stop and rule;
  - `execution: 228 rows, <s> s; five slowest: [...]`, `<s>` below 60.0 by E8. The check fails when the execution
    rows are not exactly the `test_*` functions of `tests/execution_*.py`, or when one is not PASS (a `REFDATA:`
    NOT_RUN is accepted, which happens only off Windows). From 60 s up to 120 s the run passes and the Runs line
    records the measured time with `(over the 60 s target, E8, G3-2)`; no test is changed. At 120 s or more the
    check fails (`over twice the 60 s target (E8, G3-2): a ruling for the controller`): stop; the controller rules
    and may split the module;
  - `drafted: execution 228 rows, compliance +1; this run: 228 rows, +1`. Other counts with 0 failed pass (G3-1):
    the line then ends `(G3-1: fill in <reason>)` and so does the Runs line in the `APPEND:` command, with
    `; drafted execution 228 / compliance +1, this run <n> / <comp>: <reason>`. Find the task whose ledger line
    explains the change (a test added, merged or renamed, with its ruling) and replace `<reason>` in the command by
    that reason, naming the task, before Step 3b runs it (plain words: no quotes, backticks, `$` or backslashes). A
    count that no task's ledger line explains: stop and rule;
  - a `README cells:` line with one `<group>=<cell>` per group (for example `cockpit=47 PASS`), and a
    `README Total:` line. Step 3b copies these into README.md;
  - an `APPEND:` line: a complete `printf` command that appends this run's Runs line (and one line per status
    change) to the ledger. Step 3b runs it.

  Keep this whole output for Step 3b.

- [ ] **Step 1b: Write the failing test(s): the README and ledger check**

  Save this script with the Write tool as
  `C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/readme_check.py`. It checks README.md against C17 and the
  record (every group's last cell, the execution row right above the Total line, the Total line itself, both line
  endings), and the ledger's form: the four sections in order, every entry naming its task, E1R2-1 to E1R2-12 once
  each with every test it names PASS in the record, `owner._RECORD_DISTS` unchanged on the branch (E1R2-10), this
  run's Runs line with no `<reason>` left in it, and every status change of the run listed under it. The E1 bullet
  must sit right after the status bullet and end where the next bullet starts, whichever bullet that is; the old
  cockpit and compliance words are looked for in those two rows only.

```python
"""Task 13 README and ledger check against the full-run record; reads only."""
from __future__ import annotations

import collections
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RECORD = Path("qa/acceptance_results.json")
LEDGER = Path("docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md")
ROWS = json.loads(RECORD.read_text(encoding="utf-8"))
RUN_DATE = datetime.date.fromtimestamp(RECORD.stat().st_mtime).isoformat()
BULLET = (
    "- **Read-only account inquiry (E1).** `python -m execution.poll` reads balances,",
    "  open orders, fills, deposits and withdrawals on KIS, Upbit and OKX through one",
    "  GET-only transport with frozen allowlists, and only alerts. It places no",
    "  order. A KIS key can also trade: only E1's own code keeps it read-only, so E1",
    "  sends nothing to KIS until you have signed that code. E1 also reads the KIS",
    "  account (balances, orders, fills), so P0's \"KIS is used for read-only",
    "  quotations only\" describes the macro package; the P0 read-only guards are",
    "  narrowed, file by file, for `execution/kis_inquiry.py` and",
    "  `execution/upbit_inquiry.py`.",
)
EXECUTION_ROW = ("| execution | `tests/execution_acceptance.py` over `tests/execution_*.py` | E1 read-only account "
                 "inquiry, offline: the frozen allowlists and refusals before any key is read, Upbit JWT and OKX "
                 "signing, the shared KIS token cache, KIS read only under signed code, the OKX read-only self-check, "
                 "snapshots and fail-closed positions, D16 deposit evidence (written on change and daily) with "
                 "next-Seoul-day lifting and 7-day expiry, every poll check, alert text without balances or "
                 "addresses, the poller CLI, and the guards (file-exact KIS and Upbit exceptions) |")
PRESENT = ("no account credentials requested outside `execution/kis_inquiry.py`, Settings shows presence not values",
           "D15 refusals and D16 refusals that only live deposit evidence lifts",
           "on any venue; KIS is used for read-only quotations only.",
           "Not investment advice: QUANTGEN is a read-only research desk with no order path.")
ABSENT = (("cockpit", "no account credentials requested, Settings"), ("compliance", "D15 and D16 refusals"))
SECTIONS = ("## Drift rulings", "## Deferred minors", "## Round-2 rulings as applied", "## Runs")
problems: list[str] = []


def totals(rows: list[dict]) -> str:
    n = collections.Counter(r["status"] for r in rows)
    return f"{n['PASS']}/{len(rows)} passed, {n['FAIL']} failed, {n['NOT_RUN']} not run"


def cell(group: str) -> str:
    n = collections.Counter(r["status"] for r in ROWS if r["test"].split("/", 1)[0] == group)
    return f"{n['PASS']} PASS / {n['NOT_RUN']} NOT_RUN" if n["NOT_RUN"] else f"{n['PASS']} PASS"


raw = Path("README.md").read_bytes()
if raw.count(b"\n") != raw.count(b"\r\n"):
    problems.append("README.md has a line that does not end in CRLF")
lines = raw.decode("utf-8").split("\r\n")
at = lines.index("  order audit log.") + 1 if "  order audit log." in lines else 0
if tuple(lines[at:at + len(BULLET)]) != BULLET or not lines[at + len(BULLET)].startswith("- **"):
    problems.append("the E1 status bullet is not right after the status bullet")
text = "\n".join(lines)
problems += [f"README lacks: {s}" for s in PRESENT if s not in text]
problems += [f"README still has: {s}" for group, s in ABSENT
             if any(s in line for line in lines if line.startswith(f"| {group} | "))]
for group in dict.fromkeys(r["test"].split("/", 1)[0] for r in ROWS):
    found = [line for line in lines if line.startswith(f"| {group} | ")]
    if len(found) != 1 or found[0].rsplit("|", 2)[-2].strip() != cell(group):
        problems.append(f"the {group} row is not one row ending | {cell(group)} |: {[f[-40:] for f in found]}")
total = f"| **Total** | `tests/run_all.py` | | {totals(ROWS)} ({RUN_DATE}, TRADEGEN `.venv`) |"
if total not in lines or lines[lines.index(total) - 1] != f"{EXECUTION_ROW} {cell('execution')} |":
    problems.append(f"the execution row and then the Total row {total} are not in the suite table")
ledger = LEDGER.read_bytes()
if b"\r" in ledger:
    problems.append("the ledger has a CR")
entries: dict[str, list[str]] = {}
section = ""
for line in ledger.decode("utf-8").split("\n"):
    if line.startswith("## "):
        section = line
        entries[section] = []
    elif line.startswith("- ") and section:
        entries[section].append(line)
    elif line.startswith("  ") and section and entries[section]:
        entries[section][-1] += " " + line.strip()
    elif line.strip() and section:
        problems.append(f"ledger line outside the entry form: {line[:60]}")
if tuple(entries) != SECTIONS:
    problems.append(f"ledger sections {tuple(entries)} are not {SECTIONS}")
for name in ("## Drift rulings", "## Deferred minors", "## Runs"):
    problems += [f"{name} entry without a task: {e[:60]}" for e in entries.get(name, [])
                 if not re.match(r"- Task \d+\b", e)]
rulings = entries.get("## Round-2 rulings as applied", [])
if [e.split(" ", 2)[1] for e in rulings] != [f"E1R2-{n}" for n in range(1, 13)]:
    problems.append("the round-2 section is not E1R2-1 to E1R2-12, one entry each, in order")
passed = {r["test"].rsplit("/", 1)[-1] for r in ROWS if r["status"] == "PASS"}
for entry in rulings:
    problems += [f"{entry.split(' ', 2)[1]}: no PASS row for {t}" for t in re.findall(r"`(test_\w+)`", entry)
                 if t not in passed]
owner_diff = subprocess.run(["git", "diff", "-U0", "main...HEAD", "--", "core/compliance/owner.py"],
                            capture_output=True, check=True).stdout.decode("utf-8").splitlines()
if any("_RECORD_DISTS" in line for line in owner_diff
       if line.startswith(("+", "-")) and not line.startswith(("+++ ", "--- "))):
    problems.append("E1R2-10: owner._RECORD_DISTS changed on this branch")
runs = entries.get("## Runs", [])
if not any(e.startswith(f"- Task 13: full run (KEYLESS) {totals(ROWS)} on {RUN_DATE};") for e in runs):
    problems.append("the Runs section has no Task 13 line for this record")
if any("<reason>" in e for e in runs):
    problems.append("a Runs line still holds <reason>: fill it in (G3-1)")
before = {r["test"]: r["status"] for r in json.loads(subprocess.run(
    ["git", "show", "HEAD:qa/acceptance_results.json"], capture_output=True, check=True).stdout.decode("utf-8"))}
problems += [f"the Runs section does not list the status change of {r['test']}" for r in ROWS
             if before.get(r["test"], r["status"]) != r["status"] and r["test"] not in " ".join(runs)]
print("README and ledger match the record" if not problems else "FAIL: " + "; ".join(problems))
sys.exit(1 if problems else 0)
```

- [ ] **Step 2b: Run to verify it fails**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/readme_check.py; echo "exit $?"
```

  Expected: one line starting `FAIL: the E1 status bullet is not right after the status bullet; README lacks: no
  account credentials requested outside`, then `exit 1`. Its problems, in order, are: the two `README lacks:` and
  the two `README still has:` items; `the compliance row is not one row ending | 340 PASS / 2 NOT_RUN |` (drafted:
  the odds plan's `339 PASS / 2 NOT_RUN` plus Task 9's test; under G3-1 the cell of Step 4a's `README cells:` line);
  `the execution row is not one row ending | 228 PASS |: []` (likewise);
  `the execution row and then the Total row <the expected Total line> are not in the suite table`;
  `ledger sections <the three found> are not <the four expected>`;
  `the round-2 section is not E1R2-1 to E1R2-12, one entry each, in order`;
  `the Runs section has no Task 13 line for this record`; and one
  `the Runs section does not list the status change of <test>` per status change of Step 4a. A row problem for a
  group other than compliance and execution means that group's count moved too: Step 3b's contingency handles it.
  An `E1R2-10:` problem means a task changed `owner._RECORD_DISTS`, against E1R2-10: stop and rule.

- [ ] **Step 3b: Implement: README.md and the ledger**

  Read `README.md` with the Read tool first (DRIFT RULE). Each new text below that holds a count is filled from the
  Step 4a output: `<compliance cell>` is the value after `compliance=` in its `README cells:` line, `<execution cell>`
  the value after `execution=`, and `<Total>` the text after `README Total: `.

  **Edit R1.** Anchor: the end of the status bullet that starts `- **Status (2026-10-23): no order path exists.**`
  (hint README.md:8-13) and the first line of the next bullet (hint :14). The new bullet goes between them (C17),
  wrapped at 80 columns like its neighbours. If the line after `  order audit log.` is another bullet than the one
  quoted (a later plan put one there), quote that line instead in both texts (DRIFT RULE; Edit L0 records it): the
  E1 bullet still goes right after the status bullet. Old text:

```text
  order audit log.
- **Not legal, tax or investment advice.** The software and its author are not a
```

  New text:

```text
  order audit log.
- **Read-only account inquiry (E1).** `python -m execution.poll` reads balances,
  open orders, fills, deposits and withdrawals on KIS, Upbit and OKX through one
  GET-only transport with frozen allowlists, and only alerts. It places no
  order. A KIS key can also trade: only E1's own code keeps it read-only, so E1
  sends nothing to KIS until you have signed that code. E1 also reads the KIS
  account (balances, orders, fills), so P0's "KIS is used for read-only
  quotations only" describes the macro package; the P0 read-only guards are
  narrowed, file by file, for `execution/kis_inquiry.py` and
  `execution/upbit_inquiry.py`.
- **Not legal, tax or investment advice.** The software and its author are not a
```

  P0 (hint :399-401) and the UI disclaimer stay as they are (C17, spec 8): P0 speaks of the macro package, and the
  bullet says where its quotation-only sentence stops.

  **Edit R2.** Anchor: the cockpit row (`| cockpit | `tests/acceptance.py` |`, hint :839 after Edit R1), its list of
  read-only scans. Old text:

```text
no account credentials requested, Settings shows presence not values
```

  New text:

```text
no account credentials requested outside `execution/kis_inquiry.py`, Settings shows presence not values
```

  **Edit R3.** Anchor: the compliance row (`| compliance | `tests/compliance_acceptance.py` ...`, hint :848 after
  Edit R1), the end of its `decide()` kernel parenthesis. If the Edit tool reports the old text is not unique (a
  later row uses the same words), extend it to the left with the words before it in the compliance row. Old text:

```text
D15 and D16 refusals)
```

  New text:

```text
D15 refusals and D16 refusals that only live deposit evidence lifts)
```

  **Edit R4.** Anchor: the last cell of the compliance row. At `5816d3c` the old text is:

```text
final-target checks) | 315 PASS / 2 NOT_RUN |
```

  Expected drift: the follow-up's Task 8 made the cell `325 PASS / 2 NOT_RUN` and the odds plan's Task 19 raised it
  again, so the old text is `final-target checks) | `, then the cell exactly as README.md now reads, then ` |`. By
  the drafts (G3-1) the old text is `final-target checks) | 339 PASS / 2 NOT_RUN |` and the new text
  `final-target checks) | 340 PASS / 2 NOT_RUN |`; the run's cell wins. New text:

```text
final-target checks) | <compliance cell> |
```

  **Edit R5.** Anchor: the `| **Total** |` row, the last row of the suite table (hint :840 at `5816d3c`, :850 once
  the odds row and Edit R1 are in). At
  `5816d3c` the old text is:

```text
| **Total** | `tests/run_all.py` | | 1043/1166 passed, 0 failed, 123 not run (2026-10-24, TRADEGEN `.venv`) |
```

  Expected drift: the follow-up and the odds plan rewrote its counts and date, and the odds row now sits right above
  it, so the old text is the whole Total line exactly as README.md now reads. The new text is two lines, the
  `execution` row of C17 and then the Total line of this run, so the execution row follows the last suite row
  (odds):

```text
| execution | `tests/execution_acceptance.py` over `tests/execution_*.py` | E1 read-only account inquiry, offline: the frozen allowlists and refusals before any key is read, Upbit JWT and OKX signing, the shared KIS token cache, KIS read only under signed code, the OKX read-only self-check, snapshots and fail-closed positions, D16 deposit evidence (written on change and daily) with next-Seoul-day lifting and 7-day expiry, every poll check, alert text without balances or addresses, the poller CLI, and the guards (file-exact KIS and Upbit exceptions) | <execution cell> |
| **Total** | `tests/run_all.py` | | <Total> |
```

  **Contingency (the run wins).** Only for a group other than compliance and execution whose `README cells:` value
  differs from the last cell of its row (Step 2b named it). The anchor is that row, named by its first cell. Old
  text: ` | <the last cell exactly as README.md reads> |` at the end of that row; new text: ` | <that group's value> |`.
  When the Edit tool reports the old text is not unique, extend it to the left with the words before it in that row.
  Each such row also gets a ledger entry in Edit L0.

  Then the line endings of README.md:

```bash
.venv/Scripts/python.exe -I -c "b = open('README.md', 'rb').read(); print(b.count(b'\n'), b.count(b'\r\n'))"
git diff --stat README.md
git diff --stat --ignore-cr-at-eol README.md
git diff --numstat README.md
```

  Expected: `902 902` (every line still ends in CRLF; 891 lines at `5816d3c`, 892 with the odds row, and ten more
  from Edits R1 and R5; under G3-1 two other equal numbers, ten above the count before this step, pass), two
  identical stat outputs, and the numstat `13	3	README.md` (one more added and one more deleted line for each
  contingency row other than the cockpit row, whose line Edit R2 already changed). Unequal numbers mean an edit
  wrote bare LF: run
  `git checkout -- README.md` and stop and rule.

  **Edit L0 (the ledger, the drift ruling).** Read the ledger with the Read tool first. Anchor: the
  `## Deferred minors` heading (it occurs once; ruling lines that earlier tasks added above it stay as they are).
  Old text:

```text
## Deferred minors
```

  New text:

```text
- Task 13: README.md compliance row count and Total line (C17): the follow-up and the odds plan had
  rewritten both; each now holds this run's counts, the same change on the current text.

## Deferred minors
```

  For each contingency row, add one more entry right after that one, in the same new text:
  `- Task 13: README.md <group> row: the run counts <its value> where the row said <the old cell>; <the reason>`,
  the reason taken from the ledger line of the task that changed that group's tests (for example a REFDATA test that
  now runs). A group whose count moved and that no task's ledger line explains: stop and rule.

  **The ledger cross-check.** Every drift ruling and every deferred minor of Tasks 1 to 12 must already be an entry
  of the ledger: each task recorded its own and committed it with its work. Check it from the branch's history (git
  only):

```bash
git log --reverse --format='%h %s' main..HEAD
git log -i -E --grep='ruling|drift|deferred|minor' --format='%h %s' main..HEAD
grep -n -E "^- Task [0-9]+" docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
```

  The second command lists each commit whose message names a ruling or a deferred minor; read each one's body with
  `git show -s --format=%b <hash>`.

  Expected: every commit body that names a ruling or a deferred minor has a `- Task <n>` entry of that task in the
  ledger, and so does every review-fix commit that changed a plan decision. Add any that is missing now, one entry
  each, in the `- Task <n>: ...` form (Edit tool; a drift ruling above `## Deferred minors`, a deferred minor above
  `## Runs`, before Edit L1 adds the round-2 section there), with the commit's short hash in it.

  **Edit L1 (the ledger, the round-2 rulings as applied).** Anchor: the `## Runs` heading (it occurs once). Old
  text:

```text
## Runs
```

  New text (each entry names the task that applied the ruling and the tests that prove it; Step 4b checks that each
  named test is a PASS row of this run):

```text
## Round-2 rulings as applied

- E1R2-1 (Task 12): `poll.EXIT_LOCKED = 0`; a second poller prints the lock message, exits 0 and polls nothing
  (`test_a_second_poller_exits_0_and_polls_nothing`); argument errors stay 4.
- E1R2-2 (Task 11): `checks.due` dedupes per (venue, text_key) per Asia/Seoul date, and an amber-to-red rise fires
  at once (`test_due_fires_once_per_venue_and_text_key_per_seoul_day`, `test_due_a_level_rise_fires_at_once`).
- E1R2-3 (Task 10, spec rev 2): evidence.jsonl gets a record on a `met` change or as the first poll's daily
  heartbeat, and the fold gives the same live_evidence as one record per poll
  (`test_change_and_heartbeat_records_give_the_same_evidence_as_one_record_per_poll`,
  `test_the_first_poll_of_the_next_seoul_day_is_a_heartbeat_for_every_judged_item`).
- E1R2-4 (Tasks 4 and 12, spec rev 2): one `inquiry-YYYYMMDD.jsonl` per Seoul date, never deleted; a poll opens
  yesterday's and today's only (`test_two_seoul_days_land_in_two_files_under_one_lock_file`,
  `test_each_seoul_day_has_its_own_inquiry_file_and_a_poll_reads_two`).
- E1R2-5 (Tasks 5, 6 and 7): the `[assumed]` fixture fields are accepted; a missing or malformed field fails that
  venue closed and names only the field (`test_a_missing_or_malformed_field_fails_closed_with_its_name`,
  `test_a_malformed_field_fails_closed_with_names_only`); a live mismatch is Task 14's to record.
- E1R2-6 (Task 7): the OKX self-check stays strict on autoLoan
  (`test_self_check_passes_only_exact_read_only_spot_without_borrow_and_with_an_ip`); a spot-mode key (acctLv 1)
  with autoLoan true is Task 14's stop-and-ask, never a loosening.
- E1R2-7 (Task 14): no code; KIS overseas calls that fail because the overseas service is not enabled are Task 14's
  stop-and-ask.
- E1R2-8 (Tasks 11 and 12): one amber KEY_MISSING per venue per Seoul day, never an OUTAGE
  (`test_missing_keys_alert_once_a_day_never_as_an_outage_and_clear_when_ok`,
  `test_keyless_signed_home_sends_nothing_and_alerts_key_missing`).
- E1R2-9 (Tasks 5, 11 and 12, spec rev 2): KIS sends nothing, the token POST included, unless the poll's sealed
  context has code_signed True; one amber KIS_UNSIGNED a day
  (`test_kis_sends_nothing_and_reads_no_key_unless_the_code_is_signed`,
  `test_unsigned_kis_alerts_once_a_day_and_nothing_else`,
  `test_unsigned_code_sends_nothing_to_kis_and_alerts_once_a_day`).
- E1R2-10 (plan header): requests, urllib3, certifi, idna and charset_normalizer stay outside the D14 hash, stated
  as a limit in the header; owner._RECORD_DISTS is unchanged on this branch.
- E1R2-11 (Task 2): `_send` opens one requests.Session() with trust_env False and sends with allow_redirects=False,
  pinned by the guard (`test_send_is_pinned`, `test_send_opens_one_session_with_trust_env_off_and_no_redirects`).
- E1R2-12 (Tasks 11 and 12): one info-level NOT_SET row a day in alerts.jsonl, sent true, never toasted and never
  pending (`test_due_writes_the_not_set_row_once_a_day_and_never_clears_it`,
  `test_the_not_set_row_is_written_once_a_day_and_never_sent`).

## Runs
```

  **Edit L2 (the ledger, the run).** Run the command Step 4a printed after `APPEND: `, exactly as printed (everything
  after that prefix, from `printf` to the ledger's path), except a `<reason>` that Step 4a's `drafted:` bullet said
  to fill in (Step 4b fails while one is left). It appends this run's `- Task 13: full run (KEYLESS) ...`
  line as the last line of the ledger, and after it each status-change line in the order printed. The file is LF,
  and an appended LF line keeps it so (Task 10 appends its Runs line the same way); the check builds every line from
  counts, test ids and reasons stripped of quotes, backticks, `$` and backslashes, so the double quotes hold them
  safely. Then:

```bash
tail -n 3 docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
```

  Expected: `tail` ends with the line or lines just written.

- [ ] **Step 4b: Run to verify it passes**

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13/readme_check.py; echo "exit $?"
```

  Expected:

```text
README and ledger match the record
exit 0
```

  A `no PASS row for test_...` problem names a test of the round-2 section that the executed task named differently:
  find it with `grep -n "def test_" tests/execution_*.py`, put the name from the tree into that entry, add a
  `- Task 13: ...` drift ruling naming both names above `## Deferred minors`, and run the check again. A
  `ledger line outside the entry form` or `entry without a task` problem is an earlier task's line in another form:
  rewrite it in the `- Task <n>: ...` form, keeping its words.

  Then the README readers, which read the file this task changed (module runs, so no results file is written):

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.execution_acceptance execution_guards/test_suite_is_registered_in_run_all_and_readme; echo "exit $?"
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/test_suite_is_registered_in_run_all_and_readme; echo "exit $?"
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/test_suite_is_registered_in_run_all_and_readme; echo "exit $?"
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_ui_components import test_readme_carries_both_disclaimers_and_no_stale_counts as t; t(); print('README test ok')"; echo "exit $?"
```

  Expected: the first three each end `1/1 passed, 0 failed, 0 not run` and `exit 0` (if the odds one reports `0/0`,
  the odds plan named it differently: find it with `grep -n "def test_suite_is_registered" tests/odds_*.py`, as
  Task 1 did); the fourth prints `README test ok` and `exit 0`. A failure means an edit broke what README must hold:
  fix the edit, never the test.

- [ ] **Step 5: Commit**

```bash
git status --short
git add README.md qa/acceptance_results.json docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git diff --cached --numstat -- README.md docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md
```

  `git status --short` lists exactly ` M README.md`,
  ` M docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md` and ` M qa/acceptance_results.json`
  (plus the untracked plan file, if any, which is not staged). The two stat outputs must be identical. The numstat
  reads `13	3	README.md` (plus one and one per contingency row other than cockpit) and
  `41	0	docs/superpowers/plans/2026-10-24-e1-account-inquiry-execution-ledger.md`: Edit L0's three lines, Edit L1's 37
  and the one run line, plus every line this task added besides (the status-change lines, the contingency entries,
  the entries the cross-check added and a real-home deferred minor of Step 3a, each with its lines). Then commit,
  with the trailer naming the model that writes the commit (Global Constraints 0.4):

```bash
git commit -m "test: E1 full run, README rows and the execution ledger" -m "Task 13: the KEYLESS full run record (its totals are in the ledger's Runs line); README gains the E1 status bullet, the cockpit and compliance wording, the execution row and the Total line; the ledger records E1R2-1 to E1R2-12 as applied." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

  (Replace the trailer's model name with the model that writes the commit, for example
  `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.) Expected: the new commit on `e1-account-inquiry`,
  and `git status --short` prints nothing (or only the untracked plan file). Only Task 13 commits
  `qa/acceptance_results.json`: here, and again in each repeat below. The scratch folder
  `C:/Users/whydi/AppData/Local/Temp/tradegen-e1-task13` is outside the repo and may stay (a repeat reuses its two
  scripts).

  **Repeat after a fix.** After any fix commit that changes code or tests (a Task 13 review fix, or one from the
  final branch review), the committed record, the README cells and the Total line describe an older tree (C17).
  Repeat Steps 2a to 5 in their order here, with these differences:
  - The two scripts are already saved (Step 1b saves nothing new). HEAD's record is now Task 13's own run, so Step
    2a prints the same totals twice and ends `OK` and `exit 0` (or a `FAIL: execution rows differ from the defined
    tests` that names exactly the tests the fix added or renamed), and its `previous full run:` totals equal the
    Total line Task 13 wrote.
  - Step 4a expects `rows added outside execution: []` and `drafted: execution 228 rows, compliance +0; this run:
    228 rows, +0` unless a fix changed a count (G3-1: the fix commit's ledger line is the reason).
  - Step 3b: skip Edits R1 to R3, L0 and L1 and the cross-check of Tasks 1 to 12 (they are in). Edit R5's old and
    new texts are the Total line alone (skip it if the line already reads as the run's). A cell that moved, the
    compliance and execution rows included, goes through the contingency, quoting the cell as Task 13 left it, and
    gets one `- Task 13 (repeat): README.md <group> row: ...` entry above `## Deferred minors` naming the fix
    commit's short hash. Edit L2 appends a second `- Task 13: full run (KEYLESS) ...` line (the check accepts any
    line that matches the record). The README line count stays as Task 13 left it (`902 902` by the drafts).
  - Step 3b's and Step 5's README numstat is `1	1` plus one and one per moved row (no README line at all when
    nothing moved), and the ledger numstat `1	0` plus one per status-change line and per entry line added. Stage
    only the record, README.md and the ledger, as in Step 5, check the two stat outputs as there, and commit with
    the subject `test: E1 full run after the review fixes` and a body with the repeat run's Total line, ending with
    the model trailer.
