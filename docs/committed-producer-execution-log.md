# Committed producer 실행 기록 — PR #60

작성일: 2026-11-13. **중복 제거 446개 검사 중 445 PASS, 미해결 FAIL 0, Windows 전용 NOT_RUN 1.** 여섯 실행에서 총 453건을 검사하고 정확한 registry 집합으로 중복을 제거한 결과이며 단일 process의 446개 실행이 아니다. [PR #60](https://github.com/xkg4real/tradegen/pull/60)의 전달·병합 메타데이터는 별도 [전달 체크포인트](https://github.com/xkg4real/tradegen/blob/handoff/context/upbit-universe/gpt-20261113/producer-delivery-checkpoint.json)에서 확인한다. 이 변경은 원본 보관·실제 guard commit·같은 provider의 다음 세대 게시·기존 rehearsal Coordinator/Runner를 연결한다. 실계좌 자동매매 활성화나 운영 source 완전성 인증을 완료한 것으로 해석하지 않는다.

| 기준 | 확인한 값 |
| --- | --- |
| production 구현 기준 | `c9d09fd00455ae23a67bf2ab08930795d60a83a4` |
| 계약 assertion 교정, 테스트만 변경 | `8d4bd65cf2dece1a0252984dabadc4bee583e94a` |
| terms 환경 fixture 교정, 테스트만 변경 | `605a1b620991e86bbe42fd7db81768c429a8fbc6` |
| delivery commit / tree | PR head와 별도 전달 체크포인트 |
| 실제 main 병합 commit / tree | PR 병합 기록과 별도 전달 체크포인트 |

production source는 `c9d09fd` 이후 변경하지 않았다. 뒤의 두 commit은 아래에 설명한 테스트 계약·환경 설정만 고쳤다. 최초 실패를 삭제하거나 통과로 덮어쓰지 않는다.

## 실제 수집부터 같은 provider 게시까지

[CommittedAccountProducer](https://github.com/xkg4real/tradegen/blob/c9d09fd00455ae23a67bf2ab08930795d60a83a4/execution_launch/committed_producer.py)는 실제 collector의 계좌 입력과 actual owner loader의 관찰을 연결한다. 초기 owner 관찰은 첫 interval 시작 이전에 완료돼야 한다. 공개 observation이나 claim을 만들어 전달하는 것으로 이 내부 관찰을 대체하지 않는다. 실제 정책·scope·store·head·clock·source 바인딩을 확인하며, 이 단위는 명시적 rehearsal와 정확한 DryRunAdapter에 한정한다.

각 구간은 다음 순서로 처리한다.

1. 실제 existing-only Journal에서 guard/baseline/control predecessor를 확인하고 transaction을 닫는다. 수집·보관 중에는 그 Journal transaction을 잡고 있지 않는다.
2. 기존 capture archive에 원문을 보관하고 전체 primary·backup을 읽어 검증한다. 의미 검증 실패는 원본을 보존하고 input/guard commit 이전에 멈춘다.
3. 실제 재생 material, 원 baseline, 실제 owner 전후 관찰, 원 평가 시각으로 기존 package를 구성하고 input을 보관한다. 느린 보관 후에도 현재 owner와 predecessor를 다시 확인한다.
4. 기존 startup `commit_input`이 실제 guard/baseline 전이를 수행한다. retained `expected_evaluated_at`을 유지하며 input hash만 같다는 이유로 원 시각을 바꾸지 않는다.
5. completion → input → capture와 백업을 다시 읽고 실제 COMPLETE·receipt prefix·현재 Journal prefix를 대조한다. 실제 다음 세대 게시는 별도의 strict Journal transaction에서 실행한다.
6. 최초 구간에서는 실제 startup 대조가 provider/Controller를 한 번 구성한다. 이후에는 같은 provider에 실제 successor를 게시하고 같은 Controller로 현재 계좌·주문을 다시 대조한다.
7. 마지막 actual account 관찰·owner·heads·현재 clock을 확인한 뒤에만 기술적 결과를 반환한다. 원 endpoint/owner/receipt의 시각은 그대로 남는다.

commit 뒤 완료 보관이나 게시가 실패하면 heads가 이미 이동했을 수 있다. 이전 provider를 현재 계좌로 재사용하거나 receipt를 추측하지 않는다. 도달한 단계와 확정·미확정 기록을 보존하고 해당 producer의 추가 수집·게시를 차단한다. 자동 rollback, head 채택, 재시드, 주문 재전송은 추가하지 않았다.

## 대조·Coordinator·Runner 연결

[CommittedStartup](https://github.com/xkg4real/tradegen/blob/c9d09fd00455ae23a67bf2ab08930795d60a83a4/execution_launch/committed_startup.py)의 public `reconcile(..., session_id=None)`은 최초 입력 바인딩을 유지한다. 새 private `_reconcile_runtime`은 자체 startup 잠금을 잡고 실제 세 archive graph와 현재 provider/receipt/COMPLETE/heads를 다시 검증한다. caller의 inspection·package·준비 상태를 권한으로 사용하지 않으며 초기 `_binding`, provider, Controller 또는 quote-disabled startup Runner를 재타깃하지 않는다.

공통 대조는 원래 주문·보유 조건을 유지한다. broker 증거와 충돌하는 RESERVED, 외부 미체결, UNKNOWN/DISPATCHING, 정확한 주문 identity·지정가·수량·부분 체결·누적 수수료와 실제 최근 reconciled 행을 검사한다. 상태 조회 횟수는 완료 증거가 아니다. account-only 현재 owner 읽기는 같은 선택 session을 사용하고, 개별 주문 작업은 그 주문의 기록된 session을 유지한다. 최종 대조 이후 생긴 fill은 새 실제 generation을 요구한다.

[Coordinator](https://github.com/xkg4real/tradegen/blob/c9d09fd00455ae23a67bf2ab08930795d60a83a4/execution_launch/coordinator.py)의 명시적 `committed_producer` 분기에서만 legacy advancing provider 호출을 건너뛴다. 따라서 실제 guard commit 뒤 baseline을 두 번 전진시키지 않는다. 기존 producer 미지정 경로는 유지한다. 실제 producer 결과를 내부적으로 보관하고, 현재 transaction/head 및 대조 결과를 재확인한 뒤 quote와 원 계좌 관찰을 history/tick에 연결한다.

`_current_unit`은 실제 `(account_read, endpoint, reconciliation)` 세 값을 반환한다. 현재 control head가 보관된 대조 결과와 달라지면 실제 대조를 한 번 수행하고, 최종 account head와 대조 head가 같아야 반환한다. 이 결과만으로 진입 권한을 부여하지 않는다. 기존 Runner의 기대 transaction ID 제한이 관측 → reserve → dispatch 사이 세대 변경을 거절한다.

느린 수집·보관·대조가 slot 또는 quote 시간을 넘기면 실행을 건너뛰며 과거 자료를 새 시각으로 바꾸지 않는다. 현재성은 30초뿐 아니라 기존 22시 cutoff, 서울 날짜, server time과 실제 완료 시각도 검사한다. terms는 현재 endpoint를 사용하고, runtime 전 stop/close/disarm은 만들어지지 않은 계좌나 kill 성공을 주장하지 않는다. source·저장·owner 오류는 readiness를 해제하지만 오류 자체를 매도 신호로 쓰지 않는다. 명시적 축소는 기존 account-only와 sell gate를 유지하며 새로운 연구·entry-risk 조건을 추가하지 않는다.

기존 capture의 packet/raw aggregate 각 64 MiB, 최대 2,000 receipts, 작은 generation metadata 64 KiB, startup 주문 대조 1,024개 상한은 유지한다. 새 저장 엔진이나 writer 예외는 만들지 않았다. 앱과 독립 서명 도구의 factory source 목록에 실제 producer/startup/archive/collector/owner/Coordinator/호가 sampler 의존성을 함께 반영했다. 변경 전 source review를 새 코드 승인으로 쓰지 않으며 D14 배포 검사는 별도로 유지한다.

## 실제 실행 결과

아래 값은 완료된 실제 summary에서 읽었다. 부모 검증기의 `producer-final-coverage.json`은 최초 세 registry의 정확한 합집합과 각 교정 결과를 대조했다. 최초 실패는 원본 실행에 보존하며 해당 검사의 이후 PASS와 구분한다.

| 실행 | 기준 commit | PASS | FAIL | NOT_RUN | 경과 초 |
| --- | --- | ---: | ---: | ---: | ---: |
| `producer-smoke1` | `c9d09fd` | 4 | 0 | 0 | 90.122 |
| `producer-core1` (A) | `c9d09fd` | 83 | 0 | 0 | 1221.544 |
| `producer-integration1` (B) | `c9d09fd` | 25 | 2 | 0 | 752.266 |
| `producer-related1` (C) | `c9d09fd` | 334 | 1 | 1 | 458.422 |
| `producer-contract-correction1` | `8d4bd65` | 2 | 0 | 0 | 44.819 |
| `producer-terms-correction1` | `605a1b6` | 1 | 0 | 0 | 25.518 |

최종 집계는 **446개 = 445 PASS / 미해결 FAIL 0 / NOT_RUN 1**이다. 여섯 실행의 총 453건에는 중복과 교정 재실행이 포함된다. production 기준은 `c9d09fd00455ae23a67bf2ab08930795d60a83a4`, 최종 검증 HEAD는 테스트만 교정한 `605a1b620991e86bbe42fd7db81768c429a8fbc6`이다. 최초 실패 세 건은 아래와 원래 summary에 그대로 남는다.

최초 실패 세 건과 교정은 다음과 같다.

- B의 `test_actual_opening_owner_provenance_two_intervals_and_exactly_two_durable_transitions`: 테스트가 실제 세 반환값을 둘로 unpack했다. 실제 triple을 받고 마지막 account head와 reconciliation head의 일치 assertion도 추가했다. 교정 검사에서 PASS했다.
- C의 `test_coordinator_source_static_contract`: Coordinator가 실제 factory source 검증 범위에 들어간 뒤에도 이전 제외 조건을 요구하던 정적 assertion이었다. 현재 source 목록과 정확한 포함 관계로 고쳤고 교정 검사에서 PASS했다.
- B의 `test_issued_terms_wait_for_runtime_then_use_retained_endpoint_without_a_legacy_frame`: KEYLESS 환경에서 terms fixture의 credential **환경변수 이름**이 준비되지 않아 `TERMS_ENV_CREDENTIAL_NAMES_REQUIRED`로 먼저 거절됐다. 기존 `TF.registries()` fixture로 이름만 설정했다. 실제 키 값이나 positive authority verifier를 주입하지 않았으며 원 runtime/endpoint assertion을 유지한 재검사에서 PASS했다.

미실행은 기존 `compliance_signer/test_stdin_terminal_check_follows_getconsolemode` 한 건이며 실제 사유는 `REFDATA: GetConsoleMode needs Windows`다. Linux 결과로 이 Windows 검사를 통과했다고 쓰지 않는다.

## 검증 범위와 증거 보존

완료된 core·smoke·integration·related·교정 결과에는 실제 임시 signed owner log, 기존 실제 capture/backup/head/guard commit, 같은 provider/Controller의 다음 세대, 실제 대조와 DryRun 경계가 포함된다. 실제 서명된 연구·평가·고정 factory·LiveHistory를 거쳐 warmup HOLD에 도달하고, 별도 격리된 축소 주문이 기존 gate를 한 번 통과하는 경로를 검사했다. 부분 체결·수수료·UNKNOWN 보존, 외부 미체결, 세대 변경 중 예약/전송 거절, owner 변경, 게시 실패, 원 시각 만료와 existing-only Journal 거절도 해당 검사에 포함된다.

시장 GET 응답·가격 경로·coverage는 명시적인 합성 fixture다. 실제 evaluator·서명·저장·대조 코드를 사용했다는 사실과 시장 자료의 운영상 완전성이 입증됐다는 주장은 구분한다. 실제 자동 전략 BUY/SELL 전체나 수익성·실체결을 검증했다고 보고하지 않는다.

여섯 summary 모두 19 KEYLESS 변수, import/discovery 전부터 완료까지 실제 보호 home metadata 불변, 실행 중 source 불변을 기록한다. 부모 검증기는 모든 실행의 원래 QA bytes가 동일하게 복원됐고 최종 registry 집계가 일치함을 확인했다. 최종 Python/YAML source fingerprint는 `f66e777e3d809d4ce22f7811270f14da0779e3a913b7434278a4a34553d4d419`다.

| fingerprint 범위 | Python/YAML source fingerprint |
| --- | --- |
| `c9d09fd` 최초 구현·검사 | `738be8eb0919ecd9db569312f8e09123786bec311ddaee7dcd7d67240db5bbb3` |
| `8d4bd65` 테스트 계약 교정 | `dcccaf4c9ea30a55698f33c8d60108949c8de771b794192b5cbb89585e035d30` |
| `605a1b6` terms fixture 교정 | `f66e777e3d809d4ce22f7811270f14da0779e3a913b7434278a4a34553d4d419` |

start/checkpoint/rows/summary/log를 다음 evidence root에 보존한다. 중간 실패와 교정 실행은 각각 남긴다.

- `tradegen-session/committed-producer-1113/producer-smoke1*`
- `tradegen-session/committed-producer-a-1113/producer-core1*`
- `tradegen-session/committed-producer-b-1113/producer-integration1*`
- `tradegen-session/committed-producer-c-1113/producer-related1*`
- `tradegen-session/committed-producer-1113/producer-contract-correction1*`
- `tradegen-session/committed-producer-1113/producer-terms-correction1*`
- `tradegen-session/committed-producer-1113/producer-final-coverage.json`

## 남은 운영 경계

기존 `ContinuousUpbitCandidateSource.__call__`의 live-risk 연결 거절과 controlled Runner/Coordinator 거절을 유지한다. GET 원문·hash·로컬 순서·fence·성공한 parse는 보이지 않은 mark/fill/transfer나 누락 구간의 부재를 입증하지 못한다. 이 단위는 그 빈자리를 caller boolean이나 timestamp로 채우지 않는다.

운영 source/continuous-coverage issuer, 실제 owner 사전 관찰 lifecycle의 재시작 보존, 긴 중단 구간 복구, 새 owner epoch 인계, 운영 scheduler의 완전한 자료 공급, post-deadline 새 관리 권한은 남아 있다. 후속 작업은 현재 보관·동일 provider 게시·실제 대조 기능을 재사용해야 하며, source 완전성이 없는 상태를 실거래 가능으로 바꾸면 안 된다. 패스키 grant/ledger와 HTTPS/iPhone 승인 연결의 완료 여부도 이 PR의 완료로 간주하지 않는다.

실제 계좌·실키·거래소 API·거래 활성화·실주문 사용은 **0**이다. 실제 home 내용은 읽거나 쓰지 않았고, 전후 메타데이터만 비교했다. Native Windows, 실제 broker status/cancel, 실제 전원 장애·운영 재시작과 iPhone Face ID는 **NOT_RUN**이다. 임시 자료에서 새 객체를 구성하거나 합성 장애를 재현한 검사는 이들 운영 검증과 동일하지 않다. 동일 사용자가 모든 자료와 모든 독립 anchor를 함께 과거로 바꾸는 경우까지 방어했다고 주장하지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
