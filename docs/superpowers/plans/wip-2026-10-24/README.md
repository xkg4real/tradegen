# The parts behind three implementation plans (2026-10-24 to 2026-10-28)

All three plans are finished and assembled. Each is self-contained (header, tasks, and its contract as Appendix A)
and wins over the parts in this folder:

- `docs/superpowers/plans/2026-10-24-compliance-followup.md` (8 tasks) and its `-repo-map.md`;
- `docs/superpowers/plans/2026-10-24-odds-engine.md` (19 tasks) and its `-repo-map.md`;
- `docs/superpowers/plans/2026-10-24-e1-account-inquiry.md` (14 tasks) and its `-repo-map.md`.

This folder is kept as the record of how they were drafted, reviewed and ruled. Nothing here is code that runs, and it
can go once the three plans have executed.

> This is research and software design, not legal, tax or investment advice; neither TRADEGEN nor its author is a
> licensed advisor. No plan without a real edge that keeps its floor can beat about 1 in 1,000 (1 in 1,999 with the
> floor at half the stake); the research estimates the practical chance of 1,000x in a month at 0.01% or less.

## The three plans and the order they execute in

1. **Compliance follow-up** (hardening of the merged gate): branch `compliance-followup`. Executes first.
2. **Odds engine** (the second plan of spec rev 3.2): branch `odds-engine`. Executes second.
3. **E1, read-only account inquiry** (the first of three execution sub-projects E1, E2, E3): branch
   `e1-account-inquiry`. Executes third.

Specs: `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` (rev 3.2) and
`docs/superpowers/specs/2026-10-24-e1-account-inquiry-design.md` (rev 1, approved 2026-10-24).

## Status (2026-10-28)

| Plan | State |
|---|---|
| Compliance follow-up | assembled 2026-10-27 (`48f4004`); the push-as-you-go rule (G3-3) added 2026-10-28 |
| Odds engine | Tasks 1-18 drafted, reviewed, revised; a consistency pass (15 findings, all fixed); Task 19 written and reviewed at assembly; a final two-lens review of the whole plan (9 issues, all fixed) |
| E1 | Tasks 1-12 drafted, reviewed, revised; a consistency pass (12 findings, all fixed); Tasks 13 and 14 written and reviewed at assembly; a final two-lens review (11 issues, all fixed) |

None of the plans has executed yet, and no repo code has changed. The drafting paused on 2026-10-25 at the account's
spend limit and resumed on 2026-10-27.

## What each file is

- `rulings/`: the binding decisions for the contract drafters. `RULINGS.md` and `RULINGS_ROUND2.md` cover the odds and
  follow-up plans; `E1_RULINGS.md` and `E1_RULINGS_ROUND2.md` cover E1; `RULINGS_ROUND3.md` rules on the drafts' open
  issues for all three. Later files amend earlier ones.
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

## Controller rulings

Every open question is ruled. `rulings/RULINGS_ROUND3.md` (2026-10-28) holds G3-1 to G3-5 for every plan, O3-1 to
O3-22 for the odds plan and E3-1 to E3-8 for E1; each either refuses more or fixes which task owns a piece of work, and
none loosens a check. The follow-up's two earlier questions are settled in its plan (the closure scan covers
`f_globals`; the owner signs from Windows Terminal opened from the Start menu). E1R2-9 (KIS sends nothing until the
code is owner-signed) stands; the owner may overrule it.

## How to continue

Execute the plans with subagent-driven development, one branch and one pull request each, in this order: the
compliance follow-up (`compliance-followup`), then the odds engine (`odds-engine`), then E1 (`e1-account-inquiry`).
The controller pushes each branch after every reviewed task (G3-3); merging each pull request is the owner's choice.
