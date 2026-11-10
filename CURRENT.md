---
status: returned
reason: tested_development_batch_ready_for_owner_review
from: claude
task: first-trade-foundation
cycle: 2026-11-10
done_ids: cloud-compat-1, cloud-compat-2, cloud-compat-3, odds-1, odds-2, odds-3, odds-4, odds-5, odds-6, odds-7, odds-8, odds-9, odds-10, odds-11, odds-12, odds-13, odds-14, odds-15, odds-16, odds-17, odds-18, odds-19, odds-final, odds-pr, spec-rev-3-3, policy-plan-1, policy-preview-1, policy-pr, e1-1, e1-2, e1-3, e1-4, e1-5, e1-6, e1-7, e1-8, e1-9, e1-10, e1-11, e1-12, e1-13, e1-pr, e2-1, e2-2, e3-1, e3-2, e3-3, e2-3, e3-4, e2-e3-pr, pr6-pr7-merge, research-preregister-1, research-evaluate-1, account-readiness-1, research-paper-1, account-provider-1, account-regression-1, account-research-pr, pr8-human-code-review-approval, pr8-merge, launch-network-1, launch-collector-1, launch-profile-1, launch-strategy-1, launch-runner-1, launch-program-2, launch-workflow-2, launch-baseline-2, launch-quotes-2, launch-deployment-2, launch-review-request-2, launch-driver-2, launch-review-auth-2, launch-baseline-integration-2, launch-market-protocol-1, launch-recovery-cutoff-1, kis-live-contract-1, kis-live-backend-1, kis-live-ui-1, launch-static-guard-1, launch-windows-design-1, kis-live-regression-1, launch-regression-1, launch-delivery-1, pr9-owner-review, launch-windows-inputs-1, launch-owner-authority-1, launch-live-evidence, launch-live-history-1, launch-windows-coordinator-1, launch-study-module-1, okx-data-1, final-review-1, pr10-owner-review, venues-upbit-terms, pr11-owner-review, rules-review-1122/research, launch-quote-diagnostics-1, launch-shortened-study-1, cloud-compat-4, launch-resume-regression-1, launch-resume-delivery-1, pr12-owner-merge, account-okx-usdc-1, launch-market-readiness-1/audit, rules-review-1122/entity-mapping, launch-held-positions-1/candidates, launch-held-positions-1/chronological-reducer, launch-instrument-refresh-1, launch-controlled-coordinator-1/owner-ops, launch-controlled-coordinator-1/rehearsal, launch-authenticated-selection-1, launch-source-boundaries-1, launch-preparation-freshness-1, launch-48h-integration-1, launch-48h-delivery-1, pr13-owner-merge, launch-study-review-windows-1, rules-review-1122/table-1110, launch-continuous-guard-commit-1
next_ids: rules-review-1122, launch-held-positions-1/production-authority, launch-continuous-guard-adapter-1, launch-planner-provider-1, launch-controlled-coordinator-1, launch-private-capture-setup-1, e1-14-owner-setup, launch-prospective-study, launch-kis-live-collector-1, launch-okx-live-collector-1, launch-multi-market-validation-1, tests-hermetic-runs-1, pr14-owner-merge, pr15-owner-merge, pr16-owner-merge
updated_at: 2026-11-10T21:30:13+09:00
stale_after_hours: 3
waiting_on: owner merge of PR14, PR15, PR16; code-approve after PR16; approve --kind rules after PR15 before 2026-11-22
work_branch: claude/continuous-guard-commit
work_commit: 1a5972844aa93a7aed4219b491b2701e2123886f
runtime_tested_commit: 1a5972844aa93a7aed4219b491b2701e2123886f
uncommitted_changes: none
pr: https://github.com/xkg4real/tradegen/pull/14 (open), https://github.com/xkg4real/tradegen/pull/15 (open), https://github.com/xkg4real/tradegen/pull/16 (open)
usage_weekly_pct: 19
usage_source: claude-code get_usage (Weekly, all models)
handoff_threshold_pct: 95
usage_5h_pct: unknown
usage_resets_at: 2026-11-17T17:00:00+09:00
session: Claude Code desktop on the owner's Windows PC; separate scratch clone, TRADEGEN_PR9 venv read-only
---

# 인수인계: PR13 병합 이후 세 PR(#14·#15·#16) 게시

## 0. 사용자에게 전달할 최신 상태

소유자가 PR13을 main 6032aee로 병합했습니다. 그 위에서 세 PR을 열었고, 셋 다 검토 가능·미병합입니다.

- PR14 (claude/windows-study-review-lf, ce613a4): Windows에서만 실패하던 launch_study_review 테스트 2개 수정. 테스트 파일만 바뀌어 서명할 것 없음.
- PR15 (claude/rules-review-1110, c63850a): kr_rules.yaml 47행 전체를 2026-11-10에 다시 검토. 차단·허용 판정은 한 행도 바뀌지 않음. review_by를 25행 2026-12-02, 22행 2026-12-11로 갱신. 병합 후 소유자가 approve --kind rules를 2026-11-22 전에 해야 함.
- PR16 (claude/continuous-guard-commit, 1a59728): 영속 guard transaction(launch-continuous-guard-commit-1)을 로컬 라이브러리로 구현. 실거래 경로에는 아직 연결하지 않음. 병합 후 code-approve 필요.

Windows 전체 검사(키 없음, 네트워크 없음, 임시 상태): PR16 브랜치 2529개 중 2402 PASS / 4 FAIL / 123 NOT_RUN.
main 6032aee는 2515개 중 2388 / 4 / 123. 차이 14개는 PR16의 새 테스트이고, 실패 4개는 양쪽이 같습니다(아래 4절).
실거래 시작일이나 수익을 확정하지 않습니다. 실제 API·계좌·키·owner log·서명·활성화·주문은 쓰지 않았습니다.

## 1. 이미 확정된 결정

- 이전 인수인계(handoff 브랜치 c56bace의 GPT 문서) 1절의 결정을 그대로 유지합니다.
- 소유자가 2026-11-05에 자금 목표를 새로 정했습니다. 금액과 날짜는 비공개 가이드에만 둡니다.
  TRADEGEN은 QUANTGEN 자금 계획에 반드시 포함됩니다. 제외하자고 권하지 않고, 실제 확률은 계속 그대로 보여 줍니다.
- 병합은 소유자가 PR마다 GitHub에서 직접 합니다. 에이전트는 병합하지 않습니다.

## 2. 직접 읽어야 할 근거

- 이전 CURRENT.md: handoff 브랜치 c56bace (GPT, 2026-11-06). 이번 문서가 그 내용을 대체하지만 6절 과업 목록은 이어받았습니다.
- PR14·PR15·PR16 본문: 변경 내용, 검토 방법, 반박된 지적, 소유자 후속 단계가 모두 적혀 있습니다.
- docs/continuous-guard-commit-contract.md (PR16 브랜치): 구현된 범위, 재시작 분류표, 아직 필요한 것.
- research_notes/Korean resident trading venue legality/review_2026-11-10.md (PR15 브랜치): 행별 검토 결과, 새 출처, 미확인 항목.
- Notion 1107 업무 기록 페이지 두 곳: 이번에 끝난 항목에 취소선과 PR 번호를 달았습니다.

## 3. 구현한 범위와 한계

| 구현 | 결과 | 남은 경계 |
| --- | --- | --- |
| guard transaction (PR16) | journal lock 아래에서 prepare → 필요 시 halt → baseline 저장+CAS → guard 저장+CAS → complete. 단계 사이에서 멈춘 뒤 같은 package로 다시 실행하면 중복 행 없이 끝남 | 실제 package 출처·owner/controller 문맥·신뢰 시계·계좌 관측 발행을 묶는 production adapter 없음 |
| 재시작 분류 | classify_restart가 FRESH·PENDING_*·DIVERGENCE·CONSISTENT·REFUSED를 판정. 대기·불일치·거부·halt 상태는 모두 new_entries_blocked | 저장 중 찢어진 파일이나 journal 행은 고치지 않고 거부한 뒤 검토로 넘김 |
| controller 연동 | 두 journal 종류를 fold. prepare만 있고 complete가 없는 동안 새 매수만 거부. kill·halt·observe·cancel·reconcile·감소 매도는 계속 동작. prepare_session도 거부 | ContinuousAccountProvider는 아직 journal lock 없이 baseline head를 올림 |
| 규칙표 재검토 (PR15) | 47행 모두 출처 재확인, 9행 문구 수정, KR-CONDUCT-OTHERS basis에 policy 추가, review_by 갱신 | FIU 원본 첨부(XLSX/HWPX)는 열지 않음. 개별 상품·계좌 적격 확인은 여전히 미확인 |
| Windows 테스트 (PR14) | 캡처 파일을 서명한 LF 바이트 그대로 씀 | 운영 코드는 이미 바이너리로 써서 변경 없음 |

PR16은 다섯 방향(충돌 복구, 동시성, 안전 잠금, 기존 코드 동작, 테스트)으로 검토한 뒤 지적마다 두 명이 반박을 시도했습니다.
확인된 지적을 고친 뒤 같은 방식으로 다시 검토했고, 그때 찾은 새 경로(대기 중 거래에 수동 halt가 흡수되는 문제)도 고쳤습니다.
마지막 재검토는 확인된 지적 0건이었습니다. 새 검사 18곳을 하나씩 제거해 보면 각각 테스트가 최소 하나 실패합니다.

## 4. 최종 검증

- tests.control_continuous_guard_commit: 14/14.
- 전체(PR16 브랜치 1a59728): 2402 PASS / 4 FAIL / 123 NOT_RUN, 총 2529.
- main 6032aee와 PR15 브랜치: 2388 / 4 / 123, 총 2515. 실패 목록은 세 브랜치가 같습니다.
- 실패 4개: 저장소 자체 .venv 위치를 요구하는 검사 2개(이 PC는 TRADEGEN_PR9 venv 사용), PR14가 고치는 launch_study_review 2개.
- KEYLESS, 가짜 transport, 임시 TRADEGEN_HOME만 사용. CRLF 저장소 규칙 확인: git diff --stat과 --ignore-cr-at-eol 결과 동일.
- 실제 전략 통과·실계좌 연결·전자서명·활성화·주문은 이 결과에 포함되지 않습니다.

## 5. 실패 이력과 현재 작업 상태

- 첫 수정 뒤 재검토에서 halt 흡수 경로가 나와 classify_restart 규칙을 추가했습니다. prepare_session의 이른 journal 읽기가 기존 시계 재검사 테스트 한 단계를 무력화해 원래 위치의 단일 읽기로 되돌렸습니다.
- 기존 skills 테스트가 TRADEGEN_RUNS_DIR 없이 실행되면 실제 ~/.tradegen/runs 아래에 실행 기록 폴더를 만듭니다. 이번 세션의 초기 전체 실행이 폴더를 남겼고 지우지 않았습니다. 이후 실행은 TRADEGEN_RUNS_DIR를 임시 폴더로 지정했습니다. tests-hermetic-runs-1로 남깁니다.
- 작업 clone은 세션 scratch에 있고 세 브랜치 모두 push 완료. 미커밋 변경 없음, 실행 중인 관측·거래 작업 없음.
- 사용량: 주간 19% (2026-11-17 17:00 KST 재충전). 95% 기준에 닿아서 반환하는 것이 아닙니다.

## 6. 다음 개발 과업

1. rules-review-1122: PR15 병합과 소유자 approve --kind rules(2026-11-22 전). FIU 원본 첨부와 개별 상품·계좌 적격 확인은 남아 있습니다.
2. launch-held-positions-1/production-authority: 가격·사적 체결/수수료의 완전한 순서와 gap을 증명할 실제 출처. 로컬 hash를 발행자로 승격하지 않습니다.
3. launch-continuous-guard-adapter-1: PR16 단위를 실제 package 출처·owner/controller 문맥·신뢰 시계와 연결하고, shared baseline head의 모든 전진을 control journal로 보내는 writer를 만듭니다. owner-log system_halt append와 옛 일일 정지 소비자도 여기에 속합니다.
4. launch-planner-provider-1, launch-controlled-coordinator-1, launch-private-capture-setup-1: 이전 문서 6절 4·5항 그대로.
5. e1-14-owner-setup, launch-prospective-study, KIS/OKX 수집기, launch-multi-market-validation-1: 실제 Windows·계좌·미래 관측이 필요합니다.
6. tests-hermetic-runs-1: 테스트가 실제 ~/.tradegen/runs에 쓰지 않도록 고칩니다. 이미 생긴 폴더 삭제는 소유자에게 먼저 묻습니다.

현재 하한(원금·최고점) 규칙에서는 초기 구간 sizing이 STUCK_AT_START를 반환합니다. 하한 완화·수수료 예외는 승인되지 않았고 소유자 결정 사항입니다.

## 7. 소유자가 할 순서

1. PR14를 검토하고 병합합니다. 서명할 것 없음.
2. PR15를 검토하고 병합한 뒤 Windows에서 approve --kind rules를 직접 실행합니다. 2026-11-22이 지나면 25행이 새 노출을 거부합니다.
3. PR16을 검토하고 병합한 뒤 code-approve를 직접 실행합니다. 서명 전에는 이전 코드 지문이 유지되어 새 코드가 거부됩니다. tests/launch_guards.py의 CAS_CALLERS 허용 목록 확장 한 줄을 특히 확인해 주세요.
4. rules --check로 현재 효력을 확인합니다. 병합·서명만으로 실거래가 시작되지는 않습니다.

## 8. 유지할 제한

이전 문서 8절과 같습니다. 실제 API·키·비밀번호·서명 암호·실 owner log 접근, 실제 홈 쓰기, 서명·활성화·주문을 하지 않습니다.
공개 저장소에는 금액·개인 경로·계좌 식별자·비공개 자료를 올리지 않습니다. QUANTGEN과 frozen 연구를 수정하지 않습니다.

## 9. 다음 에이전트가 이어받을 지시

AGENTS.md, 이 문서, LEDGER.md, 세 PR 본문을 먼저 읽습니다. 미병합 PR을 병합하지 않습니다.
새 개발은 병합된 main에서 새 브랜치로 시작합니다. PR16이 아직 미병합이면 그 브랜치 위에 쌓지 말고 의존 여부를 먼저 확인합니다.
전체 검사는 TRADEGEN_RUNS_DIR를 임시 폴더로 지정하고 실행합니다.

## 10. 전달 및 기록

세 브랜치를 push하고 PR을 열었으며 Notion 1107 기록에 취소선을 달았습니다.
법률·세무·투자 조언이 아니며 작성자는 면허를 가진 자문가가 아닙니다.
