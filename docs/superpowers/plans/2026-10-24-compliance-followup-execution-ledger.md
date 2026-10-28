# SDD ledger — plan: docs/superpowers/plans/2026-10-24-compliance-followup.md

Started 2026-10-28 15:35 KST from main d9f4025 (plans PR #1 merged 2026-10-28T06:33:40Z).
Branch-base check (Task 1 Step precondition): `git status --short` empty; `git diff --stat 995534b HEAD -- . ':!docs'` empty.

## Pre-flight scan (workflow wf_4ed96700-f20, 10 agents, verified)
## Per-task rows

| Task | Self-consistency | Anchors checked / problems |
|---|---|---|
| 1 | CONSISTENT (simulated: 3 FAILs match brief:330-332, then all pass) | 10/10 ok; 2 minor |
| 2 | CONSISTENT (8 FAIL lines byte-identical; loader parses shipped table, 47 rows) | 11/11 ok; 3 minor |
| 3 | CONSISTENT (59425 B, sha 74894f05...; one line changes) | 2 (1 ok, 1 after-T2-ok); 3 minor |
| 4 | CONSISTENT (12 missed targets reproduce; helpers identical in owner.py and sign.py) | 12/12 ok; 2 minor |
| 5 | CONSISTENT (4 FAILs match; mutants all caught) | 8/8 after-T4-ok; 2 minor |
| 6 | CONSISTENT (FAIL text matches brief:127; A.8 identical) | 2 (1 ok, 1 after-T2-ok); 2 minor |
| 7 | CONSISTENT (both FAILs reproduce; checked_target before POST and _MEM) | 4/4 ok; 3 minor |
| 8 | Counts, anchors and outputs consistent; Step 9 conflicts with G3-3 | 11/11 ok; 1 important, 4 minor |

## Cross-task rows

| Tasks | Shared | Produces vs consumes | Found |
|---|---|---|---|
| 2, 3 | tests/compliance_tables.py; kr_rules.yaml | T2 pins match/requires/treatment, not reason; T3 edits a reason | OK |
| 2, 6 | tests/compliance_cli.py | separate regions; 2-for-2 line swap | OK |
| 4, 5 | sign.py; compliance_signer.py | T4 nets +20 lines; T5 anchors still unique | OK |
| 4 owner vs sign | 7 closure helpers | verbatim copies plus a source-equality test | OK, identical |
| 1 vs 2, 4, 6 | guard lists over core/compliance | new code must pass 9 static guards | OK, all pass |
| 1 vs 3, 5 | guard scope | yaml and tools/ are out of scope | OK |
| 7 vs 1 | core/ficc, data/krx | raw/def/seal guards; T-RO-01/02 | OK |
| 1 R7 vs run_all/README/odds/E1 | `one suite:` lines | `_suite_names` parses both to 10 names | OK |
| 1-7 vs 8 | counts, commit subjects, README cells | 317 -> 327; 7 subjects equal | OK |
| 3 vs 8 Step 6 | draft sha prefixes | 74894f05 / 50fa819f / 603e2640 | OK |
| 7 vs 8 Step 2 | real kis_token.json | checked_target creates nothing | OK |
| 8 vs header/G3-3 | merge, push, PR | header: "merge step becomes open the PR" | MISMATCH (important, F1) |
| 5 vs 8 Step 9 | signer help shell syntax | `%USERPROFILE%` vs `$env:USERPROFILE` | open ruling (minor, F11) |
| 2/4 vs odds/E1 A.12 | line shifts cited later | +31, 633->739, 247->290 | OK |
| 1 precondition | branch base | main clean, diff empty | OK now |

## Count arithmetic

- Today: compliance 317 rows (315 PASS / 2 NOT_RUN); full run 1166 rows (1043 PASS / 123 NOT_RUN), README.md:839-840.
- New tests: T1 +1 (guards), T2 +6 (tables), T3 0, T4 +1 (signer), T5 0, T6 +1 (cli), T7 +1 (isolation). 10 in all.
- Suite after each task: 318, 324, 324, 325, 325, 326, 327. PASS goes from 315 to 325 and NOT_RUN stays 2.
- Full run: 1176 rows, 1053 PASS / 123 NOT_RUN. Task 8 Step 2's group table sums to that.
- Module lines agree: guards 15->16, tables 59->65, signer 37->38, cli 35->36, isolation 16->17; loader, model,
  gate, owner and store do not change.
- None of the new tests can raise NotRun. Helpers start with `_` and are not collected, and no names collide.

## Findings and suggested rulings

| # | Task | Sev | Finding | Suggested ruling |
|---|---|---|---|---|
| F1 | 8 | important | Step 9.1 says "**Merge**"; :10, :33, :433 and A.10 (appendix-a.md:880-881, brief :1372-1373) assume the merge; no push step and no PR step. The committed plan :3726-3728 says the same. | Apply header.md:119-122 and G3-3: Step 9.1 becomes "controller pushes `compliance-followup` (including the Step 5/7/8 commits) and opens one PR to main; the owner merges". Step 9.2 (odds plan) waits for the owner's merge. Change "the merge" to "the pull request" at :10, :33 and A.10. No subagent pushes. |
| F2 | 1 | minor | The new test repeats controls from Edit 3, so one route fails two tests. | Accept as written; the duplicates pin the list. |
| F3 | 1 | minor | `_suite_names` takes the first `one suite:` line and strips `")` only; a reworded line would fail closed. | Accept; it fails closed and its controls cover the format. |
| F4 | 2 | minor | Edit 10 runs `policy_ref.split` and `match.get("asset")` twice each. | Accept, or hoist them into locals. Behaviour stays the same. |
| F5 | 2 | minor | The no-class-axis branch hard-codes `{etp_leveraged, etp_single_stock}`. | Accept; optionally derive it from `_D16_CLASSES`, keeping the same set and the pinning test. |
| F6 | 2 | minor | `test_only_a_grey_row_states_a_cap` repeats the `{{cap}}` allow case. | Accept. |
| F7 | 3 | minor | The assertion checks presence only; R3 says the reason "starts" with the phrase. | Optional, stricter: `assert krx_deriv.reason.startswith("KOSPI200 futures and options need broker approval, ")`. |
| F8 | 3, 4, 7 | minor | The expected suite and module lines leave out the Developer Mode variant (T3 Step 4, T4 Step 4, T7 Step 2). | G3-1 covers it: 0 failed with a different count passes and is ledgered. A FAIL never passes. |
| F9 | 3 | minor | The drift note leaves out the line shifts from T2 Edits 1 and 4. | Accept; the anchor wins (drift rule). |
| F10 | 4 | minor | The synthetic trees are duplicated in the store and signer tests. | Accept; the source-equality test guards them. |
| F11 | 5, 8 | minor | Help sends the owner to Windows Terminal (PowerShell) but keeps `%USERPROFILE%` lines, and the test pins one. T5 brief :56-61 asks for a ruling, and none exists. | Rule: the T5 bullet says "a Command Prompt tab in Windows Terminal". A PowerShell rewrite of the help can follow as a later task with its own pinned needles. |
| F12 | 5 | minor | The refusal text does not name the cycle, the 256 cap or a snapshot failure. | Accept; the branch still refuses. |
| F13 | 6 | minor | The alerts.py module docstring still says log() records the fingerprint, with no condition. | Add "(codes 0-2)" to alerts.py:3-4 in Task 6. |
| F14 | 6 | minor | The R6 wording "always comes from a check that verified the log" overstates; a hand-written `--log` summary is still recorded. | Wording fix in the ledger or header; the code is unchanged. |
| F15 | 7 | minor | The docstring's "R8 (ledger:81)" becomes ambiguous once a second ledger exists. | Write "compliance-gate ledger:81". |
| F16 | 7 | minor | The reason Edit 3 gives for its context lines is wrong (the indent alone makes the old text unique). | Accept; the edit does no harm. |
| F17 | 8 | minor | The Step 5 commit body hard-codes 1053/1176; Step 2 has no Developer Mode line; Edit 1 does not give the form for 0 NOT_RUN. | Use the run's numbers (G3-1, :318). The 0 NOT_RUN form is `\| N PASS \|` (:289-290). |
| F18 | 8 | minor | Step 6 does not carry G3-4's 09:00-09:10 KST window, so the job's write could raise a false "stop and report". | Apply G3-4: write a ledger line and rerun outside the window. |
| F19 | 8 | minor | Step 6 passes vacuously if both listing captures fail (empty strings). | Guard with `test -n "$before" &&` before the equality. |
| F20 | 8 | minor | Brief :180 cites run_all.py:118 for the write; the write is :119 (:118 is the mkdir). | Cite :119. |
| F21 | status | minor | Relayed question: PR #1 (plans-wip-2026-10-24 -> main) is MERGED at d9f4025. The follow-up has no branch and no PR yet. | None needed. |

Refuted: brief :120 "compliance_guards.py:485 is stale". header.md:127 says cited line numbers are 995534b's and
only help find the anchor, so :485 follows the plan's own convention.

## Pre-flight rulings
- Ruling: the ledger is kept at .superpowers/sdd/2026-10-24-compliance-followup/progress.md during execution and copied to docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md at Task 8 Step 8 (the step allows a ledger kept outside the repo) — keeps implementers' git status clean — if wrong: one copy step at Task 8.
- Ruling F1: Task 8 Step 9.1 "Merge" becomes: the controller pushes compliance-followup (with the Step 5, 7 and 8 commits) and opens one pull request to main; the owner merges. Step 9.2 (the odds plan) waits for the owner's merge. Task 8 Step 7 (final review) is the controller's SDD final review. "the merge" reads "the pull request" at brief :10, :33 and A.10 — header.md:119-122 and G3-3 win over the task text — if wrong: none; merging was never Claude's.
- Ruling F2, F3, F6, F9, F10, F12, F16: accepted as written — each fails closed or only repeats a check — if wrong: minor duplicate test lines.
- Ruling F4, F5: Task 2 Edit 10 is applied as written (no hoisting, no derived set) — the plan's exact text and its pinning test win; behaviour is identical — if wrong: two repeated lookups.
- Ruling F7: Task 3 adds, beside the brief's assertion, `assert krx_deriv.reason.startswith("KOSPI200 futures and options need broker approval, ")` — R3 says the reason starts with that phrase; stricter, no new test row — if wrong: one extra assertion line.
- Ruling F8, F17: counts that differ from the brief with 0 failed pass and are ledgered (G3-1); Task 8's commit bodies and README cells use the run's numbers; the 0 NOT_RUN cell form is `| N PASS |` — if wrong: none.
- Ruling F11: Task 5's help and tests stay as written (its needles pin the text); the help's existing %USERPROFILE% lines are Command Prompt syntax, so the hand-off tells the owner to use the $env:USERPROFILE forms in PowerShell (as Task 8 Step 9 does). A PowerShell rewrite of the signer help is a later task with its own pinned needles — if wrong: the owner meets Command Prompt syntax in a PowerShell window; the chat hand-off gives the working form.
- Ruling F13: Task 6 also adds "(codes 0-2)" to the alerts.py module docstring sentence about the fingerprint — the docstring would otherwise state the old rule; alerts.py's hash moves in Task 6 anyway — if wrong: one docstring word.
- Ruling F14: R6 is read as "the first recorded fingerprint comes from a summary whose code is 0, 1 or 2 (one --check printed, or a hand-written --log summary)"; code unchanged — if wrong: wording only.
- Ruling F15: Task 7's docstring writes "compliance-gate ledger:81" instead of "ledger:81" — two ledgers now exist — if wrong: one word.
- Ruling F18, F19, F20: Task 8 Step 6 applies G3-4 (a run spanning 09:00-09:10 KST is ledgered and rerun), guards the equality with `test -n "$before" &&`, and cites run_all.py:119 — stricter — if wrong: none.

## Tasks
- Task 1: dispatched 2026-10-28 (BASE d9f4025; workflow wf_67ce08f6-a44, script scratchpad/sdd-task.js)
- Task 1: run wf_67ce08f6-a44 returned NEEDS_CONTEXT with nothing changed (still on main d9f4025): the implementer wants the owner's own words in chat that execution should start now, since the owner's latest message only asked whether the merge happened. Asking the owner.
- Owner approval in chat, 2026-10-28: "승인합니다" ("I approve"), answering "Start the compliance follow-up plan now, from Task 1?" (create compliance-followup from main, implement each task with review, push after each reviewed task, one PR at the end that the owner merges). Task 1 re-dispatched.
- Task 1: implemented and reviewed (run wf_9ff92eb2-cde): commit 7cae6aa; RED 13/16 with the brief's three FAILs, GREEN compliance_guards 16/16; compliance suite 318/318 passed, 0 failed, 0 not run (72 s) — G3-1 count note: the brief expected 316 PASS / 2 NOT_RUN; the two REFDATA symlink tests pass under Windows Developer Mode (the variant the brief names). Review: spec compliant, quality Approved, 0 critical/important. Controller check: diff stat equals --ignore-cr-at-eol (1 file, +98 -29), LF kept, Co-Authored-By present, compliance_guards rerun 16/16.
- Task 1: minor (deferred): T1-R1-1 _dynamic_hits' import-name branch checks DYNAMIC_NAMES, not DYNAMIC_BARE, so `from builtins import compile as c` is not a hit (plan-mandated Edit 9; stricter one-token fix `(DYNAMIC_NAMES | DYNAMIC_BARE)` for the final review to triage, checking it flags no legitimate `from re import compile`).
- Task 1: minor (deferred): T1-R1-2 the Edit 8 comment names only EntryPoint.load; R9's alias and getattr routes are not named (documentation; R2-12 accepts the limit).
- Task 1: minor (deferred): T1-R1-3 the new hit texts are asserted for truthiness only; one equality assertion would pin them.
- Task 1: minor (deferred): T1-R1-4 test data repeated across two tests (plan-mandated; pre-flight ruling F2 kept it).
- Task 1: minor (deferred): T1-R1-5 process notes: one bytes check first ran under the system python (repeated under .venv); the suite ran with timeout 600000 where the brief says 300000.
- Task 1: complete (commits d9f4025..7cae6aa, review clean)
- Task 1: pushed (git push -u origin compliance-followup, 7cae6aa)
- Task 2: dispatched (BASE 7cae6aa; workflow wf_cd13ee2b-01f)
- Task 2: implemented and reviewed (run wf_cd13ee2b-01f): commit cedfcdf; RED tables 57/65 with the brief's 8 FAIL lines byte-identical; GREEN tables 65/65, cli 35/35, gate 49/49, store 29/29, guards 16/16, guards ok; compliance suite 324/324 passed, 0 failed, 0 not run (102 s, recorded under G3-2; no budget set) — G3-1 count note: Developer Mode variant (brief: RED 56/65 + 1 not run, GREEN 64/65 + 1 not run, suite 322/324 + 2 not run). kr_rules.yaml sha unchanged 127a3c91...551bd3b79. Edit 8 applied with a shorter unique old string; result equals the brief's new text. Review: spec compliant, quality Approved, 0 critical/important. Controller check: stat equals --ignore-cr-at-eol (3 files, +212 -4), LF kept, Co-Authored-By present, tables 65/65, guards 16/16, cli 35/35 rerun.
- Task 2: minor (deferred): T2-R1-1 the max_leverage reason is pinned only for 10.5, where !r and :g print alike; one assert on 10.0000001 would pin the !r choice.
- Task 2: complete (commits 7cae6aa..cedfcdf, review clean)
- Task 2: pushed (cedfcdf)
- Task 3: dispatched (BASE cedfcdf; workflow wf_ee18171e-7dd; ruling F7 carried)
- Task 3: implemented and reviewed (run wf_ee18171e-7dd): commit 08a67bd; RED tables 64/65 (the d16 assertion, old reason as message); GREEN tables 65/65; compliance suite 324/324, 0 failed, 0 not run, exit 0 (102 s) — G3-1 count note: Developer Mode variant; tables stat 2 lines, 3 insertions in total, because ruling F7 adds the startswith assertion. kr_rules.yaml 59425 bytes, sha 74894f05e0b7f1af9183fa56632b27298cc3d4e33c2e0b5a6628227430ec27bd (the plan's value), LF. Review: spec compliant, quality Approved, 0 critical/important. Controller check (2026-10-29 02:36 KST, after a session restart): stat equals --ignore-cr-at-eol (2 files, +3 -1), sha matches, Co-Authored-By present, tables 65/65 rerun.
- Task 3: minor (deferred): T3-R1-1 the brief's presence assertion is implied by the F7 startswith assertion (both mandated).
- Task 3: minor (deferred): T3-R1-2 the comment and commit body cite "ledger:118"; with two ledgers it should read "compliance-gate ledger:118" (as ruling F15 does for Task 7).
- Task 3: minor (deferred): T3-R1-3 process: one overlap check before two module runs in one command; suite timeout 600000.
- Ruling: suite commands keep the Bash timeout 600000 (the controller's rule) where briefs say 300000 — a timeout is a ceiling, not a budget; G3-2 records the measured time — if wrong: none, a run only gets more time before it is cut.
- Task 3: complete (commits cedfcdf..08a67bd, review clean)
- Task 3: pushed (08a67bd)
- Task 4: dispatched 2026-10-29 02:40 KST (BASE 08a67bd; workflow wf_c867de39-f37)
- Task 4: implemented and reviewed (run wf_c867de39-f37): commit c4f4e6a; RED store 28/29, signer 36/38; GREEN store 29/29, signer 38/38; compliance suite 325/325, 0 failed, 0 not run (138 s, G3-2 recorded) — G3-1: Developer Mode variant; diff 4 files +149 -25 as the brief says. Review: spec compliant, quality Needs fixes (one important, plan-mandated).
- Task 4: Ruling: T4-R1-1 (important, plan-mandated; the reviewer reproduced it: `typing.__class__ = M` with a data descriptor TYPE_CHECKING keeps the dotted guard trusted while the guarded import runs) is fixed now, inside Task 4, as fix round 1: "__class__" joins the non-Load attribute set in owner._guards and its sign.py copy (character-identical), not the route-name list (reads of x.__class__ are common), plus a synthetic module like the reviewer's example in both synthetic trees — it is a binding-free route of the kind R4 closes (not "another module" or "a name built at run time"), only adds refusals, and adds no test row — if wrong: a module that stores to __class__ loses its guards and has its guarded imports hashed (fails closed).
- Task 4: Ruling: T4-R1-2 (minor, plan-mandated: `plain` accepts an `import typing` at any depth) is deferred to the final review's triage as a stated limit of the R2-12 family — it needs another module to inject builtins.typing first — if wrong: one more cross-module route stays open until a later task requires the import at module top level.
- Task 4: fix round 1/5 (1 addressed, 0 open — T4-R1-1 __class__ store; commits c4f4e6a..d3e2b79). Fixer confirmed: no __class__ store in core/__init__.py, core/isolation.py, core/compliance/*.py (git grep + ast scan); the reviewer's module really ran its guarded import before the fix; owner.py and sign.py helpers stay character-identical (signer 38/38 incl. the source-equality test). Controller check: stat equals --ignore-cr-at-eol (4 files, +162 -25 over 08a67bd..d3e2b79), LF kept, Co-Authored-By on both commits, store 29/29, signer 38/38 rerun.
- Task 4: minor (deferred): T4-R1-2 see the ruling above (`plain` at any depth).
- Task 4: minor (deferred, out of scope of the fix): dunder setattr calls (typing.__setattr__("__class__", M), object.__setattr__(typing, "TYPE_CHECKING", True)) are Load-context and not routes, so they keep the guard trusted — already a stated limit in Task 4's brief and R2-12.
- Task 4: complete (commits 08a67bd..d3e2b79, review clean after fix round 1)
- Task 4: pushed (d3e2b79)
- Task 5: dispatched (BASE d3e2b79; workflow wf_c2b092b7-4e9; rulings F11, F12 carried)
- Task 5: implemented and reviewed (run wf_c2b092b7-4e9): commit 5b16222; RED signer 34/38 with the brief's 4 FAIL lines in order; GREEN signer 38/38; compliance suite 325/325, 0 failed, 0 not run, exit 0 (116 s, G3-2 recorded) — G3-1: Developer Mode variant (registry AllowDevelopmentWithoutDevLicense=1, the reviewer checked). Edit 4 applied with a shorter unique old string; result equals the brief's new text. An uncommitted scratch property check over 1.4M random walks found no old-True verdict turning False. Review: spec compliant, quality Approved, 0 critical/important. Controller check: stat equals --ignore-cr-at-eol (2 files, +51 -11), LF kept, Co-Authored-By present, signer 38/38 rerun.
- Task 5: minor (deferred): T5-R1-1 only a missing-pid break after a session process is tested; one case {1:(2,'python.exe'),2:(3,'explorer.exe'),3:(4,'other.exe')} expecting False would pin the sticky "passed first" rule (both surviving mutants are stricter).
- Task 5: minor (deferred): T5-R1-2 help sends the owner to Windows Terminal (PowerShell) while the existing lines use %USERPROFILE% (ruling F11; the hand-off gives the $env:USERPROFILE forms; a PowerShell rewrite of the help is a later task).
- Task 5: minor (deferred): T5-R1-3 the refusal text does not name a snapshot failure, cycle or the 256 cap (ruling F12).
- Task 5: minor (deferred): T5-R1-4 the commit body cites "ledger:229, :233" (compliance-gate ledger; same family as T3-R1-2).
- Task 5: complete (commits d3e2b79..5b16222, review clean)
- Task 5: pushed (5b16222)
- Task 6: dispatched (BASE 5b16222; workflow wf_800408b6-2e3; rulings F13, F14 carried)
- Task 6: implemented and reviewed (run wf_800408b6-2e3): commit e2d3990; RED cli 35/36 with the brief's FAIL line; GREEN cli 36/36, guards 16/16; compliance suite 326/326, 0 failed, 0 not run, exit 0 (80 s) — G3-1: Developer Mode variant. Ruling F13 applied: the module docstring reads "records the key fingerprint (P20) only from codes 0-2". Review: spec compliant, quality Approved, 0 critical/important. Controller check: stat equals --ignore-cr-at-eol (2 files, +30 -3), LF kept, Co-Authored-By present, cli 36/36 and guards 16/16 rerun.
- Task 6: minor (deferred): T6-R1-1 the test docstring and commit body cite "ledger:219" (compliance-gate ledger; with T3-R1-2 and T5-R1-4 the final review may write "compliance-gate ledger:<n>" in the test docstrings; commit bodies stay).
- Task 6: minor (deferred): T6-R1-2 the commit subject and header R6 overstate the guarantee (a hand-written --log summary with code 0-2 is still recorded first); ruling F14's reading stands and goes into the hand-off and the spec rev 3.3 list.
- Task 6: complete (commits 5b16222..e2d3990, review clean)
- Task 6: pushed (e2d3990)
- Task 7: dispatched (BASE e2d3990; workflow wf_e1293bbb-c14; rulings F15, F16 carried)
- Task 7: implemented and reviewed (run wf_e1293bbb-c14): commit 3c49cee; RED isolation 15/17 with the brief's two FAILs; GREEN isolation 17/17; guards ok; suites compliance 327/327, engine 92/92, macro 419/540 + 121 not run, expansion 19/19, ficc 56/56, quant 53/53, all 0 failed — G3-1: Developer Mode variant (brief: 14/17 + 1, 16/17 + 1, 325/327 + 2). Ruling F15 applied ("R8 (compliance-gate ledger:81)"), the same words rewrapped over the same 3 lines to stay within 120 columns. No drift. Review: spec compliant, quality Approved, no findings. Controller check (03:44 KST): stat equals --ignore-cr-at-eol (3 files, +38 -1), LF kept, Co-Authored-By present, isolation 17/17 rerun.
- "KIS token burnt on refusal" (compliance-gate ledger:239) is closed by Task 7 (R8, commit 3c49cee) and leaves the execution carry list.
- Task 7: complete (commits e2d3990..3c49cee, review clean)
- Task 7: pushed (3c49cee)
- Task 8: Steps 1-6 dispatched 03:47 KST (BASE 3c49cee; workflow wf_f085b23f-ea7); Steps 7-9 are the controller's (ruling F1)
- Task 8 Steps 1-6: implemented and reviewed (run wf_f085b23f-ea7): commit bb7bcb7 "test: full run after the compliance follow-up".
  - Step 1: log check printed tasks 1-7 in order, `other after task 4` for d3e2b79 (Task 4's review fix), `missing: none`; compliance suite 327/327, 0 failed, 0 not run, exit 0 (87 s).
  - Step 2 full run (2026-10-29 03:48:16-03:59:05 KST, outside 09:00-09:10): 1055/1176 passed, 0 failed, 121 not run, exit 0; tests 637.5 s (2026-10-24: 609 s), G3-2 recorded. Groups: cockpit 47 PASS, compliance 327 PASS, engine 92 PASS, expansion 19 PASS, ficc 56 PASS, grokteam 17 PASS, macro 419 PASS / 121 NOT_RUN, paper 21 PASS, quant 53 PASS, ui 4 PASS.
  - G3-1 count note: the plan expected compliance 325 PASS / 2 NOT_RUN and full 1053/1176, 123 not run; this PC has Windows Developer Mode on (AllowDevelopmentWithoutDevLicense=1), so compliance_isolation/test_symlinks_are_refused and compliance_tables/test_calendar_sha256_refuses_a_file_symlink run and pass. Without Developer Mode the same tree gives the plan's numbers.
  - Step 4 README cells (ruling F17): compliance row `| 327 PASS |` (was `| 315 PASS / 2 NOT_RUN |`); Total `1055/1176 passed, 0 failed, 121 not run (2026-10-29, TRADEGEN .venv)`. CRLF kept (i/crlf w/crlf), stat equals --ignore-cr-at-eol (2 files, +1066 -1008).
  - Step 6 (2026-10-29 03:59:57-04:00:00 KST): ran — no owner key, TRADEGEN_HOME unset; `owner log: BROKEN: no owner key yet: owner act 1`, `owner log head: entry #0; key fingerprint none`, drafts rules 74894f05e0b7f1af, instruments 50fa819f62707eb5, venues 603e264080f4c69b; `{"code": 3, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}`, `exit 3`, `real ~/.tradegen/compliance unchanged: ()` (guarded with test -n, ruling F19).
  - Review: spec compliant, quality Approved, 0 critical/important. Controller check: record 1176 rows (1055 PASS, 121 NOT_RUN), both files CRLF, Co-Authored-By present.
- Task 8: minor (deferred): T8-R1-1 the implementer waited for the full run with a foreground until-loop instead of the notification (no overlap; record intact).
- Task 8: minor (deferred): T8-R1-2 Step 6's result and the count note are now in this ledger (above).
- Task 8: minor (deferred): T8-R1-3 the README records Developer Mode counts; without it the tree gives 325/2 and 1053/123 — say so in the hand-off and the PR body.
- Task 8 Steps 1-6: complete (commits 3c49cee..bb7bcb7, review clean)
- Task 8 Steps 1-6: pushed (bb7bcb7)
- Final review (Task 8 Step 7): dispatched 04:1x KST over d9f4025..bb7bcb7 (workflow wf_f0fc3a67-cf5: 4 lenses, 2 skeptics per critical/important finding, minor triage; package review-final-d9f4025..bb7bcb7.diff without the generated record)
- Owner merge, recorded late (final review PA-1): PR #2 "Compliance followup" (compliance-followup at 08a67bd, Tasks 1-3) was opened and merged on GitHub by the owner's account xkg4real at 2026-10-29 02:45:30 KST, while Task 4 ran (dispatched 02:40). origin/main is 0e04a24; merge-base(origin/main, HEAD) is 08a67bd. Merging is the owner's choice (G3-3, F1). Consequences: main holds Tasks 1-3 (new guards, loader, table sha 74894f05...) with README and qa records still at 315/2 and 1043/1166 until the rest lands; the closing pull request covers Tasks 4-8 and the fix wave (08a67bd..HEAD); the odds plan still waits for that pull request (R13, F1's Step 9.2), since main is a partial follow-up.
- Final review (wf_f0fc3a67-cf5, 4 lenses + 2 skeptics each + triage; readiness: plan With fixes, security With fixes, tests Yes, consistency With fixes). Confirmed (both skeptics could not refute): PA-1 (above) and FR-1. Refuted to minor by both skeptics: I1 (an import alias of sys.modules or setattr hides a route; a stated limit: from-import aliases, Task 4 brief), FR-2 (a non-blocking crypto-spot ETP row with max_leverage > 1 needs no requires.live, but the gate still refuses the intent).
- Final review: Ruling: FR-1 (important; reproduced 5 ways in both copies: `_f.__globals__["__name__"]`, `typing.cast.__globals__["TYPE_CHECKING"]`, the same plus `from typing import TYPE_CHECKING`, a dict from `gc.get_referents(typing)`, and `sys._getframe().f_builtins["typing"]` after a function-level `import typing`) is fixed in the one fix wave: "__globals__", "f_builtins", "get_referents" and "get_referrers" join the route names, and `plain` and _typing_flag's `from typing import TYPE_CHECKING` test read tree.body (module top level) instead of ast.walk, character-identical in owner.py and sign.py, with the five modules in both synthetic trees — the same binding-free in-module class as T4-R1-1; case 5 shows T4-R1-2's premise ("needs another module") was wrong, so T4-R1-2 is fixed too; no closure file uses these names and every closure typing import is top-level, so the shipped closure is unchanged — if wrong: a module using one of these names has its guarded imports hashed (fails closed).
- Final review: Ruling: T1-R1-1 (triage must-fix; also PA-2, T-2, M1, FR-3a) is fixed in the wave: `(DYNAMIC_NAMES | DYNAMIC_BARE).intersection(names)` with the positive control `from builtins import compile as c`, a stricter departure from Task 1 Edit 9 adding no test row; FR-3 (b, c) and T1-R1-2: the "left to review" comment in tests/compliance_guards.py names breakpoint()/sys.breakpointhook, string annotations evaluated by typing.get_type_hints or inspect.get_annotations(eval_str=True), functools.singledispatch's register, and importlib.metadata through an alias or getattr — comment only — if wrong: none.
- Final review: Ruling: FR-4: core/ficc/data.py's _MEM comment becomes "after the check: a refused put never reaches memory (R8)"; the read path (_cache_get reads and memory-caches <key>.json with no target check; a read, outside A0, like kis_client._cached_token) is a stated limit — if wrong: wording only.
- Final review: Ruling: bare "ledger:<n>" in this branch's code, tests and commit bodies means docs/superpowers/plans/2026-10-23-compliance-gate-execution-ledger.md, as the plan defines it (Appendix A); new citations write "compliance-gate ledger:<n>" (T3-R1-2, T5-R1-4, T6-R1-1, PA-4, T-3, M4 closed by this ruling, no code change) — if wrong: a reader opens the wrong ledger once.
- Final review: Ruling: the stated limits and spec rev 3.3 items the owner and GPT's 2026-10-30 check must read go into the pull request body and here (PA-3, M7, FR-5, M2, T8-R1-3): (a) R4: an attribute store to __class__ also voids every guard (T4-R1-1), and after the fix wave so do __globals__, f_builtins, get_referents and get_referrers, with typing imported at module top only; dunder __setattr__ calls, from-import aliases of route names, getattr by string, another module and names built at run time stay stated limits; (b) R6 per F14: the first recorded fingerprint comes from a summary whose code is 0, 1 or 2 (a --check summary or a hand-written --log summary); (c) R11: a renamed session process under Claude is refused only while claude.exe is still an ancestor; once its launcher exits, the chain cannot be told from the shell's (the walk stays defence in depth behind the passphrase and the typed code); (d) R5: the new walk does not read pid 0's own table entry (the System Idle Process on Windows); (e) R8: ficc _cache_get's read path; (f) README counts come from Developer Mode (325/2 and 1053/123 without it) — if wrong: none, wording.
- Final review: deferred (triage): T1-R1-3, T1-R1-4, T1-R1-5, T2-R1-1, T3-R1-1, T3-R1-3, T5-R1-1, T5-R1-2 (F11), T5-R1-3 (F12), T8-R1-1, T8-R1-2 (done), M2 (stated limit d), M3 (docstrings; the store test's R4 docstring list is updated in the wave), M5 (anchors the odds and E1 executors meet: README cells 327 PASS / 1055/1176/121; their drift rule covers them), M8 (F11). Rulings F1-F21 stand.
- Final review fix wave: dispatched 04:31 KST (BASE bb7bcb7; workflow wf_20a578bc-a25; brief task-final-brief.md: Fix A guards, Fix B closure routes, Fix C ficc comment; one dispatch + one scoped review, no second wave)
- Final review fix wave (run wf_20a578bc-a25): commits 070f697 (Fix A), 014d3b7 (Fix B), 547eaef (Fix C). RED guards 15/16, store 28/29, signer 37/38; GREEN guards 16/16, store 29/29, signer 38/38; guards ok; ficc 56/56; compliance suite 327/327, 0 failed, 0 not run. Fixer checks: no `from builtins import` / `from re import compile` in core; no closure file uses __globals__, f_builtins, get_referents or get_referrers; no `import typing` in the closure, top-level `from typing import TYPE_CHECKING` only in model.py:15 and rules.py:20; HEAD's and the new helpers give identical _guards and _repo_imports on all 342 tracked .py files, so the shipped closure stays at 8 paths (owner.py's text, and so the code hash, moves). Scoped review: spec compliant, quality Needs fixes (one important, plan-mandated). Controller check (04:48 KST): stat equals --ignore-cr-at-eol (6 files, +85 -40), LF kept, Co-Authored-By on all three, guards 16/16, store 29/29, signer 38/38 rerun.
- Final review fix wave: parked — FINAL-R1-1 (important): gc.get_objects() still reaches typing's module dict, so `for o in gc.get_objects(): ... o["TYPE_CHECKING"] = True` keeps the dotted guard trusted — Ruling: no second fix wave (SDD final-review rule); the route list is a denylist by R2-12, so gc.get_objects and any other introspection that reaches a module dict join stated limit (a), and the pull request body names exactly the four route names closed (not "the gc routes" in general); recommended as a one-token follow-up task with its own failing test ("get_objects" in routes, both copies, and `import gc\ngc.get_objects()` in the store test's route loop) before the owner's first code signature — if wrong: a hashed module could hide a guarded import this way until that task lands; the owner's review of each hashed diff (R4's stated limit) covers it, and no closure file imports gc today.
- Final review fix wave: minor (deferred): FINAL-R1-2 the DYNAMIC_BARE inline comment still says "an ast.Name only" (now also an imported name) — fold into the follow-up task above.
- Final review fix wave: Ruling: FINAL-R1-3 the three extra store-test assertions (a function-level `import typing` plus `from typing import TYPE_CHECKING` giving (False, False, True); f_builtins and get_referrers in the route loop) stay — they separate the top-level rule from the f_builtins route and are the only get_referrers coverage; stricter, no test row — if wrong: three redundant assertions.
- Final review: complete (fix wave 070f697..547eaef; 1 parked with ruling)
- Final review fix wave: pushed (547eaef)
- Task 8 Step 7.4 repeat (Steps 1-6): dispatched 04:50 KST (BASE 547eaef; workflow wf_467a3e91-095)
- Task 8 Step 7.4 repeat (run wf_467a3e91-095): commit 2ddfca7 "test: full run after the final review wave" (qa/acceptance_results.json only; README cells unchanged: same numbers and date).
  - Step 1: tasks 1-7 in order; d3e2b79 `other after task 4`; bb7bcb7, 070f697, 014d3b7, 547eaef `other after task 7`; `missing: none`; compliance suite 327/327, exit 0 (04:50:57-04:52:19 KST, 82 s).
  - Step 2 full run (2026-10-29 04:52:31-05:02:46 KST): 1055/1176 passed, 0 failed, 121 not run, exit 0; tests 602.6 s (G3-2). Groups: cockpit 47, compliance 327, engine 92, expansion 19, ficc 56, grokteam 17, macro 419 PASS + 121 NOT_RUN, paper 21, quant 53, ui 4. Same counts as the first pass (the wave added no test row); Developer Mode count note as above.
  - Step 6 (05:03:45-05:03:48 KST): ran — no owner key, TRADEGEN_HOME unset; drafts unchanged (rules 74894f05e0b7f1af, instruments 50fa819f62707eb5, venues 603e264080f4c69b); `{"code": 3, "due": [], "overdue": [], "head_seq": 0, "head_sha256": "", "fingerprint": ""}`, `exit 3`, `real ~/.tradegen/compliance unchanged: ()`.
  - Review: spec compliant, quality Approved. Controller check: record 1176 rows (1055 PASS, 121 NOT_RUN), CRLF, stat equals --ignore-cr-at-eol (1 file, +1009 -1009), Co-Authored-By present.
- Task 8: minor (deferred): T8-R2-1 the report quotes the exit-3 line with an unmarked elision (report text only; the line starts `exit 3: new exposure is blocked`).
- Task 8 Steps 1-7: complete (commits 3c49cee..2ddfca7)
- Task 8 Step 8: the controller copies this ledger to docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md and commits it (Ruling: the ledger kept outside the repo, progress.md:80).
- Ruling: the SDD workspace (.superpowers/sdd/2026-10-24-compliance-followup/, git-ignored) is kept until the owner merges the closing pull request, because the parked FINAL-R1-1 and any review on the pull request need its briefs and reports — if wrong: a few hundred KB of ignored files stay a little longer.
