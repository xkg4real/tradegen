# Blocker 1, approach A: held-coin account intervals rebuilt from the Upbit trade list

Date: 2026-11-20 (Asia/Seoul).
Status: proposed. Nothing is implemented. Merging this document approves the design only. It signs nothing, arms
nothing and sends no order. In design, it changes the owner-log `limit_set` schema and therefore
`tools/signer/sign.py` (BR-26). The hard rules reserve a `sign.py` change for the owner's approval. This document
asks for that approval in design, and the implementation PR asks again.

**Citations.** `path:line` is rev `1fd8792` (main, after PRs #61-#64). Short names, all under
`docs/superpowers/specs/` unless a path is given: SD = `2026-11-12-standing-deployment-design.md`, CL =
`2026-11-12-controlled-launch-and-planner-design.md`, PH = `2026-11-12-standing-protective-hold-design.md` (PR #31,
merged as `dc8a039`), PLB = `2026-11-11-principal-loss-budget-design.md`, UNI = `2026-11-11-upbit-krw-universe-design.md`,
BC = `docs/account-baseline-contract.md`, RC = `docs/recovery-cutoff-contract.md`, ACC =
`docs/account-collector-contract.md`. D5 and D12 are rows of `2026-10-23-compliance-gate-and-odds-engine-design.md`.
`handoff:` cites a file on the `origin/handoff` branch. Upbit API facts cite the Korean docs pages read on 2026-11-20
(list-pair-trades, list-candles-minutes, list-tickers, rate-limits, websocket-myorder, get-order, list-deposits,
list-withdrawals, pocket-overview) and two changelog notices (api-path-format-error-handling, add-smp-type-default).

**Tags.** Each rule carries the owner answer it rests on: `[Q1]` to `[Q9]`, `[Q6r]` (answer 6 as revised on
2026-11-12), `[Q9-1]` (continue on everything), `[Q9-2]` (the gap high raises H) and `[Y]` (where Y is signed). A rule
with no owner answer behind it is a proposed default and carries the owner question that confirms it, as
`[default, OQn]` (section 9). A rule tagged `[design]` is a mechanism this document chooses to carry out an answer.

Owner financial parameters (L, the daily loss limit, Y, X, M, Md, any amount) stay private and are not written here.
This is software design, not legal, tax or investment advice. Neither the software nor its author is a licensed
advisor.

## 0. The change in one paragraph

Today the account interval source works only while the account is flat: any position, fill or flow refuses
(`execution_launch/account_interval.py:118-126`). Approach A lets the app hold a coin. After each interval [S, E), the
app reads Upbit's public trade list for every held coin and rebuilds the exact path of the account's marked equity:
every trade, our fills, fees and flows, in time order. The path gives the interval's true lowest and highest equity.
The floor and the daily loss are checked at every point, and a floor breach writes the halt row first. A stale last
trade, a ticker or canary mismatch and a minute-candle mismatch each re-check the floor, block new buys and alert;
they never start a sale themselves. A sleep, a Windows update or a reboot no longer stops the chain: the gap path is
rebuilt, its high raises H, and the floor and daily loss are judged at the first account record after the gap. Every
account change continues the record: app fills, the owner's manual trades, deposits, withdrawals and unexplained
changes. Deposits and withdrawals are kept out of profit and loss by a flow-adjusted equity, and the owner's own coins
are kept apart from the app's, so no app sell touches them.

## 1. Owner answers this design rests on

| Tag | Answered (KST) | Owner answer, short |
|---|---|---|
| Q1 | 11-12 | Minute-candle audit. On a mismatch, re-check the floor at the candle low, halting on a breach (never apply the high); block new entries until the owner checks; alert on all channels. Sells stay allowed. |
| Q2 | 11-12 | Narrow live route: a durable halt row first; the floor at every point, from the controller fold and the signed L; a re-anchor never erases a breach; an interval is refused if the signed limits change inside it. |
| Q3 | 11-12 | Per-fill fee: the myOrder WebSocket `trade_fee` first; pro-rata by funds when it was disconnected. |
| Q4 | 11-12 | Read gate: Upbit server time (the Date header) at or after E + SETTLE + 1 s. SETTLE starts at 1 s and is fixed from A0. |
| Q5 | 11-12 | Seoul midnight and 22:00: when the boundary read fails, retry after the boundary within a bound such as 30 s, rebuilding the path exactly to the boundary. If that also fails, stop as today. No forced flat. |
| Q6r | 11-12 (revised the same day) | No 30 s age limit: the last trade is the mark however old. When it is older than 30 s, also read the best bid. A bid at least Y below the last trade re-checks the floor at the bid, blocks new entries and alerts. This and the UNI/PR 4c rule become one rule. Coins are limited by traded-value rank only. |
| Q7 | 11-20 00:16 | A canary or ticker/trade-list mismatch gets the Q1 response: re-check the floor at the mismatched price (halt on a breach), block new buys until the owner checks, alert on all channels. Sells and protective sells continue. |
| Q8 | 11-20 | No filter on off-price prints. Every public trade counts for the low and for H. The owner accepted that a spike high can raise the floor once H nears A. |
| Q9 | 11-20 | Gaps (sleep, Windows update, reboot): rebuild the gap path from the trade list and check the floor and the daily loss. If the path crossed a limit inside the gap but the first point after the gap is back within the limits, do not halt. If the loss is still there right after the gap, halt. |
| Q9-1 | 11-20 | Continue on everything: app fills, manual sells, manual buys, deposits, withdrawals and unexplained changes all continue the record. (Asked about gaps.) |
| Q9-2 | 11-20 | The gap's highest point raises H. |
| Y | 11-20 | Y is signed in the PLB `limit_set` together with L and the daily loss limit, in force whenever a coin is held. The value is never written to the repo. |

The original answer 6 (a per-coin trade-gap threshold) is replaced by Q6r. A 24 h census of all 301 KRW coins on
2026-11-12 found none without a trade gap over 30 s, so a threshold could not work.

## 2. Terms

- **Interval [S, E).** The span between two committed account records. S is the previous record's time
  (`previous.asof`), E this record's. The value at E is the snapshot just before events stamped exactly E (BC:81-84).
- **Server time.** Upbit's HTTP Date header, parsed as `Answer.server_utc` (`execution/transport.py:526-535`). Upbit does
  not document it; it has 1 s resolution.
- **Mark.** For a coin at time t: the price of its last public trade stamped before t, however old [Q6r].
- **Path.** The time-ordered points of one interval: the opening value at S, each public trade of each held coin, our
  fills, flows, and the closing value at E. At each point the account's equity is cash plus each coin's units times
  its mark.
- **Ordinary interval, long interval, forgiven gap.** An interval with E - S at most 30 s by server time is ordinary.
  A longer one is a long interval. A long interval that spans a detected suspend or restart (BR-16) is a forgiven gap;
  any other long interval is judged at every point [default, OQ6].
- **Check-block-alert (CBA).** The Q1 and Q7 response: re-check with a coin valued at a given price; set the entry
  block; alert on all channels. BR-9 defines it.
- **Entry block.** A new durable journal latch that refuses every new buy. It never sells and never blocks a sell, a
  cancel or the owner's exit.
- **App units and owner units.** Per coin, the units the app owns and the units the owner owns (BR-23).
- **F and adjusted equity.** F is the cumulative net external flow; adjusted equity is marked equity minus F (BR-22).

## 3. Rules

### 3.1 Reading the path

- **BR-1 Read gate [Q4].** A capture reads a coin's trade list for [S, E) only once server time is at or after
  E + SETTLE + 1 s. SETTLE starts at 1 s and is fixed from A0, which measures how long a trade takes to appear in the
  list (Upbit documents no delay). A response without a Date header refuses the read; the unit retries. Because the
  true time is at or after the Date value, the extra 1 s is a margin, not a truncation fix.
- **BR-2 Walk [design].** `GET /v1/trades/ticks` with `market`, `count=500` (the default is 1) and `to` = E rounded up
  to the next whole second plus 1 s on E's UTC day; then `cursor` = the oldest `sequential_id` on the page. Upbit's
  trade days split at 00:00 UTC (09:00 KST), so an interval that crosses it reads both days, choosing `days_ago` from
  server time. Pages are de-duplicated by `sequential_id` and ordered by `timestamp` (ms). Upbit says `sequential_id`
  does not guarantee order, so trades in the same millisecond are an unordered set. The walk stops once a page reaches
  a trade before S. Trades with S <= `timestamp` < E belong to the interval. A failed page fails the path; nothing is
  interpolated. No request carries an `Origin` header (the rate-limits page drops such requests to 1 per 10 s) or a
  trailing slash (refused from the announced date 2026-11-16, per the changelog notice; A0 confirms).
- **BR-3 Opening and closing value [Q6r].** The value at S uses each coin's mark at S; the value at E uses its mark at
  E. A coin with no trade inside the list's reach (7 UTC days) is marked at the ticker's `trade_price` and
  `trade_timestamp`, a path that is already allowlisted. No age limit applies to a mark.
  - **Unlisted coins [design].** A balance whose KRW market is absent from a valid `market/all` read is valued at 0
    from that read's time, as UNI:570-572 and `execution_accounts/upbit_collector.py:448-449` do today. It gets no
    trade-list path, ticker or bid read, and it never sets the entry block by itself. The drop to 0 is a judged path
    point, so it can trip the floor. `PriceMark` requires a positive price (`execution_accounts/continuous.py:149`),
    so this case is carried outside it. The coordinator's vanish latch (`execution_launch/coordinator.py:775-776`)
    keeps its input.
- **BR-4 Every trade counts [Q8].** No print is filtered. Each trade moves its coin's mark and is a path point.
  Interval minimum and maximum are taken over every point, the opening and closing values included. A same-millisecond
  set is evaluated at every price in the set against the holdings before and after any of our fills in that
  millisecond, so the extremes do not depend on an order Upbit does not give.
- **BR-5 Fees [Q3].** Each of our fills takes its fee from the myOrder `trade_fee` when the WebSocket captured that
  fill. When only some fills of an order were captured, `paid_fee` minus the captured fees is split over the
  uncaptured fills by funds: fee_i = remainder x funds_i / (sum of their funds), rounded down to the fee's precision
  with the residue on the last of them, so the parts sum exactly to `paid_fee` [design]. When no fill was captured,
  the whole `paid_fee` is split that way. If the remainder is negative, or a fully captured order's fees do not sum to
  `paid_fee`, the whole order is split by funds and an alert is raised [default, OQ15]. This replaces the refusals
  `COLLECTOR_FEE_COVERAGE_INCOMPLETE`, `COLLECTOR_FEE_RECONCILIATION_MISMATCH` and
  `COLLECTOR_PER_TRADE_FEE_EVIDENCE_REQUIRED` (`execution_accounts/upbit_collector.py:247-264`) and the `Inexact` refusal
  for this case (`:356-364`). It supersedes, for fees only,
  `handoff:context/upbit-universe/gpt-20261113/held-source-contract-evidence.md:29` ("proportional allocation does not
  suffice") and the venue note that WebSocket is at most a hint
  (`docs/superpowers/plans/wip-2026-10-24/venues/upbit.md:323`): REST order detail has no per-fill fee.

### 3.2 Cross-checks and check-block-alert

- **BR-6 Ticker against the list [Q7].** The capture reads the ticker, then the list. A mismatch is a ticker trade
  stamped before the walk's `to` bound (BR-2) whose timestamp and price are not in the walked pages. A ticker trade at
  or after `to` lies outside the walk and is not compared. Response: CBA at the ticker's price.
- **BR-7 Own-fill canary [Q7].** Each of our fills in [S, E) must match a public trade by timestamp (ms), price and
  volume. `ask_bid` is not used until A0 shows which side it reports. The part of an order stopped by self-match
  prevention (myOrder state `prevented`; in REST order detail, state `cancel` with a nonzero `prevented_volume`) has no
  fill, so it is not a miss; any fills that order did have are checked as usual. `cancel_maker` is the announced default
  from 2026-11-09 (changelog notice); A2 confirms it. A miss gets CBA at our fill price.
- **BR-8 Minute-candle audit [Q1].** A separate lagging step, not part of the commit's coverage check: once a 1-minute
  candle is final (A0 measures when; Upbit documents no delay), its low and high are compared with the path's trades
  in [start, start + 60 s). A mismatch is a candle low below the path's lowest trade, a candle high above its highest
  trade, or a candle for a minute where the path has no trade (or the reverse). Response: CBA at the candle low. The
  candle high never raises H. The audit also covers the minutes of long intervals.
- **BR-9 Check-block-alert [Q1, Q7].**
  - **(a) Re-check.** The floor is re-checked with the coin valued at the given price at that time. A floor breach
    halts by BR-14: the chosen Q1 and Q7 options say "halt on a breach". The daily loss is re-checked the same way, and
    a daily-loss breach sets the persistent daily stop, as today (`execution_control/controller.py:803-811`); it never
    halts [design]. A CBA price inside the unjudged part of a forgiven gap follows BR-16 instead.
  - **(b) Entry block.** Set at once. It needs two new journal kinds, `entry_block` and `entry_unblock`, since
    `EVENT_KINDS` is a fixed set (`execution_control/store.py:25-28`). It stays until the owner lifts it after
    checking [default, OQ9].
  - **(c) Alert on all channels,** meaning D5's set: a Windows notification, iOS push and email (D5,
    `2026-10-23-compliance-gate-and-odds-engine-design.md:64`; `_CHANNELS` in `core/compliance/alerts.py:19`).
    `_toast_once` (`execution_launch/coordinator.py:617-627`) is only the toast leg and de-duplicates by key, so each
    CBA key names the coin, the kind and the time. Push and email are sent today only by the daily Claude task
    (`core/compliance/alerts.py:1-5`); until a prompt path exists, CBA writes a durable alert row for that task
    [default, OQ14].
  - **Breach found after the interval committed** (the candle audit runs after the minute) [design]. The breach is
    held as a pending halt: the entry block is set and the alert sent at once, and the halt is written inside the next
    staged interval's commit (the in-transaction halt, `execution_launch/continuous_guard_commit.py:376-380`). A
    journal-only halt outside a guard transaction would make every later commit refuse (`:369`), which would stop the
    chain and every in-app exit.
  - Strategy sells, protective sells, cancels and the owner's exit stay allowed. CBA never sets `data_complete` or
    `external_flows_known` to false, because exits require both (`execution_launch/runner.py:464-466`;
    `execution_control/controller.py:606-607, 1092-1093`; `execution_launch/driver.py:458-461`). It replaces today's
    hard refusal on a ticker or closing-mark mismatch (`execution_launch/continuous_guard.py:438-440`;
    `execution_launch/account_interval.py:346-349`).

### 3.3 One stale-trade rule (replaces the PR #33 rule)

- **BR-10 Bid gap [Q6r, Y].** At each capture, for each held coin whose mark at E is older than 30 s by server time,
  the capture also reads the best bid. If bid <= mark x (1 - Y), the response is CBA at the bid. The mark stays the
  last trade for equity, the minimum, the maximum and H. The rule is the same for every profile (fixed and universe).
  - It covers every held coin with a listed market: app or owner units, in or out of the universe, dust included
    [default, OQ13]. Unlisted coins follow BR-3.
  - A bid that cannot be read, or an empty book, gets the entry block and an alert without a price re-check; the unit
    does not refuse [default, OQ10].
  - With no Y in force, no buy is prepared, and a held coin is checked with Y = 0, so any bid below the mark gets CBA
    [default, OQ10]. This matches the D12 fold, where an unset limit counts as the tightest
    (`core/compliance/owner.py:682-686`).
  - The app may trade a coin by the universe's traded-value rank only; no trade-gap threshold applies [Q6r].
- **What it replaces.** PR 4c merged as #33 (`7d256f9`) with a different rule: a last trade older than 30 s is marked
  at the best bid of a book at most 10 s old, and otherwise the capture fails closed
  (`execution_accounts/upbit_collector.py:436-438, 450-452`; `COLLECTOR_TICKER_STALE_OR_FUTURE` at `:456-458`). The
  provider also refuses any position mark older than 30 s (`execution_accounts/provider.py:236`). M7-T3 replaces both
  for held-coin marks. `Position` has no bid field (`execution_accounts/model.py:68-76`), so the bid goes into the
  capture evidence, not into `Position`. The tests that encode the old rule (`tests/accounts_collector.py:336-350,
  403-416`) change with it. The texts that state it are superseded on merge (section 6). PH:495 calls the rule
  "UNI 12"; it is in UNI section 11 (UNI:568-580).

### 3.4 Seoul midnight and 22:00

- **BR-11 Boundary rebuild [Q5].** The reducer's rules stay: an interval that changes Seoul day ends exactly at
  midnight, and none crosses 22:00 on a day that needs a recovery cutoff (the condition is configured and the day is
  the first trading day or follows a zero realized day; `execution_accounts/baseline.py:153-159, 297-304`; RC:3-5).
  The boundary value is now rebuilt instead of observed: holdings and cash at the boundary are the first capture after
  it minus the fills and flows stamped in [boundary, first read), and prices are the marks at the boundary. Any capture
  whose first read is within 30 s after the boundary by server time may rebuild it. The coordinator's one bracketed
  boundary unit (`execution_launch/account_interval.py:44, 111-117, 163-172`) becomes the first attempt; a slot or
  monitor capture inside the bound is the retry. No position is forced flat. A rebuilt value is computed from evidence,
  not a later balance relabelled; this amends RC:34-35, BC:104-110 and the docstring at
  `execution_launch/account_interval.py:13-15`. `BOUNDARY_BAND` stays 20 s (`execution_launch/coordinator.py:86-89`);
  a slot 20-30 s after a boundary does the rebuild in its own capture, and A0 times it.
- **BR-12 Bound expired.** While the process was running (reads failed or ran late), Q5's chosen option governs: the
  chain stops as today (`ACCOUNT_INTERVAL_BOUNDARY_MISSED`) until the owner's reviewed re-anchor [Q5]; PH:481-482
  already says so. When the bound expired inside a forgiven gap (the PC slept or restarted), the later Q9 answer
  governs: the next capture rebuilds the gap and splits it at the boundary, and the chain continues [Q9; default,
  OQ6]. A boundary rebuilt within the bound is not a missed-boundary safety stop under SD 6.2; one rebuilt later is.
  A 22:00 value rebuilt within the bound is recovery proof; one rebuilt later stays unverified (BR-16), as RC:72-75
  says today.

### 3.5 The floor and the halt

- **BR-13 Floor at every point [Q2].** At each path point the app compares adjusted equity with the floor, and the day
  opening minus adjusted equity with the signed daily loss limit. The floor is seeded from the controller's fold (H,
  the approved floor and the last journaled effective floor, `execution_control/controller.py:786-812`) and the signed
  L, not from the guard's own checkpoint floor alone (`execution_launch/continuous_guard.py:470, 497`). Today the
  controller judges only the endpoint (`execution_control/controller.py:823-836`) and the guard every point
  (`execution_launch/continuous_guard.py:479-528`). A floor breach halts by BR-14; a daily-loss breach sets the
  persistent daily stop, as today (`execution_control/controller.py:803-811`). Forgiven-gap points follow BR-16.
- **BR-14 Halt order [Q2].** The breach is carried in the guard plan: the new guard state is permanently halted with a
  `permanent_floor_halt` required record, the prepare row has `halt_required` true, and the commit appends the journal
  `halt` row before the baseline and guard advance, then the completion row
  (`execution_launch/continuous_guard_commit.py:366-385`). That row is Q2's durable halt row first. `system_halt` goes
  to the owner log only after completion, through the epoch handover (BR-15). The live path does not call
  `Controller.halt`, which appends `system_halt` in the same call (`execution_control/controller.py:1390-1396`). If the
  commit cannot run, `Controller.halt` is the fallback, and the next guard commit then refuses
  (`GUARD_CONTROL_HALT_NOT_IN_GUARD`, `execution_launch/continuous_guard_commit.py:369`) until the owner reviews it.
  The breach point's time and value are kept in the path archive and in status. A re-anchor never erases a breach:
  the new anchor's H, floor and daily stop must be at or above the journal fold, compared in raw terms with F added
  (BR-22), and a halt row stays latched.
- **BR-15 Limits that change inside an interval [Q2].** An interval whose [S, E) contains a change in the signed
  limits in force (L, the daily loss limit or Y) is refused. To keep this rare, intervals and long intervals are cut
  where the change takes effect under the D12 fold [design]: a loosening at the next Seoul midnight, already a
  boundary (`core/compliance/owner.py:682-684`), and a tightening at its owner-log entry, including one signed while
  the app was off.
  - **Epoch handover [design].** Today any owner-log append, including the app's own `system_halt` and
    `system_disarm`, ends the chain, because these sites require identical owner terms or heads:
    `execution_launch/continuous_guard.py:369-372`, `execution_launch/committed_account.py:358`,
    `execution_launch/committed_producer.py:467-468, 480, 492` and `execution_launch/continuous_guard_commit.py:135-136`.
    At a cut, the next interval starts a new owner epoch, and these sites compare the limit terms in force, not the
    owner-log head.
  - At the cut the applied floor becomes the higher of the carried floor and the new signed L, since the guard
    requires the applied floor to be at least the signed one (`execution_launch/continuous_guard.py:464-465`). Outside
    a forgiven gap, the cut point is judged against the new limits and halts by BR-14 if below them. H, the day
    opening and the daily stop carry over and are never lowered.

### 3.6 Long intervals and gaps

- **BR-16 Forgiven gap [Q9, Q9-2].** A forgiven gap is a long interval that spans a detected suspend or restart: the
  launcher's bootstrap after a process start (CL 4.1), or a coordinator gap unit
  (`execution_launch/coordinator.py:1182-1191`) whose timer woke more than 30 s late while no unit was running
  [default, OQ6]. Any other long interval (a read retry under BR-18, an overrun) is rebuilt the same way but judged at
  every point, as BR-13 does. The rebuild runs in the gap unit or in the bootstrap, not in the startup unit, which has
  a 15 s budget (`execution_launch/coordinator.py:1218-1219`). The gap is split at each Seoul midnight, each needed
  22:00 and each BR-15 cut inside it, and all pieces commit as one unit. Judging:
  - Points in [S, S + 30 s) at the gap's true S are judged one by one, as BR-13 does, so a breach seen just before a
    crash is not forgiven [default, OQ6].
  - Points from S + 30 s up to E are not judged against the floor or the daily loss [Q9]. A CBA price there (BR-6 to
    BR-10) sets the entry block and alerts but is not judged either [default, OQ6].
  - The floor and the daily loss are judged at E, the first account record after the gap, under the limits in force
    at E [Q9]. A floor breach there halts by BR-14; a daily-loss breach sets the daily stop.
  - H takes the highest point of the whole gap path [Q9-2]. E is then judged against the floor after that raise, the
    same order as a live interval (`execution_accounts/baseline.py:315`, then the controller's breach test) [default,
    OQ6]. The owner accepted under Q8 that a spike high can raise the floor.
  - Interior split points (midnight, 22:00, BR-15 cuts) are advanced in the reducer only and not observed by the
    controller. They are exempt from the reducer's extrema check (`execution_accounts/baseline.py:294-296`) and its
    daily-loss fold (`:310-311`). A midnight value still becomes the new day's opening. A 22:00 value inside a forgiven
    gap creates no `RecoveryCheckpoint` (`execution_accounts/baseline.py:306-308`;
    `execution_launch/continuous_guard.py:482-486`), so that day stays unverified, which latches the daily stop
    (`execution_control/controller.py:807`; RC:72-75) [default, OQ6].
  - The gap path's true lowest point is kept in the archive and in status for audit, outside the reducer.
- **BR-17 Reach [default, OQ7].** The trade list goes back at most 7 UTC days (`days_ago` 1 to 7). If S is older than
  that, the part before the reach cannot be rebuilt: the chain stops, the entry block is set and an alert is raised.
  The owner's reviewed re-anchor (`docs/account-baseline-integration.md:200-218`) restores it. Nothing is
  interpolated. Under today's collector a re-anchor needs zero coin inventory and zero open orders
  (`execution_accounts/upbit_collector.py:232-233`; ACC:68-69), the owner's coins included; this design keeps that, and
  a held-coin anchor is a later design [default, OQ7].
- **BR-18 Unfinished rebuild [design].** On 429, 418, a timeout or a network error the head stays at S, an alert is
  raised and the next unit retries. After a 418 nothing is retried until the next unit; E1 transport already paces each
  process at 0.2 s per request and retries a GET once (`execution/transport.py:54-57, 336-360`). No entry block is
  set for a read failure: while the head stays at S every app order and exit refuses anyway, because the account must
  be at most 30 s old (`execution_launch/runner.py:461-463`). The owner can still sell by hand on Upbit, and the
  rebuild records it (Q9-1). The rebuild holds the work lock (`execution_launch/coordinator.py:32-33, 497, 915-917`),
  so `disarm` returns pending after its timeout (1 s by default, at most 5 s;
  `execution_launch/coordinator.py:1284-1299`; `tools/owner/launch.py:296-297`); status shows the rebuild's progress.
- **BR-19 Rollback defence [design].** The existing defence survives gaps: `classify_restart` refuses a guard and
  baseline pair that is not the successor named by the journal's last completed guard transaction, whatever the time
  (`execution_launch/continuous_guard_commit.py:216-224`, used at `execution_launch/committed_startup.py:247`). The
  baseline store's own note that only the 30 s rules refuse an old coherent rollback
  (`execution_launch/baseline_head.py:14-19`) is about that store alone. A gap rebuild adds: its S equals the time of
  the baseline that transaction names; its server time is after the journal's last event; and its starting H, floor
  and daily stop are at or above the journal fold, with the day opening equal on the same Seoul day.
- **BR-20 The 30 s sites [Q6r, Q9].**

  | Site at `1fd8792` | Ordinary interval | Long interval |
  |---|---|---|
  | `execution_launch/account_interval.py:169-170, 303` (R17: capture within 30 s of `previous.asof`) | kept | replaced by BR-16 |
  | `execution_accounts/provider.py:356-359` (the bundle's baseline at most 30 s old and the same Seoul day; exported at `previous.asof`, `execution_launch/account_interval.py:161`) | kept | the reducer advances over the interval first, so the export is fresh |
  | `execution_accounts/continuous.py:184-187` (E - S at most `MAX_DURATION`, 30 s) | kept | the long kind is exempt; BR-17 bounds it |
  | `execution_accounts/continuous.py:198-199, 233-234` (each opening mark at most 30 s before S) | removed (BR-3) | removed |
  | `execution_accounts/continuous.py:157-159, 186` (receipts and watermark within 30 s of S) | rebounded to (E - S) + SETTLE + 1 s + a read budget that A0 measures | same |
  | `execution_accounts/continuous.py:297-298` (coverage verified within 30 s after E) | kept | kept for the last piece |
  | `execution_accounts/baseline.py:291-293` (`max_interval_seconds`, 1 to 300) | kept | a long-interval kind, bounded by BR-17 |
  | `execution_accounts/baseline.py:294-296, 306-308, 310-311` (extrema, recovery checkpoint, daily-loss fold) | kept | interior split points exempt (BR-16) |
  | `execution_accounts/provider.py:236` (a position mark at most 30 s old) | replaced by BR-3 and BR-10 | same |
  | `execution_accounts/upbit_collector.py:436-438, 450-458` (book at most 10 s, ticker at most 30 s) | replaced by BR-10; the unlisted branch `:448-449` stays (BR-3) | same |
  | `execution_accounts/upbit_collector.py:444-445` (the balance capture fits in 30 s) | kept; path reads come after E | same |
  | `execution_launch/committed_producer.py:464-466`; `execution_launch/continuous_guard.py:373-375` (an owner read within 30 s before S) | kept | the limit terms at each instant are folded from the owner log, not read live around S |
  | `execution_launch/continuous_guard.py:387-390` (capture observed within 30 s of S) | kept | replaced by the long kind's bound |
  | `execution_launch/guard_capture_material.py:285-287`; `execution_launch/committed_producer.py:406` (commit within 30 s of the interval end; a FRESH baseline) | kept | applied to the last piece only |
  | `execution_launch/runner.py:461-463`; `execution_control/controller.py:709-714`; `execution_accounts/baseline.py:339-344` (an account at most 30 s old for orders, observation and export) | kept | kept, after the commit |

### 3.7 Continue on everything

- **BR-21 Account changes [Q9-1].** Between S and E each change is classified, and every kind continues the record:
  - **App fill:** a fill of an order whose client id this account's control journal recorded, whatever its namespace
    prefix. That is #58's own test (`execution_launch/committed_startup.py:520-521`); the prefix itself changes with
    each profile (`execution_launch/runner.py:355`), and `identifier` carries the client id
    (`execution_orders/upbit.py:26`).
  - **Owner fill:** any other fill, including a manual order with an empty identifier (the collector maps it to `''`,
    `execution_accounts/upbit_collector.py:313-316`). Every order type counts (limit, price, market, best); today only
    limit passes (`:279-281`).
  - **Deposit or withdrawal,** KRW or coin, from `/v1/deposits` and `/v1/withdraws`. A deposit counts at `ACCEPTED`
    (its `done_at`); `TRAVEL_RULE_SUSPECTED`, `REFUNDING` and `REFUNDED` are not settled. A withdrawal counts at `DONE`
    (its `done_at`) [design; A0 and the account balances confirm the timing]. A withdrawal's fee is part of the outflow
    [default, OQ2]. An incoming coin is valued at the higher of its mark at `done_at` and its first trade after it, an
    outgoing coin at the lower, so a stale mark cannot create a gain [design].
  - **Unexplained change:** per currency, the captured balance minus (the previous balance plus fills and settled
    flows), when it is not zero.

  The same rule applies while running, not only after a gap [default, OQ1]. The app trades in the main pocket, and the
  owner makes no pocket transfer while a coin is held; a pocket transfer would show as an unexplained change [default,
  OQ11]. This replaces the exclusive-account fence (`execution_accounts/collector.py:112-131`), the transfer-scope
  coverage rule (`execution_accounts/upbit_collector.py:237-243`), the flow refusals (`:325-343`) and the KRW lock
  check (`:402-403`), the provider's coin-flow refusal and FIFO equality (`execution_accounts/provider.py:212-229,
  245-248`), the bridge's interval-flow refusal and FIFO profit equality (`execution_accounts/baseline_bridge.py:71-76`;
  FIFO then runs over app and owner fills, with unexplained changes outside it), the producer's flat-only refusal
  (`execution_launch/account_interval.py:118-126`) and the reducer's flow convention and zero-flow rule
  (`execution_accounts/baseline.py:131-132, 282-283`).
- **BR-22 Adjusted equity [Q9-1; default, OQ2].** F is the cumulative net external flow: deposits plus, withdrawals
  minus. Adjusted equity = marked equity - F. Every risk number uses adjusted equity: H, the day opening, the daily
  loss, the floor test against L, and PLB's W0, C, A and R.
  - In raw KRW, a deposit raises H, the day opening and the floor by its amount: it is protected, not headroom. PLB
    calls a deposit "safe only if the signed floor is raised by the same amount first" (PLB:348); the adjustment does
    that without a signature, because it only tightens. A withdrawal lowers them by its amount: it is not a loss.
  - F is journaled with each risk snapshot and carried through every re-anchor; it is never reset [design]. A re-anchor
    is compared in raw terms against the journal fold plus F, so it cannot turn a protected deposit into headroom (the
    gap PLB:348 names).
  - Adjusted H never falls on a flow and the day opening stays fixed, so the controller's monotone peak and fixed
    opening (`execution_control/controller.py:298-314`) still hold, in adjusted terms. This is the "coherent Controller
    transition" BC:33-37 asks for. The launch profile already names the convention `externally_cashflow_adjusted`
    (`execution_launch/profile.py:36`); the reducer gets a matching one.
  - Every cash-against-floor comparison subtracts F: the controller's admission check (cash - F - pending - needed
    must stay at or above G, PLB:236-237), the driver's cash floor C (PLB:259) and the odds card's headroom. So an
    owner's coin deposit lowers the app's buying power by its value [default, OQ2].
  - Conventions are bound into the checkpoint digest (`execution_accounts/baseline.py:137-149`). By the same principle
    as BC:120-126 (written for the recovery-cutoff schema), moving a deployment to the flow-adjusted convention is a
    reviewed owner re-anchor (`docs/account-baseline-integration.md:200-218`), with H, the day opening, the floor and
    the daily stop carried from the journal fold (BR-14, BR-19).
  - **Unexplained changes [default, OQ8].** A negative residual counts as a loss, not a flow, so it can trip the floor
    and the daily loss. A positive residual counts as a flow, not a gain, so it cannot raise H. Each is logged and
    alerted on all channels (BR-9 (c)). Neither stops the chain or sets the entry block.
  - PLB-O6 ("no flow while a budget is in force", PLB:345-349, 659) is superseded by Q9-1 under this adjustment
    [default, OQ3].
- **BR-23 App units and owner units [Q9-1].** Both are tracked per coin as journaled FIFO lots.
  - App units = app buy fills - app sell fills - owner-initiated outflows charged to the app. Owner units = owner buy
    fills + coin deposits + positive coin residuals - outflows charged to the owner.
  - An owner-initiated outflow (a hand sell, a coin withdrawal, a pocket transfer or a negative coin residual) is
    charged to app units first, but only up to the app units not locked by open app sells at that time; the rest is
    charged to owner units [default, OQ4]. A hand sell on Upbit is the documented way out of an app position when the
    app cannot act (SD:206-208), and a resting app sell's units are locked, so a hand sell can only use free units.
  - App units stay between 0 and the balance. If app units plus owner units differ from the balance, an alert is
    raised, and every app sell is capped at the lower of app units and the balance minus owner units, so it never
    sells tracked owner units. The difference is not booked as a loss; the BR-21 residual is separate.
  - **Every app sell is capped this way:** strategy, protective hold or sale, the `exit` command and the legacy
    end-slot target 0 (`execution_launch/driver.py:448-450`). CL 4.5 "every held unit of the trade coin" (CL:212-220)
    and SD 6.4 "every held unit of a coin traded by this profile" (SD:199-201) become "every app unit".
  - **Driver and runner sites [default, OQ12].** They read app units and the app's cash: the anchor
    (`execution_launch/live_history.py:561-566`; `execution_launch/driver.py:466-471`), sell sizing (`:336`), the
    other-inventory refusal (`:475-477`, which then ignores owner units), the reserved-cash check (`:478-481`, which
    then excludes cash an owner order reserves), the outstanding-order check (`:482-484`, app orders only), the
    first-bar check (`:487-489`), the universe flat check (`execution_launch/runner.py:408-413`) and the universe
    helpers `held_coins`, `choose_trade_coin` and the extra-coin buy latch
    (`execution_launch/coordinator.py:141-166, 769-779`). An owner coin or owner order does not block the app.
  - **Limits [default, OQ4].** The whole account (app units, owner units and cash) counts toward L and the daily loss
    limit. The policy budget from the previous day's realized result (PLB:325-326; `execution_control/risk.py:299-311`)
    uses the lower of the app-only and whole-account results, so an owner profit cannot enlarge it. PLB's flat check
    for preparation (PLB:283, pin 3) checks app units only. Admission keeps cash - F at or above G for every app buy,
    so an owner purchase that spent cash below it blocks app buys until cash returns. The guarantee G3 (PLB:246) and the
    card's "holds even if this position goes to zero" (PLB:290) cover the app's trades only, and the card says so.
  - **Startup [default, OQ12].** An open order with an empty identifier (an owner order) no longer blocks
    (`execution_launch/committed_startup.py:520-524, 575-579`); its locked funds count in equity and its later fills
    are owner fills. An open order with an unknown non-empty id still blocks.
- **BR-24 Price paths for every coin [Q9-1].** Every coin with a balance at S, or with a fill, flow or residual in
  [S, E), app or owner, gets a BR-1 to BR-8 path, except an unlisted coin (BR-3); equity sums them. Upbit allows 10
  trade-list requests per second per IP, shared by every reader on that IP; E1 paces each process at 5 per second.
  Many owner coins make each unit longer; A0 measures it [design; OQ17 asks about other readers].
- **BR-25 Study records [Q9-1].** Each fill and flow in the capture archive carries an origin tag: `app`, `owner`,
  `deposit`, `withdrawal` or `unexplained`. The study, the odds and the outcome ladder use app fills only. Account
  profit and loss uses all of them. A manual trade is recorded but never counted as a strategy result.

### 3.8 Y in the signed limits

- **BR-26 Y in `limit_set` [Y].** `limit_set` accepts both its current two-key shape, `{total_loss_floor_krw,
  daily_loss_krw}`, and a three-key shape that adds Y (proposed key `bid_gap_fraction`, an exact decimal string with
  0 < Y < 1). A smaller Y is tighter. With no Y in force the app treats Y as 0 (BR-10), so a first-ever Y is a loosening
  and counts from the next Seoul date under D12 (`core/compliance/owner.py:682-684`). The change touches the schema and
  exact-key checks (`core/compliance/owner.py:158-159, 176-190, 243-245`), the D12 fold
  (`core/compliance/owner.py:634-637, 681-729, 742-749, 764-769`), the signer's copy of the schema
  (`tools/signer/sign.py:217-218, 3157-3158`), `OwnerContextClaim` and `_owner_terms`
  (`execution_launch/continuous_guard.py:64-76, 192-194`) and the producer's limit read
  (`execution_launch/committed_producer.py:288-295`). PLB says no owner-log schema or signer change (PLB:71, 419), and
  CL:413 puts `sign.py` changes only in PR L3; this field is the one exception, landing with A1. The owner signs Y only
  after its parsing code is code-approved, as with a lower floor.

## 4. The committed path (#46-#60) and #58 startup reconciliation

| Committed-path element at `1fd8792` | Under this design |
|---|---|
| Startup blocks on any open order the journal does not know (`execution_launch/committed_startup.py:520-524, 575-579`) | An order with an empty identifier (an owner order) is allowed (BR-23); an unknown non-empty id still blocks. |
| Holdings are reported, not reconciled, at startup (`execution_launch/committed_startup.py:573-574`) | Holdings split into app and owner units from the journaled lots (BR-23). |
| `CommittedStartup._time_status` (`execution_launch/committed_startup.py:203-213`, also used at `execution_launch/committed_producer.py:406`): STALE after 30 s; REFUSED across a date change or a needed 22:00 | A long interval (BR-16), split at the boundaries. REFUSED stays for a clock rollback (`:204-205`), BR-12's running case, BR-17 and BR-19. `classify_restart` (`execution_launch/continuous_guard_commit.py:182-240`) and all its refusals are unchanged. |
| GPT notes forbid a REST backfill of a gap (`docs/committed-startup-retention-execution-log.md:119, 121`; `handoff:context/upbit-universe/gpt-20261113/TRADEGEN_COMMITTED_STARTUP_READINESS_2026-11-13.md:56, 60`) | Superseded by the owner's Q9 answer for the trade-list rebuild only. Order and balance history still come from the existing reads. |
| `ContinuousUpbitCandidateSource(path_source, coverage_verifier, archive_root)` (`execution_launch/account_interval.py:397-414, 446-461`), min and max from `value_path` (`execution_accounts/continuous.py:302-384`), fills equal to the path's fill events | `path_source` is the trade-list path (A1); `coverage_verifier` re-reads and runs BR-6 and BR-7; BR-8 is a separate lagging step. Fill events gain owner fills, flows and unexplained changes (BR-21). `__call__` stops raising `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED` only in A2. |
| The producer pins the exact source class (`execution_launch/committed_producer.py:165, 188-189`) | The pin moves to the new class. |
| The capture packet holds no raw path responses | A new capture schema version holds the raw trade-list, ticker, orderbook and candle responses. |
| Stream epoch and sequence continuity (`execution_launch/committed_account.py:354-361`; `execution_launch/continuous_guard.py:363-366`) | A long interval is the next sequence in the same stream epoch. |
| The owner read brackets S, and the capture and commit fall within 30 s (`execution_launch/committed_producer.py:464-466`; `execution_launch/continuous_guard.py:373-375, 387-390`; `execution_launch/guard_capture_material.py:285-287`) | As BR-20: limit terms folded from the owner log for a long interval; freshness on the last piece. |
| The guard checks every point with its own checkpoint floor (`execution_launch/continuous_guard.py:470, 479-528`) | Seeded as BR-13; forgiven-gap points as BR-16. |
| Any owner-log append ends the chain (`execution_launch/continuous_guard.py:369-372`; `execution_launch/committed_account.py:358`; `execution_launch/committed_producer.py:467-468, 480, 492`) | Epoch handover (BR-15). |
| A journal halt the guard checkpoint lacks refuses the next commit (`execution_launch/continuous_guard_commit.py:196-200, 369`) | BR-14 uses the commit's own in-transaction halt; BR-9 holds a post-commit breach for the next commit. |
| A ticker or closing-mark mismatch is a hard refusal (`execution_launch/continuous_guard.py:438-440`) | CBA (BR-6, BR-9). |
| The bridge refuses an interval flow and requires FIFO profit to equal the reducer's (`execution_accounts/baseline_bridge.py:71-76`) | BR-21 and BR-22. |
| Errors, restarts and deadlines are never sell signals (`execution_launch/runner.py:712-718`; `execution_launch/protective_state.py:10-14`) | Unchanged. No rule here starts a sale. |

## 5. The deadline (E) conflict: PH (#31) and the 2026-11-13 decision

This design does not settle which rule governs a coin held at a window's end; it records the conflict and asks
(OQ5). Its own rules never start a sale.

| Topic | PH, merged 11-12 as `dc8a039` | 11-13 decision and the merged code |
|---|---|---|
| A coin held at E (window end or `valid_until`) | The hold ends and the app sells (PH:449-454); `held_at_end` sells at once (PH:240); SD-O8 | No sale because the deadline passed; block entries and request new management approval (`handoff:context/upbit-universe/gpt-20261113/TRADEGEN_PR4D_CAPACITY_AMENDMENT_2026-11-13.md:254, 256-261`; LEDGER row `design-revision-1113`, `handoff:LEDGER.md:166`). Code: `execution_launch/coordinator.py:865-911`, `execution_launch/runner.py:489-520`, `execution_launch/managed_behavior.py:57-65, 245-256`. Main records it in `docs/evidence-object-store-execution-log.md:37`. |
| A restart or the account chain coming back | Sells (PH:147-162, 175-176, 242; SD-O5) | Not a sell signal (`execution_launch/protective_state.py:10-14, 345-347, 375-377`) |
| Inputs that cannot be checked (rule I) | Sell (PH:338-351; SD-O13) | Not a sell signal (`handoff:context/upbit-universe/gpt-20261113/TRADEGEN_PROGRESS_2026-11-13.md:10`) |
| An approach-A mismatch or the bid gap during a hold | Also fires I, so the app sells (PH:348-349, 477-478, 487-490); the owner kept that default (SD-O13) | Nothing sells; CBA (BR-9) is the whole response |
| Resting buys at a stop or at E | Cancel requests (PH:127-134, 192-194) | The deadline grants no cancel authority (`handoff:context/upbit-universe/gpt-20261113/TRADEGEN_CARRY_V2_API_CARD_2026-11-13.md:20`) |
| The universe profile | (not separate) | The legacy universe factory still targets 0 at the end slot (`execution_launch/driver.py:448-450, 567-570`); universe carry is refused (`execution_launch/managed_behavior.py:85-91`) |

What this means for approach A:

- **Rule I on approach-A events follows OQ5.** Under PH, a mismatch or bid gap during a hold still fires I and starts
  the sale, as PH:477-490 says; CBA (Q1, Q6r, Q7) runs as well and keeps sells allowed. Under the 11-13 decision
  nothing sells on it. Then a bid that collapsed while nobody trades is met only by CBA: the floor re-checked at the
  bid, the entry block, and a halt without a sale if the floor breaks.
- **A restart now keeps the chain.** PH assumed a restart over 30 s stops the chain, so its restart sale could rarely
  act (PH:242). Under Q9 it can, so if PH's restart sale stands, every reboot or Windows update sells the held coin.
  Under the 11-13 decision it does not.
- **Past E the chain must stay alive** through `monitor_until` (at most window end + 1 day,
  `execution_launch/coordinator.py:444-449`) and across the boundaries scheduled after E (`:250-261`). After
  `monitor_until` no unit runs; the next start rebuilds the gap (BR-16) within reach (BR-17).
- **A coin held past E blocks the next window under today's code,** because both drivers require a flat first bar
  (`execution_launch/driver.py:417-420, 487-489`) and SD refuses preparation while holding (SD:149-150). BR-23 makes
  these checks read app units, so an app coin carried past E still blocks the next window.

Proposed default for OQ5: the 11-13 decision governs, being later and implemented in merged code, and a later docs PR
marks the PH clauses above superseded.

## 6. Document changes in this PR and on merge

- **Edited in this PR: BC.** The daily-loss convention (BC:14-18) and the extrema sentence (BC:56) get the BR-16 gap
  exception, with the 30 s threshold and the judged first 30 s marked as proposed defaults (OQ6). The flow convention
  (BC:19-21) and the flow-adjustment paragraph (BC:33-37) point to BR-21 and BR-22, the interval bound (BC:22-23) to
  the long-interval kind, and the boundary sections (BC:81-84, 104-110) to BR-11. Each edit says the code at `1fd8792`
  still behaves as before until M7-T3 lands.
- **Superseded on merge, updated by M7-T3 or a later docs PR:**
  - the stale-trade rule (BR-10): UNI:573-575; `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md:50-54`;
    ACC:90-93;
  - the exclusive-account fence, limit orders only, and KRW-only zero-fee flows (BR-21): ACC:79-85, 126-127, 133-137;
  - raw holdings for the universe's extra coin and the fully flat rehearsal account (BR-21, BR-23): UNI:345-346,
    581-582; the sell scope (BR-23): CL:212-220, SD:199-201;
  - the 30 s account-chain stop after a sleep or reboot (BR-16): CL:206-208, 236, 423; PH:111-112, 242, 403-404,
    461-462; SD:130-131 (the handoff miss stays a safety stop, OQ16) and SD:273-274 (the clause about auto-sell after
    a reboot; "A restart ends the deployment" stays); `docs/account-baseline-integration.md:91-96`;
    `docs/windows-first-trade-integration.md:157-159`; `docs/first-trade-owner-checklist.md:91-93`. SD:179 ("the
    account chain stopped") stays, because BR-12 and BR-17 can still stop it;
  - "a boundary retry that fails is the chain stop": PH:481-482 stays for the running case (BR-12) and is superseded
    inside a forgiven gap;
  - "never relabelled": RC:34-35, BC:104-110 and `execution_launch/account_interval.py:13-15`, read with BR-11;
  - no flows while a budget is in force: PLB:345-349 and PLB-O6 (PLB:659), if OQ3 holds;
  - "no owner-log schema or signer change" (PLB:71, 419) and "`sign.py` only in PR L3" (CL:413), for Y only (BR-26);
  - PLB:246, 283 and 290 as BR-23 qualifies them, if OQ4 holds;
  - rule I on approach-A events (PH:348-349, 477-478, 487-490), only if OQ5 picks the 11-13 decision.

## 7. Delivery

Main implements in M7-T3. The order stays as recorded on 2026-11-12, re-cited at `1fd8792`:

1. **A0, a probe outside the D14 closure.** Public reads only, no keys, not in `CAPTURE_FILES`. The owner runs it for
   hours or days. It measures: the Date header on trade-list responses and its offset; when a trade appears in the
   list (SETTLE); when a minute candle becomes final; pages per interval; two reads of one interval at SETTLE 0.5, 1
   and 2 s; ticker against the list; prices within one closing millisecond; which side `ask_bid` reports; refusal of a
   trailing slash; 429 and 418; latency; behaviour across 09:00 KST; and whole-unit time against
   `MONITOR_UNIT_SECONDS` = 5 and the slot envelope (`execution_launch/coordinator.py:32-36, 90-94`). It gives a go or
   no-go before any signed code.
2. **A1, preview only.** The trade-list module, the walk, BR-1 to BR-12, the flow classification and the unit lots
   (BR-21 to BR-25), the new capture schema, and Y parsing (BR-26). Allowlist entries for `/v1/trades/ticks` and, for
   BR-8, `/v1/candles/minutes/1` in `ENDPOINTS`, `PUBLIC` and `READ_CAPTURE_ENDPOINTS`
   (`execution/upbit_inquiry.py:17-31`) and their pinned tests (`tests/execution_guards.py:855-859, 1129-1133,
   1149-1154`; `tests/execution_read_capture.py:70-73`). It changes `CAPTURE_FILES` (`execution_launch/study.py:63-65`),
   so it lands before the study freeze.
3. **A2, live, after controlled mode.** BR-13 to BR-20, the entry block, the epoch handover, F in the controller's
   admission check, and the reducer's long-interval kind and flow convention. The coordinator today refuses anything
   but rehearsal (`execution_launch/coordinator.py:394`).
4. **One `code_approved`, then the study freeze, then signing** (including Y). The driver identity hashes 46 source
   files, 49 for carry (`execution_launch/driver.py:38-92`). Every listed file that A1 and A2 touch changes it, and a
   new module must be added to the list. So the driver export and review-approve come after both merge.

Not in scope: the journal's size cap (`execution_control/store.py:29-31`); whether the legacy end-slot sale exists
(OQ5; BR-23 only caps it at app units); a held-coin anchor (OQ7); and any change to the study's strategy.

## 8. Owner-only steps this design implies

- Merging this PR (design approval).
- Approving, in design and again in the implementation PR, the `sign.py` and owner-log change for Y (BR-26).
- Running A0 on the owner's PC.
- After M7-T3: one `code_approved`; the reviewed re-anchor that moves the deployment to the new conventions (BR-22),
  which under today's collector needs a flat account with no open orders, the owner's coins included (BR-17); and
  signing Y.

## 9. Owner questions

**A. Needed before M7-T3 code.** Each has a proposed default the code follows unless the owner chooses otherwise.

- **OQ1. Flows while running.** Q9-1 was asked about gaps. Does the same rule apply while the app runs, where today a
  deposit or withdrawal stops the record (BC:19-21)? Default: yes, one rule.
- **OQ2. How a deposit or withdrawal moves the limits.** Default: adjusted equity (BR-22). A deposit is protected (H,
  the day opening and the floor rise by it, and the protection survives re-anchors); a withdrawal is not a loss (they
  fall by it); a withdrawal fee is part of the outflow; an owner's coin deposit lowers the app's buying power by its
  value. Alternatives: a deposit becomes headroom (the losable amount grows with no signed act, PLB:348); a
  withdrawal counts as a loss (it can halt).
- **OQ3. PLB-O6.** May Q9-1 with OQ2's adjustment supersede "no flow while a budget is in force" (PLB:345-349, 659)?
  Default: yes.
- **OQ4. Manual trades and the limits (BR-23).** Defaults: the whole account counts toward L and the daily loss limit;
  the next day's policy budget uses the lower of the app-only and whole-account realized results, so an owner profit
  cannot enlarge it; a hand sell, coin withdrawal or transfer comes out of the app's free units first, then the
  owner's; PLB's flat check for preparation checks app units, and its floor-keeping guarantee is stated for app trades
  only, because an owner purchase can spend cash the guarantee assumed (app buys then wait until cash returns).
- **OQ5. The deadline E.** Which governs a coin held at E: PH (sell at E, sell after a restart, sell when a check
  cannot run, and sell when an approach-A mismatch or bid gap fires rule I during a hold) or the 11-13 decision (no
  sale for the deadline alone; a restart is not a sell signal)? Default: 11-13. Under it, a bid that collapses while
  nobody trades is met by CBA only (floor re-check, entry block, halt without a sale). Does the 11-13 decision also
  cover the universe profile, whose legacy driver still sells at the end slot?
- **OQ6. Which long intervals are forgiven (BR-16, BR-12).** Default: only one that spans a detected suspend or
  restart; a long interval while the app was running (read failures, overruns) is judged at every point. A boundary
  missed while running stops the chain, as your Q5 option said; one missed during a sleep or restart is rebuilt under
  Q9 and the chain continues. Inside a forgiven gap: the first 30 s after S are still judged point by point; later
  points, including midnight, 22:00 and any CBA price, are not judged; midnight still sets the new day's opening, and a
  22:00 inside the gap stays unverified, which stops new entries for that day; E is judged against the floor after the
  gap high raised H.
- **OQ7. A gap older than the trade list's reach (about 7 days), and re-anchors.** Default: stop the chain, block
  entries and alert until your reviewed re-anchor, which today needs a flat account with no open orders, your own coins
  included. Alternatives: rebuild the unreadable part from minute-candle lows and highs; or a later design for a
  re-anchor that keeps coins held.

**B. Defaults that stand unless the owner objects.**

- **OQ8. Unexplained changes:** logged and alerted; no stop and no entry block; a negative one counts as a loss, a
  positive one as a flow (BR-22).
- **OQ9. Lifting the entry block:** an owner console command, written to the journal, after checking. A restart does
  not lift it.
- **OQ10. No bid, no Y:** an unreadable bid gets the entry block and an alert, without refusing the unit; with no Y in
  force no buy is prepared and held coins are checked at Y = 0 (BR-10).
- **OQ11. Pockets:** the app trades in the main pocket and the owner makes no pocket transfer while a coin is held.
  Alternative: give the read key pocket management (`포켓관리`), which can also move assets, so the app can read
  pocket transfers.
- **OQ12. Owner coins and orders with the app running:** an owner open order no longer blocks startup, and the
  drivers and the universe helpers read app units and app cash, so an owner coin or order does not stop the app
  (BR-23).
- **OQ13. Owner coins, coins outside the universe and dust:** each gets a path and the bid-gap rule; an unlisted coin
  is valued at 0 as today (BR-3, BR-10, BR-24).
- **OQ14. Alert delivery:** a Windows toast at once; push and email through a durable alert row that the daily Claude
  task sends, so they can arrive up to a day late until a prompt path is built.
- **OQ15. Fee mismatch:** when myOrder fees do not add up to `paid_fee`, the order's fee is split by funds and an
  alert is raised (BR-5).
- **OQ16. Standing deployment:** a restart and a handoff over 30 s still end the standing deployment as safety stops
  (SD 6.2); only the account chain now survives them.
- **OQ17. Shared IP (information):** will QUANTGEN or another Upbit public reader run from the same PC or IP while
  TRADEGEN is live? The trade-list limit of 10 per second per IP is shared.
- **OQ18. A0's reach:** public reads only (default), or also one keyed, read-only myOrder subscription with no
  orders, to learn which key permissions myOrder needs (undocumented)?
