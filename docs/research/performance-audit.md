# 연구 장부의 수익·현금 보유 검산

기존 `research_lab.run`을 마친 뒤 저장소 루트에서 다음 명령을 실행한다. 첫 인자는 `summary.json`과 `selected_daily.csv`가 함께 있는 결과 폴더다. Python 표준 라이브러리만 사용한다.

```sh
python -m research_lab.performance_audit docs/research/2026-10-31-strategy-lab/results > performance-audit.json
```

결과는 자산·통화·후보·구간별로 독립적이다. 수익률과 낙폭은 퍼센트, 수익률 차이와 비용 효과는 퍼센트포인트다. 최초 보유액 1에서 전략과 매수·보유 장부의 순일수익률을 각각 한 번씩 복리로 연결한다. 두 장부에는 기존 연구의 최초 거래 및 종료 청산 비용이 이미 반영돼 있다. 자산 자체의 시가·종가 등락률을 조사하려면 같은 달력의 가격 원본이 추가로 필요하다.

| 항목 | 해석 |
| --- | --- |
| `strategy_return_pct`, `costed_buy_hold_return_pct`, `strategy_minus_buy_hold_pp` | 전략, 같은 기간 비용을 지불한 매수·보유, 두 계좌 수익률의 차이 |
| `strategy_max_drawdown_pct`, `buy_hold_max_drawdown_pct` | 시작값을 포함해 일별 순평가액의 고점에서 저점까지 하락한 최대 비율. 하락폭을 양수로 표시한다. |
| `days_with_exposure`, `average_held_exposure_pct` | 전일 종가 거래 후 보유 비중이 있어 당일 가격 변동에 노출된 날 수와 전체 구간의 평균 보유 비중 |
| `benchmark_up_days`, `exposed_on_benchmark_up_days_pct` | 매수·보유 장부가 오른 날짜 수와 그중 전략이 일부라도 보유했던 날의 비율. 하락일도 같은 방식으로 집계한다. 해당 방향 날짜가 없으면 비율은 null이다. |
| `turnover_days`, `total_turnover` | 거래대금이 거래 직전 자산의 1e-12를 초과한 날짜 수와 일별 거래대금/거래 직전 자산의 합계. 동일한 수치 허용오차를 노출 일수 산정에 쓴다. |
| `same_exposure_fee_drag_pp` | 기록된 당일 비용 차감 전 수익 경로와 차감 후 수익 경로의 복리 격차. 비용이 없었다면 보유 수량이 바뀌었을 효과는 추정하지 않는다. |

`cash_throughout`은 유효한 장부의 전체 구간에서 노출·거래가 없었던 경우다. 후보 미선정은 `no_selected_candidate`, 연구가 기록한 자료 부족은 `insufficient_data`, 선정 후보의 예상 일수 또는 기간 경계가 맞지 않으면 `incomplete_selected_ledger`로 표시한다. 이 세 경우 수익률은 비워 둔다. 마지막 경우 명령의 종료 코드는 1이다. 날짜 역전, 기록 중복, 비용이나 보유 비중의 모순, 저장한 요약과의 누적 수익률 불일치는 오류다. 장부와 요약 파일 해시를 결과에 포함한다. 거래소 달력이나 실제 체결 자료를 인증하는 도구는 별도로 필요하다.
