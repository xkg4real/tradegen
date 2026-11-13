# TRADEGEN — Upbit 자료 완전성 계약과 공식 문서 대조

관측일: **2026-11-13 UTC**, 최종 정리 시각 **18:59 UTC**. 개발용 읽기 검토이며 실거래 수용 검사나 coverage 인증서가 아니다.

**결론:** Upbit의 공개된 실시간/조회 기능은 실제 자료 수집과 대조를 구현할 근거가 된다. 그러나 이번에 확인한 공식 문서만으로 TRADEGEN의 `complete-ordered-account-marks-and-fills-v1`을 충족했다고 판정할 수는 없다. 특히 모든 관련 가격 변화와 개인 체결의 공통 순서, 단절 구간의 완전 복원, 최종 구간 마감 증거와 REST 전체 수집의 일관성 보장이 비어 있다. 이는 “Upbit에서 영원히 구현 불가능”이라는 결론이 아니라 **현재 근거로 긍정적인 운영 issuer를 만들 수 없다는 판정**이다.

## 1. 조사 범위와 판정 용어

- 로컬 소스는 `/workspace/tradegen-committed-generation-1113`의 delivered `49796a67d793d869ab0ed1108579d79ed8c6d744`를 읽었다. PR56 main `19f6775935f8d8828eed21fcaa76449507239a5b`와 tree `3643ea46e0560ec59df49d0f654f1d8112d17b3b`가 같음을 확인했다.
- 외부 조회는 지정된 web 도구의 검색·문서 열기만 사용했고 `docs.upbit.com`, `global-docs.upbit.com` 공식 문서만 근거로 삼았다. 문서 속 API 주소·예제는 실행하지 않았다. 거래소 REST/WebSocket, 계정, credential, 시장 데이터 호출은 **0**이다.
- 소스·테스트·하네스·Notion·기존 인수인계 문서를 변경하지 않았다. 이 파일만 작성했다. 수익률·시장 우위나 실제 사용자 상태를 추정하지 않는다.

| 표기 | 의미 |
|---|---|
| **명시 제공** | 문서에 해당 기능·필드·범위가 적혀 있다. 전달 무손실·전역 순서까지 확대하지 않는다. |
| **명시 제한** | 문서가 지연·범위 상한·미보장을 명시한다. 적용 문서 버전을 함께 적는다. |
| **보장 미확인** | 검토한 문서에서 필요한 계약을 찾지 못했다. 기능이 절대로 없다고 주장하지 않는다. |
| **현재 미구현/거절** | TRADEGEN 소스에 생산용 연결이 없거나 고정 진단으로 거절한다. 거래소의 기능 유무와 구분한다. |

페이지의 상대적 “updated” 시각은 고정 배포 버전으로 취급하지 않았다. 일부 version URL이 현재 페이지로 redirect됐고, 일부 HTML 추출은 동적 Response schema를 생략했다. 검색에 노출된 공식 schema와 직접 열린 본문이 다르면 그 차이도 아래에 기록했다.

## 2. 현재 코드가 요구하는 증거

### A. 구간 전체의 평가액 경로

[`execution_accounts/continuous.py`](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/continuous.py#L1)의 계약은 계좌 scope·stream epoch·직전 상태·반개구간 `[start,end)`에 대해 시작 marks, 모든 관련 mark/fill, 두 종류의 공통 순서, 마지막 source watermark, 누락된 계좌 변화가 없음을 별도 신뢰된 verifier가 인증하도록 요구한다. 로컬 sequence가 연속인 것과 venue의 완전한 sequence는 구분돼 있다.

`verify_coverage`는 verifier를 실제 호출하고 정확한 `VerifiedCoverage` 타입, 요청 해시·계약 문자열·authority/source proof 해시·관측 시각을 확인한다. **이 구조체의 생성 가능성이나 해시 일치가 외부 사실의 인증은 아니다.** 현재 배포 소스에는 생산용 Upbit coverage verifier가 없다는 주석이 명시돼 있다. `value_path`는 입력된 전체 경로의 각 변화에서 최고/최저 평가액을 계산하므로, 빠진 중간 변화는 원금·고점 보호 판단에 영향을 준다. 같은 밀리초의 체결 순서도 인증된 공통 경로와 맞아야 한다. [코드: verifier와 valuation](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/continuous.py#L281)

여기서 “모든 mark”는 검토된 평가 규칙이 사용하는 관련 가격 사건을 뜻한다. 거래소 안의 모든 미시적 가격 움직임을 임의로 추가한 요구가 아니다. 다만 현재 collector의 최근 체결가/오래된 체결의 best bid 전환, 보유 수량·수수료·입출금 변화와 평가 시각을 포함하여 **어떤 변화가 평가액을 바꾸는지**를 실제 source 계약으로 닫아야 한다. [코드: 평가 가격 및 freshness](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/upbit_collector.py#L430)

### B. REST collection의 origin·계좌 범위·일관성

[`collector.CoverageEvidence`](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/collector.py#L103)는 다음 별도 검토 사실을 요구한다.

- origin의 현금과 보유/미체결/부분 체결 주문이 없는 실제 시작 anchor.
- credential과 main pocket/account scope의 실제 연결.
- origin부터 현재까지의 전체 이력 보존, 미보고 흐름/포켓 이동 없음, KRW 현물 현금 계좌 모드.
- 수집 전체 동안 수동·다른 API 주문/체결, 이체·보상·잔액 변화가 없다는 **외부에서 성립한 quiescent fence**.

`_validate_proofs`는 이 문서의 시간 범위와 닫힌 statement 문자열을 검사한다. 이것은 거래소의 atomic snapshot을 호출하거나 거래를 실제로 잠그는 구현이 아니다. E1 source도 credential이 주장한 account scope의 것임을 스스로 증명하지 않는다고 명시한다. [검토 증거 검사](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/upbit_collector.py#L223), [E1 source의 신뢰 경계](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/upbit_collector.py#L38)

collector는 잔액·open/closed orders·개별 체결·입출금·수수료를 실제로 대조하고 원문 receipt를 묶는다. 잔액/open orders/입출금을 다시 읽는 것은 추가 검사이며 외부 fence의 대체물이 아니다. 종료 주문은 시간 구간을 분할하고 포화된 timestamp를 거절한다. 여러 체결에 총 수수료만 있으면 임의 배분하지 않고 `TradeFeeEvidence`를 요구한다. [페이지/구간 수집](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/upbit_collector.py#L147), [체결별 수수료](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_accounts/upbit_collector.py#L247)

### C. 지금 실제로 거절하는 지점

| 실제 소스 경계 | 현재 동작 |
|---|---|
| `upbit_interval_frame` | 보유 position 또는 직전 baseline 이후 새 fill이 있으면 `ACCOUNT_INTERVAL_EXTREMA_EVIDENCE_REQUIRED`. 새 외부 흐름도 별도 거절한다. 현재 생산 경로는 flat 구간만 exact extrema로 처리한다. [소스](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_launch/account_interval.py#L98) |
| `ContinuousUpbitCandidateSource` | path source·coverage verifier·원본 보관을 받아 연구용 candidate를 만들 수 있으나 `__call__`은 `CONTINUOUS_LIVE_RISK_INTEGRATION_REQUIRED`로 거절한다. 타입만 맞춰 운영 provider로 올릴 수 없다. [소스](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/execution_launch/account_interval.py#L397) |
| PR54 원문 보관 / PR56 세대 게시 | 받은 증거의 보존 및 이미 확정된 로컬 세대의 안전한 게시를 제공한다. 받지 못한 사건, 계좌 진위, 원격 누락 부재를 새로 인증하지 않는다. [PR54 기록](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/docs/upbit-read-batch-archive-execution-log.md), [PR56 기록](https://github.com/xkg4real/tradegen/blob/49796a67d793d869ab0ed1108579d79ed8c6d744/docs/committed-generation-publication-execution-log.md) |

따라서 거래가 한 번 체결된 이후를 안전하게 이어가는 데에는 단순 잔액 조회 추가 이상의 증거가 필요하다. 현 source 거절을 삭제하거나 synthetic coverage receipt를 production에 넣는 것은 해결이 아니다.

## 3. 공식 문서와의 대조

아래 각 URL은 **2026-11-13 관측**이다. KRW 현물 판단은 한국 문서를 우선하고 Global 문서는 보조 비교로만 사용했다.

| 항목 | 문서가 실제 제공·제한하는 내용 | 현 계약에 남는 차이 |
|---|---|---|
| Orderbook | **명시 제공:** snapshot/realtime, 가격·수량·timestamp, depth/level 선택. 현재 응답 표에는 update sequence나 predecessor 필드가 없다. [KR Orderbook](https://docs.upbit.com/kr/reference/websocket-orderbook) | **보장 미확인:** 모든 호가 변경 전달, 연속 sequence, 특정 snapshot 이후 빠짐없는 diff/replay, 마지막 처리 watermark. timestamp나 수신 순서만으로 이를 만들 수 없다. |
| Public Trade | **명시 제공:** unique `sequential_id`, 체결 시각, 가격/수량과 best quotes. [KR Trade](https://docs.upbit.com/kr/reference/websocket-trade) | 연속 정수·무손실·다른 종목 및 개인 체결과의 공통 순서 보장은 **미확인**. unique를 `id+1`로 다음 사건을 예측하는 sequence로 해석하지 않는다. |
| Trade ID의 순서 | **명시 제한(버전 주의):** KR v1.5.9 REST 체결 문서는 unique 판단에 쓸 수 있지만 순서를 보장하지 않는다고 명시한다. Global v1.2.2 WebSocket 문서도 같은 제한이다. [KR 이전 명세](https://docs.upbit.com/kr/v1.5.9/reference/%EC%B5%9C%EA%B7%BC-%EC%B2%B4%EA%B2%B0-%EB%82%B4%EC%97%AD), [Global v1.2.2 Trade](https://global-docs.upbit.com/v1.2.2/reference/websocket-trade) | 이를 최신 KR transport가 반드시 역순 전송한다는 주장으로 바꾸지 않는다. 현재 문서에서 강한 순서 보장을 새로 확인해야 한다. 아래 문서 차이도 참조한다. |
| Public REST trade 복원 | **명시 제공/상한:** 페어별 체결을 시간 역순으로 조회하고 `sequential_id` cursor로 이어갈 수 있다. 요청당 최대500개, 일자 지정은 최대7일 범위다. [KR 페어 체결 이력](https://docs.upbit.com/kr/reference/list-pair-trades) | 이력 조회 기능이 없다는 주장은 틀리다. 다만 호가의 모든 변경, private events, 공통 순서·완전한 cutover는 이 API의 보장이 아니다. 체결가를 bid 경로 대체물로 바꾸지 않는다. |
| MyOrder | **명시 제공:** 주문/체결 시 이벤트, 주문 UUID·trade UUID·체결/주문/메시지 timestamp, `trade_fee`와 주문 누계. 현재 표의 `stream_type`은 REALTIME/SNAPSHOT을 모두 열거한다. [KR MyOrder](https://docs.upbit.com/kr/reference/websocket-myorder) | private snapshot이 전혀 없다고 단정하지 않는다. 그러나 이번 명세의 요청은 type/codes 중심이며 재개 offset·전체 계좌 journal sequence·마감 watermark·보존된 모든 이벤트의 replay 계약은 **미확인**. `trades_count`는 주문별 대조에 유용하나 전역 log proof가 아니다. |
| MyAsset | **명시 제공:** 자산 변화 시 balance/locked와 UUID·timestamp. **명시 제한:** 최초 구독은 변화가 있어도 초기 수분 지연될 수 있고, 변화가 없으면 데이터가 오지 않는 것이 정상이다. [KR MyAsset](https://docs.upbit.com/kr/reference/websocket-myasset) | “소켓 연결 성공/첫 메시지 수신”만으로 origin부터 누락0을 증명하지 못한다. 최초 공백의 완전 재생·공통 순서·최종 watermark 보장은 **미확인**. |
| 연결·구독·PING | **명시 제공:** snapshot과 event/주기별 realtime 구분, ticket 요청 식별자, PING/PONG 및 idle timeout. [KR WebSocket 가이드](https://docs.upbit.com/kr/reference/websocket-guide) | ticket은 source sequence가 아니고 PONG/UP은 사건 처리 watermark가 아니다. 같은 연결에 여러 항목을 구독하는 것과 거래소 엔진 공통 순서 보장은 다르다. |
| 재연결 | **명시 제공:** 공식 Best Practice는 재연결과 재구독을 설명하며 누락 방지를 위한 연결 재시도를 권한다. [KR Best Practice](https://docs.upbit.com/kr/docs/websocket-best-practice) | 이 문구를 무시하지 않는다. 다만 연결 단절 이전 offset부터 무손실 재생, 유지기간, duplicate/order 규칙 및 snapshot/live cutover를 보장하는 명세는 **찾지 못했다**. 재연결 성공을 과거 공백의 복구 완료로 자동 처리할 근거는 부족하다. |
| 잔고·개별 주문 | **명시 제공:** 포켓 잔고 조회와 UUID/identifier 기반 개별 주문 조회. [잔고](https://docs.upbit.com/kr/reference/get-balance), [주문](https://docs.upbit.com/kr/reference/get-order) | 여러 endpoint를 같은 원자적 snapshot ID로 묶거나 특정 private sequence까지 확정됐다고 증명하는 fence/version은 **미확인**. JWT 인증과 caller 문자열 account_scope 연결은 별도 운영 검토 대상이다. |
| 종료 주문·보존 | **명시 제공/상한:** 생성 시각 기준 최대7일의 조회 window, 최대1,000개, asc/desc. [종료 주문](https://docs.upbit.com/kr/reference/list-closed-orders) | **window가7일이라는 사실은 전체 보존기간이7일이라는 뜻이 아니다.** origin까지 무제한 보존, 동일 timestamp의 안정적 tie order, 호출 중 목록 변경의 snapshot isolation은 **미확인**. 포화된 한 구간을 결과 일부만으로 완전하다고 할 수 없다. |
| 입출금·포켓 범위 | **명시 제공:** 입출금 목록·상태·page 및 UUID 기반 from/to cursor. [입금](https://docs.upbit.com/kr/reference/list-deposits), [출금](https://docs.upbit.com/kr/reference/list-withdrawals) | 모든 종류의 포켓 이동/보상/정정과 전체 계좌 변동을 빠짐없이 포괄한다는 보장은 **미확인**. 현재 collector는 일부 KRW/default 완료 흐름만 지원하며 나머지를 거절한다. 조회 기능이 없다는 이유가 아니라 실제 지원 범위와 증명 의무가 다르기 때문이다. |
| 채널 간 공통 순서 | Public mark, private order/fill/asset는 각각의 시각·식별자를 제공한다. 위 채널 명세 및 [공통 가이드](https://docs.upbit.com/kr/reference/websocket-guide)를 대조했다. | **보장 미확인:** 종목 간·채널 간 total order, 같은 millisecond의 tie-break, timestamp clock domain/최대 skew, 마감 뒤 늦게 도착할 사건이 없다는 증거. local receive order로 정렬하면 재현성은 생기지만 이 외부 사실이 증명되지는 않는다. |

### 문서 차이와 조사 한계

2018 공지는 REST `sequential_id` 추가 취지에 순서 보장 표현을 사용한다. 이후 KR v1.5.9와 Global v1.2.2는 순서 미보장을 명시하고, 현재 KR WebSocket 본문은 unique로 설명한다. 검색에서 확인한 공식 KR v1.6.4 REST Response schema에도 순서 미보장 문구가 있었지만 직접 열면 현재 페이지로 redirect되고 Response schema가 생략됐다. 따라서 이 검토는 오래된 공지를 최신의 연속·무손실 계약으로 채택하지 않고, **API별 현재 공식 계약 확인이 필요한 문서 차이**로 남긴다. [2018 공식 공지](https://docs.upbit.com/kr/changelog/%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94), [확인한 v1.6.4 검색 원문 URL](https://docs.upbit.com/kr/v1.6.4/reference/list-pair-trades)

공식 도메인에서 `sequential_id/순서`, `WebSocket/재연결/누락/복구`, `resume/replay/sequence`, MyOrder/MyAsset를 검색하고 해당 본문·공통 가이드·Best Practice·REST 조회 명세를 읽었다. 검색 무결과는 기능 부재의 증명이 아니다. 일부 시도한 `.md`/잘못 추정한 slug는 web 도구에서 열리지 않았고, 실제 열리는 공식 문서 URL로 대체했다. 어떤 실패도 실제 API 호출로 우회하지 않았다.

## 4. ABA와 최고점 보호에 대한 직접적인 영향

이 절은 공식 서비스 보장에 대한 인용이 아니라 **관측 정보의 논리적 한계**다.

1. REST 첫 잔고 A → 중간 주문/체결/흐름 B → 마지막 잔고 A가 가능하면 두 끝값이 같아도 중간 경로는 알 수 없다. 새 open order가 생겼다가 종료돼 마지막 open 목록에서도 사라질 수 있다. 반복 조회는 많은 경합을 찾지만 원자성의 증명은 아니다. 코드도 같은 이유로 external fence를 요구한다.
2. 보유 수량이 일정해도 평가 mark가 A → 더 높은 값 → A로 움직였다면 끝 snapshot과 로컬 보관 해시는 중간 최고점을 복원하지 못한다. 빠진 최고점을 없던 것으로 취급하면 사용자가 정한 고점 보호 하한을 낮출 수 있다.
3. fill과 mark가 같은 timestamp일 때 어느 것이 먼저였는지에 따라 그 순간 보유 수량과 평가액이 달라진다. ID 문자열 정렬이나 수신 시각 tie-break는 계산 규칙을 정할 수 있지만, 원 계약의 실제 공통 순서 증거를 대신하지 못한다.
4. 수동 주문을 하지 않는다는 운영 약속만으로 이미 열린 주문의 체결, 외부 입출금/보상, 공급자 내부 지연까지 멈추지는 않는다. quiescence를 주장하려면 금지 범위·실제 통제·미체결 상태·위반 탐지·마감 증거를 각각 세워야 한다.

첫 거래 자체가 모든 후속 증거를 자동으로 마련하지 않는다. 반대로 보호 하한과 시작 평가액이 같다는 이유만으로 모든 주문이 논리적으로 불가능하다고도 결론 내리지 않는다. 이 조사에서 확인한 장애는 **체결 후 상태와 전체 경로를 현재 계약에 맞춰 인증하고 위험 관리에 연결하는 부분**이다.

## 5. 기존 요구를 바꾸지 않고 이어갈 수 있는 최소 단계

1. **자료 능력표를 기계적으로 분리한다.** 실제 전달 원문·채널/계좌 범위·연결 epoch·수신시각·중복·재연결·오류·조회 cursor를 보존하는 관측 산출물과, 외부 완전성을 판정하는 receipt를 분리한다. 현재 명세로 증명되지 않은 항목은 `UNKNOWN/UNPROVEN`으로 남기고 `VerifiedCoverage`를 발급하지 않는다. 기존 PR54 보관을 재사용할 범위를 설계한다.
2. **각 proof obligation의 실제 근거를 정한다.** market별 mark 시작점/변화, account/fill/fee/flow inventory, snapshot→live cutover, 재접속 복원, 공동 순서, 마지막 마감, origin 보존 및 credential-to-pocket을 따로 명시한다. UUID 중복 제거·누계 대조·cursor 조회처럼 문서에 있는 기능은 그대로 사용하되 결과를 과장하지 않는다.
3. **근거가 없는 구간은 경계로 남긴다.** source 연결이 돌아와도 이전 gap을 덮지 않는다. 새 origin/epoch 채택이 과거 최고점·하한·당일 중단을 리셋하지 않아야 한다. 자료 부족은 신규 진입과 보유 관리를 구분하며 저장/연결 실패 자체를 매도 신호로 만들지 않는다.
4. **합성 실패 검사는 외부 보장의 증명과 분리한다.** dropped/duplicate/reordered frame, 같은 millisecond, reconnect, snapshot/live overlap, fee gap, pagination saturation, ABA, source 시계 역행을 재현해 false coverage를 발급하지 않는지 검사한다. 이 통과는 실제 Upbit의 완전성 보장을 증명하지 않는다.
5. **외부 보장 확인 지점을 구체화한다.** 현재 KR API의 순서·누락 탐지·replay·retention·common watermark/atomic fence에 관한 공식 기술 계약이나 검토 가능한 추가 evidence를 확보하는 단계가 필요하다. 이 문서에서는 문의를 전송하거나 다른 회사 서비스를 연결하지 않았다. 필요한 능력이 별도로 제공될 가능성은 닫지 않는다.

## 6. 별도 설계 결정이 필요한 범위

| 변경 후보 | 필요한 결정/증명 | 이번 작업의 처리 |
|---|---|---|
| 관측 sample의 최고/최저만 보호 기준으로 삼기 | “구간 전체 실제 평가액”과 “관측 sample”의 의미 차이, 보이지 않은 최고점/손실의 처리, 기존 승인·정책 revision | 기존 사용자 보호 조건을 조용히 바꾸지 않는다. 기존 승인으로 전용하지 않는다. |
| 다른 venue/시세 공급자/별도 전용 feed 사용 | 실제 계좌 범위, 자료 권한·비용·시장/수수료·order model과 coverage 계약, 기존 서명/연구/전략 바인딩 | Upbit 외 시장 지원을 자동 추가하지 않는다. 사용자 선택과 검토 가능한 별도 설계가 필요하다. |
| 공통 순서를 모를 때 보수적 범위로 계산 | 모든 허용 순서에서 실제 high보다 낮지 않은 high와 실제 low보다 높지 않은 low라는 수학적 증명, 경계 누락·시간 불확실성, 과도한 거절의 영향 | 가능한 연구 방향이며 현재 exact contract 충족으로 주장하지 않는다. 보호 하한 완화 없이도 가능한지 먼저 입증해야 한다. |
| 외부 fence를 다른 일관성 프로토콜로 바꾸기 | snapshot/version/cutover/동시성·이미 열린 주문·외부 자금 흐름에 관한 실제 증거와 실패 정책 | 단순 두 번 조회·단일 봇 운영 약속으로 대체하지 않는다. |
| 복원 자료로 현재 계좌 경로를 이어가기 | 원 자료 신원, 당시 source coverage, 지금의 owner·정책·시간 및 전체 risk chain 재검증 | 정확한 원본 복구와 현재 사용 가능성은 별도다. 새로 받은 자료를 당시 원본으로 합성하지 않는다. |

현재 확정한 손실 하한·고점 기준·일일 조건·기한만으로 매도하지 않는 결정은 유지한다. `floor_state_check` 결과를 가정하지 않는다. 이번 결론만으로 추가 승인 질문을 반복하거나 기존 독립 개발을 중단할 필요는 없지만, **위 의미 변경을 구현으로 숨겨서는 안 된다.**

## 7. 전달 상태

완료한 것은 main56의 실제 source/refusal와 공식 문서의 능력·제한을 대조한 읽기 검토다. 계좌 접속, 실제 자료 표본, 실제 issuer, 주문 가능 판정, native Windows 운영, 수익 보장은 검증하지 않았다. 이 파일은 source authentication·coverage·activation의 새 승인 증거가 아니다.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
