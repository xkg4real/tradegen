# DIDM과 TRADEGEN 실거래 엔진 · 2026년 11월 28일

**판정.** QUANTGEN의 사건 자료 수집과 TRADEGEN의 오프라인 연구 연결은 상당 부분 구현됐다. DIDM을 추가했을 때 실제 순수익, 위험조정수익률, 낙폭 또는 체결 품질이 개선됐다는 전향 결과는 확인되지 않았다. 운영 경로는 DIDM 예측에 주문·한도변경 권한을 부여하지 않는다. 현재 검토 대상은 업비트 원화 현물의 매수호가 이상 판단이다. KIS·OKX로 성과를 일반화할 근거도 없다. [TRADEGEN 연구 설계](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/direction-model-study-design.md)

## 1. 어떤 성능을 개선하는가

최근 체결가보다 최우선 매수호가가 얼마나 낮아지면 신규 매수를 보류할지 정하는 비율이 BR-26의 Y다. 연구 가설은 같은 가격 이력에 거시 발표·뉴스 정보를 더하면 고정 Y나 가격만 이용한 모형보다 위험한 구간을 잘 구별할 수 있다는 것이다. 예를 들어 급락 전에 경보를 더 일찍 내도 평상시에 정상 매수를 자주 막으면 개선으로 판정하기 어렵다. 소유자가 지정한 상한은 5%이며 실제 서명한 상한이 더 낮으면 그 값이 적용된다. 손실 하한, 거래 중단, 미확인 주문 보류는 독립적으로 적용된다. “상승 가능성 75%”는 사용자가 제시한 사례이고 관측된 적중률이 아니다. C++ 계산 속도와 거래소 왕복 지연도 별개의 측정이다. [Y 연구와 서명 경계](https://github.com/xkg4real/tradegen/blob/d8f5181/docs/reviews/2026-11-28-pr79-requirements.md)

## 2. QUANTGEN 공급원과 모형

| 영역 | 구현·관측된 내용 | 남은 근거 |
|---|---|---|
| 기존 공급원 | GDELT 세계 뉴스·사건, ALFRED 미국 거시 빈티지, EDGAR 미국 공시, Kalshi 사건시장, ECOS 한국 통계, OpenDART 한국 공시의 수집 성공이 기록돼 있다. 저장소는 수신시각별 원본 버전과 해시를 보존한다. | TRADEGEN 연구 기간 전체의 연속 수집·전달, 공급원별 사용 권리와 버전 일치가 필요하다. 여섯 공급원을 모두 예측변수로 쓰는 구성은 아니다. |
| 추가 공급원 | EODHD Economic Events, Alpaca News, Massive 뉴스의 제공된 응답을 해석하는 파서가 QUANTGEN main에 있다. 별도 DATA_SOURCE 브랜치에서 접속·수집 제한, 공시 이력, GDELT 파일·사건 분류 작업이 진행됐다. | 인계 기록상 Alpaca Basic·Massive·KRX 계열은 연결 확인까지만 허용된 상태다. Alpha Vantage·Tiingo·CryptoPanic 무료 뉴스는 보류, Polymarket은 비활성이다. 첨부 MTFE의 83점은 자료 범위 점수이며 이용권과 수익률을 입증하지 않는다. |
| 사건 점수 | QUANTGEN main에 V0 점수·판단 계약, 점수 조립, 학습 기준일을 확인하는 규칙이 있다. 개발 브랜치에서는 사건 묶기·대상 연결, 시장 확인, 거시 서프라이즈, 신뢰도 갱신, 사건 충격과 합성 종단 검사를 추가했다. | 일부 신뢰 가중치는 임시값이다. 점수 생성 코드가 있다는 사실만으로 실제 시점의 보정된 점수·한국어와 영어 정답 집합·실모형 배포가 생기지는 않는다. |
| QUANTGEN 연구 관문 | Stage 0의 첫 등록 실험은 **REVISE**. 합성 자료에서 당일 직접 반응과 변동성 층은 기준을 충족했지만 지연 반응 비중과 연결망 파급의 검정력은 약 22%와 11%로 목표 80%에 미달했다. 수정 사전등록안 V0.1과 Stage 1 측정 도구가 개발 브랜치에 있다. | 최근 확인한 공식 인계에서 Stage 1~5의 실자료 통과는 미확인이다. 사람 표시 자료의 측정 타당성 → 사건연구 → 표본 밖 예측 → 비용 반영 전략 → 모의 운영 순이다. Stage 5의 등록 조건은 최소 6개월·200사건이다. 단독 매수·매도 알파는 V0에서 NO-GO다. |

[QUANTGEN 공급원](https://github.com/xkg4real/quantgen/blob/ba021da5/docs/didm/VENDOR_EVAL_2026-11.md) · [추가 공급원 계획](https://github.com/xkg4real/quantgen/blob/ba021da5/docs/didm/NEW_SOURCES_PLAN_2026-11-24.md) · [DATA_SOURCE 인계](https://github.com/xkg4real/quantgen/blob/33d358b8/DATA_SOURCE_SESSION_CURRENT.md) · [모형 개발 현황](https://github.com/xkg4real/quantgen/blob/33d358b8/DIDM_SESSION_CURRENT.md) · [Stage 0 결과](https://github.com/xkg4real/quantgen/blob/0a1d6c9/docs/didm/STAGE0_REPORT_V0.md) · [Stage 1~5 기준](https://github.com/xkg4real/quantgen/blob/ba021da5/docs/didm/PREREG_V0.md)

## 3. TRADEGEN에서 구현한 범위

- **main 병합.** #67은 QUANTGEN의 일관된 비공개 SQLite 사본이나 교환 JSON을 읽고, 행 형식·해시·수신 시각·수정 이력을 검사한다. #76은 SQLite를 최대 1 GiB까지 스트리밍으로 검사한다. 이는 입력 브리지의 한도이며, 이후 모든 모형 도구가 그만한 데이터를 처리했다는 뜻은 아니다. #72와 #75는 방향 예측 입력 계약과 재생 어댑터, #78은 방향 모형의 연구 설계다. 여섯 공급원에 대한 호환 검사는 실제 QUANTGEN 코드에 합성 자료를 넣어 검증했다. [입력 브리지](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/didm-source-bridge.md) · [예측 전달 계약](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/direction-forecast-contract.md)
- **#79·#80 검토 브랜치.** 가격·호가 기록, 15분 DIDM 수집 일지, 시점별 특성 생성, 모형 학습·동결, 전망 발행, 1단계 평가와 2단계 호가 재생을 구현했다. #80은 기준 모형 누락이나 다른 연구의 결과가 합격으로 이어지는 결함과 미래 자료 사용을 보완했다. 방향 연구 230건은 합성·오프라인 연구 도구의 회귀 검증이다. Qlib 32건도 소프트웨어 검사다. [연구 코드 구성](https://github.com/xkg4real/tradegen/blob/d8f5181/docs/didm-quantgpt-pipeline.md) · [검증 기록](https://github.com/xkg4real/tradegen/blob/af3fdfa/context/upbit-universe/gpt-20261128/PR79_오프라인_검증.md)
- **현재 수정에서 확인한 결함.** D3를 만드는 함수가 전체 교환 파일의 원본 사건 링크를 검사하지 않았고, 합성 종단 검사도 원본 사건 없이 통과했다. 수집 실행기가 사용하던 인수와 최신 QUANTGEN 수집기의 실제 인수에도 차이가 있었다. 이 두 결함은 자료의 출처와 누락 판정을 바꿀 수 있으므로 그 상태의 결과로 운영 승격을 결정할 수 없다. 변경·재검증 상태는 이번 작업 인계 기록과 연결한다.

| 모형 입력 | 실제 의미와 사용 조건 |
|---|---|
| P1~P4 | 가격에서만 만든 기준 특성. 해당 시점까지 도착한 봉만 사용한다. |
| D1 | 등록한 ALFRED·ECOS 시리즈의 새 발표나 내용 수정이 최근 24시간 안에 처음 수신됐는지 본다. 같은 값을 재조회하면 새 발표로 세지 않는다. 등록 기본안은 4주 동안 사건 수가 부족해 D1을 제외한다. |
| D2 | GDELT의 최근 96개 15분 구간 뉴스량을 최근 7일의 하루 평균과 비교한다. 96개 구간 전체 및 주간 672개 중 최소 639개의 관측이 필요하다. 조회 실패는 뉴스 0건과 구분한다. 기본 연구안의 DIDM 입력이다. |
| D3 | 통화정책과 암호화폐 규제·해킹 사건에 대한 V0 점수 평균. 승인된 연구 범위, 고정 모형·프롬프트, 실제 점수·원본 및 PC 수신 증거가 필요하다. 단순 수집 DB에는 이 점수가 생기지 않는다. |
| Q1 | 해당 위험 뉴스 유형이 관측됐는지를 나타내는 선택적 QuantGPT 범주 변수. QuantGPT가 낸 신뢰 점수를 보정된 상승 확률로 쓰지 않는다. |

기본 후보 M은 가격과 D2를 쓰고 조건을 충족한 경우에만 D3·Q1을 더한다. 가격만 쓰는 B1 및 학습 기간의 방향 빈도 B0와 같은 시점에서 비교한다. D1~D3의 연구 이용권이 없고 Q1도 사용할 수 없으면 M과 B1이 같아져 이 연구를 중단한다. [특성, 등록 기준과 사용 조건](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/direction-model-study-design.md)

## 4. 실거래 성능을 어떻게 판정하는가

1. **자료 준비와 사전등록.** whydi 또는 skymi가 허용된 일관된 SQLite 백업을 실제 분석 기준시각으로 검사하는 공동 업무 TG-MAN-012는 완료 통보를 기다린다. 운영 중인 DB에서 WAL을 버리고 복사하면 과거 자료가 빠질 수 있다. 연구용 원본·결과·이용권은 비공개로 보관한다. 계좌번호·키·기사 본문을 전달할 필요는 없다. 수집 권한과 호출 예산, 종목·기간·비용·중단 기준을 실제 관측 전에 확정하고 고정한다. [개인 PC 실행 절차](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/didm-source-bridge.md#run-locally)
2. **TRADEGEN 1단계.** 기본안은 KRW-BTC의 1시간 봉으로 향후 두 시간의 방향을 예측한다. 모형 학습·선택 후 새 구간에서 방향별 표본 수, 보정, 적중률 구간 하한, 가격 기준 대비 방향 로그손실, 전·후반 안정성을 본다. 기본 일정은 준비 1주, 학습 4주, 전향 관측 6주다. 이는 설계안으로 시작일과 통과가 확정된 일정은 아니다. 연구에 D3와 Q1을 함께 쓰면 M 대 B1 비교로 측정되는 것은 두 정보원을 포함한 전체 증분 효과다. DIDM만의 기여를 수치로 주장하려면 Q1 조건을 동일하게 둔 비교도 사전등록해야 한다. [설계 6·7절](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/direction-model-study-design.md)
3. **TRADEGEN 2단계.** 1단계 통과 뒤 동일한 새 호가 기록에서 고정 Y, 가격 전용 적응형 Y, DIDM 포함 적응형 Y를 비교한다. 기본 순차안은 최소 약 14일을 추가해 경보 시점, 추가 경보 횟수, 유효 호가·예측 구간 비율을 평가한다. 1단계의 배치 예측을 사후에 실시간 발행한 예측처럼 쓰지 않는다. 이 단계에는 실제 주문·체결이 없다. [호가 재생과 표본 조건](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/direction-model-study-design.md)
4. **운영 적용.** 실제 수수료·스프레드·슬리피지와 체결 결과에 대한 별도 검토, 모델·자료의 버전과 적용기한, 위험 감시 및 소유자의 코드·전략·활성화 절차가 남는다. 현재 DIDM 덕분에 순수익이나 샤프비율이 올랐다는 수치는 없다. 첫 거래 전략의 별도 48시간·577개 관측 단축 프로토콜은 DIDM의 11주 연구를 대체하지 않는다. [첫 거래 단축 프로토콜](https://github.com/xkg4real/tradegen/blob/3ef3f9a/docs/research/2026-11-06-shortened-prospective-protocol.md)

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다.
