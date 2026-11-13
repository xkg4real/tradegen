# TRADEGEN archive-only 패스키 승인 — exact API 계약 v1

작성: 2026-11-13. **구현 전 계약**. 소스·requirements·설치·실서명·실계좌·Telegram 송신을 수행하지 않았다. 기존 recovered-selection 트리는 계속 동결 상태다. 이 문서의 타입·API·새 이벤트는 아직 존재하지 않는다. 근거 조사는 `TRADEGEN_PASSKEY_IMPLEMENTATION_READINESS_2026-11-13.md` 및 현재 독립 signer/owner/archive 검증 소스를 따른다.

## 1. 지원 범위와 완료 단위

지원 업무 scope는 정확히 `archive_manifest_identity` 하나다. 실제 B1a RAW/VERIFIED 보관본의 전체 manifest·파일 해시를 확인한 소유자의 WebAuthn 증거를 독립 broker가 확정하고, 명시 소비자가 현재 상태와 실제 원본/백업을 재검증한다. **출처 확인·전략 선발·정확 복구 승인·코드 승인·규칙/한도 변경·arm·주문 권한은 발생하지 않는다.** 기존 Ed25519 문서·owner 원장의 형식과 쓰기 주체는 유지한다.

첫 단위의 종료 조건은 초기 등록→고정 HTTPS 화면→실제 WebAuthn 검증→독립 ledger 적용→실제 archive 소비→결과/알림 adapter까지 합성 환경에서 연결하는 것이다. 순수 타입·login demo·같은 프로세스의 성공 객체만으로 완료하지 않는다. 실제 RP/Windows 독립 설치/실기기는 별도 운영 수용 검사다.

`REGISTER_CREDENTIAL`, `REVOKE_CREDENTIAL`, `PORTAL_SESSION`은 이 한 범위를 관리하는 별도 control action이다. archive grant를 확장하거나 owner 로그에 이벤트를 쓰는 권한이 아니다. `deployment.code`, `policy.rules`, `policy.limits`, `research.review`, `session.activate`는 모든 v1 승인 API에서 거절한다. 이 이름을 archive payload 안에 넣어 우회하지 못한다.

## 2. 라이브러리 결정과 근거

**제안 고정: 독립 broker/RP 패키지에 `fido2==2.2.1`, `cryptography==49.0.0`.** 앱의 현재 환경에 설치하지 않는다. 실제 lock은 Python 3.13/Windows와 Linux 검증 환경별 전이 의존성·wheel/RECORD까지 고정하고 승인 배포 폐쇄에 포함한다. PC/SC·USB/CTAP client extras는 사용하지 않는다. RP HTTP framework·브라우저 시험 도구도 실제 사용 버전과 정적 자산까지 별도 lock에 넣으며 기존 Flet의 간접 의존성을 운영 계약으로 간주하지 않는다.

2026-11-13 공식 자료 읽기 결과:

| 자료 | 확인 사실 |
|---|---|
| <https://pypi.org/pypi/fido2/2.2.1/json> | `Requires-Python >=3.10,<4`; `cryptography!=35,<52,>=2.6`; `py3-none-any` wheel. Python 3.13은 선언 범위에 포함된다. |
| <https://raw.githubusercontent.com/Yubico/python-fido2/2.2.1/pyproject.toml> | 위 조건과 실제 package version이 일치한다. 텍스트 SHA256 `b0728dde2a47fb34401e2a992d84277c072f05b84a3036bc16ad7b850fb51875`. |
| <https://raw.githubusercontent.com/Yubico/python-fido2/2.2.1/fido2/server.py> | `Fido2Server.register_complete`는 create/origin/challenge/RP hash/UP/UV, `authenticate_complete`는 get/origin/challenge/RP hash/UP/UV와 `authenticatorData + SHA256(clientDataJSON)`의 실제 COSE 서명을 검증한다. SHA256 `5333c4fbf041e90b4e2e19a949d6b101b44fa5805e0a87a4c8a1f1c459993cbc`. |
| <https://raw.githubusercontent.com/Yubico/python-fido2/2.2.1/fido2/webauthn.py> | 실제 `AuthenticatorData`에 BE/BS/UP/UV·counter 접근이 있다. origin의 기본 하위 도메인 허용 대신 exact 비교 함수를 주입해야 한다. server API 자체가 replay ledger·폐기·expiry·userHandle·crossOrigin 전체 정책을 제공하지는 않는다. |
| <https://pypi.org/pypi/webauthn/3.0.1/json>, 해당 maintainer `v3.0.1` authentication 소스 | 대안 `webauthn 3.0.1`은 Python>=3.10이며 pyasn1/pyasn1-modules/cbor2/pyOpenSSL을 추가로 요구한다. 기본 counter 비교가 양수 counter의 비증가를 거절한다. 더 작은 서버 의존성과 명시적 synced-counter 정책을 위해 이 단위는 fido2를 선택한다. |

fido2 wheel SHA256: `ed397da981b9ab133da6ead7309e41f924b566b749956129efe286fae097749f` (`fido2-2.2.1-py3-none-any.whl`). 메타데이터와 릴리스 소스를 읽었을 뿐 다운로드 설치·import·실행/취약점 완전 감사·native iPhone 호환을 확인한 것은 아니다. 공식 WebAuthn 규범 참고: <https://www.w3.org/TR/webauthn-3/>. 이 조사에서 해당 표준의 최신 본문은 다시 가져오지 않았다.

## 3. 독립 구성과 신뢰/전송 경계

### 3.1 설치 및 권한

- **broker**: 저장소 밖 검토된 별도 패키지/venv, 별도 Windows service SID. root 공개키·grant·credential registry·authority ledger·전용 transport private key에 앱 SID 쓰기 권한이 없다. 별도 폴더/actual Python class만으로 격리를 주장하지 않는다.
- **RP**: 고정 HTTPS origin의 독립 배포. grant는 RP 서버·표시 JS/HTML/CSS·로컬 번들·의존성 전체 release digest까지 승인한다. 외부 CDN의 변경 가능한 script를 실행하지 않는다. WebAuthn assertion은 challenge에 결합하며, 사용자에게 보여준 문구 자체를 직접 서명하지 않는다. 악성 RP가 다른 문구를 표시하지 않았다는 사실은 assertion만으로 입증되지 않으므로 **실제 표시 릴리스가 신뢰 경계**다.
- **앱**: 실제 bundle/packet을 제안하고 상태를 읽는 비권한 client. 명시적인 새 archive consumer만 새 형식을 받는다. 앱이 `approved=True`나 ledger/head/credential을 제공하는 API는 없다.
- **기존 owner root**: 독립 bootstrap에서만 실제 소유자 확인으로 grant/reset을 서명한다. owner private key를 RP/broker/bot로 이동하지 않는다. 실제 현재 owner key/code/head 검증은 기존 독립 signer와 동일 의미를 유지하며, broker가 앱에서 계산한 `code_hash`를 신뢰하지 않는다.

### 3.2 로컬/원격 채널

1. 앱↔broker: **로컬 Windows named pipe**, 고정 pipe 이름·서버 service SID와 허용 client SID를 설치 설정에 결합. remote client 금지·서버/pipe 교체 거절·호출 thread/handle 수명 검증. Linux 시험은 실제 별도 프로세스 Unix socket+peer UID 경계로 대체하고 Windows 수용을 주장하지 않는다. 앱 제안은 언제나 비신뢰 입력이다.
2. broker↔RP: broker가 시작하는 pinned HTTPS/mTLS 연결. peer SPKI/endpoint를 grant 설정에 고정. broker가 공개 인터넷 listen을 시작할 필요는 없다. RP는 등록된 broker만 request/state를 게시할 수 있게 하고, 반환 assertion은 broker가 원문 검증한다. RP의 성공 boolean은 무효다.
3. broker는 **새 transport 전용 Ed25519 키**로 현재 상태 응답을 봉인한다. 이는 owner 키와 다른 별도 키이며 grant가 그 공개키를 `archive 상태 조회 응답` 용도로만 pin한다. owner 로그/코드/규칙/연구 source review를 서명할 수 없다. broker mTLS 키도 별도 최소 권한 통신 자격이다. 두 키의 저장 위치는 service 전용이고 키 회전은 새 root grant가 필요하다. 자가 생성 키를 앱이 즉석 신뢰하지 않는다.
4. Telegram bot token은 notification worker에만 현지 설정하고 broker/RP/앱 승인 증거에 넣지 않는다. Telegram은 요청 ID·정해진 상태·동일 HTTPS origin 진입 링크만 전송한다. 링크/Telegram account/callback은 owner 인증이나 적용 권한이 아니다.

RP가 손상되면 표시 신뢰가 깨질 수 있고, 관리자 권한 탈취·전체 ledger+anchor의 일치 rollback까지 로컬 암호/ACL만으로 막는다고 주장하지 않는다. 원본 assertion·grant·의존성·현재 head를 보존하여 관찰 가능한 변경과 보류를 처리한다.

## 4. 공통 wire/한도

모든 아래 `{...}`는 **정확한 필드 집합**이며 추가/누락 필드 거절. `?`는 필드 생략이 아니라 명시적 null 허용이다. JSON은 UTF-8 ASCII escaping, key 정렬, 공백 없음, float/NaN 금지, duplicate key 거절; bool과 int 구분. wire 배열은 tuple로 detach한다. 입력으로 class/import/path를 결정하지 않는다.

| 타입 | 정확한 규칙 |
|---|---|
| `H` / `ID` | lowercase SHA256 64hex / CSPRNG 32바이트의 64hex. 의미상 digest와 random ID는 별개 필드다. |
| `B64` | unpadded canonical base64url; decode→encode 동일, 각 필드 decoded 상한 적용. |
| `T` | aware UTC `YYYY-MM-DDTHH:MM:SS.ffffff+00:00` 32자. 외부 now 인자는 서비스 프로세스에 받지 않는다. |
| `Head` | `{sequence:int>=0, sha256:H}`; genesis만 sequence0, 실제 owner checkpoint는 sequence>=1. |
| `OwnerCheckpoint` | `{fingerprint:"SHA256:"+H, code_sha256:H, owner_head:Head, observed_at:T}`. broker의 독립 actual 관찰로만 생성한다. |
| `Purpose` | `ARCHIVE_CONFIRM`, `REGISTER_CREDENTIAL`, `REVOKE_CREDENTIAL`, `PORTAL_SESSION`, `ENROLL_PROOF`. 마지막 둘은 owner 승인 효과 없음. |
| `Limits` | fixed v1: JSON depth16/nodes500000, grant/release 문서2MiB, archive request 기존12MiB, evidence256KiB, ledger event14MiB, 상태64MiB, credentials256(활성16), pending request128, 누적 request4096, 누적 events16384, outbox8192. 초과 시 고정 RESOURCE_LIMIT·원본 보존·새 적용 중단, 자동 pruning/reset 없음. |
| assertion/등록 body | clientDataJSON16KiB, authenticatorData16KiB, signature512B, credential ID1024B, COSE key1024B, userHandle64B, attestationObject64KiB, extension JSON4KiB. 값 검사 전 길이·개수 admission. |
| 시간 | request challenge TTL `1..300`초; enrollment/proof TTL `1..300`초; portal session 최대300초; archive approval `issued_at < expires_at <= 기존 archive_request.expires_at` 및 최대86400초. grant expiry는 독립 서명 시 명시, 최대366일. 운영 기본값을 추정해 적용하지 않는다. |

digest는 `SHA256(b"tradegen-passkey-archive/<record-type>/1\n" + canonical_bytes)`; grant 서명, reset 서명, broker response 서명은 각각 다른 record-type/domain. self digest 필드는 해당 입력에서 제외한 뒤 계산한다. 기존 Ed25519 archive/signature/revocation domain을 재사용하지 않는다. 모든 crypto 원본(clientDataJSON/authData/attestationObject/signature)은 받은 bytes 그대로 보존한다.

## 5. 설정·release·grant와 bootstrap

### 5.1 공개 서명 대상과 비공개 설정

`ReleaseManifestV1 = {schema:1, role:"BROKER"|"RP", python_version:str<=64, files:[{name:str<=512, byte_count:int>=0, sha256:H}], dependencies:[{distribution:str<=128, version:str<=64, record_sha256:H, artifact_sha256:H}], manifest_sha256:H}`.

files는 경로순 unique, 최대8192; dependencies는 distribution순 unique 최대256이며 byte_count는 exact int `0..2^63-1`이다. **이름은 package-relative POSIX metadata**이며 arbitrary export path가 아니다. Python source/native modules·실제 interpreter/stdlib 신원·의존성 RECORD·실제 표시 정적 자산·config schema/renderer를 포함한다. runtime다운로드/외부 import/plugin/CDN 변경을 금지한다. 실제 설치 파일과 closure를 독립 bootstrap이 재계산한다. TRADEGEN의 D14 code approval과 독립 broker/RP의 release approval은 다른 대상이다. 앱이 만든 release manifest를 그대로 승인하지 않는다.

`BrokerConfigV1 = {schema:1, authority_id:ID, service_identity:str<=256, client_identity:str<=256, pipe_name:str<=128, authority_root:str<=4096, backup_root:str<=4096, head_root:str<=4096, packet_inbox:str<=4096, app_repo:str<=4096, rp_origin:str<=255, rp_id:str<=253, rp_transport_spki_sha256:H, broker_transport_public_key:B64(32), broker_mtls_spki_sha256:H, config_sha256:H}`.

설정은 비공개다. origin은 정확한 `https://host[:explicit-port]`, path/query/userinfo/fragment 없음; RP ID는 lower-case DNS host, scheme/port/IP/localhost/wildcard 없음. v1은 **origin host==RP ID**만 지원한다(개발 `.test` host도 실제 HTTPS 사용). service/client가 같은 principal이면 운영 provisioning 거절. authority/backup/head/packet root는 명시·서로 겹치지 않고 symlink/junction/reparse/교체를 거절한다. 실제 native 검증 전 운영-ready를 표시하지 않는다.

`AuthorityGrantV1 = {schema:1, purpose:"passkey_archive_authority_grant", authority_id:ID, grant_epoch:int>=1, previous_grant_sha256:H?, owner_checkpoint:OwnerCheckpoint, recovery_fingerprint:"SHA256:"+H, config_sha256:H, broker_release_sha256:H, rp_release_sha256:H, approval_scope:"archive_manifest_identity", lifecycle_actions:["REGISTER_CREDENTIAL","REVOKE_CREDENTIAL"], initial_credential_sha256:H, issued_at:T, expires_at:T}`.

envelope는 `{body:AuthorityGrantV1, signature_b64:B64(64)}`. **현재 owner Ed25519 root**가 독립 `archive-authority-grant` 명령으로 서명한다. 별도 검토된 복사본을 사용하며 앱을 import하지 않는다. 이미 승인한 broker만으로 자기 update/newgrant를 승인할 수 없다. 새로운 grant 설치는 current root·이전 grant/head/epoch·release/실설정을 확인하고 필요한 최초 서명과 등록을 반복한다. root 키 회전은 기존 signed owner chain과 새 grant가 모두 맞아야 하며 옛 grant를 자동 이식하지 않는다.

최초 bootstrap: 설치된 독립 도구가 원문 등록 및 `ENROLL_PROOF` 결과를 **비권한 pending record**로 만든다 → 소유자가 독립 도구에서 실제 release/RP/credential/범위/expiry를 확인 → grant 서명 → broker가 grant+initial credential을 하나의 `AUTHORITY_INSTALLED` 이벤트로 확정. grant 전에는 archive request/apply 불가. registry나 root의 최초 생성은 명시 operator 동작이며 reader/runtime가 seed하지 않는다.

## 6. credential·요청·증거의 exact 형태

### 6.1 credential

`CredentialV1 = {schema:1, credential_id:B64(1..1024), credential_sha256:H, public_key_cose:B64(1..1024), algorithm:-7, user_handle:B64(32), rp_id:str, origin:str, registration_evidence_sha256:H, proof_evidence_sha256:H, created_at:T, backup_eligible:bool, last_backed_up:bool, last_counter:int[0,2^32-1], state:"ACTIVE"|"REVOKED", revoked_at:T?}`.

`credential_sha256=SHA256(raw credential ID)`; owner user_handle은 broker가 생성해 grant authority의 private registry에 고정한다. ES256/EC2/P-256(`-7`)만 지원한다. COSE exact keys `{1,3,-1,-2,-3}` 및 kty2/alg-7/crv1/32바이트 x,y; 공개키 검증은 라이브러리 수행. attestation preference `none`이며 진짜 iPhone/기기 독점·제조사 진위 확인을 주장하지 않는다. 정상 등록 원문을 검증한 뒤 새 credential로 별도 `ENROLL_PROOF` assertion을 검증하여 실제 키 보유를 확인한다.

추가 등록은 새 credential의 유효 registration+proof와 현재 ACTIVE credential의 `REGISTER_CREDENTIAL` 승인 두 가지를 같은 변경에 결합한다. 두 proof 중 하나만으로 활성화하지 않는다. 새 credential은 동일 archive scope만 갖고 grant/owner 권한을 확장하지 못한다.

`EnrollmentRequestV1 = {schema:1, enrollment_id:ID, authority_id:ID, grant_sha256:H?, registry_epoch:int>=0, rp_id:str, origin:str, user_handle:B64(32), nonce:B64(32), requested_at:T, expires_at:T, enrollment_sha256:H, challenge:B64(32)}`. 처음 bootstrap만 grant=null/epoch0이고 나머지는 실제 현재 grant/epoch다. enrollment_sha256은 마지막 두 필드를 제외한 domain digest, challenge는 별도 `.../enrollment-challenge/1\n`+nonce+enrollment digest의 SHA256이다. 서버가 발행하기 전에 독립 broker의 bounded pending proposal에 저장한다. `registration_evidence_sha256`는 이 원 요청과 RegistrationV1 원문의 결합 digest다. root가 grant를 만들 때 원 요청·실제 등록/proof를 함께 검증하므로 caller가 공개키만 제공해 초기 credential을 승인할 수 없다.

### 6.2 불변 요청

`RequestV1 = {schema:1, request_id:ID, authority_id:ID, grant_sha256:H?, registry_epoch:int>=0, kind:Purpose, target:Target, display_sha256:H, requested_at:T, challenge_expires_at:T, approval_expires_at:T?, nonce:B64(32), challenge:B64(32), request_sha256:H}`. 최초 bootstrap의 ENROLL_PROOF만 grant=null/epoch0을 허용하며, 이 경우 승인 효과는 없다. 다른 kind는 현재 실제 grant와 epoch>=1이 필수다. approval_expires_at은 ARCHIVE_CONFIRM만 T이고 나머지는 null이다.

`Target`는 kind별 정확한 tagged object:

- ARCHIVE_CONFIRM: `{scope:"archive_manifest_identity", archive_request:기존 정확한 ArchiveRequestV1, archive_request_sha256:H, packet_sha256:H, approved_checks:기존 archive APPROVED_CHECKS 전체 순서}`.
- REGISTER_CREDENTIAL: `{credential_sha256:H, registration_evidence_sha256:H, proof_evidence_sha256:H}`.
- REVOKE_CREDENTIAL: `{credential_sha256:H, reason:"OWNER_WITHDRAWN"|"DEVICE_LOST"|"CREDENTIAL_SUSPECTED"}`.
- PORTAL_SESSION: `{session_nonce:ID}`. 원격 request/packet 읽기 세션만, 승인 효과 없음.
- ENROLL_PROOF: `{credential_sha256:H, registration_evidence_sha256:H}`. pending 신규 키의 proof만, 승인 효과 없음.

`DisplayV1 = {schema:1, authority_id:ID, kind:Purpose, target:Target, requested_at:T, challenge_expires_at:T, approval_expires_at:T?}`. display_sha256은 이 문서의 domain digest이며 자유 문구를 받지 않는다. 고정 renderer가 이 필드만 표시하고 해당하지 않는 금융값이나 권한을 덧붙이지 않는다. `request_sha256`은 nonce/display_sha256을 포함하고 challenge/request_sha256 필드만 제외한 request core의 domain digest다. `challenge=SHA256(b"tradegen-passkey-archive/challenge/1\n"+nonce+bytes.fromhex(request_sha256))`. 동일 request ID 원문 변경은 거절한다. display→request→challenge 순서여서 self-hash 순환이 없다.

packet_sha256은 기존 private review packet의 정확한 request/raw-manifest/optional verified-manifest/generated payload 파일별 `{relative_name,byte_count,sha256}` 정렬 목록의 별도 domain digest다. original_name을 path로 사용하지 않고 기존 `p-<logical_id>.bin` 생성 규칙을 유지한다. 원본/후보/실패 inventory와 바이트 상한은 기존 B1a/packet 제한을 그대로 사용한다. broker가 자체 계산한 packet과 archive request가 target의 값과 정확히 같아야 한다.

broker가 실제 packet 전체를 검사하고 현재 owner/code를 독립 조회한 다음 REQUEST_OPENED를 확정해야 RP가 challenge를 발행한다. 서버는 이미 발행한 challenge/body를 변경하거나 만료를 연장할 수 없다. request 게시 당시 registry_epoch가 바뀌면 미소비 요청은 새 요청으로 다시 발행한다.

### 6.3 browser 원문과 적용 증거

`AssertionV1 = {schema:1, request_id:ID, credential_id:B64, client_data_json:B64, authenticator_data:B64, signature:B64, user_handle:B64?, client_extensions:{}}`.

`RegistrationV1 = {schema:1, enrollment_id:ID, credential_id:B64, client_data_json:B64, attestation_object:B64, client_extensions:{}, transports:["internal"|"hybrid"|"usb"|"nfc"|"ble"]}`. transports는 정렬 unique·최대5, **권한/기기 인증에 사용하지 않는 보조 정보**다. 브라우저가 제공하지 않으면 빈 배열이다. v1은 확장 요청을 보내지 않고 미지원 client/authenticator extensions를 거절한다.

`WebAuthnEvidenceV1 = {schema:1, request_sha256:H, assertion:AssertionV1, received_at:T, evidence_sha256:H}`. received_at은 broker 실제 수신 시각이고, RP timestamp는 현재 authority timestamp가 아니다. 같은 assertion의 JSON 포장 차이가 request를 다시 적용하지 못하도록 idempotency는 원문 byte 필드의 canonical evidence identity를 사용한다.

`AppliedArchiveV1 = {schema:1, purpose:"passkey_archive_manifest_confirmation", application_id:H, authority_id:ID, grant_sha256:H, registry_epoch:int>=1, request_sha256:H, evidence_sha256:H, credential_sha256:H, bundle_digest:H, input_archive_digest:H, file_set_sha256:H, archive_request_sha256:H, packet_sha256:H, owner_checkpoint:OwnerCheckpoint, applied_at:T, expires_at:T}`.

`application_id=domain_digest(authority_id,request_sha256,evidence_sha256)`이며 서명 알고리즘을 의미하지 않는다. 이 레코드와 raw assertion은 **WebAuthn 승인 증거**이고 legacy Ed25519 signature가 아니다. credential/root/approval 폐기 여부는 이후 매 current read에서 재검증한다. 응답 봉인용 transport signature가 owner 승인으로 바뀌지 않는다.

## 7. 검증·counter·시계 정책

- 서버와 broker 모두 실제 fido2 verifier를 사용한다. broker가 신뢰하는 expected challenge/RP/origin/credential은 자신의 ledger/grant에서 온다. browser가 반환한 라이브러리 state를 expected 값으로 사용하지 않는다. `user_verification=REQUIRED`, UP/UV 모두 확인한다.
- clientDataJSON을 길이/깊이/중복 키 검사 후 그대로 보존한다. exact required `{type,challenge,origin}` + optional `{crossOrigin}`만 허용, crossOrigin이 있으면 정확히 false. topOrigin 및 미지원 필드는 거절한다. registration type=`webauthn.create`, 나머지 assertion=`webauthn.get`. nonce/challenge는 exact decoded bytes 대조.
- 인증의 userHandle은 absent/null 또는 해당 owner의 정확한 32바이트만 허용한다. raw credential ID는 등록된 키와 byte-for-byte 동일해야 한다. 알고리즘·RP/origin은 grant와일치해야 한다. CBOR도 라이브러리 전에 bounded 구조 검사로 duplicate map key/깊이/길이/indefinite 등 미지원 구조를 거절한다. signature 검증을 자체 구현하지 않는다.
- BE는 등록 값과 일치, `BS => BE`; BE=true인 synced credential은 counter0/비증가를 보조 관측으로 보존하되 이것만으로 허용/거절하지 않는다. BE=false이며 이전/새 counter 중 양수가 있으면 새 counter가 증가해야 한다. 어느 경우도 일회성 request 소비·폐기 검사를 counter로 대체하지 않는다. Face ID인지 암호인지, 특정 iPhone 한 대인지 판정하지 않는다.
- 실제 서비스 clock만 사용한다. 각 operation 최초 실제 owner 관측부터 final completion까지 30초; 마지막 signature/packet/state/currentowner 검증 후에 clock을 읽고 원래 관측 나이·모든 완료 watermark·KST date·request/approval/grant expiry를 bounded 비교한다. 느린 처리 후 최초 timestamp를 새 now로 치환하지 않는다. rollback/unknown clock이면 적용하지 않는다.
- retry가 과거 APPLIED 기록을 반환할 수는 있으나 현재 유효함은 새 `read_current`의 별도 결과다. 만료·revoked 상태에서 예전 APPLIED response를 현재 승인으로 보여주지 않는다.

## 8. 원장·직렬화·결과

### 8.1 이벤트와 파생 상태

`EventV1 = {schema:1, sequence:int>=1, previous_sha256:H, observed_at:T, kind:EventKind, payload:EventPayload, row_sha256:H}`. row hash는 row_sha256 제외 domain digest. 다음 payload만 허용한다.

| EventKind | exact payload |
|---|---|
| AUTHORITY_INSTALLED | `{grant:GrantEnvelope, config_sha256:H, initial_credential:CredentialV1, enrollment_request:EnrollmentRequestV1, registration:RegistrationV1, proof_request:RequestV1, proof:WebAuthnEvidenceV1}` |
| REQUEST_OPENED | `{request:RequestV1, notification:NotificationV1?}` |
| ARCHIVE_APPLIED | `{application:AppliedArchiveV1, evidence:WebAuthnEvidenceV1, notification:NotificationV1}` |
| CREDENTIAL_ENROLLED | `{request_sha256:H, evidence:WebAuthnEvidenceV1, credential:CredentialV1, enrollment_request:EnrollmentRequestV1, registration:RegistrationV1, proof_request:RequestV1, proof:WebAuthnEvidenceV1, new_registry_epoch:int, notification:NotificationV1}` |
| CREDENTIAL_REVOKED | `{request_sha256:H, evidence:WebAuthnEvidenceV1, credential_sha256:H, reason:REVOKE_CREDENTIAL의 reason enum, new_registry_epoch:int, notification:NotificationV1}` |
| AUTHORITY_RESET | `{reset:ResetEnvelope, replacement_grant:GrantEnvelope, initial_credential:CredentialV1, enrollment_request:EnrollmentRequestV1, registration:RegistrationV1, proof_request:RequestV1, proof:WebAuthnEvidenceV1, notification:NotificationV1}` |
| REQUEST_CLOSED | `{request_sha256:H, state:"EXPIRED"|"REJECTED", reason:Code, evidence_sha256:H?, notification:NotificationV1}` |
| PORTAL_SESSION_CONFIRMED | `{request_sha256:H, evidence:WebAuthnEvidenceV1, session_sha256:H, expires_at:T}` |
| DELIVERY_REPORTED | `{intent_id:H, attempt_id:ID, outcome:"SENT"|"FAILED"|"UNKNOWN", reported_at:T}` |

ENROLL_PROOF는 pending proposal에 보존하고 grant/enrollment 이벤트에 원문을 포함한다. 독립 proof 성공만으로 권한 원장에 credential을 추가하지 않는다.

REQUEST_OPENED의 notification은 ARCHIVE_CONFIRM/REGISTER_CREDENTIAL/REVOKE_CREDENTIAL에만 REQUEST_READY/PENDING이고 PORTAL_SESSION/ENROLL_PROOF는 null이다. ARCHIVE_APPLIED는 해당 pending request와 evidence/target의 완전 일치, CREDENTIAL_*는 현재 epoch+1, initial/reset은 실제 grant/원문 proof/initial credential hash의 완전 일치를 요구한다. 즉시 성공 object를 반환하는 것과 원장에 원자적으로 확정된 효과를 구분한다.

`StateV1`의 exact read projection은 `{head:Head, grant_sha256:H, registry_epoch:int, last_trusted_at:T, credentials:[CredentialV1], requests:[{request:RequestV1,state:"PENDING"|"APPLIED"|"EXPIRED"|"REJECTED"|"INVALIDATED",evidence_sha256:H?,application_id:H?}], applications:[AppliedArchiveV1], notifications:[NotificationV1], deliveries:[DeliveryPayload]}`다. 실제 strict event replay로만 도출한다. 외부 State, `validated=True`, 임의 credential map은 authority 입력이 아니다. 실제 검증된 assertion의 counter/BE/BS만 각 credential의 파생 관측 상태에 반영한다. 초기 상태는 명시 provision된 genesis뿐이며, missing/truncated/head 불일치를 reader가 재생성하지 않는다.

### 8.2 저장·잠금 계약

broker의 전용 authority store는 명시 primary/backup/independent head에 append-only event를 확정한다. 연구 bundle은 기존 BundleStore/packet exporter를 사용하고 별도의 연구 저장·복구 engine을 만들지 않는다. authority 이벤트는 새 신뢰 domain이므로 incident/recovery의 DELIVERY나 저장 receipt를 승인으로 해석하지 않는다. 독립 broker는 앱 모듈을 import할 수 없으므로 기존 lock/fsync/CAS/read-back 패턴을 독립 구현하고 공통 음성 vector로 대조한다.

순서: source/packet의 bounded read-only 사전 검사 → **broker operation mutex** → actual authority head/registry replay → 원문 WebAuthn/current owner/packet 재검증 → **ledger writer lock → independent head lock** → 같은 row에 request 소비+효과+notification → backup/read-back/head 확정 → locks 해제 → 응답. writer/head lock 안에서 네트워크를 기다리지 않는다. owner 원장의 write lock은 취득하지 않으며 기존 독립 checkpoint 검증 의미를 읽기 전용으로 사용한다. BundleStore lock을 broker writer/head lock과 중첩하지 않는다.

준비된 row와 필요 bytes의 용량 검사는 예약이 아니다. 최종 쓰기에서 재검사한다. quota 부족·중단 때 원본/기존 row를 삭제하지 않는다. 동일 request/evidence가 완전히 확정되어 응답만 유실됐다면 actual replay로 같은 application을 찾아 반환한다. 부분 append/backup/head 차이는 `INDETERMINATE`로 멈추고 request를 미사용으로 되돌리거나 자동 재적용하지 않는다. 뒤의 오류 때문에 이미 확정된 성공 row를 롤백하지 않으며, 재시작은 실제 disk 사실을 읽는다.

apply/revoke/register/reset/current-read는 같은 operation mutex/ledger 순서를 따른다. revoke가 먼저 확정되면 옛 credential의 apply를 거절하고, apply가 먼저였어도 뒤의 revoke로 그 credential에 의존하는 **이후 current-read**는 REVOKED다. registry epoch 변경은 미사용 request를 INVALIDATED로 만들지만 다른 유효 credential로 이미 확정된 archive 확인까지 일괄 폐기하지 않는다. reset은 모든 옛 credential/grant에 의존하는 적용을 이후 사용 불가로 만든다. 전체 재개·옛 owner 로그 변경은 하지 않는다.

### 8.3 고정 결과

`OperationResultV1 = {schema:1, status:"PENDING"|"APPLIED"|"EXACT_RETRY"|"EXPIRED"|"REJECTED"|"INVALIDATED"|"INDETERMINATE", request_id:ID?, application_id:H?, head:Head?, reason:Code}`. 확정할 수 없는 head/application은 null이다. APPLIED/EXACT_RETRY도 과거 적용 사실이며 현재 유효성의 증명이 아니다.

Code allowlist: `PASSKEY_PENDING`, `PASSKEY_APPLIED`, `PASSKEY_EXACT_RETRY`, `PASSKEY_EXPIRED`, `PASSKEY_REVOKED`, `PASSKEY_GRANT_INVALID`, `PASSKEY_REGISTRY_CHANGED`, `PASSKEY_TARGET_CHANGED`, `PASSKEY_ORIGIN_RP_INVALID`, `PASSKEY_UV_REQUIRED`, `PASSKEY_SIGNATURE_INVALID`, `PASSKEY_REQUEST_REUSED`, `PASSKEY_CLOCK_INVALID`, `PASSKEY_OWNER_CHANGED`, `PASSKEY_RESOURCE_LIMIT`, `PASSKEY_STORE_INDETERMINATE`, `PASSKEY_FORMAT_INVALID`, `PASSKEY_CHANNEL_REFUSED`, `PASSKEY_SCOPE_UNSUPPORTED`, `PASSKEY_BOOTSTRAP_REQUIRED`. 예외 본문·입력·경로·개인값을 포함하지 않는다. 미인증의 잘못된 assertion 수신만으로 다른 pending request를 소비하지 않는다. 인증됐으나 대상/현재 조건이 바뀐 request는 고정 거절로 닫는다.

## 9. 현재 상태 증거와 실제 archive 소비

`CurrentReadRequestV1 = {schema:1, authority_id:ID, application_id:H, nonce:ID}`. nonce는 app client의 CSPRNG로 호출마다 새로 생성한다. caller가 제공한 owner/head/now/success는 받지 않는다.

`CurrentReadBodyV1 = {schema:1, purpose:"passkey_archive_current_observation", authority_id:ID, application_id:H, nonce:ID, grant_sha256:H, registry_epoch:int, authority_head:Head, owner_checkpoint:OwnerCheckpoint, request_sha256:H, evidence_sha256:H, packet_sha256:H, status:"ACTIVE"|"EXPIRED"|"REVOKED"|"INVALIDATED", observed_at:T, completed_at:T, response_expires_at:T, archive_expires_at:T}`.

envelope는 `{body:CurrentReadBodyV1, broker_transport_signature:B64(64)}`이고 response_expires_at<=completed_at+30초 및 <=grant expiry다. broker가 응답 직전에 실제 ledger/credential/grant/owner/code를 재검증하고, 유효하지 않으면 ACTIVE라고 하지 않는다. original request/assertion/application/grant/release manifests는 같은 인증된 채널의 bounded immutable artifact 조회로 얻는다. 모든 hash가 응답과 일치하지 않으면 거절한다. transport 서명은 새 WebAuthn 서명이나 거래 허가가 아니다.

새 public API:

```python
authenticate_passkey_archive(
    store: BundleStore, bundle_digest: str, application_id: str, *,
    broker: PinnedBrokerClient, authority_provider: CurrentOwnerAuthority,
    clock: Callable[[], datetime],
) -> PasskeyArchiveAssessment
```

`PinnedBrokerClient`는 actual IPC 연결·operator 설정 root/grant·nonce/응답 서명을 검증하는 client다. exact type은 잘못된 연결을 막을 뿐 OS 격리를 대신하지 않는다. callback으로 current status를 주입하는 production API는 두지 않는다. consumer는 actual current owner와 같은 clock을 사용하며 grant/root/원문 assertion → 실제 원본/backup 전체 graph → broker current-read 재관측 → actual owner/checkpoint → 최종 clock을 검사한다. 첫 actual 관측의 30초를 유지하고 마지막 무거운 검증 이전의 시각을 완료 시각으로 사용하지 않는다.

assessment exact fields: `{scope:"archive_manifest_identity", bundle_digest:H, input_archive_digest:H, application_id:H, request_sha256:H, evidence_sha256:H, authority_head:Head, revocation_status:"NOT_REVOKED_AT_HEAD", verified_at:T, archive_identity_authenticated:True, source_authenticated:False, research_selection_ready:False, current_use_eligible:False, execution_ready:False, automatic_operational_recovery_supported:False}`. ACTIVE 외에는 고정 거절이다. caller가 같은 구조를 만들어도 authority가 아니다. legacy `bundle_auth`/`bundle_recovery`/source review/selection은 이 타입을 받지 않고 명시적인 별도 archive 인증 CLI만 사용한다.

## 10. 등록·분실·reset·알림/화면

`ResetBodyV1 = {schema:1,purpose:"passkey_archive_authority_reset",authority_id:ID,previous_grant_sha256:H,expected_authority_head:Head,next_grant_sha256:H,reason:"ALL_CREDENTIALS_LOST"|"AUTHORITY_COMPROMISED"|"BROKER_REPLACED",issued_at:T,expires_at:T}`에 독립 recovery root의 별도 domain 서명을 붙인다. 최대300초의 명시 유효기간이며 실제 expected head를 독립 확인한다. 자동 downgrade/head 채택은 없다. 실제 옛 원장이 손상되어 head를 증명할 수 없는 reset은 v1 미지원으로 멈추고 별도 독립 재해복구 절차가 필요하다. Telegram/이메일/DB 수정으로 복구하지 않는다.

RP session은 PORTAL_SESSION assertion을 독립 검증한 단기 Secure/HttpOnly/SameSite cookie에 결합한다. 승인 페이지의 private manifest 표시 전에 owner/authority를 대응시킨다. 링크만으로 원문을 볼 수 없고 미인증 GET은 generic login 화면만 제공한다. 링크에 secret/token/원문/금융값을 넣지 않는다. 변경 요청은 Origin+CSRF+같은 session을 검사하며 ledger의 고정 bytes만 표시한다. cookie/session 성공으로 ARCHIVE_CONFIRM을 생략하지 않는다. 기존 session이 있으면 일반 승인은 한 번의 UV이고, session이 없으면 login UV와 승인 UV는 서로 다른 challenge다.

`NotificationV1 = {intent_id:H, authority_id:ID, request_id:ID?, application_id:H?, kind:"REQUEST_READY"|"APPLICATION_RESULT"|"CREDENTIAL_RESULT", status:OperationResult.status, created_at:T}`. intent ID는 요청/적용의 immutable ID와 kind로 도출하며, 알림이 포함된 event hash를 입력으로 삼아 순환시키지 않는다. 수신자·URL 문구는 operator 설정과 고정 renderer로 만든다. sender 성공은 소유자 확인/읽음을 뜻하지 않는다. 전달 재시도는 DELIVERY_REPORTED만 추가하고 효과/request를 바꾸지 않는다. 정확 원본의 기존 유효 승인을 재검증했으면 결과 알림만, 재계산/새 관측/변경판에는 새 request가 필요하다. archive 확인에서 자동 SELL/arm은 발생하지 않는다.

## 11. 제안 함수·소유 분할·검증 입구

독립 package `tools/approval_broker/`의 공개 함수는 `prepare_enrollment(config)`, `complete_registration(enrollment_id, registration)`, `complete_enroll_proof(request_id, assertion)`, `install_grant(grant_bytes, proposal_id)`, `open_request(kind, target)`, `submit_assertion(assertion_bytes)`, `read_current(read_request_bytes)`, `export_evidence(application_id)`, `install_reset(reset_bytes, replacement_grant_bytes, proposal_id)`, `pending_notifications()`다. 각 API는 위 exact 타입/고정 bytes를 반환하며 clock/store/provider는 operator 구성에서만 얻는다. production API에 임의 source verifier나 `trusted=True`를 두지 않는다.

호출 역할도 고정한다. `prepare_enrollment(config)`, `install_grant`, `install_reset`은 별도 operator/bootstrap 채널만 가능하며 RP/app HTTP/pipe에 노출하지 않는다. RP는 이미 등록된 enrollment/request의 원문 응답 제출·등록 제안만 할 수 있고 config/root/clock/owner를 덮어쓸 수 없다. 앱은 실제 private packet 제안·archive request 발행 요청·자기 authority의 상태/원문 조회만 한다. `open_request`는 받은 target을 권한으로 믿지 않고 broker가 실제 packet/등록 proposal에서 재도출한다. notification worker는 outbox 조회·DELIVERY_REPORTED만 가능하다. export/read는 접근 제어된 원문 조회이며 원장을 변경하지 않는다.

역할별 변경은 (a) independent contract/WebAuthn verifier, (b) standalone bootstrap/grant와 독립 ledger/IPC, (c) pinned RP/정적 UI와 notification adapter, (d) actual BundleStore를 사용하는 새 passkey archive consumer/CLI, (e) actual key·별도 프로세스·가상 authenticator 통합 검사다. 기존 연구 저장 engine과 owner-log v2 전체 이관은 변경 대상이 아니다.

필수 양성 검사는 실제 임시 Ed25519 grant + 실제 ES256 등록/proof/assertion + 실제 독립 ledger + 실제 B1a 전체 graph 소비다. fixed/carry/불완전 RAW를 포함한다. 음성 검사는 origin/RP/challenge/UV/owner/algorithm/duplicate JSON/CBOR/expiry/rollback/revocation/counter/대상 변경/시각 진행/동시 apply+revoke/응답 유실/모든 쓰기 경계 중단/다른 scope/transport nonce 재사용/가짜 broker·manifest를 포함한다. 실제 checker를 `True`로 바꾼 fixture를 인증의 양성 근거로 사용하지 않는다.

가상 authenticator/별도 프로세스 Linux/모의 Telegram HTTP의 성공을 iPhone Face ID·Windows ACL·실제 bot 배달의 성공으로 세지 않는다. 기존 legacy 서명·scope·owner/limit/risk/session/복구 회귀를 유지한다. 운영 RP·domain·actual root·service identity·backup 위치·token은 미정인 명시 입력이며 값을 가정해 운영을 활성화하지 않는다. 새 라이브러리의 실제 실행 호환성과 전체 dependency lock/독립 배포 검증은 구현 단계의 남은 작업이다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
