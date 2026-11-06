# Owner preparation and process-local operations

The operator helpers fill the setup and manifest-export gaps without creating an
owner signature, arming a session, or inventing account/source review. The shipped
coordinator still refuses `controlled`: there is no production source that proves
complete held-position prices and fills over every account interval. The new
continuous-evidence mathematical adapter and synthetic tests do not establish
that missing production capability. These commands do not make a live order ready.

All development tests use invented data, temporary homes and dry adapters. Only
the owner runs the commands below in the reviewed Windows checkout. Preparatory
manifest export can precede code approval; actual runtime preparation still
requires the existing code and table approvals. They preserve the principal/high-watermark floor and all
research, account, freshness and session checks.

## One-time account and independent-head setup

Use an explicit `TRADEGEN_HOME` and a separately provisioned head directory. The
head directory must neither contain nor lie inside the state root or repository.
Keep the existing owner's key and log; do not replace them with fixture files.

Obtain a genuinely reconciled, reviewed opening `BaselineState` through the
existing account baseline bridge and retain its digest independently. The helper
does not generate or authenticate that evidence. The anchor must be at most
30 seconds old at the actual invocation. This is an in-process capture-and-setup
operation when human review cannot finish inside that interval; stale evidence
must not be relabelled with a new timestamp.

```powershell
& .\.venv\Scripts\python.exe -m tools.owner.launch setup-account `
  --state C:\tradegen-private\reviewed-anchor.json `
  --reviewed-head <independently-retained-64-character-digest> `
  --state-root C:\tradegen-state `
  --head-root C:\tradegen-heads
```

The selected `TRADEGEN_HOME` must equal `--state-root`. The helper verifies the
retained digest, seeds the checkpoint once, initializes `account-baseline` in the
independent root, and reads both back. Output explicitly leaves
`source_authenticated` and `execution_ready` false. Repeated setup refuses, even
when bytes match. If interrupted between the two writes, the second attempt also
refuses; retain both roots as evidence and use the reviewed recovery procedure.
There is no automatic repair, re-anchor, peak reset, daily-loss reset or withdrawal
adjustment.

## Export the actual driver identity before signing its review

Create the private window file with exactly `deployment_id`, `start`, and `end`.
Both timestamps must include an offset. Choose the same reviewed window that will
be used by the running program, including the existing boundary/slot constraints.
Initialize the window's empty history head before the window starts:

```powershell
& .\.venv\Scripts\python.exe -m tools.owner.launch setup-history `
  --window C:\tradegen-private\window.json `
  --state-root C:\tradegen-state --head-root C:\tradegen-heads

& .\.venv\Scripts\python.exe -m tools.owner.launch export-driver `
  --profile C:\tradegen-private\profile.json `
  --program C:\tradegen-private\program.json `
  --protocol C:\tradegen-private\protocol.json `
  --window C:\tradegen-private\window.json `
  --state-root C:\tradegen-state --head-root C:\tradegen-heads
```

`export-driver` prints the exact `FixedDriverIdentity` JSON consumed by the review
signer. Save it privately. It constructs the actual fixed driver and exact history
callbacks, binds or verifies the history journal, and needs no signed review. This
removes the circular dependency in which a manifest was needed to sign a review
but signed review was needed to obtain the manifest. It does write the existing
history binding; it is not a pure preview. Repeating export verifies the same
binding rather than resetting it. Changing the window or source produces a
different identity and requires corresponding review.

The separate full deployment manifest remains required:

```powershell
& .\.venv\Scripts\python.exe -m tools.owner.launch export-manifest --repo C:\path\TRADEGEN
```

It hashes the selected checkout and running interpreter's dependency records.
Neither manifest is a signature or a finding that the strategy passes. The owner
then follows the existing external signer workflow for final code/table approval
and the actual research/source/implementation review. No helper executes that
signer or asks for a passphrase.

## One process must retain preparation and the running coordinator

`tools.owner.launch.OwnerRuntime` accepts an actual `Coordinator` plus an optional
reviewed callback yielding `PreparationInputs` with current planner inputs and the
original selection seed. It never accepts a reconstructed `PreparedSession` or an
import string that loads arbitrary integration code. The reviewed local launcher
owns the injected account, quote, terms, history and authority sources.

`serve(runtime, stream=..., emit=...)` supplies bounded text commands for that
already composed local process. Available commands are:

| Command | Effect |
| --- | --- |
| `bootstrap` | One current account, risk and reconciliation unit; no schedule or order decision. |
| `prepare` | Runs fresh preparation using the injected current planner input callback and retains the actual issued session object; returns its ID and expiry for owner review. |
| `refresh-terms` | Performs an actual term-source read and applies only an issued, unchanged-contract renewal; does not extend the session or review expiry. |
| `run` | Starts the same coordinator once on a supervised local worker. |
| `status` | Fixed codes, timestamps and counts; no balance, account scope or credential values. |
| `stop` | Stops further strategy slots; account monitoring and explicit risk handling remain available. |
| `disarm` | Stops slots immediately and records a durable Controller kill for the actual prepared session. Reports owner-log system-disarm separately. |
| `close` | Stops slots and ends the schedule; reports whether the worker has actually finished. |

Commands that require a live process are an API/console integration, not standalone
commands that deserialize a session from disk. The standalone CLI currently
provides setup and manifest export only. Owner arming remains in the existing
separate authority flow. An injected planner, actual signed evidence and a
reviewed source composition remain necessary; absent inputs are never assumed.

Term refresh runs at monitor units when a configured term source is four minutes
old, before choosing that unit's account time. Failed refresh blocks strategy
slots and preparation while account risk observation and order reconciliation
continue. Status distinguishes term-source and account-source failures. A valid
renewal replaces current profile snapshots while keeping the same issued
`PreparedSession`; session ID, expiry, owner authority and economic/source terms
are unchanged. Changed terms require a new reviewed contract rather than an
automatic renewal. No read is restamped and no old receipt becomes current.

`disarm` sets the local stop immediately. If the unit lock remains busy beyond its
timeout (one second by default), it returns `pending: true` with both persistent
record fields false. Retry after the current unit finishes; an in-flight operation
is not forcibly cancelled. After the lock is acquired, disarm starts no network
prefetch. It uses only the last genuine frame with its original timestamp, and the
Controller can append a conservative journal kill when that frame is unavailable,
stale, or the clock is uncertain. Existing journal/owner OS-lock and durability
limits still apply to those file writes. If the system cannot also write the
owner system-disarm entry, output says `owner_disarm_recorded: false` and status
reports `COORDINATOR_DISARM_JOURNAL_ONLY`. A failed journal append is an error and
never reported as persisted. Neither stop nor disarm nor close claims that venue
orders were cancelled or positions liquidated; reconcile outstanding/unknown
orders through the existing explicit controls. EOF or an oversized command requests
closure and emits a final `console-exit` record with `closed` and `worker_running`.
Worker completion remains bounded by dependency timeouts, and `closed: false`
means it has not yet finished. The helper retains its non-daemon worker until the
dependency returns; it does not silently declare a completed shutdown.

If applying an already issued term renewal fails transiently (for example, the
Runner is still busy), the coordinator retains that exact object and retries its
application before reading another receipt. Freshness still applies. A renewal
that expires before successful application needs an explicitly reviewed restart;
the helper does not roll back the issuance registry or rewrite observation times.
Stopping strategy slots keeps same-contract term renewal available for protective
operations while monitoring continues; it never clears the stopped latch.

This software is not legal, tax or investment advice and is not a licensed adviser.
