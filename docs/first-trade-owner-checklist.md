# First automatic trade: owner checklist

This guide records the remaining owner actions after the five software foundations were implemented.
It does not certify live connectivity, a qualifying strategy, signatures or activation. The supported
collector and prospective evaluator currently cover Upbit KRW spot; other E1/E3 venue adapters do
not make those complete launch paths. No new strategy passed a real prospective study during development.

1. **Resolve private profile inputs.** Choose venue, market, symbol and an opaque account scope;
   supply current lot/tick/minimum/fee evidence. Confirm the first-day and zero-profit-day loss
   budgets and accounting conventions. Keep actual values in a private file. The published
   [template](launch-profile.example.json) intentionally contains nulls. The existing principal,
   peak protection, prior-day realized-profit and first-day rules remain unchanged; equality
   with a protection floor is not itself a breach. A profit target does not increase risk limits.
2. **Configure the selected environment securely.** Use the supported secure environment/account
   setup for credential names, venue host access and approved IP restrictions. Do not paste keys,
   passwords or account numbers into chat, Notion or GitHub. The current development Cloud has
   no venue credential bindings or permitted venue hosts. The new route supports its sidecar;
   it cannot grant network access. Keep inquiry and order capabilities separate; do not add
   withdrawal permission. See the [connection runbook](account-connection-runbook.md).
3. **Review and receive the final code version.** Review the new PR and its measured verification,
   then approve that PR's merge if acceptable. Synchronize the reviewed tree in the owner
   environment. Git commit approval, a chat signature and a merged PR do not produce an app
   code signature. A later runtime change invalidates that signature and needs renewed review.
4. **Prepare the trusted signer once.** Open Windows Terminal yourself, outside the app's process.
   Review `tools/signer/sign.py`, copy it outside the repository and independently compare/record
   the two SHA256 hashes. Inspect the repository venv's `Lib/site-packages/*.pth`: the signer
   workflow permits only `distutils-precedence.pth`. Reuse the existing owner key. Run `keygen`
   only if no owner key exists; keep its encrypted private key and password locally. Copy only
   the public PEM to `core/compliance/owner_pubkey.pem`. Never transmit the private key.
5. **Sign code, tables, eligibility and limits.** Use that repository's pinned Python and the
   external reviewed signer with isolation enabled:

   ```text
   <repo>\.venv\Scripts\python.exe -I <trusted-copy>\sign.py code-approve --repo <repo>
   ```

   This is a template, not a command containing an actual local path. Before every password
   entry, recheck the trusted copy against its independently recorded hash and recheck the
   venv's `.pth` names; the initial setup does not replace those checks. Read the displayed file
   closure, SHA256 and timestamp; type the confirmation and password directly in the terminal.
   Approve the `rules`, `instruments`, `venues` and `calendar` inputs and applicable account
   eligibility/acknowledgments, then explicit caps and loss limits through the existing signer
   workflow. Do not copy invented event JSON or session IDs. Initial or loosened limits cannot
   take effect before the next Seoul date and also depend on existing session/halt state.
   Verify their actual effective values; an advisory date is insufficient. KIS authenticated
   inquiry additionally requires code approval before its first inquiry.
6. **Verify authentic account evidence.** Perform an explicitly requested read-only inquiry in
   the configured owner environment. Check identity, permissions, server time, settled cash,
   complete fills/fees/flows and opening inventory. The collector requires reviewed identity,
   retention coverage, a zero-inventory/open-order anchor, main-pocket scope and a quiescent
   capture. A fresh response, matching hash or successful first page proves none of these by
   itself. Unsupported flows, stale prices or ambiguous per-fill fees must be resolved.
7. **Complete prospective strategy validation and rehearsal.** Freeze the actual program,
   parameters, capital, profile/rule terms, data capture implementation and evaluation protocol
   before the new capture window. Preserve the original negative research result. Review the
   independent capture/registry and causal decisions; run the cost/lot/delay evaluation and
   verify the exact implementation used by the runner. A hash alone does not authenticate a
   source or reviewer. Confirm the rehearsal's partial fills, cancellation, restart, uncertain
   sends, duplicate protection and risk responses. Passing software fixtures is not passing
   strategy evidence. See [validation](forward-strategy-validation.md) and
   [runner contract](automatic-runner-contract.md).
8. **Prepare and activate the actual session.** With current account evidence, rules and qualified
   strategy evidence, call the reviewed launch preparation integration. Inspect the returned
   actual `prepared.session_id` and bound inputs before the owner signs the session event.
   Do not use a label, example ID or deserialized substitute. Preparation expires and is bound
   to the process; restart requires reconciliation and fresh preparation. Final order checks
   still apply after activation. The development agent does not perform this owner action.

## Safe offline status

These commands do not connect to an account, sign or activate anything:

```sh
python -m execution_launch.cli
python -m execution_launch.cli --template
python -m execution_launch.cli --profile <private-profile.json> --now <aware-ISO-timestamp>
```

The current Cloud CLI accepts an explicit bounded regular file, refuses linked/private credential
paths and emits redacted field-level blockers. No owner context is loaded, so a complete file
alone still reports `SIGNED_CONTEXT_REQUIRED` and `execution_ready=false`. This release's
no-follow file reader requires POSIX support; use the pure parser/preflight library in another
reviewed integration rather than weakening the file boundary.

This software is not legal, tax or investment advice and is not a licensed adviser.
