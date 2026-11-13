# TRADEGEN 보호 보유: 다음 최소 구현 단계

2026-11-13. 읽기 기준: `/workspace/tradegen-bundle-attestation-1113`, HEAD `3ca4dee`에 포함된 carry-v2·P2-store·연속 guard 코드. B1b 작업 중인 파일은 수정하지 않았다. 이 문서는 구현 계획이며 실제 계좌 연결·운영 가능 판정이나 새 거래 권한이 아니다.

## 결론

다음 단위는 **P2-integration/commit-before-publication**으로 한정한다. 연속 guard를 먼저 확정하고, 그 확정된 관측만 Controller에 제공하는 연결부를 구현한다. 기존 account provider 안에 guard commit을 삽입하지 않는다. 이 연결부의 합성 자료 검증은 바로 진행할 수 있다. 실제 보유 계좌 운용에는 아래의 진짜 source coverage·owner/control 인증과 관리 권한이 여전히 필요하다.

현재 Coordinator는 `mode == "rehearsal"`만 허용한다. 이 제한과 `ContinuousUpbitCandidateSource.__call__()`의 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`를 이번 저장·공개 연결 검사만으로 풀지 않는다.

## 실제 코드에서 확인한 연결 장애

| 위치 | 현재 동작 | 다음 구현에서 필요한 처리 |
|---|---|---|
| `execution_control/controller.py:457`, `:376`; `execution_control/store.py:257` | `observe → journal.transaction → account_provider` 순서. 중첩 transaction은 명시적으로 거절한다. | provider가 `commit_continuous_guard`를 호출하면 그 함수도 transaction을 열어 실패한다. commit은 Coordinator 작업 잠금 안, Controller 호출 밖에서 수행한다. provider는 journal을 열지 않는다. |
| `execution_launch/coordinator.py:566`; `execution_accounts/baseline_bridge.py:130` | board에 먼저 frame을 놓고 기존 provider가 baseline을 advance/commit한다. | guard commit이 이미 baseline을 옮긴 뒤 이 provider를 재사용하지 않는다. 확정된 state+account를 재조정하는 읽기 전용 경로가 필요하다. 공개 횟수·ready 상태도 확정 후 증가시킨다. |
| `execution_launch/continuous_guard_commit.py:314` | prepare → 필요한 halt → baseline CAS → guard CAS → complete → heads 재확인. receipt는 권한이 아니다. | 모든 단계 및 현재 predecessor 확인이 끝나기 전 관측을 공개하지 않는다. 공개 직전/Controller 소비 시 변경된 owner·code·control context를 거절한다. |
| `execution_launch/continuous_guard.py:459`; `execution_control/controller.py:410` | guard는 적용 하한·최고점·일중 정지를 따로 보존한다. Controller는 기존 risk_snapshot과 관측을 사용한다. | endpoint baseline만 전달하지 않는다. 확정 guard의 retained floor/high/daily loss/halt와 당일 daily-stop을 현재 Controller 검사에 반영한다. 전날 left-limit 사건은 해당 일자 기록으로 보존하고 risk_snapshot을 소급 작성하지 않는다. |
| `execution_launch/account_interval.py:233`, `:411` | staged candidate는 preview, path/manifest digest, time만 반환한다. | 원래 captured_accounts·원본 receipt와 first_received_at·endpoint 재구성 근거·pre/post owner context가 guard 검증까지 필요하다. preview나 digest만으로 이를 재창작하지 않는다. |

첫 장애는 이미 `tests/control_continuous_guard_commit.py:391`에서 직접 중첩 거절을 검증한다. 이것은 현재 동작의 오류가 아니라 새 연결을 잘못 넣을 경우의 재현 가능한 장애다.

## 사용자 입력 없이 먼저 구현할 범위

1. **확정 상태 투영 함수와 비갱신 provider.** `baseline_bridge.py`에 기존 확정 BaselineState와 정확한 account evidence를 재조정하는 공용 함수를 추가한다. 내부 `_reconcile` 계약을 재사용하되 `advance_baseline`, store commit, CAS, journal 호출은 하지 않는다. 새 guard 연결 모듈에서 이를 확정 GuardCheckpoint에 결합한다. risk projection은 하한/최고점/일중 손실/영구 halt를 낮추지 않고, daily-stop을 별도 의미로 유지한다. 이 투영 결과만으로 source 인증을 주장하지 않는다.
2. **저장과 공개를 분리한 연결부.** 새 모듈 예: `execution_launch/continuous_guard_bridge.py`. Coordinator가 이미 수집·인증한 한 묶음과 예상 세 head를 받아 기존 commit 함수를 호출한다. 완료 receipt 및 실제 두 store/head, 정확한 account/package 결합을 재검증한 뒤 한 번만 공개한다. 실패하면 board·현재 관측을 비우며 이전 관측을 새 시각으로 재사용하지 않는다. 기존 flat 경로는 유지한다.
3. **Controller 소비 경계.** 실행 시 이미 열려 있는 journal transaction의 실제 events를 이용해 guard 완료/일치와 retained latches를 검사할 좁은 내부 경계를 만든다. 이 내부 경계는 journal.snapshot/transaction을 다시 열지 않는다. guard receipt의 control head는 검증된 완료 prefix에 결합하고, 그 뒤 행은 현재 이력으로 다시 fold한다. 매 호출마다 journal 끝이 과거 receipt head와 같아야 한다고 요구하면 정상적인 후속 risk_snapshot도 거절하므로 그렇게 구현하지 않는다. 실제 events의 최신 owner/control 위험 이력과 대조하므로, commit 뒤 D12·halt·kill·주문 변화가 생겨도 오래된 관측이 그 변화를 덮지 않는다. 필요한 새로운 현재-day latch 계약은 구현 전에 고정한다.
4. **실제 구성요소 회귀.** 기존 GuardCheckpointStore/CheckpointStore/head/Journal/Controller를 임시 홈에서 조합한다. 데이터·owner·coverage 공급자는 명시적인 시험용 fixture이며, 운영 issuer나 승인으로 부르지 않는다. 이 단계에는 실제 어댑터 dispatch나 controlled 모드 추가가 없다.
5. **P2 저장 연결은 그 다음 작은 단위.** guard·account·control의 확정된 참조를 바탕으로 P2 restart/대조 결과를 기록한다. P2 writer를 먼저 닫고 Controller 일을 수행하는 순서를 유지한다. 자료가 부족하면 `authority=None`, 확인하지 못한 ledger ref는 None, recovery_complete는 미확인으로 둔다. 계좌/주문 대조 없이 recovering을 해제하지 않는다.

권장 단일 소유 분할: bridge+baseline helper / Controller 내부 소비 계약 / Coordinator 연결 / 독립 회귀. 공용 API를 먼저 고정하고 한 파일을 두 명이 동시에 수정하지 않는다. 새 source closure와 독립 signer의 코드 해시 범위도 변경된 실제 의존성에 맞춰 갱신한다. 기존 서명으로 수정된 코드를 승인한 것으로 취급하지 않는다.

## 실제 보유 source로 넘어가기 전 필요한 것

- `execution_accounts/continuous.py:1`의 계약은 **모든 valuation mark와 fill의 공통 순서, 누락 없는 구간, opening mark, closing watermark**다. 현재 Upbit sampled book·trade ID·heartbeat·로컬 sequence로 이 계약이 성립한다는 근거는 없다. 검증자 production 구현도 없다. 새 `VerifiedCoverage(...)`, `complete=True`, 해시 복사, 임의 callback을 실제 증거로 승격하지 않는다.
- 인증된 stage는 원래 수집 자료와 receipt를 보존하고, 정확한 captured/endpoint 계좌와 first-receipt 시각을 결합해야 한다. 연속 archive는 현재 path 감사 사본이며 원본 수집 묶음·owner 인증을 대신하지 않는다.
- 현재 owner/code/효력 발생 한도를 수집 전후·commit 시점에 실제 검증해야 한다. 같은 owner head라도 자정에 예약 한도가 바뀔 수 있다. 현 guard는 변경 timeline을 구현하지 않았으므로 변경을 감지하면 거절한다.
- guard의 초기 anchor는 실제 Controller의 적용 하한·최고점·daily-stop·permanent-halt·journal head와 일치해야 한다. 잔고나 원래 profile floor에서 자동 seed/re-anchor하지 않는다.
- 실제 source가 요구한 완전성·시간 경계를 제공할 수 있는지 먼저 문서와 코드로 확인한다. 근거가 없으면 candidate 수집·감사까지만 구현 완료로 표시한다. 가격 표본이 정상이라는 이유로 손실 규칙을 완화하거나 감시가 완전하다고 표시하지 않는다.

## E 이후 관리 권한은 별도 선행 조건

`protective_state.AuthorityFacts`와 `ObservationFacts`는 누구나 구성 가능한 모델 입력이다. P2 outbox의 `consider_reduce` 역시 주문 권한이 아니다. 실제 verifier/issuer가 코드·연구·계좌/종목·evidence·scope·현재 시각·만료·폐기를 검증해야 한다. monitor/reduce/cancel/entry는 분리하며 기존 연구 검토 승인이나 archive attestation을 관리 승인으로 재사용하지 않는다.

또한 **관리 서명 하나만 추가하면 기존 fixed driver가 E 뒤에 계속 계산되는 구조가 아니다.** `LiveHistory._slot_time`은 E 뒤 slot을 거절하고 `driver._validate_frame`도 원래 window에 결합된다. post-E 전략 감시에는 새 관리 평가 기간·원본 history 연결·명시적인 새 revision이 필요하다. 기존 E gate나 만료 시각만 바꾸는 우회는 하지 않는다.

자동 감소 실행의 다음 단위는 실제 미체결/체결/수수료/잔량 대조 → fresh risk·시장자료 → 독립 매도 원인 → 현 권한 → reserve/dispatch 직전 재검증 → attempt/outbox 처리 순서다. queued/reserved/dispatching/unknown/partial/cancel_requested 및 늦은 기존 GTC 체결 모두 중복 방지에 포함한다. 기한·저장 장애·재시작은 매도 원인이 아니다. fixed GTC를 IOC로 바꾸거나 시장가 fallback을 추가하는 결정은 이 연결 범위에 넣지 않는다.

## 최소 완료 검증

- Controller.observe/reserve/dispatch 경로에서 중첩 journal 진입 0; provider의 baseline 재commit 0.
- prepare/halt/baseline CAS/guard CAS/complete/readback 각각 실패 시 공개 0; 정확한 package 재실행만 수렴.
- 두 head 일치하더라도 completion·store 내용·package·현재 owner/control 결합 불일치면 공개 0.
- intrainterval peak 후 회복한 endpoint에서 보호 하한/영구 halt/당일 stop이 사라지지 않음; 자정 이전 위반 기록 보존.
- 공개 후 control halt/kill/owner-limit/code 변경은 Controller에서 다시 적용 또는 거절; stale cached 관측 재시각화 0.
- 부분 체결·계좌와 미체결 불일치·재시작 중에는 신규 진입 차단, 검증 없는 recovery_complete 0.
- 보유 후보 fixture가 통과해도 production source/issuer 없는 controlled 실행 0.
- E 도달·HOLD·unavailable·저장 오류만으로 신규 매도 0; 기존 주문의 뒤늦은 체결은 별도 대조.

이번 결과는 **코드 읽기와 구현 계획**이다. 새 runtime 검사는 실행하지 않았다. 실계좌·키·실제 홈·거래소 API·무장·주문에 접근하지 않았다. 기존 손실 하한·위험정책 변경 없음. 법률·세무·투자 조언이 아니며 면허를 가진 자문가가 아니다.
