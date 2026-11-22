# TRADEGEN 전략 검증 기록 · 2026년 11월 23일

기존 과거 연구에서 실거래 후보의 사전 조건을 모두 충족한 전략은 0개다. 소스 `1fd87928d79a4819c3bace0255cf190f0bdeb712`에 저장된 연구 입력 12개와 산출물 6개의 해시를 확인했다. 8개 자산에 각각 2,676개 설정을 적용한 21,408개 조합을 선발 원장과 대조했다. 이후 고정 선발된 6개 자산·전략의 평가 구간 일별 기록 6,850행으로 전략과 비교 기준의 누적 수익률 12개를 다시 계산했다. 원본과의 차이는 각각 절댓값 1e-10 이내였다. [결과 원문](https://github.com/xkg4real/tradegen/blob/1fd87928d79a4819c3bace0255cf190f0bdeb712/docs/research/2026-10-31-strategy-lab/results/summary.json)

| 평가 자산 | 전략 연환산 복리수익률 | 비용 반영 동일 자산 단순 보유 | 전략 샤프비율 |
| --- | ---: | ---: | ---: |
| BTC/KRW | 7.87% | 57.39% | 0.742 |
| BTC/USDT | -1.88% | 54.45% | 0.059 |
| ETH/USDT | 9.54% | 24.03% | 0.835 |
| QQQ | -4.37% | 32.41% | -0.301 |
| SPY | -2.37% | 22.00% | -0.150 |
| TIGER 200 | 13.52% | 49.54% | 0.633 |

GLD와 TLT는 검증 단계에서 선발된 설정이 없었다. 최종 6개의 복리수익률은 세 자산에서 양수였으나 자산별 단순 보유와 비교하면 여섯 전략 모두 뒤처졌다. 이 수치는 고정된 과거 평가 구간에 대한 결과다. [연구 논문 PDF](https://github.com/xkg4real/tradegen/raw/1fd87928d79a4819c3bace0255cf190f0bdeb712/docs/research/2026-10-31-strategy-lab/paper/TRADEGEN_Strategy_Research.pdf)

다음 전향 연구는 구현·검토된 수집 코드와 유효한 비공개 상품 조건으로 계획을 고정하고, 첫 관측 전에 공개한 계획에 맞춰 5분 간격 실제 호가 577개를 48시간 동안 수집한다. PR #65의 정책 답변과 병합, A1/A2 구현, 실제 관측은 대기 중이다. [전향 연구 프로토콜](https://github.com/xkg4real/tradegen/blob/1fd87928d79a4819c3bace0255cf190f0bdeb712/docs/research/2026-11-06-shortened-prospective-protocol.md)
