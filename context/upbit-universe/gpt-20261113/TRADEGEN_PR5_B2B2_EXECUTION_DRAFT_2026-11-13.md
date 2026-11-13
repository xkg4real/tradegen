# PR5 B2b-2 실행 기록 초안 — 사건에 연결한 정확 원본 복구

작성일: 2026-11-13. 전용 브랜치 `gpt/research-recovery-controller`. 이 기록은 구현·정적 검토 상태를 설명한다. 부모 세션의 공통 개발 검사 **142개가 실행 중**이며 결과는 아직 확정하지 않았다. 최종 PASS, 배포 또는 실거래 준비 완료 기록이 아니다.

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

## 검사 상태와 사례 범위

소유 파일은 동결 후 AST와 줄바꿈을 고려한 diff 검사를 통과했다. `owner_authority.py`의 CRLF를 보존했다. 독립 읽기 검토에서 완료 시각, 원래 서명 prefix, canonical 시간 형식, 실제 사건 membership 및 두 event 용량 admission을 점검했다.

검사 작성 범위는 실제 임시 서명 owner 로그·원본/백업 저장소·사건/시도 journal·head를 사용하는 경로다. 계획된 공통 실행에는 정상 raw/verified 복구, 실제 dependency 보류 및 독립 연구, START-before-copy, raw/verified/artifact 후 중단과 동일 시도 재개, 완성 목적지와 사라진 source, expiry·철회·key/code 변경·과거 prefix rollback/fork, fresh provider 우회 거절, 60초 경계·세 번 예산, 결과/outbox·응답 유실, root/lock/backup/head/용량 경계, 실제 완료 clock 역행 및 처리 지연이 포함된다. authority 전용 12개 검사는 실제 일회용 서명과 현재 loader를 사용하며 성공 context나 서명 검사를 임의로 참으로 바꾸지 않는다.

위 항목은 **검사 구현 및 실행 계획**이다. 142개 공통 개발 실행의 실제 PASS/FAIL/NOT_RUN, source fingerprint, 격리·QA 복원 결과는 부모의 완료 artifact를 확인한 뒤 별도로 갱신해야 한다. 현재 이 초안에는 통과 개수나 실행 시간을 만들지 않았다.

## 남은 범위와 한계

이 기능은 exact archive 복구와 결과 기록에 한정된다. 사건 보류 해제, 현재 연구 선발/활성화 경로 교체, 거래 활성화·실제 주문·자동 청산은 포함하지 않는다. 기존 손실 하한과 위험정책을 완화하지 않는다. 손상 원본은 삭제·수정하지 않고 기존 서명 bytes를 보존한다.

outbox는 복구 결과 알림 intent와 별도 전달 보고만 저장한다. Telegram 전송, 알림 도착 보장, Face ID/WebAuthn 서명이나 새로운 승인 요청은 구현하지 않았다. 보고된 delivered 상태도 이 controller가 실제 네트워크 전송을 수행했다는 증거는 아니다.

사용자 PC의 native Windows 운영·전원 장애·실계좌 장애 검증은 수행하지 않았다. 임시 환경의 합성 연구/가격·GET 자료와 일회용 테스트 서명으로 실제 소프트웨어 경로를 검사한다. 모든 저장소와 anchor를 함께 되돌리는 coherent rollback, 기록 전에 전원이 끊겨 남지 않은 관찰, 미래의 source 가용성·저장 여유를 보장하지 않는다. 이 작업은 새 source 인증기관이나 거래 권한 발급기를 만들지 않는다.

계약: `TRADEGEN_PR5_B2B2_API_CARD_2026-11-13.md`. 원 설계: `TRADEGEN_PR5_B2B2_RECOVERY_CONTROLLER_PLAN_2026-11-13.md`.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
