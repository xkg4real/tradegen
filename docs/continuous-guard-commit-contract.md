# Chronological held-position guard: reducer and commit contract

`execution_launch.continuous_guard` implements a **pure reduction plan**.
It does not authenticate a live source or owner, write a journal, update a
baseline, arm a session, or place an order. `GuardPlan.execution_ready` is always
false. The existing continuous candidate source retains its unconditional
`CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED` refusal.

This document separates the implemented mathematics from the persistence and
authority contract that a later production adapter must satisfy.
`execution_launch.continuous_guard_commit` now supplies the local durable
transaction (two new controller journal kinds, a guard checkpoint store behind a
separately retained head, and a restart classifier); see "Implemented commit
unit" below. No production adapter or source-completeness verifier is supplied.

## Implemented inputs and reduction

- `GuardAnchor` is an explicit reviewed controller checkpoint. It includes the
  current applied floor, retained high-watermark, daily stop, permanent halt and
  controller-journal head. It is not inferred from a current balance or a
  profile's original floor. The candidate initializer rejects missing required
  halt/daily-stop history and an unapplied floor.
- `GuardCheckpoint` embeds the exact baseline checkpoint, retains the stricter
  controller floor/high-watermark/latches, and binds the owner head, policy and
  code epoch. It also carries the last stream epoch/watermark sequence and
  observation time. A new epoch, cross-interval sequence gap or backward receipt
  time refuses. Its digest detects changed content; it is not an independent
  trust anchor or signature.
- `OwnerContextClaim` contains a pre-interval or post-interval observation of the
  effective signed floor/daily limit, code approval and owner head. This is a
  claim to authenticate elsewhere, not a verifier-issued capability. The
  pre-interval claim must already exist before collection starts; the final claim
  must cover source verification. Head, code and effective limits must agree.
  Comparing heads alone would miss scheduled limits that become effective at
  midnight. A genuine change requires an authenticated timeline; this reducer
  refuses rather than guessing that timeline.
- The reducer accepts raw `ContinuousPath` events, full historical/interval FIFO
  inputs, normalized captured and endpoint account evidence, and a precisely
  bound source-coverage receipt. It recomputes the valuation points, reconciles
  the endpoint through the existing baseline bridge, and checks the proposed
  interval's extrema, source digest and coverage digest. A preview's public
  dataclass or precomputed point array is not accepted as proof.

Opening cash, units and the complete historical/interval fill lists are derived
from the reconciled account evidence and exactly compared with the submitted
valuation inputs. Closing cash, units and marks are compared component by
component as well. Equal aggregate equity is insufficient: replacing one coin
with half a coin plus cash can hide half of an intrainterval loss while leaving
the endpoint value unchanged.

The original captured snapshot is separately reconciled without inventing a
later risk baseline. Captured-to-endpoint reconstruction may change only the
documented boundary timestamps and path-derived prices; balances, units, order,
fill and flow history remain identical. The original capture must bracket the
endpoint and finish no later than source verification. Its first-receipt time
is a claim here and must be authenticated against the original manifest-bound
receipt by the production verifier; this module does not turn that timestamp
into proof by accepting its shape.

Every mark/fill is processed in source sequence order, including equal-time
events. Each point uses the existing risk evaluator, the current day's opening
equity, running daily maximum loss, lifetime FIFO realized profit, prior day's
profit and current effective floor. The signed daily limit is also enforced.

The floor is ratcheted forward at every point and never relaxed by this reducer.
For example, with normalized values `100 → 109 → 110 → 108 → 115`, reaching a
drawdown-activation threshold at `110` must not silently lower a previously
applied floor of `109`. A later reviewed D12 relaxation remains a separate
controller operation; neither a date change nor a new candidate applies it.

A floor breach produces a required permanent-halt record and preserves that
latch through recovery, later intervals and midnight. Daily stops persist for
their day. At midnight the old-day closing left limit is evaluated **before**
daily counters reset; the old-day required record remains in the plan. The new
day's opening is then evaluated separately. Lifetime peak, applied floor and
permanent halt do not reset. The 22:00 recovery check uses the verified boundary
value and the existing recovery convention.

`GuardPoint.source_at` and `policy_day` describe the historical event.
`RequiredGuardRecord.recorded_at` is the current observation time. For the
midnight left limit, `boundary_side="left"` explicitly distinguishes the old-day
value from the new opening at the same boundary. The internal old-day evaluation
instant is a mathematical left-limit convention; it is not a backdated network
capture or journal timestamp.

An identical input replay is idempotent and does not emit duplicate required
records. It does not refresh evidence timestamps. Changed proof/account/interval
inputs under an old path are refused. A missing checkpoint, changed owner/code
epoch or inconsistent baseline is not repaired by constructing a new anchor.

## Production authentication still required

Before any `GuardPlan` may affect live state, an adapter must:

1. Authenticate raw market/account receipts and the opening-to-closing event
   coverage under an actual reviewed venue contract. The current Upbit sampled
   feed has not established that contract. A local hash, contiguous local
   counter, heartbeat, test verifier or JSON `complete` field is insufficient.
2. Re-run source verification over the exact raw evidence, or consume a genuinely
   verifier-issued, issuer-bound, process-valid token. A publicly constructible
   `VerifiedCoverage`, `ContinuousIntervalPreview` or `GuardPlan` is not such a
   token. It must not be promotable through a caller boolean or copied digest.
3. Authenticate the pre-interval owner/code/limit checkpoint and the final owner
   context. Preserve the actual owner-head history and prove stability through
   the interval and commit, or provide a complete authenticated transition
   timeline. This pure reducer currently supports only the unchanged case.
4. Fold the actual controller journal and match its current floor, high-watermark,
   daily stop and permanent halt with the guard's expected predecessor. Prevent
   concurrent policy/floor transitions from racing the plan. An owner-head check
   alone does not freeze controller state or the files whose code is approved.
5. Compare the separately retained baseline and guard heads with the expected
   predecessors. Adjacent state files and matching self-computed hashes are not
   independent head authority.

The existing account provider's baseline history and the controller's floor
history are separate. Production observations must carry the guard's retained
floor/peak/latches into the controller; publishing only the reduced baseline's
endpoint would discard precisely the history this guard preserves.

## Required durable ordering

`continuous_guard_commit.commit_continuous_guard` implements this ordering as a
local library transaction. Package authentication (step 1) and publishing to the
controller (step 5) are still not implemented; it is not a production adapter:

1. Authenticate and freeze one evidence package and owner/control context. Under
   the reviewed lock/CAS protocol, verify expected guard, baseline and controller
   predecessors. Recompute the plan; do not deserialize it as authority.
2. Append a new `continuous_guard_prepare` record at the **current receipt time**.
   Bind the full evidence digest, owner/control proofs, path bounds, old/new
   guard digests, old/new baseline digests and transaction identifier. Any pending
   preparation must block new entries after a crash or restart.
3. Persist every required safety effect before committing or publishing the
   endpoint. A floor breach requires the existing durable local `halt` latch;
   failure to append an owner-log `system_halt` must not clear that local halt.
   Old-day daily stops and historical point summaries require explicitly defined
   new records carrying `source_at` and `policy_day`. Existing `risk_snapshot`
   requires its receipt day's semantics and must not be backdated or reused for
   historical points from a previous day.
4. Commit the baseline checkpoint and advance its separately retained head by
   compare-and-set. A refusal leaves a pending guard transaction and no published
   live observation.
5. Commit the guard checkpoint and advance its separately retained head by
   compare-and-set, then persist the completion record. Publish the account
   observation only after all durable state and controller effects agree.

The prepare record must precede any potentially partial sequence of safety
writes. A crash after preparation but before its required halt is persisted is
still a blocked pending transaction; the next process must not place an order
while treating the halt as absent.

| Durable state found on restart | Required result |
| --- | --- |
| Both old heads and no prepare record | Ordinary fresh evidence collection; no adoption of unrelated candidate files |
| Prepare exists, both heads old | Pending guard-before-baseline recovery; no new entries |
| Baseline advanced, guard head old | Pending cross-store completion; no new entries or reseeding |
| Guard advanced, baseline head old | Divergence; refuse and review the evidence/transaction |
| Both advanced, completion absent | Pending finalization; require the exact authenticated package and transaction proof |
| Both advanced, matching completion and all required effects | Consistent committed state, subject to current owner/session/source checks |
| Any missing, conflicting or unknown head/proof | Refuse; never infer the expected head from the current balance or local file |

Recovery must replay the same authenticated package and required effects
idempotently. It must preserve permanent halts. A reviewed re-anchor cannot
silently erase a floor breach, lower the ratcheted floor or hide an old-day
daily stop. Neither unit provides automatic recovery or a reset command; the
commit unit only resumes a pending transaction when the same package is re-run.

## Implemented commit unit

`execution_launch.continuous_guard_commit` (synthetic tests in
`tests/control_continuous_guard_commit.py`):

- Journal kinds `continuous_guard_prepare` and `continuous_guard_complete`.
  Existing kinds and their validation are unchanged.
- `GuardCheckpointStore` keeps the guard checkpoint below
  `TRADEGEN_HOME/execution-guard`. It uses the baseline store's path, lock,
  temporary-file, fsync and replace rules. Only the record codec and the transition
  rules are its own: no peak or floor rollback and no cleared halt. `GuardChain`
  places that store behind its own `BaselineHead` record, which advances only by
  compare-and-set.
- `commit_continuous_guard` holds the control journal transaction throughout.
  Inside it, the function:
  1. classifies the durable state;
  2. recomputes the plan from the package;
  3. requires the caller's expected guard, baseline and controller heads;
  4. appends the prepare record at the current receipt time. The record binds the
     evidence (input) digest, owner digest, controller head, path digest and
     bounds, old/new guard and baseline digests, the transaction id, whether a halt
     is required, and the plan's required records with `source_at` and
     `policy_day`;
  5. appends the existing `halt` kind, if the proposed checkpoint is permanently
     halted and no halt row exists;
  6. commits the baseline and advances its head by compare-and-set;
  7. commits the guard and advances its head by compare-and-set;
  8. appends the completion record;
  9. returns a receipt only after both heads are re-read.

  A guard state that would omit an existing local halt is refused. The halt is
  never cleared or duplicated.
- `classify_restart` is a pure function implementing the table above. Every
  pending, divergent or refused result, and any local halt, reports
  `new_entries_blocked=True`.
- Re-running the same package after a crash at any step converges without
  duplicate prepare, halt or completion rows. A store replaced before its head
  advanced is finished only for the exact successor bound by the prepare record. A
  different package under a pending prepare refuses.
- Lock order is the same as `Controller.observe`: journal, then head, then
  checkpoint store. The journal is never entered again.

Still required:

- A production adapter: authenticated source, owner and controller context, a
  trusted clock, and publication of the account observation.
- A venue completeness authority for the coverage receipt.
- An authenticated owner-head timeline; only the unchanged case is supported.
- Controller support for the new kinds. `execution_control.controller._fold`
  currently refuses any journal containing them. That fails closed, but it also
  blocks cancellation and reconciliation until defined.
- An owner-log `system_halt` append, plus controller-consumed records for old-day
  daily stops and historical points.
- The private package archive and the reviewed re-anchor procedure.

The candidate archive from `execution_launch.continuous_archive` stores only the path.
A future durable guard package must additionally retain the original account
receipts/manifest, authenticated coverage receipt, owner/control evidence and
plan/commit bindings in private storage. Candidate JSON alone is insufficient
for restart authentication. Credentials and authentication headers must never
be added to such an archive.

## Validation scope

Synthetic tests cover the hidden `100 → 110 → 105 → 115` floor breach, same-time
event ordering, threshold-crossing floor ratchets, continued permanent halts,
daily-limit breaches before midnight, exact 22:00 recovery, changed owner epochs
or effective limits, source/endpoint and cash/inventory/FIFO component binding,
raw event replay, stream/receipt continuity, duplicate input handling and ambient
Decimal precision. These tests validate arithmetic and
refusal contracts. Commit tests use temporary roots only. They cover:

- durable ordering;
- a crash after each step, followed by idempotent replay;
- divergence;
- compare-and-set refusal;
- halt preservation;
- mismatched packages and unknown heads;
- refusal of a re-entrant journal.

None of these tests validate an actual venue completeness authority, owner
signature, live Windows timing or a production adapter.

This is an engineering record, not legal, tax or investment advice. The author
is not a licensed adviser.
