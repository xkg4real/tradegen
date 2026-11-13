# PR4d Task 4 and combined history review

Date: 2026-11-13. Base: Task 2 commit `f3e6ac3e1e5cdcb74740759ac2a28d4bdf89b298`. Reviewed frozen combined-source fingerprint: `1aac24a84d06886bdc132fc36bbab4428978f366dc86f8d8b22edba3886c9cfe`. Task 3 driver review is separately assigned to universe_ioc.

## Verdict

**No new blocking replay/history finding beyond the known capacity P2.** Task 4 follows the approved original plan and can be included in a clearly labeled draft delivery. Final PR4d merge remains blocked by the unresolved unconditional size guarantee. This review does not approve or implement the proposed second fallback/admission amendment.

The earlier Task 1 and Task 2 review notes remain applicable. Task 4 completes the previously deferred replay path; source qualification and the PR4e coordinator integration remain separate dependencies.

## Replay and cross-contract checks

- `execution_launch/live_history.py:225`: `_parse_record` exactly matches the plan at the AST level. It checks v2 record keys, snapshot shape/hash/distinct market names, sorted distinct flag exceptions, available-flag dependency for ticker data, canonical positive price text, signed integer offsets, and sorted distinct allow-list names. Reasons/events remain lists of strings as specified. It does not authenticate external receipts or reconstruct an independent original snapshot, which the design explicitly delegates to the trusted recording boundary and independent journal head.
- `execution_launch/live_history.py:458`: `_parse_holdings` exactly matches the planned method. It validates row lengths and timestamps, reconstructs canonical holdings through `_holding`, and compares the complete sorted output with the stored list while rejecting duplicate symbols. The stored account evidence is retained; it is not used to invent chooser prices or fills.
- `execution_launch/live_history.py:579`: replay initializes local state, processes every row, requires the fixed identity/sequence/hash chain, and branches by the constructed window's universe mode. Fixed windows continue accepting only the existing three slot-data fields.
- Each universe row checks its own trade symbol and canonical positive tick. A book is reparsed against that symbol and row time; unavailable books remain None. Existing `_derive_universe` rechecks slot/account/book constraints, recreates the bar/chain/price buffer and recomputes the decision. At line 621 the computed choice must equal the stored choice, including the chooser state.
- Replay keeps the last L+1 prices and the two most recent carried-input values. The provider's prior-decision frame therefore has the same inputs before and after restart, including terminal/no-book cases. `recorded_allow` comes from the stored last row, including an empty allow-list after first fallback.
- No replay-derived state is published until the entire journal succeeds and the independent head equals the final row hash. `_prices`, `_state`, `_inputs` and `recorded_allow` are assigned together at line 645 with the previously restored state. Parsing errors and chooser refusals are sanitized to the existing record-invalid diagnostic; identity mismatch and I/O failures keep their existing distinctions.
- Independent AST comparison shows `_replay` is the only changed pre-existing LiveHistory method since Task 2; `_parse_holdings` is the only added class method. `_append`, record-time state handling and the known original size-refusal path are unchanged.

The two planned restart tests cover restored chooser behavior, continued decisions after restart, changed decision derivation, missed-slot refusal and row variants. The root's additional test at `tests/launch_universe_history.py:433` exercises 17 malformed v2 cases after rehashing only the journal, leaving the independent head untouched. It requires parser-level refusal rather than accidentally crediting head mismatch alone, then restores the original bytes and verifies successful restart. This preserves the documented independent-head threat model.

## Actual original-implementation capacity reproduction

The earlier plan-level size proof was converted to a scratch-only test of the actual `LiveHistory.record_slot` and unchanged `_append`.

- Real synthetic `collect_upbit` and `build_observation` validation accepted 1,500 positive-unit unlisted positions, using 1,522 requests within the default limit. Scope and timestamps were bound to the history fixture.
- The real quote parser admitted a 131,072-byte book receipt. The history sampler then admitted it during the actual record call.
- Actual first fallback produced a **279,312-byte** canonical row including newline versus the **262,144-byte** maximum. Flags/tickers were unavailable, allow was empty, and the fallback reason was present; every holding and the original book receipt remained.
- The real `_append` raised **HISTORY_STORE_RECORD_INVALID** before journal write/head advance. Journal bytes and the independent head remained identical.
- All checked memory fields remained unchanged: `_slots`, `_chain`, `_marks`, `_prices`, `_state`, `_inputs`, `recorded_allow`, `_head`, `_size`, `_seq`, `_failed`.

Evidence: `review-capacity-actual.py`, `review-capacity-actual.log`, `review-capacity-actual-evidence.json`, `review-capacity-actual-summary.json` in this directory. The probe used the existing `verify.py` launcher and suite `_wrap`, all 19 KEYLESS variables, temporary state and in-memory scratch-test discovery. It returned **1 PASS / 0 FAIL / 0 NOT_RUN**, with the exact combined-source fingerprint above and unchanged source/protected real-home metadata. PASS means the known refusal and state preservation were confirmed; it does **not** mean the size guarantee is fixed.

## Validation limits and file identity

Parent's combined focused result is **60 PASS / 0 FAIL / 0 NOT_RUN**, under the same source fingerprint. This reviewer inspected its supplied result and ran only the single requested capacity probe, not a full suite or duplicate broad focus run.

Reviewed history SHA-256: `25efe60bc5e7c97b39e351b25b576e969eb3c4c5c85862f7d4b68adce0ee9751`; 773 CRLF lines, no bare LF. The two fixed golden constants and previous fixed-path tests remain unchanged. Reviewed driver SHA-256: `e412781b6ede8f97da4af21fbbf948a6858615a4bb5dd7a251a33a28509f2be5`; combined universe-test SHA-256: `9b220ccbfbcd0d596e38725adf07f665f6cca3517a1e18b53e06fe28ac3ffc57`.

No runtime/test source modification, public write, real API request, private-owner state access, signature, activation or order was performed by this reviewer. The pending capacity decision remains visible and must not be converted into a completed guarantee in a PR description or handoff.
