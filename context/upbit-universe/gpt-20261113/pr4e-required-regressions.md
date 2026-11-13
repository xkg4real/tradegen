# PR4e required regression preparation

2026-11-13. Read-only preparation while PR4d is frozen for its full suite. No tracked edits, repository imports/test execution, APIs, real keys/home, signing, arming or installs. PR4e implementation must wait for PR4d merge and a fresh base check.

Sources: original `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4e-runner-coordinator.md` (especially Tasks5–12), spec sections7/9/12, `pr4e-preflight.md` C1–C3, handoff `context/upbit-universe/gpt-workflow-2026-11-13.md` mandatory PR4e corrections, and current coordinator/universe_odds plus existing test interfaces in `/workspace/tradegen-universe-pr4d-1113`.

Prepared append fragment: `pr4e-required-regressions.py`. It reuses the plan's exact universe test helpers/imports and is **not run or integrated**. These are existing planned safety-contract regressions, not a new live-trading workflow. Root/coordinator owner should review the proposed reuse of refusal codes before integration.

## C3: terms blocked, then held market inactive

Static path:

1. Task6 `_refresh_terms` catches TERMS_INQUIRY_FAILED while a positive-value BTC holding exists; `_terms_blocked=True`.
2. The next refresh returns TERMS_MARKET_INACTIVE; its branch sets `_vanished=True` but leaves `_terms_blocked` set. The planned test stops here.
3. Task9 `_universe_slot` rejects `_terms_blocked and _holding()` **before** fresh `_publish`, history recording and Task10 `_events` execution.
4. No vanish action runs; the normal slot path marks a missed window. This contradicts the planned next-slot stop/disarm behavior.

The fragment continues the exact sequence through the next slot, deliberately keeping the held coin's positive mark so an unrelated zero-price observation cannot hide the bug. It checks fresh publish -> recorded vanish event -> stopped state -> exactly one kill, no Runner.run and no adapter request. It covers successful kill, false kill and raised kill; the latter two require sticky `disarm_failed`. Repeated slot/event does not kill or tick again.

### Minimal code-location recommendation

Keep `_terms_blocked` as the fact that current terms remain unusable. **Do not clear it merely to get past the gate**: preparation/explicit paths must not infer fresh terms from the inactive response.

At `_universe_slot`'s initial held/terms gate, permit the already-latched `_vanished` condition to reach the fresh evidence/history/event path. Keep the readiness check and all other collection/record checks. After events, include the vanish latch itself in the no-runner-tick barrier as a defensive expression of the existing stop/disarm contract. For example, the narrow logical conditions are:

```python
_require(not (self._terms_blocked and self._holding()) or self._vanished,
         "COORDINATOR_CURRENT_TERMS_REQUIRED")
# ... fresh _publish, history attempt, each event action ...
if not recorded or self._stopping.is_set() or self._vanished:
    self._update(reasons=reasons)
    return
```

This is a recommendation, not implemented code. A different reviewed implementation is acceptable if it preserves invalid-terms blocking for all order/preparation paths and proves the same disarm ordering/no-tick behavior. An ordinary inquiry failure with no vanished latch must still refuse the held slot, as the existing Task9 test requires. Flat terms failure must retain its existing buy-only block. A history failure must still execute events, as the original Task10 test requires. Account/publish failure remains a refusal; no unverified frame or fabricated disarm success should be introduced.

## C1/C2: actual PR4a interface and required ordering

Current `execution_control/universe_odds.py:146` is:

```python
run_batch(controller, template, bars, *, n, now, clock, positions, positions_asof)
```

`positions` is `AccountObservation.positions` (`core.compliance.model.Positions`), and `positions_asof` is that **same observation object's** aware `.asof`. Do not substitute `latest_frame.accounts[0].positions`: that is a tuple of account holdings used for history and is a different contract. Do not invoke `_provider`, `controller.account_provider`, or `_publish` during this console operation; they are stateful reconciliation paths.

`Coordinator._publish` currently assigns `_observation` once after the real provider read (coordinator.py:426); `prepare` already captures `observation, now, actual` locally and uses `ACCOUNT_AGE = 30s` (lines710–735). `Coordinator._work` is a non-reentrant `threading.Lock` (line345). The odds call must not acquire it, even briefly, and should use `_now` rather than mutate the unit-only `_time`/`_last_time` ordering from the console thread.

Correct order for the new Task12 method:

1. Capture the existing snapshot reference and initial read time; remember its **Seoul date** for the bars request.
2. Call `read_bars(top_n, now=bars_time, clock=self._clock)` outside `_work`.
3. After it returns, read `self._observation` **exactly once** into a local object.
4. Then take a fresh `now`. Refuse a clock rollback or changed Seoul date; refuse absent, future or older-than-30s observation before run_batch.
5. Pass that object's `.positions` and `.asof` to run_batch with the fresh now. A worker may publish a newer object afterward; do not mix its fields into this batch.

PR4a independently checks `0 <= first_clock - now <= 30s`, `positions_asof <= now`, and `0 <= first_clock - positions_asof <= 30s` before context load/simulation. It rechecks the completion date/clock before writing. The caller precheck does not replace these checks; a scheduling delay may still make the batch refuse safely. There is no need to change run_batch or acquire the account provider to implement C1/C2.

### Fragment mapping and existing coverage

| Prepared test | What it establishes | Current interface / original coverage |
| --- | --- | --- |
| `test_odds_uses_one_observation_without_the_work_lock_or_an_account_provider_call` | Main thread holds `_work`; console thread completes; property spy sees one `_observation` read; exact positions identity/asof reach corrected batch kwargs; provider calls fail the test. | Replaces/extends Task12's old fake `run_batch` signature. Current PR4a `test_batch_never_calls_the_account_provider` already tests the batch's own provider boundary, not the coordinator's. |
| `test_odds_rejects_missing_stale_or_future_observation_before_the_batch` | Missing, 30s+1us and future observations refuse before batch; exact30s accepted with a constant fixture clock. | Reuse proposed existing `COORDINATOR_PREPARATION_ACCOUNT_NOT_CURRENT`. PR4a independently rejects stale/future positions and the extra delay until its first clock read. |
| `test_odds_reads_bars_then_one_fresh_observation_then_the_batch_clock` | Simulated 45s bar paging, worker publication during it, then observation read and fresh clock; succeeds on the same day. | Explicit trace guards against reading either now or observation too early. No actual elapsed wait or market fetch. |
| `test_odds_refuses_a_seoul_day_change_during_bars_even_with_fresh_positions` | 23:59:50 KST +20s crosses midnight; fresh positions do not rescue wrong-date bars; batch never called. | Proposed reuse `UNIVERSE_BATCH_CLOCK_INVALID` consistent with PR4a clock/date contract. No new policy or schema. |

The proposed observation refusal code reuses existing coordinator preparation semantics; the date refusal code reuses the actual batch clock contract. If the implementation owner chooses distinct fixed coordinator codes, update the approved diagnostic expectation deliberately and document it; do not weaken the rejection assertions.

Supplementary cases for the implementation reviewer: same-day clock rollback; naive observation asof; bars-reader failure remains redacted; a valid observation becomes stale only at run_batch's first clock read (existing PR4a test); source snapshot changes during the bars read (actual run_batch reloads its authoritative context and validates required bars). No rule is proposed to trust the console's earlier snapshot over that authority.

## Integration and limits

Only the PR4e coordinator owner should append these tests to `tests/launch_coordinator_universe.py` after the original Task5–12 helper contracts exist. Its source remains CRLF; new test files are LF. Do not change frozen PR4d files or run these against the current missing PR4e runtime. Once PR4e source is frozen, use the established focused suite wrappers, then parent central verification.

The fixture doubles history/terms/source review and uses invented observations. It verifies orchestration and refusal boundaries, not production held-account completeness, real signer behavior, an actual order, a completed prospective study, or a strategy success probability.
