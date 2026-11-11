---
status: returned
reason: design_spec_ready_for_owner_review
from: claude
task: first-trade-foundation
cycle: 2026-11-11
done_ids: cloud-compat-1, cloud-compat-2, cloud-compat-3, odds-1, odds-2, odds-3, odds-4, odds-5, odds-6, odds-7, odds-8, odds-9, odds-10, odds-11, odds-12, odds-13, odds-14, odds-15, odds-16, odds-17, odds-18, odds-19, odds-final, odds-pr, spec-rev-3-3, policy-plan-1, policy-preview-1, policy-pr, e1-1, e1-2, e1-3, e1-4, e1-5, e1-6, e1-7, e1-8, e1-9, e1-10, e1-11, e1-12, e1-13, e1-pr, e2-1, e2-2, e3-1, e3-2, e3-3, e2-3, e3-4, e2-e3-pr, pr6-pr7-merge, research-preregister-1, research-evaluate-1, account-readiness-1, research-paper-1, account-provider-1, account-regression-1, account-research-pr, pr8-human-code-review-approval, pr8-merge, launch-network-1, launch-collector-1, launch-profile-1, launch-strategy-1, launch-runner-1, launch-program-2, launch-workflow-2, launch-baseline-2, launch-quotes-2, launch-deployment-2, launch-review-request-2, launch-driver-2, launch-review-auth-2, launch-baseline-integration-2, launch-market-protocol-1, launch-recovery-cutoff-1, kis-live-contract-1, kis-live-backend-1, kis-live-ui-1, launch-static-guard-1, launch-windows-design-1, kis-live-regression-1, launch-regression-1, launch-delivery-1, pr9-owner-review, launch-windows-inputs-1, launch-owner-authority-1, launch-live-evidence, launch-live-history-1, launch-windows-coordinator-1, launch-study-module-1, okx-data-1, final-review-1, pr10-owner-review, venues-upbit-terms, pr11-owner-review, rules-review-1122/research, launch-quote-diagnostics-1, launch-shortened-study-1, cloud-compat-4, launch-resume-regression-1, launch-resume-delivery-1, pr12-owner-merge, account-okx-usdc-1, launch-market-readiness-1/audit, rules-review-1122/entity-mapping, launch-held-positions-1/candidates, launch-held-positions-1/chronological-reducer, launch-instrument-refresh-1, launch-controlled-coordinator-1/owner-ops, launch-controlled-coordinator-1/rehearsal, launch-authenticated-selection-1, launch-source-boundaries-1, launch-preparation-freshness-1, launch-48h-integration-1, launch-48h-delivery-1, pr13-owner-merge, launch-study-review-windows-1, rules-review-1122/table-1110, launch-continuous-guard-commit-1, tests-hermetic-runs-1, tests-keyless-krx-1, pr14-pr17-owner-merge, policy-loss-budget-spec-1
next_ids: pr18-owner-review, policy-loss-budget-state-check-1, policy-loss-budget-plan-1, rules-review-1122, launch-held-positions-1/production-authority, launch-continuous-guard-adapter-1, launch-planner-provider-1, launch-controlled-coordinator-1, launch-private-capture-setup-1, e1-14-owner-setup, launch-prospective-study, launch-kis-live-collector-1, launch-okx-live-collector-1, launch-multi-market-validation-1
updated_at: 2026-11-11T20:57:51+09:00
stale_after_hours: 3
waiting_on: owner review and merge of PR18 (design spec); universe PR 0 to PR 5 before the loss-budget implementation plan; approve --kind rules before 2026-11-22 (PR15 merged); code-approve (PR16 merged)
work_branch: claude/principal-loss-budget-spec
work_commit: 0f211a503494525e4370adf87e3a17fb5fb2fae6
runtime_tested_commit: 2b3f98be38f37a7d15c46a9d198570f41bcf41fd
uncommitted_changes: none
pr: https://github.com/xkg4real/tradegen/pull/18 (open)
usage_weekly_pct: 19
usage_source: claude-code get_usage (Weekly, all models)
handoff_threshold_pct: 95
usage_5h_pct: unknown
usage_resets_at: 2026-11-17T17:00:00+09:00
session: Claude Code desktop on the owner's Windows PC; separate scratch clone, TRADEGEN_PR9 venv read-only
---

# 인수인계: 원금 손실 한도 설계안(PR #18) 게시, PR14~17 병합 완료

## 0. 사용자에게 전달할 최신 상태

소유자가 PR14·PR15·PR16·PR17을 모두 병합했습니다. main은 fd85850입니다.

- 병합 뒤 소유자가 직접 할 일이 두 가지 있습니다. approve --kind rules(PR15, 2026-11-22 전)와 code-approve(PR16)입니다. 했는지는 이 세션에서 확인하지 않았습니다. rules --check로 확인합니다.
- PR18 (claude/principal-loss-budget-spec, 커밋 2b3f98b와 0f211a5): 설계 문서 한 개만 추가합니다. 코드·서명 표·테스트 변경 없음. docs/는 D14 코드 해시 밖이라 병합해도 서명이 풀리지 않습니다.
- 설계 요지: 활성화 기준 A 아래에서는 손실 하한을 최고점이 아니라 고정값 C = W0 - LB(원금 - 평생 손실 한도)로 둡니다. 한도는 주문을 받아들이는 지점에서 지킵니다. 매수 뒤 정산 현금이 하한 이상이어야 하므로 포지션은 남은 한도를 넘지 않습니다. A 이상에서는 이 규칙이 적용되지 않습니다.
- 문서 상태는 PROPOSED입니다. PR18 병합이 소유자의 설계 승인이고, 12.2절의 열린 결정 16개는 소유자가 같은 PR에서 바꾸지 않으면 권장 기본값을 따릅니다. 병합은 코드 승인·한도 서명·동작 변경이 아닙니다.
- 같은 날 다른 세션이 Upbit KRW 유니버스 설계(PR19)와 그 구현(PR20부터)을 시작했습니다. 두 작업이 같은 파일을 고칩니다. 설계 12.5절이 접점을 다룹니다.
- 유니버스 세션이 전한 소유자 결정: 공유 파일은 유니버스 코드 먼저, 손실 한도 코드는 그 뒤. 이 세션은 소유자에게서 직접 듣지 않았고, 설계 12.5절의 권고와 같습니다.
- 구현은 시작하지 않았습니다.

실거래 시작일이나 수익을 확정하지 않습니다. 실제 API·계좌·키·owner log·서명·활성화·주문은 쓰지 않았습니다.

## 1. 이미 확정된 결정

- 이전 인수인계(handoff 브랜치의 2026-11-10 문서) 1절을 그대로 유지합니다.
- 2026-11-11 소유자 결정: 하한 문제의 선택지 (a)~(f) 가운데 (b) 고정 손실 한도의 설계안을 쓰라고 했습니다. 설계 승인은 아직입니다.
- 2026-11-10 소유자 결정: ~/.tradegen/runs에 이미 있는 폴더는 그대로 둡니다.
- 병합은 소유자가 PR마다 GitHub에서 직접 합니다. 에이전트는 병합하지 않습니다.

## 2. 직접 읽어야 할 근거

- docs/superpowers/specs/2026-11-11-principal-loss-budget-design.md (PR18 브랜치). 0.1절이 한 쪽 요약, 12.2절이 열린 결정, 12.5절이 유니버스 설계와의 접점입니다.
- PR18 본문: 병합의 의미, 서명 순서 경고, 실제 확률, 검토 방법.
- PR19 (claude/upbit-krw-universe-spec, eab3047): 유니버스 설계와 PR 계획 10개. 이 세션의 작업이 아닙니다.
- 이전 문서가 가리킨 근거(PR14~17 본문, 계약 문서, 규칙표 재검토 기록)는 이제 main에 있습니다.

## 3. 구현한 범위와 한계

| 항목 | 결과 | 남은 경계 |
| --- | --- | --- |
| 설계 문서 (PR18) | 규칙, 검증 코드, 매수 허용 규칙, driver·paper evaluator 상한, 소유자 실행 순서, 반쯤 이행된 상태의 fail-closed 표, 불변식, 테스트와 변이 표, 열린 결정 16개, 실제 확률, 도입 비용, 유니버스 설계와의 접점 | 문서만 있습니다. 설계 자체를 위해 실행한 것은 없고 테스트 수도 인용하지 않습니다 |
| 줄 번호 | 백틱 인용 613개가 fd85850에서 파일과 줄 범위로 모두 풀립니다. 코드 블록 안 인용 5개는 손으로 확인했습니다 | main이 바뀌면 다시 맞춰야 합니다. 유니버스 PR이 병합될 때마다 바뀝니다 |

검토는 세 번 했습니다. 지적마다 다른 검토자가 반박을 시도했습니다.

1. 초안: 네 방향(코드 사실, 안전, 결정 사항 반영, 명확성). 46건 확인, 모두 반영. 3건은 일부만 반영하고 나머지는 열린 결정 PLB-O13·O14·O15로 남겼습니다.
2. main이 fd85850으로 바뀐 뒤: 15건 확인, 모두 반영. 코드 블록 안 줄 번호 5개가 첫 보정에서 빠져 있었고, A 도달 뒤 중단이 자동인 것처럼 읽히던 요약을 고쳤습니다.
3. 12.5절과 새 문장: PR19 원문과 main에 대조. 15건 확인, 모두 반영.

설계가 드러낸 한계(소유자에게 그대로 전달할 것):

- 엣지가 없을 때 목표 T에 닿을 확률은 LB / (T - W0 + LB)를 넘지 못합니다. 설계는 확률을 보이게 할 뿐 높이지 않습니다.
- A 아래의 이익은 보호되지 않습니다. LB는 W0 기준 손실만 제한합니다.
- A 이상에서는 매수 허용 규칙이 적용되지 않습니다. 기본값(PLB-O5)은 소유자가 하한을 W0로 올려 서명하는 것이고, 그 뒤에는 새 세션을 준비할 수 없습니다. 서명 전까지는 A 위에서도 매수가 허용되고 손실이 이어지면 영구 halt로 끝날 수 있습니다. A 위의 진행은 후속(post-activation) 설계가 필요합니다.
- 없애는 장애물은 M8 하나입니다. 첫 실거래는 나머지 넷(flat-only 구간 출처, rehearsal 전용 coordinator, planner provider 없음, 통과한 전략 없음) 때문에 여전히 막혀 있습니다.
- 지금 서명된 코드에서 total_loss_floor_krw만 먼저 낮추면 영구 halt로 끝날 수 있습니다. 순서는 새 코드 병합, code-approve, 그 다음 limit_set입니다(설계 9.2절).
- 유니버스와 함께 쓰면: 준비 단계의 "보유 없음" 조건이 잔량·상장폐지 코인 때문에 영영 막힐 수 있어 PLB-O16을 추가했습니다. 그 기본값에서도 한도만큼 매수한 코인을 들고 있는 동안은 odds 카드가 거부하므로 그 코인을 판 뒤에야 다음 매수를 준비할 수 있습니다.

## 4. 최종 검증

- 전체 검사(커밋 2b3f98b = main fd85850 + 설계 문서, Windows, 키 없음, 네트워크 없음, TRADEGEN_RUNS_DIR 미설정): 2530개 중 2402 PASS / 5 FAIL / 123 NOT_RUN.
- 실패 5개 중 2개는 저장소 자체 .venv 위치를 요구하는 검사입니다(이 PC는 TRADEGEN_PR9 venv 사용). 나머지 3개는 control_controller 테스트의 실제 홈 감시가 걸린 것입니다. 실행 도중 테스트 밖에서 실제 상태 폴더가 바뀌었습니다. execution_control 묶음만 다시 돌리니 201/201 통과, 실제 상태 폴더는 전후 동일했습니다.
- 한 번의 깨끗한 전체 실행으로 2405 / 2 / 123을 확인한 것은 아닙니다. 다음 에이전트가 기준선을 다시 잽니다.
- 커밋 0f211a5는 문서만 바꿨고 그 위에서 테스트를 다시 돌리지 않았습니다.
- 설계 문서: LF, UTF-8, BOM 없음, ASCII만. 금액·날짜·개인 경로 없음. git diff --stat과 --ignore-cr-at-eol 결과 동일. 7.2절 확률 표는 식으로 다시 계산해 일치를 확인했습니다.
- 실제 전략 통과·실계좌 연결·전자서명·활성화·주문은 이 결과에 포함되지 않습니다.

## 5. 실패 이력과 현재 작업 상태

- 설계를 쓰는 동안 main이 2c9c478에서 fd85850으로 바뀌었습니다(PR14·15·16 병합). 줄 내용 기준으로 인용을 다시 맞췄는데, 백틱 밖(코드 블록 안) 인용 5개가 빠져 두 번째 검토에서 잡았습니다. 다음에 줄 번호를 옮길 때는 코드 블록 안도 봐야 합니다.
- 앞서 소유자에게 "PR14~16은 아직 열려 있다"고 답했는데, 실제로는 PR17과 몇 분 차이로 모두 병합되어 있었습니다. 이번 보고에서 정정했습니다.
- 유니버스 세션의 제안 가운데 두 가지는 그대로 받지 않았습니다. (1) "문서는 언제든 넣을 수 있다": docs/launch-profile.example.json에 새 키를 넣으면 지금 코드의 parser가 거부해 테스트가 깨지므로 문서는 구현 PR과 함께 갑니다. (2) "지분 <= 정산 현금으로 바꾸기": 준비 단계가 받는 Positions에 정산 현금이 없어 입력을 하나 더 넘겨야 하고 coordinator.py가 서명 범위 변경 파일에 추가됩니다. 둘 다 12.5절과 PLB-O16에 적었습니다.
- 작업 clone은 세션 scratch에 있고 브랜치는 push 완료. 미커밋 변경 없음, 실행 중인 관측·거래 작업 없음.

## 6. 다음 개발 과업

1. pr18-owner-review: 소유자가 설계를 검토합니다. 바꿀 결정이 있으면 같은 PR에서 고칩니다.
2. policy-loss-budget-state-check-1: 승인 뒤, 읽기 전용 상태 점검 스크립트(설계 8.2절, 9.1절)를 별도 PR로 냅니다. 서명 범위 밖이라 유니버스 PR과 순서가 무관합니다.
3. policy-loss-budget-plan-1: 유니버스 PR 5가 병합된 main을 기준으로 구현 계획을 씁니다. 첫 과업은 기존 테스트 전체의 측정 실행과 영향받는 테스트 목록입니다. 12.5절의 각 행과 tests/renewal_boundaries.py 고정값(11.3절)을 계획에 넣습니다.
4. rules-review-1122: 소유자 approve --kind rules(2026-11-22 전). FIU 원본 첨부와 개별 상품·계좌 적격 확인은 남아 있습니다.
5. launch-held-positions-1/production-authority, launch-continuous-guard-adapter-1, launch-planner-provider-1, launch-controlled-coordinator-1, launch-private-capture-setup-1: 이전 문서 6절 그대로.
6. e1-14-owner-setup, launch-prospective-study, KIS/OKX 수집기, launch-multi-market-validation-1: 실제 Windows·계좌·미래 관측이 필요합니다.

코드 서명, 하한을 낮추는 limit_set, study freeze, 검토는 손실 한도 변경과 유니버스 PR 5까지가 모두 들어간 한 head에서 한 번만 합니다(설계 7.4절, 12.5절).

## 7. 소유자가 할 순서

1. PR18의 설계 문서 0.1절을 읽고, 12.2절의 열린 결정 가운데 바꿀 것이 있는지 봅니다. 특히 PLB-O5(A에 닿은 뒤), PLB-O2(창을 여러 번 열 수 있게 할지), PLB-O16(유니버스 프로필의 준비 조건), 그리고 LB·A·T의 크기입니다.
2. 동의하면 PR18을 병합합니다. 서명할 것은 없습니다.
3. 설계 9.2절의 순서가 지켜지기 전에는 total_loss_floor_krw를 낮춰 서명하지 않습니다.
4. 아직 안 했다면 approve --kind rules(2026-11-22 전)와 code-approve를 직접 실행하고 rules --check로 확인합니다. 유니버스 PR이 병합될 때마다 code-approve가 다시 필요해집니다.

## 8. 유지할 제한

이전 문서 8절과 같습니다. 실제 API·키·비밀번호·서명 암호·실 owner log 접근, 실제 홈 쓰기, 서명·활성화·주문을 하지 않습니다.
공개 저장소에는 금액·개인 경로·계좌 식별자·비공개 자료를 올리지 않습니다. QUANTGEN과 frozen 연구를 수정하지 않습니다.
소유자가 설계를 승인하기 전에는 이 설계의 코드를 쓰지 않습니다.

## 9. 다음 에이전트가 이어받을 지시

AGENTS.md, 이 문서, LEDGER.md, PR18 본문과 설계 문서를 먼저 읽습니다. 미병합 PR을 병합하지 않습니다.
PR18이 병합되기 전에는 구현 계획도 코드도 시작하지 않습니다.
병합되면 상태 점검 스크립트 PR부터 냅니다. 구현 계획은 유니버스 PR 5 병합 뒤의 main에서 씁니다. 소유자가 순서를 바꾸면 12.5절이 적은 유니버스 계획 단계들을 먼저 고쳐야 합니다.
설계의 줄 번호는 fd85850 기준입니다. 구현 계획에서 그때의 main으로 다시 확인합니다.
전체 검사 도중 실제 상태 폴더가 바뀌면 control 테스트의 감시가 실패로 보고합니다. 소유자가 같은 PC에서 서명하는 시간과 겹치지 않게 돌리거나, 실패하면 해당 묶음만 다시 돌려 확인합니다.

## 10. 전달 및 기록

브랜치를 push하고 PR18을 열었습니다. 유니버스 세션에 12.5절과 PLB-O16을 알렸습니다.
법률·세무·투자 조언이 아니며 작성자는 면허를 가진 자문가가 아닙니다.
