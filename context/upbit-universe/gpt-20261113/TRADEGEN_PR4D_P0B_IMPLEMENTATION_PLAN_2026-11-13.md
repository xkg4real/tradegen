# TRADEGEN PR4d P0b: 무손실 객체를 실제 history에 연결하는 구현 계획

작성: 2026-11-13. 기준: PR34 `a54a390` 원래 history 구현 및 P0a 커밋 `6be78659b164ba08334111f592a0bbbede32428b`. root 검증: P0a 집중24 PASS와 영향 회귀125 PASS, 모두0 FAIL/0 NOT_RUN. **이 문서는 읽기 전용 코드 대조 및 다음 구현 계획이며, P0b 구현·테스트·운영 연결 완료가 아니다. 구현 전에 독립 설계 검토가 필요하다.** 새 테스트나 소스 변경은 이 계획 작성 중 수행하지 않았다. 구현 전 독립 설계 검토가 필요한 계획이며 추가 운영 승인이 발급됐다는 뜻은 아니다.

## 1. 목표와 분리할 변경

P0b는 정상 호가·모든 보유 내역·정상 universe 입력을 버리지 않고, 실제 LiveHistory의 확정·재생·독립 head·검증기에 P0a 저장소를 연결한다. 저장 공간 때문에 `book=None`, flags/tickers=`unavailable`, allow=[]를 만드는 경로를 새 v3 window에서 사용하지 않는다. 정상적으로 관측된 조회 실패는 기존 의미로 기록한다. 기록 실패는 저장 오류이지 전략 SELL 신호가 아니다.

기존 손실 하한·일일 한도·halt·소유자 승인 요건은 변경하지 않는다. 마감 E만으로 매도하지 않고 갱신을 요청한다는 최신 사용자 결정은 확정된 요구다. 다만 현재 driver의 terminal target=0 정책과 보호 보유/A1 상태 전이까지 고치는 일은 **별도 행동 revision 단계**다. P0b 저장 연결이 이 정책을 이미 고쳤다고 표시하지 않는다. 새 보호 보유 행동이 연결·검증되기 전 실운영 준비 완료로 표시하지 않는다.

## 2. 직접 확인한 연결 지점

| 위치 | 현재 계약 | P0b 변경 필요 |
|---|---|---|
| `execution_launch/live_history.py:82` | universe 논리 슬롯은 `_SLOT_V2_KEYS`의 닫힌 필드 집합 | 이 논리 자료를 fallback 이전 상태로 온전히 저장하고 v3 참조 wrapper로 감싼다 |
| `live_history.py:728` | flags/tickers 폐기 후 chooser 재계산 | 새 v3 경로는 한 번 계산한 정상 입력 그대로 사용. legacy v2 원문 읽기는 유지 |
| `live_history.py:551` | journal lock 아래 크기 확인 → append+fsync → head CAS/readback | v3에서는 같은 history writer 직렬화 아래 quota admission·객체 staging을 append 이전에 연결 |
| `live_history.py:255`, `293` | `HistoryChain.successor`가 tail 행 해시·prev/new만 확인 | v3 tail 참조의 전체 객체 graph와 context binding 검증 후에만 sequence 반환 |
| `live_history.py:579` | replay는 row 구조, receipt, holdings, chooser와 head를 확인 | v3 참조 해석 후 같은 논리 검증 경로 사용; 참조 graph 누락/변조도 거절 |
| `live_history.py:648`, `771` | provider/verifier는 head와 journal 파일 크기를 확인 | v3 객체 변조는 journal 크기가 바뀌지 않으므로 참조 graph 검증이 추가로 필요 |
| `driver.py:36`, `156` | driver source manifest에 history/object 저장 모듈이 없음 | 신규 저장을 작동시키는 소스도 deployment code closure에 고정 |
| `driver.py:145`, `187` | FixedDriverIdentity의 7개 문자열 필드에 protocol/window digest 포함 | 기존 identity 필드 집합을 유지하면서 protocol digest를 통해 저장 정책을 bind 가능 |
| `strategy.py:101`, `138`, `605` | ForwardProtocol의 선택적 필드는 omit_none로 기존 encoding 보존 | 새로운 선택적 저장 정책 digest를 엄격하게 검증/직렬화 |
| `capability.py:24` | dataclass digest는 omit_none metadata를 무시 | DeploymentWindow에 선택 필드를 무심코 추가하면 기존 window digest가 바뀜. 피한다 |
| `coordinator.py:800` | HistoryChain/LiveHistory/fixed driver를 한곳에서 구성 | 같은 검증된 저장 정책을 세 경계에 전달 |
| `tools/owner/launch.py:154` | setup_history는 window만 받고 head를 GENESIS로 초기화 | 새 window에서 저장 정책 확인을 위한 명시 입력 연결. 초기화는 기존 operator 전용 유지 |
| `baseline_head.py:233` | CAS가 head lock 안에서 chain.successor 호출 | v3 resolver가 history lock을 재진입하거나 object lock을 잡은 채 head로 돌아가면 교착 가능 |

## 3. 구체적인 형식·identity 제안

### P0b-1. `HistoryStoragePolicy`와 선택적 protocol binding

새 표준 라이브러리 기반 순수 모듈 `execution_launch/history_storage.py`에 frozen 정책/codec를 둔다.

- 정책은 자신의 schema, history data revision=3, object format revision=1, P0a ObjectLimits 4개 값, window 총량 제한을 포함한다.
- 총량 제한에는 window에서 허용하는 물리 object bytes/object 수와 journal bytes를 포함한다. 소유자 실제 금액이나 절대 저장 경로를 정책 해시에 넣지 않는다.
- 정책 canonical bytes에 도메인 구분 해시를 계산한다. 전체 history 정책 digest와 `ObjectLimits.policy_sha256`는 서로 다르며 혼동하지 않는다.
- `ForwardProtocol.history_storage_sha256: str | None`, `metadata={"omit_none": True}`를 추가하는 방안을 채택한다. 값이 있으면 SHA-256 형식, 지원 revision, Upbit KRW 현물 universe 범위를 확인한다. 정책 원문은 명시적으로 읽어 해시를 대조한다.
- 기존 protocol에서는 이 필드를 생략하고 기존 `_plain`, `protocol_json`, `parse_protocol`의 strict optional 규칙을 이용한다. None을 명시한 JSON은 현재 규칙처럼 거절한다. 기존 evidence/protocol digest golden은 유지한다.
- FixedDriverIdentity 7개 필드와 `review_auth._IDENTITY` 형식은 그대로 둔다. 그 안의 `protocol_digest`가 저장 정책 digest를 포함한다. 별도의 새 서명키나 서명 형식이 필요하다고 가정하지 않는다.
- DeploymentWindow의 3개 필드는 바꾸지 않는다. 새 deployment_id/window와 새 head를 명시적으로 구성한다. 기존 창의 데이터 폴더를 v3로 재해석하거나 덮어쓰지 않는다.

검증: optional 생략 시 기존 protocol bytes/digest 동일, malformed/explicit-null/다른 정책 hash 거절, 저장 정책만 바뀌면 identity 달라짐, window digest는 기존 규칙 유지, 잘못된 venue/scope의 v3 거절.

### P0b-2. v3 header와 slot

control journal의 전역 `SCHEMA=1`이나 `MAX_ROW_BYTES=262144`는 변경하지 않는다. **history data의 revision**을 명시하는 것이다.

- 기존 bound 행: `data={"identity": <기존 7필드>}` 그대로 읽는다.
- 새 v3 bound 행: 닫힌 집합 `identity`, `history_version:3`, `history_storage:<정책 원문>`을 사용한다. 정책 원문의 해시를 protocol에 묶인 digest와 대조한다. 작은 header가 기존 행 한도를 넘으면 admission 거절한다.
- 새 v3 slot 행: 닫힌 집합 `history_version:3`, `index`, `payload_ref:<P0a PayloadReference>`를 사용한다. `prev_sha256`, `row_sha256`, `utc`, 순번은 기존 journal outer codec 그대로다.
- 객체 payload는 canonical wrapper로서 `schema`, `window_digest`, `driver_identity_digest`, `index`, `sampled_at`, `slot`을 포함한다. `slot` 안에는 **fallback 이전 `_SLOT_V2_KEYS` 논리 자료**가 그대로 들어간다. 이 wrapper로 다른 창·슬롯에서 같은 자료를 끼워 넣는 것을 거절한다.
- row.utc, wrapper.sampled_at, slot.index, envelope.index, 실제 grid와 sequence가 전부 같아야 한다. payloadRef의 ObjectLimits policy digest는 header의 object policy와 같아야 한다.
- 큰 호가의 원본 body base64나 보유 내역을 미리 잘라 넣지 않는다. 원본 raw body SHA와 wrapper/payload/manifest SHA는 서로 다른 해시다.
- 현재 flags/tickers는 파싱값+원본 해시만 전달된다. P0b가 과거 raw body까지 복원했다고 주장하지 않는다. PR5 신규 원본 capture 확장과 별도로 연결할 수 있다.

검증: cross-window/identity/slot/time 삽입 거절, 불필요한 필드·빠진 필드·중복 키·형식 혼합 거절, 정상 데이터의 canonical slot bytes와 chooser 결과 보존.

## 4. 실제 기록 transaction과 한도

### P0b-3. 새 window만 v3를 명시적으로 선택

자동으로 행 크기를 보고 v2/v3를 바꾸지 않는다. 창의 처음부터 한 형식을 고정한다.

- 새 universe 운영 창은 v3 정책 digest와 원문이 명시돼야 생성한다. 정책 누락은 설정 오류이며 old fallback으로 조용히 내려가지 않는다.
- 기존 v1 고정종목 codec 및 v2 원문은 그대로 읽고 검사한다. 기존 v2에 새 v3 행을 append하거나 과거 행을 바꾸지 않는다.
- 기존 코드·서명으로 돌아가던 창을 새 소스로 무승인 재개하는 것은 허용되지 않는다. 소스 closure가 바뀌면 identity도 달라지는 것이 정상이다. '파일 읽기 호환'과 '기존 승인으로 새 코드 실행'을 구분한다.
- 기존 v2 회귀 fixture는 원래 직렬화 bytes를 보관한 형태로 읽기 검증한다. 운영 생성 경로를 legacy 방식으로 열어 놓기 위해 회귀 테스트를 유지하지 않는다. v1의 기존 고정 frame/slot golden은 그대로 지킨다.

### P0b-4. history lock 아래 admission과 staging

순서는 다음과 같이 고정한다.

1. 정상 논리 슬롯/chooser 결과와 wrapper bytes를 메모리에서 계산한다. 상태를 바꾸지 않는다.
2. history 프로세스 lock 및 해당 history journal lock 아래 현재 head/size/sequence를 확인한다.
3. 전체 payload/청크 수/manifest 크기/envelope 행 크기/창 총량/남은 슬롯 상한을 검사한다. 모든 단순 admission 거부는 파일 생성이나 메모리 변경 이전이어야 한다.
4. dedicated per-window `payload-objects` root에 P0a `stage`한다. 모든 객체가 완전 검증된 뒤에만 reference가 반환된다. P0a의 final 파일명 노출은 원자적이지 않으며, reference 반환도 journal 확정이 아니다.
5. 참조 행을 append+fsync한다. 그 다음 기존 독립 head CAS/readback을 수행한다.
6. 성공 뒤에만 `_slots`, `_chain`, `_marks`, `_prices`, `_state`, `_inputs`, `recorded_allow`, `_head`, `_size`, `_seq`를 확정한다.

P0a는 전체 store/window quota 관리자가 아니다. P0b에는 다음 총량 처리가 필요하다.

- 정상 writer는 모두 같은 per-window history lock을 사용한다. object store는 창 전용이며 일반 모듈이 직접 쓰는 구성은 허용하지 않는다.
- 총량 admission은 확정 참조만 세지 않는다. 실패한 stage가 남긴 미참조 final object·임시 파일도 물리 사용량에 포함한다. bounded directory inventory로 최대 개수/크기/파일 형식/링크를 확인한다. 임계치보다 한 개 많은 지점에서 중단할 수 있어야 한다.
- 새 객체와 기존 검증된 객체의 deduplication을 계산해 실제 추가될 최대 bytes/objects를 예약한다. 임시 파일과 복사 중 final의 동시 공간도 포함한다. 이 작업을 외부 writer와 안전하게 직렬화할 수 없다면 별도 quota adapter/동일 lock 계약을 추가하고 완료로 표시하지 않는다.
- journal 총량도 append될 newline 포함 크기를 기준으로 검사한다. `MAX_ROW_BYTES`는 별도의 각 행 한도로 유지한다.
- stage 중 실제 ENOSPC/권한/fsync 오류는 사전 admission과 다르다. 임시·미참조 파일이 남을 수 있으며 자동 삭제하지 않는다. journal/head/전략 상태는 성공한 새 슬롯으로 바뀌지 않아야 한다.
- 새 write를 막는 pending 파일이 있다고 이미 확정된 무관한 reference 읽기까지 막지 않는다. 그 reference graph 자체가 손상됐으면 해당 읽기를 거절한다.

검증: payload/chunk/manifest/window bytes/window count/journal cap 각각의 바로 아래·동일·바로 위, dedup case, orphan이 남은 재시도, 두 writer 경쟁, 공간 부족·짧은 쓰기·fsync 거절, 모든 admission 실패에서 기존 journal/head/메모리와 디렉터리 snapshot 불변.

## 5. head successor·재생·실시간 검증

### P0b-5. lock 순서와 successor

잠금 순서를 문서와 테스트로 고정한다.

- 정상 기록: history lock → 객체 stage lock, 반환 후 해제 → head CAS lock → successor의 객체 read lock.
- `HistoryChain.successor`는 history lock을 다시 잡지 않는다. 기존 구조처럼 journal tail을 읽고, 그 참조의 완전한 graph와 context binding을 검사한다.
- object store lock을 잡은 상태로 head CAS를 호출하면 successor에서 같은 lock을 재진입하므로 금지한다. object reader에서 head를 다시 읽는 역방향 호출도 금지한다.
- v3 bound 행은 전체 정책과 identity 형식/일치성을 검사한다. v3 slot 행은 논리 자료 구조 및 context를 검사한 뒤 sequence를 반환한다. 단순 manifest hash 존재만 확인해서 head를 올리면 안 된다.
- 독립 `BaselineHead` 파일 형식/CAS 구현은 가능하면 그대로 유지한다. 이 단계는 chain validator 확장이다. 자동 seed/initialize/readback 채택을 새로 추가하지 않는다.

검증: 빠진 chunk/manifest 또는 잘못된 context일 때 head CAS가 거절되고 old head 그대로 유지, actual successor read 중 fault, 실행 제한 시간 안에 끝나는 lock/reentrancy 회귀, 서로 다른 창의 root 교환 거절.

### P0b-6. replay와 provider/verifier

- replay는 bounded row codec으로 header/row를 검증하고, v3면 object graph를 읽어 wrapper를 검증한 후 기존 논리 receipt/holdings/chooser 재계산 함수에 전달한다.
- 계좌 anchor, 모든 보유 내역, quote identity, 틱/시각, 누적 chooser state, 저장된 decision이 다시 계산한 값과 같아야 한다. 최종 independent head와 일치한 뒤에만 메모리를 설치한다.
- 재생 외에 provider/verifier의 신뢰 경계에서도 객체 변조를 확인해야 한다. 현재 `_durable_unchanged`의 journal size/head 검사는 객체 변조를 못 본다.
- v3 window의 검증 대상 prefix 전체를 실제 bytes/hash로 확인한다. 파일명·mtime·지난번 cache만으로 '같다'고 인정하지 않는다. 검증한 bytes와 전략 입력이 같은 immutable snapshot에서 왔음을 보장한다.
- prefix 검증 비용이 너무 크면 창 전체 처리량/슬롯 시간 측정을 한 뒤 별도 검증 가능한 최적화를 설계한다. 성능 때문에 재검증을 생략하지 않는다. 최종 slot의 원래 시간 경계는 유지한다.

검증: 같은 인스턴스에서 과거 chunk만 교체해도 다음 verifier가 거절, journal/head를 그대로 둔 manifest 변조 거절, reference 없는 orphan은 기존 frame 인증에 영향 없음, 마지막 프레임 뒤늦은 변조 포함, 객체 검사 도중 변경한 경우 검증된 입력 불일치 거절.

### P0b-7. crash 상태를 기존 head 계약과 연결

| 장애 위치 | 기대 결과 |
|---|---|
| 논리 admission | 아무 파일·journal·head·메모리 변경 없음 |
| temp/final 일부 객체만 존재 | 새 reference/슬롯 없음; 기존 무관 reference 조회 가능; 새 stage는 forensic pending 때문에 보류될 수 있음 |
| 전체 객체 완료, journal 없음 | 미참조 객체일 뿐. head를 바꾸거나 관측 슬롯을 채운 것으로 취급하지 않음 |
| journal append 일부/완료, head 미확정 | 기존 strict replay/head 불일치 거절 유지. tail 자동 채택·truncate·reseed 금지 |
| head 확정, 메모리 설치 전 | 확정 graph 전체를 재검증해서 복원; 파일 일부 손상이면 해당 history 보류 |
| 정확한 원본 백업 복구 | 기존 hashes/context/head를 전부 다시 검사. 시간 경과·승인 만료·missed-slot까지 자동 통과시키지 않음 |

무슨 저장 장애든 매도 신호를 합성하지 않는다. 계좌/미체결 대조 및 유효한 위험·전략 신호가 필요한 보호 보유의 다음 단계로 분류한다. 실제로 주문을 못 하는 상태는 '모형 HOLD'가 아니다.

## 6. 필수 재현·golden·검증 실행 순서

### P0b-8. 279531바이트 원본의 실제 연결 시험

기존 scratch 재현의 가짜 source로 1500개 보유와 131072바이트 정상 호가를 만든다. **fallback 전 실제 원래 outer row 크기 279531바이트**, fallback 후279312바이트였다는 과거 증거를 유지한다.

새 v3에서는 outer row가 작은 reference로 바뀌므로 row bytes/hash가 원래 v2와 같을 수는 없다. 그 차이를 숨기지 않는다. 다음을 비교한다.

1. 같은 입력에 대한 fallback 이전 논리 slot 자료를 확보한다. `_canonical(original_row["data"])`와 복원한 `payload["slot"]`의 canonical bytes가 정확히 같아야 한다.
2. receipt raw body bytes/hash, 모든1500개 holdings, 정상 flags/tickers, allow/reasons/events가 동일해야 한다. `SIZE_FALLBACK`이 새로 생기거나 정상 호가가 None이 되면 실패다.
3. 실제 LiveHistory.record_slot → durable reference → 실제 HistoryChain/BaselineHead CAS → 새 인스턴스 bind/replay로 이어지는 경로를 실행한다.
4. 같은 정상 논리 입력의 실제 `_derive_universe` 결과(bar, decision, history digest, prices, chooser state/inputs/choice)와 재생 결과가 같아야 한다. 현재 계좌/호가 검증을 건너뛴 임의 문자열 저장 테스트만으로 완료 처리하지 않는다.
5. 용량 초과/다른 정책/손상 객체를 넣은 실패는 journal/head/전략 상태를 확정하지 않아야 한다. 실제 계좌 장애가 아니라 합성 경계 재현으로 보고한다.

### 유지할 기존 golden

`tests/launch_live_history.py:518` 및 `:519`:

- 고정 frame: `59a151ab1b66133c71c030384df91a391178417f9249ec8a34a00558d4e16587`
- 고정 slot-data: `1354351db76d3a43b7e7ed508ae77fd98e3c22698cc70fefa1168c2b80c8bde8`

기존 v2 malformed 17가지, fixed window universe 입력 거절, 원래 head mismatch/identity binding/slot-clock 회귀도 유지한다. 기존 golden을 새 계산 결과로 덮어써서 통과시키지 않는다.

### 실행 순서

1. 순수 정책·codec 및 P0a 24개 회귀.
2. 실제 history record/replay/driver + 신규 v3 회귀와 기존 v1/v2 fixture 검증.
3. source closure/AST writer pins/negative mutation guard와5개 안전 경계 suite.
4. frozen source에서 필요한 전체 회귀. 앞선 원래 PR34 full 또는 P0a 집중 결과를 P0b 결과로 쓰지 않는다.
5. Linux 결과와 Windows 파일 잠금·재시작·권한·전원 장애 미검증 항목을 분리 기록한다. Windows 디렉터리 fsync 보장이 추가됐다고 주장하지 않는다.

## 7. 최소 변경 파일과 영향

| 파일 | 변경 목적 |
|---|---|
| `execution_launch/history_storage.py` (신규) | frozen 정책, digest, v3 wrapper/reference codec, 제한 검증 |
| `execution_launch/live_history.py` (CRLF 유지) | v3 명시 선택·header·quota·stage·append·replay·실시간 graph 검증·chain successor |
| `execution_launch/strategy.py` | 선택적 history_storage_sha256 protocol 필드와 strict parsing/binding |
| `execution_launch/driver.py` | 저장 구현 source closure 및 protocol 형식 binding 확인. E매도 정책 수정은 별도 revision |
| `execution_launch/coordinator.py` (CRLF 유지) | 같은 정책 원문을 history/chain/composition에 전달; 누락 시 명시적 설정 오류 |
| `tools/owner/launch.py` | 새 window setup 입력/검사 연결. 실제 head 초기화 호출 권한은 기존 operator 전용 |
| `tests/launch_history_storage.py` (신규) | codec/정책/한도/strict binding |
| `tests/launch_universe_history.py`, `tests/launch_live_history.py` | v3 실제경로·legacy 읽기·golden·fault/replay |
| `tests/launch_driver.py`, protocol 관련 tests | source 변경/정책 불일치 및 기존 omitted-field 호환 |
| `tests/launch_guards.py`, `tests/launch_acceptance.py` | 필요한 정확한 write call만 pin, negative mutation 검사 및 registry 추가 |
| universe spec/PR4d 계획/실행 로그 | 기존 무조건 용량 보장과 first fallback 문구를 새 계약으로 교체, 결과 기록 |

P0a `evidence_objects.py`는 원칙적으로 그대로 재사용한다. quota inventory/serialization을 안전하게 연결하려면 이 모듈의 제한된 보조 API 확장이 필요할 수 있으므로, 구현 전 정확한 lock 계약을 검토한다. 새 파일을 추가했다는 이유로 기존 source guard의 writer 금지를 넓게 해제하지 않는다.

`review_auth.py`/서명기 형식은 identity 7필드를 유지하면 이 저장 변경만으로 수정할 필요가 없다. 실제 분석에서 신규 필드가 필요해지면 해당 dependency를 명확히 드러내되 패스키 전환 설계와 혼합하지 않는다.

## 8. E 결정과 다음 단계의 명시적 경계

현재 `driver.py:378`은 window end에 target=0을 강제하며, `:472`는 terminal hold+dust를 거절한다. `live_history.py:522`는 마지막 slot의 새 decision을 만들지 않는다. 이것은 '마감 E 자체만으로 매도하지 않음'의 구현이 아니다.

후속 P1/P2에서는 새 행동 policy revision에 다음을 묶어 검증해야 한다.

- 마감/갱신 미응답은 진입·권한·판단 가능 여부를 바꾸지만 스스로 SELL을 만들지 않음.
- 갱신 승인 요청을 만들고 새 승인 없이는 기간을 자동 연장하지 않음.
- 마감 이후에도 기존 승인 범위 안의 감시·기존 위험 보호와 불능 통보를 구분. 유효한 주문 권한 없이 매도를 실행하지 않음.
- 기존 actual halt/손실 보호 규칙은 그대로 우선하며 임의 해제하지 않음.
- 실제 모델 SELL, 유효한 위험 trigger, 명시적 owner EXIT가 있을 때만 적법한 실행 경로로 연결. 부분체결·미체결·UNKNOWN은 다음 매도 단계에서 대조.

P0b를 완료하더라도 이 행동 revision과 실제 owner 상태/서명·연구 증거가 준비되기 전에는 실전 준비 완료나 활성화 가능으로 보고하지 않는다. 사용자에게 이미 확정된 E 요구나 손실 하한을 다시 묻지 않는다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
