# Amendment A1 to the standing deployment design: protective hold after a safety stop

Date: 2026-11-12 (Asia/Seoul).
Status: proposed. It amends [standing deployment](2026-11-12-standing-deployment-design.md) (below, "SD"). PR #27 is
already merged on main as `2fffeff`, an ancestor of `3868cde`, so this is a new docs PR, not a change to an open one.
Nothing is implemented. Merging this document approves the design only. It signs nothing, arms nothing and sends no
order. It changes `tools/signer/sign.py` and the owner-log fold in design. The hard rules reserve the `sign.py` change
for the owner's approval. This document asks for that approval in design, and the implementation PR asks again.

**Citations.** `path:line` is rev `3868cde` (main, after PRs #29 and #30). The two 2026-11-12 specs are byte-identical at `9b603fe` and
`3868cde` (`git diff 9b603fe 3868cde` on them is empty), so their line numbers hold at both revs. Short names, all under
`docs/superpowers/specs/`: SD = `2026-11-12-standing-deployment-design.md`, CL =
`2026-11-12-controlled-launch-and-planner-design.md`, PLB = `2026-11-11-principal-loss-budget-design.md`, UNI =
`2026-11-11-upbit-krw-universe-design.md`. D11 and D12 are rows of `2026-10-23-compliance-gate-and-odds-engine-design.md`
(`:70-71`).

Owner financial parameters stay private and are not written here. This is software design, not legal, tax or
investment advice. Neither the software nor its author is a licensed advisor.

## 0. The change in one paragraph

Today SD 6.4 sells the held coin at once after every safety stop except a halt (SD:197-216). The owner asked for
something else: hold the coin while the price holds up, and sell only on a serious downturn signal or when the account
nears its loss limit. This amendment puts a **hold** mode in front of the existing sale, which becomes **sell** mode.
In hold, the app checks the rules of 6.4.3: S, T, B (a halt line and a daily line), I and E, plus W for a universe
profile. The first rule that fires starts the sale. A rule that cannot be checked also starts the sale (SD-O13). A halt still sells nothing (SD-O1), and a sale order still resting at a halt gets a
cancel request. With the account chain stopped, nothing can act, as today. A hold lasts at most until the scheduled
end of the window it started in. The three new numbers, the trailing fraction X, the margin M and the daily margin Md,
are signed by the owner in the `standing_armed` entry. Without them, the app keeps today's sell-at-once.

## 1. Owner request and answers (2026-11-12)

- **Request.** After a safety stop, keep comparing the price with the armed strategy. Hold while the price is rising.
  Sell only when (1) a serious downturn signal is seen, or (2) the account is at risk of crossing, or has crossed, the
  owner's loss limit. The goal is to defend returns.
- **A1.** Keep SD-O1: a halt sells nothing. Add a pre-emptive sell when equity enters a band near the limit: the limit
  plus an owner-signed margin.
- **A2.** For now, a downturn signal is the armed strategy's own sell signal, plus a trailing stop: sell if the price
  falls X% from the high since the stop. X is owner-signed.
- **A3.** Later, the owner will build internal detection models and swap them in repeatedly. No model may bypass the
  study and odds evidence gates.
- **A4 (decisions on this document, same day).** The owner accepted the defaults of SD-O5, SD-O6, SD-O8, SD-O9,
  SD-O10, SD-O11, SD-O13 and SD-O14. For SD-O7 the owner chose the alternative: B also guards the signed daily loss,
  with its own signed daily margin Md. For SD-O12 the owner chose a third option: a universe profile also gets a
  strategy rule S, which re-runs the universe chooser on bars read after the stop (6.4.3).

## 2. Facts this design rests on

- **Held coins stop the chain on main.** The interval source refuses any held position and any fill inside an
  interval (`execution_launch/account_interval.py:117-122`). This amendment needs the blocker-1 code first (6.4.7).
- **The floor below activation is the peak on main.** Below A the requested floor is H (`execution_control/risk.py:274-277`),
  so the floor is never below equity. PLB's fixed floor C is design only (PLB:5). This amendment needs the PLB code
  first (6.4.7).
- **The exit route.** `Runner.submit_exit` needs a quote at most 10 s old (`execution_launch/runner.py:331`), an
  account at most 30 s old (`runner.py:332-334`), and `data_complete` and `external_flows_known` both true
  (`runner.py:335-337`). It does not check the stopped flag and does not call `_assess` (`runner.py:488-504`).
  `Coordinator.submit_exit` takes a signal that is already built and runs it in an explicit unit that reads its book
  only afterwards (`execution_launch/coordinator.py:547-559`, `741-743`).
- **The work lock.** It is a plain `threading.Lock` (`coordinator.py:345`). Monitor units (`coordinator.py:476`) and
  explicit units (`coordinator.py:549`) both take it, so a sale from inside a monitor unit would deadlock.
- **What a sell needs at the controller.** The account at most 30 s old, server time within 60 s, the same Seoul date
  for now, the account time and the server time, and a clock not behind the last journal row
  (`execution_control/controller.py:358-365`). Instrument rules at most 5 minutes old (`controller.py:605-606`).
  Complete, reconciled data (`controller.py:608-609`). Holding sources that agree (`controller.py:571-573`). Halt,
  session and stake checks apply to buys only (`controller.py:613-640`). Unfilled active sells count against sell
  capacity, `CANCEL_REQUESTED` included (`controller.py:26`, `548-549`, `574-577`).
- **No halt test on the sell path.** On the order paths, the journal halt row is written only by `_snapshot_risk`,
  which runs from `observe` or from a buy (`controller.py:416-429`, `433-441`, `622`). The only other writer is the
  explicit `Controller.halt` (`controller.py:873-889`), which only tests call at `3868cde`. An explicit unit publishes
  and acts without observing (`coordinator.py:547-559`).
- **Exits are GTC on main.** `validate_order` accepts only `gtc` outside KIS (`execution_control/model.py:95-97`), and
  the runner uses the profile's time in force (`runner.py:351-354`). The driver's own sells are priced at the bid less
  the protocol slippage, floored to the tick (`execution_launch/driver.py:215`, `227`).
- **Repeated exits need new ids.** The client id is a digest of the profile contract, the signal id and the side. A
  repeated signal id returns the old order or raises `RUNNER_DECISION_CHANGED` (`runner.py:347-351`, `498-501`).
- **Halt and daily stop.** When marked equity is below the effective floor or the signed `L`, the controller writes a
  journal `halt` and tries a `system_halt` (`controller.py:416-429`). `observe` never places an exit
  (`controller.py:434`). The daily stop blocks entries only (`controller.py:402-409`). `RiskResult` carries the
  effective floor but neither `L` nor the signed daily loss (`risk.py:86-101`; `controller.py:402`, `416`).
- **Owner-log halts.** `system_halt` rows fold into `halted_floors` (`core/compliance/owner.py:505`, `562`). The
  controller's halt latch, and with it `PERSISTENT_HALT`, comes from its own journal only (`controller.py:192-206`,
  `436-440`). It reads `halted_floors` only in the floor-relaxation route (`controller.py:457`). An owner-log halt
  also raises the signed `total_loss_floor_krw` to the halted floor (`owner.py:557-558`), which the halt test compares
  (`controller.py:416-420`), so it halts again only while equity is below that floor. The review verifier refuses on
  `halted_floors` (`execution_launch/review_auth.py:163-165`).
- **`Controller.kill` ignores its reason.** It writes `owner_requested` or `clock_ambiguous` to the journal and
  `execution control kill` to `system_disarm`, whatever the caller passes (`controller.py:863`, `867`). Without a
  current account it writes no `system_disarm` (`controller.py:856-865`).
- **Equity.** A held coin is marked at the Upbit ticker's last trade price, at most 30 s old
  (`execution_accounts/upbit_collector.py:393-401`, `416-423`; `execution_accounts/provider.py:241`). The high
  watermark follows the interval maximum, and the daily loss follows the interval minimum
  (`execution_accounts/baseline.py:309-315`).
- **The strategy's sell signal.** `target_fraction` returns 0 during warm-up and whenever the fast mean is not strictly
  above the slow mean (`execution_launch/program.py:165-183`). The mark is the book midpoint (`driver.py:268`). The
  decision made at bar k executes at bar k+1 (`driver.py:295-297`). Live history records each slot's decision when the
  slot is recorded (`execution_launch/live_history.py:328-334`, `462-475`). The driver targets 0 at the window end
  (`driver.py:297`), and the evaluator always ends flat (`execution_launch/strategy.py:360-362`, `393`).
- **The window after a stop.** A missed slot is never backfilled (`live_history.py:15-16`, `318-323`). Slot units are
  gated only by the coordinator's own stop event (`coordinator.py:616-618`), so after a runner error they keep running.
  `Coordinator.stop()` ends them and sends no venue cancel (`coordinator.py:627-631`). Monitor units continue after a
  stop (`coordinator.py:614-623`).
- **The clock.** `Coordinator._time` refuses a time earlier than the last one (`coordinator.py:384-389`). The timer
  waits on the wall clock (`coordinator.py:201-204`), so a backward step shows as a silent wait, not as a refusal.
  `RUNNER_CLOCK_ROLLBACK` makes the tick return `blocked` and does not stop the runner (`runner.py:404`, `458-459`).
  CL 4.6 says it stops the runner (CL:238). The code does not.
- **Monitor units.** They run every `monitor_seconds` (5 to 20, default 10) until `monitor_until`, which is at most
  window end + 1 day (`coordinator.py:84`, `277`, `159-164`, `314`). They refresh the terms when due and ignore a refresh
  failure (`coordinator.py:463-470`, `479-482`). They capture the account, publish no book, observe risk and reconcile
  orders (`coordinator.py:474-501`). A unit must fit in `MONITOR_UNIT_SECONDS` = 5 s; `load_context` alone takes about
  1.4 s (`coordinator.py:75-78`).
- **After `monitor_until`.** No scheduled unit runs. Explicit units still run (`coordinator.py:548`, `646-647`), but the
  account chain stops 30 s after the last capture (CL:206-208).
- **Book reads fail often today.** 3 of 40 reads (7.5%) were refused in the two PC clock runs
  (`docs/pc-clock-decision-2026-11-12.md:55`). The 1,000 ms allowance is a later code PR (`:80`, `:106-110`).
- **The universe chooser is on main (PR #30).** `choose(spec, state, now_slot, lag_slot)` makes one decision by UNI
  section 14 rules 1-8 and returns the new `ChooserState` (held coin h and hold count). It reads only recorded slots
  and the decided path, never fills or holdings (`execution_launch/program.py:190-254`). An unavailable ticker read
  gives a slot without prices (`program.py:199-206`).
- **No home for new signed numbers.** `limit_set` has exactly two keys (`owner.py:151-152`), and `_data_problem` requires
  the exact key set of a kind (`owner.py:169-170`). The control journal accepts a closed set of event kinds
  (`execution_control/store.py:25-27`).

## 3. Edits to SD 6.2 (safety stops)

Add after the current text (SD:184-185):

- **What every safety stop does first.** The coordinator calls `Coordinator.stop()`, so no slot runs again
  (`coordinator.py:616-618`, `627-631`). It then requests a cancel of every active buy in the runner's namespace through
  `Coordinator.cancel` (`coordinator.py:737-739`). A GTC buy left from the last slot could otherwise fill during a
  hold. A request is not a confirmed cancellation (`coordinator.py:738`), the unit can be refused, and an order without
  a venue id gets no request (`controller.py:750-751`). So after every later monitor unit the coordinator requests
  again for each buy that reconciliation (`coordinator.py:493`) does not show terminal. A buy that fills anyway adds to
  the held units, which the hold or the sale then covers. Active sells are left alone, except at a halt (6.4.5);
  otherwise 6.4.4 handles them.
- **Detection, in the coordinator.** A missed slot is a slot unit that is refused or skipped (`coordinator.py:197-199`,
  `526`, `535`). A runner error is `runner.stopped` while the coordinator's stop event is clear (`coordinator.py:621`).
  A clock backward is any unit refused with `COORDINATOR_CLOCK_ROLLBACK`, or any tick with `RUNNER_CLOCK_ROLLBACK`;
  the runner does not stop itself on it (`runner.py:458-459`). Section 8 corrects the CL 4.6 row. A tick blocked with
  `RUNNER_IMPLEMENTATION_REVIEW_FAILED` while the coin is held is `held_at_end` (section 4).
- **Missed boundary.** If the account chain survives it (a blocker-1 boundary retry worked), it is handled as a missed
  slot. If not, it is the account-chain stop.
- **Reason strings.** Each stop writes `system_disarm` with the standing id and one of: `safety_missed_slot`,
  `safety_missed_boundary`, `safety_runner_error`, `safety_account_chain`, `safety_halt`, `safety_clock`,
  `safety_restart`, `safety_held_at_end`. For a standing id, CL 4.1 step 3 writes `safety_restart`. It keeps
  `launcher_restart` for session ids (CL:155-157). `Controller.kill` must write the caller's reason into the standing
  `system_disarm`; today it ignores it (`controller.py:863`, `867`). SD already changes that writer (SD:233).
- **Startup.** After step 3, sell mode (6.4.4) starts when all of these hold:
  1. the newest standing `system_disarm` for the schedule's deployment id has a reason that starts with `safety_` and
     is not `safety_halt`; or the newest standing entry for that id passed its `valid_until` with no later standing
     `system_disarm` (the process ended before the check of section 4 wrote one);
  2. the startup unit's risk result has no `PERSISTENT_HALT` (6.4.5);
  3. the coin is held at or above the minimum order;
  4. now is before the end of the schedule's last window plus one day.

  A restart never resumes a hold: the high, the marks and the stop time live in memory only. The sale runs in the
  coordinator that startup builds (CL 4.1 step 2); its monitor units drive the attempts until its `monitor_until`.
  When no window is left to start (SD 5.1 skips a started window, SD:124-126), startup builds a sale-only coordinator
  for the last window, with `monitor_until` = its end + 1 day (`coordinator.py:314`), and calls `Coordinator.stop()`
  before `run()`, so no slot runs. `run()` accepts a start after `window.end` but refuses a start too close to the next
  slot inside the window (`coordinator.py:599-600`); the implementation plan settles that case. If no coordinator can be
  built, status shows `autosell_blocked`.
- **Startup under a halt.** When the newest standing `system_disarm` is `safety_halt`, or the startup unit's risk
  result has `PERSISTENT_HALT`, startup starts no sale. It still applies 6.4.5 in the coordinator it builds: it requests
  a cancel of every active sell in the runner's namespace and repeats the request after every later monitor unit until
  reconciliation shows each sell terminal. The journal does not record who sent a sell (`controller.py:666-668`; every
  exit uses `_exit_session_id()`, `runner.py:438`, `503`), so this includes an owner `exit` sent before the restart.
  A red toast asks the owner to send `exit` again.
- **A chain that comes back.** After an account-chain stop, the app never holds. When reads work again, in the same
  process (the retried disarm of SD:185 succeeds) or after a restart, sell mode starts.

## 4. Edit to SD 6.3 (normal end)

Add: "A normal end must not leave a held coin unmanaged. If the coin is held at or above the minimum order when the
driver stops managing it, that moment is the safety stop `held_at_end`, written as `safety_held_at_end` instead of
`standing_ended`. The driver stops managing the coin at the first tick that returns `blocked` with
`RUNNER_IMPLEMENTATION_REVIEW_FAILED` (`runner.py:159-162`, `419-420`, `458-459`). That happens at the review's expiry
(`review_auth.py:171`, `207`). It also happens mid-window when any other check of `review_auth.py:163-170` fails: the
owner log does not fold, the approved state is not valid, the code is not signed, or the key or the code hash differs.
Each failure blocks the driver's sells and its window-end flatten, not only its buys. A non-empty `halted_floors` is a
halt instead (6.4.5). The driver also stops at the end slot of the window that is running when the deployment ends
(`valid_until` or the last window); the check runs at the first monitor unit after that slot's 10 s window.
`valid_until` alone is not such a moment: the driver keeps selling without a session (`runner.py:438`) and flattens at
the window end (`driver.py:297`). So at a mid-window `valid_until` the app writes no disarm and does not stop the
coordinator (`Coordinator.disarm` would, `coordinator.py:673`). At the check after that window's end slot it writes
`safety_held_at_end` if the coin is held, else `standing_ended`. A restart in between sells (section 3, startup
condition 1)."

Reason: SD's "each window already ends flat" (SD:195) is false when the review expires inside a window.

## 5. Replacement for SD 6.4

### 6.4 Protective exit after a safety stop (Q6, amended by A1)

#### 6.4.1 Two modes

- **Hold.** The app keeps the coin and checks the rules of 6.4.3. The first rule that fires switches to sell. A hold
  never resumes after the sale has started.
- **Sell.** The sale of 6.4.4: today's auto-sell, with exact order mechanics.

What it acts on is unchanged: every held unit of the profile's coin for a fixed profile, or the held coin for a
universe profile (SD:199-201).

The app enters hold only when all of these hold:

1. SD-O5 lists the stop as a hold stop (6.4.2).
2. The protective values are in force (section 6 of this amendment). The stop may close several entries with the same
   deployment id (SD:98-100); the one that counts is the newest of them by sequence number. It carries X, M and Md, its
   `valid_until` bounds E (6.4.6), and, under the SD-O14 default, the stop's Seoul date is after its stamp date.
3. The end time (6.4.6) is still ahead.
4. No rule of 6.4.3 fires at the first check. The first check is the first monitor unit after the stop that completes
   T and B; T's high starts there. If none completes within 30 s of the stop on the monotonic clock, the app goes
   straight to sell (I).

Otherwise the app goes straight to sell. A halt and a stopped chain enter neither mode.

During a hold, a clock rollback switches to sell, a halt ends the hold (6.4.5), and a stopped chain blocks everything.

#### 6.4.2 Per-stop table

Rules: **S** strategy sell signal (fixed and universe profiles), **W** flag (universe profile), **T** trailing stop,
**B** risk band, **I** inputs, **E** end time (6.4.3).

| Safety stop (6.2) | Default mode (SD-O5) | Why | Rules that run | Inputs needed | When inputs are missing |
|---|---|---|---|---|---|
| Missed slot | hold | Account, risk and order units still work. Only the strategy's slot is lost | S (plus W for a universe profile), T, B, I, E | Monitor units (account capture and risk); per bar, one book read for a fixed S, or one ticker read and one flag read for a universe S and W | A refused or skipped unit checks nothing, and a refused or skipped per-bar unit counts as a failed per-bar unit. After 30 s without a T and B check, I fires and the app sells. A failed per-bar unit restarts the S series (6.4.3, missed bars); a failed universe read leaves that bar without prices |
| Missed boundary, chain alive | hold | As above | As above | As above | As above |
| Runner stopped by an unexpected error | hold | Monitors and the chain keep running (`coordinator.py:614-623`). S never calls the driver: it uses the last recorded decision and the program function | As above | As above | As above. If S raises, I fires |
| Coin held when the driver stops managing it (`held_at_end`, section 4) | hold until E | As above | As above | As above | As above. At a window end, E has already passed, so the app sells at once |
| Clock backward | sell, once units run again | T, I and E depend on the clock that just failed | none | A wall clock past its last value (`coordinator.py:384-389`) | No unit runs, protective units included, until then |
| Open arming at startup (restart) | sell | The hold's state is in memory only and is lost | none | The startup unit's account and a book | A restart over 30 s stops the chain (CL:206-208): see the next row |
| Account chain stopped (including a missed boundary that stops it) | **nothing can act** | No current account observation (`runner.py:332-334`; `controller.py:358-363`) | none | — | Nothing checks and nothing sells, exits included. Status shows `autosell_blocked` with a red toast. When reads work again, the app sells (section 3) |
| Halt | nothing (SD-O1); active sells get cancel requests (SD-O9, 6.4.5) | — | none | — | — |

If X, M and Md are not in force, every row that says hold sells instead.

#### 6.4.3 The rules

Notation, per unit:

- `q`: the held units of the coin in the unit's account observation.
- `p`: that coin's mark in the unit's capture, the Upbit ticker's last trade price (`upbit_collector.py:393-401`,
  `416-423`). On main it is at most 30 s old. Under approach A (6.4.7) it can be older; I covers a bid that fell below
  it.
- `Eq`: the observation's marked equity, the number the halt test uses (`controller.py:420`).
- `line`: the halt line, `max(effective floor, L)`, computed exactly as the halt test computes it
  (`controller.py:416-420`). It is a new field `RiskResult.halt_line`, set by `_snapshot_risk`. It is `None` when there
  is no floor, or when the owner log does not fold.
- `daily`: the observation's `observed_daily_loss`, the number the daily stop compares with the signed daily loss
  (`controller.py:402-406`). It is the day's largest loss so far: the day-open equity minus the lowest interval equity
  since Seoul midnight, never below 0. It does not go down when the price recovers, and it restarts at 0 at each Seoul
  midnight (`baseline.py:309-311`).
- `dlimit`: the signed `daily_loss_krw` (`controller.py:402`). It is a new field `RiskResult.daily_limit`, set by
  `_snapshot_risk`. It is `None` when no daily loss is signed, or when the owner log does not fold.

The rules:

- **S, strategy sell. Fixed profile.** Two parts.
  - *At the first check.* S reads the newest decision recorded in the window's live history through a new read-only
    `LiveHistory.last_decision` (`live_history.py:328-334`, `473`). If its `target_fraction` is 0, S fires. This is the
    studied strategy's own pending sell: the decision at bar k executes at bar k+1 (`driver.py:295-297`), and a missed
    slot is exactly where it never executes. If the window's history holds no decision yet (its first slot was missed
    while a coin was held, SD:149-150), S fires: the fixed driver's first slot targets 0 (`driver.py:283-285`).
  - *After that, per bar.* At each slot instant of the window (`coordinator.py:153-157`), a per-bar unit runs in place
    of the slot. It reads the book once (`coordinator.py:408-413`) and appends `(bid + ask) / 2`, the driver's mark
    (`driver.py:268`), to S's marks. S calls `target_fraction(program, marks)` (`program.py:165-183`) with the program
    of the reviewed composition (`coordinator.py:771`, `776`). S fires when at least `slow_window` marks exist and the
    result is 0. With fewer marks, S is not ready and does not fire, so the program's warm-up 0
    (`program.py:179-180`) is never read as a sell. The marks start empty at the stop. Pre-stop marks are not spliced
    across the missed slot. A failed book read clears the marks.
- **S, strategy sell. Universe profile (SD-O12, owner's choice).** The same restart idea as the fixed S, applied to the
  universe chooser (UNI section 14, rules 1-8). A missed slot ends the studied path (UNI:677), so S starts a new
  series instead of splicing across the gap.
  - *At the first check.* S reads the newest recorded decision and its state (held decision h and hold count) through
    `LiveHistory.last_decision`, from the universe history row v2 (UNI:606-614). If that decision is cash, or a coin
    other than the held coin, S fires: it is the studied path's own pending sell or switch. If the window's history
    holds no decision yet, S fires: the decided path starts in cash at the window's first slot (UNI:675). No
    `ChooserState` is built.
  - *After that, per bar.* At each slot instant, the per-bar unit makes the study's two reads in the study's order:
    one flag read (shared with W), then one ticker read over `listed` of the snapshot in force, limited to the KRW
    markets in that flag read, and no ticker read if the flag read failed (UNI:360-361). It records one `ChooserSlot`
    per bar. `top_n` is the snapshot's top-N alone, at most `max_candidates` coins (`program.py:225`); the held coin
    appears only in `prices` and `flags`. `price_X(j)` is exactly as UNI section 14 defines it (UNI:668, 696-699): the
    ticker's `trade_price`, only if X's trade time is within 60 s of the slot and the price and the trade-time offset
    fit the section 14 encoding (a decimal string of at most 16 characters; a read of more than 320 markets gives no
    prices), the encoding history row v2 uses (UNI:611). A failed read records the bar as the study does: no prices,
    and no flags either when the flag read failed (`program.py:199-206`).
  - *The state.* S keeps a `ChooserState`. It starts as the state `choose` returned with the newest recorded decision:
    held = that decision, which the first check has shown is the held coin h, and the hold count after it. If row v2
    stores the state before that decision (UNI:624), S first applies the decision to it as `choose` does
    (`program.py:254`). Each slot instant before S is ready adds one to the hold count. Once the series holds
    `lookback_slots` + 1 bars, each bar calls
    `choose(spec, state, now_slot, lag_slot)` (`program.py:208-254`), with `lag_slot` the bar `lookback_slots` earlier
    in the new series, and keeps the state it returns. S fires when the decision is not h, whether cash or another coin.
    The buy half of a switch is dropped: a hold never buys. With fewer bars, S is not ready and does not fire again
    after its first check.
  - *No snapshot in force.* A snapshot is in force from `max(built_at, 09:40 KST)` on its day until 09:40 KST the next
    day (UNI:284). If none is in force (the day's build failed, UNI:311, or has not finished), the top-N is empty and,
    as in the study, no ticker read is made. The bar has no prices, so the chooser keeps h (rule 2) unless h is
    `warning` (rule 1). When its flag read worked, such a bar is not a failed per-bar unit for I.
  - Cost: two Upbit requests per bar, on top of the monitor units.
- **Missed bars (both S kinds).** A per-bar unit that the timer skips (`coordinator.py:197-199`), or that is refused
  before its reads, is a failed per-bar unit for I. As in the study, where a missed slot ends the path (UNI:677), it
  restarts S's series: a fixed S clears its marks, and a universe S clears its bars and keeps its `ChooserState`, with
  one added to the hold count for the missed slot instant. A universe read that fails inside a unit that runs is not a
  missed slot: it records a bar without prices, as the study records an unavailable read (UNI:670). So every series
  is gap-free, and `lag_slot` is always exactly `lookback_slots` slot instants earlier.
- **W, flag. Universe profile only.** In the same per-bar unit, the held coin's flag class is read with the universe
  flag reader. W fires on `warning`, `unknown` or `absent` (`core/compliance/rules.py:1012`, `1048-1061`), where
  `absent` means the flag read worked and does not list the held coin. When the flag read fails, W checks nothing at
  that bar, and the failure counts only for I (two failed per-bar units in a row). `unflagged` and `caution` hold. This keeps the chooser's rule 1 (UNI:678) from the first bar, before S is ready, and it also
  sells a coin the read cannot vouch for.
- **T, trailing stop.** Price: `p`. Cadence: every monitor unit. The high starts at `p` at the first check (6.4.1), and
  it only moves up: `high = max(high, p)`. T fires when `p <= high * (1 - X)`.
- **B, risk band.** Cadence: every monitor unit, after `Controller.observe` (`coordinator.py:491`). B has two parts
  (SD-O7, owner's choice):
  - *Halt line.* B fires when `Eq <= line + M`, or when `line` is `None`.
  - *Daily line.* B fires when `daily >= dlimit - Md`, or when `dlimit` is `None`. Because `daily` never goes down
    within a day, a day whose loss reached `dlimit - Md` at any time before the stop sells at the first check, even if
    equity has since recovered. After Seoul midnight the new day's `daily` counts. If Md is not below the signed daily
    loss, `dlimit - Md <= 0`, and `daily` is never negative (`baseline.py:309-311`; `risk.py:204`), so the daily line
    fires at the first check and the app sells at once. A hold therefore needs a signed daily loss above Md.
  - Only the signed daily loss counts. The other causes of the daily stop, the policy daily budget
    (`DAILY_LOSS_BUDGET_REACHED`, `risk.py:312-314`) and the recovery status (`controller.py:403-405`), do not fire B
    (SD-O7). `dlimit` is read at every check, so a `limit_set` that takes effect during a hold changes it. Md stays the
    value in the entry that counts (6.4.1, section 6).
- **I, inputs.** I fires on any of these:
  - no monitor unit has completed T and B within the last 30 s (`ACCOUNT_AGE`, `coordinator.py:72`), measured on a
    monotonic clock, so a silent wait after a backward clock step also counts (`coordinator.py:201-204`);
  - the terms refresh has failed (`_terms_blocked`, `coordinator.py:458`), because sells refuse once the rules pass 5
    minutes (`controller.py:605-606`);
  - two per-bar units in a row fail. A per-bar unit fails when the timer skips it, when it is refused before its
    reads, when a fixed S's book read fails, or when a universe S's flag read or ticker read fails (a failed flag read
    also means no ticker read: one failure). A universe bar that makes no ticker read only because no snapshot is in
    force is not a failure;
  - S raises;
  - an approach-A audit or cross-check mismatch, or the capture's bid-gap alert (6.4.7). Y is defined and signed in the
    blocker-1 spec, whose code lands before this code (6.4.7).

  The owner kept this default (SD-O13).
- **E, end time.** E fires at the hold's end time (6.4.6).

**Why these prices.** T and B use what each monitor unit already has, so they add no read to a 5 s unit
(`coordinator.py:75-76`). A fixed S uses the midpoint and a universe S the ticker's last trade: each is the price its
program was studied on (`driver.py:268`; UNI:668). The sale uses the bid. The last
trade can sit above the bid, so M must cover the spread, the fee and the move between two checks (SD-O10).

**What the rules can and cannot do.** No rule buys. Each rule can only end a hold earlier. The hold's own risk is the
time it keeps the coin, which 6.4.6 bounds.

#### 6.4.4 Sell mode

- **The attempt unit.** Each attempt is its own explicit unit (`coordinator.py:547-564`). The coordinator's loop runs it
  right after the monitor unit that found it due, never inside one, because the work lock is not reentrant
  (`coordinator.py:345`, `476`, `549`). Its action, at the unit's time:
  1. Call `Controller.observe(now)`. If the result has `PERSISTENT_HALT`, send nothing (6.4.5). This is the halt test
     that the sell path lacks today (`controller.py:613-624`).
  2. Build the exit from this unit's own book and account. Quantity: every held unit, floored to the lot. Price: the
     bid less the protocol's slippage, floored to the tick, the price of the fixed driver's own sells
     (`driver.py:215`, `227`). It is a limit at or below the bid, so it fills at once unless the bid falls past it. A
     universe profile uses IOC and its own exit price once the universe code provides them (CL:217-218; CL-D4,
     CL:441).
  3. Send it with `Runner.submit_exit` (`runner.py:488-504`). Signal id: `protect:` plus a digest of (deployment id,
     stop time, attempt number). Each attempt has a new id (`runner.py:347-351`, `498-501`).
- **Attempt rule.** It is checked after every monitor unit while in sell mode:
  1. If no sell in the runner's namespace is active, run an attempt.
  2. If one is active (one of ours, or one the driver left), request its cancel and send nothing in this unit. A
     pending cancel is not repeated (`controller.py:750-751`), and it still counts against capacity
     (`controller.py:574-577`). The next attempt goes only after a later monitor unit's reconciliation
     (`coordinator.py:493`) shows the old order terminal.
  3. A refused attempt (no order placed) is retried at the next monitor unit.

  This replaces SD's "once per bar" (SD:202-203) with "as soon as the previous order is gone". Reason: in a fast fall,
  a resting limit would otherwise wait 300 s per try. Cost: an attempt unit (a capture, a book read, an observe, and a
  reserve and a dispatch that each run `load_context`, about 1.4 s each: `coordinator.py:77-78`; `controller.py:438`,
  `612`) lasts about 6 to 8 s, so it can make the next monitor unit late; a skipped monitor triggers a gap reconcile
  (`coordinator.py:566-573`).
- **Boundaries.** A boundary unit cannot run late. It starts only in the `boundary_lead_seconds` before the boundary
  (`coordinator.py:169-170`, `197-199`), and a boundary that no capture spans stops the account chain on main
  (`account_interval.py:111-116`; section 3, missed boundary). So no unit this amendment adds (an attempt, a buy or
  sell cancel request of section 3 or 6.4.5, or a per-bar unit) starts within `BOUNDARY_BAND` (20 s,
  `coordinator.py:73`) before a boundary: each Seoul midnight and, with a recovery condition, each 22:00 KST. Slots
  already keep that distance (`coordinator.py:321-325`). A unit that falls due then waits for the first monitor unit
  after the boundary unit.
- **Partial fills.** A remainder at or above the minimum order goes in the next attempt. A remainder below the minimum
  quantity or the minimum notional stays in the account (PLB 4.5) and ends the sale with status `protective_dust`.
- **When the sale ends.** When the holding is below the minimum order and no buy in the runner's namespace is active
  (section 3); on the owner's `close`; when the owner's `exit`
  order is recorded (6.4.8); at a halt (6.4.5); or at `monitor_until`. After `monitor_until` no scheduled unit runs,
  so no automatic attempt is made (`coordinator.py:159-164`, `614`). The account chain then stops 30 s after the last
  capture (CL:206-208), and after that an owner `exit` refuses too. Status shows `autosell_blocked`. Each standing
  window's coordinator is built with `monitor_until` = window end + 1 day, the maximum (`coordinator.py:314`). A normal
  handoff closes it earlier (SD 5.1).
- **Overshoot.** For a sale that T or B started, the status log records the rule and, for B, which line fired; the high
  (T), `line + M` and `Eq` (B's halt line) or `dlimit - Md` and `daily` (B's daily line); and the fill price. A gap
  past the trigger is recorded as it happened, never as a fill at the trigger price
  (`docs/superpowers/specs/2026-10-30-equity-policy-and-strategy-design.md:179`).

#### 6.4.5 Halts (SD-O1) and PLB (f)

- **What counts as a halt.** `PERSISTENT_HALT` in any risk result. Today that is a journal halt row or a new breach
  (`controller.py:420-429`; `risk.py:290-291`). This amendment adds a non-empty owner-log `halted_floors`
  (`owner.py:505`, `562`) in `_snapshot_risk`, so a halt written only to the owner log also counts. It adds the reason
  only and writes no journal row. This holds only while the owner log folds. When it does not, `halted_floors` is
  empty (`core/compliance/model.py:145`, `153`) and such a halt cannot be seen: B fires on `line` `None`, and the
  attempt unit still sends, stopped only by the journal latch. That matches D11, which keeps exits open on a corrupt
  owner state.
- **At a halt.** Whether the halt is the first safety stop or comes during a hold or a sale, the hold or the sale ends
  and nothing new is sent. As the owner decided (SD-O9), every active sell in the runner's namespace gets a cancel
  request, the driver's own sells included, so the coin stays held as SD-O1 says. After every later monitor unit the
  request is repeated for each such sell that reconciliation (`coordinator.py:493`) does not show terminal, because a
  refused unit sends nothing and an order without a venue id gets no request (`controller.py:750-751`). An owner `exit`
  order is never cancelled this way. A fill can still win the race, because a cancel request is not a confirmed
  cancellation (`coordinator.py:738`). The owner then decides with `exit` (SD:214-215).
- **The two halves of the owner's rule.** "At risk of crossing the limit" works: B sells before the line. "Has crossed
  the limit" never sells for the floor or `L`, because crossing is the halt (`controller.py:416-429`) and SD-O1 sells
  nothing. A price jump from above `line + M` to below `line` between two checks (about 10 s), or inside an attempt
  unit, ends in a halt with the coin held. The signed daily loss is different: reaching it is a daily stop, which
  blocks entries only, not a halt (`controller.py:402-409`). So B's daily line sells both near and past it.
- **PLB (f) is unchanged.** PLB (f) and SD-O1 are about a breach or a halt (PLB:37; SD:212-216). A band sale comes before
  a breach, and the attempt unit's own `observe` stops it at a breach. Risk never vetoes exits (`risk.py:98`), and no
  written rule forbids a sale before a breach. PLB's guarantee still rests on admission (PLB:227). A band sale is best
  effort and never a floor guarantee.
- **Below activation A (after the PLB code).** Under PLB, `Eq >= C` on every price path (PLB:244-247). B's halt line
  therefore fires only once most of the position is lost, and does little in the budget regime. B's daily line does
  not depend on the regime: it fires once the day's loss reaches `dlimit - Md`.
- **At or above A.** The floor follows the peak H (`risk.py:274-275`), so B's halt line acts as a second trailing stop
  near `(1 - delta) * H + M`; its daily line is unchanged. Holding while the price rises raises H through the interval
  maximum (`baseline.py:315`). If H first reaches A while the coin is held, the floor jumps to
  `max(W0, (1 - delta) * H)` (PLB:135, 145). The new floor applies in the same evaluation (PLB:135), so if `Eq` is
  already below it, that same observation halts with the coin held (`controller.py:401`, `417-429`), and B never runs.
  Otherwise B may sell at once, or a later observation may halt.

#### 6.4.6 How long a hold can last (SD-O8)

- **End time.** The scheduled `window.end` (`coordinator.py:153-157`) of the window running at the stop, or the closed
  entry's `valid_until`, whichever comes first. It is not the stop instant: SD's "a missed slot ... ends the window"
  (SD:177) means its slots stop, not its scheduled end. Reason for the bound: the strategy never held past its window
  end (`driver.py:297`), and the study never measured that (`strategy.py:360-362`, `393`). With 48-hour windows
  (SD-O2) a hold can last almost 48 hours, and almost 72 hours with the 72-hour maximum (SD:42).
- **At the end time** the hold switches to sell.
- **Worst case, in plain words.** After a stop, the app keeps a coin that no studied strategy manages, with nobody
  watching, for up to the rest of the window. Five things can go badly:
  1. The price drops in one jump between two checks. The sale fills at whatever the bid is, so the loss can be far
     larger than X.
  2. A jump from above `line + M` to below the halt line halts the account for good. Under SD-O1 nothing sells, and the
     coin stays until the owner sells it.
  3. If the PC sleeps, reboots or loses the network for over 30 s, the account chain stops. The app is blind and sells
     nothing, while the coin can keep falling.
  4. After `monitor_until`, nothing watches at all.
  5. In a fast fall a sale order can rest unfilled until the next monitor unit cancels and replaces it.

  A sale at once avoids 1, 2 and the long exposure of 3. It still fails under 3 if the chain stops before it fills.

#### 6.4.7 Prerequisites: the PLB code and blocker 1 (approach A)

- **The PLB code lands first.** On main the floor below A is the peak (`risk.py:274-277`), so `Eq <= line + M` holds at
  every check and B fires at once: no hold could start, and any dip below H while holding would halt.
- **The blocker-1 code lands first.** On main a held coin stops the account chain (`account_interval.py:117-118`), so
  neither a hold nor a sale can act.
- **The universe history lands first (universe S only).** Only history row v2 records the chooser's decision and state
  (UNI:606-614). On main, live history serves the fixed driver and stores no decision (`live_history.py:1-8`). CL's
  order already puts the universe PRs first (CL:410-411).
- **Mismatches.** Under approach A, a minute-candle audit or cross-check mismatch blocks new entries and alerts, and
  sells stay allowed. During a hold, it fires I. For "sells stay allowed" to be true, a mismatch must not set
  `data_complete` or `external_flows_known` to false; otherwise every exit refuses (`runner.py:335-337`;
  `controller.py:608-609`).
- **The server-time gate and the boundary retry.** A refused read is a refused unit, and I covers a run of them. A
  boundary retry that fails is the chain stop.
- **Long trade gaps.** On main, a held coin with no trade for over 30 s makes the capture refuse
  (`upbit_collector.py:419-421`). A 24 h census on 2026-11-12 found that every one of Upbit's 301 KRW coins had gaps
  over 30 s; BTC had 42, mostly 03:00-05:00 KST. So the owner revised blocker-1 answer 6 the same day. Under approach A
  the 30 s age limit goes: the last trade stays the mark however old it is, and a long gap does not stop the chain.
  When the last trade is older than 30 s, the capture also reads the best bid. A bid at least Y below the last trade
  (Y owner-signed, in the blocker-1 spec) re-checks the floor at the bid, blocks new entries and alerts, like a
  mismatch. During a hold it fires I, because T watches the last trade and would not see a bid that fell while nobody
  traded.
- **One stale-trade rule.** The merged universe spec changes the same collector differently: a last trade older than
  30 s is marked at the best bid if the book is at most 10 s old, and otherwise the capture fails closed
  (UNI:573-575). The owner asked on 2026-11-12 that the two become one rule. The blocker-1 spec defines it for every
  profile, universe profiles included, and the universe accounts PR implements that rule instead. This amendment uses
  its result: T uses the capture's mark `p`, and I fires on the bid-gap alert.
- **The narrow live route.** A halt written by `Controller.halt` (`controller.py:873-889`) is a journal halt row, so
  6.4.5 applies.

#### 6.4.8 Owner commands during a hold or a sale

- **`stop` and `disarm`.** No effect on a hold or a sale, and they write no standing `system_disarm`. The standing
  entry is already closed, and the coordinator has already stopped. A later restart therefore still sells (section 3).
  This keeps PR #27, where only `close` ended an auto-sell (SD:205). Status says so in one line.
- **`close`.** Ends the hold or the sale. It writes `system_disarm` with the standing id and reason `owner_requested`; a
  second disarm for a closed entry is harmless (SD:98-100). A later restart then sells nothing. A red toast says that
  protection has ended and the coin stays held.
- **`exit`.** Ends the hold or the sale only once its order is recorded (reserved or dispatched). A refused `exit`, for
  example because units are still promised to a resting protective sell (`controller.py:574-577`), leaves the hold or
  the sale running.
- **`cancel-all`.** Cancels as usual. It does not end a sale: the next attempt sends again. To stop selling, use
  `close`.

#### 6.4.9 Alerts and status

- **Red toasts:** the stop and the mode chosen; each rule that fires, with its letter (for B, also `halt` or `daily`);
  each attempt and its result; a
  halt that ends a hold or a sale; the end; a `close` during a hold or a sale.
- **Status keys:** `protective_mode` (`hold`, `sell`, `blocked` or `ended`), `protective_stop`, `protective_until`,
  `protective_high`, `protective_trigger_krw` (T's trigger price, `high * (1 - X)`), `protective_band_krw` (B's equity
  line, `line + M`), `protective_daily_band_krw` (B's daily line, `dlimit - Md`) and `protective_rule`.
  `last_protective_request` (CL 5) shows the last attempt.
- **Status log.** Each per-bar unit writes one line to the private status log (SD:145): the time, S's price (the
  midpoint, or the held coin's last trade for a universe profile), the high, the S or W result (a universe S's
  decision) and the program digest. For a universe S the line also holds the bar's `ChooserSlot` (top-N, the coins
  that are not `unflagged`, prices) and the state after `choose`, so a replay can rebuild the series. These lines are
  research data for section 7.

## 6. Edit to SD 4.2 (`standing_armed` data)

Add three optional fields:

| Field | Meaning |
|---|---|
| `protective_trail_fraction` | X for rule T. `0 < X < 1` |
| `protective_margin_krw` | M for rule B's halt line. Whole KRW, `M >= 0` |
| `protective_daily_margin_krw` | Md for rule B's daily line. Whole KRW, `Md >= 0` |

- **All three or none.** Today `_data_problem` requires the exact key set (`owner.py:169-170`). For `standing_armed` it
  gains these optional fields, checked all-or-none and in range. The signer refuses the same. A hand-made entry out of
  range is a malformed log (`owner.ok` false), like the other SD 4.2 checks (SD:86-87). Md is not checked against the
  signed daily loss, which can change later; B handles that case by selling at once (6.4.3).
- **Without them,** a safety stop sells at once, as today.
- **When they count (SD-O14).** As D12 treats a loosening (D12, `:71`): only from the Seoul date after the entry's
  stamp. Any signed X, M and Md loosen today's sell-at-once, so a stop on the signing date sells at once. A hold uses
  the values of the newest entry the stop closed (6.4.1). A later entry does not change a running hold.
- **`live.py` status** prints the three fields empty, each with one plain line on what it does. The owner fills them
  in.
- **`limit_set` is not changed** (`owner.py:151-152`).

## 7. New SD section 11: model iteration

The rule for every later model: **after a stop, a strategy sell (S) comes only from the armed program's own function,
under the reviewed driver.** T and B are owner limits, W is the listing-flag check, and I and E are fail-safes; none of
them is a model. No other rule can sell from a hold, and no new model may enter as one of them.

A new downturn model enters only as a new version of the strategy program, in this order:

1. **Shadow, record only.** Replay the candidate offline over recorded live data: the live history folders (CL:194)
   and the per-bar status-log lines (6.4.9). A read-only research script outside the signed closure, like
   `tools/clock_check.py` (`tools/clock_check.py:1-8`), writes the times it would have sold to a private research log.
   It sends nothing and reads no key. Its output is research data, never study evidence, because registration must
   come before capture (`docs/forward-strategy-validation.md:28-34`; `strategy.py:149-150`).
2. **Version.** The model becomes a new program kind or version in `execution_launch/program.py`, with its parameters in
   `ProgramSpec`. It then enters `program_digest` (`program.py:123-131`), the driver identity (`driver.py:35-38`) and the
   study's capture files (`execution_launch/study.py:59-61`, `63`). It also runs inside the window, because it is part
   of the strategy. The closure change needs a new `code_approved` (`owner.py:789-799`).
3. **Evidence.** The same preregistered prospective study, with the same criteria (`strategy.py:526-539`). Each attempt
   adds one member to the family, which raises the significance bar (CL:398-399). Honest limit: this study scores the
   whole strategy, entries included, over windows that end flat (`strategy.py:360-362`, `393`). It does not measure
   what a detector adds after a stop. Only the SD-O11 alternative would measure that.
4. **Odds.** The daily card is prepared as today. Nothing is skipped (`execution_control/session.py:138-145`).
5. **Activation.** The owner signs `review-approve` for the new driver, then a `standing_armed` entry bound to that
   review (SD 4.1, 4.2). S uses only the program of that reviewed composition. Each status-log line names the program
   digest that made it.
6. **Rollback.** Arm a review of an earlier program, while it is within its review age.

Not chosen: a runtime shadow inside the live process. It would put unstudied code into the signed closure and the live
process, and its output could not be journaled without a schema change (`store.py:25-27`).

The cost is plain: each swap needs a `code_approved`, a 48-hour study and a review. Most studies are expected to find
nothing (CL:403-406).

## 8. Edits to SD 8 (files and tests)

| File | D14 closure? | Driver identity? | Change |
|---|---|---|---|
| `execution_launch/coordinator.py` | Yes (`owner.py:798`) | No (`driver.py:35-38`) | The first actions at a stop (`stop()`, cancel active buys, repeated until terminal); cancels of active sells at a halt, repeated until terminal; detection, including clock rollback and a review failure with the coin held; hold state; T, B and I in monitor units; per-bar S and W units, including a universe S's bar series, its `ChooserState` and its calls to `choose`; the attempt unit; a setter for X, M, Md and the end time; an injected monotonic clock; status keys |
| `execution_launch/live_history.py` | Yes | No | A read-only `last_decision`; for a universe profile it also returns the recorded `ChooserState` |
| `execution_control/risk.py` | Yes | No | `RiskResult.halt_line` and `RiskResult.daily_limit` |
| `execution_control/controller.py` | Yes | Yes, but SD already changes this file (SD:233) | Set `halt_line` and `daily_limit`; treat a non-empty owner-log `halted_floors` as `PERSISTENT_HALT`; write the caller's reason into the standing `system_disarm` |
| `core/compliance/owner.py` | Yes | No | The three optional fields, all or none, with bounds; export X, M, Md and the entry's Seoul stamp date; export the newest standing `system_disarm` reason |
| `tools/signer/sign.py` | No (the closure covers `tools/owner/` only, `owner.py:798`). Reserved for the owner | No | The three fields, all or none, with bounds |
| `tools/owner/live.py` (new in PR L1) | Yes | No | Pass X, M, Md and the end time to the coordinator, with the SD-O14 date rule; `monitor_until` = window end + 1 day; `safety_restart` in step 3; the startup sale, in a sale-only coordinator when no window is left; `held_at_end`, with no disarm at a mid-window `valid_until`; the owner commands of 6.4.8 |
| SD | No | — | Fold this amendment in |
| CL | No | — | 4.6 "Clock moves backward": the runner returns `blocked`, and the coordinator detects the rollback. 4.1 step 3: `safety_restart` for standing ids |
| `docs/owner-runtime-operations.md`, `docs/first-trade-owner-checklist.md` | No | — | The hold; the three signed fields (X, M and Md), all or none; B's halt line and daily line; the universe S; what the owner does after a halt |

Not changed, on purpose: `program.py` (a universe S calls the merged `choose` as it is), `strategy.py`, `driver.py`,
`profile.py`, `model.py`, `capability.py` and `store.py`; `runner.py` beyond SD's own change. No driver-identity file changes beyond the `controller.py` change SD
already makes, and the journal schema stays as it is.

**Order.** CL's code order is universe PRs → PLB code → PR L1 → PR L2 → PR L3 → one `code_approved` (CL:410-411). This
code goes with PR L3, or in a PR L4 right after it, before that one `code_approved`. The blocker-1 code is not in CL's
order. It must also land before this code; its place among L1 to L3 is set when its plan is written.

Tests, by behaviour. All use fakes and a temporary home.

- **Mode.** With X, M and Md in force, a signed `daily_loss_krw` above Md, `Eq > line + M` and
  `daily < dlimit - Md`: a missed slot, a missed boundary with the chain alive, a runner error and `held_at_end` hold.
  A clock rollback and a restart sell. A stopped chain and a halt do nothing. Without the three fields, on the entry's
  signing date (SD-O14), with no signed daily loss, or with `Md >= daily_loss_krw`, every hold stop sells.
- **First actions.** Every safety stop calls `Coordinator.stop()`; no slot runs after it; every active buy gets a cancel
  request; sells are left.
- **S.** A decision of 0 at bar k, bar k+1 missed, coin held: sell at the first check. S is not ready before
  `slow_window` marks, and the warm-up 0 does not sell. After that, a 0 fires S. A failed read clears the marks. S uses
  the reviewed composition's program object.
- **Universe S.** A recorded last decision of cash, or of another coin, sells at the first check. S is not ready before
  `lookback_slots` + 1 post-stop bars. After that, a `choose` decision of cash or of another coin fires S, and no buy is
  sent. The state starts from the recorded one with h = the held coin, and the hold count grows by one per bar before
  S is ready. The starting state is the one after the newest recorded decision. `top_n` never holds more than
  `max_candidates` coins, even when the held coin is outside it. A failed flag read means no ticker read and one
  failed unit. A skipped per-bar unit restarts the series and adds one to the hold count; a failed read inside a unit
  records a bar without prices, so `lag_slot` stays exactly `lookback_slots` slot instants back. With no snapshot in
  force, no ticker read is made, h is kept unless it is `warning`, and I does not count the bar. A price that does not
  fit the section 14 encoding is left out.
- **W.** `warning`, `unknown` and `absent` fire W. `unflagged` and `caution` hold. A failed flag read does not fire W.
- **No decision yet.** With the coin held and no decision recorded in the window, S fires at the first check, for a
  fixed and a universe profile.
- **Boundaries.** No attempt, cancel or per-bar unit starts within 20 s before a Seoul midnight or a 22:00 KST
  boundary, and the boundary unit runs on time while a sale or a cancel loop is active.
- **T.** The first mark sets the high. The high only moves up. T fires at `p == high * (1 - X)`.
- **B.** B fires at `Eq == line + M` and when `line` is `None`. With the PLB code, B's halt line does not fire at the
  first check while `H < A` and `Eq > C + M`, and B as a whole does not fire when also `daily < dlimit - Md`. The daily
  line fires at `daily == dlimit - Md`, when `dlimit` is `None`, and at once when `Md >= dlimit`. A dip that touched
  `dlimit - Md` earlier the same day fires it even after a recovery. It uses the new day's `daily` after Seoul
  midnight. The policy daily budget and the recovery status never fire B.
- **I.** I fires after 30 s on the monotonic clock without a T and B check, even when the wall clock moved back; on a
  terms-refresh failure; on two failed per-bar reads in a row, a skipped per-bar unit counting as one; when S raises;
  on an approach-A mismatch or bid gap.
- **E.** E fires at the scheduled `window.end`, or at `valid_until` when that is earlier.
- **Attempt unit.** It observes first. A price that crosses the line between the B check and the attempt gives a halt
  and no order. The price is the bid less the protocol slippage, floored to the tick, from the unit's own book.
- **Attempt rule.** It sends when no sell is active; with one active (ours or the driver's) it requests a cancel and
  sends nothing; it resends only after reconciliation shows the old order terminal; it retries a refused attempt at the
  next unit; each attempt has a new signal id; the sale ends at dust.
- **Halt.** During a hold or a sale, a halt sends nothing new, and active sells get cancel requests. An owner-log-only
  halt counts.
- **Owner commands.** `stop` and `disarm` change nothing. `close` ends both and writes `owner_requested`, and a restart
  after it sells nothing. `exit` ends them only once its order is recorded; a refused `exit` leaves the sale running.
  `cancel-all` does not end a sale.
- **Startup.** A newest `safety_*` disarm (not `safety_halt`), no halt, a held coin and a time inside the schedule give
  a sale. So does an entry past its `valid_until` with no later standing disarm. `safety_halt`, `PERSISTENT_HALT`,
  `owner_requested` or a time past the last window's end plus one day give no sale. With `safety_halt` or
  `PERSISTENT_HALT`, every active sell left from before the restart, an owner `exit` included, gets a cancel request
  that is repeated until it is terminal. With no window left to start, the
  sale runs in a sale-only coordinator in which no slot runs. Step 3 writes `safety_restart` for a standing id, and the
  test checks the reason actually written.
- **Normal end.** A review expiry with the coin held is `held_at_end` and holds. So is a mid-window review failure
  while the owner log folds (state invalid, code unsigned, key or code hash changed). A review failure because the
  owner log does not fold is `held_at_end` and sells at the first check: X, M and Md are not in force, and B fires on
  `line` `None`. The last window's end with the coin
  held sells. A mid-window `valid_until` is not a stop: no disarm is written and the coordinator keeps running until
  the window's end slot. A restart between that `valid_until` and the window end, with the coin held, sells.
- **Buy cancels.** At every safety stop each active buy gets a cancel request; a refused or unconfirmed one is requested
  again after the next monitor unit; the sale does not end while a buy is active.
- **Halt and resting sells.** A halt as the first stop, and a halt during a hold or a sale, both request a cancel of
  every active sell, the driver's included, and repeat it until reconciliation shows each one terminal. An owner `exit`
  order is never cancelled this way.
- **Owner commands, restart.** After `stop` or `disarm` during a hold, no standing disarm is written, and a restart
  sells.
- **Several entries.** When a stop closes two entries with the same id, X, M, Md, the stamp date and `valid_until` come
  from the newer one.
- **First check.** If no monitor unit completes T and B within 30 s of the stop, the app sells without holding.
- **Signer and fold.** Entries with zero, one, two and three of the fields; the bounds; a hand-made out-of-range entry
  is malformed.
- **Approach A.** A sale started by a mismatch passes `runner.py:335-337`.

## 9. Edits to SD 9 (open owner decisions)

SD-O1 to SD-O4 are already used (SD:263-266), so the new ids start at SD-O5. The owner decided all ten on 2026-11-12
(section 1, A4). This document is written with those decisions.

| Id | Question | Proposed default | Alternative | Owner decision (2026-11-12) |
|---|---|---|---|---|
| SD-O5 | Which safety stops hold rather than sell at once? | Hold after a missed slot, a missed boundary with the chain alive, a runner error and `held_at_end`. Sell at once after a clock rollback and a restart | Hold only after a missed slot and a missed boundary with the chain alive. A restart and a clock rollback always sell | Default |
| SD-O6 | Trailing fraction X | No built-in value. X comes only from the owner's signature in `standing_armed` (`0 < X < 1`); without a signed X the app sells at once | A built-in X used when none is signed | Default (the owner signs X later) |
| SD-O7 | Margin M, and the line it guards | No value. Without a signed M the app sells at once. When signed, M guards the halt line only: B fires at `Eq <= max(effective floor, L) + M` | Also guard the signed daily loss, with its own signed daily margin. The policy daily budget is not offered: after a losing day it is 0, so B would sell at the first loss | Alternative: B guards the halt line with M and the signed daily loss with Md (6.4.3) |
| SD-O8 | Longest hold | Until the scheduled end of the stop's window, or `valid_until` if earlier | A shorter, signed `protective_max_hold_seconds` | Default |
| SD-O9 | A sell still resting when a halt comes | Request its cancel, so the coin stays held as SD-O1 says | Leave it resting. This amends SD-O1 and PLB (f) for this case | Default |
| SD-O10 | Equity measure for B | Marked equity, the halt test's own number. M must cover the spread, the fee and the move between checks | Liquidation equity from a book read in each monitor unit. It needs a PC measurement against the 5 s budget | Default |
| SD-O11 | Evidence for a new downturn model | Shadow replay, a new program version, the same whole-strategy study and review. This does not measure the detector's value after a stop | Also a new evaluator revision for post-stop holds: start from a held position, allow only sells, benchmark against sell-at-once, preregistered and prospective. It needs its own design, and stops are rare, so its power is low | Default |
| SD-O12 | Universe profile | Hold with W, T and B. This departs from A2: the universe chooser's own sell is not available after a stop | Sell at once after a stop, as PR #27 | Third option: a universe S re-runs the chooser on post-stop bars, alongside W, T and B (6.4.3) |
| SD-O13 | When a check cannot run (rule I) | Switch to sell. The sale itself waits until reads work | Keep holding, with a red toast, until inputs return or E fires | Default |
| SD-O14 | When signed X, M and Md count | From the Seoul date after the entry's stamp, as D12 treats a loosening | At once, on the signing date | Default |

## 10. Edits to SD 10 (risks and real odds)

- **Holding can lose more than selling at once.** If the price falls right after the stop, the hold loses up to X from
  the high, plus any gap, the spread and the fee. There is no evidence that holding after a stop does better. The study
  never measured it (`strategy.py:360-362`, `393`), and the frozen retrospective study found no passing candidate
  (`docs/forward-strategy-validation.md:3-6`).
- **S is the studied rule on a new series.** After a stop, S runs on a gap-free series that starts empty and restarts
  after a missed bar (6.4.3), outside any studied window. Only its first-check part uses the recorded, studied decision. It can only end a hold earlier. After
  its first check, a universe S needs `lookback_slots` + 1 bars after the stop before it can fire again; until then
  only W, T, B, I and E guard the hold. It adds two Upbit requests per bar.
- **The daily line sells into the day's loss.** Near the signed daily loss, B sells. That turns a marked loss into a
  realized one, and the price may recover later in the day.
- **A gap through B's halt band (`line + M`) ends in a halt with the coin held** (6.4.5). The "has crossed" half of the
  owner's rule never sells for the floor or `L`. A gap through the daily band does not halt (`controller.py:402-409`),
  and B still sells.
- **The daily line is sticky within a day.** A dip that touched `dlimit - Md` earlier in the Seoul day makes any later
  stop that day sell at once, even after a full recovery.
- **The sale can cause the halt.** B is measured on the last-trade mark. After a sale, equity is cash, lowered by the
  spread, the slippage and the fee. If M does not cover them, the next observation can halt.
- **Blind periods.** A stopped chain, or a time past `monitor_until`, means no protection at all (6.4.6).
- **Last-trade prints.** One spike print raises T's high, and the revert can trigger a sale. That sale is no worse than
  today's sell-at-once.
- **Frequent stops.** At today's 7.5% refused book reads, missed slots are common. Holds will be common, and S will often
  restart its warm-up, until the 1,000 ms allowance lands.
- **Daily side effects.** A sale realizes the loss, and a realized daily loss sets the next day's budget to 0
  (`risk.py:301-303`). On an eligible day (first trading day, or a previous day with exactly zero realized profit), the
  recovery rule trips when the 22:00 checkpoint equity or the current equity is below the day open
  (`risk.py:245-248`, `264-267`). That happens whether the coin is held or sold; a sale changes equity only by the
  spread and the fee.
- **Midnight.** Sells refuse from Seoul midnight until the first capture of the new day (`controller.py:360-361`),
  about one monitor unit.
- **Order churn.** In a falling market, the attempt rule can cancel and resend every one or two monitor units.
- **No edge.** This adds no edge. With no real edge, the chance of reaching a target `T` from `W0` stays at most
  `LB / (T - W0 + LB)` (PLB 7.1, PLB:373-378). Holding changes the spread of outcomes, not that ceiling. This is not
  legal, tax or investment advice.

## 11. Review issues not adopted

All other review issues were adopted. Their citations are given at `3868cde`, like the rest of this document. These
were not adopted, or only in part:

- **"Call `owner.load_context` in each monitor unit for L, the daily limit and `owner.ok`."** Not adopted: it costs about
  1.4 s in a 5 s unit (`coordinator.py:75-78`). The controller exposes `halt_line` and `daily_limit` instead, both
  `None` when the owner log does not fold, in a file SD already changes.
- **"Reprice when the bid falls below the resting limit."** Not adopted as written: monitor units read no book. Instead,
  any still-active sell is cancelled at the next monitor unit, and the price already includes the protocol slippage.
- **"I window of two monitor periods."** Not adopted: one late unit would then sell. I uses 30 s, the account age after
  which the chain itself fails, on a monotonic clock.
- **"Refuse M at or above the signed daily loss, or split M."** Superseded: the owner chose a daily line with its own
  margin Md (SD-O7), and B sells at once when Md is not below the signed daily loss.
- **"Fire S when the last decision is below the held fraction."** Not adopted: the fixed program's target is either
  `exposure_fraction` or 0 (`program.py:179-183`), so 0 is the only sell value.
- **"`stop` ends a hold but not a sale."** Not adopted: `stop` and `disarm` change neither, which keeps PR #27 for sales
  and gives one rule for both modes.
- **"Treat `launcher_restart` as a safety reason."** Not adopted: step 3 writes the explicit `safety_restart` for
  standing ids, so the startup rule reads one reason family.
- **"Owner `exit` cancels protective sells first, or is sized to unpromised units."** Not adopted: changing CL 4.5's
  command is not needed, because a refused `exit` now leaves the sale running.
- **"A partial universe S (sell when the held coin's own return is at or below 0)."** Not adopted: it is a new, unstudied
  rule. The owner chose a re-run of the full chooser instead (SD-O12). Other rules can enter only through section 7.
