---
status: returned
reason: manual
from: gpt
task: upbit-universe
cycle: 2026-11-24
done_ids: owner-merges-1127, blocker1-approach-a-code/a1-a2, protective-hold/p2-integration, launch-planner-provider-1, launch-controlled-coordinator-1, live-cpp20-accel-1, m11-didm-quantgpt-section12-1, qlib-lab-model-factory-1, launch-kis-live-collector-1, launch-okx-live-collector-1, launch-multi-market-validation-1/account-fixtures, pr79-upbit-receipt-review-1, rules-review-1202/preparation, policy-loss-budget-plan-1, pr79-study-gate-repair-1, pr79-native-integrity-1, pr79-controlled-rehearsal-1, pr79-upbit-crosscheck-preview-1, pr79-independent-review-1, first-trade-account-startup-1128, didm-coverage-and-receipts-1128, didm-upside-research-1128, first-trade-historical-comparison-1128
next_ids: rules-review-1202, launch-multi-market-validation-1, launch-held-positions-1/production-authority, launch-continuous-guard-adapter-1, universe-pr5, universe-pr5/recovery-operations, universe-pr5-clock-notify, launch-private-capture-setup-1, universe-code-approve, e1-14-owner-setup, launch-prospective-study
updated_at: 2026-11-28T15:00:40+09:00
stale_after_hours: 24
waiting_on: none
work_branch: gpt/first-trade-integration-20261128
work_commit: 9a2ad28a0582ad5693a3f25a71ac224d9652a722
uncommitted_changes: no
pr: 83, 82, 81, 80, 79, 69
usage_weekly_pct: unknown
usage_source: unavailable
usage_5h_pct: unknown
usage_resets_at: unknown
session: Codex Cloud PR 82, performance evaluation and PR 83
---

# TRADEGEN 인수인계 · 첫 거래 통합 및 네 사건의 역사적 재생

## 0. 한 줄 요약

소유자가 첫 거래 전 세 과제(계좌 대사, 손실 보호·재시작 복구, 전향 연구·배포 승인)를 최우선으로 지정했다. [PR #82](https://github.com/xkg4real/tradegen/pull/82)에서 계좌·가드·연구 경로를 보완했다. DIDM은 TRADEGEN에서 먼저 개발하고 검증된 공통 부분을 QUANTGEN에 동기화한다. 네 사건의 실험과 운영 검증의 차이는 [최신 인계 기록](context/upbit-universe/gpt-20261128/첫거래_DIDM_사건연구_인계.md)에 있다.

PR #79 원본 `cd70bdd`을 검토해 [PR #80](https://github.com/xkg4real/tradegen/pull/80)에 수정했다. 체결·분봉 대조는 [PR #81](https://github.com/xkg4real/tradegen/pull/81)에 올렸다. [이번 작업의 인계문](context/upbit-universe/gpt-20261128/TRADEGEN_인수인계_2026-11-28.md)과 [검증 보고서](context/upbit-universe/gpt-20261128/PR79_오프라인_검증.md)에 재개 지점이 있다. 운영용 자동주문은 차단돼 있다.

## 1. 목표와 완료 조건

> 위 텍스트는 Antigravity가 실행한 코드 구성의 인계 메시지입니다. 깃허브에서 인수인계 문서를 찾아 남은 일들을 마저 진행해주세요. 만약, "GPT-Handoff-Current.md" 파일이 직접적으로 필요하다면 알려주세요

대상은 PR #79의 독립 검토·수정, 규칙표 점검 준비, 다중시장 모의 계좌 증거, 손실 예산 모의 및 운영 런처의 남은 작업이다. PR·원본·검증 결과를 재현할 수 있어야 한다.

## 2. 근거

- Antigravity [인계 원본](https://github.com/xkg4real/tradegen/blob/f98c868ef10cedbad18c97d530bad513c994a3ae/CURRENT.md)과 [PR #79](https://github.com/xkg4real/tradegen/pull/79)
- [요구사항별 검토표](https://github.com/xkg4real/tradegen/blob/gpt/pr79-followup-20261128/docs/reviews/2026-11-28-pr79-requirements.md), [12월 점검 준비](https://github.com/xkg4real/tradegen/blob/gpt/pr79-followup-20261128/docs/reviews/2026-12-02-rules-preparation.md), [손실 예산 계획](https://github.com/xkg4real/tradegen/blob/gpt/pr79-followup-20261128/docs/reviews/2026-11-28-loss-budget-plan.md)
- 비공개 Notion ‘TRADEGEN : Remaining Work’, 저장소 `AGENTS.md` 및 `LEDGER.md`

## 3. 판단 기록

- 배포 권한·보유 관리·연속 가드가 운영 진입점까지 연결돼야 실제 거래를 검토할 수 있다. 현재 런처는 그 전에 중단하며 모의 실행만 검증했다. 기한 도래 시 새 관리 승인을 요청하는 것이 소유자 정책이다.
- Y를 독립 레코드로 만들던 PR #79 초안은 기존 한도 서명 규약과 충돌했다. 후속 PR은 `limit_set` 안의 선택 숫자와 기존 D12 효력 규칙을 사용하고 최대 5%를 검증한다. 인정된 모형을 이용한 적응형 Y와 이력 연결은 별도 과업이다.
- 원자료·기준 모형의 부족과 평가 시점 이후 정보가 연구 승격에 미친 영향을 수정했다. 시장 수익성 검증에는 사전등록 및 실제로 수신한 당시 자료가 필요하다.

## 4. 진행 상황

- 완료한 ID와 재현 결과는 이 파일의 `done_ids`와 `LEDGER.md`에 있다. KIS·OKX 수집기 및 교차 계좌 대사는 모의 원본으로 검증한 범위다.
- Linux의 제어 런처 리허설 7건과 보유 복구 6건이 통과했다. Linux 등록 검사 3,189회 중 최초 3,166회 통과, 수정 후 9회 통과, Windows 전용 14회 미실행. Windows에서 전용 14건을 포함한 25건 모두 통과했다. [원본 감사 PR #81](https://github.com/xkg4real/tradegen/pull/81)에서 합성 계좌 통합 검사 219건이 통과했다.

## 5. 중단 지점

PR #82에 원본 수신·연구 재현·상방 후보·프로그램 외부 배포 비교·계좌 대사 및 잠금 복구를 반영했다. 네 사건에 대한 비공개 역사 연구는 사전 고정 소스 `8a840a3`을 사용했다. 운영 D2·D3·현지 호가와 지정가 체결의 증거가 불충분하여 세 가지 공개 자료 기반 대리 실험을 분리했다. 17개 적격 사례를 두 비용으로 계산하고 두 비교군 장부 68개를 대조했다. 과거 연구가 운영 승인을 대신하지 않는다.

## 6. 다음 할 일

원래 DIDM 기사 수·양방향 호가·실제 배포 모형의 원본이 제공되면 이번 사건 연구를 동일한 조건으로 재생한다. 변동성 큰 발표에서의 상방 진입은 발표 전·후 수익 및 시간외 호가를 구분하고, Q-score 연구에는 실제 수신·산출·집행 가능 시각을 추가한다.

1. 두 초안의 검토 보고서를 확인하고 남은 운영 권한 및 보유 관리 과업을 이어받는다. 분봉 실측 증거, 주문 원장과 청산 권한은 별도 요건이다.
2. `launch-held-positions-1/production-authority`, `launch-continuous-guard-adapter-1` 배포에 결속한 관리 권한, 계좌·미체결 대사, 가드 원장 확정·알림·복구를 실제 진입점으로 연결한다. 설계 결정은 최신 개정과 대조한다.
3. `rules-review-1202` 12월 2일 공식 시행일과 시장별 적용 범위를 확인한다. OKX 경계는 12월 3일 00:00 KST다.
4. `launch-multi-market-validation-1`, `launch-prospective-study`, `launch-private-capture-setup-1` 실제 적격 데이터와 연구 사용 권한을 확인하고 전향 수집을 시작할 조건을 갖춘다.
5. `universe-pr5`, `universe-pr5/recovery-operations`는 Claude의 미공개 작업을 먼저 대조한다. `universe-pr5-clock-notify`는 PR5 실제 병합 뒤 진행한다. `universe-code-approve`, `e1-14-owner-setup`은 승인할 코드와 운영 요건이 준비된 뒤 소유자가 진행한다.

## 7. 지켜야 할 범위

인계 규약은 모의 계좌·임시 홈을 사용하도록 정한다. 실제 주문·키·소유자 홈·main 병합은 이번 작업에 포함되지 않는다. 동결 연구 데이터와 `qa/acceptance_results.json`을 보존한다. 실제 수익·주문 응답 시간은 미측정이다.

## 8. 소유자와 공동 작업자

소유자 Windows의 `floor_state_check` S1~S12와 허용된 QUANTGEN 비공개 SQLite 사본의 오프라인 검사(TG-MAN-012)는 수동 확인이 남았다. 공개 저장소에는 금액·계좌·자격 자료를 기록하지 않는다. 코드 검토, 한도 서명, 전략 승인과 실거래 활성화 권한은 각각 확인한다.

## 9. 다음 에이전트의 시작 지점

연구 성능 후속 기록. 현금 수익률, 시장 가격 및 매수보유 비용을 구분하는 독립 도구를 [PR #83](https://github.com/xkg4real/tradegen/pull/83)에서 검토한다. 추세의 방향을 양쪽으로 거래하는 IBIT·BITI 모의계좌는 선거 구간(10/27~11/16)에 +21.16%, 다른 기간(3/2~10/26)에 −29.17%였다. IBIT·현금 대조군은 각각 0.00%, −5.68%였다. 두 기간은 독립 계좌로 재시작했다. 28개 분기의 방향 연구에서 2025년 가격 모형 상승 고신뢰 판단은 115회 중 46회 적중했다. 2025년 이동평균 3/15와 강화된 진입 조건은 기존 5/20보다 낮은 수익을 냈다. 운영 승격은 미결이다. 규칙·비용·시점·보호 하한을 유지하고, 다음 미사용 구간에서 상방과 하방을 별도 검증한다. 상세 연구 원장과 자료 묶음은 소유자에게 직접 전달했다.


인계 시점의 `work_commit`, PR과 검증 문서를 먼저 읽고 `LEDGER.md`의 완료 ID와 대조한다. PR #79 원본에서 제안한 별도 서명 명령은 사용하지 않는다. 가드 어댑터나 연구 모형은 해당 미완료 항목과 실제 입력의 근거를 대조한 뒤 작업한다.

## 10. 환경과 재현

검증은 Linux Cloud 임시 홈, 모의 전송과 별도 Windows CI 테스트 프로필에서 수행한다. 새 환경에서는 저장소에 문서화된 빌드 입력으로 네이티브 바이너리를 재생성한다. 배포 승인 해시와 현재 환경 바이너리가 맞을 때만 사용한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
