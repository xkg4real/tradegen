# PR5 B2b-2 — 사건에 연결한 정확 원본 자동 복구 제어기

2026-11-13. **설계만 작성했다. 새 코드·복구 실행·서명·배포·검증 PASS 기록이 아니다.** 읽기 기준은 `tradegen-incidents-1113`의 base `9944e6a` 및 개발 중인 B2b-1 파일이다. B2b-1 최종 검사·커밋 상태는 부모 세션 기록을 따른다.

첫 구현은 **미리 등록한 단일 복구 경로와 서명 원문을 대상으로, 실제 사건을 읽어 한 차례 exact 복구를 실행하고 시도·결과·알림 대기를 독립적으로 확정하는 수직 연결**이다. 이미 구현된 복사기를 다시 만들지 않는다. 손상 저장소의 원본·catalog·head를 보존하고, 별도 사전 준비 목적지에만 쓴다. B2b-1 보류는 그대로이며 현재 선발·거래 사용 권한을 발급하지 않는다.

## 1. 실제 구현과 새로 필요한 부분

| 실제 근거 | 현재 보장과 한계 | B2b-2 변경 |
|---|---|---|
| `execution_launch/bundle_recovery.py:inspect_signed_backup`, `_inspect`, `_read_graph` | 현재 owner/key/code/서명 기간을 확인하고 signed request의 raw·verified manifest와 전체 payload를 실제 backup object store에서 반복 읽는다. 손상 primary catalog/head를 사용하지 않는다. 반환값은 권한 토큰이 아니다. | 실제 사건·등록 경로·시도 기록에 연결. 서명 철회를 별도로 판정한다. |
| 같은 파일 `restore_signed_backup`, `_preflight`, `_restore_signed_backup` | 실제 BundleStore에 raw→verified(있는 경우)→서명 artifact를 확정·백업하고 대상 전체와 artifact를 다시 검증한다. source 검사/prewrite와 copy 후 최종 검증은 별도 30초 관찰 구간이다. copy 자체에 전체 30초 제한을 두지 않는다. | 호출 전 durable START, 호출 후 실제 대상 재검증과 durable outcome. 중단 시 반환 객체를 합성하지 않는다. |
| `recovery_artifact.py:build_recovery_artifact` | exact signature bytes와 대상/file-set/request commitment를 별도 raw archive로 보관. 결정적인 내용 기록이며 사건 발생·복구 완료의 증명이 아니다. | full incident hash와 기존 artifact ID 문법을 손실 없이 연결한다. |
| `bundle_auth.py:authenticate_bundle_attestation`, `_authority`, `_revocations` | actual provider와 전체 primary/backup graph를 검사. 최종 실제 owner head에서 `REVOKED` 또는 `NOT_REVOKED_AT_HEAD`를 **보고**한다. archive identity 보관을 위해 REVOKED도 assessment를 반환한다. | 자동 복구 경로는 실제 철회 집합을 검사해 철회된 서명을 자동 실행의 근거로 받지 않는다. generic archive-auth의 역사적 보관 의미는 바꾸지 않는다. |
| `bundle_recovery.py:RecoveryInspection/RecoveryResult` | `revocation_status='UNSUPPORTED'` 기본값과 모든 사용/운영 false flag가 남아 있다. 실제 미철회 판정이 이 객체로 전달되는 것은 아니다. | 새 controller observation에 실제 최종 canonical 철회 대상/head/관찰 시각을 별도로 기록. 기본값만 바꾸거나 old result를 현재 승인으로 취급하지 않는다. |
| `research_revocation.py:revocation_target`, `target_is_revoked` | purpose+기존 canonical signing bytes를 식별. 단순 파일 SHA와 다르며 생성자·빈 집합은 신뢰 근거가 아니다. | fresh actual sealed owner context에서 얻은 집합만 소비한다. |
| `research_incidents.py`, `research_incident_store.py` | REGISTER/FAILURE/DELIVERY, 독립 journal/version backup/head, 사건+보류+outbox 동일 전이. late dependent와 사본에도 보류 전파. | 기존 v1 사건 형식에 recovery 완료/해제를 끼워 넣지 않는다. 별도의 시도 기록을 사건 namespace와 연결한다. |
| `research_incident_monitor.py:namespace_identity`, `_inputs`, `register_target` | 실제 등록은 source roots/보존한 root identities/context에 묶이며 정상 graph를 검증한다. 손상 후 check는 기존 dependency snapshot으로 보류한다. | 복구 경로 사전 등록에서 이 실제 binding을 재사용. 임의 store ID나 `dependencies_verified=True`를 받지 않는다. |
| `incident_aware_selection.py:authenticate_incident_aware_selection` | 초기/최종 사건 검사와 completion head 재검사를 수행하며 held 대상은 거절한다. | **변경하지 않는다.** exact 목적지 사본도 같은 namespace에서 여전히 held다. |

기존 회귀에는 손상/missing primary catalog·head, raw 실패 원본 전체 복원, 원래 서명 bytes 백업, 일부 raw commit 후 exact 재시도, CAS 실패 보존, 최종 인증 실패, 느린 최종 artifact 읽기, 경로/lock 교체 등이 있다. 새 controller·durable attempt·실제 사건 연결은 이 기존 PASS로 검증됐다고 표시하지 않는다.

## 2. 최소 범위와 명시 등록

첫 단위는 `register route → 실제 incident → run_once → actual B2 복사·검증 → durable 결과+outbox → 재시작 조회/동일 시도 재개`다. daemon, 자동 파일 탐색, 여러 backup 후보 순회, Telegram 전송, source review 재발급, 새 연구 계산은 제외한다. run_once를 기존 supervisor가 호출할 수 있지만 새 자동 시작 서비스는 이 단위의 완료 조건이 아니다.

**복구 경로는 자료가 정상적으로 등록 가능한 동안 명시적으로 사전 등록한다.** actual 원 연구 BundleStore, 별도 사전 provision 목적지, exact 서명 문서, incident namespace를 실제 읽어 연결한다. 이 등록은 복구의 설정·내용 관찰이지 자료/전략/거래 승인 아니다. 실행 때도 서명·현재 owner·기간·철회를 다시 검사한다.

사전 등록이 필요한 이유는 B2b-1이 root identity가 포함된 store binding을 보존하지만 private 경로를 journal에서 복원해 주지는 않기 때문이다. 프로세스 재시작 뒤 primary 전체가 사라졌을 때 caller가 제공한 새 store ID로 원래 경로를 대신할 수 없다. 최초 단위는 사전 등록 경로가 없는 사건을 `RECOVERY_ROUTE_REQUIRED`로 남긴다. B2a의 명시 exact 복구 primitive는 유지하지만 이것을 자동 controller 등록을 우회하는 토큰으로 쓰지 않는다.

등록에는 다음 실제 commitments를 저장한다. 경로 문자열·서명 원문·연구 본문은 공개 출력에 넣지 않는다.

- incident namespace identity/context와 등록 snapshot의 head/sequence, 원 store binding, target/raw/full graph hash.
- source root 설정 commitment와 실제 root identities, backup object 정책, destination 설정/context/root identities/head-name commitment, 동일 storage/object policy.
- exact archive document digest, canonical revocation target/purpose, request/file-set/raw/verified manifest digest, 원래 issued/expires 시각과 deployment code hash.
- 별도 시도 저장소의 namespace/policy 및 제한된 retry 설정.

실제 서명 원문은 손상 원 연구 밖의 **명시적인 bounded signature artifact 입력**으로 공급한다. 첫 구현은 등록·run_once에 exact `bytes`를 받되 매번 등록 document digest와 실제 서명을 검증한다. 운영 CLI가 파일을 읽는다면 기존 strict bounded no-link reader를 사용한다. 디렉터리 탐색이나 임의 key 파일 로딩은 없다. 등록된 서명 원문이 없으면 현재 복구를 거절하며 새 서명을 요구하거나 내용을 합성하지 않는다.

source/destination 두 쌍의 roots, incident 세 roots, recovery-attempt 세 roots 모두 lexical/real containment와 실제 directory identity로 분리한다. recovery artifact도 destination에서 백업한다. runtime은 어느 head도 provision/seed/adopt하지 않는다. primary catalog나 head가 손상된 경우 실제 읽기는 signed backup만 사용한다. primary directory 자체가 missing이면 등록된 원래 lexical 경로/identity commitment를 유지하고 ‘현재 없음’을 인정하되, 새 directory identity로 원래 binding을 갱신하지 않는다. backup/destination/attempt/incident roots의 교체는 거절한다.

## 3. 제안 API와 파일 단독 변경 범위

다음은 **새로 구현할 계약**이다. 이름·정확 byte 필드/상한은 구현 시작 카드에 고정한다. 공개 생성자나 return dataclass는 실제 관찰의 대체 입력이 아니다.

```python
# new research_recovery.py
@dataclass(frozen=True, kw_only=True)
class RecoveryRouteConfig:
    source: SignedBackupSource
    destination: BundleStore
    # explicit safe roots/configuration only; no approved/revoked booleans

register_recovery_route(
    incident_store: IncidentStore,
    attempts: RecoveryAttemptStore,
    source_store: BundleStore,
    destination: BundleStore,
    bundle_digest: str,
    attestation_bytes: bytes,
    *, clock, authority_provider: CurrentOwnerAuthority,
) -> RecoveryRouteObservation

run_recovery_once(
    incident_store: IncidentStore,
    attempts: RecoveryAttemptStore,
    route: RecoveryRouteConfig,
    *, route_id: str, incident_id: str, attestation_bytes: bytes,
    clock, authority_provider: CurrentOwnerAuthority,
) -> RecoveryControllerObservation

# new research_recovery_attempts.py, strict pure event/reducer
# new research_recovery_store.py, explicit 3-root journal/backup/head
RecoveryAttemptStore(... explicit roots/head-name/limits ...)
    .inspect() -> RecoveryAttemptSnapshot
    .admit(event, *, expected_head) -> current_snapshot
    .commit(event, *, expected_head) -> confirmed_snapshot
```

`run_recovery_once`는 exact actual Store/provider 타입과 provider의 같은 clock을 요구한다. caller가 만든 IncidentCheck, RecoveryInspection, RecoveryResult, restored flag, owner context를 받지 않는다. incident는 실제 저장소 replay에서 full incident ID로 찾으며 해당 route의 bundle/raw가 실제 현재 dependency closure에 포함되는지 확인한다. 무관한 사건을 빌려 복구를 시작하지 않는다. normal numerical failure는 애초 복구 incident로 생성하지 않는다.

기존 IncidentStore는 특정 v1 codec·chain에 묶인 구현이며 임의 payload의 generic journal API가 아니다. 새 attempt store는 그 **검증된 append/version-backup/head-CAS/readback·root/lock pin 패턴**을 범위가 작은 별도 모듈로 사용한다. 기존 사건 파일을 재작성하거나 형식 migration을 암묵 수행하지 않는다. 공용 I/O 기반 추출은 필요성이 확인될 때 별도 검토하고 이번 단위의 전제로 두지 않는다. 모든 write/CAS caller는 guard에 명시한다.

### 기존 artifact ID 문법과 full incident 연결

B2b-1 incident ID는 64자리 hex SHA다. 기존 artifact ID는 `[a-z][a-z0-9_-]{0,63}`이므로 hex가 숫자로 시작하면 그대로 전달할 수 없다. 앞에 문자를 붙인 65자리나 잘라낸 digest도 쓰지 않는다.

새 adapter의 결정적 표현을 `i` + **32-byte incident SHA의 패딩 없는 lowercase Base32**로 한다(총 53자). 역변환 가능한 encoding이며 hash를 줄이지 않는다. attempt record에 full incident SHA, `incident-sha256-base32-v1`, 해당 artifact ID를 모두 고정·검증한다. 기존 `build_recovery_artifact` byte schema는 유지한다. 실제 artifact record의 ID와 attempt linkage가 exact 일치하는지 확인하며, 기존 artifact만 보고 사건 authenticity를 추론하지 않는다.

## 4. Durable 상태·중단·재시작 계약

새 domain은 B2b-1 사건과 분리한다. 최소 event는 `ROUTE_REGISTERED`, `ATTEMPT_STARTED`, `RESUME_STARTED`, `ATTEMPT_OBSERVED`, `DELIVERY_REPORTED`다. 모든 상태는 전체 strict journal replay로 도출하고, caller의 현재 상태를 신뢰하지 않는다. `ATTEMPT_OBSERVED`와 해당 **결과 알림 intent는 하나의 transition**이다. 보류 해제/새 승인/경로 전환 이벤트는 없다.

- `plan_id`: namespace+full incident+route+target/raw+exact document+destination/policy의 domain-separated digest.
- `attempt_id`: plan과 단조 증가 실행 번호에 연결. 같은 시도의 재시작은 같은 ID를 유지한다. 단순 함수 재호출만으로 새 문서/목적지/정책을 적용하지 않는다.
- `ATTEMPT_STARTED`: 전제 incident head/sequence, route 및 서명 commitments, 실제 최초 owner key fingerprint/code/head/checkpoint, trusted start 시각을 확정한다. **확정 전 destination write 0**.
- `RESUME_STARTED`: 같은 plan/attempt와 증가한 resume 번호를 확정한 후 실제 재검증·필요한 복사를 수행한다. 시작/재개 예산을 함께 세어 반복 crash로 시도 상한을 우회하지 못하게 한다.
- outcome은 `EXACT_ARCHIVE_RESTORED`, `PARTIAL_UNVERIFIED`, `READ_UNAVAILABLE`, `RESOURCE_LIMIT`, `AUTHORITY_REFUSED`, `DESTINATION_UNCONFIRMED` 등 고정 코드로 구분한다. 원인별 실제 관찰이 없는 범위를 단정하지 않는다. 특히 source를 못 읽었다고 원본 영구 소실이라 하지 않는다.
- 예산은 첫 단계 기본 한 번의 신규 시도와 최대 두 번의 동일 시도 재개(총 세 번의 execution start), 최소 60초 간격의 trusted due-time으로 제한하는 구체안을 권장한다. 더 큰 자동 반복은 지원하지 않고 명시 설정 검토 대상으로 남긴다. 한 run_once 안에 sleep/retry loop는 없다. unknown/rollback clock에서는 쓰기 복구를 시작하지 않는다.
- terminal authority refusal, code/key 변경, 원래 서명 expiry, 원 사건/route 변경은 자동 재개하지 않는다. 새 provider를 생성해 같은 실행의 latch를 우회하지 않는다. 새 문서/버전은 별도 route/plan이며 기존 attempt를 성공으로 바꾸지 않는다.

**건강한 저장소의 부분 commit과 미확정 journal은 다르다.** B2는 raw만 정상 확정된 상태에서 동일 bytes를 다시 실행하면 나머지를 완료할 수 있다. 반면 torn catalog/journal, head CAS 실패, orphan row/version은 자동 adopt/truncate하지 않는다. 해당 store를 보존하고 `DESTINATION_UNCONFIRMED` 또는 attempt-record refusal로 멈춘다. 자동으로 새 목적지를 만들어 계속 쓰지 않는다.

결과 event를 확정하지 못하면 성공 알림을 내보내지 않는다. 실행 프로세스는 해당 namespace를 미확정으로 latch하고 추가 복구를 거절한다. 재시작은 실제 journal/version/head를 먼저 검사한다. 모든 매체의 coherent rollback이나 기록 전에 전원이 끊겨 존재하지 않는 관찰까지 복원한다는 보장은 하지 않는다.

### 재시작 분기

| 마지막 확정 상태 | 다음 run_once의 실제 조치 |
|---|---|
| START 없음 | full actual incident/route/source/authority admission 뒤 START 확정, 그 후 복사 |
| START 후 crash, destination에 없음 | 같은 attempt 재개 예산/시각/checkpoint 검증 후 실제 B2 경로 실행 |
| raw 또는 verified만 정상 committed | 같은 signed manifests/bytes로 실제 B2 exact retry. 이전 정상 commit·실패 원본 유지 |
| target+artifact가 실제 완성됐으나 outcome 없음 | actual 목적지 전체/백업/서명 artifact를 새 bounded transaction에서 검증한 뒤 outcome 확정. cached result로 완료 만들지 않음 |
| 원 backup이 나중에 사라졌으나 destination은 완성됨 | 현재 B2 restore는 source를 먼저 읽어 실패한다. 이를 지원하려면 아래 새 **목적지 검증 전용 helper**가 필요하며 구현 전에는 완료 추측 금지 |
| destination 또는 attempts의 journal/head 불일치 | 자동 복구·재anchor 금지. 잔여 자료와 기존 보류를 유지하고 고정 진단 |
| outcome 확정, 응답만 유실 | 실제 journal replay로 historical completion과 동일 message ID 반환. 현재 권한/사용 가능은 재사용하지 않음 |

복구 전/후 서명·자료 commit마다 같은 provider의 key/code/head/clock pins를 유지한다. 새 프로세스의 CurrentOwnerAuthority는 과거 in-memory latch를 갖지 않으므로, attempt가 보존한 key/code와 마지막 owner head의 실제 verified-prefix 연속성을 다시 확인해야 한다. 현재 provider는 constructor에 checkpoint를 받지 않는다. **새 작은 checkpoint verifier가 실제 owner log의 기존 verify_log/prefix 검증을 호출하는 연결이 필요하다.** caller의 checkpoint 숫자만으로 통과시키거나 owner 내부 `_pinned`를 덮지 않는다. 명시 기록된 authority refusal은 새 프로세스에서도 terminal이다.

## 5. 실제 복구·현재 서명 검증 순서

1. **사건과 경로:** 실제 incident/attempt replay, namespace/root/config pins, route의 full registration/manifest commitments, 해당 사건의 dependency 범위를 확인한다. 이미 held인 graph를 `check_target`의 healthy bool로 만들려고 하지 않는다. held는 정상 선행조건이며 정상 원본 검사는 B2 signed backup 경로가 한다.
2. **source와 권한 admission:** actual `inspect_signed_backup`와 실제 CurrentOwnerAuthority를 사용한다. canonical revocation target을 실제 현재 sealed owner의 restrictive set에서 확인한다. `_authority`만 호출하면 철회 거절이 되지 않는다는 점을 코드로 명시한다. 원래 issued/expires·D14 code·current key·KST date·owner log prefix를 검증한다.
3. **START와 capacity:** attempt event/outcome/outbox의 제한된 공간과 destination의 전체 raw/verified/artifact 예산을 사전 점검한다. admission은 미래 공간 보장이 아니다. START를 independent head까지 확정하고 실제 readback한다. incident/attempt locks를 모두 해제한 뒤 복사한다.
4. **B2 exact 실행:** 기존 `restore_signed_backup` 호출. 손상 원본을 이동/삭제/수정하지 않고 source catalog/head를 채택하지 않는다. fixed original candidate list와 recorded failed/incomplete raw bytes까지 모두 보존한다. 새 download·recalculation·report 수정은 exact 복구가 아니다.
5. **최종 검증 transaction:** 복사 뒤 새 실제 owner 관찰을 잡고 target/raw primary+backup 전체, original signature artifact+backup, incident/route/attempt 관찰을 다시 읽는다. 최초 최종 관찰부터 모든 무거운 검증·마지막 owner 재관찰까지 30초 한도를 유지한다. 원래 expiry와 KST date를 완료 clock으로 비교한다. 긴 복사를 제한 없이 승인하는 것이 아니라, 복사 후의 **새 실제 graph 검증**을 별도로 요구하는 구조다.
6. **철회와 결과 기록:** 마지막 actual owner head의 exact canonical target에 대해 미철회인지 확인하고 원 signature/deployment binding을 재검증한다. 결과에는 `verified_at`, owner head, document/target/artifact digest를 사실로 기록한다. 새 시각으로 서명 효력이나 30초 관찰을 연장하지 않는다. outcome+outbox를 확정하고 readback한다.
7. **반환 의미:** 결과는 그 head·시각에서 관찰한 exact 자료 복구다. durable 기록 작업 중 만료/owner 변경 등이 발생했다면 ‘현재 유효’라고 새로 주장하지 않고 `current_status_unconfirmed`를 분리한다. 모든 current-use/selection/operational flags는 false다. historical completed record를 이후에도 실제 현시점 미철회로 표시하지 않는다.

### 필요한 작은 실제 검증 helper

`bundle_recovery.py`의 copy 후 validation 부분을 공유하는 내부 helper를 추출하는 것이 가장 작은 변경이다. 제안 public adapter 이름은 `verify_restored_archive(destination, bundle_digest, attestation_bytes, *, incident_id, authority_provider, clock)`이며, 실제 구현에서는 controller 전용 private helper여도 된다.

- 입력은 actual destination와 exact signature뿐이며 기존 RecoveryResult/StoredBundle을 받지 않는다.
- 기존 `build_recovery_artifact`로 **기대 bytes만** 계산하고 actual artifact `read_raw(require_backup=True)`와 exact 대조한다.
- actual `authenticate_bundle_attestation`가 target/raw 전체를 반복 읽게 하고, artifact도 다시 읽는다. source backup은 요구하지 않는다. 따라서 성공-return 전 crash 후 원 backup이 unavailable이어도 이미 완성된 destination의 사실을 independently 재검증할 수 있다.
- 원래 source/destination/route disjoint binding은 controller가 고정하고, helper는 새 authority나 restoration token을 발급하지 않는다.
- `_authority`/revocation helper·fresh-time 비교는 기존 코드의 의미를 재사용하고 별도 서명 codec을 복제하지 않는다. 별도 verified-report clone이나 `verified=True` 입력은 없다.
- existing B2 `restore_signed_backup`의 exact byte·partial commit·30초 phase 의미를 유지하고 관련 전체 회귀를 다시 실행한다.

## 6. 재서명·해제·거래와의 경계

정확한 원본 복구이고 원래 서명 대상 bytes·scope·유효기간·current key/code·철회 및 다른 승인 조건이 모두 계속 충족하면 **복구를 했다는 이유만으로 새 서명을 요청하지 않는다.** 원 서명 bytes를 그대로 보관하고 결과 알림만 만든다. 무재서명은 승인 기간 연장이나 새 code/source/strategy 버전에 대한 승인 승계가 아니다.

첫 controller가 실제 확인하는 승인은 **archive identity attestation**이다. source review, 모든 eligible candidate의 평가·검토, 선택 factory/history/위험 정책, 활성화까지 유효하다고 주장하지 않는다. 그것들은 후속 actual sealed selection과 별도 현재 사용 binding에서 원래 scope별로 다시 확인한다. 소스 변경으로 D14 hash가 달라지면 필요한 새 코드 검토는 binding 변경 때문이며 exact 복구 자체의 추가 서명 의무와 구분한다.

정확 원본이 없지만 기초 자료로 다시 계산하는 경우는 새 run/revision/evaluator 결과이며 기존 승인을 적용하지 않는다. 당시 호가·지연·조회 실패·후보 자료가 없으면 새 연구 관측이 필요하다. 두 경우 모두 별도 새 승인 절차가 필요하지만, 이 controller는 재구성/재실행이나 승인 요청을 자동 생성하지 않는다. 원본 복구 실패만으로 다음 단계를 임의 선택하지 않는다.

**B2b-1 보류 해제 API는 추가하지 않는다.** 복구 목적지를 등록해도 logical bundle/raw에 묶인 기존 hold가 계승된다. 후속 사용 재개 단계에는 최소한 다음 exact 새 binding이 별도로 필요하다: original incident namespace/head, 사건·의존 closure 전체, 원래 full manifest, 교체 목적지 실제 graph/head, fresh actual owner/revocations, 실제 source review/family/factory/history, 소비자가 읽는 route version. 단순 새 폴더, historical result, `held=False`, copied assessment로 대신할 수 없다. 이 binding의 명세·실제 consumer 검증 전에는 정상 선발 route로 바꾸지 않는다.

새 코드에는 arm/order/cancel/sell, 보호 하한 변경, halt 해제, strategy HOLD 추정이 없다. 계좌/보유 관리가 연결됐다고 표시하지 않는다. 원래 E 결정도 유지한다: 기한만으로 매도하지 않으며 새 관리 승인 요청·권한 만료 경계는 복구가 연장하지 않는다.

결과 notification intent는 `RECOVERY_EXACT_ARCHIVE_RESTORED` 또는 고정 refused/partial 결과와 짧은 공개 식별자, `QUARANTINE_REMAINS`, `CURRENT_USE_NOT_GRANTED`만 담는다. 서명 원문/연구 가격/경로/키는 첨부하지 않는다. 전달 reported outcome은 별도 attempt ID로 기록하며 중복/unknown을 보존한다. 전달 성공·미응답·버튼 클릭은 승인이나 해제가 아니다. 실제 전송/Face ID/WebAuthn은 이번 단위에 구현하지 않는다.

## 7. 구현 분할과 완료 검사

추천 파일 분할은 ① pure route/attempt/outbox codec·reducer, ② 독립 RecoveryAttemptStore와 owner-only 빈 저장소 provision utility, ③ 실제 controller+기존 B2 최종검증 helper, ④ 실제 임시 저장소·서명·사건 통합 검사다. 기존 B2b-1 형식/보류 의미와 기존 서명 domains를 유지한다. 테스트부터 임의 result authority나 실제 key가 필요한 준비로 대체하지 않는다.

최소 수직 완료 검사는 다음과 같다.

1. 실제 temporary owner log/일회용 테스트 서명+실제 두 연구 A/B+실제 incident store: A의 primary catalog/head를 손상→A 사건 확정→signed backup 복구→별도 destination raw/verified/all files/artifact backup exact→outcome/outbox 확정. A 원본 bytes/head 그대로, B 그대로, 양쪽 operation 권한 0.
2. 실제 failed/incomplete raw와 모든 탈락 후보를 보존. 한 후보 누락/수정/실패 기록 재다운로드로 대체하면 exact 복구 거절. 성공 후보 subset만 복원하지 않는다.
3. actual owner에서 서명 철회·key/code 변경·expired/future·KST 경계·clock rollback·느린 최종 graph/artifact/attempt 읽기를 주입. source검사/prewrite/final 각 단계에서 거절되고 current-use false 유지.
4. START 확정 전, raw commit 후, verified commit 후, artifact backup 후, 실제 B2 성공-return 후 outcome 전, outcome/head CAS 전후 각각 중단. 정상 부분 commit은 exact 동일 retry, 미확정 journal/head는 거절. 캐시/constructed result가 완료 근거가 되지 않음.
5. destination만 완성하고 원 backup을 unavailable로 만든 뒤 재시작: 새 목적지 helper가 실제 전체 graph+원서명 artifact를 검증해야만 완료 기록. helper가 없거나 artifact가 없으면 완료 금지.
6. 새 프로세스에서 actual owner prefix/checkpoint 연속성, same route/document/policy/incident, retry+resume 총횟수/시간 제한. known authority refusal을 provider 재생성으로 우회하지 못함.
7. ledger/root/lock/head 교체, symlink/reparse/hardlink, 원 연구와 destination/incident/attempt roots overlap, CAS/backup/readback 오류, exact byte/row/candidate quota 경계. 원본 삭제·정상 quote None 처리·자동 seed/adoption 없음.
8. full incident hash Base32 adapter의 0–f 첫 nibble·역변환·기존 artifact 문법·다른 사건 혼동 거절. 목적지 artifact ID와 journal full incident linkage를 실제 비교.
9. 결과 outbox와 outcome 원자성, delivery unknown/failed/duplicate/restart, stable message ID. 실제 network/Telegram/signer 호출 0.
10. 복구 뒤 actual incident-aware selection은 여전히 held로 거절. 다른 independent B는 가능. 새 copy/route/ID 변경이 보류를 지우지 않음.
11. operation count로 store replay의 반복 prefix 검증 폭증을 방지하고, strict parser가 byte/row/depth 제한을 먼저 검사함을 검증. synthetic Linux 검사를 실제 Windows 전원 장애 또는 계좌 장애 사례로 보고하지 않음.

19 KEYLESS, 임시 홈, fake 가격, 일회용 테스트 서명만 사용한다. 실제 사용자 홈/API/key 접근이나 공개 경로·금액 출력은 없다. 최종 source 동결·fingerprint·guard·기존 B2/auth/revocation/incident 회귀 결과를 별도 실행 기록에 남긴 뒤에만 구현 완료로 기록한다.

코드·hermetic 검증을 시작하는 데 새 사용자 질문은 없다. 실제 배포에는 기존에 남겨 둔 독립 확정/백업/incident/attempt/head 위치, 사전 provision 목적지, 유효한 원 서명 문서 및 해당 배포의 실제 코드 승인 설정이 필요하다. 값이 아직 없으면 명시 인자를 요구하고 실홈 기본값이나 가짜 승인을 넣지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
