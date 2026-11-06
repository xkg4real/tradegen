# Standalone owner rehearsal

Run this only in the reviewed Windows environment. This command reads a real
account through the existing read-only E1 GET routes when the owner starts a
console operation, and uses exact `DryRunAdapter` instances for every order path.
It has no live switch, order credential loader, signing command or arming command.
Development tests substitute invented receipts and fixture signatures and never
read credentials or call a venue.

```powershell
& .\.venv\Scripts\python.exe -m tools.owner.rehearsal --config C:\tradegen-private\rehearsal.json
```

Construction verifies the private artifacts and current review first; it does not
start account or quote requests. At the console, enter `bootstrap` for one account
and risk/reconciliation unit, `run` for the cancellable schedule, `status` for
counts and fixed diagnostics, and `stop`, `disarm` or `close` for the documented
[owner lifecycle](owner-runtime-operations.md). `refresh-terms` is available only
when the signed audit includes the corresponding reviewed term authority.
EOF emits the actual final close status; a pending worker is not reported as
finished. Do not publish console artifacts or account audit files to GitHub.

## Required existing prerequisites

- The complete, current code and table approval for this exact deployment and
  interpreter. Existing owner keys/logs remain intact.
- A genuine prospective capture, actual qualifying evaluation and current
  detached source/implementation review. The launcher verifies the signature,
  current owner authority, code hash, source binding, implementation and driver
  identity before reaching any E1 read. It does not grant strategy qualification.
- A separately reviewed opening baseline and independent latest head, already
  initialized under `account-baseline`; the window's history head must also exist.
  The launcher never seeds, adopts, repairs or re-anchors either chain. A baseline
  older than 30 seconds refuses, so use a reviewed capture/setup procedure that
  leaves current evidence before launching.
- An explicit isolated `TRADEGEN_HOME` matching the config `state_root` (the
  default real `.tradegen` directory is not a rehearsal root), plus a separate
  existing head root outside the state root and repository. Owner authority must
  be valid in the selected environment; the launcher does not copy keys/logs.
- The existing E1 credential **names** in the owner's process environment. E1
  alone reads their values. Use read-only account credentials; do not paste values
  into configuration, audit documents, chat or logs.
- A genuinely exclusive, quiescent account during the entire declared fence:
  no other trading program, manual order, transfer, reward or other balance
  change. Paginated/repeated reads do not establish this by themselves.

## Private configuration

`rehearsal.json` has exactly these keys. Replace placeholders with the actual
reviewed paths and original evaluation timestamp; they are deliberately invalid
as supplied. No mode, credential, arbitrary module or callback field is accepted.

```json
{
  "schema_version": 1,
  "kind": "tradegen-flat-account-rehearsal/1",
  "profile": "C:\\tradegen-private\\profile.json",
  "program": "C:\\tradegen-private\\program.json",
  "protocol": "C:\\tradegen-private\\protocol.json",
  "capture": "C:\\tradegen-private\\capture.json",
  "review": "C:\\tradegen-private\\signed-review.json",
  "account_audit": "C:\\tradegen-private\\account-audit.json",
  "window": "C:\\tradegen-private\\window.json",
  "evaluated_at": "<original evaluation timestamp with timezone>",
  "monitor_until": "<reviewed monitoring-end timestamp with timezone>",
  "state_root": "C:\\tradegen-state",
  "head_root": "C:\\tradegen-heads"
}
```

The window must begin in the future, meet the existing slot/boundary rules, and
finish no later than `monitor_until`. Monitoring may extend at most one day beyond
the window and must cover the required recovery cutoff. The complete monitoring
span must lie inside both the exclusive-account fence and the review validity.
The original evaluation time is required to reproduce the signed result digest.

## Signed account audit, not a `complete: true` flag

The exact `account-audit.json` bytes must be the audit file supplied to the
existing external `review-approve` procedure. Its SHA256 must equal the audit hash
inside the actually verified detached review. Editing or reformatting it afterward
invalidates that binding. The signer and owner review the evidence; the launcher
does not create a review or establish the truth of an operator statement.

The audit schema contains exactly:

| Field | Required content |
| --- | --- |
| `schema_version` | Integer `1`. |
| `kind` | `tradegen-flat-account-rehearsal-audit/1`. |
| `account_scope` | The reviewed scope used by profile, account identity and baseline. |
| `deployment_window_digest` | Digest of the exact reviewed `DeploymentWindow`. |
| `baseline_anchor_sha256` | The anchor digest retained in the existing baseline state. |
| `opening_anchor` | Exact `OpeningAnchor` fields: scope, actual zero-inventory/open-orders origin, decimal-string opening cash, source document hash, and the reviewed statement `inventory_and_open_orders: "verified-zero"`. |
| `coverage` | Exact `CoverageEvidence` fields, including history and exclusive-fence timestamps, scope and source document hash. |
| `trade_fees` | Array of exact `TradeFeeEvidence` records for ambiguous split-fill fees; decimal strings and reviewed evidence hashes. Empty only when the actual collector requires none. |
| `source_documents` | Between 6 and 64 `{kind, path, sha256}` records, with exact private original bytes checked. |
| `terms_authority` | `null`, or exact reviewed `TermsAuthority` fields matching the profile's stable term/source digest. |

Coverage statements must be explicitly present and actually reviewed:

- `identity_binding: "reviewed-credential-to-main-pocket"`
- `history_retention: "reviewed-complete-since-origin"`
- `transfer_scope: "reviewed-no-unreported-flows-or-pocket-transfers"`
- `account_mode: "reviewed-krw-spot-cash-only"`

These strings are neither exchange attestations nor automatic proof. The six
required source-document kinds are `opening_anchor`, `coverage_review`,
`credential_identity`, `history_retention`, `exclusive_fence`, and `transfer_scope`.
Each path points to a bounded local `.json`, `.md`, `.txt` or `.pdf` file; its exact
bytes must match the signed audit's hash. The opening/coverage `source_sha256`
fields must match their respective documents. Fee records require referenced
`fill_fees` documents. Optional term authority requires `instrument_terms`
provenance and the same `credential_identity` hash. Linked/hard-linked/private
credential/state traversal paths are rejected by the existing private reader.

The fence applies to the complete accepted request interval, not merely launch
time. A context-local E1 guard freshly verifies current owner, code, source and
implementation before every request attempt, including retries and both term
GETs. One fresh authority observation is shared only within that request's
audit/source/implementation assessment. It has no positive authority cache. It checks the review/fence/history/
monitor bounds again after verification, before sending, after the response and
after pacing or retry waits. Nested guards retain all outer constraints. A failed
check permanently refuses this runtime, and guard exception text stays private.
A read-only socket operation already in progress cannot be forcibly undone: if
it returns outside the permitted interval, its result is discarded and no retry
is sent. These checks do not prove continuous external-account history.

## Limits of this runnable path

- The account interval source remains flat-only. Held inventory, a new fill,
  external flow, inconsistent fee/history, a gap or a missed cutoff refuses.
  Complete original collector validation remains active. Matching endpoint
  balances do not silently prove unobserved account history.
- Dry acknowledgments are not fills in the real account. No real order is sent,
  and simulated fills are not fabricated into that account's evidence chain.
- The console's `prepare` command requires an actual current planner provider;
  the standalone launcher does not yet supply one and returns
  `OWNER_CURRENT_PREPARATION_INPUTS_REQUIRED`. It never reconstructs a session
  from saved JSON or assumes a selected stake/seed.
- Without reviewed optional term authority, existing terms still expire after
  five minutes. The launcher does not extend their timestamps. With that
  authority, the existing same-contract renewal checks apply unchanged.
- Actual capture latency and Windows timing may exceed the coordinator's fixed
  deadlines. Each request loads current owner authority once and shares that
  observation only within its audit/source/implementation assessment; the next
  request loads authority again. Tests using the actual E1 transport with fake
  responses, virtual pacing and a current baseline confirm that 1.5 seconds per
  authority load fits the 30-second collection bound, while 4 seconds per load
  refuses without advancing its baseline head. This is a synthetic latency test,
  not a Windows performance guarantee. Real quote/slot timing still requires
  measurement; no deadline is widened and missing slots are not backfilled.
- Success at constructing, bootstrapping or monitoring this rehearsal is not
  live-order readiness, a proof of return, or a change to the protected floor.

This is not legal, tax or investment advice; the software is not a licensed adviser.
