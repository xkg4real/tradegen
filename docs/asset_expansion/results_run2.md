# Asset-expansion validation study

Run 2026-09-27 · seed 11 · results.csv md5 `76ef0621a7d317e01ca2d81eb4e4786b` · gate `core/quant/validate.py`

Every strategy: purged walk-forward (IS 756 / OOS 126 sessions), signals on close t, earn from t+1, pre-registered per-side costs (KRX ETF 3 bp, US via KIS 50 bp, KRX stock 35 bp, crypto 10 bp, futures 5 bp) and a 2× stress. PASS needs the bootstrap 90 % Sharpe interval above zero, deflated Sharpe ≥ 0.95, PBO ≤ 0.05, OOS/IS ≥ 0.5, ≥ 60 % positive years, survival at 2× costs, a parameter plateau and ≥ 100 trades. Distributional models need Kupiec, Christoffersen, 90 % coverage and PIT tests over ≥ 500 origins.

| Card | Kind | Decision | Reason | Key numbers |
|---|---|---|---|---|
| S_E1_trend_us | strategy | **REJECT** | PBO above 0.20 | SR_OOS 0.84 [0.47, 1.20], DSR 1.00, PBO 0.59, 2× costs 0.75, years+ 74%, trades 82, bench SR 0.95 |
| S_E1_trend_krx | strategy | **REJECT** | deflated Sharpe below 0.95 | SR_OOS 0.52 [-0.03, 1.04], DSR 0.84, PBO 0.31, 2× costs 0.52, years+ 67%, trades 37, bench SR 0.74 |
| S_E2_voltarget_spy | strategy | **REJECT** | PBO above 0.20 | SR_OOS 0.63 [0.34, 0.92], DSR 1.00, PBO 0.28, 2× costs 0.59, years+ 72%, trades 185, bench SR 0.56 |
| S_E2_voltarget_kodex200 | strategy | **REJECT** | does not beat its benchmark (Sharpe difference -0.13, p 0.81) | SR_OOS 0.53 [0.08, 0.97], DSR 0.96, PBO 0.10, 2× costs 0.53, years+ 67%, trades 67, bench SR 0.66 |
| S_E3_riskparity_us | strategy | **REJECT** | PBO above 0.20 | SR_OOS 0.89 [0.51, 1.27], DSR 1.00, PBO 0.35, 2× costs 0.87, years+ 84%, trades 142, bench SR 0.86 |
| S_E5_xsmom_sectors | strategy | **REJECT** | PBO above 0.20 | SR_OOS 0.48 [0.16, 0.76], DSR 0.97, PBO 0.39, 2× costs 0.36, years+ 84%, trades 131, bench SR 0.63 |
| S_B3_tsmom_futures | strategy | **REJECT** | deflated Sharpe below 0.95 | SR_OOS 0.08 [-0.27, 0.43], DSR 0.27, PBO 0.10, 2× costs 0.06, years+ 61%, trades 174, bench SR 0.58 |
| S_C3_crypto_trend_btcusd | strategy | **REVISE** | plateau check failed (plateau) | SR_OOS 1.20 [0.74, 1.64], DSR 1.00, PBO 0.11, 2× costs 1.17, years+ 82%, trades 174, bench SR 0.89 |
| S_C3_crypto_trend_krwbtc | strategy | **PASS** | every gate criterion met | SR_OOS 1.31 [0.72, 1.86], DSR 1.00, PBO 0.41, 2× costs 1.26, years+ 75%, trades 141, bench SR 0.79 |
| S_E8_pairs_kodex_tiger | strategy | **REJECT** | PBO above 0.20 | SR_OOS 0.55 [0.30, 0.81], DSR 0.97, PBO 0.45, 2× costs -0.32, years+ 73%, trades 232, bench SR nan |
| S_S6_pairs_samsung_pref | strategy | **REJECT** | PBO above 0.20 | SR_OOS 0.83 [0.48, 1.18], DSR 1.00, PBO 0.22, 2× costs 0.77, years+ 74%, trades 102, bench SR 0.85 |
| S_S6_pairs_hyundai_kia | strategy | **REJECT** | deflated Sharpe below 0.95 | SR_OOS 0.43 [0.08, 0.75], DSR 0.86, PBO 0.20, 2× costs 0.31, years+ 58%, trades 66, bench SR nan |
| S_E8_pairs_gld_iau | strategy | **REJECT** | deflated Sharpe below 0.95 | SR_OOS -2.28 [-2.53, -2.03], DSR 0.00, PBO 0.00, 2× costs -2.40, years+ 0%, trades 109, bench SR nan |
| S_V1_vix_rolldown | strategy | **REJECT** | deflated Sharpe below 0.95 | SR_OOS -0.14 [-0.58, 0.30], DSR 0.28, PBO 0.93, 2× costs -0.22, years+ 38%, trades 341, bench SR 0.54 |
| S_V3_fx_momentum | strategy | **REJECT** | deflated Sharpe below 0.95 | SR_OOS -0.59 [-1.25, 0.07], DSR 0.06, PBO 0.35, 2× costs -0.89, years+ 17%, trades 65, bench SR nan |
| S_V4_dollar_carry | strategy | **REJECT** | deflated Sharpe below 0.95 | SR_OOS 0.27 [-0.42, 0.93], DSR 0.74, PBO nan, 2× costs 0.27, years+ 67%, trades 68, bench SR nan |
| M_B1_dns | model | **REJECT** | 0/5 maturities beaten, 0/5 significant | dm_t_min 0.589 |
| S_B2_pca_fly | strategy | **REVISE** | see lines | adf_p 0.00763 |
| D_C2_garch_btc | distribution | **REVISE** | tails, clustering, coverage, pit failed | kupiec95_p 0.0267; kupiec99_p 0.382; cc_p 0.000603; pit_ks_p 0.0663 |
| D_Q_garch_spy | distribution | **REJECT** | PIT fails at the 1 % level | kupiec95_p 5.56e-05; kupiec99_p 0.000208; cc_p 0.000212; pit_ks_p 0.00298 |
| D_Q_garch_kodex200 | distribution | **REJECT** | PIT fails at the 1 % level | kupiec95_p 8.22e-05; kupiec99_p 0.00027; cc_p 0.000135; pit_ks_p 0.0004 |
| D_C2_gjr_btc | distribution | **REVISE** | tails, clustering, coverage, pit failed | kupiec95_p 0.0456; kupiec99_p 0.474; cc_p 0.00588; pit_ks_p 0.0445 |
| D_Q_gjr_spy | distribution | **REVISE** | tails, clustering, pit failed | kupiec95_p 5.56e-05; kupiec99_p 0.00111; cc_p 0.000283; pit_ks_p 0.0142 |
| D_Q_gjr_kodex200 | distribution | **REJECT** | PIT fails at the 1 % level | kupiec95_p 1.6e-05; kupiec99_p 0.000481; cc_p 3.82e-05; pit_ks_p 0.000517 |
| M_C1_kimchi | model | **REVISE** | descriptive tile only: the predictive test did not pass | adf_p 9.18e-06 |
| M_C4_funding | model | **PASS** | BIS sign confirmed | bootstrap_p 0 |
| M_C8_ethbtc | model | **REJECT** | no rejection of a unit root (the expected null) | adf_p 0.136 |
| M_C7_weekday | model | **PASS** | cost input set | return_p_bonferroni 0.175; weekend_volume_p 3.19e-35 |
| M_E4_letf_drag | model | **REVISE** | see lines |  |
| M_O1_board_today | model | **REVISE** | see lines; a single-day snapshot, history must accumulate | iv_median_gap 26; iv_p90_gap 53.4; butterfly_violations 61 |
| M_O2_basis_today | model | **PASS** | within the dividend band | theo_gap_pts 1.16 |

## Plain-language lines per card

### S_E1_trend_us — REJECT
*Faber SMA / MOP sign trend switch on ETF sleeves beats equal-weight buy-and-hold on Sharpe and drawdown (long or cash, 1/N per sleeve)*

- Out-of-sample Sharpe 0.84 over 4,711 sessions (19 years); Lo standard error 0.23; 90 % block-bootstrap interval 0.47 to 1.20: passes (the interval must exclude zero).
- Deflated Sharpe 1.00 after 12 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.59 over the 12-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.70: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.95): difference -0.11, paired block-bootstrap 90 % interval -0.38 to +0.16, one-sided p 0.75: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 74% of calendar years: passes (needs ≥ 60%); largest year carries 13% of the P&L.
- Sharpe at 2× costs 0.75: passes (must stay positive); turnover 1.6× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 82 position changes out of sample: fails (needs ≥ 100).
- Regime split (Sharpe): high-vol 0.85 / low-vol 0.87, up 0.76 / down 1.11.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.50.
- Sources: Faber 2007/2013 SSRN 962461; Moskowitz, Ooi & Pedersen 2012 JFE 104; RN→FH §6.1, §6.5, §6.8 pp. 13–16

### S_E1_trend_krx — REJECT
*Faber SMA / MOP sign trend switch on ETF sleeves beats equal-weight buy-and-hold on Sharpe and drawdown (long or cash, 1/N per sleeve)*

- Out-of-sample Sharpe 0.52 over 1,884 sessions (9 years); Lo standard error 0.37; 90 % block-bootstrap interval -0.03 to 1.04: fails (the interval must exclude zero).
- Deflated Sharpe 0.84 after 12 trials: fails (needs ≥ 0.95).
- Probability of backtest overfitting 0.31 over the 12-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.55: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.74): difference -0.22, paired block-bootstrap 90 % interval -0.52 to +0.08, one-sided p 0.89: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 67% of calendar years: passes (needs ≥ 60%); largest year carries 36% of the P&L.
- Sharpe at 2× costs 0.52: passes (must stay positive); turnover 1.8× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 37 position changes out of sample: fails (needs ≥ 100).
- Regime split (Sharpe): high-vol 1.00 / low-vol -0.28, up 0.67 / down 0.18.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.31.
- Sources: Faber 2007/2013 SSRN 962461; Moskowitz, Ooi & Pedersen 2012 JFE 104; RN→FH §6.1, §6.5, §6.8 pp. 13–16

### S_E2_voltarget_spy — REJECT
*Capped volatility targeting w = min(1, σ*/σ̂) raises Sharpe and cuts drawdown against buy-and-hold (Moreira–Muir in Cederburg's real-time form)*

- Out-of-sample Sharpe 0.63 over 7,208 sessions (29 years); Lo standard error 0.19; 90 % block-bootstrap interval 0.34 to 0.92: passes (the interval must exclude zero).
- Deflated Sharpe 1.00 after 8 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.28 over the 8-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.82: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.56): difference +0.08, paired block-bootstrap 90 % interval -0.06 to +0.22, one-sided p 0.18: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 72% of calendar years: passes (needs ≥ 60%); largest year carries 9% of the P&L.
- Sharpe at 2× costs 0.59: passes (must stay positive); turnover 1.0× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 185 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 0.46 / low-vol 0.83, up 0.63 / down 0.65.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.38.
- Sources: Moreira & Muir 2017 JF 72; Cederburg, O'Doherty, Wang & Yan 2020 JFE 138; BKM Ch. 6 slides 6-20 to 6-22

### S_E2_voltarget_kodex200 — REJECT
*Capped volatility targeting w = min(1, σ*/σ̂) raises Sharpe and cuts drawdown against buy-and-hold (Moreira–Muir in Cederburg's real-time form)*

- Out-of-sample Sharpe 0.53 over 3,496 sessions (15 years); Lo standard error 0.27; 90 % block-bootstrap interval 0.08 to 0.97: passes (the interval must exclude zero).
- Deflated Sharpe 0.96 after 8 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.10 over the 8-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 1.21: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.66): difference -0.13, paired block-bootstrap 90 % interval -0.40 to +0.13, one-sided p 0.81: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 67% of calendar years: passes (needs ≥ 60%); largest year carries 16% of the P&L.
- Sharpe at 2× costs 0.53: passes (must stay positive); turnover 0.8× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 67 position changes out of sample: fails (needs ≥ 100).
- Regime split (Sharpe): high-vol 1.02 / low-vol 0.07, up 0.78 / down 0.27.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.32.
- Sources: Moreira & Muir 2017 JF 72; Cederburg, O'Doherty, Wang & Yan 2020 JFE 138; BKM Ch. 6 slides 6-20 to 6-22

### S_E3_riskparity_us — REJECT
*Equal-risk-contribution allocation across sleeves beats equal weight on Sharpe (unlevered; the 2022 stock-bond correlation regime is inside the sample)*

- Out-of-sample Sharpe 0.89 over 4,669 sessions (19 years); Lo standard error 0.23; 90 % block-bootstrap interval 0.51 to 1.27: passes (the interval must exclude zero).
- Deflated Sharpe 1.00 after 8 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.35 over the 8-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.83: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.86): difference +0.03, paired block-bootstrap 90 % interval -0.06 to +0.12, one-sided p 0.25: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 84% of calendar years: passes (needs ≥ 60%); largest year carries 11% of the P&L.
- Sharpe at 2× costs 0.87: passes (must stay positive); turnover 0.4× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 142 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 0.70 / low-vol 1.22, up 0.96 / down 0.78.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.54.
- Sources: Asness, Frazzini & Pedersen 2012 FAJ 68; BKM Ch. 7 slides 7-5 to 7-8; Boyd §4.4.1 p. 155

### S_E5_xsmom_sectors — REJECT
*12-1 cross-sectional momentum across the nine sector SPDRs (long top third) beats the equal-weight sector basket after 50 bp per side*

- Out-of-sample Sharpe 0.48 over 6,197 sessions (25 years); Lo standard error 0.20; 90 % block-bootstrap interval 0.16 to 0.76: passes (the interval must exclude zero).
- Deflated Sharpe 0.97 after 12 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.39 over the 12-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.72: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.63): difference -0.15, paired block-bootstrap 90 % interval -0.29 to -0.02, one-sided p 0.97: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 84% of calendar years: passes (needs ≥ 60%); largest year carries 11% of the P&L.
- Sharpe at 2× costs 0.36: passes (must stay positive); turnover 4.4× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 131 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 0.43 / low-vol 0.58, up 0.44 / down 0.57.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.29.
- Sources: Jegadeesh & Titman 1993 JF 48; Asness, Moskowitz & Pedersen 2013 JF 68; McLean & Pontiff 2016 JF 71

### S_B3_tsmom_futures — REJECT
*MOP time-series momentum (12-month sign, 40 %/σ sizing, long/short) on ten Yahoo continuous futures earns a positive net Sharpe out of sample after 2009 (caveat: Yahoo's roll treatment is undocumented)*

- Out-of-sample Sharpe 0.08 over 5,634 sessions (23 years); Lo standard error 0.21; 90 % block-bootstrap interval -0.27 to 0.43: fails (the interval must exclude zero).
- Deflated Sharpe 0.27 after 12 trials: fails (needs ≥ 0.95).
- Probability of backtest overfitting 0.10 over the 12-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.13: fails (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.58): difference -0.50, paired block-bootstrap 90 % interval -0.93 to -0.06, one-sided p 0.97: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 61% of calendar years: passes (needs ≥ 60%); largest year carries 14% of the P&L.
- Sharpe at 2× costs 0.06: passes (must stay positive); turnover 3.3× equity per year.
- Parameter plateau 67% of neighbours keep half the Sharpe, on a grid edge: fails.
- 174 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 0.53 / low-vol -0.42, up 0.20 / down -0.12.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.05.
- Sources: Moskowitz, Ooi & Pedersen 2012 JFE 104 eq. (1), (5); Primer §1.3 p. 7; MTSA §8.2.2 p. 294

### S_C3_crypto_trend_btcusd — REVISE
*Short-horizon sign votes plus price/MA ratios (long/flat with hysteresis) beat buy-and-hold BTC on Sharpe with a 25 % smaller drawdown*

- Out-of-sample Sharpe 1.20 over 3,634 sessions (11 years); Lo standard error 0.26; 90 % block-bootstrap interval 0.74 to 1.64: passes (the interval must exclude zero).
- Deflated Sharpe 1.00 after 6 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.11 is reported only: with 6 configurations the CSCV rank is too coarse (needs ≥ 8); the over-search check uses the share of splits where the in-sample winner loses out of sample, 0.00: passes (needs ≤ 0.1).
- Out-of-sample over in-sample Sharpe 0.95: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.89): difference +0.31, paired block-bootstrap 90 % interval -0.02 to +0.63, one-sided p 0.06: passes (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 82% of calendar years: passes (needs ≥ 60%); largest year carries 31% of the P&L.
- Sharpe at 2× costs 1.17: passes (must stay positive); turnover 12.1× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 174 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 1.28 / low-vol 1.14, up 1.58 / down 0.18.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.72.
- Sources: Liu & Tsyvinski 2021 RFS 34; Detzel et al. 2021 FM; MTSA §5.2 p. 161

### S_C3_crypto_trend_krwbtc — PASS
*Short-horizon sign votes plus price/MA ratios (long/flat with hysteresis) beat buy-and-hold BTC on Sharpe with a 25 % smaller drawdown*

- Out-of-sample Sharpe 1.31 over 2,530 sessions (8 years); Lo standard error 0.32; 90 % block-bootstrap interval 0.72 to 1.86: passes (the interval must exclude zero).
- Deflated Sharpe 1.00 after 6 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.41 is reported only: with 6 configurations the CSCV rank is too coarse (needs ≥ 8); the over-search check uses the share of splits where the in-sample winner loses out of sample, 0.00: passes (needs ≤ 0.1).
- Out-of-sample over in-sample Sharpe 0.91: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.79): difference +0.52, paired block-bootstrap 90 % interval +0.13 to +0.93, one-sided p 0.02: passes (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 75% of calendar years: passes (needs ≥ 60%); largest year carries 28% of the P&L.
- Sharpe at 2× costs 1.26: passes (must stay positive); turnover 14.0× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, not on a grid edge: passes.
- 141 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 1.14 / low-vol 1.49, up 1.55 / down 0.80.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.79.
- Sources: Liu & Tsyvinski 2021 RFS 34; Detzel et al. 2021 FM; MTSA §5.2 p. 161

### S_E8_pairs_kodex_tiger — REJECT
*069500.KS/102110.KS: the Engle–Granger spread mean-reverts fast enough to trade at 2σ after 3 bp per side (dollar-neutral)*

- ADF rejects a unit root in 62% of the 32 formation windows; median half-life 1 sessions (gate: ≥ 60 % and 5–40 sessions).
- Out-of-sample Sharpe 0.55 over 3,504 sessions (15 years); Lo standard error 0.27; 90 % block-bootstrap interval 0.30 to 0.81: passes (the interval must exclude zero).
- Deflated Sharpe 0.97 after 8 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.45 over the 8-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.89: passes (needs ≥ 0.5).
- Positive in 73% of calendar years: passes (needs ≥ 60%); largest year carries 23% of the P&L.
- Sharpe at 2× costs -0.32: fails (must stay positive); turnover 16.3× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 232 position changes out of sample: passes (needs ≥ 100).
- Expected live Sharpe after the McLean–Pontiff haircut: 0.33.
- Sources: Gatev, Goetzmann & Rouwenhorst 2006 RFS 19; Do & Faff 2010 FAJ 66; MTSA §5.3.2 p. 170, §6.2.3 pp. 215–219, §6.3.2 pp. 228–238

### S_S6_pairs_samsung_pref — REJECT
*005935.KS/005930.KS: the Engle–Granger spread mean-reverts fast enough to trade at 2σ after 35 bp per side (long-only tilt)*

- ADF rejects a unit root in 57% of the 40 formation windows; median half-life 7 sessions (gate: ≥ 60 % and 5–40 sessions).
- Out-of-sample Sharpe 0.83 over 4,422 sessions (19 years); Lo standard error 0.24; 90 % block-bootstrap interval 0.48 to 1.18: passes (the interval must exclude zero).
- Deflated Sharpe 1.00 after 8 trials: passes (needs ≥ 0.95).
- Probability of backtest overfitting 0.22 over the 8-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 1.19: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.85): difference -0.01, paired block-bootstrap 90 % interval -0.08 to +0.06, one-sided p 0.61: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 74% of calendar years: passes (needs ≥ 60%); largest year carries 18% of the P&L.
- Sharpe at 2× costs 0.77: passes (must stay positive); turnover 5.9× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, on a grid edge: fails.
- 102 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 1.07 / low-vol 0.57, up 0.86 / down 0.86.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.50.
- Sources: Gatev, Goetzmann & Rouwenhorst 2006 RFS 19; Do & Faff 2010 FAJ 66; MTSA §5.3.2 p. 170, §6.2.3 pp. 215–219, §6.3.2 pp. 228–238

### S_S6_pairs_hyundai_kia — REJECT
*000270.KS/005380.KS: the Engle–Granger spread mean-reverts fast enough to trade at 2σ after 35 bp per side (dollar-neutral)*

- ADF rejects a unit root in 15% of the 41 formation windows; median half-life 17 sessions (gate: ≥ 60 % and 5–40 sessions).
- Out-of-sample Sharpe 0.43 over 4,615 sessions (19 years); Lo standard error 0.23; 90 % block-bootstrap interval 0.08 to 0.75: passes (the interval must exclude zero).
- Deflated Sharpe 0.86 after 8 trials: fails (needs ≥ 0.95).
- Probability of backtest overfitting 0.20 over the 8-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 0.66: passes (needs ≥ 0.5).
- Positive in 58% of calendar years: fails (needs ≥ 60%); largest year carries 14% of the P&L.
- Sharpe at 2× costs 0.31: passes (must stay positive); turnover 3.6× equity per year.
- Parameter plateau 0% of neighbours keep half the Sharpe, on a grid edge: fails.
- 66 position changes out of sample: fails (needs ≥ 100).
- Expected live Sharpe after the McLean–Pontiff haircut: 0.26.
- Sources: Gatev, Goetzmann & Rouwenhorst 2006 RFS 19; Do & Faff 2010 FAJ 66; MTSA §5.3.2 p. 170, §6.2.3 pp. 215–219, §6.3.2 pp. 228–238

### S_E8_pairs_gld_iau — REJECT
*IAU/GLD: the Engle–Granger spread mean-reverts fast enough to trade at 2σ after 50 bp per side (dollar-neutral)*

- ADF rejects a unit root in 73% of the 41 formation windows; median half-life 1 sessions (gate: ≥ 60 % and 5–40 sessions).
- Out-of-sample Sharpe -2.28 over 4,602 sessions (19 years); Lo standard error 0.24; 90 % block-bootstrap interval -2.53 to -2.03: fails (the interval must exclude zero).
- Deflated Sharpe 0.00 after 8 trials: fails (needs ≥ 0.95).
- Probability of backtest overfitting 0.00 over the 8-config grid: passes (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe 1.02: passes (needs ≥ 0.5).
- Positive in 0% of calendar years: fails (needs ≥ 60%); largest year carries 23% of the P&L.
- Sharpe at 2× costs -2.40: fails (must stay positive); turnover 6.0× equity per year.
- Parameter plateau 0% of neighbours keep half the Sharpe, on a grid edge: fails.
- 109 position changes out of sample: passes (needs ≥ 100).
- Expected live Sharpe after the McLean–Pontiff haircut: -1.37.
- Sources: Gatev, Goetzmann & Rouwenhorst 2006 RFS 19; Do & Faff 2010 FAJ 66; MTSA §5.3.2 p. 170, §6.2.3 pp. 215–219, §6.3.2 pp. 228–238

### S_V1_vix_rolldown — REJECT
*Short the VIX ETP while VIX3M/VIX − 1 exceeds a contango threshold, hedged with a rolling SPY beta (reset only when it moves by 0.25), earns the roll-down with a smaller drawdown than the unhedged short (Simon–Campasano)*

- Out-of-sample Sharpe -0.14 over 3,197 sessions (13 years); Lo standard error 0.28; 90 % block-bootstrap interval -0.58 to 0.30: fails (the interval must exclude zero).
- Deflated Sharpe 0.28 after 8 trials: fails (needs ≥ 0.95).
- Probability of backtest overfitting 0.93 over the 8-config grid: fails (needs ≤ 0.05; reject above 0.2).
- Out-of-sample over in-sample Sharpe -1.71: fails (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.54): difference -0.69, paired block-bootstrap 90 % interval -1.23 to -0.20, one-sided p 0.99: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 38% of calendar years: fails (needs ≥ 60%); largest year carries 21% of the P&L.
- Sharpe at 2× costs -0.22: fails (must stay positive); turnover 53.2× equity per year.
- Parameter plateau 0% of neighbours keep half the Sharpe, on a grid edge: fails.
- 341 position changes out of sample: passes (needs ≥ 100).
- Regime split (Sharpe): high-vol 0.14 / low-vol -0.45, up -0.27 / down 0.17.
- Expected live Sharpe after the McLean–Pontiff haircut: -0.09.
- Sources: Simon & Campasano 2014 J. Derivatives 21(3); Eraker & Wu 2017 JFE 125; RN→FH §5.1 p. 11, §5.5 p. 13

### S_V3_fx_momentum — REJECT
*Cross-sectional FX momentum (1-1 and 3-1) on G10+KRW earns a positive net return with t > 2 after 2010*

- Out-of-sample Sharpe -0.59 over 1,367 sessions (6 years); Lo standard error 0.43; 90 % block-bootstrap interval -1.25 to 0.07: fails (the interval must exclude zero).
- Deflated Sharpe 0.06 after 2 trials: fails (needs ≥ 0.95).
- Probability of backtest overfitting 0.35 is reported only: with 2 configurations the CSCV rank is too coarse (needs ≥ 8); the over-search check uses the share of splits where the in-sample winner loses out of sample, 1.00: fails (needs ≤ 0.1).
- Out-of-sample over in-sample Sharpe 0.71: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.47): difference -1.06, paired block-bootstrap 90 % interval -1.79 to -0.27, one-sided p 0.99: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 17% of calendar years: fails (needs ≥ 60%); largest year carries 22% of the P&L.
- Sharpe at 2× costs -0.89: fails (must stay positive); turnover 12.0× equity per year.
- Parameter plateau 0% of neighbours keep half the Sharpe, on a grid edge: fails.
- 65 position changes out of sample: fails (needs ≥ 100).
- Regime split (Sharpe): high-vol -1.32 / low-vol 0.40, up -0.26 / down -1.00.
- Expected live Sharpe after the McLean–Pontiff haircut: -0.35.
- Sources: Menkhoff, Sarno, Schmeling & Schrimpf 2012 JFE 106; RN→FH §6.9 p. 17; ECON302 Ch1 slides 9–17

### S_V4_dollar_carry — REJECT
*Dollar carry (long the foreign basket when the average forward discount is positive) has a positive OOS Sharpe*

- Out-of-sample Sharpe 0.27 over 1,429 sessions (6 years); Lo standard error 0.42; 90 % block-bootstrap interval -0.42 to 0.93: fails (the interval must exclude zero).
- Deflated Sharpe 0.74 after 1 trials: fails (needs ≥ 0.95).
- Probability of backtest overfitting nan is reported only: with 1 configurations the CSCV rank is too coarse (needs ≥ 8); the over-search check uses the share of splits where the in-sample winner loses out of sample, nan: fails (needs ≤ 0.1).
- Out-of-sample over in-sample Sharpe 0.78: passes (needs ≥ 0.5).
- Against the benchmark (Sharpe 0.47): difference -0.20, paired block-bootstrap 90 % interval -1.07 to +0.67, one-sided p 0.65: fails (the claim 'beats the benchmark' needs p ≤ 0.1).
- Positive in 67% of calendar years: passes (needs ≥ 60%); largest year carries 46% of the P&L.
- Sharpe at 2× costs 0.27: passes (must stay positive); turnover 12.0× equity per year.
- Parameter plateau 100% of neighbours keep half the Sharpe, not on a grid edge: passes.
- 68 position changes out of sample: fails (needs ≥ 100).
- Regime split (Sharpe): high-vol 0.34 / low-vol 0.18, up 1.21 / down -0.90.
- Expected live Sharpe after the McLean–Pontiff haircut: 0.16.
- Sources: Lustig, Roussanov & Verdelhan 2014 JFE 111; Fama 1984 JME 14; Shreve II 9.3.16 p. 385 (PDF 401)

### M_B1_dns — REJECT
*Diebold–Li AR(1) factor forecasts beat the random walk at 12 months on ≥ 4 of 5 maturities with DM p < 0.05 at ≥ 3*

- 12-month forecasts (171 origins): DNS beats the random walk at 0 of 5 maturities (1/2/5/10/30y) and significantly (DM t < −1.96) at 0: gate needs 4 and 3.
- RMSE in bp — DNS vs RW at 12m: 1y 139/127, 2y 124/114, 5y 100/96, 10y 88/85, 30y 79/73
- 6-month: DNS beats RW at 0 of 5.
- Daily NS fit RMSE 10.4 bp with λ fixed at 0.0609/month; AR(1) γ per factor at 12m: 0.75, 0.69, 0.54
- Sources: Diebold & Li 2006 J. Econometrics 130 (NBER w10048 pp. 12–16); Berkeley Lec 6 §1.1; MTSA §2.4.3 p. 85

### S_B2_pca_fly — REVISE
*The PCA-neutral 2-5-10 butterfly mean-reverts and its 2σ rule earns more than twice its cost per trade*

- Fly = -0.52·2y + 5y + -0.59·10y (bp), PCA-neutral to level and slope; ADF p = 0.008, half-life 104 sessions (gate: p < 0.05, < 120).
- 38 trades at |z| > 2: hit rate 39%, mean -3.8 bp per trade against 2 bp of round-trip cost (gate: > 55 %, > 2× cost, ≥ 30 trades).
- Sources: Litterman & Scheinkman 1991 JFI 1; Lay §7.1 p. 397, §7.5 pp. 426–433; MTSA §5.3.2 p. 170

### D_C2_garch_btc — REVISE
*GARCH(1,1)-t one-day-ahead fans on BTC-USD are calibrated (Kupiec/Christoffersen/PIT) and beat EWMA on QLIKE*

- The fan said a 5 % day would happen 5 % of the time; it happened 5.8% of the time over 3,661 origins, 2.3 standard errors from target (Kupiec p = 0.03): fails.
- 1 % days happened 1.15% of the time (Kupiec p = 0.38); Basel traffic light over the last 250 days: green.
- Exceptions cluster? Christoffersen independence p = 0.00, conditional coverage p = 0.00: fails.
- The 90 % band covered 88.3% of outcomes (target 90 % ± 1.0%): fails.
- PIT calibration: KS p = 0.07, chi-square p = 0.00, Berkowitz p = 0.05; histogram flat; correlogram flags: k=2 lag=1: +0.04, k=3 lag=1: +0.04, k=4 lag=1: +0.04: fails.
- Solver failed to converge at 0.2% of origins: passes.
- QLIKE GARCH(1,1)-t 2.010 vs EWMA(0.94) 2.040: Diebold–Mariano t -1.21 (negative favours the model; the crypto gate needs p < 0.10).
- Fitted ν: median 3.2; 0% of refits effectively normal; the persistence sat on the stationarity guardrail (near-integrated variance) at 78% of origins.
- Sources: Primer §6.3–6.4, §7.7; ARCHITECTURE_REVIEW B5; Berkeley Lec 8 §3 (coverage, PIT); Kupiec 1995; Christoffersen 1998

### D_Q_garch_spy — REJECT
*GARCH(1,1)-t one-day-ahead fans on SPY are calibrated (Kupiec/Christoffersen/PIT) and beat EWMA on QLIKE*

- The fan said a 5 % day would happen 5 % of the time; it happened 6.6% of the time over 3,199 origins, 4.2 standard errors from target (Kupiec p = 0.00): fails.
- 1 % days happened 1.72% of the time (Kupiec p = 0.00); Basel traffic light over the last 250 days: green.
- Exceptions cluster? Christoffersen independence p = 0.41, conditional coverage p = 0.00: fails.
- The 90 % band covered 89.4% of outcomes (target 90 % ± 1.1%): passes.
- PIT calibration: KS p = 0.00, chi-square p = 0.00, Berkowitz p = 0.47; histogram flat; correlogram flags: k=1 lag=20: +0.04: fails.
- Solver failed to converge at 0.0% of origins: passes.
- QLIKE GARCH(1,1)-t 1.630 vs EWMA(0.94) 1.704: Diebold–Mariano t -4.15 (negative favours the model; the crypto gate needs p < 0.10).
- Fitted ν: median 6.0; 2% of refits effectively normal; the persistence sat on the stationarity guardrail (near-integrated variance) at 24% of origins.
- Sources: Primer §6.3–6.4, §7.7; ARCHITECTURE_REVIEW B5; Berkeley Lec 8 §3 (coverage, PIT); Kupiec 1995; Christoffersen 1998

### D_Q_garch_kodex200 — REJECT
*GARCH(1,1)-t one-day-ahead fans on 069500.KS are calibrated (Kupiec/Christoffersen/PIT) and beat EWMA on QLIKE*

- The fan said a 5 % day would happen 5 % of the time; it happened 6.6% of the time over 3,082 origins, 4.1 standard errors from target (Kupiec p = 0.00): fails.
- 1 % days happened 1.72% of the time (Kupiec p = 0.00); Basel traffic light over the last 250 days: yellow.
- Exceptions cluster? Christoffersen independence p = 0.13, conditional coverage p = 0.00: fails.
- The 90 % band covered 88.0% of outcomes (target 90 % ± 1.1%): fails.
- PIT calibration: KS p = 0.00, chi-square p = 0.00, Berkowitz p = 0.00; histogram flat; correlogram flags: k=2 lag=5: +0.05, k=4 lag=5: +0.05: fails.
- Solver failed to converge at 0.0% of origins: passes.
- QLIKE GARCH(1,1)-t 1.900 vs EWMA(0.94) 1.897: Diebold–Mariano t +0.18 (negative favours the model; the crypto gate needs p < 0.10).
- Fitted ν: median 6.0; 4% of refits effectively normal; the persistence sat on the stationarity guardrail (near-integrated variance) at 7% of origins.
- Sources: Primer §6.3–6.4, §7.7; ARCHITECTURE_REVIEW B5; Berkeley Lec 8 §3 (coverage, PIT); Kupiec 1995; Christoffersen 1998

### D_C2_gjr_btc — REVISE
*GJR-GARCH(1,1)-t one-day-ahead fans on BTC-USD are calibrated (Kupiec/Christoffersen/PIT) and beat EWMA on QLIKE*

- The fan said a 5 % day would happen 5 % of the time; it happened 5.7% of the time over 3,661 origins, 2.0 standard errors from target (Kupiec p = 0.05): fails.
- 1 % days happened 1.12% of the time (Kupiec p = 0.47); Basel traffic light over the last 250 days: green.
- Exceptions cluster? Christoffersen independence p = 0.01, conditional coverage p = 0.01: fails.
- The 90 % band covered 88.3% of outcomes (target 90 % ± 1.0%): fails.
- PIT calibration: KS p = 0.04, chi-square p = 0.00, Berkowitz p = 0.11; histogram flat; correlogram flags: k=2 lag=1: +0.04, k=3 lag=1: +0.04, k=4 lag=1: +0.04: fails.
- Solver failed to converge at 0.0% of origins: passes.
- QLIKE GJR-GARCH(1,1)-t 1.977 vs EWMA(0.94) 2.040: Diebold–Mariano t -1.90 (negative favours the model; the crypto gate needs p < 0.10).
- Fitted ν: median 3.1; 0% of refits effectively normal; the persistence sat on the stationarity guardrail (near-integrated variance) at 75% of origins; median leverage γ 0.000.
- Sources: Primer §6.3–6.4, §7.7; ARCHITECTURE_REVIEW B5; Berkeley Lec 8 §3 (coverage, PIT); Kupiec 1995; Christoffersen 1998; Glosten, Jagannathan & Runkle 1993 JF 48; ARCHITECTURE_REVIEW B8

### D_Q_gjr_spy — REVISE
*GJR-GARCH(1,1)-t one-day-ahead fans on SPY are calibrated (Kupiec/Christoffersen/PIT) and beat EWMA on QLIKE*

- The fan said a 5 % day would happen 5 % of the time; it happened 6.6% of the time over 3,199 origins, 4.2 standard errors from target (Kupiec p = 0.00): fails.
- 1 % days happened 1.63% of the time (Kupiec p = 0.00); Basel traffic light over the last 250 days: green.
- Exceptions cluster? Christoffersen independence p = 0.76, conditional coverage p = 0.00: fails.
- The 90 % band covered 89.5% of outcomes (target 90 % ± 1.1%): passes.
- PIT calibration: KS p = 0.01, chi-square p = 0.00, Berkowitz p = 0.40; histogram flat; correlogram flags: k=1 lag=20: +0.04, k=2 lag=1: -0.06, k=4 lag=1: -0.04: fails.
- Solver failed to converge at 0.0% of origins: passes.
- QLIKE GJR-GARCH(1,1)-t 1.597 vs EWMA(0.94) 1.704: Diebold–Mariano t -4.04 (negative favours the model; the crypto gate needs p < 0.10).
- Fitted ν: median 6.3; 2% of refits effectively normal; the persistence sat on the stationarity guardrail (near-integrated variance) at 25% of origins; median leverage γ 0.282.
- Sources: Primer §6.3–6.4, §7.7; ARCHITECTURE_REVIEW B5; Berkeley Lec 8 §3 (coverage, PIT); Kupiec 1995; Christoffersen 1998; Glosten, Jagannathan & Runkle 1993 JF 48; ARCHITECTURE_REVIEW B8

### D_Q_gjr_kodex200 — REJECT
*GJR-GARCH(1,1)-t one-day-ahead fans on 069500.KS are calibrated (Kupiec/Christoffersen/PIT) and beat EWMA on QLIKE*

- The fan said a 5 % day would happen 5 % of the time; it happened 6.8% of the time over 3,082 origins, 4.5 standard errors from target (Kupiec p = 0.00): fails.
- 1 % days happened 1.69% of the time (Kupiec p = 0.00); Basel traffic light over the last 250 days: yellow.
- Exceptions cluster? Christoffersen independence p = 0.19, conditional coverage p = 0.00: fails.
- The 90 % band covered 87.5% of outcomes (target 90 % ± 1.1%): fails.
- PIT calibration: KS p = 0.00, chi-square p = 0.00, Berkowitz p = 0.00; histogram flat; correlogram flags: k=2 lag=5: +0.04, k=4 lag=5: +0.04: fails.
- Solver failed to converge at 0.0% of origins: passes.
- QLIKE GJR-GARCH(1,1)-t 1.879 vs EWMA(0.94) 1.897: Diebold–Mariano t -1.06 (negative favours the model; the crypto gate needs p < 0.10).
- Fitted ν: median 6.3; 4% of refits effectively normal; the persistence sat on the stationarity guardrail (near-integrated variance) at 1% of origins; median leverage γ 0.134.
- Sources: Primer §6.3–6.4, §7.7; ARCHITECTURE_REVIEW B5; Berkeley Lec 8 §3 (coverage, PIT); Kupiec 1995; Christoffersen 1998; Glosten, Jagannathan & Runkle 1993 JF 48; ARCHITECTURE_REVIEW B8

### M_C1_kimchi — REVISE
*The kimchi premium is stationary with a short half-life and a high premium predicts weaker BTC returns over the next week*

- Premium now -2.58 % (z -1.68); mean 1.94 %, max 58.8 % over 3288 days since 2017-09-25.
- ADF p = 0.000, half-life 15 days (gate: p < 0.05, < 30 days).
- Next-7-day BTC return on the premium z: slope +0.0003, Newey–West t +6.15 (gate: t < −2 for a sentiment signal; otherwise a descriptive tile only).
- USD/KRW forward-filled by date (FRED noon fixing vs UTC-midnight closes: a few hours of FX drift); a positive premium means Korea pays more than the world price.
- Sources: Makarov & Schoar 2020 JFE 135; Choi, Lehar & Stauffer (SSRN 3189051); MTSA §5.3.2, §5.3.4–5.3.5

### M_C4_funding — PASS
*High perpetual funding (crowded longs) predicts weaker 30-day BTC returns*

- Funding now +5.6 %/yr (7-day mean), 39% percentile since 2019-09-10: normal.
- Forward 30-day BTC return after top-decile funding -2.94% vs bottom decile +7.72%; bootstrap P(top ≥ bottom) = 0.000 (gate: < 0.05, the BIS sign).
- Sources: Schmeling, Schrimpf & Todorov 2023 BIS WP 1087; He, Manela, Ross & von Wachter 2022 (arXiv 2212.06888)

### M_C8_ethbtc — REJECT
*ln(ETH/BTC) is mean-reverting (null expected)*

- ADF p = 0.136, half-life 337 days over 3327 days: no rejection of a unit root (the expected null).
- Sources: MTSA Ch. 5–6; Shreve II Ex. 4.4.10 p. 150 (PDF 166)

### M_C7_weekday — PASS
*Weekday returns carry no persistent effect; weekend liquidity is lower (a cost input)*

- No weekday mean return differs after Bonferroni (p = 0.18): the expected null.
- Weekend volume is 61% of weekday volume (p = 3.2e-35); weekend slippage set at 2× in the crypto backtests.
- Sources: Baur, Cahill, Godfrey & Liu 2019 FRL 31; ECON302 Ch1 slides 2–7

### M_E4_letf_drag — REVISE
*The Avellaneda–Zhang drag with the app's GARCH-t variance term structure forecasts KODEX 레버리지's quarterly shortfall versus 2× KOSPI200*

- 52 quarters: MAE of the GARCH-based drag forecast 136 bp vs naive-zero 203 bp and last-quarter 91 bp (gate: ≥ 20 % below both).
- Realised on forecast: slope 0.25, R² 0.03 (gate: slope in [0.7, 1.3], R² ≥ 0.5).
- Mean realised quarterly drag of KODEX 레버리지 vs 2× KOSPI200: -203 bp.
- Sources: Avellaneda & Zhang 2010 SIAM JFM 1 eq. (10); Cheng & Madhavan 2009 JOIM; Shreve II §4.4.3 p. 147; Primer §5.4 p. 15

### M_O1_board_today — REVISE
*The app's Black-76 inversion, parity checks, SVI and MFIV reconcile with the live KOSPI200 board (candidate O1/O5/O6, today's snapshot)*

- Expiry 2026-10-08 (T = 11 days), CD 91d 3.21%, parity-implied forward 1187.53 (K₀ 1187.5); 80 strikes on the board, 80 calls / 80 puts.
- Black-76 inversion of 69 two-sided-quoted OTM mids within ±15 % of F vs KIS IV: median gap 25.95 vol pts, 90th pct 53.42 (gate: ≤ 0.5 and ≤ 1.5).
- Put–call parity within half the summed spread on 19% of near strikes (gate ≥ 95 %); butterfly violations calls 31 / puts 30, vertical 18 / 19.
- SVI: RMSE 26.82 vol pts (26.82 within |k| ≤ 0.15), ρ -0.15, min g(k) +0.282 (butterfly arbitrage in the fit).
- ATM implied vol 51.1%; model-free implied vol 56.6% from 80 strikes; RND integrates to 0.995 with mean +0.26% vs F.
- Sources: Shreve II §4.5.4–4.5.6 pp. 158–162 (PDF 174–178); Gatheral & Jacquier 2014 QF 14; Cboe VIX methodology pp. 7–9; RN→FH p. 19

### M_O2_basis_today — PASS
*The app's cost-of-carry fair value reconciles with KIS's theoretical price once dividend points are aligned*

- F 202612 1127.75 vs KOSPI200 1126.12: basis +1.63 pts, fair value 1133.94 at CD 91d 3.21% over 79 days (no dividend points), mispricing -55 bp.
- KIS theoretical 1132.78 (gap +1.16 pts): the dividend-point convention is the difference; implied simple funding rate 0.67%.
- Sources: Shreve II Thm 5.6.2 p. 241, eq. 5.6.11 p. 247; Cornell & French 1983 JFM 3; Ko 2022 KJFS 51
