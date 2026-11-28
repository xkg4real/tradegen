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
