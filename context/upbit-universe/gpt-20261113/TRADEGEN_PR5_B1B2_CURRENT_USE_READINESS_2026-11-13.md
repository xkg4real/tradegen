# PR5 B1b-2 — 제한적 철회와 확정본 연구 선발 연결 설계

작성: 2026-11-13. **설계 문서이며 구현·서명·실거래 완료 기록이 아니다.** 조사 대상은 `tradegen-bundle-attestation-1113`, HEAD **`3ca4dee3bcf007db63e2c2da83d8aba71f95c4e4`** 및 B1b-1 작업 변경본이다. B1b-1의 후속 수정·통합 검증은 부모 세션이 관리한다. 실제 소유자 홈·키·계좌·API는 사용하지 않았다.

## 1. 완료할 최소 수직 범위

신뢰한 현재 소유자 기록에서 문서 철회를 확인하고, **서명된 확정본 전체 → 실제 A0b 재평가 → 전체 후보 출처 검토 → 선택된 실제 실행기·history 연결 검증**을 한 경로로 연결한다. 결과는 해당 검증 시점의 **연구 선발 판정**이다. 거래 활성화, 주문, 계좌 적합성, 복구본 채택 또는 재시작 권한을 발급하지 않는다.

이미 정해진 요구는 다시 묻지 않는다. 실패·탈락 원본 보존, 확정본 불변, 정확 복구와 새 버전 구분, 기존 손실 하한·halt 유지, 기한만으로 매도하지 않는 규칙을 그대로 따른다. B1b-2 구현을 위해 실제 개인키·계좌 입력이 필요하지 않다. 운영 배포의 실제 서명은 기존 독립 소유자 절차로 남는다.

새 경로의 범위는 현재 B1a가 실제 지원하는 `forward-paper-v1` 및 `forward-paper-carry-v2`, Upbit 원화 현물의 고정 연구다. `forward-universe-v1`, 다른 시장·파생상품을 지원한다고 표시하지 않는다.

## 2. 실제 구현과의 차이

| 실제 파일·함수 | 구현된 사실 | B1b-2 변경 |
|---|---|---|
| `research_bundle_store.py:read_raw/read_verified` | catalog/head와 요청 graph 및 backup 원본을 실제 재검사 | 이 경로만 원본 공급원으로 사용. metadata receipt를 사용 가능 증거로 받지 않음 |
| `research_bundle.py:evaluate_sealed_study` | raw/verified 전체, source receipts, 현재 capture/program source, 실제 family 평가, evaluation record 및 manifest 정확 재생성 비교 | 동일 실제 평가 결과를 새 선발 경로에 연결. 임의 `SealedEvaluation` 입력 금지 |
| `study_evidence.py:evaluate_study_family` | 모든 원본의 사전검사 후 실제 평가·발급, 실패 후보도 보존 | 한 family를 한 번만 실제 평가. 임의 결과·`math_qualified=True` 입력 금지 |
| `bundle_auth.py:authenticate_bundle_attestation` | actual Store와 actual CurrentOwnerAuthority, 실제 graph/backup 재조회, 현재 코드·서명·시각 검증 | 보관 신원과 현재 사용의 철회 상태를 구분. 보관 서명만으로 선발 통과 처리 금지 |
| `study_review.py:authenticate_study_selection` | 모든 수치상 적격 후보의 family-bound source review를 검증하고 고정 순위로 선발 | 확정본 원본 공급원 및 철회 관찰을 연결. **현재 함수는 implementation_authenticated=False**이며 실제 실행기 검증까지 했다고 표현하지 않음 |
| `review_auth.py:verify_implementation_review`, `ReviewVerifiers.assess_bundle` | 실제 등록 driver identity 및 history callable identity와 승인 내용 대조 | 선택된 후보의 실제 factory/history 연결을 검사. 선발에 실패한 후보로 자동 대체하지 않음 |
| `coordinator.py:_compose_driver` | 실제 LiveHistory와 고정/carry factory 구성. 독립 history head를 임의 초기화하지 않음 | 새 경로에서 sealed plan/program/protocol과 명시 deployment 설정으로 호출 |
| `owner.py`, `model.OwnerState`, 독립 signer | signed owner chain, 신뢰 anchors, 키 회전·head rollback·현재 code approval | 새 **제한 전용** 철회 사건과 같은 봉인 Context에 포함된 철회 집합 |

기존 `study_review`에 sealed 재평가 결과를 넘기는 단순 연결은 불가능하다. 함수가 원본을 다시 평가하며, `strategy._EVALUATED`의 현재 상한은 **128개**다. 두 번 평가하면 큰 family가 자원 한도를 소모한다. production에서 registry를 지우거나 임의 capacity를 늘리는 방법으로 해결하지 않는다.

## 3. 제한 전용 철회 계약

### 3.1 서명 대상의 안정적인 식별

새 owner event의 권장 이름은 `research_attestation_revoked`이며 data는 다음 exact schema로 고정한다.

```python
{
    "purpose": "research_archive_manifest_attestation"
               | "strategy_source_and_fixed_implementation_review"
               | "strategy_source_and_fixed_carry_implementation_review",
    "target_sha256": "<64 lowercase hex>",
    "reason_code": "OWNER_WITHDRAWN" | "EVIDENCE_UNTRUSTED" | "REVIEW_ERROR",
}
```

`target_sha256`는 raw 파일 SHA가 아니다. 해당 purpose의 strict parser로 body를 읽고 **기존 실제 domain + canonical signing bytes**를 재생성한 뒤, 새 고정 domain `tradegen-research-attestation-revocation-target/1\n`을 앞에 붙인 SHA256이다. purpose와 원본 서명 의미는 변경하지 않는다.

현재 source-review parser는 JSON 공백·키 순서가 다른 같은 서명을 허용하므로 원본 JSON 파일 SHA로만 철회하면 재직렬화로 우회할 수 있다. canonical signed identity는 같은 승인 내용을 표현한 모든 envelope에 동일하게 적용된다. B1b-1의 `attestation_document_digest`는 원본 파일 식별용으로 계속 보존하고 새 철회 식별자와 혼동하지 않는다.

현재 키로 실제 서명한 사건만 인정한다. unsigned blacklist, Telegram 클릭, dataclass의 `revoked=False`, 복사된 Context는 철회 조회의 대체물이 아니다. document purpose별 parser/domain이 다르므로 owner-log 서명·옛 review를 다른 purpose로 승격하지 않는다.

### 3.2 효과와 시점

- 철회는 단조롭게 제한한다. 같은 target의 중복 철회는 같은 효과이며 취소·삭제·만료·자동 재활성화 이벤트를 만들지 않는다.
- 정상 검증된 owner log에 있는 철회는 **미래 UTC로 기록돼 있어도 즉시 제한**한다. 기존 halt·tightening과 같은 원칙이며 `_up_to`로 미래 철회를 제거하지 않는다.
- 다른 연구·다른 target은 계속 검증할 수 있다. 철회 때문에 전체 저장소를 격리하거나 모든 보유 자산을 청산하지 않는다.
- 같은 원본에 대한 새 승인 문서는 새 issued/expiry/body를 가지는 별도 소유자 판단이다. 기존 철회 행을 지우거나 기존 문서를 재사용하지 않는다.
- 키 회전·owner head rollback·코드 변경 처리와 한도 효력 날짜는 그대로 유지한다. 철회가 거래 규칙·금액·손실 하한을 완화할 수 없다.

### 3.3 신뢰 경로

`OwnerState`에 immutable `revoked_research_attestations` 집합을 추가한다. 요소는 `(purpose, target_sha256)`이다. 실제 `owner._owner_fold`가 **동일 verify_log 결과**에서 계산하고 `owner.load_context`의 Context seal/hash에 포함한다. 별도 파일을 나중에 읽고 이전 owner head에 끼워 넣지 않는다.

새 필드는 기존 Context hash 직렬화와 캐시/fixture에 영향을 준다. 빈 집합의 호환 처리 여부를 명시하고 golden vectors로 고정한다. signed owner-log의 과거 행 bytes를 수정하지 않는다. 새 사건을 모르는 구버전은 계속 fail closed해야 하며 이를 피하려고 행을 필터링하지 않는다.

현재 actual CurrentOwnerAuthority의 원래 observed_at, key/code/head pin, benign verified growth, rollback latch를 재사용한다. `ReviewAuthority`를 직접 만들어 입력하는 경로는 새 orchestrator에서 거절한다. 새 모듈의 실제 source는 기존 전체 D14 code approval에 포함하며 별도 작은 수동 hash 목록을 신뢰 근거로 만들지 않는다.

독립 signer에는 새 제한 사건 명령만 추가한다. 문서 원문을 strict parse하여 purpose/target을 독립 도출하고 철회할 대상을 표시한 뒤 기존 직접 확인·현재 키·owner log lock·서명 절차를 사용한다. 사용자 입력 digest를 무조건 믿고 다른 범위를 철회하지 않는다. 과거 키 문서를 현재 키가 제한하는 경우에도 그 입력 문서를 현재 승인으로 인정하는 것은 아니다.

## 4. 보관 확인과 현재 사용의 구분

| 결과 | 뜻 |
|---|---|
| archive identity authenticated | 현재 신뢰 키에 연결된 서명이 exact 보관 내용과 일치한다는 관찰 |
| revocation status = REVOKED | 해당 signed identity는 현재 선발/승인 사용에서 제외됨. 역사적 파일 보존은 계속함 |
| revocation status = NOT_REVOKED_AT_HEAD | **특정 실제 owner head와 관찰 시각**에서 철회가 없었음. 앞으로도 없다는 보장·재사용 token 아님 |
| revocation status = UNSUPPORTED/UNKNOWN | 필요한 구현·owner 자료가 없거나 확인 실패. 현재 사용 허용으로 해석 금지 |
| research selection ready | 아래 전체 경로에서 적격 후보와 선택된 구현의 검증이 완료됨 |
| execution ready | B1b-2에서는 항상 false |

B1b-1 `authenticate_bundle_attestation`의 archive-only 의미는 유지한다. revoked 문서가 보관 신원 검증을 통과하더라도 표시에서 철회를 숨기지 않으며 선발 함수는 이를 거절한다. 현재 source/implementation 검증인 `review_auth._authenticate`는 새 제한 집합의 해당 target을 반드시 확인한다. 따라서 source review를 다른 기존 호출 경로로 넘겨도 철회가 우회되지 않는다.

archive attestation의 철회는 이를 요구하는 새 sealed 선발 경로를 제한한다. legacy 연구 경로 전체가 새 archive 정책으로 이관됐다고 주장하지 않는다. legacy path는 archive-authenticated/sealed-selection 상태를 출력할 수 없다. 새 sealed 결과를 실제 실행에 연결하는 추후 경로도 매번 현재 제약을 확인해야 한다.

## 5. 전체 수직 흐름

1. bounded signature 원문과 명시 store/deployment 설정을 입장 검사한다. actual `BundleStore`, actual `CurrentOwnerAuthority`, 동일 trusted clock만 허용한다. JSON에서 callback/public key/authority 객체를 만들지 않는다.
2. `read_verified(require_backup=True)`와 연결 raw를 읽어 **전체 manifest·전체 파일·backup**의 현재 일치를 확인한다. RAW_ARCHIVED는 실패 원본으로 보존하되 선발 입력은 거절한다. working directory/capture 경로로 fallback하지 않는다.
3. `evaluate_sealed_study`의 실제 `_research` 경로를 한 번 수행한다. 전체 후보·receipt 기록·현재 capture/program source·사전등록 commitment·과거 연구 자료를 확인하고 실제 평가를 발급한다. 원래 evaluated_at으로 evaluation record/manifest를 정확 재현한다. 실제 조회 실패와 필수 기록 손상을 구분하는 기존 진단을 유지한다.
4. 현재 deployment profile의 economic contract와 rule terms가 sealed profile·각 protocol에 같고 asof가 신선한지 검사한다. historical profile의 asof를 현재 시각으로 임의 변경해 관측을 만들지 않는다. 원래 evaluated_at은 재현 시각이며 현재 승인 시각이 아니다.
5. 실제 재평가 결과로 eligible family를 계산한다. 결과가 수치상 실패한 후보도 complete family commitment에 포함한다. source review 문서는 **모든 eligible 후보와 exact 집합**이어야 한다. 서명 누락·불량 후보를 삭제해서 다음 후보를 선택하지 않는다. 수치상 적격 후보가 없으면 정상 `NO_QUALIFIED_MARKET`이며 source/factory/실행 허가를 만들지 않는다.
6. 새 archive attestation을 actual owner/code/key에 연결하고, 전체 eligible source reviews의 실제 signature·purpose/schema·family·computed summary·binding·expiry와 현재 철회를 검증한다. legacy request schema 2, carry schema 4 및 기존 body 1/2의 의미를 유지한다.
7. 각 source review의 `audit_sha256`를 **서명된 묶음에 이미 포함된 `role=report`의 실제 bytes SHA**와 exact 대조한다. eligible study마다 명시 report logical ID를 연결하고 임의 path를 읽지 않는다. 하나의 shared report가 여러 후보를 설명할 수 있으나 각 서명이 같은 hash를 직접 지명해야 한다. 보고서 hash 일치는 보고서의 주장이나 현재 계좌 증거를 자동 입증하지 않는다.
8. 고정 선발 규칙으로 한 후보를 고른 뒤, 그 후보의 실제 `_compose_driver`로 **등록된 factory + 실제 LiveHistory provider/verifier**를 구성한다. 명시 window·독립 head·storage policy를 사용하고 head가 없으면 거절한다. `describe_fixed_driver` 및 `verify_implementation_review`로 전체 driver identity, binding, 정확한 history callable identity를 검증한다. clone callback, fake HistoryReceipt, 임의 DriverComposition을 대신 받지 않는다. 실패 시 다른 후보로 fallback하지 않는다.
9. 대상 graph/backup을 다시 읽고 exact 최초 bytes와 비교한다. 같은 actual provider에서 owner를 새로 관찰하여 코드·키·head와 모든 관련 철회를 다시 확인한다. source review가 요구하는 active table·halt 조건도 유지한다. 보관 확인에서 trading table을 요구하지 않는 정책을 source review에 잘못 확장하지 않는다.
10. 모든 무거운 parse/hash/crypto 검사를 마친 **뒤** completion clock을 읽는다. clock rollback, Seoul 날짜, 각 원래 owner observation의 30초 lifetime, 모든 서명의 만료를 확인한다. 무거운 A0b 평가는 첫 owner snapshot 전에 수행할 수 있으나 서명은 평가 후의 실제 현재 시각에 검증한다. 새 관찰로 첫 snapshot의 유효기간을 덮어쓰지 않는다.
11. detached display assessment만 반환한다. source와 선택된 구현의 상태, exact digest, owner head/검증 시각을 기록하되 계좌·키·private path를 공개 출력하지 않는다. callback, 세션 capability, 재사용 가능한 승인 token을 반환하지 않는다.

`parent_bundle_sha256`, `prior_research` 및 source receipt hash만으로 **과거 모든 시도·원출처·공개시각의 진위가 자동 입증되지는 않는다.** 기존 source review의 전체 시도/사전 공개 검토 체크를 그대로 요구한다. 실제 관측 fixture의 진위를 입증하지 않은 연구는 서명 형식이 유효하다는 이유로 유의미한 실증 결과로 표시하지 않는다.

## 6. 최소 코드 변경과 API

권장 파일 경계는 다음과 같다. 실제 이름은 구현 시작 시 API 카드로 고정한다.

```python
# pure codec, no owner/key/store I/O
research_revocation_target(document: bytes, *, purpose: str) -> str

# New sealed-only orchestration; no caller-supplied evaluated result.
authenticate_sealed_study_selection(
    store, bundle_digest, *,
    archive_attestation: bytes,
    source_reviews: Mapping[str, bytes],
    audit_logical_ids: Mapping[str, str],
    current_profile, window, history_head_root,
    history_storage_policy, clock, authority_provider,
) -> SealedSelectionAssessment
```

- 새 `research_revocation.py`: bounded purpose→strict parser/domain routing와 target digest. 독립 signer에는 의미가 같은 독립 구현과 golden vectors를 둔다.
- `owner.py`, `model.py`, standalone signer: exact signed event, immutable same-context fold, 현재 제한 처리. 기본값만으로 신뢰를 부여하지 않는다.
- `review_auth.py`: 실제 fresh authority 안의 source/implementation 철회 검사. existing signature purpose를 수정하지 않는다.
- `bundle_auth.py`: archive identity와 현재 철회 상태 분리. display assessment를 authority 입력으로 받지 않는다.
- `study_review.py`: 원본 입장/실제 평가 이후의 **private shared authentication backend**를 분리한다. 기존 public 함수는 계속 원본을 실제 평가한다. 새 sealed orchestrator만 자신의 실제 sealed 평가 결과를 backend에 전달한다. private 함수라는 이유로 신뢰하지 않으며 모든 result의 실제 issuance·digest·raw family 연결 검사를 유지한다.
- `research_bundle.py`: 필요하다면 내부 재평가 결과에 plan/profile/exact snapshot을 동행시키는 private helper를 추가한다. 기존 공개 `SealedEvaluation` 객체의 construction/deserialization을 승인 근거로 쓰는 새 API는 만들지 않는다.
- 새 `sealed_study_review.py`: 위 흐름과 CLI. 실제 평가를 두 번 실행하거나 registry를 production에서 삭제하지 않는다. 자원 부족은 admission refusal이며 성공 결과를 만들지 않는다.

`SealedSelectionAssessment`에는 `archive_identity_authenticated`, `source_reviews_authenticated`, `selected_implementation_authenticated`, `research_selection_ready`, `verified_at`, 관련 digest 및 selection을 표시한다. **`execution_ready=False`, `automatic_recovery_supported=False`, `current_operational_use=False`**를 유지한다. 일반적인 `current_use_eligible=True`로 범위를 뭉뚱그리지 않는다.

선발 함수가 history를 구성할 때 기존 `LiveHistory.bind`의 명시적 쓰기가 발생할 수 있다. 이는 읽기 전용 인증이라고 설명하지 않으며, 허용된 기존 head 하에서만 수행한다. 별도 operator 초기화 전에는 거절한다. `arm`, account API, adapter order, 관리권한 연장, head 초기화·복구 채택은 0이다.

서명 문서는 detached로 둔다. audit report는 archive 확정 **전에** 포함되어 있어야 한다. 확정 후 보고서를 추가·수정하려면 새 연구 revision/bundle과 필요한 새 서명을 생성한다. 문서가 자기 자신의 signature hash를 포함하게 만드는 순환 참조를 만들지 않는다.

## 7. 작은 구현 순서와 필수 회귀

### B1b-2a: signed 제한 사건과 같은 Context

실제 임시 Ed25519 owner chain으로 기본·중복·미래 UTC 철회, 다른 target의 정상 진행, 새 키가 과거 문서를 제한하는 경우, owner log rollback/손상·재시작을 검증한다. raw JSON 공백/키 순서 변경으로 철회를 우회하지 못해야 한다. signer/app independent target bytes를 모든 purpose에서 대조한다. 기존 cap/floor/halt/다음날 효력 동작이 달라지지 않아야 한다. 잘못된 signature·purpose·unknown key·bool/중복 JSON은 거절한다.

### B1b-2b: 실제 sealed family → source 선발

actual B1a store/raw/verified/backup + 실제 receipt audit + actual A0b 발급 + 임시 실제 owner code/table approvals + 실제 detached archive/source signatures로 양성 경로를 만든다. 수치 실패 후보와 실패 raw를 보존한다. 위조 `VERIFIED_UNAPPROVED` metadata는 실제 재현 단계에서 거절한다. 한 후보 손상, 한 eligible review 누락·철회·만료, audit bytes 교체는 전체 해당 연구를 거절한다. 무관한 연구 object 손상/철회가 다른 연구를 막지 않는지 확인한다.

선발 backend는 기존 결과 발급 identity를 검사하며 dataclass 재구성·deserialize·copied report·인위적 PASS를 거절한다. family evaluation 호출 횟수 1을 검증하고, registry 상한을 넘기는 기존 잔여 평가가 있으면 수정 없이 admission 거절한다. 대규모 family는 소형 boundary fixture와 actual evaluator 사례를 구분해 보고한다.

### B1b-2c: 선택된 actual factory/history 및 시점 검증

legacy fixed와 carry 각각 실제 `_compose_driver` 및 명시 operator-step temporary head를 사용한다. wrong factory/revision/window/profile/terms/source closure, callback clone, history dependency 교체, absent head, head rollback은 거절한다. selected implementation 실패 뒤 낮은 순위로 재선발하지 않는다. archive-only 서명 하나로 source 또는 factory를 통과시키지 않는다.

평가·graph read·source signature loop·factory 검사 도중 철회/키 회전/코드 변경/만료/서울 자정/rollback을 주입한다. 마지막 heavy digest·crypto 뒤 실제 clock 검사도 검증한다. 완료된 display 결과를 다음 호출에 재사용하지 않으며, 반복 호출에서 실제 graph와 owner를 다시 읽는다.

각 단계의 기존 owner/compliance/review/selection/runner 관련 회귀와 exact write guards를 부모가 통합 검증한다. 테스트는 19 KEYLESS 설정, 임시 homes/keys/store, fake market source만 사용한다. 실계좌 장애 재현, Windows 실제 실행, iPhone/WebAuthn 승인을 Linux fixture로 대신 통과 처리하지 않는다.

## 8. B2 정확 복구와 연결

B2는 손상된 primary catalog 밖의 신뢰 서명·manifest로 backup bytes를 exact staging에 복원할 수 있다. 그 복원 결과나 staged manifest는 B1b-2가 받는 actual Store/current approval의 대체물이 아니다. 기존 독립 head를 자동 초기화·채택·되돌리거나 새로운 파일을 기존 catalog에 조용히 끼우지 않는다.

B1b-2의 판정은 지속적인 quarantine/보류를 해제하는 사건도 아니다. B2의 사고 기록·원본 보존과 새 store의 검증을 연결한 제한 상태 consumer가 구현되기 전에는 자동 route 전환이나 운영 재사용을 표시하지 않는다. 해당 후속 consumer는 실제로 보호된 사고 기록의 head/대상 의존성을 확인해야 하며, `quarantined=False` 입력이나 새 디렉터리로 복사했다는 사실로 기존 보류를 지우지 않는다.

복구가 기존 승인과 exact 같은 자료를 되살리고 현재 코드·키·서명 유효기간·철회·source/factory 조건도 전부 유효하면, 연구 선발 검증은 기존 서명을 사용할 수 있다. **복구했다는 이유만으로 재서명을 강제하지 않는다.** 변경된 계산·새 관측·새 report, 만료·철회·변경된 deployment 승인에는 이 예외가 적용되지 않는다. 그 뒤 실제 계좌·미체결 대조와 위험·세션 게이트는 별도다.

B1b-2의 코드 추가 자체는 전체 D14 hash를 바꾼다. 이전 코드에 연결된 실서명을 새 hash의 승인으로 옮겨 해석하지 않는다. 운영 설치 시 실제 새 code approval 및 변경된 서명 binding에 필요한 절차가 남는다는 사실을 안내한다. 개발용 임시 서명으로 이를 충족했다고 표시하지 않는다.

## 9. 완료 기준과 남는 범위

완료 기준은 별도 codec 수가 아니라 **actual store → current restrictive owner state → one actual sealed A0b family → exact signed archive/source audit/family → selected actual factory/history → fresh final revocation/time check**의 양성·음성 수직 경로다.

이 단계가 끝나도 실제 주문 활성화, 전체 universe sealed 연결, 전체 과거 시도 자동 진위 확인, historical-key 인증과 복구본 채택, backup에 서명 envelope를 자동 버전 보관하는 연결, Telegram/WebAuthn 등록·기기 분실·재등록은 완료로 표시하지 않는다. 금액·손실 하한·보호 보유 요구는 이 설계에서 변경하지 않는다.
