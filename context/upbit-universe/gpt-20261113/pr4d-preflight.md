# PR 4d preflight — universe driver and history

Date: 2026-11-13 KST. Read-only source inspection against main `971a538` plus the shared PR 4c implementation in progress. No PR 4d runtime or tracked test code was changed.

## Verdict

- The implementation anchors and prerequisite interfaces fit the current source. All 19 quoted runtime replacement blocks occur exactly once.
- The PR 4c merge is still a prerequisite. Start a new branch from the confirmed merged main, then recheck the anchors; this preflight is not authorization to base PR 4d on unfinished PR 4c.
- One expected registry difference needs preserving, and the supplied PR description's signing instruction is stale.
- Review the size-fallback residual-input bound before claiming the unconditional “row is never refused for size” guarantee. See G1.

## Sources and prerequisites

Read the complete PR 4d plan (2,073 lines), index/global constraints and universe spec sections 12 and 14, with the current handoff corrections. The planned scope is five files only:

- `execution_launch/driver.py`
- `execution_launch/live_history.py`
- `tests/launch_universe_history.py` (new)
- `tests/launch_live_history.py`
- `tests/launch_acceptance.py`

Present in current source: `ChooserState`, `ChooserSlot`, `choose`, `FlagRead`, `TickerRead`, `UNIVERSE_MARKET`, `universe_top_n`, `Universe`, `UNIVERSE_EVALUATOR_REVISION`, the `omit_none` encoder, PR 4c Upbit IOC support, PR 4c `Position.unlisted`, and PR 0's per-observation profile contract check.

No PLB runtime change has been incorporated into this inspection. If PLB unexpectedly lands first, recheck the handoff overlap note and Task 3's exact sizing expectations against the new merged code; never change expected quantities simply to make tests pass.

## Task dependencies and ownership

| Task | Depends on | Runtime ownership | Tests / acceptance |
| --- | --- | --- | --- |
| 1 — bar/input types and frame fields | Merged PR 4c and existing PR 0/1/2/4b interfaces | `driver.py`: `UniverseBar`, `ChooserInputs`, `chooser_decision`, optional frame fields | Create universe test helpers and chooser test; append fixed-frame golden test; append MODULES entry. 2 new tests. |
| 2 — construction and v2 recording | Task 1 | `driver.py` construction rule; `live_history.py` record format, incremental chooser, account anchor, fallback, `recorded_allow` | Add shared universe fixture helpers and four universe tests; append fixed-path refusal test. 5 new tests. |
| 3 — per-tick driver | Tasks 1 and 2 | `driver.py` bar/quote/decision/holding checks | Four universe tests: two-slot switch, carried prior inputs, per-bar tick/bookless rules, terminal target. |
| 4 — replay | Task 2 | `live_history.py` v2 parsing/replay, restored price/state/input/allow data | Two replay tests, including a missed slot after restart. |
| 5 — integration and delivery | Tasks 1–4 complete and source frozen | No new runtime file | Five guard suites, full suite, base comparison for failures, byte/line-ending checks, PR evidence. |

Recommended parallelization: Tasks 1 and 2 form a serial foundation. After Task 2 freezes, Task 3's driver and Task 4's history replay can use two implementers. They share `tests/launch_universe_history.py`, so the parent should integrate their separate test fragments sequentially, or assign that file to one owner. Do not allow concurrent append/edit operations on that file. An independent reviewer can inspect completed tasks and prepare adversarial cases in scratch in parallel. Run signed-source tests only after the relevant source tree freezes to avoid code-hash churn.

## Anchor comparison and corrections

| ID | Plan versus current code | Required handling |
| --- | --- | --- |
| C1 | Task 1 MODULES closing block omits existing `launch_floor_state_check` and `launch_clock_check`. The quoted old block is absent. | Use the plan's explicit fallback: retain every existing MODULES entry and append `launch_universe_history` once. No new design choice. |
| C2 | Task 5 PR text under “Effect on deployments” says code-approve after this merge. Latest handoff explicitly says one final code-approve after the universe and PLB lines; the separate clock allowance must also land before final approval. | Rewrite the PR text using the current handoff. Keep the signed owner installation at its approved version until the owner intentionally changes it. A new identity still requires a new strategy review and history window before use. |
| C3 | The plan's branch, Windows interpreter and Claude attribution examples belong to the original implementing environment. | Use the GPT branch and existing read-only Cloud Python 3.13 interpreter. Preserve actual authorship and record real execution results. These are operational substitutions, not runtime redesign. |
| A1 | Task 1 driver import/frame anchors, Task 2 construction/import/state/anchor/recording anchors, Task 3 four driver blocks and Task 4 three replay blocks | Each of the 19 runtime replacement blocks matches exactly once. Find by text, not stale line numbers. |

## Verified fixed-window baseline

An isolated scratch probe used the existing test fixture, recorded fixed slots 0–4 and computed the plan's two golden digests. Both match before PR 4d:

- Frame: `59a151ab1b66133c71c030384df91a391178417f9249ec8a34a00558d4e16587`
- Slot data: `1354351db76d3a43b7e7ed508ae77fd98e3c22698cc70fefa1168c2b80c8bde8`
- Result: `PASS preflight/fixed_window_golden`.
- Evidence: `pr4d-baseline-probe.py` and `pr4d-baseline-probe.log` in this session scratch directory.

The probe used the suite isolation wrapper, 19 KEYLESS variables and temporary state; it did not run the full suite or touch tracked files.

## Review risks and test gaps

G1 — **Residual row-size bound.** Task 2 `_record_universe` only drops `flags`, `tickers` and `allow`. The proposed input validator accepts unbounded string entries in `reasons`/`events`, an unbounded `positions` tuple, and an unrestricted snapshot top-N size; receipt/anchor data are retained. If those retained fields alone exceed the cap, the second loop iteration still falls through to `_append`, whose current implementation refuses `len(line) > MAX_ROW_BYTES` as `HISTORY_STORE_RECORD_INVALID`. The supplied 8,000-price test exercises the successful flag/ticker fallback only. Before implementation, determine and test the permitted retained-field bounds or narrow the guarantee to valid bounded coordinator inputs. Do not increase the cap or silently drop account anchors. This is a static plan-level finding, not a reproduced failure in implemented PR 4d code.

G2 — **Replay negative cases.** The two planned restart tests cover normal variants and a patched chooser disagreement, but do not directly mutate each v2 key family (`holdings`, canonical tick, snapshot, flags, tickers, decision) while preserving the independent-head tamper model. Existing fixed-row tamper tests remain useful; focused v2 malformed-shape/duplicate/canonical-boundary cases would make the new parser contract reviewable.

G3 — **Price boundary cases.** The proposed code enforces 16-character price text and millisecond offsets within 60,000. The new tests do not assert the exact accepted/refused boundaries or a valid flag-warning read with only the ticker unavailable. Preserve the existing chooser's rule that the warning can force cash even when prices are absent. Do not conflate an absent snapshot with the flag/ticker acquisition contract: the spec's live ticker request is scoped to the snapshot list.

G4 — **Account evidence is caller-supplied.** Proposed history rows take `positions` separately from `AccountObservation`, and several fixtures intentionally pass an empty positions tuple alongside a held account. This plan therefore does not itself prove complete held-position evidence. Keep the production held-position issuer and controlled-mode end-to-end acceptance tasks open; do not label successful PR 4d fixture tests as live account readiness.

G5 — **Deferred coordinator behavior.** Sticky missed-slot status, the 72-hour window bound, current-symbol renewal, retrying an off-tick/wrong-coin book as `book=None`, and passing `recorded_allow` into the runner belong to PR 4e. The unchanged coordinator cannot operate a universe history after PR 4d alone.

## Completion gate

The plan adds 13 tests (11 universe-history tests and 2 fixed-history tests). Preserve the fixed golden digests and all existing suite IDs. Check all guards without regenerating pins: neither driver nor live history is part of the renewal initializer pins. Freeze source before the full suite and before signing-fixture tests; diagnose each failure against the actual merged main rather than inheriting old Windows failure claims.

No real strategy probability, live research PASS, signature, arming or order is established by this preflight. This is a software design review, not legal, tax or investment advice; the author is not a licensed advisor.
