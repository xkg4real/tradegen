# PR5 B2b-2a — 복구 사본 재검증 실행 기록

2026-11-13. 최신 main을 통합한 HEAD `24c51f62023c5c6c932411c75fae6d1c607be004`에서 관련 **142 PASS / 0 FAIL / 0 NOT_RUN**, 한 프로세스 **812.315초**로 검증했다. 이 문서는 실제 사용자 자료 복구·전자서명·매매 승인 또는 Windows 배포 기록이 아니다.

## 변경 범위

작업 기준은 main `ed1b456`, branch `gpt/recovered-archive-revalidation`의 별도 트리다. 구현은 `execution_launch/bundle_recovery.py`, 독립 신규 검사는 `tests/launch_recovery_revalidation.py`다. API 계약은 `TRADEGEN_PR5_B2B2A_REVALIDATION_API_2026-11-13.md`를 따른다.

새 `verify_restored_archive(destination, bundle_digest, attestation_bytes, *, incident_id, authority_provider, clock)`는 실제 BundleStore와 동일 clock의 실제 CurrentOwnerAuthority만 받는다. 기존 복구 때 사용한 동일 artifact ID와 exact 원 서명 bytes로 기대 artifact를 직접 도출하며, caller가 만든 RecoveryResult·artifact digest·권한 boolean을 사용하지 않는다.

실제 검증 경로는 **artifact 및 백업 → 원래 raw/verified 전체와 primary·backup의 실제 archive 인증 → artifact 및 백업 재확인 → 최종 실제 owner/철회/완료 시각 검사**다. 당시 실패·불완전 raw와 전체 후보 원본도 그대로 확인한다. 자료를 수정·재계산·선발하지 않으며 storage write/provision/head adoption을 하지 않는다. 기존 actual owner loader의 검증된 상태 snapshot·제한 anchor 동작은 기존 경계로 유지된다.

원래 source primary/backup이 사라져도 이 API에는 source 입력이 없다. 다만 **목적지 raw/verified와 필수 원 서명 artifact가 이미 실제로 완성·백업된 경우에만** 전체를 새로 검증할 수 있다. 미완성 목적지를 복사하거나 없는 artifact를 생성하는 기능이 아니다. 원 source 없이 partial copy를 완료했다고 추정하지 않는다.

## 철회 관찰과 기존 동작 보존

새 `RestoredArchiveVerification`은 마지막 실제 owner 관찰에서 canonical signing target과 restrictive set을 계산해 `REVOKED` 또는 `NOT_REVOKED_AT_HEAD`, 해당 target/head, `verified_at`를 반환한다. 앞선 archive 인증의 오래된 head를 재사용하지 않는다. 모든 무거운 graph·서명·철회 작업은 completion clock 이전에 끝낸다.

`REVOKED`도 정확한 보관 자료의 관찰 결과로 표시할 수 있다. 이는 철회된 승인을 사용할 수 있다는 뜻이 아니다. `NOT_REVOKED_AT_HEAD` 역시 특정 head·시각의 사실이다. 새 결과의 source 인증·연구 선발·현재 사용·거래·자동 운용 복구·보류 해제 관련 flag는 모두 false다. 생성자나 과거 report는 권한 토큰이 아니다.

공통 artifact→actual auth→artifact 읽기와 final observation 코드를 좁게 공유했다. 기존 `restore_signed_backup`은 다음 의미를 보존한다.

- source inspection/prewrite와 copy 후 실제 최종 검증의 phase를 분리한다. 긴 복사 후 실제 최종 재검증이 필요하며, 최초 final owner 관찰부터 30초 한도를 유지한다.
- 같은 provider가 전체 과정의 key/code/head/clock pins를 유지한다.
- 공유 graph 읽기 뒤 기존 `_separate(source, destination)`를 최종 completion clock 전에 그대로 수행한다.
- exact partial retry와 원본 보존, 기존 artifact bytes 및 `_finish`의 3개 반환값 계약을 유지한다.
- 기존 `RecoveryInspection/RecoveryResult.revocation_status='UNSUPPORTED'`와 archive-only 의미를 바꾸지 않는다.

## 완료한 검증

- 개발 검사: 신규 21개 **21 PASS / 0 FAIL / 0 NOT_RUN, 406.028초**. fingerprint `9285dac270efafec1d74ebef6af976ffe593808d5ff2c995ffddfe68d82cc5c6`.
- 최종 관련 통합검사: 신규 21개와 기존 복구·artifact·archive 인증·철회·쓰기/권한 경계 등을 포함한 **142 PASS / 0 FAIL / 0 NOT_RUN**, 한 프로세스 **812.315초**. 개발 검사와 합산하지 않는다.
- 최종 HEAD `24c51f62023c5c6c932411c75fae6d1c607be004`에는 PR47·PR48 main을 통합했다. Python/YAML fingerprint `5afbc6402e885a67963213d0abb2420b8d4ab82e8c589fcdb31e8b2efa2f124e`의 전후 일치를 확인했다. AST·diff 및 독립 소스 읽기 검토도 완료했다.
- 19개 KEYLESS 변수, 임시 홈·일회용 테스트 서명·합성 자료를 사용했다. import/검사 목록 구성 전부터 종료까지 실제 홈 **메타데이터** 불변, QA 원본 복원을 확인했다. 실제 홈 내용·키·거래소/API·주문·알림 전송은 사용하지 않았다.
- 증거 파일: `recovery-revalidation-integration-final-start.json`, `-checkpoint.json`, `-rows.json`, `-summary.json`. 전체 저장소 suite가 아닌 관련 검사다. Linux 결과이며 native Windows·실계좌 장애 검증으로 표시하지 않는다.

신규 검사는 실제 임시 raw·verified graph와 실제 fixed/carry recorder 자료, 실제 복원 및 source 제거 후 재검증을 포함한다. verified 형태만 만든 미발급 fixture와 실제 recorder/evaluator 경로를 구분한다. 필수 artifact·backup·전체 후보·head·lock·경로 이상, fake 입력 거절, 실제 signed revocation, canonical JSON, 30초·expiry·rollback·서울 날짜·늦은 code/key/head 변경·느린 최종 철회 계산을 확인했다.

## 남은 실제 연결

이 단위는 destination-only 재검증 primitive다. 아직 자동 복구 controller, durable attempt store, 실제 사건-to-artifact linkage, 결과 outbox, Telegram 전송, 보류 해제 또는 운영 route 전환은 없다.

다음 최소 단계는 실제 incident namespace·등록 route·원 서명·사전 준비 목적지를 묶고, 독립 attempt journal/backup/head에 START를 먼저 확정한 다음 기존 B2 복구를 실행하는 controller다. 중단 후에는 이 새 helper로 완성된 목적지를 실제 재검증하여 outcome+결과 알림 intent를 확정한다. torn journal/head 자동 채택, caller의 완료 boolean, provider 재생성에 의한 알려진 거절 우회는 허용하지 않는다. B2b-1 보류는 유지한다.

정확한 원본이고 원래 scope·기간·철회·code/key 등 승인 조건이 계속 유효하면 복구 자체 때문에 재서명을 요구하지 않는다. 새 버전 재구성·새 관측에는 별도 검증과 새 승인이 필요하다. 현재 연구 사용을 재개하려면 독립 incident head·복구 목적지·fresh 실제 source/family/factory/owner 조건을 결합하는 후속 binding과 실제 consumer 구현이 필요하다. 이번 결과만으로 이를 충족했다고 표시하지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
