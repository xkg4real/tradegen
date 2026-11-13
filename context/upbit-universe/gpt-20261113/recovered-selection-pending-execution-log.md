# 정확 복구 목적지의 연구 선발 재검증 — 실행기록 초안

2026-11-13. 구현 및 정적·독립 읽기 검토 기록이다. **새 단위의 관련368개 런타임 검증은 진행 중이며, 아직 완료 결과가 없다.** label `recovered-selection-related1`, HEAD `19f6775935f8d8828eed21fcaa76449507239a5b`, source fingerprint `97b858e0fa81969d2b93fc6e6971e5bdb2795c40b8256f904c91fa4ba4d39fe3`로 동결해 실행한다. 검증 결과, 최종 source fingerprint, commit 및 PR 정보는 실제 공동 실행이 끝난 뒤 추가한다. 이 문서는 운영 배포나 실거래 준비 완료 보고가 아니다.

## 구현 범위

새 `authenticate_recovered_study_selection`은 이미 등록된 route와 terminal `EXACT_ARCHIVE_RESTORED` attempt 한 건을 실제 복구 시도 저장소에서 읽는다. 대상은 `VERIFIED_UNAPPROVED` 연구이며 source와 destination에 적용되는 사건은 각각 같은 한 건이어야 한다. 추가 사건·다른 namespace·등록 변경·다른 목적지·미완료 복구는 거절한다.

원 source의 physical 경로를 다시 열지 않는다. 실제 목적지 target/raw, 전체 파일과 양쪽 backup, 정확한 원 archive attestation artifact와 그 backup을 확인한다. 과거 성공 outcome의 destination head는 현재 검증된 catalog의 실제 `(sequence, hash)` prefix여야 한다. 정상적인 후속 catalog 게시 자체를 손상으로 취급하지 않지만, 현재 graph나 거짓 prefix를 현재 head로 대체하지 않는다.

기존 monitor의 일반 `check_target`은 보류 대상에 대해 기존 의미를 유지한다. 새 private helper만 보류 상태에서도 실제 전체 graph를 다시 읽으며, `held=True`와 실제 `graph_checked=True`를 함께 반환할 수 있다. 이 관찰 자체로 보류가 해제되지는 않는다. 실제 target 또는 별도 artifact 읽기 손상은 해당 목적지의 사건으로 기록한다. 수치 탈락·서명 만료·철회·profile 불일치나 caller가 잘못 준 문서는 자료 손상으로 기록하지 않는다.

## 매 호출 수행하는 실제 검증

기존 sealed backend가 전체 원본으로 후보 family를 한 번 평가한다. 후보를 줄이거나 공개 result/manifest를 발급된 평가로 바꾸지 않는다. 모든 적격 후보의 source review, 선정된 실제 factory·program/protocol/evidence·profile/rules/window 및 독립 head를 가진 LiveHistory를 기존 경로로 검사한다.

평가 arithmetic은 authorization 구간 전에 수행한다. 이후 실제 `CurrentOwnerAuthority`의 첫 관찰을 기준으로 기존 30초 상한을 유지한다. stored recovery checkpoint는 실제 서명 로그의 prefix인지 `observe_checkpoint`로 확인하며 key/code·현재 canonical revocation·서명 유효기간·서울 날짜·profile 시각을 다시 검사한다. 새 관찰 시각을 붙여 이전 자료나 승인 구간의 나이를 초기화하지 않는다.

연구가 실제 선정되면 private hook에 검증한 내부 snapshot에서 만든 frozen basis를 전달한다. source-review 목록은 실제 인증한 study ID만 포함하고, 전체 후보의 원본·결과 연결은 별도 family binding으로 보존한다. caller mapping이나 표시 보고서를 다시 읽어 승인 기록을 구성하지 않는다. 공개 sealed API에는 callback, cached family 또는 승인 boolean 입력을 추가하지 않는다.

정확한 동일 원본과 원래 서명 문서가 현재 조건을 만족하면 기존 서명을 재사용한다. 복구 때문에 새 연구나 새 서명을 자동으로 만들지 않는다. 다만 변경된 배포 코드에 대한 새 코드 승인 조건까지 대신하는 기능은 아니다. 다른 자료·재수집·계산·프로토콜·규칙·window에 원 승인을 전용하지 않는다.

## 제한된 기록과 보류 유지

실제 `SELECTED`이며 source/implementation 검증을 통과한 경우에만 기존 IncidentStore에 `RESEARCH_ROUTE_RELEASE` 기록을 남긴다. 기록은 route/attempt/outcome, 단일 incident, 양쪽 registration, 정확한 bundle/raw/graph/artifact, 실제 family/선정·승인 binding과 관찰한 heads/checkpoint를 묶는다.

기존 append·버전 backup·독립 head/CAS·readback 엔진을 그대로 사용한다. 새로운 저장 엔진이나 owner 서명키를 만들지 않는다. 기존 IncidentState의 wire와 limits/context 및 과거 event bytes는 유지하고 명시적인 새 event kind만 추가한다. 기존 등록·사건·outbox·전달 기록은 지우거나 바꾸지 않으며 새 알림을 자동 생성하지 않는다. 구 버전은 모르는 event를 조용히 무시하지 않는다.

같은 binding의 재사용도 매번 실제 현재 검증부터 수행한다. 원 event를 다시 쓰거나 시각을 갱신하지 않는다. 그 event가 실제 backed incident Journal row에 있고 주장한 직전 head/sequence가 맞는지 확인한다. 과거 attempt/destination heads의 실제 prefix와 저장된 owner checkpoint도 검증한다. 형식만 맞는 release payload나 복사한 assessment는 이를 대체하지 못한다.

정상 수치 탈락의 실제 상태는 `NO_QUALIFIED_MARKET`이다. 이 경우 release를 쓰지 않고 `release_record_id=None`, `research_selection_ready=False`를 반환한다. 과거 release가 있더라도 새 탈락 결과의 사용 허가로 노출하지 않는다. 실패 원본과 탈락 후보를 보존한다.

기록 저장 전 실패하거나 실제 commit 뒤 응답이 유실되면 성공으로 반환하지 않는다. 기존 namespace latch와 실제 durable row를 보존하며 새 store 객체로 latch를 우회하지 않는다. torn append, backup/head 불일치를 삭제·truncate·자동 head 채택으로 처리하지 않는다.

일반 `blocked_incidents`, 일반 monitor와 incident-aware selector는 release 기록이 있어도 보류를 계속 적용한다. 새 consumer의 특정 목적지 연구 선발 관찰만 제한적으로 반환하며 `current_operational_use`, `execution_ready`, `automatic_operational_recovery_supported`는 모두 false다. 원 손상 저장소를 정상이라고 바꾸거나 일반 quarantine을 해제하지 않는다.

## 기록 뒤에도 남는 최종 확인

release 기록 뒤 목적지 graph/artifact, route/attempt와 현재 incident dependency를 실제로 다시 확인한다. 실제 history도 다시 읽어 기록 중 생긴 변경을 놓치지 않는다. 이어 현재 archive/source/implementation 승인과 owner를 재검증하고 마지막 작은 namespace/head 확인 뒤 완료 clock을 읽는다.

recovered 경로의 마지막 owner 관찰은 실제 `observe_checkpoint`의 완료 watermark를 유지한다. 최종 시각은 그 실제 완료보다 빠를 수 없고, 최초 owner 관찰의 나이·날짜·서명 만료 검사를 그대로 통과해야 한다. 최종 clock 뒤 무거운 hash·graph·서명·새 owner 읽기를 숨기지 않는다. 기록 뒤 최종 검증이 실패하면 남은 row는 역사적 사실일 뿐 현재 사용 승인으로 반환하지 않는다.

## 소비 명령

새 명령은 `python -m execution_launch.research_recovery_cli select-recovered`다. 기존 `route-register`/`run-once`의 archive 복구와 구분한다. `inspect`와 `list-pending`은 여전히 역사적 상태/대기 조회다.

`select-recovered`는 명시적인 attempt/incident/destination 저장소 설정, `--digest`, `--route-id`, `--incident-id`, 원 `--archive-attestation`, `--profile`, `--window`, history의 `--head-root`, 반복 `--source-review`와 `--audit STUDY=LOGICAL`을 사용한다. 필요하면 `--history-storage`를 지정한다. source 경로나 source backup 옵션은 요구하지 않으며 허용하지 않는다.

CLI 내부에서 실제 UTC clock과 같은 clock을 사용하는 `CurrentOwnerAuthority`를 구성한다. caller의 `--now`, 임의 public-key/authority boolean, cached result, provisioning 또는 서명 명령으로 사용 조건을 대체하지 않는다. JSON 표시는 현재 연구 선발 관찰과 일반 보류·운영 false 상태를 구분한다. 실제 입력 순서와 placeholder 예시는 [복구 운영 절차](research-recovery-operator-guide.md)의 새 7절을 따른다.

## 검증 준비와 관측 구분

| 새 검사 모듈 | 작성한 검사 수 | 런타임 상태 |
|---|---:|---|
| `launch_research_route_release` | 17 | PENDING |
| `launch_recovered_selection` | 13 | PENDING |
| `launch_recovered_selection_boundaries` | 12 | PENDING |
| `launch_recovered_selection_integration` | 9 | PENDING |
| `launch_recovered_selection_cli` | 13 | PENDING |
| 합계 | 64 | 실행 0회 |

정적 AST/diff 검사 및 독립 소스 읽기 검토를 수행했다. 작성한 회귀는 임시 실제 서명 로그·일회용 Ed25519 키, 실제 복구/저장소/독립 heads, 실제 recorder/evaluator/source review/factory/history와 합성 가격을 사용한다. 실제 source 삭제 뒤 fixed/carry 경로, 단일 평가, NO_SELECTION, 추가 사건·false prefix·거짓 release provenance, 현재 key/code/log 변경, 후기 artifact/철회/만료/시간/head 변화, 저장 전 실패와 응답 유실, 기존 보류 보존을 검사하도록 준비했다. **작성했다는 사실은 통과했다는 뜻이 아니다.** 관련 기존 회귀와 guard 범위 및 최종 실행 숫자는 실제 실행 뒤 기록한다.

읽기 검토 과정에서 검증한 snapshot으로 release basis를 만들 필요, 별도 artifact 손상의 실제 사건 처리, 과거 head의 실제 prefix 증명, record 뒤 history 재읽기와 실제 owner 완료 clock 보존을 확인·반영했다. 이는 정적 검토 발견사항이며 실행된 FAIL 결과로 기록하지 않는다. 실제 실패가 발생하면 해당 실행의 원문·수정·재검증 범위를 별도로 남긴다. 겹치는 실행의 테스트 수는 합산하지 않는다.

## 남은 운영 경계

실제 사용자 홈·계좌·키·API·주문·Telegram·Face ID/WebAuthn을 사용하거나 검증하지 않았다. native Windows 실행과 실제 전원 장애·실계좌 장애 검증도 아직 수행하지 않았다. 성공한 합성 연구가 실제 수익성이나 누락 없는 production source/coverage를 증명하지 않는다.

거래 활성화, 계좌·미체결 대조, 운영 경로 전환과 연속 source/account 통합은 별도 게이트다. 자료 손상·재시작·저장 장애를 매도 신호로 추가하지 않고 기존 손실 하한·위험정책을 유지한다. 모든 저장소와 독립 anchors를 함께 되돌리는 coherent rollback이나 미래 가용성·저장 용량을 보장하지 않는다.

계약: `TRADEGEN_RECOVERED_SELECTION_API_2026-11-13.md`. 선행 범위: `TRADEGEN_RECOVERY_CURRENT_USE_NEXT_UNIT_2026-11-13.md`.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
