# 패스키 archive 승인 기반 검증기 — 2026-11-13 구현 경계

이 단위는 원래 archive 승인 vertical의 선행 모듈만 구현한다. 전체 archive 요청의 의미 검증, 독립 grant 발급/설치, ledger·일회성 소비, RP·IPC·Telegram·현재 사용 검증은 미지원이다. 기존 owner/앱은 이 결과를 승인 입력으로 받지 않는다.

소유 파일: 새 `tools/approval_broker/{__init__,contract,webauthn_verify}.py`, 같은 디렉터리의 독립 `requirements.txt`, `requirements-dev.txt`, `constraints.txt`; 새 `tests/launch_passkey_contract.py`, `tests/launch_passkey_webauthn.py`. 앱 모듈 import·공유 venv 설치·런타임 실행·registry/guard 수정은 하지 않는다. root가 소스 동결 후 별도 환경을 준비한다.

`contract.py`의 frozen/slotted/keyword-only 순수 타입:

- `RelyingParty(rp_id:str, origin:str)`: exact HTTPS origin, origin host==RP ID, ASCII DNS, IP/localhost/wildcard/경로/userinfo 거절.
- `EnrollmentRequest(authority_id:str, enrollment_id:str, grant_sha256:str|None, registry_epoch:int, rp:RelyingParty, user_handle:bytes, nonce:bytes, requested_at:datetime, expires_at:datetime)`: grant None은 epoch0인 bootstrap 후보만. ID/hash64hex, bytes32, exact aware datetime, TTL<=300초. `document()`, `digest`, `challenge`는 고정 domain에서 재도출한다.
- `ProofTarget(credential_sha256:str, registration_evidence_sha256:str)`.
- `ProofRequest(authority_id:str, request_id:str, grant_sha256:str|None, registry_epoch:int, target:ProofTarget, nonce:bytes, requested_at:datetime, expires_at:datetime)`: exact ENROLL_PROOF 요청/display/challenge. display→request core→challenge 순서로 순환 없음. archive full request를 받는 것처럼 표시하지 않는다.
- `Registration(enrollment_id:str, credential_id:bytes, client_data_json:bytes, attestation_object:bytes, transports:tuple[str,...]=())`와 `Assertion(request_id:str, credential_id:bytes, client_data_json:bytes, authenticator_data:bytes, signature:bytes, user_handle:bytes|None)`: 원문 bytes를 보존. JSON 입출력의 client_extensions는 정확히 빈 dict.
- `CredentialMaterial(credential_id:bytes, public_key_cose:bytes, rp:RelyingParty, user_handle:bytes, registration_evidence_sha256:str, backup_eligible:bool, backed_up:bool, counter:int)`: 등록에서 관찰한 키 재료다. 활성/등록 승인 상태나 proof 승인 필드를 만들지 않는다. ID-only hash와 **전체 material domain digest**는 별개다.
- `AssertionContext(purpose:str, request_id:str, request_sha256:str, rp:RelyingParty, challenge:bytes, user_handle:bytes, credential:CredentialMaterial, requested_at:datetime, expires_at:datetime)`: service가 보관한 기대값을 전달하는 불변 입력. 순수 constructor가 신뢰·소비 여부를 인증하지 않는다. purpose는 ENROLL_PROOF 또는 ARCHIVE_CONFIRM이며 후자는 assertion의 암호·기대값 대응만 검사하고 archive 의미·승인으로 승격하지 않는다.
- `proof_context(request:ProofRequest, credential:CredentialMaterial)->AssertionContext`: ID+실제 registration evidence binding 재검사.
- `parse_enrollment`, `parse_proof_request`, `parse_registration`, `parse_assertion` 및 각각의 `*_bytes` codec. 고정 `PasskeyError` 진단. exact keyset/type·중복키·길이/깊이/노드 admission 후 detach한다.

`webauthn_verify.py`:

```python
verify_registration(request: EnrollmentRequest, response: Registration, *, now: datetime) -> VerifiedRegistration
verify_assertion(context: AssertionContext, response: Assertion, *, now: datetime) -> VerifiedAssertion
```

반환은 실제 fido2 검증에서 얻은 불변 사실만 포함한다. `VerifiedRegistration`은 `credential:CredentialMaterial`, `request_sha256`, `registration_evidence_sha256`; `VerifiedAssertion`은 `credential_sha256`, `request_sha256`, `assertion_sha256`, `counter`, `backup_eligible`, `backed_up`, `counter_anomaly`다. 생성 가능한 데이터 구조이며 issuer token이 아니다. 두 타입의 `approval_applied`/`current_use_eligible`는 항상 false다. now도 상위 서비스가 실제 시계에서 얻어 전달하는 데이터이고 이 순수 함수 자체가 실제 시계·원장을 확인했다는 뜻이 아니다.

최대 원문: clientDataJSON16KiB/authenticatorData16KiB/credentialID1024B/COSE1024B/signature512B/userHandle64B/attestationObject64KiB, envelope256KiB. JSON depth12/nodes4096, CBOR depth8/items256; unknown/duplicate keys, indefinite/tag/float CBOR 및 미지원 확장은 거절한다. v1 등록은 ES256/EC2/P-256/attestation none만; assertion authData는 확장/AT 없는 정확한37bytes. `fido2==2.2.1`, `cryptography==49.0.0`; 원문 구조 admission 후 라이브러리의 실제 RP/origin/challenge/UP/UV/signature 검증을 사용한다. 별도 exact origin/crossOrigin/userHandle/BE·BS/counter/만료 검사를 한다.

Counter 0은 값 그대로 보존한다. old=0/new=0이면 anomaly=false이며, 둘 중 양수가 있고 비증가하면 anomaly=true다. BE=true synced key에서는 이 anomaly만으로 거절하지 않는다. BE=false에서 양수 counter가 있으면 증가 필수다. 이 정책은 향후 ledger의 일회성 challenge 소비·폐기를 대체하지 않는다. 등록의 `none`은 제조사·특정 iPhone 인증이나 키 보유 증명을 뜻하지 않으며, 실제 ENROLL_PROOF assertion이 나중에 키 보유를 검증한다. none 등록에서도 cryptography의 실제 P-256 공개키 구성 검증으로 곡선 밖·필드 범위 밖 좌표를 거절한다.

검사는 임시 ES256 키와 실제 fido2 검증을 사용한다. grant가 없는 이 단위에서 임시 Ed25519 서명을 만들어 권한으로 간주하지 않는다. 운영 서비스/ACL/RP/ledger/실기기/전체 archive vertical 완료는 여전히 미완료다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
