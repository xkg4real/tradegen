# TRADEGEN PR5 구현 준비 — 실제 계약과 보완안 대조

작성일: 2026-11-13. 계약 검토 소스: `/workspace/tradegen-universe-pr4e-1113`, `a772a24073ffb523ff7fa8d1e030398eaf56227a` (draft PR36). 이 문서는 동결된 소스를 읽고 작성한 구현 순서이며 실서명·실자료 검증 결과가 아니다. 이후 별도 worktree에서 A0a만 작성했고, 아래 마지막 절에 그 좁은 진행 상태를 구분했다. PR36 전체 검사는 root가 별도로 관리한다.

**지금 시작할 첫 단위 A0a는 ‘권한 없는 후보 outcome 문서 codec’이다.** stdlib만 사용하는 새 모듈로 분리하고 기존 고정 종목 평가·schema-1/2 서명·driver를 변경하지 않는다. 다음 A0b에서 전체 후보 입력을 먼저 검사하는 공용 검증기를 연결한다. universe 실패 outcome의 실제 발급, 새 bundle 승인, 기한에 따른 강제 매도를 없앤 운용 연결은 후속 단계다. 기존 승인 응답을 다시 포괄 확인받을 필요는 없다.

기준 문서:

- 원계획: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr5-study.md` (이하 원계획).
- 최신 보완안: `/workspace/outputs/TRADEGEN_PR5_REVIEW_AMENDMENT_2026-11-13.md` (개정 2).
- 최신 사용자 요구: 정상 호가·보유·실패 후보 보존, 원본/확정본 분리, 네 단계 복구, 패스키 승인 분리, 손상·재시작·기한만으로 매도 금지. 보유 기한 E는 새 관리 승인 요청으로 처리한다.

## 1. 원계획을 그대로 적용하면 생기는 충돌

| 원계획의 내용 | 실제 계약·최신 요구와의 차이 | 구현 방침 |
|---|---|---|
| `forward-universe-v1`은 마지막 슬롯에서 bid 전량 청산, terminal book이 없으면 실패 | 사용자 E 결정은 기한만으로 매도 금지. 현재 `driver.py:383`도 마지막 슬롯 target=0이며 `:477`은 terminal 잔량을 거부한다. PR4e의 갱신 안내만으로 이 동작이 바뀌지 않았다. | 과거 evaluator 의미를 같은 revision에서 바꾸지 않는다. 새로운 운용 정책·factory/evaluator revision과 검토 결합이 준비되기 전에는 보호 보유 운용으로 연결하지 않는다. |
| `_quiet` 예제가 `except Exception: return None`; `_replays`는 모든 `StrategyEvidenceError`를 경로 탈락으로 처리 | 정상 조회 실패, 잘못된 입력, 구현 버그가 같은 unavailable/탈락이 될 수 있다. 최신 요구는 이들을 구분한다. | 예상한 수집 실패와 의미상 평가 실패를 명시적 타입·고정 코드로만 처리한다. 형식·해시·인과성·등록 오류와 예상 못한 예외는 해당 연구 사용을 보류한다. |
| `_universe_inputs`가 모든 frame/decision을 먼저 검사 | 좋은 기반이지만 한 capture의 압축 필드 검사다. 모든 후보·원시 receipt·snapshot·파일 목록까지 검증됐다는 뜻은 아니다. | 이 선행 검사를 보존하고 공용 전체 후보 검증과 bundle 원본 대조로 확장한다. 앞 후보의 정당한 실패가 뒤 후보/프레임 손상을 숨기지 못하게 한다. |
| capture가 실패 경로를 더 이상 replay하지 않음 | 이미 실패한 모의 경로의 book 요청을 줄이는 것과 그 후보 증거를 삭제하는 것은 다르다. | 실패 위치·사유·원본 전체를 보존한다. 다른 경로와 원본 기록은 계속 검증한다. 기록이 중단된 capture를 완전한 평가 실패로 재분류하지 않는다. |
| `receipts.jsonl`은 uncapped, compact capture만 12 MiB 제한 | 묶음 전체 저장 한도·완전성·원본 승인·백업이 없다. 단순 nullable 필드만으로 timeout/실패 응답/누락을 구별할 수 없다. | 원본 receipt 기록을 명시적으로 형식화하고 streaming 검증·유한 저장 예산을 둔다. 저장 한도 때문에 정상 원본을 폐기하거나 unavailable로 바꾸지 않는다. |
| `prior_attempts`는 등록된 과거 study ID라고 설명하나 코드 예제는 형식/중복만 검사 | 실제 registry 포함 여부·동일 selection 계보·과거 실패 보존을 입증하지 않는다. 현재 후보는 strategy ID, 과거 시도는 study ID여서 두 식별자의 역할도 다르다. | 현재 후보 집합과 이전 시도 참조를 분리한다. 과거 등록·프로토콜·부모 bundle 연결을 검증하고 전체 시도 수 K를 유지한다. 임의 ID 문자열 목록을 입증된 과거 연구로 간주하지 않는다. |
| 승인 관련 파일은 원계획 변경 목록에 없음 | 현재 schema-2는 성공적으로 계산을 끝낸 전체 후보 hash만 연결한다. 새 실패 결과·전체 manifest·복구·패스키 승인 의미는 없다. | 공용 outcome/manifest 검증기와 명시적인 신규 승인 형식을 별도 단계로 구현한다. `audit_sha256`만 새로 채워 해결했다고 표시하지 않는다. |
| 기존 고정 경로와 digest가 유지된다고 설명 | 숫자 계산·직렬화 호환은 유지할 수 있다. 그러나 새 모듈/의존성 및 source closure 변화는 새 코드 해시다. | 기존 wire bytes와 결과 재현성을 회귀 검사하되, 변경 코드에 과거 코드 승인까지 유효하다고 주장하지 않는다. |

원계획의 3개 후보 상한, 최대 16개 필요한 book, lag-1/double-cost/lag-2별 실제 보유 추적, 인과적 결정, per-market 파서, 가격 없는 NAV의 임의 이월 금지는 유지할 수 있다. 577슬롯/48시간 크기 계산은 **원계획 인코더의 측정치**다. 원본 기록 형식·새 terminal 정책·인코더가 달라지면 다시 계산해야 하며 이번 검토에서 실행 확인한 수치가 아니다.

## 2. 현재 구현되어 있는 것과 미구현 부분

| 범위 | 기준 커밋에서 확인한 실제 상태 | 남은 작업 |
|---|---|---|
| universe program/chooser/protocol | `program.py`의 universe 선택기, `strategy.py:28`의 revision 상수와 `:146`의 protocol 허용은 존재 | 상수 존재가 evaluator 구현은 아니다. |
| universe evaluator | `strategy.py:433`의 `run_paper_validation`은 fixed revision만 허용. `:630` importer는 `registry/source_kind/bars/decisions` 고정 형식뿐 | universe archive decoder, 전체 검증, 경로 시뮬레이션, failure outcome, 신규 정책 평가가 미구현 |
| study freeze/capture/선발 | `study.py:59` source 목록, `:170` 단일 selection rule, `:195` MA warm-up, `:216` 현재 후보와 family 정확 일치 | universe study rule·3개 상한·program별 feasibility·prior attempts·공유 capture·크기 사전 검사가 미구현 |
| batch 파서·원본 보존 | `quotes.py`, `instrument_terms.py`에 원계획 batch 함수 없음. `universe.py:191/200`의 `FlagRead`/`TickerRead`에 raw Answer 없음 | per-market book/tick 파서와 고정된 원본/실패 기록 계약 필요 |
| 계산을 끝낸 탈락 후보 | `review_request.py:109`, `tests/launch_study_review.py:237/271`은 수치 탈락 후보를 family commitment에 포함 | 예외로 계산하지 못한 후보 outcome은 없음 |
| 평가 예외 | `study.py:589`은 예외 후보의 result/capture digest를 결과 맵에서 빼고, 후보가 하나라도 없으면 요청을 생성하지 않는다. `study_review.py:144`는 전체 평가 comprehension에서 예외 시 중단 | 두 경로가 동일한 공용 검증/평가 결과를 사용하도록 변경. 임의 지표 보충 금지 |
| 기존 서명 | `review_auth.py:148`은 현재 sealed owner context·현재 키·코드·날짜·유효기간과 실제 Ed25519 서명을 확인. `:212`는 실제 factory와 history callable을 대조 | 새 outcome/bundle 승인 및 새 factory 의미는 별도 변경 필요 |
| P0 저장 기반 | `evidence_objects.py`, `history_storage.py`, `live_history.py`의 v3 소형 참조·원본 보존이 존재 | 이는 live-history 저장 기능이다. PR5 sealed catalog·전체 manifest·백업·복구·승인이 구현된 것은 아님 |
| 보호 보유 | P1 순수 상태 모듈은 존재. P2 저장 작업은 별도 worktree/검증 범위 | 실제 계좌/주문 대조·관리 권한 issuer·신규 driver/evaluator 운용 연결은 별도다. caller의 모델 facts를 실제 승인으로 간주하지 않는다. |
| bundle·복구·패스키 | 보완안의 설계만 존재 | 신규 모듈, 독립 승인 체계, UI/알림, 실제 Windows/iPhone 수용 검사가 필요 |

현재 기능 여부는 소스에 근거한다. 문서 속 코드 블록, 기존 테스트 이름의 `failure`, draft PR 상태를 신규 기능 구현 완료의 증거로 사용하지 않는다.

## 3. 공용 검증기와 whole-family outcome 계약

공용 진입점은 편의상 `validate_and_evaluate_family`로 부른다. 새 함수명은 구현 시 정할 수 있으나, 아래 순서와 경계는 동일해야 한다. `study._select`와 `authenticate_study_selection`이 각자 다른 실패 분류를 갖지 않도록 한다.

1. **입력 집합 고정:** 검증된 plan의 현재 후보 study ID 집합과 입력 raw bytes 집합이 정확히 같아야 한다. 누락·추가·중복·다른 protocol·자료 교체를 거부한다. bytes 크기·후보 수·전체 작업량 한도를 먼저 적용한다. str을 허용하는 기존 경로는 기존 UTF-8 변환 의미를 유지하며 raw 해시를 다른 canonical JSON 해시로 대체하지 않는다.
2. **전체 입력 검증:** 모든 후보의 JSON 형식, 등록 chain/등록 시각, protocol, 전체 슬롯·프레임·결정·prefix, 규칙·시간·source-kind·완전성을 먼저 검사한다. 신규 bundle 경로에서는 모든 필수 파일·receipt·snapshot까지 대조한다. 여기서 하나라도 실패하면 발급된 family outcome도, 검토 요청도 없다.
3. **평가:** 검증된 입력에 대해서만 evaluator가 계산한다. 성공 계산과 수학적 탈락은 기존 실제 `ValidationResult`다. 허용된 universe 의미상 실패만 별도의 `tradegen-candidate-evaluation-failure/1` 결과로 발급한다. 공개 JSON parser만으로 평가가 수행됐다는 발급 상태를 얻을 수 없어야 한다.
4. **전체 결과 결합:** 각 후보의 raw capture SHA-256, protocol/registry/전체 inputs digest, evaluator revision, 실제 결과 또는 실패 outcome digest를 결합한다. 발생 slot·경로(benchmark/primary/double-cost/lag-2)·고정 사유도 실패에 포함한다. 결과 없음과 정상 실패를 구별한다. family 전체가 완성되기 전에는 일부 후보만 반환해 승인 요청을 만들지 않는다.
5. **선발:** 실제 계산 결과 중 적격 후보만 순위화한다. 수학적 탈락과 의미상 실패는 여전히 전체 family에 남는다. 벤치마크 평가 불가 또는 적격 후보 없음은 선발 없음이다. 결과 수·성공 후보 수로 K를 줄이지 않는다.

분류는 공용 validator/evaluator에서 정하고 CLI의 예외 문구 검색으로 추론하지 않는다.

| 분류 | 예시·요건 | 결과와 영향 |
|---|---|---|
| 온전한 `EVALUATED` | 전체 입력 검증과 실제 계산 완료. 수익/검정 기준 미달 포함 | 실제 숫자·p값을 보존. 수치 탈락도 family에서 제거하지 않음 |
| 정상 관측 실패 | 예정된 요청의 시간·대상·collector revision·고정 코드·응답 유무 및 가능한 raw receipt가 기록됨 | unavailable 입력으로 평가할 수 있음. 이 사실만으로 후보 전체 평가 실패나 서명 완료는 아님 |
| 온전한 `EVALUATION_FAILED` | 전체 입력 검증 이후, 해당 evaluator revision이 정의한 시장 사유로 계산 불가능 | 별도 실패 형식·도메인. 수익률/p값/성공 확률 없음, 선발 불가. 다른 후보는 계속 평가 가능 |
| 증거 손상/입증 불가 | 누락·잘림·중복 키·해시 불일치·잘못된 등록·결정 prefix·시각 역행 | 관련 연구 family 전체 보류. `EVALUATION_FAILED`로 포장하지 않음 |
| 중단/시스템 실패 | 기록 sink 중단, disk-full, 코드 예외, 지원 안 하는 revision, 자원 한도 초과 | 불완전 시도/운영 오류로 보존. 정상 시장 실패나 원본 손상이라고 단정하지 않음. 승인·선발 불가 |

원계획의 `HELD_COIN_VANISHED`, `MARK_UNAVAILABLE`, `BENCHMARK_UNAVAILABLE` 등은 **해당 검증된 revision의 명시적 실패 타입에서만** 후보 실패로 처리한다. 같은 코드 문자열을 임의 예외에 붙였다고 허용하지 않는다. `TERMINAL_BOOK_UNAVAILABLE`는 기존 청산 가정에 따른 실패다. 기한 매도를 하지 않는 새 revision에 그 이름과 의미를 자동 복사하지 않는다.

새 순수 outcome parser는 구조·무결성 검사만 한다. 실제 평가 발급·원본 출처 인증·서명·연구 선발·주문 권한을 제공하지 않는다. 기존 `_EVALUATED`의 실제 발급 결과 검사는 유지하고 실패 결과의 발급 경계는 별도로 둔다.

## 4. schema-2 및 새 bundle 승인 호환 경계

현재 strict 계약은 다음과 같다.

- `review_request.py:94`: family는 `plan_digest/members/family_sha256`, 각 member는 `study_id/capture_sha256/evidence_digest`만 허용한다. 정렬·고유성·1..128개 상한을 검사한다.
- `review_request.py:139`: 요청 schema 1 또는 2만 허용하며 schema 2의 추가 필드는 `family_commitment` 하나다. 숫자 요약은 실제 계산 후보의 필수 metrics를 요구한다.
- `review_auth.py:77`: 서명 body schema 1, purpose `strategy_source_and_fixed_implementation_review`. 실제 prospective·math 통과 후보만 대상으로 한다.
- `study_review.py:156/171`: 모든 rankable 후보의 검토가 필요하며, 각 서명은 재계산한 **전체** family와 같아야 한다. 탈락 후보마다 실행후보 검토 서명을 만드는 구조는 아니다.
- `tools/signer/sign.py:1072–1280`: 요청/서명 검증을 독립 복제한다. 앱 모듈 import로 대체하지 않는다. 신규 계약은 독립 signer와 canonical signing bytes parity를 함께 검증한다.

family member의 기존 `evidence_digest`는 해시 문자열이므로 새 failure hash를 담는 것 자체는 표현상 가능하다. 그러나 **해시를 담을 수 있다는 사실이 기존 승인 소비자가 새 의미를 검증한다는 뜻은 아니다.** 실패를 재계산할 수 없는 기존 verifier에 이를 넘기거나 기존 schema-2 서명을 새 bundle 승인으로 승격하지 않는다.

권장 연결 방식:

1. 기존 schema-1/2 요청과 서명 bytes/허용 필드/실패 동작을 그대로 유지한다. 기존 successful-result-only family의 digest 계산도 유지한다.
2. 신규 typed outcome 목록과 전체 파일 manifest는 별도 version/domain으로 정의한다. 새 bundle 승인에는 manifest canonical bytes의 digest와 기존 형태의 family commitment를 **둘 다** 명시적으로 결합한다. outcome 종류와 원본 파일 연결은 새 검증기가 해석한다.
3. 연구 보관/실패 검토와 적격 실행후보 검토의 purpose/scope를 구분한다. 실패 후보에 dummy 수치·`mathematical_criteria_met=True`를 넣거나 실패 후보를 실행 승인 대상으로 만들지 않는다.
4. manifest `files[]`는 원본·프로토콜·등록·전체 후보·결과·서명 대상 보고서의 닫힌 집합이다. manifest 자신, detached approval, 가변 catalog/incident 기록은 제외한다. detached approval이 manifest digest를 결합한다. 자기 해시 순환을 만들지 않는다.
5. 새 승인 형식의 parser/verifier/signer가 준비되기 전에는 새 bundle은 `VERIFIED_UNAPPROVED`까지만 가능하다. 기존 `audit_sha256`나 승인 boolean을 우회 통로로 쓰지 않는다.
6. 원본/현재 코드·규칙·소유자·만료·폐기·세션 조건을 사용 직전에 검사한다. exact recovery는 같은 증거를 복구할 뿐 승인 기간·신선도·arm 상태를 갱신하지 않는다.

`tradegen-research-bundle/1`의 연구 식별자/revision과 역사적 capture의 preregistered study ID는 별개다. 재계산으로 새 bundle ID를 부여하더라도 과거 등록·관측 bytes를 이름 변경 목적으로 수정하지 않는다.

## 5. 구현 순서와 완료 조건

| 순서 | 구현 단위 | 완료 조건·의존성 |
|---|---|---|
| A0a — 즉시 가능 | 새 무부작용 outcome 문서 codec와 현재 후보 집합 검증 | 아래 §6. 기존 runtime 파일 변경 없음. 문서 parse는 발급·선발·승인 아님 |
| A0b | 전체 후보 공용 검증 기반과 기존 fixed 경로 연결 | 아래 §7. 새 운영 입력 불필요. universe 미지원은 명시적으로 거부 |
| A1 | per-market 파서·원본 성공/실패 receipt 계약, snapshot 원본 결합 | 기존 단일 종목 live parser 동작 보존. malformed 한 종목과 응답 전체 손상을 구분. 네트워크 없이 합성 원본으로 검증 |
| A2 | universe 전체 decoder/평가 및 발급된 실패 outcome | 모든 후보·모든 후반 프레임 검증 후 의미상 실패 처리. 수익 계산 경로·비용·lag·benchmark 실제 재생. terminal 정책은 명시 revision으로 분리 |
| A3 | universe freeze/capture/CLI·prior attempts·수집 예산 | 3개 후보·필요 book 집합·재생기 공유·사전 크기 계산·실패/중단 보존. 이전 시도 등록과 계보 검증. 실제 public capture는 별도 운용 단계 |
| B1 | manifest codec, staging/sealed/catalog·전체 재검증·버전 백업 | 보완안 상태 전이와 모든 쓰기 경계 장애 검사. 기존 P0 객체 저장을 재사용해도 bundle transaction이 자동 완성되는 것은 아님 |
| B2 | 신규 bundle 승인 계약·독립 검증·선발기 연결 | 전체 files/family/outcomes가 승인에 결합. 기존 Ed25519 경로는 유지, 신규 형식의 독립 signer parity 필요. 패스키가 없어도 순수 계약·합성 서명 검증 가능 |
| B3 | 격리/정확 복구/새 버전 재구성/재관측/중단·의존 범위 보류 | exact bytes 및 현재 승인 조건 재검사. 같은 원본만 재서명 생략. 손상/복구만으로 주문하지 않음 |
| C1–C4 | WebAuthn 순수 계약 → 독립 bootstrap/authority ledger → HTTPS/Telegram UI → scope별 연결 | 보완안 A-1~A-4 순서. Telegram 클릭 자체는 승인 아님. 기존 root/실도메인은 미확인. 등록·실기기 검사는 운영 설정 후 |
| D — 병렬 의존 작업 | no-deadline-sale 운용 policy/factory/evaluator 및 독립 관리 권한 issuer | A0/A1/B1 순수 개발과 병렬 가능. 새 정책의 배포 적격 판정·live composition은 D 완료와 해당 신규 연구/소스 검토가 선행 |

순서상 A2의 원계획 v1 재생기는 과거 가정을 재현하는 연구 도구로 구현할 수 있으나 새 보호 보유 운용의 적격 근거로 자동 사용하지 않는다. 수집 book 집합은 evaluator 경로가 결정하므로, 새 정책을 목표로 하는 A3 실관측 계획은 그 evaluator 계약이 고정된 다음 freeze한다. 과거 v1 결과를 새 정책 통과 결과로 이름만 바꾸지 않는다.

## 6. 지금 구현할 첫 chunk — A0a의 구체 API

**소스 변경은 새 `execution_launch/research_outcomes.py` 한 파일, 검증은 새 `tests/launch_research_outcomes.py`로 제한한다.** `strategy`, `study`, `driver`, owner/signer/network/filesystem을 import하지 않는 stdlib 순수 모듈이다. 기존 runtime 호출부는 아직 이 모듈을 사용하지 않는다. 테스트 등록·기존 guard 확인은 root가 담당하고 부수 효과 허용 범위를 넓히지 않는다. 구현 worktree는 `/workspace/tradegen-research-outcomes-1113`, base `530af22`이며 이 문서의 원계약 대조 기준은 위 PR36 커밋이다.

제안 public API:

```python
@dataclass(frozen=True, kw_only=True)
class EvaluationFailureDetail:
    code: str
    slot_index: int
    phase: str  # benchmark | primary | double_cost | extra_bar_delay

@dataclass(frozen=True, kw_only=True)
class CandidateOutcomeDocument:
    schema_version: int  # exact int 1
    status: str          # EVALUATED | EVALUATION_FAILED
    study_id: str
    protocol_digest: str
    registry_digest: str
    capture_sha256: str  # claimed original-byte digest; completeness not verified
    inputs_digest: str
    evaluator_revision: str
    source_kind_claim: str
    evaluated_at: datetime
    result_digest: str | None
    failure: EvaluationFailureDetail | None

def parse_outcome_document(raw: bytes) -> CandidateOutcomeDocument: ...
def outcome_document_bytes(document: CandidateOutcomeDocument) -> bytes: ...
def outcome_document_digest(document: CandidateOutcomeDocument) -> str: ...
def validate_outcome_set(outcomes: tuple[CandidateOutcomeDocument, ...], *,
                         expected_study_ids: tuple[str, ...]) -> tuple[CandidateOutcomeDocument, ...]: ...
```

API의 정확한 의미:

- `EVALUATED`는 `result_digest`만 있고 `failure`는 None이다. `EVALUATION_FAILED`는 그 반대다. 원본 metrics를 새 형식에 복사하지 않는다. 이 문서가 수치 탈락인지 여부도 실제 결과를 다시 읽고 평가하는 후속 검증기만 판단한다.
- 실패 digest는 `tradegen-candidate-evaluation-failure/1` domain과 canonical document bytes로 계산한다. 계산 완료 문서에는 별도 `tradegen-candidate-evaluated-document/1` domain을 쓴다. **기존 ValidationResult의 `evidence_digest`는 바꾸지 않는다.** 새 wrapper digest와 기존 result digest를 혼동하지 않는다.
- 최초 실패 코드 allowlist는 원계획에서 정의한 네 가지 `STRATEGY_UNIVERSE_HELD_COIN_VANISHED`, `STRATEGY_UNIVERSE_MARK_UNAVAILABLE`, `STRATEGY_UNIVERSE_TERMINAL_BOOK_UNAVAILABLE`, `STRATEGY_UNIVERSE_BENCHMARK_UNAVAILABLE`의 **문서 표현**으로 제한한다. universe v1에만 허용하고 benchmark code/phase의 대응을 검사한다. terminal 코드는 기존 revision 의미 그대로이며 새 보호 보유 revision의 코드를 미리 만들어 적용하지 않는다. 지원 revision 이외의 실패 문서는 거부한다. 실제 v1 evaluator/failure issuer가 구현되었다는 뜻은 아니다.
- 성공 문서는 현재 알려진 fixed/universe revision 식별자만 허용한다. source-kind는 기존 세 가지 claim만 허용하되 진위를 인증하지 않는다. bool/int를 엄격히 구별하고 ID·하위 SHA-256·aware UTC 시각·유한 slot 범위를 검사한다. 20,000개 기존 슬롯 상한을 넘는 failure index는 거부한다.
- schema는 exact keys다. JSON은 UTF-8 bytes, 크기 상한(제안 64 KiB), 중복 키·NaN/무한대·과도한 중첩·알 수 없는 필드 거부, canonical UTC/JSON encoding을 고정한다. decoder 예외는 고정 코드로 정리하고 원문을 오류에 노출하지 않는다. encode/digest에서도 dataclass 전체를 다시 검사해 frozen 객체의 고의 변조를 탐지한다.
- `validate_outcome_set`은 정렬·고유한 예상 ID와 정확히 같은 현재 후보 집합인지 검사하고 결정적인 순서의 tuple을 반환한다. 최소 1개, 최대 기존 family 표현 한도 128개로 제한하며 universe freeze의 3개 상한은 후속 plan validator에서 별도로 검사한다. 누락·추가·중복 후보를 빼고 통과시키지 않는다.
- 이 API가 받는 예상 ID는 **호출자가 주장한 집합**이다. 실제 frozen plan·registry·prior attempts와의 일치 검사는 A0b/A2가 담당한다. A0a는 이전 시도 참조가 진짜라는 검증이나 새로운 family 승인 형식을 만들지 않는다.
- `Document`라는 이름을 유지한다. `ValidatedCandidateOutcome`, `IssuedFailure`, `ReviewReceipt`, `approved` 같은 인증 상태를 반환하지 않는다. 직접 구성·parse된 문서는 계산·출처 인증·선발·서명·권한으로 사용할 수 없다.

A0a의 의미 있는 수용 검사: 두 상태 각각의 canonical roundtrip/domain 분리; raw capture hash 변경; 실패 문서에 결과·metrics·승인 필드 혼입 거부; code/revision/phase 불일치; bool index/스키마·범위/중복 키/알 수 없는 필드/oversize/deep JSON; frozen 필드 변조 후 encode/digest 거부; 전체 후보 누락·추가·중복 거부; 동일한 예상 집합의 결정적 순서; 기존 `assess_strategy`가 문서를 실제 `ValidationResult`로 받아들이지 않음. 테스트는 합성 bytes·시각만 사용한다. 기존 evaluator 결과·v1/v2 signing bytes·terminal 동작에 대한 회귀는 변경되지 않았음을 확인하는 범위로 실행한다.

이 단계 완료 표시는 **‘후보 결과 문서 계약 구현’**으로 한정한다. whole-family 의미상 검증·실패 발급·선발·bundle·복구·패스키는 아직 완료가 아니다. 이는 새로운 대규모 설계 승인 없이 독립 branch/worktree에서 바로 구현 가능한 범위다.

## 7. 다음 chunk — A0b 공용 전체 검증 연결

**범위:** 기존 fixed 연구에서 전체 입력 선행 검사를 공용화하고, 향후 실패 outcome의 순수 형식을 준비한다. 파일 보관·승인 발급·driver 동작을 바꾸지 않는다.

예상 최소 파일:

- `execution_launch/strategy.py`: 현재 `evaluate_capture_json`의 strict decode와 전 기간 입력 검증을 재사용 가능한 내부 경계로 분리한다. `run_paper_validation`의 발급·실제 계산·result digest는 유지한다. 검증 토큰을 공개 JSON의 `validated=True`로 대체하지 않는다.
- 새 `execution_launch/study_evidence.py`(이름 제안): 명시적인 protocol tuple/raw capture mapping/rules/evaluation time을 받아 모든 후보를 먼저 검증한 다음 평가한다. `study.py`를 역으로 import하지 않아 순환 의존을 만들지 않는다. 입력을 받은 뒤 호출자가 바꾸지 못하도록 불변 bytes/정규화된 내부 값을 사용한다.
- `execution_launch/study.py`, `study_review.py`: 같은 공용 family 경로를 호출한다. unsigned 진단 보고서는 유지할 수 있지만 부분 결과로 review request를 만들 수 없게 한다. 기존 문서의 ‘평가 예외 후보도 이미 승인 가능’이라는 오해를 고친다.
- 신규 회귀와 기존 `launch_strategy`, `launch_study`, `launch_study_review`, `launch_review_request`, `launch_review_auth`, `compliance_signer` 회귀. registry/guard 변경과 전체 실행은 root가 관리한다. `study.py`의 CRLF를 유지한다.

A0b의 출력은 모든 정상 fixed 후보의 실제 `ValidationResult`와 정확한 원본 hash다. **현재 fixed evaluator의 임의 오류를 실패 outcome으로 발급하지 않는다.** universe 실제 입력 검증과 evaluator가 없는 상태에서 이를 구현된 실패 평가 경로라고 표시하지 않는다. 실패 JSON을 import해 발급된 결과·서명·선발로 사용하는 경로도 없다.

A0b의 완료 검사:

1. 기존 고정 capture의 결과/원본 hash/family commitment 및 schema-1/2 canonical signing bytes가 같음. 바뀐 source-code hash는 별개로 새 해시임을 확인.
2. 후보 하나의 마지막 프레임 손상, 다른 후보 누락/추가, 중복 키, 변경된 등록·prefix·시간을 공용 검증기 두 호출 경로가 동일하게 거부. 모든 입력 검사가 끝나기 전 평가 결과나 검토 요청을 외부에 공개하지 않음.
3. 수학적으로 탈락한 후보도 전체 family에 남고, raw bytes 공백 변경 역시 capture hash 변경으로 검출. 모든 후보 탈락 시 선발 없음.
4. 새 failure codec에서 미등록 코드·unknown/extra field·bool/int 혼동·NaN/무한대·형식 오류를 거부. 실패에 숫자 성과·승인 필드를 추가할 수 없음. 순수 parser 반환값이 기존 `assess_strategy`에서 실제 평가 결과로 통과하지 않음.
5. 예상하지 못한 평가 예외/자원 한도를 정상 unavailable로 바꾸지 않음. 합성 검증은 실자료 출처/수익 증명으로 보고하지 않음.
6. 공용 모듈을 실제 평가 경로에 넣으면 `CAPTURE_FILES`, driver source closure 및 독립 signer closure를 점검한다. 새 검증 의존성을 hash 목록 밖에 두지 않는다. 필요한 closure 증분을 양쪽에 동일하게 추가하고 변경 파일별 검출 회귀를 둔다. 기존 body/schema를 넓혀 승인 검사를 우회하지 않는다.

A0a/A0b는 사용자 PC 경로·키·floor-state 결과·Telegram token·운영 도메인 없이 가능하다. 원계획의 PR4e 병합 후 base 규칙은 실제 병합 전까지 상태를 정확히 표시한다. 개발이 필요하면 현재 동결 소스를 건드리지 않는 별도 worktree에서 진행하고 최종 검토 base는 병합된 upstream과 다시 대조한다.

## 8. driver terminal revision과 신뢰 의존성

현재 `FACTORY_ID`는 `tradegen-fixed-cash-trend-v1`이며 identity는 7필드다. `review_auth.py:90`, signer `:1072/:1264/:1333`이 이 factory를 고정한다. `driver.py:35`의 14개 source closure와 signer `:1283`의 독립 복제도 일치해야 한다. `history_storage_sha256`는 저장 정책만 결합하며 terminal 의미를 변경하지 않는다.

새 기한 정책에는 최소 다음이 필요하다.

- 기한·거래 활성화·감시·보호 매도·취소 권한의 별도 만료와 action policy가 protocol/driver identity/소스 검토에 결합되어야 한다. 기존 v1 의미를 덮어쓰지 않는다.
- 새 factory의 실제 callback과 history·account/order reconciliation·pending intent 경계, 그에 대응한 평가 revision이 검토돼야 한다. `P1 AuthorityFacts`나 `P2 LedgerReferences`는 외부에서 공급한 모델이며 그 자체로 독립 승인 issuer가 아니다.
- 새 승인 verifier/issuer와 평가·source review가 준비되기 전 새 protective live composition은 명시적으로 미준비 상태를 반환한다. 기존 terminal driver를 연결해 E가 구현됐다고 표시하지 않는다. 이 경계는 불필요한 시장가 매도나 권한 자동 연장으로 해결하지 않는다.
- terminal liquidation을 가정한 기존 `PaperMetrics.terminal_units='0'`, roundtrip 수, 수익률/비용/benchmark를 새 보유 정책의 결과로 재사용하지 않는다. 마지막 시점 잔량·mark·미실현 평가와 실현 결과를 새 계약에서 구분하고 정책 변경에 따른 실제 재평가를 수행한다.

PR5 연구 검토는 거래 활성화 승인이 아니다. 새 bundle 검토나 정확 복구가 기존 손실 하한·halt·한도 발효일·현재 owner/session 검사를 완화해서는 안 된다.

## 9. 후속 검증과 남은 운영 입력

후속 주요 회귀는 전체 후보 중 앞부분의 허용 실패와 뒷부분의 손상을 함께 넣은 경우, 정상 조회 실패와 원본 receipt 누락, benchmark 실패, lag-2에만 남은 보유 코인, 지연 매도 book 요청 유지, 전체 파일 변조·case 충돌·중복 경로·Windows ADS/reparse·hardlink, staging/catalog/backup 각 경계 crash·disk-full, exact recovery의 만료/폐기/코드 변경, 새 버전 승인 필요성, UI 표시 digest와 실제 승인 대상 일치를 포함한다.

기존 P0 또는 P2 모듈 통과를 PR5 bundle/복구 통과로 합산하지 않는다. Linux 합성 장애 테스트와 Windows ACL/디렉터리 게시/전원 장애, iPhone/Safari/Telegram 수용 검사는 별도 결과로 기록한다. 상위 저장 용량 초과 때문에 원본 quote를 `None`으로 바꾸는 회귀를 허용하지 않는다.

아직 실제 값이 필요한 항목은 비동기화 sealed 저장소/독립 버전 백업, 고정 HTTPS origin/RP ID, 소유자 독립 root·복구수단·범위별 만료 설정이다. 이런 값은 운영 설정·실등록 전에 확인하면 되며 A0 및 합성 검증을 막지 않는다. `floor_state_check`는 미실행 상태 그대로이며 PLB의 해당 실제 상태 분기에만 영향을 준다.

이번 산출물은 구현 착수 범위를 정한 문서다. 실자료 수집, 실제 서명, Telegram 발송, 실배포·무장·주문은 수행하지 않았다.

## 10. A0a 작성 체크포인트

root의 후속 개발 배정에 따라 `/workspace/tradegen-research-outcomes-1113`의 새 `execution_launch/research_outcomes.py`와 `tests/launch_research_outcomes.py`를 작성했다. 기존 평가·서명·driver 소스는 수정하지 않았다. source는 255줄, 테스트는 22개 함수이며 LF/AST 검사를 마쳤다. 독립 read-only 검토에서 고의 삭제된 frozen 필드의 예외를 고정 진단으로 바꾸고 JSON nesting 4/5 경계 검증을 보강했다. 검토자에게 추가 차단 지적은 없다.

현재 두 파일은 root 격리 실행을 위해 동결했다. 이 작성자는 runtime 테스트를 실행하지 않았으므로 아직 PASS 결과를 주장하지 않는다. A0a가 작성됐다는 사실은 A0b 전체 입력 검증, universe 평가/실패 발급, 새 bundle 승인, 복구 또는 패스키 구현 완료를 뜻하지 않는다.
