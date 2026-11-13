# Committed startup retention 실행 기록

작성일: 2026-11-13. **중복을 제거한 456개 검사 모두 PASS, 미해결 FAIL 0, NOT_RUN 0.** 6회 실행에서 총 562건을 검사한 결과이며 단일 process의 456개 실행으로 보고하지 않는다. 아래 구현은 보관된 확정 계좌 자료의 재시작 복원과 격리된 DryRun 대조를 연결한다. 실계좌 자동매매 활성화나 production source 완전성 인증을 완료한 것으로 해석하지 않는다. 변경은 [PR #58](https://github.com/xkg4real/tradegen/pull/58)에서 추적한다. 최종 delivery commit과 실제 main 병합·tree 대조 결과는 외부 인수인계 기록에 남긴다.

| 기준 | 버전 |
| --- | --- |
| 기반 main, PR #56 | `19f6775` |
| 구현 commit | `811c780f304f47f239d6e11a5cea1c272c6f970d` |
| 테스트 계약 정정 commit | `894552cdc08603afad77fb4726daf8b018aa35b4` |
| PR #57 main 통합 | `119c9ab` |
| 합성 adapter code 정정 commit | `ae3f3c3909781a8017a602a70b1501ac6ed4b756` |
| cutoff fixture 정정 commit | `a616fb06319e023ea1518afc078858a4d52e30ce` |

세 교정 commit은 테스트만 수정했다. `894552c`는 completion record의 `repr`에 대해 계약에 없던 숨김 조건을 제거했다. `ae3f3c3`은 기존 schema가 허용하지 않는 합성 AdapterResult code의 hyphen을 underscore로 바꾸었다. `a616fb0`은 실제 collector의 경계 bracket 규칙을 만족하는 사전 capture를 구성하고, 22시 시점의 원 endpoint 나이가 30초 이내임을 명시적으로 검증했다. startup production 구현은 `811c780` 이후 바꾸지 않았으며, 중간 main 통합에서 PR #57의 별도 변경은 포함됐다. 최초 실패 결과도 보존한다.

## 실제 보관과 원본 복원

`execution_launch/guard_generation_format.py`는 작은 `GuardInputRecord`와 `GuardCompletionRecord`의 엄격한 versioned codec을 제공한다. 입력 기록은 기존 capture archive/packet/material, 원 baseline과 세 predecessor heads, policy, 과거 owner 관찰 두 개, 원 평가 시각을 연결한다. 전체 raw capture를 다시 저장하거나 새로운 파일 쓰기 엔진을 만들지 않는다.

다음 digest와 시각은 구분해서 보존한다.

- 기존 전체 package digest는 원 `package['now']`를 포함한다. 기존 guard input digest는 이 시각을 포함하지 않는다. 새 record domain digest는 정확한 canonical metadata 표현을 별도로 묶는다.
- 원 receipt의 `control_head`, 실제 고유 COMPLETE 행의 hash, 기록할 때 관찰한 현재 Journal tail은 서로 다를 수 있다. receipt가 완료 후 정상 suffix를 가리키는 경우도 허용한다.
- capture의 역사 재생 시각, 원 package 평가 시각, completion 기록 시각, 현재 startup 완료 시각을 바꾸어 쓰지 않는다. Decimal의 부호·자리수·지수와 원 시각의 instant를 보존한다.

Metadata 기본값이자 상한은 record **65,536 bytes**, nodes **2,048**, text **16,384 bytes**, depth **12**다. JSON 파싱 전 크기와 구조를 검사하고 중복 key, float/nonfinite, 미지정 field/tag, 잘못된 타입·시각·digest를 거절한다. 기존 capture의 64MiB packet/raw aggregate, 최대 2,000 receipts 등 제한은 늘리지 않았다. 새 startup 한 번의 대조에는 로컬 주문 또는 captured broker-order rows 각각 **1,024개** 상한을 적용하며, 초과 시 상태 조회·취소 전에 거절한다.

`execution_launch/guard_generation_archive.py`는 기존 BundleStore의 원본·별도 백업·catalog·독립 head와 실제 readback을 사용한다. 입력과 완료 기록은 각각 하나의 고정 이름 payload로 보관한다. RAW manifest의 parent 표기는 자동 의존 검증이 아니므로 **completion → input → capture** 전체를 명시적으로 다시 읽고, 실제 capture-material 재생 결과와 전체 package 표현을 대조한다. caller가 만든 receipt나 `backup_verified` 값만으로 저장 완료를 판단하지 않는다.

완료 기록의 archive read는 보관된 주장 검증이다. 실제 완료 여부는 같은 실제 Journal transaction 안에서 provider가 검사한 transaction/package/input/guard/baseline/COMPLETE/receipt와 다시 대조한다. 저장된 관찰 tail은 실제 검증된 prefix이며 receipt prefix 이후여야 하고, 기록 시각은 그 행의 UTC 이상·현재 관찰 시각 이하여야 한다. 정상적인 후속 행을 허용하기 위해 저장된 tail과 현재 tail의 동등성을 강제하지 않는다.

원 입력은 commit 전에 보관한다. 실제 `commit_continuous_guard`가 반환한 receipt는 commit 후 별도 불변 기록으로 남긴다. 완료 후 응답이 유실되면 실제 CONSISTENT 재시도에서 얻은 새 replay receipt를 별도 기록하며, 잃어버린 최초 receipt의 tail·시각을 창작하지 않는다. 부분 보관과 실패 증거를 삭제하거나 기존 원본을 덮어쓰지 않는다.

## 실제 durable 검사와 초기화 없는 Journal

`CommittedAccountProvider.inspect_committed(now=..., transaction=...)`는 한 private generation 참조를 고정하여 실제 active/thread-bound Journal, 원본 바인딩, PREPARE/필요 halt/COMPLETE, 두 checkpoint store와 독립 heads를 검사하고 마지막에 다시 읽는다. 반환값은 원 시각과 durable linkage metadata이며 AccountObservation, RiskResult, 현재 owner 권한이나 주문 허가가 아니다. 기존 `read`가 stale로 실패한 예외를 복원 성공으로 바꾸거나 과거 시각으로 현재 read를 통과시키지 않는다.

`Journal(..., require_existing=True)`는 기존 root/lock/journal/anchor가 필요하며, transaction·load·append에서 없어진 상태를 초기화하지 않는다. `requires_existing`은 읽기 전용이고 설정은 생성 후 변경하지 못한다. 기존 기본값 False의 초기 설정 및 wire 동작은 유지한다. startup과 completion 보관은 exact Journal의 이 설정을 필수로 확인하고, 같은 실제 객체를 Controller와 guard commit에 전달한다. 운영자 초기 provision 뒤 strict 객체로 다시 열며, snapshot 사전 확인만으로 삭제 경주까지 막았다고 주장하지 않는다.

Guard commit에 추가된 선택 인자 `expected_evaluated_at=None`은 원 평가 시각에 대한 추가 제한이다. startup은 원 record의 평가 시각을 전달한다. 실제 Journal 잠금 안에서 plan을 다시 계산한 뒤, 쓰기 전에 이 값과 `package['now']`, 실제 proposed checkpoint의 `recorded_at`이 같아야 한다. 이 검사는 input digest가 시각을 제외하는 특성과 duplicate plan의 기존 checkpoint 반환 때문에 필요한 제한이다. None을 쓰는 기존 caller의 duplicate 의미는 유지하며 새 권한을 발급하지 않는다.

## 재시작 분류와 실제 DryRun 대조

`execution_launch/committed_startup.py::CommittedStartup`은 `commit_input`, `inspect`, `reconcile`을 제공한다. 보관 읽기, guard commit, 완료 보관, Journal 검사는 별도 lock 단계다. archive lock을 잡고 Journal을 기다리지 않고, Journal을 중첩해서 열거나 guard commit 후 legacy advancing provider를 호출하지 않는다. inspect와 새 provider의 복원 검사는 baseline을 다시 advance/commit/CAS하지 않는다.

Durable FRESH는 아직 commit되지 않은 입력을 뜻한다. 현재 계좌의 FRESH와 구분한다. pending 단계는 실제 PREPARE와 store/head 상태로 분류한다. store 쓰기는 완료됐지만 head 갱신 전인 중단에서는 해당 PREPARE에 연결된 정확한 proposed digest만 추가로 확인하며, head를 채택하거나 상태를 수리하지 않는다. 읽기 전용 inspect는 commit을 재개하지 않는다. 명시적인 `commit_input`만 기존 동일-package 재시도를 실행한다. torn 기록·DIVERGENCE·알 수 없는 head·원본 누락은 거절한다.

현재 FRESH는 실제 `provider.read(current_now, actual_transaction)`의 성공이 필요하다. 원 baseline/account 관측의 30초, 서버 시각, 서울 날짜와 필요한 22시 경계를 유지한다. 원 `owner_before`는 기존 interval 시작 bracket을 유지하고, 현재 endpoint owner 관찰의 나이는 실제 Controller completion 검사로 확인한다. 과거 owner 관찰을 전부 임의의 새 TTL로 제한하거나 현재 승인으로 바꾸지 않는다.

Reconcile은 실제 격리 root와 정확한 DryRunAdapter만 받는다. 실제 Runner rehearsal boundary와 같은 provider/Controller/Runner identity를 side effect 전에 확인한다. 이 startup Runner에는 거래 전략·연구 증거가 없고 quote 함수는 항상 거절하며 전략 tick을 실행하지 않는다. 기존 세대 게시 API를 재구현하거나 임의 새 세대를 조용히 복원하지 않는다.

- 실제 현재 account/owner 확인에는 `Controller.read_committed_account(risk=None)`를 쓴다. 대조를 위해 새로운 entry-risk snapshot·연구 entry gate를 추가하지 않는다.
- 자기 namespace의 never-sent RESERVED만 기존 로컬 취소를 한다. captured broker 주문이 이 가정과 충돌하면 취소 전에 보류한다. 불확실한 DISPATCHING/UNKNOWN은 실제 status 대조 대상이며 자동 재전송하지 않는다.
- 대조 횟수로 성공을 판단하지 않는다. 실제 최종 Journal 상태, endpoint의 전체 orders/fills/positions, client/broker identity, 지정가, 누적 체결량·fee를 확인한다. open/PARTIAL은 이번 작업 이후 실제 `reconciled` 행이 있어야 하며 `RECONCILED_OPEN`으로 잔량을 보존한다.
- 초기 외부 active 주문·충돌은 중간 local 행 때문에 숨기지 않는다. 이전부터 있던 무관한 closed 이력만으로 현재 외부 미체결이라고 판단하지도 않는다. 상태 응답의 체결이 보관 endpoint에 없다면 새 실제 계좌 세대가 필요하다.
- 상태 작업 뒤 원 3개 graph, 현재 owner/account, 실제 durable 상태를 다시 확인한다. Controller의 실제 `completed_at`을 이후 startup clock의 하한으로 보존하고, 마지막 무거운 검사 이후에 완료 clock을 확인한다. 원 계좌 시각을 새로 찍지 않는다.

분류 결과의 `RECONCILED`/`RECONCILED_OPEN`도 거래 허가가 아니다. 반환값의 `execution_ready`와 `source_authenticated`는 False다. 오류·재시작·저장 장애·기한 도달만으로 시장가 청산하는 동작을 추가하지 않았다. 원 보호 하한·daily stop·halt·현재 owner/code/effective-limit 검사를 완화하지 않는다.

## 검증 기록

검사는 실제 임시 signed owner log, 실제 capture archive와 collector/material replay, Journal·checkpoint stores·독립 heads·guard commit·실제 provider/Controller/Runner·DryRunAdapter를 사용한다. 계좌 응답·가격·연속 path·coverage는 **합성 자료**다. 합성 과거 주문 lifecycle를 직접 기록한 부정/복원 fixture와 실제 reserve/dispatch를 통과한 DryRun fixture도 구분한다. 긍정 권한 verifier나 issued-session registry 삽입을 실제 발급 대신 사용하지 않는다.

| 실행 | 기준 | 현재 확인한 결과 | 범위와 중복 |
| --- | --- | --- | --- |
| `startup-new-core1` | `811c780` | 71개: **70 PASS / 1 FAIL / 0 NOT_RUN**, 5.864초 | codec·historical inspection·commit 시각 제한·strict Journal |
| `startup-codec-correction1` | `894552c` | 22개: **22 PASS / 0 FAIL / 0 NOT_RUN**, 2.795초 | 첫 71개에 포함된 codec 22개 재검사. 추가 검사로 합산하지 않음 |
| `startup-new-integration1` | `811c780` | 64개: **54 PASS / 10 FAIL / 0 NOT_RUN**, 529.748초 | archive·focused startup·실제 startup 통합. 아래 두 fixture 원인 구분 |
| `startup-related1` | `811c780` | 321개: **321 PASS / 0 FAIL / 0 NOT_RUN**, 735.895초 | 기존 store/guard/account/Controller/Runner/session/보호 검사·source closure |
| `startup-final-affected1` | `ae3f3c3` | 83개: **82 PASS / 1 FAIL / 0 NOT_RUN**, 507.930초 | main 통합과 adapter fixture 교정 뒤 영향 범위 재검사. 기존 ID와 중복 |
| `startup-cutoff-correction1` | `a616fb0` | 1개: **1 PASS / 0 FAIL / 0 NOT_RUN**, 15.008초 | 남은 cutoff/date 경계 1개. 기존 ID 재검사 |

최초 core 실패는 `launch/launch_guard_generation_format/test_capture_registry_is_unchanged_and_returned_records_are_not_shared_cached_instances`의 completion `repr` 숨김 assertion이었다. 해당 테스트의 비공유 instance·기존 capture registry 불변 등 실제 계약 검사는 유지했고, 교정 후 codec 22개가 모두 통과했다.

최초 통합 실패 10개 중 9개는 `ValueError: invalid adapter code`였다. 실제 AdapterResult parser가 합성 fixture의 잘못된 code를 거절했으며, production schema를 완화하지 않고 fixture의 네 code 문자열을 바로잡았다. 부분 체결·잔량·누적 fee·UNKNOWN/status·현재 owner 재검사 등의 해당 사례는 이후 83개 재검사에서 통과했다.

나머지 1개는 `launch/launch_committed_startup_integration/test_required_cutoff_and_new_seoul_day_are_policy_refusals_not_fresh_or_generic_stale`였다. `ACCOUNT_INTERVAL_BOUNDARY_NOT_BRACKETED`는 21:59:45 시작의 합성 capture가 실제 collector의 사전 경계 band에 들어갔으면서 종료 경계까지 관측하지 않아 올바르게 거절된 결과다. 83개 재검사에서도 같은 실패가 남았다. 마지막 테스트 수정은 시작을 **21:59:40**으로 옮겨 정상 사전 capture를 만든 뒤 기존 정책 경계 assertion을 그대로 실행하고, **22:00에도 원 endpoint 나이가 30초 이내**라는 assertion을 추가했다. 이는 stale로 잘못 거절되어 정책 경계 검사를 우연히 통과하는 fixture를 허용하려는 수정이 아니다. 마지막 1개 재검사도 통과했다.

최종 registry/row ID 대조 결과 전체 서로 다른 ID는 **456개**다. 71 + 64 + 321개의 원래 registry union이며, codec 22개·영향 범위 83개·마지막 1개는 중복 ID 재검사다. 교정 뒤 같은 ID의 실제 재검사 결과를 적용하면 **456 PASS / 0 미해결 FAIL / 0 NOT_RUN**이다. 초기 실패 1 + 10개 및 반복된 cutoff 실패 1개는 각 원본 실행 기록에 남는다. 총 **562개 개별 실행, 6회 실행**이며 병렬 process seconds를 전체 경과 시간처럼 더하지 않는다. 집계 근거는 `tradegen-session/committed-startup-1113/startup-final-coverage.json`이다.

최초 구현 기준 Python/YAML source fingerprint:

```text
cbe4ebe714df6c4eef523a08ce716d7d346545dc1b53521e6f85dd437cc79a9e
```

테스트 계약 정정 포함 fingerprint (`894552c`):

```text
3f0cafbe0c05927d7798516cbaa589861ff40b12499e1ec93d227e501ce61e8d
```

main 통합·adapter code 교정 뒤 fingerprint (`ae3f3c3`):

```text
41f92e4b72dd5488f01f221d4cccc20f290d4756a10ac10b841cd09b9dbeddf8
```

cutoff fixture 교정과 최종 집계 fingerprint (`a616fb0`):

```text
75a3b5bc1d920941fe81dc09c53ee2e2aae22a6e7c0c65161054ea27ca412074
```

6회 실행의 각 summary는 19 KEYLESS 변수, import/discovery 전부터 완료까지의 보호 home metadata 불변, 각 실행 중 source 불변을 보고한다. 부모 검증기는 마지막 source freeze와 원래 QA bytes의 전체 복원을 확인했으며 최종 집계에도 `all_qa_restored=true`로 남겼다. 이 작성자는 테스트·import·실계좌 접근을 실행하지 않았으며 부모 검증기의 실제 증거를 읽어 기록했다.

원본 start/checkpoint/rows/summary/log는 아래 위치에 보존한다. 중간 실패를 덮어쓰지 않는다.

- `tradegen-session/committed-startup-a-1113/startup-new-core1*`
- `tradegen-session/committed-startup-1113/startup-codec-correction1*`
- `tradegen-session/committed-startup-b-1113/startup-new-integration1*`
- `tradegen-session/committed-startup-c-1113/startup-related1*`
- `tradegen-session/committed-startup-1113/startup-final-affected1*`
- `tradegen-session/committed-startup-1113/startup-cutoff-correction1*`
- `tradegen-session/committed-startup-1113/startup-final-coverage.json`

## 남은 운영 경계

실제 운영 source/continuous-coverage issuer는 없다. Upbit GET 원문·hash·로컬 sequence·성공한 parse는 누락 없는 전체 mark/fill/transfer 이력을 인증하지 않는다. 기존 continuous candidate source와 controlled-mode 거절을 유지한다. 장시간 중단은 현재 30초 구간·stream 연속성·원 owner bracket 계약을 만족한 것으로 바꿀 수 없으며, REST 재조회나 timestamp 재작성으로 과거 공백을 메우지 않는다.

이 단위는 반복 scheduler/Coordinator 전체 연결, 실제 거래소 status/cancel, 자동 전략 BUY/SELL, post-deadline 보유 관리 승인, 누락 구간의 새로운 역사 복구 프로토콜을 완료하지 않는다. 기존 PR #56 후속 세대 게시와 현재 보관 자료의 복원은 다른 작업이다. source가 없는 현재 계좌를 만들거나 보호 하한을 낮추지 않는다.

다음 최소 단위는 실제 continuous 수집 → 기존 원본/input 보관 → 실제 guard commit → 완료 readback → 같은 provider의 실제 successor 게시 → 기존 rehearsal history/Runner 연결이다. 현재 Coordinator `_publish`의 legacy advancing provider를 이 경로에서 호출하면 baseline을 중복 전진시킬 수 있으므로, 정확한 committed 경로에서만 건너뛴다. 원 owner bracket·현재 owner/계좌 시각·미확정 주문을 유지하고, startup의 한 입력용 quote-disabled Runner를 임의 재타깃하지 않는다. 구체 call graph와 변경·검사 범위는 `/workspace/outputs/TRADEGEN_COMMITTED_PRODUCER_NEXT_UNIT_2026-11-13.md`에 읽기 전용 계획으로 작성했으며 아직 구현 결과는 아니다.

실제 API·계좌·실키·activation·실주문 사용은 **0**이다. Native Windows 실행·실제 전원 장애/운영 재시작·실제 거래소 장애 검증은 **NOT_RUN**이다. 임시 디렉터리에서 실제 클래스들을 새로 구성한 복원 검사는 이들 운영 검증과 동일하지 않다. 동일 사용자가 모든 자료와 모든 독립 anchor를 함께 과거로 대체하는 상황까지 방어했다고 주장하지 않는다.
