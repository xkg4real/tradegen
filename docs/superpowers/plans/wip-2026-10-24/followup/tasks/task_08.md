### Task 8: Full run, README counts, the real-home check, the final review and the hand-off

**Files:**
- Modify: `README.md`. Anchors: the last cell of the `| compliance |` row of the suite table (README.md:839) and the
  last cell of the `| **Total** |` row (README.md:840); a contingency names the other nine rows (Step 4). The file is
  CRLF; use the Edit tool only.
- Modify: `qa/acceptance_results.json` (CRLF). The full run of Step 2 writes it, and only this task commits it: once
  in Step 5, and once more if the final review leads to fixes (Step 7).
- Commit: `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` (LF). The executor writes it
  during and after execution; this plan never writes its content. Step 8 commits it before the merge.
- Test: no new test. The full run is the check.

**Interfaces:**
- Consumes:
  - Tasks 1 to 7, each committed on `compliance-followup`.
  - `tests/run_all.py`. With no argument it runs every suite, writes `qa/acceptance_results.json` (rows of
    `{"test": "<group>/...", "status": "PASS" | "FAIL" | "NOT_RUN", ...}`) even when a test fails, and ends with
    `<passed>/<total> passed, <failed> failed, <not run> not run; <path of qa/acceptance_results.json>`
    (tests/run_all.py:92-123).
  - `tests.compliance_acceptance._real_listing() -> tuple`: the (relative path, size, mtime_ns) rows of the real
    `~/.tradegen/compliance`, and `()` when it does not exist (tests/compliance_acceptance.py:31-40). It always reads
    `Path.home() / ".tradegen" / "compliance"` (tests/compliance_acceptance.py:28), whatever `TRADEGEN_HOME` says.
  - `python -m core.compliance.rules --check` (rules.py:931-967). It uses `TRADEGEN_HOME` when that is set, else
    `~/.tradegen` (core/isolation.py:108). While `core/compliance/owner_pubkey.pem` is absent (owner.py:24), the owner
    log is BROKEN "no owner key yet: owner act 1" (owner.py:929), so the check exits 3 and writes nothing.
  - `load_context` needs an approval of all three tables, rules, instruments and venues (owner.py:602 `_TABLES`,
    owner.py:947-961 `_approved_now`).
- Produces:
  - the README compliance and Total counts;
  - the committed full-run record (`test: full run after the compliance follow-up`, and after a fix wave
    `test: full run after the final review wave`);
  - the committed execution ledger (`docs(plan): execution ledger of the compliance follow-up`);
  - the merge, after which the odds plan starts from the merged main (R13);
  - the owner-act hand-off.

**Plan decisions used:**
- R13 (the order of the plans) and the DRIFT RULE;
- R3 (the table sha the owner approves at owner act 3);
- R2, R4 and R6 (the closure changes the owner signs at owner act 2, after the odds plan), and R4's stated limit
  (R2-12), which rests on the owner's review of the hashed files;
- R4, R5 and R11 (the signer copy, owner act 1, and the owner's Windows Terminal, which runs PowerShell).

**Expected counts.**
- Compliance: 327 rows, 325 PASS / 2 NOT_RUN. That is 317 + 10 new tests:
  - Task 1: 1 (guards);
  - Task 2: 6 (5 loader tests and the pin test);
  - Task 4: 1 (source equality);
  - Task 6: 1 (fingerprint);
  - Task 7: 1 (KIS token).
- Full run: 1176 rows, 1053 PASS / 123 NOT_RUN, against 1043/1166 at README.md:840.
- Every other group keeps its README.md:830-838 count.
- A review fix inside a task, or a fix task after the final review, adds its own tests on top. The numbers the run
  prints win over these as long as nothing fails.

**Drift.** No earlier task of this plan edits README.md, and the odds and E1 plans are docs-only commits on main
until this plan merges. Re-read README.md before each Edit anyway (DRIFT RULE).

**The QUANTGEN overlap check.** Run it before every test command and every command that imports repo code: Steps 1,
2 and 6 put it in front. It must print nothing; otherwise wait. The stdlib-only one-liners of Steps 1, 2 and 4 read
a pipe or a file and import no repo code, so they need no check.
- PowerShell tool:
  `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
- Git Bash prefix (the PowerShell script is in single quotes, so Bash leaves `$_` alone):
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`

- [ ] **Step 1: Check the branch, the commits and the compliance suite**

  From the repo root in Git Bash:

```bash
git branch --show-current
git status --short
git log --format=%s --reverse main..compliance-followup | .venv/Scripts/python.exe -I -c "
import sys
for stream in (sys.stdin, sys.stdout):
    stream.reconfigure(encoding='utf-8', errors='replace')
want = [
    'test(guards): ban xml.dom, string-exec modules and bare compile; read the suite lists',
    'fix(compliance): loader refuses D15/D16 content, bounds review_by, max_leverage and {cap}; pin rows',
    'fix(tables): KR-KIS-KRX-DERIV reason names broker approval',
    'fix(compliance): closure scan skips a guard only while its name is unbound and unmutated',
    'fix(signer): the ancestor walk refuses when the chain breaks before a session process',
    'fix(alerts): record a key fingerprint only from a check that verified the log',
    'fix(isolation): check the KIS token and ficc cache targets before side effects',
]
done = 0
for subject in sys.stdin.read().splitlines():
    if done < len(want) and subject == want[done]:
        done += 1
        print('task', done, subject)
    else:
        print('other after task', done, subject)
print('missing:', want[done] if done < len(want) else 'none')
"
```

  Expected:
  - `git branch --show-current` prints `compliance-followup`. If it prints anything else, run
    `git switch compliance-followup` and start this step again.
  - `git status --short` prints nothing. The one exception is the executor's ledger while it is not committed yet:
    `?? docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`.
  - The log check prints the seven task subjects in task order, as `task 1 ...` to `task 7 ...`, and ends with
    `missing: none`.
  - Other commits are allowed, each printed as `other after task <n> <subject>`:
    - a review fix of task `<n>`, made during subagent-driven execution;
    - on a repeat of this step (Step 7), after task 7: the Step 5 record commit
      `test: full run after the compliance follow-up` and the fix commits of the final review.

    Each must have a ledger line that names it. If one has none, write that line from the commit itself
    (`git show --stat <hash>`).

  Stop and report when:
  - `missing:` names a subject: that task is not committed, so finish it first;
  - the tree is dirty beyond the ledger line;
  - a line reads `other after task 0`;
  - an `other` commit is none of the kinds above.

  Then run the compliance suite with the overlap check in front, with the Bash tool's `timeout: 600000`; never start
  a second run meanwhile. The suite's tests took 63.6 s in the 2026-10-24 record, and the guards' registration test
  (`test_suite_is_registered_in_run_all_and_readme`, tests/compliance_guards.py:485) imports `tests.run_all`, which
  imports every suite (tests/run_all.py:41-50). This command's entry point `_main` imports it too, before any test
  runs (tests/compliance_acceptance.py:79).

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance; echo "exit $?"
```

  Expected:
  - every test line is `PASS`, except these two NOT_RUN lines:

```text
NOT_RUN compliance_isolation/test_symlinks_are_refused REFDATA: symlink creation needs Developer Mode
NOT_RUN compliance_tables/test_calendar_sha256_refuses_a_file_symlink REFDATA: symlink creation needs Developer Mode
```

  - then these two lines:

```text
325/327 passed, 0 failed, 2 not run
exit 0
```

  - With Developer Mode on, `327/327 passed, 0 failed, 0 not run` and `exit 0`.
  - On a repeat after a fix wave, the totals grow by the fix tasks' tests, and each of those tests has a ledger line.

  If the output is `exit 1` alone, the overlap check found another `run_all.py`: wait and run the line again. A
  `NOT_RUN ... PENDING` line means a dependency is missing; stop and report it. For a FAIL that names the real
  `~/.tradegen/compliance`, see the ledger:67 bullet in Step 2.

- [ ] **Step 2: Run the full suite with the overlap guard**

  The full run takes about 11 minutes: its tests took 609 s in the 2026-10-24 record. That is longer than the Bash
  tool's 10-minute limit, so start this command with `run_in_background` and wait for its notification. Do not poll
  it, and do not start any other run meanwhile.

  The run includes cockpit test_21 (tests/acceptance.py:318). When KIS keys are set, it makes the quote-only calls
  that every earlier full run made: through `KRXGateway().daily` a KIS token request on a cache miss (cached in
  TRADEGEN's own `~/.tradegen/kis_token.json`, kis_client.py:53) and a daily-price GET, and through `.filings` an
  OpenDART GET when that key is set. This plan accepts them here, once per full run; Task 7 keeps them out of its
  per-suite runs.

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe tests/run_all.py; echo "exit $?"; date +%F
```

  Expected, at the end of the output:

```text
1053/1176 passed, 0 failed, 123 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
```

  A third line follows: the date of the run as `date +%F` prints it. Step 4 writes that date into the Total row.

  If the line reads `exit 1` with no test output, the overlap check found another `run_all.py`: wait and start the
  line again.

  If any test fails, or the run is cut short, stop. `tests/run_all.py` writes the record even when tests fail
  (tests/run_all.py:118), so restore it before anything else:

```bash
git checkout -- qa/acceptance_results.json
```

  Then find the task whose change broke the test and fix it there with its own failing test; never edit a guard to
  make it pass. The likely suspects:
  - **Guards and isolation.** compliance_guards (Task 1's lists over core/compliance), T-CTX-01's isolation report,
    cockpit test_08 and test_09, and T-RO-01.
  - **The kis_client source.** T-RO-02, which re-runs kis_client from its source (Task 7).
  - **The suite lists.** The R7 check (Task 1) reads the `one suite:` lists at tests/run_all.py:113 and
    README.md:816. This plan edits neither list; the odds plan adds `odds` to both.
  - **Not a task bug: ledger:67.** Suppose a compliance FAIL's detail reads
    `the test touched the real ~/.tradegen/compliance: [('alerts.jsonl', ...` and the run spanned 09:00 KST. Then
    the daily alert job `tradegen-compliance-daily` appended a row during the run: ledger:67, a deferred minor.
    Restore the record, write one ledger line, and run Step 2 again outside that time.

  When the run is green, count each group's statuses in the record (read-only):

```bash
.venv/Scripts/python.exe -c "import json, collections; rows = json.load(open('qa/acceptance_results.json', encoding='utf-8')); print(*sorted(collections.Counter((r['test'].split('/', 1)[0], r['status']) for r in rows).items()), sep='\n'); print(len(rows))"
```

  Expected (no `FAIL` entry):

```text
(('cockpit', 'PASS'), 47)
(('compliance', 'NOT_RUN'), 2)
(('compliance', 'PASS'), 325)
(('engine', 'PASS'), 92)
(('expansion', 'PASS'), 19)
(('ficc', 'PASS'), 56)
(('grokteam', 'PASS'), 17)
(('macro', 'NOT_RUN'), 121)
(('macro', 'PASS'), 419)
(('paper', 'PASS'), 21)
(('quant', 'PASS'), 53)
(('ui', 'PASS'), 4)
1176
```

  Only the compliance row changes from the 2026-10-24 record (315 to 325 PASS). If another group's counts differ
  from its README.md:830-838 row, the run wins:
  - give that row's last cell the run's counts in Step 4 (its old text is listed there);
  - write one ledger line naming the group and the reason (for example, a REFDATA test that now runs).

- [ ] **Step 3: Confirm that only the record changed**

```bash
git status --short
git diff --stat
git diff --stat --ignore-cr-at-eol
git ls-files --eol qa/acceptance_results.json
```

  Expected:
  - the only line of `git status --short` is ` M qa/acceptance_results.json`, apart from the untracked ledger line
    allowed in Step 1;
  - the two `--stat` outputs are identical;
  - the eol line reads `i/crlf  w/crlf  attr/-text`, because the run rewrites the file in text mode and keeps CRLF.

  If another tracked file changed, or an untracked file appeared, stop: a test wrote into the repo.

- [ ] **Step 4: Update the README counts (CRLF, Edit tool)**

  Re-read `README.md` (DRIFT RULE), then make the Edit-tool replacements below. Each old text lies inside one line and
  stops before the line end, so every CRLF ending stays as it is.

  Edit 1. The anchor is the last cell of the `| compliance |` row (README.md:839). Old text (exact, it occurs once):

```text
final-target checks) | 315 PASS / 2 NOT_RUN |
```

  New text, with the compliance counts of Step 2 (expected 325 PASS / 2 NOT_RUN):

```text
final-target checks) | 325 PASS / 2 NOT_RUN |
```

  Edit 2. The anchor is the `| **Total** |` row (README.md:840). Old text (exact, it occurs once):

```text
| **Total** | `tests/run_all.py` | | 1043/1166 passed, 0 failed, 123 not run (2026-10-24, TRADEGEN `.venv`) |
```

  New text. Fill the slots from Step 2: the counts from its summary line and the date that `date +%F` printed:

```text
| **Total** | `tests/run_all.py` | | <passed>/<total> passed, 0 failed, <not run> not run (<date from Step 2>, TRADEGEN `.venv`) |
```

  The expected result is
  `| **Total** | `tests/run_all.py` | | 1053/1176 passed, 0 failed, 123 not run (<date from Step 2>, TRADEGEN `.venv`) |`.
  If the date is still 2026-10-24, the date stays as it is.

  Contingency, only for a group whose Step 2 counts differ from its row. The anchor is that group's row, named by its
  first cell. The old text is its last cell, exact, and each one occurs once in README.md:
  - the `| cockpit |` row (README.md:830): `| 47 PASS |`
  - the `| engine |` row (README.md:831): `| 92 PASS |`
  - the `| ui |` row (README.md:832): `| 4 PASS |`
  - the `| quant |` row (README.md:833): `| 53 PASS |`
  - the `| ficc |` row (README.md:834): `| 56 PASS |`
  - the `| expansion |` row (README.md:835): `| 19 PASS |`
  - the `| macro |` row (README.md:836): `| 419 PASS / 121 NOT_RUN |`
  - the `| paper |` row (README.md:837): `| 21 PASS |`
  - the `| grokteam |` row (README.md:838): `| 17 PASS |`

  The new text is the run's counts in the same form: `| N PASS |`, or `| N PASS / M NOT_RUN |` when the group has
  NOT_RUN rows.

  On a repeat after a fix wave (Step 7), the old texts of Edits 1 and 2 are the two cells exactly as the first pass
  left them, re-read from README.md, and the new texts carry the repeat run's counts and date.

  Then check the endings and the diff:

```bash
.venv/Scripts/python.exe -c "b = open('README.md', 'rb').read(); print(b.count(b'\n'), b.count(b'\r\n'))"
git ls-files --eol README.md
git diff --stat README.md
git diff --stat --ignore-cr-at-eol README.md
```

  Expected:
  - `891 891`: every line still ends in CRLF;
  - `i/crlf  w/crlf  attr/-text`;
  - two identical stat outputs, ` README.md | 4 ++--` and `1 file changed, 2 insertions(+), 2 deletions(-)`;
  - two more changed lines for each contingency row.

- [ ] **Step 5: Commit the full-run record and the README**

```bash
git add README.md qa/acceptance_results.json
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  The two stat outputs must be identical, and the ledger stays out of this commit. Then, with the numbers of Step 2
  in the body:

```bash
git commit -m "test: full run after the compliance follow-up" -m "Task 8: full run 1053/1176 passed, 0 failed, 123 not run (compliance 325 PASS / 2 NOT_RUN); README compliance and Total rows." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: The read-only check against the real home**

  This step never writes. With no owner key, `--check` writes nothing. With a key, `load_context` would write a
  snapshot under `~/.tradegen/compliance/snapshots`, so the step skips in that case. It also stops when
  `TRADEGEN_HOME` is set, because then `--check` reads another home than `_real_listing()` lists, and an unchanged
  listing would prove nothing. And it waits while a `run_all.py` runs (the overlap check). Otherwise it lists the
  real compliance home before and after.

```bash
if test -e core/compliance/owner_pubkey.pem; then echo "skip: the owner key exists"
elif test -n "${TRADEGEN_HOME:-}"; then echo "stop: TRADEGEN_HOME is set to $TRADEGEN_HOME"
elif test -n "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')"; then echo "wait: a run_all.py is running"
else
  before=$(.venv/Scripts/python.exe -c "from tests.compliance_acceptance import _real_listing; print(_real_listing())")
  .venv/Scripts/python.exe -m core.compliance.rules --check; echo "exit $?"
  after=$(.venv/Scripts/python.exe -c "from tests.compliance_acceptance import _real_listing; print(_real_listing())")
  test "$before" = "$after" && echo "real ~/.tradegen/compliance unchanged: $before"
fi
```

  If it prints `wait: a run_all.py is running`, wait and run the block again. If it prints
  `stop: TRADEGEN_HOME is set to ...`, stop and report: the shell's profile points the state somewhere else, and only
  the owner can say which home is real.

  Expected when the check ran, among the human lines:
  - `owner log: BROKEN: no owner key yet: owner act 1`
  - `owner log head: entry #0; key fingerprint none`
  - `rules: the draft 74894f05e0b7f1af is not the version in force (none); it counts only once signed`. This is
    Task 3's table: sha `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd`.
  - `instruments: the draft 50fa819f62707eb5 is not the version in force (none); it counts only once signed`
  - `venues: the draft 603e264080f4c69b is not the version in force (none); it counts only once signed`
  - a line starting `exit 3: new exposure is blocked`

  Then exactly these three lines:

```text
{"code": 3, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}
exit 3
real ~/.tradegen/compliance unchanged: ()
```

  `()` means the folder does not exist. If it exists, the tuple lists its entries, and it must print the same before
  and after. If the last line is missing, the check changed the real home: stop and report. If a fix wave (Step 7)
  changed a table, the draft lines of its repeat run win, and Step 9 hands over their shas.

  Write the result in the ledger: `ran` (with exit 3 and the listing) or `skipped: the owner key exists`. Step 9's
  owner texts depend on it.

- [ ] **Step 7: The final review, and the repeat run after a fix**

  1. Request the final review of `main..compliance-followup` (superpowers:requesting-code-review).
  2. Fix each finding the controller takes in a new task with its own failing test, under the rules of Tasks 1 to 7:
     - the DRIFT RULE;
     - the overlap check before each test command;
     - the record restored after each `--suite` run;
     - one commit per fix;
     - one ledger line per finding and per ruling.

     Then request a re-review of the fix commits, and repeat until it finds nothing to fix.
  3. If no fix commit was made, go to Step 8.
  4. After any fix commit, the record and the README rows of Step 5 are stale. Repeat Steps 1 to 6:
     - Step 1's log check also lists the Step 5 record commit and the fix commits as `other after task 7`;
     - the run's numbers win;
     - Step 4 edits the cells as the first pass left them;
     - Step 5 runs as written, but its commit uses this subject and the repeat run's numbers in the body.

     The repeat's Step 5 commit:

```bash
git commit -m "test: full run after the final review wave" -m "Task 8, after the final review: full run <passed>/<total> passed, 0 failed, <not run> not run (compliance <n> PASS / <m> NOT_RUN); README compliance and Total rows." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

     Fill the five slots from the repeat run's Step 2. If README.md did not change, `git add` only
     `qa/acceptance_results.json`, and drop "README compliance and Total rows." from the body. After the repeat's
     Step 6, go to Step 8.

- [ ] **Step 8: Commit the execution ledger**

  `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` is the executor's record. If you kept it
  outside the repo, copy it to that path first. Before the commit, check that it holds:
  - one line per task, with its commit and module counts, and one line per review fix;
  - every DRIFT RULE ruling;
  - "KIS token burnt on refusal" (ledger:239) closed by Task 7;
  - the full-run line of Step 2, and of its repeat if Step 7 made one;
  - the real-home result of Step 6;
  - the final review, each finding and ruling, and the re-review.

```bash
git add docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md
git status --short
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  Expected:
  - `git status --short` prints only
    `A  docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md`;
  - the two stat outputs are identical: `1 file changed, <n> insertions(+)`.

  No test reads a `.md` file under `docs/superpowers`, so this commit leaves the record of Step 5 (or Step 7) current.

```bash
git commit -m "docs(plan): execution ledger of the compliance follow-up" -m "Every task review, fix round, DRIFT RULE ruling, the final review and the full runs of the follow-up execution, kept for the owner's audit and GPT's 2026-10-30 check." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 9: Merge, then hand off**

  1. **Merge** per superpowers:finishing-a-development-branch.
  2. **The odds plan.** Start it from the merged main (R13), under its DRIFT RULE for the files this plan changed.
     The E1 plan follows after the odds plan merges.
  3. **The owner acts.** Tell the owner these in chat. Claude does none of them, and never runs the signer with a
     real key. Pick each text by Step 6's result.

     The order of the plans matters to acts 1 and 2. The E1 plan changes `tools/signer/sign.py` and the D14 code hash
     again (its Task 9, which adds `execution/*.py` to the closure). If you do acts 1 and 2 before E1 lands, you
     re-copy the signer and sign again after it.

     - **Owner act 1, the signer copy.**
       - If Step 6 ran (no owner key), act 1 is not done. When you do it:
         - copy the merged `tools/signer/sign.py` to your folder `$env:USERPROFILE\tradegen-signer\`;
         - read it in full;
         - in Windows Terminal (PowerShell), run
           `certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256`, and write the hash on paper;
         - then finish act 1 as spec section 11 lists it.

         Tasks 4 and 5 changed the file: the closure scan, and the ancestor walk that refuses when the parent chain
         breaks before a Windows session process.
       - If Step 6 printed `skip: the owner key exists`, act 1 is done, and your copy is older than the merged file.
         Re-verify it:
         - read the diff of your copy against the merged file, in Windows Terminal (PowerShell):
           `fc.exe /n "$env:USERPROFILE\tradegen-signer\sign.py" "C:\Users\whydi\OneDrive\Desktop\TRADEGEN\tools\signer\sign.py"`;
         - copy the merged file;
         - run the same `certutil` line;
         - write the new hash on paper.
       - Either way, run the signer from Windows Terminal opened from the Start menu; an editor's terminal can be
         refused.
     - **Owner act 2, one code signature, after the odds plan lands.** It covers this plan's closure changes
       (`core/compliance/rules.py`, `owner.py`, `alerts.py`) and the odds plan's together.
       - Before signing, read the hashed files: every file the signing prompt lists. Today these are
         `core/__init__.py`, `core/isolation.py`, `core/compliance/*.py` and `core/odds/*.py`; E1 adds
         `execution/*.py`.
       - If no `code_approved` exists yet, this is your first signature, so read them in full; otherwise read each
         diff since the signed version.
       - R4's stated limit relies on that review: the closure scan cannot see a module that changes
         `typing.TYPE_CHECKING` for another one, or a name built at run time.
     - **Owner act 3, the three tables, after the odds plan lands and together with act 2.** `load_context` needs an
       approval of all three. Approve:
       - `core/compliance/kr_rules.yaml` as Task 3 left it, sha
         `74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd`;
       - `core/compliance/instruments.yaml`, sha
         `50fa819f62707eb58e09135355b4f84160611ef4a8ad1af7345bb119b6f1431a`, unless a later plan changes it;
       - `core/odds/venues.yaml` as the odds plan leaves it, with the fixed charges and lots its owner gate asks you
         to add. Its sha changes from today's `603e264080f4c69b...`.

       `--check`'s draft lines print the first 16 hex digits of each sha to compare.
     - **What to expect until then.**
       - If Step 6 ran: every new-exposure intent is BLOCK, and `--check` exits 3. That is the designed safe
         default, not a fault.
       - If Step 6 skipped: Claude did not run `--check` against your home, because with your key it would write a
         snapshot there. Run it yourself to see the current state.
