# PR5 A0b — complete family preflight before evaluation

2026-11-13. The study selection CLI and authenticated selection path now share complete current-family validation. If a later candidate is missing or malformed, earlier candidates are not evaluated or exposed as a partial successful selection. This is input validation and real evaluation integration, not immutable research storage, failed-evaluation issuance or trading activation.

## Changed behavior

- `study_evidence.evaluate_study_family` snapshots exact raw bytes, protocols and economic rules; checks the exact study/strategy ID sets and the plan's registration-chain digest; validates every complete capture; checks remaining real evaluator capacity; and only then invokes the existing actual evaluators. Both legacy fixed and carry formats use their existing arithmetic and result issuance.
- The new validator-only path reuses the same input checks as evaluation. It performs no simulation, statistical inference or result issuance. A parsed input or constructed `FamilyEvaluation` is not an approval or privileged result token.
- Numerically rejected candidates and their original bytes remain in the returned family. Raw whitespace and original encoding bytes remain part of each capture hash. The request's family commitment comes from the actual validated/evaluated snapshot, so a caller changing its mapping later cannot substitute different signed evidence.
- Both CLI entry points use the same loader. Missing, additional or case-aliased `*.capture.json` entries refuse the family; unrelated reports and receipt logs are allowed. Explicit directory/file identities, link restrictions, bounded enumeration and secure private-file reads are retained. The loader does not claim an atomic or sealed filesystem snapshot: the immutable bytes actually read are what it validates, evaluates and commits to.
- A confirmed oversized regular file produces a resource-admission refusal. Links, inaccessible files and replacement races retain their path/read refusal. No original is deleted, rewritten or changed to unavailable to satisfy a size limit.

## Resource admission and compatibility

The existing protocol family limit of 1,000 remains unchanged. One synchronous family evaluation admits at most 128 candidates, matching the existing result registry capacity, with the existing 16 MiB per-capture bound and new aggregate bounds of 128 MiB raw input and 40,000,000 units of the existing bootstrap-work formula. These aggregate bounds represent eight maximum-sized captures and four maximum per-candidate inference budgets. Lower explicit limits are supported; higher ones are refused.

An admission limit is not evidence corruption, a statistical rejection or a recorded market lookup failure. The entire call stops with `STUDY_EVIDENCE_RESOURCE_LIMIT` before evaluation. The bounds are not promises about process RSS or elapsed time. Remaining registry capacity is checked before the first family evaluation, without reserving it against unrelated concurrent callers; each real evaluator retains its own limit check.

An unexpected calculation failure after preflight returns no partial family or approval request. Already issued internal results are not deleted or rolled back. Explicit failure outcomes and preservation of all prior attempts require the later PR5 contract; this change proves the supplied current family only.

Existing legacy/carry result arithmetic, statistical thresholds, request schemas, signature bytes and risk policy remain unchanged. New source bytes require current code approval. The actual study capture-source manifest includes its new helper dependency. The helper does not become an execution-driver dependency merely because study selection uses it.

## Validation

Frozen-source focused validation: **123 PASS / 0 FAIL / 0 NOT_RUN**, **69.611 seconds**, one process. Python/YAML fingerprint:

`599e196fa192193299c2b42a99fa80e4b0a125f459c92138cdde91fde9736bf8`

This includes the new helper and CLI boundary tests, authenticated family tests, legacy/carry strategy tests and affected source guards. It covers later-candidate corruption and duplicate JSON keys with zero earlier evaluations, exact registration chains, missing/extra files, actual 16 MiB+1 files, resource boundaries, real registry exhaustion, caller mapping changes, raw whitespace hashes, genuine temporary Ed25519 review and numerical rejection retention. Independent review additionally executed 11 selected cases successfully.

Nineteen KEYLESS variables, isolated homes and invented research inputs were used. The source and actual-home metadata remained unchanged from before imports through completion; QA bytes were restored. No actual account, private key, source API, notification, activation or order was used. Full repository regression and delivery status will be added after completion.

## Still pending

PR5's normal lookup-failure evidence issuer, all-prior-attempt lineage, sealed versioned research bundles, separately retained backups, signature-based exact recovery, reconstruction/research reruns and Telegram/WebAuthn remain separate. This change does not make a research review a trading activation or enable production account management.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
