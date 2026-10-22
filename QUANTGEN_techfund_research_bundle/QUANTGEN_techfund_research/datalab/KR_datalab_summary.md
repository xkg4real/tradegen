# KRX technical signals: data-lab results (Korea)

QUANTGEN technical and fundamental signals project, Korea data lab. Data: marcap daily snapshots of every KRX-listed stock, 1995-05-02 to 2026-09-29 (survivorship-free). Portfolios run from 1996-03 (first formation with 252 days of history) to 2026-09-29. All numbers below are read from the CSV files in `/home/claude/datalab/kr/results/` by `kr_09_summary.py`; scripts are in `/home/claude/datalab/scripts/kr_*.py` (`python3 kr_run_all.py` reruns everything in about 10 minutes, peak memory about 2 GB).

Conventions: signal at the close of t, portfolio formed at the close of t, returns from t+1. Price returns (r = ChangesRatio/100, dividends excluded). Costs: 35 bp per side on every unit traded (stress 70 bp); index timing 3 bp (stress 6 bp). LS = best minus worst quintile in the hypothesised direction, both legs pay costs, $1 long / $1 short. LO = best quintile. "Excess" = LO minus the universe portfolio with the same weighting (EW vs EW universe, VW vs VW universe), net of the LO leg's costs. Sharpe uses raw returns (no risk-free rate). Newey-West t uses 6 lags (monthly) or 4 (weekly).

## Headline findings

1. **Gross long-short spreads are real; most of them do not survive 35 bp per side, and the ones that do come from the short leg.** The strongest monthly spreads in the ALL universe (EW) are low turnover (+23.1%/yr, Sharpe 0.90, t 5.47), low MAX (+18.4%, Sharpe 1.12) and low volatility (+18.7%, Sharpe 0.76). The quintile means show where the spread comes from: the worst quintile loses money in absolute terms (high turnover -11.7%/yr, high volatility -8.2%, high MAX -6.2%, gross) while the best quintile is close to the EW universe (+7.3%).
2. **Long-only top quintiles: only small caps beat the universe net of 35 bp with t > 2 (SIZE, EW), and that edge has faded.** SIZE (smallest quintile of the screened universe) +5.8%/yr over the EW universe (t 2.94); by sub-period +11.0% / +5.9% / +0.9%, and the SIZE long-short spread returned -26.9% in 2025 and -26.5% in 2026 to date; market impact in these stocks is not modelled. Every other EW top quintile is within noise of the universe or below it (TURN low +1.7%, HIGH52 +1.6%, VOL low +1.1%, MOM 12-1 -1.3%). Against the VW universe (the investable benchmark) only MOM_12_1 (+1.6%, t 0.6), SIZE (+3.1%, t 0.6) of the VW top quintiles are positive net of costs (largest t 0.6).
3. **What is implementable long-only is the exclusion screen, not the stock-picking quintile.** Holding the universe minus the worst quintile of TURN 1M (highest turnover) earns +3.6%/yr over the EW universe net of 35 bp (t 5.63, 87% of years positive, +2.5% at 70 bp); excluding the most volatile quintile (VOL 3M) +3.0% (t 4.67). Value-weighted the effect shrinks to +0.8% and +1.1% over the VW universe (t 2.86 and 2.83). These are small, steady tilts, not alpha engines.
4. **Weekly reversal is the largest gross effect and the clearest cost casualty.** REV 1W long-short earns +19.9%/yr gross (EW, Sharpe 0.99; VW +38.7%, Sharpe 1.43) on 159x turnover per year (both legs), so the break-even cost is 12.5 bp per side (EW) and 22.2 bp (VW), far below 35 bp: net Sharpe -1.78 (EW). The volume split does not rescue it: gross Sharpe 1.01 after low-volume weeks, 1.05 mid, 0.75 high (EW); value-weighted the high-volume tercile is strongest (1.21 vs 0.92). The prior design's volume-filtered short-term reversal (Korea weight 3) is not supported at 35 bp.
5. **Momentum, trend and oscillators are weak in Korea.** MOM 12-1 LS gross +9.3% (Sharpe 0.45; 2016-2026 Sharpe 0.12); MOM 6-1 0.15; PMA200 -0.05. RSI14 and Bollinger %B work only in the contrarian direction and only gross (Sharpe 0.36 and 0.38); at 35 bp both are negative (-0.15, -0.32). The momentum direction of RSI/%B loses money even gross.
6. **Index timing on the KOSPI: no rule beats buy-and-hold on mean return; trend rules cut drawdowns and, thanks to 1997-2000, compound slightly faster.** Close > SMA200 (net 3 bp): CAGR 8.1% and 10-month SMA 9.1% vs 7.2% buy-and-hold, Sharpe 0.53 / 0.57 vs 0.39, max drawdown -41.5% / -43.7% vs -67.1%; but their arithmetic mean daily return is below buy-and-hold (-1.1% and -0.1% a year), and in 2006-2015 the 10-month SMA compounded at -0.4% vs 3.7%. Hansen SPA over 303 variants (losses relative to buy-and-hold): consistent p = 0.880; the best rule in the full sample (MACD(12,26,1)) beats buy-and-hold by +1.2%/yr (t 0.34). The rule selected on 1996-2012 (RSI2>50 (momentum)) trailed buy-and-hold by 6.1% a year in 2013-2026.

## Key numbers: monthly and weekly signals, ALL universe (microcap screen), 1996-2026

Annualised. LS = long-short; LO excess = best quintile minus the universe with the same weighting; Excl = universe minus the worst quintile, minus the universe. Turnover = per year, both legs for LS.

### EW (equal-weighted)

| Signal | LS gross | Sharpe | NW t | LS Sharpe net35 / net70 | LO net35 (abs) | LO excess net35 (t) | Excl-worst excess net35 (t) | LS turnover/yr | LS % years > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MOM 12-1 (buy winners) | +9.3% | 0.45 | 2.7 | 0.20 / -0.04 | +6.0% | -1.3% (-0.6) | +0.9% (2.1) | 14.7 | 68% |
| MOM 6-1 (buy winners) | +3.4% | 0.15 | 1.1 | -0.15 / -0.45 | +3.3% | -4.0% (-2.2) | -0.3% (-0.7) | 19.6 | 58% |
| REV 1M (buy losers) | +11.2% | 0.45 | 2.7 | -0.08 / -0.62 | +2.4% | -4.9% (-2.2) | +0.3% (0.5) | 37.9 | 68% |
| 52-week high (buy near high) | +9.1% | 0.32 | 2.2 | 0.12 / -0.08 | +8.9% | +1.6% (0.8) | +0.1% (0.2) | 16.2 | 68% |
| VOL 3M (buy low vol) | +18.7% | 0.76 | 4.6 | 0.56 / 0.37 | +8.4% | +1.1% (0.5) | +3.0% (4.7) | 13.6 | 74% |
| MAX 1M (buy low MAX) | +18.4% | 1.12 | 6.0 | 0.48 / -0.16 | +7.1% | -0.2% (-0.1) | +1.8% (3.7) | 30.1 | 84% |
| TURN 1M (buy low turnover) | +23.1% | 0.90 | 5.5 | 0.68 / 0.46 | +9.0% | +1.7% (0.9) | +3.6% (5.6) | 16.3 | 77% |
| TURN 1M (buy high turnover) | -23.1% | -0.90 | -5.5 | -1.12 / -1.34 | -15.1% | -22.4% (-8.7) | -2.2% (-4.5) | 16.3 | 10% |
| SIZE (small minus big) | +7.7% | 0.39 | 1.9 | 0.25 / 0.09 | +13.1% | +5.8% (2.9) | -0.9% (-1.4) | 8.4 | 55% |
| Price/SMA200 (buy high) | -1.5% | -0.05 | -0.3 | -0.26 / -0.48 | +1.7% | -5.6% (-2.4) | -0.9% (-1.4) | 17.1 | 48% |
| RSI14 contrarian (buy low) | +8.7% | 0.36 | 2.0 | -0.15 / -0.65 | +4.8% | -2.5% (-1.1) | -0.7% (-1.3) | 34.9 | 61% |
| RSI14 momentum (buy high) | -8.7% | -0.36 | -2.0 | -0.86 / -1.36 | -3.7% | -11.1% (-4.8) | -2.8% (-4.8) | 34.9 | 29% |
| Bollinger %B contrarian | +7.4% | 0.38 | 2.0 | -0.32 / -1.01 | +1.7% | -5.6% (-2.8) | -0.6% (-1.3) | 38.8 | 58% |
| Bollinger %B momentum | -7.4% | -0.38 | -2.0 | -1.07 / -1.76 | -5.5% | -12.8% (-6.4) | -2.5% (-4.9) | 38.8 | 29% |
| REV 1W weekly (buy losers) | +19.9% | 0.99 | 5.7 | -1.78 / -4.54 | -14.2% | -21.4% (-12.1) | n/a (weekly) | 159.5 | 74% |
| REV 1W, low volume spike | +21.8% | 1.01 | 6.0 | -1.87 / -4.72 | -15.3% | -22.5% (-9.2) | n/a (weekly) | 178.4 | 81% |
| REV 1W, mid volume spike | +21.7% | 1.05 | 6.5 | -2.15 / -5.34 | -12.9% | -20.0% (-10.7) | n/a (weekly) | 188.4 | 81% |
| REV 1W, high volume spike | +18.2% | 0.75 | 4.2 | -1.78 / -4.30 | -23.0% | -30.1% (-12.8) | n/a (weekly) | 175.6 | 74% |
| *Universe EW (benchmark)* | | | | | +6.6% (Sharpe 0.22, max DD -76.1%) | | | 1.9 (LO) | |

### VW (value-weighted, Marcap at t)

| Signal | LS gross | Sharpe | NW t | LS Sharpe net35 / net70 | LO net35 (abs) | LO excess net35 (t) | Excl-worst excess net35 (t) | LS turnover/yr | LS % years > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MOM 12-1 (buy winners) | +13.5% | 0.43 | 2.4 | 0.25 / 0.07 | +11.3% | +1.6% (0.6) | -0.1% (-0.3) | 16.2 | 65% |
| MOM 6-1 (buy winners) | +5.1% | 0.18 | 1.1 | -0.10 / -0.38 | +6.2% | -3.5% (-1.4) | -0.7% (-1.5) | 22.5 | 55% |
| REV 1M (buy losers) | +1.0% | 0.03 | 0.2 | -0.45 / -0.93 | -0.7% | -10.5% (-3.0) | -0.8% (-0.7) | 40.4 | 55% |
| 52-week high (buy near high) | +11.5% | 0.36 | 2.0 | 0.19 / 0.03 | +9.1% | -0.6% (-0.4) | +0.2% (0.7) | 15.0 | 68% |
| VOL 3M (buy low vol) | +20.1% | 0.63 | 3.6 | 0.48 / 0.33 | +8.0% | -1.8% (-0.6) | +1.1% (2.8) | 13.8 | 68% |
| MAX 1M (buy low MAX) | +8.4% | 0.34 | 1.9 | -0.13 / -0.60 | +2.8% | -7.0% (-2.8) | +0.2% (0.5) | 33.1 | 61% |
| TURN 1M (buy low turnover) | +15.5% | 0.47 | 2.8 | 0.27 / 0.07 | +3.0% | -6.8% (-2.7) | +0.8% (2.9) | 18.7 | 68% |
| TURN 1M (buy high turnover) | -15.5% | -0.47 | -2.8 | -0.66 / -0.86 | -13.0% | -22.7% (-4.8) | -0.5% (-0.5) | 18.7 | 26% |
| SIZE (small minus big) | +4.5% | 0.18 | 0.9 | 0.09 / 0.00 | +12.8% | +3.1% (0.6) | -5.3% (-1.5) | 6.3 | 58% |
| Price/SMA200 (buy high) | +6.7% | 0.20 | 1.2 | 0.00 / -0.20 | +9.1% | -0.7% (-0.2) | -0.4% (-0.8) | 19.0 | 52% |
| RSI14 contrarian (buy low) | +3.6% | 0.13 | 0.7 | -0.34 / -0.80 | +4.4% | -5.3% (-1.6) | -1.3% (-1.0) | 37.1 | 55% |
| RSI14 momentum (buy high) | -3.6% | -0.13 | -0.7 | -0.60 / -1.07 | +1.4% | -8.3% (-3.2) | -2.1% (-3.0) | 37.1 | 39% |
| Bollinger %B contrarian | +6.8% | 0.29 | 1.7 | -0.31 / -0.90 | +5.0% | -4.7% (-1.7) | -1.2% (-1.2) | 40.1 | 55% |
| Bollinger %B momentum | -6.8% | -0.29 | -1.7 | -0.88 / -1.47 | -1.3% | -11.0% (-4.4) | -2.8% (-4.7) | 40.1 | 35% |
| REV 1W weekly (buy losers) | +38.7% | 1.43 | 8.4 | -0.82 / -3.07 | -3.7% | -13.1% (-4.4) | n/a (weekly) | 174.5 | 84% |
| REV 1W, low volume spike | +26.7% | 0.92 | 5.5 | -1.31 / -3.52 | -16.7% | -26.1% (-6.0) | n/a (weekly) | 185.9 | 81% |
| REV 1W, mid volume spike | +31.9% | 1.09 | 6.7 | -1.21 / -3.49 | -5.5% | -15.0% (-4.4) | n/a (weekly) | 192.1 | 84% |
| REV 1W, high volume spike | +41.9% | 1.21 | 6.5 | -0.67 / -2.55 | -6.4% | -15.8% (-4.3) | n/a (weekly) | 186.1 | 77% |
| *Universe VW (benchmark)* | | | | | +9.6% (Sharpe 0.34, max DD -70.0%) | | | 0.3 (LO) | |

LARGE universe (top 200 by market cap, KOSPI200-like), VW: gross LS Sharpe and LO excess over the VW top-200 portfolio, net 35 bp:

| Signal | LS gross Sharpe | LS net35 Sharpe | LO excess net35 | Excl-worst excess net35 |
|---|---:|---:|---:|---:|
| MOM 12-1 (buy winners) | 0.23 | 0.07 | +1.0% | +0.2% |
| MOM 6-1 (buy winners) | 0.12 | -0.13 | -2.9% | -1.1% |
| REV 1M (buy losers) | 0.03 | -0.41 | -10.2% | -1.7% |
| 52-week high (buy near high) | 0.19 | -0.02 | -2.7% | +0.2% |
| VOL 3M (buy low vol) | 0.25 | 0.10 | -1.8% | +0.2% |
| MAX 1M (buy low MAX) | 0.08 | -0.38 | -7.4% | -0.5% |
| TURN 1M (buy low turnover) | 0.06 | -0.12 | -6.5% | +0.2% |
| TURN 1M (buy high turnover) | -0.06 | -0.24 | -8.8% | -1.2% |
| SIZE (small minus big) | -0.23 | -0.36 | -6.9% | -3.0% |
| Price/SMA200 (buy high) | 0.06 | -0.13 | -0.4% | -0.7% |
| RSI14 contrarian (buy low) | 0.10 | -0.34 | -5.8% | -1.8% |
| RSI14 momentum (buy high) | -0.10 | -0.54 | -8.8% | -1.7% |
| Bollinger %B contrarian | 0.42 | -0.11 | -3.5% | -1.0% |
| Bollinger %B momentum | -0.42 | -0.94 | -14.6% | -2.8% |
| REV 1W weekly (buy losers) | 1.53 | -0.60 | -10.9% | n/a |
| REV 1W, low volume spike | 1.15 | -1.01 | -20.5% | n/a |
| REV 1W, mid volume spike | 1.26 | -0.81 | -12.0% | n/a |
| REV 1W, high volume spike | 1.06 | -0.76 | -17.7% | n/a |

In large caps the monthly anomalies largely disappear (low-vol LS gross Sharpe 0.25, low turnover 0.06, SIZE -0.23); weekly reversal stays large gross (1.53) but is still negative at 35 bp (-0.60).

## Stability: Sharpe by sub-period (ALL universe)

| Signal | LS gross EW 1996-2005 / 2006-2015 / 2016-2026 | LS gross VW (same) | Excl-worst excess net35 EW (ann.) 1996-2005 / 2006-2015 / 2016-2026 |
|---|---|---|---|
| MOM 12-1 (buy winners) | 0.51 / 0.77 / 0.12 | 0.43 / 0.36 / 0.50 | +1.5% / +1.8% / -0.4% |
| MOM 6-1 (buy winners) | 0.31 / 0.11 / -0.13 | 0.01 / 0.09 / 0.44 | +0.2% / -0.1% / -1.0% |
| REV 1M (buy losers) | 0.65 / 0.35 / 0.33 | 0.46 / -0.35 / -0.23 | +2.3% / -0.7% / -0.6% |
| 52-week high (buy near high) | 0.13 / 0.64 / 0.56 | 0.35 / 0.21 / 0.50 | -0.2% / +0.5% / +0.0% |
| VOL 3M (buy low vol) | 0.60 / 1.15 / 0.81 | 0.98 / 0.51 / 0.34 | +3.1% / +3.2% / +2.7% |
| MAX 1M (buy low MAX) | 1.44 / 1.29 / 0.67 | 0.66 / 0.24 / 0.12 | +3.0% / +1.6% / +0.8% |
| TURN 1M (buy low turnover) | 0.88 / 1.30 / 0.82 | 0.53 / 0.68 / 0.29 | +5.1% / +3.6% / +2.3% |
| TURN 1M (buy high turnover) | -0.88 / -1.30 / -0.82 | -0.53 / -0.68 / -0.29 | -3.2% / -2.0% / -1.4% |
| SIZE (small minus big) | 0.56 / 0.71 / -0.05 | 0.35 / 0.68 / -0.32 | -0.4% / -0.6% / -1.6% |
| Price/SMA200 (buy high) | 0.02 / 0.01 / -0.30 | 0.31 / 0.01 / 0.24 | -0.8% / -0.5% / -1.2% |
| RSI14 contrarian (buy low) | 0.56 / 0.13 / 0.26 | 0.44 / -0.13 / -0.09 | +0.9% / -1.7% / -1.4% |
| RSI14 momentum (buy high) | -0.56 / -0.13 / -0.26 | -0.44 / 0.13 / 0.09 | -4.3% / -2.1% / -2.2% |
| Bollinger %B contrarian | 0.66 / 0.21 / 0.06 | 0.46 / 0.08 / 0.23 | +1.4% / -1.6% / -1.6% |
| Bollinger %B momentum | -0.66 / -0.21 / -0.06 | -0.46 / -0.08 / -0.23 | -3.6% / -2.1% / -1.8% |
| REV 1W weekly (buy losers) | 1.29 / 1.14 / 0.53 | 1.64 / 2.22 / 0.53 | n/a (weekly) |
| REV 1W, low volume spike | 0.86 / 1.73 / 0.81 | 0.94 / 1.67 / 0.38 | n/a (weekly) |
| REV 1W, mid volume spike | 1.15 / 1.60 / 0.65 | 0.96 / 2.15 / 0.43 | n/a (weekly) |
| REV 1W, high volume spike | 1.04 / 0.62 / 0.51 | 1.71 / 1.59 / 0.21 | n/a (weekly) |

## Where and when it failed (dated episodes)

Cumulative return in each window, ALL universe, EW. LS gross; LO excess = top quintile minus EW universe, net 35 bp. Windows run from the close of the start date to the close of the end date (see kr_common.EVENT_WINDOWS).

| Window | EW universe | VW universe | MOM_12_1 LS | REV_1M LS | HIGH52 LS | VOL_3M LS | MAX_1M LS | TURN_1M_LOW LS | SIZE LS | PMA200 LS | REV_1W LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1997-11..1998-06 | -55.6% | -33.1% | +28.9% | +66.9% | -8.3% | +58.4% | +47.7% | +29.5% | -26.9% | -29.7% | +0.5% |
| 2000-03..2000-12 | -46.7% | -44.1% | -37.1% | -1.5% | +11.7% | +106.7% | +51.2% | +200.7% | +79.1% | -7.2% | +36.9% |
| 2008-06..2009-03 | -32.6% | -34.2% | -14.1% | +24.8% | -26.0% | +11.3% | +25.7% | +3.0% | +5.8% | -32.2% | +63.4% |
| 2020-02-17..2020-03-19 | -41.0% | -35.3% | -1.6% | -7.6% | +7.3% | +12.7% | +7.1% | +12.4% | -9.3% | +3.3% | +4.5% |
| 2020-03-20..2020-06-30 | +68.0% | +47.8% | +1.2% | +16.0% | -19.2% | -15.2% | -6.8% | -13.2% | +9.2% | -11.9% | +27.7% |
| 2022 | -24.9% | -26.3% | +1.7% | +26.9% | +4.6% | +42.8% | +28.6% | +36.4% | +5.6% | -20.1% | +10.5% |
| 2024-07-11..2024-08-05 | -15.6% | -16.0% | -1.9% | -5.7% | +7.1% | +10.8% | +6.3% | +12.7% | +2.0% | +1.0% | -9.5% |
| 2026-01-02..2026-06-22 | +0.8% | +104.9% | +39.8% | -13.3% | +34.0% | -12.9% | -17.9% | -11.2% | -31.0% | +43.6% | -8.7% |
| 2026-06-22..2026-07-30 | -18.2% | -38.5% | -24.4% | -9.0% | +9.4% | +36.2% | +30.5% | +33.5% | +9.0% | -13.1% | -8.0% |
| 2026-07-31..2026-09-29 | +20.5% | +23.6% | +19.8% | +12.2% | -20.6% | -25.9% | -24.1% | -18.8% | -2.2% | -9.5% | +14.3% |

| Window | MOM_12_1 LO xs | REV_1M LO xs | HIGH52 LO xs | VOL_3M LO xs | MAX_1M LO xs | TURN_1M_LOW LO xs | SIZE LO xs | PMA200 LO xs | REV_1W LO xs | TURN excl-worst xs | VOL excl-worst xs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1997-11..1998-06 | +5.8% | +21.7% | -5.9% | +16.1% | +16.4% | +2.0% | -4.4% | -15.5% | -16.3% | +5.2% | +7.7% |
| 2000-03..2000-12 | -32.1% | -21.6% | -4.9% | +55.1% | +27.3% | +59.2% | +56.5% | -16.1% | -25.2% | +16.8% | +6.8% |
| 2008-06..2009-03 | -13.1% | -3.1% | -15.1% | -2.0% | +0.7% | -6.9% | +2.1% | -20.4% | -5.6% | +1.6% | +2.4% |
| 2020-02-17..2020-03-19 | -3.3% | -4.8% | +4.4% | +10.7% | +7.1% | +10.2% | -4.1% | -0.6% | +2.4% | +0.5% | +0.5% |
| 2020-03-20..2020-06-30 | +4.3% | +5.0% | -12.5% | -15.3% | -10.5% | -14.4% | +1.1% | -6.0% | +2.3% | -0.1% | -0.4% |
| 2022 | -5.8% | -1.5% | +1.4% | +11.3% | +3.8% | +10.9% | +5.2% | -16.5% | -25.5% | +3.8% | +5.6% |
| 2024-07-11..2024-08-05 | -3.9% | -6.7% | +3.6% | +6.3% | +3.7% | +6.7% | +1.9% | -2.6% | -7.8% | +1.4% | +1.1% |
| 2026-01-02..2026-06-22 | +18.8% | -8.0% | +8.5% | -9.1% | -10.5% | -8.0% | -11.1% | +20.1% | -13.6% | -1.6% | -1.6% |
| 2026-06-22..2026-07-30 | -19.5% | -10.5% | +4.4% | +16.6% | +14.5% | +14.9% | +3.6% | -13.1% | -13.1% | +4.4% | +4.8% |
| 2026-07-31..2026-09-29 | +15.2% | +9.2% | -10.0% | -12.5% | -11.9% | -10.6% | -1.8% | -1.1% | +6.2% | -2.9% | -4.4% |

Failure episodes worth naming (all numbers from the tables above and results/kr_event_windows.csv):

- **2026 melt-up (2026-01-02..06-22): the market was two stocks.** Samsung Electronics and SK hynix were 31% of the VW universe at the 2025-12-30 formation and returned +195% and +349% to 2026-06-22. VW universe +104.9% vs EW universe +0.8%; LARGE VW +119.1%. Every defensive signal lagged: low-vol LS -12.9%, low-MAX -17.9%, SIZE -31.0%; trend/momentum won (MOM 12-1 +39.8%, PMA200 +43.6%).
- **2026 crash (06-22..07-30) and rebound (07-31..09-29): momentum crash pattern.** MOM 12-1 LS -24.4% in the crash (low-vol +36.2%, low-MAX +30.5%), then the defensive signals gave it back in the rebound (low-vol -25.9%, low-MAX -24.1%). The rebuilt KOSPI gained +17.9% on 2026-07-31 alone (Samsung +26.8%, SK hynix +30.0% that day in the raw data).
- **2000 dot-com bust (2000-03..12): MOM 12-1 LS -37.1%**, the worst momentum episode; low turnover +200.7% and low-vol +106.7% were the big winners (the high-turnover, high-vol KOSDAQ bubble names collapsed).
- **2008-06..2009-03 GFC: trend lost** (PMA200 -32.2%, HIGH52 -26.0%, MOM 12-1 -14.1%); weekly reversal earned +63.4% gross but -5.6% long-only after costs.
- **2020-03-20..06-30 COVID rebound: low-vol and low-turnover lagged** (-15.2%, -13.2%), HIGH52 -19.2%.
- **Weekly reversal stopped working after 2020**: REV 1W LS gross calendar-year returns 2021 -7.2%, 2023 -2.2%, 2024 -2.5%, 2025 -20.2%, 2026 -1.9%.
- **Long-only weekly reversal is a disaster net of costs:** max drawdown -99.9% (EW, 35 bp).
- **SIZE (small minus big) flipped:** EW LS gross 2015-2021 mostly positive, then -26.9% in 2025 and -26.5% in 2026 to date.

Calendar years 2015-2026, LS gross, ALL EW (total return per year):

| Signal | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MOM_12_1 | +11% | -3% | -0% | -11% | -10% | +7% | -19% | +2% | -0% | +21% | +4% | +27% |
| REV_1M | -20% | +19% | +6% | +9% | +11% | +3% | -7% | +27% | -1% | +4% | -11% | -11% |
| HIGH52 | +0% | +5% | +16% | -3% | -5% | -11% | +27% | +5% | +4% | +24% | +16% | +16% |
| VOL_3M | -17% | +13% | +13% | +6% | +14% | -2% | +31% | +43% | +12% | +33% | +13% | -12% |
| MAX_1M | -21% | +20% | +13% | +8% | +12% | -2% | +16% | +29% | +5% | +25% | +7% | -19% |
| TURN_1M_LOW | -12% | +11% | +22% | +5% | +11% | -8% | +30% | +36% | +10% | +33% | +15% | -4% |
| SIZE | +37% | +29% | -20% | +16% | +16% | +10% | +12% | +6% | -5% | -10% | -27% | -26% |
| PMA200 | +13% | -11% | +7% | -15% | -15% | -8% | -1% | -20% | -14% | -1% | +2% | +13% |
| RSI14_CON | -19% | +14% | -4% | +6% | +8% | -1% | -9% | +24% | +6% | +2% | -17% | +8% |
| REV_1W | +5% | +11% | +5% | +43% | +11% | +33% | -7% | +10% | -2% | -3% | -20% | -2% |

Calendar years, implementable version (universe minus worst quintile, excess over EW universe, net 35 bp):

| Signal | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TURN_1M_LOW | -1.9% | +1.3% | +4.2% | +1.1% | +2.3% | +0.7% | +2.8% | +3.8% | +2.4% | +3.7% | +2.3% | -0.2% |
| VOL_3M | -2.6% | +1.5% | +2.8% | +0.5% | +3.1% | +1.5% | +4.5% | +5.6% | +3.8% | +4.1% | +3.3% | -1.5% |
| MAX_1M | -5.2% | +1.5% | +1.1% | +0.1% | +1.0% | +0.1% | +1.2% | +2.8% | +0.7% | +2.3% | +1.4% | -3.9% |
| MOM_12_1 | +1.3% | -0.5% | -0.5% | -1.1% | -2.0% | -1.1% | -1.5% | +0.4% | -1.5% | +2.4% | -1.2% | +2.7% |

## Correlations of long-short returns (calendar months, ALL EW, gross)

| | MOM_12_1 | MOM_6_1 | REV_1M | HIGH52 | VOL_3M | MAX_1M | TURN_1M_LOW | SIZE | PMA200 | RSI14_CON | BBPCTB_CON | REV_1W |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MOM_12_1 | 1.00 | 0.74 | -0.15 | 0.50 | -0.14 | -0.04 | -0.20 | -0.20 | 0.65 | -0.24 | -0.16 | -0.13 |
| MOM_6_1 | 0.74 | 1.00 | -0.42 | 0.73 | 0.06 | -0.02 | 0.06 | -0.20 | 0.89 | -0.54 | -0.43 | -0.27 |
| REV_1M | -0.15 | -0.42 | 1.00 | -0.72 | -0.31 | 0.14 | -0.29 | 0.26 | -0.72 | 0.92 | 0.87 | 0.32 |
| HIGH52 | 0.50 | 0.73 | -0.72 | 1.00 | 0.54 | 0.25 | 0.49 | -0.38 | 0.88 | -0.78 | -0.69 | -0.34 |
| VOL_3M | -0.14 | 0.06 | -0.31 | 0.54 | 1.00 | 0.69 | 0.90 | -0.31 | 0.15 | -0.28 | -0.26 | -0.06 |
| MAX_1M | -0.04 | -0.02 | 0.14 | 0.25 | 0.69 | 1.00 | 0.67 | -0.15 | -0.07 | 0.13 | 0.14 | 0.06 |
| TURN_1M_LOW | -0.20 | 0.06 | -0.29 | 0.49 | 0.90 | 0.67 | 1.00 | -0.28 | 0.14 | -0.30 | -0.27 | -0.08 |
| SIZE | -0.20 | -0.20 | 0.26 | -0.38 | -0.31 | -0.15 | -0.28 | 1.00 | -0.28 | 0.27 | 0.25 | 0.16 |
| PMA200 | 0.65 | 0.89 | -0.72 | 0.88 | 0.15 | -0.07 | 0.14 | -0.28 | 1.00 | -0.80 | -0.69 | -0.39 |
| RSI14_CON | -0.24 | -0.54 | 0.92 | -0.78 | -0.28 | 0.13 | -0.30 | 0.27 | -0.80 | 1.00 | 0.95 | 0.37 |
| BBPCTB_CON | -0.16 | -0.43 | 0.87 | -0.69 | -0.26 | 0.14 | -0.27 | 0.25 | -0.69 | 0.95 | 1.00 | 0.29 |
| REV_1W | -0.13 | -0.27 | 0.32 | -0.34 | -0.06 | 0.06 | -0.08 | 0.16 | -0.39 | 0.37 | 0.29 | 1.00 |

Three clusters: (i) low-risk/low-attention: VOL 3M, TURN low, MAX 1M (TURN-VOL 0.90); (ii) trend: MOM 6-1, PMA200, HIGH52 (PMA200-HIGH52 0.88); (iii) short-horizon contrarian: REV 1M, RSI14, %B (RSI-%B 0.95, REV-RSI 0.92). RSI14 and %B are repackaged 1-month reversal, not separate signals. Clusters (i) and (iii) are close to uncorrelated with each other and negatively correlated with (ii).

## KOSPI index timing (rebuilt value-weighted KOSPI)

Sanity check against official KOSPI closes (ratio of gross index changes, rebuilt / official):

| From | To | Official change | Rebuilt change | Ratio |
|---|---|---:|---:|---:|
| 2007-10-31 (2,064.85) | 2020-03-19 (1,457.64) | -29.4% | -29.4% | 0.9999 |
| 2007-10-31 (2,064.85) | 2021-07-06 (3,305.21) | +60.1% | +59.9% | 0.9987 |
| 2007-10-31 (2,064.85) | 2026-06-22 (9,114.55) | +341.4% | +341.7% | 1.0006 |
| 2007-10-31 (2,064.85) | 2026-07-30 (5,593.56) | +170.9% | +171.2% | 1.0010 |
| 2020-03-19 (1,457.64) | 2021-07-06 (3,305.21) | +126.8% | +126.5% | 0.9989 |
| 2020-03-19 (1,457.64) | 2026-06-22 (9,114.55) | +525.3% | +525.8% | 1.0007 |
| 2020-03-19 (1,457.64) | 2026-07-30 (5,593.56) | +283.7% | +284.2% | 1.0011 |
| 2021-07-06 (3,305.21) | 2026-06-22 (9,114.55) | +175.8% | +176.3% | 1.0019 |
| 2021-07-06 (3,305.21) | 2026-07-30 (5,593.56) | +69.2% | +69.6% | 1.0023 |
| 2026-06-22 (9,114.55) | 2026-07-30 (5,593.56) | -38.6% | -38.6% | 1.0004 |

All ratios are within 0.23% of 1 (index built from all KOSPI common-share lines including listed REITs/funds; an operating-companies-only version is within 0.93%).

1996-06-03..2026-09-29, net 3 bp per side (6 bp stress in brackets), cash 0%:

| Rule | CAGR | Vol | Sharpe | Max DD | Time in market | Entries/yr | Excess vs B&H /yr (t) | CAGR at 6 bp | Sharpe 96-05 / 06-15 / 16-26 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Buy & hold | 7.2% | 26.5% | 0.39 | -67.1% | 100% | 0.0 | +0.0% (n/a) | 7.2% | 0.32 / 0.28 / 0.62 |
| SMA200 (close > SMA200) | 8.1% | 17.6% | 0.53 | -41.5% | 58% | 3.9 | -1.1% (-0.3) | 7.8% | 0.81 / 0.20 / 0.50 |
| 10M_SMA (monthly) | 9.1% | 18.2% | 0.57 | -43.7% | 57% | 1.0 | -0.1% (-0.0) | 9.0% | 0.80 / 0.04 / 0.72 |
| SMA50 > SMA200 | 6.9% | 18.6% | 0.45 | -56.0% | 57% | 0.8 | -2.1% (-0.6) | 6.8% | 0.61 / 0.13 / 0.53 |
| MACD(12,26,9) > signal | 3.7% | 17.5% | 0.30 | -65.2% | 52% | 9.7 | -5.3% (-1.5) | 3.1% | 0.04 / 0.39 / 0.65 |
| Connors RSI(2)<10 & >SMA200, exit >SMA5 | 2.8% | 9.4% | 0.34 | -26.5% | 10% | 6.1 | -7.3% (-1.6) | 2.4% | 0.21 / 0.11 / 0.57 |
| Bollinger(20,2) MR: buy < lower, exit > middle | 2.4% | 16.0% | 0.23 | -40.8% | 23% | 4.6 | -6.8% (-1.7) | 2.1% | 0.21 / 0.21 / 0.27 |
| Donchian 20-high entry / 10-low exit | 6.0% | 14.6% | 0.47 | -40.2% | 41% | 5.7 | -3.6% (-0.9) | 5.6% | 0.55 / 0.29 / 0.55 |
| TSMOM 12M sign (monthly) | 7.5% | 19.1% | 0.48 | -38.8% | 58% | 0.8 | -1.4% (-0.4) | 7.5% | 0.56 / 0.23 / 0.58 |

Event windows (cumulative, net 3 bp):

| Rule | 1997-11..1998-06 | 2000-03..2000-12 | 2008-06..2009-03 | 2020-02-17..2020-03-19 | 2020-03-20..2020-06-30 | 2022 | 2024-07-11..2024-08-05 | 2026-01-02..2026-06-22 | 2026-06-22..2026-07-30 | 2026-07-31..2026-09-29 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Buy & hold | -35.1% | -39.0% | -34.8% | -35.0% | +44.6% | -24.9% | -15.5% | +116.2% | -38.6% | +22.8% |
| SMA200 (close > SMA200) | +0.0% | +0.0% | -3.2% | -8.5% | -1.5% | +0.0% | -15.5% | +116.2% | -37.9% | +4.1% |
| 10M_SMA (monthly) | +0.0% | -0.0% | -9.6% | -11.4% | +3.9% | +0.0% | -15.5% | +116.2% | -38.6% | +22.8% |
| SMA50 > SMA200 | +0.0% | +1.0% | +0.0% | -35.0% | +1.6% | +0.0% | -15.5% | +116.2% | -38.6% | +22.8% |
| MACD(12,26,9) > signal | -48.7% | -36.0% | -15.4% | -2.1% | +14.9% | +2.7% | -1.7% | +28.7% | -10.0% | -1.6% |
| Connors RSI(2)<10 & >SMA200, exit >SMA5 | +0.0% | +0.0% | +0.0% | -6.3% | +0.2% | +0.0% | -2.1% | +32.4% | -3.8% | +29.4% |
| Bollinger(20,2) MR: buy < lower, exit > middle | +35.2% | +5.8% | -19.6% | -29.9% | +18.3% | -11.9% | -9.9% | +16.2% | -22.8% | +17.6% |
| Donchian 20-high entry / 10-low exit | +11.2% | -13.1% | -8.8% | +0.0% | +10.5% | +4.0% | -2.3% | +39.3% | -16.1% | -1.8% |
| TSMOM 12M sign (monthly) | +0.0% | -12.9% | -9.6% | +0.0% | +0.0% | -10.6% | -15.5% | +116.2% | -38.6% | +22.8% |

Trend rules (SMA200, 10-month SMA, 12M TSMOM) were out of the market for most of 1997-98, 2000, 2008 and 2022 and cut the maximum drawdown from -67.1% to about -41.5%, but they were fully invested into the 2026-06-22..07-30 crash (SMA200 -37.9% vs -38.6%): the index stayed above its 200-day average until 2026-07-29, and SMA200 then missed the +17.9% rebound day of 2026-07-31. Mean-reversion rules (Connors RSI(2), Bollinger) spend 10-24% of the time in the market and have CAGRs of 2.8% and 2.4%.

### Data-snooping test (Hansen SPA)

- Family: 303 variants (price vs SMA 5-250 and EMA 10-250, SMA bands, SMA/EMA crossover pairs, MACD variants, Connors RSI(2-14) thresholds 5-30, RSI>50, Bollinger mean-reversion and breakout (10-50 days, 1.5-2.5 sd), Donchian entry/exit pairs, TSMOM 1-12 months and 20-240 days, 3-12 month SMA). arch.bootstrap.SPA, stationary bootstrap, block 15, 2,000 reps, seed 20261002, studentized; losses = -(rule daily net return) vs benchmark loss -(buy-and-hold return), i.e. the test asks whether any rule beats buy-and-hold on mean daily return net of 3 bp.
- Best rule in-sample (highest NW t of the daily excess return): **MACD(12,26,1)**, Sharpe 0.67 vs buy-and-hold 0.39, CAGR 10.7% vs 7.2%, excess +1.2%/yr, t 0.34. Highest Sharpe in the family: BB(20,2.0) breakout (0.79).
- **SPA p-values: consistent 0.880, lower 0.737, upper 0.890**: no rule beats buy-and-hold on return. On 1996-2012 alone: consistent 0.522. 44 of 303 rules have a positive mean excess, 213 have a higher Sharpe than buy-and-hold (they hold cash about 40-70% of the time).
- **Time split**: best variant on 1996-2012 by excess t = RSI2>50 (momentum) (in-sample Sharpe 0.82 vs 0.33); 2013-2026: CAGR 4.3% vs buy-and-hold 9.4%, Sharpe 0.38 vs 0.53, excess -6.1%/yr (t -1.65), 77 position changes per year. Best variant on 1996-2012 by Sharpe = BB(20,2.0) breakout (in-sample 0.89): 2013-2026 Sharpe 0.64 vs 0.53, CAGR 6.2% vs 9.4%, max DD -19.7% vs -44.0%, time in market 27%.
- Supplementary (not the pre-specified test): against an exposure-matched benchmark (buy-and-hold scaled by each rule's average exposure), SPA consistent p = 0.051 (best BB(20,2.0) breakout, +7.1%/yr, t 3.41, exposure 29%). Selected on 1996-2012 by Sharpe, its 2013-2026 excess over the exposure-matched benchmark was +3.6%/yr (t 1.32); selected by excess t (RSI2>50 (momentum)): -1.1%/yr (t -0.41). Timing reduces risk; evidence that it adds return per unit of exposure is borderline and did not hold out of sample for the excess-t winner.

## Cross-checks against figures in the context brief

- 1-month reversal, ALL deciles, EW, 1999-2021: losers minus winners +1.41%/month gross (t 2.52), +0.20%/month net 35 bp.
- 1-month reversal, BROAD deciles (no microcap screen, no price floor), EW, 1999-2021: losers minus winners +1.09%/month gross (t 2.17), -0.07%/month net 35 bp.
- 1-month reversal, ALL quintiles, EW, 1999-2021: losers minus winners +0.89%/month gross (t 2.20), -0.21%/month net 35 bp.
  The brief quotes WML -2.95%/month (t -3.77) for 1999-2021, i.e. reversal of +2.95%/month. Our spread is about half of that, probably because of our screens (microcap cut, 1,000 KRW price floor, >= 200 valid days) and a different specification in the source paper (not opened by the data lab); in our data it is not reliably profitable after 35 bp per side (best: ALL deciles, +0.2%/month net, t below 1).
- MOM 12-1 Q5-Q1 inside the low turnover tercile (ALL, EW, 1996-2026): +0.71%/month gross, t 2.28.
- MOM 12-1 Q5-Q1 inside the mid turnover tercile (ALL, EW, 1996-2026): +0.89%/month gross, t 3.25.
- MOM 12-1 Q5-Q1 inside the high turnover tercile (ALL, EW, 1996-2026): +1.44%/month gross, t 3.41.
  The brief's claim that Korean 12-1 momentum is negative in high-turnover stocks is not reproduced: in our sample momentum is positive in every turnover tercile and largest in the high-turnover one.

## Validation

| Test | What | Passed |
|---|---|---:|
| V0 | Share classes (preferred = non-zero last code character) | 3/3 |
| V1 | 10 random stock-days: r vs Close/prev Close | 10/10 |
| V1b | Population: r vs Close/prev Close on all kept days | 1/1 |
| V2 | Look-ahead: universe and all signals recomputed on data truncated at 2015-06-30 | 12/12 |
| V3 | Look-ahead: returns start at t+1; hand-recomputed periods | 4/4 |
| V4 | Quintile breakpoints from the eligible universe only | 6/6 |
| V5 | Index rules use prices <= t only | 2/2 |
| V6 | Reproducibility (SPA seed) and SHA-256 of result files | 30/30 |

- r vs Close/prevClose: 12,186 of 13,949,140 = 0.0874% of kept daily returns differ by more than 0.5% (KRX base-price adjustments: splits, rights issues, stock dividends; r is the adjusted figure). The 10 random spot checks agree within 0.005 pp (ChangesRatio is rounded to 0.01%).
- Preferred shares: 1127 of 1144 (98.5%) of non-zero-ending code/name pairs carry a preferred or new-share marker (우, 우B, 1신, 전환); the rest are 1990s new-share lines (e.g. "코닉스1"). No common-share code has a preferred-looking name.
- Look-ahead: the panel was rebuilt from data truncated at 2015-06-30; universe membership and all 11 monthly signals at all 231 month-ends up to then are identical to the full-data values (assertion test in kr_06_validation.py). The engine returns for random periods were recomputed by hand from t+1..t_next.
- Breakpoints: quintiles are formed within the eligible universe only (no non-member is ever assigned; universe-only breakpoints reproduce the assignment exactly; ALL and all-listed breakpoints differ, so the test has power).

## Data handling and caveats

- **Returns are price returns** (dividends excluded). Korean dividend yields were roughly 1-2% a year for most of the sample, higher for low-vol, low-turnover and large value stocks; long-only absolute returns are understated by about that much, and the defensive signals (low vol, low turnover) are probably understated relative to the universe.
- **Return cleaning** (13,953,730 stock-days): first day of each listing segment set to missing (4,396: new listings, relistings, KONEX transfers and 1990s KOSPI/KOSDAQ transfers with a base-price reset). 4,108 returns exceed the daily limit (+-15% before 2015-06-15, +-30% after). Of these, 3,902 fall in the last 30 trading days before a delisting (liquidation trading, which has no price limit) and 13 are the first trade after a halt of >= 5 sessions; both are kept because they are real losses (median -30.4%). 12 coincide with a corporate action and agree with the market-cap change (kept); 75 coincide with a corporate action but do not (missing); 106 others (mostly 1996-99 records with repeated +16.7% prints on zero-volume days) are set to missing; 13 placeholder 1-KRW prices are missing. Event list: results/kr_return_flags_events.csv.
- **Sensitivity to that choice** ("strict": every beyond-limit return without a consistent corporate action set to missing, the literal rule): the low-vol LS gross mean moves from +18.7% to +17.9%, low-turnover from +23.1% to +22.5%, MOM 12-1 from +9.3% to +8.9%, EW universe from +7.3% to +7.5%: dropping liquidation losses flatters the short legs' victims. Full strict tables: results/*_strict.csv.
- **Delistings**: a stock that disappears is held at its last price as cash. Across monthly ALL quintiles, about 62 universe members disappear during a holding month over 30 years (the same events seen through each of the 11 monthly signals; 11% of them distressed liquidations, the rest mergers, voluntary delistings or restructurings). They concentrate in the extreme quintiles: e.g. TURN 1M Q1 35 vs Q5 7 (mostly mergers of quiet stocks), HIGH52 Q1 has 5 distressed exits with a mean -52% over their last 21 days (counts per signal and quintile in results/kr_disappearances.csv). The book-value share that disappears is 0.78% a year for the median quintile book (max 1.77%, TURN_1M Q1); the share exiting at a stale (no-trade) last price is at most 1.42% a year, which bounds the delisting bias at 1.4% a year even if all of it were worth zero (most of it is 1997-2000 mergers and bank/conglomerate restructurings, not liquidations). Direction of the bias: delisting returns are unknown; for distressed exits the last price is usually above the eventual recovery, so long legs holding losers (REV 1M Q1, MOM Q1, high-vol) are biased slightly upward and the LS spreads that short them are biased slightly downward; the sensitivity run below (liquidation losses dropped) moves the main spreads by under 1 pp a year.
- **Halted positions**: a held stock that is halted at a rebalance cannot be sold; it is carried (and its resumption-day move is earned) until the first rebalance at which it trades. Stocks halted at the formation close are not bought (1.5 per month removed from the specified screen); a beyond-limit move without corporate action in the last 30 days also excludes a stock (3 cases in 366 months).
- **Universe**: microcap cut = 20th percentile of Marcap within the eligible set; the ALL universe averages 1178 stocks (from 453 in 1998-09 to 1834 in 2026-08); KOSDAQ is 44%-62% of it (yearly averages) from 2001 and 0%-6% in 1996-99: KOSDAQ data start in 1996-07 and 76% of KOSDAQ stock-days in 1996-98 have zero volume, so most KOSDAQ stocks fail the 200-valid-day rule until 1999. SPACs, REITs (incl. 코크렙, 리얼티), listed ship/infrastructure/resource funds (동북아12호, 바다로, 맥쿼리인프라, 한국ANKOR유전), listed mutual funds (박현주1호, ...MF) and KDRs are excluded by name; the literal 리츠/인프라 substring rule was not used because it would also drop 메리츠 group companies, 두산인프라코어 and other operating companies.
- **Shorting**: long-short results are research benchmarks. Short selling of Korean stocks was banned from 2023-11-06 to 2025-03-30 (with earlier temporary bans in parts of 2008-09, 2011 and 2020-21) and is impractical for individuals (stock borrow is limited and costly, and the 35 bp cost does not include borrow fees). Only the long-only results are implementable.
- **Costs**: 35 bp per side is charged on every unit of turnover (it includes the sell-side transaction tax); market impact is not modelled, which flatters small-cap EW portfolios. The ALL EW universe itself turns over 1.9x a year (rebalancing to equal weights), costing about 0.66% a year.
- **Index**: the rebuilt KOSPI is a price index from all KOSPI common-share lines with lagged market-cap weights; the official KOSPI also uses market-cap weights on common shares; the two track within 0.23% between the 2007-2026 check dates. Before 2007 it is not checked against official closes (none were supplied).

## What looks implementable for QUANTGEN at 35 bp per side, long-only

1. **Exclusion screens on the KRX stock universe (BUILD-candidate, as a filter, not a signal).** Drop the top quintile of 1-month turnover (Amount/Marcap) and/or of 3-month volatility from whatever long book QUANTGEN holds. EW: +3.6% and +3.0% a year over the EW universe net of 35 bp (t 5.63 / 4.67), positive in every sub-period, still positive at 70 bp, turnover about 3.3x a year. VW the gain is +0.8%-+1.1%. It should pass QUANTGEN's 2x-cost gate; against a cap-weighted benchmark the edge is about 1% a year, so the benchmark gate (one-sided p <= 0.10) is the binding test. The expected edge is a 1-4% a year tilt, mostly from avoiding lottery-like stocks. It lagged in the 2026 melt-up (-1.6%) and after the 2026 crash (-2.9%; low-vol screen -4.4%).
2. **Index trend filter as a risk overlay, not an alpha source (CONTEXT).** SMA200 or 10-month SMA on the KOSPI via a KRX ETF (3 bp): CAGR 9.1% (10M SMA) vs 7.2% buy-and-hold over 1996-2026, all of the gain from 1996-2005 (15.2% vs 5.3%; 2006-2015 -0.4% vs 3.7%), Sharpe 0.57 vs 0.39, max drawdown -43.7% vs -67.1%. The SPA test says no rule beats buy-and-hold on return, consistent with QUANTGEN's own E1 REJECT. Use only as the macro-research style exposure multiplier (0.5-1.0), never above 1.0.
3. **Not implementable at 35 bp (DROP for KRX single stocks)**: weekly reversal in any volume tercile, 1-month reversal, RSI14 / Bollinger %B in either direction, price-vs-SMA200 stock selection, MOM 6-1. Monthly MOM 12-1 and 52-week-high long-only quintiles are within noise of the universe after costs (BACKLOG at most; MOM 12-1 VW top quintile +1.6%/yr over the VW universe, t 0.62).
4. **Weekly reversal belongs on a cheaper venue**: break-even cost 12-25 bp per side; the 35 bp KRX stock cost (tax included) kills it. Not a Korea stock card.

Prior Korea weights (context brief section 2: XS-mom 1, ST-rev 3, ...): the data support **lowering ST-reversal from 3 to 0-1 for cash-equity implementation** (strong gross, negative net), keeping XS-momentum low (1), and adding low-turnover / low-volatility as exclusion filters (the brief has low-vol 2 for Korea, which fits as a filter, not as a long-only quintile).

## Files

- Scripts: `kr_common.py`, `kr_01_build_panel.py` (panel, return cleaning), `kr_02_signals.py` (universes, signals), `kr_03_portfolios.py` (quintile books, turnover, delistings), `kr_04_stats.py` (statistics, events, correlations), `kr_05_index_timing.py` (KOSPI rebuild, timing rules, SPA), `kr_06_validation.py`, `kr_07_charts_summary.py` (chart JSON), `kr_08_crosschecks.py`, `kr_09_summary.py`, `kr_run_all.py`.
- Results: `kr_signal_stats_long.csv` (signal, universe, weighting, leg, cost_level, period, metric, value, freq; legs LS, LO, LO_xs_UEW/UVW, LO_excl_worst(_xs_UEW/UVW), Q1..Q5), `kr_event_windows.csv`, `kr_ls_correlations.csv`, `kr_index_timing.csv`, `kr_index_timing_events.csv`, `kr_index_spa.csv`, `kr_index_spa_family.csv`, `kr_index_sanity.csv`, `kr_validation.csv`, `kr_disappearances.csv`, `kr_delisting_exposure_*.csv`, `kr_return_flags_*.csv`, `kr_universe_counts.csv`, `kr_crosschecks.csv`, `kr_key_numbers.csv`, and `*_strict.csv` sensitivity copies.
- Charts (JSON): `kr_chart1_cumlog_monthly.json`, `kr_chart2_sharpe_subperiods.json`, `kr_chart3_kospi_timing.json`, `kr_chart4_quintiles_2025_2026.json`.
