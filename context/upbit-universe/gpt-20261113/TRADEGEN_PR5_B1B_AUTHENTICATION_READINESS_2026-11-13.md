# PR5 B1b — 전체 연구 묶음 인증 구현 준비

작성일: 2026-11-13. 읽기 전용 조사이며 새 서명·승인·복구 기능의 구현 완료 기록이 아니다.

조사 기준은 B1a 전용 작업 트리의 base `2879b53` 및 개발 중인 bundle format/store/adapter다. B1a 통합 검사는 부모 세션이 진행 중이므로 이 문서에서 최종 통과·병합을 주장하지 않는다. 실제 소유자 자료·키·계좌·API를 읽거나 호출하지 않았다. 아래 파일 경로는 저장소 내 상대 경로다.

## 1. 다음 최소 수직단계

**B1b-1: 실제 B1a 묶음에서 제한된 검토 패키지를 만들고, 기존 독립 signer가 전체 manifest와 모든 원본 파일의 해시를 확인하여 새 범위로 서명하며, 앱의 별도 인증 명령이 실제 B1a graph와 외부 소유자 신뢰를 다시 검사하는 경로.**

이 단계의 서명 범위는 `research_archive_manifest_attestation`, 즉 **보관한 정확한 파일 집합과 그 명세의 소유자 확인**이다. 출처 진위, 통계 통과, 전략 선발, 거래 활성화를 합쳐 승인하지 않는다. `RAW_ARCHIVED`도 미완료·조회 실패·손상 기록을 그대로 표시하여 확인할 수 있다. 그 서명이 raw 보관본을 검증된 연구로 바꾸지는 않는다.

범용 서명 codec만 만들고 완료하지 않는다. 실제 `BundleStore.read_raw/read_verified` → 독립 signer 검토·서명 → 실제 저장 graph와 신뢰 anchor를 통한 인증 CLI까지 테스트한다. **선발 연결은 B1b-2, 신뢰 서명을 기준으로 한 복구 실행은 B2**로 남긴다. B1a의 `StoredBundle`이나 임의 `authenticated=True`를 승인 증거로 받아들이지 않는다.

## 2. 현재 코드와 새로 필요한 것

| 근거 | 현재 구현 | B1b에서 필요한 차이 |
|---|---|---|
| `research_bundle_format.py` | raw/verified 별도 domain, 전체 파일·입력 archive·후보 연결, 엄격한 형식. kind와 parent는 문서상의 주장 | 독립된 서명 envelope와 범위. 기존 manifest bytes를 수정하거나 kind를 APPROVED로 바꾸지 않음 |
| `research_bundle_store.py`의 `BundleReceipt`, `inspect`, `read_raw`, `read_verified` | catalog/head, 전체 graph, backup bytes 확인. receipt는 역사 저장 사실 | 신뢰한 소유자 서명 인증은 없음. backup_verified는 서명·출처·복구 권한이 아님 |
| `research_bundle.py`의 `finalize_study_bundle`, `evaluate_sealed_study` | raw 선보관·backup, 실제 receipt/A0b 평가, sealed-only 재현. 인증·실행 준비는 false | 실제 묶음 인증 consumer. 재현된 결과와 서명된 자료의 동일성 확인 및 새 승인 범위 표시 |
| `review_request.py:120,138` | 현재 전체 후보의 plan/capture/result family commitment. 새 unsigned 요청 생성 | receipt/source/report를 포함한 전체 파일 집합은 서명하지 않음 |
| `review_auth.py:80,166` | legacy/carry 별도 purpose/domain, 실제 Ed25519, 현재 소유자·코드·만료·유효 context 검사 | archive attestation에 기존 전략 출처·실행기 purpose를 재사용하지 않음 |
| `study_review.py:122` | 실제 A0b 평가, 모든 eligible 후보의 기존 source review 검증, 현재 authority 재조회 후 선발 | 새 manifest 인증을 먼저 요구하는 sealed 전용 경로. 기존 family 서명만으로 새 manifest 승인 표시 금지 |
| `tools/signer/sign.py:1450`의 `review-approve` | 저장소 밖 복사본, 독립 parser/source hash, 현재 key/code 확인, 사용자 직접 확인, 입력·로그 재검사 후 detached 서명 | 전체 묶음 검토 명령과 독립 manifest/file validator. 앱 모듈을 import하여 자기 승인을 발급하지 않음 |
| `execution_control/owner_authority.py` | `CurrentOwnerAuthority`: 신뢰한 owner loader·현재 공개키, 30초 freshness, key/code/head pin, rollback·회전·변경 시 latch | 기존 신뢰 경계를 활용하되 archive 확인과 거래 허용 조건을 구분 |
| `core/compliance/owner.py:279,464`, signer의 key rotation | owner chain/anchor·서명·키 회전 검증. 현재 키와 다른 detached review는 현재 사용 거절 | **개별 연구 attestation 폐기 이벤트·목록은 아직 없음.** 이를 구현하지 않고 revoked=False로 채우지 않음 |

현재 `ReviewAuthority`는 review 전용 context이며 실제 계좌/세션 증거가 아니다. 현재 `review_auth._authenticate`는 전략 검토에 유효 규칙 상태와 중지 조건도 요구한다. 보관 원본의 신원 확인에 같은 함수를 무조건 호출해 거래 준비와 혼동하지 않는다. 새 비거래 범위는 owner/code/key/context 무결성을 검사하며, 기존 전략·위험·활성화 게이트는 그대로 남긴다.

## 3. 독립 signer가 읽을 정확한 대상

앱 쪽 exporter는 실제 B1a graph를 읽어 **명시한 새 빈 검토 디렉터리**에 제한된 패키지를 만든다. 공개 저장소로 내보내지 않는다. 패키지는 backup이나 신뢰 anchor가 아니며 그 자체로 인증되지 않는다.

- 정확한 raw manifest bytes, 그리고 대상이 verified라면 정확한 verified manifest bytes.
- 모든 logical file의 원본 bytes. 저장 파일 이름은 검증된 generated logical ID만 사용하고 `original_name`/`source_name`을 경로로 사용하지 않는다.
- 정렬된 logical ID·역할·후보·길이·SHA 목록, 대상 kind/digest, raw input archive digest, export schema 및 필요한 명시적 storage policy.
- raw의 expected 후보 unknown 여부, 관찰 inventory·미수집/누락/실패 상태를 숨기지 않는 검토 요약. 요약이 원본 manifest를 대신하지 않는다.

standalone signer는 앱에서 계산한 `PASS`나 `StoredBundle`을 입력으로 받지 않는다. 독립 복사본의 strict parser로 두 manifest의 domain/digest/전체 파일 집합·raw→verified 연결을 검사하고, 각 실제 payload 파일을 bounded read로 hash한다. 줄바꿈·공백을 고쳐 저장하지 않는다. 목록 밖 추가 파일, 링크·이름 충돌·파일 교체·길이/해시 불일치를 거절한다. 검토 디렉터리 파일들의 실제 byte 일치를 확인하는 것이며, 원본 object store의 정상 상태는 인증 consumer가 다시 검사한다.

독립 signer의 manifest 계약과 앱의 계약은 공통 정상/비정상 golden vectors로 비교한다. 같은 앱 함수를 import하여 동일 결과를 만드는 방식은 독립 검증이 아니다. `tools/signer/sign.py` 밖의 app-owned Python을 암호 입력 과정에서 실행하지 않는다.

사용자 확인 후 실제 서명 직전에도 exact manifest/payload 집합, 현재 key/code/source closure, owner head와 시각을 재검사한다. 변경되면 새 확인이 필요하며 이미 존재하는 output을 덮어쓰지 않는다. 기존 격리 실행·직접 확인·신뢰한 signer 사본·dependency 검토 경계는 유지한다. 개발 테스트는 가짜 키와 임시 자료만 사용한다.

## 4. 새 서명 형식과 최소 API

새 domain 예시: `tradegen-research-archive-attestation/1`. 기존 `tradegen-owner-log/1`, `tradegen-strategy-review/1`, carry review `/2`와 호환하지 않는다. 요청/서명에 서명 자체를 포함하는 순환 참조를 만들지 않는다.

서명 body의 최소 필드는 다음과 같다. exact 이름은 구현 직전 API 카드에서 고정한다.

| 묶음 | 필드 |
|---|---|
| 문서·범위 | schema_version, purpose=`research_archive_manifest_attestation`, request_sha256, approved_checks |
| 정확한 대상 | bundle_kind, bundle_digest, raw_manifest_sha256, verified_manifest_sha256 또는 null, input_archive_digest 또는 null, 전체 logical file 목록의 file_set_sha256 |
| 소유자·코드 | owner_fingerprint, reviewer_id, deployment_code_hash, 독립 검증이 확인한 source closure digest |
| 유효기간 | requested_at, issued_at, expires_at. 현재 사용의 만료 조건을 고정하고 자동 연장하지 않음 |

signature envelope는 exact body와 Ed25519 signature만 담는다. envelope에 공개키를 넣어 그 키 자체를 신뢰하는 기능은 없다. 전체 manifest의 domain digest와 정확한 bytes SHA를 함께 대조하고 파일 목록 hash를 실제 manifest에서 재계산한다. `audit_sha256` 한 필드에 manifest를 넣어 기존 purpose를 새 범위로 해석하지 않는다.

제안 파일 분할:

| 파일 | 최소 변경 |
|---|---|
| 새 `execution_launch/bundle_attestation.py` | strict unsigned request/body/envelope parser, domain signing bytes, 서명 수학 검증. 입력 public bytes만으로 trust를 발급하지 않음 |
| 새 `execution_launch/bundle_auth.py` | 실제 B1a store read, raw/verified 전체 대조, 신뢰한 현재 owner provider, exact 서명 대상·시각·현재 코드 검사. display receipt를 다시 입력 권한으로 받지 않음 |
| 새 `execution_launch/bundle_review.py` | 실제 bounded review packet export 및 authenticate CLI. 명시적 roots만 사용하고 activation·복구·key 생성 없음 |
| `tools/signer/sign.py` | standalone `bundle-attest` 명령, 독립 형식·파일 검사, 새 scope 표시와 detached 서명 |
| 새 관련 tests 및 `tests/compliance_signer.py` | 실제 fixture Ed25519와 B1a graph를 통한 수직 검사, signer/app parser의 일치·불일치 vectors |

B1a immutable manifest에 서명을 끼워 넣거나 `VERIFIED_UNAPPROVED`를 수정하지 않는다. attestation은 별도 새 파일/보관 artifact로 남기며 서명 자체의 hash로 식별한다. 실제 독립 백업에도 **서명 envelope와 그 서명이 가리키는 manifest bytes**를 버전으로 보존하는 연결이 필요하다. 서명 파일 하나를 만들었다고 backup까지 완료됐다고 보고하지 않는다.

최소 B1b-1 출력은 “소유자 신뢰 anchor에 연결된 exact archival signature 확인”과 그 검증 시각·대상이다. **현재 선발/활성화/자동복구 사용 가능**을 반환하지 않는다. 만료·현재 키/코드·개별 폐기 조회의 결과는 각각 구분한다. 미구현 폐기 조회는 `UNKNOWN/UNSUPPORTED`이며 false로 대신하지 않는다.

## 5. 서로 다른 승인 범위

| 범위 | 필요한 근거 | 범위를 넘어서지 않는 결과 |
|---|---|---|
| 원본 보관 확인 | 새 archive attestation, 전체 manifest/file bytes, 외부 소유자 신뢰 | 정확한 보관 내용의 소유자 확인. 실패 raw도 그대로 확인 가능 |
| 자료 출처·사전 등록 검토 | 기존 source review의 실제 원본·공개 시각·전체 후보/시도 검토와 audit bytes | 로컬 hash나 원본 보관 서명만으로 이 검토를 자동 충족하지 않음 |
| 전략 선발 | sealed bytes의 실제 재평가, 모든 후보 family, exact source/factory review, 새 manifest 인증, 현재 승인 조건 | 수치 탈락·실패 후보를 삭제하지 않음. 계산 통과만으로 승인하지 않음 |
| 거래 활성화 | 기존 현재 코드·규칙/한도·계좌/위험·세션·주문 게이트 | 연구 검토/보관 서명에서 자동 arm 또는 주문을 만들지 않음 |

**B1b-2의 최소 실제 연결**은 `authenticate_sealed_study_selection`이다. verified bundle과 raw 전체를 읽고 실제 `evaluate_sealed_study` 경로로 재평가한 다음, 기존 `authenticate_study_selection`의 실제 source/factory review와 같은 family commitment를 대조한다. 새 attestation도 별도로 요구한다. source review의 audit hash가 서명된 묶음의 해당 보고서 bytes와 같은지 확인한다. 보고서가 새로 생기거나 바뀌면 새 묶음과 필요한 새 승인을 받는다.

옛 review가 여전히 유효한 기존 바인딩을 갖는지 검증할 수는 있지만, 옛 body를 수정하거나 새 manifest 승인으로 승격할 수 없다. 기존 request schema 1/2 및 carry 3/4, body 1/2의 의미는 유지한다. old key/signature, mock verifier, 직접 만든 result/authority 객체의 deserialize로 새 승인 권한을 만들지 않는다.

## 6. 폐기·만료·현재 코드와 정확 복구

현재 코드에는 개별 attestation 폐기 기능이 없으므로 **B1b-1은 자동 재사용·재서명 불요 판정을 발급하지 않는다.** 현재 키 회전이 old detached signature의 현재 사용을 막는 사실과 개별 문서 폐기는 별개다.

B1b-2/B2 전에 가장 작은 폐기 연결안은 신뢰한 기존 owner log에 **연구 attestation만 제한하는** 새 signed revocation 사건을 추가하는 것이다. 대상 attestation digest와 범위를 exact schema로 고정하고, 취소·재활성화를 겸하는 이벤트로 만들지 않는다. signer와 owner parser가 동일 새 형식을 알아야 하며, 기존 문서와 code hash는 새 버전으로 검토한다. 별도 unsigned JSON blacklist나 앱이 제공한 `revoked=False`는 대체재가 아니다.

새 current authority 조회는 실제 검증한 owner log head·key와 폐기 목록이 같은 관찰에서 나왔는지 확인한다. freshness·head 성장·rollback latch를 유지하며 폐기 자료가 없거나 손상됐으면 사용을 거절한다. 시간 역행·미래로 적힌 제한 이벤트가 철회 효력을 미루지 않도록 기존 제한 정책과 일관된 보수적 처리 및 회귀가 필요하다. 이 사건은 기존 금액·손실 하한·한도 발효일을 바꾸지 않는다.

정확 복구의 판정은 다음 세 층으로 분리한다.

1. **역사적 서명·원본 일치:** 신뢰 근거가 있는 서명이 지정한 exact manifest/all files와 복구 후보 bytes가 일치한다. 유효기간이 지났어도 원본 bytes의 역사적 확인 자체와 현재 사용 권한을 혼동하지 않는다. 과거 키도 임의 입력 키가 아니라 실제 검증된 키 전환 이력에 연결돼야 한다. 그 역사 검증 경로가 없으면 미지원이다.
2. **현재 승인 재사용 조건:** 현재 신뢰 key/허용된 키 전환, attestation 및 별도 source review의 미폐기·유효기간, 현재 승인된 deployment/source code, exact plan/profile/rule/family/binding을 모두 확인한다. 한 조건이라도 미확인·만료·변경이면 원본을 보존해도 자동 선발·운영 사용을 재개하지 않는다.
3. **현재 운용 조건:** 실제 현재 risk/계좌/미체결/세션·한도·손실 하한·기존 halt 정책과 재시작 대조까지 통과해야 한다. review용 placeholder positions나 원본 복구 결과는 이 증거가 아니다.

1~3이 기존 승인 그대로 충족되는 정확 원본 복구에는 서명을 무조건 다시 요구하지 않는다. 새 계산·새 관측·변경된 report/manifest에는 기존 서명을 적용하지 않는다. 만료된 서명이 있는 자료를 역사 보관으로 복원하는 것은 가능한 별도 동작이며 자동 재승인을 뜻하지 않는다.

B1a read는 primary catalog/head와 graph를 확인하므로 primary가 손상되면 단순 `read_verified`로 backup을 채택할 수 없다. B2에는 **손상된 catalog 밖의 신뢰 서명과 manifest**를 기준으로 backup을 읽는 별도 복구 경로가 필요하다. 손상본을 보존·격리하고 새 임시 위치에 exact graph를 복원하여 전체 재검증한다. 자동 head 초기화/reanchor로 기존 guard를 우회하지 않는다. 복구 사건·새 물리 위치는 외부 사건 기록에 남기며 signed manifest 원본은 수정하지 않는다.

## 7. 필요한 검증

- 실제 임시 B1a raw/verified 묶음 → export → standalone fixture signer → 앱의 실제 owner/context 검사 → 실제 graph 인증. bare codec 통과나 수동 boolean만으로 끝내지 않는다.
- malformed/실패 raw의 exact 보관 서명은 가능하지만 verified 연구·source review·선발로 승격되지 않는지 검사한다.
- manifest/file 하나의 byte·길이·목록·candidate·raw link·보고서 변경, 파일 추가/누락/교체, 확인 후 수정, 부분 export, symlink/hardlink/reparse, record/type/JSON 경계를 거절한다.
- 앱 parser와 독립 signer의 정상·비정상 golden vectors, 실제 서명 domain 불일치, 기존 source/owner-log 서명 replay, embedded attacker key, 잘못된 현재 key/code/source closure를 거절한다.
- 신뢰 provider의 stale/future/rollback·owner head/key 교체·expired/future signature, 인증 도중 만료·자료 변경을 검사한다. B1b-1의 폐기 미지원 상태가 자동 사용 허가가 되지 않아야 한다.
- B1b-2에서 실제 signed revocation·owner chain/head·expiry/current code·source review 조합을 검사한다. revoked/만료된 원본의 역사적 보존과 현재 사용 거절을 각각 확인한다.
- B2에서 exact backup과 일부만 일치하는 backup을 구분하고, 모든 파일이 정확하고 현재 승인 조건도 유효한 경우에만 재서명 없이 재사용한다. 재구성·재관측은 새 버전·새 승인 경로로 간다.
- 임시 home과 KEYLESS/fake source만 사용한다. 실제 signer 사용자 입력·실제 키·소유자 로그·API·arm/order는 0이다. Windows 전용 실행·파일·의존성 검증은 별도 결과로 남기며 Linux 통과로 갈음하지 않는다.

## 8. 입력 없는 개발과 이후 배포·WebAuthn

현재 입력 없이 구현 가능한 부분은 새 bounded 형식, 실제 패키지 exporter, 독립 signer parser/해시 계산·fixture 서명, 실제 인증 CLI, 위 격리 검증이다. 실제 신뢰 공개키와 독립 signer 복사본의 배포·검토는 소유자 환경의 기존 절차를 따른다. 에이전트에게 키·암호를 보내도록 요구하지 않는다. 실제 archive/backup 위치·신뢰 anchor/회전 정책·폐기 저장의 운영 배치는 배포 시 명시해야 하며 임시 테스트 값으로 대신하지 않는다.

향후 Telegram/WebAuthn 전환은 새 authentication method/version으로 추가한다. 서명할 exact action/manifest/scope/expiry의 digest를 공통으로 고정하되 **passkey가 Ed25519 서명을 생성한다고 가정하지 않는다.** WebAuthn은 등록 credential 공개키, RP ID/origin, challenge, user verification, 만료·일회 사용·재사용/중복 적용을 실제 검증해야 한다. Face ID/기기 암호는 장치 내부 처리이며 동기화 passkey가 특정 iPhone 한 대를 증명하지 않는다.

최초 credential 등록·폐기·기기 분실 복구는 기존 독립 owner 신뢰에 의해 승인되는 별도 절차여야 한다. 앱이 새 passkey를 자체 등록하고 자신을 승인하게 해서는 안 된다. 서버·Telegram 봇에 기존 소유자 개인 서명키나 주문키를 맡기지 않는다. Telegram 버튼/알림 수신만으로 승인하지 않으며, 지원되지 않는 내부 브라우저는 신뢰 HTTPS 외부 브라우저로 연결한다. 이 변경으로 기존 코드·연구·규칙/한도·활성화 범위를 합치지 않는다.

권장 다음 완료 ID는 `PR5/B1b-archive-attestation`이다. 실제 source/selection 결합, 개별 폐기 조회, 정확 복구 executor, WebAuthn 승인·등록/폐기, 실제 배포는 각각 남은 상태로 기록한다.
