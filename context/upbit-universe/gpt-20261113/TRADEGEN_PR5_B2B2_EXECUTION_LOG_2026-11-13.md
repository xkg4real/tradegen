# PR5 B2b-2 실행 기록 — 사건에 연결한 정확 원본 복구

작성일: 2026-11-13. 전용 브랜치 `gpt/research-recovery-controller`. PR50 main을 통합한 `e789223bc1909a4a9546be12a2f66f4cfb921f64`에 마지막 진단 수정을 적용한 runtime `63d1864a96b0b1c9c577a72fe1c51ff284a5b9eb`를 검증했다. 최종 영향 범위 **131 PASS / 0 FAIL / 0 NOT_RUN, 138.115초**이며, 세 실행의 고유 검사 목록 대조는 **205 PASS / 미해결 FAIL 0 / NOT_RUN 0**이다. 단일 전체 suite 205개 연속 통과를 뜻하지 않는다. 실제 배포·서명·활성화·주문은 수행하지 않았다.

## 구현된 동작

정상 자료가 기존 사건 저장소에 등록돼 있을 때 실제 원본·백업·서명·현재 소유자 정보를 다시 확인하여 복구 경로를 사전 등록한다. 기존 등록 객체를 반환받았다는 이유만으로 자료가 정상이라고 간주하지 않는다. 실제 전체 graph를 다시 검사하고 서명을 인증하며, 이미 보류된 원본의 새 경로 등록은 거절한다. 목적지는 사용자가 별도로 준비한 실제 저장소여야 한다. runtime은 목적지나 head를 새로 생성·초기화·채택하지 않는다.

경로는 실제 사건·시도 namespace, 원 자료의 전체 dependency 목록, source/destination 설정과 원래 directory identity, storage/object 정책, 정확한 원 서명 및 canonical 철회 대상을 연결한다. 실행 시 caller가 만들어 넘긴 성공 판정·owner context·복구 결과를 근거로 받지 않는다. 원 primary가 없어져도 등록된 경로·identity를 바꾸지 않으며, 같은 경로에 다른 directory가 생기면 원래 저장소로 취급하지 않는다.

`run_recovery_once`는 실제 관련 사건과 독립 시도 기록을 읽어 한 번만 진행한다. source admission 실패는 보관 자료의 영구 소실이라고 부르지 않는다. 원본 및 실패·불완전 후보 기록을 포함한 정확한 bytes의 복구에는 기존 `restore_signed_backup`을 사용한다. 복구 결과를 이용해 연구 선발이나 거래를 활성화하지 않는다.

## 기록·중단·재개 계약

- 실제 destination write 전에 `ATTEMPT_STARTED` 또는 `RESUME_STARTED`가 독립 head와 backup/readback까지 확정돼야 한다. source·authority 사전 확인에서 실패하면 `PREFLIGHT_REFUSED`가 결과와 outbox를 함께 남긴다. 이 거절도 동일한 실행 예산을 소비하며 현재 관찰이 없으면 checkpoint는 null이다.
- 단일 plan은 신규 시도 한 번과 최대 두 번의 재개만 허용한다. 재개 간격은 마지막 시작 또는 결과 중 늦은 trusted 시각부터 최소 60초다. 한 호출 안에서 대기하거나 반복하지 않는다. 원래 서명의 만료를 연장하지 않으며, authority 거절은 영속 terminal 상태여서 새로운 provider 인스턴스로 우회하지 못한다.
- 별도의 실제 operation lock을 복구 전체 동안 유지한다. 오래 걸리는 복사를 다른 프로세스가 중단된 작업으로 오인해 동시에 재개하지 못하게 한다. 각 journal/head 작업은 별도 짧은 lock을 사용하고 복사 중 해당 session lock을 유지하지 않는다. `check_operation`은 현재 retained root/lock identity를 재검사하며 미래의 배타적 접근이나 매체 안전성을 보증하는 lease는 아니다.
- `admit_pair`는 START/RESUME와 뒤따를 결과·outbox의 row·record·state·byte 용량을 쓰기 전에 함께 예측한다. controller의 두 번째 event는 길이가 보수적으로 큰 **용량 계산 전용 자료**이며 확정하거나 관찰 결과로 반환하지 않는다. admission은 실제 디스크 예약이 아니며 최종 commit은 모든 검사를 반복한다.
- commit에서 예외가 나면 해당 프로세스의 namespace를 미확정 상태로 latch한다. 같은 프로세스가 임의로 읽어 채택하는 복구 기능은 추가하지 않았다. 새 프로세스는 실제 journal·version backup·head 전체를 replay해야 한다. 이미 확정된 결과의 응답만 유실됐다면 그 결과를 역사적 사실로 조회할 수 있으나, 현재 자료가 여전히 온전하다는 주장이나 현재 사용 권한은 재발급하지 않는다.
- 정상적으로 확정된 일부 raw/verified/artifact는 보존한다. torn journal, head 불일치나 orphan 기록은 잘라내거나 자동 채택하지 않는다. 새 목적지를 자동 생성해 반복하지 않는다.

## 소유자 이력·철회·완료 시각

새 선택적 `CurrentOwnerAuthority.observe_checkpoint`는 실제 현재 owner loader와 PEM을 읽고, 현재 key·전체 D14 code hash를 기존 checkpoint와 비교한다. 현재 서명 로그 전체를 실제 `verify_log`로 검사하면서 저장된 과거 head가 그 로그의 정확한 prefix인지 확인한다. checkpoint의 공개 생성자나 저장된 숫자 자체에 신뢰를 부여하지 않고 provider의 private pin에 caller 값을 대입하지 않는다. 기존 일반 `__call__`의 수락 동작은 유지한다.

checkpoint 검사는 원래 관찰 시각을 유지한 채 내부 실제 완료 시각과 마지막 clock 사이의 역행, 원래 관찰로부터 30초 초과, 서울 날짜 변경을 거절한다. controller의 마지막 완료 clock은 선택적 provider가 실제로 관찰한 완료 시각보다도 빠를 수 없다. 새 시각으로 오래된 관찰을 갱신하지 않는다. 재시작 시에는 route와 모든 시작·결과에서 실제로 얻은 checkpoint 중 가장 최근 것을 선택하여 더 오래된 결과로 기대 prefix를 낮추지 않는다.

복사 후 최종 단계는 actual owner 관찰을 **목적지 전체 재검증 전에** 확보한다. 실제 `verify_restored_archive`로 target/raw·양쪽 backup·원 서명 artifact를 다시 읽은 뒤 사건·route·attempt와 current owner checkpoint·canonical 철회를 확인한다. 무거운 graph·서명·로그 작업 후 retained root/head/operation 상태를 확인하고 마지막 clock을 읽는다. 전체 최종 검증을 최초 관찰의 30초 범위로 묶으며 helper가 반환한 완료 시각을 새 시작 시각으로 사용하지 않는다.

실제 관찰된 철회는 현재 checkpoint와 `REVOKED`로 기록하고 terminal `AUTHORITY_REFUSED`로 처리한다. 관찰이 실패하거나 시각을 신뢰할 수 없으면 해당 사실은 null/UNOBSERVED로 보존한다. 결과를 commit하는 동안 시간이 더 흐르더라도 완료 시각을 새로 붙여 현재 승인이라고 주장하지 않는다.

## 원 backup이 사라진 경우

목적지에 이미 target과 원 서명 artifact가 완성됐지만 결과 기록 전 중단된 경우, 목적지 전용 실제 재검증을 먼저 수행할 수 있다. 이 분기는 원 source catalog나 사라진 backup을 복구 완료의 필수 입력으로 다시 요구하지 않는다. 등록된 source 경로에 존재하는 replacement inode는 여전히 거절한다.

목적지가 불완전하면 원래 backup을 실제로 읽을 수 있어야 복사를 계속한다. source가 없다는 이유로 완료를 추측하거나 cached 반환 객체를 사용하지 않는다. 읽기 불가와 실제로 관찰한 부분 자료를 구분하며 보류를 유지한다. 완료된 자료도 source provenance 또는 전략 검증 결과로 승격되지 않는다.

## 검증 이력과 사례 범위

| 실행 | 결과 | 소요 시간 | Python/YAML fingerprint |
|---|---|---|---|
| recovery-controller-dev1 | 142개: 140 PASS / 2 FAIL / 0 NOT_RUN | 752.628초 | af1345f467944da14c5a8c4d9bf2aa4e57af53b730ffcd572520c6191043d551 |
| recovery-controller-corrected-related | 153개: 152 PASS / 1 FAIL / 0 NOT_RUN | 96.241초 | a3849ce43c0232cb47543f47fa519c49b2335b3f68c581f558f68ec61f27fe65 |
| recovery-controller-final-affected | 131 PASS / 0 FAIL / 0 NOT_RUN | 138.115초 | 1dec546fe298a31f8b2635c3ec37ed46c0c542ea8bf558343c7567722a00120d |

첫 두 실패는 검사 준비 오류였다. 세 번째 preflight fixture가 앞선 실제 사건 번호보다 작은 head를 사용했고, 네 번째 실행 번호는 저장소에 들어가기 전 codec에서 정상 거절되는데 저장소 오류만 기대했다. 사건 head를 단조롭게 유지하고 네 번째 codec 거절과 실제 저장소의 반복 세 번째 전이 거절을 각각 검사하도록 수정했다. 실행 횟수·재개 시간·보호 정책은 완화하지 않았다.

두 번째 실행은 실제 START는 들어가지만 outcome까지의 공간은 부족한 사례와 같은 경로의 source backup directory 교체 사례를 추가했으며 두 사례 모두 통과했다. 다만 반복 전이의 구체 진단을 비교하면서 형식 상태 전이 오류가 `_pinned`의 일반 ValueError 처리에 의해 `RECOVERY_STORE_PIN_REFUSED`로 바뀌는 결함을 확인했다.

마지막 수정은 실제 model 연산 경계에서 `RecoveryAttemptError`만 먼저 정규화한다. 정확한 `RECOVERY_RESOURCE_LIMIT`는 저장 용량 거절, 잘못된 전이는 `RECOVERY_STORE_TRANSITION_REFUSED`, 손상된 상태 재생은 `RECOVERY_STORE_REPLAY_REFUSED`로 구분한다. 실행 횟수 초과를 디스크 부족으로 바꾸지 않는다. 기존 경로·쓰기·잠금·무결성 오류는 그대로 보존하며 journal/backup/CAS 순서와 bytes를 바꾸지 않는다. 실제 max_attempts 용량·max_resumes 전이·정상 JSON/backup이나 잘못된 기록 전이의 재생 거절 회귀 3개를 추가했다.

최종 실행은 새 저장소 40개·형식 26개·실제 CLI 14개·추가 controller 경계 2개 및 권한/쓰기/계좌 guard를 포함한다. 기존 actual authority 12개·통합 23개와 기존 owner 검사는 앞선 실행에서 통과했다. 세 실행의 정확한 테스트 ID를 대조하고 최신 결과로 치환한 고유 범위는 **205 PASS / 미해결 FAIL 0 / NOT_RUN 0**이다. 실행별 실패 원문·rows·summary와 `recovery-controller-validation-combined-{rows,summary}.json`을 보존했다. 각 실행의 범위가 겹치므로 숫자를 합산하지 않는다.

실제 임시 owner 서명 로그·원본/백업 저장소·사건/시도 journal/head·기존 복원 함수를 사용했다. raw/verified 및 실제 fixed/carry recorder 가족, 실패 원본과 모든 후보 보존, START-before-copy, 부분 복사/artifact 뒤 중단·동일 시도 재개, 사라진 source와 완성 목적지, expiry·철회·key/code 변경·prefix rollback/fork, fresh provider 우회 거절, 60초 경계·세 번 예산, 결과/outbox·응답 유실, root/lock/backup/head/용량 및 마지막 완료 clock 역행을 확인했다. 성공 owner context·서명·평가를 임의 참으로 대체하지 않았다.

세 실행 모두 19 KEYLESS 이름, 격리 임시 홈·일회용 테스트 서명·합성 자료를 사용했다. import/발견 전부터 종료까지 실제 home **메타데이터**와 동결 source가 불변이었고 QA를 원본으로 복원했다. CRLF인 owner_authority.py를 유지했으며 AST·diff·독립 읽기 검토를 마쳤다. 마지막 runtime commit의 Python/YAML fingerprint는 최종 실행과 동일하다. Linux에서 수행한 관련 검사이며 native Windows·실계좌·실제 전원 장애 검증으로 표시하지 않는다.

## 남은 범위와 한계

이 기능은 exact archive 복구와 결과 기록에 한정된다. 사건 보류 해제, 현재 연구 선발/활성화 경로 교체, 거래 활성화·실제 주문·자동 청산은 포함하지 않는다. 기존 손실 하한과 위험정책을 완화하지 않는다. 손상 원본은 삭제·수정하지 않고 기존 서명 bytes를 보존한다.

outbox는 복구 결과 알림 intent와 별도 전달 보고만 저장한다. Telegram 전송, 알림 도착 보장, Face ID/WebAuthn 서명이나 새로운 승인 요청은 구현하지 않았다. 보고된 delivered 상태도 이 controller가 실제 네트워크 전송을 수행했다는 증거는 아니다.

사용자 PC의 native Windows 운영·전원 장애·실계좌 장애 검증은 수행하지 않았다. 임시 환경의 합성 연구/가격·GET 자료와 일회용 테스트 서명으로 실제 소프트웨어 경로를 검사한다. 모든 저장소와 anchor를 함께 되돌리는 coherent rollback, 기록 전에 전원이 끊겨 남지 않은 관찰, 미래의 source 가용성·저장 여유를 보장하지 않는다. 이 작업은 새 source 인증기관이나 거래 권한 발급기를 만들지 않는다.

계약: `TRADEGEN_PR5_B2B2_API_CARD_2026-11-13.md`. 원 설계: `TRADEGEN_PR5_B2B2_RECOVERY_CONTROLLER_PLAN_2026-11-13.md`.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
