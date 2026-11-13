# PR5 B1b-1 — independent attestation of an exact research archive

2026-11-13. This change connects the actual B1a archive to an independently reviewed signer and the application's current owner authority. The scope is `research_archive_manifest_attestation`: owner confirmation of the exact archived manifests and available file bytes. It does not approve source provenance, strategy selection, recovery, activation or an order. The frozen validation and source delivery record appears below.

## Behavior and trust boundaries

The exporter reads the actual primary and backup graphs, including the linked raw archive of a verified revision. It writes a new explicit review directory containing `request.json` and `payloads/p-<logical_id>.bin`. Original names remain metadata; the fixed prefix avoids Windows device filenames. Exact canonical raw and optional verified manifests are embedded in the request. The request binds the complete file inventory, hashes, code closure, scope and explicit expiry. Failed, incomplete, malformed and empty originals remain visible; signing them does not promote them into successful research.

The independent `bundle-attest` command is implemented in the existing standalone signer. The owner must use a separately reviewed copy outside the deployment and review packet, with the deployment's isolated interpreter and existing direct confirmation procedure. The signer does not import application code. It independently parses the B1a manifests and new request, checks every file and the complete packet inventory, verifies the owner signature and key-rotation chain, and checks the actual D14 deployment closure against an effective code approval. This is an Ed25519 archive signature, not a WebAuthn or Face ID implementation.

The displayed body is fixed before confirmation. After confirmation the signer rechecks the packet, deployment, current key and owner head under the log lock. A future-dated code approval is not effective early. The current approval is checked again before signing and publication, including a different future approval becoming effective during confirmation or signing. Expiry and a five-minute confirmation window are checked after expensive work; the signed issue time is not silently refreshed. Output is a new exclusive JSON file with readback. Interrupted output is preserved, not overwritten or treated as valid completion. No owner-log event, key creation, activation or order is emitted.

Application authentication uses the actual `BundleStore` and `CurrentOwnerAuthority`, not a deserialized result, arbitrary verification callback or public key embedded in the document. It checks exact Ed25519 bytes, the current trusted key and approved code, source graph and backup contents, and the raw dependency. It re-observes owner authority and rereads the graph, with a completion clock after heavy work. Key or approved-code changes, rewritten or unverified owner heads, rollback, stale observations, time reversal, expiry and object changes refuse authentication. Verified benign owner-log growth is permitted. The original observation cannot be refreshed indefinitely to bypass the thirty-second bound.

The returned assessment is a display result for that observation, not a reusable authority token. Individual revocation is explicitly unsupported in this stage and `current_use_eligible` remains false. Source authentication, research selection, execution, recovery and signature backup remain false. Archive identity can be inspected under an existing trading halt without removing that halt or obtaining trading authority. A format-valid claimed evaluation is still only an archived claim until the separate actual evaluation and review gates run.

## Filesystem handling

The review directory is explicit, empty and outside the repository, private state and archive roots. POSIX writes use retained directory descriptors, exclusive creation, generated relative names and identity checks. The Windows implementation pins ancestors and the destination with native directory handles: attributes-only access, `OPEN_EXISTING`, reparse inspection and read sharing only. Write and delete sharing are denied. Unsupported pins are refused rather than replaced with a weaker path check. Handles are closed even if an earlier close fails.

The runtime guard exception is limited to the exact reviewed native class and its two local imports. Exact native calls and flags are pinned, and native references outside that class are refused. Negative controls cover extra DLL loaders, destructive calls through aliases, changed sharing/access flags and external native-handle access. This is a source-review guard, not a sandbox for arbitrary hostile Python. Fake Windows API tests validate the call contract; actual Windows filesystem, synchronization, power-loss and deployment behavior remain untested here.

## Validation evidence

The development combined run completed 274 selected tests: **256 PASS, 5 FAIL, 13 NOT_RUN**, 239.701 seconds. Three failures came from a test fixture treating `owner.home()`'s `compliance` child as the isolated state root; the root reference was corrected without changing production behavior. Two failures exposed the missing narrow native-import guard allowance. All failures are retained in the development evidence.

An independent nine-test trust run passed on that frozen development source. A separate adversarial probe exposed an actual signer inconsistency: a genuine future-dated code approval could produce a signature that the real current owner authority rejected. The new command now applies the same time-filtered code approval semantics. Three new timing regressions and two existing expiry/rotation regressions passed in the isolated developer check; these overlap with the final suite and are not additive.

The first final attempt was deliberately interrupted after 27 passes when independent review found that an import-only guard exception allowed extra native loaders or alias calls in hypothetical source mutations. No such call was present in production. The native class and out-of-class references were then pinned and the independent mutation checks passed. QA bytes were restored on interruption. That interrupted attempt is not acceptance evidence.

The final selected suite covers all new format, authentication, packet and signer cases, actual B1a archives, existing source/carry reviews, owner and runtime guards, private-input/Windows acceptance cases, and no-account/no-order regressions. Positive cases include actual fixed and carry recorders, real temporary Ed25519 keys and owner records, independent packet parsing and actual current authority. The full-command fixed case copies the actual D14 Python closure to an isolated deployment; faster raw/carry signer cases explicitly use synthetic deployment fixtures. Neither case is a real owner signature or live account run.

The final frozen run completed **277 selected tests: 264 PASS / 0 FAIL / 13 NOT_RUN**, in **260.380 seconds**, one continuous process. The thirteen unexecuted cases require native Windows: twelve private-input cases and one console-input case. The new fake Windows API checks passed but do not replace those or establish native Windows acceptance.

The tracked Python/YAML fingerprint was `3af46ef90144fd03d2a67dc6edb7710de4ec8f9678dd12359bc1d99e0bf4de7d`. Nineteen KEYLESS variables were set; source and protected-home metadata were unchanged from before test imports/discovery through completion; QA bytes were restored. Evidence is `attestation-final2-summary.json` and `attestation-final2-rows.json`. This selected suite is not a new full-repository run. Counts from overlapping development, independent and final tests must not be summed.

Implementation commit: `173f346` on `gpt/research-bundle-attestation`. Integration with main `a4e6601` changed only the preceding three execution logs; the frozen source fingerprint remained identical after integration commit `0e06a37`. The PR and final delivery identifiers are recorded in the handoff ledger.

## Remaining work

- Individual restrictive revocation tied to the trusted owner log and current authority.
- Sealed actual evaluation, source/factory review and family-complete selection integration; archive identity alone remains insufficient.
- Separate versioned preservation of the signature envelope and its trusted recovery material.
- Exact signed-original recovery, changed-version reconstruction, new observations and discontinued-study handling.
- Telegram/WebAuthn registration, approval application, revocation and device-loss recovery.
- Actual Windows acceptance and production account/hold/order reconciliation, followed by the required owner approvals and activation checks.

Existing loss floors, risk limits, halt behavior and approval scopes are unchanged. No actual private home contents, real credentials, exchange/data API, notification, activation or order were used.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
