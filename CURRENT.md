---
status: handoff
reason: usage_limit_weekly
from: claude
task: upbit-universe
cycle: 2026-11-17
done_ids: universe-pr5/passkey-archive-authority
next_ids: blocker1-approach-a-code, launch-private-capture-setup-1, launch-kis-live-collector-1, launch-okx-live-collector-1, launch-multi-market-validation-1, universe-pr5, universe-pr5/recovery-operations, universe-pr5-clock-notify, policy-loss-budget-plan-1, rules-review-1202, protective-hold/p2-integration, launch-held-positions-1/production-authority, launch-continuous-guard-adapter-1, launch-planner-provider-1, launch-controlled-coordinator-1, universe-code-approve, e1-14-owner-setup, launch-prospective-study
updated_at: 2026-11-20T15:50:00+09:00
stale_after_hours: 24
waiting_on: owner
work_branch: claude/passkey-windows
work_commit: ae255f8
uncommitted_changes: no
pr: 65, 66 (열림, 소유자 답변·병합 대기)
usage_weekly_pct: 99
usage_5h_pct: unknown
usage_resets_at: 2026-11-24T17:00:00+09:00
session: Claude Code 메인 세션 TRADEGEN_GITHUB (local_a72616d1)
---

# 인수인계: Claude 주간 한도 도달 (패스키 PR #66, 블로커1 사양 PR #65)

## 0. 한 줄 요약

Claude 주간 사용량이 99%라 인계합니다. 패스키 PR #66과 블로커1 사양 PR #65가 열려 소유자를 기다립니다. GPT가 지금 잡을 수 있는 일은 `blocker1-approach-a-code`의 A0 측정 프로브 하나이고, A1·A2는 소유자가 #65에 답하고 병합한 뒤입니다.

## 1. 목표와 완료 조건

- **소유자 지시 (원문 그대로):**
  > 주간 사용량 98%가 되면 GPT에 인계합니다.
  > 잠금 정리, 메인 담당
- **완료 조건:** 아래 6절 ID 중 GPT가 잡은 것마다 PR이 열리고, 관련 테스트가 PASS이며, LEDGER에 한 줄이 기록됨
- **범위 밖 (GPT가 잡지 않음):** `universe-pr5`, `universe-pr5/recovery-operations`, 패스키 후속은 소유자 결정(11-20 "잠금 정리, 메인 담당")으로 Claude 메인 담당입니다. 이번 창이 끝나는 2026-11-24 17:00 KST까지 잡지 마세요.

## 2. 근거

| 종류 | 위치 | 쓰는 부분 |
|---|---|---|
| 블로커1 사양 | PR #65 `docs/superpowers/specs/2026-11-20-blocker1-held-interval-approach-a-design.md` | 규칙 BR-1~26, A0/A1/A2, 질문 OQ1-OQ18 |
| 패스키 PR | PR #66 (`claude/passkey-windows` `ae255f8`) | 리뷰 수정 13건, 사양 편차 2건, 소유자 질문 |
| 직전 Claude 문서 | handoff `abfc320` | LEDGER 8행, O5 결정 |

## 3. 판단 기록

| 결정 | 이유 | 버린 대안 |
|---|---|---|
| 패스키 PR만 열고 인계 | 테스트가 끝난 상태라 PR 개설은 몇 단계뿐임 | PR 없이 인계: 소유자가 11-24까지 검토를 시작할 수 없음 |
| engine 실패 16건은 환경 문제로 판정 | 테스트마다 별도 프로세스로 돌리니 16건 모두 PASS. 같은 프로세스 5회 반복 시 핸들 수 고정(329-330), 커밋 73→119 MB | 코드 수정: 누수 증거 없음. 배포 전 브로커 장시간 실행 시험은 PR #66 본문에 남김 |

## 4. 진행 상황

- [x] PR #61-#64 병합(11-20 00:56-00:57, main `1fd8792`)
- [x] `universe-pr5/passkey-archive-authority`: PR #66 열림. light 84, ledger 24, bootstrap 16, engine 25, integration 14 PASS; compliance·deployment 140/142(알려진 2건)
- [x] 블로커1 사양: PR #65 열림 (다른 Claude 세션 작성)
- [ ] `blocker1-approach-a-code` ← **GPT가 여기서 시작 가능 (A0만)**

**마지막으로 통과한 검증:**

```
claude/passkey-windows ae255f8, Windows, broker venv, keyless, 테스트 프로세스 하나씩
light 84/84, ledger 24/24, bootstrap 16/16, engine 25/25(실패 16건은 따로 재실행), integration 14/14
```

## 5. 중단 지점

커밋되지 않은 변경은 없습니다. 패스키는 PR #66에서 소유자 검토를 기다립니다. 소유자 결정(O11): 서명 설계 b-lite/b/c, 일시적 읽기 실패로 승인이 거절로 소모되는 문제(검증자 둘 다 제외 권장), clientDataJSON·REJECTED evidence 사양 편차, 엔진 시작 약 40초 vs 30초.

## 6. 다음 할 일 (순서대로)

1. `blocker1-approach-a-code` A0: PR #65 사양의 A0(Upbit 공개 체결 목록 측정 프로브, 키 없음, D14 밖). OQ18이 기본값이라는 전제로만 시작하고, 소유자가 OQ18에 이의를 달면 멈춥니다. — 완료 기준: 별도 PR 열림, 프로브 테스트 PASS, D14 파일 변경 없음
2. `blocker1-approach-a-code` A1/A2: 소유자가 PR #65의 OQ1-OQ7에 답하고 #65를 병합한 뒤에만 합니다. — 완료 기준: 사양 BR 규칙별 테스트 PASS, A1은 study freeze 전에 병합
3. `launch-private-capture-setup-1`: A1/A2 뒤
4. `launch-kis-live-collector-1`, `launch-okx-live-collector-1`, `launch-multi-market-validation-1`: 소유자가 TRADEGEN 자격 증명을 QUANTGEN .env와 분리한 뒤(O21)
5. 그 밖의 ID는 Claude 메인이 11-24 17:00 이후 이어갑니다.

## 7. 주의사항 / 하지 말 것

- `universe-pr5`, `universe-pr5/recovery-operations`, 패스키(PR #66)는 잡지 않습니다.
- PR 병합·코드 승인·서명·키 입력·arm·주문은 소유자만 합니다.
- 저장소는 공개입니다. Y 값·금액·개인 경로·자격 증명을 쓰지 않습니다.
- 기존 파일의 줄 끝(LF/CRLF)을 그대로 둡니다. `git diff --stat`가 `--ignore-cr-at-eol`과 같아야 합니다.

## 8. 사용자에게 물어야 할 것

- PR #65 OQ1-OQ7 답변과 병합 (기한 2026-11-21 02:47 KST)
- PR #66 검토와 소유자 결정(O11)
- 다음 서명 전: 저장소 밖 서명기 사본을 main `1fd8792`의 `tools/signer/sign.py`로 교체(O8)

## 9. 이어받는 에이전트에게 주는 지시문

```
너는 xkg4real/tradegen 레포의 "blocker1-approach-a-code" 작업을 이어받는다.
1. handoff 브랜치의 CURRENT.md, AGENTS.md, LEDGER.md를 먼저 읽어라. LEDGER.md에 있는 ID는 다시 하지 마라.
2. CURRENT.md의 status를 taken으로, from을 gpt로 바꾸고 updated_at을 갱신해 handoff 브랜치에 push해라.
3. AGENTS.md 2절 5번에 따라 main 1fd8792에서 gpt/blocker1-a0 브랜치를 만들어 작업해라. AGENTS.md 5절을 한 줄도 어기지 마라.
4. PR #65 사양의 A0(공개 체결 목록 측정 프로브)만 만든다. A1/A2는 소유자가 #65를 병합하기 전에는 시작하지 마라. universe-pr5, universe-pr5/recovery-operations, 패스키는 잡지 마라.
5. ID 하나를 끝낼 때마다 LEDGER.md에 한 줄을 덧붙이고 CURRENT.md를 같은 양식으로 갱신해라. 끝나거나 멈출 때, 늦어도 화요일(11-24) 17:00(KST) 전에 status를 returned로 바꿔라.
```

## 10. 결과 확인 방법

```
python push_handoff.py --show     # status: handoff, from: claude
gh pr view 66 --repo xkg4real/tradegen   # 패스키 PR
gh pr view 65 --repo xkg4real/tradegen   # 블로커1 사양 PR
```
