# PR5 B2a exact archive restoration API

Tree `/workspace/tradegen-exact-recovery-1113`, base `0e06a3782e6c437490d57dd549d2743def278c19`. Main owner: protective_hold_design. Root owns registry/guards/tests/commit. Existing B1a/B1b-1 and parallel B1b-2 files remain unchanged.

## Public contract

New `execution_launch/bundle_recovery.py`, `execution_launch/recovery_artifact.py`, `tests/launch_bundle_recovery.py`, and `tests/launch_recovery_artifact.py`.

```python
@dataclass(frozen=True, kw_only=True)
class SignedBackupSource:
    roots: BundleRoots        # original primary AND backup; primary contents never trusted
    limits: BundleStoreLimits

inspect_signed_backup(source: SignedBackupSource, bundle_digest: str,
    attestation_bytes: bytes, *, authority_provider: CurrentOwnerAuthority,
    clock) -> RecoveryInspection

restore_signed_backup(source: SignedBackupSource, destination: BundleStore,
    bundle_digest: str, attestation_bytes: bytes, *, incident_id: str,
    authority_provider: CurrentOwnerAuthority, clock) -> RecoveryResult
```

Exact classes/same actual clock required. No caller-supplied approval facts, StoredBundle, inspection reuse token, signed-key loader or implicit home/root. Source primary may be damaged or missing; source backup/object roots must exist and be safe. Both original roots are supplied so destination cannot overlap either. All roots must be distinct under lexical/real/identity checks, including containment; links/reparse/invalid identity are refused.

`RecoveryInspection`: scope=`archive_identity_only`, bundle_kind/digest/input_archive_digest/request_sha256/attestation_sha256/verified_at, source_backup_exact=True; no payload or reusable authority escapes. revocation_status=UNSUPPORTED; source_authenticated/research_selection_ready/current_use_eligible/execution_ready=False.

`RecoveryResult`: status=`EXACT_ARCHIVE_RESTORED`, incident_id, bundle_kind/digest/input_archive_digest/attestation_sha256, recovery_artifact_digest, verified_at, destination_backup_verified=True, signature_backup_verified=True, original_store_modified=False. Same non-operational flags; automatic_operational_recovery_supported=False. It reports this completed observation, not a lease/token. On refusal raise fixed `BUNDLE_RECOVERY_*` or retained bounded existing diagnostic; never report completed restoration. Already copied immutable evidence survives later failure and an exact retry may resume.

## Exact source verification

1. Strict attestation parse/target equality and actual owner/provider observation; reuse the existing `bundle_auth._authority` identity/time/code check internally. No private key and no app-supplied public trust.
2. Derive exact raw/verified manifest bytes from signed request, match source limits.policy_sha256/object policy and actual file references. Signed bytes/metadata—not damaged catalog/head—select the target.
3. Pin explicit backup directory/object directories/objects.lock identities. POSIX held directory fds and the existing Windows directory pin primitive keep path checks explicit. Use the real EvidenceObjectStore.read for each known reference; no automatic initialize/stage/adopt.
4. Compute manifest references with preview_payload of signed exact manifest bytes. Read raw and optional verified manifest objects, then every signed file; empty only length0/SHA(empty)/None. Recompute preview/reference, payload hashes and request equality. Repeat complete source graph reading across actual owner re-observation and compare snapshots.
5. Finish crypto/digest work before final clock; retain original observation timestamps, <=30s and unexpired current code/key context. Return an internal immutable snapshot; public inspection exposes facts only.

Do not keep EvidenceObjectStore's non-reentrant process lock while calling another read or destination operation. Per-read object locks are released. Held path identities are rechecked throughout; no source catalog/head or primary file is read/adopted. Root presence/path metadata checks do not validate primary contents.

## Destination and signature artifact

The destination is an already explicitly provisioned actual BundleStore with the same evidence storage/object policy. Recovery does not call provision_empty, initialize_reviewed_head, compare_and_set directly, or change routes.

Construct a deterministic separate RAW_ARCHIVED artifact with two exact files:

- `attestation`: original attestation bytes, original_name=`attestation.json`, role=`other_input`.
- `record`: strict canonical recovery commitment document, original_name=`recovery-record.json`, role=`other_input`.

Artifact run ID=`recovery-` + attestation document digest; revision ID=`incident-` + incident_id; attempt ID=incident_id. incident_id uses generated-ID grammar `[a-z][a-z0-9_-]{0,63}`. parent_bundle_sha256 is the restored target digest. expected_candidates=None, inventory_complete=True; this is an auxiliary archive, never a complete evaluated research family. All files use real destination preview refs and current exact storage policy.

Record schema1/kind=`exact-signed-archive-recovery`, scope=`archive_identity_only`, incident_id, bundle_kind, bundle_digest, input_archive_digest, attestation_sha256, request_sha256, file_set_sha256, storage_policy_sha256. No mutable wall-clock in this deterministic commitment: actual verification time is returned separately and may be logged by the caller. The record commits content and method, not independent proof of when recovery happened or permission to operate.

Preflight the entire raw + optional verified + auxiliary archive operation using existing destination read-only catalog/object admission primitives under its real session lock. Predict exact row sizes and deduplicated object inventory including backups. Refuse budget/ID/graph conflicts before any stage. This is not capacity reservation against unrelated writers; normal commit repeats checks.

Release that lock and revalidate the original source observations before calling archive_raw/commit_verified/archive_raw for the auxiliary artifact. The source-inspection and prewrite transaction must fit its original 30-second observation lifetime. Existing store methods take their own non-reentrant lock and perform actual catalog/head/backup commits. Copying immutable archival evidence may take longer; it grants no current operational authority.

After all copy commits, start a separate final validation transaction with a fresh actual provider observation (`final_first`) using the same provider, retaining its code/key/head/clock pins across phases. Then read the exact auxiliary artifact, authenticate the restored target with actual `authenticate_bundle_attestation` (which rereads complete primary/backup raw and target graphs), and reread the auxiliary backup. Retain `final_first` through all of that heavy work and the final bounded clock/expiry/date checks. A 31-second final auxiliary read must fail even if a later owner observation is fresh. A long copy can succeed only after the new final transaction actually rereads and verifies all destination evidence; relabeling the old source snapshot with a fresh time is forbidden.

An interrupted call may have completed only raw or verified or auxiliary writes. Preserve those records and never truncate/reanchor. Retry with the same incident/document/bytes is deterministic; another document/incident is another auxiliary artifact. Signature artifact must fit the signed destination policy; failure cannot weaken that policy or report signature backup complete.

## Tests and boundary

Use actual temporary owner logs/key fixtures, actual source/destination BundleStore and backups. Positive setup signs the final B2 code hash before corruption. Cases: damaged/missing primary catalog/head but exact backup succeeds; raw failed/empty originals; source one-byte/manifest/ref/policy mismatch; wrong key/code/domain/expiry/stale provider; no preprovision destination; overlap/containment/replaced roots or locks; source/destination lock order; ID collision; whole-batch budget refusal before stage; crash/CAS/readback/final-auth failure; exact retry; original tree bytes and old head unchanged; actual signature artifact backup readback; no trading/evaluation/arm/provision calls.

Persistent quarantine/current selection/route changes remain outside B2a. B1b-2's future actual sealed-selection API includes audit_logical_ids and normalized signing-identity revocations; it still does not release durable quarantine or operational use. No default revoked=False/quarantined=False. Existing floor/risk policies unchanged. No actual user home/key/API/orders and no public private-data output.
