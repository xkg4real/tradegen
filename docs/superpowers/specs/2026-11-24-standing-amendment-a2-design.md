# Amendment A2 to the standing deployment design: no sale on errors, restarts or deadlines

Date: 2026-11-24 (Asia/Seoul).
Status: proposed. It amends [protective hold](2026-11-12-standing-protective-hold-design.md) (below, "PH"),
[standing deployment](2026-11-12-standing-deployment-design.md) ("SD") and
[controlled launcher](2026-11-12-controlled-launch-and-planner-design.md) ("CL"). It records one owner amendment to
[blocker 1, approach A](2026-11-20-blocker1-held-interval-approach-a-design.md) ("B1"). Nothing is implemented.
Merging this document approves the design only. It signs nothing, arms nothing and sends no order. It changes no
code, no signed table and no `tools/signer/sign.py`.

**Citations.** `path:line` is rev `6d30fb0` (main). PH, SD and CL are unchanged since `b380ef8`, and B1 since PR #71's
head `ba5f7fd`, so their line numbers hold at those revs too. This PR adds one sentence pointing here to an existing
line of each one's Status paragraph, so no line number in them moves. All four are under `docs/superpowers/specs/`.
A2 is this document. "Row n" is row n of the M7-T4 consistency review of 2026-11-24. Section 4 restates each row, so
this document stands alone.

Owner financial parameters stay private and are not written here. This is software design, not legal, tax or
investment advice. Neither the software nor its author is a licensed advisor.

## 0. The change in one paragraph

PH, merged on 2026-11-12, sells a held coin after a restart, after a clock rollback, when inputs are missing, at the
hold's end time E, and at once after any safety stop when the protective values X, M and Md are not in force. The
owner's later decisions say otherwise. The 11-13 rule and OQ5 make the deadline a request for fresh management
approval, not a sale (B1:534-564, 653-655). OQ16 makes a restart end the deployment without a sale (B1:714-716). On
2026-11-24 the owner answered nine more questions (section 1). This amendment keeps PH's hold and its protective rules
S, W, T and B, and removes every sale whose only cause is an error, a restart or a deadline. It applies B1's app units
(BR-23) and flow-adjusted equity (BR-22) to the hold. It also keeps the universe profile out of live use until its own
deadline path exists.

## 1. Owner decisions of 2026-11-24 (O33)

The owner answered in the blockers-design session, after reading the M7-T4 review.

| Q | Question | Owner answer | Applied in |
|---|---|---|---|
| Q1 | Does OQ5 apply at each window end inside a standing deployment, or only at its end? | (b) A standing deployment carries the app position across its own window boundaries. Its own end keeps the 11-13 rule | 3.2 |
| Q2 | What happens at a safety stop when X, M and Md are not in force? | (a) No sale. Block entries, alert and request management approval. X, M and Md count from the signing, because they now only add sales | 3.6 |
| Q3 | Does a protective sale keep its authority after an in-process safety stop closes the standing entry? | (a) Yes, under the signed X, M and Md, until E, in the same process. A restart ends it (OQ16) | 2, 3.3 |
| Q4 | Clock rollback | (a) Handle it like a missed slot. The owner's wording of the principle: "오류라고 해서 반드시 매도 신호라는게 아니다 ... 보호 기준(X,M,Md)에 맞게 매도하는게 최우선" | 2, 3.5 |
| Q5 | May the app cancel its own resting buys at a stop and at E? | (a) Yes. Owner orders are never cancelled | 3.7 |
| Q6 | Universe profile | (a) No live universe use until M7-T11 and a universe carry design land | 3.14 |
| Q7 | A held coin after a restart | The recommended answer: accept that nothing sells it automatically, and make the alerts reliable (OQ14). Keeping the hold across a restart is designed in M7-T9 | 3.3 |
| Q8 | Document route | PR #71 is merged (`41f255f`). This separate docs PR does the alignment | - |
| Q9 | Does SD 4.3's loosening freeze cover BR-26's working Y? | (a) No. It covers signed entries only | 3.13 |

## 2. Principles

1. **An error is not by itself a sell signal. Selling by the protective criteria comes first** (owner, Q4). A missed
   slot or boundary, a runner error, a clock rollback, a restart, missing inputs, an approach-A mismatch or bid gap, an
   expiry and a deadline never start a sale on their own. While a hold runs, its protective rules (S, W, T and B,
   PH 6.4.3 as amended here) keep running and sell when they fire.
2. **The deadline asks for approval** (11-13 rule, OQ5). At E nothing sells. New entries are blocked and fresh
   management approval is requested. After E no automatic action runs without separate authority
   (`execution_launch/managed_behavior.py:57-65`, `post_deadline_automatic_action`). The app's own resting buys are the
   one exception (3.7).
3. **A restart ends the deployment and sells nothing** (OQ16). Startup reconciles holdings and orders (B1:448-453). Later
   orders need a new valid deployment.
4. **Authority for a protective sale** (owner, Q3). Between a safety stop and E, in the same process, two things are the
   authority. For T and B, it is the X, M and Md signed in the standing entry that the stop closed. For S and W, it is
   the reviewed program. The authority ends at E, at a restart, at a halt, at the owner's `close` and at a dispatched
   owner `exit` (PH 6.4.8).
5. **The app sells only app units** (BR-23, OQ4; B1:417-432).

## 3. Edits

Each subsection names the row it resolves, the lines it supersedes and the new text. Superseded lines stay in their
documents for history. Where they differ, this amendment wins.

### 3.1 The hold's end time E (row 1)

Supersedes the following, where they sell:
- PH 6.4.6 "At the end time the hold switches to sell" (PH:454) and rule E (PH:352)
- the `held_at_end` row's "At a window end, E has already passed, so the app sells at once" (PH:240)
- the sale in PH section 4 (PH:180-198)
- the second clause of startup condition 1, an entry past its `valid_until` (PH:149-150)
- the sale of SD-O8 (PH:699)

- **E ends the hold without a sale.** At E the hold ends. The app sends no sell for E. It blocks new entries, raises a
  red toast and the urgent alerts of OQ14, and requests fresh management approval for the held app units. S, W, T and B
  stop at E.
- **E is unchanged otherwise.** It is the scheduled end of the stop's window or the closed entry's `valid_until`,
  whichever comes first (PH:449-450).
- **`held_at_end`** stays a safety stop (PH section 4). With the protective values in force (3.6) and E ahead, the app
  holds. Otherwise nothing sells: entries are blocked and approval is requested. At a window end, E has passed, so this
  applies.
- **A buy still active at the end** gets PH's cancel requests (3.7). A fill after E adds to the held app units and is
  not sold for E.
- **What still runs after E.**
  - The floor and daily checks run while monitor units run, until `monitor_until` (PH:402-406).
  - A floor breach halts with the coin held (SD-O1).
  - The owner decides with `exit`, a hand sell or a new approval.

### 3.2 Window boundaries inside a standing deployment (row 2, Q1)

Supersedes:
- "The fixed driver still targets zero at each window end ... starts every window flat" (SD:52-53)
- "The fixed driver targets zero at the window end, so every window ends flat" (CL:69)
- SD 6.3's "There is no auto-sell, because each window already ends flat" (SD:195)

- **Principle (owner, Q1 b).** A standing deployment carries the app position across its own window boundaries. A
  window that ends with app units held does not sell them for the window end. The next window of the same deployment
  starts with them.
- **Not built yet.** Three things stand in the way today:
  - Both drivers require a flat first bar (`execution_launch/driver.py:487-489`).
  - SD refuses preparation while holding (SD:149-150).
  - The study measured only windows that start and end flat (PH:451-452).
  The carry design, its study evidence and its `code_approved` are task M7-T12.
- **Until M7-T12 lands,** a window that ends with app units held is handled like E (3.1): nothing sells, entries are
  blocked and approval is requested. The next window does not start until the app holds no units again, or until the
  carry exists.
- **The deployment's own end,** its `valid_until` or the last window's end, always uses the 11-13 rule (3.1), with or
  without M7-T12.
- **No end-slot sale in a live window.** A live fixed window uses the carry factory, managed behavior v2
  (`execution_launch/managed_behavior.py:57-65`), or a factory that M7-T11 has changed. The legacy end-slot target of
  zero (`execution_launch/driver.py:448-450`) is not used live (B1:430, 550).

### 3.3 Restart, and a chain that comes back (row 3, Q7)

Supersedes the following, where they sell:
- PH section 3 "Startup" (PH:147-168)
- "A chain that comes back" (PH:175-176)
- the restart and stopped-chain rows (PH:242-243)
- PH 6.4.8 "A later restart therefore still sells" (PH:505) and the matching tests (PH:658-665, 680-681)
- SD-O5's restart sale (PH:696)
- SD 6.2's "Then auto-sell starts (6.4)" after a restart (SD:182-185)

- **Startup.**
  - Step 3 still writes `safety_restart` for a standing id (PH:144).
  - Startup then reconciles holdings and open orders under BR-23 (B1:448-453) and requests a cancel of every active
    app buy (3.7).
  - It starts no sale and no hold. The hold's state lived in memory (PH:156), and its authority ended with the
    deployment (OQ16).
  - New entries stay blocked until a new valid deployment exists: a review and a new `standing_armed` (SD:90-91).
  - A red toast and the OQ14 alerts say that app units are held without protection.
- **Under a halt,** startup keeps PH's cancel requests for active app sells (PH:169-174; SD-O9).
- **A chain that comes back in the same process** does not sell for the stop. BR-12 can still stop the chain
  (B1:579-583). When reads return, two cases follow:
  - If the hold conditions of PH 6.4.1, as amended in 3.6, hold and E is ahead, the app holds as after a missed slot,
    and T's high starts at the first check.
  - Otherwise nothing sells and approval is requested.
- **The gap after a restart (owner, Q7).** Nothing sells a held app coin automatically until a new deployment exists.
  What remains is the floor check (a breach halts with the coin held, SD-O1), the daily stop, the alerts, and the
  owner's `exit` or hand sell. Keeping the hold across a restart is M7-T9.

### 3.4 Rule I (row 4)

Supersedes:
- "A rule that cannot be checked also starts the sale (SD-O13)" (PH:26)
- rule I as a sale trigger (PH:338-351)
- the first check's "the app goes straight to sell (I)" (PH:222-224)
- "After 30 s without a T and B check, I fires and the app sells" (PH:237-239)
- the matching test (PH:684)
- SD-O13 (PH:704)

B1:590 already supersedes rule I for approach-A events.

- **I no longer sells.** Its conditions (PH:339-347) stay as checks. When one holds, the app sends nothing for it and
  keeps the mode it is in. It raises a red toast and the OQ14 alert. For an approach-A mismatch or bid gap it applies
  CBA (BR-9) and nothing more. The rules that can still be checked keep running and sell when they fire (principle 1).
- **No first check within 30 s of the stop.** The app enters hold anyway if the other conditions of PH 6.4.1 hold. T's
  high starts at the first completed check.
- **What cannot run cannot sell.** For example, after a failed terms refresh, sells refuse after 5 minutes
  (PH:341-342).

### 3.5 Clock rollback (row 5, Q4)

Supersedes:
- "During a hold, a clock rollback switches to sell" (PH:228)
- the sale in the clock row (PH:241)
- SD-O5's clock sale (PH:696)
- "A clock rollback and a restart sell" (PH:615)

- **Like a missed slot (owner, Q4 a).** No unit runs until the wall clock passes its last value, protective units
  included (PH:241, unchanged). Then the hold continues with its rules and its high. If the rollback was the stop
  itself, the app enters hold at the first check, under PH 6.4.1.
- **Clocks.** E uses the wall clock and I uses the monotonic clock (PH:339-340), as before.

### 3.6 Protective values not in force, and when they count (row 6, Q2)

Supersedes:
- "Without them, the app keeps today's sell-at-once" (PH:29)
- "Otherwise the app goes straight to sell" (PH:226)
- "If X, M and Md are not in force, every row that says hold sells instead" (PH:246)
- "Without them, a safety stop sells at once, as today" (PH:547)
- the SD-O14 date rule (PH:220, 548-550) and SD-O14 (PH:705)
- the matching tests (PH:613-616)
- SD 6.2's auto-sell after every safety stop but a halt (SD:184-185)

- **Without X, M and Md in force, nothing sells for the stop** (owner, Q2 a). The app blocks new entries, raises a red
  toast and the OQ14 alert, and requests management approval.
- **PH 6.4.1, last lines.** The outcome depends on which condition fails:
  - Condition 1, 2 or 3 fails: nothing sells for the stop (3.1, 3.3, 3.6).
  - A rule fires at the first check (condition 4): the app sells by that rule.
- **When X, M and Md count.** They count from the entry's own stamp. Under this default they only add sales, so they
  tighten, and a tightening counts at once (D12; SD:103-105).
  - The one exception is a loosening. The newest entry for a deployment id may loosen a value that an earlier entry
    for the same id had in force: a larger X, a smaller M or a smaller Md.
  - The looser value then counts from the next Seoul date (D12). Until then, the stricter of the two applies, field by
    field.
- **Unchanged.** The values come from the newest entry the stop closed (PH:218-220). The fields are all three or none
  (PH:543).
- **Status.** The `live.py` status (PH:551-552) says plainly that without the three values a stopped deployment keeps
  its coin without protection.

### 3.7 Resting buys (row 7, Q5)

- **PH's cancel requests stay:**
  - at every safety stop (PH:127-134)
  - at startup (PH:164-168)
  - after E (PH:192-194)
- **The authority.** The owner granted it on 2026-11-24 (Q5 a) for the app's own buys in the runner's namespace. This
  amends "Expiry alone grants neither sell nor cancel authority" (B1:553) and the resting-buy row (B1:545) for those
  buys only.
- **Not cancelled:**
  - Owner orders are never cancelled (OQ12, OQ13; B1:683-688, 700).
  - Sells are not cancelled for this reason. A halt still cancels active app sells (SD-O9, PH 6.4.5).

### 3.8 Sell scope: app units (row 8)

Supersedes:
- "every held unit" in PH 6.4.1 (PH:212-213) and the attempt unit's quantity (PH:369)
- "held" in startup condition 3 (PH:152) and in `held_at_end` (PH:180-181, 192)

- **What a protective sale sells.** App units only: the lower of the free app units and the balance minus owner units,
  floored to the lot (BR-23, B1:426-432). Owner units are never sold.
- **What "held" means.** In the hold conditions, in `held_at_end` and in the dust rule (PH:396-400), "held" means app
  units at or above the minimum order. A coin only the owner holds starts nothing.

### 3.9 Rule B and external flows (row 9)

Supersedes the definitions of `Eq` and `line` for B (PH:256-258) and B's halt line (PH:328), read with SD-O10
(PH:701).

- **The halt line.** B uses the measure the halt test uses under blocker 1: flow-adjusted equity against the
  flow-adjusted floor and BR-22's protected raw floors (BR-13, BR-22; B1:241, 383-410). B's halt line fires when that
  equity is at or below the nearest of those lines plus M. `RiskResult.halt_line` is computed in that measure. So a
  deposit or a withdrawal moves both sides alike and never fires B by itself.
- **A withdrawal below a protected floor** is OQ2's case: record, block entries and alert (B1:642-646). It is not a B
  sale.
- **The daily line.** `daily` is the daily loss as BR-22 defines it, without settled flows.
- **SD-O10 stays:** marked equity, read as above.

### 3.10 Preparation and stake (row 10)

Supersedes SD 5.2's "preparation is refused until the account is flat" (SD:149-150). Qualifies CL 6.1's stake cap
(CL:265-267).

- **Preparation** is refused while the app holds units (BR-23; B1:441-447). Owner units and owner orders do not block
  it. An order of unresolved origin defers new entries (OQ12).
- **The stake cap** reads `E` and settled cash as BR-22 and BR-23 define them. Owner reservations are excluded from
  app buying power, and buy admission applies both BR-22 cash-floor checks (B1:439-447). The PLB code (M6-T3) settles
  the formula.

### 3.11 Superseded owner decisions (row 11)

PH section 9 (PH:694-705) records these as the owner's 2026-11-12 decisions. They are superseded as follows.

| Id | 2026-11-12 decision | Superseded by | Now |
|---|---|---|---|
| SD-O5 | A restart and a clock rollback sell | OQ16; Q4 | Restart: no sale (3.3). Clock: hold like a missed slot (3.5) |
| SD-O8 | Hold until E, then sell | 11-13 rule; OQ5 | At E nothing sells and approval is requested (3.1) |
| SD-O13 | Rule I sells | OQ5; Q4 | Rule I alerts and sells nothing (3.4) |
| SD-O14 | X, M and Md count from the next Seoul date | Q2 | From the stamp. A loosening counts from the next Seoul date (3.6) |

SD-O1, SD-O6, SD-O7, SD-O9, SD-O10, SD-O11 and SD-O12 stand. SD-O12's universe S stays as design. It is not used live
until 3.14 allows a universe profile.

### 3.12 Where Y is signed (row 12)

- **PH:553.** "`limit_set` is not changed" becomes: "`limit_set` gains only BR-26's optional `bid_gap_fraction`
  (B1:470-475). X, M and Md stay in `standing_armed`."
- **PH:597.** The `sign.py` row adds nothing for Y here. The BR-26 field belongs to M7-T3 and is reviewed in its own
  implementation PR.

### 3.13 SD 4.3 and the working Y (row 13, Q9)

Adds to SD 4.3 (SD:103-105) and to its test (SD:248):
- The freeze covers signed entries only. One of them is a `limit_set` that raises `bid_gap_fraction`.
- A move of BR-26's working Y inside the signed terms in force is not a loosening under SD 4.3. It needs no new entry
  and no midnight wait (B1:496-497; owner, Q9 a).

### 3.14 The universe profile (row 17, Q6)

- **No live universe use yet.** No universe profile runs live, in a session or a standing deployment, until both of
  these land:
  - M7-T11: no end-slot sale in any factory
  - a universe carry design, with its own evaluator revision and study
- **Why, at `6d30fb0`.**
  - The universe carry is refused (`execution_launch/managed_behavior.py:85-91`).
  - The legacy universe factory sells at the end slot (`execution_launch/driver.py:448-450`).
  - A review binds the legacy factory to the legacy evaluators only (`execution_launch/review_auth.py:99-101`).
- **Until then,** live arming accepts the fixed carry factory only. PH's universe rules (the universe S and W,
  PH:282-323) stay as design.
- **The first-trade path is still open.** The owner has not yet decided (O35) whether to keep the universe study
  (M9-T4) or move to a fixed profile. This amendment does not decide it.

## 4. Rows of the M7-T4 review and where each is resolved

| Row | Topic | Superseded or qualified lines | Resolved in |
|---|---|---|---|
| 1 | Sale at the end time E | PH:149-150, 180-198, 240, 352, 447-454; SD-O8 (PH:699) | 3.1 (A2:70) |
| 2 | "Every window ends flat" | SD:52-53, 195; CL:69 | 3.2 (A2:94) |
| 3 | Sale at a restart or when the chain comes back | PH:147-168, 175-176, 242-243, 505, 658-665, 680-681; SD:182-185; SD-O5 (PH:696) | 3.3 (A2:118) |
| 4 | Rule I sells | PH:26, 222-224, 237-239, 338-351, 684; SD-O13 (PH:704) | 3.4 (A2:146) |
| 5 | Clock rollback sells | PH:228, 241, 615; SD-O5 (PH:696) | 3.5 (A2:166) |
| 6 | Sale at once without X, M and Md | PH:29, 220, 226, 246, 547-550, 613-616; SD:184-185; SD-O14 (PH:705) | 3.6 (A2:179) |
| 7 | Buy cancels at a stop and at E | PH:127-134, 164-168, 192-194 stay; B1:545, 553 amended | 3.7 (A2:206) |
| 8 | Sell scope | PH:152, 180-181, 192, 212-213, 369, 396-400 | 3.8 (A2:219) |
| 9 | Rule B and flows | PH:256-258, 328; SD-O10 (PH:701) | 3.9 (A2:230) |
| 10 | Flat check and stake | SD:149-150; CL:265-267 | 3.10 (A2:244) |
| 11 | Superseded decisions | PH:694-705 | 3.11 (A2:255) |
| 12 | Where Y is signed | PH:553, 597 | 3.12 (A2:269) |
| 13 | SD 4.3 and the working Y | SD:103-105, 248 | 3.13 (A2:276) |
| 17 | Universe deadline path | PH:282-323; SD-O12 (PH:703) | 3.14 (A2:283) |

Rows 14 and 15 needed no change, because B1:579-583 and B1:590 already supersede those lines. Row 16 was settled by
PR #71's edits to `docs/account-baseline-contract.md`.

## 5. Readings for the owner to confirm

These details follow from the owner's answers but were not decided word for word. Each is open to change in review.

1. A chain that comes back in the same process holds as after a missed slot (3.3). This follows from Q3 and Q4.
2. After a clock rollback, the hold keeps its T high (3.5). The earlier high is the stricter choice.
3. When a newer entry loosens X, M or Md, the stricter value applies until the next Seoul date (3.6). This follows
   D12.
4. Until 3.14's conditions hold, live arming accepts the fixed carry factory only. This follows from Q6 a and OQ5.
5. After E, S, W, T and B stop (3.1). This follows from "until E" in Q3 and from the 11-13 behavior document.

## 6. Code follow-ups

- **Tasks.**
  - M7-T8: standing and protective code
  - M7-T9: the lifecycle across a restart, and authority after the deadline
  - M7-T11: no end-slot sale, and execution of protective sales
  - M7-T12: carry across windows
- **PH section 8's tests change as 3.1 to 3.10 say.** These become no-sale tests, each with an alert and an approval
  request:
  - the startup sale (PH:658-665)
  - "a restart sells" (PH:615, 680-681)
  - I's sale (PH:684)
  - the clock sale (PH:615)
  - the sale without the three values (PH:616)
- **Not in this PR.** It changes no code, no signed table and no `sign.py`.

## 7. Risks and real odds

- **Longer holds.** Not selling on errors means a coin can stay held longer after a restart, a rollback or missing
  inputs. With no protective values in force, or after a restart, nothing sells it automatically. Only the floor halt
  acts, and it sells nothing, so the owner must act.
- **The limit still holds.** Under the PLB budget the app's position is sized so that the floor holds even if the
  position goes to zero (B1:446-447). The change is in how much of the budget can be lost, not in the limit itself.
- **Fewer forced sales.** Missed slots are common while 7.5% of book reads are refused (PH:729-730). The sales they
  forced, each one realizing a loss, go away.
- **No edge.** Holding or selling changes the spread of outcomes, not the ceiling on reaching a target (PH:739-741).
  This is not legal, tax or investment advice.
