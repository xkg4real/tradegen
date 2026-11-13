# PR5 A0b — 전체 후보 선행 검증 API

기준: carry `571e24d`, 별도 작업본 `/workspace/tradegen-research-family-1113`. 기존 carry 작업본은 동결 상태로 유지한다. 이 변경은 현재 plan의 **전체 원본을 먼저 검사한 뒤 기존 실제 평가기를 호출**하는 단위다. 새 실패 결과 발급, 과거 시도 계보, 확정본·복구, 승인 형식, 활성화, 주문은 포함하지 않는다.

## 1. 공용 계약

`execution_launch.study_evidence`의 공개 진입점:

```python
evaluate_study_family(protocols: tuple[ForwardProtocol, ...],
    captures: Mapping[str, str | bytes], rules: InstrumentRules, *,
    registry: tuple[Registration, ...], now: datetime,
    limits: FamilyEvidenceLimits = DEFAULT_LIMITS) -> FamilyEvaluation
```

- 호출자는 먼저 `validate_study_plan(plan)`을 실행한다. 공용 함수는 plan/study를 import하지 않고 protocol·현재 후보 family·registry를 다시 검사한다.
- 캡처 key는 protocol의 고유 study ID 집합과 정확히 같아야 한다. strategy ID 집합은 각 protocol의 family_members와 정확히 같아야 한다. 현재 후보 집합 검증이 과거 시도의 누락 검증을 대신하지 않는다.
- mapping은 한 번 스냅샷하고, 각 값은 정확한 bytes 또는 str만 받는다. str은 기존 UTF-8 의미로 고정한다. 원본 공백·키 순서·개행을 canonicalize하지 않는다. SHA-256은 이 raw bytes의 해시다.
- 기본 admission 한도: 후보 128, 개별 raw 16 MiB, 전체 raw 128 MiB, 기존 bootstrap work 식의 합 40,000,000. 유한 admission 제한이며 연구 수치·유의수준·K를 변경하지 않는다. `FamilyEvidenceLimits`는 exact int 양수이며 기본값 이하의 제한만 허용한다. CLI도 동일한 기본 한도를 사용한다.
- 기존 protocol의 family ID 상한 1,000은 변경하지 않는다. 공용 호출의 128은 실제 평가 발급 registry 용량에서 온 별도 상한이다. 전체 128 MiB와 40M은 이번에 새로 정한 운영 admission 정책으로, 최대 크기 capture 8개 및 기존 후보별 최대 bootstrap work 4회에 해당한다. 지원을 약속한 통계 임계를 낮추는 것이 아니며, 초과하면 원본을 그대로 두고 `STUDY_EVIDENCE_RESOURCE_LIMIT`으로 전체 호출을 보류한다. 이 상한은 Python RSS나 실제 소요시간 보장값이 아니다.
- phase 1: 집합·크기·작업량, 모든 protocol/registry, 각 archive의 전체 형식·등록·규칙·시각·슬롯·prefix·완전성 검사. 모든 archive의 등록 chain digest는 plan.registry와 같아야 한다. carry는 기존 V2 프로그램/typed decision 전체 재도출을 재사용한다. universe는 지원하지 않으므로 명시 거절한다.
- phase 2: phase 1이 전부 성공한 뒤에만 스냅샷 bytes로 기존 `evaluate_capture_json`을 순서대로 호출한다. 실제 평가기는 입력을 다시 검증한다. 공개 `validated=True`, parser 발급 권한, 임의 결과/지표 입력은 없다.
- 전체 평가가 성공해야 `FamilyEvaluation`을 반환한다. 이후 평가 중단이 발생하면 일부 실제 계산이 내부 등록됐을 수 있으나 부분 family/result는 반환하지 않고 승인 요청도 생성하지 않는다. 내부 발급 registry를 지우거나 기존 발급을 폐기하는 rollback은 하지 않는다.
- 전체 입력 검사 후 현재 실제 `_EVALUATED` 잔량을 `strategy.require_evaluation_capacity(count)`로 먼저 확인한다. 부족하면 첫 평가 전 같은 RESOURCE_LIMIT으로 보류한다. 이는 동기 호출의 사전 검사이며 다른 thread의 임의 동시 발급까지 예약하는 잠금 계약은 아니다. 각 실제 발급의 기존 한도 검사도 유지한다.

반환값은 frozen `FamilyEvaluation(rows: tuple[EvaluatedCandidate, ...])`이며 각 row는 `study_id`, `raw_capture: bytes`, `capture_sha256`, 실제 발급 `result`를 가진다. `results`와 `capture_digests` 속성은 각각 새 dict를 반환한다. 결과는 legacy `ValidationResult` 또는 실제 `CarryValidationResult`다. 수학적으로 탈락한 후보도 row와 원본을 그대로 포함한다. 객체를 직접 생성해도 평가 발급·승인·선발 권한이 생기지 않는다.

## 2. 입력 검사 분리

`strategy.validate_capture_json(protocol, raw, rules, *, now, expected_registry_digest=None) -> None`를 추가한다. 기존 legacy decoder를 재사용 가능한 내부 함수로 추출하고, `run_paper_validation`/`run_carry_validation`의 산술 직전 입력 검사도 각각 내부 함수로 추출한다. 검증 전용 경로는 simulator, bootstrap, `_EVALUATED`를 호출/변경하지 않는다. expected registry digest는 caller의 plan 일치 조건이지 등록 출처 인증이 아니다.

`evaluate_capture_json` 및 두 실제 run 함수는 동일한 검증 함수를 사용하되 기존 산술·발급·result digest를 유지한다. legacy capture·request 1/2·서명 bytes와 carry result/domain·request 3/4·summary binding을 변경하지 않는다. source code 해시 변경은 새 코드다.

## 3. 예외와 소비자

- `StudyEvidenceError(ValueError)`는 집합/한도/스냅샷 등의 공용 고정 진단이다. `STRATEGY_*` 입력 오류는 기존 `StrategyEvidenceError`를 그대로 전파한다. 정상 시장 실패 outcome을 새로 만들지 않는다.
- 예상 못한 계산·시스템 예외는 평가 중단으로 전파하고, 기존 CLI 바깥 경계가 고정 일반 오류로 표시한다. `except Exception -> unavailable` 또는 일부 후보 삭제는 금지한다.
- `study._select`는 공용 loader로 모든 원본을 읽고 공용 함수 한 번을 호출한 뒤 기존 ranking/family/request 로직을 수행한다. 원본 누락/손상 시 이전의 앞 후보 EVALUATED 진단을 내지 않고 전체 작업을 거절한다. 이때 workflow_complete/승인 준비 상태는 거짓이다.
- `study_review.authenticate_study_selection`도 같은 공용 함수를 사용한다. 전체 입력 검사 전 실제 평가·서명 검증은 0회다. 현재 owner/key/code/clock/만료·전체 eligible 서명 검증은 그대로 유지한다.
- `study.load_capture_family(plan, directory) -> dict[str, bytes]`를 두 CLI가 공유한다. 추가/누락 `*.capture.json` 파일은 거절하고 receipts.jsonl/보고서는 후보로 세지 않는다. 명시 경로의 기존 `_read_file` 검증과 한도를 유지하고 후보 파일을 삭제·수정하지 않는다. 디렉터리 검사 성공 자체가 서명된 sealed snapshot이라는 주장은 하지 않는다.

## 4. 파일 소유와 검증

| 담당 | 소유 파일 |
|---|---|
| revision_review | 새 `study_evidence.py`, `strategy.py`, 새 `tests/launch_study_evidence.py` |
| notion_revision | `study.py`(CRLF 유지), 공유 CLI loader, `tests/launch_study.py` 관련 회귀 |
| pr4e_owner | `study_review.py`, `tests/launch_study_review.py`와 필요한 실제 임시 서명 회귀 |
| root | registry/guards, source closure 최종 일치, 최종 실행·커밋 |

필수 회귀: 뒤 후보 마지막 프레임/등록/prefix/중복 키 손상이 앞 평가 발급을 막음; 누락·추가·집합 변조; 개별/전체 bytes 및 work 한도 경계; caller mapping 변경에도 검사·평가 raw 동일; 정상 계산된 탈락 후보 원본 포함; raw 공백 hash 보존; legacy/carry 실제 결과 digest parity; 알려지지 않은 evaluator와 실패 JSON 거절; 두 진입점 같은 거절; 실제 임시 서명으로 정상 family 재검토 성공 및 원본 변경 거절. 함수 monkeypatch는 호출 수/장애 주입에만 사용하고 성공한 평가·승인을 임의 True로 대체하지 않는다.

source closure는 최종 import graph에 맞춰 검사한다. 새 helper를 사용하는 study manifest는 포함시켜야 한다. driver와 독립 signer는 실제 전이 의존성에 새 파일이 생기는 경우 둘 다 정확히 추가한다. 선언만으로 사용하지 않는 파일까지 driver의 필수 의존성이라고 보고하지 않는다.
