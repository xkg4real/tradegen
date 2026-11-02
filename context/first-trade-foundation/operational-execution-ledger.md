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

## Remaining production integration

A fixed reviewed order-generating driver, authenticated source/implementation
review adapters, continuous complete account extrema and trusted durable baseline
storage still need deployment-specific integration. The current full-scan account
collector does not establish that continuous coverage. Missing owner choices are
explicit inputs; they are not assumed to have been supplied or signed.

The actual deployment, venue/market, exceptional-day budgets and loss-accounting
conventions remain to be confirmed. Real secret/host bindings, current effective
owner approval, qualified independent strategy evidence and the issued prepared
session are operational prerequisites. First limits signed on November2 KST cannot
take effect before November3 KST under unchanged D12. Existing effective limits
are unknown. The owner alone performs actual signing and activation.

Frozen research and its zero-passing result are unchanged. PR9 requires its own
merge approval. Usage telemetry is unavailable; no percentage is inferred.
