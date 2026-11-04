# First automatic trade: owner checklist

This guide records the remaining owner actions after the five software foundations were implemented.
It does not certify live connectivity, a qualifying strategy, signatures or activation. The supported
collector and prospective evaluator currently cover Upbit KRW spot; other E1/E3 venue adapters do
not make those complete launch paths. No new strategy passed a real prospective study during development.

1. **Complete the private launch profile.** The owner selected Windows PC, delegated market
   selection to independent validation, and confirmed the exceptional-day intraday budget
   and 22:00 KST recovery requirement without relaxing principal or peak protection.
   These decisions are already recorded privately; do not request them again. Development
   must select a qualifying market/symbol and current lot/tick/minimum/fee evidence. The owner
   supplies the actual private account binding and reviews the completed terms. Keep actual
   values in a private file. The published
   [template](launch-profile.example.json) intentionally contains nulls. The existing principal,
   peak protection, prior-day realized-profit and first-day rules remain unchanged; equality
   with a protection floor is not itself a breach. Below `drawdown_activation_equity` the protection
   floor equals the peak, so the first fee or loss blocks new entries. A profit target does not
   increase risk limits. Save the private profile as UTF-8 without a byte-order mark: the profile
   reader decodes strict UTF-8, so in Windows PowerShell 5.1 do not write it with `>` or `Out-File`;
   pipe to `Set-Content -Encoding ascii <file>.json` instead.
2. **Configure the selected environment securely.** Use the supported secure environment/account
   setup for credential names, venue host access and approved IP restrictions. Do not paste keys,
   passwords or account numbers into chat, Notion or GitHub. The development Cloud has no venue credential bindings or permitted venue hosts;
   that observation is not a requirement to change the selected Windows deployment. The
   Cloud route supports its sidecar but cannot grant network access. Keep inquiry and order capabilities separate; do not add
   withdrawal permission. See the [connection runbook](account-connection-runbook.md).
3. **Review and receive the final code version.** Review the new PR and its measured verification,
   then approve that PR's merge if acceptable. Synchronize the reviewed tree in the owner
   environment. Git commit approval, a chat signature and a merged PR do not produce an app
   code signature. The app's signed hash also includes dependency RECORD files from the signer
   interpreter; the same Git commit in Windows and Cloud can therefore have different hashes.
   Compare the actual deployment closure using the [deployment manifest](deployment-readiness.md)
   before relying on an approval transferred between environments. Copying a public key or owner
   log does not complete an unsupported remote-approval workflow. A later runtime change needs
   renewed review.
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
   Verify their actual effective values; an advisory date is insufficient. KIS authenticated account
   inquiries through E1 require signed code. KIS Live market-data viewing is separate: it
   obtains a temporary subscription approval key and does not read account balances,
   activate an owner session or submit orders. See the [KIS Live guide](kis-live-usage.md).
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
   source or reviewer. Use the [offline workflow](launch-workflow.md) to recompute
   results and prepare the unsigned request, then review the actual
   [fixed driver identity](fixed-driver-contract.md) and deployment closure. The
   owner-only [detached review signer](strategy-review-signing.md) signs the exact
   request, driver identity and audit document; it does not sign synthetic evidence
   as real or replace the current runtime history adapters. Confirm the rehearsal's partial fills, cancellation, restart, uncertain
   sends, duplicate protection and risk responses. Passing software fixtures is not passing
   strategy evidence. See [validation](forward-strategy-validation.md) and
   [runner contract](automatic-runner-contract.md).
8. **Prepare and activate the actual session.** With current account evidence, rules and qualified
   strategy evidence, call the reviewed launch preparation integration. Inspect the returned
   actual `prepared.session_id` and bound inputs before the owner signs the session event.
   Do not use a label, example ID or deserialized substitute. Preparation expires and is bound
   to the process; restart requires reconciliation and fresh preparation. Final order checks
   still apply after activation. The development agent does not perform this owner action.

The [Windows integration plan](windows-first-trade-integration.md) describes the implemented
adapters and what still blocks a first trade. The account interval producer is flat-only, so the
coordinator refuses `controlled`, and a first fill would stop the account chain. A gap over 30 s
between account captures, or a missed 22:00 or midnight boundary, stops the account chain until
the reviewed re-anchor. A missed strategy slot ends that deployment window, and a new window needs
a new `review-approve`. The prospective study that can select a market is described in the
[offline workflow](launch-workflow.md); nothing trades until the owner signs `review-approve` on
one of its review requests. This checklist is not a completed launcher.

## Safe offline status

These commands do not connect to an account, sign or activate anything:

```sh
python -m execution_launch.cli
python -m execution_launch.cli --template
python -m execution_launch.cli --profile <private-profile.json> --now <aware-ISO-timestamp>
```

The current Cloud CLI accepts an explicit bounded regular file, refuses linked/private credential
paths and emits redacted field-level blockers. No owner context is loaded, so a complete file
alone still reports `SIGNED_CONTEXT_REQUIRED` and `execution_ready=false`. On POSIX the file
reader is descriptor-relative and no-follow. On Windows `execution_launch/private_input.py`
enforces the same boundary: a plain, singly-linked regular file on a local lettered drive, every
path component checked for reparse points and cloud placeholders, 8.3 aliases and SUBST or
network drives refused, and the opened handle must be the file that was checked. There is no
override: move such a file to a plain local folder yourself; it is never read another way.

This software is not legal, tax or investment advice and is not a licensed adviser.
