# E2 and E3 implementation plan

Date: 2026-10-31. The owner authorized E1 through E3 development in this session. This plan follows the
[execution design](../specs/2026-10-31-e2-e3-execution-design.md). It is a work contract, not a completion record.

## Execution rules

- First finish and review the E1 implementation on the feature branch. E2/E3 can build on its reviewed commits;
  no additional intermediate merge is required for already-authorized development.
- Use disjoint file ownership for parallel implementation. The integrator alone edits shared guards,
  compliance seeds, suite registration, README and ledgers. Run tests serially with KEYLESS and temporary homes.
- No real account/venue/data call, credential read, signer use, arming, money movement or order is performed.
  Public official protocol documentation may be read. Tests patch both inquiry and trading HTTP seams.
- Keep CRLF legacy files unchanged in style, new files LF. Stage named files only. Compare staged stats with and
  without CRLF ignoring. Commit and checkpoint each reviewed task, recording actual results and any deviations.
- Preserve E1's read-only transport and guards. Every new E3 exemption is exact and has a negative control.
- No tests are weakened to meet counts or timing. Unknown private risk inputs stay unknown. No new strategy PASS
  is inferred from implementation tests. Existing per-PR merge approval and owner-only setup remain separate.

## E2-1: value types, durable lifecycle and reservations

Owner: lifecycle builder. Files: `execution_control/model.py`, `store.py`, package marker, and focused store tests.

- Implement the design's frozen order/rule/fill/risk roles and canonical decimal digests. Reject bools, floats,
  nonfinite numbers, unknown fields, malformed IDs and unsupported enums.
- Implement checked paths, exclusive lock, journal hash chain, fsync, version/sequence checks and transition replay.
- Enforce never-reused client IDs, exact order identity, persistent reservations and conservative restart handling.
- Build transaction operations usable by the controller without releasing the lock between read and commit.
- Verify cross-thread/process exclusion with temporary files, concurrent oversubscription, idempotent duplicate,
  contradictory duplicate, torn tail, truncation/anchor mismatch, linked targets and every restart window.

Review boundary: no transport or credentials; reservation expiry is allowed only before dispatch. `UNKNOWN` and
`DISPATCHING` never expire into free cash or free units.

## E2-2: accounting, risk, session confirmation and controller

Owner: control builder, after E2-1 interface agreement. Files: `risk.py`, `session.py`, `controller.py`, `dry_run.py`
and focused accounting/control tests. Coordinate shared model additions with E2-1 rather than editing concurrently.

- Implement deterministic realized-profit accounting, fee allocation, duplicate-fill handling and incomplete-input
  refusal. Persist day-opening equity and lifetime peak; restart does not create another first day.
- Implement the supplied policy branches and effective-floor transitions. Keep target diagnostics independent of
  admission and size. Do not silently select first-day loss tolerance or signed-limit exceptions.
- Run the actual odds engine with a fresh comparison ID before session activation. Bind its evidence, selected
  plan, policy, instrument rules, state and code into the content-derived ID the owner signs. Refusals and stale
  data do not prepare a session; the input label itself is not an armable preparation.
- Atomically build reservations; load contexts only through owner; issue and verify gate permits; bind exact wire
  order and permit digests; mint/consume one dispatch capability; persist before side effects.
- Implement dry-run acknowledgment, partial/final fills, rejection, timeout and reconciliation. Acknowledgment
  changes order state but never manufactures a fill or realized profit.
- Implement local kill latch plus safe system event append. Test H2 server-clock/day-boundary disagreement and
  append failure. Preserve qualified exits and known-order cancellation; unknown holdings require manual handling.
- Verify duplicate dispatch, float-interface cap boundaries, stale owner/code/session/day, racing cash/sells, target
  misses, first/zero/negative day cases, discontinuous peak-floor relaxation, corrupt-state recovery and kill exits.
- Verify aggregate fee-inclusive session capital from exact held exposure and all active buy reservations. External
  gate reservations/promised sells require manual reconciliation; internal sell promises share crypto base units
  across quote pairs. Require complete cumulative fill identity, fee and supplied average-price agreement.

Review boundary: no real arming entry is written, no caller can supply an unissued Context/Permit/capability, and
E2 has no hidden live transport fallback.

## E2-3: integration and mock acceptance

Owner: root integrator.

- Add both new packages to runtime scans, owner/signer hash seeds and closure tests in lockstep. Check owner key
  presence before changing the closure; record any required re-signing as an owner action.
- Register focused suites using the repository's existing function-test convention. Keep read-only inquiry tests.
- Add narrow new-package guards with negative controls for arbitrary URL/method/endpoint, alternate HTTP, dynamic
  import, secret logging, direct owner-only writes and transfer/withdrawal routes.
- Run E1 and E2 integration tests plus compliance and odds regressions. Inspect every FAIL and NOT_RUN. Review
  source against the design's state-machine and capability requirements before E3 relies on them.

## E3-1: Upbit codec and authenticated transport

Owner: venue builder. Files: `execution_orders/model.py`, `transport.py`, `upbit.py`, package marker and tests.

- Verify official create/cancel/status contracts and authentication rules; record URL, date and exact GitHub blob
  SHA where available. Restrict initial products/order type as specified.
- Implement strict pure request builders/parsers and exact ordered query/body signing. Keep full requests free of
  credentials until after endpoint and one-use capability validation. Use repr-safe typed credential providers.
- Add single bounded HTTP seam, fixed host, TLS verification, disabled redirects/proxies and no effectful retries.
- Test independent golden HMAC/JWT fixtures, Unicode/escaping/order sensitivity, extra fields, altered request,
  duplicate identifier, malformed success, mismatched identity, partial fill, cancel race and unknown response.
- Integrate controller dispatch and reconciliation with mocked HTTP. Assert no real seam invocation.

## E3-2: KIS KRX and US adapters

Owner: venue builder. Add `execution_orders/kis.py` and focused tests.

- Use current official cash TRs and exact uppercase payload contracts, preserving string quantity/price. Restrict
  KRX and NASD/NYSE/AMEX cash long orders; no borrowed/credit quantity, derivatives or other foreign venues.
- Verify cancel/status/TR/hash-header contracts from official sources. Preserve broker branch/order identity.
- Require reconciled available cash plus costs and independently established no-credit state. Do not infer these
  from the cash endpoint name or a broker's permissive buying-power response.
- Do not invent KIS server idempotency. A lost POST response remains UNKNOWN until uniquely reconciled.
- Bind authoritative venue-local trade date and branch to KIS order/fill identity. Single complete-page status is
  the supported subset; pagination and unverified US terminal cancellation remain UNKNOWN with reservations held.
- Test TR/side/market mismatches, account-field suppression, unsigned-context refusal, fractional shares, tick and
  band limits, canceled-but-filled responses, ambiguous matching and unknown outcome with retained reservations.

## E3-3: OKX cash-spot adapter

Owner: venue builder. Add `execution_orders/okx.py` and focused tests.

- Pin place/cancel/status fields, regional host applicability, byte-exact HMAC signing and client-ID constraints.
- Require cash spot configuration with no auto-loan, current grey-session acknowledgment and capped exposure.
- Refuse margin, derivatives, position-side/leverage extras, algorithmic/batch routes and automatic cap relaxation.
- Parse both top-level and per-order status, verify identities, preserve unknown outcomes and reconcile partials.
- Test auto-off/date behavior, cap rounding, stale config, response row failures under HTTP success, request path
  query signing, ID reuse, unexpected fields, cancel races and timeout retention.

## E3-4: end-to-end validation and handoff

Owner: root integrator, with an independent reviewer.

- Run complete mocked prepare/session/reserve/dispatch/reconcile/fill/stop/exit scenarios for Upbit, KIS KRX,
  KIS US and OKX in `tests/orders_lifecycle.py`, through the authenticated adapter with mocked HTTP. Use actual
  fresh-odds preparation and temporary signed owner state; pure-codec tests alone do not fulfill this step.
- Compare the implemented subset and every unsupported route with the design and verified official evidence.
- Run all applicable E1, E2, E3, compliance and odds suites serially, then one full regression run. Include exact
  commands/counts/timing, source SHA, guards, side-effect probes and owner-only limitations in the ledger.
- Update README with the actual state and a clear distinction between mock-tested adapters and live readiness.
  Keep private risk parameters out of public examples. Prepare safe owner setup/run instructions without secrets.
- Push reviewed feature commits, create a reviewable PR for the plan, attach it to the task and update Claude's
  handoff. Do not merge a new PR under the earlier approval for PR #4/#5.

Completion requires all supported paths implemented and offline-tested, no unexplained failures, and honest
documentation of account setup and live validation still pending. A missing route or unresolved production input
is listed explicitly; it is not converted to a successful trade or a skipped test counted as PASS.
