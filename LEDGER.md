# 완료 기록 (LEDGER)

Claude와 GPT가 끝낸 작업을 한 줄씩 쌓는 기록입니다. 같은 작업을 두 번 하지 않기 위한 장부입니다.

- **지우거나 고치지 않습니다.** 맨 아래에 행을 덧붙이기만 합니다.
- **작업을 시작하기 전에** 이 표에서 작업 ID와 바뀐 파일을 찾아봅니다. 이미 있는 ID는 다시 하지 않습니다.
  사용자가 그 일을 더 해 달라고 하면 `odds-3/2`처럼 새 ID를 붙입니다.
- **작업 ID**는 `README.md`의 "작업 ID와 완료 기록" 표(계획 문서의 Task 번호)를 씁니다.
  한 항목을 나눠서 끝냈다면 `odds-12/a`, `odds-12/b`처럼 붙입니다.
- **주기**는 사용량이 다시 채워진 화요일 17:00(KST)의 날짜입니다. 예: `2026-10-27`은
  2026-10-27 17:00부터 2026-11-03 17:00 전까지입니다.
- **커밋**은 원격(GitHub)에 push된 커밋이어야 합니다.
- 이 기록이 생기기 전에 끝난 일(컴플라이언스 게이트 `995534b`, 세 계획 PR #1 `d9f4025`)은 계획 문서와 `main`의
  git 기록, 각 계획의 `*-execution-ledger.md`를 봅니다.

| id | 완료 시각 (KST) | 주기 | 누가 | 한 일 | 바뀐 파일 | 커밋 | 확인 방법과 결과 |
|---|---|---|---|---|---|---|---|
| fu | 2026-10-29T13:26:46+09:00 | 2026-10-27 | claude | 컴플라이언스 후속 계획 전체(Task 1~8, 최종 검토 수정, 소유자 요청의 gc.get_objects 경로). 거부만 늘리는 변경. Task 1~3은 PR #2(소유자 병합, 02:45 KST), 나머지는 PR #3(소유자의 "Yes merge please" 뒤 Claude가 병합)으로 main에 들어감 | core/compliance/owner.py, rules.py, alerts.py, kr_rules.yaml, tools/signer/sign.py, data/krx/kis_client.py, core/ficc/data.py, tests/compliance_*.py, README.md, qa/acceptance_results.json, docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md | f3bedd3 | compliance 327/327 통과, 전체 1055/1176 통과 0 실패 121 미실행(기록 커밋 b385dd9, Windows 개발자 모드라 계획보다 PASS 2 많고 NOT_RUN 2 적음, G3-1). 실행 장부 docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md |
| odds-1 | 2026-10-29T14:51:24+09:00 | 2026-10-27 | claude | odds 계획 Task 1: odds-engine 브랜치, 빈 core/odds와 core/oddsdata 패키지, odds 스위트와 odds 가드, run_all과 README 등록. 사전 점검 P11(금지 모듈 8개 추가)과 검토 수정 3회(_pyio 등 경로 모듈 금지, 시계 별칭 추적, match __name__) | core/odds/__init__.py, core/oddsdata/__init__.py, tests/odds_acceptance.py, tests/odds_fixtures.py, tests/odds_guards.py, tests/run_all.py, README.md | 68082a5, c8dcc9b, 2f5d2e1, 418d9bb | odds_guards 18/18, --suite odds 18/18, compliance_guards 16/16, compliance_store 29/29, cockpit 47/47. 과제 검토: 스펙 준수, 품질 승인. 남긴 한계 3건은 context/odds-engine/execution-ledger.md "Deferred minors" |
| odds-2 | 2026-10-29T15:17:12+09:00 | 2026-10-27 | claude | odds 계획 Task 2: venues 파서가 odds 키 lot, min_order, fee_extras, tick_ladder와 출처를 읽고 잘못된 값은 거부. 사전 점검 P9(경로 이름 16개 grep), P10(정수 키 거부 2줄) 적용 | core/compliance/rules.py, tests/compliance_tables.py | bd6a51e | compliance_tables 69/69, compliance_gate 49/49, compliance_cli 36/36, compliance_guards 16/16, compliance_store 29/29, odds_guards 18/18, cockpit 47/47, --suite compliance 331/331(개발자 모드, 계획 329/331 2 미실행, G3-1). 과제 검토: 스펙 준수, 품질 승인, 수정 라운드 없음. 사소한 지적 2건은 odds-final로 |
| odds-3 | 2026-10-29T15:33:02+09:00 | 2026-10-27 | claude | odds 계획 Task 3: 배포용 core/odds/venues.yaml에 출처가 붙은 lot, min_order, KRX 주식 호가 단위 사다리 추가와 연구 문서 줄 대조 테스트. 사전 점검 P14 기록, P15 검토로 남김, P16 Deferred minor | core/odds/venues.yaml, tests/compliance_tables.py | f37661c | compliance_tables 70/70, gate 49/49, cli 36/36, guards 16/16, store 29/29, cockpit 47/47, --suite compliance 332/332(개발자 모드, 계획 330/332 2 미실행, G3-1), venues sha256 283c143f...a042a 계획과 같음. 과제 검토: 스펙 준수, 품질 승인, 수정 라운드 없음 |
| odds-4 | 2026-10-29T16:40:13+09:00 | 2026-10-27 | claude | odds 계획 Task 4: 컴플라이언스 도우미 calendar_in_force, grey_rows, 공개 서명 홈 픽스처. 검토 수정 1회: 계획 코드가 모든 예외를 'log'로 바꿔 --check가 0~3으로 끝날 수 있던 것을 스펙 5.4대로 고침(_calendar_approval은 좁은 catch, calendar_in_force는 None으로 실패 닫힘) | core/compliance/owner.py, core/compliance/gate.py, core/compliance/rules.py, tests/compliance_fixtures.py, tests/compliance_store.py, tests/compliance_gate.py | 46fed98, 07bb309 | compliance_store 36/36, gate 51/51, cli 36/36, owner 52/52, signer 38/38, guards 16/16, odds_guards 18/18, cockpit 47/47, --suite compliance 341/341(개발자 모드, 계획 339/341 2 미실행, G3-1). 재검토 CLEAN. 내부 오류에서 --check 종료 코드 4는 임시 홈 탐침으로 확인 |
| odds-5 | 2026-10-29T17:05:19+09:00 | 2026-10-27 | claude | odds 계획 Task 5: 계획 타입, 주입 입력, 상품·상태·데이터 점검(core/odds/plan.py). 사전 점검 P23(거부 순서 이중 결함 사례로 14개 뒤바꿈 모두 잡음), P26 gate 복사본 일치 단언, P29 Leg 하위 클래스 사례, P24·P25·P30 기록 | core/odds/plan.py, tests/odds_plan.py, tests/odds_fixtures.py | 66acd15 | odds_plan 25/25, --suite odds 43/43, odds_guards 18/18, compliance_guards 16/16, compliance_store 36/36, cockpit 47/47, 실패 0. 과제 검토: 스펙 준수, 품질 승인, 수정 라운드 없음. 계획이 정한 한계 3건(거래소 미상장 기호, plan_hash 정규화, Refusal 해시 불가)은 odds-final 후보로 실행 장부에 |
| odds-6 | 2026-10-29T17:36:30+09:00 | 2026-10-27 | claude | odds 계획 Task 6: 비용, 거래소 조건, 밴드, 감당 가능성, 투입액(core/odds/costs.py), 계획 원문과 바이트 단위로 같음. 사전 점검 P31 유지, P32 변경 없음, P33 수용(모두 기록) | core/odds/costs.py, tests/odds_costs.py | 1a7eaba | odds_costs 23/23, --suite odds 66/66, odds_guards 18/18, compliance_guards 16/16, compliance_store 36/36, cockpit 47/47, 실패 0. 과제 검토: 스펙 준수, 품질 승인, 수정 라운드 없음. 계획이 정한 한계 3건은 odds-final 후보로 실행 장부에 |
