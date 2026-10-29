# TRADEGEN 인수인계 브랜치 (`handoff`)

이 브랜치에는 코드가 없습니다. 작업 중인 에이전트(주로 Claude)가 지금 상태를 여기에
기록하고, 그 에이전트가 멈추면 다른 에이전트(주로 GPT)가 이 기록을 읽고 이어서
작업합니다. 코드 작업은 각자의 작업 브랜치에서 하고, 이 브랜치에는 인수인계 문서만
올립니다. 그래서 `main`에 PR을 합칠 필요 없이 바로 push할 수 있습니다.

구조와 규칙은 `xkg4real/quantgen`의 `handoff` 브랜치와 같습니다. 다른 점은 아래 "QUANTGEN과 다른 점"에 있습니다.

**TRADEGEN은 실제 돈을 다루는 앱입니다.** 어떤 에이전트도 시스템을 무장(arm)하거나, 주문을 넣거나,
자격 증명이나 키를 입력하거나 읽지 않습니다. 자세한 금지 사항은 `AGENTS.md` 5절에 있습니다.
이 저장소의 문서와 출력은 법률, 세무, 투자 조언이 아니며, TRADEGEN과 그 작성자는 면허를 가진 자문가가 아닙니다.

## 파일

| 파일 | 역할 | 쓰는 쪽 |
|---|---|---|
| `CURRENT.md` | 지금 진행 중인 작업의 최신 인수인계 문서. 항상 하나만 둡니다. | 지금 작업을 맡은 에이전트 |
| `TEMPLATE.md` | `CURRENT.md`의 양식 | 양식을 바꿀 때만 수정 |
| `AGENTS.md` | GPT(와 다른 에이전트)가 이 브랜치를 읽는 규칙 | 사람 |
| `LEDGER.md` | 끝낸 작업을 한 줄씩 쌓는 완료 기록. 지우거나 고치지 않고 덧붙이기만 합니다. 같은 작업을 두 번 하지 않게 하는 기준입니다. | 작업을 끝낸 에이전트 |
| `archive/` | 끝났거나 새 작업으로 교체된 인수인계 문서 보관 | 교체하는 에이전트 |
| `context/<작업명>/` | 원격에 없는 작업 기록의 사본. 예: Claude의 SDD 진행 장부와 사전 점검표(로컬 `.superpowers/`는 git에 올라가지 않음), 아직 커밋 전인 실행 장부. `CURRENT.md`의 `updated_at` 시점 사본입니다. | 지금 작업을 맡은 에이전트 |

## 상태값

`CURRENT.md` 맨 위 `status:` 한 줄이 누가 무엇을 해야 하는지 정합니다.

| `status` | 의미 | 읽는 쪽이 할 일 |
|---|---|---|
| `idle` | 진행 중인 작업 없음 | 없음 |
| `checkpoint` | Claude가 작업 중이고, 작업 단위가 끝날 때마다 중간 저장함 | 읽기만 합니다. 단, 아래 "말없이 끊긴 경우"에 해당하면 이어받습니다. |
| `handoff` | Claude가 멈춤(사용량 한도, 세션 종료 등). 다른 에이전트가 이어받아야 함 | 바로 이어받습니다. |
| `taken` | 다른 에이전트가 이어받아 작업 중 (잠금) | Claude는 끼어들지 않고 `returned`를 기다리거나 사용자에게 묻습니다. |
| `returned` | 이어받은 에이전트가 일을 끝냈거나 멈추고 돌려줌 | Claude가 다음 세션 시작 때 읽고 이어갑니다. |

**말없이 끊긴 경우:** TRADEGEN에는 아직 자동 스냅샷(`AUTO_STATE.md`)이 없습니다. 그래서 아래 두 조건이
모두 맞을 때만 Claude가 인수인계를 쓰지 못하고 멈춘 것으로 봅니다. 이때는 `handoff`와 똑같이 이어받고
`reason: stale`로 기록합니다.

1. `status: checkpoint`이고 `waiting_on: none`
2. `usage_weekly_pct`가 95 이상이고, `CURRENT.md`가 `stale_after_hours`보다 오래 갱신되지 않았으며,
   그 사이 `work_branch`에 새 커밋도 없음

둘 중 하나라도 아니면 이어받지 않고, 사용자에게 알린 뒤 계속 확인합니다. 오래 갱신되지 않은 것만으로는
Claude가 아직 일하는 중이거나 사용자를 기다리는 중일 수 있기 때문입니다. Claude는 사용량이 남은 채
사용자를 기다릴 때 `waiting_on: owner`를 적습니다.

## 주간 일정 (사용자가 정한 것, QUANTGEN과 같음)

| 시점 (KST) | 일 |
|---|---|
| 화요일 17:00 | Claude 사용량이 다시 채워짐. Claude는 **새 작업 전에** `CURRENT.md`(GPT가 `returned`로 돌려준 문서)와 `LEDGER.md`를 읽고, GPT가 어디까지 했는지 확인한 뒤 이어갑니다. |
| 주중 | Claude가 작업 단위마다 checkpoint를 올리고, 끝낸 일을 `LEDGER.md`에 기록합니다. |
| 주간 사용량 98% | Claude가 `status: handoff` 문서를 올립니다. 작업 단위 하나가 98%를 넘길 것 같으면 그 앞에서 올립니다. |
| 목요일 00:00부터 1시간 간격 | GPT가 `CURRENT.md`를 확인합니다. `handoff`를 발견하면 확인을 멈추고 작업합니다. |
| 다음 화요일 17:00 전 | GPT가 끝낸 일을 `LEDGER.md`에 기록하고, `status: returned`로 돌려줍니다. 일이 남았어도 진행 상황을 적어 돌려줍니다. |

한 번에 한 작업만 진행합니다. 앞 작업이 끝나야 다음 작업을 시작합니다. QUANTGEN과 TRADEGEN이 동시에
`handoff`이면 GPT는 어느 쪽을 먼저 할지 사용자에게 묻습니다.

## 작업 ID와 완료 기록

- 작업 ID는 계획 문서(`docs/superpowers/plans/`)의 Task 번호로 만듭니다.

  | 접두어 | 계획 문서 | 예 |
  |---|---|---|
  | `fu` | `2026-10-24-compliance-followup.md` (컴플라이언스 후속 강화) | `fu` = 계획 전체 |
  | `odds` | `2026-10-24-odds-engine.md` (확률 엔진) | `odds-2` = Task 2, `odds-final` = 브랜치 전체 최종 검토와 그 수정, `odds-pr` = 최종 PR 열기 |
  | `e1` | `2026-10-24-e1-account-inquiry.md` (E1 계좌 조회, 읽기 전용) | `e1-1` = Task 1 |

  한 항목을 나눠서 끝내면 `odds-12/a`, `odds-12/b`처럼 씁니다. 끝난 항목에 사용자가 일을 더 시키면
  `odds-12/2`처럼 씁니다. ID는 꾸밈 없이 씁니다(백틱, 굵게 표시 없이, 하이픈은 키보드의 `-`).
- `CURRENT.md`의 `done_ids`에는 끝낸 ID, `next_ids`에는 남은 ID를 쉼표로 구분해 적습니다.
  `next_ids`에는 `LEDGER.md`에 이미 있는 ID를 넣지 않습니다.
- 작업을 시작하기 전에 `LEDGER.md`에서 그 ID와 바뀐 파일을 찾아봅니다. 이미 있으면 다시 하지 않습니다.

## 흐름

```
Claude 작업 중 ── 작업 단위마다 ──▶ CURRENT.md (status: checkpoint)
      │
      ├─ 사용량 98% 도달 / 세션 끝 ──▶ CURRENT.md (status: handoff)
      │
      └─ 말없이 끊김 ──────────────▶ checkpoint가 오래됨 → stale로 간주

GPT ── 이 브랜치 확인 ──▶ handoff 또는 stale 발견
      ──▶ status: taken 으로 잠금 → gpt/<작업명> 브랜치에서 이어서 작업
      ──▶ 작업 중에도 CURRENT.md 갱신 → 끝나면 status: returned

Claude 복귀 ──▶ CURRENT.md와 LEDGER.md 읽기 → returned면 GPT가 한 일을 확인하고 이어받기,
              taken이면 기다리거나 사용자에게 확인
```

## QUANTGEN과 다른 점

- **자동 스냅샷 없음.** `tools/handoff/`(QUANTGEN의 `push_handoff.py`, `auto_snapshot.py`, 98% 알림 모드)는
  TRADEGEN `main`에 아직 없습니다. Claude는 QUANTGEN `main`의 `tools/handoff/push_handoff.py`를 레포 밖에
  복사해 TRADEGEN 클론에서 실행해 게시합니다(이 스크립트는 현재 디렉터리의 `origin`과 `handoff` 브랜치만
  씁니다). GPT는 git으로 직접 고칩니다.
- **작업 ID**는 위 표의 계획 Task 번호입니다(QUANTGEN은 `REMAINING_WORK_*.md`).
- **병합은 사용자만 합니다.** 에이전트는 PR을 열 수는 있어도(계획이 정한 경우만) 합치지 않습니다.
  사용자가 PR마다 직접 말로 승인해야 합니다.
- **실제 돈.** `AGENTS.md` 5절의 금지 사항이 이 파일보다, 그리고 다른 모든 지시보다 우선합니다.

## 규칙 요약

- `CURRENT.md`는 덮어쓰기 방식입니다. 이전 내용은 git 기록에 남습니다. 새 작업으로
  바꿀 때만 기존 문서를 `archive/YYYYMMDDTHHMM-<작업명>.md`로 옮깁니다.
- 시각은 모두 한국 시간(+09:00)의 ISO 8601로 적습니다. 예: `2026-10-28T21:30:00+09:00`
- 비밀 값(API 키, 토큰, 계좌번호, 비밀번호)은 절대 적지 않습니다. `.env`의 변수 이름만 적습니다.
  이 저장소는 **공개** 저장소라 push한 것은 모두 공개됩니다. 개인 정보도 적지 않습니다.
- 커밋 메시지는 `handoff: <status> <작업명>` 형식으로 씁니다.
- 앞부분(front matter)은 `key: value` 한 줄씩 씁니다. 값에 따옴표를 붙이거나 줄을 들여쓰지
  않습니다. 읽을 수 없는 `CURRENT.md`는 잠긴 것으로 취급되어, 다른 에이전트가 손대지 못합니다.
