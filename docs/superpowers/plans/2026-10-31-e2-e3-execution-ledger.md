# E2/E3 execution ledger

Development authorized by the owner on 2026-10-31 after explicit approval to merge PR #4 and #5. E1 source checkpoint is 94fb3cb; its full regression is recorded separately. This ledger distinguishes implementation, offline verification and unperformed owner/live setup.

## Decisions

- E2 and E3 use separate signed packages; E1 inquiry remains read-only. Runtime scans include all packages with exact tested exceptions.
- Cash-only limit orders use GTC on Upbit/OKX and DAY on KIS. No GTC behavior is inferred for KIS.
- Private financial settings and target dates are excluded from public examples.
- Tests are serialized under KEYLESS and temporary state. Real network/order/arming/signing actions are not performed.

## Completed checkpoints

- E2-1: strict immutable order and instrument inputs, canonical digests, exact rational lot/tick checks, cross-platform exclusive journal, anchored fsync/checkpoint durability and corruption refusal. Root first integration run verified model 7/7 and store 12/12; no failures or skips in those modules. Cross-thread/process capacity tests use temporary state. Independent model/store source review completed. The process-test exception is pinned to the exact temporary-home worker and tested with negative controls; no process test was removed.

## Integration and review evidence

- E1 final verification is merged into this branch from `5087f99`; PR #6 targets main. Its measured full result is 1584/1706 PASS, 0 FAIL, 122 inherited NOT_RUN in 402.010 seconds. E1 owner-only Task14 setup remains unperformed.
- First partial E2/E3 run: 86/89 PASS, 3 FAIL, 0 NOT_RUN. It omitted not-yet-written session/controller modules and is not a completion record. Failures exposed narrow-guard handling and the raw-send golden fixture; these were corrected with exact exceptions and negative controls.
- First complete eight-module run: 126/127 PASS, 1 FAIL, 0 NOT_RUN. The failure was an OKX sell-capacity fixture using an inherited hyphenated Upbit client ID. It is corrected to an alphanumeric ID without changing capacity assertions; targeted rerun follows. All 29 codec and 15 authenticated transport tests passed.
- Independent reviews corrected aggregate session capital reuse, binding instrument rules and preparation content to the owner-armed ID, exact holdings/promise checks before legacy float gates, shared crypto base inventory, full KIS broker identity, persistent daily/floor stops, H2 day-boundary handling, and contradictory cumulative fill/fee/average evidence before journal append. Dedicated regressions retain each boundary.
- Final acceptance adds four authenticated mocked lifecycle scenarios (KIS KRX, KIS US, Upbit, OKX). They use real temporary signatures and fresh odds, independent wire/auth checks, complete authoritative synthetic fill evidence, stop/exit/cancel flows and explicit unsupported KIS US cancel retention. These are still offline tests, not a production account provider.
- Protocol evidence is in `../specs/2026-10-31-e3-wire-evidence.md`; final API/setup and supported limits are in `../../execution-runbook.md`. Private financial settings remain outside this repository.

## Focused verification complete

- Root rechecked the corrected OKX capacity case and all 10 control guards: 11/11 PASS, 0 FAIL, 0 NOT_RUN. No runtime source change was needed for the fixture correction.
- All four authenticated lifecycle tests passed on their first run. Commands: `python -m tests.control_acceptance orders_lifecycle`; the root focused runner selected `control_guards/` and the corrected capacity test through the same hermetic wrapper.
- The final registered E2/E3 set contains 131 unique tests across nine modules. Every test has passed in the serial focused runs (model7, store12, risk23, session6, controller25, codecs29, transport15, lifecycle4, guards10). This is coverage across runs; the final full-suite record will execute the complete registered set together.
- Parallel source ownership and serial testing retained the approved rapid-development workflow. E2/E3 implementation is saved as an integrated source checkpoint after its disjoint module reviews and focused verification. No intermediate dependency-incomplete result is represented as a complete suite.

## Pending final verification and owner work

- One final inherited/full acceptance run on the frozen integrated source, then measured README/QA/ledger update, PR and handoff.
- Owner configured authoritative account provider, rules/credentials, code signature, arming and actual venue validation remain outside these offline results. E1 Task14 setup remains unperformed.
- New policy strategy remains UNVALIDATED; missing policy inputs, live provider integration and unsupported status shapes are not inferred from passing mocks.
