# First-trade blockers 2 to 4: controlled launcher, current planner, study runbook

Date: 2026-11-12 (Asia/Seoul).
Status: proposed. The owner approved this design in conversation on 2026-11-12 (six questions, section 1). Nothing
is implemented. Merging this document approves the design only. It signs nothing, arms nothing and sends no order.
Companion: [standing deployment and multi-day arming](2026-11-12-standing-deployment-design.md), which builds on
this document.

Inputs: [Upbit KRW universe design](2026-11-11-upbit-krw-universe-design.md) and its PR plans,
[principal loss budget design](2026-11-11-principal-loss-budget-design.md) (PLB), `docs/owner-runtime-operations.md`,
`docs/standalone-owner-rehearsal.md`, `docs/remaining-market-readiness-2026-11-06.md`,
[the live-readiness ledger plan](../plans/2026-11-06-live-readiness-execution-ledger.md), and the code at
`origin/main` 0757542. Owner financial parameters remain private and are not written here.
This is software design, not legal, tax or investment advice. Neither the software nor its author is a licensed
advisor.

## 1. Scope and owner decisions

PLB section 7.4 lists four blockers to a first live trade. This document designs three of them.

| # | Blocker | Evidence | Here |
|---|---|---|---|
| 1 | The account interval source is flat-only | `account_interval.py:117-118` | Not designed here. A separate design is in progress. This document uses it only as an interface (3.2). |
| 2 | The coordinator accepts only `rehearsal` | `coordinator.py:281`; built only at `rehearsal.py:368` | Sections 3 to 5 |
| 3 | No odds-plan provider is shipped, so `prepare` refuses | `launch.py:222-225`; `rehearsal.py:374`; `docs/owner-runtime-operations.md:178` | Section 6 |
| 4 | No strategy has passed a prospective study | `docs/first-trade-owner-checklist.md:6` | Section 8: a runbook only, with no new mechanism |

Owner decisions of 2026-11-12:

- **Q1, the study.** One universe study: 48 hours at 300-second bars, 577 slots. The brief that started this
  design named 7 gap-free days at 300 s (2,016 slots). That does not fit the universe capture limit (8.1), and on
  2026-11-05 the owner approved 48-hour drafts (`docs/launch-workflow.md:153-156`).
- **Q2, armings left from an ended process.** The live launcher disarms them itself (4.3).
- **Q3, how long arming lasts.** Once armed, trading continues until the owner says stop, or until the app stops
  itself under a safety rule (for example after a Windows update restart). Multi-day standing arming is designed in
  the companion document.
- **Q4, the standing period.** A fixed cap of 7 days per signature. The study freezes `review_max_age_seconds` at
  30 days (8.2), so one study can be traded for up to 30 days after it ends, re-signed every 7 days.
- **Q5, protective commands.** Two new console commands: `cancel-all` and `exit` (4.5).
- **Q6, holdings after a safety stop under standing arming.** Sold automatically (companion, section 6.4), except
  after a halt, which sells nothing, as PLB (f) says (companion SD-O1, decided 2026-11-12).

**Approach chosen:** a separate live launcher module, `tools/owner/live.py`. `tools/owner/rehearsal.py` is not
edited and stays dry-only. Rejected alternatives:

- A `--mode controlled` flag on `rehearsal.py`. Fewer files, but it would end the guarantee that a rehearsal can
  never send an order, and the tests that prove it.
- One spec for everything. It would be too large to review as one unit.

## 2. Facts this design rests on

- The coordinator refuses every mode but `rehearsal` (`coordinator.py:281`). The runner already has a `controlled`
  mode, but its controller boundary checks only the rehearsal constraints (`runner.py:273-284`).
- `AuthenticatedTransport` is the controller-compatible adapter for real orders (`transport.py:256-275`). Its
  default credentials provider refuses (`transport.py:61-63`), and the module has no environment reader
  (`transport.py:1-8`). `execution/keys.py:24` `read(names)` returns named keys from the environment, then from
  the repository-root `.env`, and never prints a value.
- A prepared session lives only in process memory (`session.py:38`, `_PREPARED`). The owner console loads no session
  from disk (`docs/owner-runtime-operations.md:109-110`).
- The owner-log fold never expires an arming. Only a `system_disarm` clears it (`owner.py:509-522`). Only
  `Controller.kill` writes that entry, and only after a current account observation (`controller.py:850-870`). The
  signer signs no system entry (`tools/signer/sign.py:240-241`). While any arming is open, every preparation is
  refused (`session.py:138-139`), and so is the relaxation route (`controller.py:457`). PLB 9.1 S8 records that no
  shipped command clears an arming left by an ended process.
- `verify_session` requires the preparation's Seoul date (`session.py:221`) and an armed session
  (`session.py:227-228`).
- Exits need no prepared session. A tick sells under `_exit_session_id` (`runner.py:376-384`, `:437`).
  `submit_exit` and `cancel` keep working after a stop (`runner.py:468-500`).
- The fixed driver targets zero at the window end (`driver.py:297`), so every window ends flat.
- Owner tools accept a window of at most one day (`launch.py:107`). The coordinator allows 2 to 20,000 slots
  (`coordinator.py:298-299`), and the universe PR 4e caps a universe window at 72 hours.
- **A race in `prepare` today.** `OwnerRuntime.prepare` calls the provider, which chooses `inputs.now`, before
  `Coordinator.prepare` takes the work lock (`launch.py:222-227`). If a monitor unit publishes a frame in between,
  its `observation.asof` is later than `inputs.now`, and preparation fails with
  `COORDINATOR_PREPARATION_ACCOUNT_NOT_CURRENT`. Section 6.3 fixes this.
- The odds CLI (`core/oddsdata/run.py`) builds `plan.Inputs` through `begin_run` and `build_inputs`
  (`core/oddsdata/inputs.py:179-221`). `begin_run` keeps a comparison registry under `state_root()/odds/`. Reusing an
  issued comparison id reuses its run counter, so the selection seed is reproducible. It allows one writer at a time
  (its note at `inputs.py:186-189`).
- PR 4e (universe) adds the console command `odds`, which calls the preparation provider and uses only
  `.selected_plan`, as the per-coin batch template. `prepare` passes the kept batch. PR 4e also adds
  `_disarm_locked(*, reason, code, republish)` and `_toast_once` to the coordinator. PR 4a makes `Controller.kill`
  record the given reason.

## 3. The controlled launcher

### 3.1 What it builds

`tools/owner/live.py` reads one private config file, schema `tradegen.live/1`. Its fields are those of the rehearsal
config (`rehearsal.py` `load_config`) with four changes:

- `kind` is `controlled`.
- There is no `state_root` field. The state root is `state_root()`: `TRADEGEN_HOME`, else `~/.tradegen`.
- New fields `plan` and `plan_sha256`, for the planner (section 6).
- New field `schedule`, which replaces `window` when standing deployment is used (companion, section 3). Without a
  schedule, the config holds one `window`, as in a rehearsal.

The launcher reuses the rehearsal's account audit parser, read guard and read sources (`parse_account_audit`,
`_ReadGuard`, `_AccountSource`, `_QuoteSource`, `_TermsSource`) by importing them. `rehearsal.py` itself is not
edited. It builds the same composition as `build_rehearsal`, with three exceptions: the mode is `controlled`, the
order adapter is real (3.3), and the account source is the blocker-1 source (3.2).

### 3.2 Gates for the `controlled` mode

`coordinator.py:281` accepts `controlled` as well as `rehearsal`. In `controlled` mode, the coordinator constructor
and the runner's controller boundary (`runner.py:273-284`) both require:

- **The order adapter.** The adapters are exactly `{"upbit": AuthenticatedTransport}`, and its `credentials` is not
  `unconfigured_credentials`. Otherwise `COORDINATOR_LIVE_ADAPTER_REQUIRED` or `RUNNER_LIVE_ADAPTER_REQUIRED`.
- **The account source.** It is the held-capable interval source of the blocker-1 design, checked by exact type.
  The current flat-only source is refused with `COORDINATOR_HELD_SOURCE_REQUIRED`. Until blocker 1 is merged, the
  `controlled` mode cannot be built at all. The only assumption this design makes about that source is its interface:
  `(previous, now) -> BaselineFrame`.
- **The driver.** It is the fixed driver, as in a rehearsal.
- **The state.** The journal base equals `state_root()`. Otherwise `COORDINATOR_LIVE_STATE_MISMATCH` or
  `RUNNER_LIVE_STATE_MISMATCH`. A rehearsal still requires the opposite, a root outside `~/.tradegen`
  (`runner.py:283`).

The rehearsal checks do not change.

### 3.3 The order key

- **A separate Upbit key pair for orders.** Its names are `UPBIT_ORDER_ACCESS_KEY` and `UPBIT_ORDER_SECRET_KEY`. The
  owner creates it on Upbit with only the order-inquiry and place-order permissions. It has no withdrawal permission
  and is restricted to the PC's IP address. The inquiry key (`UPBIT_ACCESS_KEY`, `UPBIT_SECRET_KEY`) stays read-only.
- **How the launcher uses it.** `live.py` builds `AuthenticatedTransport(credentials=_order_credentials)`.
  - `_order_credentials(venue, scope)` requires venue `upbit` and the profile's `account_scope`. It reads both names
    with `keys.read` at each dispatch and returns `Credentials`.
  - It never caches, logs or prints a value. Errors name the key, never its value (`keys.py:4`).
- **Startup checks.** Before any coordinator is built, both names must resolve, else `LIVE_ORDER_KEY_MISSING`. The
  order access key must differ from the inquiry access key, else `LIVE_ORDER_KEY_NOT_SEPARATE`. Both checks run in
  memory and print only key names.
- **Who sets the key.** Setting the key values is an owner act. No agent reads or sets them.

### 3.4 One launcher per home

- `live.py` holds an exclusive OS file lock on `state_root()/live.lock` for its whole life. A second launcher on the
  same home is refused with `LIVE_ALREADY_RUNNING`. The OS releases the lock when the process dies, so no stale lock
  survives a crash.
- The lock also makes the planner the only writer of the odds comparison registry (2, `begin_run`).
- `ponytail:` the lock guards only `live.py`. The odds CLI (`python -m core.oddsdata.run`) and the other owner CLIs
  do not take it, and the owner must not run them against the same home while the launcher runs. A refusal in those
  CLIs can be added if that ever matters.

## 4. Lifecycle

### 4.1 Startup

Each step runs in order. A failed step stops startup with its code. Nothing is prepared or armed at startup.

1. Take the lock. Parse the config. Check the plan file's sha256 (6.1). Check the order key (3.3).
2. Build the coordinator and run `bootstrap`. The startup unit captures the account, observes risk, and reconciles
   every journal order through the runner (`runner.py:386-395`): reserved orders in its namespace that were never
   sent are cancelled, and active orders are reconciled.
3. **Close leftover armings.** Every arming that the owner-log fold still holds open, whether a session arming or a
   standing arming (companion), was signed before this process existed. It is closed with
   `Controller.kill(id, reason="launcher_restart", now)`, using the startup unit's account observation. The fold gains
   one export for this, `open_armings`: a `("session", id)` pair for each id of its `blocking` map
   (`owner.py:512-522`), which covers armings that are already in force and armings stamped for later. The companion
   adds `("standing", id)` pairs. If any kill returns `False` (journal only), startup stops with
   `LIVE_LEFTOVER_ARMING_NOT_CLEARED`. The owner restarts once the account read works.
4. Print the status.

### 4.2 The prepared object

- The prepared session exists only in this process (`_PREPARED`, keyed by object identity). It is never saved and
  never restored.
- The coordinator holds the one `LaunchSession`, and status shows its session id. The owner signs `session_armed`
  for exactly that id with the existing signer event, or uses a standing arming (companion).
- The object is frozen. `verify_session` rechecks its fields on every order (`session.py:217-228`).

### 4.3 Automatic disarm (Q2)

The launcher closes an arming in three cases, through PR 4e's `_disarm_locked` under the work lock:

- **At startup**, as in 4.1 step 3.
- **At the session's `expires_at`.** The schedule gains one explicit unit at that instant, which calls
  `_disarm_locked(reason="session_expired", ...)`. Without it, an expired session stays armed in the owner log, and
  `session.py:138` would refuse the next preparation.
- **On `close`.** The session is disarmed first, then the coordinator closes. `stop` is unchanged: it stops slots and
  does not disarm (`docs/owner-runtime-operations.md:105`).

If the kill cannot write the `system_disarm` because there is no current account observation, status shows
`disarm_failed` (a PR 4e status key) with a red toast. The launcher retries at each monitor unit until the write
succeeds.

### 4.4 What survives a restart

| On disk, continued | In memory only, never restored |
|---|---|
| Control journal: orders, kills, odds batches, preparations | The prepared session |
| Owner log | The odds batch object and the planner's selection (6.2) |
| Account chain head and checkpoints | The coordinator's published frames |
| Live history, one folder per window digest | |
| Odds comparison registry | |

After a restart:

- The startup sequence of 4.1 runs, and leftover armings are closed.
- No buy happens until a new preparation and a new owner arming, or a new standing arming (companion).
- Exits and cancels work as soon as the startup unit has a current account observation and quote.

Two existing rules still apply, and the companion depends on them:

- A slot missed while the process was down ends that window.
- If more than 30 seconds pass between two account captures, the account chain stops. A reboot almost always takes
  longer than that. With the chain stopped, nothing can be read, so nothing can trade, exits included, until the owner
  re-anchors the account in the way the blocker-1 design specifies. Relaxing this rule belongs to blocker 1, not here.

### 4.5 Protective console commands (Q5)

- **`cancel-all`.** It sends a cancel request through `Coordinator.cancel` (`coordinator.py:737`) for every order in
  the runner's namespace with an active status. It reports the request result for each order.
- **`exit`.** It builds one exit signal for every held unit of the trade coin and sends it through
  `Coordinator.submit_exit` (`coordinator.py:741`).
  - The trade coin is the profile's symbol for a fixed profile, and the held coin for a universe profile.
  - The price is the best bid of the current book. A universe profile sells immediate-or-cancel. A fixed profile
    uses its profile's time in force, as the fixed driver's sells do today.
  - Remainders below the minimum order stay in the account (PLB 4.5).
  - It needs a current account and quote, and otherwise refuses with the runner's code.

Common rules for both commands:

- They need no arming and no prepared session, and they work after `stop`.
- They run under the work lock, like `disarm`.
- Their result is "requested", never "filled".

After this design, the console commands are: `status`, `bootstrap`, `odds`, `prepare`, `run`, `stop`, `disarm`,
`close`, `refresh-terms`, `cancel-all` and `exit`.

### 4.6 Failure cases

| Event | What happens |
|---|---|
| Process killed during a dispatch | The controller writes `DISPATCHING` durably before its single send. At restart the order is reconciled. An unknown outcome stays unknown, and new buys are blocked while it is active (`RUNNER_OUTSTANDING_ORDERS`). |
| Power loss, or a Windows update restart | Same as above. The window ends at its first missed slot. The account chain stops if the gap was over 30 s (4.4). |
| Network loss | An account or book read fails, the slot is missed and the window ends. Exits also need reads, so they wait. |
| Clock moves backward | `RUNNER_CLOCK_ROLLBACK` stops the runner. Protective actions refuse while the time is earlier than the last one. |
| An order key is missing or revoked | Startup refuses (3.3). At dispatch, the transport's existing failure path applies, and an acknowledgment is never assumed. |

## 5. Status and alerts

- **New status keys:** `mode` (`controlled`), `lock_held`, `leftover_armings_closed`, `session_expires_at`,
  `planner_selection` (the comparison id, run counter, seed and plan hash, or `null`) and `last_protective_request`.
- **Red toasts** (PR 4e `_toast_once`) on a failed disarm, a refused protective command, and a stopped account chain.
- No amount, key or account number is printed. Amounts that the odds card shows stay on the owner's screen and in
  the private home, never in the repository.

## 6. The current planner

### 6.1 Input

`tools/owner/planner.py` holds one fixed class, `CurrentPlanner`. Its input is one private odds plan file, reviewed
by the owner, in the existing `tradegen.odds_plan/1` schema (`core/oddsdata/run.py`) and holding exactly one plan.

- **Pinned file.** The live config pins the file's sha256. A different file is refused with
  `PLANNER_PLAN_CHANGED`.
- **Start date.** The file's `start` is replaced with the Seoul date at run time, because the CLI requires it to equal
  the context date.
- **Plan checks.** The planner refuses, each with its own code:
  - a leg venue other than `upbit`;
  - for a fixed profile, a symbol other than the profile's coin;
  - a sizing other than `floor_safe` (PLB 4.3, pin 1);
  - the BTC-only replay edge (`plan.py:302`).
- **Stake.** The stake used is the smaller of the file's stake and the PLB cap at that moment. The cap is
  `min(W0, E)` for a fixed profile (PLB 4.3, pin 2) and `min(W0, settled cash)` for a universe profile (PLB-O16),
  read from the coordinator's current observation. The card shows the stake used.

### 6.2 The `odds` step

Fixed profiles get the `odds` command too. The planner:

1. Reads the daily bars with PR 2's receipt-checked `daily_bars([market], now=, clock=)` and builds `plan.Series` with
   PR 4a's `_series`, the same path that the universe batch uses.
2. Calls `begin_run(None, [plan_hash], typed)` for a new comparison, then `build_inputs` with `now` set to the odds
   time. Then it runs `simulate` and `report.render`.
3. Prints the full card, which shows the real odds, together with: pass or refusal, the plan hash, the comparison id,
   the run counter and the selection seed. Every run is registered, so the card discloses how many comparisons the
   plan has been through.
4. Keeps a `Selection` in memory: the plan with today's start and the stake used, the five-tuple from `begin_run`,
   the seed, the Seoul date, and the digest of the bar receipts.

For a universe profile, PR 4e's `odds` calls the planner for the template. The planner sets the template's symbol to
the first coin of `universe_top_n` of the snapshot that the coordinator holds. It runs the steps above for that
coin, and the batch then runs every coin of the top N. All N must pass (universe spec, section 9).

### 6.3 `prepare` in two phases

- **Phase 1, on the console thread, without the lock.** Read the daily bars again and rebuild the series.
- **Phase 2, inside the work lock.** `Coordinator.prepare` takes a builder, `build(now) -> PreparationInputs`, and calls
  it under the work lock with its own `now`. That `now` is never earlier than the latest published observation, which
  removes the race of section 2.
  - The builder reuses the `Selection`'s five-tuple. It writes nothing to the registry, so the comparison id and run
    counter are the same as at the odds step.
  - It passes the odds-time seed as `selection_seed_hex`.
- **Data check.** `prepare_session` already recomputes the seed from the inputs and compares it
  (`session.py:117-146`). If the bars changed since the odds step, for example because a new daily bar became final at
  09:00 KST, preparation is refused, and status says to run `odds` again. If the PLB cap fell below the stake used at
  the odds step, the builder refuses with `PLANNER_STAKE_CHANGED`.
- **`expires_at`** is the earliest of:
  - the window end;
  - the next Seoul midnight less 60 s;
  - the review receipt's expiry less 60 s;
  - for a universe profile, the snapshot's `valid_until` less 60 s (PR 4e already applies this one).

  This replaces the 30-minute default. The 24-hour maximum in `session.py` still holds.
- The rehearsal keeps its plain `PreparationInputs` provider. `PreparationInputs` stays as it is.

### 6.4 What the planner does not do

- It does not choose a plan. The owner writes and reviews the plan file.
- It does not loosen any card check.
- It does not run the replay edge.
- It does not keep a selection across a restart.

## 7. Files and tests for blockers 2 and 3

| File | Change |
|---|---|
| `execution_launch/coordinator.py` | Accept `controlled` and run its gates (3.2); an explicit expiry unit (4.3); `prepare(build=...)` (6.3); `cancel_all` and `exit` over the existing routes (4.5) |
| `execution_launch/runner.py` | The `controlled` branch of `_controller_boundary` (3.2) |
| `core/compliance/owner.py` | Export `open_armings` from the fold (4.1) |
| `tools/owner/launch.py` | Console commands `cancel-all` and `exit`; `odds` for fixed profiles; `prepare` passes the builder |
| `tools/owner/live.py` (new) | Config, lock, key checks, composition, startup sequence |
| `tools/owner/planner.py` (new) | `CurrentPlanner`: the odds step and the builder |
| `docs/owner-runtime-operations.md`, `docs/first-trade-owner-checklist.md` | Updated commands and owner steps |

Closure files among these (`coordinator.py`, `runner.py`, `owner.py`, `launch.py`) need the one final
`code_approved` of section 9.

Tests, by behaviour. All of them use fakes. No test makes a real exchange call or reads a real key or home.

- The `controlled` mode is refused with a `DryRunAdapter`, with `unconfigured_credentials`, with the flat-only
  account source, and with a state root other than `state_root()`. The existing rehearsal tests pass unchanged.
- A second launcher on the same home is refused.
- Startup closes a leftover arming found in a fake owner log, and stops if the kill is journal-only.
- An expired session is disarmed at `expires_at`, and the next preparation is then allowed.
- `cancel-all` and `exit` call only the existing routes, need no arming, and work after `stop`.
- A monitor unit that publishes between phase 1 and phase 2 no longer causes a refusal (the race of section 2).
- Changed bars between `odds` and `prepare` are refused by the seed check.
- Fake key values never appear in status, toasts, logs or exception text.

## 8. Study runbook (blocker 4)

### 8.1 Why 48 hours

- The universe capture limit is `UNIVERSE_CAPTURE_LIMIT`, 12 MiB. The PR 5 plan sizes a worst-case frame at about
  14.9 KB, so about 835 slots fit.
- At 300 s, 577 slots (48 hours) come to about 8.70 MB and fit. 865 slots (72 hours) come to about 13.03 MB and are
  refused, and so are 2,016 slots (7 days), with `STUDY_UNIVERSE_CAPTURE_SIZE`.
- The 7-day study in the original brief is therefore not possible for a universe study at 300 s. The owner chose
  48 hours (Q1).

### 8.2 Freeze parameters

- 300-second bars, 577 slots.
- At most 3 candidates. A candidate needs at least 20 round trips.
- `review_max_age_seconds` = 2,592,000 (30 days), the largest value allowed (`strategy.py:156`). A review receipt
  must still expire by the study end plus that age (`strategy.py:539-542`).
- `prior_attempts` counts every earlier attempt in the family, honestly.

### 8.3 Code that must be merged first

1. Universe PRs 4a to 4e and 5.
2. The PLB code.
3. This design's code and the companion's.

After all three, the owner signs one `code_approved` on the merged head. Every closure change before that would
void it again. The rules re-review, due by 2026-12-02, is independent of all of this.

### 8.4 Owner acts, in order

These are the PLB section 9.3 and universe section 16 acts, merged into one sequence.

1. `code-approve` on the merged head (PLB step 4, universe 16.2).
2. Set the `universe_rule` values, check the file with the venues parser, then sign `approved {kind: venues}`
   (universe 16.3).
3. Private profile: `principal_loss_budget`, the `policy.version` bump, and `policy.source_sha256` (PLB step 5).
4. `limit_set` with the new total-loss floor and the daily value restated, only after step 1 and with nothing armed
   (PLB step 6). It counts from the next Seoul date.
5. On the next Seoul date or later, run the state check (PLB step 7).
6. Add the v2 `universe_terms_authority` to the private account audit (universe 16.4).
7. Run the measurements of universe section 17 on the PC.
8. Freeze with the parameters of 8.2. Publish the commitment before the capture starts. Capture 48 hours with no gap.
   Run `select` (PLB step 8).
9. If `select` prints review requests: export the driver, the review request and the audit, then sign
   `review-approve` (PLB step 9): in the schedule form of the companion for a standing deployment, or in the
   existing form for one session. If it reports `NO_QUALIFIED_MARKET`, nothing
   trades.
10. On the trading day, follow PLB step 10: capture the anchor, run the state checks, run `setup-account`, start
    `live.py`. Then either sign a standing arming (companion) or run `prepare` and sign `session_armed` on the
    returned id (PLB step 11).

### 8.5 The PC during the capture

- Turn sleep off, pause Windows Update, and keep the clock synchronized. `tools/clock_check.py` (PR 26) checks it
  read-only.
- One missed slot ends every candidate. A retry needs a new window and a new `study_id`, and it adds one member to
  the attempt family, which raises the significance bar.

### 8.6 Real odds of the study

- This rotation strategy has no prior evidence of an edge.
- A 48-hour study has low statistical power.
- Passing after costs is unlikely. If no candidate passes, nothing trades, and that is the expected outcome, not a
  failure of the software.

## 9. Delivery order

- **Code order.** Universe PRs through 5 → PLB code → PR L1 (the controlled launcher and lifecycle, sections 3 to
  5) → PR L2 (the planner, section 6) → PR L3 (standing deployment, companion) → one `code_approved`.
- **Before each PR,** run `gh pr list` so that no two open PRs touch one signed-closure file.
- **Signed tables and `sign.py`** change only in PR L3, as the companion describes. Merging the companion spec
  approves that change in design. The PR itself is still reviewed and merged by the owner.

## 10. Risks this design does not remove

- **Ambiguous order outcomes.** An acknowledgment is not a fill (`transport.py:7`). Unknown outcomes block buys until
  they are reconciled.
- **Key compromise.** The order key can trade but cannot withdraw, and only from the PC's IP address. A stolen key
  could still make losing trades, up to what the account holds.
- **Upbit outages and rule changes.** These stop reads, and with them trading and exits.
- **One PC.** Every restart longer than 30 seconds stops the account chain (4.4).

## 11. Real odds

Nothing in this design creates an edge. The PLB ceiling still applies: with no real edge, the chance of reaching a
target `T` from `W0` is at most `LB / (T - W0 + LB)` (PLB 7.1). A far target with a small budget has a small chance.
The most likely result of the study is that no market qualifies, and then nothing
trades. This is not legal, tax or investment advice.

## 12. Defaults chosen without a question

The owner can change any of these when reviewing this document.

| Id | Topic | Default | Alternative |
|---|---|---|---|
| CL-D1 | Order key storage | Two named keys read with `execution/keys.py` from the environment or the repository-root `.env`, separate from the inquiry key (3.3) | Windows Credential Manager, which needs a new dependency or `ctypes` code |
| CL-D2 | Module names | `tools/owner/live.py` and `tools/owner/planner.py` | Any other names |
| CL-D3 | The plan file's `start` | Replaced with the Seoul date at run time (6.1) | One plan file per day, which the owner edits and re-pins daily |
| CL-D4 | Order type of `exit` | IOC for a universe profile; the profile's time in force for a fixed profile (4.5) | IOC for both |
