# Revisions to the follow-up drafts (CONTRACT.md, TASKS.md, header.md)

## Round 1 (2026-10-24): adversarial critic of the follow-up contract

Each issue was re-checked in `sandbox_reviser/` (read-only on the repo): `make_r2.py`/`make_r2b.py` + `probe_cli_fix.py`,
`probe_d16.py`, `probe_flips.py` (C4), `make_r4.py` + `probe_r4b.py` + `probe_tamper.py` (C6), `walk_c71.py` (C7),
`make_r1.py` + `probe_r1.py` (C3).

| # | Issue | Verdict | Reason |
|---|---|---|---|
| 1 | blocker: `{cap}`-only-in-grey breaks tests/compliance_cli.py:576-577 | fixed | Reproduced (KR-KIS-US-OPTION Invalid). Now the third R10 rewrite (`{cap}` on the grey row only, VALID in the dry run); R10, C2, C4.4, header R10 and File map, TASKS Task 2 and Coverage updated; Task 2 verifies `compliance_cli/` 35/35. Counts unchanged. |
| 2 | blocker: the walk stops at a process named winlogon.exe and misses a claude.exe above it | fixed | Reproduced (today True, draft False). The walk now goes on to pid 0 or a break, and a break returns `not rooted`. Every C7.3 case passes, plus a new renamed-root case (True). R5, R11, C7.1-7.3, header, TASKS Task 5 and sign.py:3 updated. |
| 3 | major: D16 by content misses an ETP-asset row with no class axis | fixed | Reproduced (allow row on asset krx_etp VALID). With no class key, check 4 counts an ETP asset as matching `etp_leveraged` and `etp_single_stock`, not all four D16 classes, so the reason does not name elw or krx_derivative. Shipped table VALID; rules.py +31 lines; two cases and a class-axis control added. |
| 4 | major: R4 misses attribute stores, setattr, globals(), sys.modules | fixed | Reproduced. In a module with any such route `_guards` trusts no guard, the bare TYPE_CHECKING one included (`typing.TYPE_CHECKING = True` before `from typing import TYPE_CHECKING` also hid an import). Real closure unchanged; no closure file uses a route; 5 synthetic files m-q added; the limit is stated. |
| 5 | major: the comment says pstats/tracemalloc open nothing | fixed | Confirmed (Snapshot.load unpickles; Stats/dump_stats use marshal). The comment, R1, header R1 and TASKS were corrected. The ruling (no ban) is kept and raised as an open issue. |
| 6 | minor: the `importlib.<attr>` route after `import importlib.metadata` | fixed | `_dynamic_hits` flags any attribute of the Name `importlib` except `metadata`. No hit in core/compliance (also on the R2/R4 copies). Three positive controls and one `importlib.metadata.version` negative added; the alias limit is stated in R9. |
| 7 | minor: the not-in-scope list is incomplete | fixed | Checked against map/followup.md section 8. Added the ACCEPT lines (:84 ... :205), execution :144/:150/:157, odds :68/:101, the rest of :233, a "closed" bullet (:74, :75, :80, :133, :145, :242, ...), the three DIGEST 8.2/8.4 limits, and an "every other line keeps its class" clause, in C11, TASKS and header. |
| 8 | minor: odds allowlist via a raw prefix drops importlib.metadata | fixed | Confirmed against odds/CONTRACT.md:89-94. C3.10 and C12 say the odds guards use `_dynamic_module`. |
| 9 | minor: the C6.1 docstring line is 123 characters | fixed | Docstring rewritten (issue 4). Every new code line is 120 or fewer (checked by awk and in the sandbox copies). |

## Round 2 (2026-10-24): controller rulings RULINGS_ROUND2.md R2-10 to R2-13

Checked in `followup/sandbox_round2/` (read-only on the repo): `make_and_probe.py` builds a copy of
tests/compliance_guards.py with the new C3.3 block and the C3.4 functions and runs it with `python -I -B`.
`git diff --stat 995534b 5816d3c -- . ':!docs'` prints nothing; the only commit since `995534b` adds
`docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md`.

| Ruling | Change | Where |
|---|---|---|
| R2-10 pstats and tracemalloc banned | `DYNAMIC_MODULES` 27 -> 29 entries (`pstats`, `tracemalloc` appended after `idlelib`). The comment now says they load files (pstats.Stats with marshal, tracemalloc.Snapshot.load with pickle) and that faulthandler stays allowed. New positives `import pstats`, `from pstats import Stats`, `import tracemalloc`, `from tracemalloc import Snapshot`; both modules were dropped from the second negative control, which keeps traceback, faulthandler, logging and `re.compile`. The open issue of round 1 (#5) is closed. Dry run: 29 distinct entries, every entry in every import form is a hit, the negatives are clean, no hit in core/compliance, core/odds or the R2/R4 sandbox copies, longest line 120. Test counts unchanged (16/16). | CONTRACT R1 (header, DYNAMIC list, controls, scope note), C3.3 (old text now quoted with its anchor; new block; dry-run note), C3.6, C12; header Spec intro, Global Constraints (29 dynamic modules), R1; TASKS Task 1 (constants, positives, failing-first list), Coverage F1 row |
| R2-11 branch base | Task 1 branches from main's HEAD at execution time, not from `995534b`. It first checks on `main` that `git status --short` and `git diff --stat 995534b HEAD -- . ':!docs'` print nothing, and stops and reports if either prints. The repo line now says the plans are written against `5816d3c`, equal to `995534b` outside docs/ (the cited docs files are unchanged too). | CONTRACT preamble, C0 branch bullet, R13; header Global Constraints, R13; TASKS Task 1 first bullet, Coverage (new row) |
| R2-12 R4 denylist limit | The R4 stated limit is marked as accepted as stated and names the route list a denylist. Nothing else changed. | CONTRACT R4; header R4; TASKS Task 4 "State the limit", Coverage (new row) |
| R2-13 DRIFT RULE | Added to C0 (and so to Global Constraints) and to the header's Global Constraints as its own block. Each Edit is an exact old/new pair quoted from `5816d3c` and names its anchor; cited line numbers are those of `995534b` and the anchor wins, including when earlier tasks of this plan move lines (Task 2 before 3 and 6, Task 4 before 5); re-read before each Edit; if text drifted because of an earlier plan, apply the same change, keep the earlier behaviour, write one ledger line; stop and rule if the change no longer makes sense. C12 now says the odds and E1 plans carry the rule for every file this plan changes, and that this plan renames no name they anchor on. Anchors were added where a section lacked one (C3.3 old text, C5 the `KR-KIS-KRX-DERIV` row). | CONTRACT C0, R13, C3.3, C5, C12; header Global Constraints, R13; TASKS legend, Coverage (new row) |
| (not follow-up) R2-1 to R2-9 | Odds plan only; not folded here. | - |

Cross-plan note (not edited here): odds/CONTRACT.md's prose list of the F1 additions (the "no import of
`importlib.util`, ..." bullet, about line 97) lacks `pstats` and `tracemalloc`. The odds guards read the lists from
tests/compliance_guards.py at test time, so the code is bound either way.

## Round 3 (final assembly): controller amendments and rulings

Checked in `followup/sandbox_assemble/` (read-only on the repo): `verify_t4.py` applies task_04.md's Edits T0-T5 and
O1-O3 to scratch copies of the four repo files (each old text occurs once), prints `git diff --no-index --numstat`,
and probes the old and new helpers on the synthetic sources and the real closure files.

| # | Amendment / ruling | Change | Where |
|---|---|---|---|
| 1 | C12 numbers and two bullets | `minimum_krw` :633 moves to about :739; the store helpers move down by 43 lines (`_pubkey_at` 247 -> 290). The controller's 38 / 285 predates the two frame modules of ruling 5 (+5 lines; numstat +44 -1 on the store test). New bullets: the `_T5_PINNED` pin rule, and the R4 TYPE_CHECKING advice for core/odds and execution/. Heading now "Effects on the odds and E1 plans". | CONTRACT 12 |
| 2 | C3.10 `_suite_names` | Bullet added: used by the E1 plan's registration test; name and signature fixed. | CONTRACT 3.10 |
| 3 | C7.2 help pin | "No test pins the help text" replaced by "test_help_names_owner_acts_1_and_2 pins help needles; Task 5 adds the two new ones"; Task 5's departure line no longer calls 7.2 wrong. | CONTRACT 7.2; task_05 |
| 4 | Commits and departures | File map ledger row "commit only (Task 8 Step 8); the executor writes it"; "Commit once per task (Task 8: the full-run record, the ledger, and a repeat record after a review fix wave)" in Global Constraints and C0; TASKS Task 8 lists the ledger commit and the optional repeat record; TASKS Tasks 4, 5, 6 and Coverage F4/F5/F6 name what each task adds beyond the contract (the three task files already had their "Departures from Appendix A" lines). | header; CONTRACT 0; TASKS |
| 5 | Ruling: frame routes | `f_globals`, `f_locals` join `_guards`'s route set (one Edit O1 text, applied to owner.py and sign.py alike, so the copies stay identical; the verify script confirms all seven helpers identical). Synthetic modules r.py (`sys._getframe().f_globals["__name__"]`, `__main__` guard) and s.py (`f_locals["TYPE_CHECKING"]`, bare guard) and targets `core/frame_main.py`, `core/frame_bare.py` in both synthetic trees: today's helpers hide both targets, the new ones hide neither. No closure file names either; the real closure keeps its guards. Stated limit rewritten: the frame route is closed; `getattr(sys, "modules")["typing"]` stays (getattr: gate.py, model.py, rules.py, alerts.py, owner._binds). Step 2/3 expectations updated (twelve targets; owner.py and sign.py +32 -12, store +44 -1, signer +41; 149 insertions, 25 deletions); Task 5's sign.py shift is now 20 lines. | task_04, task_05; CONTRACT 1 (R4), 6.1, 6.4; header R4 and Spec; TASKS Task 4, Coverage F4 |
| 6 | Ruling: cockpit test_21 | Task 8 Step 2 and Task 7: test_21 makes a read-only KIS quotation call when KIS keys are set, as every earlier full run did; accepted; no key check added. | task_07, task_08; TASKS Task 8 |
| 7 | Rulings: accepted limits | Task 6 fingerprint window, Task 7 token read path, Task 5 VS Code refusal (Windows Terminal from the Start menu) added to the header's Spec list; Windows Terminal also in the header's owner gates and Task 8's hand-off; Task 6 window also in Task 8's "What to expect". | header; task_06, task_07, task_08; TASKS |
| 8 | Names | References use Appendix A / round-2 ruling / odds ruling ids; the header defines F1-F8, R2-10 to R2-13, O1, O2, O3, O5; no scratch file names remain in the assembled plan. | all tasks; CONTRACT; header |
