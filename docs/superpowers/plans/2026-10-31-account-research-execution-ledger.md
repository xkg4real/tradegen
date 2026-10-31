# Account evidence and strategy research execution ledger

The owner authorized PR #6/#7 merges, account connection development, owner setup preparation, broad strategy research and an academic-style PDF on 2026-10-31. This ledger records software and research evidence separately from live account access and owner actions.

## Merges and source provenance

- PR #6 merged at `7676b80c24fb1f47925e2eec952a311757b7eb47`; PR #7 was retargeted to main and merged at `c5459a29bf01730ad1a9b4a4588dd9b8592fe76f`. Expected heads were checked before each authorized merge.
- New branch `gpt/account-research` starts from the merged E1/E2/E3 implementation. New work needs its own PR approval.
- Protocol and data manifest were committed/pushed at `240c5a1`; the complete research implementation, catalogue and synthetic tests were committed/pushed at `8e7c6c85c5ed3799a7cb6d4ac350ebdf57af1175` before candidate performance was computed.
- The first historical evaluation completed successfully in 15.493 seconds. All outcomes are preserved at `af4d240`: 21,408 asset/configuration pairs, six validation selections, zero candidates passing the frozen exploratory screen. No performance-driven retuning or historical rerun occurred.

## Implementation and review

- The exact evidence provider reconciles settlement cash, FIFO inventory and realized results, fees, external flows, complete page chains, authoritative account scope, current valuations, FX, clock/day boundaries and broker order identities. Source hashes establish content integrity, not source authenticity. A trusted complete venue-history collector remains necessary.
- Review corrected mixing different settlement currencies, counting cash as invested session capital, non-settlement assets disguised as cash, old-day snapshots falsely finalizing yesterday's profit and unbound order FX rates. New orders use authoritative current rates; reservations are valued with current rates. Existing signed venue-exposure limits retain their defined treatment of cash.
- Configuration diagnostics inspect names and non-secret metadata only. Explicit read-only adapters use the existing E1 clients; mocked connectivity does not establish a live connection or execution readiness.
- `execution_accounts` is included recursively in the owner and signer code hashes, runtime scans and acting-module graph. Research code remains separate from the acting runtime. Exact readiness-name exceptions retain negative guard controls.

## Focused verification

- Before historical evaluation, 35 unique research tests passed: data11, engine14, inference7 and guards3. These check data hashes/chronology, causal execution, exact cash/fee behavior, selection, frozen-source refusal, shared-block inference and multiplicity. The first run contained33 tests; two subsequently added orchestration regressions passed before performance evaluation.
- Initial readiness run:12 PASS,2 FAIL,0 NOT_RUN. Both were incorrect fixture expectations: a name-only report legitimately includes the substring `SECRET`, and the E1 Upbit fixture map contains an intentionally unused wallet-status route. Corrections check the entire sentinel credential value, trap `.env` reads and assert the exact eight inquiry routes. Runtime was unchanged by these corrections.
- Corrected readiness rerun:14/14 PASS. Complete account suite:42/42 PASS (provider23, readiness14, guards5). Complete E2/E3 control integration:140/140 PASS,0 FAIL,0 NOT_RUN. The final full result is recorded below. Tests are serialized under all19 KEYLESS names, isolated state and actual-home metadata watches. No skipped test is counted as a pass.

## Research interpretation

- Eight economic families yield223 raw rules, expanded to2,676 configurations per asset across eight assets. Parameter combinations are not independent economic discoveries.
- Existing caches had been inspected in prior research. Chronological splits, delayed execution, cost stresses and multiplicity corrections improve discipline but do not create fresh confirmatory evidence.
- Independent output review verified all21,408 unique rows, validation-only selection and ties, frozen hashes, selection registry persistence, split dates/currencies and both eight-asset Holm calculations. All selected holdout benchmark-comparison adjusted p-values equal1. No candidate passes this finite screen; this is not a proof that no possible strategy has an edge.
- Positive arithmetic average returns can coexist with negative compound wealth growth. Lower volatility/drawdown may reflect reduced exposure. The paper distinguishes those effects from alpha, FIFO realized profits and executable small-account results.

## Live work not completed

The current managed Cloud has no credential/runtime/outbound-identity bindings and does not allow the venue hosts. E1's reviewed direct-only transport also does not support the mandatory Cloud proxy path. This work does not bypass that boundary, broaden inquiry-key permissions, contact a venue, access owner keys, sign code, arm a session or submit an order. Complete authenticated history collection, reviewed network integration, owner configuration/signing/activation, unresolved policy measurements and a suitable independently validated strategy remain prerequisites.

- First full-suite attempt was stopped after119.423 seconds when two inherited text guards found the new diagnostic name `ORDER_CASH_RESERVATION_INCOMPLETE` containing the forbidden order-path token. The partial log contains411 PASS,2 FAIL,45 NOT_RUN; restored prior QA is not this attempt’s result. The diagnostic was renamed `CASH_RESERVATION_INCOMPLETE`; execution logic and guard rules remain unchanged. Both affected guards and the entire account suite passed together:44/44 PASS,0 FAIL,0 NOT_RUN. The final full verification follows this source checkpoint.


## Final verification and delivery

- Full run at `fc6d26a014a61c94bf8aab4cddef5134dc4c03d9` (runtime `fc6d26a`): **1801/1923 PASS,0 FAIL,122 inherited NOT_RUN**, 600.886 seconds. All 86 newly registered cases passed; no inherited case disappeared or changed status. The inherited122 skips are121 unavailable macro inputs and one Windows-only GetConsoleMode case.
- Executed `python tests/run_all.py` with Cloud Python3.13.16, all19 KEYLESS variables asserted, temporary state and unchanged real-home metadata. The existing two localhost cases use loopback permission; no real venue/account/data call occurred.
- All account42, control140 and research35 tests passed together in the full run. The measured study itself was executed once, before any performance-dependent changes; no such changes were made.
- The 17-page PDF, four vector figures,11 references, source, bibliography verification and integrity/visual QA records are committed at `f74a40a`. Every page was rendered and inspected; no overflow, glyph issue, placeholder, LaTeX warning or hash mismatch remained. PDF SHA256: `9807d05e008c58d58502b76cac1578c28caae99716c96a3d28b566f6f2c411e9`.
- Base CLI on the actual Cloud reports all three venue hosts blocked, required credential names absent, the proxy path unsupported and execution readiness false. This is a configuration observation, not a live account authentication attempt.
- PR #8: https://github.com/xkg4real/tradegen/pull/8. This new PR requires its own owner approval before merge. The task's PR attachment API failed with a host connection-closed error; the PR exists and is linked directly.
- Final README, QA and this ledger record measured results; source/protocol/data/candidate catalogue and runtime did not change after their respective freezes. Existing CRLF and LF conventions are preserved. No protected study or QUANTGEN file was changed.
