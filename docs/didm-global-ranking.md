# 공개 사건의 수치화와 시장 간 기대 초과수익 비교

`python -m tools.research.didm_global_ranking STUDY.json evidence --catalogue instruments.csv`는 지정한 결정 시각에 발표된 사실을 수치화하고, 자료가 갖춰진 상품의 비용 차감 기대 초과수익을 비교한다. Python 표준 라이브러리로 실행한다. 출력은 연구 기록이며 실행권한 필드는 항상 거짓이다.

## 사건에서 방향과 크기를 구하는 방법

이 규격 v1은 금액, 물량, 비율 등 단위가 정해진 지표와 사전에 관측된 같은 기간·단위의 기준값을 사용한다. 예를 들어 회사가 이전 분기 발표에서 제시한 6,500과 새 분기 보고 매출 7,192가 모두 백만 달러라면 (7,192−6,500)÷6,500은 +0.106461538…이다. 이것은 회사 가이던스 대비 +10.65%라는 뜻이다. 시장 컨센서스나 주가 기대수익률은 별도 자료가 필요하다. 기준 유형에는 회사 가이던스, 설문 컨센서스, 이전 관측값, 사전등록 기준선이 있다.

사건 및 기준의 `event_id,event_series,metric,unit,period`를 대조한다. 원시 변화율은 `(발표값−기준값)/abs(기준값)`이고 모형 입력은 이를 [−1,1]로 제한한다. 기준값이 0이거나 결측이거나 첫 발표 뒤에 알려진 경우에는 계산을 보류한다. 적절한 기준·단위가 없는 서술형 사건은 이 버전에서 미측정이다. 최초 발표와 정정은 서로 다른 해시를 사용한다. 연속된 version과 바로 전 해시 supersedes를 요구하며 당시 이용 가능한 버전만 선택한다.

## 연구 입력

- study에는 `schema=tradegen.global_didm.v1`, 사건 및 기준 식별자, `event_series`, UNIX UTC 초 단위 결정시각, horizon_seconds, 통화 numeraire, 공통 benchmark, reference 해시, observations 해시 목록, candidates 목록이 필요하다. clock 필드 `information_clock`은 기본 `receipt`이며 실제 수신 기록을 따른다. 명시적인 `public_reconstruction`은 원 발표 시점에 공개 정보를 알 수 있었다고 가정하는 회고 연구다. 출력은 그 가정과 실제 기록 시각을 함께 보존한다.
- 원천 바이트를 `put_source`로 저장하면 파일명은 `SHA256.blob`이다. 필드 추출 기록은 `put_evidence`로 저장하며 `SHA256.json`이다. 모든 기록은 `source_uri,source_sha256,published_at,received_at,kind`를 포함한다. 지문은 보관한 바이트에 대한 증거다. 공시의 진위, 추출의 정확성, 연구자가 과거에 실제로 수신했다는 사실은 원천 및 수집기록과 별도로 대조해야 한다.
- `observation`과 `reference`는 사건·사건군·지표·단위·기간의 5개 키와 10진수 문자열 `value`를 공유한다. 최초 관측 version은 1, 그 이후부터 supersedes는 직전 관측 해시다. reference에는 `reference_type`을 넣는다.
- 외부 종목 목록은 CSV 전체의 바이트 지문을 `catalogue_sha256`으로 등록한다. 목록의 역사 시각과 실제 수신 시각은 `catalogue_as_of,catalogue_received_at`로 분리하며 결정 뒤의 목록은 허용하지 않는다. 헤더는 `instrument_id,family,venue,symbol,payoff_id,market_access,response,costs`이고 필요하면 `listing_status,terms_sha256`를 함께 추가한다. 빈 response/costs는 결측을 뜻한다. 식별자는 거래소·종목·계약의 조합과 일대일로 연결한다. 거래소가 제공한 새로운 family도 목록에 보존한다. 옵션·선물·스왑·ETN·구조화채권·워런트에는 계약 조건 지문이 필요하다. 펀드·FX·실물상품도 비교 근거를 검증한다. 직접 매수할 수 없는 지수와 코인 기준정보는 REFERENCE_ONLY, 새 상품군은 평가 구현 전까지 UNMODELED_FAMILY로 남긴다. missing_families는 기존 6개 핵심 유형에 대한 별도 점검이다. listing_status가 placeholder 또는 unverified면 선발에서 제외한다. Kalshi처럼 한 계약의 YES/NO가 다른 지급을 가지면 payoff_id를 분리한다. 바이너리 계약·ELN은 계약 원문 지문이 있어야 평가한다.
- 상품별 `response`와 `costs`는 공통 사건군·지표·단위, 상품 5개 식별필드, `horizon_seconds,benchmark,numeraire,return_basis=total_return_on_invested_cash`를 일치시켜야 한다. 모델에는 `score_method=relative_surprise_clamped_v1,reference_type,intercept_bps,beta_bps,training_end,valid_through`를 넣는다. beta는 사건 점수 1단위당 기대 초과수익(bp)이다. 해당 상품의 거래·배당·쿠폰·계약 지급을 반영한 수익으로 사전에 추정한 계수와 학습 증거가 필요하다. 기초지수 변화에 ETF의 배수를 곱해 계수를 대신하지 않는다. 이 CLI는 추정 결과를 적용하며 훈련 표본의 적정성이나 예측력은 증명하지 않는다.
- 비용에는 `execution_bps,fx_bps,tax_bps,other_bps,valid_through`가 필요하다. 투자 원금 기준 왕복 비용이며 증거상 0인 경우에도 0을 명시한다. 외국 통화 수익을 기준 통화로 변환한 기대 효과는 응답 계수, 환전 수수료는 비용에 넣는다. 상품가격수익에 이미 반영된 보수나 투자비용을 중복 차감하지 않는다.
- 부호 있는 비용 차감 예상 초과수익(bp)은 `intercept_bps + beta_bps × 사건 점수 − 비용`이다. 같은 비교 기준을 충족하는 상품만 순위를 받는다. 음수와 0도 결과표에 남기며 양수만 선발 후보가 된다. 동률은 동일 순위로 기록한다. 누락 후보가 있으면 비교 가능한 1위와 선언한 우주 전체의 1위를 구분한다. 카탈로그가 전 세계 상품을 망라한다는 보장은 없으며 관측하지 못한 상품군은 missing_families에 남긴다.
- market_access는 자료 제공자가 표시한 unknown·unavailable·paper_only·reported_access 중 하나이다. 이 항목은 추정 성과 순위를 바꾸지 않으며, 체결 가능한 가격·세금·계좌 적격성·소유자 위험정책 등은 주문 계층이 다시 확인해야 한다.

검산 명령은 `python -m unittest tools.research.test_didm_global_ranking`이다. 테스트에 사용한 가격과 반응계수는 합성 자료다.

사건을 식별하려면 발표자·사건 ID·버전·지표·단위·공표시각·원본 해시를 함께 이용한다. `raw_surprise`는 현재 모델이 정의한 부호 있는 상대차이며 출력할 때 ±1로 자르지 않는다. 응답 모형의 `relative_surprise_clamped_v1` 변환이 이 값을 [-1,1]로 제한한다. 서로 다른 사건이나 극단치가 같은 점수를 가질 수 있으므로 스칼라를 고유 식별자로 사용할 수 없다. `delisted`, `closed`, `expired`, `inactive`, `settled`, `halted`는 목록에 보존하고 평가 시점의 거래 중단 사유를 기록한다.

## 공개 상품 목록 수집

`python -m tools.research.didm_public_catalogue kalshi_current NEW_FOLDER`는 상태·산업·거래량 필터 없이 계약을 조회하고 서버의 빈 커서까지 반복한다. 오래된 시장은 `kalshi_historical`, 일반 이벤트는 `kalshi_events`, 복합 이벤트는 `kalshi_multivariate_events`, 시리즈는 `kalshi_series`로 각각 새 폴더에 수집한다. 제공자는 현재·과거 시장의 시간 경계를 이동시킬 수 있다. 엔드포인트별 `complete`는 여러 페이지가 동일 시점의 전체 시장을 보장하지 않는다. 국가·계정별 접근 권한은 확인되지 않았다. [시장 목록](https://docs.kalshi.com/api-reference/market/get-markets) · [역사적 시장](https://docs.kalshi.com/api-reference/historical/get-historical-markets) · [복합 이벤트](https://docs.kalshi.com/api-reference/events/get-multivariate-events)

`upbit`, `coinbase`, `binance_spot`, `binance_usdm`, `binance_coinm`, `coingecko`도 같은 명령을 사용한다. 거래소·거래쌍·지급구조를 분리하고 코인 기준정보는 주문 대상에서 제외한다. 코인 증거금 inverse 선물은 지급 산식의 호가 관행을 나타내며, 그 자체로 하락에 투자한 포지션이 되지는 않는다. [업비트](https://docs.upbit.com/kr/reference/list-trading-pairs) · [코인베이스](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-all-known-trading-pairs) · [Binance](https://developers.binance.com/docs/derivatives/coin-margined-futures/market-data/rest-api/Exchange-Information) · [CoinGecko](https://docs.coingecko.com/reference/coins-list)

`--max-pages N`은 표본 수집용이다. 같은 경로를 덮어쓰지 않는다. `coverage.json`에는 페이지·수신 객체 수·중복·불일치·오류·종료 사유가 있다. `pages.jsonl`과 압축 원문으로 재검증할 수 있다. `observations.sqlite`의 `entries`는 한 상품의 첫 구조 기록, `rejects`는 식별할 수 없는 페이지와 행 번호다. 행사·시리즈·복합 다리 정보는 별도 식별되며 원본에서 계약·증거를 대조할 수 있다. 한 복합계약의 구성 다리를 독립된 계약 거래로 계산하지 않는다. 수집된 두 방향은 원문 계약 검증 전까지 서명·연구 순위 근거로 삼지 않는다. HTTP 거절, 비정상 커서, 변경된 중복·불완전 자료는 일부 수집으로 보고된다. 결과 `candidates.csv`는 해시를 별도 등록하여 글로벌 연구 평가기로 가져올 수 있다. 주문 가능 여부는 `unknown` 또는 `unavailable`이다.

## 통합 발굴 목록에서 연구 후보를 연결하기

`python -m tools.research.didm_discovery_bridge unified_discovery.csv.gz bindings.json study.json evidence`는 전체 압축 목록의 SHA-256을 대조하고, 지정한 기록만 별도의 연구 평가기에 보낸다. study는 위 규격에서 `candidates=[]`로 두고 별도 catalogue를 지정하지 않는다. 입력 예시는 다음과 같다.

```json
{
  "archive_sha256": "<압축 파일 전체의 SHA-256>",
  "bindings": [
    {"record_key": "<발굴 기록 키>"},
    {"record_key": "<다른 기록 키>", "listing": "<listing 증거 해시>",
     "response": "<response 증거 해시>", "costs": "<costs 증거 해시>"}
  ]
}
```

- 첫째 형식은 목록에 기록된 출처·관측 단위·상품·지급 방향·상태를 조회한다. 현재의 목록 등재 사실만으로 과거 후보나 수익을 만들지 않는다. 체인 자산과 지수 등 기준정보에는 순위를 부여하지 않는다.
- 둘째 형식에는 독립적인 당시 근거에서 추출한 `kind=listing` 기록이 필요하다. `put_source`와 `put_evidence`로 원문과 추출값을 보관한다. 공통 원천·시각 필드 외에 발굴 행의 `dataset,source_id,unit,product_class,symbol_or_contract,venue_or_chain,side`와 평가기의 `instrument_id,family,venue,symbol,payoff_id`, 당시 `listing_status`, 적용 구간 `as_of,valid_through`를 기록한다. 출처와 해시의 확인은 발행기관이나 사용자가 해석한 근거의 진위를 보장하지 않는다.
- 계약은 binding에 `terms_sha256`도 넣는다. Kalshi·Polymarket의 YES/NO는 각각 해당 방향의 근거를 사용한다. 원본에 있는 outcome_token_id와 settlement_group도 listing 기록과 일치해야 한다. 미지원 지급 방향은 UNMODELED_PAYOFF로 보존한다. 당시 활동 중지 상태, 미수신, 유효기한 종료, 기록 미발견은 이유와 함께 남긴다. 현재 목록의 상장폐지 표시를 보존한다. 그 표시보다 과거인 시점의 상장 여부는 당시 독립 근거로만 확인한다.
- `archive_records_by_unit, requested, matched, submitted, scored`는 각각 관측 단위별 원본 행 수, 요청·일치·평가 제출·점수 산출 건수다. `submitted_subset_ranking`은 검토자가 요청하고 당시 상장을 입증한 일부 상품 간의 비교이다. 전 시장 또는 과거 전체 상장 종목의 성과를 주장하려면 표본 선정 기준과 당시 전체 모집단을 별도로 입증해야 한다. 어떤 결과에도 주문 권한이 생기지 않는다.

검산은 `python -m unittest tools.research.test_didm_discovery_bridge`로 실행한다.
