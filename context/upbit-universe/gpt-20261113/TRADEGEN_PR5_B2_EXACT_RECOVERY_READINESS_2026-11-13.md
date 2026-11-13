# PR5 B2 — 서명에 연결된 정확한 원본 복구 설계

작성일: 2026-11-13. 읽기 전용 설계이며 복구 구현·실행·현재 운영 승인 기록이 아니다. 기준은 B1b-1 전용 트리 base `3ca4dee`와 개발 중인 archive attestation/auth/export 코드다. B1b-1 최종 검증 상태는 부모 세션 기록을 따른다. 기존 B1a/B1b 소스·테스트·실제 소유자 자료를 수정하지 않았다.

## 1. 권장 최소 수직 구현

**B2a: 손상 primary catalog를 사용하지 않고 독립 서명이 지정한 backup graph 전체를 읽어, 미리 명시적으로 provision한 별도 BundleStore에 정확한 raw/verified 원본을 복원한 뒤 실제 read/auth 경로로 재검증한다.**

기존 head를 재초기화하거나 backup의 head를 현재 head로 채택하지 않는다. 원래 손상 파일을 덮거나 삭제하지 않는다. 기존 논리 bundle digest/run/revision/attempt·원본 bytes는 유지하며 새 물리 위치와 복구 사건은 별도로 기록한다. 대상이 실패·미완료 `RAW_ARCHIVED`이면 그 상태 그대로 복구한다.

첫 결과는 **`EXACT_ARCHIVE_RESTORED`라는 보관 복원 사실**이다. 실제 선발·운영 재사용 판정은 B1b-2의 현재 승인/폐기/실제 전략 검증과 기존 운용 조건을 통과해야 한다. 자동 route 교체·arm·매매·head 수리까지 완료했다고 표시하지 않는다. 외부에서 복구 대상과 서명·roots를 명시해 호출하면 내부 복사·검증은 자동 수행하도록 하되, 장애 탐지 daemon/Telegram 전달은 별도 연결이다.

## 2. 현재 재사용 가능한 실제 코드

| 실제 근거 | 재사용 범위 | 사용할 수 없는 가정 |
|---|---|---|
| `bundle_attestation.py` | exact request/body/domain/Ed25519 검증. signed request 안에 raw와 optional verified manifest 전체, 모든 파일 SHA/길이/PayloadReference가 포함됨 | supplied public key만으로 소유자 신뢰 발급 불가. 보관 서명은 source/선발/복구 권한이 아님 |
| `bundle_auth.py:_authority`, `authenticate_bundle_attestation` | 실제 CurrentOwnerAuthority, 봉인 context, 현재 key/code·만료·30초 freshness·종료 시각 검사 | 현재 `_graph`는 primary와 backup 양쪽 정상 catalog를 요구하므로 primary 손상 복구에 그대로 호출할 수 없음 |
| `research_bundle_store.py:_objects` | backup의 object root는 명시 backup root 아래 `payload-objects` | `BundleStore.read_verified`를 fake store 또는 예외 무시로 우회할 수 없음 |
| `research_bundle_store.py:_manifest`, `_graph`, `_validate_graph` | exact policy/manifest/object graph/raw→verified 연결 검사 패턴 | `_load`는 catalog와 독립 head 일치를 요구함. 여기서 실패한 head를 읽은 파일에 맞춰 갱신하면 복구가 아니라 신뢰 경계 우회 |
| `evidence_objects.py:preview_payload, EvidenceObjectStore.read` | signed object policy에 따른 deterministic reference, manifest/chunk hash·길이·순서 검증, exact bytes 반환 | 객체 파일명 존재·부분 final·orphan은 유효한 백업이 아님. read는 누락 object를 만들지 않음 |
| `research_bundle_store.py:archive_raw, commit_verified` | 새 목적지의 기존 정상 append/head CAS/backup 검증 경로. 같은 ID 다른 bytes 거절 | 이 호출은 저장 사실을 만들 뿐 서명·선발/운영 승인을 발급하지 않음 |
| `tools/owner/research_bundle.py:provision_research_store` | 사용자가 명시하는 새 빈 연구 저장소 provision 및 최초 genesis/head 설정 | runtime recovery에서 호출하거나 손상 저장소를 비었다고 꾸며 재초기화할 수 없음 |
| `bundle_review.py` | 생성 파일명 `p-<logical_id>.bin`, exact packet 읽기/쓰기 검증, POSIX/Windows directory pin 패턴 | exporter는 primary 정상 graph를 읽으므로 장애 시 exporter 재실행으로 원본을 구할 수 있다고 가정하지 않음 |

B1b-1은 서명 envelope의 별도 backup을 아직 보장하지 않는다(`signature_backup_verified=False`). 복구 입력에는 손상 primary 밖에서 얻은 **exact 서명 문서**가 필요하다. 그 문서가 사라졌다면 로컬 unsigned manifest나 새 공개키를 대신 신뢰하지 않는다.

## 3. Primary catalog 없이 backup을 읽는 검증 순서

1. 명시한 attestation bytes와 기대 bundle digest를 strict parse한다. 소유자 신뢰는 실제 `CurrentOwnerAuthority`가 읽은 현재 key/context에서만 얻는다. 문서 내부의 키·`StoredBundle`·수동 승인 bool을 신뢰하지 않는다.
2. 별도 owner-only 검증 helper를 현재 auth와 공유한다. 실제 서명, scope, 현재 key/code, issued/expiry, context freshness를 확인한다. 이 helper만 성공했다고 payload 검증이나 현재 운영 승인이 끝난 것은 아니다.
3. signed request 안의 exact raw/verified manifest bytes를 복원한다. domain digest, bytes SHA, file set digest, raw→verified input archive 전체 연결을 기존 format/attestation validator로 검사한다. requested target과 다른 bundle을 같은 backup에서 발견해도 대신 사용하지 않는다.
4. 명시 `BundleStoreLimits`와 각 manifest의 storage policy/object policy digest를 대조한다. object chunk policy를 추측하거나 더 넉넉한 policy로 바꿔 같은 서명이 유지된다고 취급하지 않는다.
5. 기존 backup object root를 read-only로 연다. signed manifest bytes로 `preview_payload`를 계산하여 **catalog에서 가져오지 않은 정확한 manifest reference**를 도출하고, 해당 backup object가 같은 bytes인지 확인한다. 각 signed file의 exact PayloadReference로 모든 payload를 읽는다. 빈 파일만 signed length=0/hash(empty)/ref=None 규칙으로 b''를 복원한다.
6. raw의 모든 파일과 verified의 파생 파일까지 읽어 길이·SHA·reference를 다시 검사한다. 수치상 탈락 후보·보고서·source 파일·receipt log를 생략하지 않는다. partial/corrupt/missing 하나라도 있으면 전체 정상 복구로 판정하지 않는다.
7. actual owner 재관찰과 실제 종료 시각으로 key/code/expiry/freshness를 재확인한다. 오래 걸린 검증에 현재 시각만 붙여 observation을 새 것으로 만들지 않는다. verified graph 결과는 변경 불가 byte snapshot으로 내부에 보관한다.

primary catalog/head는 이 경로의 신뢰 입력이 아니다. backup의 `BACKUP_VERIFIED` 역사 표식도 필요조건을 대신하지 않는다. **외부에서 신뢰 검증한 서명 → exact manifest → 실제 backup bytes**가 근거다. 기존 B1a read의 fail-closed 동작을 바꾸지 않고 별도의 복구 전용 reader를 만든다.

첫 reader는 완전한 B1a backup object graph를 지원한다. signed request 자체에 있는 manifest bytes와 여러 다른 원본 복사본을 조합해 복원하는 확장은 후속 source adapter로 구분한다. 불완전 backup에 필요한 bytes가 다른 정확한 복사본에 존재할 가능성과, 현재 adapter가 찾을 수 없는 상태를 구분한다. 거래소 재조회나 재계산을 exact 원본으로 끼워 넣지 않는다.

## 4. 새 목적지로 복원하는 방법

목적지는 **실제 BundleStore exact 타입**, source backup 및 손상 primary와 겹치지 않는 명시 roots, 같은 signed storage/object policy를 사용한다. operator가 미리 provision해 유효한 genesis/head를 가진 저장소만 받는다. 기존 데이터가 있으면 같은 run/revision의 충돌을 기존 규칙으로 거절한다. 필요한 여유 용량·최대 파일/전체 bytes·임시 복사 peak를 복사 전에 admission한다.

복구 함수는 다음 경로를 실제 사용한다.

1. 앞 절의 전체 signed backup 검증을 수행한다. 이 단계가 실패하면 목적지 연구 bundle을 쓰지 않는다.
2. signed raw manifest bytes와 모든 raw 원본을 `destination.archive_raw`에 공급한다. 목적지 자체 backup도 full readback까지 완료해야 한다.
3. 원 대상이 verified이면 동일 raw를 연결하는 signed verified manifest bytes와 전체 payload를 `destination.commit_verified`에 공급한다. 기존 평가 결과·시각·source·보고서를 다시 계산해 덮어쓰지 않는다.
4. 목적지의 실제 `read_raw/read_verified(require_backup=True)`와 `authenticate_bundle_attestation`으로 exact 전체 묶음을 다시 확인한다. 형식상 동일한 dict나 caller가 만든 StoredBundle로 이 단계를 대체하지 않는다.
5. 서명 envelope와 복구 사건의 별도 보관·backup 결과를 확인한다. 원본 manifest 바깥의 복구 기록에 source/target 식별 commitment, attestation 서명 identity, 원 bundle digest, 단계·고정 오류 코드를 연결한다. 원본 bytes/서명 문서를 수정하지 않는다.

원본의 logical run/revision을 새 것으로 바꾸는 것은 exact 복구가 아니다. 물리적 위치와 복구 incident ID만 새로 만든다. 새 연구 계산·새 관측을 하게 되면 그때 새 연구/버전과 새 승인이 필요하다.

복구 중단 후에는 raw만 목적지에 확정됐거나 verified가 backup 미완료일 수 있다. 단계별 사실을 보존하고 같은 exact bytes 재시도로만 이어간다. 부분 파일·row·head 불일치를 잘라서 정상으로 만들지 않는다. 최종 인증 전에 만료/키·코드 변경이 발생했으면 bytes가 복사됐다는 사실은 보존하되 `RESTORED_ARCHIVE_NOT_CURRENT`로 보고하고 사용을 재개하지 않는다.

원본 store의 catalog/head를 복원하는 것이 아니라 **별도의 유효한 보관 경로를 새로 확정하는 것**이다. 기존 runner/provider를 가리키는 객체를 몰래 바꾸거나 실행 중 승인 경로를 새 목적지로 자동 교체하지 않는다. 기존 head와 손상 증거는 원래 위치에 남는다.

## 5. 제안 API와 파일 분담

아래는 아직 존재하지 않는 API 제안이다. exact 필드/오류 이름은 구현 전에 카드로 고정한다.

```python
SignedBackupSource(backup_root: Path, limits: BundleStoreLimits)

inspect_signed_backup(source, bundle_digest, attestation_bytes, *,
                      authority_provider: CurrentOwnerAuthority, clock) -> RecoveryInspection

restore_signed_backup(source, destination: BundleStore, bundle_digest,
                      attestation_bytes, *, incident_id: str,
                      authority_provider: CurrentOwnerAuthority, clock) -> RecoveryResult
```

`RecoveryInspection`은 확인 시점의 exact backup 사실이며 재사용 권한 토큰이 아니다. `restore_signed_backup`은 inspection 객체를 인자로 받아 검증을 생략하지 않고 자신의 호출 안에서 실제 검증을 수행한다. `RecoveryResult`는 raw/verified/서명 backup의 단계별 사실과 고정 진단, scope를 담으며 operational flags는 계속 false다.

| 소유 파일 | 변경 범위 |
|---|---|
| 새 `execution_launch/bundle_recovery.py` | signature-first backup reader, 명시 roots/policy, 전체 bytes 비교, 실제 destination store 복원, 결과 구분 |
| `execution_launch/bundle_auth.py`의 좁은 내부 공통 부분 | 실제 owner/context/key/code/expiry 검증 helper를 공유하되 기존 primary auth 경로·조건을 유지. public bool provider나 새 셀프 발급 권한을 만들지 않음 |
| 새 `execution_launch/recovery_record.py` 또는 기존 bundle 기반 사건 보관 adapter | signed document/incident의 불변 보관 및 backup. 원본 manifest와 별도 artifact이며 actual storage 소비자까지 연결 |
| 명시 CLI 및 관련 tests | actual backup graph→실제 목적지 BundleStore→실제 auth 통합. 초기화 명령으로 자동 전환하지 않음 |
| root의 guard/registry | 새 쓰기 경로는 원칙적으로 기존 BundleStore만 사용. 증거/사건 보관 경로와 허용 write call을 명시 검토 |

서명 envelope/incident를 같은 store에 보관한다면 원 연구를 수정하지 말고 별도의 `RAW_ARCHIVED` 보조 artifact로 저장한다. 그 artifact가 자기 신뢰를 발급하지 않으며, 대상 서명의 identity가 실제 verified body/domain에서 도출됐는지 consumer가 확인한다. 후속 재해 복구 때 signed document를 찾을 수 있도록 별도 서명 보관 위치와 index 정책을 명시해야 한다. B1b-1의 서명 backup 미구현 상태를 단순 성공 flag로 바꾸지 않는다.

## 6. 격리와 보류 범위

자동 복구가 손상 원본을 덮어쓰거나 전체 자료를 지워서는 안 된다. 첫 단계는 원본을 보존하는 **논리 격리**와 새 목적지 복원이다. 실행 중 writer가 있을 수 있는 root 전체를 임의 rename하지 않는다. 물리 이동이 필요하면 해당 writer 중지·잠금·원본 보존을 갖춘 별도 절차가 필요하다.

- 단일 bundle 파일 손상: 그 signed manifest를 사용하는 연구·승인·신규 진입 근거만 보류한다.
- 공유 object 손상: 그 reference를 사용하는 모든 확인된 의존 bundle이 영향을 받는다. 관계가 불명확하면 완전성을 검증할 수 없는 해당 저장 경로의 소비를 거절하고, 독립된 다른 연구까지 임의로 전역 halt하지 않는다.
- catalog/head 손상: 그 catalog를 신뢰해야 하는 소비자는 정상적으로 거절된다. 이것은 모든 연구 데이터의 폐기를 뜻하지 않는다. 서명 기준 복구 reader는 별도 경로에서 제한적으로 동작한다.
- 보유 자산: 자료 손상·저장 장애·복구·재시작은 매도 신호가 아니다. 기존 독립 위험/전략 자료와 권한으로 보유를 감시한다. 판단 불가 상태를 상승 예상 또는 실제 HOLD 판단으로 표시하지 않는다.

첫 복원 CLI가 runtime 의존 경로를 자동 통제한다고 주장하지 않는다. **지속적인 quarantine/hold 적용**은 실제 current-use consumer가 사건 상태와 현재 graph를 확인하도록 연결해야 완료다. 원 자료를 복원했다고 임의로 보류를 해제하지 않는다. B1b-2의 재검증과 기존 운용 준비 경로에서 해제 여부를 판단한다.

## 7. 재서명 없이 재사용할 조건과 B1b-2 의존

정확 원본 복구 자체에 새 서명을 요구하지 않는다. 그러나 B1b-1 archive attestation은 이미 operational use를 허용하지 않는다. 새 복구 기능이 이 서명 범위를 넓힐 수 없다.

현재 승인 재사용은 **정확 bytes + 기존 승인 범위 + 실제 현재 조건**의 교집합이다. B1b-2 담당의 계획 API는 다음과 같다.

```python
authenticate_sealed_study_selection(store, bundle_digest, *, archive_attestation,
    source_reviews, current_profile, window, history_head_root,
    history_storage_policy, clock, authority_provider) -> SealedSelectionAssessment
```

이 경로는 실제 A0b, 전체 eligible source reviews, 실제 선택 factory와 실제 LiveHistory 의존성을 검증한다. 새 signed revocation은 JSON whitespace나 envelope 표현이 아니라 **purpose + 실제 signing-domain/body digest의 서명 identity**를 대상으로 하는 제안이다. B2는 그 fresh 신뢰 조회를 재사용하며 임의 `revoked=False`를 넣지 않는다. 그 결과조차 actual activation/order/recovery permit은 아니므로 기존 위험·계좌·미체결·세션 준비가 별도로 필요하다.

기존 code hash가 바뀌었거나 키가 회전·폐기됐거나 서명이 만료된 경우 현재 B1b-1 auth는 거절한다. 과거 승인 코드·키를 신뢰 가능한 이력으로 검증하여 역사 자료를 복구하는 기능과 현재 운영 재사용은 별도다. 그 역사 검증이 구현되기 전에는 미지원이라고 반환한다. 개발 중 B2 코드를 추가한 뒤 옛 deployment hash 서명이 계속 현재 코드 승인을 뜻한다고 가정하지 않는다. 양성 테스트는 **B2가 포함된 동일 코드에 대한 실제 fixture 서명을 먼저 생성한 후 손상을 주입**한다.

정확 원본을 찾지 못하면 온전한 기초 자료의 새 버전 재계산, 새 관측 연구, 사용 중단 순서로 가능한 조치를 판단한다. B2a는 이 후속 연구를 자동 발급하지 않는다. 정상 기록된 조회 실패·실패 raw를 그대로 복구할 수는 있어도 missing 당시 응답/시각을 채워 넣지는 않는다.

## 8. 단계별 검증과 완료 기준

1. **서명 우선 read 경로:** actual B1a raw/verified와 backup을 생성하고 actual fixture signer로 문서를 만든 후 primary catalog를 손상시킨다. 기존 `read_verified`는 그대로 거절하고 새 reader만 signed exact backup을 읽는다. primary/head bytes 전후 불변, initialize/CAS 호출 0을 확인한다.
2. **전체 graph:** file 하나·manifest object 하나·raw 입력 링크·source/report·payload chunk·empty-file SHA·policy를 바꾼 경우 전체 거절. 수치 탈락 후보나 failed raw를 빼고 정상으로 반환하지 않는다. 다른 bundle/다른 유효 서명으로 대체 불가.
3. **실제 목적지 복원:** operator가 임시 destination을 미리 provision한다. 실제 `archive_raw/commit_verified/read`를 사용하여 exact 원본과 backup까지 확인한다. 원본과 다른 목적지 policy·중복 ID 다른 bytes·root 겹침·미provision head는 거절한다. runtime provision 호출 0.
4. **중단·변경:** source read, raw 저장, verified 저장, backup, head CAS/readback, 최종 auth마다 실패를 주입한다. partial 결과를 완료로 표시하지 않고 같은 bytes 재시도만 허용한다. copy 중 expiry/code/key 변경이면 보관 사실과 현재 사용 거절을 분리한다.
5. **신뢰·경로:** 실제 CurrentOwnerAuthority/context/crypto 경로를 사용한다. fabricated inspection/StoredBundle/authority bool, 현재 키와 다른 서명, stale/rollback, old-domain replay, 디렉터리/lock 교체·reparse·hardlink·Windows 예약명·예산 경계에 대한 회귀를 수행한다. Windows 보장은 실제 또는 명시 synthetic 검증 범위를 나눠 보고한다.
6. **비작용:** 같은 사건에서 다른 독립 연구의 원본이 유지되고, 실제 주문/arm/시장가 청산/거래 한도 변경은 0이다. 자기 복구를 위해 실제 owner key·현재 home·계좌 API를 사용하지 않는다. 테스트는 임시 roots/KEYLESS/fake 자료만 사용한다.

최소 완료 ID는 `PR5/B2a-exact-archive-restore`다. read helper만 만들면 이 ID를 완료하지 않는다. 실제 손상 primary를 둔 상태에서 **서명 → backup 전체 → 정상 destination store → 전체 read/auth/서명 보관 확인**까지 통과해야 한다. persistent quarantine의 운영 적용, 현재 선발 재검증·정상 재준비, 외부 알림 및 무인 trigger는 완료 범위에서 별도로 표시한다.
