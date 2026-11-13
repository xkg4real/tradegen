# P2 after I3b — 다음 최소 실행 경계 보완

2026-11-13. 읽기 기준은 PR50 병합 `d21ffaa10c0115d313d675433acff2c093313f47`다. 조사 worktree `874e9a9`와 해당 main의 execution_launch / execution_control / execution_accounts 소스 diff가 없음을 확인했다. 이 문서는 **설계만**이며 코드 수정·검사 실행·실계좌 연결·승인·주문 기록이 아니다.

추천은 **I3c-time: 기존 Controller가 확정 계좌를 소비할 때, 느린 검증·주문 준비·DISPATCHING 기록 뒤의 실제 완료 시각과 현재 owner를 다시 검사하는 작은 수직 단계**다. 새 허가 엔진이나 저장 엔진을 만들지 않는다. 현재 존재하는 실제 Controller → 기존 gate/session/capability → DryRunAdapter 경로에서 검증할 수 있고, source completeness를 발급한 척할 필요가 없다.

이 단위를 마쳐도 앱 실행만으로 연속 보유 계좌 자동매매를 시작할 수 없다. 현재 생산 Upbit 연속 자료 인증 계약, 당시 owner 관찰, guard commit/publication 및 Runner 연결이 없다는 차단은 그대로 남는다. **현재 정보만으로 새로운 controlled 조합을 정당하게 열 수 있는 단위는 없다.** 그와 별개로 기존 주문 경로의 구체적인 시간 경계 결함은 개발·검증할 수 있다.

## 1. 현재 실제 경계

| 근거 | 구현된 기능 | 아직 없는 기능 |
|---|---|---|
| `guard_capture_format.py`, `guard_capture_archive.py` | I3a 전체 typed stage·이전 baseline·모든 원 응답을 실제 BundleStore primary/backup/catalog/head와 연결. 새 reader로 actual collector/material 역사 감사 | source authenticity/current freshness/guard committed/execution ready는 모두 false. 원 자료 없는 중단 수집을 복원하지 않음 |
| `guard_capture_material.py:prepare_guard_capture_material` | 원 receipt 순서/요청/시각을 실제 collector로 재소비, captured/endpoint 및 path/FIFO/fees를 재도출 | 입력 `now`의 실제성, 생산 coverage issuer, current owner 인증을 발급하지 않음 |
| `continuous_guard.py:plan_continuous_guard` | 기존 floor/high/daily/permanent halt를 시간 순서대로 계산 | OwnerContextClaim/VerifiedCoverage의 실제 진위를 자체 발급하지 않음 |
| `continuous_guard_commit.py:commit_continuous_guard` | Journal PREPARE→halt→baseline/head→guard/head→COMPLETE, 동일 package 중단 재시도 | package 출처 인증, full package 재시작 자료, holder publication 없음 |
| `committed_account.py:CommittedAccountProvider.read` | 실제 같은 열린 Journal tx·두 store/head·완료 및 suffix·원 package 대조, 별도 daily-stop 보존 | noncallable이며 인증된 source/owner claim producer가 아님 |
| `execution_control/controller.py:_account/_committed_context` | exact committed provider 소비, actual owner.load_context의 seal/hash/code/head/효력 한도 비교 | Controller가 받은 `now`가 실제 작업 완료 시각인지 자체 재검증하지 않음 |
| `controller.py:_authorize/reserve/dispatch/_send` | 기존 risk/gate/session·용량 검증, 실제 예약/전송중 기록, 단 한 번의 capability 발급/adapter dispatch | `_authorize` 이후 느린 adapter.prepare·fsync 동안 경과한 시간을 새로 확인하지 않음 |
| `execution_orders/transport.py:dispatch` | capability 소비 뒤 명시 credentials provider, wire 서명, 단 한 번 HTTP `_send` | credentials/_wire가 지연돼도 별도 최신 clock 검사 없음. Controller 개선만으로 실제 소켓 send 시각까지 원자적으로 보장할 수 없음 |
| `runner.py`, `coordinator.py` | legacy callable account provider와 rehearsal 조합. carry actual E gate는 Runner/Coordinator 단계에 존재 | Runner는 committed noncallable reader를 받을 수 없고 Coordinator는 기존 frame→provider advance 경로. `COORDINATOR_MODE_UNSUPPORTED`, `RUNNER_CARRY_CONTROLLED_UNSUPPORTED`, candidate `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED` 유지 |

I3b 실제 기록은 관련 **161 PASS / 0 FAIL / 0 NOT_RUN, 34.278초**다. 현재 문서 작성에서 검사를 새로 수행한 것이 아니며, 그 결과는 아래 미구현 시간 경계를 검증하지 않는다. 새 reader 검사는 OS 강제 종료나 Windows 전원 장애 시험과 다르다.

## 2. 개발만으로 구현할 한 단위: I3c-time

### 파일과 API

생산 변경은 `execution_control/controller.py`에 한정한다. 새 `tests/control_committed_completion.py`와 기존 `tests/control_committed_account.py` fixture의 명시 clock 입력을 추가한다. Runner/Coordinator/transport 및 deadline wire 변경은 이번 단위에서 제외한다. 필요하면 기존 control guard의 정확한 호출 경계 검사만 갱신한다. capability.py, owner.py, gate.py, session.py, 저장 codecs의 의미를 바꾸거나 새 permission registry를 만들지 않는다.

제안 API:

```python
Controller(..., clock=None)
# legacy callable provider는 기존 API 유지.
# exact CommittedAccountProvider를 사용하는 경로는 명시 callable clock 필수.
# clock은 signed composition의 의존성이지 source/owner 권한이나 영구 lease가 아니다.

# public observe/reserve/dispatch의 now는 기존 호출 계약으로 유지.
# committed 경로에서는 내부 clock 관찰보다 미래인 now를 거절하고,
# caller now만으로 freshness 검사를 통과시키지 않는다.
# private helper names finalized in implementation card:
_started_committed_boundary(...)       # private operation-local original evidence
_recheck_committed_boundary(...)       # actual tx/owner checks, no new authority
_finish_committed_boundary(...)        # last clock + finite comparisons
```

이번 단위는 reserved/dispatching wire keyset, session 형식, 기존 legacy callable API를 바꾸지 않는다. exact committed fixture에서만 실제/가상 trusted clock을 명시한다. 새 production 조합을 여는 callsite는 없다. 현재 carry Runner/Coordinator는 legacy provider 경로이므로 이 보완을 자동 적용받는다고 주장하지 않는다.

Controller에는 실제 carry E가 전달·보존되어 있지 않다. 따라서 이번 단위는 **E 후 전송 차단을 완료하지 않는다.** 향후 E를 하위 경계까지 보장하려면 actual issued driver의 E를 Runner→예약 기록→dispatch에 완화 불가 제한으로 연결하는 별도 계약이 필요하다. caller의 임의 datetime이나 연구의 과거 종료시각으로 대신하지 않는다. 현재 carry controlled/Coordinator gate가 닫힌 상태를 유지하며, 그 연결 전에 새 조합을 활성화하지 않는다.

첫 범위는 observe/reserve/create dispatch다. kill/halt의 보수적 지속 동작, 알려진 주문 cancel/reconcile, legacy callable 동작은 현재 계약을 유지한다. 특히 owner 불가를 이유로 kill/halt가 실패하거나 모든 reducing sell이 막히도록 바꾸지 않는다. 기존 daily stop/kill 아래 독립적으로 허용된 reducing 주문은 같은 현재 data/owner 검증을 통과하면 계속 허용한다.

### 실제 처리 순서

1. exact committed 경로의 operation 시작에 내부 clock을 읽는다. aware/finite range, 이전 내부 관찰 및 Journal 마지막 trusted 시각에 대한 rollback을 검사한다. 원 account.asof/server_time/risk.asof, 원 claim.observed_at, 최초 현재 owner 조회 시작시각은 별도로 유지한다. 뒤의 새 clock으로 옛 자료 시각을 덮지 않는다.
2. 기존 `_account`가 실제 열린 tx로 holder를 읽고, `_positions`로 같은 operation/session의 positions를 만든 뒤 actual `owner.load_context`를 호출한다. `_committed_context`, 기존 위험·용량·instrument/session/gate 검사를 재사용한다. Context나 `fresh=True`를 caller가 넣는 API를 만들지 않는다.
3. reserve는 adapter.prepare와 request 검증 **후** owner·committed head를 다시 확인하고, 마지막 clock으로 original evidence의 나이를 검사한 뒤만 기존 reserved row를 쓴다. append가 길어졌다면 반환 직전 검사에서 오래된 결과를 성공 예약처럼 제시하지 않는다. 이미 기록된 RESERVED를 지우거나 새 ID로 재시도하지 않으며, 이후 dispatch는 별도의 전체 검증을 거친다.
4. dispatch는 기존 request/issued permit 검증 후 DISPATCHING을 실제로 기록한다. 그 느린 append까지 끝난 뒤 같은 열린 tx에서 committed reader를 다시 읽고 actual current owner를 다시 관찰한다. 원 request/permit/session과 비교하고, 모든 무거운 읽기·hash·검증 뒤에 마지막 clock을 읽는다. 그 검사가 통과해야 `_send`/기존 `_issue`를 호출한다.
5. 새 helper가 기존 `_authorize` 전체를 DISPATCHING 뒤에 무작정 재호출해서는 안 된다. 자신의 DISPATCHING을 타 주문 불확실성으로 오인하거나 risk snapshot/permit을 무의미하게 재발급할 수 있다. `_account`, `_capacity`, `_positions`, `_committed_context`, `_intent`, `_exact_caps`, 실제 `gate.verify_permit`와 `verify_session`의 기존 검사를 재사용하는 private read-only 재검증 부분을 분리한다. 현재 risk 계산을 복제하지 않는다.
6. 시간에 따라 위험정책 의미가 바뀌는 22시·서울 날짜 경계를 넘으면 이전 risk 판단을 재사용하지 않는다. 첫 단계는 그 operation을 거절하고 새 정상 관측을 요구하는 보수적인 경계로 제한할 수 있다. 기존 risk reducer가 이미 계산한 floor/high/daily stop을 줄이거나 다른 예산을 가정하지 않는다. 다음 정상 operation은 기존 위험 계산을 실제 해당 시각에 수행한다.
7. 최종 clock 비교는 원 계좌 30초, server 60초 및 같은 서울 날짜, 원 owner/claim 관찰 나이, 현재 instrument rule 유효성, actual PreparedSession expiry와 날짜를 포함한다. equality는 기존 계약을 유지한다(account 30초 포함, session expires_at 미포함). 비교 후 새로운 무거운 작업을 삽입하지 않는다. carry E의 별도 관리 권한을 만들지 않으며 controlled carry 거절은 유지한다.
8. private phase proof는 같은 실제 활성 tx에서 방금 기록한 DISPATCHING row의 전체 digest/client/request/permit/이전 head와 마지막 row 위치를 보관한다. 실제 tx tail이 달라졌거나 다른 unknown/dispatching 주문이 있는 경우 이 proof로 예외 처리하지 않는다. 동일 주문의 방금 쓴 row만 phase 확인에 쓰며 일반 `_authorize`의 불확실 주문 검사를 완화하지 않는다.
9. 그 phase에서 최종 재검증이 거절되고 **같은 정상 실제 tx + 정확한 자신의 DISPATCHING row + `_send`/adapter 진입 전임을 보장하는 private 제어흐름**이 모두 남아 있으면, 확실한 no-send다. trusted clock이 유효할 때 기존 `_result`에 `AdapterResult(status='rejected', code='local_pre_send_boundary_refused', venue_order_id='', metadata=(...))`를 전달해 기존 REJECTED 전이를 기록한다. metadata는 `tg_local_pre_send=not_called`, `tg_local_reason=<고정 코드>`, `tg_dispatch_row=<원 row hash>`로 제한한다. 이는 거래소가 거절했다고 주장하지 않는 **로컬 전송 전 거절**이다. 실제 HTTP/capability=0이고 exact row를 성공 기록한 경우에만 예약 해제가 정당하다. 동일 client는 기존 terminal 기록을 반환하므로 재전송하지 않는다. `_result`가 code를 저널에 저장하지 않으므로 provenance를 metadata에 남기는 것이 필수다.
10. phase proof가 불명확하거나 adapter에 이미 진입했거나 거절 row 기록/cleanup이 실패하면 로컬 REJECTED를 확정했다고 반환하지 않는다. clock 자체가 불확실할 때 옛 시각을 현재 기록 시각으로 꾸며 row를 쓰지 않는다. 마지막 확정 DISPATCHING/UNKNOWN 또는 torn journal을 보존하고 기존 불확실 상태와 재시작 대조로 처리한다. 단순 편의 때문에 확실한 no-send까지 UNKNOWN으로 만들지 않지만, 불확실한 경우에는 예약을 풀지 않는다.
11. 원본을 자르거나 RESERVED로 되돌리지 않고 재시작에서 create를 자동 재전송하지 않는다. 같은 프로세스가 실패를 삼키고 다시 dispatch해도 기존 상태 검사가 send를 막아야 한다. 실제 대조·정리는 기존 reconcile/owner 경로의 책임이다.

원자적 경계는 ‘같은 actual Journal tx의 확정 DISPATCHING 확인 + 최종 검사 통과 뒤에만 capability 발급’이다. 독립 owner 파일/시장/네트워크까지 하나의 원자적 잠금이라고 주장하지 않는다. 마지막 clock은 최초 관찰뿐 아니라 작업 중 모든 trusted completion 이상이어야 한다. rollback 때 마지막 trusted 시각을 앞으로 덮지 않는다.

이 변화는 처리 완료 시점의 한 번의 관찰이다. 다른 프로세스 owner 변경을 잠그는 lease가 아니다. 특히 Transport의 credentials provider·`_wire`·네트워크 경계는 이후의 실제 write boundary 과업이다. 다음 transport 작업은 기존 한 번 소비하는 capability 계약을 확장할지 검토할 수 있으나, 이번 단계에서 별도 허가 엔진·임의 TTL·권한 bool을 만들지 않는다. **I3c-time 완료 보고는 ‘Controller capability 발급 전의 실제 완료 재검증’으로 한정하며 ‘거래소 전송 순간 신선도 보장’이라고 쓰지 않는다.**

### 의미 있는 회귀 검사

기존 실제 임시 서명 owner log, 실제 BaselineHead/CheckpointStore/GuardCheckpointStore/Journal·실제 commit·CommittedAccountProvider를 사용한다. 계좌·연속 path/coverage는 합성임을 명시한다. 실제 DryRunAdapter가 기존 capability를 소비하되 실제 API·키·계좌·주문은 사용하지 않는다.

- 느린 provider.read, owner.load_context, adapter.prepare 각각에서 30초 초과, 경계 +1µs, rollback/미래/naive clock. 원 시각을 유지하고 reserve/create가 새로 나가지 않는지 확인한다.
- DISPATCHING append/fsync hook에서 시간을 넘기는 실제 저널 경로: 원 row 보존, exact no-send proof+정상 기록 시 fixed local-no-send REJECTED, capability/create=0, 다음 dispatch도 자동 재전송하지 않음. 거절 append 실패·torn tail·clock 불가에는 terminal을 확정하지 않고 마지막 DISPATCHING을 지우지 않음. 실패를 잡은 후 caller가 같은 now를 다시 써도 우회 불가.
- 마지막 actual owner 조회·서명 검증이 오래 걸리는 경우: 완료clock을 반드시 그 **후** 읽고 최초 관찰 나이를 유지한다. 나이 기준을 마지막 조회 시작시각으로 갈아끼우지 않음.
- adapter.prepare 중 실제 임시 owner log의 code 승인/owner head/효력 한도/세션을 바꾼 뒤 final read가 거절. 같은 head에서도 서울 자정/세션 한도 효력이 달라지는 기존 사례를 보존.
- 계좌/head가 final 재읽기 중 바뀌면 거절. 유효 control suffix를 단순 head 동일성 때문에 전부 거절하지 않고 기존 committed reader prefix 규칙 사용.
- local rejected 결과는 실제 adapter 거절과 metadata로 구분하고, known no-send 예약 해제/동일 client 재전송0을 확인한다. 반대로 _send 진입/phase 불명확/거절 기록 실패에는 예약을 해제하지 않는다.
- 기존 22시·자정 정책 boundary 및 actual session expiry를 넘는 작업 거절. source observed_at/server_time, baseline.asof를 완료 시각으로 relabel하지 않음. owner 동일 head만 비교하지 않고 현재 effective limits/day/session과 retained key/code/prefix 경계를 유지.
- 정상 fresh 실제 reducing dry create는 정확히 한 번; daily stop/kill이 독립적으로 허용된 reduce를 일괄 차단하지 않음. 기존 hard halt/owner 금지와 gate 조건은 유지.
- 전후 baseline/guard head·state는 불변. 새 advance/commit/CAS/Journal 중첩획득/owner 서명/auto seed 호출=0. 기존 위험 snapshot/보호 latch 기록은 보수적으로 보존.
- legacy callable Controller 회귀, reserved local cancel·known cancel/reconcile·kill/halt 회귀 및 source-integrity/carry/Coordinator 거절 유지.

현재 positive buy fixture에 실제 PreparedSession이 필요하면 기존 session 발급 경로를 사용한다. dataclass·registry 삽입·`armed=True` 입력으로 양성 사례를 꾸미지 않는다. 필요한 existing issuer 경로를 범위 안에서 재사용할 수 없다면 해당 양성 사례를 미검증으로 남기고 genuine reducing 양성+실제 부정 경계를 검증한다.

## 3. 실제 외부 계약·운영 설정이 필요한 부분

아래는 codec/테스트 fixture를 더 만드는 것으로 충족되지 않는다. 사용자에게 이미 정한 정책을 다시 묻는 항목도 아니다.

- **계좌·venue 출처 계약:** 같은 account scope/credential binding, origin 이후 order/fill/transfer/fee 이력 보존, 누락 페이지 및 동시 manual/API 활동의 의미. REST 양끝 잔고 일치만으로 중간 ABA·체결 누락이 없었다고 인증할 수 없다.
- **연속 자료 완전성:** 실제 Upbit sequence/gap/reconnect/watermark가 어떤 관찰 구간과 자산을 보증하는지와 독립 verifier/운영 책임. 로컬 recorder seq, heartbeat, 해시, VerifiedCoverage 콜백 성공은 이를 대신하지 않는다. 지원 가능한 실제 공급 계약이 없다면 현재의 강한 연속 extrema 계약으로 controlled를 열 수 없다.
- **운영 owner 관찰:** 실제 positions/session으로 owner.load_context를 수행하는 composition과 기록된 원 시각. `owner_before <= path.start` 조건을 충족하는 관찰은 recorder 시작 전 실제로 있어야 한다. 나중에 읽은 Context를 과거 관찰로 재작성할 수 없다. review용 CurrentOwnerAuthority의 placeholder positions를 trading issuer로 바꿔 쓰지 않는다.
- **현재 predecessor/저장 환경:** 실제 baseline/guard/control 독립 heads와 reviewed anchor, 비동기화 primary/backup 위치·용량·head 설정, 재시작/동시 실행 정책. I3b packet 속 과거 baseline은 현재 trusted head가 아니다. 같은 장치의 두 directory를 물리적 독립 백업이라고 주장하지 않는다.
- **개별 승인/설정:** 현재 code·rules/limits·전략 검토·실거래 활성화 scope, 실제 거래 대상·계좌·권한·provider 설정은 해당 owner 경로에서 유효해야 한다. 현재 미실행인 소유자 PC floor_state_check의 S1–S12는 운영에서 확인해야 하며 결과를 가정하거나 기록 하한을 몰래 바꿀 수 없다. 실키는 로컬 운영 설정에만 있고 채팅/공개 저장소로 전달하지 않는다.

이 중 source 계약 확인 전에도 I3c-time, full guard package의 재시작 표현 설계, commit→holder publication의 lock-order/세대 전이 테스트, Runner의 exact committed read 경계 구현 준비는 가능하다. 이들은 현재 controlled 거절 해제의 증거가 아니다. 실제 production source를 정하지 않고 generic auth token을 추가하는 작업은 추천하지 않는다.

## 4. 시장에 대해 보장할 수 없는 것

기존 원금·최고점 보호 하한, 하루 손실 예산과 22시 회복 기준은 소프트웨어의 주문 admission·감시·보호정책으로 그대로 유지한다. 손실 허용치를 낮추거나 확대하는 제안이 아니다.

그 정책이 있어도 시장 gap, 거래 정지, 체결 지연/거절, 유동성 부족, 비용·부분 체결, 통신 단절 때문에 실제 평가액·실현손익이 하한을 절대 침범하지 않는다는 보장은 만들 수 없다. 관측되지 않은 순간의 모든 가격을 완전하다고 사후 증명할 수도 없다. 하루 최소 목표 수익이나 특정일까지의 순수익은 검증·추정할 목표이며 실행 프로그램이 확정 결과로 보장할 수 없다. 양성 테스트·과거 수익률·전자서명은 그 보장의 대체물이 아니다.

이 문서에는 새 승인 질문이 없다. 개발 권한은 기존 계속 진행 지시에 따르며, 제안한 한 단위의 실제 구현은 별도 작업 배정·검증 기록으로만 완료 표시한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
