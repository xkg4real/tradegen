---
status: taken
reason: manual
from: gpt
task: upbit-universe
cycle: 2026-11-24
done_ids: owner-merges-1127, blocker1-approach-a-code/a1-a2, protective-hold/p2-integration, launch-planner-provider-1, launch-controlled-coordinator-1, live-cpp20-accel-1, m11-didm-quantgpt-section12-1, qlib-lab-model-factory-1, launch-kis-live-collector-1, launch-okx-live-collector-1, launch-multi-market-validation-1/account-fixtures, pr79-upbit-receipt-review-1, rules-review-1202/preparation, policy-loss-budget-plan-1, pr79-study-gate-repair-1, pr79-native-integrity-1
next_ids: pr79-independent-review-1, rules-review-1202, launch-multi-market-validation-1, launch-held-positions-1/production-authority, launch-continuous-guard-adapter-1, universe-pr5, universe-pr5/recovery-operations, universe-pr5-clock-notify, launch-private-capture-setup-1, universe-code-approve, e1-14-owner-setup, launch-prospective-study
updated_at: 2026-11-28T13:12:15+09:00
stale_after_hours: 24
waiting_on: none
work_branch: gpt/pr79-followup-20261128
work_commit: 171365f
uncommitted_changes: no
pr: 80 (PR #79 대상 후속 초안), 79 (검토 중), 69 (초안)
usage_weekly_pct: unknown
usage_source: unavailable
usage_5h_pct: unknown
usage_resets_at: 2026-12-01T17:00:00+09:00
session: Codex Cloud, PR #79 독립 검증
---

# 인수인계: 3대 메인 목표(실거래 제어·C++20 가속, DIDM·QuantGPT 파이프라인, Qlib 모형 팩토리) PR #79 개설 및 후속 인계

## 0. 한 줄 요약

**GPT 진행 중.** 후속 [PR #80](https://github.com/xkg4real/tradegen/pull/80)의 최초 체크포인트. KIS와 OKX의 모의 증거 수집 및 양 시장 합산 대사를 검증했다. PR #79 원본의 보유 관리 권한, 사후 시점으로 학습·평가하는 문제와 서명 형식 불일치를 수정 중이다. 독립 검토가 끝날 때까지 운영 서명·활성화를 진행하지 않는다.

소유자가 PR #74~#78을 `main`(`3ef3f9a`)에 병합한 뒤, Antigravity 세션에서 3대 메인 목표(① 실거래 `controlled` 개통·Blocker 1 Approach A·Standing Amendment A2·C++20 저지연 엔진 `44b226c`, ② DIDM & QuantGPT 브리지 및 방향 모형 12절 전체 도구 `2a94271`, ③ Qlib 방식 지속 모형 팩토리 `qlib_lab/` `cd70bdd`)를 구현·검증해 PR #79(`gpt/live-cpp-didm-qlib-20261127`)를 열었습니다. 이어받는 GPT는 먼저 `pr79-independent-review-1`(PR #79 독립 코드 리뷰·경계 대조·필요 시 후속 보완 커밋)과 다가오는 `rules-review-1202` 규칙 테이블 월간 점검 준비부터 진행합니다.

## 1. 목표와 완료 조건

- **사용자 요청 (원문 그대로):**
  > 깃허브에서 Tradegen repository에서 남은 업무들을 claude가 남기고 간 인계 파일들을 참고해서 마저 진행해주세요. 이때, (1) 실거래/실주문(라이브 실시간) 활성화 및 시간 딜레이 최소화(C++ 도입 등) (2) DIDM 및 QuantGPT 도입, 그리고 (3) 내부 모형/모델의 지속적인 개발/수정/발전을 위한 qlib의 방식 차입 (웹사이트 : https://github.com/microsoft/qlib) 이라는 세가지 메인 목표를 세워 멈추지 말고 계속 진행해주세요.
  > 이번 커밋/푸시 및 PR 생성 직후 Handoff 브랜치에 있는 양식을 그대로 따라해서 GPT한테 넘길 인수인계 문서를 하나 생성해주세요
- **완료 조건:**
  1. PR #79(`gpt/live-cpp-didm-qlib-20261127`, 커밋 `44b226c`, `2a94271`, `cd70bdd`)에 대한 독립 정적·동적 검증(`pr79-independent-review-1`) 완료 및 결함 발견 시 후속 수정 PR/커밋 반영
  2. 아래 6절의 남은 오프라인 구현 가능 항목(`rules-review-1202`, `policy-loss-budget-plan-1`, `launch-kis-live-collector-1`, `launch-okx-live-collector-1` 등)을 순서대로 진행하고 각 ID마다 테스트 PASS 및 `LEDGER.md` 기록
- **범위 밖:**
  - `main` 브랜치 직접 push 및 PR 병합(소유자만 수행)
  - 실제 거래소 API 호출, 자격 증명·`.env` 비밀값 열람, 실제 `~/.tradegen` 및 `~/.nextgen` 쓰기, 실제 키로 `tools/signer/sign.py` 실행, 시스템 무장(arm) 및 실주문 제출(`AGENTS.md` 5절 절대 준수)
  - 동결 연구 파일(`research_lab/**`, `grokteam/PREREG_book.json`, `grokteam/out/frozen_book/`, `docs/research/2026-10-31-strategy-lab/**`) 변경 금지

## 2. 근거

무엇을 근거로 작업하고 있었는지 적습니다. 다음 사람이 같은 자료를 열어볼 수 있게 경로를 정확히 씁니다.

| 종류 | 위치 | 이 작업에서 쓰는 부분 |
|---|---|---|
| 블로커1 사양 및 계획 | `docs/superpowers/specs/2026-11-20-blocker1-held-interval-approach-a-design.md`, `origin/claude/blocker1-a1-a2:docs/superpowers/plans/2026-11-24-blocker1-approach-a-implementation.md` | 규칙 BR-1~BR-26, OQ1~OQ18 소유자 결정 반영, `/v1/trades/ticks`·`/v1/order` 수집, 유동성 공백 `best_bid`, 다중 코인 연속 가치평가, `00:00`/`22:00 KST` 경계 분할 |
| 보호 보유 개정 A2 | `docs/superpowers/specs/2026-11-24-standing-amendment-a2-design.md` (PR #74, `main` `3ef3f9a`) | 오류·재시작·마감 시 강제 매도 전면 금지, 앱 취득 수량 $q_{\text{app}}$ 한도 내 `S`/`W`/`T`/`B` 보호 매도, `PERSISTENT_HALT` 시 소유자 `exit` 보존(N2) |
| 제어 런처·플래너 사양 | `docs/superpowers/specs/2026-11-12-controlled-launch-and-planner-design.md` | `Runner`·`Coordinator` `"controlled"` 모드 개통, D14 클린 `CurrentPlanner`, `tools/owner/live.py` 및 `launch.py`(`odds`, `cancel-all`, `exit`) |
| 방향 모형·QuantGPT 계약 | `docs/direction-forecast-contract.md`, `docs/direction-model-study-design.md` (PR #78), `xkg4real/quantgen` `origin/handoff:QUANTGPT_TRADEGEN.md` (v0.2), `origin/claude/quantgpt-q0-20261124` (`qgpt/`) | 12절 연구 도구 8종 전체, `quantgen-feature-snapshot-v0` 및 `qgpt-env-v1` 검증/채점, D14 코드 닫힘 격리 및 5대 연구 전용 플래그 |
| 외부 아키텍처 참조 | https://github.com/microsoft/qlib (`qlib/data`, `qlib/model`, `qlib/workflow`, `qlib/workflow/online`) | `qlib_lab/` 수식형 알파·이중시점 PIT 엔진, `DataHandlerLP`/`DatasetH`, `HistGBDT`/`DoubleEnsemble`/`RegimeDriftAdapter`, 무피클 `Recorder` + `FamilyLedger` DSR 게이트, `RollingTrainer`·`OnlineManager` |
| 이번 PR #79 문서 | `docs/live-execution-and-cpp-acceleration.md`, `docs/didm-quantgpt-pipeline.md`, `docs/qlib-model-factory.md` (`gpt/live-cpp-didm-qlib-20261127`) | 3대 목표 상세 구현 명세, C++20/C++17 빌드·검증 절차 및 소유자 CLI 매뉴얼 |

## 3. 판단 기록

| 결정 | 이유 | 버린 대안과 이유 |
|---|---|---|
| D14 C++20 가속 경계를 `core/compliance/native_accel.py` 단일 AST 핀(`ACCEL_NATIVE_AST_SHA256`)으로 집약하고 `EXPECTED_SOURCE_SHA256` + `O_NOFOLLOW` `/proc/self/fd/<fd>` 검증 후 로드 | `core/odds`, `execution_accounts`, `execution_control`, `execution_launch` 가드 스위트가 모두 `core.compliance.*` 임포트를 허용하며 `revocation_paths.py`의 기존 AST 핀 패턴과 일관됨. 미빌드 환경이나 `10^-18` 범위 밖 입력은 `TG_FALLBACK_PRECISION`으로 순수 Python `Decimal`/`Fraction` 경로로 무손실 폴백 | 각 `execution*` 패키지에 개별 `ctypes` 로더 추가: 모든 가드 스위트의 `EFFECT_PREFIXES` 차단 범위를 넓혀 보안 표면이 커지므로 기각 |
| `tools/owner/planner.py`(`CurrentPlanner`)에서 `core.oddsdata`를 임포트하지 않고 `execution_accounts.universe.daily_bars` + `core.odds.simulate` + `execution_control.universe_odds`만 사용 | `tools/owner/`는 D14 `owner.code_files` 재귀 시드이므로 `core.oddsdata`나 `data.*`를 임포트하면 `odds_guards/test_code_closure_holds_no_data_layer`가 즉시 실패함 | `core.oddsdata` 직접 호출: D14 서명 클로저에 데이터 계층이 유입되어 규칙 위반 |
| DIDM·QuantGPT 파이프라인 전체를 `tools/research/` 아래에 두고 Regime A(`ensure_ascii=True`)와 Regime B(`ensure_ascii=False`) 직렬화를 명시적으로 분리 | `direction-model-study-design.md` 2절·12절의 위치 규칙을 그대로 만족하며, 한글(`label_ko` 등) 포함 시 `qgpt-env-v1`/`AttemptLedger`(Regime B)와 `tradegen-direction-forecast-v1`(Regime A)의 SHA-256 불일치를 원천 방지 | 단일 `json.dumps` 헬퍼 사용: 비ASCII 문자가 들어올 때 양쪽 저장소 간 해시 검증이 깨지므로 기각 |
| Qlib 방식 모형 팩토리를 동결된 `research_lab/` 밖의 최상위 `qlib_lab/`으로 신설하고 `pickle`을 전면 금지(JSON + `allow_pickle=False` NPZ) | `research_lab/run.py`는 9개 파일 바이트 해시가 고정된 과거 연구이므로 수정 불가하며, `pickle`은 임의 코드 실행 위험이 있어 TRADEGEN 보안 기준과 충돌함. 또한 `RollingGen`에서 프로세서 `[fit_start_time, fit_end_time]`을 창마다 자동 재결속하고 비중첩 `[active_from, active_until)`만 노출해 Qlib 원본 `manager.py`의 신호 오염 문제를 구조적으로 해결 | `research_lab/` 내부 확장 또는 원본 `pyqlib` 패키지 설치: 동결 연구 검증 파괴 및 `constraints.txt` 외부 의존성 오염으로 기각 |

## 4. 진행 상황

- [x] 12월 규칙 재검토 자료, PLB 모의 검증 및 구현 순서 작성. 연구 시점·자료 동일성, 네이티브 무결성 보완. PR #80의 코드 기준을 `171365f`에 고정해 운영 권한·계좌·제어·준법 전체 시험 실행 중.

- [x] KIS 9개, OKX 8개, 다시장 대사 4개 모의 검사. 업비트 체결 자료 경계 7개 검사. 입력과 거절 조건을 각 후보 커밋에 보존.
- [ ] 원 사양 비교와 포괄적 검증 진행. 아래 Antigravity 기록은 원 커밋의 주장으로 보존한다.

- [x] `owner-merges-1127` 소유자가 PR #74(개정 A2), #75(M11-T3 어댑터), #76(M11-T8 대용량 DIDM 스트리밍), #77(패스키 개정 P1), #78(M11-T6 방향 모형 설계)을 `main`(`3ef3f9a`)에 병합 확인 — 커밋 `3ef3f9a`, LEDGER 기록함
- [x] `blocker1-approach-a-code/a1-a2` `/v1/trades/ticks`·`/v1/order` E1 경로, 역방향 체결 수집·주문 수수료 정산, 유동성 공백 `best_bid`·BR-10 `Y` 래치, 4-마켓 연속 가치평가, `00:00`/`22:00 KST` 경계 분할, `owner.py`/`sign.py` D12 서명 미러링 — 커밋 `44b226c`, LEDGER 기록함
- [x] `protective-hold/p2-integration` Standing Amendment A2 보호 보유 통합(오류·재시작·마감 시 강제 매도 0건, 앱 취득분 $q_{\text{app}}$ 한정 `S`/`W`/`T`/`B` 보호 매도, `PERSISTENT_HALT` 시 소유자 `exit` 보존) — 커밋 `44b226c`, LEDGER 기록함
- [x] `launch-planner-provider-1` D14 클린 `CurrentPlanner`(`tools/owner/planner.py`) 및 `tools/owner/launch.py`(`odds`, `cancel-all`, `exit`) 구현 — 커밋 `44b226c`, LEDGER 기록함
- [x] `launch-controlled-coordinator-1` `Runner`·`Coordinator` `"controlled"` 모드 개통 및 독점 `live.lock`·조회/주문 키 분리 기반 `tools/owner/live.py` 구현 — 커밋 `44b226c`, LEDGER 기록함
- [x] `live-cpp20-accel-1` `native/tradegen_fast`(`libtradegen_fast.so`) C++20 `__int128`/`u256` 고정소수점 가속 커널 HP-1~HP-6 및 `native_accel.py`/`_kis_native.py` 브리지·차등 검증 — 커밋 `44b226c`, LEDGER 기록함
- [x] `m11-didm-quantgpt-section12-1` `quantgpt_feature_bridge.py` 및 `direction-model-study-design.md` 12절 연구 도구 8종 전체 + E2E 파이프라인 테스트(`226/226 PASS`) — 커밋 `2a94271`, LEDGER 기록함
- [x] `qlib-lab-model-factory-1` `qlib_lab/` 5-Pillar 지속 모형 개발·진화 프레임워크 + C++17 `libqlib_accel.so` + `FamilyLedger` DSR 게이트 + `OnlineManager` + `v1` 익스포터(`30/30 PASS`) — 커밋 `cd70bdd`, LEDGER 기록함
- [ ] `pr79-independent-review-1` PR #79(`gpt/live-cpp-didm-qlib-20261127` `cd70bdd`) 전체 독립 코드 리뷰, 경계·회귀 검증 및 후속 보완 ← **여기서 멈춤 (GPT 첫 작업)**
- [ ] `rules-review-1202` 2026-12-02 도래 예정 컴플라이언스 규칙 테이블(`kr_rules.yaml`, `instruments.yaml`, `venues.yaml`) 월간 점검 초안 준비
- [ ] `policy-loss-budget-plan-1`, `launch-kis-live-collector-1`, `launch-okx-live-collector-1`, `launch-multi-market-validation-1` 등 후속 과업

**마지막으로 통과한 검증:**

```
브랜치 gpt/live-cpp-didm-qlib-20261127 (커밋 cd70bdd), Linux Python 3.13.18 .venv + g++ 13.3, keyless, 네트워크 소켓 차단
- native_cpp_acceptance: 7/7 PASS (1,160+ C++20 vs Python 무작위 차등 정합성 및 변조 거부 포함)
- live_controlled_acceptance: 7/7 PASS (Approach A, BR-10 Y, D12, controlled 모드, 개정 A2 보호 보유)
- unittest discover -s tools/research -p "test_*.py": 226/226 PASS
- tests.qlib_lab_acceptance: 30/30 PASS (C++17 커널 및 순수 NumPy 폴백 모두 통과)
- 기존 가드·수용 스위트: compliance_guards 17/17, compliance_owner 54/54, compliance_signer 대조 12/12, execution 280/280, accounts 161/161, orders/renewal_boundaries 52/52, kis_live 47/47, research 35/35, launch_protective_store 36/36, launch_coordinator 30/30, launch_carry_review 23/23, launch_carry_evaluator 21/21, launch_account_interval 19/19, launch_program 15/15, owner_guards 3/3 (모두 0 FAIL)
- EOL 정합성: git diff origin/main...HEAD --stat == git diff origin/main...HEAD --stat --ignore-cr-at-eol (PARITY_OK)
```

## 5. 중단 지점

커밋되지 않은 변경이나 실패 중인 테스트는 없습니다(`git status --short` 빈 출력). 브랜치 `gpt/live-cpp-didm-qlib-20261127`(`cd70bdd`)이 `origin`에 push되었고 GitHub에 **PR #79**(`https://github.com/xkg4real/tradegen/pull/79`)가 열려 있습니다. 네이티브 빌드 산출물(`native/tradegen_fast/build/`, `qlib_lab/_accel/build/`)은 `.gitignore` 처리되어 있어 새 환경에서는 아래 10절의 빌드 스크립트를 실행하면 공유 라이브러리가 생성되며, 빌드 전에도 모든 호출부가 순수 Python/NumPy 경로로 무손실 작동합니다.

## 6. 다음 할 일 (순서대로)

각 항목에 작업 ID와 그 계획 Task의 완료 기준을 함께 적습니다. `LEDGER.md`에 이미 있는 ID는 적지 않습니다.

1. `pr79-independent-review-1` `origin/gpt/live-cpp-didm-qlib-20261127`(`cd70bdd`)에서 새 검토 브랜치를 분기해 PR #79의 3개 커밋(`44b226c`, `2a94271`, `cd70bdd`)을 사양 원문(`2026-11-20-blocker1-held-interval-approach-a-design.md`, `2026-11-24-standing-amendment-a2-design.md`, `2026-11-12-controlled-launch-and-planner-design.md`, `direction-model-study-design.md`)과 줄 단위로 독립 대조하고, 아직 일괄 실행하지 않은 나머지 `launch_acceptance`·`control_acceptance`·`compliance_acceptance` 하위 케이스까지 전수 확인합니다. 보완할 엣지 케이스가 있으면 수정 커밋과 회귀 테스트를 추가해 별도 후속 PR(또는 PR #79 코멘트/후속 브랜치)로 제출합니다. — 완료 기준: 독립 리뷰 보고서 작성, 발견된 결함 0건(또는 수정 테스트 PASS), 줄바꿈 `PARITY_OK`, `LEDGER.md` 기록
2. `rules-review-1202` 2026-12-02 도래 예정인 컴플라이언스 규칙 테이블(`core/compliance/kr_rules.yaml`, `instruments.yaml`, `core/odds/venues.yaml`, OKX 회색 행 2026-12-03 자동 종료 경계 포함) 월간 재검토 체크리스트와 오프라인 검증(`python -m core.compliance.rules --check`) 보고서를 준비합니다(실제 서명은 소유자 몫). — 완료 기준: 변경 필요 행·근거 문서 정리 및 `compliance_tables`/`compliance_cli` 전체 PASS
3. `launch-kis-live-collector-1` 및 `launch-okx-live-collector-1` KIS 국내/해외 현금주식 및 OKX 현물 계좌에 대해 Upbit `upbit_collector.py`와 동등한 오프라인 모의 트랜스포트 기반 증거 수집기·정합성 대사 어댑터를 구현합니다(실계좌 호출 금지, 오프라인 픽스처만 사용). — 완료 기준: 각 거래소 수집기 단위·수용 테스트 PASS 및 D14 가드 통과
4. `launch-held-positions-1/production-authority` 및 `launch-continuous-guard-adapter-1` 보유 포지션 운영 권한 경계와 연속 가드 어댑터(`continuous_guard_commit.py` ↔ `Coordinator`)의 잔여 엣지 케이스 통합 테스트를 보강합니다. — 완료 기준: `launch_acceptance` 및 `control_acceptance` 관련 스위트 전수 PASS
5. `policy-loss-budget-plan-1` 원금 손실 예산(`principal-loss-budget-spec`) 후속 계획 문서화 및 오프라인 시뮬레이션 검증을 정리합니다. — 완료 기준: 계획/검증 문서 및 관련 `control_risk` 테스트 PASS

## 7. 주의사항 / 하지 말 것

- **`AGENTS.md` 5절 절대 준수:** 시스템을 무장(arm)하거나, 실제 주문을 넣거나, 자격 증명·API 키·토큰·비밀번호·서명 암호를 읽거나 출력하지 않습니다. 실제 `~/.tradegen`과 `~/.nextgen`을 절대 건드리지 않습니다.
- **병합 금지:** `main`에 직접 push하거나 PR #79, PR #69 등 어떤 PR도 에이전트가 직접 merge하지 않습니다.
- **QUANTGEN 수정 금지:** `xkg4real/quantgen`은 읽기만 가능하며 절대 수정·push하지 않습니다.
- **동결 자산 보호:** `research_lab/**`, `grokteam/PREREG_book.json`, `grokteam/out/frozen_book/`, `docs/research/2026-10-31-strategy-lab/**`, `qa/acceptance_results.json`을 수정하지 않습니다(`tests/run_all.py`의 `main()`을 직접 돌리면 `qa/acceptance_results.json`을 덮어쓰므로 스위트별 실행기나 Python 인라인 `run(tests())`를 사용합니다).
- **D14 코드 닫힘 격리 유지:** `core/compliance`, `core/odds`, `execution*`, `tools/owner` 안의 어떤 파일도 `tools/research/*`, `qlib_lab/*`, `core/oddsdata/*`, `data/*`, `core/quant/*`, `config.py`를 임포트하면 안 됩니다. 또한 `core/compliance/owner.py`와 `tools/signer/sign.py`(및 `tools/approval_broker/release.py`)의 클로저 스캔 헬퍼 7개는 글자 단위로 동일해야 합니다.
- **줄바꿈(CRLF/LF) 보존:** `.gitattributes`가 `* -text`이므로 `execution_launch/coordinator.py`, `execution_launch/account_interval.py`, `README.md`, `tests/run_all.py` 등 기존 CRLF 파일은 반드시 CRLF(`\r\n`)를 유지하고, 나머지 파일과 신규 파일은 LF(`\n`)를 유지합니다. 커밋 전 항상 `git diff --cached --stat`과 `git diff --cached --stat --ignore-cr-at-eol` 일치를 확인하세요.

## 8. 사용자에게 물어야 할 것

- **PR #79 검토 및 병합 승인:** `https://github.com/xkg4real/tradegen/pull/79` 확인 및 `main` 병합 여부
- **소유자 PC 오프라인 서명 (`tools/signer/sign.py`):** PR #79 병합 후 소유자 PC의 외부 서명기 사본을 최신 `tools/signer/sign.py`로 갱신하고, 새 D14 코드 해시 `code_approved` 서명 및 계좌 스코프별 `bid-gap-set`($0 < Y \le 0.05$), `protective-terms-set`(`--trailing-stop-x`, `--halt-margin-krw`, `--daily-margin-krw`) 서명 진행 여부
- **업비트 주문 전용 키 분리 (O21 연계):** `tools/owner/live.py` 기동 전 조회 전용(`UPBIT_ACCESS_KEY`/`SECRET_KEY`)과 별도인 주문 전용(`UPBIT_ORDER_ACCESS_KEY`/`SECRET_KEY`) 발급·설정 여부
- **방향 모형 연구(M11-T4) 10절 비공개 결정값:** `docs/direction-model-study-design.md` 10절(비공개 연구 상한 `ceiling_y`, `up_y`, `down_y`, 수집 주기 등 — 공개 PR에 적지 말고 소유자 비공개 폴더에 보관) 및 `QUANTGPT_TRADEGEN.md` 9.4절 주기 실행 여부

## 9. 이어받는 에이전트에게 주는 지시문

아래 블록을 그대로 첫 지시로 사용합니다. 이 문서를 쓴 에이전트가 직접 작성합니다.

```
너는 xkg4real/tradegen 레포의 "upbit-universe (PR #79 후속 독립 검증 및 잔여 과업)" 작업을 이어받는다.
1. handoff 브랜치의 CURRENT.md, AGENTS.md, LEDGER.md를 먼저 읽어라. LEDGER.md에 있는 ID는 다시 하지 마라.
2. CURRENT.md의 status를 taken으로, from을 gpt로 바꾸고 updated_at을 갱신해 handoff 브랜치에 push해라.
3. AGENTS.md 2절 5번에 따라 gpt/live-cpp-didm-qlib-20261127의 cd70bdd(또는 소유자가 PR #79를 병합했다면 최신 origin/main)에서 gpt/pr79-followup-20261128 브랜치를 만들어 작업해라. AGENTS.md 5절을 한 줄도 어기지 마라.
4. 먼저 CURRENT.md 6절 1번(pr79-independent-review-1)에 따라 PR #79의 세 커밋(44b226c, 2a94271, cd70bdd)을 사양 원문과 대조하고 C++20/C++17 빌드 및 전체 오프라인 수용 스위트를 검증해라. 이어서 6절 2번(rules-review-1202 점검 준비), 3번(KIS/OKX 오프라인 수집기), 4번(보유 포지션 권한·연속 가드 통합 테스트) 순으로 진행해라.
5. ID 하나를 끝낼 때마다 LEDGER.md에 한 줄을 덧붙이고 CURRENT.md를 같은 양식으로 갱신해라. 끝나거나 멈출 때, 늦어도 화요일(2026-12-01) 17:00(KST) 전에 status를 returned로 바꿔라.
```

## 10. 결과 확인 방법

```bash
# 1. handoff 상태 및 PR #79 확인
python3 /path/to/push_handoff.py --show
gh pr view 79 --repo xkg4real/tradegen

# 2. C++20 실거래/시뮬레이션 가속 엔진 및 C++17 Qlib 커널 빌드
.venv/bin/python -X utf8 -B native/tradegen_fast/build_native.py
.venv/bin/python -X utf8 -B -m qlib_lab._accel.build_accel

# 3. 3대 목표 핵심 수용 스위트 실행 (네트워크 차단 / 오프라인)
.venv/bin/python -X utf8 -B -m tests.native_cpp_acceptance          # 기대: 7/7 PASS
.venv/bin/python -X utf8 -B -m tests.live_controlled_acceptance     # 기대: 7/7 PASS
.venv/bin/python -X utf8 -B -m unittest discover -s tools/research -p "test_*.py"  # 기대: 226/226 OK
.venv/bin/python -X utf8 -B -m tests.qlib_lab_acceptance            # 기대: 30/30 PASS

# 4. 줄바꿈(CRLF/LF) 무결성 확인
test "$(git diff origin/main...HEAD --stat)" = "$(git diff origin/main...HEAD --stat --ignore-cr-at-eol)" && echo PARITY_OK
```

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
