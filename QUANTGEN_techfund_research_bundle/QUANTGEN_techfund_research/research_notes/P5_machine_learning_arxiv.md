# P5: Machine learning and AI applied to technical and fundamental return predictors

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

---

## 1. What does ML add over simple linear combinations of technical and fundamental signals?

### Takeaway
In US stocks over 1987-2016, shallow nonlinear ML roughly doubles gross OOS R² and long-short Sharpe against a 3-characteristic OLS, and a nonparametric model lifts hedge-portfolio Sharpe by about 50% over a linear one. Adding many features to a linear model helps little: the elastic net's R² is below OLS-3's. Simple combinations (1/N, Fama-MacBeth composites) are hard to beat when samples are short. ML's edge is interactions and nonlinearity, and it is paid for with data.

### Cited Findings
- **Gu-Kelly-Xiu (GKX, RFS 2020), design.** US stocks, March 1957 to December 2016, about 30,000 stocks (average above 6,200 a month). Features: 94 characteristics, 74 industry dummies and 8 macro variables, combined into 920 predictors. Initial split: training 1957-1974, validation 1975-1986, OOS test 1987-2016 — [GKX, Chicago Booth copy](https://dachxiu.chicagobooth.edu/download/ML.pdf)
- **GKX monthly OOS R², all stocks, gross.** OLS on all features -3.46%; OLS-3 0.16%; PLS 0.27%; PCR 0.26%; elastic net 0.11%; GLM 0.19%; random forest 0.33%; GBRT 0.34%; NN1 0.33%; NN2 0.39%; NN3 0.40%; NN4 0.39%; NN5 0.36% — [GKX NBER w25398 PDF](https://www.nber.org/system/files/working_papers/w25398/w25398.pdf)
- **GKX by size.**
  - Top 1,000 stocks: OLS-3 0.31%, ENet 0.25%, RF 0.63%, GBRT 0.52%, NN3 0.70%.
  - Bottom 1,000 stocks: OLS-3 0.17%, ENet 0.20%, RF 0.35%, GBRT 0.32%, NN3 0.45% — [GKX NBER w25398 PDF](https://www.nber.org/system/files/working_papers/w25398/w25398.pdf)
  - A second automated extraction of the Chicago Booth copy returned different subsample values. Verify against the published RFS Table 1 before quoting.
- **GKX portfolios (OOS 1987-2016, gross).** Neural-network long-short decile Sharpe is 1.35 value-weighted and 2.45 equal-weighted, against 0.61 and 0.83 for OLS-3. The paper does not model transaction costs — [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf)
- **GKX, depth and timing.** Neural-network performance peaks at three hidden layers and then declines. GKX stress that interactions among baseline predictors are what matters. A bottom-up S&P 500 timing strategy built from NN forecasts has OOS Sharpe 0.77 against 0.51 for buy-and-hold (gross) — [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf)
- **Freyberger-Neuhierl-Weber (FNW; NBER WP version of the RFS 2020 paper).**
  - Method and sample: adaptive group LASSO, nonparametric, over 36 characteristics, US July 1963 to June 2015. Many published predictors add no incremental information; 15 of the 36 are selected in the baseline specification.
  - OOS 1991-2014: equal-weighted hedge-portfolio Sharpe 3.42 for the nonparametric model against 2.26 for the linear one (gross).
  - Above the NYSE 20th size percentile, only seven characteristics keep predictive power — [NBER w23227 PDF](https://www.nber.org/system/files/working_papers/w23227/w23227.pdf). The abstract puts the Sharpe gain at about 50% — [NBER w23227](https://www.nber.org/papers/w23227)
- **Chen-Pelger-Zhu (CPZ, Management Science 2024).**
  - Model and data: a GAN-trained no-arbitrage SDF using 46 characteristics and 178 macro series; train 1967-86, validate 1987-91, test 1992-2016.
  - OOS annual Sharpe: 2.6, against 0.42 (linear), 0.50 (elastic net), 0.44 (feed-forward return forecast) and 0.8 (Fama-French 5).
  - The model explains 8% of individual return variation; cross-sectional R² is 23% against 14-15% for the alternatives. Results hold after excluding small and illiquid stocks from the test assets (gross) — [arXiv 1904.00745 PDF](https://arxiv.org/pdf/1904.00745)
- **Kelly-Pruitt-Su IPCA (JFE 2019).** Four latent factors with loadings instrumented by characteristics. Eight characteristics account for nearly all of the model's accuracy, and anomaly intercepts become small and insignificant — [NBER w24540](https://www.nber.org/papers/w24540)
- **Feng-Giglio-Xiu (JF 2020).** Under double-selection testing, most newly proposed factors are redundant. Profitability keeps significant incremental explanatory power — [NBER w25481](https://www.nber.org/papers/w25481)
- **Kozak-Nagel-Santosh (JFE 2020).** A characteristics-sparse SDF cannot summarize the cross-section. A few principal components of characteristic portfolios, with economically motivated shrinkage, do so robustly OOS — [NBER w24070](https://www.nber.org/papers/w24070)
- **Bryzgalova-Pelger-Zhu (JF 2025), asset-pricing trees.** Tree-built cross-sections yield OOS Sharpe up to three times higher than leading reduced-form models. Deciles and long-short anomaly factors are too low a hurdle for testing models — [LBS Research Online](https://lbsresearch.london.edu/id/eprint/1531/)
- **Lewellen (Critical Finance Review 2015).** A plain Fama-MacBeth composite of 15 characteristics with rolling slopes produces expected-return estimates with a cross-sectional SD of 0.87% a month and an OOS predictive slope of 0.74 (SE 0.07) — [now publishers](https://www.nowpublishers.com/article/Details/CFR-0024)
- **DeMiguel-Garlappi-Uppal (RFS 2009).** None of 14 optimizing models across 7 datasets consistently beats 1/N on Sharpe, certainty-equivalent return or turnover. Sample mean-variance needs about 3,000 months of data for 25 assets — [RePEc](https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html)
- **Rapach-Strauss-Zhou (RFS 2010).** Combining individual predictive regressions gives consistent, significant OOS gains over the historical mean, even though the individual predictors fail — [RePEc](https://ideas.repec.org/a/oup/rfinst/v23y2010i2p821-862.html)
- **Israel-Kelly-Moskowitz (JIM 2020).** ML for return prediction is held back by small data, a low signal-to-noise ratio and adaptive, nonstationary markets; economic theory and human expertise remain necessary — [AQR](https://www.aqr.com/Insights/Research/Journal-Article/Can-Machines-Learn-Finance)

### Inferences
- **The baseline drives the headline.** GKX's doubling is measured against OLS-3 (size, book-to-market, momentum). The elastic net, which uses all 920 features, does worse than OLS-3 in R². So "more features, linear" adds little, and "few features with nonlinear interactions" is where the gain sits. No study I found compares GKX-type ML with a rich equal-weight z-score composite of the same features net of costs.
- **R² is not the decision metric.** A monthly OOS R² of 0.3-0.7% can map into a long-short Sharpe above 1, and in Kelly-Malamud-Zhou a strongly negative R² sits beside a positive Sharpe (section 3). QUANTGEN should judge ML only on net portfolio returns.
- **The robust lesson is dimension reduction and shrinkage, not depth.** IPCA, Kozak-Nagel-Santosh, Feng-Giglio-Xiu and asset-pricing trees all point the same way, and the 1/N literature says a learned combiner must beat an equal-weight composite out of sample before it earns a place.

### Gaps
- No direct study of ML against an equal-weight composite net of costs.
- GKX subsample R² extractions conflict (see above). ENet, RF and GBRT portfolio Sharpe ratios in GKX were not extracted.
- The published RFS version of FNW may use a different characteristic set from the 36 in the working paper.

---

## 2. Which features carry the predictive power?

### Takeaway
Across methods and markets, the dominant inputs are:
- price trends (short-term reversal, momentum, industry momentum, 52-week high);
- liquidity and size (market value, dollar volume, spread, turnover);
- volatility and beta.

Fundamentals (valuation, profitability, accruals) matter more at longer horizons, in large caps and outside the US. Valuation stands out in Europe, liquidity in China, and gross profitability and accruals in Korea.

### Cited Findings
- **GKX.** Every method yields a similar ranking. Price-trend variables come first (momentum, industry momentum, short-term reversal), then liquidity (market value, dollar volume, bid-ask spread), then risk (return volatility, idiosyncratic volatility, beta, beta squared). Valuation ratios follow — [GKX](https://dachxiu.chicagobooth.edu/download/ML.pdf)
- **FNW.** The most consistently selected characteristics are short-term reversal, size, closeness to the 52-week high and standardized unexplained volume. Eight characteristics are significant before 1990 and 17 after — [NBER w23227 PDF](https://www.nber.org/system/files/working_papers/w23227/w23227.pdf)
- **CPZ.** Short-term reversal and momentum are the two most important variables, followed by size and value — [arXiv 1904.00745 PDF](https://arxiv.org/pdf/1904.00745)
- **Drobetz-Otto (Journal of Asset Management 2021, Europe).** The most important predictors are price trends and valuation-ratio fundamentals. Neural networks perform best, also after transaction costs — [RePEc](https://ideas.repec.org/a/pal/assmgt/v22y2021i7d10.1057_s41260-021-00237-x.html)
- **Leippold-Wang-Zhou (JFE 2022, China A-shares).** Liquidity is the single most important predictor, unlike in the US — [EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:145:y:2022:i:2:p:64-82)
- **Cakici-Fieberg-Metko-Zaremba (46 markets, 148 characteristics).** The algorithms get most of their predictability from simple, popular factor types: momentum, reversal, value and size. Predictability is stronger in markets with fewer listed firms and higher idiosyncratic risk — [SSRN 4141663](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4141663)
- **Blitz-Hanauer-Hoogteijling-Howard.** ML strategies trained on longer horizons load more on slower signals such as quality and value, which proved more resilient — [Robeco](https://www.robeco.com/en-us/insights/2023/07/the-term-structure-of-machine-learning-alpha)
- **Bang-Kang-Ryu (Finance Research Letters 2024; Korea, KOSPI and KOSDAQ, 2001-2023).** Double-selection LASSO over 28 candidate factors.
  - Gross profitability is the most significant pricing factor.
  - The parsimonious model is gross profitability, percent accruals and long-term momentum.
  - Factors that matter in the US (for example operating profitability) need not matter in Korea — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612324009760)
- **Hou-Xue-Zhang (Replicating Anomalies).** With NYSE breakpoints and value-weighted returns, 95 of 102 liquidity variables (93%) are insignificant — [NBER w23394](https://www.nber.org/papers/w23394)

### Inferences
- **What drives ML's headline R² is the weakest part.** The reversal, liquidity and size interactions behind it are the fastest-decaying, most cost-sensitive and most microcap-dependent inputs. The features that survive value-weighting, large caps and longer horizons are quality/profitability, value, momentum and 52-week high.
- **Design consequence.** QUANTGEN's composite should centre on those robust features. Fast features (1-5 day reversal, volume shocks) belong in separate, cost-gated sleeves, not inside a single combiner whose turnover they would dominate.
- **Conflict to flag.** The prior design gives Korean quality a weight of 1 on the 0-3 scale. Bang-Kang-Ryu find gross profitability is the most significant Korean pricing factor over 2001-2023. Their test is an SDF/pricing test, not a net long-only test, so this is a data-check item for the fundamental panel rather than settled.

### Gaps
- I found no Korea-specific ML study that reports variable importance alongside net-of-cost results. The importance ranking in Choi et al. (2023) was not accessible.

---

## 3. How do ML gains decay after costs, size filters and publication, and does "complexity" help?

### Takeaway
ML long-short gains shrink in stages:
1. gross equal-weighted;
2. value-weighted;
3. excluding microcaps and distressed names;
4. net of costs;
5. after 2004;
6. after publication.

Gains survive mainly when the model is cost-aware or trained on longer horizons. Claims that massively over-parameterized models predict returns better ("virtue of complexity") have been largely explained away as mechanical momentum or volatility timing, or as an artefact of the implementation.

### Cited Findings
- **Avramov-Cheng-Metzker (Management Science 2023).**
  - Deep-learning signals earn their profits in difficult-to-arbitrage stocks and in high limits-to-arbitrage market states.
  - Excluding microcaps, distressed stocks or high-volatility episodes considerably attenuates profitability.
  - Reasonable trading costs make it worse, because of high turnover and extreme positions.
  - The signals stay profitable on the long side and in recent years, with low downside risk — [HUJI CRIS](https://cris.huji.ac.il/en/publications/machine-learning-vs-economic-restrictions-evidence-from-stock-ret/); [SSRN 3450322](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3450322)
- **Blitz-Hanauer-Hoogteijling-Howard (Journal of Financial Data Science 2023).** Common ML models show high full-sample gross alphas, but net of costs their performance after 2004 (2004-2021) is close to zero for 1-month forecasts. Training on 3-, 6- or 12-month horizons and using efficient portfolio rules (lower turnover) gives significant positive net returns — [SSRN 4474637](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4474637); [Robeco](https://www.robeco.com/en-us/insights/2023/07/the-term-structure-of-machine-learning-alpha)
- **Azevedo-Hoegner-Velikov (AFA program paper).**
  - Setup: only post-publication anomalies, January 2005 to December 2021, with costs from a high-frequency effective-spread estimator (about 20-25 bp a month).
  - Results: ML strategies earn net OOS returns of up to 1.42% a month (gross up to 1.63%); costs cut returns by 13-40%; turnover exceeds 50%.
  - An LSTM earns a six-factor alpha of 1.20% a month (t 3.46) — [AFA](https://afajof.org/management/viewp.php?n=75544)
- **Jensen-Kelly-Malamud-Pedersen (forthcoming in RFS).**
  - 1981-2020: Portfolio-ML, which learns portfolio weights with trading costs in the objective, earns a net Sharpe of 1.38 and 19% net excess return.
  - Markowitz-ML has a gross Sharpe of 2.00 but negative net returns.
  - Larger investors face a worse implementable frontier — [AFA](https://afajof.org/management/viewp.php?n=32368); [SFS listing, Dec 2025](https://sfs.org/rfs-forthcoming-paper-123/)
- **DeMiguel-Martin-Utrera-Nogales-Uppal (RFS 2020).** Once costs are included, the number of significant characteristics rises from 6 to 15, because rebalancing trades across characteristics partly cancel — [EconPapers](https://econpapers.repec.org/article/ouprfinst/v_3a33_3ay_3a2020_3ai_3a5_3ap_3a2180-2222..htm)
- **Green-Hand-Zhang (RFS 2017).** Of 94 characteristics, 12 are independent predictors in non-microcaps over 1980-2014, but only 2 since 2003. Hedge returns have been insignificant since 2003 — [RePEc](https://ideas.repec.org/a/oup/rfinst/v30y2017i12p4389-4436..html)
- **Hou-Xue-Zhang.** Of 447 anomalies, 286 (64%) are insignificant at 5% with NYSE breakpoints and value-weighted returns, and 380 (85%) fail a t-cutoff of 3 — [NBER w23394](https://www.nber.org/papers/w23394)
- **Chen-Velikov.** After spreads, post-publication decay and modern trading technology, the average anomaly's expected return is about 8 bp a month. The strongest anomalies earn 10-20 bp after data-mining adjustments — [SSRN 3073681](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681)
- **Arnott-Harvey-Markowitz (JFDS 2019), citing Arnott-Beck-Kalesnik (2016).** Eight popular factors averaged 5.8% a year before publication and 2.4% after. AHM add that even modest costs wipe out the significance of many anomalies — [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf)
- **Kelly-Malamud-Zhou (KMZ, JF 2024), "virtue of complexity".**
  - Data: CRSP value-weighted index 1926-2020 (sample effectively from 1930), 15 Goyal-Welch predictors, up to 12,000 random Fourier features (RFF).
  - With a 12-month training window: OOS timing Sharpe improvement of roughly 0.47 a year (t about 3), even though OOS R² is substantially negative.
  - With 60- and 120-month windows: information ratios about 0.25 (t above 2).
  - Positions behave like a long-only strategy and divest before 14 of 15 NBER recessions; costs are not addressed — [KMZ JF PDF (Yale)](https://economics.yale.edu/sites/default/files/2024-01/The%20Journal%20of%20Finance%20-%202023%20-%20KELLY%20-%20The%20Virtue%20of%20Complexity%20in%20Return%20Prediction%20(1).pdf)
- **Nagel (NBER w34104, 2025).** When features vastly outnumber observations, RFF ridge reduces to kernel regression, a similarity-weighted average of the training returns. Because predictors are persistent and heteroskedastic, it mechanically builds "a volatility-timed momentum strategy".
  - In his replication, RFF earns an information ratio of 0.255 (t 2.42) against 0.388 (t 3.68) for a simple volatility-timed momentum rule.
  - On artificial data with return reversals, the same method earns alpha of -0.143 a year (t -1.84).
  - A wild bootstrap that destroys most predictor information leaves the IR almost unchanged (0.228).
  - With 12,000 features and 12 observations, the maximum achievable noiseless Sharpe is about 0.03 a year — [Nagel PDF](https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/f/575/files/2025/07/Complexity_2.pdf); [BFI WP 2025-104](https://bfi.uchicago.edu/wp-content/uploads/2025/08/BFI_WP_2025-104.pdf)
- **Buncic (SSRN working paper, March 2026).**
  - KMZ's results come from a zero-intercept restriction and an unconventional way of aggregating performance, both of which handicap the simple models.
  - The same "virtue of complexity" pattern appears on simulated i.i.d. (unpredictable) returns.
  - Standard linear models with an intercept give Sharpe ratios up to 40% larger than KMZ's complex models — [danielbuncic.com](https://www.danielbuncic.com/)
- **Fallahgoul (arXiv 2506.03780, 2025).** Standardizing within the sample changes the kernel that RFF approximates. With 12,000 features, 12 observations and an R² of 2-3%, reliable learning needs more than 25-30 years of data, so the OOS success must come from lower-complexity artefacts — [arXiv](https://arxiv.org/abs/2506.03780)
- **Kılıç (Fed FEDS 2025-089; FX, 8 currencies, 1-month horizon).** Ridge-RFF helps only with 12-month windows and still does not beat the random walk consistently. With 120-month windows it is uniformly worse than linear regression — [Federal Reserve](https://www.federalreserve.gov/econres/feds/files/2025089pap.pdf)

### Inferences
- **Size of the decay.** The steps appear to take away most of the headline: Green-Hand-Zhang (post-2003), Blitz et al. (post-2004 net), Chen-Velikov (8 bp a month net) and Arnott-Beck-Kalesnik (5.8% to 2.4%). Azevedo-Hoegner-Velikov is the main counterweight. QUANTGEN's 60% live haircut in gate step 9 is consistent with this picture for any ML combiner.
- **Cost-aware design matters more than model class.** Jensen et al. (gross Sharpe 2.00 turning negative net, against a net 1.38 for the cost-aware version) and DeMiguel et al. (6 to 15 characteristics) say how the combiner trades matters more than which model forecasts.
- **The complexity critique supports the macro panel.** If complex timing models are effectively volatility-timed momentum, the macro panel's decision stands: macro sizes risk and never sets direction, with vol scaling and trend already in place. Nothing here argues for over-parameterized timing models.

### Gaps
- Avramov-Cheng-Metzker's numbers (magnitude of attenuation, turnover) were not accessible beyond the abstract.
- I could not open McLean-Pontiff (2016): 403/429 errors. Their decay percentages, which underpin the gate's 60% haircut, are not verified in these notes.
- I found no published KMZ reply to Nagel or Buncic, and could not open the Economics Letters paper "Is complexity virtuous?" (429). The search budget ran out before more could be tried.

---

## 4. Price-pattern deep learning (CNN, LSTM, order books): does it survive?

### Takeaway
- **Image CNNs on price charts:** strong equal-weighted, modest value-weighted. Weekly versions trade roughly 8-9 times more than monthly ones.
- **Daily LSTM / ensemble stat-arb on S&P 500 constituents:** decayed to about zero net after 2010.
- **Order-book deep learning:** predicts direction at tick horizons, but overfits benchmark datasets and is evaluated without costs.

None of these transfers to a 35 bp per side, decide-at-close, read-only system.

### Cited Findings
- **Jiang-Kelly-Xiu (JKX, JF 2023), image CNN.** US stocks 1993-2019; training and validation 1993-2000, OOS test 2001-2019; gross.
  - Monthly holding, equal-weighted: I5/R20 Sharpe 2.35, I20/R20 2.16, I60/R20 1.29, against MOM 0.25, STR 0.55, WSTR 1.23.
  - Monthly holding, value-weighted: I5/R20 0.45, I20/R20 0.49, I60/R20 0.17, against MOM 0.36, STR 0.03, WSTR 0.30 — [JKX PDF](https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf)
  - Weekly holding, equal-weighted: I5/R5 Sharpe 7.15 (turnover 862%), I20/R5 6.75 (834%), I60/R5 4.89 (774%), against MOM 0.07, STR 1.76, WSTR 2.84.
  - Weekly holding, value-weighted: I5/R5 1.49 (947%), I20/R5 1.74 (910%), I60/R5 1.44 (839%), against MOM 0.33, STR 0.44, WSTR 0.77.
  - Monthly-strategy turnover is about 155-187% (equal-weighted), similar to the reversal strategies.
  - The obvious trend and reversal candidates explain 12% or less of the variation in CNN forecasts.
  - Transferring the US-trained model to 26 foreign markets raises the average country Sharpe from about 0.3 (locally trained) to 0.7 — [JKX PDF](https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf)
- **Fischer-Krauss (EJOR 2018), LSTM on S&P 500 constituents, December 1992 to October 2015, survivor bias removed.** Before costs: 0.46% a day, Sharpe 5.8. Assumed cost is 5 bp per half-turn. The authors write that "as of 2010, excess returns seem to have been arbitraged away", with profitability around zero after costs — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0377221717310652)
- **Krauss-Do-Huck (EJOR 2017; S&P 500 1992-2015; 31 lagged-return features; long top 10, short bottom 10, daily).**
  - Ensemble: 0.45% a day before costs and 0.25% after 5 bp per half-turn; Sharpe 1.81 after costs.
  - By sub-period after costs: above 200% a year (12/1992-03/2001); 22% (04/2001-08/2008, Sharpe 0.51); above 400% (09/2008-12/2009); negative (01/2010-10/2015) — [EconStor WP version](https://www.econstor.eu/bitstream/10419/130166/1/856307327.pdf)
- **Sirignano-Cont (Quantitative Finance 2019).** Deep learning on billions of US equity quotes and trades. A universal model trained on pooled stocks beats asset-specific models, including on stocks outside the training sample, with stable OOS direction-prediction accuracy — [arXiv 1803.06917](https://arxiv.org/abs/1803.06917)
- **DeepLOB (Zhang-Zohren-Roberts, IEEE TSP 2019).** A CNN plus LSTM on limit-order-book data (the FI-2010 benchmark and one year of LSE quotes) is state of the art on the benchmark and generalizes to instruments outside training. The abstract does not mention costs — [arXiv 1808.03668](https://arxiv.org/abs/1808.03668)
- **LOBCAST benchmark (Artificial Intelligence Review 2024).** 15 models re-implemented (13 state-of-the-art plus 2 baselines). The best model scores 82.6% F1 on FI-2010 but about 63% on 2021-22 NASDAQ data; most models score 48-61% on the new data and overfit FI-2010. Its trading simulation charges no transaction costs — [Springer](https://link.springer.com/article/10.1007/s10462-024-10715-4)
- **Jeong-Byun-Kim (Research in International Business and Finance 2026), Korean chart CNN.** KRX OHLCV images, 2000-2023: training 2000-2009, OOS test 2010-2023. I20/R5 long-short earns 56% a year with Sharpe 5.48, against 12% (Sharpe 0.69) for the best benchmark, weekly short-term reversal. The authors say JKX's CNN was significantly weaker in South Korea, which motivated local training. The abstract does not give cost-adjusted figures — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0275531925004878)

### Inferences
- **Cost arithmetic for a weekly KRX long-only strategy (P5's illustration, conventions stated).** Replacing half the book each week means trading 100% of NAV weekly (50% sold, 50% bought). At 35 bp per side that costs 52 × 1.00 × 0.35% ≈ 18% a year, and 36% a year at the 2x stress. That is larger than the entire gross long-short return of the Korean WSTR benchmark (12% a year). A long-short version trades both legs and costs roughly twice as much. A weekly CNN with JKX-like turnover is uneconomic at QUANTGEN's KRX cost schedule unless its net figures prove otherwise.
- **The decay pattern fits the US evidence.** Daily LSTM and RF strategies collapsed around 2010, in line with Blitz et al.'s post-2004 net-zero result for short horizons. Korean daily or weekly deep learning should be presumed to face the same.
- **Order-book models are DROP for QUANTGEN.** They predict mid-price moves over seconds to minutes, which are far smaller than a 35 bp per side cost. QUANTGEN has no order path, and its KIS quote snapshots are not a historical full-depth order book.
- **Pooling is the useful idea.** Sirignano-Cont's universal model and JKX's transfer gains suggest that if QUANTGEN ever trains ML, a model pooled across markets with market-specific shrinkage is better suited to Korea's short samples than a Korea-only deep model.

### Gaps
- JKX's country-level transfer result for Korea (Table IA6 or equivalent) was not in the text I could access.
- No net-of-cost Korean CNN result was found.
- JKX's turnover definition was not checked; the 774-947% figures are reported as given.

---

## 5. Text and LLMs: what is real and what is look-ahead?

### Takeaway
LLM-derived news signals carry real, fast information after the training cutoff. But:
- equal-weighted performance far exceeds value-weighted;
- the signal is absorbed within about two days and is strongest in small stocks and the short leg;
- it decays as adoption rises and dies at about 20 bp costs.

Backtests inside the training window are contaminated: models recall outcomes and leak future events, and masking firm names does not fix it. The honest options are post-cutoff evaluation or point-in-time models.

### Cited Findings
- **Ke-Kelly-Xiu (NBER w26186).** A supervised sentiment model built on Dow Jones Newswires: screen sentiment words, weight them by topic modelling, then aggregate by penalized likelihood. It extracts return-predictive signals — [NBER w26186](https://www.nber.org/papers/w26186)
- **Chen-Kelly-Xiu, "Expected Returns and Large Language Models".**
  - Data: more than 3 million US news articles (1996-2019) plus 16 international markets in 13 languages.
  - Equal-weighted long-short sentiment Sharpe: 4.62 with ChatGPT embeddings, 4.16 LLaMA2, 3.75 RoBERTa, 3.06 Word2vec.
  - LLaMA2 return-prediction portfolios: 5.31 equal-weighted and 1.32 value-weighted (against 4.16 and 0.98 for sentiment).
  - Information is absorbed by the start of day 3. Returns are gross of costs — [paper copy](https://mgmt675-2025.kerryback.com/assets/ExpectedReturns_LLMs.pdf)
- **Lopez-Lira-Tang, version 1 (Oct 2021 to Dec 2022, after ChatGPT's September 2021 cutoff; 50,767 headline-return observations).** Next-day return coefficient on the ChatGPT score is 0.231 (t 4.69) for all stocks, 0.652 (t 5.02) for small stocks and 0.118 for the rest. Basic models (GPT-1, GPT-2, BERT) cannot forecast. No transaction costs — [arXiv v1 PDF](https://arxiv.org/pdf/2304.07619v1)
- **Lopez-Lira-Tang, version 6 (Oct 2021 to May 2024).**
  - Overnight-news long-short: 34 bp a day, Sharpe 2.97 at zero cost; still profitable at 5 and 10 bp, unprofitable at 20 bp. The extraction labelled these as round-trip costs; I have not verified the convention.
  - Annualized Sharpe falls from 6.54 (2021Q4) to 3.68 (2022), 2.33 (2023) and 1.22 (January-May 2024).
  - The short leg on negative news earns 26 bp a day against 8 bp for the long leg — [arXiv v6](https://arxiv.org/html/2304.07619v6)
  - The abstract reports roughly 90% portfolio-day hit rates, but for the non-tradable initial reaction, and links the decline to rising LLM adoption — [arXiv abstract](https://arxiv.org/abs/2304.07619)
- **Glasserman-Lin (arXiv 2309.17322, 2023).**
  - Thomson Reuters S&P 500 headlines (181,908): long-short with original headlines earns 77.27 bp a day in-sample (January 2015 to September 2021, inside GPT-3.5's training window) and 6.07 bp a day OOS (October 2021 to December 2022). With anonymized headlines: 81.64 and 12.23.
  - Scraped headlines: 25.08 against 30.97 in-sample, 16.32 against 11.09 OOS.
  - In-sample, removing firm identifiers helps. The authors attribute this to a "distraction" effect (general firm knowledge interfering with sentiment) that outweighs look-ahead, and it is strongest for large firms — [arXiv PDF](https://arxiv.org/pdf/2309.17322); [arXiv abstract](https://arxiv.org/abs/2309.17322)
- **Sarkar-Vafa (ICML 2025 workshop).**
  - Llama-2 70B, given earnings calls from September-November 2019 and asked about 2020 risks, mentions "COVID-19" in 6.8% of generations; pandemic terms are 3.6 times more frequent than in 2019 predictions.
  - On close US House races (2014-2022) it reaches 70-80% accuracy.
  - Prompting the model to ignore later information does not remove the leakage. With firm names masked, it still recovers firm identity 70% of the time, and its guess of the call year correlates 0.79 with the truth.
  - Their remedy is a family of models with dated pretraining cutoffs — [OpenReview PDF](https://openreview.net/pdf?id=fn9cJkB86T)
- **Gao-Jiang-Yan (arXiv 2512.23847, revised June 2026).** A "Lookahead Propensity" measure is strongly positive inside the training period and collapses to about zero just after the cutoff. LLM forecast power, for news-to-returns and for earnings-call-to-capex, is concentrated in high-propensity firm-dates and disappears after the cutoff — [arXiv](https://arxiv.org/abs/2512.23847)
- **Didisheim-Fraschini-Somoza (Economics Letters 2025).**
  - Asked to recall returns from a ticker and date, GPT models range from almost no recall (individual stocks, daily, small models) to 100% correlation (S&P 500, yearly, GPT-4.1).
  - For the largest model, yearly recall correlates 0.43 against 0.05 for daily.
  - Adding market context raises the share of data that must be excluded from 3.5% to 22% — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0165176525004392)
- **He-Lv-Manela-Wu (arXiv 2502.21206, 2025).** ChronoBERT and ChronoGPT are trained only on text available at each point in time. Their real-time news-return portfolios reach Sharpe ratios comparable to a much larger Llama model, and they find look-ahead bias modest and specific to the model and application — [arXiv](https://arxiv.org/abs/2502.21206)
- **Kong et al. (arXiv 2602.14233, February 2026).** They reviewed 164 LLM-finance papers from 2023-2025 and identify five biases: look-ahead, survivorship, narrative, objective and cost. They write: "No single bias is discussed in more than 28 percent of studies" — [arXiv](https://arxiv.org/abs/2602.14233)

### Inferences
- **Where Chen-Kelly-Xiu's OOS window sits.** Their 1996-2019 window lies inside the pretraining data of the embedding models used. Didisheim et al. find daily single-stock recall weak (0.05), which limits but does not rule out inflation. Glasserman-Lin's in-sample to OOS collapse (77 to 6 bp a day for original headlines) mixes look-ahead, distraction and a regime change, and should be read as a warning about in-window LLM backtests, not as a clean estimate of the bias.
- **For QUANTGEN, daily LLM-news strategies on KRX stocks are DROP.** At 35 bp per side they would need to be several times more profitable than the US strategy that already fails at 20 bp.
- **A slower LLM feature is a possible later item.** For example, LLM scoring of OpenDART filings (주요사항보고서, annual-report text) into monthly features. It would have to be evaluated strictly after the cutoff of the exact model version used, or with a point-in-time model, and the post-cutoff window is currently short (a few years). BACKLOG.

### Gaps
- Ke-Kelly-Xiu's portfolio statistics were not extracted.
- I found no Korean-language LLM return-prediction study in a peer-reviewed venue.
- The "Scaling Point-in-Time Language Models" preprint (arXiv 2607.11889) could not be read; the fetch returned no text.

---

## 6. Typical flaws and leakage traps in ML/LLM backtests, including arXiv technical-indicator papers

### Takeaway
The applied ML stock-prediction literature often does without trading backtests, transaction costs and bias controls. It frequently evaluates on accuracy, F1 or RMSE rather than net returns, and leakage is a documented cross-disciplinary failure. Treat any arXiv technical-indicator ML paper as unverified until it passes a leakage checklist.

### Cited Findings
- **Olorunnimbe-Viktor (Artificial Intelligence Review 2022).** Of 185 initial search hits on deep learning for stock markets, only 35 papers explicitly reported backtesting.
  - Many papers use only ML metrics (accuracy, F-score).
  - Most treat the problem as offline learning, which the authors call flawed.
  - Financial series are not i.i.d., and proper testing needs long or multiple periods — [d-nb.info PDF](https://d-nb.info/1265952744/34)
- **Kapoor-Narayanan (Patterns 2023).** Leakage-related reproducibility failures, documented in 41 papers across 30 fields, affect 648 papers. Their taxonomy of leakage types:
  1. no clean train/test split;
  2. illegitimate features;
  3. a test set from the wrong distribution;
  4. temporal leakage;
  5. preprocessing on combined train and test data;
  6. feature selection on train and test together;
  7. duplicates across the split;
  8. sampling bias.

  After fixing leakage in civil-war prediction, complex ML did no better than logistic regression — [Princeton reproducibility project](https://reproducible.cs.princeton.edu/)
- **Arnott-Harvey-Markowitz (JFDS 2019), backtesting protocol.** Key points:
  - Pre-specify the sample, transformations, winsorization and outlier rules.
  - Record every test and interaction tried.
  - Hold back true OOS data; live trading is the only true OOS test.
  - Include costs.
  - Beware nonstationarity and crowding.
  - Demand interpretability.
  - Require that a more elaborate ML model win by an economically significant margin.
  - They report a researcher calling tuning 10 hyperparameters with k-fold cross-validation on 50 years of returns a terrible idea — [Duke PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf)
- **LOBCAST.** Models tuned on the FI-2010 benchmark lose about 20 F1 points on new data, and the published simulation ignores costs — [Springer](https://link.springer.com/article/10.1007/s10462-024-10715-4)
- **Metric confusion, two examples.** Lopez-Lira-Tang's roughly 90% hit rates refer to the non-tradable initial reaction — [arXiv](https://arxiv.org/abs/2304.07619). KMZ's strategies have strongly negative OOS R² but positive Sharpe — [KMZ](https://economics.yale.edu/sites/default/files/2024-01/The%20Journal%20of%20Finance%20-%202023%20-%20KELLY%20-%20The%20Virtue%20of%20Complexity%20in%20Return%20Prediction%20(1).pdf)
- **Kong et al.** Five biases (look-ahead, survivorship, narrative, objective, cost) compound to create an illusion of validity, and none is addressed in more than 28% of 164 recent LLM-finance papers — [arXiv](https://arxiv.org/abs/2602.14233)

### Inferences: P5 leakage checklist for QUANTGEN (each item is a gate pre-condition for any ML card)
1. **Split by time only.** No random K-fold across dates. Purge any training sample whose label window overlaps the test window, and embargo for at least the label horizon (21 or 63 sessions), consistent with gate step 1.
2. **Fit preprocessing inside training windows.** Scalers, winsorization, PCA and feature selection are fitted on training data only, or cross-sectionally per date (rank transforms use same-date data only).
3. **Point-in-time fundamentals.** OpenDART values become available at the receipt date (rcept_dt) plus one session. Use as-first-reported values, not later restatements.
4. **Survivorship-free universe.** Include delisted stocks and their final returns. The data lab's marcap set is survivorship-free.
5. **Align markets by clock time.** At the KRX close of day t, the last completed US session is US date t−1. US session t has not happened yet. Calendar-date joins of US and KRX data leak information (see DC5).
6. **Respect publication times for flows and short-sale data.** If investor-type flows or short-sale data for day t are published after the KRX close, lag them one session.
7. **Corporate actions.** Build adjusted prices so that no future adjustment factor enters past features.
8. **Count every configuration as a trial.** Every model, feature set and hyperparameter setting is a trial for the deflated Sharpe (step 3) and the PBO/CSCV test (step 4). Pre-register small grids.
9. **Report net results.** Use 35/70 bp per side (KRX stocks) and 50/100 bp (US via KIS), with turnover reported.
10. **Decide on portfolio metrics.** Net return, Sharpe and IR decide; accuracy, F1, RMSE and hit rates never do.
11. **LLM features.** Test only after the exact model's pretraining cutoff, or use point-in-time models. Run a look-ahead propensity diagnostic; anonymization is not sufficient.
12. **Mandatory benchmarks.** Equal-weight composite, buy-and-hold KOSPI200, and a simple reversal-or-momentum rule.

### Gaps
- I found no source that counts how many arXiv technical-indicator ML papers use random train/test splits or ignore survivorship. The flaws are documented qualitatively and through the leakage taxonomy, not as prevalence rates for this subgenre.
- López de Prado's "10 reasons most ML funds fail" and Bailey et al.'s "Pseudo-mathematics" could not be opened (pages blocked).

---

## 7. Korea and Asia ML evidence

### Takeaway
Peer-reviewed Korea-specific ML evidence is thin and almost entirely gross of costs. Tree boosting (LightGBM/GBRT) tends to be the best model, chart CNNs report very high gross Sharpe, and LASSO selection points to gross profitability, accruals and long-term momentum. Some results carry red flags. Regional evidence (China, 32 emerging markets, 46 markets) suggests ML has more room, including net of costs, in less efficient, retail-heavy markets, but the gains come from simple factor families.

### Cited Findings
- **Choi, Jang, Kim, Park, Park, Song (Journal of the Korean Statistical Society 53(1), 2024, online December 2023; listed on Korea University's research portal).**
  - Monthly Korean stock returns forecast with linear, tree, neural-network and learning-to-rank models, using up to about 29 feature columns.
  - LightGBM and GBRT beat the other models when one model is used for the whole test period; switching models each year did worse.
  - They propose a validation metric based on the cumulative net return of the predicted top-10% portfolio (CRP10). The accessible text gives no R², Sharpe or cost figures — [Springer](https://link.springer.com/article/10.1007/s42952-023-00245-0); [Korea University Pure](https://pure.korea.ac.kr/en/publications/return-prediction-by-machine-learning-for-the-korean-stock-market/)
- **Jeong-Byun-Kim (RIBAF 2026), Korean chart CNN.** OOS 2010-2023: I20/R5 long-short 56% a year, Sharpe 5.48, against weekly reversal at 12% a year (Sharpe 0.69); gross, net figures unclear — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0275531925004878)
- **Bang-Kang-Ryu (FRL 2024; KOSPI and KOSDAQ, 2001-2023).** Double-selection LASSO over 28 factors. Gross profitability is the most significant factor; the parsimonious model is gross profitability, percent accruals and long-term momentum — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612324009760)
- **Chun-Kang-Kim (Financial Innovation 2024).** Index-level daily forecasts, January 2007 to August 2020, OOS from January 2012, 137 macro and market indicators. OOS R² for KOSPI with LASSO is 16.68%; S&P 500 4.98%; KRW/USD 24.29% (elastic net and LASSO). A global portfolio reaches Sharpe 3.45-3.48 against 0.56 for a US benchmark. Transaction costs are not addressed — [Springer](https://link.springer.com/article/10.1186/s40854-024-00648-w)
- **Leippold-Wang-Zhou (JFE 2022, China).** Liquidity is the top predictor. Retail investors' dominance raises short-term predictability, especially for small stocks. Large stocks and state-owned enterprises are highly predictable over longer horizons. OOS performance stays economically significant after transaction costs — [EconPapers](https://econpapers.repec.org/RePEc:eee:jfinec:v:145:y:2022:i:2:p:64-82)
- **Hanauer-Kalsbach (Emerging Markets Review 2023).** 32 emerging markets, July 1995 to December 2021, OOS January 2002 to December 2021, 36 characteristics. ML beats linear models OOS. Significant net returns remain after costs, short-selling constraints and restricting to big stocks. Higher predictability in harder-to-arbitrage stocks is less pronounced for nonlinear models — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1566014123000274)
- **Cakici et al.** Across 46 markets, ML predictability comes mainly from momentum, reversal, value and size, and is stronger where there are fewer listed firms and idiosyncratic risk is higher — [SSRN 4141663](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4141663)
- **JKX transfer.** The US-trained CNN lifts the average foreign-market Sharpe from about 0.3 to 0.7 across 26 markets — [JKX PDF](https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf). Jeong-Byun-Kim describe the JKX CNN as significantly weaker in Korea — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0275531925004878)

### Inferences
- **Chun-Kang-Kim's 16.68% daily KOSPI R² is a red flag.** It is implausibly high for a tradable close-to-close forecast and is consistent with the cross-market timing trap in checklist item 5. I have not proven this; DC5 tests it directly.
- **The Korean CNN's 5.48 Sharpe is gross and weekly.** Under QUANTGEN's schedule it should be presumed largely consumed by costs until net figures are shown (section 4 arithmetic).
- **Korea's mix may favour ML more than US large caps.** The combination of retail-heavy trading and concentrated large caps resembles the China and emerging-market settings where ML survived costs. But the gains there come from simple factor families, which a linear composite already captures.

### Gaps
- "The effect of portfolio size on return prediction in the Korean stock market" (Journal of the Korean Statistical Society 2026) could not be opened: the fetch was rate-limited.
- I found no Korean ML study with net results at about 35 bp per side, and no Japan or Taiwan ML cross-section study within the search budget.

---

## 8. Where and when it failed (mandatory: dated episodes)

### Takeaway
ML and AI return-prediction failures cluster in three patterns:
- decay after about 2003-2010 in liquid US markets once costs are charged;
- collapse when the model is moved off its training regime or benchmark dataset;
- crowding events and look-ahead artefacts that make backtests unrepeatable.

### Cited Findings

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

### Inferences
- The recurring failure mechanism is a fast signal plus turnover plus a modern cost or liquidity regime. ML models that load on short-term reversal and liquidity inherit the crowding risk of August 2007 and the post-2010 decay.
- A model that looks excellent on a benchmark dataset or inside an LLM's training window should be expected to lose a large fraction of its edge on genuinely new data (rows 7 and 8).

### Gaps
- I found no dated Korean ML failure episode, such as a live Korean ML fund drawdown, in peer-reviewed sources.
- The 2009 momentum crash is relevant to ML models that load on momentum but is covered by the macro panel.

---

## 9. QUANTGEN translation: model choice, required protocol, BUILD vs BACKLOG, expected net uplift

### Takeaway
- **BUILD now:**
  - the equal-weight z-score composite (technical plus fundamental) as the first stock-level card;
  - a ridge or rolling Fama-MacBeth challenger shrunk toward the prior per-market weights;
  - an ML-grade harness: purged and embargoed walk-forward, trial counting, cost-aware evaluation and turnover controls.
- **BACKLOG:** gradient-boosting and neural combiners as non-gating shadow challengers with explicit promotion criteria.
- **DROP:** daily deep sequence, image, order-book and LLM-news strategies for KRX stocks at current costs.
- **Expected uplift (P5 judgment).** Net uplift of a GBRT or neural combiner over the composite in liquid KRX stocks is about 0 to +0.01 IR (plausible range -0.15 to +0.10) before the 60% live haircut, and about zero after it. That is undetectable by the gate with the data available.

### Cited Findings (inputs to the decision)
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

### Inferences

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

### Data-check requests (exact tests for the data lab)
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

### Gaps
- No pre-2015 point-in-time Korean fundamentals are in QUANTGEN's data list. Commercial sources would be needed for a longer fundamental history.
- The uplift estimate in (f) is P5's judgment from US, emerging-market and Chinese evidence plus stated assumptions. No Korean net-of-cost ML-against-composite study exists to anchor it.
- The data lab's datasets contain no fundamentals, so fundamental-feature ML cannot be data-checked until OpenDART data is assembled.

---

## 10. Claims ledger

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

## 11. Source list

**Cross-sectional ML and asset pricing**
- Gu, Kelly, Xiu, Empirical Asset Pricing via Machine Learning (RFS 2020): https://dachxiu.chicagobooth.edu/download/ML.pdf ; https://www.nber.org/system/files/working_papers/w25398/w25398.pdf
- Freyberger, Neuhierl, Weber, Dissecting Characteristics Nonparametrically (RFS 2020; NBER w23227): https://www.nber.org/papers/w23227 ; https://www.nber.org/system/files/working_papers/w23227/w23227.pdf
- Chen, Pelger, Zhu, Deep Learning in Asset Pricing (Management Science 2024): https://arxiv.org/abs/1904.00745 ; https://arxiv.org/pdf/1904.00745
- Kelly, Pruitt, Su, Characteristics Are Covariances (JFE 2019; NBER w24540): https://www.nber.org/papers/w24540
- Feng, Giglio, Xiu, Taming the Factor Zoo (JF 2020; NBER w25481): https://www.nber.org/papers/w25481
- Kozak, Nagel, Santosh, Shrinking the Cross-Section (JFE 2020; NBER w24070): https://www.nber.org/papers/w24070
- Bryzgalova, Pelger, Zhu, Forest Through the Trees (JF 2025): https://lbsresearch.london.edu/id/eprint/1531/
- Leippold, Wang, Zhou, Machine Learning in the Chinese Stock Market (JFE 2022): https://econpapers.repec.org/RePEc:eee:jfinec:v:145:y:2022:i:2:p:64-82
- Lewellen, The Cross-section of Expected Stock Returns (CFR 2015): https://www.nowpublishers.com/article/Details/CFR-0024
- DeMiguel, Garlappi, Uppal, Optimal Versus Naive Diversification (RFS 2009): https://ideas.repec.org/a/oup/rfinst/v22y2009i5p1915-1953.html
- Rapach, Strauss, Zhou, Out-of-Sample Equity Premium Prediction (RFS 2010): https://ideas.repec.org/a/oup/rfinst/v23y2010i2p821-862.html
- Israel, Kelly, Moskowitz, Can Machines "Learn" Finance? (JIM 2020): https://www.aqr.com/Insights/Research/Journal-Article/Can-Machines-Learn-Finance
- Drobetz, Otto, Empirical Asset Pricing via ML: Evidence from Europe (JAM 2021): https://ideas.repec.org/a/pal/assmgt/v22y2021i7d10.1057_s41260-021-00237-x.html
- Hanauer, Kalsbach, ML and the Cross-Section of Emerging Market Stock Returns (EMR 2023): https://www.sciencedirect.com/science/article/abs/pii/S1566014123000274
- Cakici, Fieberg, Metko, Zaremba, Machine Learning Goes Global (SSRN 4141663): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4141663

**Costs, decay, critiques**
- Avramov, Cheng, Metzker, ML vs. Economic Restrictions (Management Science 2023): https://cris.huji.ac.il/en/publications/machine-learning-vs-economic-restrictions-evidence-from-stock-ret/ ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3450322
- Blitz, Hanauer, Hoogteijling, Howard, The Term Structure of ML Alpha (JFDS 2023): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4474637 ; https://www.robeco.com/en-us/insights/2023/07/the-term-structure-of-machine-learning-alpha
- Azevedo, Hoegner, Velikov, The Expected Returns on ML Strategies (AFA program): https://afajof.org/management/viewp.php?n=75544
- Jensen, Kelly, Malamud, Pedersen, ML and the Implementable Efficient Frontier (RFS forthcoming): https://afajof.org/management/viewp.php?n=32368 ; https://sfs.org/rfs-forthcoming-paper-123/ ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4187217 ; https://www.aqr.com/Insights/Research/Working-Paper/Machine-Learning-and-the-Implementable-Efficient-Frontier
- DeMiguel, Martin-Utrera, Nogales, Uppal, A Transaction-Cost Perspective on the Multitude of Firm Characteristics (RFS 2020): https://econpapers.repec.org/article/ouprfinst/v_3a33_3ay_3a2020_3ai_3a5_3ap_3a2180-2222..htm
- Green, Hand, Zhang (RFS 2017): https://ideas.repec.org/a/oup/rfinst/v30y2017i12p4389-4436..html
- Hou, Xue, Zhang, Replicating Anomalies (NBER w23394): https://www.nber.org/papers/w23394
- Chen, Velikov, Zeroing in on the Expected Returns of Anomalies (SSRN): https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3073681
- Arnott, Harvey, Markowitz, A Backtesting Protocol in the Era of ML (JFDS 2019): https://people.duke.edu/~charvey/Research/Published_Papers/P138_A_backtesting_protocol.pdf
- Kelly, Malamud, Zhou, The Virtue of Complexity in Return Prediction (JF 2024): https://economics.yale.edu/sites/default/files/2024-01/The%20Journal%20of%20Finance%20-%202023%20-%20KELLY%20-%20The%20Virtue%20of%20Complexity%20in%20Return%20Prediction%20(1).pdf ; https://economics.yale.edu/research/virtue-complexity-return-prediction
- Nagel, Seemingly Virtuous Complexity in Return Prediction (NBER w34104; BFI WP 2025-104): https://bpb-us-w2.wpmucdn.com/voices.uchicago.edu/dist/f/575/files/2025/07/Complexity_2.pdf ; https://bfi.uchicago.edu/wp-content/uploads/2025/08/BFI_WP_2025-104.pdf ; https://www.nber.org/papers/w34104
- Buncic, Simplified: A Closer Look at the Virtue of Complexity (SSRN WP, March 2026; summary on author site): https://www.danielbuncic.com/
- Fallahgoul, High-Dimensional Learning in Finance (arXiv 2506.03780): https://arxiv.org/abs/2506.03780
- Kılıç, Virtue or Mirage? Complexity in Exchange Rate Prediction (FEDS 2025-089): https://www.federalreserve.gov/econres/feds/files/2025089pap.pdf
- Khandani, Lo, What Happened to the Quants in August 2007? (NBER w14465): https://www.nber.org/papers/w14465

**Price-pattern deep learning**
- Jiang, Kelly, Xiu, (Re-)Imag(in)ing Price Trends (JF 2023): https://www.aidf.nus.edu.sg/wp-content/uploads/2022/02/Xiu-Re-Imagining-Price-Trends.pdf
- Fischer, Krauss, LSTM networks for financial market predictions (EJOR 2018): https://www.sciencedirect.com/science/article/abs/pii/S0377221717310652
- Krauss, Do, Huck, DNN, GBT, RF: Statistical arbitrage on the S&P 500 (EJOR 2017; WP version): https://www.econstor.eu/bitstream/10419/130166/1/856307327.pdf
- Sirignano, Cont, Universal Features of Price Formation (Quantitative Finance 2019): https://arxiv.org/abs/1803.06917
- Zhang, Zohren, Roberts, DeepLOB (IEEE TSP 2019): https://arxiv.org/abs/1808.03668
- LOBCAST benchmark, LOB-based deep learning models (Artificial Intelligence Review 2024): https://link.springer.com/article/10.1007/s10462-024-10715-4

**Text and LLMs**
- Ke, Kelly, Xiu, Predicting Returns with Text Data (NBER w26186): https://www.nber.org/papers/w26186
- Chen, Kelly, Xiu, Expected Returns and Large Language Models: https://mgmt675-2025.kerryback.com/assets/ExpectedReturns_LLMs.pdf
- Lopez-Lira, Tang, Can ChatGPT Forecast Stock Price Movements?: https://arxiv.org/abs/2304.07619 ; https://arxiv.org/pdf/2304.07619v1 ; https://arxiv.org/html/2304.07619v6
- Glasserman, Lin, Assessing Look-Ahead Bias in GPT Sentiment (arXiv 2309.17322): https://arxiv.org/abs/2309.17322 ; https://arxiv.org/pdf/2309.17322
- Sarkar, Vafa, Lookahead Bias in Pretrained Language Models (ICML 2025 workshop): https://openreview.net/pdf?id=fn9cJkB86T
- Gao, Jiang, Yan, Detecting Lookahead Bias in LLM Forecasts (arXiv 2512.23847): https://arxiv.org/abs/2512.23847
- He, Lv, Manela, Wu, Chronologically Consistent LLMs (arXiv 2502.21206): https://arxiv.org/abs/2502.21206
- Didisheim, Fraschini, Somoza, AI's predictable memory in financial analysis (Economics Letters 2025): https://www.sciencedirect.com/science/article/pii/S0165176525004392
- Kong et al., Evaluating LLMs in Finance Requires Explicit Bias Consideration (arXiv 2602.14233): https://arxiv.org/abs/2602.14233

**Methodology and flaws**
- Olorunnimbe, Viktor, Deep learning in the stock market: systematic survey (AIR 2022): https://d-nb.info/1265952744/34
- Kapoor, Narayanan, Leakage and the reproducibility crisis in ML-based science (Patterns 2023): https://reproducible.cs.princeton.edu/

**Korea**
- Choi et al., Return prediction by ML for the Korean stock market (JKSS 2023/2024): https://link.springer.com/article/10.1007/s42952-023-00245-0 ; https://pure.korea.ac.kr/en/publications/return-prediction-by-machine-learning-for-the-korean-stock-market/
- Jeong, Byun, Kim, Image-based CNN return forecasts: evidence from Korea (RIBAF 2026): https://www.sciencedirect.com/science/article/abs/pii/S0275531925004878
- Bang, Kang, Ryu, Potential pricing factors in the Korean market (FRL 2024): https://www.sciencedirect.com/science/article/abs/pii/S1544612324009760
- Chun, Kang, Kim, Forecasting returns with ML: Korean and US markets (Financial Innovation 2024): https://link.springer.com/article/10.1186/s40854-024-00648-w
- OpenDART API guide, single-company key accounts (data from 2015): https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS003&apiId=2019016

**Could not be opened (cited only as gaps):** McLean-Pontiff 2016 (SSRN/Wiley 403/429); Economics Letters "Is complexity virtuous?" (429); Korean portfolio-size paper, JKSS 2026 (rate-limited); López de Prado "10 reasons" (content not available); Bailey et al. "Pseudo-mathematics" (403); arXiv 2607.11889 (no text returned).
