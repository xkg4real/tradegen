# I3d 이후: 출처와 확정 계좌 공개의 최소 후속 단위

작성 2026-11-13. 읽기 기준은 `/workspace/tradegen-committed-runner-1113`의 `f3d9a53` 및 개발 중 I3d 소스다. 코드·테스트·네트워크·실계좌 실행 없이 조사했다. I3a 원본 재현, I3b 전체 capture 보관, I3c 완료 시각 검증, I3d committed 계좌 소비를 다시 구현하는 계획이 아니다. 사용량은 `usage_weekly_pct: unknown`, `usage_source: unavailable`이다.

**결론:** 현재 Upbit 자료만으로 생산 `VerifiedCoverage`를 발급할 근거는 없다. 다음 독립 구현은 실제 E1 조회 호출의 원문·실패 기록을 기존 보관소에 남기는 작은 수집 연결이 적합하다. 그와 별개로 guard commit 뒤에만 같은 provider에 새 계좌를 공개하는 연결은 모의 환경에서 구현·검증할 수 있다. 둘 중 하나를 끝냈다는 이유로 production source gate를 열지 않는다.

## 현재 요구와 실제 증거

| 근거 | 실제 입증 범위 | 입증하지 못하는 것 |
|---|---|---|
| `execution_accounts/upbit_collector.py:38`, `E1UpbitSource.fetch` | 명시 환경·상태 경로와 E1 허용 GET, 실제 응답 bytes/시각/hash. E1은 지정 HTTPS 호스트·redirect 금지·검토된 routing을 사용 | credential이 특정 소유자/main pocket에 대응함, 응답 외 전체 역사/계좌 변화가 완전함 |
| `collector.py:78` SourceReceipt, `upbit_collector.py:346` collect_upbit | 원문 exact decode, 요청 path/params/scope 일치, 실제 페이지/주문 상세·체결·수수료·잔고 식 대조, 반복 조회 | 반복 전후 값이 같은 ABA 변화 부재, 무제한 retention, 모든 flow 종류, 원자적 계좌 snapshot |
| `collector.py:113` CoverageEvidence, `_validate_proofs` | origin·history·capture fence의 선언 형식/기간 검사 | `reviewed-*` 문자열이나 문서 hash 자체가 독립 인증이라는 주장 |
| `continuous.py:1–13,281`, `docs/continuous-price-candidates.md` | exact 후보에 결합된 별도 verifier 결과 요구, local gap/중복/시각 검증 | 로컬 순번·heartbeat·trade ID·잔고/호가 snapshot만으로 remote 누락 부재 인증 |
| `guard_capture_material.py:237`, `guard_capture_archive.py:251` | 같은 원문으로 재수집/계산 재현, 전체 packet의 raw 보관·백업·독립 head·재읽기 | source 진위, 현재 owner/coverage 승인. 이미 받은 원문도 `collect()`가 실패하면 이 완성-packet wrapper까지 오지 못함 |
| `continuous_guard_commit.py:314`, `committed_account.py:242` | 실제 PREPARE→필요 halt→baseline/head→guard/head→COMPLETE와 동일 package 재개, actual committed pair 재읽기 | source/owner claim의 최초 진위 발급, 새 interval의 자동 게시 |

현재 클래스명은 `E1UpbitSource`다. 이 checkout에는 `E1UpbitCaptureSource`라는 클래스가 없다. 후속 명칭을 이미 구현된 것으로 기록하지 않는다.

현재 coverage 계약은 **받은 표본을 모두 보존했다는 계약보다 강하다.** opening marks, 관련 가격 변화와 fills, 공통 순서, closing watermark, 누락된 계좌 변화의 부재를 요구한다. 대상은 지원하는 계좌의 평가 경로이며 전 세계 모든 시장 tick을 뜻하지 않는다. 그러나 유한 표본의 최저·최고값을 구한 것만으로 수집 사이에 더 낮은 가격이 없었다고 할 수 없다는 요구는 기존 명세에 명시돼 있다. 이것을 관측 표본 기준으로 조용히 바꾸지 않는다. 가격 수신을 완벽하게 해도 주문 지연·gap·체결 가격 때문에 원금/수익/손실 하한의 실제 달성은 보장되지 않는다.

## 입력 없이 진행할 작은 순서

### 1. 실제 조회 batch 보관 — 권장 다음 단위

가칭 `execution_launch/upbit_read_archive.py`의 `collect_retained_upbit_batch(source, *, store, anchor, coverage, risk_baseline, clock, trade_fees=(), limits=...)`가 **실제 E1UpbitSource와 실제 collect_upbit**를 연결한다. `BundleStore`의 RAW_ARCHIVED/object/backup/head를 재사용하고 새 저장 엔진이나 승인 registry를 만들지 않는다. storage roots는 명시 인자이며 실제 사용자 홈을 기본값으로 잡지 않는다.

- 조회 ordinal, path/ordered params, 호출/완료 시각, 실제 받은 원문 hash/길이, 고정 성공·실패 종류를 기록한다. 동일 bytes의 여러 조회도 각각의 observation을 남긴다. 값·계좌 경로·응답 본문을 공개 진단에 출력하지 않는다.
- 호출 자체가 실제 E1 경로를 거쳤다는 로컬 사실과 credential/account identity·remote completeness를 분리한다. 직접 구성한 SourceReceipt나 서명으로 네트워크 출처를 승격하지 않는다.
- `execution/transport.py:98–163`은 GET 재시도 및 실패 응답 처리를 내부에서 수행한다. 바깥 fetch 한 번은 HTTP attempt 한 번과 같지 않다. 최소 호출 단위 기록이라면 이를 정확히 표시하고, 모든 실제 응답을 보존하려면 `_send` 반환 직후/`_check_answer` 이전의 **허용 GET 전용** 좁은 수집 seam을 추가한다. headers·JWT·키·임의 예외 문자열은 기록하지 않는다. 실제로 받지 못한 body는 unknown으로 남긴다.
- 완성된 연구/capture만 보관하지 않는다. 반환된 원문은 의미 검사 실패에도 보존하고 중단·수집 실패는 미완료 batch다. 기존 BundleStore의 immutable raw 부분 기록을 재사용해 순번별 기록과 최종 inventory를 구분한다. 최종 inventory가 없으면 완전 batch라고 소비하지 않는다. 새 publisher나 coverage 증거로 사용하지 않는다.
- 제한 초과를 미리 거절하고 quota/write/readback 실패 시 다음 조회·운영 공개를 중단한다. 저장하지 못한 자료를 저장됐다고 하거나 정상 호가를 None으로 치환하지 않는다. capacity 사전 점검은 미래 디스크 공간의 보장이 아니다.

검증: actual E1 경로의 허용 transport만 합성으로 대체하여 순서·raw bytes·중복 observation·중간 실패·잘못된 JSON·retry 관찰 범위를 검사한다. old successful batch를 실패한 새 batch의 결과로 재사용하지 않음, 한도 이전 중단, final inventory 누락/부분 저장/백업 실패 거절, no order/key/header export를 검사한다. 이 단계의 출력은 보관 사실이며 `source_authenticated`, `coverage_verified`, `execution_ready`는 모두 false다. E1 read authentication의 기존 의미를 약화하지 않는다.

### 2. full guard package 보관→commit→공개 — 모의 환경에서 개발 가능

I3b packet에는 pre/post owner의 실제 관찰, risk policy, guard/control predecessor의 완전한 게시 transaction이 없다. 원 packet을 덮어쓰지 않고 packet digest에 결합한 별도 제한된 publication 문서에 이를 보관한다. 실제 owner 관찰은 시작 전과 source 검증 후에 수행하며 기존 코드/head/효력 한도/날짜/세션과 원 시각을 보존한다. 출처 검증의 미구현 부분을 임의 boolean이나 기본 verifier로 채우지 않는다.

실제 `commit_continuous_guard`를 그대로 사용하고 COMPLETE·두 checkpoint/head·현재 Journal prefix의 재읽기가 성공한 뒤에만 공개한다. 원 package를 exact 보관하므로 중단 후에는 같은 transaction/package만 재개하며, commit 성공 후 response loss도 실제 durable state로 판정한다. 새 seed/head adoption·이중 baseline advance·floor/halt 리셋은 없다.

현재 `CommittedAccountProvider`는 한 package/receipt를 생성 시 고정하고 Controller/Runner는 같은 provider identity를 요구한다. interval마다 새 provider를 바꾸는 것으로 해결할 수 없다. 필요한 작은 변경은 **기존 provider의 동일 identity 안에서 actual completed package만 원자적으로 설치하는 private 게시 경계**다. 읽기는 실제 transaction/head 검증을 유지하고 게시 중에는 이전 자료를 새 시각으로 사용하지 않는다. `Coordinator._publish`(565)는 아직 board.publish→ContinuousAccountProvider의 baseline advance 경로이므로 새 committed 경로에서 이 옛 advance를 다시 호출하면 안 된다.

검증은 기존 actual stores/head/Journal/owner와 명시 synthetic source를 사용한 rehearsal에 한정한다: 각 durable 단계 중단, response loss, 동일 재시도, stale package, current owner/한도 변경, head 교체, publication 이전 소비 거절, publication 후 metadata 보존, baseline CAS 1회. 오류·복구·재시작 자체는 SELL이 아니다. 완성해도 source gate 및 carry controlled 거절은 유지한다.

## 실제로 멈춰야 하는 경계와 인계

생산 issuer에는 계좌 identity/main-pocket binding, origin/retained history와 per-trade fee, capture 기간의 실제 fence, 관련 mark/fill 누락·순서·watermark를 입증할 **자료 및 공급 계약**이 필요하다. 현재 코드/보관된 REST 설명에는 마지막 완전성 증거가 없다. API 키를 입력하거나 프로그램에 서명하는 것만으로 이 공백을 메울 수 없다. 특히 resting order가 체결될 수 있는 동안 단순 operator idle을 quiescence로 선언하지 않는다. 기존 flat-only `UpbitIntervalSource`는 no-fill/no-flow의 일정 현금 경로만 다루며 첫 fill 뒤 정상 보유 운영의 대안이 아니다.

따라서 위 1과 2는 사용자 추가 입력 없이 개발·격리 검증할 수 있다. 실제 계좌 설정·키·독립 origin/retention 자료·보관/backup/head 경로 선택은 로컬 배포 단계의 입력이고, 생산 coverage issuer는 실제 공급 계약 확인 전 **미지원**으로 인계한다. 강한 기존 coverage 계약을 바꿔야만 가능한 경우에는 코드 편법으로 처리하지 않고 별도 정책/자료 정의 변경으로 표시한다. 시장 수익·무손실을 보장하는 새 계약을 만들지는 않는다.

각 구현 단위의 마지막에는 exact commit·테스트 범위·known limits·다음 파일을 인계한다. 사용량 조회 불가를 95% 도달로 추정하지 않는다. 이 문서는 설계 조사 완료이며 1/2 구현 완료 기록이 아니다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
