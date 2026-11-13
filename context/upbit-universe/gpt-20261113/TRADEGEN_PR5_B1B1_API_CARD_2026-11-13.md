# PR5 B1b-1 API 계약

작업 트리 `/workspace/tradegen-bundle-attestation-1113`, base `3ca4dee`. 실제 원본 보관 내용의 소유자 확인만 다룬다. source provenance/strategy selection/activation/exact recovery 권한은 부여하지 않는다. B1a 트리는 수정하지 않는다.

## 형식 — protective_hold_design

새 `execution_launch/bundle_attestation.py`, `tests/launch_bundle_attestation.py`.

Constants:

```python
PURPOSE = 'research_archive_manifest_attestation'
SCOPE = 'archive_manifest_identity'
REQUEST_DOMAIN = b'tradegen-research-archive-attestation-request/1\n'
SIGNING_DOMAIN = b'tradegen-research-archive-attestation/1\n'
FILE_SET_DOMAIN = b'tradegen-research-archive-file-set/1\n'
DOCUMENT_DOMAIN = b'tradegen-research-archive-attestation-document/1\n'
MAX_REQUEST_BYTES = 12 * 1024 * 1024
MAX_DOCUMENT_BYTES = 13 * 1024 * 1024
MAX_VALIDITY_SECONDS = 86400
APPROVED_CHECKS = (
    'exact_manifest_and_entire_file_inventory',
    'all_available_original_bytes_match',
    'raw_and_verified_link_exact',
    'raw_incomplete_and_failure_statuses_visible',
    'archive_only_scope_and_expiry_reviewed',
)
```

JSON는 ASCII canonical bytes(sort_keys, compact separators, ensure_ascii=True, allow_nan=False), newline 없음. envelope도 newline 없음. 실제 원본 payload bytes는 그대로 보존한다. exact keyset/type/정수·깊이·node/byte 제한과 duplicate-key 거절. 코드는 `ARCHIVE_ATTESTATION_*` 고정 진단만 사용하고 대문자 CANONICAL 문자열은 쓰지 않는다.

```python
request_from_manifests(raw_manifest: bytes, verified_manifest: bytes | None, *,
    requested_at: datetime, expires_at: datetime, deployment_code_hash: str) -> dict
parse_archive_request(raw: bytes) -> dict
archive_request_bytes(request: dict) -> bytes
archive_request_digest(request: dict) -> str  # validates stored request_sha256
payload_filename(logical_id: str) -> str       # '<logical_id>.bin', no folders
file_set_digest(payload_files: list[dict]) -> str
validate_request_payloads(request: dict, payloads: Mapping[str, bytes]) -> None

attestation_body(request: dict, *, owner_fingerprint: str, issued_at: datetime) -> dict
attestation_signing_bytes(body: dict) -> bytes
attestation_document_bytes(body: dict, signature: bytes) -> bytes
parse_attestation_document(raw: bytes) -> dict
attestation_document_digest(raw: bytes) -> str
verify_attestation_signature(raw: bytes, *, public_key_raw: bytes) -> dict  # body only
```

verify_attestation_signature는 실제 Ed25519 수학 검증만 한다. public_key_raw 자체가 신뢰된 키라는 주장을 하지 않는다. clock/key loading/owner authority/store I/O 없음. signature가 올바른지와 현재 사용 가능한지는 별개다. 모든 함수는 입력 dict를 보존하고 반환값은 detached dict이다.

`request_from_manifests`는 strict B1a parsers로 정확한 canonical 원문을 읽는다. verified가 있으면 `validate_verified_inputs`를 수행한다. 대상 파일 집합은 raw 대상이면 raw.files, verified 대상이면 verified.files 전체다. verified는 raw 전체를 포함하므로 logical ID를 기준으로 별도 필터·중복 제거·성공 후보 선별을 하지 않는다.

Unsigned request exact keys:

```python
{
 'schema_version': 1,
 'artifact_kind': 'unsigned_research_archive_attestation_request',
 'purpose': PURPOSE, 'scope': SCOPE,
 'requested_at': '<UTC microseconds>', 'expires_at': '<UTC microseconds>',
 'deployment_code_hash': '<64hex>',
 'bundle_kind': 'RAW_ARCHIVED' | 'VERIFIED_UNAPPROVED',
 'bundle_digest': '<B1a domain digest of target>',
 'input_archive_digest': '<B1a raw archive digest, ALWAYS populated>',
 'raw_manifest_sha256': '<SHA256 of exact raw manifest bytes>',
 'verified_manifest_sha256': '<SHA256 or null>',
 'raw_manifest': {... strict raw manifest body ...},
 'verified_manifest': {... strict verified manifest body ...} | None,
 'payload_files': [ {'logical_id': str, 'byte_count': int, 'sha256': str}, ... ],
 'file_set_sha256': '<domain SHA256 of exact payload_files list>',
 'request_sha256': '<domain SHA256 of request without this key>',
}
```

payload_files는 target.files에서 도출한 logical_id 정렬 exact list다. generated payload file은 packet의 `payloads/<payload_filename(logical_id)>`로 고정한다. 원본 original_name/source_name은 경로로 사용하지 않는다. empty 원본도 exact 빈 .bin 파일로 내보내고 hash한다. 원본 수집 누락 상태는 raw manifest에 그대로 남고 가짜 빈 파일로 대신하지 않는다.

requested_at < expires_at <= requested_at + 24h. requested_at은 verified이면 evaluated_at 이상이어야 한다. raw에는 존재하지 않는 관측·평가 시각을 요구/합성하지 않는다. expiry는 caller의 명시 값이며 자동 기본값/연장 없음.

Signed body exact keys:

```python
{
 'schema_version': 1, 'purpose': PURPOSE, 'scope': SCOPE,
 'request': {... exact unsigned request ...},
 'deployment_code_hash': '<equal request value>',
 'owner_fingerprint': 'SHA256:<64hex>', 'reviewer_id': 'owner:<64hex>',
 'issued_at': '<UTC microseconds>', 'expires_at': '<equal request expiry>',
 'approved_checks': list(APPROVED_CHECKS),
}
```

requested_at <= issued_at < expires_at, expires_at-issued_at <=24h。서명키와 현재 owner/code는 signer/auth가 독립 확인한다. body가 현재 승인 조건을 만들어주지 않는다. envelope exact keys=`body,signature_b64`; canonical base64 64-byte Ed25519 signature. 같은 대상을 재검증하는 것은 가능하며 1회용 주문권한이 아니다.

## Source closure 결정

새 작은 수동 source hash 목록을 만들지 않는다. existing D14 `owner.code_hash(repo)` / standalone `signer.code_hash(repo)`는 recursive execution_launch와 그 실제 의존성 및 도구를 포함한다. 새 format/auth/exporter도 이 closure에 포함된다. request의 deployment_code_hash는 주장일 뿐이며 **signer는 현재 실제 code_hash와 현재 code approval, auth는 실제 CurrentOwnerAuthority의 봉인 context code_hash/code_signed를 대조**한다. callback/caller가 넘긴 hash로 대체하지 않는다. 독립 signer 자체는 기존 repo 밖 복사본·사용자 해시 확인 신뢰 경계에 남는다.

## Packet/CLI — notion_revision

새 `bundle_review.py`와 관련 테스트. exact packet tree는 `request.json` 한 개와 `payloads` 실제 디렉터리 한 개, 그 안에 정확한 generated .bin 파일 집합이다. 별도 raw/verified manifest 파일은 request에 exact canonical body로 포함되므로 만들지 않는다. 원본 bytes 모두를 복사하며 private packet이다. 추가 파일·링크·부분파일·교체를 거절하고 재시도에 기존 패키지를 덮어쓰지 않는다.

```python
export_review_packet(store, bundle_digest, output_dir, *, requested_at, expires_at,
                     deployment_code_hash) -> dict  # exact request
```

실제 store require_backup=True로 raw/verified graph를 읽고 verified의 raw도 읽어 연결한다. exporter가 새 현재 승인이나 실제 서명을 발급하지 않는다. 요청 hash는 명시 입력이어도 signer/auth 독립 확인 필수. CLI currentcode 계산은 기존 신뢰 code_hash를 사용하고 사용자 입력 hash를 현재값으로 간주하지 않는다. 출력은 digest/status만, 원본·금액·경로 없음.

## Independent signer — revision_review

`bundle-attest --repo --packet --expires-at --output`(+기존 --key). --expires-at은 request.expires_at과 exact 일치해야 하며 signer가 요청을 수정하지 않는다. packet 전체 독립 parse/file hash → 현재 code/key/owner head 확인 → scope/incomplete inventory/expiry 표시 및 직접 확인 → unlock → owner log lock → code/key/head/packet 전체/actual clock 재검증 → 새 detached 파일. scope는 archive-only이며 미구현 source/selection/recovery를 암시하는 문구 없음.

모든 parser/digest/manifest link validator는 standalone 복사본이며 앱 import 금지. B1a format에서 사용하는 PayloadReference 표현 검사는 독립으로 복제한다. physical object store 자체를 서명기에서 승인하지 않고 packet에 복사된 exact logical file bytes를 확인한다. root가 signer/앱 golden 검증 및 write guard를 확인한다.

## 실제 인증 — pr4e_owner

새 `bundle_auth.py`와 관련 테스트:

```python
authenticate_bundle_attestation(store, bundle_digest, document_bytes, *,
    authority_provider: CurrentOwnerAuthority, clock) -> ArchiveAttestationAssessment
```

실제 provider exact 타입/동일 clock, 초기 관찰 → 실제 raw/verified backup 포함 graph → manifests로 request 재도출·file bytes 대조 → 실제 서명 → 동일 provider 재관찰 → 종료 시각/freshness/rollback/expiry 확인. owner/context는 sealed/hash·현재 서울 날짜·owner.ok·code_signed·현재 PEM fingerprint 및 key/code/head 일치 확인. archive-only이므로 active.valid/halts/가짜 계좌를 거래 승인처럼 요구하지 않는다. 이 판단은 기존 전략·거래 gate에 적용하지 않는다.

Assessment는 대상·검사 시각·archive_identity_authenticated를 표시하는 비권한 결과다. **source_authenticated=False, research_selection_ready=False, execution_ready=False, automatic_recovery_supported=False, current_use_eligible=False, revocation_status='UNSUPPORTED'**로 남긴다. 이 객체를 재입력하여 인증을 생략하는 consumer 없음. 새로운 code/source/키로 변조하거나 오래된 provider를 현재로 재표기하지 않는다.

모든 구현/검사는 별도 새 트리·임시 home·가짜 서명키·fake source에서만 수행한다. 실제 owner home/keys/API/orders 없음. root가 registry/guard/통합 검사·commit을 소유한다.
