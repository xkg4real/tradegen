# E2/E3 execution ledger

Development authorized by the owner on 2026-10-31 after explicit approval to merge PR #4 and #5. E1 source checkpoint is 94fb3cb; its full regression is recorded separately. This ledger distinguishes implementation, offline verification and unperformed owner/live setup.

## Decisions

- E2 and E3 use separate signed packages; E1 inquiry remains read-only. Runtime scans include all packages with exact tested exceptions.
- Cash-only limit orders use GTC on Upbit/OKX and DAY on KIS. No GTC behavior is inferred for KIS.
- Private financial settings and target dates are excluded from public examples.
- Tests are serialized under KEYLESS and temporary state. Real network/order/arming/signing actions are not performed.

## Completed checkpoints

- E2-1: strict immutable order and instrument inputs, canonical digests, exact rational lot/tick checks, cross-platform exclusive journal, anchored fsync/checkpoint durability and corruption refusal. Root first integration run verified model 7/7 and store 12/12; no failures or skips in those modules. Cross-thread/process capacity tests use temporary state. Independent model/store source review completed. The integration guard's process-test exception is being refined separately, without removing that test.

## Pending

- E1 final full-run record and owner-only Task14 setup distinction.
- E2 risk/session/controller integration and durable stop/approved relaxation verification.
- E3 codecs/authenticated transport end-to-end controller tests.
- Correct first partial integration guard/mock failures, run complete focused and inherited regressions, then full suite.
- Owner configured data/credentials, signature, arming and actual venue validation remain outside these offline results.
