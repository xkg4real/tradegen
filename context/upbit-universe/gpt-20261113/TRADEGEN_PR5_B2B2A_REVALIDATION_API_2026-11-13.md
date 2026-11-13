# PR5 B2b-2a — 완성된 복구 사본의 실제 재검증 API

2026-11-13. 전용 `tradegen-recovery-revalidation-1113`, base main `ed1b456`. 이 카드는 구현 계약이며 테스트 통과·복구 실행·운영 승인이 아니다. 소유: protective_hold_design=`execution_launch/bundle_recovery.py`; notion_revision=`tests/launch_recovery_revalidation.py`; pr4e_runner=읽기 검토; root=registry/guards/동결 검증/commit.

## API

```python
verify_restored_archive(
    destination: BundleStore,
    bundle_digest: str,
    attestation_bytes: bytes,
    *, incident_id: str,
    authority_provider: CurrentOwnerAuthority,
    clock,
) -> RestoredArchiveVerification
```

- 실제 exact BundleStore와 exact CurrentOwnerAuthority, provider와 동일 clock을 요구한다. source 입력·원본 백업·cached RecoveryResult·caller의 authority/revoked/complete boolean은 받지 않는다.
- `incident_id`는 기존 `restore_signed_backup`에 전달한 **동일 artifact ID 문자열**(`[a-z][a-z0-9_-]{0,63}`)이다. 이번 API는 B2b-1 full incident hash를 대신하거나 durable 사건 linkage를 검증하지 않는다. full hash encoding/controller는 다음 단위다.
- artifact digest/expected bytes는 기존 `build_recovery_artifact(attestation_bytes, incident_id, destination.limits)`에서 직접 도출한다. caller가 artifact digest나 원문 목록을 바꿔 전달할 수 없다.
- 원래 signed raw/verified 전체 graph, 모든 original files와 primary/backup, exact signature artifact 및 그 backup을 실제 읽는다. raw 실패 원본은 raw 그대로다. 목적지의 완성 사실을 확인하며 원래 복사 행위를 재구성하거나 새 현재 사용 권한을 만들지 않는다.

```python
@dataclass(frozen=True, kw_only=True)
class RestoredArchiveVerification:
    status: str                      # RESTORED_ARCHIVE_REVERIFIED
    scope: str                       # archive_identity_only
    incident_id: str
    bundle_kind: str
    bundle_digest: str
    input_archive_digest: str
    request_sha256: str
    attestation_sha256: str
    recovery_artifact_digest: str
    verified_at: datetime
    revocation_status: str           # REVOKED | NOT_REVOKED_AT_HEAD, required/no optimistic default
    revocation_target_sha256: str
    revocation_owner_head: tuple[int, str]
    destination_backup_verified: bool = True
    signature_backup_verified: bool = True
    archive_storage_modified: bool = False
    source_authenticated: bool = False
    research_selection_ready: bool = False
    current_use_eligible: bool = False
    execution_ready: bool = False
    automatic_operational_recovery_supported: bool = False
    quarantine_release_supported: bool = False
```

`REVOKED`도 archive identity가 유효한 목적지의 관찰 결과로 반환한다. 이는 generic `bundle_auth`의 역사적 보관 의미와 같다. 자동 복구 controller는 후속 구현에서 이 실제 관찰의 철회를 거절 조건으로 소비해야 하며, 이 helper는 복사를 실행하지 않는다. `NOT_REVOKED_AT_HEAD`는 해당 최종 owner head의 유한 관찰일 뿐 현재 사용 permit이나 lease가 아니다. 만료/키 변경/code 변경/서명 불일치/owner 불완전은 기존 실제 검증에서 거절한다.

## 실제 호출 순서와 공유 범위

1. exact destination/provider/bytes/target 확인, 실제 store configuration 검증, 기존 pure artifact codec으로 기대 bytes/digest 생성. 새 artifact schema나 서명 domain 없음.
2. 실제 첫 owner 관찰과 `_authority`로 검증 transaction 시작.
3. 실제 artifact `read_raw(require_backup=True)`와 전체 기대 bytes 비교.
4. 실제 `authenticate_bundle_attestation`로 target/raw primary·backup 전체를 두 번 읽고 현재 owner/key/code/time 검증.
5. artifact 전체/backup을 실제 다시 읽고 exact 비교. destination configuration 최종 검사.
6. 최종 실제 provider 관찰에서 `_authority`, 원래 최초 관찰/기간/KST-day 검증을 준비하고, **같은 최신 context의** canonical revocation target + 실제 restrictive set membership + owner head를 계산한다.
7. 모든 무거운 작업 이후 completion clock을 읽고 최초 transaction 관찰부터 30초, 원래 signature expiry, rollback/date를 bounded 비교한다. 이 시각 뒤에는 graph/서명/철회 parsing 또는 owner I/O 없음.

공유는 기존 copy-final의 artifact→actual auth→artifact 읽기 helper와 final observation 완료 함수를 좁게 추출한다. 기존 `_finish` 3개 반환값 계약은 wrapper로 보존 가능하다. 새 결과용 revocation 계산은 optional 내부 관찰일 뿐 authority 입력이 아니다.

**기존 restore 의미 보존:** copy 이후 final first observation을 잡고 공유 graph helper를 수행한 다음, 기존 `_separate(source,destination)`를 그대로 **마지막 completion clock 이전**에 수행한다. 같은 actual provider가 inspection/prewrite/copy-final의 key/code/head pins를 유지한다. 기존 RecoveryResult/RecoveryInspection의 archive-only scope·UNSUPPORTED 표시·원본 보존·partial retry·exact artifact bytes를 이번 변경으로 바꾸지 않는다. source 권한/조건을 완화하는 변경이 아니다.

## 오류·미구현·검증

기존 고정 `BUNDLE_RECOVERY_*`/`ARCHIVE_AUTH_*`/bundle store/artifact 진단을 유지한다. missing/partial artifact, target/raw/backup 손상, swapped incident/document, 잘못된 target, unprovisioned destination, fake provider/store, root/lock/head 변경은 거절한다. 원본/목적지 쓰기·provision·adopt·sign·evaluate·message·order 호출은 없다. actual owner loader의 기존 verified-state snapshot/제한 anchor 동작은 별도 기존 경계다.

필수 검사는 실제 B2 복구 후 source primary와 backup을 unavailable로 만든 positive, raw와 verified/all-candidate/failed-original exact 보존, 필수 signature artifact/backup 누락·변조, source helper 호출 금지, caller result/boolean 거절, actual current owner의 마지막 철회/head 증거, reserialized signing-target 불변 의미, expiry/30초/rollback/date/code/key/owner-prefix 및 마지막 artifact/철회 계산 지연이다. 기존 B2 전체 회귀와 실제 temporary signature fixture로 공통 경로 의미를 검증한다. 일회용 테스트 key·19 KEYLESS·임시 홈 외 실제 자격/홈/API를 사용하지 않는다.

attempt store/controller, full incident mapping, B2b-1 보류 해제, 선발 route 변경, 실제 알림, 거래 연결은 미구현으로 남긴다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
