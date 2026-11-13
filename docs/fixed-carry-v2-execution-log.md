# Fixed carry-v2: deadline handling across evaluation, review and rehearsal

2026-11-13. This change implements a separate fixed Upbit KRW spot GTC behavior revision. It preserves open inventory at the study end, separates strategy decisions from execution blocking, and requests new management approval at the runtime deadline. It does not activate live trading or issue post-deadline management authority. Validation below is being completed before delivery.

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

## Validation status

Final frozen-source results and delivery commits will be recorded here after verification. All work uses 19 KEYLESS variables, isolated test homes, synthetic observations and temporary test signing keys. Actual home contents, real keys, exchange APIs, activation and orders are not used.

Independent review found and fixed: no-order E/HOLD valuation incorrectly requiring a stressed executable bid, below-minimum SELL being labelled HOLD, midpoint disagreement, deadline crossing during callback, slow protective persistence losing original history, repeated writes to closed management, missing source dependencies and signed display values not checked through direct Runner assessment.

The first development run completed 124 checks: 113 PASS and 11 FAIL. The common Coordinator fixture used future-dated rules relative to its review time. After correcting those times, real quote parsing exposed a locked-book fixture (`bid == ask`); the parser was retained and the fixture was corrected. These failed runs are preserved and are not final acceptance evidence.

## Remaining production boundaries

This is a fixed-market rehearsal and research behavior revision, not the whole protective lifecycle or an operational trading app. Real account/fill/open-order reconciliation, authenticated source completeness, continuous risk integration, controlled composition and planner, post-deadline management approval, durable reduction dispatch/settlement, sealed research versions and recovery, Telegram/WebAuthn, Windows/iPhone validation and final owner approvals remain separate work. The real `floor_state_check` has not been run by the owner; its result is not assumed.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
