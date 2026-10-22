# E4 position paper: fundamental and "quantamental" equity signals for QUANTGEN

As of 2 October 2026 (Asia/Seoul). Panel: finance-career executives. Claim IDs E4-C01 to E4-C30. Every number is labelled with market, period, in-sample (IS) or out-of-sample (OOS), and gross or net where the source allows. "Own calc" means I computed it from a dataset named in the line; the method is given so the data lab can reproduce it.

---

## 1. Persona and position summary

**Persona (fictional composite).** E4 is not a real person and does not speak for any real firm. E4 is a former Head of US Equity Research at the broker-dealer of a large US bank (BofA/Merrill-style), later a fundamental long/short portfolio manager. E4 knows how consensus estimates, ratings and target prices are produced and why they are biased. E4 has lived through crowded-book unwinds (August 2007), the 2008 value trap in financials, the 2009 junk rally and the 2023-2026 mega-cap concentration. E4 judges a signal on three questions. Can an individual investor compute it point-in-time from public filings? Does it survive QUANTGEN's costs (KRX stock 35 bp, US shares 50 bp per side, both re-run at 2x)? Can it clear a benchmark-relative gate?

**Position summary**
1. Three fundamental signals combine good evidence, robustness and public-data availability: profitability (gross profits/assets), net share issuance/payout, and value. Value works only as a low-weight partner to profitability and momentum, never alone. In my calculation from Ken French data, US HML had a Sharpe ratio of 0.60 in 1963-2006 and −0.17 in 2007-2017/03.
2. Earnings momentum explains most of price momentum: earnings-surprise and announcement-return factors subsume UMD, and net Sharpe was 0.55 versus 0.33 in the US over 1975-2012. But post-earnings drift (PEAD) in large US stocks has been about zero since roughly 2006, and the strategy costs about 46 bp per month to trade. **QUANTGEN should not build a standalone US PEAD card.** The prior map gives Korean earnings drift a weight of 3; I found no Korean evidence for that weight, so it must be tested with DART timestamps first.
3. Sell-side output is useful only as changes, not levels:
   - consensus recommendation levels did not survive costs, and in 2000-01 they inverted;
   - twelve-month target prices sit about 28% above the price, and only 38% are met within 12 months;
   - analysts' long-term growth (LTG) forecasts are inversely related to returns: 3% a year for the highest-LTG stocks against 15% for the lowest.
   Revisions are well documented, but QUANTGEN has no point-in-time consensus history. **The right step is to start archiving KIS and FMP snapshots now.**
4. Buying by "opportunistic" insiders is the most credible event signal in public filings: US value-weighted alpha of 82 bp per month over 1986-2007, with a two-business-day Form 4 lag. It belongs as an overlay, not a factor. Short interest is a filter on longs (and a possible macro risk-sizing input). 13F cloning is not an alpha source after the 45-day lag: the hedge-fund-clone ETF index lagged the S&P 500 by about 3 pp a year over ten years.
5. Practitioner hybrids (CANSLIM/IBD, Minervini SEPA/VCP) bundle parts that each have an academic analogue. I found no independent out-of-sample test of either composite. The live IBD 50 ETF has returned 3.5% a year since April 2015 against roughly 13-14% for the S&P 500. Treat both as T3 descriptions.
6. Mixing fundamentals with technicals works in two cases:
   - when momentum is used as a diversifying sleeve or a confirmation filter (value and momentum are negatively correlated; a 50/50 US mix had Sharpe 0.63 against 0.29 and 0.33 in 1972-2011);
   - when earnings-momentum sleeves get the same bear-state protection as price momentum (the SUE strategy also crashed in spring 2009).
7. Long-only quality is not a crash hedge:
   - QUAL fell −34.1% against −33.9% for the S&P 500 from 19 February to 23 March 2020;
   - the MSCI USA quality index lost −20.3% against −18.1% for the S&P 500 in 2022.
   The defensive object is the academic long/short QMJ factor, and an individual cannot short.
8. Concentration is the main threat to any diversified fundamental tilt:
   - **US:** the top ten S&P 500 stocks were about 41% of the index at end-2025, against about 19% at end-2015;
   - **Korea:** Samsung Electronics plus SK hynix were 50.8% of KOSPI market cap on 29 September 2026; the median KOSPI stock was −5.9% year to date while the cap-weighted universe was +64%.
9. What QUANTGEN should build:
   - a point-in-time fundamental layer keyed to filing timestamps (DART rcept_dt; EDGAR and Form 4 dates);
   - a small pre-registered composite: profitability, issuance and value, plus an earnings-momentum term tested in Korea first;
   - filters: F-score inside the cheap bucket, extreme accruals, high days-to-cover, recent downgrades and the highest-LTG names;
   - all expressed as long-only tilts against a concentration-capped benchmark.
   My judgment for such a composite is a backtest information ratio (IR) of 0.3-0.5 net of 1x costs, and 0.12-0.2 live after the 60% haircut. That is below the prior map's 0.3-0.5 for quality alone.
10. Statistical power binds the gate. With one-sided p ≤ 0.10, an IR of 0.3 needs about 18 years of out-of-sample data to pass gate step 5. DART financial statements are available by API only from 2015, so a Korean fundamental card can only prove an IR of about 0.4-0.5 or more. **Expect REVISE or INSUFFICIENT DATA unless the effects are larger than the literature suggests.**

---

## 2. Key question A: estimate revisions, earnings momentum, surprises/PEAD, the announcement premium and guidance

### Takeaway
Earnings momentum (surprises, announcement returns, analyst revisions) is the best-documented fundamental return predictor and explains most of price momentum. But in liquid stocks the tradable drift has decayed sharply: large-cap US PEAD has been about zero since around 2006, and the signal needs high turnover. For QUANTGEN it is a Korea test candidate and a confirmation input, not a standalone US card.

### Cited Findings
- **Chan-Jegadeesh-Lakonishok (1996, JF), US:** past return and past earnings surprise each predict large drifts after controlling for the other; there is little sign of later reversal; analysts revise forecasts sluggishly — [EconPapers abstract](https://econpapers.repec.org/article/blajfinan/v_3a51_3ay_3a1996_3ai_3a5_3ap_3a1681-1713.htm); [NBER w5375](https://www.nber.org/papers/w5375).
- **Open Source Asset Pricing (OSAP) replication file, original-paper statistics (US, IS, gross, mostly equal-weighted):**
  - forecast revisions REV6 (CJL 1996; 1977-1992): t = 4.07 in regressions;
  - EPS forecast revision (Hawkins-Chamberlin-Daniel 1984; 1975-1980): 0.46% a month long-only CAPM alpha, t 3.17;
  - announcement return (CJL 1996): t 9.25;
  - earnings-surprise streak (Loh-Warachka 2012; 1987-2009): 0.96% a month FF3 alpha, t 9.51;
  - revenue surprise (Jegadeesh-Livnat 2006; 1987-2003): significant in event studies;
  - all are graded "1_clear" by OSAP.
  — [OSAP SignalDoc.csv](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv)
- **OSAP reproduction rate:** of 161 predictors that were clearly significant in the original papers, 98% reproduce with t > 1.96; the slope of reproduced on original t-statistics is 0.88 (R² 82%) — [Chen & Zimmermann, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3604626).
- **Novy-Marx (2015), US, January 1975 to December 2012, IS:**
  - UMD 0.64% a month (t 3.03); SUE 0.59% (t 7.14); CAR3 0.53% (t 8.42);
  - UMD's alpha after controlling for SUE and CAR3 is −0.48% (t −2.55);
  - SUE and CAR3 stay significant after controlling for UMD (t 5.31 and 6.18);
  - adding the earnings factors raises the adjusted R² of UMD from 5.8% to 40.6%;
  - **net of modelled costs, Sharpe ratios are UMD 0.33, SUE 0.55, combined 0.57, market 0.48;**
  - SUE suffered a large drawdown in the spring-2009 momentum crash; SUE conditioned on (orthogonal to) price momentum avoided the crash, with a maximum loss of 8.7% against 21.4% unconditional.
  — [NBER w20984 PDF](https://www.nber.org/system/files/working_papers/w20984/w20984.pdf)
- **Martineau (Critical Finance Review, 2022):** PEAD has not existed in large stocks since 2006 and has recently disappeared in microcaps (paper revised August 2021) — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607).
- **Two 2025 papers claiming PEAD survives, as reviewed by Subrahmanyam:**
  - Dickerson-Julliard-Mueller use an announcement-return earnings factor: t = 2.18 with all stocks, falling to 1.43 without microcaps;
  - Hirshleifer-Peng-Wang report t ≈ 14 but do not filter microcaps;
  - microcaps are about 3% of market value, so Martineau's conclusion may hold for liquid stocks.
  — [UCLA Anderson Review](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/)
- **Kettell-McInnis-Zhao, US 1974-2020:** SUE hedge returns fell from about 5% (five-year moving average, 1980s-1990s) to about 3% or less by the late 2010s. The trend is about −2 bp per quarter and becomes insignificant once declining earnings persistence is controlled for. The 5% and 3% levels are read off a figure. — [Columbia CEASA PDF](https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf)
- **Costs (US, value-weighted, Novy-Marx-Velikov 2016, Table 3):** PEAD/SUE gross 0.72% a month, cost 46 bp, **net 0.26% (t 1.60)**, one-sided turnover 35.07% a month. Strategies with one-sided monthly turnover under 50% mostly stay significant net; few above that do — [NBER w20721 PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf); [abstract](https://www.nber.org/papers/w20721).
- **News days (97 US anomalies):** anomaly returns are 50% higher on corporate news days and 6 times higher on earnings-announcement days, which is most consistent with biased expectations being corrected on news — [Engelberg-McLean-Pontiff, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2631228).
- **Earnings announcement premium (Frazzini-Lamont), US January 1972 to December 2004, IS, gross:**
  - long expected announcers against non-announcers earned 61 bp a month (about 7% a year), or 72 bp with a fiscal-year-end method;
  - by subperiod: 0.396% a month (1973-83), 0.521% (1984-93), 0.915% (1994-2004);
  - high past-announcement-volume stocks earned 153 bp against 39 bp for low;
  - the premium is strong in large caps.
  — [NBER w13090 PDF](https://www.nber.org/system/files/working_papers/w13090/w13090.pdf)
- **The premium globally:** 9 of the 20 countries with enough data show a significantly positive premium; it is strongest where idiosyncratic volatility rises most around announcements — [Barber-De George-Lehavy-Trueman 2013 JFE](https://econpapers.repec.org/article/eeejfinec/v_3a108_3ay_3a2013_3ai_3a1_3ap_3a118-138.htm).
- **Guidance and disclosure:**
  - managers on average delay bad news, so negative reactions to bad-news disclosures are larger than positive reactions to good news — [Kothari-Shu-Wysocki 2009 JAR](https://ideas.repec.org/a/bla/joares/v47y2009i1p241-276.html);
  - firms that stop quarterly guidance had poorer prior performance and more uncertainty; announcing the stop brought negative three-day returns, then higher analyst dispersion and lower forecast accuracy — [Chen-Matsumoto-Rajgopal 2011 JAE](https://ideas.repec.org/a/eee/jaecon/v51y2011i1p134-150.html);
  - across about 4,000 US firms with revenue above $500m (1994-2004), guidance did not raise valuation multiples; of 126 firms that stopped, 58 beat and 68 lagged the market, which the authors attribute to underlying performance — [McKinsey 2006](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/the-misguided-practice-of-earnings-guidance).
- **Lord Abbett (asset manager, T2, November 2025):** SUE strategies have been superior to cross-sectional price momentum with smaller drawdowns, and the firm proposes "confirmed momentum" (price plus operating momentum). The report gives no new statistics — [Lord Abbett PDF](https://www.lordabbett.com/content/dam/lordabbett-captivate/documents/insights/InvestmentPerspectives/2025/11425-the-benefits-of-price-and-operating-momentum-in-equity-portfolios-non-us.pdf).

### Inferences
- QUANTGEN does not need consensus data to compute earnings momentum. **CAR3** (three-day abnormal return around the filing) and **time-series SUE** (seasonal EPS change scaled by its own volatility) need only OHLCV, filing timestamps and reported EPS. All three are available from OpenDART/marcap for Korea and from FMP/EDGAR for the US.
- **US:** at 50 bp per side and about 35% monthly one-sided turnover, a long-only PEAD tilt costs about 4.2% a year (8.4% at 2x) by my arithmetic: 2 × 0.35 × 12 × 0.50%. That exceeds any plausible drift in the large, KIS-tradable stocks QUANTGEN can reach after 2006. Expected live net Sharpe is ≤ 0.
- **Korea:** at 35 bp the same tilt costs about 2.9% a year (5.9% at 2x), so it needs more than about 3% a year of gross drift in liquid names. Korean firms often publish preliminary results through exchange (I-type) disclosures before the periodic report. The event clock should therefore be the first public disclosure, the earliest rcept_dt among I-type preliminary-results filings and A001-A003 periodic reports. This is a design inference, not a sourced fact about any firm.
- The announcement premium is a calendar effect: hold names into their expected report month. In Korea reports cluster in a few weeks, so it partly becomes a market-timing effect and must be tested before use.
- Guidance is mainly a risk screen. Stopped guidance and negative pre-announcements are red flags because bad news is withheld and then released in bulk.
- **Earnings-momentum sleeves should get the same bear-state gate as price momentum.** SUE crashed in spring 2009 (Novy-Marx), and the macro research applied the Daniel-Moskowitz gate only to price momentum.

### Gaps
- I found no post-2010 public evidence on revision breadth (bank research pages were not reachable, and the session's web-search budget was used up).
- I retrieved no Korean evidence on PEAD, revisions or the announcement premium. The prior map's Korea weight of 3 for earnings drift is unverified in this note.
- The sample periods of the two 2025 papers (Dickerson-Julliard-Mueller; Hirshleifer-Peng-Wang) are not stated in the source I read.
- I did not confirm whether Korea is among Barber et al.'s nine significant countries.
- The Anilowski-Feng-Skinner (2007) abstract was unavailable ("no abstract" on IDEAS), and I have no numbers on the size of guidance effects.

---

## 3. Key question B: sell-side information (recommendations, optimism, target prices)

### Takeaway
Analyst outputs carry information mainly in their changes, and mostly on the negative side (downgrades). Levels are biased: optimistic growth and inflated targets. Consensus-recommendation strategies did not survive costs and inverted badly in 2000-01. QUANTGEN should store analyst data point-in-time and use only revisions and downgrades, never target-price upside.

### Cited Findings
- **Womack (1996, JF), US:** after new buy recommendations, drift averages +2.4% and fades quickly; after sell recommendations, drift is about −9.1% and lasts six months — [EconPapers](https://econpapers.repec.org/article/blajfinan/v_3a51_3ay_3a1996_3ai_3a1_3ap_3a137-67.htm).
- **Barber-Lehavy-McNichols-Trueman (2001, JF), US (1985-1997 per OSAP):** long the most favourable consensus and short the least, rebalanced daily, earned more than 4% a year abnormal gross. Slower rebalancing cut that, and **net returns were not reliably above zero** — [EconPapers](https://econpapers.repec.org/article/blajfinan/v_3a56_3ay_3a2001_3ai_3a2_3ap_3a531-563.htm); [OSAP row ConsRecomm](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **Barber et al. (2003, FAJ), 2000-2001:**
  - least-favoured stocks returned +13.44% a year market-adjusted while the most recommended returned −7.06%, a spread of about −20 pp;
  - the spread was about −25 pp in 2000 and −16 pp in 2001, in both tech and non-tech;
  - analysts kept recommending small-cap growth stocks.
  — [EconPapers](https://econpapers.repec.org/article/tafufajxx/v_3a59_3ay_3a2003_3ai_3a2_3ap_3a88-96.htm)
- **Changes in recommendations (Jegadeesh-Kim-Krische-Lee 2004, US 1985-1998):** 0.225% a month (p < 0.01) in the original paper; OSAP marks it as lacking data before 1993 — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **Target prices, Brav-Lehavy (2003, JF), US 1997-1999:** the market reacts significantly to target-price revisions; on average the 12-month target is 28% above the current price — [EconPapers](https://econpapers.repec.org/article/blajfinan/v_3a58_3ay_3a2003_3ai_3a5_3ap_3a1933-1967.htm).
- **Target prices, Bradshaw-Brown-Huang (2013, RAST), US 2000-2009:**
  - implied target-price returns exceed actual returns by 15% on average;
  - absolute target-price errors average 45%;
  - 38% of targets are met at the 12-month horizon and 64% at some point within it;
  - evidence of persistent analyst skill is economically weak.
  — [IDEAS](https://ideas.repec.org/a/spr/reaccs/v18y2013i4d10.1007_s11142-012-9216-5.html)
- **Optimism in aggregate (McKinsey, 2010):** over about 25 years, forecast earnings growth was 10-12% a year against about 6% realised. Actual growth beat forecasts in only two years, both post-recession recoveries, and the optimism persisted after Reg FD, SOX and the Global Settlement — [McKinsey](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/equity-analysts-still-too-bullish).
- **Long-term growth optimism (Bordalo-Gennaioli-La Porta-Shleifer), US December 1981 to December 2016:**
  - the highest-LTG portfolio earned about 3% a year and the lowest about 15%;
  - for the high-LTG group, the earnings path implied by forecasts by year 3 (0.70 in the paper's units) far exceeded the realised path (0.21);
  - LTG is cut most sharply in the first year.
  — [NBER w23863 PDF](https://www.nber.org/system/files/working_papers/w23863/w23863.pdf). La Porta's (1996) original LTG result has t 4.9 — [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **Data access, Korea:** KIS exposes three relevant endpoints — [KIS GitHub estimate_perform](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/estimate_perform/estimate_perform.py); [invest_opinion](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/invest_opinion/invest_opinion.py); [field map](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/invest_opinion/chk_invest_opinion.py); [invest_opbysec](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/invest_opbysec/invest_opbysec.py):
  - **consensus estimates ("estimate-perform"):** API 국내주식-187, tr_id HHKST668300C0;
  - **per-stock opinions ("invest-opinion"):** 국내주식-188, with fields for date, opinion, previous opinion, target price (hts_goal_prc), prior close and gap ratio, queried by date range;
  - **opinions by broker ("invest-opbysec"):** 국내주식-189.
- **Data access, US:** FMP documents a financial-estimates API, stock grades and historical grades, price-target summary and consensus, and earnings calendar/report endpoints (actual against estimate) — [FMP docs](https://site.financialmodelingprep.com/developer/docs).

### Inferences
- **Use downgrades, not upgrades.** The asymmetric drift in Womack fits E4's desk experience that sell ratings are rare and costly for analysts to issue. A "downgraded in the last 30-60 days" exclusion screen is the cheapest sell-side feature. KIS's previous-opinion field makes changes detectable without a separate history, but only from the date QUANTGEN starts polling.
- **Never treat target-price upside or LTG as expected return.** Both are biased levels. The highest-LTG decile is a glamour flag, a candidate exclusion screen.
- Revision breadth (analysts raising minus analysts cutting, over the number of estimates) is the practitioner standard. QUANTGEN cannot backtest it honestly without point-in-time history. The gate needs 756 + 126 sessions (about 3.5 years) of archived snapshots before a first verdict.

### Gaps
- I could not retrieve the abstract of Jegadeesh-Kim-Krische-Lee (2004): Wiley returned 403, Semantic Scholar and OpenAlex returned 429, and IDEAS returned 404. The commonly cited finding that recommendation levels tilt toward glamour and momentum stocks is therefore not verified here beyond the OSAP row.
- I found no post-2010 evidence on recommendation or target-price performance.
- I found no evidence on Korean analyst optimism (for example the share of sell ratings).
- The history depth of KIS estimate and opinion data, and whether FMP's estimate history is point-in-time, are unknown.

---

## 4. Key question C: short interest, insiders and 13F/best-ideas cloning

### Takeaway
- **Insider buying:** opportunistic purchases are the strongest public-filing event signal, and the Form 4 lag is short.
- **Short interest:** informative at both the market and the stock level, but the public stock-level data are slow (twice a month) and dangerous to read naively (squeezes). Use it as a long-side filter, and at the market level only as a risk-sizing input under the macro rules.
- **13F cloning:** best ideas outperform on paper, but cloning after the 45-day lag has not beaten the index in a live product.

### Cited Findings
- **Insider trading, Lakonishok-Lee (RFS 2001), NYSE/Amex/Nasdaq 1975-1995:** insiders act as contrarians, predict market moves better than simple contrarian rules, and predict the cross-section, especially in smaller firms; **purchases are more informative than sales** — [NBER w6656](https://www.nber.org/papers/w6656).
- **Jeng-Metrick-Zeckhauser, US 1975-1996:** the insider-purchase portfolio earns about 40 bp a month abnormal; about one sixth arrives within five days and about one third within the first month; the sales portfolio earns no abnormal return — [NBER w6913](https://www.nber.org/papers/w6913).
- **Cohen-Malloy-Pomorski (JF 2012), US January 1986 to December 2007:**
  - "routine" traders traded in the same calendar month for at least three consecutive years (55% of trades); all others are "opportunistic" (45%);
  - opportunistic buys minus sells earn a five-factor alpha of **82 bp a month (t 2.15) value-weighted**, about 9.8% a year, and 180 bp (t 6.07) equal-weighted;
  - routine trades show no signal (value-weighted −20 bp, t −0.57);
  - opportunistic sells earn an additional −78 bp (t 5.67);
  - returns build for about six months with no reversal; the median reporting lag in the sample was 3 days;
  - costs were not modelled.
  — [NBER w16454 PDF](https://www.nber.org/system/files/working_papers/w16454/w16454.pdf)
- **Form 4 deadline:** before the end of the second business day after the transaction — [SEC Form 4](https://www.sec.gov/about/forms/form4.pdf).
- **Korean insider rules (FSC):**
  - insiders must disclose planned trades 30 days in advance, effective **24 July 2024**;
  - trades under 1% of shares over six months and under KRW 5bn in total are exempt, as are pension funds, collective investment vehicles, banks and insurers.
  — [FSC press releases, "insider"](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=insider)
- **Korean insider data:** OpenDART's officer and major-shareholder ownership report API (elestock) returns receipt number and date (rcept_dt), reporter, position, shares held and change, and ownership ratio and change — [OpenDART elestock guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS004&apiId=2019022).
- **Aggregate short interest, Rapach-Ringgenberg-Zhou (JFE 2016), US 1973-2014:**
  - in-sample R² 1.24% monthly and 12.89% annual;
  - **out-of-sample R² 1.94% (1 month), 6.54% (3 months), 11.70% (6 months), 13.24% (12 months);**
  - a mean-variance investor would pay 343-544 bp a year for the forecasts, about 1,100 bp in the 2008 crisis period;
  - the predictive power works mainly through a cash-flow channel;
  - described as "arguably the strongest known predictor of aggregate stock returns".
  — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0304405X16300320)
- **Stock-level shorting:**
  - NYSE 2000-2004, proprietary order data: shorting is more than 12.9% of volume; heavily shorted stocks underperform lightly shorted ones by 1.16% over the next 20 trading days (15.6% annualised), and by 1.43% the next month when shorted by institutions — [Boehmer-Jones-Zhang 2008](https://econpapers.repec.org/article/blajfinan/v_3a63_3ay_3a2008_3ai_3a2_3ap_3a491-527.htm);
  - days-to-cover (short ratio divided by daily turnover) beats the plain short ratio; a long/short DTC strategy earns 1.2% a month — [Hong et al., NBER w21166](https://www.nber.org/papers/w21166);
  - overvaluation appears only when short-sale constraints and dispersion of opinion occur together — [Boehme-Danielsen-Sorescu 2006 JFQA](https://econpapers.repec.org/article/cupjfinqa/v_3a41_3ay_3a2006_3ai_3a02_3ap_3a455-487_5f00.htm);
  - OSAP rows: short interest (Dechow et al. 2001, 1976-1993) 35 bp spread, graded "2_likely"; low analyst recommendations combined with high short interest (Drake-Rees-Swanson 2011, 1994-2006) 1.11% a month (t 4.09) — [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **Public short-interest data (FINRA):** firms report twice a month, by 6 p.m. ET on the second business day after the settlement date; FINRA publishes about a week after the filing deadline — [FINRA](https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest).
- **Squeeze risk (GME, SEC staff):** GameStop short interest reached 122.97% of float in January 2021, with an intraday high of $483.00 on 28 January, about +2,700% from the 8 January low. The staff attribute the sustained rise to positive sentiment rather than buying to cover — [SEC staff report](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf).
- **Korean short-selling regime (FSC):**
  - temporary ban 10 August to 9 November 2011;
  - partial resumption for KOSPI 200 and KOSDAQ 150 from 3 May 2021;
  - full ban from **6 November 2023**, extended;
  - revised rules on 18 February 2025, including a 12-month repayment limit for institutions;
  - full reinstatement from **31 March 2025**;
  - KRW 26.52bn of penalties on global investment banks for naked shorting (26 December 2023).
  — [FSC press releases, "Short Selling"](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Short%20Selling)
- **13F rules:** managers with at least $100m in 13(f) securities must file within 45 days after quarter-end, reporting long positions only, not shorts — [SEC 13F FAQ](https://www.sec.gov/divisions/investment/13ffaq.htm).
- **Best ideas (Cohen-Polk-Silli):** the stock active managers show the most conviction in beats the market by about 1.6-2.1% per quarter; their other holdings show no meaningful outperformance — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364827).
- **Mimicking Berkshire (Martin-Puthenpurackal), 1976-2006:** buying Berkshire's disclosed positions at the start of the month after disclosure earned abnormal returns of 10.75% over the S&P 500 — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=806246).
- **Live 13F-clone product, Global X GURU (Solactive Guru Index, hedge-fund conviction ideas), to 30 September 2026:** expense ratio 0.75%; inception 4 June 2012 — [Global X GURU](https://www.globalxetfs.com/funds/guru/).

  | Period | NAV (% a year) | Index (% a year) |
  |---|---|---|
  | 1 year | 13.60 | 14.47 |
  | 3 years | 23.44 | 24.14 |
  | 5 years | 7.07 | 7.37 |
  | 10 years | 11.80 | 12.04 |
  | Since inception | 12.10 | 12.45 |

- **S&P 500 comparison (benchmark of the iShares IVV ETF, mid-2026):**

  | Period | Cumulative | Annualised (own conversion) |
  |---|---|---|
  | 1 year | 22.32% | 22.32% |
  | 3 years | 75.47% | ≈20.6% |
  | 5 years | 87.57% | ≈13.4% |
  | 10 years | 322.71% | ≈15.5% |

  — [iShares IVV](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf). The as-of dates (June and August 2026) differ from GURU's 30 September 2026, so the comparison is approximate.
- **13F ownership breadth (Chen-Hong-Stein 2002, 1979-1998):** quarterly change in the number of 13F owners, 0.67 (t 3.96) — [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **FMP data:** documents latest, search and statistics endpoints for insider trades, and a Form 13F suite; a short-interest endpoint was not listed — [FMP docs](https://site.financialmodelingprep.com/developer/docs).

### Inferences
- Opportunistic insider buying is a credible **US overlay**. My rough conversion of the value-weighted t-statistic (2.15 over 22 years) gives a gross Sharpe of about 0.46. After a post-publication haircut (McLean-Pontiff −58%), restriction to the larger stocks QUANTGEN can trade, and about 1.0-1.4% a year of US costs on a six-month hold, the live information ratio is roughly 0.05-0.15. Worth having as a tilt, not as a card.
- **Korea's 2024 pre-disclosure rule changes the game.** Large insider trades are now announced about 30 days ahead, so a "planned insider buy" event exists that has no US analogue. It is untested.
- **Short interest:** exclude top-decile days-to-cover names from the long book. Do not build a factor from it.
  - In Korea, the 6 November 2023 to 30 March 2025 ban breaks the series, so any Korean short-interest feature needs regime handling.
  - Aggregate short interest is a direction predictor. Under the macro decisions it may only scale exposure inside [0.5, 1.0]. **I flag this conflict: Rapach-Ringgenberg-Zhou is direction evidence, and QUANTGEN can use it only as a de-risking input.**
- **13F cloning: DROP as an alpha source.** Over 2016-2026 the live GURU index lagged the S&P 500 by about 3.5 pp a year over 10 years and about 6 pp a year over 5 years. Breadth change is a possible minor US feature for the backlog.

### Gaps
- The sample period of Cohen-Polk-Silli was not verified (the abstract does not state it), and the Martin-Puthenpurackal 10.75% should be confirmed as an annual figure.
- I did not retrieve the "copycat funds" literature (Frank-Poterba-Shackelford-Shoven); the NBER number I tried was wrong.
- The Agarwal-Jiang-Tang-Yang (2013) abstract was unavailable.
- I found no Korean evidence on insider trading or short interest.
- KRX/KIS short-sale balance data, their lag and their history are not verified.
- Post-2007 performance of opportunistic insider signals is not verified.

---

## 5. Key question D: practitioner hybrids (CANSLIM/IBD, Minervini SEPA/VCP, quality at a reasonable price, Piotroski in practice)

### Takeaway
Each building block of the practitioner hybrids maps to a documented anomaly, but the composites themselves lack independent out-of-sample evidence.
- **CANSLIM/IBD:** the only live record I found is poor; the IBD 50 ETF returned 3.5% a year against roughly 13-14% for the S&P 500 since April 2015.
- **Minervini SEPA/VCP:** supported by contest claims and testimonials, not tests.
- **Quality at a reasonable price (profitable value):** the best-supported hybrid.
- **Piotroski F-score:** works mainly in small, illiquid, unfollowed cheap stocks, so it is a value-trap filter, not a large-cap engine.

### Cited Findings
- **CANSLIM components and their academic analogues** (from the OSAP file and the papers cited):

  | CANSLIM letter | Academic analogue | Evidence |
  |---|---|---|
  | C/A (current and annual earnings growth) | earnings surprise and streaks | Loh-Warachka t 9.51; Foster-Olsen-Shevlin event drift |
  | N (new highs) | 52-week-high proximity (George-Hwang 2004, 1963-2001) | 0.45% a month, t 2.0, graded "2_likely" (sign depends on January) |
  | L (leader) | price momentum (Jegadeesh-Titman 1993) | 1.31% a month, t 3.74 |
  | I (institutional sponsorship) | 13F breadth change | t 3.96 |
  | M (market direction) | market-state conditioning | Cooper-Gutierrez-Hameed 2004: momentum earned 0.93% a month after up markets and −0.37% after down markets, 1929-1995 |

  — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv); [Cooper-Gutierrez-Hameed via OpenAlex](https://api.openalex.org/works/doi:10.1111/j.1540-6261.2004.00665.x)
- **Live CANSLIM-style product (Innovator IBD 50 ETF, FFTY), T3 aggregator:** tracks the IBD 50 TR index of 50 US aggressive-growth stocks; inception 9 April 2015; expense ratio 0.80%; **since-inception return 3.52% a year**; 1-year total return −3.76%; AUM $67.37m; as of 18 September 2026 — [stockanalysis.com FFTY](https://stockanalysis.com/etf/ffty/).
- **S&P 500 over the same windows:**
  - price compound growth April 2015 to September 2026 was 12.04% a year from Shiller monthly averages (own calc from `/home/claude/data_raw/us/shiller_sp500_monthly.csv`); adding roughly 1.5-1.9% dividends gives total return of about 13.5-14% a year;
  - SPY price return 30 September 2025 to 30 September 2026 was +15.4% (Stocklake API pull, 2 October 2026; no public URL; T3).
- **Minervini:** the official site presents "2-time U.S. Investing Champion" and testimonials. It gives no definition of SEPA or VCP on the home page and no performance figures — [minervini.com](https://www.minervini.com/).
- **Piotroski (2000, JAR), US 1976-1996:**
  - selecting financially strong high-B/M firms raised returns by at least 7% a year;
  - a winners-minus-losers strategy earned 23% a year;
  - benefits concentrate in small and mid-size firms, low-turnover stocks and firms with no analyst following;
  - about a sixth of the spread arrives in the four three-day earnings-announcement windows.
  — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455). OSAP reproduces the F-score at 1.96% a month (t 5.59, value-weighted decile) — [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **Novy-Marx, "The Quality Dimension of Value Investing", US July 1963 to December 2013:**

  | Long/short quality measure | Excess return (% a year) | FF3 alpha (% a year) |
  |---|---|---|
  | Gross profitability | 2.70 | 5.21 (t 4.65) |
  | Piotroski F-score | 2.24 | 4.33 |
  | ROIC | 2.17 | 4.66 |
  | Grantham quality | −0.55 | 4.84 |
  | Graham G-score | −0.08 | 1.69 |
  | Sloan accruals | 1.17 | 2.13 (not significant) |

  - in the Russell 1000, gross profitability's FF3 alpha is 4.99%;
  - long-only "profitable value" earned 9.20% a year (Sharpe 0.52) in large caps and 12.3% (Sharpe 0.57) in small caps;
  - only gross profitability earns significant excess returns on its own.
  — [Rochester PDF](http://rnm.simon.rochester.edu/research/QDoVI.pdf)
- **Piotroski-So (RFS 2012):** value/glamour returns, and later revisions to market expectations, concentrate in firms whose prices conflict with their fundamental strength — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v25y2012i9p2841-2875.html).
- **S&P 500 Quality Index:** scores stocks on return on equity, accruals and financial leverage — [S&P DJI](https://www.spglobal.com/spdji/en/indices/strategy/sp-500-quality-index/).

### Inferences
- CANSLIM's value is mostly a **packaging of earnings momentum and price momentum with a market-state switch**. QUANTGEN can test each part through its academic version, with fixed definitions, rather than test the discretionary composite.
- The poor FFTY record is consistent with my desk view. Concentrated aggressive-growth lists carry momentum-crash and valuation risk, and in the AI-led years the gains went to mega-caps the list did not own in size. **This is my interpretation, not a decomposition of FFTY's returns.**
- **Use the F-score as a value-trap filter inside the cheap bucket, not as a large-cap alpha engine.** Its original evidence concentrates in illiquid names that QUANTGEN's 35/50 bp cost model treats as expensive.
- **Build "quality at a reasonable price" as profitability plus value.** This is the hybrid with the best large-cap evidence.

### Gaps
- **I could not locate any peer-reviewed independent out-of-sample test of CANSLIM or SEPA/VCP.** The search budget was exhausted; OpenAlex and Crossref returned rate-limit errors; the final api.crossref.org query for CAN SLIM studies was refused with HTTP 429 and could not be read; DuckDuckGo and EconPapers search are blocked by robots.txt.
- The IBD 50 index methodology was not verified: innovatoretfs.com looped on redirects and investors.com is blocked.
- Minervini's contest returns are not verified.
- The FFTY figures come only from a T3 aggregator, and the 1-year windows for FFTY and SPY differ by about 12 days.

---

## 6. Key question E: history checks 2007-2026 (value, concentration, quality's defensive record, value traps)

### Takeaway
- **Value:** failed from 2007 to 2020, then rebounded in 2022 and 2025.
- **AI concentration (2023-2026):** made cap-weighted indices unbeatable for diversified tilts in both the US and Korea.
- **Long-only quality:** matched or lagged the market in 2020, 2022, 2024, 2025 and March 2026; it is not a hedge.
- **Value traps and crashes:** the worst losses came from financials in 2008, the crowded quant unwind of 2007 and the 2009 rebound that hit both price and earnings momentum.

### Cited Findings
**Value 2007-2020 and its rebounds**
- **Own calc, Ken French factors (US, monthly, gross, IS)** — the copy bundled in the linearmodels 7.0 package, covering January 1949 to March 2017 ([Ken French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html); [linearmodels on PyPI](https://pypi.org/project/linearmodels/)):

  | Period | HML % a year | HML Sharpe | UMD % a year | UMD Sharpe | 50/50 % a year | 50/50 Sharpe | corr(HML, UMD) | Market Sharpe |
  |---|---|---|---|---|---|---|---|---|
  | 1949-1989 | 5.12 | 0.61 | 9.94 | 0.92 | 7.53 | 1.21 | −0.18 | 0.54 |
  | 1990-2006 | 5.34 | 0.49 | 9.94 | 0.61 | 7.64 | 0.80 | −0.06 | 0.51 |
  | 2007-2017/03 | −1.59 | −0.17 | −0.49 | −0.03 | −1.04 | −0.13 | −0.44 | 0.51 |
  | 1963-2006 | 5.87 | 0.60 | 9.80 | 0.71 | 7.84 | 0.99 | −0.12 | 0.39 |

  - HML peaked in December 2006 and was −18.9% cumulative from January 2007 to March 2017, with a maximum drawdown of −27.5% by July 2015;
  - big value (S5V5) returned +78.5% against +145.8% for big growth (S5V1) over 2007-2017/03;
  - calendar years: 2007 HML −13.7% and UMD +22.8%; 2009 UMD −52.6%; 2015 HML −9.7%; 2016 HML +21.1% and UMD −17.5%.
- **Value to 2020 (Arnott-Harvey-Kalesnik-Linnainmaa):** HML had a −39.1% peak-to-trough drawdown lasting more than 12 years; the value spread reached the 97th percentile; the authors estimate about a 1-in-20 chance under the historical distribution and reject "structural impairment" — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3488748).
- **AQR (Asness, 8 May 2020):** the first quarter of 2020 was value's worst quarter since 1963 and second worst since 1926; the value spread was at the 100th percentile on 31 March 2020 — [AQR](https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead).
- **Fama-French, "The Value Premium":** value premiums were much lower in the second half of July 1963 to June 2019, though volatility prevents rejecting equal expected premiums — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3525096).
- **Earlier counter-episode (own calc, French):** March 2000 to December 2002, HML +95.7% and UMD +11.1% while the market fell −37.3%.
- **Calendar returns 2021-2025 (benchmark indices, total return %, from iShares product pages)** — [QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf); [IVV](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf); [IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); [IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf); [MTUM](https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf); [VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf); [USMV](https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf). Cumulative and annualised figures are own calc.

  | Index | 2021 | 2022 | 2023 | 2024 | 2025 | Cum. 2021-25 | % a year | Years beating S&P 500 |
  |---|---|---|---|---|---|---|---|---|
  | S&P 500 | 28.71 | −18.11 | 26.29 | 25.02 | 17.88 | 96.2 | 14.4 | n/a |
  | MSCI USA Sector Neutral Quality | 27.22 | −20.28 | 31.09 | 22.42 | 12.92 | 83.8 | 12.9 | 1/5 |
  | Russell 1000 Value | 25.16 | −7.54 | 11.46 | 14.37 | 15.91 | 71.0 | 11.3 | 1/5 |
  | Russell 1000 Growth | 27.60 | −29.14 | 42.68 | 33.36 | 18.56 | 104.0 | 15.3 | 3/5 |
  | MSCI USA Enhanced Value | 29.20 | −13.99 | 14.42 | 7.35 | 32.87 | 81.4 | 12.6 | 3/5 |
  | MSCI USA Momentum | 13.61 | −18.10 | 9.24 | 33.16 | 22.33 | 65.6 | 10.6 | 3/5 |
  | MSCI USA Minimum Volatility | 21.01 | −9.19 | 9.79 | 15.99 | 7.84 | 50.9 | 8.6 | 1/5 |

**Growth and AI concentration 2023-2026**
- **US concentration (RBC Wealth Management, 22 January 2026):**
  - top-10 weight in the S&P 500 was about 19% in 1990, about 23% at end-2000 (peak 27% within the year), about 19% at end-2015 and **about 41% at end-2025**;
  - the top 10 hold about 32% of expected earnings;
  - cap-weighted beat equal-weighted by about 32% over 2023-2025, against about 31% in the late 1990s;
  - cap-weighted trades at about a 30% premium to equal-weighted, against about 13% before the pandemic;
  - NVIDIA is nearly 8% of the index.
  — [RBC](https://www.rbcwealthmanagement.com/en-us/insights/the-great-narrowing-sp-500-concentration)
- **S&P Global (partner piece):** the top 10 were almost 40% of the S&P 500 by mid-2025, a level not seen since the mid-1960s — [S&P Global](https://www.spglobal.com/en/research-insights/special-reports/look-forward/partner-perspectives/unlocking-potential-ahead-with-vanguard/in-the-shadows-of-giants).
- **Korea concentration (own calc; lab data, KRX marcap, all KOSPI-listed lines, Samsung common shares only, last trading day of each year)** — [FinanceData/marcap](https://github.com/FinanceData/marcap):

  | Date | Samsung Elec. % of KOSPI cap | SK hynix % | Both % | Top-10 % |
  |---|---|---|---|---|
  | 2007-12-28 | 8.6 | 1.3 | 9.9 | 32.1 |
  | 2012-12-28 | 19.4 | 1.5 | 21.0 | 39.1 |
  | 2020-12-30 | 24.4 | 4.4 | 28.8 | 48.4 |
  | 2024-12-30 | 16.2 | 6.4 | 22.6 | 41.7 |
  | 2025-12-30 | 20.4 | 13.6 | 34.0 | 48.3 |
  | **2026-09-29** | **28.1** | **22.7** | **50.8** | **64.3** |

- **Korean returns (own calc, marcap, KOSPI stocks listed on both dates, price returns):**

  | Period | Cap-weighted return | Median stock | Samsung + SK hynix contribution |
  |---|---|---|---|
  | 2023 | +18.8% | −1.4% | +10.6 pp |
  | 2024 | −9.8% | −13.3% | −6.0 pp |
  | 2025 | +78.0% | +12.7% | +38.1 pp |
  | 2026 YTD (30 Dec 2025 to 29 Sep 2026) | +64.1% | −5.9% | +49.4 pp |

  In 2026 YTD only 11.7% of 939 stocks beat the cap-weighted return. Samsung's price rose +127.3% and SK hynix's +171.1%.
- **Korean policy regime:**
  - Corporate Value-up Program announced 26 February 2024; draft guidelines 2 May 2024 — [FSC "Value-up"](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Value-up);
  - high-dividend companies must disclose value-up plans under rules effective 24 February 2026 (same source);
  - draft standards (28 July 2026) to publish a twice-yearly list of persistently low-P/B companies: KOSPI bottom 25% or KOSDAQ bottom 10% within sector for three years; about 120 firms as of May 2026; one-year exemption for firms that disclose value-up plans — [FSC "Price-to-Book"](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Price-to-Book); [FSC press list](https://www.fsc.go.kr/eng/pr010101).

**Quality's defensive record**
- **QMJ (Asness-Frazzini-Pedersen, RAST 2019):**
  - US June 1957 to December 2016: four-factor alpha 60 bp a month (t 9.95), excess return 42 bp;
  - 24 other developed markets June 1989 to December 2016: global alpha 61 bp (t 8.07), positive in 23 of 24 countries;
  - significantly negative market and size exposures, and "mild flight to quality" in severe bear markets (past 12-month market return below −25%).
  — [Springer](https://link.springer.com/article/10.1007/s11142-018-9470-2); [AQR page](https://www.aqr.com/Insights/Research/Working-Paper/Quality-Minus-Junk)
- **Own calc, factor ETFs, adjusted daily closes (T3 data: dataset bundled in the skfolio package, 2 January 2014 to 28 December 2022, with an S&P 500 price index)** — [skfolio on PyPI](https://pypi.org/project/skfolio/):

  | Window | S&P 500 | QUAL | USMV | MTUM | VLUE | SIZE |
  |---|---|---|---|---|---|---|
  | Q4-2018 (20 Sep to 24 Dec) | −19.8 | −20.3 | −12.5 | −21.2 | −22.2 | −18.6 |
  | COVID crash (19 Feb to 23 Mar 2020) | −33.9 | **−34.1** | −33.0 | −34.1 | −38.8 | −39.1 |
  | 2022 to the 12 Oct low | −24.9 | **−27.5** | −17.8 | −25.3 | −22.4 | −22.9 |

  QUAL's beta to the S&P 500 was 0.99 and USMV's 0.78 over 2014-2022. In calendar 2020, VLUE returned −0.9% and MTUM +29.4% (first to last trading day).
- **2026 drawdown (Stocklake API pull, T3, prices):** from 25 February to 30 March 2026, QUAL −9.0% against SPY −8.6%; SPY fell −8.9% from 27 January to 30 March; year to date (31 December 2025 to 1 October 2026), QUAL +12.9% against SPY +12.6%.
- **Volatility episodes (own calc from the CBOE VIX file at `/home/claude/data_raw/us/vix_daily.csv`):**
  - 80.9 on 20 November 2008;
  - 82.7 on 16 March 2020;
  - 36.5 on 7 March 2022;
  - **2025 tariff shock: 15.27 on 19 February 2025 to 52.33 on 8 April 2025;**
  - 31.1 on 27 March 2026.
  On Shiller monthly averages the S&P 500 fell −11.1% from February to April 2025.

**Value traps and earnings-signal failures in crashes**
- **Financials (own calc, French "Money" industry):** October 2007 to February 2009 return −69.5% against −49.3% for the market; HML −19.6% and UMD +36.1% over the same window.
- **August 2007 quant unwind (Khandani-Lo):**
  - deleveraging began in July 2007 and ran to year-end;
  - two unwinds: 1 August (10:45 to 11:30 a.m.) and 6 August (open to 1 p.m.);
  - they began in financials, long book-to-market and short earnings momentum;
  - market-making capital withdrew from 8 August.
  — [NBER w14465](https://www.nber.org/papers/w14465)
- **Momentum crash, March to May 2009:**
  - past-loser decile +163%, past-winner decile +8%, market +26%; 14 of the 15 worst momentum months came after a negative two-year market return — [Daniel-Moskowitz PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf);
  - own calc: UMD −11.5%, −34.6% and −12.3% in March, April and May 2009, −49.3% in total;
  - the SUE strategy also had a large drawdown (maximum loss 21.4%) — [Novy-Marx 2015](https://www.nber.org/system/files/working_papers/w20984/w20984.pdf).

### Inferences
- **Value:** use it as a component, not a bet. Post-2007 value was a poor standalone, consistent with the Ilmanen et al. haircut of −49% in the context brief. But it paid when growth multiples deflated (2000-02, 2022) and in 2025, so it diversifies a growth-heavy book.
- **Quality:** the prior map's "most consistent sign of any fundamental factor" holds for the long/short QMJ and GP factors. For a long-only individual, the investable quality index lagged the S&P 500 in four of five years from 2021 to 2025 and fell as much in every crash I could measure. **Keep quality at 1.0x, as the macro research already decided, but drop any expectation that it protects.**
- **Concentration:** in both markets a diversified fundamental tilt fails mostly because it does not own the two to ten names driving the index. The choice of benchmark for gate step 5 (cap-weighted, capped or equal-weighted) will decide many verdicts and must be pre-registered.
- **Value traps:** 2008 financials looked cheap on price-to-book while their balance sheets were impaired. Leverage and earnings-quality filters (F-score, accruals, leverage change) are the practitioner defence. Earnings-momentum signals failed in the 2009 rebound, the same pattern as price momentum.

### Gaps
- **AQR QMJ monthly data could not be downloaded** (403 to curl; WebFetch returned binary), so I could not measure QMJ in 2008, 2020, 2022 or 19 February to 8 April 2025. **Quality's behaviour in the 2025 tariff shock is unmeasured:** the Stocklake history starts on 21 April 2025, after the trough.
- Ken French's site is blocked (403), so HML/UMD after March 2017 come only from secondary sources.
- The S&P 500 top-10 weight in 2026 is not verified.
- The 2021 QUAL calendar return from the skfolio data (29.0%) differs from iShares' NAV figure (26.90%), probably because of first-trading-day boundaries and adjustment method. I quote iShares for calendar years and the skfolio data only for intra-year windows.

---

## 7. Key question F: combining fundamentals and technicals

### Takeaway
The evidence supports two kinds of technical overlay on fundamental selection.
- **Momentum as a negatively correlated partner and confirmation filter.** Value works best among past losers and momentum best among expensive stocks. Fundamental (earnings) momentum explains most of price momentum, and earnings momentum orthogonal to price momentum avoided the 2009 crash.
- **Market-state gating.** Momentum-type payoffs, fundamental ones included, collapse after bear markets.

I found no independent evidence that chart patterns (VCP, breakouts) improve fundamental picks.

### Cited Findings
- **Asness (1997, FAJ):** value and momentum measures are negatively correlated across stocks; value is strongest among low-momentum (loser) stocks and weakest among winners; momentum is strongest among expensive stocks — [EconPapers](https://econpapers.repec.org/article/tafufajxx/v_3a53_3ay_3a1997_3ai_3a2_3ap_3a29-36.htm).
- **Asness-Moskowitz-Pedersen (2013, JF), Table I, Sharpe ratios.** Stock samples run January 1972 to July 2011 for the US and UK, and January 1974 to July 2011 for Europe and Japan. Value and momentum correlate at roughly −0.6 on average within asset classes (from the fetched summary; verify in Table I). Funding-liquidity shocks hurt value and help momentum but explain little of either premium.

  | Market | Value | Momentum | 50/50 combination |
  |---|---|---|---|
  | US stocks | 0.29 | 0.33 | 0.63 |
  | UK stocks | 0.33 | 0.38 | 0.77 |
  | Europe stocks | 0.42 | 0.55 | 0.87 |
  | Japan stocks | 0.79 | 0.09 | 0.78 |
  | Global stocks | 0.57 | 0.47 | 1.04 |
  | All asset classes | 0.73 | 0.67 | 1.42 |

  — [NYU Stern PDF](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf); [AQR page](https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere)
- **The US combination failed after 2007 (own calc, French):** the 50/50 HML+UMD mix had Sharpe 1.21 (1949-1989), 0.80 (1990-2006) and **−0.13 (2007-2017/03)**, with the correlation falling to −0.44 in the last period.
- **Novy-Marx (2015):** earnings momentum subsumes price momentum. SUE conditioned on price momentum cut the maximum loss from 21.4% to 8.7% around 2009 — [NBER w20984 PDF](https://www.nber.org/system/files/working_papers/w20984/w20984.pdf).
- **Market state:**
  - momentum profits after positive market returns were 0.93% a month against −0.37% after negative returns, 1929-1995 — [Cooper-Gutierrez-Hameed 2004 via OpenAlex](https://api.openalex.org/works/doi:10.1111/j.1540-6261.2004.00665.x);
  - a dynamic momentum strategy roughly doubles the alpha and Sharpe ratio of static momentum (static WML Sharpe 0.71, 1927-2013) — [Daniel-Moskowitz NBER w20439](https://www.nber.org/papers/w20439); [PDF](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf).
- **Fundamentals that confirm price:** value/glamour returns concentrate where price and fundamental strength disagree — [Piotroski-So 2012](https://ideas.repec.org/a/oup/rfinst/v25y2012i9p2841-2875.html).
- **52-week-high proximity (George-Hwang 2004, US 1963-2001):** 0.45% a month (t 2.0), with the sign depending on January — [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **Asset-manager view (T2):** Lord Abbett proposes "confirmed momentum" (price plus operating momentum) to limit price momentum's downside, with no new statistics — [Lord Abbett PDF](https://www.lordabbett.com/content/dam/lordabbett-captivate/documents/insights/InvestmentPerspectives/2025/11425-the-benefits-of-price-and-operating-momentum-in-equity-portfolios-non-us.pdf).

### Inferences
- For QUANTGEN, **"technical timing" of fundamental picks should mean three things:**
  1. a separate momentum sleeve combined with the fundamental composite (the diversification is the gain);
  2. a mild confirmation filter: avoid fundamental longs in the bottom 12-1 momentum quintile or far below their 52-week high, which is the value-trap guard Asness (1997) implies;
  3. the macro research's bear-state gate (floor 0.5) applied to **all momentum-type sleeves, earnings momentum included**.
  Breakout or VCP entry timing should not be added without a pre-registered test by the technical panel.
- The post-2007 failure of the US value+momentum combination means a combination is not a guarantee. Size combination sleeves with the gate's decay haircut and expect long dry spells.

### Gaps
- I found no study testing whether chart-pattern entry (VCP, cup-with-handle, pivot breakouts) adds return to fundamentally selected stocks.
- I found no evidence on combinations in Korea.
- The −0.6 average value-momentum correlation in Asness-Moskowitz-Pedersen comes from a fetched summary and should be checked against Table I.

---

## 8. Key question G: QUANTGEN translation (ranked features, data, lags, costs, roles)

### Takeaway
QUANTGEN can compute about eight fundamental features point-in-time from public data today: profitability, value, issuance, F-score, accruals, event-based earnings momentum, insider trades (US) and short-interest filters. Analyst-revision features need a forward-collected archive. In a long-only form at QUANTGEN's costs, only the low-turnover features (profitability, issuance, value) clearly survive costs. Earnings momentum survives only if Korea shows more than about 3% a year of gross drift in liquid names. Expected live information ratios are modest: 0.05-0.15 per feature and 0.12-0.2 for the composite. Given the gate's benchmark test, a Korean card needs an IR of 0.4-0.5 or more to PASS on DART's post-2015 history.

### Cited Findings: data availability and point-in-time stamps

| Feature input | Korea source | US source | Timestamp and lag | History (verified?) |
|---|---|---|---|---|
| Financial statements (IS, BS, CF) | OpenDART fnlttSinglAcntAll: CFS/OFS; Q1 11013, H1 11012, Q3 11014, FY 11011; receipt number linked; quota error above about 20,000 requests — [guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020) | FMP as-reported statements plus a filing-dates API — [FMP](https://site.financialmodelingprep.com/developer/docs); EDGAR | KR: rcept_dt from the disclosure list; US: 10-Q due 40/45 days after quarter-end — [SEC 10-Q](https://www.sec.gov/files/form10-q.pdf); 10-K due 60/75/90 days — [SEC 10-K](https://www.sec.gov/files/form10-k.pdf) | DART API from bsns_year 2015 (verified); FMP depth not verified |
| Filing and event dates | OpenDART list API: rcept_dt; types A001 annual, A002 half, A003 quarterly, I-type exchange disclosures (I001-I006); 3-month search window without corp_code — [guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001) | FMP earnings calendar/report (actual against estimate) | event date | not verified |
| Shares outstanding (issuance) | marcap `Stocks` column, daily (lab data) — [marcap](https://github.com/FinanceData/marcap) | FMP/EDGAR | daily (KR) | KR 1995-2026 (lab data) |
| Insider trades | OpenDART elestock (rcept_dt, change in shares) — [guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS004&apiId=2019022); 30-day pre-disclosure of large trades from 24 Jul 2024 — [FSC](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=insider) | FMP insider endpoints (Form 4) | US: 2 business days — [Form 4](https://www.sec.gov/about/forms/form4.pdf) | not verified |
| Short interest | KIS short-sale data (per context brief); KRX | FINRA, twice monthly — [FINRA](https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest) | US: settlement date + 2 business days to file + about 1 week to publish | KR series broken 6 Nov 2023 to 30 Mar 2025 — [FSC](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Short%20Selling) |
| Analyst estimates, opinions, targets | KIS estimate-perform, invest-opinion, invest-opbysec — [KIS GitHub](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/invest_opinion/chk_invest_opinion.py) | FMP estimates, grades, historical grades, price targets | archive timestamp | depth unknown, so start archiving |
| 13F holdings | n/a | FMP 13F suite | quarter-end + 45 days, longs only — [SEC 13F FAQ](https://www.sec.gov/divisions/investment/13ffaq.htm) | not verified |

**Costs and decay anchors**
- **Value-weighted costs and turnover (Novy-Marx-Velikov, Table 3, US):**

  | Strategy | Gross (% a month) | Cost (bp) | Net (% a month) | One-sided turnover (% a month) |
  |---|---|---|---|---|
  | Value | 0.47 | 5 | 0.42 (t 2.39) | not stated |
  | Gross profitability | 0.40 | 3 | 0.37 (t 2.74) | not stated |
  | ROE | 0.71 | 38 | 0.33 (t 1.38) | 22 |
  | PEAD | 0.72 | 46 | 0.26 (t 1.60) | 35 |
  | Momentum | 1.33 | 65 | 0.68 (t 2.45) | 35 |
  | Industry momentum | 0.93 | 122 | −0.29 | 90 |
  | Short-term reversal | 0.37 | 165 | −1.28 | 91 |

  A buy/hold band cut the turnover of a value-momentum-profitability mix by 41% while slightly raising its net spread (1.02% against 0.99%) — [NBER w20721 PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- **Decay:**
  - McLean-Pontiff, 97 predictors: returns are −26% lower out-of-sample and −58% lower after publication — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623);
  - anomaly returns roughly halved after decimalisation — [Chordia-Subrahmanyam-Tong 2014](https://econpapers.repec.org/article/eeejaecon/v_3a58_3ay_3a2014_3ai_3a1_3ap_3a41-58.htm);
  - Chen-Velikov: the average anomaly's expected net return is about 8 bp a month, and the strongest earn 10-20 bp — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681);
  - Hou-Xue-Zhang, 447 anomalies: 64% insignificant at 5% and 85% at t < 3 — [NBER w23394](https://www.nber.org/papers/w23394);
  - in contrast, most factors replicate and work out-of-sample across 93 countries — [Jensen-Kelly-Pedersen NBER w28432](https://www.nber.org/papers/w28432).

### Inferences: QUANTGEN translation (E4 judgment unless cited)

**Cost arithmetic for long-only tilts (own calc).** Annual cost = 2 × (one-sided monthly turnover) × 12 × (cost per side).

| Turnover profile | KRX 35 bp (1x / 2x) | US 50 bp (1x / 2x) |
|---|---|---|
| Fundamental, 4% a month | 0.34% / 0.67% | 0.48% / 0.96% |
| Insider overlay, 10% a month | 0.84% / 1.68% | 1.20% / 2.40% |
| Revisions, 25% a month | 2.10% / 4.20% | 3.00% / 6.00% |
| SUE/PEAD, 35% a month | 2.94% / 5.88% | 4.20% / 8.40% |

**Gate power (own calc).** One-sided p ≤ 0.10 needs t ≥ 1.28, and t ≈ IR × √years.

| IR | Years needed (p ≤ 0.10) | Years needed (p ≤ 0.05) |
|---|---|---|
| 0.2 | 41 | 68 |
| 0.3 | 18 | 30 |
| 0.4 | 10 | 17 |
| 0.5 | 6.6 | 11 |

With about 10 years of DART-based signals the minimum detectable IR is about 0.41. With about 7 years of walk-forward OOS (the first 756 sessions are in-sample) it is about 0.48. **Pre-register at most four or five features and one combination rule so the deflated-Sharpe trial count stays small.**

**Ranked fundamental features.** The expected-IR column is my judgment from the cited anchors, haircut for publication decay and QUANTGEN costs; it is not measured.

| Rank | Feature (definition) | Data (KR / US) | PIT stamp; rebalance | Evidence anchor (market, period, IS, gross unless noted) | Expected live net IR, long-only tilt | Role / verdict |
|---|---|---|---|---|---|---|
| 1 | **Profitability:** gross profits/assets; cash-based operating profitability for robustness; ex-financials | DART fnlttSinglAcntAll / FMP or EDGAR | rcept_dt + 1 session; monthly with buy/hold band (signal changes quarterly) | GP FF3 alpha 5.21% a year (t 4.65), 4.99% in Russell 1000, US 1963-2013; value-weighted quintile 0.31% a month, t 2.49 (≈0.36 Sharpe), 1963-2010; cost 3 bp a month; QMJ positive in 23/24 countries | 0.05-0.15 | COMPOSITE core; BUILD-candidate |
| 2 | **Net share issuance:** −ln(shares_t / shares_t−12m), split-adjusted; buybacks score positive | marcap `Stocks` (1995+, daily) / FMP or EDGAR | daily data; monthly | Pontiff-Woodgate t 7.08 (1970-2003); Daniel-Titman composite issuance t 4.39; net payout yield 0.37% a month, t 2.83 ([OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv)) | 0.05-0.15 (KR untested) | COMPOSITE plus KR dilution screen; BUILD-candidate, testable now (DC-1) |
| 3 | **Value composite:** E/P, B/M, CF/P, sector-relative | DART + marcap cap / FMP | rcept_dt + 1; monthly with band | HML Sharpe 0.60 (1963-2006) against −0.17 (2007-2017/03); 2022 and 2025 rebounds; KR Value-up regime from 2024 | 0.0-0.1 standalone; more inside the composite | COMPOSITE at low weight plus valuation guardrail; BUILD-candidate |
| 4 | **Event earnings momentum:** CAR3 around the first earnings disclosure plus time-series SUE | DART list (I-type preliminary results, A001-A003) + OHLCV / FMP calendar + OHLCV | event + 2 sessions; hold 60 sessions | US 1975-2012: SUE t 7.14, CAR3 t 8.42, SUE net Sharpe 0.55; but value-weighted PEAD net only 0.26% a month (t 1.60) and large caps ≈0 since 2006 | US ≤ 0; KR unknown (0-0.15 if DC-2 passes) | KR: BACKLOG then composite if DC-2 passes; US: DROP standalone, use only as confirmation |
| 5 | **Opportunistic insider buys:** buys by non-routine insiders in the last 90 days | DART elestock (+ 2024 pre-disclosure) / FMP Form 4 | filing date; event; hold about 6 months | US 1986-2007 value-weighted 82 bp a month (t 2.15, ≈0.46 gross Sharpe); purchases about 40 bp a month (1975-1996) | US 0.05-0.15; KR untested | OVERLAY; BUILD-candidate (US), BACKLOG (KR) |
| 6 | **F-score floor** inside the cheapest value bucket | DART / FMP | annual report; quarterly refresh | +7% a year within high B/M (1976-1996, small/illiquid); FF3 alpha 4.33% (1963-2013) | n/a (filter) | FILTER; BUILD-candidate |
| 7 | **Extreme accruals** (top decile excluded) | DART / FMP | as above | Sloan accrual alpha 2.13% a year, not significant (1963-2013) | n/a | FILTER (red flag) |
| 8 | **High days-to-cover** (top decile excluded from longs) | KIS/KRX short balance / FINRA | twice monthly with lag; KR series broken 2023-25 | heavily shorted −1.16% per 20 days (NYSE 2000-04, proprietary); DTC long/short 1.2% a month; GME failure | n/a | RISK SCREEN; BACKLOG (KR data check) |
| 9 | **Revision breadth, downgrades, recommendation changes** | KIS estimate/opinion / FMP estimates and grades | archive time; monthly | REV6 t 4.07 (1977-1992); sell drift −9.1% over 6 months (Womack) | unknown: INSUFFICIENT DATA | BACKLOG: archive daily now (DC-9); a downgrade exclusion screen can start once about 60 days are archived |
| 10 | **Earnings announcement premium** (hold into the expected report month) | DART / FMP calendars | monthly | US 61 bp a month (1972-2004); 9 of 20 countries | unknown | BACKLOG |
| 11 | **Highest-LTG or glamour exclusion** | FMP (LTG field unverified) / n/a | monthly | high-LTG 3% a year against low-LTG 15% (1981-2016) | n/a | FILTER; BACKLOG |
| 12 | 13F breadth change; 13F cloning | — / FMP 13F | quarter + 45 days | breadth t 3.96 (1979-1998); GURU index lagged the S&P 500 ≈3.5 pp a year over 10 years | ≤ 0 (cloning) | Breadth BACKLOG; cloning DROP |
| 13 | Recommendation level; target-price upside | KIS / FMP | — | net ≈ 0 (Barber et al. 2001); targets +28% biased, 38% met | ≤ 0 | DROP |
| 14 | CANSLIM/IBD composite; SEPA/VCP | — | — | no independent OOS test found; FFTY 3.52% a year since 2015 | ≤ 0 (composite) | DROP (components handled above or by the technical panel) |
| 15 | Aggregate short interest | FINRA aggregate / KR market short balance | twice monthly | OOS R² 1.94-13.24% (1973-2014) | n/a | CONTEXT: macro overlay may only scale exposure down (≤ 1.0) |
| 16 | Guidance withdrawal or negative pre-announcement | DART I-type / 8-K | event | negative 3-day returns when guidance stops; bad news withheld | n/a | CONTEXT / BACKLOG red-flag screen |

**Recommended first card ("F1 fundamental composite").** Pre-register all of the following before the test:
- **Inputs:** equal-weighted z-scores of features 1-3, plus feature 4 in Korea only if DC-2 passes.
- **Neutralisation:** within sector and within size tercile.
- **Filters:** features 6, 7 and 8.
- **Portfolio:** long-only top 20-30% of a liquid universe (Korea: KOSPI 200 + KOSDAQ 150 or top 300 by cap; US: S&P 500), with a 5-10% single-name cap.
- **Benchmark:** a concentration-capped benchmark, since the gate's step-5 choice must be fixed in advance.
- **Trading:** monthly rebalance with a 20%/30% buy/hold band; costs 35 bp (KR) and 50 bp (US), re-run at 2x.

My expectation is a backtest IR of 0.3-0.5 net at 1x, about 0.12-0.2 live after the 60% haircut. Turnover should stay below about 60% a year one-sided, so it should survive 2x costs. **Likely verdict on Korean DART-only history: REVISE, because of power, unless the effect is larger than the literature suggests.** A US version with a longer FMP/EDGAR history has a better chance of reaching a decisive verdict.

**Per-market weight corrections (fundamental columns of the prior map, 0-3 scale)**

| Market | Value | Quality | Earnings drift | New: issuance/payout | New: insider |
|---|---|---|---|---|---|
| US | 1 → 1 | 3 → 2 (sign robust in long/short; long-only IR modest and not defensive) | 2 → 1 (PEAD ≈ 0 in large caps since 2006; keep as confirmation) | 2 | 1 |
| Korea | 2 → 2 (regime test: before vs after Value-up 2024) | 1 → 1, pending DC-8 | **3 → 2, pending DC-2/DC-3** (no Korean evidence retrieved) | 2, pending DC-1 | 0 until tested (2024 pre-disclosure regime) |

**Conflicts and alignments with the macro decisions (flagged, not re-litigated)**
1. The **Daniel-Moskowitz bear-state gate should also cover earnings-momentum and revision sleeves.** SUE crashed in spring 2009, and the macro note applied the gate only to price momentum.
2. **Aggregate short interest** is direction evidence (Rapach-Ringgenberg-Zhou). Under the macro rules it can only scale exposure within [0.5, 1.0]. That is acceptable but leaves the upside unused.
3. **Quality held at 1.0x in stress** is consistent with E4, but the long-only quality ETF evidence (2020, 2022, March 2026) means the macro research should not count quality as a hedge in any risk budget.

### Gaps
- FMP plan limits, history depth and point-in-time behaviour for estimates, grades, targets, shares outstanding and Form 4 are not verified.
- The history depth of KIS estimate and opinion data is unknown.
- EDGAR XBRL depth was not checked: data.sec.gov was not reachable from this session.
- Korean statutory filing deadlines were not verified. Using rcept_dt makes them irrelevant for point-in-time purposes.
- **Every expected-IR figure in the ranked table is E4 judgment, not a measured result.**

---

## 9. Where and when it failed (dated episodes, with numbers)

| # | Dates | Episode | What failed | Numbers | Source |
|---|---|---|---|---|---|
| 1 | Jul to 10 Aug 2007 | Quant unwind | Crowded value + earnings-momentum long/short books | Unwinds on 1 Aug (10:45-11:30) and 6 Aug (open to 1 p.m.); started in financials, long B/M and short earnings momentum; HML −13.7% in 2007 (own calc) | [Khandani-Lo](https://www.nber.org/papers/w14465); French (own calc) |
| 2 | Oct 2007 to Feb 2009 | Financials value trap | Cheap-on-book banks | French Finance industry −69.5% against market −49.3%; HML −19.6% | own calc, [French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) |
| 3 | Mar to May 2009 | Junk rally / momentum crash | Price and earnings momentum | UMD −49.3% (−11.5/−34.6/−12.3); losers +163% against winners +8%; SUE maximum loss 21.4% | [Daniel-Moskowitz](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf); [Novy-Marx 2015](https://www.nber.org/system/files/working_papers/w20984/w20984.pdf) |
| 4 | 2000-2001 | Dot-com bust | Sell-side recommendations | Top-rated −7.06% a year against least-favoured +13.44%; about −25 pp (2000), −16 pp (2001) | [Barber et al. 2003](https://econpapers.repec.org/article/tafufajxx/v_3a59_3ay_3a2003_3ai_3a2_3ap_3a88-96.htm) |
| 5 | 2007-2020 | Value's lost decade | Value (HML) | −18.9% cumulative and −27.5% maximum drawdown to 2017/03 (own calc); −39.1% peak-to-trough to 2020; Q1 2020 worst quarter since 1963 | own calc; [Arnott et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3488748); [AQR](https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead) |
| 6 | 2007-2017/03 | Value + momentum combination | US 50/50 HML+UMD | Sharpe −0.13 against 0.80 in 1990-2006 | own calc (French) |
| 7 | 2016 | Momentum reversal | UMD | UMD −17.5% while HML +21.1% | own calc (French) |
| 8 | 19 Feb to 23 Mar 2020 | COVID crash | Long-only quality as a hedge | QUAL −34.1% against S&P 500 −33.9%; VLUE −38.8%; USMV −33.0%; VIX 82.7 on 16 Mar | own calc ([skfolio data](https://pypi.org/project/skfolio/)); VIX file |
| 9 | Jan 2021 | GME squeeze | High short interest as a bearish signal | Short interest 122.97% of float; +2,700%; intraday high $483 on 28 Jan | [SEC staff](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf) |
| 10 | 2022 | Rate shock | Long-only quality, momentum | MSCI USA SN Quality −20.28% against S&P −18.11%; MSCI Momentum −18.10%; value worked (Russell 1000 Value −7.54% against Growth −29.14%) | [iShares QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf); [IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); [IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf) |
| 11 | 2023-2025 | AI mega-cap concentration | Value, quality and equal-weight tilts | Growth beat value by 31.2 pp (2023) and 19.0 pp (2024); Enhanced Value +7.35% against S&P +25.02% (2024); top-10 ≈41% at end-2025; cap-weighted beat equal-weighted ≈32% over 2023-25 | iShares pages; [RBC](https://www.rbcwealthmanagement.com/en-us/insights/the-great-narrowing-sp-500-concentration) |
| 12 | 19 Feb to 8 Apr 2025 | Tariff shock | Unmeasured for quality (data gap) | VIX 15.27 to 52.33; S&P monthly average −11.1% (Feb to Apr); 2025 calendar: quality +12.92% against S&P +17.88% | VIX and Shiller files (own calc); [iShares QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf) |
| 13 | 27 Jan to 30 Mar 2026 | US drawdown | Long-only quality as a hedge | SPY −8.9%; QUAL −9.0% against SPY −8.6% (25 Feb to 30 Mar); VIX 31.1 on 27 Mar | Stocklake pull (T3); VIX file |
| 14 | 2024 and 2026 YTD | Korean memory-chip concentration | Any diversified Korean tilt | 2024: cap-weighted −9.8% against median −13.3%; 2026 YTD: +64.1% against median −5.9%; 11.7% of stocks beat; Samsung + SK hynix 50.8% of cap on 29 Sep 2026 | own calc ([marcap](https://github.com/FinanceData/marcap)) |
| 15 | 6 Nov 2023 to 30 Mar 2025 (also 10 Aug to 9 Nov 2011) | Korean short-selling bans | Short-interest features (series break) | Full ban; reinstated 31 Mar 2025 | [FSC](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Short%20Selling) |
| 16 | Apr 2015 to Sep 2026 | Live CANSLIM-style list (IBD 50 ETF) | Practitioner growth-momentum composite | 3.52% a year against S&P ≈13.5-14% a year; 1 year −3.76% | [stockanalysis.com](https://stockanalysis.com/etf/ffty/) (T3); Shiller (own calc) |
| 17 | 2016-2026 | Live 13F hedge-fund clone (GURU) | Cloning after the 45-day lag | Index 5 years 7.37% against S&P ≈13.4%; 10 years 12.04% against ≈15.5% | [Global X](https://www.globalxetfs.com/funds/guru/); [iShares IVV](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf) |

---

## 10. Data-check requests for the data lab

- **DC-1 (Korea, marcap only): net share issuance.**
  - **Universe:** KOSPI + KOSDAQ common stocks (exclude preferred lines and SPACs) with market cap ≥ KRW 50bn and price ≥ KRW 1,000 at formation, and at least 252 sessions of history.
  - **Signal at each month-end:** ISS = ln(Stocks_t / Stocks_t−252).
  - **Split adjustment:** treat a day as a split or consolidation when Stocks changes by a factor ≥ 1.5 or ≤ 0.67 and Close moves by about 1/factor (±20%); rescale history.
  - **Portfolios:** quintiles; long-only Q1 (lowest issuance, including net buybacks) against (a) cap-weighted, (b) equal-weighted and (c) 10%-capped benchmarks; paper long/short Q1−Q5.
  - **Timing and costs:** decide at the last close of the month, earn from the next session; 35 bp and 70 bp per side.
  - **Periods:** 2000-2026, 2000-2012 and 2013-2026.
  - **Report:** Sharpe and IR, Lo SE, t, maximum drawdown, % of years positive, full gate run.
  - **Hypothesis:** Q5 (heavy issuers: rights offerings, convertible conversions) underperforms by ≥ 3% a year.
- **DC-2 (Korea, needs an OpenDART pull): earnings-announcement drift.**
  - **Events:** list API 2015-2026; earliest of I-type preliminary-results disclosures (report_nm containing "잠정") and A001-A003 periodic reports; if rcept_dt is after 15:30, shift to the next session.
  - **Signals:** CAR3 = sum over days −1 to +1 of (stock return − KOSPI/KOSDAQ index return); time-series SUE = (EPS_q − EPS_q−4) / std of the last 8 such changes.
  - **Portfolios:** deciles within size terciles; enter at event + 2 and hold 60 sessions; value- and equal-weighted; KOSPI 200 against the rest.
  - **Costs:** 35/70 bp.
  - **Report:** drift by decile and calendar-year stability.
  - **Purpose:** this tests the prior map's Korea "earnings drift = 3".
- **DC-3 (Korea, marcap only, proxy without dates): information-event drift.**
  - **Event:** stock-day with volume ≥ 4× its 60-session average and |stock return − market return| ≥ 3σ (60-day).
  - **Measure:** returns from t+1 close to t+60 by event sign and size tercile, 1999-2026, net of 35 bp.
  - **Compare:** 1999-2005 against 2006-2026, as a Martineau-style decay check.
- **DC-4 (Korea, marcap): concentration and benchmark choice.**
  - **Annual returns 2000-2026 YTD:** (i) cap-weighted, (ii) equal-weighted, (iii) 10%-capped cap-weighted KOSPI universe.
  - **Report:** % of years equal-weighted beat cap-weighted, tracking error, and the Samsung + SK hynix contribution.
  - **Replicate:** 2026 YTD cap-weighted +64.1%, median −5.9%, 11.7% of stocks beating; Samsung + SK hynix 50.8% of cap on 29 Sep 2026.
  - **Output:** a pre-registered step-5 benchmark for Korean stock-level cards.
- **DC-5 (US, French 1926-2018): stability of value, momentum and their combination.**
  - **Statistics:** mean, Sharpe and Lo SE for HML, UMD, 50/50, and RMW/CMA if available, over 1927-1962, 1963-1989, 1990-2006 and 2007-2018.
  - **Test:** whether 2007-2018 is significantly below 1963-2006.
  - **Replicate:** my 1949-2017/03 figures (Section 6).
  - **Cooper-Gutierrez-Hameed test:** next-month UMD conditional on the sign of the trailing 24- and 36-month market return, 1929-2018.
- **DC-6 (US, French): value-trap episodes.** Finance industry against market (October 2007 to February 2009; my −69.5% against −49.3%), and HML and UMD in each NBER recession and the 12 months after.
- **DC-7 (Shiller): index-level valuation discipline.**
  - **Regression:** 10-year forward real total return on ln(CAPE), 1881-2006 in-sample; OOS forecasts for 2007-2016 start dates; report errors.
  - **Data flag:** in `shiller_sp500_monthly.csv` the Dividend, Earnings, CPI and PE10 columns are zero-filled after mid-2023 (the last non-zero dividend row is 2023-06). Treat them as missing, not zero.
- **DC-8 (Korea, needs OpenDART financials): quality and value from 2016 to 2026.**
  - **Build:** GP/A, ROA, accruals, leverage change, F-score and P/B (CFS preferred, OFS fallback), point-in-time at rcept_dt + 1.
  - **Test:** (a) GP/A quintiles; (b) F-score high against low within the cheapest P/B quintile; (c) low-P/B quintile in 2016-2023 against 2024-2026 (Value-up regime).
  - **Note:** the minimum detectable IR is about 0.41-0.48 with this sample.
- **DC-9 (forward collection, starting now).**
  - **Korea:** daily snapshots of KIS estimate-perform, invest-opinion and invest-opbysec for KOSPI 200 + KOSDAQ 150.
  - **US:** FMP estimates, grades and price targets for the S&P 500.
  - **Storage:** keep as-of timestamps.
  - **Planned tests:** a downgrade exclusion screen after about 60 sessions; a revision-breadth card at the earliest gate opportunity (756 + 126 sessions, about 3.5 years).
- **DC-10 (US quotes via KIS or FMP): fill the 2025 tariff-shock gap.** Daily closes for QUAL, USMV, VLUE, MTUM and SPY: 19 Feb to 8 Apr 2025 drawdown, 8 Apr to 30 Jun 2025 recovery, and 27 Jan to 30 Mar 2026.
- **DC-11 (Korea, KIS short-sale data if history exists): days-to-cover filter.**
  - **Universe:** KOSPI 200 names; DTC = short balance / 20-day average volume.
  - **Test:** the effect of excluding the top DTC decile from a long-only composite over May 2021 to October 2023 and April 2025 to September 2026, with the ban window treated as missing.

---

## 11. Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| E4-C01 | Price momentum is mostly earnings momentum. | US 1975-2012 IS: UMD 0.64% a month (t 3.03), SUE 0.59% (t 7.14), CAR3 0.53% (t 8.42); UMD alpha on SUE+CAR3 −0.48% (t −2.55); net Sharpe: SUE 0.55, UMD 0.33 | [Novy-Marx 2015](https://www.nber.org/system/files/working_papers/w20984/w20984.pdf) | T1 | Consistent with CJL 1996; costs modelled; pre-dates PEAD decay | SUE maximum loss 21.4% in spring 2009 | BUILD-candidate (KR): CAR3/SUE term pending DC-2; US: confirmation only |
| E4-C02 | Large-cap US PEAD has been about zero since around 2006; "revival" results depend on microcaps. | No large-cap drift since 2006; 2025 earnings factor t 2.18 with all stocks, 1.43 ex-microcaps; microcaps ≈3% of market value | [Martineau](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607); [UCLA Anderson](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/) | T1/T2 | OOS in time; post-publication | — (this is the failure) | DROP a standalone US PEAD card |
| E4-C03 | PEAD's decline coincides with lower earnings persistence. | US 1974-2020: about −2 bp per quarter trend; insignificant after controlling for persistence | [Kettell-McInnis-Zhao](https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf) | T1 (working paper) | Single study | — | CONTEXT: decay may be structural; haircut any drift signal |
| E4-C04 | Net of costs PEAD is marginal, and QUANTGEN's rates make it unprofitable in liquid US stocks. | US value-weighted: gross 0.72% a month, cost 46 bp, net 0.26% (t 1.60), 35% turnover; long-only cost ≈4.2% a year US and 2.9% KRX at 1x (own calc) | [Novy-Marx & Velikov](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) | T1 | Cost model replicated; costs are estimates | 2009 crash | DROP (US); KR only if gross drift > ≈3% a year |
| E4-C05 | Stocks earn a premium in their expected announcement months. | US 1972-2004 gross: 61 bp a month; 0.92% a month in 1994-2004; strong in large caps; 9 of 20 countries significant | [Frazzini-Lamont](https://www.nber.org/system/files/working_papers/w13090/w13090.pdf); [Barber et al. 2013](https://econpapers.repec.org/article/eeejfinec/v_3a108_3ay_3a2013_3ai_3a1_3ap_3a118-138.htm) | T1 | Partly global; post-2004 not verified | Korea untested | BACKLOG (calendar overlay; needs DART dates) |
| E4-C06 | Analyst forecast revisions predict returns because analysts update slowly. | REV6 t 4.07 (US 1977-1992); revision 0.46% a month long-only alpha (1975-1980) | [CJL 1996](https://econpapers.repec.org/article/blajfinan/v_3a51_3ay_3a1996_3ai_3a5_3ap_3a1681-1713.htm); [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv) | T1 | Reproduced by OSAP; no recent public evidence found | Likely 2009-type crash (inferred from SUE) | BACKLOG: no point-in-time consensus; archive now (DC-9) |
| E4-C07 | Consensus recommendation levels do not survive costs and can invert violently. | >4% a year gross only with daily rebalancing, net ≈ 0 (US 1985-1997); 2000-01: top −7.06% a year against bottom +13.44% | [Barber et al. 2001](https://econpapers.repec.org/article/blajfinan/v_3a56_3ay_3a2001_3ai_3a2_3ap_3a531-563.htm); [Barber et al. 2003](https://econpapers.repec.org/article/tafufajxx/v_3a59_3ay_3a2003_3ai_3a2_3ap_3a88-96.htm) | T1 | Two samples | 2000-2001 | DROP as a feature |
| E4-C08 | Downgrades carry more information than upgrades. | Drift +2.4% after buys (short-lived) against −9.1% over 6 months after sells (US) | [Womack 1996](https://econpapers.repec.org/article/blajfinan/v_3a51_3ay_3a1996_3ai_3a1_3ap_3a137-67.htm) | T1 | Pre-Reg FD sample | — | BACKLOG: "recent downgrade" exclusion screen via the KIS previous-opinion field |
| E4-C09 | Target prices are biased upward and inaccurate. | 12-month target 28% above price (1997-99); implied return exceeds actual by 15%, absolute error 45%, 38% met at 12 months (2000-09) | [Brav-Lehavy](https://econpapers.repec.org/article/blajfinan/v_3a58_3ay_3a2003_3ai_3a5_3ap_3a1933-1967.htm); [Bradshaw-Brown-Huang](https://ideas.repec.org/a/spr/reaccs/v18y2013i4d10.1007_s11142-012-9216-5.html) | T1 | Two consistent samples | — | DROP target-upside levels; use revisions only |
| E4-C10 | Analysts' long-term growth optimism predicts low returns. | Highest LTG 3% a year against lowest 15% (US 1981-2016); EPS growth forecasts 10-12% against ≈6% realised over 25 years | [Bordalo et al.](https://www.nber.org/system/files/working_papers/w23863/w23863.pdf); [McKinsey 2010](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/equity-analysts-still-too-bullish) | T1/T2 | La Porta 1996 replicated (OSAP t 4.9) | — | FILTER: exclude the top-LTG decile if the field is available |
| E4-C11 | Opportunistic insider trades predict returns; routine ones do not. | US 1986-2007: value-weighted 82 bp a month (t 2.15), equal-weighted 180 bp (t 6.07); routine −20 bp (t −0.57); 6-month build-up, no reversal; gross, costs not modelled | [Cohen-Malloy-Pomorski](https://www.nber.org/system/files/working_papers/w16454/w16454.pdf) | T1 | Published in JF; post-2007 unverified | Unknown live | BUILD-candidate (US overlay; Form 4 lag 2 business days) |
| E4-C12 | Insider purchases, not sales, carry most of the information, especially in small firms. | Purchases ≈40 bp a month, sales ≈0 (1975-1996); purchases more informative (1975-1995) | [Lakonishok-Lee](https://www.nber.org/papers/w6656); [Jeng-Metrick-Zeckhauser](https://www.nber.org/papers/w6913) | T1 | Independent studies agree | — | Use buys only; KR BACKLOG (DART elestock + 2024 pre-disclosure) |
| E4-C13 | Aggregate short interest is among the strongest market-return predictors. | OOS R² 1.94% (1 month) to 13.24% (12 months), US 1973-2014; worth 343-544 bp a year | [Rapach-Ringgenberg-Zhou](https://www.sciencedirect.com/science/article/pii/S0304405X16300320) | T1 | OOS within paper; post-2014 unverified | — | CONTEXT: macro input that may only scale exposure within [0.5, 1.0] (flagged conflict) |
| E4-C14 | Stock-level shorting is informed, but public data support only a slow long-side filter. | −1.16% per 20 days for heavily shorted stocks (NYSE 2000-04, proprietary data); DTC long/short 1.2% a month; overvaluation needs constraints plus dispersion; FINRA data twice monthly | [Boehmer-Jones-Zhang](https://econpapers.repec.org/article/blajfinan/v_3a63_3ay_3a2008_3ai_3a2_3ap_3a491-527.htm); [Hong et al.](https://www.nber.org/papers/w21166); [Boehme et al.](https://econpapers.repec.org/article/cupjfinqa/v_3a41_3ay_3a2006_3ai_3a02_3ap_3a455-487_5f00.htm); [FINRA](https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest) | T1 | Multiple studies; data-access gap | GME 2021; KR ban 2023-25 | FILTER (exclude top-DTC longs); not a composite feature |
| E4-C15 | Extreme short interest can squeeze and punish a bearish reading. | GME short interest 122.97% of float; +2,700%; $483 on 28 Jan 2021 | [SEC staff](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf) | T1 | Single episode | — | Use short interest only to exclude longs, never as a short signal |
| E4-C16 | Best ideas outperform on paper, but 13F cloning after the lag has lagged the index live. | Best ideas +1.6-2.1% a quarter; Berkshire mimic +10.75% over S&P (1976-2006); GURU index 10 years 12.04% a year against S&P ≈15.5%, 5 years 7.37% against ≈13.4% (to 2026, approximate) | [Cohen-Polk-Silli](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364827); [Martin-Puthenpurackal](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=806246); [Global X](https://www.globalxetfs.com/funds/guru/); [SEC 13F](https://www.sec.gov/divisions/investment/13ffaq.htm) | T1/T2 | Live OOS since 2012 | 2016-2026 underperformance | DROP as alpha; breadth change BACKLOG |
| E4-C17 | Gross profitability is the most robust single quality measure, including in large caps, and is cheap to trade. | US 1963-2013: FF3 alpha 5.21% a year (t 4.65), 4.99% in Russell 1000; accruals 2.13% (n.s.); cost 3 bp a month | [Novy-Marx QDoVI](http://rnm.simon.rochester.edu/research/QDoVI.pdf); [Novy-Marx & Velikov](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf); [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv) | T1 | Replicated (OSAP 1_clear/1_good); post-2013 not measured | Long-only quality lagged in 2022/24/25 | BUILD-candidate: composite core |
| E4-C18 | QMJ is a robust long/short factor, but long-only quality indices are not crash hedges. | QMJ 4-factor alpha 60 bp a month (t 9.95, US 1957-2016), 61 bp global, 23/24 countries; QUAL −34.1% against −33.9% (Feb-Mar 2020); −20.28% against −18.11% (2022); −9.0% against −8.6% (Mar 2026) | [Asness-Frazzini-Pedersen](https://link.springer.com/article/10.1007/s11142-018-9470-2); [iShares QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf); own calc (skfolio data, Stocklake) | T1/T2/T3 | QMJ in 24 countries; ETF results are live | 2020, 2022, 2026 | Quality as a sector-neutral composite part; remove the "defensive" assumption |
| E4-C19 | The US value premium weakened sharply after 2006. | HML Sharpe 0.60 (1963-2006) against −0.17 (2007-2017/03); −18.9% cumulative (own calc); −39.1% drawdown to 2020; Q1 2020 worst quarter since 1963 | [French](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) (own calc); [Arnott et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3488748); [AQR](https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead); [Fama-French](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3525096) | T1/T2 | Many sources agree; statistically fragile | 2007-2020 | Value at low weight only |
| E4-C20 | Value rebounds after bubbles and in rate shocks, so it diversifies. | HML +95.7% (Mar 2000 to Dec 2002); 2022 Russell 1000 Value −7.54% against Growth −29.14%; 2025 MSCI Enhanced Value +32.87% against S&P +17.88% | own calc (French); [iShares IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); [IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf); [VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf) | T1/T2 | Style indices are not pure factors | 2023-24 (value lagged by 31 and 19 pp) | Keep value in the composite with profitability |
| E4-C21 | Value and momentum combine well because they are negatively correlated, but the US combination failed after 2007. | Sharpe 0.63 against 0.29/0.33 (US 1972-2011); global stocks 1.04; own calc 1.21 (1949-89), 0.80 (1990-2006), −0.13 (2007-2017/03) | [Asness-Moskowitz-Pedersen](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf); [Asness 1997](https://econpapers.repec.org/article/tafufajxx/v_3a53_3ay_3a1997_3ai_3a2_3ap_3a29-36.htm) | T1 | Replicated across 8 asset classes | 2007-2017 | BUILD combinations with a decay haircut; momentum sleeve under the macro rules |
| E4-C22 | Accounting fundamentals separate cheap winners from value traps. | F-score +7% a year within high B/M, long/short 23% a year (US 1976-96, small/illiquid); value/glamour returns concentrate where price and fundamentals conflict | [Piotroski 2000](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455); [Piotroski-So 2012](https://ideas.repec.org/a/oup/rfinst/v25y2012i9p2841-2875.html) | T1 | OSAP reproduces (t 5.59) | Financials −69.5% against −49.3% (Oct 2007 to Feb 2009) | FILTER: F-score floor inside the cheap bucket |
| E4-C23 | Published anomalies decay after publication and costs. | −26% OOS, −58% post-publication (97 predictors); returns halved after decimalisation; average anomaly ≈8 bp a month net; 64%/85% fail at t 1.96/3 (447 anomalies); but 98% of clear originals reproduce | [McLean-Pontiff](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623); [Chordia et al.](https://econpapers.repec.org/article/eeejaecon/v_3a58_3ay_3a2014_3ai_3a1_3ap_3a41-58.htm); [Chen-Velikov](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681); [Hou-Xue-Zhang](https://www.nber.org/papers/w23394); [Chen-Zimmermann](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3604626) | T1 | Meta-studies differ on replication but agree on decay | — | Keep the gate's 60% haircut; ≤5 pre-registered features |
| E4-C24 | Fundamental anomaly payoffs cluster on news and earnings days. | 6× higher on earnings days and 50% higher on news days (97 anomalies); ≈1/6 of the F-score spread in four 3-day windows | [Engelberg-McLean-Pontiff](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2631228); [Piotroski 2000](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455) | T1 | Published | — | Refresh signals on filing timestamps (event-driven), not on a fixed quarterly lag |
| E4-C25 | Concentration is the main threat to diversified fundamental tilts in both markets. | US top-10 ≈41% (end-2025) against ≈19% (end-2015); cap-weighted beat equal-weighted ≈32% over 2023-25; KOSPI Samsung + SK hynix 50.8% (29 Sep 2026); cap-weighted +64.1% YTD against median −5.9% | [RBC](https://www.rbcwealthmanagement.com/en-us/insights/the-great-narrowing-sp-500-concentration); [S&P Global](https://www.spglobal.com/en/research-insights/special-reports/look-forward/partner-perspectives/unlocking-potential-ahead-with-vanguard/in-the-shadows-of-giants); own calc ([marcap](https://github.com/FinanceData/marcap)) | T2 / lab data | Data-driven | 2023-2026 | CONTEXT: pre-register a capped benchmark (DC-4); single-name caps |
| E4-C26 | CANSLIM/IBD-style composites lack independent OOS validation, and the live IBD 50 ETF lagged badly. | FFTY 3.52% a year since 9 Apr 2015 against S&P ≈13.5-14% (approximate); 1 year −3.76%; components map to documented anomalies (streaks t 9.51; 52-week high t 2.0; market state 0.93% against −0.37% a month) | [stockanalysis FFTY](https://stockanalysis.com/etf/ffty/); [OSAP](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv); [Cooper-Gutierrez-Hameed](https://api.openalex.org/works/doi:10.1111/j.1540-6261.2004.00665.x) | T3 (live) / T1 (components) | One live product; fee 0.80% | 2015-2026 | DROP the composite; test components in their academic form |
| E4-C27 | Minervini SEPA/VCP is a practitioner description supported by contest claims, not by tests. | Site states "2-time U.S. Investing Champion" plus testimonials; no definitions or returns | [minervini.com](https://www.minervini.com/) | T3 | None | — | DROP for E4; send VCP to the technical panel for an independent test |
| E4-C28 | Momentum-type payoffs, earnings momentum included, depend on market state and need bear-state protection. | Momentum 0.93% a month after up markets against −0.37% after down (1929-95); 14 of 15 worst months after a negative 2-year market; dynamic strategy ≈ doubles Sharpe; UMD −49.3% Mar-May 2009 | [Cooper-Gutierrez-Hameed](https://api.openalex.org/works/doi:10.1111/j.1540-6261.2004.00665.x); [Daniel-Moskowitz](https://www.nber.org/papers/w20439); own calc (French) | T1 | Replicated | 1932, 2009 | Extend the Daniel-Moskowitz gate to SUE and revision sleeves (flag to macro) |
| E4-C29 | Point-in-time public data cover most fundamental features; consensus data lack usable history. | DART statements via API from 2015 with rcept_dt; Form 4 within 2 business days; 13F within 45 days, longs only; 10-Q 40/45 days; 10-K 60/75/90 days; KIS and FMP estimate endpoints exist, depth unknown | [OpenDART](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020); [SEC Form 4](https://www.sec.gov/about/forms/form4.pdf); [SEC 10-Q](https://www.sec.gov/files/form10-q.pdf); [SEC 10-K](https://www.sec.gov/files/form10-k.pdf); [KIS GitHub](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/estimate_perform/estimate_perform.py); [FMP](https://site.financialmodelingprep.com/developer/docs) | T1/T2 | Official documentation | — | BUILD a point-in-time layer keyed on filing timestamps; start the archive now |
| E4-C30 | Korean regulation changed several fundamental signals between 2023 and 2026. | Short-selling ban 6 Nov 2023 to 30 Mar 2025; insider 30-day pre-disclosure from 24 Jul 2024 (≥1% or ≥KRW 5bn); Value-up program from 26 Feb 2024; low-P/B list standards 28 Jul 2026 (≈120 firms) | [FSC short selling](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Short%20Selling); [FSC insider](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=insider); [FSC Value-up](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Value-up); [FSC P/B](https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Price-to-Book) | T1 | Official | Regime breaks in backtests | CONTEXT: regime dummies and before/after splits in DC-1, DC-8 and DC-11 |

---

## 12. Source list

**Peer-reviewed papers and working papers (T1)**
- Chan, Jegadeesh & Lakonishok (1996), Momentum Strategies, JF — https://econpapers.repec.org/article/blajfinan/v_3a51_3ay_3a1996_3ai_3a5_3ap_3a1681-1713.htm ; https://www.nber.org/papers/w5375
- Novy-Marx (2015), Fundamentally, Momentum is Fundamental Momentum, NBER w20984 — https://www.nber.org/system/files/working_papers/w20984/w20984.pdf
- Martineau (2022), Rest in Peace Post-Earnings Announcement Drift, CFR — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607
- UCLA Anderson Review (Subrahmanyam) on 2025 PEAD papers — https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/
- Kettell, McInnis & Zhao, Why Has PEAD Declined Over Time? — https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf
- Novy-Marx & Velikov (2016), A Taxonomy of Anomalies and Their Trading Costs, RFS / NBER w20721 — https://www.nber.org/system/files/working_papers/w20721/w20721.pdf ; https://www.nber.org/papers/w20721
- Engelberg, McLean & Pontiff, Anomalies and News — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2631228
- Frazzini & Lamont (2007), The Earnings Announcement Premium and Trading Volume, NBER w13090 — https://www.nber.org/system/files/working_papers/w13090/w13090.pdf
- Barber, De George, Lehavy & Trueman (2013), The Earnings Announcement Premium Around the Globe, JFE — https://econpapers.repec.org/article/eeejfinec/v_3a108_3ay_3a2013_3ai_3a1_3ap_3a118-138.htm
- Kothari, Shu & Wysocki (2009), Do Managers Withhold Bad News?, JAR — https://ideas.repec.org/a/bla/joares/v47y2009i1p241-276.html
- Chen, Matsumoto & Rajgopal (2011), Is Silence Golden?, JAE — https://ideas.repec.org/a/eee/jaecon/v51y2011i1p134-150.html
- Womack (1996), Do Brokerage Analysts' Recommendations Have Investment Value?, JF — https://econpapers.repec.org/article/blajfinan/v_3a51_3ay_3a1996_3ai_3a1_3ap_3a137-67.htm
- Barber, Lehavy, McNichols & Trueman (2001), Can Investors Profit from the Prophets?, JF — https://econpapers.repec.org/article/blajfinan/v_3a56_3ay_3a2001_3ai_3a2_3ap_3a531-563.htm
- Barber, Lehavy, McNichols & Trueman (2003), Reassessing the Returns to Analysts' Stock Recommendations, FAJ — https://econpapers.repec.org/article/tafufajxx/v_3a59_3ay_3a2003_3ai_3a2_3ap_3a88-96.htm
- Brav & Lehavy (2003), An Empirical Analysis of Analysts' Target Prices, JF — https://econpapers.repec.org/article/blajfinan/v_3a58_3ay_3a2003_3ai_3a5_3ap_3a1933-1967.htm
- Bradshaw, Brown & Huang (2013), Target Price Forecasting Ability, RAST — https://ideas.repec.org/a/spr/reaccs/v18y2013i4d10.1007_s11142-012-9216-5.html
- Bordalo, Gennaioli, La Porta & Shleifer, Diagnostic Expectations and Stock Returns, NBER w23863 — https://www.nber.org/system/files/working_papers/w23863/w23863.pdf
- Rapach, Ringgenberg & Zhou (2016), Short Interest and Aggregate Stock Returns, JFE — https://www.sciencedirect.com/science/article/pii/S0304405X16300320
- Boehme, Danielsen & Sorescu (2006), Short-Sale Constraints, Differences of Opinion, and Overvaluation, JFQA — https://econpapers.repec.org/article/cupjfinqa/v_3a41_3ay_3a2006_3ai_3a02_3ap_3a455-487_5f00.htm
- Boehmer, Jones & Zhang (2008), Which Shorts Are Informed?, JF — https://econpapers.repec.org/article/blajfinan/v_3a63_3ay_3a2008_3ai_3a2_3ap_3a491-527.htm
- Hong, Li, Ni, Scheinkman & Yan, Days to Cover and Stock Returns, NBER w21166 — https://www.nber.org/papers/w21166
- Lakonishok & Lee (2001), Are Insider Trades Informative?, RFS / NBER w6656 — https://www.nber.org/papers/w6656
- Jeng, Metrick & Zeckhauser, The Profits to Insider Trading, NBER w6913 — https://www.nber.org/papers/w6913
- Cohen, Malloy & Pomorski (2012), Decoding Inside Information, JF / NBER w16454 — https://www.nber.org/system/files/working_papers/w16454/w16454.pdf
- Cohen, Polk & Silli, Best Ideas — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1364827
- Martin & Puthenpurackal, Imitation is the Sincerest Form of Flattery (Berkshire Hathaway) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=806246
- Piotroski (2000), Value Investing: The Use of Historical Financial Statement Information, JAR — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=249455
- Piotroski & So (2012), Identifying Expectation Errors in Value/Glamour Strategies, RFS — https://ideas.repec.org/a/oup/rfinst/v25y2012i9p2841-2875.html
- Novy-Marx, The Quality Dimension of Value Investing — http://rnm.simon.rochester.edu/research/QDoVI.pdf
- Asness, Frazzini & Pedersen (2019), Quality Minus Junk, RAST — https://link.springer.com/article/10.1007/s11142-018-9470-2
- Asness (1997), The Interaction of Value and Momentum Strategies, FAJ — https://econpapers.repec.org/article/tafufajxx/v_3a53_3ay_3a1997_3ai_3a2_3ap_3a29-36.htm
- Asness, Moskowitz & Pedersen (2013), Value and Momentum Everywhere, JF — https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf
- Daniel & Moskowitz (2016), Momentum Crashes, JFE / NBER w20439 — https://www.nber.org/papers/w20439 ; https://www.nber.org/system/files/working_papers/w20439/w20439.pdf
- Cooper, Gutierrez & Hameed (2004), Market States and Momentum, JF (abstract via OpenAlex) — https://api.openalex.org/works/doi:10.1111/j.1540-6261.2004.00665.x
- McLean & Pontiff (2016), Does Academic Research Destroy Stock Return Predictability?, JF — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623
- Chen & Velikov, Zeroing in on the Expected Returns of Anomalies — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681
- Hou, Xue & Zhang, Replicating Anomalies, NBER w23394 — https://www.nber.org/papers/w23394
- Jensen, Kelly & Pedersen, Is There a Replication Crisis in Finance?, NBER w28432 — https://www.nber.org/papers/w28432
- Chen & Zimmermann, Open Source Cross-Sectional Asset Pricing — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3604626 ; data documentation https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv
- Chordia, Subrahmanyam & Tong (2014), Have Capital Market Anomalies Attenuated?, JAE — https://econpapers.repec.org/article/eeejaecon/v_3a58_3ay_3a2014_3ai_3a1_3ap_3a41-58.htm
- Khandani & Lo, What Happened to the Quants in August 2007?, NBER w14465 — https://www.nber.org/papers/w14465
- Arnott, Harvey, Kalesnik & Linnainmaa, Reports of Value's Death May Be Greatly Exaggerated — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3488748
- Fama & French, The Value Premium — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3525096

**Official and regulatory sources (T1)**
- SEC Form 4 instructions — https://www.sec.gov/about/forms/form4.pdf
- SEC Form 13F FAQ — https://www.sec.gov/divisions/investment/13ffaq.htm
- SEC Form 10-Q — https://www.sec.gov/files/form10-q.pdf ; Form 10-K — https://www.sec.gov/files/form10-k.pdf
- SEC staff report on early-2021 market structure (GME) — https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf
- FINRA short interest — https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest
- FSC (Korea) press releases — https://www.fsc.go.kr/eng/pr010101 ; short selling https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Short%20Selling ; insider https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=insider ; Value-up https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Value-up ; low P/B https://www.fsc.go.kr/eng/pr010101?srchKey=all&srchText=Price-to-Book
- OpenDART guides — https://opendart.fss.or.kr/guide/main.do ; fnlttSinglAcntAll https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020 ; elestock https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS004&apiId=2019022 ; list https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
- Ken French Data Library (accessed via the copy bundled in linearmodels 7.0) — https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html ; https://pypi.org/project/linearmodels/

**Banks, asset managers and index providers (T2)**
- AQR, Is (Systematic) Value Investing Dead? (2020) — https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead ; QMJ page https://www.aqr.com/Insights/Research/Working-Paper/Quality-Minus-Junk ; Value and Momentum Everywhere page https://www.aqr.com/Insights/Research/Journal-Article/Value-and-Momentum-Everywhere
- iShares/BlackRock product pages: QUAL https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf ; IVV https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf ; IWD https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf ; IWF https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf ; MTUM https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf ; VLUE https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf ; USMV https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf
- Global X GURU ETF — https://www.globalxetfs.com/funds/guru/
- RBC Wealth Management, The "Great Narrowing" (22 Jan 2026) — https://www.rbcwealthmanagement.com/en-us/insights/the-great-narrowing-sp-500-concentration
- S&P Global (Vanguard partner piece), In the Shadows of Giants — https://www.spglobal.com/en/research-insights/special-reports/look-forward/partner-perspectives/unlocking-potential-ahead-with-vanguard/in-the-shadows-of-giants
- S&P DJI, S&P 500 Quality Index — https://www.spglobal.com/spdji/en/indices/strategy/sp-500-quality-index/
- McKinsey, Equity Analysts: Still Too Bullish (2010) — https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/equity-analysts-still-too-bullish ; The Misguided Practice of Earnings Guidance (2006) — https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/our-insights/the-misguided-practice-of-earnings-guidance
- Lord Abbett, Price and Operating Momentum (Nov 2025) — https://www.lordabbett.com/content/dam/lordabbett-captivate/documents/insights/InvestmentPerspectives/2025/11425-the-benefits-of-price-and-operating-momentum-in-equity-portfolios-non-us.pdf
- Korea Investment & Securities Open API (official GitHub) — https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/estimate_perform/estimate_perform.py ; https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/invest_opinion/invest_opinion.py ; https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/invest_opinion/chk_invest_opinion.py ; https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/invest_opbysec/invest_opbysec.py
- Financial Modeling Prep developer docs — https://site.financialmodelingprep.com/developer/docs

**Other (T3: aggregators, practitioner pages, packaged datasets)**
- stockanalysis.com, FFTY — https://stockanalysis.com/etf/ffty/
- Minervini — https://www.minervini.com/
- skfolio (bundled factor-ETF and S&P 500 index datasets, 2014-2022) — https://pypi.org/project/skfolio/
- Stocklake market-data API (MCP tool pull on 2 Oct 2026; no public URL), used for QUAL and SPY daily closes from 21 Apr 2025 to 1 Oct 2026
- Lab data: KRX marcap (https://github.com/FinanceData/marcap), Shiller monthly S&P 500 and CBOE VIX daily files in `/home/claude/data_raw/us/`

**Pages I could not read (blocked or rate-limited), recorded for the writer**
- Ken French site and AQR dataset downloads: HTTP 403.
- Yahoo Finance and SEC data.sec.gov: blocked.
- Wiley article pages: 403.
- Semantic Scholar, OpenAlex search and Crossref: 429. **The final api.crossref.org query for CAN SLIM studies was refused with HTTP 429 and could not be read.**
- DuckDuckGo and EconPapers search: robots.txt.
- innovatoretfs.com: redirect loop.
- investors.com: blocked.
- S&P DJI factsheet PDF: robots.txt.
- The web-search budget for the session was exhausted mid-task.
