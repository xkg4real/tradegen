# TRADEGEN recovered research selection — 확정 API 카드

작성: 2026-11-13. 전용 트리 `/workspace/tradegen-recovered-selection-1113`, branch `gpt/recovered-research-selection`, base `6fa15f2`. 기존 사용자 요구 안에서 승인된 개발 계약이다. 구현·검사 결과 보고가 아니며 실제 홈·키·API·주문을 사용하지 않는다.

## 1. 범위와 소유

정확한 VERIFIED 원본의 성공한 복구 route/attempt 한 개, 현재 적용 incident 한 개, 실제 목적지 한 개에 한정한다. 기존 일반 incident 보류는 유지한다. 새 consumer가 매번 전체 실제 자료·현재 승인·철회를 검증하고, 명시적인 연구용 release 기록이 확정된 경우에만 제한된 연구 선발 결과를 반환한다. 기록 자체는 권한이 아니다. 운영 해제·거래 재개·새 서명·Telegram 전송은 없다.

| 담당 | 소유 파일 |
| --- | --- |
| coordinator | `execution_launch/research_incidents.py`, 새 `tests/launch_research_route_release.py` — 순수 codec/reducer/query. |
| owner | 새 `execution_launch/recovered_study_selection.py`, 새 `tests/launch_recovered_selection.py` — 실제 consumer와 좁은 단위 검사. |
| runner | `execution_launch/sealed_study_review.py`, `execution_launch/research_incident_monitor.py`, 새 `tests/launch_recovered_selection_boundaries.py` — private 실제 hook/helper와 기존 API 보존. |
| 독립 통합 담당 | 새 `tests/launch_recovered_selection_integration.py` — 실제 서명·복구·평가·선발의 수직 검사. |
| root | registry/guard/harness·최종 runtime·commit/PR. |

저장 엔진 `IncidentStore`는 기존 generic event append/backup/head/replay를 그대로 쓴다. 기존 `IncidentState` 필드와 limits/context, legacy event/state bytes는 변경하지 않는다.

## 2. 엄격한 release event

기존 `IncidentEvent(schema=1)`에 정확한 kind `RESEARCH_ROUTE_RELEASE`를 추가한다. `observed_at`은 기존 UTC 시각 codec의 non-null 값이다. payload의 **정확한 키**는 다음과 같다.

```text
release_schema = 1                         # exact int, bool 불가
scope = "recovered_research_selection"
binding                                   # 아래 닫힌 객체
binding_sha256                            # 아래 domain digest
incident_head = [sequence, sha256]         # 기록 직전 실제 incident head
attempt_head = [sequence, sha256]
destination_head = [sequence, sha256]
owner_checkpoint = {
  key_fingerprint, code_hash,
  owner_head: [positive_sequence, sha256],
  observed_at: UTC_string
}
```

`binding`의 정확한 키:

```text
route_id, attempt_id, outcome_event_id, incident_id,
incident_namespace_sha256, attempt_namespace_sha256,
source_store_binding_sha256, source_registration_sha256,
destination_store_binding_sha256, destination_registration_sha256,
bundle_digest, input_archive_digest, graph_sha256,
recovery_artifact_digest, selection
```

`selection` 이외의 binding 값은 소문자 64-hex다. `selection`의 정확한 키:

```text
bundle_digest, input_archive_digest, attestation_sha256,
revocation_target_sha256, family_sha256, selected_study_id,
program_sha256, protocol_sha256, evidence_sha256,
profile_contract_sha256, rule_terms_sha256, window_sha256,
driver_identity_sha256, source_reviews, evaluated_at, approval_expires_at
```

`source_reviews`는 1..128개의 `study_id` 기준 정렬·유일 list다. 각 row의 정확한 키는 `study_id, document_sha256, purpose, revocation_target_sha256, audit_logical_id, audit_sha256`다. purpose는 기존 `strategy_source_and_fixed_implementation_review` 또는 `strategy_source_and_fixed_carry_implementation_review`만 허용한다. study ID는 기존 `[A-Za-z][A-Za-z0-9_.:-]{0,95}`, audit logical ID는 `[a-z][a-z0-9_-]{0,63}` 문법이다. 모든 SHA는 64-hex이고 시각은 기존 엄격한 UTC 문자열이다. selected ID가 source_reviews에 있어야 한다. binding/selection의 bundle/raw는 동일해야 한다.

모든 head sequence는 exact positive int64다. key fingerprint는 `SHA256:`+64-hex다. evaluated_at ≤ checkpoint 시각 ≤ event 시각 < approval_expires_at이며 checkpoint부터 event까지의 차이가 기존 30초 상한을 넘을 수 없다. 이 형태·시각 검사는 실제 authority 검증을 대체하지 않는다. 경로·금액·키·임의 reason 문자열·승인 bool은 payload에 없다.

순수 공개 API:

```python
registration_digest(registration, *, limits=DEFAULT_LIMITS) -> str
research_release_binding_digest(binding, *, limits=DEFAULT_LIMITS) -> str
research_route_releases(state, *, route_id=None, incident_id=None,
    destination_store_binding_sha256=None, limits=DEFAULT_LIMITS
) -> tuple[IncidentEvent, ...]
```

각 digest는 엄격히 검증한 객체의 기존 canonical JSON bytes 앞에 각각 `b'tradegen-research-release-registration/1\n'`, `b'tradegen-research-route-release-binding/1\n'`을 붙인 SHA256이다. registration digest는 catalog snapshot 필드까지 포함한 정확한 `registration_document` 전체를 묶는다. query의 선택 filter는 None 또는 정확한 hash이며 state를 실제 재검증한 뒤 **원래 frozen event**를 반환한다. 새로운 authority projection은 만들지 않는다. event 생성/parse/bytes/state replay는 기존 함수에 새 kind를 추가한다.

reducer 조건:

- source/destination registration이 현재 state에 존재하고 두 digest·bundle/raw/graph·binding 값이 일치해야 한다. kind는 둘 다 `VERIFIED_UNAPPROVED`이며 원 raw/verified manifest SHA도 각각 같아야 한다. 서로 다른 store binding이어야 한다. 각 registration digest는 서로 다른 store/catalog 필드까지 독립적으로 묶는다.
- 지정 incident가 존재하고 현재 전체 등록 집합으로 계산한 source와 destination의 적용 incident 집합이 각각 **정확히 그 한 개**여야 한다. `_apply` 안에서 public `blocked_incidents`를 호출해 재귀 재검증하지 말고 기존 내부 affected 계산을 재사용한다.
- namespace·route/outcome·owner·서명의 실제 진위는 순수 reducer가 검증할 수 없다. 실제 consumer가 확인하며 생성된 event로 일반 held 결과는 바뀌지 않는다.
- release 수 ≤ `max_incidents`; 기존 전체 event 수(`max_targets+max_incidents+max_attempts`)·event/state/journal byte 상한도 그대로 적용한다. 새 limits 필드·새 저장 엔진은 없다.
- 같은 binding ID의 기존 payload와 다른 관찰 payload를 덮어쓰지 않는다(`INCIDENT_RELEASE_CONFLICT`). 원 event exact retry만 no-op다. 새로운 현재 검증 후 같은 binding을 사용할 때 consumer는 기존 원 event를 선택하고 관찰 시각을 고쳐 쓰지 않는다.
- registrations/incidents/outbox/receipts는 변경하지 않고 events/last_trusted_at만 기존 방식으로 진행한다. 새 메시지를 자동 발급하지 않는다. 기존 `blocked_incidents`, 일반 monitor와 incident-aware selector는 계속 held를 거절한다. generic `RELEASE`/`APPROVE`/`SELL` kind는 여전히 거절한다.

## 3. 실제 sealed backend hook

private `_authenticate_sealed_study_selection`에만 선택 인자 `selection_record_guard=None`를 추가한다. public `authenticate_sealed_study_selection` signature에는 추가하지 않는다.

```python
@dataclass(frozen=True, kw_only=True, slots=True)
class _SourceReviewRecordBasis:
    study_id: str
    document_sha256: str
    purpose: str
    revocation_target_sha256: str
    audit_logical_id: str
    audit_sha256: str

@dataclass(frozen=True, kw_only=True, slots=True)
class _SelectionRecordBasis:
    bundle_digest: str
    input_archive_digest: str
    attestation_sha256: str
    revocation_target_sha256: str
    family_sha256: str
    selected_study_id: str
    program_sha256: str
    protocol_sha256: str
    evidence_sha256: str
    profile_contract_sha256: str
    rule_terms_sha256: str
    window_sha256: str
    driver_identity_sha256: str
    source_reviews: tuple[_SourceReviewRecordBasis, ...]
    evaluated_at: datetime
    approval_expires_at: datetime
    started_at: datetime             # arithmetic 뒤 FIRST actual owner 관찰 시작
    observed_at: datetime            # selected implementation을 검증한 실제 관찰
    first_authority: ReviewAuthority # 함수 안 실제 provider에서 얻은 동일 객체
    selected_authority: ReviewAuthority

# private actual callback
selection_record_guard(basis: _SelectionRecordBasis) -> None
```

앞의 16개 basis 필드가 위 payload.selection과 정확히 대응한다. datetime은 기존 UTC 문자열, source_reviews tuple은 고정 row list로 변환한다. caller mapping을 다시 읽어 만들지 않는다. 실제 검증한 내부 snapshot에서 도출한다: family hash는 `_authenticate_evaluated_selection`이 실제 full issued family와 일치시킨 signed `request.family_commitment.family_sha256`; evidence는 실제 발급 result digest; program/protocol/profile/rules는 실제 ImplementationBinding; window는 실제 identity.deployment_window_digest; driver identity digest는 기존 capability.digest(identity); review 목록은 actual authenticated IDs의 정확한 원 문서 SHA256·purpose·canonical target·sealed audit ID/hash다. evaluated_at은 원 연구의 시각이고 approval_expires_at은 실제 archive/해당 source 문서들의 가장 이른 만료다. source_reviews는 새 frozen row tuple로 분리한다. 실제 first/selected authority 외에 mutable caller 객체를 보존하지 않는다. 구조체 constructor는 issuer가 아니며 public 입력으로 받지 않는다.

호출 위치를 고정한다:

```text
실제 graph/route의 비권한 사전 읽기
→ 기존 실제 family 평가 정확히 1회 (authorization 구간 밖)
→ backend.started/첫 actual owner + 기존 archive/source 승인
→ 실제 selected factory/history/implementation 승인
→ 두 번째 graph/history 재읽기
→ SELECTED이고 실제 source/implementation 검사 성공 시 selection_record_guard(basis)
     [actual stored-checkpoint/복구 artifact/current revocation 검사 + release commit]
→ 기존 final_dependency_guard()
     [post-release actual artifact/graph/incident/attempt/current checkpoint]
→ SELECTED hook 경로의 actual LiveHistory._durable_unchanged + _replay(install=False) 재검사
→ latest owner/archive/모든 source/implementation 최종 검증
     [hook-present 경로는 FIRST actual key/code/head로 observe_checkpoint; hook 없는 public은 기존 __call__]
→ completion_dependency_guard()
     [작은 namespace/head 확인, optional completion watermark]
→ final clock + 기존 첫 관찰 나이/날짜/expiry/profile 검사
→ 결과
```

hook은 SELECTED에서 한 번만 호출한다. NO_SELECTION에서는 호출하지 않는다. `final_dependency_guard`는 NO_SELECTION에도 실제 artifact/checkpoint를 확인한다. SELECTED hook 경로는 record/final dependency 작업 중의 실제 history 변경을 놓치지 않도록 그 두 단계 뒤에 actual `LiveHistory._durable_unchanged`와 전체 `_replay(install=False)`를 다시 수행한 다음 latest owner/crypto/final clock으로 진행한다. 앞의 history 검사도 유지하며 hook 없는 기존 public 경로는 바꾸지 않는다. 실제 artifact/owner helper를 arithmetic 전에 호출해 놓고 backend.started로 그 관찰의 나이를 리셋하지 않는다. arithmetic 전은 route/attempt/registration·실제 graph의 구조 읽기만 한다.

`completion_dependency_guard`의 private 반환은 기존 None 또는 exact aware datetime이다. 반환 시각은 actual `observe_checkpoint`/helper의 마지막 완료 watermark다. hook-present recovered 경로의 마지막 actual owner 관찰은 SELECTED/NO_SELECTION 모두 FIRST actual key/code/head를 입력으로 `observe_checkpoint`를 사용한다. 일반 `__call__`은 내부 완료 시각을 `_last`에 남기지 않으므로 그것만으로 hidden completion을 확인했다고 주장하지 않는다. hook 없는 public 경로의 호출 방식은 기존 `__call__`을 유지한다. backend는 **최종 clock 이전**에 형식·UTC를 확인하고, finished가 반환 watermark·latest 관찰·actual provider가 실제 보존한 완료 시각보다 빠르지 않은지 bounded 비교한다. 기존 None callback 형태는 유지하지만 completion watermark 비교로 시계 역행은 이전보다 일찍 거절될 수 있다. hook 뒤 무거운 검증을 생략하거나 final clock 뒤 hash/graph/서명/새 owner 읽기를 추가하지 않는다. 원 started/first authority는 끝까지 유지한다.

## 4. held 대상의 실제 graph helper

```python
_check_recovered_target(incident_store, bundle_store, bundle_digest, *, clock) -> IncidentCheck
```

`research_incident_monitor.py`의 private helper다. `check_target`과 같은 actual exact 입력·namespace/latch·capacity·registration·전체 graph·마지막 snapshot 확인을 사용하되, 기존 hold 때문에 graph 검사를 생략하지 않는다. 실제 성공이면 `held=True`와 `graph_checked=True`가 함께 가능하다. incident_ids는 그대로다. 일반 `_projection/check_target`의 의미를 바꾸지 않는다. graph 실패는 기존 `_record_failure`, 저장 실패는 기존 latch를 쓴다.

artifact는 target registration graph 바깥의 별도 필수 자료다. consumer는 exact route/document binding을 먼저 확인하고 actual artifact/backup 읽기의 손상·누락을 발견하면 기존 monitor의 `_record_failure(...,_GraphFailure('graph',cause),...)` 경로로 **해당 destination target**에 기록한다. target dependency에 없는 artifact hash를 `failed_objects`로 꾸며 넣지 않는다. authority 만료/철회·profile/숫자 실패·caller 문서 불일치는 graph 손상으로 기록하지 않는다. 필요한 helper 추출은 같은 private 경계만 사용한다.

## 5. public recovered consumer

```python
authenticate_recovered_study_selection(destination, bundle_digest, *,
    incident_store, attempts, route_id, incident_id,
    archive_attestation, source_reviews, audit_logical_ids,
    current_profile, window, history_head_root,
    history_storage_policy=None, clock, authority_provider
) -> RecoveredSelectionAssessment
```

```python
@dataclass(frozen=True, kw_only=True)
class RecoveredSelectionAssessment:
    scope: str                        # "recovered_research_selection"
    selection_assessment: SealedSelectionAssessment
    route_id: str
    attempt_id: str
    incident_id: str
    outcome_event_id: str
    recovery_artifact_digest: str
    destination_store_binding_sha256: str
    release_record_id: str | None      # 원 IncidentEvent.event_id
    incident_context_sha256: str
    incident_head: str
    incident_sequence: int
    attempt_head: str
    attempt_sequence: int
    research_selection_ready: bool    # actual selected result AND confirmed record
    current_operational_use: bool = False
    execution_ready: bool = False
    automatic_operational_recovery_supported: bool = False
```

exact 실제 destination/IncidentStore/RecoveryAttemptStore/provider 및 동일 clock을 요구한다. route는 actual replay에서 찾으며 현재 성공 outcome이 `EXACT_ARCHIVE_RESTORED`, actual canonical status `NOT_REVOKED_AT_HEAD`, 실제 checkpoint·artifact·destination head를 보유해야 한다. 생성된 RecoveryResult/assessment/context나 cached family를 받지 않는다. source physical 경로를 다시 열거나 손상 원본을 바꾸지 않는다. 목적지 및 두 독립 store의 roots/namespace/config/원 directory identity/정책은 실제 확인한다.

동일 route의 terminal 성공이 있어도 매 호출 actual destination target/raw/backups와 exact signature artifact/backups를 검사하고 새 current owner checkpoint·canonical 철회를 확인한다. 저장된 과거 owner prefix는 실제 `observe_checkpoint`를 이용한다. 현재 적용 사건은 source/destination 모두 정확히 단일 incident여야 한다. 추가 사건은 `RECOVERED_SELECTION_ADDITIONAL_INCIDENT`로 거절한다.

과거 성공 outcome.destination_head는 현재 catalog의 실제 prefix여야 한다. 기존 `BundleStore._locked/_load`로 전체 chain이 검증된 상태에서 bounded 기존 catalog reader/decoder를 이용해 `(sequence,hash)` 포함을 확인하고 마지막 `_load` 일치를 확인하는 좁은 read-only helper를 둔다. 새로운 catalog 검증/쓰기 엔진을 만들지 않는다. 정상 catalog extension은 허용하되 조작된 prefix·현재 graph 불일치는 거절한다.

release 기록 재사용 시 actual IncidentStore journal에서 해당 event의 실제 row previous head/sequence와 payload.incident_head가 맞는지도 확인한다. generic pure event constructor가 주장한 과거 head를 신뢰하지 않는다. 기존 actual lock/read/replay primitives만 쓰고 새 head를 채택하지 않는다. source/destination 등록 digest와 binding은 매번 actual 자료로 재도출한다.

record hook은 actual 후보 검증 뒤 owner/복구 검증을 수행하고 현재 heads를 읽어 event를 구성한다. `incident_store.commit(event, expected_head=payload.incident_head[1])` 뒤 실제 snapshot/backup/head 확인을 유지한다. 이미 같은 binding의 원 event가 있으면 actual provenance를 확인해 재사용한다. actual record commit 실패는 기존 incident namespace latch를 적용하고 `RECOVERED_SELECTION_RECORD_UNCONFIRMED`로 거절한다. 마지막 검증 실패 후 남은 기록은 역사적 증거이며 권한이 아니다. 다음 호출은 다시 모든 현재 검사를 수행한다.

NO_SELECTION은 `release_record_id=None`, `research_selection_ready=False`다. 과거 release가 있더라도 새 NO_SELECTION의 해제 근거로 노출하지 않는다. 정상 수치 탈락은 incident가 아니며 기존 raw·실패 후보를 지우지 않는다. 기존 서명/평가 증거와 bytes가 같고 현재 조건이 맞으면 재서명하지 않는다. 새 자료·재수집·다른 계산/코드/프로토콜은 새 승인 경계이고 기존 서명을 전용하지 않는다.

consumer 고정 진단 prefix는 `RECOVERED_SELECTION_`다. 최소 구분: `ACTUAL_INPUT_REQUIRED`, `ROUTE_REQUIRED`, `RESTORED_ATTEMPT_REQUIRED`, `VERIFIED_TARGET_REQUIRED`, `DESTINATION_CHANGED`, `DOCUMENT_CHANGED`, `ADDITIONAL_INCIDENT`, `DEPENDENCY_CHANGED`, `RELEASE_BINDING_CHANGED`, `RECORD_UNCONFIRMED`. 기존 실제 archive/owner/review/incident/store 진단은 개인정보 없이 보존할 수 있다. 임의 OS/경로/금액 메시지는 노출하지 않는다.

## 6. 동결 전 필수 검사와 보류 경계

순수 검사: 모든 extra/missing/type/bool-int/초과/시간/ID/참조/동일binding충돌; legacy golden bytes; event 1-pass replay; release 추가 후 기존 incidents/outbox/blocked 결과 불변. 실제 수직 검사: 실제 임시 owner 서명·actual route→손상→복구 terminal→source 소실→actual restored read→단일 issued family→source/factory/history→record→최종 검증. NO_SELECTION, 추가 사건·공유 dependency/사본, artifact/backup 변조, 가짜 event/결과, late signed revocation·만료·30초·날짜·owner prefix, record 실패·응답유실·재시작·동시head 변경을 포함한다. 실제 signer 재호출·registry reset·자동 주문은 0.

scope는 Upbit KRW spot의 기존 fixed/carry sealed selection이다. 일반 selector의 보류, 기존 손실 하한·위험정책, production source/coverage/계좌/활성화 게이트는 유지한다. actual fresh callback·서명 문서는 소유자의 입력을 대신하는 bool로 만들지 않는다. native Windows·실제 계좌·네트워크·Telegram 동작을 주장하지 않는다. 코드/검사 공동 동결 전 runtime은 실행하지 않는다.

사용자 명령 진입점은 같은 단위에서 병렬 구현한다. 담당은 `research_recovery_cli.py`, 운영 가이드, `tests/launch_recovered_selection_cli.py`를 맡아 source 옵션 없는 명시 `select-recovered`를 연결한다. 기존 bounded parser/loader와 실제 clock/provider를 재사용하고 signer·키 입력·자동 활성화를 추가하지 않는다. core/CLI를 함께 동결한 뒤 새 집중 검사와 관련 회귀를 수행한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
