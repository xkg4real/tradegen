# Unsigned strategy review handoff

`execution_launch.review_request` prepares a concrete review queue artifact from
an actually computed prospective evaluator result, a profile, a protocol, and
explicit program source bytes and canonical parameters. It does not authenticate
the source, reviewer or program callback, sign anything, or grant execution.

## Prepare and inspect a request

The pure API is:

```python
request = build_review_request(
    profile, protocol, computed_result, now=explicit_aware_time,
    program_artifact=reviewed_source_bytes, parameters_json=canonical_parameters,
)
text = review_request_json(request)
```

The program digest uses `execution_launch.program.program_digest`, matching the
runner's artifact-plus-parameters formula. Actual program bytes and parameters
must match the protocol and profile. Stable profile/rule terms, full current
profile snapshot, initial capital, computed result, input capture and registration
digests are bound. Account scope and monetary profile values are not copied into
the request. A changed account, strategy, capital or economic rule cannot borrow
another study's request.

The output includes computed mathematical criteria/metrics, explicit blockers,
the claimed source category, a review deadline and nine unfinished review checks.
An unverified `prospective_paper_capture` label is preserved as a **claim**, with
`source_authenticated=false`; it is not promoted by being written to a request.
Replay/synthetic categories and expired evidence remain visible. Every review,
signature, owner-context and execution flag remains false. Reviewer, public key,
signature, deployment code hash and per-check review evidence remain null.

`parse_review_request` validates bounded JSON, exact schema, chronology and the
request's digest. It checks integrity only. An adversary can edit an unsigned
summary and recompute its digest; the import remains an unsigned request and is
not accepted as a `ValidationResult`, `ReviewReceipt` or `ImplementationReceipt`.
Imported PASS fields, completed check marks, signatures and permission flags are
refused. Review completion needs a different, reviewed authentication workflow;
editing this JSON is not that workflow.

## The review still to perform

1. Authenticate the original source identity and archived records.
2. Establish independently reviewable publication before the capture began.
3. Check that the capture window was genuinely independent of strategy selection.
4. Disclose the whole candidate family and all relevant retries.
5. Check that causal recorded decisions came from the frozen program.
6. Bind the exact running driver implementation to that reviewed program.
7. Compare the deployment's source and dependency-inclusive approved code closure.
8. Confirm capital, costs, instrument rules and account-risk applicability.
9. Confirm effective owner limits and the actual prepared trading session.

These checks are requirements for a subsequent human/technical review, not claims
that this artifact has satisfied them. Software fixtures demonstrate request
handling; they are not authentic source reviews or profitable live studies.

## Authenticated review is a separate workflow

The standalone signer now provides a reviewed `review-approve` command, and
`execution_launch.review_auth` verifies its detached documents. Follow
[strategy-review-signing.md](strategy-review-signing.md) for owner steps and the
runtime integration contract. The existing owner ledger schemas are unchanged;
a code approval is never reinterpreted as a source review.

The separately versioned signing domain binds the full unsigned request, actual
fixed-driver identity, deployment code, reviewer/current key, audit-document
hash, issuance time and bounded expiry. Verification pins raw Ed25519 public
bytes to the **current** fingerprint in a freshly loaded, intact sealed owner
context with current signed code. `Context.owner.fingerprint` is the current
PEM fingerprint; `LogCheck.first_key_fingerprint` is the historical first key.
A cached same-day context cannot prove that its key remains current. The trusted
authority provider must observe rotations and current state on each invocation.

The fixed implementation verifier requires an actual factory-issued driver and
its unchanged callback, program, dependencies, profile, protocol and deployment
window. Artifact hashes alone never authenticate an arbitrary Python callable.
It also compares the exact upstream history provider and verifier with explicitly
selected trusted deployment objects. Those identities establish selection only;
they do not cryptographically prove that the adapters or live records are valid.

Actual human source review, fresh owner-loader/public-key integration, and
trusted live-history capture/verification remain separate deployment work.
This unsigned request never satisfies them. E2 owner/session and per-order
checks remain separate even after a genuine detached review succeeds.

This software is not legal, tax or investment advice and is not a licensed adviser.
