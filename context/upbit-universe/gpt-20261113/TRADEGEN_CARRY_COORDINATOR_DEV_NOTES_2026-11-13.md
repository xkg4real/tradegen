# Carry-v2 Coordinator development verification — 2026-11-13

Working tree: `/workspace/tradegen-protective-carry-1113`, base `59e15cb12b822597c2296afda3649eaca3dcb3ad`.

## Final focused result

`carry-coordinator-dev6`: **11 PASS / 0 FAIL**, 39.668 seconds, 19 credential variables set to `<unset>`. The verifier reports unchanged source and unchanged protected-home metadata. Source fingerprint: `8ab8e43060cb2e2de5b82c0c15ed115eae300e9a47435f945faea397ea4df9bb`.

Evidence: `/workspace/tradegen-session/protective-carry-1113/carry-coordinator-dev6-summary.json` and corresponding `-rows.json`. Coordinator and LiveHistory retain CRLF; whitespace checks passed. This is focused development verification, not the root agent's complete regression run.

## Corrections made after the first integrated run

- Review fixture: instrument rules were observed 30 seconds after the review request, correctly causing `REVIEW_REQUEST_NOT_ELIGIBLE`. Aligning `t0 = research.now + 30 seconds` makes rule observation and review occur at `research.now`; the final execution slot is 290 seconds later and remains within the existing five-minute freshness bound.
- Quote fixture: equal bid/ask was correctly refused by the strict parser as `QUOTE_LOCKED_OR_CROSSED_BOOK`. Synthetic live books now use bid `100 + index`, ask `101 + index`, both aligned to the unchanged tick of 1. Midpoints are derived by the real parser/history path.
- Fixture performance: cache only real code-closure discovery and strict YAML parsing. Before every closure lookup, hash all current repository Python bytes plus dependency RECORD bytes; additions, removals or modifications invalidate the cache. YAML cache keys contain exact raw bytes and role, and returns are deep-copied. Approval, signature, profile, strategy, history, callback, risk and dispatch verdicts are never replaced or cached by this helper.
- Closed management: a CoordinatorError raised inside ProtectiveStore's I/O context was wrapped as `PROTECTIVE_STORE_IO_REFUSED`. The Coordinator now captures closed/confirmed facts under the exclusive verified session and checks its own fixed diagnostics after normal session exit. Closed state still causes no append and keeps the independent head unchanged; it is correctly reported as `COORDINATOR_MANAGEMENT_CLOSED`.

Earlier failures remain preserved: dev2 11/11 review refusals; dev3 4 PASS/7 FAIL from locked quotes and downstream absent history; dev5 10 PASS/1 FAIL for the closed-state diagnostic. Dev4 separately demonstrated the actual final-slot path before broadening to all 11 tests.

## Meaning of the 11 checks

The tests use actual issued research results, temporary Ed25519 signatures with current owner-code verification, actual composition, original receipt storage, independent heads, typed prior decisions, actual factory-issued callback, Runner/Controller, and DryRunAdapter. Synthetic account pages, fill history, coverage and prices are explicitly invented test data, not live source certification. The callback/assessment are not replaced with successful results.

Coverage includes final-slot LONG retention and one durable request; deadline storage failure preserving original quotes; no implicit provisioning; exact P2 binding and continued controlled-mode refusal; existing GTC late fills without a new create; legacy terminal-exit behavior; positive entry blocked at E before reserve; callback processing crossing E; delayed failing CAS preserving the final quote; closed-state head stability; and one restart with request/outbox reuse.

## Scope retained

This is a rehearsal-only fixed Upbit KRW GTC deadline bridge. It does not implement the complete pre-deadline P2 lifecycle, real held-account evidence issuer, current account/order/fill/high-water/floor reconciliation, independent management-approval issuer, or post-E live management execution. Unknown ledger references and authority remain absent. Existing late GTC fills can change holdings after E even when this code creates zero orders. No real keys, external API calls, real orders, activation or live authorization were used.
