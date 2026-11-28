# 호가 단위 상방 기회 모의 연구

`tools.research.didm_upside_candidate`는 Upbit 원화 현물 한 종목에서 다음 시간봉이 닫히기 전에 상방 후보를 기록한다. 이미 독립 연구 프로그램에서 수신한 전망이 유효한 동안, 각 호가에서 직전 매도호가로 사고 현재 매수호가로 팔았을 때의 **과거** 변화를 계산한다. 양쪽 수수료와 슬리피지를 적용한 변화가 사전 등록한 모멘텀 문턱에 도달해야 한다. 체결 가능한 수량, 현재 스프레드 및 보호 상태도 확인한다. 이 수치는 이후 보유 수익을 예측한 값이 아니다.

세 비교군은 같은 종목·시각·호가·비용을 사용한다. `q-M`은 DIDM 특성을 포함한 동결 M 전망의 상방 판정과 최소 신뢰값을 추가로 요구한다. `q-B1`은 가격 기반 B1 전망에 같은 조건을 적용한다. `q-price`는 공통 호가 모멘텀과 보호 조건만 적용하는 이진 기준이다. `p_up`은 원래 예측 기간의 확률이다. 이진 기준에는 확률값을 넣지 않는다. 비교군 ID는 각각 `sha256_ascii(["tradegen-upside-quote-momentum-v1", terms_sha, arm])`으로 계산한다.

## 증거 준비

- 시작 시각 전에 연구 조건의 정규 JSON SHA-256을 독립적으로 보존한다. `validate_terms`에 정의한 정확한 필드를 사용한다. 종목·범위·시각·호가 간격, 허용 처리 지연과 만료, 시간봉 전망 기간과 문턱, 두 원본 모델 해시, 주문 크기를 나타내는 연구용 금액·양방향 비용·스프레드·모멘텀 문턱, 연구 증거 검증 프로그램의 해시와 Ed25519 공개키를 고정한다. 이 키는 독립 연구 프로그램용이다. 계좌나 주문 서명키는 사용하지 않는다.
- `prospective_direction_study`의 사전 등록, 상방을 통과한 Stage 1 최종 보고서, Stage 2 실시간 발행 기록이 필요하다. 최신 원장 체크포인트와 각 원본 해시는 운영자가 별도로 확인한다. 매번 확인할 것은 프로그램 원본, 데이터 사용 권리, 수신 시각과 누락 기록이다. 로컬 해시만으로 자료 출처나 소급 생성 여부를 인증할 수 없다.
- 호가 수집기의 `quotes.jsonl`에는 같은 초의 bid/ask가 있지만 수량은 없다. 별도 `support.json`에는 `quote_sha256, market, at, book, status`를 넣는다. `book`은 동일 시장·초인 거래소 호가의 `market, timestamp`(밀리초), `orderbook_units[0]`의 `bid_price, ask_price, bid_size, ask_size`를 담는다. 가격과 수량은 자릿수를 보존한 십진 문자열이다. `status`에는 같은 범위·초의 `scope, at, floor_halt, daily_stop, block_causes, complete`가 필요하다. 기존 BID_GAP 보류도 보존한다. 자료가 없으면 파일 내용으로 JSON `null`을 써서 미관측을 기록한다. 런타임 상태가 해소되지 않았거나 양쪽 수량이 부족하면 상방 진입을 제시하지 않는다.
- 두 호가가 연속이고 원본 전망·원장 수신이 의사결정 호가보다 앞서야 한다. 같은 초로 선후관계를 입증할 수 없는 전망은 다음 호가를 기다린다. 누락·만료한 근거는 `unavailable`로 남기고, 실제 관측에서 조건을 충족하지 못한 경우 `neutral`을 기록한다.

## 호가별 기록과 평가

실제 공급자가 허용한 자료를 안전한 비공개 폴더에 보관한다. 아래 이름은 해당 자료 위치를 가리킨다. 출력은 새 파일명으로 만든다. `propose`는 최신 체인 끝을 확인하고 로컬 현재 시각을 부여한다. 과거 호가를 방금 포착한 기회로 다시 발행할 수 없다.

```text
python -m tools.research.didm_upside_candidate propose --terms terms.json --terms-sha TERMS_SHA --support support.json --quote-dir QUOTES --quote-head QUOTE_SHA --study-dir STUDY --study-head STUDY_SHA --out proposal.json

python -m tools.research.didm_upside_candidate confirm --terms terms.json --terms-sha TERMS_SHA --support support.json --quote-dir QUOTES --quote-head QUOTE_SHA --study-dir STUDY --study-head STUDY_SHA --proposal proposal.json --receipt independent-receipt.json --out paired-signals.json
```

독립 연구 프로그램은 조건·상태와 원본 파일을 대조하고 제안을 실제로 수신한 시각을 기록한다. 영수증의 `body`에는 `format="tradegen-upside-independent-receipt-v1", program_sha256, proposal_sha256, received_at`가 있고, `signature`에는 그 body의 정규 ASCII JSON 바이트에 대한 Ed25519 서명(소문자 128자리 hex)이 있다. 로컬 프로그램은 서명을 만들지 않는다. `confirm`은 원래 원장 위치에서 제안을 다시 계산하고 독립 영수증을 검증한다. 공개 저장소에는 개인 호가 파일, 위험 상태, 개인 연구 금액, 연구 서명을 올리지 않는다.

확정 파일은 `tradegen-upside-signals-v1` 형식이다. 신호 수신 전의 가격은 진입가로 사용할 수 없다. 연구 기간에 보류와 손실 사례를 포함한 모든 시각의 제안·영수증·누락을 보관한다. 비교 평가기는 모든 군에 `quote_gate="corroborated"`와 같은 기간을 적용하고, 수신 이후의 첫 별도 적격 호가에서 수량·손실 하한·보류 상태를 다시 확인한다. 해당 호가를 확인할 수 없는 구간은 결측으로 표시한다. 실제 체결을 시험하거나 수익성을 입증한 기록은 아직 없다.
