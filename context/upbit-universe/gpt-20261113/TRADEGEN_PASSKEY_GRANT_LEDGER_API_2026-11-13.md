# 패스키 archive engine: grant·일회성 원장 — 다음 구현 카드

작성: 2026-11-13. **읽기 설계이며 아직 구현하지 않았다.** 기준은 PR59 main `5bb4d7d8bdf65fbd6a3048530947b72b563406a7`, 실제 foundation 계약과 `TRADEGEN_PASSKEY_ARCHIVE_API_2026-11-13.md`/부록 A다. 이 문서는 원 계약을 수정하지 않는 **추가 구현 단계 B, 2차 검토안**이다. 1차 제안의 별도 OFFLINE_ENGINE grant/domain은 채택하지 않는다. 승인 wire를 분리하지 않고 원 AuthorityGrantV1을 구현하며, engine-only는 구현·검증 범위를 뜻한다.

## 1. 이번에 끝낼 실제 경로와 범위

실제 보존한 초기 enrollment → 실제 fido2 등록 → 새로운 ENROLL_PROOF의 실제 서명 → 독립 owner의 Ed25519 grant → 실제 primary/backup/head 설치 → 실제 archive packet에서 요청 생성 → 실제 assertion으로 request 한 번 소비 → 현재 credential 폐기 뒤 current read 거절을 **한 engine 경로로 구현·검증**한다. 타입/서명 함수만 추가하고 완료로 세지 않는다.

업무 범위는 `archive_manifest_identity` 하나다. HTTPS RP·브라우저 UI·IPC·Windows service ACL·Telegram·앱의 권한 소비자는 이번 단위에 붙이지 않는다. 결과는 **archive engine 내부 검증/원장 사실**이며 `operational_channel_ready=False`, `current_use_eligible=False`, `execution_ready=False`다. 기존 Ed25519 archive 인증·source review·선발·복구·활성화 consumer는 새 결과를 받지 않는다. `PinnedBrokerClient`를 in-process status callback이나 caller가 만든 assessment로 대체하지 않는다.

실제 BundleStore 검사는 통합 fixture와 기존 private packet export/readback 경로에서 수행한다. engine는 독립 packet parser로 같은 전체 manifest/파일 bytes를 검증한다. 시험에서 두 실제 경로의 digest/원본/backup을 대조하되, 이를 아직 존재하지 않는 production 앱↔broker authenticated channel로 표시하지 않는다.

## 2. 현재 코드에서 재사용할 것과 실제 공백

| 실제 파일/API | 재사용 또는 필요한 변화 |
|---|---|
| `tools/approval_broker/contract.py` | 기존 EnrollmentRequest/ProofRequest/Registration/Assertion/CredentialMaterial 그대로 사용. 불변 typed context는 issuer가 아니므로 engine가 저장한 요청/credential에서만 구성. 기존 wire/domain 불변. |
| `tools/approval_broker/webauthn_verify.py` | 실제 등록·proof·assertion crypto, exact origin/RP/UV/counter 정책 재사용. none은 후보 재료이며 proof와 구분. |
| `tools/signer/sign.py:_bundle_verified_head`, `_bundle_code_approval_at`, `_head` | 독립 owner 서명/rotation/현재 code approval 의미를 재사용할 근거. **기존 helper는 외부 anchor 전체를 대신하지 않는다.** 새 owner reader는 operator-pinned 시작 checkpoint와 authority 원장에 남긴 후속 checkpoint를 실제 prefix로 확인. |
| `tools/signer/sign.py:code_files/code_hash` | 현재 실행 환경의 `importlib.metadata` RECORD를 사용한다. 독립 broker venv에서 그대로 호출하면 앱 D14와 달라진다. 새 명시 target-environment reader가 앱 `.venv`의 실제 cryptography/PyYAML RECORD를 읽고 기존 source closure와 결합해야 한다. 기존 함수를 조용히 변경하지 않는다. |
| `tools/signer/sign.py:_bundle_packet`, `_ba_parse_archive_request` | 실제 `request.json`+`payloads/p-<id>.bin` exact inventory/원본 hash/링크·교체 거절의 독립 구현. grant/engine에 앱 `execution_launch` import를 추가하지 않고 검토된 standalone dependency로 재사용. |
| `execution_launch/bundle_review.py`, `research_bundle_store.py`, `bundle_attestation.py` | 앱 측 실제 backed RAW/VERIFIED graph와 packet exporter는 그대로. 새 연구 파일 저장 engine을 만들지 않는다. |
| `research_incident_store.py`, `baseline_head.py` | append/backup/head·잠금·중단·재읽기 검증 패턴을 독립 authority store 설계의 근거로 사용. 이 앱 모듈을 root signer/broker에 import하지 않는다. incident DELIVERY나 기존 receipt를 승인으로 해석하지 않는다. |

## 3. 원 AuthorityGrantV1 유지: commitment 검증과 운영 설치를 구분

원 카드의 `AuthorityGrantV1`, envelope, `BrokerConfigV1`, `CredentialV1`, `RequestV1`·display/challenge, `AppliedArchiveV1`과 archive scope를 그대로 사용한다. **별도 EngineGrant/엔진 전용 승인 purpose 또는 OFFLINE_ENGINE 필드를 서명 본문에 추가하지 않는다.** 원 카드의 record-type 규칙을 구체화한 grant signing domain은 `tradegen-passkey-archive/authority-grant/1\n`이며, digest domain과 signature domain을 코드에서 명시 구분한다. 기존 owner-event/archive-attestation domain을 재사용하지 않는다.

`AuthorityGrantV1 = {schema:1,purpose:"passkey_archive_authority_grant",authority_id:ID,grant_epoch:int>=1,previous_grant_sha256:H|null,owner_checkpoint:OwnerCheckpoint,recovery_fingerprint:"SHA256:"+H,config_sha256:H,broker_release_sha256:H,rp_release_sha256:H,approval_scope:"archive_manifest_identity",lifecycle_actions:["REGISTER_CREDENTIAL","REVOKE_CREDENTIAL"],initial_credential_sha256:H,issued_at:T,expires_at:T}`. Envelope는 원 `{body,signature_b64}`다. 이번 최초 설치는 epoch=1/previous=null만 지원하며 이미 설치한 grant를 덮어쓰는 갱신 API는 없다. 추가 credential/reset은 handler가 아직 없으므로 capability 목록에 있어도 호출하면 UNSUPPORTED다.

`initial_credential_sha256`는 부록 A대로 **전체 초기 CredentialV1** domain digest다. ID-only hash가 아니며 실제 등록/proof commitments, 공개키·algorithm·RP/origin·owner handle·초기 proof counter/BE/BS와 state=ACTIVE/revoked_at=null을 결합한다. 초기 `created_at`은 실제 registration 수신/검증 시각으로 고정한다. `proof_evidence_sha256`는 원 WebAuthnEvidenceV1의 원문 assertion+실제 proof received_at을 포함한 domain digest이며, foundation의 시간 미포함 assertion digest와 구분한다. 따라서 root가 서명한 전체 초기 credential이 두 historical 검증 시각도 결합하고, installer는 각각 그 시각과 원 challenge 유효기간으로 실제 crypto를 재검증한다. 초기 원문은 나중의 counter 관측으로 덮어쓰지 않는다.

**테스트에서 서명하는 것은 진짜 임시 root가 실제 임시 설치 inventory/설정 bytes에 한 서명이다.** broker release는 실제 새 engine 소스/의존성 inventory이고, RP release는 실제 생성한 임시 정적 fixture 파일 목록이다. 각 manifest 파일·길이·hash를 직접 재계산하며, 0 hash·설명만 있는 성공 boolean·없는 파일을 넣지 않는다. 임시 RP 파일의 commitment 검증은 HTTPS 서버·화면 표시·기기·서비스 identity가 기능하거나 안전하게 설치됐다는 검증이 아니다. 실제 임시 transport/mTLS 공개키 commitment도 실제 연결 성공으로 해석하지 않는다.

원 `BrokerConfigV1` 구조를 유지한다. 현재 도메인/서비스 SID/IPC 설정은 테스트 fixture에만 명시하고 실제 사용자의 값으로 채택하지 않는다. owner log/public key/외부 anchors, target app environment, 독립 release 경로는 별도 **operator 설치 경로 입력**으로 받으며 protected installation의 genesis/context에 고정한다. 이를 앱 제안이나 서명 문서에서 임의 선택하게 하지 않는다. 원 config의 root/identity 제한과 이 추가 경로의 pin을 동시에 검사한다. reader/runtime는 경로나 head를 만들지 않는다.

이번에는 **운영 provisioning 명령과 PinnedBrokerClient/app consumer를 공개하지 않는다**. root·identity·release·channel을 실제 확인하는 installer가 없는데 `--ready`, 환경변수 또는 caller bool로 이를 우회하는 분기를 만들지 않는다. engine의 명시 bootstrap preparation은 저장소/crypto 작업 도구이며 실제 서비스 설치 수용을 발급하지 않는다. CLI·결과는 항상 현재 운영 채널 미구현을 표시한다.

이렇게 하면 후속 실제 RP/IPC를 연결할 때 grant 형식 migration만을 위한 재서명이 필요하지 않다. 다만 실제 배포 파일·release·설정이 테스트와 다르면 기존 원칙대로 **그 실제 대상에 대한 새 owner grant가 필요**하다. 테스트 grant를 운영 grant로 복사하거나 현재 개발의 root 서명을 사용자 서명으로 취급하지 않는다.

## 4. 독립 release와 owner/root 확인

독립 signer는 앱 source를 실행/import하지 않는다. 새 command는 검토해 따로 설치한 signer/package에서만 동작한다. 기존 `sign.py`의 암호·키 unlock·typed confirmation·isolated execution 방어를 유지하고, 새 패키지·실제 의존성 전체가 독립 release review에 포함된 상태에서만 새 명령을 추가한다. `sys.path`에 입력받은 repo/packet 경로를 넣지 않는다. signer 실행 시 owner 개인키가 broker/원장에 저장되거나 전달되지 않는다.

`read_current_owner(config, *, required_checkpoint) -> OwnerObservation`는 실제 고정 PEM·전체 signed owner log·명시 기존 anchor inventory와 retained checkpoint를 읽고, 현재 key rotation·code approval 및 target app environment의 D14를 재계산한다. 반환을 외부에서 주입할 수 있는 production callback은 두지 않는다. grant의 historical key/code/head는 현재 관찰과 같거나 실제 검증된 log prefix여야 하며, **grant 발급 key/code가 달라지면 기존 grant는 계속 유효하다고 보지 않는다**. root 회전·code 변경 시 새 독립 grant 경로를 따른다. recovery key는 별도 명시 공개키/fingerprint이며 현재 앱이나 broker가 생성해서 신뢰하지 않는다. 동일한 owner/recovery 공개키를 소유자가 명시 설정하는 것은 가능하나 자동 선택하지 않는다.

중요 의존성 계약: `target_deployment_code_hash(repo, environment)`는 현재 앱 D14 source 목록과 **대상 environment의 실제 RECORD bytes**를 사용한다. ambient broker fido2/cryptography RECORD로 대체하지 않는다. 파일·디렉터리 identity, symlink/reparse/교체/중복 dist 및 누락 RECORD를 거절한다. 현재 app 환경에서 기존 owner/signer D14와 정확히 같다는 golden parity, 별도 broker 환경에서도 같은 대상 hash가 나오는 검사를 필수로 한다. source closure 리팩터링을 하더라도 기존 code-approve bytes를 바꾸지 않는다.

`ReleaseManifestV1`의 실제 설치 package/source, interpreter/stdlib와 native module, 직접·전이 dependency RECORD 및 실제 파일 inventory를 독립 재검사한다. RECORD hash만 같고 설치 파일이 바뀐 경우를 허용하지 않는다. app D14와 broker/signer release hash는 서로 다른 대상이다. RP release의 실제 bytes/hash commitment와 RP 기능·설치 수용을 구분한다. 이번 core는 전자를 실제 검증하지만 후자는 발급하지 않는다. 전체 host 관리자 침해·모든 anchor의 일치 rollback 방어를 새로 보장하지 않는다.

## 5. 정확한 최소 engine API

아래 신규 API는 미구현 제안이며 public operation은 내부 actual clock/CSPRNG/독립 owner reader를 사용한다. caller `now`, credential map, approved bool, 결과 token 또는 arbitrary verifier를 받지 않는다. 테스트만 actual 독립 인스턴스의 명시 test clock을 fixture construction에 주입하며 CLI에는 노출하지 않는다.

```python
Engine.open(config_path: Path) -> Engine                 # 명시 prepared store만
Engine.prepare_initial_enrollment() -> EnrollmentRequest
Engine.submit_registration(enrollment_id: str, document: bytes) -> ProofRequest
Engine.submit_initial_proof(request_id: str, document: bytes) -> BootstrapProposal
Engine.export_grant_proposal(proposal_id: str, output: Path) -> ProposalReceipt
Engine.install_grant(document: bytes, proposal_id: str) -> OperationResult
Engine.open_archive_request(packet_directory: Path, *, approval_expires_at: datetime) -> RequestRecord
Engine.open_revoke_request(credential_sha256: str, *, reason: str) -> RequestRecord
Engine.submit_assertion(document: bytes) -> OperationResult
Engine.read_current(application_id: str) -> EngineCurrentObservation
Engine.inspect() -> HistoricalEngineSummary
Engine.pending_notifications() -> tuple[NotificationIntent, ...]
```

expiry는 명시 목표값이지만 현재 시각·허용 범위는 engine가 검증한다. 반환 request에는 exact fixed display/request/challenge가 들어가고 RP가 존재한다고 말하지 않는다. packet_directory는 actual pinned private packet만 읽으며 target/digest는 engine가 재도출한다. ordinary `submit_assertion`은 저장된 request의 kind/epoch/credential만 선택하고 임의 expected context를 받지 않는다.

독립 bootstrap/engine 명령은 `prepare-authority-store`, `archive-authority-grant`, `install-grant`, `archive-authority-disable`로 분리한다. 이는 운영 service provisioning CLI가 아니다. 최초 provision은 actual pinned roots/config·empty genesis/head를 함께 명시 준비할 뿐 grant를 승인하지 않는다. 정상 reader의 missing head는 `BOOTSTRAP_REQUIRED`; 잘린 journal은 `STORE_INDETERMINATE`다. 원 signer의 기존 명령·기존 owner log는 그대로다.

`archive-authority-grant`는 원문 enrollment+registration+proof 전체를 실제 검증하고 전체 initial credential digest를 재도출한 뒤, 현재 owner/key/code/release/config·명시 expiry를 확인하고 actual owner key로 원 AuthorityGrantV1만 서명한다. proof 검증 때 실제 수신 시각을 보존한다. 원문 challenge 유효기간 안에 완료한 proof와 해당 전체 record를 root가 서명한 뒤에는, installer가 원문 crypto를 **서명된 historical proof 관측 시각**으로 재검증할 수 있다. 이를 현재 assertion의 만료 우회로 사용하지 않는다. installer는 현재 grant/root/code/release/expiry를 새로 검사한다.

recovery root의 `AuthorityDisableV1 = {schema:1,purpose:"passkey_archive_authority_disable",authority_id:ID,grant_sha256:H,expected_head:Head,reason:"DEVICE_LOST"|"AUTHORITY_COMPROMISED",issued_at:T,expires_at:T}` 별도 `tradegen-passkey-archive/authority-disable/1\n` signature는 현재 검증된 exact head에만 적용한다(TTL<=300초). 이는 최소 emergency restriction이며 과거 원문을 지우지 않는다. **reset/교체 grant와 추가 credential 등록은 다음 단계**다. 모든 키 분실 시에도 disable 뒤 서명을 생략한 새 registry/head를 만들지 않는다. 기존 exact 카드의 전체 recovery reset을 구현했다고 세지 않는다.

## 6. 영속 이벤트·일회성 적용·clock

새 `authority_contract.py`/`ledger.py`는 foundation codec를 변경하지 않는다. canonical event는 원 `{schema:1,sequence,previous_sha256,observed_at,kind,payload,row_sha256}`이며 record-type을 `authority-event/1`로 고정한다. 이는 향후 운영 원장과 같은 wire다. 아래 초기 세 kind는 원 카드의 pending proposal 보관을 같은 저장 엔진의 비권한 phase로 명시한 추가 B이며, grant가 없는 초기 projection만 grant=null/registry_epoch=0이다. 이 phase에서는 archive 요청·적용을 허용하지 않는다. 아래 폐쇄 kind만 받는다.

| kind | payload의 실제 근거/효과 |
|---|---|
| ENROLLMENT_OPENED | engine가 생성해 보존한 기존 EnrollmentRequest 원문. 아직 비권한. |
| REGISTRATION_RECORDED | 실제 등록 원문+registration evidence+새 ProofRequest. 임시 공개키만, ACTIVE 아님. |
| INITIAL_PROOF_RECORDED | 원문 proof+실제 received_at+전체 BootstrapProposal digest. 아직 비권한. |
| AUTHORITY_INSTALLED | actual signed AuthorityGrantV1+동일 proposal 원문 commitment+완전한 초기 credential. 최초만 active. |
| REQUEST_OPENED | 실제 archive packet의 전체 request/manifest/inventory·display/challenge 또는 exact revoke target. 요청 알림 intent를 함께 보존. |
| ARCHIVE_APPLIED | 저장된 request ID+actual raw assertion/evidence+정확한 application+counter 관측+result intent. request 소비와 효과가 한 row. |
| CREDENTIAL_REVOKED | 현재 ACTIVE credential의 실제 revoke assertion+target/reason+epoch+1+result intent. 이후 해당 credential application의 current read는 REVOKED. |
| AUTHORITY_DISABLED | actual recovery-root signed disable+exact expected previous head+result intent. 모든 current use 거절. |
| REQUEST_CLOSED | EXPIRED/INVALIDATED 등 이미 인증되었거나 객관적으로 만료된 요청의 고정 사유. 잘못된 미인증 응답만으로 정상 pending을 소비하지 않음. |
| OWNER_CHECKPOINT_ADVANCED | **추가 정정 B**: 전체 signature/rotation/prefix 검증에 성공한 실제 더 뒤 owner head를 한 번 보존. 그 head의 code/key/restriction 때문에 grant가 무효가 되어도 eligibility 거절 **전에** 보존한다. 같은 head면 새 row 없음. |
| DELIVERY_REPORTED | 이미 committed intent의 전달 사실만. 실제 전송은 이번 단위에 없음. |

초기/새 epoch의 inactive request는 INVALIDATED로 projection하며 과거 이벤트를 수정하지 않는다. 이미 다른 유효 credential로 적용한 과거 application까지 epoch 변화만으로 폐기하지 않는다. 이번 단계는 active initial credential 하나와 self-revoke를 지원하며 추가 등록 API는 거절한다. individual application revoke는 미지원이고 기존 research-revoke가 새 domain을 처리한다고 가정하지 않는다.

상한은 원 카드의 event14MiB/state64MiB/credentials256·active16/pending128/requests4096/events16384/outbox8192와 envelope 원문 상한을 넘지 않는다. 이번 engine는 별도 `max_journal_bytes<=256MiB`, `max_backup_bytes<=256MiB`도 적용하고 전체 admission을 사전에 검사한다. 이벤트 수 제한은 공간 예약이 아니다. payload 원문·backup·state 누적 한도를 동시에 만족해야 하며 quota 초과 시 원본 삭제/자동 pruning/None 변환 없이 새 operation을 거절한다.

operation mutex → 실제 bounded replay/owner log authenticity → 필요한 owner restriction checkpoint 영속 → grant eligibility/packet/원문 crypto → 짧은 writer lock → independent head lock 순서다. owner log authenticity와 현재 grant 사용 가능성을 하나의 fail-fast helper로 합치지 않는다. 검증된 새 head가 key/code/revocation 조건 때문에 사용을 막더라도 먼저 checkpoint를 보존한 뒤 거절해야 한다. broken/unverified log는 절대 pin하지 않는다. checkpoint quota/write failure는 ACTIVE/성공이 아니라 INDETERMINATE로 멈춘다. 이 순서는 기존 app CurrentOwnerAuthority의 semantics를 바꾸지 않는 새 독립 engine 경로다. BundleStore/owner write lock 또는 네트워크를 writer/head lock 안에서 취득하지 않는다. pure replay는 자체 initial state에서 각 실제 canonical event를 한 번 parse/apply하며, crypto evidence도 실제 검증한다. 외부 State·validated cache를 받지 않는다. 과거 crypto는 해당 원문에 결합된 당시 시각/epoch로 replay하고, 현재 유효성은 마지막 grant/credential/owner/deployment와 현재 actual clock에서 별도 검사한다.

먼저 exact row를 primary+backup에 durable 보존하고 검증된 직접 successor에만 independent head를 전진시킨 뒤 다시 읽는다. response-loss retry는 **같은 request와 같은 raw evidence의 이미 완결된 row**에서 같은 application을 반환한다. 다른 assertion의 재사용은 거절한다. torn append/backup/head 불일치는 미사용으로 되돌리지 않고 INDETERMINATE; 완결된 row를 뒤의 실패 때문에 삭제하지 않는다. coherent rollback의 한계는 문서에 남긴다.

첫 actual owner 관찰부터 마지막 heavy packet/crypto/state/current-owner 확인까지 기존 30초를 유지한다. 원 관측 시각과 모든 완료 watermark, 날짜, request/grant/application expiry를 마지막 clock에서 비교한다. commit 뒤 최종 검증이 실패하면 durable historical row는 보존하되 current ACTIVE 성공을 반환하지 않는다. 최초 시간을 새 timestamp로 바꿔 늦은 작업을 통과시키지 않는다.

## 7. 반환과 앱 consumer 차단

`OperationResult`는 원 카드의 PENDING/APPLIED/EXACT_RETRY/EXPIRED/REJECTED/INVALIDATED/INDETERMINATE와 safe IDs/head/reason만 반환한다. APPLIED는 역사적 engine 적용 사실이다.

`EngineCurrentObservation`는 actual ledger/head/grant/request/evidence/application/credential status와 actual owner checkpoint·observed_at/completed_at/expiry를 담는다. status는 ACTIVE/EXPIRED/REVOKED/INVALIDATED이고 항상 `observation_scope=ENGINE_STATE_ONLY`, `operational_channel_ready=False`, `current_use_eligible=False`, `source_authenticated=False`, `research_selection_ready=False`, `execution_ready=False`다. 복사한 관찰을 앱에 주입하는 API는 만들지 않는다.

후속 실제 `PinnedBrokerClient`·독립 IPC/RP release가 완성되기 전 `authenticate_passkey_archive` production consumer는 **구현/등록하지 않는다**. 이번 통합 테스트는 실제 B1a 전체 graph+packet과 engine 기록을 대조하는 검증 harness이며 앱 운용 승인 입력이 아니다. Telegram 결과 outbox가 있어도 메시지 송신/사용자 읽음/승인을 주장하지 않는다.

## 8. 파일 소유 분할과 필수 검증

| 담당 단위 | 제안 파일 | 완료 조건 |
|---|---|---|
| 계약/독립 packet adapter | `tools/approval_broker/authority_contract.py`, `packet.py`; 별도 계약 tests | 기존 foundation/standalone packet golden bytes 및 실제 inventory 일치. 원 AuthorityGrant/Request/Applied wire·scope와 초기 전체 credential binding. |
| 독립 owner/release/bootstrap | `tools/approval_broker/owner_view.py`, `release.py`, `bootstrap.py`; 필요 최소 `tools/signer/sign.py` helper/새 command | 실제 target D14·현재 서명 log/prefix·release·root와 genuine enrollment/proof→root grant. 앱 import0, 기존 signer 회귀 불변. |
| 독립 원장 | `tools/approval_broker/ledger.py`; 실제 디스크 tests | 실제 3roots/lock/backup/head, fault injection·응답 유실·재시작·동시 apply/revoke·bounded streaming replay. |
| engine/CLI | `tools/approval_broker/engine.py`, `cli.py`; 순차 operation tests | 실제 저장된 요청에서 context를 재구성하고 실제 검증기를 호출. no supplied verifier/state/clock CLI. |
| 독립 통합 | 신규 passkey engine integration tests와 독립 runner registry | 실제 임시 root Ed25519+ES256+current signed owner/code+actual disk ledger+실제 B1a RAW/fixed/carry graph와 packet. |
| root/읽기 리뷰 | 환경·guard·registry·실행 근거·배포 | 앱/독립 환경 구분, 현재 25+61 회귀 유지. native/service claims는 actual 결과만. |

필수 수직 양성: engine가 생성·보존한 초기 요청→실제 none 등록/proof→실제 독립 root grant→설치→실제 불완전 RAW 및 fixed/carry packet→actual assertion 한 번 적용→재시작 exact retry→actual current read→actual self-revoke/독립 disable 뒤 거절. raw 실패 상태가 archive 확인으로 정상 연구가 되지 않아야 한다.

필수 음성: ID만 같은 다른 공개키/registration/proof·grant 변경, 잘못된/구형 root·owner prefix·target-env RECORD·release 파일, 패킷 누락/추가/변경과 raw→verified 연결, scope 확장, 늦은 관측·clock rollback·expiry, 두 assertion 경합/두 credential epoch 변경, 요청/원장·primary·backup·head 단독 rollback/중단/동시 writer, current-read 및 verified-new-head 거절 뒤 재시작 owner rollback(거절 head를 먼저 보존), invalid log를 pin하지 않음, checkpoint quota/write failure, enum/type/size/깊이·장기 replay의 operation count. 모든 양성은 실제 crypto/현재 원장 판독이며 `positive_verifier=True`를 사용하지 않는다.

사용자 입력 없이 코드·합성 키·임시 roots·실제 라이브러리·실제 저장과 packet 검증까지 구현할 수 있다. 운영 RP/domain, owner/recovery 공개키의 실제 신뢰 설정, 독립 설치/ACL, 실제 roots와 사용자 root 서명은 아직 미정인 운영 입력이다. 값이 있다고 간주하거나 사용자 키를 읽지 않는다. 이번에는 구현 승인 질문을 새로 만들지 않고 기술 계약으로 다음 작업을 준비한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다

## 부록 C — 2026-11-13 병렬 구현 인터페이스(구현 전)

이 부록이 다음 단위의 callable 이름과 파일 간 전달 계약이다. 원 카드의 승인 형식은 유지한다. 추가 pending/owner-checkpoint/disable 이벤트는 위 B의 명시적 확장이며, 해당 코드와 실제 수직 검증이 완료되기 전에는 기능 완료로 기록하지 않는다. 운영 설치·authenticated transport·app consumer는 범위 밖이다.

### C1. 공통 타입·wire와 제한

새 파일은 `tools/approval_broker/authority_contract.py`이며 별칭 `A`, 기존 foundation `contract.py`는 `C`로 표기한다. dataclass는 모두 frozen/slots/kw_only, 배열은 exact tuple, 원문은 exact bytes다. 생성자는 구조 검증만 하며 issuer가 아니다. 공용 오류는 `C.PasskeyError`의 고정 `PASSKEY_*` 코드로 통일한다.

- `Head(sequence:int, sha256:str)`: genesis만 0, 이후 양수 int64. SHA는 H.
- `OwnerCheckpoint(fingerprint:str, code_sha256:str, owner_head:Head, observed_at:datetime)`: owner sequence>=1.
- `FileDigest(name:str, byte_count:int, sha256:str)`: 상대 metadata 이름, byte_count int64>=0; path로 직접 사용하지 않는다.
- `DependencyDigest(distribution:str, version:str, record_sha256:str, artifact_sha256:str)`.
- `ReleaseManifest(role:str, python_version:str, files:tuple[FileDigest,...], dependencies:tuple[DependencyDigest,...])`: wire는 원 ReleaseManifestV1+재도출 manifest_sha256. role BROKER/RP만. 최대 파일8192/dependency256, 정렬 unique.
- `BrokerConfig`: 원 BrokerConfigV1의 **전체 필드 그대로**이며 `config_sha256`은 자신의 필드를 제외해 재도출한다. 별도 engine mode/ready 필드는 넣지 않는다.
- `Credential`: 원 CredentialV1의 **전체 필드 그대로**. algorithm=-7, state ACTIVE/REVOKED, revoked_at 명시 null/T. `.material()`은 현재 prefix의 실제 관측 counter/flags를 담은 `C.CredentialMaterial`을 반환하는 데이터 변환일 뿐이다.
- `GrantDocument(body_bytes:bytes, signature:bytes)`, `DisableDocument(body_bytes:bytes, signature:bytes)`: body_bytes는 각 exact body의 canonical bytes. envelope는 원 body object+canonical unpadded signature_b64다.
- `WebAuthnEvidence(request_sha256:str, assertion:C.Assertion, received_at:datetime)`: wire에 재도출 evidence_sha256을 포함. `.digest`는 실제 received_at까지 결합한다.
- `BootstrapProposal(enrollment:C.EnrollmentRequest, registration:C.Registration, registration_received_at:datetime, proof_request:C.ProofRequest, proof:WebAuthnEvidence, initial_credential:Credential)`: wire는 `{schema:1,enrollment,registration,registration_received_at,proof_request,proof,initial_credential,proposal_sha256}`. proposal SHA는 마지막 필드를 제외한 별도 domain. 실제 crypto 검증 책임은 C4/C6이고 이 구조의 생성 자체는 발급이 아니다.
- `RequestRecord(raw:bytes)`, `ApplicationRecord(raw:bytes)`, `NotificationIntent(raw:bytes)`: 각각 원 RequestV1/AppliedArchiveV1/NotificationV1의 canonical bytes만 보관한다. 검증된 읽기 속성은 Request의 `request_id,request_sha256,kind,display_bytes,challenge,challenge_expires_at,approval_expires_at`, Application의 `application_id,credential_sha256,bundle_digest,expires_at`, Notification의 `intent_id`다. raw는 caller가 구성할 수 있으므로 소비자는 실제 원장 membership을 별도로 확인한다.
- `ProposedEvent(kind:str, observed_at:datetime, payload_bytes:bytes)`: commit 제안 데이터. `LedgerEvent(sequence:int,previous_sha256:str,observed_at:datetime,kind:str,payload_bytes:bytes,row_sha256:str)`는 실제 full row. wire payload는 JSON object이며 bytes를 다시 base64로 겹쳐 저장하지 않는다.

`A.{config,release,credential,grant,disable,evidence,proposal,request,application,notification,event}_bytes(value)->bytes` 및 `A.parse_{config,release,credential,grant,disable,evidence,proposal,request,application,notification,event}(raw:bytes)->해당타입`을 제공한다. `A.grant_signing_bytes(document:GrantDocument|body_bytes:bytes)`처럼 overload를 두지 않고 **`grant_signing_bytes(body_bytes:bytes)->bytes`**, `disable_signing_bytes(body_bytes:bytes)->bytes`로 고정한다. `A.record_digest(record_type:str, canonical_bytes:bytes)->str`의 record_type은 이 모듈의 폐쇄 상수 목록만 허용한다.

기존 foundation `C.decode`는 bytes maximum을 늘려도 depth12/nodes4096/quoted scalar90000이므로 archive용으로 재사용하지 않는다. A는 별도의 fixed scanner를 사용한다: depth16/nodes500000, raw envelope 상한 검사 뒤 scalar 원문 길이<=해당 전체 record 한도, int64·float/NaN/중복·trailing 거절, exact wrapper 재인코딩. 파일 경로/hash/enum 같은 작은 scalar는 각 필드의 기존 작은 한도를 추가 적용한다. full row+LF 포함 max_event_bytes=14MiB, state=64MiB, grant/release=2MiB, request=12MiB, proof/registration/assertion 원문은 C의 기존 상한이다. 양성 큰 archive 회귀로 실제 parser 경계를 검증한다.

**좁은 foundation 변경 한 건:** `C.AssertionContext.purpose`에 `REVOKE_CREDENTIAL`만 추가한다. engine/replay는 실제 저장된 revoke request의 digest·challenge·target·epoch로 context를 만든다. revoke를 ARCHIVE_CONFIRM으로 표시하지 않는다. 기존 C wire/domain과 기존 두 목적의 동작은 그대로이며 실제 revoke 서명/목적 교차 음성 검사를 추가한다. 추가 등록/PORTAL_SESSION은 이 단위에서 지원하지 않는다.

### C2. packet.py — 독립 실제 packet 판독

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class PacketSnapshot:
    archive_request_bytes: bytes
    files: tuple[FileDigest, ...]       # request.json + payloads/p-<id>.bin 정렬 전체 목록
    packet_sha256: str

read_packet(directory: Path) -> PacketSnapshot
recheck_packet(directory: Path, expected: PacketSnapshot) -> PacketSnapshot
archive_target(packet: PacketSnapshot) -> bytes        # exact ARCHIVE_CONFIRM target canonical object
```

실제 `tools/signer/sign.py:_bundle_packet`/독립 `_ba_*` 검증 의미를 재사용하며 앱 import는 없다. files의 request.json hash는 원 raw request bytes, payload는 실제 streamed bytes의 길이/hash다. immutable snapshot은 authority가 아니고 `recheck_packet`은 항상 파일을 다시 읽는다. root/handle/path identity·정확한 file set·크기·actual hash를 최종 재확인한다. 반환에 private path/원본 금융값을 repr로 노출하지 않는다.

engine packet 위치는 operator-configured `packet_inbox/packet-<전체packet_sha256>`다. `open_archive_request` 입력은 그 실제 direct-child 디렉터리만 받는다. 이름과 실제 digest가 같아야 한다. 기존 exporter로 staging packet을 만들고 실제 digest를 얻은 뒤 이 이름으로 준비하는 것은 별도 명시 bootstrap/테스트 작업이다. engine가 입력 이름을 export path로 쓰거나 연구 payload를 새 engine에 복제하지 않는다. 이 규칙으로 원 RequestV1을 바꾸거나 서명되지 않은 임의 locator를 원장에 추가하지 않고 재시작 후 같은 packet을 다시 찾는다.

### C3. owner_view.py / release.py — authenticity 먼저, eligibility 나중

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class OwnerLocations:
    app_repo: Path
    app_environment: Path
    compliance_root: Path   # explicit; owner.jsonl, alerts.jsonl, snapshots/, approved/ layout
    public_key_path: Path

@dataclass(frozen=True, slots=True, kw_only=True)
class TrustRoots:
    initial_public_key_raw: bytes      # Ed25519 32 bytes, operator pinned
    initial_owner_head: Head           # positive signed/verified prefix
    recovery_public_key_raw: bytes     # Ed25519 32 bytes, explicitly pinned

@dataclass(frozen=True, slots=True, kw_only=True)
class OwnerLogEvidence:
    public_key_raw: bytes
    log_bytes: bytes
    anchors: tuple[Head, ...]
    observed_at: datetime
    completed_at: datetime
    head: Head

@dataclass(frozen=True, slots=True, kw_only=True)
class OwnerObservation:
    evidence: OwnerLogEvidence
    deployment_code_sha256: str | None
    deployment_problem: str | None
    completed_at: datetime

class OwnerReader:
    def __init__(self, *, locations: OwnerLocations, roots: TrustRoots, clock): ...
    def observe(self, *, retained: OwnerLogEvidence | None) -> OwnerObservation: ...

verify_owner_evidence(evidence: OwnerLogEvidence, *, roots: TrustRoots,
                      previous: OwnerLogEvidence | None) -> None
require_grant_eligibility(grant: GrantDocument, observation: OwnerObservation,
                          *, at: datetime) -> OwnerCheckpoint

target_deployment_code_hash(repo: Path, environment: Path) -> str
verify_release(directory: Path, manifest: ReleaseManifest, *, dependency_roots: tuple[Path, ...]) -> None
```

OwnerReader는 app/owner loader를 import하지 않는다. 실제 owner schemas/signature/rotation을 검토된 독립 signer와 대조하고 모든 retained prefix·external anchor를 검사한다. log 전체 authenticity가 깨지면 observation을 만들지 않는다. 반면 실제 최신 head의 key/code가 grant와 달라 사용을 막는 경우 **authentic observation을 반환하고 eligibility만 나중에 거절**한다. actual code scan 실패도 log 검증이 성공하면 `deployment_problem`을 고정 코드로 반환하여 verified restrictive head를 먼저 보존할 수 있게 한다. hash/problem 중 하나만 존재한다.

외부 anchor는 실제 `alerts.jsonl`의 head, snapshot head, approved `*.anchor.json`와 research-attestation 전용 inventory를 기존 의미대로 확인한다. absence/범위는 최초 명시 설치 당시 실제 상태에 맞추며, malformed나 읽기 실패를 조용히 생략하지 않는다. `verify_owner_evidence`는 evidence의 실제 signatures와 prefix를 다시 확인하는 **역사적 순수 검증**이며 파일/current-code/실제 clock 관찰을 주장하지 않는다. payload public key 자체를 root로 삼지 않고 TrustRoots부터 signed rotation을 확인한다. Owner evidence 최대 raw log8MiB/32768행/anchors8192이며 초과는 RESOURCE_LIMIT다.

`verify_release`는 선언한 경로+허용 inventory를 실제 읽고 bytes/RECORD/설치 파일을 대조한다. arbitrary runtime import/search path를 주지 않는다. 실제 target environment의 D14 RECORD를 사용하며 ambient broker 환경 metadata로 대체하지 않는다. 기존 signer code_hash와 같아야 하는 source closure golden 검사를 유지한다. KST/30초/actual last completion 검사는 engine가 최초 OwnerObservation 시각을 보존해 적용한다.

### C4. bootstrap.py — 실제 초기 증거와 독립 root 서명

```python
verify_bootstrap(proposal: BootstrapProposal) -> Credential
build_grant_body(proposal: BootstrapProposal, *, config: BrokerConfig,
                 broker_release: ReleaseManifest, rp_release: ReleaseManifest,
                 owner: OwnerCheckpoint, recovery_fingerprint: str,
                 issued_at: datetime, expires_at: datetime) -> bytes
verify_grant_document(document: GrantDocument, *, signer_public_key_raw: bytes) -> None
verify_disable_document(document: DisableDocument, *, recovery_public_key_raw: bytes) -> None
```

`verify_bootstrap`는 C의 실제 등록 verifier를 registration_received_at에서 호출하고 `C.proof_context`→실제 assertion verifier를 proof.received_at에서 호출한다. 요청·authority/epoch·credential ID·전체 등록 hash·initial created_at·proof evidence/최초 counter를 대조한다. C의 검증 결과를 입력으로 받지 않는다. `build_grant_body`는 데이터 builder이며 현재 owner/release 인증은 caller인 실제 독립 command/engine가 수행한다. signature 함수는 cryptography를 사용한다.

실제 signer 명령 `archive-authority-grant`는 별도 설치한 signer의 기존 isolated/terminal/typed-confirm/key unlock 방어를 통과하고 실제 current owner/release/config/원문 proposal을 재읽는다. 마지막 검증 뒤 실제 시각과 expiry를 확인해 owner key로 위 signing bytes만 서명한다. broker/engine API에는 sign 또는 private-key 인자를 추가하지 않는다. 테스트의 실제 임시 signer/키 경로는 운영 키가 아니다. release의 검토된 dependency로 standalone helper를 사용하되 `execution_launch`/`core` 또는 arbitrary repo path를 import하지 않는다.

### C5. authority_contract의 exact 추가 event payload

기존 AUTHORITY_INSTALLED/REQUEST_OPENED/ARCHIVE_APPLIED/CREDENTIAL_REVOKED/REQUEST_CLOSED/DELIVERY_REPORTED는 원 카드 §8 exact 필드를 그대로 쓴다. 기존 payload 안 원문을 생략하고 새로운 캐시 token으로 바꾸지 않는다. INITIAL_PROOF와 INSTALL에는 동일 원문을 재검증하며 전체 데이터 budget을 적용한다.

| 추가 kind | exact payload object |
|---|---|
| ENROLLMENT_OPENED | `{enrollment:EnrollmentRequestV1}` |
| REGISTRATION_RECORDED | `{enrollment_sha256:H,registration:RegistrationV1,registration_received_at:T,registration_evidence_sha256:H,proof_request:RequestV1}` |
| INITIAL_PROOF_RECORDED | `{enrollment_sha256:H,proof:WebAuthnEvidenceV1,initial_credential:CredentialV1,proposal_sha256:H}` |
| OWNER_CHECKPOINT_ADVANCED | `{evidence:{public_key_raw:B64(32),log_bytes:B64,anchors:[Head],observed_at:T,completed_at:T,head:Head}}` |
| AUTHORITY_DISABLED | `{disable:DisableEnvelope,notification:NotificationV1}` |

Owner checkpoint row를 적용하려면 full signature/rotation/prefix를 재검증한다. caller가 주장한 H/시각만 저장해서 current authority를 만들지 않는다. 바뀌지 않은 실제 head는 no-op이며 원장의 같은 event를 새 시각으로 다시 쓰지 않는다. valid 최신 head가 eligibility를 막아도 먼저 이 row를 보존하고 거절한다. quota/쓰기 실패는 INDETERMINATE, broken log는 pin하지 않는다.

새 `PendingEnrollment` projection의 exact 필드: `(enrollment,registration|None,registration_received_at|None,proof_request|None,proof|None,initial_credential|None,proposal_sha256|None)`이며 단계별 null 조합을 엄격히 제한한다. `RequestState(request:RequestRecord,state:str,evidence_sha256:str|None,application_id:str|None)`는 원 state enum만 받는다. `AuthorityState(grant:GrantDocument|None,registry_epoch:int,last_trusted_at:datetime|None,owner_evidence:OwnerLogEvidence|None,enrollments:tuple[PendingEnrollment,...],credentials:tuple[Credential,...],requests:tuple[RequestState,...],applications:tuple[ApplicationRecord,...],notifications:tuple[NotificationIntent,...],deliveries:tuple[bytes,...],disabled:bool,events:tuple[LedgerEvent,...])`다. `disabled`는 root-signed disable로만 전이하며 되돌리는 event는 없다. pregrant만 grant=null/epoch0이며 archive 요청은 불가하다. 순수 projection 생성 자체는 authority가 아니다.

### C6. ledger.py + authority_replay.py — 실제 replay와 short locks

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerRoots:
    primary: Path
    backup: Path
    head: Path

@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerLimits:
    max_event_bytes: int = 14 * 1024 * 1024
    max_state_bytes: int = 64 * 1024 * 1024
    max_journal_bytes: int = 256 * 1024 * 1024
    max_backup_bytes: int = 256 * 1024 * 1024
    max_events: int = 16384

@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerInstallation:
    authority_id: str
    config_sha256: str
    operator_paths_sha256: str
    roots: TrustRoots

@dataclass(frozen=True, slots=True, kw_only=True)
class LedgerSnapshot:
    head: Head
    context_sha256: str
    journal_bytes: int
    state: AuthorityState

class AuthorityLedger:
    def __init__(self, *, roots: LedgerRoots, installation: LedgerInstallation,
                 limits: LedgerLimits = LedgerLimits()): ...
    def inspect(self) -> LedgerSnapshot: ...
    def operation(self): ...    # yields private _Operation; OS nonblocking lock

class _Operation:              # created only by actual ledger.operation()
    def load(self) -> LedgerSnapshot: ...
    def commit(self, event: ProposedEvent, *, expected_head: Head) -> LedgerSnapshot: ...
    def check(self) -> None: ...

# authority_replay.py: no file/current clock access; real historical crypto
replay_events(raw_rows: tuple[bytes, ...], *, installation: LedgerInstallation,
              limits: LedgerLimits) -> AuthorityState
validate_transition(state: AuthorityState, event: LedgerEvent, *,
                    installation: LedgerInstallation, limits: LedgerLimits) -> AuthorityState
```

Limits exact ints만, 각 기본값 이하만 허용한다. 기타 credential/request/outbox 수는 원 fixed v1 limits다. context/genesis는 installation 전체 canonical bytes+limits와 실제 root identities를 결합한다. root는 미리 존재하는 명시 별도 local directories만. `prepare-authority-store` operator helper만 empty journal/operation.lock/writer.lock/backup 및 head namespace `authority-<전체ID>`의 head.json/head.lock을 만든다. runtime constructor/read는 파일을 만들거나 없는 head를 채택하지 않는다. 모든 준비 중단 잔재와 orphan backup은 보존·거절한다.

operation lock을 owner/crypto/packet 검사 동안 유지한다. `_Operation`은 thread/수명/root/lock identity를 보존하고 nested store work 전후 확인한다. 각 `load/commit`은 실제 primary/backup/head의 snapshot을 short writer lock으로 확보한 뒤, writer/head lock **밖**에서 자기 disk bytes/genesis로 full historical crypto replay한다. proposal의 실제 grant/proof/assertion과 prefix-local counter를 검증한 뒤 writer→head lock 안에서 동일 prefix bytes/inventory/head를 다시 읽어 그대로인지 확인하고 append/backup/head를 확정한다. `expected_head`는 추가 제한일 뿐 prior-state authority가 아니다.

operation/pin의 healthy cleanup은 본문에서 발생한 고정 SIGNATURE_INVALID/EXPIRED 등 PasskeyError를 그대로 전달한다. 실제 lock/root/integrity cleanup failure만 STORE_INDETERMINATE로 덮을 수 있으며 generic ValueError를 무조건 I/O 실패로 바꾸지 않는다.

head 전진 중에는 이미 검증한 실제 prefix와 새 row의 직접 연결·정확한 backup/readback만 확인한다. full historical crypto를 다시 수행하는 head-CAS callback이나 중첩 owner/BundleStore lock은 없다. 외부 supplied State/validated flag/cache로 검증을 생략하는 API는 없다. `validate_transition`의 public arbitrary state는 실제 events부터 재구성한다. store 내부의 한 operation에 한정된 fold는 자기가 검증한 disk prefix에만 사용할 수 있으며 최종 actual disk equality가 필요하다. 각 full pass는 각 행/증거를 한 번씩 검증하고 prefix 전체를 행마다 재검증하지 않는다. test는 operation count로 이를 확인한다.

historical replay는 등록→proof→각 적용 순서의 **직전 counter**와 원 received_at을 쓴다. 최종 ACTIVE/REVOKED credential을 과거 검증에 역사용하지 않는다. 동일 응답의 retry는 새 now-stamped WebAuthnEvidence를 만들기 **전에**, 입력 canonical Assertion bytes/request ID를 이미 committed된 원 Assertion과 비교해 기존 evidence/received_at/application을 반환한다. 원문 received_at을 다시 쓰거나 오늘의 challenge TTL로 역사적 성공을 지우지 않는다. 현재 유효성은 별도의 fresh current operation이다.

### C7. engine.py — exact 반환·구성·현재 확인

`Engine.__init__(*,config:BrokerConfig,ledger:AuthorityLedger,owner_reader:OwnerReader,broker_release_root:Path,broker_release:ReleaseManifest,rp_release_root:Path,rp_release:ReleaseManifest,dependency_roots:tuple[Path,...],clock)`는 trusted composition 전용이다. 정확한 concrete classes와 동일 clock을 요구하되 그것을 OS 격리 증명이라고 하지 않는다. CLI는 실제 UTC clock 하나를 직접 만들고 사용자가 넣는 clock/provider/status 옵션을 받지 않는다. `Engine.open(config_path)`는 명시 설치 sidecar의 실제 경로로 이 구성을 만들며 누락된 운영 서비스가 준비됐다는 상태를 만들지 않는다.

공개 operation 이름/인자는 §5 그대로다. `submit_initial_proof`가 반환하는 BootstrapProposal은 역사적 검증 원문이고, `install_grant`는 저장된 동일 proposal membership과 실제 grant/root/current/release를 다시 확인한다. self-revoke는 정확한 저장 request에서 만든 REVOKE_CREDENTIAL context를 실제 verifier로 검증한다. ENGINE_STATE_ONLY 반환을 서명된 current transport envelope로 가장하지 않는다.

- `OperationResult(status:str,request_id:str|None,application_id:str|None,head:Head|None,reason:str)` — 원 허용 status/reason만. pending 상태에서 확정 application을 만들지 않는다.
- `ProposalReceipt(proposal_sha256:str,byte_count:int,sha256:str)` — output write/readback 사실만, 서명 아님.
- `HistoricalEngineSummary(authority_id:str,head:Head,grant_sha256:str|None,registry_epoch:int,credential_count:int,pending_request_count:int,application_count:int,pending_notification_count:int,disabled:bool)` — 현재 인증 없이 실제 backed replay 사실.
- `EngineCurrentObservation(authority_id:str,application_id:str,grant_sha256:str,registry_epoch:int,authority_head:Head,owner_checkpoint:OwnerCheckpoint,request_sha256:str,evidence_sha256:str,packet_sha256:str,status:str,observed_at:datetime,completed_at:datetime,expires_at:datetime)` — status ACTIVE/EXPIRED/REVOKED/INVALIDATED. 속성 `observation_scope='ENGINE_STATE_ONLY'`, operational_channel_ready/current_use_eligible/source_authenticated/research_selection_ready/execution_ready=False 고정. 현재 검증 불가면 관찰 객체 대신 고정 오류.

현재 operation 순서는 실제 ledger load → authentic owner 관찰 → 필요 checkpoint commit → grant eligibility/release/packet/assertion → 적용 commit → 실제 ledger·owner·release·packet 최종 확인 → 마지막 clock이다. 최초 관찰의 30초/날짜/완료 watermark/모든 expiry를 유지한다. 새로운 제한 때문에 거절해야 하면 checkpoint부터 보존하고, 그 보존이 불확실하면 ACTIVE/성공이 아니다. commit 뒤 최종 실패가 이미 durable인 application을 되돌리지 않는다.

### C8. 소유권·교차 검증 시작 조건

1. 계약/packet 담당: A의 exact codecs/dataclasses와 packet adapter, C의 REVOKE_CREDENTIAL 한 enum 확장 및 해당 genuine crypto 검사. 기존 C 두 codec 목적/wire 회귀를 계속 실행한다.
2. 독립 root 담당: owner_view/release/bootstrap 및 signer 최소 연결. 공개 typed 결과를 actual current observation으로 주입하지 않는 CLI composition과 D14 두 환경 parity를 소유한다.
3. 저장 담당: ledger/authority_replay와 실제 fault/restart/race tests. owner evidence의 역사적 순수 verifier는 2번이 제공하며, 역할 사이 function 이름은 C3 그대로다.
4. engine 담당: engine/cli, 실제 frozen request→crypto→durable effect의 통합과 현재 restriction 순서. 저장된 요청을 engine 밖에서 공급받아 대체하지 않는다.
5. 독립 integration 담당: 실제 임시 Ed25519 root log/code approval+ES256 enrollment/proof+actual disk/head+실제 BundleStore/packet을 연결한다. source/owner/release 기능을 True로 바꾸는 양성 verifier 없음. 실제 임시 RP 파일 commitment와 아직 하지 않은 RP/IPC 기능 검증을 결과에서 구분한다.

각 담당이 이 exact 인터페이스를 확인한 뒤 코드에 들어간다. 이름/record 변경은 공유 카드에서 먼저 합의한다. 타입 파일만 준비된 상태는 전체 단위 완료가 아니며, 초기 grant→실제 한 번 적용→재시작→폐기→fresh current refusal와 관련 기존 회귀가 같은 frozen source에서 검증되어야 다음 단계의 완료 ID를 정한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
