# TRADEGEN 업무처리 워크플로우

기준: 2026-11-13 18:27 KST. PR 4c 병합·PR 4d 원안 전체 검사 완료 기록이며 capacity 승인·해결과 PR34 병합은 대기 중이다. 전체 실거래 준비 완료 판정은 아니다.

## 1. 근거와 현재 상태

- [Claude CURRENT](https://github.com/xkg4real/tradegen/blob/handoff/CURRENT.md): 2026-11-12 16:53 KST 인계.
- [구현 계획 index](https://github.com/xkg4real/tradegen/blob/971a5389208c85d34fdd6479c96580e9b8fcc68d/docs/superpowers/plans/2026-11-11-upbit-krw-universe-index.md): 승인된 유니버스 rev 3의 의존성과 계약.
- [진행 기록](https://github.com/xkg4real/tradegen/blob/handoff/context/upbit-universe/universe-impl-status.md), [완료 원장](https://github.com/xkg4real/tradegen/blob/handoff/LEDGER.md).
- [업무 기록 Notion](https://app.notion.com/p/40f5c916fe0c80b49d10fec810a95cbb), [승인 전 정리 Notion](https://app.notion.com/p/40d5c916fe0c80e49e2bd9f3fc1c2145).
- GitHub 확인 기준 PR33 병합 main: `7d256f9090bb4de593bf496b010a9753ae5508fd`.
- PR 4c는 Claude가 사전 점검 중 중단한 뒤 GPT가 최신 main에서 대조·구현했다. 아래 최신 체크포인트를 따른다.
- Claude의 마지막 실행 기록: PR 4a head `56a0b7f`, 2,547 PASS / 2 FAIL / 123 NOT_RUN, 총 2,672개.
  실패 2건은 인계문서상 checkout의 가상환경 위치 문제다. 이번 Cloud 실행 결과로 취급하지 않는다.
- 유니버스 전략의 실제 수익성과 목표 달성 확률은 아직 검증되지 않았다. 연구 도구 구현과 실제 연구 통과를 구분한다.

### 최신 완료: universe-pr4c 구현·검증·병합

- ~~PR 4c Tasks 1–10 구현·독립 리뷰·전체 검증·병합~~ 완료.
- [PR #33](https://github.com/xkg4real/tradegen/pull/33)은 2026-11-13 **17:46:10 KST**에 병합됐다.
  병합 커밋은 `7d256f9090bb4de593bf496b010a9753ae5508fd`, 최종 head는 `b21439ca4b97151028ac3ba9659c1c5fbc69dd27`이다.
- 최종 실행 소스 `c80c56cdab946a80ae40be31432b41c881dcd5a2`의 전체 검사:
  **총 2,705개 / 2,570 PASS / 0 FAIL / 135 NOT_RUN**, 소요 **1,093.970초**.
  이후 최종 head의 변경은 문서뿐이며 검증한 런타임·테스트는 동일하다.
- 미실행은 매크로 선행 조건 121건과 Windows 전용 14건이다. 통과로 합산하지 않았다.
  검사 전후 소스와 실제 홈 메타데이터가 동일했다. 기준 2,672개 ID는 stale-book 검사 이름 정정 1건 외에 유지했고,
  새 ID 34개는 모두 PASS다(이름 정정 포함, 순증 33개).
- 앞선 `8137c47`의 전체 2,569/0/135와 이후 `RecursionError` 수정 40 PASS 기록은 이력으로 보존한다.
  이 수치를 최종 실행 결과에 합산하지 않는다.
- 앞선 고정 소스 경계 검사: **81 PASS / 0 FAIL / 0 NOT_RUN**. 당시 검사 전후 소스와 실제 홈 메타데이터가 동일했다.
- 앞선 집중 검사: IOC 56 PASS, collector/provider 106 PASS, E1 119 PASS, readiness 18 PASS,
  비유한 보유량 방어 16 PASS. 범위가 겹치므로 이 수치를 합산하지 않는다.
- [최종 소스 실행 기록](https://github.com/xkg4real/tradegen/blob/b21439ca4b97151028ac3ba9659c1c5fbc69dd27/docs/universe-pr4c-execution-log.md).
  앞선 handoff `7e16536`·`650d3fb`의 push는 확인됐다. 최종 인계 commit/push는 주 작업 세션에서 별도로 기록한다.
- **추가 설계 2건의 사용자 클릭 승인은 대기 중**이다: PR 4d capacity 처리, PR 5 실패한 연구의 인증된 결과 기록.
  PR 4d capacity 승인 대기는 Task 2의 최종 대체 경로 변경에 한정된다. 기존 승인된 Tasks 1–4 구현은 아래 초안 PR에 보존했다.
  소유자 `floor_state_check` 고정 결과 코드 답변도 별도로 대기 중이다. 최종 전자서명은 전체 필수 코드가 정리된 뒤다.
- 실제 API 호출·전자서명·무장·주문·실제 전략 통과를 수행하거나 완료로 표시하지 않았다.

### PR 4d 원안 Tasks 1–4 구현·독립 리뷰·전체 검사 완료, PR34 병합 보류

- ~~PR 4d 원안 Tasks 1–4 구현·독립 리뷰~~ 완료. Task 2는 기존 승인 원안만 구현했으며 알려진 capacity 공백은 남아 있다.
- [초안 PR #34](https://github.com/xkg4real/tradegen/pull/34): **open / draft / 미병합**.
  현재 head `a54a390d14d665a93bb8779ac078c8ea113c69f2`, base `7d256f9090bb4de593bf496b010a9753ae5508fd`를 원격에서 확인했다.
  이 head는 실행 소스 `ea4e2a4925922ce468208c89020881cb01a08403`에 `docs/universe-pr4d-execution-log.md`만 갱신한 커밋이다.
- 영향 모듈 통합 검사 **60 PASS / 0 FAIL / 0 NOT_RUN, 7.445초**.
  경계 guard 5개 모듈 **81 PASS / 0 FAIL / 0 NOT_RUN, 11.953초**. 서로 겹치는 수치이므로 합산하지 않는다.
- 두 실행의 고정 소스 fingerprint는 `1aac24a84d06886bdc132fc36bbab4428978f366dc86f8d8b22edba3886c9cfe`로 같고
  전달 커밋의 런타임과 일치한다. 소스·실제 홈 메타데이터도 불변이다.
- ~~PR 4d 원래 구현의 전체 검사~~ 완료. `pr4d-original-full`은 18:07:28 KST에 소스 `ea4e2a4`를 동결해 시작했고,
  **총 2,719개 / 2,584 PASS / 0 FAIL / 135 NOT_RUN**, **1,105.243초**로 끝났다.
  PR 4c 기준 ID 2,705개를 모두 유지했고 신규 14개는 모두 PASS다. 미실행은 동일한 매크로 선행 조건 121개·Windows 전용 14개다.
  전체 실행에서도 같은 fingerprint와 소스·실제 홈 메타데이터 불변을 확인했다. 기존 집중 검사 숫자와 합산하지 않는다.
- 별도 실제 코드 경로의 합성 probe: collector가 검증한 보유 항목 1,500개, 가짜 조회 1,522회,
  131,072바이트 book 입력에서 첫 fallback 뒤 이력 행이 **279,312바이트 > 262,144바이트 한도**로 남는다.
  `HISTORY_STORE_RECORD_INVALID`로 거부되며 journal·독립 head·slots·chooser 상태는 모두 변하지 않았다.
  probe PASS는 **알려진 차단 재현과 거부 동작 확인**이며 capacity 결함을 고친 결과가 아니다. 실제 API 조회는 없었다.
- 두 번째 fallback이나 새 admission/capacity 계약은 구현하지 않았다. **원안 전체 검사 통과는 알려진 capacity 공백을 해결하지 않는다.**
  capacity 결정과 공백 해결 전 **PR34 최종 병합은 보류**한다. 후속 런타임 수정에는 독립 리뷰와 새 검증이 필요하다.
- 다음 PR 4e 코드는 병합된 PR 4d에 의존한다. PLB 구현은 병합된 PR 5와 소유자 상태 증거에 의존한다.
  추가 설계 승인 2건과 `floor_state_check` 고정 결과 코드 답변은 모두 대기 중이다.
- [PR 4d 최종 실행 기록](https://github.com/xkg4real/tradegen/blob/a54a390d14d665a93bb8779ac078c8ea113c69f2/docs/universe-pr4d-execution-log.md).
  이전 Task 1 `d34395b`의 31/31 PASS(3.427초)는 아래 이력에 보존한다.

### 기존 잔여 업무의 의존성 사전분석 완료

- `production-readiness-dependencies.md`와 `plb-dependencies.md`를 현재 소스 `c80c56c`에서 읽기 전용으로 작성·대조했다.
  기존 task의 의존성 근거이며 새 파생업무나 완료된 구현이 아니다. 이 분석은 코드/테스트 수정·실행을 하지 않았다.
- 11월 12일 승인된 최신 설계의 순서는 **유니버스 PR 5 → PLB → L1 live launcher → L2 현재 planner → L3 standing deployment + A1 protective hold**다.
  설계 문서에 승인 기록이 있지만 실제 런타임 구현은 아직 없다. 기존 standing 안전정지 매도 규칙은 A1의 보호 보유 정정과 대조해야 한다.
- 실제 보유 구간의 완전성을 보증하는 source 계약은 미확정이다. 표본 호가·잔고 조회, heartbeat, 자료형 또는 로컬 hash를 완전성 증거로 간주하지 않는다.
- `Controller.observe`가 이미 journal transaction을 잡으므로, provider에서 `commit_continuous_guard`를 그대로 호출하면 중복 잠금 위험이 있다.
  하나의 journal transaction 안에서 독립 head·저장소와 위험 기록이 일치한 뒤 관측을 게시하도록 연결해야 한다.
- **PLB O1–O16의 기본 결정은 이미 승인됐으며 재질문하지 않는다.** PLB 구현 계획은 유니버스 PR 5가 병합된 main 기준으로 작성한다.
- **별도의 소유자 상태 증거가 대기 중**이다. PLB §9.3 step 0 / O14에 따라 실제 운영 home의 `floor_state_check` S1–S12 결과가 있어야 조건부 구현 범위를 확정한다.
  실행 여부와 고정 결과 코드만 이미 요청했고 답변을 기다린다. 금액·키·실제 로그를 요청하지 않는다. 단순 exit 0이나 과거 `--check OK`는 이 증거를 대신하지 않는다.
- 위 상태 증거 요청은 PR 4d capacity / PR 5 실패 연구 인증 결과의 **새 설계 승인 2건과 구분**한다.
  승인됐던 PLB 선택지를 다시 승인받는 요청이 아니다. PR 4c의 최종 전체 검증·병합 완료와도 별개다.

근거: [L1/L2 설계](https://github.com/xkg4real/tradegen/blob/c80c56cdab946a80ae40be31432b41c881dcd5a2/docs/superpowers/specs/2026-11-12-controlled-launch-and-planner-design.md),
[L3 설계](https://github.com/xkg4real/tradegen/blob/c80c56cdab946a80ae40be31432b41c881dcd5a2/docs/superpowers/specs/2026-11-12-standing-deployment-design.md),
[A1 정정](https://github.com/xkg4real/tradegen/blob/c80c56cdab946a80ae40be31432b41c881dcd5a2/docs/superpowers/specs/2026-11-12-standing-protective-hold-design.md),
[PLB 설계](https://github.com/xkg4real/tradegen/blob/c80c56cdab946a80ae40be31432b41c881dcd5a2/docs/superpowers/specs/2026-11-11-principal-loss-budget-design.md).

### 보유 구간 완전성: 공식 Upbit 문서 대조 근거

- `held-source-official-docs.md`의 2026-11-13 17:44 KST 확인 기록을 검토했다. 공식 문서만 읽었으며 거래소 API·WebSocket·실제 계좌를 관측한 결과가 아니다.
- [MyOrder](https://docs.upbit.com/kr/reference/websocket-myorder)는 주문/체결이 없으면 전송하지 않으며,
  [MyAsset](https://docs.upbit.com/kr/reference/websocket-myasset)은 자산 변화가 없을 때의 침묵과 초기 수분 지연을 명시한다.
  침묵이나 heartbeat를 빠진 이벤트가 없다는 증명으로 바꿀 수 없다.
- [공개 체결 이력](https://docs.upbit.com/kr/reference/list-pair-trades)의 cursor 조회와
  [재접속 지침](https://docs.upbit.com/kr/docs/websocket-best-practice)은 유용한 기능이지만,
  확인한 문서에서 계좌·호가·체결·수수료를 공통 순서로 완전하게 연결하는 재전송/최종 watermark·지연 상한 계약까지 확인되지는 않았다.
- `sequential_id` 순서는 과거 변경 공지의 보장 표현과 검색으로 확인한 공식 v1.6.4 스키마의 비보장 표현이 충돌한다.
  버전 URL의 직접 열기는 현재 페이지로 이동하므로 후자는 검색 색인의 공식 스키마 근거로 구분한다.
  현재 authoritative schema 또는 거래소 설명 없이 공통 순서나 누락 검출 보장으로 승격하지 않는다.
- 결론은 **현재 확인한 근거로 production completeness verifier를 승인할 수 없음**이다.
  적합한 source가 영원히 불가능하다는 판정이나 신규 정책 변경은 아니다. 기존 source 계약 미확정을 유지한다.

## 2. 완료가 확인된 개발

| 상태 | 작업 | 근거 |
|---|---|---|
| 완료 | ~~기존 PR13 후속 개발 병합~~ | [PR #13](https://github.com/xkg4real/tradegen/pull/13), `6032aee` |
| 완료 | ~~유니버스 PR 0: 고정 드라이버 규칙 갱신~~ | [PR #20](https://github.com/xkg4real/tradegen/pull/20), `59a4eb8` |
| 완료 | ~~PR 1: 규칙·플래그·스냅샷 검증~~ | [PR #21](https://github.com/xkg4real/tradegen/pull/21), `df9118c` |
| 완료 | ~~PR 2: 공개 데이터 리더·스냅샷 작성~~ | [PR #24](https://github.com/xkg4real/tradegen/pull/24), `c213ed0` |
| 완료 | ~~PR 3: 게이트·read-back·조회~~ | [PR #25](https://github.com/xkg4real/tradegen/pull/25), `249cc3d` |
| 완료 | ~~PR 4b: 프로필·프로토콜·로테이션 프로그램~~ | [PR #30](https://github.com/xkg4real/tradegen/pull/30), `3868cde` |
| 완료 | ~~PR 4a: odds 배치·세션 바인딩~~ | [PR #32](https://github.com/xkg4real/tradegen/pull/32), `971a538` |
| 완료 | ~~PR 4c: 상품 조건·IOC 주문·계좌·E1 경고~~ | [PR #33](https://github.com/xkg4real/tradegen/pull/33), `7d256f9`, 최종 전체 2570/0/135 |

## 3. 구현 순서와 완료 조건

| 순서·ID | 작업 | 선행 조건 | 완료를 판정할 근거 | 현재 상태 |
|---|---|---|---|---|
| 1 / universe-pr4c | ~~상품 조건 authority v2, 종목 교체 갱신, IOC 주문, 상장폐지·저유동성 보유 코인 평가, E1 경고~~ | PR 2·3·4b 병합 | Tasks 1–10·독립 리뷰 완료, 최종 전체 2570/0/135, PR33 merge 7d256f9 | 완료 |
| 2 / universe-pr4d | 종목 전환 드라이버, 거래 코인을 따르는 이력, history v2와 프레임 입력 | PR 4c 병합 완료 | 원안 Tasks1–4 구현·리뷰, 전체2584/0/135 of2719, capacity 차단 재현은 미해결 | 초안 PR34 / 원안 전체 검사 완료 / capacity 결정·수정 후 검증·최종 병합 대기 |
| 3 / universe-pr4e | runner·coordinator·준비·console odds·리허설 연결 | PR 4a·4d 병합 | 아래 계약 정정 2건, 오래된 관측 거부, 취소·청산·중지 흐름 검사, PR·병합 근거 | 대기 |
| 4 / universe-pr5 | forward-universe-v1 평가기·수집·후보군 검증·48시간 연구 도구 | PR 4e 병합 | 전체 후보와 실패 시도 보존, 자료 크기·종목별 파서·평가기 검사, PR·병합 근거 | 대기 |
| 5 / universe-pr5-clock-notify | PR 5 병합 번호·커밋 통지와 담당 세션 조율 | PR 5 실제 병합 | 전달 가능한 채널의 실제 통지 기록. Claude 로컬 세션에 직접 전달할 수 없으면 사용자에게 전달 요청 | 대기 |
| 6 / policy-loss-budget-plan-1 | 최신 main 기준 PLB 구현 계획 작성·명세 대조 후 구현 | 유니버스 PR 5 병합, step 0 S1–S12 상태 결과 | O1–O16 승인 기본값 보존, O14 조건부 범위, 위험·효력·재시작 검사, PR·병합 근거 | 의존성 사전분석 완료 / 상태 증거 대기 / 구현 전 |
| 7 / clock-allowance | 승인된 호가 시계 1초 허용치 코드와 경계 검사 | PR 5의 공통 호가 파서 | 1,000ms 허용·1,001ms 거부, 기존 10초 신선도·receipt·HTTP Date 조건 유지 | 대기 |
| 8 / launch-production-integration | 보유 source·영속 위험 adapter, L1 live → L2 planner → L3 standing + A1 protective hold | 유니버스·PLB, 확정된 보유 source 완전성 계약 | 원본 자료 권한·시간순 위험·단일 journal 잠금·장애복구·독립 head·보호 보유 검사 | 의존성 사전분석 완료 / source 계약 미확정 / 런타임 미구현 |
| 9 / owner-setup | 실제 Windows 반영·읽기 전용 계좌/호가 준비·최종 코드와 표/정책 서명 | 실행할 최종 소스 확정 | 사용자가 검토한 코드와 로컬 설치 일치, 실제 서명·효력 검사, 읽기 전용 운영 증거 | 소유자 단계 |
| 10 / launch-prospective-study | 새 history 구간·사전등록·실제 관측·전체 후보 평가·출처/구현 검토 | 최종 코드·시계 점검·필요 서명·환경 준비 | 소급 변경 없는 실제 48시간 관측, 누락·비용·통계 조건 충족, 전체 후보 검토 증거 | 미실행 |
| 11 / launch-ready | 실제 통과 전략 검토 서명, 당일 준비·중지/복구 리허설, 무장 안내 | 실제 연구 통과와 유효한 권한·정책·계좌 상태 | 같은 최종 버전에서 모든 실행 전 조건 충족. 실제 arm은 사용자가 직접 수행 | 미완료 |
| 병행 관리 / rules-review-1202 | 법규표 재검토·효력 확인 | 최신 표와 행별 출처 | 예정 재검토일과 현재 서명 효력을 별도로 확인, 기한 임의 연장 금지 | 잔여 목록 유지 |
| 후속 확장 / launch-kis-live-collector-1·launch-okx-live-collector-1·launch-multi-market-validation-1 | KIS/OKX 계좌 수집·시장별 비용/환율/달력·주문 상태·전략 비교 | 각 시장의 계약과 운영 검증 | 해당 시장의 수집·평가·주문 계약 검사와 실제 검증을 각각 기록 | 미완료 |

8번은 인계문서의 `launch-held-positions-1/production-authority`, `launch-continuous-guard-adapter-1`,
`launch-planner-provider-1`, `launch-controlled-coordinator-1`을 묶은 추적 항목이다.
9번은 `launch-private-capture-setup-1`, `e1-14-owner-setup`, `universe-code-approve`를 포함한다.
기존 PR16의 로컬 영속 라이브러리 구현을 실제 실거래 연결 완료로 확대 해석하지 않는다.

### PR 4c 세부 체크포인트

1. Task 1–2: v2 authority·관측 최대치·매수 상한. 매도에는 관측 한도가 적용되며 매수 상한을 잘못 적용하지 않는다.
2. Task 3: IOC 요청·응답 일치, 기존 gtc 요청 바이트 유지.
3. Task 4–5: 모든 거부 검사를 head 이동 전에 수행, 종목 교체와 리허설 감사의 v1/v2 선택 검증.
4. Task 6–7: 상장폐지 표식이 있는 보유 코인만 0 평가 허용, 저유동성 코인은 신선한 최우선 매수호가로 평가.
5. Task 8–9: E1 시장 플래그·보유 경고·09:45 KST 스냅샷 경고.
6. Task 10: 독립 리뷰, 경계와 전체 검사, 줄바꿈·핀·공개정보 점검, PR와 전달 기록.

### PR 4e에 반드시 반영할 계약 정정

- `run_batch` 안에서 계좌 provider를 다시 호출하지 않는다. 마지막 observation을 work lock 없이 한 번 읽고
  `positions`, `positions_asof`를 넘긴다. 관측이 없거나 오래되면 거부한다.
- `now`는 `read_bars` 뒤에 읽고 서울 날짜가 바뀌면 거부한다. 오래 걸린 조회 전 시각을 배치에 넘기지 않는다.

## 4. 매 Task의 진행·완료 기록

1. 계획의 요구사항·원문 계약과 현재 main을 대조하고, 의존 PR와 열린 PR의 공유 파일 충돌을 확인한다.
2. 파일 소유 범위를 나누어 구현한다. 독립 검토 담당은 요구사항 누락·회귀·경계 우회를 확인한다.
3. 계획이 지정한 집중 검사와 필요한 독립 반례 검사를 수행한다. PR 단위 전체 검사는 한 번에 하나씩 실행한다.
4. `구현`, `검증`, `PR 생성`, `병합`, `실제 환경 검증`을 별도 상태로 기록한다. 알려진 실패도 실패로 남긴다.
5. 완료 알림에는 task ID, 구현 요약, 코드 SHA, 검사 결과, PR URL, 병합 SHA 또는 미병합 상태를 적는다.
6. source 브랜치를 push한 뒤 handoff CURRENT와 append-only LEDGER에 체크포인트를 남긴다.
7. 동일 근거로 이 `.md`와 기존 Notion 업무 페이지를 갱신한다. 완료한 범위에만 취소선을 적용한다.

기록 형식:

| 시각 KST | Task ID | 구현 커밋 | 검사 PASS/FAIL/NOT_RUN·환경 | 독립 리뷰 | PR·병합 | 남은 조건 |
|---|---|---|---|---|---|---|
| 2026-11-13 16:52 | workflow-resume-1113 | 문서만 | 원격 main·handoff·Notion 대조, 코드 테스트 미실행 | 출처·상태·개인정보·권한 구분 자체 점검 | 코드 PR 없음 | PR 4c 사전 점검부터 구현 |
| 2026-11-13 16:54 | workflow-resume-1113/notion | 문서만 | 기존 Notion 2페이지 갱신·저장 내용 재조회 확인, 과거 절 보존 | 공개 정보·완료 범위·서명 경계 확인 | 새 페이지·코드 PR 없음 | 후속 Task별 실제 근거 추가 |
| 2026-11-13 17:06 | universe-pr4c/tasks1-9 | 8137c4712b164c120ec8063e50dc3e05b741c23f | 고정 경계 81/0/0, 전체 회귀 실행 중, 집중 검사는 위 개별 기록 | 완료 | PR33 open/draft/미병합, 원격 head 확인 | Task 10 전체 회귀·최종 전달·병합 |
| 2026-11-13 17:30 | universe-pr4c/regression-checkpoint | 첫 실행 8137c47 / 현재 c80c56c | 첫 전체 2569/0/135, 이후 재귀오류 수정 40 PASS, 수정 후 전체 재검증 실행 중 | 수정 독립 리뷰 완료 | PR33 head c80c56c, open/draft/미병합 | 최종 전체 결과·Task 10·병합, 별도 설계 승인 2건 대기 |
| 2026-11-13 17:37 | existing-task-dependency-evidence | c80c56c 읽기 전용 분석 | 테스트·앱 실행 없음, 최신 승인 설계와 런타임 부재 대조 | production/PLB 의존성 기록 확인 | 문서 기록만 | 새 설계 승인 2건과 별개인 소유자 S1–S12 상태 증거 대기 |
| 2026-11-13 17:46:10 | universe-pr4c | runtime c80c56c / final head b21439c | 최종 전체 2570/0/135 of 2705, 1093.970초, 소스·실제 홈 메타데이터 불변 | 완료 | PR33 merge 7d256f9090bb4de593bf496b010a9753ae5508fd, GitHub 재확인 | 다음 PR4d Task1, 추가 설계 승인 2건·소유자 상태 증거 별도 대기 |
| 2026-11-13 17:52 | universe-pr4d/task1 | d34395bd27e0ea30e7a23eed7f626a2ca350bf56 | 31/31 PASS, 3.427초, 소스·실제 홈 메타데이터 불변 | 지적 없음 | gpt/universe-pr4d-driver-history push·원격 head 확인, 미병합 | 기존 Tasks2–4 진행, capacity 최종 fallback 변경은 승인 대기, 알려진 size 공백으로 최종 병합 보류 |
| 2026-11-13 18:04 | universe-pr4d/original-tasks1-4 | ea4e2a4925922ce468208c89020881cb01a08403 | 집중60/0/0(7.445초)·경계81/0/0(11.953초), 중복 합산 금지, 전체 미실행 | 완료 | PR34 open/draft/미병합, base7d256f9 | capacity 차단 재현은 수정 아님; 최종 병합·전체 검사·승인2건·상태 증거 대기 |
| 2026-11-13 18:27 | universe-pr4d/original-full | runtime ea4e2a4 / docs-only head a54a390 | 전체2584/0/135 of2719,1105.243초,baseline2705유지+14신규PASS,소스·실제홈메타데이터불변 | 원안 리뷰 완료 | PR34 draft/미병합, 원격 head a54a390 확인 | 알려진capacity공백 미해결, 후속수정 새검증 필요, 승인2건·상태증거 대기 |

## 5. 사용자 업무와 승인 경계

- 현재 클릭 승인 대기: **PR 4d capacity 처리**, **PR 5 실패한 연구의 인증된 결과 기록** 추가 설계 2건.
  승인 여부가 확인되기 전에는 해당 변경을 승인된 작업으로 처리하지 않는다.
  PR 4d의 승인 대기는 Task 2 최종 fallback 변경에 국한한다. 기존 fallback·크기 오류 거부를 유지하는 Tasks 1–4 원안은 PR34에 구현·전체 검사됐고, 최종 병합은 공백 해소와 수정 후 새 검증 뒤로 남긴다.
- 현재 상태 증거 대기: 소유자 `floor_state_check` 실행 여부와 **S1–S12 고정 결과 코드** 답변.
  PLB §9.3 step 0 / O14의 조건부 범위 확인용이며, 이미 승인된 O1–O16 결정을 재질문하는 절차가 아니다.
- 기존 승인 명세 안의 개발·검사·PR 전달과 사용자가 요청한 push·merge 절차는 계속 진행한다.
  새 작업·새 워크플로우·판정 기준 변경이 필요하면 먼저 구체적 결과와 영향 범위를 제시하고 이 대화에서 승인을 요청한다.
- GitHub 병합은 검토한 정확한 head와 검사 결과를 확인한 뒤 진행하며, 코드/표 전자서명과 무장 승인을 대신하지 않는다.
- 매 PR마다 `code-approve`를 반복하지 않는다. 현재 서명된 Windows 환경은 유지한다.
  유니버스·PLB·시계 및 실행에 필요한 최종 코드가 정리된 뒤 사용자가 최종 코드 승인을 수행한다.
- 법규표 갱신의 서명·효력 확인은 최종 코드 서명 일정과 별개로 관리한다. 이미 완료된 서명을 임의로 초기화하지 않는다.
- 사용자는 자신의 PC에서 실제 자료 준비, 필요한 표/정책·전략 검토 서명, 최종 `arm`을 수행한다.
  구체적 시점에 검토할 파일·목적·명령·예상 결과·효력 시각을 순서대로 제공한다.
- Cloud에서는 키·암호·실제 owner log를 읽거나 입력하지 않고, 실제 계좌 호출·전자서명·무장·주문을 수행하지 않는다.
- 실제 48시간 관측은 준비가 끝난 뒤 시작한다. 도구 구현 완료나 합성 테스트를 실제 전략 통과로 표시하지 않는다.

## 6. 게시 전 확인

- [x] 공개 GitHub 문서와 개인 Notion 자료를 구분하고 공개용 파일에 개인 금액·계좌·비밀·사용자 경로를 넣지 않음.
- [x] 과거 PR13 미병합·매 PR 서명·7일 고정 연구 안내와 최신 인계의 차이를 구분함.
- [x] 완료한 개발만 취소선 처리하고 실제 관측·서명·전략 통과는 미완료로 유지함.
- [x] 유니버스 우선 순서, PR 4e 계약 정정, 최종 코드 승인 순서를 보존함.
- [x] GPT 사용량 조회값은 미확인. Claude의 98%를 GPT 수치로 사용하지 않음.
- [ ] 각 후속 Task의 실제 코드·검사·병합 근거를 받을 때마다 완료 원장 갱신.

Notion 저장 확인: 업무 기록 페이지 2026-11-13 16:54:24 KST, 승인 전 페이지 16:54:47 KST.
두 페이지에 새 절이 있고 과거 절도 남아 있음을 재조회했다. 업무 페이지 패널 열기 도구는 성공 응답을 반환했다.

이 문서는 소프트웨어 개발·연구 기록이며 법률·세무·투자 조언이 아니다. 검증되지 않은 수익 확률을 생성하지 않는다.
