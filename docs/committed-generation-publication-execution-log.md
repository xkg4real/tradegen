# Committed generation publication 실행 기록

작성일: 2026-11-13. 최종 관련 검사 **312 PASS / 0 FAIL / 0 NOT_RUN**, 단일 프로세스 **740.398초**로 완료했다. 첫 집중 검사의 달력 비교 오류 두 건과 별도 PR55의 정적 검사 누락 두 건을 보완한 상태이며, 첫 115개 검사 ID 모두가 최종312개에 포함돼 통과했다. 최초 실패 기록도 보존한다.


## 실제 후속 세대 게시

`execution_launch/committed_account.py`는 기존 exact `CommittedAccountProvider` 객체를 유지하면서 이미 확정된 직접 후속 계좌 세대를 게시하는 `publish_committed(...)`를 추가한다. package와 receipt는 입력에서 분리 복사하고 private frozen generation에 묶으며, 내부 자료와 바인딩의 해시를 재검사한다. 반환 projection이나 caller의 원 package를 게시 상태 자체로 사용하지 않는다. private generation은 source 인증이나 owner·주문 권한 토큰이 아니다.

publication은 caller가 연 **실제 active·thread-bound Journal transaction** 안에서만 수행한다. provider가 새 transaction·publisher lock을 열거나 Journal row·baseline·guard를 advance/commit/CAS하지 않는다. `commit_continuous_guard(...)`가 기존 별도 transaction에서 실제 확정된 다음, publication을 위한 transaction을 열어 호출하는 계약이다. 실제 commit과 publication 사이에 이전 reader가 HEAD_CHANGED로 거절하는 구간은 허용하며, 그 간격을 숨기기 위해 현재 head를 채택하지 않는다.

후보의 PREPARE·필요 halt·COMPLETE와 package input digest, guard/baseline 두 store 및 독립 heads를 기존 reader 경로로 대조한다. endpoint·interval·account scope·정책·owner/code epoch·stream 연속성과 직접 predecessor를 확인한다. 후속 후보의 old heads는 현재 게시 세대의 확정 heads여야 한다. 여러 세대를 건너뛰거나 구세대로 되돌아가는 게시, 한쪽 head만 이동한 불완전 상태를 정상으로 게시하지 않는다.

직접 predecessor 검증에는 실제 Journal prefix와 후속 package의 `baseline_before`를 사용한다. 이미 후속 상태로 이동한 store를 이전 세대라고 가정하거나 임의의 guard 객체를 만들어 검증 완료로 취급하지 않는다. 모든 후보 검사와 마지막 store/head/control 재읽기가 끝난 다음 private generation 참조를 한 번 교체한다. 게시 실패 시 기존 참조를 보존하지만, 실제 heads가 이미 이동했다면 옛 자료를 현재인 것처럼 반환하지 않는다.

## Exact retry와 기존 제한 보존

동일 package·transaction·확정 heads의 재시도는 새 세대나 durable row를 만들지 않는다. 재시도 receipt가 COMPLETE 뒤의 정상 control suffix를 가리킬 수 있으므로 실제 prefix 포함 여부를 검증하며, receipt head가 반드시 현재 tail 또는 COMPLETE 자체여야 한다고 강제하지 않는다. supplied replay receipt가 검증되더라도 기존 generation의 **원 receipt identity와 receipt_control_head**를 유지하고 현재의 보수적인 suffix 결과를 반환한다.

현재 floor·high·daily stop·halt 병합 및 owner·정책 epoch 검사는 기존 reader를 재사용한다. 새 자료라는 이유로 원 account 관측 시각이나 completion lifetime을 갱신하지 않는다. 높은 보호 하한과 정지 상태를 낮추는 새 전이를 추가하지 않는다. constructor에서 고정한 Journal·store·head integration도 게시 요청으로 교체하지 않는다.

## Controller와 Runner의 세대 연결

Controller가 한 operation 안에서 첫 실제 account read와 마지막 read의 transaction·heads·owner claim·policy/day를 고정하는 검사는 이미 존재한다. 이 단위는 이를 별도 권한 엔진으로 재구현하지 않는다. 서로 다른 transaction인 Runner 관측 → reserve → dispatch 사이에 다음 선택 인자만 추가한다.

```python
expected_committed_transaction_id=None
```

committed Runner는 실제 paired observation에서 얻은 transaction ID를 reserve와 dispatch에 그대로 전달한다. Controller는 인자가 있으면 exact committed provider 경로·형식·실제 현재 read의 ID를 대조한다. `COMMITTED_COMPLETION_GENERATION_REQUIRED`와 `COMMITTED_COMPLETION_GENERATION_CHANGED`는 추가 제한 진단이다. 같은 ID만으로 owner/session·기존 위험정책·quote/terms·capacity·permit·최종 시계 검사를 생략하지 않는다.

관측 뒤 예약 전 또는 예약 뒤 dispatch 전 실제 후속 세대가 게시되면 옛 판단으로 새 전송을 진행하지 않는다. 기존 terminal/idempotent 조회는 새 주문을 만들지 않는 기존 동작을 유지한다. 세대 불일치 때문에 기존 RESERVED·DISPATCHING·UNKNOWN 기록을 삭제하거나 자동으로 다시 생성하지 않는다. local cancel과 불확실 전송의 대조 절차, 기존 wire 형식과 legacy callable 경로는 유지한다.

명시적 `submit_exit`는 계속 `read_committed_account(risk=None)`를 사용한다. 세대를 맞추려는 이유로 entry-risk snapshot·새 halt 쓰기·연구 entry gate를 끼워 넣지 않는다. 실제 현재 계좌와 기존 reducing 권한 조건을 확인하는 독립 매도 경로를 보존한다. 자동 전략 tick과 명시적인 dry exit는 구분해 검증한다.

## 검사 범위와 현재 상태

수정 소스는 `execution_launch/committed_account.py`, `execution_control/controller.py`, `execution_launch/runner.py`다. 새 검사는 `tests/launch_committed_generation.py` 19개, `tests/control_committed_generation.py` 12개, `tests/launch_committed_generation_runner.py` 9개로 총 40개다. 실제 연속 commit fixture를 포함하여 첫 관련 115개 집중 검사에서 실행했다.

검사는 실제 임시 owner 서명 log·Journal·guard/baseline store와 독립 head·guard commit·publication을 사용한다. source/coverage/시장 자료는 합성임을 표시하며, hash·receipt constructor·긍정 boolean을 실제 issuer 대신 사용하지 않는다. 주요 범위는 직접 successor와 exact replay receipt, 원본·projection 변경 격리, 마지막 dependency 재읽기, 불완전 commit 거절, 추가 baseline advance/CAS/Journal 쓰기 없음, 관측/예약/dispatch 사이 세대 교체 거절, UNKNOWN 무재전송, 독립 reducing 유지다.

첫 runtime 전 독립 읽기 검토에서 이전 세대의 historical prefix가 다른 정책·완화된 floor suffix 또는 전날의 day-open 충돌을 숨기지 못하도록 보완했다. 이 수정은 첫 실행에 포함됐다. 아래 네 런타임 실패를 이 읽기 검토 발견과 혼동하지 않는다.

첫 실행 기준 HEAD는 `61b2b20`이고 Python/YAML source fingerprint는 다음과 같다.

```text
65affd1d1f2698b1e374167e1713718af2de4e470e96f94269f84feaeb11c062
```

19 KEYLESS 환경에서 import 전부터 실제 home metadata 및 소스 불변을 확인했고, 실행 뒤 QA를 복원했다. 첫 실행의 네 실패는 다음과 같이 구분한다.

- 새 달력 검사 두 개는 저장된 UTC 정규화 timestamp의 `.date`/`.hour`를 KST 기대값과 직접 비교했다. assertion만 `astimezone(M.KST)`로 바꿨다. 같은 실제 instant·정책 날짜·latch 검사는 유지하며 generation runtime은 변경하지 않았다.
- 기존 control renewal guard 두 개는 PR54의 transport/Upbit 선언이 전이 import 경로에 추가됐는데 이전 initializer pin이 남아 있어 실패했다. generation runtime 결함으로 처리하거나 guard를 넓게 허용하지 않았다. 별도 `gpt/read-capture-renewal-boundaries`에서 `tests/renewal_boundaries.py`의 검토한 pin 두 개와 음성 검사 여섯 개만 보완한다. 해당 관련 105개 검사는 105 PASS / 0 FAIL / 0 NOT_RUN, 단일35.472초로 완료했고 PR55로 병합했다(main `6fa15f200e6fb66952a3202e210842f968a59da0`). 운영 코드는 바뀌지 않았다. 상세 증거는 `read-capture-renewal-boundaries-execution-log.md`에 기록했다.

generation runtime과 달력 테스트 수정은 `1e4fe9e4132da29ab9d710a589656d7a7bbe08e8`에 저장·push했다. [PR56](https://github.com/xkg4real/tradegen/pull/56)으로 전달한다. 별도 guard 보완을 통합한 HEAD `a88ab967fb71a5be55722be01260b1fdffa84f1b`에서 최종 관련312개 검사를 한 프로세스로 완료했다. 서로 다른 실행의 수를 더하지 않는다.

새 successor의 실제 연구/driver/history 경로로 warmup HOLD에 도달하는 검사는 **첫 집중 실행에서 통과했다**. 이는 전체 자동 BUY 또는 전략 SELL tick 통과를 뜻하지 않는다. 명시 dry exit·local cancel·결과 매핑 단위와 자동 전략 실행을 구분한다. 최종 검증 label은 `committed-generation-final-related`, source fingerprint는 `8e1ec8ced66cc3131bc619fa2f75b7d78c54769d945e9f6d7b37364db1b392af`다. 최종312 PASS / 0 FAIL / 0 NOT_RUN, 단일740.398초다. 전체 Controller/order lifecycle 및 committed account/completion/observation/generation, Runner/universe/driver/carry, 관련 guards와 두 global read-only 검사를 포함한다. 19 KEYLESS 및 격리 임시 환경에서 import/discovery 전부터 완료까지 source와 실제 home metadata가 불변이었고 QA bytes를 복원했다. 최종 소스와 전달 작업본 fingerprint 일치를 다시 확인했다. 상세 증거는 `tradegen-session/committed-generation-1113/committed-generation-final-related-{start,rows,summary}.json`과 첫 `committed-generation-dev1-*`다.

## 남은 운영 경계

이 단위는 이미 실제 로컬 commit된 세대의 메모리 게시와 소비를 연결한다. source authenticity·remote coverage issuer·실계좌 owner 권한을 발급하지 않는다. committed Runner의 rehearsal-only 제한, carry controlled 거절, Coordinator의 기존 운영 차단은 유지한다. 실제 Coordinator의 구 publication 경로를 guard commit 뒤 다시 호출해 baseline을 중복 advance시키지 않는다.

전체 guard package·원 owner 관측·정확한 receipt의 재시작 보관 및 복구, 실제 source 수집과 commit 후 자동 게시의 운영 composition, 마지막 검사와 wire send 사이의 별도 경계는 남아 있다. native Windows 운영·전원 장애·실제 계좌·API·키·주문 검증을 수행했다고 주장하지 않는다. 기존 손실 하한·daily stop·halt·위험정책은 완화하지 않는다.

계약: `TRADEGEN_COMMITTED_GENERATION_NEXT_UNIT_2026-11-13.md`. 이 단위의 코드·관련 검증은 완료했으며 남은 운영 경계는 위와 같다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
