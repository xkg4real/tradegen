# PR5 B1a — preserved research inputs and separate verified bundles

2026-11-13. This draft records the B1a implementation and development checks. The combined format/receipt/storage unit run has completed; whole-B1a adapter/operator integration and delivery status remain pending. B1a adds offline archival and actual historical re-evaluation for fixed v1 and fixed carry v2 study families. It does not authenticate a manifest, approve a strategy, recover damaged evidence or activate trading.

## Observable behavior

The explicit input descriptor identifies the plan, profile, original source receipts, program bytes, capture-source manifest and listed source files, prior research, registration commitment, optional reports, and a bounded capture directory. The adapter snapshots the observed files and inventory. Names are metadata, not storage paths. Empty and malformed files are retained as exact bytes; missing, refused, changed and over-limit inputs remain explicit observations. An invalid plan leaves expected candidates unknown rather than replacing them with an empty successful family.

`finalize` first commits and backs up this `RAW_ARCHIVED` snapshot. Only after that does it reopen the catalog-backed originals and run complete input, receipt, source and actual A0b family validation. A well-recorded capture abort, incomplete capture, malformed input or calculation exception does not become a successful research result. The archived originals remain available with a bounded diagnostic. Existing end-error records do not contain every failed response or its timestamp; missing historical evidence is not synthesized or re-downloaded as an original. A diagnostic is not the separate authoritative failed-evaluation outcome that later PR5 work requires. If the inventory envelope or storage admission cannot be completed, the operation does not claim a complete archive; working originals are not deleted or reduced to fit.

Successful validation produces a separate immutable `VERIFIED_UNAPPROVED` revision linked to the raw archive digest. It retains every original input and every expected candidate, including numerically rejected candidates, and adds the actual evaluation record. The raw manifest is not edited. Run/revision identities cannot be reused for different bytes, including across raw and verified kinds. A new collection, calculation or changed included report requires a new revision.

`evaluate` accepts a verified bundle digest and reads the complete primary and backup graphs plus its raw dependency. It takes no working-input paths. The adapter validates the saved inputs again, invokes the actual evaluator at the recorded historical evaluation time, and compares the reconstructed manifest and result bytes. It does not deserialize a result into an issued evaluator token. Installed source compatibility is still checked; archived source is neither automatically executed nor substituted for current source hashes. The historical evaluation time is not a current approval time.

## Storage publication and backup

- Objects are immutable and addressed by content. Staging may leave an orphan, pending object or partially copied final name. Their existence does not publish an archive.
- A `PRIMARY_COMMITTED` catalog row binds the kind, identity, manifest reference, full file-list digest and storage policy. The whole target graph is checked before catalog append, then the independent head's successor verifier checks it again. Append/fsync, head compare-and-set and head readback must complete before the local artifact is published.
- Backup writes copy the exact manifest and payload bytes into independent destination objects, without primary-file hardlinks or symlinks. Full destination readback precedes a separate `BACKUP_VERIFIED` row and head confirmation. Primary and backup are separate commits; there is no claim that both locations change atomically.
- Backup failure returns no successful completion receipt. A committed primary can be inspected as unbacked through the explicit storage API. A byte-identical retry validates the retained primary and resumes the backup stage. CAS or readback response loss is resolved by reading the catalog/head; retries do not duplicate an already confirmed event. Partial objects, contradictory catalog/head states and damaged copies are preserved and refused, never overwritten, truncated, adopted or automatically repaired.
- Every consumer checks the shared catalog chain, but object checks are limited to the requested bundle and its raw dependency. An unrelated damaged object does not block a healthy study's read or new commit. Corruption of the common catalog/head affects their shared dependency and is not bypassed. `BundleStore.inspect` returns historical catalog metadata, not present usability; the CLI `inspect` additionally performs a backed graph read.

The store pins roots, session lock, catalog, object directories and independent-head context. Link restrictions, exact bytes, quotas and temporary-copy peak admission remain enforced. Quota admission, I/O failure and object-integrity refusal have separate diagnostics. Lower-level I/O wrappers may hide the original operating-system error, so an I/O refusal is not asserted to prove either full-disk exhaustion or evidence corruption.

These checks do not prove market provenance, prior public registration, completeness of unobserved historical attempts, physical backup separation, or protection against coherent rollback of both controlled roots. File-name visibility is not atomic publication. Windows power-loss durability and device-specific behavior have not been established by these Linux development checks.

## Explicit operator setup and CLI

Both storage roots must already exist as empty, real, separate local directories outside the repository and state home. The operator chooses paths and storage limits explicitly. There is no default account/home/key path, automatic parent creation or selection of a synchronized working directory. Known OneDrive names are refused, which is not proof against every synchronization tool.

Only `tools.owner.research_bundle provision` prepares the empty stores and explicitly initializes their independent storage genesis. Runtime finalize/read/evaluate never initializes a missing head. Existing or interrupted roots are refused rather than reinitialized. **This setup is not electronic signing or owner approval of research.**

The following are command templates; replace each quoted placeholder with the specified absolute path or value. Use the same limits descriptor and head name for subsequent access.

```text
python -m tools.owner.research_bundle provision --sealed-root "<ABS_SEALED_ROOT>" --backup-root "<ABS_BACKUP_ROOT>" --head-name research-head --limits "<ABS_LIMITS_JSON>"
python -m execution_launch.research_bundle finalize --sealed-root "<ABS_SEALED_ROOT>" --backup-root "<ABS_BACKUP_ROOT>" --head-name research-head --limits "<ABS_LIMITS_JSON>" --inputs "<ABS_INPUTS_JSON>" --run-id research-run --raw-revision raw-v1 --verified-revision verified-v1 --attempt-id attempt-1 --evaluated-at "<AWARE_ISO8601_EVALUATION_TIME>"
python -m execution_launch.research_bundle inspect --sealed-root "<ABS_SEALED_ROOT>" --backup-root "<ABS_BACKUP_ROOT>" --head-name research-head --limits "<ABS_LIMITS_JSON>" --digest "<BUNDLE_DIGEST>"
python -m execution_launch.research_bundle evaluate --sealed-root "<ABS_SEALED_ROOT>" --backup-root "<ABS_BACKUP_ROOT>" --head-name research-head --limits "<ABS_LIMITS_JSON>" --digest "<VERIFIED_BUNDLE_DIGEST>"
```

The inputs JSON has exactly `schema_version: 1`, `files`, and `captures_directory`. Each explicit file entry has `role`, absolute `path`, `source_name`, and `required`. Required singleton roles are `plan`, `profile`, `registration_commitment`, `source_receipts`, `program_source`, `capture_source_manifest`, and `prior_research`; include the actual `source_file` list and optional `report` entries. `source_name` is the repository-relative name for `source_file`, otherwise null. The bounded directory inventory supplies the complete capture family. The adapter creates the evaluation record after actual evaluation; callers do not supply it as a pre-issued result.

The limits JSON has exactly `format_limits`, `object_limits`, `primary_budget`, `backup_budget`, `max_catalog_bytes`, and `max_catalog_records`. Format limits bound manifest/file/aggregate/candidate/name sizes. Object limits contain `chunk_bytes`, `max_payload_bytes`, `max_chunks`, and `max_manifest_bytes`; each object budget has `max_bytes` and `max_objects`, including temporary-copy peak. Catalog capacity is bounded separately. Limits are part of the immutable storage policy; silently changing them is not a supported migration.

## Validation record

The storage developer's final direct run passed **23 of 23** tests in **3.180 seconds** using KEYLESS variables and isolated temporary roots. These cover malformed/empty originals, exact independent backup copies, immutable raw-to-verified derivation, complete candidate retention, ID reuse refusal, backup retry, CAS/readback response loss, pending/partial objects, catalog/head rollback, root and lock replacement, competing OS locks, zero inode identity, bounded diagnostics, and graph-specific corruption. Temporary-copy peak was exercised immediately below, at and above its exact boundary; catalog event capacity was likewise checked. Compilation and whitespace checks passed.

An independent reviewer separately exercised **16 selected storage cases** successfully and checked the head-name collision, exact mapping snapshot and publication boundaries. These counts overlap and must not be added. The current checks make no Windows, iPhone or real-source execution claim.

The parent session subsequently completed the combined format/receipt/storage unit run: **62 PASS / 0 FAIL / 0 NOT_RUN**, **6.749 seconds**. Its tracked Python/YAML fingerprint was `890a6b9c229e8922a53b7dcf99e1b35ff2f72b5ee1c61ae11adddabd38bf34ab`. Nineteen KEYLESS variables were set; tracked source and protected-home metadata remained unchanged; QA bytes were restored. Evidence artifacts are `bundle-storage-dev3-summary.json` and `bundle-storage-dev3-rows.json`. The adapter/operator files were still untracked development and were not included in that closure, so this is unit development evidence. Whole-B1a integration, complete regression and delivery checks remain pending.

## Remaining boundaries

B1b manifest-specific authentication and independent signer integration, trusted exact recovery, reconstruction/recollection workflows, all-prior-attempt lineage and authoritative failure issuance remain separate work. Telegram/WebAuthn registration, device recovery and approval application are absent. B1a returns `BUNDLE_MANIFEST_AUTHENTICATION_REQUIRED`; source/manifest authentication and execution readiness remain false. Existing code, limit, research and trading-activation scopes are not merged. No account access, real key, source API, notification, arming or order is part of these commands.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
