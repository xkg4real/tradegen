# PR5 B2b-2 — 정확 복구 제어기 API 카드

2026-11-13. 전용 `tradegen-recovery-controller-1113`, base `a836760`. 이 문서는 구현 계약이며 실제 복구·승인·검사 통과 기록이 아니다. 다른 트리·registry·guard는 부모 소유다.

## 소유

- protective_hold_design: 이 카드, `research_recovery_attempts.py`, `tests/launch_research_recovery_attempts.py`.
- pr4e_runner: `research_recovery_store.py`, store tests.
- pr4e_coordinator: `research_recovery.py`, 좁은 actual owner checkpoint 검증, controller tests.
- pr4e_owner: `research_recovery_cli.py`, `tools/owner/research_recovery.py`, CLI tests.
- notion_revision: `tests/launch_research_recovery_integration.py` 실제 수직 검사.
- revision_review: 독립 읽기 검토. root: registry/guards/최종 검증·commit.

## Pure 형식

모든 타입은 frozen/kw_only dataclass다. 구성은 내부 일관성 자료일 뿐 actual 관찰·서명·승인 발급이 아니다. 기존 `research_incidents.TargetRegistration`의 pure codec을 재사용하고 source/auth codec은 복제하지 않는다.

```python
class RecoveryAttemptError(ValueError): ...  # fixed RECOVERY_* diagnostics
class RecoveryAttemptLimits:
    max_event_bytes: int = 2*1024*1024
    max_state_bytes: int = 32*1024*1024
    max_routes: int = 128
    max_attempts: int = 1024
    max_delivery_attempts: int = 8192
    max_new_attempts: int = 1
    max_resumes: int = 2
    min_retry_seconds: int = 60
DEFAULT_LIMITS = RecoveryAttemptLimits()
# Exact int/no bool. Size/count fields are positive, default is hard ceiling.
# max_new_attempts is exactly 1; max_resumes 0..2; retry seconds 60..86400.

class OwnerCheckpoint:
    key_fingerprint: str                  # SHA256:<lowerhex64>
    code_hash: str                        # lowerhex64, actual D14 in adapter
    owner_head: tuple[int, str]           # positive seq + lowerhex64
    observed_at: datetime                 # aware UTC canonical

class RecoveryRoute:
    incident_namespace_sha256: str
    attempt_namespace_sha256: str
    incident_head: tuple[int, str]
    registration: TargetRegistration     # full actual original registered graph
    source_configuration_sha256: str     # lexical roots + limits; excludes mutable path state
    source_root_ids: tuple[tuple[int,int], tuple[int,int]]
    destination_configuration_sha256: str
    destination_root_ids: tuple[tuple[int,int], tuple[int,int]]
    destination_context_sha256: str
    storage_policy_sha256: str
    object_policy_sha256: str
    attestation_sha256: str
    request_sha256: str
    file_set_sha256: str
    revocation_target_sha256: str
    issued_at: datetime
    expires_at: datetime
    checkpoint: OwnerCheckpoint
    # .route_id property is stable domain digest below

class RecoveryEvent:
    schema: int                          # exact 1
    event_id: str
    kind: str
    observed_at: datetime | None
    payload: dict                        # detached deep immutable inside event

checkpoint_document(checkpoint) -> dict
parse_checkpoint(document) -> OwnerCheckpoint
route_document(route) -> dict            # includes derived route_id
parse_route(document, *, limits=DEFAULT_LIMITS) -> RecoveryRoute
artifact_incident_id(incident_id: str) -> str
plan_id(route: RecoveryRoute, incident_id: str) -> str
attempt_id(route: RecoveryRoute, incident_id: str) -> str
make_event(kind, payload, *, observed_at) -> RecoveryEvent
event_bytes(event, *, limits=DEFAULT_LIMITS) -> bytes
parse_event(raw, *, limits=DEFAULT_LIMITS) -> RecoveryEvent
initial_state() -> RecoveryState
reduce(state, event, *, limits=DEFAULT_LIMITS) -> RecoveryState
state_bytes(state, *, limits=DEFAULT_LIMITS) -> bytes
state_digest(state, *, limits=DEFAULT_LIMITS) -> str
_replay_events(raw_events: tuple[bytes,...], *, limits=DEFAULT_LIMITS) -> RecoveryState
```

Domain=`tradegen-research-recovery-attempts/1\n`; subtag+LF+canonical document for route/plan/attempt/event/state/notification hashes. JSON uses exact sorted keys/compact separators/ASCII, UTC microsecond strings ending Z; exact parse/no duplicate keys/no bool-as-int/extra keys; byte/depth/node/count limits before allocation. Public arbitrary state is rederived from events; private store replay owns initialstate, strict parses each raw row once and applies once, no caller trusted flag.

Root IDs are `(st_dev>=0, st_ino>0)` exact integer pairs, two distinct roots; no strings/paths. Owner-head/source identity provenance is verified by actual adapter, not pure codec. Route time `issued<=checkpoint.observed<expires`, validity at most 86400s.

Stable route ID excludes only `incident_head`, checkpoint `owner_head`/`observed_at`; it includes checkpoint key/code and every immutable route/registration field. Re-registering that ID with changed record refuses; actual adapter returns the retained route after revalidating the same immutable binding instead of rewriting its historical checkpoint. Exact same record replay is idempotent. Route count and state byte cap never truncate dependency inventory.

`plan_id` binds route ID + full 64hex incident ID. `attempt_id` binds plan + ordinal 1. First-stage max_new_attempts=1 cannot be reset by another call/benign owner head growth. Artifact ID is `i` + unpadded lowercase Base32 of the full 32-byte incident hash (53 characters, reversible/no truncation). Both full SHA and derived artifact label are retained in attempt projection. This does not change legacy artifact schema.

## Events, chronology, attempts

Every payload below is an exact dict. Head/checkpoint documents use JSON lists/canonical strings. Event names are exactly as written.

### ROUTE_REGISTERED

Payload=`route_document(route)`. observed_at required. It must be at/after checkpoint.observed_at, within 30s, and before route.expires_at. It records actual adapter observations only; no automatic destination write.

### ATTEMPT_STARTED

Keys: `route_id`, `incident_id`, `incident_head`, `checkpoint`.

Requires registered route, no attempt for its plan, trusted nondecreasing observed_at, current checkpoint with identical route key/code and monotonic owner-head prefix metadata, and observed_at before original expiry. Actual verified prefix evidence remains the adapter's job. Creates ordinal-1 attempt and execution entry 1. **This event must be durable before any destination write.**

### RESUME_STARTED

Keys: `attempt_id`, `execution_number`, `incident_head`, `checkpoint`.

Requires existing nonterminal attempt, exact next execution number, total entries <=1+max_resumes. Same route/document/destination binding and current owner checkpoint requirements as START. Due-time is 60s (configured minimum) after the latest trusted execution start or outcome, whichever is later. In-progress crash may resume only under controller-wide singleflight. A fresh provider cannot clear a stored terminal refusal.

### PREFLIGHT_REFUSED

Keys: `route_id`, `incident_id`, `execution_number`, `incident_head`, `status`, `reason_code`, `checkpoint`, `revocation_status`.

This is necessary when actual source/authority admission fails before START. It creates or continues the same plan/attempt, consumes one of the same three execution opportunities, and atomically records one outcome+result outbox intent. It does not claim a copy began. First execution_number=1; later exact next number with the same retry timing/cap. `checkpoint` may be null when actual owner observation failed; never fabricate one. `AUTHORITY_REFUSED` is terminal across provider/process recreation. Unknown time is accepted only for this event or ATTEMPT_OBSERVED with AUTHORITY_REFUSED, no checkpoint and UNOBSERVED revocation; it never permits START/RESUME and preserves last trusted chronology.

### ATTEMPT_OBSERVED

Keys: `attempt_id`, `execution_number`, `status`, `reason_code`, `checkpoint`, `revocation_status`, `verified_at`, `recovery_artifact_digest`, `destination_head`.

One outcome per current execution entry; conflicting rewrite refuses. Exact event/body replay is globally idempotent. It is valid only for a START/RESUME entry, since PREFLIGHT_REFUSED creates its outcome atomically.

Statuses:

- `EXACT_ARCHIVE_RESTORED`: terminal. Requires actual final checkpoint, `NOT_REVOKED_AT_HEAD`, verified_at equal observed_at, exact artifact digest and destination head, owner observation within original30s, same key/code and signature unexpired at observed_at. These are structural conditions, never a substitute for actual verifier calls.
- `AUTHORITY_REFUSED`, `DESTINATION_UNCONFIRMED`, `EVIDENCE_REFUSED`: terminal automatic refusal. Preserve already copied bytes; no repair/adopt/newroute fallback.
- `READ_UNAVAILABLE`, `RESOURCE_LIMIT`, `PARTIAL_UNVERIFIED`: retryable only with the same plan, remaining execution budget and due-time. PARTIAL denotes actual observed partial/unfinished evidence; unknown I/O is not called proven partial.

All non-success outcomes may carry checkpoint/verified_at/artifact/destination facts only if actually observed; null means unobserved. `revocation_status` is `UNOBSERVED|REVOKED|NOT_REVOKED_AT_HEAD`; non-UNOBSERVED requires checkpoint. A positive archival observation with REVOKED becomes AUTHORITY_REFUSED in this controller, although the lower-level archive helper may report revoked identity. reason_code grammar `[A-Z][A-Z0-9_]{0,95}`, adapter supplies fixed diagnostics only.

Every outcome creates one stable notification ID from outcome event+attempt. Notification is RESULT ONLY: `RECOVERY_RESULT_RECORDED` with status/reason, target bundle, `quarantine='REMAINS'`, `current_use='NOT_GRANTED'`. No approval request, payload/paths/financial fields.

### DELIVERY_REPORTED

Keys: `message_id`, `delivery_attempt_id`, `outcome`; observed_at required. ID grammar `[a-z][a-z0-9_-]{0,63}`, outcome delivered|failed|unknown. Existing result message required. Same attempt+message+outcome+time is idempotent; changed same attempt refuses; delivered message cannot receive a new attempt. Failed/unknown new attempts preserve same message. No actual network send is proven by this record.

### Immutable state projections

```python
ExecutionEntry: execution_number, kind, observed_at, incident_head, checkpoint
AttemptOutcome: event_id, execution_number, status, reason_code, observed_at,
    checkpoint, revocation_status, verified_at, recovery_artifact_digest, destination_head
RecoveryAttempt: plan_id, attempt_id, route_id, incident_id, artifact_incident_id,
    entries:tuple[ExecutionEntry,...], outcomes:tuple[AttemptOutcome,...]
# .phase: IN_PROGRESS or latest current-entry outcome.status
# .terminal: phase in terminal statuses
# .execution_count: len(entries)
RecoveryNotification: message_id, attempt_id, outcome_event_id,
    kind='RECOVERY_RESULT_RECORDED', bundle_digest, status, reason_code,
    quarantine='REMAINS', current_use='NOT_GRANTED'
RecoveryDelivery: message_id, delivery_attempt_id, outcome, observed_at
RecoveryState: routes, attempts, outbox, receipts, events (all tuples), last_trusted_at
# .pending_notifications excludes messages with reported delivered receipt
```

No expiry/release/repair/arm/sell/reset event. Unknown clock restricts; trusted equal timestamps allowed, rollback refuses. Chronology and prefix metadata do not authenticate clocks/logs. Reducer consumes supplied model facts only; controller must make actual checks.

## Actual store and singleflight

```python
RecoveryStoreLimits(format_limits:RecoveryAttemptLimits,
    max_journal_bytes=128*1024*1024, max_records=16384)
RecoveryStoreSnapshot(state, head, sequence)
RecoveryAttemptStore(*, root, backup_root, head_root, head_name, limits)
# .head/.genesis_digest/.context_sha256
.provision_empty()          # files only; never initializes head
.inspect()
.admit(event, *, expected_head)
.admit_pair(first, second, *, expected_head) # exactly two strict forecast rows; returns current snapshot only
.commit(event, *, expected_head)
.operation()                # separate cross-process operation lock, no journal/head lock held
.check_operation()          # recheck currently held operation root/lock identity; no permission
limits_bytes(limits) -> bytes
parse_limits(raw) -> RecoveryStoreLimits
```

Three actual distinct explicit roots, version backup/head CAS/readback and safe root/lock pins follow incident-store reviewed patterns. Separate `operation.lock` is created by explicit provision only; `.operation()` retains that singleflight lock across route registration/run_once, while each journal operation takes/releases its own independent lock. Restore never runs under an incident/store session lock. This prevents another process treating a still-running long copy as a crashed attempt after60s. No runtime provision or automatic catch-up of partial rows/head. Admission is not a disk reservation.

## Actual controller and checkpoint

```python
class RecoveryRouteConfig:       # frozen kw_only; config only
    source: SignedBackupSource
    destination: BundleStore

register_recovery_route(incident_store, attempts, source_store, destination,
    bundle_digest, attestation_bytes, *, clock, authority_provider) -> RecoveryRouteObservation
run_recovery_once(incident_store, attempts, route:RecoveryRouteConfig, *,
    route_id, incident_id, attestation_bytes, clock, authority_provider) -> RecoveryControllerObservation

# narrow existing trusted provider method, never private-pin assignment:
CurrentOwnerAuthority.observe_checkpoint(now, *, key_fingerprint, code_hash,
    owner_head:tuple[int,str]) -> ReviewAuthority
```

Route registration uses actual normal original graph and incident registration, actual signature and canonical current revocation, actual roots/config IDs and already provisioned destination. It refuses revoked/expired/code/key mismatch. Full registration/namespace actual observations are not caller booleans. run config does NOT require source BundleStore/head-name: SignedBackupSource can retain recorded source paths while primary is missing. Present source primary/backup identities must match their recorded identities. Only the actual completed-destination revalidation branch may allow either original source leaf to be absent; it preserves the registered original binding and never adopts a replacement. Actual copying requires the original backup present/pinned. Do not call source-dependent _separate before deciding the destination-only branch. Destination/incident/attempt/source roots may not overlap.

Checkpoint method calls actual owner loader/current PEM and actual signed log verify_log with the historical head as trusted-prefix requirement, confirms current head/key/code and original observation lifetime/date. It never sets provider._pinned from supplied data. Same actual provider retained through each call. Known terminal refusal is checked in durable attempt state before any new actual source/authority/copy work.

Within operation singleflight: inspect actual incident+attempt records → derive stable route/plan/IDs → historical completed/terminal return (no current permit) or due/cap admission → actual current checkpoint/source/target inspection → durable START/RESUME (or atomic PREFLIGHT_REFUSED+outbox on admission failure) → release journal locks → existing actual restore → actual verify_restored_archive and final canonical revocation/incident/route checks → durable outcome+outbox and readback. Source absence with already-complete target uses actual destination-only helper; cached result never proves completeness. If target incomplete and source absent, refuse/partial facts, not success. Actual source failure is distinguished from numerical research rejection.

Original expiry/code/key constraints, stage clocks and original B2 source postcheck remain. An actual completed copy with later authority refusal is preserved but not marked current usable. Result commit delay does not relabel observation time as fresh. Attempt storage failure latches this configured process and never emits a success result; partial journals/head fail on restart. Coherent rollback of all roots and pre-crash events never written are outside local guarantee.

Minimum return shapes (frozen observations, not authority):

```python
RecoveryRouteObservation: route_id, bundle_digest, incident_namespace_sha256,
    attempt_namespace_sha256, attempt_head, attempt_sequence, registered_at
RecoveryControllerObservation: route_id, plan_id, attempt_id, incident_id,
    artifact_incident_id, bundle_digest, phase, execution_count,
    outcome_event_id:str|None, recovery_artifact_digest:str|None,
    attempt_head, attempt_sequence, observed_at:datetime|None,
    quarantine_released=False, current_use_eligible=False,
    research_selection_ready=False, execution_ready=False,
    automatic_operational_recovery_supported=False
```

Error/observation exact codes are fixed RECOVERY_* and existing normalized downstream codes; expose no paths/raw exception text. Status/phase finite historical facts, not claim that currently deleted destination still exists. No controller result bypasses B2b-1 hold. Incident store is read-only here; no release/route activation.

## CLI and tests

Commands: `route-register`, `run-once`, `inspect`, `list-pending`. Common explicit `--attempt-root --attempt-backup-root --attempt-head-root --attempt-head-name --attempt-limits`. Registration/run additionally explicit incident configuration, source roots/limits, destination roots/head-name/limits and bounded `--archive-attestation`. `--source-head-name` applies registration only. Registration adds `--digest`; run adds `--route-id --incident-id`. Actual UTC/provider constructed internally, no --now/key/provider/success/release options. Owner-only utility provisions attempt store/head explicitly. inspect/list-pending reports only bounded IDs/status and false operation flags.

Runtime tests wait for joint freeze. Required actual vertical cases: healthy registration, actual held A and independent B, complete backup exact restore+artifact, source gone after full destination complete, START/partial/outcome response-loss crash, preflight authority failure terminal across freshprovider, 60s±1us +3start budget, checkpoint rollback/code/key/clock/date/late revoke, no nested session locks/concurrentprocesscopy, original preservation and hold maintained, outcome+outbox atomic/delivery unknown, limits/parse/root/head/backup faults. Use existing actual temporary signed fixtures/19 KEYLESS/fake prices. No actual home/API/key/order/Telegram. Native Windows claims only actual tests.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
