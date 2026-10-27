# Work in progress: three implementation plans (2026-10-24 to 2026-10-27)

This folder holds the unfinished work behind three implementation plans, so it can be continued from GitHub. Nothing
here is code that runs; every file is plan material. When a plan is finished it is assembled into
`docs/superpowers/plans/<date>-<name>.md` and this folder can go.

> This is research and software design, not legal, tax or investment advice; neither TRADEGEN nor its author is a
> licensed advisor. No plan without a real edge that keeps its floor can beat about 1 in 1,000 (1 in 2,000 with the
> floor at half the stake); the research estimates the practical chance of 1,000x in a month at 0.01% or less.

## The three plans and the order they execute in

1. **Compliance follow-up** (hardening of the merged gate): branch `compliance-followup`. Executes first.
2. **Odds engine** (the second plan of spec rev 3.2): branch `odds-engine`. Executes second.
3. **E1, read-only account inquiry** (the first of three execution sub-projects E1, E2, E3): branch
   `e1-account-inquiry`. Executes third.

Specs: `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` (rev 3.2) and
`docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md` (rev 1, approved 2026-10-24).

## Status when this folder was committed

| Plan | Contract and task scope | Task drafts | What is left |
|---|---|---|---|
| Compliance follow-up | done, critiqued, revised (`followup/`) | all 8 drafted, each reviewed and revised; a consistency pass found 11 issues and fixed all 8 files | controller review of the drafts' open issues (below), then assemble and commit the plan |
| Odds engine | done, critiqued, revised; round-2 rulings folded (`odds/`, 19 tasks) | only `tasks/task_02.md` (written as the spend limit hit; never reviewed) | draft Tasks 1 and 3-18, review, revise, consistency; Task 19 is written at assembly |
| E1 | done, critiqued, revised; round-2 rulings folded (`e1/`, 14 tasks) | `task_01`, `task_04`, `task_08`, `task_09`, `task_11` exist but are NOT verified: 1 and 9 were cut off mid-draft, 4 and 11 were never reviewed, 8 was reviewed (8 issues) but not revised | redraft or verify those five, draft 2, 3, 5, 6, 7, 10, 12, review, revise, consistency; Tasks 13 and 14 are written at assembly |

The drafting stopped on 2026-10-25 around 01:12 KST when the account hit its monthly spend limit (the error named a
weekly reset on 2026-10-27 17:00 KST). No repo code was changed by any of this work.

## What each file is

- `rulings/`: the binding decisions for the contract drafters. `RULINGS.md` and `RULINGS_ROUND2.md` cover the odds and
  follow-up plans; `E1_RULINGS.md` and `E1_RULINGS_ROUND2.md` cover E1. Later files amend earlier ones.
- `map/`: about 400 verified repo facts with file:line evidence (one file per area, merged in `DIGEST.md`, which ends
  with the 32 odds design questions and how they were answered).
- `venues/`: official-docs research on the KIS, Upbit and OKX read-only APIs; each file ends with an independent
  skeptic's "Verification" section, which wins where it says WRONG.
- `followup/`, `odds/`, `e1/`: per plan, `CONTRACT.md` (binding names, signatures, values), `TASKS.md` (scope per
  task and coverage tables), `header.md` (the plan header with Global Constraints), `REVISIONS.md` (critique verdicts),
  and `tasks/task_NN.md` (full task text with code).
- `format-models/`: the compliance plan's own contract, task list and header, used as the format model.
- `workflows/`: the workflow scripts that produced all of this. They hard-code the original local scratch path
  (`.../scratchpad/odds_plan`); point `OP`, `dir`, `rulings` and the map paths at this folder before re-running one.

## Owner decisions these plans encode (all made in chat, 2026-10-24)

Execution split: E1 account inquiry, E2 execution core (arming, permits, reservations, audit log, kill switch, loss
limits, system_halt/disarm, H2), E3 live order adapters (Upbit, then KIS, then OKX), built in that order, each with its
own spec and plan.

E1:
- all three venues may be queried by TRADEGEN processes that Claude starts, KIS included, although a KIS key can trade;
- keys come from the shared `.env`;
- a fetched broker answer lifts its D16 refusal automatically, unsigned, from the next Asia/Seoul day;
- polling while the PC is on, started by a Windows Task Scheduler logon task the owner creates;
- a mismatch shows a Windows toast at once; the 09:05 KST Claude task sends push and email for unsent alerts;
- the code lives in a new top-level `execution/` package, scanned by the guards and inside the signed code hash.

Odds:
- "everything injected": the signed `core/odds/` imports only stdlib, numpy, scipy, `core.isolation` and
  `core.compliance`; garch and other repo pieces are copied with equality tests; bar loading and the S_C3 replay live
  in the unsigned `core/oddsdata/` and are passed in with hashes;
- a `review_by` inside a horizon stops new entries from that date and keeps holdings (not the spec's forced exit);
- crypto venues priced: Upbit (its own KRW candles) and OKX BTC/USDT (Binance BTCUSDT x Upbit KRW-USDT, PROXY_DATA);
  everything else refused until it has its own feed and signed minimums;
- SPECIAL_REGIME: refuse a KRX symbol whose history starts fewer than 60 sessions before the plan start.

## Controller rulings still to make before assembly

- Follow-up Task 4: two routes the closure-scan denylist misses (`sys._getframe().f_globals["__name__"]` and
  `getattr(sys, "modules")["typing"]`): accept as a stated limit, or add `f_globals`/`f_locals` to the routes.
- Follow-up Task 5: the fail-closed ancestor walk refuses 228 of 721 processes on the owner's PC, VS Code terminals
  included; the owner must sign from Windows Terminal opened from the Start menu. Say so in the hand-off.
- Follow-up Task 6 and the others: read each task's open issues in the drafting results before assembly.
- E1 round 2 (E1_RULINGS_ROUND2.md, E1R2-9): KIS inquiry sends nothing until the code is owner-signed. Stricter than
  the approved spec; the owner was told and may overrule.

## How to continue

1. Finish the follow-up: review its open issues, assemble `followup/header.md` + `followup/tasks/task_01..08.md` into
   `docs/superpowers/plans/2026-10-24-compliance-followup.md`, self-review, commit.
2. Draft the odds tasks (groups in the workflow's args: [1], [2,3]->[4], [5], [6], [7]->[8], [9]->[10], [11], [12],
   [15,16], [13]->[14], [17], [18]), then review, revise, consistency, and assemble with a coordinator-written Task 19.
3. Same for E1 (groups [1], [2]->[3], [4], [5,6,7], [8], [9]->[10], [11], [12]; Tasks 13 and 14 at assembly).
4. Each finished plan is then executed with subagent-driven development, in the order above, with a review per task.
