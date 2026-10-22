# E3: How professional trend followers implement trend systems, how they performed through 2026, and what QUANTGEN's trend cards should claim

**Persona line.** E3 is the Chief Investment Officer of a systematic managed-futures program and a former commodities trader at a Goldman-style bulge-bracket desk. E3 is a *fictional composite persona*: it is not a real person and speaks for no real firm. The lens is implementation: what a trend book keeps after roll, costs and fees, and what drawdowns its investors actually sit through. E3 distrusts single-asset backtests and any card that measures a diversifier against a long-only benchmark.

**Position summary.**
- **Evidence vs record.** Diversified time-series momentum (TSMOM) is among the best-documented effects in finance:
  - AQR's simulation earns a net Sharpe of 0.77 over 1880–2013.
  - All 58 liquid futures showed positive 12-month TSMOM in 1985–2009.
  - The realised industry record is much weaker. Net-of-fee CTA indices ran at a Sharpe of about 0.5–0.6 from 2000 to 2022. Over 2009–2025 the annual mean-to-SD ratio was about 0.30, and 2009–2018 was a lost decade (Barclay Systematic Traders CAGR −0.30%).
- **B3.** QUANTGEN's futures card (B3) was rejected with "no measurable edge after 2009", which is what the industry itself recorded after 2009. With ten markets, about 17 years out of sample and a long-only benchmark (Sharpe 0.58), B3 could not have passed even if its true net Sharpe were a realistic 0.3–0.4.
- **C3.** The crypto card passed for three reasons: crypto still shows strong 1–4 week autocorrelation, its volatility is large relative to a 10 bp cost, and its −75% to −85% bear markets can be sidestepped by a long/flat rule.
  - E3's replication on Coin Metrics data finds the edge is timing, not volatility scaling.
  - The edge shrank in 2022–2026 and was negative in 2025.
- **Single equity indices.** Trend on one equity index is a protective tool, not an alpha source.
  - On SPY (1999–2021) and a survivorship-free KOSPI proxy (1996–2026), a multi-speed long/flat rule cut maximum drawdown by about 13–17 percentage points versus a static book with the same average exposure, at roughly unchanged Sharpe.
  - It lost badly in 2009–2019 and did not protect in the 22 Jun–30 Jul 2026 KOSPI crash. A 20% volatility target (VT20) did.
- **What to build.** Trend handles slow bear markets and VT20 handles fast crashes, so the credible equity card is "trend × VT20", registered as a protective card (CARD-P). A diversified futures card should be re-registered with:
  - at least 25 markets;
  - a fixed multi-speed ensemble;
  - per-asset volatility scaling;
  - a *diversifier* claim, tested against cash plus a portfolio-uplift test.
- **What to drop.** QUANTGEN should drop trend evidence built on Shiller monthly-average prices, which inflate trend Sharpe. It should also expect the ≥60%-positive-years step to reject most trend cards: that step would have rejected the net CTA industry over 2009–2025 (9 of 17 positive years).

**Note on structure.** Sections 1–7 follow the researcher template (Takeaway / Cited Findings / Inferences / Gaps). The project's mandatory items are kept as well: section 7 holds the failure episodes, and the data-check requests, claims ledger (E3-C01 … E3-C30) and source list follow at the end. "E3 check" means E3's own computation on local data, described in §3. These checks are in-sample illustrations, **not runs of QUANTGEN's gate**.

---

## 1. Industry performance 2000–2026: SG CTA / SG Trend, BarclayHedge, and dispersion across managers

### Takeaway
- **Two eras.** Net-of-fee CTA returns split cleanly:
  - 2000–2008: steady gains, with Barclay Systematic Traders positive in 9 of 9 years (CAGR 6.98%).
  - 2009–2018: flat to negative (CAGR −0.30%, 3 of 10 years positive).
  - Since then: lumpy recovery. 2022 was a record year (SG Trend +27.3%), 2023–2025 were lean, and April 2025 brought the worst rolling-12-month loss in SG Trend history (−18.6%).
- **2026.** Year-to-date about +16% (SG Trend +15.85%, BarclayHedge estimate as of 1 Oct 2026).
- **Dispersion.** It is large and persistent: about a 15% best-to-worst range in 2024, and 30% among trend followers in early 2025.

### Cited Findings
- **Index construction.**
  - SG CTA and SG Trend are equal-weighted, reconstituted annually and calculated from the *net* daily returns of large CTAs open to new investment (SG CTA) or of trend followers (SG Trend). The SG Short-Term Traders Index (STTI) covers managers with average holding periods under 10 days. — [SG Prime Services indices page](https://wholesale.banking.societegenerale.com/en/prime-services-indices/)
  - Barclay CTA Index: 305 programs in 2026, equal-weighted, rebalanced each January — [BarclayHedge, Barclay CTA Index](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Barclay-CTA-Index)
  - Barclay Systematic Traders Index: 224 programs — [BarclayHedge, Systematic Traders](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index)
  - BTOP50: 20 funds in 2026 that together hold at least 50% of investable assets in the Barclay CTA universe — [BarclayHedge, BTOP50](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-Investable-Benchmarks&indexName=BTOP50-Index)
- **Annual returns, % (net as reported).** Barclay CTA and Barclay Systematic come from the two BarclayHedge pages above. SG columns are sourced cell by cell (see the notes below). "n.r." means not retrieved.

| Year | Barclay CTA | Barclay Systematic | SG Trend | SG CTA | Other / notes |
|---|---|---|---|---|---|
| 2000 | 7.86 | 9.89 | n.r. | n.r. | |
| 2001 | 0.84 | 2.99 | n.r. | n.r. | |
| 2002 | 12.36 | 12.09 | n.r. | n.r. | |
| 2003 | 8.69 | 8.71 | n.r. | n.r. | |
| 2004 | 3.30 | 0.54 | n.r. | n.r. | |
| 2005 | 1.71 | 0.95 | n.r. | n.r. | |
| 2006 | 3.54 | 2.10 | n.r. | n.r. | |
| 2007 | 7.64 | 8.72 | n.r. | n.r. | |
| 2008 | 14.09 | 18.16 | n.r. | < 20.1 (inferred: 2022 was its best year) | |
| 2009 | −0.10 | −3.38 | 2009–13 cumulative −1.8 | n.r. | |
| 2010 | 7.05 | 7.82 | | | |
| 2011 | −3.09 | −3.83 | | | |
| 2012 | −1.70 | −3.20 | | | |
| 2013 | −1.42 | −1.10 | | | |
| 2014 | 7.61 | 10.32 | n.r. | < 20.1 (inferred) | |
| 2015 | −1.50 | −2.92 | n.r. | n.r. | |
| 2016 | −1.23 | −1.78 | n.r. | n.r. | |
| 2017 | 0.70 | 0.53 | n.r. | n.r. | |
| 2018 | −3.17 | −4.31 | rolling 12m −16.0 to Jan 2019 | n.r. | |
| 2019 | 5.17 | 4.97 | (2019–22 cumulative +61.3) | (2019–22 cumulative +39.8) | |
| 2020 | 5.43 | 5.54 | Mar 2020 +1.1 | n.r. | |
| 2021 | 5.03 | 3.81 | n.r. | n.r. | TTU TF Index +10.02 |
| 2022 | 7.13 | 7.52 | **+27.3** | **+20.1** | STTI +11.3; BTOP50 +13.8 |
| 2023 | −0.39 | −1.04 | −4.16 | n.r. | BTOP50 −1.70 |
| 2024 | 3.45 | 3.32 | +2.42 (TTU) / +2.6 (AT) | +2.4 | BTOP50 +4.44 |
| 2025 | 3.10 | 1.72 | +2.39 (TTU) / +2.4 (AT) | −0.2 | BTOP50 +2.81; S&P 500 TR +17.89 |
| 2026 YTD | +7.55 (est., 1 Oct) | +7.36 (est., 30 Sep) | **+15.85** (est., 1 Oct) | **+15.67** (est., 1 Oct) | Through Aug: SG Trend +11.07, BTOP50 +11.13, S&P 500 TR +13.14 |

  - **Table sources by cell:**
    - SG Trend 2009–13 cumulative, the Jan-2019 rolling figure and the 2008 GFC note: [Man Group, "Is this time different?"](https://www.man.com/insights/is-this-time-different).
    - SG Trend Mar 2020: [Man AHL via AIMA](https://www.aima.org/article/trend-following-and-long-short-quality-loading-the-dice.html).
    - 2022 SG figures and 2019–22 cumulatives: [Hedgeweek, 27 Jan 2023](https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/) and [AlphaWeek, 9 Feb 2023](https://www.alpha-week.com/2022-cta-index-performance-review).
    - 2022 BTOP50: [TTU Dec 2022](https://www.toptradersunplugged.com/trend-following-performance-report-december-2022/).
    - 2023: [TTU Dec 2023](https://www.toptradersunplugged.com/trend-following-performance-report-december-2023/).
    - 2024: [TTU Dec 2024](https://www.toptradersunplugged.com/trend-following-performance-report-december-2024/), [Aussie Turtles Dec 2024](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2024/), and SG CTA 2024 from [CFM, Mar 2025](https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/).
    - 2025: [TTU Dec 2025](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/) and [Aussie Turtles Dec 2025](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/).
    - 2021: [TTU Dec 2021](https://www.toptradersunplugged.com/trend-following-performance-report-december-2021/).
    - 2026: [BarclayHedge SG Trend](https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=SG-Prime-Services-Indices&indexName=SG-Trend-Index), [BarclayHedge SG CTA](https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=SG-Prime-Services-Indices&indexName=SG-CTA-Index) and [TTU Aug 2026](https://www.toptradersunplugged.com/trend-following-performance-report-august-2026/).
- **Era split (E3 compounding of the BarclayHedge annual returns above).**
  - Barclay Systematic: 2000–2008 cumulative +83.6% (CAGR 6.98%, 9/9 years positive, mean 7.13%/yr, SD 5.95%). 2009–2018 cumulative −2.9% (CAGR −0.30%, 3/10 years positive). 2009–2019 CAGR +0.17%. 2019–2025 CAGR 3.66%. 2000–2025 CAGR 3.24%.
  - Barclay CTA: 2009–2018 CAGR 0.25%; 2000–2025 CAGR 3.44%.
  - Barclay Systematic 2009–2025: mean 1.41%/yr, SD 4.63%, ratio 0.30, positive in 9/17 years (53%).
  - Sources: [BarclayHedge Systematic](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index), [BarclayHedge CTA](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Barclay-CTA-Index)
- **Drawdown episodes (Man).**
  - The SG Trend Index lost −1.8% in total from 2009 to 2013.
  - Its rolling 12-month return reached −18.6% at 30 Apr 2025. Only twice in its history has it lost more than 15% over 12 months; the earlier worst was −16.0% in Jan 2019.
  - After every rolling 12-month drawdown worse than −10%, the following 12 months averaged +9.8%.
  - For a hypothetical strategy with Sharpe 0.5, 10% volatility and zero correlation, the chance of a drawdown of 20% or more over 25 years is nearly four in five.
  - Man also states the SG Trend Index fell more than 17% peak to trough "during the GFC" (context unclear; see Gaps).
  - Source: [Man Group, Korgaonkar 2025](https://www.man.com/insights/is-this-time-different)
- **The April 2025 tariff episode (SG).**
  - SG Trend −9.3% year-to-date to 13 Apr 2025; STTI −0.9%.
  - April 2025, as reported: SG Trend −4.9%, STTI −0.9%.
  - A 30% spread between the best and worst trend followers year-to-date; the best short-term program was up nearly 15%.
  - In 2024, average pairwise correlation among constituents was 0.78, yet the range of returns was nearly 15%.
  - The SG Trend Indicator (SG's model) has a 0.75 lifetime correlation with the SG Trend Index. Since 2007 the index fits slower (60–300-day) moving-average models better, i.e. CTAs have slowed.
  - Source: [SG CTA Industry Update, May 2025](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025)
- **Other dated episodes.**
  - The trailing 12-month return to June 2025 was −15.05% for SG Trend, against +15.18% for the S&P 500 TR — [TTU June 2025](https://www.toptradersunplugged.com/trend-following-performance-report-june-2025/)
  - SG Trend +36% year-to-date through September 2022, while a global 60/40 portfolio was −20% — [AQR, "Trend-Following: Why Now?", Nov 2022](https://www.aqr.com/Insights/Research/White-Papers/Trend-Following-Why-Now-A-Macro-Perspective)
  - In 2022, 27 of 30 SG CTA programs were positive, and trend followers ranged from +11% to +40% — [AlphaWeek](https://www.alpha-week.com/2022-cta-index-performance-review)
- **Cumulative since 2020 (Aussie Turtles).** SG Trend +49.0% (CAGR 6.9%) and SG CTA +29.8% (CAGR 4.4%) from Jan 2020 to Dec 2025. Through Feb 2026: SG Trend +62.1%, SG CTA +40.6%, with 2026 year-to-date at +8.8% and +8.3%. Comparator indices in 2024: Classic Trend +18.8% and Eurekahedge TF +16.4%, versus SG Trend +2.6%. — [Aussie Turtles Dec 2025](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/), [Feb 2026](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-february-2026/), [Dec 2024](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2024/)
- **2026 drivers (TTU).** Profits came mainly from moves already a week or more old: an equity uptrend since spring, grains near highs in August, short meats and VIX, and short bitcoin (falling since January). June and July losses were largely recovered in August. — [TTU Aug 2026](https://www.toptradersunplugged.com/trend-following-performance-report-august-2026/)
- **Dispersion is not rising (CFM).** Using SG CTA constituents over 2010–2024, the cross-sectional SD of monthly returns averaged about 2% per month with no visible drift. Pairwise correlation sat near 50%. The index is explained by trend following with about 85% regression correlation. — [CFM, Mar 2025](https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/)
- **Realised Sharpe (CFM).** From 2000 to mid-2022 the SG CTA Index had a Sharpe of 0.61, against 0.44 for the S&P 500. Individual CTA track records converge toward about 0.5. CFM's 200-year trend backtest gives about 0.7 before costs and fees. CFM attributes the 2009–2013+ weakness to central-bank QE. — [CFM, "A Good Time for Trend Following", May 2022](https://www.cfm.com/wp-content/uploads/2022/12/39-A-Good-Time-for-Trend-Following-FINAL.pdf)
- **Equity-crisis behaviour (E3 arithmetic, 1999–2020).** Annual Barclay CTA returns correlate −0.40 with SPY's annual price return. Barclay CTA was positive in SPY's down years 2000 (+7.9), 2001 (+0.8), 2002 (+12.4) and 2008 (+14.1). It was negative in the mild down years 2011 (−3.1), 2015 (−1.5) and 2018 (−3.2). — [BarclayHedge CTA](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Barclay-CTA-Index); SPY from local LEAN data (see §3 method)

### Inferences
- **Derived SG Trend values** (approximate; rounding-sensitive):
  - 2019–2021 cumulative ≈ +26.7% (= 1.613 / 1.273 − 1).
  - 2020–2021 cumulative ≈ +16.5% (from the +49.0% for 2020–2025 divided by the product of the 2022–2025 annual returns).
  - SG CTA 2019–2021 ≈ +16.4%.
  - Q4 2022 ≈ −6.4% (= 1.273 / 1.36 − 1). Even the record year ended with a sharp give-back.
  - 2026 to date: about +4.7% in January, +3.9% in February, only about +2% from March to August, and about +4.3% in September (BarclayHedge's month-to-date figure as of 1–2 Oct is almost certainly September). The year's gains are concentrated in a few months.
- **Cash return.** CTA index returns include interest on collateral. US bill yields in 2023–2025 were far above zero, so the SG Trend Index's +2.4% in 2024 and 2025 most likely means near-zero or negative *excess* returns. The T-bill series could not be fetched; see Gaps.
- **Industry indices are not one return stream.** In 2022: SG Trend +27.3%, BTOP50 +13.8%, Barclay Systematic +7.5%. In 2024: Classic Trend +18.8% vs SG Trend +2.6%. Index construction (largest trend followers vs hundreds of equal-weighted programs) matters as much as the strategy.
- **Persona view.** What investors in this industry actually live with is a decade (2009–2018) in which roughly 3 years in 10 are positive, then 30%-plus years. Any gate that requires steady annual hit rates will fight the payoff shape of trend following.

### Gaps
- **SG annual series.** The full SG CTA / SG Trend annual series for 2000–2021 (including 2008, 2014 and 2020) could not be retrieved. SG's historical spreadsheet host was blocked by the egress proxy (403), and the BarclayHedge SG pages render without their tables. The Barclay series stands in for those years.
- **SG constituent counts** were not verified (SG's methodology PDF returned 403).
- **BarclayHedge fee basis.** The methodology statement (whether index returns are net of all fees, and how interest income is treated) was not fetched. Returns are described here only as reported.
- **T-bill yields** for 2023–2026 excess returns: FRED was blocked by the egress proxy (403) and its TB3MS text page was rate-limited (429), so excess returns are not computed.
- **Man's ">17% peak-to-trough during the GFC"** for SG Trend: the exact window is unclear. It conflicts with trend following's strong calendar 2008 and may refer to the post-2008 period.
- **2024 SG Trend:** sources conflict slightly (+2.42% TTU vs +2.6% Aussie Turtles).

---

## 2. Academic evidence vs practitioner results: reconciliation

### Takeaway
- **Gross backtests vs live net.** Diversified, vol-scaled TSMOM backtests show gross Sharpe of about 1.0–1.8. Live, net-of-fee industry results are about 0.5–0.6 since 2000 and about 0.3 since 2009.
- **Where the gap comes from:**
  - fees (2/20 takes about 6% a year on a gross-1.8 strategy);
  - costs and roll (1–4% a year);
  - the decay of short-horizon trends;
  - a 2009–2019 regime of smaller market moves and higher cross-asset correlation.
- **Asset-level evidence is fragile.** Much of the measured alpha comes from volatility scaling and from cross-sectional mean returns rather than true asset-level predictability.

### Cited Findings
- **Moskowitz–Ooi–Pedersen 2012 (JFE).**
  - Sample: 58 futures (24 commodities, 9 equity indices, 13 bonds, 12 FX), 1985–2009.
  - Rule: 12-month sign, 1-month hold, 40% per-asset ex-ante volatility scaling, EWMA volatility with a 60-day centre of mass.
  - Every contract had positive TSMOM; 52 of 58 were significant.
  - Diversified gross Sharpe above 1.0; alpha 1.58% per month (t 7.99).
  - Alpha t-stats by asset class: commodities 4.66, equities 3.77, fixed income 3.53, FX 3.41.
  - A straddle-like smile against the market (coefficient on squared market returns 1.99, t 3.88).
  - Partial reversal after 12 months.
  - Source: [MOP 2012](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf)
- **Hurst–Ooi–Pedersen, "A Century of Evidence" (2014 AQR white paper version).**
  - Sample: 67 markets (29 commodities, 11 equity indices, 15 bonds, 12 FX), 1880–2013.
  - Rule: equal-weight 1-, 3- and 12-month signals, equal-volatility positions, 10% portfolio volatility.
  - Costs and fees: 2/20 fees with a high-water mark. One-way costs for 2003–2013 were 0.06% (equities), 0.01% (bonds), 0.10% (commodities) and 0.03% (FX), multiplied by 6 for 1880–1992 and by 2 for 1993–2002.
  - Results: gross 14.9%, net 11.2%, volatility 9.7%, net Sharpe 0.77. Correlation 0.00 with US equities and −0.04 with bonds.
  - Net Sharpe was positive in every decade; 2000–2013 net Sharpe was 0.62.
  - Positive in 8 of the 10 largest 60/40 drawdowns:
    - GFC (Nov 2007–Feb 2009): +17.8% vs −39.5%.
    - Dot-com: +28.8% vs −27.9%.
    - 1937–38 recession (a failure): −6.8% vs −26.1%.
  - Worst strategy drawdowns: −26.3% (Aug 1947–Dec 1948, recovered May 1951) and −25.3% (Feb 1937–Jun 1940).
  - A 20% allocation raised a 60/40 portfolio's Sharpe from 0.38 to 0.54 and cut its max drawdown from −62.3% to −50.3%.
  - Systematic trend AUM grew from $22bn (1999) to $280bn (2014).
  - Source: [HOP 2014 PDF](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- **HOP 2017, published in the *Journal of Portfolio Management* (1880–2016).** Average correlations rose meaningfully from late 2008 to mid-2014 as markets moved "risk-on/risk-off", and the strategy does best when correlations are low. — [HOP 2017 (Yale course copy)](https://fairmodel.econ.yale.edu/ec439/hurst.pdf); [JPM listing](https://www.pm-research.com/content/iijpormgmt/44/1/15)
- **Hurst–Ooi–Pedersen 2013, "Demystifying Managed Futures".**
  - Sample: 58 instruments, 1985–2012.
  - TSMOM explains the BTOP50, the DJCS Managed Futures index and the five largest managers: R² 0.36–0.64, correlations 0.66–0.78.
  - The simulated TSMOM's gross Sharpe of 1.8 at 10% volatility falls to about 1.0 after 2/20 fees (about 6% a year) and 1–4% a year in costs.
  - Index net Sharpe ratios: 0.27–0.88.
  - Implied manager weights: 1-month 24%, 3-month 54%, 12-month 22%.
  - Source: [HOP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/DemystifyingManagedFutures.pdf)
- **Levine–Pedersen 2016 (FAJ), "Which trend is your friend?"**
  - Sample: 58 instruments, 1985–2015.
  - Moving-average crossovers (MACROSS) and TSMOM are special cases of each other.
  - Gross Sharpe: TSMOM(22d) 0.97, TSMOM(66d) 1.20, TSMOM(260d) 1.45; MACROSS(3,12) 1.01, (8,32) 1.06, (32,128) 1.33.
  - R² above 80% in all cross-regressions; no MACROSS alpha over TSMOM.
  - Source: [LP 2016 (CBS publisher version)](https://research-api.cbs.dk/ws/portalfiles/portal/60084063/lasse_heje_pedersen_et_al_which_trend_is_your_friend_publishersversion.pdf)
- **Baltas–Kosowski, "Demystifying TSMOM" (2017 version; Wiley 2020 chapter).**
  - Sample: 56 futures, 1983–2013.
  - The Yang–Zhang volatility estimator cuts turnover 17% (t 5.33) at no performance cost.
  - The TREND rule (capped t-statistic) cuts turnover 24%; combined, the cut is 36%.
  - Gross Sharpe: SIGN 1.15 vs TREND 1.11.
  - Modelled annual costs fall from 163 bp (default) to 105 bp.
  - Correlation-adjusted leverage (CF) lifts the full-sample Sharpe from 1.15 to 1.19.
  - In 2009–2013 the default TSMOM Sharpe was 0.01 gross and −0.09 net; with CF, 0.17 gross and 0.06 net.
  - Causes: fewer strong trends, and higher correlations after 2004 (commodity financialisation) and after 2008 (across asset classes).
  - Source: [BK via CME Group](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf); [Wiley chapter](https://onlinelibrary.wiley.com/doi/abs/10.1002/9781119599364.ch3)
- **Lempérière et al. 2014 (CFM, arXiv).** Trend t-statistic about 5 since 1960 and about 10 since 1800, stable across asset classes. Long trends show no statistical degradation; shorter trends have withered. — [arXiv 1404.3274](https://arxiv.org/abs/1404.3274)
- **Huang–Li–Wang–Zhou 2020 (JFE).**
  - Sample: 55 futures, 1985–2015.
  - Only 8 of 55 assets show significant predictive slopes at 10%; out-of-sample R² is negative for 45 of 55.
  - The pooled t of 4.34 falls short of bootstrap critical values of 4.83 (pairs) and 12.53 (wild).
  - A "time-series history" (TSH) strategy, which buys assets with a positive historical mean, matches TSMOM (difference 0.14%, p 0.19).
  - Without volatility scaling, t drops to 1.68.
  - Profits come mainly from long legs; short legs are insignificant.
  - Source: [HLWZ working paper](https://down.aefweb.net/WorkingPapers/w717.pdf); [RePEc JFE](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html)
- **Kim–Tse–Wald 2016 (JFM).**
  - Sample: 55 futures, 1985–2009.
  - Monthly alphas: vol-scaled TSMOM 1.08%, unscaled TSMOM 0.39%, unscaled buy-and-hold 0.40%, vol-scaled buy-and-hold 0.73%.
  - Conclusion: TSMOM's results are largely driven by volatility scaling.
  - Source: [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1386418116301379)
- **Babu et al., "Trends Everywhere".**
  - Sample: 156 assets, 1985–2017: 58 traditional; 82 alternative (including KOSPI 200, MSCI Taiwan, Nifty and China A); 16 equity factors.
  - 12-month gross Sharpe: traditional 1.17, alternative 1.34, factors 0.95, all combined 1.60.
  - Median *single-asset* Sharpe only 0.34–0.39.
  - Returns are gross of costs.
  - Source: [Trends Everywhere WP](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/fd3c53f7-c472-4898-a7e1-f6c100b1b81e.pdf)
- **Babu et al. 2020 (JPM), "You Can't Always Trend When You Want".** The weak 2010s came from smaller-than-usual market moves, not from a loss of the ability to monetise trends, and show little sign of permanent structural change. — [AQR summary](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want)
- **Hamill–Rattray–Van Hemert (Man AHL), 1960–2015.**
  - Performance was best in the worst equity and bond environments (a smile).
  - Lags of 1–4 months were consistently strong; lags of 5–8 months underperformed.
  - Faster momentum had more positive skew.
  - Restricting equity or bond positions to non-positive improved protection in one asset class but worsened it in the other.
  - Source: [Man Institute](https://www.man.com/maninstitute/trend-following-equity-and-bond-crisis-alpha); [SSRN 2831926](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2831926)
- **Harvey et al. / Man, "Best strategies for the worst crises" (1985–2016).** TSMOM performed well in all seven S&P 500 drawdowns larger than 15%. A version excluding long equity positions did as well. Puts were the most reliable hedge but costly. — [Man Institute (Taylor)](https://www.man.com/maninstitute/best-strategies-for-the-worst-crises); [SSRN 3383173](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3383173)
- **Koijen–Moskowitz–Pedersen–Vrugt, "Carry" (1983–2012).**
  - Carry is a separate predictor. Gross Sharpe of the diversified global carry factor is 1.10 (equities 0.74, commodities 0.66, FX 0.54, bonds 0.48).
  - Fixed-income and commodity carry load positively on TSMOM; equity carry does not.
  - Carry suffers in recessions (e.g., Aug 2008–Feb 2009).
  - Source: [NBER w19325](https://www.nber.org/system/files/working_papers/w19325/w19325.pdf)
- **Goulding–Harvey–Mazzoleni 2023 (JFE), abstract.** Turning points occur when slow and fast momentum signals disagree. Intermediate-speed blends earn positive unconditional alpha by exploiting market cycles. — [RePEc](https://ideas.repec.org/a/eee/jfinec/v149y2023i3p378-406.html)

### Inferences
- **Reconciliation arithmetic.**
  - Start from a gross backtest Sharpe of about 1.0–1.2 for a 50-plus-market book (MOP, LP, BK).
  - Subtract about 0.3–0.5 for 2/20 fees and costs. HOP 2013's 1.8 → 1.0 includes an unusually strong gross figure.
  - Allow post-publication decay and the faster-signal decay noted by Lempérière and SG.
  - The result is about 0.5–0.6 live, which matches CFM's 0.61 for SG CTA over 2000–2022. In a 2009–2019-type regime (smaller moves, higher correlation) it falls to about 0–0.3.
  - QUANTGEN users pay no fee, so their relevant number is gross of fees but net of costs, i.e. a few tenths above the CTA index figures.
- **HLWZ and KTW together** say a single-asset trend signal is a weak predictor and that vol scaling does much of the work. Every trend card should therefore print two controls at the same average exposure: (a) a vol-scaled long-only book and (b) the TSH control. A trend card that cannot beat its own vol-scaled long-only control has not shown a trend effect.
- **Speed evidence conflicts.** Lempérière and SG point to slower trends surviving; Hamill et al. and HOP 2013's manager weights point to 1–4-month signals for crisis alpha. E3's resolution: fix an equal-weight multi-speed ensemble before the test, and never let walk-forward choose speed. Speed-chasing is a classic way to buy the last regime.

### Gaps
- **Baltas–Kosowski (2013), "Momentum strategies in futures markets and trend-following funds",** on capacity and frequency: the SSRN page returned 429 and was not read.
- **Kaminski, "In Search of Crisis Alpha"** (CME Group): the URL returned 404. Crisis-alpha evidence above comes from Man and AQR instead.
- **HOP 2017 decade table.** The 2010–2016 net Sharpe was not extractable from the PDF text; only the 2014 version's decade table (to 2013) is quoted.

---

## 3. Equity-index trend (S&P 500, KOSPI/KOSPI200, Nikkei): protection vs alpha

### Takeaway
- **Protection.** On a single equity index, trend is a drawdown-control rule with roughly zero Sharpe uplift over the full cycle. It cut max drawdown versus a static book of the same average exposure on both SPY and KOSPI. That makes it a genuine protective claim, not simple de-gearing.
- **Cost.** It loses in V-shaped markets and whipsaw decades: 2009–2019; Feb–Dec 2020; and the KOSPI crash of 22 Jun–30 Jul 2026, which arrived from a strong uptrend.
- **Why E1 was rejected.** E1 (max drawdown −15% vs −27%, Sharpe 0.84 vs 0.95) is a textbook protective rule judged on an outperformance claim.

### Cited Findings
**Method of the E3 local checks (applies to every "E3 check" in this note).**
- **Data.**
  - SPY: LEAN raw daily closes, 2 Jan 1998–31 Mar 2021 (`/home/claude/data_raw/us/spy_lean_daily.zip`).
  - KOSPI proxy: the cap-weighted daily return of all KOSPI-listed stocks from the survivorship-free KRX marcap files (May 1995–29 Sep 2026; `/home/claude/data_raw/marcap/data`). Weights are prior-day market cap; ChangesRatio is clipped to ±30%; price-only.
    - Validation: 2008 −40.9%, 2022 −25.0%, H1-2026 +101.1%, 22 Jun–30 Jul 2026 −38.0%. The macro research reports about +101% and −38.6% for H1-2026 and the crash window.
    - A KOSPI200-like top-200 proxy correlates 0.9977 daily with it.
  - Shiller monthly S&P 500 (monthly *average* prices), 1871–Sep 2026.
  - Crypto: Coin Metrics community PriceUSD.
- **Conventions.**
  - Decide at the close of t, earn from t+1.
  - Costs per side on |Δweight|: 5 bp for equity and futures, 10 bp for crypto, plus a 2× rerun.
  - Returns are price-only (no dividends, no cash yield).
  - Static comparator S = buy-and-hold × the rule's average exposure, on the same days and without cost (the macro spec's CARD-P comparator).
- **Rules.**
  - "ens L/F": the share of positive signs of the 20/60/120/250-day returns (QUANTGEN's prior-design lookbacks), giving exposure 0, ¼, ½, ¾ or 1.
  - "200d L/F": long when the close is above its 200-day moving average.
  - "ens L/S": the mean of the four signs.
  - "VT20": min(1, 0.20/σ20), with σ20 from a 20-day SMA of daily returns (QUANTGEN macro rule R-06).
  - "VS15": min(1, 0.15/σ_EWMA60).
- **Caveats.** In-sample, no walk-forward or bootstrap. About 40 configurations were tried across this note.

**Results.**
- **SPY 200d L/F, 1999–2021, 5 bp.**
  - Sharpe 0.38 vs buy-and-hold 0.40; max drawdown −30.0% vs −56.5%; static S (exposure 0.72) −43.8%; about 7.4 switches a year.
  - By period: 1999–2008 Sharpe 0.05 vs −0.04 (drawdown −30.0% vs −51.4%); 2009–2019 Sharpe 0.57 vs 0.79; 2008 calendar 0.0% vs −38.3%.
  - Source: E3 check (SPY LEAN data)
- **SPY in 2020 (the V-shape).**
  - The 200d rule exited 27 Feb; flipped in and out on 2, 3, 4 and 5 Mar; re-entered 27 May; and switched again on 11, 12, 26 and 29 Jun.
  - 19 Feb–23 Mar 2020: −17.6% vs buy-and-hold −34.1%.
  - 19 Feb–31 Dec 2020: −1.4% vs +10.5%.
  - Source: E3 check
- **SPY whipsaw years** (200d / buy-and-hold, price-only): 2000 −18.9% / −10.0%; 2011 −10.2% / −0.2%; 2015 −9.4% / −0.8%; 2018 −9.8% / −6.3%. Strong years: 2008 0.0% / −38.3%; 2001 0.0% / −13.1%. — E3 check
- **SPY episode table, rule return minus S over each buy-and-hold peak-to-trough** (200d / ens L/F):
  - 2000–02: +15.1 / +13.3 pp
  - 2007–09: +35.1 / +25.4 pp
  - Apr–Jul 2010: −3.2 / −1.6 pp
  - Apr–Oct 2011: +5.9 / +1.2 pp
  - Q4 2018: +0.2 / +5.1 pp
  - Feb–Mar 2020: +7.6 / +10.7 pp
  - Positive in 5 of 6 episodes for both. The largest episode is 55% of the 200d rule's total benefit (fails the 50% concentration cap) and 46% for ens L/F.
  - ens × VS15: 6 of 6 positive, largest share 45%.
  - Source: E3 check
- **SPY ens × VT20 (CARD-P-style metrics), 1999–2021.**
  - Sharpe 0.41 vs S 0.37; max drawdown −27.3% vs S −41.3% (PC-1 +14.1 pp).
  - Tail-exposure ratio 0.51 (PC-2 passes at ≤ 0.90).
  - 6 of 6 episodes positive (largest share 45%); 61% of years positive.
  - 2009–2019 Sharpe 0.69 vs S 0.79.
  - Source: E3 check
- **Mechanism on SPY.** Average 200d exposure was 0.71. On the 92 days when VIX rose 20% or more it was 0.75, so the rule does **not** de-risk on the first day of a volatility spike. It was 0.01 on days after VIX closed above 40, and fully long on only 10% of SPY's 20 worst days (22% of the 50 worst). The worst days cluster *after* the trend has turned. — E3 check (VIX daily file `/home/claude/data_raw/us/vix_daily.csv`)
- **KOSPI proxy, 1996–2026, 5 bp.**
  - Buy-and-hold: Sharpe 0.41, max drawdown −69.8%.
  - ens L/F: Sharpe 0.60, max drawdown −35.3% (S −48.1%); 12.1 turns a year; tail ratio 0.77.
  - 200d L/F: Sharpe 0.54, −42.8%.
  - ens L/S: Sharpe 0.42, −60.1%.
  - 250d L/S: Sharpe 0.24, −74.3%.
  - At 2× cost: ens L/F Sharpe 0.56.
  - Source: E3 check (KRX marcap)
- **KOSPI by sub-period** (ens L/F vs buy-and-hold Sharpe): 1996–2008 0.72 vs 0.26; **2009–2019 0.23 vs 0.49** (200d 0.08, L/S −0.33); 2020–2026 0.77 vs 0.76. Against S: ΔSharpe 2001–2026 +0.04; 2013–2026 +0.01 with PC-1 −3.4 pp. — E3 check
- **KOSPI episodes, buy-and-hold / ens L/F / ens L/S / ens × VS15** (%):
  - 1996–98: −69.8 / −14.3 / +94.1 / −15.4
  - Jul–Oct 1999: −22.4 / −16.0 / −9.4 / −6.5
  - 2000–01: −54.1 / −35.3 / −22.0 / −17.6
  - 2007–08: −54.5 / −14.7 / +48.3 / −9.4
  - May–Sep 2011: −25.7 / −16.2 / −7.1 / −12.2
  - 2018–20: −43.5 / −11.7 / +33.0 / −11.0
  - 2021–22: −34.8 / −12.1 / +15.4 / −12.1
  - **22 Jun–30 Jul 2026: −38.4 / −31.2 / −23.4 / −7.9**
  - Source: E3 check
- **KOSPI: trend vs volatility targeting** (buy-and-hold / ens L/F / VT20 long-only / ens × VT20):
  - 2008: −40.9 / −7.0 / −31.2 / −6.4
  - 2022: −25.0 / −5.9 / −25.0 / −5.9
  - 22 Jun–30 Jul 2026: −38.0 / −30.7 / −12.0 / −9.5
  - H1-2026: +101.1 / +84.2 / +51.5 / +47.2
  - ens × VT20 over 1996–2026: Sharpe 0.65 vs S 0.41; max drawdown −26.7% vs S −43.9%; 8 of 8 episodes beat S (largest share 31%); 2009–2019 Sharpe 0.24 vs S 0.49; 53–55% of years positive (buy-and-hold 69%).
  - Source: E3 check
- **KOSPI200-like top-200 proxy.** ens L/F Sharpe 0.56 vs S 0.41; max drawdown −37.0% vs S −47.0%; 2009–2019 0.16 vs 0.47; 2013–2026 0.56 vs 0.55. — E3 check
- **Companion macro research (internal) for other markets.**
  - An equal-weight vol-scaled 12-index trend book: Sharpe 0.49 (2001–26; 0.60 with 16 assets), correlation with the S&P 0.08.
  - KOSPI long/flat 0.47 vs buy-and-hold 0.52; KOSDAQ ≈ 0.
  - Trend "dead" in Europe, the UK and India since 2013.
  - 2020: −16.7% vs S&P +16.3%.
  - KOSDAQ was fully long into its −39.7% fall (Feb–Jul 2026).
  - Source: project doc `claude/QUANTGEN_MACRO_INTEGRATION.md` §R-14 / N-33 (Projects)
- **QUANTGEN E1 trend switch.**
  - US ETF sleeves: out-of-sample Sharpe 0.84 [0.47, 1.20] vs 0.95; p 0.75; PBO 0.59; 1.6 turns a year; max drawdown −15% vs −27%.
  - KRX ETF sleeves: 0.52 [−0.03, 1.04] vs 0.74; p 0.89; deflated Sharpe (DSR) 0.84.
  - Source: QUANTGEN study record (`00_QUANTGEN_context.md`, study run 2026-09-27)
- **Trend fails in volatility spikes.** In extreme volatility spikes (97th percentile) trend was positive only about 50% of the time, against nearly 90% for long-short quality. SG Trend was +1.1% in March 2020 and −4.2% in the August 2024 yen-carry unwind. — [Man AHL via AIMA, Mar 2025](https://www.aima.org/article/trend-following-and-long-short-quality-loading-the-dice.html)
- **Published timing results are overstated.** Published performance of MA and TSMOM equity-timing rules is highly overstated once data-mining bias and realistic costs are accounted for. — [Zakamulin 2014, JAM (RePEc)](https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html)
- **Shiller averaging bias.**
  - On SPY 1998–2021, the lag-1 autocorrelation of monthly returns is 0.057 from month-end prices but 0.206 from monthly-average prices.
  - Month-end vs month-average Sharpe: 12-month L/S 0.35 vs 0.62; 10-month SMA long/flat 0.70 vs 0.82.
  - On the Shiller series (1872–2026), a one-month skip cuts 12-month L/S from 0.50 to 0.30 and the 10-month SMA from 0.75 to 0.59. In 2009–2026 the skip turns 1.15 (above buy-and-hold's 1.10) into 0.90 (below it).
  - Source: E3 check
- **Shiller annual figures** (no skip, biased; buy-and-hold / 10m SMA / 12m L/S): 2008 −40.7 / 0.0 / +37.4; 2020 +16.3 / −0.7 / −4.7; 2022 −16.3 / −5.2 / −12.1. — E3 check

### Inferences
- **Card class.** Single-index trend should be registered as a protective card (CARD-P). Its value is drawdown reduction *beyond* de-gearing:
  - SPY PC-1 +14.1 pp; KOSPI +12.8 to +17.3 pp.
  - Sharpe parity or better against S over full cycles.
  - It fails the outperformance test whenever the out-of-sample window is dominated by 2009–2019-style markets. This explains E1, and predicts the KRX version's result.
- **Two crash types.** Trend protects against *slow* bear markets (2000–02, 2008, 2022). VT20 protects against *fast* crashes from high-volatility states (Jun–Jul 2026). Their product beats each alone on drawdown and episode coverage. This is the strongest argument for a "trend × VT20" card.
- **Decision rule.** Long/flat beats long/short on single equity indices. The short leg loses in V-recoveries (KOSPI L/S 2009–2019 Sharpe −0.33), consistent with HLWZ's finding that profits come from long legs.
- **Data hygiene.** Any data-lab trend test on Shiller monthly averages must use a skip month or month-end prices. Otherwise trend Sharpe is overstated by about 0.15–0.25.
- **Japan.** No local data (see Gaps). The macro research's prior is 1–2.

### Gaps
- **Nikkei 225 / TOPIX:** no local daily data and no fetched single-index study, so no Japan-specific numbers.
- **KOSPI200 index:** official history not used. The proxy is a cap-weighted KOSPI (or top-200), not the free-float KOSPI200, and is price-only.
- **SPY coverage:** the local file ends 31 Mar 2021, so SPY 2022 and 2025–26 are covered only through Shiller averages (biased).
- **Trends Everywhere:** per-asset Sharpe for KOSPI 200 is shown only in a figure and could not be extracted.

---

## 4. Practice: universe, risk allocation, signals and exits, costs and roll, capacity, fees, realistic net statistics

### Takeaway
- **What a professional trend book looks like:**
  - 50–150+ liquid futures across four asset classes;
  - equal risk per position;
  - a portfolio volatility target of about 10%;
  - multi-speed signals (MA crossovers and TSMOM are one family);
  - continuous signals and range-based volatility to save turnover;
  - signal exits instead of stop-losses;
  - costs of roughly 1–4% a year including roll.
- **Realistic expectations:** a live net Sharpe of about 0.5 long-run (about 0.3 or less in bad decades), and a drawdown of 20% or more that is likely within 25 years.

### Cited Findings
- **Universe size.** Research universes run from 56–67 markets (BK, HOP) to 156 (Trends Everywhere). Adding 82 alternative markets lifts the combined Sharpe from 1.17 to 1.60 gross. — [Trends Everywhere](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/fd3c53f7-c472-4898-a7e1-f6c100b1b81e.pdf); [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- **Risk allocation.**
  - Positions are sized to equal ex-ante volatility (40% per asset in MOP; 10% portfolio in HOP).
  - BK's correlation factor CF = √(N / (1 + (N−1)ρ̄)) de-levers when signed correlations rise. It added +0.16 Sharpe gross in 2009–2013 but raises turnover 23% unless combined with Yang–Zhang volatility and the TREND rule.
  - Source: [MOP 2012](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf); [BK](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf)
- **Signals.** Crossovers and TSMOM are equivalent families (R² above 80%); the 12-month signal had the highest gross Sharpe in 1985–2015 (1.45). — [LP 2016](https://research-api.cbs.dk/ws/portalfiles/portal/60084063/lasse_heje_pedersen_et_al_which_trend_is_your_friend_publishersversion.pdf)
- **Donchian channels in crypto.** An ensemble of Donchian-channel models with volatility sizing on a rotating top-20 crypto basket reports a net Sharpe above 1.5 and 10.8% a year alpha over bitcoin. — [Zarattini–Pagani–Barbon 2025, SSRN 5209907](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5209907)
- **Stops vs signal exits.** Stop-loss rules reduce expected return under a random walk and add value only when returns are serially correlated: 50–100 bp per month during stop-out periods for US stocks against long bonds, 1950–2004. — [Kaminski–Lo, SSRN 968338](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=968338)
- **Costs and roll.**
  - HOP's one-way costs for 2003–2013: equities 0.06%, bonds 0.01%, commodities 0.10%, FX 0.03% — [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
  - BK's two-part model (roll costs on gross exposure plus rebalancing costs on turnover): 163 bp a year default, 105 bp with Yang–Zhang + TREND — [BK](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf)
- **Fees.** 2/20 averages about 6% a year on a 10%-volatility TSMOM; costs add 1–4% a year; index net Sharpe 0.27–0.88 (1985–2012) — [HOP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/DemystifyingManagedFutures.pdf). A recent liquid-alternative example: an ETF's gross expense ratio of 0.75% (T3, fund marketing) — [Simplify CTA flyer 1Q26](https://www.simplify.us/sites/default/files/etf/2026-04/Simplify%20CTA%20Flyer%201Q26.pdf)
- **Capacity.** Estimated systematic-trend positions in 2014 were about 0.2% of equity markets, 2% of bond, 6% of commodity and 0.4% of FX markets. — [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- **Realistic net Sharpe and drawdown.**
  - SG CTA Sharpe 0.61 over 2000–2022; individual CTAs about 0.5 — [CFM 2022](https://www.cfm.com/wp-content/uploads/2022/12/39-A-Good-Time-for-Trend-Following-FINAL.pdf)
  - About an 80% chance of a drawdown of 20% or more in 25 years at Sharpe 0.5 and 10% volatility; SG Trend's worst rolling 12-month loss was −18.6% (Apr 2025) — [Man 2025](https://www.man.com/insights/is-this-time-different)
  - Simulated century-long worst drawdown −26.3% — [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- **Implied lookback mix.** Managers' implied weights put the most on 3-month signals (54%), reflecting transaction-cost optimisation toward slower-decaying signals. — [HOP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/DemystifyingManagedFutures.pdf)
- **Faster programs in 2025.** Short-term programs (holding under 10 days) were almost flat year-to-date to 13 Apr 2025 (−0.9%) while SG Trend lost −9.3%. — [SG May 2025](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025)
- **Carry as a separate premium.** Carry is measured from the futures curve (commodities: slope between two maturities; equity index: dividend yield minus the rate). It is a separate return source from trend and is recession-exposed. — [KMPV, NBER w19325](https://www.nber.org/system/files/working_papers/w19325/w19325.pdf)

### Inferences
- **Persona view (desk practice).** Continuous futures are where naive backtests lie.
  - Build signals on ratio-back-adjusted series or on the underlying index, and book P&L on the actual front contract, with roll costs and dates explicit.
  - The KOSPI200 December contract carries the dividend points (QUANTGEN's own monitor notes this basis gap), so an unadjusted continuous KOSPI200 futures series shows a fake December jump that a trend signal will trade.
  - At 4 rolls a year × 2 sides × 5 bp × an average exposure of about 0.5, KOSPI200 roll costs about 20 bp a year. That is immaterial to Sharpe; KOSPI ens L/F moved from 0.60 to 0.56 at 2× cost.
- **No separate stop layer.** Signal exits (vote share, hysteresis) are the stop. A separate stop layer double-counts the same serial-correlation bet (Kaminski–Lo) and adds parameters that count as trials.
- **Breadth.** A 10-market book cannot reproduce industry Sharpe ratios. With single-asset Sharpe s ≈ 0.35 and average correlation ρ̄, portfolio Sharpe ≈ s·√(N/(1+(N−1)ρ̄)): about 0.8 at N = 10 and ρ̄ = 0.1, but much lower post-2008 when ρ̄ rose and s fell. This is arithmetic, not a fitted estimate.

### Gaps
- **Market counts at real CTAs** (e.g., hundreds of markets at the largest programs): no fetched source.
- **Turtle/Donchian rules on traditional futures:** no fetched head-to-head study against EWMA crossovers; LP's equivalence result is the closest evidence.
- **KRX execution:** no fetched data on KOSPI200 futures bid-ask, roll spreads or market impact. QUANTGEN's pre-registered 5 bp per side is used as given.

---

## 5. Crypto trend: why QUANTGEN's C3 passed and what supports crypto TSMOM

### Takeaway
- **The evidence.** Crypto shows documented short-horizon (1–4 week) time-series momentum. Long/flat trend avoided most of bitcoin's and ether's −75% to −94% bear markets, and its edge over buy-and-hold is **not** reproduced by volatility scaling alone.
- **Caveats:**
  - The benchmark is a bull decade.
  - The edge shrank in 2022–2026.
  - 2025 was a whipsaw year in which the rule lagged buy-and-hold.
  - Most of the drawdown reduction comes from lower average exposure rather than from timing.

### Cited Findings
- **QUANTGEN C3 card.**
  - Rule: long/flat on KRW-BTC; sign votes over 7–28-day lookbacks plus price/moving-average ratios, with a hysteresis band; 10 bp per side.
  - Out-of-sample Sharpe 1.22 [0.62, 1.77] vs buy-and-hold 0.79; p 0.04; DSR 1.00; PBO 0.27 with the winner losing in 0% of splits; 1.17 at 2× costs; 13.7 turns a year.
  - 75% of years positive; the largest year carries 29% of P&L.
  - BTC-USD: 1.19 [0.72, 1.64] vs 0.89; p 0.07; 10.0 turns a year.
  - Expected live Sharpe after the 40% haircut: 0.73, below buy-and-hold's 0.79. The app itself notes that the KRW-BTC benchmark is a bull decade.
  - Source: QUANTGEN study record and public page text (`00_QUANTGEN_context.md`)
- **Liu–Tsyvinski (bitcoin 2011–May 2018).**
  - A one-SD rise in today's return predicts +0.33% the next day; a one-SD rise in this week's return predicts +3.16% next week.
  - Top-quintile weekly return 11.22% (Sharpe 0.45) vs bottom quintile 2.60% (0.19).
  - Attention (Google searches, Twitter) predicts returns.
  - Exposure to stock, FX, commodity and macro factors is mostly insignificant.
  - Source: [NBER w24877 (RFS 2021)](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf)
- **Liu–Tsyvinski–Wu (2014–2018; 109 to 1,583 coins).** Cross-sectional 3-week momentum earns 4.1% a week (t 2.74). It is significant only in above-median-size coins (4.2% a week vs an insignificant 0.6%). — [NBER w25882 (JF 2022)](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf)
- **Zarattini–Pagani–Barbon 2025.** Donchian ensemble on the top-20 liquid coins (survivorship-free since 2015): net Sharpe above 1.5, alpha 10.8% a year over BTC. — [SSRN 5209907](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5209907)
- **E3 replication (C3-like rule).**
  - Rule: 8 votes (sign of the 7/14/21/28-day return and of price/MA); enter at a score of +0.25 or more, exit at −0.25 or less; 10 bp.
  - Data: Coin Metrics daily PriceUSD, BTC to 23 May 2026.
  - BTC 2017-10 to 2026-05: Sharpe 1.19 vs buy-and-hold 0.83; max drawdown −53.1% vs −83.8%; average exposure 0.53.
  - 2020–2026: 1.16 vs 0.92.
  - **2022–2026: 0.61 vs 0.48** (max drawdown −36.3% vs −66.9%).
  - Full 2011–2026: 1.72 vs 1.32.
  - 20 bp cost: 1.67.
  - Calendar years (rule / buy-and-hold): 2014 +9% / −56%; 2018 −33% / −74%; 2022 −31% / −64%; **2025 −11% / −6%**; 2026 year-to-date to 23 May about 0% / −12%.
  - Best year 25% of positive log-P&L; 75% of years positive.
  - Excluding 2018 and 2022: Sharpe 1.96 vs 1.64.
  - Source: E3 check; data [Coin Metrics community btc.csv](https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv)
- **Volatility-scaling control (Kim–Tse–Wald style).** A vol-scaled long-only BTC book with matched exposure earns Sharpe 0.83 (2017-10 onward; max drawdown −51%), the same as buy-and-hold. The C3-like rule earns 1.19, and C3 × vol scaling 1.24 (max drawdown −39%). For ETH (2017-10 onward): vol-scaled long-only 0.71 vs C3-like 1.12. — E3 check
- **Static-exposure comparator.** Against S (buy-and-hold × 0.53), the BTC drawdown improvement is only −53.1% vs −58.1% (2017–2026) and −36.3% vs −41.0% (2022–2026). On ETH in 2022–2026 the rule's drawdown (−46.3%) was **worse** than S (−42.8%). — E3 check
- **ETH as an out-of-asset replication** (2016–May 2026): C3-like Sharpe 1.52 vs buy-and-hold 1.08; max drawdown −61.2% vs −94.0%. 2022–2026: 0.40 vs 0.17. 2025: +26% vs −11%. 2026 year-to-date: −13% vs −29%. — E3 check; data [Coin Metrics eth.csv](https://raw.githubusercontent.com/coinmetrics/data/master/csv/eth.csv)
- **Bitcoin in 2026.** It has fallen since January 2026, which helped trend followers holding it short. — [TTU Aug 2026](https://www.toptradersunplugged.com/trend-following-performance-report-august-2026/)
- **Macro research on crypto.** It prohibited a net-liquidity crypto rule (−0.20 Sharpe in 2023–26) and kept crypto at own-trend plus a volatility cap. — project doc `claude/QUANTGEN_MACRO_INTEGRATION.md`

### Inferences
- **Why C3 passes where futures fail:**
  1. Crypto's short-horizon autocorrelation is still large (Liu–Tsyvinski), whereas short trends in traditional futures have withered (Lempérière).
  2. A single high-volatility asset makes a long/flat timing rule's benefit large relative to costs. 13.7 turns a year × 10 bp is about 1.4–2.7% a year against a 60–85% volatility asset.
  3. Buy-and-hold's −77% to −84% drawdowns make it beatable on Sharpe even in a bull decade.
  4. The test is against buy-and-hold of the *same* asset, which a long/flat rule can beat by avoiding its bear markets. B3 had to beat a passive basket with a long/short book.
- **Caveat on the turnover gap.** C3's out-of-sample record shares the bull-decade benchmark caveat. The edge is concentrated in avoiding 2014, 2018 and 2022. E3's turnover count (about 29 a year, counting |Δw|) is double QUANTGEN's 13.7, presumably because QUANTGEN counts round trips; this needs confirming.
- **Expected live Sharpe** is about 0.6–0.7 for BTC (C3's haircut gives 0.73), with a realistic chance of lagging buy-and-hold in strong up-years or chop (2025).

### Gaps
- **Data end date.** The Coin Metrics community file ends 23 May 2026, so the June–September 2026 crypto path is not tested. Live exchange APIs (Upbit, Binance, CoinGecko, Yahoo) were blocked by the egress proxy (403).
- **No practitioner fund record** for crypto trend programs was retrieved, and no peer-reviewed *time-series* crypto trend paper beyond Liu–Tsyvinski. The Liu–Tsyvinski–Wu result is cross-sectional.

---

## 6. QUANTGEN translation: why B3 failed and C3 passed; card class; defensible grid; per-market priors; card specifications

### Takeaway
- **B3** was rejected because it asked a ten-market long/short trend book to beat a long-only basket in 2009–2026, under a nine-step gate whose power at Sharpe 0.3–0.4 is close to zero. The record rejects *that claim*, not trend as a family.
- **What QUANTGEN should build:**
  - **Equity indices:** protective trend × VT20 cards (CARD-P), one per index.
  - **Futures:** a re-registered diversified futures card with a diversifier claim and at least 25 markets.
  - **Crypto:** keep C3, with stronger controls.
  - **Weights:** separate per-market *alpha* weights from *protection* weights.

### Cited Findings
- **B3 card.**
  - Ten continuous futures: out-of-sample Sharpe 0.08 [−0.27, 0.43]; DSR 0.27; PBO 0.10 with the winner losing in 7% of splits.
  - Benchmark Sharpe 0.58; p 0.97; 0.06 at 2× costs; 3.3 turns a year.
  - Verdict: REJECT, "no measurable edge after 2009".
  - Source: QUANTGEN study record (`00_QUANTGEN_context.md`)
- **Industry and academic record after 2009.**
  - Net industry: Barclay Systematic 2009–2025 annual mean/SD 0.30, 9/17 years positive; 2009–2018 CAGR −0.30% — [BarclayHedge Systematic](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index) (E3 arithmetic)
  - Academic: 2009–2013 TSMOM Sharpe 0.01 gross, −0.09 net — [BK](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf)
- **CARD-P protective class** (pre-registered in the macro spec):
  - PC-1: drawdown reduction of at least 3 pp versus S at 1× and 2× costs.
  - PC-2: tail-exposure ratio ≤ 0.90.
  - PC-3: Sharpe non-inferiority versus S with margin δ = 0.10.
  - PC-4: at least 3 positive episodes, none above 50% of the total benefit.
  - PC-5: at least 60% of years positive.
  - PC-6: plateau.
  - PC-7: data sufficiency.
  - Source: project doc `claude/QUANTGEN_MACRO_INTEGRATION.md` §8.7
- **R-14 in the macro spec.** The trend sleeve is a 12-1-month sign, rebalanced monthly, with weight min(1, 0.15/σ12m), registered as CARD-O against an equal-weight long-only basket. The spec itself warns that the result will repeat E1 unless the diversification claim is registered. — project doc §R-14
- **Statistical power (E3 arithmetic, iid approximation).** SE(Sharpe) ≈ 1/√T.
  - T = 17 years: SE ≈ 0.24; Sharpe detectable at one-sided 5% with 80% power ≈ 0.60; 90% interval half-width ≈ 0.40.
  - T = 25 years: 0.20, 0.50 and 0.33.
- **Multi-speed vs 12-month only on KOSPI.** In E3's grid, the 12-month-only rule was the weakest cell (full-sample ΔSharpe vs S +0.04; 2009–2019 −0.42). The 20/60 set was the strongest (+0.26; −0.16). — E3 check
- **KOSPI grid (E3 check).**
  - 5 lookback sets (20/60/120/250; 60/120/250; 120/250; 250; 20/60) × 4 volatility settings (none; VT 15%, 20% and 25%, using SMA20, cap 1).
  - All 20 cells: full-sample ΔSharpe vs S between +0.04 and +0.26, and PC-1 between +6.5 and +17.3 pp.
  - All 20 cells negative in 2009–2019 (−0.16 to −0.42).
  - 2013–2026: −0.06 to +0.20.
  - Years positive: 45–62%, against buy-and-hold's 69%.
- **Long/half variants** (exposure in [0.5, 1]):
  - KOSPI 0.5 + 0.5 × votes: PC-1 +12.5 pp, tail ratio 0.92 (fails PC-2), 5/8 episodes.
  - KOSPI with VT20 and a 0.5 floor: PC-1 +8.1 pp, tail ratio 0.79, 8/8 episodes (largest share 19%), 63% of years positive.
  - SPY long/half: PC-1 +11.2 pp, tail ratio 0.82, 65% of years positive.
  - Source: E3 check

### Inferences
**A. Why B3 failed (ranked by E3's judgement of importance).**
1. **The wrong claim and benchmark.** A long/short diversifier was required to beat a long-only basket (Sharpe 0.58) on the same days in a QE bull market. Even a good CTA does not do that; its value is low correlation and positive convexity.
2. **Power.** About 17 years out of sample cannot separate Sharpe 0.3 from 0. B3's interval [−0.27, 0.43] contains the realistic net industry level (0.30).
3. **Breadth.** Ten markets give perhaps a third to half of a 50-market book's Sharpe.
4. **Regime.** 2009–2019 was the trend drought; B3's verdict matches the industry's.
5. **Multiple testing.** DSR 0.27 means the configurations tried were not counted cheaply. The likely pattern is walk-forward selection of lookbacks (speed-chasing).
6. **Possible data artefacts.** Unadjusted front-month "continuous" futures can contain roll gaps. This needs checking (DC-1).

Costs are *not* the reason: 3.3 turns a year × 5 bp ≈ 0.17% a year.

**B. Card classes.**
- **Single-asset long/flat equity-index trend → CARD-P.** Comparator S, PC-1 to PC-7. It is functionally a de-risking rule.
- **Diversified long/short futures trend → a "diversifier" variant of CARD-O.** Claims:
  - (i) a net Sharpe above 0 versus cash (step 2 interval clears zero);
  - (ii) correlation with the reference equity book ≤ 0.2;
  - (iii) a positive mean in the worst-decile equity months;
  - (iv) adding 20% to the reference book raises its Sharpe, one-sided p ≤ 0.10. This replaces the long-only benchmark test in step 5.

  This is a **new card** under QUANTGEN's rules (a changed claim counts as a trial). E3 flags that it needs the coordinator's or gate owner's approval as a class.
- **Crypto long/flat → keep CARD-O (C3).** Add CARD-P metrics to the card for information.

**C. Defensible parameter grid** (fixed before the test; every cell counted in DSR; the registered *centre* is the equal-weight ensemble, never the in-sample best):
- **Lookbacks (trading days):** {20/60, 20/60/120/250 (centre), 60/120/250, 120/250}. An EWMA crossover set (16/64, 32/128, 64/256) may be registered *as the same family* under Levine–Pedersen, not as a new card.
- **Volatility:** {none, 15%, **20% (centre, SMA20 = R-06)**, 25%}, cap 1.0. For diversified futures, per-asset EWMA-60 to equal risk, a 10% portfolio target and an optional correlation-factor overlay.
- **Signal mapping:** {long/flat vote share (centre for equity indices), long/half floor 0.5, signed votes (centre for diversified futures)}.
- **Trading:** decide daily at the close; no-trade band of |Δw| < 0.10 (or C3-style hysteresis); costs 5 bp per side plus explicit roll for futures, 3 bp for KRX ETFs, 10 bp for crypto; a 2× rerun.
- **Plateau check (PC-6 / step 7):** one step on each axis around the centre.

**D. Per-market priors for TS trend, on QUANTGEN's 0–3 scale** (E3 opinion from the evidence above). Alpha weight is for an outperformance claim; protection weight is for a CARD-P sleeve.

| Market | Alpha weight | Protection weight | Evidence status / comment |
|---|---|---|---|
| US (S&P 500) | 1 | 3 | SPY 1999–2021: 5–6 of 6 episodes vs S; PC-1 +14 pp; Sharpe ≈ parity |
| Korea KOSPI / KOSPI200 | 1 | 2 | 8/8 episodes with VT20; failed alone in Jun–Jul 2026; 2009–19 negative; years-positive risk |
| Korea KOSDAQ | 0 | 1 | Macro research: ≈ 0; fully long into the 2026 −39.7% fall |
| Japan | 1 | 2 (untested) | No local test; macro research prior 1–2 |
| Europe | 0–1 | 1–2 (untested) | Macro research: trend "dead" since 2013 in Europe and the UK |
| Crypto (BTC) | 2–3 | 2 | C3 PASS; replicated on ETH; edge smaller in 2022–26 |
| FX (G10, USD/KRW) | 0–1 | 1 | QUANTGEN V3 FX momentum −0.59 (REJECT) |
| Rates futures (KTB, UST) | 1–2 | 2 | Long-history evidence (HOP, MOP); 2022; untested in QUANTGEN |
| Commodities | 1–2 | 2 | Highest MOP t-stat (4.66); data quality is QUANTGEN's binding constraint |
| Diversified (≥ 25 markets) | 1–2 (net Sharpe 0.3–0.5) | 3 as a diversifier | Industry 2000–2026 |

**E. Card specifications E3 would register.**
- **T-K1, "KOSPI200 trend × VT20" (CARD-P).**
  - Signal on the KRX KOSPI200 index; P&L on the front KOSPI200 future, with an alternative KODEX 200 book declared in advance.
  - w = min(1, 0.20/σ20) × (share of positive 20/60/120/250-day returns).
  - A long/half cell with a 0.5 floor is pre-registered.
  - Episodes: 1997–98, 2000–01, 2008, 2011, 2018–20, 2021–22, Jun–Jul 2026.
  - Expected: PC-1 to PC-4 likely pass. The long/flat cell is at risk on PC-5 (53–55% of years), which would mean REVISE (extend history using the KRX index back to 1990); the long/half cell is likely to pass. The 2009–19 cost is about −0.25 Sharpe versus S.
- **T-US1 / T-JP1 / T-EU1:** the same rule per index, as separate cards.
- **T-F1, "diversified futures trend" (re-registration of B3).**
  - Universe: at least 25 back-adjusted markets. KIS provides KOSPI200, KTB 3y/10y and USD/KRW; global equity, rate, FX and commodity futures need a proper back-adjusted source.
  - Signed multi-speed votes; equal risk per asset; 10% portfolio volatility; weekly decision with a band.
  - Diversifier claim (B above).
  - Expected net Sharpe 0.3–0.5 over 2000–2026, about 0 in 2009–2019. **INSUFFICIENT DATA or REVISE is the honest base case.**
- **C3 (keep).** Add:
  - the vol-scaled long-only control;
  - a slow 50/100/200 sleeve as a plateau/robustness line (2022–26 BTC Sharpe 0.80 vs C3-like 0.61, E3 check);
  - ETH as an out-of-asset replication;
  - a sub-period table;
  - the forward record from registration.

**F. Conflicts with the macro research (flagged, not re-litigated).**
1. **R-14's 12-1-month monthly sign** is the slowest and weakest cell in E3's KOSPI grid. Its monthly rebalance would miss fast turns. E3 proposes a multi-speed ensemble decided daily with a band.
2. **R-14 registered as CARD-O against a long-only basket** repeats E1. E3 recommends CARD-P for single-index sleeves and a diversifier claim for multi-asset trend.
3. **P2 bounds.** If a trend switch is classed as an *overlay*, exposure would be held to [0.5, 1.0], giving about half the protection (KOSPI PC-1 +8.1 pp vs +17.3 pp long/flat). If it is a *signal*, it may reach 0. E3 asks the coordinator to classify; E3 reads trend as a signal family, so 0 is allowed.
4. **Prior design's "0.4–0.8 per asset, ~1.0 diversified".** Correct to about 0.3–0.4 gross per asset (Trends Everywhere median 0.34–0.39) and about 1.0+ gross for a backtested diversified book, but 0.3–0.6 live net.
5. **Vol scaling.** E3 agrees with the macro finding that vol scaling adds little Sharpe on its own (KOSPI VT20 long-only 0.40 vs S 0.41). It is complementary to trend for protection, and it is a necessary control for any trend Sharpe claim (Kim–Tse–Wald).

### Gaps
- **B3's internals.** Its exact markets, continuous-contract construction, lookbacks searched and out-of-sample start date are not documented in the brief.
- **Diversifier-claim power.** No computation of how often a diversifier claim would pass at T ≈ 17–26 years; this needs the data lab's bootstrap.
- **Gate rules.** Whether QUANTGEN's gate permits a "diversifier" claim class is a governance question E3 cannot settle.

---

## 7. Where and when it failed (mandatory): dated episodes with numbers

### Takeaway
- **Industry.** Trend fails in four repeatable situations:
  - long, low-volatility, QE-supported bull markets with correlated assets (2009–2019);
  - V-shaped shocks and policy reversals (Feb–Mar 2020; Aug 2024; Apr 2025);
  - give-backs after big trend years (Q4 2022);
  - fast crashes out of strong uptrends (KOSPI Jun–Jul 2026).
- **Single-index equity trend** also loses in choppy years (SPY 2000, 2011, 2015, 2018; KOSPI 2011, 2024).

### Cited Findings
- **1937–38 recession:** trend −6.8% while 60/40 lost −26.1%, one of only 2 failures in the 10 largest 60/40 drawdowns. Worst simulated trend drawdowns: −26.3% (Aug 1947–Dec 1948, 29 months to recover) and −25.3% (Feb 1937–Jun 1940). — [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- **2009–2013:**
  - SG Trend −1.8% cumulative — [Man 2025](https://www.man.com/insights/is-this-time-different)
  - Diversified TSMOM Sharpe 0.01 gross / −0.09 net — [BK](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf)
  - Barclay Systematic 2009 −3.38%, 2011 −3.83%, 2012 −3.20%, 2013 −1.10% — [BarclayHedge](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index)
- **2015–2018:**
  - Barclay Systematic −2.92%, −1.78%, +0.53%, −4.31% — [BarclayHedge](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index)
  - SG Trend rolling 12-month −16.0% to Jan 2019 — [Man 2025](https://www.man.com/insights/is-this-time-different)
- **Feb–Dec 2020 (V-shape):**
  - SPY 200d switch −1.4% vs buy-and-hold +10.5% (19 Feb–31 Dec), after −17.6% vs −34.1% in the crash — E3 check
  - The macro research's 12-index trend book: −16.7% vs S&P +16.3% in 2020 — project doc §R-14
  - SG Trend only +1.1% in March 2020 — [Man/AIMA](https://www.aima.org/article/trend-following-and-long-short-quality-loading-the-dice.html)
- **Q4 2022 give-back:** SG Trend +36% year-to-date to September ([AQR](https://www.aqr.com/Insights/Research/White-Papers/Trend-Following-Why-Now-A-Macro-Perspective)) vs +27.3% for the full year ([Hedgeweek](https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/)), an implied Q4 of about −6.4% (inference).
- **2023:** SG Trend −4.16%, BTOP50 −1.70% — [TTU Dec 2023](https://www.toptradersunplugged.com/trend-following-performance-report-december-2023/). SG lists SVB (March 2023) among the episodes when its trend model's 6-month correlation with the index fell below 0.6 — [SG May 2025](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025)
- **August 2024 yen-carry unwind:** SG Trend −4.2% — [Man/AIMA](https://www.aima.org/article/trend-following-and-long-short-quality-loading-the-dice.html); dispersion spike that month — [CFM](https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/)
- **April 2025 tariff shock:**
  - SG Trend −4.9% in April (as reported), −9.3% year-to-date to 13 Apr — [SG](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025)
  - Rolling 12 months −18.6% to 30 Apr, the worst in index history. Man attributes it to sharp reversals around 2 Apr and the 9 Apr 90-day pause. — [Man 2025](https://www.man.com/insights/is-this-time-different)
- **Calendar 2025:** SG CTA −0.2% ([Aussie Turtles](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/)) vs S&P 500 TR +17.89% ([TTU](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/)).
- **KOSPI, 22 Jun–30 Jul 2026:** buy-and-hold −38.0%; multi-speed trend L/F −30.7%; 200d −37.2%. Trend was fully long into the crash; only VT20 protected (−12.0%; trend × VT20 −9.5%). — E3 check
- **KOSPI 2009–2019 whipsaw decade:** ens L/F Sharpe 0.23 vs 0.49; 200d 0.08; L/S −0.33. Also 2011 (ens L/F −16.3% vs −10.7%) and 2024 (−13.5% vs −9.8%). — E3 check
- **SPY choppy years** (200d vs buy-and-hold): 2000 −18.9% vs −10.0%; 2011 −10.2% vs −0.2%; 2015 −9.4% vs −0.8%; 2018 −9.8% vs −6.3%. — E3 check
- **Crypto 2025:** C3-like BTC −11% vs buy-and-hold −6% (whipsaw). On ETH in 2022–2026 the drawdown was worse than the static comparator (−46.3% vs −42.8%). — E3 check
- **QUANTGEN B3:** out-of-sample Sharpe 0.08 [−0.27, 0.43]; p 0.97 against a 0.58 benchmark. **E1:** Sharpe 0.84 vs 0.95, p 0.75. — QUANTGEN record

### Inferences
- **Pre-registration.** Every trend card should carry these episodes in its header. A protective card should report its premium: the share of years lagging S was 52% for KOSPI ens L/F and 59–73% for the SPY rules (E3 check).
- **Persona view.** A trend program's "failure" usually means a year of −5% to −15% while equities rise 15–30%. Investors fire managers over the opportunity cost, not the loss. For QUANTGEN's users the display should frame trend as insurance, with the premium visible.

### Gaps
- **SG daily index series:** the exact peak-to-trough drawdown dates of the SG Trend Index in 2009–2013, 2016–2019 and 2023–2025 were not retrieved.

---

## Data-check requests for the data lab (exact tests)

- **DC-1. Re-run B3 with diagnostics.**
  - (a) Print each of the ten series' construction (front-month unadjusted vs ratio back-adjusted), the roll dates, and the share of P&L earned on roll days.
  - (b) Rebuild on ratio-back-adjusted series and rerun the identical walk-forward.
  - (c) Report out-of-sample Sharpe by sub-period: 2003–08, 2009–19, 2020–26.
  - (d) List the configuration the walk-forward picked in each window, and compare with a *fixed* equal-weight 20/60/120/250 ensemble (selection penalty).
  - (e) Report correlation with the long-only basket and the mean return in the basket's worst-decile months.
- **DC-2. Re-gate E1 (US and KRX ETF sleeves) as CARD-P.** Use comparator S = buy-and-hold × E1's average exposure. Report PC-1 to PC-7 and the episode table (US: 2000–02, 2007–09, 2010, 2011, Q4 2018, Feb–Mar 2020, 2022). Expectation from E3's SPY check: PC-1 ≈ +13–14 pp.
- **DC-3. KOSPI trend × VT20 (T-K1).**
  - Data: the KRX all-stock marcap files, or the official KOSPI200 back to 1990 if available.
  - Rule: w = min(1, 0.20/σ20) × the share of positive 20/60/120/250-day returns.
  - Settings: purged walk-forward 756/126; costs 5/10 bp (futures) and 3/6 bp (KODEX 200); cells {long/flat, long/half floor 0.5}.
  - Report: PC-1 to PC-7, yearly table, 2009–2019 sub-period, the 22 Jun–30 Jul 2026 window. E3's in-sample values: Sharpe 0.65 vs S 0.41; max drawdown −26.7% vs −43.9%; 8/8 episodes; 53–55% of years positive.
- **DC-4. Shiller averaging bias.**
  - On the SPY/Shiller overlap (1998–2021), compute the lag-1 autocorrelation of monthly returns from month-average vs month-end prices (E3: 0.206 vs 0.057).
  - Rerun every Shiller-based trend statistic with a one-month skip.
  - Do not publish trend Sharpe from monthly averages.
- **DC-5. C3 controls.**
  - (a) A vol-scaled long-only BTC book at matched exposure.
  - (b) Sub-period Sharpe 2018–21 vs 2022–26.
  - (c) Costs at 20 and 40 bp.
  - (d) ETH as an out-of-asset replication.
  - (e) Calendar 2025 and 2026 year-to-date versus buy-and-hold.
  - (f) Confirm how turnover is counted (round trips vs |Δw|).
- **DC-6. VIX conditioning.**
  - SPY trend exposure on VIX +20% days versus all days (E3: 0.75 vs 0.71).
  - VT20 exposure on the same days.
  - Expected result: trend does not de-risk on spike day 1; the vol target does.
- **DC-7. KOSDAQ.** Build a cap-weighted KOSDAQ proxy from marcap and run the T-K1 test. Expect ≈ 0 (per the macro research). Report the Feb–Jul 2026 window.
- **DC-8. Positive-years test on industry indices.** Share of positive calendar years for Barclay Systematic and Barclay CTA in 2000–2008 vs 2009–2025 (E3: 9/9 vs 9/17), and for any SG annual series the lab can obtain. This documents the structural tension between positively skewed trend returns and step 8 / PC-5.
- **DC-9. French data (1926–2018).** A US market long/flat 10-month trend on month-end (Mkt-RF + RF) total returns, without monthly averaging. Report the episode table against S for the 1929–32, 1937–38, 1973–74, 1987, 2000–02 and 2007–09 drawdowns.
- **DC-10. KOSPI200 futures roll.** Measure the December dividend-point basis jump in a naive continuous KOSPI200 futures series. Confirm T-K1's signal uses the spot index (or a back-adjusted series), and that P&L includes 4 rolls a year × 5 bp per side.
- **DC-11. Grid plateau (PC-6).** Rerun E3's 20-cell KOSPI grid (5 lookback sets × VT {none, 0.15, 0.20, 0.25}) out of sample. Report the share of neighbours keeping at least half the centre's PC-1 improvement and its PC-3 point estimate.

---

## Claims ledger (E3)

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| E3-C01 | Diversified TSMOM has a 130-year simulated record with a net Sharpe of about 0.77. | 67 markets, 1/3/12-month signals, 10% vol, 2/20 fees plus period costs; 1880–2013 gross 14.9%, net 11.2%, vol 9.7%; 2000–13 net Sharpe 0.62; correlation with equities 0.00. | [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf); [HOP 2017](https://fairmodel.econ.yale.edu/ec439/hurst.pdf) | T2 (white paper) / T1 (JPM) | Pre-1985 is out of sample relative to MOP; simulated, not live; costs estimated. | Worst drawdowns −26.3% (1947–48) and −25.3% (1937–40); 1937 recession −6.8%. | CONTEXT: a prior for a 50+-market book only. |
| E3-C02 | In 1985–2009 every one of 58 liquid futures showed positive 12-month TSMOM. | 52/58 significant; diversified gross Sharpe above 1; alpha 1.58%/month (t 7.99); smile coefficient 1.99 (t 3.88); in-sample, gross. | [MOP 2012](https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf) | T1 | Widely replicated; decayed after 2009. | 2009–2019 (C08). | CONTEXT. |
| E3-C03 | Single-asset trend is weak; diversified Sharpe is a breadth effect. | Median single-asset gross Sharpe 0.34–0.39 vs 1.17 (58 traditional assets), 1.34 (82 alternative, incl. KOSPI 200) and 1.60 (all 156); 1985–2017; gross. | [Trends Everywhere](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/fd3c53f7-c472-4898-a7e1-f6c100b1b81e.pdf) | T1 (journal working paper) | Gross of costs; 12-month signal. | — | BUILD: single-index trend cards must not claim alpha; correct the prior to ≈ 0.3–0.4 gross per asset. |
| E3-C04 | Asset-level TSMOM significance is fragile. | 8/55 assets significant at 10%; out-of-sample R² < 0 for 45/55; pooled t 4.34 < bootstrap critical values 4.83 (pairs) and 12.53 (wild); TSH ≈ TSMOM (p 0.19); unscaled t 1.68; 1985–2015. | [HLWZ](https://down.aefweb.net/WorkingPapers/w717.pdf); [RePEc](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html) | T1 | Peer-reviewed critique; disputed by MOP's authors (not fetched). | — | CONTEXT: require portfolio-level claims; print TSH and vol-scaled controls. |
| E3-C05 | Volatility scaling drives much of TSMOM's measured alpha. | Monthly alpha: scaled TSMOM 1.08%, unscaled TSMOM 0.39%, unscaled buy-and-hold 0.40%, scaled buy-and-hold 0.73%; 55 futures, 1985–2009; gross. | [KTW 2016](https://www.sciencedirect.com/science/article/abs/pii/S1386418116301379) | T1 | Consistent with HLWZ. | — | BUILD: every trend card prints a vol-scaled long-only control at the same exposure. |
| E3-C06 | Moving-average crossovers and TSMOM are one family. | R² > 80% in all regressions; TSMOM(260d) Sharpe 1.45, MACROSS(32,128) 1.33, TSMOM(22d) 0.97; 58 instruments, 1985–2015; gross. | [LP 2016](https://research-api.cbs.dk/ws/portalfiles/portal/60084063/lasse_heje_pedersen_et_al_which_trend_is_your_friend_publishersversion.pdf) | T1 | Analytical plus empirical. | — | BUILD: count MA, Donchian and TSMOM variants as trials of one family (DSR). |
| E3-C07 | Better volatility estimators and continuous signals cut turnover by about 36% at no Sharpe cost. | Yang–Zhang −17%, TREND −24%, both −36%; costs 163 → 105 bp/yr; Sharpe 1.15 vs 1.11; 56 futures, 1983–2013. | [BK (CME)](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf) | T1 | Cost model includes roll. | — | BUILD: vote-share or continuous signal plus a band; range volatility where OHLC exists. |
| E3-C08 | The 2009–2013 trend drought appears in both academic and industry data. | TSMOM Sharpe 0.01 gross / −0.09 net (BK); SG Trend −1.8% cumulative 2009–13 (Man); correlations elevated from late 2008 to mid-2014 (HOP 2017). | [BK](https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf); [Man](https://www.man.com/insights/is-this-time-different); [HOP 2017](https://fairmodel.econ.yale.edu/ec439/hurst.pdf) | T1/T2 | Net index and simulation agree. | — | CONTEXT: B3's "no edge after 2009" replicates the industry. |
| E3-C09 | Net CTA returns split sharply around 2009. | Barclay Systematic CAGR 6.98% in 2000–08 (9/9 years positive) vs −0.30% in 2009–18 (3/10); 2009–25 mean/SD 0.30 with 9/17 years positive. | [BarclayHedge Systematic](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index) (E3 arithmetic) | T2 | Reported net (fee basis not verified); includes collateral interest. | 2009–2018. | CONTEXT: step 8's 60% rule would reject the net industry index over 2009–25. |
| E3-C10 | 2022 was the best year in SG index history. | SG CTA +20.1% (best since 2000), SG Trend +27.3%, STTI +11.3%; 27/30 programs positive; trend followers +11% to +40%. | [AlphaWeek](https://www.alpha-week.com/2022-cta-index-performance-review); [Hedgeweek](https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/) | T2 | Net; quotes SG. | Q4 2022 ≈ −6.4% (derived from [AQR](https://www.aqr.com/Insights/Research/White-Papers/Trend-Following-Why-Now-A-Macro-Perspective)). | CONTEXT: trend pays in slow inflation and rates bear markets. |
| E3-C11 | 2023–2025 were lean years well below equities. | SG Trend −4.16% (2023), +2.42/+2.6% (2024), +2.39% (2025); SG CTA −0.2% (2025); S&P 500 TR +17.89% (2025). | [TTU 2023](https://www.toptradersunplugged.com/trend-following-performance-report-december-2023/); [TTU 2025](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/); [Aussie Turtles 2025](https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/); [CFM](https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/) | T3/T2 | Two compilers agree within 0.2 pp. | 2024 figures conflict slightly. | CONTEXT. |
| E3-C12 | April 2025 produced the worst rolling 12-month loss in SG Trend history. | −18.6% to 30 Apr 2025 (prior worst −16.0%, Jan 2019); −9.3% year-to-date to 13 Apr; April −4.9%; 30% best-to-worst spread. | [Man](https://www.man.com/insights/is-this-time-different); [SG](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025) | T2 | Net, daily index. | Tariff reversals, 2–9 Apr 2025. | CONTEXT: pre-register a −20% drawdown expectation (≈ 80% chance in 25 years at Sharpe 0.5). |
| E3-C13 | 2026 has been a strong trend year so far. | SG Trend +15.85% and SG CTA +15.67% year-to-date (estimates, 1 Oct 2026); to August, SG Trend +11.07% vs S&P 500 TR +13.14%. | [BarclayHedge SG Trend](https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=SG-Prime-Services-Indices&indexName=SG-Trend-Index); [BarclayHedge SG CTA](https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=SG-Prime-Services-Indices&indexName=SG-CTA-Index); [TTU Aug 2026](https://www.toptradersunplugged.com/trend-following-performance-report-august-2026/) | T2 (estimates) / T3 | Estimates, not final. | June–July drawdown, recovered. | CONTEXT: do not tune on 2026; treat it as forward record. |
| E3-C14 | "Trend" is a wide distribution of manager outcomes. | 2024: average pairwise correlation 0.78 yet about a 15% range; 2022: +11% to +40%; cross-sectional SD ≈ 2%/month, stable 2010–24. | [SG](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025); [AlphaWeek](https://www.alpha-week.com/2022-cta-index-performance-review); [CFM](https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/) | T2 | — | — | CONTEXT: one QUANTGEN configuration ≈ one manager draw; use an ensemble. |
| E3-C15 | Managed-futures returns are largely TSMOM, and fees and costs remove roughly half the gross Sharpe. | R² 0.36–0.64; simulated gross Sharpe 1.8 → ≈ 1.0 after 2/20 (≈ 6%/yr) and 1–4%/yr costs; index net Sharpe 0.27–0.88 (1985–2012); implied weights 1m 24%, 3m 54%, 12m 22%. | [HOP 2013](https://w4.stern.nyu.edu/facdir/lpederse/papers/DemystifyingManagedFutures.pdf) | T1 | — | — | BUILD: multi-speed signal with 1–3-month weight; QUANTGEN users pay no fee. |
| E3-C16 | A realistic long-run live net Sharpe for trend programs is about 0.5–0.6, and lower after 2009. | SG CTA Sharpe 0.61 vs S&P 0.44 (2000–mid-2022); individual CTAs ≈ 0.5; 200-year backtest ≈ 0.7 before costs and fees. | [CFM 2022](https://www.cfm.com/wp-content/uploads/2022/12/39-A-Good-Time-for-Trend-Following-FINAL.pdf) | T2 | Net. | 2009–19 ≈ 0.3 or less (C09). | CONTEXT: expected live Sharpe for a diversified card 0.3–0.5. |
| E3-C17 | Short-horizon trends have decayed in traditional markets, and CTAs have slowed. | t ≈ 5 since 1960 and ≈ 10 since 1800; long trends intact, short trends withered; since 2007 the SG Trend Index fits 60–300-day MAs better. | [Lempérière 2014](https://arxiv.org/abs/1404.3274); [SG 2025](https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025) | T1 (preprint) / T2 | Conflicts with Hamill et al. (1–4-month lags strongest for crisis alpha). | — | BUILD: fixed equal-weight multi-speed ensemble; no walk-forward speed selection. |
| E3-C18 | Crisis alpha is real for prolonged sell-offs and unreliable for fast shocks. | Positive in 8/10 largest 60/40 drawdowns (GFC +17.8% vs −39.5%) and in all 7 S&P drawdowns > 15% (1985–2016); positive in only ≈ 50% of extreme volatility spikes vs ≈ 90% for L/S quality; SG Trend +1.1% in Mar 2020, −4.2% in Aug 2024. | [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf); [Man (Taylor)](https://www.man.com/maninstitute/best-strategies-for-the-worst-crises); [Man/AIMA](https://www.aima.org/article/trend-following-and-long-short-quality-loading-the-dice.html) | T2 | Diversified books, not single index. | 1937–38; Aug 2024; Apr 2025. | BUILD: pair trend with VT20 (fast crashes); quality covers spikes. |
| E3-C19 | On SPY, trend switches protect beyond de-gearing but do not raise Sharpe. | 1999–2021, 5 bp: 200d Sharpe 0.34–0.38 vs buy-and-hold 0.37–0.40; max drawdown −30.0% vs S −43.7% vs −56.5%; 2009–19 Sharpe 0.57 vs 0.79; ens × VT20 PC-1 +14.1 pp, tail ratio 0.51, 6/6 episodes (largest 45%), 61% of years positive; in-sample, price-only. | E3 check (SPY LEAN); consistent with [Zakamulin 2014](https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html) on overstated timing alpha | T3 (own check) | Not walk-forward; ≈ 40 configurations tried. | 2000 (−18.9% vs −10.0%), 2011, 2015, 2018; Feb–Dec 2020 (−1.4% vs +10.5%). | BUILD-candidate: re-gate E1 as CARD-P against S. |
| E3-C20 | On KOSPI, multi-speed trend beats a same-exposure static book over 1996–2026 but not over 2009–2019. | ens L/F Sharpe 0.60 vs S 0.41; max drawdown −35.3% vs −48.1%; 2001–26 ΔSharpe +0.04; 2009–19 0.23 vs 0.49; 2013–26 0.56 vs 0.55; 59% of years positive (buy-and-hold 69%). | E3 check (KRX marcap, survivorship-free) | T3 (own check) | Benefit concentrated in 1997–98 (largest share 42%). | 2009–2019; 2011 (−16.3% vs −10.7%); 2024 (−13.5% vs −9.8%). | BUILD-candidate CARD-P; never CARD-O. |
| E3-C21 | Trend and volatility targeting protect against different crash types. | KOSPI: trend 2008 −7.0% and 2022 −5.9% vs VT20 −31.2% and −25.0% (buy-and-hold −40.9%, −25.0%); 22 Jun–30 Jul 2026 trend −30.7% vs VT20 −12.0% (buy-and-hold −38.0%); trend × VT20 8/8 episodes (largest 31%), Sharpe 0.65 vs 0.41, max drawdown −26.7% vs −43.9%. | E3 check | T3 (own check) | Parameters taken from QUANTGEN's prior design (20/60/120/250) and macro rule R-06 (VT20). | 2009–19 Sharpe 0.24 vs 0.49; 53–55% of years positive (fails PC-5). | BUILD-candidate: register "trend × VT20" CARD-P on KOSPI200 / KODEX 200. |
| E3-C22 | The KOSPI protective result is a plateau, not a peak. | 20/20 grid cells: ΔSharpe vs S +0.04 to +0.26 and PC-1 +6.5 to +17.3 pp (1996–2026); all 20 negative in 2009–19 (−0.16 to −0.42); the 20/60 set is best. | E3 check | T3 (own check) | In-sample. | 2009–2019. | BUILD: use this grid; PC-6 likely met; PC-5 at risk. |
| E3-C23 | Long/half variants with a 0.5 floor keep about half the protection and pass the years test. | KOSPI long/half × VT20 floor 0.5: PC-1 +8.1 pp, tail ratio 0.79, 8/8 episodes (largest 19%), 63% of years positive; long/flat × VT20: PC-1 +17.3 pp but 53%; SPY long/half: PC-1 +11.2 pp, 65%. | E3 check | T3 (own check) | In-sample. | Long/half without VT: tail ratio 0.92 (fails PC-2). | BUILD-candidate alternative cell; flag the P2 signal-vs-overlay question. |
| E3-C24 | Crypto has documented short-horizon momentum. | BTC 2011–18: a one-SD weekly return predicts +3.16% next week (daily +0.33%); cross-sectional 3-week momentum 4.1%/week (t 2.74), large coins only; Donchian ensemble on top-20 coins net Sharpe > 1.5. | [LT, NBER w24877](https://www.nber.org/system/files/working_papers/w24877/w24877.pdf); [LTW, NBER w25882](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf); [Zarattini et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5209907) | T1 / T1 (preprint) | Samples end 2018 (LT/LTW); short histories. | 2018 and 2022 bear markets. | CONTEXT: supports a C3 prior of 2–3. |
| E3-C25 | Crypto trend's edge is timing, not volatility scaling, but it is shrinking. | BTC 2017-10 to 2026-05: C3-like Sharpe 1.19 vs buy-and-hold 0.83 vs vol-scaled long-only 0.83; ETH 1.12 vs 0.69 vs 0.71; drawdown vs static S only −53% vs −58%; 2022–26 Sharpe 0.61 vs 0.48; 2025 −11% vs −6%. | E3 check; [Coin Metrics data](https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv) | T3 (own check) | Approximation of C3; data end 23 May 2026; 10 bp. | 2025 whipsaw; ETH 2022–26 drawdown worse than S. | Keep C3 PASS; add the vol-scaled control, sub-period table and ETH replication; expected live Sharpe ≈ 0.6–0.7. |
| E3-C26 | Shiller monthly-average prices inflate trend backtests. | SPY 1998–2021: lag-1 autocorrelation 0.057 (month-end) vs 0.206 (month-average); 12m L/S Sharpe 0.35 vs 0.62; Shiller 1872–2026 12m L/S 0.50 → 0.30 with a one-month skip; 10m SMA 0.75 → 0.59. | E3 check | T3 (own check) | Known time-averaging mechanism (source not fetched). | — | DROP Shiller-average trend Sharpe claims; use month-end or skip-month. |
| E3-C27 | B3's REJECT cannot distinguish "no edge" from a realistic small edge. | Over ≈ 17 years out of sample, SE(Sharpe) ≈ 0.24 and the 80%-power detectable Sharpe ≈ 0.60; B3's interval [−0.27, 0.43] contains the 2009–25 industry ratio of 0.30; its benchmark (0.58) is a long-only basket. | QUANTGEN record; [BarclayHedge](https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index); E3 arithmetic | T3 | iid approximation. | — | REVISE path: re-register B3 as a diversifier (≥ 25 markets, multi-speed, against cash plus portfolio uplift). |
| E3-C28 | Stop-losses help only where returns are serially correlated; in a trend system the signal exit is the stop. | +50–100 bp/month during stop-out periods (US stocks vs bonds, 1950–2004); stop-losses lower returns under a random walk. | [Kaminski–Lo](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=968338) | T1 | — | Random-walk assets. | DROP separate stop layers on trend cards (double counting); keep signal exits and hysteresis. |
| E3-C29 | Carry is a separate premium that suffers in recessions. | Global carry gross Sharpe 1.10 (1983–2012); equities 0.74, commodities 0.66; fixed-income and commodity carry load on TSMOM, equity carry does not; worst drawdown Aug 2008–Feb 2009. | [KMPV, NBER w19325](https://www.nber.org/system/files/working_papers/w19325/w19325.pdf) | T1 | Gross. | Recessions. | BACKLOG: a KTB / commodity carry card after trend; keep it out of the trend card. |
| E3-C30 | Capacity is not QUANTGEN's constraint; fees and breadth are. | Systematic trend AUM $22bn (1999) → $280bn (2014); positions ≈ 0.2% of equity, 2% of bond, 6% of commodity and 0.4% of FX markets. | [HOP 2014](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf) | T2 | Estimates (BarclayHedge, via AQR). | — | CONTEXT: QUANTGEN is read-only; breadth is the binding limit. |

---

## Sources

**T1: academic (journal, NBER, arXiv, SSRN working papers)**
- Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum", *JFE* — https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf
- Hurst, Ooi & Pedersen (2017), "A Century of Evidence on Trend-Following Investing", *JPM*: https://fairmodel.econ.yale.edu/ec439/hurst.pdf ; https://www.pm-research.com/content/iijpormgmt/44/1/15
- Hurst, Ooi & Pedersen (2013), "Demystifying Managed Futures", *JOIM* — https://w4.stern.nyu.edu/facdir/lpederse/papers/DemystifyingManagedFutures.pdf
- Levine & Pedersen (2016), "Which Trend Is Your Friend?", *FAJ* — https://research-api.cbs.dk/ws/portalfiles/portal/60084063/lasse_heje_pedersen_et_al_which_trend_is_your_friend_publishersversion.pdf
- Baltas & Kosowski, "Demystifying Time-Series Momentum Strategies" (2017 version; Wiley 2020 chapter): https://www.cmegroup.com/education/files/demystifiing-time-series-momentum-strategies.pdf ; https://onlinelibrary.wiley.com/doi/abs/10.1002/9781119599364.ch3
- Lempérière, Deremble, Seager, Potters & Bouchaud (2014), "Two centuries of trend following", arXiv — https://arxiv.org/abs/1404.3274
- Huang, Li, Wang & Zhou (2020), "Time series momentum: Is it there?", *JFE*: https://down.aefweb.net/WorkingPapers/w717.pdf ; https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html
- Kim, Tse & Wald (2016), "Time series momentum and volatility scaling", *JFM* — https://www.sciencedirect.com/science/article/abs/pii/S1386418116301379
- Babu, Levine, Ooi, Pedersen & Stamelos, "Trends Everywhere" (JOIM 2020; working paper) — https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/fd3c53f7-c472-4898-a7e1-f6c100b1b81e.pdf
- Babu, Levine, Ooi, Schroeder & Stamelos (2020), "You Can't Always Trend When You Want", *JPM* (AQR summary) — https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want
- Koijen, Moskowitz, Pedersen & Vrugt, "Carry", NBER w19325 — https://www.nber.org/system/files/working_papers/w19325/w19325.pdf
- Liu & Tsyvinski, "Risks and Returns of Cryptocurrency", NBER w24877 (*RFS* 2021) — https://www.nber.org/system/files/working_papers/w24877/w24877.pdf
- Liu, Tsyvinski & Wu, "Common Risk Factors in Cryptocurrency", NBER w25882 (*JF* 2022) — https://www.nber.org/system/files/working_papers/w25882/w25882.pdf
- Zarattini, Pagani & Barbon (2025), "Catching Crypto Trends", SSRN — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5209907
- Kaminski & Lo, "When Do Stop-Loss Rules Stop Losses?", SSRN — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=968338
- Zakamulin (2014), "The real-life performance of market timing with moving average and time-series momentum rules", *JAM* — https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html
- Goulding, Harvey & Mazzoleni (2023), "Momentum turning points", *JFE* — https://ideas.repec.org/a/eee/jfinec/v149y2023i3p378-406.html
- Harvey et al., "The Best of Strategies for the Worst of Times", SSRN — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3383173
- Hamill, Rattray & Van Hemert, "Trend Following: Equity and Bond Crisis Alpha", SSRN — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2831926

**T2: index providers, asset managers, trade press**
- SG Prime Services indices page — https://wholesale.banking.societegenerale.com/en/prime-services-indices/
- SG, "CTA Industry Update: Keeping Up With The Trend-Followers" (May 2025) — https://content.sgmarkets.com/CTA_UPDATE_KEEPING_UP_WITH_THE_TRENDFOLLOWERS_2025
- BarclayHedge:
  - Barclay CTA Index — https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Barclay-CTA-Index
  - Systematic Traders Index — https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-CTA-Indices&indexName=Systematic-Traders-Index
  - BTOP50 — https://portal.barclayhedge.com/cgi-bin/indices/displayCtaIndex.cgi?indexCat=Barclay-Investable-Benchmarks&indexName=BTOP50-Index
  - SG Trend — https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=SG-Prime-Services-Indices&indexName=SG-Trend-Index
  - SG CTA — https://portal.barclayhedge.com/cgi-bin/indices/displayHfIndex.cgi?indexCat=SG-Prime-Services-Indices&indexName=SG-CTA-Index
- AQR:
  - Hurst, Ooi & Pedersen (2014 white paper copy) — https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf
  - "Trend-Following: Why Now? A Macro Perspective" (Nov 2022) — https://www.aqr.com/Insights/Research/White-Papers/Trend-Following-Why-Now-A-Macro-Perspective
- Man Group:
  - Korgaonkar, "Trend Following and Drawdowns: Is This Time Different?" (2025) — https://www.man.com/insights/is-this-time-different
  - Taylor, "The Best Strategies for the Worst Crises" — https://www.man.com/maninstitute/best-strategies-for-the-worst-crises
  - Hamill, Rattray & Van Hemert (Man Institute) — https://www.man.com/maninstitute/trend-following-equity-and-bond-crisis-alpha
  - Goodall (Man AHL) via AIMA (Mar 2025) — https://www.aima.org/article/trend-following-and-long-short-quality-loading-the-dice.html
- CFM:
  - "Steady Trends: The Reality of CTA Return Dispersion" (2025) — https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/
  - "A Good Time for Trend Following" (May 2022) — https://www.cfm.com/wp-content/uploads/2022/12/39-A-Good-Time-for-Trend-Following-FINAL.pdf
- Trade press:
  - Hedgeweek (27 Jan 2023) — https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/
  - AlphaWeek (9 Feb 2023) — https://www.alpha-week.com/2022-cta-index-performance-review
- Coin Metrics community data:
  - BTC — https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv
  - ETH — https://raw.githubusercontent.com/coinmetrics/data/master/csv/eth.csv

**T3: practitioner compilations and fund marketing (used only where T1/T2 were unavailable)**
- Top Traders Unplugged monthly reports:
  - Dec 2021 — https://www.toptradersunplugged.com/trend-following-performance-report-december-2021/
  - Dec 2022 — https://www.toptradersunplugged.com/trend-following-performance-report-december-2022/
  - Dec 2023 — https://www.toptradersunplugged.com/trend-following-performance-report-december-2023/
  - Dec 2024 — https://www.toptradersunplugged.com/trend-following-performance-report-december-2024/
  - Jun 2025 — https://www.toptradersunplugged.com/trend-following-performance-report-june-2025/
  - Dec 2025 — https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/
  - Aug 2026 — https://www.toptradersunplugged.com/trend-following-performance-report-august-2026/
- Aussie Turtles, "Battle of the Trend Following Indexes":
  - Dec 2024 — https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2024/
  - Dec 2025 — https://www.aussieturtles.com/battle-of-the-trend-following-indexes-december-2025/
  - Feb 2026 — https://www.aussieturtles.com/battle-of-the-trend-following-indexes-february-2026/
- Simplify:
  - CTA flyer 1Q26 — https://www.simplify.us/sites/default/files/etf/2026-04/Simplify%20CTA%20Flyer%201Q26.pdf
  - "Four Years In" — https://www.simplify.us/etfs-use-case/cta-four-years-investor-portfolios

**Internal / local**
- `00_QUANTGEN_context.md`: QUANTGEN record, cards B3, C3, E1, E2 and V3; study run 2026-09-27.
- Project docs `claude/QUANTGEN_MACRO_INTEGRATION.md` (R-14, R-15, §8.7 CARD-P, N-33) and `claude/QUANTGEN_macro_overlay_research_report.md`.
- Local data:
  - `/home/claude/data_raw/us/spy_lean_daily.zip`
  - `/home/claude/data_raw/us/shiller_sp500_monthly.csv`
  - `/home/claude/data_raw/us/vix_daily.csv`
  - `/home/claude/data_raw/marcap/data/marcap-1995…2026.parquet`
- E3 check scripts (session scratchpad, temporary): `e3_checks.py` to `e3_checks8.py`.

**Could not be read** (for the record):
- SG historical index spreadsheets and the SG CTA methodology PDF: 403.
- FRED TB3MS: 403 from the egress proxy, and 429 rate-limited on the text page.
- Ken French data library: 403.
- SSRN pages for Baltas–Kosowski 2013 (SSRN 1968996) and "Breaking Bad Trends" (SSRN 3594888): 429.
- Kaminski, "In Search of Crisis Alpha" (CME): 404.
- JSTOR, for Working (1960) on time-averaging: page unreadable.
