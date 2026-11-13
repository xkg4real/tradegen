# P2 account integration — committed state projection and Controller consumption

2026-11-13. The read-only committed-state projection and its existing Controller consumer are implemented. Related validation reconciles to 708 PASS / 0 outstanding FAIL / 1 Windows-only NOT_RUN across an initial 709-case run and a 70-case focused correction run; this is not a single all-green 709-case run. Neither stage enables the production coordinator or authenticates missing venue coverage.

## Why this connection is needed

Controller reads accounts while holding its actual control-journal transaction. Committing a continuous guard from that account callback would enter the same journal again and be refused. Reusing the old advancing account provider after an already completed guard commit would also attempt to advance the baseline a second time. The new path reads the exact already committed account/guard state without reducing or publishing it again.

The existing pure account reconciliation is shared through `reconcile_committed_baseline`. It checks the strict state codec, exact endpoint hash, account identity, FIFO/cumulative and daily profit, half-open fill/flow cutoffs, recovery checkpoint, original observation time and Seoul day. A matching self-digest alone is internal consistency, not proof of commitment or authentic source coverage.

`CommittedAccountProvider.read` therefore additionally requires the actual active, thread-bound Transaction belonging to its actual Journal. It rereads real journal bytes, both checkpoint stores and independently retained heads; binds the exact original package, interval, account source, PREPARE/COMPLETE pair and explicit predecessor heads; and verifies them again before returning. It does not start a transaction, reduce the baseline, commit, initialize a head or perform CAS. An idempotent commit receipt may name a later verified journal prefix after COMPLETE. Normal later risk records are accepted without assuming that the receipt always names the current tail.

The projection retains the original account timestamp, highest valuation, protected floor, observed loss and permanent halt. It also retains the separate same-day stop; that stop is not represented by a fabricated loss or permanent halt. The latest validated prior Controller floor is retained without undoing an earlier valid floor-relaxation epoch. An unsupported relaxation after the matched commit is refused. Controller policy digests use its actual capability codec; guard package digests use the separate account-content codec.

Original owner claims and policy hashes are descriptive metadata. Local storage correspondence does not authenticate their source. The existing Controller now compares the actual sealed current context, owner head, code approval, effective policy and floor/daily terms when it consumes this provider. It preserves the separate daily-stop and permanent-halt metadata and retains the original account timestamp. A changed owner/policy epoch or unsupported floor relaxation refuses use. Legacy callable providers retain their existing contract; the returned projection is not an execution permit.

## Staged validation

I1 development: **72 PASS / 0 FAIL / 0 NOT_RUN**, one continuous **12.091-second** run, including 11 new reconciliation and 28 actual-store/transaction projection cases plus existing account/launch guards. Fingerprint `bea500c2661e93716d5b20f7950cd5eed23a30edb7380cc38267ed92ab8b6258`; source and protected-home metadata unchanged before imports/discovery through completion; nineteen KEYLESS variables; QA restored. The matching runtime was committed as `ba5167f`; subsequent integration with the already verified research-revocation main is `b967b7a`.

Independent review before this run corrected original package-time binding, head readback after final store reads, actual journal-byte readback, retention of the prior control floor, exact Controller policy-hash parity and fixed I/O diagnostics. Actual temporary Journal/stores/heads/commit paths are used; owner and coverage inputs in these local-commit tests are expressly synthetic. Native Windows, actual account failures and live venue continuity are not established.

I2 development: 16 PASS in 19.355 seconds after two retained fixture-only failures (history chronology, then a modified page retaining its prior digest). These tests use actual temporary owner signatures, Journal, stores and heads, with DryRun transport only. They cover current owner changes between reservation and dispatch, same-head effective term changes, source-code changes, stop/halt retention, cancellation and status reconciliation.

The Controller's fixed and carry review dependency lists and the independent signer now include the same ten transitive committed-account dependencies: 25 shared files and 32 carry files total. Actual temporary source mutations demonstrate that either factory and the independent signer detect each dependency change. Exact method-scoped import guard exceptions do not allow neighboring modules, writers, aliases or other methods.

The first broad run was deliberately interrupted after 225 PASS to repair an existing clock-disagreement fixture that omitted the now-required actual transaction. It has no completed-run result and is not counted as a passing integration run. The replacement run at `9944e6aa38209acf3ae48ce144d6da14de3ab7c4` completed all 709 cases in 965.710 seconds: 706 PASS, 2 FAIL, 1 NOT_RUN. Both failures were test-only: the old 15/22 dependency counts and one test source read lacking explicit UTF-8. Runtime sources did not change after this run.

The test-only correction was committed as `81efce3`. One intermediate edit accidentally added an extra closing parenthesis; its 57-case run (54 PASS, 3 syntax/import-related FAIL) is preserved, not hidden or counted as final validation. After correction and AST checking, the affected driver, carry review, launch guard and control guard suites passed all 70 cases in 18.659 seconds. Their identifiers are a subset of the original 709 registry. Replacing those affected results reconciles to **708 PASS / 0 outstanding FAIL / 1 NOT_RUN across two runs**. This is a related regression selection, not the entire repository suite. The Windows-only terminal/GetConsoleMode check was not run on Linux.

Original fingerprint: `993dfcb5f2ba4f30e315dacfdebb53a2b4260b5eea847cd2e2a495cceedea904`. Final fingerprint including corrected tests: `93e81aef848c209139c6d8c41b03976e0cf58f65886a85edd87139ac5a52b670`. Both completed evidence runs used nineteen KEYLESS variables, protected-home metadata checks before imports/discovery through completion, unchanged source fingerprints, and restored QA artifacts. Development counts overlap these runs and must not be added to them.

## Operational boundary

The production coordinator remains rehearsal-only and the continuous live candidate source still refuses unsupported integration. A new timestamp does not refresh the original evidence. The existing Controller's supplied-now contract alone does not prove completion-time freshness after expensive reads; the actual live bridge still needs a trusted final clock/current-owner boundary. Authentic complete path coverage, capture receipts, current held-account/open-order reconciliation, commit-before-publication, P2 restart reconciliation and post-window management authority remain separate prerequisites.

No actual owner-home contents, real key, account, exchange API, activation or order is used. Errors, restarts and the end of the holding window remain non-sale causes. Loss floors and approval scopes are not relaxed.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
