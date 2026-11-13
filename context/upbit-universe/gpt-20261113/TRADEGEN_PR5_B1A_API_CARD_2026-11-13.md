# PR5 B1a 공용 API 카드

기준: `/workspace/tradegen-research-bundle-1113`, base `2879b53`. 2026-11-13. 아래 객체·digest·저장 receipt는 비권한 기록이며 실제 평가·출처·소유자 승인·복구 권한을 발급하지 않는다. 모든 dataclass는 frozen/kw_only이고 정확한 타입을 재검사한다.

## 1. 형식 담당 — protective_hold_design

파일: `execution_launch/research_bundle_format.py`, `tests/launch_research_bundle_format.py`.

`BundleFormatError(ValueError)`는 고정 `BUNDLE_*` 코드만 반환한다. 형식은 `FORMAT_INVALID`, 크기 admission은 `RESOURCE_LIMIT`으로 구분한다. 원본 bytes를 canonical JSON으로 다시 저장하지 않는다. canonical codec는 envelope에만 적용한다.

```python
BundleLimits(
    max_manifest_bytes=4*1024*1024, max_files=2048,
    max_file_bytes=64*1024*1024, max_total_bytes=512*1024*1024,
    max_candidates=128, max_name_bytes=1024,
)
DEFAULT_LIMITS: BundleLimits

BundleFile(
    logical_id: str, original_name: str, source_name: str | None,
    role: str, study_id: str | None,
    required: bool, byte_count: int, sha256: str,
    payload_ref: PayloadReference | None,
)
InputObservation(
    observation_id: str, original_name: str, source_name: str | None, role: str,
    study_id: str | None, required: bool,
    status: str, logical_id: str | None,
)
RawArchiveManifest(
    schema_version: int, kind: str, run_id: str, revision_id: str, attempt_id: str,
    parent_bundle_sha256: str | None,
    storage_policy_sha256: str, object_policy_sha256: str,
    expected_candidates: tuple[str, ...] | None,
    inventory_complete: bool,
    observed_inputs: tuple[InputObservation, ...], files: tuple[BundleFile, ...],
)
CandidateEvidence(
    study_id: str, protocol_digest: str,
    capture_logical_id: str, result_digest: str,
)
VerifiedBundleManifest(
    schema_version: int, kind: str, run_id: str, revision_id: str, attempt_id: str,
    parent_bundle_sha256: str | None,
    storage_policy_sha256: str, object_policy_sha256: str,
    input_archive_digest: str,
    plan_digest: str, profile_digest: str, rules_digest: str, registry_digest: str,
    source_digest: str, family_digest: str, receipt_audit_digest: str,
    evaluator_revision: str, source_kind_claim: str,
    capture_start: datetime, capture_end: datetime, evaluated_at: datetime,
    candidates: tuple[CandidateEvidence, ...], files: tuple[BundleFile, ...],
)

raw_archive_bytes(manifest, *, limits=DEFAULT_LIMITS) -> bytes
parse_raw_archive(raw: bytes, *, limits=DEFAULT_LIMITS) -> RawArchiveManifest
raw_archive_digest(manifest, *, limits=DEFAULT_LIMITS) -> str
verified_bundle_bytes(manifest, *, limits=DEFAULT_LIMITS) -> bytes
parse_verified_bundle(raw: bytes, *, limits=DEFAULT_LIMITS) -> VerifiedBundleManifest
verified_bundle_digest(manifest, *, limits=DEFAULT_LIMITS) -> str
validate_verified_inputs(raw_archive, verified, *, limits=DEFAULT_LIMITS) -> None
validate_payloads(manifest, payloads: Mapping[str,bytes], *, limits=DEFAULT_LIMITS) -> None
```

- Schema는 exact integer 1. kind는 각각 `RAW_ARCHIVED`, `VERIFIED_UNAPPROVED`. domain은 `b'tradegen-research-raw-archive/1\x00'`, `b'tradegen-research-bundle/1\x00'`.
- run/revision/attempt/study ID는 기존 `[A-Za-z][A-Za-z0-9_.:-]{0,95}` 문법. **경로로 사용하지 않는다.** logical/observation ID는 `[a-z][a-z0-9_-]{0,63}`. 실제 저장 key는 digest.
- `original_name`은 bounded UTF-8 metadata일 뿐 경로가 아니다. raw의 대소문자·NFC·예약명 차이를 보존한다. 실제 파일 경계는 adapter/store가 검사한다. 이를 그대로 export 경로로 사용하지 않는다. source_name은 source_file 역할에서만 repo 상대 이름 metadata이고 다른 역할은 None이다. raw에서는 비정상 source_name도 bounded metadata로 보관할 수 있고 verified에서 엄격히 검사한다.
- 역할: `plan`, `profile`, `registration_commitment`, `capture`, `incomplete_capture`, `source_receipts`, `program_source`, `capture_source_manifest`, `source_file`, `prior_research`, `report`, `other_input`, `evaluation_record`.
- input status: `COLLECTED`, `MISSING`, `REFUSED`, `CHANGED`, `LIMIT_EXCEEDED`, `NOT_READ`. COLLECTED에만 logical_id 필수이고 같은 metadata의 파일을 정확히 하나 참조한다. files와 COLLECTED 관측은 전단사다. 빈 raw inventory도 표현 가능하며 정상 연구가 아니다. expected_candidates=None은 unknown이고 빈 tuple과 구분한다.
- tuples는 logical_id/observation_id/study_id별 사전식 정렬·중복 없음. 원본 이름 중복/대소문자 별칭은 raw에서 metadata로 보존한다. verified는 같은 역할 내 casefold/NFC 이름 충돌·불안전 상대 이름 및 other_input/incomplete_capture를 거절한다. source_file의 경로 구분은 source_name을 사용한다.
- 빈 파일은 정확히 `byte_count=0`, `sha256=SHA256(b'')`, `payload_ref=None`. nonempty는 exact PayloadReference이고 payload bytes/hash/policy가 파일·manifest와 일치해야 한다. store는 empty에 object.stage를 호출하지 않고 b''를 반환한다.
- source_kind_claim은 prospective_paper_capture/synthetic/retrospective_replay. evaluator는 forward-paper-v1/forward-paper-carry-v2만. 시간은 aware datetime → UTC microsecond 문서형식, start<end<=evaluated_at.
- verified에는 raw.files 전체를 동일 항목으로 포함하고 추가 파일 역할은 evaluation_record/report뿐. evaluation_record는 정확히 한 개. raw는 evaluation_record 역할을 받지 않는다.
- `validate_verified_inputs`는 raw digest= input_archive_digest, 동일 run/attempt/정책, 서로 다른 revision, raw의 complete inventory·expected nonempty set·모든 관측 COLLECTED, verified candidates=expected, 정확한 capture file study ID 대조, raw.files 전부 동일 포함을 검사한다. 새 판정은 기존 manifest 수정이 아니다. 실제 plan/source/receipt/evaluator 진위는 adapter 재검증 책임이다. parent_bundle_sha256는 보관 계보 주장이지 과거 모든 attempt의 완전성 검증이 아니다.
- parser는 exact keyset/type/중복 key/깊이/노드/정수 자릿수/크기를 제한하고 canonical envelope bytes만 받는다. dataclass를 직접 구성·변조해도 serialize/validate에서 재검사한다. float/NaN/Infinity 금지.
- `validate_payloads`는 files의 정확한 logical_id 집합과 bytes의 길이/SHA를 확인한다. payload_ref의 실제 object graph 읽기는 store 책임이다.

## 2. Receipt 담당 — revision_review

파일: `execution_launch/study_receipts.py`, `tests/launch_study_receipts.py`.

```python
ReceiptLimits(max_log_bytes=64*1024*1024,max_line_bytes=512*1024,
    max_records=20002,max_json_depth=12,max_json_nodes=100000,
    max_capture_bytes=16*1024*1024,max_total_capture_bytes=128*1024*1024,
    max_candidates=128,max_body_bytes=131072)
ReceiptAudit(plan_digest: str, receipt_log_sha256: str,
    capture_digests: tuple[tuple[str,str],...], slot_count: int, receipt_count: int)
validate_study_receipts(plan,captures: Mapping[str,bytes],receipt_log:bytes,
    *,limits=DEFAULT_LIMITS) -> ReceiptAudit
receipt_audit_bytes(audit) -> bytes
receipt_audit_digest(audit) -> str
```

실제 source I/O가 있는 validate_study_plan을 순수 validator에서 호출하지 않는다. plan의 순수 구조/registry/program/protocol·capture prefix 재도출을 검사하며 실제 설치 source·rules/time·actual evaluator는 adapter/A0b가 담당한다. end:error가 온전하면 CAPTURE_ABORTED, 앞선 자료가 손상되면 손상 진단 우선. 당시 실패 응답/시각이 없으면 만들지 않는다. 원본 receipt.received_at와 각 후보 bar.received_at를 같은 시각으로 가정하지 않는다.

## 3. Store 담당 — pr4e_coordinator

```python
BundleRoots(sealed_root: Path, backup_root: Path)
BundleStoreLimits(format_limits: BundleLimits,object_limits: ObjectLimits,
    primary_budget: StoreBudget,backup_budget: StoreBudget,
    max_catalog_bytes: int,max_catalog_records: int)
# limits.policy_sha256: exact frozen policy digest; no path/authority grant.
BundleStore(*,roots: BundleRoots,limits: BundleStoreLimits,head_name: str)
store.head: BaselineHead
store.genesis_digest: str
store.provision_empty() -> None  # root/object/catalog only; NO head initialization
store.preview_payload(raw: bytes) -> PayloadReference | None  # None only empty
store.archive_raw(manifest: bytes,payloads: Mapping[str,bytes]) -> BundleReceipt
store.commit_verified(manifest: bytes,payloads: Mapping[str,bytes]) -> BundleReceipt
store.read_raw(digest: str,*,require_backup=True) -> StoredBundle
store.read_verified(digest: str,*,require_backup=True) -> StoredBundle
BundleReceipt(kind: str,bundle_digest: str,run_id: str,revision_id: str,
    attempt_id: str,backup_verified: bool)
StoredBundle(manifest_bytes: bytes,
    manifest: RawArchiveManifest|VerifiedBundleManifest,
    files: Mapping[str,bytes],backup_verified: bool)
```

StoredBundle.files는 immutable mapping snapshot이다. raw/verified별 parser/domain을 사용한다. partial-final 존재나 READY marker가 공개 기준이 아니며 PRIMARY_COMMITTED/BACKUP_VERIFIED catalog와 독립 head CAS/readback을 요구한다. commit_verified는 참조 raw를 읽고 validate_verified_inputs로 정확한 전체 입력을 확인한다. primary/backup 양쪽 쓰기 성공을 추측하지 않는다. 재시도는 동일 byte identity만 허용하고 같은 run/revision의 다른 bytes는 거절한다. backup 미완료는 성공 receipt를 반환하지 않으며 read(require_backup=False) 조사를 통해서만 미완료 상태를 볼 수 있다.

`provision_empty`는 head를 초기화하지 않는다. 별도 명시 operator utility에서 **사용자가** `store.head.initialize_reviewed_head(store.genesis_digest)`를 수행한다. runtime finalize/read에 초기화·reanchor·backup 자동 채택 caller를 두지 않는다. 테스트는 temporary roots와 실제 BaselineHead를 명시 provision한다. path/lock/head identity를 고정하고 동일 root나 포함/링크 관계를 거절한다. root 밖의 owner home에 접근하지 않는다.

## 4. Adapter/CLI担当 — notion_revision

새 `research_bundle.py`와 테스트. 입력 file의 안전한 bounded snapshot → RAW_ARCHIVED와 backup → receipt 검증과 actual A0b → 동일 입력에 연결된 VERIFIED_UNAPPROVED와 backup → sealed-only actual 재평가 순서다. 실패해도 원본을 남긴다. 읽을 수 없는/초과 file은 상태를 기록하고 complete로 가장하지 않는다. archive 전 source 의미 검사로 malformed 입력을 보관 대상에서 제외하지 않는다.

실제 plan/profile/registry/source digest·CandidateEvidence·평가 record는 실제 호출 결과로 구성한다. verified manifest의 평가 시각으로 재현하여 digest를 비교하지만 현재 승인 시각에 재사용하지 않는다. source 변경 시 옛 plan을 통과시키는 hash 우회나 보관한 source 코드 자동 실행은 없다. canonical envelope뿐 아니라 참조 원본 bytes 전체를 보관한다. 미구현 새 manifest 승인은 고정 미준비 상태다. 새 failure outcome 발급, WebAuthn, 정확 자동 복구, arm/orders는 포함하지 않는다.

owner utility의 구체 파일은 root와 write guard 합의로 확정하고 runtime provision과 분리한다. root가 registry/guard/통합 검증을 소유한다. 기존 carry/family 동결 트리는 변경하지 않는다.
