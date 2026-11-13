# PR 4c independent code review

Base: `971a5389208c85d34fdd6479c96580e9b8fcc68d`. Review covers the working-tree changes, not a merged or owner-approved release.

## Scope

Reviewed the terms v2, observed maximum, IOC, cross-coin renewal, owner audit selection, account listing/valuation, thin-book mark, E1 serialization/value/alert and poll changes and their focused regressions. Reviewed initializer/call-surface changes independently. No external API, owner data, real signing, arm, order or repository mutation was performed by this reviewer. Scratch review notes and pure in-memory probes only.

## Findings

1. **P2 — malformed listings could manufacture zero-valued absence. Resolved in collector; E1 fix reviewed.** The plan filtered missing/non-string market ids from list-of-dict receipts. A hermetic collector probe accepted `[{}]` and `[{"market":null}]` as a proof of absence, producing price 0 and unlisted=True. The new consumer checks now require one structurally valid, unique full market id in each row. Other quote groups, long/numeric-leading identifiers and an empty valid listing remain allowed. E1 marks unknown and keeps normal valuation on malformed input.
2. **P2 — incomplete flags could clear a prior red alert. Resolved.** The planned `unknown not in (flags or {}).values()` was vacuously true for legacy None or incomplete mappings. The implementation now needs coverage for every positive held coin before clearing the category. End-to-end due() regression covers None, empty, missing coin and explicit unknown, followed by a full read. Counts ignore unheld/zero-balance flags.
3. **Compatibility regression — readiness serialized an optional absent field incorrectly. Resolved.** `load(model.jsonable(snap))` includes market_flags=None, contrary to the canonical omission contract. `load(json.loads(dump(snap)))` preserves the canonical byte/hash check. Tests cover legacy None, populated flags and nested flag mutation.
4. **P2 — absent-coin shortcut masks nonfinite nested holding mutation. Resolved and independently reproduced after correction.** Snapshot construction rejects infinity, but its nested holdings mapping remains mutable. Replace one valid holding with Holding(units=inf): the absent path returns cash-only value and live_positions admits it, whereas the existing marked-price path yields inf and live_positions refuses it. The absent branch now requires finite, nonnegative units before zero-valued skip. An independent post-fix probe confirmed inf/NaN/-1 refuse both venue value and live positions; 0/5 retain zero-valued marking. Root was notified with before/after in-memory evidence.

## Boundary review

- The only added exact pure calls are `_SYMBOL.fullmatch` in parse_term_receipts and `type` in validate_observed_order.
- New v2 authority declarations/defaults/annotations are pure; reader functions remain outside the two E2 validation ports.
- Final reviewed initializer hashes:
  - execution/upbit_inquiry.py: `b84e2b291939c70ce20572f18cdf6c962a5054dbcb39f438fc0bc9be1a9d72f0` (stdlib json plus the previously reviewed declarations; no new E2 effect).
  - execution_accounts/instrument_terms.py: `debf4f2f2e095214adf60a193bac5252b4c402373bf3d5e8e039182a74e6a9d0`.
  - execution_accounts/model.py: `e7807322ce6b91df9ada3724e43d64fb39f40bac328bfbcbdd0150498e6d52a2`.
  - execution_launch/instrument_refresh.py: `11f9aaf16bb9528b30146a8887ec0b67a40c32baefd6fc81abd363d123539467`.
- Renewal re-parses issued evidence, compares observed maximum, keeps source/contract identity, and performs refusing checks before head mutation. Sell limits use the observed maximum; buy limits additionally use the v2 cap.
- IOC changes only the IOC create body and create-response identity requirement. Fixed GTC body stays unchanged; only status reads establish terminal state.
- The zero-value exception is explicitly restricted to Upbit in E1; other venue pricing requirements are tested.

## Validation evidence and limits

- Independent AST comparison showed exactly the four planned initializer files and two planned call additions, plus the reviewed json import for malformed-list handling. With the reviewed upbit_inquiry hash set in the reviewer process only, the pure guard returns an empty problem list. The source pin update remains root-owned.
- CRLF was preserved in tests/launch_account_interval.py: baseline 569 CRLF lines, current 571 CRLF lines, zero bare LF in both. Git diff --check flags the two added CRLF lines; this is not a line-ending conversion.
- Task 7 deliberately renamed the stale-last-trade test to include the stale-book case. Baseline test-ID accounting must explicitly record the rename rather than claim every old id is unchanged.
- Suggested additional focused integrity regression: mutate a renewed observation's observed_maximum_krw and require TERMS_OBSERVATION_CHANGED before order validation. Code currently implements this comparison.
- Focused test execution counts reported by implementers are not independently repeated here. Root owns frozen-source integration and full regression. No claim of live strategy qualification or Windows deployment readiness.

## Verdict

No remaining blocking code finding in the reviewed runtime diff. All four findings above are resolved. Final source review is complete; release/merge readiness remains conditional on root frozen-source focused guards and full regression. The requested observed-maximum tamper regression is a pending test-only improvement and does not change this runtime verdict.

## Final source anchors

- execution_accounts/instrument_terms.py:121,174,248 — typed authority, receipt-bound parse, issued-record verification.
- execution_launch/instrument_refresh.py:59,164 — same-chain renewal and observed/cap order validation.
- execution_accounts/upbit_collector.py:132,413 — fresh thin-book mark and complete listing identifiers.
- execution/upbit_inquiry.py:170 — contained held-flag read with structural listing checks.
- execution_accounts/readiness.py:284 — canonical snapshot reconstruction and unchanged hash comparison.
- execution/checks.py:210 — complete positive-holding coverage before alert clearing.
- execution/positions.py:35 — finite/nonnegative unit check before absent-coin zero valuation.

## Late PR4c correction — deeply nested listing response (2026-11-13)

**P2 resolved in source; updated full regression pending.** Independently reviewed the two-file correction from `8137c4712b164c120ec8063e50dc3e05b741c23f` to `c80c56cdab946a80ae40be31432b41c881dcd5a2`. A valid JSON listing with 10,000 nested arrays in an ignored field exceeds the decoder's recursion depth while remaining about 20 KiB. `execution/transport.py:342` decodes the HTTP response before `market_all()` returns; its handler catches ValueError, not RecursionError. Thus this failure previously escaped the new optional listing-read boundary and aborted the snapshot/poll instead of producing the spec §15 unknown-flag amber alert.

The approved correction at `execution/upbit_inquiry.py:187` adds only RecursionError to the local `_held_flags` exception tuple. The existing global `_CONTAINED` tuple, outer snapshot handler and transport behavior are unchanged. The local try covers both the initial HTTP decoding and the subsequent listing parse/classification. Failure returns unknown for every held coin, does not retain the unsuccessful listing receipt, and allows the existing ticker/valuation path to continue. It does not manufacture absence, zero values, successful listing evidence or order authority.

The new `tests/execution_upbit.py:330` regression returns actual nested raw bytes through the fake HTTP fixture rather than injecting an exception. It asserts a successful snapshot, unknown BTC flag, retained BTC price and portfolio value, the normal BTC/USDT ticker request, exclusion of the listing response hash and exactly the held-flag unknown amber alert. No new test or test execution was performed by this reviewer.

Independent AST inspection confirms `_held_flags` is the only changed runtime function body and the initializer surface remains `b84e2b291939c70ce20572f18cdf6c962a5054dbcb39f438fc0bc9be1a9d72f0` on both versions. No initializer or pure E2 call pin change is warranted; the helper remains outside the E2 renewal validation graph. No remaining blocker was found in this correction.

Parent reports that the earlier `8137c471...` full run completed with 2,569 PASS / 0 FAIL / 135 NOT_RUN (2,704 total), and the correction's focused run passed 40/40. Those results are attributed to the parent and were not repeated here. The earlier full result must not be presented as a full run of `c80c56cd...`; the parent will rerun the complete suite against the corrected frozen source before the final delivery verdict.
