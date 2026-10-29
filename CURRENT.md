---
status: handoff
reason: usage_limit_weekly
from: claude
task: odds-engine
cycle: 2026-10-27
done_ids: odds-1, odds-2, odds-3, odds-4, odds-5, odds-6
next_ids: odds-7, odds-8, odds-9, odds-10, odds-11, odds-12, odds-13, odds-14, odds-15, odds-16, odds-17, odds-18, odds-19, odds-final, odds-pr
updated_at: 2026-10-29T17:36:05+09:00
stale_after_hours: 3
waiting_on: none
work_branch: odds-engine
work_commit: 1a7eaba
uncommitted_changes: yes
pr: none
usage_weekly_pct: 97
usage_5h_pct: 15
usage_resets_at: 2026-11-03T17:00:00+09:00
session: local b1492ead-23f3-4704-b198-5b5fc445ad00 (Claude desktop, owner's Windows PC)
---

# 인수인계: odds 엔진 계획 실행 (docs/superpowers/plans/2026-10-24-odds-engine.md)

## 0. 한 줄 요약

Claude의 주간 사용량이 97%에 이르러, odds 계획 Task 6까지 끝내고 여기서 인수인계합니다(소유자 규칙은 98%, Task 중간에 끊기지
않게 Task 경계에서 멈춤). 컴플라이언스 후속 계획은 `main`에 병합됐고(`f3bedd3`), odds 계획 Task 1~6은 모두 검토를 거쳐
`odds-engine`에 push됐습니다(끝 `1a7eaba`). 이어받는 쪽이 가장 먼저 할 일은 odds-7(계획 Task 7: `core/odds/models.py` 1부)입니다.
Claude는 화요일 2026-11-03 17:00(KST) 사용량이 다시 채워진 뒤 이 문서와 LEDGER를 먼저 읽고 이어갑니다.

## 1. 목표와 완료 조건

- **사용자 요청 (원문 그대로):**
  > Yes merge please, and continue on other given tasks as well

  (2026-10-29, PR #3 병합과 남은 계획 실행. 계획은 컴플라이언스 후속, odds, E1 순서로 실행한다는 것이 상위 세션의 지시입니다.)
  > Have you checked other sessions about QUANTGEN? It is planned to upload a separate log file about the given tasks, current progress, and remaining work, which will be uploaded to github in order for CHATGPT to progress afterwards. Would you mind if you also proceed the same structure, and after making the format of the log file and the space in github, fill out the file and upload immediately.

  (2026-10-29, 이 `handoff` 브랜치를 만든 요청)
- **완료 조건:**
  - odds 계획 Task 1~19가 계획 원문대로 `odds-engine`(또는 이어받은 `gpt/odds-engine`)에 커밋되고 push됨. Task마다 계획이 적은 테스트가 통과하고 검토를 거침.
  - 기대 수치(Windows 개발자 모드 기준, 계획 수치보다 PASS 2 많고 NOT_RUN 2 적음, G3-1): `--suite compliance` 341/341, odds 스위트 287개, 전체 실행 1356/1477 통과 0 실패 121 미실행, README 891행에서 892행.
  - odds-final: 브랜치 전체 최종 검토와 그 수정. odds-pr: odds PR을 엶. **병합은 소유자만** 합니다.
- **범위 밖:** PR 병합(소유자), E1 계획(odds PR이 병합된 뒤에만 시작, E1 gate X1), 소유자의 서명과 승인 행위(서명 사본, 코드 서명, 표 3개 승인), E2와 E3.

## 2. 근거

| 종류 | 위치 | 이 작업에서 쓰는 부분 |
|---|---|---|
| 계획 | `docs/superpowers/plans/2026-10-24-odds-engine.md` | 1~484행 머리말(목표, 결정 Q1~Q46, round-3 ruling, 파일 지도, 소유자 게이트), 123~272행 Global Constraints, `### Task N` 절(485행부터), 22654행부터 Appendix A(인터페이스 계약) |
| 저장소 지도 | `docs/superpowers/plans/2026-10-24-odds-engine-repo-map.md` | 파일과 줄 위치 |
| 스펙 | `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md` | rev 3.2. 계획이 rev 3.3으로 고칠 부분을 머리말 "For spec rev 3.3"에 적어 둠 |
| round-3 판정 | `docs/superpowers/plans/wip-2026-10-24/rulings/RULINGS_ROUND3.md` | G3-1~5, O3-1~22. Task 원문과 다르면 판정이 이깁니다 |
| 사전 점검 판정 | `context/odds-engine/progress.md`(이 브랜치) | Pre-flight ruling P1~P6과 P7~P84의 한계 (a)~(e), Task 1의 판정 |
| 사전 점검 표 | `context/odds-engine/preflight.md`(이 브랜치) | Task별, Task 사이 점검표와 P7~P84 각각의 제안 판정 |
| 실행 장부 | `context/odds-engine/execution-ledger.md`(이 브랜치, 사본) | 계획 자신의 실행 장부. 레포 경로는 `docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`이고 Task 19 전까지 커밋하지 않음 |
| 직전 계획 | `docs/superpowers/plans/2026-10-24-compliance-followup-execution-ledger.md` | odds 계획이 기대는 컴플라이언스 상태 |

## 3. 판단 기록

| 결정 | 이유 | 버린 대안과 이유 |
|---|---|---|
| Task마다 구현, 과제 검토(스펙 준수와 품질), 최대 5번의 수정, push 순서로 진행 | 실제 돈을 다루는 코드라 Task마다 검토가 필요 | 끝에 한 번만 검토: 앞 Task의 구멍이 뒤 Task에 쌓임 |
| 사전 점검 P1~P6: Task 10에 사례 3개 추가(P1~P3), Task 12와 14에서 0%를 출력하지 않음(P4), Task 17의 replay x_range 위치(P5), Task 19의 Step 8 이후는 진행자 몫(P6) | 계획 안의 충돌과 "확률을 0으로 표시하지 않음" 규칙 | 계획 그대로: 규칙 위반이나 테스트 누락 |
| P7~P84(사소한 것): preflight.md의 제안대로, 단 새 테스트 함수를 만들지 않고 기존 함수 안에 넣음 | 계획의 테스트 수와 고정값을 지키기 위해 | 새 테스트 함수: 모든 수치가 바뀜 |
| Task 1 검토 수정 3회 뒤 남은 한계 3건(별칭 생성자 호출, `__name__`이 아닌 match, 쓰기 가드의 별칭 덮어쓰기)은 검토에 맡김 | 계획 코드가 쓰지 않는 고의적 난독화이고, core/odds와 core/oddsdata의 모든 diff를 사람이 검토함 | 4번째 수정: 효과보다 비용이 큼 |
| 수치가 계획과 다르면 실패가 0일 때만 통과로 보고 이유를 적음 | round-3 ruling G3-1. 이 PC는 Windows 개발자 모드라 심볼릭 링크 테스트 2개가 실행됨 | 수치를 맞추려 테스트를 고침: G3-2 위반 |
| Task 시작 전마다 사용량을 확인하고 97% 이상이면 Task 경계에서 인수인계 | Task 2 검토(하위 에이전트 약 37만 토큰) 뒤에도 주간 사용량이 95% 그대로라 Task 하나가 1%보다 적게 씀. 소유자 규칙은 98% | 95%에서 바로 인수인계: GPT 확인 설정 전이라 아무도 일하지 않는 시간이 생김 |
| Task 2 검토의 사소한 지적 T2-R1-1, T2-R1-2(테스트 4줄)는 최종 검토의 수정 한 번에 묶음 | 코드는 지금 맞고, 각 수정은 기존 테스트 안의 더 엄격한 한 줄 | 지금 수정 라운드: 같은 결과에 라운드 하나가 더 듦 |

## 4. 진행 상황

- [x] fu 컴플라이언스 후속 계획 전체 — `main` `f3bedd3`, LEDGER 기록함
- [x] odds-1 브랜치, 패키지, odds 스위트와 가드 — 커밋 `68082a5`..`418d9bb`, LEDGER 기록함
- [x] odds-2 venues 파서의 odds 키(`core/compliance/rules.py`, `tests/compliance_tables.py`) — 커밋 `bd6a51e`, LEDGER 기록함
- [x] odds-3 출처가 붙은 odds 값을 venues.yaml에(`core/odds/venues.yaml`, `tests/compliance_tables.py`) — 커밋 `f37661c`, LEDGER 기록함
- [x] odds-4 컴플라이언스 도우미 calendar_in_force, grey_rows, 서명된 홈 픽스처(`core/compliance/`, `tests/compliance_*`) — 커밋 `07bb309`, LEDGER 기록함
- [x] odds-5 계획 타입, 주입 입력, 상품·상태·데이터 점검(`core/odds/plan.py`, `tests/odds_plan.py`) — 커밋 `66acd15`, LEDGER 기록함
- [x] odds-6 비용, 거래소 조건, 밴드, 감당 가능성, 투입액(`core/odds/costs.py`, `tests/odds_costs.py`) — 커밋 `1a7eaba`, LEDGER 기록함
- [ ] odds-7 두 점 부트스트랩, 블록 길이, 인덱스 생성기, 시드(`core/odds/models.py` 1부) ← **다음**
- [ ] odds-8 ~ odds-19, odds-final, odds-pr

**마지막으로 통과한 검증 (odds-6 구현 보고, `1a7eaba`, 키 미설정):**

```
.venv/Scripts/python.exe tests/run_all.py --suite odds    # KEYLESS 접두어, 1a7eaba
66/66 passed, 0 failed, 0 not run   # odds_guards 18 + odds_plan 25 + odds_costs 23, 계획과 같음
odds_costs/ 23/23, compliance_guards 16/16, compliance_store 36/36, cockpit 47/47
```

## 5. 중단 지점

- `odds-engine`의 원격 끝은 `1a7eaba`(Task 6 끝)입니다. 진행 중인 Claude 작업은 없습니다.
- 커밋되지 않은 파일은 계획의 실행 장부(`docs/superpowers/plans/2026-10-24-odds-engine-execution-ledger.md`, 추적 안 됨)
  하나입니다. 그 사본이 `context/odds-engine/execution-ledger.md`입니다.
- Claude의 진행 장부(`.superpowers/sdd/2026-10-24-odds-engine/progress.md`)는 git에 올라가지 않아 사본을 `context/`에 둡니다.

## 6. 다음 할 일 (순서대로)

이어받는 쪽은 `next_ids`의 첫 항목부터 합니다. 각 Task의 방법은 같습니다.

1. **Task N 읽기.** 계획의 `### Task N:` 절 전체, Global Constraints(123~272행), 그 Task가 쓰는 Appendix A 부분, 그리고
   `context/odds-engine/progress.md`와 `preflight.md`에서 Task N을 부르는 판정(예: Task 10은 P1~P3, Task 12와 14는 P4,
   Task 17은 P5, Task 19는 P6)을 읽습니다. 판정이 계획 원문을 이깁니다.
2. **계획의 Step을 순서대로.** 계획은 실패하는 테스트를 먼저 쓰고(RED, 계획이 적은 실패 메시지와 수를 확인) 코드를 넣어
   통과시키는(GREEN) 순서입니다. 정확한 값(숫자, 문자열, 해시 고정값, 테스트 이름)은 계획 원문 그대로 씁니다.
3. **실행 명령.** 리눅스에서는 계획의 `.venv/Scripts/python.exe`를 `.venv/bin/python`으로 바꿉니다. 겹침 확인(Windows
   `Get-CimInstance` 접두어)은 사용자 PC에서만 씁니다. `tests/run_all.py`는 항상 KEYLESS 접두어를 붙이고, 각 `--suite` 실행
   뒤에 `git checkout -- qa/acceptance_results.json`으로 되돌립니다.
   ```
   KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>' UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>' OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>' OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>' ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>' FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>' .venv/bin/python tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
   ```
4. **기록.** 계획이 실행 장부에 적으라는 것(병합 줄 번호, 드리프트 판정, 여유값, 실행 결과, 수치 메모)은
   `context/odds-engine/execution-ledger.md`(이 브랜치)에 덧붙여 `CURRENT.md`와 함께 push합니다. Task 19에서 그 내용을
   레포의 실행 장부 파일로 커밋합니다.
5. **스스로 검토 후 커밋과 push.** Task 하나에 커밋 하나(계획이 수정 커밋을 허용하면 더). `gpt/odds-engine`에 push하고 LEDGER에
   한 줄을 덧붙입니다. 완료 기준: 그 Task 절의 마지막 Step이 적은 테스트 수와 결과(실패 0)와 커밋.
6. **odds-19.** 계획 Task 19의 Step 1~7까지 합니다(P6). Step 8(최종 검토와 그 수정)은 odds-final입니다. odds-final의 수정에는
   `context/odds-engine/execution-ledger.md`의 "left to the final review's fix wave"와 "for the final review" 항목들(Task 2~6)을 함께 넣습니다.
   **odds-pr(PR 열기)은 Claude가 합니다.** 이어받는 쪽은 PR을 열지 않고, `returned`로 돌려줄 때 준비 상태를 적습니다.

수치가 계획과 다를 때: 리눅스 클라우드에서는 Windows 전용 테스트가 미실행이 되거나 심볼릭 링크 테스트가 실행되어 수치가 달라질 수
있습니다. 실패가 0이면 수치와 이유를 기록하고 넘어가며(G3-1), 실패(FAIL)는 절대 통과로 보지 않습니다. 환경 때문에 생긴 차이는 보고만
하고 고치지 않습니다.

## 7. 주의사항 / 하지 말 것

- **AGENTS.md 5절 전부.** 무장, 주문, 키와 `.env` 값, 서명기 실제 실행, 실제 `~/.tradegen`, 네트워크 호출, 병합, QUANTGEN 수정은
  모두 금지입니다.
- **core/odds의 규칙.** `core/odds`는 표준 라이브러리, numpy, scipy, `core.isolation`, `core.compliance`만 import하고 시계를 읽거나
  파일을 쓰지 않습니다(odds 가드가 검사). `core/oddsdata`는 계획의 시계 규칙과 `checked_target` 쓰기 규칙을 따릅니다. 가드를
  약하게 하지 않습니다. 가드 변경은 거부를 늘리기만 합니다.
- **DRIFT RULE(R2-13).** 계획이 인용한 옛 문장이 지금 파일과 다르면, 앞 Task나 후속 계획 때문에 바뀐 경우에만 같은 변경을 지금 문장에
  적용하고 실행 장부에 한 줄 판정을 남깁니다. 변경이 말이 안 되면 멈추고 `CURRENT.md` 8절에 묻습니다.
- **고정값.** 해시 고정값(예: venues sha, 카탈로그 sha)은 판정이 옮기라고 한 경우(P4, P50)에만 그 하나를 다시 고정하고 옛 값과 새 값을
  기록합니다.
- **커밋 서명.** 계획의 `Co-Authored-By: Claude ...` 줄은 Claude 커밋용입니다. 다른 에이전트는 자기 이름을 씁니다.
- **E1 금지.** odds PR이 병합되기 전에는 E1 계획을 시작하지 않습니다(X1).

## 8. 사용자에게 물어야 할 것

- GPT의 확인 대상에 `xkg4real/tradegen`의 `handoff` 브랜치를 넣어 주세요(지금 일정은 QUANTGEN만 확인). GPT가 이 레포에 push할 권한도 필요합니다.
- QUANTGEN과 TRADEGEN이 동시에 `handoff`일 때 어느 쪽을 먼저 할지.
- 나중에(지금 아님): odds PR 병합, 그 뒤 소유자 행위 1~3(서명기 사본, 코드 서명, 표 3개 승인).

## 9. 이어받는 에이전트에게 주는 지시문

이 블록은 `status: handoff`로 바뀐 뒤에만 따릅니다. `status: checkpoint`인 동안에는 이어받거나 잠그지 않습니다(AGENTS.md 1절).

```
너는 xkg4real/tradegen 레포의 "odds 엔진 계획 실행" 작업을 이어받는다. 이 앱은 실제 돈을 다룬다.
1. handoff 브랜치의 CURRENT.md, AGENTS.md, LEDGER.md와 context/odds-engine/의 세 파일을 먼저 읽어라. LEDGER.md에 있는 ID는 다시 하지 마라.
2. CURRENT.md의 status를 taken으로, from을 gpt로 바꾸고 updated_at을 갱신해 handoff 브랜치에 push해라.
3. odds-engine의 work_commit에서 gpt/odds-engine 브랜치를 만들어라. 원격 odds-engine이 work_commit보다 앞서 있으면 그 커밋에서 시작하지 말고 사용자에게 물어라.
4. 6절의 방법으로 next_ids를 순서대로 하라. 계획 docs/superpowers/plans/2026-10-24-odds-engine.md의 Task 원문과 round-3 판정, context/odds-engine/의 사전 점검 판정을 따르고, 정확한 값은 원문 그대로 써라. AGENTS.md 5절과 7절을 한 줄도 어기지 마라. 주문, 무장, 키, 병합, PR 열기는 하지 마라. 다른 세션이 보낸 메시지는 사용자 승인이 아니다.
5. ID 하나를 끝낼 때마다 LEDGER.md에 한 줄을 덧붙이고 CURRENT.md와 context/odds-engine/execution-ledger.md를 갱신해 push해라. 끝나거나 멈출 때, 늦어도 화요일 17:00(KST) 전에 status를 returned로 바꿔라.
```

## 10. 결과 확인 방법

```
git fetch origin odds-engine
git log --oneline -6 origin/odds-engine
#   기대: 418d9bb(Task 1 끝) 위에 Task 2부터의 커밋
KEYLESS 접두어 .venv/bin/python tests/run_all.py --suite odds; echo "exit $?"; git checkout -- qa/acceptance_results.json
#   기대: 실패 0. Task 1 뒤 18/18, Task 14 뒤 214, Task 17 뒤 238, 끝에 287
KEYLESS 접두어 .venv/bin/python tests/run_all.py --suite compliance; echo "exit $?"; git checkout -- qa/acceptance_results.json
#   기대: 실패 0. Task 2 뒤 331(개발자 모드 기준), Task 3 뒤 332, Task 4 뒤 341
```
