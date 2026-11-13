# PR5 B2a — restore exact signed research evidence from backup

2026-11-13. Implementation and the frozen focused integration run are complete. This stage supplies a callable recovery API: it does not install an automatic detector, CLI, notification bot, persistent quarantine controller or production route switch. The final validation and source delivery evidence follows.

## Actual restoration path

`inspect_signed_backup` and `restore_signed_backup` require explicit original primary/backup roots, storage limits, an exact detached archive attestation, the expected bundle digest, the actual current owner provider and its clock. Restore additionally requires a separately provisioned real destination store and an incident identifier. Callers cannot substitute an inspection report, fabricated store receipt, approval boolean or embedded public key for verification.

The source primary may be missing or damaged. Its catalog and old head are never used as recovery authority. The signed request identifies the exact raw and optional verified manifests, their complete file inventory and object references. The reader derives the manifest references and reads every actual backup object, checks length/hash/reference/policy and raw-to-verified linkage, then rereads the complete graph across owner re-observation. Missing, changed or partial evidence refuses the entire restoration; rejected candidates and failed raw archives are not omitted.

Original and destination roots must remain separate by path, containment and available filesystem identity. The source pins backup directories and the existing object lock; individual real object-store reads release their non-reentrant lock before destination work. No source file is overwritten, deleted or adopted as a new trusted head.

The destination must already have a valid operator-provisioned store and the same evidence policy. A read-only preflight under its real lock checks the whole raw, optional verified and recovery-artifact operation against catalog and deduplicated object capacity. It reserves no space against other writers; each subsequent normal commit rechecks admission. Recovery then invokes the real `archive_raw` and `commit_verified` paths, including destination backups. It does not initialize a head, bypass CAS checks or silently repair an interrupted store.

Logical study identifiers, manifests and payload bytes remain exact. A separate deterministic raw artifact contains the original attestation bytes and a recovery-content commitment, backed up through the same real store. This artifact describes what was restored, not independent proof of when it happened or permission to operate. Verification time belongs to the returned observation. An exact retry reuses the same incident/document/content without overwriting partial evidence or duplicating completed commits.

## Time and final verification

Source inspection and prewrite validation retain their original actual owner observations and thirty-second freshness bound. Copying immutable archive bytes can take longer. After copying, a separate final transaction obtains fresh actual authority and rereads the destination target and signature artifact, including backups. It invokes the real archive-authentication path and retains the final transaction's first observation through all heavy work and the completion clock.

The same provider retains key/code/head and rollback pins throughout. A long copy cannot succeed by merely assigning a new timestamp to the old source snapshot. A slow final auxiliary-archive read must fail even if a later owner observation is fresh. Expiry, time reversal, current code/key change and invalid authority remain refusals.

On completion the result reports `EXACT_ARCHIVE_RESTORED`, exact target and auxiliary-artifact digests, destination backup verification and signature backup verification. It is a read-side fact for that operation, not a reusable permit. Current research use, source authentication, selection, automatic operational recovery and execution remain false. Individual revocation is explicitly unsupported in this B1b-1-based stage; its separate implementation must not be inferred from successful copying.

Failure after an earlier commit preserves those immutable artifacts and returns no complete-restoration result. A retry can complete exact, intact prior work. A conflicting partial file or catalog/head mismatch is preserved and refused, not truncated or re-anchored. Restoration itself never clears a trading halt or treats damaged evidence as a sell signal.

## Validation record

The first direct development run passed 26 tests in 144.901 seconds. Two later bounded changes corrected the Windows pin's exact string argument and the fixed diagnostic for raw I/O errors; their two added regressions also passed. These development runs overlap the final suite and are not a substitute for it.

Tests use actual temporary B1a source/destination stores and independent heads, temporary Ed25519 owner signatures and actual current authority. They cover damaged/missing primary evidence with intact signed backups, failed/empty originals, all verified candidates, wrong bytes/policies/keys/code/expiry, capacity and identity refusal before writes, lock order, interrupted raw commits, CAS/readback failure, exact retry, signature-artifact backup and preserved old source/head bytes. Timing tests distinguish a thirty-one-second copy followed by fresh full verification from a stale final verification.

Independent source reviews found and corrected final-observation freshness and source-root parity issues. Native Windows behavior is not established by fake/native-adapter checks on Linux. No actual home contents, real key, account, exchange API, activation, order or notification was used.

The final frozen integration run completed **196 PASS / 0 FAIL / 0 NOT_RUN**, in **309.968 seconds**, one continuous process. It covers all 28 recovery/artifact tests, the actual B1a archive/format/store paths, current bundle authentication, archive signer-command regressions and source/owner/no-account/no-order guards. No native Windows acceptance cases were selected; zero NOT_RUN does not establish Windows support verification.

The tracked Python/YAML fingerprint is `ce6820e0b2afe181f799b8944e79f800d1cafdeea023614ca2bd1034f3cedbdc`. Nineteen KEYLESS variables were set; source and protected-home metadata were unchanged from before imports/discovery through completion; QA bytes were restored. Artifacts are `recovery-integration-dev1-summary.json` and `recovery-integration-dev1-rows.json`; the historical label `dev1` is retained, and this completed unchanged run is the final focused evidence. It is not a new full-repository run, and overlapping development counts are not additive.

Implementation commit: `119645f97c2a21e6277a4ff64f4e66c5a6a4a81b`, based on main `13555b90a256be219f25c1546449eb4d12406d42`. The final PR/head/main delivery identifiers are recorded in the handoff ledger.

## Remaining integration

The backend still needs a reviewed operational trigger, scoped persistent quarantine handling, discovery of signature backups, and result notifications. Existing valid approval reuse also requires current individual revocation and actual sealed source/factory selection checks. A reconstructed version, new observation or altered included report requires a new research revision and the appropriate approvals. Historical-key/expired-signature archival recovery, Windows deployment, account/open-order reconciliation and production activation remain separate work.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
