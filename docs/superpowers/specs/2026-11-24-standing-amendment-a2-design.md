# Amendment A2 to the standing deployment design: no sale on errors, restarts or deadlines

Date: 2026-11-24 (Asia/Seoul).
Status: proposed. It amends [protective hold](2026-11-12-standing-protective-hold-design.md) (below, "PH"),
[standing deployment](2026-11-12-standing-deployment-design.md) ("SD") and
[controlled launcher](2026-11-12-controlled-launch-and-planner-design.md) ("CL"). It records one owner amendment to
[blocker 1, approach A](2026-11-20-blocker1-held-interval-approach-a-design.md) ("B1"). Nothing is implemented.
Merging this document approves the design only. It signs nothing, arms nothing and sends no order. It changes no
code, no signed table and no `tools/signer/sign.py`.

**Citations.** `path:line` is rev `6d30fb0` (main). PH, SD and CL are unchanged since `b380ef8`, and B1 since PR #71's
head `ba5f7fd`, so their line numbers hold at those revs too. This PR appends a short note pointing here (a pointer
and a one-line summary) to an existing line of each one's Status paragraph, so no line number in them moves. All four
are under `docs/superpowers/specs/`. A2 is this document. "Row n" is row n of the M7-T4 consistency review of
2026-11-24. Section 4 restates each row, so this document stands alone.

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
deadline path exists, and every standing deployment until the owner answers N5 (3.15).

## 1. Owner decisions of 2026-11-24 (O33)

The owner answered in the blockers-design session, after reading the M7-T4 review.

| Q | Question | Owner answer | Applied in |
|---|---|---|---|
| Q1 | Does OQ5 apply at each window end inside a standing deployment, or only at its end? | (b) A standing deployment carries the app position across its own window boundaries. Its own end keeps the 11-13 rule. The question noted that carry needs its own design and evidence (M7-T12). The interim until then is this document's (3.2, N5), not part of the answer | 3.2, N5 |
| Q2 | What happens at a safety stop when X, M and Md are not in force? | (a) No sale. Block entries, alert and request management approval. X, M and Md count from the signing, because they now only add sales | 3.6 |
| Q3 | Does a protective sale keep its authority after an in-process safety stop closes the standing entry? | (a) Yes, under the signed X, M and Md, until E, in the same process. A restart ends it (OQ16) | 2, 3.3 |
| Q4 | Clock rollback | (a) Handle it like a missed slot. The owner's wording of the principle: "오류라고 해서 반드시 매도 신호라는게 아니다 ... 보호 기준(X,M,Md)에 맞게 매도하는게 최우선" | 2, 3.5 |
| Q5 | May the app cancel its own resting buys at a stop and at E? | (a) Yes. Owner orders are never cancelled | 3.7 |
| Q6 | Universe profile | (a) No live universe use until M7-T11 and a universe carry design land | 3.14 |
| Q7 | A held coin after a restart | The recommended answer: accept that nothing sells it automatically, and make the alerts reliable (OQ14). Keeping the hold across a restart is designed in M7-T9 | 3.3 |
| Q8 | Document route | PR #71 is merged (`41f255f`). This separate docs PR does the alignment | - |
| Q9 | Does SD 4.3's loosening freeze cover BR-26's working Y? | (a) No. It covers signed entries only | 3.13 |

## 2. Principles

1. **An error is not by itself a sell signal. Selling by the protective criteria (X, M, Md) comes first** (owner, Q4;
   the Korean wording is in section 1). A missed slot or boundary, a runner error, a clock rollback, a restart, missing
   inputs, an owner log that does not fold, an approach-A mismatch or bid gap, an expiry and a deadline never start a
   sale on their own. While a hold runs, T and B, which use X, M and Md, keep running and sell when they fire. S and W
   also keep running in a hold (PH 6.4.3). That is PH's decision of 2026-11-12, kept here, not part of the Q4 wording.
2. **The deadline asks for approval** (11-13 rule, OQ5). At E nothing sells. New entries are blocked and fresh
   management approval is requested. After E no automatic action runs without separate authority
   (`execution_launch/managed_behavior.py:57-65`, `post_deadline_automatic_action`). The app's own resting buys are the
   one exception (3.7).
3. **A restart, or a handoff longer than 30 s, ends the deployment** (OQ16, B1:555-556, 714-716). A restart sells
   nothing. Startup reconciles holdings and orders (B1:448-453). Later orders need a new valid deployment. A handoff
   over 30 s is a safety stop that ends the deployment (OQ16; SD:253; B1:579-580): no hold authority carries over,
   nothing sells and approval is requested. It is not one of 3.3's hold stops, and it is not an account-chain stop.
   Under B1 its interval is rebuilt as a long interval (B1:282-283, 520), and only BR-12 or BR-17 stops the chain
   (B1:582-583). So it does not block the owner's `exit` or the floor and daily checks, as a chain stop does (PH:243).
4. **Authority for a protective sale** (owner, Q3 a: T, B, S and W may sell until E, in the same process). For T and B
   the authority is the X, M and Md signed in the standing entry that the stop closed. For S and W it is the reviewed
   program. The Q3 question in the M7-T4 review already cited B1:553's "current authority" when the owner chose (a).
   Its examples were a missed slot and a runner error. Whether a program review that has expired or failed its check
   is still the current authority Q3 covered is new choice N3 (section 5). By this document's default it is not:
   after a `held_at_end` caused by the review's expiry or a failed review check, only T and B run (PH:182-185; OQ5,
   B1:553, 654-655). The driver's own sells are already blocked then (PH:186). The authority ends at E, at a restart,
   at a halt, at the owner's `close` and at a dispatched owner `exit` (PH 6.4.8).
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
- the Normal end test's sales at the last window's end with the coin held, and of a later fill (PH:669-670, 673-674)

- **E ends the hold without a sale.** At E the hold ends. The app sends no sell for E. It blocks new entries, raises a
  red toast and the urgent alerts of OQ14, and requests fresh management approval for the held app units. S, W, T and B
  stop at E.
- **E is unchanged otherwise.** It is the scheduled end of the stop's window or the closed entry's `valid_until`,
  whichever comes first (PH:449-450). That bound is SD-O8, which the owner decided on 2026-11-12 (PH:691, 699), and
  Q3 a's "until E" keeps it. Whether a stop in a window that is not the deployment's last should instead hold until
  `valid_until` is new choice N6 (section 5). Its alternative would amend SD-O8.
- **`held_at_end`** stays a safety stop (PH section 4). With the protective values in force (3.6) and E ahead, the app
  holds. Otherwise nothing sells: entries are blocked and approval is requested. At a window end, E has passed, so this
  applies.
- **A buy still active at the end** gets PH's cancel requests (3.7). A fill after E adds to the held app units and is
  not sold for E.
- **What still runs after E.**
  - The floor and daily checks run while monitor units run, until `monitor_until` (PH:402-406).
  - A floor breach halts with the coin held (SD-O1).
  - The owner decides with `exit` or a hand sell. Until M7-T9 or M7-T12 lands, the approval requested at E cannot be
    granted while the app holds units, because a new deployment's preparation is refused then (3.2, 3.10). So nothing
    sells the coin automatically after E. The owner is asked to reconfirm this (N5, section 5).

### 3.2 Window boundaries inside a standing deployment (row 2, Q1)

Supersedes:
- "The fixed driver still targets zero at each window end ... starts every window flat" (SD:52-53)
- "The fixed driver targets zero at the window end, so every window ends flat" (CL:69)
- SD 6.3's "There is no auto-sell, because each window already ends flat" (SD:195)

- **Principle (owner, Q1 b).** A standing deployment carries the app position across its own window boundaries. A
  window that ends with app units held does not sell them for the window end. The next window of the same deployment
  starts with them.
- **Not built yet.** Four things stand in the way today:
  - Both drivers require a flat first bar (`execution_launch/driver.py:487-489`).
  - SD refuses preparation while holding (SD:149-150).
  - The study measured only windows that start and end flat (PH:451-452).
  - At a hold's first check, S fires when the window's history holds no decision yet (PH:273-274; universe,
    PH:287-288). With carried app units and a missed first slot, that is a sale caused by a missing input
    (principle 1). M7-T12 must make S check nothing there instead.
  The carry design, its study evidence and its `code_approved` are task M7-T12.
- **Until M7-T12 lands,** a window that ends with app units held is `held_at_end`. Under N6's default it is past E
  (3.1): nothing sells, entries are blocked and approval is requested. Under N6's alternative, T and B first protect
  the units until `valid_until`. As a safety stop it closes the standing entry (SD:184), so the
  remaining windows do not start. Only a new deployment, the owner's management approval (a review and a new
  `standing_armed`), starts trading again, and until M7-T12 lands it needs a flat app start. The app becoming flat, or
  an OQ9 model release, never reopens entries by itself (B1:670-674, 714-716). Until then the held coin has no
  automatic sale, and the only ways out are the owner's `exit` and a hand sell (3.1, N5).
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
- SD 6.2's "Then auto-sell starts (6.4)" after a restart (SD:182-185), and its test (SD:250-251)
- the Normal end test's restart sale after a mid-window `valid_until` (PH:671)
- the `live.py` row's startup sale (PH:598)
- "the journal schema stays as it is" (PH:603-605), for the sender tag below only

- **Startup.**
  - Step 3 still writes `safety_restart` for a standing id (PH:144).
  - Startup then reconciles holdings and open orders under BR-23 (B1:448-453) and requests a cancel of every active
    app buy (3.7).
  - It starts no sale and no hold. The hold's state lived in memory (PH:156), and its authority ended with the
    deployment (OQ16).
  - New entries stay blocked until a new valid deployment exists: a review and a new `standing_armed` (SD:90-91).
    Its windows start only once the app holds no units (3.2).
  - A red toast and the OQ14 alerts say that app units are held without protection.
- **Under a halt,** startup keeps PH's cancel requests for every active sell in the runner's namespace (PH:169-174;
  SD-O9), so the coin stays held (SD-O1). Today nothing tells an owner `exit` apart from the app's own sells: the
  journal does not record who sent a sell (PH:172-173), and B1 adds no such record, because an `exit` is an app order
  (B1:348-351) under the app sell cap (B1:429-430). M7-T8 adds one: a sender tag in the `reserved` row, where a sell
  is first journaled (`execution_control/controller.py:228`). A journal written before the tag replays as untagged.
  - A sell tagged as an owner `exit` is never cancelled, as during a hold (PH:425-426, 677-679).
  - Every other sell in the runner's namespace gets the cancel requests, an untagged one included. For an owner
    `exit` sent before the tag exists, PH's red toast asks the owner to send `exit` again (PH:174).
  - Orders outside the runner's namespace (PH:170-171), including orders whose origin is unresolved, are never
    cancelled. They defer new entries (OQ12, B1:683-688) and raise a red toast. This is this document's rule: Q5 a
    covers owner orders, and OQ13's proposed amendment never cancels a personal order (B1:700). The namespace
    changes with the profile (`execution_launch/runner.py:355`), so an app sell left from an earlier profile also
    rests under the halt and can fill (section 7).
  This is new choice N2 (section 5).
- **A chain that comes back in the same process** does not sell for the stop. BR-12 or BR-17 can still stop the
  chain (B1:582-583). Such a stop is a hold stop for PH 6.4.1 condition 1 (3.11, SD-O5; reading 1). A handoff over
  30 s is a separate stop, not a chain stop: it ends the deployment (principle 3). When reads return, two cases
  follow:
  - If the hold conditions of PH 6.4.1, as amended in 3.6, hold and E is ahead, the app holds as after a missed slot.
    A hold that was already running when the chain stopped keeps its T high, as after a clock rollback (3.5).
    Otherwise T's high starts at the first check.
  - Otherwise nothing sells and approval is requested.
- **The gap after a restart (owner, Q7).** Nothing sells a held app coin automatically after a restart. A new
  deployment does not end this gap while the app holds units: its windows do not start and preparation is refused
  (3.2, 3.10; B1:560-562). Until M7-T9 or M7-T12 lands, the only ways out are the owner's `exit` and a hand sell. The
  floor check (a breach halts with the coin held, SD-O1), the daily stop and the alerts still run. Keeping the hold
  across a restart is M7-T9. The owner is asked to reconfirm Q7 with this wording (N5, section 5).

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

- **Like a missed slot (owner, Q4 a), with one difference.** No unit runs until the wall clock passes its last
  value, protective units included (PH:241, unchanged). The timer waits on the wall clock (PH:102-103), so until then
  T and B cannot sell and the coin is unprotected, for as long as the clock was set back, with no upper limit. Then
  the hold continues with its rules and its high. If the
  rollback was the stop itself, the app enters hold at the first check, under PH 6.4.1. A rollback can also stop the
  account chain, for example when it leaves the PC clock more than 60 s from Upbit's server time
  (`execution_accounts/upbit_collector.py:167-168`); 3.3's chain rule then follows. Running protective units on the
  monotonic clock instead is new choice N4 (section 5).
- **Clocks.** E uses the wall clock and I uses the monotonic clock (PH:339-340), as before.

### 3.6 Protective values not in force, and when they count (row 6, Q2)

Supersedes:
- "Without them, the app keeps today's sell-at-once" (PH:29)
- "Otherwise the app goes straight to sell" (PH:226)
- "If X, M and Md are not in force, every row that says hold sells instead" (PH:246)
- "Without them, a safety stop sells at once, as today" (PH:547)
- the SD-O14 date rule (PH:220, 548-550), SD-O14 (PH:705) and the `live.py` row's date rule (PH:598)
- the matching tests (PH:613-616), except that `Md >= daily_loss_krw` still sells at the first check (3.9)
- the Normal end test's sale on an owner log that does not fold (PH:667-669)
- SD 6.2's auto-sell after every safety stop but a halt (SD:184-185), and its test (SD:250-251)
- the sell-at-once clauses of SD-O6 and SD-O7 (PH:697-698; 3.11)

- **Without X, M and Md in force, nothing sells for the stop** (owner, Q2 a). The app blocks new entries, raises a red
  toast and the OQ14 alert, and requests management approval. Until M7-T9 or M7-T12, that approval cannot be granted
  while app units are held (N5).
- **PH 6.4.1, last lines.** The outcome depends on which condition fails:
  - Condition 1, 2 or 3 fails: nothing sells for the stop (3.1, 3.3, 3.6).
  - A rule fires at the first check (condition 4): the app sells by that rule.
- **When X, M and Md count.** They count from the entry's own stamp. Under this default they only add sales, so they
  tighten, and a tightening counts at once (D12; SD:103-105).
  - The one exception is a loosening. The newest entry for a deployment id may loosen a value that was in force for
    the same id when it was signed: a larger X, a smaller M or a smaller Md. A newest entry without the three fields,
    after one with them was in force, loosens all three.
  - The looser value then counts from the next Seoul date (D12). Until then, the stricter of the two applies, field by
    field.
  - The values of an entry closed before the newer one was signed were not in force then, so the newer values count
    at once.
  - X, M and Md are read only after a stop has closed the entries. SD 4.3's freeze lasts only while an entry is open,
    so it never decides them; the rule above does (3.13).
- **Unchanged.** The values come from the newest entry the stop closed (PH:218-219), except as the loosening rule
  above says. The fields are all three or none (PH:543).
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
  - Owner orders are never cancelled (owner, Q5 a). OQ12 (B1:683-688) and OQ13's proposed amendment (B1:692-700)
    agree.
  - Sells are not cancelled for this reason. A halt still cancels active app sells (SD-O9, PH 6.4.5), never an owner
    `exit` (PH:425-426; at startup, only one tagged as such, 3.3).

### 3.8 Sell scope: app units (row 8)

Supersedes:
- "every held unit" in PH 6.4.1 (PH:212-213) and the attempt unit's quantity (PH:369)
- "held" in startup condition 3 (PH:152) and in `held_at_end` (PH:180-181, 192)

- **What a protective sale sells.** App units only: the lower of the free app units and the balance minus owner units,
  floored to the lot (BR-23, B1:426-432). Owner units are never sold.
- **What "held" means.** In the hold conditions, in `held_at_end` and in the dust rule (PH:396-400), "held" means app
  units at or above the minimum order. A coin only the owner holds starts nothing.

### 3.9 Rule B and external flows (row 9)

Supersedes, for B:
- the definitions of `Eq`, `line` and `dlimit` (PH:256-259, 264-265)
- B's halt line and daily line, with their `None` clauses (PH:328-329), read with SD-O10 (PH:701)
- "B fires on `line` `None`, and the attempt unit still sends" (PH:417-420)
- the B test's `None` cases (PH:637-639)
- the single `line + M` in the overshoot log (PH:407-408) and in the status key `protective_band_krw` (PH:523-525)

- **The halt line, in two pairs.** Each pair compares like with like (BR-13, BR-22; B1:241, 383-397). B's halt line
  fires when either holds:
  - adjusted equity, marked equity minus F, is at or below the flow-adjusted floor plus M;
  - raw marked equity is at or below the binding protected raw floor plus M, or, while R_w (below) is lower than that
    line, strictly below R_w. The binding floor is the higher of the protected raw principal and high-water amounts
    (B1:392-393).
  `RiskResult.halt_line` carries both lines. The status keys, the toasts and the overshoot log show each pair in its
  own units and record which pair fired.
- **A flow alone never fires B** (OQ2, owner-approved; B1:391).
  - A settled KRW flow changes neither adjusted equity nor the adjusted floor (B1:383-386). A coin flow changes
    adjusted equity only by the gap in its valuation, an incoming coin at the higher mark and an outgoing one at the
    lower (B1:360-361). That gap is a price move.
  - A settled withdrawal lowers raw equity but not a protected raw floor (B1:388-389), so it can leave raw equity at
    or below the binding raw floor plus M. R_w keeps that from firing B. It is a state of the account, not an event
    between two checks, so it covers a withdrawal settled at any time: during the hold, before it, or before the
    deployment.
- **OQ2's own case is narrower.** B1:389-390: "If marked equity falls below either as a result, record the
  withdrawal, block new buys and alert." OQ2 (B1:644): "If the withdrawal takes equity below a protected floor, record
  it, block new entries and alert." So OQ2 blocks entries only when raw equity is strictly below a protected floor,
  and equality is not a breach (B1:397). It starts no B sale. Whether entries are also blocked above the floor, up to
  the floor plus M, is new choice N1b (section 5).
- **R_w, the raw equity after a withdrawal** (new choice N1a, section 5).
  - It is the raw equity of the first account capture after a settled withdrawal, recorded before that capture's B
    check, whether or not a deployment or a hold exists. After several, the lowest counts. It is kept with the account
    record (BR-22), not in a hold's memory, so it holds across holds, deployments and restarts. No M is stored with it.
  - Each app fill after it is recorded lowers R_w by the fill's cost: its fee, plus the gap between its price and the
    mark of the first capture after it, times its quantity, when that gap is against the app (a buy above the mark,
    a sell below it). So the app's own trading cost never fires the raw pair. Only a fall in marks does.
  - At each B check the raw line is the lower of the binding raw floor plus M and R_w, with M from the entry that
    counts (3.6; PH:218-219). While R_w is the lower, the pair fires only strictly below it, so a check at unchanged
    marks never fires it.
  - R_w is cleared only at a B check whose raw equity is above the binding raw floor plus that hold's M. A capture
    outside a hold does not clear it, because no M counts there yet and a later entry may sign a larger one (3.6).
- **An unresolved balance decrease** (BR-21, OQ8; B1:362-364, 372-373, 408-414). A capture can show a balance fall
  that is not yet matched to a withdrawal, a transfer leg or a confirmed loss. B treats it as a pending withdrawal:
  - R_w is recorded at the first capture that shows it, as for a settled withdrawal. It is not recorded again when
    the withdrawal settles.
  - The adjusted pair and `daily` count the amount as a flow, valued as an outgoing one (B1:360-361), until it is
    matched.
  - The app raises a red toast and the OQ14 alert. The residual itself adds no halt and no entry block (B1:411-412).
  - Once matched, a withdrawal or transfer follows the settled rules. A confirmed loss (OQ8, B1:667-668) counts in
    the adjusted pair and in `daily` from that capture, and its R_w stays.
  - Exposure: B does not act on a real unexplained loss until it is matched. The floor checks, which compare marked
    equity with the raw floor, still run (B1:389-390, 392-393).
- **`line` or `dlimit` is `None`.** B checks nothing on that line. `line` is `None` when there is no floor or the
  owner log does not fold, and `dlimit` when no daily loss is signed or the owner log does not fold (PH:258-259,
  264-265). As with rule I (3.4), the app raises a red toast and the OQ14 alert, blocks new entries and keeps its
  mode. T keeps running. S and W follow principle 4: an owner log that does not fold is a failed review check
  (PH:184-185), so under N3's default they stop. A sale already running goes on, stopped only by the journal latch, as
  D11 keeps exits open on a corrupt owner state (PH:417-420). B starts no sale from `None`.
- **The daily line.** B fires when `daily >= dlimit - Md` (PH:329). `daily` is the daily loss as BR-22 defines it,
  without settled flows or pending decreases (above). If Md is not below the signed daily loss, the daily line fires
  at the first check and the app sells (PH:330-333). That sale comes from the owner's own signed values, which
  principle 1 puts first.
  - `dlimit` is read at every check (PH:336), and Md is not checked against it (PH:545-546). So a later `limit_set`
    that lowers the daily loss to Md or below makes every hold stop sell at its first check.
  - While that is so, `live.py` status says it in a plain line and the app raises a red toast: every hold stop (a
    missed slot, a runner error, a `held_at_end` before E, a clock rollback, a chain that comes back) will sell at
    its first check while X, M and Md are in force and E is ahead.
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
| SD-O5 | A restart and a clock rollback sell | OQ16; Q4 | Restart: no sale (3.3). Clock: hold like a missed slot (3.5). An account-chain stop (BR-12 or BR-17) whose chain comes back in the same process is a hold stop (3.3; reading 1). A handoff over 30 s is a separate safety stop that ends the deployment (OQ16, principle 3) |
| SD-O6 | No built-in X; without a signed X the app sells at once | Q2, in part | Without X nothing sells (3.6). The rest stands |
| SD-O7 | B guards the halt line with M and the signed daily loss with Md; without a signed M the app sells at once | Q2, in part | Without M and Md nothing sells (3.6). B's two lines stand as 3.9 restates them |
| SD-O8 | Hold until E, then sell | 11-13 rule; OQ5 | At E nothing sells and approval is requested (3.1). The bound E stays (N6's alternative would amend it) |
| SD-O13 | Rule I sells | OQ5; Q4 | Rule I alerts and sells nothing (3.4) |
| SD-O14 | X, M and Md count from the next Seoul date | Q2 | From the stamp. A loosening counts from the next Seoul date (3.6) |

SD-O1, SD-O9, SD-O10, SD-O11 and SD-O12 stand. SD-O9 stands under N2's default: PH 6.4.5's owner-`exit` exception
to it (PH:425-426) reaches startup once M7-T8's sender tag exists (3.3). N2's alternative would amend SD-O9, SD-O1
and PLB (f) for untagged sells. SD-O12's universe S stays as design. It is not used live until 3.14 allows a universe
profile.

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
- **Until then,** live arming refuses a universe profile, and any factory that still sells at the end slot (OQ5;
  B1:430). A live fixed window uses the carry factory or a factory that M7-T11 has changed, as 3.2 says. A legacy
  study sells at its last bar (`execution_launch/strategy.py:391-393`). Whether such a study is enough evidence for
  an M7-T11 factory that holds past it is for M7-T11 to settle. PH's universe rules (the universe S and W,
  PH:282-323) stay as design.
- **The first-trade path is still open.** The owner has not yet decided (O35) whether to keep the universe study
  (M9-T4) or move to a fixed profile. This amendment does not decide it.

### 3.15 Live gate for standing deployments (N5)

- **Proposed.** Live arming refuses a standing deployment until the owner answers N5 (section 5). Merging this
  document is not that answer. This gate is this document's rule, not an owner answer.

## 4. Rows of the M7-T4 review and where each is resolved

| Row | Topic | Superseded or qualified lines | Resolved in |
|---|---|---|---|
| 1 | Sale at the end time E | PH:149-150, 180-198, 240, 352, 447-454, 645, 669-670, 673-674; SD-O8 (PH:699) | 3.1 (A2:79) |
| 2 | "Every window ends flat" | SD:52-53, 195; CL:69 | 3.2 (A2:108) |
| 3 | Sale at a restart or when the chain comes back | PH:147-168, 175-176, 242-243, 505, 598, 658-665, 671, 680-681; SD:182-185, 250-251; SD-O5 (PH:696) | 3.3 (A2:139) |
| 4 | Rule I sells | PH:26, 222-224, 237-239, 338-351, 684; SD-O13 (PH:704) | 3.4 (A2:189) |
| 5 | Clock rollback sells | PH:228, 241, 615; SD-O5 (PH:696) | 3.5 (A2:209) |
| 6 | Sale at once without X, M and Md | PH:29, 220, 226, 246, 547-550, 598, 613-616, 667-669; SD:184-185, 250-251; SD-O6, SD-O7 (PH:697-698); SD-O14 (PH:705) | 3.6 (A2:227) |
| 7 | Buy cancels at a stop and at E | PH:127-134, 164-168, 192-194 stay; B1:545, 553 amended | 3.7 (A2:262) |
| 8 | Sell scope | PH:152, 180-181, 192, 212-213, 369, 396-400 | 3.8 (A2:277) |
| 9 | Rule B and flows | PH:256-259, 264-265, 328-329, 407-408, 417-420, 523-525, 637-639; SD-O10 (PH:701) | 3.9 (A2:288) |
| 10 | Flat check and stake | SD:149-150; CL:265-267 | 3.10 (A2:358) |
| 11 | Superseded decisions | PH:694-705 | 3.11 (A2:369) |
| 12 | Where Y is signed | PH:553, 597 | 3.12 (A2:387) |
| 13 | SD 4.3 and the working Y | SD:103-105, 248 | 3.13 (A2:394) |
| 17 | Universe deadline path | PH:282-323; SD-O12 (PH:703) | 3.14 (A2:401) |

Rows 14 and 15 needed no change, because B1:579-583 and B1:590 already supersede those lines. Row 16 was settled by
PR #71's edits to `docs/account-baseline-contract.md`.

## 5. Readings and new choices for the owner to confirm

**Readings.** These follow from the owner's answers but were not decided word for word. Each is open to change in
review.

1. A chain that comes back in the same process holds as after a missed slot, so SD-O5 lists that stop as a hold stop
   (3.3, 3.11). A hold that was already running keeps its T high. This follows from Q3 and Q4. A handoff over 30 s
   is not such a stop, because OQ16 ends the deployment (principle 3).
2. After a clock rollback, the hold keeps its T high (3.5). The earlier high is the stricter choice.
3. When a newer entry loosens X, M or Md, or leaves out all three, the stricter value applies until the next Seoul
   date (3.6). This follows D12.
4. Live arming refuses a universe profile and any factory that sells at the end slot (3.2, 3.14). This follows from
   Q6 a and OQ5. A fixed profile may use the carry factory or a factory that M7-T11 has changed.
5. After E, S, W, T and B stop (3.1). This follows from "until E" in Q3 and from the 11-13 behavior document.

**New choices.** These do not follow from the owner's answers, or two answers point different ways. Each row shows
the default this document uses and what each option exposes. N5 is a reconfirmation and has no default.

| Id | Question | Default here | Alternative |
|---|---|---|---|
| N1a | Where the raw pair's line goes after a withdrawal, or a pending balance decrease, leaves raw equity at or below the binding raw floor plus M (3.9). That the flow itself sells nothing is settled (OQ2, B1:391) | The line drops to R_w, the raw equity at the first capture after the flow, lowered by later app fill costs. It fires only strictly below R_w. A B check with raw equity above the floor plus that hold's M clears it. Exposure: the raw pair's M is spent, so a fall in marks below R_w sells at the next check (about 10 s, PH:106). A fresh M in a new `standing_armed` does not restore it, and a rise between holds does not clear it. Once a B check clears it, a return to the post-withdrawal level fires B, at a price where R_w had just declined to fire | While R_w is below the floor plus M, the raw pair checks nothing. It resumes when R_w is cleared, by the same rule. The adjusted pair, T, S, W and the floor halt keep running. Exposure: the coin can fall to the raw floor with no raw-pair sale, and the breach then halts with the coin held (SD-O1) |
| N1b | Entries while R_w is below the binding raw floor plus M and raw equity is not below a protected floor (3.9). OQ2 blocks entries only below a protected floor (B1:389-390, 644) | No block beyond OQ2's. Exposure: the app can buy while the raw pair's margin is spent. Its fill costs lower R_w, so only a later fall in marks below R_w sells | Also block new entries then, using the M of the newest standing entry in force. Lift: a capture with raw equity above the floor plus that M, or an OQ9 release (B1:670-674). Exposure: no buys near the floor after a withdrawal, and an OQ9 release is an extra owner action |
| N2 | Sells still resting at a restart under a halt (3.3). An owner `exit` is never cancelled by a halt during a hold (PH:425-426, 677-679). PH cancels it at startup only because the journal cannot tell who sent it (PH:172-174). Owner orders are never cancelled (Q5 a) | Cancel every sell in the runner's namespace except one tagged as an owner `exit` (M7-T8), as SD-O9 says. Exposure: an `exit` sent before the tag exists is cancelled, and the owner must send it again. An app sell left from an earlier profile is outside the namespace, so it rests and can fill | Leave untagged sells resting. This amends SD-O9, SD-O1 and PLB (f) for them (PH:700). Exposure: an app sell, a protective or driver sell included, can fill after the halt |
| N3 | S and W after a `held_at_end` caused by the review's expiry or a failed review check (principle 4). The Q3 question cited B1:553's "current authority" when the owner chose (a). Its examples were a missed slot and a runner error. Open point: is a program review that has expired or failed its check still the current authority Q3 covered? | No. Only T and B run (OQ5, B1:553, 654-655). The driver's own sells are already blocked then (PH:186). Exposure: the coin is held past the strategy's own exit signal until T, B or E acts | Yes. S and W also run until E. Exposure: a program whose review expired or failed still drives real sells |
| N4 | Protective units after a clock rollback (3.5) | Wait for the wall clock, as PH:241. Exposure: T and B cannot sell for as long as the clock was set back, with no upper limit (a 1 h rollback leaves about 1 h unprotected) | Run them on the monotonic clock. Exposure: new code in `coordinator.py`, a D14 closure file that needs `code_approved` (PH:592; it builds on M7-T8's injected monotonic clock). The units must accept captures whose wall-clock stamps `Coordinator._time` refuses (PH:102-104). E stays on the wall clock (3.5), and committed startup still refuses a rollback (B1:520). A rollback of more than 60 s from Upbit's server time still refuses captures (`execution_accounts/upbit_collector.py:167-168`), so B has no fresh equity until the clock is fixed |
| N5 | Reconfirm Q7, widened (3.1, 3.2, 3.3, 3.6). After E, a window end with app units held, a restart, a stop without X, M and Md, or, once M7-T12 carries app units across windows, a handoff over 30 s, nothing sells the held app coin automatically. Until M7-T9 or M7-T12, the approval requested then cannot be granted while app units are held, so the only ways out are `exit` and a hand sell. The floor halt (no sale, SD-O1), the daily stop and the alerts run until `monitor_until`, at most window end + 1 day (PH:402-406) | None. Merging this document is not an answer, and no standing deployment goes live before the owner answers (3.15) | (a) Accept. Exposure: the coin can stay held with no automatic sale for as long as the owner does not act. (b) A protect-only approval, designed in M7-T9 and brought forward before the first standing deployment. It runs T and B on held app units, sends no buy and starts no window. Exposure: more design, code and review before the first standing deployment |
| N6 | E for a stop in a window that is not the deployment's last, including a `held_at_end` at that window's end (3.1) | The window's end: SD-O8 (owner, 2026-11-12; PH:699), which Q3 a's "until E" keeps. Exposure: at each such window end with app units held, the normal case before M7-T12, T and B stop at once and N5's gap starts | The closed entry's `valid_until` (at most 7 days, SD:82). This amends SD-O8 and extends Q3 a's protective authority past the window end. That authority is the signed X, M and Md (principle 4), the separate authority that principle 2 and `execution_launch/managed_behavior.py:61` require. Q1 b, carry across window boundaries, argues for it. T and B keep protecting the held app units until then; S and W stop at the window's end, where its slots end. Exposure: a hold longer than any studied one (PH:451-452), and monitor units must run past `monitor_until` (at most window end + 1 day, PH:405-406), which is new code in M7-T8 |

## 6. Code follow-ups

- **Tasks.**
  - M7-T8: standing and protective code. It includes a sender tag in each sell's `reserved` row (3.3, N2), R_w kept
    with the account record and lowered by app fill costs, B's pending-decrease rule (3.9, N1a), both B pairs in
    status and logs (3.9), and the warning when Md is not below the signed daily loss (3.9).
  - M7-T9: the lifecycle across a restart, and authority after the deadline
  - M7-T11: no end-slot sale, and execution of protective sales
  - M7-T12: carry across windows
- **PH section 8's tests change as 3.1 to 3.10 say.** These become no-sale tests. Each raises an alert. Those that 3.1
  to 3.10 send to approval also request it. Rule I keeps the mode and alerts (3.4), and B on `None` also blocks
  entries (3.9):
  - the startup sale (PH:658-665)
  - "a restart sells" (PH:615, 680-681)
  - I's sale (PH:684)
  - the clock sale (PH:615)
  - the sale without the three values (PH:616), except with `Md >= daily_loss_krw` (3.9)
  - B on `line` or `dlimit` `None` (PH:637-639)
  - E at the scheduled `window.end` (PH:645)
  - the Normal end sales: an owner log that does not fold, the last window's end, a restart after a mid-window
    `valid_until`, and a later fill (PH:667-674)
  - SD's "All but a halt start auto-sell" (SD:250-251)
- **New tests.**
  - A newest entry without X, M and Md, after one with them, keeps the old values until the next Seoul date (3.6).
  - A withdrawal settled before the deployment leaves raw equity inside B's raw band. The deployment buys, and the
    fee and spread lower raw equity. A later missed slot's first check, at unchanged marks, sells nothing (3.9).
  - After a withdrawal into the raw band, a check at unchanged marks does not fire, a check with raw equity strictly
    below R_w fires, and a B check with raw equity above the floor plus M clears R_w (3.9).
  - A withdrawal leaves raw equity above the floor plus the M then signed. A later entry signs a larger M, which puts
    it inside the band. The first B check at unchanged marks sells nothing (3.9).
  - A balance fall with no matched withdrawal record yet, at unchanged marks, fires neither pair nor the daily line.
    Neither does an unresolved missing-leg pocket move (3.9).
  - Under N1b's default, a withdrawal that leaves raw equity inside the band but above every protected floor blocks
    no entry (OQ2).
  - At a restart under a halt, a sell tagged as an owner `exit` gets no cancel request. An untagged sell in the
    runner's namespace gets the cancel requests and the red toast (3.3).
  - A handoff over 30 s ends the deployment with no hold and no sale, and the account chain continues (principle 3).
  - With Md not below the signed daily loss in force, `live.py` status and a red toast warn (3.9).
- **Not in this PR.** It changes no code, no signed table and no `sign.py`.

## 7. Risks and real odds

- **Longer holds.** Not selling on errors means a coin can stay held longer after a restart, a rollback or missing
  inputs. After E, a window end with app units held, a restart, a stop without protective values in force, or, once
  M7-T12 carries app units, a handoff over 30 s, nothing sells it automatically. Only the floor halt acts, and it
  sells nothing, so the owner must act with `exit` or a hand sell (N5, N6).
- **Clock rollback.** Until the wall clock catches up, no protective unit runs, so the coin is unprotected, with no
  upper limit on how long. A rollback can also stop the account chain (3.5).
- **Withdrawals.** Under N1a's default, a withdrawal into B's raw band spends the raw pair's margin until a B check
  sees raw equity above the floor plus M. A fresh M does not restore it. A later fall in marks below R_w then sells.
  B does not act on an unexplained balance fall until it is matched, though the floor checks still run (3.9).
- **Sells from another profile.** At a restart under a halt, an app sell left from an earlier profile is outside the
  runner's namespace, so it gets no cancel request and can fill (3.3, N2).
- **The limit still holds.** Under the PLB budget the app's position is sized so that the floor holds even if the
  position goes to zero (B1:446-447). The change is in how much of the budget can be lost, not in the limit itself.
- **Fewer forced sales.** Missed slots are common while 7.5% of book reads are refused (PH:729-730). The sales they
  forced, each one realizing a loss, go away, unless Md is not below the signed daily loss in force. Then every hold
  stop sells at its first check (3.9).
- **No edge.** Holding or selling changes the spread of outcomes, not the ceiling on reaching a target (PH:739-741).
  This is not legal, tax or investment advice.
