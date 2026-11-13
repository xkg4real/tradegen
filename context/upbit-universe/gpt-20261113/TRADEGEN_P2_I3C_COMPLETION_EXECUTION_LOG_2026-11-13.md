# P2 I3c — Controller completion checks

2026-11-13. Implementation and staged validation are in progress. This document will record the final frozen-source run before delivery. It is not a statement that the application can trade on launch.

## Change

The exact committed-account Controller now requires an explicit clock. It checks original account and owner observation ages, the Seoul policy boundary, actual current owner/code/limits, issued session and instrument-term expiration after expensive preparation and journal work. Original evidence timestamps are preserved. Legacy callable providers retain their contract.

After the actual DISPATCHING row is durable, the Controller rereads the physical journal under the same active transaction and verifies that its own exact row is still the tail. It reuses the current account, risk, capacity, session and permit checks before entering the existing one-use send capability. It does not issue another permit, advance a baseline, commit a guard or acquire a nested journal transaction.

If it can prove that send was never entered, the transaction and physical tail are intact, and recording time is valid, a refusal is recorded through the existing REJECTED result with fixed local provenance. A changed/torn journal, invalid clock, uncertain write, or an already-entered adapter does not become a local rejection or an automatic retry. A rejection that actually became durable is retained even when its response was lost.

The final risk check shares the existing pure calculation. It compares all risk fields while disregarding repeated copies of the same reason code; the original result and legacy stored rows remain unchanged. This preserves an existing halt plus continuing floor breach without falsely rejecting the status observation. Changed protective floors and daily stops still refuse a stale result.

## Staged evidence

- Development run: 64 cases, 62 PASS / 2 FAIL / 0 NOT_RUN, 92.832 seconds; fingerprint `9ac3c9fa5d6e73b8fec3136c390f74cd73a9a48dea699b16a85a47789e0c049a`. Both failures were test construction errors: issued terms are reparsed into an equal new value, and a legacy cancellation fixture replaced a constructor-bound committed provider instead of constructing a legacy Controller. Actual issuance, expiry checks, reconciliation and fallback cancellation assertions were retained in the fixes.
- Independent review found the duplicate halt-reason comparison defect. A dedicated actual-journal reproduction failed before the runtime correction: 0 PASS / 1 FAIL / 0 NOT_RUN, 3.121 seconds; fingerprint `b39e258b73f23bc029a34d08dde2fe384b19711e1d547b5388de75805697d710`. An earlier mistyped selector matched no tests and produced no test results; its log is retained separately.
- Final related run: pending. Final evidence must include all existing control tests, actual committed-account tests, new completion cases and affected Runner/Coordinator/terms regressions. These development counts overlap and must not be summed.

Fixtures use actual temporary owner signatures, signed session issuance, stores, independent heads, transactions and DryRun capability consumption. Market responses, coverage and clock progression are synthetic. No positive issuer registry is manually populated. Boundary tests include expiry equality and minus one microsecond, slow preparation/fsync/owner work, owner/key/code/head changes, durable response loss, torn records and no-send versus adapter-entered uncertainty.

## Operational boundary

This is a Controller completion check, not final socket/send freshness, an authenticated venue-completeness issuer, current guard publication, carry-deadline integration or trading activation. The production source and controlled carry gates remain closed. Runner/Coordinator production assembly, actual held-account/order reconciliation, Windows acceptance and valid scoped owner approvals remain separate work. Storage failures, restarts and a holding deadline are not sale signals. Existing loss floors and halt policy are unchanged.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
