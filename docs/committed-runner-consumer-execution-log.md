# P2 I3d — committed account consumption by Runner

2026-11-13. **Completed related validation: 399 distinct cases pass across the broad run and the affected correction run; no unresolved failures or NOT_RUN cases. This is not one 399-case all-green execution.** The implemented connection is limited to rehearsal with actual local account/guard stores, current owner checks and DryRunAdapter. It does not make launching the app sufficient for automatic trading.

## Implemented behavior

`Controller.observe_committed` returns a `CommittedControllerObservation` containing the final actual account read, its committed projection, the checked risk result and the actual completion time. The account and risk belong to the same validated observation operation. Original account and source timestamps remain unchanged. The projection retains the independent daily stop, high-watermark, protected floor and permanent halt; none is discarded by adapting the provider into a callable. This object is descriptive data, not a new approval, source authenticator or capability.

The operation retains I3c's actual current owner, effective limits, session, physical journal, checkpoint/head and completion-clock checks. Heavy reads cannot extend the original observation lifetime by replacing its timestamp. The existing risk snapshot and latch semantics remain in the observation path; its final result must still match the final checked account/risk inputs.

Explicit reducing work uses the separate `Controller.read_committed_account` method. Its paired result has `risk=None`. It performs the actual account, owner/session, journal/head and completion checks, but does not create a new risk snapshot/halt or require entry-risk result stability. This prevents a conservative floor/daily-stop suffix from becoming an unintended new veto on otherwise independently permitted reducing work. The subsequent existing reserve/dispatch checks still decide whether a sell is allowed. The normal owner loader may retain its existing snapshot effects; this method does not claim that the entire operation is free of filesystem writes.

Runner accepts the exact `CommittedAccountProvider` only in rehearsal, with the same actual Controller/provider identity, matching policy, isolated state root and DryRunAdapter. A tick reconciles durable orders first, obtains one actual paired observation, and uses its account/risk and finite `completed_at` for the quote/strategy path. It does not call the old provider again or replace original source times. Explicit `submit_exit` uses only the account-read route and the actual exit session. A later owner/head change is checked again during reserve/dispatch.

Legacy callable-provider APIs and their requested-time semantics remain supported. Committed observe/controlled modes are explicitly refused. Error, restart and deadline conditions do not manufacture a SELL signal.

## What the new tests actually exercise

The new tests use actual temporary signed owner logs, current owner loading, Journal, baseline/guard stores, independent heads, guard commitment and capability consumption. Account history, continuous paths and coverage are invented fixtures, explicitly not live venue-completeness evidence.

The positive automatic-decision case constructs a new **501-slot** synthetic carry study for the exact committed fixture's capital, account scope, program and instrument rules. It runs the actual recorder and evaluator, signs the actual review with a disposable key, verifies it through `CurrentOwnerAuthority`/`ReviewVerifiers`, and connects the registered carry factory to actual `LiveHistory` and its independently initialized temporary head. Flat account inputs are reconciled and committed before this first history slot; an already-issued account/result is not rewritten to satisfy the driver's initial-state rule. The real tick reaches `DecisionInput` with the exact paired account and returns a qualified warmup **HOLD**, with no capability or create request. This is an integration proof over invented data, not a profitability or production-source claim.

Explicit-exit tests separately exercise actual reducing authorization and one DryRun capability consumption. They cover duplicate/restart suppression, daily stop, retained permanent halt, prior restrictions, owner-epoch changes, source/head damage, delayed quotes and preservation of the old account timestamp. An actual kill after the matched guard commit changes the owner epoch and therefore invalidates that old package; the implementation does not bypass that restriction to preserve an outdated fixture expectation.

Two additional narrow behavior changes have correspondingly narrow tests:

- If stop occurs after an actual committed reservation finishes later than the original tick, local cleanup uses at least the returned reservation's actual `updated_at`, preventing a journal clock rollback. The test calls the extracted cleanup seam after actual reserve and proves local cancellation with zero capability/create. The legacy cleanup test preserves the original caller-requested timestamp. Neither test claims a complete strategy-generated SELL tick.
- A real committed local no-send rejection or DryRun rejection is displayed as neutral `blocked / RUNNER_ORDER_REJECTED`, with actual `order_status=REJECTED`. ACK and uncertain dispatch retain their existing submitted representation; legacy callable behavior is unchanged. These tests feed actual Controller outcomes into the extracted display mapper. They do not replace a strategy callback, fabricate a SELL signal to claim end-to-end coverage, or claim that every rejection happened before transport.

## Validation evidence

All completed runs below used nineteen KEYLESS variables and temporary fixtures. Their summaries report unchanged runtime sources and unchanged protected-home metadata from before imports/discovery through completion. QA output was restored after each run. These are separate runs at different source fingerprints; only the final two runs are reconciled by exact case ID below. They are not one final all-green suite.

| Run | Result | Elapsed | Runtime fingerprint |
|---|---|---:|---|
| Initial development | 86 PASS / 1 FAIL / 0 NOT_RUN, 87 cases | 91.885 s | `dd3d0029250a0802a82b8b0ea6dba4fa3a84da98fff3164ea1429e437c943647` |
| Genuine warmup plus paired Controller observations | 13 PASS / 0 FAIL / 0 NOT_RUN | 20.063 s | `688377ba2de04c676cf00ba52831ee9db57d305df080a4fbd8ec9ef90873cd42` |
| Focused correction/integration, before the three display-mapping tests | 91 PASS / 0 FAIL / 0 NOT_RUN | 100.381 s | `13f270f1998a577a1363c6a8d8d8a2e7b9155ec8304e0b7d79c532de0de9ada9` |
| Broad related run, 399 registered cases | 398 PASS / 1 fixture FAIL / 0 NOT_RUN | 887.730 s | `b728a105236cafc8b48164dc87900a2fb8d8fef065ffba549ca18043aaafaf27` |
| Corrected persisted-metadata assertion; all 22 committed Runner cases | 22 PASS / 0 FAIL / 0 NOT_RUN | 39.567 s | `cc5665045337852c116c09240fbe7d20960e0b033a53783110469382167102e1` |

The initial failure was `COMMITTED_ACCOUNT_OWNER_EPOCH_CHANGED` in the kill/independent-exit fixture. The actual kill changed signed owner state after the prior guard observation. The corrected tests separate a retained precommit restriction from a genuine postcommit owner-epoch change; the latter must refuse. This was a fixture correction, not relaxation of the owner gate.

The 399-case run started at `2a6cc2cd67dc93363b95aa9a3cdda2a18ee6d1be`. Its observed failure is in `test_actual_local_no_send_rejection_maps_to_neutral_blocked_without_a_strategy_tick_claim`: the test indexes persisted `metadata` as a dictionary, but the actual stored representation is a list of pairs, producing `TypeError: list indices must be integers or slices, not str`. The actual local rejection was reached before this assertion. The correction converts those persisted pairs to a dictionary and asserts the full exact three-field local provenance, including the actual dispatch row hash. No production code changed. All 22 committed Runner tests then passed. The broad 399 IDs and the overlapping 22 corrected IDs yield **399 distinct PASS / 0 unresolved FAIL / 0 NOT_RUN across two runs**. Earlier development and warmup counts are not added to this total.

Runtime implementation commit: `1bba7c5d4dfd51cd2f52c0769687a884e2ca1183`; integrated main52 HEAD: `2a6cc2cd67dc93363b95aa9a3cdda2a18ee6d1be`; final test-correction commit: `353f64abf9d5fba579fd29c377333725d1b4db7c`. The final runtime fingerprint includes the corrected test. Machine-readable evidence is retained under `tradegen-session/committed-runner-1113`, including both original result files and the exact-ID `committed-runner-validation-combined` summary/rows. No failed historical result was overwritten.

## Remaining boundaries

There is no new production source/continuous-coverage issuer, committed publication scheduler or controlled launcher. Coordinator's full guard-commit-before-publication connection remains separate. A later fill or order reconciliation does not make the previously committed endpoint current. Existing source completeness, account identity/history, current owner/code/limits, actual session and order gates remain required.

The positive automated tick is warmup HOLD. Automatic BUY and a complete strategy-generated SELL/stop-after-reserve tick are not established by these new tests. No real API, account, owner credential, order, activation or native Windows validation was performed. This change does not guarantee a market return, execution price, deadline-at-the-wire behavior or protection from every real market loss; it preserves the existing protection policy and rehearsal restrictions.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
