# P2-I2: Controller의 확정 계좌 관측 소비 설계

2026-11-13. 읽기 기준: `/workspace/tradegen-guard-projection-1113`의 실제 Controller/Journal/owner fold와 `TRADEGEN_PROTECTIVE_P2_INTEGRATION_API_2026-11-13.md`. I1 source와 Controller는 수정하지 않았다. 실제 코드 연결 설계이며 완료된 runtime 검증·실계좌 출처 인증·운영 승인이 아니다.

## 최소 다음 변경

I1의 `CommittedAccountProvider.read(now=..., transaction=...)`를 **이미 열린 실제 Controller transaction** 안에서 읽는다. 관측과 guard 일중 정지를 명시적으로 같이 전달한다. 기존 callable provider, exact AccountObservation 검사, 주문·위험·승인 절차를 그대로 유지한다. Coordinator의 controlled 거절과 continuous live source 거절은 해제하지 않는다.

생산 파일 소유는 Controller 한 담당으로 제한한다. I1 helper/provider는 그 담당에게서 호출만 한다. I2에 baseline advance/commit, guard commit, head CAS/seed, P2 writer, source 수집, 자동 활성화를 넣지 않는다.

```python
@dataclass(frozen=True, kw_only=True)
class _AccountRead:
    observation: AccountObservation
    committed: CommittedAccountProjection | None

# 공개 API/기존 callable provider signature를 바꾸지 않는 내부 seam
Controller._account(now, transaction: Transaction, order=None) -> _AccountRead
Controller._snapshot_risk(tx, obs, now, orders, ctx, *, committed=None)
```

`type(account_provider) is CommittedAccountProvider`일 때만 `.read(now=now, transaction=tx)`를 호출한다. 임의 `.read` duck type, callable이 반환한 projection, caller-supplied projection은 승인 입력으로 받지 않는다. 기존 경로는 `account_provider(now)`를 호출하고 **exact AccountObservation**을 요구한 뒤 `(obs, None)`으로 감싼다. committed_account가 AccountObservation을 import하므로 새 provider 타입 import는 Controller의 소비 함수 안에서 수행해 import cycle을 피한다. 모든 기존 시각·server day·risk.asof·계좌 범위·무신용·금액·환율·노출·equity 일치 검사를 공통으로 수행한다. provider 실패를 기존 provider로 fallback하거나 마지막 정상 관측의 시각을 바꾸지 않는다.

현재 `_account` 내부 호출 지점 7곳(`observe`, `approve_floor_relaxation`, `_authorize`, `cancel`, `reconcile`, `kill`, `halt`)에 actual tx를 전달한다. `_authorize`가 reserve와 dispatch 양쪽에서 쓰이므로 영향을 받는 public 메서드는 8개다. kill/halt의 시계 확인 실패에도 기존 restrictive journal 기록을 남기는 동작은 유지한다. `_authorize`의 외부 반환형은 그대로 유지한다. observation과 metadata를 인스턴스 mutable cache에 분리 저장하지 않는다.

## metadata와 현재 owner의 별도 경계

I1 결과의 `policy_day`, `daily_stopped` 외에 다음 두 **비인증 자료 필드**를 보존하는 것이 최소다.

- `owner_claim: OwnerContextClaim`: 원래 확정 package의 `owner_after` 전체. caller가 새 한도를 끼워 넣은 대체 claim이 아니다.
- `policy_sha256`: 원래 확정 guard/package의 정책 hash.

GuardCheckpoint 자체에는 signed daily limit과 code-approval hash가 없으므로 owner head만으로 아래 비교를 수행할 수 없다. 이 필드 추가는 실제 owner 인증을 발급하지 않는다. `source_sha256` 일치는 과거 owner 관찰의 진위를 증명하지 않는다.

Controller는 기존 `_positions(obs, current_orders, exclude)`로 현재 미체결·예약을 합친 positions를 만들고, **실제 `owner.load_context(now, positions, session_id=...)`** 결과를 사용한다. 과거 claim의 Context를 재사용하거나 review용 placeholder positions를 쓰지 않는다.

새 guard 경로의 좁은 검사는 다음과 같다.

1. actual Context의 exact type/seal/context hash, 현재 서울 날짜, owner.ok, code_signed와 현재 코드 hash를 확인한다. 권한을 주장하는 경로의 기존 active/session/gate 검사는 그대로 유지한다.
2. `content_digest(self.policy)`와 확정 policy hash, actual owner head의 row hash와 claim의 owner_head_sha256, actual code hash와 claim.code_sha256를 비교한다.
3. `code_approval_sha256`는 현재 효력 있는 code_approved의 **승인 코드 hash 값**으로 의미를 고정한다. approval row hash와 혼동하지 않는다. actual Context.code_signed가 True라는 검증 아래 actual approved code hash는 context.code_hash와 같아야 한다. 기존 synthetic claim은 그 자체로 이 검사를 통과한 인증이라고 표시하지 않는다.
4. actual `ctx.owner.limits`에서 해당 session과 현재 서울 날짜에 실제 효력이 있는 floor/daily 값을 정확한 Decimal 표현으로 읽어 원래 claim의 두 값과 대조한다. 누락·비유한·부적합 값, 다른 값은 거절한다. 같은 head에서도 D12의 자정·session 상태에 따라 유효 한도가 달라지므로 head 일치만으로 통과하지 않는다.
5. 현재 guard는 owner/code/policy epoch 변경과 승인된 하한 완화의 이행을 구현하지 않았다. 바뀐 head/코드/한도를 임의 max()·head 교체·anchor 재생성으로 흡수하지 않는다. 현재 owner의 halt/철회/효력 조건을 삭제하지 않고 새 guard epoch가 필요함을 표시한다.

이 검사는 현재 owner와의 불일치를 거절하는 경계다. package의 과거 pre/post owner/source completeness 인증은 별도 실제 issuer가 필요하며, I1 로컬 commit과 이 비교만으로 과거 source가 진짜였다고 주장하지 않는다.

## completion prefix와 현재 control fold

I1이 receipt와 prefix를 검증한 후에도 Controller는 동일 transaction의 **현재 전체 events**를 `_fold`한다. receipt.control_head는 현재 끝과 같을 필요가 없다.

- matched PREPARE → 필요한 halt → COMPLETE와 exact predecessor/후속 store heads는 I1이 확인한다. idempotent commit retry의 receipt가 COMPLETE 뒤 risk_snapshot/kill 행을 가리키는 경우도 검증된 prefix로 인정한다.
- 그 뒤 정상 risk_snapshot, kill, order/reconcile 행은 새 control 이력이다. 현재 예약·약속 매도 수량·UNKNOWN/PARTIAL/CANCEL_REQUESTED·재시작 대조 요구를 다시 fold하고 기존 검사를 사용한다.
- COMPLETE 누락·중복, receipt prefix 롤백/미존재, 뒤의 미완료 PREPARE, 다른 guard/baseline head는 I1이 거절한다. 소비자가 이를 우회해 projection.observation만 꺼내 쓰지 않는다.
- 기존 `_fold`의 시간·일중 opening equity·permanent halt·peak/floor·daily stop 단조 조건을 유지한다. 새 risk_snapshot을 기록한 뒤 같은 projection을 다시 읽을 때 정상 suffix를 허용하되 최신 latch를 지우지 않아야 한다.

Journal.snapshot/transaction 중첩 0, baseline reduction/commit 0, head CAS/seed 0이다. 실제 tx의 active/thread-local identity와 exact Journal 소유 확인을 그대로 사용한다. publication lock을 보유한 채 Journal에 진입하지 않는다.

## 위험과 행동의 의미

`_snapshot_risk`는 공통 기존 risk 평가 후 아래 정보만 추가로 보존한다.

- `committed.policy_day == now.astimezone(KST).date()`를 요구한다. 관측 asof/서버 날짜에 대한 기존 조건도 유지한다.
- 현재 일중 정지 = 기존 같은 날 risk_snapshot 정지 OR 확정 guard.daily_stopped OR 현재 정책/서명한도의 stop 조건이다. True이면 기존 `PERSISTENT_DAILY_STOP`, `new_entry_blocked=True`, `protective_action_needed=True`를 사용하고 **현재 receipt 시각**의 기존 risk_snapshot에 기록한다.
- guard의 peak/floor/daily-loss/permanent-halt는 I1에서 이미 보수적으로 투영됐고, Controller의 더 최근 high/floor/halt와도 충돌 없이 유지해야 한다. 같은 날 opening denominator가 다르면 거절한다. daily_stopped를 permanent halt나 가짜 손실 금액으로 바꾸지 않는다.
- 전날 left-limit 위반은 원래 guard prepare.required_records에 남는다. 오늘 risk_snapshot을 전날로 소급 작성하지 않고, 전날 daily-stop을 새날의 stop으로 복사하지 않는다. lifetime peak/floor/permanent halt는 날짜가 바뀌어도 유지한다.
- `approve_floor_relaxation`의 legacy 경로는 유지한다. 새 guard 경로에서는 guard epoch 전환이 없는 하한 감소를 수행하지 않는다. 현재 I1도 post-commit 승인 완화/epoch 변경을 거절하므로 Controller만 먼저 낮추지 않는다.

| 호출/행동 | I2 처리 |
|---|---|
| observe / 보유 감시 | actual 확정 관측과 현재 owner/control로 위험 상태 기록. 실패는 관측 불가/새 진입 차단이다. 실패를 상승 전망이나 보유 전략 판단으로 표시하지 않는다. |
| reserve/dispatch 매수 | 기존 일중 stop, permanent halt, kill, pending guard, 주문 불확실성, capacity, signed floor, session, gate/permit을 모두 유지한다. projection 자체는 매수 허가가 아니다. |
| 명시적 매도 | 일중 진입 정지를 단순 전체 주문 금지로 바꾸지 않는다. 검증된 보유·약속 수량, 현재 시장/주문 규칙, 실제 owner/conduct/gate, 기존 전략·관리 권한이 필요하다. I2는 매도 신호를 만들지 않는다. |
| cancel/reconcile | 실제 현재 tx와 fresh account를 사용하고 기존 주문 식별·수수료·잔량·fill 대조를 유지한다. 실패 시 주문을 terminal로 꾸미거나 예약을 해제하지 않는다. RESERVED의 기존 로컬 취소는 불필요한 계좌 읽기를 추가하지 않는다. |
| 기한·저장 실패·재시작 | 신규 매도 원인 아님. P2 outbox의 consider_reduce도 주문 권한 아님. 실제 보유 감시/대조가 불가능하면 그 상태를 사실대로 유지한다. |

기존 GTC 주문의 뒤늦은 체결은 새 주문 생성과 다르다. 새 committed package와 control reconciliation으로 처리하며 duplicate create/exit를 만들지 않는다. fixed GTC를 IOC·시장가로 바꾸지 않는다. E 이후 기존 driver/history 기간을 늘리지 않는다.

## 시각의 정확한 한계와 후속 실제 bridge

I1은 `read(now=...)`를 받으며 clock을 보유하지 않는다. 기존 Controller도 메서드 인자로 받은 now로 관측·owner·rule 시각을 검사한다. 무거운 store/account/owner 처리 뒤 실제 완료 시각을 읽는 계약은 없다. 따라서 **I1/I2의 입력 now 검사만으로 완료·dispatch 순간의 freshness를 증명했다고 보고하지 않는다.**

carry Runner의 기존 fresh clock gate는 E를 막지만, Controller 내부의 무거운 작업 뒤 계좌/owner freshness를 독립적으로 보증하는 장치는 아니다. 실제 live bridge를 연결하기 전에는 신뢰된 completion clock 또는 Controller 내부 마지막 caller 재검증 seam을 명시적으로 추가해야 한다. 그 seam은 원래 observation.asof와 최초 owner 관찰 시각을 보존하고 완료 시각으로 account age/server day/효력 한도와 실제 owner/code를 다시 확인해야 한다. 원래 관측을 새 timestamp로 바꾸지 않는다. 이 후속 시간 경계가 없는데 controlled 운용을 열지 않는다.

그 후 Coordinator의 수집·진짜 coverage/owner 인증 → commit 완료 → 실제 stores/heads/readback 확인 → 짧은 publication 단계가 들어간다. commit은 Controller 밖에서 끝내고 holder만 공개한다. 현재 StagedContinuousCandidate의 preview/digest만으로 빠진 원본 receipt·captured accounts·pre/post owner 관측을 복원하지 않는다. P2 writer도 Controller 진입 전에 닫는다. 새 관리 승인이나 연구 서명으로 누락된 source completeness를 대체하지 않는다.

## 단계별 검증과 완료 기준

1. **Legacy parity**: 기존 callable AccountObservation fixture로 observe/reserve/dispatch/cancel/reconcile 회귀 유지. callable이 projection/dict/True를 반환하거나 임의 read-only duck type이 와도 거절.
2. **실제 I1→Controller**: 실제 임시 Journal/두 store/head/완료 receipt를 사용한다. Controller의 actual tx가 전달되고 snapshot/추가 transaction/advance/commit/CAS가 0인지 검증. repeated observe 후 정상 risk_snapshot suffix와 idempotent receipt prefix 재사용 확인.
3. **Risk 보존**: peak→trough→recovered endpoint, guard-only same-day daily stop, 후속 control의 더 강한 risk/halt, 같은 날 opening 충돌, 자정 left/right, old-day stop 비전파. 신규 주문 생성 없이 observe에서 retained daily stop이 durable 행으로 남는지 확인.
4. **Actual owner 경계**: 임시 실제 owner 서명/fold를 사용해 code/head/한도 불일치와 **같은 head의 자정 D12 효력 변경**, session별 완화 적용 차이를 검증한다. forged sealed/caller Context나 임의 verifier True로 통과시키지 않는다. 과거 synthetic source claim의 진짜 인증은 여전히 주장하지 않는다.
5. **현재 control suffix**: receipt 뒤 kill/UNKNOWN/partial/추가 reserved가 새 매수와 capacity에 반영됨. 이후 guard prepare, head/store 변경·rollback은 거절. 소스 실패·재시작·E만으로 새 매도/취소 호출 0; 기존 주문 late fill은 별도 대조.
6. **활성화 경계**: actual controlled composition/live candidate refusal 유지. 새 패치의 성공은 합성 자료의 transaction/risk 소비 연결이며 production completeness·관리 승인·post-E 실행 준비 판정이 아니다. 실제 Windows·실계좌 검증을 실행하지 않았다면 NOT_RUN으로 기록한다.

소스 변경 후 실제 factory dependency closure와 독립 signer의 대응 목록에 새 consumed module을 같은 범위로 포함하고 전체 D14/current code 검증을 유지한다. 이전 코드 서명을 새 코드 승인으로 재사용하지 않는다. root가 guard/registry/통합 회귀를 소유한다.

## 실제 codec 구분

GuardCheckpoint.policy_sha256는 execution_accounts.model.content_digest를 사용한다. Controller risk_snapshot.policy_digest는 execution_control.capability.digest를 사용하며 exponent Decimal 표현에서 결과가 다를 수 있다. guard epoch 비교에는 전자, control suffix 비교에는 후자를 그대로 사용한다. 두 문자열이 같다고 가정하거나 한쪽 codec으로 기록을 바꾸지 않는다.

## I2 개발 확인

2026-11-13 소유 구현은 Controller와 새 control_committed_account 회귀 모듈이다. 실제 현재 owner halt가 있는데 projection의 permanent-halt가 누락된 경우도 COMMITTED_ACCOUNT_OWNER_HALT_NOT_RETAINED로 거절한다. 원래 파일은 LF이므로 LF를 보존했다. 개발 3차는 16/16 PASS(19KEYLESS, 임시 owner/store/head, 실제 임시 서명, DryRunAdapter만)이며 root 통합 회귀는 별도다. 1차14건 중13PASS/1fixtureFAIL(날짜가 다른 원래 historical fill), 2차16건 중15PASS/1fixtureFAIL(변경한 원본 page hash 재생성 누락) 기록도 보존했다. 두 오류 모두 fixture를 정상 원본 계약에 맞춰 수정했으며 실제 검증을 완화하지 않았다.
