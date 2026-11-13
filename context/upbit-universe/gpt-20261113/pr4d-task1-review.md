# PR4d Task 1 independent review

Date: 2026-11-13. Base: merged PR #33, `7d256f9090bb4de593bf496b010a9753ae5508fd`. Scope: frozen Task 1 diff only in `/workspace/tradegen-universe-pr4d-1113`.

## Verdict

**No blocking Task 1 finding.** The four-file change implements the approved plan's data types, carried-input chooser adapter, optional frame fields and two tests. No Task 2 recording/construction/capacity behavior or Task 3 live universe driver behavior has been implemented or approved by this review. The capacity amendment remains separate and pending.

The parent will commit and rerun the same 31 focused tests against that exact committed head. This will also include the new test module in the verification launcher's tracked-source fingerprint. Full PR4d/release readiness is not claimed.

## Requirement and source checks

- `execution_launch/driver.py:89`: `UniverseBar` is a frozen keyword-only dataclass with the exact planned symbol, tick, timestamps and nullable book fields. It adds no source read or execution behavior.
- `execution_launch/driver.py:106`: `ChooserInputs` has the prescribed state, top-N, flag/price pair tuples and optional lag-price tuple. It carries one decision's inputs; it does not read account anchors, holdings, fills or historical files.
- `execution_launch/driver.py:130`: both optional frame fields default to None and use `omit_none`. Existing `strategy._plain` omits them while absent. `history_frame_digest` itself is byte-for-byte unchanged at the AST level.
- `execution_launch/driver.py:216`: `chooser_decision` matches the exact approved plan. It requires the intended outer tuple shapes, builds the current and optional lag slots, and delegates the state/value/range checks and strategy rules to the existing `choose`. TypeError and ValueError, including ProgramError, become the fixed sanitized refusal code. No exception detail is exposed.
- Shape-validation boundary: this helper is not a raw history-row parser. It checks outer containers and relies on the existing chooser for state, flag values, positive exact prices and candidate count. It does not separately enforce sorted/distinct nested pairs or market-id spelling; the planned history producer supplies sorted mapping-derived pairs and Task 4 owns canonical stored-row validation. This is the plan's existing boundary, not a new Task 1 deviation or a demonstrated execution bypass. Do not describe this helper as independently authenticating arbitrary carried evidence.
- Independent AST comparison against the merged base found **zero changes to existing driver function bodies** and exactly one added function, `chooser_decision`. Construction still requires the existing fixed profile, and per-tick validation is unchanged. This confirms that Task 2/3 behavior was not pulled into the foundation change.
- `tests/launch_universe_history.py:44` covers normal switching, cash before a lag exists, warning-to-cash, invalid outer shapes, malformed pairs, non-Decimal prices and excess candidates. It uses the existing offline fixture and sanitized-refusal helper.
- `tests/launch_acceptance.py:16` preserves all 31 previous MODULES entries, including floor and clock checks, and appends `launch_universe_history` once. The final line wrap does not alter the parsed tuple.

## Fixed encoding and file preservation

The appended `tests/launch_live_history.py:522` golden test records slots 0–4 and checks the existing fixed row key set, both optional fields absent, and these exact previously computed constants:

- Frame: `59a151ab1b66133c71c030384df91a391178417f9249ec8a34a00558d4e16587`.
- Slot data: `1354351db76d3a43b7e7ed508ae77fd98e3c22698cc70fefa1168c2b80c8bde8`.

They match the immutable plan and the earlier independent preflight reproduction. The Task 1 focused result includes this golden test passing; no expected digest was regenerated or relaxed.

Raw-byte inspection confirms the old history test file is an exact prefix of the new file: 514 original CRLF lines retained, 532 current CRLF lines, zero bare LF. Driver, acceptance registry and new test module remain LF. All prior history-test identifiers remain present; exactly the planned golden test was appended.

Reviewed file SHA-256 values before the parent's commit:

| File | SHA-256 |
| --- | --- |
| execution_launch/driver.py | c095d9bcc6e98878c8cf14330eb002bfe647171cd149eede758ba8f0049a1df8 |
| tests/launch_live_history.py | 3baa780f86cd929b6133bfb311bd078b123821a9aa2d74952ed927cac4ab8456 |
| tests/launch_acceptance.py | efd4656d3d33230730334dc50dc140d6e5d5150792430f2641481951a8e3afa7 |
| tests/launch_universe_history.py | 85d175f76425fb2a303b1e186bd674a810bbaf1ef59d5dac9d87b9df0fc0ab38 |

## Validation evidence and limits

Read the implementer's `task1-green.log` and `task1-green-summary.json`: **31 PASS / 0 FAIL / 0 NOT_RUN**, 19 KEYLESS names, source unchanged during that run and protected real-home metadata unchanged. The implementer reported the two planned RED failures before implementation. The GREEN run preceded only the final MODULES line wrap; the parent will bind the final files with the committed-head rerun.

This reviewer performed source/AST/byte comparisons and inspected the supplied test results; no additional suite, ad hoc runtime test, API request, private-home access, signing, source/test edit or repository mutation was performed. No broader testing is requested for Task 1 beyond the parent's already-planned exact-commit focused rerun.
