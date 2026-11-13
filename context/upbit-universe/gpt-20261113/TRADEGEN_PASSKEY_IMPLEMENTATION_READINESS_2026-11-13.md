# TRADEGEN 패스키 승인 구현 준비 — 다음 최소 수직 단위

작성: 2026-11-13. **읽기 전용 조사·다음 구현 제안이며 구현 완료·운영 승인·실기기 검증 결과가 아니다.** 조사한 저장소 HEAD는 `19f6775935f8d8828eed21fcaa76449507239a5b`이며, 같은 작업 트리의 recovered-selection 변경은 공동 동결·회귀 검사 중이다. 이 조사에서는 저장소 코드·테스트·HEAD, 실제 사용자 홈·키·계좌·네트워크를 변경하거나 사용하지 않았다.

## 1. 결론과 첫 완료 범위

다음 단위는 **독립 승인 서비스의 최초 등록부터 실제 연구 보관본의 전체 manifest 확인까지 연결하는 패스키 승인 흐름**을 권장한다. 첫 업무 범위는 기존 `archive_manifest_identity`에 대응하는 새 WebAuthn 승인이다. Telegram 진입 → 고정 HTTPS 화면 → 장치 UV → 독립 검증·확정 → 기존 실제 보관본과 대조 → 결과 표시·알림까지 하나의 흐름으로 검증한다. 로그인 성공만 표시하거나 순수 codec만 추가하고 사용자 승인 기능을 완료했다고 하지 않는다.

이 선택은 이미 구현된 `bundle-attest`의 반복 수동 확인을 대체할 첫 경로를 만든다. **연구 출처·전략 선발·코드·규칙/한도·세션 활성화까지 패스키로 전환하는 단계는 아니다.** 이들을 한 번에 바꾸면 기존 owner 원장·발효일·정지·코드 폐쇄·전략 검토 소비자를 함께 이관해야 한다. 첫 범위를 확정본 신원 확인으로 제한하면 기존 Ed25519 owner 원장과 거래 게이트를 그대로 유지하면서 실제 업무 한 가지를 끝낼 수 있다.

실제 승인 사이트/RP·독립 설치·최초 소유자 신뢰 설정이 없으므로 지금 실사용 등록을 완료할 수는 없다. 그 값들을 필수 명시 설정으로 받는 코드·브라우저 화면·독립 검증·임시 credential 통합 검사는 사용자 추가 입력 없이 개발할 수 있다. 미설정 운영 환경에서는 요청 발행·등록·적용을 거절한다.

## 2. 현재 구현과 근거

아래 경로는 조사한 저장소 기준이다. 과거 실행 기록의 “남은 일”은 당시 상태이므로 현재 기능 판단은 실제 코드에 따랐다.

| 현재 있는 기능 | 실제 근거 | 재사용·남은 경계 |
|---|---|---|
| 저장소 밖 독립 Ed25519 서명기 | `tools/signer/sign.py:1`, `:209`, `:2815`, `:3068` | 앱 import 없이 배포 코드/자료를 독립 검사하고 직접 확인한다. `code-approve`, `review-approve`, `bundle-attest`, `research-revoke`가 있다. 패스키 bootstrap/grant 명령은 없다. |
| 소유자 서명 원장·현재 키·효력/철회 | `core/compliance/owner.py:151`, `:293`, `:662`, `:997`; `execution_control/owner_authority.py:46`, `:75` | 실제 코드 폐쇄·현재 owner/head와 원 관측 시각을 검증한다. WebAuthn credential, 등록 origin, RP ID, challenge 소비 상태는 없다. 기존 Ed25519 `sig` 필드는 새 응답을 받지 못한다. |
| 전체 보관본 검토 요청·독립 서명·소비 | `execution_launch/bundle_attestation.py:22`, `:265`; `bundle_review.py:497`, `:515`; `bundle_auth.py:113`, `:139` | 실제 RAW/VERIFIED 원본·백업·전체 파일 목록을 읽고 요청을 재도출한다. 기존 `archive_manifest_identity`는 출처·선발·거래 권한이 아니다. 단순 저장 영수증도 인증이 아니다. |
| 전략/실행기 검토와 범위별 철회 | `execution_launch/review_auth.py:30`, `:82`, `:168`, `:234`, `:248`; `research_revocation.py:44` | 실제 fixed/carry 요청·factory·체크리스트·최대 유효기간·현재 서명/철회를 검증한다. WebAuthn envelope와 credential 폐기 의미는 별도 추가가 필요하다. |
| 실제 보관·정확 복구·사건 및 결과 outbox | `research_bundle_store.py`; `bundle_recovery.py`; `research_recovery.py:492`; `research_recovery_attempts.py:425`; `research_incidents.py:560` | 이미 있는 파일 보관/백업/복구를 다시 만들지 않는다. outbox는 의도와 보고된 전달 결과이며 Telegram 전송 구현이 아니다. 정확 복구와 새 승인 요청도 구분한다. |
| 사용자 앱 | `main.py:43`, `:99`; `pyproject.toml`의 Flet 설정 | 기존 Flet 앱이 있다. 이를 승인 프로그램과 같은 신뢰 권한으로 삼을 수 없다. 별도 HTTPS RP나 등록·승인 화면 구현을 찾지 못했다. |
| 의존성·검사 | `requirements.txt:16`, `pyproject.toml:18`, `constraints.txt:27`, `:102` | `cryptography`는 고정되어 있으나 WebAuthn/COSE/CBOR 검증 라이브러리는 없다. FastAPI/uvicorn의 constraints 항목은 승인 서비스 구현·직접 의존성 계약이 아니다. 실제 WebAuthn/Safari/Face ID/Telegram 테스트도 없다. |

`core`, `execution_launch`, `execution_control`, `tools`, `ui`의 Python 코드 및 테스트에서 관련 키워드를 검색했으며, WebAuthn 언급은 기존 archive codec의 “별도 체계” 설명뿐이었다. Telegram 테스트는 현재 명령이 임의 전송 옵션을 거절하는 음성 검사다.

기존 설계는 `/workspace/outputs/TRADEGEN_PASSKEY_DESIGN_NOTES_2026-11-13.md`와 `TRADEGEN_PR5_REVIEW_AMENDMENT_2026-11-13.md`에 있다. 여기서 이미 확정한 UV·범위 분리·독립 신뢰·원본 복구 시 조건부 재서명 생략을 다시 질문하지 않는다. 다만 그 문서의 전체 v1→v2 owner 전환은 여전히 설계이며 아래 첫 범위에서 완료했다고 하지 않는다.

## 3. 독립 신뢰 경계

1. **기존 독립 소유자 root → 신규 승인 검증기 grant.** 새 독립 bootstrap 명령은 현재 root, 실제 검증기/서비스 릴리스와 의존성 폐쇄, 고정 HTTPS origin/RP ID, 소유자 식별자, 최초 credential 공개키·registry epoch, 허용 범위, 복구 root를 고정한 새 domain의 grant를 만든다. 앱이 보내는 코드 해시만 믿거나 앱 안의 버튼으로 grant/root를 교체하지 않는다. 현재 signer에는 이 명령이 없으므로 구현·검토가 필요하다.
2. **Windows 독립 broker가 적용 순서를 소유한다.** 검증기, 공개 root, registry와 적용 ledger는 TRADEGEN과 다른 OS identity/ACL로 보호한다. 같은 사용자 권한의 다른 폴더만으로 악성 승인 대상 프로그램과 격리했다고 하지 않는다. 자체 버전 갱신과 grant 변경은 기존 bootstrap/recovery 경계로만 처리한다.
3. **HTTPS RP는 표시·인증 수집, Telegram은 알림·진입.** 서버가 성공이라 표시해도 로컬 broker는 원본 WebAuthn assertion·미리 등록한 요청·현재 credential/epoch를 직접 검증한다. 봇·RP에 소유자 개인 서명키나 거래소 키를 보관하지 않는다. broker와 RP 사이의 전송 자격은 승인 권한이 아니다.
4. **새 승인은 새 증거다.** WebAuthn assertion을 Ed25519 `signature_b64`/owner-log `sig`에 넣거나 서버가 소유자 키로 대리 서명하지 않는다. 기존 Ed25519 문서·원장 bytes는 유지하고, 새 envelope/domain과 명시적인 새 archive 소비자를 둔다. 첫 범위의 credential/승인 ledger만 새 체계이며 owner의 코드·한도·arm 이벤트 writer를 이중화하지 않는다.
5. **범위 혼용을 금지한다.** 첫 grant는 archive 신원 확인 및 해당 credential 관리에 필요한 정확한 범위만 허용한다. `deployment.code`, `policy.rules`, `policy.limits`, `research.review`, `session.activate`는 파서·UI 예약 이름이 있더라도 이 첫 소비자가 거절한다. 이후 코드 승인 지원은 실제 배포 폐쇄를 독립 broker가 계산·확인하는 별도 연결이고, 코드 승인 대상 앱이 그 판정을 발급하지 못해야 한다.

## 4. 제안 API와 파일 분할

아래는 다음 단위의 계약 초안이며 현재 존재하는 API가 아니다. 실제 구현 전에 별도 exact API 카드로 스키마·한도·오류코드·동시성 계약을 고정한다.

| 소유 경계 / 제안 파일 | 최소 API·역할 |
|---|---|
| `tools/approval_broker/` 독립 배포 패키지와 자체 고정 의존성 | `bootstrap_archive_authority(...)`, `register_credential(...)`, `create_archive_request(...)`, `apply_archive_assertion(...)`, `revoke_credential(...)`, `read_archive_application(...)`. TRADEGEN import 없이 grant/등록/원본 request/assertion/실제 packet을 독립 검증한다. 검토된 standalone signer의 packet·owner/D14 검증 로직은 독립 계약·golden vector를 재사용하되 앱 import로 바꾸지 않는다. |
| 같은 독립 패키지의 `contract.py`, `webauthn_verify.py`, `authority_ledger.py` | 별도 bounded `AuthorityGrantV1`, `CredentialRegistrationV1`, `ArchiveApprovalRequestV1`, `WebAuthnEvidenceV1`, `AppliedArchiveApprovalV1`. immutable target·원본 bytes·scope·expiry·epoch와 일회성 소비/적용/결과 outbox를 한 권한 원장에서 처리한다. 기존 일반 incident/delivery 원장을 승인 원장으로 재해석하지 않는다. |
| 독립 `approval_rp/` HTTPS 서비스·정적 페이지 | 등록 시작/완료, 고정 요청 조회, assertion 제출, 상태 조회. 서버가 고정한 요청으로만 화면을 렌더링한다. `navigator.credentials.create/get`과 외부 Safari 열기 안내를 제공한다. 적용은 broker의 실제 확정 결과를 기다린다. |
| 새 `execution_launch/passkey_archive_auth.py`와 명시 archive CLI 경로 | `authenticate_passkey_archive(store, bundle_digest, evidence_bytes, *, broker, authority_provider, clock)`. 호출자 boolean/임의 registry/가짜 완료 영수증을 받지 않는다. 실제 보호된 broker의 현재 head·grant/credential·원문 기록, 현재 owner/code와 실제 BundleStore 원본/백업 전체를 검증한다. 매 호출 새 관측이며 현재 사용 권한 토큰을 발급하지 않는다. 기존 Ed25519 `authenticate_bundle_attestation`과 별도 entrypoint로 둔다. |
| 독립 notification adapter | 확정된 request/result intent만 읽어 Telegram 링크·고정 상태를 전송한다. 전송 성공은 메시지를 읽었거나 승인했다는 뜻이 아니다. 동일 intent 재시도는 새 challenge/적용/주문을 만들지 않는다. 실제 token/수신자 미설정이면 송신하지 않는다. |

원본 bundle 보관·백업·packet 내 파일 inventory는 기존 `BundleStore`와 packet 계약을 재사용한다. 독립 broker의 권한 원장은 새로 필요하지만, 연구 파일 저장 엔진이나 복구 엔진을 다시 작성하지 않는다. 원장 저장 방식은 명시적 루트·단일 writer·독립 head·불완전 쓰기 거절·확정 후 read-back이라는 기존 검증된 패턴을 적용하며, 독립 패키지가 승인 대상 앱의 실행 코드를 import하는 편의 재사용은 허용하지 않는다. 전체 원장과 anchor가 함께 되돌아가는 공격까지 해결했다고 주장하지 않는다.

## 5. 첫 수직 흐름과 정확히 한 번 적용

1. 실제 보관본을 읽어 기존 `archive_request`와 전체 manifest/file-set commitment를 재도출한다. request는 현재 owner·broker grant·credential registry epoch, scope, deployment code, 대상 revision, 표시 본문 hash, 요청/승인 유효기간을 함께 고정한다. RAW의 누락·실패 기록은 UI에 보존하고 VERIFIED나 source-auth로 승격하지 않는다.
2. broker는 32바이트 이상 CSPRNG nonce와 request digest에 결합한 일회성 challenge를 영속 등록한 뒤에만 RP에 게시한다. 서버에서 만든 미등록 challenge나 수정된 동일 request ID는 거절한다. 화면/실제 적용은 같은 고정 request bytes를 사용한다. 공개 링크에 원본·자격증명·금융값을 넣지 않는다.
3. 사용자는 신뢰한 HTTPS origin에서 대상·scope·자료 해시·유효기간을 확인한다. 단순 GET/Telegram callback은 상태를 바꾸지 않고, 상태 변경은 인증된 세션·CSRF 검사 후 진행한다. RP는 `userVerification="required"`를 요청한다. Face ID/기기 암호는 장치에서만 처리하며 서버가 어느 방식을 썼는지 단정하지 않는다. Telegram 내부 브라우저 미지원 시 동일 origin을 Safari로 연다.
4. 검토해 버전을 고정한 WebAuthn 라이브러리로 서버와 broker가 각각 원본 응답을 검증한다. 정확한 `webauthn.get`, challenge, HTTPS origin, RP ID hash, credential/owner/알고리즘, UP/UV, top-level cross-origin 정책, signature·userHandle·BE/BS를 확인한다. canonical base64url/중복 JSON/크기·깊이·COSE/extension 한도를 검증하며 암호 구현을 자체 제작하지 않는다. 동기화 credential의 0/비단조 counter를 무조건 거절하거나 counter만으로 재사용을 허용하지 않는다.
5. broker의 같은 직렬화 경계에서 **current grant/credential·미사용 nonce·원 target·만료/시계·현재 owner/code 재검증 → 사용 처리 + archive 승인 효과 + 결과 intent**를 확정한다. 다른 증거로 동일 request를 다시 적용하거나 만료 후 재전송으로 기간을 연장하지 않는다. 같은 확정 결과의 응답 유실 재시도는 기존 결과만 돌려준다. 불완전 쓰기·head 불일치는 성공으로 추정하거나 자동 초기화하지 않는다.
6. 새 archive 소비자가 실제 보관본/백업과 원본 WebAuthn 증거 및 현재 broker 상태를 다시 읽고 결과를 표시한다. `archive_identity_authenticated`만 범위에 맞게 보고하고 `source_authenticated`, `research_selection_ready`, `current_use_eligible`, `execution_ready`는 false다. 원 증거·적용 기록의 버전 보관/백업 여부도 실제 확인한 사실만 표시한다. 이 증거를 기존 exact-recovery/selection API가 자동으로 받아들이도록 바꾸지 않는다.
7. 알림은 `요청 발행 / 인증 증거 접수 / PC 적용 대기 / 적용 확인 / 거절·만료 / 적용 확인 필요`를 구분한다. PC가 꺼지거나 알림·통신이 끊기면 완료로 처리하지 않는다. 결과 통지 재시도는 승인 자체를 반복하지 않는다.

## 6. 등록·철회·분실과 후속 범위

- 최초 등록은 실제 bootstrap root가 새 credential 공개키·RP/origin·scope·registry epoch를 승인한 뒤 확정한다. 등록 challenge 성공 또는 Telegram 계정만으로 owner가 되지 않는다.
- 추가 등록은 현재 등록 수단의 명시 enrollment 승인 또는 별도 offline recovery 증거를 요구한다. 분실 시 같은 ledger에서 credential 폐기를 확정하고 미사용 challenge/미적용 증거를 무효화한다. 동기화 패스키는 특정 iPhone 한 대에서만 사용됐다는 증거가 아니며 필요 시 credential 전체를 폐기한다.
- `apply/revoke/current-use-check`의 순서는 독립 broker가 확정한다. RP에서 폐기 접수만 됐으면 `PC 적용 대기`이고, 폐기 확인 뒤 이전 head를 복사한 응답/캐시 승인으로 새 사용을 허용하지 않는다. 이미 완료된 기록은 삭제하지 않는다. 모든 기기를 잃으면 미리 둔 독립 recovery 수단으로 새 epoch/등록을 만든다. Telegram/이메일/DB 직접 수정은 복구 권한이 아니다.
- 첫 범위는 owner의 코드·규칙·한도·세션 이벤트를 쓰지 않으므로 전체 v2 owner-log cutover를 수행하지 않는다. 이후 이 범위를 추가할 때는 유효한 이전 head·새 epoch·halt/더 높은 하한·다음 KST 발효·동시 legacy writer 차단과 실제 소비자를 함께 연결해야 한다. 기존 한도를 재설정하거나 무장하는 전환을 암묵 적용하지 않는다.
- 정확 원본 복구는 기존 유효 서명·철회·현재 조건을 재검증한 결과만 알린다. 새 버전/재계산/새 관측에는 새 request와 새 승인이 필요하다. 첫 패스키 archive 승인이 기존 source review나 복구·보류 해제 승인까지 대체하지 않는다. 연구 손상이나 승인 서비스 장애 자체로 자동 매도하지 않는다.

## 7. 완료 판정과 필수 검증

다음 전체를 통과해야 첫 업무 흐름의 개발 완료로 기록한다. 현재는 모두 **미구현/미실행**이다.

- 실제 임시 root의 서명 grant → 라이브러리로 만든 실제 임시 credential 등록/서명 → RP 화면/요청 → broker 적용 → 실제 B1a RAW 및 fixed/carry VERIFIED bundle의 전체 graph 재검증까지 잇는다. 가짜 `verified=True`, positive callback, 수동 조립한 성공 객체를 양성 근거로 사용하지 않는다. 실패/불완전 RAW도 그대로 확인할 수 있어야 한다.
- wrong origin/RP/challenge/credential/owner/UV/UP/알고리즘, 변조된 화면 대상·manifest·파일목록, 초과 필드/중복 JSON/큰 CBOR, 만료·미래시각·역행·epoch/head rollback·현재 코드 변경을 거절한다. code/rules/research/activate scope를 archive 요청으로 바꾸거나 반대로 재사용할 수 없다.
- 실제 독립 ledger의 쓰기·backup/head/read-back 경계마다 중단·재시작·동시 submit·응답 유실을 재현한다. apply-before-revoke/revoke-before-apply, 다른 assertion 재사용, 서명 후 target 변경, 장시간 검증 중 만료를 검사한다. 공개된 미확정 결과나 복구된 옛 head가 유효 승인이 되면 실패다.
- browser 테스트는 실제 WebAuthn 검증과 가상 authenticator를 사용해 등록/인증/표시-대상 일치를 검증한다. HTTPS 개발 origin과 임시 root만 사용한다. 이것을 iPhone Face ID 실기기 통과라고 보고하지 않는다.
- Telegram adapter는 가짜 HTTP endpoint로 실제 intent payload/링크·중복·timeout·수신 실패를 검사한다. 버튼 callback만으로 ledger 변화가 없고 token/raw evidence가 로그에 나오지 않아야 한다. 실제 메시지는 보내지 않는다.
- 기존 Ed25519 signer/owner/revocation, archive/auth/recovery, 전략 source/carry review, code/rules/limits/session 및 주문 게이트 회귀를 수행한다. 새 WebAuthn 문서는 기존 parser에서 계속 거절되어야 한다.
- 독립 패키지 앱 import 금지·scope별 쓰기·민감키 접근 금지 정적 검사와 Windows 실제 OS identity/ACL·서비스 재시작 검사를 구분한다. Linux synthetic Windows 검사를 native 합격으로 세지 않는다.

## 8. 개발 가능 부분과 운영에 필요한 미정값

| 지금 추가 사용자 입력 없이 구현할 부분 | 운영 시 실제로 필요한 값·행동 |
|---|---|
| exact 스키마, 서명 grant·독립 parser, UI/RP/broker/consumer, 트랜잭션·폐기·재시작·mock Telegram 통합 | 고정 승인 도메인/RP ID와 HTTPS 서비스 운영 장소·접근 경로. 임시 tunnel 주소를 운영 RP로 자동 채택하지 않는다. |
| Python 3.13 호환 WebAuthn 라이브러리 하나 선택·버전/전이 의존성 고정·표준 vector 검토. 필요한 HTTP/browser 의존성을 독립 패키지에 명시 | 검토한 독립 broker/서비스 설치와 별도 OS identity/ACL, 명시 authority 저장/백업/head 위치, 실제 최초 root/grant 확인. 실제 root 존재 여부는 아직 관찰하지 않았다. |
| 실제 값 없는 개발 설정·정상/만료 경계 테스트. challenge TTL은 기존 제안 5분을 시험값으로 쓰고 승인 효력은 별도 필드로 검사 | 실제 recovery 수단의 준비·보관, 서비스 주소와 초기 credential 등록. 기존 root를 offline bootstrap/recovery용으로 유지하는 제안은 실제 설치 시 확정해야 한다. |
| 요청/결과 outbox·notification adapter와 미설정 거절 | Telegram 봇/수신자 binding과 비밀의 현지 설정. 토큰·키·장치 암호는 채팅/공개 GitHub에 제출받지 않는다. |
| 모든 scope 격리 음성 검사와 archive 범위 만료 상한(기존 최대 24시간) 보존 | 실제 정책 설정의 challenge/승인 유효기간. 미정 범위는 발행하지 않으며, 순수 개발을 기다리게 할 이유는 없다. |

이는 지금 다시 묻는 승인 질문 목록이 아니다. 기존 사용자 요구·개발 승인은 유효하며 코드/검증은 진행할 수 있다. **실제 RP 등록과 독립 신뢰 설치 없이 임의 도메인·root·credential을 운영에 채택할 수 없다는 배포 경계**다. 기존 손실 하한·허용 손실·전략 목표·알림과 승인 분리 등 이미 확정한 사항은 재질문하지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
