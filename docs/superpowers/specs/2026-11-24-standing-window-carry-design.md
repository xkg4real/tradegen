# Standing window carry (M7-T12): one window per standing deployment

Date: 2026-11-24 (Asia/Seoul).
Status: draft for owner review. It designs how a standing deployment keeps the app's position across its window
boundaries, as the owner decided on 2026-11-24 (O33 Q1 b). It builds on section 3.2 of
[amendment A2](2026-11-24-standing-amendment-a2-design.md) ("A2", PR #74). Nothing is implemented. Merging this
document approves the design only. It signs nothing, arms nothing and sends no order. It changes no code, no signed
table and no `tools/signer/sign.py`. It edits no other document, but if the owner chooses C1 (a) it supersedes the SD
and PH lines listed in 3.0 for fixed carry standing schedules. Where they differ, this document then wins. If the
owner merges it unchanged, each decision of section 7 takes its recommended option, as PLB:7 does, except C3, which
stays open until `p` is measured (3.7). The already approved policies that section 7 names are not choices.

**Citations.** `path:line` is rev `b828b2d` (main). PH, SD, CL and B1 are the documents A2 names, at the same line
numbers A2 cites; A2 only appends to existing lines. A2's own lines are at PR #74's head `91465e5`. PLB is
[principal loss budget](2026-11-11-principal-loss-budget-design.md). All of them are under `docs/superpowers/specs/`.
`launch.py` is `tools/owner/launch.py`. Other code paths are under `execution_launch/` unless they say otherwise.

**Scope.** The fixed carry path only (factory `tradegen-fixed-carry-v2`). The universe profile waits for M7-T11 and
its own carry design (A2 3.14, A2:365). Owner financial parameters stay private and are not written here. This is
software design, not legal, tax or investment advice.

## 0. The proposal in one paragraph

A standing deployment of a fixed carry profile runs as one deployment window. The window ends no later than the review's
expiry and the newest standing entry's `valid_until` (C6), so its end is the deployment's end. That makes it a little
under 7 days at most. Inside it there is no window boundary, so nothing has to be handed from one window to the next.
The carry driver already holds through its window without an end-slot sale (`managed_behavior.py:55-65`), and its
history keeps every mark of the window (`live_history.py:591-592`). The first-bar flat check stays, and runs once, at
the deployment start. The evidence is a carry study whose span is at least the deployment's span. The interface shared
with M7-T9 is a position record that the app writes whenever a deployment ends or stops while the app holds units. W1
pays for this with a full restart after every stop: a new review signature, a new `standing_armed` and a flat start, so
a coin held at the stop must be sold first or wait for M7-T9. Chained windows with carried history (W2, section 5) avoid
the new review signature, and the sale too if section 5's held start is built, but still need a new `standing_armed`, at
a much larger cost in code and evidence. Two prerequisites apply to any multi-day window: the time a late slot takes and
the completion odds of a long study. A third applies to all live use, on any route: the control journal fills after
about 11 operating days in total (3.7, M7-T13).

## 1. What the code does today

| # | Fact | Evidence |
|---|---|---|
| 1 | The carry driver never sells for its window end. At the deadline an exit is blocked and approval is requested. | `managed_behavior.py:55-65`, `253-256`; `driver.py:564-566` |
| 2 | A window's first bar must hold zero units and exactly the protocol's initial cash. | `driver.py:487-489`; PLB-O2 relaxes the cash part to `>= C` (PLB:339) |
| 3 | A window's history starts empty at its own start. Bars are indexed from `window.start`, and a journal is created only before the window starts, over a head at GENESIS. | `driver.py:383`; `live_history.py:892-896` |
| 4 | At the first bar there is no decision and the driver holds. Until `slow_window` marks exist, the decision is warmup, and the carry intent has no branch for it, so the driver holds: no buy and no sell. | `driver.py:417-420`, `494-498`; `managed_behavior.py:202-203`, `244-252` |
| 5 | The carry history keeps every mark of the window, not only the last `slow_window`. | `live_history.py:591-592` |
| 6 | A window has at most 20,000 bars; 7 days at 300 s is 2,017. Three places on the live path cap a fixed window at 24 h and a universe window at 72 h: the owner tool's window reader, `setup_history` and the driver composition. A fourth, in the sealed research selection, is off the live path (3.1). | `driver.py:237-238`; `launch.py:113`, `175-179`; `coordinator.py:1492-1493`; `sealed_study_review.py:189` |
| 7 | A review approves one driver identity, which includes one window digest, for at most 24 h. Review body schema 2 already means carry. The runner checks the review at every tick, sells included. | `review_auth.py:32`, `39-42`, `85-88`, `113-115`; `runner.py:229-238`, `640-641` |
| 8 | The carry study starts flat and marks its inventory at the end; it invents no sale. The legacy study sold at its last bar. | `carry_evaluator.py:6-7`, `208`, `231`; `strategy.py:391-393` |
| 9 | Preparation is refused while the app holds units. Sells need no session and continue. | A2 3.10 (A2:323); PLB:283; SD:149-150 |
| 10 | The account anchor is the whole account's holding of the symbol. App units (BR-23, B1:417) come with M7-T3. | `live_history.py:563-566` |
| 11 | All end-of-window handling is keyed to `window.end`: the carry deadline, the deadline record, and the protective policy's `holding_deadline`. | `driver.py:655-660`; `runner.py:509-520`; `coordinator.py:202`, `872` |

**So today two windows in a row cannot hold across their boundary.** Window `k + 1` refuses a held first bar (fact 2).
If only that check were relaxed, window `k + 1` would start in warmup (facts 3 and 4). For `slow_window` bars the
strategy could then neither top up nor exit, and only the protective rules could sell.

## 2. Two shapes

- **W1, one window per standing deployment (recommended).** The schedule has one window, as long as the deployment.
- **W2, chained windows with carried history.** SD's 48-hour windows stay. Each new window takes over the previous
  window's position and history.

| | W1 | W2 |
|---|---|---|
| Window boundaries inside a deployment | None | One every `window_seconds`, plus one gap bar (SD:45-47) |
| First-bar check (`driver.py:487-489`) | Only PLB-O2's change | Also accepts the previous window's position record |
| The position record gates a first bar | No: every deployment starts flat | Yes: its store must sit in the D14 closure, under a trusted head |
| History | Unchanged | Spans windows (`driver.py:383`, `417-440`; `live_history.py:892-896`) |
| Carry deadline | `window.end`, which 3.1 makes the deployment end | Moves from `window.end` to the deployment end (`driver.py:655-660`) |
| Coordinator handoff (SD 5.1) | Not used | Kept, with its 30 s account-chain stop (SD:129-131) |
| Study | The carry study at the evaluator revision after M6-T3 | A new evaluator revision with an idle gap bar at each boundary; studies of the other revision do not count |
| After a safety stop or a restart | The deployment is over. Trading again needs a new schedule, a new review signature, a new `standing_armed` and a flat app, then a new warmup. The strategy no longer manages a held position. After a stop in the same process, the protective rules may sell until E if X, M and Md are in force (3.5); otherwise nothing sells and approval is requested (Q2 a). After a restart there is no hold: nothing sells until the owner acts or M7-T9 lands (A2:150-151, 172-176) | The deployment ends too (SD:177-184). The same deployment can be re-armed with a new `standing_armed` under the same review (SD:90-91), and its next window starts (SD:125-127). It may start with held units only after a stop in the same process; after a restart it starts flat unless the owner decides otherwise in M7-T9 (section 5) |
| Code to approve | Small (section 6) | Large (section 5) |

W2 keeps SD 4.2's re-arm of the same deployment under one review; W1 does not. Stops are common until the 1,000 ms
allowance lands (PH:729-730), so under W1 each one costs the owner a new review signature and a flat restart. A quick
restart works only if the app is flat at the stop: then a new deployment can start as soon as those are signed,
which may come sooner than W2's next window. With app units held, a new W1 deployment cannot start until the coin is
sold, by the owner's `exit` or a hand sell, by a protective sell before E, or under what M7-T9 brings (A2:174).
M7-T12 adds no other way out. This cost grows with `p` (3.7), so C1 is reopened with C3 if `p` turns out high. Apart
from the re-arm we found no requirement that W2 meets and W1 does not. A renewed profile is already swapped in inside a
window (`driver.py:356-357`), so a long window needs no restart for it.

## 3. Design W1

### 3.0 What C1 (a) supersedes

For a fixed carry standing schedule only, this document wins over:
- SD:42's maximum `window_seconds` of 259,200 (72 hours). The universe cap of 72 hours stays for universe schedules.
- SD-O2's default window of 48 hours, with 24 to 72 hours as the alternative (SD:264). This is a default, not an owner
  ruling; the span is chosen under C3 instead.
- SD:49 and the `launch.py` row of SD:236, which raise the owner tool's cap to 72 hours for every window.
- SD 4.1's schedule body as version 2, and its window-`k` match (SD:59-63), with the file row and tests that follow
  them (SD:229, 242-243).
- PH:670-671, "a mid-window `valid_until` is not a stop": under W1 the newest entry's `valid_until`, if it comes
  before `window.end`, ends the deployment there under the 11-13 rule (3.1).

A2 already supersedes SD:52-53 (A2:107). With C1 (b) none of these change, except as section 5 says.

### 3.1 The schedule

- **One window.** For a fixed carry profile the schedule (SD 3) has `count` 1. The window id is
  `<deployment_id>.w0` (SD:45). Its `window_seconds` is a multiple of the bar.
- **End rule (C6 a).** `window.end + bar_seconds <= expires_at` of the review that `live.py` loaded, and
  `window.end <= valid_until` of the newest `standing_armed` entry for the deployment. The review is issued before the
  window starts (`sign.py:1585`; SD:79, 88; `live_history.py:895`). It lasts at most 7 days (3.4), and no later than
  the study's `capture_end + review_max_age_seconds` (`review_auth.py:114`; `review_request.py:325`;
  `strategy.py:628`, `669-670`). `valid_until` is at most 7 days after its signing (SD:82). So
  `window.end + bar_seconds <= min(issued_at + 7 days, capture_end + review_max_age_seconds)`. With a review age that
  covers it, the longest window is 7 days minus the lead from the review's signing to the window start, minus one bar:
  at most 2,016 slots at 300 s, about 2,000 with a one-hour lead.
- **Where it is checked.** `live.py` checks the review part before it composes the driver. A deployment may have
  several open entries, because a change of X, M or Md is a new signed entry (A2:236-237; SD:97-100), and the newest
  one counts (PH:218-220). Each is signed after `live.py` starts (SD:88).
  - `live.py status` prints the minimum `valid_until` for any new entry of the running deployment: `window.end`.
  - `live.py` checks the newest entry at every preparation and at every fold of the owner log while the deployment
    runs. It refuses to prepare under an entry whose `valid_until` is before `window.end`, and flags one in status
    and with a red toast.
  - If such an entry comes into force anyway, for example while the app holds units and no preparation runs (A2
    3.10), the deployment ends at that `valid_until` under the 11-13 rule (A2:128-129). The slot ticks stop, so the
    driver sends no more orders. Entries are blocked and approval is requested; nothing sells. The monitor units run
    on until `monitor_until`, as after E (A2:98). For a W1 deployment this replaces PH:670-671 (3.0).
- **Why.** Without this rule the review expires before a 7-day window ends, and every later tick is refused, sells
  included (`runner.py:229-238`, `640-641`; `review_auth.py:199`). A `valid_until` inside the window would let the
  driver keep selling without a session after the deployment has ended (PH:189-191; SD:149-150). A2 makes
  `valid_until` the deployment's own end under the 11-13 rule (A2:128-129), and the behavior document allows no
  automatic action after that end (`managed_behavior.py:60-61`). The alternative is option (b) of C6: a carry deadline
  equal to the earliest of the three ends, which changes the driver, the runner, the coordinator and the protective
  policy (fact 11).
- **Span rule (C2).** `window_seconds` is at most the capture span of the carry study that the review names
  (`capture_end - capture_start`).
- **Only standing.** The multi-day cap applies only to a fixed carry standing schedule with `count` 1, bound to a
  `standing_armed` entry. `launch.py` and the coordinator cannot see that entry, because setup runs before it is signed
  (SD:88, 125-126). They accept up to 7 days for a fixed carry protocol, and the gate sits in two places: `live.py`'s
  schedule, and the single-session preparation (`prepare_launch_session` without `standing`, SD:113-115), which refuses
  a carry window longer than 24 hours. A single session keeps 24 hours and review version 2.
- **How the caps learn the protocol is carry.** `read_window` gets only a universe flag (`launch.py:384-385`), and
  the fixed path calls `setup-history` without `--protocol`, because `setup_history` requires a protocol and a
  storage policy together (`launch.py:168`) and only a universe protocol may carry one (`strategy.py:171-174`). The
  change passes the parsed protocol to `read_window`, `setup_history` and `_compose_driver`. Each allows up to 7 days
  when the protocol's behavior is `protective-carry-v2` (as `coordinator.py:198` resolves it). For any other protocol
  each keeps its cap: 24 hours fixed and 72 hours universe today, or what SD:49 sets once M7-T6 lands.
  `setup_history` then accepts a fixed carry protocol without a storage policy, and the CLI stops requiring
  `--history-storage` for it (`launch.py:382-390`). A fourth fixed-only 24-hour cap sits in the sealed research
  selection (`sealed_study_review.py:189`, before its `_compose_driver` call at `239`). That route grants no order
  authority (`sealed_study_review.py:1`) and is not the standing carry path, so it keeps 24 hours.
- **Renewal registry.** One process issues a terms renewal about every 4 minutes (`coordinator.py:95`), in the window
  and in its monitor tail, which can run up to one day past `window.end` (`coordinator.py:252`, `444`, `923`): about
  2,880 in 8 days. Both process registries hold 4,096 (`instrument_refresh.py:19`, `100`;
  `execution_accounts/instrument_terms.py:33`, `315`). It fits; a test records the margin.
- A fixed carry schedule never has a handoff (SD 5.1).

### 3.2 Driver and history

- **First bar.** No change beyond PLB-O2 (zero units and settled cash `>= C`, PLB:339). The check now runs once per
  deployment. A flat start is also what the behavior document says (`initial_condition: flat_start`,
  `managed_behavior.py:59`).
- **History.** No logic change. One journal per deployment. A fixed protocol has no storage policy
  (`strategy.py:171-174`; `live_history.py:470-474`), so the journal is bounded per row and by its slot count
  (`live_history.py:740`, `791`), not by a byte budget. A test checks its total size at the last slot.
- **Work per slot.** Each tick validates the frame twice, and each pass digests the whole history and recomputes the
  prior decision over every mark (`driver.py:364`, `428`, `437`, `538`, `550`). The driver and the verifier digest it
  again (`driver.py:560-562`; `live_history.py:1003`, `1012`). The history journal's `record_slot` also derives the
  slot's decision over every mark (`live_history.py:591-601`). All of it must finish inside the 10 s slot window
  (`driver.py:402-403`; `live_history.py:581`, `1000-1001`). At about 2,000 bars that work is about 7 times a 24-hour
  window's. A slot that overruns is a missed slot. So a measurement on the owner's PC of the whole slot unit at the
  last slot, from the slot instant through `record_slot` and the runner tick to the verifier's receipt, is a
  prerequisite of a multi-day window (3.7). Carrying the chain incrementally would be a driver change.
- **Deployment end.** By 3.1 the window end is the deployment end, so the 11-13 rule applies there (A2 3.1,
  A2:86-88; A2:128-129). Held app units are not sold, entries are blocked and approval is requested. Under C6 (a) the
  review's expiry cannot come first, and a newest entry's `valid_until` that comes first ends the deployment in the
  same way (3.1). A review check that fails mid-window for another reason (the owner log does not fold, the code or
  key differs) is a `held_at_end` safety stop (PH:182-186; A2 principle 4 and N3, A2:63-68, 427). The next
  deployment needs a flat start, so a held position waits for the owner (`exit`, a hand sell) or for what M7-T9
  brings, such as A2 N5's protect-only approval (A2:429). Carry across deployments is out of scope. Under W1, M7-T12
  therefore opens no way out of A2 3.3's gap after a restart (A2:172-176).

### 3.3 Daily sessions inside a long window (SD:149-150, A2 3.10)

- **Sessions stay daily.** A prepared session is valid only on its Seoul date (SD:25). The app prepares again after
  each Seoul midnight (SD 5.2).
- **While the app holds units at a Seoul date change,** preparation is refused (A2 3.10, A2:323). The new day then has
  no session: buys wait until the app is flat again, and sells continue (PLB:283). Refusals are retried every
  15 minutes (SD:144).
- **Effect against the study.** 3.6 lists every way live trading differs from the study. The sign of their effect on
  returns is unknown (C5).

### 3.4 The review

- **One window digest.** A review names one window (`review_auth.py:39-42`). With `count` 1, SD 4.1's window-`k`
  match is not needed.
- **Lifetime.** The review must outlive the window (3.1), so a standing review lasts up to 7 days, not 24 hours
  (`review_auth.py:32`, `113-115`). SD 4.1 planned `schema_version: 2` for this (SD:59), but body schema 2 already
  means carry (`review_auth.py:85-88`). The standing form takes the next free version, 3. It exists only in schedule
  form; its audit carries the schedule digest, which never equals a window digest (SD:66-68). This is M7-T8's code, and
  it changes the `_rv_*` mirror in `sign.py` (SD:69-70), which needs the owner's approval as always.
- **Reuse.** One study can back several deployments in a row, while the review age allows: `review_max_age_seconds`
  is at most 30 days (`strategy.py:185`, `628`). Each deployment starts from what the account holds, not from the
  study's `W0` (PLB:339).

### 3.5 The protective hold's end E

- **E is unchanged.** A2 keeps E as the stop window's scheduled end or the entry's `valid_until`, whichever is first
  (A2:89-90). Under W1 a hold after a stop can therefore last until the deployment end: almost 7 days, not PH's 48 or
  72 hours (PH:449-453). A2's N6 asks about E in a window that is not the deployment's last (A2:430), so it does not
  arise under W1.
- **What a later E changes.** After E nothing sells (A2:86-88, reading 5 at A2:418). A later E keeps the protective
  rules S, W, T and B able to sell for longer. It also delays the red toast, the urgent alerts and the approval
  request that A2 raises at E, and it stretches PH's worst case, a coin that no studied strategy manages with nobody
  watching (PH:455-456), from 48 or 72 hours to almost 7 days (C4).
- **Many W1 deployments may end here.** At a per-slot stop rate `p` of 0.1%, a deployment ends by a safety stop 44%
  of the time at 48 hours, 58% at 72 hours and 87% at 7 days. A stop is more likely than a full run when `p` is above
  about 0.12%, 0.08% and 0.034% for those spans (3.7). It then goes to the protective hold, if X, M and Md are in
  force, or to a no-sale approval request.

### 3.6 Study evidence

- **What PH found missing.** PH:451-452 says the study never held past its window end. That was the legacy evaluator,
  which sold at the last bar (`strategy.py:391-393`). The carry evaluator holds and marks instead
  (`carry_evaluator.py:6-7`). A carry study of span `L` has the same decision rule as a W1 deployment of span `L`: a
  flat start, continuous decisions and a held end that is marked, not sold.
- **Where live differs from the study.** The study measures none of these:
  - Buys at the Seoul date change: while the app holds units, preparation is refused, so live skips the top-ups that
    the carry intent makes whenever its allocation gap is positive (`managed_behavior.py:247-248`; 3.3).
  - Entries after going flat: live waits for the next preparation retry, up to 15 minutes (SD:144), while the study
    enters at the next bar.
  - Starting cash: the study starts at `W0`; a live deployment, and a reused study's later deployments, start from what
    the account holds (PLB:339; 3.4).
  - The protective hold after a stop, as PH section 7 already says.
  - Early ends: a missed slot, a restart or another safety stop ends a live deployment (3.7).
  - Held starts: W1 has none.
- **The study itself.** The fixed carry study: registered before its capture (`strategy.py:162-163`;
  `capture_v2.py:95-97`), captured slot by slot (`study.py:384`, `395-396`) and issued by `run_carry_validation`
  (`strategy.py:530-558`). It accepts any Upbit KRW spot coin (`strategy.py:164-167`). M6-T3 changes the driver's buy
  sizing and the evaluator in the same way and bumps the evaluator revision, so every earlier study is refused
  (PLB 4.2, PLB:252-259). "The carry study" here means one at that new revision.
- **Its span is `L` (C3).** 7 days is 2,017 rows, inside the capture's 20,000-row and 16 MiB limits
  (`capture_v2.py:26-27`, `100`). A test checks the byte limit. The inference work also grows with `L`: at most
  10,000,000 per candidate and 40,000,000 per family (`study.py:214-216`; `strategy.py:525-526`;
  `study_evidence.py:31`, `93-96`). With 2,016 returns and 9,999 replications, `block_length` must be at least 3, 6 or
  11 for a family of 4, 10 or 20. The preregistration step checks this. The study takes `L` of real time before the
  review.
- **Its review age.** `review_max_age_seconds` is frozen in the protocol before the capture (`strategy.py:162`,
  `185`), and it caps the review at `capture_end + review_max_age_seconds` (3.1). So the preregistered value must
  cover the time from `capture_end` to the planned `window.end` plus one bar, and the reuse span of 3.4. Otherwise
  the review cannot outlive the window and 3.1 refuses it, after `L` of capture. The preregistration step checks
  this too.

### 3.7 Prerequisites

- **The control journal's row cap (all live use).** One global journal (`coordinator.py:474`;
  `execution_control/store.py:166`) refuses any append once it holds 100,000 rows (`execution_control/store.py:31`,
  `357`), and nothing rotates it. Every live run writes to it: standing deployments, single one-day sessions and
  universe sessions alike. Each monitor unit and each slot tick appends a `risk_snapshot` row (`coordinator.py:948`;
  `runner.py:632`; `execution_control/controller.py:817-822`, `840-842`). The monitor interval is 5 to 20 s and must
  divide the bar, with at least 5 s after the prefetch lead (`coordinator.py:99`, `431`), so at 300 s bars it is at
  least 6 s; the default is 10 s (`coordinator.py:386`).
  - At 10 s: about 8,928 rows a day, about 62,500 in 7 days. The cap is reached after about 11 operating days in total,
    across all runs, which can fall inside a second deployment on a reused study (3.4).
  - At 6 s: about 102,800 rows in 7 days, over the cap from an empty journal.
  - After the cap every append fails, so monitoring, strategy sells and protective sells all stop.
  - So every C3 option and every O35 route, a daily one-day session included, reaches the cap after about 11
    operating days in total. The fix is a prerequisite of any live use beyond that, not of M7-T12 alone. It is its
    own task, M7-T13, outside M7-T12's code. C7 asks the owner which fix, and M7-T13 adds a headroom test of the
    control journal for it.
- **A late slot's time.** The measured slot unit at the last slot (3.2) fits inside the 10 s slot window, with its
  margin.
- **Completion odds.** Both a study and a live deployment end at their first missed slot (`study.py:374-377`,
  `395-399`, `414-416`; SD:177; `live_history.py:15-16`). A live deployment also ends at its other safety stops: a
  runner error, an account-chain stop, a halt, a clock rollback and a restart (SD:175-182). So for live, `p` is the
  per-slot rate of any safety stop, and it is measured that way. With a per-slot rate `p` and `n` slots:
  - the chance that a run completes is `(1 - p)^n`;
  - if each failed run is followed at once by a new one, the expected wait for one complete run is at least
    `(1 - (1 - p)^n) / (p * (1 - p)^n)` slots; every new study also needs a new registration before its capture.
  - Example at `p` = 0.1%: 48 hours (577 slots) completes 56% of the time, with an expected wait of about 65 hours;
    72 hours (865 slots), 42% and about 115 hours; 7 days (2,017 slots for a study, at most 2,016 live), 13% and
    about 544 hours (23 days). So a run ends by a stop 44%, 58% and 87% of the time.
  - A stop is more likely than a full run when `p` is above about 0.12% for 48 hours, 0.08% for 72 hours and 0.034%
    for 7 days.
  - At `p` = 0.01% the three complete 94%, 92% and 82% of the time. At 1% almost none completes.
  - `p` is not measured yet. Before the 1,000 ms allowance PR, 7.5% of book reads were refused (PH:113-114); the PC
    clock note expects the clock part to fall to about 0. The project computed the same odds for 48 hours
    (`docs/pc-clock-decision-2026-11-12.md:66-72`). Live records each slot within a 10 s window
    (`live_history.py:15`), so its miss rate may differ from the study's per-read rate. Both are measured after the
    allowance PR, before C3 is decided.

## 4. The position record, shared with M7-T9

**Why one record.** A restart ends the deployment without a sale (OQ16, B1:714-716). A deadline requests management
approval (11-13 rule). W2 would also need the same facts at every window boundary. One record of the app's position
serves all three. M7-T9 may use it; whether any management or protective state resumes after a restart is an owner
decision in M7-T9 under OQ16 (B1:554-556), Q7 (A2:43) and A2's N5 reconfirmation (A2:429).

| Field | Meaning |
|---|---|
| `schema` | `tradegen.app_position/1` |
| `deployment_id`, `window_sha256` | The deployment, and the window that wrote the record |
| `driver_identity_sha256` | Digest of the driver identity (`driver.py:242-274`) |
| `slot`, `written_at` | The last recorded slot, and the write time |
| `reason` | `deadline`, `safety_stop`, `owner_stop` or `restart_found`; also `window_end` under W2 |
| `venue`, `market`, `symbol`, `account_scope` | The scope |
| `app_units`, `app_cash_quote` | App units and app cash (BR-22, BR-23) at the slot's account capture; owner units excluded |
| `app_ledger_head` | The head of B1's app lot ledger (M7-T3) that the two amounts come from |
| `history_head`, `bar_count` | The history journal's head and its number of bars at `slot` |
| `last_decision_sha256` | Digest of the slot's carry decision (`live_history.py:597-601`) |
| `management_state_sha256` | `state_digest` of the management state at the slot (`protective_state.py:265-268`); null until M7-T9 |
| `previous_sha256` | The record before it, or null |

- **Writing.** Once per reason, after the slot's account capture. Records are append-only and hash-chained, under the
  same head discipline as the history journal: never rewritten. M7-T9 chooses the store, inside the D14 closure.
- **Reading.** A reader refuses a record whose identity digests differ from the current driver identity, or whose
  `app_units` differ from the app ledger at the reader's own capture. A new `code_approved`, protocol or profile means
  a new deployment; carry never crosses one.
- **A fact, not a permission.** Like the facts in `protective_state.py:1-8`, the record authorizes no sale, entry or
  cancel. Under W1 no deployment starts from a record: each starts flat.
- **What M7-T9 can do with it.** Show the owner what is held and why, and bind each management approval request to
  one record digest. Anything more, such as resuming a hold after a restart, needs the owner's decision in M7-T9.
- **W2's use.** At window `k + 1`'s bind, the first anchor must equal the record's app units and app cash, and the
  history must continue from `history_head`. The record then replaces the fail-closed flat check, so its integrity is
  safety-critical.

## 5. W2 in detail, if the owner chooses it

- **First bar** (`driver.py:487-489`). Window 0 as today, with PLB-O2. Window `k > 0` compares its first anchor with
  window `k - 1`'s position record, only when the two windows run in the same process. After a restart and a re-arm
  the next window starts flat, unless the owner decides otherwise in M7-T9 (OQ16, B1:554-556; Q7).
- **Deadline.** Under Q1 (b) a window end inside a deployment is not a deadline (A2:111-113). Today's carry deadline
  is `window.end` (`driver.py:655-660`), and reaching it writes the deadline record and asks for approval
  (`runner.py:509-520`). W2 moves the deadline to the deployment end, with the same end rule as 3.1 against the
  review's expiry and `valid_until`. For a stop inside window `k`, A2's N6 decides whether the hold's E is that
  window's end or `valid_until` (A2:430).
- **History** (`driver.py:383`, `417-440`). Bar indices and the prior-decision recomputation run over the whole
  deployment's history, not the window's. The decision's 20,000-bar bound still holds for 7 days.
- **Journals** (`live_history.py:892-896`). Window `k > 0` binds over the previous journal's head instead of GENESIS,
  and replay verifies the chain across journals.
- **Evaluator.** The carry arithmetic has one deadline, `capture_end` (`carry_evaluator.py:244-246`). With the deadline
  at the deployment end, what remains is the idle gap bar between windows (SD:45-47). That needs a new evaluator
  revision, so studies of another revision would not count. It could share M6-T3's bump (PLB:259) if both land
  together.
- **Handoff.** SD 5.1 stays, with its PC measurement and its 30 s account-chain stop (SD:129-133).

## 6. `code_approved` scope

Every code file below is inside the D14 closure (`core/compliance/owner.py:998-1009`), so each change needs a new
`code_approved`. The plan is one signature after the related code lands (M6-T3, M7-T3, M7-T8, M7-T9, M7-T11 and
M7-T12), as the main session schedules it.

W1 changes:
- `tools/owner/launch.py:104-114` (`read_window`), `160-187` (`setup_history`) and `382-390` (the CLI dispatch, which
  today reads `--history-storage` whenever a protocol is given): up to 7 days for a fixed carry protocol, learned from
  the parsed protocol; `setup_history` and its CLI accept a fixed carry protocol without a storage policy (3.1).
- `execution_launch/coordinator.py:1492-1493` (`_compose_driver`): the same 7-day cap for a fixed carry protocol. Every
  driver composition goes through it, `export-driver` included (`launch.py:392`).
- `tools/owner/live.py` (M7-T6, M7-T8; not on main yet): `count` 1 for a fixed carry schedule, the span rule, the end
  rule, and the check of every newest entry's `valid_until` with its flag (3.1).
- `execution_launch/coordinator.py`: stopping the slot ticks, with the monitor units running on, when a newest entry's
  `valid_until` before `window.end` comes into force (3.1). It adds no sale.
- The single-session preparation: a carry window longer than 24 hours is refused without a standing binding (3.1).
- `execution_launch/review_auth.py`: the standing review, version 3, in schedule form only, with its 7-day lifetime
  (3.4). The `sign.py` mirror is outside D14, and changes only with the owner's approval.
- The position record's writer and reader, in M7-T9's code (section 4).

Tests (section 8) are outside the closure. The control journal fix that C7 chooses is not in this list: it is task
M7-T13, which every route needs before about 11 operating days of live use (3.7).

M6-T3 changes the driver's buy sizing and the evaluator (PLB 4.2) and the first-bar rule (PLB-O2). Beyond those, W1
leaves the logic of `driver.py`, `live_history.py`, `carry_evaluator.py`, `strategy.py` and `study.py` unchanged.

## 7. Owner decisions

| ID | Question | Options | Recommended |
|---|---|---|---|
| C1 | Window shape | (a) W1, one window per deployment. This replaces SD's default of 48-hour windows and the SD lines of 3.0 for fixed carry. (b) W2, chained windows. | (a): no boundary to carry across, and little code. Its cost: every safety stop or restart ends the deployment, and trading again needs a new review signature, a new `standing_armed` and a flat app. With a coin held, a flat app means a sale first (the owner's `exit`, a hand sell, or a protective sell before E) or a wait for M7-T9 (section 2). The cost grows with `p`, so reopen C1 with C3 if the measured `p` makes a stop more likely than a full run at the chosen span (3.7) |
| C2 | Span rule | (a) A deployment is no longer than the study that qualified it. (b) A shorter study may approve up to 7 days. | (a): only (a) is measured (3.6) |
| C3 | Study and deployment span `L` | (a) 48 h, 577 slots. (b) 72 h, 865 slots. (c) The longest that 3.1 allows: at most 2,016 slots, less the review's lead and any shortfall of the review age. | None yet. Decide after `p` is measured (3.7), with the completion odds and expected wait of each option shown |
| C4 | E under W1: reopen SD-O8? | SD-O8's default is approved: the owner chose it on 11-12, and A2 amends it so that at E nothing sells (A2:343; PH:699). Under W1, E can come almost 7 days after a stop, not 48 or 72 hours (3.5). (a) Keep it. (b) Reopen SD-O8 for its alternative, a shorter signed `protective_max_hold_seconds`, such as 48 h after the stop. At that cap nothing sells either (A2 3.1). It adds a signed field to `standing_armed` and to the `sign.py` mirror, which needs the owner's approval. | (a), if the owner confirms A2 reading 5 (O36). (a) keeps protective selling longer but delays the approval request and the urgent alerts, and leaves an unmanaged hold for up to almost 7 days. (b) asks the owner sooner |
| C5 | Buys after a date change while the app holds: reopen PLB pin 3? | A2 3.10 applies the approved PLB pin 3 (PLB:283): preparation is refused while the app holds, so buys wait until flat. The main session counts, from the study capture and outside signed code, the top-ups and entries that live would have skipped or delayed (3.6), and shows them. (a) Keep it. (b) Reopen pin 3 in M6-T3 and allow preparation while the app holds. Exposure of (b): with a coin held, the odds card would show `E - C` of headroom while the runtime has only `cash - C` (PLB:283), so it overstates the headroom. It amends PLB pin 3 and A2 3.10. | (a): no new signed change |
| C6 | The end of a multi-day window | (a) The end rule of 3.1: the window ends no later than the review's expiry and the newest entry's `valid_until`. (b) A carry deadline equal to the earliest of `window.end`, the review's expiry and `valid_until`, in the driver, the runner, the coordinator and the protective policy. Under (b) a deployment can reach its review's expiry, after which every tick is refused, sells included (`runner.py:229-238`). | (a): it adds no code that sells |
| C7 | The control journal's row cap (3.7, M7-T13) | (a) Write a `risk_snapshot` only when its fields change. This lowers the rate but is not a bound: while a coin is held and equity keeps making new highs, `high_watermark` changes at almost every observation (`execution_control/controller.py:818-822`), and the rows still add up across deployments. (b) A new journal per deployment, or rotation. The new journal must start from everything the controller reads back (`execution_control/controller.py:787-805`, `1052-1055`): the effective-floor ratchet, the recorded peak, the day's start equity and the daily-stop latch, the kill and halt latches, every open, unknown or cancel-requested order, and the reservation history. Rotating only at a Seoul date change with no open order and no pending guard removes the day's values and the orders from that list. | (b), rotating only at a Seoul date change with no open order, with the carried values checked against the old journal's last rows. (a) can be added to slow the growth, but alone it does not remove the cap |
| C8 | Activation during a multi-day carry deployment (PLB-O4) | Already applied, not options here: PLB-O4's guidance, including a plan target below `A` (PLB:145), and PLB-O5, `L = W0` signed when the state check first shows `H >= A` (PLB:38, 144). Both are approved defaults (PLB:7, 657-658). What standing carry adds is how long a position is held across `A` (section 10). (a) Nothing more. (b) `live.py` refuses to start a multi-day carry deployment while `H` is within a signed margin of `A`, a new signed value that needs the owner's approval. | (a) if the private plan keeps its target below `A`, as the applied guidance says. Otherwise (b): it makes a crossing inside a deployment less likely, but it does not bound a position already open at the jump |

- **What PLB-O5 covers, in plain words.** PLB-O5 acts only after the state check shows `H >= A`. It does not protect a
  position already open at the jump, and a session already armed keeps admitting buys (PLB:142). After it, no new
  session can be prepared until the post-activation spec exists (PLB:144). Of the measures above, only a plan target
  below `A` bounds the open position at the jump, and C8 (b) bounds it in part. A signed X, M or Md does not cover it
  in normal running (section 10).

- **C3's cost.** It applies only when the first trade is a fixed standing deployment. O35, the first-trade path, is
  still open (A2:380-381). The owner was given these options:
  1. Keep the universe study (M9-T4, 48 h, 577 slots) as planned, and move the first live trade after M7-T11 and
     the universe carry design (Q6 a, A2 3.14).
  2. Move the first trade to the fixed path (KRW-BTC).
  3. Run both studies at the same time.
  4. A one-day fixed carry session first. It needs neither M7-T8 nor M7-T12, is signed daily, and uses a study shaped
     like a one-day window.
  5. Reopen Q6 and allow the universe window-end sale as a temporary exception.

  This document chooses none of them. Under 1 and 5 the first trade is universe, and C3 does not change when it
  happens. Under 4 it is a one-day session, which keeps the 24-hour cap (3.1), and C3 does not apply. Under 2, and
  under 3 when the fixed path goes first, the first trade waits for the study: by span alone, 7 days is about 5 days
  longer than 48 hours, and with the completion odds of 3.7 the expected wait can be much longer. With (a) or (b), a
  deployment ends every 48 or 72 hours, and a held position at that end waits for approval (3.2). Every route,
  4 included, needs M7-T13 before about 11 operating days of live use in total (3.7).
- **SD 4.1's version number** changes from 2 to 3 (3.4). It is not a new decision; SD already decided the 7-day
  review.

## 8. Tests for the code

- `test_fixed_carry_window_of_seven_days_is_accepted` and `test_other_window_caps_are_unchanged`, each for
  `read_window`, `setup_history` (no storage policy, through the `setup-history` CLI too) and `export-driver`
  (`_compose_driver`)
- `test_single_session_refuses_a_carry_window_over_one_day`
- `test_fixed_carry_schedule_has_one_window` and `test_schedule_longer_than_the_study_is_refused` (C2 a)
- `test_window_end_plus_one_bar_equal_to_the_review_expiry_is_accepted` and
  `test_window_end_less_than_one_bar_before_the_review_expiry_is_refused` (3.1)
- `test_valid_until_before_the_window_end_refuses_preparation` (3.1)
- `test_mid_window_entry_with_an_early_valid_until_is_flagged_and_ends_the_deployment_without_a_sale`: the slot ticks
  stop at that `valid_until`, entries are blocked, approval is requested and the monitor units run on (3.1)
- `test_carry_driver_holds_across_seoul_midnight_without_a_sale`
- `test_preparation_refused_while_the_app_holds_and_sells_continue` (A2 3.10)
- `test_fixed_carry_journal_of_2016_slots_replays_within_row_limits`, at the 3.1 maximum, with its total size at
  the last slot
- `test_renewal_registries_fit_eight_days` (the window and the longest monitor tail, about 2,880 of 4,096)
- `test_position_record_is_written_at_deadline_and_stop_with_app_units_only`
- `test_position_record_with_another_identity_is_refused`
- `test_position_record_grants_no_sale_entry_or_cancel`
- `test_standing_review_version_3_lasts_at_most_seven_days`, with `sign.py` test vectors (SD:69-70)
- A measurement on the owner's PC, not a unit test: the whole slot unit at slot index 2,015, the last that 3.1
  allows, finishes inside the 10 s slot window, with its margin (3.2)

## 9. Order of work

1. This document, as a PR after #74 merges.
2. Code that comes first: PLB-O2 and PLB 4.2 in M6-T3, and app units in M7-T3.
3. M7-T8 (schedule, end rule and review version 3) and M7-T9 (the position record).
4. M7-T12's code: the caps, the schedule rules and the tests of section 8. Then one `code_approved`. M7-T13, the
   control journal fix of C7, is a separate task on every route, needed before about 11 operating days of live use
   in total (3.7).
5. Measure `p` after the 1,000 ms allowance PR, and the late slot's time (3.7). The owner decides C3.
6. A carry study of span `L` for a preregistered candidate. None has qualified yet. Its preregistered
   `review_max_age_seconds` covers `capture_end` through the planned `window.end` plus one bar, and the reuse span
   (3.6). The capture binds the installed files of its manifest and refuses a change to them (`study.py:63-68`,
   `233-235`). It can start once no planned change touches those files: after M6-T3 at least, which changes the
   evaluator.

## 10. Risks and real odds

- **Activation with a position open (PLB-O4).** When the peak `H` first reaches the activation level `A`, the floor
  jumps while nothing sells. A position worth more than `min(H - W0, delta * H)` can then cause a permanent halt that
  ends the budget for good (PLB:145). PLB-O4's guidance and PLB-O5 already apply (C8). PLB:145 bounded the exposure
  to one window of at most a day. Standing carry (Q1 b) with W1's long window lets the app hold the position across
  `A` for up to almost 7 days. Top-ups go on only for the rest of the Seoul day of the crossing (3.3, A2 3.10), and
  new entries only until `L = W0` is signed (PLB:38). A halt sells nothing (SD-O1) and ends protective selling
  (A2:63-68), so the coin then stays held under a permanent halt. Rule B does not help in normal running. It runs only
  in a protective hold that an earlier safety stop started, before E (PH:204, 208, 215-217; A2:63-68), and then only
  with a signed M in force and if the jump itself did not halt. During normal W1 running only the strategy's own exit
  can sell before the halt. PLB's one-day bound was already weak on main, because the carry driver does not sell at
  its window end.
- **Longer holds.** A position can be held for up to `L` with no forced flat point. Below `A`, sizing keeps the floor
  even if the position goes to zero (B1:446-447). Above `A` it does not (PLB:141; the item above). A held position
  also meets the daily loss checks of up to 8 Seoul dates inside the window, and of one more in the monitor tail
  (A2:98; `coordinator.py:444`). Each resets at the Seoul date change.
- **Many long deployments may end early.** At `p` = 0.1%, a deployment ends by a safety stop 44% of the time at
  48 hours, 58% at 72 hours and 87% at 7 days (3.7). It then needs a new review signature and a flat restart, and a
  coin held at the stop must be sold first or wait for M7-T9 (section 2).
- **Later first trade.** When the first trade is a fixed standing deployment, it waits for the study, and a longer
  study waits longer, by more than its span (C3, 3.7).
- **No strategy has qualified** (`docs/forward-strategy-validation.md:3-6`). A study of any length can fail, and
  until one passes that is the honest expected outcome. Holding longer changes the spread of outcomes, not the
  ceiling on reaching a target (PH:739-741).
- This is not legal, tax or investment advice.
