# Upbit KRW universe implementation — status (session universe-impl)

Scratch clone: <local scratch clone tgu>
(PR 1 worktree: <scratch>/tgu-pr1). SDD ledgers under each worktree's `.superpowers/sdd/<plan>/progress.md`.

## Overlap note received 2026-11-11 (from the starting session)
- Universe lands first in shared files; execute plans as written. If PLB code reaches main before a universe PR,
  apply the overlap note's section 1 amendments (PR 4a Steps 1/6 + counts, PR 4b Tasks 1/2/5, PR 4d Task 3
  quantities, PR 5 Tasks 4/5/8) and re-map citations by content.
- Before each PR touching a shared file: `gh pr list`; never two open PRs on one shared file.
- Every code PR body: code unsigned until both lines are merged; owner signs nothing until then except the
  2026-12-02 rules re-review.
- Full overlap JSON (read-only, local only): <starting session scratchpad>/overlap_result.json

## Progress
- PR 0 (driver pin): MERGED by the owner as #20 (main 59a4eb8, with #18 PLB spec and #19 universe plans).
- PR 1 (compliance pure): OPEN as #21 (head 0e94df7), 8 commits, final review clean, full suite 2425/2551, 3 FAIL
  all pre-existing on main (2 checkout-location + flaky launch_owner_ops worker test). Two tightening rulings: every
  receipt read after D 00:00 UTC; verify requires encode's receipt order. TRADEGEN_GITHUB notified 2026-11-11.
- PR 1 MERGED as #21 (df9118c); docs #22 merged (main 6d9bf56).
- PR 2 (worktree tgu-pr2) and PR 3 (worktree tgu-pr3) running in parallel from 6d9bf56 (disjoint files).
  Rulings: PR 3 C1 amends test_history_maps_serve_exits_only (first `gone` row -> ALLOW_EXIT close_long, spec 8);
  PR 2 daily_bars also refuses a candle row of another market. PR 4b waits for PR 2 + PR 3 (shares profile.py,
  renewal_boundaries.py, launch_acceptance.py).

## Owner decision relayed 2026-11-11
- Owner answered "Universe first": shared files take universe code first, PLB code after; PLB plan is written against main after universe PR 5 merges. Keep the gh pr list check anyway.

## Pre-flight scans (vs PR 1 head 0e94df7)
- PR 2: scratchpad/pr2-preflight.md — 0 blocking; Task 2 Step 2 / Task 5 Step 2 expect ModuleNotFoundError but get ImportError (row still FAILs); reviewer to check: daily_bars does not check each row's market; no UNIVERSE_NOT_FINAL test.
- PR 3: pr3-preflight.md — C1: Task 2 breaks tests/compliance_gate.py test_history_maps_serve_exits_only (held USDT sell on upbit, no map/history → now ALLOW_EXIT via derived coin, per spec 8 'whatever the venue facts say'); needs a ruling to amend that test keeping its intent. C2: _screen anchor 'inst = _lookup(...)' is a substring of grey_rows' 8-space line.
- Cross-PR hazard noted 2026-11-12 (PR 2 final review): PR 4e odds_batch reads daily_bars after taking now; PR 4a _CLOCK_AGE=30s may refuse the batch for >=3 coins (~19 GETs/coin). Re-check in PR 4a/4e.
- Note for PR 4a: plan cites core/odds/plan.py:301; after PR 3 it is :302 — cite by text.
- 2026-11-12: PR 2 ready (8c9a311, suite 2451/2577, 3 pre-existing FAIL) but HELD: open PR #23 (floor-state-check) edits the same MODULES closing line of tests/launch_acceptance.py; asked the starting session (a) wait+rebase or (b) open now with a note. PR 3 shares no file with #23; its guards + suite running (b1wkx3rz4).
- PR 2 OPEN as #24 (head 8c9a311) per the starting session's ruling (b): MODULES registry appends are exempt from the one-open-PR rule; body names #23; second to merge rebases (if #23 first: rebase #24, keep both, re-run launch_guards + launch tests, push). TRADEGEN_GITHUB notified 2026-11-12.
- PR 3 OPEN as #25 (head 6eed8b8), 8 commits, reviews clean, full suite 2450/2575, 2 FAIL checkout-location; no file shared with #23/#24. TRADEGEN_GITHUB notified 2026-11-12.
- Next: PR 4b after #24 AND #25 merge (shares profile.py, renewal_boundaries.py, launch_acceptance.py); then 4a (needs PR 3), 4c, 4d, 4e, 5.
- 2026-11-12: owner merged #24 (c213ed0) and #25 (249cc3d). main 249cc3d == local premerge tree. Worktrees tgu-pr4a (claude/universe-pr4a-control) and tgu-pr4b (claude/universe-pr4b-profile) from 249cc3d; pre-flight scans running.
- 2026-11-12: pre-flights done. 4b: 0 conflicts (pr4b-preflight.md). 4a: C1 test counts +1 (PR 3 added two controller tests), C2 fixtures anchor (pr4a-preflight.md). Hazard 5 verdict: PR 4e must take now AFTER read_bars (~51+ GETs for N>=3 coins breaks the 30 s _CLOCK_AGE), refuse if the Seoul date changed, pass the new now; PR 4e test at P3008 changes. 4a/4b share only renewal_boundaries.py (lines 32/35): parallel implementation, sequential PRs. Both Task 1s dispatched.
- 2026-11-12 ~03:10 KST: #23 merged (main 0962e94). Owner code-approved 0962e94 (owner.jsonl write 02:51 KST explained; it tripped the real-home guard in two implementer runs). 4a/4b branches (base 249cc3d) get rebased onto 0962e94 before suites; 4b resolves the MODULES line keeping both entries. PR bodies must say merging makes the 0962e94 code-approve stale.
- 2026-11-12 ~10:10 KST: 4b rebased onto main 0757542 (#26 merged; only the MODULES line conflicted, kept all three). Final review (opus): Yes, 0 Critical/0 Important/5 Minor; two Minors fixed (non-str top-N coin refused, docstring) -> 23abca9. First full-suite try aborted at start on OpenBLAS out-of-memory (PC ~0.5 GB free RAM; many sessions open); rerunning with OPENBLAS_NUM_THREADS=1. PR 4b opens after that run. 4a: Task 3 done (1b02867, review clean); Task 4 (universe_odds) dispatched.
- 2026-11-12: PR 4b OPEN as #30 (head 5d70e72 on main a456ea8). Full suite on the same code 2521/2648, 4 FAIL (2 checkout-location, owner_ops pre-existing, coordinator 1.5 s timing under memory load, PASS alone). TRADEGEN_GITHUB notified. 4a: Tasks 1-4 done (Task 4 5607f43 + registry snapshot fix 860f00b); Task 5+5b implementer resumed after a stream stall. 4a opens only after #30 merges (shared tests/renewal_boundaries.py).
- 2026-11-12 OWNER RULING (approved option a) — PR 4e plan change: universe_odds.run_batch no longer reads the account provider (it called the coordinator's non-reentrant ContinuousAccountProvider off the work lock: could fail the worker's tick and commit a baseline advance on refusal). New signature run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof); positions_asof <= now and started - positions_asof <= 30 s else UNIVERSE_BATCH_POSITIONS_STALE. PR 4e odds_batch must pass the coordinator's last observation (self._observation.positions / .asof, as Coordinator.prepare does), still off the work lock, and its fake run_batch test must take the new kwargs. Also in the 4a fix wave: no-batch upbit prep of an unmapped coin refuses SESSION_UNIVERSE_BATCH_REQUIRED; kill with an invalid reason journals 'reason_invalid'.
- 2026-11-12: #30 (PR 4b) MERGED as 3868cde. The rule 3 top-N test fix from the starting session's pre-merge review (cc571fe) landed on the branch after the merge, so it is not on main; it rides in PR 4a (cherry-picked when 4a rebases onto 3868cde). 4a final fix wave (option a) in progress; then rebase onto 3868cde (renewal_boundaries.py lines 32/35), full suite, open.
- PR 4e brief corrections (starting session's ruling, 2026-11-12): Coordinator.odds_batch reads self._observation ONCE WITHOUT taking the work lock, even briefly (the 4e test test_the_odds_batch_runs_off_the_work_lock_over_the_snapshot_top_n holds c._work on another thread, ~P3004; any lock hangs it); refuse with a coordinator code if the observation is None or older than ACCOUNT_AGE; pass positions=observation.positions, positions_asof=observation.asof. In that test the fake run_batch gains the two kwargs and one assert checks they are the last observation's values. Anchors: 4e plan P2977 (Consumes), P3001 (fake), P3129 (call). PR 4a also updates docs/superpowers/plans/2026-11-11-upbit-krw-universe-index.md (~line 188) run_batch signature.
- OWNER INSTRUCTION 2026-11-12 (to universe-impl): when universe PR 5 is merged into main, SendMessage to local_597dbe11-9cd4-4fd6-8f04-6c9e741d8a1b: '유니버스 PR 5 병합 완료: <PR number>, merge <commit>'. That session then opens the 1 s allowance code PR from docs/pc-clock-decision-2026-11-12.md.
- 2026-11-12: PR 4a OPEN as #32 (head 56a0b7f on main 3868cde; 14 commits incl. #30's rule 3 test fix and the index run_batch line). Full suite 2547/2672, only the 2 checkout-location FAILs. TRADEGEN_GITHUB notified. Next: PR 4c (needs PR 2, PR 3, PR 4b: all merged).
- 2026-11-12: #32 body corrected per TRADEGEN_GITHUB: NO per-PR code-approve; one code-approve after all universe PRs + loss-budget code (owner 11-11); TRADEGEN_PR9 stays at 0962e94 (signed, --check OK); per-head approve only to run an intermediate head. Use this wording in the 4c/4d/4e/5 bodies.
- 2026-11-12: owner MERGED #32 (PR 4a) as 971a538 (and #31 docs as dc8a039). Usage at 98% weekly: work handed to GPT via the handoff branch (context/upbit-universe). PR 4c pre-flight was stopped unfinished; worktree tgu-pr4c has no commits.
