# TRADEGEN: 기한 비청산·보호 보유의 단계별 구현 계획

작성: 2026-11-13. 소스 기준: PR34 `a0b28d0fc0fee4a359f833f91a7c0f572777481e`. 이 문서는 읽기 전용 코드 대조와 후속 구현 계획이다. P0b 전체 회귀가 진행되는 동안 작성했으며 그 결과를 선취하지 않는다. 아래 행동·권한·평가 변경은 아직 구현하지 않았다. 실제 계좌 조회·키·서명·주문·소유자 홈을 사용하지 않았다.

근거 문서: `TRADEGEN_PR4D_CAPACITY_AMENDMENT_2026-11-13.md`, `TRADEGEN_PROTECTIVE_HOLD_DESIGN_NOTES_2026-11-13.md`, `TRADEGEN_PR5_REVIEW_AMENDMENT_2026-11-13.md`, 저장소의 universe/PR4e/PR5 및 standing-protective-hold A1 설계. 최신 사용자 지시는 이전 A1의 충돌 조항보다 우선한다.

## 1. 확정된 요구와 완료 기준

- **기한만으로 매도하지 않고 새 관리 승인을 요청한다.** 새 진입 차단과 승인 요청은 기한 도달 사실에 따른다. SELL은 실제 전략 판단, 기존 유효 위험 조건, 명시적 소유자 exit에만 근거한다.
- 저장 장애·자료 부족·계산 오류·재시작·설정 누락은 SELL이 아니다. 판단 불가를 모형 HOLD나 상승 예상으로 표시하지 않는다.
- 기존 손실 하한·일일 한도·수수료·위험 최고점·halt를 완화하거나 초기화하지 않는다. 기존 SD-O1의 halt 시 자동매도 금지도 그대로다.
- 만료 후에는 **이미 유효한 독립 관리 권한**이 있는 범위만 수행한다. 그러한 주문 권한이 없으면 허용된 읽기 감시만 하고, 감시 기한도 끝나면 소유자 관리 필요로 인계한다. 미응답·알림 실패는 승인이나 유예가 아니다.
- 지원 범위는 Upbit 원화 현물 유니버스다. 다른 시장·파생상품 지원을 추정하지 않는다. 재서명·실거래 활성화·실제 주문은 이 구현 계획의 실행에 포함되지 않는다.

완료는 새 정책이 코드·연구·검토·운영 경계에서 같은 의미를 갖고, 숨은 종단 청산이 없으며, 장애/복구 시 중복 주문·무승인 재개가 없음을 검증한 상태다. P0b의 정상 자료 저장 성공만으로 이 완료를 주장하지 않는다. 이 문서에는 새 사용자 승인 질문이 없다.

## 2. 현재 코드의 정확한 변경 지점

행 번호는 `a0b28d0` 기준이며 구현 시 함수 이름과 원문을 다시 대조한다.

| 현재 위치 | 현재 동작 | 필요한 변경 |
|---|---|---|
| `driver.py::_validate_frame`, 382–384행 | 창 마지막 바이면 전략 판단과 무관하게 target=0 | 새 행동 revision은 이 강제를 사용하지 않는다. 마감 통제 결과와 모형의 목표/SELL 원인을 분리 |
| `driver.py::_FixedCallback.__call__`, 476–478행 | 마지막 바에서 보유 중 HOLD이면 종단 dust 미청산 오류 | 새 비청산 계약에서는 유효한 잔량 종료를 허용. 실제 최소주문/dust 사실은 그대로 기록 |
| `driver.py::_validate_frame`, 362–365행 | 첫 바의 prior decision은 없어야 하고 target=0 | 재시작·관리 갱신 후 보유를 이 flat-start 경로에 억지로 끼워 넣지 않음. 초기 보유 상태와 모형 준비 상태를 별도 계약으로 검증 |
| `program.py::choose`, 240–254행 | warning은 cash, 보유종목 수익률을 계산할 수 없으면 h 유지; 반환은 coin/state뿐 | 새 관리 판단에 원인과 자료 유효성을 추가. rule 2의 h 유지가 상승 전망이나 검증된 HOLD라는 뜻은 아님 |
| `program.py::target_fraction`, 179–180행 | 준비 구간에는 0 반환 | 새 관리 경로는 warm-up 0을 실제 매도 신호로 읽지 않음. 고정 종목 과거 재생은 유지 |
| `live_history.py::_derive_universe`, 673–685행 | 마지막 슬롯은 새 decision/inputs/choice를 만들지 않음 | 기존 창 끝에 다음 창 자료를 append하지 않음. 마지막 관측·잔량과 관리 종료/갱신 이벤트를 별도 기록하고 새 관리 시계열은 명시적인 새 구간으로 시작 |
| `strategy.py::_simulate`, 368–410행 | 마지막 바에서 강제 청산, 잔량 0 요구, `terminal_units='0'` 고정 | 새 평가 revision은 종단 잔량을 보존하고 평가액을 계산. 실제 매도/수수료를 만들어 넣지 않음 |
| `strategy.py::run_paper_validation`, 440–457행 | 현재 구현은 fixed evaluator만 실행; 기본·배비용·추가지연·benchmark에 같은 simulator 사용 | universe 평가 자체는 PR5 예정 작업. 새 비청산 universe revision을 그 경로에 명시적으로 추가. 현재 fixed evaluator를 universe로 오인해 재사용하지 않음 |
| `strategy.py::assess_strategy`, 508행 이후 | 발급된 ValidationResult와 프로토콜·기간·검토를 대조 | 새 종단 회계와 결과 revision을 포함한 발급·검토를 엄격히 확인. 오래된 결과 객체/서명 재사용 금지 |
| `study.py::_feasible`, 195–206행 | 기존 왕복 횟수 상한과 inference 예산 검사 | 종단 가짜 왕복이 사라진 새 경로에도 기준이 성립하는지 재계산. 통과를 위해 최소 횟수나 유의수준을 낮추지 않음 |
| `study.py::validate_study_plan`, 209–225행 | 후보 공통 protocol 필드·전체 family·capture source 고정 | 새 관리/종단 정책을 후보 공통 계약으로 고정. 후보별로 다른 종단 정책을 비교군에 몰래 혼합하지 않음 |
| `coordinator.py::schedule`, 146–172행 | 마지막 슬롯까지 생성, 모니터는 monitor_until까지 | 슬롯 실행보다 먼저 처리되는 deadline event 추가. 같은 시각의 entry/order 생성 전에 차단을 확정 |
| `coordinator.py::_refused`, 364–373행 | 사유/진입 차단 상태 갱신; 자동매도 없음 | 이 사실을 유지하며 오류 종류별 판단 가능/실행 가능 상태를 추가. 여기에 자동 exit를 넣지 않음 |
| `coordinator.py::_slot`, 504행 이후 | 관측→history→runner tick | 새 정책의 마감/관리 권한 gate를 history와 order 사이에 재검증. 정상 자료를 버려 gate를 대신하지 않음 |
| `coordinator.py::stop/close/disarm`, 628/634/663행 | stop은 슬롯 중단, close는 스케줄 종료, disarm은 kill 기록 시도 | 기능을 구분해서 유지. deadline을 무조건 close나 명시적 owner exit로 변환하지 않음 |
| `coordinator.py::_explicit/submit_exit`, 548/742행 | 이미 만든 exit signal을 별도 단위에 전달하며 그 단위가 나중에 호가를 읽음 | 보호 자동매도는 같은 실행 단위의 계좌·호가로 계획을 만들도록 별도 내부 함수 추가. 외부에서 만든 오래된 가격을 현재 호가와 섞지 않음 |
| `runner.py::tick`, 419–424행 | 검토 검증 후 driver 실행 | 연구 손상·만료 시 그 전략을 실행하지 않음. 별도 위험 관리가 유효한 경우만 독립 경로로 분리 |
| `runner.py::submit_exit`, 488–504행 | 정지/검토 만료 후 명시적 exit 경로, 현재 계좌·호가·규칙 검사는 유지 | 메서드 존재를 자동매도 권한으로 보지 않음. 자동 보호 실행은 독립 검증 권한과 원인 검사를 앞에 둠 |
| `review_auth.py::_authenticate`, 163–171행 | 코드·현재 키·정책 상태와 `issued <= now < expires` 검사 | 만료 규칙을 완화하지 않음. 다른 독립 관리 권한과 연구 검토를 혼동하지 않음 |
| `controller.py::_snapshot_risk/observe`, 409/457행 | 하한·일일 정지/halt를 기록하되 observe는 매도하지 않음 | 기존 우선순위와 latch 보존. 넓은 `protective_action_needed` 플래그만으로 SELL을 만들지 않음 |
| `controller.py::_capacity/_authorize/dispatch/reconcile`, 568/627/698/805행 | 수량 약정·최신 자료·전송 전 기록·체결 대조 | 보호 매도도 그대로 통과. reserve와 실제 dispatch 사이의 승인 만료/폐기를 재확인할 검증점 추가 |

A1에서 바꿀 조항은 26행(I 오류→매도), 147–176행(재시작/체인 복귀→매도), 223–246행(초기 검사·값 부재→매도), 328–351행(위험 수치 미상·검사 불가→매도), 449–454행(E 매도), 547–550행(미설정/미효력→매도)다. 이 설계 문구를 기존 그대로 구현하면 최신 요구를 어긴다.

## 3. 먼저 고정할 버전·자료 계약

다음 이름은 구현을 위한 구체 제안이며 현재 발급된 권한이나 구현된 API가 아니다.

1. 새 순수 `execution_launch/management_policy.py`에 `ManagementPolicy`를 둔다. 필드는 schema/revision, `deadline_action=request_management_approval`, `failure_action=block_dependent_action`, `terminal_accounting=mark_open_positions`, 기존 위험 정책 digest, 연구/driver revision 참조, 대상 `upbit/spot/KRW`다. 손실값을 새 기본값으로 추가하지 않는다. 정책 원문은 명시 입력이며 canonical hash로 bind한다.
2. `ForwardProtocol`의 새 schema/revision 조합을 명시한다. 제안: schema 2 + evaluator `forward-universe-carry-v1` + 필수 `management_policy_sha256` 및 `terminal_accounting` 값. 기존 schema 1의 선택 필드는 계속 omit-none이고 기존 fixed/universe 문서 bytes·digest는 유지한다. schema 1에 새 비청산 의미를 조용히 붙이지 않는다. 지원하지 않는 조합/명시 null/누락/잘못된 시장은 거절한다.
3. driver의 새 behavior revision은 명시적인 factory 식별자로 구분한다. 제안: `tradegen-upbit-universe-managed-v2`. FixedDriverIdentity의 7필드 모양은 유지하되 `factory_id`와 protocol/source digest가 새 행동을 구분한다. 기존 factory는 과거 해석용으로 남기며 새 운영 구성에서 최신 정책을 요구한다. 거래소 데이터나 계좌가 같아도 구 행동 검토를 새 행동 검토로 승격하지 않는다.
4. `_sources`와 독립 signer `_review_source_hash`는 동일한 allowlisted factory ID와 동일한 확장 source 목록을 사용하도록 같이 바꾼다. signer가 app을 import하지 않는 경계는 유지한다. `review_auth`, request 검증 및 signer의 factory allowlist도 동시에 갱신한다. 새 순수 정책/관리 reducer가 실행 판단에 쓰이면 그 파일을 source closure에 추가한다. 경로·코드 hash가 source 진위나 연구 성공을 대신한다고 주장하지 않는다.
5. 새 관리 시계열은 기존 마감 창을 연장해서 만들지 않는다. 별도 관리 구간 ID, 이전 확정 history head, 계좌/주문 대조 snapshot, 연구·승인 참조와 독립 head를 갖는다. 손상/공백을 새 구간의 과거 관측으로 채우지 않는다. 새 보유 초기조건과 warm-up 의미를 preregister한다.
6. `PaperMetrics`의 기존 모양을 몰래 재해석하지 않는다. 새 결과 revision에는 현금·종목별 잔량·평가 가격과 시각/출처·잔량 원가·실현/미실현 손익·누적 비용을 명시한다. legacy 결과는 legacy codec로만 읽는다. 결과 전체/등록/family digest와 승인 evidence가 새 revision을 함께 묶어야 한다.

새 값의 존재만으로 자동매도나 승인 권한이 발급되지 않는다. 새 protocol 원문과 정책 원문의 해시 일치, 발급된 source/management 권한, 실제 코드 승인은 각각 검증한다.

## 4. P1 — 순수 상태 전이와 기한 이벤트

**변경 파일:** 새 `execution_launch/protective_state.py`, 새 `tests/launch_protective_state.py`, policy codec/테스트, 관련 설계 문서. 아직 실제 runner/거래소 호출을 연결하지 않는다.

`reduce_management(previous, event, validated_inputs)`는 네트워크·파일·시계 접근 없이 새 immutable 상태와 `EffectIntent` 목록만 반환한다. 효과는 `block_entry`, `request_management_approval`, `notify`, `reconcile`, 그리고 **유효한 명시 원인이 있을 때만** `consider_reduce`다. `consider_reduce`는 주문 허가가 아니다.

- 상태 축을 `strategy_verdict={HOLD,SELL,UNAVAILABLE}`, `management_state={MONITORING,WAITING_INPUTS,RECOVERING,RENEWAL_PENDING,EXIT_PENDING,HALTED,OWNER_ACTION_REQUIRED,CLOSED}`, 관측/평가/기록/감소/진입 가능성으로 분리한다.
- deadline, 연구 만료, 진입 권한 만료, 감소/취소 권한 만료, `monitor_until`은 서로 다른 이벤트다. 모두 같은 `expiry` boolean으로 합치지 않는다. 유효기간은 `[issued_at, expires_at)`로 고정한다.
- deadline event는 `block_entry`와 갱신 요청을 한 번 만들며 `consider_reduce`를 만들지 않는다. 유효한 독립 위험/전략 이벤트가 동시에 있더라도 별도의 원인·권한·입력 해시를 요구한다.
- `choose`의 결과에 근거 상태를 붙인다. valid warning·완전한 비교의 momentum/rotation exit·valid hold·missing held return·warm-up·계산 실패를 구분한다. 기존 `choose` 2튜플 반환은 legacy 호환으로 보존하고 새 typed 결과를 내는 공용 내부 계산에서 원인과 target을 함께 결정해 중복 구현의 불일치를 피한다.
- missing data 때 h 유지가 필요하더라도 전략 확신을 뜻하는 HOLD로 표시하지 않는다. 새로운 초기 구간에서 cash/0 또는 warm-up을 보유 종목 매도의 원인으로 사용하지 않는다. 보유 기간 계수와 실제 관측 공백을 정직하게 기록한다.
- 유효한 halt가 우선한다. 위험 평가 불가와 실제 한도 도달을 구분하며 어느 쪽도 임의 하한 감소나 halt 해제를 만들지 않는다.

**검증:** deadline 직전/동일/직후, 동일 시각의 마감과 entry, duplicate event, 알림 실패, 6가지 장애(입력/계산/계좌/저장/설정/재시작)에서 자동 SELL 의도 0개; 유효한 독립 위험 이벤트만 별도 감소 검토 의도; warm-up/unknown≠SELL; 실제 HOLD와 UNAVAILABLE 표시 구분; mutable 입력·잘못된 policy hash·다른 계좌/종목 거절. 이 단계는 실제 주문 0건이 합격 조건이다.

## 5. P2 — 상태 영속화·재시작·승인 요청의 정확한 결합

**선행:** P0b의 실제 graph/head 연결 검증 완료, P1 reducer. **변경 파일:** 새 `execution_launch/protective_store.py`, 새 `tests/launch_protective_store.py`, 이후 coordinator의 최소 bootstrap 연결. 독립 journal 종류를 추가하는 경우 기존 control journal enum을 무분별하게 열지 않는다.

1. 보호 인스턴스·policy/driver/research 해시·마지막 정상 source hash·확정 상태·위험 최고점·하한/halt 참조·관리 기한·주문 의도/시도·승인 요청 ID를 hash-chain과 독립 head에 기록한다. 원본 payload는 P0의 객체 저장을 재사용한다. 최고점과 금융 원장은 새 보호 로그가 대신 쓰지 않고 권위 있는 원본을 참조한다.
2. 상태 전이와 승인 요청 outbox 기록을 같은 확정 순서로 묶는다. 요청 ID는 인스턴스·deadline 이벤트·정책/대상 해시·요청 scope에 고정한다. 재시작/중복 클릭/재전송이 새 승인이나 중복 적용을 만들지 않는다. 알림 전송 여부는 별도 receipt이며 요청 적용의 선행 승인이 아니다.
3. startup은 단일 실행 잠금→코드/정책/원본/head 검사→보호 상태 복원→계좌·체결·수수료·흐름·관련 미체결 대조 순서다. 새 진입은 처음부터 차단한다. UNKNOWN/DISPATCHING은 조회로 대조하고 새 ID 전송으로 대체하지 않는다.
4. 동일 원본 exact recovery는 해시/서명/대상 목록을 재검사한다. 복구 성공이 elapsed deadline·revocation·missed slot을 지우지 않는다. 새 버전 재구성은 새로운 승인이 필요하며 old head를 임의 초기화하지 않는다.
5. 재시작 뒤 이미 만료한 deadline은 다시 발급하지 않는다. 영속 UTC와 새 부팅의 monotonic clock을 구분한다. 옛 monotonic tick 수치를 새 부팅에서 유효 시간으로 사용하지 않는다. 계좌 chain 공백을 가격 불변·손익 0·최고점 불변으로 단정하지 않는다.
6. 새 관리 승인 적용은 대상 코드/정책/자료/계좌·scope·기한·폐기를 모두 검증한 후 상태를 전환한다. `management` 승인만으로 `entry/arming` 권한을 발급하지 않는다. 승인 범위가 감소/감시라면 그 두 기능만 가능하다.

**검증:** 단계별 crash/fault injection, state 기록과 outbox 사이 crash, journal/head 불일치, 과거 정상 백업 rollback, 만료 이후 exact restore, 요청/응답 replay, 다른 연구/계좌 승인 끼워 넣기, 원본 누락을 일부 성공으로 승인하는 동작 거절; 과매도 약정·취소 경합·부분/늦은 fill·미확인 전송 복원. 실패로 생성한 승인 요청을 알림 성공만으로 적용하지 않는다.

## 6. P3a — 새 driver·연구 평가의 종단 정책을 함께 구현

**선행:** universe PR5의 capture/evaluator와 전체 후보 인증 경로. PR5가 아직 없으므로 기존 fixed simulator에 rename만 하여 universe 검증으로 보고하지 않는다. **변경 파일:** `program.py`, `strategy.py`, `driver.py`, `paper_capture.py`, `study.py`, `study_review.py`, review request/auth 및 독립 signer의 좁은 version 경계; 새 또는 확장된 universe capture/strategy/driver/review 테스트.

- 새 protocol/evaluator/factory 조합을 strict하게 dispatch한다. legacy 경로의 종단 청산 결과는 읽기·과거 재계산을 위해 그대로 유지하며, 새 운영 구성은 새 정책 없으면 진입 준비를 거절한다. old signature로 new factory/result를 통과시키지 않는다.
- 새 `_validate_frame` 경로는 창 끝이라는 이유로 target=0을 만들지 않는다. 유효한 lagged 전략 판단은 그대로 검증하되, 신규 진입 기한과 별도 감소 권한은 planner/runner/dispatch gate에서 다시 확인한다. 만료 시점의 기존신호도 새 권한을 대신하지 못한다.
- `_FixedCallback`의 terminal dust 강제 거절은 legacy 전용으로 둔다. 새 정책의 잔량은 정상 보유 종료/최소주문 잔량으로 기록한다. 빈약한 자료를 정상 HOLD로 만들기 위해 source/quote 검사 자체를 빼지 않는다.
- 새 simulator는 마지막 바를 강제 매도하지 않는다. 마지막 관측에서 cash와 실제 시뮬레이션 잔량을 평가하고 다음 창의 주문·가격은 읽지 않는다. 신호가 있어도 그 시점의 정책상 권한 범위를 연구 프로토콜에서 동일하게 모델링한다.
- 기존 회계 계약은 `profile.py:37–39`의 **FIFO, 모든 수수료, 18dp 배분/마지막 잔량 귀속**이다. 연구의 잔량 원가·실현 순손익도 같은 정의를 사용한다. 임의 평균원가로 바꾸지 않는다. simulator 내부 Fraction과 실제 금융 Decimal의 경계·반올림을 독립 수기 사례로 검사한다.
- 종단 `valuation_return`에는 미실현 손익이 있을 수 있다. `realized_net_profit`, `unrealized_pnl`, 실제/시뮬레이션 발생 수수료, terminal quantity/cash/source를 별도로 기록한다. 가상 청산 비용을 보수적 시나리오로 제시할 경우 별도 항목이며 체결·실현 수익에 넣지 않는다.
- 기본·배비용·추가지연·benchmark에 동일한 종단 회계 정책을 적용한다. 종단 미청산으로 완성 왕복 횟수가 줄어도 합격 문턱을 낮추지 않는다. 자료가 부족하면 평가 실패 후보로 전체 family 안에 보존한다. 과거 연구·실패 후보·시험 횟수도 지우지 않는다.
- 종단 가격 미확인은 합성 0가격/최근가격으로 대체하지 않는다. 완전하고 유효한 상장 목록 조회로 해당 종목의 부재가 확인된 경우에만 기존 명시적 0평가 회계 정책을 적용한다. 목록 조회 실패·불완전은 미확인 상태로 남긴다. 이 0평가는 관측된 시장가격·체결가격·실현손익이나 유동성의 증거가 아니다. 자료 손상은 전체 의존 연구의 인증을 보류하는 PR5 정책을 따른다.
- 정상 flat-start 전략 성과가 post-stop 보유 관리 성과를 입증한다고 주장하지 않는다. 보유에서 시작하는 별도 관측/평가의 초기조건·권한·대조 benchmark가 필요한 경우 새 연구 버전을 만들고, 근거가 없는 동안 새 모델의 자동 보호 결정을 승격하지 않는다. 이미 유효한 기존 위험 관리와 수동 exit는 별도다.

**검증:** 마지막 바까지 계속 보유하는 경로의 주문·fee·roundtrip이 늘지 않음; 기존 종료 청산 평가와 새 평가의 digest가 다름; 종단 가격 하락·가격 누락·부분체결·dust·음의 수익을 숨기지 않음; 다른 정책을 benchmark에 혼합하면 거절; old/new capture·review·factory 조합의 상호 오인 거절; 실현 손익이 평가손익으로 늘어나지 않음; source clause를 하나씩 변조하면 독립 signer/driver 검증 실패.

## 7. P3b — 보호 매도의 실행 및 중복 방지

**선행:** P1/P2, 새 행동 revision, 실제 보유 계좌 source 계약과 그 구현, 현재 위험 정책 연결. `account_interval.py:117`의 flat-only 구간 source를 그대로 둔 채 보유 감시가 실전 가능하다고 주장하지 않는다. PLB의 owner S1~S12 확인이 필요한 하한 변경 분기도 임의 통과시키지 않는다.

**변경 파일:** 새 `execution_launch/protective_execution.py`, `runner.py`, `controller.py`의 목적이 한정된 검증점, coordinator의 별도 작업 단위, 해당 테스트. 기존 주식/파생 어댑터는 바꾸지 않는다.

- `consider_reduce`를 받으면 그 실행 단위 안에서 fresh account/book/rules/risk/authority를 다시 읽고 계획한다. 검증된 `ReduceIntent`에는 원인·입력 해시·실제 조건값·scope·권한 digest·만료·시도 번호가 들어간다. `deadline`, `storage_error`, `restart`, `settings_missing`은 허용된 매도 원인이 아니다.
- reserve뿐 아니라 dispatch 직전에도 관리 권한·만료·폐기와 같은 주문 내용을 대조한다. 승인 직후 만료/폐기되거나 입력이 바뀐 경우 이미 예약했다는 이유로 전송하지 않는다. 새 검증점은 단순 callable true나 임의 dataclass만으로 권한을 발급하지 않는다.
- 기존 controller의 계좌 완전성·수량 약정·규칙·conduct·fee 검사와 halt 우선순위를 그대로 통과한다. 매도량은 확인된 미약정 보유량 이하, 가격은 해당 단위의 best bid와 승인된 슬리피지/틱 규칙으로 계산한 IOC 지정가다. 자동 시장가 전환·슬리피지 확대 없음.
- 보호 intent ID와 실행 attempt ID를 분리한다. 동일 attempt의 불확실 전송은 같은 ID 조회로 대조한다. terminal 확인 전 새 시도를 만들지 않는다. 시도가 종료된 뒤에도 현재 권한·원인·자료를 다시 확인한다. 만료는 자동 재시도를 중지하고 갱신 요청/상태를 갱신한다.
- 부분 체결은 실제 fee/fill 증거로 반영하며 남은 수량만 재계획한다. 취소 요청은 약정량 해제나 terminal 확인이 아니다. 외부 미체결을 임의 취소하지 않는다. 최소금액 미만 잔량은 DUST로 계속 계좌에 남고 전량 청산 성공으로 표시하지 않는다.
- monitor 안에서 `_work`를 잡은 채 `_explicit/submit_exit`를 호출하지 않는다. 모니터는 intent를 확정하고, 잠금을 풀고 별도 실행 단위를 예약한다. 모든 경로의 lock 순서를 하나로 문서화하고 account provider의 control journal 재진입을 막는다.

**검증:** 유효한 SELL/T/B 각 원인과 단독 오류/E의 전송 0/1회 구분; reserve/dispatch 사이 만료·폐기; 0/부분/전부 체결; 응답 분실·늦은 체결·취소 경합; 수량/price 변경 후 ID 재사용 거절; 현재 fee/lot/tick/minimum; halt 중 감소 주문 0회; close/권한 종료 후 자동 재시도 0회; 교착/경계 시간/요청 예산 검증.

## 8. P4 — coordinator·운영 화면·승인 흐름의 통합

**선행:** PR4e와 L1/L3 운영 구성, PR5 증거 보관·손상 복구, 새 승인 verifier/management scope. Telegram·WebAuthn 설계는 별도 통합 계획을 따르며 봇에 키를 맡기지 않는다.

- `schedule`에 정확한 deadline event를 추가하고 같은 시각에는 진입 슬롯보다 먼저 처리한다. 실제 전송 시각의 gate도 필요하므로 타이머 순서만으로 안전을 보장하지 않는다. 창 종료의 마지막 관측/잔량은 기록할 수 있지만 deadline-only 매도를 만들지 않는다.
- 최초 기한 이벤트에 승인 요청을 내보내고 `RENEWAL_PENDING`을 표시한다. Telegram은 알림·화면 이동 수단이며 등록된 인증수단의 서명 증거와 독립 verifier가 실제 적용을 결정한다. 승인 범위가 관리뿐이면 별도 entry arming은 여전히 필요하다.
- 연구가 손상되면 그 연구를 쓰는 전략판단과 신규 진입만 먼저 막는다. 신뢰 가능한 독립 위험/계좌/권한이 남아 있는지 검사하여 사용 범위를 결정한다. code 또는 계좌 journal이 깨지면 더 넓은 실행 차단이 필요하다. 전체 자료 복원 전 정상 연구로 표시하지 않는다.
- `monitor_until` 이후에는 감시를 조용히 계속하지 않는다. 남은 보유·미체결·마지막 관측·후속 필요 조치를 남기고 `OWNER_ACTION_REQUIRED`로 끝낸다. 알림 실패도 저장하며, 사용자가 알림을 받지 못했다는 이유로 승인됐다거나 보호가 계속된다고 추정하지 않는다.
- 신규 Windows 운영 전에는 실제 파일 잠금/재시작/권한·OneDrive 외 저장 경로·백업·owner 승인 적용을 검증한다. Linux fake 테스트는 Windows 운영 증거나 실제 계좌 장애 시험이 아니다.

**검증:** end-to-end로 deadline → 진입차단/요청 → Face ID/WebAuthn 테스트 증거 → 독립 로컬 검증 → 해당 관리 scope만 적용 → 결과 알림. 만료·변경·재사용·폐기·통신 실패 모두 자동 승인 없음. 연구 승인이나 관리 승인이 거래 활성화까지 넓어지지 않음. 새 관리 후 과거 보유/미체결을 대조하지 않고 신규 진입하는 경로 없음.

## 9. 검증·출시 경계

각 단계는 변경된 순수 모듈/해당 suite → 영향 있는 history/driver/strategy/owner/controller 회귀 → 경계 guard → 안정된 소스에서 필요한 전체 suite 순서로 검사한다. 실행 중 소스를 고치지 않는다. 기존 bytes golden을 새 값으로 바꿔 실패를 숨기지 않는다. 새 정책 때문에 바뀌는 기대치는 새 revision 테스트에서 검증하고 legacy 결과를 그대로 유지한다.

로그에는 `synthetic_boundary_reproduction`, `offline_fault_injection`, `owner_pc_real_incident`를 구분한다. 이 계획의 준비 과정은 **읽기 전용 분석**이며 새 테스트 실행도 하지 않았다. 실제 계좌 장애 사례는 없다. 실제 연구 합격·전자서명·관리 권한·활성화 준비가 완료됐다고 표시하지 않는다.

당장 독립적으로 진행 가능한 일은 P1 순수 codec/reducer·검증표, P2 저장/복구 fault fixture, P3a의 버전·회계 수기 사례와 기존 source 대조다. 실제 owner 입력·source 권위·승인이 필요한 단계는 그 전제에 도달할 때만 적용하며, 미실행을 실행됨으로 간주하지 않는다. 이미 확정된 E 비청산이나 기존 손실 정책은 다시 질문하지 않는다.

법률·세무·투자 조언이 아니며 작성자는 면허를 가진 자문가가 아니다.
