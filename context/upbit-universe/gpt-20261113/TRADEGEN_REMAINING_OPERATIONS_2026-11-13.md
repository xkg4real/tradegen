# TRADEGEN 남은 운영 과업 — 2026-11-13 현황

**앱을 실행하는 것만으로 자동 실거래를 시작할 수는 없다.** 현재 운영 조립은 모의운영 전용이다. 첫 체결 이후의 보유 계좌 증거, 위험 상태, 주문·체결 대조와 실제 운영 승인을 연결하는 작업이 남아 있다. API 설정이나 서명만 추가하면 끝나는 상태가 아니다.

관측 시각: **2026-11-13T13:59:33+00:00**. PR39는 최종 종료 요약을 확인했고, PR40의 실행 중 검사 수는 해당 체크포인트 관측값이다. 이번 문서 갱신은 기존 기록을 읽고 이 파일만 수정했으며 실제 홈·키·계좌·API·주문·활성화를 사용하지 않았다. 금액과 개인 경로는 포함하지 않는다.

## 1. 완료·검증 중·구현 중

서로 겹치는 검사 수를 합산하지 않는다. NOT_RUN은 통과가 아니다. 최신 인계 `CURRENT.md`의 `updated_at`은 `2026-11-13T22:46:57+09:00`이며, 병합 main은 `5217f1e7977fab170a5453ad1ac8d4fc58521dc6`이다.

| 단위 | 현재 상태와 증거 | 완료로 확대하지 않는 범위 |
|---|---|---|
| PR34·35 | 정상 호가·보유 자료 보존과 v3 이력, 순수 보호 상태를 검증·병합. main `86c9e94`, `6030fe3` | 실제 보유 계좌 운영·승인 발급 |
| [PR36](https://github.com/xkg4real/tradegen/pull/36) | main `dc34c1a` 병합. 유니버스 Runner/Coordinator/owner 모의운영 연결. 전체 2,907개 = 2,772 PASS / 0 FAIL / 135 NOT_RUN, 단일 연속 실행 1,240.435초 | 새 유니버스 평가기·실거래 조립 |
| [PR37](https://github.com/xkg4real/tradegen/pull/37) | main `f41501f` 병합. 보호 상태/outbox 영속화·독립 head·전체 재생. 관련 통합 187 PASS / 0 FAIL / 0 NOT_RUN, 31.198초 | 실제 startup 계좌·미체결·체결 대조와 주문 재개 |
| [PR38](https://github.com/xkg4real/tradegen/pull/38) | main `5217f1e` 병합. A0a strict outcome 문서 codec. 154 PASS / 0 FAIL / 1 Windows NOT_RUN, 43.321초 | 실제 실패 평가 발급·연구 승인·확정본 복구 |
| [PR39](https://github.com/xkg4real/tradegen/pull/39), carry-v2 | **최종 전체 회귀 종료 요약 확인, 병합·전달 대기**. 검증 소스 `2b1de13227a8985620f253260dd2ab836a498d0f`, fingerprint `3001278c9174a007be7d5531cbedf3f643a6d6dd11b5044a73316d6d7877d36b`. 2026-11-13T13:58:33+00:00 종료 기록: 3,071개 = 2,936 PASS / 0 FAIL / 135 NOT_RUN, 단일 연속 실행 1,385.116초. 소스·실제 홈 메타데이터 전후 불변. | 병합·운영 완료, 미실행 135개의 통과 |
| [PR40](https://github.com/xkg4real/tradegen/pull/40), A0b | **구현 완료, 집중 123 PASS / 0 FAIL, 전체 검사·최종 전달 대기**. PR39 위의 stacked draft. 검증 소스 `2879b536d883d42206c827fc6f650ee2ca135d8f`, fingerprint `599e196fa192193299c2b42a99fa80e4b0a125f459c92138cdde91fde9736bf8`. 2026-11-13T13:59:26+00:00 체크포인트: 2,294/3,103개 기록, 2,172 PASS / 0 FAIL / 122 NOT_RUN. | 최종 전체 통과·main 병합·PR5 전체 완료 |
| B1a 연구 보관·백업 | `2879b53` 기반 별도 작업본에서 **실제 구현 중**. 형식·receipt 검증·저장·연구 adapter를 분담하며 공용 API 카드를 확정했다. 아직 통합 검증 완료가 아니다. | 신뢰 manifest 승인·정확 자동복구·WebAuthn·실거래 |

PR39의 session `95772`는 최종 요약까지 남았고 PR40의 `20430`은 진행 중이다. 두 검증 소스는 동결 상태다. PR40 체크포인트의 FAIL 0을 전체 종료·소스 및 실행 환경의 전후 확인 완료로 확대하지 않는다.

**역사적 실패 기록:** 초기 carry 개발 검사는 124개 중 113 PASS / 11 FAIL, 28.14초였다. 당시 통합 fixture의 규칙 관측 시각과 검토 시각 불일치로 `REVIEW_REQUEST_NOT_ELIGIBLE`가 발생했다. 이 결과는 이전 개발 소스의 기록으로 남기며, 이후 수정·집중 검증을 거쳐 최종 전체 회귀를 마친 현재 소스의 실패 수로 재사용하지 않는다. 중단·진단·재실행의 세부 기록은 각 실행 로그에 보존한다.

## 2. 이번에 구현한 경계

**Carry-v2:** 고정 Upbit 원화 현물 GTC 경로에서 유효한 LONG, CASH/SELL, 준비 부족·자료 부족을 구분한다. 기한 E는 자동 청산 신호가 아니며 초기 자동 전략의 신규 실행을 차단하고 새 관리 요청을 기록한다. 실제 평가기는 잔여 보유를 마지막 관측값으로 평가하고 FIFO 원가·모든 수수료·실현 손익·미실현 손익을 분리한다. 실제 typed decision 재도출, 새 factory/review/signature 결합과 직접 Runner 경로의 표시 요약 검증을 연결했다. 기존 GTC 주문의 늦은 체결은 새 주문 생성과 구분한다.

P2 기한 연결의 승인·관측·원장 참조를 실제 인증된 사실처럼 채우지 않았다. Coordinator와 carry controlled 실행은 계속 운영 미준비를 거절한다. 저장 장애·재시작·기한 자체를 매도 원인으로 만들거나 기존 손실 하한·halt를 완화하지 않는다.

**A0b:** `study_evidence.py`의 전체 후보 선행 검증을 `study select`와 `authenticate_study_selection`에 연결했다. 후보 ID·등록·원본 bytes·규칙·전체 슬롯/prefix·시각을 모두 검사한 뒤 기존 실제 평가기를 호출한다. 뒤 후보의 손상은 앞 후보의 평가·서명 검증도 시작하지 못하게 한다. 수학적으로 탈락한 후보도 보존하며, 크기/작업량 초과는 누락·손상과 구분한다. CLI는 추가·누락 capture를 거절하고 보고서·receipt 파일은 후보로 잘못 세지 않는다. 기존 승인 형식·통계 임계·위험정책은 유지했다.

A0b는 이제 다음 설계 제안이 아니라 **구현 및 집중 검증을 마친 변경**이다. 남은 일은 현재 전체 실행의 완료 확인과 PR39 이후 최종 병합·인계다. A0a outcome JSON은 여전히 실제 실패 발급자가 아니며, A0b도 과거 시도 계보·신뢰 출처·새 실패 outcome을 발급하지 않는다.

## 3. 다음 개발·전달 단계

1. **PR39·40 전달 마무리:** PR39의 완료된 전체 결과를 전달하고 PR40의 최종 전체 결과·미실행 사유·registry 일치·동결 소스 전후 확인을 마친다. PR39 병합 후 PR40을 main 기준으로 정리한다. 실행 중인 검사 트리는 수정하지 않는다. 실패가 생기면 그 소스의 실패를 남기고 수정한 소스로 다시 검증한다.
2. **B1a 실제 연구 보관 경로 완성:** 실제 recorder 원본을 읽어 `RAW_ARCHIVED`와 별도 백업을 먼저 남긴다. 전체 receipt·후보·source를 검증하고 실제 A0b 평가 후 동일 입력의 `VERIFIED_UNAPPROVED` 묶음을 확정·백업한다. 작업본 없이 저장된 bytes만으로 실제 재평가하고 원래 결과 digest를 대조한다. malformed·중단·계산 실패 원본도 보존한다. 부품 작성이나 manifest 파싱만으로 이 단계를 완료 처리하지 않는다.
3. **B1b 신뢰 승인, B2 정확 복구:** 앱 밖의 기존 독립 신뢰 경계에서 manifest·전체 파일 목록·승인 범위·기한을 검증하는 새 서명 체계를 연결한다. 정확한 원본 복구는 그 신뢰 서명과 일치하는 전체 bytes에서만 수행한다. 기존 승인 만료·폐기·현재 코드 등 다른 조건도 유효할 때만 재서명 없이 사용할 수 있다. B1a의 백업 검증을 이 기능의 완료로 표시하지 않는다.
4. **보유 계좌의 실제 운영 생애주기:** 아래 source·위험 commit/publish·startup 대조·보호 관리·주문 연결을 구현하고, 실제 운영 전까지 합성·장애 주입 회귀로 검증한다. 데이터 저장과 연구 승인이 이 운영 연결을 대신하지 않는다.
5. **실제 환경 수용과 활성화:** 준비된 구현에 대해 Windows·실계좌·실자료 연구·최종 범위별 서명·controlled 조립을 검증한다. 입력 없이 가능한 개발은 계속하며 기존 사용자 결정을 다시 묻지 않는다.

## 4. 실거래 전에 남은 운영 경계

| 과업 | 아직 필요한 것 |
|---|---|
| 보유 계좌 source·완전성 | 실제 가격·체결·수수료·입출금·사건 순서·구간 마감·누락을 입증하는 어댑터. 현재 flat-only 경로는 보유/새 체결에서 거절하며 continuous source도 실제 위험 연결을 요구한다. 잔고 스냅샷·heartbeat·임의 `complete=True`로 증거를 대체하지 않는다. |
| 위험 상태 commit/publish | 인증된 입력, 일관된 잠금 순서, guard/baseline/head 확정 후 observation 공개. provider 내부에 transaction을 중첩하는 단순 연결 대신 중단·재시작 경계까지 검증한다. |
| startup 대조·보호 관리 | 계좌·미체결·부분 체결·수수료·UNKNOWN/DISPATCHING 상태와 pending intent를 대조하고 중복 전송을 막는다. 유효한 전략/위험 원인과 별도 감소·취소 권한을 확인한다. |
| controlled launcher·상시 관리 | 실제 source·현재 승인·계획/세션·현재 위험정책을 조립한다. source나 관리 권한이 미준비이면 시작을 거절한다. 앱 시작과 거래 활성화를 구분한다. |
| 연구의 후속 검증 | 실제 실패 outcome 발급, 이전 시도 계보, 새로운 유니버스 평가기/revision, 실제 전향 관측과 실자료 선발. 합성 수익이나 문서의 결과 주장은 시장 우위 증거가 아니다. |
| Telegram/WebAuthn | Telegram 알림→HTTPS 승인 화면→기기 사용자 확인→일회성 요청·origin/RP·범위·기한·재사용 검증과 별도 승인 증거. 최초 등록·폐기·분실 복구 및 기존 독립 signer 전환도 남아 있다. 버튼 클릭만으로 서명하지 않는다. |
| 실제 상태·배포 | `floor_state_check`의 소유자 PC 실행은 **미실행**이다. 상태에 의존하는 분기는 실제 S1–S12가 필요할 때 처리한다. Windows 경로·잠금·전원 중단·재시작, 확정본/백업의 동기화 제외·장애 분리와 실제 계좌 설정도 검증해야 한다. |
| 법규·다시장 후속 | 인계의 `rules-review-1202`, KIS·OKX 실제 수집과 다시장 검증은 별도 남은 작업이다. 현재 fixed/carry 개발을 다른 시장이나 파생상품 운영 완료로 확대하지 않는다. |

## 5. 사용자 입력·승인의 적용 시점

이미 확정한 손실 보호 규칙과 **기한만으로 매도하지 않고 새 관리 승인을 요청한다는 결정**은 유지한다. 개발 승인은 실제 주문 실행 승인이 아니다.

- 상태 의존 단계에서는 금액·키·계좌번호 없이 S1–S12 결과 코드만 확인한다. 미실행을 정상 상태로 추정하지 않는다.
- 배포 단계에서 확정본/백업 위치, 동기화 제외·ACL·장애 분리, HTTPS/RP ID와 인증수단 등록·복구 절차를 확인한다.
- 실제 계좌/API 권한 확인은 사용자 로컬에서 수행한다. 채팅이나 공개 저장소로 키를 받지 않는다.
- 실제 코드, 규칙·한도, 실자료 연구 검토, 거래 세션 활성화는 각각의 범위에서 유효해야 한다. 기존 키·소유자 기록을 초기화하거나 연구 검토 승인을 거래 활성화로 확장하지 않는다.

실제 첫 거래 가능 여부는 **검증된 보유 source → 인증된 위험 상태 확정 → 원장 대조가 연결된 보호 관리 → 현재 범위별 승인 → controlled 실행 → 해당 Windows 환경 수용 검사**가 함께 확인되어야 판단할 수 있다. 소프트웨어 검사 통과는 수익 목표 달성이나 실전 시작 시각의 보장이 아니다.

## 근거와 다음 확인 위치

- 인계: `/workspace/tradegen-handoff-1113/CURRENT.md`, `LEDGER.md`.
- PR39 실행: `/workspace/tradegen-session/protective-carry-1113/carry-full-final-start.json`, `carry-full-final-checkpoint.json`, `carry-full-final-summary.json`, `carry-full-final.log`.
- PR40 실행: `/workspace/tradegen-session/research-family-1113/family-dev1-checkpoint.json`, `family-full-start.json`, `family-full-checkpoint.json`, `family-full.log`.
- A0b 계약: `/workspace/outputs/TRADEGEN_PR5_A0B_API_CARD_2026-11-13.md`.
- B1a 기준·진행 작업본: `/workspace/tradegen-research-bundle-1113`, base `2879b53`. 상세 계약은 `/workspace/outputs/TRADEGEN_PR5_SEALED_BUNDLE_READINESS_2026-11-13.md`, `/workspace/outputs/TRADEGEN_PR5_B1A_API_CARD_2026-11-13.md`.
- 운영 경계 소스: `account_interval.py`, `execution_accounts/continuous.py`, `continuous_guard.py`, `continuous_guard_commit.py`, `protective_store.py`, `coordinator.py`, `runner.py`, `tools/owner/rehearsal.py`. 함수·진단 코드를 근거로 읽으며 진행 중 파일의 행 번호를 고정 사실로 사용하지 않는다.
