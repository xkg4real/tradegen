# PR4d Task 2 independent review

Date: 2026-11-13. Reviewed immutable commit `f3e6ac3e1e5cdcb74740759ac2a28d4bdf89b298` against Task 1 commit `d34395bd27e0ea30e7a23eed7f626a2ca350bf56`. Source inspection used git blobs/diffs, not the worktree that is moving on to Tasks 3/4.

## Verdict

**No additional blocking finding in the original approved Task 2 implementation. The previously reproduced retained-evidence size P2 remains open and blocks final PR4d merge.** This is approval of the reviewed incremental source against the original plan, not approval of the pending capacity amendment, complete universe execution, replay or production account authority.

The functional implementation follows Task 2. Two docstrings accurately disclose the existing residual-cap refusal and unresolved unconditional guarantee. The proposed second fallback, additional admission policy and new capacity diagnostic were not implemented. Further authorized Tasks 3/4 can proceed with that limitation recorded.

## Account, symbol and arithmetic checks

- `execution_launch/driver.py:194`: universe construction requires IOC, the shared program/profile/protocol rule hash and the universe program kind; the initial profile still matches the protocol benchmark. Fixed construction requires GTC and absent universe rules. This is the intended construction change; per-tick universe behavior belongs to Task 3.
- `execution_launch/live_history.py:369`: the account anchor reads units for the supplied trade symbol while retaining the construction profile's venue, market and account scope. Exact Decimal anchor fields are canonicalized through `_anchor_body` before recording; stale/future account times are refused by `_derive_universe` at line 475.
- Lines 413–423: holdings use finite, nonnegative Decimal units/marks, valid KRW identifiers and aware timestamps. `_plain` enforces existing numeric bounds. Dust is computed with exact Fractions against the construction profile's signed minimum, whose contract remains pinned across the allowed symbol/tick renewal. Duplicate holding symbols are rejected at line 661.
- Existing trust boundary remains explicit: the separate positions tuple is supplied by the trusted account/capture integration. Task 2 does not independently prove that it is complete, reconcile it against every AccountObservation holding, authenticate every individual mark time, or verify the Position.unlisted marker before deriving the stored marker from price zero. These are not new deviations from the reviewed plan; synthetic history tests must not be represented as production account-source readiness.

## Read times, chooser and record semantics

- Lines 389–395 enforce due-time, window end and the ten-second recording window. Lines 467–472 reuse the existing receipt reparsing/freshness sampler, check the requested trade symbol and refuse off-tick books before append. The sampler requires book receipt at or before the slot. The caller can retry with no book as specified.
- Lines 435–456 require the matching snapshot rule and validity interval, validate available read types and hashes, retain only prices for snapshot-listed markets also present in flags, and apply the existing 16-character price and signed millisecond-offset bounds. A failed flag read also makes ticker information unavailable. A valid flag read survives a failed ticker read, preserving warning-to-cash behavior.
- The original plan does not validate or persist FlagRead/TickerRead.received_at here. It consumes the coordinator's per-slot reads; the production reader/coordinator timing contract remains necessary. This review does not describe a raw hash or caller-created read dataclass as proof of source timing/authenticity.
- Lines 478–491 retain the last L+1 price vectors and derive the lag from k−L only when that vector exists. Inputs carry the state before the decision; stored choice carries the resulting state. A terminal slot has no new decision. Lines 494–500 expose the current universe digest and the previous decision's inputs, not the current decision's inputs.
- The returned allow-list and reason/event codes retain the coordinator's caller-supplied meaning. Only the size fallback replaces allow with empty. Task 2 is not a second eligibility-policy issuer.

## State before append and capacity boundary

- `_record_universe` at lines 645–682 validates and serializes into local values. Wrong symbol/tick/input, stale account, late decision and duplicate holding refusals occur before `_append`.
- Both size-loop iterations derive from the original `self._chain`, `self._prices` and `self._state`; the unsuccessful first derivation does not increment the committed chooser state or insert a phantom price vector.
- `_slots`, `_chain`, `_prices`, `_state`, `_inputs` and `recorded_allow` are assigned only after `_append` returns from durable write, independent-head advance and readback. Independent AST comparison confirms `_append` is unchanged from Task 1. Its existing size check precedes `_failed=True`, journal write and head advancement.
- The size comparison uses the exact row envelope and reserves its newline correctly. However, after the second iteration retained holdings/receipt/anchor/snapshot may still exceed the cap; the unchanged append refuses them. The known 279,312-byte reproduction against the 262,144-byte cap therefore remains applicable. The existing 8,000-price test proves only successful first fallback; it does not resolve the residual-size finding.

## Compatibility and evidence

- The fixed recording path still writes exactly index/receipt/anchor. `_slot_at` factors the same three prior timing checks out of `_derive`. The fixed path passes its original profile symbol to the updated anchor helper and refuses supplied universe-only arguments.
- The two fixed golden digests are unchanged. Existing test bytes/identifiers are preserved; the history test file is its previous content plus the planned fixed-input-refusal test. `live_history.py` remains all CRLF (711 lines), `tests/launch_live_history.py` all CRLF (545 lines); driver and universe tests remain LF.
- All four committed blob hashes match `task2-files.json`. Independent AST comparison also confirms `_now` and `_replay` are unchanged. Universe replay is consequently still the scheduled Task 4 dependency at this intermediate commit.
- The recorded `task2-green-summary.json` reports **53 PASS / 0 FAIL / 0 NOT_RUN**, 19 KEYLESS variables, source unchanged and protected real-home metadata unchanged. Reviewed file hashes bind that working-source run to commit f3e6ac3. The result includes the fixed golden test, the planned Task 2 tests and launch guards. This reviewer inspected the result but did not rerun tests while Tasks 3/4 were mutating the worktree.

No runtime/test source edits, network/private-home access, signatures, orders, full-suite run or repository mutation were performed by this reviewer. The next combined-source validation must be run after Tasks 3/4 freeze; final merge remains held for the known capacity-contract gap.
