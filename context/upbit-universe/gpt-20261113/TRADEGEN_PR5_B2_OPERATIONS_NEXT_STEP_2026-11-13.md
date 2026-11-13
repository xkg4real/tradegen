# PR5 B2 운영 연결 — 다음 최소 구현 단계

작성: 2026-11-13. **설계 문서이며 구현·배포·복구 실행·사용 승인 기록이 아니다.** 읽기 기준은 `/workspace/tradegen-sealed-selection-1113`의 base `797e8f5b934127734ae1207daaced9d1c3501200`과 이 트리에서 개발 중인 B1b-2b/c 소스다. 해당 개발 소스의 최종 동결·검증·commit은 부모 세션 기록을 따른다. 이 작업에서는 이 문서만 작성했다.

권장 다음 단위는 **B2b-1: 실제 검증 실패를 독립 사건 기록에 확정하고, 해당 증거에 의존하는 sealed 선발을 지속 보류하며, 재시도 가능한 결과 알림을 보관하는 연결**이다. 실제 복사 backend는 이미 있으므로 다시 만들지 않는다. 첫 단위에 Telegram 전송, 자동 매매 경로 전환 또는 보류 해제까지 넣지 않는다. 현재 사용 승인을 만들지 않고도 실제 장애 감지→영속 보류→소비자 거절→알림 대기까지 검증할 수 있다.

## 1. 기존 계획과 현재 구현의 차이

다음 문서의 설계를 잇는다. 네 단계 복구·정상 호가 보존·손실 하한·보호 보유 요구를 다시 결정하지 않는다.

- `TRADEGEN_PR5_REVIEW_AMENDMENT_2026-11-13.md` A§5–6, B§7: 네 단계 판단 순서, 의존 관계별 보류, 정확 복구 시 조건부 재서명 생략, 알림과 승인 분리.
- `TRADEGEN_PR5_B2_EXACT_RECOVERY_READINESS_2026-11-13.md` §1, §6–8: 별도 목적지 exact 복구, 지속 격리와 실제 consumer 연결의 후속 범위.
- `TRADEGEN_PR5_B2A_API_CARD_2026-11-13.md`: 구현된 복구 API와 signature artifact, 중단·재시도 계약.
- `TRADEGEN_PR5_B1B2_CURRENT_USE_READINESS_2026-11-13.md` §4–8 및 `TRADEGEN_PR5_B1B2BC_API_CARD_2026-11-13.md`: 실제 sealed A0b·전체 eligible 검토·선택 factory·현재 철회 검증. 이 결과도 지속 보류 해제나 거래 허가가 아니다.
- 저장소 `docs/exact-research-archive-recovery-execution-log.md`: B2a backend 검증 기록. 과거 B2a의 196 PASS는 아래 신규 운영 연결을 검증한 수치가 아니다.

| 현재 코드 | 이미 할 수 있는 일 | 새로 필요한 연결 |
|---|---|---|
| `bundle_recovery.py:inspect_signed_backup/restore_signed_backup` | 손상 primary catalog/head에 의존하지 않고 실제 현재 서명과 전체 backup을 검증; 별도 사전 provision 목적지에 동일 raw/verified와 signature artifact를 보관; 목적지 전체 재검증 | 장애 감지 trigger, 대상·서명·백업/목적지의 명시 등록, durable 시도 상태와 사건 연계, 결과 전달 |
| `recovery_artifact.py:build_recovery_artifact` | 원 서명 bytes와 content commitment를 별도 RAW_ARCHIVED로 보관 | 사건의 발생/시도/중단/결과 이력과 persistent quarantine은 별도 필요. 이 deterministic artifact는 복구 시각이나 승인 효력의 독립 증거가 아님 |
| `research_bundle_store.py:record_diagnostic` | 정상 catalog의 기존 raw ID에 고정 진단을 기록 | catalog/head 자체가 손상되면 호출 불가. 손상 저장소 밖의 독립 사건 journal 대체물이 아님 |
| `research_bundle.py:_evaluate_sealed_study_snapshot` | 전체 graph와 source/receipt를 검증하고 실제 family를 한 번 발급; manifest/record exact 재현 | 사건 journal의 현재 보류 상태를 확인하지 않음 |
| 개발 중 `sealed_study_review.py` | actual store→actual family→현재 archive/source 철회→실제 factory/history→최종 graph/owner 재검증 | incident/quarantine 입력이나 지속 상태 consumer는 아직 없음. `research_selection_ready` 결과를 격리 해제 token으로 쓰면 안 됨 |
| `protective_state.py`, `protective_store.py`, coordinator의 `_management_deadline` | 오류/재시작/기한과 매도 신호 분리; durable 보호 관리 사건/outbox와 일부 기한 연결 | bundle 사건과 실제 dependency·계좌/주문/관리 권한을 검증하여 연결하는 adapter는 없음. `AuthorityFacts`는 입력 모델이지 검증된 승인 증거가 아님 |
| `toast_queue.py` | 프로세스 내 비동기 FIFO 알림 | 영속 outbox, 재시작 중복 방지, 전송 영수증 또는 Telegram 전달을 보장하지 않음 |

**특히 B2 결과의 철회 표시를 주의한다.** 현재 `RecoveryInspection/RecoveryResult.revocation_status`는 `UNSUPPORTED` 기본값을 유지한다. 2a 이후 실제 `bundle_auth`는 최종 owner head의 철회를 표시하지만 B2 반환값으로 이를 전달하지 않는다. B2 복사는 `archive_identity_only`이고 모든 운영 flag는 false다. 이 반환값에서 `미철회`나 `현재 사용 가능`을 추론하지 않는다. 후속 status adapter는 실제 최종 관찰을 새로 수행해 시각/head와 함께 표시하거나, 확인하지 못했다고 그대로 표시해야 한다. 새 default를 `NOT_REVOKED`로 바꾸는 방식은 금지한다. 철회된 보관 자료를 보존하는 것과 그 승인을 선발에 사용하는 것은 별개다.

## 2. B2b-1의 최소 수직 범위

새 `research_incidents.py`(strict 사건 형식·reducer), `research_incident_store.py`(독립 journal/head와 outbox), `research_incident_monitor.py`(실제 읽기 adapter), 관련 임시 저장소 회귀를 권장한다. 이름·정확 API·write pins는 구현 시작 시 작은 카드로 확정한다. 기존 `BaselineHead`·object store·protective journal에서 검증한 방법을 재사용하되 보호 관리 정책/승인 의미를 임의로 섞지 않는다.

1. **명시 target 등록:** 실제 정상 Store graph 또는 실제 검증한 detached archive manifest로 bundle/raw/object 참조를 읽어 대상과 dependency snapshot을 기록한다. 임의 dict의 `dependencies_verified=True`는 받지 않는다. 저장 위치·source backup·대상 정책·서명 문서 위치는 명시 configuration으로 받고 private path는 공개 결과에 넣지 않는다. 등록은 감시 범위 구성이지 연구/매매 승인 아니다.
2. **사용 직전 실제 검사:** 등록 target의 `read_raw/read_verified(require_backup=True)`와 필요한 source 검증의 실제 실패를 adapter가 포착한다. 예외 문자열 전체를 손상으로 분류하지 않고 고정 진단을 분리한다. bounded scrub은 같은 adapter를 호출할 수 있지만 첫 단위에는 daemon/자동 시작을 추가할 필요가 없다.
3. **손상 저장소 밖에 사건 확정:** 실패 사실·영향 범위·사용한 dependency snapshot·진단을 독립 journal/head에 기록한다. 그 전후에 손상 원본을 rename/delete/덮어쓰기 하지 않는다. 한 사건의 restrictive state와 최초 알림 intent는 같은 확정 transition에 묶는다.
4. **실제 sealed 선발 consumer 연결:** 새 incident-aware 진입점은 actual incident store와 등록 scope가 필수다. 초기 평가 전과 최종 결과 반환 전에 해당 bundle/raw/object/store의 현재 보류를 검사한다. 보류·journal 손상·head 누락·필수 등록 누락이면 관련 선발을 거절한다. `incident_store=None` 또는 `quarantined=False`로 우회하는 기본값을 만들지 않는다. 기존 direct 연구 API가 사건 상태를 검사한다고 표시하지 않고, 새 운영 연결의 모든 경로가 필수 adapter를 통하도록 별도 회귀로 확인한다.
5. **표시와 알림 대기:** 상태 조회는 검증된 journal replay 결과만 보여 준다. 전송은 fake adapter로 시험하고, 실제 Telegram·toast는 호출하지 않는다. 발생 사실·보류 범위·복구 단계·다음 조치만 표시하며 승인 완료나 거래 재개 버튼을 만들지 않는다.

이 단위에는 `release_quarantine`, `resume`, `arm`, `sell`, `adopt_head` 사건을 넣지 않는다. 정상 원본이 다시 보이더라도 저장된 보류가 저절로 사라지지 않는다. 따라서 **B2b-1 완료는 자동 복구 운영 완료가 아니라 지속 보류 consumer의 완성**이다.

## 3. 사건·의존 관계·저장 계약

### 영향 범위

- bundle 원본/manifest 손상: 해당 bundle, 연결 raw, 그 증거를 참조한 review/selection만 보류한다. 손상 후보를 빼고 같은 family를 정상 승인하지 않는다.
- 공유 object 손상: 실제 검증된 인덱스에서 같은 object reference를 사용하는 bundle들을 함께 보류한다. 아직 완전성을 확인하지 못한 해당 store consumer는 거절하되, 별도 store의 독립 연구를 전역 중단하지 않는다.
- catalog/head 손상: 해당 catalog를 신뢰해야 하는 모든 소비를 보류한다. 손상 catalog에서 새로 읽은 목록으로 영향 범위를 좁히지 않는다. 등록 이력의 확인된 관계와 `scope incomplete` 사실을 함께 남긴다.
- source review 또는 archive attestation 철회: 2a의 실제 signed owner 제한을 그대로 소비한다. 이를 데이터 손상이나 재다운로드로 해결 가능한 사건으로 바꾸지 않는다.
- 새 물리 경로의 동일 bundle: `bundle_digest/raw_digest/object identity`에 연결된 기존 보류를 계승한다. 새 폴더나 새 store ID를 만들었다는 이유만으로 문제없는 연구로 등록하지 않는다. 물리 사본 장애와 논리적 서명 철회는 별도 축으로 기록한다.

dependency index는 `store binding + 검증한 catalog/head + bundle/raw manifest digest + signed identity + object refs + consumer binding`의 관찰이다. `bundle → review → selection → deployment/session` 중 실제로 확인되지 않은 간선은 `unknown`이며 완성됐다고 표시하지 않는다. 첫 단위는 bundle/raw/object/store와 실제 sealed 선발 consumer까지 완성하고, deployment/session adapter의 미구현 상태를 명시한다.

### 독립 사건 기록

원 연구 store와 별개의 journal root, 별도 head root, 별도 버전 backup을 명시한다. 최초 빈 저장소/head는 operator utility가 명시 provision하며 runtime은 seed/재초기화하지 않는다. 복구 대상 catalog가 손상돼도 사건 기록은 읽혀야 한다.

최소 event는 schema, incident_id, sequence, previous_event_digest, subject/dependency commitment, category, fixed reason, trusted observed_at 또는 clock-unavailable 구분, evidence reference, immutable transition payload, outbox intents다. 전체 parser는 bounded bytes/rows/depth와 exact 타입·알려진 enum을 검사한다. 로컬 시간 오류는 상태 순서를 되돌리거나 정상 timestamp를 덮지 않는다. 원문 계좌값·키·private path·예외문은 journal의 공개 projection에 넣지 않는다.

append → fsync/readback → 실제 direct-successor 확인 → 별도 head CAS → replay 검증 순서를 고정한다. journal/독립 head 한쪽 rollback, partial append, root/lock replacement, quota 초과는 거절한다. 기록 실패 시 해당 consumer는 메모리상으로도 거절하고 `사건 기록 미확정`을 알리며 계속 진행하지 않는다. 재시작은 필수 incident store를 검증하지 못하면 관련 새 선발을 시작하지 않는다. 저장 용량을 확보하려고 원본·정상 호가·보유 내역·기존 사건을 삭제하지 않는다.

이 로컬 chain/head 구조가 동일 사용자 권한으로 두 위치를 함께 바꾸는 공격이나 모든 매체의 coherent rollback까지 막는다고 주장하지 않는다. 기존 BaselineHead의 명시적 한계와 Windows native 검증 범위를 유지한다. 더 강한 trust anchor는 별도 설계이며 이번 단계에서 임의로 추가된 사용자 승인 요구가 아니다.

### 진단 분류

| 실제 관찰 | 기록/대응 |
|---|---|
| missing 필수 파일·잘린 기록·형식/해시/reference 불일치 | `INTEGRITY_FAILURE`; 의존 범위 보류, exact 복구 후보 |
| 일시 I/O/잠금/접근 거절 | `READ_UNAVAILABLE`; 현재 사용 거절, 원본 손상이라고 확정하지 않음. 재검사는 별도 관찰이며 기존 사건을 삭제하지 않음 |
| 용량·시간·평가 registry admission 초과 | `RESOURCE_LIMIT`; 손상/정상 평가 탈락으로 위장하지 않음. 원본 보존, 후속 시도 조건 표시 |
| 정상 기록된 조회 실패·중단된 연구 | `CAPTURE_ABORTED/RECORDED_UNAVAILABLE`; 해당 raw는 보관 가능하지만 완전 verified 연구로 승격하지 않음 |
| signature 만료/철회·code/key 변경 | `AUTHORITY_NOT_CURRENT`; byte 복원 성공과 분리. 기존 철회·halt·한도 효력을 유지 |
| 수치상 부적격·적격 후보 없음 | 정상 연구 평가 결과; 이를 storage incident나 복구 대상으로 만들지 않음 |

예외 종류만으로 네 단계 중 ② 또는 ③으로 자동 이동하지 않는다. 당시 자료의 완전성과 원본 복구 가능성을 별도 검사해야 한다.

## 4. 다음 두 단위와 네 단계 복구

**B2b-2: 사건에 연결한 exact 복구 controller.** B2b-1 통과 후, 명시 등록한 서명 후보/backup source/이미 provision된 목적지를 대상으로 실제 `restore_signed_backup`을 호출한다. signature discovery는 등록된 별도 원문 보관 위치만 bounded 탐색한다. 손상 폴더의 임의 key/manifest, 인터넷 재조회 또는 working copy로 trust fallback하지 않는다. 서명 bytes와 원래 target/domain을 실제 provider로 매번 확인한다.

복구 호출 전에 `ATTEMPT_STARTED`를 독립 journal에 확정하고, 중단 후에는 실제 목적지 target와 signature artifact를 재읽어 `PARTIAL/EXACT_ARCHIVE_RESTORED/REFUSED`를 구분한다. 같은 incident/document/content의 exact 재시도만 이어가며 partial row/head를 잘라 맞추지 않는다. 성공 반환이 journal에 기록되기 전에 종료돼도 다음 시작은 실제 전체 검증으로 상태를 재구성한다. caller가 만든 RecoveryResult는 완료 증거가 아니다. 재시도는 bounded 횟수/명시 backoff를 사용하며 provider의 key/code/head latch를 재생성해서 같은 작업의 거절을 우회하지 않는다.

**B2b-3: 복구 사실과 현재 연구 검토를 연결.** exact 복원 확인 뒤 destination에서 B1b-2b/c의 전체 실제 sealed 평가·source/factory·현재 철회/expiry 검증을 수행한다. 이전 SealedSelectionAssessment를 재사용하지 않는다. 성공해도 이 단계는 검토 사실이며 주문 권한이 아니다. 지속 보류를 풀거나 정상 소비 경로를 새 물리 사본에 연결하려면 독립 incident head와 exact replacement binding을 소비하는 별도 검증 transition을 구현한다. 그 transition은 새 승인·세션 arm·halt 해제·위험 하한 변경을 하지 않으며, 실제 운용 consumer가 이를 읽기 전에는 `복구 후 운영 재개 완료`로 표시하지 않는다. 단순 result bool이나 새 디렉터리 등록으로 해제하지 않는다.

| 판단 단계 | 구현 연결 및 결과 | 승인 의미 |
|---|---|---|
| ① 정확 원본 복구 | B2a 실제 전체 backup 검증과 별도 목적지 복원, B2b 사건/알림 연결. 실패 raw도 원 상태로 보존 | 원래 bytes·서명 대상·scope·유효기간·철회·현재 code/key/규칙/출처·factory 조건이 모두 유지되면 **복구만을 이유로 새 서명을 요구하지 않는다**. 결과 알림만 생성. 복구 시각으로 신선도·효력 연장 금지 |
| ② 새 버전 재구성 | exact 원본은 찾지 못했지만 온전한 기초 자료가 입증될 때 새 run/revision/evaluator version과 parent lineage로 재계산 | 기존 확정본 덮어쓰기/기존 승인 승계 금지. 전체 후보·실패 기록과 새 검증 결과를 포함하는 새 승인 요청 필요 |
| ③ 새 연구 재실행 | 당시 필수 호가/시각/지연/실패/후보 기록을 입증할 수 없을 때 새 등록·관측·평가 | 재다운로드한 자료를 당시 원본으로 가장하지 않음. 새 연구·새 승인 |
| ④ 사용 중단 | 복구·재구성·재실행 불가 또는 사용자 중단 선택 | 원인/잔여 자료/실패 시도 유지, 해당 의존 선발만 제외. 자동 청산이나 전역 자료 삭제 아님 |

네 단계는 판단 순서이며 모든 사건이 끝까지 진행해야 하는 workflow가 아니다. 아직 찾지 못한 exact 사본이 있다는 가능성과 현재 지원 adapter가 복구할 수 없다는 사실을 구분한다. `현재 signature 인증 불가`를 `원본 영구 소실`로 단정하지 않는다. 현재 B2는 current key/code/expiry를 요구하므로 historical-key·만료 서명의 보관 복구는 미지원이다. 이때 원본을 보존하고 해당 제한을 명시하며, 새 서명을 받아 같은 자료였다고 소급 증명하는 우회는 하지 않는다.

개발로 deployment D14 hash나 실제 source closure가 바뀌면 과거 실서명을 새 코드 승인으로 옮기지 않는다. 필요한 코드/자료 검토는 실제 binding 변경 때문이며, exact 복구 자체의 재서명 의무와 다르다.

## 5. 상태와 알림 인터페이스

단일 `recovered=True` 대신 독립 상태를 표시한다.

- **자료:** 검증 실패 / 읽기 불가 / exact 복원 검증됨 / 새 버전 검증 필요.
- **보류:** 관련 새 선발 보류 / 복구 사실은 있으나 보류 해제 검증 전. 첫 단위에는 해제 상태를 발급하지 않는다.
- **현재 검토:** 미검사 / 거절 및 고정 사유 / 특정 owner head·시각에서 검증됨. 영구 사용 permit 아님.
- **보유 관리:** 독립 유효 자료와 권한으로 감시 중 / 감시 가능하나 전략 판단 불가 / 계좌·미체결·주문 경로 확인 불가 / 권한 만료로 자동 주문 불가. incident adapter 혼자 이 사실을 만들어 내지 않음.
- **알림:** 대기 / 전송 확인 / 실패 / 결과 불명. 연구·복구·승인 상태와 별개.

`NotificationIntent`는 incident/transition에 domain-separated digest로 연결한 message ID, kind, 대상의 짧은 공개 식별자, 고정 상태/사유, 다음 절차, 요청이 필요한 경우 정확한 새 요청 ID만 담는다. 개인키·거래소 주문키·생체정보·기기암호를 저장하거나 전달하지 않는다. 원 서명/원본 연구도 메시지에 첨부하지 않는다.

outbox는 사건 확정과 함께 영속화한다. 전송 attempt ID와 `delivered/failed/unknown`을 append하며 동일 attempt 결과 재기록은 멱등, 모순된 결과는 거절한다. unknown/failed는 새 attempt로 재시도하되 같은 message ID를 유지한다. 외부 전송 직후 영수증 기록 전에 중단되면 중복 전달 가능성을 사실대로 남기며 exactly-once 전송을 주장하지 않는다. 전달 성공·클릭·미응답은 승인이나 보류 해제가 아니다.

첫 구현은 `list_pending_notifications`/`record_delivery_attempt`와 fake transport까지만 검증한다. 이미 있는 ToastQueue는 표시용 adapter로 추후 사용할 수 있으나 durable outbox를 대체하지 않는다. Telegram 연동은 별도 명시 전송·운영 설정 단계다. 이번 작업은 실제 메시지 발송을 요청하거나 수행하지 않는다. WebAuthn/Face ID 승인 경계도 기존 통합 설계 그대로이며 이 단계에 구현됐다고 표시하지 않는다.

exact 복구가 끝났으면 `원본 복구 검증됨 / 현재 검토 미확인 또는 확인 결과 / 관련 보류 상태`를 결과 알림으로 보낸다. 새 버전·새 관측·변경된 서명 대상에는 별도의 새로운 승인 요청을 만든다. 이미 유효한 기존 서명을 재사용할 수 있는 경우 새 승인 요청을 중복 생성하지 않는다.

## 6. 보호 보유와 주문 경계

자료 손상·저장 장애·복구·재시작은 전략 매도 신호가 아니다. incident는 해당 연구의 신규 선발/진입 근거를 제한한다. 매도 판단은 현재 유효한 독립 전략/위험 자료, 실제 계좌·미체결 대조와 해당 관리 권한을 기존 gate가 확인할 때만 가능하다. 자료 없음은 `판단 불가`이며 상승 예상이나 전략상 HOLD로 표현하지 않는다.

첫 단위는 보호 reducer에 `AuthorityFacts(accepted=True)` 또는 `ObservationFacts(recovery_complete=True)`를 임의 공급하지 않는다. 이미 보유 중인 자산의 관리는 해당 연결을 완성한 후 검증된 실제 facts adapter가 담당한다. incident journal 장애 자체가 주문 실행 가능성을 만든다고 가정하지 않는다. 독립된 유효 관리 경로가 있으면 그 범위의 감시는 유지하고, 그렇지 않으면 관리 불가를 알린다. 기존 손실 하한·daily loss·halt·권한 만료를 완화하지 않는다.

확정된 E 결정도 그대로다. 기한 도래만으로 매도하지 않고 신규 진입을 막고 새 관리 승인을 요청한다. 기존 권한이 유효한 동안 그 범위만 사용하고, 만료 후에는 자동 주문 없이 읽기 감시/알림·인계 상태다. 복구는 기한이나 권한을 연장하지 않는다. 첫 단계에서 account-wide liquidation/global halt를 새로 호출하지 않는다.

## 7. 최소 검증과 완료 판정

B2b-1은 순수 reducer 검사만으로 완료하지 않는다. **실제 임시 BundleStore와 독립 incident journal/head → 실제 파일 손상 → 사용 직전 실제 reader 거절 → durable 의존 보류 → sealed 선발 거절 → fake 알림/outbox 재시도**를 연결해야 한다.

1. 실제 독립 두 연구 A/B에서 A만 손상시키면 A만 보류하고 B의 실제 정상 읽기/검토는 유지. shared object와 catalog/head 손상에서는 정확한 공통 의존 범위만 확장.
2. 정상 unavailable/aborted raw, 수치 탈락, quota, I/O, hash 손상을 구분. 뒤 후보 손상에서 앞 후보만 정상 선발하지 않음.
3. detector 후/append 중/head CAS 전후/outbox 전후마다 중단. journal/root/head 단독 rollback, lock/root 교체, partial rows, 양 플랫폼 경로 경계, 수명·quota를 거절. 재시작 시 열린 사건을 잊지 않음.
4. 실제 원본을 고치거나 새 경로에 exact 복사해도 v1 보류가 자동 해제되지 않음. 새 폴더·새 store ID·caller assessment·false bool로 우회 불가.
5. 통합 후속 검사에서는 기존 B2 actual 복원/backup/서명 artifact를 사용. partial restore/retry를 정확히 표시하고 final graph/owner 철회·expiry·code change로 정상 사용 상태를 만들지 않음.
6. outbox 전송 실패/unknown/duplicate/restart에서도 사건·보류·승인 상태 불변. 실제 Telegram/네트워크/owner private key/API/order 호출 0.
7. 보호 관리 독립 facts가 없는 동안 incident가 HOLD/SELL/approval을 합성하지 않음. 정상 호가·보유 내역·탈락 후보·원 사건 bytes 보존.

19 KEYLESS·임시 homes/일회용 서명·fake 시장 자료로 실행한다. 테스트 중 registry는 fixture별 원래 기록을 보존·복원하며 production에서 비우지 않는다. Linux synthetic path 검사를 실제 Windows durability나 계좌 장애 사례로 보고하지 않는다. 최종 root가 source 동결/fingerprint/guard/관련 회귀를 기록하고, 이 문서 자체에는 새 PASS 수를 적지 않는다.

## 8. 사용자 입력과 남은 결정

**B2b-1 코드·fake 장애 검증을 시작하는 데 새 사용자 결정은 없다.** 기존 손실 하한, 전역 청산 금지, 정확 복구 조건부 무재서명, Telegram은 알림이라는 요구를 다시 묻지 않는다. journal 형식·bounded admission·idempotency·기본 retry 정책은 위 요구 안에서 구현자가 구체화한다.

실제 배포 때에는 이미 이전 문서에 남아 있던 비동기화 확정/백업 매체와 별도 incident/head 위치, 사전 provision 복구 목적지, 신뢰 가능한 서명 보관 위치를 실제 PC에서 설정해야 한다. 실제 Telegram 대상/전송 자격 및 HTTPS/RP/독립 승인 trust 설정은 그 연동 단계에서만 필요하다. 이 정보가 없다고 임의 실경로나 계정으로 설정하지 않으며, 공개 로그에는 개인 경로·금액·비밀값을 쓰지 않는다.

재구성/재실행/사용 중단 중 당시 선택이 필요한 실제 사건이나, historical-key 복구 trust를 새로 도입하는 단계가 생기면 그때 **새로 필요한 선택만** 제시한다. 현재는 사건도 실자료도 조작하지 않았으므로 사용자에게 추가 승인 질문을 만들지 않는다.
