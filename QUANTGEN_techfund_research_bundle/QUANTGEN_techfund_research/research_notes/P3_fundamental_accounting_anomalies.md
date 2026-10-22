# P3 — Professor of Accounting and Valuation: fundamental-analysis signals, accounting anomalies and market-level valuation (as of 2 Oct 2026)

Labels used throughout: market; sample period; IS (in-sample, original paper) / OOS (out-of-sample, post-publication or held-out); gross / net of costs; EW / VW (equal / value weighted); L/S (long-short). "Local" means a test P3 ran during this session on QUANTGEN's own data (`/home/claude/data_raw/marcap` KRX all-stock daily 1995-05 to 2026-09; `/home/claude/data_raw/us/shiller_sp500_monthly.csv`). Local tests are unreviewed, single-researcher and not pre-registered. Network note: Ken French's library, AQR data, JKP, FRED, SEC EDGAR, OpenDART, KRX and Yale were blocked to shell downloads in this session (proxy 403), so no French factor returns after 2018 could be recomputed; pages were read with a web fetcher instead.

## 0. Persona, position summary and proposed changes to the prior map

### Takeaway
**Persona.** P3 is a *fictional composite* "Professor of Accounting and Valuation" (not a real person): teaches financial statement analysis and valuation, has worked with NYU-Stern-style valuation curricula (intrinsic value, implied equity risk premium), and argues from the lens that *accounting measurement and point-in-time (PIT) data decide whether a fundamental signal is real*.

**Position summary.** (1) Accounting signals are real but small after costs and publication: in the US, only slow composites (value + profitability, investment, net issuance) keep net premia at a 50 bp per side cost; accruals, a standalone Piotroski F-score, PEAD, analyst revisions, buyback drift and distress long-shorts do not. (2) Value's 2007-2020 failure was mostly valuation compression plus mis-measured book value (intangibles), not dead fundamentals, so QUANTGEN should fix measurement (timely price, intangibles-adjusted book) and pair value with profitability instead of buying raw low P/B. (3) US PEAD has been gone for non-microcap stocks since about 2006; the prior map's US "earnings drift 2" should become 0, and Korea's "earnings drift 3" has no Korean evidence behind it that I could open, so it should be 1 until a DART-timestamped test runs. (4) CAPE is a 10-year expected-return *context*, not a timing signal; at 1-year horizons it fails out of sample (locally, OOS R² −11% since 1990 and −39% for 2010-2022), and the Fed model should not be built. (5) In Korea the binding constraint is PIT data (OpenDART statements start in 2015; filing receipts carry a date but no time), so the first Korean fundamental card should be **net share issuance**, which needs only KRX listed-share counts; my local test shows it survives 35 bp per side over 1996-2026 (long-only active IR 0.84, 90% CI 0.46-1.25) but has decayed (IR 0.42 since 2017, CI −0.28 to 0.95). (6) Realistic expectation for a US value-quality composite: net L/S Sharpe ≈ 0.3-0.4 at 50 bp per side after decay haircuts, ≈ 0.15 after QUANTGEN's 60% live haircut; long-only tilts keep roughly 60% of value profits.

### Cited Findings
- Across 97 published predictors, returns were 26% lower out of sample and 58% lower after publication (US) — [McLean & Pontiff 2016, JF (copy)](https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf).
- Strategies with one-sided monthly turnover below 50% generally keep significant net spreads; a buy/hold spread is the single most effective cost mitigation — [Novy-Marx & Velikov, NBER w20721](https://www.nber.org/papers/w20721).
- Value + profitability ("ValProf") earned 0.82%/month gross and 0.77% net (t 4.82), US 1963-2012, IS — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- PEAD has not existed for non-microcap US stocks since 2006 (since 2016 for microcaps) — [Martineau, SSRN 3111607](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607).
- OpenDART's full-statement API covers 2015 onward; the disclosure list returns `rcept_dt` as YYYYMMDD only — [OpenDART fnlttSinglAcntAll](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020); [OpenDART list API](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001).
- Long positions supply about 60% of value profits and half of momentum profits (US and international) — [Israel & Moskowitz 2013 (AQR page)](https://www.aqr.com/Insights/Research/Journal-Article/The-Role-of-Shorting-Firm-Size-and-Time-on-Market-Anomalies).
- Local Korea issuance and CAPE results: see §5 and §6 (Local, `marcap` and Shiller files).

### Inferences
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

### Gaps
- No Korean academic paper on value, quality, F-score or PEAD could be opened in this session (web-search budget exhausted; KRX/FnGuide/KCI blocked), so Korean priors other than issuance rest on international and emerging-market samples.
- French factor returns after 2018 (HML, RMW, CMA through Aug-2026) could not be downloaded; 2021-2026 value/quality behaviour relies on iShares style-ETF returns.

## 1. Value: the premium, the 2007-2020 drawdown debate, and 2021-2026

### Takeaway
The value premium is real over long samples and outside the US but is small and statistically fragile among large US stocks after 1991. The 2007-2020 drawdown (−54.8% over 13.5 years) came mostly from value getting cheaper relative to growth, and was much milder when book value includes intangibles. Since 2021, US value has rebounded in some years (2022, 2025-26) but still trails growth cumulatively, and outcomes now depend heavily on how "value" is built.

### Cited Findings
- **Foundations.** Size and book-to-market subsume the cross-sectional power of beta, leverage and E/P (US, 1963-1990, IS) — [Fama & French 1992 (RePEc)](https://ideas.repec.org/a/bla/jfinan/v47y1992i2p427-65.html). OSAP's replication notes a book-to-market (December ME) slope t = 5.71 in Fama-MacBeth regressions, 1963-1990 — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- Lakonishok-Shleifer-Vishny (portfolios formed Apr-1968 to Apr-1989, US, IS): value-minus-glamour year-1 return gaps of 7.8% (B/M), 8.8% (C/P), 5.4% (E/P), 8.7% (C/P × past sales growth); 5-year cumulative size-adjusted gaps of 38.7%, 42.9%, 26.3% and 46%; in the worst 25 market months value lost 8.6% vs glamour 10.3%, which they read as extrapolation error rather than risk — [LSV, NBER w4360](https://www.nber.org/system/files/working_papers/w4360/w4360.pdf).
- **International.** Value premiums exist in North America, Europe, Japan and Asia Pacific and, except in Japan, shrink with firm size — [Fama & French 2012, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v105y2012i3p457-472.html). Value appears in all 18 emerging markets studied, Jan-1990 to Dec-2011 — [Cakici, Fabozzi & Tan 2013 (RePEc)](https://ideas.repec.org/a/eee/ememar/v16y2013icp46-65.html). Across 49 countries, cash-flow-to-price and momentum, not size or B/M, best capture global return variation — [Hou, Karolyi & Kho 2011 (RePEc)](https://ideas.repec.org/a/oup/rfinst/v24y2011i8p2527-2574.html).
- **Decline, US.** Average monthly value premiums: market-wide 0.42% (t 3.25), big value 0.36% (t 2.91), small value 0.58% (t 3.19) in 1963-1991, vs 0.11% (t 0.60), 0.05% (t 0.24), 0.33% (t 1.52) in 1991-2019; the difference is not significant (t 1.39 market, 1.41 big) — [Fama & French "The Value Premium" (WP copy)](https://ebicapital.nl/wp-content/uploads/2022/05/The-Value-Premium.pdf); published in RAPS 2021 — [OUP abstract](https://academic.oup.com/raps/article-abstract/11/1/105/6033665). In annual terms the big-stock premium fell from 4.3% to 0.6% a year and the small-stock premium from 7.0% to 4.0% — [Chicago Booth Review](https://www.chicagobooth.edu/review/value-stock-premium-shrinking).
- The value premium falls with firm size and is weak among the largest stocks; about 60% of value profits come from the long side — [Israel & Moskowitz 2013](https://www.aqr.com/Insights/Research/Journal-Article/The-Role-of-Shorting-Firm-Size-and-Time-on-Market-Anomalies).
- **2007-2020 drawdown, decomposition.** HML fell 54.8% from Jan-2007 to Jun-2020 (13.5 years, the longest since 1963; the 1999-2000 drawdown was −40.6%). HML averaged +6.1%/yr from Jul-1963 to Jun-2007 and −6.1%/yr from Jul-2007 to Jun-2020. Revaluation (value getting cheaper relative to growth) contributed −7.2 pp/yr after 2007 vs +0.2 pp before; the structural part (income yield + migration) fell from +5.9 to +1.1 pp/yr; revaluation explains 116% of the shortfall. A drawdown this deep appeared in 2.3% of 1 million bootstrap paths. The value spread sat at its 100th percentile in Jun-2020, with a mean-reversion half-life of about 2.2 years — [Arnott, Harvey, Kalesnik & Linnainmaa, FAJ 2021](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf).
- Systematic value is not dead: expectations of fundamentals keep driving returns, and the criticisms "generally lack in substance" — [Israel, Laursen & Richardson, JPM 2021 (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/Is-Systematic-Value-Investing-Dead).
- **Intangibles.** Intangibles-adjusted value (HML_INT) returned 5.60%/yr (Sharpe 0.86) vs 3.49% (0.35) for standard HML over 1975-2018, with a 3.86%/yr alpha on HML; over 2007-2018 HML_INT earned +0.76%/yr vs −2.77% for HML (US, IS) — [Eisfeldt, Kim & Papanikolaou, NBER w28056 PDF](https://www.nber.org/system/files/working_papers/w28056/w28056.pdf); published in Critical Finance Review 2022 — [NBER page](https://www.nber.org/papers/w28056). The same adjustment adds 2.2 pp/yr after 2007 and shortens the drawdown to 3.5 years at −43.0% — [AHKL 2021](https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf).
- Lev and Srivastava: $1 in value-minus-glamour grew to $0.82 over 2010-2018; industry-adjusted value returns over 2007-2018 averaged 0.65%/yr (not significant). The median market-to-book rose from about 1.0 (mid-1980s) to about 3.0 (2018). Capitalising intangibles turns the 2010-2018 loss into a gain. Value firms' average stay in the value portfolio rose from 2.5 to 3.3 years — [Lev & Srivastava, CFR 2022](https://cfr.ivo-welch.org/forthcoming/papers/lev2021explaining.pdf).
- **Timely prices.** Using current prices (with properly lagged book) yields value alphas of 305-378 bp/yr, US 1950-2011 and international 1983-2011 — [Asness & Frazzini, "The Devil in HML's Details" (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/The-Devil-in-HMLs-Details).
- **2021-2026 (US, long-only style ETFs, NAV total return).** Russell 1000 Value (IWD) vs Russell 1000 Growth (IWF): 2021 24.92% vs 27.37%; 2022 −7.72% vs −29.26%; 2023 11.31% vs 42.49%; 2024 14.16% vs 33.11%; 2025 15.71% vs 18.34%; 2026 YTD to 30 Sep 16.12% vs 5.22% — [iShares IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); [iShares IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf). Compounded (P3 arithmetic), Jan-2021 to Sep-2026: value +96.8% vs growth +112.8%.
- Construction dispersion: the sector-neutral MSCI USA Enhanced Value index (VLUE) returned +32.65% in 2025 (vs +15.71% for Russell 1000 Value) and +80.03% over the year to 30 Jun 2026 — [iShares VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf).
- Valuation gap on 30 Sep 2026: IWF P/B 15.74, P/E 42.51 vs IWD P/B 3.27, P/E 22.87 — [iShares IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf); [iShares IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf).
- **Korea context.** KOSPI P/B averaged 0.99 in 2014-2024, vs 1.8 for Japan and 3.7 for the US. The Corporate Value-Up Program launched Feb-2024, and the Korea Value-Up Index (Oct-2024, 100 firms) has beaten KOSPI 200 by 17% since launch. Commercial Act revisions followed in Jul/Aug-2025, a dividend-tax reform in Jan-2026, and a rise in the independent-director share in Jul-2026 — [KEIA](https://keia.org/analysis/explaining-south-koreas-stock-market-boom/) (T2).

### Inferences
- Do not build a raw low-P/B card in the US. Value's US large-cap premium after 1991 is indistinguishable from zero, and the post-2007 losses are dominated by valuation moves that no fundamental signal predicts in real time.
- If value is used, measure it properly: book lagged to its filing date but divided by *today's* market cap (Asness-Frazzini), with capitalised R&D (and optionally part of SG&A) added to book (Eisfeldt-Kim-Papanikolaou; Lev-Srivastava). Combine it with profitability (§2). These are construction choices made after the 2007-2020 failure, so each counts as a trial in the deflated-Sharpe step.
- Korea is a different case: market-wide P/B near 1, policy-driven re-rating since Feb-2024, and extreme concentration (Samsung + SK hynix ≈ 54-56% of KOSPI per the macro research). A Korean value card must (a) split samples at Feb-2024, (b) use sector-neutral or capped weights (R-07 caps), and (c) treat 2024-26 as a regime, not as an OOS confirmation.
- Value timing by value spread is not supported (see §6 and Ilmanen et al. in §8); consistent with the macro decision that nothing scales above 1.0.

### Gaps
- French HML/RMW/CMA annual returns for 2019-2026 were not retrievable (host blocked); the ETF proxies are long-only and not the same as the long-short factors.
- No Korean study of the value premium (PBR/PER sorts) was opened; Korea's value premium is unquantified here.
- The LSV figures come from a web-fetch summary of the NBER PDF; the table-level definitions (year-1 vs annualised) should be re-checked against the PDF before quoting precisely.

## 2. Quality and profitability: GP/A, QMJ, Buffett's Alpha, Piotroski F-score, Mohanram G-score, RMW/CMA

### Takeaway
Profitability is the strongest accounting signal and a natural hedge for value. Gross profitability plus value roughly doubles value's Sharpe in-sample, and quality-minus-junk earns large alphas in 23 of 24 developed countries. However, a long-only quality ETF did not beat the market over 2021-2026 and lost slightly more in 2022. A standalone F-score is weak net of costs in broad US samples, though it was strong internationally in 2000-2018 (including emerging markets with Korea).

### Cited Findings
- **Gross profitability.** (Revenue − COGS)/total assets: value-weighted quintile spread 0.31%/month (t 2.49), Fama-French 3-factor alpha 0.52% (t 4.49), HML loading −0.44; large caps 0.26% (t 1.88), small 0.67% (t 4.59); US Jul-1963 to Dec-2010, IS. Running profitability and value together at full size: 0.71%/month at 2.89% monthly volatility, Sharpe 0.85 vs 0.34 for the market; the two strategies' correlation is −0.57. Non-US developed markets 1990-2009: GP/A 0.76%/month (t 2.25) vs B/M 0.51% (t 2.12) — [Novy-Marx 2013, JFE (PDF copy)](https://oldschoolvalue-files.s3.amazonaws.com/pdf/Novy-Marx_Gross-Profitability-Anomaly_JFE_2013.pdf).
- Net of trading costs, US 1963-2012: gross profitability 0.40% gross, 0.37% net (t 2.74); value 0.47% gross, 0.42% net (t 2.39); ValProf 0.82% gross, 0.77% net (t 4.82); one-sided turnover about 2-3%/month with annual rebalancing — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- **Quality minus junk.** Quality = profitability (incl. GP/A, ROE, ROA, CF/A, margins, low accruals) + growth + safety (low beta, leverage, bankruptcy risk, ROE volatility). Four-factor alpha 60 bp/month (t 9.95), US Jun-1957 to Dec-2016; 61 bp (t 8.07) across 24 developed countries, Jun-1989 to Dec-2016; positive in 23 of 24 countries, significant in 18. Quality explains only about 10% of price variation univariately, and QMJ shows mild positive convexity in market stress — [Asness, Frazzini & Pedersen, RAS 2019](https://link.springer.com/article/10.1007/s11142-018-9470-2).
- **Buffett's Alpha.** Berkshire's Sharpe ratio of 0.76 is the highest of any stock or fund with 30+ years of history; leverage averages about 1.6:1 (partly insurance float); the alpha becomes insignificant once betting-against-beta and QMJ exposures are controlled for — [Frazzini, Kabiller & Pedersen, NBER w19681](https://www.nber.org/papers/w19681); [AQR FAJ page](https://www.aqr.com/Insights/Research/Journal-Article/Buffetts-Alpha).
- **Five-factor model.** With profitability (RMW) and investment (CMA), HML becomes redundant in describing US average returns; the model fails for small stocks that invest heavily despite low profitability — [Fama & French 2015 (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2287202). RMW sorts on operating profitability (revenue − COGS − SG&A − interest)/book equity; CMA on asset growth; portfolios are formed each June using fiscal-year t−1 data — [French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html).
- **Not universal.** Japan shows strong B/M effects but little relation of returns to profitability or investment — [Fama & French 2017, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v123y2017i3p441-463.html).
- **Emerging markets.** Across 28 emerging markets over 21 years, cash-flow-to-price, gross profitability, composite equity issuance and momentum predict returns robustly — [Hanauer & Lauterbach 2019 (RePEc)](https://ideas.repec.org/a/eee/ememar/v38y2019icp265-286.html).
- **Piotroski F-score.** Original result: a 23.5% annual EW high-minus-low spread among US value stocks, 1976-1996 (as restated by Walkshäusl) — [Walkshäusl 2020, J. Asset Mgmt](https://d-nb.info/121155211X/34). OSAP's replication: 1.96%/month (t 5.59) for a decile spread, with rebalancing four months after fiscal year-end — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- F-score OOS internationally, Jul-2000 to Jun-2018, all firms (not only value), size-adjusted high-minus-low: developed ex-US 0.79%/month (t 6.5); emerging 0.95% (t 9.6); Europe 1.08%; Asia-Pacific 0.57% (t 4.8); large caps 0.62% (t 4.0) developed and 0.76% (t 5.2) emerging; about 0.30-0.40%/month for large caps after five-factor adjustment. South Korea is in the emerging sample; portfolios formed in July from the prior fiscal year — [Walkshäusl 2020](https://d-nb.info/121155211X/34).
- F-score in broad US tests net of costs, 1973-2012: 0.20%/month gross, 7.24% one-sided turnover, **0.09% net (t 0.45)** — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- **Mohanram G-score** (low-B/M firms: profitability and cash flow, earnings and sales stability, R&D/capex/advertising intensity): 1.575%/month EW (t 9.14), 1978-2001, IS — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- **Quality 2021-2026 (long-only, US).** MSCI USA Quality (QUAL) vs Russell 1000 (IWB): 2021 26.90% vs 26.27%; 2022 −20.39% vs −19.24%; 2023 30.83% vs 26.40%; 2024 22.23% vs 24.33%; 2025 12.65% vs 17.19%; 2026 YTD to 30 Sep 11.10% vs 10.24% — [iShares QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf); [iShares IWB](https://www.ishares.com/us/products/239707/ishares-russell-1000-etf). Compounded (P3 arithmetic): +102.2% vs +107.0%. By contrast, the macro research records French RMW at +8.4% in 2022 (QUANTGEN project doc, QUANTGEN_MACRO_BACKLOG.md §6.6).

### Inferences
- Profitability's best use is as the partner of value (negative correlation, same low turnover). The prior map's "quality: most consistent sign, 0.3-0.5 L/S" is right gross and in-sample for the US, but after decay and a 50 bp cost the standalone expectation is about 0.15-0.2 (§8). Quality is also not universal (Japan).
- Long-only quality ≠ the long-short factor: QUAL lagged in 2022 while RMW gained. QUANTGEN should not expect long-only quality to work as a crash hedge, which is consistent with holding quality at 1.0× (macro rule).
- The F-score works best as a *filter inside value* and in less-efficient markets (emerging, small caps). In large US stocks it adds little net. For Korea, the emerging-market evidence (t 9.6, 2000-2018) justifies testing it as a component of a Korean composite once OpenDART data are PIT-stored.
- Korean implementation caveat (not verified here): under K-IFRS a company may present expenses by nature rather than by function, so "cost of sales" (매출원가) and hence gross profit may be missing for some filers; the data lab must measure coverage before GP/A is used in Korea.

### Gaps
- No post-2016 OOS QMJ or post-2010 GP/A long-short returns were opened (French/AQR data blocked).
- Mohanram's own abstract was not retrievable (404); the G-score has no post-publication evidence in this note.
- Korea-specific quality evidence (local GP/A or ROE sorts) is absent; Walkshäusl reports only regional aggregates, not a Korea row.

## 3. Accruals and earnings quality: Sloan, its decline, Beneish M-score, Dechow et al.

### Takeaway
The accrual anomaly was large in 1962-1991 (10.4% in year 1) but had decayed by around 2011 to "no longer reliably positive", and its net-of-cost spread over 1963-2012 is insignificant. Earnings-quality measures still matter as *screens*: the M-score flags firms whose accruals are likely to reverse, with a large return gap inside the low-accrual group.

### Cited Findings
- Sloan (1996): 40,679 firm-years, 1962-1991. Accruals (balance-sheet method: Δcurrent assets ex cash − Δcurrent liabilities ex short-term debt and taxes payable − depreciation, scaled by average assets) are less persistent than cash flows (coefficients 0.765 vs 0.855). A low-minus-high accrual hedge earned size-adjusted 10.4% (t+1), 4.8% (t+2), 2.9% (t+3). Over 40% of the year-1 return came around the next quarterly earnings announcements — [Sloan 1996, TAR (copy)](https://www.cuhk.edu.hk/acy2/workshop/June2009Wasley/1996TAR%29.pdf).
- Hedge returns to accruals decayed in US markets to the point of being "no longer reliably positive"; the authors attribute this more to hedge-fund capital than to a weaker signal — [Green, Hand & Soliman 2011, Management Science (PSU record)](https://pure.psu.edu/en/publications/going-going-gone-the-apparent-demise-of-the-accruals-anomaly/).
- Net of costs, US 1963-2012: accruals 0.27%/month gross, 5.74% turnover, 0.18% net (t 1.43) — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- Related accrual-type signals in the original papers: percent operating accruals 0.97%/month (t 3.29, 1989-2008), abnormal accruals 0.92%/month (t 8.43, 1971-1992), net operating assets 1.48%/month (t 8.45, 1964-2002), all EW and IS — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).
- Beneish M-score: high manipulation-probability firms earn lower returns, just under 1%/month risk-adjusted. In the lowest-accrual quintile the high-minus-low M-score spread is −19.8% over 12 months; the score predicts whether accruals persist — [Beneish, Lee & Nichols 2013, FAJ (RePEc)](https://ideas.repec.org/a/taf/ufajxx/v69y2013i2p57-82.html).
- Dechow, Ge, Larson & Sloan (2011), "Predicting Material Accounting Misstatements", Contemporary Accounting Research 28(1) — bibliographic record only; no abstract or numbers were accessible — [RePEc](https://ideas.repec.org/a/wly/coacre/v28y2011i1p17-82.html).
- Survey: transaction costs and the ex-ante vs ex-post treatment of risk materially change conclusions about accounting anomalies' exploitability — [Richardson, Tuna & Wysocki 2010, JAE (RePEc)](https://ideas.repec.org/a/eee/jaecon/v50y2010i2-3p410-454.html).

### Inferences
- Do not build an accruals return card (net t 1.43 even before post-2011 decay). Keep accruals as a small-weight component of the quality composite (it is already inside QMJ's profitability block).
- The M-score and a misstatement score are better used as *exclusion screens* for long books (avoid likely manipulators) than as long-short factors. That is useful in a long-only individual-investor context and costs little turnover.
- Korea: an M-score needs receivables, gross margin, asset quality, depreciation, SG&A, leverage and total accruals. All of these are on OpenDART (2015+), subject to the COGS caveat in §2.

### Gaps
- No post-2011 US accrual returns and no international or Korean accrual evidence were opened (the Pincus et al. international paper returned 404).
- The sample period of Beneish-Lee-Nichols and the Dechow et al. F-score accuracy are not documented here.

## 4. Earnings news: Ball-Brown, PEAD, the earnings-announcement premium, analyst revisions

### Takeaway
Earnings news is priced faster than it used to be. In the US, PEAD has been absent for non-microcap stocks since about 2006 and for microcaps since about 2016. Where it survives it lives in illiquid stocks whose trading costs consume 70-100% of the profit. The earnings-announcement *premium* (holding stocks through scheduled announcements) is a separate, calendar-driven effect with global support in about half of countries. Analyst-recommendation strategies are profitable gross but not reliably net.

### Cited Findings
- Ball & Brown (1968), "An Empirical Evaluation of Accounting Income Numbers", JAR 6(2):159-178 — bibliographic record — [RePEc](https://ideas.repec.org/a/bla/joares/v6y1968i2p159-178.html). Bernard & Thomas (1989), JAR 27, and (1990), JAE 13(4) — bibliographic records only; magnitudes not accessible — [RePEc 1989](https://ideas.repec.org/a/bla/joares/v27y1989ip1-36.html); [RePEc 1990](https://ideas.repec.org/a/eee/jaecon/v13y1990i4p305-340.html).
- **Liquidity.** Earnings-momentum long-short returns were 0.04%/month in the most liquid stocks vs 2.43%/month in the most illiquid, 1972-2005; transaction costs consume 70-100% of potential profits — [Chordia, Goyal, Sadka, Sadka & Shivakumar 2009, FAJ (RePEc)](https://ideas.repec.org/a/taf/ufajxx/v65y2009i4p18-32.html).
- **Disappearance.** Using IBES (1984-2019) and Compustat (1973-2019): since 2006, analyst earnings surprises fail to predict 60-day post-announcement returns for all-but-microcap stocks; for microcaps this holds since 2016. The announcement-day response coefficient rose six-fold (0.002 in 1984-1990 to 0.012 in 2016-2019) — [Martineau, CFR 2022 (SSRN abstract)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607); numbers from the full text — [document copy (T3 host)](https://www.readkong.com/page/rest-in-peace-post-earnings-announcement-drift-critical-7777848).
- Hedge PEAD (SUE decile 10 − 1, buy-and-hold abnormal return from day +2 to the day after the next announcement) averaged 4.4% per quarter over 1974-2020 (526,828 firm-quarters). It declined about 2 bp per quarter and is indistinguishable from zero after 2017; the decline disappears once falling SUE persistence is controlled for — [Kettell, McInnis & Zhao (UT Austin; Columbia CEASA conference PDF)](https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf).
- A 2025 replication over Feb-2001 to Dec-2024 finds PEAD t = 2.18 with all stocks but t = 1.43 excluding microcaps (about 3% of market value). Hirshleifer, Peng & Wang (2025) report t ≈ 14 using microcaps; the two results conflict mainly on microcap inclusion — [UCLA Anderson Review research brief](https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/).
- Net of costs, US: PEAD (SUE) 0.72%/month gross, 35.07% one-sided monthly turnover, 0.26% net (t 1.60); PEAD (3-day CAR) 0.91% gross, 0.34% net (t 2.41) — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- **Emerging vs developed.** Across 56 markets, short-term reversal, post-earnings drift and momentum earn similar returns in emerging and developed markets — [Griffin, Kelly & Nardari 2010, RFS (RePEc)](https://ideas.repec.org/a/oup/rfinst/v23y2010i8p3225-3277.html).
- **Announcement premium.** Buying expected announcers and shorting non-announcers earned 61 bp/month (t 5.30), US 1973-2004 (52 bp over 1927-2004); 153 bp/month (t 6.0) among stocks with high past announcement-volume concentration; frequent trading needed and costs not quantified — [Frazzini & Lamont, NBER w13090 PDF](https://www.nber.org/system/files/working_papers/w13090/w13090.pdf). Of 20 countries with enough data, nine show a significant announcement-month premium, linked to uncertainty about the news — [Barber, De George, Lehavy & Trueman 2013, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v108y2013i1p118-138.html).
- **Analysts.** Buying the most favourably and shorting the least favourably rated stocks earned over 4%/yr in abnormal gross returns with daily rebalancing, but net returns were not reliably above zero — [Barber, Lehavy, McNichols & Trueman 2001, JF (RePEc)](https://ideas.repec.org/a/bla/jfinan/v56y2001i2p531-563.html). Forecast revisions (REV6) t = 4.07 in regressions, 1977-1992; EPS-revision long-only CAPM alpha t = 3.17 (1975-1980); changes in consensus recommendations 0.225%/month (1985-1998; OSAP notes IBES recommendations start in 1993) — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).

### Inferences
- US: DROP the earnings-drift family (prior weight 2 → 0). The large-stock drift is gone, and at QUANTGEN's 50 bp per side the expected net Sharpe after haircuts is negative (§8: about −0.5).
- Korea: the prior map's "earnings-announcement drift: strong (3)" has no Korean source in this note. Griffin-Kelly-Nardari suggests emerging markets are not systematically slower, and Chordia et al. show the drift sits where costs are highest. Downgrade to 1 and test with DART timestamps (data-check DC-3). The first Korean version must use the 3-day announcement return (CAR3) because QUANTGEN has no PIT consensus forecasts.
- The announcement premium (long into scheduled announcements) is a BACKLOG idea for the US, where announcement calendars are known. In Korea, preliminary-results (잠정실적) timing is irregular, which makes "expected announcers" hard to define ex ante. Unverified.
- Analyst-based signals: DROP for now (no PIT analyst data among QUANTGEN's sources; net returns not reliable).

### Gaps
- Savor & Wilson (2016) magnitudes were not accessible (RePEc has no abstract; Wiley 403).
- Bernard-Thomas magnitudes and the Ball-Brown results are cited bibliographically only.
- No Korean PEAD or announcement-premium study could be opened.

## 5. Investment and financing: asset growth, issuance, buybacks, distress (with a local Korean issuance test)

### Takeaway
Investment (asset growth) and net share issuance are robust worldwide and low-turnover enough to survive costs in composites. Buyback drift died in the US for 2003-2012 events, and the distress anomaly is real but too costly to harvest as a long-short. My local Korean test supports **net issuance** as the first Korean fundamental card: strong in 1996-2026, surviving 35 bp per side, but clearly decaying and concentrated in smaller and KOSDAQ names.

### Cited Findings
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

### Inferences
- Issuance is the Korean signal with the best evidence-to-data ratio. It needs only daily listed shares, which are PIT by construction because KRX publishes them daily, so it can be backtested on 30 years of survivorship-free data without OpenDART. The effect is economically large in EW and in KOSDAQ, weaker in VW and large caps, and decaying; the recent-decade CI includes zero at 35 bp.
- QUANTGEN translation: a **long-only "avoid heavy issuers" tilt/exclusion** (card KR-ISS). This fits a read-only individual-investor desk better than a short leg. Shorting heavy issuers (often distressed KOSDAQ names issuing convertible bonds) is impractical for retail investors and is where delisting and borrow problems concentrate.
- Caveats on the local test: (a) rights offerings with ex-rights price adjustment (권리락) are partly treated as splits or excluded by the event filter, so issuance is *understated*. The signal mostly captures CB/BW conversions, third-party allotments, stock options and mergers. (b) Delisting returns may be incomplete if 정리매매 prices are missing. (c) About 10 variants were examined, so a deflated Sharpe must count them. (d) Not walk-forward.
- Buyback/cancellation (BL-O04 in the macro backlog): the local result is regime-specific. It was weak for 1996-2023 and strong in 2024-26, which coincides with Value-Up (Feb-2024) and the 2025 Commercial Act revisions (KEIA). Keep it in BACKLOG as a regime-flagged candidate; 32 months is not enough.
- Asset growth and investment belong in the US composite (CMA-like, low turnover), not as standalone cards. Distress (failure probability, O-score) belongs in long-book exclusion screens, not as a return card.

### Gaps
- The Cooper-Gulen-Schill magnitudes come from OSAP's replication notes, not the paper's tables. Titman-Wei-Xie's abstract was not fetched.
- The local Korean test has not been reproduced by the data lab and does not yet use DART-based issuance events (rights offerings, CB conversions) to classify issuance types.
- Korean distress models (O-score/CHS on OpenDART) are untested.

## 6. Market-level valuation: CAPE, dividend yield, the Fed model, implied ERP, Graham-Dodd

### Takeaway
Smoothed valuation ratios explain about 30-40% of 10-year US returns in-sample and were directionally right after 2000. But equity-premium predictors, valuation ratios included, mostly fail out of sample, and value-based market timing has not beaten buy-and-hold over 1900-2015. On 1 Oct 2026 CAPE is about 41, near its 1999 peak, yet the S&P 500 rose about 70% in the 36 months after CAPE first crossed 30 in Sep-2023. The Fed model is theoretically flawed and has no long-horizon forecasting power. QUANTGEN should display valuation as context and never use it as a multiplier.

### Cited Findings
- Graham and Dodd (1934) advised averaging earnings over at least five years, preferably seven or ten; Campbell and Shiller use a 10-year average. Over 1872-2000 the smoothed P/E explains 30% of 10-year real price growth and 40% of 10-year real returns (the dividend-price ratio 9% and 16%). From Jan-2000 valuations they projected a log real price fall of 0.6 over ten years (about −55% real), while warning that extrapolating far outside history could be excessively bearish — [Campbell & Shiller 2001, NBER w8221 PDF](https://www.nber.org/system/files/working_papers/w8221/w8221.pdf).
- Equity-premium prediction models have predicted poorly both in-sample and out-of-sample for 30 years and would not have helped a real-time investor — [Welch & Goyal 2008, RFS (RePEc)](https://ideas.repec.org/a/oup/rfinst/v21y2008i4p1455-1508.html). In the 2024 update (29 post-2008 variables plus the original 17, data through 2021), more than one third of the new variables lose in-sample significance and half of the rest perform poorly out of sample — [Goyal, Welch & Zafirov 2024, RFS (SFI summary)](https://www.sfi.ch/en/publications/a-comprehensive-2022-look-at-the-empirical-performance-of-equity-premium-prediction); [OUP](https://academic.oup.com/rfs/article/37/11/3490/7749383).
- With sign restrictions (non-negative forecasts, theory-signed slopes), OOS R² over 1927-2003 is 0.54% monthly and 6.64% annual for smoothed E/P. Monthly E/P is worth about 3%/yr to a mean-variance investor with risk aversion 1 and about 1%/yr with risk aversion 3 — [Campbell & Thompson, NBER w11468 PDF](https://www.nber.org/system/files/working_papers/w11468/w11468.pdf).
- Value-based (CAPE-type) market timing: Sharpe 0.37 vs buy-and-hold 0.38 over 1900-2015, and 0.37 vs 0.37 over 1958-2015. The timing strategy averaged 89% invested, forgoing about 0.6%/yr of equity premium. Adding momentum lifts the Sharpe to 0.43 vs 0.38 (1900-2015) and 0.41 vs 0.37 (1958-2015). Recommendation: small tilts only — [Asness, Ilmanen & Maloney 2017, "Market Timing: Sin a Little" (AQR PDF)](https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Market-Timing-Sin-a-Little.pdf).
- The Fed model compares the market's (real) earnings yield to a nominal bond yield, a money-illusion error, and has no power to forecast long-term real stock returns, whereas the plain P/E has been effective — [Asness 2003, "Fight the Fed Model" (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/Fight-the-Fed-Model).
- Current CAPE: 41.07 on 1 Oct 2026; historical mean 17.42, median 16.13, maximum 44.19 (Dec-1999) — [multpl.com](https://www.multpl.com/shiller-pe) (T3 aggregator; Shiller's own page was blocked).
- Implied equity risk premium (Damodaran, NYU Stern): 4.14% on 1 Sep 2026 with a 4.75% T-bond rate (range 3.56-6.05% across his variants) — [Damodaran home page](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm). Year-end values: 1999 2.05% (T-bond 6.44%); 2008 6.43%; 2021 4.24%; 2022 5.94%; 2023 4.60%; 2024 4.33%; 2025 4.23% (S&P 500 6,845.50, T-bond 4.18%) — [Damodaran histimpl](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html). His Sep-2026 post notes analysts raised S&P 500 earnings estimates by more than 11% for both 2026 and 2027 — [Damodaran blog, 10 Sep 2026](https://aswathdamodaran.blogspot.com/) (T2).
- **Local test (Shiller monthly file; the local copy's PE10 ends 2023-09 and dividends/CPI end 2023-06).**
  - In-sample, 10-year forward real total return on log CAPE, 1881-2013 (n = 1,590 overlapping months): slope −0.066, R² 0.29 (0.33 in both 1881-1949 and 1950-2013).
  - The fitted 10-year real return is +1.7%/yr at CAPE 30.8 and −0.3%/yr at CAPE 41.1.
  - **Out-of-sample, 1-year horizon.** Expanding-window OLS using only fully realised targets; OOS R² vs the historical mean, with the Campbell-Thompson non-negativity restriction in brackets:

| OOS period | OOS R² (CT-restricted) |
|---|---|
| 1926-2022 | +2.9% (+4.1%) |
| 1950-2022 | −4.7% (−2.4%) |
| 1990-2022 | −16.3% (−11.1%) |
| 2000-2022 | +7.1% (+4.5%) |
| 2010-2022 | −38.6% (−39.1%) |

  - **CAPE buckets (forward 10-year real annual return).** CAPE < 10: +11.3% (227 months). 15-20: +6.0%. 20-25: +4.3%. 25-30: +4.4% (83 months). Above 30: −1.0% (57 months, essentially 1929 and 1997-2002).
  - **Episodes (S&P 500 price change over the next 36 months).**
    - Dec-1999 (CAPE 44.2): −37.1%. Aug-2000 (42.9): −33.4%.
    - Jan-2018 (33.3): +36.0%. Dec-2021 (38.3): +28.6%. Sep-2023 (30.8): +69.8%.
  - Jan-2000 to Jan-2010: the real price fell 38.6% and the real total return was −3.0%/yr, so the Campbell-Shiller warning was directionally right but too large.

### Inferences
- CAPE and implied ERP belong on a **context panel** (a 10-year expected-return band). They should not be a multiplier, consistent with the macro rule that macro variables size risk only within [0.5, 1.0] and must clear an OOS-R² gate. At the 1-month to 1-year horizons on which QUANTGEN rebalances, the local OOS R² is negative in every post-1950 window except 2000-2022.
- The two valuation gauges disagree in Oct-2026: CAPE about 41 (near the record) vs implied ERP 4.1% (mid-range, well above 1999's 2.05%). The gap is driven by expected earnings growth; QUANTGEN should display both, with the disagreement, rather than a single "expensive" flag.
- DROP the Fed model (theory and evidence both against it).
- Korea: the market-level analogue (KOSPI P/B around 1, a structural "discount" now being re-rated by policy) is context for Korean value cards. It is not a KOSPI timing signal, and no Korean CAPE test was run.

### Gaps
- Shiller's site was blocked; the latest CAPE (41.07) is from a T3 aggregator, and the local Shiller file needs refreshing beyond 2023-09.
- GWZ's specific out-of-sample statistics for dividend yield, E/P and CAPE were not extracted (abstract-level only).
- No Korean market-level valuation predictability study was opened.

## 7. Point-in-time data: reporting lags, restatements, survivorship; US (EDGAR/FMP) and Korea (DART/OpenDART)

### Takeaway
Fundamental backtests fail most often through look-ahead, not through bad signals. The US has statutory deadlines of 60/75/90 days (10-K) and 40/45 days (10-Q), plus EDGAR timestamps (`acceptanceDateTime`) and XBRL "filed" dates from 2009-2011 onward, which allow a true first-reported dataset. Korea has 90/45-day deadlines and DART receipt numbers. OpenDART statements start only in 2015, receipt dates carry no time of day, and values can change after corrections, so QUANTGEN must snapshot first-filed versions itself.

### Cited Findings
- **Fama-French convention.** Portfolios are formed at the end of June of year t using accounting data for fiscal years ending in calendar t−1 (an effective lag of 6-18 months); market equity is taken from Dec t−1 and Jun t. The five-factor file covers Jul-1963 to Aug-2026 monthly — [French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html). The local data-lab copy of French factors ends in 2018 (QUANTGEN context brief).
- **US deadlines.** 10-K: 60 days after fiscal year-end (large accelerated filers), 75 (accelerated), 90 (others) — [SEC Form 10-K instructions](https://www.sec.gov/files/form10-k.pdf). 10-Q: 40 days (large accelerated and accelerated), 45 (others); no Q4 10-Q — [SEC Form 10-Q instructions](https://www.sec.gov/files/form10-q.pdf).
- **XBRL phase-in.** Large accelerated filers with float above $5bn from periods ending on or after 15 Jun 2009; other large accelerated filers from 2010; all remaining filers (incl. smaller companies and IFRS foreign private issuers) from 2011; detailed footnote tagging after one year — [SEC Release 33-9002](https://www.sec.gov/rules/final/2009/33-9002.pdf).
- **EDGAR APIs.** The submissions JSON and XBRL APIs (companyconcept, companyfacts, frames) update in near real time (under a second for submissions, under a minute for XBRL) — [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). Submissions records include `accessionNumber`, `filingDate`, `reportDate` and `acceptanceDateTime` (e.g., Apple's FY2024 10-K accepted 2024-11-01T10:49:43Z) — [data.sec.gov submissions example](https://data.sec.gov/submissions/CIK0000320193.json). XBRL facts carry `end`, `val`, `accn`, `fy`, `fp`, `form`, `filed` and `frame`, and the same period value reappears in later filings with later `filed` dates — [companyconcept example](https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/AccountsPayableCurrent.json).
- **FMP.** FMP offers an "As Reported Financial Statements" API; field names, filing-date fields and restatement policy could not be verified (docs excerpt incomplete; demo endpoint returned 401) — [FMP docs](https://site.financialmodelingprep.com/developer/docs/stable/income-statement).
- **Korea deadlines (2026 table, December fiscal year).** 2025 business report due 03/31; 2026 Q1 report 05/15; half-year report 08/14; Q3 report 11/16. Consolidated interim reports get 15 extra days in a company's first two fiscal years (06/01, 08/31, 11/30). Non-K-IFRS firms with assets under ₩2tn get 30 extra days for consolidated statements — [DART periodic-disclosure schedule](https://dart.fss.or.kr/info/main.do?menu=410). DART has operated since April 1999 — [English DART](https://englishdart.fss.or.kr/).
- **OpenDART.**
  - Disclosure list API: returns `rcept_dt` (YYYYMMDD, no time of day) and a 14-digit `rcept_no`.
  - The `rm` codes flag KOSPI (유) and KOSDAQ (코) listing, consolidated statements (연), an amendment existing (정) and withdrawal (철). `report_nm` carries tags such as [기재정정] (content correction).
  - Disclosure types A (periodic: A001 business, A002 half-year, A003 quarterly), B (major matters), C (issuance), D (ownership) and I (exchange: I001 timely disclosure, I002 fair disclosure) — [OpenDART list API](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001).
- The full financial-statement API (`fnlttSinglAcntAll`) takes `corp_code`, `bsns_year` (2015 onward), `reprt_code` (11013 Q1, 11012 half-year, 11014 Q3, 11011 annual) and `fs_div` (CFS consolidated / OFS separate). Exceeding roughly 20,000 requests triggers error −020 — [OpenDART fnlttSinglAcntAll](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020). The same API group offers original XBRL files and taxonomy templates, and warns that values can change if the filer later corrects the statements — [OpenDART DS003 group](https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS003).
- KRX daily per-stock BPS, PER, PBR, EPS, DIV and DPS are retrievable through the open-source `pykrx` wrapper (`get_market_fundamental`) — [pykrx README](https://raw.githubusercontent.com/sharebook-kr/pykrx/master/README.md) (T3; how KRX updates BPS after filings is undocumented there).
- **Survivorship.** QUANTGEN's `marcap` KRX file is survivorship-free per the context brief and contains KOSPI, KOSDAQ and KONEX through 2026-09-29 (Local inspection). OSAP's replication notes show how far data-lag choices move published results (e.g., F-score rebalanced four months after fiscal year-end; issuance measured with a 6-month skip) — [OSAP SignalDoc](https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv).

### Inferences
**PIT rules P3 recommends writing into the code (BUILD, invariant):**
1. Every fundamental value carries `(period_end, filed_ts, source_id)`. US: `acceptanceDateTime`; if it is at or after 16:00 ET, the value becomes usable at the close of the next session. Korea: `rcept_dt`, usable from the close of the *next* KRX session, because OpenDART has no time of day and filings can arrive after the close.
2. Store the **first-filed** value; keep amendments (Korea `rm` = 정 / [기재정정]; US later `accn`) as new versions with their own timestamps; never overwrite.
3. Use the timely market cap (today's price) against the latest *filed* book (Asness-Frazzini).
4. Fallback lags when a timestamp is missing: annual +4 months, quarterly +2 months (US); annual 90 days, quarterly 45 days (+15 for first-time consolidated filers) (Korea).
5. Consolidated (CFS) first, separate (OFS) as fallback, flagged.
6. Universes must include delisted names (marcap for Korea; for the US, verify FMP delisted coverage or derive the universe from EDGAR filers).

**History constraint.** Korean statement-based cards have about 11 years of OpenDART history (2015-2026) unless older filings are parsed or KRX BPS is shown to be PIT. Across 11 years the standard error of an annual Sharpe is about 0.30, so a true 0.3-0.4 signal will often come back **INSUFFICIENT DATA or REVISE**, not PASS. US XBRL history (2009/2011 to 2026) gives about 15-17 years.

**Point-in-time inputs by signal:**

| Signal | Items needed (PIT) | Korea source | US source |
|---|---|---|---|
| Value (B/M, E/P, CF/P) | book equity, net income, D&A, OCF; R&D for intangibles | OpenDART fnlttSinglAcntAll (2015+); KRX BPS (pre-2015; PIT unverified) | EDGAR XBRL companyfacts (2009/11+) |
| Profitability (GP/A, OP/BE) | revenue, COGS, SG&A, interest, assets, equity | OpenDART (COGS may be missing for nature-of-expense filers; verify) | EDGAR XBRL |
| F-score | NI, OCF, ROA change, leverage change, current ratio, shares issued, margin, turnover | OpenDART | EDGAR XBRL |
| Accruals / M-score | working-capital items, receivables, depreciation | OpenDART | EDGAR XBRL |
| Asset growth / investment | total assets, capex | OpenDART | EDGAR XBRL |
| Net issuance | listed or outstanding shares (split-adjusted) | KRX daily listed shares (marcap), PIT by construction | EDGAR dei shares or FMP share counts (verify) |
| PEAD / CAR3 | announcement timestamp, returns | DART list (I002 fair disclosure, I001) `rcept_dt` | EDGAR 8-K Item 2.02 `acceptanceDateTime` |
| Distress (O-score, CHS) | liabilities, NI history, cash, market cap, volatility | OpenDART + KRX | EDGAR + prices |

### Gaps
- The statutory text of Korea's FSCMA Arts. 159-160 could not be fetched; deadlines come from DART's own 2026 schedule.
- K-IFRS mandatory adoption year and early-adoption details were not verified (the IFRS jurisdiction profile omitted them).
- FMP's field definitions, history depth and delisted coverage are unverified.
- DART filing time-of-day (and whether evening filings are common) is unknown from the API.
- The exact report names for Korean preliminary results (e.g., "영업(잠정)실적(공정공시)", "매출액또는손익구조30%(대규모법인15%)이상변경") are from practice and must be verified against `list.json` output.

## 8. QUANTGEN translation: which fundamental cards, rebalancing, combination with momentum, expected net Sharpe

### Takeaway
Build two fundamental cards now: **KR-ISS** (Korean net-issuance long-only tilt, buildable today from KRX data) and **US-VQ** (a value + profitability + investment + issuance composite on EDGAR PIT data), both rebalanced monthly with buy/hold bands. Put the Korean value-quality composite, Korean PEAD and the buyback/cancellation signal in BACKLOG behind a PIT store. Drop US PEAD, analyst signals, standalone F-score, distress long-shorts and every market-valuation timing rule. Realistic net Sharpe after decay haircuts and QUANTGEN costs is about 0.15-0.4 for the survivors, and roughly 0.1-0.2 after the gate's 60% live haircut.

### Cited Findings
- The average anomaly's expected return is about 8 bp/month after spreads, post-publication decay and modern trading technology; the best are 10-20 bp after data-mining adjustments — [Chen & Velikov (SSRN 3073681)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681). Anomaly returns roughly halved after decimalisation — [Chordia, Subrahmanyam & Tong 2014, JAE (RePEc)](https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html). With NYSE breakpoints and VW returns, 64% of 447 anomalies are insignificant at 5% (85% at t ≥ 3) — [Hou, Xue & Zhang, NBER w23394](https://www.nber.org/papers/w23394). Most accounting anomalies look spurious in pre-1963 data — [Linnainmaa & Roberts (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2897719).
- Counter-evidence: most factors replicate, cluster into 13 themes and work out of sample in 93 countries — [Jensen, Kelly & Pedersen, NBER w28432](https://www.nber.org/papers/w28432); [JKP data, through Dec-2025](https://jkpfactors.com/). Reliable post-publication decline across 241 anomalies in 39 markets appears only in the US — [Jacobs & Müller 2020, JFE (RePEc)](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html).
- Factor timing: timing strategies lose their profitability once proper data lags and transaction costs are applied — [Ilmanen, Israel, Lee, Moskowitz & Thapar 2021 (AQR)](https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence).
- **Value + momentum.** Global individual stocks (US, UK, Europe, Japan; 1972/74-2011): Sharpe 0.51 (value), 0.59 (momentum), 1.28 (50/50). All asset classes: 0.72, 0.74, 1.59. Within-asset-class value-momentum correlation about −0.49 to −0.60 (IS). Book-to-market uses 6-month-lagged book and current price — [Asness, Moskowitz & Pedersen 2013, JF](https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf). Net of costs, US 1963-2012: ValMom 0.93% gross, 0.51% net (t 2.67); ValMomProf 1.43% gross, 0.99% net (t 5.18), one-sided turnover about 27-29%/month — [Novy-Marx & Velikov PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf).
- QUANTGEN's own context: US 12-1 momentum Sharpe 0.02 since 2008 (French WML); French value-momentum correlation −0.17 vs AMP's −0.65 over the same window; Korean 12-1 momentum negative (QUANTGEN context brief; QUANTGEN_MACRO_INTEGRATION.md §2.2).
- Costs: below 50% one-sided monthly turnover most anomalies keep significant net spreads; a buy/hold spread is the most effective simple mitigation — [Novy-Marx & Velikov, NBER w20721](https://www.nber.org/papers/w20721).

### Inferences
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

### Gaps
- The expected-Sharpe table applies published US 1963-2012 gross figures and assumed haircuts; none of these numbers has gone through QUANTGEN's gate.
- Korean costs for small KOSDAQ names (spreads above 35 bp per side) are not modelled; the 2× stress (70 bp) is the only proxy.
- Whether long-only tilts keep about 60% of each anomaly (Israel-Moskowitz show this for value, not for issuance or profitability) is untested.

## 9. Where and when it failed (dated episodes)

### Takeaway
Every fundamental signal in this note has a documented failure. The failure modes are valuation compression (value), arbitrage and learning after publication (accruals, PEAD, buybacks), mis-measurement (book value without intangibles), construction dispersion (value indices in 2025), costs (PEAD, distress, analyst strategies), long-only versus long-short gaps (quality in 2022), and policy or regime shifts (Korea 2024-26).

### Cited Findings
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

### Inferences
- For QUANTGEN's gate, step 8 (≥ 60% positive calendar years) will bind for fundamental cards: the Korean issuance long-only active result net of 35 bp had 68% positive years over 1996-2026 but only 60% in 2017-2026.
- Value's failures cluster in growth manias (1999, 2020, 2023-24), when the valuation spread widens. A value card's drawdown should be reported alongside the valuation spread, but the spread must not be used to time it (Ilmanen et al.).
- Signals with published, easily computed definitions (accruals, PEAD, F-score, buybacks) decayed fastest in the US. Korea may lag (Jacobs-Müller), but the local issuance decay shows Korea is not immune.

### Gaps
- No Korean value, quality or PEAD failure episodes can be dated here (no Korean data or studies opened).
- French long-short factor drawdowns for 2021-2026 are not measured.

## 10. Data-check requests, claims ledger and sources

### Takeaway
Eight data-lab tests would settle the claims P3 could not verify, and the 30-claim ledger below states each claim's evidence, robustness and QUANTGEN implication. The most decision-relevant tests are DC-1 (Korean issuance through the full gate), DC-3 (Korean PEAD on DART timestamps) and DC-2 (whether KRX BPS is point-in-time, which would unlock pre-2015 Korean value).

### Cited Findings
#### Claims ledger

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

### Inferences
#### Data-check requests (exact tests for the data lab)
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

### Gaps
- Claims P3-C20/C21 (local) and the expected-Sharpe computations (P3-C24) await data-lab reproduction.
- Korean-specific academic evidence for value, quality, accruals and PEAD is missing from this ledger.
- FMP fields, KRX BPS timing and DART filing time-of-day remain unverified.

### Source list
**Value:**
- Fama & French 1992 — https://ideas.repec.org/a/bla/jfinan/v47y1992i2p427-65.html
- Lakonishok, Shleifer & Vishny (NBER w4360) — https://www.nber.org/system/files/working_papers/w4360/w4360.pdf
- Fama & French "The Value Premium" — https://ebicapital.nl/wp-content/uploads/2022/05/The-Value-Premium.pdf ; https://academic.oup.com/raps/article-abstract/11/1/105/6033665 ; https://www.chicagobooth.edu/review/value-stock-premium-shrinking
- Fama & French 2012 — https://ideas.repec.org/a/eee/jfinec/v105y2012i3p457-472.html
- Arnott, Harvey, Kalesnik & Linnainmaa 2021 — https://people.duke.edu/~charvey/Research/Published_Papers/P149_Reports_of_values.pdf
- Israel, Laursen & Richardson 2021 — https://www.aqr.com/Insights/Research/Journal-Article/Is-Systematic-Value-Investing-Dead
- Eisfeldt, Kim & Papanikolaou — https://www.nber.org/papers/w28056 ; https://www.nber.org/system/files/working_papers/w28056/w28056.pdf
- Lev & Srivastava — https://cfr.ivo-welch.org/forthcoming/papers/lev2021explaining.pdf
- Asness & Frazzini — https://www.aqr.com/Insights/Research/Journal-Article/The-Devil-in-HMLs-Details
- Asness 2021 — https://www.aqr.com/Insights/Perspectives/The-Long-Run-Is-Lying-to-You
- Israel & Moskowitz 2013 — https://www.aqr.com/Insights/Research/Journal-Article/The-Role-of-Shorting-Firm-Size-and-Time-on-Market-Anomalies
- Cakici, Fabozzi & Tan 2013 — https://ideas.repec.org/a/eee/ememar/v16y2013icp46-65.html
- Hou, Karolyi & Kho 2011 — https://ideas.repec.org/a/oup/rfinst/v24y2011i8p2527-2574.html

**Quality:**
- Novy-Marx 2013 — https://oldschoolvalue-files.s3.amazonaws.com/pdf/Novy-Marx_Gross-Profitability-Anomaly_JFE_2013.pdf
- Asness, Frazzini & Pedersen 2019 — https://link.springer.com/article/10.1007/s11142-018-9470-2
- Frazzini, Kabiller & Pedersen — https://www.nber.org/papers/w19681 ; https://www.aqr.com/Insights/Research/Journal-Article/Buffetts-Alpha
- Fama & French 2015 — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2287202
- Fama & French 2017 — https://ideas.repec.org/a/eee/jfinec/v123y2017i3p441-463.html
- Walkshäusl 2020 — https://d-nb.info/121155211X/34
- Hanauer & Lauterbach 2019 — https://ideas.repec.org/a/eee/ememar/v38y2019icp265-286.html
- OSAP SignalDoc — https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv ; https://www.openassetpricing.com/

**Accruals:**
- Sloan 1996 — https://www.cuhk.edu.hk/acy2/workshop/June2009Wasley/1996TAR%29.pdf
- Green, Hand & Soliman — https://pure.psu.edu/en/publications/going-going-gone-the-apparent-demise-of-the-accruals-anomaly/
- Beneish, Lee & Nichols — https://ideas.repec.org/a/taf/ufajxx/v69y2013i2p57-82.html
- Dechow et al. 2011 — https://ideas.repec.org/a/wly/coacre/v28y2011i1p17-82.html
- Richardson, Tuna & Wysocki — https://ideas.repec.org/a/eee/jaecon/v50y2010i2-3p410-454.html

**Earnings news:**
- Ball & Brown — https://ideas.repec.org/a/bla/joares/v6y1968i2p159-178.html
- Bernard & Thomas — https://ideas.repec.org/a/bla/joares/v27y1989ip1-36.html ; https://ideas.repec.org/a/eee/jaecon/v13y1990i4p305-340.html
- Chordia et al. 2009 — https://ideas.repec.org/a/taf/ufajxx/v65y2009i4p18-32.html
- Martineau — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3111607 ; https://www.readkong.com/page/rest-in-peace-post-earnings-announcement-drift-critical-7777848
- Kettell, McInnis & Zhao — https://business.columbia.edu/sites/default/files-efs/imce-uploads/CEASA/Events%20Page/PEAD_Declined_over_time.pdf
- UCLA Anderson Review — https://anderson-review.ucla.edu/is-post-earnings-announcement-drift-a-thing-again/
- Frazzini & Lamont — https://www.nber.org/system/files/working_papers/w13090/w13090.pdf
- Barber et al. 2013 — https://ideas.repec.org/a/eee/jfinec/v108y2013i1p118-138.html
- Griffin, Kelly & Nardari — https://ideas.repec.org/a/oup/rfinst/v23y2010i8p3225-3277.html
- Barber et al. 2001 — https://ideas.repec.org/a/bla/jfinan/v56y2001i2p531-563.html

**Investment and financing:**
- Cooper, Gulen & Schill — https://ideas.repec.org/a/bla/jfinan/v63y2008i4p1609-1651.html
- Watanabe et al. — https://ideas.repec.org/a/eee/jfinec/v108y2013i2p529-563.html
- Pontiff & Woodgate — https://ideas.repec.org/a/bla/jfinan/v63y2008i2p921-945.html
- McLean, Pontiff & Watanabe — https://ideas.repec.org/a/eee/jfinec/v94y2009i1p1-17.html
- Ikenberry, Lakonishok & Vermaelen — https://ideas.repec.org/a/eee/jfinec/v39y1995i2-3p181-208.html
- Fu & Huang — https://ideas.repec.org/a/inm/ormnsc/v62y2016i4p964-984.html
- Campbell, Hilscher & Szilagyi — https://www.nber.org/papers/w12362

**Decay and costs:**
- McLean & Pontiff — https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf ; https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365
- Hou, Xue & Zhang — https://www.nber.org/papers/w23394
- Jensen, Kelly & Pedersen — https://www.nber.org/papers/w28432 ; https://jkpfactors.com/
- Jacobs & Müller — https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html
- Chen & Velikov — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681
- Chordia, Subrahmanyam & Tong — https://ideas.repec.org/a/eee/jaecon/v58y2014i1p41-58.html
- Linnainmaa & Roberts — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2897719
- Novy-Marx & Velikov — https://www.nber.org/papers/w20721 ; https://www.nber.org/system/files/working_papers/w20721/w20721.pdf
- Ilmanen et al. — https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence
- Asness, Moskowitz & Pedersen — https://w4.stern.nyu.edu/facdir/lpederse/papers/ValMomEverywhere.pdf

**Market valuation:**
- Campbell & Shiller 2001 — https://www.nber.org/system/files/working_papers/w8221/w8221.pdf
- Welch & Goyal 2008 — https://ideas.repec.org/a/oup/rfinst/v21y2008i4p1455-1508.html
- Goyal, Welch & Zafirov 2024 — https://www.sfi.ch/en/publications/a-comprehensive-2022-look-at-the-empirical-performance-of-equity-premium-prediction ; https://academic.oup.com/rfs/article/37/11/3490/7749383
- Campbell & Thompson — https://www.nber.org/system/files/working_papers/w11468/w11468.pdf
- Asness 2003 — https://www.aqr.com/Insights/Research/Journal-Article/Fight-the-Fed-Model
- Asness, Ilmanen & Maloney 2017 — https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Market-Timing-Sin-a-Little.pdf
- multpl (T3) — https://www.multpl.com/shiller-pe
- Damodaran — https://pages.stern.nyu.edu/~adamodar/New_Home_Page/home.htm ; https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html ; https://aswathdamodaran.blogspot.com/

**Style ETFs (T2):**
- IWD — https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf
- IWF — https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf
- VLUE — https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf
- QUAL — https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf
- IWB — https://www.ishares.com/us/products/239707/ishares-russell-1000-etf

**PIT data and regulation:**
- French Data Library — https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html
- SEC 10-K — https://www.sec.gov/files/form10-k.pdf
- SEC 10-Q — https://www.sec.gov/files/form10-q.pdf
- SEC XBRL rule — https://www.sec.gov/rules/final/2009/33-9002.pdf
- EDGAR APIs — https://www.sec.gov/search-filings/edgar-application-programming-interfaces ; https://data.sec.gov/submissions/CIK0000320193.json ; https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/AccountsPayableCurrent.json
- FMP docs — https://site.financialmodelingprep.com/developer/docs/stable/income-statement
- DART schedule — https://dart.fss.or.kr/info/main.do?menu=410
- OpenDART — https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001 ; https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019020 ; https://opendart.fss.or.kr/guide/main.do?apiGrpCd=DS003
- English DART — https://englishdart.fss.or.kr/
- pykrx (T3) — https://raw.githubusercontent.com/sharebook-kr/pykrx/master/README.md

**Korea context:**
- KEIA (T2) — https://keia.org/analysis/explaining-south-koreas-stock-market-boom/

**Internal:**
- QUANTGEN context brief — /home/claude/research_notes/QUANTGEN technical and fundamental signals/00_QUANTGEN_context.md
- QUANTGEN project docs — claude/QUANTGEN_MACRO_INTEGRATION.md, claude/QUANTGEN_MACRO_BACKLOG.md
- Local data — /home/claude/data_raw/marcap/data/marcap-*.parquet, /home/claude/data_raw/us/shiller_sp500_monthly.csv
