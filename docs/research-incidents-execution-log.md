# PR5 B2b-1 사건 기록과 의존 연구 보류 — 실행 기록

2026-11-13. 구현 작업 단위이며 전체 TRADEGEN 완료·실거래 준비 완료를 뜻하지 않는다. 관련 331개와 수정 검사 27개를 대조하여 고유 331 PASS / 미해결 FAIL 0 / NOT_RUN 0을 확인했다. 단일 연속 331개 전체 통과 기록은 아니다.

## 구현 범위

- 실제 `BundleStore`의 raw/verified 전체 원본과 백업을 확인하여 논리 bundle/raw 식별자 및 물리 object 의존성을 등록한다. 형식상 생성한 등록 객체나 표시 보고서는 실제 관찰의 근거가 아니다. 첫 등록부터 이미 깨진 저장소를 독립 서명 manifest로 등록하는 경로는 이번 단위에 포함하지 않는다.
- 사건은 연구 저장소 밖의 명시적 세 경로(일지·버전 백업·독립 head)에 남긴다. runtime은 head를 초기화하지 않으며 별도 소유자 유틸리티가 빈 저장소 genesis만 준비한다. 일지 row, 정확한 별도 버전 복사본, head CAS, 전체 readback 순서가 성공한 경우만 확정한다.
- 장애 사건과 최초 알림 의도는 같은 전이에서 함께 확정된다. 알림은 로컬 outbox까지이며 Telegram 전송이나 성공 수신을 수행하지 않는다. reported delivery/unknown/retry 기록은 보류나 승인 상태를 바꾸지 않는다.
- 직접 확인한 object 손상은 해당 물리 저장소의 실제 의존 연구로 제한한다. catalogue/head 장애는 등록된 저장소 범위로 넓힌다. 일시 읽기 불가, 자원 한도, 형식 검증 거절과 입증된 무결성 실패를 구분한다. 같은 논리 연구를 다른 연구 저장소로 복사해도 동일 incident namespace의 보류는 유지한다. 뒤늦게 등록된 의존 연구와 그 사본에도 제한이 전파된다.
- 새로운 incident-aware 선발 경로는 초기 보류 확인 후 실제 family를 한 번 평가하고, 최종 graph/history 확인 후 다시 사건을 확인한다. 이후 실제 소유자·서명·폐기·기한 검사를 실행하며, 마지막 작은 head 확인 뒤 기존 완료 시각 검사를 유지한다. 기존 research-only API의 인수는 그대로이고 incident-aware로 표시하지 않는다.
- 유효 호가/보유 내역 삭제, 오류에 의한 매도, 자료 자동 복원, 보류 해제, 새 승인 발급, 거래 활성화는 없다. 모든 결과의 실행·현재 운영·자동 복구 필드는 false이다.

## 제한과 남은 연결

- 건강한 읽기 전에 실패 사건을 기록할 여유를 readonly `admit`로 확인하지만 미래 I/O 성공이나 다른 writer에 대한 용량 예약은 아니다.
- 사건 확정 실패는 `INCIDENT_RECORD_UNCONFIRMED`이며 같은 프로세스의 해당 namespace를 계속 거절한다. 부분 일지/백업/head는 재시작 후에도 거절한다. 아무 durable byte도 남기지 못한 I/O 실패의 프로세스 latch를 영속 사건이라고 주장하지 않는다.
- 고정된 namespace 구성과 독립 anchor 보존이 전제다. 전체 namespace/모든 anchor를 일관되게 교체·되돌리는 행위까지 보호한 것으로 취급하지 않는다. 저장소의 별도 디렉터리 배치는 별도 물리 장애 도메인이라는 증명이 아니다.
- 실제 Windows 네이티브 실행·전원 손실 내구성은 미검증이다. Linux 검사와 fake Windows API 계약 검사는 Windows 실운영 증거가 아니다.
- 정확 원본 복구 backend 이후 사건별 격리/복구 절차 연결, 새 버전/재실행/중단 운영 흐름, 재사용 시 현재 승인 재확인 및 보호된 관리 상태와의 연결, 승인 UI/Telegram 전송은 후속 단위다.

## 개발 검사 기록 (최종 검사와 합산하지 않음)

- Monitor 17 PASS / 0 FAIL / 0 NOT_RUN, 4.1598초. 실제 임시 object/catalog/head/backup, 원본·백업 손상, leaf/부모 소실 구분, 경로 교체, 기존 등록 관찰 실패, 용량 경계, 확정 실패 latch, 알 수 없는 시각을 검사했다.
- 19 KEYLESS 환경, 임시 홈만 사용, 공유 QA 미수정. 해당 생산소스와 테스트의 before/after SHA256 동일. 이 작은 개발런에서는 실제 홈 metadata 점검은 수행하지 않았다.
- 근거: `/workspace/tradegen-session/incidents-1113/monitor-dev1-summary.json`.
- 실제 fixed/carry 수직 smoke는 1 PASS / 0 FAIL, 26.957초. 각 actual recorder/family3/source signatures/factory/history와 초기·최종 guard를 거쳤다.
- 통합 개발 14개는 최초 13 PASS / 1 FAIL, 145.206초. 마지막 실제 서명 검증 후 사건 주입은 정확히 거절됐지만, 테스트가 authority 호출 수를 4회가 아닌 3회로 기대했다. 테스트만 수정해 해당 실제 경로 1개가 8.282초에 통과했다. 14개 성공 근거는 두 실행에 걸쳐 있으며 단일 최종 14 PASS 기록으로 표시하지 않는다.
- Launch guard 개발 26개는 25 PASS / 1 FAIL, 14.265초. 신규 4개는 모두 통과했고 기존 control guard 테스트의 UTF-8 미지정만 실패했다. 이미 PR46에서 고친 테스트를 main 통합으로 가져왔으며 B2b 코드는 완화하지 않았다. 최초 system Python 실행은 flet을 찾지 못해 테스트를 0개 실행했고 기존 프로젝트 가상환경으로 바로잡았다.
- 최종 monitor에는 원본 저장소 경로가 symlink로 바뀌어도 기존 등록에 연결된 STORE/READ_UNAVAILABLE 사건을 영속화하는 18번째 회귀가 추가됐다. 파일 경로를 원상복구해도 사건 보류는 유지한다.

## 최종 통합검사

PR46 main `ed1b4567fbd8161f1998a56241993880afccbb71`에 통합했다. 새 5개 모듈과 sealed selection, bundle store/recovery/auth/revocation 및 경계 검사를 포함한 관련 331개를 동결 소스에서 실행했다. 최초 launcher의 잘못된 cockpit selector는 발견 단계에서 거절되어 테스트 0개였고, 정확한 등록 ID로 실행했다.

최초 331개는 **330 PASS / 1 FAIL / 0 NOT_RUN**, 단일 프로세스 756.288초다. 실패는 frozen event의 잘못된 ID를 생성자가 먼저 거절하여 store.commit 경계까지 도달하지 못한 테스트 구성이다. 실제 생성자 거절은 정상이며 생산 코드는 변경하지 않았다. 이 런타임과 원래 검사를 `f96420bcd4730cdfde474f4d1578188ef971f0e7`에 기록했다.

수정 검사는 잘못된 ID의 생성자 거절 코드를 먼저 확인한 후 정상 복사본을 시험용으로 변조해 실제 저장소에 전달한다. 저장소 거절 `INCIDENT_STORE_COMMIT_REFUSED`, stale head 거절 `INCIDENT_STORE_EXPECTED_HEAD_CHANGED` 및 전체 파일 무변경을 모두 확인한다. 해당 저장소 모듈 **27 PASS / 0 FAIL / 0 NOT_RUN**, 8.903초. 처음 331개 registry에서 해당 27개 결과를 대체하면 고유 **331 PASS / 미해결 FAIL 0 / NOT_RUN 0**이다. 두 실행을 대조한 결과이며 합산하거나 단일 전체 통과로 표시하지 않는다.

원래 fingerprint: `b3a8c4225dcb2576da62027969af573a0c6a3b71e2f656c5393089e45ac59e1c`. 테스트만 수정한 최종 fingerprint: `3b3f9f47fa8a8368410e03b4afb99c13edb22ea54f12adac6c3889adf10dad09`. 양쪽 모두 19 KEYLESS, source 전후 불변, import/목록 구성 전부터 완료까지 실제 홈 metadata 불변, QA 복원. 전체 저장소 suite 재실행이 아니며, NOT_RUN 0은 native Windows 검증을 했다는 뜻이 아니다.

## 다음 단계

사건이 난 원본은 보존한다. 정확한 복구 controller가 현재 서명·철회·전체 파일 해시를 확인하고 별도 저장소에 복구한 뒤에도, 현재 사용 가능성을 별도로 검증하고 보호된 대체 경로를 확정하기 전에는 기존 보류를 해제하지 않는다. 새 버전 재구성·새 관측·사용 중단·Telegram/패스키·실계좌 실행 연결은 별도 남은 구현이다.

실제 owner 홈 내용, 사용자 키, 거래소/API, 실제 서명·활성화·주문은 사용하지 않았다. 임시 합성 자료의 테스트 성공은 실제 전략 성과나 수익 가능성의 증거가 아니다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
