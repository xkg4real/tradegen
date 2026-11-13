# TRADEGEN: 지금 실행하면 곧바로 자동 실거래가 되는가

**아직 아니다.** 현재 제공되는 운영 조립 경로는 모의 주문 전용이다. API 설정이나 서명만 추가하면 곧바로 실거래로 전환되는 상태가 아니며, 첫 체결 이후 보유 자산을 계속 검증·관리할 운영 연결이 남아 있다.

확인 기준: 2026-11-13, 소스 `a0b28d0fc0fee4a359f833f91a7c0f572777481e` 및 handoff `CURRENT.md`의 P0b 체크포인트. P0b 핵심 회귀는 **213 PASS / 0 FAIL / 0 NOT_RUN**, 전체 검사는 이후 완료됐다: 2660 PASS / 0 FAIL / 135 NOT_RUN (전체 2795개; 환경 재시작 뒤 동일 소스의 나머지 검사를 재개). 기존 macro121/Windows14 미실행을 통과로 계산하지 않는다. 환경 재시작 전후의 동일 소스 결과를 registry 전체와 대조했다. 이전 커밋의 전체 통과 수를 이번 코드의 결과로 대신 쓰지 않았다. 본 문서 작성은 읽기 전용 코드 대조이며 실제 계좌·키·소유자 홈·거래소 API를 확인하지 않았다. 사용자 Windows PC에 이 커밋이 설치됐다고 가정하지 않는다.

## 실제로 구현된 것과 막힌 경계

| 경계 | 구현된 부분 | 즉시 실거래를 막는 구체적 부분 |
|---|---|---|
| 호가·계좌 조회 및 주문 부품 | Upbit 조회 collector, 호가·규칙 검증, `execution_orders/upbit.py:prepare/prepare_cancel/prepare_status`, IOC 주문 형식과 `Controller.reserve/dispatch/cancel/reconcile`가 있다. | 부품 존재가 실제 계좌 연결·주문 권한·운영 조립의 완료를 뜻하지 않는다. 이번 검사는 fake transport였다. |
| 앱 실행 경로 | `execution_launch/coordinator.py:Coordinator.__init__`가 계좌 provider·이력·Runner를 조립한다. | `mode == "rehearsal"`만 받으며 controlled는 `COORDINATOR_MODE_UNSUPPORTED`로 거절한다. `tools/owner/rehearsal.py:build_rehearsal`도 `DryRunAdapter`를 만들고 `held_positions_supported=False`를 보고한다. |
| 보유 자산의 연속 계좌 증거 | `execution_accounts/baseline_bridge.py:ContinuousAccountProvider.__call__`가 이전 상태에서 계좌 구간을 검증하고 checkpoint·독립 head를 전진시킨다. | 현재 공급자인 `execution_launch/account_interval.py:upbit_interval_frame`는 보유 종목이 있거나 직전 기준 이후 체결이 있으면 `ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED`로 거절한다. 따라서 첫 매수 뒤 그대로 사용할 수 없다. |
| 보유 중 가격·체결·수수료·입출금 경로 | `execution_accounts/continuous.py`의 path 기록/평가 및 `preview_continuous_upbit_interval`이 후보 증거를 검사한다. | 거래소 자료의 누락 없음, 공통 사건 순서, 마감 지점, 모든 관련 평가 변화에 대한 **실제 검증 어댑터**가 없다. 스냅샷·heartbeat·로컬 sequence·`VerifiedCoverage` 객체를 만든 것만으로 이 조건을 만족시키지 않는다. |
| 보유 계좌를 Controller로 전달 | `ContinuousUpbitCandidateSource.collect/latest`는 후보 자료를 수집·보관할 수 있다. | 같은 클래스의 `__call__`은 무조건 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`를 낸다. 아직 Controller용 계좌 provider가 아니다. |
| 위험 상태의 영속화·재시작 | `execution_launch/continuous_guard.py:plan_continuous_guard`와 `continuous_guard_commit.py:commit_continuous_guard/classify_restart`가 계산·단계별 commit·중단 분류를 구현한다. | 완전성/소유자 증거의 실제 인증 및 성공 후 account observation 발행이 연결되지 않았다. `Controller.observe`는 이미 journal transaction 안에서 provider를 호출한다. 기존 provider 안에 commit 함수를 단순 삽입하면 같은 journal을 중첩 진입한다. 조립 단계에서 journal→head/store 순서와 publish 시점을 함께 해결해야 한다. |
| 이력 용량 | P0a 객체 저장과 P0b 실제 v3 history·정책 해시·독립 head·재생 연결을 구현했다. 정상 호가·보유·유니버스 입력을 저장 용량 때문에 삭제하지 않는다. | 저장 단계 완료가 보유 관리·실거래 허가를 만들지는 않는다. 전체 회귀의 실행 가능한 검사는 완료했다. PR 정리와 실제 Windows 저장·시간 경계 검증은 구분해야 한다. |
| 보호 보유·매도 | 위험 gate, 중지 후 명시적 취소/매도 경로, 미체결·부분 체결 대조 부품이 있다. | PR35로 오류/저장 장애/재시작/E 만료 자체로 SELL을 만들지 않는 순수 보호 상태를 구현했다. 영속 복구·주문 실행과의 통합은 남았다. 현재 `execution_launch/driver.py:_validate_frame`에는 window end의 target=0 분기가 남아 있다. P0b에서 이 행동을 고쳤다고 보고하지 않는다. |
| 전략 연구·인증 | 기존 `study.py`의 고정 후보군 동결·전향 capture·선발, `study_review.py:authenticate_study_selection`의 원본 전체 재평가, Ed25519 연구 검토가 있다. | PR5 유니버스 연구 경로·정상 평가 실패 outcome·불변 연구 묶음/복구 및 새 승인 흐름은 후속 단계다. 실제 자료로 선정되고 현재 배포에 인증된 전략이 준비됐다는 증거는 없다. |
| 최종 활성화 | `execution_control/session.py:prepare_session/verify_session`은 현재 코드·규칙·계좌·기한·소유자 `session_armed`를 별도로 확인한다. Runner의 controlled 모드 부품도 있다. | 세션 준비는 활성화가 아니다. 운영 coordinator/planner/standing 관리 연결과 사용자 최종 승인·실제 세션 검증이 남았다. 연구 검토 승인만으로 거래 활성화되지 않는다. |

`execution_launch/live.py`, `planner.py`, `standing.py`라는 계획상의 운영 조립 파일은 이 확인 시점에 없다. 이는 주문 엔진이 전혀 없다는 뜻이 아니라, 검토된 부품을 실제 상시 운용 경로로 조립하는 단계가 남았다는 뜻이다. 지원 범위는 우선 **Upbit 원화 현물**이며 다른 시장·파생상품의 준비 완료로 확대하지 않는다.

## 사용자 입력 없이 계속할 개발

1. 완료한 P0b 전체 회귀·독립 검토의 실행 기록·PR 정리. 통과하지 않은 검사를 통과로 바꾸지 않는다.
2. PR4e 유니버스 coordinator 연결과 보호 보유 상태 전이: 판단에 따른 HOLD와 자료/프로그램 장애로 판단·주문 불가능한 상태를 구분한다.
3. 재시작 시 계좌·미체결·부분 체결·UNKNOWN 대조, 장애 복구, 가격·호가 깊이·체결 가능성을 고려한 매도 실행을 단계별로 검증한다. 마감 E 자체로 매도하거나 미응답으로 권한을 연장하지 않는다.
4. PR5 전체 후보군 outcome, 원본/작업본 분리, 불변 manifest·백업·복구, Telegram 진입·WebAuthn 승인 및 독립 신뢰 전환을 작은 단계로 구현한다.
5. 실제 완전성 source 계약의 근거를 정리하고, 인증 어댑터·위험 commit·provider 발행·controlled launcher/planner/standing 연결을 구현·검증한다. 증명하지 못한 자료 완전성을 `complete=True`로 대신 채우지 않는다.
6. PLB·시계 허용치 및 최종 코드 폐쇄 검증을 후속 의존 순서에 맞춰 마친다. 새 연구의 전향 관측 시간은 기존 합성 데이터나 과거 테스트 결과로 대체하지 않는다.

## 나중에 소유자 쪽에서 필요한 것

현재 개발을 멈추고 아래를 한꺼번에 요구하지 않는다. 실제 적용 시점에만 필요한 절차를 안내한다.

- **PLB 상태 결정 전:** 사용자 PC에서 아직 미실행인 `floor_state_check`의 S1~S12 결과. 실제 보호 하한·halt 기록을 모르므로 기존 상태를 완화해야 하는 기능이 필요한지 가정하지 않는다. 공유할 것은 결과 코드이며 금액·개인 경로·키가 아니다.
- **실제 설치·등록 전:** 동기화 폴더 밖 확정본 위치, 별도 버전 백업 위치, 고정 HTTPS 승인 도메인/RP ID, 독립 최초 신뢰·복구 수단의 실제 상태. 미정인 동안 fixture·계약·UI 개발은 가능하다.
- **실계좌 연결 전:** 사용자 로컬의 계좌/API 권한·계정 일치 및 운영 환경 설정. 키를 채팅이나 공개 저장소에 올리지 않는다. 실제 연결 검사를 했다는 증거가 아직 없다.
- **최종 사용 전:** 최종 배포 코드, 규칙·한도, 실제 연구 검토, 해당 거래 세션 활성화를 각각 그 범위로 승인한다. 기존 발효일·손실 보호·halt를 유지한다. 본 대화의 개발 승인은 실거래 활성화나 실제 주문 승인이 아니다.

계좌 연결 성공, 코드 회귀 통과, 연구 통과, 사용자 서명, 세션 활성화는 서로 다른 완료 조건이다. 지금 확인된 것은 P0b 개발·집중 회귀 단계이며 이 조건들이 모두 충족된 상태가 아니다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.

최종 저장 단계 상태: PR34 병합 완료, main `86c9e94bcd3fedbbe3d7879d66786ec1590d1b74`. 병합 tree와 검증된 문서 head062c127의 tree가 일치한다. P1 순수 보호 상태 전이는 PR35로 구현·106개 검사·병합을 완료했다. 실주문 경로 연결은 아직이다.

최신 main: `6030fe3063dc6b63eeaad48b3d818577f1c1219b` (PR35). 전체 현황은 `TRADEGEN_STATUS_2026-11-13.md` 참조.
