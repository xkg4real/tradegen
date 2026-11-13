# P2 I3c — Controller completion checks

2026-11-13. Implemented and validated: 567 distinct passing related tests across a 566-case regression run and a 67-case affected-scope run. This is not a single 567-case run and does not enable trading on application launch.

## Change

The exact committed-account Controller now requires an explicit clock. It checks original account and owner observation ages, the Seoul policy boundary, actual current owner/code/limits, issued session and instrument-term expiration after expensive preparation and journal work. Original evidence timestamps are preserved. Legacy callable providers retain their contract. A Controller created with a legacy provider cannot opt into committed consumption by replacing its provider later, even if a clock was supplied; the exact constructor-admitted provider is required before any actual committed read.

After the actual DISPATCHING row is durable, the Controller rereads the physical journal under the same active transaction and verifies that its own exact row is still the tail. It reuses the current account, risk, capacity, session and permit checks before entering the existing one-use send capability. It does not issue another permit, advance a baseline, commit a guard or acquire a nested journal transaction.

If it can prove that send was never entered, the transaction and physical tail are intact, and recording time is valid, a refusal is recorded through the existing REJECTED result with fixed local provenance. A changed/torn journal, invalid clock, uncertain write, or an already-entered adapter does not become a local rejection or an automatic retry. A rejection that actually became durable is retained even when its response was lost.

The final risk check shares the existing pure calculation. It compares all risk fields while disregarding repeated copies of the same reason code; the original result and legacy stored rows remain unchanged. This preserves an existing halt plus continuing floor breach without falsely rejecting the status observation. Changed protective floors and daily stops still refuse a stale result.

## Staged evidence

- Development run: 64 cases, 62 PASS / 2 FAIL / 0 NOT_RUN, 92.832 seconds; fingerprint `9ac3c9fa5d6e73b8fec3136c390f74cd73a9a48dea699b16a85a47789e0c049a`. Both failures were test construction errors: issued terms are reparsed into an equal new value, and a legacy cancellation fixture replaced a constructor-bound committed provider instead of constructing a legacy Controller. Actual issuance, expiry checks, reconciliation and fallback cancellation assertions were retained in the fixes.
- Independent review found the duplicate halt-reason comparison defect. A dedicated actual-journal reproduction failed before the runtime correction: 0 PASS / 1 FAIL / 0 NOT_RUN, 3.121 seconds; fingerprint `b39e258b73f23bc029a34d08dde2fe384b19711e1d547b5388de75805697d710`. An earlier mistyped selector matched no tests and produced no test results; its log is retained separately.
- Broad related regression at runtime `f3d9a530d60ad56c0b6b3aece07dd87313c516e6`: **566 PASS / 0 FAIL / 0 NOT_RUN**, 1,129.753 seconds, one process. Fingerprint `42719d6fb3effab2e9a6c3fc48d07a50069d48b3f90fe1b5a78dac3935d84cde`. This includes all control modules plus affected committed account, provider, Runner, Coordinator, carry, terms, owner rehearsal and boundary checks.
- Subsequent review identified a provider-replacement bypass: constructing with a legacy callable and then assigning an exact committed provider skipped clock admission. The actual-operation reproduction failed as expected before correction: 0 PASS / 1 FAIL, 3.307 seconds; fingerprint `d2056f50e4e200b453dc4dd8cef8fdc1e0430528733c44181178f825852819d4`. No approval result was substituted.
- The final correction checks the constructor-admitted provider identity before its read. Affected completion, existing committed-account and control boundary modules then passed **67 PASS / 0 FAIL / 0 NOT_RUN**, 108.795 seconds, one process. This includes observe/reserve/dispatch with both omitted and supplied legacy clocks and no provider/owner read, journal mutation or capability issuance on refusal.
- Final runtime commit: `9266d32af7f0a3215b3ac24f54a7dfb1e28224e8`. The affected run used the preceding HEAD with this exact working change; final Python/YAML fingerprint is `bc0a6b77acfcd2ca12aa1a264036b186a3f2e699ebea3f6759a9b64fd8bc8226`. The broad run's 566 identifiers and final 67 overlap by 66, yielding **567 distinct PASS / 0 outstanding FAIL / 0 NOT_RUN across two runs**. Development/reproduction counts are not added.

Every completed run used nineteen KEYLESS variables, unchanged source fingerprints and protected-home metadata checks from before test imports/discovery through completion. QA bytes were restored. The entire repository and native Windows environment were not rerun. These are temporary-data software checks, not real account faults or market results.

Fixtures use actual temporary owner signatures, signed session issuance, stores, independent heads, transactions and DryRun capability consumption. Market responses, coverage and clock progression are synthetic. No positive issuer registry is manually populated. Boundary tests include expiry equality and minus one microsecond, slow preparation/fsync/owner work, owner/key/code/head changes, durable response loss, torn records and no-send versus adapter-entered uncertainty.

## Operational boundary

This is a Controller completion check, not final socket/send freshness, an authenticated venue-completeness issuer, current guard publication, carry-deadline integration or trading activation. The production source and controlled carry gates remain closed. Runner/Coordinator production assembly, actual held-account/order reconciliation, Windows acceptance and valid scoped owner approvals remain separate work. Storage failures, restarts and a holding deadline are not sale signals. Existing loss floors and halt policy are unchanged.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
