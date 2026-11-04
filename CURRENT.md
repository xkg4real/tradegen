---
status: handoff
reason: usage_limit_weekly
from: claude
task: first-trade-foundation
cycle: 2026-11-03
done_ids: cloud-compat-1, cloud-compat-2, cloud-compat-3, odds-1, odds-2, odds-3, odds-4, odds-5, odds-6, odds-7, odds-8, odds-9, odds-10, odds-11, odds-12, odds-13, odds-14, odds-15, odds-16, odds-17, odds-18, odds-19, odds-final, odds-pr, spec-rev-3-3, policy-plan-1, policy-preview-1, policy-pr, e1-1, e1-2, e1-3, e1-4, e1-5, e1-6, e1-7, e1-8, e1-9, e1-10, e1-11, e1-12, e1-13, e1-pr, e2-1, e2-2, e3-1, e3-2, e3-3, e2-3, e3-4, e2-e3-pr, pr6-pr7-merge, research-preregister-1, research-evaluate-1, account-readiness-1, research-paper-1, account-provider-1, account-regression-1, account-research-pr, pr8-human-code-review-approval, pr8-merge, launch-network-1, launch-collector-1, launch-profile-1, launch-strategy-1, launch-runner-1, launch-program-2, launch-workflow-2, launch-baseline-2, launch-quotes-2, launch-deployment-2, launch-review-request-2, launch-driver-2, launch-review-auth-2, launch-baseline-integration-2, launch-market-protocol-1, launch-recovery-cutoff-1, kis-live-contract-1, kis-live-backend-1, kis-live-ui-1, launch-static-guard-1, launch-windows-design-1, kis-live-regression-1, launch-regression-1, launch-delivery-1, pr9-owner-review, launch-windows-inputs-1, launch-owner-authority-1, launch-live-evidence, launch-live-history-1, launch-windows-coordinator-1, launch-study-module-1, okx-data-1, final-review-1, pr10-owner-review, venues-upbit-terms, pr11-owner-review
next_ids: e1-14-owner-setup, launch-prospective-study
updated_at: 2026-11-05T03:33:31+09:00
stale_after_hours: 3
waiting_on: owner Step D and code-approve on 06d0674, owner approve --kind venues for the new venues.yaml, prospective evidence
work_branch: main
work_commit: 06d06740cb1d275cd981e5750a212725ac21efbc
uncommitted_changes: none
pr: https://github.com/xkg4real/tradegen/pull/11 (merged by the owner 2026-11-05 03:29 KST as 06d0674, tree identical to 6e3adb5; PR 10 merged 02:24 KST as a5edaf4)
usage_weekly_pct: 95
usage_source: Claude Code desktop usage card (Weekly, all models)
handoff_threshold_pct: 95
usage_5h_pct: unknown
usage_resets_at: 2026-11-10T16:59:59+09:00
session: Claude Code desktop (TRADEGEN, Windows)
---

# 인수인계: Windows 첫 거래 어댑터, 전향 연구 모듈, OKX 시세 전환

## 0. 사용자에게 전달할 최신 상태

2026-11-05 추가: https://github.com/xkg4real/tradegen/pull/11(`claude/venues-upbit-terms`, `6e3adb5`)을 소유자가 03:29 KST에 merge commit `06d0674`(트리는 `6e3adb5`와 같음)로 병합했습니다. 이 PR에서 `core/odds/venues.yaml`의 Upbit 블록에 `lot` 0.00000001(소수점 8자리)과 `fee_extras` 0/0(주문당 고정 원화 요금 없음)을 Upbit 개발자 문서를 근거로 넣었습니다. 근거와 한계는 `research_notes/Korean resident trading venue legality/upbit_order_terms.md`에 있습니다. 8자리는 KRW-BTC 예시 두 곳(주문 FAQ의 시장가 매수, 지정가 매수 안내의 샘플 코드)에서만 나오고 규칙으로 명시되지 않았으며, 고정 요금 0은 수수료가 비율 필드로만 제시된다는 점에서 읽은 값입니다. 서명 대상 코드는 바뀌지 않아 코드 해시가 main과 같습니다(`5acd2bcc...`). 소유자는 병합 뒤 `approve --kind venues`만 다시 하면 됩니다(sha256 `283c143f...`에서 `5d966ef1...`로 바뀜). 검사(KEYLESS): compliance 345/347, odds 287/287, 전체 2202/2327(실패 2건은 `.venv` 위치 검사, NOT_RUN 123). 출처와 코드 두 관점의 반박 검증에서 값은 반박되지 않았고, 코드 관점이 찾은 `tests/odds_pipeline.py`의 기대값 변경을 같은 커밋에 넣었습니다. 주간 사용량이 95%라 status를 handoff로 둡니다.

소유자의 2026-11-05 Step C 결과(포크 세션이 전달): `tables, owner log and code signature: OK`, owner log head #5, rules·instruments·venues 초안이 효력 중(`74894f05e0b7f1af`, `50fa819f62707eb5`, `283c143f800b7ddc`), calendar 미서명(암호화폐만), exit 0. 즉 표 승인과 한도 서명은 끝났고, venues 승인은 PR11 이전 파일입니다. 남은 소유자 차례는 Step D(`TRADEGEN_PR9`를 `06d0674`로 전환하고 `code-approve`, 코드 해시 `5acd2bcc...`는 `a5edaf4`와 같음)와 새 venues.yaml(`5d966ef1...`)의 `approve --kind venues`입니다. 그 사이 Step C는 `venues: the draft 5d966ef1639d5da2 is not the version in force (283c143f800b7ddc)`와 `venue upbit: fee_extras, lot, odds_sources changed`를 보이며, 이 줄은 exit 코드에 영향이 없습니다. 소유자가 venues.yaml의 UNVERIFIED 4개 항목을 실제로 확인했는지는 안내서로 물었고 답은 아직 없습니다.

`claude/windows-first-trade`(`c11f516`)를 담은 https://github.com/xkg4real/tradegen/pull/10을 소유자가 2026-11-05 02:24 KST에 merge commit `a5edaf4`(부모 `d5ece51`, `c11f516`)로 병합했습니다. 그 트리는 `c11f516`과 같습니다. PR9(`gpt/first-trade-foundation`, `ab21116`)는 2026-11-04에 `d5ece51`로 병합됐고, 소유자의 서명은 `ab21116` 코드에 대한 것입니다.

GPT가 `ab21116`에 남긴 Windows 통합 설계의 남은 부분을 구현했습니다. 비공개 입력 로더, 현재 소유자 권한 조회, 계좌 구간 생성기와 독립 head, 실시간 이력, 코디네이터, 전향 연구 모듈입니다. 암호화폐 시세는 소유자 요청으로 Binance에서 OKX 공개 API로 옮겼고 Upbit는 그대로입니다. 네 관점(규칙, 런타임, OKX, 문서)의 최종 검토에서 나온 지적을 고쳤고, 수정마다 재검토 승인을 받았습니다.

전체 검사(Windows, KEYLESS, 오프라인): 2202/2327 PASS, 2 FAIL, 123 NOT_RUN(매크로 참조 자료 없음 121, POSIX 전용 2). 실패 2건은 checkout 밖의 venv로 돌려서 생긴 `.venv` 위치 검사입니다.

실제 계좌 연결, 이 PR 코드에 대한 서명, 세션 활성화, 주문, 검증된 전략은 아직 없습니다. 이 PR은 서명 대상 13개 파일을 바꿨으므로, 소유자가 병합된 트리에서 `code-approve`를 한 번 해야 서명 코드가 다시 유효해집니다.

병합 뒤 코드 대조와 두 차례 반박 검증으로 rehearsal조차 지금은 주문 단계에 갈 수 없다는 제한을 더 확인했습니다(6절 5번, 10-13번). Upbit 거래소 값이 없어 모든 Upbit 계획이 `NOT_TRADABLE`이고, instrument rules가 5분 뒤 만료되어 한 번의 실행에서 300초 배포 기간은 dry-run 주문도 낼 수 없으며, 어떤 정책 값으로도 수수료 여유를 둘 수 없습니다. PR10 본문의 "Limits the owner should know about"에도 같은 내용을 반영했습니다.

## 1. 확정한 운영 결정

- 2026-11-02 소유자가 `ab21116`에 `code_approved`를 서명했습니다(owner log #1). 표 승인과 `limit_set`은 코드 해시와 무관해서 병합 뒤에도 유지됩니다.
- 암호화폐 시세 출처는 OKX 공개 API(키 없음)이고 Upbit는 유지합니다(소유자 요청, 2026-11-03).
- 클라우드 세션은 쓰지 않습니다. 기능 브랜치와 PR로 올리고, 병합은 소유자가 PR마다 직접 승인할 때만 합니다.
- 실시간 틱 수집은 보류입니다. 소유자의 기준은 수익 확률과 엔진 성능을 높일 때만 만든다는 것입니다. 300초 봉의 비용 계산으로는 지금 필요하지 않다고 판단했고, 비교·감사 결과는 로컬에만 있습니다.

## 2. 근거

- 작업 브랜치의 `qa/acceptance_results.json`과 README 검사 표
- `docs/windows-first-trade-integration.md`, `docs/account-baseline-integration.md`
- `docs/launch-workflow.md`(전향 연구 절), `docs/first-trade-owner-checklist.md`, `docs/deployment-readiness.md`
- `docs/market-selection-protocol.md`, `docs/strategy-review-signing.md`
- PR 본문: 서명 대상 파일 목록, 소유자가 알아야 할 제한

## 3. 구현과 판단

- `execution_launch/private_input.py`: Windows 비공개 입력 로더입니다. Windows에서는 launch의 읽기 경로가 이 로더를 씁니다. POSIX 전용 검사 2개는 Windows에서 NOT_RUN이고, Windows 경우는 `tests/launch_private_input.py`가 다룹니다.
- `execution_control/owner_authority.py`: owner log와 공개키에서 현재 소유자 권한을 읽습니다. 임의의 Context나 receipt를 만들지 않습니다.
- `execution_launch/baseline_head.py`: 독립된 최신 head 기록입니다. compare-and-set은 체인에 이미 확정된 바로 다음 항목으로만 head를 옮깁니다.
- `execution_launch/account_interval.py`: Upbit 계좌 구간 생성기입니다. flat 계좌만 보증하므로 첫 체결 뒤에는 체인이 멈춥니다.
- `execution_launch/live_history.py`: 실시간 이력(`LiveHistory`) 저널, 슬롯과 계좌 앵커, 재시작 시 재생입니다. 슬롯 하나를 놓치면 그 배포 기간(window)의 이후 슬롯이 모두 끝납니다.
- `execution_launch/coordinator.py`: 코디네이터, 취소 가능한 스케줄러, `compose()`입니다. rehearsal 모드만 있고 `"controlled"`는 거부합니다.
- `execution_launch/study.py`: `freeze`, `capture`, `select`입니다. `plan.json`은 비공개이고 `commitment.json`은 `capture_start` 전에 공개합니다.
- OKX: `data/crypto/okx_public.py`, `core/odds/plan.py`, `core/odds/report.py`. OKX BTC 레그의 원화 가격은 OKX BTC-USDT 가격에 같은 UTC 날짜의 Upbit USDT 원화 가격을 곱한 값입니다.

코디네이터 타이밍 규칙(최종 검토 R12-R15):

- 슬롯 작업은 슬롯 시각보다 lead(`prefetch_lead_seconds`, 기본 3초)만큼 앞서 호가를 먼저 읽고, 그다음 계좌를 캡처합니다. 캡처 한도는 lead + 5.5초와, 10초에서 호가 타임스탬프 지연을 뺀 값 중 짧은 쪽입니다. 기본 lead에서 약 8.5초이고 10초를 넘지 않습니다.
- 배포 기간의 슬롯 중 하나라도 서울 자정이나 22:00 KST(회복 조건이 있을 때만)와 20초 이하로 떨어져 있으면 코디네이터 생성 단계에서 거부합니다. 그래서 배포 기간은 60초나 300초처럼 분 단위 봉으로, hh:mm:30처럼 초가 30인 시각에 시작합니다(hh:mm:30에서 90초 봉이면 슬롯이 하나 걸러 정각에 놓입니다). 10초 모니터에서 시작 시각 초의 끝자리가 3에서 8이면 경계 2-7초 전에 모니터가 걸립니다. 끝자리가 8이면 기본 1초 lead에서 그 모니터가 경계 단위보다 먼저 돌고, 그 캡처가 경계를 넘기면 경계를 확정하므로 체인이 경계를 지켜도 `status()`가 건너뛴 경계 단위를 놓쳤다고 셉니다. 2초 lead에서는 같은 시각의 경계 단위가 먼저 돌아 생기지 않으므로 이것이 R19의 비용입니다. 다만 서울 자정에는 PC 시계로 잰 관측이 자정 뒤인데 마지막 응답의 `Date` 헤더(`server_time`, Upbit 시계)가 자정 전인 캡처가 `SERVER_CLOCK_OR_SEOUL_DAY_MISMATCH`로 거부되므로, 두 시계가 맞을 때 끝자리 8은 요청당 약 20-45ms인 빠른 회선에서 두 lead 모두 경계를 실제로 놓칩니다. 3에서 7이면 그 모니터의 캡처가 경계 직전에 끝날 때 거부되며 경계 단위를 늦추고, 늦어진 경계 단위의 첫 응답이 경계 뒤에 오면 경계를 실제로 놓칩니다. 모든 응답 시간이 같으면 요청당 약 120-580ms 사이의 일부 시간대(끝자리 7이면 약 120-130ms, 자정에는 약 155ms까지)에서 이렇게 되고, 캡처마다 첫 응답만 느리면 제때 시작한 경계 단위가 허용하는 약 1초보다 짧아도(끝자리 7에서 나머지 응답이 30ms이면 첫 응답 약 0.5-0.9초) 이렇게 됩니다. 끝자리마다 그 시간대보다 느린 응답에서는 그 모니터가 경계를 확정해 8과 같은 잘못된 집계가 생깁니다. 3에서 7의 경우는 lead 1초와 예전 2초에서 같으며 R19 전부터 있었습니다. hh:mm:30 시작은 10초 모니터에서 이 모든 경우를 피합니다. 12초 모니터에서는 hh:mm:30 시작도 경계 6초 전에 모니터를 두므로 lead 1초와 2초 모두 두 경우가 남아, 요청당 약 420-464ms(자정에는 약 487ms까지)에서는 경계를 실제로 놓치고 그보다 느리면 잘못된 집계가 생깁니다. 6초 모니터(`prefetch_lead_seconds` 1에서만 허용)도 경계 6초 전에 모니터를 두어 두 경우가 모두 생깁니다. 수치는 가장 짧은 9요청 캡처 기준이며 캡처가 길면 낮아집니다.
- 자정 시계: 위의 자정 수치는 모두 PC 시계가 Upbit 시계와 맞을 때의 값이며, PC 시계가 앞서면 경계를 놓치는 응답 시간대가 넓어집니다. 기본 1초 lead에서 제때 시작한 경계 단위의 마지막 응답은 PC 시계로 자정 뒤 약 0.6초에 요청당 응답 시간의 9배를 더한 때(가장 짧은 캡처에서 20ms 회선이면 약 0.8초이고, 캡처가 길면 늘어납니다)에 오므로, PC 시계가 Upbit 시계보다 그 이상 앞서면 hh:mm:30 시작에서도 경계 단위가 같은 코드로 거부되고 다음 단위가 `ACCOUNT_INTERVAL_BOUNDARY_MISSED`로 거부되어 체인이 재앵커 전까지 멈춥니다. PC 시계가 앞서는 쪽은 `Date` 헤더와 비교하는 다른 서버 시각 검사가 60초까지 허용하고 호가 검사도 그 차이를 10초 한도 안의 호가 나이로만 세므로, 0.5초쯤 앞선 시계는 자정 전에는 드러나지 않습니다. 늦는 쪽은 자정 검사에 걸리지 않지만 자정과 상관없이 호가 검사에 걸립니다. `parse_orderbook`은 호가의 `timestamp`(Upbit 시계)가 PC 시계로 잰 수신 시각보다 뒤이면 `QUOTE_BOOK_STALE_OR_FUTURE`로 거부하므로(`execution_accounts/quotes.py:142`), PC 시계가 호가 타임스탬프 지연(Upbit가 호가에 시각을 찍은 때부터 PC가 응답을 받을 때까지, 아직 실제로 재지 않았습니다)보다 더 늦으면 호가 읽기가 거부됩니다. 예를 들어 지연이 20ms이면 PC 시계가 0.02초 넘게 늦을 때 거부됩니다. 코디네이터에서는 그 슬롯을 잃고 `LiveHistory`에서는 창의 나머지 슬롯도 모두 끝나며, 호가를 읽는 운영자 청산(`submit_exit`)도 같은 코드로 거부됩니다. 전향 연구 캡처에서는 창 전 확인 읽기가 `STUDY_PREWINDOW_PROBE_FAILED`로 거부되거나 창 안의 첫 거부로 시행이 끝납니다. 시작 단위는 호가를 읽지 않으므로 어느 쪽도 미리 경고하지 않습니다. 그래서 PC 시계는 Upbit 시계보다 0.5초 넘게 앞서지도, 호가 타임스탬프 지연보다 더 늦지도 않게 맞춰 둡니다(6절 9번). 창이 도는 중에 시계를 맞추면 시계가 뒤로 갈 수 있고, 그동안의 계좌 읽기나 슬롯은 `COLLECTOR_RECEIPT_CLOCK_REGRESSED`, `COORDINATOR_CLOCK_ROLLBACK` 등으로 거부되므로, 동기화는 단위가 쉬는 때(hh:mm:30 시작과 10초 모니터라면 매분 45초쯤)에 하고 22:00과 자정 앞뒤 5분은 피합니다. 2초 lead에서는 경계 단위가 경계 2초 전에 시작해 끝자리 8의 모니터와 같아지므로, 시계가 맞아도 hh:mm:30 시작이 22:00에서는 요청당 약 22ms 미만, 자정에서는 약 45ms 미만에서 경계를 놓칩니다. R19가 lead를 1초로 바꾼 이유입니다.
- `monitor_seconds`는 `bar_seconds`의 약수이고 lead + 5 이상, 20 이하여야 합니다. lead 3이면 60초 봉과 300초 봉 모두 10, 12, 15, 20입니다. 그래도 기본값 10초를 유지합니다. 모든 캡처는 마지막 확정 구간 끝에서 30초 안에 관측해야 하므로, 캡처가 한 번 실패하면 공백이 10초 간격에서는 20초, 15초에서는 30초, 20초에서는 40초가 되고, 30초를 넘으면 체인이 멈춥니다(R21).
- `run()`을 첫 슬롯의 호가 사전 읽기(prefetch) 15초 전보다 늦게 시작하면 거부합니다. 체크포인트를 읽을 때마다 체인의 `recovery_cutoff_seconds`와 프로필의 회복 조건이 둘 다 있거나 둘 다 없는지 검사하고, 어긋나면 `COORDINATOR_CUTOFF_MISMATCH`로 거부합니다.

## 4. 검증 완료

- 최종 트리 전체 검사: `bf21494`(그 뒤 커밋은 문서, README 표, QA 기록만 바꿉니다)에서 2202/2327 PASS, 2 FAIL(venv 위치 검사), 123 NOT_RUN(매크로 121, POSIX 전용 2)입니다. README 표와 QA 기록을 읽는 모듈은 최종 트리에서 다시 돌려 158개 중 148 PASS, 같은 venv 검사 1 FAIL, 매크로 9 NOT_RUN이었습니다. 변이 검사: 자정 신선도(R17)는 수정과 동등하지 않은 모든 변이가 최소 한 테스트에서 실패하고, 경계 lead(R19)는 기본값을 2초로 되돌리면 R19 테스트 4개만 실패합니다(나머지 코디네이터 테스트 31개 통과).
- 같은 Windows PC에서 `ab21116`은 2050/2199 PASS, 28 FAIL, 121 NOT_RUN이었습니다. Windows 실패 26건(cp949 디코딩, POSIX 전용 파일 검사, kis_live UI의 소켓 가드)을 고쳤고, 남은 2건은 venv 위치 검사입니다.
- 서명 대상 closure는 67개에서 74개 파일이 됐습니다. 추가 7개, 변경 6개, 삭제 0개이고 `driver._SOURCE_FILES`의 파일은 바뀌지 않았습니다.
- 서명된 표, `tools/signer/sign.py`, 고정 파일(`data/crypto/crypto_client.py`, `data/net.py`), 동결 연구는 `ab21116`과 같습니다.
- 최종 검토: 배치 A(코디네이터 타이밍)는 수정 라운드 한 번 뒤 승인됐습니다. 배치 B(OKX와 가드)는 재검토의 F4 지적을 고친 뒤 확정했습니다. 배치 C(문서)는 수정 라운드와 재검토를 거쳤고, 재검토에 남은 사소한 지적 1건(경계마다 생기는 일시 거부 횟수)은 최종 문서 패치에서 고쳤습니다. 그 뒤 문서 사실 검사를 찾기와 반박 검증으로 9차까지 돌렸습니다. 실제 문제로 확인된 것은 2-3차 26건, 4차 13건 중 10건(PC 시계가 앞서면 자정 경계를 놓침), 5차 11건 중 10건(PC 시계가 늦으면 호가 검사에 걸림), 6차 7건, 7차 8건 중 7건(지연 측정은 `freeze` 전에, 한국어 크기 표현), 8차 8건(`code-approve`는 병합 직후, 연구 캡처 재시작 규칙), 9차 1건(재시작 예외와 일반 시작 규칙의 충돌)이고 모두 반영했습니다.

## 5. 발견·수정한 실패

- 코디네이터: 계좌 캡처가 길어지면 호가가 늦게 도착해 슬롯을 잃던 순서를 바꿨습니다(R12). 경계 근처 슬롯, 어긋난 모니터 위상, 늦은 시작, cutoff 불일치는 생성이나 시작 시점에 거부합니다(R13-R15).
- 배치 A 재검토 지적: 늦은 호가 규칙과 `_started` 잠금의 테스트를 넣었고, 20초 경계의 양끝, 캡처 한도 문구, 체크포인트를 읽을 때마다 하는 cutoff 검사를 고쳤습니다.
- OKX: 오류 메시지에 OKX의 숫자 코드만 싣고 OKX 응답 원문은 싣지 않습니다.
- 정적 가드: `os.open`의 flags 인자로 쓰인 이름이 단순 대입이 아닌 방식(매개변수, import, `for`·`with`·`except` 대상 등)으로 한 번이라도 묶이면, `os.O_*` 비트만 담는다고 증명되지 않으므로 쓰기로 판정합니다(F4).
- Windows 예시 작성기는 `%LOCALAPPDATA%` 아래에만 씁니다. `requires-python >= 3.13`을 선언했습니다.
- 자정 경계: 자정을 감싸는 계좌 캡처도 마지막 확정 구간 끝에서 30초 안에 관측해야 합니다. 30초가 넘는 공백은 자정에도 메워지지 않고, 계좌 체인은 검토를 거친 새 앵커에서 다시 시작해야만(re-anchor) 복구됩니다(R17).
- 앵커 시각: 새 앵커의 `asof`는 그 앵커를 만든 계좌 읽기의 관측 시각입니다. 코디네이터의 첫 캡처(시작 단위)도 그 시각에서 30초 안에 관측해야 하므로, 앵커 값은 미리 검토해 두고 앵커 읽기, `initialize_account_baseline`, `store.seed`, `initialize_reviewed_head`, `run()`을 한 스크립트에서 연달아 실행해야 합니다. 늦으면 `EVIDENCE_STALE_OR_FUTURE`로 새 체인이 바로 멈춥니다. 30초 안이어도 첫 캡처의 첫 잔고 읽기 전에 서울 자정이나 대기 중인 22:00 KST 마감이 지나면 `ACCOUNT_INTERVAL_BOUNDARY_MISSED`로 똑같이 멈추므로, 앵커 읽기는 자정과 22:00 직전 1분 안에는 하지 않습니다. 앵커마다 `BaselineConventions.max_interval_seconds`는 30 이상으로 둡니다. 더 작으면 계좌 읽기 사이의 30초 한도가 모두 그 값으로 줄어, 30초 안이어도 그 값보다 긴 구간은 `BASELINE_BRIDGE_EVIDENCE_REFUSED`로 거부되고 체인이 똑같이 멈춥니다. 더 크게 둬도 30초 한도는 늘지 않습니다. 처음 설정(e1-14-owner-setup)과 재앵커 모두 해당하며, 이 순서를 실행하는 명령은 아직 없습니다.
- 경계 캡처: 기본 lead를 2초에서 1초로 바꿨습니다. 요청마다 0.2초를 쉬므로 가장 짧은 캡처(요청 9개)도 1.8초 이상 걸려 경계를 넘깁니다. 첫 응답이 약 1초보다 늦거나 첫 요청을 재시도하면 경계를 놓칩니다(R19).
- 코디네이터 테스트: 호가 읽기 실패는 `account` 단계가 아닌 `quote` 단계의 거부여서 `reasons`에만 남습니다. cutoff가 어긋난 체인에서 운영자의 취소와 청산은 `COORDINATOR_CUTOFF_MISMATCH`로 거부되고 아무것도 커밋하지 않습니다(N1, N3).

## 6. 남은 개발과 실제 운영

1. 이 PR의 소유자 검토와 병합: 2026-11-05에 `a5edaf4`로 완료(PR9는 2026-11-04).
2. 병합된 트리에서 `code-approve` 한 번(소유자 차례).
3. 전향 연구: 300초 간격 2,016회 관측(약 7일)의 빈틈없는 캡처, 최소 20회 왕복, 비용을 뺀 유의성 검정이 필요합니다. 첫 거부나 놓친 슬롯이 그 시행을 끝냅니다. 2026-11-20 전 통과는 현실적이지 않습니다.
4. flat 전용 생성기라 첫 체결 뒤 체인이 멈춥니다. 보유 포지션을 증명하려면 소유자 결정(연속 가격 기록 또는 수동 청산)이 필요합니다.
5. `drawdown_activation_equity` 아래에서는 보호 하한이 최고점과 같아서 첫 수수료나 손실이 신규 진입을 영구 정지(halt)시킵니다. 지금 코드에서는 어떤 정책 값으로도 수수료 여유를 둘 수 없습니다. 위험 하한은 `initial_equity` 아래로 내려가지 않고(`execution_control/risk.py:206`, `:274-275`), 고정 driver는 첫 슬롯에서 KRW 현금이 `initial_equity`와 정확히 같기를 요구하며(`FIXED_DRIVER_INITIAL_STATE_INVALID`, `execution_launch/driver.py:326-328`), 서명한 `total_loss_floor_krw`가 현금과 같으면 첫 투입액이 0이라 `STUCK_AT_START`입니다(`core/odds/costs.py:357-359`, `core/odds/simulate.py:441-444`). 여유를 두려면 소유자의 위험 결정과 서명된 코드 변경이 함께 필요합니다.
6. `kr_rules.yaml`의 가장 이른 `review_by`는 2026-11-22입니다. Upbit KRW 현물 행 `KR-DOMESTIC-SPOT`과 OKX 행을 포함한 25개 행이 이 날짜이고, 나머지 22개 행은 2026-11-23입니다. `review_by`가 지난 행은 그 행에 걸리는 신규 진입을 막고, 청산은 막지 않습니다.
7. `AuthenticatedTransport`를 쓰는 controlled 배포는 나중에 따로 승인받을 단계입니다.
8. 앵커의 `asof`부터 재는 30초는 `run()` 호출이 아니라 `run()` 안에서 도는 시작 단위 캡처의 관측에서 끝납니다. 이 캡처는 가장 짧아도 요청 9개라 응답 시간에 더해 1.8초가 걸리고 재시도 한 번마다 2.2초가 더 걸리므로, `run()`은 그만큼 더 일찍 불러야 합니다. 앵커 읽기, `initialize_account_baseline`, `store.seed`, `initialize_reviewed_head`, `run()`을 이렇게 연달아 실행하는 명령이 없어 소유자가 스크립트를 직접 써야 합니다. 서명 대상 코드를 바꾸는 일이므로 소유자 결정 뒤 별도 PR로 다룰 후보입니다.
9. 300초 실캡처 전에 PC 시계가 계속 동기화되는지(계좌 캡처는 서울 자정의 날짜 검사 때문에 Upbit 시계보다 0.5초 넘게 앞서면 안 되고, 호가 읽기는 `QUOTE_BOOK_STALE_OR_FUTURE` 검사 때문에 PC 시계가 호가 타임스탬프 지연보다 더 늦으면 안 됩니다. 호가만 읽는 전향 연구 캡처에는 자정 날짜 검사가 없고 호가 검사가 걸리며, 첫 거부가 시행을 끝냅니다. 이 지연은 7일 연구 계획의 `freeze` 전에 실제 Upbit 호가에서 재야 하고(지연에는 소유자 회선이 들어가므로 소유자 PC에서 재며, 저장소에 측정 명령은 아직 없습니다), 100분의 몇 초(수십 ms) 이하로 짧으면 Windows 시계를 7일 내내 그만큼 맞춰 둔다고 장담할 수 없으므로 늦는 쪽 허용 폭을 서명된 코드로 둘지도 그 전에 소유자가 정합니다. 허용 폭은 `execution_accounts/quotes.py:142`의 검사를 바꾸는데, 이 파일은 `code-approve`가 서명하는 코드 해시에 들어 허용 폭을 넣으면 그 변경을 병합한 뒤 `code-approve`를 다시 해야 하고, `freeze`가 digest로 묶는 `CAPTURE_FILES`(`execution_launch/study.py:59`)에도 들어 그 digest가 `commitment.json`에 공개되므로, 바꾸기 전에 고정한 계획은 `capture`에서 `STUDY_CAPTURE_SOURCE_CHANGED`로 거부되고 이미 공개한 `commitment.json`도 쓸 수 없게 됩니다), 프록시 없이 인터넷에 직접 연결되는지, 인증서를 바꿔 끼우는 HTTPS 검사 백신이 없는지, Upbit 응답 형식 가정이 실제와 맞는지 확인해야 합니다. 감사에서 나온 항목이며 아직 검증하지 않았습니다.
10. PR11이 `core/odds/venues.yaml`에 Upbit `lot`과 `fee_extras`를 넣었습니다(2026-11-05 `06d0674`로 병합, 소유자 승인 전). 승인 전까지는 모든 Upbit 계획이 `NOT_TRADABLE`로 거부되고(`core/odds/costs.py:76-87`), 세션 준비도 멈춥니다(`execution_control/session.py:80-82`). 병합과 소유자의 `approve --kind venues` 뒤에는 Upbit 계획이 비용 계산을 통과하고, 서명 하한이 현금과 같으면 다음 거부는 `STUCK_AT_START`입니다(5번). 이 표는 코드 해시 밖이라 `code-approve`는 필요 없고, 새 승인은 state hash를 바꾸므로 그 전에 준비한 세션은 다시 준비해야 합니다. 실주문은 프로필 instrument rules의 lot, tick, 최소 금액, 수수료를 쓰며 venues.yaml과 맞는지 확인하는 코드는 없습니다. odds 시뮬레이션의 `floor_units`(`core/odds/costs.py:281-288`, 고정 허용오차 1e-9)는 1e-8 lot에서 5,000원 근처 USDT 스테이크를 한 lot 줄여 bold 베팅을 0으로 만들 수 있습니다(과소 베팅 쪽, 시뮬레이션 한정, 고치려면 서명 코드 변경). 같은 파일의 UNVERIFIED 항목 4개(Upbit와 OKX의 BTC 입금 네트워크, Korbit과 OKX의 `source`)는 그대로 소유자 확인 대상입니다(PR11 파일 기준 27-28, 53, 59-61행).
11. 프로필의 instrument rules는 `asof`부터 5분만 유효하고(`execution_launch/profile.py:366-367`, `execution_control/controller.py:596-597`), 이를 Upbit에서 읽거나 갱신하는 코드가 없으며, 실행 중에는 프로필을 바꿀 수 없습니다(`RUNNER_PROFILE_MUTATED`). 고정 driver는 첫 슬롯에서 주문하지 않고(`execution_launch/driver.py:276-278`), 이동평균 프로그램은 이전 표시가 `slow_window`(2 이상)개 쌓일 때까지 현금을 유지하므로(`execution_launch/program.py:63`, `:139-140`) 첫 주문은 빨라야 세 번째 슬롯입니다. 300초 봉에서는 그 슬롯이 600초 뒤라 규칙이 이미 만료되어, 프로그램을 한 번 실행하는 동안 300초 배포 기간은 dry-run 주문조차 낼 수 없습니다. `asof`는 `profile_contract_digest`에 들지 않으므로(`execution_launch/profile.py:299-311`) 규칙을 다시 읽어 슬롯 사이에 재시작하면 같은 배포 기간에서 새 5분이 시작되지만, 첫 캡처가 마지막 확정 구간 끝에서 30초 안에 와야 하고 이를 해 주는 명령은 없습니다. 실시간 규칙 갱신은 별도의 서명 코드 변경입니다.
12. `study select`는 신뢰할 수 있는 검토를 연결하지 않으므로(`review_verifier=None`, `execution_launch/study.py:597`) 항상 `NO_QUALIFIED_MARKET`을 보고합니다. 수치를 통과한 후보마다 출력 JSON 한 줄의 `review_requests`에 검토 요청을 싣고 파일은 쓰지 않습니다. 서명한 검토는 `compose()`가 형식만 읽고, `prepare_launch_session`과 매 `Runner.tick`이 `ReviewVerifiers.source`로 인증합니다(`execution_launch/review_auth.py:228-243`).
13. 계좌 수집기는 `UPBIT_ACCESS_KEY`, `UPBIT_SECRET_KEY` 이름과, 상태 폴더와 같은 절대 경로의 `TRADEGEN_HOME`이 프로세스 환경에 있어야 하고 `.env`로는 안 됩니다(`execution_accounts/upbit_collector.py:55-63`). rehearsal은 `~/.tradegen` 밖의 상태 폴더를 요구하고(`execution_launch/runner.py:252-255`) owner log, 승인, 한도를 그 폴더에서 읽으므로, 소유자가 `~/.tradegen`에 서명한 상태를 rehearsal에 쓰는 방법은 아직 정해지지 않았습니다. 서명기와 `--check`도 `TRADEGEN_HOME`을 따르므로 소유자 안내서는 그 창에서 서명하지 말라고 적었습니다.

## 7. 제한

AGENTS.md 5절을 지킵니다. 실제 키, `.env` 값, 소유자 비공개 로그를 읽거나 쓰지 않고, 실제 API 호출, 서명, 활성화, 주문을 하지 않습니다. QUANTGEN과 동결 연구를 수정하지 않습니다. 소유자 PC에 아무것도 설치하지 않습니다. CRLF를 보존합니다. PR마다 소유자 승인 없이는 병합하지 않습니다. 서브에이전트는 push하지 않습니다.

## 8. 소유자 절차

PR10 병합 완료(2026-11-05, `a5edaf4`) → 병합된 트리에서 `code-approve` → `freeze` 전에 실제 Upbit 호가 타임스탬프 지연 측정과 늦는 쪽 허용 폭 결정(6절 9번. 지연에는 소유자 회선이 들어가므로 소유자 PC에서 재며, 7절에 따라 에이전트는 직접 호출하지 않습니다. 저장소에 측정 명령은 아직 없습니다. 허용 폭을 넣는다면 그 변경을 병합하고 `code-approve`를 다시 합니다) → 필요하면 한도 서명(다음 서울 날짜부터 효력) → 전향 연구 `freeze`와 `commitment.json` 공개 → 약 7일 `capture` → `select` → 신뢰할 수 있는 검토와 `review-approve` → rehearsal 배포 기간 순서입니다. rehearsal 전에 새 venues.yaml의 `approve --kind venues`(6절 10번, PR11은 병합됨)가 필요하고, 6절 11번 때문에 300초 배포 기간은 지금 코드로는 한 번의 실행으로 주문 단계에 가지 못합니다. 비밀값은 본인 PC 터미널에만 입력하고 채팅에 쓰지 않습니다.

## 9. 다음 에이전트가 이어받을 지시

CURRENT, LEDGER, 위 근거와 PR 본문을 읽고 소스를 확인합니다. 끝난 ID는 반복하지 않습니다. 확정된 결정을 다시 묻지 않습니다. 실제 증거, 서명, 계좌 설정이 있다고 가정하지 않습니다. 동결 연구를 미래 검증 자료로 대신하지 않습니다. PR마다 소유자의 병합 승인이 따로 필요하고, PR8 승인을 재사용하지 않습니다.

## 10. 로컬 검사와 비공개 자료

전체 로그, 검토 보고서, 수정 기록, 틱과 300초 감사 결과는 이 PC의 비공개 scratch에만 있고 Git에 올리지 않았습니다. 소유자 안내서는 세션에서 소유자에게 직접 전달했습니다. 공개 QA JSON의 실패 메시지 한 건은 로컬 venv 경로를 중립 문구로 바꿨습니다.

## 실제 확률

검증된 우위가 없으므로 목표 도달 확률은 사실상 0입니다. 기한 안에 목표에 닿으려면 매일 수십 퍼센트의 수익이 필요합니다. 이 문서는 법률, 세무, 투자 자문이 아니며 작성자는 면허가 있는 자문가가 아닙니다.
