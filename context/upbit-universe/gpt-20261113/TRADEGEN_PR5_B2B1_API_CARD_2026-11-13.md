# PR5 B2b-1 — 사건 기록과 의존 연구 선발 보류 API

2026-11-13. 전용 tree `/workspace/tradegen-incidents-1113`, branch `gpt/research-incident-quarantine`, base `9944e6a`. 기존 tree·부모 CURRENT/LEDGER·QA 변경 금지. 범위는 실제 graph 등록/읽기 실패→독립 durable 사건+outbox→의존 연구 선발의 초기/최종 보류다. 복구·해제·삭제·매매·Telegram 전송·새 승인은 없다.

## 파일 단독 소유

- notion_revision: 이 카드, 새 `execution_launch/research_incident_monitor.py`, 새 `execution_launch/incident_aware_selection.py`, 새 `tests/launch_research_incident_monitor.py`, **부모가 허용한 `sealed_study_review.py`의 작은 private final-guard 추출**.
- protective_hold_design: 새 `execution_launch/research_incidents.py`, 새 `tests/launch_research_incidents.py`.
- pr4e_runner: 새 `execution_launch/research_incident_store.py`, 새 `tests/launch_research_incident_store.py`.
- pr4e_owner: 새 `execution_launch/research_incident_cli.py`, `tools/owner/research_incidents.py`, 새 `tests/launch_research_incident_cli.py`.
- pr4e_coordinator: 새 `tests/launch_research_incident_integration.py` 실제 수직 경로.
- revision_review: 독립 읽기 검토. 부모: registry/writeguards/통합검사/commit/PR.

## 형식과 reducer — exact 계약

`research_incidents.py`는 stdlib만 사용하며 형식/제한 상태만 계산한다. dataclass 생성은 실제 관찰·승인 증거가 아니다. 저장/replay는 모든 자료를 strict parse하여 caller mutable 객체를 보존하지 않는다.

```python
class IncidentFormatError(ValueError): ...
@dataclass(frozen=True, kw_only=True)
class IncidentLimits:
    max_event_bytes: int = 2*1024*1024
    max_state_bytes: int = 32*1024*1024
    max_targets: int = 256
    max_dependencies_per_target: int = 8192
    max_incidents: int = 4096
    max_attempts: int = 8192
# above defaults are hard upper bounds; exact positive ints, downward configuration only.
DEFAULT_LIMITS = IncidentLimits()

@dataclass(frozen=True, kw_only=True)
class ObjectDependency:
    kind: str                     # 'chunk'|'manifest'
    sha256: str                   # exact lowercase 64 hex
    byte_count: int               # exact positive int
    from_raw: bool                # this exact object is part of raw graph too

@dataclass(frozen=True, kw_only=True)
class TargetRegistration:
    store_binding_sha256: str
    bundle_digest: str
    input_archive_digest: str
    bundle_kind: str              # RAW_ARCHIVED|VERIFIED_UNAPPROVED
    raw_manifest_sha256: str      # SHA256 of exact canonical bytes
    verified_manifest_sha256: str | None
    graph_sha256: str             # fixed monitor canonical byte-inventory digest
    catalog_head_sha256: str
    catalog_sequence: int
    objects: tuple[ObjectDependency, ...] # unique sha, sorted; complete, never truncated

@dataclass(frozen=True, kw_only=True)
class IncidentEvent:
    schema: int                   # 1
    event_id: str                 # domain digest of kind/observed_at/payload
    kind: str                     # REGISTER|FAILURE|DELIVERY
    observed_at: datetime | None  # aware datetime canonical UTC; None only FAILURE
    payload: dict                 # detached strict per-kind shape below

make_event(kind, payload, *, observed_at) -> IncidentEvent
registration_document(registration) -> dict
parse_registration(document, *, limits=DEFAULT_LIMITS) -> TargetRegistration
event_bytes(event, *, limits=DEFAULT_LIMITS) -> bytes
parse_event(raw, *, limits=DEFAULT_LIMITS) -> IncidentEvent
initial_state() -> IncidentState
reduce(state, event, *, limits=DEFAULT_LIMITS) -> IncidentState
state_bytes(state, *, limits=DEFAULT_LIMITS) -> bytes
state_digest(state, *, limits=DEFAULT_LIMITS) -> str
blocked_incidents(state, registration) -> tuple[ResearchIncident, ...]
```

REGISTER payload is exactly `registration_document(registration)`. Key is `(store_binding_sha256,bundle_digest)`. Existing key cannot be rewritten. Identical replay is idempotent. Monitor avoids re-registering on catalog growth and compares the graph identity fields excluding observed catalog head/sequence.

FAILURE payload exact keys: `store_binding_sha256`, `bundle_digest`, `scope`, `failed_objects`, `category`, `reason_code`.
- scope: `TARGET|OBJECTS|STORE`. OBJECTS has sorted unique nonempty hashes that occur in the referenced registration; others require empty list. Unknown referenced registration refuses.
- category: `INTEGRITY_FAILURE|READ_UNAVAILABLE|RESOURCE_LIMIT|VALIDATION_REFUSED`.
- reason_code: bounded `[A-Z][A-Z0-9_]{0,95}`; monitor only uses fixed exception diagnostics or fixed fallback, never raw text. Codec validates syntax, not provenance.
- TARGET affects trigger logical bundle; if raw target, raw identity too. OBJECTS affects all registered targets in the same physical store binding sharing any failed object; affected raw identities are included only where the failed dependency has from_raw=True. STORE affects every currently registered bundle/raw under the binding and retains store-wide scope so newly registered targets cannot bypass it. Old records are never narrowed using a damaged catalog.
- Derive immutable ResearchIncident with `incident_id=event_id`, original failure fields, `observed_at`, `affected_bundle_digests` and `affected_raw_digests` sorted tuples. It also derives one NotificationIntent in the SAME state transition.
- Later registration remains blocked if its logical bundle/raw is already affected, or it matches the same physical STORE/OBJECTS scope. Copying an affected logical bundle to a new research store inside the same configured incident namespace does not clear the hold. The same object bytes in an unrelated store are not globally poisoned merely by matching content hash.

DELIVERY payload exact keys: `message_id`, `attempt_id`, `outcome`; observed_at required. attempt_id is generated-ID grammar `[a-z][a-z0-9_-]{0,63}`, outcome delivered|failed|unknown. Target must be existing outbox ID. Same attempt ID+message+outcome+time is idempotent; altered same attempt refuses, delivered message cannot receive new attempt. Failed/unknown can retry with new attempt, same message. This records REPORTED delivery only, never evidence that a network send happened.

```python
# Frozen projections; no operational authority fields.
ResearchIncident: incident_id, store_binding_sha256, bundle_digest, scope,
    failed_objects(tuple[str]), category, reason_code, observed_at,
    affected_bundle_digests(tuple[str]), affected_raw_digests(tuple[str])
NotificationIntent: message_id, incident_id, kind='RESEARCH_EVIDENCE_HELD',
    bundle_digest, category, reason_code
NotificationReceipt: message_id, attempt_id, outcome, observed_at
IncidentState: registrations(tuple[TargetRegistration]), incidents(tuple[ResearchIncident]),
    outbox(tuple[NotificationIntent]), receipts(tuple[NotificationReceipt]),
    events(tuple[IncidentEvent]), last_trusted_at(datetime|None)
# .pending_notifications property returns outbox without delivered receipt.
```

All IDs/digests are domain-separated canonical bytes (`tradegen-research-incidents/1\n`). Global event ID same exact body replay returns unchanged state; conflicting ID refuses. Only strict chronological observed_at advances last_trusted_at. Unknown FAILURE clock preserves last trusted time and still restricts. No expiry/release/repair/resume event. Resource exhaustion refuses before append, never truncates candidate/dependency/incident inventory. Parsing bounds bytes before JSON, bounded depth/nodes, rejects duplicate keys/bools-as-ints/noncanonical/extra keys. Fixed diagnostics `INCIDENT_*`; no CANO substring.

## Independent store — actual I/O

```python
@dataclass(frozen=True, kw_only=True)
class IncidentStoreLimits:
    format_limits: IncidentLimits
    max_journal_bytes: int        # <=128MiB
    max_records: int              # <=16384
parse_limits(raw: bytes) -> IncidentStoreLimits
limits_bytes(limits) -> bytes

IncidentStore(*, root: Path, backup_root: Path, head_root: Path,
              head_name: str, limits: IncidentStoreLimits)
# three distinct existing explicit directories, no overlap, links/reparse, repo/private-state/sync roots.
store.provision_empty()           # journal/lock/backup versions only; never seeds .head
store.head                       # actual BaselineHead in head_root/head_name
store.genesis_digest
store.context_sha256
store.inspect() -> IncidentStoreSnapshot(state, head, sequence)
store.commit(event, *, expected_head) -> IncidentStoreSnapshot
```

Store code pins configuration/root+lock identities through all operations. Journal canonical chained row includes schema, sequence, previous hash, context hash, exact event, row hash. Before head CAS each exact row is backed to `backup_root/versions/<rowhash>.json` through exclusive publication/flush/readback. Replay requires matching version copies and actual retained independent head; no auto catch-up/adoption. Whole append/backup/head/readback admitted before writes. Lock ordering prevents holding other research-store locks across incident commits. Same event idempotency returns actual current snapshot, not cached receipt.

Only owner utility `provision_incident_store(store)` calls `store.provision_empty(); store.head.initialize_reviewed_head(store.genesis_digest)` on explicit empty roots. Runtime/consumer never initialize. Journal/backup/head failure refuses dependent use. Same-user coherent rollback of every root and replacing an entire incident namespace is outside the local head guarantee; explicit configured namespace must be retained. New namespace cannot be advertised as protected continuation of old one.

## Monitor and real dependency enrollment

```python
register_target(incident_store, bundle_store, bundle_digest, *, clock) -> TargetRegistration
check_target(incident_store, bundle_store, bundle_digest, *, clock) -> IncidentCheck
# IncidentCheck: registered=True, held:bool, incident_ids:tuple[str,...],
#     store_binding_sha256,bundle_digest,incident_head,incident_sequence,
#     graph_checked:bool,checked_at:datetime|None; no use/approval flag.
```

Both require exact actual IncidentStore/BundleStore. Monitor rejects overlap among incident root/backup/head and actual research primary/backup by path/containment/retained filesystem identity. No default home/root. `store_binding_sha256` derives internally from actual fixed roots/identities/context/head-name; caller cannot name a new store_id to clear a hold.

Register supports actual complete `read_raw/read_verified(require_backup=True)` first. It validates raw→verified linkage and exact raw-byte inclusion with real format validators. It does not evaluate or authenticate source. Catalogue/head snapshot is captured from actual locked `_load`, released before incident commit. Atomic catalogue snapshot mismatch during graph read refuses/retries explicitly, never claims a coherent registration. All object descriptors derive from actual exact manifests/payloads through `preview_payload` (raw flag by raw graph membership). Full immutable graph commitment includes manifest bytes hashes and sorted exact file IDs/hash/length; objects list complete. No caller-provided Registration/StoredBundle/boolean is accepted by monitor. Actual verified signed-manifest recovery registration is DEFERRED; do not fake missing primary with unsigned claims.

Check requires existing registration (error `INCIDENT_TARGET_UNREGISTERED`), never auto-enrolls. It consults actual durable state first; active hold returns held=True without pretending to validate the repaired graph. Otherwise actual research catalogue/head then graph are read. On healthy graph, rederive full registration fields and compare all identity fields except catalog head/sequence; mismatch is target integrity failure.

On actual catalogue/head/shared-store failure record STORE scope using verified prior registrations. On object failure diagnose only already registered known object descriptors, via actual read-only EvidenceObjectStore lock+`_read_object` on both copies, without reading arbitrary paths or writing source. Identified damaged objects produce OBJECTS scope. If exact object cannot be localized, retain TARGET scope with unknown-cause/read-unavailable diagnostic rather than blaming every object. Missing or IO normalized by existing readers remains READ_UNAVAILABLE unless a specific actual check proves integrity failure. Quota is RESOURCE_LIMIT. No broad catch turns research/financial rejection into corruption. Commit restrictive event+outbox through actual IncidentStore; commit failure throws and consumer refuses. Never mutate primary/backup objects, call restore, clear holds, or dispatch messages.

## Incident-aware sealed entry point and timing seam

```python
# New incident_aware_selection.py; full existing sealed selection keyword arguments plus REQUIRED incident_store.
authenticate_incident_aware_selection(bundle_store, bundle_digest, *, incident_store,
    archive_attestation, source_reviews, audit_logical_ids, current_profile,
    window, history_head_root, history_storage_policy=None, clock, authority_provider)
    -> IncidentAwareSelectionAssessment
# frozen result: selection_assessment (actual existing SealedSelectionAssessment),
# incident_context_sha256, incident_head, incident_sequence,
# execution_ready=False,current_operational_use=False,automatic_recovery_supported=False
```

Initial actual check must be registered/unheld/graph_checked before numerical issuance. Held raises `INCIDENT_SELECTION_QUARANTINED`. Missing/broken incident journal/backup/head refuses. Existing direct API remains plain research inspection and is NEVER labelled incident-aware; all new CLI/entry paths must call this mandatory wrapper.

Parent approved narrow extraction in sealed_study_review.py: original public signature delegates to private `_authenticate_sealed_study_selection(..., final_dependency_guard=None)` with no public caller callback argument. New wrapper alone constructs the actual final guard. The private backend calls it **after all other heavy final graph/history reads and before final actual owner/archive/all-source/implementation rechecks and completion clock**. It raises on incident/read failure and records the finite observed incident head in wrapper-owned state. Do not perform heavy replay after the existing final timestamp; do not start original 30s authorization age before heavy actual evaluation. One actual family evaluation remains.

Actual registered-store read failures inside selection are rechecked through monitor in exception handling and persisted where actual corruption is observed; if graph remains healthy, preserve original signature/profile/math refusal without opening a false integrity incident. No helper-made assessment, callback or bool bypass. Capture original incident store object/context configuration before work and require same on final check. A copied result or new journal location cannot continue the SAME configured consumer. Whole-namespace replacement is not defended by a local record and must not be called continuous protected deployment.

## CLI/operator

Common exact options: `--incident-root --incident-backup-root --incident-head-root --incident-head-name --incident-limits`. `register`/`check` additionally use existing bundle-store flags `--sealed-root --backup-root --head-name --limits --digest`. `inspect`/`list-pending` only incident configuration. `incident-aware-select` adds existing sealed-study selection args (`--archive-attestation --profile --window --head-root`, optional `--history-storage`, repeated `--source-review`, repeated `--audit`). No user --now/provider/key/restore/release/send/arm options. Actual clock UTC; actual CurrentOwnerAuthority only for selection.

Delivery recording is library/store mechanism tested with fake transport; CLI has NO delivery-success argument in this first unit (prevents presenting manual reported delivery as an observed send). Runtime `provision` refuses; separate owner utility accepts only explicit incident configuration. Output bounded public IDs/head/fixed status and false operations; no paths/keys/financial bytes. Read limits with existing strict explicit bounded reader, parse with store codec.

## Integration acceptance

Actual stores/backup/owner signatures/family/factory: register/check/select healthy; actual report-only corruption A held while independent B succeeds; shared object affects only actual same-store dependents; catalog/head failure widens only registered catalogue scope; new copy of held bundle cannot clear hold; new dependent registration remains held. Initial hold prevents evaluator call; incident append/corruption during work fails final guard; slow final guard reaches expiry/30s and final actual revocation is rechecked. No-qualified family remains normal, recorded aborted raw is preserved, caller-created registries/results/providers refuse. Journal/backup/head crash/CAS/rollback and outbox unknown/duplicate/restart preserve restrictions. Every test uses 19 KEYLESS/temp homes/fake prices/no actual API/order/Telegram. Parent owns runtime freeze/guards/registry; no old-tree edits.

## Implementation clarifications — same scope

- `IncidentStore.admit(event, *, expected_head)` returns the actual current snapshot after the same strict reducer/proposed state/row/record/aggregate journal and backup capacity checks as commit, with no writes or CAS. It is a readonly capacity preflight, not a reservation against concurrent events or future I/O failure. Healthy monitor results require this admission for a conservative STORE failure event.
- Physical OBJECTS/STORE scope is expanded over all currently genuine registrations on every hold query, then their logical bundle/raw IDs propagate to copies. A dependent target registered after the original failure and subsequently copied cannot bypass the hold. Original incident affected_* bytes remain unchanged.
- Failed incident publication produces `INCIDENT_RECORD_UNCONFIRMED`, no success/delivery claim. A bounded process latch refuses later use of that configured namespace in the same process. Torn journal/backup/head remains refused after restart. If I/O refused before any durable byte, this process latch is not a persistent incident and must not be described as one; capacity-only exhaustion remains detectable by the repeat admission after restart. No broad cleanup/adoption/emergency permission is introduced.

- Private format `_replay_events(events: tuple, *, limits=DEFAULT_LIMITS)` starts from initial state, strictly reparses every event and derives the final bounded projection once. Store replay uses it to avoid repeatedly validating every prior prefix; no caller validation token/state is accepted. Public `reduce` still fully validates arbitrary input state.
- Re-registering an existing identity delegates to the same actual `check_target` failure/incident path and returns only the immutable registration identity, never healthy status or release. First-ever unreadable enrollment remains unregistered because no genuine graph snapshot exists.

- Parent-approved private completion guard follows all final owner/signature work and precedes the original completion clock. It compares the same retained namespace/configuration and actual small `BaselineHead.read()` with the final incident head under bounded directory pins. It performs no journal replay and changes no observation time. Head changes/refusal reject the result (`INCIDENT_FINAL_HEAD_CHANGED`); no persistent filesystem lease is claimed. The public research-only signature stays unchanged.

- Monitor input separation uses the actual constructors’ retained absolute lexical paths and original root identities. Current source-path checks run in the actual catalogue reader, so a known source changing to a link/unreadable location becomes a durable STORE observation instead of disappearing during preliminary path resolution. Incident namespace validation is never skipped.
