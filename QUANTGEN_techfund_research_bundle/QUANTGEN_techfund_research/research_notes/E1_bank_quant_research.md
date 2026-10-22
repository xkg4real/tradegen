# E1: What bank and asset-manager quant research claimed, what happened after publication, and what QUANTGEN should build

**Persona (fictional composite).** E1 is the "Global Head of Quantitative and Derivatives Strategy Research at a bulge-bracket bank". This is a made-up composite whose career looks like a J.P. Morgan / Morgan Stanley-style quant and derivatives strategy desk. E1 is not a real person and speaks for no real firm. The lens: "I have written and marketed these reports. I know which numbers are construction advice and which are sales material. My job here is to separate them using the data that came after publication." All real research is credited to its real authors and firms. As of 2 October 2026.

**Position summary.**
1. Sell-side and asset-manager research is very useful for *construction*: how to define a factor, how to scale risk, how to combine signals. It is unreliable for *headline performance numbers*. Almost every headline Sharpe ratio is in-sample, often not clearly labelled gross or net, and later decays.
2. The J.P. Morgan 2015 momentum report showed a 1.21 Sharpe for 12-month time-series momentum across assets (1992-2014 backtest). Live trend-following since then has earned roughly 3%/yr over T-bills net of fees (AQR managed-futures fund, 10 years to Sep-2026). QUANTGEN's own futures time-series momentum card scored 0.08 out of sample. Treat 1.21 as a ceiling, not a prior.
3. Valuation explains long-horizon equity returns (5-10 years) somewhat. It explains almost nothing over one year:
   - J.P. Morgan Asset Management's own Guide to the Markets R² for forward P/E vs 1-year returns: 5-8%.
   - Its 5-year R² fell from 44% (Sep-2020 edition) to 28% (Mar-2026) as post-2020 data arrived.
   - My Shiller test shows CAPE keeps the right *ranking* out of sample but gets the *level* badly wrong after 1990.
4. Long-only smart-beta products did not deliver their pitches after 2016. To 30-Jun-2026, net of fees:
   - MSCI momentum (MTUM) beat the S&P 500 by 2.1 percentage points a year over 10 years.
   - Quality (QUAL) lagged by 1.0 points a year and lost more than the index in 2022.
   - Minimum volatility (USMV) lagged by 5.9 points a year.
   - All four MSCI single-factor ETFs lagged IVV cumulatively over 2021-2025.
5. Crowding is real and measurable (Goldman Sachs prime-book data). It works as a *risk monitor*, not a timing signal. Record crowding in Nov-2023 was followed by more outperformance, then sharp unwinds (Jan-2026; Jun-Jul 2026: MTUM -18% vs SPY -2% in five weeks).
6. Big-data/AI claims (J.P. Morgan 2017) have not reached retail products. The AI-selected ETF AIEQ returned 4.2%/yr over five years vs 12.7% for SPY.
7. **What QUANTGEN should do:**
   - Copy the *definitions*: multi-measure, industry-neutral value; quality composites; risk-adjusted momentum with crash controls; buy/hold bands against turnover.
   - Treat crowding and valuation as sizing context only, consistent with the macro rule that sizing multipliers stay in [0.5, 1.0].
   - Drop factor-ETF rotation, valuation timing and ML as alpha sources for now.
   - Haircut any bank or asset-manager backtest by at least 50-60% before it becomes a prior.

---

## Key question 1: What does bank research say works (momentum/trend, valuation, crowding, big data/AI), and did the headline claims hold up after publication?

### Takeaway
Bank research correctly identified 6-12-month trend, crash risk and the valuation-return link. Its headline numbers did not survive later data:
- Live trend-following after the 2015 J.P. Morgan report earned far less than the 1.21 backtest Sharpe.
- J.P. Morgan's own one-year valuation R² is 5-8%, and its five-year R² decayed from 44% to 28% between editions.
- Goldman's record-crowding readings did not predict when unwinds would come.

### Cited findings

**J.P. Morgan, "Momentum Strategies Across Asset Classes" (Kolanovic and Wei, 15 April 2015).** Source: [J.P. Morgan via CME](https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf) for every point below.
- A cross-asset momentum portfolio with Equal Marginal Volatility (EMV) weighting had a Sharpe of 0.78 over 1972-2014. Single asset classes ranged 0.18-0.57. (Backtest, in-sample.)
- The prototype 12-month time-series ("absolute") momentum strategy across equities, bonds, FX and commodities had a Sharpe of 1.21 over 1992-2014 (Table 3).
  - Cross-sectional ("relative") 12-month momentum across all assets: 0.44 (Table 7).
  - "Enhanced" relative momentum, which adds an absolute-momentum filter: 0.82 (Table 8).
  - All in-sample backtests.
- Costs: the paper assumes 10 bp one-way per asset. The tables do not say whether Sharpe ratios are net or gross. Net/gross is ambiguous.
- Lookback horizon:
  - 12 months: Sharpe 0.82 (equity), 0.75 (bonds), 0.63 (commodities).
  - 6 months: 0.84 / 0.31 / 0.46.
  - 3 months: 0.56 / 0.42 / 0.51.
  - 1 month: 0.33 / 0.27 / 0.19.
  - The authors favour 6-12-month horizons.
- The authors warn that momentum has negative skew and fat tails, loses money at turning points, and that long backtests underestimate risks and costs. On a perfect trend signal: the effect "would have to disappear".
- Live CTA returns after fees fell from +7.4%/yr (1994-2010, of which +4.1 points was cash yield) to -1.9%/yr (2011-2013). This is the average of the Barclay CTA, BTop50, DJCS CTA and CISDM CTA indices. CTA assets were $316.8bn in 4Q14.

**Post-publication evidence on trend.**
- AQR's live managed-futures mutual fund (AQMIX, inception 5-Jan-2010), net of fees, to 30-Sep-2026 [AQR fund page](https://funds.aqr.com/funds/alternatives/aqr-managed-futures-strategy-fund):

  | Horizon | AQMIX | 3-month T-bill |
  |---|---|---|
  | 10 years | 5.44%/yr | 2.42% |
  | 5 years | 15.04%/yr | 3.70% |
  | Since inception | 4.54%/yr | 1.48% |

  Adjusted expense ratio 1.25%.
- AQR blames the weak trend-following decade of the 2010s on fewer large market moves, not on a lost ability to profit from trends. It sees little evidence of a permanent change ([Babu, Levine, Ooi, Schroeder, Stamelos, JPM 2020, AQR](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want)).
- AQR's century study reports time-series momentum consistently profitable since 1880. The page did not give numbers ([Hurst, Ooi, Pedersen, JPM Oct-2017](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)).
- **E1 desk calculation** (local Shiller monthly S&P 500 file `/home/claude/data_raw/us/shiller_sp500_monthly.csv`).
  - Method: S&P 500 only, long or flat; signal at month t applied to month t+1. Prices are monthly averages. Flat months earn zero (no T-bill). No costs (0.3-1.3 switches a year). Dividends after Jun-2023 approximated at the last known yield.
  - "R/V" below is return ÷ volatility, not a true Sharpe. "Gross" means before costs.

  | Rule and period | Strategy return / vol / R/V / max DD | Buy-and-hold return / vol / R/V / max DD |
  |---|---|---|
  | 12-month sign, 1927-1991 | 9.3% / 11.3% / 0.82 / -37.5% | 11.1% / 16.8% / 0.66 / -81.8% |
  | 12-month sign, 1992-2014 (J.P. Morgan sample) | 11.6% / 8.8% / 1.32 / -11.7% | 10.0% / 12.4% / 0.81 / -49.0% |
  | 12-month sign, 2015-Sep 2026 (post-publication) | 10.9% / 10.7% / 1.02 / -18.9% | 13.8% / 11.9% / 1.16 / -19.3% |
  | 10-month moving average, 2015-2026 | 12.2% / 9.6% / 1.27 / -18.9% | 13.8% / 11.9% / 1.16 / -19.3% |

  - Post-publication, both rules earned less than buy-and-hold, and drawdown protection vanished.
  - This matches QUANTGEN's E1 trend-switch REJECT (protects but does not outperform) and B3 (0.08 out of sample) in `00_QUANTGEN_context.md`.

**J.P. Morgan, "Big Data and AI Strategies" (Kolanovic and Krishnamachari, May 2017).** Source: [J.P. Morgan via UCI faculty site](https://bpb-us-e2.wpmucdn.com/faculty.sites.uci.edu/dist/2/51/files/2018/05/JPM-2017-MachineLearningInvestments.pdf).
- Headline claims: the big-data market was about $130bn, rising to over $200bn by 2020. Investment-management spend on big data was $2-3bn. Managers who do not adopt big data and machine learning risk becoming obsolete.
- On how much predictive power alternative data contains: "most data have a small positive Sharpe ratio". Datasets with high-Sharpe signals will disappear. The authors also warn about overfitting and instability.
- The only performance example is a Twitter-sentiment S&P 500 strategy (vendor iSentium): 13.7%/yr since Jan-2013, information ratio 1.4 after 5 bp costs, vs S&P 500 12.1% and IR 0.95. This is a short vendor sample, not independent.
- After publication: the AI-selected ETF AIEQ (EquBot, IBM Watson, inception 17-Oct-2017, expense ratio 0.75%) returned, NAV to 31-Aug-2026 [Amplify ETFs](https://amplifyetfs.com/aieq/):

  | Horizon | AIEQ | SPY ([SSGA](https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy)) |
  |---|---|---|
  | 1 year | 15.47%/yr | 20.21% |
  | 3 years | 17.74%/yr | 20.89% |
  | 5 years | 4.18%/yr | 12.65% |
  | Since inception | 10.08%/yr | about 13.3%/yr price-only plus dividends (E1 calc from the Shiller file, Oct-2017 to Aug-2026) |

- Academic checks:
  - Machine learning can double the performance of regression-based strategies in gross academic tests. Trees and neural nets do best, and the dominant predictors are momentum, liquidity and volatility ([Gu, Kelly, Xiu, NBER w25398](https://www.nber.org/papers/w25398)).
  - Deep-learning profits come mainly from hard-to-arbitrage stocks. They shrink after excluding microcaps, distressed stocks or high-volatility periods, and shrink further after realistic costs because of high turnover ([Avramov, Cheng, Metzker, Management Science 2023, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3450322)).

**J.P. Morgan Asset Management Guide to the Markets (GTM): forward P/E vs subsequent S&P 500 returns.**

| Edition | 1-year R² | 5-year R² | Forward P/E vs average | Source |
|---|---|---|---|---|
| 4Q20 (30-Sep-2020) | 8% | 44% | 21.54x vs 25-year avg 16.46x (+1.60 SD); IBES data since Sep-1995 | [GTM 4Q20 copy](https://www.gillentinegroup.com/wp-content/uploads/2020/12/JP-Morgan-Asset-Management-Guide-to-the-Markets.pdf) |
| 2Q24 (31-Mar-2024) | 7% | 29% | 20.96x vs 30-year avg 16.62x | [GTM 2Q24 copy](https://www.hiltonheadadvisors.org/assets/Councils/HiltonHead-SC/library/JPMorgan%20Guide%20to%20the%20Markets%20-Merrill%20Lynch%20version2Q24%202024-Mar-31.pdf) |
| Daily GTM (30-Mar-2026) | 5% | 28% | 19.2x vs 30-year avg 17.2x | [J.P. Morgan AM daily GTM](https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/market-insights/guide-to-the-markets/daily/mi-daily-gtm-us.pdf) |

- 2Q24 notes: the footnote, as extracted, describes monthly data starting 1/31/1999. CAPE was 34.75x vs 27.65x.
- In the 3Q26 GTM (as of 30-Jun-2026) [J.P. Morgan AM GTM](https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/market-insights/guide-to-the-markets/mi-guide-to-the-markets-us.pdf):
  - Forward P/E 20.4x vs 30-year average 17.2x; CAPE 40.7x vs 28.8x; dividend yield 1.4% vs 2.0%; earnings-yield spread -0.5% vs 0.7%.
  - The equity-slide R² values were not extractable as text.
  - The bond slide (starting yield vs subsequent 5-year Bloomberg US Aggregate return) shows R² 89%.
- An earlier copy (1Q16 edition, data as of 31-Dec-2015) showed forward P/E 16.1x vs 25-year average 15.8x and no R² chart ([copy](https://www.faswealthpartners.com/wp-content/uploads/2016/03/JP-Morgan-Market-Slides_4Q15.pdf)).
- E1 check of what followed each reading (Shiller monthly-average price, no dividends):

  | Forward P/E reading | Next 12 months | To Sep-2026 |
  |---|---|---|
  | 21.5x (Sep-2020) | +32.1% | +127.9% |
  | 21.0x (Mar-2024) | +9.9% | +48.3% |
  | 16.1x (Dec-2015) | +9.4% | — |

**E1 desk calculation: Shiller CAPE and trailing P/E vs forward annualized real total return.**
- Method: monthly start dates, overlapping windows, OLS on log valuation. Data runs to Jun-2023 for 10-year windows that start by mid-2013. Local file as above.

  | Start dates | Measure | 1-year R² | 5-year R² | 10-year R² |
  |---|---|---|---|---|
  | From 1881 | CAPE | 0.05 | 0.16 | 0.29 |
  | From 1881 | Trailing P/E | 0.01 | 0.04 | 0.17 |
  | From 1950 | CAPE | 0.04 | 0.14 | 0.34 |
  | From 1990 | CAPE | 0.11 | 0.52 | 0.86 (in-sample, few independent decades) |
  | From 1990 | Trailing P/E | 0.01 | 0.02 | 0.09 |

- Out-of-sample: a fit on 1881-1979 start dates, used to predict 1990-2013 start dates, gave out-of-sample R² of:
  - -0.54 at 10 years (correlation +0.93);
  - -0.58 at 5 years (correlation +0.72);
  - -0.38 at 1 year (correlation +0.33).
  - Mean predicted 10-year real return was 1.1%/yr; the actual was 6.5%/yr.
  - In short, CAPE ranked periods correctly but got the level badly wrong.
- Expanding-window point forecasts of 10-year real total return:

  | Date | CAPE | Forecast | Realized |
  |---|---|---|---|
  | Dec-1995 | 25.0 | 0.8%/yr | 6.5%/yr |
  | Jan-2000 | 43.8 | -3.9%/yr | -3.0%/yr |
  | Mar-2009 | 13.3 | 7.3%/yr | 14.3%/yr |
  | Jun-2013 | 22.9 | 2.9%/yr | 9.5%/yr |

- Months with CAPE above 30 (n=102 through Sep-2023):
  - Average forward 1-year price return 3.0%, positive 58% of the time. Unconditional (1881-2025 starts): 6.7% and 65%.
  - The first month above 30 after 2010 was Sep-2017 (30.17). The S&P 500 then rose from 2,492.8 to 7,669.4 by Sep-2026: +208%, or 13.3%/yr price-only.

**BofA Global Research (Savita Subramanian), from a May-2024 interview transcript.** Source: [Ritholtz transcript](https://ritholtz.com/2024/05/transcript-savita-subramanian/).
- Price to normalized earnings explains about 80% of subsequent 10-year S&P 500 returns. Valuation does poorly over a 1-year horizon.
- The Sell Side Indicator is the monthly average of Wall Street strategists' recommended equity allocation since 1980, used as a contrarian signal. A 43% reading in 2012 was a buy signal. She says it has become more effective since the global financial crisis. No hit-rate numbers were given.
- On pure momentum: it "works when, until it stops". BofA pairs momentum with fundamentals and revisions.
- The S&P 500 is now about 50% asset-light tech and healthcare, vs about 70% asset-intensive in 1980. It is less levered, which she says justifies higher multiples. Active share has fallen (closet indexing).

**Goldman Sachs crowding research (via press reports and a GS Insights article).**
- Goldman Sachs, reported 21-Nov-2023 ([Investing.com report on GS research](https://investing.com/news/stock-market-news/magnificent-7-bets-drive-hedge-fund-crowding-to-record-high-goldman-sachs-3240404)):
  - The average hedge fund held 70% of its long portfolio in its top-10 positions, the highest in the 22 years GS has tracked it.
  - Megacap tech was 13% of aggregate hedge fund longs, double the start of 2023.
  - The most popular hedge fund positions (the VIP basket) were +31% year-to-date vs +19% for the S&P 500.
  - Coverage: 735 funds, $2.4tn gross equity positions.
- Goldman Sachs Prime Insights (Parker and Lin), 12-Feb-2026 ([GS Insights](https://www.goldmansachs.com/insights/articles/hedge-funds-have-momentum-after-posting-double-digit-returns-last-year)):
  - Hedge funds returned 11.8% in 2025 and 11.9% in 2024. Alpha in 2025 was the highest in more than 30 years.
  - Net inflows were about $79bn in 2025. 49% of allocators planned to add hedge fund exposure.
  - Demand for quant funds is outstripping supply.
- Unwinds reported from GS prime-brokerage data: see Key question 3 ([Hedgeweek, 22-Jan-2026](https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind); [Hedgeweek, 7-Jul-2026](https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/)).

### Inferences
- J.P. Morgan's 1.21 Sharpe came from a sample (1992-2014) that contains two great trend environments (2000-02 and 2008). My S&P 500 split shows the same rule at 1.32 inside that window and at or below buy-and-hold afterwards. The paper's own CTA data (-1.9%/yr in 2011-13) already contradicted the backtest at publication.
- Practical live prior for diversified trend: about 3%/yr excess return net of fees (AQMIX), so a Sharpe around 0.3 if volatility is about 10%. I could not verify the fund's volatility. For a single equity index the uplift is about zero; the only benefit is drawdown reduction in slow bear markets.
- The GTM R² series is the cleanest "headline-claim decay" in this file. The same chart, from the same firm, lost a third of its five-year explanatory power in under six years because high valuations in 2020-21 were followed by strong returns. Valuation charts belong in client education, not in a one-year timing model.
- Subramanian's ~80% for 10-year returns is consistent with my 0.86 for post-1990 start dates. It is not consistent with the 0.29 for the full history from 1881. The figure depends on the window and rests on only about three independent decades.
- Her structural argument (asset-light, less levered index) is one explanation for why CAPE's level failed out of sample after 1990. This is a regime shift that a fixed regression cannot see.
- The crowding data shows crowded books *outperforming* for long stretches (2023: VIP +31% vs +19%). The cost is concentrated in short, sharp unwinds. That argues for crash controls (volatility scaling, gross reduction) rather than avoiding crowded factors.

### Gaps
- **Morgan Stanley quant strategy on crowding:** no publicly accessible primary document found in this session. No Morgan Stanley figures are used.
- **Deutsche Bank quant "Signal Processing" (Yin Luo's team):** not accessible. No figures used.
- **Goldman Sachs primary notes** (e.g., the 12-Mar-2025 note on the Magnificent 7) returned 403. GS figures above are from GS Insights or press summaries of GS data. The long-run performance of the VIP basket since 2001 was not obtained.
- **BofA Sell Side Indicator** current reading, implied return and quantified track record: not obtained.
- The 3Q26 GTM equity R² values could not be extracted. The start date of the 2Q24 footnote (1/31/1999 as extracted) should be checked against the slide.
- Whether the J.P. Morgan 2015 tables are net or gross is ambiguous in the document itself.

---

## Key question 2: What do asset managers and index providers say works (AQR, Research Affiliates, Man Group, Robeco, MSCI factor indices, SPIVA), and how did it hold up?

### Takeaway
Asset-manager research holds up on *structure*:
- Momentum and value hedge each other.
- Multi-measure, industry-neutral value beats book-to-price.
- Volatility targeting helps risk assets.
- Most active managers lose to the index.

It held up poorly on *timing*:
- AQR's May-2020 call that the odds favoured value paid off only unevenly.
- Research Affiliates' 2016 valuation warning was right for low volatility, but more than five years early for value.

Over 2021-2025, every long-only MSCI single-factor ETF lagged the S&P 500.

### Cited findings

**AQR, "Fact, Fiction and Momentum Investing" (Asness, Frazzini, Israel, Moskowitz, JPM Fall 2014).** Sources: [AQR article page](https://www.aqr.com/Insights/Research/Journal-Article/Fact-Fiction-and-Momentum-Investing); [PDF](https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/JPM-Fact-Fiction-and-Momentum-Investing.pdf).
- US momentum factor (UMD): 8.3%/yr, Sharpe 0.50 (1927-2013). Value factor (HML): 4.7%/yr, Sharpe 0.39. Correlation between them about -0.4.
- Large-cap momentum Sharpe over 1991-2013, out of sample after its discovery: 0.24.
- The long side contributes 5.5%/yr and the short side 5.1%/yr.
- The paper says momentum survives trading costs, but the PDF summary gave no cost numbers.

**AQR, "Fact, Fiction, and Value Investing" (same authors, JPM Oct-2015).** Source: [AQR](https://www.aqr.com/Insights/Research/Journal-Article/Fact-Fiction-and-Value-Investing).
- It rebuts myths that value only works when concentrated, buys junk, is redundant given newer factors, or works only long-only. It says the jury is out on risk vs behavioural explanations. No performance numbers were in the page text.

**AQR, "Craftsmanship Alpha: An Application to Style Investing" (Israel, Jiang, Ross).** Source: [AQR working paper PDF](https://www.aqr.com/-/media/AQR/Documents/Insights/Working-Papers/AQR--Craftsmanship-Alpha.pdf).
- Dating: AQR lists it as JPM Multi-Asset Special Issue 2018 (Dec-2017). The brief's "2020" date may refer to another version (not verified).
- A multi-measure value portfolio averaged Sharpe 0.26 vs 0.07 for book-to-price alone. Their correlation is about 0.9. The multi-measure version beat book-to-price in almost every five-year period since 1990.
- In naive value only 32% of risk comes from within-industry stock selection, so industry-neutral value earns higher risk-adjusted returns.
- Using current prices rather than 6-18-month-lagged prices removes accidental momentum exposure.
- Market impact is about 17 bp when trading 2% of daily volume and about 28 bp at 6%.
- Timing skill must exceed about 0.1 Sharpe to justify any tactical allocation. Even 0.5-Sharpe timing skill justifies only ±12% tilts.

**AQR value-spread notes, 2020-2022.**
- "Is (Systematic) Value Investing Dead?" (8-May-2020) [AQR PDF](https://www.aqr.com/-/media/AQR/Documents/Perspectives/Cliffs-Perspective-5620-Is-Systematic-Value-Investing-Dead.pdf?sc_lang=en):
  - Price-to-book value spread at the 100th percentile of 50+ years; expensive stocks at almost 12x the price of cheap ones; +4.5 SD above the median.
  - The industry-neutral composite was at the 100th percentile, 98% of the way to the maximum. Realistic implementations were 100% above the previous maximum.
  - HML had its worst quarter (1Q2020) since 1963 and second-worst since 1926.
  - Cheap stocks' fundamentals were normal: profitability spread at the 52nd percentile, so the drawdown came from spreads widening rather than fundamentals.
  - Conclusion: "medium-term odds are now, rather dramatically, on the side of value".
- 16-Dec-2021: value factors were up in 2021 even as spreads widened to record cheapness ([AQR](https://www.aqr.com/Insights/Perspectives/Thats-it-Thats-the-Blog)).
- 4-Feb-2022: spreads at about the tech-bubble peak level ([AQR](https://www.aqr.com/Insights/Perspectives/thats-it-that-the-update)).
- 5-Aug-2022: spreads fully back to the tech-bubble peak; value returns still strong year-to-date ([AQR](https://www.aqr.com/Insights/Perspectives/Value-Spreads-Back-to-Tech-Bubble-Highs-Are-You-People-Crazy)).

**Research Affiliates, "How Can 'Smart Beta' Go Horribly Wrong?" (Arnott, Beck, Kalesnik, West, Feb-2016; data 1967-2015Q3).** Source: [Research Affiliates](https://www.researchaffiliates.com/en_us/publications/articles/442_how_can_smart_beta_go_horribly_wrong.html).
- Relative valuations predict later factor returns, and recent factor returns were inflated by rising valuations.
  - Low volatility: 0.82%/yr after removing valuation change, with more than 100% of its return from valuation expansion.
  - Profitability: essentially all outperformance from rising valuations; 0.39%/yr valuation-adjusted.
  - Momentum and illiquidity also had valuation tailwinds.
  - Value was in its cheapest historical decile.
- The authors warn of a "smart beta crash".

**Man Group, volatility targeting (Harvey, Hoyle, Korgaonkar, Rattray, Sargaison, Van Hemert, JPM Fall 2018; 60+ assets, daily data from 1926).** Source: [Man Institute](https://www.man.com/maninstitute/the-impact-of-volatility-targeting).
- Volatility targeting raises Sharpe ratios for equities and credit, and for balanced and risk-parity portfolios.
- The effect is negligible for bonds, FX and commodities. The mechanism is the leverage effect (volatility rises when prices fall).
- It reduces extreme returns and left-tail severity in all asset classes, and cuts maximum drawdowns of balanced and risk-parity portfolios.

**MSCI factor indices, via the iShares ETFs that track them.**
- NAV returns net of 0.15% fees, with benchmark (MSCI index) returns in brackets, as of 30-Jun-2026 factsheets. iShares product pages label some of these "Aug/Sep 2026" but show identical numbers. My Stocklake price check reproduced MTUM +43.7% and USMV +4.3% for the year to 30-Jun-2026.

  | ETF (MSCI index) | 1 year | 3 years | 5 years | 10 years | Source |
  |---|---|---|---|---|---|
  | MTUM (USA Momentum SR Variant) | 43.70 (43.92) | 34.58 (34.79) | 15.94 (16.12) | 17.58 (17.79) | [iShares MTUM factsheet](https://www.ishares.com/us/literature/fact-sheet/mtum-ishares-msci-usa-momentum-factor-etf-fund-fact-sheet-en-us.pdf) |
  | QUAL (USA Sector Neutral Quality) | 21.34 (21.64) | 18.93 (19.13) | 11.92 (12.11) | 14.47 (14.67) | [iShares QUAL factsheet](https://www.ishares.com/us/literature/fact-sheet/qual-ishares-msci-usa-quality-factor-etf-fund-fact-sheet-en-us.pdf) |
  | VLUE (USA Enhanced Value) | 80.03 (80.94) | 31.90 (32.23) | 16.81 (17.06) | 15.44 (15.65) | [iShares VLUE factsheet](https://www.ishares.com/us/literature/fact-sheet/vlue-ishares-msci-usa-value-factor-etf-fund-fact-sheet-en-us.pdf) |
  | USMV (USA Minimum Volatility) | 4.32 (4.46) | 10.90 (10.86) | 7.29 (7.33) | 9.59 (9.70) | [iShares USMV factsheet](https://www.ishares.com/us/literature/fact-sheet/usmv-ishares-msci-usa-min-vol-factor-etf-fund-fact-sheet-en-us.pdf) |
  | IVV (S&P 500) | 22.29 | 20.58 | 13.37 | 15.47 | [iShares IVV factsheet](https://www.ishares.com/us/literature/fact-sheet/ivv-ishares-core-s-p-500-etf-fund-fact-sheet-en-us.pdf) |

  - Holdings notes: MTUM had 126 holdings, P/E 46.1x and 54.3% information technology ([iShares MTUM page](https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf)). VLUE's top holding was Micron at 24.46%, with 41.75% information technology. USMV's 3-year beta was 0.49 and 3-year standard deviation 9.31%.
- Calendar-year NAV returns, 2021 / 2022 / 2023 / 2024 / 2025 (same factsheets):

  | ETF | 2021 | 2022 | 2023 | 2024 | 2025 |
  |---|---|---|---|---|---|
  | MTUM | 13.45 | -18.23 | 9.10 | 32.88 | 22.10 |
  | QUAL | 26.90 | -20.39 | 30.83 | 22.23 | 12.65 |
  | VLUE | 28.98 | -14.14 | 14.26 | 7.21 | 32.65 |
  | USMV | 20.79 | -9.35 | 10.21 | 15.83 | 7.68 |
  | IVV | 28.66 | -18.13 | 26.27 | 24.98 | 17.85 |

- **E1 derived from the factsheets:**
  - 10-year excess vs IVV: MTUM +2.11 points/yr, QUAL -1.00, VLUE -0.03, USMV -5.88.
  - First five years (Jul-2016 to Jun-2021, backed out of the 10- and 5-year figures): MTUM +1.63, QUAL -0.53, VLUE -3.52, USMV -5.67.
  - Last five years (Jul-2021 to Jun-2026): MTUM +2.57, QUAL -1.45, VLUE +3.44, USMV -6.08.
  - Cumulative 2021-2025: MTUM +64.2%, QUAL +82.0%, VLUE +79.9%, USMV +50.5%, IVV +95.9%.
- SPHB (S&P 500 High Beta), price-only from Stocklake daily data: +60.6% (year to 30-Jun-2026) vs SPY +22.2%. Long-run SPHB returns were not obtained.

**S&P DJI SPIVA.**

| Scorecard | Category | Share of funds underperforming |
|---|---|---|
| US year-end 2025 ([SPIVA US YE2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-us-year-end-2025.pdf)) | Large-cap vs S&P 500 | 78.78% (1y), 66.84% (3y), 88.96% (5y), 85.59% (10y), 89.93% (15y), 92.89% (20y) |
| | All domestic vs S&P Composite 1500 | 95.01% (20y) |
| | Mid-cap vs S&P 400 | 89.74% (20y) |
| | Small-cap vs S&P 600 | 90.28% (20y) |
| US H1 2026 ([SPIVA US page](https://www.spglobal.com/spdji/en/spiva/article/spiva-us/)) | Large-cap | 67% |
| Europe year-end 2025 ([SPIVA Europe YE2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-europe-year-end-2025.pdf)) | EUR Europe equity | 81.83% (1y), 97.02% (10y) |
| | EUR global equity | 98.44% (10y) |
| | GBP UK equity | 92.98% (10y) |
| Japan year-end 2025 ([SPIVA Japan YE2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-japan-year-end-2025.pdf)) | Large-cap | 49% (1y), 83% (10y) |
| | All Japan equity | 78% (10y) |

- US notes: 2025 was the fourth-worst year on record for large-cap active funds. Only 34.61% of large-cap funds survived 20 years.
- Japan note: the 49% one-year figure was the best relative showing since 2017.

**Academic tests of practitioner factor claims.**
- **Hou, Xue, Zhang:** 286 of 447 anomalies (64%) are insignificant at 5% when using NYSE breakpoints and value-weighting, including 95 of 102 liquidity variables. 85% fail at t>3 ([NBER w23394](https://www.nber.org/papers/w23394)).
- **Jensen, Kelly, Pedersen:** most factors replicate under a Bayesian approach, cluster into 13 themes, and hold out of sample in 93 countries ([NBER w28432](https://www.nber.org/papers/w28432)).
- **McLean and Pontiff (2012 SSRN version):** about 15% out-of-sample decay from statistical bias, and about 50% post-publication decay ([Crossref record, DOI 10.2139/ssrn.2080900](https://api.crossref.org/works?query.bibliographic=Does+Academic+Research+Destroy+Stock+Return+Predictability+McLean+Pontiff&rows=2); final version in Journal of Finance 71(1), 2016: [RePEc](https://ideas.repec.org/a/bla/jfinan/v71y2016i1p5-32.html)).

### Inferences
- **Post-2016 scorecard by factor:**
  - Momentum: the one long-only factor that beat the index (+2.1 points/yr). Much of that came from being long mega-cap tech (54% information technology in mid-2026), not from a diversified long/short premium. It also came with -15 and -17 point relative years (2021, 2023).
  - Quality: failed the test it is marketed for. It lost 2.3 points *more* than the S&P 500 in 2022.
  - Minimum volatility: did what Research Affiliates predicted. It underperformed by about 6 points a year as valuation expansion reversed and the market rallied.
  - Value: Research Affiliates' cheapness signal was 5 years early (-3.5 points/yr in Jul-2016 to Jun-2021). Value then paid (+3.4 points/yr in Jul-2021 to Jun-2026) in two bursts (2022, 2025), separated by -12 and -18 point years (2023, 2024).
- AQR's 2020 call worked only on a 5-year horizon and only in bursts. Craftsmanship Alpha's own ±12% tilt ceiling is the right humility.
- USMV's beta of 0.49 means its raw underperformance is mostly beta. Its CAPM alpha may be about zero or slightly positive. This needs a data check (DC9), not a press verdict.
- SPIVA is the base rate for QUANTGEN's step 5 (beat the benchmark on the same days, p ≤ 0.10). Roughly 85-98% of professional active funds fail a 10-year net test across the US, Europe and global equity. QUANTGEN's REJECT rate (18/34) is not too harsh.
- Man Group's result partly conflicts with the macro research's "vol-scaling robust only for momentum". Man finds Sharpe gains for equities and credit too. QUANTGEN's own E2 test (SPY 0.63 vs 0.56, p 0.18) fits a small, statistically weak uplift. I flag this rather than re-open it.

### Gaps
- Robeco "Conservative Formula" and other Robeco factor research: the page fetch did not return the paper. No Robeco numbers used.
- AQR long/short value and HML Devil returns 2020-2026 were not obtained. The ETF proxies (sector-relative, long-only) are weak tests of AQR's long/short call.
- Numbers from Hurst-Ooi-Pedersen's century study were not obtained (only the qualitative finding).
- McLean-Pontiff's final Journal of Finance figures (number of predictors and decay percentages) were not re-fetched this session (SSRN rate-limited). Only the 2012 SSRN version is cited.
- SPHB long-run (2011-2026) returns and calendar years before 2021 for the MSCI ETFs (2014-2020) were not available from the pages fetched.
- MSCI's own factsheets were not fetched. The iShares-reported benchmark returns are used as MSCI index data.

---

## Key question 3: Where and when did it fail? (dated episodes with numbers; mandatory)

### Takeaway
The failures cluster into three groups:
1. Crash-type momentum reversals: 1932, 2009, Jun-Jul 2026.
2. Long regime droughts: trend in 2011-2019; value in 2017-2020; low volatility in 2023-2026.
3. Valuation-timing errors: CAPE above 30 from 2017 while the S&P 500 tripled in price.

Every family that bank or asset-manager research markets had at least one dated episode of multi-year underperformance or a double-digit relative loss within weeks.

### Cited findings
**Momentum crashes.**
- Jul-Aug 1932: past losers +232% vs past winners +32%. Mar-May 2009: losers +163% vs winners +8%. Crashes occur in bear markets with high volatility when the market rebounds. A dynamic momentum strategy reaches Sharpe 1.18, about four times static momentum, over 1927-2013, in-sample ([Daniel and Moskowitz, NBER w20439](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf)).
- 2021 and 2023: MTUM lagged IVV by 15.2 and 17.2 points (iShares factsheets above).
- 2025: quant drawdowns in early summer and October from momentum reversals and rallies in low-quality stocks ([Hedgeweek, 22-Jan-2026](https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind)).
- First half of Jan-2026 ([Hedgeweek, 22-Jan-2026](https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind)):
  - Goldman: systematic long/short managers had their weakest 10 days in more than three months, about -1%.
  - UBS: US quant funds were about -2.8% in the first two weeks of the year.
  - Drivers: crowded-trade drawdowns, short exposure to high-beta stocks, and idiosyncratic moves.
- Late Jun to early Jul-2026 ([Hedgeweek, 7-Jul-2026](https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/)):
  - Momentum fell more than 3% for a second straight week (S&P Global long/short momentum series).
  - Goldman: systematic managers -2.1% in one week and -3.1% over the previous five days, the "weakest stretch since December 2023".
  - Momentum had climbed for nearly three years to the highest level since the series began in 2002.
  - Managers cut leverage because momentum volatility and VaR rose. Rotation was out of high-momentum AI stocks into cheaper defensive sectors.
  - Year-to-date: systematic funds about +11.1%, fundamental funds about +16%.
- **E1 desk calculation** (Stocklake daily closes, validated against iShares):

  | Window | MTUM | SPY | SPHB | USMV |
  |---|---|---|---|---|
  | 22-Jun to 29-Jul-2026 | -18.0% | -2.0% | -14.1% | +4.3% |
  | 3 to 5-Feb-2026 | -4.8% | -1.7% | — | +0.1% |
  | 29-Jan to 30-Mar-2026 | -11.5% | -8.7% | -9.9% | -2.8% |

  - In the Jun-Jul window MTUM lost 16.3% relative to SPY.
- A secondary blog (T3) reports Goldman's high-beta momentum basket down about 37% in July 2026 and about 35% below its June peak ([Artificial Finance, 11-Aug-2026](https://artificialfinance.org/2026/08/the-ai-momentum-unwind/)). The primary GS source was not seen, so treat this as unverified.

**Trend and CTA droughts.**
- CTAs averaged -1.9%/yr after fees in 2011-2013, vs +7.4% in 1994-2010 ([J.P. Morgan 2015](https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf)).
- AQR describes lower trend returns through the 2010s ([AQR 2020](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want)).
- E1 calculation: S&P 500 12-month long/flat earned 10.9%/yr vs buy-and-hold 13.8% over 2015-Sep 2026, with the same drawdown (-18.9% vs -19.3%). Monthly signals do not protect against fast crashes such as 2020.
- QUANTGEN's own record: futures time-series momentum (B3) 0.08 out of sample; US ETF trend switch (E1) 0.84 vs 0.95, p 0.75 (`00_QUANTGEN_context.md`).

**Value drought and whipsaw.**
- 1Q2020 was HML's worst quarter since 1963, with spreads at the 100th percentile ([AQR, May-2020](https://www.aqr.com/-/media/AQR/Documents/Perspectives/Cliffs-Perspective-5620-Is-Systematic-Value-Investing-Dead.pdf?sc_lang=en)).
- Spreads were back at tech-bubble highs in Aug-2022 ([AQR, Aug-2022](https://www.aqr.com/Insights/Perspectives/Value-Spreads-Back-to-Tech-Bubble-Highs-Are-You-People-Crazy)).
- VLUE vs IVV: -3.5 points/yr (Jul-2016 to Jun-2021); -12.0 points (2023); -17.8 points (2024). Then +14.8 points (2025), and +80% absolute in the year to Jun-2026 with 24.5% in Micron (iShares factsheet).

**Quality and low volatility failing their marketing.**
- QUAL returned -20.39% in 2022 vs IVV -18.13% ([iShares QUAL](https://www.ishares.com/us/literature/fact-sheet/qual-ishares-msci-usa-quality-factor-etf-fund-fact-sheet-en-us.pdf)).
- USMV lagged IVV by 16.1, 9.2 and 10.2 points in 2023-2025, and returned 4.32% vs 22.29% in the year to Jun-2026 ([iShares USMV](https://www.ishares.com/us/literature/fact-sheet/usmv-ishares-msci-usa-min-vol-factor-etf-fund-fact-sheet-en-us.pdf)).

**Valuation-timing failures.**
- GTM Sep-2020 edition: forward P/E 21.5x (+1.6 SD). The S&P 500 then rose +32.1% in 12 months and +127.9% to Sep-2026 (E1 calc). The GTM's own 5-year R² fell from 44% to 28% ([GTM 4Q20](https://www.gillentinegroup.com/wp-content/uploads/2020/12/JP-Morgan-Asset-Management-Guide-to-the-Markets.pdf); [daily GTM Mar-2026](https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/market-insights/guide-to-the-markets/daily/mi-daily-gtm-us.pdf)).
- CAPE first exceeded 30 in Sep-2017; the S&P 500 then rose +208% in price to Sep-2026 (E1 calc). An out-of-sample CAPE regression predicted 2.9%/yr real from Jun-2013; 9.5%/yr was realized.

**Big data / AI products.**
- AIEQ returned 4.18%/yr vs SPY 12.65%/yr over the 5 years to Aug-2026 ([Amplify](https://amplifyetfs.com/aieq/); [SSGA](https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy)).

**Active management.**
- 79% of US large-cap funds lagged in 2025, the fourth-worst year on record ([SPIVA US YE2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-us-year-end-2025.pdf)).

### Inferences
- Momentum failures are fast: weeks, with -16 to -18 points relative. Value and low-volatility failures are slow: years. One generic risk control will not handle both:
  - Momentum needs volatility scaling plus a bear-state or crash gate (already adopted by the macro research).
  - Value and low volatility need patience and small weights, not stop-losses.
- The 2026 episodes came right after record momentum levels (highest since 2002) and record allocator demand for quant (GS Feb-2026). "Extreme positioning plus record factor level" is a reasonable *risk-sizing* condition. Its timing value is unproven: crowding reached a record in Nov-2023 and kept paying for 2.5 years.

### Gaps
- No primary GS document was seen for the Jun-Jul 2026 basket drawdown magnitudes. Only the S&P Global series (more than 3% per week) via Hedgeweek, and my MTUM/SPY calculation, are verified.
- Daily long/short factor returns (MSCI Barra, French daily) for 2024-2026 were not accessible. The Ken French site was blocked by proxy policy. The lab's French file ends in 2018.

---

## Key question 4: How do banks and asset managers actually use technical vs fundamental signals in products, and what are the cost, capacity and marketing-backtest pitfalls?

### Takeaway
**How products use signals.**
- In bank products, technical analysis appears in formalized form: the sign of a 6-12-month return or moving-average crossovers, volatility-scaled and weighted by equal marginal risk.
- Fundamentals appear in rules-based equity factor indices: quality = ROE, earnings stability, low debt; value = valuation ratios, sector-relative.
- Sentiment and positioning data (Sell Side Indicator, VIP crowding) are sold as context.

**Costs and capacity.**
- Institutional market impact is about 17-28 bp at 2-6% of daily volume.
- Anomalies with more than 50% monthly turnover rarely survive costs.

**The largest marketing pitfalls.**
- In-sample windows and net/gross ambiguity.
- R² from overlapping windows.
- Index construction that drifts into concentrated bets: a "value" ETF with 24% in one chip stock.

### Cited findings
- **Technical construction (J.P. Morgan 2015).**
  - Signals: simple price returns over 1-12 months. Moving averages, RSI and volatility-normalized indicators are tested in the appendices.
  - Sizing: Equal Marginal Volatility weighting across sleeves, 20% volatility targets for individual underliers, and ex-ante volatility from an exponentially weighted standard deviation (63-day half-life).
  - Costs: 10 bp one-way per futures asset.
  - Source: [J.P. Morgan](https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf).
- **CTA benchmarks.** SG Trend Index and SG CTA Index: equal-weighted, reconstituted annually, net daily returns of large trend-following and CTA managers ([Société Générale index page, 2015 snapshot](https://wholesale.banking.societegenerale.com/en/prime-services-indices/)).
- **Fundamental factor indices.**
  - QUAL targets high ROE, stable earnings and low debt ([iShares QUAL](https://www.ishares.com/us/literature/fact-sheet/qual-ishares-msci-usa-quality-factor-etf-fund-fact-sheet-en-us.pdf)).
  - VLUE targets value characteristics and relatively lower valuations ([iShares VLUE](https://www.ishares.com/us/literature/fact-sheet/vlue-ishares-msci-usa-value-factor-etf-fund-fact-sheet-en-us.pdf)).
  - USMV targets lower volatility ([iShares USMV](https://www.ishares.com/us/literature/fact-sheet/usmv-ishares-msci-usa-min-vol-factor-etf-fund-fact-sheet-en-us.pdf)).
  - Fees are 0.15%.
- **Alternative data in products.** Fundamental investors prefer processed signals. Quants take raw data and build proprietary signals. Hiring data scientists without finance expertise may not produce results ([J.P. Morgan 2017](https://bpb-us-e2.wpmucdn.com/faculty.sites.uci.edu/dist/2/51/files/2018/05/JPM-2017-MachineLearningInvestments.pdf)).
- **Sentiment and positioning products.** BofA's Sell Side Indicator is a contrarian sentiment gauge ([transcript](https://ritholtz.com/2024/05/transcript-savita-subramanian/)). GS hedge fund crowding is measured as top-10 concentration and VIP-basket returns ([Investing.com on GS](https://investing.com/news/stock-market-news/magnificent-7-bets-drive-hedge-fund-crowding-to-record-high-goldman-sachs-3240404)).
- **Costs and capacity.**
  - Market impact about 17 bp at 2% of daily volume and about 28 bp at 6%. Patient multi-day execution lowers costs. Faster rebalancing raises gross returns but costs more ([AQR Craftsmanship Alpha](https://www.aqr.com/-/media/AQR/Documents/Insights/Working-Papers/AQR--Craftsmanship-Alpha.pdf)).
  - Strategies with more than 50% monthly turnover generally lose significance after costs. A buy/hold spread is the single most effective mitigation ([Novy-Marx and Velikov, NBER w20721](https://www.nber.org/papers/w20721)).
  - CTA assets were $316.8bn in 4Q14. J.P. Morgan suggests inflows may have reduced alpha ([J.P. Morgan 2015](https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf)).
- **Concentration drift.** As of 30-Jun-2026, VLUE held 24.46% in Micron and 41.75% in information technology. MTUM held 54.3% in information technology at P/E 46.1x (iShares factsheets above).
- **Survivorship.** Only 34.61% of US large-cap funds survived 20 years ([SPIVA US YE2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-us-year-end-2025.pdf)).

### Inferences
**Marketing-backtest pitfalls, and the QUANTGEN control for each:**

| # | Pitfall | Example | QUANTGEN control |
|---|---|---|---|
| 1 | In-sample window chosen around favourable regimes | J.P. Morgan 1992-2014 includes 2000-02 and 2008 | Gate step 1 walk-forward; report pre- and post-publication splits |
| 2 | Net/gross not labelled | J.P. Morgan tables | Rule 2: every result at 1x and 2x costs |
| 3 | Statistics from overlapping windows | GTM 5-year R²; BofA "80%" | Report effective independent observations and Newey-West errors (DC1) |
| 4 | Rolling statistics that decay as data arrives | GTM 44% → 28% | Re-estimate on every data refresh; record each re-estimate as a trial (gate step 3) |
| 5 | Index rules that turn a factor label into a concentrated bet | VLUE with 24% Micron | Single-name cap (e.g., 5%) and sector bands; report "factor purity" |
| 6 | Vendor alternative-data examples on short samples | iSentium since 2013 | Minimum history = 756 + 126 sessions × 3 splits |
| 7 | Survivorship in manager or fund data | SPIVA 20-year survival 35% | marcap is survivorship-free for KRX; never use current-constituent US lists (OHLCVault US list is survivor-only) |
| 8 | Cash yield inside "returns" | CTA 1994-2010: 4.1 of 7.4 points | Compare excess-of-cash returns |

- **Costs for QUANTGEN.** Its retail cost table is far above institutional impact for small tickets: KRX stocks 35 bp per side, US shares through KIS 50 bp per side. Cost drag ≈ 2 × cost per side × annual one-way turnover. A monthly-rebalanced momentum book with about 150% one-way turnover therefore loses about 1.05%/yr in KRX at 1x costs and about 2.1% at 2x, and more in the US. That is the same order as the long-only momentum premium. Buy/hold bands (Novy-Marx-Velikov) are mandatory, not optional.

### Gaps
- No primary bank QIS index rulebook (e.g., a published J.P. Morgan or Goldman momentum-factor index methodology) was retrieved. Bank product construction is inferred from the 2015 research note.
- **Bank-index overfitting study:** Suhonen, Lennkh and Perez, "Quantifying Backtest Overfitting in Alternative Beta Strategies" (JPM 2017), compares backtest and live Sharpe ratios. It could not be read (robots/rate limits), so no figures are used. It is listed as a data-check and reading item.
- Detailed MSCI methodology (score definitions, constraints, rebalance dates) was not fetched in this session.

---

## Key question 5: QUANTGEN translation. Which bank-style constructs are worth replicating as cards, which numbers are priors, with what haircuts, and what should the data lab test?

### Takeaway
- **Copy as cards:**
  - Multi-measure, industry-neutral value, current-price based.
  - A quality composite.
  - Risk-adjusted 12-1 and 6-1 momentum with volatility scaling and a bear gate.
  - Buy/hold bands on all of them.
- **Keep as context or sizing only:** crowding and positioning monitors, valuation (CAPE / forward P/E), and volatility-targeted trend.
- **Drop for now:** factor-ETF rotation, one-year valuation timing, ML/alternative data.
- **Priors:** start from published Sharpe ratios and cut them by 50-60% (in line with gate step 9). Add the Ilmanen factor-specific decay (value -49%, momentum -23%, multifactor -18%) and the retail cost drag.

### Cited findings

#### Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| E1-C01 | J.P. Morgan's 12-month time-series momentum across four asset classes had a backtest Sharpe of 1.21. | All-asset Sharpe 1.21 (1992-2014); cross-sectional 0.44; enhanced 0.82; EMV 0.78 (1972-2014). IS; 10 bp one-way assumed; net/gross unlabelled. | [J.P. Morgan 2015](https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf) | T2 | No OOS in the paper. Live analogues much weaker (C05). | CTAs -1.9%/yr after fees in 2011-13, shown in the same paper | CONTEXT/DROP as an alpha prior: 1.21 is an IS ceiling. Live prior 0.3-0.4 diversified. |
| E1-C02 | 6-12-month lookbacks dominate 1-month for trend. | 12m Sharpe equity 0.82 / bonds 0.75 / commodities 0.63 vs 1m 0.33 / 0.27 / 0.19. IS, 1992-2014. | [J.P. Morgan 2015](https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf) | T2 | Consistent with academic TSMOM literature | 1m worst after costs | BUILD (design rule): trend and sizing cards use 6-12m windows. Never 1m trend. |
| E1-C03 | Cash yield was a large share of historical CTA returns. | After-fee CTA return 7.4%/yr in 1994-2010, of which 4.1 points cash; -1.9%/yr in 2011-13. Live, net, 4-index average. | [J.P. Morgan 2015](https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf) | T2 | Live data | Zero-rate era 2011-13 | BUILD (accounting rule): all cards report excess-of-cash returns; flat periods earn T-bill. |
| E1-C04 | AQR attributes 2010s trend weakness to fewer large moves, not decay. | Qualitative attribution; no numbers on the page. | [AQR 2020](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want) | T2 | Explanation, not a forecast | 2011-2019 | BACKLOG: re-test B3 after 126 more OOS sessions. Do not loosen the gate. |
| E1-C05 | A live diversified managed-futures fund earned about 3%/yr over cash net of fees over 10 years. | AQMIX 10y 5.44% vs T-bill 2.42%; 5y 15.04% vs 3.70%; since Jan-2010 4.54% vs 1.48%; as of 30-Sep-2026. Live, net. | [AQR fund page](https://funds.aqr.com/funds/alternatives/aqr-managed-futures-strategy-fund) | T2 | OOS since 2010, one manager | Weak 2010s implied | PRIOR: diversified trend excess about 3%/yr net (Sharpe about 0.3 if 10% vol; vol unverified). |
| E1-C06 | S&P 500 long/flat trend beat buy-and-hold in the J.P. Morgan sample window but not after publication. | 12m rule R/V 1.32 vs 0.81 (1992-2014); 1.02 vs 1.16 (2015-Sep 2026); return 10.9% vs 13.8%; max DD -18.9% vs -19.3%. Gross, no cash; Shiller monthly averages. | E1 calc on `/home/claude/data_raw/us/shiller_sp500_monthly.csv` | calc | Pre/post split; monthly-average bias flatters timing | 2015-2026 underperformance | DROP as alpha. CONTEXT as a drawdown overlay ≤1.0 (macro rule). DC3. |
| E1-C07 | J.P. Morgan AM's forward-P/E chart explains little 1-year return, and its 5-year R² decayed. | 1y R² 8% (Sep-2020 ed.), 7% (Mar-2024), 5% (Mar-2026); 5y 44% → 29% → 28%. IS, overlapping monthly, US. | [GTM 4Q20](https://www.gillentinegroup.com/wp-content/uploads/2020/12/JP-Morgan-Asset-Management-Guide-to-the-Markets.pdf); [GTM 2Q24](https://www.hiltonheadadvisors.org/assets/Councils/HiltonHead-SC/library/JPMorgan%20Guide%20to%20the%20Markets%20-Merrill%20Lynch%20version2Q24%202024-Mar-31.pdf); [daily GTM](https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/market-insights/guide-to-the-markets/daily/mi-daily-gtm-us.pdf) | T2 | Statistic decays as data arrives | Fwd P/E 21.5x (Sep-2020) → S&P +32% next 12m | DROP for 1y timing. CONTEXT for 5-10y return-expectation display with wide bands. |
| E1-C08 | CAPE ranks long-horizon returns but its level failed OOS after 1990. | Full-history R² 0.05 / 0.16 / 0.29 (1y/5y/10y); post-1990 10y 0.86 IS; OOS R² -0.54 (10y) with correlation +0.93; Jun-2013 forecast 2.9%/yr real vs 9.5% realized. | E1 calc, local Shiller file | calc | Clear IS/OOS split | Calibration break after 1990 | CONTEXT. Any valuation overlay must use expanding-window percentiles, not regression levels. DC1, DC2. |
| E1-C09 | BofA says normalized P/E explains about 80% of 10-year returns but little over 1 year. | Interview statement; no sample stated. | [Ritholtz transcript, May-2024](https://ritholtz.com/2024/05/transcript-savita-subramanian/) | T2 | E1 calc gives 0.86 post-1990 but 0.29 full-history: window-dependent | — | CONTEXT. Treat "80%" as window-specific IS. |
| E1-C10 | BofA's Sell Side Indicator is a contrarian sentiment gauge. | Strategists' average equity allocation since 1980; 43% in 2012 = buy; "more effective since GFC" (no stats given). | [Ritholtz transcript](https://ritholtz.com/2024/05/transcript-savita-subramanian/) | T2 | No public hit-rate data | — | BACKLOG: proprietary, cannot replicate. Korean analogue (investor-type flow extremes) via DC5. |
| E1-C11 | CAPE above 30 has not been a reliable 1-year sell signal. | 102 months (through Sep-2023): mean fwd 1y price +3.0%, 58% positive vs 6.7% / 65% unconditional; S&P +208% from Sep-2017 (first >30) to Sep-2026. Price-only. | E1 calc, local Shiller file | calc | Overlapping windows; few episodes | 1997-99, 2017-21, 2023-26 | DROP as a timing card. At most a [0.5, 1.0] multiplier if DC2 passes the gate. |
| E1-C12 | Hedge fund crowding hit a record without immediate payback. | Nov-2023: 70% of longs in top-10 (22-year high); VIP +31% vs S&P +19% YTD; 735 funds, $2.4tn. | [Investing.com on GS](https://investing.com/news/stock-market-news/magnificent-7-bets-drive-hedge-fund-crowding-to-record-high-goldman-sachs-3240404) | T2 | Press summary of GS data | Unwinds came 2+ years later | CONTEXT: crowding is a risk monitor, never a direction signal. |
| E1-C13 | Momentum/crowding unwinds hit systematic funds in 2025-2026. | Jan-2026: GS systematic long/short about -1% in 10 days; UBS US quant -2.8%. Jul-2026: momentum -3%+ for 2 weeks; GS systematic -2.1% / -3.1%; weakest since Dec-2023; momentum at highest level since 2002 just before. | [Hedgeweek 22-Jan-2026](https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind); [Hedgeweek 7-Jul-2026](https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/) | T2 (trade press citing GS/UBS/S&P Global) | Multiple sources agree on direction | 2025 summer and Oct; 2026 Jan and Jul | BUILD: volatility scaling + bear gate on momentum (already decided). Add a factor-vol trigger (DC5). |
| E1-C14 | The Jun-Jul 2026 unwind cost long-only momentum 16 points relative in five weeks. | MTUM -18.0% vs SPY -2.0% (22-Jun to 29-Jul-2026); SPHB -14.1%; USMV +4.3%. Price-only. | E1 calc on Stocklake closes (1y returns match iShares NAV) | calc | Matches press direction | — | BUILD: the momentum card must report worst-5-week relative loss. Test a crash gate on KRX (DC4, DC8). |
| E1-C15 | US momentum has a positive long-run premium, weaker in large caps after discovery, and hedges value. | UMD 8.3%/yr, Sharpe 0.50 (1927-2013); large-cap Sharpe 0.24 (1991-2013, OOS); correlation with HML -0.4. Gross. | [AQR 2014 PDF](https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/JPM-Fact-Fiction-and-Momentum-Investing.pdf) | T2 (peer-reviewed practitioner journal) | Replicated; post-2008 weak (macro brief: 0.02 since 2008) | 1932, 2009, 2021, 2023, 2026 | PRIOR: large-cap long/short momentum Sharpe 0.25 gross before haircuts. Always pair with value (C17). |
| E1-C16 | Dynamic (volatility- and state-aware) momentum roughly quadruples the static Sharpe. | Dynamic Sharpe 1.18 vs about 0.3 static (1927-2013, IS); crashes Jul-Aug 1932 (losers +232%) and Mar-May 2009 (losers +163%). | [Daniel and Moskowitz NBER w20439](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf) | T1 | Widely replicated; adopted by the macro research | Crashes in rebounds after bear markets | BUILD (already decided): sigma126 scaling, 12% target, cap 1.0, bear gate floor 0.5. |
| E1-C17 | Multi-measure, industry-neutral, current-price value beats book-to-price. | Sharpe 0.26 vs 0.07 since 1990; correlation 0.9; naive value only 32% within-industry risk; impact 17 bp at 2% ADV / 28 bp at 6%; timing needs >0.1 Sharpe skill, tilts ±12%. IS, gross. | [AQR Craftsmanship Alpha](https://www.aqr.com/-/media/AQR/Documents/Insights/Working-Papers/AQR--Craftsmanship-Alpha.pdf) | T2 | IS; consistent with HXZ/JKP replication themes | Value drought 2017-2020 | BUILD-candidate (KRX via OpenDART PIT): B/P + E/P + CF/P + S/P, industry-neutral. No factor timing. |
| E1-C18 | AQR said in May-2020 that extreme value spreads made the medium-term odds favour value. | Spread at 100th percentile; HML worst quarter since 1963 (1Q2020). After: VLUE +3.4 pts/yr vs IVV (Jul-2021 to Jun-2026) but -12.0 (2023) and -17.8 (2024); spreads back at tech-bubble highs in Aug-2022. | [AQR May-2020](https://www.aqr.com/-/media/AQR/Documents/Perspectives/Cliffs-Perspective-5620-Is-Systematic-Value-Investing-Dead.pdf?sc_lang=en); [AQR Aug-2022](https://www.aqr.com/Insights/Perspectives/Value-Spreads-Back-to-Tech-Bubble-Highs-Are-You-People-Crazy); iShares factsheets | T2 | Partly vindicated on 5y, in bursts | 2023-2024 | CONTEXT: show the value spread as an expected-return gauge. Never size up above 1.0. |
| E1-C19 | Research Affiliates (2016) said recent factor returns were inflated by valuation changes, warning low volatility and profitability were expensive. | Low vol: >100% of return from valuation expansion, 0.82%/yr adjusted; profitability 0.39%/yr adjusted; value cheapest decile (1967-2015Q3). After: USMV -5.9 pts/yr and QUAL -1.0 pts/yr vs IVV over 10y; VLUE -3.5 pts/yr in the first 5 years. | [Research Affiliates](https://www.researchaffiliates.com/en_us/publications/articles/442_how_can_smart_beta_go_horribly_wrong.html); iShares factsheets | T2 | Right on low vol; early on value | Value 2016-2020 | BUILD (reporting): model cards show valuation-adjusted factor returns next to raw returns. |
| E1-C20 | Long-only MSCI factor ETFs did not reliably beat the S&P 500 after 2016. | 10y to Jun-2026 excess vs IVV: MTUM +2.1, QUAL -1.0, VLUE -0.0, USMV -5.9 pts/yr; cum 2021-2025 +64 / +82 / +80 / +50% vs IVV +96%. Live, net. | iShares factsheets (MTUM, QUAL, VLUE, USMV, IVV URLs in source list) | T2 | Live OOS | 2022 QUAL -2.3 pts; 2023 MTUM -17.2 pts | DROP factor-ETF rotation. PRIOR: long-only factor tilt active return ≈ 0 ± 2%/yr. |
| E1-C21 | Rules-based factor indices can drift into concentrated bets. | VLUE: Micron 24.46%, IT 41.75%; MTUM: IT 54.3%, P/E 46.1x (30-Jun-2026). | [iShares VLUE factsheet](https://www.ishares.com/us/literature/fact-sheet/vlue-ishares-msci-usa-value-factor-etf-fund-fact-sheet-en-us.pdf); [iShares MTUM factsheet](https://www.ishares.com/us/literature/fact-sheet/mtum-ishares-msci-usa-momentum-factor-etf-fund-fact-sheet-en-us.pdf) | T2 | Observed holdings | Label vs exposure mismatch | BUILD: single-name cap (e.g., 5%) and sector bands; publish factor-purity and concentration in every card. Korea: Samsung/SK hynix caps (macro). |
| E1-C22 | Most professional active equity funds lag their index after fees. | US large-cap: 78.78% (2025), 85.59% (10y), 92.89% (20y); 20y survival 34.61%. Europe equity 10y 97.02%. Japan large-cap 10y 83% (49% in 2025). Live, net. | [SPIVA US YE2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-us-year-end-2025.pdf); [SPIVA Europe](https://www.spglobal.com/spdji/en/documents/spiva/spiva-europe-year-end-2025.pdf); [SPIVA Japan](https://www.spglobal.com/spdji/en/documents/spiva/spiva-japan-year-end-2025.pdf) | T2 | Persistent for 20+ years, many markets | Occasional good years (Japan 2025) | CONTEXT: base rate for gate step 5; supports keeping the p ≤ 0.10 benchmark test. |
| E1-C23 | J.P. Morgan (2017) said alternative data mostly carries small Sharpe ratios and high-Sharpe datasets decay. | Most datasets carry only a small positive Sharpe (paraphrase); Twitter example IR 1.4 after 5 bp since 2013 (vendor, short sample). After: AIEQ 5y 4.18% vs SPY 12.65% (to Aug-2026). | [J.P. Morgan 2017](https://bpb-us-e2.wpmucdn.com/faculty.sites.uci.edu/dist/2/51/files/2018/05/JPM-2017-MachineLearningInvestments.pdf); [Amplify AIEQ](https://amplifyetfs.com/aieq/) | T2 | One retail AI product is weak evidence | AIEQ underperformance | DROP for now. Revisit only after linear cards pass. |
| E1-C24 | ML gains in academic tests concentrate in hard-to-arbitrage stocks and shrink after costs. | Machine learning up to doubles regression-strategy performance (gross, US); profits shrink excluding microcaps, distressed stocks and high-vol periods, and with costs. | [Gu-Kelly-Xiu NBER w25398](https://www.nber.org/papers/w25398); [Avramov-Cheng-Metzker SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3450322) | T1 | Peer-reviewed | Costs and turnover | BACKLOG: only with liquidity filters and 2x costs. |
| E1-C25 | Published anomalies shrink out of sample and after publication; many fail with microcaps controlled. | 64% of 447 anomalies insignificant with NYSE breakpoints/VW (85% at t>3); JKP: most replicate in 93 countries; McLean-Pontiff SSRN version: about 15% OOS and about 50% post-publication decay. | [HXZ NBER w23394](https://www.nber.org/papers/w23394); [JKP NBER w28432](https://www.nber.org/papers/w28432); [Crossref McLean-Pontiff](https://api.crossref.org/works?query.bibliographic=Does+Academic+Research+Destroy+Stock+Return+Predictability+McLean+Pontiff&rows=2) | T1 | Replicated meta-evidence | Liquidity anomalies (93% fail) | PRIOR: keep the 60% live haircut (gate step 9); avoid liquidity-type anomalies. |
| E1-C26 | High-turnover anomalies rarely survive costs; buy/hold bands are the best fix. | Strategies with >50% monthly turnover generally insignificant after costs (US). | [Novy-Marx and Velikov NBER w20721](https://www.nber.org/papers/w20721) | T1 | Peer-reviewed | Short-term reversal, high-frequency signals | BUILD: hysteresis/buy-hold bands on every stock-level card; report turnover. |
| E1-C27 | Volatility targeting improves Sharpe for equities and credit, not bonds, FX or commodities, and trims left tails. | 60+ assets, daily since 1926 (Man Group, JPM 2018), IS. | [Man Institute](https://www.man.com/maninstitute/the-impact-of-volatility-targeting) | T2 | Peer-reviewed practitioner journal | QUANTGEN E2 SPY uplift not significant (p 0.18) | CONTEXT: keep the macro decision (momentum sleeves). Flag the partial conflict; no up-weighting above 1.0. |
| E1-C28 | Hedge fund alpha and quant demand were at records just before the 2026 unwinds. | GS: HF return 11.8% (2025), alpha highest in 30+ years, $79bn inflows, quant demand outstripping supply (12-Feb-2026); Jul-2026 quant drawdown followed. | [GS Insights](https://www.goldmansachs.com/insights/articles/hedge-funds-have-momentum-after-posting-double-digit-returns-last-year); [Hedgeweek 7-Jul-2026](https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/) | T2 | Anecdotal sequence (n=1) | Jul-2026 | CONTEXT: a capacity/crowding risk flag in the momentum card. No timing rule. |

#### Source list
- J.P. Morgan, Kolanovic and Wei, "Momentum Strategies Across Asset Classes" (Apr-2015): https://www.cmegroup.com/education/files/jpm-momentum-strategies-2015-04-15-1681565.pdf
- J.P. Morgan, Kolanovic and Krishnamachari, "Big Data and AI Strategies" (May-2017): https://bpb-us-e2.wpmucdn.com/faculty.sites.uci.edu/dist/2/51/files/2018/05/JPM-2017-MachineLearningInvestments.pdf
- J.P. Morgan AM Guide to the Markets US, 3Q26: https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/market-insights/guide-to-the-markets/mi-guide-to-the-markets-us.pdf
- J.P. Morgan AM Daily Guide to the Markets (30-Mar-2026): https://am.jpmorgan.com/content/dam/jpm-am-aem/global/en/insights/market-insights/guide-to-the-markets/daily/mi-daily-gtm-us.pdf
- J.P. Morgan AM GTM 2Q24 (adviser-hosted copy): https://www.hiltonheadadvisors.org/assets/Councils/HiltonHead-SC/library/JPMorgan%20Guide%20to%20the%20Markets%20-Merrill%20Lynch%20version2Q24%202024-Mar-31.pdf
- J.P. Morgan AM GTM 4Q20 (adviser-hosted copy): https://www.gillentinegroup.com/wp-content/uploads/2020/12/JP-Morgan-Asset-Management-Guide-to-the-Markets.pdf
- J.P. Morgan AM GTM 1Q16 (adviser-hosted copy): https://www.faswealthpartners.com/wp-content/uploads/2016/03/JP-Morgan-Market-Slides_4Q15.pdf
- BofA, Savita Subramanian interview transcript (May-2024): https://ritholtz.com/2024/05/transcript-savita-subramanian/
- Goldman Sachs Insights, Parker and Lin (12-Feb-2026): https://www.goldmansachs.com/insights/articles/hedge-funds-have-momentum-after-posting-double-digit-returns-last-year
- Investing.com on Goldman Sachs crowding research (21-Nov-2023): https://investing.com/news/stock-market-news/magnificent-7-bets-drive-hedge-fund-crowding-to-record-high-goldman-sachs-3240404
- Hedgeweek (22-Jan-2026): https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind
- Hedgeweek (7-Jul-2026): https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/
- Artificial Finance blog (T3, 11-Aug-2026): https://artificialfinance.org/2026/08/the-ai-momentum-unwind/
- AQR, "Fact, Fiction and Momentum Investing" (2014): https://www.aqr.com/Insights/Research/Journal-Article/Fact-Fiction-and-Momentum-Investing and https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/JPM-Fact-Fiction-and-Momentum-Investing.pdf
- AQR, "Fact, Fiction, and Value Investing" (2015): https://www.aqr.com/Insights/Research/Journal-Article/Fact-Fiction-and-Value-Investing
- AQR, "Craftsmanship Alpha": https://www.aqr.com/-/media/AQR/Documents/Insights/Working-Papers/AQR--Craftsmanship-Alpha.pdf
- AQR, "Is (Systematic) Value Investing Dead?" (May-2020): https://www.aqr.com/-/media/AQR/Documents/Perspectives/Cliffs-Perspective-5620-Is-Systematic-Value-Investing-Dead.pdf?sc_lang=en
- AQR, "That's It, That's the Blog" (Dec-2021): https://www.aqr.com/Insights/Perspectives/Thats-it-Thats-the-Blog
- AQR, "That's It, That's the Update" (Feb-2022): https://www.aqr.com/Insights/Perspectives/thats-it-that-the-update
- AQR, "Value Spreads Are Back to Tech Bubble Highs" (Aug-2022): https://www.aqr.com/Insights/Perspectives/Value-Spreads-Back-to-Tech-Bubble-Highs-Are-You-People-Crazy
- AQR, "You Can't Always Trend When You Want" (2020): https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want
- AQR, "A Century of Evidence on Trend-Following Investing" (2017): https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing
- AQR Managed Futures Strategy Fund (AQMIX): https://funds.aqr.com/funds/alternatives/aqr-managed-futures-strategy-fund
- Research Affiliates, "How Can 'Smart Beta' Go Horribly Wrong?" (2016): https://www.researchaffiliates.com/en_us/publications/articles/442_how_can_smart_beta_go_horribly_wrong.html
- Man Institute, "The Impact of Volatility Targeting": https://www.man.com/maninstitute/the-impact-of-volatility-targeting
- iShares factsheets (30-Jun-2026):
  - MTUM: https://www.ishares.com/us/literature/fact-sheet/mtum-ishares-msci-usa-momentum-factor-etf-fund-fact-sheet-en-us.pdf
  - QUAL: https://www.ishares.com/us/literature/fact-sheet/qual-ishares-msci-usa-quality-factor-etf-fund-fact-sheet-en-us.pdf
  - VLUE: https://www.ishares.com/us/literature/fact-sheet/vlue-ishares-msci-usa-value-factor-etf-fund-fact-sheet-en-us.pdf
  - USMV: https://www.ishares.com/us/literature/fact-sheet/usmv-ishares-msci-usa-min-vol-factor-etf-fund-fact-sheet-en-us.pdf
  - IVV: https://www.ishares.com/us/literature/fact-sheet/ivv-ishares-core-s-p-500-etf-fund-fact-sheet-en-us.pdf
  - MTUM product page: https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf
- SSGA SPY page: https://www.ssga.com/us/en/intermediary/etfs/spdr-sp-500-etf-trust-spy
- Amplify AIEQ: https://amplifyetfs.com/aieq/
- SPIVA US YE2025: https://www.spglobal.com/spdji/en/documents/spiva/spiva-us-year-end-2025.pdf
- SPIVA US page (H1 2026): https://www.spglobal.com/spdji/en/spiva/article/spiva-us/
- SPIVA Europe YE2025: https://www.spglobal.com/spdji/en/documents/spiva/spiva-europe-year-end-2025.pdf
- SPIVA Japan YE2025: https://www.spglobal.com/spdji/en/documents/spiva/spiva-japan-year-end-2025.pdf
- Société Générale Prime Services indices page (2015 snapshot): https://wholesale.banking.societegenerale.com/en/prime-services-indices/
- Daniel and Moskowitz, "Momentum Crashes" (NBER w20439): https://www.nber.org/system/files/working_papers/w20439/w20439.pdf
- Hou, Xue, Zhang, "Replicating Anomalies" (NBER w23394): https://www.nber.org/papers/w23394
- Novy-Marx and Velikov, "A Taxonomy of Anomalies and Their Trading Costs" (NBER w20721): https://www.nber.org/papers/w20721
- Jensen, Kelly, Pedersen, "Is There a Replication Crisis in Finance?" (NBER w28432): https://www.nber.org/papers/w28432
- McLean and Pontiff, Crossref record (SSRN 2012 version): https://api.crossref.org/works?query.bibliographic=Does+Academic+Research+Destroy+Stock+Return+Predictability+McLean+Pontiff&rows=2 ; JF 2016 RePEc: https://ideas.repec.org/a/bla/jfinan/v71y2016i1p5-32.html
- Gu, Kelly, Xiu, "Empirical Asset Pricing via Machine Learning" (NBER w25398): https://www.nber.org/papers/w25398
- Avramov, Cheng, Metzker, "Machine Learning vs. Economic Restrictions" (Management Science 2023): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3450322
- Local data used for E1 calculations: `/home/claude/data_raw/us/shiller_sp500_monthly.csv` (Shiller monthly S&P 500 data: price to Sep-2026, dividends/CPI to Jun-2023, PE10 to Sep-2023); Stocklake MCP daily OHLC for MTUM, SPY, SPHB, USMV (21-Apr-2025 to 1-Oct-2026).

### Inferences

**Cards worth replicating from bank and asset-manager constructs.**

| Proposed card | Construct and origin | Market order | Prior (before → after haircuts) | Verdict |
|---|---|---|---|---|
| F1 Multi-measure value | B/P, E/P, CF/P, S/P z-scores, winsorized ±3, industry-neutral, current price, monthly, buy/hold band (AQR Craftsmanship; Novy-Marx-Velikov) | KRX (OpenDART PIT) → US | Long/short Sharpe 0.26 (AQR, US, IS) → ×0.51 (value decay -49%) → ×0.4 (gate live haircut) ≈ 0.05-0.10 long/short; long-only active IR ≈ 0.05 | BUILD-candidate (low expectation; main use is diversifying momentum, correlation about -0.4) |
| F2 Quality composite | GP/A, ROE, low accruals, low leverage, earnings stability; sector-neutral (MSCI Quality; prior design) | KRX → US | Long/short 0.3-0.5 (prior design) → long-only reality: QUAL -1.0 pts/yr vs S&P over 10y, failed in 2022 → long-only active IR ≈ 0-0.1 | BUILD-candidate as a composite member, not standalone. Flag: lower the US long-only quality weight from 3 to 2. |
| F3 Risk-adjusted momentum + crash controls | 12-1 and 6-1 return ÷ σ252, sector-neutral, monthly, buy/hold band; sigma126 vol target 12%, cap 1.0; Daniel-Moskowitz bear gate (floor 0.5) | US, Europe; KRX only if DC4 passes | Large-cap long/short 0.24-0.33 gross (AQR; macro brief), 0.02 since 2008 → dynamic ×2 uplift (DM, IS) → ×0.77 (momentum decay) → ×0.4 ≈ 0.15-0.25 | BUILD-candidate (US); BACKLOG (KRX, Korean evidence negative) |
| F4 Composite (F1+F2+F3 equal-risk) | Value/momentum negative correlation (AQR) | KRX → US | Multifactor decay -18% → most credible of all | BUILD-candidate (preferred over single-factor cards) |
| C1 Crowding/fragility monitor | Factor realized vol (GS 2026 VaR deleveraging); factor valuation spread (RA/AQR); comomentum; Korean investor-type flow concentration (foreign net-buy share in top names) | KRX, US | No direction; output = multiplier in [0.5, 1.0] for momentum sleeves only | BACKLOG (needs DC5 to pass the gate) |
| C2 Valuation context | CAPE/forward-P/E percentile vs expanding history; 5-10y expected-return band | US (Shiller), KRX (marcap + DART) | 1y R² ≈ 0.05; OOS level failure | CONTEXT (display only); DC2 decides any [0.5, 1.0] use |
| T1 Vol-targeted trend overlay | 6-12m sign + vol target (J.P. Morgan 2015; Man) | ETF sleeves | Single index: about 0 Sharpe uplift post-2015; diversified futures about 3%/yr excess net | CONTEXT (already REJECTED as alpha: E1, B3); keep as drawdown multiplier ≤1.0 |
| X1 Factor-ETF rotation (MTUM/QUAL/VLUE/USMV/SPHB) | Factor timing | US | Timing skill rarely >0.1 Sharpe (AQR); all four lagged IVV 2021-25; 50 bp/side KIS costs | DROP |
| X2 ML/alternative data | J.P. Morgan 2017 | — | Gross academic gains; vanish in liquid, costed universes | DROP for now |
| X3 Enhanced relative momentum (dual momentum) on ETFs | J.P. Morgan Table 8 (0.82 IS) | KRX/US sector ETFs | QUANTGEN E5 sector momentum already REJECT (0.48 vs 0.63) | BACKLOG at most: pre-register ONE configuration to protect the deflated Sharpe |

**Numbers QUANTGEN should treat as priors, and the haircuts to apply.**
- *Any* bank or asset-manager backtest Sharpe: multiply by 0.4-0.5 before using it as a prior. This combines McLean-Pontiff (about 50% post-publication decay, SSRN version) and QUANTGEN's 60% live haircut. Then subtract the cost drag: 2 × cost per side × turnover.
  - Example: J.P. Morgan's 1.21 → about 0.5 before costs, and about 0.3 after the evidence from live funds (AQMIX).
- Long-only factor tilt vs cap-weighted index: active return prior 0 ± 2%/yr, tracking error 5-10%. Evidence: 2016-2026 MSCI ETFs.
- Probability that a rule beats its benchmark over 10 years net: about 15%. Evidence: SPIVA US large-cap (85.59% fail). This is consistent with a strict step-5 gate.
- Valuation → 1-year return: R² 0.05 (CAPE, Shiller) to 0.05-0.08 (GTM forward P/E). For 5 years, use 0.15-0.30, not the post-1990 0.5-0.9.
- Momentum crash budget: assume a 15-20-point relative loss within 5-6 weeks about once every 2-3 years for long-only US momentum (2021, 2023, 2026 episodes). Daniel-Moskowitz show long/short crash months of -50% to -70% in 1932 and 2009.

**Data-check requests for the data lab** (exact tests).
- **DC1 (Shiller, valuation R² decay).**
  - For window ends E ∈ {1990, 2000, 2010, 2015, 2020, 2023}: OLS of forward 1y and 5y real total return (dividends reinvested, CPI-deflated) on log CAPE and log trailing P/E, monthly starts 1881→E.
  - Report R², slope, Newey-West t (lags = horizon in months) and the effective number of independent observations.
  - Then compute Campbell-Thompson out-of-sample R² for every month after E using only pre-E fits.
  - Expected: 1y R² < 0.06 everywhere; OOS R² < 0 for E ≥ 1990.
- **DC2 (Shiller, valuation overlay in QUANTGEN form).**
  - Equity weight = 0.5 if CAPE > its expanding-window 80th percentile (needs ≥ 240 months of history), else 1.0. Flat portion earns cash (Shiller long rate minus 1% as a T-bill proxy if no T-bill series is available; state the proxy).
  - Costs 3 bp per unit of turnover; run all 9 gate steps on 1926-2026, with 1990-2026 as a holdout.
  - Report Sharpe, max drawdown, the step-5 p-value vs buy-and-hold, and years positive.
- **DC3 (trend: Shiller + SPY daily 1998-2021).**
  - Re-run my 12m-sign and 10m-SMA long/flat S&P rules with **month-end** prices instead of monthly averages. Use SPY 1998-2021 to measure the averaging bias: compare signals computed both ways over 1998-2021.
  - Add cash yield and 3 bp per side. Splits: 1927-1991 / 1992-2014 / 2015-2026.
  - Expected: the post-2015 advantage of the 10m SMA (R/V 1.27 vs 1.16) shrinks or disappears with month-end data.
- **DC4 (KRX marcap 1995-2026, bank-style vs academic momentum).**
  - Universe: top 200 KRX stocks by 60-day average traded value, rebuilt monthly; survivorship-free.
  - Signals: (a) raw 12-1; (b) risk-adjusted (12-1 return ÷ σ252) + (6-1 return ÷ σ126), averaged z-scores, size-bucket-neutral (no sector field in marcap).
  - Portfolios: top-30% long-only cap-weighted vs the universe cap-weighted; also decile long/short.
  - Overlays: buy/hold band (enter top 30%, exit below top 50%); then add sigma126 vol scaling (12% target, cap 1.0) and a bear gate (KOSPI-proxy 24-month return < 0 → 0.5).
  - Costs 35 / 70 bp per side; report turnover, gate verdict, the 10 worst months, and returns conditional on the bear state.
- **DC5 (KRX marcap, crowding).** Two tests, rated against the 9 steps as an overlay (multiplier in [0.5, 1.0] only):
  - (i) Comomentum (Lou-Polk style): average pairwise correlation of weekly market-residual returns among winner-decile stocks over the 52-week formation window. Sort months into terciles and test whether the high-comomentum tercile predicts lower next-12-month momentum returns and fatter left tails.
  - (ii) Factor-vol trigger: if 63-day realized vol of the momentum long/short return > its expanding 80th percentile, momentum weight × 0.5. Measure max drawdown and Sharpe change.
- **DC6 (KRX marcap, low volatility).**
  - Bottom-quintile σ252 stocks within the liquid top-200 universe, cap-weighted, monthly, buy/hold band.
  - Report raw excess vs universe, CAPM alpha and beta (vs the universe cap-weighted index), Sharpe at 2x costs, and sub-periods (1997-2007, 2008-2019, 2020-2026).
- **DC7 (Ken French monthly 1926-2018).**
  - (a) UMD Sharpe by sub-period: 1927-1990, 1991-2008, 2009-2018.
  - (b) HML peak-to-trough 2007-2018 and the 2009 UMD crash months.
  - (c) Correlation of UMD and HML, and Sharpe of a 50/50 and a 60/40 HML/UMD mix (checks AQR's -0.4).
  - (d) Volatility-scaled UMD (sigma126 from daily data is unavailable, so use 6-month rolling monthly σ; 12% target, cap 1.0) for 1991-2018 as OOS vs 1927-1990 as IS.
- **DC8 (VIX 1990-2026 + KRX/French).** Does a momentum crash follow high fear? Test whether VIX > 30, or a 1-month VIX change > +50%, at the formation date predicts negative next-month momentum long/short returns (KRX DC4 portfolio; French UMD to 2018). One pre-registered threshold only.
- **DC9 (ETF data via FMP/Yahoo/KIS when available).**
  - Rebuild the total-return calendar-year table for MTUM, QUAL, VLUE, USMV, SPHB vs SPY, 2014-2026.
  - Compute monthly CAPM alpha and beta for USMV and SPHB from 2012, and the worst-5-week relative loss of MTUM by year.
  - Checks whether USMV's raw underperformance is beta (beta 0.49) rather than negative alpha.

**Conflicts with the prior design (flagged, not re-litigated).**
- US time-series momentum weight 3: the bank headline (1.21) has not replicated after publication; QUANTGEN's E1 and B3 rejected it. Suggestion: 3 as a *risk overlay*, 1 as an *alpha source*.
- US quality weight 3: long-only quality evidence is weak (QUAL -1.0 pts/yr over 10y, worse than the market in 2022). Keep 3 only for the long/short, sector-neutral composite; use 2 for long-only.
- US low-volatility weight 2: raw underperformance of about 6 points a year over 10y. Keep 2 as a defensive sleeve only after DC9 shows alpha net of beta.
- Volatility scaling "robust only for momentum" (macro research): Man Group finds Sharpe gains for equities and credit too. QUANTGEN's E2 result is consistent with a small, insignificant uplift. No change proposed.

### Gaps
- **Morgan Stanley** quant crowding research and **Deutsche Bank** "Signal Processing" (Yin Luo) research: not publicly accessible in this session. No claims from either are made.
- **Suhonen-Lennkh-Perez (2017)** bank alternative-beta backtest-vs-live study: not readable (robots/rate limit). This is the single most relevant missing source for haircutting bank QIS backtests. The data lab or the coordinator should obtain it.
- **SG Trend and SG CTA index** calendar-year returns 2015-2026, and the volatility of AQMIX: not obtained. The diversified-trend Sharpe prior (about 0.3) therefore rests on AQMIX excess return plus an assumed 10% volatility.
- **Factor return data:** Ken French and AQR datasets were blocked by proxy policy, so post-2018 long/short factor returns (UMD, HML, HML Devil, QMJ) could not be computed. All post-2018 factor evidence here is long-only ETF data, which mixes factor premia with market beta and sector concentration.
- **SPHB and earlier ETF years:** SPHB long-run returns and MSCI ETF calendar years before 2021 were not obtained.
- **E1 calculation caveats:**
  - The Shiller calculations use monthly-average prices (which flatter timing rules) and approximate dividends after Jun-2023.
  - The Stocklake ETF prices switch feed in late Jul-2026 (volume units change). Prices are continuous, but treat sub-1% differences as noise.
