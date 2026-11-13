# P2 다음 연결 계획: 원본 수집 보존에서 확정 계좌 소비까지

작성: 2026-11-13. 읽기 기준은 `tradegen-incidents-1113` base `9944e6aa38209acf3ae48ce144d6da14de3ab7c4`의 실제 P2/I1/I2 소스다. 이 문서는 **설계만**이며 구현·실계좌 수집·주문·새 승인·검증 실행 기록이 아니다. incident 개발 파일과 기존 P2 소스를 수정하지 않았다.

권장 첫 단위는 **I3a: 연속 후보가 버리던 원본 계좌 수집 자료를 보존하고, 그 동일 자료로 guard의 계좌/평가 입력을 구성하는 audit-only 연결**이다. 실제 거래소의 연속 자료 완전성 검증기가 없는 현재 상태에서 `controlled` 거절을 먼저 없애는 것은 다음 단계가 아니다. I3a 뒤에 실제 출처·owner 시각 경계, commit/publication, Runner 소비를 각각 연결한다.

## 1. 실제 구현과 공백

현재 소스의 실제 클래스명은 `execution_launch.coordinator.Coordinator`다. 이 base에는 `ProductionCoordinator` 클래스가 없다. 아래에서 생산 Coordinator라는 말은 **앞으로 연결할 운용 경로**를 뜻한다.

| 실제 함수/타입 | 현재 가능한 일 | 아직 없는 연결 |
|---|---|---|
| `execution_accounts.upbit_collector.E1UpbitSource.fetch` | 명시 source를 통한 허용 GET의 원문·SHA·수신/서버 시각을 `SourceReceipt`로 반환 | 자격증명이 어느 account scope인지, 거래소 기록 보존이 완전한지까지 자체 입증하지 않음 |
| `collect_upbit` / `_collect` | 잔고·open/closed orders·개별 주문/체결·입출금·가격을 수집, 반복 fence·잠금 수량·수수료·이력 대조 | 동일 시작/종료 잔고 사이의 ABA 변화 부재나 전체 역사/연속 가격 완전성은 추가 증거 필요 |
| `CoverageEvidence` / `_validate_proofs` | 명시 origin·보존 범위·quiescence·계좌 모드의 구조/문구/기간 검사 | dataclass의 `reviewed-*` 문구 자체는 독립적인 출처 인증이 아님 |
| `ContinuousPriceRecorder.append/seal`, `validate_path` | 제한된 연속 후보, 순서/시각/반개구간 검사, disconnect/gap 이후 거절 | 로컬 sequence를 거래소 sequence라고 증명하지 않음. 실제 Upbit completeness issuer 없음 |
| `verify_coverage(path, account_capture_sha256, verifier, now)` | 실제 callback 호출, exact `VerifiedCoverage`·request binding·시각 검사 | callable이나 공개 dataclass라는 이유만으로 생산 인증수단이 되는 것은 아님. 생산 verifier를 제공하지 않음 |
| `preview_continuous_upbit_interval` / `_preview_continuous_upbit_interval` | 실제 수집과 path의 현금·수량·체결·mark·extrema/FIFO를 재도출하고 baseline 전이 가능성 검사 | pure preview이며 durable commit/owner 인증/주문 권한 없음 |
| `ContinuousUpbitCandidateSource.collect/latest` | 이미 실행 중인 recorder의 후보와 capture를 결합, path 파일 보관, non-operational preview | 반환 `StagedContinuousCandidate`는 preview/path hash/manifest hash/`observed_at`만 남김. 원 `SourceReceipt`와 원 captured accounts를 stage에서 잃음 |
| `continuous_archive.archive_candidate` | 원 candidate path의 제한된 파일을 exact 재시도/거절 규칙으로 보관 | capture 원문·coverage 검증 근거·pre/post owner 관찰·full guard package를 보관하지 않음. 재시작 trust anchor 아님 |
| `plan_continuous_guard` | path 및 계좌 입력 전체 재계산, chronological floor/peak/daily/permanent halt 보존 | `OwnerContextClaim`, `VerifiedCoverage`, `AccountCaptureInputs`는 외부에서 진위를 확인해야 하는 입력 |
| `commit_continuous_guard` / `classify_restart` | 실제 Journal PREPARE→필요 halt→baseline/head→guard/head→COMPLETE, 동일 package 재시도/부분 상태 거절 | source/owner 인증이나 Controller publication을 수행하지 않음. receipt는 승인/운용 permit 아님 |
| `CommittedAccountProvider.read(now, transaction)` | 실제 열려 있는 같은 Journal transaction에서 두 checkpoint/head와 PREPARE/COMPLETE/receipt prefix 재검증, 원 endpoint 계좌 대조 | noncallable. 원 package 출처 인증과 완료 시각 확인 없음. 새 state를 reduce/commit하지 않음 |
| `Controller._account/_committed_context/_snapshot_risk` | I2 exact provider 소비, 실제 `owner.load_context`와 현재 코드/head/session별 유효 한도 대조, daily stop/peak/floor/halt 보존 | caller `now` 계약. 무거운 처리 후 actual completion clock·dispatch 직전 재검증 없음 |
| `Coordinator.__init__/_publish/_monitor/_slot` | rehearsal만 허용. 기존 frame 게시→`ContinuousAccountProvider(now)`의 baseline reduce/commit→Controller/Runner | guard commit receipt/holder publication 연결 없음. 현재 `_publish`는 guard의 commit-before-publication 경로가 아님 |
| `Runner.__init__/_controller_boundary/_observations` | callable account provider를 요구하고 Controller와 같은 provider 객체인지 검사 | noncallable I1 holder를 바로 받을 수 없음. lambda로 observation만 꺼내 metadata를 버리는 우회는 부적합 |

현재 거절은 `ContinuousUpbitCandidateSource.__call__`의 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`, `Coordinator`의 `COORDINATOR_MODE_UNSUPPORTED`, carry Runner의 `RUNNER_CARRY_CONTROLLED_UNSUPPORTED`다. 다음 단위에서 그대로 유지한다.

## 2. I3a의 작은 구현 계약

소유 변경 범위는 `account_interval.py`의 candidate stage와 새 순수 helper/test로 제한한다. Controller/Runner/Coordinator, guard commit, 승인·세션, 주문 adapter는 바꾸지 않는다. 기존 flat producer와 `BaselineFrame` 의미를 보존한다.

### 보존할 실제 수집 자료

`StagedContinuousCandidate`를 확장하거나 별도의 frozen `ContinuousCapturePacket`을 반환하도록 한다. 이름은 구현 카드에서 하나로 고정하되 다음 자료는 빠지면 안 된다.

- 원 `OpeningAnchor`, 입력 `CoverageEvidence`, `TradeFeeEvidence` 전체. 재현을 위한 입력이지 인증된 승인이라고 표시하지 않는다.
- 같은 `collect_upbit` 호출의 원 `ContinuousCapture`: captured accounts, **원 bytes를 포함한 전체 receipts**, manifest SHA, 원 fenced `observed_at`.
- 실제 collection 시작 시각과 원 첫 receipt 시각. 현재 staged `observed_at`은 preview를 평가한 뒤의 clock 값이므로 capture 시각과 별도 이름으로 보존한다.
- 기존 preview의 path, `VerifiedCoverage`, valuation, interval, endpoint accounts. captured/endpoint는 boundary 재구성이 있는 경우에도 별개로 남긴다.
- 원 path archive digest. 기존 archive가 **path만** 저장한다는 사실을 그대로 표시한다. full packet 재시작 복구 가능 여부를 참으로 만들지 않는다.

실제 collection 직후 내부에서 새 packet을 구성하고 caller mutable 입력과 분리한다. `latest()`가 반환한 객체·hash·boolean을 공개 authority로 쓰지 않는다. source/path/verifier callback은 원래와 같이 명시 의존성이다. 긍정 fixture의 verifier는 합성이라는 사실을 테스트 이름/문서에 명시하고 생산 issuer로 등록하지 않는다.

제안하는 첫 helper 경계는 다음과 같다. **아래 이름은 새 계약 제안이며 현재 존재하는 함수가 아니다.**

```python
prepare_guard_capture_material(
    staged: StagedContinuousCandidate,
    previous: BaselineState,
    *, now: datetime,
) -> GuardCaptureMaterial

# frozen, non-operational material only:
# account_capture: AccountCaptureInputs
# valuation_inputs: ValuationInputs
# path: ContinuousPath
# coverage: VerifiedCoverage
# interval: BaselineInterval
# capture_material_sha256: str
# execution_ready property: False
```

helper는 다음을 수행한다.

1. exact 타입/기존 bounds를 검사하고 모든 원 receipt의 `decode()`/hash·scope·path/params·순서·원 시각을 확인한다. 원 anchor/coverage/fees와 receipt 메타데이터로 collector manifest의 **기존 `content_digest` 공식**을 재계산한다. raw bytes 해시 일치는 원격 source authenticity의 증명이 아니라 packet 내부 일치다.
2. captured accounts는 원 capture에서, endpoint accounts는 같은 preview에서만 가져온다. `AccountCaptureInputs(manifest_sha256, captured_accounts, endpoint_accounts, first_received_at)`를 정확히 만든다. hash나 endpoint에서 사라진 captured 원본을 추측하지 않는다.
3. 기존 실제 account/FIFO 대조의 historical/inside fill 분할, 이전 inflow/outflow 합산, opening cash/units를 사용해 `ValuationInputs`를 도출한다. `continuous_guard._plan`의 `expected_inputs`와 같은 exact arithmetic 계약으로 대조한다. 별도 수익·손실 숫자를 입력받지 않는다.
4. path start/이전 baseline digest/sequence·반개구간 end·captured/endpoint 수량/mark·coverage request의 capture hash를 검사한다. 원 capture 시각·endpoint 시각을 바꾸지 않고 주어진 완료 `now`에서 기존 freshness/서울 날짜/경계 규칙을 적용한다.
5. 반환은 **guard 입력 재현 자료**다. owner_before/after, 현재 policy, receipt, actual source approval을 합성하지 않는다. baseline/guard 저장·CAS·Controller 호출·provider publication·주문 호출은 모두 0이다.

I3a는 full packet의 새 durable codec/저장소까지 한 번에 만들지 않는다. packet이 메모리에만 있으면 재시작 시 같은 package를 복구할 수 없다는 제한을 명시한다. 후속 commit bridge를 추가하기 **전** full 원문/claim/receipt/identity를 exact 복구할 수 있는 private versioned archive가 필요하다. 기존 path JSON을 full package나 restart authority로 오인하지 않는다.

### I3a 검증

- actual fake-GET collector→actual recorder/path 검증→stage→material→기존 pure guard plan의 전체 경로를 사용한다. fixture source/coverage는 명확히 합성이며 real API/키/주문은 없다.
- 원 receipts와 captured accounts가 stage 이후에도 byte-for-byte 남는지, source 입력 객체 변경이 packet을 바꾸지 않는지 검사한다.
- checksum만 새로 맞춘 raw/manifest/account substitution, equal-equity 수량 변경, 누락 fee/fill/open-order row, 뒤 후보·page 누락을 거절한다.
- flat/held/partial-fill 경로, 22시·자정 bracket의 원 capture와 재구성 endpoint 구분을 검사한다. 당시 실제 자료 없이 boundary 시각으로 relabel하는 경우는 거절한다.
- gap/disconnect/재접속/new stream epoch·늦은 watermark·되감긴 clock·30초 초과를 거절한다. end에서 발생한 체결을 `[start,end)`에 끼우지 않는다.
- caller-created material/`VerifiedCoverage`/hash가 생산 ready나 `BaselineFrame`으로 승격되지 않는지 검사한다. 기존 continuous callable와 controlled Coordinator 거절 유지.
- store/Journal/Controller/adapter 호출을 관찰해 reducer preview 외 durable effect가 새로 생기지 않았음을 확인한다. 기존 path audit 저장만 그대로 허용한다.

완료 기준은 **자료 손실 없이 정확한 guard 입력을 재현**하는 것이다. 실전 source 인증·운영 bridge 완료로 보고하지 않는다.

## 3. 다음 단계의 실제 출처와 owner 시간 경계

I3a 이후에는 source provenance를 별도 실제 adapter로 확정해야 한다. 단순한 callback 반환 타입/등록 bool/로컬 서명/서버 timestamp/연결 유지 heartbeat만으로 다음 조건을 증명하지 않는다.

- 동일 main-pocket credential/account identity, origin부터의 누락 없는 주문·체결·자금 이동 이력 및 fee scope.
- `[start,end)`의 보유 자산 전체에 대한 ordered mark/fill, 실제 sequence·gap·재연결·watermark의 의미.
- REST fence와 continuous source가 같은 계좌/체결/interval을 관찰했다는 결합. endpoint 잔고가 같아도 중간 roundtrip/가격 trough를 생략할 수 없음.

**현재 코드에는 이를 충족하는 생산 Upbit verifier가 없다.** 최초 구현에 임의 `authority_sha256`, `source_proof_sha256`, `verified=True`로 긍정 경로를 채우지 않는다. 실제 지원 가능한 source contract가 확인될 때까지 audit/test 경로만 사용한다. 이 설계 작업에는 API 연결이나 사용자 입력이 필요하지 않다.

owner 검증은 다음 실제 제약을 보존한다.

1. `continuous_guard._plan`은 `owner_before.observed_at <= path.start == previous.baseline.asof`와 최대 30초, `owner_after.observed_at >= coverage.verified_at >= path.watermark_received_at`를 요구한다. 뒤늦게 수집을 시작한 시각의 Context를 과거 start 관찰로 바꾸면 안 된다.
2. 따라서 연속 recorder를 시작/다음 interval 경계를 확정하기 **전에 실제로 관찰한 owner 증거**를 보존하는 스케줄이 필요하다. 이전 owner_after가 이전 endpoint보다 늦다면 다음 owner_before로 단순 재사용할 수 없다. 필요한 이전 관찰이 없으면 해당 interval을 거절한다.
3. `CurrentOwnerAuthority`는 review용 placeholder Positions와 session=None을 사용한다. 이를 trading/guard의 운용 owner issuer로 재사용하지 않는다. 실제 `owner.load_context(now, actual_positions, session_id=actual_session)`를 신뢰 코드에서 호출하고 exact seal/hash·현재 public key/fingerprint·D14 code approval·검증된 log/head를 결합해야 한다.
4. head가 같아도 자정·session별 D12 효력으로 한도가 바뀔 수 있다. floor/daily·정책·code·halt를 실제 효력값으로 비교한다. guard의 unsupported epoch/limit transition을 max(), 새 anchor 또는 timestamps로 숨기지 않는다. 현재 I2의 0 이하 signed daily-limit 거절도 임의 양수로 고쳐 통과시키지 않는다.
5. guard policy hash는 accounts `content_digest`, Controller risk snapshot policy hash는 control `capability.digest`를 사용한다. Decimal exponent 표현에서 다를 수 있으므로 용도를 바꾸거나 문자열 동일을 가정하지 않는다.

현재 소스에 과거 pre/post owner 관찰을 인증해 `OwnerContextClaim`으로 만드는 운용 adapter가 없다는 사실을 명확히 남긴다. 이미 만들어진 claim이나 sealed Context만 받는 공개 함수로 이를 대체하지 않는다.

## 4. 후속 commit → publication 계약

아래는 I3a에 포함하지 않는 **필수 다음 연결 순서**다. 이 순서가 실제 구현되기 전에는 I1 holder를 production Coordinator에 공개하지 않는다.

1. 하나의 serialized work unit에서 실제 baseline/guard/control의 predecessor triple을 확보한다. source 수집, 원본 보관, 실제 pre/post owner·source 인증은 Controller transaction 밖에서 수행한다. 초기 head/store는 기존 명시 operator 준비를 사용하고 runtime seed/adopt는 없다.
2. full capture/package를 immutable private archive로 exact readback한 뒤 기존 `plan_continuous_guard`를 재도출한다. 계획 dataclass를 caller가 만들어 넣는 경로는 받지 않는다. archive의 raw source claim과 인증 근거/검증 코드/원 관찰 시각을 구별한다.
3. `commit_continuous_guard`를 Controller 밖에서 호출한다. Journal이 가장 바깥 lock이고 checkpoint/head lock이 안쪽인 기존 순서를 유지한다. `PREPARE` 후 실패는 pending 상태로 보존하고 같은 원 package만 `classify_restart`에 따라 재시도한다. 손상된 파일/row를 truncate하거나 guessed head로 따라잡지 않는다.
4. 함수가 성공한 뒤에도 actual Journal/guard/baseline heads, 완료 row와 원 package를 재읽어 I1 holder를 구성한다. receipt의 `control_head`는 COMPLETE 뒤의 유효 suffix prefix일 수 있다. 현재 끝과 무조건 같게 만들지 않는다.
5. **commit transaction을 완전히 닫은 후** generation/pointer를 짧은 publication lock 아래 교체한다. publication lock을 보유한 채 Journal을 요청하지 않는다. 독자는 generation을 pin하고 source 수집/commit을 자신이 열린 Controller tx 안에서 수행하지 않는다.
6. publish 전 실패에는 새 holder를 노출하지 않는다. commit은 성공했지만 publication이 실패한 경우 옛 holder는 새 head와 불일치하므로 안전하게 거절하며, 다음 읽기를 위해 같은 completed package를 재검증한다. 옛 observation을 새 timestamp로 연장하지 않는다.
7. runtime publication 이후에도 소비자는 매번 I1 `read(now, actual_tx)`를 사용한다. 공개된 dataclass snapshot만 읽어 guard metadata·현재 control suffix·신선도 검사를 생략하지 않는다.

기존 `Coordinator._publish`의 board 게시→`ContinuousAccountProvider(now)` 흐름을 재사용하면 baseline을 두 번 advance/commit할 수 있다. 새 경로에서는 기존 legacy provider와 committed holder를 분리하고, 한 unit에서 어느 경로를 쓰는지 고정한다. mutable flag로 같은 provider가 두 의미를 번갈아 갖게 하지 않는다.

## 5. Controller/Runner의 완료 시각과 주문 대조

I2는 정확한 actual tx 소비를 이미 구현했지만 `now`는 caller가 준 값이다. Controller `_authorize` 이후 adapter.prepare/append/send 동안 실제 시간이 얼마나 지났는지 확인하지 않는다. carry Runner의 fresh E gate도 Controller 내부의 느린 작업까지 대신 검증하지 않는다.

후속 구현은 committed 경로에만 trusted-clock의 명시 내부 seam을 두고 legacy callable 계약은 보존해야 한다. 공개 callback/`fresh=True`를 승인으로 받는 방식은 피한다.

- observe 완료와 reserve 완료, **dispatch의 실제 create 경계**에서 원 account.asof/server_time/risk.asof, 최초 owner 관찰 시각, 서울 날짜, rule age, E/관리 권한의 expiry를 실제 완료 clock으로 다시 확인한다.
- 무거운 계좌/owner/signature/adapter.prepare 작업 뒤 실제 현재 owner를 같은 positions/session으로 다시 읽고 I2의 code/head/effective limits/halt 조건을 재검사한다. 모든 무거운 검증 뒤 completion clock을 읽어 최초 관찰의 나이를 포함한 시간 비교를 끝낸다. 마지막 primitive 비교 이후에 또 긴 작업을 넣지 않는다.
- `DISPATCHING` durable append 자체도 지연될 수 있으므로 “그 전에 시각 한 번 확인”만으로 send 순간 신선도를 주장하지 않는다. 실제 send 직전 경계와 원 permit의 code/context/expiry 연결을 별도 회귀로 고정한다. 이미 DISPATCHING이 기록된 뒤 경계가 실패하면 새로운 create를 보내지 않고 기존 불확실 상태/재시작 대조 규칙을 보존한다.
- 이 검사는 동시 외부 변경을 원자적으로 잠그는 lease가 아니다. 확인한 owner/head와 원 관찰 시각의 유한한 검증이며, 새 timestamp로 오래된 자료를 인증하지 않는다.

Runner 연결은 별도 좁은 단계로 한다. 현재 `_observations`는 callable account provider를 직접 호출하고 `_controller_boundary`는 같은 객체 identity를 검사한다. I1 holder에 `__call__`을 붙이거나 lambda로 `.observation`만 반환하면 I2 exact-type 소비와 daily stop이 사라질 수 있다. **Controller가 actual tx 안에서 검증한 observation+committed metadata를 Runner에 제공하는 명시 seam** 또는 exact shared holder 지원을 설계하고 그 identity 계약을 함께 수정해야 한다. Runner가 열린 tx에 다시 진입하거나 provider가 Journal을 중첩 획득하지 않도록 한다. 첫 연결은 monitor/rehearsal 전용이다.

미체결·보유 대조는 publication과 별도의 사실이다.

- `Controller.reconcile`은 실제 status 요청의 수량·가격·수수료·broker identity와 원 authoritative fill history를 대조한 뒤에만 fill/reconciled row를 기록한다. 단순히 guard가 COMPLETE라는 이유로 `_known`/`reconciled_client_ids`를 채우지 않는다.
- UNKNOWN/DISPATCHING/CANCEL_REQUESTED, 부분 체결, ACKNOWLEDGED의 재시작 대조 필요를 보존한다. 기존 GTC의 늦은 체결은 새로운 주문 생성이 아니다. 동일 client identity로 재-create하지 않는다.
- status와 계좌 자료의 관찰 순서가 달라 맞지 않으면 unresolved로 남기고 새 실제 수집을 요구한다. 필요하다면 기존 흐름대로 후속 unit에서 다시 대조한다. fill을 계좌에 임의 삽입하거나 cash/holdings를 terminal order 예상값으로 바꾸지 않는다.
- 실제 held inventory, locked amounts, pending buy/sell capacity, unlisted/extra holdings를 보존한다. 자료 부족은 판단 불가다. 오류·재시작·기한은 sell 신호가 아니며 daily entry stop을 모든 reducing action의 금지나 자동 청산으로 바꾸지 않는다.
- E 이후 새 entry 금지/관리 승인 요청, 기존 halt/floor, exact session·매도 권한, post-E history/driver window 제한을 유지한다. 이번 bridge가 관리 승인 연장이나 자동 arm을 제공하지 않는다.

## 6. 구현 단위의 경계와 완료 표시

| 단위 | 산출물 | 완료라고 표시할 범위 |
|---|---|---|
| **I3a, 다음 최소 단위** | 원 collection/receipt가 남는 stage, 순수 guard material builder, actual synthetic-source 회귀 | 원본 보존 및 guard 입력 재현. production readiness false |
| I3b | 실제 source contract/issuer + 전후 owner 관찰의 출처/시간 인증, full private package archive | 실제 관찰의 인증과 복구 가능한 입력. 거래 활성화와 별개 |
| I3c | 실제 guard commit→readback→generation publication→I1/I2 monitor consumer | 이미 확정된 계좌를 중복 reducer/중첩 tx 없이 관측. controlled 거절 유지 |
| I3d | Controller completion/send clock 경계, Runner의 exact committed observation 연결, 실제 미체결 대조 | rehearsal의 end-to-end 실행 경계. source/관리/승인 조건이 실제 충족되기 전 live 준비 완료 주장 금지 |

첫 구현에 새 사용자 결정을 요구하지 않는다. 자료/코드 검토·현재 서명·실운영 source 설정·운용 activation은 서로 다른 경계다. 이후 source adapter가 실제로 보장할 수 없는 조건이 확인되면 해당 불가 사실을 기록하며, 가짜 coverage나 위험정책 완화로 해결하지 않는다.

이 문서 작성에서는 API 호출·원 owner home 읽기·실키 사용·주문·기존 테스트 재실행을 하지 않았다. 근거는 명시한 실제 함수의 읽기 검토다. 이후 변경이 확정되면 app factory의 source closure와 독립 signer의 동일 목록, D14 approval, guard/registry/관련 회귀를 부모 통합 단계에서 함께 갱신해야 한다. 이전 코드 서명을 새 code hash 승인으로 재사용하지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
