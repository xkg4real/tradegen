# PR5 B1b-2a API 및 파일 소유 계약

작성: 2026-11-13. 부모가 승인한 B1b-2의 첫 구현 단계다. **새 전용 작업 트리가 지정될 때까지 현재 B1b-1 트리의 runtime/tests는 수정하지 않는다.** B1b-2b/c의 sealed A0b 선발·실행기 연결은 이 단계 통과 후 진행한다.

목표는 제한 전용 signed owner event, 같은 Context에 봉인한 철회 집합, 기존 모든 source/implementation authentication 경로의 실제 소비다. archive 신원 확인·문서 철회·현재 연구 사용·거래 활성화의 범위를 합치지 않는다.

## 1. 소유권

| 담당 | 단독 소유 |
|---|---|
| `pr4e_coordinator` | 새 `execution_launch/research_revocation.py`, 새 `tests/launch_research_revocation.py`, 이 API 카드 |
| `revision_review` | `tools/signer/sign.py`, `tests/compliance_signer.py`의 새 사건/독립 codec/명령 검사 |
| `pr4e_owner` | `core/compliance/owner.py`, `core/compliance/model.py`, 필요시 `execution_control/owner_authority.py`, 새 `tests/compliance_research_revocation.py` |
| `notion_revision` | `execution_launch/review_auth.py`, `execution_launch/bundle_auth.py`, 새 `tests/launch_research_revocation_auth.py`; 기존 consumer tests 변경은 담당자에게 알림 |
| 부모 `/root` | registries, write guards, 통합 launcher/검증, 최종 문서/commit |

`protective_hold_design`은 별도 트리의 B2a 담당이다. 이 단계 파일을 중복 수정하지 않는다. 기존 CRLF 파일은 CRLF를 보존한다.

## 2. 고정 event와 식별 규칙

```python
EVENT_KIND = 'research_attestation_revoked'
TARGET_DOMAIN = b'tradegen-research-attestation-revocation-target/1\n'
PURPOSES = frozenset({
    'research_archive_manifest_attestation',
    'strategy_source_and_fixed_implementation_review',
    'strategy_source_and_fixed_carry_implementation_review',
})
REASON_CODES = frozenset({'OWNER_WITHDRAWN', 'EVIDENCE_UNTRUSTED', 'REVIEW_ERROR'})

# exact data keys; no unknown field, bool, uppercase/short hash, empty text
data = {
    'purpose': '<one PURPOSES value>',
    'target_sha256': '<64 lowercase hex>',
    'reason_code': '<one REASON_CODES value>',
}
```

target은 `SHA256(TARGET_DOMAIN + actual_existing_signing_bytes(parsed_body))`다. archive는 `bundle_attestation.attestation_signing_bytes`, source/carry는 `review_auth.review_signing_bytes`의 기존 domain과 canonical body를 사용한다. **raw document bytes SHA, signature bytes SHA, unsigned request SHA로 대신하지 않는다.**

동일 signed body를 JSON 공백/키 순서만 바꾼 source envelope는 같은 target이다. purpose, body, owner fingerprint, 유효기간 또는 실제 signing domain이 다르면 다른 target이다. invalid JSON/서명 envelope 형식은 거절하지만 여기서 서명의 암호학적 유효성이나 키의 신뢰를 발급하지 않는다. 현재 소유자가 과거/만료/잘못된 서명 표현의 동일 body를 제한할 수 있다는 사실과 그 문서의 현재 승인 여부는 별개다.

archive의 기존 `attestation_document_digest`는 exact file 식별로 유지한다. 이를 새 target과 같은 값이라고 표시하지 않는다. source request schemas 1/2, carry 3/4, body 1/2를 기존 strict parser 그대로 수용한다. legacy universe source review도 기존 purpose로 제한되지만 새 universe sealed 선발 지원을 뜻하지 않는다.

## 3. Pure codec API — pr4e_coordinator

```python
class ResearchRevocationError(ValueError): ...

def revocation_target(document: bytes, *, purpose: str) -> str: ...

def validate_revocation_data(value: dict) -> dict:
    # Strict exact schema; returns a detached dict, no authority.
    ...

def validate_revoked_targets(value) -> frozenset[tuple[str, str]]:
    # Requires exact frozenset, exact 2-tuple rows, exact purpose/hash strings.
    # No list/dict coercion or caller-owned mutable view.
    ...

def target_is_revoked(revoked_targets, *, purpose: str, target_sha256: str) -> bool:
    # Pure membership after strict validation; never loads or authenticates state.
    ...
```

진단은 `RESEARCH_REVOCATION_DOCUMENT_INVALID`, `RESEARCH_REVOCATION_PURPOSE_INVALID`, `RESEARCH_REVOCATION_DATA_INVALID`, `RESEARCH_REVOCATION_STATE_INVALID`의 네 종류로 고정한다. 외부 parser exception/path/body를 포함하지 않는다. `target_sha256`의 단독 타입 오류는 DATA_INVALID다.

순환 import 방지: module top level은 stdlib만 import한다. `revocation_target` 호출 안에서 해당 기존 parser/signing function을 local import한다. `review_auth._authenticate`는 새 helper를 top-level import해도 된다. helper가 호출하는 것은 parse/signing-bytes이며 `_authenticate`를 재호출하지 않는다. owner/model은 execution_launch를 import하지 않고 동일 작은 enum/schema를 독립 유지한다.

파일/clock/key/owner/store/network I/O, 결과 issuance, 승인 flag는 없다. 기존 document 크기 제한과 strict parser를 그대로 사용한다. 입력은 exact bytes이며 source parser가 허용하는 표현 차이만 target으로 정규화한다. signed bytes를 새 purpose로 재해석하지 않는다.

## 4. Owner/model/current provider — pr4e_owner

- `OWNER_KINDS`와 `_DATA`에 새 signed event를 추가한다. `SYSTEM_KINDS`에는 넣지 않는다. signature·rotation·anchor 검사는 기존 전체 owner log 경로를 그대로 따른다.
- `OwnerState` 마지막에 `revoked_research_attestations: frozenset = frozenset()`을 추가한다. 값은 `(purpose, target_sha256)` pair 집합이다. reason은 감사 원본 행에 남고 제한 집합에는 필요하지 않다.
- `_owner_fold`가 정상 verify_log의 모든 해당 사건을 모은다. 미래 UTC도 즉시 제한하며 일반 future skip 전에 처리한다. `_up_to`의 code/table 승인 시점 로직은 바꾸지 않는다. duplicate는 set union; unrevocation/expiry/reset 이벤트는 없다.
- 같은 실제 loader 호출이 만든 Context 안에서 head와 철회 집합을 함께 봉인한다. 별도 blacklist 읽기나 두 번째 owner log의 set을 앞선 Context에 합치는 방식은 금지한다.
- Context hash 호환: **빈 새 집합은 기존 owner-field 직렬화에서 생략하여 기존 context_hash를 유지**한다. nonempty 집합은 deterministic sorted pairs로 hash에 포함한다. 수정은 hash projection에 국한하며 원본 event bytes를 바꾸지 않는다. consumer는 exact frozenset/pair 타입도 별도 검사한다.
- 실제 CurrentOwnerAuthority의 original observed_at, 전체 D14 current code/key, head growth/rollback latch는 유지한다. provider 반환 타입/시그니처를 늘리지 않아도 Context로 전달된다. 반환된 별도 revocation bool은 만들지 않는다.
- owner 상태 BROKEN, malformed field, missing current context는 미철회로 처리하지 않는다. 현재 owner schema를 모르는 구버전이 새 사건을 거절하는 것은 fail-closed 동작이다.

## 5. 독립 signer — revision_review

독립 상수/schema/target 구현은 앱 모듈을 import하지 않는다. 기존 `_ba_*` archive 및 `_rv_*` source strict codec/signing-bytes를 재사용하고 app와 golden vectors를 대조한다.

권장 명령은 다음으로 고정한다.

```text
sign.py research-revoke --repo <DEPLOYMENT> --document <DETACHED_DOCUMENT.json>
    --purpose <EXACT_PURPOSE> --reason-code <EXACT_REASON> [--key <OWNER_KEY>]
```

문서 전체 bounded read와 실제 snapshot identity → 독립 target 산출 → 목적·target·reason 및 "현재 승인 사용만 제한, 원본 삭제/거래/청산 아님" 표시 → 기존 직접 확인·key unlock → 현재 PEM/key/전체 signed owner chain 및 입력 재검사 → 기존 owner log에 한 행 append 순서다. 현재 코드 승인이나 trading table이 없다는 이유로 **제한 사건을 자동 승인/재활성화로 바꾸지 않는다**. 제한 사건은 새 사용 허가를 만들지 않는다.

명령은 `target_sha256` 사용자 인자를 받지 않는다. generic `event` parser choices에서 새 event를 제외하고 `_cmd_event` 직접 우회도 거절한다. 실제 event 형식 자체는 owner parser가 정상 읽어야 하므로 SCHEMAS에는 포함한다.

기존 `_commit` write 경로를 재사용하고 새 event의 under-lock 경로에서 전체 owner signatures를 실제 검증한다. head hash만 같고 과거 sig bytes가 손상된 경우에도 append하지 않는다. 기존 lock/head CAS·fsync·현재 key·단조 timestamp 원칙은 유지한다. 새 append 호출/정확 write shape가 필요해지면 부모에게 먼저 알린다. 입력 문서가 확인 뒤 바뀌면 거절한다. 실제 소유자 자료나 실제 키로 명령을 실행하지 않는다.

## 6. Consumers — notion_revision

### Source/implementation: 공통 `_authenticate`

현재 actual authority/context seal/hash/key/code·source signature 검사를 보존하고, 같은 Context의 `owner.revoked_research_attestations`를 strict 검증한다. 문서 purpose와 `revocation_target`을 계산해 membership을 검사한다.

- 철회됨: `ReviewAuthenticationError('REVIEW_ATTESTATION_REVOKED')`.
- malformed revocation state: `ReviewAuthenticationError('REVIEW_REVOCATION_STATE_INVALID')`.
- helper 문서 오류: 기존 strict parser의 거절을 유지하고 불필요한 raw error를 노출하지 않는다.

한 공통 `_authenticate`에 연결하여 `verify_source_review`, `verify_implementation_review`, `ReviewVerifiers.source`, `.implementation`, `.authenticated_body`, `.assess_bundle`, `study_review`가 모두 소비한다. 해당 후보를 조용히 빼고 다른 후보를 선발하는 처리로 바꾸지 않는다. 순수 parse/codec은 철회 사실을 읽지 않는다.

### Archive identity

`bundle_auth`는 actual owner/graph 확인을 계속 수행한다. **서명의 보관 신원은 유지하되 revoked 상태를 숨기지 않는다.** 기존 `ArchiveAttestationAssessment`의 `revocation_status`는 성공 관찰에 한해 `REVOKED` 또는 `NOT_REVOKED_AT_HEAD`를 반환하고, `revocation_target_sha256: str | None = None`, `revocation_owner_head: tuple[int,str] | None = None`를 끝에 추가한다. 메타데이터는 final actual authority에서만 도출한다. 직접 생성한 assessment는 여전히 권한이 아니다.

최초·중간·최종 actual Context의 집합을 검증하고 마지막 동일 target 상태를 반환한다. benign growth 중 새 철회가 생기면 전체 archive identity를 거래 허가로 오해하게 실패/성공 bool로 압축하지 말고 final status=REVOKED를 보여준다. head rollback/키·코드 변경/expiry/변조는 기존대로 거절한다. malformed set은 `ARCHIVE_AUTH_REVOCATION_STATE_INVALID`로 거절한다.

archive output에서 미지원이라고 남기는 것은 `current_operational_use`, automatic recovery, source/selection/activation, signature backup이다. **개별 철회 지원 후에도 기존 `current_use_eligible=False`, `execution_ready=False`, `automatic_recovery_supported=False`는 그대로다.** reasons의 `ARCHIVE_AUTH_INDIVIDUAL_REVOCATION_UNSUPPORTED`는 성공 관찰에서 제거하고 `ARCHIVE_AUTH_ATTESTATION_REVOKED` 또는 `ARCHIVE_AUTH_NOT_REVOKED_AT_VERIFIED_HEAD`로 교체한다. 검증 시각·head의 한 번 관찰이며 미래 유효성 token이 아님을 문서에 명시한다.

## 7. 단계 완료 검증

- app/signer target golden: archive, legacy source schemas 1/2, carry 3/4; source JSON 공백/순서 변경은 같은 target; domain/purpose/body 변경은 거절 또는 다른 target.
- actual signed temporary owner log: 기본·중복·미래 UTC 철회, 다른 target 정상, wrong key/domain/signature, rotations, original head rollback, 재시작. 실제 owner load_context를 사용한다.
- 기본 빈 집합 context_hash는 새 필드가 없던 projection과 같고 nonempty는 달라야 한다. seal을 유지한 field mutation이나 mutable type 치환은 consumer가 거절해야 한다.
- 모든 source/implementation 공개 경로 및 authenticated_body/assess_bundle가 동일 철회를 거절한다. cached ReviewBundle/report, copied Context/callback은 새 허가 입력이 되지 않는다.
- actual archive store/backup/서명/owner chain으로 NOT_REVOKED_AT_HEAD와 REVOKED 표시를 검증한다. 폐기됐어도 원본 bytes는 보존되고 source/selection/execution flags는 false다. final owner observation에 새 철회를 주입한다.
- actual signer command는 독립 codec과 실제 임시 Ed25519 append를 사용한다. 확인 뒤 파일/key/head 교체, 앞선 log signature 손상, generic-event 우회를 거절한다.
- 기존 한도·손실 하한·halt·code approval 미래 시점·독립 head/owner write guards가 유지돼야 한다. 관련 source/owner/review/strategy tests는 부모가 통합 실행한다.

19 KEYLESS, isolated temporary homes/keys, no API/arm/order. source-level/fake-Windows/native-Windows 범위를 구분한다. 새 기능 검증과 기존 B1b-1 검증 수를 합쳐 중복을 숨기지 않는다. 2a 완료가 sealed selection 또는 exact recovery 완료를 뜻하지 않는다.
