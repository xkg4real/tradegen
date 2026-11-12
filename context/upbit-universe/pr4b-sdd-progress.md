# SDD ledger — plan: docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4b-profile-program.md
Base: origin/main 249cc3d (#24 + #25 merged). Branch claude/universe-pr4b-profile. Spec: docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md (10, 12, 14).
Pre-flight scan (table): <local-path> — 0 real conflicts at 249cc3d-equivalent tree; all 38 anchors match once; plan applied in memory, RED/GREEN reproduce; pins equal today's values.
Ruling N1: Task 3 MODULES edit = append "launch_program" before the closing ) of the last MODULES line, whatever it holds (#23 may land first; MODULES appends exempt per starting session) — cost if wrong: none.
Ruling N2: expected RED rows match by prefix (3.13 ImportError appends " (<path>)") — cost: none.
Ruling N3: Task 3 _OMIT comment reads "strategy._plain leaves it out while None; parse_program accepts the v1 keys or v1 plus all five" (plan text claims _object sees it; it does not) — cost: wording.
Ruling N4: Task 5 AST scan also counts ast.Attribute calls whose attr is rule_terms_digest / economic_rules_digest (closes the alias gap; 0 such calls today) — cost: 2 lines.
Ruling N5: staged LF check after git add (implementer rules already require it).
Ruling N6: PR body names the stricter bounds (L, m, N ints in 1..4096) and that PR 5 pairs kind with revision.
Ruling P1: Task 1 Step 6 updates the profile.py pin in tests/renewal_boundaries.py to the plan's stated value only after the surface diff matches the plan; that is the plan's reviewed value, not regeneration (implementer rule "never regenerate a pin" means never compute-and-paste a new value the brief does not state) — cost if wrong: guard pin mismatch caught by renewal_boundaries.
Ruling O1: 4a and 4b share tests/renewal_boundaries.py (different lines, clean 3-way merge): implement in parallel; the first finished opens; the second opens after the first merges (one-open-PR-per-file; not a MODULES append) — cost: owner wait.
Task 1: dispatched (sonnet, agent aa53f9e82943af962), BASE 249cc3d
Task 1: implemented a1e0d55 (base 249cc3d); review dispatched (sonnet)
Task 1: review (sonnet): spec ✅, Approved, no findings; independent git-archive digest equality for fixture_profile (profile, contract, rule-terms) at 249cc3d vs a1e0d55.
Task 1: complete (commits 249cc3d..a1e0d55, review clean)
Task 2: dispatched (sonnet), BASE a1e0d55
Task 2: implemented 3b2db84 (base a1e0d55); review dispatched (sonnet)
Task 2: review (sonnet): spec ✅, Approved, no findings; independent git-archive protocol_json/evidence_digest equality a1e0d55 vs 3b2db84 (28ea85cb.../8d008761...). Reviewer saw only run tails; implementer's full rows 19/17/14/7 PASS; full suite will re-check.
Task 2: complete (commits a1e0d55..3b2db84, review clean)
Task 3: dispatched (sonnet) with N1, N3 in brief, BASE 3b2db84
Task 3: implemented df63841 (base 3b2db84); implementer skipped RED; controller ran it: old program.py -> 1 PASS + 2 FAIL TypeError (as plan), new -> 3 PASS. Review dispatched (sonnet).
Task 3: review (sonnet): spec ✅, Approved, no findings; independent git-archive digest equality for trend + cash fixtures (plain/program_digest/parameters/program_json/evidence) 3b2db84 vs df63841; bool refused for L/m/N; _OMIT line verified verbatim by controller.
Task 3: complete (commits 3b2db84..df63841, review clean)
Task 4: dispatched (sonnet), BASE df63841
Task 4: implemented caef4d3 (base df63841), RED ImportError ChooserSlot, GREEN 13/13; review dispatched (opus)
Task 4: review (opus): spec ✅ (rules 1-8 order/text, exact Fraction, lag top_n/flags never read, cash->cash counts); Important: rule 5 test cannot separate rule 6 (r_best +0.5). Minors: flag values unchecked (fail-open on rule 1 sale); lag-not-read unpinned; held off top-N with defined r untested; index refusal list misses PROGRAM_DECIMAL_RANGE (doc, left).
Ruling F1: chooser refuses flag values outside the five FLAG_CLASSES (PROGRAM_CHOOSER_INPUT_INVALID) via a local _FLAG_CLASSES constant pinned in a test to core.compliance.rules.FLAG_CLASSES — fail closed at a trust boundary (PR 4d builds slots from recorded history rows whose shape check is type-only) — cost if wrong: a valid slot refused, caught by PR 4d tests.
Task 4: fix round 1 dispatched (resume implementer): items 1-4.
Task 4: fix round 1/5 (4 addressed + non-str flag refusal; commit 01a4acf); scoped re-review dispatched (sonnet)
Task 4: re-review (sonnet): Approved; all 4 addressed; mutation (rule 6 above 5) fails test_rule_5; empty flags + all 5 classes accepted; launch_guards 17 def tests stable (PR 2 added one; the 15 was a miscount).
Task 4: complete (commits df63841..01a4acf, 1 fix round, review clean)
Task 5: dispatched (sonnet) with N4 in brief, BASE 01a4acf
Task 5: implemented 592de76 (base 01a4acf); RED 11 AST sites + WorkflowError + RenewalError; study.py CR 690->692; launch_runner unknown_send test tripped real-home guard once (same 02:51 owner.jsonl write), PASS alone. Review dispatched (opus).
Task 5: review (opus): spec ✅, Approved; per-site selectors correct; _bound_profile probes refuse both cross-forms; renewal tick-in-universe ok, fee refused before registry write; study.py CRLF ok. Minor fixed by controller: cross-form refused pairs with matching digests (mutant without the sha element now FAILs) -> fbd48db. Minor left: driver/runner/review_request/study_review bind digests only (spec asks no more).
Task 5: complete (commits 01a4acf..fbd48db, review clean)
Final review: dispatched (opus) 249cc3d..fbd48db
Main moved 2026-11-12: #23 merged -> origin/main 0962e94 (4 files: floor-state-check plan, launch_acceptance MODULES last line, launch_floor_state_check test, tools/floor_state_check.py). Owner code-approved 0962e94 (02:51 KST owner.jsonl write = that signing; hash 1660e1db..., per TRADEGEN_GITHUB). Plan: rebase onto 0962e94 after the final review (4b: MODULES conflict per N1, keep both entries), then guards + full suite on the rebased head. PR body: this PR's merge makes the 0962e94 code-approve stale.
Rebased 2026-11-12 onto origin/main 0757542 (#26 clock-check merged): only conflict tests/launch_acceptance.py MODULES last line, kept both (launch_floor_state_check, launch_clock_check, launch_program). New head 7778847 (9fbefff 8749777 111e98a e5e095b 522c37f 956d397 7778847). diff --stat = --ignore-cr-at-eol (18 files +578/-37). tools/clock_check.py, tools/floor_state_check.py: no digest calls. Commit identity unchanged (same as merged PRs).
Final review: earlier dispatch on 249cc3d..fbd48db superseded; fresh final review (opus) dispatched on 0757542..7778847
Full suite attempt 1 on 7778847: aborted at start, OpenBLAS memory allocation failed (PC commit charge: 0.7 GB free RAM, 1.2 GB free virtual; reviewer + 4a implementer tests running). Not a test result. Ruling: rerun the full suite after the final review and 4a T3 finish, with OPENBLAS_NUM_THREADS=1 — cost if wrong: ~1 h later PR.
Final review (opus) on 0757542..7778847: Ready to merge Yes; 0 Critical, 0 Important, 5 Minor (report final-review-report.md). Independent digest equality base vs head, 200k-case chooser cross-check 0 mismatches, 16 pins match. Ruling: fix M1 (non-str top_n coin -> PROGRAM_CHOOSER_INPUT_INVALID) and M3 (docstring) myself, RED seen then GREEN (launch_program 15, strategy 19, profile 18, renewal 3, launch_guards 17) -> 23abca9; no re-review (4-line diff, verified by RED/GREEN) — cost if wrong: a reviewer would catch it in the PR. M2 (scan scope), M4 (PR 4d adds driver equality) left; M5 handled in PR body (name the head actually code-approved).
Full suite (OPENBLAS_NUM_THREADS=1) on 23abca9: 2521/2648, 4 FAIL (2 checkout-location, owner_ops pre-existing, launch_coordinator close_while_awaiting_timer 1.5 s timing under load — PASS alone), 123 NOT_RUN REFDATA/OWNER/POSIX. qa restored. Rebased onto origin/main a456ea8 (#27, #28 docs only, no overlap) -> 5d70e72. PR #30 opened 2026-11-12, bound; TRADEGEN_GITHUB notified.
PR #30 follow-up: starting session's pre-merge review (2 of 3 skeptics) found rule 3 test did not pin the top-N filter; fixed cc571fe (ZZZ unflagged + lag price), mutant 'for coin in now_slot.prices' FAILs rule 3, launch_program 15/15; pushed. Test-only.
PR #30 was MERGED by the owner as 3868cde (head 5d70e72) before cc571fe was pushed; cc571fe is on the merged branch only. Ruling: cherry-pick cc571fe into PR 4a when 4a rebases onto 3868cde (test-only, launch_program.py not otherwise in 4a) and name it in the 4a body — cost if wrong: owner may prefer a separate PR.
