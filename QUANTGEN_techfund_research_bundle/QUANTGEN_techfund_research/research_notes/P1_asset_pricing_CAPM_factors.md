# P1 — Professor of Asset Pricing: CAPM, APT, multifactor models and the factor zoo, for QUANTGEN

Position paper for the QUANTGEN "technical and fundamental signals" professors' panel. Current as of 2 October 2026 (Asia/Seoul).

Structure: this note follows the mandatory structure in `00_QUANTGEN_context.md` (persona, position summary, evidence, failures, data checks, claims ledger, sources). Inside the evidence section, each key question uses the research protocol's Takeaway / Cited Findings / Inferences / Gaps layout.

**Data-access note (read first).** The agent proxy blocked direct downloads (HTTP 403 on CONNECT) of the Kenneth French zip files, AQR data sets, JKP data files and q-factor CSVs. So every factor number below comes from a page that was actually opened:
- the French Data Library's "current research returns" table (data through August 2026);
- MSCI index factsheets dated 31 August 2026;
- iShares fund pages (calendar years through 2025, trailing returns to 30 June 2026);
- the original papers.

I did not estimate decade-by-decade US factor statistics. They are requested from the data lab instead (DC-4). Numbers labelled "P1 calc" are my own arithmetic on the cited data, and the inputs are stated each time.

---

## 1. Persona

**P1, "Professor of Asset Pricing".** This is a fictional composite persona, not a real person: a tenured finance professor who teaches empirical asset pricing (PhD) and investments (MBA) at a top US business school and spent a visiting term at KAIST. P1 judges a model first as a measurement tool (does it describe risk and attribute returns correctly?) and only second as a forecasting tool. A premium counts only if it replicates out of sample, after publication and after realistic trading costs. All research cited is by real, named authors and institutions.

## 2. Position summary

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

---

## 3. Evidence by key question

### KQ1. CAPM tests and failures; where CAPM is still useful

#### Takeaway
Every major test since Black-Jensen-Scholes (1972) finds the beta-return relation flatter than CAPM predicts: flat in 1963-1990 and even inverted when disagreement is high. Low-beta stocks have historically beaten high-beta stocks, but in 2020-2026 long-only low-volatility products lost heavily because their beta is about 0.67. CAPM is still useful for exposure measurement, hedging, cost-of-capital conventions and as the first layer of attribution. It should never be used as a return forecast.

#### Cited Findings
- **The SML is too flat (US, 1928-2003, in-sample, gross).** Using value-weighted portfolios formed on prior beta, the lowest-beta portfolio's CAPM-predicted return was 8.3%/yr against an actual 11.1%. The highest-beta portfolio was predicted at 16.8% and earned 13.7%. Fama and French conclude that "the relation between beta and average return is too flat." — [Fama-French 2004, JEP, full text (Dartmouth)](https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa); [AEA article page](https://www.aeaweb.org/articles?id=10.1257/0895330042162430)
- **Early tests.** Fama-French (2004) report that Black, Jensen and Scholes (1972) found the beta-return relation much flatter than Sharpe-Lintner predicts. They also note that Fama-MacBeth (1973) introduced month-by-month cross-section regressions to deal with residual correlation in cross-section tests. The original BJS and FM abstracts were not available on the fetched index pages. — [Fama-French 2004](https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa)
- **Beta is flat even on its own (US, 1963-1990 sample per the paper).** Once beta variation unrelated to size is allowed, the relation between beta and average return is flat even when beta is the only regressor. Size and book-to-market absorb the cross-sectional variation associated with beta, leverage and E/P. — [Fama-French 1992, JF abstract (IDEAS)](https://ideas.repec.org/a/bla/jfinan/v47y1992i2p427-65.html)
- **Consequences for applications.** CAPM cost-of-equity estimates are too high for high-beta stocks and too low for low-beta stocks. Passive portfolios tilted to size or value show CAPM "abnormal returns", so CAPM-only performance evaluation mistakes factor tilts for skill. Roll's critique (the true market portfolio cannot be observed) makes a clean test of the model nearly impossible. — [Fama-French 2004](https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa)
- **Betting against beta (in-sample, gross of trading costs).**
  - US, January 1926 to March 2012: BAB earned an excess return of 0.70%/month with an annualized Sharpe of 0.78, and a four-factor alpha of 0.55%/month (t = 5.59).
  - CAPM alphas fall almost monotonically from the lowest-beta decile (+0.52%/month) to the highest-beta decile (-0.10%/month).
  - In 19 developed markets outside the US, positive Sharpe ratios in 18 and significant alphas in 13 (as extracted from the paper's tables).
  - BAB is also positive in Treasuries, credit and futures.
  - A wider TED spread coincides with BAB losses, consistent with the funding-constraint theory.

  — [Frazzini-Pedersen 2014, JFE (author PDF, NYU)](https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf)
- **Critique of BAB's construction.** Novy-Marx and Velikov (2022, JFE) argue that BAB's non-standard construction effectively equal-weights stocks. For each dollar in BAB, it commits on average $1.05 to stocks in the bottom 1% of market capitalization. Its returns come from tilts toward profitability and investment, and the beta-estimation procedure biases the evidence offered for the theory. BAB does remain positive after transaction costs. — [Novy-Marx & Velikov 2022 abstract (EconPapers)](https://econpapers.repec.org/RePEc:eee:jfinec:v:143:y:2022:i:1:p:80-106)
- **Speculative betas.** When aggregate disagreement is low, expected returns rise with beta. When disagreement is high, expected returns first rise and then fall with beta, because short-sale constraints let optimists overprice high-beta stocks. — [Hong-Sraer, NBER w18548 (JF 2016)](https://www.nber.org/papers/w18548)
- **The low-risk anomaly in long-only terms (US top 1,000 stocks, January 1968 to December 2008, nominal, gross).**
  - $1 in the lowest-beta quintile grew to $78.66, against $4.70 in the highest-beta quintile.
  - $1 in the lowest-volatility quintile grew to $53.81, against $7.35 in the highest-volatility quintile.
  - Proposed causes: lottery preferences, representativeness and overconfidence, combined with cap-weighted benchmarking that stops institutions from arbitraging the effect.

  — [Baker-Bradley-Wurgler 2011, FAJ (NYU PDF)](https://pages.stern.nyu.edu/~jwurgler/papers/faj-benchmarks.pdf)
- **When beta is priced.**
  - On scheduled macro-announcement days, beta is strongly and positively related to average returns, for stocks, test portfolios, bonds and currencies. — [Savor-Wilson 2014, JFE (IDEAS)](https://ideas.repec.org/a/eee/jfinec/v113y2014i2p171-201.html)
  - Returns are positively related to beta overnight and negatively during the trading day, so the 24-hour relation is weak. — [Hendershott-Livdan-Rösch 2020, JFE (IDEAS)](https://ideas.repec.org/a/eee/jfinec/v138y2020i3p635-662.html)
- **Live low-volatility record, 2012 to August 2026 (MSCI, gross USD, P1 calc from calendar-year returns).**

  | Period | MSCI World Minimum Volatility | MSCI World | Difference |
  |---|---|---|---|
  | 2012-2025 (geometric, per year) | 9.29% | 12.46% | -3.17 pp/yr; ahead in 5 of 14 years |
  | 2012-2019 | | | -0.25 pp/yr |
  | 2020-2025 | | | -7.00 pp/yr |
  | 2023-2025 | | | -11.45 pp/yr |
  | 12 months to 31 Aug 2026 | 7.29% | 20.83% | -13.5 pp |

  The index beta is 0.67 and its maximum drawdown was 47.73% (2007-2009). — [MSCI World Minimum Volatility factsheet, 31 Aug 2026](https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf); MSCI World annual returns from [MSCI World Value factsheet](https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf)
- **USMV (US minimum-volatility ETF, NAV, net of 0.15% fee).** Calendar years: 2021 +20.79%, 2022 -9.35%, 2023 +10.21%, 2024 +15.83%, 2025 +7.68%. One year to 30 June 2026: +4.32%, against +21.83% for IWB (Russell 1000). — [iShares USMV](https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf); [iShares IWB](https://www.ishares.com/us/products/239707/ishares-russell-1000-etf)
- **CAPM in practice: corporate finance.** In a survey of 392 CFOs, 73.5% always or almost always use CAPM for the cost of equity. 34.3% use CAPM with extra risk factors, 39.4% use average historical returns and 15.7% use dividend-discount models. — [Graham-Harvey 2001, JFE (Duke PDF)](https://people.duke.edu/~charvey/Research/Published_Papers/P67_The_theory_and.pdf)
- **CAPM in practice: valuation teaching.** Damodaran keeps CAPM as the default model despite a weak beta-return relation. His reason is that APT and multifactor models explain past returns better but do not forecast future returns better, and they cost more complexity and data. — [Damodaran, "Risk and Return Models" slides (NYU Stern)](https://pages.stern.nyu.edu/~adamodar/pdfiles/acf4E/presentations/risk&ret.pdf)
- **Attribution.** Common factors (including one-year momentum) and expenses almost completely explain apparent persistence in mutual fund performance. — [Carhart 1997, JF (IDEAS)](https://ideas.repec.org/a/bla/jfinan/v52y1997i1p57-82.html)

#### Inferences
- **Beta is a good risk measure and a bad return forecast.** QUANTGEN should use beta for exposure, hedging, position sizing and attribution, and never as an expected-return input. If a card ever shows an "expected return", it should come from a flattened SML (intercept above the risk-free rate, slope below the market premium) and be labelled as such.
- **2012-2026 low-volatility losses are mostly beta, not broken alpha.** P1 calc, assuming beta = 0.67 and an average T-bill rate of about 1%/yr in 2012-19 and about 2.5%/yr in 2020-25 (assumption, to be checked against FRED TB3MS), the approximate CAPM alpha of MSCI World Minimum Volatility was:

  | Period | Approximate CAPM alpha |
  |---|---|
  | 2012-2019 | about +3.3%/yr |
  | 2020-2025 | about -3.4%/yr |
  | 2012-2025 | about +0.4%/yr |

  Low-volatility failed badly as a raw-return product, but over the full period it only roughly broke even as a CAPM anomaly.
- **Gate implication.** Comparing Sharpe ratios does not change when a benchmark is mixed with cash, but comparing raw returns does. For any card with beta well below 1 (E1 trend switch, E2 volatility targeting, E3 risk parity, any low-volatility sleeve), the right "beat the benchmark" statistic is Jensen's alpha. That means regressing daily card returns on the benchmark with Newey-West standard errors. A positive alpha is the same thing as "adding the card raises the benchmark's Sharpe". This is a proposal for the next pre-registered gate version, not a retroactive change.
- **BAB as published is not implementable by QUANTGEN users.** It requires micro-caps, leverage and shorting. A value-weighted, liquid-universe, beta-neutral version is a legitimate hypothesis. Given the Novy-Marx-Velikov critique and the 2020-2026 record, it belongs in BACKLOG.
- **In Korea, a low-beta tilt today is effectively an underweight in Samsung Electronics and SK hynix.** Those two stocks are about 61% of MSCI Korea (see KQ2), which became a very costly relative bet in 2025-26.

#### Gaps
- I found no fetched evidence on the SML slope or on BAB in Korea (requested as DC-1 and DC-2).
- The original Fama-MacBeth (1973) and Black-Jensen-Scholes (1972) texts were not retrieved; they are described here through Fama-French (2004).
- The result of Berk-van Binsbergen (2016, "revealed preference": which model investors actually use) could not be verified from the pages I reached, so it is not used.
- Evidence on macro-factor APT (e.g., Chen-Roll-Ross 1986) was not retrieved. APT is covered only as taught (KQ5) and through Kozak-Nagel-Santosh (KQ4).

---

### KQ2. Multifactor evidence and how factor premia behaved, by period and in 2010-2026

#### Takeaway
- Modern models (FF5, q-factor, Barillas-Shanken's {Mkt, SMB, IA, ROE, HMLm, UMD}) price test portfolios far better than CAPM, but all are statistically rejected or fragile.
- Over the long run, value and momentum have the deepest histories. Profitability and investment are strong after 1963 but absent before it.
- From 2012 to August 2026, live indexes ranked roughly: quality (IR about 0.3-0.4) > momentum (about 0) > value (negative in the world index, positive outside the US since 2021) > low-volatility (most negative in raw terms). Size added nothing.
- The 2023-2026 AI-concentration years and Korea's two-stock market dominated any factor tilt.

#### Cited Findings

**Models**
- **FF5 (US sample starting 1963).** The model explains 71% to 94% of the cross-sectional variance of expected returns for its test portfolios, yet the GRS test rejects it. Its main failure is small stocks that invest heavily despite low profitability. HML becomes redundant once RMW (profitability) and CMA (investment) are added. — [Fama-French 2015, JFE abstract (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0304405X14002323)
- **FF3 and Carhart.** FF3 is the market, size (SMB) and value (HML) factors. Carhart (1997) adds one-year momentum. The French Data Library still publishes FF3, FF5 (2x3 and new 2x2 variants), momentum and short- and long-term reversal factors, plus Developed, Europe, Japan, Asia-Pacific ex Japan and North America versions. Data run through August 2026. Since January 2025 the library uses CRSP's CIZ format, with monthly returns compounded from daily returns and dividends reinvested on ex-dates. — [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html); [Carhart 1997 (IDEAS)](https://ideas.repec.org/a/bla/jfinan/v52y1997i1p57-82.html)
- **Hou-Xue-Zhang q-factor model (US, January 1972 to December 2011, in-sample, gross; working-paper version of RFS 2015).**
  - Size: 0.31%/month (t = 2.09). Investment: 0.44%/month (t = 4.73). ROE: 0.60%/month (t = 4.85).
  - The q-model cuts the earnings-surprise alpha to 0.14% (t = 0.92), against 0.32% (t = 2.43) under Carhart.
  - Idiosyncratic-volatility alpha falls to -0.04%, against -0.58% under Carhart; distress alpha to 0.02%, against -0.55%.
  - Average absolute winner-minus-loser alpha is 0.19%, against 0.25% under Carhart.
  - P1 calc (annualized Sharpe implied by mean and t over 480 months): about 0.33 for size, 0.75 for investment and 0.77 for ROE.

  — [HXZ, NBER w18435 PDF](https://www.nber.org/system/files/working_papers/w18435/w18435.pdf)
- **Stambaugh-Yuan mispricing factors (US, January 1967 to December 2013).**
  - Two clusters built from 11 anomalies. MGMT: net and composite equity issuance, accruals, net operating assets, asset growth, investment-to-assets. PERF: distress, O-score, momentum, gross profitability, ROA.
  - Average absolute alpha across the anomaly set: 0.18% (their four-factor model), 0.45% (FF5), 0.34% (q).
  - Sentiment predicts the short legs with slopes two to three times larger than on the long legs.
  - Their size factor shows a small-firm premium nearly twice the usual estimate.

  — [Stambaugh-Yuan, NBER w21533](https://www.nber.org/papers/w21533); [PDF](https://www.nber.org/system/files/working_papers/w21533/w21533.pdf)
- **Daniel-Hirshleifer-Sun behavioral factors (US, 1972-2014).**
  - FIN: 0.80%/month (t = 4.6). PEAD: 0.65%/month (t = 7.91). Monthly Sharpe 0.20 and 0.35, about 0.69 and 1.21 annualized (P1 calc).
  - Of 34 anomalies, significant alphas remain for 3 under their three-factor model, against 18 under FF5, 6 under q and 7 under Stambaugh-Yuan.
  - Maximum monthly Sharpe: BF3 0.52, FF5 0.36, q 0.43, SY 0.50, Novy-Marx four-factor 0.57.

  — [DHS, NBER w24163 PDF](https://www.nber.org/system/files/working_papers/w24163/w24163.pdf)
- **Barillas-Shanken Bayesian model comparison (US, January 1972 to December 2013).** The single best model is {Mkt, IA, ROE, SMB, HMLm, UMD}. Models built from size, profitability, investment, value and momentum carry about 73-74% posterior probability. The monthly-updated value factor HMLm takes 99.5% of the value-factor probability, and ROE takes 99.5% of the profitability probability. FF5 and HXZ rank lower. — [Barillas-Shanken, NBER w21771 PDF](https://www.nber.org/system/files/working_papers/w21771/w21771.pdf)

**International and Korea**
- **Developed regions.** Value premiums appear in North America, Europe, Japan and Asia-Pacific, and shrink with size except in Japan. Momentum appears everywhere except Japan. Local models give passable descriptions; an integrated global model is not supported. — [Fama-French 2012, JFE (EconPapers)](https://econpapers.repec.org/RePEc:eee:jfinec:v:105:y:2012:i:3:p:457-472)
- **Value and momentum across markets and asset classes (January 1972 to July 2011, gross, in-sample).**

  | Market | Value Sharpe | Momentum Sharpe | 50/50 combination Sharpe | Value-momentum correlation |
  |---|---|---|---|---|
  | US stocks | 0.29 | 0.33 | 0.63 | -0.53 |
  | UK stocks | 0.33 | 0.38 | 0.77 | -0.43 |
  | Europe stocks | 0.42 | 0.55 | 0.87 | -0.52 |
  | Japan stocks | 0.79 | 0.09 | 0.78 | -0.60 |
  | Global stocks | 0.57 | 0.47 | 1.04 | |
  | Country indices | 0.61 | 0.73 | 1.16 | |
  | Currencies | 0.34 | 0.34 | 0.63 | |
  | Bonds | 0.18 | 0.06 | 0.19 | |
  | Commodities | 0.26 | 0.53 | 0.71 | |
  | All asset classes | 0.73 | 0.67 | 1.42 | |

  — [Asness-Moskowitz-Pedersen 2013, JF (NYU PDF)](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf)
- **Japan momentum.** Stock momentum in Japan made essentially no money for about 30 years on its own, but adds value inside a value-plus-momentum system. — [Asness 2011, AQR](https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-That-Proves-the-Rule)
- **Emerging markets (18 EMs, January 1990 to December 2011).** Value appears in all EMs and momentum in all but Eastern Europe. Local factors explain returns much better than US or global ones, indicating segmentation. — [Cakici-Fabozzi-Tan 2013 (IDEAS)](https://ideas.repec.org/a/eee/ememar/v16y2013icp46-65.html)
- **Korea, July 2002 to June 2015 (156 months; KOSPI and KOSDAQ non-financials; 2x3 sorts; in-sample, gross).**
  - Monthly averages: market 0.52% (t = 1.12), SMB 0.16% (t = 0.45), HML 1.05% (t = 3.41), quarterly profitability RMWq 0.65% (t = 2.75), CMA 0.66% (t = 3.57).
  - The best model is FF5 with quarterly profitability. Unlike in the US, HML stays significant alongside the other factors. The model digests 8 of 10 anomalies.
  - P1 calc (annualized Sharpe implied by mean and t): HML about 0.95, RMWq about 0.76, CMA about 0.99, SMB about 0.12.

  — [Kang 2016, Korea Finance Association conference paper (PDF)](http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf)
- **Korea anomaly replication (January 2000 to June 2019, 148 anomalies).**
  - In value-weighted KOSPI+KOSDAQ portfolios, 37.8% clear t > 1.96 and 27.7% clear t > 2.78.
  - By category: value 69.2%, momentum 66.7%, trading frictions 48.2%, investment 24.1%, intangibles 23.5%, profitability 5%.
  - Excluding KOSDAQ, the momentum success rate falls from 66.7% to 20%.

  — [Han, Lee & Kang 2020, Journal of Derivatives and Quantitative Studies (Emerald)](https://www.emerald.com/jdqs/article/28/2/3/206237/Market-anomalies-in-the-Korean-stock-market)
- **Korea factor investing.** Size, value, momentum, profitability and low-risk premiums exist in Korea, with size largest. Removing stocks with large negative exposures to unintended factors improves performance. (Only the abstract was available, without numbers.) — [Kim 2021, Pacific-Basin Finance Journal (IDEAS)](https://ideas.repec.org/a/eee/pacfin/v67y2021ics0927538x21000652.html)

**Long-history performance, by period (US unless stated)**
- **Value.**
  - Pre-1963 (1926-1963, out of sample relative to its discovery): 0.43%/month (t = 2.09). — [Linnainmaa-Roberts, NBER w22894 PDF](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf)
  - July 1963 to June 2019: value premiums were much lower in the second half, but monthly volatility is too high to reject equal expected premiums in both halves. — [Fama-French 2021, "The Value Premium" (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3525096)
  - Drawdowns: HML fell 55% from 2007 to mid-2020 (13.5 years, the deepest since 1963). Earlier drawdowns were 40.6% over 2.5 years (tech bubble) and 24.9% over 3.7 years. — [Arnott-Harvey-Kalesnik-Linnainmaa 2021, FAJ (Duke PDF)](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf)
  - MSCI World Value since December 1974: 11.68%/yr against 11.32% for MSCI World, only +0.36 pp/yr (gross, partly back-tested). — [MSCI World Value factsheet](https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf)
- **Momentum.** Winner-minus-loser (WML), 1927-2013: 17.9%/yr mean, 30.0% volatility, Sharpe 0.60, monthly skewness -4.70. — [Daniel-Moskowitz, NBER w20439 PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf). The context brief adds Sharpe 0.33 since 1990 and 0.02 since 2008 (French WML).
- **Profitability and investment.** Pre-1963: 0.09%/month (t = 0.86) and 0.02%/month (t = 0.14), i.e. absent. 1972-2011: ROE 0.60% and investment 0.44%/month (above). — [Linnainmaa-Roberts PDF](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf); [HXZ PDF](https://www.nber.org/system/files/working_papers/w18435/w18435.pdf)
- **Size.** 0.31%/month (t = 2.09) in 1972-2011 (q-factor version). A robust size premium (stable over time, beyond January and micro-caps, in 24 international markets) appears only after controlling for quality or "junk". — [Asness-Frazzini-Israel-Moskowitz-Pedersen 2018, JFE (IDEAS)](https://ideas.repec.org/a/eee/jfinec/v129y2018i3p479-509.html)

**2012 to August 2026: live factor indexes (P1 calc from MSCI calendar-year returns, gross USD, before costs)**

| Factor index vs parent | Active return 2012-25 (geometric, pp/yr) | Years ahead | IR (annual data) | 2012-19 (pp/yr) | 2020-25 (pp/yr) | 2023-25 (pp/yr) | 12 months to 31 Aug 2026 (pp) |
|---|---|---|---|---|---|---|---|
| World Value vs World | -2.31 | 5/14 | -0.37 | -1.55 | -3.33 | -6.37 | +3.33 |
| World Quality vs World | +1.68 | 9/14 | +0.43 | +2.14 | +1.04 | +1.00 | -1.51 |
| World Minimum Volatility vs World | -3.17 | 5/14 | -0.47 | -0.25 | -7.00 | -11.45 | -13.54 |
| USA Momentum vs USA | +0.34 | 9/14 | +0.04 | +2.33 | -2.26 | -3.74 | +6.14 |
| USA Quality vs USA | +1.06 | 8/14 | +0.33 | +1.49 | +0.49 | +2.01 | +1.32 |
| Japan Value vs Japan | +0.47 | 8/14 | +0.05 | -1.47 | +3.10 | +5.00 | n/a |
| Europe Value vs Europe (2016-25 only) | +0.53 | 5/10 | +0.09 | -2.87 (2016-20) | +4.16 (2021-25) | — | +6.22 |
| EM Value vs EM (2016-25 only) | -0.27 | 5/10 | -0.12 | -3.50 (2016-20) | +2.81 (2021-25) | — | +4.48 |

Sources: [World Value](https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf), [World Quality](https://www.msci.com/documents/10199/255599/msci-world-quality-index.pdf), [World Minimum Volatility](https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf), [USA Momentum](https://www.msci.com/documents/10199/255599/msci-usa-momentum-index.pdf), [USA Quality](https://www.msci.com/documents/10199/255599/msci-usa-quality-index.pdf), [USA parent](https://www.msci.com/documents/10199/255599/msci-usa-index-gross.pdf), [Japan Value](https://www.msci.com/documents/10199/255599/msci-japan-value-index.pdf), [Europe Value](https://www.msci.com/documents/10199/255599/msci-europe-value-index.pdf), [EM Value](https://www.msci.com/documents/10199/255599/msci-emerging-markets-value-index.pdf) (all dated 31 Aug 2026).

How to read these indexes:
- MSCI USA Momentum launched in February 2013 and MSCI USA Quality in December 2012. Their histories before launch (base date June 1994) are back-tests.
- Since 1994, USA Momentum shows 13.81%/yr and USA Quality 13.17%/yr, against 11.36% for MSCI USA. Most of that edge is back-tested.
- Live from 2013 to 2025 (P1 calc): momentum +0.45 pp/yr and quality +1.31 pp/yr over MSCI USA.

Notable single-year active returns (pp):

| Index | Notable years |
|---|---|
| World Value | 2020 -16.9; 2022 +11.9; 2023 -12.0; 2024 -6.9 |
| USA Momentum | 2021 -14.1; 2023 -17.6; 2024 +7.2 |
| World Minimum Volatility | 2020 -13.2; 2022 +8.5; 2023 -16.3; 2025 -10.4 |
| World Quality | 2022 -4.2; 2025 -4.7 |
| Japan Value | 2020 -13.6; 2022 +11.6; 2025 +7.6 |
| Europe Value | 2020 -10.4; 2025 +13.1 |

**US style and factor ETFs (NAV, net of fund fees, before investor trading costs).**
- Russell 1000 Value minus Russell 1000 Growth (IWD minus IWF), 2021-2025: -2.45, +21.54, -31.18, -18.95, -2.63 pp, i.e. about -4.0 pp/yr geometric.
- Russell 2000 minus Russell 1000 (IWM minus IWB): -11.65, -1.24, -9.60, -12.98, -4.50 pp, i.e. about -7.5 pp/yr.
- One year to 30 June 2026: IWD 26.87% vs IWF 17.47%; IWM 40.59% vs IWB 21.83%; MTUM 43.70%; VLUE 80.03%; QUAL 21.34%; USMV 4.32%; SIZE 17.16%.
- On 29 September 2026, VLUE (MSCI USA Enhanced Value) held 43.14% in Information Technology.

— [IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf), [IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf), [IWM](https://www.ishares.com/us/products/239710/ishares-russell-2000-etf), [IWB](https://www.ishares.com/us/products/239707/ishares-russell-1000-etf), [MTUM](https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf), [VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf), [QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf), [USMV](https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf), [SIZE](https://www.ishares.com/us/products/251465/ishares-msci-usa-size-factor-etf)

**Fama-French research factors, latest (US, data through August 2026, gross, long-short).**

| Factor | 12 months to Aug 2026 | Last 3 months | August 2026 |
|---|---|---|---|
| Mkt-RF | +16.06% | | |
| SMB (FF3 version) | -0.22% | | |
| SMB (FF5 version) | +5.03% | | |
| HML | +13.55% | +2.25% | -3.54% |
| RMW | -16.44% | +2.62% | -4.08% |
| CMA | +0.08% | +3.91% | -2.01% |

12-month research-portfolio returns tell the same story:
- Big Value +42.49% vs Big Growth +14.96%.
- Small Weak (low profitability) +43.29% vs Small Robust +19.16%.
- Big Weak +26.85% vs Big Robust +18.10%.

The momentum factor is not shown in the current-returns table. — [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)

**Korea concentration, 2025-26.**
- MSCI Korea returned +100.76% in 2025 (MSCI EM +34.36%) and +170.65% in the 12 months to 31 August 2026.
- Weights: Samsung Electronics 34.55%, SK hynix 26.27%, Samsung Electronics preferred 4.25%; Information Technology 68.99%. Three-year standard deviation: 47.14%.

  — [MSCI Korea factsheet, 31 Aug 2026](https://www.msci.com/documents/10199/255599/msci-korea-index.pdf)
- Samsung Electronics and SK hynix accounted for about half of the 2025 increase in KOSPI market capitalization. KOSPI price-to-book averaged 0.99, and over 60% of Korean firms earn ROE below 7%. — [AMRO, "Narrowing the Korea Discount", 30 Mar 2026](https://www.amro-asia.org/narrowing-the-korea-discount-stock-market-reform-via-corporate-value-up)

#### Inferences
- **Value.**
  - The pattern was a lost decade (2012-2020: World Value -16.9 pp in 2020 alone), a 2022 rebound, AI-concentration losses in 2023-24, and a 2025-26 recovery led outside the US.
  - "Value" no longer means one thing. In the 12 months to mid-2026, MSCI USA Enhanced Value (sector-relative, 43% Information Technology) rose 80% while B/M-based HML rose 13.6%. Factor definitions (sector-neutral or not, capped or cap-weighted) now matter as much as the factor itself.
  - Over 1974-2026, MSCI World Value's gross premium over MSCI World is only about 0.4 pp/yr.
- **Quality was the most consistent live factor of 2012-2025** (IR about 0.33-0.43), but it lost 16.4% (RMW) in the 2025-26 junk rally. It is absent before 1963 and is displaced from the JKP tangency portfolio (KQ3). The prior design's line that quality is the "most consistent sign of any fundamental factor" overstates the evidence; weight 2, not 3.
- **Momentum.** The live US momentum index earned about 0 IR over 2012-2025. Its 2023 loss (-17.6 pp) is a "turning-point" crash after the 2022 leadership flip, consistent with Daniel-Moskowitz. The 2024-26 recovery came from holding AI leaders.
- **Size** produced nothing as a standalone premium in 2021-2025. It reappeared only in the 2025-26 junk rally (IWM +40.6% over 12 months), which coincided with RMW -16.4%. That is a low-quality small-cap rally, not a clean size premium.
- **Low-volatility** was the worst raw-return factor of the 2020s; see KQ1 for the beta decomposition.
- **Korea.** Kang (2016) and Han-Lee-Kang (2020) agree that value is the strongest Korean cross-sectional effect. They disagree on profitability: quarterly RMWq is significant in Kang, but only 5% of profitability anomalies replicate in Han et al. They also disagree on momentum: 67% replicate including KOSDAQ, 20% without it. In 2025-26 the Korean cap-weighted benchmark was effectively a leveraged memory-chip trade, so any diversified Korean factor tilt looked terrible against it whatever its long-run merit.

#### Gaps
- No decade-by-decade table for US SMB, HML, RMW, CMA and UMD (zip downloads blocked). Requested as DC-4; the data lab's French file ends in 2018 and misses all of 2019-2026.
- MSCI's July 2025 paper "Factor Indexing Through the Decades" (Gupta and Doole), which reports decade results, is gated behind a form: [MSCI landing page](https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/factor-indexing-through-the-decades/factor-indexing-through-the-decades.pdf).
- q-factor data for 2012-2025 (global-q.org) and AQR's BAB and QMJ updates could not be accessed.
- No Korean factor return series for 2016-2026 was retrieved. JKP covers Korea, but only through an interactive interface.
- One extraction conflict: the MSCI World Quality factsheet extraction gave a 10-year Sharpe for MSCI World (0.47) that contradicts the World Value factsheet (0.77, which matches 13.56% return and 14.86% volatility). I did not use the quality-factsheet Sharpe values.

---

### KQ3. The factor zoo, replication and post-publication decay

#### Takeaway
Two readings of the replication literature look opposed but are consistent:
- Hou-Xue-Zhang: most published anomalies fail with NYSE breakpoints and value weights, especially liquidity and micro-cap-driven ones.
- Jensen-Kelly-Pedersen and Chen-Zimmermann: most factors, and all major themes, replicate, with about one-third smaller out-of-sample alphas.

The economically binding constraint is decay plus costs. In the US, returns fall about 58% after publication, and the average anomaly nets only about 4 bps/month after 2005. Only low-turnover themes survive at retail costs.

#### Cited Findings
- **Multiple testing (Harvey-Liu-Zhu 2016, RFS).**
  - 316 factors catalogued from 313 papers.
  - A new factor should clear t > 3.0 (p = 0.27%).
  - Adjusted thresholds by 2012: 3.78 (Bonferroni), 3.64 (Holm), 3.39 (BHY at 1% false discovery rate), projected to reach about 4.0 by 2032.
  - Among 296 published significant factors, false discoveries number 158 (53%) under Bonferroni, 142 (48%) under Holm, 132 (45%) under BHY 1% and 80 (27%) under BHY 5%.

  — [Harvey-Liu-Zhu (Duke PDF)](https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF)
- **Hou-Xue-Zhang "Replicating Anomalies" (US, 1967-2016, NYSE breakpoints and value weights).**
  - Of 447 anomalies, 286 (64%) are insignificant at 5%, including 95 of 102 liquidity variables (93%). With a t = 3 cutoff, 380 (85%) fail.
  - The October 2018 version (452 anomalies) shows replication by category: investment 73.7%, momentum 63.2%, profitability 44.3%, value 42%, intangibles 25.2%, trading frictions 3.8%.
  - Magnitudes shrink: B/M about 0.54%/month and six-month momentum 0.82%/month, against much larger originals.
  - Short-term reversal, idiosyncratic volatility, MAX and Amihud illiquidity become small or insignificant.
  - Micro-caps are 60.7% of firms but only 3.21% of market capitalization.

  — [HXZ, NBER w23394 abstract](https://www.nber.org/papers/w23394); [HXZ October 2018 PDF](https://theinvestmentcapm.com/uploads/1/2/2/6/122679606/replication2018oct.pdf)
- **Jensen-Kelly-Pedersen 2023, JF ("Is There a Replication Crisis in Finance?").**
  - 153 factors, 93 countries, 13 themes: accruals, debt issuance, investment, leverage, low risk, momentum, profit growth, profitability, quality, seasonality, size, skewness, value.
  - US replication rate: 84.9% (OLS), 77.3% (Benjamini-Yekutieli), about 81-84% (empirical Bayes).
  - Average alpha: 0.45%/month in-sample against 0.31%/month after the original sample, a decline of about one-third.
  - 10 of 13 themes enter the tangency portfolio with significantly positive weight; profitability, investment and size are displaced.
  - Replication rates using regional data only: developed ex-US 60.7%, emerging 56.3%. Both rise to about 77-78% when global data inform the estimates.
  - Their reconciliation with HXZ's 35% replication comes mainly from capped value-weighting (+8.5 pp), using CAPM alphas (+16.5 pp) and Bayesian multiple-testing treatment (+6.7 pp).

  — [JKP, NBER w28432](https://www.nber.org/papers/w28432); [JKP PDF](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf)
- **JKP database.** Latest update April 2026, with data through December 2025. Downloads by country, theme, universe size (mega to nano), weighting (capped value-weighted, value-weighted, equal-weighted), monthly or daily. Data licence CC BY-NC 4.0 (non-commercial). — [jkpfactors.com](https://jkpfactors.com/); [data page](https://jkpfactors.com/data)
- **Chen-Zimmermann open-source asset pricing.** 319 characteristics. Of the 161 clear predictors, 98% reproduce with t > 1.96. Regressing reproduced t-statistics on original ones gives a slope of 0.90 and R² of 83%. The data and code were last updated in October 2025. — [Chen-Zimmermann, Federal Reserve FEDS](https://www.federalreserve.gov/econres/feds/open-source-cross-sectional-asset-pricing.htm); [Open Source Asset Pricing](https://www.openassetpricing.com/)
- **Post-publication decay.**
  - McLean-Pontiff (2016): US predictor returns are 26% lower out of sample and 58% lower after publication (as quoted in JKP). — [JKP PDF](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf)
  - Jacobs-Müller (2020, JFE): across 241 anomalies in 39 markets, the US is the only country with a reliable post-publication decline. — [Jacobs-Müller (IDEAS)](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html)
- **Pre-1963 out-of-sample test (Linnainmaa-Roberts 2018, RFS).** In 1926-1963 only 8 of 36 accounting anomalies are significant. Value survives (0.43%/month); profitability (0.09%) and investment (0.02%) do not. Data-snooping is severe enough that even the true model would be rejected in-sample. — [Linnainmaa-Roberts, NBER w22894](https://www.nber.org/papers/w22894); [PDF](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf)
- **Net of costs (Chen-Velikov 2023, JFQA).**
  - 204 anomalies earn 68 bps/month gross in-sample, decaying about 50% after publication.
  - Anomaly portfolios paid a 67 bp effective spread in 2014, against an average NYSE spread of 16 bps.
  - After 2005 and after publication, the average anomaly nets about 4 bps/month with cost mitigation. The strongest net at most about 10 bps, and combinations about 20 bps, against 180+ bps before 2006.
  - The earlier Fed working-paper version reported 120 anomalies, 66 bps and 8 bps.

  — [Chen-Velikov JFQA PDF (Cambridge)](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/945133D5A3ECEEAF466AEE91551FD225/S0022109022000874a.pdf/zeroing-in-on-the-expected-returns-of-anomalies.pdf); [Fed working paper](https://www.federalreserve.gov/econres/feds/files/2020039pap.pdf)
- **Turnover and costs.**
  - Strategies with one-sided monthly turnover below 50% mostly keep significant net spreads when costs are mitigated. A buy/hold spread is the single most effective simple mitigation. — [Novy-Marx & Velikov, NBER w20721 (RFS 2016)](https://www.nber.org/papers/w20721)
  - Live data on about $1 trillion of institutional trades (19 developed markets, 1998-2011) show size, value and momentum survive costs at very large fund sizes. Short-term reversal does not survive at reasonable sizes. — [Frazzini-Israel-Moskowitz, AQR](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies)
- **Century of evidence (value, momentum, carry, defensive across six asset classes).** Estimated premia fall about 30% out of sample, more likely from overfitting than informed trading. Premia vary over time and are mildly predictable, but timing profits disappear once data lags and costs are included. — [Ilmanen-Israel-Moskowitz-Thapar-Lee, AQR](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence)
- **The phrase.** Cochrane's 2011 AFA presidential address describes the state of the cross-section as a "zoo of new factors". — [Cochrane, "Discount Rates", NBER w16972](https://www.nber.org/papers/w16972)

#### Inferences
- **Most of the replication disagreement is construction, not truth.** Micro-cap, equal-weighted and liquidity anomalies die; capped value-weighted thematic factors live. QUANTGEN should therefore use only capped value-weighted or liquidity-screened portfolios, exclude micro-caps, and judge by CAPM alpha as well as raw spread.
- **What survives is low-turnover.** Value, profitability, investment and low risk can be held with quarterly or annual rebalancing. Monthly momentum and weekly or monthly reversal must clear QUANTGEN's 35 bp (KRX) and 50 bp (US) per side, and HXZ plus Frazzini-Israel-Moskowitz say this is hard.

  > **Flag for the reversal panelist:** HXZ's value-weighted US reversal is only about 0.27%/month against much larger originals. The context brief's Korean figure of -2.95%/month (1999-2021) should be re-checked for value-weighting and micro-cap exclusion before reversal keeps weight 3 in Korea.
- **Haircuts.** The 58% post-publication decline (McLean-Pontiff) is calibrated on the US. Outside the US, decay is not reliably observed (Jacobs-Müller), and JKP's global out-of-sample decline is about one-third. Keeping QUANTGEN's 60% live haircut as a reported conservative figure is reasonable. For planning, use 33% ex-US and about 58% for US signals.
- **Hurdle for new characteristics.** The gate already counts trials (deflated Sharpe, PBO). The Harvey-Liu-Zhu t > 3 standard should apply to the published in-sample evidence before a new characteristic is allowed to become a card.

#### Gaps
- The original McLean-Pontiff abstract could not be fetched (SSRN rate-limited). The 26% and 58% figures are taken from JKP's quotation; the predictor count (97) is from my knowledge of the paper and was not re-verified here.
- The per-factor decay haircuts quoted in the context brief from Ilmanen et al. (value -49%, momentum -23%, multifactor -18%) are not visible on the AQR landing page I fetched. Only the aggregate 30% out-of-sample decline is verified.
- JKP's per-country theme statistics (e.g., Korea low-risk or value) are interactive-only and were not extracted.

---

### KQ4. Risk versus mispricing, and what each implies for persistence

#### Takeaway
The data cannot cleanly separate risk from mispricing: reduced-form factor tests cannot discriminate (Kozak-Nagel-Santosh). The weight of evidence nevertheless points to largely behavioral or constraint-driven premia:
- anomaly returns concentrate on news days;
- sentiment predicts the short legs;
- premia show little reliable relation to macro risk;
- US premia decay after publication.

Expect premia to persist mainly where limits to arbitrage bind (short legs, small or illiquid stocks, markets with barriers), and to shrink where arbitrage capital flows. A long-only retail implementation captures the less mispriced long leg.

#### Cited Findings
- **Factor models cannot settle the debate.** Tests of reduced-form factor models and "characteristics vs covariances" horse races cannot discriminate between models of investor beliefs. Sentiment-driven mispricing is large only if arbitrageurs bear factor risk when trading against it. Absence of near-arbitrage implies a stochastic discount factor spanned by a few dominant factors even when sentiment causes all cross-sectional variation. — [Kozak-Nagel-Santosh 2018, JF (IDEAS)](https://ideas.repec.org/a/bla/jfinan/v73y2018i3p1183-1223.html)
- **News-day concentration.** Across 97 anomalies, returns are 50% higher on corporate news days and six times higher on earnings-announcement days. The authors read this as biased expectations corrected when news arrives. — [Engelberg-McLean-Pontiff 2018, JF (IDEAS)](https://ideas.repec.org/a/bla/jfinan/v73y2018i5p1971-2001.html)
- **Sentiment and short legs.** Sentiment predicts mispricing factors, with short-leg slopes two to three times larger than long-leg slopes. — [Stambaugh-Yuan PDF](https://www.nber.org/system/files/working_papers/w21533/w21533.pdf)
- **Psychology-based factors fit best.** Factors built from investor psychology (FIN for long-horizon mispricing, PEAD for short-horizon) price 34 anomalies better than FF5, q or Stambaugh-Yuan. — [DHS PDF](https://www.nber.org/system/files/working_papers/w24163/w24163.pdf)
- **Risk-based and constraint-based accounts.**
  - The q-factor (investment-based) model frames premia as firms' rational investment responses to discount rates; the HXZ replication study concludes markets are more efficient than previously recognized. — [HXZ NBER w23394](https://www.nber.org/papers/w23394)
  - BAB is a leverage-constraint equilibrium (constrained investors bid up high-beta assets), and funding stress hurts it. — [Frazzini-Pedersen PDF](https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf)
  - Low-risk mispricing persists because cap-weighted benchmarking limits arbitrage. — [Baker-Bradley-Wurgler PDF](https://pages.stern.nyu.edu/~jwurgler/papers/faj-benchmarks.pdf)
- **Little link to macro risk.** Factor premia show little reliable relation to macroeconomic risk, liquidity, sentiment or crash risk over a century, and the out-of-sample decline looks more like overfitting than informed trading. — [Ilmanen et al., AQR](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence)
- **Value's slump came from repricing.** All of value's 2007-2020 shortfall comes from revaluation (spread widening, -7.2 pp/yr). The "structural" return (migration of value stocks plus their profitability gap) stayed positive at +1.1%/yr, down from 5.9% before 2007. Value spreads hit the cheapest percentile on record in 2020. — [Arnott et al. (Duke PDF)](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf)
- **Barriers to arbitrage abroad.** Outside the US, published anomalies do not reliably decline, consistent with segmented markets and genuine mispricing. — [Jacobs-Müller (IDEAS)](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html)

#### Inferences
- **Persistence by interpretation.**
  - Risk premia should persist but come with bad-times losses: value in the 2020 COVID crash, momentum in 1932 and 2009.
  - Mispricing premia should decay with publication and arbitrage capital, except where shorting is hard or costly.
  - For QUANTGEN this means: apply haircuts, expect US decay to be larger than Korean decay, and do not expect macro variables to time the premia. This is consistent with the macro panel's rule that macro variables only size risk.
- **Long-only captures less of the premium.** Mispricing is concentrated in short legs (Stambaugh-Yuan) and micro-caps (HXZ). A long-only, liquid implementation should be expected to capture well under half of a published long-short spread. This is a P1 assumption used in the KQ6 estimates.
- **Value spreads as a conditioning variable.** Because value's 2007-2020 losses were revaluation, a value card's ex-ante attractiveness can be monitored with its own valuation spread. Under the macro decision this may only size the card (multiplier at most 1.0), never direct it.

#### Gaps
- No Korea-specific evidence was retrieved on whether factor returns concentrate on DART filing or earnings dates (could be tested; see DC-3).

---

### KQ5. What leading university courses teach (with course pages)

#### Takeaway
Top programmes teach the same sequence:
1. CAPM as the equilibrium benchmark;
2. its empirical failures (the flat SML);
3. APT and multifactor models;
4. Fama-French factors and anomalies;
5. at PhD level, GMM/SDF tests, cross-sectional econometrics and the factor zoo.

Applied corporate finance keeps CAPM for cost of capital. That is the split P1 recommends for QUANTGEN: CAPM and factor models for measurement, characteristics for any signal.

#### Cited Findings
- **MIT Sloan 15.401 Finance Theory I (Andrew Lo, Fall 2008, OpenCourseWare).** Dedicated sessions on "Risk and Return", "Portfolio Theory", "The CAPM and APT" and "Efficient Markets"; text is Brealey-Myers-Allen. — [Syllabus](https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/pages/syllabus/); [Lecture notes](https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/pages/lecture-notes/)
- **MIT Sloan 15.433 Investments (Spring 2003, OCW).** Covers portfolio theory, CAPM and APT, empirical evidence on equity returns and time-varying expected returns, market efficiency and one lecture on behavioral finance; text is Bodie-Kane-Marcus. — [Syllabus](https://ocw.mit.edu/courses/15-433-investments-spring-2003/pages/syllabus/)
- **Chicago Booth (John Cochrane).**
  - *Asset Pricing* (revised edition) and a free online course: module 6 covers CAPM, ICAPM and APT; the econometrics modules cover GMM, time-series and cross-sectional tests, FF3 and momentum. — [Asset Pricing materials](https://www.johnhcochrane.com/asset-pricing)
  - PhD 35905 Empirical Asset Pricing: weeks 8-10 cover size, book-to-market, momentum, FF3 and anomalies, with Fama-French (1996, 2006) readings. — [Course page](https://www.johnhcochrane.com/empirical-asset-pricing)
  - Course list (35150 Advanced Investments MBA, 35904 Asset Pricing PhD, 35911 Advanced Asset Pricing). — [Teaching page](https://www.johnhcochrane.com/teaching)
  - A Stanford edition of the PhD class (Spring 2015) opened with the cross-section of returns and factor models. — [Stanford edition](https://www.johnhcochrane.com/asset-pricing-phd-class-stanford-edition)
- **Stanford GSB PhD finance.** Base requirements include FIN 620 Financial Markets I, FIN 625 Empirical Asset Pricing and FIN 638 Empirical Methods in Financial Economics; FIN 622 Dynamic Asset Pricing Theory is in the capital-markets track. — [Stanford GSB finance requirements](https://www.gsb.stanford.edu/programs/phd/fields/finance/requirements)
- **NYU Stern (Aswath Damodaran).** Corporate Finance (Spring 2025 syllabus; Spring 2026 lecture packets). The risk-and-return session compares CAPM, APT, multifactor and proxy models and keeps CAPM as the default. — [Course page](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/corpfin.html); [Lecture notes](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/cflect.htm); [Risk and return slides](https://pages.stern.nyu.edu/~adamodar/pdfiles/acf4E/presentations/risk&ret.pdf)
- **Wharton.** FNCE 2050/5050/7050 Investment Management covers factor models and the risk-return relation. FNCE 2570/5570/7570 Foundations of Asset Pricing covers mean-variance theory, capital-market equilibrium and APT. FNCE 2390 Behavioral Finance covers investor-bias inefficiencies. FNCE 2450 Hedge Funds teaches backtesting quantitative strategies. — [Penn catalog, FNCE](https://catalog.upenn.edu/courses/fnce/)
- **Yale ECON 252 Financial Markets (Robert Shiller, 2008, Open Yale).** Lecture 4 "Portfolio Diversification and Supporting Financial Institutions (CAPM Model)", Lecture 6 "Efficient Markets vs. Excess Volatility", Lecture 7 "Behavioral Finance". — [Open Yale ECON 252](https://oyc.yale.edu/economics/econ-252-08)
- **KAIST College of Business.** Finance programmes are the Financial MBA, the Master of Financial Engineering (two years, 54 credits including 19.5 required financial-engineering credits, a quant asset-management emphasis, and the KAIST Student Investment Fund) and the Digital Finance MBA. Course-level syllabi were not exposed on the pages fetched. — [KAIST College of Business](https://business.kaist.ac.kr/); [MFE programme](https://www.business.kaist.ac.kr/programs/02040201)

#### Inferences
- **The curriculum consensus matches P1's recommendation.** Students learn CAPM and APT as theory, learn that the SML is flat, and learn multifactor models mainly as performance-evaluation and pricing-error tools. Practitioners (Damodaran, the CFO survey) still use CAPM for discount rates. QUANTGEN should mirror this division of labour.
- **QUANTGEN's gate is itself a teachable artifact.** Its pre-registered gate (walk-forward, deflated Sharpe, PBO) operationalizes the PhD-level factor-zoo critique (Harvey-Liu-Zhu, Linnainmaa-Roberts) that most MBA syllabi only mention.

#### Gaps
- Korea University finance and economics course pages could not be retrieved: biz.korea.ac.kr returned no content and econ.korea.ac.kr failed robots and connection checks. No Korea University syllabus is cited.
- Stanford GSB MBA investment syllabi and Wharton syllabus PDFs were not publicly retrievable; only catalog descriptions are cited.

---

### KQ6. QUANTGEN translation: signal, risk model, or neither?

#### Takeaway
1. Make CAPM and multifactor models a mandatory risk and attribution layer on every card.
2. Do not use beta or factor loadings as return signals. Low-beta goes to BACKLOG, and only in a value-weighted, beta-neutral, alpha-judged form.
3. Use characteristics (not loadings) for at most two factor-tilt cards now: a Korea value + quarterly profitability composite, and a US quality composite.

Expected net IR for these cards is about 0.1-0.3. The gate is underpowered at that level, so REVISE or INSUFFICIENT DATA is the expected and acceptable verdict.

#### Cited Findings (inputs used below)
- QUANTGEN costs are 35 bp per side for KRX stocks, 50 bp per side for US shares via KIS and 5 bp per side for futures, all re-run at 2x. The gate's step 2 uses a Lo Sharpe confidence interval, step 5 requires one-sided p ≤ 0.10 against the benchmark, step 8 requires at least 60% positive calendar years, and step 9 applies a 60% live haircut. — `00_QUANTGEN_context.md` (local brief)
- Published gross long-short Sharpe ratios and turnover and decay facts are as cited in KQ2 and KQ3 (AMP 2013; HXZ; Kang 2016; Frazzini-Pedersen; Novy-Marx-Velikov 2016; Chen-Velikov; McLean-Pontiff via JKP; Jacobs-Müller).
- **Characteristics, not loadings.** Timely characteristics (monthly HMLm, quarterly ROE) dominate in model comparisons. — [Barillas-Shanken PDF](https://www.nber.org/system/files/working_papers/w21771/w21771.pdf)
- **Per-market models.** Local factor models beat global ones in developed and emerging markets. — [Fama-French 2012](https://econpapers.repec.org/RePEc:eee:jfinec:v:105:y:2012:i:3:p:457-472); [Cakici et al. 2013](https://ideas.repec.org/a/eee/ememar/v16y2013icp46-65.html)
- **Gate power (P1 calc).** Using the Lo (2002) i.i.d. standard error of the Sharpe ratio, SE ≈ √((1 + SR²/2)/T):

  | True annual Sharpe | OOS years needed for 90% CI to exclude zero | P(step 2 passes) with ~27 OOS years | P(at least 60% of 27 years positive) |
  |---|---|---|---|
  | 0.2 | 69 | 0.27 | 0.37 |
  | 0.3 | 31 | 0.45 | 0.54 |
  | 0.4 | 18 | 0.64 | 0.69 |
  | 0.5 | 12 | 0.79 | 0.82 |
  | 0.6 | 9 | 0.89 | 0.91 |
  | 0.8 | 5.6 | 0.98 | 0.98 |

  Probability that step 5 (one-sided p ≤ 0.10 on active returns) passes:

  | True IR | 27 OOS years | 10 OOS years |
  |---|---|---|
  | 0.20 | 0.40 | 0.26 |
  | 0.25 | 0.51 | 0.31 |
  | 0.30 | 0.61 | 0.37 |
  | 0.40 | 0.79 | 0.49 |

  Negative skew (momentum) lowers power further.

#### Inferences: the recommended design

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

#### Gaps
- Turnover and volatility assumptions in table B are P1 assumptions, not measured values. DC-3 and DC-4 should replace them.
- No retrieved source covers Korean retail short-selling feasibility, so long-only plus futures hedge is assumed as the implementable form.

---

## 4. Where and when it failed (dated episodes)

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

---

## 5. Data-check requests for the data lab

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

---

## 6. Claims ledger

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

## 7. Source list (all opened during this research)

**Papers (T1)**
1. Fama, E. & French, K. (2004). The Capital Asset Pricing Model: Theory and Evidence. JEP 18(3). https://www.aeaweb.org/articles?id=10.1257/0895330042162430; full text https://digitalcommons.dartmouth.edu/cgi/viewcontent.cgi?article=3446&context=facoa
2. Fama, E. & French, K. (1992). The Cross-Section of Expected Stock Returns. JF. https://ideas.repec.org/a/bla/jfinan/v47y1992i2p427-65.html
3. Frazzini, A. & Pedersen, L. (2014). Betting Against Beta. JFE. https://w4.stern.nyu.edu/facdir/lpederse/papers/BettingAgainstBeta.pdf
4. Novy-Marx, R. & Velikov, M. (2022). Betting Against Betting Against Beta. JFE 143(1). https://econpapers.repec.org/RePEc:eee:jfinec:v:143:y:2022:i:1:p:80-106
5. Hong, H. & Sraer, D. Speculative Betas. NBER w18548 (JF 2016). https://www.nber.org/papers/w18548
6. Baker, M., Bradley, B. & Wurgler, J. (2011). Benchmarks as Limits to Arbitrage. FAJ. https://pages.stern.nyu.edu/~jwurgler/papers/faj-benchmarks.pdf
7. Savor, P. & Wilson, M. (2014). Asset Pricing: A Tale of Two Days. JFE. https://ideas.repec.org/a/eee/jfinec/v113y2014i2p171-201.html
8. Hendershott, T., Livdan, D. & Rösch, D. (2020). Asset Pricing: A Tale of Night and Day. JFE. https://ideas.repec.org/a/eee/jfinec/v138y2020i3p635-662.html
9. Graham, J. & Harvey, C. (2001). The Theory and Practice of Corporate Finance. JFE. https://people.duke.edu/~charvey/Research/Published_Papers/P67_The_theory_and.pdf
10. Carhart, M. (1997). On Persistence in Mutual Fund Performance. JF. https://ideas.repec.org/a/bla/jfinan/v52y1997i1p57-82.html
11. Fama, E. & French, K. (2015). A Five-Factor Asset Pricing Model. JFE. https://www.sciencedirect.com/science/article/pii/S0304405X14002323
12. Hou, K., Xue, C. & Zhang, L. Digesting Anomalies: An Investment Approach. NBER w18435 (RFS 2015). https://www.nber.org/papers/w18435; PDF https://www.nber.org/system/files/working_papers/w18435/w18435.pdf
13. Stambaugh, R. & Yuan, Y. Mispricing Factors. NBER w21533 (RFS 2017). https://www.nber.org/papers/w21533; PDF https://www.nber.org/system/files/working_papers/w21533/w21533.pdf
14. Daniel, K., Hirshleifer, D. & Sun, L. Short- and Long-Horizon Behavioral Factors. NBER w24163 (RFS 2020). https://www.nber.org/system/files/working_papers/w24163/w24163.pdf
15. Barillas, F. & Shanken, J. Comparing Asset Pricing Models. NBER w21771 (JF 2018). https://www.nber.org/papers/w21771; PDF https://www.nber.org/system/files/working_papers/w21771/w21771.pdf
16. Fama, E. & French, K. (2012). Size, Value, and Momentum in International Stock Returns. JFE. https://econpapers.repec.org/RePEc:eee:jfinec:v:105:y:2012:i:3:p:457-472
17. Asness, C., Moskowitz, T. & Pedersen, L. (2013). Value and Momentum Everywhere. JF. https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf
18. Cakici, N., Fabozzi, F. & Tan, S. (2013). Size, Value, and Momentum in Emerging Market Stock Returns. EMR. https://ideas.repec.org/a/eee/ememar/v16y2013icp46-65.html
19. Harvey, C., Liu, Y. & Zhu, H. (2016). ...and the Cross-Section of Expected Returns. RFS. https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF
20. Hou, K., Xue, C. & Zhang, L. Replicating Anomalies. NBER w23394 (RFS 2020). https://www.nber.org/papers/w23394; Oct-2018 PDF https://theinvestmentcapm.com/uploads/1/2/2/6/122679606/replication2018oct.pdf
21. Jensen, T., Kelly, B. & Pedersen, L. Is There a Replication Crisis in Finance? NBER w28432 (JF 2023). https://www.nber.org/papers/w28432; PDF https://www.nber.org/system/files/working_papers/w28432/w28432.pdf
22. Chen, A. & Zimmermann, T. Open Source Cross-Sectional Asset Pricing. Federal Reserve FEDS 2021-037 (CFR 2022). https://www.federalreserve.gov/econres/feds/open-source-cross-sectional-asset-pricing.htm
23. Chen, A. & Velikov, M. (2023). Zeroing In on the Expected Returns of Anomalies. JFQA 58(3). https://www.cambridge.org/core/services/aop-cambridge-core/content/view/945133D5A3ECEEAF466AEE91551FD225/S0022109022000874a.pdf/zeroing-in-on-the-expected-returns-of-anomalies.pdf; Fed WP https://www.federalreserve.gov/econres/feds/files/2020039pap.pdf
24. Linnainmaa, J. & Roberts, M. The History of the Cross-Section of Stock Returns. NBER w22894 (RFS 2018). https://www.nber.org/papers/w22894; PDF https://www.nber.org/system/files/working_papers/w22894/w22894.pdf
25. Jacobs, H. & Müller, S. (2020). Anomalies Across the Globe: Once Public, No Longer Existent? JFE. https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html
26. Engelberg, J., McLean, R. D. & Pontiff, J. (2018). Anomalies and News. JF. https://ideas.repec.org/a/bla/jfinan/v73y2018i5p1971-2001.html
27. Kozak, S., Nagel, S. & Santosh, S. (2018). Interpreting Factor Models. JF. https://ideas.repec.org/a/bla/jfinan/v73y2018i3p1183-1223.html
28. Novy-Marx, R. & Velikov, M. A Taxonomy of Anomalies and Their Trading Costs. NBER w20721 (RFS 2016). https://www.nber.org/papers/w20721
29. Daniel, K. & Moskowitz, T. Momentum Crashes. NBER w20439 (JFE 2016). https://www.nber.org/papers/w20439; PDF https://www.nber.org/system/files/working_papers/w20439/w20439.pdf
30. Arnott, R., Harvey, C., Kalesnik, V. & Linnainmaa, J. (2021). Reports of Value's Death May Be Greatly Exaggerated. FAJ. https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf
31. Fama, E. & French, K. (2021). The Value Premium. RAPS. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3525096; https://academic.oup.com/raps/article/11/1/105/6125688
32. Asness, C., Frazzini, A., Israel, R., Moskowitz, T. & Pedersen, L. (2018). Size Matters, If You Control Your Junk. JFE. https://ideas.repec.org/a/eee/jfinec/v129y2018i3p479-509.html
33. Novy-Marx, R. (2013). The Other Side of Value: The Gross Profitability Premium. JFE. https://ideas.repec.org/a/eee/jfinec/v108y2013i1p1-28.html
34. Cochrane, J. Discount Rates. NBER w16972 (JF 2011). https://www.nber.org/papers/w16972
35. Kang, H. (2016). A Comparison of New Factor Models in the Korean Stock Market. Korea Finance Association conference paper. http://www.korfin.org/korfin_file/forum/2016co-conf19-3.pdf
36. Han, Lee & Kang (2020). Market Anomalies in the Korean Stock Market. Journal of Derivatives and Quantitative Studies 28(2). https://www.emerald.com/jdqs/article/28/2/3/206237/Market-anomalies-in-the-Korean-stock-market
37. Kim, S. (2021). Enhanced Factor Investing in the Korean Stock Market. Pacific-Basin Finance Journal. https://ideas.repec.org/a/eee/pacfin/v67y2021ics0927538x21000652.html
38. Fama, E. & French, K. (2018). Choosing Factors. JFE (abstract only; ranks models by maximum squared Sharpe). https://ideas.repec.org/a/eee/jfinec/v128y2018i2p234-252.html

**Data libraries and official sources (T1)**
39. Kenneth R. French Data Library (current returns through August 2026). https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
40. JKP Global Factor Data. https://jkpfactors.com/; https://jkpfactors.com/data; https://jkpfactors.com/analysis
41. Open Source Asset Pricing. https://www.openassetpricing.com/
42. AMRO (30 Mar 2026). Narrowing the Korea Discount: Stock Market Reform via Corporate Value-up. https://www.amro-asia.org/narrowing-the-korea-discount-stock-market-reform-via-corporate-value-up

**Asset manager and index provider research and data (T2)**
43. AQR: Momentum in Japan (Asness 2011). https://www.aqr.com/Insights/Research/Journal-Article/Momentum-in-Japan-The-Exception-That-Proves-the-Rule
44. AQR: How Do Factor Premia Vary Over Time? (Ilmanen et al.). https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence
45. AQR: Trading Costs of Asset Pricing Anomalies (Frazzini, Israel, Moskowitz). https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies
46. AQR: Value and Momentum Everywhere (landing page). https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere
47. MSCI factsheets, 31 Aug 2026:
    - World Minimum Volatility: https://www.msci.com/documents/10199/255599/msci-world-minimum-volatility-index.pdf
    - World Quality: https://www.msci.com/documents/10199/255599/msci-world-quality-index.pdf
    - World Value: https://www.msci.com/documents/10199/255599/msci-world-value-index.pdf
    - USA Momentum: https://www.msci.com/documents/10199/255599/msci-usa-momentum-index.pdf
    - USA Quality: https://www.msci.com/documents/10199/255599/msci-usa-quality-index.pdf
    - USA: https://www.msci.com/documents/10199/255599/msci-usa-index-gross.pdf
    - Korea: https://www.msci.com/documents/10199/255599/msci-korea-index.pdf
    - EM Value: https://www.msci.com/documents/10199/255599/msci-emerging-markets-value-index.pdf
    - Japan Value: https://www.msci.com/documents/10199/255599/msci-japan-value-index.pdf
    - Europe Value: https://www.msci.com/documents/10199/255599/msci-europe-value-index.pdf
    - World Small Cap: https://www.msci.com/documents/10199/255599/msci-world-small-cap-index.pdf
48. MSCI (29 Jul 2025). Factor Indexing Through the Decades (landing page; gated). https://www.msci.com/downloads/web/msci-com/research-and-insights/paper/factor-indexing-through-the-decades/factor-indexing-through-the-decades.pdf
49. iShares fund pages:
    - MTUM: https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf
    - VLUE: https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf
    - QUAL: https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf
    - USMV: https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf
    - SIZE: https://www.ishares.com/us/products/251465/ishares-msci-usa-size-factor-etf
    - IWD: https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf
    - IWF: https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf
    - IWM: https://www.ishares.com/us/products/239710/ishares-russell-2000-etf
    - IWB: https://www.ishares.com/us/products/239707/ishares-russell-1000-etf
    - EWY: https://www.ishares.com/us/products/239681/ishares-msci-south-korea-capped-etf

**University course pages (T1)**
50. MIT OCW 15.401 (Lo, Fall 2008): https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/pages/syllabus/; https://ocw.mit.edu/courses/15-401-finance-theory-i-fall-2008/pages/lecture-notes/
51. MIT OCW 15.433 Investments (Spring 2003): https://ocw.mit.edu/courses/15-433-investments-spring-2003/pages/syllabus/
52. Chicago Booth / Cochrane:
    - https://www.johnhcochrane.com/asset-pricing
    - https://www.johnhcochrane.com/teaching
    - https://www.johnhcochrane.com/empirical-asset-pricing
    - https://www.johnhcochrane.com/asset-pricing-phd-class-stanford-edition
53. Stanford GSB PhD finance requirements: https://www.gsb.stanford.edu/programs/phd/fields/finance/requirements
54. NYU Stern / Damodaran:
    - https://pages.stern.nyu.edu/~adamodar/New_Home_Page/corpfin.html
    - https://pages.stern.nyu.edu/~adamodar/New_Home_Page/cflect.htm
    - https://pages.stern.nyu.edu/~adamodar/pdfiles/acf4E/presentations/risk&ret.pdf
55. Wharton FNCE catalog: https://catalog.upenn.edu/courses/fnce/
56. Yale ECON 252 (Shiller, 2008): https://oyc.yale.edu/economics/econ-252-08
57. KAIST College of Business: https://business.kaist.ac.kr/; MFE programme https://www.business.kaist.ac.kr/programs/02040201

**Local brief**
58. `/home/claude/research_notes/QUANTGEN technical and fundamental signals/00_QUANTGEN_context.md` (QUANTGEN costs, gate, prior design, macro decisions).
