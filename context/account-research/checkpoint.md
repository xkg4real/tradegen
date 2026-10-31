---
status: taken
reason: account_evidence_and_research_in_progress
from: gpt
task: account-research
cycle: 2026-10-27
done_ids: cloud-compat-1, cloud-compat-2, cloud-compat-3, odds-1, odds-2, odds-3, odds-4, odds-5, odds-6, odds-7, odds-8, odds-9, odds-10, odds-11, odds-12, odds-13, odds-14, odds-15, odds-16, odds-17, odds-18, odds-19, odds-final, odds-pr, spec-rev-3-3, policy-plan-1, policy-preview-1, policy-pr, e1-1, e1-2, e1-3, e1-4, e1-5, e1-6, e1-7, e1-8, e1-9, e1-10, e1-11, e1-12, e1-13, e1-pr, e2-1, e2-2, e3-1, e3-2, e3-3, e2-3, e3-4, e2-e3-pr, pr6-pr7-merge, research-preregister-1, research-evaluate-1, account-readiness-1, research-paper-1, account-provider-1
next_ids: account-regression-1, account-research-pr
updated_at: 2026-10-31T15:59:01+09:00
stale_after_hours: 3
waiting_on: no software approval; actual credentials/network/owner activation unavailable
work_branch: gpt/account-research
work_commit: f74a40adc35771162978dc8dcd35b0b98bb7a7e1
uncommitted_changes: no
pr: https://github.com/xkg4real/tradegen/pull/8 (draft; full regression running)
usage_weekly_pct: unknown
usage_source: unavailable
handoff_threshold_pct: 95
usage_5h_pct: unknown
usage_resets_at: unknown
session: cloud Codex (TRADEGEN)
---

# 인수인계: 계좌 증거 연결과 전략 연구

## 0. 한 줄 요약

소유자가 승인한 PR #6/#7을 병합했습니다. 새 `gpt/account-research`에서 계좌 증거 provider·조회 준비 도구·실행 한도 보완·전략 연구와 PDF를 작업 중입니다. 사전 고정한 21,408개 설정을 평가했고 6개가 내부 후속 구간으로 선택됐으나 통계 기준 통과는 0개입니다. 실계좌 접속·실제 서명·활성화·주문은 수행하지 않았습니다.

## 1. 목표와 완료 조건

2026-10-31 소유자는 PR #6/#7 병합, 실계좌 연결 개발·소유자 설정 준비, 많은 전략의 정량/경제학적 검증과 논문 형식 PDF를 요청했습니다. 기존 인수인계 범위를 넘어 필요한 후속 소프트웨어를 진행합니다. 실제 키·서명·무장·주문은 AGENTS.md5절 및 소유자 실행 경계를 유지합니다.

## 2. 근거

- `docs/superpowers/plans/2026-10-31-account-research.md`
- `docs/superpowers/plans/2026-10-31-strategy-research-protocol.md`, `research_lab/protocol.json`, `research_lab/data_manifest.json`
- `docs/account-evidence-contract.md`, `docs/account-connection-runbook.md` (작성 중)
- 기존 E1/E2/E3 계획·실행 장부와 `context/execution-e1-e3/`
- `LEDGER.md`의 기존 완료 ID는 재수행하지 않습니다.

## 3. 판단 기록

- PR #6/#7에 대한 이번 사용자 승인은 병합에 적용했습니다. 새 PR에는 별도 PR별 승인이 필요합니다.
- E1 첫 페이지/float 요약은 완전한 계좌 증거가 아닙니다. 정확한 Decimal, FIFO, 모든 수수료·현금흐름·페이지·시간·통화·FX 증거를 요구하는 provider를 구현합니다.
- 연구는 기존에 분석된 캐시를 재사용한 후향적 탐색입니다. 미관측 독립 표본 검증으로 표현하지 않습니다. 8경제학적 계열의 파라미터 설정 21,408개이며 독립 아이디어 21,408개가 아닙니다.
- 후보·자료 해시·코드를 성과 평가 전에 GitHub에 고정했습니다. 후속 구간 결과를 본 뒤 튜닝하지 않습니다. 결과가 0개 통과여도 그대로 보존합니다.
- 사용량 조회 수단은 없어 unknown/unavailable입니다. 95% 도달을 추측하지 않고 작업 단위마다 push합니다.

## 4. 진행 상황

- PR #6 merge: `7676b80c24fb1f47925e2eec952a311757b7eb47`.
- PR #7 main 재타겟 후 merge: `c5459a29bf01730ad1a9b4a4588dd9b8592fe76f`.
- 사전등록 `240c5a1`, 연구 소스 고정 `8e7c6c85c5ed3799a7cb6d4ac350ebdf57af1175`, 전체 결과 `af4d240` push 완료.
- 성과 평가 전 연구 synthetic 검사35/35 PASS. 최초 평가 실행 정상 완료(15.493초), 후보21,408/선택6/통과0.
- 계좌 provider·연결 readiness·서명범위/가드·통합 수정은 `a1c0102`에 고정했습니다. accounts42/42 PASS, control통합140/140 PASS,0FAIL,0NOT_RUN입니다. 최종 전체 회귀는 f74a40a에서 실행 중입니다. PDF17쪽/4그림/11참고문헌과 전체 페이지 검수 기록을 `f74a40a`에 push했습니다.

## 5. 현재 지점

- `/workspace/tradegen-research`, `gpt/account-research`. 연구 원본 결과는 `docs/research/2026-10-31-strategy-lab/results/`에 고정했습니다.
- 연구 source freeze 이후 source/protocol/data/catalogue는 변경하지 않습니다. 신규 연구는 별도 버전/시행 수 기록이 필요합니다.
- 계좌 검토에서 현금 이중계산·다른 통화 현금 사용·가짜 주문 FX·자정 이전 history로 전날 손익 확정 문제를 수정하고 독립 검토했습니다. 자료 provenance hash는 진위 인증이 아닙니다.
- 현재 Cloud: secrets/runtime bindings/outbound identities 없음, 거래소 호스트 미허용, E1의 고정 direct-only 전송은 Cloud proxy 경로 미지원. 실제 probe 없음. 완전하고 인증된 거래소 history collector는 아직 필요합니다.
- 비공개 소유자 정책은 `/workspace/tradegen-session/owner-policy/`에만 있습니다. 개인 금액·기한을 공개 저장소에 넣지 않습니다.
- 루트가 검사/커밋을 직렬 관리합니다. 연구 성과 재실행은 하지 않습니다.

## 6. 다음 할 일

1. 계좌/통합 집중 검사42+140개 완료. 실행 중인 전체 회귀를 확인하고 실패가 있다면 원인을 수정한 뒤 필요한 검사를 진행합니다.
2. PDF17쪽 생성/검수/push 완료. 원본 자료와 PDF 해시를 보존합니다.
3. 실행 장부/QA/README를 실제 검사 결과로 갱신하고 새 PR을 생성합니다. main 직접 push나 새 PR 무승인 병합은 하지 않습니다.
4. 완료 후 새 ID를 LEDGER에 추가하고 CURRENT를 returned로 돌립니다.
5. 실제 계좌 실행 전: secure 환경 설정, 검토된 Cloud transport 경로, 완전한 계좌 collector, 소유자의 최종 서명/세션 활성화, 미지정 정책 입력, 실제 체결 가능한 전략의 새로운 검증이 남습니다. 현재 기본 CLI에서도 3거래소 모두 네트워크blocked·credentialnamesmissing·proxy미지원·execution_ready=false를 확인했습니다.

## 7. 주의사항 / 하지 말 것

AGENTS.md5절: 실제 키/서명/무장/주문/홈 쓰기/거래소·데이터 API/QUANTGEN 변경 금지. 테스트19개 KEYLESS·임시 TRADEGEN_HOME, Cloud Python3.13 venv. 기존 localhost 검사에만 네트워크 권한. 파일명별stage, CRLF 보존, 기존 LEDGER행 불변. 동률만으로 하한 위반을 만들지 않고 목표 수익률을 위험예산으로 바꾸지 않습니다.

## 8. 소유자 실행 및 미완료 입력

이번 PR #6/#7 승인은 처리했습니다. 실제 signer는 소유자의 검토된 환경에서만 실행합니다. 조회 가능·계좌 증거 완전성·코드 서명·세션 활성화·전략 유효성은 각각 별개입니다. 첫날/전날 수익0인 날의 미지정 예산·측정/현금흐름 관례를 임의로 정하지 않습니다. 소프트웨어 구현을 실제 거래나 수익 목표 달성으로 표현하지 않습니다.

## 9. 이어받는 에이전트에게

현재 GPT 작업 중입니다. 새 사용자 지시 없이 중복 작업하지 마세요. 돌아받으면 CURRENT와 LEDGER 및 결과/검증 기록을 먼저 읽으세요. 연구가 통과0개인 사실을 숨기거나 같은 후속 구간을 보며 우승자가 나올 때까지 튜닝하지 마세요. 누락된 실제 계좌 설정/collector/서명/활성화와 새 전략의 live feasibility를 구분해 이어갑니다.

## 10. 확인 방법

연구 `results/summary.json`, `selection_registry.json`, 전체 `candidates_all.csv`, `run_manifest.json`에 고정 커밋/해시·전체 후보·선택·비용/지연 스트레스·다중검정 결과가 있습니다. 연구35개 검사는 평가 전 통과했습니다. accounts42개·control140개 PASS, full 검사는 아직 pending이며 이전 E2/E3 기준은1715/1837 PASS,0 FAIL,122 기존 NOT_RUN입니다.
