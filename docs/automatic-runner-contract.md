# Automatic runner contract

`execution_launch.runner` implements a synchronous orchestration boundary. It is
not an activated service. Importing it starts nothing, and the default `observe`
mode never invokes a Controller, changes owner/control state, reserves an order,
or sends one. The launch CLI exposes offline checks. Rehearsal is an explicit
Python integration and test mode.

## Explicit dependencies and modes

The caller supplies the launch profile, quote provider, complete reconciled
account provider, strategy implementation, prospective validation evidence and
trusted review verifiers. Time is an explicit aware `datetime`. No provider,
credential loader, wall clock, timer, background thread or trading adapter is
selected automatically.

- `observe`: inspect supplied observations and return diagnostics. Providers and
  strategy callbacks are injected trusted code; they must themselves honor the
  caller's intended read-only boundary.
- `rehearsal`: invoke the existing Controller with exact `DryRunAdapter` objects
  and an explicitly selected state directory outside the normal owner home.
  Synthetic signatures in temporary test fixtures exercise E2; rehearsal never
  turns test receipts into genuine owner approval.
- `controlled`: future owner-operated integration, selected explicitly in Python.
  It requires a supplied Controller and the actual process-issued E2 prepared
  session. This implementation work never selects real credentials, activates a
  real session, or submits a real order.

The same account-provider callable must be installed in the runner and Controller.
The Controller fetches and validates current account evidence again at reservation
and dispatch. A runner observation cannot override that final decision.

## Research, implementation and owner binding

`EvidencePackage` contains the actual result issued by the prospective evaluator,
its frozen protocol and an explicit source-review verifier. Retrospective results,
missing/unknown evidence, expired evidence and an unverified source review block
entries. Current historical research has **zero passing strategies** and does not
qualify. A fabricated `eligible=True` object cannot replace evaluator output.

`program_digest(StrategyDriver)` binds the source/package artifact hash and its
canonical fixed parameter object. This is the profile/protocol's
`strategy_code_sha256`. Parameters use decimal strings rather than JSON floating
point, and the callback receives that same canonical parameter string. The
additional implementation verifier receives both the binding and actual driver.
Its typed receipt must bind the same callback object, program, protocol, evidence,
profile and economic rules, plus review time/expiry and audit reference.

These verifiers are **audited external trust boundaries**, not authentication
provided by matching hashes. Their operator must verify original prospective
capture and registration, trial independence, source authenticity and that the
actual implementation/parameters generated the studied decisions. There is no
default successful verifier. Arbitrary Python callbacks are not sandboxed; a
receipt manufactured by the same untrusted caller is not real review.

The current evaluator is scoped to KRW Upbit spot. Research starting cash must
equal the profile's original principal, and selected session stake cannot exceed
that evaluated capital. This prevents large-capital studies from silently
standing in for a small account where lots, minimum orders and fees differ. Live
equity may change after profits; E2 still checks current reconciled cash,
holdings, principal/floor, signed limits and aggregate prepared stake.

Stable profile/rule digests omit only the rules observation timestamp. Every
economic term, source reference, owner policy, strategy identity and account
scope remains bound. The full current rules and profile digests remain bound to
the actual prepared session and must satisfy E2's freshness checks.

`prepare_launch_session(...)` recomputes these bindings, verifies qualification,
selected-plan scope and capital, then invokes existing fresh-odds preparation.
It writes the existing preparation event and never signs or arms a session. Its
derived label is `L` plus the first 31 URL-safe base64 characters of the binding's
SHA-256 hash: 186 retained bits (approximately 93-bit generic birthday collision
strength). Complete digests remain in `LaunchSession` metadata and are recomputed
on entry. The returned E2 session ID includes E2's additional full content digest.

The owner must review/sign/arm that exact returned ID afterward. The runner passes
the actual `launch_session.prepared.session_id`; a reconstructed dataclass cannot
replace the registered runtime object. The Controller retains final owner,
session, risk, conduct, account, instrument and capability checks.

## Tick, restart and protection

Each `tick(now=...)` first reconciles existing durable active orders in effectful
modes, then invokes the independent risk monitor. Runner-owned reservations left
without a send are cancelled locally; they are not dispatched during recovery.
An uncertain create outcome is queried by status and is never retried. Unknown,
open, partial and cancel-pending reservations remain outstanding until E2 verifies
authoritative identity, quantity and fill/fee evidence.

A stable signal key and profile contract derive the client ID. Repeated decisions
return the existing state; changing economics under the same key refuses. New
entries wait while any order remains active. Reservation and the pre-send journal
transition occur before the Controller's single create attempt. This provides
at-most-once dispatch per client ID, not a claim of guaranteed exchange delivery.
Signal keys must remain stable across process restarts; inventing a new key for an
old decision defeats application-level deduplication and violates this contract.

Quotes require exact positive ordered bid/ask, matching instrument and at most
10 seconds of age. Accounts require at most 30 seconds of age, known external
flows and complete accounting; E2 performs the more detailed validation again.
Clock rollback blocks work. Exceptions become fixed diagnostic codes without
provider/account response text. An unexpected effectful dependency failure stops
the runner; a new instance still reconciles durable state first.

The risk monitor preserves persistent daily stop and floor/halt behavior. It
reports when protective action is needed; it does not invent a liquidation policy
or promise loss floors will survive gaps, fees or slippage. Explicit `cancel` and
verified `submit_exit` remain available after stop or research expiry, subject to
the existing Controller's conduct, holdings, freshness and reconciliation rules.
A cancel acknowledgment does not release the reservation as a completed cancel.

`stop()` prevents subsequent ticks and checks again before dispatch; it is not a
broker cancellation. An already submitted request can still complete. `run()`
accepts an external iterable of timestamps, requires a finite step bound, checks
an optional stop predicate and starts no worker. A blocking external iterator must
provide its own cancellation. Restarting Python requires fresh session preparation
before new entries; status reconciliation and qualified exits remain available.

`Controller.states()` uses `Journal.snapshot()` to read an existing journal under
its existing lock. Missing, partial and corrupt state refuses. Snapshot never
creates state files, rewrites a checkpoint, or repairs a journal.

## Offline verification

`tests/launch_runner.py` uses invented future paper data, synthetic review receipts,
temporary test-signed homes and DryRunAdapters. It covers observation without
state creation, owner/runtime-object binding, one create per decision, uncertain
send recovery, reserved-crash cancellation, partial fills/cancel acknowledgments,
research-independent exits, stale data/refused reviews, isolation, bounded stop
behavior and non-mutating durable-state reads. It establishes orchestration
behavior only; it supplies no genuine account/source evidence or live approval.
