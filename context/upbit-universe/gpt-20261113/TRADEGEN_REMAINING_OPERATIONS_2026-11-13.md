# TRADEGEN 남은 운영 과업 — 2026-11-13 소스 대조

**지금 앱을 실행하는 것만으로 자동 실거래를 시작할 수는 없다.** 현재 운영 조립은 모의운영 전용이며, 첫 체결 이후의 보유 계좌 증거·위험 상태·주문 대조를 실제 운영 경로로 연결하는 작업이 남아 있다. API 설정이나 서명만 추가하면 끝나는 상태가 아니다. Windows PC 설치 상태, 실제 계좌 연결, 소유자 전자서명·활성화는 이번 작업에서 확인하지 않았다.

이 문서는 읽기 전용 소스 검토 결과다. 소스·테스트·실제 홈·키·계좌를 변경하거나 운영 명령을 실행하지 않았다. 금액과 개인 경로는 넣지 않았다.

## 1. 확인 기준과 상태 해석

- 최신 인계: `/workspace/tradegen-handoff-1113/CURRENT.md`, `updated_at: 2026-11-13T22:12:37+09:00`. PR36/37/38 병합 완료가 기록돼 있다. 뒤에 붙은 최신 체크포인트가 앞부분의 과거 “개발 중/검사 중” 문구를 대체한다.
- 병합된 최신 main 기록: `5217f1e7977fab170a5453ad1ac8d4fc58521dc6` — PR38 병합.
- 진행 중 carry 소스: `/workspace/tradegen-protective-carry-1113`, branch `gpt/protective-fixed-carry-v2`, base `59e15cb`. 신규 파일과 수정이 있는 미커밋 작업본이다. 이 트리는 PR38의 outcome codec을 아직 포함하지 않으므로, 해당 기능은 `/workspace/tradegen-research-outcomes-1113`의 `34b4a3b` 소스를 별도로 읽었다.
- carry 첫 개발 검사: **124개 = 113 PASS / 11 FAIL**, 28.14초. 담당 root 보고상 source fingerprint `06039df4`와 실제 홈 메타데이터가 전후 불변이었다. 실패 11개는 Coordinator 공통 fixture의 규칙 관측 시각이 검토 시각보다 미래라 `REVIEW_REQUEST_NOT_ELIGIBLE`가 발생한 사례이며 수정 중이다. 평가·전체 family·검토·캡처·드라이버·산술 검사가 통과한 사실을 통합 전체 완료로 확대하지 않는다.
- 이전 `TRADEGEN_LIVE_READINESS_GAPS_2026-11-13.md`와 PR5/P3 readiness는 출발점이다. 이 문서는 이후 완료된 저장·상태·모의운영 작업을 다시 미완료로 적지 않으며, 아직 구현 중인 carry를 병합 완료로 적지도 않는다.

## 2. PR34–38에서 완료된 것

아래 검사 수는 최신 인계에 보존된 각 작업의 결과다. 서로 겹치는 검사이므로 합산한 “전체 통과 수”를 만들지 않는다. NOT_RUN은 통과가 아니다.

| 작업 | 완료 범위 | 검증·병합 근거 | 완료로 보지 않는 범위 |
|---|---|---|---|
| PR34 | 정상 호가·보유·유니버스 자료를 보존하는 객체 저장, v3 참조 이력, 저장 정책 결합, 독립 head와 전체 재생 연결 | main `86c9e94`; 집중 213 PASS, 전체 2660 PASS / 0 FAIL / 135 NOT_RUN. 전체는 환경 재시작 후 같은 소스의 남은 검사를 재개해 registry를 대조한 결과 | 실계좌 보유 관리, Windows 전원 장애 내구성, 자동 복구 승인, 실거래 활성화 |
| PR35 | `protective_state.py` 순수 보호 상태·효과 의도. 오류·재시작·기한 자체를 SELL 원인으로 삼지 않음 | main `6030fe3`; 신규 24개와 기존 경계 검사를 합한 106 PASS | `AuthorityFacts`가 실제 승인이라는 의미, 주문 실행·원장 인증 |
| PR36 | 유니버스 Runner/Coordinator/owner **모의운영** 연결, 기존 저장·진입 검증·안내 연계 | main `dc34c1a`; 전체 2907개 중 2772 PASS / 0 FAIL / 135 NOT_RUN, 단일 프로세스 결과 | 실제 유니버스 연구 평가기·새 비청산 유니버스 정책·실거래 조립. 기존 universe-v1 종단 의미는 그대로 |
| PR37 | `protective_store.py` 상태와 outbox의 영속 결합, 독립 head, 잠금·중단·재생·전역 중복 방지; PR4e와 통합 | main `f41501f`; 저장 단위 178 PASS, 이후 통합 187 PASS / 0 FAIL / 0 NOT_RUN | 원래 P2 전체: 실제 startup 계좌·체결·미체결 대조, 현재 원장 인증, 주문 outbox 실행·재개 |
| PR38 | `research_outcomes.py`의 엄격한 후보 outcome 문서 codec. 성공 계산 문서와 평가 실패 문서를 표현·검사 | main `5217f1e`; 154 PASS / 0 FAIL / 1 Windows NOT_RUN | 실제 실패 평가 발급, 전체 입력의 의미 검증, 선발·서명 소비, 연구 봉인·백업·복구 |

주요 구분: PR38의 `EVALUATION_FAILED` JSON은 평가가 실제로 실행됐다는 증거가 아니다. PR37의 승인 요청 outbox는 사용자 승인도 아니다. PR34의 원본 객체 저장은 PR5의 서명된 연구 확정본·백업 시스템이 아니다.

## 3. 현재 carry-v2에서 진행한 범위

고정 종목 Upbit 원화 현물 GTC 경로를 먼저 연결했다. 유니버스 전체의 새 평가·운영 정책을 완성한 것은 아니다.

- `managed_behavior.py`, `driver.py`: 새 protocol/factory를 사용해 유효한 LONG, CASH/SELL, warm-up, unavailable을 구분한다. LONG의 비중 초과가 암묵적 매도로 바뀌지 않으며, 기한 E에는 이 초기 자동 전략 경로의 신규 후보 실행을 차단한다. 기존 별도 명시적 보호 취소/매도 경로에 새로운 권한을 부여하거나 그 기존 위험 검증을 없애지 않는다. 과거 fixed/universe-v1의 숫자·종단 의미는 별도 경로에 남긴다.
- `carry_evaluator.py`, `strategy.py`: 실제 새 평가 발급 경로와 FIFO 원가·모든 수수료·실현/미실현 손익·마지막 관측 평가잔량을 연결한다. 종단 평가액을 실제 매도나 실현 순이익으로 표시하지 않는다. 산술 모듈 단독 출력은 발급된 평가가 아니다.
- `capture_v2.py`, `paper_capture.py`, `workflow.py`: 실제 프로그램과 전체 prefix를 결합해 typed decision을 다시 계산한다. benchmark나 unavailable 표기로 잘못된 원본을 숨기는 경로를 거절한다.
- `review_request.py`, `review_auth.py`, `tools/signer/sign.py`: 새 결과·요약·factory/source closure를 구분해 검토한다. 과거 승인을 새 의미에 재사용하지 않는다.
- `live_history.py`, `coordinator.py`, `runner.py`: 원본 이력을 먼저 기록하고 현재 시각으로 P2 기한 요청을 확인한 뒤 Runner에 들어간다. callback 처리 중 E를 넘기는 경우도 신규 예약·전송 전 경계에서 다시 검사한다. 기한 저장 실패는 신규 의존 실행을 막으며 매도 원인이 아니다.
- P2 연결에서 `authority=None`, `observations=None`, 원장 참조는 모두 unknown으로 둔다. 실제 승인·원장 대조가 수행된 것처럼 채우지 않는다. 재전달은 같은 요청 ID를 읽고, 이미 종료된 관리 상태는 기록을 반복 추가하지 않는다.
- 합성 계좌·실제 임시 서명 검증·실제 발급 드라이버·LiveHistory·Controller/DryRunAdapter를 쓰는 통합 검사를 추가했다. 기존 GTC 주문의 뒤늦은 체결은 같은 주문 ID의 계좌 증거로 다루며, “새 create 없음”을 “E 이후 보유량 증가 불가능”으로 확대하지 않는다.

**현 상태는 통합 결함 수정 중이다.** 최종 동결 소스의 집중 회귀·기존 회귀, PR38 이후 main과의 통합·검증, 커밋/PR 정리가 남아 있다. 실제 transport 전송까지 원자적으로 보장하는 기한, 현재 관리 승인 발급자, 보유 계좌 운영 source는 이 단계에서 완료되지 않는다. `Coordinator`는 계속 rehearsal만 받고 carry `Runner`의 controlled 연결도 거절한다.

## 4. 실제 자동매매를 막는 운영 과업

| 우선 경계 | 현재 코드에서 확인한 사실 | 필요한 구현·검증 | 지금 사용자 입력 없이 진행할 수 있는 부분 |
|---|---|---|---|
| 보유 계좌 source와 완전성 발급 | `account_interval.py:upbit_interval_frame`은 보유 종목·새 체결이 있으면 `ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED`로 거절한다. `ContinuousUpbitCandidateSource.__call__`은 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`를 낸다 | 실제 가격·체결·수수료·입출금·공통 사건 순서·구간 마감·누락 여부를 입증하는 source 계약과 검증 어댑터. 잔고 스냅샷, heartbeat, 로컬 sequence, 임의 `complete=True`로 대체 금지 | 실제 API 문서와 보유 source 계약 대조, 명시적 실패/단절·재연결 fixture, 증명 가능한 항목과 입증 불가능한 항목 구분. 근거 없는 완전성 발급은 하지 않음 |
| continuous guard의 잠금·commit·publish 연결 | `plan_continuous_guard`와 `commit_continuous_guard`는 존재하지만 후보 근거의 진위를 발급하지 않는다. commit은 control journal transaction을 잡고, `Controller.observe`도 transaction 안에서 account provider를 호출한다 | 인증된 입력→동일 순서 잠금→guard/baseline/head commit→완료 확인 후 observation publish. provider 안에 commit을 단순 삽입하는 중첩 잠금 금지. 중단 시 신규 진입 차단·동일 거래 재개/격리 | source 인증 인터페이스·잠금/발행 경계·crash matrix를 별도 branch에서 구현·검증. 실제 source 없는 경로는 명시적으로 거절 |
| P2 전체 복구·보호 매도 운용 | 저장/outbox와 carry의 E 연결은 있으나 전체 startup 원장 대조가 아니다. P1 facts는 모델 입력이고 P2 원장 참조는 opaque 참조다 | 실제 계좌/미체결/체결·수수료/UNKNOWN/DISPATCHING 대조, pending intent와 실제 주문 연결, 재전송 방지, 유효한 전략·위험 원인과 별도 감소/취소 권한 검증. 부분 체결·최소금액 미만 잔량을 보유에 남김 | 실제 주문 없는 통합 fixture와 중단/재시작 검증. 오류·저장 장애·E를 청산 원인으로 쓰지 않음 |
| controlled launcher·planner·상시 관리 | `Coordinator.__init__`은 `mode == 'rehearsal'`만 허용한다. `tools/owner/rehearsal.py`는 정확한 `DryRunAdapter`를 만들며 `held_positions_supported=False`를 보고한다. 계획상의 `execution_launch/live.py`, `planner.py`, `standing.py`는 현재 없다 | 검토된 부품을 실제 운영 source·신선한 승인·계획/세션·현재 위험정책과 조립. source/guard/관리 권한 미준비 때 시작 거절. 앱 시작과 거래 활성화 분리 | 조립·준비도 검사·부작용 없는 시작 화면과 실패 경로 설계/개발. 모드 문자열 변경으로 실거래를 여는 방식 금지 |
| 전체 후보 연구·유니버스 평가 | 기존 fixed/carry는 실제 평가를 발급한다. PR38은 문서 codec만이며 universe-v1 실패 코드가 있다고 실제 universe evaluator가 생긴 것이 아니다 | 전체 후보 원본 선행 검증, 정상 조회 실패와 손상 구분, 발급된 실패 outcome, 이전 시도 계보, 다중검정 가족 유지, 새 비청산 유니버스 evaluator/revision | 다음 절의 A0b를 즉시 개발 가능. 실제 전향 관측 시간과 실자료 선발은 합성 검사로 대체하지 않음 |
| 연구 확정본·백업·4단계 복구 | live-history 객체 저장은 있으나 서명에 연결된 전체 연구 manifest와 확정본 catalog·복구 운용은 없다 | 작업본/확정본 분리, 임시 저장 후 전체 후보·파일·해시 검증, 별도 버전 백업. 정확한 원본 복구→새 버전 재구성→재관측→해당 연구 사용 중단. 정확 원본이라도 승인 만료/폐기 조건 재검사 | 봉인·검증·격리·복구 상태 및 fault 테스트. 실제 복구 신뢰 발급자가 없는데 자체 해시만으로 승인 복원을 주장하지 않음 |
| Telegram/WebAuthn 승인 UI·독립 신뢰 | 현재 확인한 launch/owner/core 경로에 요구한 패스키 승인 서버·등록·폐기·복구 UI는 없다. 기존 검토는 Ed25519 체계다 | Telegram 알림→HTTPS 승인 내용→WebAuthn UV→요청/대상/범위/기한 검증→별도 승인 증거 저장·적용. 일회성 challenge·origin/RP·재사용·중복/만료 검증. 기존 코드 승인 신뢰 경계와 전환 | mock 인증기·서버 계약·UI·음성 응답 없는 실패·replay 검증. Telegram 클릭이나 알림 성공을 서명으로 취급하지 않음 |
| PLB와 실제 기존 상태 | `tools/floor_state_check.py`는 S1~S12를 읽는 도구다. 사용자와 Claude 모두 실제 소유자 PC에서 미실행이라고 답했다 | 실제 기존 하한·halt·anchor·서명 상태에 의존하는 분기를 코드 결과로 결정. 기존 하한을 임의로 낮추거나 미실행을 성공으로 간주하지 않음 | 상태와 무관한 codec·계산·검증·CLI 준비는 계속 가능. 실제 상태 의존 분기는 결과가 필요해질 때만 보류 |
| 실제 배포·관측·최종 활성화 | 사용자 PC 설치·계좌 설정·현재 코드/한도/전략/활성화 서명과 실계좌 관측 연구 완료 근거가 없다 | Windows 잠금/전원 중단/재시작·시각·동기화 폴더 경계, iPhone 인증 수용, 실제 source 품질, 전향 연구, 코드·규칙/한도·연구·세션 활성화 범위별 승인 | 자동 검사와 설치/복구 절차 준비. 실제 환경 수용 검사를 Linux 합성 PASS로 보고하지 않음 |

현재 범위는 우선 Upbit 원화 현물이다. KIS·OKX 수집/다시장 검증은 CURRENT의 후속 ID에 남아 있으며, 조회·주문 부품이 존재한다는 이유로 다른 시장이나 파생상품까지 운영 가능하다고 보고하지 않는다. 최신 법규 재검토 ID `rules-review-1202`도 인계의 미완료 작업이다.

## 5. 다음 독립 개발 최소 단계 추천: PR5 A0b

**현재 carry 통합 수정·검증을 마친 뒤, 전체 후보의 입력을 먼저 검사하고 같은 평가 경로를 선발과 독립 재검토에서 함께 쓰게 하는 한 단위를 추천한다.** 부품만 더 만드는 단계가 아니라 실제 `study select → 실제 평가 → family commitment → 독립 재검토` 경로의 순서를 바로잡는 작업이다. 사용자 PC·키·서명·S1~S12·운영 도메인 없이 개발할 수 있다.

현재 근거:

- `study.py:_select`는 후보별로 읽고 곧바로 평가하며, 예외 후보는 진단에만 남긴다. 일부 결과만 있을 때 검토 요청을 만들지 않는 기존 보호는 유지해야 한다.
- `study_review.py:authenticate_study_selection`도 후보별 평가 comprehension을 사용한다. 전체 원본의 의미 검증이 끝나기 전에 앞 후보의 실제 평가가 실행될 수 있으며, 두 진입점의 실패 처리도 다르다.
- PR38 `research_outcomes.py`는 현재 `forward-paper-v1`/`forward-universe-v1` 문서만 받는다. carry 결과를 이 codec에 억지로 넣거나 revision 문자열을 바꿔 수용시키면 안 된다.

최소 구현 범위:

1. 신규 `study_evidence.py` 같은 공용 모듈에 후보 ID 정확 일치, 불변 raw bytes 스냅샷·개별/전체 크기, 등록·protocol·규칙·전체 슬롯/결정/prefix·시각·출처 종류의 선행 검증을 둔다. 전부 검사한 다음에만 기존 실제 evaluator를 호출한다.
2. legacy fixed는 기존 decoder/검증기를 재사용하고, carry-v2는 실제 `CaptureArchiveV2`와 프로그램 재도출 검증을 재사용한다. 공용 모듈이 임의로 typed decision을 만들거나 계산 실패를 unavailable로 바꾸지 않는다. 미구현 universe 평가 경로는 명시적으로 거절한다.
3. `study._select`와 `authenticate_study_selection`을 같은 공용 경로에 연결한다. 출력은 실제 발급된 `ValidationResult` 또는 `CarryValidationResult`와 정확한 원본 SHA-256이다. 수학적으로 탈락한 후보도 전체 family에서 제거하지 않는다.
4. 기존 review request schema 1/2와 carry schema 3/4의 의미·canonical signing bytes·요약 결합을 보존한다. source closure는 실제 새 의존성에 맞춰 driver와 독립 signer 양쪽을 함께 갱신한다. 변경 코드의 과거 승인 유효성을 주장하지 않는다.
5. **첫 A0b에는 새 실패 발급·bundle 승인·패스키를 끼워 넣지 않는다.** PR38 문서 codec의 carry revision 확장이 필요하면 실제 결과와의 대응을 정의한 별도 변경으로 한다. A0b가 완료돼도 전체 PR5가 끝난 것은 아니다.

필수 수용 검사:

- 뒤 후보의 마지막 프레임 손상·누락/추가 후보·등록 변경·중복 JSON 키가 있으면 어느 후보도 평가/검토 요청 발급 단계로 넘어가지 않는다.
- 선발 CLI와 독립 재검토가 같은 잘못된 family를 동일하게 거절한다. 일부 성공으로 나머지를 숨기지 않는다.
- 실제 계산된 탈락 후보·원본 raw bytes hash가 보존된다. 모든 후보 탈락이면 선발 없음이다.
- legacy 결과/서명 bytes와 carry 결과/domain·schema 3/4 바인딩이 유지된다. 모든 새 source 의존성의 변경을 승인 검증에서 검출한다.
- 임의 outcome JSON·수동 metrics·clone 결과가 실제 발급 평가로 통과하지 않는다. 예상 못한 산술/자원 오류는 정상 평가 실패로 분류하지 않는다.

현재 carry가 `strategy.py`, `study.py`, `study_review.py`, review/signature 경로를 수정 중이므로 같은 작업본을 동시에 편집하지 않는다. carry와 PR38을 반영한 확인된 기준점에서 별도 branch로 시작하고, 그 기준점의 정확한 새 schema와 테스트를 읽는다. 이 단계와 병렬로 보유 source의 증명 가능한 계약 분석은 진행할 수 있지만, 입증되지 않은 completeness 발급자를 먼저 만들어서는 안 된다.

## 6. 나중에 사용자에게 필요한 입력과 지금 묻지 않을 것

이미 확정된 E 비청산 결정과 손실 보호 정책은 다시 묻지 않는다. 현재 독립 개발은 다음 입력 때문에 멈출 이유가 없다.

- PLB의 실제 상태 분기에 도달하면 소유자 PC의 **S1~S12 결과 코드만** 필요하다. 금액·키·계좌번호·개인 경로를 공개 기록으로 받지 않는다.
- 확정본/백업을 배치할 때 실제 보관 위치와 독립 복구 수단을 확인한다. 승인 UI 배포 시 고정 HTTPS 도메인/RP ID와 최초 등록·기기 분실 복구 절차를 확정한다.
- 실제 계좌 연결은 사용자 로컬에서 API 권한·계정 일치·운영 설정을 확인한다. 채팅이나 공개 저장소에 키를 넣지 않는다.
- 최종 사용 전에는 실제 배포 코드, 규칙·한도, 실자료 전략 검토, 거래 세션 활성화를 해당 범위별로 확인한다. 연구 검토나 이번 개발 승인은 거래 활성화를 자동으로 포함하지 않는다.

## 7. 완료를 보고할 때 필요한 최종 증거

“앱 실행 후 자동매매 가능”이라는 설명에는 최소한 **검증된 보유 계좌 source → 인증된 위험 commit/publish → 실제 원장 대조가 연결된 보호 관리 → 현재 코드/전략/한도/세션 승인 → controlled launcher → 해당 Windows 환경의 시작·중단·재시작 수용 검사**가 함께 필요하다. 이 가운데 하나의 합성 검사나 저장소 병합만으로 전체를 완료 처리하지 않는다.

실제 전향 연구 결과와 수익 목표 달성은 소프트웨어 회귀 통과와 별개다. 현 단계에서 완료 시간을 보장하거나 실제 연구 수익·승인·활성화가 이미 존재한다고 보고할 근거는 없다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.

## 근거 파일

- 최신 상태: `/workspace/tradegen-handoff-1113/CURRENT.md`와 `LEDGER.md`.
- 운영 source: carry 작업본의 `execution_launch/account_interval.py:97`, `:353`, `:417`; `execution_accounts/continuous.py:118`, `:281`; `execution_accounts/baseline_bridge.py`.
- 위험 연결: `execution_launch/continuous_guard.py:174`, `:240`, `:316`; `continuous_guard_commit.py:314`; `execution_control/controller.py:457`.
- 실행 차단과 현재 연결: `execution_launch/coordinator.py:Coordinator.__init__`, `_management_deadline`, `_slot`; `runner.py:_controller_boundary`, `_carry_execution_time`; `tools/owner/rehearsal.py:379`, `:455`.
- P1/P2: `execution_launch/protective_state.py`, `protective_store.py`; 좁은 E 통합 검사는 `tests/launch_carry_coordinator.py`.
- 연구: `execution_launch/strategy.py:run_carry_validation/evaluate_capture_json`, `study.py:_select`, `study_review.py:authenticate_study_selection`, `capture_v2.py`, `review_request.py`, `review_auth.py`.
- PR38 문서 계약: `/workspace/tradegen-research-outcomes-1113/execution_launch/research_outcomes.py` — 모듈 상단의 비권한·비발급 경계 및 `_REVISIONS`.
- 소유자 상태: `tools/floor_state_check.py` — 도구의 존재는 실제 실행 결과가 아니다.
- 상세 계획: `/workspace/outputs/TRADEGEN_PR5_IMPLEMENTATION_READINESS_2026-11-13.md` §7, `TRADEGEN_PROTECTIVE_HOLD_IMPLEMENTATION_PLAN_2026-11-13.md` P2/P3/P4, `TRADEGEN_CARRY_V2_API_CARD_2026-11-13.md`.

함수명을 우선 근거로 사용한다. 진행 중 소스의 행 번호는 후속 수정으로 이동할 수 있다.
