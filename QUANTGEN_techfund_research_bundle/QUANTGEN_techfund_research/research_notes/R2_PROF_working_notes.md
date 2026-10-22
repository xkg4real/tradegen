# R2 Professors' panel: chair's working notes (extracts)

Prepared by the chair of the Professors' panel (fictional composite persona) on 2 October 2026 for round 2.
Part A is the chair's own digest (written after reading the extracts). Part B holds verbatim extracts of each paper's position summary, recommendations, failure section, data-check requests and claims ledger (line ranges given), so that disputes can be traced back without re-reading the full papers. The executives' papers (E1-E7) were deliberately not opened.

# Part A. Chair's digest (written after reading the extracts in Part B)

## A1. One-paragraph position of each paper
- **P1 (asset pricing).** CAPM is wrong on average returns but right on risk. Make attribution mandatory (beta, Jensen's alpha, FF5+UMD, local KR factors plus a SEMI factor). Build at most two factor cards: a Korea value + quarterly-ROE composite and a US quality composite, with expected net information ratio 0.1-0.3. BAB and low beta go to BACKLOG (value-weighted, beta-neutral only). Drop size. Drop momentum in Korea and Japan, partly on the brief's "negative Korean momentum" anchor. Gate power is low: 18-31 out-of-sample years are needed.
- **P2 (technical analysis).** After data snooping and costs, classic technical rules fail after the late 1980s. Four slow constructs survive as features: diversified trend, the 52-week high, MA distance, and short-term reversal (gross only). P2 ran KRX desk checks: top-500 weekly reversal is -0.59%/week net; the volume-filtered version -0.88%/week; July-2026 WML -27.2%. Proposes a family gate (F0-F7) and a DO-NOT-BUILD register.
- **P3 (accounting).** Accounting signals are real but small after costs. In the US only slow composites survive (value + profitability + investment + issuance). US earnings drift has been dead since 2006 (2 -> 0); Korean drift has no Korean evidence (3 -> 1). CAPE is context only. P3's first Korean card is net issuance (local test: long-only net information ratio 0.84, decaying). Point-in-time data is the binding constraint in Korea (OpenDART from 2015).
- **P4 (econometrics).** Anomalies replicate statistically but shrink at every honest step (about 4 bp/month net on average). Turnover decides survival. Audits the gate and finds five holes: no family-wise test, single-test hurdles, flat costs, no implementability rules, and a miscalibrated haircut plus a weak calendar-year rule. Proposes protocol P4-TF-1: tiered hurdles, CPCV, a sealed 2019-2026 holdout, liquidity-bucket costs, long-only primary statistic, program-wide FDR.
- **P5 (machine learning).** Shallow ML doubles gross out-of-sample performance over weak baselines, but net it is about 0 at 1-month horizons after 2004. Build an equal-weight composite and a ridge challenger now; run GBRT/NN as shadows; drop daily deep learning, order-book and LLM-news strategies. Exclude macro x characteristic interactions. The gate cannot detect plausible uplifts.
- **P6 (Korea/Asia).** Outside the US, low risk and lottery effects travel better than momentum. In Korea the lottery family is strongest but lives in the short leg, so P6 proposes a lottery-exclusion screen at 3. Korean momentum is positive but fragile (the KJFS -6.13% result is not replicated). Reversal is gross-only; the volume filter has the "wrong sign"; flow 3 -> 1; earnings drift 3 -> 2; quality 1 -> 2. Korean market structure (bans, limits, tax, concentration) must be encoded.
- **P7 (crypto/FX/canon).** Crypto trend has the best modern evidence (keep C3; split at the January 2024 ETF launch). G10 FX technical rules are dead. The practitioner canon reduces to three primitives; TradingView backtests are optimistic by construction. Crypto short-horizon evidence is momentum, not reversal (ST-rev 2 -> 0-1). CTREND is a strong BACKLOG item.

## A2. Disputes identified for round 2 (resolved in R2_PROF_chair_resolution.md, section 6)
D1 sign of Korean momentum (P1/P3 + brief vs P6/P2); D2 Korean reversal weight and the volume filter (P2 vs P6; brief -2.95); D3 low vol / BAB as alpha vs protection (P1 vs P4 vs P6; US lab flat SML); D4 quality robustness (prior vs P1/P3/P4; P5 on Korean GP); D5 value after Value-up / TSE (P1 3-if vs P3/P6 2); D6 Korean earnings drift (P6 2 vs P3 1); D7 52-week high (P6 2 vs P2 1); D8 surviving technical forms, trend as protection (P2, P7, P4); D9 ML now or later, macro interactions (P5; P4/P7 reviews); D10 gate amendments (P4, P2, P1); D11 TradingView/CMT canon (P7, P4, P2); D12 crypto momentum vs reversal (P7, P2); D13 decay haircuts (brief/Ilmanen, P3, P4, P5); D14 Korean net issuance (P3; P1 review).

## A3. Numbers flagged for verification (priority = drives BUILD/DROP or conflicts)
Context-brief anchors (-2.95%/month reversal; negative high-turnover momentum; Ilmanen per-factor haircuts); P3 local issuance IR 0.84; P2 and P6 weekly volume-filter results (0.44 vs 0.03%/week); P6 52-week high +0.34%/month vs KR lab +1.6%/yr (t 0.8); P6 12-7 net Sharpe 0.54; P6 lottery exclusion +0.23%/month; P6 Corwin-Schultz spreads; P4 2026 crash winners -43%; Chen-Velikov 4 vs 8 bp; P2 Jeon-Byun drawdowns; P1 MSCI min-vol and momentum gaps; Kang 2016 and Han-Lee-Kang 2020 Korean factor numbers; all gate arithmetic (P1-C29, P4-C05/C06/C22/C23/C27/C28, P5-C28/C29).
Results: see /home/claude/datalab/r2/verification/prof_verification_log.csv (108 rows).


# Part B. Verbatim extracts



---

## P1_asset_pricing_CAPM_factors.md

### [P1] Position summary (lines 21-42)

###### 2. Position summary

1. **CAPM is wrong about average returns but right about risk.** For about 90 years the security market line (SML) has been too flat. In US data for 1928-2003, the lowest-beta portfolio earned 11.1%/yr against a CAPM prediction of 8.3%, and the highest-beta portfolio earned 13.7% against 16.8%. Beta earns a positive premium mainly on macro-announcement days and overnight. Beta is still the right tool for measuring, hedging and attributing market exposure, and it remains the default practitioner model for cost of capital.
2. **Multifactor models describe the cross-section better, but none is "true".** This covers FF3, Carhart, FF5, Hou-Xue-Zhang q, Stambaugh-Yuan, Daniel-Hirshleifer-Sun and the Barillas-Shanken six-factor model. FF5 is rejected by formal tests, and model rankings shift with sample and factor definitions. For QUANTGEN their main use is risk measurement and attribution, not prediction.
3. **The factor zoo is mostly noise at the single-signal level, but a few themes are real.**
   - 64-85% of 447 US anomalies fail with NYSE breakpoints and value weights, and the recommended hurdle for a new factor is t > 3.
   - Value, momentum, profitability/quality, investment and low risk replicate across 93 countries, with out-of-sample alphas about one-third smaller.
   - In the US, returns fall about 58% after publication, and the average anomaly nets only about 4 bps/month after 2005.
4. **2010-2026 was hostile to factor investors.**
   - Value fell 55% over 13.5 years to mid-2020, rebounded in 2022 and again in 2025-26 (mostly outside the US and in cheap technology).
   - Size was absent: the Russell 2000 lagged the Russell 1000 by 7.5 pp/yr over 2021-25.
   - Low-volatility lagged world equities by 7.0 pp/yr over 2020-25.
   - US momentum indexes earned roughly nothing over the market after 2012.
   - Profitability (RMW) lost 16.4% in the 12 months to August 2026 during a junk rally.
5. **QUANTGEN should make a factor-attribution block mandatory on every card.** The block reports CAPM beta, Jensen's alpha against a beta-matched benchmark, FF5+UMD alpha for US cards, and alpha against local Korean factors for KRX cards. Factor loadings are not signals.
6. **At most two characteristic-based factor cards are worth building now:**
   - a Korea value + quarterly-profitability composite (long-only, liquid universe, capped, optionally beta-hedged with KOSPI200 futures);
   - a US quality composite.

   Expect a net information ratio (IR) of about 0.1-0.3. The gate will often return REVISE or INSUFFICIENT DATA for these cards. That is the honest outcome and not a reason to loosen it.
7. **Low-beta and betting-against-beta (BAB) go to BACKLOG.** Only a value-weighted, liquid, beta-neutral version, judged on alpha, should ever be built. Size is dropped as a signal. Standalone stock momentum is dropped in Korea and Japan and moved to BACKLOG in the US, because at QUANTGEN's 50 bp per side its turnover makes net returns negative.


### [P1] Recommended design (KQ6 inferences) (lines 456-525)

######## Inferences: the recommended design

**A. Risk and attribution module (BUILD, applies to all 34+ cards)**
1. **For every card**, regress daily out-of-sample returns on the card's benchmark (KOSPI200 for KRX, SPY for US) with Newey-West standard errors (lag = holding period). Report beta, Jensen's alpha and its t-statistic, and the beta-matched benchmark return β×B + (1−β)×rf.
2. **US equity cards:** add FF5 + UMD daily loadings and alpha, from the French library (updated monthly, available through August 2026). Optionally add q5 if the data become accessible.
3. **KRX equity cards:** build local factors from marcap (market cap, prices) plus OpenDART (book equity, operating profit, total assets), with strict point-in-time lags:
   - MKT (value-weighted all-KRX), SMB, HML (B/M), RMW (operating profitability, quarterly version as in Kang 2016), CMA (asset growth), UMD (12-1);
   - plus a SEMI factor (Samsung Electronics + SK hynix value-weighted minus market) to absorb the 2025-26 concentration.

   Cross-check against JKP's Korea factors, noting the CC BY-NC licence: fine for non-commercial research, not for redistribution inside a paid product.
4. **Labelling rule:** if CAPM alpha is significant but FF5+UMD (or local-factor) alpha is not (t < 2), label the card "factor tilt", not "new alpha".
5. **Beta-neutral variant for long-only KRX selection cards:** also report a simulated "long portfolio + KOSPI200 futures hedge" version. Hedge with trailing 252-day beta (no look-ahead) at 5 bp per side (10 bp at 2x).
6. **Gate proposal for the next pre-registered version, not retroactive:** for cards with beta ≠ 1, run step 5 as a Jensen's-alpha t-test (one-sided p ≤ 0.10) alongside the existing comparison. Comparing Sharpe ratios ignores cash mixing; comparing raw returns penalizes low-beta designs in bull markets.

**B. Signals: what gets a card, per market**

Planning estimates below are P1 inferences, not facts. The arithmetic is:
- expected net long-short Sharpe = published gross Sharpe × (1 − haircut) − annual cost / long-short volatility;
- long-short cost per year = 4 × one-sided turnover per leg × cost per side;
- long-only tilt cost per year = 2 × turnover × cost per side.

| Market | Card (characteristic signal) | Published gross L/S Sharpe (in-sample) | Planning haircut | Assumed turnover / L/S cost per year | Expected net L/S Sharpe | Expected net IR, long-only tilt (or long + futures hedge) | Recent live check | Verdict |
|---|---|---|---|---|---|---|---|---|
| US | Quality/profitability (quarterly ROE, GP/A), sector-neutral | 0.77 (HXZ ROE, 1972-2011) | 58% | 1.0x / 2.0% on about 9% vol | about 0.1 | about 0.1-0.2 (MSCI USA Quality live gross IR 0.33 minus about 0.1 cost) | RMW -16.4% in the 12 months to Aug 2026 | **BUILD-candidate** (also a benchmark for other cards' alphas) |
| US | Value (HMLm-style B/M, E/P) | 0.29 (AMP, 1972-2011) | 58% | 1.0x / 2.0% on about 10% vol | about -0.1 to 0 | about 0 | World Value IR -0.37 (2012-25); +3.3 pp over 12 months | BACKLOG (composite leg only) |
| US | 12-1 momentum (volatility-scaled per macro decision) | 0.33 (AMP); 0.60 (WML 1927-2013) | 58% | 4x / 8.0% on about 15% vol | below 0 | about 0 | USA Momentum IR 0.04 (2012-25) | BACKLOG (inside composite only) |
| US | Low-beta / BAB (value-weighted, beta-neutral) | 0.78 (Frazzini-Pedersen, equal-weight-like) | 58% plus Novy-Marx-Velikov critique | 1.5x / 3.0% | about 0 | raw negative; CAPM alpha about 0 (2012-25) | Minimum volatility -7.0 pp/yr (2020-25) | BACKLOG |
| US | Size | 0.33 (HXZ size factor) | 58% | 0.5x / 1.0% | about 0 | negative | R2000 minus R1000 -7.5 pp/yr (2021-25) | **DROP** |
| Korea | Value (B/P, E/P) + quarterly ROE composite; liquid universe; capped weights | 0.95 HML, 0.76 RMWq (Kang 2002-15) | 50% (short sample; less ex-US decay) | 1.0x / 1.4% on about 13% vol | about 0.3-0.4 | about 0.1-0.25 | value replicates in 69% of tests (Han et al. 2000-19) | **BUILD-candidate** (pending DC-3) |
| Korea | Investment (low asset growth) | 0.99 (Kang CMA), but only 24% of investment anomalies replicate (Han et al.) | 60% | 0.8x / 1.1% | about 0.2 | about 0.1 | conflicting evidence | BACKLOG (composite leg) |
| Korea | Low-beta / low-volatility | none retrieved | — | — | unknown | likely negative in 2025-26 (semis underweight) | top-2 stocks are 61% of MSCI Korea | BACKLOG (pending DC-1/DC-2) |
| Korea | Size | 0.12 (Kang SMB, t = 0.45) | — | — | about 0 | about 0 | — | **DROP** |
| Korea | 12-1 momentum | context brief: negative in high-turnover stocks; 20% replication excluding KOSDAQ | — | — | below 0 | below 0 | — | **DROP** |
| Japan | Value | 0.79 (AMP) | 33% | 1.0x / 2.0% (assumes 50 bp per side) | about 0.3 | about 0.1-0.2 (MSCI Japan Value IR 0.05 for 2012-25; +3.1 pp/yr for 2020-25) | 2025 +7.6 pp | BACKLOG (no Japan stock data yet) |
| Japan | Momentum | 0.09 (AMP) | — | — | below 0 | — | — | **DROP** (standalone) |
| Europe | Value + momentum composite | 0.87 (AMP Europe combination) | 33% | 2.0x / 4.0% on about 7% vol | about 0-0.2 | about 0.1 | Europe Value +4.2 pp/yr (2021-25) | BACKLOG |
| EM | Country-level value + momentum via ETFs | 1.16 (AMP country-index combination, all countries) | 33% | low (ETF) | — | — | MSCI EM Value IR -0.12 (2016-25) | BACKLOG (stock-level EM: DROP) |

**C. Corrections to the prior per-market weights (0-3 scale)**

| Market | Factor | Prior | P1 | Reason |
|---|---|---|---|---|
| US | XS-momentum | 3 | **1** | Live index IR about 0.04 (2012-25); WML about 0 since 2008 (context); 4x turnover at 50 bp per side gives negative net |
| US | Value | 1 | 1 | Long-run premium small (+0.36 pp/yr World since 1974); HML redundant in FF5 but HMLm survives in Barillas-Shanken; 2025-26 rebound |
| US | Quality | 3 | **2** | Most consistent live factor (IR 0.33-0.43) but RMW -16.4% (12 months to Aug 2026); absent before 1963; displaced from JKP tangency portfolio |
| US | Low-volatility | 2 | **1** | -7.0 pp/yr (2020-25); only defensible on a CAPM-alpha basis |
| Europe | XS-momentum | 3 | **2** | Best developed-market momentum in AMP (0.55) but cost-sensitive; no live check retrieved |
| Europe | Value | 2 | 2 | +4.2 pp/yr (2021-25) |
| Europe | Quality | 3 | **2** | Same reasons as US |
| Europe | Low-volatility | 2 | **1** | Global minimum-volatility failure in 2020-26 |
| Japan | Value | 3 | 3 | AMP 0.79 (strongest anywhere); +3.1 pp/yr (2020-25) |
| Japan | XS-momentum | 0 | 0 (use only as a hedge inside value-momentum composites) | AMP 0.09; Fama-French 2012 find no momentum in Japan |
| Japan | Low-volatility | 3 | **2** | No fresh Japan-specific evidence; global failure in 2020-26 |
| Korea | Value | 2 | **3 if DC-3 confirms with point-in-time book data; otherwise 2** | Strongest Korean evidence (Kang t = 3.41; 69% replication); KOSPI P/B 0.99 |
| Korea | Quality | 1 | 1 (test quarterly ROE) | Conflicting: RMWq t = 2.75 vs 5% replication |
| Korea | Low-volatility | 2 | **1** | Two-stock concentration; no Korean low-beta evidence retrieved |
| Korea | XS-momentum | 1 | **0** | Context brief plus Han et al. (20% replication excluding KOSDAQ) |
| EM | XS-momentum | 3 | **2** | Momentum in all EMs but Eastern Europe (Cakici); local and costly |
| EM | Value | 2 | 2 | Value in all 18 EMs; MSCI EM Value +2.8 pp/yr (2021-25) but -0.3 pp/yr (2016-25) |

**D. What not to do**
- Do not use CAPM-implied expected returns as forecasts.
- Do not rank stocks on estimated factor loadings (beta to HML, etc.).
- Do not build US long-short factor portfolios at 50 bp per side. If a US tilt is wanted, test the cheapest implementation (a static QUAL-vs-IWB style ETF tilt) as a separate card; it has only 13 years of live history, so INSUFFICIENT DATA is likely.
- Do not loosen the gate because factor cards fail it. Pool evidence across markets and use the longest point-in-time histories instead.

######## Gaps
- Turnover and volatility assumptions in table B are P1 assumptions, not measured values. DC-3 and DC-4 should replace them.
- No retrieved source covers Korean retail short-selling feasibility, so long-only plus futures hedge is assumed as the implementable form.


### [P1] Where and when it failed (lines 528-557)

###### 4. Where and when it failed (dated episodes)

| Date | What failed | Market | Numbers | Source |
|---|---|---|---|---|
| 1928-2003 (full sample) | CAPM SML | US | Lowest-beta 11.1% actual vs 8.3% predicted; highest-beta 13.7% vs 16.8% | [Fama-French 2004](https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa) |
| 1963-1990 | CAPM beta | US | Beta-return relation flat even as the only regressor | [Fama-French 1992](https://ideas.repec.org/a/bla/jfinan/v47y1992i2p427-65.html) |
| 1926-1963 (pre-discovery) | Profitability, investment | US | 0.09%/month (t = 0.86); 0.02%/month (t = 0.14) | [Linnainmaa-Roberts](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf) |
| July-August 1932 | Momentum | US | Losers +232% vs winners +32%; WML -60.98% (July), -74.36% (August) | [Daniel-Moskowitz](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf) |
| About 1972-2011 (about 30 years) | Stock momentum | Japan | About zero standalone; Sharpe 0.09 | [Asness 2011](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-That-Proves-the-Rule); [AMP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf) |
| Tech bubble (about 2.5 years) | Value (HML) | US | -40.6% drawdown | [Arnott et al.](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf) |
| Funding-stress episodes (TED spikes) | BAB | US | Wider TED spread coincides with BAB losses | [Frazzini-Pedersen](https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf) |
| March-May 2009 | Momentum | US | Losers +163% vs winners +8%; April 2009 WML -45.52% | [Daniel-Moskowitz](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf) |
| 2007 to mid-2020 (13.5 years) | Value (HML) | US | -55% drawdown, the deepest since 1963; revaluation -7.2 pp/yr | [Arnott et al.](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf) |
| After 2005, after publication | Average anomaly, net | US | About 4 bps/month net (68 bps gross in-sample) | [Chen-Velikov](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/945133D5A3ECEEAF466AEE91551FD225/S0022109022000874a.pdf/zeroing-in-on-the-expected-returns-of-anomalies.pdf) |
| Post-publication | Published predictors | US | 58% lower returns | [JKP quoting McLean-Pontiff](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf) |
| 1998-2011 at institutional scale | Short-term reversal | 19 developed markets | Does not survive trading costs | [Frazzini-Israel-Moskowitz](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies) |
| 2012-2019 | Value | Japan | -1.47 pp/yr vs MSCI Japan | [MSCI Japan Value](https://www.msci.com/documents/10199/255599/msci-japan-value-index.pdf) |
| 2020 | Value | World, Japan, Europe, EM | -16.9 / -13.6 / -10.4 / -12.7 pp vs parents | MSCI factsheets ([World](https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf), [Japan](https://www.msci.com/documents/10199/255599/msci-japan-value-index.pdf), [Europe](https://www.msci.com/documents/10199/255599/msci-europe-value-index.pdf), [EM](https://www.msci.com/documents/10199/255599/msci-emerging-markets-value-index.pdf)) |
| 2020 | Minimum volatility | World | -13.2 pp | [MSCI World Min Vol](https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf) |
| 2021 | Momentum | US | MSCI USA Momentum -14.1 pp | [MSCI USA Momentum](https://www.msci.com/documents/10199/255599/msci-usa-momentum-index.pdf) |
| 2021-2025 (every year) | Size | US | R2000 minus R1000: -11.7, -1.2, -9.6, -13.0, -4.5 pp | [IWM](https://www.ishares.com/us/products/239710/ishares-russell-2000-etf); [IWB](https://www.ishares.com/us/products/239707/ishares-russell-1000-etf) |
| 2022 | Quality | World | -4.2 pp (and -21.9% absolute) | [MSCI World Quality](https://www.msci.com/documents/10199/255599/msci-world-quality-index.pdf) |
| 2023 | Value, momentum, minimum volatility (AI concentration) | US, World | R1000V minus R1000G -31.2 pp; USA Momentum -17.6 pp; World Value -12.0 pp; World Min Vol -16.3 pp | [IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf)/[IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf); MSCI factsheets |
| 2024 | Value, minimum volatility | US, World | R1000V minus R1000G -19.0 pp; World Value -6.9 pp; World Min Vol -7.7 pp | Same |
| 2025 | Quality, minimum volatility | World | World Quality -4.7 pp; World Min Vol -10.4 pp | MSCI factsheets |
| 2025 | Any diversified or low-beta tilt | Korea | MSCI Korea +100.76% with 61% in two stocks; those two drove about half of the KOSPI market-cap gain | [MSCI Korea](https://www.msci.com/documents/10199/255599/msci-korea-index.pdf); [AMRO](https://www.amro-asia.org/narrowing-the-korea-discount-stock-market-reform-via-corporate-value-up) |
| September 2025 to August 2026 | Profitability (RMW) | US | -16.44% over 12 months; Small Weak +43.3% vs Small Robust +19.2% | [French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) |
| September 2025 to August 2026 | Minimum volatility | World | -13.5 pp over 12 months | [MSCI World Min Vol](https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf) |
| August 2026 (one month) | Value, profitability, investment | US | HML -3.54%; RMW -4.08%; CMA -2.01% | [French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) |


### [P1] Data-check requests (lines 560-604)

###### 5. Data-check requests for the data lab

- **DC-1. Korean SML test.**
  - Data: marcap 1995-2026.
  - Universe at each month-end: KOSPI+KOSDAQ common stocks with market cap above the 20th percentile and non-zero volume.
  - Beta: Frazzini-Pedersen style (1-year daily volatility ratio × 3- to 5-year correlation of overlapping 3-day returns, shrunk 0.6/0.4 toward 1) against a value-weighted market built from marcap.
  - Form beta deciles. Report next-month value-weighted and equal-weighted returns, CAPM alphas, and the Fama-MacBeth slope of returns on beta (Newey-West).
  - Split into 1995-2007, 2008-2016 and 2017-2026, with and without Samsung Electronics and SK hynix.
  - Expected: a flat or negative slope.
- **DC-2. Korean BAB and low-beta, two constructions.**
  - (a) Frazzini-Pedersen rank-weighted BAB.
  - (b) Novy-Marx-Velikov-style value-weighted, liquid, beta-neutral version.
  - (c) Long-only low-beta tercile vs KOSPI200, on a beta-adjusted (Jensen's alpha) basis.
  - Costs at 35/70 bp per side for stocks and 5/10 bp per side for a KOSPI200 futures hedge. Run all versions through the full nine-step gate.
- **DC-3. Korean value and quarterly profitability with point-in-time data.**
  - Signals: B/P from KRX marketplace PBR, or book equity from OpenDART lagged at least 3 months after the filing date; E/P; quarterly ROE (OpenDART, 2015 onward).
  - Portfolios: 2x3 size × characteristic sorts, value-weighted within legs, ex-micro-caps (bottom 20% by market cap removed), quarterly rebalance with a buy/hold buffer.
  - Report gross and net (35/70 bp) long-short Sharpe, and long-only top-quintile IR vs both KOSPI200 and a 10%-capped KOSPI.
  - Split 2000-2014 vs 2015-2026; report returns on DART earnings-filing days vs other days.
  - This test decides the Korea value weight (2 vs 3) and whether quality enters the composite.
- **DC-4. Update and decompose US factors.**
  - Replace the lab's French file (1926-2018) with the current release (through August 2026; CIZ-based since January 2025).
  - For Mkt-RF, SMB, HML, RMW, CMA (from 1963), UMD and short-term reversal, report by decade (1930s to 2020s) plus 2010-2019 and 2020-2026: annualized mean, volatility, Sharpe, t-statistic, maximum drawdown and its duration.
  - Report the annual returns for 2019-2026 explicitly.
  - Feed monthly HML and UMD through the gate, adapted to monthly frequency.
- **DC-5. Gate power calibration.**
  - Simulate 1,000 synthetic factor return paths with true Sharpe in {0.2, 0.3, 0.4, 0.6}, matching the empirical skewness and kurtosis of HML and UMD (block bootstrap of residuals).
  - Run the nine-step gate on each and report the share of PASS / REVISE / REJECT / INSUFFICIENT DATA.
  - This tells the owner what verdict a genuine but modest factor should be expected to get.
- **DC-6. Attribution of existing cards.**
  - For E1 (US and KRX), E2 (SPY and KODEX 200), E3, E5 and the KRX pairs cards, regress daily out-of-sample returns on the benchmark: Jensen's alpha, beta and Newey-West t-statistic.
  - For US sleeves, also regress on daily FF5+UMD.
  - Report whether the E1, E2 and E3 rejections reverse on a beta-matched (alpha) basis. E1 had a maximum drawdown of -15% vs -27%, so it may show positive alpha despite a lower Sharpe.
- **DC-7. Korean momentum-crash conditioning.**
  - 12-1 momentum deciles in the liquid KRX universe.
  - Mark months where the lagged 24-month market return is negative and the market rises in the same month.
  - List the 15 worst months and check the Daniel-Moskowitz pattern (14 of 15 in the US).
- **DC-8. Concentration and benchmark choice.**
  - From marcap, compute KOSPI cap-weighted vs 10%-capped vs equal-weighted returns for 2020-2026.
  - Compute the share of the 2025 KOSPI market-cap increase due to Samsung Electronics and SK hynix (AMRO reports "about half").
  - Use the capped index as the secondary benchmark for all Korean factor cards.
- **DC-9. Risk-free series for alpha calculations.**
  - Pull FRED TB3MS (US) and the Korean CD91 or KTB 3-month yield, 1995-2026.
  - Re-compute the approximate CAPM alpha of MSCI World Minimum Volatility (beta 0.67) for 2012-2019, 2020-2025 and 2012-2025, replacing the assumed 1% and 2.5% T-bill averages.


### [P1] Claims ledger (lines 607-641)

###### 6. Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P1-C01 | The security market line is too flat: low-beta stocks earn more and high-beta stocks less than CAPM predicts. | US 1928-2003 beta-sorted VW portfolios: lowest beta 11.1% actual vs 8.3% predicted; highest 13.7% vs 16.8%. Flat 1963-1990 (FF 1992). IS, gross. | [FF 2004](https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa); [FF 1992](https://ideas.repec.org/a/bla/jfinan/v47y1992i2p427-65.html) | T1 | Replicated from BJS 1972 and FM 1973 to FF 1992; international via BAB. | Beta is priced on macro-announcement days and overnight (C02). | CONTEXT: never use CAPM expected returns as forecasts; use beta for risk only. |
| P1-C02 | Beta earns a positive premium when macro news arrives and overnight, but not intraday. | Strong positive beta-return relation on announcement days (stocks, bonds, FX); positive overnight and negative intraday, weak over 24h. US and international. IS. | [Savor-Wilson 2014](https://ideas.repec.org/a/eee/jfinec/v113y2014i2p171-201.html); [Hendershott-Livdan-Rösch 2020](https://ideas.repec.org/a/eee/jfinec/v138y2020i3p635-662.html) | T1 | Two independent studies, multi-asset. | Non-announcement days flat or negative. | BACKLOG: any beta-timing or intraday card must condition on the calendar or the overnight session; low priority. |
| P1-C03 | Betting-against-beta shows large paper alphas, but much of it comes from equal-weight/micro-cap construction and profitability/investment tilts. | US 1926-2012: 0.70%/month, Sharpe 0.78, four-factor alpha 0.55% (t = 5.59); 18/19 international markets positive. NMV: $1.05 per $1 of BAB in bottom-1% market-cap stocks. IS, gross. | [Frazzini-Pedersen](https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf); [Novy-Marx-Velikov 2022](https://econpapers.repec.org/RePEc:eee:jfinec:v:143:y:2022:i:1:p:80-106) | T1 | Replicated internationally and across asset classes; construction contested; positive after costs per NMV. | Funding stress (TED spikes); 2020-26 low-risk slump. | BACKLOG: only a VW, liquid, beta-neutral version judged on alpha (DC-2). |
| P1-C04 | Long-only low-volatility lost heavily to cap-weighted markets in 2020-2026, mostly because of its 0.67 beta. | MSCI World Min Vol vs World: -3.17 pp/yr 2012-25 (ahead 5 of 14 years); -7.00 pp/yr 2020-25; -11.45 pp/yr 2023-25; -13.5 pp in the 12 months to Aug 2026. Approximate CAPM alpha +0.4%/yr 2012-25 (P1 calc, assumed rf). Gross index. | [MSCI World Min Vol](https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf); [MSCI World (in Value factsheet)](https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf) | T2 + derived | Live index; before costs; alpha uses assumed rf (DC-9). | 2020 (-13.2), 2023 (-16.3), 2025 (-10.4) pp. | DROP as a return signal; risk sleeve only, judged on Jensen's alpha. |
| P1-C05 | The low-risk anomaly is consistent with lottery demand plus benchmarking limits to arbitrage. | US top 1,000 stocks 1968-2008: $1 grew to $78.66 in the lowest-beta quintile vs $4.70 in the highest; lowest vs highest volatility $53.81 vs $7.35. Nominal, gross. | [Baker-Bradley-Wurgler 2011](https://pages.stern.nyu.edu/~jwurgler/papers/faj-benchmarks.pdf) | T1 | 41-year US sample; mechanism-based. | Raw-return losses 2020-26. | CONTEXT. |
| P1-C06 | The SML flattens and can invert when aggregate disagreement is high. | Model plus tests: with high disagreement, expected return first rises then falls with beta (short-sale constraints). US. | [Hong-Sraer, NBER w18548](https://www.nber.org/papers/w18548) | T1 | Published JF 2016. | — | BACKLOG: possible conditioning variable for beta cards only (macro sizes risk, never directs). |
| P1-C07 | CAPM remains the practitioner standard for cost of equity despite known bias at extreme betas. | 73.5% of 392 CFOs use CAPM always or almost always; Damodaran keeps it as default; FF 2004: CAPM cost of equity too high for high-beta and too low for low-beta. | [Graham-Harvey 2001](https://people.duke.edu/~charvey/Research/Published_Papers/P67_The_theory_and.pdf); [Damodaran slides](https://pages.stern.nyu.edu/~adamodar/pdfiles/acf4E/presentations/risk&ret.pdf); [FF 2004](https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa) | T1 | Survey plus standard textbook practice. | Bias at extreme betas. | CONTEXT: any displayed "expected return" uses a flattened SML and is labelled. |
| P1-C08 | FF5 improves on FF3 but is statistically rejected, and HML becomes redundant once RMW and CMA are included. | Explains 71-94% of cross-sectional variance of test-portfolio expected returns; GRS rejects; fails on small, high-investment, low-profit stocks. US from 1963. IS. | [FF 2015](https://www.sciencedirect.com/science/article/pii/S0304405X14002323) | T1 | US; RMW and CMA fail before 1963 (C17). | Small-growth-junk portfolios; 2025-26 junk rally. | BUILD (risk model): FF5+UMD daily attribution for US cards. |
| P1-C09 | In the q-factor model, investment and ROE carry the strongest premia and absorb many anomalies. | US 1972-2011: investment 0.44%/month (t = 4.73), ROE 0.60% (t = 4.85), size 0.31% (t = 2.09); earnings-surprise alpha 0.14% (t = 0.92) vs Carhart 0.32% (t = 2.43). IS, gross. | [HXZ, NBER w18435](https://www.nber.org/system/files/working_papers/w18435/w18435.pdf) | T1 | Published RFS 2015; q-data after 2015 not accessed. | Absent before 1963 (Linnainmaa-Roberts). | CONTEXT / alternative risk model; use quarterly ROE in signal design. |
| P1-C10 | The best-ranked factor model uses timely factors: {Mkt, SMB, IA, ROE, HMLm, UMD}. | US 1972-2013 Bayesian comparison: highest posterior; HMLm takes 99.5% of value-factor probability, ROE 99.5% of profitability probability. | [Barillas-Shanken, NBER w21771](https://www.nber.org/system/files/working_papers/w21771/w21771.pdf) | T1 | Published JF 2018; US only. | — | BUILD-candidate design: monthly-updated value and quarterly ROE; UMD in the risk model. |
| P1-C11 | Mispricing and behavioral factor models price anomalies better than FF5. | SY 1967-2013: average absolute alpha 0.18% vs 0.45% (FF5) vs 0.34% (q). DHS 1972-2014: 3 of 34 alphas significant vs 18 (FF5), 6 (q), 7 (SY); PEAD monthly Sharpe 0.35 (about 1.2 annualized). IS, gross. | [Stambaugh-Yuan PDF](https://www.nber.org/system/files/working_papers/w21533/w21533.pdf); [DHS PDF](https://www.nber.org/system/files/working_papers/w24163/w24163.pdf) | T1 | Published RFS; in-sample model horse races. | — | CONTEXT: supports an earnings-drift card (other panel); a PEAD factor is an optional attribution add-on. |
| P1-C12 | Most of the factor zoo is false at the single-signal level, and new factors need t > 3. | 316 factors; 27-53% of 296 significant factors are false discoveries (BHY 5% to Bonferroni); thresholds 3.39-3.78 by 2012, about 4.0 by 2032. | [Harvey-Liu-Zhu 2016](https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF) | T1 | Multiple-testing theory; widely adopted. | — | Gate already consistent; require in-sample t ≥ 3 before a new characteristic becomes a card. |
| P1-C13 | With NYSE breakpoints and value weights, 64-85% of anomalies fail; liquidity anomalies almost all fail; micro-caps drive many results. | 447 anomalies: 64% insignificant at 5%, 85% at t = 3; 93% of liquidity anomalies fail. Micro-caps: 60.7% of firms, 3.21% of market cap (US 1967-2016). | [HXZ, NBER w23394](https://www.nber.org/papers/w23394); [HXZ 2018 PDF](https://theinvestmentcapm.com/uploads/1/2/2/6/122679606/replication2018oct.pdf) | T1 | Published RFS 2020. | — | BUILD rule: capped VW weights and micro-cap exclusion in all KRX and US cards. |
| P1-C14 | Major factor themes replicate globally, with about one-third smaller out-of-sample alpha. | 153 factors, 93 countries: US replication 84.9% (OLS) / 77.3% (BY); OOS alpha 0.31% vs IS 0.45%/month; regional-only replication 60.7% (developed ex-US), 56.3% (EM). Chen-Zimmermann: 98% of 161 clear predictors reproduce (slope 0.90). | [JKP PDF](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf); [Chen-Zimmermann (Fed)](https://www.federalreserve.gov/econres/feds/open-source-cross-sectional-asset-pricing.htm) | T1 | Bayesian, global OOS, open code. | Profitability, investment and size displaced from the tangency portfolio. | CONTEXT: themes are real but smaller; use JKP Korea data for cross-checks (non-commercial licence). |
| P1-C15 | US anomaly returns decay sharply after publication, while outside the US the decay is not reliably observed. | McLean-Pontiff: 26% lower OOS, 58% lower post-publication (US). Jacobs-Müller: 241 anomalies in 39 markets, only the US declines reliably. Ilmanen: about 30% OOS drop over a century. | [JKP quoting McLean-Pontiff](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf); [Jacobs-Müller](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html); [Ilmanen et al.](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence) | T1/T2 | Several independent studies. | — | Keep the 60% live haircut (US-calibrated, conservative for Korea); plan with 33-60%. |
| P1-C16 | Net of realistic costs and data-mining, the average anomaly earns about zero today, and only low-turnover strategies survive. | 204 anomalies: 68 bps/month gross IS falls to about 4 bps net after 2005 and publication; best at most about 10 bps. Strategies under 50% one-sided monthly turnover survive (NMV); short-term reversal fails at scale (FIM, 19 markets, 1998-2011). | [Chen-Velikov JFQA](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/945133D5A3ECEEAF466AEE91551FD225/S0022109022000874a.pdf/zeroing-in-on-the-expected-returns-of-anomalies.pdf); [Novy-Marx-Velikov 2016](https://www.nber.org/papers/w20721); [Frazzini-Israel-Moskowitz](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies) | T1/T2 | Published; FIM uses live institutional trade data. | — | DROP high-turnover anomalies; quarterly or annual rebalancing with buy/hold buffers only. |
| P1-C17 | Profitability and investment premia are absent in pre-1963 data, whereas value survives. | US 1926-1963: value 0.43%/month (t = 2.09); profitability 0.09% (t = 0.86); investment 0.02% (t = 0.14); 8 of 36 accounting anomalies significant. True OOS. | [Linnainmaa-Roberts PDF](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf) | T1 | Published RFS 2018. | — | Downweight quality from 3 to 2; drop the "most consistent factor" claim. |
| P1-C18 | Value's 2007-2020 drawdown was the deepest since 1963 and came from revaluation, not broken fundamentals. | HML -55% over 13.5 years; revaluation -7.2 pp/yr; structural return +1.1%/yr (5.9% before 2007); value spread at the cheapest percentile in 2020; intangibles-adjusted HML drawdown -43%. US. | [Arnott et al. 2021](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf) | T1 | FAJ 2021; US. | 2020 trough. | CONTEXT: value cards need evaluation windows of 15+ years; decade-long droughts are normal. |
| P1-C19 | Value rebounded in 2021-22 and again in 2025-26, most strongly outside the US and in cheap technology. | World Value active: +0.4 (2021), +11.9 (2022), -12.0 (2023), -6.9 (2024), 0.0 (2025), +3.3 pp (12 months to Aug 2026). Europe +4.2 pp/yr (2021-25), Japan +3.1 pp/yr (2020-25). HML +13.55% over 12 months to Aug 2026. VLUE +80% over 1 year with 43% IT. | MSCI ([World](https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf), [Japan](https://www.msci.com/documents/10199/255599/msci-japan-value-index.pdf), [Europe](https://www.msci.com/documents/10199/255599/msci-europe-value-index.pdf)); [French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html); [VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf) | T2/T1 | Live; gross index or net fund. | 2023-24 AI-concentration years. | BUILD-candidate for Korea and Japan value; US value only as a composite leg; always report sector composition. |
| P1-C20 | Stock momentum earns a positive premium but crashes in market rebounds after bear markets. | US 1927-2013 WML: 17.9%/yr, 30% volatility, Sharpe 0.60, monthly skew -4.70. July-August 1932 losers +232% vs winners +32%; March-May 2009 losers +163% vs winners +8%; 14 of 15 worst months followed negative 2-year market returns. | [Daniel-Moskowitz PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf) | T1 | Replicated across markets and asset classes. | 1932, 2009, 2023. | CONTEXT: supports volatility scaling and the bear-state gate (already decided). |
| P1-C21 | US momentum indexes have earned roughly nothing over the cap-weighted market since 2012, before costs. | MSCI USA Momentum: +0.34 pp/yr 2012-25 (IR 0.04); live 2013-25 +0.45 pp/yr; -14.1 (2021), -17.6 (2023), +7.2 (2024), +6.1 pp (12 months to Aug 2026). Gross. | [MSCI USA Momentum](https://www.msci.com/documents/10199/255599/msci-usa-momentum-index.pdf); [MSCI USA](https://www.msci.com/documents/10199/255599/msci-usa-index-gross.pdf) | T2 | Live index after launch. | 2021, 2023. | BACKLOG: no standalone US stock-momentum card at 50 bp per side. |
| P1-C22 | Quality/profitability was the most consistent live factor in 2012-2025 but crashed in the 2025-26 junk rally. | World Quality +1.68 pp/yr (ahead 9 of 14 years, IR 0.43); USA Quality live +1.31 pp/yr (2013-25). RMW -16.44% over 12 months to Aug 2026; Small Weak +43.3% vs Small Robust +19.2%. | [MSCI World Quality](https://www.msci.com/documents/10199/255599/msci-world-quality-index.pdf); [MSCI USA Quality](https://www.msci.com/documents/10199/255599/msci-usa-quality-index.pdf); [French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) | T2/T1 | Live; gross. | 2022 (-4.2 pp), 2025 (-4.7 pp), 2025-26 RMW. | BUILD-candidate as a composite leg; weight 2. |
| P1-C23 | Size is not a standalone premium in recent data or in Korea, and survives only after controlling for junk. | Korea 2002-15 SMB 0.16%/month (t = 0.45); R2000 minus R1000 -7.5 pp/yr (2021-25); SMB (FF3) -0.22% over 12 months to Aug 2026; size robust after quality control in 24 markets. | [Kang 2016](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [IWM](https://www.ishares.com/us/products/239710/ishares-russell-2000-etf); [French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html); [Asness et al. 2018](https://ideas.repec.org/a/eee/jfinec/v129y2018i3p479-509.html) | T1/T2 | Consistent across sources. | 2021-25 every year. | DROP size as a signal; keep SMB in risk models. |
| P1-C24 | Value and momentum are negatively correlated in every market, so combinations beat either alone (Japan momentum is the weak case). | 1972-2011 combination Sharpe: US 0.63, UK 0.77, Europe 0.87, Japan 0.78, global 1.04; correlations -0.43 to -0.60; Japan momentum alone 0.09. Gross, IS. | [AMP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf); [Asness 2011](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-That-Proves-the-Rule) | T1 | Replicated across 8 asset classes. | Japan momentum standalone. | Build composite cards, not single-factor cards; Japan momentum weight 0. |
| P1-C25 | Factor premia exist internationally, but local factor models explain local returns better than global ones. | Value in all four developed regions; momentum everywhere except Japan; integrated pricing not supported. 18 EMs (1990-2011): value everywhere, momentum except Eastern Europe; local factors much better. | [FF 2012](https://econpapers.repec.org/RePEc:eee:jfinec:v:105:y:2012:i:3:p:457-472); [Cakici et al. 2013](https://ideas.repec.org/a/eee/ememar/v16y2013icp46-65.html) | T1 | Two independent studies. | — | Per-market risk models (local Korean factors) and per-market weights. |
| P1-C26 | In Korea, value, investment and quarterly profitability were priced in 2002-2015, while 2000-2019 replication favours value and (KOSDAQ-driven) momentum, not profitability. | Kang: HML 1.05%/month (t = 3.41), RMWq 0.65% (t = 2.75), CMA 0.66% (t = 3.57). Han-Lee-Kang: 37.8% of 148 anomalies VW-significant; value 69%, momentum 67% (20% excluding KOSDAQ), profitability 5%. IS, gross. | [Kang 2016](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [Han-Lee-Kang 2020](https://www.emerald.com/jdqs/article/28/2/3/206237/Market-anomalies-in-the-Korean-stock-market) | T1 | Two Korean studies; conflicting on profitability; short samples; not cost-adjusted. | 2025-26 concentration. | BUILD-candidate: Korean value + quarterly ROE composite (DC-3); momentum DROP. |
| P1-C27 | Korea's cap-weighted benchmark is dominated by two semiconductor stocks, and that dominates any factor test. | MSCI Korea (Aug 2026): Samsung Electronics 34.55%, SK hynix 26.27%, IT 68.99%; 2025 +100.76%; 12 months +170.65%. AMRO: those two drove about half of the 2025 KOSPI market-cap gain; KOSPI P/B 0.99; over 60% of firms have ROE below 7%. | [MSCI Korea](https://www.msci.com/documents/10199/255599/msci-korea-index.pdf); [AMRO 2026](https://www.amro-asia.org/narrowing-the-korea-discount-stock-market-reform-via-corporate-value-up) | T2/T1 | Official and index-provider data. | 2025-26. | Evaluate Korean cards against both cap-weighted and capped benchmarks; add a SEMI factor to attribution (DC-8). |
| P1-C28 | Anomaly returns concentrate on news days, pointing to mispricing, but factor-model tests alone cannot separate risk from mispricing. | 97 anomalies: returns 6x higher on earnings days and 50% higher on news days. KNS: reduced-form tests cannot discriminate. SY: short-leg sentiment slopes 2-3x larger. Ilmanen: little relation to macro risk. | [Engelberg-McLean-Pontiff](https://ideas.repec.org/a/bla/jfinan/v73y2018i5p1971-2001.html); [Kozak-Nagel-Santosh](https://ideas.repec.org/a/bla/jfinan/v73y2018i3p1183-1223.html); [SY PDF](https://www.nber.org/system/files/working_papers/w21533/w21533.pdf); [Ilmanen et al.](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence) | T1/T2 | Several independent studies. | — | CONTEXT: treat premia as decaying mispricing (haircuts); long-only captures less than the published spread. |
| P1-C29 | QUANTGEN's gate is structurally underpowered for factor-tilt cards with net Sharpe or IR of 0.2-0.4. | P1 calc (Lo i.i.d. SE): 18 OOS years needed for SR 0.4 and 31 for SR 0.3. With about 27 OOS years: P(step 2) = 0.64 at SR 0.4; P(step 5) = 0.51 at IR 0.25 (0.31 with 10 years). | Derived from the gate definition in `00_QUANTGEN_context.md` | Derived | i.i.d. approximation; skew lowers power (DC-5). | — | Expect REVISE or INSUFFICIENT DATA; do not loosen the gate; pool markets and use the longest PIT histories. |
| P1-C30 | Every card needs a factor-attribution block, and cards with beta ≠ 1 need a beta-matched (Jensen's alpha) benchmark test. | Sharpe comparisons ignore cash mixing, while a Jensen's-alpha t-test asks whether adding the card raises the benchmark's Sharpe. Factor exposures plus expenses explain apparent fund skill (Carhart); passive tilts show CAPM alpha (FF 2004). | [Carhart 1997](https://ideas.repec.org/a/bla/jfinan/v52y1997i1p57-82.html); [FF 2004](https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa) | T1 + derived | Standard performance-evaluation practice. | — | BUILD: risk/attribution module (beta, CAPM alpha, FF5+UMD or local Korean alpha, Newey-West) on all cards; gate change only via pre-registration (DC-6). |



---

## P2_technical_analysis_evidence.md

### [P2] Persona and position summary (lines 1-29)

##### P2 position paper: technical trading rules after correcting for data snooping and costs (QUANTGEN technical & fundamental signals panel)

**Persona line.** P2 is a "Professor of Financial Econometrics, technical-analysis specialist". This is a fictional composite persona, not a real person. Its background is replication work on published trading rules and the bootstrap and multiple-testing machinery used to check them (White's Reality Check, Hansen-type SPA tests, false-discovery-rate control). The lens: every chart rule is one draw from a large family of rules. A result counts only if it survives family-wise testing, out-of-sample data, and costs charged at QUANTGEN's pre-registered rates: KRX stock 35 bp per side, US shares via KIS 50 bp, KRX ETF 3 bp, futures 5 bp, crypto 10 bp, with everything re-run at 2x.

**Position summary.**
1. After data-snooping control and realistic costs, the classic technical toolkit has no robust out-of-sample, net-of-cost support in developed equity markets after the late 1980s. That toolkit covers moving-average, filter, breakout and OBV rules on one index; oscillators (RSI, MACD, stochastics/Williams %R, Bollinger Bands, ADX, Ichimoku); candlesticks; chart patterns; Fibonacci levels; and Elliott waves.
2. Profits found in early samples (DJIA 1897-1986, FX 1973-1990) either vanish in publication-era data or are erased by low costs once false discoveries are controlled.
3. Four price-based constructs keep better support. Each has an economic mechanism and slow turnover:
   - (i) Diversified, volatility-scaled time-series trend. It was strong from 1880 to 2009, but excess returns were only about 0.4%/yr in 2010-2018. It is also statistically fragile once volatility scaling and small-sample bias are handled.
   - (ii) Proximity to the 52-week high (anchoring). Strong gross in the US 1963-2001, but not significant net of costs in most international markets.
   - (iii) Moving-average-distance and trend-factor signals in the US cross-section.
   - (iv) Short-term reversal. It is real gross, but it is a payment for supplying liquidity and cannot be harvested at QUANTGEN's 35-50 bp per-side retail costs.
4. QUANTGEN's own data agree. On KRX top-500 stocks 1996-2026, none of the price-based signals P2 tested clears 35 bp per side with t > 2. The volume-filtered 5-day reversal in the prior design loses about 0.9% per week net. In the July 2026 KRX crash, 12-1 momentum lost 27% in one month and a 200-day trend filter lost 34%, against 23% for buy-and-hold.
5. Recommendations:
   - Keep the crypto trend card (C3).
   - Build 52-week-high proximity, MA distance and capital-gains overhang only as features feeding cross-sectional composites. Standalone cards with slow rebalancing stay in the BACKLOG.
   - Add a 52-week-high-neutral construction to any momentum sleeve.
   - Use technical indicators only as bounded risk-sizing inputs, consistent with the macro overlay.
   - Enter candlesticks, Fibonacci, Elliott waves, chart-pattern rules, standalone oscillator rules, KRX stock-level MA timing and the volume-filtered 5-day reversal in the DO-NOT-BUILD register.
6. Any new technical family must pass a family-level SPA/Reality Check and FDR test before its best member may enter the nine-step gate, with every family member counted as a trial.

**How to read the numbers.**
- Every number is labelled with market, period, in-sample (IS) or out-of-sample (OOS), and gross or net.
- "Desk check" means P2's own computation on the data-lab files named in the context brief: KRX marcap daily 1995-2026, SPY daily 1998-2021 and Shiller monthly 1871-2026.
- Desk checks are unreviewed. Their parameters were taken from the literature rather than tuned, which makes them pseudo-out-of-sample for those constructs.
- All desk checks decide at the close of day t and earn from t+1.
- Cash earns 0% unless stated. This understates rules that sit in cash by roughly the T-bill rate times the share of time spent out of the market.
- KRX returns come from the file's ChangesRatio field, which is price change only (no dividends). SPY desk checks are price-only.


### [P2] Desk checks on data-lab files (lines 207-274)

######## F. P2 desk checks on QUANTGEN data-lab files (unreviewed; parameters from the literature, not tuned)
- **DC1: SPY trend-rule family with Reality Check and SPA.**
  - Setup: SPY daily closes, price only, 1998-12-31 to 2021-03-31 (5,598 sessions). K = 100 long/flat rules: close > SMA(n) and n-day return > 0, for n = 5, 10, …, 250. Costs 5 and 50 bp per side; benchmark buy-and-hold on the same days. Stationary bootstrap, mean block 10, B = 1,000, seed 11.
  - At 5 bp: 0 of 100 rules beat buy-and-hold mean return; 30 of 100 beat its Sharpe (0.37).
  - Best rule: 155-day TSMOM, Sharpe 0.52 (+0.16). Nominal p = 0.172, RC p = 0.696. On the mean criterion, RC p = 0.932 and consistent SPA p = 1.000.
  - The IS (1999-2009) winner, 175-day TSMOM, beat buy-and-hold Sharpe by +0.40 in-sample and lost by 0.22 OOS (2010-2021). 0 of 100 rules beat buy-and-hold Sharpe in 2010-2021.
  - At 50 bp: 0 of 100 rules beat buy-and-hold Sharpe.
  — P2 desk check (data-lab SPY file)
- **DC2: SPY cost sensitivity, 1998-10-20 to 2021-03-31, price only (buy-and-hold CAGR 6.05%, Sharpe 0.40, max DD −56.5%).**
  - SMA200 (7.4 switches/yr): at 5 bp, CAGR 3.76%, Sharpe 0.38, max DD −30.0%. At 50 bp, 0.37% (Sharpe 0.09). At 100 bp, −3.28% (Sharpe −0.22).
  - SMA20 (31 switches/yr): −0.26% at 5 bp; −13.3% at 50 bp.
  — P2 desk check
- **DC3: KRX cross-section.**
  - Universe: KOSPI + KOSDAQ + KOSDAQ GLOBAL common shares (SPACs excluded). Top 500 by market cap at each month-end, price ≥ 1,000 KRW, at least 200 valid sessions in the past 252.
  - Portfolios: 30% tails, equal-weighted, monthly. Costs 35/70 bp per side on |Δw|. Period Jul 1996 to Sep 2026. Each row lists long/short (L/S) gross, net of 35 bp and net of 70 bp per side.
  - **52-week high (P / 252-day max):**
    - Monthly rebalancing: L/S 0.66%/month gross (t 1.67) → 0.25% (t 0.65) → −0.15%.
    - Gross by decade: 0.63 (1996-2005), 0.73 (2006-15), 0.62 (2016-26).
    - Long minus equal-weighted universe: 0.31% gross (t 1.69) → 0.07% at 35 bp. 2016-2026 long-only: 0.44% gross (t 2.15) → 0.21% (t 1.05).
    - Rebalanced every 6 months: L/S 7.37%/yr gross (t 1.37) → 5.73% → 4.10%. Long-only 2.20% gross → 1.34% → 0.48%.
    - Rebalanced every 3 months: L/S 7.73% gross (t 1.66) → 5.19% → 2.64%. Long-only 2.33% → 0.92% → −0.48%.
  - **Price / SMA200:** L/S 0.28%/month gross (t 0.69) → −0.12% at 35 bp.
  - **MA21 / MA200 (MAD-like):** L/S 0.51% gross (t 1.28) → 0.15% at 35 bp; 2006-15 0.25%, 2016-26 0.27% (t 0.61).
  - **12-1 momentum:** L/S 0.62% gross (t 1.82) → 0.28% (t 0.83) → −0.05%. Worst months: 2026-07 −27.2%, 2001-01 −25.5%, 1998-01 −21.3%.
  - **1-month reversal (losers minus winners):** L/S 0.41% gross (t 1.20) → −0.58% at 35 bp (t −1.68). Gross by decade: 1.35% (1996-2005), −0.13% (2006-15), +0.09% (2016-26).
  - **Value-weighted, 2016-2026** (from an earlier run without KOSDAQ GLOBAL): L/S gross MA21/MA200 1.17% (t 1.64), P/SMA200 0.99% (t 1.38), 12-1 momentum 0.98% (t 1.39), 52-week high 0.57% (t 0.89). All insignificant and dominated by a few mega-caps.
  — P2 desk check (marcap)
- **DC4: KRX weekly 5-day reversal (the prior design's card).**
  - Setup: top 500, quintiles on the 5-day return, losers minus winners, hold 5 sessions; costs 35 bp per side on both legs.
  - Unconditional, 1996-2026: 0.53%/week gross (t 6.47) and −0.59%/week net. Turnover Σ|Δw| ≈ 3.2 per week.
    - Gross by decade: 0.85% (1996-2005), 0.53% (2006-15), 0.21% (2016-26, t 2.12).
    - Net, 2016-2026: −0.89%/week.
  - With the volume filter (5-day average volume / prior 20-day average > 1.5), 1996-2026: 0.44%/week gross (t 3.17) and −0.88%/week net.
    - Gross by decade: 1.09%, 0.35% and −0.10% (2016-26, t −0.45).
  — P2 desk check
- **DC5: KRX Medhat-Schmeling design.**
  - Setup: top 1,500 by market cap; prior-month turnover = 21-day sum of traded value / market cap; turnover terciles; quintiles of the past-21-day return within each tercile; equal-weighted; monthly.
  - Winners minus losers, 1996-2026, gross: high-turnover tercile −1.10%/month (t −2.24); low-turnover tercile −0.61% (t −1.85).
  - So KRX shows reversal, not short-term momentum, in high-turnover stocks. The reversal side nets about −0.1% (high turnover) and −0.5% (low turnover) per month at 35 bp per side, given turnover of about 3.3-3.4 per month.
  — P2 desk check
- **DC6: KRX replication of Han-Yang-Zhou.**
  - Setup: equal-weighted volatility deciles (past-252-day daily volatility, re-sorted each June); 10-day MA of each decile index; long the decile or 0% cash; costs per full-portfolio switch.
  - Highest-volatility decile, 1996-2026:
    - Buy-and-hold −7.9%/yr.
    - MA timing: 30.0%/yr gross (t 6.99), 18.0% at 35 bp, 5.9% at 70 bp; 34 switches per year.
    - Gross by decade: 44.9% (1996-2005), 31.0% (2006-15), 15.0% (2016-26), the last netting −11.7% at 70 bp.
    - With one extra day of execution lag: 18.0% gross, 6.0% at 35 bp, −6.0% at 70 bp. In 2016-2026 with the lag: 6.7% gross (t 0.99), −6.7% at 35 bp.
  - Lowest-volatility decile: 8.5% gross → −2.9% at 35 bp.
  - Daily lag-1 autocorrelation of the decile returns: 0.14-0.22.
  — P2 desk check
- **DC7: KRX index-level trend.**
  - Setup: value-weighted top-200 index proxy, price only, cash 0, 3 bp per switch.
  - SMA50, Sharpe (rule vs buy-and-hold): 1.05 vs 0.42 (1997-2005); 0.27 vs 0.26 (2006-15); 0.63 vs 0.63 (2016-26).
  - 2016-2026 is mixed by lookback: SMA120 Sharpe 0.73 vs 0.63, SMA200 0.57 vs 0.63. CAGR is below buy-and-hold for all three lookbacks (SMA200 9.58% vs 13.10%).
  — P2 desk check
- **DC8: The monthly-average price trap.**
  - Shiller's S&P series is built from monthly averages of daily closes ([Shiller data page](http://www.econ.yale.edu/~shiller/data.htm)). Its monthly returns have lag-1 autocorrelation of 0.274 (1871-2026). SPY month-end returns have 0.057, SPY monthly-average returns 0.206 (1998-2021).
  - 10-month SMA on Shiller total return (dividends/12), 1881-2023, cash 0:
    - Next-month execution: CAGR 9.35%, Sharpe 0.98.
    - Skipping one month: 7.58%, Sharpe 0.82.
    - Buy-and-hold: 9.16%, Sharpe 0.69.
  - SPY month-end 10-month SMA, Nov 1999 to Mar 2021, price only: CAGR 6.89% vs 5.10%, max DD −16.8% vs −52.2%. That sample contains two deep bear markets.
  — P2 desk check
- **Data-quality flags for the data lab** (P2 desk check of the marcap files):
  - Codes before 2000-05-26 are stored without leading zeros ("5930" instead of "005930"). This silently breaks every code-keyed history at that date unless codes are zero-padded.
  - A separate "KOSDAQ GLOBAL" market label exists from 2022-11-21: 48 names worth about 77 trillion KRW at 2024-12-30, 42 of them in the top 500. It must be included in KOSDAQ universes.
  - ChangesRatio is price change only (no dividends).


### [P2] Where and when it failed (Q4) (lines 406-463)

###### Q4. Where and when it failed (dated episodes, with numbers)

####### Takeaway
- Technical rules fail in five recurring ways: post-publication and out-of-sample decay (US 1987+, FX 1989-1993, trend 2010-2018); market-structure change (decimalization in 2001, ETF listings); whipsaws in range-bound markets (US 2011/2015/2018, KRX 2024-25); V-shaped crashes (Mar 2020, Jul 2026); and cost sensitivity (any rule with more than about 10 switches per year at retail costs).
- QUANTGEN's own futures-trend and sector-momentum cards already sit inside this failure set.

####### Cited Findings
| When | Construct | Market | What happened (numbers) | Source |
|---|---|---|---|---|
| 1987-1996 (OOS) | Best of 7,846 MA/filter/S&R/breakout/OBV rules | DJIA | Best rule 14.41%/yr gross, nominal p 0.004 → RC p 0.341 | [STW 1999](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf) |
| 1984-1996 | Same universe | S&P 500 futures | Nominal p 0.042 → RC p 0.908 | [STW 1999](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf) |
| 1987-2011 (OOS) | BLL's best rules, unchanged | US indices | No predictive power | [FJQ 2014](https://ideas.repec.org/a/eee/revfin/v23y2014i1p30-45.html) |
| After mid-1980s | Momentum-type rules on DJIA members | US | Profits confined to mid-1960s to mid-1980s; required short selling | [Taylor 2014](https://ideas.repec.org/a/eee/jbfina/v40y2014icp286-302.html) |
| 1989-1993 breaks; 1991-2005 | Published FX filter/MA rules | 10 USD pairs | Levich-Thomas portfolio 5.74% → −0.11%/yr net; Sharpe 0.90 → −0.02 | [NWU WP](https://files.stlouisfed.org/files/htdocs/wp/2006/2006-046.pdf) |
| 2001 (decimalization) | Prominent anomaly portfolio | US | Average returns roughly halved | [CST 2014](https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html) |
| 2001-2007 | 5,806 rules | 49 markets incl. Korea | Zero markets significant after RC; Korea adjusted p 0.942 | [MCC](https://c.mql5.com/forextsd/forum/210/Technical%20Analysis%20Around%20the%20World.pdf) |
| 2003-2010 | Rule universe | US tech and small caps | Futile after snooping adjustment (vs significant 1995-2002) | [Shynkevich 2012](https://ideas.repec.org/a/eee/jbfina/v36y2012i1p193-208.html) |
| After ETF listings | Rule universe | Growth and emerging indices | Predictive power weakens | [HHK 2010](https://ideas.repec.org/a/eee/empfin/v17y2010i3p471-484.html) |
| Jul-Aug 1932; Mar-Apr 2009 | Momentum (WML) | US | −88.48%; −45.60% (gross) | [Jeon & Byun 2023](https://epublications.marquette.edu/cgi/viewcontent.cgi?article=1168&context=fin_fac) |
| 2010-2018 | Diversified trend, 67 markets | Futures/forwards | Excess return 0.4%/yr vs 6.3% in 2000-09 (net of costs) | [AQR 2019](https://www.belmontinvestments.com/cimg/file/articles/53/pdf/190425aqrtrendfollowing.pdf) |
| 2010-2016 | Same | Same | 3.3%/yr net of 2/20 vs 6.3% (2000s) and 8.3% (1990s) | [HOP 2017](https://static.twentyoverten.com/593e8a9e7299b471eaecf644/SkLoGL67M/A-Century-of-Evidence-on-Trend-Following-Investing.pdf) |
| Since 2011 | Low-turnover short-term reversal | US | "Tapered off" | [MS 2022](https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf) |
| QUANTGEN OOS | B3 TSMOM, 10 futures | Futures | OOS Sharpe 0.08 [−0.27, 0.43]; "no measurable edge after 2009" | context brief |
| QUANTGEN OOS | E1 trend switch; E5 sector momentum | US/KRX ETFs; sector SPDRs | 0.84 vs 0.95 (US), 0.52 vs 0.74 (KRX); 0.48 vs 0.63 | context brief |
| 1998-01 (post-IMF rebound: KRX top-500 EW +40.3%, VW +50.1%) | 52-week-high L/S; 12-1 momentum | KRX top 500 | 52-week-high L/S −39.6%; momentum −21.3% (gross) | P2 desk check |
| 2010-2019 | SMA200 timing, 5 bp | SPY (price only) | CAGR 5.29% vs 11.21%; Sharpe 0.51 vs 0.79; 85% time in market | P2 desk check |
| 2011 / 2015 / 2018 | SMA200 whipsaw years (10, 13 and 11 switches) | SPY | −9.7% vs −0.2%; −8.9% vs −0.8%; −9.3% vs −6.3% | P2 desk check |
| 2010-2019 | 10-month SMA, skip-month execution | S&P Composite (Shiller, total return) | CAGR 8.06% vs 13.31%; Sharpe 0.92 vs 1.36 | P2 desk check |
| 2020-02-19 to 2020-12-31 (V-crash) | SMA200 | SPY | +11.0% buy-and-hold vs −0.5% for the rule (gross). Crash leg (2/20-3/23): −34.1% vs −17.4%. Rebound (3/24-8/31): +56.7% vs +12.1%. Exit 2020-02-28, three whipsaws in early March, re-entry 2020-05-28 | P2 desk check |
| 2020-03 to 2020-07 | 10-month SMA (monthly) | S&P Composite (monthly averages) | −16.4% vs −2.1% (long through March's −19.1%, out for the rebound) | P2 desk check |
| 2020-03-20 to 2020-12-31 | SMA200 | KRX value-weighted top-200 proxy | +43.4% vs +97.1% | P2 desk check |
| 2024-07 to 2025-04 (range) | SMA200, 9 switches | KRX proxy | −19.7% vs −9.2% | P2 desk check |
| 2025-03 to 2025-06 (tariff V) | 10-month SMA (monthly) | S&P Composite (monthly averages) | −2.3% vs −0.1% | P2 desk check |
| 2026-07 (KRX crash: aggregate KOSPI market cap in the file 6,930 → 5,445 trillion KRW, −21.4%) | SMA200 | KRX proxy | −34.1% vs −23.2%. Long through −11.0% (7/28) and −6.0% (7/29); out for +18.4% (7/31); back in 8/3 | P2 desk check (marcap) |
| 2026-07 | 12-1 momentum | KRX top 500 | WML −27.2% (EW, gross). Winners (median past 12-1 return +200%) −26.8% vs losers −1.9% | P2 desk check (marcap) |
| 2016-2026 | Weekly 5-day reversal (unconditional; volume-filtered) | KRX top 500 | Gross 0.21% / −0.10% per week; net 35 bp −0.89% / −1.42% per week | P2 desk check |
| 2016-2026 | HYZ 10-day MA timing, high-volatility decile, one-day lag | KRX | 6.7%/yr gross (t 0.99); −6.7% net 35 bp | P2 desk check |
| Whole sample | Cost sensitivity of SMA20 (31 switches/yr) | SPY 1998-2021 | CAGR −0.26% at 5 bp; −13.3% at 50 bp (buy-and-hold 6.05%) | P2 desk check |

- **Context for the July 2026 KRX move, from the marcap file (not independently verified):**
  - Aggregate KOSPI market cap was 2,512 trillion KRW on 2025-06-30 and 6,930 trillion KRW on 2026-06-30 (+176% in 12 months).
  - Samsung Electronics closed at 59,800 → 334,000 → 262,500 KRW, and SK hynix at 292,000 → 2,650,000 → 1,718,000 KRW (2025-06-30 → 2026-06-30 → 2026-07-31).
  - On 2026-07-31 SK hynix rose +30.0% and Samsung +26.8%.

####### Inferences
- **Two distinct crash types matter for QUANTGEN:**
  - (a) Rebound crashes (KRX 1998-01, 2020-04; US 1932, 2009). Momentum and 52-week-high shorts squeeze when beaten-down stocks rally. The Daniel-Moskowitz bear-state gate in the macro research targets this type.
  - (b) A bubble-top crash in the winners themselves (KRX 2026-07). The market came from a strong bull state (+176% in 12 months), so a bear-state gate would likely not have fired. Only volatility scaling and concentration caps would have helped. The nearhigh-neutral construction would not obviously help either, because the winners were at their highs.
- **V-shaped crashes are the structural failure mode of every price-trend filter.** The rule exits after most of the fall and re-enters after most of the rebound. In 2020 (SPY) and 2026 (KRX) the trend filter did worse than buy-and-hold over the full episode.
- **Range-bound years (US 2011/2015/2018, KRX 2024-25) cost the SMA200 3-10 points per year vs buy-and-hold.** These are the "whipsaw tax" years. Over 2010-2019 the tax summed to about 6 points per year of CAGR on SPY.

####### Gaps
- KRX index-level episodes use a self-built value-weighted top-200 price-only proxy, not the official KOSPI 200 or KODEX 200 total-return series. Dividends (about 1.5-2%/yr) and the CD-rate cash return are omitted.
- The July-September 2026 marcap figures were not cross-checked against official KRX index data; they post-date P2's external sources.
- No academic source covering 2020-2026 technical-rule performance in Korea was found.

---


### [P2] Claims ledger (lines 489-524)

######## Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P2-C01 | Classic single-index MA/filter/breakout/OBV rules lose significance once the full rule universe is counted and the sample moves past 1986. | DJIA 1897-1986 best rules RC p 0.000 (IS, gross); 1987-1996 OOS best 14.41%/yr, Sharpe 0.87, nominal p 0.004 → RC p 0.341; S&P futures 1984-1996 nominal 0.042 → RC 0.908; break-even 0.27%/trade | [STW 1999](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf); [BLL 1992](https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html) | T1 | Replicated OOS: FJQ 1987-2011 null; BS 1897-2011 FDR null after costs | US after 1986 | DROP: no index MA/TRB alpha card |
| P2-C02 | Controlling false discoveries, even early-sample rule profits are wiped out by low costs and best rules cannot be picked ex ante. | DJIA 1897-2011, FDR portfolios: in-sample edge offset by low transaction costs; persistence tests fail | [BS 2012](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html) | T1 | FDR + persistence + costs | Whole sample | DROP; adopt FDR + persistence in the family gate |
| P2-C03 | The literature's positive results cluster in pre-1990 samples and in methodologically weak studies. | 95 studies (1988-2004): 56 positive / 20 negative / 19 mixed; profits in US stocks until late 1980s, FX until early 1990s, futures until mid-1980s; break-even 0.39%/transaction for BLL rules on dividend-adjusted DJIA | [Park & Irwin WP](https://www.kdajdqs.org/bbs/presentation/303/download/319); [record](https://experts.illinois.edu/en/publications/what-do-we-know-about-the-profitability-of-technical-analysis/) | T1 | Survey | Post-1990 | CONTEXT |
| P2-C04 | Across 49 markets in 2001-2007, no market (Korea included) has a significant rule after data-snooping adjustment. | 5,806 rules; Korea nominal p 0.298 → adjusted 0.942; Taiwan 0.076 → 0.748; gross | [MCC (mirror)](https://c.mql5.com/forextsd/forum/210/Technical%20Analysis%20Around%20the%20World.pdf); [SSRN](https://www.ssrn.com/abstract=1181367) | T1 (WP) | Reality Check; post-publication era | Korea, Taiwan 2001-2007 | DROP index rule-mining on KOSPI/KOSDAQ indices |
| P2-C05 | Where rules worked, it was in young, small or illiquid segments, and the edge faded with maturity and ETFs. | NASDAQ/Russell 2000 1990-2000 IS best 38.19%/47.10%/yr after 0.05% one-way (DJIA/S&P insignificant); stepwise SPA: edge weakens after ETF listings; tech/small caps significant 1995-2002, futile 2003-2010 | [Hsu & Kuan](https://homepage.ntu.edu.tw/~ckuan/pdf/snoop01.pdf); [HHK 2010](https://ideas.repec.org/a/eee/empfin/v17y2010i3p471-484.html); [Shynkevich](https://ideas.repec.org/a/eee/jbfina/v36y2012i1p193-208.html) | T1 | RC/SPA; OOS decay documented | 2003-2010; post-ETF | BACKLOG: KOSDAQ-segment families only, via the family gate; expect decay |
| P2-C06 | Rule profits in DJIA stocks were episodic and depended on short selling. | DJIA members 1928-2012: profits mainly mid-1960s to mid-1980s, reliant on shorts | [Taylor 2014](https://ideas.repec.org/a/eee/jbfina/v40y2014icp286-302.html) | T1 | Time-varying models | After mid-1980s | CONTEXT: a long-only read-only desk cannot harvest short-side profits |
| P2-C07 | Monthly technical indicators forecast the US equity premium out-of-sample and complement macro predictors. | S&P 500 OOS 1966-2011: R²OS 0.09-0.75% (14 indicators), PC-TECH 0.65%, PC-ALL 1.79%; CER gains 0.73-3.17%/yr (γ = 5), 0.40-2.82% after 50 bp; technicals catch declines near cycle peaks | [NRTZ WP](https://files.stlouisfed.org/files/htdocs/wp/2010/2010-008.pdf) | T1 | Recursive OOS; costs included; post-2011 unverified | Not reported | BACKLOG: risk-sizing input inside the macro overlay's [0.5, 1.0] band, never direction (consistent with the macro decision) |
| P2-C08 | Index MA timing mainly cuts drawdowns; return gains are inflated by look-ahead/data-mining bias and by averaged prices. | Faber S&P 500 1901-2012: 10.18% vs 9.32% CAGR, max DD 42.2% vs 83.7% (practitioner, mostly IS); Zakamulin: bias-corrected MA ≈ buy-and-hold, OOS with costs overstated; desk check: Shiller monthly-average returns lag-1 autocorrelation 0.274 vs SPY month-end 0.057; SMA10 1881-2023 9.35% (next month) vs 7.58% (skip month) vs buy-and-hold 9.16% | [Faber](https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf); [Zakamulin 2014](https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html); [Zakamulin 2018](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2743119); [Shiller data](http://www.econ.yale.edu/~shiller/data.htm); P2 desk check | T2 (Faber) / T1 / T3 (desk) | Practitioner claims not snooping-adjusted | 2010-2019: SMA10 (skip) 8.06% vs 13.31% | DROP as alpha card (E1 already REJECT); allow display-only drawdown context; data lab must use month-end prices |
| P2-C09 | Diversified time-series momentum earned large gross alphas in 1965-2009 futures and across 1880-2016. | 58 futures 1985-2009: alpha 1.58%/month (t 7.99), Sharpe > 1, gross, no costs; 67 markets 1880-2016: 18.0% gross, 11.0% net of costs, 7.3% net of 2/20, Sharpe 0.76; trend t ≈ 10 since 1800 | [MOP](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf); [HOP](https://static.twentyoverten.com/593e8a9e7299b471eaecf644/SkLoGL67M/A-Century-of-Evidence-on-Trend-Following-Investing.pdf); [Lempérière](https://arxiv.org/abs/1404.3274) | T1 / T2 | Pre-1985 back-extension is OOS in time; HOP models costs and fees | 2010s (P2-C10) | CONTEXT: B3 already REJECT; reset expectations |
| P2-C10 | Trend following's excess return collapsed toward zero after 2009. | Excess return 6.3%/yr (2000-09) → 0.4% (2010-18), net of costs; net-of-fee decades 8.3% / 6.3% / 3.3% (1990s / 2000s / 2010-16); short trends withered; QUANTGEN B3 OOS Sharpe 0.08 | [AQR 2019](https://www.belmontinvestments.com/cimg/file/articles/53/pdf/190425aqrtrendfollowing.pdf); [HOP](https://static.twentyoverten.com/593e8a9e7299b471eaecf644/SkLoGL67M/A-Century-of-Evidence-on-Trend-Following-Investing.pdf); context brief | T2 / internal | Post-publication (MOP 2012) | 2010-2018 | DROP futures TSMOM card; cut the prior "~1.0 diversified" expectation to 0.0-0.3 before haircut |
| P2-C11 | TSMOM's statistical evidence is weak once small-sample bias and volatility scaling are handled. | 55 assets 1985-2015: pooled t 4.34 < bootstrap critical 4.83 / 12.53; 8 of 55 significant; 3 with significant R²OS; TSM − TSH 0.14% (p 0.19); unscaled t 1.68; unscaled TSMOM ≈ buy-and-hold | [HLWZ](https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=7520&context=lkcsb_research); [KTW](https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html) | T1 | Bootstrap; asset by asset | n/a | Gate design: benchmark trend against vol-scaled buy-and-hold and the TSH sign rule |
| P2-C12 | Volatility-scaled crypto trend has independent academic support and is QUANTGEN's strongest technical card. | Strong crypto TSMOM and attention effects; P/MA ratios predict daily bitcoin returns IS and OOS; MA rules best on high-frequency bitcoin; QUANTGEN C3 KRW-BTC OOS 1.22 [0.62, 1.77] vs 0.79, p 0.04, 1.17 at 2x costs | [Liu-Tsyvinski](https://www.nber.org/papers/w24877); [Detzel](https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html); [Corbet](https://ideas.repec.org/a/eee/finlet/v31y2019icp32-37.html); context brief | T1 / internal | QUANTGEN OOS PASS; short history | Not documented | BUILD (keep C3); use P/MA-ratio neighbours in the plateau test; apply the 60% haircut |
| P2-C13 | Proximity to the 52-week high predicts US returns better than past returns and does not reverse, but international profits rarely survive costs. | US 1963-2001 (6,6): 0.45%/month all months, 1.23% ex-January (t 7.06), risk-adjusted 1.13% (t 11.35), IS gross; 20 markets: profitable in 18, significant in 10, mostly insignificant after costs | [George & Hwang](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf); [Liu-Liu-Ma](https://www.sciencedirect.com/science/article/abs/pii/S0261560610001099) | T1 | Replicated internationally; costs bind | January | BUILD as feature; card BACKLOG |
| P2-C14 | On KRX top-500 stocks the 52-week-high tilt is gross-positive in every decade but not significant net of 35 bp per side. | 1996-2026 monthly: L/S 0.66%/month gross (t 1.67), 0.25% net 35 (t 0.65); long-only vs universe 0.31% → 0.07%; 6-monthly rebalance L/S 5.73%/yr net 35 (gross t 1.37), long-only 1.34%/yr net 35 | P2 desk check (marcap) | T3 | Literature parameters; 4 variants tried; not snooping-adjusted | 1998-01 L/S −39.6%; 2020-04 −17.4% | BACKLOG card (long-only, 6-month rebalance); feature weight KRX 1, US 2 |
| P2-C15 | Neutralizing 52-week-high distance inside momentum removes most of momentum's crash risk. | US 1930-2022: WML* 1.37%/month vs WML 1.19%; Sharpe 0.276 vs 0.159 (monthly); skew +0.13 vs −1.89; max DD −23.7% vs −74.1% | [Jeon & Byun](https://epublications.marquette.edu/cgi/viewcontent.cgi?article=1168&context=fin_fac) | T1 | Single study; gross | Rebound crashes | BUILD-candidate construction rule for any momentum sleeve; test on KRX incl. 2026-07 |
| P2-C16 | MA-based cross-sectional trend signals have US support but are weak in KRX. | US: trend factor Sharpe > 2x STR/MOM/LTR, 2009 +0.75%/month vs MOM −3.88%; MAD VW alpha ~9%/yr after institutional costs; KRX desk check: MA21/MA200 L/S 0.51%/month gross (t 1.28), 0.15% net 35; P/SMA200 0.28% (t 0.69), −0.12% net 35 | [HZZ](https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html); [AKS](https://ideas.repec.org/a/wly/revfec/v39y2021i2p127-145.html); P2 desk check | T1 / T3 | US published; KRX not replicated | KRX 2006-2026 | BACKLOG feature (US weight 2, KRX 1) |
| P2-C17 | MA timing of high-volatility portfolios (HYZ) is large gross but lag- and cost-fragile in KRX. | US 1963-2009: MAP 5.17% → 18.55%/yr, alpha up to 21.38%, 15.8-18.0% after 25 bp; KRX 1996-2026 decile 10: 30.0%/yr gross (t 7.0), 18.0% net 35, 5.9% net 70; with one-day lag 18.0% gross, −6.0% net 70; 2016-26 with lag 6.7% gross (t 0.99) | [HYZ (mirror)](https://www.smallake.kr/wp-content/uploads/2016/03/49.pdf); [JFQA record](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/new-anomaly-the-crosssectional-profitability-of-technical-analysis/B9E41049F2E55B4F274D46E72ECA8E29); P2 desk check | T1 / T3 | Decays 45% → 31% → 15%/yr gross by decade in KRX | 2016-2026 | DROP stock-level card; optional BACKLOG ETF variant (e.g., a KOSDAQ 150 tracker at 3 bp) |
| P2-C18 | Short-term reversal is real gross but is a liquidity-provision return that retail costs cannot harvest. | US 1934-1987 decile spread 2.49%/month gross; weekly reversals (Lehmann); profits below likely costs (ACG); 30-50 bp/week net only in large caps with turnover control; VIX-predictable; tapered after 2011 | [Jegadeesh](https://ideas.repec.org/a/bla/jfinan/v45y1990i3p881-98.html); [Lehmann](https://www.nber.org/papers/w2533); [ACG](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html); [dGHZ](https://ideas.repec.org/a/eee/jbfina/v36y2012i2p371-382.html); [Nagel](https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html); [MS 2022](https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf) | T1 | Widely replicated; post-2011 decay | After 2011 | CONTEXT; feature only |
| P2-C19 | On KRX top-500 stocks, the weekly 5-day reversal, with or without the prior design's volume filter, is deeply negative net of 35 bp per side and has decayed gross. | 1996-2026 unconditional L/S 0.53%/week gross (t 6.47), decades 0.85 / 0.53 / 0.21; net 35 −0.59%/week (2016-26 −0.89); volume filter (> 1.5x): 0.44%/week gross, 2016-26 −0.10%, net 35 −0.88%/week; Σ|Δw| ≈ 3.2-3.8 per week | P2 desk check (marcap) | T3 | Literature design; one implementation; not snooping-adjusted | 2016-2026 gross ≈ 0 | DROP card; conflicts with the prior Korea ST-reversal weight 3 and the macro note's −2.95%/month (likely all-cap, gross) |
| P2-C20 | Volume's predictive sign depends on horizon and market; in KRX, high turnover predicts reversal, not short-term momentum. | US 1963-2018 VW: high-turnover winners continue +1.37%/month (t 4.74), 1.00% net; 22 developed markets +1.39%/month; weekly: high-transaction stocks reverse (CHN), falling-volume stocks reverse more (Cooper); KRX desk check 1996-2026: high-turnover WML −1.10%/month (t −2.24) gross | [MS 2022](https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf); [CHN](https://ideas.repec.org/a/bla/jfinan/v49y1994i4p1305-29.html); [Cooper](https://ideas.repec.org/a/oup/rfinst/v12y1999i4p901-35.html); [LMSW](https://ideas.repec.org/a/oup/rfinst/v15y2002i4p1005-1047.html); [GKM](https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html); P2 desk check | T1 / T3 | Mixed across studies | KRX contradicts MS | DROP short-term momentum for KRX; volume only as a conditioning feature inside a pre-registered family |
| P2-C21 | Chart patterns carry statistical information but have no demonstrated net trading profit. | NYSE/AMEX and Nasdaq stocks 1962-1996 (350 sampled): 7 of 10 / 10 of 10 patterns change conditional return distributions; no cost or profit test | [LMW](https://www.nber.org/system/files/working_papers/w7613/w7613.pdf) | T1 | Distributional only | n/a | DO-NOT-BUILD as trading cards |
| P2-C22 | A CNN reading chart images produces strong gross OOS sorts that concentrate in small caps and high turnover; there is no net-of-cost evidence. | US OOS 2001-2019: EW 1-month Sharpe 2.16-2.35 vs MOM 0.25, STR 0.55, WSTR 1.23; VW 0.45-0.49; turnover 155-187%/month; transfer to 26 markets Sharpe 0.7 | [JKX](https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf) | T1 | OOS; no costs | n/a | BACKLOG (research only); expect the same KRX cost failure as reversal |
| P2-C23 | Candlestick patterns do not predict returns in large US stocks; the one positive (Taiwan) is single-market. | 28 patterns on 35 DJIA stocks 1992-2002, EGARCH-null bootstrap: no predictability; Taiwan Top-50 2002-2008: three bullish reversal patterns profitable (costs unstated in abstract) | [MYR (mirror)](https://c.mql5.com/forextsd/forum/211/Market%20Timing%20with%20Candlestick%20Technical%20Analysis.pdf); [JBF record](https://ideas.repec.org/a/eee/jbfina/v30y2006i8p2303-2323.html); [Lu-Shiu-Liu](https://ideas.repec.org/a/wly/revfec/v21y2012i2p63-68.html) | T1 | Bootstrapped | US 1992-2002 | DO-NOT-BUILD |
| P2-C24 | Fibonacci retracements have no special support/resistance effect, and Elliott waves lack peer-reviewed tests. | DJ30, DAX30, NASDAQ-100 stocks 1968-2019: bounce probability at Fibonacci zones = non-Fibonacci zones; the rule trails buy-and-hold after risk; Elliott: only subjective, non-refereed work found | [TGV 2022](https://www.sciencedirect.com/science/article/abs/pii/S0957417421012495); [Chendroyaperumal (SSRN, metadata)](https://doi.org/10.2139/ssrn.1887789) | T1 / T3 | One rigorous study | All periods | DO-NOT-BUILD |
| P2-C25 | Published RSI/MACD tests show market-specific, non-robust effects without snooping control, and a 52-rule oscillator family on SPY fails the Reality Check. | 5 OECD indices 1976-2002: significant only in Italy and Canada, 1% round trip; ASX 1996-2014: MACD insignificant, RSI small, no costs; desk check SPY 1999-2021 at 5 bp: 5 of 52 beat buy-and-hold Sharpe; best nominal p 0.18 → RC p 0.92; 0 of 52 beat it in 2010-2021 | [Chong-Ng-Liew](https://mpra.ub.uni-muenchen.de/54149/1/MPRA_paper_54149.pdf); [MNW 2014](https://businessperspectives.org/images/pdf/applications/publishing/templates/article/assets/6228/imfi_en_2014_04cont_Nor.pdf); P2 desk check | T1 (lower-tier journals) / T3 | No published snooping control | 2010-2021 | DO-NOT-BUILD standalone oscillator cards; RSI/%B only as normalized reversal features |
| P2-C26 | Support/resistance levels and order clustering create small, real order-flow effects intraday. | FX intraday 1996-1998: bounce 60.8% at published levels vs 56.2% at arbitrary levels (+4.6 points; 13 of 16 significant); take-profits cluster at round numbers, stops just beyond | [Osler 2000](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf); [Osler 2003](https://ideas.repec.org/a/bla/jfinan/v58y2003i5p1791-1819.html) | T1 | No profitability test | n/a | BACKLOG intraday research (round-number features on KIS quotes); no daily card |
| P2-C27 | Technical-rule profitability rises and decays as the Adaptive Markets Hypothesis predicts: genuine early profits, decay after publication, slower decay for complex rules. | FX: Levich-Thomas portfolio 5.74% → −0.11%/yr, Sharpe 0.90 → −0.02 (1991-2005, net); breaks 1989-1993; simple FX rules ~8%/yr 1975-1990 → ~0 by the 1990s; conflicting: >21,000 rules on 30 currencies over 45 years still predictive under a stepwise test; anomaly returns halved after decimalization | [NWU](https://files.stlouisfed.org/files/htdocs/wp/2006/2006-046.pdf); [Neely-Weller 2011](https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf); [HTW 2016](https://ideas.repec.org/a/eee/inecon/v102y2016icp188-208.html); [CST 2014](https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html); [Lo 2004](https://web.mit.edu/Alo/www/Papers/JPM2004_Pub.pdf) | T1 | Multiple independent studies; one conflict | 1989-1993; 2001 | CONTEXT: rolling live-decay monitoring; V3 FX momentum REJECT stands; DROP FX technical cards |
| P2-C28 | With 100 trend rules on one index, the "best" rule's edge is a selection artifact. | SPY 1998-12-31 to 2021-03-31, SMA/TSMOM n = 5…250, 5 bp: best Sharpe 0.52 vs 0.37 (nominal p 0.17) → RC p 0.70; 0 of 100 beat buy-and-hold mean; IS winner +0.40 → OOS −0.22; 0 of 100 beat it in 2010-21; at 50 bp 0 of 100 beat it | P2 desk check; [HLZ](https://www.nber.org/papers/w20592) | T3 / T1 | Stationary bootstrap, B = 1,000 | 2010-2021 | Family-level SPA/RC + FDR on top of the gate; DSR trials = family size |
| P2-C29 | KRX index-level trend timing added value only in 1997-2005 and failed in the 2024-2026 episodes. | Value-weighted top-200 proxy, 3 bp: SMA50 Sharpe 1.05 vs 0.42 (1997-2005), 0.27 vs 0.26 (2006-15), 0.63 vs 0.63 (2016-26); SMA200 2016-26 CAGR 9.58% vs 13.10%; 2024-07 to 2025-04 −19.7% vs −9.2%; 2026-07 −34.1% vs −23.2% | P2 desk check; context brief (E1 KRX REJECT) | T3 / internal | Consistent with E1; lookbacks mixed (SMA120 2016-26 Sharpe 0.73 vs 0.63) | 2024-2026 | DROP KRX index trend card; display-only |
| P2-C30 | KRX 12-1 price momentum is weak, and its worst month was July 2026. | Top-500 EW 1996-2026: L/S 0.62%/month gross (t 1.82), 0.28% net 35 (t 0.83); 2026-07: winners (median past return +200%) −26.8% vs losers −1.9%, WML −27.2%; aggregate KOSPI market cap −21.4% in the month (marcap) | P2 desk check (marcap); context brief (Korea momentum weak) | T3 | 2026 data not cross-checked with official KRX | 2026-07, 2001-01, 1998-01 | CONTEXT: no KRX momentum card without nearhigh-neutral construction and volatility/concentration caps; test whether the bear gate would have fired |
| P2-C31 | Behavioural mechanisms (anchoring, disposition effect, slow diffusion) explain why a few price-state variables work, and disposition subsumes momentum. | Capital-gains overhang removes the predictive power of past returns (US cross-section); anchoring explains 52-week-high continuation without reversal; newswatcher/momentum-trader model; 692 fund managers mostly use technical analysis at horizons of weeks | [Grinblatt-Han](https://ideas.repec.org/a/eee/jfinec/v78y2005i2p311-339.html); [George-Hwang](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf); [Hong-Stein](https://ideas.repec.org/a/bla/jfinan/v54y1999i6p2143-2184.html); [Menkhoff](https://ideas.repec.org/a/eee/jbfina/v34y2010i11p2573-2586.html) | T1 | Theory + US evidence | Untested in KRX | BACKLOG feature: capital-gains overhang from KRX OHLCV (data-check DC-I) |


### [P2] Register, family gate, corrections, data checks (lines 598-706)

####### Inferences

######## BUILD / BACKLOG / DO-NOT-BUILD register (P2 recommendation)
| Construct | Verdict | Form | Market weights (0-3, technical lens) | One-line reason |
|---|---|---|---|---|
| Vol-scaled crypto trend (sign votes + P/MA with hysteresis) | BUILD (keep C3) | Card | Crypto 3 | Independent academic support plus a QUANTGEN OOS PASS |
| 52-week-high proximity | BUILD as feature; card BACKLOG | Feature in cross-sectional composite; long-only, 6-month-rebalance card for the gate | US 2, KRX 1, Europe/Japan 1 | Mechanism (anchoring), no reversal; costs bind outside the US |
| Nearhigh-neutral construction for momentum sleeves | BUILD-candidate | Construction rule | US 2, KRX 1 | Halves drawdown and fixes skew in US 1930-2022 |
| MA distance / trend factor (MA21/MA200, multi-horizon MAs) | BACKLOG | Feature | US 2, KRX 1 | US published support; KRX gross insignificant |
| Capital-gains overhang (turnover-weighted reference price) | BACKLOG | Feature | KRX 2 (to test), US 1 | Disposition effect; retail-heavy KRX is the natural test bed |
| Technical indicators as risk-sizing inputs (MA/momentum/OBV, NRTZ-style) | BACKLOG | Overlay input bounded to [0.5, 1.0] | All markets 1 | OOS equity-premium evidence; fits the macro rule "size only, never direction" |
| Intraday first/last half-hour momentum; round-number S/R features | BACKLOG | Intraday research card | KOSPI 200 futures/ETF 1 | Published evidence; costs 3-5 bp make it testable |
| CNN on chart images | BACKLOG (research) | Research only | 0 until net-of-cost evidence exists | Gross only; reversal-like and high turnover |
| Index MA/TSMOM timing on SPY/KOSPI | DROP as alpha (display-only drawdown context) | — | US 1, KRX 1 (display) | E1 REJECT; DC1 and DC7 show no post-2006 edge |
| Futures/FX TSMOM, FX technical rules | DROP (keep REJECT) | — | Futures 1, FX 0 | B3 0.08, V3 −0.59; AQR 2010-18 excess 0.4% |
| KRX volume-filtered 5-day reversal (prior design) | DO-NOT-BUILD | — | KRX ST-rev 3 → 1 (feature) | −0.88%/week net at 35 bp; gross −0.10%/week in 2016-26 |
| KRX short-term momentum (high-turnover winners) | DO-NOT-BUILD | — | 0 | Reverses in KRX (−1.10%/month gross) |
| HYZ stock-level MA timing in KRX | DO-NOT-BUILD | — | 0 | Lag- and cost-fragile; −6.7%/yr net in 2016-26 with one-day lag |
| Standalone RSI / MACD / stochastics / Williams %R / Bollinger / ADX / Ichimoku | DO-NOT-BUILD | (RSI/%B allowed only as normalized reversal features) | 0 | RC p 0.92 on SPY; published positives are snooped single-market results |
| Candlesticks | DO-NOT-BUILD | — | 0 | Null in DJIA stocks 1992-2002 |
| Chart patterns (H&S, double tops etc.) | DO-NOT-BUILD | — | 0 | Distributional effects only; no net profit evidence |
| Fibonacci retracements; Elliott waves | DO-NOT-BUILD | — | 0 | Fibonacci = random levels; Elliott unfalsifiable |

######## How to test a family of technical rules without data snooping (proposed "family gate", run before the nine-step gate)
- **F0. Pre-register.** Fix the full family F before any data is touched:
  - rule definitions × parameter grid × universes, and K = |F|;
  - the benchmark: same-day buy-and-hold for timing rules, vol-matched buy-and-hold for trend rules, the equal-weighted universe for cross-sectional rules;
  - the cost model: QUANTGEN rates at 1x and 2x;
  - the criterion: mean net excess return, with Sharpe difference as secondary;
  - the split: purged walk-forward 756/126, embargo = holding period.
- **F1. Family-level null.**
  - Compute the out-of-sample walk-forward net excess-return series for all K rules.
  - Test "no rule beats the benchmark" with a studentized SPA-type test and White's RC, using a stationary bootstrap (mean block 10 sessions, B = 2,000).
  - The family passes only if SPA p ≤ 0.10 at 1x costs. Otherwise the whole family is REJECTED and no member may be carried forward. This stops the "best of K" from entering the gate.
- **F2. Identification.**
  - If F1 passes, list individually significant rules with a stepwise SPA (or Romano-Wolf) test at FWER 10%.
  - If several rules will be combined into a portfolio, control the false discovery rate at 10% as in Bajgrowicz-Scaillet.
- **F3. Persistence.** Rules selected in each in-sample window must have positive OOS net excess in at least 60% of walk-forward windows, with positive Spearman correlation of in-sample and OOS ranks. In DC1 the correlation was only 0.19 and the winner flipped sign.
- **F4. Trial accounting.** Survivors enter the nine-step gate with deflated-Sharpe trials = K plus all earlier trials on the same data. For example, E1, E5 and B3 count toward any new trend family, and every oscillator variant counts toward an oscillator family.
- **F5. Plateau.** The family structure supplies the neighbour set for step 7 directly: at least 50% of parameter neighbours must keep half the Sharpe.
- **F6. Hurdles.**
  - New cross-sectional technical factors need full-sample t ≥ 3.0 gross and t ≥ 2.0 net at 1x costs.
  - The last decade (2016-2026) must be net-positive at 1x costs.
  - Report subperiods 1996-2005, 2006-2015 and 2016-2026.
- **F7. Data hygiene.**
  - Month-end prices only, never monthly averages.
  - Decide at close t, trade at t+1, plus a t+2 robustness run (DC6 shows how much is lost).
  - Zero-pad KRX codes and include KOSDAQ GLOBAL.
  - No fills on zero-volume days.
  - Long-only versions are primary, because a read-only retail desk cannot short reliably.

######## Corrections to the prior design ("QUANTGEN Signal & Macro Map", 1 Oct 2026) and flags vs the macro research
- **Time-series trend.** "0.4-0.8 per asset, ~1.0 diversified" are pre-2009 gross figures (MOP, HOP). Expect 0.0-0.3 diversified after 2009 before the 60% haircut (AQR 2019; QUANTGEN B3 0.08). Lower the US/EM TS-mom weight from 3 to 1 for index timing and keep crypto at 3.
- **Volatility-scaling uplift.** HLWZ and KTW indicate that most TSMOM alpha *is* volatility scaling. This agrees with the macro research's correction that vol scaling is robust mainly for momentum. Trend cards must beat vol-scaled buy-and-hold.
- **Short-term reversal with volume filter.** Replace "0.5-1.0 gross, costs take half or more" with this for KRX at 35 bp per side: costs take *more than all* (gross Sharpe 1.20 → net −1.35, weekly, 1996-2026). Lower the Korea ST-reversal weight from 3 to 1, as a feature only.
- **Conflict with the macro note's Korean 1-month reversal.** The macro note's −2.95%/month (t −3.77, 1999-2021) is not reproduced in KRX top-500 stocks: 1-month reversal there is +0.41%/month gross (t 1.20) over 1996-2026 and about zero after 2006. The effect likely sits in small, illiquid names where it is least harvestable.
- **Momentum crash control.** The macro research's Daniel-Moskowitz bear gate addresses rebound crashes. The July 2026 KRX momentum crash came from a bull state, so P2 asks the data lab to test whether the gate would have reduced exposure (data check DC-J). P2 expects it would not, and recommends that the nearhigh-neutral construction and the existing Samsung/SK hynix concentration caps be evaluated together.
- **Reversal sizing.** Keep the macro research's rule that reversal sleeves are never up-weighted in stress, despite Nagel's VIX result.

######## Data-check requests for the data lab (exact tests)
- **DC-A, KRX 52-week-high long-only card.**
  - Universe: KOSPI + KOSDAQ + KOSDAQ GLOBAL common shares (codes zero-padded, SPACs excluded), top 500 by market cap at formation, price ≥ 1,000 KRW, at least 200 valid sessions in the prior 252.
  - Signal: P / max(P over 252 sessions) on a ChangesRatio-compounded index.
  - Portfolio: top 30% equal-weighted vs the equal-weighted universe, rebalanced every 1, 3 and 6 months (K = 3 variants, all counted). Decide at the formation-day close; trade t+1.
  - Costs: 35/70 bp per side.
  - Run the full nine-step gate and report 1996-2005 / 2006-2015 / 2016-2026 and 2026-07 separately.
  - P2 desk-check expectation: long-only 6-month 1.34%/yr net at 35 bp, gross t ≈ 1.0, i.e. REJECT or REVISE.
- **DC-B, KRX short-term reversal family with RC/SPA.**
  - 5-day-return quintiles × volume filter {none, 5d/20d > 1.5, < 1.0} × holding {5, 10, 20} sessions × universe {top 200, top 500, all with price ≥ 1,000} = 27 rules.
  - Long-only (losers vs equal-weighted universe) and L/S versions. Net 35 bp per side.
  - White RC + Hansen SPA, stationary bootstrap (block 10, B 2,000).
  - Expectation: the family fails (desk check: −0.59%/week net L/S at top 500).
- **DC-C, KRX Medhat-Schmeling double sort.**
  - Prior-month return × prior-month turnover (21-day sum of Amount/Marcap); KOSPI breakpoints; value-weighted and equal-weighted; 1996-2026.
  - Confirm that high-turnover winners reverse in KRX (desk check: WML −1.10%/month gross, t −2.24, equal-weighted top 1,500).
- **DC-D, HYZ tradability check on KRX.**
  - Equal-weighted volatility deciles (June re-sort), 10-day MA timing.
  - Run with (i) t+1-close execution, (ii) t+2 execution, (iii) excluding stocks with zero volume on day t.
  - 35 bp per stock-level switch.
  - Repeat on a tradable KOSDAQ 150 tracker series at 3 bp.
  - Desk-check expectation: 2016-2026 net negative with the lag.
- **DC-E, Shiller averaging trap.**
  - Faber 10-month SMA on (a) Shiller monthly averages as delivered and (b) with a one-month skip; report lag-1 autocorrelation.
  - Cross-check on SPY month-end 1998-2021.
  - Desk check: 9.35% vs 7.58% CAGR (1881-2023, total return, cash 0); autocorrelation 0.274 vs 0.057.
- **DC-F, SPY and KODEX 200 trend family RC.**
  - SMA(n) ∪ TSMOM(n), n = 5, 10, …, 250, long/flat; 5 bp (SPY) / 3 bp (KODEX 200) and 2x; criterion Sharpe difference vs same-day buy-and-hold.
  - Also benchmark against vol-scaled buy-and-hold.
  - Desk check SPY: RC p 0.696 at 5 bp.
- **DC-G, Oscillator family RC on SPY and KODEX 200.** Repeat the 52-rule family listed in Q2. Desk check SPY: RC p 0.92.
- **DC-H, VIX-conditioned reversal.** KRX weekly reversal gross returns sorted by lagged VIX (or VKOSPI if available) terciles, 1996-2026. Purpose: confirm Nagel's liquidity-provision pattern in KRX before anyone proposes stress-timed reversal.
- **DC-I, Capital-gains overhang on KRX.**
  - Grinblatt-Han reference price: the turnover-weighted average of past prices, with daily turnover = Volume / shares outstanding (Stocks).
  - Overhang = (P − RP) / P.
  - Monthly top-500 deciles, equal- and value-weighted; horse race against 12-1 momentum and 52-week high; costs 35/70 bp.
- **DC-J, July 2026 crash anatomy.**
  - Compute daily for June-August 2026: (a) the macro research's momentum overlay (σ126, 12% target, Daniel-Moskowitz bear-state floor 0.5); (b) a nearhigh-neutral WML*; (c) the Samsung/SK hynix concentration caps.
  - Report which, if any, would have cut KRX momentum exposure before 2026-07-01.
  - Cross-check the marcap July 2026 moves against official KOSPI/KOSPI 200 index levels.

####### Gaps
- The proposed family gate thresholds (SPA p ≤ 0.10; 60% persistence; t ≥ 3.0) are P2's design choices. They come from the cited literature's conventions but have not been tested on QUANTGEN's 34-card record.
- No net-of-cost study of 52-week-high or MAD signals specific to Korea was found. P2's KRX numbers are unreviewed desk checks with literature parameters; the data lab should re-run them under the gate (DC-A, DC-I).
- **Access limits this session:**
  - Web search budget exhausted (200-call session cap).
  - Semantic Scholar and some Crossref API calls rate-limited (429).
  - IDEAS/EconPapers search pages blocked by robots.txt.
  - Direct PDF downloads blocked by egress policy (403 CONNECT).
  - Several papers were therefore cited from abstracts or bibliographic records only (see Gaps under Q1-Q3).


---

## P3_fundamental_accounting_anomalies.md

### [P3] Persona, position summary, proposed weights (lines 5-42)

###### 0. Persona, position summary and proposed changes to the prior map

####### Takeaway
**Persona.** P3 is a *fictional composite* "Professor of Accounting and Valuation" (not a real person): teaches financial statement analysis and valuation, has worked with NYU-Stern-style valuation curricula (intrinsic value, implied equity risk premium), and argues from the lens that *accounting measurement and point-in-time (PIT) data decide whether a fundamental signal is real*.

**Position summary.** (1) Accounting signals are real but small after costs and publication: in the US, only slow composites (value + profitability, investment, net issuance) keep net premia at a 50 bp per side cost; accruals, a standalone Piotroski F-score, PEAD, analyst revisions, buyback drift and distress long-shorts do not. (2) Value's 2007-2020 failure was mostly valuation compression plus mis-measured book value (intangibles), not dead fundamentals, so QUANTGEN should fix measurement (timely price, intangibles-adjusted book) and pair value with profitability instead of buying raw low P/B. (3) US PEAD has been gone for non-microcap stocks since about 2006; the prior map's US "earnings drift 2" should become 0, and Korea's "earnings drift 3" has no Korean evidence behind it that I could open, so it should be 1 until a DART-timestamped test runs. (4) CAPE is a 10-year expected-return *context*, not a timing signal; at 1-year horizons it fails out of sample (locally, OOS R² −11% since 1990 and −39% for 2010-2022), and the Fed model should not be built. (5) In Korea the binding constraint is PIT data (OpenDART statements start in 2015; filing receipts carry a date but no time), so the first Korean fundamental card should be **net share issuance**, which needs only KRX listed-share counts; my local test shows it survives 35 bp per side over 1996-2026 (long-only active IR 0.84, 90% CI 0.46-1.25) but has decayed (IR 0.42 since 2017, CI −0.28 to 0.95). (6) Realistic expectation for a US value-quality composite: net L/S Sharpe ≈ 0.3-0.4 at 50 bp per side after decay haircuts, ≈ 0.15 after QUANTGEN's 60% live haircut; long-only tilts keep roughly 60% of value profits.

####### Cited Findings
- Across 97 published predictors, returns were 26% lower out of sample and 58% lower after publication (US) — [McLean & Pontiff 2016, JF (copy)](https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf).
- Strategies with one-sided monthly turnover below 50% generally keep significant net spreads; a buy/hold spread is the single most effective cost mitigation — [Novy-Marx & Velikov, NBER w20721](https://www.nber.org/papers/w20721).
- Value + profitability ("ValProf") earned 0.82%/month gross and 0.77% net (t 4.82), US 1963-2012, IS — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- PEAD has not existed for non-microcap US stocks since 2006 (since 2016 for microcaps) — [Martineau, SSRN 3111607](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607).
- OpenDART's full-statement API covers 2015 onward; the disclosure list returns `rcept_dt` as YYYYMMDD only — [OpenDART fnlttSinglAcntAll](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020); [OpenDART list API](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001).
- Long positions supply about 60% of value profits and half of momentum profits (US and international) — [Israel & Moskowitz 2013 (AQR page)](https://www.aqr.com/Insights/Research/Journal-Article/The-Role-of-Shorting-Firm-Size-and-Time-on-Market-Anomalies).
- Local Korea issuance and CAPE results: see §5 and §6 (Local, `marcap` and Shiller files).

####### Inferences
Proposed changes to the prior per-market weights (0-3 scale; every change is a prior only and must pass the gate):

| Market / family | Prior | P3 proposal | Reason (detail in sections) |
|---|---|---|---|
| US value | 1 | 1, but only inside a value+profitability composite; standalone HML-style 0 | §1, §2, §8 |
| US quality | 3 | 2 (as composite component; long-only quality ETF lagged 2021-26) | §2 |
| US earnings drift | 2 | **0** | §4 (dead for non-microcaps since 2006; negative after costs) |
| US issuance/investment (new) | — | 2 as composite components | §5 |
| Korea value | 2 | 2, pending PIT test; split sample at Feb-2024 (Value-Up) | §1, §7 |
| Korea quality | 1 | 2 (F-score and gross profitability work in emerging-market samples) | §2 |
| Korea earnings drift | 3 | **1** until a DART-timestamped test passes | §4 |
| Korea net issuance (new) | — | 2 (local evidence, decaying) | §5 |
| Japan quality | 2 | 1-2 (FF 2017: little profitability/investment effect in Japan; F-score works in Asia-Pacific) | §2 |
| Market-level valuation (CAPE, Fed model) | n/a | CONTEXT only; no multiplier | §6 |

Conflicts with the companion macro research: none that require re-litigation. CAPE as context (not a multiplier) and quality held at 1.0× are consistent with its rules. One clarification: AQR's summary of Ilmanen et al. (2021) reports an average **30%** out-of-sample drop across factors, while the macro research adopted factor-specific values (value −49%, momentum −23%); both can hold (average vs per-factor), and I did not re-verify the per-factor numbers — [AQR summary](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence).

####### Gaps
- No Korean academic paper on value, quality, F-score or PEAD could be opened in this session (web-search budget exhausted; KRX/FnGuide/KCI blocked), so Korean priors other than issuance rest on international and emerging-market samples.
- French factor returns after 2018 (HML, RMW, CMA through Aug-2026) could not be downloaded; 2021-2026 value/quality behaviour relies on iShares style-ETF returns.


### [P3] Local Korean issuance test (section 5) (lines 155-205)

###### 5. Investment and financing: asset growth, issuance, buybacks, distress (with a local Korean issuance test)

####### Takeaway
Investment (asset growth) and net share issuance are robust worldwide and low-turnover enough to survive costs in composites. Buyback drift died in the US for 2003-2012 events, and the distress anomaly is real but too costly to harvest as a long-short. My local Korean test supports **net issuance** as the first Korean fundamental card: strong in 1996-2026, surviving 35 bp per side, but clearly decaying and concentrated in smaller and KOSDAQ names.

####### Cited Findings
- **Asset growth.** Annual asset growth strongly predicts lower future returns, holds among large caps and beats B/M, size, past returns and accruals (US) — [Cooper, Gulen & Schill 2008, JF (RePEc)](https://ideas.repec.org/a/bla/jfinan/v63y2008i4p1609-1651.html). OSAP's replication: decile spread 1.73%/month EW (t 8.45), 1968-2003; value-weighted t ≈ 5 — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- Net of costs, US 1963-2012: asset growth 0.37% gross, 0.26% net (t 1.75); investment 0.56% gross, 0.46% net (t 3.60) — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf). Titman-Wei-Xie investment (capex-to-revenue): 0.168%/month VW quintile (t 2.86), 1973-1996 — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- Internationally, high-asset-growth firms earn lower returns; the effect is stronger in developed, more efficient markets and looks like an optimal-investment (q-theory) effect rather than mispricing — [Watanabe, Xu, Yao & Yu 2013, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v108y2013i2p529-563.html).
- **Issuance.** After 1970, share issuance predicts returns more significantly than size, B/M or momentum individually; before 1970 it shows no significant predictive power — [Pontiff & Woodgate 2008, JF (RePEc)](https://ideas.repec.org/a/bla/jfinan/v63y2008i2p921-945.html). OSAP: 1-year issuance (shares t−18 to t−6) t = 7.08 (1970-2003); Daniel-Titman composite issuance t = 4.39 (1968-2003) — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- In 41 countries, issuance predictability is stronger than size or momentum and comparable to B/M; it is driven mainly by low returns after share creation and is stronger where issuing and repurchasing are easier — [McLean, Pontiff & Watanabe 2009, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v94y2009i1p1-17.html). Composite equity issuance is among the robust predictors in 28 emerging markets — [Hanauer & Lauterbach 2019](https://ideas.repec.org/a/eee/ememar/v38y2019icp265-286.html).
- Net of costs, US: net issuance 0.57% gross, 14.36% one-sided turnover (monthly rebalancing), 0.37% net (t 2.43) — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- **Buybacks.** After open-market repurchase announcements (1980-1990) the average 4-year abnormal buy-and-hold return was 12.1%, and 45.3% for value stocks — [Ikenberry, Lakonishok & Vermaelen 1995, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v39y1995i2-3p181-208.html). Long-run abnormal returns after both repurchases and SEOs disappear for events in 2003-2012 — [Fu & Huang 2016, Management Science (RePEc)](https://ideas.repec.org/a/inm/ormnsc/v62y2016i4p964-984.html).
- **Distress.** Since 1981, financially distressed US stocks have delivered anomalously low returns despite higher volatility, beta and value/size loadings, contrary to the idea that value and size premia compensate for distress risk (1963-2003) — [Campbell, Hilscher & Szilagyi, NBER w12362](https://www.nber.org/papers/w12362). OSAP labels the CHS failure-probability VW quintile spread (0.525%/month, t 1.41, 1981-2003) and Altman Z (t 1.59) as placebos; Dichev's O-score spread is t 3.36 (1981-1995) — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv). Net of costs: failure probability 0.85% gross, 26.10% turnover, **0.24% net (t 0.73)** — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- **Local test: Korean net share issuance (Local, IS, gross and net, unreviewed).**
  - Design: KOSPI + KOSDAQ common shares from `marcap`, 1996-05 to 2026-08 formation (352 months). Exclusions: names containing 스팩/리츠/인프라, price < ₩1,000, and the bottom 30% by market cap each month. Listed shares are adjusted for splits and stock dividends (detected where the close-to-close ratio departs from KRX's reported change); stock-months with such events in months t..t−2 or t−11..t−13 are dropped. Signal: ISS = log(adjusted shares_t / adjusted shares_t−12). Rebalanced monthly at the month-end close; costs charged on all one-way traded weight, including drift.
  - **L/S, non-issuers (ISS ≤ 0.5%) minus top-quintile issuers.**
    - EW: 14.1%/yr gross, Sharpe 1.31 (t 7.09). Net 35 bp per side: 11.3%/yr, Sharpe 1.04. Net 70 bp: Sharpe 0.78. Average traded weight 0.68 per month across both legs.
    - VW: 8.0%/yr gross, Sharpe 0.47 (t 2.55). Net 35 bp: Sharpe 0.34. Net 70 bp: Sharpe 0.21.
  - **Long-only active, EW non-issuers minus EW universe.** 3.2%/yr gross, IR 1.22, 90% block-bootstrap CI [0.88, 1.60] (2,000 × 10-month blocks, seed 11).
    - Net 35 bp: 2.2%/yr, IR 0.84, CI [0.46, 1.25], 68% of years positive.
    - Net 70 bp: IR 0.46, CI [0.07, 0.89].
    - 2017-2026, net 35 bp: IR 0.42, CI [−0.28, 0.95], 60% of years positive.
    - 2017-2026, net 70 bp: IR 0.06.
    - Long-leg traded weight: 0.23 per month.
    - VW long-only active: IR 0.10 gross, about 0 net.
  - **Decay.** EW L/S gross Sharpe 1.78 (1997-2007), 1.37 (2008-2016), 0.79 (2017-2026). VW L/S gross Sharpe 0.66, 0.49, 0.39 over the same periods.
  - **Robustness.**
    - Skipping one month: Sharpe 1.55. 24-month horizon: 1.47. 36-month horizon: 1.18.
    - Top 200 caps: EW L/S 6.9%/yr, Sharpe 0.53 (t 2.89); VW L/S 6.1%/yr, Sharpe 0.33 (t 1.80).
    - KOSPI: EW Sharpe 0.68, VW 0.32. KOSDAQ: EW Sharpe 1.20, VW 0.47.
    - EW L/S beta to the cap-weighted universe: −0.11. Maximum drawdown: −17% (trough Mar-2018).
  - **Monotonic buckets (EW annual mean returns).** ISS < −0.5%: 8.0%. About 0: 10.0%. 0.5-5%: 4.1%. 5-20%: −0.4%. Above 20%: −12.0%.
  - **Exclusion screen (drop ISS > 5%) vs universe.** EW +2.7%/yr (IR 1.30). VW +0.4%/yr (IR 0.08).
  - **Share-count decreasers (cancellations).**
    - Full sample: not significant (EW +1.3%/yr, t 0.61; VW +2.7%, t 0.88).
    - 2014-2023: EW −0.6%/yr; VW +9.6%/yr (t 2.03), about 22 names a month.
    - 2024-2026: EW +10.0%/yr (t 2.37); VW +20.6%/yr (t 2.07), about 133 names a month, over only 32 months.

####### Inferences
- Issuance is the Korean signal with the best evidence-to-data ratio. It needs only daily listed shares, which are PIT by construction because KRX publishes them daily, so it can be backtested on 30 years of survivorship-free data without OpenDART. The effect is economically large in EW and in KOSDAQ, weaker in VW and large caps, and decaying; the recent-decade CI includes zero at 35 bp.
- QUANTGEN translation: a **long-only "avoid heavy issuers" tilt/exclusion** (card KR-ISS). This fits a read-only individual-investor desk better than a short leg. Shorting heavy issuers (often distressed KOSDAQ names issuing convertible bonds) is impractical for retail investors and is where delisting and borrow problems concentrate.
- Caveats on the local test: (a) rights offerings with ex-rights price adjustment (권리락) are partly treated as splits or excluded by the event filter, so issuance is *understated*. The signal mostly captures CB/BW conversions, third-party allotments, stock options and mergers. (b) Delisting returns may be incomplete if 정리매매 prices are missing. (c) About 10 variants were examined, so a deflated Sharpe must count them. (d) Not walk-forward.
- Buyback/cancellation (BL-O04 in the macro backlog): the local result is regime-specific. It was weak for 1996-2023 and strong in 2024-26, which coincides with Value-Up (Feb-2024) and the 2025 Commercial Act revisions (KEIA). Keep it in BACKLOG as a regime-flagged candidate; 32 months is not enough.
- Asset growth and investment belong in the US composite (CMA-like, low turnover), not as standalone cards. Distress (failure probability, O-score) belongs in long-book exclusion screens, not as a return card.

####### Gaps
- The Cooper-Gulen-Schill magnitudes come from OSAP's replication notes, not the paper's tables. Titman-Wei-Xie's abstract was not fetched.
- The local Korean test has not been reproduced by the data lab and does not yet use DART-based issuance events (rights offerings, CB conversions) to classify issuance types.
- Korean distress models (O-score/CHS on OpenDART) are untested.


### [P3] QUANTGEN translation (section 8) (lines 300-357)

###### 8. QUANTGEN translation: which fundamental cards, rebalancing, combination with momentum, expected net Sharpe

####### Takeaway
Build two fundamental cards now: **KR-ISS** (Korean net-issuance long-only tilt, buildable today from KRX data) and **US-VQ** (a value + profitability + investment + issuance composite on EDGAR PIT data), both rebalanced monthly with buy/hold bands. Put the Korean value-quality composite, Korean PEAD and the buyback/cancellation signal in BACKLOG behind a PIT store. Drop US PEAD, analyst signals, standalone F-score, distress long-shorts and every market-valuation timing rule. Realistic net Sharpe after decay haircuts and QUANTGEN costs is about 0.15-0.4 for the survivors, and roughly 0.1-0.2 after the gate's 60% live haircut.

####### Cited Findings
- The average anomaly's expected return is about 8 bp/month after spreads, post-publication decay and modern trading technology; the best are 10-20 bp after data-mining adjustments — [Chen & Velikov (SSRN 3073681)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681). Anomaly returns roughly halved after decimalisation — [Chordia, Subrahmanyam & Tong 2014, JAE (RePEc)](https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html). With NYSE breakpoints and VW returns, 64% of 447 anomalies are insignificant at 5% (85% at t ≥ 3) — [Hou, Xue & Zhang, NBER w23394](https://www.nber.org/papers/w23394). Most accounting anomalies look spurious in pre-1963 data — [Linnainmaa & Roberts (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2897719).
- Counter-evidence: most factors replicate, cluster into 13 themes and work out of sample in 93 countries — [Jensen, Kelly & Pedersen, NBER w28432](https://www.nber.org/papers/w28432); [JKP data, through Dec-2025](https://jkpfactors.com/). Reliable post-publication decline across 241 anomalies in 39 markets appears only in the US — [Jacobs & Müller 2020, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html).
- Factor timing: timing strategies lose their profitability once proper data lags and transaction costs are applied — [Ilmanen, Israel, Lee, Moskowitz & Thapar 2021 (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence).
- **Value + momentum.** Global individual stocks (US, UK, Europe, Japan; 1972/74-2011): Sharpe 0.51 (value), 0.59 (momentum), 1.28 (50/50). All asset classes: 0.72, 0.74, 1.59. Within-asset-class value-momentum correlation about −0.49 to −0.60 (IS). Book-to-market uses 6-month-lagged book and current price — [Asness, Moskowitz & Pedersen 2013, JF](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf). Net of costs, US 1963-2012: ValMom 0.93% gross, 0.51% net (t 2.67); ValMomProf 1.43% gross, 0.99% net (t 5.18), one-sided turnover about 27-29%/month — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- QUANTGEN's own context: US 12-1 momentum Sharpe 0.02 since 2008 (French WML); French value-momentum correlation −0.17 vs AMP's −0.65 over the same window; Korean 12-1 momentum negative (QUANTGEN context brief; QUANTGEN_MACRO_INTEGRATION.md §2.2).
- Costs: below 50% one-sided monthly turnover most anomalies keep significant net spreads; a buy/hold spread is the most effective simple mitigation — [Novy-Marx & Velikov, NBER w20721](https://www.nber.org/papers/w20721).

####### Inferences
**Expected net Sharpe (P3 computation; inputs: Novy-Marx-Velikov US 1963-2012 gross returns, turnover and net t-statistics; cost = 4 × one-sided turnover × QUANTGEN's 50 bp per side; decay haircut h).** The cost formula reproduces Novy-Marx-Velikov's own cost estimates within about 10% (value 0.70 vs 0.60%/yr; momentum 8.3 vs 7.8%/yr). h = 0.49 for value (macro research), 0.50 for other single anomalies (McLean-Pontiff 58% post-publication, rounded), 0.35 for multi-signal composites (assumption between Ilmanen's −18% for multifactor and McLean-Pontiff), and 0.75 for PEAD (Martineau: zero for non-microcaps).

| Signal (US L/S) | Gross Sharpe (IS) | Vol %/yr | Cost %/yr at 50 bp | h | Exp. net Sharpe 1× | at 2× cost | After 60% live haircut |
|---|---|---|---|---|---|---|---|
| Value | 0.38 | 14.8 | 0.70 | 0.49 | 0.15 | 0.10 | 0.06 |
| Gross profitability | 0.42 | 11.4 | 0.47 | 0.50 | 0.17 | 0.13 | 0.07 |
| **Value + profitability** | 0.73 | 13.5 | 0.71 | 0.35 | **0.42** | **0.37** | **0.17** |
| Investment | 0.62 | 10.8 | 1.54 | 0.50 | 0.17 | 0.03 | 0.07 |
| Asset growth | 0.35 | 12.5 | 1.53 | 0.50 | 0.06 | −0.07 | 0.02 |
| Accruals | 0.30 | 10.6 | 1.38 | 0.50 | 0.02 | −0.11 | 0.01 |
| Piotroski F-score | 0.16 | 15.1 | 1.74 | 0.50 | −0.04 | −0.15 | <0 |
| Net issuance (monthly) | 0.53 | 12.9 | 3.45 | 0.50 | 0.00 | −0.27 | 0 |
| Failure probability | 0.41 | 24.8 | 6.26 | 0.50 | −0.05 | −0.30 | <0 |
| Value+mom+prof | 1.06 | 16.1 | 6.43 | 0.35 | 0.29 | −0.11 | 0.12 |
| Momentum (raw, for reference) | 0.68 | 23.4 | 8.28 | 0.50 | −0.01 | −0.37 | <0 |
| PEAD (SUE) | 0.70 | 12.3 | 8.42 | 0.75 | −0.51 | −1.20 | <0 |

The US issuance row is monthly-rebalanced; with annual or band-based rebalancing its cost falls by about two-thirds. Korean issuance local result (long-only active, EW, 35 bp): IR 0.84 full sample, 0.42 for 2017-26; after the 60% live haircut about 0.17-0.34.

**Card proposals.**

| Card | Market | Status | Construction | Rebalance | Gate expectation |
|---|---|---|---|---|---|
| **KR-ISS** | Korea | BUILD-candidate | Long-only: exclude or underweight stocks with 12-month split-adjusted share growth > 5% (or the top quintile); EW within capped universe (bottom-30% cap and < ₩1,000 excluded; R-07 caps) | Monthly at close t, trade t+1; hold band (re-admit only below 0.5% issuance) | Net 35 bp IR ≈ 0.4-0.8; recent CI includes 0, so REVISE/INSUFFICIENT is plausible; 2× cost Sharpe positive full-sample, ≈ 0 recent |
| **US-VQ** | US | BUILD-candidate | Rank composite: timely B/M with capitalised R&D, E/P, CF/P, GP/A, operating profitability, −asset growth, −net issuance, −accruals (small weight), with an M-score/distress exclusion; top 1,000 caps; sector-neutral; long-only tilt vs IWB-like benchmark plus L/S research twin | Monthly signal refresh as filings arrive (EDGAR acceptance + 1 session); buy/hold band (enter top 20%, exit below top 40%) | L/S net ≈ 0.3-0.4 at 50 bp; long-only active IR ≈ 0.15-0.25; needs ≥ 15 years of XBRL data, so expect REVISE before PASS |
| KR-VQ | Korea | BACKLOG (needs PIT store) | PBR (timely price; BPS from first-filed OpenDART), profitability (where COGS exists), F-score, issuance; split at Feb-2024 | Monthly with bands | Only 11 years of OpenDART history, so INSUFFICIENT DATA likely until pre-2015 PIT book is validated |
| KR-PEAD (CAR3) | Korea | BACKLOG | DART 잠정실적 timestamps; enter at rcept_dt + 1 close; hold 60 sessions; size terciles | Event-driven | Unknown; must clear 35/70 bp |
| KR buyback/cancel | Korea | BACKLOG (BL-O04 update) | Share-count decreasers; regime flag post-Feb-2024 | Monthly | 32 months of evidence only |
| US PEAD, analyst revisions/recommendations, standalone F-score, distress L/S, Fed model, CAPE overlay | US | DROP | — | — | Negative or zero expected net Sharpe (table above; §4, §6) |
| CAPE / implied ERP / KOSPI P/B panel | US, Korea | CONTEXT | 10-year expected-return band; no weight | Monthly display | Not gated |

**Combination with momentum.**
- US: combine value-quality with QUANTGEN's vol-scaled momentum sleeve (macro R-03) at the *portfolio* level, weighted by realised sleeve correlation measured on QUANTGEN's own data (ρ may be near −0.2, not −0.6). Do not ship a single "ValMom" card, because its turnover (about 27-29%/month) makes it negative at 2× cost.
- Korea: 12-1 momentum is negative, so the Korean partner for fundamentals is the reversal sleeve or flow. Measure the KR-ISS correlation with Korean 1-month reversal before any combination (DC-7).

**Rebalancing.**
- Annual-accounting signals: refresh monthly as filings arrive, but trade only on band crossings. Target one-sided turnover below 5-8%/month (L/S) or below 25%/month long-leg, well under Novy-Marx-Velikov's 50% survival threshold.
- Quarterly signals (quarterly ROE, SUE): turnover of 22-35%/month makes them uneconomic at QUANTGEN's costs.

####### Gaps
- The expected-Sharpe table applies published US 1963-2012 gross figures and assumed haircuts; none of these numbers has gone through QUANTGEN's gate.
- Korean costs for small KOSDAQ names (spreads above 35 bp per side) are not modelled; the 2× stress (70 bp) is the only proxy.
- Whether long-only tilts keep about 60% of each anomaly (Israel-Moskowitz show this for value, not for issuance or profitability) is untested.


### [P3] Where and when it failed (section 9) (lines 358-393)

###### 9. Where and when it failed (dated episodes)

####### Takeaway
Every fundamental signal in this note has a documented failure. The failure modes are valuation compression (value), arbitrage and learning after publication (accruals, PEAD, buybacks), mis-measurement (book value without intangibles), construction dispersion (value indices in 2025), costs (PEAD, distress, analyst strategies), long-only versus long-short gaps (quality in 2022), and policy or regime shifts (Korea 2024-26).

####### Cited Findings
- **1990s value.** A $1 value strategy lost 10% over the 1990s — [Lev & Srivastava](https://cfr.ivo-welch.org/forthcoming/papers/lev2021explaining.pdf). HML drew down 40.6% in the 1999-2000 tech bubble — [AHKL](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf).
- **Jan-2007 to Jun-2020 value.** HML −54.8% over 13.5 years; −6.1%/yr after Jul-2007 — [AHKL](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf). $1 → $0.82 over 2010-2018 — [Lev & Srivastava](https://cfr.ivo-welch.org/forthcoming/papers/lev2021explaining.pdf). Value was a "grave disappointment" out of sample since about 1990, and 2018-2020 was essentially a crash — [Asness, AQR, 4 Mar 2021](https://www.aqr.com/Insights/Perspectives/The-Long-Run-Is-Lying-to-You).
- **2023-2024 value vs growth.** Russell 1000 Value trailed Growth by 31.2 pp in 2023 (11.31% vs 42.49%) and 19.0 pp in 2024 (14.16% vs 33.11%) — [iShares IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); [iShares IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf).
- **2025 construction dispersion.** Russell 1000 Value +15.71% vs MSCI USA Enhanced Value +32.65% — [iShares IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); [iShares VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf).
- **2022 quality (long-only).** MSCI USA Quality −20.39% vs Russell 1000 −19.24% — [iShares QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf); [iShares IWB](https://www.ishares.com/us/products/239707/ishares-russell-1000-etf).
- **Japan profitability and investment.** Little relation to returns — [Fama & French 2017](https://ideas.repec.org/a/eee/jfinec/v123y2017i3p441-463.html).
- **Accruals by about 2011.** No longer reliably positive (US) — [Green, Hand & Soliman](https://pure.psu.edu/en/publications/going-going-gone-the-apparent-demise-of-the-accruals-anomaly/).
- **PEAD.** Gone for non-microcaps since 2006 and for microcaps since 2016 — [Martineau](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607). Hedge PEAD indistinguishable from zero after 2017 — [Kettell, McInnis & Zhao](https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf). Ex-microcap t = 1.43 over 2001-2024 — [UCLA Anderson Review](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/).
- **Buybacks and SEOs, 2003-2012 events.** Long-run abnormal returns disappear — [Fu & Huang](https://ideas.repec.org/a/inm/ormnsc/v62y2016i4p964-984.html).
- **F-score and distress, US 1973-2012, net of costs.** Net t 0.45 and 0.73 — [Novy-Marx & Velikov](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- **Analyst recommendations (late-1980s to 1990s sample).** Net returns not reliably above zero — [Barber et al. 2001](https://ideas.repec.org/a/bla/jfinan/v56y2001i2p531-563.html).
- **Market valuation.**
  - Value-only market timing, 1900-2015: Sharpe 0.37 vs 0.38 — [AIM 2017](https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Market-Timing-Sin-a-Little.pdf).
  - Equity-premium predictors failing OOS for decades — [Welch & Goyal 2008](https://ideas.repec.org/a/oup/rfinst/v21y2008i4p1455-1508.html); [GWZ 2024](https://www.sfi.ch/en/publications/a-comprehensive-2022-look-at-the-empirical-performance-of-equity-premium-prediction).
  - Local: after CAPE 30.8 (Sep-2023), the S&P 500 rose 69.8% in 36 months; after CAPE 38.3 (Dec-2021), +28.6%. The 1-year OOS R² was −39% in 2010-2022.
  - The Jan-2000 forecast of −55% real (ten years) compared with a realised −38.6% real price change: directionally right — [Campbell & Shiller 2001](https://www.nber.org/system/files/working_papers/w8221/w8221.pdf).
- **Korean issuance (Local).**
  - L/S losing years: 1997 (−0.5%), 2011 (−0.4%), 2015 (−6.7%), 2017 (−2.6%), 2020 (−3.9%), 2023 (−0.1%). Maximum drawdown −17% (Mar-2018).
  - Recent-decade long-only net IR 0.42 with a CI including zero.
  - Share-count decreasers −0.6%/yr EW in 2014-2023.

####### Inferences
- For QUANTGEN's gate, step 8 (≥ 60% positive calendar years) will bind for fundamental cards: the Korean issuance long-only active result net of 35 bp had 68% positive years over 1996-2026 but only 60% in 2017-2026.
- Value's failures cluster in growth manias (1999, 2020, 2023-24), when the valuation spread widens. A value card's drawdown should be reported alongside the valuation spread, but the spread must not be used to time it (Ilmanen et al.).
- Signals with published, easily computed definitions (accruals, PEAD, F-score, buybacks) decayed fastest in the US. Korea may lag (Jacobs-Müller), but the local issuance decay shows Korea is not immune.

####### Gaps
- No Korean value, quality or PEAD failure episodes can be dated here (no Korean data or studies opened).
- French long-short factor drawdowns for 2021-2026 are not measured.


### [P3] Claims ledger and data checks (lines 394-470)

###### 10. Data-check requests, claims ledger and sources

####### Takeaway
Eight data-lab tests would settle the claims P3 could not verify, and the 30-claim ledger below states each claim's evidence, robustness and QUANTGEN implication. The most decision-relevant tests are DC-1 (Korean issuance through the full gate), DC-3 (Korean PEAD on DART timestamps) and DC-2 (whether KRX BPS is point-in-time, which would unlock pre-2015 Korean value).

####### Cited Findings
######## Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P3-C01 | The US value premium is small and statistically fragile among large stocks after 1991 and falls with firm size. | Market value 0.42%/mo (t 3.25) 1963-91 vs 0.11% (t 0.60) 1991-2019; big value 0.36 → 0.05; difference t 1.39; US, gross, IS→later sample | [FF Value Premium](https://ebicapital.nl/wp-content/uploads/2022/05/The-Value-Premium.pdf); [FF 2012](https://ideas.repec.org/a/eee/jfinec/v105y2012i3p457-472.html); [Israel-Moskowitz](https://www.aqr.com/Insights/Research/Journal-Article/The-Role-of-Shorting-Firm-Size-and-Time-on-Market-Anomalies) | T1 | Replicated internationally; post-publication of FF1992 | 1990s; 2007-2020; 2023-24 | CONTEXT: no standalone US value card |
| P3-C02 | The 2007-2020 value drawdown came mainly from valuation compression, not structural decay. | HML −54.8% (Jan-07 to Jun-20, 13.5 yrs); revaluation −7.2 pp/yr; structural +1.1 vs +5.9 pp/yr; 116% of shortfall; bootstrap p 2.3%; US, gross | [AHKL FAJ 2021](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf) | T1 | Decomposition-dependent; ex post | 2007-2020 | CONTEXT; do not time value by spread |
| P3-C03 | Including intangibles in book value materially improves value. | HML_INT 5.60%/yr SR 0.86 vs HML 3.49% SR 0.35 (1975-2018); alpha 3.86%/yr; 2007-18 +0.76% vs −2.77%; iHML drawdown −43.0% over 3.5 yrs; US, gross, IS | [EKP NBER PDF](https://www.nber.org/system/files/working_papers/w28056/w28056.pdf); [AHKL](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf); [Lev-Srivastava](https://cfr.ivo-welch.org/forthcoming/papers/lev2021explaining.pdf) | T1 | Three teams agree; designed after the failure | Unknown post-2020 | BUILD feature: capitalised R&D in US-VQ book (counted as a trial) |
| P3-C04 | Timely prices in B/M add value alpha. | 305-378 bp/yr alphas; US 1950-2011, intl 1983-2011; gross | [Asness-Frazzini](https://www.aqr.com/Insights/Research/Journal-Article/The-Devil-in-HMLs-Details) | T2 | Practitioner journal; US + intl | Raises turnover | BUILD rule: lagged filed book / current market cap |
| P3-C05 | US value since 2021 trailed growth cumulatively, and results depend heavily on construction. | IWD +96.8% vs IWF +112.8% (Jan-21 to Sep-26); VLUE +32.65% vs IWD +15.71% (2025); IWF P/B 15.74 vs IWD 3.27 (30 Sep 26); long-only, net of fees | [IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); [IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf); [VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf) | T2 | Index data; not the long-short factor | 2023 (−31 pp), 2024 (−19 pp) | Pre-register one value definition; sector-neutral |
| P3-C06 | Gross profitability is a strong signal that hedges value. | GP/A 0.31%/mo (t 2.49), FF3 α 0.52 (t 4.49), 1963-2010; GP+value SR 0.85 vs mkt 0.34; ρ −0.57; intl 0.76%/mo (t 2.25) 1990-2009; ValProf net 0.77%/mo (t 4.82) 1963-2012 | [Novy-Marx 2013](https://oldschoolvalue-files.s3.amazonaws.com/pdf/Novy-Marx_Gross-Profitability-Anomaly_JFE_2013.pdf); [NMV](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) | T1 | Replicated (OSAP); international; survives costs | Large-cap spread weaker (t 1.88) | BUILD-candidate: core of US-VQ |
| P3-C07 | Quality minus junk earns robust alphas worldwide, but long-only quality did not beat the US market in 2021-26. | QMJ α 60 bp/mo (t 9.95) US 1957-2016; 61 bp (t 8.07) 24 countries 1989-2016; 23/24 positive; QUAL +102.2% vs IWB +107.0% (Jan-21 to Sep-26); 2022 −20.39% vs −19.24% | [AFP RAS 2019](https://link.springer.com/article/10.1007/s11142-018-9470-2); [QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf); [IWB](https://www.ishares.com/us/products/239707/ishares-russell-1000-etf) | T1/T2 | Strong IS; long-only ≠ long-short | 2022 long-only | US quality prior 3 → 2; hold at 1.0× (macro rule) |
| P3-C08 | Buffett's record is largely explained by cheap, safe, quality stocks plus about 1.6× leverage. | SR 0.76; alpha insignificant after BAB + QMJ | [NBER w19681](https://www.nber.org/papers/w19681); [AQR](https://www.aqr.com/Insights/Research/Journal-Article/Buffetts-Alpha) | T1 | Single-entity case | — | CONTEXT: supports quality + low-risk composite |
| P3-C09 | Profitability and investment effects are not universal; Japan is an exception, and HML is redundant in the US five-factor model. | Japan strong B/M, little profitability/investment relation; HML redundant given RMW/CMA | [FF 2017](https://ideas.repec.org/a/eee/jfinec/v123y2017i3p441-463.html); [FF 2015](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2287202) | T1 | Multi-region | Japan | Japan quality prior 2 → 1-2 |
| P3-C10 | The F-score worked internationally in 2000-2018 (incl. EM with Korea) but is near zero net in broad US tests. | EM 0.95%/mo (t 9.6), developed 0.79% (t 6.5), large caps 0.62-0.76%; US 1973-2012 0.20% gross, 0.09% net (t 0.45); original 23.5%/yr EW 1976-96 | [Walkshäusl 2020](https://d-nb.info/121155211X/34); [NMV](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf); [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv) | T1 | Post-publication OOS internationally | US net | Component of US-VQ and KR-VQ; DROP standalone |
| P3-C11 | The Mohanram G-score separates winners among growth stocks in-sample only. | 1.575%/mo EW (t 9.14), 1978-2001, IS | [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv) | T1 | No post-publication evidence found | Unknown | BACKLOG |
| P3-C12 | The accrual anomaly has decayed in the US. | Sloan 10.4% / 4.8% / 2.9% (t+1..t+3), 1962-91, >40% at announcements; "no longer reliably positive" by 2011; NMV 0.27% gross, 0.18% net (t 1.43) | [Sloan 1996](https://www.cuhk.edu.hk/acy2/workshop/June2009Wasley/1996TAR%29.pdf); [GHS](https://pure.psu.edu/en/publications/going-going-gone-the-apparent-demise-of-the-accruals-anomaly/); [NMV](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) | T1 | Post-publication decay documented | 2000s-2011 | DROP card; small weight in composite |
| P3-C13 | High M-score (likely manipulators) predicts lower returns, especially among low-accrual firms. | About −1%/mo risk-adjusted; −19.8% over 12 months in the lowest-accrual quintile | [Beneish-Lee-Nichols 2013](https://ideas.repec.org/a/taf/ufajxx/v69y2013i2p57-82.html) | T2 | Single study; period not documented here | Unknown | BACKLOG: long-book exclusion screen |
| P3-C14 | US PEAD has disappeared for non-microcap stocks. | No drift since 2006 (non-microcap), since 2016 (microcap); announcement-day coefficient 0.002 → 0.012; hedge PEAD 4.4%/qtr 1974-2020, ≈0 after 2017; 2001-24 t 2.18 all, 1.43 ex-micro (conflict: HPW 2025 t ≈ 14) | [Martineau](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607); [KMZ](https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf); [UCLA AR](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/) | T1 | Multiple independent studies | 2006+ | DROP US earnings drift (2 → 0) |
| P3-C15 | PEAD lives in illiquid stocks and is mostly consumed by costs. | 2.43%/mo illiquid vs 0.04% liquid (1972-2005); costs 70-100%; NMV SUE 0.72% gross, 35% turnover, 0.26% net (t 1.60) | [Chordia et al. 2009](https://ideas.repec.org/a/taf/ufajxx/v65y2009i4p18-32.html); [NMV](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) | T1 | Robust across studies | Any high-cost setting | Korea earnings drift 3 → 1 pending DC-3 |
| P3-C16 | An earnings-announcement premium exists in the US and in about half of countries. | 61 bp/mo (t 5.30) 1973-2004; 153 bp in high-volume-concentration stocks; 9 of 20 countries significant | [Frazzini-Lamont](https://www.nber.org/system/files/working_papers/w13090/w13090.pdf); [Barber et al. 2013](https://ideas.repec.org/a/eee/jfinec/v108y2013i1p118-138.html) | T1 | International partial | Costs unquantified | BACKLOG (US calendar-based) |
| P3-C17 | Analyst recommendation strategies are gross-profitable but not net. | >4%/yr gross with daily rebalancing; net not reliably > 0; REV6 t 4.07 (1977-92) | [Barber et al. 2001](https://ideas.repec.org/a/bla/jfinan/v56y2001i2p531-563.html); [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv) | T1 | Costs decisive | Net of costs | DROP (no PIT analyst data) |
| P3-C18 | Asset growth and investment predict lower returns worldwide; they survive costs best inside composites. | CGS decile 1.73%/mo EW (t 8.45), VW t ≈ 5 (1968-2003); NMV asset growth net 0.26% (t 1.75), investment net 0.46% (t 3.60); stronger in developed markets | [CGS](https://ideas.repec.org/a/bla/jfinan/v63y2008i4p1609-1651.html); [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv); [NMV](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf); [Watanabe et al.](https://ideas.repec.org/a/eee/jfinec/v108y2013i2p529-563.html) | T1 | International; q-theory consistent | Weak standalone net | US-VQ component |
| P3-C19 | Net share issuance is among the most robust financing signals internationally. | Post-1970 strong, pre-1970 none (US); 41 countries, comparable to B/M; robust in 28 EM; NMV net 0.37%/mo (t 2.43) monthly | [Pontiff-Woodgate](https://ideas.repec.org/a/bla/jfinan/v63y2008i2p921-945.html); [MPW 2009](https://ideas.repec.org/a/eee/jfinec/v94y2009i1p1-17.html); [Hanauer-Lauterbach](https://ideas.repec.org/a/eee/ememar/v38y2019icp265-286.html) | T1 | International OOS | Pre-1970 US | US-VQ component; KR-ISS basis |
| P3-C20 | Korean net issuance predicts returns net of QUANTGEN costs but is decaying and strongest in EW/KOSDAQ. | 1996-2026: EW L/S SR 1.31 gross, 1.04 net 35 bp, 0.78 at 70 bp; VW 0.47/0.34/0.21; long-only active IR 0.84 net 35 bp [0.46, 1.25]; 2017-26 0.42 [−0.28, 0.95]; decay 1.78 → 1.37 → 0.79 | Local: `/home/claude/data_raw/marcap` (P3 test, §5) | Local (unreviewed) | Lag/horizon robust; ~10 variants tried; not walk-forward | 2015, 2017, 2020 | BUILD-candidate KR-ISS (long-only exclusion) through gate |
| P3-C21 | US buyback drift disappeared; Korean cancellation effects look regime-specific (2024-26). | ILV 4-yr BHAR 12.1% (value 45.3%), 1980-90; none for 2003-12 events; Korea decreasers: full EW t 0.61; 2024-26 EW +10.0%/yr (t 2.37), VW +20.6% (t 2.07), 32 months | [ILV](https://ideas.repec.org/a/eee/jfinec/v39y1995i2-3p181-208.html); [Fu-Huang](https://ideas.repec.org/a/inm/ormnsc/v62y2016i4p964-984.html); Local marcap | T1 + Local | US decay confirmed; Korea n small | US 2003-12; Korea 2014-23 EW | BACKLOG (BL-O04 update) |
| P3-C22 | Distressed stocks underperform, but the long-short is not harvestable after costs. | CHS: low returns since 1981 (1963-2003); OSAP failure-prob t 1.41 (placebo), O-score t 3.36, Z t 1.59; NMV 0.85% gross, 26% turnover, 0.24% net (t 0.73) | [CHS NBER](https://www.nber.org/papers/w12362); [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv); [NMV](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) | T1 | Mixed replication | Net of costs | Exclusion screen, not a card |
| P3-C23 | Published anomaly returns shrink by about 26% OOS and 58% post-publication in the US, less clearly elsewhere. | 97 predictors; HXZ 64% insignificant (VW, NYSE breakpoints); Chen-Velikov avg net 8 bp/mo; halved after decimalisation; vs JKP replicate in 93 countries; Jacobs-Müller decline reliable only in US | [McLean-Pontiff](https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf); [HXZ](https://www.nber.org/papers/w23394); [Chen-Velikov](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681); [CST](https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html); [JKP](https://www.nber.org/papers/w28432); [Jacobs-Müller](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html) | T1 | Meta-evidence; partly conflicting | — | Haircut US 50%; Korea smaller but measure locally |
| P3-C24 | Slow, low-turnover fundamental strategies survive costs; high-turnover ones do not. | <50% one-sided monthly turnover survives; buy/hold spread best mitigation; P3 estimate at 50 bp after haircuts: ValProf 0.42, GP 0.17, value 0.15, PEAD −0.51 | [NMV](https://www.nber.org/papers/w20721); P3 computation (§8) | T1 + computation | Cost formula matches NMV within ~10% | ValMom negative at 2× | Monthly refresh with bands; reject quarterly signals |
| P3-C25 | Value and momentum diversify in-sample, but the hedge is weaker on recent US data and inapplicable to Korean 12-1 momentum. | AMP SR 0.51/0.59 → 1.28 (global stocks 1972-2011, IS); ρ −0.49 to −0.60; NMV ValMomProf net 0.99%/mo (t 5.18); QUANTGEN French ρ −0.17 | [AMP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf); [NMV](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf); QUANTGEN macro doc | T1 | Strong IS; weaker recently | Turnover; US momentum ≈ 0 since 2008 | Combine at sleeve level; measure own correlations |
| P3-C26 | CAPE predicts 10-year returns in-sample but fails at 1-year horizons out of sample. | CS 2001: R² 30% / 40% (1872-2000); Jan-2000 forecast −55% real vs realised −38.6%; Local OOS R² 1y: −2.4% (1950-), −11.1% (1990-), −39.1% (2010-22); post-Sep-23 S&P +69.8% in 36m; CAPE 41.07 (1 Oct 26) | [CS NBER w8221](https://www.nber.org/system/files/working_papers/w8221/w8221.pdf); [multpl](https://www.multpl.com/shiller-pe); Local Shiller | T1 + T3 + Local | Long-horizon IS robust; OOS fails | 2013-2026 | CONTEXT only (no multiplier) |
| P3-C27 | Equity-premium predictors and value-based market timing do not beat simple benchmarks out of sample. | WG 2008 poor IS/OOS for 30 yrs; GWZ 2024: >1/3 of 29 new variables insignificant IS, half of rest poor OOS; CT-restricted smoothed E/P annual OOS R² 6.6% (1927-2003); AIM value timing SR 0.37 vs 0.38 (1900-2015), V+M 0.43 | [WG 2008](https://ideas.repec.org/a/oup/rfinst/v21y2008i4p1455-1508.html); [GWZ](https://www.sfi.ch/en/publications/a-comprehensive-2022-look-at-the-empirical-performance-of-equity-premium-prediction); [Campbell-Thompson](https://www.nber.org/system/files/working_papers/w11468/w11468.pdf); [AIM](https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Market-Timing-Sin-a-Little.pdf) | T1/T2 | Replicated over decades | Post-1990 | No valuation overlay (consistent with macro rules) |
| P3-C28 | The Fed model is theoretically flawed and has no long-horizon forecasting power. | Real E/P vs nominal yield (money illusion); no power for long-term real returns; P/E alone effective | [Asness 2003](https://www.aqr.com/Insights/Research/Journal-Article/Fight-the-Fed-Model) | T2 | Widely cited | — | DROP |
| P3-C29 | The implied ERP (4.14% on 1 Sep 2026) is mid-range even though CAPE is near its record. | ERP 4.14% (T-bond 4.75%); year-end 2022 5.94%, 2024 4.33%, 2025 4.23%; 1999 2.05%; analysts raised 2026-27 EPS estimates by >11% | [Damodaran home](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm); [histimpl](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html); [blog](https://aswathdamodaran.blogspot.com/) | T1/T2 | Model-dependent (3.56-6.05% range) | — | CONTEXT: show both gauges and their disagreement |
| P3-C30 | Point-in-time fundamentals require filing timestamps and first-filed snapshots; Korean statement history is short and date-only. | US 10-K 60/75/90 d, 10-Q 40/45 d; XBRL 2009-11; `acceptanceDateTime`; XBRL `filed`/`accn`; Korea 2026: annual 03/31, Q1 05/15, H1 08/14, Q3 11/16 (+15 d first consolidated years); OpenDART FS from 2015; `rcept_dt` date only; values may change after corrections; ~20,000 requests limit | [10-K](https://www.sec.gov/files/form10-k.pdf); [10-Q](https://www.sec.gov/files/form10-q.pdf); [33-9002](https://www.sec.gov/rules/final/2009/33-9002.pdf); [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces); [DART schedule](https://dart.fss.or.kr/info/main.do?menu=410); [OpenDART list](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001); [OpenDART FS](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020) | T1 | Official | Look-ahead if ignored | BUILD invariant: PIT store; rcept_dt + 1 session |

Context claim (not numbered; T2): the Korea discount and Value-Up regime (KOSPI P/B 0.99 vs Japan 1.8 and US 3.7 in 2014-2024; Value-Up launched Feb-2024; Value-Up Index +17% vs KOSPI 200 since Oct-2024) — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/). Implication: split all Korean value/payout tests at Feb-2024.

####### Inferences
######## Data-check requests (exact tests for the data lab)
- **DC-1, Korean issuance through the full gate (P3-C20).** Reproduce §5 exactly.
  - Universe: marcap KOSPI + KOSDAQ codes ending "0"; drop 스팩/리츠/인프라; Close ≥ ₩1,000; drop the bottom 30% by month-end market cap.
  - Shares: split-adjust listed shares by detecting days with |log(prev × (1 + ChangesRatio/100) / Close)| > 0.002; drop stock-months with events in months t..t−2 or t−11..t−13.
  - Signal: ISS = log(S_t / S_t−12). Long-only: EW basket with ISS ≤ 0.5% vs the EW universe; L/S research twin minus the top-quintile ISS.
  - Then run QUANTGEN's 9-step gate: monthly rebalance at the close, purged walk-forward 756/126 sessions, embargo 21 sessions, 35/70 bp. Count at least 10 trials in the deflated Sharpe (EW/VW, lags 0/1, horizons 12/24/36, size cuts, market splits).
  - Also test a pre-registered quarterly-rebalance variant and an ex-Samsung/SK hynix variant.
  - Report IR, 90% block-bootstrap CI, share of positive calendar years, and the 2017-2026 sub-sample.
- **DC-2, KRX BPS point-in-time check.** For 50 random KOSPI/KOSDAQ firms in 2016-2025, compare the date the KRX/pykrx BPS changes with the OpenDART `rcept_dt` of the business report or quarterly report. If BPS changes on or after `rcept_dt`, KRX PBR can serve as a PIT book from about 2000; otherwise lag it by 90/45 days.
- **DC-2 continued, Korean value test (if DC-2 passes).** Monthly PBR quintiles 2001-2026, EW and VW, sector-neutral; exclude and include the Samsung/SK hynix pair; split at Feb-2024; costs 35/70 bp; long-only top quintile vs EW universe.
- **DC-3, Korean PEAD/CAR3.**
  - Events: OpenDART `list.json` with `pblntf_ty=I`, filtered to `report_nm` containing "영업(잠정)실적" or "매출액또는손익구조"; event date = `rcept_dt`.
  - Signal: CAR(−1, +1) vs the KOSPI/KOSDAQ index (no consensus needed).
  - Entry at the close of `rcept_dt` + 1 session; hold 60 sessions; decile long-short and long-only top decile.
  - Sample 2012-2026; split by size tercile and by year (Martineau-style decay test); costs 35/70 bp.
  - Pass rule: at the 2× cost the Sharpe must be > 0 in the top two size terciles.
- **DC-4, Korean profitability/F-score coverage.**
  - Pull `fnlttSinglAcntAll` (CFS, fallback OFS) for all listed firms, 2015-2026.
  - Report the share of firm-years with 매출원가 (COGS) available, computable GP/A, and all nine F-score inputs.
  - Store `rcept_no` and `rcept_dt` with every value and keep amended versions separately.
- **DC-5, CAPE refresh and replication (P3-C26).**
  - Update the Shiller file (PE10 and dividends are stale after 2023-09/2023-06).
  - Rerun: monthly real total return; 1-year forward target; expanding OLS on log CAPE with at least 240 months of training, using only targets realised by t; Campbell-Thompson non-negativity.
  - Report OOS R² vs the historical mean for 1926-, 1950-, 1990-, 2010-.
  - Pre-register one overlay (multiplier 0.75 when CAPE is above its trailing 80th percentile, else 1.0, inside [0.5, 1.0]) and report ΔSharpe vs buy-and-hold with a paired bootstrap.
- **DC-6, French factor refresh.** Update the local French file (ends 2018) to Aug-2026. Report annual HML, RMW and CMA for 2019-2026, the HML drawdown from 2007 to its latest high, and verify RMW 2022 = +8.4%.
- **DC-7, sleeve correlations.** Monthly correlations, 1996-2026, of the KR-ISS long-only active return with Korean 1-month reversal, 12-1 momentum and the KOSPI vol-target sleeve. In the US, the correlation of French HML+RMW with vol-scaled WML for 1990-2026 and 2008-2026.
- **DC-8, delisting bias.** For marcap codes that stop trading, check whether 정리매매 prices are present and compute the last-month return. Re-run the DC-1 L/S with a −30% delisting-return assumption for codes that disappear without a liquidation-trading record.

####### Gaps
- Claims P3-C20/C21 (local) and the expected-Sharpe computations (P3-C24) await data-lab reproduction.
- Korean-specific academic evidence for value, quality, accruals and PEAD is missing from this ledger.
- FMP fields, KRX BPS timing and DART filing time-of-day remain unverified.


---

## P4_backtest_econometrics_costs.md

### [P4] Persona and position summary (lines 1-38)

##### P4: Backtest econometrics, multiple testing, decay and costs. How much published technical and fundamental edge survives, and the testing protocol every QUANTGEN technical/fundamental card must follow

**Persona (fictional composite, not a real person):** P4, "Professor of Empirical Finance Methods". An econometrician who referees empirical asset-pricing papers for top finance journals. P4 asks three questions of every number: (1) how many things were tried before it was found (multiplicity), (2) what is left after decay and realistic costs (economic size), and (3) could a retail, long-only, KRX-first investor actually earn it (implementability). P4 argues from published econometrics and large replication studies, and treats TradingView-style strategy claims as unverified practitioner hypotheses.

As of 2 October 2026. Conventions: SR = annualized Sharpe ratio unless stated; IS = in-sample; OOS = out-of-sample; gross/net = before/after trading costs; bp = basis points; /m = per month; L/S = long-short. "Own computation" means P4's arithmetic from formulas in the cited papers. It is not a quoted result.

**Position summary**
1. Published cross-sectional anomalies mostly **replicate statistically** when they are built the way the papers built them: 98% of 161 clear predictors reproduce at t > 1.96 (Chen-Zimmermann), and 84.9% of US factor CAPM alphas replicate, or 77.3% after a Benjamini-Yekutieli correction (Jensen-Kelly-Pedersen). So "it was all data mining" is wrong as a blanket claim.
2. The **economic size shrinks at every honest step**. Returns are 26% lower out of sample and 58% lower after publication (McLean-Pontiff, 97 US predictors). Sharpe ratios of accounting anomalies are 60-77% lower outside their discovery samples (Linnainmaa-Roberts). After effective spreads in the post-2000 trading era, the average of 204 anomalies is expected to earn about 4 bp/m (Chen-Velikov), roughly a tenth or less of the published in-sample premium.
3. **Construction choices are a hidden multiple-testing channel.** With NYSE breakpoints and value weights, 64% of 447 anomalies fail t >= 1.96 and 85% fail t >= 3 (Hou-Xue-Zhang). The main reason is that microcaps (about 61% of firms but about 3% of market cap) drive equal-weighted results.
4. **Turnover decides survival.** Anomalies with one-sided turnover below 50% a month mostly keep significant net spreads. Short-term reversal (US 1963-2012: 37 bp/m gross becomes -128 bp/m net), industry momentum and seasonality turn negative (Novy-Marx-Velikov). Even an institution whose live costs are an order of magnitude below academic estimates could not make reversal pay (Frazzini-Israel-Moskowitz).
5. For **technical trading rules** the large-universe evidence is negative. Across 7,846 rules on the DJIA, no rule outperforms after 1962 even before costs; earlier outperformance is wiped out by 16-70 bp one-way costs; and in-sample winners do not persist (Bajgrowicz-Scaillet). Rules that stay profitable after data-snooping checks appear only in "young" markets (Hsu-Kuan).
6. **Retail backtest "success rates" are not evidence.** A win rate without the payoff ratio says nothing about expectancy: a +1%/-9% bracket on a driftless price wins 90% of trades with zero gross expectancy. TradingView's strategy defaults simulate zero commission and zero slippage, and its own documentation estimates that over 95% of indicators repaint in some form.
7. **QUANTGEN's gate is already stricter than most published practice** (pre-registration, revision counting, DSR, PBO, 2x costs, published failures). For stock-level cards it has five holes:
   - no family-wise test (SPA, StepM or FDR) across a rule family or across cards;
   - single-test hurdles (a 90% interval, one-sided p <= 0.10), far below the t of about 3 that the literature asks of novel signals;
   - flat per-side costs that ignore liquidity buckets, the 2026 KRX sell tax of 0.20%, price limits and entry timing;
   - no rules for long-only implementability under KRX short-sale bans, for delisting returns, or for point-in-time DART data;
   - a fixed 60% haircut that double-counts decay when the test window is already post-publication, plus a calendar-year rule that passes 36-38% of zero-edge strategies over 8-10 years.
8. **Recommendation:** every new technical or fundamental card follows a pre-registered protocol (detailed in Q7):
   - at most 27 configurations per card;
   - purged walk-forward plus CPCV on KRX 2000-2018, and a sealed holdout from 2019-01-02 to 2026-09-30 that is opened once;
   - liquidity-bucket costs, re-run at 2x;
   - long-only evaluation against an equal-weighted liquid-universe benchmark;
   - two hurdle tiers: net t >= 2.0 for replications of published, internationally replicated anomalies, and net t >= 3.0 plus a family-wise SPA p <= 0.05 for novel or chart-pattern signals;
   - a program-wide FDR (q = 10%) across all cards.
9. **What to expect:** most chart-pattern cards will REJECT. The realistic BUILD candidates are low-turnover fundamental sleeves (profitability/quality, value) and possibly long-only low volatility on liquid KRX names. Korean short-term reversal, weighted 3 in the prior design, conflicts with the cost evidence and should get weight only after it passes net of bucket costs.

**Survival funnel at a glance** (approximate, across studies; each number is labeled with its study, market and period in the sections below)

| Stage | Evidence | Share of published edge left | Sources |
|---|---|---|---|
| Published, IS | 97 US predictors, average L/S 0.582%/m gross, IS | 100% | McLean-Pontiff |
| (a) Multiple testing and construction | 447 US anomalies, NYSE breakpoints + VW, 1967-2014: 36% significant at t >= 1.96, 15% at t >= 3. US factor CAPM-alpha replication 84.9%, falling to 77.3% after BY. Publication-bias-adjusted returns 12% below IS | 15-77% of anomalies survive, depending on construction and hurdle; about 88% of the magnitude for predictors that passed peer review | Hou-Xue-Zhang; Jensen-Kelly-Pedersen; Chen-Zimmermann |
| (b) Post-publication decay (US) | Pre-publication OOS -26%, post-publication -58% (McLean-Pontiff); alpha -31% (Jensen-Kelly-Pedersen); about 50% remains (Chen-Lopez-Lira-Zimmermann); Sharpe -60% to -77% for accounting anomalies (Linnainmaa-Roberts). No reliable decline outside the US across 39 markets (Jacobs-Müller) | About 40-70% (US) | as listed |
| (c) Costs and short-sale constraints | Average anomaly about 4 bp/m net in the modern era (204 anomalies); US short-term reversal -128 bp/m net (1963-2012); mutual funds realize about 15-18% of momentum's paper return and about 34-51% of value's (1970-2016); the long side is about half of momentum profits and 60% of value profits | About 7% for the average anomaly (4 bp vs 58 bp, a cross-sample ratio); about 90% for low-turnover value and gross profitability before decay | Chen-Velikov; Novy-Marx-Velikov; Patton-Weller; Israel-Moskowitz |
| (d) Honest OOS for technical rules | 7,846 DJIA rules: zero outperformers 1962-2011 even at zero cost, and no persistence. Backtest SR explains less than 2.5% of OOS SR variance across 888 algorithms | About 0% for generic chart rules on mature indices | Bajgrowicz-Scaillet; Wiecki et al. |


### [P4] Gate audit, protocol P4-TF-1, cost buckets (lines 466-558)

####### Inferences

######## A. Gate audit: each step against the literature

| Step | Current rule | Literature anchor | P4 verdict | Change for technical/fundamental cards |
|---|---|---|---|---|
| 1 | Purged walk-forward 756/126, embargo = holding period | Purging/embargo (López de Prado); hold-out unreliability (Bailey et al. 2015); CPCV beats WF (Arian et al. 2024) | Keep, but not enough on its own: one path, and a single 126-session window has SE of about 1.41 | Add CPCV (10 groups, 2 test groups: 45 splits, 9 paths). Embargo >= max(holding period, 21 sessions, reporting lag). Infer only from the concatenated OOS path or the CPCV distribution. Skip parameter selection for single-configuration replications |
| 2 | Lo IID SE + 90% bootstrap, 10-session blocks | Lo 2002; Mertens / PSR (Bailey-López de Prado); Politis-White 2004 | Too weak (about a one-sided 5% test, t of about 1.65); blocks too short for 21-session holds; ignores skew and fat tails | PSR/Mertens variance and HAC (Newey-West, lag >= holding period) t on **net excess** returns. Stationary bootstrap, block = max(Politis-White, 2 x holding period), 5,000 replications. Tiered hurdle t >= 2.0 / 3.0 / 3.4 (section C) |
| 3 | DSR >= 0.95, revisions counted | Bailey-López de Prado 2014 | Keep; the strongest step. Honest N already implies t of about 3.2-3.7 for 9-27 independent configurations | Pre-register how N_eff is estimated (BLdP formula, floored at 3 for any grid). TradingView-sourced ideas: N >= 100. Composites of k chosen from n signals: count n^k (Novy-Marx). Count data-lab quick-check looks as trials |
| 4 | PBO via CSCV <= 0.05 (REJECT if > 0.2 with the winner losing) | Bailey-Borwein-López de Prado-Zhu | Keep | S = 16 (12,870 splits). Also report the performance-degradation slope and probability of loss. Not applicable when only one configuration is tested |
| 5 | Beat benchmark, one-sided p <= 0.10 | White RC; Hansen SPA; Romano-Wolf StepM; Ledoit-Wolf | Too weak; single-test; no family-wise control | Ledoit-Wolf studentized bootstrap of the Sharpe difference, or HAC alpha t, against a **same-universe** benchmark. Multi-configuration cards: SPA consistent p <= 0.05 across all configurations, and StepM to name survivors. Program-wide Benjamini-Hochberg at q = 0.10 across all cards in a release |
| 6 | SR > 0 at 2x flat costs | Novy-Marx-Velikov; Chen-Velikov; Frazzini-Israel-Moskowitz; Patton-Weller; Detzel-Novy-Marx-Velikov | Right idea, wrong cost model: too cheap for small caps, too dear for mega-caps, ignores the 2026 tax and limit-locks | Liquidity-bucket costs plus statutory sell tax, no fills at locked limits, next-open execution for short horizons (section D). Require the net t-hurdle at 1x and SR > 0 at 2x. Report break-even cost per side |
| 7 | Plateau: >= 50% of neighbours keep half the SR | Heuristic; consistent with PBO logic | Keep as a robustness check | Define neighbours ex ante (one grid step in each dimension); neighbours count toward N |
| 8 | >= 60% of calendar years positive | No formal anchor | Weak: a zero-edge strategy passes 36% (8 years) or 38% (10 years) of the time (own computation) | Report-only. Replace with: positive net excess in >= 2 of 3 pre-registered subperiods, plus a KRX short-sale regime split (open / partial ban / full ban) |
| 9 | 60% haircut on Sharpe, reported | McLean-Pontiff; JKP; Linnainmaa-Roberts; Jacobs-Müller; Chen-Lopez-Lira-Zimmermann | Mis-calibrated: double-counts decay in post-publication windows, and wrongly haircuts market beta | Haircut **alpha versus the benchmark** only: h = 0.5 (in-sample or discovery overlap), h = 0.3 (fully post-publication). Display only the haircut figure |

######## B. Gaps not covered by any current step
- **G1. Multiplicity across cards.** A release with 34 cards at one-sided p <= 0.10 expects about 3.4 false passes if every card is null. Program-wide BH at q = 0.10 is required.
  - *Example (own computation, approximate):* C3's benchmark-difference p of 0.04 fails Bonferroni across the 16 trading cards (threshold 0.10/16 = 0.006). Under BH it would need at least 7 of the 16 trading cards to have p <= 0.044, and the brief reports only one or two.
  - C3's Sharpe against zero, though, is roughly t 3.5 (SE of about 0.35, inferred from the width of its 90% CI), which survives Bonferroni.
  - So C3's edge over zero is family-wise robust, while its edge over buy-and-hold is not. Re-score existing cards transparently rather than silently demoting them (D11).
- **G2. Cost realism:** liquidity buckets, the time-varying sell tax (0.15% in 2025, 0.20% from 2026; about 0.30% before 2019 per the Herald article), limit-locked days, and a participation cap.
- **G3. Implementability.** The long-only leg against the benchmark is the primary statistic. Long-short is a diagnostic only, and the short-leg share of long-short profits must be reported. Short-ban periods must be flagged: full bans 2020-03-16 to 2021-05-02 and 2023-11-06 to 2025-03-28 (about 2.5 years in total), and a partial ban 2021-05-03 to 2023-11-05 (about 2.5 years), using the data lab's regime dates.
- **G4. Data integrity.**
  - Delisting and suspension: the data lab's handling of zero-volume days effectively assumes a suspended stock leaves the portfolio at no loss. That is optimistic exactly when a stock is suspended before delisting (D5).
  - Point-in-time fundamentals: availability = OpenDART rcept_dt + 1 session; use first-reported values, not restated ones.
- **G5. Weighting robustness.** Report equal-weighted and capped value-weighted results. A sign disagreement means REVISE (Hou-Xue-Zhang microcap evidence).
- **G6. Execution timing.** Rule 2's "earn from t+1" should mean the t+1 open for holding periods of 5 sessions or less. Close-to-close is acceptable for holds of 20 sessions or more, with a t+1-open sensitivity check.
- **G7. Benchmark concentration.** Samsung Electronics and SK hynix account for most of the 2025-26 gap between the cap-weighted KOSPI200 proxy and the equal-weighted index. Compare long-only cards with the same-universe EW benchmark first, and with KODEX 200 and an ex-Samsung/SK hynix variant second.
- **G8. Contaminated holdouts.** The data lab's quick-checks already examined 2015-2026 for 12-1 momentum, 1-month reversal, 60-day low volatility, MAX and 52-week high. For those families the "sealed" 2019-2026 holdout is used up, and prospective incubation is the only clean out-of-sample test (D9).
- **G9. Power.** When MinTRL at the tier hurdle and the haircut SR exceeds the available history, the verdict is INSUFFICIENT DATA, not REJECT. Example (own computation): a true net SR of 0.5 needs about 16 years for t = 2 and about 36 years for t = 3.
- **G10. Event clustering.** For event cards (PEAD, chart patterns, limit-up), use calendar-time portfolios or date-clustered SEs. Pooling events on the same dates overstates t.
- **Conflict flag for the macro panel.** The data lab's mid-2026 KRX crash (2026-06-23 to 07-30) was led by the **winner** quintile (-43.0% vs -27.1% for the EW benchmark) after a melt-up. A Daniel-Moskowitz bear-state gate keyed to past market declines would not have fired in this state. Its documented crash mechanism is loser rebounds after bear markets. Volatility scaling and the bear gate should be stress-tested on this episode (D12). This flag does not reopen the macro decisions.

######## C. Protocol P4-TF-1 (pre-registered; applies to every new technical or fundamental card)
1. **Pre-registration file**, hashed before the first test: hypothesis; mechanism tier (A or B, per Q4); signal formula; configuration grid; universe; rebalance and holding period; weighting; banding rule; benchmark; cost model; primary statistic; hurdles; subperiods; holdout dates; incubation start.
2. **Configurations:** at most 27 per card (for example 3 lookbacks x 3 holding periods x 3 thresholds), and at most 3 revisions, each counted in N. A single-configuration replication of a published anomaly (Tier A) uses the paper's exact definition.
3. **Universe and data:**
   - KRX common stocks, excluding preferred shares, SPACs, ETFs/ETNs and administrative or warning-flag stocks at formation.
   - Liquid screen: market cap >= KRW 100bn, 20-day average traded value >= KRW 1bn, price >= KRW 1,000 (the data lab's screen), with point-in-time membership on survivorship-free data.
   - Delisting: last traded price including any final trading period; if no exit print exists, a stress case of -30% or -100% for negative delistings (see D5).
   - Fundamentals available from rcept_dt + 1 session.
4. **Sample split:**
   - (a) Development: 1996-01-02 to 2018-12-28 for OHLCV-only cards; 2000 (or the first year of point-in-time fundamentals) to 2018-12-28 for fundamental cards.
   - (b) Sealed historical holdout: 2019-01-02 to 2026-09-30 (about 7.75 years, SE of about 0.36), opened once. A failure is final for that design.
   - (c) Prospective paper incubation: at least 252 sessions from registration. This is a sanity and implementation check, not a significance test.
   - For signal families already viewed by the data lab (G8), (c) replaces (b).
5. **Validation inside development:** purged walk-forward as now, plus CPCV (45 splits, 9 paths); PBO over S = 16; DSR with N_eff.
6. **Primary statistic:** daily net excess return of the long-only portfolio over the same-universe benchmark. Report HAC t, PSR, and a stationary-bootstrap 95% CI.
7. **Hurdles (development, net of base costs):**

| Tier | Which cards | Required |
|---|---|---|
| A | Published, internationally replicated anomaly with a mechanism; single configuration | HAC t >= 2.0 and DSR >= 0.95 |
| B | New variant or technical rule, up to 27 configurations | t >= 3.0, SPA consistent p <= 0.05 and DSR >= 0.95 |
| B+ | More than 100 configurations, TradingView-sourced, or a k-of-n composite | t >= 3.4 (cross-sectional) or 3.8 (time-series alpha), plus SPA |

   All tiers also need: the program-wide BH at q = 0.10; positive net SR at 2x costs; positive net excess in >= 2 of 3 subperiods; PBO <= 0.05 where applicable; plateau as now.
8. **Holdout and incubation verdicts:**
   - PASS: holdout net excess >= 50% of the haircut development estimate (Linnainmaa-Roberts' "half of in-sample alpha").
   - REVISE: holdout net excess between 0 and 50% of that estimate, an equal-weight vs value-weight sign split, or a failure only at 2x costs.
   - REJECT: holdout net excess below 0, or the development hurdle missed.
   - Incubation kill rule: cumulative net excess below the 5th percentile of the bootstrap path implied by the haircut estimate.
9. **Display:** only the haircut net alpha (h = 0.5 or 0.3) is displayed. Exposure from stock cards is capped until incubation is complete.

######## D. Cost and execution assumptions (P4 proposals; calibrate in D3 before first use)

| Bucket (20-day avg traded value) | Non-tax cost per side | Plus statutory sell tax | Approx. all-in per side (2026 tax) | Current flat rule |
|---|---|---|---|---|
| >= KRW 50bn | 8 bp | 0.20% on sells | about 18 bp | 35 bp |
| KRW 10-50bn | 15 bp | same | about 25 bp | 35 bp |
| KRW 3-10bn | 30 bp | same | about 40 bp | 35 bp |
| KRW 1-3bn | 50 bp | same | about 60 bp | 35 bp |
| < KRW 1bn | excluded | | | |

- 2x stress doubles all components, conservatively matching current practice. Base case: the 2026 tax rate throughout; historical rates in force as a sensitivity check.
- No buys at a locked limit-up, and no sells at a locked limit-down: the position is carried and exited at the next tradable price.
- Each trade <= 2% of 20-day traded value at a reference portfolio of KRW 1bn. Report the size at which this cap binds for more than 10% of names.
- Banding (buy in the top quintile, hold until the name leaves the top 40%) is the default mitigation, counted as one design choice (Novy-Marx-Velikov).
- **US stock cards** at 50 bp per side: a monthly-rebalanced card with 100% turnover loses about 12% a year to costs. US stock-level cards should therefore be annual or quarterly rebalances of low-turnover fundamentals only. Higher-frequency ideas go to ETF cards (3 bp).

######## E. What to expect when the protocol is applied
- Chart-pattern and oscillator cards on liquid KRX stocks: mostly REJECT. This is the priced-in base rate implied by Bajgrowicz-Scaillet, the noise calibration, and 70 bp round trips.
- Tier A low-turnover fundamentals (cash profitability/quality, value) and possibly long-only low volatility: the realistic BUILD candidates. Their likely verdict is INSUFFICIENT DATA or REVISE rather than PASS, because KRX history only supports t of about 2 for SR of about 0.5.
- Korean reversal: BACKLOG pending D2.
- Momentum on KRX: Tier B (weak local evidence), with a crash stress test (D12).

####### Gaps
- OpenDART's coverage of structured financial-statement data was not verified; it may begin around 2015. If so, fundamental cards would have about 10 years of point-in-time history, which strengthens the INSUFFICIENT DATA and shrinkage logic.
- KRX's liquidation-trading procedure for delisting stocks and its tick-size table were not verified from KRX sources. The delisting stress values (-30%, -100%) are P4 assumptions (-30% echoes the common CRSP-literature replacement value, which P4 could not verify from Shumway's text).
- The cost-bucket numbers are P4 proposals, not estimates; D3 must calibrate them.
- The program-wide FDR re-scoring of existing cards needs every card's p-value, but the brief lists only some.


### [P4] Where and when it failed (Q8) (lines 561-611)

###### Q8. Where and when it failed (dated episodes, mandatory)

####### Takeaway
Failures cluster in five patterns:
1. technical rules after the early 1960s on mature indices;
2. high-turnover signals once costs are charged;
3. accounting anomalies outside their discovery samples;
4. crowded or levered factor books in liquidity shocks (August 2007; momentum crashes of 1932 and 2009);
5. on KRX in 2025-26, reversal, low-volatility and momentum quintiles each took deep, short drawdowns against an equal-weighted benchmark during the melt-up and the June-July 2026 crash.

####### Cited Findings
**Published episodes**

| Period | Market / strategy | What happened | Source |
|---|---|---|---|
| 1962-2011 | DJIA, 7,846 technical rules | Estimated share of outperforming rules is **zero** in every subperiod even before costs. Earlier subperiods' outperformance is wiped out by one-way costs of 16 bp (1897-1914), 35 bp (1915-1938) and 70 bp (1939-1962). Monthly selection of past winners loses in most recent periods | [Bajgrowicz-Scaillet, UNIGE](https://access.archive-ouverte.unige.ch/access/metadata/d1a36296-e8c4-423b-9ed9-9870cfc76d9c/download) |
| 1926-06/1963 (pre-discovery) and post-discovery to 2015 | US, 36 accounting anomalies | Only 8 of 36 significant before discovery and 2 of 34 after. Profitability 0.09%/m (t 0.86) and investment 0.02%/m (t 0.14) before 1963. Sharpe ratios -60% to -77% | [Linnainmaa-Roberts, NBER PDF](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf) |
| July-Aug 1932 | US winner-minus-loser momentum | Monthly WML returns of -60.98% (July) and -74.36% (Aug) during a bear-market rebound. The loser decile gained about 232% while winners gained about 32% | [Daniel-Moskowitz, NBER PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf) |
| Mar-Apr 2009 | US WML momentum | -42.28% (March) and -45.52% (April). Losers rose about 163% while winners rose about 8% | same |
| Week of 6 Aug 2007 | US quant long/short equity | Unprecedented losses. A mini-unwind on 1 August (10:45-11:30am) and a sustained unwind from the open on 6 August, attributed to deleveraging of similar portfolios (book-to-market, earnings momentum) and withdrawal of market-making capital from 8 August | [Khandani-Lo, NBER w14465](https://www.nber.org/papers/w14465) |
| 1963-2012 | US short-run reversal | 0.37%/m gross becomes **-1.28%/m net** (t -6.02). Microcap high-turnover strategies: 1.77%/m gross becomes -0.66%/m net | [Novy-Marx-Velikov, NBER PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) |
| 1998-2013 | AQR live trading, short-term reversal | Unprofitable after realized costs at about 300% monthly turnover, even at institutional cost levels | [Frazzini-Israel-Moskowitz PDF](http://spinup-000d1a-wp-offload-media.s3.amazonaws.com/faculty/wp-content/uploads/sites/3/2021/08/Trading-Cost-of-Asset-Pricing-Anomalies.pdf) |
| 1970-2016 | 4,267 US equity mutual funds | Realized momentum 1.28-1.54%/yr against 8.7-8.9%/yr on paper | [Patton-Weller WP](https://public.econ.duke.edu/~ap172/Patton_Weller_MF_25sep18.pdf) |
| Original papers vs replication | US idiosyncratic volatility | -1.06%/m (t -3.1) becomes -0.51%/m (t -1.62) with NYSE breakpoints and value weights | [Hou-Xue-Zhang, NBER PDF](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf) |
| BAB as constructed | US betting-against-beta | $1.05 per dollar of BAB sits in the bottom 1% of market cap; results are driven by non-standard beta estimation | [Novy-Marx-Velikov 2022, IDEAS](https://ideas.repec.org/a/eee/jfinec/v143y2022i1p80-106.html) |
| Quantopian OOS (at least 6 months) | 888 retail-built algorithms | Backtest Sharpe explains less than 2.5% of the variance in OOS Sharpe | [Wiecki et al., SSRN](https://ssrn.com/abstract=2745220) |
| Hedge-fund track records | Illiquid-strategy funds | Annualized SR overstated by up to 65% (4.03 vs a corrected 2.44) because of serial correlation | [Lo 2002 PDF](https://traders.studentorg.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf) |

**QUANTGEN's own record and context** (shared brief, run of 2026-09-27; local file [00_QUANTGEN_context.md](/home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/00_QUANTGEN_context.md))
- B3 time-series momentum on ten futures: OOS SR 0.08 [-0.27, 0.43], "no measurable edge after 2009".
- E5 sector momentum: 0.48 vs buy-and-hold 0.63, and below buy-and-hold after 50 bp per side.
- E8 KODEX/TIGER pairs: half-life of one session (bid-ask bounce) and losses at 2x costs. GLD/IAU: -2.28, with costs eating the spread.
- US 12-1 momentum (French WML): Sharpe 0.33 since 1990 and 0.02 since 2008.

**KRX data-lab quick-checks** (in-sample and descriptive; liquid universe; monthly quintiles; EW benchmark; 35 bp per side; local [E7_quickchecks](/home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/))
- 2015-07 to 2019-12, 12-1 momentum winners: cumulative -40.1%, against -30.1% for the EW benchmark; L/S gross SR -0.31.
- 2025-01-02 to 2026-06-22 (melt-up), 1-month reversal: L/S gross SR -1.24, net -1.88. Losers +16.0% against benchmark +43.3%; long-only net excess -26.3% cumulative.
- 2026-06-23 to 2026-07-30 (crash, 27 sessions), 12-1 momentum winners: -43.0%, against -27.1% for the benchmark. Losers fell 11.7%. This crash was **winner-led after a melt-up**, unlike the loser-rebound crashes of 1932 and 2009.
- 2026-07-31 to 2026-09-29 (rebound, 40 sessions), 60-day low-volatility long leg: +5.4%, against +28.3% for the benchmark; long-only net excess -19.4%.
- Calendar-year long-only net excess: 1-month reversal -15.4% (2025) and -14.0% (2026 YTD); 12-1 momentum -18.5% (2021); low volatility -18.3% (2020).

####### Inferences
- Every family QUANTGEN plans to build has at least one documented failure of 15-75% over one to two months, or of several years. The protocol must therefore report worst rolling 21- and 63-session net excess, and a stress replay of 2008-09, 2020-03, 2025-01 to 2026-06 and 2026-06-23 to 07-30. Means and Sharpe ratios alone are not enough.
- The 2026 KRX episodes come from data the data lab has **already looked at**. They are failure evidence, not out-of-sample tests (G8).
- 2007 and 2026 point the same way: crowding risk is about the **position** (a common factor book or common winners), not the signal's historical t-statistic. Concentration caps (for example Samsung and SK hynix) belong in the risk layer, as the macro panel decided.

####### Gaps
- No dated KRX failure from peer-reviewed Korean literature was retrieved, because the search budget was exhausted. The KRX episodes above come from the in-house quick-checks only.
- Magnitudes for the August 2007 unwind (percentage losses by strategy) were not in the fetched abstract.
- Neely-Weller-Ulrich (2009) on the decline of FX technical-rule profits could not be opened (404), so it is not used.


### [P4] Data-check requests (Q9) (lines 614-648)

###### Q9. Data-check requests for the data lab (exact tests)

####### Takeaway
Fourteen tests, in priority order. **D14 (the size of the gate under the null)** and **D3 (cost buckets)** come first because every other verdict depends on them. **D2 (KRX reversal net of costs)** decides the Korea weight conflict.

####### Cited Findings
Each test operationalizes a cited method: SPA, StepM and FDR (Q1); bucket costs and spread estimators (Q3); Lo/HAC and the stationary bootstrap (Q6); delisting returns (Q5).
- **D1. KRX technical-rule universe.**
  - Data: survivorship-free KRX marcap, 1996-2018 development.
  - Rules: about 2,000 STW-style rules (MA crossovers of 1-250 days, filter rules of 0.5-20%, channel breakouts of 5-250 days, RSI(2-30) thresholds, MACD (12/26/9 plus neighbours), Bollinger(20, k = 1.5-2.5)), applied long-or-flat to (a) a cap-weighted liquid KOSPI index proxy and (b) an EW liquid KOSDAQ index.
  - Execution: decide at the close of t, enter at the t+1 open, 3 bp per side (index/ETF) and 35 bp per side (stock-level).
  - Statistics: Hansen SPA consistent p (stationary bootstrap, Politis-White block, 5,000 replications); StepM survivors at FWER 5%; BH count at q = 10%; Bajgrowicz-Scaillet monthly persistence test. Report by 5-year subperiod.
- **D2. KRX reversal, net.** 1-week (5-session) and 1-month reversal, liquid universe, 2000-2026, long losers minus the EW liquid benchmark.
  - Entry at the t+1 open; D3 bucket costs plus the sell tax in force each year; banded variant (enter at the bottom 10%, hold until the 30th percentile).
  - Report gross, net, break-even cost per side, the short-ban regime split, and EW vs capped-VW. Replicate the shared brief's -2.95%/m Korean figure under VW.
- **D3. Cost buckets.** Corwin-Schultz and Abdi-Ranaldo spread estimates for all stocks, 2000-2026, by 20-day traded-value bucket and year. Validate against KIS quote snapshots (bid/ask at 15:20 and at the close) for at least 20 days in 2026. Output: median effective half-spread per bucket and year, to replace the P4 placeholder table.
- **D4. Price-limit realism.** Frequency of days with High = Low = Close at the upper or lower limit, by bucket and year. Re-run the event cards (golden cross, volume spike, limit-up) excluding locked-limit entries, and with next-open entry.
- **D5. Delistings.** Identify every code that disappears in 1995-2026. Classify: merger or code change vs negative (administrative or warning flags in the last 12 months). Re-run the E7 factors under (a) current handling, (b) -30% on negative exits, (c) -100% on negative exits that had a prior administrative flag. Report the change in long-leg and L/S returns.
- **D6. Serial correlation.** ACF at lags 1-10 of daily net excess returns of each E7 portfolio, by size bucket. Lo-corrected annualized SR vs naive sqrt(252) scaling. Monthly-return SR vs daily.
- **D7. Weighting.** Re-run the E7 factors with capped value weights (cap at the 80th market-cap percentile) and report sign agreement with EW by subperiod.
- **D8. Power and MinTRL.** For each candidate card: development SR, skew and kurtosis; MinTRL at its tier hurdle (t = 2.0 / 3.0) and at the haircut SR; flag INSUFFICIENT DATA where MinTRL exceeds the available years.
- **D9. Contamination log.** List every signal family and date range already examined in the E7 quick-checks (2013/2014-2026). Mark the 2019-2026 holdout as consumed for those families and start the prospective-incubation clock from 2026-10-01.
- **D10. Step 8 false-pass rate on KRX.** Stationary-bootstrap a de-meaned (zero-edge) version of each candidate card's daily net excess returns 10,000 times. Report P(at least 60% of years positive) against the proposed "at least 2 of 3 subperiods" rule.
- **D11. Re-score the existing 34 cards** with Holm and with BH (q = 0.10) on their one-sided benchmark p-values, and on Sharpe-vs-zero p-values. List which of the 5 PASSes survive.
- **D12. 2026 momentum crash stress.** Apply the macro panel's own-volatility scaling (sigma126, 12% target, cap 1.0) and the Daniel-Moskowitz bear-state gate to KRX 12-1 momentum, 2025-01 to 2026-09. Did exposure fall before 2026-06-23? Report drawdown with and without the overlay.
- **D13. Decay calibration on French data.** For HML, UMD, RMW and CMA, compute the Sharpe ratio before vs after publication (1992, 1993, 2015) and after the original sample's end, with HAC SEs. Note that the local French file ends in 2018, so RMW/CMA post-publication evidence is about 3 years only.
- **D14. Size of the gate.** Simulate 1,000 zero-edge strategies with KRX-like properties (stationary-bootstrap resampling of de-meaned real card returns, keeping their turnover, skew and autocorrelation) through all nine gate steps with the current settings. Estimate the false-PASS rate per card, then repeat with protocol P4-TF-1. Target: a false PASS of at most 5% per card.

####### Inferences
- D14 is the single most informative test. It turns the gate from a collection of literature-inspired rules into a test of known size. D3 is a prerequisite for every net-of-cost verdict on stock cards.

####### Gaps
- D3 requires KIS quote snapshots, which are not in the listed historical datasets. Validation may need prospective collection.
- D5 depends on whether the marcap data carries delisting reasons; if not, the classification must use flag history alone.


### [P4] Claims ledger (lines 651-696)

###### Q10. Claims ledger (mandatory)

####### Takeaway
30 claims. In the implication column, "BUILD-candidate (gate)" means build the item into the gate or protocol. For signal claims, the implication names the card decision.

####### Cited Findings

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P4-C01 | Once the search is counted, a new signal needs t of about 3.0-3.8, not 2.0. | HLZ: t > 3.0 for new factors (US literature, 1967 onward). CGS: more than 2m random strategies on US data; MHT thresholds 3.8 (TS alpha) and 3.4 (FM); about 45% false rejections without correction. Gross, IS | [HLZ, NBER w20592](https://www.nber.org/papers/w20592); [CGS, RFS 2020, IDEAS](https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2134-2179..html) | T1 | Two independent frameworks agree; RFS-published | A t = 3 rule rejects true but modest premia (low power, C23) | BUILD-candidate (gate): Tier B t >= 3.0, B+ t >= 3.4/3.8 |
| P4-C02 | Sharpe haircuts for multiple testing are nonlinear, not a flat 50%. | Above 50% for SR < 0.4; at most 25% for SR > 1.0. 50 tests: E/P (SR 0.43) about 50% vs BAB (0.78) 7.9%. N = 200: SR 0.75 becomes 0.32. US, IS | [Harvey-Liu JPM 2015, Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF) | T1 | Depends on assumed test correlation (rho = 0.2 default) | A 50% rule coincides with BHY only at about SR 1.0 / 240 months / 316 tests | BUILD-candidate (gate): report the BHY haircut; replace the flat step 9 (see C11) |
| P4-C03 | Large universes of classic technical rules have no edge on the DJIA after 1962, even at zero cost. | 7,846 rules, DJIA daily 1897-2011: FDR share of outperformers 0 in every post-1962 subperiod. Earlier gains removed by 16/35/70 bp one-way (1897-1914/1915-38/1939-62). Monthly persistence OOS negative | [Bajgrowicz-Scaillet JFE 2012, EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:106:y:2012:i:3:p:473-491); [UNIGE full text](https://access.archive-ouverte.unige.ch/access/metadata/d1a36296-e8c4-423b-9ed9-9870cfc76d9c/download) | T1 | Generalizes STW 1999; OOS persistence test; costs included | The only positive evidence is pre-1962 | DROP generic chart-rule cards as BUILD; test only through D1 (SPA/StepM) |
| P4-C04 | Where technical profits survive snooping checks, they sit in young markets and earlier decades. | Hsu-Kuan: Reality Check + SPA; significant only for NASDAQ Composite and Russell 2000, not DJIA or S&P 500; net of costs. Park-Irwin: 56/95 modern studies positive, profits mainly until the early 1990s, most studies flawed | [Hsu-Kuan JFEc 2005, IDEAS](https://ideas.repec.org/a/oup/jfinec/v3y2005i4p606-628.html); [Park-Irwin JES 2007, IDEAS](https://ideas.repec.org/a/bla/jecsur/v21y2007i4p786-826.html) | T1 | Snooping-adjusted (Hsu-Kuan); survey evidence mixed | Positive survey results suffer from ex post selection | BACKLOG: KOSDAQ-only technical test via D1; no KOSPI200 technical cards |
| P4-C05 | DSR >= 0.95 with honest trial counts already implies t of about 3.2-3.7 for 9-27 independent configurations. | BLdP example: best SR 2.5 on 1,250 daily obs fails (DSR about 0.90) and would pass with 46 trials (0.9505). P4: t_req of about E[max of N] + 1.645 = 2.50 (N 3), 3.17 (9), 3.67 (27), 4.18 (100) | [BLdP JPM 2014, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); [author PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) | T1 (formula); P4 computation | Formula reproduced by P4; parameter details of the paper's example uncertain | Gaming via understated or over-correlated N_eff | BUILD-candidate (gate): keep step 3; registry for N_eff (floor 3; TradingView ideas N >= 100) |
| P4-C06 | Pure noise produces "SR above 1" backtests after modest searches. | Expected best annualized SR of N zero-edge configs: 1.13 (N 100, 5 y), 1.46 (N 1,000, 5 y), 0.89 (N 100, 8 y). IID, own computation | [BLdP formula, author PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf); [BBLZ AMS 2014, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659) | T1 formula; P4 computation | Exact under IID normal; real configs correlated (lower N_eff) | Retail backtests rarely report N | CONTEXT: why TradingView SRs are not evidence |
| P4-C07 | Overfit backtests are common, hold-out testing is unreliable, and overfitting can make OOS returns negative. | PBO = P(IS-best config ranks below the OOS median); CSCV with S = 16 (C(16,8) = 12,870 splits). Hold-out flaws listed (reuse, under 1,000 obs, ignores N). Under memory effects, negative expected OOS | [BBLZ, SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253); [author PDF](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf); [AMS 2014, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659) | T1 | Widely used; simulation-based | Not applicable to single-config replications | BUILD-candidate (gate): keep step 4; add degradation slope and P(loss) |
| P4-C08 | CPCV beats walk-forward at preventing false discoveries. | Synthetic markets (Heston, Merton jumps, drift-burst, regime switching): CPCV has lower PBO and better DSR than WF, K-fold and purged K-fold; WF shows more temporal variability | [Arian-Norouzi-Seco, SSRN 4686376](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4686376) | T1 (journal: Knowledge-Based Systems, 2024) | Synthetic data only; not replicated on real KRX | Untested on real data | BUILD-candidate (gate): add CPCV (45 splits, 9 paths) next to step 1 |
| P4-C09 | Microcap-neutral construction knocks out most published anomalies. | 447 US anomalies, 1967-2014, NYSE breakpoints + VW: 64% fail t >= 1.96, 85% fail t >= 3. Trading frictions 93%, intangibles 75%, momentum 35% insignificant. Microcaps 61% of firms, 3.28% of cap. Gross | [HXZ RFS 2020, NBER w23394](https://www.nber.org/papers/w23394); [NBER PDF](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf) | T1 | Disputed by JKP/CZ on construction (C10) | IVOL -1.06%/m (t -3.1) becomes -0.51%/m (t -1.62) | BUILD-candidate (gate): liquid screen + EW/VW sign agreement (G5) |
| P4-C10 | Built as the papers built them, published predictors are mostly statistically real. | CZ: 98% of 161 clear predictors t > 1.96 (slope 0.90, R² 83%). JKP: 84.9% US CAPM-alpha replication, 77.3% after BY, 84.9% world. CZ publication bias: returns 12% below IS; t 1.8 suffices. US, IS | [CZ, FEDS 2021-037](https://www.federalreserve.gov/econres/feds/files/2021-037pap.pdf); [JKP, NBER w28432](https://www.nber.org/papers/w28432); [CZ pub-bias, FEDS](https://www.federalreserve.gov/econres/feds/publication-bias-and-the-cross-section-of-stock-returns.htm) | T1 | JF 2023 (JKP); open-source code (CZ) | Replication of the sign, not the magnitude | BUILD-candidate (gate): Tier A t >= 2.0 for published, internationally replicated anomalies |
| P4-C11 | US anomaly returns fall about a quarter OOS and about a third to a half after publication. | MP: 97 predictors, average 0.582%/m IS; -26% OOS pre-publication, -58% post-publication (US, data to about 2013, gross). JKP: alpha 0.45 to 0.31%/m post-publication (-31%) | [MP, author PDF](https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf); [JKP NBER PDF](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf) | T1 | Replicated across studies | Larger decline for high-IS-return predictors | BUILD-candidate (gate): step 9 becomes an alpha haircut, h = 0.5 (IS) or 0.3 (post-pub window) |
| P4-C12 | Accounting anomalies lose most of their Sharpe outside discovery samples. | 36 anomalies: IS 0.28%/m (t 8.67); pre-1963 0.08%/m (8 of 36 significant); post-discovery 0.10%/m (2 of 34). SR -60 to -77%. Profitability pre-1963 0.09%/m (t 0.86). US 1926-2015, gross | [Linnainmaa-Roberts, NBER PDF](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf) | T1 | RFS 2018; true OOS in both directions | Profitability and investment insignificant before 1963 | CONTEXT: quality prior is not ironclad; must pass the KRX holdout |
| P4-C13 | Outside the US, published anomalies show no reliable post-publication decline. | 241 anomalies, 39 markets, more than 2m anomaly-country-months: only the US shows a reliable decline; interpreted as segmentation / mispricing | [Jacobs-Müller JFE 2020, IDEAS](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html) | T1 | Large international sample | Korea-specific estimate not retrieved | CONTEXT: KRX premia may last longer; hurdles not loosened |
| P4-C14 | Theory does not protect a predictor from post-sample decay. | 29,000 data-mined ratios vs peer-reviewed: about 50% of predictability remains post-sample for both; risk theory gives no protection (US) | [Chen-Lopez-Lira-Zimmermann, arXiv](https://arxiv.org/abs/2212.10317) | T1 (working paper) | Broad data-mining benchmark | Not yet peer-reviewed in final form | BUILD-candidate (gate): mechanism lowers the t-hurdle, not the haircut |
| P4-C15 | Turnover decides whether anomalies survive costs; reversal-type signals do not. | US 1963-2012, Gibbs spreads: momentum 133 to 68 bp/m (t 2.45); value 47 to 42; GP 40 to 37; short-run reversal 37 to -128 bp/m (t -6.02); industry momentum and seasonality negative. Below 50%/m turnover mostly survives; banding cuts turnover about 41% | [NMV RFS 2016, NBER w20721](https://www.nber.org/papers/w20721); [NBER PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) | T1 | Corroborated by FIM's live STR (C17) | Microcap high-turnover 1.77 to -0.66%/m net | BACKLOG Korea reversal (weight 3 to pending D2); BUILD-candidate low-turnover fundamentals with banding |
| P4-C16 | The average anomaly's realistic net expected return is a few bp per month. | 204 anomalies, spreads + post-pub + post-2000 era: about 4 bp/m; best about 10 bp; combinations about 20 bp; excludes price impact. FEDS WP version: 120 anomalies, 8 bp | [Chen-Velikov JFQA 2023, Cambridge](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/zeroing-in-on-the-expected-returns-of-anomalies/945133D5A3ECEEAF466AEE91551FD225); [FEDS page](https://www.federalreserve.gov/econres/feds/zeroing-in-on-the-expected-returns-of-anomalies.htm) | T1 | Published version supersedes the WP | Spread-based costs may overstate institutional costs (C17) | CONTEXT: expect INSUFFICIENT DATA or REVISE for most KRX stock cards |
| P4-C17 | Institutional live costs are far below academic estimates, but realized fund returns still lose most of momentum. | FIM: $1.7tn live trades, 1998-2016, mean MI 9.97 bp (large 8.90, small 18.95); US break-even size $275bn, value $214bn, momentum $56bn; STR unprofitable. Contradicted in realized terms by Patton-Weller: 4,267 funds 1970-2016, momentum 1.3-1.5%/yr realized vs 8.7-8.9% paper; value 2.3-2.6% vs 5.2-6.7% | [FIM AQR page](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs); [FIM anomalies PDF](http://spinup-000d1a-wp-offload-media.s3.amazonaws.com/faculty/wp-content/uploads/sites/3/2021/08/Trading-Cost-of-Asset-Pricing-Anomalies.pdf); contradicted by [Patton-Weller JFE 2020, EconPapers](https://econpapers.repec.org/article/eeejfinec/v_3a137_3ay_3a2020_3ai_3a2_3ap_3a515-549.htm) | T1/T2 | Conflict reconciled by fund size (smaller funds capture more) | STR fails in both | CONTEXT: capacity not binding for a retail investor; costs and implementation are |
| P4-C18 | With costs included, the cash-profitability Fama-French model beats high-turnover factor models. | 205 anomalies: q-factor and BS6 look best gross but fail to span the net frontier; FF5 with cash profitability significantly better net | [Detzel-NM-V JF 2023, IDEAS](https://ideas.repec.org/a/bla/jfinan/v78y2023i3p1743-1775.html) | T1 | JF-published | US only | BUILD-candidate: cash-profitability/quality card, Tier A |
| P4-C19 | Long-only investors get about half of momentum and 60% of value; short legs carry sentiment-driven overpricing. | Israel-Moskowitz: long side = almost all of size, 60% of value, half of momentum (86 y US + international). SYY: short legs more profitable after high sentiment; long legs unrelated | [Israel-Moskowitz JFE 2013, IDEAS](https://ideas.repec.org/a/eee/jfinec/v108y2013i2p275-301.html); [SYY JFE 2012, IDEAS](https://ideas.repec.org/a/eee/jfinec/v104y2012i2p288-302.html) | T1 | Long sample; multiple markets | KRX short-leg share unknown (D2/D7) | BUILD-candidate (gate): long-only excess vs EW benchmark is the primary statistic |
| P4-C20 | KRX short selling was fully or partly banned for most of 2020-2025, with full resumption from 2025-03-31. | Bans 2008-10 to 2009-05, 2011-08 to 2011-11, 2020-03-16 to 2021-05-03 (then K200/KQ150 only), 2023-11 to 2025-03-31. From 2025-03-31: all stocks, NSDS, 105% collateral, 90-day repayment renewable to 12 months | [FSC press release](https://www.fsc.go.kr/eng/pr010101/84220); [KCMI report](https://www.kcmi.re.kr/common/downloadw?fid=27533&fgu=002001&fty=004003) | T1 | Official | FSC and KCMI differ by 2 days on the 2023 start | BUILD-candidate (gate): short-ban regime split; L/S as diagnostic only |
| P4-C21 | The KRX sell-side tax rose to 0.20% on KOSPI and KOSDAQ from 2026-01-01. | KOSPI 0.05% + 0.15% rural tax = 0.20% (2025: 0.15%); KOSDAQ and K-OTC 0.20% (from 0.15%); KONEX 0.10% | [Herald Business, Dec 2025](https://biz.heraldcorp.com/article/10627001) | T2 | Major press reporting a government decree; not checked against the decree text | Historical rates differ (about 0.30% in 2019 per the article) | BUILD-candidate (gate): time-varying statutory tax in the cost model; 35 bp flat leaves about 25 bp non-tax |
| P4-C22 | Sharpe ratios are imprecise, and serial correlation can overstate annualized SR by up to 65%. | SE = sqrt((1 + SR²/2)/T); e.g. SR 1.5, 60 months: 0.188. MBS fund annual SR 4.03 vs corrected 2.44. P4: SE about 1.41 for one 126-session window | [Lo FAJ 2002, PDF](https://traders.studentorg.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf) | T1 | Standard result | Fat tails widen SEs further (Mertens) | BUILD-candidate (gate): PSR/HAC in step 2; infer only on concatenated OOS or CPCV |
| P4-C23 | Realistic net factor Sharpes cannot reach t = 3 on KRX history alone. | MinTRL (monthly, skew -0.72, kurt 5.78): SR 1.0 needs 3.62 y vs 0 and 14.23 y vs 0.5. P4: SR 0.5 needs 16 y (t 2) and 36 y (t 3); P(t >= 3 over 16 y with true SR 0.5) = 0.16 | [BLdP Sharpe frontier, author PDF](https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf) | T1 formula; P4 computation | Reproduced by P4 | Shrinkage to global evidence needed | BUILD-candidate (gate): INSUFFICIENT DATA verdict + JKP-style shrinkage for Tier A |
| P4-C24 | Comparing a strategy with its benchmark needs a studentized time-series bootstrap, not Jobson-Korkie. | JK/Memmel invalid with heavy tails or time-series dependence; studentized block bootstrap CI for the SR difference has better finite-sample size | [Ledoit-Wolf JEF 2008, IDEAS](https://ideas.repec.org/a/eee/empfin/v15y2008i5p850-859.html); [Politis-White 2004, IDEAS](https://ideas.repec.org/a/taf/emetrv/v23y2004i1p53-70.html) | T1 | Standard method | Fixed short blocks under-cover for 21-session holds | BUILD-candidate (gate): step 5 test; blocks >= max(Politis-White, 2 x holding period) |
| P4-C25 | TradingView backtests default to zero costs and are exposed to repainting and look-ahead. | `commission_value` default 0; `slippage` default 0; next-bar-open fills by default; intrabar path assumed; over 95% of indicators repaint in some form; `lookahead_on` without offset leaks future data | [TV declaration statements](https://www.tradingview.com/pine-script-docs/language/declaration-statements/); [TV strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/); [TV repainting](https://www.tradingview.com/pine-script-docs/concepts/repainting/) | T2 (primary platform docs) | Platform's own statements | Survivorship handling undocumented | DROP: never import TradingView metrics; re-implement and count N >= 100 |
| P4-C26 | A win rate without the payoff ratio is uninformative, and backtest SR barely predicts live SR. | Driftless price: any +a/-b bracket wins b/(a+b) of the time with zero gross expectancy; 90%-win +1/-9% loses 0.70% per trade at 70 bp round trip (P4). 888 Quantopian algos: backtest SR R² < 0.025 for OOS SR | [Wiecki et al., SSRN](https://ssrn.com/abstract=2745220); [CFTC 4.41, eCFR](https://www.ecfr.gov/current/title-17/chapter-I/part-4/subpart-C/section-4.41) | T1/T2; P4 computation | Algebraic identity; one large live sample | Real drift changes the arithmetic | BUILD-candidate (gate): report net expectancy per trade with a bootstrap CI; ignore "success rate" |
| P4-C27 | Gate step 8 (>= 60% of years positive) admits many zero-edge strategies. | P(pass) under zero edge: 36% (8 y), 38% (10 y), 25% (20 y); P4 binomial computation, normal annual returns | P4 computation (no external source) | Derived | Exact under independence of years | Autocorrelated years raise the false-pass rate | BUILD-candidate (gate): step 8 becomes report-only; replace with >= 2 of 3 subperiods + regime split (D10) |
| P4-C28 | Card-level testing without program-wide control yields false passes. | 34 cards at one-sided p <= 0.10 expect about 3.4 false passes if all null. C3's benchmark p 0.04 fails Bonferroni across 16 trading cards (threshold 0.006), while its SR-vs-zero (t of about 3.5) survives | [QUANTGEN brief, local file](/home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/00_QUANTGEN_context.md); [Romano-Wolf, IDEAS](https://ideas.repec.org/a/ecm/emetrp/v73y2005i4p1237-1282.html) | Derived from T1 methods | Depends on p-values not all listed in the brief | Re-scoring may demote existing PASSes | BUILD-candidate (gate): BH q = 0.10 per release; Holm for displayed cards; run D11 |
| P4-C29 | Momentum fails in fast, deep crashes, and the 2026 KRX crash was winner-led, a pattern unlike 1932 and 2009. | US WML: -61%/-74% (Jul/Aug 1932), -42%/-46% (Mar/Apr 2009), loser rebounds. KRX 2026-06-23 to 07-30 (in-house, IS): winners -43.0% vs EW -27.1%, losers -11.7% | [Daniel-Moskowitz NBER PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf); [E7 quick-check, local](/home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_factor_quickcheck.csv) | T1 + in-house (T3-equivalent, descriptive) | US crash mechanism published; KRX episode IS only | Bear-state gate may not fire after melt-ups | CONTEXT: flag to macro overlay; run D12 before any KRX momentum card |
| P4-C30 | Missing delisting returns bias anomaly backtests, in either direction. | CRSP lacks correct delisting returns for most negative delistings since 1962, and the omitted returns are large (Shumway). Including delisting firm-years raises earnings, cash-flow and B/M strategy returns and lowers accruals' (BMP). HXZ replace missing values with 60-month type/exchange means | [Shumway JF 1997, IDEAS](https://ideas.repec.org/a/bla/jfinan/v52y1997i1p327-40.html); [BMP JAE 2007, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=949601); [HXZ PDF](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf) | T1 | Established | KRX delisting treatment untested | BUILD-candidate (gate): delisting rule + D5 stress; point-in-time DART (rcept_dt + 1) |

####### Inferences
- The claims that change gate mechanics (C01, C05, C11, C15, C19-C21, C24, C27, C28, C30) should be decided together, because they interact. For example, tiered hurdles combined with long-only primary statistics and bucket costs will reject many more cards than any single change would. D14 measures the combined size of the gate.

####### Gaps
- Tiers for in-house quick-checks and own computations are labeled "derived" or "in-house" because the T1/T2/T3 scale does not cover them.



---

## P5_machine_learning_arxiv.md

### [P5] Persona and position summary (lines 1-18)

##### P5: Machine learning and AI applied to technical and fundamental return predictors

As of 2 October 2026. Panel: Professors. Claim IDs P5-C01 to P5-C30 (ledger in section 10).

**Persona (a fictional composite, not a real person).** P5, "Professor of Machine Learning in Finance", holds a joint appointment in computer science and finance and is active on arXiv q-fin and cs.LG. P5 argues from statistical learning theory and out-of-sample (OOS) evaluation. Every backtest is treated as a prediction problem that can be broken by leakage, by multiple testing or by costs. ML is judged on net, liquid, post-publication and post-training-cutoff evidence, never on R², F1, hit rates or gross equal-weighted Sharpe.

**Position summary (P5 speaking).**
1. The strongest evidence (Gu-Kelly-Xiu 2020; Freyberger-Neuhierl-Weber 2020; Chen-Pelger-Zhu 2024) shows that regularized nonlinear models roughly double gross OOS predictive R² and long-short Sharpe over small linear benchmarks in US stocks. These are shallow models: trees and nets with 1 to 3 layers. The gain comes from interactions among a few price-trend, liquidity and volatility characteristics, not from depth.
2. The gains are mostly gross. Profits attenuate considerably once microcaps, distressed names and high-volatility episodes are removed, and they deteriorate further under realistic costs (Avramov-Cheng-Metzker 2023). US ML portfolios built on 1-month forecasts have earned close to zero net of costs since 2004 (Blitz et al. 2023). What keeps ML profitable after costs is longer forecast horizons, trading bands and cost-aware portfolio construction (Jensen-Kelly-Malamud-Pedersen).
3. The "virtue of complexity" result is substantially undercut. Nagel shows its market-timing gains are mechanically produced volatility-timed momentum. Buncic shows plain linear models with an intercept earn Sharpe ratios up to 40% higher.
4. Daily deep-learning and ensemble stat-arb on S&P 500 stocks decayed to about zero net after 2010. Image-CNN price-pattern signals are spectacular equal-weighted but modest value-weighted, and their weekly versions trade very heavily.
5. LLM news signals are real after the training cutoff, but they are fast (absorbed within about two days) and tilted toward small stocks and the short leg. They decay as adoption rises (Sharpe 6.54 in late 2021 to 1.22 in early 2024) and are unprofitable at 20 bp costs. Backtests inside a model's training window are contaminated by memorization, and masking firm names does not remove it.
6. QUANTGEN's constraints work against ML: KRX stocks cost 35 bp per side, only about 11 years of point-in-time OpenDART fundamentals exist, and the gate counts every hyperparameter configuration as a trial. Under these conditions I expect the net uplift of a gradient-boosting or neural combiner over a well-built equal-weight composite to be about 0 to +0.01 IR (plausible range -0.15 to +0.10) before the 60% live haircut, and about zero after it. That is far too small for the gate to detect.
7. My verdict on the stock-level layer:
   - **BUILD now:** the equal-weight z-score composite; a ridge / rolling Fama-MacBeth challenger shrunk toward the prior weights; and a leakage-safe ML evaluation harness.
   - **BACKLOG:** gradient-boosting and neural combiners, run as shadow challengers with explicit promotion criteria.
   - **DROP:** daily deep sequence, limit-order-book and LLM-news strategies for KRX stocks at current costs.


### [P5] Where and when it failed (section 8) (lines 335-373)

###### 8. Where and when it failed (mandatory: dated episodes)

####### Takeaway
ML and AI return-prediction failures cluster in three patterns:
- decay after about 2003-2010 in liquid US markets once costs are charged;
- collapse when the model is moved off its training regime or benchmark dataset;
- crowding events and look-ahead artefacts that make backtests unrepeatable.

####### Cited Findings

| # | Period | Market / data | Method | What failed (numbers) | Source |
|---|---|---|---|---|---|
| 1 | Jan 2010 to Oct 2015 | S&P 500 constituents, daily | RF/GBT/DNN ensemble on lagged returns | Negative returns after 5 bp per half-turn, against above 200% a year (1992-2001) and 22% a year (2001-2008), net | [Krauss-Do-Huck](https://www.econstor.eu/bitstream/10419/130166/1/856307327.pdf) |
| 2 | 2010 to 2015 | S&P 500 constituents, daily | LSTM | Profitability around zero after costs, against 0.46% a day (Sharpe 5.8) pre-cost over the full sample | [Fischer-Krauss](https://www.sciencedirect.com/science/article/abs/pii/S0377221717310652) |
| 3 | 2003 to 2014 | US non-microcaps | Joint test of 94 characteristics | Only 2 characteristics independent; hedge returns insignificant | [Green-Hand-Zhang](https://ideas.repec.org/a/oup/rfinst/v30y2017i12p4389-4436..html) |
| 4 | 2004 to 2021 | US | ML with 1-month forecast horizon | Net of costs close to zero | [Blitz et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4474637) |
| 5 | Week of 6 Aug 2007 (unwind July to end-2007) | US quant equity | Contrarian / market-making and factor books | Simulated market-making strategy significantly negative that week, positive before and after; deleveraging of similar portfolios | [Khandani-Lo](https://www.nber.org/papers/w14465) |
| 6 | 2021Q4 to May 2024 | US, overnight news | GPT headline long-short | Sharpe 6.54, 3.68, 2.33, 1.22 by period; unprofitable at 20 bp costs | [Lopez-Lira-Tang v6](https://arxiv.org/html/2304.07619v6) |
| 7 | 2015 to Sep 2021 against Oct 2021 to Dec 2022 | US, S&P 500 headlines | GPT-3.5 sentiment | 77.27 bp a day in-sample (inside training window) to 6.07 bp a day OOS, original headlines | [Glasserman-Lin](https://arxiv.org/pdf/2309.17322) |
| 8 | FI-2010 benchmark to 2021-22 NASDAQ | Limit-order book | 13 deep-learning models | Best F1 82.6% to about 63%; others 48-61% on new data; no costs in backtest | [LOBCAST](https://link.springer.com/article/10.1007/s10462-024-10715-4) |
| 9 | 1926-2020 sample, synthetic tests | US market timing | RFF "complex" ridge | On artificial reversal data, alpha -0.143 a year (t -1.84); the effect reappears on i.i.d. returns; linear models with an intercept earn Sharpe up to 40% higher | [Nagel](https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/f/575/files/2025/07/Complexity_2.pdf); [Buncic](https://www.danielbuncic.com/) |
| 10 | 120-month windows | 8 USD currency pairs | Ridge-RFF | Uniformly worse than linear; underperforms the random walk | [Kılıç FEDS 2025-089](https://www.federalreserve.gov/econres/feds/files/2025089pap.pdf) |
| 11 | 1981-2020 | US | Cost-agnostic Markowitz-ML | Gross Sharpe 2.00 turns into negative net returns | [Jensen-Kelly-Malamud-Pedersen](https://afajof.org/management/viewp.php?n=32368) |
| 12 | Earnings calls Sep-Nov 2019, asked about 2020 | US | Llama-2 70B | 6.8% of generations mention COVID-19 (future leakage); masked firms re-identified 70% of the time | [Sarkar-Vafa](https://openreview.net/pdf?id=fn9cJkB86T) |
| 13 | Before vs after publication | US, 8 popular factors | Factor premia | 5.8% a year falls to 2.4% a year | [Arnott-Beck-Kalesnik via AHM](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf) |
| 14 | 447 published anomalies | US | Replication with NYSE breakpoints, value-weighted | 64% insignificant at 5%; 85% fail t>3; 93% of liquidity variables fail | [Hou-Xue-Zhang](https://www.nber.org/papers/w23394) |
| 15 | Korea, 2000s-2020s | KRX | US-trained image CNN | Described as significantly weaker in Korea (Korea-specific numbers not extracted) | [Jeong-Byun-Kim](https://www.sciencedirect.com/science/article/abs/pii/S0275531925004878) |
| 16 | Civil-war prediction literature (non-finance) | — | Complex ML against logistic regression | After leakage was fixed, ML no better than logistic | [Kapoor-Narayanan](https://reproducible.cs.princeton.edu/) |

####### Inferences
- The recurring failure mechanism is a fast signal plus turnover plus a modern cost or liquidity regime. ML models that load on short-term reversal and liquidity inherit the crowding risk of August 2007 and the post-2010 decay.
- A model that looks excellent on a benchmark dataset or inside an LLM's training window should be expected to lose a large fraction of its edge on genuinely new data (rows 7 and 8).

####### Gaps
- I found no dated Korean ML failure episode, such as a live Korean ML fund drawdown, in peer-reviewed sources.
- The 2009 momentum crash is relevant to ML models that load on momentum but is covered by the macro panel.

---


### [P5] QUANTGEN translation (section 9) (lines 374-526)

###### 9. QUANTGEN translation: model choice, required protocol, BUILD vs BACKLOG, expected net uplift

####### Takeaway
- **BUILD now:**
  - the equal-weight z-score composite (technical plus fundamental) as the first stock-level card;
  - a ridge or rolling Fama-MacBeth challenger shrunk toward the prior per-market weights;
  - an ML-grade harness: purged and embargoed walk-forward, trial counting, cost-aware evaluation and turnover controls.
- **BACKLOG:** gradient-boosting and neural combiners as non-gating shadow challengers with explicit promotion criteria.
- **DROP:** daily deep sequence, image, order-book and LLM-news strategies for KRX stocks at current costs.
- **Expected uplift (P5 judgment).** Net uplift of a GBRT or neural combiner over the composite in liquid KRX stocks is about 0 to +0.01 IR (plausible range -0.15 to +0.10) before the 60% live haircut, and about zero after it. That is undetectable by the gate with the data available.

####### Cited Findings (inputs to the decision)
- **QUANTGEN's operating constraints.**
  - Costs: KRX stocks 35 bp per side (70 bp stressed); US via KIS 50 bp (100 bp).
  - Gate: purged walk-forward of 756 in-sample and 126 OOS sessions, embargo equal to the holding period; deflated Sharpe at least 0.95 with every revision counted as a trial; PBO via CSCV; plateau test; at least 60% of years positive; 60% live haircut.
  - No stock-level cross-sectional card exists yet — QUANTGEN context brief (local file `00_QUANTGEN_context.md`)
- **OpenDART history.** The single-company key-accounts API provides financial data only from the 2015 business year — [OpenDART guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016)
- **Horizon and trading rules.** Longer forecast horizons and efficient trading rules turn near-zero net ML into significant positive net returns — [Robeco](https://www.robeco.com/en-us/insights/2023/07/the-term-structure-of-machine-learning-alpha)
- **Cost-aware learning.** It gives a net Sharpe of 1.38, against negative net returns for cost-agnostic ML — [AFA](https://afajof.org/management/viewp.php?n=32368)
- **Combining signals.** Combining characteristics nets trades and makes more of them useful after costs (6 to 15) — [EconPapers](https://econpapers.repec.org/article/ouprfinst/v_3a33_3ay_3a2020_3ai_3a5_3ap_3a2180-2222..htm)
- **1/N.** It is hard to beat without very long samples — [RePEc](https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html)
- **Shallow beats deep.** GKX's neural networks peak at three layers — [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf). In Korea, LightGBM/GBRT were best among tested models — [Springer](https://link.springer.com/article/10.1007/s42952-023-00245-0)
- **Pooling helps short samples.** A pooled or "universal" model beats asset-specific models — [Sirignano-Cont](https://arxiv.org/abs/1803.06917). US-to-foreign transfer lifts country Sharpe on average — [JKX](https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf)
- **Complex models must earn their place.** AHM require that a more elaborate model beat simpler ones by an economically significant margin and stay interpretable — [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf)

####### Inferences

**(a) Model ladder and verdicts**

| Level | Model | What the evidence says | QUANTGEN verdict |
|---|---|---|---|
| L0 | Equal-weight rank/z-score composite, signs fixed in advance, per-market prior weights (0-3 scale) | 1/N robustness; Lewellen composite works OOS; one trial | **BUILD now** (baseline and production candidate) |
| L1 | Rolling 36-60 month Fama-MacBeth slopes, or ridge on rank features, shrunk toward L0 weights | Cheap; tests the prior per-market weights; few trials | **BUILD now** (challenger) |
| L2 | Elastic net on many features | GKX R² 0.11%, below OLS-3; little gain | Optional diagnostic only |
| L3 | Shallow GBRT/LightGBM (depth at most 3, monotone constraints, early stopping on purged validation) | Best in Korea (Choi et al.); GKX R² 0.34%; gains mostly gross and short-horizon | **BACKLOG** (shadow challenger) |
| L4 | MLP with at most 3 layers, ensemble of at least 5 seeds | GKX NN3 0.40%; peak at 3 layers; data-hungry | **BACKLOG** (after L3) |
| L5 | LSTM/CNN price patterns, order-book deep learning, daily LLM news | Post-2010 decay, turnover far beyond 35 bp economics, look-ahead risk | **DROP** for KRX stocks; LLM-on-DART at a monthly horizon BACKLOG |

**(b) Required protocol for any learned combiner (L1 to L4)**

1. **Target.** Forward 63-session return (21-session as a sensitivity), decided at close t and earned from t+1. Rank-transform the target cross-sectionally, in excess of the universe mean.
2. **Features.** Rank-normalize each feature to [-1, 1] per date and set missing values to 0 (the median). Fundamentals become available at DART rcept_dt plus one session, using as-first-reported values. Exclude macro × characteristic interactions (see (g)).
3. **Splits.** Walk-forward 756 in-sample / 126 OOS sessions, as in gate step 1. Purge overlapping labels and embargo for at least 63 sessions. Tune hyperparameters on an inner purged validation block (the last 252 sessions of each in-sample window).
4. **Pre-registration.** At most 12 hyperparameter configurations per model family, a fixed feature list and a fixed seed set, hashed before the OOS run. Every configuration counts in the deflated-Sharpe trial count and in the CSCV-based PBO. Reserve a final untouched holdout (for example the last 15 months) and evaluate it once.
5. **Cost-aware objective.** Use the 63-session target, and a no-trade band (enter the top 20%, exit below the top 40%) or an explicit turnover penalty. Evaluate at 35/70 bp per side.
6. **Universe.** Liquid KRX names only (for example the top 300-500 by 60-session average traded value). Also report the result excluding the bottom 30% by market cap, to check that the uplift is not a microcap effect.
7. **Reporting.**
   - Prediction quality: GKX-style OOS R² (not demeaned), rank IC and IC t-statistic.
   - Portfolio: net top-quintile active return, Sharpe and IR against the equal-weight universe and KOSPI200; turnover.
   - Robustness: share of years positive; results by size bucket; 1998-2009 against 2010-2026; sector-neutral variant.
   - Model risk: dispersion of results across seeds.
8. **LLM features, if ever added.** OOS starts after the pretraining cutoff of the exact model version, or use point-in-time models; run a look-ahead propensity check.
9. **Promotion from BACKLOG to BUILD requires all of:**
   - a net uplift over L0 at 2x costs, with a paired block-bootstrap 90% CI that clears zero;
   - PBO at most 0.05 over the pre-registered grid;
   - at least 50% of neighbouring configurations keeping at least half the uplift;
   - uplift positive in at least 60% of calendar years;
   - turnover no more than 1.5 times L0's;
   - uplift not confined to the bottom size tercile.

**(c) Power arithmetic (P5 calculation).** For two strategies with return correlation ρ, the standard error of the difference in annualized Sharpe is approximately √(2(1−ρ)/T) for small Sharpe ratios, under i.i.d. assumptions and with T in years.
- Detecting a +0.10 Sharpe uplift at a one-sided 5% level with 50% power (SE at most 0.061) needs about 27 years at ρ = 0.95, 54 years at ρ = 0.90 and 108 years at ρ = 0.80. At 80% power each figure is about 2.3 times longer.
- With roughly 8 OOS years in the DART era (2018-2026 after a 3-year training window), the SE is 0.11-0.22.
- With technical-only features over KRX 1998-2026 (about 28 OOS years) and ρ = 0.9, the SE is about 0.085, so the minimum detectable uplift is about 0.14.

So the gate cannot verify a plausible ML uplift on Korean fundamentals at all, and only marginally on 30 years of price-only data.

**(d) Trial-count arithmetic (P5 calculation).** Over 8 years, one strategy's annual Sharpe has an SE of about 0.354. The expected best of N zero-skill independent trials uses the expected-maximum approximation from the deflated-Sharpe literature, E[max] ≈ (1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne)) with γ ≈ 0.577. This gives about 0.354 × 1.57 ≈ 0.56 for N = 10, 0.354 × 2.28 ≈ 0.81 for N = 50 and 0.354 × 2.53 ≈ 0.90 for N = 100. Correlated configurations reduce the effective N but do not remove the penalty. A routine ML search therefore starts with a deflated-Sharpe handicap of roughly 0.6-0.9 Sharpe that the one-trial L0 composite does not carry.

**(e) Cost arithmetic (illustrative assumptions, to be replaced by DC1).** Take a long-only top-quintile book rebalanced monthly with one-way turnover u. It trades 2u of NAV a month (sells plus buys), so its annual cost is 24 × u × 0.35% ≈ 8.4u % a year.
- u = 0.20 (slow composite, assumed): about 1.7% a year (3.4% at 2x).
- u = 0.50 (ML on a 1-month target, assumed): about 4.2% a year (8.4% at 2x).

The difference of about 2.5% a year (5% at 2x) equals about −0.25 to −0.42 IR at 6-10% tracking error. An ML combiner trained on 1-month targets without turnover control is therefore expected to be net-negative against L0 at KRX costs.

**(f) Expected net uplift (P5 judgment; replaced once DC1/DC8 results arrive).**
1. Literature gross relative uplift: +50% Sharpe for nonparametric over linear (FNW, equal-weighted, 1991-2014); about +120% against OLS-3 (GKX value-weighted, 1987-2016).
2. Against a richer linear composite in liquid names: assume +15-25%, for three reasons. GKX's baseline has only 3 characteristics. FNW's large-cap set shrinks to 7 characteristics. Avramov et al. find considerable attenuation outside microcaps. (GKX's top-1,000 R² gains point the other way; the evidence conflicts.)
3. If L0 earns a long-only gross IR of about 0.4 (an assumption), that is +0.06 to +0.10 gross.
4. Extra turnover with a 63-session target and bands (+5 to +10 percentage points of one-way turnover a month): −0.42% to −0.84% a year, or about −0.04 to −0.14 IR at 6-10% tracking error (central about −0.08 at 8%).
5. Net result: gross +0.06 to +0.10 less cost −0.04 to −0.14 gives about −0.08 to +0.06 on these inputs. Central estimate about 0 to +0.01. The plausible range widens to about −0.15 to +0.10 once overfitting risk is added. After the 60% live haircut: about zero.
6. Without turnover control (1-month target): −0.2 to −0.4.

The L1 ridge challenger: expected 0 to +0.03 with little downside, because it is shrunk to the prior and carries few trials.

**(g) Conflicts with the macro panel and the prior design**
1. **GKX's macro interactions.** GKX feed 8 macro variables interacted with characteristics. An ML combiner with macro × characteristic terms would implicitly re-weight sleeves by macro state, conflicting with "macro never generates direction" and with "reversal and quality held at 1.0x". Recommendation: exclude macro interactions from any combiner; macro stays in the overlay.
2. **ML market timing.** GKX's bottom-up timing Sharpe of 0.77 against 0.51, and KMZ's timing gains, do not overturn the macro rule. After Nagel and Buncic, the KMZ effect reads as mechanical momentum and volatility timing, which QUANTGEN already implements.
3. **Prior weight on Korean quality.** The weight of 1 conflicts with Bang-Kang-Ryu (gross profitability most significant in Korea, 2001-2023). Refer to the fundamental panel.
4. **Reversal with a volume filter is already a nonlinear rule.** ML evidence that interactions matter supports testing such rules explicitly and pre-registered (DC9), not via a black box.

####### Data-check requests (exact tests for the data lab)
- **DC1: technical-only ML against the composite (KRX marcap 1995-2026, survivorship-free).**
  - Universe: at each month-end, the top 500 by 60-session average traded value; repeat for the top 200.
  - Features at close t, cross-sectionally ranked to [-1, 1]:
    - returns r(t−5,t), r(t−21,t), r(t−252,t−21);
    - close / 252-session high;
    - 60-session volatility and idiosyncratic volatility against the EW market;
    - 252-session beta;
    - log market cap;
    - 21-session traded value / market cap;
    - Amihud illiquidity (21-session);
    - MAX (largest daily return in 21 sessions);
    - 5/60-session volume ratio.
  - Targets: r(t, t+21) and r(t, t+63) minus the universe mean.
  - Models:
    - M0: equal-weight composite with literature signs fixed in advance;
    - M1: 36-month rolling Fama-MacBeth slopes;
    - M2: ridge shrunk to M0;
    - M3: LightGBM, depth 3, 300 trees, learning rate 0.05, at least 200 observations per leaf, three configurations in total;
    - M4: MLP 32-16-8 averaged over 5 seeds.
  - Walk-forward 756/126 sessions with purge and embargo equal to the target horizon.
  - Portfolios: long-only top quintile, equal-weighted and cap-weighted (10% cap), with and without a band (enter top 20%, exit below top 40%).
  - Costs: 35 and 70 bp per side.
  - Report:
    - prediction quality: OOS R² and rank IC;
    - portfolio results: net active return, Sharpe, IR, turnover, share of years positive;
    - deflated Sharpe with N equal to all configurations, and PBO via CSCV (16 blocks);
    - the Sharpe difference against M0 with a paired block bootstrap (10-session blocks × 2,000);
    - correlation ρ of the M3/M4 active returns with M0's;
    - all of the above split into 1998-2009 and 2010-2026.
- **DC2: microcap attenuation (Avramov-Cheng-Metzker test).** Repeat DC1 for all stocks, for stocks excluding the bottom 30% by market cap, and for the top 200 by traded value. Report the net ML-minus-M0 spread per bucket.
- **DC3: Korean replication of the Krauss / Fischer-Krauss setup.**
  - Universe: the top 200 KRX stocks by market cap at each date (a proxy for KOSPI200 membership).
  - Features: returns over 1-20 sessions and 40, 60, …, 240 sessions.
  - Model: random forest (500 trees) predicting whether the next-day return beats the cross-sectional median.
  - Portfolio: daily, long the top 10 and short the bottom 10 (also long-only top 10).
  - Costs: 5, 35 and 70 bp per side.
  - Report 1996-2009 against 2010-2026.
- **DC4: weekly reversal tradability.** Weekly reversal (prior-week losers minus winners, and long-only bottom-decile losers) among the top 500 by traded value, 2010-2023. Compare with Jeong-Byun-Kim's gross WSTR of 12% a year (Sharpe 0.69). Report gross, net at 35 and 70 bp, and turnover.
- **DC5: cross-market alignment trap.** Using SPY daily 1998-2021 and a KOSPI proxy (cap-weighted marcap index, or KODEX 200 if available):
  - regress the KRX close-to-close return on KST date d on the SPY return of US date d−1 (calendar join);
  - regress it on the SPY return of US date d−2, the last US session known at the KRX close of d−1;
  - report both R², and the Sharpe of "long KOSPI at the KRX close of d−1 if the known SPY return is positive".

  Expect a high R² for d−1 (which is a contemporaneous, untradable result) and near zero for d−2. This documents the leakage that could inflate studies such as Chun-Kang-Kim.
- **DC6: virtue-of-complexity check (Shiller monthly 1871-2026).**
  - Predictors: D/P, E/P, CAPE, long rate, inflation, 12-month momentum, 12-month realized volatility.
  - Compare: RFF ridge (12,000 features, 12-month window, shrinkage 10³), Nagel's volatility-timed momentum (linearly declining weights on the past 12 monthly returns, scaled by inverse predictor volatility), and linear ridge with an intercept.
  - Report timing Sharpe and position correlations for 1930-2026 and 1990-2026, and repeat on permuted and sign-reversed return series.
- **DC7: learned against equal-weight factor combination (French monthly, 1963-2018).**
  - Factors: Mkt-RF, SMB, HML, RMW, CMA, UMD, ST_Rev, LT_Rev.
  - Combinations: equal-weight; rolling 120-month sample mean-variance weights; ridge-shrunk weights.
  - OOS 1973-2018. Report Sharpe and the bootstrap CI of the Sharpe difference.
- **DC8: power audit.** From DC1's OOS series, compute ρ(M3, M0), the Memmel-type SE of the Sharpe difference, the minimum detectable uplift, and the years needed for a +0.10 uplift.
- **DC9: interactions as pre-registered hypotheses.** Fit LightGBM on 1998-2009 only and extract the top 3 SHAP interaction pairs (for example reversal × volume ratio, momentum × volatility). Add them as fixed linear terms to M2 and evaluate once on 2010-2026, as a single trial.

####### Gaps
- No pre-2015 point-in-time Korean fundamentals are in QUANTGEN's data list. Commercial sources would be needed for a longer fundamental history.
- The uplift estimate in (f) is P5's judgment from US, emerging-market and Chinese evidence plus stated assumptions. No Korean net-of-cost ML-against-composite study exists to anchor it.
- The data lab's datasets contain no fundamentals, so fundamental-feature ML cannot be data-checked until OpenDART data is assembled.

---

### [P5] Claims ledger (lines 528-562)

###### 10. Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P5-C01 | Shallow nonlinear ML roughly doubles OOS R² and long-short Sharpe against a 3-characteristic OLS in US stocks. | US, OOS 1987-2016, gross: R² NN3 0.40% vs OLS-3 0.16%; VW decile L/S Sharpe 1.35 vs 0.61; EW 2.45 vs 0.83 | [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf); [NBER w25398](https://www.nber.org/system/files/working_papers/w25398/w25398.pdf) | T1 | Replicated gross in Europe, EM, China, 46 markets; no costs; weak baseline | Microcap and cost attenuation (C07); post-2004 net about zero (C08) | CONTEXT: headline is gross and measured against a weak baseline |
| P5-C02 | Depth does not help: neural nets peak at about 3 layers and unregularized OLS on all features fails. | US OOS 1987-2016: NN4/NN5 below NN3; OLS on 920 features R² -3.46% | [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf) | T1 | Consistent with small-data, low-signal arguments | — | BACKLOG design rule: trees depth ≤3, MLP ≤3 layers |
| P5-C03 | Many-feature linear models add little; ML gains come from interactions and nonlinearity. | ENet R² 0.11% vs OLS-3 0.16% (US OOS); FNW nonparametric EW hedge Sharpe 3.42 vs 2.26 linear, OOS 1991-2014 | [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf); [FNW](https://www.nber.org/system/files/working_papers/w23227/w23227.pdf) | T1 | FNW working-paper version; equal-weighted | Large caps keep only 7 characteristics | BUILD-candidate: pre-registered explicit interactions in the linear model (DC9) |
| P5-C04 | Price trends, then liquidity, then volatility dominate ML importance in the US; reversal and momentum lead SDF learning. | GKX ranking; FNW: reversal, size, 52-week high, SUV; CPZ: reversal and momentum top | [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf); [FNW](https://www.nber.org/system/files/working_papers/w23227/w23227.pdf); [CPZ](https://arxiv.org/pdf/1904.00745) | T1 | Consistent across methods; US-centric | Fast features most cost-sensitive; 93% of liquidity variables fail VW (C13) | BUILD-candidate features (52-week high, momentum, low vol); fast signals in cost-gated sleeves |
| P5-C05 | Outside the US, valuation (Europe), liquidity (China), simple factors (46 markets) and gross profitability/accruals (Korea) carry the power. | Europe NN best after costs; China liquidity top; 46 markets mom/rev/value/size; Korea 2001-2023 DS-LASSO: GP, accruals, long-term momentum | [Drobetz-Otto](https://ideas.repec.org/a/pal/assmgt/v22y2021i7d10.1057_s41260-021-00237-x.html); [LWZ](https://econpapers.repec.org/RePEc:eee:jfinec:v:145:y:2022:i:2:p:64-82); [Cakici et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4141663); [Bang-Kang-Ryu](https://www.sciencedirect.com/science/article/abs/pii/S1544612324009760) | T1 | Mixed methods; mostly gross | — | CONTEXT; flag: Korean quality weight 1 may be too low |
| P5-C06 | Few characteristics are independent, and non-microcap hedge returns vanished after 2003. | US 1980-2014: 12 of 94 independent; 2 since 2003; hedge returns insignificant since 2003 | [Green-Hand-Zhang](https://ideas.repec.org/a/oup/rfinst/v30y2017i12p4389-4436..html) | T1 | US Fama-MacBeth; post-2003 subsample | Post-2003 | BUILD rule: keep the composite to about 10 or fewer features; expect decay |
| P5-C07 | ML profits concentrate in hard-to-arbitrage stocks and states, and deteriorate under realistic costs. | US: considerable attenuation excluding microcaps, distressed and high-vol episodes; worse after costs; long side still profitable | [Avramov-Cheng-Metzker](https://cris.huji.ac.il/en/publications/machine-learning-vs-economic-restrictions-evidence-from-stock-ret/) | T1 | Abstract-level only (numbers not accessed) | Microcaps; high turnover | BUILD rule: liquid universe; long-only evaluation |
| P5-C08 | 1-month-horizon ML nets about zero after 2004; longer horizons plus trading rules restore positive net returns. | US 2004-2021 net about zero at 1 month; 3/6/12-month targets plus efficient rules significantly positive; tilt to quality/value | [Blitz et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4474637); [Robeco](https://www.robeco.com/en-us/insights/2023/07/the-term-structure-of-machine-learning-alpha) | T1/T2 | Post-2004, net | Short-horizon ML | BUILD rule: 63-session target, no-trade bands |
| P5-C09 | Cost-aware ML construction beats cost-agnostic ML by a wide margin net. | US 1981-2020: Portfolio-ML net Sharpe 1.38, 19% net excess return; Markowitz-ML gross Sharpe 2.00, negative net | [JKMP](https://afajof.org/management/viewp.php?n=32368); [SFS](https://sfs.org/rfs-forthcoming-paper-123/) | T1 | Forthcoming RFS; net | Larger AUM, worse frontier | BUILD the cost-aware harness and turnover penalty now |
| P5-C10 | Combining signals nets trades, so more characteristics are useful after costs. | US: significant characteristics rise from 6 to 15 with costs | [DeMiguel et al. 2020](https://econpapers.repec.org/article/ouprfinst/v_3a33_3ay_3a2020_3ai_3a5_3ap_3a2180-2222..htm) | T1 | Net | — | BUILD one combined composite, not one sleeve per signal |
| P5-C11 | Some US ML strategies stayed profitable net on post-publication anomalies over 2005-2021. | Net up to 1.42%/month (gross 1.63%); costs cut 13-40%; turnover >50%; LSTM alpha 1.20%/month (t 3.46) | [Azevedo-Hoegner-Velikov](https://afajof.org/management/viewp.php?n=75544) | T1 (WP) | Post-publication, net, US | Hard-to-arbitrage exposure | CONTEXT: counterweight to C08; must be re-costed at the KRX schedule |
| P5-C12 | The average anomaly earns about 8 bp/month net in the modern era. | US: about 8 bp/month net; strongest 10-20 bp after data-mining adjustment | [Chen-Velikov](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681) | T1 | Post-publication, net | — | CONTEXT: realistic prior for any single feature |
| P5-C13 | Most anomalies fail replication with NYSE breakpoints and VW returns, liquidity variables most of all. | 447 anomalies: 64% insignificant at 5%, 85% at t>3; 93% of liquidity variables fail | [Hou-Xue-Zhang](https://www.nber.org/papers/w23394) | T1 | Replication study | — | CONTEXT: down-weight microcap-driven liquidity features |
| P5-C14 | Simple combinations are hard to beat in short samples. | None of 14 models consistently beats 1/N (about 3,000 months needed for 25 assets); combination forecasts beat the mean; Lewellen OOS slope 0.74 (SE 0.07) | [DGU](https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html); [RSZ](https://ideas.repec.org/a/oup/rfinst/v23y2010i2p821-862.html); [Lewellen](https://www.nowpublishers.com/article/Details/CFR-0024) | T1 | OOS; widely replicated | — | BUILD the equal-weight composite as baseline, ridge as challenger |
| P5-C15 | "Virtue of complexity" timing gains are largely mechanical or artefactual. | KMZ about +0.47 Sharpe at T=12 with negative R²; Nagel: RFF IR 0.255 vs vol-timed momentum 0.388; reversal-data alpha -0.143 (t -1.84); Buncic: linear with intercept up to 40% higher Sharpe; Fallahgoul: >25-30 years needed; FX at T=120 worse | [KMZ](https://economics.yale.edu/sites/default/files/2024-01/The%20Journal%20of%20Finance%20-%202023%20-%20KELLY%20-%20The%20Virtue%20of%20Complexity%20in%20Return%20Prediction%20(1).pdf); [Nagel](https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/f/575/files/2025/07/Complexity_2.pdf); [Buncic](https://www.danielbuncic.com/); [Fallahgoul](https://arxiv.org/abs/2506.03780); [Kılıç](https://www.federalreserve.gov/econres/feds/files/2025089pap.pdf) | T1 | Contested; critiques 2025-26; no reply found | Reversal regimes; i.i.d. data | DROP complexity-based timing; consistent with the macro rule |
| P5-C16 | Image-CNN price-pattern signals are strong equal-weighted but modest value-weighted, with high turnover. | US OOS 2001-2019, gross: EW I5/R20 Sharpe 2.35; VW I20/R20 0.49 (MOM 0.36); weekly EW 7.15 / VW 1.49 at 774-947% turnover; ≤12% explained by known signals; transfer to 26 markets +0.4 Sharpe | [JKX](https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf) | T1 | OOS, gross | Value-weighting; turnover | BACKLOG (KRX costs) |
| P5-C17 | The Korean chart CNN reports very high gross Sharpe, but tradability at KRX costs is unverified. | KRX OOS 2010-2023: I20/R5 L/S 56%/year, Sharpe 5.48 vs WSTR 12% (0.69) | [Jeong-Byun-Kim](https://www.sciencedirect.com/science/article/abs/pii/S0275531925004878) | T1 | OOS; cost treatment unclear | Weekly turnover | BACKLOG + DC4 |
| P5-C18 | Daily deep-learning stat-arb on S&P 500 constituents decayed to about zero net after 2010. | LSTM 0.46%/day, Sharpe 5.8 pre-cost (1992-2015), about zero after 5 bp/half-turn after 2010; ensemble 0.45% pre / 0.25% post-cost; >200%/year, then 22%, then negative 2010-15 | [Fischer-Krauss](https://www.sciencedirect.com/science/article/abs/pii/S0377221717310652); [Krauss-Do-Huck](https://www.econstor.eu/bitstream/10419/130166/1/856307327.pdf) | T1 | OOS; costs at 5 bp | Post-2010 | DROP for KRX (35 bp ≫ 5 bp); DC3 |
| P5-C19 | Order-book deep learning predicts tick-horizon direction but overfits benchmarks and ignores costs. | Stable accuracy claims (DeepLOB, Sirignano-Cont); best F1 82.6% on FI-2010 falls to about 63% on 2021-22 NASDAQ; no-cost backtests | [DeepLOB](https://arxiv.org/abs/1808.03668); [Sirignano-Cont](https://arxiv.org/abs/1803.06917); [LOBCAST](https://link.springer.com/article/10.1007/s10462-024-10715-4) | T1 | Fails on new data | Dataset shift | DROP (no order path; costs) |
| P5-C20 | LLM embeddings extract strong but fast news signals, gross. | US 1996-2019 plus 16 markets: EW L/S Sharpe 4.62 (ChatGPT), 4.16 (LLaMA2); return prediction EW 5.31 / VW 1.32; absorbed by day 3 | [Chen-Kelly-Xiu](https://mgmt675-2025.kerryback.com/assets/ExpectedReturns_LLMs.pdf) | T1 | OOS window inside pretraining data | VW much weaker | BACKLOG (no news feed; daily turnover) |
| P5-C21 | Post-cutoff ChatGPT headline strategies decayed as adoption rose and fail at 20 bp costs. | US Oct 2021-May 2024: 34 bp/day, Sharpe 2.97 at zero cost; unprofitable at 20 bp; Sharpe 6.54 → 3.68 → 2.33 → 1.22; small-stock coefficient 0.652 vs 0.118 | [Lopez-Lira-Tang v6](https://arxiv.org/html/2304.07619v6); [v1](https://arxiv.org/pdf/2304.07619v1) | T1 | Post-cutoff OOS | Adoption decay; costs | DROP for KRX daily signals |
| P5-C22 | LLM backtests inside the training window are contaminated, and masking does not fix it. | 6.8% COVID mentions from 2019 calls; masked firms re-identified 70%; look-ahead propensity about 0 after cutoff; S&P 500 yearly recall up to 100%; S&P 500 headlines 77 bp/day in-window vs 6 bp/day OOS | [Sarkar-Vafa](https://openreview.net/pdf?id=fn9cJkB86T); [Gao-Jiang-Yan](https://arxiv.org/abs/2512.23847); [Didisheim et al.](https://www.sciencedirect.com/science/article/pii/S0165176525004392); [Glasserman-Lin](https://arxiv.org/pdf/2309.17322) | T1 | Multiple independent studies | In-window backtests | BUILD protocol rule: post-cutoff only, or point-in-time LLMs |
| P5-C23 | Point-in-time LLMs make honest text backtests feasible at modest cost in accuracy. | ChronoBERT/ChronoGPT news-return Sharpe comparable to a larger Llama; bias modest and application-specific | [He-Lv-Manela-Wu](https://arxiv.org/abs/2502.21206) | T1 | Single study | — | BACKLOG (only route for in-sample LLM tests) |
| P5-C24 | The ML/LLM finance literature commonly omits backtests, costs and bias controls. | 35 of 185 DL papers report backtests; many use ML metrics only; 164 LLM papers with no bias discussed in >28%; leakage in 648 papers across 30 fields | [Olorunnimbe-Viktor](https://d-nb.info/1265952744/34); [Kong et al.](https://arxiv.org/abs/2602.14233); [Kapoor-Narayanan](https://reproducible.cs.princeton.edu/); [AHM](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf) | T1 | Systematic reviews | — | BUILD the leakage checklist (section 6) into the gate |
| P5-C25 | ML gains in China and emerging markets survive costs better than in US large caps. | 32 EMs, OOS 2002-2021: significant net returns with costs, short-sale constraints, big stocks only; China OOS economically significant after costs | [Hanauer-Kalsbach](https://www.sciencedirect.com/science/article/abs/pii/S1566014123000274); [LWZ](https://econpapers.repec.org/RePEc:eee:jfinec:v:145:y:2022:i:2:p:64-82) | T1 | Net; OOS | — | CONTEXT: Korea may offer more room, not yet shown |
| P5-C26 | Korean ML evidence is thin, mostly gross, and contains red-flag results. | LightGBM/GBRT best (about 29 features), no cost figures; index-level daily KOSPI LASSO R² 16.68%, Sharpe 3.45, no costs | [Choi et al.](https://link.springer.com/article/10.1007/s42952-023-00245-0); [Chun-Kang-Kim](https://link.springer.com/article/10.1186/s40854-024-00648-w) | T1 | Gross; possible timing misalignment | Possible look-ahead (DC5) | CONTEXT + DC5 |
| P5-C27 | Point-in-time Korean fundamentals via OpenDART begin in 2015. | OpenDART key-accounts API: data from the 2015 business year | [OpenDART guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016) | T1 | Official | — | BACKLOG fundamental ML (about 8 OOS years) |
| P5-C28 | The gate cannot detect a plausible ML uplift over the composite; P5's net uplift estimate for GBRT/NN over L0 in liquid KRX is about 0 to +0.01 IR (range −0.15 to +0.10). | SE(ΔSR) ≈ √(2(1−ρ)/T); a +0.10 uplift needs 27/54/108 years at ρ = 0.95/0.90/0.80 (one-sided 5%, 50% power); SE 0.11-0.22 with 8 years; uplift = gross +0.06 to +0.10 minus turnover cost 0.04-0.14 (section 9(f)) | P5 calculation; inputs from the gate in the context brief and C01, C03, C07, C08 | n/a (P5 calculation) | i.i.d. approximation; assumed IR and turnover | — | BACKLOG nonlinear ML; BUILD L0/L1; replace with DC1/DC8 results |
| P5-C29 | ML hyperparameter search raises the deflated-Sharpe bar sharply. | Expected best zero-skill Sharpe over 8 years ≈ 0.354 × E[max of N]: 0.56 (N=10), 0.81 (N=50), 0.90 (N=100) | P5 calculation; gate step 3 (deflated-Sharpe expected-maximum approximation) | n/a (P5 calculation) | Independent trials; correlation lowers effective N | — | BUILD rule: pre-register ≤12 configurations per family; count all |
| P5-C30 | Crowded quant reversal and factor books can crash together. | US, week of 6 Aug 2007: market-making/contrarian strategy significantly negative; unwind July-Dec 2007 | [Khandani-Lo](https://www.nber.org/papers/w14465) | T1 | Transaction-data evidence | Liquidity withdrawal | CONTEXT: ML loading on reversal inherits crowding risk |



---

## P6_international_korea_asia.md

### [P6] Persona and position summary (lines 1-66)

##### P6: Technical and fundamental anomalies outside the US (Korea first, then Japan, China A, Taiwan, EM) and what QUANTGEN should do

As of 2 October 2026 (Asia/Seoul). These notes are by panel member P6, a fictional composite persona. Every number carries its market, period, in-sample (IS) or out-of-sample (OOS) status, and gross or net basis.

"Local check" means P6's own indicative run on the survivorship-free KRX marcap file (KOSPI + KOSDAQ common stocks, 1998-2026). The scripts and CSVs are in `/home/claude/datalab/scripts/p6_indicative/` (see `README.txt` there). Read every local number with these caveats:
- It is in-sample. About 60 configurations were tried and no deflation was applied.
- Returns are price returns from KRX `ChangesRatio`, which is split-adjusted but excludes cash dividends.
- Each monthly sort is decided at the month-end close and earned the following month.
- Costs are 35 bp per side on every unit of weight change, with a 2x stress at 70 bp.
- The universe excludes preferred shares and SPACs. It requires at least 15 traded days in the month, a close of at least KRW 1,000, and a market cap above the 20th percentile, unless stated otherwise.
- Holding month January 2001 is excluded. It is an outlier: the December-2000 loser decile rose 111.8% in January 2001.

These are evidence for the data lab to re-run, not gate results.

###### Q0. Persona line and position summary

####### Takeaway
**Persona line.** P6 is the "Professor of International and Korean Finance", a fictional composite persona and not a real person. The persona is a Korean finance professor who has published in Korean (KCI-indexed) and international journals on cross-sectional anomalies, investor-type trading and market microstructure in Korea and Asia. P6 argues from local replication: a US factor prior is not evidence for KRX until it survives KRX data, KRX costs and KRX market rules.

**Position summary.**
1. Outside the US, the anomaly family that travels best is low risk and lottery, not momentum. In Griffin-Ji-Martin's 40-country sample, 6/6 momentum is insignificant in every East Asian market: Korea -0.76%/month, Japan 0.02, Taiwan 0.01, China -0.01. Low-volatility and MAX effects, by contrast, are large in China, Korea and emerging markets.
2. In Korea the lottery family (MAX, volatility, turnover; pairwise correlations 0.83-0.93) is the strongest signal both before and after QUANTGEN's costs. The local check gives an equal-weighted long-short Sharpe of 0.6-0.9 net of 35 bp per side over 2001-2026, in-sample. But nearly all of it sits in the short leg. For a read-only, long-only desk it is therefore an exclusion screen, not a tilt: worth about +0.23%/month equal-weighted and +0.04%/month capped value-weighted.
3. Korean 12-1 momentum is contested.
   - The headline KJFS result, -6.13%/month in high-turnover stocks over 2000-2019, does not replicate on survivorship-free KRX data. P6's approximate replication of the same design gives +0.58% to +1.42%/month; an exact replication is requested as DC-P6-02.
   - Momentum still lost money in 2017-2019 and 2021, and crashed by -22.3% in July 2026.
   - The intermediate-horizon (12-7) and 52-week-high variants behave better, but their margin after costs is thin.
4. One-month reversal is real before costs: 0.86%/month, t 2.70.
   - It has fallen by roughly two thirds to three quarters since 2001-09 (1.55 to 0.54 and 0.41%/month).
   - It needs 3.5x monthly turnover and is negative at 35 bp per side.
   - The prior design's volume-filtered 5-day reversal has the wrong sign in Korea: high-volume weekly moves do not reverse.
5. The prior design's strong Korean flow weight is not supported for close-to-close trading. Lagged foreign and institutional net buying predicts the next open but not the next close, and copying foreign buying underperformed KOSPI.
6. The fundamental candidates are earnings drift and value plus profitability. Both are cheap to hold, and both still need a point-in-time DART test.
   - Earnings drift: a 60-day spread of 4.8% over 2002-2017, driven by retail investors selling into good news.
   - Value plus profitability: HML 1.05%/month and RMW 0.65%/month over 2002-2015.
7. Market structure changes the answer.
   - Shorting has been banned for 42 months since 2008, and for small caps for five continuous years (2020-2025).
   - Price limits have been ±30% since June 2015.
   - A 0.20% sell tax applies from 2026.
   - Estimated half-spreads are about 27-39 bp outside the top 5% of caps.
   - KOSPI is effectively a two-stock market (Samsung and SK hynix are 55.5% of its cap). A value-weighted low-risk tilt lagged the value-weighted universe by 20.3 points in 2025 and 46.4 points in 2026 to date.
8. Outside Korea:
   - Japan keeps value at 3, with momentum allowed only when paired with value or dynamically scaled.
   - China A and Taiwan get 0 for cross-sectional momentum.
   - China A gets 3 for low volatility.
9. QUANTGEN should:
   - cut Korean short-term reversal and flow from 3 to 1;
   - raise quality from 1 to 2;
   - cut low volatility as a tilt from 2 to 1;
   - add a lottery-exclusion screen at 3 and a 52-week-high tilt at 2;
   - cut earnings drift from 3 to 2 until a point-in-time DART test passes;
   - run the five experiments in Q6 before any Korean stock card is believed.

####### Cited Findings
- 6/6 momentum by country, to December 2000, gross: Korea -0.76%/month (t -0.80), Japan 0.02 (0.10), Taiwan 0.01 (0.02), China -0.01 (-0.02). The Asia average is 0.32 (t 1.64), against 0.77 (t 8.15) for Europe. — [Griffin, Ji, Martin 2003, JF (PDF copy)](https://gyanresearch.wdfiles.com/local--files/alpha/Momentum.pdf)
- Korea, July 2000 to June 2019, equal-weighted, gross, IS: in high-turnover stocks, 12-1 momentum winners minus losers is -6.13%/month (t -4.76). — [Eom, Chang, Kang, Lee, Park 2020, KJFS 49(4)](https://www.e-kjfs.org/journal/view.php?number=901). The local replication of this design gives +0.58%/month (t 1.50) on all stocks and +1.42% (t 3.52) excluding the smallest 20% of caps. — [P6 local check p6_eom_x01.py](/home/claude/datalab/scripts/p6_indicative/p6_eom_x01.py)
- Korea, February 2001 to September 2026, monthly decile long-short, local IS (details in Q2):
  - Low-volatility, equal-weighted: 2.40%/month gross (t 6.31); Sharpe net of 35 bp 0.91.
  - Low-MAX, equal-weighted: 1.95%/month (t 6.55); Sharpe net of 35 bp 0.59.
  - One-month reversal, equal-weighted: 0.86%/month gross (t 2.70); Sharpe net of 35 bp -0.22.
  - Source: [P6 local check p6_sorts.py](/home/claude/datalab/scripts/p6_indicative/p6_sorts.py)

####### Inferences
- The US prior (cross-sectional momentum at 3) is the wrong starting point for Korea, Japan, Taiwan and China A. The low-risk and lottery family and fundamental drift are the right starting points.

####### Gaps
- None at summary level; see the Gaps under Q1 to Q7.

### [P6] Korea in depth (Q2) (lines 170-344)

###### Q2. Korea in depth: momentum, reversal, 52-week high, MAX/lottery, low volatility, value/P-B, quality, earnings drift, investor flows

####### Takeaway
On local KRX data (2001-2026, in-sample) the ranking after QUANTGEN's 35 bp costs is:
1. Low volatility, low turnover and low MAX: all one lottery factor.
2. Intermediate momentum (12-7).
3. 52-week-high nearness.
4. 12-1 momentum.
5. One-month reversal and size, which are negative net.

The lottery premium lives in the short leg, which QUANTGEN cannot hold. Long-only, it works as an exclusion screen.

The literature's Korean headline, "negative momentum and reversal carry-over", does not replicate on survivorship-free data. Momentum is fragile, not reliably negative.

Earnings drift (retail investors trading against the news) and value plus profitability are the best-documented fundamental signals. Flow signals predict the next open, not the next close.

####### Cited Findings

**Momentum and short-term reversal (literature)**
- **Eom, Chang, Kang, Lee, Park 2020, KJFS 49(4).** Design (Table 3): KOSPI + KOSDAQ, July 2000 to June 2019; 12-month formation skipping month t-1; 1-month hold; top and bottom 30% turnover groups by period-average turnover; 3x5 sorts; financials, non-December fiscal years and the highest-volatility decile excluded. Returns are monthly averages in excess of the risk-free rate; the weighting is not stated explicitly (likely equal). Gross, IS:
  - High-turnover winners minus losers: -6.13%/month (t -4.76). Losers earn 6.85% (t 4.87); winners 0.73% (t 1.05).
  - Low-turnover winners minus losers: -0.53% (t -1.17).
  - 6-1 high turnover: -5.52% (t -4.51). 3-1: -2.89% (t -2.83).
  - Source: [KJFS article page](https://www.e-kjfs.org/journal/view.php?number=901); [KJFS PDF](https://www.e-kjfs.org/upload/pdf/KJFS-2020-08-49-4-589.pdf)
- **Eom and Park (2021).** Negative momentum profits occur in high-attention stocks, and the reversal comes from firm-specific rather than common return components. — [RIBAF 57, RePEc](https://ideas.repec.org/a/eee/riibaf/v57y2021ics0275531921000258.html)
- **Chae and Eom (2009, APJFS), "Negative Momentum Profit in Korea and its Sources".** The title was confirmed, but the abstract could not be fetched (403). — [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/j.2041-6156.2009.tb00013.x)
- **Sim and Kim (2021), JDQS 29(3), January 1999 to February 2021.**
  - pret(12,7) momentum FF5 alpha: 0.531%/month (t 2.05). pret(6,2): -0.084% (t -0.28).
  - Return coefficients: one-month r(-1) -2.950 (t -3.77); r(-2) -1.108 (t -2.01).
  - Reversal-strategy FF5 alpha: 1.275%/month (t 3.22) at k=1; 0.514% (t 1.99) at k=2.
  - Conclusion: the term structure of momentum is a two-month reversal effect.
  - Gross, IS. Source: [Emerald JDQS](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on)
- **Bae and Lee (2021), JDQS 29(1), July 2001 to June 2019, value-weighted.**
  - Winners minus losers: 0.76%/month (t 1.58) at top/bottom 10%; 1.06% (t 2.53) at 20%; 0.83% (t 2.43) at 30%.
  - These are significant after CAPM, FF3 and FF5 adjustment.
  - A duration factor explains 54-67% of momentum's variation.
  - Source: [Emerald JDQS](https://www.emerald.com/jdqs/article/29/1/49/195316/Illiquidity-duration-and-momentum-profits-evidence)
- **Ryu (2021), JKDAS 23(4).** In Korea, 52-week-high strategies (George-Hwang and RR) beat Jegadeesh-Titman momentum after risk adjustment. The skip period matters. — [Kyobo Scholar abstract](https://scholar.kyobobook.co.kr/article/detail/4010028467563)
- **SK Securities (sell-side, 30 April 2025).**
  - Practitioner claim: "since 2020, as retail influence rose, short-term momentum exists" in Korea.
  - On KS200 + KQ150, a "leading" price-and-volume group had a Sharpe of 0.964 and a "lagging" group -1.728.
  - The backtest is not fully specified. T2/T3 claim to be tested.
  - Source: [SK Securities report (PDF)](https://www.sks.co.kr/data1/research/qna_file/20250429151923625_0_ko.pdf)

**Momentum and short-term reversal (local check, KRX marcap)**

Monthly top-minus-bottom deciles, February 2001 to September 2026 holding months. "EW" is equal-weighted and "VW" value-weighted. "net35" deducts 35 bp per side on turnover; "SR" is annualised Sharpe.

| Signal | EW gross %/month (t) | EW Sharpe net35 / 2x | VW gross %/month (t) | VW Sharpe net35 | Turnover L+S per month | 2001-09 / 2010-19 / 2020-26 (EW %/month, t) |
|---|---|---|---|---|---|---|
| 1-month reversal | 0.86 (2.70) | -0.22 / -0.94 | 0.04 (0.09) | -0.51 | 3.50 | 1.55 (2.8) / 0.54 (1.2) / 0.41 (0.6) |
| 12-1 momentum | 0.76 (2.37) | 0.18 / -0.09 | 1.66 (2.71) | 0.39 | 1.31 | 1.44 (2.7) / 0.41 (0.8) / 0.40 (0.7) |
| 12-7 momentum | 1.30 (4.91) | 0.54 / 0.10 | 1.46 (2.75) | 0.30 | 1.66 | 1.96 (4.5) / 0.95 (2.3) / 0.95 (1.8) |
| 52-week-high nearness | 1.23 (3.22) | 0.30 / 0.01 | 1.44 (2.69) | 0.28 | 1.71 | 1.37 (1.7) / 1.19 (2.4) / 1.08 (1.6) |

  Source: [P6 local check p6_sorts.py and CSV](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv). Keeping delisting-window returns changes no mean by more than 0.03%/month. — [p6_krx_monthly_anomalies_delist.csv](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies_delist.csv)
- **Local replication of Eom et al.'s design.** Top and bottom 30% period-average turnover, highest-volatility decile dropped, 1-month hold, equal-weighted raw returns; holding months July 2000 to June 2019, excluding January 2001 (n = 227):

  | Universe | Horizon | High-turnover W-L %/month (t) | Losers / winners | Low-turnover W-L %/month (t) |
  |---|---|---|---|---|
  | All caps | 12-1 | +0.58 (1.50) | 0.00 / 0.58 | +0.59 (1.92) |
  | Excluding smallest 20% | 12-1 | +1.42 (3.52) | -1.02 / 0.39 | +0.82 (2.68) |
  | All caps | 3-1 | -0.37 (-1.01) | n/a | n/a |
  | Excluding smallest 20% | 3-1 | -0.04 (-0.10) | n/a | n/a |

  In the paper, losers earn +6.85%/month. In the replication they earn -1.02% to 0.00%. — [P6 local check p6_eom_x01.py](/home/claude/datalab/scripts/p6_indicative/p6_eom_x01.py)
- **By trailing-12-month-turnover tercile** (excluding the smallest 20% of caps), 12-1 momentum winners minus losers:
  - T1 (lowest turnover): 0.95%/month (t 3.17).
  - T2: 1.10% (t 2.79).
  - T3 (highest turnover): 0.80% (t 1.90). By period: 1.52 (2.2) in 2001-09, 0.04 (0.1) in 2010-19, 0.98 (1.2) in 2020-26.
  - In T3, losers minus the universe earn -1.16% (t -4.9): high-attention losers keep losing, not reversing.
  - 6-1 momentum in T3: -0.43% (t -1.11). In the T3 tercile of the all-stocks universe (micro-caps included): -0.74% (t -2.11), and -1.50% (t -2.3) in 2020-26.
  - One-month reversal is concentrated in T3: -1.48%/month (t -3.14). Low-turnover stocks: -0.51% (t -2.02).
  - Source: [P6 local check p6_split_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_split_f01.py)
- **Skipping the most recent month matters.** Measured in the lowest and highest 1-month-turnover terciles, on both universes. Without a skip (12-0), momentum winners minus losers is -0.02 to +0.49%/month (all t < 1.6). With the one-month skip (12-1), it is +0.21 to +1.38%/month (t up to 3.25). — [P6 local check p6_final_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_final_f01.py)
- **Weekly 5-day reversal** (the daily-swing proxy for the prior design's ST-rev). Weekly long last-week losers, short winners, equal-weighted deciles, February 2001 to September 2026:
  - Gross: 0.30%/week (t 3.8), Sharpe 0.80. 2001-09: 0.64%/week (Sharpe 1.44). 2020-26: -0.03%/week.
  - Net of 35 bp per side: Sharpe -2.37 (3.25x weekly turnover).
  - With the prior design's volume filter (week's average traded value over the prior 20-day average above 1.5): gross 0.03%/week (t 0.2).
  - Long-only losers versus the universe under the filter: -0.34%/week (t -4.1). High-volume losers continue down.
  - Source: [P6 local check p6_weekly_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py)

**52-week high and anchoring**
- **Goh and Jeon (2017).** In Korea, earnings drift after positive earnings is pronounced for stocks near their 52-week high. Individuals buy stocks far from the high around announcements. — [PBFJ 44, RePEc](https://ideas.repec.org/a/eee/pacfin/v44y2017icp150-159.html)
- **Local check, long-only nearness-to-high tilt.** Top 52-week-high-ratio quintile, equal-weighted, monthly:
  - Net of 35 bp: +0.34%/month over the equal-weighted universe (t 2.31); Sharpe 0.57 versus 0.31; turnover 0.78 per month.
  - At 2x costs: only +0.09%/month.
  - Excluding lottery stocks as well: +0.55%/month (t 3.63) net of 35 bp; +0.31 at 2x; Sharpe 0.72.
  - Capped value-weighted (5% cap): +0.06%/month (t 0.40), and negative at 2x.
  - Source: [P6 local check p6_excl2.py](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py)

**MAX / lottery, low volatility, turnover**
- **Cheon and Lee (2018), Korea, January 1992 to June 2016.**
  - Value-weighted low-minus-high MAX abnormal return: 2.40%/month, versus 0.66% in the US.
  - The overpayment is 2.23% in high-volatility periods and 0.13% in calm ones.
  - Source: [PBFJ](https://www.sciencedirect.com/science/article/abs/pii/S0927538X17304870)
- **Goh and Kim (2024), JDQS 32(2), July 2000 to December 2020.**
  - Equal-weighted high-minus-low MAX: -2.08%/month (t -5.01); FF3 alpha -2.00 (t -4.61).
  - The effect is significant only among overpriced stocks: alpha -2.78 (t -5.79) in the most overpriced quintile.
  - Individuals' buying concentrates in overpriced high-MAX stocks.
  - Source: [Emerald JDQS](https://www.emerald.com/jdqs/article/32/2/159/1236382/The-role-of-arbitrage-risk-in-the-MAX-effect)
- **Cho (2021), JDQS 29(1), 2000-2016.** High-minus-low MAX: -1.94%/month (t -5.10) equal-weighted; -1.89% (t -3.40) value-weighted. The standalone effect is insignificant once idiosyncratic volatility is controlled. — [Emerald JDQS](https://www.emerald.com/jdqs/article/29/1/29/195322/Extreme-returns-and-idiosyncratic-risks-evidence)
- **Eom, Lee, Park, Jang, Park (2014), KJFS 43(4), July 1992 to June 2012.** Idiosyncratic volatility is significantly negatively related to future returns after controls for reversal, momentum and turnover. The effect concentrates in down markets and outside January. — [DBpia abstract](https://dbpia.co.kr/Journal/articleDetail?nodeId=NODE07228272)
- **Local check, long-short (equal-weighted unless noted), February 2001 to September 2026:**

  | Signal | Gross %/month (t) | Sharpe net35 / 2x | Positive years |
  |---|---|---|---|
  | Low volatility (63-day) | 2.40 (6.31) | 0.91 / 0.72 | 85% |
  | Low volatility, VW | 2.29 (4.09) | 0.63 / n/a | n/a |
  | Low turnover | 2.42 (6.00) | 0.84 / 0.60 | 88% |
  | Low MAX | 1.95 (6.55) | 0.59 / -0.02 | 85% |

  - Pairwise correlations among the three are 0.83 to 0.93.
  - For every one, the long leg minus the universe is small (low volatility: +0.25%/month, t 1.25). The short leg (the riskiest decile) minus the universe is about -1.6% to -2.4%/month.
  - Source: [P6 local check p6_sorts.py](/home/claude/datalab/scripts/p6_indicative/p6_sorts.py); [p6_regime_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_regime_f01.py)
- **Local check, low-risk as a long-only tilt.** A composite of low volatility, low MAX and low turnover, top quintile, February 2001 to September 2026:
  - Equal-weighted, net of 35 bp: +0.12%/month over the equal-weighted universe (t 0.75).
  - Value-weighted, net: -0.50%/month versus the value-weighted universe (t -2.16). Annual relative returns of -20.3 points in 2025 and -46.4 points in 2026.
  - Source: [P6 local check p6_final_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py)
- **Local check, lottery exclusion (long-only).** Drop the worst-decile composite stocks, about 135 of about 1,361 per month:
  - Equal-weighted: +0.23%/month net of 35 bp (t 8.25); +0.20 at 2x; 92% of years positive; +0.18 in 2020-26. Sharpe 0.31 to 0.44.
  - Value-weighted with a 5% cap: +0.04%/month (t 3.46).
  - Value-weighted excluding Samsung and SK hynix: +0.04%/month (t 3.36).
  - Source: [P6 local check p6_excl2.py](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py); [p6_exclusion_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_exclusion_hold.py)

**Size, value, quality**
- **Kang (Korea, July 2002 to June 2015, 2x3 sorts).**
  - SMB: 0.16%/month (t 0.45), insignificant.
  - HML: 1.05% (t 3.41).
  - RMW (quarterly profitability): 0.65% (t 2.75).
  - CMA: 0.66% (t 3.57).
  - Gross, IS. Source: [KFA 2016 conference paper (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf)
- **Kim (2021).** Risk premia exist in Korea for size, value, momentum, profitability and low risk, with size the highest. Removing unintended negative factor exposures improves multifactor returns. — [PBFJ 67](https://www.sciencedirect.com/science/article/abs/pii/S0927538X21000652). This conflicts with Kang's and P6's insignificant size premium.
- **Local check, size.** Small-minus-big deciles, equal-weighted: 0.28%/month (t 0.87); Sharpe net of 35 bp -0.02. Annual sums of -29.3 points in 2025 and -25.7 points in 2026 (to September). — [P6 local check](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv)
- **Mispricing and investor types.** Kim, Kang and Roh (2025) build a mispricing measure from 26 significant Korean anomalies. Individuals are the uninformed traders who create the anomalies. Only asset-management institutions and registered foreigners exploit them. — [PBFJ 90, RePEc](https://ideas.repec.org/a/eee/pacfin/v90y2025ics0927538x24003743.html)

**Earnings drift**
- **Shin, Shin and Kim (2019), Korea, 2002Q4-2017Q4.**
  - Unconditional 60-day market-adjusted drift spread: 4.80% (t 9.35).
  - 6.93% (t 8.19) when market sentiment trends up; 3.49% when it trends down.
  - Gross, IS. Source: [Sustainability 11(18), MDPI](https://www.mdpi.com/2071-1050/11/18/5137)
- **Eom, Hahn and Sohn (2019).** Individuals trade against earnings surprises. Drift exists only in stocks where individuals trade against the news, and it is larger with heavier contrarian individual trading. — [PBFJ 53, RePEc](https://ideas.repec.org/a/eee/pacfin/v53y2019icp379-398.html)
- **Choi and Cho (2021).** More related-party transactions increase drift, especially in chaebol firms (1,286 firm-years, 2015-2018). — [FRL](https://www.sciencedirect.com/science/article/abs/pii/S1544612320317293)

**Investor-type flows**
- **Choe, Kho and Stulz (1999).** Foreigners showed strong positive-feedback trading and herding before the 1997 crisis. The market adjusted quickly to their large sales, with no destabilising effect. — [NBER w6661, RePEc](https://ideas.repec.org:443/p/nbr/nberwo/6661.html)
- **Choe, Kho and Stulz (2001 and 2004/05).**
  - Foreigners sell to domestic investors before large positive abnormal returns and buy before large negative ones.
  - Domestic individuals, not institutions, hold the short-lived edge.
  - Foreign money managers pay 21 bp more on purchases and receive 16 bp less on sales (trade-weighted daily).
  - Source: [NBER w8073](https://www.nber.org/papers/w8073); [NBER w10502](https://www.nber.org/papers/w10502)
- **Kim and Byun (2011), 2003 to April 2011.**
  - Lagged (t-1) foreign and institutional net-buying intensity has a significant negative effect on the next close-to-close return.
  - It has a positive effect on the next close-to-open return.
  - Same-day intensity is positively related to returns.
  - Source: [Korea Science (PDF)](https://koreascience.kr/article/JAKO201103750648232.pdf)
- **Yu and Jang (2012), 22 large caps, 2004-2010.** Following foreign net buying underperformed KOSPI. Following institutions beat KOSPI in 20 of 22 stocks. — [Hanyang ScholarWorks (PDF)](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download)
- **Richards (2005).** Foreign flows into six Asian emerging markets show positive-feedback trading, with price impacts "much larger than earlier estimates". — [JFQA, RePEc](https://ideas.repec.org/a/cup/jfinqa/v40y2005i01p1-27_00.html)

####### Inferences
- **Momentum.** The "Korean negative momentum" result in Eom et al. (2020) is not robust to a survivorship-free re-run. Likely causes:
  - Their Table 3 reports monthly averages with a 1-month hold and a skip month, so the gap is not a units mismatch (excess-versus-raw returns shift both legs by under 0.5%/month and cannot explain it). More likely it is sample construction: they exclude the top-volatility decile and keep December fiscal-year non-financials only, and their database's handling of delistings and suspended or managed stocks may differ.
  - The robust local facts: short-horizon (3-6 month) momentum is weak or negative in high-turnover stocks, and the most recent month reverses. That is why the skip and the 12-7 window matter.
  - Korea's 12-1 momentum should be treated as "positive on average, fragile, with 2017-21 losses", not "negative".
- **Reversal.** One-month and 5-day reversal is a gross anomaly that QUANTGEN cannot harvest at 35 bp per side. Its edge has fallen about 75% since 2001-09 (1.55 to 0.41%/month; weekly 0.64 to -0.03%/week). The prior design's volume filter selects continuation, not reversal.
- **Lottery and low risk.** This is a short-leg phenomenon, partly because shorting small Korean stocks was banned or impractical for long stretches. It belongs in QUANTGEN as an exclusion screen and a risk flag, not as an alpha tilt. A value-weighted low-risk tilt loses badly in concentrated, momentum-led bull markets (2025-26).
- **Fundamentals.** Earnings drift, value and profitability are the most "fundamental" Korean signals with academic support and low turnover. They are the best candidates for the 35 bp cost structure but need OpenDART point-in-time data.

####### Gaps
- Abstracts and results that could not be opened (CAPTCHA, 403 or robots.txt): Ko and Kim, "저변동성 이상현상과 투자전략의 수익성 검증" (KCI ART001885142); Chae and Eom (2009); Lee (2014, APJFS) on news and momentum; KCI papers on 52-week high and crash risk (ART002739222); low-beta and lottery (ART002915381); idiosyncratic-volatility robustness (ART002377110); investor-type predictability (ART001162926).
- No Korean-journal net-of-cost study of short-term reversal was found.
- No Korean quality-composite study (GP/A, accruals, leverage) with post-2015 data was found. Kang's RMW sample ends June 2015.
- Earnings-drift net-of-cost evidence for Korea was not found.
- Dividends are missing from the local returns. This understates value and low-volatility long legs by roughly the dividend-yield spread (not measured).


### [P6] Revised weight table (Q5) (lines 574-633)

###### Q5. QUANTGEN translation: revised per-market x per-family weight table (0-3) and Korea-specific constraints

####### Takeaway
Revised table, families as in the prior design plus three columns:
- "Lottery-excl" is an exclusion screen, not a tilt.
- "52wH" is nearness to the 52-week high.
- "Value+Q" is the value-plus-profitability composite.

Weights are design priors, not gate results. Any weight of 2 or more for Korea still needs a PASS card.

The main changes from the prior Korea row:
- Short-term reversal falls from 3 to 1 and flow from 3 to 1.
- Earnings drift falls from 3 to 2, pending a point-in-time DART test.
- Low volatility as a tilt falls from 2 to 1.
- Quality rises from 1 to 2.
- Cross-sectional momentum stays at 1, but only as 12-7 or the 52-week high; the new 52-week-high tilt is weighted 2 and flagged.
- New: a lottery-exclusion screen at 3.

####### Cited Findings
The table synthesises the findings cited in Q1-Q4; each cell's justification lists its sources.

| Market | XS-mom | ST-rev | Value | Quality | Low-vol | Flow | Earn. drift | TS-mom | **Lottery-excl (new)** | **52wH (new)** |
|---|---|---|---|---|---|---|---|---|---|---|
| Prior Korea | 1 | 3 | 2 | 1 | 2 | 3 | 3 | 2 | n/a | n/a |
| **Korea (revised)** | **1** (12-7 / 52wH only) | **1** (gross real, net negative) | **2** (pre/post Value-up split) | **2** | **1** as a tilt | **1** (log; open-only effect) | **2** (DART pending) | 2 (unchanged; macro research) | **3** | **2** |
| Japan | 0 → **1** (only value-paired, residual or D-M-scaled) | 2 → **1** | 3 | 2 | 3 → **2** | 1 | 1 | 2 | 1 | 1 |
| China A | 0 | 3 | 1 → **2** (E/P, ex-shells) | 1 → **2** (GP) | 1 → **3** | 3 → **1** (untested) | 1 | 1 | **3** | 0 |
| Taiwan | 1 → **0** | 3 → **2** | 1 → **2** (CF/P) | 1 | 1 | 3 → **1** (untested) | 2 | 2 | 2 | 1 |
| EM (broad) | 3 → **2** | 1 | 2 → **3** | 2 → **3** | 1 → **2** | 2 → **1** | 1 | 3 | 2 | 1 |
| India | 3 | 1 | 2 | 3 | 2 | 2 | 2 | 2 | n/a | n/a |

India is unreviewed by P6 and kept as prior.

**Per-cell justification (Korea)**
- **XS-mom 1.** Literature conflicts (12-1 -6.13% versus +0.76 to +1.06%/month). Locally, equal-weighted 12-1 nets a Sharpe of 0.18 (-0.09 at 2x), while 12-7 nets 0.54 (0.10 at 2x). The strategy lost money in 2017-19 and 2021 and had a -22.3% month in July 2026. — [KJFS](https://www.e-kjfs.org/journal/view.php?number=901); [Bae and Lee](https://www.emerald.com/jdqs/article/29/1/49/195316/Illiquidity-duration-and-momentum-profits-evidence); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv)
- **ST-rev 1.** Gross 1-month reversal is 0.86%/month (t 2.70) but nets a Sharpe of -0.22. Weekly reversal nets -2.37. The volume-filtered version is about zero gross. Keep it as a guard (do not buy last month's top-decile winners) rather than a sleeve. — [Sim and Kim](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on); [P6 local weekly](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py)
- **Value 2.** HML 1.05%/month (t 3.41) over 2002-2015. The Korea discount and Value-up regime break justify a pre/post split. — [Kang (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [AMRO](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf)
- **Quality 2.** RMWq 0.65%/month (t 2.75). Profitability is robust across 28 EMs. Profitability (P/B plus ROE) is also the selection logic of Value-up. — [Kang](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [Hanauer and Lauterbach](https://www.sciencedirect.com/science/article/abs/pii/S1566014118304230); [KED Global](https://www.kedglobal.com/korean-stock-market/newsView/ked202409250005)
- **Low-vol 1 as a tilt.** The long-short is strong but lives in the short leg. As a long-only tilt it earns +0.12%/month equal-weighted (t 0.75) and -0.50%/month value-weighted (t -2.16), with 2025-26 relative returns of -20 and -46 points. — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py)
- **Flow 1.** Lagged foreign/institutional intensity is negative close-to-close and positive close-to-open. Copying foreign flow underperformed KOSPI. Foreigners trade at a disadvantage. — [Kim and Byun (PDF)](https://koreascience.kr/article/JAKO201103750648232.pdf); [Yu and Jang (PDF)](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download); [NBER w10502](https://www.nber.org/papers/w10502)
- **Earnings drift 2.** A 4.80% 60-day spread (t 9.35, 2002-2017), driven by individuals trading against the news. Low turnover suits 35 bp costs, but there is no Korean net-of-cost or post-2017 evidence. — [MDPI](https://www.mdpi.com/2071-1050/11/18/5137); [Eom, Hahn, Sohn](https://ideas.repec.org/a/eee/pacfin/v53y2019icp379-398.html)
- **Lottery-exclusion 3.** Locally +0.23%/month equal-weighted net (t 8.25), positive in 92% of years and in every subperiod; small but positive value-weighted (+0.04). Consistent with Cheon and Lee, Goh and Kim, Cho, and Eom et al. (2014). — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py); [Cheon and Lee](https://www.sciencedirect.com/science/article/abs/pii/S0927538X17304870); [Goh and Kim](https://www.emerald.com/jdqs/article/32/2/159/1236382/The-role-of-arbitrage-risk-in-the-MAX-effect)
- **52wH 2.** A local equal-weighted long-only tilt earns +0.34%/month net (+0.55 with lottery exclusion), but +0.09 at 2x and about zero capped value-weighted. Ryu (2021) and Goh and Jeon (2017) support anchoring on the 52-week high in Korea. Internationally the profits do not survive costs. — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py); [Kyobo](https://scholar.kyobobook.co.kr/article/detail/4010028467563); [Liu, Liu, Ma](https://ideas.repec.org/a/eee/jimfin/v30y2011i1p180-204.html)

**Korea-specific constraints for every Korean stock card**
1. **Long-only, size-tiered costs.** Keep 35 bp per side for the top 20% of caps (where the 0.20% sell tax is averaged over both sides). Add the measured half-spread for smaller tiers: Corwin-Schultz medians imply half-spreads of 27-39 bp below the top 20%. Run 2x as usual. — [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_micro.py); [Herald Economy](https://biz.heraldcorp.com/article/10627001)
2. **Price limits.** Flag stocks that closed within 1% of ±30% or had a static VI on day t. Never compute reversal from a limit-locked close. For a stock locked at the limit on day t, simulate entry at the t+1 open rather than the t close, since a locked close cannot be traded (see DC-P6-06). — [Eom, Kwon, La, Park 2022](https://www.mdpi.com/1911-8074/15/3/105)
3. **Short-sale regime as a logged state.** Tag each holding month as full ban, partial (index stocks only) or allowed. Report the anomaly by regime. — [KCMI](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517)
4. **Concentration.** Capped weights (for example 5%) or equal weights for cross-sectional tests. Report every value-weighted result with and without Samsung and SK hynix (55.5% of KOSPI). — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/)
5. **Universe hygiene.** Exclude preferred shares, SPACs, KONEX, managed/warning-designated stocks and stocks under KRW 1,000. Require at least 15 traded days. Include delisting returns. Treat January 2001 and other KOSDAQ-bubble months (1999-2001) as stress tests, not training data.
6. **Investor-type flow.** Use only as a logged context variable. Any flow card must be decided with data published by the t close and earn from t+1 open or close, labelled separately (BL-D01).

####### Inferences
- The revised Korea row puts its weight on low-turnover fundamental families (value plus quality, earnings drift) and on a risk screen (lottery exclusion). This matches QUANTGEN's high per-side cost and long-only, read-only design better than the prior's reversal and flow emphasis.
- Conflict with the macro research: it holds "reversal and quality at 1.0x". P6 agrees on quality, but recommends that the Korean reversal sleeve not be built as a standalone card at stock level, because it is negative net at 35 bp. The 1.0x rule then applies only to an index-level reversal (for example the KOSPI day-after-a-5%-fall pattern, which is a different test). Flagged for the report writer, not re-litigated.

####### Gaps
- No primary data on China A, Taiwan and EM costs or data access through KIS. Those rows are priors only.
- None of the new Korea weights has a gate result yet. They are hypotheses for the experiments in Q6.


### [P6] Failures, five experiments, data checks (Q6) (lines 634-756)

###### Q6. Where and when it failed, the first five experiments on KRX stock-level data, and data-check requests

####### Takeaway
Every Korean family has dated failure episodes:
- Momentum: 2017-2019 and 2021, and -22.3% in July 2026.
- Reversal: 2015 and 2025-26.
- Low volatility and MAX: January 2005, 2015, 2020 and early 2026.
- 52-week high: 2008-09 and April 2020.
- Size: 2003 and 2024-26.

Failures cluster in retail-mania rebounds and in concentrated mega-cap rallies. The first five experiments should settle:
1. lottery exclusion;
2. the momentum term structure;
3. whether reversal is feasible after costs;
4. DART earnings drift;
5. value plus quality across the Value-up break.

####### Cited Findings
**Where and when it failed (dated episodes).**
- Local results are equal-weighted long-short gross, labelled by holding month. — [P6 local p6_sorts_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_sorts_hold.py)

  | Signal | Worst months | Losing years (annual sums) |
  |---|---|---|
  | 12-1 momentum | Jul 2026 -22.3%; Nov 2014 -13.2%; Jan 2012 -12.9%; Feb 2017 -12.3% | 2017 -5.2, 2018 -16.4, 2019 -17.6, 2021 -22.6, 2009 -14.7 |
  | 12-7 momentum | Jul 2026 -15.5%; Apr 2009 -12.9% | 2021 -16.7 |
  | 1-month reversal | Jan 2005 -19.1%; Sep 2001 -18.0%; May 2015 -13.6%; May 2026 -12.0% | 2015 -25.6, 2025 -13.6, 2026 YTD -12.6 |
  | Low volatility | Jan 2005 -29.9%; May 2005 -20.6%; Oct 2001 -20.3%; Jan 2018 -18.4% | 2015 -17.9, 2020 -15.0 |
  | Low MAX | Jan 2005 -20.6%; Apr 2026 -14.9%; Jan 2018 -14.1%; Aug 2026 -13.1% | 2015 -20.7, 2020 -10.0 |
  | 52-week-high nearness | Apr 2020 -26.6%; Oct 2001 -24.8%; Dec 2008 -24.0% | 2008 -14.0, 2009 -25.8, 2020 -17.0 |
  | Small size | n/a | 2003 -42.1, 2017 -24.4, 2025 -29.3, 2026 YTD -25.7 |

- **Weekly 5-day reversal** (gross annual sums, by formation year): 2014 -27.7, 2023 -22.3, 2025 -31.9. From 2020 to 2026 the gross mean is -0.03%/week. — [P6 local p6_weekly_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py)
- **Long-only low-risk tilt (value-weighted top quintile) against the value-weighted universe, net of 35 bp:** 2009 -29.5 points, 2025 -20.3, 2026 YTD -46.4. Only 35% of years are positive. — [P6 local p6_final_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py)
- **Lottery exclusion (equal-weighted) worst year:** 2015, -1.6 points. — [P6 local p6_exclusion_hold.py](/home/claude/datalab/scripts/p6_indicative/p6_exclusion_hold.py)
- **2023-25 short-sale ban.** It did not support prices: KCMI reports KOSPI -10.1% and KOSDAQ -22.8% in 2024 (window as reported), and Korea was the weakest major Asian market. — [KCMI 2025](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517)
- **2020-21 ban.** Price efficiency fell, and extreme positive returns became more frequent. — [KCMI 2023](https://www.kcmi.re.kr/en/report/report_view?report_no=1521)
- **23 Jun 2026.** KOSPI fell 9.99%, retail bought a record KRW 8.54tn, and seven SK hynix leveraged ETFs fell 25.6% on average. — [Seoul Economic Daily](https://en.sedaily.com/markets/2026/06/23/kospi-plunges-10-percent-on-chip-concentration-leverage)
- **Japan momentum.** About 30 years of no profit to 2011. — [Asness 2011 (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-that-Proves-the-Rule). WML -0.08%/month over 1989-2011. — [FF 2012](https://www.johnhcochrane.com/s/Fama_French_size_value_momentum_JFE.pdf)
- **Taiwan momentum.** A documented exception over 1982-2020. — [Chen, Hsieh, Lee 2023](https://www.sciencedirect.com/science/article/abs/pii/S0927538X23000094)
- **52-week-high momentum internationally.** Not significant in most of 20 markets after transaction costs. — [Liu, Liu, Ma 2011](https://ideas.repec.org/a/eee/jimfin/v30y2011i1p180-204.html)
- **Following foreign flows (Korea, 2004-2010).** Underperformed KOSPI. — [Yu and Jang 2012 (PDF)](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download)
- **TSE P/B request.** Marginal disclosers just below P/B 1 subsequently had lower valuations. — [Kitagawa, Liu, Nagata](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5866042)

####### Inferences
######## First five experiments (KRX stock-level; each a pre-registered card through the nine-step gate)

All five experiments share these settings:
- Decide at the close of day t and earn from t+1.
- Size-tiered costs (Q5 constraint 1), also at 2x.
- Universe hygiene as in Q5 constraint 5.
- Report equal-weighted, 5%-capped value-weighted, and capped value-weighted excluding Samsung and SK hynix.
- Report by short-sale regime and by subperiods 2001-09 / 2010-19 / 2020-26.
- Data: KIS stock OHLCV with investor-type flows (BL-D01/BL-D03), the marcap history file for backfill, and OpenDART for fundamentals.

1. **P6-X1: Lottery-exclusion screen (protective card, family weight 3).**
   - Signal: a composite rank of 63-day volatility, the month's maximum daily return, and 1-month turnover.
   - Rule: drop the worst decile from any Korean long book (base = equal-weighted or capped value-weighted universe, then each candidate sleeve).
   - Pass: excess over the base above 0 at 2x costs, at least 60% of years positive, and positive in each subperiod.
   - Daily-swing variant: also exclude any stock that hit ±29.5% or triggered a static VI on day t.
   - Local prior: +0.23%/month equal-weighted, +0.04%/month capped value-weighted, net.
2. **P6-X2: Momentum term structure.**
   - Signals: 12-1, 12-7, 12-0 (no skip), 52-week-high nearness, and residual momentum (36-month FF3-residual returns, scaled by residual volatility).
   - Splits: by turnover tercile.
   - Overlays: own-volatility scaling and the Daniel-Moskowitz bear gate on KOSPI state (the macro research's R-04).
   - Long-only top quintile against the universe.
   - Must report 2017-2021 and July 2026.
   - Embedded: the exact Eom et al. (2020) Table 3 replication (DC-P6-02).
   - Local prior: 12-7 net Sharpe 0.54 equal-weighted; 52-week-high long-only +0.34%/month net equal-weighted, about zero capped value-weighted.
3. **P6-X3: Reversal feasibility.**
   - Signals: 1-day, 5-day and 1-month reversal, long-only "buy losers" against the universe, by size tier.
   - Volume filter both ways (above 1.5 and below 0.7 times the prior 20-day average).
   - Limit-locked days excluded.
   - Each return split into overnight (close to open) and intraday (open to close).
   - Costs from measured KIS quote half-spreads (DC-P6-05).
   - Decision: no Korean stock reversal card unless the long-only version is positive at measured cost. The index-level KOSPI reversal (backlog BL-C02) is tested separately.
   - Local prior: gross 0.86%/month (monthly) and 0.30%/week (weekly); negative net; the volume-filtered version about zero.
4. **P6-X4: Earnings drift with point-in-time DART.**
   - Signal: SUE from preliminary-earnings disclosures (잠정실적) and periodic reports, timestamped by filing receipt (rcept_dt plus time, so a post-close filing counts as t+1). Alternative: the announcement return CAR[-1,+1].
   - Hold 60 sessions; long-only top quintile.
   - Interactions: individual net selling (Eom, Hahn, Sohn) and 52-week-high nearness (Goh-Jeon).
   - Pass: at 2x costs.
   - Literature prior: 4.80% 60-day spread (2002-2017, gross).
5. **P6-X5: Value plus quality across the Value-up break.**
   - Signals: E/P, B/M and CF/P plus GP/A, ROE and payout/buyback yield.
   - Point-in-time lags: annual reports at fiscal year-end plus 90 days, quarterly at plus 45 days, or the actual DART filing date.
   - Splits: excluding holding companies and financials; pre versus post 26 Feb 2024.
   - Add an event study of P/B deciles around 26 Feb 2024, 27 May 2024 and 24 Sep 2024.
   - Literature prior: HML 1.05%/month and RMWq 0.65%/month (2002-2015).

######## Data-check requests for the data lab
- **DC-P6-01.** Re-run p6_sorts.py on total returns (add DART or KRX cash dividends). Report how much the value, low-volatility and lottery long legs change.
- **DC-P6-02.** Exact replication of Eom et al. (2020) Table 3:
  - KOSPI plus KOSDAQ, holding months Aug 2000 to Jun 2019, December fiscal-year non-financials only (DART).
  - Drop the top decile of 12-month return standard deviation.
  - Turnover = average monthly volume over shares outstanding in the formation window; independent 30/40/30 x quintile sorts; equal-weighted; skip 1; hold 1.
  - Report winners minus losers, winners and losers, with delisting returns as given, and forced to -30% and -100%.
  - Settle: is high-turnover winners minus losers below -5%/month (paper) or about +0.6 to +1.4% (P6 local)?
- **DC-P6-03.** The P6-X1 card through all nine gate steps, with every exclusion-threshold variant (5%, 10%, 20%) counted as a trial.
- **DC-P6-04.** 1-day and 5-day reversal on daily data:
  - Decide at the t close and earn the t+1 close-to-close return, then split it into the t+1 overnight and the t+1 intraday leg.
  - Report by volume ratio (below 0.7, 0.7-1.5, above 1.5) and by size tier.
  - Report the share of the gross edge earned overnight, which a decide-at-close desk cannot capture after costs.
- **DC-P6-05.** Spread calibration:
  - KIS quote snapshots for 200 stocks stratified by size bucket over 20 sessions.
  - Quoted half-spread at about 15:15 (before the closing auction) and at 09:05.
  - Compare with the Corwin-Schultz medians (39-79 bp full spread) and set tier costs.
- **DC-P6-06.** Price limits:
  - After a limit-up close (≥ +29.5%), the t+1 open-to-close and close-to-close returns, 15 Jun 2015 to 2026, against ≥ +14.5% closes in 1998-2015.
  - Re-run the 1-month reversal and MAX sorts excluding stocks with a limit day in the formation month.
- **DC-P6-07.** Short-sale regime:
  - Pooled regression of each family's short-leg excess return on regime dummies (full ban, partial, allowed), with Newey-West errors.
  - Plus the May 2021 KOSPI 200 / KOSDAQ 150 entry/exit difference-in-differences for lottery-stock short legs.
- **DC-P6-08.** Ken French international files (Japan, Asia Pacific ex Japan, Emerging):
  - HML, WML, RMW and CMA over April 2011 to the latest month, as out-of-sample tests against Fama-French 2012 (Japan WML -0.08, HML 0.48; Asia Pacific WML 0.69, HML 0.62%/month).
  - Daniel-Moskowitz scaling on Japan WML.
  - Note: this sandbox could not download the files (egress 403); the lab's local copy ends in 2018.
- **DC-P6-09.** Concentration: every value-weighted Korean result repeated with a 5% cap and excluding 005930 and 000660.
- **DC-P6-10.** Value-up event study: P/B-decile cumulative abnormal returns (CAR) around 26 Feb 2024, 27 May 2024 and 24 Sep 2024, and around the July and August 2025 Commercial Act revisions (dates to be taken from the National Assembly record). Plus a post-Feb-2024 versus pre-Feb-2024 HML comparison.

####### Gaps
- The experiments need DART fundamentals (P6-X4 and P6-X5) and KIS quote snapshots (P6-X3). Neither exists in the local lab today.
- No dated Korean value or quality failure episodes could be computed locally, because there are no fundamentals in the marcap file.


### [P6] Claims ledger (lines 757-816)

###### Q7. Claims ledger (P6-C01 to P6-C28)

####### Takeaway
There are 28 claims:
- **Nine BUILD-candidates**, each needing a PASS card first: C11, C12, C13 (as an exclusion), C15, C16, C19, C20, C25 (limit-day rule), C26 (cost tiers).
- **Four BACKLOG:** C04, C10, C17, C24.
- **Six DROP:**
  - C03: standalone Japan momentum;
  - C08: stock-level reversal as a sleeve;
  - C09: the volume-filtered 5-day reversal;
  - C14: low-vol as a long-only tilt;
  - C18: size;
  - C21: flow as a close-to-close alpha.
- **Nine CONTEXT:** C01, C02, C05, C06, C07, C22, C23, C27, C28.

Tiers:
- **T1** is peer-reviewed or official.
- **T2** is bank, asset manager, major press or index provider.
- **"T1-local"** is P6's in-sample check on KRX marcap data. It is not peer-reviewed and must be re-run by the data lab.

####### Cited Findings

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P6-C01 | Standalone stock momentum is insignificant in every East Asian market in the 40-country GJM sample. | 6/6 momentum to Dec-2000: Korea -0.76%/mo (t -0.80), Japan 0.02, Taiwan 0.01, China -0.01; Asia 0.32 (t 1.64) vs Europe 0.77 (t 8.15). Gross, IS. | [GJM 2003](https://gyanresearch.wdfiles.com/local--files/alpha/Momentum.pdf) | T1 | Consistent with FF 2012 (Japan), LSY (China), Chen et al. (Taiwan) | Asia average positive but weak | CONTEXT: start East Asian XS-mom weights at 0-1, not 3 |
| P6-C02 | Momentum profits rise with national individualism, which predicts weak momentum in Korea, Japan, Taiwan and China. | Positive relation of momentum to Hofstede individualism, robust to controls (country numbers not obtained). | [Chui-Titman-Wei 2010](https://econpapers.repec.org/RePEc:bla:jfinan:v:65:y:2010:i:1:p:361-392) | T1 | Published JF; 52-week-high momentum is NOT explained by individualism (Liu-Liu-Ma) | Not applicable | CONTEXT: prior for low XS-mom weights in collectivist markets |
| P6-C03 | Japanese stock momentum has had no standalone premium but pays as a hedge to value. | Japan 1974-2011: momentum 1.7%/yr (t 0.57), value 12.0% (t 4.31), combo Sharpe 0.78, correlation -0.64. FF: WML -0.08%/mo (t 0.25), 1989-2011. Gross, IS. | [AMP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf); [FF 2012](https://www.johnhcochrane.com/s/Fama_French_size_value_momentum_JFE.pdf); [Asness 2011](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-that-Proves-the-Rule) | T1 | Two independent datasets; no post-2011 OOS obtained | 1974-2011 "near 30 years" without profit | DROP standalone Japan XS-mom; BACKLOG value+mom pair (DC-P6-08) |
| P6-C04 | Dynamic (Daniel-Moskowitz) scaling or market-state conditioning rescues part of Japanese momentum. | Japan WML Sharpe 0.067 → 0.416 (D&M Table 11); momentum higher when market state persists. | [QUANTGEN_MACRO_INTEGRATION.md](claude/QUANTGEN_MACRO_INTEGRATION.md); [Hanauer 2014](https://ideas.repec.org/a/bla/irvfin/v14y2014i1p141-160.html) | T1 | IS in the original paper | Frequent state transitions in Japan | BACKLOG: test on French Japan WML after 2011 |
| P6-C05 | Outside the US, anomalies have not reliably decayed after publication. | 241 anomalies, 39 markets; only the US shows a reliable post-publication decline. | [Jacobs-Müller 2020](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html) | T1 | JFE; meta-analysis | Korea's local time decay (C08, C10) contradicts it for reversal | CONTEXT: keep the 60% live haircut for Korea anyway (time decay, not publication) |
| P6-C06 | In China A, past returns at all horizons predict reversal and there is no momentum. | 2000-2016: 1-month reversal CAPM alpha 1.49%/mo (t 3.07); JSZ 2008-20: reversal 1.41 (t 4.09), momentum 0.04 (t 0.11). Gross, IS. | [LSY](https://www.nber.org/system/files/working_papers/w24458/w24458.pdf); [JSZ](https://www.cfrn.com.cn/uploads/fileupload/a86579f7d6fb4328b45fa45156d074f7/paper/2a7aea538ad943c4b4220e51ec6dbfe5.pdf) | T1 | Replicated across samples | No net evidence | CONTEXT: China A XS-mom 0, ST-rev 3 (no data path) |
| P6-C07 | Clientele drives the sign: retail-dominated A shares reverse, foreign-institutional B shares of the same firms show momentum. | 2001-2018: B momentum 1.15%/mo VW (t 3.33) vs A 0.27 (n.s.); A reversal 1.2% EW (t 4.93), B n.s.; A retail ≈ 85% of volume. | [Chui-Subrahmanyam-Titman, NBER w29453](https://www.nber.org/system/files/working_papers/w29453/w29453.pdf) | T1 | Natural experiment; working paper | Not applicable | CONTEXT: Korea's retail-heavy small caps should reverse more than foreign-held large caps |
| P6-C08 | Korea's 1-month reversal is real before costs but has decayed and is negative at QUANTGEN's costs. | Sim-Kim 1999-2021: r(-1) -2.950 (t -3.77). Local Feb-2001 to Sep-2026 EW L/S 0.86%/mo (t 2.70): 1.55 (2001-09) → 0.41 (2020-26); turnover 3.5/mo; net35 Sharpe -0.22; VW 0.04%/mo. | [Sim & Kim 2021](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv) | T1 / T1-local | Literature IS; local IS; not OOS | 2015 -25.6, 2025 -13.6, 2026 YTD -12.6 (annual sums) | DROP as a standalone stock card; keep as a do-not-buy-last-month-winner guard |
| P6-C09 | The prior design's volume-filtered 5-day reversal has no edge in Korea; high-volume losers continue down. | Local weekly 2001-2026: unfiltered gross 0.30%/wk (t 3.8), net35 Sharpe -2.37; filter (vol ratio > 1.5) gross 0.03%/wk (t 0.2); filtered losers minus universe -0.34%/wk (t -4.1). | [P6 local p6_weekly_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_weekly_f01.py) | T1-local | IS; one filter threshold | 2020-26 unfiltered gross -0.03%/wk | DROP the volume-filter spec for Korea; re-test the opposite (low-volume) filter in P6-X3 |
| P6-C10 | Korean 12-1 momentum is positive on average but fragile, not reliably negative as the KJFS headline suggests. | KJFS 2000-19 high-turnover W-L -6.13%/mo (t -4.76) vs local replication +0.58 (t 1.50) all caps / +1.42 (t 3.52) ex-micro; local 12-1 EW 0.76%/mo (t 2.37), net35 Sharpe 0.18, 2x -0.09; Bae-Lee VW 1.06 (t 2.53). | [Eom et al. 2020](https://www.e-kjfs.org/journal/view.php?number=901); [Bae & Lee 2021](https://www.emerald.com/jdqs/article/29/1/49/195316/Illiquidity-duration-and-momentum-profits-evidence); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_eom_x01.py) | T1 / T1-local | Conflicting; DC-P6-02 must settle | 2017-19, 2021 (-22.6), Jul-2026 -22.3% month | BACKLOG (P6-X2); XS-mom weight 1 |
| P6-C11 | The intermediate window (12-7) and skipping the latest month carry most of Korean momentum. | Sim-Kim pret(12,7) FF5 alpha 0.531%/mo (t 2.05) vs pret(6,2) -0.084; local 12-7 EW 1.30%/mo (t 4.91), net35 Sharpe 0.54 (2x 0.10); 12-0 ≈ 0 vs 12-1 up to 1.38 (t 3.25). | [Sim & Kim](https://www.emerald.com/jdqs/article/29/3/174/206550/The-effect-of-short-term-return-reversals-on); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_final_f01.py) | T1 / T1-local | Two sources agree; IS | 2021 -16.7; Jul-2026 -15.5% | BUILD-candidate (P6-X2), only with the vol-scaling and D&M gate per the macro research |
| P6-C12 | Nearness to the 52-week high is a Korean anchoring signal that helps an equal-weighted long book but not a cap-weighted one after costs. | Ryu 2021: GH/RR beat JT in Korea. Local EW top-quintile: +0.34%/mo net35 (t 2.31), +0.09 at 2x; with lottery exclusion +0.55 (t 3.63); capped VW +0.06 (t 0.40). | [Ryu 2021](https://scholar.kyobobook.co.kr/article/detail/4010028467563); [Goh & Jeon 2017](https://ideas.repec.org/a/eee/pacfin/v44y2017icp150-159.html); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py) | T1 / T1-local | Internationally fails after costs (Liu-Liu-Ma) | 2008 -14.0, 2009 -25.8, Apr-2020 -26.6% month | BUILD-candidate at weight 2, EW/capped small-mid book only |
| P6-C13 | MAX/lottery stocks earn very low subsequent returns in Korea, more so in volatile markets. | Cheon-Lee 1992-2016: VW low-minus-high MAX 2.40%/mo (US 0.66); Goh-Kim 2000-20: H-L -2.08 (t -5.01); Cho 2000-16: -1.94 (t -5.10); local EW 1.95%/mo (t 6.55). | [Cheon & Lee](https://www.sciencedirect.com/science/article/abs/pii/S0927538X17304870); [Goh & Kim 2024](https://www.emerald.com/jdqs/article/32/2/159/1236382/The-role-of-arbitrage-risk-in-the-MAX-effect); [Cho 2021](https://www.emerald.com/jdqs/article/29/1/29/195322/Extreme-returns-and-idiosyncratic-risks-evidence) | T1 | Replicated by 3 papers + local; IS | 2015, 2020; Apr-2026 -14.9% month | BUILD-candidate as exclusion (see C15), not as a tilt |
| P6-C14 | The Korean low-risk premium sits in the short leg; as a long-only tilt it is about zero (EW) or negative (cap-weighted). | Local L/S EW 2.40%/mo (t 6.31), net35 Sharpe 0.91; long leg minus universe +0.25 (t 1.25); composite long-only EW +0.12 (t 0.75), VW -0.50 (t -2.16) net. | [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_final_hold.py); [Eom et al. 2014](https://dbpia.co.kr/Journal/articleDetail?nodeId=NODE07228272) | T1-local / T1 | IS; dividends excluded (understates long leg) | VW relative -20.3 (2025), -46.4 (2026 YTD) | DROP as a tilt (weight 1); keep for risk display |
| P6-C15 | Excluding the most lottery-like decile improves a long-only Korean book in every subperiod. | Local Feb-2001 to Sep-2026: EW +0.23%/mo net35 (t 8.25), 2x +0.20, 92% of years positive; capped VW +0.04 (t 3.46); VW ex-Samsung/SK hynix +0.04 (t 3.36). | [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_excl2.py) | T1-local | IS; composite chosen ex ante from the literature; no deflation | Worst year 2015 (-1.6) | BUILD-candidate P6-X1 (weight 3) |
| P6-C16 | Korean earnings drift is large and is caused by individuals trading against the news. | 2002Q4-2017Q4: 60-day spread 4.80% (t 9.35); 6.93% when sentiment trends up. Drift only where individuals trade against the news. Gross, IS. | [Shin et al. 2019](https://www.mdpi.com/2071-1050/11/18/5137); [Eom, Hahn, Sohn 2019](https://ideas.repec.org/a/eee/pacfin/v53y2019icp379-398.html) | T1 | Two papers; no net or post-2017 evidence | Not applicable | BUILD-candidate P6-X4 (needs DART timestamps) |
| P6-C17 | Chaebol-style related-party transactions amplify Korean earnings drift. | 1,286 firm-years 2015-18; more RPT → larger drift, especially in chaebol firms. | [Choi & Cho 2021](https://www.sciencedirect.com/science/article/abs/pii/S1544612320317293) | T1 | Short sample | Not applicable | BACKLOG: interaction term in P6-X4 |
| P6-C18 | Size has no reliable premium in Korea. | Kang 2002-15 SMB 0.16%/mo (t 0.45); local small-minus-big EW 0.28 (t 0.87), net35 Sharpe -0.02; Kim 2021 reports a size premium (conflict). | [Kang (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [Kim 2021](https://www.sciencedirect.com/science/article/abs/pii/S0927538X21000652); [P6 local](/home/claude/datalab/scripts/p6_indicative/p6_krx_monthly_anomalies.csv) | T1 / T1-local | Conflicting | 2003 -42.1; 2025 -29.3; 2026 YTD -25.7 | DROP size as a signal; keep as a risk control |
| P6-C19 | Korean value and profitability premia were significant before Value-up. | Jul-2002 to Jun-2015: HML 1.05%/mo (t 3.41), RMWq 0.65 (t 2.75), CMA 0.66 (t 3.57). Gross, IS. | [Kang (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf); [Hanauer-Lauterbach (EM)](https://www.sciencedirect.com/science/article/abs/pii/S1566014118304230) | T1 | No post-2015 Korean evidence found | Not measured | BUILD-candidate P6-X5 (value 2, quality 2) |
| P6-C20 | The Korea discount is structural (governance and inheritance tax), and the 2024-26 reforms are a regime break for value signals. | KOSPI P/B 0.99 (10-yr avg) vs 2.65 advanced; ~70% of stocks P/B < 1 at end-2025; Value-up Index +89.4% vs market +75.6% in 2025; Commercial Act Jul/Aug 2025; inheritance tax up to 60%. | [AMRO 2026](https://amro-asia.org/wp-content/uploads/2026/03/Korea-ACV-2025-SI-3.pdf); [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/); [Seafarer](https://www.seafarerfunds.com/field-notes/seoul/2024/Q2/value-up/) | T1 / T2 | Official and think-tank sources; causal effect unmeasured | Gains concentrated in Samsung + SK hynix | BUILD-candidate: pre/post-2024 split in P6-X5; DC-P6-10 |
| P6-C21 | Lagged foreign and institutional net buying predicts the next open, not the next close; copying foreign flow underperformed. | 2003-2011: t-1 intensity negative for the close-to-close return, positive for the close-to-open; 2004-2010: following foreigners < KOSPI, following institutions > KOSPI in 20 of 22 stocks. | [Kim & Byun 2011](https://koreascience.kr/article/JAKO201103750648232.pdf); [Yu & Jang 2012](https://hanyang.scholarworks.kr/api/assets/9df82c36-bd3b-4089-af65-b5235f10bb6b/download) | T1 | Older samples; Korean-journal | Not applicable | DROP flow as a close-to-close alpha (weight 3 → 1); BACKLOG open-leg test |
| P6-C22 | Foreign investors trade at a disadvantage in Korea; domestic individuals hold a short-lived edge. | Foreigners pay 21 bp more on buys and receive 16 bp less on sales; they sell before large positive abnormal returns (1996-98). | [NBER w10502](https://www.nber.org/papers/w10502); [NBER w8073](https://www.nber.org/papers/w8073) | T1 | Published (RFS/JF versions) | Not applicable | CONTEXT: do not treat foreign buying as "smart money" |
| P6-C23 | Korean short-sale bans reduced price efficiency and did not support prices. | 2008: efficiency "dramatically decreased", price effect n.s.; 2020: efficiency and liquidity down, extreme positive returns up; May-2021 index experiment: shorting cut price delay by 0.14-0.15; 2024 ban: KOSPI -10.1%, KOSDAQ -22.8%. | [KCMI 2010 (PDF)](https://www.kcmi.re.kr/kcmifile/oldfiledata/weekly_6_4_567.pdf); [KCMI 2023](https://www.kcmi.re.kr/en/report/report_view?report_no=1521); [Kim & Kim 2024](https://www.e-kjfs.org/upload/pdf/KJFS-2024-08-53-4-393.pdf); [KCMI 2025](https://www.kcmi.re.kr/en/publications/pub_detail_view?syear=2025&zcd=002001017&zno=1840&cno=6517) | T1 | Several bans, consistent | KOSDAQ 150 results insignificant | CONTEXT: tag the short-sale regime on every Korean card (DC-P6-07) |
| P6-C24 | Short-sale regime does not consistently change Korean anomaly short legs. | Local, EW top decile minus universe: high-MAX -2.56 (ban 2023-25) vs -1.41 (resumption 2025-26); 12-7 losers -0.71 (restricted) vs -1.38 (allowed); post-resumption n = 18 months. | [P6 local p6_regime_f01.py](/home/claude/datalab/scripts/p6_indicative/p6_regime_f01.py) | T1-local | IS; tiny post-resumption sample | Not applicable | BACKLOG (INSUFFICIENT DATA): re-check in 2027 |
| P6-C25 | The ±30% price limits (since 15 Jun 2015) raised low-frequency volatility, and limit hits spike in retail manias. | Intraday realised vol +3.6% to +9.3% (2014-16, top 200); static VI adds < 2% stabilisation; local KOSDAQ up-limit hits 54.0 per 10k stock-days in 2026 vs 15-28 normally. | [Kim & Jun (arXiv)](https://www.arxiv.org/pdf/1805.04728); [Eom et al. 2022](https://www.mdpi.com/1911-8074/15/3/105); [P6 local p6_micro.py](/home/claude/datalab/scripts/p6_indicative/p6_micro.py) | T1 / T1-local | Consistent | 2020 and 2026 spikes | BUILD-candidate rule: flag and exclude limit-locked days (DC-P6-06) |
| P6-C26 | QUANTGEN's flat 35 bp per side understates the cost of trading the bottom 60% of KRX caps. | 2026 tax 0.20% (KOSPI 0.05 + 0.15 rural; KOSDAQ 0.20); local Corwin-Schultz median full spread 39 bp (top 5%) to 79 bp (bottom 20%), Jan-2024 to Sep-2026. | [Herald Economy](https://biz.heraldcorp.com/article/10627001); [P6 local p6_micro.py](/home/claude/datalab/scripts/p6_indicative/p6_micro.py) | T2 / T1-local | Estimator noisy and upward-biased (means 97-130 bp) | Not applicable | BUILD-candidate: size-tiered cost schedule after DC-P6-05 |
| P6-C27 | Low volatility, E/P value and gross profitability are robust in China A; low volatility is close to independent of other regions' VOL factors. | Nov-2000 to Dec-2018: VOL factor alpha 9.1% (t 3.72), Sharpe 0.88, CAPM alpha spread 16.1%/yr; JSZ 2008-20: idiosyncratic vol 1.56%/mo (t 5.24), gross profitability 1.10 (t 4.60). | [Blitz-Hanauer-van Vliet 2021](https://assets.ctfassets.net/tl4x668xzide/1QBgySFzYmwqGlDmSaFYay/b118ecac9f394202b5d657f33f5d5fab/the-volatility-effect-in-china.pdf); [JSZ](https://www.cfrn.com.cn/uploads/fileupload/a86579f7d6fb4328b45fa45156d074f7/paper/2a7aea538ad943c4b4220e51ec6dbfe5.pdf) | T2 / T1 | Asset-manager research plus academic replication | No net figures | CONTEXT: China A low-vol 3, quality 2 (no data path yet) |
| P6-C28 | The TSE 2023 P/B request changed payout behaviour, but its valuation effect is modest and uneven. | 815 of 1,656 Prime firms disclosed by Dec-2023; P/B < 1 share down about 4 pp; RD/DiD: modest short-run valuation gains, higher profitability; marginal disclosers lost value. | [DLRI 2024](https://www.dlri.co.jp/english/report_en/202402YK.html); [Kitagawa, Liu, Nagata (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5866042) | T2 / T1 (WP) | Working paper; short window | Marginal firms just below P/B 1 | CONTEXT: Japan value 3 with a capital-efficiency (ROE, payout) overlay |

####### Inferences
- The ledger's BUILD-candidates for Korea are low-turnover or protective (C11, C12, C15, C16, C19/C20, C25, C26), which suits a 35 bp per-side, long-only, read-only desk.
- All "T1-local" claims are in-sample and need the data lab's gate run before any card is believed.

####### Gaps
- Claims C02, C04, C17 and C28 rest on abstracts or secondary summaries rather than full tables.
- C10 needs DC-P6-02 to resolve the KJFS-versus-local conflict.


---

## P7_crypto_fx_tradingview_canon.md

### [P7] Persona and position summary (lines 1-22)

##### P7: Technical trading in crypto, FX and futures, and an audit of the practitioner canon (TradingView community scripts, CMT curriculum, classic system books)

As of 2 October 2026. Written for the QUANTGEN technical & fundamental signals research (see `00_QUANTGEN_context.md`). All numbers carry their market, period, in-sample (IS) or out-of-sample (OOS) status and gross or net label where the source gives them.

**Persona line.** P7, "Professor of Market Microstructure and Digital Assets". This is a fictional composite persona, not a real person. P7 studies crypto and FX trading and teaches a practitioner-facing seminar on technical analysis. The lens is market microstructure plus the adaptive-markets view: who takes the other side of a technical signal, what the trade costs, how the backtest engine fills the order, and whether the edge survives once execution gets cheaper and competitors get smarter.

**Position summary.**
1. Technical rules work in some markets and periods and not others. Where trends are large, costs are small relative to volatility and the marginal trader is unsophisticated, simple trend rules have earned credible OOS, net-of-cost premia. That describes crypto from 2010 to 2022, major FX in the 1970s and 1980s, and diversified commodity and financial futures. Where professional adoption and falling costs arrived, the same rules decayed to roughly zero: G10 FX after about 1990, US equity-index timing, and developed futures after 2009.
2. Crypto has the best modern evidence of any market reviewed here. Price-to-moving-average trend forecasts Bitcoin returns OOS, cross-sectional momentum over 1–4 weeks is priced, and a 28-indicator technical composite survives costs among large, liquid coins. This agrees with QUANTGEN's PASSing C3 card. However, almost all of this evidence predates the spot-ETF regime that began on 10 January 2024, so C3 needs a pre-registered post-ETF split and a decay monitor, not more parameter search.
3. For G10 FX the evidence says DROP. The OOS Sharpe has been about 0.06 since 1999 and turns negative after modest costs, which agrees with V3's rejection.
4. In the practitioner canon, only a few items have peer-reviewed support: moving-average and channel trend, oscillators used inside a cross-sectional composite, ATR as a volatility estimate, and nearness to the 52-week high. For Ichimoku, Supertrend, the Squeeze, UT Bot, WaveTrend, Connors RSI(2), TD Sequential, Wyckoff, Elliott waves and Fibonacci, CANSLIM/VCP as a system, and Lorentzian Classification, I found no rigorous OOS, net-of-cost test in this session.
5. Nearly every canon indicator is a re-parameterisation of three primitives: trend (price relative to a moving average or channel), short-term reversal (a recent-return z-score) and volatility (range). QUANTGEN should build these primitives once and count every indicator variant as a trial in the deflated-Sharpe count. It should never build an indicator as a monolithic "system".
6. TradingView backtests are optimistic by construction. Its documentation says more than 95% of indicators repaint in some form. A higher-timeframe request with lookahead and no offset leaks future data. Backtests on non-standard charts fill at synthetic prices. Pine v5 strategies defaulted to 0% margin. Realistic costs are something the publishing rules ask authors to set, not something the engine guarantees.
7. The closest systematic evidence on retail strategy libraries is a study of 888 Quantopian algorithms. In it, backtest Sharpe explained less than 2.5% of the variance in OOS Sharpe.
8. QUANTGEN should therefore treat every TradingView script as an unverified claim. Port its logic into point-in-time features, keep the "decide at the close of t, earn from t+1" rule, charge the pre-registered costs (crypto 10/20 bp, futures 5/10 bp, FX 10/20 bp per side), and let the nine-step gate decide.

**Research limitations (read first).**
- The session's web-search budget ran out early (200 of 200 calls).
- Several publisher and API pages were rate-limited (HTTP 429) or blocked. These include the Springer article "Cryptocurrency momentum has (not) its moments", the SSRN abstract page for Detzel et al., Wiley and Semantic Scholar pages, the detailed CMT curriculum pages, SG index history files, and the trading-cost subsections of the TradingView strategies page, which were truncated.
- "No rigorous test found" for a canon item below therefore means "not found with the tools available in this session". It does not mean none exists.
- Where a number comes from a working-paper version or a copy hosted by a third party, I flag it.


### [P7] Design, DO-NOT-BUILD, corrections (Q5) (lines 432-501)

###### Q5. Translating indicator logic into testable QUANTGEN features, and what to put on the DO-NOT-BUILD list

####### Takeaway
Build three primitive feature families once, point-in-time at the close of day t: trend/position, short-term reversal, and range-based volatility. Add abnormal volume and, for crypto, a funding/basis crowding gauge. Use ATR as a risk and stop input, not a signal, and apply stops only to trend sleeves. Test volatility compression only as a conditioning variable for breakouts. Put every repainting, look-ahead, synthetic-chart, subjective or monolithic "system" item on DO-NOT-BUILD.

####### Cited Findings (evidence anchors for the design)
- **Kaminski & Lo (Journal of Financial Markets 18, 2014).** They give a framework for when stop-loss rules add or subtract value. Their benefit depends on serial correlation (momentum) rather than a random walk. In daily index-futures data, some stop-loss policies at longer sampling frequencies raised expected return while sharply cutting volatility. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html)
- **Nagel (Review of Financial Studies 25(7), 2012).** Short-term reversal returns are compensation for supplying liquidity. They are highly predictable from VIX and rise in market stress. — [IDEAS/RePEc](https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html)
- **Jegadeesh (JF, 1990).** Negative first-order serial correlation in monthly stock returns is highly significant. Over 1934–87, the extreme-decile spread was 2.49% a month. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v45y1990i3p881-98.html)
- **Gao, Han, Li & Zhou (JFE 129(2), 2018).** On SPY, 1993–2013, the first half-hour return (measured from the prior close) predicts the last half-hour return. The effect is stronger on volatile, high-volume, recession and macro-announcement days. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html)
- **Gu, Kelly & Xiu (Review of Financial Studies 33(5), 2020).** Across machine-learning methods, momentum, liquidity and volatility are the most consistent predictors. Trees and neural networks capture interactions. — [NBER w25398](https://www.nber.org/papers/w25398)
- **Other anchors already cited:** Alizadeh-Brandt-Diebold 2002 (range volatility), George-Hwang 2004 (52-week high), Han-Zhou-Zhu 2016 (MA trend factor), Detzel et al. 2021 (BTC price/MA), Fieberg et al. 2025 (CTREND), Schmeling-Schrimpf-Todorov 2023 (crypto carry and crash risk), Gervais-Kaniel-Mingelgrin 2001 (abnormal volume), Neely-Rapach-Tu-Zhou 2014 (technical index-level forecasts work near peaks).

####### Inferences: the QUANTGEN design

**A. Feature specifications.** Every feature uses only information available at the close of t and is traded from t+1. Each named variant counts as a trial.

| ID | Feature (point-in-time) | Logic translated from | Evidence anchor | Sleeve / use | Status |
|---|---|---|---|---|---|
| F1 | `atr_n`: Wilder ATR (n = 14, 20) divided by close; also Parkinson range volatility over 20 days | Wilder ATR, Keltner, Supertrend and UT Bot bands | Alizadeh-Brandt-Diebold 2002 | Risk unit for sizing and stop distance (e.g., stop = 2–3 × ATR) in trend sleeves only; candidate replacement for close-to-close σ20 | **BUILD** as a risk input (not a signal). Stops on trend sleeves only (Kaminski-Lo) |
| F2 | `px_ma_L` = ln(C_t / SMA_L) for L = 10, 20, 50, 100, 200; `trend_vote` = mean of signs; MACD as the EMA version | MA crossovers, MACD, Parabolic/Supertrend direction | Detzel 2021; Han-Zhou-Zhu 2016; Neely et al. 2014; C3 | Crypto time-series trend (exists as C3); US cross-sectional trend factor; Korea to be tested (may be reversal at short L) | **BUILD-candidate** (US cross-section; crypto); Korea only via data-check DC-1 |
| F3 | `chan_pos_L` = (C − min L_L)/(max H_L − min L_L) for L = 20, 55, 252; `near_52wh` = C / max H over 252 days | Donchian/Turtle, Ichimoku midlines, CANSLIM/VCP "near highs" | George-Hwang 2004; Szakmary 2010; Lukac et al. 1988 | Cross-sectional stock feature; time-series trend variant | **BUILD-candidate** (`near_52wh`); `chan_pos` as a trend parameterisation |
| F4 | `vol_compress` = Bollinger width / Keltner width (squeeze when < 1); or the percentile of Bollinger width over 120 days | TTM/LazyBear Squeeze, VCP, Bollinger width | No peer-reviewed evidence found | Conditioning variable only: interact with F2/F3 breakout signals | **BACKLOG**. Pre-registered interaction test (DC-4); DROP if it fails |
| F5 | `rev_k` = −(k-day return)/σ for k = 1, 2, 5; RSI(2) and RSI(14) and %B as alternative transforms | RSI, Connors RSI(2), %B, WaveTrend, stochastic, CCI | Jegadeesh 1990; Nagel 2012; Chong-Ng-Liew 2014; CTREND | The short-term reversal sleeve (Korea weight 3); RSI only if it adds beyond `rev_k` (DC-3) | **BUILD** inside the reversal sleeve, not as separate cards |
| F6 | `vwap_dist` = (C − VWAP_t)/ATR from KIS intraday bars | VWAP bands | No alpha evidence found | Intraday horizon; execution benchmark for the simulated order book | **BACKLOG** (intraday). CONTEXT for cost modelling |
| F7 | `abn_vol` = V_t / mean(V over t−20 to t−1); OBV slope | Wyckoff/VSA volume reading, OBV, CANSLIM volume | Gervais-Kaniel-Mingelgrin 2001; Lee-Swaminathan 2000; Neely et al. 2014 (OBV) | Conditioning variable (prior design: reversal when volume ratio > 1.5) | **BUILD** as a conditioner |
| F8 | `trend_state_atr`: long/flat state that flips when C crosses a trailing ATR band (hysteresis) | Supertrend, UT Bot, Parabolic SAR, Turtle exits | Trend family (above) | Variant inside the trend family (C3 already uses hysteresis) | Variant; count as a trial |
| F9 | `funding_z` / `basis_z` for BTC and ETH: z-score of the 7-day mean perp funding (Binance public data) or futures basis vs its 1-year history; multiplier m in [0.5, 1.0] that falls when z is high | Crypto-native crowding gauges | Schmeling-Schrimpf-Todorov 2023; He et al. 2026 | Down-only sizing overlay on C3 | **BACKLOG** (DC-9) |
| F10 | `ctrend_lite`: elastic-net combination of F2, F3, F5, F7, MACD and Bollinger width across the top 100 Upbit/Binance coins by 30-day volume; weekly; long-only top quintile vs BTC | CTREND; Lorentzian-style "ML on indicators", done properly | Fieberg et al. 2025 | New crypto cross-sectional card | **BACKLOG** (strong candidate; DC-10) |

**B. DO-NOT-BUILD list** (and port-rejection rules for any TradingView logic)
1. Same-bar fills: any rule that decides and fills on the same close (Pine `process_orders_on_close = true`) or evaluates intrabar (`calc_on_every_tick`). This violates "decide at t, earn from t+1".
2. Higher-timeframe values not yet confirmed at t (`request.security(..., lookahead_on)` without a `[1]` offset), including weekly or monthly indicator values used on daily bars before the period has closed.
3. Signals plotted or used with negative time offsets, such as Ichimoku's lagging (Chikou) span used as a signal, ZigZag, and `ta.pivothigh`/`pivotlow` levels placed at the pivot bar. Only values confirmed at t may be used.
4. Backtests on Heikin Ashi, Renko, Kagi, point-and-figure or range bars, including UT Bot's Heikin Ashi mode.
5. Elliott-wave counts, Fibonacci retracement and extension levels, and Gann tools: subjective, with no evidence found.
6. DeMark TD Sequential counts, Wyckoff phase labels and VSA bar classes. Only the volume and range content survives, as F7, F1 and F4.
7. "Machine Learning: Lorentzian Classification" and similar community ML scripts. In-chart "Trade Stats" are not backtests, which the author says. If machine learning is wanted, use F10 with purged walk-forward validation, labels only from bars already realised by t, and every hyper-parameter counted as a trial.
8. Crypto day-of-week, weekend, Monday, January and Halloween rules; these anomalies did not persist.
9. Technical rules and momentum on G10 FX: OOS collapse since 1990–1999, and V3 is already REJECTED.
10. Chart-pattern recognisers (head-and-shoulders, double tops, triangles): dominated by simple trend rules.
11. One-minute or intraday crypto MA rules at QUANTGEN's 10 bp per side, because turnover makes costs dominant.
12. Pivot points and round-number support/resistance as daily-swing signals.
13. Composite "systems" used as monoliths (CANSLIM, VCP, Turtle with pyramiding, multi-indicator confluence scripts). Decompose them into F-features with their own evidence.
14. Any parameter set tuned on TradingView with zero commission or slippage or margin = 0. Re-derive it at QUANTGEN costs and count each tuned variant as a trial.
15. Exits where a stop and a target both sit inside the same daily bar and the outcome depends on an assumed intrabar path. Treat such bars as stop-first (worst case).

**C. Corrections and flags for the prior design** (macro decisions are not re-litigated)
- **Crypto per-market weights.**
  - TS-mom 3: confirmed.
  - XS-mom 1: keep. Momentum over 1–4 weeks is significant in Liu-Tsyvinski-Wu but null in Grobys-Sapkota.
  - Add a "technical composite" line with a provisional weight of 2, pending DC-10.
  - Lower ST-rev from 2 toward 0–1 until tested, because the fetched literature shows short-horizon cross-sectional *momentum*, not reversal.
  - Flow 2: lower to 1 until tested. The attention evidence is in-sample (2018 working paper), and ETF flows follow price rather than lead it (Oefele).
- **Futures and FX TS-mom "strong".** Correct this to "strong only for broad multi-market books and long lookbacks; weak in G10 FX since the 1990s and in narrow post-2009 books" (Hutchinson; Hsu-Taylor-Wang; Hurst; Lempérière; QUANTGEN B3).
- **Volatility scaling.** Consistent with the macro research. Kim-Tse-Wald show that scaling drives TSMOM's apparent alpha, so it belongs on momentum and trend sleeves and benchmarks should be vol-scaled. ATR (F1) may replace σ for short-horizon crypto sizing, but the macro sleeve scaling (σ126, 12% target, cap 1.0) stays.
- **Reversal sleeve held at 1.0x.** Nagel (2012) shows reversal returns rise when VIX is high. That supports not cutting the reversal sleeve in stress, so there is no conflict. Any desire to up-weight it in stress is blocked by the macro rule capping overlays at 1.0.
- **Funding/basis overlay.** It follows the same down-only [0.5, 1.0] convention as the macro overlays. Note that it is a market-internal crowding variable, not a macro variable.

**D. Porting protocol for any TradingView or CMT idea**
1. Write the indicator as a pure function of OHLCV available at t.
2. Prove there is no look-ahead with a shift test: the signal computed with data to t+1 must equal the signal at t+1, and computing it on data truncated at t must change nothing for dates up to t.
3. Map it to F1–F10. If it is a re-parameterisation, add it to that family's plateau grid (gate step 7) and to the trial count (step 3) instead of creating a card.
4. Run the gate at base and 2x costs.
5. Report pre-2024 and post-2024 results for crypto.

####### Gaps
- No peer-reviewed evidence was found for volatility compression (F4) or VWAP distance (F6) as return predictors, so both remain BACKLOG with a pre-registered kill rule.
- The thresholds for the funding/basis multiplier (F9) have no published calibration that I could verify, so they must be set before testing and counted as trials.


### [P7] Where and when it failed (lines 504-527)

###### Where and when it failed (mandatory)

| Episode (dates) | What failed | Numbers | Source |
|---|---|---|---|
| 1970s–80s, then early 1990s | Filter and MA rules in major FX | Excess returns of about 8%/yr in the 1970s–80s disappeared by the early 1990s; Olson: about zero by the 1990s | [Neely-Weller-Ulrich 2009](https://gpbib.cs.ucl.ac.uk/gp-html/Neely_2009_JFQA.html); [Neely-Weller 2011 WP](https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf) |
| 1972–76 vs 1992–2015 | Predictability of developed currencies | 5 of 9 developed currencies predictable in 1972–76; none after 1992–96; OOS 2012–15 developed Sharpe 0.24 | [Hsu-Taylor-Wang](https://www.cicfconf.org/sites/default/files/paper_412.pdf) |
| 1999–2020 (OOS) | G11 FX technical portfolios | Mean Sharpe 0.66 in-sample (1980–98) → 0.06 OOS; negative after modest costs | [Hutchinson et al. 2022](https://pureadmin.qub.ac.uk/ws/portalfiles/portal/370624058/1_s2.0_S0275531922001659_main_1_.pdf) |
| 1897–2011 | DJIA technical rules | Even in-sample, low costs offset profits; future winners never selectable ex ante | [Bajgrowicz-Scaillet 2012](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html) |
| 2009–2013 | Diversified trend following | "Disappointing"; the 10 largest historical drawdowns were 13.5–26.3%; CTA results poor in 2009 and 2011 | [Hurst et al.](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf); [Baltas-Kosowski](https://www.naaim.org/wp-content/uploads/2013/10/00S_Momentum_Strategies_in_Futures_Markets_Nick_Baltas.pdf) |
| 2010s | Trend following | Muted market moves across the decade | [Babu et al. 2020](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want) |
| Post-2009 (QUANTGEN B3) | Ten-futures TSMOM | OOS Sharpe 0.08 [−0.27, 0.43] | QUANTGEN context brief (study run 2026-09-27) |
| 1800–2014 | Short-horizon trends | Shorter trends "significantly withered"; long trends intact | [Lempérière et al.](https://arxiv.org/abs/1404.3274) |
| H1 2018 (OOS) | Crypto technical rules on Bitcoin | Negative OOS returns on BTC (positive on LTC, ETH, XRP) | [Hudson-Urquhart 2021](https://link.springer.com/article/10.1007/s10479-019-03357-1) |
| 2010–2018 | BTC MA strategies | Still suffered max drawdowns of 64.3–70.3% (buy-and-hold 89.5%) | [Detzel et al. WP](https://community.portfolio123.com/uploads/short-url/jS0qs8gndLATbD3WlYQ79thDnzD.pdf) |
| 2014–2018 | Crypto cross-sectional momentum | No significant payoffs across 143 coins (contradicts Liu-Tsyvinski-Wu) | [Grobys-Sapkota 2019](https://ideas.repec.org/a/eee/ecolet/v180y2019icp6-10.html) |
| After 2015 | BTC Monday effect | Did not persist; no abnormal weekend returns | [Mueller 2024](https://www.sciencedirect.com/science/article/pii/S1544612324004598) |
| Mar 2019 – Jan 2022 | Crypto cash-and-carry; high-carry regimes | Carry up to 60% p.a. preceded crashes; liquidation risk in over half of months at 10x; Sharpe 0.59 gross | [BIS WP 1087](https://www.bis.org/publ/work1087.pdf) |
| Ongoing | Perpetual-futures arbitrage edge | Deviations shrinking about 22 pp a year | [He et al. 2026](https://arxiv.org/html/2212.06888v7) |
| 1973–1994 | Head-and-shoulders in FX | Profitable but dominated by simpler rules | [Chang-Osler 1999](https://ideas.repec.org/a/ecj/econjl/v109y1999i458p636-61.html) |
| 1976–2002 | RSI/MACD on the Nikkei | Ineffective in Japan (profitable only in Italy and Canada) | [Chong-Ng-Liew 2014](https://www.mdpi.com/1911-8074/7/1/1) |
| 2016 (Quantopian cohort) | Backtested retail algorithms | Backtest Sharpe R² < 0.025 for OOS Sharpe; more backtests, bigger gap | [Wiecki et al.](https://ssrn.com/abstract=2745220) |
| 1992–2006; 2013–2015; 2018; 2000–2006 | Retail speculators | Taiwan: <1% of day traders reliably profitable. Brazil: 97% of persistent day traders lost. EU: 74–89% of CFD accounts lose. Dutch technical-analysis users earned lower returns | [Barber et al.](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20Skill%20110523.pdf); [Chague et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101); [ESMA](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors); [Hoffmann-Shefrin](https://ideas.repec.org/a/eee/jeborg/v107y2014ipbp487-511.html) |

---

### [P7] Data-check requests (lines 529-583)

###### Data-check requests for the data lab

The lab datasets are: KRX marcap 1995–2026, Shiller monthly 1871–2026, SPY daily 1998–2021, VIX daily 1990–2026, and French monthly factors 1926–2018. Requests marked † need crypto data the lab does not list (Upbit/Binance daily).

1. **DC-1: KRX price-to-MA and channel-position cross-section** (tests F2 and F3 in Korea).
   - Universe: KRX common stocks with 20-day average daily value ≥ KRW 1bn, survivorship-free.
   - Signals at the close of t: ln(C/SMA_L) for L = 20, 50, 200, and channel position for L = 20, 252.
   - Portfolios: monthly quintile sorts, equal- and cap-weighted; returns from t+1.
   - Costs: 35 bp per side, with a 70 bp stress.
   - Report gross and net Sharpe for 1995–2007, 2008–2019 and 2020–2026, and Fama-MacBeth slopes controlling for 1-month reversal and 12-1 momentum.
   - Hypothesis: short L behaves like reversal (negative slope) in Korea, while long L and the 52-week-high measure may be positive.
2. **DC-2: George-Hwang 52-week-high replication on KRX.**
   - Signal: C / max(H over t−251 to t).
   - Monthly quintiles, net of 35/70 bp.
   - Spanning test against 12-1 momentum and against the 1-month reversal factor.
3. **DC-3: Is RSI redundant with returns?** On KRX daily data:
   - Compute RSI(2) and RSI(14) with Wilder smoothing, and 2-, 5- and 14-day return z-scores.
   - Report Spearman correlations.
   - Run Fama-MacBeth regressions of next-5-day returns on RSI, controlling for the matching return z-score.
   - If RSI's t-statistic falls below 2 after the control, treat RSI as a re-parameterisation, not a new card.
4. **DC-4: Volatility-compression conditioning** (KRX stocks and SPY daily).
   - Squeeze_t = 1 if Bollinger(20, 2σ) lies inside Keltner(20, 1.5 × ATR20).
   - Test (a) next-10-day realised volatility divided by the prior 20-day realised volatility after squeeze releases, compared with unconditional periods.
   - Test (b) returns of 55-day channel-breakout entries with a squeeze in the prior 5 days, compared with entries without one.
   - Costs: 35 bp per side on KRX stocks and 3 bp per side on ETFs.
   - Pre-registered success: a net Sharpe uplift of at least 0.2 for conditioned breakouts, with at least 50% of neighbouring configurations keeping half the uplift. Otherwise DROP F4.
5. **DC-5: ATR vs close-to-close volatility forecasts** (SPY 1998–2021 and the top 200 KRX stocks).
   - Compare ATR14/C, ATR20/C, Parkinson(20), σ20, σ126 and EWMA(λ = 0.94) as forecasts of next-20-day realised volatility, using QLIKE and MSE.
   - Re-run E2 (SPY volatility targeting) with the best estimator, counted as one trial.
6. **DC-6: Long-sample equity-index MA timing** (Shiller monthly 1871–2026).
   - Rule: long when the price is above its 10-month SMA, otherwise flat (T-bill), at 3 bp per side.
   - Report Sharpe, max drawdown and the share of rolling 10-year windows in which the rule beats buy-and-hold, for 1871–1945, 1946–1989 and 1990–2026.
   - Purpose: tests whether E1's "protects but does not outperform" holds on a long sample, and whether the edge declined after 1990 as the adaptive-markets view predicts.
7. **DC-7: Nagel replication on KRX.**
   - Weekly 1-week reversal decile spread, 1995–2026, net of 35 bp.
   - Regress the spread on lagged VIX (1990–2026) and on the lagged realised volatility of the KOSPI index.
   - Purpose: confirms or contradicts holding the reversal sleeve at 1.0x in stress.
8. **DC-8: How much do TradingView-style shortcuts inflate a backtest?** (SPY daily).
   - For three ported logics (50/200 MA cross, Supertrend(10, 3), squeeze breakout), compute three versions:
     - (a) QUANTGEN: signal at t, return from t+1;
     - (b) Pine `process_orders_on_close`: signal and fill at the close of t;
     - (c) weekly-timeframe indicator value with lookahead and no offset.
   - Report Sharpe and max drawdown for each. The gaps measure the inflation that retail backtests carry.
9. **DC-9† C3 robustness.**
   - Split KRW-BTC and BTC-USD results at 10 Jan 2024.
   - Cut-time sensitivity: daily bars cut at 00:00 UTC, 00:00 KST and 21:00 UTC.
   - Funding overlay: multiplier 0.5 when the 7-day mean funding is in the top decile of its trailing 365-day distribution, otherwise 1.0.
   - Count three extra trials in the deflated Sharpe.
10. **DC-10† CTREND-lite.**
    - Universe: top 100 coins by 30-day volume on Binance/Upbit, weekly.
    - Features: F2, F3, F5, F7, MACD and Bollinger width, combined with elastic net under purged walk-forward validation.
    - Portfolio: long-only top quintile vs BTC; costs 10 bp per side with a 20 bp stress.
    - Report pre- and post-2024 results separately.

---

### [P7] Claims ledger (lines 585-619)

###### Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| P7-C01 | Price-to-moving-average ratios forecast Bitcoin returns out of sample and improve Sharpe mainly by cutting drawdowns. | BTC daily, Jul 2010–Jan 2018. OOS R² (7-day) 1.17–3.66% for the combination forecast. Sharpe 1.92 → 2.09–2.51. Max drawdown 89.5% → 64–70%. Break-even one-way cost 1.12–3.96% | [Detzel et al. FM 2021](https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html); [WP PDF](https://community.portfolio123.com/uploads/short-url/jS0qs8gndLATbD3WlYQ79thDnzD.pdf) | T1 | Recursive OOS; one asset; pre-2018; WP numbers | Buy-and-hold Sharpe fell 2.45 → 1.45 in the second half; drawdowns still 64–70% | CONTEXT: supports the C3 PASS (similar +0.43 uplift); keep C3 and add a post-2024 monitor |
| P7-C02 | Thousands of technical rules were significant on major cryptocurrencies to 2017 after multiple-testing correction, but failed OOS on Bitcoin in H1 2018. | 14,919 rules; BTC/LTC/ETH/XRP daily to Dec 2017; 20–50% significant after Bonferroni/Holm/BH/BY; break-even 7.88–147.56 bp; H1 2018 OOS negative on BTC | [Hudson-Urquhart 2021](https://link.springer.com/article/10.1007/s10479-019-03357-1) | T1 | Multiple-testing control; short OOS | 2018 bear market (BTC) | BUILD (trend family exists as C3); exclude fast rules with break-even ≤ 20 bp |
| P7-C03 | Other crypto technical-rule studies are positive but weaker in design (no costs, short samples, or intraday). | 20-day variable MA: 8.76% p.a. ex-BTC (11 coins, 2016–18, no costs). One-minute BTC variable MA best (2014–18, no costs). 75,360 rules can beat buy-and-hold OOS net of costs (Deprez-Frömmel) | [Grobys et al. 2020](https://ideas.repec.org/a/eee/finlet/v32y2020ics1544612319308852.html); [Corbet et al. 2019](https://www.sciencedirect.com/science/article/abs/pii/S1544612319300315); [Deprez-Frömmel 2024](https://ideas.repec.org/a/eee/reveco/v93y2024ipbp858-874.html) | T1 | Mixed: only Deprez-Frömmel controls costs and data mining | 2018 crash inside the samples; intraday costs | CONTEXT; DROP intraday crypto MA rules |
| P7-C04 | Bitcoin weekly returns show time-series momentum and attention effects, and almost no exposure to equity factors. | One-SD current-week return → +3.16% next week; one-SD Google searches → +1.84%; only 4 of 155 equity factors significant (IS, WP) | [Liu-Tsyvinski RFS 2021](https://www.nber.org/papers/w24877); [VoxEU](https://cepr.org/voxeu/columns/risks-and-returns-cryptocurrencies) | T1 | In-sample regressions; early sample | Not tested net of costs | CONTEXT: supports crypto TS-mom weight 3; attention BACKLOG (no feed) |
| P7-C05 | Crypto cross-sectional momentum is short-horizon (1–4 weeks) and contested. | Weekly long-short 2.5–4.1% (t 2.0–2.7) for 1–4 weeks; 8–16 weeks not significant; 2014–18; shorting limited. Contradicted by Grobys-Sapkota (143 coins, null) | [LTW JF 2022 WP](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf); [Grobys-Sapkota 2019](https://ideas.repec.org/a/eee/ecolet/v180y2019icp6-10.html) | T1 | Not replicated across studies; gross | Small, unshortable coins | BACKLOG; flags the crypto ST-rev weight of 2 as unsupported |
| P7-C06 | A 28-indicator technical composite (CTREND) predicts the crypto cross-section, including large and liquid coins, after costs. | 3,245 coins, Apr 2015–May 2022: 3.87%/week (t 5.19), Sharpe 1.94; top-100 by cap 3.39%/week; top-100 liquid 3.30%; significant in 79% of 55,296 designs | [Fieberg et al. JFQA 2025](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178) | T1 | Machine-learning OOS; costs; liquid subsamples | Pre-ETF; long-short with impractical shorts | BACKLOG (strong): CTREND-lite, long-only vs BTC (DC-10) |
| P7-C07 | Perpetual-futures premia are large, extrapolative and shrinking, so they are a crowding gauge rather than a tradable edge for QUANTGEN. | Mean absolute perp–spot deviation 52–90%/yr; past returns predict the gap; shrinking about 22 pp/yr; BTC arbitrage Sharpe 3.35 at retail costs | [He et al. arXiv v7 2026](https://arxiv.org/html/2212.06888v7) | T1 (WP) | Needs an order path; declining | Edge shrinking | CONTEXT; input to F9 |
| P7-C08 | High crypto carry predicts crashes and liquidations; cash-and-carry earns little and carries liquidation risk. | Mar 2019–Jan 2022: carry avg >10%, peak 60%, trough <−20%; $1 higher basis → about $5–10 lower spot; cash-and-carry Sharpe 0.59 gross; liquidation risk in >50% of months at 10x | [BIS WP 1087](https://www.bis.org/publ/work1087.pdf) | T1 | In-sample; short; pre-ETF | Crashes after high-carry peaks | BACKLOG: F9 down-only multiplier on C3 in [0.5, 1.0] |
| P7-C09 | Crypto calendar effects are not persistent; weekends are illiquid but not abnormal in returns. | 500+ coins, 2013–2024: BTC Monday effect not after 2015; lower weekend volume; no weekend abnormal returns. BTC 2013–19: no day-of-week return effect, lower weekend volatility | [Mueller 2024](https://www.sciencedirect.com/science/article/pii/S1544612324004598); [Kinateder-Papavassiliou 2021](https://www.sciencedirect.com/science/article/abs/pii/S1544612319311316) | T1 | Replicated across two studies | Anomaly decay after publication | DROP calendar rules; test sensitivity to the daily cut time (DC-9) |
| P7-C10 | The spot-ETF era changed Bitcoin's market structure (lower volatility, flows chasing price, higher equity correlation). | Event 10 Jan 2024. BTC spot volatility fell. ETP assets ~$20bn → >$100bn in one year; flows follow price (0.2% per 3.4% move). BTC–S&P correlation broke upward. Kurtosis 161 → 7 | [Babalos et al. 2025](https://www.sciencedirect.com/science/article/pii/S106297692500047X); [Oefele 2025](https://www.sciencedirect.com/science/article/pii/S0165176525001417); [Hong et al. 2025](https://arxiv.org/html/2512.12815v1); [Mehdian et al. 2025](https://www.sciencedirect.com/science/article/pii/S221484502500153X) | T1 (one arXiv) | Short post-event windows | No post-ETF test of technical rules exists | CONTEXT: pre-register a C3 split at 2024-01-10 |
| P7-C11 | Technical analysis is near-universal among FX professionals and its persistence is best explained by non-fundamental influences. | 90% of FX dealers use some form of technical analysis (Taylor-Allen 1992); about 30% of US FX traders are technical analysts (Cheung-Chinn 2001) | [Menkhoff-Taylor JEL 2007](https://www.aeaweb.org/articles?id=10.1257/jel.45.4.936); [Neely-Weller 2011](https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf) | T1 | Survey evidence | Usage is not profitability | CONTEXT |
| P7-C12 | Simple MA and filter rule profits in major FX were genuine in the 1970s–80s and gone by the early 1990s. | About 8%/yr then about zero by the 1990s (Olson 1971–2000 re-optimisation); FX costs 10–15 bp → ≤2 bp | [Neely-Weller-Ulrich 2009](https://gpbib.cs.ucl.ac.uk/gp-html/Neely_2009_JFQA.html); [Neely-Weller 2011](https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf) | T1 | True ex ante OOS; adaptive-markets view | Decay after adoption | DROP G10 FX MA/filter rules (confirms V3 REJECT) |
| P7-C13 | G10 FX technical portfolios have earned roughly nothing OOS since 1999 and lose after modest costs. | 388 portfolios; G11; Sharpe 0.66 (1980–98, IS) → 0.06 (1999–2020, OOS); TSMOM explains abnormal returns | [Hutchinson et al. 2022](https://pureadmin.qub.ac.uk/ws/portalfiles/portal/370624058/1_s2.0_S0275531922001659_main_1_.pdf) | T1 | OOS; net | Whole OOS period | DROP |
| P7-C14 | FX technical predictability survived in emerging currencies but died in developed ones. | 21,000+ rules, 30 currencies, 1971–2015, stepwise SPA. Developed: 5/9 predictable in 1972–76, 0/9 after 1992–96. OOS 2012–15: developed Sharpe 0.24, EM 1.81 | [Hsu-Taylor-Wang](https://www.cicfconf.org/sites/default/files/paper_412.pdf); [Neely-Weller 2013](https://ideas.repec.org/a/eee/jbfina/v37y2013i10p3783-3798.html) | T1 | Data-snooping control; short OOS | Developed currencies after the 1990s | DROP G10; BACKLOG one USD/KRW futures slow-trend test |
| P7-C15 | Cross-sectional currency momentum is large gross but limited by costs and arbitrage frictions. | Spread up to 10% p.a.; partly explained by transaction costs | [Menkhoff et al. JFE 2012](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p660-684.html) | T1 | Published; cost-sensitive | Concentrated where costs are high | DROP (no FX cross-section in QUANTGEN) |
| P7-C16 | Diversified trend following has a 135-year record with crisis alpha, but disappointed after 2008. | 67 markets, 1880–2013: gross 14.9%, net 11.2%, net Sharpe 0.77; positive in 8 of 10 largest 60/40 drawdowns; correlation with equities 0.00; post-2008 "disappointing" | [Hurst et al.](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf); [Babu et al. 2020](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want) | T1/T2 | Long history; costs modelled by era | 2009–2013; muted 2010s | CONTEXT: B3's narrow 10-market post-2009 book explains its REJECT; keep REJECT |
| P7-C17 | TSMOM works at monthly, weekly and daily frequency in broad futures books, but faster rules multiply turnover. | 71 futures, 1978–2012: gross Sharpe ≥1.2; after 2/20 fees about 0.9; weekly 3–5x and daily about 10x monthly turnover; no capacity limits | [Baltas-Kosowski WP](https://www.naaim.org/wp-content/uploads/2013/10/00S_Momentum_Strategies_in_Futures_Markets_Nick_Baltas.pdf) | T1 (WP) | Pre-2012 | CTA results in 2009 and 2011 | CONTEXT: prefer monthly or weekly rebalancing |
| P7-C18 | Single-asset TSMOM evidence is weak and much of the apparent alpha is volatility scaling plus drift. | Little asset-by-asset predictability IS/OOS; TSMOM profits ≈ a historical-mean strategy; unscaled TSMOM ≈ buy-and-hold | [Huang et al. JFE 2020](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html); [Kim-Tse-Wald JFM 2016](https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html) | T1 | Bootstrap-robust critique | Per-asset trend claims | CONTEXT: benchmark trend cards against a vol-scaled long-only portfolio; correct the prior "0.4–0.8 per asset" for futures/FX |
| P7-C19 | Long-horizon trends have not degraded over two centuries; short-horizon trends have withered. | t ≈ 5 since 1960 and ≈ 10 since 1800; shorter trends "significantly withered" | [Lempérière et al.](https://arxiv.org/abs/1404.3274) | T1 (WP/journal) | Very long sample | Short lookbacks | BUILD rule: long lookbacks for futures and FX; short ones only where gated (crypto C3) |
| P7-C20 | Commodity-futures trend rules, and old futures systems including Wilder's directional parabolic, were net-profitable. | 28 commodities, 48 years: positive net in ≥22 markets. 12 futures, OOS 1978–84: 4 of 12 systems net-profitable at 1.89–2.78%/month | [Szakmary et al. 2010](https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html); [Park-Irwin AgMAS (Lukac et al. 1988)](https://farmdoc.illinois.edu/assets/marketing/agmas/AgMAS04_04.pdf) | T1 | Data-mining adjusted (Szakmary); old (Lukac) | Before the 1990s decay | CONTEXT; DO-NOT-BUILD ADX or Parabolic SAR standalone |
| P7-C21 | The technical-analysis literature is mostly positive but unreliable because of data snooping, and on the DJIA profits vanish with low costs. | 95 studies: 56 positive, 20 negative, 19 mixed. DJIA 1897–1986: buy signals beat sell signals (IS). DJIA 1897–2011: low costs offset in-sample profits; winners not selectable ex ante | [Park-Irwin 2007](https://ideas.repec.org/a/bla/jecsur/v21y2007i4p786-826.html); [BLL 1992](https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html); [Bajgrowicz-Scaillet 2012](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html) | T1 | FDR and persistence tests | Zero-cost backtests | DROP equity-index technical timing beyond E1; count every rule as a trial |
| P7-C22 | In equities, MA-based trend and nearness to the 52-week high carry cross-sectional information, and technical indicators help forecast the index equity premium. | US: trend factor more than doubles momentum's Sharpe; 2008 +0.75%/month vs momentum −3.88%. 52-week high dominates past returns with no long-run reversal. MA/momentum/OBV forecast the equity premium IS and OOS | [Han-Zhou-Zhu 2016](https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html); [George-Hwang 2004](https://ideas.repec.org/a/bla/jfinan/v59y2004i5p2145-2176.html); [Neely et al. 2014](https://ideas.repec.org/a/inm/ormnsc/v60y2014i7p1772-1791.html) | T1 | Replicated (trend in crypto via CTREND) | Korea untested; costs | BUILD-candidate: F2 and F3 in the US cross-section; Korea via DC-1 and DC-2 |
| P7-C23 | Oscillator and band rules (RSI, MACD, Bollinger) have only weak, old, market-specific standalone support. | Five indices 1976–2002: Italy and Canada yes, Japan no; MACD survived 1% round trip in two markets. Bollinger Bands underperform MA envelopes | [Chong-Ng-Liew 2014](https://www.mdpi.com/1911-8074/7/1/1); [Leung-Chong 2003](https://ideas.repec.org/a/taf/apeclt/v10y2003i6p339-341.html) | T1 (lower-tier) | No data-snooping control | Japan; post-2002 untested | DROP as standalone rules; RSI → F5; Bollinger width → F4 |
| P7-C24 | Chart patterns are dominated by simple rules, while support and resistance have a microstructure basis without a demonstrated daily profit. | Head-and-shoulders FX 1973–94: profitable but dominated. US stocks 1962–96: patterns give incremental information. FX S/R 1996–98: bounces 60.8% vs 56.2%; orders cluster at round numbers | [Chang-Osler 1999](https://ideas.repec.org/a/ecj/econjl/v109y1999i458p636-61.html); [Lo-Mamaysky-Wang 2000](https://www.nber.org/papers/w7613); [Osler 2000](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf); [Osler 2003](https://ideas.repec.org/a/bla/jfinan/v58y2003i5p1791-1819.html) | T1 | Old samples; no cost tests for S/R | Pattern rules dominated | DO-NOT-BUILD pattern recognisers or pivot points; CONTEXT |
| P7-C25 | For Ichimoku, Supertrend, Squeeze, UT Bot, WaveTrend, Connors RSI(2), TD Sequential, Wyckoff/VSA, Elliott/Fibonacci, CANSLIM/VCP and Lorentzian Classification, no rigorous OOS net-of-cost test was found. | Script pages describe only computation (T3); the Lorentzian author warns its Trade Stats are not a backtest | [Squeeze](https://www.tradingview.com/script/nqQ1DT5a-Squeeze-Momentum-Indicator-LazyBear/); [WaveTrend](https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/); [UT Bot](https://www.tradingview.com/script/n8ss8BID-UT-Bot-Alerts/); [Lorentzian](https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/) | T3 | Absence of evidence (search budget exhausted) | n/a | DO-NOT-BUILD as systems; translate into F1–F8 primitives |
| P7-C26 | TradingView's engine and indicators are structurally prone to repainting, look-ahead and unrealistic fills unless the author intervenes. | >95% of indicators repaint; lookahead_on without offset leaks future data; non-standard charts give synthetic fills; intrabar path assumption; Bar Magnifier paid-only; v5 margin default 0 → v6 100 | [Repainting](https://www.tradingview.com/pine-script-docs/concepts/repainting/); [Other timeframes](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/); [Strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/); [v6 migration](https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/); [FAQ](https://www.tradingview.com/pine-script-docs/faq/strategies/) | T1 (official docs) | Primary documentation | Same-bar fills; HTF lookahead; Heikin Ashi | DO-NOT-BUILD rules B1–B4, B14–B15; porting protocol D |
| P7-C27 | TradingView's publishing standards are minimal compared with QUANTGEN's gate. | Requires realistic capital, costs and non-zero margin, typically >100 trades, no lookahead_on, no non-standard charts | [Publishing rules](https://www.tradingview.com/support/solutions/43000590599-script-publishing-rules/) | T1 (official) | Policy, not enforcement evidence | 100 trades cannot separate skill from noise | CONTEXT; treat published scripts as unverified claims |
| P7-C28 | Backtest performance barely predicts live or OOS performance, and searching more makes it worse. | 888 Quantopian algorithms: backtest Sharpe R² < 0.025. Overfitting implies negative OOS returns under memory. Sharpe 0.75/20 years/N = 200 → about 0.32 | [Wiecki et al.](https://ssrn.com/abstract=2745220); [Bailey et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659); [Harvey-Liu 2015](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF) | T1 | Large cohort; theory | Any multi-trial search | CONTEXT: supports gate steps 3–4; expected PASS share for community scripts is low (inference) |
| P7-C29 | Retail technical and day traders overwhelmingly lose after costs. | Taiwan 1992–2006: <1% reliably profitable. Brazil 2013–15: 97% of persistent day traders lost. EU 2018: 74–89% of CFD accounts lose. Dutch 2000–06: technical-analysis users earned lower returns | [Barber et al.](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20Skill%20110523.pdf); [Chague et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101); [ESMA 2018](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors); [Hoffmann-Shefrin 2014](https://ideas.repec.org/a/eee/jeborg/v107y2014ipbp487-511.html) | T1/T2 | Population data; several countries | n/a | CONTEXT: show the base rate beside TradingView-derived cards |
| P7-C30 | Range-based volatility, stops on serially correlated returns, reversal as liquidity provision, and abnormal volume give the canon's best-founded translations. | Range volatility efficient and noise-robust. Stops add value only under momentum-type serial correlation. Reversal returns rise with VIX. High abnormal volume → higher next-month returns | [Alizadeh-Brandt-Diebold 2002](https://ideas.repec.org/a/bla/jfinan/v57y2002i3p1047-1091.html); [Kaminski-Lo 2014](https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html); [Nagel 2012](https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html); [Gervais-Kaniel-Mingelgrin 2001](https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html) | T1 | Published, theory plus data | Stops on reversal sleeves would hurt (inference) | BUILD: F1 (ATR risk input), F5 (reversal), F7 (volume conditioner); ATR stops on trend sleeves only |

