# P2 I3b — 전체 수집 패킷의 불변 보관·재시작 감사 재현

2026-11-13. **읽기 기반 설계이며 구현·실계좌 수집·검사 실행·운영 승인 기록이 아니다.** 근거는 I3a가 병합된 main `68240cc`와 이를 포함한 작업 기준 `24c51f6`의 실제 소스다. 동결 중인 recovery-controller 소스·테스트는 수정하지 않았다.

추천 최소 단위는 **I3b-archive: I3a가 메모리에 보존한 전체 수집 패킷을 실제 private 불변 저장소에 보관·백업하고, 새 프로세스에서 원문을 복원하여 동일한 collector/guard-material 감사를 재현하는 연결**이다. 기존 계획의 I3b에 있던 생산 source 인증까지 완료했다고 표시하지 않는다. 출처·연속 자료 완전성의 실제 issuer와 pre/post owner 인증은 별도 미완료 조건으로 유지한다.

## 1. 실제 경계와 재사용

| 현재 파일/API | 실제 가능한 것 | 이 단위의 처리 |
|---|---|---|
| `account_interval.py:ContinuousUpbitCandidateSource.collect` | 원 anchor/coverage/fees, collector 내부 시작·완료 시각, raw SourceReceipt, captured accounts, path/preview/endpoint를 `StagedContinuousCandidate`에 분리 보존 | actual collect 반환물을 보관 adapter에 연결. 기존 callable live 거절은 유지 |
| `account_interval.py:StagedContinuousCandidate`, `ContinuousCapture` | 전체 메모리 snapshot이며 `execution_ready=False` | typed packet의 정확한 입력. 새 프로세스에서 읽을 codec은 현재 없음 |
| `guard_capture_material.py:prepare_guard_capture_material` | 원 receipts를 actual `collect_upbit`로 순서대로 재소비, captured/endpoint·manifest·path/coverage·FIFO/fees를 타입까지 재대조 | archive readback으로 복원한 typed stage와 원 previous baseline에 그대로 적용. hash만 맞추는 별도 계산기를 만들지 않음 |
| 같은 파일 `_admit_receipts/_admit_tree/_same` | JSON/deepcopy/계산 전에 크기를 제한하고 bool/Decimal/string 치환·추가 dataclass 속성을 거절 | 재사용할 사전 admission 및 의미 비교. private helper를 사용한다면 codec과 공동 회귀로 계약 고정 |
| `continuous_archive.py:archive_candidate` | 현재 state_root 아래 path-only 파일. `O_EXCL`·readback·fsync, exact retry; 부분 파일은 거절 | 기존 감사 기록 의미 유지. full packet이나 독립 restart head로 재해석하지 않음 |
| `execution_accounts/model.py:canonical/content_digest` | 기존 증거 hash의 canonical 표현 | legacy digest 계산 그대로 사용. Decimal/string·dataclass 종류를 구별하는 복원 codec이 아니므로 새 typed archive decoder를 대신할 수 없음 |
| `baseline.py:state_json/restore_state` | 이전 BaselineState의 기존 strict checkpoint bytes/expected hash 검사 | 원 predecessor snapshot payload를 그대로 보존·재해석. packet 안의 self-hash는 현재 trusted baseline head가 아님 |
| `evidence_objects.py:EvidenceObjectStore` | lossless chunked bytes/reference, bounded publication/readback; 부분 final은 확정 증거가 아님 | 아래 실제 BundleStore 내부 사용 그대로 재사용 |
| `research_bundle_store.py:BundleStore.archive_raw/read_raw(require_backup=True)` | 전체 파일 manifest·primary/backup·catalog·독립 retained head를 연결, exact retry/부분 publication 거절 | **새 저장 엔진을 만들지 않고 이 실제 RAW_ARCHIVED 경로를 재사용**. 계좌 자료는 `other_input` 역할의 감사 원본이며 연구 평가/승인과 무관 |
| `continuous_guard_commit.py`, `CommittedAccountProvider`, Controller/Runner/Coordinator | 별도의 plan/commit/actual tx 소비 경계 | 이번 단위에서 호출·변경하지 않음. archive 성공은 guard commit/publication 준비 완료가 아님 |

I3a의 실제 274 PASS 기록은 원본 보존/material 재현 검증이다. 새 codec·backup·restart 동작을 검증한 결과로 재사용하지 않는다.

## 2. 작은 파일·API 범위

새 `guard_capture_format.py`는 닫힌 typed codec과 전체 payload inventory만 담당한다. 새 `guard_capture_archive.py`는 actual BundleStore 저장/readback과 I3a 감사 재현을 연결한다. 별도 실제 임시 저장소 통합 검사를 추가한다. account model, 위험 reducer, source verifier, 실행 provider, 기존 연구 서명 형식은 바꾸지 않는다.

구체 시작 계약은 다음이 적당하다. 구현 전 카드에서 이름/필드·exact bytes를 확정한다.

```python
# Pure codec. No source verifier, file, owner or clock read.
build_capture_archive(staged, previous, *, storage_limits) -> EncodedCaptureArchive
parse_capture_archive(manifest_bytes, payloads, *, storage_limits,
                      expected_previous_state_sha256) -> RetainedCapturePacket

# Actual persistence; no default root/home and no runtime provisioning.
archive_guard_capture_packet(store: BundleStore, staged, previous) -> CaptureArchiveReceipt
read_guard_capture_packet(store: BundleStore, archive_digest, *,
                          expected_previous_state_sha256) -> RetainedCapturePacket
replay_guard_capture_archive(store: BundleStore, archive_digest, *,
                            expected_previous_state_sha256) -> ArchivedCaptureReplay
```

actual consumer 경로도 같은 단위에서 제공한다: `ContinuousUpbitCandidateSource.collect`의 실제 반환 stage를 `archive_guard_capture_packet`에 전달하고, **반환된 actual archive digest로 다시 읽은 내용만** `replay_guard_capture_archive`에서 재현한다. 별도 작은 wrapper/호출점으로 연결하고 기존 collect의 in-memory API와 path-only archive를 몰래 full-durable API로 바꾸지 않는다. 테스트가 codec만 호출해 통과한 것을 수직 완료로 보고하지 않는다.

Receipt에는 packet digest, 실제 RAW_ARCHIVED digest, original capture/path/predecessor/material 식별자, observed catalog head/sequence와 backup 완료 사실만 둔다. 모두 해당 관찰의 보관 사실이다. `source_authenticated`, `current_freshness_verified`, `guard_committed`, `execution_ready`는 false다. 사용자 원 계좌값·scope·private 경로·raw 응답을 public 출력에 넣지 않는다.

## 3. 패킷과 lossless codec

하나의 `RAW_ARCHIVED` manifest 안에 아래 **완전한 생성 파일 목록**을 고정한다. names는 metadata이며 외부 경로로 사용하지 않는다. 원 HTTP raw_body는 canonical JSON으로 다시 쓰지 않는다.

- `baseline.json`: 기존 `state_json(previous)`의 exact bytes. predecessor digest·schema에 연결한다. 초기화나 현재 baseline head adoption에 사용하지 않는다.
- `packet.json`: schema/replay revision, exact stage typed fields, 순서가 있는 receipt metadata와 raw logical ID/length/SHA, 원 baseline/path/collector manifest commitments. 원 anchor/collection coverage/fees, collection_requested_at, collector의 두 시각, preview observed_at을 모두 포함한다.
- `receipt-000000.bin` …: 같은 collect 호출의 **모든 raw 응답 bytes**, 순서·path·params·scope·received_at·server_time·SHA 연결. 같은 bytes가 반복되어도 receipt 위치·요청·시각 row를 제거하지 않는다. 저장 object가 dedup되는 것과 관찰 이력을 dedup하는 것은 다르다.

`packet.json`의 typed stage는 captured accounts와 reconstructed endpoint accounts, ContinuousPath 전체 events/opening marks/sequence/watermark, retained VerifiedCoverage, preview interval/valuation을 구분한다. 임시 자정 collector `RiskBaseline`/AccountBundle을 새로 저장하지 않는다(R6). 원 collection_baseline_sha256만 그대로 두고 I3a가 같은 이전 상태·원 시각으로 다시 도출한다.

새 codec은 명시 allowlist의 exact class/field schemas를 사용한다. 임의 클래스명 import, pickle, eval, reflection-based 객체 생성은 금지한다. Decimal은 원래 부호·자릿수·지수/scale을 재현하는 제한된 typed 표현을 사용하고, 기존 계산 hash에는 원 `content_digest`를 적용한다. JSON number/float나 문자열 치환으로 Decimal 타입을 잃지 않는다. tuple과 필드 순서, bool/int, optional `Position.unlisted=None`, datetime/date도 exact 구분한다. 시각은 원 instant를 canonical UTC로 표현하되 원 수집 시각을 새 시각으로 바꾸지 않는다. 원 raw JSON whitespace·number spelling·배열 순서는 raw payload에 그대로 남는다.

새 `packet_digest`는 별도 `tradegen-continuous-capture-packet/1` domain으로 typed metadata와 ordered **전체** payload SHA/length를 묶는다. legacy path/capture/material digest와 같다고 가정하지 않는다. metadata에 넣은 authority/source_proof SHA는 원래 callback의 주장 식별자이며 서명이나 실제 issuer 인증으로 승격하지 않는다.

### 한도

I3a의 실제 한도(2,000 receipts, 개별 8 MiB, raw 합계64 MiB, rows100,000, path events20,000, symbols64, typed depth/nodes/Decimal 범위)를 유지한다. JSON byte/depth/node 및 declared fields를 객체 생성·deepcopy 전에 제한한다.

receipt 2,000개+metadata/baseline 2개는 기존 BundleLimits max_files2,048 안에 들어간다. typed metadata는 기존 단일 payload의 64 MiB ceiling, 전체 파일은 설정된 manifest/total/object/store budget 안에서 사전 검사한다. raw64 MiB와 별도로 metadata 크기도 합산하고 primary+backup·temporary peak를 기존 admission에 반영한다. 기존 format manifest 한도4 MiB도 그대로다.

I3a에 적합한 모든 이론적 최댓값이 이 archive 설정에도 무조건 들어간다고 보장하지 않는다. 한도 초과는 저장 admission 거절이며 원 stage/raw를 줄이거나 정상 호가·보유 내역을 None으로 바꾸지 않는다. 여러 chunk의 임시 final을 ‘확정 패킷’으로 표시하지 않는다. metadata 분할이 실제 경계 검사에서 필요하면 별도 format revision으로 설계한다.

## 4. 보관 성공과 감사 성공을 분리

구조·타입·필수 inventory·raw length/hash가 확인된 패킷은 RAW_ARCHIVED로 exact 보관할 수 있다. 원본을 보관하기 위해 새 source 인증·전략 평가를 통과한 척하지 않는다. 보관 후 실제 I3a 재현에서 불일치가 발견되면 해당 raw archive를 유지하고 **감사 거절**을 표시한다. 성공한 packet만 남기려고 원본을 지우거나 내용/claim을 고치지 않는다.

이 첫 단위의 입력은 I3a가 반환한 완성된 stage다. 실제 collector가 중간 예외로 반환하지 않은 raw receipts나 애초 수집하지 않은 upstream proof를 복구해 준다고 주장하지 않는다. 표현 불가/한도 초과로 archive 자체가 거절된 자료는 확정본이 아니며 caller의 원 작업본을 보존한다. 중단 수집기의 partial receipts를 외부로 발급·저장하는 기능은 별도 후속이다.

실제 읽기는 BundleStore 전체 manifest/file set과 primary/backup을 확인한 뒤 typed decode를 수행한다. receipt 누락·추가·순서 바꿈·params 변조·hash만 재계산한 계좌 바꿔치기·불완전 path를 감사에서 거절한다. 모든 원 receipt를 기존 actual `collect_upbit`의 bounded in-memory replay source가 정확히 한 번 소비해야 한다. preview와 material은 기존 I3a로 다시 계산하며 stored derived material을 권위로 받아들이지 않는다.

## 5. 재시작: 역사 재현과 현재 신선도

새 프로세스가 몇 시간 뒤 패킷을 읽는 것은 정상적인 **역사 감사**다. I3a의 `prepare_guard_capture_material(..., now=...)`는 30초/서울 날짜 경계를 적용하므로 실제 현재 시각을 넣으면 오래된 패킷은 거절되는 것이 맞다.

`replay_guard_capture_archive`는 archive에 보존된 원 preview 시각을 **명시적인 historical audit evaluation time**으로 사용해 당시 입력으로 같은 material이 재현되는지 검사한다. 반환에는 원 관찰 시각과 `historical_replay=True`, `current_freshness_verified=False`를 명시한다. caller가 `now`를 조작해 이 경로를 운영 신선도 검사처럼 쓸 수 있는 옵션은 두지 않는다.

향후 현재 consumer는 실제 trusted completion clock으로 별도의 freshness·source·owner 검증을 해야 한다. archive digest/backup/head와 historical material은 현재 계좌 증거·현재 baseline·source authenticity·approval을 만들지 않는다. 특히 원 path source의 completeness callback을 재호출하거나 새로운 VerifiedCoverage.verified_at을 발급하지 않는다.

predecessor는 외부에서 명시한 expected_previous_state_sha256와 exact 일치해야 한다. packet 속 baseline self-digest는 일관성을 검사할 뿐 trusted latest head가 아니다. 현재 baseline/guard/control predecessor triple을 실제 보존 head와 연결하는 작업은 I3c다. 여기서는 state advance/commit/CAS를 계좌/guard 저장소에 수행하지 않는다.

## 6. 실제 저장소와 중단 경계

새 packet 전용 실제 BundleStore를 명시 non-OneDrive primary/backup roots와 head-name·limits로 구성한다. 기존 store의 private-state/repo/sync-root/링크·reparse·hardlink/정체성 검사를 유지한다. 실제 별도 저장 장치인지 단순 별도 directory인지 구분하며 자동으로 물리적 독립성을 주장하지 않는다. 현재 BundleStore head는 backup root 아래에 있으며 primary와 분리된다. 서로 다른 모든 매체의 coherent rollback을 막는 외부 anchor는 현재 없다.

처음 빈 저장소/head는 기존 owner operator utility의 명시 준비 경로만 사용한다. packet runtime은 seed/provision/adopt하지 않는다. source 수집이나 계좌/guard Journal lock을 잡은 채 archive lock을 요청하지 않는다. archive commit/readback을 모두 닫은 뒤에만 감사 결과를 반환한다.

| 중단 위치 | 재시작 시 의미와 처리 |
|---|---|
| object staging 중 | 임시/partial final은 미확정이다. 원 bytes를 보존하며 자동 삭제·수리하지 않는다. 남은 partial이 안전한 exact retry를 막으면 고정 미완료 진단 |
| 정상 PRIMARY_COMMITTED, backup 아직 없음 | `require_backup=True`로 확정 패킷 반환 금지. 같은 manifest·파일 bytes의 기존 archive_raw 재시도만 허용되는 상태인지 actual store가 판정 |
| backup 전체 검증과 BACKUP_VERIFIED/head 확정 | actual read_raw(require_backup=True)로 전체를 재검증한 후만 재시작 복원 가능 |
| catalog append/독립 head 불일치 또는 orphan/torn 기록 | 기존 store 거절. 파일 길이를 줄이거나 최신처럼 head를 따라잡지 않음 |
| 정상 완료 뒤 응답 유실 | 동일 packet의 결정적 run/revision/manifest identity로 actual store exact retry; 새 복사/새 시각으로 재발급하지 않음 |
| 외부 저장 실패/한도 초과 | 원 stage·작업본 유지, archive 미확정 표시. 신규 패킷을 정상이라고 노출하거나 정상 관측을 삭제하지 않음 |

archive identity는 packet digest에서 결정적인 run/revision을 도출하고 codec/replay revision을 고정한다. 서로 다른 bytes를 같은 ID에 덮어쓰는 시도는 거절한다. 새 re-collection/recalculation은 새 packet·새 archive identity다. 기존 EvidenceObjectStore의 partial final 가시성은 원자적 확정이 아니며, catalog+backup+head 검증이 전체 publication 경계다.

## 7. 실제 완료 검사와 남는 차단

최소 수직 검사는 **실제 fake-GET collector→actual recorder/path→I3a stage→actual BundleStore primary/backup/head→모든 메모리 객체 폐기/새 reader→full typed decode→actual collector/material replay**다. source/coverage fixture는 합성이라고 명시하고 실제 API·키·홈·주문은 사용하지 않는다.

- flat/held/partial-fill, 22시·자정 boundary에서 captured/endpoint 구분과 원 두 collector 시각·fees·원 raw bytes·path event 전부 roundtrip.
- Decimal scale/typed bool·int·string, optional field, duplicate JSON keys/extra fields, source raw number spelling/whitespace 보존과 rehashed substitution 거절.
- 누락/추가 receipt·page·fill·fee·호가·보유 종목, path discontinuity/epoch/watermark, scope/request 순서 불일치 거절.
- archive가 성공했으나 감사가 실패한 raw 원본도 유지. 실패가 source authenticity를 새로 발급하지 않는지 확인.
- 시간 지난 뒤 historical audit는 같은 material을 재현하되 실제 현재 freshness 경로는 stale 거절. clock/verified_at relabel이나 completeness callback 재호출 없음.
- 각 publication 단계 중단·재시작·exact retry, one-sided rollback, root/lock/head 교체, quota 경계, temporary partial 보존·no auto seed/adopt.
- 저장·읽기에서 공개 출력에는 bounded IDs/status만 남고 계좌값·raw scope·private 경로가 노출되지 않음.
- `ContinuousUpbitCandidateSource.__call__`, controlled Coordinator/carry Runner 거절 유지. account/guard baseline의 high/floor/daily stop/halt·손실 한도 값과 source/owner 승인 정책 불변.

**I3b-archive 완료로 표시할 범위는 ‘원본 패킷의 durable exact 보관·백업·재시작 감사 재현’뿐이다.** 실제 account identity/history retention, 연속 marks/fills의 venue completeness issuer, 당시 pre/post owner 관찰 인증, 처리 완료 시각/실제 send 경계, guard commit 뒤 publication과 exact Runner/Controller 소비는 남는다. Callback hash, 로컬 서명, raw digest, 봉인된 저장소 중 어느 것도 이 인증의 대체물이 아니다.

코드·hermetic 검증을 시작하기 위한 새 사용자 승인 질문은 없다. 실제 배포 위치·매체·source contract·원 승인 설정은 이후 명시 입력으로 연결하고 현재 실홈 기본값이나 가짜 권한을 넣지 않는다. 이 문서 작성에서 동결 runtime 소스·테스트와 위험정책은 변경하지 않았다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
