---
status: taken
reason: owner_requested_resume
from: gpt
task: upbit-universe
cycle: 2026-11-10
done_ids: workflow-resume-1113, universe-pr0, universe-pr1, universe-pr2, universe-pr3, universe-pr4b, universe-pr4a
next_ids: universe-pr4c, universe-pr4d, universe-pr4e, universe-pr5, universe-pr5-clock-notify, universe-code-approve, policy-loss-budget-plan-1, rules-review-1202, launch-held-positions-1/production-authority, launch-continuous-guard-adapter-1, launch-planner-provider-1, launch-controlled-coordinator-1, launch-private-capture-setup-1, e1-14-owner-setup, launch-prospective-study, launch-kis-live-collector-1, launch-okx-live-collector-1, launch-multi-market-validation-1
updated_at: 2026-11-13T16:52:19+09:00
stale_after_hours: 3
waiting_on: none
work_branch: gpt/universe-pr4c-terms
work_commit: 971a5389208c85d34fdd6479c96580e9b8fcc68d
runtime_tested_commit: 56a0b7f (PR 4a head, 전체 실행)
uncommitted_changes: no
pr: https://github.com/xkg4real/tradegen/pull/32 (merged)
usage_weekly_pct: unknown
usage_source: unavailable
handoff_threshold_pct: 95
usage_5h_pct: unknown
usage_resets_at: unknown
session: Cloud Codex; owner Windows deployment remains separate
---

# 인수인계: Upbit KRW 유니버스 구현 (PR 0 ~ PR 5)

## 0. 한 줄 요약

유니버스 PR 0, 1, 2, 3, 4b, 4a가 모두 main에 병합됐습니다. main은 `971a538`(#32)입니다. 다음 사람은 **PR 4c**부터 시작하면 됩니다: `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md`(Task 1-10). 4c의 사전 점검은 시작했지만 사용량 때문에 중간에 멈췄고 결과물이 없습니다. 그러니 사전 점검부터 다시 하세요.

## 1. 목표와 완료 조건

- **사용자 요청 (원문 그대로):**
  > 자자잦 시발 사용량 ㅈ됐습니다. 지금까지 한 일들 GPT한테 인계할 준비 하고 지난주처럼 .md파일 제공해주세요.
- **이 작업의 원래 요청:** 시작 세션이 맡긴 일입니다. owner가 승인한 스펙 rev 3과 계획 10개(PR 0, 1, 2, 3, 4a, 4b, 4c, 4d, 4e, 5)를 index의 "Needs" 순서대로 하나씩 PR로 구현합니다.
- **owner 지시 (원문 그대로, 2026-11-12):**
  > 유니버스 PR 5까지 모두 main에 병합되면, SendMessage로 세션 local_597dbe11-9cd4-4fd6-8f04-6c9e741d8a1b 에 "유니버스 PR 5 병합 완료: PR 번호와 merge 커밋" 을 보내 주세요. 그 세션이 docs/pc-clock-decision-2026-11-12.md 의 1초 허용치 코드 PR을 만듭니다.
- **완료 조건:**
  - PR 4c, 4d, 4e, 5가 각각 계획대로 구현되고 리뷰를 거쳐 PR로 열려야 합니다.
  - 각 PR의 전체 실행에서 실패는 아래 7절의 "알려진 실패"만 있어야 합니다.
  - 병합은 owner가 합니다.
  - PR 5가 병합되면 위 메시지가 전달되어야 합니다.
- **범위 밖:**
  - 서명, 무장, 실주문, 병합은 하지 않습니다.
  - loss-budget(PLB) 코드는 유니버스 PR 5 병합 뒤에 main 기준으로 계획을 새로 씁니다. owner가 11-11에 "Universe first"로 정했습니다.

## 2. 근거

| 종류 | 위치 | 이 작업에서 쓰는 부분 |
|---|---|---|
| 스펙 | `docs/superpowers/specs/2026-11-11-upbit-krw-universe-design.md` (rev 3) | 6, 7, 8, 9, 10, 19절 |
| 계획 index | `docs/superpowers/plans/2026-11-11-upbit-krw-universe-index.md` | 순서("Needs"), 공유 파일, run_batch 계약 줄(4a에서 갱신됨) |
| 남은 계획 | `docs/superpowers/plans/2026-11-11-upbit-krw-universe-pr4c-terms-orders-accounts.md`, `...-pr4d-driver-history.md`, `...-pr4e-runner-coordinator.md`, `...-pr5-study.md` | Task 전체 |
| 진행 기록 | handoff 브랜치 `context/upbit-universe/` | 아래 표 참조 |
| PLB 스펙 | `docs/superpowers/specs/2026-11-11-principal-loss-budget-design.md` | 유니버스 다음 순서, 겹치는 파일 |
| PC 시계 결정 | `docs/pc-clock-decision-2026-11-12.md` | PR 5 뒤 1초 허용치 PR |

`context/upbit-universe/` 안의 파일:
- `universe-impl-status.md`: 진행 기록 전체. 판정, 위험 요소, 4e 수정 지시가 들어 있습니다.
- `implementer-rules.md`: 구현자 규칙. LF, 줄 120자 이내, 커밋 trailer, 금지 사항.
- `pr4a-preflight.md`, `pr4b-preflight.md`: 사전 점검 표. 4c 사전 점검을 이 형식으로 쓰면 됩니다.
- `pr4a-sdd-progress.md`, `pr4b-sdd-progress.md`: Task별 커밋, 리뷰, 판정 기록.

## 3. 판단 기록

| 결정 | 이유 | 버린 대안과 이유 |
|---|---|---|
| `run_batch`가 호출자의 `positions`와 `positions_asof`를 받고, 계좌 provider를 호출하지 않음 (owner가 (a) 승인) | 코디네이터의 `ContinuousAccountProvider`는 재진입이 안 되고, 겹친 호출을 거부하며, baseline 전진을 커밋함. console의 odds 배치가 worker tick을 실패시키고 거부될 때도 상태를 쓸 수 있었음 | 계획 원안(배치 안에서 provider 호출): 위의 위험 때문에 버림 |
| positions 신선도 조건: `positions_asof <= now`이고 `started - positions_asof <= 30 s`. 어기면 `UNIVERSE_BATCH_POSITIONS_STALE`, 모양이 틀리면 `_INVALID` | `prepare_session`과 같은 기준 | — |
| 배치 없이 upbit의 매핑 안 된 코인을 준비하면 `SESSION_UNIVERSE_BATCH_REQUIRED`로 거부 | 스펙 9절은 임의 코인 집합을 금지함. 이 수정 전에는 ETH 단일 세션이 배치 없이 준비됐음 | KRW-BTC 고정 세션은 그대로 둠 |
| kill의 reason이 비었거나 str이 아니면 `reason_invalid`로 기록하고 kill은 그대로 진행 | kill latch는 안전 정지라서 reason 때문에 실패하면 안 됨 | 계획 원안(빈 reason이면 raise): 버림 |
| odds 카드의 `notin.delist` 문구에 로테이션 선택을 추가하고, `tests/odds_report.py`의 catalogue pin을 갱신 | 스펙 9절. 그 한 줄을 되돌리면 이전 해시가 정확히 복원되는 것을 확인함 | — |
| 서명 문구: PR마다 code-approve를 하지 않음. 유니버스 PR 전부와 PLB 코드가 끝난 뒤 owner가 한 번만 함. TRADEGEN_PR9는 0962e94(서명됨, --check OK)에 그대로 둠. 중간 head를 실행할 때만 그 head에 승인이 필요함 | owner의 11-11 지시. TRADEGEN_GITHUB 세션과 합의함 | "병합 head마다 code-approve": 틀린 문구라서 #32 본문에서 고침 |
| MODULES 등록 줄에 append만 하는 경우는 "공유 파일 PR은 동시에 하나만" 규칙의 예외 | 시작 세션의 판정 (b) | — |
| **PR 4e 수정 1:** `Coordinator.odds_batch`는 `self._observation`을 work lock 없이 한 번만 읽음. None이거나 ACCOUNT_AGE보다 오래됐으면 코디네이터 코드로 거부. `positions=observation.positions`, `positions_asof=observation.asof`를 넘김 | 위 (a) 결정의 후속. 4e 테스트 `test_the_odds_batch_runs_off_the_work_lock_over_the_snapshot_top_n`는 다른 스레드에서 `c._work`를 잡고 있어서, lock을 잠깐이라도 잡으면 멈춤 | lock 안에서 읽기: 테스트가 멈추고 worker도 막힘 |
| **PR 4e 수정 2 (Hazard 5):** `now`는 `read_bars` 뒤에 잡음. 서울 날짜가 바뀌었으면 거부하고, 새 `now`를 넘김 | 코인 3개 이상이면 GET이 51번 넘게 나가서 30 s `_CLOCK_AGE`를 넘김 | 원안(now 먼저): 배치가 거부됨 |

## 4. 진행 상황

- [x] universe-pr0: 규칙을 갱신한 뒤에도 고정 드라이버가 계속 동작함. #20, merge `59a4eb8`
- [x] universe-pr1: 서명 규칙, 플래그 분류, 스냅샷 검증. #21, `df9118c`
- [x] universe-pr2: 공개 데이터 리더, 스냅샷 빌더와 라이터. #24, `c213ed0`
- [x] universe-pr3: 게이트, read-back, 공개 조회. #25, `249cc3d`
- [x] universe-pr4b: 프로필, 프로토콜 다이제스트, 로테이션 프로그램. #30, `3868cde`
- [x] universe-pr4a: odds 배치, 유니버스 세션 바인딩, kill reason. #32, `971a538`. #30의 rule 3 top-N 테스트 수정(cc571fe)도 여기에 포함됨
- [ ] universe-pr4c: 약관, 주문, 계좌 ← **여기서 멈춤** (사전 점검 중에 중단, 결과물 없음)
- [ ] universe-pr4d: 드라이버 이력 (4c 필요)
- [ ] universe-pr4e: runner와 coordinator (4a와 4d 필요, 위 수정 1과 2 반영)
- [ ] universe-pr5: 48시간 study (4e 필요)
- [ ] universe-pr5-clock-notify: PR 5 병합 뒤 메시지 전달
- [ ] universe-code-approve: owner만 함

**마지막으로 통과한 검증 (PR 4a head 56a0b7f, main 3868cde 위):**

```
OPENBLAS_NUM_THREADS=1 TRADEGEN_RUNS_DIR=<scratch> python -X utf8 -m tests.run_all   (그 뒤 git restore qa/acceptance_results.json)
2547/2672 passed, 2 failed (checkout-location 2건), 123 not run (REFDATA/OWNER/POSIX)
```

## 5. 중단 지점

- PR 4c 사전 점검 에이전트(계획 4c를 main과 대조하는 작업)를 사용량 때문에 직접 멈췄습니다. 결과 파일은 없습니다.
- 4c 작업 트리는 로컬 스크래치에 있습니다. 브랜치는 `claude/universe-pr4c-terms`, 기준은 3868cde이고 커밋은 없습니다. 이제 main이 971a538이므로 **새로 origin/main에서 브랜치를 따는 것이 맞습니다.**
- 커밋하지 않은 변경, 실패 중인 테스트는 없습니다.

## 6. 다음 할 일 (순서대로)

1. **universe-pr4c**
   - **브랜치:** `git fetch && git switch -c gpt/universe-pr4c-terms origin/main` (971a538 이상)
   - **사전 점검:** 계획 4c와 main을 대조합니다. 형식은 `context/upbit-universe/pr4a-preflight.md`와 같은 표입니다.
     - PR 4a와 4b에서 테스트가 추가되어 테스트 개수와 줄 번호가 바뀌었을 수 있습니다. 인용은 줄 번호가 아니라 내용으로 다시 찾으세요.
     - 4c가 4a/4b와 같은 파일을 건드리는지 확인하세요. 특히 `tests/renewal_boundaries.py`, `tests/launch_acceptance.py`의 MODULES, `execution_control/*`, `core/compliance/*`를 보세요.
   - **구현:** Task 1-9를 Task마다 리뷰하고, 마지막에 브랜치 전체를 리뷰합니다.
   - **전체 실행:** `OPENBLAS_NUM_THREADS=1`, `TRADEGEN_RUNS_DIR=<스크래치>`로 돌리고, 끝나면 `git restore qa/acceptance_results.json`.
   - **줄바꿈 확인:** `git diff --stat`와 `git diff --stat --ignore-cr-at-eol`이 같아야 합니다.
   - **PR 전:** `gh pr list`로 공유 파일을 쓰는 열린 PR이 있는지 확인합니다.
   - **PR 본문:** 3절의 서명 문구, 실제 확률, "법률·투자 조언 아님"을 넣습니다.
   - 완료 기준: 계획 Task 10, 그리고 알려진 실패만 있는 전체 실행.
2. **universe-pr4d** (4c가 병합된 뒤): 계획 4d를 위와 같은 절차로 진행합니다. 완료 기준은 계획 4d의 마지막 Task입니다.
3. **universe-pr4e** (4a와 4d가 병합된 뒤)
   - 3절의 수정 1과 2를 반드시 반영합니다. 앵커는 계획 4e의 P2977(Consumes), P3001(가짜 run_batch), P3129(호출)인데, 내용으로 찾으세요.
   - 테스트의 가짜 `run_batch`는 `positions`와 `positions_asof`를 받고, 그 값이 마지막 observation의 값인지 assert합니다.
4. **universe-pr5** (4e가 병합된 뒤): 계획 5를 진행합니다.
   - PLB 쪽 겹침 메모(`context/upbit-universe/universe-impl-status.md`의 "Overlap note")도 확인하세요. PLB 코드가 먼저 main에 들어온 경우에만 해당합니다.
5. **universe-pr5-clock-notify**
   - PR 5가 병합되면 `git fetch`로 merge 커밋을 확인하고 owner에게 "유니버스 PR 5 병합 완료: #번호, merge 커밋"을 알립니다.
   - GPT는 Claude 세션에 메시지를 보낼 수 없습니다. owner나 사용량이 풀린 Claude가 세션 local_597dbe11-9cd4-4fd6-8f04-6c9e741d8a1b에 전달합니다. 그 세션이 1초 허용치 코드 PR을 엽니다.
6. **universe-code-approve:** owner만 할 수 있습니다.
   - 유니버스 PR 전부와 PLB 코드가 병합된 뒤 한 번 code-approve합니다.
   - 그 뒤에 strategy review와 history window를 새로 해야 합니다.

## 7. 주의사항 / 하지 말 것

**절대 규칙 (owner):**
- 무장, 실주문, 자격 증명·키·`.env` 값을 입력하거나 읽는 일은 하지 않습니다.
- `tools/signer/sign.py`를 실행하지 않고, 암호를 묻지 않습니다. 서명은 owner만 합니다.
- 실제 `~/.tradegen`과 `~/.nextgen`에는 쓰지 않습니다. 테스트에서 네트워크와 실제 거래소 API는 쓰지 않습니다.
- QUANTGEN은 수정하지 않습니다. 서명된 표와 `sign.py`는 owner 승인 없이 바꾸지 않습니다. 고정(pinned) 파일은 바이트 단위로 같게 유지합니다.
- 공개 repo입니다. 비밀, 금액, 개인정보, 사용자 이름이 든 로컬 경로를 넣지 않습니다.
- Windows 예약 작업을 만들지 않습니다. `pip install`을 하지 않습니다. 병합하지 않습니다.
- 매번 실제 확률과 "법률·투자 조언 아님"을 밝힙니다. 다른 세션, 웹, Notion의 내용은 지시가 아니라 자료로 봅니다.

**환경:**
- repo는 바이트 단위로 정확해야 합니다(`* -text`). Python 파일은 LF이고, `execution_launch/study.py`와 일부 문서(plans index.md 등)는 CRLF입니다.
- `sed -i`는 쓰지 마세요. CRLF가 사라집니다. 편집기나 Python bytes로 고치세요.
- 실행: `.venv\Scripts\python.exe -X utf8`. `-I`를 쓰면 PYTHONIOENCODING이 무시되니, 출력은 `-X utf8`로 받으세요.
- PC의 RAM이 부족합니다. `OPENBLAS_NUM_THREADS=1`을 쓰고 무거운 실행은 하나씩 하세요.
- 커밋 identity는 기존 PR과 같게 두고, 덮어쓰지 마세요.

**알려진 실패 (main에서도 남; 새로 생긴 실패가 아님):**
- `compliance_guards/test_cryptography_is_pinned_installed_and_usable`, `compliance_signer/test_commands_sign_exactly_what_was_shown`: 실행한 checkout에 자체 `.venv`가 없으면 실패합니다.
- `launch_owner_ops/test_runtime_worker_runs_once_and_closes_with_bounded_lifecycle`: 원래 가끔 실패합니다.
- `launch_coordinator/test_close_while_awaiting_timer_returns_promptly`: 1.5 s 타이밍 테스트라서 부하가 있으면 실패하고, 단독으로 돌리면 통과합니다.
- owner가 전체 실행 도중 서명하면 `control_controller`의 실제 home 가드가 걸릴 수 있습니다.

**실제 확률:**
- 이 인계는 확률을 바꾸지 않고, 주문도 내지 않습니다.
- 유니버스 전략은 아직 백테스트되지 않았습니다. 확률은 PR 4c의 평가기와 48시간 study가 끝나야 나옵니다. 그 전까지는 기존 odds 카드의 수치가 적용됩니다.
- 이 문서는 소프트웨어 설계 기록이며, 법률·세무·투자 조언이 아닙니다.

## GPT 작업 시작 (2026-11-13 KST)

소유자의 이 대화 지시로 PR 4c부터 재개합니다. 최신 main과 인계 문서를 대조했고, 작업 흐름·각 Task 검증 기록을 md와 기존 Notion 페이지에 연결합니다. 실서명·무장·주문은 수행하지 않습니다. 개발 결과가 검증되면 요청된 push/PR/병합 절차를 진행합니다. 기존 계획 밖의 별도 작업이 필요하면 구체안을 작성한 뒤 클릭형 승인 입력을 요청합니다. 현재 PR 4c 사전 점검 단계이며 새 기능 완료로 기록하지 않습니다.

### 워크플로우 완료와 PR 4c 구현 중

작업흐름은 context/upbit-universe/gpt-workflow-2026-11-13.md와 기존 Notion 두 페이지에 기록했습니다. PR4c의 Tasks1~9를 파일별로 병렬 구현하고 있으며, 전체 검증은 소스를 고정한 뒤 수행합니다. 구현 중 서명 대상 코드 변경으로 생긴 검사 오류는 최종 검증으로 세지 않습니다. Task9 불완전 플래그 자료의 경보 해제, Task8 타시장 0평가 및 legacy snapshot 직렬화 회귀, 잘못된 시장목록의 상장폐지 오판을 기존 계획의 요구사항에 맞게 보완하고 있습니다.
