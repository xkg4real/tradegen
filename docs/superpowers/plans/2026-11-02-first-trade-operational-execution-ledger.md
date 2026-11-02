# First-trade operational execution ledger

Continuation of PR9 from `db7ddeca7de13745f33663cf5801b8d7709512af`, on the
owner's explicit November 2 resume instruction. The October 31 interrupted full
run is not treated as completed. This unit implements the remaining independent
recording, evaluation, account-baseline, quote and deployment diagnostics.

## Completed implementation

- Fixed cash/trend candidate definitions and causal, clock-bound paper capture;
  explicit historical input remains replay/synthetic rather than prospective.
- Bounded-file offline record/evaluate/request-review commands, plus an executable
  invented cash-baseline example. Evaluation always recomputes its own result.
- Exact account baseline reducer with continuous extrema, realized-profit totals,
  Seoul-midnight boundaries and explicit no-external-flow accounting conventions.
  Restores require an independently trusted checkpoint head; it is not a live feed.
- Narrow public Upbit orderbook GET, original response receipts, exact decimals,
  native level checks and stale/future refusal. Quote-to-runner and paper sampling
  bridges preserve original receipt identity and timing.
- Deployment source/dependency manifest export and comparison use the existing
  owner-code hash algorithm. Matching manifests do not create signed approval.
- Canonical unsigned strategy-review requests bind recomputed evidence, program,
  profile and rules. Source and implementation authority remain false.
- Shared suite registration and exact-file/exact-route guards include the new
  code without opening neighboring endpoints or permitting signing/orders.

## Verification before source freeze

- New pure suites: **61 PASS, 0 FAIL, 0 NOT_RUN** (baseline14, quotes16,
  capture14, deployment8, review-request9).
- Offline workflow and launch/account/execution guards: **47 PASS, 0 FAIL,
  0 NOT_RUN** (workflow11, launch guards5, account guards7, execution guards24).
- Actual generator -> record -> evaluate -> request-review command smoke passed.
  The invented cash baseline has 60 observations, zero strategy roundtrips and
  `math_qualified=false`; every source/review/execution authority remains false.
- Tests use all19 KEYLESS inputs, isolated state and fake HTTP only. No owner
  signature, live account connection, deployment activation or order was made.
- Independent read-only review checked quote timing, reducer continuity and the
  distinction between review requests and authenticated review implementations.
- Full acceptance and comparison against main's 1923-case baseline are pending
  the source checkpoint. Measured results will be appended after completion.

## Initial full-run finding

The first full attempt at `c5ae030` was deliberately interrupted after the cockpit
credential-token scan failed. The existing uppercase `CANO` substring prohibition
also matched `NOT_CANONICAL` diagnostic names in runner/review-request code.
Those diagnostics were renamed to `FORMAT_INVALID`; the original guard was not
weakened or exempted, and its focused rerun passes. The interrupted run did not
write a complete new QA record; its inherited QA counts are not new results.
The prior QA file was restored and the partial console log retained locally.

The independent integration audit also identified implementable fixed-driver,
review authentication and durable baseline bridge gaps. These are being completed
under the same owner authorization before the final full run.

## Additional operational integration

- A fixed cash/trend driver now issues exactly sized, delayed signals with stable
  slot identities, original account anchors and factory-instance verification.
  Its tests reproduce the paper evaluator's exact fees, turnover and final NAV.
- Detached review authentication binds current owner key, sealed context, approved
  deployment code, source evidence and exact issued driver/history dependencies.
  A standalone owner-only `review-approve` signer command preserves the existing
  Windows/TTY/isolation/confirmation/password protections and separate signature
  domain. It does not append a fictitious owner-log event or activate trading.
- Explicit checkpoint persistence and account bridge reconcile actual anchors,
  full FIFO profit and endpoint evidence, with atomic local writes and an external
  trusted-head compare-and-set. Repeated same-tick evidence does not advance twice;
  torn writes, mismatched heads and changed endpoint evidence refuse.
- Focused new integration, existing runner, boundary guards and complete signer
  suite: **114 PASS, 0 FAIL, 1 inherited NOT_RUN**. The skip is the real Windows
  GetConsoleMode check, unavailable on this Linux Cloud. All new cases passed.
- Read-only review found and fixed a FIFO-blocking risk in the standalone bounded
  file reader. Synthetic signing tests use only fixed test keys in temporary state.

The owner then specified an exception-day recovery deadline while explicitly
preserving all existing principal/high-watermark floors. A separate current-equity
and authentic boundary-evidence check is now implemented; historical daily loss
is not reset or compared with an artificial zero budget after recovery.

## Recovery-condition implementation

- The optional typed 22:00 KST condition checks genuine first-day or previous-zero
  days using explicit decision time, the exact boundary checkpoint and current
  marked equity. Equality with day-opening equity is permitted. Existing principal,
  peak and signed floors always apply; no floor exception or owner-schema change.
- Controller monitoring, reserve and dispatch apply the condition and retain its
  daily stop across restart. Ordinary profit/loss-day behavior is unchanged.
- Baseline schema2 records exact cutoff evidence and refuses boundary gaps or
  pre-cutoff observations used after the deadline. Legacy schema1 JSON/digests
  still restore without silently creating evidence or migrating history.
- Independent review found and corrected direct checkpoint commits which could
  lower same-day historical loss or change the opening reference. Source tests
  include self-consistent forged digests and exact same-tick redelivery.
- Focused recovery checks: **22 PASS, 0 FAIL, 0 NOT_RUN** (21 newly added cases and
  one existing recovery/equality regression). AST and whitespace checks also pass.
- Actual operator values are stored in an uncommitted private partial profile.
  Technical accounting conventions follow the supported implementation and remain
  visible for owner review. This is not a signature or an active session.

## Remaining production integration

A fixed driver, detached review verifier, checkpoint store and account bridge are
implemented. Authentic continuous account extrema, durable immutable live-history
anchors, an independently trusted head service and freshly verified owner-context
providers still need deployment-specific integration. The current full-scan account
collector does not establish continuous coverage. Missing actual approvals and
source evidence are not assumed to have been supplied.

The owner selected Windows PC and delegated market selection to independent
validation. Exceptional-day budget and recovery decisions are recorded privately,
and supported technical accounting conventions are filled for review. Actual account
bindings and a qualifying market/strategy remain unresolved. Real secret/host bindings, current effective
owner approval, qualified independent strategy evidence and the issued prepared
session are operational prerequisites. First limits signed on November2 KST cannot
take effect before November3 KST under unchanged D12. The owner confirmed there
has been no actual electronic signature yet. The owner alone performs actual
signing and activation.

Frozen research and its zero-passing result are unchanged. PR9 requires its own
merge approval. Usage telemetry is unavailable; no percentage is inferred.

## Full-run static integration correction

The complete af46688 run measured2073PASS/1FAIL/122NOT_RUN (2196 total). Its
sole failure was the macro text guard missing the new collector's read-only order
history and withdrawal-history paths. Added a file-exact collector exception that
itself invokes the strict account-route/call guard. Arbitrary neighboring URLs,
POST/DELETE/PUT, dynamic request arguments, import aliases and extracted request
functions remain rejected. Runtime endpoints and transport behavior are unchanged.

Focused cockpit/Flet/macro-harness/E1/account guards: **97 PASS, 0 FAIL, 0 NOT_RUN**,
including three new negative-control tests. Failed full output is preserved locally;
the inherited QA record was restored until the corrected full run finishes.

The Windows composition design now records actual APIs, remaining source/head/history
authority adapters, bounded loader/coordinator work and acceptance criteria. It is
explicitly a design, not a completed Windows launcher or authentic live evidence.
