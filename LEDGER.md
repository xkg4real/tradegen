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
