# Committed startup retention — exact implementation card

2026-11-13 · base `19f6775` (main PR #56) · proposed tree `/workspace/tradegen-committed-startup-1113`.

This card defines the first vertical implementation: **retain exact inputs → actual guard commit → retain completion → reconstruct new actual objects → classify durable/current state → actual Controller/DryRun startup reconciliation**. No source/test changes or runtime checks have been made for this card. Existing principal/peak/daily loss policies remain unchanged. Controlled operation, source-completeness issuance, scheduling, historical gap repair, order creation and automatic liquidation are excluded.

## 1. Scope and existing dependencies

Reuse `guard_capture_archive.read_guard_capture_packet/replay_guard_capture_archive`, existing `BundleStore.archive_raw/read_raw`, `commit_continuous_guard/classify_restart`, `CommittedAccountProvider`, actual `Controller`, and the Runner rehearsal boundary. Do not re-encode/store all capture receipts again or create a filesystem writer/lock/head engine.

`replay_guard_capture_archive` is historical: actual retained bytes are replayed at `staged.observed_at`. This is independent of original `package['now']`, current startup time, and record-writing time. Retained owner/coverage values remain historical assertions. Local correspondence to a committed transaction is not source authenticity or current owner approval.

RAW `parent_bundle_sha256` is descriptive: BundleStore does **not** automatically traverse RAW parents. The new adapter explicitly reads and verifies **completion → input → capture**, each with actual primary, backup, catalog and retained head checks. Unknown unrelated object corruption is not silently promoted into a dependency; the actual catalog/anchor still has to be valid.

## 2. Exact package and digest meanings

The actual guard package is an exact `dict`, with no extra or missing keys:

| Key | Exact class | Reconstruction source |
| --- | --- | --- |
| `baseline_before` | `execution_accounts.baseline.BaselineState` | Actual capture packet `previous`, verified by its existing codec |
| `policy` | `execution_control.risk.RiskPolicy` | New strict small input record |
| `owner_before`, `owner_after` | `continuous_guard.OwnerContextClaim` | New strict small input record, historical only |
| `path` | `execution_accounts.continuous.ContinuousPath` | Actual historical capture-material replay |
| `valuation_inputs` | `continuous_guard.ValuationInputs` | Same actual material replay |
| `account_capture` | `continuous_guard.AccountCaptureInputs` | Same actual material replay |
| `coverage` | `execution_accounts.continuous.VerifiedCoverage` | Same retained material; no new issuer invocation |
| `interval` | `execution_accounts.baseline.BaselineInterval` | Same actual material replay |
| `now` | aware exact `datetime` | Record `evaluated_at`, preserved original value |

The actual `_PACKAGE_KEYS` contract remains unchanged. Separate values must never be aliased:

- `capture_packet_sha256`: existing capture packet domain digest.
- `capture_material_sha256`: actual I3a historical replay output digest.
- `package_sha256`: existing `committed_account._package_digest(package)` over the sorted complete key/value tuple; **includes `now`**.
- `input_sha256`: actual `continuous_guard._input_digest(expected_guard_head, ...all original inputs...)`; **excludes `now`**, as the existing commit contract does.
- `record_sha256`: the new domain-separated exact canonical metadata bytes, retaining representation details such as Decimal sign/scale. It is not interchangeable with either legacy digest.
- `transaction_id`: actual guard transaction binding, only known from actual commit/verified PREPARE; never an input-record identifier or an authorization token.

Admission snapshots exact declared attributes and exact types before invoking generic copying/serialization. No arbitrary object hooks, import/eval/pickle, global codec-registry mutation, or permissive subclass acceptance.

## 3. Pure format — `execution_launch/guard_generation_format.py`

Constants:

```python
SCHEMA_VERSION = 1
INPUT_DOMAIN = b'tradegen-guard-generation-input/1\n'
COMPLETION_DOMAIN = b'tradegen-guard-generation-completion/1\n'
```

`GenerationFormatLimits` is frozen, slotted, keyword-only. Exact positive integers only; defaults are hard ceilings: `max_record_bytes=65536`, `max_nodes=2048`, `max_text_bytes=16384`, `max_depth=12`. `DEFAULT_LIMITS`. Capture limits remain the existing `CaptureFormatLimits`; no increase to their 64MiB packet/raw aggregate, 2000 receipts or other bounds. Startup also has a separate fixed maximum of 1024 local orders or captured broker-order rows per operation; exceedance refuses before cancellation/status dispatch.

Closed records, frozen/slotted/keyword-only:

```python
class GuardInputRecord:
    schema_version: int                 # exactly 1
    kind: str                           # exactly 'GUARD_INPUT'
    replay_revision: str                # exactly existing 'guard-capture-material-v1'
    capture_archive_digest: str
    capture_packet_sha256: str
    capture_material_sha256: str
    previous_state_sha256: str
    expected_guard_head: str
    expected_baseline_head: str
    expected_control_head: str
    package_sha256: str
    input_sha256: str
    policy: RiskPolicy                   # repr=False
    owner_before: OwnerContextClaim      # repr=False
    owner_after: OwnerContextClaim       # repr=False
    evaluated_at: datetime               # original package['now']

class GuardCompletionRecord:
    schema_version: int                 # exactly 1
    kind: str                           # exactly 'GUARD_COMPLETION'
    input_archive_digest: str
    input_record_sha256: str
    package_sha256: str
    input_sha256: str
    receipt: GuardCommitReceipt          # exact six original fields below
    completion_head: str                # actual unique COMPLETE row hash
    observed_control_head: str           # actual verified tail at recording observation
    recorded_at: datetime                # actual recording observation, not account asof

input_bytes(record, *, limits=DEFAULT_LIMITS) -> bytes
parse_input(raw: bytes, *, limits=DEFAULT_LIMITS) -> GuardInputRecord
input_digest(record, *, limits=DEFAULT_LIMITS) -> str
completion_bytes(record, *, limits=DEFAULT_LIMITS) -> bytes
parse_completion(raw: bytes, *, limits=DEFAULT_LIMITS) -> GuardCompletionRecord
completion_digest(record, *, limits=DEFAULT_LIMITS) -> str
```

All hash fields are exactly 64 lowercase hexadecimal characters; bool is never an int. Records use canonical sorted compact ASCII JSON. Input canonical object keys are the complete field list above; completion likewise. No optional omitted/defaulted fields. Digest fields do not contain the record's own digest, avoiding circular hashes.

Small nested schemas are closed and complete:

- `RiskPolicy`: `version`, `initial_equity`, `drawdown_activation_equity`, `positive_profit_loss_fraction`, `peak_drawdown_fraction`, `zero_profit_day_target_fraction`, `first_day_loss_budget`, `zero_profit_day_loss_budget`, `valuation_convention`, `daily_loss_convention`, `recovery_condition`. Optional budgets/condition are explicit null.
- `RecoveryCondition`: `cutoff_seconds`, `timezone`, `reference`; use the existing supported-condition validation, not a new policy.
- `OwnerContextClaim`: `owner_head_sha256`, `code_sha256`, `code_approval_sha256`, `signed_floor_krw`, `signed_daily_loss_krw`, `observed_at`, `source_sha256`. Existing `_owner` semantic constraints still apply. This does not authenticate the claim.
- `GuardCommitReceipt`: `transaction_id`, `guard_head`, `baseline_head`, `control_head`, `permanently_halted`, `replayed`. The last two are exact bool. Receipt has **no timestamp or COMPLETE field**; do not invent either inside it.

Reuse the reviewed capture scalar tag conventions/helpers without adding classes to its global `_SCHEMAS`: Decimal `{'$':'decimal','v':[sign,digits,exponent]}` (finite, ≤512 digits, exponent ±512), datetime `{'$':'datetime','v':canonical_UTC_ISO}`. Nested records have their exact named field objects; constructor/encode/decode roundtrip must preserve bytes. Original numeric scale/signed zero and original time instant survive. Existing semantic validators may impose narrower number bounds. Pre-scan bytes/depth/nodes/text before JSON allocation; reject duplicates, raw JSON float/nonfinite, unknown keys/tags, malformed UTF-8/ASCII, overlong scalars, invalid dates and noncanonical encodings. The new metadata pre-scan enforces these own small bounds directly; GenerationFormatLimits is not a CaptureFormatLimits and must not be passed to capture._scan. Reusing capture Decimal/datetime scalar helpers may use a fixed bounded CaptureFormatLimits internally, without expanding the metadata parser limits or adding schemas. Existing raw capture bytes are referenced, not normalized.

Errors are fixed `GuardGenerationFormatError(ValueError)`: `GENERATION_FORMAT_INVALID`, `GENERATION_LIMITS_INVALID`, `GENERATION_RESOURCE_LIMIT`, `GENERATION_DIGEST_MISMATCH`. Do not include private data or underlying exception strings.

## 4. Actual archive adapter — `execution_launch/guard_generation_archive.py`

The following data-only returned wrappers are frozen/keyword-only. Hidden nested records/packages are detached snapshots, not issuer tokens:

```python
class RetainedGuardInput:
    archive_digest: str
    record_sha256: str
    record: GuardInputRecord             # repr=False
    package: dict                        # repr=False; exact reconstructed package

class RetainedGuardCompletion:
    archive_digest: str
    record_sha256: str
    record: GuardCompletionRecord        # repr=False
    retained_input: RetainedGuardInput   # repr=False

retain_guard_input(store, capture_archive_digest, package, *,
    expected_guard_head, expected_baseline_head, expected_control_head,
    limits=DEFAULT_LIMITS, capture_limits=CAPTURE_DEFAULT_LIMITS) -> RetainedGuardInput
read_guard_input(store, input_archive_digest, *,
    limits=DEFAULT_LIMITS, capture_limits=CAPTURE_DEFAULT_LIMITS) -> RetainedGuardInput
record_guard_completion(store, input_archive_digest, receipt, *,
    journal, guard_store, guard_head, baseline_store, baseline_head, clock,
    limits=DEFAULT_LIMITS, capture_limits=CAPTURE_DEFAULT_LIMITS) -> RetainedGuardCompletion
read_guard_completion(store, completion_archive_digest, *, expected_input_archive_digest,
    limits=DEFAULT_LIMITS, capture_limits=CAPTURE_DEFAULT_LIMITS) -> RetainedGuardCompletion
```

`store` must be exact actual BundleStore; `journal` exact Journal and checkpoint stores exact existing types. Required head objects remain the same explicit integrations; no new persisted head is initialized/adopted. Both wrappers expose constant properties `source_authenticated=False`, `current_freshness_verified=False`, `execution_ready=False`.

Input retention loads the actual capture packet and actual historical replay, reconstructs the six material/baseline fields, copies only the three original policy/owner fields and original `now`, then compares the entire candidate package against the supplied exact package by existing whole-package digest and closed representation where applicable. The supplied package cannot replace accounts/path/coverage with equal-looking fabricated output. Re-read original actual graph after heavy replay and record publication. Mutation/refusal preserves prior records.

Each new raw archive has **exactly one generated payload**:

| Meaning | logical ID / original name | run and attempt ID | revision | parent |
| --- | --- | --- | --- | --- |
| Input | `guard-input` / `guard-input.json` | `guard-input-` + full input record digest | `guard-input-v1` | exact capture archive digest |
| Completion | `guard-completion` / `guard-completion.json` | `guard-completion-` + full completion record digest | `guard-completion-v1` | exact input archive digest |

Manifest is actual `RAW_ARCHIVED`, schema 1, actual store/object policy hashes, `expected_candidates=None`, `inventory_complete=True`; file role `other_input`, required True, source/study None; exactly matching COLLECTED observation. It is complete metadata inventory, not research eligibility or source coverage. Preflight the actual manifest/ref/one-file length **before** loading payload bytes. Reuse actual preview_payload/archive_raw/readback with require_backup=True and compare complete manifest+bytes. No original private filenames become paths.

Read paths explicitly verify the parent graph chain, record/domain hashes, reference identities, original material replay, all legacy digests, and actual store configuration/head before returning. Do not rely on a supplied archive receipt or arbitrary `backup_verified=True`. Three linked metadata/capture graphs are the fixed traversal depth; do not recursively follow arbitrary RAW chains. `read_guard_completion` has no Journal/head inputs and therefore verifies retained archive claims only; it never certifies a completed control transaction. During actual startup or completion-record finalization, compare saved transaction/package/input/guard-head/baseline-head/COMPLETE/receipt-prefix fields with actual inspect_committed. In that same actual Transaction, require saved observed_control_head to identify a verified prefix at or after the receipt prefix, and require its row UTC <= saved recorded_at <= actual current clock. A benign later suffix is allowed: saved observed tail need not equal the current tail. Neither a genuine embedded receipt nor a valid outer hash excuses forged completion metadata.

Completion recording builds a fresh actual provider from the just-reloaded input plus supplied receipt and same integration objects, invokes its new actual `inspect_committed` under a caller-owned Journal transaction, and compares every input/receipt binding. The ordinary startup orchestration supplies the **actual commit-returned** receipt; independently calling this archive function with a matching receipt proves durable correspondence only, not how a caller obtained the receipt or its replay flag. It issues no permit. Retain original receipt unchanged, actual COMPLETE hash and current tail separately. Sample aware monotonic recording time after that observation; release Journal lock before BundleStore writes. After complete write/readback, repeat actual durable inspection under a new Journal transaction and final clock monotonicity check. No fake fresh account read and no owner lookup at historical time.

Input identity has no archive-write clock, making exact retries identical. Completion identity includes the complete original receipt and recording observation; changed replay flag/prefix/recording observation produces a new immutable record. Exact identical completion bytes may use existing store retry. Lost first receipts are never recreated by guessing their tail or recording time.

Archive errors: fixed `GuardGenerationArchiveError(ValueError)` with `GENERATION_ARCHIVE_INPUT_INVALID`, `GENERATION_ARCHIVE_RESOURCE_LIMIT`, `GENERATION_ARCHIVE_NOT_PUBLISHED`, `GENERATION_ARCHIVE_WRAPPER_INVALID`, `GENERATION_ARCHIVE_BINDING_MISMATCH`, `GENERATION_ARCHIVE_READBACK_MISMATCH`, `GENERATION_ARCHIVE_DURABLE_REFUSED`, `GENERATION_ARCHIVE_CLOCK_INVALID`, `GENERATION_ARCHIVE_CLOCK_ROLLBACK`, `GENERATION_ARCHIVE_STORE_REFUSED`. Preserve original stored evidence on any failure. Resource refusals must not be mislabeled as corrupt pins; private OS text is never returned.

## 5. Narrow existing-provider addition — `committed_account.py`

Parent and independent reviewer agreed this seam is necessary: existing `read` may raise on stale baseline reconciliation **before its final reread**. Catching that exception as verified restore would skip final integrity checks. Calling read with a fabricated historical current time is also incorrect.

```python
class CommittedGenerationInspection:     # frozen, kw-only
    transaction_id: str
    guard_head: str
    baseline_head: str
    completion_head: str
    receipt_control_head: str
    observed_control_head: str
    package_sha256: str
    input_sha256: str
    asof: datetime                       # original baseline.asof
    evaluated_at: datetime               # exact package['now']/guard.recorded_at
    # property execution_ready=False; no account/risk/current-owner object

CommittedAccountProvider.inspect_committed(*, now, transaction) -> CommittedGenerationInspection
```

Take one private generation reference at entry, check actual active/thread-bound/same-Journal Transaction, `_configuration/_still/_events/_states/_binding/_history`, exact `guard.recorded_at == package['now'] <= now`, and original baseline binding. Repeat actual stores/heads and events before returning and run final `_still`. No partial private-generation reads in the new archive/startup module. Reuse a private common durable portion with existing `read` if this reduces duplication; retain its full legacy checks and final readback. Never turn historical inspection into an AccountObservation, RiskResult, current freshness, permit, cached verifier success or public lease. No advance/commit/CAS/snapshot/nested Journal/owner calls. Existing fixed `COMMITTED_ACCOUNT_*` refusals remain applicable.

### Existing-only Journal integration

Root approved `Journal(root=None, *, require_existing=False)` with an immutable private flag and read-only `requires_existing` property. Default False preserves all existing bootstrap bytes/behavior. True requires existing root/lock/journal/anchor throughout transaction/load/append and never creates a missing pair. Startup construction and completion recording require the exact actual Journal with `requires_existing is True`; the same strict object is passed to Controller and guard commit. Provisioning remains an explicit separate operator operation, followed by `Journal(root=actual_control_directory, require_existing=True)` reopening. A snapshot preflight alone does not close a deletion-before-transaction race and is not the no-initialization guarantee. The Journal owner adds its focused regression/guard updates; this is no new writer engine or authority.

### Restrictive original-time binding inside the existing commit lock

Root approved one optional addition to `commit_continuous_guard(..., expected_evaluated_at=None)`. When None, all existing callers and duplicate-retry semantics remain unchanged. When supplied, require an exact aware datetime and, inside the actual Journal lock after actual plan recomputation but before any write, require `expected_evaluated_at == package['now'] == plan.proposed_checkpoint.recorded_at`. Invalid input or mismatch has a fixed GUARD diagnostic chosen by the commit owner. Startup always passes the original retained record.evaluated_at. The argument is an extra restriction, not authority. This closes the race where a different evaluation-time successor appears after external startup preflight; preflight alone is insufficient. Only the separately assigned commit owner edits that module.

## 6. Startup orchestration — `execution_launch/committed_startup.py`

```python
class CommittedStartup:
    def __init__(self, *, archive_store, journal, guard_store, guard_head,
                 baseline_store, baseline_head, profile, adapters,
                 isolated_state_root, clock, session_provider=None,
                 limits=DEFAULT_LIMITS, capture_limits=CAPTURE_DEFAULT_LIMITS): ...
    def commit_input(self, input_archive_digest) -> RetainedGuardCompletion: ...
    def inspect(self, input_archive_digest, completion_archive_digest=None) -> StartupInspection: ...
    def reconcile(self, input_archive_digest, completion_archive_digest) -> StartupResult: ...
```

Constructor performs only dependency/configuration admission; no clock/file writes/provision/seed/source fetch/threads. It is exclusively rehearsal; no mode/allow bool can select controlled behavior. Every adapter must be exact DryRunAdapter. Exact profile policy must agree with retained package policy. Journal and both checkpoint stores use the same explicit isolated state root; existing Runner rehearsal checks additionally require it to be the actual configured state root and outside the actual default live home. Archive roots/head must retain existing path checks and be separated from runtime state roots. Do not open/read any actual owner home in development.

`commit_input` reloads the already retained input, performs the original-time/pending binding preflight described below (including actual proposed recorded_at equality when present), samples actual clock, invokes existing `commit_continuous_guard` outside all other locks with `expected_evaluated_at=retained.record.evaluated_at`, then passes its actual receipt into `record_guard_completion`. It does not manually append PREPARE/COMPLETE, call baseline advance, publish a provider, or dispatch. Input survives all failures; fixed failure plus known input archive ID lets the caller inspect/retry. Existing exact pending/CONSISTENT commit retry semantics remain; no auto repair/truncate/adopt. An inspection itself never calls commit, including CONSISTENT commit, because that is not a read-only API.

`StartupInspection` is frozen/keyword-only:

```python
class StartupInspection:
    input_archive_digest: str
    completion_archive_digest: str | None
    durable_status: str                  # exact existing classifier statuses below
    current_status: str                  # NOT_CHECKED, FRESH, STALE, REFUSED
    reason: str                         # fixed code or empty
    transaction_id: str | None
    observed_control_head: str | None
    asof: datetime                       # original account interval end
    inspected_at: datetime               # actual final observation
    # execution_ready=False, source_authenticated=False
```

Durable status is existing `FRESH` (retained input not yet committed), `CONSISTENT`, `PENDING_GUARD_BEFORE_BASELINE`, `PENDING_CROSS_STORE`, `PENDING_FINALIZATION`, `DIVERGENCE`, or `REFUSED`. Explain that durable FRESH is **not** current account FRESH. `current_status=NOT_CHECKED` unless there is an actual complete, bound result. Missing completion record with actual CONSISTENT returns `NOT_CHECKED/STARTUP_COMPLETION_RECORD_REQUIRED`; call `commit_input` explicitly to obtain/retain the actual replay receipt. Unknown/torn states refuse, with no mutation.

Inspection uses actual archive reads and actual Journal transaction/classify_restart with separately retained heads. The actual PREPARE must also match this input's computed input/owner/path/control binding, path endpoints and expected predecessor hashes; classifier status alone does not bind an arbitrary package to a pending transaction. For pending states, reuse the existing pure plan/transition checks with the original package evaluation time and actual retained old-or-proposed guard checkpoint when available; this is historical recomputation only. If the actual proposed/successor checkpoint already exists, require its recorded_at == retained record.evaluated_at == package.now before any pending finalization or CONSISTENT retry. The old guard predecessor has its own earlier time and is not subject to this equality. Existing duplicate-plan input/transaction equality alone is insufficient because input_sha excludes now and that branch returns the already stored successor. If the required checkpoint is unavailable, refuse rather than reconstruct its authority from a balance. When a completion record exists, reconstruct an actual provider and invoke its new historical inspection at actual current time. Final actual states/heads/Journal and archive/configuration checks precede the last clock sample.

`current_status=FRESH` additionally requires a successful **actual provider.read(now=current, transaction=actual_tx)**, followed by the final dependency/time checks. It describes current local account reconciliation, not current owner authentication or source authenticity. After successful separate durable inspection, STALE is classified only from explicit existing baseline/account age conditions; future/clock rollback, crossed Seoul date/required 22:00 boundary or other inconsistency is REFUSED with the specific fixed reason. Existing `risk_baseline`/required-cutoff logic may be reused for this diagnosis. Never recognize only generic `COMMITTED_ACCOUNT_EVIDENCE_REFUSED` as a freshness success. Do not invent a new now-minus-30-seconds limit for both owner claims: `owner_before` retains its existing original path.start bracket; the endpoint `owner_after` current-age check remains the actual Controller completion check. Real owner/code/effective-limit authentication occurs in reconcile.

`reconcile` performs a fresh inspection; stale/pending/refused returns a blocked result with no broker status or cancel request. For a completed/current input it constructs exactly one actual provider/Controller/Runner tuple, pins all dependency identities and the retained input/completion binding, and retains that tuple for repeated calls with the **same** binding. Different binding on the same startup object refuses; PR56 explicit successor publication remains the existing separate API, not an implicit restore operation. Reconstructing another process uses a new actual tuple from the same retained original.

The Runner has no strategy/evidence and a fixed quote function which always raises `STARTUP_QUOTE_UNAVAILABLE`; startup never calls it or ticks a strategy. Use actual Runner(mode='rehearsal', same actual provider/controller/profile/root) to establish the existing complete boundary. Check its actual `_controller_boundary` before any side-effecting reconciliation and again after dependency work. A rehearsal string without exact dry adapters/root/identities is insufficient. The Controller clock is the same explicit callable. No positive authority/issued-session registry is fabricated.

Startup uses actual `Controller.read_committed_account` for fresh account/current owner checks; risk=None, no new risk snapshot or entry/research gate. It then applies the existing Runner reconciliation semantics: only its own namespace RESERVED may be locally cancelled; other active orders use actual Controller.reconcile. Before local cancellation, any captured broker-order evidence conflicting with the presumed never-sent reservation is a conflict, not permission to release it. Bounded preflight covers the complete relevant local/captured order lists before side effects. No automatic retry/send or liquidation is added.

`StartupResult` is frozen/keyword-only:

```python
class StartupResult:
    inspection: StartupInspection
    status: str                          # BLOCKED, RECONCILED, RECONCILED_OPEN
    reason: str                          # fixed code or empty
    attempted_reconciliations: int
    unresolved_client_ids: tuple[str, ...]
    external_order_ids: tuple[str, ...]
    open_client_ids: tuple[str, ...]
    holdings: tuple[tuple[str, str, Decimal], ...]  # venue, asset, exact quantity; repr=False
    final_control_head: str | None
    completed_at: datetime
    # execution_ready=False; source_authenticated=False
```

Success is determined by actual final durable states and the complete original endpoint AccountEvidence order/fill/position rows, **not** the count. Open/PARTIAL may be reconciled and still open; report RECONCILED_OPEN only when actual new `reconciled` rows and exact cumulative quantities/identities/fees agree. UNKNOWN/DISPATCHING, absent current reconciliation, conflicting/missing/external orders, contradictory fills or pending reservations remain BLOCKED with recorded IDs. Empty local orders do not prove an empty external account. Preserve unresolved quantities/state; do not clear a failure because no exception occurred.

After any status/fill writes, perform actual final Controller account/current owner read, actual durable provider inspection and actual Journal fold; require the same generation. Existing endpoint values do not change merely because a fill/reconciled suffix appeared. If the status result describes fills absent from this endpoint, retain uncertainty and require a real next capture/commit/publication. The last actual clock is sampled after all heavy checks; it must be monotonic and retain original observation age, policy day/cutoff and owner-completion watermark. Do not call Journal.snapshot/states inside an active transaction. Known final control tail and returned state rows must agree under the actual read transaction.

Startup fixed errors/reasons: `STARTUP_INPUT_INVALID`, `STARTUP_REHEARSAL_REQUIRED`, `STARTUP_BINDING_CHANGED`, `STARTUP_RESOURCE_LIMIT`, `STARTUP_CLOCK_INVALID`, `STARTUP_CLOCK_ROLLBACK`, `STARTUP_POLICY_BOUNDARY`, `STARTUP_STALE`, `STARTUP_DURABLE_REFUSED`, `STARTUP_COMPLETION_RECORD_REQUIRED`, `STARTUP_CURRENT_AUTHORITY_REFUSED`, `STARTUP_RECONCILIATION_REQUIRED`, `STARTUP_ORDER_CONFLICT`, `STARTUP_DEPENDENCY_CHANGED`, `STARTUP_QUOTE_UNAVAILABLE`. Existing fixed commit/archive diagnostics may be retained in a dedicated safe error chain; do not expose OS/private text or convert unrelated model errors to stale.

## 7. Lock/time, restart and scope invariants

- No archive/store/head lock is held while requesting a Journal transaction. Actual guard commit owns its existing Journal→head→checkpoint ordering. Archival pre/post work and provider publication/inspection use separate phases; no nested Journal transaction/snapshot and no second baseline advance/CAS.
- Read-only startup classification does not resume commits. Only explicit `commit_input` can run the existing exact package replay. Completed-but-unretained and partially committed states are reported distinctly. Partial/orphan records remain; no overwrite/truncate/latest-head adoption.
- Retained `evaluated_at`, capture `staged.observed_at`, receipt prefix, COMPLETE hash, recording time and current completion time remain distinct. Input integrity does not establish current freshness. Current unchanged owner head does not excuse changed effective limits/day/session.
- A long gap is blocked. Existing path/watermark ≤30 seconds, exact predecessor baseline, source stream continuity and genuine preinterval owner observation remain. No historical backfill by inventing current timestamps; no new reviewed anchor/floor relaxation in this unit.
- Source/coverage issuance remains absent. Raw GET evidence, local hashes/sequence, successful parsing or dataclasses do not prove all marks/fills/transfers/account changes. Existing ContinuousUpbitCandidateSource refusal and controlled-mode refusals stay in place.
- Scope is one complete restart retention/reconciliation vertical and repeated exact-binding checks. Coordinator scheduling, live transport status/cancel, new order dispatch, post-deadline management authority, source gaps, Windows live/power-failure validation and full anchor rollback resistance are not claimed.

## 8. Proposed ownership and meaningful verification

Root assigns after reading this card. Proposed split: format + pure tests; archive + actual archive tests; provider historical seam + its tests; startup module + independent startup integration tests; independent reviewer; root owns registry/guard/source-closure/runtime/commit. Existing capture/store formats stay unchanged. Startup composition imports new files, so root must check actual code/source closure and independent signer consistency instead of omitting new dependencies to preserve old hashes.

Use disposable actual signed owner logs, actual capture archive/I3a collector replay, actual checkpoint stores/independent heads/Journal/guard commit, actual new provider/Controller/Runner/DryRunAdapter. Source pages/path/coverage are explicitly synthetic. No fake positive verifier, issuer result or session registry insertion. No test runtime before joint source freeze.

Essential tests: strict Decimal/time/type/byte bounds and package-now vs input digest distinction; actual full input→commit→completion→new object restore; each interruption between retain/prepare/both store-head pairs/COMPLETE/result retention; actual replay receipt with later valid prefix; old record remains immutable; all dependency graph/backup corruption and exact wrapper mismatch; current stale/30s±1µs/day/cutoff/rollback after heavy work; generation/head mutation on final reread; read/inspect/publish add zero baseline advances/CAS and no nested Journal; pending inspection never commits; current actual owner/code/effective-limit refusal; true terminal/open/partial/UNKNOWN and external/contradictory broker-order cases; reserved namespace cancellation without fabricated remote success; actual status calls only exact dry adapters and bound isolated root; no strategy tick/order create/resend/market liquidation; source completeness and controlled refusal retained. Windows native and real API execution remain NOT_RUN.
