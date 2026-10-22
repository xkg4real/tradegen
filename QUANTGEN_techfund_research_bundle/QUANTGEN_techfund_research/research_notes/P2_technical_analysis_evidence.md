# P2 position paper: technical trading rules after correcting for data snooping and costs (QUANTGEN technical & fundamental signals panel)

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

---

## Q1. Classic and modern evidence: which technical constructs survive data-snooping control and costs, in which markets and periods?

### Takeaway
- Single-market rule families (MA, filter, breakout, OBV) were profitable in early samples. They fail family-wise tests and costs from the late 1980s in US equities and from the early 1990s in FX.
- Better-supported constructs are slow, mechanism-backed price-state variables:
  - diversified vol-scaled trend (strong 1880-2009, near-zero excess return in 2010-2018);
  - 52-week-high proximity (strong gross in the US, rarely significant net abroad);
  - MA-distance and trend factors in the US cross-section.
- CNN chart-reading is strong gross out-of-sample but has no net-of-cost evidence.

### Cited Findings

#### A. Single-market rule families and family-wise (data-snooping) tests
- **Brock-Lakonishok-LeBaron (1992).** DJIA 1897-1986, moving-average and trading-range-break rules, IS, gross. Buy-signal returns exceeded sell-signal returns and were less volatile, and sell-signal returns were negative. The pattern was inconsistent with bootstrapped random-walk, AR(1), GARCH-M and EGARCH nulls. — [BLL 1992, IDEAS abstract](https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html)
- **Sullivan-Timmermann-White (1999), Reality Check (RC).**
  - Universe: 7,846 rules (497 filter, 2,049 MA, 1,220 support/resistance, 2,040 channel-breakout, 2,040 OBV).
  - DJIA 1897-1986 subperiods: the best rule stays significant after RC (RC p = 0.000). Example: 1962-1986 best = 2-day OBV, 23.82%/yr, Sharpe 1.41, IS, gross.
  - OOS 1987-1996 (DJIA): best rule (a filter rule) 14.41%/yr, Sharpe 0.87. Nominal p = 0.004, but RC p = 0.341.
  - S&P 500 futures 1984-1996: best rule (30/75-day OBV) 9.43%/yr, nominal p = 0.042, RC p = 0.908.
  - Break-even cost of the best 100-year rule ≈ 0.27% per trade over 6,310 trades.
  — [STW 1999 PDF (Oxford teaching page)](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf)
- **Park & Irwin survey (JES 2007; WP 2006).**
  - 95 "modern" studies (1988-2004): 56 positive, 20 negative, 19 mixed.
  - Profits existed in US stocks until the late 1980s, FX until the early 1990s and futures until the mid-1980s. Emerging stock markets were more persistently profitable.
  - Main defects: data snooping, ex post rule selection, weak risk adjustment and low cost assumptions.
  - Break-even costs cited: 1.07% per transaction for the optimal DJIA rule (1968-1988), 0.39% for BLL MA rules on the dividend-adjusted DJIA, 0.22-0.26% in FX.
  — [Park & Irwin WP PDF](https://www.kdajdqs.org/bbs/presentation/303/download/319); [published record](https://experts.illinois.edu/en/publications/what-do-we-know-about-the-profitability-of-technical-analysis/)
- **Hsu & Kuan (2005).**
  - 39,832 rules and strategies tested.
  - 1990-2000 IS, after a 0.05% one-way cost: best rules significant on the NASDAQ Composite (2-day MA, 38.19%/yr) and the Russell 2000 (47.10%/yr), p = 0.00.
  - Not significant on the DJIA (14.67%/yr) or S&P 500 (15.38%/yr).
  - OOS 2001-2002: mixed.
  — [Hsu & Kuan PDF (NTU)](https://homepage.ntu.edu.tw/~ckuan/pdf/snoop01.pdf)
- **Hsu, Hsu & Kuan (2010), stepwise SPA test.** Technical rules showed significant predictive power for growth and emerging-market indices, and the evidence weakens after the corresponding ETFs were introduced. — [HHK 2010, IDEAS](https://ideas.repec.org/a/eee/empfin/v17y2010i3p471-484.html)
- **Bajgrowicz & Scaillet (2012 JFE).** DJIA 1897-2011, false-discovery-rate control. Even in-sample, rule performance is completely offset by low transaction costs. Persistence tests show investors could not have picked the future best rules ex ante. — [BS 2012, IDEAS](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html)
- **Marshall, Cahan & Cahan, "Technical Analysis Around the World" (WP).**
  - 49 markets (23 developed, 26 emerging), 5,806 rules, 2001-2007, gross.
  - No developed market has a significant rule after RC, and the emerging-market advantage disappears after adjustment.
  - South Korea: nominal p 0.298, RC-adjusted 0.942. Taiwan: 0.076 → 0.748.
  — [MCC PDF (forum mirror of the SSRN paper)](https://c.mql5.com/forextsd/forum/210/Technical%20Analysis%20Around%20the%20World.pdf); [SSRN record](https://www.ssrn.com/abstract=1181367)
- **Fang, Jacobsen & Qin (2014 RFE).** BLL's own best rules applied to new data, 1987-2011 (OOS): no predictive power. The authors attribute the earlier success to bias rather than to markets becoming more efficient. — [FJQ 2014, IDEAS](https://ideas.repec.org/a/eee/revfin/v23y2014i1p30-45.html)
- **Taylor (2014 JBF).** Momentum-type rules on DJIA members, 1928-2012. Profits evolve slowly, are confined mainly to the mid-1960s to mid-1980s, and depend on short selling. — [Taylor 2014, IDEAS](https://ideas.repec.org/a/eee/jbfina/v40y2014icp286-302.html)
- **Shynkevich (2012 JBF).** US technology and small-cap portfolios. Rules were significant in 1995-2002 with small-to-moderate costs, and futile in 2003-2010 after data-snooping adjustment. — [Shynkevich 2012, IDEAS](https://ideas.repec.org/a/eee/jbfina/v36y2012i1p193-208.html)
- **FX: Neely, Weller & Ulrich (St. Louis Fed WP 2006-046; JFQA 2009).**
  - Published FX rules re-run after their publication, net of time-declining costs (10 bp in 1973 falling to 1.88 bp in 2005).
  - Sweeney 1% filter: 8.61%/yr net in 1973-1980, 1.82% in 1981-2005.
  - Levich-Thomas rule portfolio: 5.74% → −0.11%/yr, Sharpe 0.90 → −0.02 (1991-2005).
  - Taylor channel rules: 5.74% → 1.91%. Genetic-programming rules: 2.94% → 0.15% (Oct 1995 to 2005).
  - Structural breaks cluster in 1989-1993.
  — [NWU WP](https://files.stlouisfed.org/files/htdocs/wp/2006/2006-046.pdf)
- **FX: Neely & Weller (St. Louis Fed WP 2011-001).** Simple FX rules earned roughly 8%/yr from about 1975 to 1990 and roughly zero by the 1990s. Spot spreads fell to 2 bp or less, so falling profits are not a cost story. Central-bank intervention follows trends rather than creating them. — [Neely & Weller 2011](https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf)
- **Conflicting FX evidence: Hsu, Taylor & Wang (2016 JIE).** More than 21,000 rules on 30 developed and emerging currencies over 45 years, using a stepwise data-snooping test. They report substantial predictability and profitability, varying across subperiods and regions. — [HTW 2016, IDEAS](https://ideas.repec.org/a/eee/inecon/v102y2016icp188-208.html)

#### B. Index timing with moving averages
- **Faber, 10-month SMA (practitioner paper, updated version).**
  - Rule: hold the S&P 500 when the month-end price is above its 10-month SMA, else cash.
  - 1901-2012, gross: 10.18%/yr vs buy-and-hold 9.32%/yr. Max drawdown 42.2% vs 83.7%. About 70% time in market, fewer than one round trip per year.
  - Reported post-original-sample (2006-2012): about 2 points per year better with lower drawdowns.
  - Not data-snooping adjusted.
  — [Faber PDF](https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf)
- **Zakamulin (2014 JAM).** Reported market-timing performance with MA and TSMOM rules contains considerable data-mining bias and ignores frictions. Out-of-sample tests with realistic costs show the performance is highly overstated. — [Zakamulin 2014, IDEAS](https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html)
- **Zakamulin (2018 IRF).** Correcting a prior study's look-ahead bias makes MA timing statistically indistinguishable from buy-and-hold. — [Zakamulin 2018, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2743119)
- **Zhu & Zhou (2009 JFE), theory.** MA rules add value when returns are predictable but the investor is uncertain about the model or its parameters. They can beat model-based optimal rules when the model is uncertain. — [Zhu & Zhou 2009, IDEAS](https://ideas.repec.org/a/eee/jfinec/v92y2009i3p519-544.html)
- **Neely, Rapach, Tu & Zhou (St. Louis Fed WP 2010-008; Management Science 2014).**
  - S&P 500 monthly, Dec 1950 to Dec 2011; recursive OOS Jan 1966 to Dec 2011.
  - 14 technical indicators (MA(1-3, 9-12), momentum 9/12, OBV-based volume rules): all have positive OOS R² of 0.09-0.75%. Only 3 of 14 macro variables are positive.
  - Principal-component forecasts: PC-TECH R² 0.65%, PC-ECON −0.06%, PC-ALL 1.79%.
  - Certainty-equivalent gains (risk aversion 5): technical indicators 0.73-3.17%/yr, PC-ALL 4.20%/yr. After 50 bp per transaction: 0.40-2.82% and 4.12%.
  - Technical indicators catch the equity-premium decline near business-cycle peaks; macro variables catch the rise near troughs.
  — [NRTZ WP](https://files.stlouisfed.org/files/htdocs/wp/2010/2010-008.pdf)
- **Levine & Pedersen (2016 FAJ).** MA crossovers, TSMOM and other filters are generalized forms of the same trend filter, and implementation quality matters more than which filter is used. — [AQR page](https://www.aqr.com/Insights/Research/Journal-Article/Which-Trend-Is-Your-Friend)
- **Marshall, Nguyen & Visaltanachoti (2017 QF).** MA rules often signal earlier than TSMOM. Both work best outside large-stock series. — [MNV 2017, IDEAS](https://ideas.repec.org/a/taf/quantf/v17y2017i3p405-421.html)

#### C. Time-series momentum (TSMOM) and trend
- **Moskowitz, Ooi & Pedersen (2012 JFE).**
  - 58 liquid futures, results from 1985 to 2009 (data from 1965), IS, gross; no transaction-cost analysis.
  - Diversified 12-month TSMOM: alpha 1.58%/month vs Fama-French factors (t = 7.99), Sharpe above 1.
  - All 58 contracts have positive TSMOM returns, 52 of them significant.
  - Partial reversal in year 2. Best returns in extreme markets: profits in Oct-Dec 2008, losses in Mar-May 2009.
  - CFTC data: speculators ride trends at hedgers' expense.
  — [MOP PDF (NYU)](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)
- **Hurst, Ooi & Pedersen (2017, AQR / JPM).**
  - 67 markets, 1880-2016. The pre-1985 part is out-of-sample in time relative to MOP.
  - 1-, 3- and 12-month TSMOM blend at a 10% volatility target.
  - Returns: 18.0%/yr gross; 11.0% net of transaction costs (before fees); 7.3% net of 2/20 fees and costs. Volatility 9.7%, net Sharpe 0.76.
  - Correlation −0.01 with the S&P 500 and −0.03 with US 10-year bonds.
  - Net decade returns: 1990s 8.3%, 2000s 6.3%, 2010-2016 3.3%.
  - Cost assumptions: 6x the baseline for 1880-1992 and 2x for 1993-2002.
  - Positive in 8 of the 10 largest 60/40 drawdowns. A 20% allocation cut 60/40 max drawdown from −62.3% to −50.2% and raised Sharpe from 0.39 to 0.55.
  — [HOP PDF](https://static.twentyoverten.com/593e8a9e7299b471eaecf644/SkLoGL67M/A-Century-of-Evidence-on-Trend-Following-Investing.pdf); [AQR page](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)
- **Lempérière et al. (2014, arXiv; CFM).** Commodities, currencies, stock indices and bonds, 1800-2014. Trend excess-return t-statistic is about 10 since 1800 and about 5 since 1960, after removing market drift. Long trends show no statistical degradation, but short trends have "significantly withered". Signals saturate at large values. — [arXiv 1404.3274](https://arxiv.org/abs/1404.3274)
- **AQR, "You Can't Always Trend When You Want" (2019).** Hypothetical trend portfolio, gross of advisory fees and net of transaction costs per its methodology section. Excess return 6.3%/yr in 2000-2009 (total 9.2%, cash 2.9%) vs 0.4%/yr in 2010-2018 (total 1.6%, cash 1.2%). AQR attributes the gap to smaller market moves rather than lower trend "efficiency" or diversification. — [AQR 2019 PDF (third-party host)](https://www.belmontinvestments.com/cimg/file/articles/53/pdf/190425aqrtrendfollowing.pdf)
- **Huang, Li, Wang & Zhou (2020 JFE), "Time-series momentum: is it there?"**
  - 55 futures, 1985-2015.
  - The pooled-regression t of 4.34 is below bootstrap critical values (pairs 4.83, wild 12.53).
  - Only 8 of 55 assets are significant at the 10% level, and only 3 have significant OOS R². Average IS R² is 0.39%.
  - TSMOM vs a "time-series history" (TSH) strategy that bets on the sign of each asset's historical mean: return difference 0.14% (p = 0.19). Alpha differences are insignificant.
  - Without volatility scaling, t falls from 4.34 to 1.68.
  — [HLWZ PDF (SMU)](https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=7520&context=lkcsb_research)
- **Kim, Tse & Wald (2016 JFM).** TSMOM alphas are largely driven by volatility scaling. Unscaled TSMOM and buy-and-hold have similar cumulative returns and alphas that are not significantly different. — [KTW 2016, IDEAS](https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html)
- **Georgopoulou & Wang (2017 RoF).** Developed and emerging equity indices and commodities, 1969-2015: robust TSMOM. The authors note that recent central-bank interventions distorted cross-asset correlations, challenging such portfolios. — [GW 2017, IDEAS](https://ideas.repec.org/a/oup/revfin/v21y2017i4p1557-1592..html)
- **Szakmary, Shen & Sharma (2010 JBF).** 28 commodity futures, 48 years of monthly data. Dual-MA and channel rules have positive mean excess returns net of costs in at least 22 of 28 markets. Results are robust to data-mining adjustments. — [SSS 2010, IDEAS](https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html)
- **Crypto.**
  - Liu & Tsyvinski (NBER w24877; RFS 2021): strong TSMOM, and investor-attention proxies forecast crypto returns. — [NBER w24877](https://www.nber.org/papers/w24877)
  - Detzel et al. (2021 FM): price-to-MA ratios forecast daily bitcoin returns in- and out-of-sample; the same holds for hard-to-value stocks (small, young, low-coverage, dot-com Nasdaq). — [Detzel 2021, IDEAS](https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html)
  - Corbet et al. (2019 FRL): high-frequency bitcoin; variable-length MA rules perform best. — [Corbet 2019, IDEAS](https://ideas.repec.org/a/eee/finlet/v31y2019icp32-37.html)
- **QUANTGEN's own record (study of 2026-09-27; OOS Sharpe with 90% CI).**
  - C3 crypto trend: KRW-BTC PASS, 1.22 [0.62, 1.77] vs 0.79 for buy-and-hold, p 0.04, 1.17 at 2x costs. BTC-USD PASS, 1.19 vs 0.89.
  - B3 TSMOM on ten futures: REJECT, 0.08 [−0.27, 0.43].
  - E1 trend switch: US ETF sleeves REJECT (0.84 vs 0.95); KRX sleeves REJECT (0.52 vs 0.74).
  - E5 sector momentum: REJECT (0.48 vs 0.63).
  - V3 FX momentum: REJECT (−0.59).
  — context brief (00_QUANTGEN_context.md)

#### D. Cross-sectional price-state signals (52-week high, MA distance, reversal, volume)
- **George & Hwang (2004 JF).**
  - CRSP, Jul 1963 to Dec 2001, IS, gross; (6,6) formation/holding with top/bottom 30%.
  - 52-week-high strategy: 0.45%/month in all months; 1.23%/month excluding January (t = 7.06). Jegadeesh-Titman momentum: 0.48% and 1.07%. Industry momentum: 0.45% and 0.50%.
  - Risk-adjusted, ex-January: 1.13%/month (t = 11.35) vs 0.46% for JT.
  - 52-week-high nearness dominates past returns in horse races and shows no long-run reversal. Explanation: anchoring.
  — [George & Hwang PDF (U. Houston)](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf)
- **Liu, Liu & Ma (JIMF, 2011).** 52-week-high strategy in 20 international markets: profitable in 18, significant in 10. Profits exist independently of JT momentum and do not reverse. After transaction costs they are not significant in most markets. — [JIMF abstract](https://www.sciencedirect.com/science/article/abs/pii/S0261560610001099)
- **Jeon & Byun (2023 FAJ).**
  - US, 1930 to Mar 2022, gross. Standard momentum (WML) lost −88.48% in Jul-Aug 1932 and −45.60% in Mar-Apr 2009.
  - A "nearhigh-neutral" momentum (WML*), with similar distance from the 52-week high in both legs: 1.37%/month vs 1.19% for WML.
  - Monthly Sharpe 0.276 vs 0.159; skewness +0.13 vs −1.89; max drawdown −23.66% vs −74.06%.
  — [Jeon & Byun PDF (Marquette)](https://epublications.marquette.edu/cgi/viewcontent.cgi?article=1168&context=fin_fac)
- **Han, Yang & Zhou (2013 JFQA).**
  - NYSE/AMEX volatility-decile portfolios, Jul 1963 to Dec 2009, IS.
  - Rule: hold the decile when yesterday's price is above its 10-day MA, else T-bills.
  - Excess return over buy-and-hold ("MAP"): 5.17%/yr in the lowest-volatility decile rising to 18.55% in the highest. Fama-French alphas 7.48-21.38%/yr.
  - At 25 bp costs, the high-volatility deciles keep 15.81-17.95% alpha. 200-day-MA alphas are only 5.33-6.19%.
  — [HYZ PDF (mirror)](https://www.smallake.kr/wp-content/uploads/2016/03/49.pdf); [JFQA record](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/new-anomaly-the-crosssectional-profitability-of-technical-analysis/B9E41049F2E55B4F274D46E72ECA8E29)
- **Han, Zhou & Zhu (2016 JFE).** A "trend factor" built from moving averages over several horizons has more than double the Sharpe ratio of short-term reversal, momentum or long-term reversal. In 2009 it earned +0.75%/month vs −3.88% for momentum (gross). — [HZZ 2016, IDEAS](https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html)
- **Avramov, Kaplanski & Subrahmanyam (2021 RFE).** The distance between short- and long-run MAs ("MAD") predicts returns. Value-weighted hedge-portfolio alphas are about 9%/yr and survive institutional trading costs. The effect holds beyond momentum, 52-week highs and profitability. — [AKS 2021, IDEAS](https://ideas.repec.org/a/wly/revfec/v39y2021i2p127-145.html)
- **Short-term reversal.**
  - Jegadeesh (1990): 1934-1987, monthly; extreme-decile spread 2.49%/month (gross); 12-month continuation. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v45y1990i3p881-98.html)
  - Lehmann (1990 QJE): weekly winner/loser reversals; profits survive bid-ask and plausible costs in his sample. — [NBER w2533](https://www.nber.org/papers/w2533)
  - Avramov, Chordia & Goyal (2006 JF): reversals concentrate in high-turnover, illiquid stocks, and contrarian profits are smaller than likely transaction costs. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)
  - de Groot, Huij & Zhou (2012 JBF): restricted to large caps with turnover-reducing construction, reversal earns 30-50 bp per week net. — [IDEAS](https://ideas.repec.org/a/eee/jbfina/v36y2012i2p371-382.html)
  - Da, Liu & Schaumburg (2014 MS): reversal in the non-fundamental return component is about 4x larger than standard reversal. — [IDEAS](https://ideas.repec.org/a/inm/ormnsc/v60y2014i3p658-674.html)
  - Nagel (2012 RFS): reversal returns proxy the return to liquidity provision, are highly predictable with the VIX and spike in turmoil. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html)
- **Medhat & Schmeling (2022 RFS), "Short-term Momentum".**
  - US, Jul 1963 to Dec 2018, value-weighted.
  - In the lowest-turnover decile, last month's return reverses: −1.41%/month (t = −7.13).
  - In the highest-turnover decile it continues ("short-term momentum"): +1.37%/month (t = 4.74). Net of 0.37%/month costs: 1.00%/month (t = 3.47).
  - 22 developed markets, 1993-2018: short-term momentum +1.39%/month (t = 3.65). Korea is not in the sample.
  - The low-turnover reversal has "tapered off" since 2011.
  — [MS 2022 PDF (City, Univ. of London)](https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf)
- **Volume conditioning (signs disagree across horizons).**
  - Lee & Swaminathan (2000 JF): high-volume winners and losers reverse faster; past turnover links momentum and value. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v55y2000i5p2017-2069.html)
  - Gervais, Kaniel & Mingelgrin (2001 JF): unusually high daily or weekly volume predicts appreciation over the following month (visibility). — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html)
  - Conrad, Hameed & Niden (1994 JF): weekly, high-transaction stocks reverse while low-transaction stocks are positively autocorrelated. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v49y1994i4p1305-29.html)
  - Cooper (1999 RFS): weekly, large caps; decreasing-volume stocks reverse more. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v12y1999i4p901-35.html)
  - Llorente, Michaely, Saar & Wang (2002 RFS): risk-sharing (hedging) volume reverses, speculative volume continues. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v15y2002i4p1005-1047.html)

#### E. Chart patterns, machine-read charts, intraday
- **Lo, Mamaysky & Wang (2000).**
  - Kernel-regression pattern detection of 10 patterns: head-and-shoulders, broadening, triangle, rectangle and double tops/bottoms.
  - Sample: NYSE/AMEX and Nasdaq stocks, 1962-1996, 350 stocks sampled.
  - Patterns change the conditional return distribution for 7 of 10 patterns (NYSE/AMEX) and 10 of 10 (Nasdaq).
  - No trading-profit or cost analysis; the authors explicitly do not claim excess profits.
  — [LMW, NBER w7613](https://www.nber.org/system/files/working_papers/w7613/w7613.pdf)
- **Jiang, Kelly & Xiu (2023 JF).**
  - CNN on 5/20/60-day OHLC-volume images of US stocks; trained 1993-2000, tested OOS 2001-2019, gross.
  - Equal-weighted high-minus-low annualized Sharpe ratios:
    - 1-week holding: 7.15;
    - 1-month holding: 2.35 (5-day images) and 2.16 (20-day images), vs momentum 0.25, short-term reversal 0.55, weekly reversal 1.23.
  - Value-weighted 1-month Sharpe is only 0.45-0.49.
  - Monthly turnover 155-187%, similar to short-term reversal (168%). No net-of-cost results.
  - Applying the US-trained model to 26 foreign markets gives Sharpe 0.7, vs 0.3 for locally trained models.
  - The model favours stocks closing near the low of their recent range.
  — [JKX PDF (NUS)](https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf)
- **Gao, Han, Li & Zhou (2018 JFE).** SPY 1993-2013: the first half-hour return predicts the last half-hour return. The effect is stronger on volatile, high-volume, recession and macro-news days, and exists in 10 other ETFs. — [GHLZ 2018, IDEAS](https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html)

#### F. P2 desk checks on QUANTGEN data-lab files (unreviewed; parameters from the literature, not tuned)
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

### Inferences
- The early-sample "successes" (DJIA before 1987, FX before 1990) look genuine rather than pure data mining. The NWU structural breaks and the declining FX profits despite falling costs point that way. But they are not exploitable today: every post-publication test (STW 1987-1996, FJQ 1987-2011, MCC 2001-2007, BS with costs) fails.
- Expect index-level technical edges to be zero after costs for the S&P 500 and KOSPI 200. Any residual edge in a QUANTGEN market should sit in hard-to-value or illiquid segments (KOSDAQ, small caps, crypto), where costs and stale prices also sit.
- Time-series trend is mainly volatility scaling plus a modest, decaying directional component. HLWZ and KTW plus AQR 2019 together explain QUANTGEN's B3 REJECT. A trend card must therefore be benchmarked against volatility-scaled buy-and-hold and against a sign-of-historical-mean rule, not raw buy-and-hold.
- The prior design's trend Sharpe figures ("0.4-0.8 per asset, ~1.0 diversified") are pre-2009 gross numbers. P2's expectation for a diversified futures trend book after 2009 is Sharpe 0.0-0.3 before QUANTGEN's 60% haircut. For long/flat timing of a single equity index, the Sharpe gain over buy-and-hold is about zero (DC1: 0 of 100 rules beat buy-and-hold OOS in 2010-2021).
- Among cross-sectional technicals, only 52-week-high proximity has both a clear mechanism and no long-run reversal. In KRX it is gross-positive in every decade (0.62-0.73%/month L/S), but at 35 bp per side it needs slow rebalancing, and even then it is not significant (6-month long-only net 1.34%/yr). It is a feature, not a card.
- HYZ-style MA timing of high-volatility portfolios in KRX mostly harvests the autocorrelation of equal-weighted portfolios of thinly traded stocks. Evidence: one extra day of lag cuts gross from 30% to 18%, and 2016-2026 is insignificant with the lag. It is not a tradable retail card.

### Gaps
- BLL's full text (buy-day vs sell-day mean returns, break-even costs) could not be fetched (the Brandeis host failed TLS/robots checks); only the abstract is cited.
- White (2000) and Hansen (2005) abstracts were unavailable on IDEAS, so the method descriptions rest on STW and HHK.
- McLean-Pontiff (2016) could not be re-verified this session (SSRN returned 429, Wiley 403). The 60% haircut in the gate is taken from the context brief.
- No peer-reviewed technical-rule test specific to Korea was retrievable: Bessembinder-Chan (1995) and Ratner-Leal (1999) abstracts are unavailable. Korea-specific evidence here is MCC (2001-2007) plus P2's desk checks.
- NRTZ performance after 2011, JKX net-of-cost performance and Faber's performance after 2012 are not verified.
- The AQR 2019 exhibit's fee basis is ambiguous. Its methodology says gross of advisory fees, yet the 2000-2009 excess return (6.3%) equals HOP's net-of-2/20 decade figure.
- Goyal & Jegadeesh (2018 RFS) on time-series vs cross-sectional tests could not be retrieved (404).

---

## Q2. Oscillators and popular indicators (RSI, MACD, stochastics, Bollinger, Williams %R, ADX/ATR, Ichimoku), candlesticks, Fibonacci and Elliott waves: what peer-reviewed tests exist and what survives costs?

### Takeaway
- Published oscillator tests are few, mostly in lower-tier journals, have no data-snooping control, and give market-specific results that do not replicate across markets.
- Candlesticks fail in US large caps.
- Fibonacci levels have no special support/resistance effect, and Elliott waves have no credible peer-reviewed support.
- A 52-rule oscillator family on SPY fails the Reality Check (p = 0.92) and has no rule beating buy-and-hold out-of-sample in 2010-2021.

### Cited Findings
- **Chong, Ng & Liew (2014 JRFM, MDPI), RSI and MACD.**
  - Five OECD indices (Italy's Milan Comit General, Canada's S&P/TSX, DAX, DJIA, Nikkei 225), Jan 1976 to Dec 2002, 10-day returns after signals.
  - MACD(12,26,0) buy-minus-sell spreads are significant only in Milan (+1.379%) and Toronto (+1.335%, t 2.593).
  - RSI(21,50) spreads: Milan +2.268% (t 3.394), Toronto +0.885%.
  - Nothing is significant in the Nikkei; the authors call the rules not robust to market choice.
  - Profitable in Milan and Toronto after a 1% round-trip cost. No formal data-snooping control despite many parameterizations and five markets.
  — [Chong-Ng-Liew, MPRA](https://mpra.ub.uni-muenchen.de/54149/1/MPRA_paper_54149.pdf)
- **Mohd Nor & Wickremasinghe (2014 IMFI).** Australian All Ordinaries, 1996 to Jun 2014, next-day execution, 10-day hold. MACD buy signals are insignificant (about −0.04%/yr). RSI(14, 30/70) long-short averages 0.406% per 10-day signal, significant only at 10% overall. Costs are not modelled, and the authors say profits are too small. — [MNW 2014 PDF](https://businessperspectives.org/images/pdf/applications/publishing/templates/article/assets/6228/imfi_en_2014_04cont_Nor.pdf)
- **Candlesticks: Marshall, Young & Rose (2006 JBF).** 28 patterns (14 single-line, 14 reversal; bullish and bearish) on 35 DJIA stocks, 1992-2002. Bootstrap against an EGARCH null with 500 simulations per stock: no evidence that candlestick lines or patterns predict prices. t-tests show weak predictability in the wrong direction. — [MYR working version (forum mirror)](https://c.mql5.com/forextsd/forum/211/Market%20Timing%20with%20Candlestick%20Technical%20Analysis.pdf); [JBF record](https://ideas.repec.org/a/eee/jbfina/v30y2006i8p2303-2323.html)
- **Candlesticks, Taiwan: Lu, Shiu & Liu (2012 RFE).** Taiwan Top-50 tracker constituents, Oct 2002 to Dec 2008. Three bullish reversal patterns were profitable under a hold-until-opposite-signal rule, with an out-of-sample test and bootstrap. The abstract does not state how costs were treated. — [LSL 2012, IDEAS](https://ideas.repec.org/a/wly/revfec/v21y2012i2p63-68.html)
- **Fibonacci: Tsinaslanidis, Guijarro & Voukelatos (2022, Expert Systems with Applications).** Algorithmically identified Fibonacci zones on DJ30, DAX30 and NASDAQ-100 constituents, Jan 1968 to Mar 2019. The probability of a bounce at a Fibonacci zone is statistically indistinguishable from a bounce at any non-Fibonacci zone. The Fibonacci rule earns lower mean returns than buy-and-hold, especially after risk adjustment. — [TGV 2022 abstract](https://www.sciencedirect.com/science/article/abs/pii/S0957417421012495)
- **Elliott waves.** A metadata search surfaced only a non-refereed SSRN paper on India that stresses the theory's high subjectivity, plus practitioner book chapters. No peer-reviewed out-of-sample test was found. — [Chendroyaperumal 2011, SSRN DOI (metadata only)](https://doi.org/10.2139/ssrn.1887789)
- **Support/resistance (the mechanism behind many indicator "levels"): Osler (2000).** Intraday FX (DEM, JPY, GBP vs USD), Jan 1996 to Mar 1998, levels published by six firms. Rates bounced at published levels 60.8% of the time vs 56.2% at arbitrary levels (+4.6 points), significant for 13 of 16 firm-currency pairs. 96% of published levels end in 0 or 5. No profitability test. — [Osler 2000, NY Fed EPR](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf)
- **Osler (2003 JF).** Take-profit orders cluster at round numbers, which explains reversals at support/resistance. Stop-loss orders cluster just beyond them, which explains fast moves after a break. — [Osler 2003, IDEAS](https://ideas.repec.org/a/bla/jfinan/v58y2003i5p1791-1819.html)
- **DC2b: SPY oscillator family with Reality Check (P2 desk check).**
  - Setup: SPY daily, price only, cash 0, 1999-06-01 to 2021-03-31 (5,495 sessions), long/flat, 52 non-degenerate rules:
    - RSI 2/5/14/21 with 10/90, 20/80, 30/70 entry/exit thresholds, a 50 exit and a ">50" trend version;
    - MACD (12,26,9), (8,17,9) and (5,35,5), signal-line and zero-line versions;
    - Bollinger bands (10/20/50 days, 1.5/2/2.5 s.d.), contrarian and breakout;
    - stochastic %K 5/14 (identical in signal to Williams %R, which is %K − 100) with threshold and %K > %D rules;
    - DMI and ADX > 20/25 filters;
    - Ichimoku close above cloud, tenkan > kijun, and both;
    - Donchian 20/10 and 55/20.
  - At 5 bp per side: 0 of 52 rules beat buy-and-hold mean return; 5 of 52 beat its Sharpe (0.36).
  - Best: RSI14 buy below 20 / exit above 80, Sharpe 0.52, but only 0.3 switches per year (a handful of trades in 22 years). Nominal p = 0.18, RC p = 0.92, SPA p = 1.00.
  - The IS (1999-2009) winner, RSI2 buy below 10 / exit above 50 (+0.40 Sharpe), lost 0.22 OOS (2010-2021). 0 of 52 rules beat buy-and-hold in 2010-2021.
  - Examples of losers: stochastic %K > %D Sharpe −0.39 (14-day) and −0.46 (5-day) with about 103-108 switches per year; MACD(12,26,9) 0.12; Ichimoku close above cloud 0.16; ADX > 25 with +DI > −DI −0.21; Bollinger(20,2) contrarian 0.20 and breakout −0.38.
  — P2 desk check

### Inferences
- **Oscillators.** The only peer-reviewed positives are single-market results (Italy and Canada 1976-2002, weakly Australia) without multiple-testing control. Under P2's family standard they are expected false discoveries. The SPY desk check behaves exactly like a snooped family: a nominal p of 0.18 becomes 0.92 after RC, and the in-sample winner reverses out-of-sample.
- **Duplicates.** Williams %R and stochastics are the same signal. MACD's zero line is an EMA crossover. "RSI > 50" is a short-horizon momentum sign. These are rescaled versions of returns over the last n days, not independent constructs. Treat them as members of the trend/reversal family, never as separate cards: separate cards would inflate the trial count without adding information.
- **Normalized versions as features.** Bollinger %B and RSI(2) "oversold" are normalized short-term reversal signals. They inherit reversal's mechanism (liquidity provision) and its cost problem (DC4).
- **ATR and ADX.** ATR is a volatility estimate and belongs with volatility scaling, which the macro research already handles. ADX as a "trend strength" filter hurt on SPY (Sharpe −0.21).
- **Ichimoku.** No peer-reviewed test was found. On SPY its rules underperformed buy-and-hold (Sharpe 0.12-0.20 vs 0.36).
- **Candlesticks and Fibonacci** have negative rigorous evidence. Elliott waves are not falsifiable as practised because wave counts are subjective. All three go in DO-NOT-BUILD.

### Gaps
- Lento, Gradojevic & Wright (2007) on Bollinger Bands could not be retrieved (404), so there is no verified peer-reviewed Bollinger test beyond P2's desk check.
- No peer-reviewed tests of Ichimoku or ADX were found; a metadata search returned only a practitioner book.
- Batchelor & Ramyar ("Magic numbers in the Dow") could not be retrieved (IDEAS/EconPapers search blocked by robots).
- Marshall, Young & Cahan (2008, Japanese candlesticks): the paper exists (RQFA 31(2), 191-207) but its abstract was unavailable, so its result is not cited — [record](https://ideas.repec.org/a/kap/rqfnac/v31y2008i2p191-207.html).
- The Journal of Technical Analysis (CMT) practitioner evidence was not reviewed this session.

---

## Q3. Mechanisms: why might any technical construct work?

### Takeaway
Credible mechanisms exist, but they predict small, conditional and decaying effects, concentrated where information is slow or valuation is hard and where liquidity is scarce:
- anchoring on salient prices;
- the disposition effect and capital-gains overhang;
- gradual information diffusion;
- order clustering at round numbers (a self-fulfilling coordination effect);
- compensation for supplying liquidity;
- learning under model uncertainty.
The Adaptive Markets Hypothesis fits the documented rise-and-decay pattern better than either "always efficient" or "always exploitable".

### Cited Findings
- **Anchoring: George & Hwang (2004).** Traders treat the 52-week high as a reference point and under-react to good news near it. The no-reversal result fits anchoring better than overreaction models. — [UH PDF](https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf)
- **Disposition effect: Grinblatt & Han (2005 JFE).** Reluctance to sell losers creates under-reaction. A proxy for aggregate unrealized capital gains ("capital gains overhang") generates momentum, and past returns lose predictive power once it is controlled for. — [IDEAS](https://ideas.repec.org/a/eee/jfinec/v78y2005i2p311-339.html)
- **Slow diffusion: Hong & Stein (1999 JF).** "Newswatchers" with gradually diffusing private information produce short-run under-reaction. Trend-chasing "momentum traders" exploit it and cause long-run overreaction. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v54y1999i6p2143-2184.html)
- **Who trades on trends: MOP (2012).** Speculators trend-follow at hedgers' expense, consistent with a hedging-pressure / slow-adjustment risk transfer. — [NYU PDF](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)
- **Coordination and order clustering: Osler (2000; 2003).** Published levels and clustered take-profit/stop-loss orders create small bounce and acceleration effects. — [NY Fed](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf); [IDEAS](https://ideas.repec.org/a/bla/jfinan/v58y2003i5p1791-1819.html)
- **Usage: Menkhoff (2010 JBF).** Survey of 692 fund managers in five countries: the vast majority use technical analysis, and at horizons of weeks it is their most important tool. Users believe prices are heavily driven by psychology. — [IDEAS](https://ideas.repec.org/a/eee/jbfina/v34y2010i11p2573-2586.html)
- **Liquidity provision.**
  - Nagel (2012): reversal returns are the return to liquidity provision and spike with the VIX. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html)
  - Avramov, Chordia & Goyal (2006): reversal concentrates in illiquid stocks and is not exploitable after costs. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html)
  - Da, Liu & Schaumburg (2014): liquidity shocks drive the long side and sentiment plus short-sale constraints drive the short side. — [IDEAS](https://ideas.repec.org/a/inm/ormnsc/v60y2014i3p658-674.html)
- **Volume as a signal of trade type.**
  - Llorente et al. (2002): speculative trades continue, risk-sharing trades reverse. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v15y2002i4p1005-1047.html)
  - Gervais, Kaniel & Mingelgrin (2001): volume shocks raise visibility and subsequent demand. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html)
- **Rational learning.**
  - Zhu & Zhou (2009): MA rules are robust when the model is uncertain. — [IDEAS](https://ideas.repec.org/a/eee/jfinec/v92y2009i3p519-544.html)
  - Detzel et al. (2021): in an equilibrium with learning, technical analysis predicts returns for assets with hard-to-value fundamentals (bitcoin, small, young, low-coverage stocks). — [IDEAS](https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html)
- **Saturation: Lempérière et al. (2014).** Trend signals saturate at large values, consistent with fundamentalists stepping in against strong trends. — [arXiv](https://arxiv.org/abs/1404.3274)
- **Adaptive Markets Hypothesis: Lo (2004 JPM).** Profit opportunities appear and are competed away, the risk/reward relation varies over time, and strategies wax and wane. Rolling first-order autocorrelation of monthly S&P Composite returns, 1871-2003, swings cyclically instead of trending to zero. — [Lo 2004 PDF (MIT)](https://web.mit.edu/Alo/www/Papers/JPM2004_Pub.pdf)
- **AMH evidence in FX: Neely, Weller & Ulrich.** Early FX rule returns were genuine and declined at rates that differ by rule and currency. Complex rules (genetic programming, Markov switching) persisted longer than simple filter/MA rules. Breaks cluster in 1989-1993. — [St. Louis Fed WP](https://files.stlouisfed.org/files/htdocs/wp/2006/2006-046.pdf)
- **Arbitrage capacity: Chordia, Subrahmanyam & Tong (2014 JAE).** Average returns from prominent-anomaly portfolios roughly halved after decimalization. The decline is linked to hedge-fund assets, short interest and turnover. — [IDEAS](https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html)

### Inferences
- **Mechanism-to-construct mapping:**

| Mechanism | Construct it supports | Where it should be strongest |
|---|---|---|
| Anchoring | 52-week-high proximity | Salient price levels |
| Disposition effect | Capital-gains overhang, computable from KRX OHLCV via a turnover-weighted reference price | Retail-heavy markets such as KRX |
| Slow diffusion | Medium-horizon trend | Low-coverage, hard-to-value assets: crypto, KOSDAQ, small caps |
| Liquidity provision | Short-term reversal | Returns peak in stress; costs highest exactly there |
| Order clustering | Round-number features | Intraday only (KIS quotes) |

- The mechanisms imply that technical effects should be largest where QUANTGEN's costs are also largest: illiquid, small and high-volatility names. That is exactly what the KRX desk checks show. Gross effects exist (DC4, DC6), and net effects vanish at 35 bp per side.
- The AMH implies that a technical card's "edge" has a half-life. QUANTGEN should monitor live performance with rolling gates rather than treat a PASS as permanent.
- **Caution on Lo (2004).** If his rolling autocorrelations use Shiller's monthly-average S&P series, as series back to 1871 usually do, their level is inflated by averaging. P2 measured lag-1 autocorrelation of 0.274 in that series (1871-2026) vs 0.057 for SPY month-end returns. The cyclicality may still be informative, but the level is not evidence of exploitable trend.
- **Conflict with the macro decision (flagged, not re-litigated).** Nagel's finding that reversal returns peak when the VIX is high is in tension with the macro research's rule that reversal sleeves are never up-weighted in stress. P2 sides with the macro rule for QUANTGEN, because spreads and impact also peak then and retail costs already exceed the gross reversal premium.

### Gaps
- No direct test of a capital-gains-overhang signal on KRX was found or run. This is a data-check request.
- Evidence on the self-fulfilling coordination channel is FX-intraday only (Osler). Nothing equivalent was found for KRX equities.
- Holbrook Working's (1960) classic result that averaging induces autocorrelation could not be fetched (404). The averaging effect is shown here empirically (DC8) rather than cited.

---

## Q4. Where and when it failed (dated episodes, with numbers)

### Takeaway
- Technical rules fail in five recurring ways: post-publication and out-of-sample decay (US 1987+, FX 1989-1993, trend 2010-2018); market-structure change (decimalization in 2001, ETF listings); whipsaws in range-bound markets (US 2011/2015/2018, KRX 2024-25); V-shaped crashes (Mar 2020, Jul 2026); and cost sensitivity (any rule with more than about 10 switches per year at retail costs).
- QUANTGEN's own futures-trend and sector-momentum cards already sit inside this failure set.

### Cited Findings
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

### Inferences
- **Two distinct crash types matter for QUANTGEN:**
  - (a) Rebound crashes (KRX 1998-01, 2020-04; US 1932, 2009). Momentum and 52-week-high shorts squeeze when beaten-down stocks rally. The Daniel-Moskowitz bear-state gate in the macro research targets this type.
  - (b) A bubble-top crash in the winners themselves (KRX 2026-07). The market came from a strong bull state (+176% in 12 months), so a bear-state gate would likely not have fired. Only volatility scaling and concentration caps would have helped. The nearhigh-neutral construction would not obviously help either, because the winners were at their highs.
- **V-shaped crashes are the structural failure mode of every price-trend filter.** The rule exits after most of the fall and re-enters after most of the rebound. In 2020 (SPY) and 2026 (KRX) the trend filter did worse than buy-and-hold over the full episode.
- **Range-bound years (US 2011/2015/2018, KRX 2024-25) cost the SMA200 3-10 points per year vs buy-and-hold.** These are the "whipsaw tax" years. Over 2010-2019 the tax summed to about 6 points per year of CAGR on SPY.

### Gaps
- KRX index-level episodes use a self-built value-weighted top-200 price-only proxy, not the official KOSPI 200 or KODEX 200 total-return series. Dividends (about 1.5-2%/yr) and the CD-rate cash return are omitted.
- The July-September 2026 marcap figures were not cross-checked against official KRX index data; they post-date P2's external sources.
- No academic source covering 2020-2026 technical-rule performance in Korea was found.

---

## Q5. QUANTGEN translation: which constructs become model cards or features, which go to DO-NOT-BUILD, and how to test a rule family without data snooping

### Takeaway
- BUILD only:
  - (1) the crypto trend card (C3, already PASS);
  - (2) 52-week-high proximity, MA distance and capital-gains overhang as cross-sectional features (cards BACKLOG, with slow rebalancing and long-only implementation);
  - (3) a 52-week-high-neutral construction inside any momentum sleeve;
  - (4) technical indicators as bounded risk-sizing inputs.
- DROP candlesticks, Fibonacci, Elliott waves, chart-pattern rules, standalone oscillators, classic index MA/breakout rule-mining, KRX stock-level MA timing, Korean short-term momentum and the volume-filtered 5-day reversal card.
- Every technical family must clear a pre-registered family-level SPA/RC plus FDR test before any member enters the nine-step gate.

### Cited Findings
- **Multiple-testing hurdle: Harvey, Liu & Zhu (NBER w20592; RFS 2016).** With hundreds of tested factors, new factors should clear t > 3.0, and most claimed findings are likely false. — [NBER w20592](https://www.nber.org/papers/w20592)
- **Family-wise tools validated on technical rules:**
  - White's Reality Check (STW 1999): the best rule's nominal p of 0.004 becomes RC p 0.341 out-of-sample. — [STW](https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf)
  - Stepwise SPA (HHK 2010): identifies individually significant rules without snooping bias and has more power than stepwise RC. — [IDEAS](https://ideas.repec.org/a/eee/empfin/v17y2010i3p471-484.html)
  - FDR plus persistence tests (BS 2012): low costs remove the in-sample edge, and the best rules are not identifiable ex ante. — [IDEAS](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html)
- **Desk-check proof of concept:**
  - SPY trend family (100 rules): best nominal p 0.17 → RC p 0.70; IS winner +0.40 → OOS −0.22.
  - SPY oscillator family (52 rules): nominal p 0.18 → RC p 0.92.
  — P2 desk checks DC1 and DC2b
- **Benchmark choice: HLWZ (2020) and KTW (2016).** Volatility scaling, not trend, drives most of TSMOM's alpha. — [SMU PDF](https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=7520&context=lkcsb_research); [IDEAS](https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html)
- **Execution lag sensitivity.** In the KRX HYZ replication, one extra day of lag cut gross from 30.0% to 18.0%/yr and the 70 bp net from +5.9% to −6.0%/yr. — P2 desk check DC6
- **Averaging trap.** On Shiller's monthly-average prices, skip-month execution lowers 10-month-SMA CAGR from 9.35% to 7.58% (1881-2023). — P2 desk check DC8; [Shiller data page](http://www.econ.yale.edu/~shiller/data.htm)

#### Claims ledger

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

#### Source list
- Brock, Lakonishok & LeBaron (1992 JF): https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html
- Sullivan, Timmermann & White (1999 JF): https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Sullivan_Timmermann_White.pdf
- Park & Irwin (2007 JES; WP): https://www.kdajdqs.org/bbs/presentation/303/download/319 ; https://experts.illinois.edu/en/publications/what-do-we-know-about-the-profitability-of-technical-analysis/
- Hsu & Kuan (2005 JFEc): https://homepage.ntu.edu.tw/~ckuan/pdf/snoop01.pdf
- Hsu, Hsu & Kuan (2010 JEF): https://ideas.repec.org/a/eee/empfin/v17y2010i3p471-484.html
- Bajgrowicz & Scaillet (2012 JFE): https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html (SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1095202 returned 429)
- Marshall, Cahan & Cahan (WP): https://c.mql5.com/forextsd/forum/210/Technical%20Analysis%20Around%20the%20World.pdf ; https://www.ssrn.com/abstract=1181367
- Fang, Jacobsen & Qin (2014 RFE): https://ideas.repec.org/a/eee/revfin/v23y2014i1p30-45.html
- Taylor (2014 JBF): https://ideas.repec.org/a/eee/jbfina/v40y2014icp286-302.html
- Shynkevich (2012 JBF): https://ideas.repec.org/a/eee/jbfina/v36y2012i1p193-208.html
- Neely, Weller & Ulrich (St. Louis Fed WP 2006-046): https://files.stlouisfed.org/files/htdocs/wp/2006/2006-046.pdf
- Neely & Weller (St. Louis Fed WP 2011-001): https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf
- Hsu, Taylor & Wang (2016 JIE): https://ideas.repec.org/a/eee/inecon/v102y2016icp188-208.html
- Faber (practitioner WP, updated): https://mebfaber.com/wp-content/uploads/2016/05/SSRN-id962461.pdf
- Zakamulin (2014 JAM): https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html
- Zakamulin (2018 IRF): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2743119
- Zhu & Zhou (2009 JFE): https://ideas.repec.org/a/eee/jfinec/v92y2009i3p519-544.html
- Neely, Rapach, Tu & Zhou (St. Louis Fed WP 2010-008; MS 2014): https://files.stlouisfed.org/files/htdocs/wp/2010/2010-008.pdf
- Levine & Pedersen (2016 FAJ): https://www.aqr.com/Insights/Research/Journal-Article/Which-Trend-Is-Your-Friend
- Marshall, Nguyen & Visaltanachoti (2017 QF): https://ideas.repec.org/a/taf/quantf/v17y2017i3p405-421.html
- Moskowitz, Ooi & Pedersen (2012 JFE): https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- Hurst, Ooi & Pedersen (2017): https://static.twentyoverten.com/593e8a9e7299b471eaecf644/SkLoGL67M/A-Century-of-Evidence-on-Trend-Following-Investing.pdf ; https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing
- AQR, "You Can't Always Trend When You Want" (2019): https://www.belmontinvestments.com/cimg/file/articles/53/pdf/190425aqrtrendfollowing.pdf
- Lempérière, Deremble, Seager, Potters & Bouchaud (2014, arXiv): https://arxiv.org/abs/1404.3274
- Huang, Li, Wang & Zhou (2020 JFE): https://ink.library.smu.edu.sg/cgi/viewcontent.cgi?article=7520&context=lkcsb_research
- Kim, Tse & Wald (2016 JFM): https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html
- Georgopoulou & Wang (2017 RoF): https://ideas.repec.org/a/oup/revfin/v21y2017i4p1557-1592..html
- Szakmary, Shen & Sharma (2010 JBF): https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html
- Liu & Tsyvinski (NBER w24877): https://www.nber.org/papers/w24877
- Detzel et al. (2021 FM): https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html
- Corbet, Eraslan, Lucey & Sensoy (2019 FRL): https://ideas.repec.org/a/eee/finlet/v31y2019icp32-37.html
- George & Hwang (2004 JF): https://www.bauer.uh.edu/tgeorge/papers/gh4-paper.pdf
- Liu, Liu & Ma (JIMF): https://www.sciencedirect.com/science/article/abs/pii/S0261560610001099
- Jeon & Byun (2023 FAJ): https://epublications.marquette.edu/cgi/viewcontent.cgi?article=1168&context=fin_fac
- Han, Yang & Zhou (2013 JFQA): https://www.smallake.kr/wp-content/uploads/2016/03/49.pdf ; https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/new-anomaly-the-crosssectional-profitability-of-technical-analysis/B9E41049F2E55B4F274D46E72ECA8E29
- Han, Zhou & Zhu (2016 JFE): https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html
- Avramov, Kaplanski & Subrahmanyam (2021 RFE): https://ideas.repec.org/a/wly/revfec/v39y2021i2p127-145.html
- Jegadeesh (1990 JF): https://ideas.repec.org/a/bla/jfinan/v45y1990i3p881-98.html
- Lehmann (1990 QJE; NBER w2533): https://www.nber.org/papers/w2533
- Avramov, Chordia & Goyal (2006 JF): https://ideas.repec.org/a/bla/jfinan/v61y2006i5p2365-2394.html
- de Groot, Huij & Zhou (2012 JBF): https://ideas.repec.org/a/eee/jbfina/v36y2012i2p371-382.html
- Da, Liu & Schaumburg (2014 MS): https://ideas.repec.org/a/inm/ormnsc/v60y2014i3p658-674.html
- Nagel (2012 RFS): https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html
- Medhat & Schmeling (2022 RFS): https://openaccess.city.ac.uk/id/eprint/31278/1/MS_short_term_mom_v27.pdf
- Lee & Swaminathan (2000 JF): https://ideas.repec.org/a/bla/jfinan/v55y2000i5p2017-2069.html
- Gervais, Kaniel & Mingelgrin (2001 JF): https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html
- Conrad, Hameed & Niden (1994 JF): https://ideas.repec.org/a/bla/jfinan/v49y1994i4p1305-29.html
- Cooper (1999 RFS): https://ideas.repec.org/a/oup/rfinst/v12y1999i4p901-35.html
- Llorente, Michaely, Saar & Wang (2002 RFS): https://ideas.repec.org/a/oup/rfinst/v15y2002i4p1005-1047.html
- Lo, Mamaysky & Wang (2000 JF; NBER w7613): https://www.nber.org/system/files/working_papers/w7613/w7613.pdf
- Jiang, Kelly & Xiu (2023 JF): https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf
- Gao, Han, Li & Zhou (2018 JFE): https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html
- Chong, Ng & Liew (2014 JRFM): https://mpra.ub.uni-muenchen.de/54149/1/MPRA_paper_54149.pdf
- Mohd Nor & Wickremasinghe (2014 IMFI): https://businessperspectives.org/images/pdf/applications/publishing/templates/article/assets/6228/imfi_en_2014_04cont_Nor.pdf
- Marshall, Young & Rose (2006 JBF): https://c.mql5.com/forextsd/forum/211/Market%20Timing%20with%20Candlestick%20Technical%20Analysis.pdf ; https://ideas.repec.org/a/eee/jbfina/v30y2006i8p2303-2323.html
- Marshall, Young & Cahan (2008 RQFA), bibliographic only: https://ideas.repec.org/a/kap/rqfnac/v31y2008i2p191-207.html
- Lu, Shiu & Liu (2012 RFE): https://ideas.repec.org/a/wly/revfec/v21y2012i2p63-68.html
- Tsinaslanidis, Guijarro & Voukelatos (2022 ESWA): https://www.sciencedirect.com/science/article/abs/pii/S0957417421012495
- Chendroyaperumal (2011, SSRN; metadata only): https://doi.org/10.2139/ssrn.1887789
- Osler (2000 FRBNY EPR): https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf
- Osler (2003 JF): https://ideas.repec.org/a/bla/jfinan/v58y2003i5p1791-1819.html
- Menkhoff (2010 JBF): https://ideas.repec.org/a/eee/jbfina/v34y2010i11p2573-2586.html
- Grinblatt & Han (2005 JFE): https://ideas.repec.org/a/eee/jfinec/v78y2005i2p311-339.html
- Hong & Stein (1999 JF): https://ideas.repec.org/a/bla/jfinan/v54y1999i6p2143-2184.html
- Lo (2004 JPM): https://web.mit.edu/Alo/www/Papers/JPM2004_Pub.pdf
- Chordia, Subrahmanyam & Tong (2014 JAE): https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html
- Harvey, Liu & Zhu (NBER w20592; RFS 2016): https://www.nber.org/papers/w20592
- Shiller data page: http://www.econ.yale.edu/~shiller/data.htm
- Bibliographic only (abstracts unavailable): Bessembinder & Chan (1995) https://ideas.repec.org/a/eee/pacfin/v3y1995i2-3p257-284.html ; Ratner & Leal (1999) https://ideas.repec.org/a/eee/jbfina/v23y1999i12p1887-1905.html
- QUANTGEN context brief: /home/claude/research_notes/QUANTGEN technical and fundamental signals/00_QUANTGEN_context.md
- P2 desk checks: data-lab files /home/claude/data_raw/marcap/data/marcap-*.parquet, /home/claude/data_raw/us/spy_lean_daily.zip, /home/claude/data_raw/us/shiller_sp500_monthly.csv

### Inferences

#### BUILD / BACKLOG / DO-NOT-BUILD register (P2 recommendation)
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

#### How to test a family of technical rules without data snooping (proposed "family gate", run before the nine-step gate)
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

#### Corrections to the prior design ("QUANTGEN Signal & Macro Map", 1 Oct 2026) and flags vs the macro research
- **Time-series trend.** "0.4-0.8 per asset, ~1.0 diversified" are pre-2009 gross figures (MOP, HOP). Expect 0.0-0.3 diversified after 2009 before the 60% haircut (AQR 2019; QUANTGEN B3 0.08). Lower the US/EM TS-mom weight from 3 to 1 for index timing and keep crypto at 3.
- **Volatility-scaling uplift.** HLWZ and KTW indicate that most TSMOM alpha *is* volatility scaling. This agrees with the macro research's correction that vol scaling is robust mainly for momentum. Trend cards must beat vol-scaled buy-and-hold.
- **Short-term reversal with volume filter.** Replace "0.5-1.0 gross, costs take half or more" with this for KRX at 35 bp per side: costs take *more than all* (gross Sharpe 1.20 → net −1.35, weekly, 1996-2026). Lower the Korea ST-reversal weight from 3 to 1, as a feature only.
- **Conflict with the macro note's Korean 1-month reversal.** The macro note's −2.95%/month (t −3.77, 1999-2021) is not reproduced in KRX top-500 stocks: 1-month reversal there is +0.41%/month gross (t 1.20) over 1996-2026 and about zero after 2006. The effect likely sits in small, illiquid names where it is least harvestable.
- **Momentum crash control.** The macro research's Daniel-Moskowitz bear gate addresses rebound crashes. The July 2026 KRX momentum crash came from a bull state, so P2 asks the data lab to test whether the gate would have reduced exposure (data check DC-J). P2 expects it would not, and recommends that the nearhigh-neutral construction and the existing Samsung/SK hynix concentration caps be evaluated together.
- **Reversal sizing.** Keep the macro research's rule that reversal sleeves are never up-weighted in stress, despite Nagel's VIX result.

#### Data-check requests for the data lab (exact tests)
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

### Gaps
- The proposed family gate thresholds (SPA p ≤ 0.10; 60% persistence; t ≥ 3.0) are P2's design choices. They come from the cited literature's conventions but have not been tested on QUANTGEN's 34-card record.
- No net-of-cost study of 52-week-high or MAD signals specific to Korea was found. P2's KRX numbers are unreviewed desk checks with literature parameters; the data lab should re-run them under the gate (DC-A, DC-I).
- **Access limits this session:**
  - Web search budget exhausted (200-call session cap).
  - Semantic Scholar and some Crossref API calls rate-limited (429).
  - IDEAS/EconPapers search pages blocked by robots.txt.
  - Direct PDF downloads blocked by egress policy (403 CONNECT).
  - Several papers were therefore cited from abstracts or bibliographic records only (see Gaps under Q1-Q3).
