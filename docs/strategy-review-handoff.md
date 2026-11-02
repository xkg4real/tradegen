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

## Authentication design left explicit

The existing signer has no reviewed detached strategy-document signing command,
and the current owner ledger schemas contain no strategy-review event. This
change adds neither and does not reinterpret a code approval as a data review.

A future detached source-review workflow can use a separately versioned signing
domain, pin the raw Ed25519 public key to the **current** fingerprint in a fresh,
intact, sealed owner context, and require current signed code. In the existing
code, `Context.owner.fingerprint` is the current PEM key fingerprint;
`LogCheck.first_key_fingerprint` is the historical first key. They must not be
confused. A fresh authority provider must reflect rotations/revocation; a cached
same-day context does not prove that its key is still current.

The signed document should bind review kind/version, exact protocol/result/input/
registry/profile/program/deployment hashes, actual review identity, audit-document
digest, issuance time and bounded expiry. Domain separation prevents interpreting
an owner-log signature as a detached review. Binding and expiry prevent reuse for
a different account/profile, study, program or evidence window. Any owner-log
anchor design must allow subsequent legitimate session events through verified
ancestry rather than invalidating every review when the log head advances.

An implementation review requires more than that signature. A callable's claimed
artifact digest does not establish that it executes the artifact. A verifier
which merely compares artifact bytes and then returns the arbitrary supplied
`driver.callback` would authenticate unrelated code. The smallest defensible
integration is a fixed, audited driver factory/type included in the approved code
closure, with canonical parameters and exact per-process instance binding. A
reviewed registry can bind that issued driver; a generic JSON importer cannot.

Until those workflows exist and actual review evidence is supplied, existing
`review_verifier` and `implementation_verifier` remain explicit trusted integration
boundaries. This request preparation does not close them. E2 owner/session and
per-order checks remain separate even after a future review succeeds.

This software is not legal, tax or investment advice and is not a licensed adviser.
