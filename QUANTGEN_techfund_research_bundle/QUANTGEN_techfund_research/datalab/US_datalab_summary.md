# QUANTGEN US data lab: technical timing, valuation timing and CAPM/factor tests

Run date: 2 October 2026. Scripts: `/home/claude/datalab/scripts/us_*.py`. Results (long format `test, series, period, cost_level, metric, value`): `/home/claude/datalab/us/results/`. Charts (JSON): `/home/claude/datalab/us/charts/`.
Conventions: decide at the close of t, earn from t+1. Costs are charged per side on every unit of turnover, including the first entry, at QUANTGEN's pre-registered rates: futures 5 bp (2x = 10 bp) and US shares via KIS 50 bp (2x = 100 bp). Sharpe ratios are measured over cash: the T-bill proxy for monthly tests, French RF / T-bill for daily tests.

## 1. Bottom line for QUANTGEN

1. **Trend timing on the US index is a drawdown tool, not a return tool.** On 154 years of Shiller data the 10-month SMA rule cuts the maximum drawdown from -82% to -43/-48% and raises Sharpe. Once the averaging bias is removed, though, its CAGR is at or below buy-and-hold, and after 50 bp costs it is 1.0 pp/yr below. From 2010 to 2026 every trend rule lost to buy-and-hold by 1.7-5.2 pp/yr. This agrees with QUANTGEN's own E1 REJECT ("protects, does not outperform").
2. **The Shiller monthly-average data flatter monthly timing rules.** The standard backtest gives SMA10 a CAGR of 10.9% against 9.4% for buy-and-hold. Delaying the signal one month gives 9.1%. On French month-end CRSP data (1927-2018) the gross gap to buy-and-hold is -0.04 pp. The commonly quoted Faber-style "+1.5 pp/yr" edge is mostly an artefact of averaged prices.
3. **None of the 322 daily technical variants beats buy-and-hold after data snooping.** Hansen SPA consistent p-values are 0.82-0.97 (SPY) and 0.52-0.75 (S&P 500), and studentized p-values are 0.42-0.97. Rules picked on 1999-2009 underperformed buy-and-hold in 2010-2021 at every cost level, and from 2010 on 0 of 322 SPY variants had a mean return above buy-and-hold. Short-horizon mean-reversion rules (Connors RSI(2), Bollinger, MACD) turn negative at 50 bp per side.
4. **Valuation predicts 10-year returns in sample (R2 0.29), but is not a timing signal.** The out-of-sample R2 from 1990 is negative (-0.25 for log CAPE). From 1990 to 2013 the residuals were positive 83% of the time (+3.2 pp/yr on average). The 1-year R2 is 0.05 in sample and negative out of sample after 1990. A point-in-time CAPE de-risking rule lost 1-4.5 pp/yr. The Fed model has no post-1965 power.
5. **CAPM's security market line is flat.** The Fama-MacBeth slope is +0.46%/yr (t 0.17) against a market premium of 7.2%/yr (difference t -3.1). Low-beta portfolios had the highest Sharpe (0.65 against 0.41). GRS rejects CAPM, FF3 and FF3+Mom on both 9-portfolio sets (p < 0.01 in every period). Factor premia decayed after 2000: HML has a -32% drawdown from 2007 that had not recovered by the end of the data in 2018-11, Mom lost 49% in March-May 2009, and SMB has earned close to zero since 1981.

## 2. Key numbers

### A. Monthly index timing, Shiller S&P 500, 1872-03 to 2026-09 (cash = 10y yield - 1 pp)
`standard` = signal on month-t average price (biased up). `lag1` = signal applied one month later (no overlap with the averaged price; biased down). Month-end CRSP sits close to lag1 (section 4).

| Rule | Cost | CAGR | Vol | Sharpe | Max DD | Switches/yr | CAGR - B&H |
|---|---|---|---|---|---|---|---|
| Buy-and-hold | gross | 9.36% | 14.0% | 0.46 | -81.8% | 0 | - |
| SMA10 standard | gross | 10.89% | 9.5% | 0.78 | -42.6% | 1.35 | +1.52 pp |
| SMA10 standard | 5 bp / 10 bp | 10.82% / 10.74% | 9.5% | 0.77 / 0.76 | -42.7% | 1.35 | +1.45 / +1.38 |
| SMA10 standard | 50 bp / 100 bp | 10.15% / 9.41% | 9.5% | 0.70 / 0.63 | -43.9% / -45.3% | 1.35 | +0.78 / +0.05 |
| SMA10 lag1 | gross | 9.10% | 9.3% | 0.61 | -48.1% | 1.35 | -0.27 pp |
| SMA10 lag1 | 50 bp / 100 bp | 8.37% / 7.63% | 9.3% | 0.54 / 0.46 | -49.2% / -50.5% | 1.35 | -1.00 / -1.73 |
| MOM12 (12m TR > cash) standard | gross / 50 bp | 10.00% / 9.52% | 9.8% | 0.67 / 0.62 | -36.9% / -37.8% | 0.89 | +0.64 / +0.15 |
| MOM12 lag1 | gross / 50 bp | 8.40% / 7.92% | 9.8% | 0.52 / 0.48 | -52.2% / -53.8% | 0.89 | -0.96 / -1.44 |
| COMBO_AVG (0.5 SMA + 0.5 MOM) standard | gross / 50 bp | 10.48% / 9.88% | 9.3% | 0.75 / 0.69 | -37.4% | 1.96 | +1.12 / +0.51 |
| COMBO_AVG lag1 | gross / 50 bp | 8.79% / 8.19% | 9.2% | 0.59 / 0.53 | -40.6% | 1.96 | -0.58 / -1.18 |
| COMBO_AND (both) lag1 | gross / 50 bp | 8.49% / 7.83% | 8.8% | 0.58 / 0.51 | -37.1% | 1.24 | -0.87 / -1.54 |

By era (SMA10, gross, T-bill cash; standard / lag1 CAGR minus buy-and-hold):

| Era | B&H CAGR / Sharpe / MDD | SMA10 standard | SMA10 lag1 | MOM12 lag1 |
|---|---|---|---|---|
| 1871-1925 | 7.3% / 0.42 / -33.9% | +1.55 pp (Sharpe 0.76) | -0.06 pp (0.58) | -0.29 pp |
| 1926-1945 | 7.3% / 0.33 / -81.8% | +4.18 pp (0.67) | +1.97 pp (0.58) | +0.53 pp |
| 1946-1989 | 11.6% / 0.56 / -39.2% | +1.07 pp (0.84) | -1.10 pp (0.59) | -3.04 pp |
| 1990-2009 | 8.2% / 0.33 / -49.0% | +2.35 pp (0.74) | +1.85 pp (0.67) | +1.82 pp |
| 2010-2026 | 14.3% / 1.09 / -19.3% | -1.68 pp (1.11) | -4.13 pp (0.85) | -2.95 pp |

At 0% cash the full-sample SMA10 standard rule gives CAGR 9.50% (+0.14 pp), and the lag1 rule gives 7.73% (-1.63 pp).

### A4/A5. Valuation (Shiller, real total returns)

| Regression | Sample | Slope (NW t) | In-sample R2 | OOS R2 1950-2013 | OOS R2 1950-89 | OOS R2 1990-2013 |
|---|---|---|---|---|---|---|
| 10y real ~ log CAPE | 1881-2013 starts | -0.071 (-5.9) | 0.29 | +0.20 | +0.37 | **-0.25** |
| 10y real ~ log D/P | 1881-2013 | +0.042 (2.3) | 0.12 | -0.13 | +0.22 | -1.02 |
| 10y real ~ E/P | 1881-2013 | +0.90 (4.7) | 0.23 | +0.21 | +0.36 | -0.19 |
| 10y real ~ E/P - GS10 (Fed model) | 1881-2013 | +0.51 (1.6) | 0.11 | -0.33 | -0.27 | -0.49 |
| 1y real ~ log CAPE | 1881-2022 | -0.103 (-2.9) | **0.05** | -0.04 (1950-2022) | +0.05 | -0.18 (1990-2022) |
| 1y real ~ E/P | 1881-2022 | +0.77 (1.5) | 0.01 | +0.01 | +0.04 | -0.03 |

- Fit: 10y real return = 0.260 - 0.0708 ln(CAPE). At the last CAPE reading (30.8, 2023-09, 95th percentile) the fit implies 1.7%/yr. The price has risen another 70% since then, so CAPE is now higher still (not computable: earnings data end 2023-06).
- Residuals 1990-2013: mean +3.2 pp/yr and positive in 83% of start months. The mean OOS forecast error was +4.8 pp/yr; out-of-sample forecasts beat the historical mean in only 21% of months. Start 1990-01: CAPE 17, fit 5.9%, actual 15.0%. Start 1997-01: CAPE 28, fit 2.3%, actual 5.5%. Start 2010-2013: CAPE 20-23, fit 3.6-4.6%, actual 9.4-13.1%. The 1999-2001 starts (CAPE 37-44) were the only clear hits.
- Fed model (A5): the 10y slope is +1.01 (t 5.8, R2 0.32) before 1965 and +0.20 (t 0.4, R2 0.01) after 1965. For 1y returns the post-1965 R2 is 0.002. The correlation of E/P with GS10 was -0.06 in 1881-1964, +0.70 in 1965-1999 and -0.12 in 2000-2023: the Fed model only "works" in the 1965-1999 inflation regime, and even there it does not predict.
- Point-in-time CAPE de-risking rules (expanding percentile, applied next month), 1891-2023: cash above the 90th percentile gives -1.8 pp/yr gross, Sharpe 0.37 against 0.46. Half position above the 80th percentile gives -1.1 pp/yr, with the max drawdown cut only from -82% to -76%. In 1990-2023 the losses were -4.5 pp/yr and -3.0 pp/yr.

### B. Daily technical rules (price return + 1.8%/yr dividend accrual; signal at close t, trade from t+1)
Buy-and-hold: SPY 1999-01-05 to 2021-03-31, CAGR 7.3%, Sharpe 0.37, max DD -55.3%. S&P 500 index 2000-01-04 to 2018-12-31, 4.8%, 0.26, -55.7%.

| SPY 1999-2021 | Sharpe gross / 5bp / 50bp / 100bp | CAGR gross / 50bp | Max DD gross / 50bp | Switches/yr | Time in market |
|---|---|---|---|---|---|
| Close > SMA200 | 0.39 / 0.36 / 0.07 / -0.24 | 5.6% / 1.9% | -21% / -36% | 7.3 | 71% |
| SMA50/200 cross | 0.52 / 0.52 / 0.48 / 0.44 | 8.0% / 7.5% | -34% / -34% | 1.0 | 71% |
| MACD(12,26,9) | 0.18 / 0.08 / -0.76 / -1.60 | 3.1% / -7.6% | -39% / -85% | 21.9 | 50% |
| RSI(14) 30/70 contrarian | 0.27 / 0.27 / 0.22 / 0.17 | 4.9% / 4.0% | -52% / -52% | 1.6 | 41% |
| Connors RSI(2)<10 above SMA200, exit > SMA5 | 0.60 / 0.48 / -0.55 / -1.51 | 5.3% / -2.1% | -15% / -50% | 14.6 | 10% |
| Bollinger(20,2) mean reversion | 0.25 / 0.21 / -0.09 / -0.42 | 4.1% / -0.5% | -36% / -48% | 9.1 | 21% |
| Donchian 20/10 | 0.24 / 0.20 / -0.18 / -0.58 | 3.6% / -0.5% | -30% / -44% | 8.1 | 49% |
| 52-week-high breakout (exit -10% from high) | 0.43 / 0.42 / 0.39 / 0.34 | 5.8% / 5.3% | -21% / -22% | 0.9 | 61% |
| 12-month momentum sign | 0.47 / 0.46 / 0.33 / 0.18 | 7.2% / 5.2% | -25% / -30% | 3.7 | 76% |

The S&P 500 index 2000-2018 gives the same ranking. SMA50/200 Sharpe is 0.54 gross and 0.50 at 50 bp, against 0.26 for buy-and-hold. This is the only canonical rule whose mean beat buy-and-hold there (+1.4 pp/yr, NW t 0.49), and it is not significant.

**Data snooping (322 variants: 16 price/SMA, 62 SMA crosses, 32 MACD, 42 RSI contrarian, 60 Connors, 40 Bollinger, 29 Donchian, 24 52-week-high, 17 TSMOM).** Loss = -(net rule return - net buy-and-hold return). Settings: stationary bootstrap, block 15 (10 and 20 checked), 2,000 reps, seed 20261002.

| Series | Cost | Best variant (mean excess vs B&H) | Its Sharpe (B&H) | Excess p.a. | Naive boot p | arch SPA p consistent / lower / upper | Studentized SPA p (c / l / u) |
|---|---|---|---|---|---|---|---|
| SPY | gross | BOLL_MR(10, 1.5, exit upper) | 0.59 (0.37) | +2.1% | 0.18 | 0.82 / 0.66 / 0.83 | 0.86 / 0.69 / 0.87 |
| SPY | 5 bp | same | 0.54 | +1.4% | 0.28 | 0.92 / 0.76 / 0.93 | 0.94 / 0.78 / 0.95 |
| SPY | 50 bp | RSI_CONTRA(21, 25/75) | 0.59 | +0.5% | 0.43 | 0.96 / 0.73 / 0.98 | 0.97 / 0.75 / 0.99 |
| SPY | 100 bp | same | 0.58 | +0.4% | 0.44 | 0.94 / 0.69 / 0.99 | 0.95 / 0.70 / 0.99 |
| S&P 500 | gross | BOLL_MR(10, 1.5, exit upper) | 0.57 (0.26) | +4.1% | 0.06 | 0.52 / 0.44 / 0.53 | 0.56 / 0.43 / 0.57 |
| S&P 500 | 5 bp | same | 0.52 | +3.3% | 0.10 | 0.66 / 0.56 / 0.68 | 0.55 / 0.42 / 0.57 |
| S&P 500 | 50 bp | RSI_CONTRA(21, 20/80) | 0.43 | +2.7% | 0.05 | 0.68 / 0.49 / 0.78 | 0.50 / 0.30 / 0.59 |
| S&P 500 | 100 bp | same | 0.43 | +2.7% | 0.06 | 0.65 / 0.44 / 0.84 | 0.42 / 0.26 / 0.62 |

- The highest full-sample Sharpe in the family was CONNORS(n=3, 20, SMA200, exit SMA10) on the S&P 500 at 0.80 gross, but it is invested only 13% of the time. Vol-matched SPA (each variant scaled to buy-and-hold volatility) gives a studentized consistent p of 0.25 at best (S&P 500, gross) and 0.48 at 50 bp.
- **Time split (choose on 1999/2000-2009, hold through 2010-2021/2018):**
  - SPY gross, best IS Sharpe: CONNORS(2,10,SMA200,exit SMA10), IS Sharpe 0.95, OOS Sharpe 0.28 against buy-and-hold 0.82. OOS CAGR 3.0% against 14.0%; OOS percentile in the family 10%.
  - SPY 50 bp: SMA50/200 cross, IS 0.47, OOS 0.50 against 0.82 (CAGR 7.0% against 14.0%).
  - S&P 500 gross: CONNORS(3,20,SMA200,exit SMA10), IS 0.79, OOS 0.82 against 0.77. It was invested only 16% of the time, so OOS CAGR was 6.7% against 11.4%.
  - Every selected variant had a negative OOS mean excess over buy-and-hold (one-sided p 0.91-0.999). From 2010 the share of variants whose mean beat buy-and-hold was 0.0% (SPY) and 0.3-0.6% (S&P 500). The OOS family SPA has consistent p 0.95-0.99.
- **VIX regimes** (VIX above or below its trailing 1-year median at t; 43% of days high): trend rules lose their edge exactly when VIX is high. SPY SMA200 excess vs buy-and-hold is -8.1%/yr in high-VIX days and +1.2%/yr in low-VIX days (difference -9.3%, NW t -1.5; -13.7%, t -2.1 at 50 bp). Mean-reversion rules are only active in high-VIX states. Bollinger gross Sharpe is 0.40 high-VIX against -0.05 low-VIX, but no regime difference is significant at 50 bp.
- **Next-open execution** (instead of the signal close) changes Sharpe by -0.02 to +0.10, and none of the conclusions change.

### C. CAPM and factors (Ken French)

**C1 Security market line** (28 portfolios: 10 industries + 9 size/value + 9 size/momentum; rolling 60-month beta; next-month return):

| Period | FM slope p.a. (t) | Mkt-RF p.a. | Slope - Mkt (t) | FM intercept p.a. (t) |
|---|---|---|---|---|
| 1954-01 to 2017-03 | +0.46% (0.17) | 7.20% | -6.74 pp (-3.07) | 7.84% (3.77) |
| 1954-1969 | +4.86% (1.05) | 9.47% | -4.61 (-1.18) | 5.70% (1.49) |
| 1970-1989 | -3.98% (-0.83) | 4.84% | -8.82 (-2.14) | 10.04% (2.60) |
| 1990-2017 | +1.15% (0.26) | 7.61% | -6.46 (-1.90) | 7.48% (2.34) |
| 2000-2017 | -4.44% (-0.80) | 4.62% | -9.06 (-2.17) | 11.63% (2.99) |

- Using full-period betas, the cross-sectional slope is -2.7%/yr with an R2 of 0.02. The CAPM line has slope +7.2%.
- Beta terciles (1954-2017): low beta 0.77 gives 8.4%/yr excess, Sharpe 0.65, CAPM alpha +2.6%. Mid beta 1.02 gives 8.9%, Sharpe 0.55, alpha +1.5%. High beta 1.30 gives 8.3%, Sharpe 0.41, alpha -0.7%. High minus low is -0.1%/yr (t -0.07) where CAPM implies +3.9%/yr. The 30-portfolio set (12 industries) gives the same picture.

**C2 GRS / J tests, 1949-01 to 2017-03 (819 months):**

| Test assets | CAPM GRS F (p), mean abs alpha | FF3 | FF3+Mom |
|---|---|---|---|
| 9 size/value | 7.73 (<0.001), 3.1%/yr | 5.73 (<0.001), 1.6% | 4.68 (<0.001), 1.4% |
| 9 size/momentum | 13.62 (<0.001), 5.0% | 12.64 (<0.001), 5.1% | 7.81 (<0.001), 1.6% |

- Robust J tests (linearmodels TradedFactorModel) agree, with all p < 0.01, as do the sub-periods 1949-1982 and 1983-2017. The lowest rejection is FF3 on size/value in 1949-1982 (p 0.010).
- Largest FF3+Mom alphas: small growth S1V1 -5.5%/yr (t -4.3), small losers S1M1 -3.7% (t -3.6). FF3 leaves small winners/losers at +6.1% / -11.2%/yr (t 6.3 / -7.4).

**C3 Factor history:**

| Factor | Sample | Mean p.a. | Vol | Sharpe | t | Max DD (peak to trough) |
|---|---|---|---|---|---|---|
| Mkt-RF | 1926-07 to 2018-11 | 7.9% | 18.5% | 0.43 | 4.1 | -84.7% (1929-08 to 1932-06; recovered 1945-02) |
| SMB | 1926-2018 | 2.5% | 11.1% | 0.22 | 2.2 | -55.1% (1983-07 to 1999-03; recovered 2010-12) |
| HML | 1926-2018 | 4.4% | 12.1% | 0.37 | 3.5 | -43.5% (1933-08 to 1935-03) |
| Mom | 1949-01 to 2017-03 | 8.4% | 13.5% | 0.62 | 5.1 | -57.6% (2008-11 to 2009-09; not recovered by 2017-03) |
| 50/50 HML+Mom | 1949-2017 | 6.3% | 7.5% | 0.84 | 6.9 | -34.3% (2008-11 to 2012-02) |

- By decade (Sharpe): HML was -0.01 in the 1990s, 0.59 in the 2000s and -0.23 in 2010-2018. Mom was 1.21 in the 1990s, 0.04 in the 2000s and 0.25 in 2010-2017. SMB was 0.01 in the 1980s and -0.14 in the 1990s.
- Rolling 10-year Sharpe: HML reached -0.33 for the window ending 2018-09 (its minimum). Mom was -0.17 at 2012-09 and -0.04 at 2017-03. SMB was negative in 27% of windows.
- **HML from 2007:** cumulative -29.8% (Sharpe -0.27), max DD -32.2% to a trough in 2018-09, not recovered by 2018-11.
- **Mom 2009:** -11.5% in March, -34.6% in April and -12.3% in May, for -49.3% cumulative and -52.6% for calendar 2009. The worst months follow bear markets: in April 2009 the market's past 24 months were -41% and the market rose 10.2% that month.
- **SMB after 1981 (Banz 1981):** 1926-1980 mean 3.5%/yr, Sharpe 0.30 (t 2.2). 1981-2018: 1.1%/yr, Sharpe 0.10 (t 0.6). 1981-1999: -1.0%/yr.
- Correlation of HML and Mom: -0.18 (1949-2017); -0.12 in 1949-1979, -0.29 in 1980-1999 and -0.16 in 2000-2017.

### D. Factor ETFs, 1-year to 2026-10-01 (Stocklake; approximate, see caveat)
SPY +15.2%, MTUM +26.0% (+10.7 pp vs SPY), QUAL +14.9% (-0.3), USMV +4.4% (-10.8), IWM +15.9% (+0.7). VLUE is not available from Stocklake. Quarterly breakdowns are in `us_D_factor_etfs.csv`.

## 3. Failure episodes (dated)

| Episode | What happened |
|---|---|
| 1932-07 to 1933-06 rebound | Buy-and-hold +135%. SMA10 caught +32% and MOM12 +55% (each out for 4-10 of 12 months): the trend exit missed most of the bottom rally. |
| 1946-1989 | SMA10 lag1 -1.1 pp/yr and MOM12 lag1 -3.0 pp/yr against buy-and-hold. Long calm bull eras punish trend exits even before costs. |
| 1987-10 crash | Month-end SMA10 was still invested in October 1987 (-22.6%) and exited only for November (Sep-Nov: -24% against -30%). The lag1 rule took the full -30%. Monthly rules do not protect against one-month crashes. |
| 2009-03 to 2010-03 | Buy-and-hold +56% (Shiller avg prices); SMA10 +27% and MOM12 +10%. Daily SPY: SMA200 +19% against +71%. Missing the V-shaped recovery cost about as much as the drawdown saved. |
| 2010-2019 bull | SMA10: 5 exits, 4 of them whipsaws (2010-07..09, 2011-09..2012-01, 2015-09..11, 2018-12..2019-02), costing 15.4% of log return gross and 20.3% at 50 bp. MOM12: 4 of 4 whipsaws, -20.4%. Daily SPY SMA200: 58 switches, +102% against +246%; at 50 bp, +51%. |
| 2020-02 to 2020-04 (COVID) | Shiller monthly: every rule did worse than buy-and-hold (-18.8% against -15.3%; out only in April, missing the April rebound). Daily SPY 2020-02-20 to 03-23: SMA200 -17% against -34% (helped), then the rebound to 2020-12 gave +21% against +70%. SMA50/200 never exited. |
| 2022 | Monthly rules helped: SMA10 -3.3% against -15.0% (out 10 of 12 months); MOM12 -11.9%. |
| 1990-2013 valuation | High CAPE (25 on average) "predicted" 2.3-5.9% real returns; realised 5-15% for 1990-1997 and 2009-2013 starts. OOS R2 -0.25. Rule "cash above the 90th CAPE percentile" was out 78% of the 2000s and 98% of the 2020s, losing 4.5 pp/yr over 1990-2023. |
| Fed model after 1965 | 10y R2 0.01 (t 0.4); 1y R2 0.002. |
| HML 2007-2018 | -32.2% drawdown (trough 2018-09). Decade Sharpe 2010s -0.23. |
| Mom 2009-03 to 2009-05 | -49.3% in three months; -34.6% in April 2009 alone. Mom drawdown -57.6% from 2008-11, not recovered by 2017-03. Sharpe 0.04 in the 2000s. |
| SMB 1983-07 to 1999-03 | -55% drawdown; mean +1.1%/yr since 1981 (t 0.6). |
| Daily rules after 2009 | The best IS variants all underperformed buy-and-hold 2010-2021/2018 (gross OOS excess -5 to -12%/yr). No variant of 322 beat SPY buy-and-hold in mean after 2010. |

## 4. Robustness: the Shiller averaging bias
- The Shiller price is the monthly average of daily closes. A signal formed on the month-t average and applied to the average(t) to average(t+1) return overlaps about half a month of price action before the decision. The first-order autocorrelation of Shiller monthly returns is 0.28, against 0.11 for French month-end returns (1927-2018), the Working (1960) effect.
- Same months 1927-06 to 2018-11, gross, buy-and-hold CAGR about 9.8-9.9%:

| Rule | CAGR - B&H | Sharpe | Max DD |
|---|---|---|---|
| Shiller standard | +1.58 pp | 0.79 | -44% |
| Shiller lag1 | -0.26 pp | 0.64 | -49% |
| French month-end SMA10 (signal on the month-end TRI) | -0.04 pp | 0.55 | -43% |
| French month-end, lag1 | -0.61 pp | 0.49 | -50% |

- After 50 bp on month-end data the rule costs -0.82 pp/yr. Signal states agree 91% of the time; the gain comes from return timing, not from different signals.
- Month-end crash avoidance is real for slow bears: 1929-1932 -20% against -84%, 2000-2002 -8% against -45%, 2008-2009 -3.5% against -50%. It does not help in one-month crashes (October 1987).

## 5. SPA results and implementation notes
- `arch.bootstrap.SPA` (arch 8.0.0) **does not studentize** in this version. `compute()` uses the raw max mean loss differential; the studentize flag only sets the info label and the variance is used only for the consistent-recentring threshold. So I report (a) the arch p-values exactly as produced and (b) Hansen's studentized SPA computed from the same bootstrap draws.
- My replica reproduces arch's p-values exactly at the same seed (validation check). The loss variance matches arch's kernel estimator to 3e-13. Block-length sensitivity (10 and 20) moves the consistent p by at most 0.02.

## 6. Validation (all 30 checks PASS, `us_validation.csv`)
- **No look-ahead.** Perturbing all prices after day t leaves every signal at t unchanged for all 322 variants at 5 cut dates. The position at t equals the signal at t-1, and the first P&L day uses the t+1 return. The monthly Shiller rules pass the same perturbation test. The valuation OOS regressions train only on outcomes realised by the forecast date (training ends at t-120 for 10y).
- **Burn-in.** Window-only rules (SMA, crosses, TSMOM) are identical when the history starts 100 sessions later. 4 of 227 path-dependent variants differ, and only in the first 23 evaluation days.
- **French data.** The arch index is stored as nanoseconds; it decodes to YYYYMM, the first row is 1926-07 and the last 2018-11, with 1,109 contiguous months. Spot checks: Mkt-RF 1987-10 = -23.24%, 2008-09 = -9.24%, 2008-10 = -17.23%, 1929-10 = -20.12%, Mom 2009-04 = -34.58%.
  - linearmodels data are decimals (arch: percent), 1949-01 to 2017-03, with 12 industry columns (not 10).
  - The two vintages agree on Mkt-RF within 0.03 pp; SMB and HML differ by up to 0.37 / 0.56 pp (corr 0.9999 / 0.9996).
- **Raw data.** SPY Lean: no split-like jumps (max |return| 11.3% on 2008-10-13), OHLC consistent, ratio to the S&P 500 index/10 within 0.993-1.021. arch 'Adj Close' = 'Close' (price index, no dividends).
- **Reproducibility.** SPA p-values are identical across runs with seed 20261002.

## 7. Caveats and data problems
1. **Shiller data.**
   - Monthly average prices bias monthly timing rules upward (section 4); trust the lag1 and month-end numbers.
   - Dividends and earnings stop at 2023-06 (39 months imputed at the last 12-month yield, 1.58%; flagged in `div_imputed`). CPI, GS10 and CAPE stop at 2023-09, so no CAPE reading exists for 2023-10 to 2026-09; GS10 is carried forward for the cash leg.
   - The cash proxy (GS10 - 1 pp, floored at 0) is crude before 1920 and in 1940-1951.
   - The SP500 column has 12-13 decimal values in 2019-2023, suggesting a different vintage splice; there is no visible level break.
2. **Daily data.** Both daily series are price-only. The 1.8%/yr dividend accrual is an approximation: the actual S&P yield was 1.1-3.2% over 1999-2021. It slightly penalises time out of the market in high-yield years (2009) and flatters it in low-yield years (2000).
   - The SPY Lean file covers 1998-2021 only; its last line has no trailing newline (harmless).
   - After 2018-11 the T-bill rate comes from approximate TB3MS values typed in by hand (no network access). The effect on Sharpe is below 0.01.
3. **Family and SPA.** The 322-variant family spans 9 rule types. SPA is conditional on this family; a broader search would only raise the p-values. Three RSI(10-21, 10/90) variants never trade (excluded from Sharpe ranking; they earn cash).
4. **French data.** linearmodels has 12 industries; I used the 10 named in the task plus 18 = 28 portfolios (with 30 as a robustness set). The Mom series ends 2017-03 and the arch factors end 2018-11, so the post-2018 value recovery and the 2020-2022 value rebound are not covered.
5. **Part D (Stocklake).**
   - The series is a splice: adjusted closes to mid-June 2026 and raw 2-decimal closes after; volume units change on 2026-07-21/22 (source 'ibkr' from 2026-08-12).
   - The 1-year changes are therefore between price and total return (error up to about ±0.5-1 pp; USMV/IWM yield-dependent).
   - VLUE is not available ("history_not_found").
   - Closes were transcribed from MCP tool output into `us_D_stocklake_closes_raw.csv` (anchors and month-ends only, not the full daily file).

## 8. Implications for QUANTGEN's prior design (flags)
- **TS-mom / trend on the US index.** The prior expects Sharpe 0.4-0.8 per asset. The data show Sharpe 0.47-0.62 on SPY, but below buy-and-hold since 2010 and losing in mean after costs. As an index overlay, trend should size risk (drawdown control) and should not be scored as an alpha source. This is consistent with the E1 REJECT and the macro rule "overlay multipliers in [0.5, 1.0]".
- **US short-term technical rules (RSI/MACD/Bollinger/Donchian) at 50 bp per side.** All canonical versions lose to buy-and-hold net of costs and the family fails SPA. Recommendation: DROP as index timing signals; at most BACKLOG for futures-cost venues (5 bp).
- **Valuation (CAPE) as a direction signal: DROP.** It is CONTEXT only for long-horizon expected-return displays, and the multi-decade residual drift (1990-2013) must be shown alongside it.
- **Low beta / defensive.** A flat SML and a higher low-beta Sharpe (0.65 against 0.41) support a low-vol / defensive weight (prior US low-vol = 2). The edge is in Sharpe, not raw return (tercile returns 8.3-8.9%).
- **Momentum.** The 2009 crash (-49% in 3 months, after a -41% 24-month bear) supports the Daniel-Moskowitz bear-state gate already adopted. Momentum Sharpe 0.04 in the 2000s and 0.25 in 2010-2017 matches the macro team's "0.02 since 2008".
- **Value.** Using value as a factor needs a decay haircut: HML Sharpe -0.23 in 2010-2018 and a -32% drawdown from 2007, consistent with the -49% decay haircut. The HML-Mom correlation of -0.18 argues for combining value and momentum (50/50 Sharpe 0.84 for 1949-2017, but -0.19 for 2008-2017).
