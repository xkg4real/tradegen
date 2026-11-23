# Blocker 1, approach A: held-coin account intervals rebuilt from the Upbit trade list

Date: 2026-11-20 (Asia/Seoul).
Status: proposed amendment to PR #65. Section 9 records the owner's direct approval of OQ1–OQ7 on 2026-11-23 KST
and their subsequent decisions on OQ8–OQ11 and OQ13–OQ18. OQ12 remains open. Separate decisions cover the BR-26
owner-log and signer schema, PR merges, code review, signatures and trading activation.

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
tagged with an answered OQ refers to the owner decision in section 9. A `[default, OQn]` tag denotes
a proposal still awaiting an answer. Earlier Q-numbered answers in section 1 are distinct from these OQ items.
A rule tagged `[design]` is a mechanism this document chooses to carry out an answer.

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
an independently established, authorized protective sell can then execute under OQ13. A sleep, a Windows update or a reboot no longer stops the chain: the gap path is
rebuilt, its high raises H, and the floor and daily loss are judged at the first account record after the gap. Every
account change continues the record: app fills, the owner's manual trades, deposits, withdrawals and unexplained
changes. Flow adjustment separates deposits and withdrawals from trading results. A withdrawal preserves the existing
raw principal and protected high-water floors. The app tracks its coins separately from the owner's and caps its sales
at its own units.

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

The historical Q1 and Q7 answers above describe why the latch is set. The later OQ9 decision defines both ways to
release that latch under BR-9(b); its independent risk checks still apply.

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
  any other long interval is judged at every point [OQ6].
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
  - **Unlisted coins [OQ13].** A balance whose KRW market is absent from a valid `market/all` read is valued at 0
    from that read's time, as UNI:570-572 and `execution_accounts/upbit_collector.py:448-449` do today. It gets no
    trade-list path, ticker or bid read, and it never sets the entry block by itself. The drop to 0 is a judged path
    point, so it can trip the floor. `PriceMark` requires a positive price (`execution_accounts/continuous.py:149`),
    so this case is carried outside it. The coordinator's vanish latch (`execution_launch/coordinator.py:775-776`)
    keeps its input. Zero valuation records risk even where no executable market exists. It supplies no executable sale price.
- **BR-4 Every trade counts [Q8].** No print is filtered. Each trade moves its coin's mark and is a path point.
  Interval minimum and maximum are taken over every point, the opening and closing values included. A same-millisecond
  set is evaluated at every price in the set against the holdings before and after any of our fills in that
  millisecond, so the extremes do not depend on an order Upbit does not give.
- **BR-5 Fees [Q3].** Each of our fills takes its fee from the myOrder `trade_fee` when the WebSocket captured that
  fill. When only some fills of an order were captured, `paid_fee` minus the captured fees is split over the
  uncaptured fills by funds: fee_i = remainder x funds_i / (sum of their funds), rounded down to the fee's precision
  with the residue on the last of them, so the parts sum exactly to `paid_fee` [design]. When no fill was captured,
  the whole `paid_fee` is split that way. If the remainder is negative, or a fully captured order's fees do not sum to
  `paid_fee`, allocate that order's total fee in proportion to executed notional (funds), preserve the reported
  order total and record the allocation and alert [OQ15]. This replaces the refusals
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
  volume. Applying `ask_bid` requires paired evidence of which side it reports (see OQ18). The part of an order stopped by self-match
  prevention (myOrder state `prevented`; in REST order detail, state `cancel` with a nonzero `prevented_volume`) has no
  fill, so it is not a miss; any fills that order did have are checked as usual. `cancel_maker` is the announced default
  from 2026-11-09 (changelog notice); A2 confirms it. A miss gets CBA at our fill price.
- **BR-8 Minute-candle audit [Q1].** A separate lagging step, not part of the commit's coverage check: once a 1-minute
  candle is final (A0 measures when; Upbit documents no delay), its low and high are compared with the path's trades
  in [start, start + 60 s). A mismatch is a candle low below the path's lowest trade, a candle high above its highest
  trade, or a candle for a minute where the path has no trade (or the reverse). Response: CBA at the candle low. The
  candle high never raises H. The audit also covers the minutes of long intervals.
- **BR-9 Check-block-alert [Q1, Q7].**
  - **(a) Re-check.** At the given price, BR-13 rechecks adjusted equity and the BR-22 raw protections. A floor breach
    halts by BR-14: the chosen Q1 and Q7 options say "halt on a breach". The daily loss is re-checked the same way, and
    a daily-loss breach sets the persistent daily stop, as today (`execution_control/controller.py:803-811`); it never
    halts [design]. A CBA price inside the unjudged part of a forgiven gap follows BR-16 instead.
  - **(b) Entry block [OQ9].** Set the durable `entry_block` latch immediately. A matching `entry_unblock` may be
    written through either route below. Bind the release to the active block, account, deployment and policy terms;
    journal its cause, authority and supporting evidence. `EVENT_KINDS` is a fixed set
    (`execution_control/store.py:25-28`).
    - **Manual release.** One Telegram button opens the owner approval for the identified block. Display its reason
      and terms and verify user presence and user verification through the independent WebAuthn approval path before
      applying the release. Reuse the existing scoped, single-use approval checks.
    - **Automatic release.** An authorized, tested model may release the latch when verified evidence shows that a new buy offers an
      advantage. With every independent admission check satisfied, continue through the authorized automated order
      path to pursue excess returns without another manual click within a valid deployment. After restart, reconcile
      state, balances and open orders and obtain a valid deployment before using that route. OQ16 ends the old one. A restart alone leaves the latch in place. The model's comparison
      basis, benefit metric and acceptance criterion still require definition; until they are specified and
      validated for the authorized model, no automatic release can be justified. An absent or unproven advantage
      leaves the latch in place for the manual route.
    - Check current permissions, reconciled account and market evidence, and the condition that raised the block.
      Any outstanding input mismatch, missing evidence, independent entry block, daily stop or floor halt remains
      binding. OQ9 can clear only the corresponding entry latch. Each later order still needs valid deployment and
      order authority. A restart or a handoff longer than 30 s ends the standing deployment under OQ16.
  - **(c) Alert delivery [OQ14].** Persist a unique alert for each event (coin, kind and time). At a floor breach,
    entry block or account-chain stop, dispatch immediately through the Telegram bot and Android app as well as the
    configured Windows, iOS and email channels. Track attempts and acknowledgement separately by channel. Retry
    failed sends from the durable record with backoff and deduplicate successful sends by event and channel.
    At `1fd8792`, `_toast_once` (`execution_launch/coordinator.py:617-627`) covers Windows and the daily task
    handles the other existing deliveries (`core/compliance/alerts.py:1-5`). Immediate remote delivery needs
    implementation and device checks. Provide an Android companion alongside the Windows app so the owner can
    inspect current status, alert details and pending approval requests from the phone. An approval notification
    opens its scoped HTTPS request in a browser
    that supports WebAuthn. Verify the enrolled user's passkey and current one-time request before applying the
    approved action. A push delivery receipt or a Telegram/Android button tap supplies no order authorization.
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
    [OQ13]. Unlisted coins follow BR-3. A verified risk condition can trigger an automatic protective sale under
    current risk policy and order authority, up to free app units eligible to sell (BR-23). Check the executable
    market, price, available size and outstanding orders before submitting. Unfilled amounts remain held and
    monitored subject to the existing order policy. Personal holdings enter the risk calculation; OQ4 caps sales
    at app units. Selling personal units would require a separate grant. Expiry, restart or missing data alone
    never supplies the protective trigger (OQ5).
  - A bid that cannot be read, or an empty book, gets the entry block and an alert without a price re-check; the unit
    does not refuse [OQ10].
  - With no Y in force, no buy is prepared, and a held coin is checked with Y = 0, so any bid below the mark gets CBA
    [OQ10]. This matches the D12 fold, where an unset limit counts as the tightest
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
  governs: the next capture rebuilds the gap and splits it at the boundary, and the chain continues [Q9; OQ6]. A boundary rebuilt within the bound is not a missed-boundary safety stop under SD 6.2; one rebuilt later is.
  A boundary whose read meets the BR-11 evidence and timing requirements can supply recovery proof. A required
  22:00 inside the unjudged portion of BR-16 stays unverified, even if its historical value can be rebuilt.

### 3.5 The floor and the halt

- **BR-13 Floor at every point [Q2].** At each judged point the app checks both the flow-adjusted floor and BR-22's protected
  raw-KRW floor. It compares the adjusted day opening minus adjusted equity with the signed daily loss limit. The floor is seeded from the controller's fold (H,
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
  the new anchor carries the journaled H, floor, applicable raw principal and protected high-water floors, cumulative
  flow and daily stop (BR-22). Previously recorded halts stay latched.
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
  - At the cut the applied floor respects the carried BR-22 raw protections as well as the higher of the carried
    adjusted floor and the new signed L, since the guard
    requires the applied floor to be at least the signed one (`execution_launch/continuous_guard.py:464-465`). Outside
    a forgiven gap, the cut point is judged against the new limits and halts by BR-14 if below them. H, the day
    opening and the daily stop carry over and are never lowered.

### 3.6 Long intervals and gaps

- **BR-16 Forgiven gap [Q9, Q9-2].** A forgiven gap is a long interval that spans a detected suspend or restart: the
  launcher's bootstrap after a process start (CL 4.1), or a coordinator gap unit
  (`execution_launch/coordinator.py:1182-1191`) whose timer woke more than 30 s late while no unit was running
  [OQ6]. Any other long interval (a read retry under BR-18, an overrun) is rebuilt the same way but judged at
  every point, as BR-13 does. The rebuild runs in the gap unit or in the bootstrap, not in the startup unit, which has
  a 15 s budget (`execution_launch/coordinator.py:1218-1219`). The gap is split at each Seoul midnight, each needed
  22:00 and each BR-15 cut inside it, and all pieces commit as one unit. Judging:
  - Points in [S, S + 30 s) at the gap's true S are judged one by one, as BR-13 does, so a breach seen just before a
    crash is not forgiven [OQ6].
  - Points from S + 30 s up to E are not judged against the floor or the daily loss [Q9]. A CBA price there (BR-6 to
    BR-10) sets the entry block and alerts but is not judged either [OQ6].
  - The floor and the daily loss are judged at E, the first account record after the gap, under the limits in force
    at E [Q9]. A floor breach there halts by BR-14; a daily-loss breach sets the daily stop.
  - H takes the highest point of the whole gap path [Q9-2]. E is then judged against the floor after that raise, the
    same order as a live interval (`execution_accounts/baseline.py:315`, then the controller's breach test) [OQ6]. The owner accepted under Q8 that a spike high can raise the floor.
  - Interior split points (midnight, 22:00, BR-15 cuts) are advanced in the reducer only and not observed by the
    controller in the unjudged portion. There they are exempt from the reducer's extrema check (`execution_accounts/baseline.py:294-296`) and its
    daily-loss fold (`:310-311`). A midnight value still becomes the new day's opening. A required 22:00 value in the unjudged portion
    creates no `RecoveryCheckpoint` (`execution_accounts/baseline.py:306-308`;
    `execution_launch/continuous_guard.py:482-486`), so that day stays unverified, which latches the daily stop
    (`execution_control/controller.py:807`; RC:72-75) [OQ6].
  - The gap path's true lowest point is kept in the archive and in status for audit, outside the reducer.
- **BR-17 Reach [OQ7].** The trade list goes back at most 7 UTC days (`days_ago` 1 to 7). If S is older than
  that, the part before the reach cannot be rebuilt: the chain stops, the entry block is set and an alert is raised.
  The owner's reviewed re-anchor (`docs/account-baseline-integration.md:200-218`) restores it. Nothing is
  interpolated. Under today's collector a re-anchor needs zero coin inventory and zero open orders
  (`execution_accounts/upbit_collector.py:232-233`; ACC:68-69), the owner's coins included; this design keeps that, and
  a held-coin anchor is a later design [OQ7]. The app must not sell assets to make the account eligible for re-anchoring.
- **BR-18 Unfinished rebuild [OQ17].** A timeout, transport error, 429 or 418 leaves the head at S and raises an alert.
  On a venue limit response, stop reads for the affected endpoint group and shared egress. Honour `Retry-After`,
  any stated ban expiry and the shared limiter's backoff across units and restarts before retrying. Where the
  venue gives no retry time, use conservative backoff. E1's existing per-process pacing and GET retry
  (`execution/transport.py:54-57, 336-360`) must respect the shared wait. No new entry block is
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
  and daily stop are at or above the journal fold, with the day opening equal on the same Seoul day. Restore
  the BR-22 raw principal and protected high-water amounts and F from the same checkpoint.
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
    [OQ2]. An incoming coin is valued at the higher of its mark at `done_at` and its first trade after it, an
    outgoing coin at the lower, so a stale mark cannot create a gain [design].
  - **Unmatched balance difference [OQ8].** For each currency, compare the captured balance with the prior balance
    plus reconciled fills and flows. Preserve any nonzero difference and reconcile the tracking records, withdrawals
    and pocket movements before booking it under BR-22.

  The same rule applies while running, not only after a gap [OQ1]. The main pocket remains the trading location.
  Inter-pocket asset movement is permitted, including while holding; the approved permission scope can include
  Upbit's pocket-management capability (`포켓관리`), which may also be needed to read the transfer records [OQ11].
  Match movement records to balances on both sides. A transfer inside the valued account scope preserves units,
  ownership and total equity; it contributes no external F and no trading P&L. For movements across the measured
  boundary, record the evidenced direction and pocket endpoints and account for the boundary flow exactly once.
  Keep its origin distinguishable from a deposit or withdrawal at the exchange. A missing leg or ambiguous scope
  remains unresolved until reconciled under OQ8. OQ11 specifies the permission category; it supplies no transfer
  instruction, amount, source/destination policy, external withdrawal authority or change of order permissions.

  This replaces the exclusive-account fence (`execution_accounts/collector.py:112-131`), the transfer-scope
  coverage rule (`execution_accounts/upbit_collector.py:237-243`), the flow refusals (`:325-343`) and the KRW lock
  check (`:402-403`), the provider's coin-flow refusal and FIFO equality (`execution_accounts/provider.py:212-229,
  245-248`), the bridge's interval-flow refusal and FIFO profit equality (`execution_accounts/baseline_bridge.py:71-76`;
  FIFO then runs over app and owner fills, with unexplained changes outside it), the producer's flat-only refusal
  (`execution_launch/account_interval.py:118-126`) and the reducer's flow convention and zero-flow rule
  (`execution_accounts/baseline.py:131-132, 282-283`).
- **BR-22 Adjusted equity and protected raw floor [Q9-1; OQ2].** F is cumulative net external flow, with deposits
  positive and withdrawals (including withdrawal fees) negative. Adjusted equity is marked equity minus F. A flow
  changes neither realized trading P&L nor the adjusted day's opening. H, the daily loss calculation and PLB's W0, C,
  A and R retain their flow-adjusted basis.
  - A settled deposit is included in F once and creates no additional loss allowance.
    A settled withdrawal changes F but cannot lower the raw principal floor or the high-water floor already protected
    under the applicable policy before that withdrawal. If marked equity falls below either as a result, record the
    withdrawal, block new buys and alert. The ordinary floor halt, daily stop and BR-16 gap rules still apply at
    their respective check points. The flow itself grants no authority to sell.
  - In raw KRW, enforce the higher of the flow-adjusted floor translated back by adding F and the applicable
    protected raw principal and high-water amounts. Returning withdrawn funds restores the flow-adjusted amount
    through F once. Do not also add those funds to an already carried nominal floor. The same comparison governs buy
    admission, the driver's required cash and the displayed headroom. Charge pending purchases and required cash
    once, in the same units (PLB:236-237, 259). An owner's coin deposit adds no cash or buying power; any increase in the effective
    protected amount reduces the available headroom. Mere equality with the floor does not, by itself, trigger a breach.
  - Journal F and the raw protected amounts with each risk snapshot and carry them through owner-epoch changes,
    restarts and reviewed re-anchors. A restored snapshot must compare against the journal in the same units.
    Re-anchoring must preserve protection without applying a historical flow a second time.
  - Adjusted H never falls on a flow and the adjusted day opening stays fixed
    (`execution_control/controller.py:298-314`; BC:33-37). The launch profile already names the convention
    `externally_cashflow_adjusted` (`execution_launch/profile.py:36`); the reducer gets a matching one.
  - Conventions are bound into the checkpoint digest (`execution_accounts/baseline.py:137-149`). By the same principle
    as BC:120-126 (written for the recovery-cutoff schema), moving a deployment to the flow-adjusted convention is a
    reviewed owner re-anchor (`docs/account-baseline-integration.md:200-218`), carrying H, the day opening, both
    floor bases, F and the daily stop from the journal fold (BR-14, BR-19).
  - **Unexplained changes [OQ8].** Journal and alert on the observed difference. Apply the signed amount only
    after evidence rules out a tracking discrepancy and a withdrawal and reconciles the pocket-transfer records
    under BR-21. Then book a remaining decrease as a loss subject to the floor and daily loss, and a remaining
    increase as a flow that does not raise adjusted H. The residual classification alone imposes no new halt or
    entry block. While the cause is unresolved, keep the evidence and unresolved status; do not book either side
    as profit, loss or flow, or certify reconciliation from those records. If it later matches a tracking correction,
    withdrawal or internal transfer, link the correction to the original observation and recognize its effect once.
  - PLB-O6 ("no flow while a budget is in force", PLB:345-349, 659) is superseded only with the
    amended OQ2 raw-floor protection and flow accounting in force [OQ3].
- **BR-23 App units and owner units [Q9-1].** Both are tracked per coin as journaled FIFO lots.
  - App units = app buy fills - app sell fills - owner-initiated outflows charged to the app. Owner units = owner buy
    fills + coin deposits + classified positive coin residuals - outflows charged to the owner.
  - For a same-scope pocket move, carry each lot's origin to its destination and exclude moved units from main-pocket
    availability. An owner-initiated outflow from measured inventory (a hand sell, coin withdrawal, outward transfer
    across scope, or a classified negative coin residual) is
    charged to app units first, but only up to the app units not locked by open app sells at that time; the rest is
    charged to owner units [OQ4]. A hand sell on Upbit is the documented way out of an app position when the
    app cannot act (SD:206-208), and a resting app sell's units are locked, so a hand sell can only use free units.
  - App units stay between 0 and the balance. If app units plus owner units differ from the balance, an alert is
    raised, and every app sell is capped at the lower of app units and the balance minus owner units, so it never
    sells tracked owner units. The difference is not booked as a loss; the BR-21 residual is separate.
  - **App sell caps.** The cap applies to strategy sells, protective sells and the owner's
    `exit` command. The legacy end-slot target of zero must not produce an expiry-only sale under OQ5
    (`execution_launch/driver.py:448-450`). CL 4.5 "every held unit of the trade coin" (CL:212-220)
    and SD 6.4 "every held unit of a coin traded by this profile" (SD:199-201) become "every app unit".
  - **Driver and runner sites [default, OQ12, pending].** Under the proposal they would read app units and the app's cash: the anchor
    (`execution_launch/live_history.py:561-566`; `execution_launch/driver.py:466-471`), sell sizing (`:336`), the
    other-inventory refusal (`:475-477`, which then ignores owner units), the reserved-cash check (`:478-481`, which
    then excludes cash an owner order reserves), the outstanding-order check (`:482-484`, app orders only), the
    first-bar check (`:487-489`), the universe flat check (`execution_launch/runner.py:408-413`) and the universe
    helpers `held_coins`, `choose_trade_coin` and the extra-coin buy latch
    (`execution_launch/coordinator.py:141-166, 769-779`). The owner has yet to choose whether a reconciled personal coin or order alone blocks the app.
  - **Limits [OQ4].** The whole account (app units, owner units and cash) counts toward L and the daily loss
    limit. The policy budget from the previous day's realized result (PLB:325-326; `execution_control/risk.py:299-311`)
    uses the lower of the app-only and whole-account realized net results. Apply the existing policy to that value,
    preserving its separate rules for zero and negative results. PLB's flat check for preparation (PLB:283, pin 3)
    checks app units only. Buy admission enforces both BR-22 cash-floor checks; an owner purchase that consumes
    the required cash blocks app buys until cash returns. The guarantee G3 (PLB:246) and the
    card's "holds even if this position goes to zero" (PLB:290) cover the app's trades only, and the card says so.
  - **Startup [default, OQ12, pending].** Under the proposal an order identified as personal would no longer block
    (`execution_launch/committed_startup.py:520-524, 575-579`). Reserved personal funds would remain in account
    equity and unavailable to the app; a known personal fill would retain its owner tag. An unknown non-empty
    identifier would still block startup. The OQ12 choice is pending.
- **BR-24 Price paths for every coin [Q9-1].** Every coin with a balance at S, or with a fill, flow or residual in
  [S, E), app or owner, gets a BR-1 to BR-8 path, except an unlisted coin (BR-3); equity sums them.
  - **Public read capacity [OQ17].** The Upbit trade-list limit cited in this design is per public IP. Track the
    currently observed egress and venue group, and coordinate the aggregate budget across concurrent TRADEGEN,
    QUANTGEN or other readers using that route, including multiple PCs behind NAT. A per-process cap alone cannot
    bound the aggregate. For unknown sharing or a change of public egress, assume shared capacity, reduce pacing
    or pause until a safe allocation is known, and carry outstanding backoff forward. Do not switch IPs to obtain
    a fresh quota. Actual network topology and other readers still need observation. No additional venue/account
    privileges are needed for rate coordination. A0 can measure observed unit duration and rate responses.
- **BR-25 Study records [Q9-1].** Each fill and flow in the capture archive carries an origin tag: `app`, `owner`,
  `deposit`, `withdrawal`, `pocket_transfer` or `unexplained`. An unresolved difference retains its evidence and
  reconciliation status until BR-21 and BR-22 classify it. The study, the odds and the outcome ladder use app fills only. Account
  profit and loss uses all of them. A manual trade is recorded but never counted as a strategy result.

### 3.8 Y in the signed limits

- **BR-26 Y in `limit_set` [Y], proposed schema pending separate approval.** The proposal accepts both its current two-key shape, `{total_loss_floor_krw,
  daily_loss_krw}`, and a three-key shape that adds Y (proposed key `bid_gap_fraction`, an exact decimal string with
  0 < Y < 1). A smaller Y is tighter. With no Y in force the app treats Y as 0 (BR-10), so a first-ever Y is a loosening
  and counts from the next Seoul date under D12 (`core/compliance/owner.py:682-684`). The change touches the schema and
  exact-key checks (`core/compliance/owner.py:158-159, 176-190, 243-245`), the D12 fold
  (`core/compliance/owner.py:634-637, 681-729, 742-749, 764-769`), the signer's copy of the schema
  (`tools/signer/sign.py:217-218, 3157-3158`), `OwnerContextClaim` and `_owner_terms`
  (`execution_launch/continuous_guard.py:64-76, 192-194`) and the producer's limit read
  (`execution_launch/committed_producer.py:288-295`). PLB says no owner-log schema or signer change (PLB:71, 419), and
  CL:413 puts `sign.py` changes only in PR L3. The proposed A1 exception needs separate owner approval. The owner signs Y only
  after its parsing code is code-approved, as with a lower floor.

## 4. The committed path (#46-#60) and #58 startup reconciliation

| Committed-path element at `1fd8792` | Under this design |
|---|---|
| Startup blocks on any open order the journal does not know (`execution_launch/committed_startup.py:520-524, 575-579`) | OQ12 remains open. The proposal would allow an identified personal order after reconciliation and keep an unknown non-empty identifier blocked (BR-23). |
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

## 5. Deadline E under the 11-13 rule for fixed and universe profiles

The owner's OQ5 answer applies the 11-13 rule to both profiles. The table identifies the changes from PH and the
legacy driver. At window end, block new entries and request fresh management approval for the held position.

| Topic | PH, merged 11-12 as `dc8a039` | 11-13 decision and the merged code |
|---|---|---|
| A coin held at E (window end or `valid_until`) | The hold ends and the app sells (PH:449-454); `held_at_end` sells at once (PH:240); SD-O8 | No sale because the deadline passed; block entries and request new management approval (`handoff:context/upbit-universe/gpt-20261113/TRADEGEN_PR4D_CAPACITY_AMENDMENT_2026-11-13.md:254, 256-261`; LEDGER row `design-revision-1113`, `handoff:LEDGER.md:166`). Code: `execution_launch/coordinator.py:865-911`, `execution_launch/runner.py:489-520`, `execution_launch/managed_behavior.py:57-65, 245-256`. Main records it in `docs/evidence-object-store-execution-log.md:37`. |
| A restart or the account chain coming back | Sells (PH:147-162, 175-176, 242; SD-O5) | Not a sell signal (`execution_launch/protective_state.py:10-14, 345-347, 375-377`) |
| Inputs that cannot be checked (rule I) | Sell (PH:338-351; SD-O13) | Not a sell signal (`handoff:context/upbit-universe/gpt-20261113/TRADEGEN_PROGRESS_2026-11-13.md:10`) |
| An approach-A mismatch or the bid gap during a hold | Also fires I, so the app sells (PH:348-349, 477-478, 487-490); the owner kept that default (SD-O13) | Nothing sells; CBA (BR-9) is the whole response |
| Resting buys at a stop or at E | Cancel requests (PH:127-134, 192-194) | The deadline grants no cancel authority (`handoff:context/upbit-universe/gpt-20261113/TRADEGEN_CARRY_V2_API_CARD_2026-11-13.md:20`) |
| The universe profile | (not separate) | The legacy universe factory still targets 0 at the end slot (`execution_launch/driver.py:448-450, 567-570`); universe carry is refused (`execution_launch/managed_behavior.py:85-91`) |

What this means for approach A:

- **Rule I and the universe end slot.** Remove the expiry-only target of zero. Expiry, restart, missing inputs, a
  mismatch and a bid gap create no sale signal. A mismatch or bid gap calls for the BR-9 floor re-check, entry block
  and alert, with a halt if the floor breaks. Valid strategy and protective sells may proceed under their own
  conditions and current authority. Expiry alone grants neither sell nor cancel authority.
- **Restart.** Reconcile the prior position and outstanding orders when rebuilding the chain. A recovered account
  record supplies no new management authority. On restart or a handoff over 30 s the old standing deployment ends.
  A reviewed, valid deployment is required for subsequent orders (OQ16).
- **Past E the chain must stay alive** through `monitor_until` (at most window end + 1 day,
  `execution_launch/coordinator.py:444-449`) and across the boundaries scheduled after E (`:250-261`). After
  `monitor_until` no unit runs; the next start rebuilds the gap (BR-16) within reach (BR-17).
- **A coin held past E blocks the next window under today's code,** because both drivers require a flat first bar
  (`execution_launch/driver.py:417-420, 487-489`) and SD refuses preparation while holding (SD:149-150). BR-23 makes
  these checks read app units, so an app coin carried past E still blocks the next window.

The PH clauses above and the legacy universe deadline path require alignment with the 11-13 rule in OQ5.

## 6. Document changes in this PR and on merge

- **Edited in this PR: BC.** The daily-loss convention (BC:14-18) and the extrema sentence (BC:56) get the BR-16 gap
  exception, with the 30 s threshold and the judged first 30 s as specified in OQ6. The flow convention
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
  - no flows while a budget is in force: PLB:345-349 and PLB-O6 (PLB:659), when the OQ2 protection and flow accounting are in force (OQ3);
  - "no owner-log schema or signer change" (PLB:71, 419) and "`sign.py` only in PR L3" (CL:413), for Y only, subject to separate BR-26 approval;
  - PLB:246, 283 and 290 as BR-23 qualifies them under OQ4;
  - rule I on approach-A events (PH:348-349, 477-478, 487-490), as superseded by the 11-13 rule under OQ5 for both profiles.

## 7. Delivery

The delivery plan below describes M7-T3. Changes that depend on an open OQ or BR-26 still need the corresponding decision
before implementation. The sequence was recorded on 2026-11-12 and re-cited at `1fd8792`:

1. **A0 observation.** The existing probe in PR #67 uses public reads, outside D14 and `CAPTURE_FILES`. It
   measures Date-header offsets, visibility of trades at separate 0.5/1/2 s SETTLE targets, repeated reads of
   the same interval, page counts, ticker/candle comparisons, closing-millisecond prices, trailing-slash behaviour,
   observed 429/418 responses, latency and the 09:00 KST boundary. The owner can gather hours or days of observations.
   Public data alone does not establish `ask_bid` semantics or whole-account timing against the five-second envelope.
   - OQ18 permits a separate, optional authenticated Upbit `myOrder` WebSocket observation using the minimum
     query permission supported by the venue. Verify actual entitlement on the owner's system and record a refusal,
     missing events or unresolved permissions truthfully. Observe naturally occurring events without creating
     an order to produce a sample. Restrict access to the private account evidence and keep it separate from public
     A0 logs. This design grants neither order submission nor credential provisioning. The existing public probe
     remains usable without authentication.
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

Outside this design are the journal's size cap (`execution_control/store.py:29-31`), a held-coin anchor (OQ7) and
any change to the study's strategy. Section 5 defines the required behaviour for the legacy end-slot path.

## 8. Owner-only steps this design implies

- Merging this PR (design approval).
- Approving, in design and again in the implementation PR, the `sign.py` and owner-log change for Y (BR-26).
- Running A0 on the owner's PC, and choosing whether to enable the separate query-only session under OQ18.
- After M7-T3: one `code_approved`; the reviewed re-anchor that moves the deployment to the new conventions (BR-22),
  which under today's collector needs a flat account with no open orders, the owner's coins included (BR-17); and
  signing Y.

## 9. Owner questions

**A. Owner-approved answers, 2026-11-23 KST.** The owner confirmed direct authorship of the OQ1–OQ7 approval.
The decisions below apply the recommended answers, including the OQ2 amendment and OQ3 condition.

- **OQ1. Flows while running.** Use the same recording and classification rules during normal operation and
  recovered gaps (BR-21). Track deposits, withdrawals and manual trades.
- **OQ2. Deposits, withdrawals and limits.** Exclude settled flows from trading P&L, protect deposits, and carry F
  across re-anchors. A withdrawal, including its fee, cannot lower existing raw principal or already protected
  high-water floors. If the withdrawal takes equity below a protected floor, record it, block new entries and alert.
  The applicable BR-13/BR-14 protection and the BR-16 gap rules continue. Personal coin deposits never increase
  app buying power. BR-22 specifies the two floor checks.
- **OQ3. PLB-O6.** Allow flows while a budget is in force only with amended OQ2 applied. Flows cannot increase
  the loss allowance.
- **OQ4. Manual trades and limits.** Apply the floor and daily loss test to the whole account. Apply existing next-day
  budget rules to the lower of app-only and whole-account realized net results. Preserve the zero and loss branches.
  Charge manual outflows to free app units first, then owner units. The app may sell only its own units. Its PLB
  preparation flat check and stated guarantee cover its own trades (BR-23).
- **OQ5. Deadline E.** Apply the 11-13 rule to fixed and universe profiles. At E block new entries and request fresh
  management approval. Expiry, restart, unavailable data, a mismatch or a bid gap alone never forces a sale. A valid
  independent strategy or protective sell still requires current authority (section 5).
- **OQ6. Gaps.** Limit the exception to a detected suspend or restart. Judge the first 30 s point by point and keep
  the remaining path for audit. Fold the gap high into H before checking the first post-gap account record. A floor
  breach at that point halts; a daily loss breach latches the daily stop. A required 22:00 within the unjudged
  portion stays unverified and blocks that day's new entries; midnight still sets the next day's opening. A slow
  read while running gets the usual point-by-point checks; a missed boundary after retries stops the chain (BR-12).
- **OQ7. Gap beyond trade-list reach.** Stop the chain, block new entries and alert. The current reviewed re-anchor
  requires zero inventory (including personal coins) and zero open orders. No candle substitution or automatic
  liquidation to meet the re-anchor prerequisite (BR-17).

**B. Owner decisions on OQ8–OQ11.**

- **OQ8. Unexplained changes.** Log and alert. Apply the residual rule only after excluding a tracking discrepancy
  and withdrawal and reconciling pocket movements. A confirmed negative residual counts as loss, a positive
  residual as flow. Unresolved differences keep their evidence for subsequent reconciliation and single booking.
- **OQ9. Lifting an entry block.** One Telegram button initiates manual release through independent WebAuthn
  verification when a new buy has no verified advantage. When a tested model establishes an advantage to buying
  and all other permissions and order checks pass, automatically release the latch and enter through the normal
  trading path to pursue excess returns, regardless of restart, without a further click. The benefit test still
  needs an agreed definition and validation. Apply BR-9(b)'s evidence and authority checks on both routes.
- **OQ10. No bid, no Y.** Accept the proposed fallback. An unreadable bid blocks entries and alerts without rejecting
  the unit. With no Y in force, prepare no buy and check held coins at Y = 0 (BR-10).
- **OQ11. Pockets.** Allow inter-pocket asset movement permission. Retain evidence for both ends, preserve lot
  ownership and classify each movement according to its relation to the measured account scope under BR-21.
  Provisioning this permission and authorizing a specific transfer remain separate steps.

**C. Remaining account decision and subsequent owner answers.**

- **OQ12. Personal holdings and open orders.** Decision pending. Consider an identified personal coin outside the
  universe, a resting personal buy with reserved cash, and an open order whose identifier cannot be reconciled.
  Under the proposed rule the first two can coexist with startup once reconciled, with the personal assets and
  reserved cash unavailable for app orders. The unknown order blocks startup. An alternative is to block startup
  whenever personal inventory or personal orders are present. No choice is recorded yet.
- **OQ13. Coverage and risk sales.** Include personal holdings, holdings outside the universe and dust. A listed
  holding gets its price path and bid-gap checks and an unlisted holding is valued at zero. When the established
  risk policy calls for a sale and an executable market and authority exist, automatically sell up to available
  app units (OQ4). Coverage of personal units grants no authority to sell them.
- **OQ14. Urgent notifications.** Persist urgent events and send immediately through the Telegram bot and Android
  app alongside the configured channels. Provide Android status and pending-request views alongside the Windows
  app. Retry undelivered notifications and deduplicate successful delivery.
  Approval actions use the scoped HTTPS/WebAuthn path in BR-9.
- **OQ15. Fee mismatch.** Preserve the reported order total. On a mismatch allocate fees in proportion to
  executed notional under BR-5 and record the allocation and alert.
- **OQ16. Standing deployment.** Restart or a handoff longer than 30 s ends that deployment. Preserve the
  account chain where BR-16 permits recovery and reconcile balances and orders. Automatic entries under OQ9
  can resume only within a valid deployment. Restart does not itself trigger a sale.
- **OQ17. Shared public IP.** Design for varying egress and readers behind a shared route. Coordinate aggregate
  pacing, honour rate responses and preserve backoff on a route change (BR-18 and BR-24). Confirm the actual
  PC/network arrangement during observation.
- **OQ18. A0 reach.** Permit a separate optional authenticated, query-only `myOrder` WebSocket observation.
  Document actual permissions and naturally observed events privately; reserve orders and other private operations
  for their own authority. The public probe in PR #67 is already separate (§7).
