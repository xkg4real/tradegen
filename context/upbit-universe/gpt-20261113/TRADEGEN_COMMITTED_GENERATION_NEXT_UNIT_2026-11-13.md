# TRADEGEN: 다음 확정 계좌 세대 게시 단위

작성: 2026-11-13. 읽기 기준: `/workspace/tradegen-committed-runner-1113`, HEAD `2a6cc2cd67dc93363b95aa9a3cdda2a18ee6d1be`의 I3d 소스. 이 문서는 다음 구현 계약 제안이며 구현·검사 완료 보고가 아니다. 실행 중인 검증 트리, 소유자 홈, 계좌, 키, API는 변경하거나 사용하지 않았다.

## 1. 현재 가능한 것과 정확한 빈틈

- `execution_launch/committed_account.py::CommittedAccountProvider.__init__`는 한 package와 receipt를 깊게 복사한다. `read(now, transaction)`는 실제 활성 Journal transaction, PREPARE/COMPLETE, 원 package 해시, 현재 guard/baseline stores와 독립 heads를 대조한다. 이미 확정한 baseline을 대조할 뿐 다시 advance/commit/CAS하지 않는다. 실제 heads가 다음 세대로 이동하면 이전 provider는 정상적으로 거절한다.
- `Controller.__init__/_account`와 `Runner.__init__/_controller_boundary`는 같은 exact provider 객체를 고정한다. 새 provider 객체로 대입하거나 lambda로 observation만 꺼내는 방법은 연결 방법이 아니다.
- **작업 안의 세대 고정은 이미 있다.** `Controller._completion_owner`는 첫 실제 `frame.read`의 transaction_id, guard/baseline/completion/receipt heads, policy/claim/day를 뒤의 실제 read와 비교한다. `_completion_recheck`의 현재 소스에 이를 또 다른 허가 토큰으로 복제할 필요는 없다.
- 반면 Runner의 `observe_committed` 또는 `read_committed_account` → 전략/호가 처리 → `reserve` → `dispatch`는 서로 다른 Journal transaction이다. 같은 객체 내부의 세대 교체를 허용하면 이 경계도 연결해야 한다. 현재 공급자 identity 검사만으로 처음 전략이 사용한 세대와 마지막 주문 판단의 세대가 같다는 사실까지 확인하지는 못한다.
- `Coordinator._publish`는 기존 board 게시 뒤 `ContinuousAccountProvider.__call__`을 호출한다. 후자는 baseline을 advance/commit/CAS할 수 있다. guard가 이미 확정한 값을 이 경로에 다시 넣으면 안 된다. 현 Coordinator를 다음 단계의 게시자로 간주하지 않는다.

## 2. 최소 구현 범위: 같은 provider에 검증된 직접 후속 세대 게시

기존 constructor/read와 exact 객체 identity를 유지하고, 내부 package/receipt/기대 predecessor 묶음만 하나의 private immutable generation으로 추출한다. 외부 package 변경이나 반환 projection 수정으로 내부 세대가 달라지지 않도록 기존 복사·해시·재읽기 검사를 보존한다. 생성자와 generation 자체는 source 인증이나 주문 허가가 아니다.

아래 메서드는 **아직 없는 제안 API**다. 기존 integration 객체는 constructor에서 고정하고 메서드 인자로 교체받지 않는다.

```python
provider.publish_committed(
    package, receipt, *,
    expected_guard_head, expected_baseline_head, expected_control_head,
    now, transaction,
) -> CommittedAccountProjection
```

호출 순서는 다음으로 고정한다.

1. 실제 source/package 준비는 Journal 밖에서 한다. 실제 `commit_continuous_guard(...)`가 자신의 바깥 Journal transaction에서 한 번 확정하도록 한다. provider의 publication mutex를 잡은 상태에서 commit을 부르지 않는다.
2. commit이 반환한 뒤 새 실제 `journal.transaction()`을 열고 위 메서드를 호출한다. 메서드는 받은 exact active/thread-bound transaction만 소비하며 내부에서 `snapshot()`이나 `transaction()`을 열지 않는다. 기존 Journal의 process/OS 잠금이 같은 Journal의 read/publication을 직렬화하므로 별도의 역순 잠금을 새로 만들지 않는 편이 작다.
3. 후보 package/receipt를 원 입력에서 분리하고 기존 reader의 실제 `_events`, `_states`, `_binding`, `_history`, endpoint reconciliation 및 마지막 재읽기로 검증한다. 실제 PREPARE/필요 halt/COMPLETE가 있어야 하며 guard·baseline 두 store와 독립 heads가 모두 후보와 같아야 한다. receipt 클래스나 hash 문자열만으로 게시하지 않는다.
4. 후보의 old guard/baseline은 현재 게시 세대의 확정 heads와 정확히 같아야 한다. baseline sequence, interval 연결, account scope, 기존 guard의 owner/code/policy epoch와 stream 연속성을 유지한다. 여러 세대를 건너뛰거나 이전 generation으로 돌아가는 게시를 거절한다. 기존 높은 하한·고점·daily stop·permanent halt를 낮추는 별도 전이를 만들지 않는다.
5. 모든 검사가 끝난 뒤 내부 generation 참조를 한 번 교체한다. 실패하면 이전 참조를 보존한다. 실제 heads가 이미 이동했는데 게시가 실패한 경우 이전 세대를 현재인 것처럼 반환하지 않고 기존 HEAD_CHANGED 거절을 유지한다.
6. 동일 package/transaction/확정 heads의 재시도는 새 generation이나 새 Journal row를 만들지 않는 no-op다. CONSISTENT replay receipt의 control_head가 뒤의 정상 suffix를 가리킬 수 있다. 이를 이유로 기존 generation identity를 바꾸지 않고 실제 prefix 포함 여부를 검증한다. 기존 receipt_control_head를 보존하여 같은 세대의 제자리 재시도가 진행 중 operation을 불필요하게 바꾸지 않게 한다.

`receipt.control_head == current tail` 또는 `receipt.control_head == COMPLETE`를 강제하면 안 된다. 기존 reader처럼 해당 transaction의 유일한 PREPARE/COMPLETE를 찾고 receipt가 가리키는 head가 완료 이후의 검증된 prefix인지 확인한다. 뒤의 정상 risk_snapshot/kill/halt는 기존 fold로 반영한다. open PREPARE, 부정 predecessor, 누락 halt, 두 head 불일치와 승인된 epoch 변경은 기존 거절을 유지한다.

commit과 publication 사이에 작업이 들어오면 옛 provider read는 HEAD_CHANGED로 거절될 수 있다. 이 짧은 불가 구간은 안전한 초기 계약이다. 이를 없애려고 현재 head를 자동 채택하거나 불완전한 commit을 완료로 표시하지 않는다. 두 publisher 경합은 실제 commit의 predecessor 및 Journal 검사로 직렬화하고, 이미 바뀐 predecessor의 게시를 거절한다.

## 3. Controller와 Runner 연결: 기대 세대는 추가 제한뿐

Controller의 기존 operation-local 비교는 그대로 재사용한다. 새 실제 publication이 read 사이에 끼는 비정상/테스트 재진입도 원 세대 비교에서 거절되는지 회귀로 고정한다. 새 세대를 읽었다고 원 account/owner 관찰 시각이나 completion 시작 시각을 갱신하지 않는다.

Runner의 별도 transaction 사이에는 다음 선택 인자를 좁게 추가한다.

```python
Controller.reserve(..., expected_committed_transaction_id=None)
Controller.dispatch(..., expected_committed_transaction_id=None)
```

- Runner의 committed 경로만 실제 paired observation의 `committed.transaction_id`를 두 호출에 그대로 전달한다. tick과 explicit exit 모두 동일하다. legacy 호출은 기존 signature 의미와 동작을 유지한다.
- Controller는 해당 인자가 있으면 exact committed 경로인지, 형식이 맞는지, 자신의 열린 실제 transaction에서 읽은 transaction_id와 같은지 검사한다. 첫 신규 예약 전·첫 DISPATCHING/전송 전 검증에 포함한다. 인자 일치는 기존 owner/session/위험/quote/terms/capacity/permit/최종 clock 검사를 생략할 근거가 아니다.
- 이미 terminal인 주문을 반환하는 기존 멱등 경로는 새 주문을 만들지 않는다. 예약 뒤 세대가 바뀌면 그 예약을 자동 전송·재생성하지 않는다. 아직 실제 RESERVED인 로컬 취소는 기존 확인된 취소 절차만 사용하며 DISPATCHING/UNKNOWN은 기존 대조 대상으로 남긴다. 새 세대를 바탕으로 다시 판단하는 것은 새 정상 작업이다.
- 이 인자를 새 durable order wire, 공개 lease, 승인 bool로 만들지 않는다. 재시작의 RESERVED/no-resend 규칙은 그대로다. 필요하면 고정 generation-mismatch 진단만 추가한다.
- `submit_exit`는 계속 `read_committed_account(risk=None)`를 사용한다. 세대 일치 확인을 위해 위험 snapshot/새 halt/연구 승인·entry gate를 추가하지 않는다. 정상적으로 현재 자료를 다시 관찰한 독립 reducing 경로는 기존 정책 아래 유지된다.

## 4. 정확한 수정 소유 범위와 검사

| 소유 단위 | 파일 및 변경 |
| --- | --- |
| provider | `execution_launch/committed_account.py`: private generation 분리, 실제 tx 안의 직접 successor 게시와 exact 재시도. 기존 판정의 복사본을 별도 엔진으로 만들지 않는다. |
| Controller | `execution_control/controller.py`: 선택 expected transaction-id의 실제 read 대조. 기존 `_completion_owner` 비교, 최종 시간 및 no-send phase proof 재사용. |
| Runner | `execution_launch/runner.py`: paired generation을 reserve/dispatch에 전달. legacy·exit 독립성·local cancel·REJECTED 표시 보존. |
| 독립 검사 | 새 `tests/launch_committed_generation.py`와 필요한 실제 Controller/Runner 경계 검사. parent가 registry/guards 및 source closure 영향 검증 담당. |

`committed_account.py`, Controller, Runner와 baseline helper는 기존 driver/독립 signer의 source closure에 이미 들어 있다. 새 helper 파일을 추가하지 않으면 명단 확장보다 두 source manifest의 실제 변경 hash·독립 signer parity 검사가 우선이다. 변경된 코드에는 기존 코드 승인이 그대로 적용된다고 보고하지 않는다.

의미 있는 최소 회귀는 다음이다. 실제 temporary owner 서명 log·Journal·두 store/독립 head·guard commit을 사용하고 source/coverage 입력만 명시 합성으로 둔다.

- 연속한 두 실제 interval을 각각 commit하고 같은 provider/Controller/Runner identity로 다음 값을 읽는다. 각 interval의 baseline/guard commit·CAS는 각각 한 번이며 publication/read의 추가 advance/commit/CAS는 0이다. closed/foreign/thread 다른 transaction과 중첩 Journal 접근은 거절한다.
- 실제 COMPLETE 전, 한 head만 이동, store/head 손상, package/endpoint 변경, 다른 predecessor, 구세대 재게시, 세대 건너뛰기에서는 게시하지 않는다. 실제 successor가 확정됐지만 미게시이면 old reader가 거절하는지 확인한다.
- COMPLETE 뒤 publication 전 실패 후 동일 원 package/receipt의 exact retry와 뒤 control suffix를 가진 replay receipt를 허용한다. 새 row/CAS/시각 변경 없이 동일 세대가 남아야 한다. 두 publisher 경합에서 하나의 명확한 successor만 게시된다.
- caller 원 package와 반환 projection의 변경은 게시 자료를 바꾸지 못한다. actual final store/head 재읽기 도중 변경은 거절한다. 동일 transaction_id라도 다른 확정 자료를 교체하지 못한다.
- 작업 중 실제 세대 교체 시 기존 `_completion_owner`가 거절한다. Runner 관측 후 예약 전, 예약 후 dispatch 전 새 실제 commit/publication을 넣으면 옛 판단으로 capability/create가 발생하지 않는다. 원 예약·불확실 상태를 지우지 않는다.
- 원 관찰 시각·30초/22시/서울 날짜·owner current head/code/effective limits·원금/최고점 하한·daily stop/permanent halt를 보존한다. 새 세대는 fresh data라는 이유로 다른 승인 epoch를 자동 수용하지 않는다. 정상 다음 operation과 독립 reducing은 실제 현재 자료와 기존 권한 조건에서 확인한다.

## 5. 이 단위 밖에 남는 실제 운영 조건

이번 단위는 **이미 실제 로컬 commit된 다음 세대를 안전하게 소비하는 연결**이다. 실제 운영 source를 발급하거나 Coordinator의 controlled 거절을 해제하지 않는다. 현재 `ContinuousUpbitCandidateSource.__call__`의 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`, rehearsal-only Coordinator, carry controlled 거절을 유지한다.

Upbit GET 원문 보관은 receipt/bytes/hash의 로컬 대응을 남길 수 있지만 동일 credential/account identity, origin 이후 누락 없는 order/fill/transfer/fees, 모든 보유 자산의 연속 sequence/gap/reconnect/watermark와 REST fence 결합을 인증하지 않는다. 합성 `VerifiedCoverage`, dataclass, 로컬 서명, 성공 boolean으로 이 빈틈을 채우지 않는다. 실제 source/coverage 계약과 별도 owner/code/rules/전략/활성화 범위는 계속 필요하다.

재시작에 필요한 full guard package·원 owner 관찰·정확한 commit receipt는 별도로 복구 가능해야 한다. 기존 raw/path/material archive가 이 전체를 자동 포함한다고 가정하지 않는다. 다음 구현은 caller가 실제 보존한 같은 package를 제공하는 명시적 경계까지만 다루며, 폴더에서 최신 파일을 골라 head를 채택하는 자동 복구는 넣지 않는다.

`Coordinator._publish`의 구 provider를 새로운 commit 후 다시 실행하지 않으며, scheduler/생산 source composition은 후속 단위로 남긴다. Controller의 마지막 검사와 실제 network send 사이의 권한·시간 경계, Windows 운영 및 전원 장애 복구도 이번 로컬 테스트로 보장하지 않는다. 새 사용자 승인 질문이나 기존 위험정책 변경은 필요하지 않다.
