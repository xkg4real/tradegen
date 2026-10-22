# P7: Technical trading in crypto, FX and futures, and an audit of the practitioner canon (TradingView community scripts, CMT curriculum, classic system books)

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

---

## Q1. Crypto: what credible, out-of-sample, net-of-cost evidence supports technical trading, and what changed with funding rates, calendar effects and the 2024 spot ETFs?

### Takeaway
Crypto has the strongest modern evidence for simple technical trend rules of any market covered here:
- Price-to-MA ratios forecast Bitcoin returns OOS (2010–2018), with break-even one-way costs of 1–4%.
- Thousands of rule variants survive multiple-testing corrections up to 2017.
- Cross-sectional momentum over 1–4 weeks is priced (2014–2018).
- A 28-indicator technical composite earns a large, cost-robust cross-sectional premium among large and liquid coins (2015–2022).

The caveats are serious:
- Almost all of this predates the January 2024 spot-ETF regime.
- The first true OOS check already showed a Bitcoin-specific failure (first half of 2018).
- Calendar anomalies have disappeared.
- Crypto basis and funding are better used as a crash-risk gauge than as a return signal.

### Cited Findings

**Time-series trend and price-to-MA rules (Bitcoin and majors)**
- **Detzel, Liu, Strauss, Zhou & Zhu (Financial Management 50(1), 2021).** Ratios of price to moving averages forecast daily Bitcoin returns both in and out of sample. They raise alpha and Sharpe over buy-and-hold. The authors' equilibrium model shows technical analysis can arise from rational learning, and similar patterns appear in hard-to-value stocks. — [IDEAS/RePEc abstract](https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html)
- **Detzel et al., working-paper numbers.** Sample: BTC, 18 Jul 2010 – 31 Jan 2018; MA lengths 5, 10, 20, 50 and 100 days. These figures come from a copy hosted on a third-party forum and may differ from the published version.
  - OOS R² at the 7-day horizon: individual MA predictors ranged from about −1.3% to 4.2%. The mean-combination forecast ranged from 1.17% to 3.66%, significant at the 5–10% level. VIX, T-bill, term-spread and default-spread predictors all had negative OOS R².
  - Annualised Sharpe: buy-and-hold 1.92; MA strategies 2.09–2.51.
  - Maximum drawdown: buy-and-hold 89.5%; MA strategies 64.3–70.3%.
  - The one-way fee that would eliminate MA alpha was 1.12%–3.96%, with daily turnover of 2.68%–21.75%.
  - Results stayed strong in the second half (Jun 2014 – Jan 2018), even though buy-and-hold Sharpe fell from 2.45 in the first half to 1.45.
  - — [Detzel et al. WP PDF](https://community.portfolio123.com/uploads/short-url/jS0qs8gndLATbD3WlYQ79thDnzD.pdf)
- **Hudson & Urquhart (Annals of Operations Research 297, 2021).** Tested 14,919 rules in five families on daily data for BTC (CoinDesk from 18 Jul 2010; Bitstamp from Dec 2012), LTC, XRP and ETH, all through 31 Dec 2017.
  - All five rule classes produced significant annualised returns.
  - After Bonferroni, Holm, Benjamini-Hochberg and Benjamini-Yekutieli corrections, 20–50% of rules stayed significant.
  - Break-even transaction costs ranged from 7.88 to 147.56 bp, with a large share above 50 bp.
  - In the true OOS window (first half of 2018), returns were negative for Bitcoin but positive for the other three coins.
  - — [Springer](https://link.springer.com/article/10.1007/s10479-019-03357-1)
- **Deprez & Frömmel (International Review of Economics & Finance 93, 2024).** Tested 75,360 simple rules in six classes, at daily and intraday frequency, on bitcoin. Rules were selected after transaction costs using multiple-hypothesis procedures. Portfolios of the selected rules can beat buy-and-hold OOS, mainly on a risk-adjusted basis. The sample dates were not visible in my fetch. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/reveco/v93y2024ipbp858-874.html)
- **Grobys, Ahmed & Sapkota (Finance Research Letters 32, 2020).** Daily data on the 11 most-traded coins, 2016–2018. A 20-day variable-moving-average rule worked; excluding Bitcoin, it earned 8.76% a year in excess return after controlling for the average market return. The abstract mentions no transaction-cost treatment. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finlet/v32y2020ics1544612319308852.html); [Surrey repository abstract](https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Technical-trading-rules-in-the-cryptocurrency/99929028502346)
- **Ahmed, Grobys & Sapkota (FRL 35, 2020).** Ran the same MA design on ten "privacy" coins, 2016–2018. The abstract was truncated in my fetch but indicates that only a variable-MA strategy succeeded. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finlet/v35y2020ics1544612320300829.html)
- **Corbet, Eraslan, Lucey & Sensoy (FRL 31, 2019).** One-minute BTC data, 1 Jan 2014 – 25 Jun 2018, testing variable-MA, MA-oscillator and trading-range-breakout rules. The variable-MA rule performed best, and buy signals earned more than sell signals. The abstract does not mention transaction costs. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612319300315)
- **Liu & Tsyvinski (Review of Financial Studies 34(6), 2689–2727, 2021).** Crypto returns have little exposure to common stock-market and macroeconomic factors. They show strong time-series momentum, and investor-attention proxies forecast them. — [NBER w24877](https://www.nber.org/papers/w24877)
- **Liu & Tsyvinski, 2018 column (working-paper numbers).**
  - A one-standard-deviation rise in the current week's Bitcoin return is associated with a 3.16% higher return over the next week.
  - A one-standard-deviation rise in Google searches is associated with a 1.84% higher next-week return.
  - Only 4 of 155 equity-market factors were significant for crypto returns.
  - — [VoxEU/CEPR column](https://cepr.org/voxeu/columns/risks-and-returns-cryptocurrencies)
- **Red flag from unrefereed work.** An MPRA paper (Sakemoto 2021) reports a weekly OOS R² of 21.26% for Bitcoin from lagged returns (Jul 2015 – Jul 2020, 26-week rolling window, 50 bp costs). — [MPRA PDF](https://mpra.ub.uni-muenchen.de/108283/1/MPRA_paper_108283.pdf)

**Cross-sectional momentum and technical composites**
- **Liu, Tsyvinski & Wu (Journal of Finance 77(2), 2022).** All nine crypto counterparts of equity price and market factors earn significant excess returns. A three-factor model (crypto market, size, momentum) explains them. — [NBER w25882](https://www.nber.org/papers/w25882)
- **Liu, Tsyvinski & Wu, working-paper detail.** Weekly data, 2014–2018; the universe grew from 109 to 1,583 coins with a $1m minimum market cap.
  - Momentum long-short returns per week: 1-week 2.7% (t 1.99), 2-week 3.3% (t 2.44), 3-week 4.1% (t 2.74), 4-week 2.5% (t 2.00).
  - 8-week and 16-week momentum were not significant (0.6% and 0.4%).
  - The market-cap sort gave a significant spread of 3.4% a week in favour of small coins (reported as −3.4% for the long-short).
  - Shorting is impossible or limited for most coins, but results hold with Bitcoin as the short leg.
  - — [NBER WP PDF](https://www.nber.org/system/files/working_papers/w25882/w25882.pdf)
- **Contradicting result.** Grobys & Sapkota (Economics Letters 180, 2019) found no significant momentum payoffs across 143 coins, 2014–2018. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/ecolet/v180y2019icp6-10.html)
- **Fieberg, Liedtke, Poddig, Walker & Zaremba (JFQA 60(7), 3116–3153, 2025), "CTREND".**
  - Construction: CTREND combines 28 technical indicators with a cross-sectional combined elastic net. The indicators are SMAs of 3–200 days, MACD variants, RSI, stochastic K/D, stochRSI, CCI, volume SMAs, volume MACD, Chaikin money flow, and Bollinger bands and band width.
  - Sample: 3,245 coins, Apr 2015 – May 2022 (423 weeks).
  - Full sample: weekly long-short return 3.87% (t 5.19), annualised Sharpe 1.94, alpha against the Liu-Tsyvinski-Wu model 2.62% a week (t 4.22).
  - Top 100 coins by market cap: 3.39% a week (t 4.49). Top 100 most liquid coins: 3.30% a week (t 4.36).
  - Sharpe was significant under the Lo (2002) test in 79% of 55,296 alternative research designs.
  - Individually, more than half of the single indicators were significant. Oscillators were strongest; moving averages and volume indicators were weaker.
  - The authors state the effect survives transaction costs and persists in big, liquid coins.
  - — [Cambridge abstract](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178); [JFQA PDF](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/4C1509ACBA33D5DCAF0AC24379148178/S0022109024000747a.pdf/trend_factor_for_the_cross_section_of_cryptocurrency_returns.pdf)

**Funding rates, basis and perpetual futures**
- **He, Manela, Ross & von Wachter, "Fundamentals of Perpetual Futures" (arXiv 2212.06888, v7 dated 17 Sep 2026).**
  - The mean absolute deviation between perpetual and spot prices is about 52%–90% a year across coins, far above traditional FX.
  - Past spot returns positively predict the futures–spot gap, which the authors read as extrapolative demand for leverage.
  - Deviations co-move across coins and have shrunk by about 22 percentage points a year.
  - Their theory-based "random-maturity" arbitrage earned a Bitcoin Sharpe of 3.35 under high retail costs (3.27 after bid-ask) and 11.65 for fee-free market makers (10.46 after bid-ask).
  - — [arXiv abstract](https://arxiv.org/abs/2212.06888); [arXiv HTML v7](https://arxiv.org/html/2212.06888v7)
- **Schmeling, Schrimpf & Todorov, "Crypto carry" (BIS Working Paper 1087, Mar 2023; sample Mar 2019 – Jan 2022).**
  - Carry levels: futures carry averaged above 10% a year, peaked near 60%, and fell below −20% in troughs. CME BTC carry was 8.7% (1-month) and 8.2% (3-month), against 11.1% and 10.8% on OKEx.
  - High carry predicts later price crashes. As extracted, a $1 higher basis is followed by roughly $5 lower spot (1-month contract) to about $10 lower (3-month contract).
  - High carry also predicts more liquidations. As extracted, a 10% rise in carry goes with 44% more short-futures liquidations relative to open interest over the next month.
  - A CME cash-and-carry trade earned a Sharpe of only 0.59 before costs and faced liquidation risk in more than half of months at 10x leverage.
  - The drivers are trend-chasing small investors seeking leveraged upside and scarce arbitrage capital.
  - — [BIS page](https://www.bis.org/publ/work1087.htm); [BIS PDF](https://www.bis.org/publ/work1087.pdf)

**Weekend, day-of-week and time-of-day effects**
- **Mueller (FRL 64, 2024).** 500+ coins, 28 Apr 2013 – 29 Feb 2024.
  - Bitcoin's Monday effect does not persist after 2015.
  - Weekends show robustly lower trading activity but no abnormal returns.
  - Ethereum's January effect became insignificant, and Halloween effects are inconsistent.
  - — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1544612324004598)
- **Kinateder & Papavassiliou (FRL 38, 2021).** BTC 2013–2019, GARCH model with calendar dummies. They find no day-of-week effect in returns, significantly lower weekend volatility, a reverse January effect and no Halloween effect. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612319311316)
- **Jasiak & Zhong (International Review of Economics & Finance 96, 2024).** Hourly data for only 1 Jan – 28 Jun 2022 (179 days).
  - Intraday patterns line up with equity-market hours. Returns are positive near the Hang Seng open (UTC 1:00) and negative during NYSE hours (UTC 14:00–20:00).
  - Volume and volatility peak during the London–New York overlap.
  - There is no analysis of costs or exploitability.
  - — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1059056024006506)

**After the US spot ETF approvals (Bitcoin 10 Jan 2024; Ethereum Jul 2024)**
- **Babalos, Bouri & Gupta (Quarterly Review of Economics and Finance 102, 2025).** Sample Dec 2017 – 15 Mar 2024, event date 10 Jan 2024. Spot volatility of Bitcoin and XRP fell after the ETF launch; ETH and LTC were unchanged and BTC futures volatility was unaffected. Volatility spilled over from GBTC to BTC futures. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S106297692500047X)
- **Oefele (Economics Letters 250, 2025).**
  - US spot BTC ETP assets grew from about $20bn to over $100bn within a year; iShares held over half by Jan 2025.
  - The average weekly net inflow was 1.4%.
  - Flows respond to current and lagged Bitcoin price changes (about 0.2% net flow per 3.4% price move) and to lagged flows. In other words, flows chase price.
  - — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0165176525001417)
- **Hong, Feng, Wang & Li (arXiv 2512.12815, Dec 2025).** Window Oct 2023 – Apr 2024.
  - There is a structural break toward higher BTC–S&P 500 correlation after approval.
  - The BTC–gold correlation stayed low, and the BTC–dollar correlation was negative or negligible.
  - The window is short, and the paper measures volatility on price levels, which is a weak metric.
  - — [arXiv HTML](https://arxiv.org/html/2512.12815v1)
- **Mehdian, Gherghina & Stoica (Borsa Istanbul Review 25(6), 2025).** Intraday event study.
  - After the BTC ETF approval, BTC return kurtosis fell from 161.24 to 7.39, and the reported total spillover index fell from 691.82 to 403.82.
  - Cross-correlations among cryptocurrencies declined.
  - There was no sell-the-news reversal.
  - — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S221484502500153X)

### Inferences
- **C3 matches the literature.** QUANTGEN's C3 crypto-trend PASS has the same sign and similar size as the literature. C3 shows KRW-BTC OOS Sharpe 1.22 against 0.79 for buy-and-hold (+0.43), and 1.17 at 2x costs; Detzel et al. report +0.2 to +0.6 for BTC MA strategies. The economic source is mostly drawdown avoidance in a volatile, strongly trending asset, not better returns in up-markets.
- **Costs do not bind for slow crypto trend rules.** Detzel's break-even one-way costs of 112–396 bp dwarf QUANTGEN's 10/20 bp. With C3's 13.7x a year turnover, the cost drag is about 1.4% a year at base cost and 2.7% a year at 2x, assuming turnover is counted one-way. Fast rules are different: Hudson-Urquhart's lowest break-evens (about 8 bp) fail even the base cost.
- **The weakest link is regime change.** The evidence mostly ends in 2017–2022. The post-ETF market has lower BTC volatility, higher equity correlation and flows that chase price. Price-chasing flows could sustain trends through feedback. But the FX precedent (Q2) shows cheaper access and institutional adoption can erase simple-rule profits within about a decade. C3 should get a pre-registered split at 10 Jan 2024 and a decay monitor, not more parameter search; every revision would add to the deflated-Sharpe trial count.
- **Bitcoin is not where technical edges are largest.** Grobys et al. found the MA premium outside BTC, Hudson-Urquhart's OOS failure was specific to BTC, and CTREND works across thousands of coins. A cross-sectional technical composite among liquid altcoins is the most promising crypto signal QUANTGEN has not yet tested. Its short side cannot be implemented by a long-only, read-only desk, so it should be tested as long-only top quintile versus BTC.
- **Conflict with the prior design.** Liu-Tsyvinski-Wu document momentum, not reversal, at 1–4 weeks in the crypto cross-section. That conflicts with the prior design's crypto short-term-reversal weight of 2. I found no fetched evidence supporting a 1-week reversal premium in crypto.
- **Use funding and basis as a down-only crowding gauge.** High carry signals crash risk, which fits the macro rule that overlays only cut exposure within [0.5, 1.0]. Perpetual-futures arbitrage needs an order path and its spread is shrinking, so it is CONTEXT only.
- **Drop calendar rules, but fix the daily close.** Crypto trades 24/7, so the daily "close" is a design choice. C3 should be shown to be insensitive to the cut time; a trend edge that depends on the cut hour is fragile.
- **Treat implausible OOS R² as a red flag.** A weekly R² of 21% would be extraordinary, and in unrefereed work it should be read as a sign of look-ahead or overlapping-window errors.

### Gaps
- Pages I could not open:
  - SSRN page for Detzel et al. (HTTP 429), so the published-version numbers are unverified.
  - The Springer article "Cryptocurrency momentum has (not) its moments" (rate-limited).
  - The Wiley JF page for Liu-Tsyvinski-Wu (403).
  - Shen (2022), "Bitcoin intraday time series momentum" (403).
  - Wei et al. (2024), "Cryptocurrencies and Lucky Factors" (403).
  - Kia (2026), "Price Discovery in Bitcoin ETF Market" (403).
- I found no study testing BTC technical-rule profitability after 10 Jan 2024 (a true post-ETF OOS test).
- The sample period of He et al. could not be confirmed from my fetch.
- In the BIS paper, the direction of the liquidation result (long vs short) and the horizon of the basis regression need checking in the PDF.
- I found no peer-reviewed evidence on the funding rate as a directional return predictor at daily horizons.
- The sign of the oscillator signals inside CTREND (momentum-like or reversal-like) was not extracted.

---

## Q2. FX and futures: what is the record of technical trading and trend following?

### Takeaway
FX is the textbook adaptive market. Surveys show almost all dealers use technical analysis, and simple MA and filter rules earned genuine excess returns (about 8% a year) in the 1970s and 1980s. Those returns vanished in major currencies by the early 1990s. G10 technical portfolios have had an OOS Sharpe near zero (0.06) since 1999, negative after modest costs, and the profits migrated to emerging currencies.

Diversified futures trend following has a 135-year record with a net Sharpe of about 0.8 and positive crisis behaviour. But its post-2008 decade disappointed, its single-asset evidence is statistically weak, and much of its edge comes from volatility scaling and from breadth across 50–150 markets, not from any single indicator.

### Cited Findings

**FX technical analysis**
- **Menkhoff & Taylor (Journal of Economic Literature 45(4), 936–972, 2007).** Technical analysis is widespread in FX and may be profitable. Of the four explanations they weigh (irrationality, exploiting official intervention, efficient information processing, identifying non-fundamental influences), the last is judged most plausible. — [AEA](https://www.aeaweb.org/articles?id=10.1257/jel.45.4.936)
- **Neely & Weller survey chapter (St. Louis Fed Working Paper 2011-001).**
  - Usage: in Taylor & Allen (1992), 90% of FX dealers reported using some form of technical analysis. Cheung & Chinn (2001) classify about 30% of US FX traders as technical analysts.
  - Profits: simple MA and filter rules earned about 8% a year on major pairs in the 1970s and 1980s.
  - Decline: Olson (2004), re-optimising over successive 5-year windows from 1971 to 2000, found returns after the 1970s fell to about zero by the 1990s.
  - Costs: institutional FX costs fell from 10–15 bp (1975–79) to about 5 bp (1990s) and 2 bp or less after 2000.
  - Intervention: the authors reject central-bank intervention as the cause of technical profits.
  - — [St. Louis Fed WP PDF](https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf); Olson's bibliographic record (abstract paywalled): [IDEAS/RePEc](https://ideas.repec.org/a/eee/jbfina/v28y2004i1p85-105.html)
- **Neely, Weller & Ulrich (JFQA, 2009).** The excess returns of the 1970s and 1980s were genuine, but they had disappeared by the early 1990s for filter and MA rules. Less-studied rules declined without vanishing completely. The authors read this as support for the adaptive-markets hypothesis over efficient markets. — [UCL GP bibliography abstract](https://gpbib.cs.ucl.ac.uk/gp-html/Neely_2009_JFQA.html)
- **Neely & Weller (Journal of Banking & Finance 37(10), 2013).** FX trading returns dipped in the 1990s and recovered by the end of the decade, and have been markedly better than an equity position since 1998. Rule returns persist, but they have moved to a considerable degree into emerging markets. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jbfina/v37y2013i10p3783-3798.html)
- **Hutchinson, Kyziropoulos, O'Brien, O'Reilly & Sharma (Research in International Business and Finance 63, 2022).**
  - Design: 388 portfolios from filter, MA, channel-breakout and trading-range-breakout rules on G11 currencies, Jan 1980 – Apr 2020. In-sample 1980–1998, OOS 1999–2020.
  - The mean Sharpe fell from 0.66 in-sample to 0.06 OOS.
  - Returns do not survive modest transaction costs OOS.
  - Time-series momentum explains all of the abnormal returns.
  - — [QUB repository PDF](https://pureadmin.qub.ac.uk/ws/portalfiles/portal/370624058/1_s2.0_S0275531922001659_main_1_.pdf)
- **Hsu, Taylor & Wang, "Technical Trading: Is it Still Beating the Foreign Exchange Market?" (conference version).**
  - Design: more than 21,000 rules on 30 currencies (9 developed, 21 emerging), 1971–2015, with a stepwise Superior Predictive Ability test.
  - Full sample: 15 of 30 currencies showed significant predictability (10% level). Annualised returns were 6.5–7.7% for developed currencies and 5.2–16.2% for emerging ones.
  - Over time: 5 of 9 developed currencies were predictable in 1972–76; none were after 1992–96.
  - Costs: profitable rules had break-even costs 6–170 times actual costs.
  - True OOS (rules chosen with data to 2011, tested 2012–2015): developed currencies 1.35% a year (Sharpe 0.24); emerging 7.3% (Sharpe 1.81).
  - — [CICF conference PDF](https://www.cicfconf.org/sites/default/files/paper_412.pdf)
- **Menkhoff, Sarno, Schmeling & Schrimpf (JFE 106(3), 2012).** The cross-sectional currency momentum spread is up to 10% a year. It is partly explained by transaction costs, is limited by strong limits to arbitrage, and differs from carry and from conventional technical rules. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p660-684.html)

**Futures trend following (time-series momentum, TSMOM)**
- **Moskowitz, Ooi & Pedersen (JFE 104(2), 2012).** 58 liquid instruments. Returns persist for 1–12 months and partly reverse at longer horizons. A diversified TSMOM strategy earns large abnormal returns with little exposure to standard factors and does best in extreme markets. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v104y2012i2p228-250.html)
- **Hurst, Ooi & Pedersen, "A Century of Evidence on Trend-Following Investing" (AQR; published in the Journal of Portfolio Management 2017).** Numbers below are from the working-paper version (sample to Dec 2013) hosted on a mirror.
  - Sample: Jan 1880 – Dec 2013, 67 markets (29 commodities, 11 equity indices, 15 bond markets, 12 currency pairs).
  - Returns: gross 14.9% a year; net of 2/20 fees 11.2%; volatility 9.7%; net Sharpe 0.77.
  - Decades: best 1970s (+21.3% net); weakest 1910s (+5.7%).
  - Crises: positive in 8 of the 10 largest 60/40 drawdowns.
  - Correlations: 0.00 with US equities and −0.04 with US 10-year bonds.
  - Assumed one-way costs fell over time: equities 0.34% → 0.06%, commodities 0.58% → 0.10%, currencies 0.18% → 0.03%.
  - Post-2008 performance was "disappointing", which the authors link to higher cross-market correlation.
  - The 10 largest drawdowns ranged from 13.5% to 26.3%.
  - — [Mirror PDF](https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf); [AQR article page](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing)
- **Baltas & Kosowski, "Momentum Strategies in Futures Markets and Trend-following Funds" (working paper).**
  - Sample: 71 futures (26 commodities, 23 equity indices, 7 currencies, 15 bonds), Dec 1974 – Jan 2012.
  - Monthly, weekly and daily TSMOM strategies all had gross Sharpe ratios around or above 1.20.
  - After 2/20 fees, J=1 strategies earned 11–13% a year with a Sharpe of about 0.90.
  - Weekly rebalancing had 3–5 times the turnover of monthly; daily had about 10 times.
  - The authors find no statistically significant capacity constraints.
  - Adding their factors raised the explained share (adjusted R²) of a CTA index from 27% to over 37%.
  - CTA returns in 2009 and 2011 were disappointing.
  - — [NAAIM-hosted PDF](https://www.naaim.org/wp-content/uploads/2013/10/00S_Momentum_Strategies_in_Futures_Markets_Nick_Baltas.pdf)
- **Babu, Levine, Ooi, Pedersen & Stamelos, "Trends Everywhere" (AQR).**
  - Sample: 156 assets (58 traditional, 82 alternative, 16 equity factors), Jan 1985 – Dec 2017.
  - Gross 12-month trend Sharpe: traditional 1.17, alternative 1.34, equity factors 0.95, combined 1.60.
  - Transaction costs were not studied; the authors note they are likely higher for alternative assets.
  - — [Third-party-hosted PDF](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/fd3c53f7-c472-4898-a7e1-f6c100b1b81e.pdf)
- **Babu, Levine, Ooi, Schroeder & Stamelos (Journal of Portfolio Management, Mar 2020).** Trend's post-crisis struggles reflect smaller-than-usual market moves rather than a failure of the strategy, and the authors see little evidence of a permanent structural change. — [AQR](https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want)
- **Lempérière, Deremble, Seager, Potters & Bouchaud, "Two centuries of trend following" (arXiv 1404.3274).** The trend t-statistic is about 5 since 1960 and about 10 since 1800, after accounting for market drift. Long trends show no statistical degradation, but shorter trends have significantly withered. Large signals show a saturation effect. — [arXiv](https://arxiv.org/abs/1404.3274)
- **Huang, Li, Wang & Zhou (JFE 135(3), 2020).** Asset-by-asset regressions show little evidence of TSMOM, in or out of sample. The pooled t-statistic is unreliable once bootstrapped. TSMOM strategy profits match those of a strategy built on historical sample means, which needs no predictability. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html)
- **Kim, Tse & Wald (Journal of Financial Markets 30, 2016).** Without volatility scaling, TSMOM and buy-and-hold have similar cumulative returns and statistically indistinguishable alphas. The apparent TSMOM alpha comes from volatility (risk-parity-like) scaling. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html)
- **Szakmary, Shen & Sharma (Journal of Banking & Finance 34(2), 2010).** 28 commodity futures, 48 years of monthly data. Every parameterisation of dual-MA-crossover and channel rules yields positive mean excess returns net of transaction costs in at least 22 of the 28 markets. Results are robust to data-mining adjustments and to the cost assumptions. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html)
- **SG Trend Index definition.** An equal-weighted index of trend-following managers, reconstituted annually (Bloomberg NEIXCTAT). The page I reached is an old snapshot with no usable return history. — [Société Générale prime services indices](https://wholesale.banking.societegenerale.com/en/prime-services-indices/)

### Inferences
- **QUANTGEN's rejections are consistent with the evidence.** V3 (G10 FX momentum, Sharpe −0.59) and B3 (TSMOM on ten futures, OOS Sharpe 0.08, "no measurable edge after 2009") match the post-1990 FX decay (Hutchinson, Hsu-Taylor-Wang, Neely-Weller-Ulrich) and the disappointing post-2008 trend decade (Hurst; Babu 2020).
- **The prior design is too optimistic for futures and FX.** The headline trend Sharpe ratios come from 58–156 markets, and per-asset predictability is weak (Huang et al.). The prior "0.4–0.8 per asset, ~1.0 diversified" overstates what a ten-market, post-2009 futures book can deliver. For futures and FX it should be corrected to something like 0–0.3 per asset after 2009 (my inference from B3 and Hurst's post-2008 results). Crypto is the exception, with a per-asset Sharpe near 1 (C3, Detzel).
- **Use long lookbacks only in futures and FX.** Lempérière et al. find short trends have withered and long trends have not. Short (7–28 day) lookbacks belong only where they have passed the gate, which so far is crypto (C3).
- **Benchmark trend cards against a vol-scaled long-only portfolio.** Kim-Tse-Wald and Huang et al. imply that much of TSMOM's apparent alpha is volatility scaling plus average drift, so the benchmark should be a vol-scaled long-only portfolio, not raw buy-and-hold. This agrees with the macro research's conclusion that volatility scaling is robust mainly for momentum.
- **FX costs.** QUANTGEN's FX cost of 10 bp per side is a retail level, about five times the post-2000 institutional cost (≤2 bp). An FX rule with an OOS gross Sharpe of about 0.06 cannot survive it.
- **Emerging FX.** EM currencies kept their predictability (Hsu-Taylor-Wang; Neely-Weller 2013). The only EM FX series QUANTGEN can read is USD/KRW (fixing and KRX USD futures), so a single slow-trend test on USD/KRW futures is a defensible BACKLOG item. I could not verify whether KRW is in Hsu-Taylor-Wang's EM set.
- **Old futures-system evidence is historical context only.** It predates the early-1990s decay.

### Gaps
- Olson's (2004) original abstract is paywalled; his findings are taken from Neely & Weller's summary.
- The SG Trend Index annual return history (2000–2026) could not be retrieved (SG data files blocked; the page reached is a 2015 snapshot). I therefore have no verified figures for recent CTA years (e.g., 2022, 2023–2025).
- The Journal of Portfolio Management 2017 version of Hurst et al. was not opened (the AQR PDF link returned 404). Numbers come from the 2014 working-paper mirror.
- I did not verify the OOS figures in Sullivan-Timmermann-White (1999). The commodity-futures data-snooping paper by Marshall, Cahan & Cahan (2008) had no accessible abstract.
- Baltas-Kosowski and "Trends Everywhere" were read from hosted copies, not the journal versions.

---

## Q3. The practitioner canon, item by item: which indicators have peer-reviewed or rigorous out-of-sample tests, and what did they find?

### Takeaway
Only a handful of canon items have peer-reviewed support:
- the trend family: moving averages, MACD, Donchian/channel breakouts, and Wilder's directional/parabolic system in old futures data;
- range-based volatility (ATR);
- nearness to highs (the "near the 52-week high" ingredient in CANSLIM and VCP);
- oscillators used inside a cross-sectional crypto composite.

Most of that support is old (before the early-1990s decay), in-sample, or limited to markets where trend works anyway.

For the rest I found no peer-reviewed, OOS, net-of-cost test in this session. Classic chart patterns (head-and-shoulders) are dominated by simpler rules. Support and resistance have a real microstructure basis, namely order clustering at round numbers, but no demonstrated daily-swing profit.

### Cited Findings

**Canon audit table.** Descriptions of community indicators come from their TradingView script pages and are T3, used only to describe what is computed.

| Item | What it computes | Best rigorous evidence found | Market / period / IS-OOS / gross-net | Main failure modes | QUANTGEN translation |
|---|---|---|---|---|---|
| Moving-average rules; MACD (Appel) | Price vs MA, or the gap between fast and slow EMAs | Brock-Lakonishok-LeBaron 1992; Bajgrowicz-Scaillet 2012; Neely-Rapach-Tu-Zhou 2014; Han-Zhou-Zhu 2016; Detzel et al. 2021; Chong-Ng-Liew 2014 (MACD 12,26) | DJIA 1897–1986: buy signals beat sell signals (IS, gross). DJIA 1897–2011: even in-sample profits vanish with low costs, and winners cannot be picked ex ante. US equity premium forecasting: IS and OOS. US stock cross-section: trend factor more than doubles momentum's Sharpe. BTC: OOS. MACD on Milan/TSX 1976–2002: positive after 1% round trip (IS) | Whipsaw; decay after adoption; zero-cost backtests | Price-to-MA feature (F2). MACD only as a parameterisation inside the trend family |
| Donchian / Turtle channel breakout | Long when the close exceeds the N-day high | Lukac-Brorsen-Irwin 1988 (via Park-Irwin); Szakmary et al. 2010; Hutchinson et al. 2022; Hudson-Urquhart 2021 | 12 futures, OOS 1978–84: channel systems net-profitable. 28 commodities over 48 years: positive net in ≥22 markets. G11 FX OOS 1999–2020: about zero, negative net. Crypto to 2017: significant | Same as trend; the Turtle unit and pyramiding rules add many settings | Channel-position feature (F3); breakout only as a trend variant |
| Wilder RSI | Average up-move vs down-move over n bars, scaled 0–100 | Chong-Ng-Liew 2014; CTREND 2025 (oscillators strongest individually) | Five stock indices 1976–2002: mixed (Italy and Canada yes, Japan no; no data-snooping control). Crypto cross-section 2015–2022: useful inside a composite | Overbought/oversold thresholds are arbitrary; overlaps with short-term reversal | Reversal measure inside the reversal sleeve (F5), not a separate card |
| Wilder ATR | Wilder-smoothed true range | Alizadeh-Brandt-Diebold 2002 (range-based volatility estimators are efficient) | FX daily data (estimation study) | Not a return signal | Risk input for sizing and stops (F1) |
| Wilder ADX/DMI; Parabolic SAR | Directional-movement strength; accelerating trailing stop | Lukac et al. 1988: the "directional parabolic" system was one of 4 of 12 systems that were net-profitable | 12 futures, OOS 1978–84, net 1.89–2.78% a month for the four profitable systems (pre-decay era) | Old evidence; many parameters | Trend strength only as an interaction term. DO-NOT-BUILD as a standalone card |
| Bollinger Bands | MA ± k standard deviations | Leung-Chong 2003 (Bollinger Bands underperform simple MA envelopes); also a CTREND input | Market and period not visible in my fetch; crypto composite 2015–2022 | Mean-reversion and breakout readings conflict | Band width only, as a volatility-compression input (F4). %B equals a reversal z-score (F5) |
| Ichimoku | Lines from midpoints of N-day high-low ranges, with some spans shifted forward or back in time | None found. TradingView docs list Ichimoku-type plotting into the past as potentially misleading repainting | n/a | Time offsets invite look-ahead | DO-NOT-BUILD as a system. Its midlines equal channel position (F3) |
| VWAP | Volume-weighted average price for the session | No alpha test found | n/a | Intraday concept; daily approximations are poor | Intraday BACKLOG (F6); execution benchmark |
| Pivot points / support–resistance | Levels from the prior period's high, low and close; round numbers | Osler 2000 (FRBNY); Osler 2003 (JF) | FX intraday, Jan 1996 – Mar 1998: trends stalled at published levels 60.8% of the time vs 56.2% at arbitrary levels. Orders cluster at round numbers. Profitability not tested | Not a daily-swing signal | CONTEXT. DO-NOT-BUILD for daily swing |
| Supertrend | Trend state from an ATR band with hysteresis | None found | n/a | Parameter-tuned; repaints if computed intrabar | Variant of trend with hysteresis (F8), counted as a trial |
| TTM / LazyBear Squeeze Momentum | Squeeze on when Bollinger Bands sit inside Keltner Channels; momentum histogram from a linear regression (T3) | None found | n/a | Visual signal with many settings | Compression as a conditioning variable (F4), BACKLOG |
| UT Bot | ATR trailing stop scaled by a "key value"; optional Heikin Ashi input (T3) | None found | n/a | Heikin Ashi option means synthetic prices | Variant of F8. DO-NOT-BUILD on Heikin Ashi |
| WaveTrend | EMA-smoothed, CCI-like oscillator on hlc3 with overbought/oversold crossovers (T3) | None found | n/a | Arbitrary overbought/oversold levels | Covered by F5. DO-NOT-BUILD separately |
| Connors RSI(2) | Very short RSI used for buying dips (no source fetched) | None found | n/a | Practitioner-only evidence; overlaps reversal | F5 × F2 interaction test on KRX (BACKLOG) |
| DeMark TD Sequential | Count-based exhaustion setups (no source fetched) | None found | n/a | Discretionary counting rules | DO-NOT-BUILD |
| Wyckoff / volume spread analysis | Phase labels and volume–range reading (no source fetched) | Indirect: Gervais-Kaniel-Mingelgrin 2001; Lee-Swaminathan 2000 | US stocks: unusually high volume predicts higher returns over the next month; volume speeds up momentum reversals | Subjective labels | Abnormal-volume feature (F7). DO-NOT-BUILD phase labels |
| Elliott waves; Fibonacci | Wave counts; retracement ratios (no source fetched) | None found | n/a | Subjective and unfalsifiable | DO-NOT-BUILD |
| O'Neil CANSLIM; Minervini VCP | Composites of earnings growth, new highs, volume, relative strength and market direction; VCP = shrinking volatility near highs (no source fetched) | Components only: George-Hwang 2004 (52-week high); Han-Zhou-Zhu 2016; Gervais-Kaniel-Mingelgrin 2001 | US stocks | A composite has many degrees of freedom | Decompose into near_52wh (F3), F4, F7, plus earnings drift (another panel) |
| "Machine Learning: Lorentzian Classification" | k-nearest-neighbours with Lorentzian distance on RSI, WaveTrend, CCI and ADX; up to 2,000 bars of history; several filters (T3) | None found | n/a | Overfitting risk; assumes mid-bar entries; the author says its Trade Stats are not a backtest | DO-NOT-BUILD. Machine learning only through a purged cross-sectional composite (F10) |
| Chart patterns (head-and-shoulders, etc.) | Pattern recognition | Chang-Osler 1999; Lo-Mamaysky-Wang 2000 | FX 1973–94: profitable but dominated by simpler rules. US stocks 1962–96: some incremental information | Subjective; dominated by simple trend rules | DO-NOT-BUILD pattern recognisers |

**Sources behind the table and the canon verdicts**
- **Park & Irwin (Journal of Economic Surveys 21(4), 2007).** Of 95 modern studies, 56 found positive results for technical trading, 20 negative and 19 mixed. Technical strategies were profitable in FX and futures, but not stocks, in early studies, and generated profits across speculative markets at least until the early 1990s. Testing problems include data snooping, ex post selection of rules and difficulty estimating risk and costs. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jecsur/v21y2007i4p786-826.html)
- **Park & Irwin review, earlier AgMAS version (92 studies: 58 positive, 24 negative, 10 mixed).** It describes Lukac, Brorsen & Irwin (1988), who tested 12 systems on 12 futures markets over 1975–84 with OOS testing over 1978–84.
  - 7 of the 12 systems had significant gross returns.
  - 4 had significant net returns of 1.89–2.78% a month: close channel, directional parabolic, MII price channel and dual-MA crossover.
  - The profits were not explained by CAPM risk.
  - — [Illinois AgMAS PDF](https://farmdoc.illinois.edu/assets/marketing/agmas/AgMAS04_04.pdf)
- **Brock, Lakonishok & LeBaron (JF 47(5), 1992).** MA and trading-range-break rules on the DJIA, 1897–1986. Buy signals consistently earned more than sell signals, and returns after sell signals were negative. The results are inconsistent with random-walk, AR(1), GARCH-M and EGARCH bootstrap models. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html)
- **Sullivan, Timmermann & White (JF 54(5), 1999).** Applied White's Reality Check bootstrap to 100 years of daily DJIA data, extending Brock et al.'s 26 rules to a much larger universe. Detailed figures were not visible in my fetch. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v54y1999i5p1647-1691.html)
- **Bajgrowicz & Scaillet (JFE 106(3), 2012).** DJIA 1897–2011, using false-discovery-rate control. Persistence tests show an investor could never have selected the future best-performing rules ex ante. Even in-sample, low transaction costs completely offset performance. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html)
- **Neely, Rapach, Tu & Zhou (Management Science 60(7), 2014).** MA, momentum and on-balance-volume indicators forecast the US equity risk premium in and out of sample, matching or beating macro variables. Technical indicators capture declines near business-cycle peaks, macro variables work near troughs, and combining the two improves forecasts. — [IDEAS/RePEc](https://ideas.repec.org/a/inm/ormnsc/v60y2014i7p1772-1791.html)
- **Han, Zhou & Zhu (JFE 122(2), 2016).** A trend factor built from moving averages over short, intermediate and long horizons more than doubles the Sharpe ratio of momentum and other factors in the US stock cross-section. In 2008 it earned +0.75% a month while momentum lost −3.88%. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html)
- **George & Hwang (JF 59(5), 2004).** Nearness to the 52-week high explains a large part of momentum profits, forecasts better than past returns, and does not reverse in the long run. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v59y2004i5p2145-2176.html)
- **Lo, Mamaysky & Wang (JF 55(4), 2000).** Kernel-regression pattern recognition on US stocks, 1962–1996. Several technical patterns provide incremental information. — [NBER w7613](https://www.nber.org/papers/w7613)
- **Chang & Osler (Economic Journal 109(458), 1999).** A head-and-shoulders rule on daily dollar exchange rates, 1973–1994, was profitable and replicable in real time, but not efficient, because simpler trading rules dominate it. — [IDEAS/RePEc](https://ideas.repec.org/a/ecj/econjl/v109y1999i458p636-61.html)
- **Osler (FRBNY Economic Policy Review, 2000).**
  - Data: support and resistance levels published by six firms, Jan 1996 – Mar 1998, for DEM, JPY and GBP against USD, using one-minute quotes from 9:00 to 16:00 New York time.
  - Intraday trends were interrupted at published levels 60.8% of the time, against 56.2% at artificial levels. The difference was significant at 5% for 13 of 16 firm-currency pairs.
  - 96% of the published levels ended in 0 or 5.
  - Profitability was not assessed.
  - — [FRBNY PDF](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf)
- **Osler (JF 58(5), 2003).** Take-profit orders cluster at round numbers and stop-loss orders cluster just beyond them. This explains why trends tend to reverse at support and resistance and to accelerate once a level is crossed. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v58y2003i5p1791-1819.html)
- **Chong, Ng & Liew (Journal of Risk and Financial Management 7(1), 2014).** Five OECD stock indices, 1976–2002.
  - MACD(12,26,0) produced significant abnormal returns on Milan and the S&P/TSX.
  - RSI(21,50) was profitable on Milan and Canada.
  - Rules were ineffective on the Nikkei.
  - MACD stayed profitable after 1% round-trip costs on Milan and Canada.
  - — [MDPI](https://www.mdpi.com/1911-8074/7/1/1)
- **Leung & Chong (Applied Economics Letters 10(6), 2003).** Bollinger Bands, despite reacting to sudden volatility, earned less than simple moving-average envelopes. — [IDEAS/RePEc](https://ideas.repec.org/a/taf/apeclt/v10y2003i6p339-341.html)
- **Ding, Mazouz, ap Gwilym & Wang (2023).**
  - Signals from 2,127 technical strategies on the S&P 500 and DJIA (Jan 1964 – Dec 2019) were averaged into a daily sentiment index.
  - The index tracks VIX and survey-based sentiment, predicts near-term returns positively and long-term returns negatively.
  - Only 4 of 16 portfolios had break-even costs above 25 bp.
  - — [Cardiff ORCA PDF](https://orca.cardiff.ac.uk/id/eprint/161200/1/TA%20sentiment_20230405.pdf)
- **Gervais, Kaniel & Mingelgrin (JF 56(3), 2001).** Stocks with unusually high (low) volume over a day or week tend to rise (fall) over the following month, which the authors attribute to visibility. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html)
- **Lee & Swaminathan (JF 55(5), 2000).** High-volume winners and losers reverse faster. Past turnover links momentum and value. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v55y2000i5p2017-2069.html)
- **Alizadeh, Brandt & Diebold (JF 57(3), 2002).** Range-based volatility proxies are highly efficient, approximately Gaussian and robust to microstructure noise. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v57y2002i3p1047-1091.html)
- **Community script descriptions (T3, used only for what the scripts compute).**
  - Squeeze Momentum [LazyBear], 4 Jul 2014: squeeze when Bollinger Bands are inside Keltner Channels; derived from John Carter's TTM Squeeze; momentum histogram based on linear regression. — [TradingView script page](https://www.tradingview.com/script/nqQ1DT5a-Squeeze-Momentum-Indicator-LazyBear/)
  - WaveTrend [LazyBear], 27 May 2014: EMA of hlc3; EMA of the absolute deviation; CI = (ap − esa)/(0.015·d); signal = EMA of CI; crossovers of WT1/WT2 at overbought/oversold bands; a port of a TradeStation/MetaTrader indicator. — [TradingView script page](https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/)
  - UT Bot Alerts (QuantNomad, 8 Feb 2020; originally Yo_adriiiiaan, concept from HPotter): ATR trailing stop multiplied by a key value, with an optional Heikin Ashi source. — [TradingView script page](https://www.tradingview.com/script/n8ss8BID-UT-Bot-Alerts/)
  - Machine Learning: Lorentzian Classification (jdehorty, 23 Jan 2023): k-nearest-neighbours with Lorentzian distance; features RSI, WaveTrend, CCI and ADX; up to 2,000 bars back; volatility, regime, ADX, EMA/SMA and kernel-regression filters. The author states the Trade Stats are "NOT meant to be used as a substitute for proper backtesting" and assume mid-bar entries. — [TradingView script page](https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/)
- **CMT Association program.**
  - Three levels taken in sequence: Level I covers terminology and analytical tools, Level II application, Level III integration and practical application.
  - The program describes itself as addressing behavioural finance, quantitative systems design and risk management, and points candidates to a Nasdaq Dorsey Wright tool for building and testing relative-strength strategies.
  - — [CMT Association](https://cmtassociation.org/chartered-market-technician/)

### Inferences
- **The canon reduces to three primitives.** Each primitive already has its own literature:
  - Trend: MA, MACD, Donchian, Supertrend, UT Bot, Parabolic SAR, Ichimoku midlines.
  - Short-term reversal: RSI, Connors RSI(2), %B, WaveTrend, stochastic, CCI.
  - Volatility and range: ATR, Bollinger width, Keltner, Squeeze, VCP.
  
  Indicator names are mostly brand names for parameter choices. QUANTGEN should test each primitive once, let the gate's plateau test (step 7) cover neighbouring parameterisations, and count every named variant as a trial in the deflated Sharpe (step 3).
- **Whether an indicator "works" depends on the market, not the indicator.** The same MA rule is positive in crypto (to 2022) and commodities, near zero in G10 FX after 1999, and cost-dominated on the DJIA. That is why QUANTGEN's per-market signal weights are the right architecture.
- **Old evidence for Wilder's systems.** The best evidence for Wilder's Parabolic/DMI-style systems comes from the late 1970s and early 1980s, before the decay that Park-Irwin and Neely-Weller-Ulrich document. It cannot support a modern standalone card.
- **Support and resistance is real microstructure, not a daily signal.** Order clustering at round numbers is genuine, but the evidence is intraday FX with no profitability test. For KRX the analogue would be round-number price levels and tick-size boundaries, which is too speculative to build.
- **The CMT curriculum is a vocabulary, not evidence.** It teaches the canon and mentions systems design and testing, but I could not verify how far it requires costed OOS testing. Holding the CMT credential is no evidence that any rule works.

### Gaps
- I found no peer-reviewed OOS test, within this session's tools, for Ichimoku, Supertrend, TTM/LazyBear Squeeze, UT Bot, WaveTrend, Connors RSI(2), TD Sequential, Wyckoff/VSA, Elliott waves, Fibonacci, CANSLIM or VCP as systems, or Lorentzian Classification. I believe practitioner-journal studies exist for some of these (for example IFTA-journal work on Ichimoku), but I could not open them and do not cite them.
- The detailed CMT curriculum pages (topics and weights by level) were blocked by robots rules.
- The VWAP benchmark literature (Berkowitz-Logue-Noser 1988) could not be opened (404).
- The market and period for Leung-Chong (2003) were not visible.

---

## Q4. Backtest realism on charting platforms: how TradingView fills, repaints and charges costs, and how many community strategies would survive a costed, out-of-sample test

### Takeaway
TradingView's own documentation shows how optimistic its backtests are by default:
- More than 95% of indicators repaint in some form.
- A higher-timeframe request with lookahead and no offset leaks the future.
- Backtests on non-standard charts (Heikin Ashi, Renko and similar) fill at synthetic prices.
- Fills inside a bar follow an assumed price path unless the paid "Bar Magnifier" is used.
- Pine v5 strategies defaulted to zero margin, changed to 100% in v6.
- Realistic commission and slippage depend on the author, as the publishing rules require.

I found no systematic study of TradingView's published strategies. The nearest evidence comes from the Quantopian algorithm library, FX rule universes and data-snooping studies, and all of it implies that only a small minority of backtested strategies would survive a costed OOS test.

### Cited Findings

**How the TradingView broker emulator fills orders**
- **Intrabar price path.** For historical bars, the emulator infers the path inside a bar. If the open is closer to the high, it assumes the price went open → high → low → close; otherwise it assumes the reverse. — [Pine Script docs: Strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/)
- **Default fill timing.** By default an order fills at the next available tick, which on historical bars means the open of the following bar. — [Pine Script docs: Strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/)
- **Bar Magnifier.** `use_bar_magnifier` makes the emulator use lower-timeframe OHLC data for more precise fills. It is available on Premium and Ultimate plans only. — [Pine Script docs: Strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/)
- **Non-standard charts.** By default, strategy results on non-standard charts such as Heikin Ashi do not reflect actual market conditions, because they use synthetic prices. `fill_orders_on_standard_ohlc` lets Heikin Ashi strategies fill at real prices. — [Pine Script docs: Strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/)
- **Where costs live.** The strategy report's Properties tab lists initial capital, order size, leverage, pyramiding, commission and slippage. The page has dedicated "Trading costs → Commission / Slippage" subsections. — [Pine Script docs: Strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/)

**Repainting and look-ahead**
- **Scale of repainting.** TradingView estimates that more than 95% of indicators in existence exhibit some form of repainting.
- **Heavily misleading cases.** The docs name three: scripts that leak future information into the past, strategies on non-standard charts, and scripts that use realtime intrabars for alerts or orders.
- **Potentially misleading cases.** Plotting values into the past with offsets, including Ichimoku-type and pivot-based scripts.
- **Avoidance.** The docs recommend `barstate.isconfirmed` or referencing the prior bar with `[1]`.
- — [Pine Script docs: Repainting](https://www.tradingview.com/pine-script-docs/concepts/repainting/)
- **Lookahead in `request.security()`.** The default is `barmerge.lookahead_off`. Using `lookahead_on` without offsetting the expression leaks future data into historical bars. The docs call this extremely misleading and prohibit it in published scripts. The non-repainting idiom combines `lookahead_on` with a `[1]` offset. On realtime bars both settings return the unconfirmed higher-timeframe value, so the result repaints unless offset. — [Pine Script docs: Other timeframes and data](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/)
- **Emulator settings that introduce repainting.** Changing emulator behaviour, for example `calc_on_every_tick` or `process_orders_on_close`, typically introduces repainting, and processing orders on the bar close may not give accurate results. — [Pine Script docs: Strategies FAQ](https://www.tradingview.com/pine-script-docs/faq/strategies/)
- **Margin default.** Pine v6 changed the default strategy margin to 100% for longs and shorts. In v5 the defaults were 0, meaning no check on available funds. — [Pine Script docs: Migration guide to v6](https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/)

**Publishing rules and platform documentation**
- **TradingView rules for publishing strategies.** Authors must:
  - use realistic initial capital, and commission and slippage that match expected costs for the instrument;
  - use realistic margin (a margin of 0 is called unrealistic);
  - simulate a reasonable number of trades, in most cases more than 100;
  - explain the default Properties settings and use them in the published report;
  - not publish `request.security()` calls with `lookahead_on` or strategies on non-standard chart types;
  - resolve strategy-report caution warnings.
  - — [TradingView script publishing rules](https://www.tradingview.com/support/solutions/43000590599-script-publishing-rules/)
- **TradingView's support article on strategies, backtesting and forward testing** contains no warning about costs or repainting. — [TradingView support](https://www.tradingview.com/support/solutions/43000562362-what-are-strategies-backtesting-and-forward-testing/)

**Survival evidence for large libraries of backtested strategies**
- **Wiecki, Campbell, Lent & Stauth (Quantopian, 2016).** 888 algorithms with at least 6 months of OOS data.
  - Backtest Sharpe had almost no power to predict OOS Sharpe (R² < 0.025).
  - Volatility and maximum drawdown were more predictive.
  - More backtesting produced a larger gap between backtest and OOS results.
  - Non-linear classifiers using many backtest features reached an R² of 0.17.
  - — [SSRN 2745220](https://ssrn.com/abstract=2745220)
- **Bailey, Borwein, López de Prado & Zhu (Notices of the AMS 61(5), 2014).** High simulated performance is easy to reach after trying a relatively small number of configurations. When returns have memory, backtest overfitting implies negative expected OOS returns rather than zero. — [SSRN 2308659](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659)
- **Harvey & Liu (Journal of Portfolio Management, Fall 2015).** Multiple-testing haircuts to Sharpe are non-linear. An annualised Sharpe of 0.75 over 20 years of monthly data with 200 strategies tried falls to about 0.32, a haircut of roughly 60%. Sharpe ratios below 0.4 lose more than half; those above 1.0 lose about 25%. — [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF)
- **Hutchinson et al. (2022).** In 388 FX rule portfolios the mean Sharpe dropped from 0.66 to 0.06 OOS. **Bajgrowicz & Scaillet (2012)** found the future best DJIA rules could never be picked ex ante. — see Q2 and Q3 for links.

**Retail outcomes (base rates for "technical traders")**
- **Hoffmann & Shefrin (Journal of Economic Behavior & Organization 107, 2014).** Dutch discount-broker clients, 2000–2006. Investors who used technical analysis earned lower returns, traded more, used more options and held more concentrated portfolios. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jeborg/v107y2014ipbp487-511.html)
- **Barber, Lee, Liu & Odean, "The Cross-Section of Speculator Skill" (working paper).** Taiwan day traders, 1992–2006. Fewer than 1% earned reliably positive abnormal returns net of fees; the working paper reports that about 85% lose money net of costs. — [Berkeley Haas PDF](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20Skill%20110523.pdf)
- **Chague, De-Losso & Giovannetti, "Day Trading for a Living?" (2020).** Brazilian equity-futures day traders who started in 2013–2015. Of those who persisted beyond 300 days, 97% lost money, only 1.1% earned more than the minimum wage, and 0.5% earned more than an entry-level bank teller. — [SSRN 3423101](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101)
- **ESMA (27 Mar 2018).** 74–89% of retail CFD accounts lose money, with average losses of €1,600 to €29,000 per client. Leverage caps were set at 30:1 for major FX pairs and 2:1 for crypto. — [ESMA](https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors)

### Inferences
- **Default costs.** The publishing rules require authors to set commission and slippage, and the Properties tab exposes them. This implies the engine does not impose realistic costs by default; my understanding is that the default commission and slippage are zero, but I could not verify those defaults in the documentation in this session. Bajgrowicz-Scaillet show that adding even low costs removes in-sample technical profits on the DJIA. A zero-cost TradingView equity curve is therefore uninformative.
- **How a ported script can mislead.** Each mechanism below can manufacture apparent profit:
  - A same-bar fill (`process_orders_on_close`) decides and fills on the same close, which breaks QUANTGEN's t → t+1 rule.
  - A higher-timeframe value requested with lookahead and no offset uses data from the future.
  - A pivot or ZigZag level confirmed with a lag but plotted at the pivot bar shows the signal earlier than it was knowable.
  - A Heikin Ashi or Renko series fills at synthetic prices.
  - When a stop and a target sit inside the same bar, the assumed intrabar path decides which fills first. Without Bar Magnifier, which is paid, that assumption is decisive.
- **Survival share of community strategies.** No systematic study exists that I could find, so this is my inference. Evidence from large rule universes suggests OOS Sharpe ratios cluster near zero: 0.06 in Hutchinson's FX universe and R² < 0.025 in Quantopian. Under QUANTGEN's gate (deflated Sharpe ≥ 0.95 with trials counted, PBO ≤ 0.05, positive at 2x costs, 60% of years positive), I would expect only a small minority, plausibly in the low single-digit percent, of published community strategies to PASS. This is a reasoned estimate, not a measured number.
- **Platform standards versus QUANTGEN's gate.** TradingView's "more than 100 trades" bar is far weaker than QUANTGEN's gate. A strategy with 100 trades and an apparent Sharpe of 1 over a few years is well within the range that Harvey-Liu-style haircuts and the Bailey et al. minimum-backtest-length argument would treat as noise once several configurations have been tried.
- **Display a base rate.** QUANTGEN's public cards could show retail base rates (Taiwan, Brazil, ESMA) beside any strategy derived from TradingView. This fits its "publish what fails" ethos.

### Gaps
- I could not verify TradingView's default `commission_value`, `slippage`, `initial_capital` or `default_qty` values, or whether slippage applies to limit orders; the "Trading costs" subsections were truncated in every fetch and direct downloads were blocked by the proxy.
- I found no academic or systematic study of TradingView's public script library or of other retail strategy marketplaces (MQL5, cTrader, crypto copy-trading). arXiv search was blocked by robots rules in this session.
- The published-journal version of the Quantopian study was not opened.

---

## Q5. Translating indicator logic into testable QUANTGEN features, and what to put on the DO-NOT-BUILD list

### Takeaway
Build three primitive feature families once, point-in-time at the close of day t: trend/position, short-term reversal, and range-based volatility. Add abnormal volume and, for crypto, a funding/basis crowding gauge. Use ATR as a risk and stop input, not a signal, and apply stops only to trend sleeves. Test volatility compression only as a conditioning variable for breakouts. Put every repainting, look-ahead, synthetic-chart, subjective or monolithic "system" item on DO-NOT-BUILD.

### Cited Findings (evidence anchors for the design)
- **Kaminski & Lo (Journal of Financial Markets 18, 2014).** They give a framework for when stop-loss rules add or subtract value. Their benefit depends on serial correlation (momentum) rather than a random walk. In daily index-futures data, some stop-loss policies at longer sampling frequencies raised expected return while sharply cutting volatility. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html)
- **Nagel (Review of Financial Studies 25(7), 2012).** Short-term reversal returns are compensation for supplying liquidity. They are highly predictable from VIX and rise in market stress. — [IDEAS/RePEc](https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html)
- **Jegadeesh (JF, 1990).** Negative first-order serial correlation in monthly stock returns is highly significant. Over 1934–87, the extreme-decile spread was 2.49% a month. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v45y1990i3p881-98.html)
- **Gao, Han, Li & Zhou (JFE 129(2), 2018).** On SPY, 1993–2013, the first half-hour return (measured from the prior close) predicts the last half-hour return. The effect is stronger on volatile, high-volume, recession and macro-announcement days. — [IDEAS/RePEc](https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html)
- **Gu, Kelly & Xiu (Review of Financial Studies 33(5), 2020).** Across machine-learning methods, momentum, liquidity and volatility are the most consistent predictors. Trees and neural networks capture interactions. — [NBER w25398](https://www.nber.org/papers/w25398)
- **Other anchors already cited:** Alizadeh-Brandt-Diebold 2002 (range volatility), George-Hwang 2004 (52-week high), Han-Zhou-Zhu 2016 (MA trend factor), Detzel et al. 2021 (BTC price/MA), Fieberg et al. 2025 (CTREND), Schmeling-Schrimpf-Todorov 2023 (crypto carry and crash risk), Gervais-Kaniel-Mingelgrin 2001 (abnormal volume), Neely-Rapach-Tu-Zhou 2014 (technical index-level forecasts work near peaks).

### Inferences: the QUANTGEN design

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

### Gaps
- No peer-reviewed evidence was found for volatility compression (F4) or VWAP distance (F6) as return predictors, so both remain BACKLOG with a pre-registered kill rule.
- The thresholds for the funding/basis multiplier (F9) have no published calibration that I could verify, so they must be set before testing and counted as trials.

---

## Where and when it failed (mandatory)

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

## Data-check requests for the data lab

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

## Claims ledger

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

---

## Source list

**Crypto**
- Liu & Tsyvinski, Risks and Returns of Cryptocurrency (RFS 2021) — https://www.nber.org/papers/w24877
- Liu & Tsyvinski, VoxEU column (2018) — https://cepr.org/voxeu/columns/risks-and-returns-cryptocurrencies
- Liu, Tsyvinski & Wu, Common Risk Factors in Cryptocurrency (JF 2022) — https://www.nber.org/papers/w25882 ; WP PDF https://www.nber.org/system/files/working_papers/w25882/w25882.pdf
- Detzel, Liu, Strauss, Zhou & Zhu (FM 2021) — https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html ; WP PDF https://community.portfolio123.com/uploads/short-url/jS0qs8gndLATbD3WlYQ79thDnzD.pdf
- Grobys, Ahmed & Sapkota (FRL 2020) — https://ideas.repec.org/a/eee/finlet/v32y2020ics1544612319308852.html ; https://openresearch.surrey.ac.uk/esploro/outputs/journalArticle/Technical-trading-rules-in-the-cryptocurrency/99929028502346
- Ahmed, Grobys & Sapkota (FRL 2020, privacy coins) — https://ideas.repec.org/a/eee/finlet/v35y2020ics1544612320300829.html
- Grobys & Sapkota, Cryptocurrencies and momentum (Econ Letters 2019) — https://ideas.repec.org/a/eee/ecolet/v180y2019icp6-10.html
- Hudson & Urquhart, Technical trading and cryptocurrencies (AOR 2021) — https://link.springer.com/article/10.1007/s10479-019-03357-1
- Corbet, Eraslan, Lucey & Sensoy (FRL 2019) — https://www.sciencedirect.com/science/article/abs/pii/S1544612319300315
- Deprez & Frömmel (IREF 2024) — https://ideas.repec.org/a/eee/reveco/v93y2024ipbp858-874.html
- Fieberg et al., CTREND (JFQA 2025) — https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/trend-factor-for-the-cross-section-of-cryptocurrency-returns/4C1509ACBA33D5DCAF0AC24379148178 ; PDF https://www.cambridge.org/core/services/aop-cambridge-core/content/view/4C1509ACBA33D5DCAF0AC24379148178/S0022109024000747a.pdf/trend_factor_for_the_cross_section_of_cryptocurrency_returns.pdf
- He, Manela, Ross & von Wachter, Fundamentals of Perpetual Futures (arXiv v7, 2026) — https://arxiv.org/abs/2212.06888 ; https://arxiv.org/html/2212.06888v7
- Schmeling, Schrimpf & Todorov, Crypto carry (BIS WP 1087, 2023) — https://www.bis.org/publ/work1087.htm ; https://www.bis.org/publ/work1087.pdf
- Mueller, Revisiting seasonality in cryptocurrencies (FRL 2024) — https://www.sciencedirect.com/science/article/pii/S1544612324004598
- Kinateder & Papavassiliou, Calendar effects in Bitcoin (FRL 2021) — https://www.sciencedirect.com/science/article/abs/pii/S1544612319311316
- Jasiak & Zhong, Intraday and daily dynamics of cryptocurrency (IREF 2024) — https://www.sciencedirect.com/science/article/pii/S1059056024006506
- Babalos, Bouri & Gupta (QREF 2025) — https://www.sciencedirect.com/science/article/pii/S106297692500047X
- Oefele, One year of bitcoin spot ETPs (Econ Letters 2025) — https://www.sciencedirect.com/science/article/pii/S0165176525001417
- Hong, Feng, Wang & Li (arXiv 2025) — https://arxiv.org/html/2512.12815v1
- Mehdian, Gherghina & Stoica (Borsa Istanbul Review 2025) — https://www.sciencedirect.com/science/article/pii/S221484502500153X
- Sakemoto (MPRA 2021), cited as a red-flag example — https://mpra.ub.uni-muenchen.de/108283/1/MPRA_paper_108283.pdf

**FX and futures**
- Menkhoff & Taylor (JEL 2007) — https://www.aeaweb.org/articles?id=10.1257/jel.45.4.936
- Neely, Weller & Ulrich (JFQA 2009), abstract — https://gpbib.cs.ucl.ac.uk/gp-html/Neely_2009_JFQA.html
- Neely & Weller, Technical Analysis in the Foreign Exchange Market (St. Louis Fed WP 2011-001) — https://files.stlouisfed.org/files/htdocs/wp/2011/2011-001.pdf
- Neely & Weller, Lessons from the evolution of FX trading strategies (JBF 2013) — https://ideas.repec.org/a/eee/jbfina/v37y2013i10p3783-3798.html
- Olson (JBF 2004), bibliographic record — https://ideas.repec.org/a/eee/jbfina/v28y2004i1p85-105.html
- Hutchinson et al. (RIBAF 2022) — https://pureadmin.qub.ac.uk/ws/portalfiles/portal/370624058/1_s2.0_S0275531922001659_main_1_.pdf
- Hsu, Taylor & Wang (CICF conference version) — https://www.cicfconf.org/sites/default/files/paper_412.pdf
- Menkhoff, Sarno, Schmeling & Schrimpf, Currency momentum (JFE 2012) — https://ideas.repec.org/a/eee/jfinec/v106y2012i3p660-684.html
- Moskowitz, Ooi & Pedersen, Time series momentum (JFE 2012) — https://ideas.repec.org/a/eee/jfinec/v104y2012i2p228-250.html
- Hurst, Ooi & Pedersen, A Century of Evidence on Trend-Following (AQR) — https://www.trendfollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf ; https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing
- Baltas & Kosowski (WP) — https://www.naaim.org/wp-content/uploads/2013/10/00S_Momentum_Strategies_in_Futures_Markets_Nick_Baltas.pdf
- Babu et al., Trends Everywhere — https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/fd3c53f7-c472-4898-a7e1-f6c100b1b81e.pdf
- Babu et al., You Can't Always Trend When You Want (JPM 2020) — https://www.aqr.com/Insights/Research/Journal-Article/You-Cant-Always-Trend-When-You-Want
- Lempérière et al., Two centuries of trend following — https://arxiv.org/abs/1404.3274
- Huang, Li, Wang & Zhou (JFE 2020) — https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html
- Kim, Tse & Wald (JFM 2016) — https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html
- Szakmary, Shen & Sharma (JBF 2010) — https://ideas.repec.org/a/eee/jbfina/v34y2010i2p409-426.html
- Société Générale prime services indices (SG Trend Index definition) — https://wholesale.banking.societegenerale.com/en/prime-services-indices/

**Practitioner canon and equity technical evidence**
- Park & Irwin (JES 2007) — https://ideas.repec.org/a/bla/jecsur/v21y2007i4p786-826.html
- Park & Irwin, AgMAS review (Lukac-Brorsen-Irwin 1988 summary) — https://farmdoc.illinois.edu/assets/marketing/agmas/AgMAS04_04.pdf
- Brock, Lakonishok & LeBaron (JF 1992) — https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html
- Sullivan, Timmermann & White (JF 1999) — https://ideas.repec.org/a/bla/jfinan/v54y1999i5p1647-1691.html
- Bajgrowicz & Scaillet (JFE 2012) — https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html
- Neely, Rapach, Tu & Zhou (Management Science 2014) — https://ideas.repec.org/a/inm/ormnsc/v60y2014i7p1772-1791.html
- Han, Zhou & Zhu, A trend factor (JFE 2016) — https://ideas.repec.org/a/eee/jfinec/v122y2016i2p352-375.html
- George & Hwang, 52-week high (JF 2004) — https://ideas.repec.org/a/bla/jfinan/v59y2004i5p2145-2176.html
- Lo, Mamaysky & Wang (JF 2000) — https://www.nber.org/papers/w7613
- Chang & Osler (EJ 1999) — https://ideas.repec.org/a/ecj/econjl/v109y1999i458p636-61.html
- Osler, Support for Resistance (FRBNY EPR 2000) — https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf
- Osler, Currency Orders and Exchange Rate Dynamics (JF 2003) — https://ideas.repec.org/a/bla/jfinan/v58y2003i5p1791-1819.html
- Chong, Ng & Liew, MACD and RSI (JRFM 2014) — https://www.mdpi.com/1911-8074/7/1/1
- Leung & Chong, MA envelopes vs Bollinger Bands (AEL 2003) — https://ideas.repec.org/a/taf/apeclt/v10y2003i6p339-341.html
- Ding, Mazouz, ap Gwilym & Wang (2023) — https://orca.cardiff.ac.uk/id/eprint/161200/1/TA%20sentiment_20230405.pdf
- Gervais, Kaniel & Mingelgrin (JF 2001) — https://ideas.repec.org/a/bla/jfinan/v56y2001i3p877-919.html
- Lee & Swaminathan (JF 2000) — https://ideas.repec.org/a/bla/jfinan/v55y2000i5p2017-2069.html
- Alizadeh, Brandt & Diebold (JF 2002) — https://ideas.repec.org/a/bla/jfinan/v57y2002i3p1047-1091.html
- Kaminski & Lo (JFM 2014) — https://ideas.repec.org/a/eee/finmar/v18y2014icp234-254.html
- Nagel, Evaporating Liquidity (RFS 2012) — https://ideas.repec.org/a/oup/rfinst/v25y2012i7p2005-2039.html
- Jegadeesh (JF 1990) — https://ideas.repec.org/a/bla/jfinan/v45y1990i3p881-98.html
- Gao, Han, Li & Zhou, Market intraday momentum (JFE 2018) — https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html
- Gu, Kelly & Xiu (RFS 2020) — https://www.nber.org/papers/w25398
- CMT Association program page — https://cmtassociation.org/chartered-market-technician/
- TradingView community scripts (T3, computation only): Squeeze Momentum https://www.tradingview.com/script/nqQ1DT5a-Squeeze-Momentum-Indicator-LazyBear/ ; WaveTrend https://www.tradingview.com/script/2KE8wTuF-Indicator-WaveTrend-Oscillator-WT/ ; UT Bot https://www.tradingview.com/script/n8ss8BID-UT-Bot-Alerts/ ; Lorentzian Classification https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/

**Backtest realism, overfitting and retail outcomes**
- TradingView Pine Script docs, Strategies — https://www.tradingview.com/pine-script-docs/concepts/strategies/
- TradingView Pine Script docs, Repainting — https://www.tradingview.com/pine-script-docs/concepts/repainting/
- TradingView Pine Script docs, Other timeframes and data — https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/
- TradingView Pine Script docs, Strategies FAQ — https://www.tradingview.com/pine-script-docs/faq/strategies/
- TradingView Pine Script docs, Migration to v6 — https://www.tradingview.com/pine-script-docs/migration-guides/to-pine-version-6/
- TradingView script publishing rules — https://www.tradingview.com/support/solutions/43000590599-script-publishing-rules/
- TradingView support, strategies/backtesting — https://www.tradingview.com/support/solutions/43000562362-what-are-strategies-backtesting-and-forward-testing/
- Wiecki, Campbell, Lent & Stauth, All that Glitters Is Not Gold (Quantopian) — https://ssrn.com/abstract=2745220
- Bailey, Borwein, López de Prado & Zhu (Notices AMS 2014) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659
- Harvey & Liu, Backtesting (JPM 2015) — https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF
- Hoffmann & Shefrin (JEBO 2014) — https://ideas.repec.org/a/eee/jeborg/v107y2014ipbp487-511.html
- Barber, Lee, Liu & Odean, Speculator skill (WP) — https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20Skill%20110523.pdf
- Chague, De-Losso & Giovannetti, Day Trading for a Living? — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101
- ESMA, CFD and binary-option measures (27 Mar 2018) — https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors
