# TRADEGEN — 연속 producer에서 확정 세대를 rehearsal Runner로 연결하는 다음 단위

2026-11-13, 읽기 전용 설계. 기준 트리 `/workspace/tradegen-committed-startup-1113`, HEAD `ae3f3c3`. 이 문서는 구현·실행 결과가 아니다. source/tests/HEAD는 변경하지 않았다. startup 검증의 최종 결과는 별도 실행 기록에서 확정한다.

## 1. 남은 실제 연결 지점

| 현재 함수 | 실제 동작과 다음 연결 |
| --- | --- |
| `account_interval.ContinuousUpbitCandidateSource.collect` | 실제 `collect_upbit` → 이미 가동 중인 recorder의 path → coverage 검증 → 원 capture를 포함한 `StagedContinuousCandidate`. `latest()`는 후보일 뿐이고 `__call__`은 계속 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`로 거절한다. |
| `guard_capture_archive.collect_archive_guard_capture` | 실제 수집 → 전체 원문 archive/backup/readback → 원 시각의 material 재생. 재생 실패도 원본 archive ID와 함께 남긴다. 이 경로를 다시 만들 필요가 없다. |
| `guard_generation_archive.retain_guard_input` | 보관된 capture에서 material을 다시 도출하고 정확한 전체 package·원 policy/owner/time·세 predecessor heads를 묶는다. |
| `committed_startup.CommittedStartup.commit_input` | 보관 입력 재검사 → 실제 `commit_continuous_guard(expected_evaluated_at=원 시각)` → 실제 완료 기록 보관. provider 게시와 전략 실행은 하지 않는다. |
| `CommittedAccountProvider.publish_committed` | 같은 실제 Journal의 열린 Transaction 안에서 실제 COMPLETE·두 store/head·직접 successor 연속성·현재성을 확인하고 **같은 provider의 private generation만** 교체한다. advance/commit/CAS는 없다. 이미 구현됐다. |
| `Coordinator.__init__ / _publish` | 아직 legacy `ContinuousAccountProvider`를 무조건 생성한다. `_publish`는 `BaselineFrame`을 board에 넣고 `_provider(now)`를 호출한다. 그 호출은 `advance_account_baseline` → checkpoint commit → head CAS를 수행하므로, guard commit 뒤 재사용하면 이중 전진 경로다. |
| `Coordinator._slot` | `_prefetch` → 원 book sample → `_publish` → 실제 `LiveHistory.record_slot` → deadline 기록 → 실제 `Runner.run(..., max_steps=1)`. 현재 account 단계만 확정 세대 경로와 연결되지 않았다. |
| `Runner.tick / submit_exit` | 정확한 committed provider는 이미 지원한다. 실제 Controller paired/account-only 관찰, 실제 완료 시각, 같은 관측 transaction ID를 reserve/dispatch 제한으로 전달한다. 이 부분을 다시 구현하지 않는다. |

최소 목표는 **fixed Upbit KRW 현물 rehearsal 한 unit**에서 실제 수집·보관·commit·완료 보관·동일 provider 게시를 순서대로 수행하고, 기존 실제 history/factory/Runner까지 도달하는 것이다. universe 전환, controlled 활성화, 새 source issuer, post-E 관리 승인으로 범위를 늘리지 않는다.

## 2. 최소 seam과 호출 순서

새 `execution_launch/committed_producer.py`에 rehearsal 전용 실제 orchestration을 둔다. 제안 객체 이름은 `CommittedAccountProducer`; Coordinator가 받는 것은 이 정확한 객체와 실제로 바인딩된 provider/strict Journal/store/heads이며, `ready=True`, 호출자가 만든 projection 또는 범용 성공 callback이 아니다. 생성자는 저장·발급·초기화하지 않는다.

한 unit의 `collect_and_publish(...)`는 다음 순서만 연결한다. 최종 인자 이름은 구현 API 카드에서 기존 collection의 anchor/coverage/trade-fees 계약에 맞춰 확정한다.

1. 현재 실제 guard/baseline heads와 checkpoint, 기존 provider의 정확한 generation, 실제 검증된 control prefix를 읽는다. 그 baseline을 다음 path의 `previous`로 고정한다. 같은 계좌 scope·policy·기존 owner epoch·stream epoch·다음 sequence를 유지한다.
2. 기존 `collect_archive_guard_capture`를 직접 호출한다. 성공한 실제 archive replay의 material과 원 baseline으로 package의 여섯 자료 항목을 구성한다. 원 owner 관찰 두 개·policy·평가 시각은 별도로 정확하게 연결한다. audit 실패이면 원문을 남기고 이후 단계는 없다.
3. 실제 `retain_guard_input` → `CommittedStartup.commit_input`을 호출한다. commit은 자체 Journal transaction을 열므로 다른 Journal transaction 밖에서 실행한다. 완료 보관에 실패하면 이미 완료된 commit을 되돌리거나 old generation을 현재로 가장하지 않는다.
4. 실제 `read_guard_completion`으로 completion → input → capture 전체와 별도 backups를 다시 읽는다. 보관 record만으로 완료 권한을 주장하지 않고, 같은 실제 Journal의 **새 transaction** 안에서 기존 publication의 candidate 검증과 실제 `tx.events`를 통해 receipt·COMPLETE·두 heads·저장된 observed prefix를 대조한다. 이미 heads가 이동했을 때 이전 generation의 `inspect_committed`를 성공시키려 하지 않는다. 별도 역사 검사가 필요하면 기존 startup/completion adapter처럼 정확히 복원된 candidate를 검사한다.
5. 같은 provider의 `publish_committed`를 호출한다. 이 시점의 실제 clock을 전달하고 원 `package['now']`, 계좌 asof, source/server 시각을 바꾸지 않는다. 실패하면 provider의 이전 private 참조는 유지되지만, 이미 이동한 실제 heads 때문에 이전 계좌 read가 거절되는 상태도 그대로 유지한다.
6. transaction을 닫은 뒤 같은 실제 Controller의 account-only 관찰로 현재 owner/code/effective limits와 최종 시각을 확인한다. 이 관찰은 entry-risk snapshot을 쓰지 않는다. 원 endpoint AccountEvidence와 거래 unit용 book만 게시하고 실제 history → Runner로 진행한다. slot 시간·book 신선도가 지났으면 실행을 건너뛴다.

반환값은 원 capture/input/completion IDs, 실제 transaction ID, 실제 관측 완료 시각과 원 endpoint 자료를 연결한 불변 **기록**이다. `source_authenticated`/`execution_ready`를 True로 만들거나 새 permit을 발급하지 않는다. 실제 account 관찰과 주문 허가는 계속 Controller가 판단한다.

## 3. Coordinator에 필요한 좁은 변경

`Coordinator.__init__`에 명시적인 optional committed 경로를 둔다. legacy 값이 없으면 기존 생성·호출 의미를 유지한다. 새 경로는 fixed rehearsal, 정확한 DryRunAdapter, 같은 격리 root, `Journal.requires_existing is True`, 같은 policy/clock/provider/Controller identity를 필수로 확인한다. 이 경로의 Controller에는 legacy와 달리 명시 clock을 전달한다. Caller의 `BaselineFrame`을 committed 경로로 승격하지 않는다.

- `_prefetch/_publish`: legacy 경로는 그대로 둔다. committed 경로는 새 producer를 호출하고 **legacy `_provider(now)` 및 `ContinuousAccountProvider.__call__`을 호출하지 않는다.** board는 book 보관에만 사용한다. 별도 endpoint accessor는 실제 해당 generation의 `account_capture.endpoint_accounts[0]`에서만 얻는다.
- `_latest_frame.accounts[0]`을 쓰는 terms 갱신, holdings, disarm의 재게시를 분리한다. committed 계좌를 가짜 advancing frame으로 바꾸지 않는다. 최초 단위는 fixed만 허용하여 universe branch의 종목 전환까지 지원한다고 주장하지 않는다.
- `_slot`: 실제 account-only 완료 시각 이후 history 기록 및 Runner tick을 수행한다. tick 자체의 기존 `observe_committed`·generation pin·연구/driver 검사는 그대로다. 수집 전 `now`를 끝까지 재사용하지 않고, heavy work 이후 clock을 다시 검사하되 원 evidence 시각은 유지한다.
- `_explicit`: exit는 같은 producer/Controller의 account-only 경로를 유지한다. 새 entry-risk 또는 연구 승인 gate를 추가하지 않는다. 실제 sell의 기존 reserve/dispatch·loss guard가 그대로 적용된다.
- `_monitor/bootstrap`: 현재 `_ready=True`와 `reconcile_orders`의 반환 count만으로 새 경로를 준비 완료로 표시하면 안 된다. 이미 구현된 startup의 실제 최종 states·captured orders/fills·외부/미해결 주문 판정을 재사용해야 한다. 공개 `StartupResult` 자체는 허가가 아니다.

**최초 startup 연결 방식은 구현 카드에서 하나로 고정한다.** 권장 최소안은 새 runtime 구성 전에 기존 `CommittedStartup.reconcile`을 실제 호출하고, 그 실제 provider/Controller와 현재 generation을 재검증하여 launch용 Runner를 한 번 구성하는 것이다. startup의 quote-disabled Runner·한 input/completion binding을 사후 변조하지 않는다. 이후 같은 provider 게시에는 기존 publication API를 쓴다. 계속되는 monitor에서도 완전 대조가 필요하면 startup의 실제 대조 본문을 같은 runtime에서 호출할 수 있는 좁은 private seam으로 추출하고, 최종 archive/owner/clock 검사를 보존한다. 임의 runtime 전달·bool 허용·대조 알고리즘 복사는 피한다. 이 seam 없이 전체 scheduler의 restart readiness까지 완료했다고 보고하지 않는다.

## 4. 꼭 유지할 실제 경계

- **Owner 관찰:** `OwnerContextClaim` 생성 자체는 인증이 아니다. `path.start` 이전 실제 관찰이 없으면 수집 완료 시점의 `owner.load_context`를 과거 시각으로 호출하여 메우지 않는다. 기존 계약은 `0 ≤ path.start − owner_before.observed_at ≤ 30초`, watermark/coverage 이후의 `owner_after`, 동일 signed terms/epoch다. producer는 이미 진행 중인 interval의 실제 사전 관찰을 보존해야 한다. 연구용 `CurrentOwnerAuthority`는 `_REVIEW_POSITIONS`를 사용하므로 계좌 보유량·session별 effective limits 관찰의 대용으로 쓰지 않는다.
- **Current authority:** 보관 claim은 역사 자료다. 실제 현재 Controller load와 signed code/head/effective-limit/session/date 검사를 계속 수행한다. kill/disarm 또는 새 서명으로 epoch가 바뀌면 정상 새 세대처럼 우회하지 않고 기존 거절을 유지한다.
- **시간:** package 평가, capture 종료, owner 관찰, commit receipt 기록, publication, Controller 완료 시각을 구별한다. 알려진 완료 시각 뒤 rollback, 30초·KST 자정·22시 경계, 오래된 server/quote, session/terms 만료는 기존 실제 검사를 따른다. 오래 걸린 보관을 새 timestamp로 보정하지 않는다.
- **Lock:** unit 직렬화 lock → 개별 collection/archive 단계 → 실제 guard commit의 Journal 단계 → completion archive → 별도 실제 Journal publication → Controller/Runner 순서다. archive lock을 잡은 채 Journal을 기다리거나 Controller callback에서 producer/commit을 호출하지 않는다. provider publication용 역순 lock도 추가하지 않는다.
- **실패:** input만 남은 상태, PREPARE pending, store-new/head-old, COMPLETE 후 completion 보관 실패, completion 후 publication 실패를 구분한다. 기존 exact retry/inspection을 쓰며 자동 head 채택·truncate·원본 덮어쓰기·새 baseline seed를 하지 않는다. 미확정 send·partial/UNKNOWN은 다음 세대에서도 지우거나 재전송하지 않는다.
- **기한:** 기존 fixed carry의 E-only 무매도, `[start,E)` 신규 진입, 관리 승인 요청 기록은 유지한다. source/저장 오류나 scheduler overrun은 매도 신호가 아니다. 새 post-E 관리 권한을 만들지 않는다.

## 5. 최소 수락 검사와 파일 소유

| 담당 단위 | 파일과 필요한 검사 |
| --- | --- |
| producer | 새 `committed_producer.py`, 새 focused tests. 실제 두 연속 capture → 두 input/완료 archive → 실제 guard commit → 동일 provider 직접 successor 게시. 최종 bytes/heads/transaction/readback 검사. 각 실패 단계 원본·pending 보존. |
| scheduler 연결 | 기존 `coordinator.py`, 새 integration tests. 명시 committed branch만 변경. legacy advance/commit/CAS spy는 실제 본문을 유지한 계수로 검증하고 새 branch에서는 legacy advance 호출 0. guard의 실제 각 세대 checkpoint/head 갱신은 1회씩이며 후속 read/history/tick은 추가 전진 0. |
| 실제 end-to-end | 기존 `tests.launch_guard_capture_archive`, `launch_guard_generation_archive`, `launch_committed_generation_runner`의 실제 fixture를 연결한다. 임시 signed owner log·실제 evaluator/review signature·LiveHistory/head·fixed carry factory → 새 세대 warmup **HOLD** 도달. source/path/coverage는 명시 합성이고 실제 API·통계 성능 검증이 아니다. |
| 경계 회귀 | actual current owner 변경, 원 owner bracket 없음, source sequence gap, stale book/account, publication 전후 head 변경, actual paired 관찰 후 다음 세대 게시로 reserve/dispatch 거절, RESERVED/UNKNOWN 보존, 종료/stop/보관 실패에서 create 0. 실제 고립 DryRun explicit exit 경로는 기존 승인 조건 안에서 별도로 확인한다. |
| closure/guards | `driver.py`와 독립 `tools/signer/sign.py` source manifest에서 새 직접 실행 dependency를 함께 점검한다. coordinator는 현재 carry closure에 포함되므로 새 import를 hash 밖에 두지 않는다. 추가 writer 엔진은 만들지 않으며 기존 guard의 구체 caller 허용만 필요한 범위에서 갱신한다. |

기존 archive/current-provider/generation/startup 단위의 테스트를 다시 작성하지 않는다. 신규 seam에 필요한 실제 통합과 영향받는 기존 회귀만 실시한다. 통합 결과에는 warmup tick·explicit exit·status/cancel과 실제 BUY/전략 SELL 미검증 범위를 구분한다. Native Windows·실계좌·운영 전원 장애는 실행하지 않았다면 계속 NOT_RUN이다.

## 6. 이 연결 뒤에도 남는 production source 공백

`execution_accounts/continuous.py`는 Upbit book snapshots/trade IDs/heartbeat/로컬 sequence가 gap-free venue sequence가 아니며 production coverage verifier가 없다고 명시한다. 요구 계약은 opening marks, 모든 mark/fill과 공통 순서, 종료 watermark, 누락된 계좌 변화의 부재다. raw GET 보관·같은 응답 반복·hash·로컬 서명은 관측하지 못한 mark/fill/transfer의 부재를 증명하지 못한다.

따라서 이번 단위가 실제 호출 경로를 완성해도 **rehearsal 연결**이다. `ContinuousUpbitCandidateSource.__call__`과 controlled-mode 거절을 유지한다. 장시간 중단·stream reset·누락 interval은 기존 30초/연속 sequence/owner bracket 조건으로 연결할 수 없으며, REST 재조회 자료를 당시 원본으로 간주하지 않는다. 향후 운영 source의 인증 근거 또는 그 근거로 성립 가능한 위험 관측 모델을 별도 설계·검토해야 한다. 현재 보호 하한을 조용히 완화하는 구현으로 이 공백을 해결하지 않는다.
