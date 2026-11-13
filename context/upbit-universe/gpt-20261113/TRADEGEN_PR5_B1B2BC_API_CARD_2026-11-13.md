# PR5 B1b-2b/c — 확정본 선발 API·소유 계약

작업 트리 `/workspace/tradegen-sealed-selection-1113`, base `797e8f5b934127734ae1207daaced9d1c3501200`. 이전 트리 수정 금지. 사용자가 이미 허용한 단계 구현이며 실제 키·계좌·API·주문·활성화는 사용하지 않는다. 2a의 canonical 철회와 durable owner anchors를 그대로 소비한다.

## 소유

| 담당 | 파일 |
|---|---|
| pr4e_coordinator | 새 `execution_launch/sealed_study_review.py`, 새 `tests/launch_sealed_study_review.py`, 카드 |
| protective_hold_design | `execution_launch/study_review.py` private backend 추출, 관련 legacy/새 backend tests |
| notion_revision | `execution_launch/research_bundle.py` private sealed snapshot 추출, 관련 helper tests |
| pr4e_owner | 새 `execution_launch/sealed_study_cli.py`, 새 `tests/launch_sealed_study_cli.py` |
| root | registry/guards/통합 검증/commit/문서 |

CRLF 파일은 그대로 유지한다. 동결 후 부모의 통합 검증 전에는 소유 밖 파일을 바꾸지 않는다.

## 실제 sealed 평가 helper

```python
@dataclass(frozen=True, kw_only=True)
class _SealedStudySnapshot:
    bundle_digest: str
    input_archive_digest: str
    evaluated_at: datetime
    plan: StudyPlan
    profile: LaunchProfile
    family: FamilyEvaluation
    raw_manifest_bytes: bytes
    verified_manifest_bytes: bytes
    files: Mapping[str, bytes]  # fresh dict wrapped in MappingProxyType

_evaluate_sealed_study_snapshot(store, bundle_digest) -> _SealedStudySnapshot
```

구현은 actual `BundleStore.read_verified/read_raw(require_backup=True)` → `_research` → exact manifest/evaluation-record 재생성을 한 번만 수행한다. public `evaluate_sealed_study`는 이 helper 한 번과 기존 표시 dataclass로의 투영을 사용한다. helper의 plan/profile/program/protocol/raw bytes는 sealed graph에서만 얻는다. 외부 snapshot을 승인 입력으로 받는 API는 만들지 않는다.

최종 graph 재확인은 orchestrator가 actual store read 또는 `bundle_auth._graph`를 사용한다. 두 번째 `_research`, 평가·발급, registry clear는 호출하지 않는다.

## 인증 backend 추출

```python
_authenticate_evaluated_selection(
    plan, *, profile, evaluated: FamilyEvaluation, reviews,
    evaluated_at, clock, authority_provider, initial_now=None,
) -> AuthenticatedSelection
```

기존 public `authenticate_study_selection`은 admission → `evaluate_study_family` **1회** → 위 backend로 유지한다. public 초기 clock을 `initial_now`에 전달해 기존 rollback 경계를 보존한다. 새 orchestrator는 sealed helper가 실제 발급한 family만 내부에서 전달한다.

backend는 exact FamilyEvaluation/EvaluatedCandidate, 전체 candidate 집합, raw bytes·SHA, plan registry, actual `_EVALUATED` result identity/digest, protocol/time/source 및 decoded inputs_digest 연결을 검사한다. 단순히 private 함수이거나 dataclass 타입이 맞는다고 신뢰하지 않는다. 이 재검사는 입력 parsing/검증이며 evaluator/시뮬레이터/발급 호출은 0이다. 모든 eligible 후보의 exact family-bound source review와 고정 순위 규칙은 그대로 유지한다. legacy callback-provider API는 유지하되 새 orchestrator는 actual provider만 허용한다.

## 새 orchestrator

```python
authenticate_sealed_study_selection(
    store, bundle_digest, *,
    archive_attestation: bytes,
    source_reviews: Mapping[str, bytes],
    audit_logical_ids: Mapping[str, str],
    current_profile: LaunchProfile,
    window: DeploymentWindow,
    history_head_root: Path,
    history_storage_policy: HistoryStoragePolicy | None = None,
    clock, authority_provider: CurrentOwnerAuthority,
) -> SealedSelectionAssessment
```

입력 exact Store/profile/window/provider와 provider의 동일 clock을 확인한다. signature/audit mappings는 한 번 snapshot하고 exact 타입/개수/크기를 검사한다. caller의 public key, cached report, 임의 evaluator result, callable authority, DriverComposition을 입력으로 받지 않는다. profile/window는 현재 명시 설정이며 실제 계좌 증거는 아니다.

1. 원본을 한 번 실제 평가하고 source/evaluation-record를 exact 재현한다. RAW_ARCHIVED는 선발 근거로 거절한다. fixed v1과 fixed carry v2만 허용하며 universe/다른 시장 지원을 확장하지 않는다.
2. 무거운 평가 뒤 actual owner 관찰을 시작한다. 실제 `bundle_auth._authority` 및 `_graph`로 archive signature와 exact sealed graph를 연결하고 canonical target의 현재 철회를 거절한다. source 조건과 섞어 archive-only signature를 source approval로 승격하지 않는다.
3. current_profile의 frozen economic contract/rule terms가 sealed 각 protocol과 맞는지 확인한다. asof만 임의 갱신해 관측을 만들지 않는다. backend는 actual family로 모든 eligible source reviews를 검증한다. signature 하나가 누락/변조/철회됐다고 후보를 삭제하지 않는다.
4. `audit_logical_ids`의 keys는 source_reviews와 exact 같다. 각 값은 signed verified manifest의 `role=report`, required=True, nonempty 파일이어야 하며 actual bytes SHA가 해당 source body.audit_sha256와 같아야 한다. study_id 메타데이터가 있다면 해당 후보와 같아야 한다. shared report도 각 서명이 그 hash를 직접 지명해야 한다. report hash가 출처 진위나 현재 account audit까지 자동 검증하지 않는다.
5. 고정 선발 결과의 선택 후보를 actual `coordinator._compose_driver`로 구성한다. sealed program/protocol, 검증한 current profile variant, 명시 window/head/storage policy와 actual LiveHistory를 사용한다. 독립 history head가 없으면 거절하며 provision/initialize하지 않는다. 현재 factory identity/정확 history callable과 selected source document의 implementation binding을 `verify_implementation_review`로 대조한다. 실패 시 낮은 후보로 다시 선발하지 않는다.
6. actual store graph/backup를 다시 읽어 최초 sealed snapshot과 비교한다. 같은 actual provider에서 final owner를 다시 읽고 archive 및 모든 eligible source reviews의 current code/key/revocation/expiry를 재검증한다. 선택된 실제 driver/history도 final identity와 대조한다.
7. 모든 heavy parse/hash/crypto 뒤 completion clock을 읽는다. 처음 authorization observation의 30초 수명, clock rollback/Seoul 날짜, archive/source 문서들의 만료와 current profile freshness를 유지한다. 새 owner 관찰로 이전 관찰 timestamp를 덮어쓰지 않는다. finite observation이며 filesystem lease가 아니다.

적격 후보가 없으면 `NO_QUALIFIED_MARKET` 결과를 유지하며 source/selected-implementation flags=false다. 이 경우에도 exact archive 및 현재 철회/graph 검증은 통과해야 한다. actual factory/history 생성은 하지 않는다.

```python
@dataclass(frozen=True, kw_only=True)
class SealedSelectionAssessment:
    scope: str  # 'sealed_research_selection'
    bundle_digest: str
    input_archive_digest: str
    attestation_sha256: str
    revocation_target_sha256: str
    revocation_owner_head: tuple[int, str]
    selection: MarketSelection
    evaluated_at: datetime
    verified_at: datetime
    authenticated_study_ids: tuple[str, ...]
    archive_identity_authenticated: bool
    source_reviews_authenticated: bool
    selected_implementation_authenticated: bool
    research_selection_ready: bool
    revocation_status: str = 'NOT_REVOKED_AT_HEAD'
    execution_ready: bool = False
    current_operational_use: bool = False
    automatic_recovery_supported: bool = False
```

선택 함수는 실제 `LiveHistory.bind`의 기존 명시적 기록을 만들 수 있으므로 읽기 전용이라고 표현하지 않는다. 반환에 callback/session/권한 token은 없다. code-bound 기존 서명을 다른 deployment로 자동 승격하지 않으며 실제 승인·risk·account·session·보호 보유·quarantine 해제는 별도다.

## CLI

```text
python -m execution_launch.sealed_study_cli select-sealed
  --sealed-root ROOT --backup-root ROOT --head-name NAME --limits LIMITS.json
  --digest SHA --archive-attestation FILE.json --profile PROFILE.json
  --window WINDOW.json --head-root ROOT [--history-storage POLICY.json]
  [--source-review FILE.json ...] [--audit STUDY_ID=LOGICAL_ID ...]
```

기존 explicit bounded path readers/open_explicit_store, fixed 24h read_window, optional parse_policy를 사용한다. review study ID는 bounded strict signed document에서 도출하며 중복을 거절한다. audit는 하나의 `=`만 허용하고 중복/빈 ID를 거절한다. actual CurrentOwnerAuthority와 하나의 UTC clock을 직접 구성한다. --now/provider/key/report/arm 옵션은 없다. 입력·설계에 필요한 새 서명은 만들지 않는다. 완료 출력은 dataclass 표시와 false operational flags이며 no provisioning/API/order다.

## 핵심 검증

actual retained receipts+전체 후보 capture → actual B1a finalization → 같은 원본의 actual single reevaluation → 임시 실제 owner code/table 서명 → actual archive/source signatures → 실제 preprovisioned history head/factory 연결의 양성 경로가 필요하다. 수치 결과나 PASS를 교체하지 않는다. 개발 fixture는 명시 fake market source이며 실증 수익 증거가 아니다.

single evaluation/발급 횟수, 후보 실패 보존, forged/unissued/mutated family, missing/revoked/expired source, audit mismatch, archive 철회, final graph/backup 손상, actual final owner 변화, actual factory/window/history 불일치, head 미설정, 최종 crypto 지연·만료·30초·clock rollback, no-qualified/no history write, cached result 재사용 거절을 검증한다. 실제 user home/키/API/orders 없음, KEYLESS 임시환경, QA는 부모만 관리한다.

## 구현 검토 보완

- 최종 history 검사는 실제 `_durable_unchanged()`에 이어 `_replay(identity, install=False)`로 전체 원본을 다시 읽는다. legacy journal의 같은 길이 변조는 크기 검사만으로 충분하지 않으므로 전체 row/hash/chain 및 독립 head를 대조한다. 재검사는 새 head 초기화·채택·수정 없이 수행한다.
- 적격 후보가 없는 경로에도 경제 계약, current profile 전체 설정, 관측 시각의 freshness 검사를 적용한다. 과거 sealed profile의 asof는 원본 재현용으로 유지하며 현재 명시 profile의 asof만 별도 입력으로 검사한다. 새 timestamp를 설정하는 것 자체를 실제 관측의 증거라고 주장하지 않는다.
- 문서 mapping은 처음 길이를 제한하고 실제 열거도 129번째 전에 중단한다. 같은 key를 반복하는 custom mapping을 거절한다.
- 구현 인증 실패 뒤 정상적으로 남은 bind journal을 지우거나 되돌리지 않는다. 반환 assessment는 실제 실행기 callback을 전달하지 않으며, 별도의 계좌·위험·session·활성화 절차를 대체하지 않는다.
