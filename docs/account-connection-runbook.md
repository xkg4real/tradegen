# Account connection and owner setup

This change connects explicit read-only E1 clients to a sanitized probe interface and supplies an
exact evidence contract for E2. The status command does not contact a venue, read a credential
value, inspect an owner ledger, sign, arm or submit an order. An inquiry result and reconciled
account evidence are separate from permission to execute a trading session.

## Current Cloud findings

At development time the managed environment reported current observations, enforced restricted
network policy, no configured secrets, no runtime bindings and no outbound account identities.
KIS, Upbit and OKX hosts were absent from the allowed-host list. No live account connection was
attempted, and no credentials were requested in chat or copied into the repository.

E1 intentionally sets `requests.Session.trust_env=False`. Managed Cloud routing now has an
explicit [sidecar and CA integration](cloud-transport-contract.md). Build a `ManagedRoute` from
current nonsecret policy/runtime observations and the approved proxy/CA selectors, then pass it
to `inspect_configuration(..., route=route)` and the reader. Inspection revalidates this route
without activating it. Without that explicit opt-in, the report still exposes
`E1_PROXY_PATH_UNSUPPORTED` when a proxy path is required. A configured route is not proof of
connectivity, credential validity or account permissions.

## Read the configuration report

Run in the repository's configured Python environment:

```sh
python -m execution_accounts.cli
python -m execution_accounts.cli --configuration-manifest
```

The first command exits 2 because configuration diagnostics never establish execution readiness.
It lists variable names as present or missing, fixed reason codes and owner-public-key existence.
Presence includes blank or placeholder variables: it is explicitly `PRESENCE_UNVERIFIED`, not
credential validity. Public-key existence is not proof of a signature or owner approval.
The second command emits a reviewable JSON request containing host names and variable names only.
It does not change Cloud configuration or include credential values.

Optional `--runtime-status <metadata.json>` and `--network-policy <metadata.json>` accept non-secret
configuration snapshots. Use the supported Cloud environment status/configuration interface to
obtain current metadata. Missing, stale, desired-only or unenforced observations remain unknown.
Metadata files must be bounded JSON files outside the actual account-state homes; linked paths,
duplicate JSON keys and nonfinite JSON numbers are refused. Neither option accepts a key file.

The owner must configure credentials through the secure environment/user-PC workflow, never by
sending values in chat or committing them. E1's Upbit and OKX keys remain inquiry-only. KIS keys
can have trading capability, so the existing signed-code requirement remains mandatory.

## Explicit read-only inquiry integration

`execution_accounts.readiness.E1InquiryReader` delegates to the existing E1 venue snapshot client;
it never invokes the E1 poller, owner-context loader, alert writer or order adapter. A caller must:

1. Select a venue and an explicit isolated state directory, with `TRADEGEN_HOME` already pointing
   to that directory. The default `~/.tradegen`, `~/.nextgen`, linked/aliased roots and mismatches
   are refused. No state directory is created by configuration inspection.
2. Declare every credential variable for the selected venue in the process environment. This
   prevents E1's `.env` fallback. The readiness code examines names only; E1 consumes credentials
   only when the owner explicitly runs the inquiry in their authorized environment.
3. Supply KIS with a fresh, sealed, code-signed context from the existing reviewed owner workflow.
   Its canonical context hash is rechecked before the E1 client is called.
   The probe does not call `owner.load_context`, because that loader can write state snapshots.
   For OKX supply an explicit finite positive KRW value for USDT, as required by E1.
4. For managed Cloud, pass the validated `route` and an explicit callable `clock` to
   `E1InquiryReader`. Every clock read must return an aware datetime; there is no implicit wall
   clock. The route and clock bindings apply only during that reader call and are restored on
   exit. Existing direct integrations may continue supplying E1's reviewed poll/test clock seam.
5. Call `inquire_once(..., reader=reader, configuration=report, allow_read_only_probe=True)` with
   an aware timestamp. Environment/network blockers refuse before the reader is called. There
   is no implicit live reader and no probe command in the default CLI.

The operation returns only status, reason codes and counts. Balance amounts, account identifiers,
order IDs, addresses, credentials and raw exceptions are not included. Fresh venue scope and
server clock are checked, including a Seoul-day disagreement near midnight. A successful probe
still returns `account_evidence_ready=false` and `execution_ready=false`.

KIS's existing token acquisition may write only its checked cache under the explicitly selected
isolated state root. It is the sole mutation inherited by this reader; it is not an order. During
development, all three clients ran against synthetic HTTP fixtures and temporary state only.

## Complete evidence before E2

E1 uses bounded recent pages and floating-point inquiry summaries. It cannot establish complete
FIFO history, exact available/locked cash or the full authoritative execution state. Do not
convert an E1 `ok` flag into an E2 permit.

Use [`AccountBundle` and the evidence contract](account-evidence-contract.md) with authenticated,
complete, account-scoped source records. `build_observation(bundle, now=...)` reconciles evidence
into an `AccountObservation`; `assess_bundle` reports evidence readiness only. Provenance hashes
prove internal content integrity, not that the input came from an exchange. A trusted collector
and its complete history/fee/flow coverage remain explicit prerequisites.

## Owner signing and activation

Signing is performed by the owner in their own reviewed environment. No owner key, signing
password or active account state was accessed or changed during this work. These instructions
are preparation, not a record that the owner has signed or activated anything.

After reviewing the final code and independently checking the trusted signer copy against the
repository, the existing signer supports:

```text
<repo-python> -I <reviewed-signer-copy> code-approve --repo <TRADEGEN-repository>
```

Use the repository's pinned Python environment and the existing signer workflow. The tool uses
an interactive terminal and the owner's encrypted key; do not automate password entry. Review
and configure the existing approved tables, account eligibility and loss limits separately.
Public-key existence and a merged PR do not replace these approvals.

Prepare a new odds session using complete current account evidence and final instrument rules.
The owner must review the preparation and use the returned content-derived `prepared.session_id`,
never the input label. The existing owner workflow accepts a `session_armed` event, but this
readiness tool does not generate, sign, append or run that event. A restart or changed code needs
fresh reconciliation/preparation and the corresponding owner review.

Before activation, resolve missing first-day/zero-profit-day loss budgets and valuation/flow
conventions without guessing. The research paper does not establish a validated live strategy,
reliable intraday fills or a profit guarantee. Inquiry capability, complete account evidence,
owner approval and a suitable strategy are independent requirements.

This software and report are not legal, tax or investment advice and are not licensed advisers.
