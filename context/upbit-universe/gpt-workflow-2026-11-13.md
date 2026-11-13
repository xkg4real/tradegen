# TRADEGEN 업무처리 워크플로우

기준: 2026-11-13 17:06 KST. PR 4c 구현 체크포인트이며 전체 검증·병합·실거래 준비 완료 판정은 아니다.

## 1. 근거와 현재 상태

- [Claude CURRENT](https://github.com/xkg4real/tradegen/blob/handoff/CURRENT.md): 2026-11-12 16:53 KST 인계.
- [구현 계획 index](https://github.com/xkg4real/tradegen/blob/971a5389208c85d34fdd6479c96580e9b8fcc68d/docs/superpowers/plans/2026-11-11-upbit-krw-universe-index.md): 승인된 유니버스 rev 3의 의존성과 계약.
- [진행 기록](https://github.com/xkg4real/tradegen/blob/handoff/context/upbit-universe/universe-impl-status.md), [완료 원장](https://github.com/xkg4real/tradegen/blob/handoff/LEDGER.md).
- [업무 기록 Notion](https://app.notion.com/p/40f5c916fe0c80b49d10fec810a95cbb), [승인 전 정리 Notion](https://app.notion.com/p/40d5c916fe0c80e49e2bd9f3fc1c2145).
- GitHub 조회 기준 main: `971a5389208c85d34fdd6479c96580e9b8fcc68d` (PR #32 병합).
- PR 4c는 Claude가 사전 점검 중 중단한 뒤 GPT가 최신 main에서 대조·구현했다. 아래 최신 체크포인트를 따른다.
- Claude의 마지막 실행 기록: PR 4a head `56a0b7f`, 2,547 PASS / 2 FAIL / 123 NOT_RUN, 총 2,672개.
  실패 2건은 인계문서상 checkout의 가상환경 위치 문제다. 이번 Cloud 실행 결과로 취급하지 않는다.
- 유니버스 전략의 실제 수익성과 목표 달성 확률은 아직 검증되지 않았다. 연구 도구 구현과 실제 연구 통과를 구분한다.

### 최신 체크포인트: PR 4c Tasks 1–9 구현·독립 리뷰 완료

- ~~PR 4c Tasks 1–9 구현과 독립 리뷰~~: `8137c4712b164c120ec8063e50dc3e05b741c23f`를 push했다.
- [초안 PR #33](https://github.com/xkg4real/tradegen/pull/33)은 **open / draft / 미병합**이며 원격 head를 확인했다.
- 고정 소스 경계 검사는 **81 PASS / 0 FAIL / 0 NOT_RUN**이다. 검사 전후 소스와 실제 홈 메타데이터가 동일했다.
- 집중 검사: IOC 56 PASS, collector/provider 106 PASS, E1 119 PASS, readiness 18 PASS,
  비유한 보유량 방어 16 PASS. 범위가 겹치므로 이 수치를 합산하지 않는다.
- **전체 회귀 검사는 실행 중**이다. 전체 PASS와 Task 10 완료는 아직 선언하지 않는다.
- [소스 실행 기록](https://github.com/xkg4real/tradegen/blob/8137c4712b164c120ec8063e50dc3e05b741c23f/docs/universe-pr4c-execution-log.md).
  handoff 체크포인트 `7e16536`은 이 보고 시점에 원격 게시 확인 대기다.
- 실제 API 호출·전자서명·무장·주문·실제 전략 통과를 수행하거나 완료로 표시하지 않았다.

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

## 3. 구현 순서와 완료 조건

| 순서·ID | 작업 | 선행 조건 | 완료를 판정할 근거 | 현재 상태 |
|---|---|---|---|---|
| 1 / universe-pr4c | 상품 조건 authority v2, 종목 교체 갱신, IOC 주문, 상장폐지·저유동성 보유 코인 평가, E1 경고 | PR 2·3·4b 병합 | 계획 Task 1–10 충족, 고정 BTC 호환성, 경계 검사, 전체 검사·리뷰·PR·병합 커밋 | Tasks 1–9 구현·독립 리뷰 완료 / 전체 검증 중 / PR33 초안·미병합 |
| 2 / universe-pr4d | 종목 전환 드라이버, 거래 코인을 따르는 이력, history v2와 프레임 입력 | PR 4c 병합 | 계획별 검사와 재시작·이력 일관성 검증, PR·병합 근거 | 대기 |
| 3 / universe-pr4e | runner·coordinator·준비·console odds·리허설 연결 | PR 4a·4d 병합 | 아래 계약 정정 2건, 오래된 관측 거부, 취소·청산·중지 흐름 검사, PR·병합 근거 | 대기 |
| 4 / universe-pr5 | forward-universe-v1 평가기·수집·후보군 검증·48시간 연구 도구 | PR 4e 병합 | 전체 후보와 실패 시도 보존, 자료 크기·종목별 파서·평가기 검사, PR·병합 근거 | 대기 |
| 5 / universe-pr5-clock-notify | PR 5 병합 번호·커밋 통지와 담당 세션 조율 | PR 5 실제 병합 | 전달 가능한 채널의 실제 통지 기록. Claude 로컬 세션에 직접 전달할 수 없으면 사용자에게 전달 요청 | 대기 |
| 6 / policy-loss-budget-plan-1 | 최신 main 기준 PLB 구현 계획 작성·명세 대조 후 구현 | 유니버스 PR 5 병합 | 기존 승인 명세와 일치하는 구체적 계획, 위험·다음날 효력·재시작 검사, PR·병합 근거 | 대기 |
| 7 / clock-allowance | 승인된 호가 시계 1초 허용치 코드와 경계 검사 | PR 5의 공통 호가 파서 | 1,000ms 허용·1,001ms 거부, 기존 10초 신선도·receipt·HTTP Date 조건 유지 | 대기 |
| 8 / launch-production-integration | 완전한 보유 구간 증거, 영속 위험 adapter, 현재 planner, controlled coordinator 연결 | 관련 코드와 최종 위험 정책 확정 | 원본 자료 권한·시간순 위험·장애복구·독립 head·동시성·보호 청산 검사 | 미완료 |
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

## 5. 사용자 업무와 승인 경계

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
