# Upbit read-batch archive 실행 기록

작성일: 2026-11-13. 실제 조회 시도·응답·실패를 보관하는 단위를 구현했다. 수정 후 관련 **485 PASS / 0 FAIL / 0 NOT_RUN**, 한 프로세스 **146.692초**를 확인했다. 실제 계좌 연결·출처 인증·거래 활성화 완료를 의미하지 않는다.

## 구현 범위

실제 `E1UpbitSource.fetch`와 `collect_upbit`를 기존 `BundleStore`의 `RAW_ARCHIVED` 보관 경로에 연결했다. `execution/transport.py`의 선택적 관찰 문맥은 허용된 Upbit GET 아홉 개만 대상으로 한다: `/v1/accounts`, `/v1/orders/open`, `/v1/orders/closed`, `/v1/order`, `/v1/deposits`, `/v1/withdraws`, `/v1/ticker`, `/v1/market/all`, `/v1/orderbook`. `/v1/order`는 주문 상세 조회다. 다른 venue, KIS POST, 주문 생성·취소 요청에는 이 관찰 문맥을 사용할 수 없다.

한 외부 fetch의 순번과 내부 재시도 순번을 구분한다. 각 전송 시도의 `BEFORE_SEND`, 실제 수신 `RESPONSE`, 고정 분류의 `TRANSPORT_ERROR`를 보관한다. `_send`가 반환한 응답은 JSON·인증 오류 검사, 응답 후 guard, pacing 및 다음 재시도보다 먼저 기록한다. 첫 429/5xx, 잘못된 JSON, 빈 본문, 연결 실패와 재시도 기록을 최종 성공 응답으로 대체하지 않는다. `BEFORE_SEND`는 전송하려던 시도의 기록이며 실제 wire 송신 증거가 아니다. 기록 뒤 guard가 전송을 중단할 수도 있다.

원래 query를 만들기 전에 매개변수 순서와 중복을 제한된 크기로 고정한다. 헤더·JWT·토큰·키·`json_body`는 새 event 필드에 포함하지 않는다. 본문과 query 값은 공개 repr에서 숨긴다. 동일 문맥의 재사용·중첩·재진입·다른 thread 사용은 거절하며, 문맥 없는 기존 요청의 시계·pacing·재시도·예외 경로는 유지한다. 이 thread 문맥은 무관한 전체 프로그램의 통신을 통제하는 sandbox가 아니다.

응답 시계가 예외·잘못된 값·역행을 보이면 `observed_at=None`과 고정 clock 상태를 기록한다. 수신된 제한 이내 원문을 먼저 보관한 뒤 추가 요청을 중단한다. 한도를 초과한 본문은 실제 길이와 `LIMIT_EXCEEDED` 상태만 남기며 전체 원문을 보존했다고 표시하지 않는다. 보관 callback 자체가 실패하면 다음 HTTP 시도를 진행하지 않는다. 느린 `BEFORE_SEND` 보관 뒤에는 기존 전송 직전 guard를 다시 확인한다.

## 저장과 재읽기

새 순수 codec `execution_launch/upbit_read_format.py`는 `OPEN → FETCH_BEGIN → ATTEMPT → FETCH_END → CLOSE`의 닫힌 형식과 제한된 canonical JSON을 정의한다. 응답 원문은 metadata와 별도 payload로 저장한다. batch ID, record 순서, 이전 archive digest, 전체 최종 inventory가 연결되며 숫자·시간·필드·원문 길이·총량을 엄격히 검사한다. 기본 한도는 호출 2,000개, 시도 4,000개, record 12,002개, 본문 하나 8 MiB·총 64 MiB, metadata 하나 2 MiB·총 64 MiB이며 설정은 이 상한 이내로만 좁힐 수 있다.

`research_bundle_store.py`의 좁은 변경은 `archive_raw(..., require_new=False)`다. 새 batch의 OPEN은 `require_new=True`를 사용해 기존 catalog의 실제 lock 안에서 이미 게시된 동일 OPEN도 거절한다. 같은 batch ID에 다른 시작시각을 넣어 새 조회를 재개하는 우회도 기존 run/revision 충돌 검사로 거절한다. 기본 exact retry와 backup 완료 재시도, verified 게시의 기존 의미는 유지한다. storage admission은 공간 예약이나 향후 쓰기 성공 보장이 아니며 각 실제 게시에서 다시 검사한다.

`execution_launch/upbit_read_archive.py`는 매 record의 실제 primary·backup readback을 확인한다. 재읽기는 한 catalog snapshot/lock에서 metadata 한도를 먼저 검사하고 각 연결 graph를 읽는다. 전체 batch·parent·순서·retry·최종 inventory와 primary/backup 원문을 대조한 뒤 catalog/head를 마지막으로 재확인한다. 부모 hash가 있다는 사실만으로 이전 record를 생략하지 않는다. CLOSE가 없는 prefix는 `INCOMPLETE`이고, 새 reader가 과거 기록에서 실제 발급 `CollectionResult`나 HTTP 재시도를 만들어내지 않는다.

독립 읽기 검토에서 발견한 source 변경 경계도 현재 소스에 반영됐다. 실제 응답이 돌아온 뒤 source scope 또는 clock이 바뀌어도 이미 수신한 본문은 기존 OPEN에 먼저 보관하고 이후 `READ_BATCH_SOURCE_CHANGED`로 거절한다. 변경된 source가 정상 collection으로 반환되지 않으며 실패 record·CLOSE의 성공 manifest도 발급하지 않는다. 해당 실제 전송 callback 회귀도 최종 실행에서 통과했다.

`COLLECTED`는 이 wrapper가 실제 collector 반환값과 보관된 전체 호출 기록을 확인한 결과다. raw manifest의 `expected_candidates=None`과 `other_input`은 연구 전체 후보의 완전성을 뜻하지 않는다. 모든 공개 결과의 `source_authenticated`, `coverage_verified`, `execution_ready`는 `False`다. 실패·중단 원본을 정상 연구나 현재 계좌 권한으로 승격하지 않는다.

## 소스·검사 범위와 상태

새 파일은 `execution_launch/upbit_read_format.py`, `execution_launch/upbit_read_archive.py`다. 기존 변경은 transport 관찰 경계, `upbit_inquiry.py`의 정확한 아홉 GET 상수, BundleStore의 `require_new` 옵션 및 검사 registry/guard다. 기존 `_send` 구현과 실제 HTTP 호출 위치는 유지한다.

guard 변경은 새 capture 구현의 정확한 AST와, `upbit_read_archive.py` 한 파일에서만 허용하는 정확한 두 import(`UpbitReadEvent`, `capture_upbit_reads`)로 제한한다. 일반 transport import, 별칭·재바인딩·private helper 접근, 다른 파일로의 허용 전파 또는 기존 `_send` 변경을 포괄 허용하지 않는다. mutation 회귀도 최종 실행에서 통과했다.

새 기능 검사 86개와 좁은 guard 음성 검사 4개를 기존 관련 회귀와 함께 실행했다. 아래 수량은 485개에 이미 포함되므로 합산하지 않는다.

- `tests/execution_read_capture.py`: 30개 — 원문 우선 기록, retry/예외/guard/clock·문맥·기존 요청 동작.
- `tests/launch_upbit_read_format.py`: 22개 — 정확한 닫힌 형식·크기·시간·변조 거절.
- `tests/launch_upbit_read_archive.py`: 16개 — 실제 임시 store의 원문·backup·chain·inventory·quota·새 OPEN 충돌과 기존 retry.
- `tests/launch_upbit_read_integration.py`: 18개 — 합성 응답을 사용하는 실제 E1 collector부터 임시 BundleStore까지의 연결, 실패 원문·source 변경·불완전 prefix.

검증 기록은 실패를 포함해 원래 결과대로 보존했다.

| 실행 | 결과 | 시간 | 소스 fingerprint |
| --- | --- | ---: | --- |
| 최초 새 기능·guard 집중 | 144개: 138 PASS / 6 FAIL / 0 NOT_RUN | 83.795초 | `4ed267180d6a83801c21546a2613ea67c8d5d9ad9d75d253723342cba1f35051` |
| 수정 후 전체 E1 및 관련 회귀 | 485 PASS / 0 FAIL / 0 NOT_RUN | 146.692초 | `fb36785dc8fb1e0452f48e0046284408fab0d1007f3068ffd5edab4728bf5af0` |

실제 codec 결함 1건은 작은 사용자 지정 본문 한도를 초과한 응답을 생성자가 기본 한도로 다시 검사하여 초과 사실 기록도 거절한 문제였다. 생성자는 비권한 구조를 확인하고, 저장·해시·parse는 실제 선택 한도를 엄격히 검사하도록 수정했다. 기존 초과 원문 미보관/잘라내기 금지/정상 collection 거절 검사는 그대로 유지했다.

나머지 실패는 guard 3개와 fixture 2개였다. Python 3.12/3.13의 `ast.dump` 빈 필드 출력 차이를 동일 `ast.unparse` pin으로 바꾸고 기존 음성 검사를 유지했다. encoder 호출 감시 전에 fixture의 limits digest를 준비하도록 고쳤다. JSON 문법·중복 키는 첫 조회에서 거절되지만 잔고의 의미 오류는 실제 collector의 다섯 조회 뒤 판단하므로 그 실제 순서와 모든 원문 보존을 검사하도록 수정했다. 정상 경제 결과를 만들거나 실패 검사를 제외하지 않았다.

별도 읽기 검토에서는 record body의 외부 mapping hook이 header를 바꾸는 문제와 typed input의 비표준 `__dict__`를 발견했다. 검증된 header snapshot·재검사 및 exact dict inventory로 보완하고 음성 회귀를 추가했다. 이는 읽기 검토 발견 사항이며 최초 런타임 FAIL로 집계하지 않는다.

최종 실행은 전체 `execution` suite, 새 세 모듈, launch guards, 실제 account collector, BundleStore/format/연구 bundle 및 기존 full-capture archive, 두 전역 read-only 검사를 포함한다. 소스 커밋 `69b3dced40abec9d7f9da88d0c321db8a000c8c5`를 main53에 통합한 `95ab0e8378d66116602e1ad89485891a83be2729`에서 실행했다. registry 충돌은 양쪽 모듈의 중복 없는 합집합으로 해결했다.

두 실행 모두 19개 KEYLESS 변수·격리된 임시 홈을 사용했고 import/discovery 이전부터 종료까지 소스와 보호 홈 메타데이터가 불변이었다. QA 출력은 복원했다. 실제 E1/collector/JWT 경로와 실제 임시 primary/backup/head를 사용하되 HTTP·키 공급·시계·coverage 입력은 합성 fixture였다. 실제 API·사용자 홈 내용·실계좌·키·주문·알림을 사용한 검증이나 native Windows 장애 검증은 아니다. 실행 증거는 `tradegen-session/upbit-read-archive-1113/upbit-read-batch-{dev1,final-related}-{start,checkpoint,rows,summary}.json`과 각 로그에 있다.

## 남은 경계

이 단위는 관측한 조회 시도와 원문을 보관한다. 계좌·원격 출처의 진위, 관련 가격·체결의 누락 부재, 실제 venue coverage issuer, 현재 owner 승인, guard commit 뒤 publication, 운영 Coordinator/Runner 연결 및 실거래 활성화는 이 보관 결과로 발급하지 않는다. 보관 장애를 매도 신호로 바꾸거나 기존 손실 하한·daily stop·halt를 완화하지 않는다. 별도 backup 경로만으로 독립 장애 영역이나 전체 root의 동시 rollback 방어를 주장하지 않는다.

계약: `TRADEGEN_UPBIT_READ_BATCH_API_2026-11-13.md`. 같은 provider에 다음 확정 계좌 세대를 게시하는 연결은 별도 후속 단위다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
