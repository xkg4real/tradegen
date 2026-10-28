### Task 19: Full run, README rows, the real-home smoke, the ledger, the pull request and the hand-off

**Files:**
- Modify: `README.md` (CRLF; Edit tool only, never `sed -i`). Anchors: the last cell of the `| compliance |` row of
  the suite table (hint README.md:839) and the `| **Total** |` row (hint :840); the new `| odds |` row goes between
  them, so the Total row moves to :841. A contingency names the other nine rows (Step 5). Line numbers are hints; the
  quoted text is the anchor (DRIFT RULE).
- Modify: `qa/acceptance_results.json` (CRLF). Only the full run of Step 3 writes it, and only this task commits it:
  once in Step 6, and once more if the final review leads to fixes (Step 8).
- Modify, then commit: `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` (LF; untracked until
  Step 9). Anchors: the `## Deferred minors` heading (one drift ruling goes above it), the `## Runs` heading (two new
  sections go above it), and the end of the file inside `## Runs` (the run lines).
- Create outside the repo, in `<the session scratchpad>/tradegen-odds-task19/` (the scratchpad directory the
  executing session's system prompt names, written with forward slashes): `run_check.py` (Step 2, Write tool),
  `smoke.py` (Step 7, Write tool; it writes `smoke_plan.json` beside itself) and `pr_body.md` (Step 10, the Bash
  heredocs there). Every command block below that uses them starts by setting `S` to that folder; replace the
  `<the session scratchpad>` placeholder there.
- Test: no new test in the repo. The full run is the check, read by `run_check.py`, which reads files and git only.

This task changes no code. It runs the whole repo suite once with the KEYLESS prefix, writes what that run proved into
the README and the ledger, runs the CLI once against the real home with every network touchpoint refused, commits the
record, the README and the ledger, and hands the branch to the controller for the push and the pull request (G3-3).
Claude performs none of the owner acts.

Notes for the implementer (read before Step 1):
- Work from the repo root `C:/Users/whydi/OneDrive/Desktop/TRADEGEN` in Git Bash (the Bash tool), on branch
  `odds-engine`, with Tasks 1 to 18 committed on it.
- The full run takes about 15 minutes: 609 s of test time in the 2026-10-24 record, plus the odds suite's about
  3.3 minutes (CONTRACT 3.4) and the follow-up's and Tasks 2 to 4's compliance tests. The Bash tool's foreground limit
  is `timeout: 600000` (10 minutes), so Step 3 starts it with `run_in_background: true` and waits for the exit
  notification. Do not poll its output file, and start no other run until it has exited.
- The daily task `tradegen-compliance-daily` appends to the real `~/.tradegen/compliance/alerts.jsonl` at about 09:00
  to 09:10 KST (compliance execution ledger:67, a deferred minor; G3-4). Steps 3 and 7 start outside 08:30 to
  09:15 KST. To wait, use the Monitor tool (an until-loop on the time line of Step 3) or come back later in the
  session; never a foreground `sleep`, which the Bash tool blocks.
- Task 19 itself writes nothing under `~/.tradegen`. The full run's cockpit test_19 adds its run record under
  `~/.tradegen/runs`, as every full run does (`config.runs_dir()` is `state_root() / "runs"`). Steps 3 and 7 read
  only file metadata there. Never read a value from `.env`.
- Every stop report that reaches the owner (from any step, the controller's rulings included) uses Step 3's form:
  metadata only (paths, sizes, mtimes, test ids), the real-odds sentence and the disclaimer.
- Every Edit of an existing file starts with a Read of it (the Edit tool refuses a file it has not read) and applies
  the DRIFT RULE (R2-13).
- No subagent pushes. Step 10 is the controller's (G3-3); an implementer subagent stops after Step 9 and reports.

**Interfaces:**
- Consumes:
  - Tasks 1 to 18, one commit each on `odds-engine`, with these subjects in order:
    1. `feat(odds): empty odds packages, the odds suite and its guards`
    2. `feat(compliance): venue odds keys lot, min_order, fee_extras and tick_ladder`
    3. `feat(odds): sourced lots, minimums and the KRX stock tick ladder in venues.yaml`
    4. `feat(compliance): calendar_in_force, grey_rows and public signed-home fixtures`
    5. `feat(odds): plan types, injected inputs and the product, state and data checks`
    6. `feat(odds): costs, venue terms, bands, affordability and stakes`
    7. `feat(odds): two-point bootstrap, block lengths, index generator, seeds`
    8. `feat(odds): GARCH-t copy and its pilot checks`
    9. `feat(odds): path engine part 1: moves, entries, exits, ledger and outcomes`
    10. `feat(odds): path engine part 2: bands, locks, daily loss, rule dates, delisting`
    11. `feat(odds): references: ceiling, structural maximum, brackets needed, bold play`
    12. `feat(odds): report catalogue, honest number formats, flags and language guard`
    13. `feat(odds): simulate pipeline with Q24 refusals and the headline column`
    14. `feat(odds): every column, the spread, the GARCH pilots and the flags`
    15. `feat(odds): unsigned bar loader with finality, KRW series and the bars cache`
    16. `feat(odds): calendar from the owner's store, sessions, provenance copies and the comparison state`
    17. `feat(odds): the D13 replay, Kelly and the replay card`
    18. `feat(odds): the odds CLI and its end-to-end runs`
  - `tests/run_all.py` with no argument (tests/run_all.py:92-123 at `5816d3c`; Task 1 added the `odds` group). It
    runs every suite, writes `qa/acceptance_results.json` even when a test fails (rows
    `{"test": "<group>/...", "status": "PASS" | "FAIL" | "NOT_RUN", "seconds": float, "detail": str}`, plus
    `"reason"` on a NOT_RUN row), and ends with `<passed>/<total> passed, <failed> failed, <not run> not run; <path>`.
  - Task 1's `tests/odds_acceptance.py`: `MODULES` (CONTRACT 3.1, fifteen stems); `tests()` names every test
    `odds_<module>/<test>`, so the record holds `odds/odds_<module>/<test>`; it skips a module whose file is missing,
    and a module that fails to import gives one `odds_<module>/import` FAIL row.
  - Task 1's ledger, with its sections `## Base`, `## Merged line numbers ...`, `## Drift rulings`,
    `## Deferred minors` and `## Runs`. Task 1 sets the line form `- Task <n>: ...` (Task 8 adds
    `- Task 8 R2-9 margins ...`); the tasks that only say "append the tails of these runs" may have left lines
    without that prefix, which Step 9's cross-check finds.
  - Task 18's CLI `python -m core.oddsdata.run --plan <file>` (`main(argv=None, *, now=None)`; exit 0 when every plan
    is reported, 2 when any plan is refused, 4 on a crash). Its precheck (PARTIAL_CHUNK, the plan checks with the
    start on the Asia/Seoul date of the run, STATE_UNUSABLE, LIMITS_UNSET) runs before any data load (Q45). With no
    owner key, `owner.load_context` gives a sealed context whose owner log is BROKEN, head `(0, "")`, fingerprint
    `""`, `code_signed` False and an invalid approved state, so every plan is refused STATE_UNUSABLE. Each refused
    card carries `simulate.context_provenance(ctx)` (O3-16).
  - Task 15's seams `core.oddsdata.bars._kis_daily`, `_upbit_daily`, `_binance_daily` and `_yf_download`, looked up
    at call time.
  - `tests.macro_acceptance.hermetic()`: a context manager that refuses every network touchpoint (sockets included)
    and restores them on exit. It does not move any home.
  - The README readers, run again in Step 5: `odds_guards/test_suite_is_registered_in_run_all_and_readme` (Task 1),
    `compliance_guards/test_suite_is_registered_in_run_all_and_readme` (the follow-up) and
    `tests.macro_ui_components.test_readme_carries_both_disclaimers_and_no_stale_counts`.
- Produces:
  - `README.md`: the compliance count of this run, the `odds` row and the Total line of this run;
  - the committed record of a KEYLESS full run with 0 failed (`test: full run after the odds engine`, and after a fix
    wave `test: full run after the odds final review wave`);
  - the committed ledger (`docs(plan): execution ledger of the odds engine`) with two new sections,
    `## Rulings as applied` and `## Hand-off to execution (E1, E2, E3)`, and this task's run lines;
  - the pushed branch and one pull request into main (the controller, G3-3); merging stays the owner's choice;
  - the hand-off to the owner, in chat.

**Plan decisions used:**
- the order of the plans (DQ26, R2-11): the follow-up merged first; E1 starts after this plan merges;
- R2-13 (the DRIFT RULE and the ledger); Q45 (the precheck before any data load); O13 (the budgets of CONTRACT 3.4);
  O15 (the CLI);
- R2-1 and R2-2 (no open issue of this plan's own), R2-3 (the "For spec rev 3.3" list), R2-4 (the fresh-seed rerun
  handed to E2), R2-5 (the replay leg needs only the Upbit lot);
- round 3: G3-1 (counts), G3-2 (time budgets), G3-3 (pushes and one pull request), G3-4 (the daily job's window), G3-5
  (sandbox leftovers stay out), O3-14 (quote reads before owner act 4), O3-16 (provenance on the CLI's cards), O3-17
  and O3-22 (the E2 and E3 hand-off items);
- decisions this task makes:
  - T19-1 KEYLESS. The full run and the smoke start with the KEYLESS prefix of Global Constraints ("Python and test
    runs"; repeated below), as every `tests/run_all.py` command of this plan does, so cockpit test_21 cannot reach
    KIS or OpenDART. The follow-up's Task 8 accepted test_21's quote calls once per full run; this plan's header says
    "No odds test and no task step calls a network function for real", which is stricter, and wins here. Every key
    and secret `.env.example` names (`ANTHROPIC_API_KEY`, `GS_CLIENT_ID`, `GS_CLIENT_SECRET`, `FINVIZ_API_KEY`,
    `ALPACA_*` and `FXMACRODATA_API_KEY` included, which `config.skill_env()` hands to cockpit test_19's skill
    subprocess), plus the KIS account and OKX names the later plans read, is set to `'<unset>'`, which
    `config._clean` reads as unset. No test is gated on those seven names (their readers go through
    `config._clean`), so no row changes. The settings in `.env.example` (`QUANTGEN_AI_MODEL`, the `*_FICC_*` and
    `NEXTGEN_NO_DATA_GRACE` lines) are not keys and stay as they are.
  - T19-2 The smoke runs the CLI's `__main__` block in-process through `runpy`, inside `hermetic()` and with
    raising stubs on the four seams, instead of a bare `python -m core.oddsdata.run` subprocess. It is the same entry
    point `-m` runs, and the only form in which "no network" is enforced and "no seam called" can be observed.
  - T19-3 The previous full run is the record of main at the branch point (`git merge-base main HEAD`): the
    follow-up's run. A repeat after a fix wave then still compares with that run, and the drafted additions stay
    visible.
  - T19-4 The ledger gains `## Rulings as applied` (TASKS' "RULINGS ... recorded") and
    `## Hand-off to execution (E1, E2, E3)` (TASKS' hand-off notes), so both are committed with the record.
  - T19-5 The rev 3.3 fold (TASKS' last Task 19 bullet, the header's "For spec rev 3.3") is a docs change on main
    after GPT's 2026-10-30 14:40 check, outside this branch: CONTRACT 2 keeps every file under `docs/` except the
    ledger out of it, and R2-3 asks only that the departures be listed. Task 19 hands the list to that fold (Step 11)
    and edits no spec file.

**Expected counts (G3-1: from the drafts; the run's numbers win as long as nothing fails).**
- Compliance: 341 rows, 339 PASS / 2 NOT_RUN. That is the follow-up's 327 rows (325 PASS / 2 NOT_RUN, follow-up Task
  8) plus this plan's 14 new tests:
  - Task 2: 4 in compliance_tables (`test_venue_odds_keys_parse_to_exact_tuples`,
    `test_venue_odds_lookups_fall_back_and_answer_none`, `test_venue_odds_lookups_are_pure_tuple_lookups`,
    `test_check_extras_lives_in_the_parser`);
  - Task 3: 1 in compliance_tables (`test_shipped_venue_odds_values_are_the_sourced_ones`);
  - Task 4: 7 in compliance_store (29 to 36: `test_signed_home_helpers_are_the_public_fixtures`,
    `test_full_home_signs_the_odds_keywords`, `test_calendar_in_force_is_the_sha_of_the_intact_signed_copy`,
    `test_calendar_in_force_is_none_without_an_ok_owner_log`,
    `test_calendar_in_force_counts_only_approvals_stamped_by_now`,
    `test_calendar_in_force_refuses_a_naive_or_out_of_range_now`,
    `test_calendar_line_maps_the_shared_calendar_approval`) and 2 in compliance_gate (49 to 51:
    `test_grey_rows_names_the_in_force_grey_rows_of_the_leg`, `test_grey_rows_is_empty_when_nothing_can_be_looked_up`).

  327 + 4 + 1 + 7 + 2 = 341; Task 4 records `339/341` for the compliance suite.
- Odds: 287 rows, all PASS: guards 18 (Task 1), plan 25 (Task 5), costs 23 (Task 6), models 19 (Task 7; Task 17 adds
  code only), garch 17 (Task 8), simulate 18 (Task 9; Tasks 10 and 17 edit it without adding), locks 14 (Task 10),
  bold 12 (Task 11), report 41 (Task 12), pipeline 13 (Task 13; Tasks 14 and 17 replace tests, the count stays),
  columns 14 (Task 14), bars 25 (Task 15), inputs 12 (Task 16), replay 24 (Task 17), cli 12 (Task 18).

  18 + 25 + 23 + 19 + 17 + 18 + 14 + 12 + 41 + 13 + 14 + 25 + 12 + 24 + 12 = 287. Task 14 records 214 after columns,
  and Task 18 records `287/287`.
- Full run: 1477 rows, 1354 PASS / 0 FAIL / 123 NOT_RUN, against the follow-up's 1053/1176:
  - rows 1176 + 14 + 287 = 1477;
  - PASS 1053 + 14 + 287 = 1354;
  - NOT_RUN 123 = macro 121 + compliance 2 (the two REFDATA symlink tests).
- Every other group keeps its row: cockpit 47 PASS, engine 92, ui 4, quant 53, ficc 56, expansion 19, macro 419 PASS
  / 121 NOT_RUN, paper 21, grokteam 17 (728 PASS + 121 NOT_RUN; with compliance 325 + 2 that is the follow-up's 1176).
- With Developer Mode on, the two symlink tests run: compliance 341 PASS and `1356/1477 passed, 0 failed, 121 not
  run`. A review fix inside a task, or a fix task after the final review, adds its own tests on top.
- Time per module against CONTRACT 3.4 (G3-2): guards 5 s, plan 2, costs 2, models 6, garch 25, simulate 18, locks
  12, bold 12, report 12, pipeline 20, columns 30, bars 4, inputs 12, replay 20, cli 20 (about 3.3 minutes).

**Drift.** Two README lines changed after `5816d3c`, and both are anchors here:
- the follow-up's Task 8 made the compliance row's last cell `325 PASS / 2 NOT_RUN` (from `315 PASS / 2 NOT_RUN`)
  and rewrote the Total line (from `1043/1166 ... (2026-10-24, ...)` to its own run's counts and date);
- this plan's Task 1 changed the suite list at README.md:816 to `... macro, paper, grokteam, compliance or odds`. This
  task does not touch that line.

So Edits 1 and 2 quote the two cells as README.md now reads them: the same change on the current text, one ledger line
(Step 5). Two later anchors are kept for E1's Task 13: the compliance row's description, which E1's Edit R3 finds by
`D15 and D16 refusals)`, stays as it is; and E1's Edits R4 and R5 expect the odds row right above the Total line.

**The QUANTGEN overlap check.** Run it before every command that runs Python on repo code: every such command below
starts with the Git Bash form. When it finds a process, nothing after `&&` runs and the line prints nothing (or only
`exit 1`): wait, then run it again. `run_check.py` imports no repo code, but it carries the prefix anyway, so no read
of `qa/acceptance_results.json` overlaps a run that is still writing it. The stdlib-only one-liners that read git
output or a file import no repo code and need no check.
- PowerShell tool:
  `Get-CimInstance Win32_Process -Filter "Name LIKE 'python%'" | Where-Object { $_.CommandLine -match 'run_all' } | Select-Object ProcessId,Name,CommandLine`
- Git Bash prefix (the PowerShell script is in single quotes, so Bash leaves `$_` alone):
  `test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && <command>`

**The KEYLESS prefix (T19-1; the KEYLESS bullet of Global Constraints, "Python and test runs").** As in every task,
it goes right before `.venv/Scripts/python.exe`; here that is in Steps 3 and 7:

`KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>'`

- [ ] **Step 1: Check the branch, the commits and the tree (git only)**

  From the repo root in Git Bash:

```bash
git branch --show-current
git status --short
git log --format=%s --reverse main..odds-engine | .venv/Scripts/python.exe -I -c "
import sys
for stream in (sys.stdin, sys.stdout):
    stream.reconfigure(encoding='utf-8', errors='replace')
want = [
    'feat(odds): empty odds packages, the odds suite and its guards',
    'feat(compliance): venue odds keys lot, min_order, fee_extras and tick_ladder',
    'feat(odds): sourced lots, minimums and the KRX stock tick ladder in venues.yaml',
    'feat(compliance): calendar_in_force, grey_rows and public signed-home fixtures',
    'feat(odds): plan types, injected inputs and the product, state and data checks',
    'feat(odds): costs, venue terms, bands, affordability and stakes',
    'feat(odds): two-point bootstrap, block lengths, index generator, seeds',
    'feat(odds): GARCH-t copy and its pilot checks',
    'feat(odds): path engine part 1: moves, entries, exits, ledger and outcomes',
    'feat(odds): path engine part 2: bands, locks, daily loss, rule dates, delisting',
    'feat(odds): references: ceiling, structural maximum, brackets needed, bold play',
    'feat(odds): report catalogue, honest number formats, flags and language guard',
    'feat(odds): simulate pipeline with Q24 refusals and the headline column',
    'feat(odds): every column, the spread, the GARCH pilots and the flags',
    'feat(odds): unsigned bar loader with finality, KRW series and the bars cache',
    \"feat(odds): calendar from the owner's store, sessions, provenance copies and the comparison state\",
    'feat(odds): the D13 replay, Kelly and the replay card',
    'feat(odds): the odds CLI and its end-to-end runs',
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
git ls-files --eol README.md qa/acceptance_results.json
.venv/Scripts/python.exe -I -c "b = open('docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md', 'rb').read(); print(b.count(b'\r\n'), b.count(b'\n') > 0)"
git grep -n -E "NotRun|PENDING" -- 'tests/odds_*.py' 'core/odds/*.py' 'core/oddsdata/*.py'
```

  Expected:
  - `git branch --show-current` prints `odds-engine`. If it prints anything else, run `git switch odds-engine` and
    start this step again.
  - `git status --short` prints exactly `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.
  - The log check prints the eighteen subjects in task order, as `task 1 ...` to `task 18 ...`, and ends with
    `missing: none`. Other commits are allowed, each printed as `other after task <n> <subject>`:
    - a review fix of task `<n>`, made during subagent-driven execution;
    - after task 18: a full-run fix made in Step 3 (with its ledger line);
    - on a repeat of this step (Step 8), after task 18: the Step 6 record commit
      `test: full run after the odds engine` and the fix commits of the final review.

    Each must have a ledger line that names it. If one has none, write that line from the commit itself
    (`git show --stat <hash>`).
  - The two eol lines read `i/crlf  w/crlf  attr/-text` before `README.md` and before `qa/acceptance_results.json`.
  - The ledger line prints `0 True`: no CRLF in the ledger, and it is not empty.
  - `git grep` prints nothing: no odds test raises NotRun and no PENDING mark is left in the odds files (TASKS
    Task 19's first bullet). The run check of Step 4 also refuses any odds row that is not PASS.

  Stop and report when:
  - `missing:` names a subject: that task is not committed, so finish it first;
  - the tree is dirty beyond the ledger line (a leftover `--suite` run shows as ` M qa/acceptance_results.json`:
    restore it with `git checkout -- qa/acceptance_results.json` and start this step again);
  - a line reads `other after task 0`, or an `other` commit is none of the kinds above;
  - `git grep` prints a line.

- [ ] **Step 2: Save the run check and run it on the record before the run**

  Save this script with the Write tool as `<the session scratchpad>/tradegen-odds-task19/run_check.py`. It
  compares the record with the previous full run (main's record at the branch point, T19-3), checks the odds rows
  against the `test_*` functions of the fifteen modules, prints the G3-1 and G3-2 lines, and checks README.md against
  the record (every group's last cell, the Total line, the odds row between the compliance row and the Total row,
  CRLF everywhere).

```python
"""Odds plan Task 19 run check: the full-run record against the previous full run (the record of main at the branch
point, the follow-up's run), and README.md against the record. Reads files and git only, imports no repo code; run it
from the repo root."""
from __future__ import annotations

import ast
import collections
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RECORD = Path("qa/acceptance_results.json")
LEDGER = "docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md"
MODULES = ("odds_guards", "odds_plan", "odds_costs", "odds_models", "odds_garch", "odds_simulate", "odds_locks",
           "odds_bold", "odds_report", "odds_pipeline", "odds_columns", "odds_bars", "odds_inputs", "odds_replay",
           "odds_cli")                                                            # CONTRACT 3.1
DRAFTS = dict(zip(MODULES, (18, 25, 23, 19, 17, 18, 14, 12, 41, 13, 14, 25, 12, 24, 12)))  # Tasks 1, 5-18: 287
TARGETS = dict(zip(MODULES, (5, 2, 2, 6, 25, 18, 12, 12, 12, 20, 30, 4, 12, 20, 20)))      # CONTRACT 3.4, seconds
ADDED = {f"compliance/compliance_{m}/{t}" for m, names in (
    ("tables", ("test_venue_odds_keys_parse_to_exact_tuples", "test_venue_odds_lookups_fall_back_and_answer_none",
                "test_venue_odds_lookups_are_pure_tuple_lookups", "test_check_extras_lives_in_the_parser",
                "test_shipped_venue_odds_values_are_the_sourced_ones")),              # Task 2 (4), Task 3 (1)
    ("store", ("test_signed_home_helpers_are_the_public_fixtures", "test_full_home_signs_the_odds_keywords",
               "test_calendar_in_force_is_the_sha_of_the_intact_signed_copy",
               "test_calendar_in_force_is_none_without_an_ok_owner_log",
               "test_calendar_in_force_counts_only_approvals_stamped_by_now",
               "test_calendar_in_force_refuses_a_naive_or_out_of_range_now",
               "test_calendar_line_maps_the_shared_calendar_approval")),            # Task 4 (7)
    ("gate", ("test_grey_rows_names_the_in_force_grey_rows_of_the_leg",
              "test_grey_rows_is_empty_when_nothing_can_be_looked_up"))) for t in names}  # Task 4 (2)
ODDS_ROW = ("| odds | `tests/odds_acceptance.py` over `tests/odds_*.py` | The odds engine, offline with every price "
            "feed faked: the single-leg plan whitelist and the named refusals in their fixed order, the cost ledger "
            "with the per-fill tick floor (the KRX stock sell tax inside it), floor-protected and stop-based stakes "
            "with lot rounding, the no-edge two-point bootstrap and GARCH-t with their pilot checks and corruption "
            "tests, the path engine (open and close checks, limit-down locks, the daily loss, rule dates, delisting "
            "stress, the OKX cap per entry), the ceiling, the KRX structural maximum and exact bold play, the "
            "HIDDEN_EDGE and CEILING_BREACH bug checks, the S_C3 replay against its pinned card with lower-bound "
            "Kelly, the report's sentence catalogue, outward number formats and language guard, the unsigned bar "
            "loader and its checked cache, the signed calendar, one seed per comparison, the CLI, and the odds guards "
            "(the import allowlist, no clock and no file I/O in the signed core) |")
KEYISH = re.compile(r"(?i)key|credential|token|\.env")
NEW = json.loads(RECORD.read_text(encoding="utf-8"))
BASE = subprocess.run(["git", "merge-base", "main", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
OLD = json.loads(subprocess.run(["git", "show", f"{BASE}:qa/acceptance_results.json"],
                                capture_output=True, check=True).stdout.decode("utf-8"))
RUN_DATE = datetime.date.fromtimestamp(RECORD.stat().st_mtime).isoformat()
record: list[str] = []          # problems that stop the task
readme: list[str] = []          # README.md lines that do not match the record
notes: list[str] = []           # G3-1 and G3-2 lines for the ledger
rulings: list[str] = []         # G3-2: a module over twice its target is the controller's ruling


def totals(rows: list[dict]) -> str:
    n = collections.Counter(r["status"] for r in rows)
    return f"{n['PASS']}/{len(rows)} passed, {n['FAIL']} failed, {n['NOT_RUN']} not run"


def cell(group: str) -> str:
    n = collections.Counter(r["status"] for r in NEW if r["test"].split("/", 1)[0] == group)
    return f"{n['PASS']} PASS / {n['NOT_RUN']} NOT_RUN" if n["NOT_RUN"] else f"{n['PASS']} PASS"


def safe(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9 ._:/,()=+-]", " ", text)[:100].strip()


old = {r["test"]: r for r in OLD}
new = {r["test"]: r for r in NEW}
record += [f"FAIL row {r['test']}" for r in NEW if r["status"] == "FAIL"]
record += [f"a row of the previous run is missing: {t}" for t in old if t not in new]
added = {t for t in new if t not in old and not t.startswith("odds/")}
changes = []
for t in new:
    if t in old and new[t]["status"] != old[t]["status"]:
        before, after, why = old[t]["status"], new[t]["status"], safe(new[t].get("reason", ""))
        changes.append(f"  - {t}: {before} -> {after}" + (f", {why}" if why else ""))
        if after == "NOT_RUN" and not KEYISH.search(why):
            record.append(f"{t} turned NOT_RUN for a reason that names no key: stop and rule")
tree = ast.parse(Path("tests/odds_acceptance.py").read_bytes())
listed = next((ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(getattr(x, "id", "") == "MODULES" for x in n.targets)), None)
if listed != MODULES:
    record.append(f"tests/odds_acceptance.MODULES is not CONTRACT 3.1's list: {listed}")
defined = set()
for m in MODULES:
    path = Path("tests") / f"{m}.py"
    if not path.is_file():
        record.append(f"tests/{m}.py is missing, so the suite skips it")
        continue
    defined |= {f"odds/{m}/{n}" for n in re.findall(r"^def (test_\w+)\(", path.read_text(encoding="utf-8"), re.M)}
odds = [r for r in NEW if r["test"].startswith("odds/")]
if not odds:
    record.append("the record holds no odds rows")
elif defined != {r["test"] for r in odds}:
    record.append(f"odds rows differ from the defined tests: {sorted(defined ^ {r['test'] for r in odds})[:5]}")
record += [f"odds row not PASS: {r['test']} {r['status']} {safe(r.get('reason', ''))}" for r in odds
           if r["status"] != "PASS"]
seconds = round(sum(r["seconds"] for r in odds), 1)
over = []
for m in MODULES if odds else ():
    rows = [r for r in odds if r["test"].startswith(f"odds/{m}/")]
    spent = round(sum(r["seconds"] for r in rows), 1)
    if len(rows) != DRAFTS[m]:
        notes.append(f"  - G3-1: {m} has {len(rows)} tests where the drafts expect {DRAFTS[m]}")
    if spent > TARGETS[m]:
        over.append(f"{m} {spent} s > {TARGETS[m]} s")
        notes.append(f"  - G3-2: {m} took {spent} s in the full run, over its {TARGETS[m]} s target")
    if spent > 2 * TARGETS[m]:
        rulings.append(f"RULING: {m} took {spent} s, over twice its {TARGETS[m]} s target (G3-2)")
if odds and added != ADDED:
    notes.append(f"  - G3-1: rows added outside odds differ from the drafts (Tasks 2 to 4): "
                 f"extra {sorted(added - ADDED)}, absent {sorted(ADDED - added)}")
groups = list(dict.fromkeys(r["test"].split("/", 1)[0] for r in NEW))
raw = Path("README.md").read_bytes()
if raw.count(b"\n") != raw.count(b"\r\n"):
    readme.append("a line of README.md does not end in CRLF")
lines = raw.decode("utf-8").split("\r\n")
for group in groups:
    found = [i for i, line in enumerate(lines) if line.startswith(f"| {group} | ")]
    if len(found) != 1 or lines[found[0]].rsplit("|", 2)[-2].strip() != cell(group):
        readme.append(f"the {group} row is not one row ending | {cell(group)} |")
total = re.compile(r"\| \*\*Total\*\* \| `tests/run_all\.py` \| \| " + re.escape(totals(NEW))
                   + r" \((\d{4}-\d{2}-\d{2}), TRADEGEN `\.venv`\) \|")
at = [i for i, line in enumerate(lines) if total.fullmatch(line)]
if len(at) != 1 or (NEW != OLD and total.fullmatch(lines[at[0]]).group(1) != RUN_DATE):
    readme.append(f"the Total row is not | **Total** | ... | {totals(NEW)} ({RUN_DATE}, TRADEGEN .venv) |")
if "odds" in groups:
    row = [i for i, line in enumerate(lines) if line == f"{ODDS_ROW} {cell('odds')} |"]
    comp = [i for i, line in enumerate(lines) if line.startswith("| compliance | ")]
    if not (row and comp and at and comp[0] + 1 == row[0] == at[0] - 1):
        readme.append("the odds row of Task 19 is not between the compliance row and the Total row")
comp_delta = sum(t.startswith("compliance/") for t in new) - sum(t.startswith("compliance/") for t in old)
line = (f"- Task 19: full run (KEYLESS) {totals(NEW)} on {RUN_DATE}; previous full run {totals(OLD)}; "
        f"odds {cell('odds')} in {seconds} s; compliance {cell('compliance')} ({comp_delta:+d} rows); "
        f"status changes {len(changes)}")
print(f"previous full run (main at {BASE[:7]}):", totals(OLD))
print("this run:", totals(NEW), "on", RUN_DATE)
verdict = ("as the drafts expect" if added == ADDED else "(see G3-1)") if odds else ""
print(f"rows added outside odds: {len(added)} {verdict}".rstrip())
print("status changes:", len(changes))
if changes:
    print(*changes, sep="\n")
print("odds:", len(odds), "rows in", seconds, "s; modules over their CONTRACT 3.4 target:", over or "none")
print("README cells:", "; ".join(f"{g}={cell(g)}" for g in groups))
print(f"README Total: {totals(NEW)} ({RUN_DATE}, TRADEGEN `.venv`)")
for extra in (*notes, *rulings):
    print(extra.strip())
if not record:                  # the Runs lines exist only for a record that stands
    print("APPEND: printf '%s\\n' " + " ".join(f'"{x}"' for x in [line, *changes, *notes]) + f" >> {LEDGER}")
print("record: OK" if not record else "record: FAIL: " + "; ".join(record))
print("README: matches the record" if not readme else "README: FAIL: " + "; ".join(readme))
sys.exit(1 if record or readme else 0)
```

  Run it now, before the full run (on a repeat after a fix wave, skip this run: the script is already saved):

```bash
S='<the session scratchpad>/tradegen-odds-task19'; test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I "$S/run_check.py"; echo "exit $?"
```

  Expected, with the record still main's (the `<...>` values are what the script prints: the short hash of the merged
  main and the date of the record file):

```text
previous full run (main at <short hash of the merged main>): 1053/1176 passed, 0 failed, 123 not run
this run: 1053/1176 passed, 0 failed, 123 not run on <date of the record file>
rows added outside odds: 0
status changes: 0
odds: 0 rows in 0 s; modules over their CONTRACT 3.4 target: none
README cells: cockpit=47 PASS; engine=92 PASS; ui=4 PASS; quant=53 PASS; ficc=56 PASS; expansion=19 PASS; macro=419 PASS / 121 NOT_RUN; paper=21 PASS; grokteam=17 PASS; compliance=325 PASS / 2 NOT_RUN
README Total: 1053/1176 passed, 0 failed, 123 not run (<date of the record file>, TRADEGEN `.venv`)
record: FAIL: the record holds no odds rows
README: matches the record
exit 1
```

  The failure is the point: no full run has written odds rows yet. Two things must hold:
  - the `previous full run` totals equal the README Total line as the follow-up left it;
  - the last line is `README: matches the record`.

  If either fails, the committed record and the README disagree before this task: stop and rule. If the follow-up's
  fix wave changed its counts, its own numbers are on these lines instead, and the expected totals of Step 3 move by
  the same amount.

- [ ] **Step 3: The full KEYLESS run, in the background**

  Before the run, four read-only checks (no repo code):

```bash
.venv/Scripts/python.exe -I -c "import datetime, zoneinfo; t = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Seoul')).time(); print(t.strftime('%H:%M KST'), 'wait until 09:15 KST' if datetime.time(8, 30) <= t < datetime.time(9, 15) else 'ok to start')"
test -z "${TRADEGEN_HOME:-}" && echo "TRADEGEN_HOME unset" || echo "stop: TRADEGEN_HOME is set"
stat -c '%n %s %Y' ~/.tradegen/kis_token.json 2>/dev/null || echo "no kis_token.json"
test -e ~/.tradegen/odds && echo "a real odds home exists" || echo "no real odds home"
```

  Expected:
  - `ok to start`. On `wait until 09:15 KST`, wait with the Monitor tool until the line prints `ok to start`, or come
    back to this step later in the session.
  - `TRADEGEN_HOME unset`. On `stop: TRADEGEN_HOME is set`, stop and report: the real-home checks here and in Step 7
    assume the default home `~/.tradegen`, and only the owner can say which home is real. (A `TRADEGEN_HOME` line in
    `.env` is caught by Step 7's smoke, which compares the state root after `.env` loads.)
  - The token line (its path, size and mtime), or `no kis_token.json`. Keep it for after the run.
  - `no real odds home`: no task ran the CLI against the real home. `a real odds home exists` means something wrote
    odds state there: stop and report it.

  Then the full run, with the Bash tool's `run_in_background: true`. The overlap check gates the whole group, so a
  running `run_all` makes the command print nothing and exit 1:

```bash
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && { KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe tests/run_all.py; echo "exit $?"; date +%F; }
```

  Expected, at the end of its output when the notification arrives:

```text
1354/1477 passed, 0 failed, 123 not run; C:\Users\whydi\OneDrive\Desktop\TRADEGEN\qa\acceptance_results.json
exit 0
<the date of the run, as date +%F prints it>
```

  A run with 0 failed and other counts still passes (G3-1); Step 4 names the difference. If the background command
  ends with exit code 1 and no output, the overlap check found another `run_all.py`: wait and start it again.

  If any test fails, or the run is cut short, stop. The runner writes the record even then
  (tests/run_all.py:118), so restore it first:

```bash
git checkout -- qa/acceptance_results.json
```

  Then find the task whose change broke the test and fix it there with its own failing test, as a fix commit; never
  edit a guard to make it pass. Stage only the files the fix names (never `qa/acceptance_results.json` and never the
  ledger), check that `git diff --cached --stat` equals `git diff --cached --stat --ignore-cr-at-eol`, end the message
  with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the model that writes the commit), write one ledger
  line, and start Step 3 again. The likely suspects:
  - **The scans over `core/`.** cockpit test_08 and test_09, T-RO-01 and T-CTX-01's isolation report read the files
    under `core/`, `core/odds` and `core/oddsdata` included (raw text: docstrings, comments and the sentence
    catalogue count).
  - **The closure.** The D14 code hash covers `core/odds/*.py` (`owner.code_files`), so the closure tests of
    odds_guards and of the compliance suite read every `core/odds` file.
  - **The suite lists.** The registration tests read the `one suite:` lists at tests/run_all.py:113 and
    README.md:816 (Task 1).
  - **An import.** An `odds/odds_<module>/import` FAIL row means that test module no longer imports; its detail
    names the error.
  - **Not a task bug (G3-4).** A FAIL whose detail (the runner writes it as `AssertionError: <message>`) contains
    `the test touched the real ~/.tradegen/odds or compliance: [(1, 'alerts.jsonl', ...` (an odds row) or
    `the test touched the real ~/.tradegen/compliance: [('alerts.jsonl', ...` (a compliance row), in a run that
    spanned 09:00 to 09:10 KST, is the daily task. Restore the record, append one ledger line, and run again outside
    that time:

```bash
printf '%s\n' "- Task 19: G3-4: the full run of $(date +%F) spanned 09:00 KST and the daily alert job appended to ~/.tradegen/compliance/alerts.jsonl; record restored, run again outside 08:30 to 09:15 KST" >> docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
```

    Any other real-home FAIL is a bug: stop and report.

  After the run, the same two real-home checks, then the tree:

```bash
stat -c '%n %s %Y' ~/.tradegen/kis_token.json 2>/dev/null || echo "no kis_token.json"
test -e ~/.tradegen/odds && echo "a real odds home exists" || echo "no real odds home"
git status --short
git ls-files --eol qa/acceptance_results.json
```

  Expected:
  - the token line exactly as before the run: KEYLESS kept cockpit test_21's KIS client from asking for a token;
  - `no real odds home`;
  - ` M qa/acceptance_results.json` and `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`;
  - `i/crlf  w/crlf  attr/-text` before the path: the runner writes the file in text mode, so it stays CRLF.

  A changed token line means a KIS token was issued during the run: stop and report it. Any other changed or new
  file means a test wrote into the repo: stop and report it. Report a stop to the owner in this form, metadata only
  (paths, sizes and mtimes; never a file's content, a value or a key):

```text
Task 19 stopped before its commit. What changed: <the path with its size and mtime before and after the run, or the
FAIL row's test id and the paths its detail names>. The odds engine places no order, and Task 19 waits here until
you rule. The real odds are unchanged: no plan without a real edge can beat 1 in 1,000 for KRW 42,000 to
KRW 42,000,000 (1 in 1,999 when a floor at half the stake truly holds), and the research puts the practical chance of
1,000x in a month at 0.01% or less. This is not legal or investment advice; I am not a licensed advisor.
```

- [ ] **Step 4: Run the check on the new record**

```bash
S='<the session scratchpad>/tradegen-odds-task19'; test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I "$S/run_check.py"; echo "exit $?"
```

  Expected (the `<...>` values are printed by the script: the merged main's short hash, the run's date, the odds
  suite's summed seconds):

```text
previous full run (main at <short hash of the merged main>): 1053/1176 passed, 0 failed, 123 not run
this run: 1354/1477 passed, 0 failed, 123 not run on <the run's date>
rows added outside odds: 14 as the drafts expect
status changes: 0
odds: 287 rows in <seconds> s; modules over their CONTRACT 3.4 target: none
README cells: cockpit=47 PASS; engine=92 PASS; ui=4 PASS; quant=53 PASS; ficc=56 PASS; expansion=19 PASS; macro=419 PASS / 121 NOT_RUN; paper=21 PASS; grokteam=17 PASS; compliance=339 PASS / 2 NOT_RUN; odds=287 PASS
README Total: 1354/1477 passed, 0 failed, 123 not run (<the run's date>, TRADEGEN `.venv`)
APPEND: printf '%s\n' "- Task 19: full run (KEYLESS) 1354/1477 passed, 0 failed, 123 not run on <the run's date>; previous full run 1053/1176 passed, 0 failed, 123 not run; odds 287 PASS in <seconds> s; compliance 339 PASS / 2 NOT_RUN (+14 rows); status changes 0" >> docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
record: OK
README: FAIL: the compliance row is not one row ending | 339 PASS / 2 NOT_RUN |; the odds row is not one row ending | 287 PASS |; the Total row is not | **Total** | ... | 1354/1477 passed, 0 failed, 123 not run (<the run's date>, TRADEGEN .venv) |; the odds row of Task 19 is not between the compliance row and the Total row
exit 1
```

  `record: OK` is what this step needs; the README failure is Step 5's work. The date on the `this run:` line must be
  the date Step 3 printed. Keep the whole output for Step 5. Where the output differs:
  - **`record: FAIL: ...`.** Stop. Each problem names its cause:
    - a FAIL row or a missing previous row: Step 3's failure rules apply (restore the record first);
    - `tests/odds_acceptance.MODULES is not CONTRACT 3.1's list` or `tests/<module>.py is missing`: a task changed the
      module list: stop and rule;
    - `odds rows differ from the defined tests`: a `test_*` function the suite did not run, or a row with no function
      (for example an `import` row): stop and report;
    - `<id> turned NOT_RUN for a reason that names no key`: stop and rule.
  - **`status changes: <n>` above 0.** Each line reads `  - <test>: <old> -> <new>, <reason>`. A test that turned
    NOT_RUN because the KEYLESS prefix switched its key off is not a failure: its line goes into the ledger with the
    run's line (the `APPEND:` command carries it). `NOT_RUN -> PASS` (for example after Developer Mode was turned on)
    is listed the same way.
  - **G3-1 lines** (`G3-1: odds_<module> has <n> tests where the drafts expect <d>`, or
    `G3-1: rows added outside odds differ from the drafts ...`). The run passes. Each difference must already be
    explained by a ledger line of the task that wrote that module or test (find it with
    `grep -n "^- Task" docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`). The `APPEND:` command
    carries the G3-1 lines into the Runs section. A difference that no ledger line explains: stop and rule.
  - **G3-2 lines** (`G3-2: odds_<module> took <s> s in the full run, over its <t> s target`). The run passes, and
    the `APPEND:` command records each line with its measured time. No test is changed, shortened or dropped to fit.
  - **`RULING:` lines** (a module over twice its target). Stop and send the controller the RULING lines as printed.
    The controller may split the module (a fix task, then Step 3 again) or accept the time. When it accepts, append
    `- Task 19: <the RULING line as printed>; accepted by the controller, no test changed` to the ledger with
    `printf '%s\n' "<that line>" >> docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` after Step 5's
    `APPEND:` command, and go on.

- [ ] **Step 5: Update README.md (CRLF, Edit tool) and append the run to the ledger**

  Read `README.md` with the Read tool first (DRIFT RULE). Each old text lies inside one line and stops before the
  line end, so every CRLF ending stays as it is. The counts in the new texts come from Step 4's output.

  **Edit 1.** Anchor: the last cell of the `| compliance |` row (hint README.md:839). At `5816d3c` the old text is
  `final-target checks) | 315 PASS / 2 NOT_RUN |`. Expected drift: the follow-up's Task 8 made the cell
  `325 PASS / 2 NOT_RUN`, so the old text is (exact, it occurs once):

```text
final-target checks) | 325 PASS / 2 NOT_RUN |
```

  If README.md reads another count there (a fix wave of the follow-up), the old text is `final-target checks) | `,
  the cell as README.md reads it, and ` |`. New text, with the value after `compliance=` on Step 4's
  `README cells:` line (expected `339 PASS / 2 NOT_RUN`):

```text
final-target checks) | 339 PASS / 2 NOT_RUN |
```

  **Edit 2.** Anchor: the `| **Total** |` row, the last row of the suite table (hint README.md:840). At `5816d3c` the
  old text is
  ``| **Total** | `tests/run_all.py` | | 1043/1166 passed, 0 failed, 123 not run (2026-10-24, TRADEGEN `.venv`) |``.
  Expected drift: the follow-up's Task 8 rewrote its counts and date, so the old text is the whole Total line exactly
  as README.md now reads it, expected:

```text
| **Total** | `tests/run_all.py` | | 1053/1176 passed, 0 failed, 123 not run (<the date the follow-up's run printed, as README.md reads it>, TRADEGEN `.venv`) |
```

  The new text is two lines: the `odds` row, then the Total line of this run. The odds row's last cell is the value
  after `odds=` on Step 4's `README cells:` line (expected `287 PASS`); the Total line is
  ``| **Total** | `tests/run_all.py` | | `` followed by the text after `README Total: ` on Step 4's output and ` |`:

```text
| odds | `tests/odds_acceptance.py` over `tests/odds_*.py` | The odds engine, offline with every price feed faked: the single-leg plan whitelist and the named refusals in their fixed order, the cost ledger with the per-fill tick floor (the KRX stock sell tax inside it), floor-protected and stop-based stakes with lot rounding, the no-edge two-point bootstrap and GARCH-t with their pilot checks and corruption tests, the path engine (open and close checks, limit-down locks, the daily loss, rule dates, delisting stress, the OKX cap per entry), the ceiling, the KRX structural maximum and exact bold play, the HIDDEN_EDGE and CEILING_BREACH bug checks, the S_C3 replay against its pinned card with lower-bound Kelly, the report's sentence catalogue, outward number formats and language guard, the unsigned bar loader and its checked cache, the signed calendar, one seed per comparison, the CLI, and the odds guards (the import allowlist, no clock and no file I/O in the signed core) | 287 PASS |
| **Total** | `tests/run_all.py` | | 1354/1477 passed, 0 failed, 123 not run (<the run's date>, TRADEGEN `.venv`) |
```

  The odds row's text up to its last cell must stay exactly as written: `run_check.py` compares it in full (its
  `ODDS_ROW`), and E1's Task 13 inserts its execution row right after it.

  **Contingency (the run wins).** Only for a group other than compliance and odds whose `README cells:` value differs
  from the last cell of its row. The anchor is that row, named by its first cell. The old text is its last cell,
  exact, and each one occurs once in README.md:
  - the `| cockpit |` row (README.md:830): `| 47 PASS |`
  - the `| engine |` row (README.md:831): `| 92 PASS |`
  - the `| ui |` row (README.md:832): `| 4 PASS |`
  - the `| quant |` row (README.md:833): `| 53 PASS |`
  - the `| ficc |` row (README.md:834): `| 56 PASS |`
  - the `| expansion |` row (README.md:835): `| 19 PASS |`
  - the `| macro |` row (README.md:836): `| 419 PASS / 121 NOT_RUN |`
  - the `| paper |` row (README.md:837): `| 21 PASS |`
  - the `| grokteam |` row (README.md:838): `| 17 PASS |`

  The new text is that group's value in the same form: `| N PASS |`, or `| N PASS / M NOT_RUN |`. Each such row gets
  one ledger line in Edit L0 below.

  On a repeat after a fix wave (Step 8): Edit 1's old text is the compliance cell exactly as the first pass left it,
  re-read from README.md; Edit 2's old text is the Total line as the first pass left it, and its new text is only the
  repeat's Total line (the odds row is already there). If the odds count changed, one more Edit: old text
  `no file I/O in the signed core) | 287 PASS |`, new text `no file I/O in the signed core) | ` followed by the value
  after `odds=` and ` |`.

  Then the endings and the diff:

```bash
.venv/Scripts/python.exe -I -c "b = open('README.md', 'rb').read(); print(b.count(b'\n'), b.count(b'\r\n'))"
git ls-files --eol README.md
git diff --stat README.md
git diff --stat --ignore-cr-at-eol README.md
git diff --numstat README.md
```

  Expected:
  - `892 892`: one line more than the follow-up left (891), and every line still ends in CRLF;
  - `i/crlf  w/crlf  attr/-text` before `README.md`;
  - two identical stat outputs, ` README.md | 5 +++--` and `1 file changed, 3 insertions(+), 2 deletions(-)`;
  - the numstat `3	2	README.md`, plus one and one for each contingency row.

  Unequal numbers mean an edit wrote a bare LF: run `git checkout -- README.md`, then stop and rule. On a repeat,
  README.md keeps its 892 lines (`892 892`), and the diff is against the Step 6 commit: one added and one deleted
  line per changed row.

  **Edit L0 (the ledger, the drift ruling; first pass only).** Read the ledger with the Read tool first. Anchor: the
  `## Deferred minors` heading (it occurs once; ruling lines that earlier tasks added above it stay as they are). Old
  text:

```text
## Deferred minors
```

  New text:

```text
- Task 19: README.md compliance row count and Total line (R2-13): the follow-up's Task 8 had rewritten both; each
  now holds this run's counts, the same change on the current text.

## Deferred minors
```

  For each contingency row, add one more line right after that entry, in the same new text, filled from Step 4's
  `README cells:` line, the old cell and the ledger:
  `- Task 19: README.md <group> row: the run counts <its README cells value> where the row said <the old cell>; see <the "- Task <n>" line that explains it>`.
  When the count moved only because KEYLESS turned a test NOT_RUN for a key-named reason (Step 4), the explanation is
  this run's own status-change line: end the line `; see the Task 19 status-change line for <test>`. A group whose
  count moved and that neither a task's ledger line nor this run's status-change lines explain: stop and rule.

  **Edit L1 (the ledger, the run).** Run the command Step 4 printed after `APPEND: `, exactly as printed (everything
  after that prefix, from `printf` to the ledger's path). It appends this run's `- Task 19: full run (KEYLESS) ...`
  line as the last line of the ledger, then each status-change, G3-1 and G3-2 line in the order printed. The file is
  LF, and an appended LF line keeps it so. The script builds every line from counts, test ids and reasons stripped of
  quotes, backticks, `$` and backslashes, so the double quotes hold them safely. Then:

```bash
tail -n 3 docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
```

  Expected: `tail` ends with the line or lines just written.

  **The check, and the README readers.**

```bash
S='<the session scratchpad>/tradegen-odds-task19'; test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -I "$S/run_check.py"; echo "exit $?"
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.odds_acceptance odds_guards/test_suite_is_registered_in_run_all_and_readme; echo "exit $?"
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -m tests.compliance_acceptance compliance_guards/test_suite_is_registered_in_run_all_and_readme; echo "exit $?"
test -z "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')" && .venv/Scripts/python.exe -c "from tests.macro_ui_components import test_readme_carries_both_disclaimers_and_no_stale_counts as t; t(); print('README test ok')"; echo "exit $?"
```

  Expected:
  - the check prints Step 4's lines again (the `APPEND:` line included: do not run it a second time) and ends
    `record: OK`, `README: matches the record` and `exit 0`;
  - the next two each end `1/1 passed, 0 failed, 0 not run` and `exit 0` (they are module runs, so no results file
    is written);
  - the last prints `README test ok` and `exit 0`.

  A README failure names the line that does not match: fix the edit, never the test. If the odds reader reports
  `0/0`, Task 1 named it differently: find it with `grep -n "def test_suite_is_registered" tests/odds_*.py`.

- [ ] **Step 6: Commit the full-run record and the README**

```bash
git status --short
git add README.md qa/acceptance_results.json
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
git diff --cached --numstat -- README.md
```

  Expected: `git status --short` lists exactly ` M README.md`, ` M qa/acceptance_results.json` and
  `?? docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`; the two stat outputs are identical; the
  numstat is `3	2	README.md` (plus one and one per contingency row). The ledger stays out of this commit. Then,
  with the counts of Step 4's `this run:` and `README cells:` lines in the body (expected as written):

```bash
git commit -m "test: full run after the odds engine" -m "Task 19: full run 1354/1477 passed, 0 failed, 123 not run (odds 287 PASS; compliance 339 PASS / 2 NOT_RUN); README compliance, odds and Total rows." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

  Expected: the new commit on `odds-engine`, and `git status --short` prints only the ledger's `??` line. Replace the
  trailer's model name with the model that writes the commit.

- [ ] **Step 7: The read-only real-home smoke (Q45; no network)**

  This step never writes under `~/.tradegen` and calls no network. With no owner key, the CLI's precheck refuses
  every plan STATE_UNUSABLE before any data load (Q45). With a key, `load_context` would write a snapshot under
  `~/.tradegen/compliance/snapshots`, so the step skips. It stops when `TRADEGEN_HOME` is set in the shell, or when the
  state root after `.env` loads is not `~/.tradegen` (the CLI would read another home than the one listed, and an
  unchanged listing would prove nothing). It waits while a `run_all.py` runs, while the clock is inside 08:30 to 09:15
  KST (G3-4), and while it is inside 23:55 to 00:05 KST (the plan's start is today's Seoul date, and a date that
  turns between the plan file and the CLI's clock read refuses the start before STATE_UNUSABLE).

  Save this script with the Write tool as `<the session scratchpad>/tradegen-odds-task19/smoke.py`. It writes Task
  18's default plan (a one-day Upbit BTC compounding plan, KRW 42,000 to 46,200, starting on today's Asia/Seoul date)
  to `smoke_plan.json` beside itself, lists every folder and file under `~/.tradegen` (the pattern of
  `tests/compliance_acceptance._real_listing`) before importing any repo code, checks the state root, replaces the
  four seams with stubs that record a call and raise, runs the CLI's `__main__` block through `runpy` inside
  `hermetic()` (T19-2), restores everything, and lists `~/.tradegen` again. The STATE_UNUSABLE line it looks for is
  built from Task 12's catalogue, as Task 18's own test reads it, so a reworded sentence (DRIFT RULE) still matches.

```python
"""Odds plan Task 19: the read-only real-home smoke (Q45). Runs `python -m core.oddsdata.run --plan <plan>` in this
process through runpy, the way `-m` runs it, with every network touchpoint refused (the macro suite's hermetic
guard) and the four bars seams replaced by stubs that record a call and raise; lists every folder and file under
~/.tradegen before and after. It writes only its own plan file, next to this script. Run it from the repo root."""
from __future__ import annotations

import contextlib
import datetime
import io
import json
import os
import runpy
import sys
import warnings
import zoneinfo
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = Path.cwd()
if not (REPO / "core" / "oddsdata" / "run.py").is_file():
    raise SystemExit("STOP: run this from the repo root")
sys.path.insert(0, str(REPO))
HOME = Path.home() / ".tradegen"
PLAN = Path(__file__).resolve().parent / "smoke_plan.json"
LEDGER = "docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md"
SEAMS = ("_kis_daily", "_upbit_daily", "_binance_daily", "_yf_download")


def listing() -> tuple:
    """(relative path, size, mtime_ns) of every folder and file under ~/.tradegen, as
    tests/compliance_acceptance._real_listing lists them: the home itself is `.`, a folder `<path>/` with 0, 0."""
    rows = [(".", 0, 0)] if HOME.exists() else []
    for dirpath, dirs, files in os.walk(HOME):
        here = Path(dirpath)
        rows += [((here / n).relative_to(HOME).as_posix() + "/", 0, 0) for n in dirs]
        for name in files:
            st = (here / name).stat()
            rows.append(((here / name).relative_to(HOME).as_posix(), st.st_size, st.st_mtime_ns))
    return tuple(sorted(rows))


today = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Seoul")).date().isoformat()   # Q25: the plan starts today
leg = {"venue": "upbit", "symbol": "BTC", "model": "bootstrap", "bracket": None, "sizing": "floor_safe",
       "edge_source": "none", "assumed_p": None}
PLAN.write_text(json.dumps({"schema": "tradegen.odds_plan/1", "plans": [{
    "name": "smoke", "track": "compounding", "stake_krw": 42_000, "target_krw": 46_200, "fx_krw_per_usd": 1_400.0,
    "start": today, "horizon_days": 1, "leg": leg, "fraction": {"kind": "fixed", "value": 1.0}}]}), encoding="utf-8")
before = listing()                                       # before any repo module is imported

import config                                            # noqa: E402  (runs load_dotenv, as hermetic() does)
from core.odds import report                             # noqa: E402
from core.oddsdata import bars                           # noqa: E402
from tests.macro_acceptance import hermetic              # noqa: E402

if config.state_root() != HOME:                          # a TRADEGEN_HOME line in .env moves the CLI's home
    raise SystemExit("STOP: the state root is not ~/.tradegen")
WHY = report.say("refused.head", why=report.say("why.STATE_UNUSABLE"))   # Task 12's catalogue, as Task 18's test
calls: list[str] = []


def stub(name: str):
    def seam(*_a, **_k):
        calls.append(name)
        raise RuntimeError(f"bars.{name} was called by the smoke")
    return seam


saved, argv = {n: getattr(bars, n) for n in SEAMS}, sys.argv
out, err, code, caught = io.StringIO(), io.StringIO(), None, []
try:
    for n in SEAMS:
        setattr(bars, n, stub(n))
    sys.argv = ["core.oddsdata.run", "--plan", str(PLAN)]
    with (hermetic(), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err),
          warnings.catch_warnings(record=True) as caught):
        warnings.simplefilter("always")          # recorded, never printed, as in tests/odds_cli.py
        try:
            runpy.run_module("core.oddsdata.run", run_name="__main__", alter_sys=True)
        except SystemExit as exc:
            code = exc.code
finally:
    sys.argv = argv
    for n, fn in saved.items():
        setattr(bars, n, fn)
after = listing()
changed = sorted({row[0] for row in set(before) ^ set(after)})     # relative paths only (metadata)
problems = [f"exit {code}, not 2"] if code != 2 else []
problems += [f"stderr {err.getvalue()[:300]!r}"] if err.getvalue() else []
problems += [] if WHY in out.getvalue().splitlines() else ["no STATE_UNUSABLE card"]
problems += [f"seams called {calls}"] if calls else []
problems += [f"~/.tradegen changed: {len(changed)} path(s), listed above"] if changed else []
print(out.getvalue(), end="")
print("exit", code)
print("seams called:", calls)
print("warnings recorded:", len(caught))
if changed:
    print("~/.tradegen CHANGED (paths under it; a folder ends in /):", *changed, sep="\n  ")
else:
    print(f"~/.tradegen unchanged: {len(after)} entries")
if not problems:
    line = (f"- Task 19: real-home smoke (Q45; KEYLESS, hermetic, seams stubbed) on {today}: exit 2 STATE_UNUSABLE, "
            f"no seam called, ~/.tradegen unchanged ({len(after)} entries)")
    print("APPEND: printf '%s\\n' " + f'"{line}"' + f" >> {LEDGER}")
print("OK" if not problems else "FAIL: " + "; ".join(problems))
sys.exit(1 if problems else 0)
```

  Run it (KEYLESS; the guards print one line and run nothing when they fire):

```bash
S='<the session scratchpad>/tradegen-odds-task19'
if test -e core/compliance/owner_pubkey.pem; then echo "skip: the owner key exists"
elif test -n "${TRADEGEN_HOME:-}"; then echo "stop: TRADEGEN_HOME is set to $TRADEGEN_HOME"
elif test -n "$(powershell -NoProfile -Command 'Get-CimInstance Win32_Process | Where-Object { $_.Name -like "python*" -and $_.CommandLine -match "run_all" } | Select-Object ProcessId,Name,CommandLine')"; then echo "wait: a run_all.py is running"
elif .venv/Scripts/python.exe -I -c "import datetime, sys, zoneinfo; t = datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Seoul')).time(); sys.exit(0 if datetime.time(8, 30) <= t < datetime.time(9, 15) or not datetime.time(0, 5) <= t < datetime.time(23, 55) else 1)"; then echo "wait: 08:30 to 09:15 or 23:55 to 00:05 KST"
else
  KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/Scripts/python.exe -I "$S/smoke.py"; echo "exit $?"
  test -e ~/.tradegen/odds && echo "a real odds home exists" || echo "no real odds home"
fi
```

  On `wait: ...`, wait and run the block again. On `stop: TRADEGEN_HOME is set to ...` or
  `STOP: the state root is not ~/.tradegen` (a `TRADEGEN_HOME` line in the shell's profile or in `.env`), stop and
  report: the state is pointed somewhere else, and only the owner can say which home is real.

  Expected when it ran (the `<...>` values are printed by the run: the plan hash and the code hash, 16 hex digits
  each, the number of warnings Python recorded, the number of folders and files under `~/.tradegen` with the home
  itself, and today's date):

```text
Plan 1 of 1 (<plan hash, 16 hex digits>)
Refused: the signed owner state is not usable (no owner key yet, a broken owner log, unapproved tables, or code changed since you signed it), so nothing new is allowed.
No numbers are shown for a refused plan.
These numbers describe rules you wrote, run in a model. They are not advice, and TRADEGEN does not recommend any plan. A higher chance of reaching the target does not make a plan better.
Recorded with this report:
code hash: <code hash, 16 hex digits>
code signed: no
owner log entry: 0
exit 2
seams called: []
warnings recorded: <n>
~/.tradegen unchanged: <n> entries
APPEND: printf '%s\n' "- Task 19: real-home smoke (Q45; KEYLESS, hermetic, seams stubbed) on <today>: exit 2 STATE_UNUSABLE, no seam called, ~/.tradegen unchanged (<n> entries)" >> docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
OK
exit 0
no real odds home
```

  The card's lines come from Task 12's catalogue in its render order (plan head, refusal, `refused.none`, footer,
  provenance); the provenance lines are the ones the no-key context has (no table hashes and no key fingerprint, so
  those lines are left out). The script itself decides on five things: exit 2, an empty stderr, the STATE_UNUSABLE
  line, no seam called, and an unchanged listing. If the card differs from this listing only in its provenance
  lines, the drafts of Tasks 12, 13 and 18 win over the listing, and the script's verdict stands. The last line must
  be `no real odds home`; `a real odds home exists` is a bug: stop and report.

  Then run the command it printed after `APPEND: `, exactly as printed, and check it with
  `tail -n 1 docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`.

  On `skip: the owner key exists`, append instead:

```bash
printf '%s\n' "- Task 19: real-home smoke skipped on $(date +%F): the owner key exists (core/compliance/owner_pubkey.pem), and with it the context load would write a snapshot under ~/.tradegen/compliance" >> docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
```

  When the script's last line is `FAIL: ...` (`exit <code>, not 2`, `stderr ...`, `no STATE_UNUSABLE card`,
  `seams called [...]` or `~/.tradegen changed: <n> path(s), listed above`), stop and report it to the owner in the
  form of Step 3, with the paths it names; only a FAIL whose one problem is the changed listing can lead to a rerun.
  Other programs also write under `~/.tradegen`, so read that listing's paths (printed under `~/.tradegen CHANGED`, a
  folder ending in `/`) in this order:
  1. Any path under `odds/`, `.` (the home itself), any path under `compliance/` other than
     `compliance/alerts.jsonl`, or a new `compliance/` without `compliance/alerts.jsonl`: the CLI or an import wrote
     to the real home. That is a bug, never a rerun: stop.
  2. Otherwise, any path outside `odds/` and `compliance/` (for example `runs/`, `ficc_cache/` or `trading/`, which
     an open TRADEGEN app writes): stop and ask the owner, through the controller, whether the TRADEGEN app was open.
     On a yes, append
     `- Task 19: the real-home smoke of <date> saw <the paths> change while the TRADEGEN app was open; run again with it closed`
     with `printf '%s\n' "<that line>" >> docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`, and
     run the block again once the owner has closed it. On a no, it is a bug: stop.
  3. Otherwise the only change is `compliance/alerts.jsonl` (with `compliance/` when that folder is new): the daily
     alert job (G3-4; Task Scheduler can also start a missed run outside 09:00 to 09:10). Append one line and run the
     block again:

```bash
printf '%s\n' "- Task 19: G3-4: the real-home smoke of $(date +%F) saw the daily alert job append to ~/.tradegen/compliance/alerts.jsonl; run again" >> docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
```

  Keep the card for Step 11: the owner sees it.

- [ ] **Step 8: The final review, and the repeat run after a fix**

  1. Request the final review of `main..odds-engine` (superpowers:requesting-code-review).
  2. Fix each finding the controller takes in a new task with its own failing test, under the rules of Tasks 1 to 18:
     - the DRIFT RULE;
     - the overlap check before each test command;
     - the record restored after each `--suite` run;
     - one commit per fix;
     - one ledger line per finding and per ruling.

     The controller pushes after each fix's review passes (G3-3). Then request a re-review of the fix commits, and
     repeat until it finds nothing to fix.
  3. If no fix commit was made, go to Step 9.
  4. After any fix commit, the record and the README rows of Step 6 are stale. Repeat Steps 1 to 7:
     - Step 1's log check also lists the Step 6 record commit and the fix commits as `other after task 18`;
     - Step 2's baseline run is skipped;
     - the run's numbers win (G3-1); the run check still compares with main's record (T19-3), so its
       `rows added outside odds:` line counts the fix tests too, as `(see G3-1)` with a G3-1 line naming them, each
       explained by its fix's ledger line;
     - Step 5 edits the cells as the first pass left them, and skips Edit L0;
     - Step 6 runs as written, but its commit uses the subject and body below;
     - Step 7 runs again, because a fix may have touched the CLI's path; its `APPEND:` line goes into the ledger
       beside the first one.

     The repeat's Step 6 commit:

```bash
git commit -m "test: full run after the odds final review wave" -m "Task 19, after the final review: full run <passed>/<total> passed, 0 failed, <not run> not run (odds <odds cell>; compliance <compliance cell>); README compliance, odds and Total rows." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

     Fill the five slots from the repeat run's Step 4 output: the three totals of its `this run:` line, and the
     values after `odds=` and `compliance=` on its `README cells:` line. If README.md did not change, `git add` only
     `qa/acceptance_results.json` and drop "README compliance, odds and Total rows." from the body. After the
     repeat's Step 7, go to Step 9.

- [ ] **Step 9: Complete the ledger and commit it**

  Read the ledger with the Read tool first.

  **Edit L2 (the rulings as applied and the hand-off).** Anchor: the `## Runs` heading (it occurs once). Old text:

```text
## Runs
```

  New text (each entry names the tasks that applied the ruling, from the TASKS coverage tables):

```text
## Rulings as applied

- Order of the plans (Tasks 1 and 19; DQ26, R2-11): the follow-up merged first and this branch was cut from the
  merged main (see Base); E1 starts after this plan merges.
- O1 (Tasks 1, 5, 6, 7, 8, 15, 16, 17): everything injected; the signed core `core/odds` holds no clock, no file
  I/O and no data layer, and the unsigned `core/oddsdata` loads, caches and runs.
- O2 (Task 1): the odds-own guards, each with a positive control.
- O3 (Tasks 2, 3, 4): the compliance-side prerequisites: the venue odds keys, the sourced lots and minimums,
  `owner.calendar_in_force` and `gate.grey_rows`.
- O4 (Task 5): the plan types.
- O5 (Tasks 10, 13): review_by and rule dates.
- O6 (Tasks 4, 13, 15, 16): the calendar from the owner's signed store.
- O7 (Tasks 5, 15): venues and feeds.
- O8 (Tasks 5, 13): SPECIAL_REGIME.
- O9 (Task 17): the D13 replay against its pinned card.
- O10 (Tasks 6, 7, 8, 9, 13, 14): models, statistics and the simulator.
- O11 (Tasks 2, 3, 6, 10, 13): stakes, equity and costs.
- O12 (Tasks 7, 16, 18): seeds and the persisted odds state.
- O13 (Tasks 1, 5, 15, 18, 19): the cache, the seams, the harness and the budgets (times under Runs).
- O14 (Tasks 12, 17): the report.
- O15 (Tasks 18, 19): the CLI, and its real-home smoke under Runs.
- R2-1 (Tasks 6, 13): the KRX stock sell tax sits inside the floor, equal to `instruments.cost_per_side`; a sell
  year missing from SELL_TAX_BP is NOT_TRADABLE.
- R2-2 (Tasks 6, 19): the band lower edge is 1,404 at ETF reference 2,005; `orders.limit_prices` is unchanged; E3
  takes the venue's quoted edges (hand-off below).
- R2-3 (plan header, Task 19): the spec departures are listed under "For spec rev 3.3"; they are folded into the spec
  at GPT's checkpoint after 2026-10-30 14:40, as a docs change outside this branch (CONTRACT 2).
- R2-4 (Tasks 12, 19): the fresh-seed rerun is not built and `compare.fresh` says so; handed to E2 (below).
- R2-5 (Tasks 3, 6, 13, 17): a replay leg needs only `lot` and `min_order`; every other leg also needs `fee_extras`.
- R2-6 (Tasks 1, 16, 18): `repo_anchor` and `tree_hash` are copied into `core/oddsdata/inputs.py` with equality
  tests; no run-time `sys.modules` check.
- R2-7 (Task 12): HIDDEN_EDGE with no finite range prints "unavailable for this plan (no finite range)".
- R2-8 (Tasks 5, 14): STALE_DAYS 3 and 14, and the per-refit pilot checks.
- R2-9 (Task 8): the GARCH corruption margins on the real pilot stream (Task 8's R2-9 margins line under Runs).
- R2-10 (Task 1): `pstats` and `tracemalloc` bind `core/odds` through the merged lists.
- R2-11 (Task 1): the follow-up branched from main's HEAD, and this plan after the follow-up merged.
- R2-13 (Tasks 1, 2, 3, 4, 19): the DRIFT RULE; every drift ruling is a `- Task <n>` line under Drift rulings.
- Round 3 (G3-1 to G3-5, O3-1 to O3-22; every task): counts from the drafts, with each difference under Runs
  (G3-1); times over target under Runs (G3-2); the controller's pushes and one pull request (G3-3); the 09:00 KST
  window (G3-4); no sandbox leftovers copied (G3-5).

## Hand-off to execution (E1, E2, E3)

- E1 (read-only account inquiry, next): it inherits `owner.load_context`, `gate.screen`, `gate.grey_rows`,
  `owner.calendar_in_force`, `report.OddsReport` with `report.render`, and the refusal codes of `core/odds/plan.py`.
  Live balances replace `Positions(equity_krw=stake)`; E1 itself passes no live positions to `load_context` (E24,
  E3-5), so that replacement is E2's.
- E2 (execution core, which arms): never pass a zero stake to `screen` (the odds engine refuses STUCK_AT_START
  first). Apply the OKX cap per entry, and size the first entry so the gate's cap check passes: `first_stake =
  floor_units(cap x W0) x p0` can exceed cap x equity by one ulp, which the gate blocks as "cap exceeded" (O3-22);
  never loosen the gate. Halt for the rest of the Asia/Seoul date on a daily-loss breach, whatever names the exit,
  and at the floor (O3-17). Rerun the plan on a fresh market seed before arming, which `compare.fresh` says this plan
  does not build (R2-4). Entries at the limit-up price fill in the odds engine, while
  `core/engine/orders.simulate_fill` refuses them (O3-17, O3-22).
- E3 (live order adapters): take band edges from the venue's own quoted limit prices, never computed. The odds band
  (per-edge rule, 1,404 at ETF reference 2,005) and `orders.limit_prices` (one tick for both edges, 1,405) differ by
  one tick there, and this plan changes neither (Q41, R2-2). For limit-up fills, use the venue's answer (O3-17).
- No open issue of this plan's own is left: R2-1 settled the KRX stock tax inside the floor, and R2-2 the band edge.
- The owner acts (spec 11; Claude performs none): 1 the signer; 2 the code hash; 3 the rules table, the instrument
  map and the venues file, once it carries `fee_extras` (0 allowed) and the missing lots and minimums; 4 the calendar
  set (KRX and US plans only); 5 `total_loss_floor_krw`, `daily_loss_krw` and `okx_equity_share`; 6
  `age_of_majority` (KR-OKX-SPOT requires it, so OKX plans need it) and the withdrawal entries.

## Runs
```

  **The ledger cross-check (git and grep only).**

```bash
L=docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
grep -n "^## " "$L"
grep -n -E "MISSING|^- open:" "$L"
grep -c "^- Task 8 R2-9 margins" "$L"
for n in $(seq 1 19); do grep -q -E "^- Task $n[: ]" "$L" || echo "no line of Task $n"; done
for id in "Order of the plans" O1 O2 O3 O4 O5 O6 O7 O8 O9 O10 O11 O12 O13 O14 O15 R2-1 R2-2 R2-3 R2-4 R2-5 R2-6 R2-7 R2-8 R2-9 R2-10 R2-11 R2-13 "Round 3"; do test "$(grep -c "^- $id (" "$L")" = 1 || echo "rulings: $id"; done
git log --format='%h %b' main..HEAD | grep -i -E "ruling|drift|deferred|minor"
grep -n "^- Task 19" "$L"
```

  Expected:
  - the headings in this order: `## Base`, `## Merged line numbers (Task 1; cited by line in the contract as of
    995534b)`, `## Drift rulings`, `## Deferred minors`, `## Rulings as applied`,
    `## Hand-off to execution (E1, E2, E3)`, `## Runs`;
  - no `MISSING` and no `- open:` line (an `open:` line means an anchor nobody ruled on: stop and rule);
  - `1` or more for the R2-9 margins line;
  - no `no line of Task <n>` and no `rulings: <id>` line. Tasks 4 to 6, 9, 10 and 12 to 18 say only "append the
    tails of these runs", so a line without the `- Task <n>` prefix is likely: on `no line of Task <n>`, write the
    missing line now from `git show --stat <that task's commit>` and the run tails it recorded, in the
    `- Task <n>: ...` form under `## Runs` (the Edit tool, after a Read), then run the cross-check again;
  - every commit body that names a ruling, a drift or a deferred minor has a `- Task <n>` line of that task in the
    ledger, and so does every review-fix commit. Add any that is missing now, one line each, in the
    `- Task <n>: ...` form with the commit's short hash (a drift ruling above `## Deferred minors`, a deferred minor
    above `## Rulings as applied`);
  - the `- Task 19` lines: the drift ruling of Edit L0, the full-run line (two after a fix wave) with its
    status-change, G3-1 and G3-2 lines, any G3-4, open-app or RULING line, and the smoke line (two after a fix
    wave).

  Then the commit:

```bash
git add docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
git status --short
git diff --cached --stat
git diff --cached --stat --ignore-cr-at-eol
```

  Expected: `git status --short` prints only `A  docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`;
  the two stat outputs are identical: `1 file changed, <n> insertions(+)`, `<n>` the ledger's line count. No test
  reads a `.md` file under `docs/superpowers`, so this commit leaves the record of Step 6 (or Step 8) current.

```bash
git commit -m "docs(plan): execution ledger of the odds engine" -m "Every task review, fix round, DRIFT RULE ruling, the R2-9 margins, the rulings as applied, the hand-off to E1, E2 and E3, the full runs and the real-home smoke of the odds engine execution, kept for the owner's audit and GPT's check after 2026-10-30 14:40." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -3
git status --short
```

  Expected: the ledger commit on top of the record commit (and its repeat), and `git status --short` prints nothing.
  An implementer subagent stops here and reports the hashes of the record commit(s) and the ledger commit to the
  controller.

- [ ] **Step 10: Push and open the pull request (the controller only, G3-3)**

  The controller pushes the branch and opens one pull request into main. Nobody merges: merging stays the owner's
  choice (superpowers:finishing-a-development-branch).

```bash
git remote -v
gh pr list --head odds-engine --state all --json number,url,state
```

  Expected: `origin	https://github.com/xkg4real/tradegen.git (fetch)` and `(push)`, and `[]` (no pull request for
  this branch yet). A listed one means it exists already: stop and report its URL instead of opening another.

  Write the body with these commands (the static parts are quoted heredocs; the run lines come from the ledger):

```bash
S='<the session scratchpad>/tradegen-odds-task19'
B="$S/pr_body.md"
L=docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md
cat > "$B" <<'EOF'
## Summary
- The odds engine of spec rev 3.2, with the departures listed under "For spec rev 3.3" in the plan: the signed core
  `core/odds` (plan types and named refusals, costs with the per-fill tick floor, the no-edge bootstrap and GARCH-t
  with their pilot checks, the path engine, the ceiling and exact bold play, the report and its language guard), the
  unsigned loader `core/oddsdata` (the bars cache, the signed calendar, the S_C3 replay and the CLI
  `python -m core.oddsdata.run --plan <file>`), and the compliance helpers it needs (`calendar_in_force`,
  `grey_rows`, the venue odds keys).
- On `odds-engine`: Tasks 1 to 18, one commit each; Task 19's full-run record and ledger commits; and the review
  fixes. The execution ledger `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md` records every
  drift ruling, the R2-9 margins, the rulings as applied, the hand-off to E1, E2 and E3, and the runs.
- No order path: nothing here places an order, arms anything or signs anything. Every odds run is refused until the
  owner acts of spec section 11 are done.

## Test plan
EOF
grep -E "^- Task 19: (full run|real-home smoke)" "$L" >> "$B"
cat >> "$B" <<'EOF'
- The final review of `main..odds-engine` and the re-review of its fixes; each finding and ruling is in the ledger.

The real odds are unchanged: no plan without a real edge can beat 1 in 1,000 for KRW 42,000 to KRW 42,000,000, or
1 in 1,999 when a floor at half the stake truly holds. This is research and software design, not legal or investment
advice; TRADEGEN and its author are not licensed advisors. Merging is the owner's choice.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
cat "$B"
```

  Expected: the body as written, with the `- Task 19: full run (KEYLESS) ...` and `- Task 19: real-home smoke ...`
  lines of the ledger under `## Test plan` (two of each after a fix wave). Then:

```bash
S='<the session scratchpad>/tradegen-odds-task19'
git push -u origin odds-engine
gh pr create --base main --head odds-engine --title "Odds engine: signed odds core, unsigned loader and CLI, full run" --body-file "$S/pr_body.md"
gh pr view --json url,state,baseRefName,headRefName --jq '.state + " " + .baseRefName + " " + .headRefName + " " + .url'
```

  Expected: the push ends with `branch 'odds-engine' set up to track 'origin/odds-engine'.` (or
  `Everything up-to-date` when the controller pushed after the last review); `gh pr create` prints the pull request's
  URL, `https://github.com/xkg4real/tradegen/pull/<the number gh prints>`; and `gh pr view` prints
  `OPEN main odds-engine https://github.com/xkg4real/tradegen/pull/<the same number>`. Do not merge. If `gh` says
  `You are not logged into any GitHub hosts`, Claude never logs in (the sign-in is the owner's): skip `gh pr create`
  and `gh pr view`, and give the owner `https://github.com/xkg4real/tradegen/compare/main...odds-engine` with the
  title above and the body in `$S/pr_body.md`; Step 11's URL is then that compare link until the owner opens it.

- [ ] **Step 11: Hand off**

  1. **The pull request.** Give the owner its URL from Step 10. The owner decides on the merge. After it merges, E1
     starts from the merged main, under its own DRIFT RULE (E1 Task 13's Edits R4 and R5 find the odds row and the
     Total line this task wrote).
  2. **Spec rev 3.3.** The departures under the plan header's "For spec rev 3.3" are folded into the spec at GPT's
     checkpoint after 2026-10-30 14:40, as their own docs change on main (T19-5). This task does not edit the spec:
     CONTRACT 2 keeps every file under `docs/` except the ledger out of this branch. A valid finding of that check that
     touches built code becomes a new task with its own failing test.
  3. **The owner.** Tell the owner the text below in chat, with Step 7's card above it. Claude performs none of the
     acts, never runs the signer with a real key, and never asks for a passphrase or a key. Pick the first paragraph
     by Step 7's result.

     If Step 7 ran:

```text
The odds engine is built, and its pull request is open: <the URL from Step 10>. Merging it is your choice; nothing
has been merged, armed or signed.

The card above is the odds program run once against your real home folder, with every network connection blocked.
With no owner key yet, it refused the plan before reading any price data ("the signed owner state is not usable"),
called no price feed and wrote nothing under ~/.tradegen. That is the designed safe default, not a fault.
```

     If Step 7 printed `skip: the owner key exists`:

```text
The odds engine is built, and its pull request is open: <the URL from Step 10>. Merging it is your choice; nothing
has been merged, armed or signed.

I did not run the odds program against your home folder: your owner key exists, and with it the program would write
a snapshot there. To see what it says now, run `.venv/Scripts/python -m core.oddsdata.run --plan <your plan file>`
yourself from the TRADEGEN folder. Once your acts let a plan through, it downloads public price history (no account
and no order call) and keeps its cache and comparison state under ~/.tradegen/odds. Act 1 is done; the acts below
from act 2 on still apply, and act 2 needs a new signature that covers core/odds.
```

     Then, in both cases:

```text
Every odds run stays refused until you do these owner acts (spec section 11). I do none of them.
1. Set up the signer, with the steps of the compliance follow-up's hand-off: copy the merged tools/signer/sign.py to
   %USERPROFILE%\tradegen-signer\ and read it in full; in Windows Terminal (PowerShell), run
   certutil -hashfile "$env:USERPROFILE\tradegen-signer\sign.py" SHA256 and write the hash on paper; then create
   your key with a long passphrase, as spec section 11 lists it. Run the signer only from Windows Terminal opened
   from the Start menu: it refuses a VS Code integrated terminal (its parent chain stops at a launcher that has
   exited).
2. Sign the code hash, after reading every file the signing prompt lists (today core/__init__.py, core/isolation.py,
   core/compliance/*.py and core/odds/*.py).
3. Approve the rules table, the instrument map and the venues file. First add to core/odds/venues.yaml the fixed
   charges (fee_extras; 0 is allowed). fee_extras is the fixed charge in KRW per buy and per sell (phi_buy,
   phi_sell) beyond the commission and tax rates already built in. Write 0 only when the venue really charges
   nothing extra: a charge you leave out makes every chance on the card look better than it is. Also add the lots
   and minimums the file still lacks (Upbit, OKX and the US shares). Until then every leg is refused as not
   tradable; only the S_C3 replay needs nothing beyond the Upbit lot. The card's "not tradable" sentence does not
   say which act is missing: it is this one.
4. Sign the calendar set (KRX and US plans only). Until then only crypto plans run. A KRX or US plan run after acts
   1 to 3 and 5 but before this one still reads its price quotes (read-only, no account and no order call) before
   it is refused.
5. Set your loss limits, which take effect from the next Asia/Seoul day.
   - total_loss_floor_krw is the least you are willing to keep (for example KRW 21,000 of KRW 42,000). Under
     floor-safe sizing (the default) no position can take you below it, and a plan that can no longer place an
     order above it stops trading; the card shows what is kept. Under stop-based sizing a price gap past the stop
     can take you below it, and the card says so.
   - daily_loss_krw is the most you accept losing in one Asia/Seoul day. It is checked at each check point: a loss
     that reaches it closes the position and stops trading for the rest of that day, and a fast move can pass it
     between two checks.
   - okx_equity_share is the largest share of your equity (above 0, at most 1) that one OKX entry may use; the card
     states it.
   A higher floor or a smaller daily limit makes losses smaller and the target rarer; neither makes a plan better.
6. Record age_of_majority (OKX plans need it) and your withdrawal entries.
An Upbit crypto plan needs acts 1, 2, 3 and 5; a KRX or US plan also needs act 4; an OKX plan also needs act 6.

The order matters for acts 1 and 2: the next plan (E1, read-only account inquiry) changes the signer and the signed
code again. Do them after E1 lands; if you do them before (or act 1 is already done), re-copy and re-hash the signer
as in act 1 and sign again after E1 lands. The data loader and the odds program itself
(core/oddsdata) are outside your signature: read them before you rely on them.

The real odds, which none of this changes: with no real edge, no plan can beat 1 in 1,000 for KRW 42,000 to
KRW 42,000,000, or 1 in 1,999 (about 1 in 2,000) when a floor at half the stake truly holds. A KRX buy-and-hold plan
is capped at about 95x to 459x in 30 days, so it cannot reach 1,000x at all. The typical month ends at the floor.
The research puts the practical chance of 1,000x in a month at 0.01% or less. A higher chance on a card does not
make a plan better.

This is not legal or investment advice; I am not a licensed advisor, and neither TRADEGEN nor its author is.
```

  The scratch folder `<the session scratchpad>/tradegen-odds-task19` is outside the repo and may stay
  (G3-5: nothing from it is copied into the repo or the plan folder).

---
