# 다음 운영 연결 API 카드 — I3d committed Runner consumer

2026-11-13. **읽기 기반 제안이며 구현·검사 실행·실거래 승인이 아니다.** 근거는 main51 `a2e61b30daea8f4d4095ca2fc3ffeda776197df6` 및 `/workspace/tradegen-committed-completion-1113`의 검증 대기 I3c 소스다. I3c runtime 검증·병합 뒤 별도 트리에서 진행한다. 동결 소스·테스트를 수정하지 않았다.

**추천 한 단위:** 이미 존재하는 `CommittedAccountProvider`를 **실제 Controller가 검사한 account+risk 묶음으로 Runner의 rehearsal 경로에 연결**한다. 실제 소비자가 없는 저장/승인 타입을 더 만들지 않고, 현재 constructor/callable 단절을 없애는 작업이다. source completeness issuer, guard commit/publication 또는 controlled 활성화를 이 단위에 포함했다고 표시하지 않는다.

## 이미 있는 기능과 선택 근거

- `execution_launch/committed_account.py:CommittedAccountProvider.read(now, transaction)`는 실제 열린 control tx·두 checkpoint/head·원 PREPARE/COMPLETE·원 package·현재 suffix를 확인한다. read를 위한 callable wrapper를 만들어 observation만 꺼내면 daily-stop와 provenance가 손실된다.
- `execution_control/controller.py:_account/_committed_context`는 exact provider를 실제로 소비한다. I3c `observe/_completion_recheck`는 현재 owner와 완료 시각까지 재검사하지만 public observe는 RiskResult만 반환한다.
- `execution_launch/runner.py:Runner.__init__`는 아직 callable(account_provider)만 허용한다. `_observations`도 직접 account_provider(now)를 호출하고 tick은 별도로 controller.observe를 호출한다. 따라서 이미 확정·검사된 account+risk를 같은 관찰로 전달할 경로가 없다. `submit_exit`도 같은 `_observations`를 사용하므로 두 호출점을 함께 고쳐야 한다.
- `Coordinator._publish`는 legacy board 게시→ContinuousAccountProvider의 baseline advance 경로다. 이번에 이 경로를 재사용하거나 guard를 두 번 commit하지 않는다. 실제 publisher는 후속이다.
- `execution_accounts/continuous.py`의 모듈 계약과 `verify_coverage`에는 생산 venue completeness verifier가 없다. 공개 callback, 로컬 순번/heartbeat, 해시, 서명, `complete=True`는 누락 없는 원격 자료를 만들지 않는다. 이번 consumer 연결에서 이 결론을 바꾸지 않는다.

**KIS 표시 기능은 재구현하지 않는다.** 실제 `data/kis_live.py`, `data/kis_live_catalog.py`, `ui/kis_live_page.py`, `main.py` navigation에 연결돼 있다. `docs/kis-live-usage.md`에는 명시 연결·체결/호가 동시 구독·depth/spread/imbalance/표본 VWAP·지연/오래된 자료·중지/화면 이탈 절차가 있다. 기존 실행 ledger는 업로드22 XLSX의32 공개 채널과 focused45 PASS, 당시 integrated2077 PASS/122 NOT_RUN을 기록한다. 이는 이번에 재실행한 결과나 실제 KIS 접속 성공이 아니다. 남은 실제 PC 권한/접속 확인은 로컬 설정·운영 확인이며, 추가 UI를 만드는 것으로 해결되지 않는다. 미검증 가격 단위/시각의 채널을 임의로 열지 않는다.

## 작은 변경 범위와 API

생산 소스는 `execution_control/controller.py`와 `execution_launch/runner.py`만 변경한다. 기존 wire, permission/capability engine, account/guard stores, source verifier, strategy/evaluator, Coordinator, transport, E deadline 기록은 변경하지 않는다.

제안 public seam:

```python
@dataclass(frozen=True, kw_only=True)
class CommittedControllerObservation:
    account: AccountObservation             # repr=False
    risk: RiskResult | None                 # repr=False; read route는 None
    committed: CommittedAccountProjection   # repr=False; local provenance
    completed_at: datetime                  # actual I3c final clock
    # execution_ready=False; no source-authentication/current-use permission

Controller.observe_committed(*, now, session_id=None) -> CommittedControllerObservation
# actual risk-observe route: risk is exact RiskResult
Controller.read_committed_account(*, now, session_id=None) -> CommittedControllerObservation
# explicit-exit account-read route: risk is None
```

두 API는 exact CommittedAccountProvider를 가진 실제 Controller만 사용한다. caller가 account/risk/Context/반환 view를 넣는 인자는 없다. 기존 observe(now)는 반환 RiskResult와 동작을 보존한다. observe_committed는 기존 observe와 private 위험 관측 core를 공유해 한 호출에서 existing risk snapshot을 한 번 기록하고 동일 actual tx에서 최종 검증을 마친 실제 account/risk/projection을 함께 반환한다. read_committed_account는 아래의 별도 비주문 계좌 읽기 계약을 따른다. `_last_account` 캐시나 public dataclass를 권한으로 재사용하지 않는다. I3c private recheck의 내부 반환형을 좁게 확장해 실제 마지막 `_AccountRead`를 전달한다. final physical tx/head와 owner 검증에 사용한 그 read에서 account/committed를 꺼낸다. observe_committed에서만 동일 final read와 기존 `_risk_view`로 비교가 통과한 RiskResult를 짝지우며, read_committed_account에서는 이 계산/비교 없이 risk=None을 반환한다. 최초 read의 account와 뒤의 다른 risk를 섞거나 캐시에서 꺼내지 않는다. 현재 suffix의 daily stop/영구 halt/high/floor는 final account/projection에 보존하고, observe 결과에는 RiskResult에도 보존한다. 이 내부 반환형은 public proof token이 아니다. 이 타입 자체를 직접 구성한 것은 허가가 아니며 별도 issued registry나 cryptographic seal을 만들지 않는다. 기존 trusted composition에서 Runner가 exact Controller의 실제 메서드를 직접 호출하고 반환값을 같은 호출 흐름에서만 소비하는 것으로 충분하다. 외부 view/Projection/tuple을 public tick 입력으로 받지 않는다. observe operation은 기존 risk_snapshot/halt와 owner.load_context의 snapshot 기록을 수행할 수 있으므로 read-only API라고 부르지 않는다; 반환값만 비권한 데이터다. read_committed_account도 actual owner.load_context가 기존 owner snapshot을 기록할 수 있으므로 전체 filesystem 무쓰기라고 주장하지 않는다. 새 Controller journal/risk/halt 쓰기가 없는 계좌 읽기다.

`session_id`는 실제 owner.load_context와 I3c 재검증에 그대로 전달한다. 일반 tick의 기존 observe는 None 의미를 유지하고, 명시 exit의 read_committed_account는 기존 `_exit_session_id()`로 대조한다. head가 같아도 효력 한도/세션이 다를 수 있으므로 임의 None 치환을 하지 않는다.

Runner는 두 경로를 명확히 구분한다.

1. legacy callable provider: 기존 API/기본 observe 경로 유지.
2. exact CommittedAccountProvider: 첫 단계는 **mode='rehearsal'만 허용**, 실제 같은 Controller/provider 객체·같은 policy·기존 isolated root·DryRunAdapter 조건 필수. observe/controlled를 묵시 지원하지 않고 고정 `RUNNER_COMMITTED_REHEARSAL_REQUIRED`로 거절한다. duck type/read method/람다로 소비 경계를 대체하지 않는다.

Tick에서는 기존 durable-order reconcile을 먼저 수행한 뒤 실제 `controller.observe_committed(now=now)`를 정확히 한 번 호출한다. 그 결과의 account와 risk만 같은 tick의 quote/decision/preflight에 사용한다. 같은 tick에 다시 controller.observe와 provider(now)를 호출하지 않는다. `_observations`의 private 분기는 이 내부 결과만 받고 기존 quote/account scope·나이·완전성 검사를 그대로 적용한다. public tick에는 observation override를 추가하지 않는다.

Explicit `submit_exit`는 **read_committed_account만** 사용해 risk=None인 실제 결과에서 account를 얻고 기존 reserve/dispatch를 호출한다. 일반 위험 관측 observe_committed를 앞에 실행하지 않는다. 이 읽기 계약은 다음과 같다.

- 실제 같은 provider와 하나의 실제 열린 Journal tx, actual account read·현재 positions와 정확한 exit session의 owner, I3c final clock·actual head/physical journal 검증은 모두 유지한다. 같은 방법의 final `_AccountRead`에서 account/projection/completed_at를 반환한다.
- `_snapshot_risk`, `_risk_view` 결과 일치 조건, 신규 risk_snapshot/halt/예약 쓰기, research 선발, entry session/odds gate를 실행하지 않는다. I3c private recheck에서 observed_result=None인 읽기 분기를 재사용할 수 있으며 public caller가 내부 mode flag를 지정하게 하지 않는다.
- account/projection에는 이미 확정된 high/floor/daily-stop/permanent halt를 그대로 보존한다. 이 값이 보수적으로 강화됐거나 risk.new_entry_blocked라는 이유만으로 건강한 계좌 읽기나 명시 exit를 거절하지 않는다. 손상·stale·시계 역행·owner/epoch 불일치 등 현재 데이터/권한 경계는 계속 거절한다.
- 반환 view는 매도 허가가 아니다. 실제 기존 `_authorize(sell)` 및 reserve/dispatch가 현재 holdings·수량·약정·수수료·current owner/gate·I3c 완료 시각으로 허용 여부를 결정한다. 새 view risk=None을 reduce 허가 bool로 해석하지 않는다.

error/restart/deadline 자체에서 SELL을 만들지 않는다. 기존 research expiry·stop 뒤의 명시적인 검증된 reducing exit/cancel 경로를 유지한다. 실제 reserve/dispatch는 I3c를 포함한 Controller 검증을 다시 수행하므로 view 반환 시점 이후 owner/head/clock 변경을 허가로 우회할 수 없다.

관측 이후 오래 걸린 quote/driver 작업은 원 account 시각을 갱신하지 않는다. Runner가 전략을 계산한 시각과 create admission 시각은 구분하며 최종 create는 현재 Controller가 거절할 수 있다. `completed_at`은 유한 관측 시각이지 source freshness 연장이나 send lease가 아니다.

## 실제 검증의 최소 수직 경로

새 `tests/launch_committed_runner.py`에서 기존 실제 임시 서명 owner log·baseline/guard stores/head·Journal·guard commit·CommittedAccountProvider·Controller를 사용한다. source/path/coverage는 합성 fixture라고 명시하고 실제 API는 없다. 기존 Runner의 driver/review/session 발급 helper를 재사용하며 수익 결과·issuer registry·approval flag를 만들어 넣지 않는다.

- actual committed holder → actual Controller 완료검증 묶음 → Runner tick의 실제 decision input까지 account/risk가 같은 관찰인지 확인. held/flat·daily stop·peak/floor/halt가 유지되고 baseline/guard advance·CAS는 0회.
- 유효한 명시 reducing signal → actual read_committed_account(risk=None) → Runner.submit_exit → 실제 Controller reserve/dispatch → 실제 DryRunAdapter capability 소비가 정확히 한 번. read 단계의 _snapshot_risk/risk-result equality/신규risk·halt 쓰기를 금지하는 회귀를 둔다. daily stop/영구halt/stop/research expiry와 보수적인 control risk suffix 변화만으로 기존 independently allowed reduce를 일괄 차단하지 않음. tick의 risk-result 동일성 요구는 그대로 유지한다.
- 보관 source binding 불일치/stale account/늦은 quote/owner 변경/head 교체/계산 오류/서명 실패에 create=0; 오류를 SELL로 바꾸지 않음. 실제 늦은 fill/미체결은 기존 대조가 확인해야 하며 옛 endpoint를 최신 계좌로 부풀리지 않음.
- current risk 보호 때문에 buy가 막히는 사례, 실제 발급 PreparedSession이 준비되는 기존 fixture가 있으면 동일 positive dry buy도 검사. 실제 발급 없이 armed/eligible bool로 양성 사례를 채우지 않음.
- pending RESERVED는 기존 Runner startup 로컬 cancel 규칙, DISPATCHING/UNKNOWN은 기존 status/reconcile 우선과 no-create-retry 규칙 유지. 같은 client의 중복 tick/exit는 중복 create를 만들지 않음.
- 실제 transaction 중첩/Journal.snapshot 중첩/발급 view clone 주입은 불가. 반환값 이후 실제 source/head/owner가 바뀌면 reserve/dispatch가 다시 거절함.
- exact committed controlled/observe constructor는 early refusal. 같은 provider identity·dry adapter·isolation 조건과 legacy callable 회귀 유지. carry E gate와 현재 controlled 거절도 유지하지만 E의 Controller 전달 완료를 주장하지 않음.

완료 기준은 **현재 실제 consumer 단절을 메워 같은 검증 계좌·위험 관찰로 Runner의 모의 의사결정 및 기존 dry control을 실행**하는 것이다. 새 운영 기본값·scheduler·계좌키·소유자 승인·실주문을 만들지 않는다.

## 그 뒤에도 남는 최소 외부/운영 조건

실제 Upbit 계좌 identity/history retention와 현재 continuous coverage 계약을 충족하는 생산 source adapter가 아직 없다. 이는 코드에 이미 요구된 계약이며 이 카드에서 더 강한 보장을 추가하지 않는다. 지원 가능한 공급 자료의 의미를 조사·구현해야 하며 로컬 서명이나 사용자 입력 한 줄로 완전성을 간주할 수 없다.

실제 pre/post owner 관찰, 현재 baseline/guard/control predecessor 결합, 확정 package 보관과 commit 뒤 publication, transport 마지막 send 경계, 실제 계좌 설정·유효 code/limits/전략/활성화 승인은 별도다. 사용자 입력이 없어도 위 consumer 단위의 코드·hermetic 검증은 가능하다. 실제 시장 수익·무손실·모든 순간의 가격 관측을 보장하는 새 요구를 만들어 이 작업을 늘리지 않는다. 기존 손실 하한·일중 한도·기한만으로 매도하지 않는 정책은 그대로 유지한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
