# P4: Backtest econometrics, multiple testing, decay and costs. How much published technical and fundamental edge survives, and the testing protocol every QUANTGEN technical/fundamental card must follow

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

---

## Q1. Data snooping and multiple testing: how much survives the corrections?

### Takeaway
Once the number of strategies tried is honestly counted, the significance bar rises from t of about 2 to about 3.0 for a new factor (Harvey-Liu-Zhu) and to 3.4-3.8 for randomly searched strategies (Chordia-Goyal-Saretto). Under such corrections, essentially none of a 7,846-rule technical universe beats buy-and-hold on the DJIA after 1962. The tools QUANTGEN needs exist and complement each other:
- Reality Check, SPA and StepM for family-wise control;
- FDR for diversified rule baskets;
- DSR for selection bias and non-normality;
- PBO/CSCV for in-family selection overfitting;
- CPCV as a better out-of-sample protocol than a single walk-forward path.

### Cited Findings
**Family-wise frameworks**
- White's Reality Check tests the null that the best model found in a specification search has no predictive superiority over a benchmark, with the search itself taken into account. White treats data snooping as practically unavoidable when only one historical time series exists. — [Econometric Society, White (2000) Econometrica 68(5)](https://www.econometricsociety.org/publications/econometrica/2000/09/01/reality-check-data-snooping)
- Hansen's SPA test keeps the same null ("no model is better than the benchmark"). It reports lower, consistent and upper p-values from different re-centerings, and the documentation recommends the consistent one. Romano-Wolf StepM shares the null but **identifies the set** of models that beat the benchmark. — [arch library documentation (multiple comparisons)](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison_examples.html)
- StepM asymptotically controls the family-wise error rate, is more powerful than single-step methods (it rejects more false hypotheses), and the authors recommend studentization because it captures the dependence among test statistics. — [IDEAS, Romano-Wolf (2005) Econometrica 73(4)](https://ideas.repec.org/a/ecm/emetrp/v73y2005i4p1237-1282.html)
- The false discovery rate selects more outperforming rules than FWER methods, which lets an investor diversify across rules against model uncertainty. — [EconPapers, Bajgrowicz-Scaillet (2012) JFE 106(3)](https://econpapers.repec.org/RePEc:eee:jfinec:v:106:y:2012:i:3:p:473-491)

**Hurdles implied by the literature-wide search**
- Harvey-Liu-Zhu argue that a newly proposed factor should clear t > 3.0 rather than 2.0, and that most claimed findings are probably false given hundreds of papers and factors. Their framework allows for correlation among tests and for missing (unpublished) tests. — [NBER w20592; RFS 29(1):5-68, 2016](https://www.nber.org/papers/w20592)
- Chordia-Goyal-Saretto test more than 2 million strategies randomly generated from real data. The t-thresholds that control for multiple testing are 3.8 for time-series (alpha) regressions and 3.4 for cross-sectional (Fama-MacBeth) regressions. Without the correction, about 45% of rejections would be false discoveries. — [IDEAS, RFS 33(5):2134-2179, 2020](https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2134-2179..html)
- Harvey-Liu "Backtesting" (JPM 2015):
  - The industry rule of thumb of halving backtested Sharpe ratios is wrong, because haircuts are nonlinear: above 50% for SR < 0.4 and at most 25% for SR > 1.0.
  - With 50 tests, an E/P strategy (SR 0.43) loses about 50% while BAB (SR 0.78) loses 7.9%.
  - A single-test p of 0.05 becomes a multiple-test p of 0.401 with N = 10 tests, and with N = 200 an SR of 0.75 becomes 0.32.
  - With 300 tests and 10% volatility, BHY requires 0.90%/m (120 months), 0.616%/m (240) and 0.44%/m (480) of mean return, against 0.58, 0.365 and 0.26 for a single test.
  - The default test correlation is rho = 0.2. With 240 months, SR 1.0 and 316 earlier factors, the BHY haircut is about 50%: the rule of thumb holds there only by coincidence.
  - Source: [Duke-hosted PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF)
- Harvey's presidential address:
  - The minimum Bayes factor is MBF = exp(-t²/2), and the Bayesianized p is MBF x prior odds / (1 + MBF x prior odds). At the 5% threshold, MBF is about 0.147, and with 4:1 prior odds against the effect the null still has about a 37% chance of being true.
  - He recommends pre-registration, reporting every test run, multiple-testing controls, and Bayesianized p-values under more than one prior.
  - Source: [Duke-hosted PDF, JF 72(4), 2017](https://people.duke.edu/~charvey/Research/Published_Papers/P131_The_scientific_outlook.pdf).
  - *Note:* the tool summary of this PDF also mentioned t = 2.6 for this example. MBF 0.147 and 0.37 are consistent only with t of about 1.96 (P4 recomputation), so the consistent version is reported here.
- Novy-Marx: combining the best k of n candidate signals produces a bias almost as large as picking the single best of n^k signals. Critical t-values for such composites can be several times the standard level, and combinations of random signals can look highly significant. — [NBER w21329](https://www.nber.org/papers/w21329)

**Technical-rule universes**
- Sullivan-Timmermann-White apply the Reality Check to a universe expanded from Brock-Lakonishok-LeBaron's 26 rules, using 100 years of daily DJIA data. — [EconPapers, JF 54(5):1647-1691, 1999](https://econpapers.repec.org/article/blajfinan/v_3a54_3ay_3a1999_3ai_3a5_3ap_3a1647-1691.htm)
- Bajgrowicz-Scaillet, DJIA daily 1897-2011, 7,846 rules (filters, moving averages, support/resistance, channel breakouts, on-balance volume) — [EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:106:y:2012:i:3:p:473-491); [UNIGE full text](https://access.archive-ouverte.unige.ch/access/metadata/d1a36296-e8c4-423b-9ed9-9870cfc76d9c/download):
  - The FDR-estimated share of outperforming rules is about 20% in 1897-1914 and positive in 1915-1938 and 1939-1962. It is **zero in every subperiod after 1962, even with zero costs**.
  - One-way costs that remove all in-sample outperformance: 16 bp (1897-1914), 35 bp (1915-1938), 70 bp (1939-1962).
  - Persistence test (choose rules each month using the previous month's data, hold them for the next month): OOS performance is negative in most recent periods, so there is no "hot hands" effect.
  - In BS's account, STW's best rule was not significant after the snooping adjustment in 1915-1938.
- Hsu-Kuan use the Reality Check and SPA on simple rules and complex strategies. Significant profits appear only in "young" markets (NASDAQ Composite, Russell 2000), not in the DJIA or S&P 500. The best NASDAQ and Russell strategies beat buy-and-hold net of costs in most periods. — [IDEAS, J. Financial Econometrics 3(4), 2005](https://ideas.repec.org/a/oup/jfinec/v3y2005i4p606-628.html)
- Park-Irwin survey 95 "modern" studies: 56 positive, 20 negative and 19 mixed. Technical profits in speculative markets are found at least until the early 1990s, but most studies suffer from data snooping, ex post rule selection, or problems estimating risk and transaction costs. — [IDEAS, J. Economic Surveys 21(4), 2007](https://ideas.repec.org/a/bla/jecsur/v21y2007i4p786-826.html)
- A discrete-FDR study (more than 21,000 rules, 12 markets, 2004-2015) finds short-term value in advanced, emerging and frontier markets that varies with financial stress and market development, and stresses frequent rebalancing. The abstract does not discuss costs. — [arXiv 1811.06766](https://arxiv.org/abs/1811.06766)

**Overfitting diagnostics**
- Deflated Sharpe ratio (Bailey-López de Prado, JPM 40(5):94-107, 2014) — [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); [author PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf):
  - It corrects for selection bias under multiple testing and for non-normal returns, using the expected maximum Sharpe ratio across N trials (a formula with the Euler-Mascheroni constant).
  - With M correlated trials of average correlation rho, the effective number of trials is N = M / (1 + (M-1) rho).
  - In the paper's example (best SR 2.5, 1,250 daily observations), the finding is not a discovery at 95% (DSR of about 0.90); with only 46 trials, DSR would have been 0.9505.
  - *P4 check:* the formula reproduces DSR 0.900 at N = 100 and 0.9505 at N = 46 with annualized trial-SR variance 0.5, skew -3 and kurtosis 10. Tool summaries of the PDF gave inconsistent parameter sets (for example N = 88), so treat the parameter details as approximate.
- Probability of backtest overfitting (PBO) via CSCV (Bailey-Borwein-López de Prado-Zhu; J. Computational Finance per SSRN) — [SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253); [author PDF](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf):
  - PBO is the probability that the configuration chosen as best in-sample underperforms the median configuration out of sample.
  - The T x N performance matrix is split into S blocks and every C(S, S/2) recombination is evaluated; S = 16 is recommended. C(16,8) = 12,870; the summarized PDF text prints "12,780", which is probably a typo.
  - Other outputs: performance degradation, probability of loss and stochastic dominance.
  - The paper argues that hold-out testing is unreliable: researchers reuse held-out data, prior knowledge of the hold-out period shapes design, it is inadequate below about 1,000 observations, it wastes data, and it ignores the number of trials.
- Bailey-Borwein-López de Prado-Zhu, Notices of the AMS 61(5), 2014: high simulated performance is easy to reach after trying a small number of configurations, and that number is rarely reported. When returns have memory, overfitting leads to **negative** expected OOS returns, not zero. — [SSRN 2308659](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659)
- Arian-Norouzi-Seco simulate synthetic markets (Heston, Merton jump-diffusion, drift-burst, regime switching). Combinatorial purged cross-validation (CPCV) gives lower PBO and better DSR statistics than walk-forward, K-fold or purged K-fold; walk-forward shows notable weaknesses in preventing false discoveries. — [SSRN 4686376](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4686376); [ScienceDirect (Knowledge-Based Systems, 2024)](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110)

### Inferences
- **Noise calibration (own computation).** Expected best annualized SR among N zero-edge configurations with IID returns, using the DSR paper's expected-maximum formula divided by sqrt(T in years):

| N configs | T = 3 y | 5 y | 8 y | 21 y | 31 y |
|---|---|---|---|---|---|
| 10 | 0.91 | 0.70 | 0.56 | 0.34 | 0.28 |
| 27 | 1.17 | 0.91 | 0.72 | 0.44 | 0.36 |
| 45 | 1.29 | 1.00 | 0.79 | 0.49 | 0.40 |
| 100 | 1.46 | 1.13 | 0.89 | 0.55 | 0.45 |
| 1,000 | 1.88 | 1.46 | 1.15 | 0.71 | 0.58 |
| 10,000 | 2.23 | 1.73 | 1.36 | 0.84 | 0.69 |

  Trying 100 settings of a chart rule on 5 years of data gives an expected best SR of about 1.1 **from noise alone**. This is the arithmetic behind the many "SR above 1" retail strategies. (N = 45 with T = 5 gives about 1.0, matching the often-quoted minimum-backtest-length statement, which P4 could not open: AMS PDF returned 403.)
- **The DSR hurdle in t-units (own approximation).** When the dispersion of trial Sharpe ratios equals pure sampling noise, DSR >= 0.95 requires roughly t >= E[max of N] + 1.645:

| N | 1 | 3 | 9 | 27 | 100 | 1,000 | 7,846 |
|---|---|---|---|---|---|---|---|
| t | 1.65 | 2.50 | 3.17 | 3.67 | 4.18 | 4.90 | 5.45 |

  So step 3 of QUANTGEN's gate, with honest trial counting, already implies t of about 3.2-3.7 for a card with 9-27 nearly independent configurations. Correlated configurations reduce the effective N (27 configurations at rho = 0.5 give N of about 1.9). The trial registry must therefore record how N_eff was estimated, rather than letting the author choose it.
- **Bonferroni haircut examples (own computation).** An observed SR of 0.8 over 8 years (t 2.26) becomes 0.55, 0.25 and 0 after 5, 20 and 100 tests. An observed SR of 1.2 over 8 years becomes 1.03, 0.87 and 0.64. This matches Harvey-Liu's nonlinearity: marginal strategies are wiped out, strong ones survive.
- **What this means for QUANTGEN.** Generic chart rules mined on liquid KRX large caps need t of about 3.4-3.8 (or StepM survival) before anyone should take them seriously. Positive technical-analysis findings are concentrated before 1990 and in young markets, so if technical rules are tested at all, KOSDAQ should be tested separately from KOSPI200 names, and only with full costs.
- **Which error rate to control.** FDR (Bajgrowicz-Scaillet) suits a **diversified basket** of rules. FWER (StepM/SPA) suits a **single displayed recommendation**. QUANTGEN displays exposure recommendations, so it should use FWER for any card it displays and FDR for the program-wide candidate list.

### Gaps
- Hansen (2005) could not be opened (publisher 403; no abstract on IDEAS/EconPapers/Semantic Scholar). The SPA description relies on the arch documentation.
- STW (1999) itself (the universe size as STW report it, and its 1987-1996 OOS result) is not verified here; the 7,846-rule count comes from Bajgrowicz-Scaillet.
- López de Prado (2018), *Advances in Financial Machine Learning* (purged k-fold, embargo, CPCV), was not opened. The CPCV evidence used here comes from Arian et al. and is synthetic-data evidence only.
- The fetched abstract of Chordia-Goyal-Saretto does not say whether the surviving strategies have economic content.
- No study testing a large technical-rule universe on KRX with SPA/StepM/FDR was found; the web search budget was exhausted. See data-check D1.

---

## Q2. Replication and post-publication decay: how much of the published premium is left?

### Takeaway
Whether anomalies replicate depends on construction. With careful replication, most published US predictors reproduce, at roughly 77-98% depending on the method. Microcap-neutral construction (NYSE breakpoints, value weights) knocks out 64-85%. Magnitudes are a different matter: in the US they fall about 26% out of sample and about 58% after publication (McLean-Pontiff), about 31% for alphas (Jensen-Kelly-Pedersen), and 60-77% for accounting-anomaly Sharpe ratios outside their discovery samples (Linnainmaa-Roberts). Outside the US there is **no reliable post-publication decline** across 39 markets (Jacobs-Müller). A single flat 60% haircut therefore fits poorly for a KRX-first desk whose test windows are already post-publication.

### Cited Findings
**Replication rates**
- Hou-Xue-Zhang, RFS 33(5):2019-2133, 2020 — [NBER w23394](https://www.nber.org/papers/w23394); [NBER PDF](https://www.nber.org/system/files/working_papers/w23394/w23394.pdf):
  - 447 anomalies, NYSE breakpoints, value-weighted returns, 1967-2014. 286 (64%) fail at t >= 1.96 and 380 (85%) fail at t >= 3.
  - Insignificant at the 5% level, by category: momentum 20/57 (35%), value-growth 37/68 (54%), investment 11/38 (29%), profitability 46/79 (58%), intangibles 77/103 (75%), trading frictions 95/102 (93%).
  - Microcaps are 61% of firms (2,406 of 3,938) but 3.28% of market cap. They make up more than 60% of extreme deciles under NYSE-AMEX-NASDAQ breakpoints.
  - Example: idiosyncratic volatility goes from -1.06%/m (t -3.1, as originally reported) to -0.51%/m (t -1.62) with NYSE breakpoints and value weights.
  - Of the 161 anomalies significant at 5%, the q-factor model makes 115 alphas insignificant.
  - Delisting returns: they follow Beaver-McNichols-Price. A missing delisting return is replaced by the mean of available delisting returns of the same delisting type and exchange over the prior 60 months; this "has little impact" on their results.
  - Jegadeesh-Titman momentum replicates at about 0.55-0.82%/m, against about 0.9-1.1%/m originally reported (per the PDF extraction).
- Chen-Zimmermann, "Open Source Cross-Sectional Asset Pricing": 319 characteristics from 153 papers. For the 161 clear predictors, 98% of long-short portfolios reproduce with t > 1.96, and a regression of reproduced on original t-statistics has slope 0.90 and R² 83%. — [Federal Reserve FEDS 2021-037 PDF](https://www.federalreserve.gov/econres/feds/files/2021-037pap.pdf)
- Jensen-Kelly-Pedersen, JF 78(5):2465-2518, 2023 — [NBER w28432](https://www.nber.org/papers/w28432); [NBER PDF](https://www.nber.org/system/files/working_papers/w28432/w28432.pdf):
  - US replication rate: 84.9% for CAPM alphas by OLS; 84.0% under their empirical Bayes model (80.7% when global data inform the US posteriors); 77.3% after a Benjamini-Yekutieli correction; 56.9% on raw returns, comparable to the Hou-Xue-Zhang baseline.
  - Capped value weights (winsorized at the NYSE 80th percentile) add about 8.5 points to the replication rate compared with pure value weights.
  - Average in-sample alpha of 0.45%/m falls to 0.31%/m after publication (about 31% attenuation). Factors that were stronger in sample stay stronger (slope 0.25-0.43).
  - World replication 84.9%; developed markets 77.8%; emerging markets 76.5%. Ex-US alpha = 0.067 + 0.73 x US alpha (R² 0.49).
  - 13 factor clusters; data covering 93 countries. Their Bayesian approach finds that the evidence is strengthened by the large number of factors.

**Decay**
- McLean-Pontiff, JF 2016 (working-paper PDF). 97 predictors from 80 studies; average in-sample L/S return 0.582%/m. Returns are 26% lower out of sample before publication (coefficient -0.150%/m) and 58% lower after publication (-0.337%/m), so about 32% is attributed to publication. Average spans: 323 months in sample, 56 months OOS before publication, 156 months after publication. Predictors with higher in-sample returns decline more. Post-publication returns stay higher in stocks with high idiosyncratic risk and low liquidity, consistent with limits to arbitrage. — [working-paper PDF (third-party-hosted copy)](https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf); [Wiley abstract page](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365)
- Linnainmaa-Roberts, RFS 31(7):2606-2649, 2018. Pre-discovery sample July 1926-June 1963 — [NBER w22894](https://www.nber.org/papers/w22894); [NBER PDF](https://www.nber.org/system/files/working_papers/w22894/w22894.pdf):
  - 36 accounting anomalies in sample: average 0.28%/m (t 8.67), FF3 alpha 0.26%/m (t 11.03).
  - Pre-discovery: 0.08%/m (t 2.18), with only 8 of 36 significant individually.
  - Post-discovery: 0.10%/m (t 2.83), with only 2 of 34 significant individually.
  - Sharpe ratios fall 60-77% out of sample, and three-factor information ratios fall 61%.
  - Before 1963, profitability earns 0.09%/m (t 0.86) and investment 0.02%/m (t 0.14), against 0.30%/m (t 3.60) and 0.25%/m (t 3.41) after 1963.
  - Data snooping is severe enough that even the true model would be rejected in sample. They propose OOS tests, or asking whether a model explains half of the in-sample alpha.
- Chen-Zimmermann, "Publication Bias and the Cross-Section of Stock Returns": 156 hedge portfolios. Bias-adjusted returns are only 12% smaller than in-sample returns, and a t-hurdle of 1.8 is enough to control multiple testing among predictors that pass journal review. The bias is too small to explain the post-publication deterioration, which points to mispricing. — [Federal Reserve FEDS page](https://www.federalreserve.gov/econres/feds/publication-bias-and-the-cross-section-of-stock-returns.htm)
- Chen-Lopez-Lira-Zimmermann: 29,000 data-mined accounting ratios. About 50% of predictability remains after the original sample periods, for both peer-reviewed and data-mined signals. Risk- or equilibrium-based theory does not protect against decay. — [arXiv 2212.10317](https://arxiv.org/abs/2212.10317)
- Jacobs-Müller, JFE 135(1):213-230, 2020: 241 anomalies in 39 stock markets (more than two million anomaly-country-months). The US is the only country with a reliable post-publication decline in long-short returns. They interpret this as barriers to arbitrage segmenting markets, and as mispricing rather than data mining. — [IDEAS](https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html)
- Context only (shared brief §3, not re-fetched by P4): Ilmanen et al. (2021) decay haircuts of value -49%, momentum -23% (not significant), multifactor -18%. — [00_QUANTGEN_context.md, local file]

### Inferences
- **The two literatures fit together.** Statistically, most published predictors are real. That supports JKP's Bayesian view and Chen-Zimmermann's small publication-bias estimate. Economically, US premia shrink by about a third to a half after publication, and microcap-heavy construction inflates both t-statistics and magnitudes.
- **Step 9 (fixed 60% haircut) double-counts decay for most KRX tests.** McLean-Pontiff's 58% is a US, in-sample-to-post-publication ratio. A KRX test over 2000-2026 of anomalies published in 1992-2008 is mostly post-publication already, so the measured OOS Sharpe already contains decay. Recommended rule:
  - h = 0.5, when the evidence is in-sample only or overlaps the original discovery sample (McLean-Pontiff 58%; Linnainmaa-Roberts "half");
  - h = 0.3, when the evaluation window is wholly post-publication, to allow for further crowding and the 2025 return of KRX short selling (JKP 31%; McLean-Pontiff 32% publication effect);
  - DSR, not h, handles selection bias for novel signals.
- **Korea may decay less, but only as a prior.** Jacobs-Müller suggest that published anomalies may keep more of their power in markets with arbitrage barriers. This supports testing published anomalies on KRX at all, but it is not a reason to weaken hurdles: their KRX-specific estimate was not checked.
- **Theory raises the probability that an effect is real, not the expected live size** (Chen-Lopez-Lira-Zimmermann). A behavioral mechanism should lower the t-hurdle (Q4). It should not lower the decay haircut.
- **Shrink toward clusters.** Following JKP, a KRX card's estimated alpha should be shrunk toward the global estimate for its factor cluster (for example quality, value, low risk, momentum). Global evidence then disciplines a short, noisy KRX sample.

### Gaps
- Korea's individual country estimates in Jacobs-Müller and JKP were not retrieved.
- Ilmanen et al. (2021) was not re-fetched; its numbers come from the shared brief.
- The JF 2016 published tables of McLean-Pontiff were not opened. Numbers come from the working-paper PDF, whose headline 26%/58% matches the published abstract as widely cited.
- Hou-Xue-Zhang's survival counts at t >= 3 by category could not be verified reliably from the extraction, so they are not reported.

---

## Q3. Costs, short-sale constraints, microcaps and capacity: what is implementable?

### Takeaway
Costs sort anomalies by turnover:
- **Low turnover** (value, gross profitability, annually rebalanced fundamentals) keeps roughly 90% of its gross spread in academic cost studies.
- **Monthly momentum** keeps about half on paper, but realized fund implementation leaves little of it.
- **High turnover** (short-term reversal, industry reversal, seasonality) is negative net of costs, even at institutional cost levels.

Across 204 anomalies, the expected net return in the modern era is about 4 bp/m. Short-side profits are hard to capture (long-only investors get about half of momentum and 60% of value), and KRX short selling was banned for long stretches. Every KRX stock card should therefore be judged long-only, against an equal-weighted liquid-universe benchmark.

### Cited Findings
**Academic spread-based costs**
- Novy-Marx-Velikov, RFS 2016, 23 anomalies, July 1963-December 2012, effective spreads estimated with Hasbrouck's Gibbs sampler — [NBER w20721](https://www.nber.org/papers/w20721); [NBER PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf):
  - Monthly costs: about 5 bp/m for low turnover (annual rebalancing), 20-57 bp/m for mid turnover, more than 100 bp/m for high turnover.
  - Momentum 133 bp/m gross becomes 68 bp/m net (t 2.45). Value 47 becomes 42. Gross profitability 40 becomes 37.
  - Short-run reversal 0.37%/m gross becomes -1.28%/m net (t -6.02). Industry momentum 0.93 becomes -0.29 (t -1.20). Industry-relative reversal 0.98 becomes -0.80 (t -4.73). Seasonality 0.84 becomes -0.62 (t -3.88). High-frequency combination 1.61 becomes 0.16 (t 1.11). Low-volatility industry-relative reversal 1.25 becomes 0.19 (t 1.41). *Caveat:* the tool table labeled average cost "bp", but the arithmetic implies percent per month, roughly 1.1-1.8%/m.
  - Most anomalies with one-sided monthly turnover below 50% keep significant net spreads.
  - A buy/hold spread is the single most effective simple mitigation: it cuts turnover by about 41% while keeping most of the gross return.
  - High-turnover strategies in microcaps: 1.77%/m gross becomes -0.66%/m net (t -5.12).
- Novy-Marx-Velikov (FAJ 2019): liquidity screens, slower rebalancing and banding all cut costs. Turnover-reducing methods hurt gross performance less than restricting trading to cheap stocks, and banding beats slower rebalancing because it keeps more exposure to the signal. — [IDEAS](https://ideas.repec.org/a/taf/ufajxx/v75y2019i1p85-102.html)
- Chen-Velikov, JFQA 58(3):968-1004, 2023: 204 anomalies, adjusted for effective spreads, post-publication effects and the post-2000 trading technology era. The average anomaly's expected return is a "measly 4 bps per month" (P4 shortens the quote). The strongest earn at best about 10 bp after data-mining controls, and combinations about 20 bp. Price impact is not even included. — [Cambridge Core](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/zeroing-in-on-the-expected-returns-of-anomalies/945133D5A3ECEEAF466AEE91551FD225). *Conflict:* the Fed FEDS working-paper page says 120 anomalies and 8 bp/m — [FEDS page](https://www.federalreserve.gov/econres/feds/zeroing-in-on-the-expected-returns-of-anomalies.htm). Use the published JFQA figures.
- Detzel-Novy-Marx-Velikov, JF 78(3):1743-1775, 2023, 205 anomalies. Ignoring costs favors models built on high-cost factors (the q-factor and Barillas-Shanken six-factor models). Net of costs, the Fama-French five-factor model, especially with cash profitability, does significantly better. — [IDEAS](https://ideas.repec.org/a/bla/jfinan/v78y2023i3p1743-1775.html)
- Novy-Marx-Velikov, "Betting against betting against beta" (JFE 2022): BAB's construction effectively equal-weights; each dollar of BAB commits on average $1.05 to stocks in the bottom 1% of market cap; its non-standard beta estimation drives the results. It stays positive after costs, through profitability and investment tilts. — [IDEAS](https://ideas.repec.org/a/eee/jfinec/v143y2022i1p80-106.html)

**Institutional and realized costs**
- Frazzini-Israel-Moskowitz, "Trading Costs" (AQR live executions: $1.7 trillion, 21 developed markets, 19 years) — [AQR page](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs); [PDF](https://spinup-000d1a-wp-offload-media.s3.amazonaws.com/faculty/wp-content/uploads/sites/3/2021/08/Trading-Cost.pdf):
  - Over August 1998-June 2016, mean market impact is 9.97 bp (median 6.18) and mean implementation shortfall 11.02 bp (median 8.63). Large caps average 8.90 bp of impact, small caps 18.95 bp.
  - Linear academic cost models imply costs an order of magnitude larger.
- Frazzini-Israel-Moskowitz, "Trading Costs of Asset Pricing Anomalies" (about $1 trillion of live trades, 1998-2013) — [PDF](http://spinup-000d1a-wp-offload-media.s3.amazonaws.com/faculty/wp-content/uploads/sites/3/2021/08/Trading-Cost-of-Asset-Pricing-Anomalies.pdf); [SSRN abstract](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2294498):
  - US break-even fund sizes for standard strategies: size $275.5bn, value $214.3bn, momentum $56.2bn. International: value about $95bn, momentum just under $19bn.
  - Cost-optimized versions at under 1% tracking error reach $1.9tn, $1tn and $160bn.
  - Short-term reversal, at about 300% monthly turnover, was **unprofitable after realized costs**.
- Patton-Weller, JFE 137(2):515-549, 2020 — [EconPapers](https://econpapers.repec.org/article/eeejfinec/v_3a137_3ay_3a2020_3ai_3a2_3ap_3a515-549.htm); [working paper PDF](https://public.econ.duke.edu/~ap172/Patton_Weller_MF_25sep18.pdf):
  - Implementation costs are measured from 4,267 US equity mutual funds, 1970-2016.
  - Momentum costs 2.3-7.6% a year: on paper 8.72-8.85% a year, realized by funds 1.28-1.54%.
  - Value costs 2.1-4.1% a year: on paper 5.20-6.71%, realized 2.31-2.64%.
  - Size and market are implemented at near-zero cost.
  - Typical funds earn little from value and nothing from momentum. Smaller funds earn 5-6% more per unit of momentum beta than the largest funds.

**Short-sale constraints and limits to arbitrage**
- Shleifer-Vishny: arbitrage needs capital, is risky, and is done by a few specialists using other people's money. It can become ineffective exactly when prices are far from fundamentals. — [IDEAS, JF 52(1), 1997](https://ideas.repec.org/a/bla/jfinan/v52y1997i1p35-55.html)
- Stambaugh-Yu-Yuan: anomaly long-short returns are larger after high investor sentiment, the short leg in particular. Sentiment has no relation to long-leg returns, consistent with short-sale impediments causing overpricing. — [IDEAS, JFE 104(2), 2012](https://ideas.repec.org/a/eee/jfinec/v104y2012i2p288-302.html)
- Israel-Moskowitz: long positions earn almost all of the size premium, about 60% of value profits and about half of momentum profits. The value premium is weak among the largest stocks; momentum has no reliable relation with size. — [IDEAS, JFE 108(2), 2013](https://ideas.repec.org/a/eee/jfinec/v108y2013i2p275-301.html)
- McLean-Pontiff: post-publication returns stay higher in high-idiosyncratic-risk, illiquid stocks. — [PDF](https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf)
- Fama-French (2008): net issues, accruals and momentum anomalies appear in micro, small and big stocks. Asset growth and profitability are less robust, with asset growth absent among big firms. — [IDEAS, JF 63(4)](https://ideas.repec.org/a/bla/jfinan/v63y2008i4p1653-1678.html)

**KRX facts that bear on the cost model**
- Short-selling bans: 2008-10-01 to 2009-05-31; 2011-08-11 to 2011-11-09; 2020-03-16 to 2021-05-03, after which only KOSPI200 and KOSDAQ150 stocks (350 names) reopened; 2023-11-05 to 2025-03-31 (KCMI dates). — [KCMI report](https://www.kcmi.re.kr/common/downloadw?fid=27533&fgu=002001&fty=004003)
- Full resumption for all listed stocks from 2025-03-31, with the KRX naked short-sale detection system (NSDS). Retail and institutional investors both get 105% cash collateral and stock repayment within 90 days, renewable up to 12 months. Penalties for naked shorting are 4-6x the unfair gains. — [FSC press release](https://www.fsc.go.kr/eng/pr010101/84220). (FSC gives the ban start as 2023-11-03, the announcement date; KCMI gives 2023-11-05.)
- Securities transaction tax from 2026-01-01: KOSPI 0.05% tax plus 0.15% rural special tax = 0.20%; KOSDAQ and K-OTC 0.20% (up from 0.15%); KONEX 0.10%. In 2025 KOSPI was 0% + 0.15% = 0.15%. — [Herald Business, Dec 2025](https://biz.heraldcorp.com/article/10627001)

**KRX quick-checks from the parallel data lab** (descriptive and in-sample, not gate runs). Liquid universe = market cap >= KRW 100bn, 20-day average traded value >= KRW 1bn, price >= KRW 1,000, no warning flags. Monthly quintiles, equal weight, 35 bp per side. — [E7_quickchecks local files: E7_factor_quickcheck.csv, E7_part2_*.csv, e7_checks_part1_factors.py; /home/claude/research_notes/QUANTGEN technical and fundamental signals/E7_quickchecks/]
- **1-month reversal (STR), long losers vs short winners:**
  - 2015-07 to 2019-12: SR 0.98 gross, **0.12 net**.
  - 2020-2024: 0.58 gross, **-0.28 net**.
  - 2025-01 to 2026-06: -1.24 gross.
  - The long leg turns over about 10x a year one-way.
- **60-day low volatility:**
  - L/S net SR 0.51 (2015-2019) and 0.81 (2020-2024).
  - Long leg minus EW benchmark: net SR 0.35 and 0.27.
  - About 3.8x a year one-way turnover.
- **Short-sale regime split for STR**, gross L/S SR: open 0.24, partial ban 0.99, full ban 0.54.

### Inferences
- **Cost arithmetic (own computation):** annual drag = 2 x per-side cost x one-way turnover per year.

| Turnover | KRX stock 35 bp | KRX stock 70 bp (2x) | KRX ETF 3 bp | US shares 50 bp |
|---|---|---|---|---|
| Monthly, 100% one-way | 8.4%/yr | 16.8%/yr | 0.7%/yr | 12.0%/yr |
| Weekly, 100% one-way | 36.4%/yr | 72.8%/yr | 3.1%/yr | 52.0%/yr |

  A KRX weekly reversal card would need about 36% a year of gross alpha just to break even.
- **QUANTGEN's 35 bp per side is mis-specified in both directions.**
  - It is generous for small, illiquid KOSDAQ names. The 2026 sell tax alone is 20 bp (10 bp per side on average), leaving about 25 bp per side for spread, impact and commission. US academic estimates for small-cap, high-turnover trades exceed that.
  - It is probably too harsh for KOSPI200 mega-caps, whose spreads are a tick or two. KRX tick sizes were not verified here.
  - A **liquidity-bucket cost model** is needed (see Q7). It can be estimated from OHLC alone with a high-low spread estimator (Corwin-Schultz 2012; Abdi-Ranaldo 2017: "a new method to estimate the bid-ask spread when quote data are not available", [Oxford Academic](https://academic.oup.com/rfs/article/30/12/4437/3982054)), checked against KIS quotes where available. The estimator details were not opened.
- **Short-term reversal should drop from Korea weight 3 to BACKLOG** until it passes net of bucket costs. US academic and institutional evidence and the in-sample KRX quick-check agree that it is gross-positive and net-zero or negative. The regime split also suggests part of the KRX reversal premium came from the short leg while shorting was banned, a premium a long-only retail investor cannot capture.
- **Long-only by default.** QUANTGEN is a read-only retail desk. Since March 2020 KRX has had about 2.5 years of full short-selling bans and about 2.5 years of a partial ban (only KOSPI200/KOSDAQ150 names shortable), roughly 5 of the last 6.5 years. Every stock card should report (i) long leg minus the EW liquid-universe benchmark (primary) and (ii) the long-short spread (diagnostic only). Israel-Moskowitz imply the long leg keeps roughly 50-60% of momentum and value premia.
- **Capacity is not binding for an individual investor.** Institutional break-even sizes are in the tens to hundreds of billions of dollars. The binding constraints are per-name liquidity (a cap on participation in daily traded value) and KRX price limits.
- **Microcap artefacts.** All cross-sectional KRX cards must use a liquid-universe screen and report value-weighted (or capped value-weighted) results alongside equal-weighted ones. A card whose EW and VW results disagree in sign is REVISE, not PASS.

### Gaps
- No published KRX-specific estimate of effective spreads or price-impact functions by size bucket was retrieved, because the search budget was exhausted. KRX tick-size tables were not verified.
- Corwin-Schultz (2012) and Abdi-Ranaldo (2017): the estimator details and accuracy statistics were not opened.
- Korean evidence on anomaly costs (for example reversal net of the transaction tax) was not found in the literature; see data-checks D2-D4.
- Stambaugh-Yu-Yuan's 11-anomaly table and magnitudes were not retrieved.

---

## Q4. Behavioral foundations as priors: which signal families deserve a lower hurdle?

### Takeaway
The four canonical behavioral models predict two patterns: **underreaction and drift over roughly 1-12 months** (earnings drift, intermediate momentum) and **overreaction and reversal over roughly 3-5 years**. None of them makes a specific prediction for oscillator thresholds, crossovers or chart patterns. Following Harvey (2017), a credible mechanism should change the *prior odds*, and therefore the t-hurdle. It should not change the expected live magnitude, because theory does not protect against decay (Chen-Lopez-Lira-Zimmermann).

### Cited Findings
- Barberis-Shleifer-Vishny: conservatism (slow updating) produces underreaction to news such as earnings announcements. Representativeness produces overreaction to a series of good or bad news. One parsimonious model of belief formation generates both. — [IDEAS, JFE 49(3), 1998](https://ideas.repec.org/a/eee/jfinec/v49y1998i3p307-343.html)
- Daniel-Hirshleifer-Subrahmanyam: overconfidence about private signals produces overreaction to private information, underreaction to public signals, long-lag reversals and excess volatility. Biased self-attribution adds short-lag momentum and short-run earnings drift. In their account momentum is continuing overreaction. — [Author-hosted PDF, JF 53(6), 1998](http://www.kentdaniel.net/papers/published/jf98.pdf)
- Hong-Stein: "newswatchers" do not fully extract others' information from prices, so gradual diffusion causes short-run underreaction. Momentum traders, limited to simple univariate strategies, then push prices to overreact at longer horizons. — [IDEAS, JF 54(6), 1999](https://ideas.repec.org/a/bla/jfinan/v54y1999i6p2143-2184.html)
- Grinblatt-Han: the disposition effect (prospect theory plus mental accounting) produces underreaction. A proxy for aggregate unrealized capital gains is the key driver of momentum profits, and past returns lose their predictive power once it is controlled for. — [IDEAS, JFE 78(2), 2005](https://ideas.repec.org/a/eee/jfinec/v78y2005i2p311-339.html)
- Harvey: posterior probability of the null = MBF x prior odds / (1 + MBF x prior odds), with MBF = exp(-t²/2). He recommends treating theory-derived predictions differently from data-mined ones, and showing results under more than one prior. — [Duke PDF, JF 72(4), 2017](https://people.duke.edu/~charvey/Research/Published_Papers/P131_The_scientific_outlook.pdf)
- Chen-Lopez-Lira-Zimmermann: risk- or equilibrium-based explanations did not protect predictors from post-sample decay. Only papers agnostic about the explanation outperformed. — [arXiv 2212.10317](https://arxiv.org/abs/2212.10317)
- Shleifer-Vishny: the limits-to-arbitrage model predicts where anomalies persist, namely where arbitrage is costly and risky. This is a "survival" prior that complements the behavioral "origin" priors. — [IDEAS, JF 52(1), 1997](https://ideas.repec.org/a/bla/jfinan/v52y1997i1p35-55.html)

### Inferences
- **Bayesian t-hurdles (own computation with Harvey's formula).** Smallest t at which the posterior probability of the null is at most 10% (or 5%):

| Prior odds against a real effect | Posterior P(null) <= 10% | <= 5% |
|---|---|---|
| 1:1 (published, mechanism, international replication) | t >= 2.10 | 2.43 |
| 4:1 | 2.68 | 2.94 |
| 9:1 (published but fragile, or a plausible new variant) | 2.96 | 3.21 |
| 19:1 (novel chart pattern, no mechanism) | 3.21 | 3.43 |

  The resulting two-tier rule (t of about 2.0-2.1 for strong-prior replications; t >= 3.0 for weak-prior signals, rising to 3.4 for large rule searches) agrees with Harvey-Liu-Zhu's 3.0 and Chordia-Goyal-Saretto's 3.4-3.8 for weak priors, and with Chen-Zimmermann's 1.8 for peer-reviewed predictors.
- **Prior assignment for QUANTGEN's planned families** (P4 judgment, to be pre-registered):

| Family | Theory or mechanism prior | Survives frictions? | Proposed tier |
|---|---|---|---|
| Earnings-announcement drift (PEAD), event-timed on DART | Strong (BSV conservatism; DHS public-signal underreaction) | Moderate turnover | A |
| Profitability/quality (GP/A, cash profitability) | Contested mechanism; best net-of-cost model evidence (Detzel-Novy-Marx-Velikov) | Low turnover | A |
| Value (B/M, E/P) | Strong (BSV long-horizon overreaction; limits to arbitrage) | Low turnover | A |
| 12-1 momentum and capital-gains-overhang / 52-week-high variants | Strong (Hong-Stein, DHS, Grinblatt-Han) | Mid turnover; crash risk | A for the US; B for KRX, given the weak KRX evidence in the shared brief |
| Low volatility / low MAX | Leverage and lottery-preference mechanisms (not opened here) | Mid turnover | B until sourced |
| 1-5 day / 1-month reversal | Not predicted by the four behavioral models above (they work at 1-12 months and 3-5 years) | Fails costs in the US | B, with a cost-first test (D2) |
| RSI/MACD/Bollinger thresholds, crossovers, chart patterns | No model-specific prediction | Usually high turnover | B (t >= 3.0; >= 3.4 if more than 100 configurations) |
| 3-5 year long-run reversal | BSV, DHS, Hong-Stein | Very low turnover | A, BACKLOG |

- **Grinblatt-Han offers a theory-backed alternative to raw 12-1 momentum for Korea**, where 12-1 is weak (shared brief §3). A capital-gains-overhang or 52-week-high-proximity card should be pre-registered as **one** configuration family, not added to a momentum grid after the fact.
- **A mechanism lowers the hurdle; it does not lower the haircut.** Tier A cards still take the decay haircut from Q2.

### Gaps
- The low-volatility mechanism literature (leverage constraints, lottery demand) and Korean behavioral evidence (for example retail-investor dominance and the disposition effect on KRX) were not retrieved.
- The tier assignments are P4's judgment and are not taken from any source.

---

## Q5. "Success rate" claims and retail charting-platform backtests: why they mislead

### Takeaway
A win rate says nothing about profitability without the payoff ratio. Expectancy per trade = p x average win - (1-p) x average loss - costs, and on a driftless price any bracket order has zero gross expectancy whatever its win rate. Retail strategy testers add further problems, many of them documented by the platform itself: zero default commission and slippage, idealized intrabar fills, repainting and look-ahead (more than 95% of indicators repaint in some form, per TradingView), optimization on the same data used to report results, and universes that do not handle delistings. A TradingView "percent profitable" figure should be treated as an untested claim. The only number to carry forward is net expectancy, with a confidence interval, measured on an independent re-implementation.

### Cited Findings
**Platform documentation (TradingView Pine Script v6, T2 primary documentation)**
- The `strategy()` declaration defaults: `commission_value` is 0, so no commission is simulated unless the user sets one. `slippage` is 0, so orders fill at expected prices. With `process_orders_on_close = false` (the default), an order generated at a bar's close fills at the next bar's open. `calc_on_every_tick = false` (default) runs the strategy once per bar. Default `initial_capital` is 1,000,000 and default order size is 1 unit. — [TradingView, Declaration statements](https://www.tradingview.com/pine-script-docs/language/declaration-statements/)
- Broker-emulator assumptions — [TradingView, Strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/):
  - On historical bars it uses chart data only by default.
  - It infers the intrabar path as open, high, low, close when the open is nearer the high (open, low, high, close otherwise), and it assumes no gaps inside a bar for price-based orders.
  - Results on non-standard charts (for example Heikin Ashi or Renko) use synthetic prices, which the documentation calls unrealistic.
  - The optional bar magnifier uses lower-timeframe data to improve intrabar fills.
  - The report shows metrics such as profitable-trade share, profit factor, Sharpe and Sortino.
- Repainting means historical and realtime calculations behave differently, and the documentation estimates that over 95% of indicators show some form of it — [TradingView, Repainting](https://www.tradingview.com/pine-script-docs/concepts/repainting/):
  - `request.security()` with `lookahead = barmerge.lookahead_on` and no offset returns future data on historical bars ("dangerously misleading").
  - `varip` state cannot be reproduced on historical bars.
  - `barstate.isnew` behaves differently on historical and realtime bars.
  - Strategies with `calc_on_every_tick = true` run on every realtime tick but only at bar closes historically, so the backtest does not reflect live order execution.

**Regulatory framing**
- US CFTC Regulation 4.41(b)(1) requires hypothetical or simulated performance to carry a disclaimer. It must state that the results do not represent actual trading, may under- or over-compensate for liquidity, and benefit from hindsight. — [eCFR 17 CFR 4.41](https://www.ecfr.gov/current/title-17/chapter-I/part-4/subpart-C/section-4.41)

**Evidence that backtest statistics do not predict live results**
- Wiecki-Campbell-Lent-Stauth (Quantopian): across 888 algorithms with at least 6 months of out-of-sample data, backtest Sharpe ratio has R² below 0.025 for OOS Sharpe. Volatility, maximum drawdown and hedging carry more predictive value. More backtesting goes with a larger IS-OOS gap. A non-linear classifier reaches R² of 0.17 on hold-out data. — [SSRN 2745220](https://ssrn.com/abstract=2745220)
- Bajgrowicz-Scaillet: picking last month's best technical rules gives negative next-month performance in most recent periods ("no hot hands"). — [UNIGE full text](https://access.archive-ouverte.unige.ch/access/metadata/d1a36296-e8c4-423b-9ed9-9870cfc76d9c/download)

**Survivorship and look-ahead in data**
- Shumway: CRSP lacks correct delisting returns for most stocks delisted for negative reasons since 1962, and the omitted delisting returns are large. — [IDEAS, JF 52(1), 1997](https://ideas.repec.org/a/bla/jfinan/v52y1997i1p327-40.html)
- Beaver-McNichols-Price: delisting firm-years are concentrated in the extreme deciles of anomaly variables. Including them can raise returns (earnings, cash flow, book-to-market strategies) or lower them (accruals). — [SSRN 949601, JAE 43, 2007](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=949601)
- OpenDART's `rcept_dt` field is the date a disclosure was received (YYYYMMDD). That is the natural point-in-time availability stamp for Korean fundamentals. — [OpenDART API guide](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)

### Inferences
- **Expectancy arithmetic (own computation).** For a driftless price, a bracket with target +a and stop -b hits the target first with probability b/(a+b), so gross expectancy is zero at any win rate:

| Bracket (target / stop) | Win rate | Gross expectancy per trade | Net at 70 bp round trip (KRX stock, 35 bp per side) |
|---|---|---|---|
| +1% / -1% | 50% | 0 | -0.70% |
| +1% / -3% | 75% | 0 | -0.70% |
| +1% / -9% | 90% | 0 | -0.70% |
| +2% / -8% | 80% | 0 | -0.70% |

  The breakeven win rate is L/(W+L) plus costs. A "90% success rate" strategy with a 1:9 payoff ratio is therefore a cost-losing machine unless it has real drift.
- **How many trades are needed to test expectancy (own computation).** n = (t / per-trade Sharpe)². A per-trade Sharpe of 0.1 needs 400 trades for t = 2 and 900 for t = 3. Most retail "high win-rate" tests report far fewer trades.
- **Translation rules for TradingView-sourced ideas** (P4 recommendation):
  1. Re-implement the logic in QUANTGEN's Python engine from the written description; never import reported metrics.
  2. Fix the published parameters as the single configuration, with neighbours only for the plateau test.
  3. Count the unknown search done on the platform as N >= 100 for DSR, putting the idea in the t >= 3.4 tier.
  4. Reject scripts using `lookahead_on` without an offset, `varip`, `calc_on_every_tick`, intrabar stop/limit assumptions on daily bars, or non-standard chart types.
  5. Report win rate, payoff ratio, profit factor and net expectancy per trade with a bootstrap CI, at QUANTGEN costs.
- **Default fills are a problem in KRX.** TradingView's default (fill at the next bar's open) is in principle compatible with QUANTGEN's rule 2 (decide at the close of t, earn from t+1). The danger is in small KRX names, where the t+1 open can gap through the signal price, or open locked at the price limit. QUANTGEN's engine should model next-open fills and refuse fills at locked limit prices (Q7, P4).

### Gaps
- No TradingView documentation was found stating how its symbol universe handles delisted stocks (survivorship). This is not asserted either way.
- The publication venue of the Quantopian study is not verified; it is cited as an SSRN paper.
- No academic study measuring the live performance of published TradingView community strategies was found.

---

## Q6. Sharpe-ratio inference: standard errors, serial correlation, track-record length and bootstrap design

### Takeaway
Sharpe ratios are estimated imprecisely. With IID returns the standard error of an annualized SR is about sqrt((1 + SR²/2) / years): about 1.41 for a single 126-session OOS window, about 0.35 over 8 years and about 0.18 over 31 years. Positive serial correlation inflates annualized Sharpe ratios (by up to 65% in Lo's hedge-fund examples). Negative skew and fat tails lengthen the track record needed. Comparing a strategy with a benchmark calls for a studentized time-series bootstrap of the Sharpe difference (Ledoit-Wolf) with a data-driven block length (Politis-White), not a fixed 10-session block. The power problem is severe: a true net SR of 0.5 has only about a 16% chance of reaching t >= 3 over 16 years.

### Cited Findings
- Lo (2002) — [Berkeley-hosted PDF, FAJ 58(4)](https://traders.studentorg.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf); [IDEAS](https://ideas.repec.org/a/taf/ufajxx/v58y2002i4p36-52.html):
  - IID asymptotic standard error: SE(SR) = sqrt((1 + SR²/2) / T). For example, SR 1.5 with T = 60 gives SE 0.188.
  - Under serial correlation, scaling by sqrt(q) is wrong. In his examples, a mortgage-backed-securities fund's annual SR falls from 4.03 to 2.44 (a 65% overstatement) and a convertible/option-arbitrage fund's from 4.35 to 2.99 (45%).
  - Positive autocorrelation lowers the correctly annualized SR; negative autocorrelation raises it.
- Bailey-López de Prado, "The Sharpe Ratio Efficient Frontier" — [author PDF](https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf); [SSRN 1821643](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1821643):
  - Non-normal SR variance (after Mertens 2002): (1 + SR²/2 - SR x skew + SR² (K - 3)/4) / n, with K raw kurtosis.
  - PSR(SR*) = Phi[(SR - SR*) sqrt(n - 1) / sqrt(1 - skew x SR + SR² (K - 1)/4)].
  - MinTRL = 1 + [1 - skew x SR + SR² (K - 1)/4] x (z_alpha / (SR - SR*))².
  - For monthly returns with skew -0.72 and kurtosis 5.78, 95% confidence: an observed SR of 1.0 needs 3.62 years to reject SR* = 0 and 14.23 years to reject SR* = 0.5. An observed SR of 2.0 needs 1.31 / 2.26 / 4.99 years against SR* = 0 / 0.5 / 1.0. *P4 reproduced all of these with the formula.*
- Ledoit-Wolf (2008): to test whether two Sharpe ratios differ, build a studentized time-series bootstrap confidence interval for the difference. The Jobson-Korkie test (with Memmel's correction) is invalid under heavy tails or time-series dependence. — [IDEAS, J. Empirical Finance 15(5)](https://ideas.repec.org/a/eee/empfin/v15y2008i5p850-859.html)
- Politis-White (2004): automatic estimators of the optimal block length for block bootstraps, adapting to the strength of correlation shown in the correlogram. — [IDEAS, Econometric Reviews 23(1)](https://ideas.repec.org/a/taf/emetrv/v23y2004i1p53-70.html)
- Bailey-López de Prado (2014): the deflated Sharpe ratio uses skewness, kurtosis and sample length together with the number of trials. — [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)
- The arch library implements SPA, StepM and the Model Confidence Set on loss series of a benchmark and competing models (here, negative returns). — [arch documentation](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison_examples.html)

### Inferences
- **Precision (own computation; IID SE of annualized SR):**

| Window | True SR 0 | 0.5 | 1.0 |
|---|---|---|---|
| One 126-session window | 1.41 | 1.50 | 1.73 |
| 3 years | 0.58 | 0.61 | 0.71 |
| 8 years | 0.35 | 0.38 | 0.43 |
| 31 years | 0.18 | 0.19 | 0.22 |

  Single walk-forward windows are uninformative on their own. Gate inference must use the concatenated OOS path or the CPCV distribution.
- **Years of data needed (own computation; MinTRL, normal daily returns, SR* = 0):**

| True SR | One-sided 95% (z 1.645) | t = 2.0 | t = 3.0 |
|---|---|---|---|
| 0.3 | 30 | 45 | 100 |
| 0.5 | 10.8 | 16 | 36 |
| 0.8 | 4.2 | 6.3 | 14.1 |
| 1.0 | 2.7 | 4.0 | 9.0 |

  Realistic net fundamental-factor Sharpe ratios of 0.3-0.5 **cannot reach t = 3 on KRX history (about 26 years) alone**.
- **Power (own computation).** With a true net SR of 0.5, P(t >= 2) / P(t >= 3) is 0.50 / 0.16 over 16 years and 0.74 / 0.36 over 28 years. With a true SR of 0.8, it is 0.88 / 0.58 over 16 years. Hence the tiered hurdles (Q4/Q7), and JKP-style shrinkage toward global factor evidence for Tier A cards, rather than demanding t = 3 of everything. A blanket t = 3 would reject most true-but-modest factor premia. A blanket t = 2 would let chart-pattern noise through.
- **Block bootstrap.** Monthly-rebalanced stock portfolios hold for about 21 sessions, and daily returns of overlapping-holding strategies are autocorrelated. The bootstrap block length should be at least the larger of the Politis-White estimate and twice the holding period (about 42 sessions for monthly cards), not a fixed 10. A stationary bootstrap (random block lengths) is the natural default for SPA/StepM, as in standard implementations.
- **Serial correlation.** For strategies whose daily returns are autocorrelated (stale-price small caps, overlapping holdings), report Lo's corrected annualization or compute Sharpe on monthly returns. A KOSDAQ small-cap card's daily-return Sharpe is likely overstated.
- **Use PSR rather than Lo's IID formula.** Short-volatility-like and reversal strategies have negative skew. Replace Lo's IID SE in gate step 2 with the Mertens/PSR variance.

### Gaps
- The tool summary of the PSR worked example in the Sharpe-frontier PDF (SR 1.59 over 2 years, PSR 0.98 falling to 0.43 under skew -2.448, kurtosis 10.164) could not be reproduced: P4's recomputation gives about 0.91. The example is not used.
- Politis-Romano (1994), the stationary bootstrap paper, could not be opened (403/404). Its use is described as standard practice without a quoted source.
- No study was found estimating the autocorrelation of daily returns of KRX anomaly portfolios. See data-check D6.

---

## Q7. QUANTGEN translation: an audit of the nine-step gate, and the protocol every technical/fundamental card must follow

### Takeaway
The gate's design is sound, and on several points stricter than most published practice: pre-registration, revisions counted as trials, DSR, PBO, 2x costs, and published failures. For stock-level cards, though, it mis-calibrates five things:
1. multiplicity across configurations and across cards (no SPA/StepM/FDR);
2. single-test hurdles (a 90% interval, p <= 0.10);
3. costs (flat per side, no liquidity buckets, no time-varying tax, no price-limit or entry-timing realism);
4. implementability (no long-only, short-ban, delisting or point-in-time rules);
5. decay (a flat 60% haircut on total Sharpe).

The protocol below fixes these with tiered hurdles, a sealed holdout, prospective incubation and a liquidity-bucket cost model, without discarding the existing nine steps.

### Cited Findings
- QUANTGEN's gate (shared brief):
  - (1) purged walk-forward, 756 IS / 126 OOS sessions, embargo = holding period;
  - (2) Lo SE plus a 90% block bootstrap (2,000 x 10-session blocks) whose interval must clear zero;
  - (3) DSR >= 0.95, with every revision counted as a trial;
  - (4) PBO via CSCV <= 0.05;
  - (5) beat the benchmark on the same days, one-sided p <= 0.10;
  - (6) SR > 0 at 2x costs;
  - (7) plateau: >= 50% of neighbouring configurations keep half the Sharpe;
  - (8) >= 60% of calendar years positive;
  - (9) a 60% live haircut, reported but not gated.
  - KRX stock cost is 35 bp per side (70 bp at 2x); US shares via KIS 50 bp. Study of 2026-09-27: 34 cards, 5 PASS / 11 REVISE / 18 REJECT. C3 crypto trend PASS: SR 1.22 [0.62, 1.77] vs buy-and-hold 0.79, p 0.04 (BTC-USD p 0.07). No stock-level cross-sectional card exists yet.
  - Source: [00_QUANTGEN_context.md, local file](/home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/00_QUANTGEN_context.md)
- The benchmark choice matters on KRX. In the data lab's in-sample yearly table, the KOSPI200 proxy (cap-weighted) returned +80.6% in 2025 and +66.5% in 2026 YTD. Excluding Samsung Electronics and SK hynix, it returned +51.4% and +21.0%; the equal-weighted 200 returned +56.5% and +23.1%. — [E7_part2_k200proxy_factor_years.csv, local data-lab output](/home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/E7_part2_k200proxy_factor_years.csv)
- How the data lab's quick-check code handles returns: a stock's return is set to missing on zero-volume days. Portfolio returns are cross-sectional means of the non-missing returns, so a suspended stock drops out of the average. Positive returns above the daily price limit (30.5% after 2015-06-15, 15.5% before) are discarded as artefacts. The liquid universe excludes stocks with administrative or warning flags at formation. — [e7_checks_part1_factors.py, local file](/home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/E7_quickchecks/e7_checks_part1_factors.py)
- Daniel-Moskowitz: a dynamic momentum strategy built on forecasts of mean and variance roughly doubles the alpha and Sharpe of static momentum. Crashes happen in panic states, after market declines and when volatility is high, at the same time as market rebounds. — [NBER w20439](https://www.nber.org/papers/w20439)
- Supporting literature for each step is cited in Q1-Q6: White; Hansen via arch; Romano-Wolf; Bajgrowicz-Scaillet; Bailey-López de Prado; Bailey-Borwein-López de Prado-Zhu; Arian et al.; Lo; Ledoit-Wolf; Politis-White; Novy-Marx-Velikov; Chen-Velikov; Frazzini-Israel-Moskowitz; Patton-Weller; McLean-Pontiff; JKP; Jacobs-Müller; Shumway; Beaver-McNichols-Price; OpenDART; FSC; Herald.

### Inferences

#### A. Gate audit: each step against the literature

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

#### B. Gaps not covered by any current step
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

#### C. Protocol P4-TF-1 (pre-registered; applies to every new technical or fundamental card)
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

#### D. Cost and execution assumptions (P4 proposals; calibrate in D3 before first use)

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

#### E. What to expect when the protocol is applied
- Chart-pattern and oscillator cards on liquid KRX stocks: mostly REJECT. This is the priced-in base rate implied by Bajgrowicz-Scaillet, the noise calibration, and 70 bp round trips.
- Tier A low-turnover fundamentals (cash profitability/quality, value) and possibly long-only low volatility: the realistic BUILD candidates. Their likely verdict is INSUFFICIENT DATA or REVISE rather than PASS, because KRX history only supports t of about 2 for SR of about 0.5.
- Korean reversal: BACKLOG pending D2.
- Momentum on KRX: Tier B (weak local evidence), with a crash stress test (D12).

### Gaps
- OpenDART's coverage of structured financial-statement data was not verified; it may begin around 2015. If so, fundamental cards would have about 10 years of point-in-time history, which strengthens the INSUFFICIENT DATA and shrinkage logic.
- KRX's liquidation-trading procedure for delisting stocks and its tick-size table were not verified from KRX sources. The delisting stress values (-30%, -100%) are P4 assumptions (-30% echoes the common CRSP-literature replacement value, which P4 could not verify from Shumway's text).
- The cost-bucket numbers are P4 proposals, not estimates; D3 must calibrate them.
- The program-wide FDR re-scoring of existing cards needs every card's p-value, but the brief lists only some.

---

## Q8. Where and when it failed (dated episodes, mandatory)

### Takeaway
Failures cluster in five patterns:
1. technical rules after the early 1960s on mature indices;
2. high-turnover signals once costs are charged;
3. accounting anomalies outside their discovery samples;
4. crowded or levered factor books in liquidity shocks (August 2007; momentum crashes of 1932 and 2009);
5. on KRX in 2025-26, reversal, low-volatility and momentum quintiles each took deep, short drawdowns against an equal-weighted benchmark during the melt-up and the June-July 2026 crash.

### Cited Findings
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

### Inferences
- Every family QUANTGEN plans to build has at least one documented failure of 15-75% over one to two months, or of several years. The protocol must therefore report worst rolling 21- and 63-session net excess, and a stress replay of 2008-09, 2020-03, 2025-01 to 2026-06 and 2026-06-23 to 07-30. Means and Sharpe ratios alone are not enough.
- The 2026 KRX episodes come from data the data lab has **already looked at**. They are failure evidence, not out-of-sample tests (G8).
- 2007 and 2026 point the same way: crowding risk is about the **position** (a common factor book or common winners), not the signal's historical t-statistic. Concentration caps (for example Samsung and SK hynix) belong in the risk layer, as the macro panel decided.

### Gaps
- No dated KRX failure from peer-reviewed Korean literature was retrieved, because the search budget was exhausted. The KRX episodes above come from the in-house quick-checks only.
- Magnitudes for the August 2007 unwind (percentage losses by strategy) were not in the fetched abstract.
- Neely-Weller-Ulrich (2009) on the decline of FX technical-rule profits could not be opened (404), so it is not used.

---

## Q9. Data-check requests for the data lab (exact tests)

### Takeaway
Fourteen tests, in priority order. **D14 (the size of the gate under the null)** and **D3 (cost buckets)** come first because every other verdict depends on them. **D2 (KRX reversal net of costs)** decides the Korea weight conflict.

### Cited Findings
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

### Inferences
- D14 is the single most informative test. It turns the gate from a collection of literature-inspired rules into a test of known size. D3 is a prerequisite for every net-of-cost verdict on stock cards.

### Gaps
- D3 requires KIS quote snapshots, which are not in the listed historical datasets. Validation may need prospective collection.
- D5 depends on whether the marcap data carries delisting reasons; if not, the classification must use flag history alone.

---

## Q10. Claims ledger (mandatory)

### Takeaway
30 claims. In the implication column, "BUILD-candidate (gate)" means build the item into the gate or protocol. For signal claims, the implication names the card decision.

### Cited Findings

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

### Inferences
- The claims that change gate mechanics (C01, C05, C11, C15, C19-C21, C24, C27, C28, C30) should be decided together, because they interact. For example, tiered hurdles combined with long-only primary statistics and bucket costs will reject many more cards than any single change would. D14 measures the combined size of the gate.

### Gaps
- Tiers for in-house quick-checks and own computations are labeled "derived" or "in-house" because the T1/T2/T3 scale does not cover them.

---

## Q11. Source list

### Takeaway
All sources below were opened (fetched) during this research unless marked "not opened". Numbers attributed to them in this note come from the fetched pages.

### Cited Findings
**Multiple testing and data snooping (T1)**
- White (2000) Econometrica — https://www.econometricsociety.org/publications/econometrica/2000/09/01/reality-check-data-snooping
- Romano-Wolf (2005) Econometrica — https://ideas.repec.org/a/ecm/emetrp/v73y2005i4p1237-1282.html
- Hansen SPA, via arch documentation (T2 software documentation) — https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison_examples.html
- Sullivan-Timmermann-White (1999) JF — https://econpapers.repec.org/article/blajfinan/v_3a54_3ay_3a1999_3ai_3a5_3ap_3a1647-1691.htm
- Bajgrowicz-Scaillet (2012) JFE — https://econpapers.repec.org/RePEc:eee:jfinec:v:106:y:2012:i:3:p:473-491 ; full text https://access.archive-ouverte.unige.ch/access/metadata/d1a36296-e8c4-423b-9ed9-9870cfc76d9c/download
- Hsu-Kuan (2005) JFEc — https://ideas.repec.org/a/oup/jfinec/v3y2005i4p606-628.html
- Park-Irwin (2007) JES — https://ideas.repec.org/a/bla/jecsur/v21y2007i4p786-826.html
- Discrete-FDR technical analysis (2004-2015) — https://arxiv.org/abs/1811.06766
- Harvey-Liu-Zhu (2016) RFS — https://www.nber.org/papers/w20592
- Harvey-Liu (2015) JPM "Backtesting" — https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF
- Harvey (2017) JF presidential address — https://people.duke.edu/~charvey/Research/Published_Papers/P131_The_scientific_outlook.pdf
- Chordia-Goyal-Saretto (2020) RFS — https://ideas.repec.org/a/oup/rfinst/v33y2020i5p2134-2179..html
- Novy-Marx, Backtesting strategies based on multiple signals — https://www.nber.org/papers/w21329

**Overfitting and Sharpe inference (T1)**
- Bailey-López de Prado (2014) deflated Sharpe — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 ; https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- Bailey-Borwein-López de Prado-Zhu, PBO — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253 ; https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
- Bailey-Borwein-López de Prado-Zhu (2014) Notices AMS — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659
- Bailey-López de Prado, Sharpe ratio efficient frontier (PSR, MinTRL) — https://www.davidhbailey.com/dhbpapers/sharpe-frontier.pdf
- Arian-Norouzi-Seco, CPCV vs walk-forward — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4686376
- Lo (2002) FAJ — https://traders.studentorg.berkeley.edu/papers/The-Statistics-of-Sharpe-Ratios.pdf ; https://ideas.repec.org/a/taf/ufajxx/v58y2002i4p36-52.html
- Ledoit-Wolf (2008) JEF — https://ideas.repec.org/a/eee/empfin/v15y2008i5p850-859.html
- Politis-White (2004) Econometric Reviews — https://ideas.repec.org/a/taf/emetrv/v23y2004i1p53-70.html
- Wiecki-Campbell-Lent-Stauth, Quantopian 888 algorithms — https://ssrn.com/abstract=2745220

**Replication and decay (T1)**
- Hou-Xue-Zhang (2020) RFS — https://www.nber.org/papers/w23394 ; https://www.nber.org/system/files/working_papers/w23394/w23394.pdf
- Chen-Zimmermann, Open Source Cross-Sectional Asset Pricing — https://www.federalreserve.gov/econres/feds/files/2021-037pap.pdf
- Chen-Zimmermann, Publication Bias — https://www.federalreserve.gov/econres/feds/publication-bias-and-the-cross-section-of-stock-returns.htm
- Jensen-Kelly-Pedersen (2023) JF — https://www.nber.org/papers/w28432 ; https://www.nber.org/system/files/working_papers/w28432/w28432.pdf
- McLean-Pontiff (2016) JF — https://tevgeniou.github.io/EquityRiskFactors/bibliography/AcademicReviewFactor.pdf ; https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365
- Linnainmaa-Roberts (2018) RFS — https://www.nber.org/papers/w22894 ; https://www.nber.org/system/files/working_papers/w22894/w22894.pdf
- Jacobs-Müller (2020) JFE — https://ideas.repec.org/a/eee/jfinec/v135y2020i1p213-230.html
- Chen-Lopez-Lira-Zimmermann — https://arxiv.org/abs/2212.10317

**Costs, implementability and limits to arbitrage (T1/T2)**
- Novy-Marx-Velikov (2016) RFS — https://www.nber.org/papers/w20721 ; https://www.nber.org/system/files/working_papers/w20721/w20721.pdf
- Novy-Marx-Velikov (2019) FAJ, cost mitigation — https://ideas.repec.org/a/taf/ufajxx/v75y2019i1p85-102.html
- Novy-Marx-Velikov (2022) JFE, BAB — https://ideas.repec.org/a/eee/jfinec/v143y2022i1p80-106.html
- Chen-Velikov (2023) JFQA — https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/zeroing-in-on-the-expected-returns-of-anomalies/945133D5A3ECEEAF466AEE91551FD225 ; WP https://www.federalreserve.gov/econres/feds/zeroing-in-on-the-expected-returns-of-anomalies.htm
- Detzel-Novy-Marx-Velikov (2023) JF — https://ideas.repec.org/a/bla/jfinan/v78y2023i3p1743-1775.html
- Frazzini-Israel-Moskowitz, Trading Costs (T2, AQR) — https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs ; https://spinup-000d1a-wp-offload-media.s3.amazonaws.com/faculty/wp-content/uploads/sites/3/2021/08/Trading-Cost.pdf
- Frazzini-Israel-Moskowitz, Trading Costs of Asset Pricing Anomalies — http://spinup-000d1a-wp-offload-media.s3.amazonaws.com/faculty/wp-content/uploads/sites/3/2021/08/Trading-Cost-of-Asset-Pricing-Anomalies.pdf ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2294498
- Patton-Weller (2020) JFE — https://econpapers.repec.org/article/eeejfinec/v_3a137_3ay_3a2020_3ai_3a2_3ap_3a515-549.htm ; WP https://public.econ.duke.edu/~ap172/Patton_Weller_MF_25sep18.pdf
- Shleifer-Vishny (1997) JF — https://ideas.repec.org/a/bla/jfinan/v52y1997i1p35-55.html
- Stambaugh-Yu-Yuan (2012) JFE — https://ideas.repec.org/a/eee/jfinec/v104y2012i2p288-302.html
- Israel-Moskowitz (2013) JFE — https://ideas.repec.org/a/eee/jfinec/v108y2013i2p275-301.html
- Fama-French (2008) JF, Dissecting Anomalies — https://ideas.repec.org/a/bla/jfinan/v63y2008i4p1653-1678.html
- Abdi-Ranaldo (2017) RFS (abstract page only) — https://academic.oup.com/rfs/article/30/12/4437/3982054
- Shumway (1997) JF — https://ideas.repec.org/a/bla/jfinan/v52y1997i1p327-40.html
- Beaver-McNichols-Price (2007) JAE — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=949601

**Behavioral priors and crashes (T1)**
- Barberis-Shleifer-Vishny (1998) JFE — https://ideas.repec.org/a/eee/jfinec/v49y1998i3p307-343.html
- Daniel-Hirshleifer-Subrahmanyam (1998) JF — http://www.kentdaniel.net/papers/published/jf98.pdf
- Hong-Stein (1999) JF — https://ideas.repec.org/a/bla/jfinan/v54y1999i6p2143-2184.html
- Grinblatt-Han (2005) JFE — https://ideas.repec.org/a/eee/jfinec/v78y2005i2p311-339.html
- Daniel-Moskowitz, Momentum Crashes — https://www.nber.org/papers/w20439 ; https://www.nber.org/system/files/working_papers/w20439/w20439.pdf
- Khandani-Lo, August 2007 — https://www.nber.org/papers/w14465

**Korea market structure and data (T1 official / T2 press)**
- FSC press release, short-selling resumption — https://www.fsc.go.kr/eng/pr010101/84220
- KCMI report, short-selling bans — https://www.kcmi.re.kr/common/downloadw?fid=27533&fgu=002001&fty=004003
- Herald Business, 2026 securities transaction tax — https://biz.heraldcorp.com/article/10627001
- OpenDART API guide (rcept_dt) — https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001

**Platform and regulatory documentation (T2)**
- TradingView Pine Script: declaration statements — https://www.tradingview.com/pine-script-docs/language/declaration-statements/ ; strategies — https://www.tradingview.com/pine-script-docs/concepts/strategies/ ; repainting — https://www.tradingview.com/pine-script-docs/concepts/repainting/
- CFTC Regulation 4.41 (eCFR) — https://www.ecfr.gov/current/title-17/chapter-I/part-4/subpart-C/section-4.41

**In-house (local; descriptive, in-sample)**
- QUANTGEN context brief — /home/claude/research_notes/QUANTGEN technical and fundamental signals/00_QUANTGEN_context.md
- Data-lab E7 quick-checks — /home/claude/research_notes/QUANTGEN technical and fundamental signals/E7_quickchecks/ (E7_factor_quickcheck.csv, E7_part2_shortban_regimes.csv, E7_part2_signal_splits.csv, E7_part2_calendar_years_longonly_excess.csv, E7_part2_k200proxy_factor_years.csv, e7_checks_part1_factors.py, e7_checks_part2.py)

### Inferences
- The evidence base is overwhelmingly US. Korea-specific inputs here are limited to official market-structure facts and in-house quick-checks. That is why the protocol leans on data checks D1-D14 rather than on published Korean magnitudes.

### Gaps
- Not opened (403, 404 or 429, or no abstract available): Hansen (2005) JBES; STW (1999) full text; López de Prado (2018) book; "10 Reasons Most ML Funds Fail"; Corwin-Schultz (2012); Politis-Romano (1994); Suhonen-Lennkh-Perez (backtest overfitting in alternative beta); Neely-Weller-Ulrich (2009); the Notices AMS PDF. None of their numbers are used.
- The web search budget was exhausted mid-research. Korean academic studies of anomaly costs and replication, and KRX tick-size and delisting rules, could not be searched.
