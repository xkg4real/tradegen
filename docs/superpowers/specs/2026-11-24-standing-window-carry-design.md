# Standing window carry (M7-T12): one window per standing deployment

Date: 2026-11-24 (Asia/Seoul).
Status: draft for owner review. It designs how a standing deployment keeps the app's position across its window
boundaries, as the owner decided on 2026-11-24 (O33 Q1 b). It builds on section 3.2 of
[amendment A2](2026-11-24-standing-amendment-a2-design.md) ("A2", PR #74). Nothing is implemented. Merging this
document approves the design only. It signs nothing, arms nothing and sends no order. It changes no code, no signed
table, no `tools/signer/sign.py` and no line of any other document.

**Citations.** `path:line` is rev `b828b2d` (main). PH, SD, CL and B1 are the documents A2 names, at the same line
numbers A2 cites; A2 only appends to existing lines. A2's own lines are at PR #74's head `d3197c8`. PLB is
[principal loss budget](2026-11-11-principal-loss-budget-design.md). All of them are under `docs/superpowers/specs/`.
`launch.py` is `tools/owner/launch.py`. Other code paths are under `execution_launch/` unless they say otherwise.

**Scope.** The fixed carry path only (factory `tradegen-fixed-carry-v2`). The universe profile waits for M7-T11 and
its own carry design (A2 3.14, A2:283). Owner financial parameters stay private and are not written here. This is
software design, not legal, tax or investment advice.

## 0. The proposal in one paragraph

A standing deployment of a fixed carry profile runs as one deployment window, from its first start to its end, at
most 7 days. Inside it there is no window boundary, so nothing has to be handed from one window to the next. The carry
driver already holds through its window without an end-slot sale (`managed_behavior.py:55-65`), and its history keeps
every mark of the window (`live_history.py:591-592`). The first-bar flat check stays, and runs once, at the deployment
start. The evidence is a carry study whose span is at least the deployment's span. The interface shared with M7-T9 is
a position record that the app writes whenever a deployment ends or stops while the app holds units. Chained windows
with carried history (W2, section 5) would also work, at a much larger cost in code and evidence.

## 1. What the code does today

| # | Fact | Evidence |
|---|---|---|
| 1 | The carry driver never sells for its window end. At the deadline an exit is blocked and approval is requested. | `managed_behavior.py:55-65`, `253-256`; `driver.py:564-566` |
| 2 | A window's first bar must hold zero units and exactly the protocol's initial cash. | `driver.py:487-489`; PLB-O2 relaxes the cash part to `>= C` (PLB:339) |
| 3 | A window's history starts empty at its own start. Bars are indexed from `window.start`, and a journal is created only before the window starts, over a head at GENESIS. | `driver.py:383`; `live_history.py:892-896` |
| 4 | Until `slow_window` marks exist, the decision is warmup and the driver holds: no buy and no sell. | `managed_behavior.py:203`; `driver.py:494-498` |
| 5 | The carry history keeps every mark of the window, not only the last `slow_window`. | `live_history.py:591-592` |
| 6 | A window has at most 20,000 bars; 7 days at 300 s is 2,017. Owner tools cap a fixed window at 24 h and a universe window at 72 h. | `driver.py:237-238`; `launch.py:113` |
| 7 | A review approves one driver identity, which includes one window digest, for at most 24 h. Review body schema 2 already means carry. | `review_auth.py:32`, `39-42`, `85-88`, `113-115` |
| 8 | The carry study starts flat and marks its inventory at the end; it invents no sale. The legacy study sold at its last bar. | `carry_evaluator.py:6-7`, `208`, `231`; `strategy.py:391-393` |
| 9 | Preparation is refused while the app holds units. Sells need no session and continue. | A2 3.10 (A2:244); PLB:283; SD:149-150 |
| 10 | The account anchor is the whole account's holding of the symbol. App units (BR-23, B1:417) come with M7-T3. | `live_history.py:563-566` |

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
| History | Unchanged | Spans windows (`driver.py:383`, `417-440`; `live_history.py:892-896`) |
| Coordinator handoff (SD 5.1) | Not used | Kept, with its 30 s account-chain stop (SD:129-131) |
| Study | The existing carry study | A new evaluator revision with a deadline at every window end; existing studies do not count |
| A missed slot | Ends the deployment (SD:177) | The same |
| Code to approve | Small (section 6) | Large (section 5) |

We found no requirement that W2 meets and W1 does not. A renewed profile is already swapped in inside a window
(`driver.py:356-357`), so a long window needs no restart for it.

## 3. Design W1

### 3.1 The schedule

- **One window.** For a fixed carry profile the schedule (SD 3) has `count` 1. Its `window_seconds` is the deployment
  span: a multiple of the bar, at most 604,800 (7 days, SD:48). The window id is `<deployment_id>.w0` (SD:45).
- **Caps.** `launch.py:113` accepts up to 7 days for a carry protocol only. The legacy fixed cap (24 h) and the
  universe cap (72 h, SD:42) stay. A fixed carry schedule never has a handoff (SD 5.1).
- **Span rule (C2).** `window_seconds` is at most the capture span of the carry study that the review names
  (`capture_end - capture_start`).

### 3.2 Driver and history

- **First bar.** No change beyond PLB-O2 (zero units and settled cash `>= C`, PLB:339). The check now runs once per
  deployment. A flat start is also what the behavior document says (`initial_condition: flat_start`,
  `managed_behavior.py:59`).
- **History.** No change. One journal per deployment, at most 2,017 slots at 300 s.
- **Deployment end.** The window end is the deployment end, so the 11-13 rule applies there (A2 3.1, A2:79-81).
  Held app units are not sold, entries are blocked and approval is requested. The next deployment needs a flat start,
  so a held position waits for the owner (`exit`, a hand sell) or for M7-T9's management approval. Carry across
  deployments is out of scope.

### 3.3 Daily sessions inside a long window (SD:149-150, A2 3.10)

- **Sessions stay daily.** A prepared session is valid only on its Seoul date (SD:25). The app prepares again after
  each Seoul midnight (SD 5.2).
- **While the app holds units at a Seoul date change,** preparation is refused (A2 3.10, A2:244). The new day then has
  no session: buys wait until the app is flat again, and sells continue (PLB:283).
- **Effect against the study.** The carry intent tops up a held position whenever its allocation gap is positive
  (`managed_behavior.py:247-248`). The study makes those buys; live skips them after a date change until the app is
  flat. Live can therefore hold less than the study did. The sign of the effect on returns is unknown (C5).

### 3.4 The review

- **One window digest.** A review names one window (`review_auth.py:39-42`). With `count` 1, SD 4.1's window-`k`
  match is not needed.
- **Lifetime.** The review must last as long as the deployment, up to 7 days, not 24 h (`review_auth.py:32`,
  `113-115`). SD 4.1 planned `schema_version: 2` for this (SD:59), but body schema 2 already means carry
  (`review_auth.py:85-88`). The standing form takes the next free version, 3. This is M7-T8's code, and it changes
  the `_rv_*` mirror in `sign.py` (SD:69-70), which needs the owner's approval as always.
- **Reuse.** One study can back several deployments in a row, while the review age allows: `review_max_age_seconds`
  is at most 30 days (`strategy.py:185`, `628`).

### 3.5 The protective hold's end E

- **E is unchanged.** A2 keeps E as the stop window's scheduled end or the entry's `valid_until`, whichever is first
  (A2:82-83). Under W1 the window end is the deployment end, so a hold after a stop can last until then: up to
  7 days, not PH's 48 or 72 hours (PH:449-453).
- **A later E adds no sale.** After E nothing sells (A2:79-81, reading 5 at A2:329). A later E only keeps the
  protective rules S, W, T and B able to sell for longer (C4).

### 3.6 Study evidence

- **What PH found missing.** PH:451-452 says the study never held past its window end. That was the legacy evaluator,
  which sold at the last bar (`strategy.py:391-393`). The carry evaluator holds and marks instead
  (`carry_evaluator.py:6-7`). A carry study of span `L` therefore runs what a W1 deployment of span `L` runs: a flat
  start, continuous decisions and a held end that is marked, not sold.
- **What it still does not measure.**
  - Held starts. W1 has none.
  - The top-ups that live skips after a date change (3.3).
  - A protective hold after a stop, as PH section 7 already says.
- **The study itself.** The existing fixed carry study: registered before its capture (`review_auth.py:34`), captured
  slot by slot (`study.py:384`, `395-396`) and issued by `run_carry_validation` (`strategy.py:530-558`). It accepts
  any Upbit KRW spot coin (`strategy.py:164-167`).
- **Its span is `L` (C3).** 7 days is 2,017 rows, inside the capture's 20,000-row limit (`paper_capture.py:27`). A
  test checks the 16 MiB byte limit (`paper_capture.py:24`). The study takes `L` of real time before the review.

## 4. The position record, shared with M7-T9

**Why one record.** M7-T9 resumes management of held app units after a restart and after a deadline. A restart ends
the deployment without a sale (OQ16, B1:714-716). A deadline requests management approval (11-13 rule). W2 would also
need the same facts at every window boundary. One record serves all three.

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
  same head discipline as the history journal: never rewritten. M7-T9 chooses the store.
- **Reading.** A reader refuses a record whose identity digests differ from the current driver identity, or whose
  `app_units` differ from the app ledger at the reader's own capture. A new `code_approved`, protocol or profile means
  a new deployment; carry never crosses one.
- **A fact, not a permission.** Like the facts in `protective_state.py:1-8`, the record authorizes no sale, entry or
  cancel. Under W1 no deployment starts from a record: each starts flat.
- **M7-T9's uses.** It shows the owner what is held and why. It binds each management approval request to one
  record digest. After a restart it lets the protective state resume where A2 allows.
- **W2's use.** At window `k + 1`'s bind, the first anchor must equal the record's app units and app cash, and the
  history must continue from `history_head`.

## 5. W2 in detail, if the owner chooses it

- **First bar** (`driver.py:487-489`). Window 0 as today, with PLB-O2. Window `k > 0` compares its first anchor with
  window `k - 1`'s position record.
- **History** (`driver.py:383`, `417-440`). Bar indices and the prior-decision recomputation run over the whole
  deployment's history, not the window's. The decision's 20,000-bar bound still holds for 7 days.
- **Journals** (`live_history.py:892-896`). Window `k > 0` binds over the previous journal's head instead of GENESIS,
  and replay verifies the chain across journals.
- **Evaluator.** The carry arithmetic has one deadline, `capture_end` (`carry_evaluator.py:244-246`). W2 needs a block
  at every window end and an idle gap bar. That is a new evaluator revision, so studies of the current revision would
  not count.
- **Handoff.** SD 5.1 stays, with its PC measurement and its 30 s account-chain stop (SD:129-133).

## 6. `code_approved` scope

The D14 closure covers `execution_launch/`, `execution_control/`, `tools/owner/`, `core/compliance/` and `core/odds/`
(`core/compliance/owner.py:998-1009`). Every change below therefore needs a new `code_approved`. The plan is one
signature after the related code lands (M6-T3, M7-T3, M7-T8, M7-T9, M7-T11 and M7-T12), as the main session
schedules it.

W1 changes:
- `tools/owner/launch.py:104-114`: the 7-day cap for a carry protocol (3.1).
- `tools/owner/live.py` (M7-T6, M7-T8; not on main yet): `count` 1 for a fixed carry schedule, and the span rule (3.1).
- `execution_launch/review_auth.py`: the standing review, version 3, with its 7-day lifetime (3.4). The `sign.py`
  mirror is outside D14, and changes only with the owner's approval.
- The position record's writer and reader, in M7-T9's code (section 4).
- Tests only: the driver and the history over a 2,017-slot carry window.

Beyond PLB-O2 (M6-T3), W1 leaves the logic of `driver.py`, `live_history.py`, `carry_evaluator.py`, `strategy.py`
and `study.py` unchanged.

## 7. Owner decisions

| ID | Question | Options | Recommended |
|---|---|---|---|
| C1 | Window shape | (a) W1, one window per deployment. (b) W2, chained windows. | (a): no boundary to carry across, little code, and the existing study counts |
| C2 | Span rule | (a) A deployment is no longer than the study that qualified it. (b) A shorter study may approve up to 7 days. | (a): only (a) is measured (3.6) |
| C3 | Study and deployment span `L` | (a) 48 h, 577 slots. (b) 72 h, 865 slots. (c) 7 days, 2,017 slots. | (c): it matches the 7-day standing cap, and gives 2,016 returns instead of 576 |
| C4 | E under W1 | (a) Keep A2: until the deployment end. (b) Cap at 48 h after the stop. | (a): after E nothing sells, so (b) only ends protective selling earlier |
| C5 | Buys after a date change while the app holds | (a) Keep A2 3.10: buys wait until flat. The main session counts the skipped top-ups from the study capture, outside signed code, and shows them. (b) Allow preparation while the app holds (a PLB pin 3 change in M6-T3). | (a) for the first deployment: no new signed change |

- **C3's cost.** The first trade waits for the study: 7 days is about 5 days longer than 48 h. With (a) or (b), a
  deployment boundary comes every 48 or 72 hours, and each held position at a boundary waits for approval (3.2).
- **O35 comes first.** If the owner keeps the universe path, W1 waits with the rest of the fixed path (A2 3.14).
- **SD 4.1's version number** changes from 2 to 3 (3.4). It is not a new decision; SD already decided the 7-day
  review.

## 8. Tests for the code

- `test_fixed_carry_window_of_seven_days_is_accepted` and `test_legacy_fixed_window_cap_stays_one_day` (`launch.py`)
- `test_fixed_carry_schedule_has_one_window` and `test_schedule_longer_than_the_study_is_refused` (C2 a)
- `test_carry_driver_holds_across_seoul_midnight_without_a_sale`
- `test_preparation_refused_while_the_app_holds_and_sells_continue` (A2 3.10)
- `test_history_of_2017_slots_replays_within_the_storage_policy`
- `test_position_record_is_written_at_deadline_and_stop_with_app_units_only`
- `test_position_record_with_another_identity_is_refused`
- `test_position_record_grants_no_sale_entry_or_cancel`
- `test_standing_review_version_3_lasts_at_most_seven_days`, with `sign.py` test vectors (SD:69-70)

## 9. Order of work

1. This document, as a PR after #74 merges.
2. Code that comes first: PLB-O2 in M6-T3, and app units in M7-T3.
3. M7-T8 (schedule and review version 3) and M7-T9 (the position record).
4. M7-T12's code: the cap, the schedule rules and the tests of section 8. Then one `code_approved`.
5. A carry study of span `L` for a preregistered candidate. None has qualified yet.

## 10. Risks and real odds

- **Longer holds.** A position can be held for up to `L` with no forced flat point. Sizing still keeps the floor
  even if the position goes to zero (B1:446-447). PLB:145 assumed that a carried position stays inside one window of
  at most a day. Under W1 it can meet up to 7 daily loss lines.
- **Later first trade.** A longer study delays the first trade by its length (C3).
- **No strategy has qualified** (`docs/forward-strategy-validation.md:3-6`). A study of any length can fail, and
  until one passes that is the honest expected outcome. Holding longer changes the spread of outcomes, not the
  ceiling on reaching a target (PH:739-741).
- This is not legal, tax or investment advice.
