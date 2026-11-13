# Upbit 조회 batch 원본 보관 API — 개발 계약

2026-11-13. 전용 tree `/workspace/tradegen-upbit-read-archive-1113`, base `a2e61b3`. 이 카드는 구현 계약이며 테스트 통과/실계좌 연결 기록이 아니다. I3c/I3d tree는 수정하지 않는다.

범위는 실제 E1 허용 GET의 **호출·각 HTTP 시도·원 응답·완료 inventory**를 기존 BundleStore에 보관하는 것이다. source/coverage 인증, guard 공개, 서명, 주문, 활성화, CLI는 포함하지 않는다. 키·headers·JWT·token·json_body·임의 exception text는 hook/기록에 들어가지 않는다.

## 1. 파일 소유

- transport 담당: `execution/transport.py`, `execution/upbit_inquiry.py`의 새 `READ_CAPTURE_ENDPOINTS` 상수만, 새 `tests/execution_read_capture.py`.
- archive 담당: 새 `execution_launch/upbit_read_format.py`, `execution_launch/upbit_read_archive.py`, 기존 `research_bundle_store.py`의 require_new 인자에 한정된 변경. 순수 format/store-adapter tests는 별도 담당과 정확히 분할한다.
- 독립 통합 담당: 실제 collect_upbit→E1→transport synthetic seam→BundleStore/head를 통과하는 새 테스트 파일. fake positive source/coverage issuer를 추가하지 않는다.
- root: registry/guard의 정확한 새 import·API pin, 최종 검증·커밋. 기존 `_send` 본문과 endpoint allowlist를 완화하지 않는다.

## 2. Transport의 exact 계약

`upbit_inquiry.READ_CAPTURE_ENDPOINTS`는 다음 9개 기존 GET의 frozen subset이다: `/v1/accounts`, `/v1/orders/open`, `/v1/orders/closed`, `/v1/order`, `/v1/deposits`, `/v1/withdraws`, `/v1/ticker`, `/v1/market/all`, `/v1/orderbook`. `/v1/order` 조회는 필요하다. 주문 생성/POST, KIS/OKX, api_keys/address/token 경로는 capture 대상이 아니다. transport는 기존 venue module 경계로 이 상수를 읽어 path literal guard를 보존한다.

```python
@dataclass(frozen=True, kw_only=True)
class UpbitReadEvent:
    call_ordinal: int
    attempt: int
    phase: str
    path: str
    params: tuple[tuple[str, str], ...]  # repr=False
    observed_at: datetime | None
    clock_status: str
    status_code: int | None
    body_status: str
    body_bytes: int | None
    body_sha256: str | None
    raw_body: bytes | None              # repr=False
    error_code: str | None

@contextmanager
def capture_upbit_reads(observer, *, call_ordinal: int,
                       not_before: datetime,
                       max_body_bytes: int = 8 * 1024 * 1024): ...
```

- `observer(event)->None`다. observer가 저장/재읽기를 완료하기 전에 request는 진행하지 않는다. return이 None이 아니거나 callback 실패면 `READ_CAPTURE_SINK_REFUSED`; 요청/재시도 허가를 반환하는 callback이 아니다.
- 한 context는 한 logical request만 허용한다. attempt는 1 또는 2이고 retry는 같은 call ordinal이다. ContextVar의 같은 thread identity를 확인하며 nested/reused/recursive/in-callback/wrong-thread/잘못된 context 입력은 `READ_CAPTURE_CONTEXT_REFUSED`다. 실패 latch를 유지하므로 내부 거절을 삼켜도 다음 send가 진행되지 않는다. context 종료 시 원 상태를 복원한다.
- ordinal은 exact int 1..2000, not_before는 exact aware datetime(year 2..9998), body limit은 exact int 1..8MiB다. params는 query 생성 **전** exact tuple snapshot: 최대 16 pairs, key ≤128 chars, value ≤65536 chars, exact str. 이후 그 snapshot으로 실제 query와 event를 만들며 외부 iterable을 재순회하지 않는다.
- active context에서 scope 외 request는 credentials 이전 `READ_CAPTURE_SCOPE_REFUSED`. context가 없으면 기존 입력·clock reads·pacing·retry·예외·Answer 동작을 그대로 유지한다.
- phase는 `BEFORE_SEND`, `RESPONSE`, `TRANSPORT_ERROR`다. BEFORE_SEND는 기존 before_send guard 뒤 실제 send 직전의 기록/admission이다(전송 완료 뜻 아님). RESPONSE는 `_send` 반환과 기존 수신 clock 관측 직후, after_response guard·pacing·retry·`_check_answer`보다 먼저 호출한다. 오류는 기존 pacing/retry 판단 전에 TRANSPORT_ERROR로 보존한다.
- clock_status는 `OK`, `INVALID`, `RAISED`, `ROLLBACK`. 활성 context에서 BEFORE_SEND는 명시 clock을 읽고, RESPONSE는 기존 `_now()` 수신 관측을 재사용한다. `not_before` 및 직전 정상 관측보다 이르면 ROLLBACK. 정상 시각은 UTC; 나머지는 observed_at=None. 시계가 실패해도 이미 반환된 원 bytes를 먼저 보관한 뒤 `READ_CAPTURE_CLOCK_REFUSED`로 중단한다. 나쁜 시각을 전날/현재 시각으로 보정하지 않는다. 후속 retry도 없다.
- body_status는 `NOT_RECEIVED`, `PRESENT`, `LIMIT_EXCEEDED`, `INVALID`. BEFORE_SEND/TRANSPORT_ERROR에는 NOT_RECEIVED와 raw/hash/length/status=None. RESPONSE의 exact bytes(빈 bytes 포함)는 한도 안이면 PRESENT/실제 length/SHA/raw다. 한도 초과면 LIMIT_EXCEEDED/실제 length, raw/hash=None인 진단을 먼저 남긴 뒤 `READ_CAPTURE_RESOURCE_LIMIT`; 원문 전체를 보관했다고 하지 않는다. 이 한도는 `_send`가 이미 받은 response의 보관 한도이며 기존 HTTP allocator를 제한했다고 주장하지 않는다.
- status는 exact int 100..999(비표준 상태도 원 사실로 보존). status 타입/범위 또는 raw bytes 타입이 `_send` 계약과 다르면 RESPONSE/error_code=`INVALID_RESPONSE`; 정상 bytes는 여전히 보관하고 잘못된 status는 None, nonbytes body는 INVALID/raw/hash/length=None. 이후 `READ_CAPTURE_RESPONSE_INVALID`로 중단한다. 임의 str 변환은 없다.
- TRANSPORT_ERROR error_code는 `CONNECTION_ERROR`, `READ_TIMEOUT`, `TIMEOUT`, `OS_ERROR`, `VALUE_ERROR`, `OTHER_EXCEPTION`만. 실제 ConnectionError의 기존 1회 retry 규칙은 observer가 정상 완료하고 clock이 정상일 때만 유지한다. 예외 본문은 저장하지 않는다. BaseException/프로세스 종료를 정상 완료로 바꾸지 않는다.
- 429/5xx 첫 응답, 두 번째 응답, 잘못된 JSON, 인증 오류 body도 **검증 전에** 보관한다. server Date는 event에 headers로 넘기지 않는다. 성공한 fetch의 최종 SourceReceipt metadata에서 server_time을 별도로 결합한다.

## 3. 순수 format

```python
@dataclass(frozen=True, kw_only=True, slots=True)
class ReadBatchLimits:
    max_calls: int = 2000
    max_attempts: int = 4000
    max_records: int = 12002
    max_body_bytes: int = 8 * 1024 * 1024
    max_total_body_bytes: int = 64 * 1024 * 1024
    max_record_bytes: int = 2 * 1024 * 1024
    max_total_record_bytes: int = 64 * 1024 * 1024

@dataclass(frozen=True, kw_only=True, slots=True)
class ReadBatchRecord:
    schema_version: int
    batch_id: str
    ordinal: int
    previous_archive_digest: str | None
    kind: str
    body: Mapping  # exact kind별 아래 keyset, bounded detached immutable values

def record_bytes(record, *, limits=DEFAULT_LIMITS) -> bytes: ...
def parse_record(raw: bytes, *, limits=DEFAULT_LIMITS) -> ReadBatchRecord: ...
def record_digest(record, *, limits=DEFAULT_LIMITS) -> str: ...
def limits_digest(limits=DEFAULT_LIMITS) -> str: ...
```

모든 limit은 exact positive int이며 위 기본값 이하만 허용한다. `ReadBatchFormatError`의 고정 코드만 반환한다. UTF-8 canonical JSON(sort keys, compact separators, ensure_ascii=True), 중복/extra/missing key·bool-as-int·NaN·깊이/개수 초과 거절. datetime은 UTC microsecond 32-char 표현; hash는 lowercase64hex. batch_id는 `[A-Za-z][A-Za-z0-9_-]{0,63}`. ordinal은 0부터 연속, max_records 미만. domain은 `b'tradegen-upbit-read-batch-record/1\x00'`, limits는 `b'tradegen-upbit-read-batch-limits/1\x00'`. raw_body 자체는 JSON에 base64로 넣지 않는다.

| kind | body exact keys/의미 |
|---|---|
| OPEN | account_scope, started_at, limits_sha256, anchor_sha256, coverage_sha256, baseline_sha256, trade_fees_sha256. source/operator 입력의 content_digest이며 인증 아님. ordinal0/previous=None |
| FETCH_BEGIN | call_ordinal, path, params, requested_at. 실제 outer fetch마다 연속 ordinal, 임의 symbol/path 입력을 새로 만들지 않음 |
| ATTEMPT | UpbitReadEvent의 모든 필드 중 raw_body 제외. PRESENT이면 별도 raw payload `body`가 hash/length와 정확히 일치해야 함 |
| FETCH_END | call_ordinal, status, receipt, error_code. status=RETURNED 또는 REFUSED. RETURNED receipt는 {path,params,account_scope,received_at,server_time,sha256}; 마지막 PRESENT RESPONSE와 exact binding, error=None. REFUSED receipt=None, fixed error code |
| CLOSE | status, error_code, collection_manifest_sha256, records, calls, attempts, finished_at, clock_status. status=COLLECTED 또는 REFUSED. records는 앞의 모든 ordinal/digest pair를 순서대로 담고 자기 자신은 포함하지 않음. COLLECTED는 manifest hash/정상 완료시각/error=None, REFUSED는 manifest=None. clock 문제는 시각=None, 해당 clock_status |

body 내 기록시각은 위 representation으로 encode하고 tuple은 JSON array로 encode한다. 순수 parse가 caller 문서를 actual network/source/collector 결과로 발급하지 않는다. 제한된 구조/문자열을 먼저 검사하고 dataclass 변조나 lying Mapping이 큰 사본/문자열/리스트를 먼저 할당하게 하지 않는다. JSON은 depth≤12/nodes≤250000/int64로 제한한다.

행 순서: OPEN → (FETCH_BEGIN → [BEFORE_SEND → RESPONSE/TRANSPORT_ERROR] 최대2회 → FETCH_END)* → CLOSE. credential/allowlist/clock refusal로 send 전에 FETCH_END가 나올 수 있다. failed/partial trace는 열린 fetch나 response 없는 BEFORE_SEND를 보존할 수 있지만 COLLECTED로 끝낼 수 없다. refused CLOSE는 실제 관찰된 prefix와 실패 원인을 담는다. 단순 metadata 조회나 별도 caller 작성 문서는 실제 수집 발급으로 해석하지 않는다.

## 4. BundleStore 연결 및 신규 OPEN 단일 승자

기존 `BundleStore.archive_raw(manifest, payloads, *, require_new=False)`의 optional exactbool만 추가한다. `_commit`의 기존 실제 catalog lock 안에서 require_new이며 existing digest가 존재하면 `BUNDLE_STORE_ALREADY_PUBLISHED`(부분 primary도 포함)다. 같은 run/revision의 다른 digest는 기존 ID_REUSED다. 기본 false의 exact retry와 commit_verified는 불변이다. 기존 손상/실제 catalog 검증·CAS·backup 의미를 완화하지 않는다.

모든 record는 RAW_ARCHIVED이며 run_id=`upbit-`+batch_id, revision_id=`read-v1-`+ordinal의 5자리 0padding, attempt_id=`upbit-`+batch_id다. OPEN은 require_new=True, 이후는 false. batch ID를 재사용해 새 HTTP를 시작하지 않는다. 새 수집은 새 명시 batch_id다. 서로 다른 호출의 동일 bytes도 서로 다른 record이고 payload object 내용 dedup만 허용한다.

각 manifest에는 generated `record`(`record.json`)와 PRESENT일 때 `body`(`response.bin`) payload만 있다. role=other_input, source_name/study_id=None, expected_candidates=None. 해당 record 자체 inventory_complete=True는 보관한 파일 목록 완전성일 뿐 batch/계좌 완전성이 아니다. parent_bundle_sha256는 previous_archive_digest와 같다. 기존 parent 필드는 자동 graph 검증이 아니므로 새 reader가 모든 실제 부모 graph를 검증한다.

각 callback은 archive_raw → actual read_raw(require_backup=True) → exact record/body 비교를 마쳐야 반환한다. 이를 기다리는 동안 다음 HTTP는 없다. store/head 초기화는 기존 명시 operator 단계로만; wrapper에서 provision/initialize/reanchor를 호출하지 않는다.

## 5. 실제 collector wrapper 및 reader

```python
def collect_retained_upbit_batch(source, *, store, batch_id: str,
    anchor, coverage, risk_baseline, clock, trade_fees=(),
    limits=DEFAULT_LIMITS) -> ReadBatchResult: ...

def read_upbit_read_batch(store, last_archive_digest: str, *,
    limits=DEFAULT_LIMITS) -> ReadBatchArchive: ...
```

source는 exact E1UpbitSource, store는 exact BundleStore, `source.clock is clock`이며 명시 state scope/입력 구조를 검증한다. 실제 source class의 fetch를 호출하는 private wrapper가 FETCH_BEGIN과 context를 만든다. alias callable/constructed receipt를 actual E1의 대체 발급자로 받지 않는다. 실제 collect_upbit에 이 wrapper를 넘기며 max_requests=limits.max_calls, max_rows=100000을 사용한다. E1의 실제 transport·키 처리 코드는 바꾸지 않고 테스트에서만 `_send`/기존 키 공급 seam을 합성으로 대체한다.

`ReadBatchResult` frozen fields: batch_id, open_archive_digest, last_confirmed_archive_digest, final_archive_digest(str|None), status(`COLLECTED`/`REFUSED`/`INCOMPLETE`), failure_code(str|None), collection(CollectionResult|None, repr=False). 모든 source_authenticated/coverage_verified/execution_ready는 property False. open digest는 성공적으로 backed OPEN을 만든 뒤만 반환한다. OPEN 이전 실패는 고정 ReadBatchArchiveError다.

`ReadBatchArchive` frozen fields: batch_id, last_archive_digest, status(`COLLECTED`/`REFUSED`/`INCOMPLETE`), records(tuple[ReadBatchRecord,...], repr=False), payloads(immutable mapping[ordinal,bytes], repr=False), final_archive_digest(str|None). 같은 false flags를 가진다. historical reader는 collection을 재발급하거나 네트워크를 호출하지 않는다.

수집 성공 뒤 exact 최종 inventory와 전체 부모/원문/backup graph를 다시 읽은 경우에만 result.collection을 반환한다. REFUSED는 실패 final을 보관·검증한 경우, INCOMPLETE는 final이 없거나 저장 실패로 완성하지 못한 경우다. 저장 실패 이후 새 HTTP는 0이며 기존 confirmed prefix를 덮어쓰거나 삭제하지 않는다. INCOMPLETE의 last_confirmed digest는 과거 callback 확인 사실이며 현재 graph 건강/권한을 보장하지 않는다. reader는 실제 현재 손상 graph를 거절한다. 배치 중단 후 자동 network resume는 없고 원 prefix를 유지한 새 batch_id로만 새 수집을 시작한다.

정규화 코드: READ_BATCH_INPUT_INVALID, LIMITS_INVALID, RESOURCE_LIMIT, SOURCE_REQUIRED, STORE_REQUIRED, SOURCE_CHANGED, CLOCK_REFUSED, ID_REUSED, ARCHIVE_REFUSED, COLLECTOR_REFUSED, TRANSPORT_REFUSED, FORMAT_INVALID, CHAIN_INVALID(각각 READ_BATCH_ 접두어). known transport READ_CAPTURE_* 코드는 고정 allowlist로 보존할 수 있다. 임의 exception 문자열을 코드처럼 저장하지 않는다. 수집 실패의 raw 사실은 실제 attempt records가 설명하며 추정 body/status를 합성하지 않는다.

## 6. 자원·중단 검증 및 완료 범위

- admission: OPEN/다음 FETCH_BEGIN/BEFORE_SEND 전에 남은 calls/attempts/records/aggregate bytes를 검사한다. 각 실제 archive는 기존 primary/backup/catalog admission을 다시 수행한다. 사전 확인은 다른 writer나 OS 실패에 대한 공간 예약/보장이 아니다. 전체 기록 목록을 먼저 무한 생성하거나 full graph를 무제한 읽지 않는다.
- 이미 `_send`가 반환한 body가 너무 크거나 aggregate/storage 한도에 걸리면, 보관하지 못했다는 고정 상태와 마지막 exact prefix만 남기고 중단한다. bytes를 truncate하거나 정상 가격을 None으로 바꿔 정상 collection을 반환하지 않는다. 진단 자체 저장이 실패하면 final을 꾸미지 않는다.
- transport: 첫429/5xx와 retry, malformed/empty/auth-failure body, ConnectionError/ReadTimeout, callback 실패 전후 send count, after_response guard 실패 전 raw 보존, clock 예외/역행 raw 보존, nested/reentry/thread, excluded KIS/OKX/POST, no-observer clock/pacing/bytes 불변.
- archive: 실제 BundleStore의 동시 same-batch OPEN 단일 승자, distinct batch ID, quota±1, partial primary/backup/CAS/response loss, omitted/duplicate/reordered parent·final inventory, 동일 raw의 서로 다른 observation, readback mutation, ID 변경 재시도 금지. 신규 reader는 exact raw/backup 전체를 검증하고 저장된 kind를 인증으로 해석하지 않는다.
- integration: 실제 E1+collect_upbit가 수행하는 여러 fetch의 원문을 actual stores에 보관하고 현금·체결 등 collector 성공/거절을 원 코드로 확인한다. source/retention/fence 입력은 합성 테스트 자료임을 명시한다. 정상 경제 결과나 오류를 approved/complete coverage로 승격하지 않는다.

완료는 **유용한 실제 read-call 증거와 부분/완성 보관 경계**다. 생산 source 완전성, guard commit/publication, 자동 BUY/SELL, 실계좌 연결은 이번 변경으로 제공하지 않는다. usage_weekly_pct는 unknown이며 체크포인트는 실제 단위 검증 후 root가 기록한다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
