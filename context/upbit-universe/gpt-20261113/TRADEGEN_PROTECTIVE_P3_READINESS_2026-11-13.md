# TRADEGEN P3 준비: 기한 비청산의 새 행동 버전과 운영 차단 경계

작성: 2026-11-13. 읽기 전용 대조 기준: PR4e 작업 트리 `/workspace/tradegen-universe-pr4e-1113`, HEAD `a772a24073ffb523ff7fa8d1e030398eaf56227a`, 확인 시 작업 트리 clean. 이 문서를 위해 운영 코드·테스트·승인·키·실제 홈을 수정하거나 실행하지 않았다. 전체 회귀가 진행되는 소스는 그대로 유지했다.

참조: `TRADEGEN_PROTECTIVE_HOLD_IMPLEMENTATION_PLAN_2026-11-13.md`의 P3a/P3b, 최신 PR4D/PR5 개정안, handoff AGENTS, P1 순수 상태 모듈과 별도 P2 저장 모듈. P1은 구현된 모델이며 P2 개발 검증은 별도 기록이다. **이 문서는 P3 구현 완료나 운용 가능 판정이 아니다.**

병렬 PR5 준비와의 연결은 `TRADEGEN_PR5_IMPLEMENTATION_READINESS_2026-11-13.md` §8을 따른다. 독립 outcome 문서 codec의 구현은 실제 outcome 발급·전략 합격·승인·운용 연결이 아니며, 기존 연구 결과를 새 carry 행동의 근거로 재사용하지 않는다.

완료 범위 표기는 `protective-hold/p2-store`로 한정한다. 원래 P2 계획의 Coordinator bootstrap 연결, 실제 계좌·fills·수수료·미체결 대조, 그 결과에 따른 복구 전이는 `protective-hold/p2-integration`으로 남아 있다. 저장 인프라의 완료를 P2 전체 운용 통합 완료로 바꾸지 않으며, 이 남은 원래 P2 범위를 단순히 P3라고 이름 바꾸지 않는다.

## 1. 현재 결론

소유자의 E 결정은 확정됐다: **기한만으로 매도하지 않고 새 관리 승인을 요청한다.** PR4e가 마감 이후 알림·준비 차단을 고쳤지만, 마지막 정상 슬롯은 여전히 구 driver의 `target=0` 경로를 실행한다. 해당 알림 검사의 통과를 E 전체 구현으로 표시하면 안 된다.

다음 구현은 세 갈래로 나눈다.

1. 지금 개발할 수 있는 순수 행동 계약·판단 원인·새 배포 거절 경계. 실제 승인 발급자가 없어도 구현·음성 검증이 가능하다.
2. 새 행동에 맞는 driver/history/protocol 및 연구 평가 버전. 구 버전과 구 연구 해석은 보존한다.
3. 새 연구·소유자 관리 권한·보유 계좌 자료·주문 대조를 실제 검증하는 실행 연결. 발급자와 자료가 없는 동안 준비 상태를 거절하며, 임의의 `True`나 P1/P2 데이터클래스를 권한으로 사용하지 않는다.

다만 순수 계약만 별도 PR로 계속 쌓지 않는다. **첫 수직 구현은 이미 평가/검토 경로가 있는 fixed Upbit KRW 현물에 새 carry-v2 driver와 evaluator를 함께 연결하고, 실제 마지막 슬롯의 무매도를 dry control까지 검증한다.** 그 다음 같은 계약을 universe로 확장한다. fixed 검증을 universe 운용 완료로 표시하지 않는다. 신규 controlled/live는 현재 rehearsal-only 차단을 유지한다.

P2의 `unresolved_reductions`는 현재 알림으로 해제할 수 없다. 후속 실행/대조 경로를 만들기 전에는 해당 의도를 처리 완료한 것으로 간주하지 않는다.

## 2. 현재 코드에서 실제로 이어지는 경로

| 위치 | 확인한 사실 | 새 버전에서 필요한 조치 |
|---|---|---|
| `coordinator.py:schedule` 205–231 | `range(... + 1)`로 `window.end` 슬롯까지 예약한다. 관리 기한 이벤트 종류는 없다 | 관리 기한을 진입 슬롯보다 먼저 확정하고, 전송 직전에도 별도로 검사한다. 기존 Seoul 위험 경계 이벤트와 혼동하지 않는다 |
| `Coordinator._universe_slot` 785–895 | 정상 마지막 슬롯도 원본 관측 → 실제 history 기록 → `Runner.run`을 거친다 | 기한/관리 상태가 먼저 저장돼야 한다. 정상 호가나 보유를 버려 차단을 대신하지 않는다 |
| `LiveHistory._derive_universe` 651–685 | 최종 바는 기록하지만 새 decision/choice는 만들지 않는다 | 최종 관측과 평가를 남긴다. 창 밖 관측을 구 창에 덧붙이지 않는다 |
| `LiveHistory._frame` 687–693 | 마지막 슬롯도 직전 슬롯의 decision/inputs를 전달한다 | 직전 판단의 시차·원인·자료 유효성을 보존해 검증한다 |
| `Runner.tick` 479–544 | 대조/위험 관측 → `_assess` → 실제 callback → `_order` → reserve/dispatch. 전략 assessment 사유는 508행에서 buy에 적용되고 sell에는 같은 방식으로 붙지 않는다 | 새로운 자동 감소에는 별도 현재 관리 권한·전략/위험 원인 검증이 필요하다. 기존 explicit exit나 reducing gate가 새 자동매도 권한을 뜻하지 않는다 |
| `driver._validate_frame` 382–384 | `current.observed_at == window.end`이면 직전 전략 판단과 무관하게 target을 0으로 덮는다 | 구 factory 전용으로 보존한다. 새 factory는 기한을 매도 원인으로 만들지 않는다 |
| `driver._sized_signal` 264–293 | 목표 비중과 실제 비중의 차이가 음수이면 `exit`를 만든다 | 숫자 target만으로 판단 유효성이나 매도 원인을 추정하지 않는다 |
| `_FixedCallback.__call__` 476–478 | 마지막 바의 잔량 + HOLD는 terminal dust 오류다 | 새 버전은 잔량을 보존하고 DUST/관리 필요 상태로 기록한다. 가짜 전량 체결을 만들지 않는다 |
| `_validate_frame` 362–365, 421–423 | 첫 바는 target=0이며 실제 보유도 0이어야 한다 | 보유를 이어 관리하는 구간은 별도 초기조건/버전을 요구한다. 기존 flat-start 검사 삭제로 해결하지 않는다 |
| `Coordinator._after_tick` 주변 618–632 | 마지막 슬롯의 허용 구간이 지난 뒤 보유가 남으면 관리 승인 요청 문구를 알린다 | 이 알림만으로 앞선 마지막 슬롯 주문을 취소하거나 방지했다고 주장하지 않는다 |
| `Coordinator.prepare` 1093–1099 | missed window 및 window.end 이후 준비를 차단한다 | 마감 시각의 action gate와 독립 권한 만료 검사는 별도로 필요하다 |
| `Coordinator.__init__` 354 | 현재 `mode == 'rehearsal'`만 허용한다 | 준비 변경을 이유로 controlled/live 모드를 열지 않는다 |

실제 마지막 슬롯 호출 순서는 다음과 같다.

`schedule(final slot) → Coordinator._universe_slot → LiveHistory.record_slot → Runner.run/tick → _assess → factory-issued callback → _validate_frame(target=0) → _sized_signal(exit) → Controller.reserve/dispatch → dry adapter(검사 시)`

`entry_allow`는 buy gate다. 빈 allow-list나 신규 진입 차단만으로 이 sell 경로를 막았다고 판단하지 않는다. `_assess`는 실제 구현 검토 receipt를 별도로 검사하므로 “아무 검토도 없이 매도한다”는 뜻은 아니다. 문제는 그 기존 검토/exit 경계가 **새로운 독립 자동 관리 범위**를 발급하는 경계가 아니라는 점이다.

**prefetch 순서의 함정:** final-slot Due는 E가 아니라 `E - prefetch_lead`에 시작하고, `_await(E)` 후 같은 작업에서 Runner를 호출한다. E 시각 deadline Due를 추가하고 rank만 높여도 먼저 시작한 slot이 이미 점유한 실행 순서를 바꿀 수 없다. `_await` 이후 실제 `now >= E`를 확인하여 Runner/주문보다 먼저 deadline 차단을 확정하는 gate가 필요하다. 별도 deadline timer는 동일 ID의 보조/catch-up 경로이며, 그 타이머의 적시 실행만 신뢰하지 않는다.

## 3. target=0 삭제만으로 해결되지 않는 이유

`program.choose` 240–253행에서 warning은 cash, 보유 종목 수익률 미상은 같은 종목 유지(rule 2), 최소 보유 기간은 유지, 정상 비교 결과는 cash/rotation/유지를 반환한다. 반환값은 종목과 다음 chooser state뿐이다.

특히 242–243행의 “자료 부족이라 종목을 그대로 둠”은 검증된 HOLD가 아니다. 이 값을 양의 `exposure_fraction`으로 바꿔 `_sized_signal`에 넣으면 실제 비중이 목표보다 클 때 매도할 수 있다. **기한 override를 제거하더라도 UNAVAILABLE가 비중 조정 매도로 바뀌는 우회 경로를 차단해야 한다.**

새 판단 결과에는 최소 다음을 구분한다. 이는 순수 계산 결과이며 주문 허가가 아니다.

| 판단 | 의미 | 자동 감소 검토 |
|---|---|---|
| 유효한 warning/cash/rotation exit | 실제 유효한 자료로 기존 프로그램 규칙이 매도 또는 교체를 결정 | 별도 현재 권한·계좌/호가/위험 gate를 통과할 때만 검토 |
| 유효한 HOLD | 정의된 전략 조건으로 현재 보유 유지 | HOLD 자체를 매도 사유로 사용하지 않음 |
| 보유 수익률/lag/필수 입력 미상 | 프로그램이 판단할 근거가 부족 | UNAVAILABLE, 감소 원인 없음 |
| warm-up/초기 구간 | 필요한 관측 이력이 없음 | cash/0 숫자를 기존 보유의 매도 신호로 읽지 않음 |
| 코드 계산 예외 | 판단 계산 실패 | 고정 오류 + 의존 동작 보류, 감소 원인 없음 |
| 기한 도달 | 진입 차단·새 관리 승인 요청 | 기한 자체 감소 원인 없음 |

기존 비중 조정 매도를 새 경로에서도 전략 매도 사유로 지원하려면 `allocation_rebalance` 같은 원인을 **명시적으로 버전화·사전등록·평가**해야 한다. 이 문서는 그런 권한이나 새 전략 규칙을 기본값으로 추가하지 않는다. chooser의 과거 “결정 종목”과 계좌의 실제 보유는 별개이므로, 재시작 시 실제 보유를 구 chooser state에 덮어쓰지도 않는다.

## 4. A1에서 그대로 구현하면 안 되는 조항

대상: `docs/superpowers/specs/2026-11-12-standing-protective-hold-design.md`. 아래는 설계 문구이며 모두 현재 실행 코드에 구현됐다는 뜻이 아니다.

| A1 행 | 충돌 문구/동작 | 최신 요구에 따른 대체 |
|---|---|---|
| 26, 29 | 검사 불가능 → 매도, 설정 없음 → 즉시 매도 | 판단 불가와 실행 불가를 기록; 의존 동작 보류 |
| 147–176 | 재시작·만료·계좌 chain 복귀 → sell mode | P2 상태 복원과 계좌/미체결/체결 대조; 새 유효 원인 없으면 매도 없음 |
| 223–228 | 초기 검사 30초 실패·조건 미충족·시계 역행 → 매도 | 시간/자료 신뢰 회복과 필요한 관리 승인 절차 |
| 237–246 | 누락 슬롯/오류/재시작/설정 부재가 입력 I 또는 즉시 매도로 연결 | 원인별 진입 차단·감시 가능 범위·복구 상태 |
| 328–329, 338–351 | 위험선 미상·입력/시세/규칙 오류 → 위험 또는 I 매도 | 실제 위험 조건 충족과 위험 평가 불가를 분리 |
| 449–454 | E에 도달하면 sell mode | 새 진입 차단 + 같은 대상의 관리 승인 요청; 자동 연장 없음 |
| 547–550 | 설정이 없거나 아직 효력이 없으면 즉시 매도 | 미효력 설정을 사용하지 않고 권한 없는 동작 보류 |

유효한 S/T/B 및 실제 규칙에 따른 위험·halt 처리는 별도 보존한다. halt는 종류별 기존 gate가 결정한다. P1의 `halted`는 entry halt 모델이며, 적용되는 전체 주문 금지는 upstream의 `reduce_eligible=False`에도 반영해야 한다. 일괄 “모든 halt는 매도”나 “모든 halt는 같은 감소 금지”로 단순화하지 않는다.

## 5. 새 버전 계약과 구 근거 보존

다음 식별자는 구현 제안이며 아직 허용되는 버전이나 발급된 권한이 아니다.

| 계층 | 현재 | 새 경로 제안 |
|---|---|---|
| 공통 행동 계약 | 별도 canonical 계약 없음 | 새 `ManagedBehaviorContract` v1: `deadline_action=request_management_approval`, `failure_action=block_dependent_action`, `terminal_accounting=mark_open_positions`, 유효 감소 원인/초기조건 revision, Upbit/spot/KRW 범위 |
| 연구 protocol | schema 1, `forward-paper-v1` 또는 명칭만 정의된 `forward-universe-v1` | 첫 수직 경로는 명시적인 schema 2 + `forward-paper-carry-v2` + 행동 계약 digest. universe는 별도 `forward-universe-carry-v2` 구현 시 허용. 기존 schema 1에 새 의미를 몰래 붙이지 않음 |
| driver | `tradegen-fixed-cash-trend-v1` 단일 factory | 첫 수직 경로 `tradegen-fixed-cash-trend-carry-v2`; 후속 universe `tradegen-upbit-universe-managed-v2`. 각각 독립 발급/describe 분기 |
| identity | 정확한 7필드 | 모양을 유지할 수 있으나 새 factory 값·protocol digest·source digest로 구 행동과 구분. 새 필드가 필요하면 별도 schema로 전환 |
| 판단/history | 기존 `ChooserInputs`와 `HistoryFrame`; unavailable 정보 일부가 빈 값으로 축약됨 | 새 typed 판단 원인/가용성 및 입력 commitment를 새 revision에서 검증. 구 frame/slot bytes와 v3 저장 graph는 보존 |
| 연구 결과 | `PaperMetrics.terminal_units='0'`, 종단 전량 청산 | 새로운 결과 revision: 잔량·cash·FIFO 원가·실현/미실현 손익·발생 비용·최종 가격/시각/출처 |
| 검토·승인 | strict request/document/signer 형식 + 현재 실제 owner 검증 | 새 factory/evaluator/행동 계약 및 결과 의미를 명시적으로 검토·서명. 기존 signature를 변형된 bytes에 적용하지 않음 |

**두 종류 정책을 분리한다.** P1 `ManagementPolicy`는 관리 인스턴스·계좌·단일 symbol·기한·코드/전략/위험 해시에 고정된다. universe의 모든 종목에 적용되는 공통 행동 계약과 동일하지 않다. 연구 protocol이 공통 행동 계약을 bind하고, 실제 보유별 P1 policy와 독립 관리 승인이 해당 계약·현재 계좌·종목·자료·scope를 다시 bind해야 한다. 한 symbol의 관리 승인을 universe 전체 주문 승인처럼 확대하지 않는다.

현재 `strategy._protocol` 142–165행은 schema 1과 기존 두 evaluator 값만 허용한다. 새 값을 parser allowlist에 먼저 추가하고 나중에 의미를 채우는 순서도 금지한다. 새 revision의 parser/semantic dispatch/result issuer를 같은 단계로 도입하거나, 구현되지 않은 evaluator는 명시적으로 거절한다.

`driver._SOURCE_FILES` 36–42행은 14개 파일이며 `_sources` 178행은 factory ID까지 hash에 포함한다. 새 경로가 행동 모듈·P1/P2·추가 실행 모듈을 실제로 사용하면 필요한 source closure와 독립 signer 목록을 함께 갱신한다. signer는 app을 import하지 않는 현재 경계를 유지한다. 소스 hash 일치는 연구 성공이나 owner 승인의 대체물이 아니다.

구 protocol/frame/slot/registry의 bytes golden과 구 evaluator 결과는 그대로 검사한다. 구 factory는 과거 해석/명시된 legacy 검사에서만 재현하며 새 managed deployment의 선택지로 자동 승격하지 않는다. 소스 변경 때문에 구 runtime source hash가 달라지는 것은 구 서명이 새 코드를 승인한다는 뜻이 아니다.

## 6. 연구 평가를 함께 바꿔야 하는 부분

`strategy._simulate` 368–370행은 마지막 바에서 target=0, 387–388행은 종단 dust 오류, 401행은 잔량 0 요구, 410행은 `terminal_units='0'`를 기록한다. `run_paper_validation` 440–441행은 실제로 fixed evaluator만 허용한다. universe evaluator의 문자열이 선언돼 있다는 이유로 universe 평가가 구현됐다고 표시하지 않는다.

새 universe evaluator는 다음을 같이 구현해야 한다.

- 마지막 관측이 있다는 이유만으로 체결·수수료·왕복 횟수를 추가하지 않는다. 유효한 독립 매도 원인이 실제 모델에서 발생한 경우만 체결을 계산한다.
- 최종 평가는 잔량을 유지한 valuation이며 현금화 수익이 아니다. FIFO 원가, 모든 발생 수수료, 실현 순손익, 미실현 손익, 잔량과 최종 mark 근거를 분리한다.
- price 미확인은 0이나 최신 값으로 메우지 않는다. 온전한 상장 목록에서 부재가 확인된 경우의 명시적 0평가 정책도 체결가·실현손익·유동성 증거와 분리한다.
- 기본·배비용·추가 지연·benchmark에 같은 종단 회계를 적용한다. 최소 왕복 수나 유의 기준을 낮춰 새 결과를 통과시키지 않는다.
- `study._feasible` 195–206, `validate_study_plan` 209–225의 공통 terms/전체 family/출처 commitment와 새 revision을 일치시킨다. flat-start 성과를 carry 상태의 관리 성과로 간주하지 않는다.
- `study_review.authenticate_study_selection` 144–156은 전 후보 재평가 후 eligible만 review 문서를 요구한다. PR5의 정당한 실패 outcome·완전 family·확정 bundle 설계와 함께 확장하며, 실패 후보를 삭제하거나 허구의 ValidationResult를 발급하지 않는다.

새 evaluator/result issuer가 없는 동안은 parser·순수 회계의 수기 사례·부정 사례를 먼저 만들 수 있다. universe의 실제 양성 인증을 만들어 냈다고 보고할 수는 없다.

## 7. 새 live composition의 실패 시 차단 설계

현재 `compose/_compose_driver/compose_driver`는 `coordinator.py` 1170–1259행에 있으며 별도 composition.py는 없다. `_compose_driver`는 head/history를 만들고 `make_fixed_driver`를 발급한 뒤 `history.bind`로 기록한다. 새 managed composition의 거절 검사는 **해당 history bind 이전**에 둔다.

초기 개발 단계에서는 새 managed 생성/준비/활성화 진입점이 다음 미준비 상태를 고정 코드로 거절하도록 한다. 이것은 실제 검증 성공을 가장하는 `ready=True` 옵션이 아니다.

1. legacy factory·terminal evaluator·누락된 행동 계약의 조합: `MANAGED_BEHAVIOR_REVISION_REQUIRED`.
2. 새 universe capture/evaluator/issued result 및 전체 family 검토가 아직 지원되지 않음: `MANAGED_RESEARCH_REVISION_UNAVAILABLE`.
3. 독립 관리 승인 발급/검증 경로가 구현·설치되지 않음: `MANAGED_AUTHORITY_UNAVAILABLE`.
4. 실제 보유 계좌 interval의 가격 경로·체결/수수료/미체결 대조가 지원되지 않음: `MANAGED_ACCOUNT_SOURCE_UNAVAILABLE`.
5. P2에 미완료 감소 의도/불확실 시도가 남고 검증된 처리 결과가 없음: `MANAGED_RECONCILIATION_REQUIRED`.

코드는 제안이다. 임의의 사용자 JSON에 이 코드 대신 `approved:true`나 임의 callback을 주면 진행하는 우회로를 만들지 않는다. 새 managed composition의 실제 양성 경로는 concrete issuer/verifier가 준비된 후 추가한다. 기존 `Coordinator`의 rehearsal-only 제한, owner code/rules/limits/strategy/activation 범위 분리, 독립 관리 scope/만료/폐기 검사는 유지한다. 신규 gate가 기존 보유를 즉시 매도하거나 미체결을 임의 취소하지 않는다.

현재 `account_interval.py` 117–125행의 source는 flat-only exact extrema이며 보유/최근 fill을 거절한다. 이 경계를 삭제하거나 P1의 `account_ok=True`로 대체해 live 보유 관리 준비를 주장할 수 없다. 원장 참조 hash는 실제 원장 내용·최고점·보호 하한 검증을 대신하지 않는다.

## 8. 마지막 슬롯 회귀를 실제 구성요소로 검증하는 방법

현재 `tests/launch_coordinator_universe.py:119–130`의 fixture는 HOLD callback/history double을 사용하고 `_assess`를 patch한다. 950–964행의 deadline 검사는 `window.end + 11초` 뒤 monitor 알림 경로만 지나며 `env.decisions == []`를 확인한다. 따라서 마지막 정상 슬롯의 factory callback이나 종단 주문을 검증하지 않는다.

새 회귀의 양성 경로는 **Coordinator, 실제 factory-issued driver, 실제 LiveHistory+independent head, Runner, Controller+Journal, DryRunAdapter**를 사용한다. source 제공자만 고정된 합성 계좌·시세·시계로 구성하고 그 사실을 명시한다. `driver.callback=HOLD`, `_validate_frame` 대체, `_sized_signal` 대체, `_assess=lambda ...`, 승인 verifier의 임의 `True`로 최종 동작을 통과시키지 않는다.

| 단계/사례 | 필수 증거 |
|---|---|
| 구 버전 대조 | 기존 fixed evaluator와 실제 factory를 써 마지막 바 target=0/종단 청산이 재현됨을 별도 legacy 검사로 보존. 구 기대값을 새 값으로 고쳐 숨기지 않음 |
| 새 기한-only 사례 | 기한 직전 실제 보유, 유효한 HOLD/전략 매도 사유 없음. 정확한 마지막 슬롯이 실제 callback까지 도달한 trace와 final history graph 존재를 확인. 신규 reserve/dispatch/dry-create 0건, 잔량 유지, P2 갱신 요청 1개 |
| 같은 시각 entry 후보 | E 이벤트를 먼저 확정하고 새 entry reserve/create 0건. callback이 만드는 후보가 있어도 현재 E gate가 차단함 |
| 자료 미상/warm-up/계산 실패 | 실제 실패 원인을 보존; UNAVAILABLE, 신규 매도 0건. 정상 호가를 None으로 조작해 결과를 만들지 않음 |
| 유효한 독립 SELL/risk | 별도 현재 관리 권한·자료·기존 reducing gate를 통과한 경우만 1개 검토/시도. E 존재만으로 원인을 바꾸지 않음 |
| 만료/폐기/상충 scope | 예약 이전 및 실제 dispatch 직전 거절, 새 ID 자동 재시도 없음 |
| 미완료/부분/늦은 체결 | 기존 client/attempt ID로 대조; 알림·취소 수락만으로 잔량/약정 해제 없음 |
| 재시작/동일 E 재전달 | P2 restart·원장 대조·신규 진입 차단, 동일 승인 요청 ID 유지, 신규 자동 매도 없음 |
| dust/최종 mark 하락 | 잔량과 미실현 손익을 그대로 남기며 terminal dust를 전량 체결 성공으로 바꾸지 않음 |

**구현 순서에 따른 검증 한계:** 새 universe evaluator와 실제 source/implementation review issuer가 아직 없으므로, 당장 완전한 universe 양성 통합을 만들 수는 없다. 첫 수직 구현에서는 이미 있는 fixed 연구·검토 경계를 명시적인 carry-v2로 확장해 실제 구성요소를 연결하고, 기존 fixed-v1 대조와 새 final-slot 무매도를 같은 검사에서 입증한다. universe는 새 연구/승인 경계가 준비되면 동일 fixture 구조를 확장한다. 임시 테스트 키로 검증되는 합성 승인 문서는 실제 owner 서명이 아니며, 아직 지원하지 않는 연구 결과를 발급한 것처럼 가정해서는 안 된다.

## 9. 바로 이어 구현할 fixed carry-v2 수직 단계

### 9.1 선택 API와 canonical binding

- 선택의 단일 원천은 서명 대상 protocol이다. `schema_version=2`, `evaluator_revision='forward-paper-carry-v2'`, `behavior_revision='protective-carry-v2'`, `terminal_accounting='mark_open_positions'`, `management_behavior_sha256=<명시 계약 원문 해시>`를 함께 요구하는 조합을 제안한다. protocol schema 2와 기존 **review-request schema 2(family)**는 다른 형식임을 parser/문서에서 구분한다.
- 기존 `ForwardProtocol`을 확장한다면 새 필드는 기본 None/omit-none로 두되 **schema 1에서 전부 None만 허용**한다. schema 2는 누락/null/부분 조합을 거절한다. 또는 별도 typed protocol을 사용하더라도 동일한 strict dispatch가 필요하다. root가 기존 outcome 작업과 충돌하지 않는 형태를 최종 통합한다.
- `resolve_behavior(protocol)`는 검증된 revision 조합을 반환하는 순수 함수다. 임의 bool·env flag·callback으로 behavior를 바꾸지 않는다. `compose_driver`와 signer는 같은 protocol→factory의 닫힌 매핑을 사용한다. 알 수 없는 조합에 legacy fallback은 없다.
- `make_fixed_driver`의 기존 v1 계약을 보존하고 새 `make_fixed_carry_driver`를 별도 발급 경로로 둔다. 공용 frame 검사는 공유할 수 있으나 policy별 target/원인/terminal 처리는 명시 분기한다. `describe_*`는 실제 발급 객체·callback·source·history dependencies의 일치를 검증한다.
- 신규 fixed 연구는 flat-start부터 E까지의 구간을 평가한다. 창 밖 무기한 관리 성과를 증명한다고 하지 않는다. E 이후 독립 관리 구간은 기존 구간을 연장하지 않고 별도 정책/승인/초기 보유 상태로 연결한다.
- 신규 진입 구간은 `[window.start, E)`다. **E와 같은 시각부터 신규 매수도 차단**하며 evaluator와 driver가 같은 경계를 사용한다. E의 positive target을 그대로 남겨 마지막 매수를 만드는 구현은 불합격이다. 감소/취소/감시 scope의 만료는 E와 별도이며 각각 `[issued_at, expires_at)`로 검증한다.
- 첫 fixed carry-v2는 기존 fixed profile의 **GTC** 조건을 명시적으로 유지하는 개발 경로를 제안한다(`driver._identity:203–207`). universe의 IOC를 가져와 조용히 바꾸지 않는다. 이후 IOC를 선택한다면 profile/protocol/계산/검토를 묶은 별도 행동 변경이다.

**배정 전 공유할 API 카드(구현 명세 제안):**

| API/형식 | 필수 내용 | 경계 |
|---|---|---|
| `resolve_behavior(protocol)` | schema 1 + `forward-paper-v1` → legacy v1; schema 2 + `forward-paper-carry-v2` + exact behavior/terminal fields → fixed carry-v2 | 알 수 없는 값/혼합/누락은 거절. universe carry는 구현 전 허용 안 함 |
| `FixedDecisionV2` | `schema_version`, `bar_index`, `decided_at`, `history_sha256`, `behavior_sha256`, `state`, `cause`, `target_fraction`, `decision_sha256` | state는 `long_target/cash_target/warmup/unavailable`; cause는 버전화한 닫힌 집합. warmup/unavailable target은 None, valid cash는 0. metadata를 붙인 legacy PaperDecision이 아니라 새 codec |
| `derive_fixed_decision_v2(spec, validated_prefix, recorded_input_status, behavior)` | 공용 수식과 prefix만으로 위 결정을 계산 | 정상적으로 기록된 조회 실패와 손상된 prefix를 구분. malformed/hash mismatch는 거절하며, 정상 unavailable로 바꾸지 않음 |
| `derive_fixed_intent_v2(decision, account_anchor, slot, deadline)` | 실제 보유와 결정으로 `no_action/entry_candidate/reduce_candidate` 및 명시 원인을 계산 | 순수 후보, 주문 허가 아님. E부터 entry candidate를 실행 가능한 것으로 만들지 않음. 독립 SELL의 원인은 보존하고 권한 부재를 HOLD로 덮지 않음 |
| `CaptureArchiveV2` | legacy와 구분되는 schema, 원본 registry/source-kind/bars + canonical V2 decisions/behavior commitment | 전체 prefix/판단을 공용 함수로 재계산. 원본 receipt·당시 실패 기록을 재수집으로 대체하지 않음 |
| `evaluate_fixed_carry_v2(...)` | protocol, capture V2, 실제 program artifact, 규칙, registry, 평가 시각 → 새 typed 결과를 실제 발급 | callback bool 또는 수동 생성 metrics를 issued 결과로 허용하지 않음 |
| `CarryMetricsV2` / 새 결과 envelope | 공통 평가 통계 + terminal cash/units/mark/시각/출처, 남은 FIFO basis, signed realized/unrealized PnL, 발생 fee, fill/lot commitment | 결과 revision/domain은 legacy와 다름. 기존 독립 outcome codec과 root가 조합하며 중복 envelope를 만들지 않음 |
| `make_fixed_carry_driver` / `describe_fixed_carry_driver` | 설치된 artifact, 새 protocol, profile/window, 정확한 history provider/verifier → 실제 factory registry에 발급 | factory는 source/research/management/order 승인이 아님. implementation verifier는 정확한 registry 객체와 callback을 대조 |
| `compose_driver` revision dispatch | protocol에서 위 factory를 유일하게 선택하고 unsupported managed/live 경로를 bind 전에 거절 | CLI bool로 v1 서명을 v2 승인처럼 사용하지 않음 |

`state/cause`의 exact enum과 field names는 위 카드에 따라 root가 작업 배정 시 고정한다. 모델 의도를 실제 Runner `Signal`로 바꾸는 adapter도 versioned 분기이며, current 독립 scope 검사 없이 `reduce_candidate`를 Controller에 넘기지 않는다. unavailable를 단순 `Signal(action='hold')`로만 반환해 UI에서 모형 HOLD로 오인하게 하지 않는다.

### 9.2 첫 수직 구현의 행동과 회계

1. 기존 fixed 전략 계산과 같은 수식에서 `valid_hold`, `valid_strategy_sell`, `warmup`, `unavailable`을 분리한다. 유효한 독립 SELL/기존 위험 감소는 해당 현재 권한으로 가능한 경로를 남긴다. 기한, 실패, warm-up은 SELL 원인이 아니다.
2. 최종 바에는 실제 전략 판단과 수명주기 결정을 따로 남긴다. E-only이면 `block_entry/request_management_approval`이고 새 매도 없음이다. 모델이 유효한 SELL을 냈지만 별도 현재 관리 권한이 없으면 **SELL 판단 + 실행 차단**이지 HOLD가 아니다. 반대로 `hold` 숫자를 sizing해서 출처 없는 rebalance exit로 만들지 않는다.
3. 새 carry evaluator는 같은 행동 revision을 사용한다. final-bar의 보유 잔량을 최종 mark로 평가하며, 기한만으로 가상 매도/fee/roundtrip을 만들지 않는다. 기본·배비용·지연·benchmark 모두 같은 terminal contract를 쓴다.
4. FIFO 원가, 18dp 내림 배분과 마지막 잔량 귀속, 실제 발생 수수료, 실현 순손익·미실현 손익·valuation return을 분리한다(`profile.py:33–39`의 회계 계약 유지). 한 번 매수/부분 매도/여러 lot·수수료/최종 잔량의 독립 수기 예상값을 검사한다. `float` summary가 원장 계산을 대신하지 않는다.
5. 결과는 새 revision의 실제 evaluator만 발급한다. 기존 `PaperMetrics.terminal_units='0'`의 의미를 바꾸지 않는다. review request의 요약에 valuation을 실현 수익으로 표시하지 않으며 결과 digest와 승인 대상이 같아야 한다.
6. 실제 Coordinator final slot을 수행하는 시험을 같은 변경 단위에 포함한다. history/driver/runner/control을 stub HOLD로 우회하지 않는다. 신규 controlled 구성은 끝까지 거절한다. fixture의 합성 source 및 테스트 서명은 실제 시장 성과/owner 승인으로 표시하지 않는다.

fixed의 `target_fraction` 179–183행은 cash, warm-up, fast<=slow를 모두 0으로 표현한다. 새 공용 판단 함수는 원인을 각각 구분하고 evaluator와 driver가 같은 결과를 소비해야 한다. 두 곳에 별도 수식을 복제하거나 종단에서만 예외를 붙이지 않는다.

capture도 같은 계약을 사용한다. `paper_capture.py`와 `workflow.py`의 기존 경로는 숫자 `PaperDecision.target_fraction`을 생성하고, importer는 기존 exact shape를 읽는다. 새 revision은 typed 이유/가용성을 담은 **새 decision/capture codec**을 사용하거나, 검증된 program artifact와 모든 prefix에서 공용 typed 판단을 결정적으로 재계산한 commitment를 원본 capture와 함께 고정해야 한다. 권장 구현은 별도 v2 decision/capture 형식이며 구 `CaptureArchive/PaperDecision` bytes는 그대로 둔다. driver에서만 이유를 추가하고 evaluator가 구 숫자 target만 신뢰하는 조합은 거절한다. 각 결정의 시점·prefix hash·behavior revision·원인·target을 전체 재평가에서 대조한다.

새 손익 codec도 필요하다. 현재 `strategy._plain`의 Decimal 처리는 음수를 허용하지 않으므로, 구 serializer를 전역 완화하지 않고 새 결과 전용 **bounded signed decimal 문자열 codec**을 사용한다(독립 outcome 작업의 계약과 중복되지 않도록 root가 통합). FIFO 순손익 항등식은 `cash + market_value - initial_cash = realized_net + unrealized_net`이다. 매입 수수료를 원가에 포함하고 매도 수수료를 순수취액에서 뺀 뒤, 잔량의 원가도 보존한다. 표시용 총 fee를 다시 빼서 이중 차감하지 않는다. 반올림 배분 잔여분과 마지막 lot 귀속을 별도로 검사한다.

P2 갱신 요청 연결은 새 수직 단계의 좁은 통합 항목으로 포함한다. 마지막 슬롯의 `_await` 후 `now >= E` gate가 **명시적으로 구성된 P2 writer**에 deadline event를 한 번 기록하고, 확정 후에만 새 상태/요청을 표시한다. 이 event는 `authority=None`, 필요 시 `observations=None`으로도 진입 차단/요청을 만들 수 있으므로 현재 관리 권한을 가짜로 채울 이유가 없다. 원장 참조가 확인되지 않으면 None을 그대로 남긴다. 같은 P2 인스턴스에 중첩 session을 열거나 Controller journal lock을 잡은 상태에서 반대 순서 잠금을 얻지 않는다. 이 bridge의 완료는 원래 **P2-integration 중 기한 기록 부분**의 완료일 뿐, 실제 계좌/fill/openorders 대조 전체의 완료가 아니다. P2 저장 실패 시 신규 실행을 차단하고 실패를 알리며, 실패 자체로 매도하지 않는다.

**기존 GTC의 별도 경계:** E의 신규 reserve/create 0건은 E 이전에 이미 ACK/PARTIAL인 매수가 나중에 체결되지 않는다는 보장이 아니다. 기존 주문은 같은 ID로 실제 체결·수수료·잔량을 대조한다. 독립 현재 cancel scope가 없으면 deadline만으로 취소 권한을 만들어 내지 않는다. 회귀에는 E 전 부분 체결 후 E 후 늦은 fill이 새 주문 없이 반영되는 사례를 넣고, 이를 신규 매수나 평가지표용 가상 체결과 구분한다. 위험 gate·이미 유효한 취소 정책은 그대로 적용한다.

**허용 범위:** 이 단계의 실제 source/implementation review는 새 fixed 연구와 실행 구현을 검증한다. 아직 없는 독립 post-E 관리 권한 발급을 대신하지 않는다. 따라서 post-E 권한이 필요한 양성 매도는 미준비로 차단하고, 그 별도 issuer가 준비될 때 실제 양성 검증을 추가한다. 현재 유효한 별도 위험/명시 exit 경로를 기한 신호 때문에 폐기하거나 자동 발급하지 않는다.

### 9.3 파일별 단일 소유 분할 제안

현재 frozen PR4e와 P2-store 통합 후 **새 독립 branch**에서 시작한다. 아래는 작업 배정을 위한 제안이며 이미 해당 파일을 배정하거나 수정했다는 뜻이 아니다.

| 단일 소유자 역할 | 파일 | 의존/제외 |
|---|---|---|
| root 통합 소유 | `strategy.py`, `study.py`, `study_review.py`, `review_request.py`, `runner.py` | protocol/result/assessment dispatch의 단일 변경자. 독립 outcome codec 작업이 진행 중이므로 **strategy.py는 지금 다른 에이전트에게 배정하지 않음**. 준비된 새 모듈 API를 순차 통합 |
| driver/판단 소유자 | 새 `managed_behavior.py`, `program.py`, `driver.py`, 관련 driver/program tests | 공용 판단 수식·typed 원인·새 factory 발급. 고정 source 목록은 signer 소유자와 합의한 한 계약으로 맞춤 |
| carry 평가 소유자 | 새 `carry_evaluator.py`, 새 `tests/launch_carry_evaluator.py` | 독립 수기 회계 및 시뮬레이터 구현. `strategy.py` dispatch는 root만 변경; 다른 outcome codec 중복 구현 금지 |
| capture 소유자 | 새 v2 decision/capture codec, `paper_capture.py`, `workflow.py`, 해당 capture/workflow tests | 공용 typed 판단을 원본 기록/재평가까지 연결. codec·protocol adapter는 root와 먼저 합의; legacy capture shape 보존 |
| 검토/독립 signer 소유자 | `review_auth.py`, `tools/signer/sign.py`, 관련 review/signer tests | factory/evaluator 조합·실제 source closure·현재 owner 검증. app import 금지 유지, 구 schema/bytes 보존 |
| history/coordinator 통합 소유자 | `live_history.py`, `coordinator.py`, 새 final-slot integration tests | 같은 작업자가 frame revision과 final-slot 호출을 연결. P2-store의 순수 저장/잠금 코드는 동결 유지. 기존 PR4e 수정을 다시 병렬 편집하지 않음 |
| root 최종 검증 | acceptance registry, guards, 명세/로그 | source freeze 후 focused→필요 회귀. CRLF 유지, guard 약화 금지 |

`profile.py`의 금전 한도/회계 convention과 controller의 기존 위험·주문 권한 gate를 이 단계에서 완화하지 않는다. API 합의 순서는 (1) protocol/revision/result 형태 → (2) 새 평가/판단 모듈 → (3) root dispatch와 signer → (4) history/coordinator 실제 final-slot 검사다. 각 소스 파일에 두 작성자를 붙이지 않는다.

### 9.4 이후 남는 원래 범위

| 범위 | 남은 일 | 완료로 표시할 수 있는 때 |
|---|---|---|
| **P2-integration** | Coordinator bootstrap → 영속 상태 복원 → 실제 계좌/fills/openorders/수수료 대조 → 복구 전이, authoritative ledger 참조 내용 검사 | 순수 supplied facts를 넘어 실제 대조 결과를 검증하고 재시작 중 중복/신규 진입 차단까지 통과 |
| fixed carry-v2 이후 universe | PR5 universe capture/evaluator/정당한 실패 outcome/전체 family 검토 + 새 universe factory | 실제 universe 결과를 발급·검토하며 같은 final-slot 회귀가 실제 구성요소를 통과 |
| 독립 관리 권한 | 코드·연구·계좌/symbol·감시/감소/취소 scope·만료/폐기·입력 hash의 실제 verifier/issuer | P1/P2 모델 bool과 구 연구 검토를 권한으로 대체하지 않는 양성/음성 검증 |
| P3 자동 감소 실행 | fresh planning, reserve/dispatch 재검증, attempt ID, 미확인/부분/늦은 체결, 검증된 outbox 처리 결과 | 동일 원인/attempt 중복 전송 0, 미확정 잔량 해제 0, 유효한 독립 원인만 허용 |

첫 수직 PR의 완료 조건은 **새 fixed revision에서 actual final-slot E-only 매도 0건 + evaluator carry 회계 + 새 signer binding + legacy 회귀 보존**이다. detached 계약 모듈 존재나 준비 알림 검사만으로 완료 처리하지 않는다.

이 순서는 새 사용자 승인 질문이 아니다. 이미 확정된 E·오류 비청산·기존 손실 하한을 다시 묻지 않는다. 배포 환경·실제 서명·진짜 자료가 필요한 지점은 그 전제에 도달했을 때 검증하며, 미제공을 제공됨으로 간주하지 않는다.

## 10. 이번 읽기 대조의 파일 지문

```text
driver.py       012c670bc04640b92481afe222895ac8263cfb42466d4b6b80fda4895337d442
program.py      26c828174fdc89f749ddec4dc1e01ea8c8f0ee65a5401577390285ea6ec02666
strategy.py     14a332552591df5ac12917e2eb8d17e6e0ce9d7d4eaf25715431f8d1e5d0a9b5
study_review.py 5227c2ff545e2a882ddf9d8ceda624841948276290dcf98b3408cfc05ad0b70b
coordinator.py  a00942b311a68e8524b5150046fe5fd22cb95aca160e5b5f6853a1991662a5f0
runner.py       c2e72c019a79207f1a7fe0c26fafd01fd93b9290deb7ba0c1c5054f26dcdf637
```

분류: read-only source audit / implementation readiness. 실제 계좌 장애·Windows 운영·연구 합격·전자서명·실거래 시험 결과가 아니다. 법률·세무·투자 조언이 아니며 작성자는 면허를 가진 자문가가 아니다.
