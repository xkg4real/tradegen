# Fixed carry-v2: deadline handling across evaluation, review and rehearsal

2026-11-13. This change implements a separate fixed Upbit KRW spot GTC behavior revision. It preserves open inventory at the study end, separates strategy decisions from execution blocking, and requests new management approval at the runtime deadline. It does not activate live trading or issue post-deadline management authority. Frozen-source full regression is complete; production activation remains a separate boundary.

## Connected behavior

- Protocol schema 2 explicitly binds `forward-paper-carry-v2`, `protective-carry-v2`, `mark_open_positions` and a closed behavior-document hash. Unknown, partial, mixed and universe-carry combinations are refused. Legacy schema 1 wire representations and terminal-liquidation semantics remain separate.
- Typed decisions distinguish warmup, valid LONG, valid CASH/SELL and unavailable input. The actual program, parameters, prefix, time, cause and decision digest are re-derived from every complete V2 capture. Malformed data is not converted to a recorded lookup failure. V2 marks must equal the exact bid/ask midpoint used by the driver.
- LONG never creates an allocation-rebalancing sale. A valid SELL below the minimum order size remains a SELL verdict with an execution-block reason. The shared behavior derives candidates; it does not authenticate observations or authorize orders.
- Base, double-cost, delayed and benchmark paper scenarios use the same carry terminal policy. FIFO buy costs include buy fees, sell proceeds deduct sell fees, partial cost release rounds down to 18 decimal places and the final sale releases the residual cost. Cash, units, cost basis, actual fees, final mark/source, realized and unrealized net profit are separate. Unsold inventory is valuation, not realized profit; no liquidation fee or fill is fabricated.
- The evaluator validates complete inputs and issues a distinct result before existing statistical and selection checks apply. Manually constructed results are not accepted. Whole-family review preserves rejected candidates and refuses missing or invalid candidate evidence. It does not implement the later PR5 failed-evaluation issuer, immutable bundle or recovery workflow.
- Carry review requests use schema 3/4 and signed body schema 2 with `tradegen-strategy-review/2`. Actual-result summary hashes bind the displayed values even through direct Runner assessment. The independent signer validates the same closed factory/revision/behavior combination without importing the application.
- Legacy driver source closure now includes its new shared behavior dependency: 15 files. Carry commits 22 files, including actual evaluation, capture, Coordinator, protective-store and review-summary dependencies. The independent signer matches both lists. Compatible legacy wire formats do not preserve approval of changed source bytes.

## Deadline and storage path

The real LiveHistory records typed decisions through the final slot, while the driver consumes the causally prior decision. A valid final LONG cannot open a new position. A final SELL remains visible but requires separately supported management authority; that issuer is not present in this change.

Coordinator first commits the original observation/history, then persists the P2 deadline event before calling Runner. This order preserves valid quotes even if protective-state storage is slow and fails. The explicit store must already be provisioned with an independent head and exact context commitments. The bridge never seeds or repairs a head. Closed management refuses further writes; a nonempty reopened writer records restart and reuses the stable request ID.

The P2 event supplies unknown authority, observations and financial-ledger references as unknown. Persisting its outbox request is not approving management or validating the current account. The policy's code field binds the factory implementation closure; actual whole-code owner approval remains separately verified. No permission is inferred from matching hashes alone.

Runner checks the actual issued runtime deadline against a fresh clock after the callback and before reserve/dispatch. A slow callback crossing E cannot submit a new candidate. A reserved order that reaches E before dispatch is preserved for reconciliation, without inventing cancellation authority. These checks do not prove an atomic real-network send deadline; controlled/live composition remains refused.

Existing GTC orders can fill after E. The regression distinguishes a late fill under an existing venue/client identity from a new create. This fixture does not prove a production held-account issuer or reconciliation of every managed-order state. Errors, restart and storage failure remain execution conditions, not strategy SELL signals. Existing risk floors and halt rules remain unchanged.

## Validation

Final complete repository run: **2,936 PASS / 0 FAIL / 135 NOT_RUN**, **3,071 total**, **1,385.116 seconds**, one uninterrupted process. Tested runtime commit: `2b1de13227a8985620f253260dd2ab836a498d0f`. Python/YAML fingerprint:

`3001278c9174a007be7d5531cbedf3f643a6d6dd11b5044a73316d6d7877d36b`

All 2,907 preceding PR4e test IDs and terminal statuses are retained, with 164 additional passing checks including the integrated outcome contract. NOT_RUN comprises the existing 121 macro prerequisites and 14 Windows-specific cases; these are not passes. Source and actual-home metadata remained unchanged from before imports/discovery through completion, and original QA bytes were restored. All work used 19 KEYLESS variables, isolated test homes, synthetic observations and temporary test signing keys. Actual home contents, real keys, exchange APIs, activation and orders were not used.

Eleven real Coordinator-to-history/head-to-Runner tests passed together, including final HOLD/SELL, reused approval requests after restart, late fill under an existing GTC identity, and slow persistence. They exercise actual temporary owner approval and independent Ed25519 signatures; invented source/account fixtures are not production source-completeness issuers.

Independent review found and fixed: no-order E/HOLD valuation incorrectly requiring a stressed executable bid, below-minimum SELL being labelled HOLD, midpoint disagreement, deadline crossing during callback, slow protective persistence losing original history, repeated writes to closed management, missing source dependencies and signed display values not checked through direct Runner assessment.

Development failures remain recorded rather than being counted as acceptance:

- First development run: 113 PASS / 11 FAIL of 124. The common Coordinator fixture used future rules relative to its review time. A subsequent 4 PASS / 7 FAIL run exposed a locked-book fixture (`bid == ask`); the real parser was retained and the fixture corrected.
- A 10 PASS / 1 FAIL Coordinator run exposed the closed-management diagnostic being wrapped as a storage error. Moving that diagnostic outside the storage context produced 11 PASS / 0 FAIL.
- Focused integration: 359 PASS / 1 FAIL / 2 Windows NOT_RUN. The remaining legacy signer display fixture omitted its explicit body schema. Testing both supported body schemas corrected the fixture without weakening typed confirmation; 22 confirmation/review checks passed.
- The first full run was intentionally interrupted after 1,108 results (985 PASS / 2 FAIL / 121 NOT_RUN). Existing credential guards matched a credential-field substring in a new diagnostic. Only that diagnostic was renamed; neither guard was weakened. Both guards and affected capture/review cases then passed (35 PASS). The final 3,071-test run restarted from the beginning on the frozen source above.

Focused runs overlap the final suite and are not added to its total. Earlier selector-launch mistakes ran zero tests and supply no acceptance evidence.

## Remaining production boundaries

This is a fixed-market rehearsal and research behavior revision, not the whole protective lifecycle or an operational trading app. Real account/fill/open-order reconciliation, authenticated source completeness, continuous risk integration, controlled composition and planner, post-deadline management approval, durable reduction dispatch/settlement, sealed research versions and recovery, Telegram/WebAuthn, Windows/iPhone validation and final owner approvals remain separate work. The real `floor_state_check` has not been run by the owner; its result is not assumed.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
