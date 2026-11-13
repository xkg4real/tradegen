# PR 4e preflight — runner and coordinator

Date: 2026-11-13 KST. Read-only inspection against source commit `8137c4712b164c120ec8063e50dc3e05b741c23f`
(PR 4c branch), not a claim that PR 4c or PR 4d has merged. PR 4d is not implemented in this checkout yet.
No application code, tests, imports of application modules, network requests, signing or commits were executed here.
Only this scratch Markdown report was written.

Sources:
- `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4e-runner-coordinator.md` (P below).
- `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md`, revision 3, sections 7, 9, 10, 12, 13, 15, 17.
- PR 4d plan contract; current runner, coordinator, history, owner runtime and rehearsal source.
- `handoff/context/upbit-universe/universe-impl-status.md` and CURRENT's two Task 12 corrections.

## Verdict

The sequence remains PR 4c -> PR 4d -> PR 4e. Most quoted edits to existing runner/coordinator/owner code still have
unique anchors, but PR 4e must not be copied verbatim. Two inherited Task 12 amendments are mandatory. One additional
control-flow defect was found in the planned inactive-market handling. The plan's per-PR signature instructions and
blanket line-ending description are stale. Final owner readiness remains much broader than this PR.

## Required corrections and review findings

| ID | Plan/current evidence | Impact | Required implementation/review action |
|---|---|---|---|
| C1 — inherited | P2977, P3001, P3129 use old `run_batch(..., n, now, clock)`. Actual `execution_control/universe_odds.py:146` requires `positions` and `positions_asof`; :151-164 forbids provider calls and requires a recent reconciliation. | Literal implementation raises a missing-keyword error; calling the provider instead can conflict with the worker and advance baseline state. | Read `self._observation` exactly once without acquiring `_work`, check that it exists and is current, pass its `.positions` and `.asof`. The fake run_batch must accept and assert both. |
| C2 — inherited | P3126 chooses now before read_bars. Actual run_batch requires started-now <=30 s. Handoff records >51 reads for multiple coins. | Ordinary bar collection can consume the freshness interval or cross Seoul midnight. | Remember the bars' Seoul date, read bars, then sample the last observation once and take a fresh now. Refuse a changed Seoul date and stale/future observation before invoking run_batch. Do not take even a brief `_work` lock: P3004's test holds it on another thread. |
| C3 — newly found, static control-flow defect | P1592-era test `test_terms_failures_block_slots_only_while_a_coin_is_held` performs inquiry failure then inactive-market failure. P1693 sets `_terms_blocked=True`; P1695 only sets `_vanished=True`. P2539 gates a held slot on `_terms_blocked` before P2812 reaches `_events`. | With a still-marked held coin, a transient terms failure followed by `TERMS_MARKET_INACTIVE` leaves the gate latched. The advertised next-slot vanish/disarm event cannot run. The planned test only asserts `_vanished`, masking the failure. | Add a regression continuing that exact sequence through the next slot and asserting stop/one disarm/no tick. Review a fix that lets the vanish event reach its fresh-frame disarm while never authorizing orders with unavailable terms. Do not simply relax all terms checks. This is statically established; no runtime reproduction was executed in this read-only preflight. |
| C4 — historical prose | P3526-3532 says code-approve after this merge. CURRENT says one final code approval after all universe PRs plus PLB; the clock decision requires its 1 s change before that approval. | Per-PR sign instructions would unnecessarily invalidate the signed owner deployment and contradict the latest workflow. | Rewrite the actual PR body around the final once-only approval sequence. Keep the already signed owner checkout unchanged until its intended deployment step. Code merge is not electronic signing. |
| C5 — byte preservation | Actual `execution_launch/coordinator.py` and `execution_launch/live_history.py` are CRLF, despite the index's broad Python-LF statement. | Text-mode rewriting would churn signed bytes across the whole files. | Preserve CRLF in these two existing files. All other existing PR4e targets inspected are LF; new files can be LF. Compare both normal and ignore-cr-at-eol diff stats. |

C2 ordering detail: taking the observation before a long bar read would itself guarantee stale account input.
Use the latest immutable observation after bars complete; take the comparison clock after capturing that object so
an immediately newer worker publication cannot make an otherwise valid copied object appear future-dated.
Do not reconstruct positions from unrelated reads or make separate `.positions` and `.asof` reads from
`self._observation`. A fresh worker publication during bar collection is expected and should be usable.

## Expected versus actual dependencies

| Dependency | Current checkout | PR4e consumer / action |
|---|---|---|
| PR4a registered_batch, run_batch, session universe_batch_digest, RiskResult.universe, OrderState side/symbol/updated_at | Present | Tasks 2, 4, 5, 12; adopt corrected batch signature. |
| PR4b universe profile/program fields and chooser | Present | Universe construction and max_candidates; fixed-profile digests must remain identical. |
| PR4c v2 terms authority, read(symbol), within_buy_cap, allow_symbol_change, split inactive code, IOC, unlisted marker | Present in current PR4c branch | Tasks 3, 6, 7, 9, 13; recheck from the actual merged base rather than an unmerged branch. |
| PR4d SlotUniverse | Absent here, expected pending | Task 9 import cannot work until 4d. Expected fields: snapshot, flags, tickers, allow, reasons, events. |
| PR4d LiveHistory.record_slot universe keywords | Current API only `(book, account)` | Require keyword trade_symbol, universe, tick_size, positions; accept book=None only for universe windows. |
| PR4d recorded_allow, _universe, _state, chooser state held | Absent here, expected pending | Tasks 7 and 9; use recorded_allow after any size fallback, never the pre-record candidate list. |
| PR4d unavailable-book refusals before write | Not present here | Only HISTORY_BOOK_OFF_TICK and HISTORY_BOOK_MARKET_MISMATCH may retry record_slot once with book=None. Any other refusal misses the slot. |
| PR2 UniverseSlotSource / FlagRead / TickerRead / daily_bars | Present | Slot sources are keyless but rehearsal wraps their reads with the existing signed read guard. |
| ToastQueue, alerts.toast | Absent, expected new Task 1 | Worker starts on first put, not construction; slow PowerShell must never run within a coordinator unit. |
| OwnerRuntime preparation_provider | Optional, rehearsal passes none | New odds command in rehearsal still refuses; this PR does not introduce an actual planner. |

After PR4d merges, re-run the dependency inspection and anchors by content. Pending PR4d changes to live_history and
its tests are expected, not defects to patch around inside PR4e.

## Anchor and shared-file findings

A read-only exact-text scan found unique existing anchors for Runner.tick/run, refresh_instrument_rules,
prepare_launch_session signature/scope/session call, Coordinator construction/prepare/monitor blocks,
OwnerRuntime status/prepare/command, and the complete build_rehearsal Coordinator call. Task 6's import replacement
exists once; Task 7's modified import is expected only after Task 6. Task 5's disarm block contains a literal `...`
in the plan and must be moved structurally, never matched/copied as code. This is a targeted scan, not a claim that
all plan edits were applied in memory or compiled.

The MODULES tuple already includes launch_floor_state_check and launch_clock_check as well as launch_program.
Append new test modules while preserving every existing entry and the PR4d launch_universe_history entry.
No PR4e runtime target belongs to the renewal initializer pin list; do not regenerate renewal pins for convenience.
Task 1 deliberately adds one clean import example to launch_guards, not an unrestricted effects exception.

## Parallel ownership proposal inside PR4e

| Owner | Tasks and files | Dependencies / serialization |
|---|---|---|
| Toast seam | Task 1: alerts.py, toast_queue.py, compliance_cli.py, launch_toast_queue.py | Can develop independently; parent integrates launch_guards and MODULES. |
| Runner | Tasks 2-4: runner.py, launch_runner_universe.py | Sequential within this owner; relies on merged4a/4c. Publish helper fixtures before coordinator tests import them. |
| Coordinator | Tasks 5-12: coordinator.py, launch_coordinator_universe.py | One owner, sequential edits to avoid overlap. Task7 also owns the small live_history.decided_symbol addition after4d. Incorporate C1-C3. |
| Owner adapters | Task13: rehearsal.py, launch_owner_rehearsal.py | Wait until coordinator keyword contract is stable; no collision with coordinator source. |
| Console integration | Task12: tools/owner/launch.py | Keep with coordinator owner or dispatch only after odds/preparation contract frozen. |
| Parent | MODULES registry, launch_guards integration, final docs/pins/review/full suite | Only one writer for each shared file; don't run signed fixture suites while any signed runtime file is changing. |

No additional PR/workstream is needed for these existing-plan tasks. A new design outside this scope still requires
the user's requested explicit approval procedure. Existing signatures, private account data and activation stay
outside agent implementation.

## Required tests at implementation time

No tests were run during this preflight. Execute through the suite wrappers with KEYLESS inputs and temporary
state after the relevant signed source is stable.

- Task 12 corrected batch: another thread holds `_work` while odds completes; one observation object supplies both
  inputs; no provider invocation; missing/stale/future observation refuses without calling run_batch; exactly30 s
  versus >30 s boundary; slow bars >30 s followed by a new worker observation succeed; Seoul-midnight crossing
  refuses even with a fresh observation; same-day slow bars pass a newly sampled now; read errors remain redacted.
- C3: held coin -> inquiry failure -> inactive-market failure -> next slot reaches fresh publish, one vanish
  disarm and no runner tick; repeated slot/event does not repeat kill; disarm false/exception latches status.
- Runner: allow-list missing/empty, wrong snapshot/rule/expired snapshot/bound batch/coin; all normal blocks preserve
  runner liveness; sells and explicit exits ignore entry allow-list; same-symbol active sells block duplicate sell.
- Flat/renewal: exact minimum boundary, unlisted dust, unknown-symbol active order, order.updated_at >= account.asof,
  uncertain IOC sell, pending renewal retry without forking, both coordinator and runner flat checks.
- Slots/history: failed or stale book becomes unavailable; record without a book; retry exactly the two pre-write
  book errors; actual recorded_allow is used after size fallback; record failure still executes events and ends
  the window; no later tick after missed slot; snapshot/flags/ticker absence blocks buys without blocking exits.
- Events/alerts: warning, caution, unknown, absent, vanished, extra holdings, two-slot remainder, window-end
  remainder, sticky missed/disarm-failed state; dedupe and a slow toast never hold the unit lock.
- Adapters: every quote/terms/flags/ticker read keeps the before/after guard; v1 calls remain unchanged; universe
  symbol is passed at read time; rehearsal has no preparation provider and cannot submit a buy.
- Existing fixed-profile runner/coordinator/owner/history suites and all seven guard families from Task14;
  one frozen full suite with actual failure and NOT_RUN accounting, not the plan's illustrative zero-failure line.

## Remaining owner readiness and measurement limits

- `Coordinator` still explicitly supports rehearsal only; controlled mode is refused. PR4e must preserve that.
- `UpbitIntervalSource` remains flat-only; `ContinuousUpbitIntervalSource.__call__` still raises
  CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED. Snapshot/history features do not issue complete held-price evidence.
- Production held-position coverage, durable continuous-guard integration, real planner inputs and controlled
  end-to-end lifecycle remain separate unfinished launch tasks.
- Planned coordinator tests intentionally double LiveHistory, terms, slot reads and universe evidence assessment.
  They do not prove end-to-end build_rehearsal, real prepared universe session/verify_session, actual filled switch,
  delayed IOC fill recovery or live order transport. The plan itself declares these limits at P3534-3547.
- PR5 evaluator/study and new qualified actual captures remain required. No probability, successful strategy,
  capture duration or deployability is inferred from software tests. An actual48 h window needs elapsed time.
- Owner PC measurements remain: public body limits, thin-coin quote freshness, keyed inactive/warning terms,
  daily-bar and batch latency, monitor/slot timing, final-slot72 h replay/runtime and capture size.
- The72 h construction bound alone is not a formal4096-observation capacity guarantee. At the allowed60 s bar,
  a continually flat rehearsal can switch targets each bar (4320 bars in72 h), and repeated parsed observations
  whose renewals fail may consume the unpruned registry faster. Treat capacity as a measurement/review item;
  never claim the72 h ceiling proves liveness for every schedule or silently increase the cap.
- Final owner code/table/audit/review signatures, current private account binding and explicit arm are owner
  actions after the complete approved code line and clock change. Existing frozen research remains unchanged.

Software implementation review only; not legal, tax or investment advice.
