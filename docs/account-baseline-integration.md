# Durable baseline and account reconciliation

`execution_accounts.baseline_bridge` connects the pure reducer to actual
`AccountBundle` reconciliation, and `baseline_store` saves exact private state.
`ContinuousAccountProvider` implements the callable account-provider interface
used by the existing controller and runner. It does not collect market data,
authenticate a source, select owner policy, sign approval or grant execution.

## Explicit setup and integration

1. Select the reviewed baseline conventions and a complete account-history
   origin with zero opening inventory. The supported route is one KRW-settled
   account, `maximum_net_equity_loss_from_day_open`, and `no_external_flows`.
   The cumulative realized net P&L counter starts at this same history origin;
   an arbitrary offset is unsupported. The first trading day is the reviewed
   actual date, never the process start date. The day-opening value, historical
   peak and observed loss require their own reviewed history.
2. Obtain authenticated, complete `AccountEvidence` at the anchor cut-off. Set
   `anchor.baseline.source_sha256 = content_digest(accounts)` for the exact tuple
   of records. Call `initialize_account_baseline(conventions, anchor, accounts,
   now=observed_now)`. It reconciles the real balance, cumulative FIFO P&L,
   current/prior-day P&L and cut-off before returning a `BaselineUpdate`.
   It uses the actual initialized baseline; there is no provisional permissive
   baseline or circular readiness check.
3. Independently review and retain that resulting `state.state_digest` as the
   trusted initial head. Select one explicit absolute private `TRADEGEN_HOME`,
   already created by the operator's provisioning process. Construct
   `CheckpointStore(root=selected_root)` and explicitly call
   `store.seed(update.state, expected_head=reviewed_head)` once. Existing state
   refuses reseeding. Normal provider calls never initialize missing state.
4. Implement an authenticated interval source callable
   `source(previous_state, now) -> BaselineFrame(interval, accounts)` and a
   separately trusted durable head adapter exposing `read() -> digest` and
   `compare_and_set(previous_digest, new_digest) -> bool`. Exact `True` means
   that the external compare-and-set durably succeeded. These adapters are
   trusted application code, not a sandbox or an authorization substitute.
   The shipped source is `execution_launch/account_interval.py`
   `UpbitIntervalSource`: `collect(...)` runs one fenced `collect_upbit`
   capture before the tick time is chosen and stages one frame, and
   `__call__(previous, now)` returns it without I/O. It is flat-only: a held
   position, any fill at or after the previous endpoint or any external flow
   refuses, so the chain stops after a first fill until a reviewed
   intra-interval price-path source exists (owner open item). It brackets the
   22:00 and Seoul-midnight boundaries only with a capture that reads the
   balance at or before the boundary and finishes at or after it, and never
   relabels a late capture.
5. Construct `ContinuousAccountProvider(source=source, store=store,
   trusted_head=head_adapter)` and supply it where the controller/runner expects
   `account_provider`. Each successful new interval is reconciled, saved,
   committed to the external head and read back before an observation returns.
   All separate code approval, risk policy, credentials and execution gates
   remain required by their existing contracts.

The initializer and bridge are pure: they do not fetch records, create files or
advance the trusted head. The store writes only after explicit seed/commit.
The lower-level `CheckpointStore.seed` verifies structure/integrity and trusts
the externally reviewed head; integrations must use the account initializer
above to establish the balance/P&L reconciliation rather than treating a local
hash as evidence of review.

## Continuous source and runner timing

An interval covers all account activity in `[start, end)`. Its snapshot is just
before events timestamped exactly at `end`; the bridge refuses fills/flows at
that endpoint. Source history and totals must keep the same complete origin.
`interval.source_sha256` must equal `content_digest(accounts)`. Its separate
`coverage_sha256` identifies the authenticated coverage/extrema evidence.
Both hashes are integrity bindings, **not source authentication**.

The source must establish complete equity maxima and minima for every interval,
including between snapshots. Periodic account polls alone do not establish
these extrema. Source coverage gaps, missing gross-flow coverage, sequence/time
rollback, unsupported external flows, stale evidence and inconsistent balances
or realized totals refuse. The bridge independently rejects account-history
flows inside an interval claiming zero flows. A new Seoul day requires an exact
midnight opening sample, with the prior day's realized P&L reconciled from fills.
See [the reducer contract](account-baseline-contract.md) for exact semantics.

Fetch/validate required source records before choosing the runner tick's `now`;
the provider must consume that already collected frame. Do not start HTTP work
after the fixed tick time, rewrite source receipt times or mark old data fresh.
Runner observe, reserve and dispatch may call the same provider several times
with the same `now`. If that exact interval is already committed, the source
must redeliver the **identical interval and account evidence**. The reducer
accepts identical redelivery without increasing sequence or changing the
timestamp; the provider performs no second save/CAS. A new interval with an
equal endpoint, or changed account evidence with the old interval, refuses.
The provider does not cache account evidence or hide later source changes.
Sources must retain the latest exact frame across process restarts; the store
retains its digest, not the complete source frame.

If the reviewed risk policy enables recovery by 22:00 Seoul time, select the
matching `BaselineConventions.recovery_cutoff_seconds=79200` before initializing
the source state. The source must additionally capture the exact boundary on
first trading days and days following zero realized net profit. Its genuine
endpoint proof is reconciled into `RiskBaseline.recovery_checkpoint` and
`RiskObservation.recovery_checkpoint`, durably retained for that day, and never
replaced by later recovery. Pre-boundary evidence cannot be reused after the
deadline, even inside the normal freshness window. A late anchor without proof
remains unknown. This option uses schema 2; existing schema 1 checkpoints keep
their original hashes and are never automatically migrated or reset. See the
[boundary contract](account-baseline-contract.md#optional-recovery-boundary).

The no-flow choice is deliberate: the existing controller retains a monotone
raw-equity high-water mark and a fixed daily opening. A general deposit or
withdrawal adjustment would require a jointly reviewed change to those
contracts. This implementation does not silently change those meanings.

## Files, durability and refusal recovery

The only state files are under the selected root's `execution-baseline/`:
`checkpoint.json`, `checkpoint.tmp`, and `checkpoint.lock`. Root selection must
match `state_root()` exactly. Existing path isolation, symlink/junction checks,
bounded regular files, no hardlinks, descriptor checks and platform locking
apply. New files use mode `0600` and the new directory uses `0700` where the
platform enforces POSIX modes; platform access controls still require normal
operator provisioning. No arbitrary filename or automatic directory traversal
is accepted. Loading existing state opens the existing lock for locking only;
it does not create a missing lock or state directory.

Writes validate exact serialization, exclusively create the fixed temporary
file, flush/fsync it, atomically replace the checkpoint and fsync the directory
on POSIX. There is no claim of directory-fsync durability on Windows or of
protection from hostile code controlling both files and external head.
An unexpected temporary file, malformed/oversized record or linked path refuses;
the store does not erase evidence or automatically repair it.

Local replacement and external head CAS are two separate durable operations.
Failure between them can leave a new local file with the old external head.
No observation is returned; the next read refuses the mismatch before requesting
another source interval. Operators must compare independently retained heads
and authenticated source evidence, reconcile any in-flight activity, and carry
out a reviewed recovery. Never fix this by blindly copying a local digest to
the trusted head, deleting the store or resetting the first trading day. A
local checkpoint alone does not prevent rollback; an externally retained latest
head is an explicit operational prerequisite. A failed final head read or a
concurrent head change likewise returns no observation.

The shipped head is `execution_launch/baseline_head.py`:
`BaselineHead(root=head_root, name="baseline-head", chain=CheckpointChain(store))`.
It keeps one record, `{"baseline_sequence":n,"head":"<digest>","schema_version":1}`,
under `<head_root>/baseline-head/` with its own OS byte lock, fsync and atomic
replace. The root is provisioned by the operator (an existing, link-free folder on
a drive letter, outside OneDrive, that neither contains nor lies inside
`TRADEGEN_HOME` or the checkout; `%LOCALAPPDATA%\TRADEGEN-head` is recommended)
and is re-checked on every operation; the code never creates it or changes its
permissions. `compare_and_set(old, new)` returns True only after the store
durably holds `new` as the committed direct successor of `old` with the next
sequence and the record is fsynced and replaced; it returns False when the head
has moved, and raises a fixed `HEAD_*` code otherwise. The record holds no
amounts or identifiers.

Setup order: `initialize_account_baseline`, `store.seed(state, expected_head=d)`,
then once `head.initialize_reviewed_head(d)` with the digest the operator retained
from the reviewed anchor output; the head adopts only a seed-shaped checkpoint and
refuses an advanced store, an existing record or a store that is not yet seeded.
There is no runtime caller of initialization.

Honest limits. A rollback of either root alone, a crash between the two replaces,
a mutated or truncated record, a hard link or junction, a second process and a
reset-valued successor all refuse. A coherent rollback of both roots (one backup
restored over both) is not detected by the files themselves: no frame is retained
durably in this phase, so it is refused only when it is old, by the 30 s rules
(`advance_baseline` maximum interval, `risk_baseline` freshness) and by the fixed
driver's 30 s account-anchor rule; a coherent rollback younger than 30 s followed
by a fresh honest interval is indistinguishable from an ordinary tick. Code running
as the same Windows user can rewrite both roots; that boundary is unchanged.

Recovery after any refusal (owner-performed; the code adopts nothing): stop the
runner; copy both roots to an evidence folder without editing them; note the head
record or its `HEAD_*` code and the checkpoint's digest and sequence; reconcile
outstanding orders with the venue; classify the case (checkpoint is the direct
successor of the head, checkpoint older or unrelated, `head.tmp` present, record
invalid); then move `<TRADEGEN_HOME>/execution-baseline` and
`<head_root>/baseline-head` aside as evidence and re-anchor with a new reviewed
anchor, `store.seed`, `initialize_reviewed_head` and fresh session preparation.
A same-day re-anchor after the cutoff carries no recovery proof, so
recovery-dependent permission stays blocked until the next Seoul day.

The files contain private account amounts and identifiers. Do not commit them,
attach them to public handoffs or copy them into user-facing reports. Tests use
invented records and temporary roots only. No autonomous continuous source is
shipped by this integration; the trusted head above is a local record, not a
service.

This software and document are not legal, tax or investment advice, and their
authors do not act as licensed advisers.
