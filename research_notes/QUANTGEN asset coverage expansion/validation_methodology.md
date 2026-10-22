# Validation protocol for strategies and distributional models in QUANTGEN

Scope: what a personal quant app must check, out of sample, before a trading strategy or a
predictive-distribution (risk) model is embedded; grounded first in the user's own study
materials, then in the standard literature; ending with one concrete gate (statistics,
formulas, thresholds, minimum samples, PASS / REVISE / REJECT) and a model-card schema.

Conventions. "Lec N" = UC Berkeley *Introduction to Time Series* (Tibshirani, Fall 2023) lecture
PDF in `C:\Users\whydi\iCloudDrive\퀀트 학습 자료\Introduction to Time Series (UC Berkeley)\`;
page numbers are the PDF's own printed page numbers. "STAT248" = *Applied Time Series - Full
Lecture Notes.pdf* (printed page numbers = PDF page numbers). "CS229" = `main_notes.pdf`
(printed page p = PDF page p+1). "MTSA" = Kirchgässner–Wolters–Hassler, *Modern Time Series
Analysis*, 2nd ed., Springer (printed pages). All PDFs were read by text extraction (pypdf);
the PDF renderer is not installed on this machine, so no page was viewed as an image.
Where a formula could not be confirmed against a primary text it is marked **UNVERIFIED**.

---

## What do the user's own materials teach about out-of-sample validation?

### Takeaway
The folder already contains every principle the gate needs: selection by training error
"does not work" and must be replaced by hold-out or k-fold validation (CS229); for time series
the fold is a *rolling origin* and the *entire procedure* (including any model/parameter
selection) must be re-run at every origin (Lec 6); a distributional forecast is scored on
empirical coverage and PIT calibration, with an online quantile-tracking fix (Lec 8 §3);
in-sample criteria (AIC) are only an asymptotic proxy for out-of-sample log-likelihood and a
held-out set is the direct estimate, with an explicit noise/bias trade-off (STAT248 §21–22);
Mincer–Zarnowitz, RMSE, MAE, Theil's U are the classical point-forecast scores and the book
cites Diebold–Mariano but does not present it (MTSA §2.4.3); the user's own roadmap already
names purged/embargoed CV, the t≈3 hurdle, the deflated Sharpe ratio and fixed-seed
reproducibility as the required vocabulary; and the user's own note warns that P-tail
estimates "need decades of data".

### Cited Findings

**CS229 §9.3 "Model selection via cross validation" (printed pp. 139–142, PDF 140–143)**
- Selecting the hypothesis with the smallest *training* error: "This algorithm does not work"; the higher-degree polynomial always wins in-sample — [CS229 main_notes.pdf p. 140](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/CS229(Machine%20Learning,%20Stanford)/main_notes.pdf)
- Hold-out cross validation: split S into S_train (≈70 %) and S_cv (≈30 %); train each model on S_train; pick the smallest validation error; "somewhere between 1/4–1/3 of the data" for the hold-out set, smaller fractions acceptable when the absolute validation count is "decent" — [CS229 p. 140](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/CS229(Machine%20Learning,%20Stanford)/main_notes.pdf)
- k-fold: k disjoint subsets, train on k−1, test on the k-th, average; "A typical choice ... k = 10"; leave-one-out when data are "really scarce"; CV "can also be used more simply to evaluate a single model" — [CS229 pp. 141–142](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/CS229(Machine%20Learning,%20Stanford)/main_notes.pdf)
- The bias–variance framing: CV is the tool for "a good tradeoff between the twin evils of bias and variance" (p. 139).

**Berkeley Lec 4 (regularization)**
- Tuning λ for ridge/lasso in a forecasting problem: "use time series cross-validation!" (p. 6); for smoothing (a retrospective task) the folds are structured, "every 5th point", not random (p. 10) — [Lecture004.pdf](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/Introduction%20to%20Time%20Series%20(UC%20Berkeley)/Lecture004.pdf)

**Berkeley Lec 6 (ARIMA: model building, residual checks, TS-CV)**
- Model-building steps: 0 plot/transform; 1 difference to stationarity; 2 ACF/PACF for orders; 3 "Fit an ARMA model, inspect the residuals: they should look like white noise" (p. 12) — [Lecture006.pdf](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/Introduction%20to%20Time%20Series%20(UC%20Berkeley)/Lecture006.pdf)
- "an ARMA model is useful if it predicts well. And as before, we can assess this with time series cross-validation" (p. 12); AICc is offered by software but "if we cared about prediction, then we should probably just use time series cross-validation" (p. 19).
- §5.2 defines split-sample MSE = (1/(n−t₀)) Σ_{t>t₀} (x̂_t − x_t)² and time-series CV MSE = (1/(n−t₀)) Σ_{t>t₀} (x̂_{t|t−h} − x_t)², retraining at each t (p. 21).
- "Cross-validation evaluates the prediction error of an entire procedure. Thus the entire procedure must be rerun each time predictions are to be validated" — the *wrong way* is to select the order once on all data and apply it retrospectively, "since we would have used the future at t > t₀" (pp. 21–22).
- Occam's razor: among models with similar CV error prefer the simplest (p. 22).
- §5.3: neither the Gaussian nor the bootstrap prediction interval is "guaranteed to actually give coverage in practice" (p. 22).

**Berkeley Lec 8 §3 (calibration of predictive distributions)**
- Empirical coverage in a TS-CV sense: Coverage = (1/(n−t₀)) Σ_{t=t₀+1}^{n} 1{x_t ∈ I^{1−α}_{t|t−h}}, target ≈ 1−α; "traditional methods ... will not always yield empirical coverage that hovers around the nominal level" (p. 9) — [Lecture008.pdf](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/Introduction%20to%20Time%20Series%20(UC%20Berkeley)/Lecture008.pdf)
- §3.1 quantile tracking (Angelopoulos, Candès, Tibshirani 2023): q̂_{t+1} = q̂_t + η(1−α) if the interval missed, q̂_t − ηα if it covered; long-run coverage → 1−α "with no assumptions on the distribution of the data" provided errors are bounded (p. 10).
- §3.2 PIT calibration: the forecaster is PIT-calibrated if the empirical distribution of F_t(x_t) converges to Unif(0,1); equivalently (1/T) Σ 1{F_t(x_t) ≤ τ} → τ for all τ; PIT histogram U-shaped ⇒ underdispersed (fan too narrow), inverted-U ⇒ overdispersed (p. 11); PIT calibration "is even stronger than coverage of prediction intervals" (p. 11).

**STAT248 (AIC, MLE asymptotics, sandwich, AIC vs held-out)**
- AIC(M) := −2 × (maximised log-likelihood) + 2 × (number of parameters) (§21.2, p. 96; §22.1 eq. 144, p. 106) — [Applied Time Series - Full Lecture Notes.pdf](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/STAT248(UC%20Berkeley)/Applied%20Time%20Series%20-%20Full%20Lecture%20Notes.pdf)
- The in-sample average log-likelihood is biased upward for the out-of-sample quantity ∫ f* log p_θ̂ "especially ... if p_θ is a complicated model which overfits" (§21.2.2, p. 98).
- Well-specified MLE: √n(θ̂_n − θ*) → N(0, I(θ*)⁻¹), I = score covariance = −E[Hessian] (§21.2.3, pp. 99–100). Misspecified: θ* is the KL-closest parameter and the limiting covariance "is not simply the inverse of the Fisher Information" (pp. 100–101).
- §22.1 (p. 106): AIC "arises in the process of estimation of the out-of-sample accuracy"; the direct estimate is (1/m) Σ log p_θ̂(ỹ_j) on independent data; without new data one splits the sample — "If the test dataset is too small, the estimate will be noisy. On the other hand, if the training dataset set is too small, the MLE ... will be quite different from the MLE calculated on the full dataset ... which create bias".

**인공지능경제분석 tut03_cv.R and tut03_cv_bulletin.md**
- The course scheme: forward-stepwise selection with 3-fold CV over 19 regressors on a stacked cross-section (df14 + df15, 446 rows); folds are assigned *randomly* (`set.seed(1); sample(rep(1:nfolds, ...))`) but *grouped by region* so a region's two years never straddle train/validation ("누수(leakage) 방지"); the chosen size k is re-fitted on all data; a one-year-ahead "rehearsal" (train df14 → test df15) reports RMSE 48.98 vs naive 53.24 — [tut03_cv.R](file:///C:/Users/whydi/iCloudDrive/26년%202학기%20수업자료/인공지능경제분석/tut03_cv.R)
- The bulletin records the fragility: "k = 3 chosen in 31 of 50 seeds; 3 folds are noisy", "Test-set discipline: Test-run RMSE is for reporting only, not for choosing k" — [tut03_cv_bulletin.md](file:///C:/Users/whydi/iCloudDrive/26년%202학기%20수업자료/인공지능경제분석/tut03_cv_bulletin.md)

**계량2 MTSA §2.4.3 "Evaluation of Forecasts" (pp. 85–88) and §5.3 / ch. 6**
- Predictability P(τ)² = V[x̂_t(τ)]/V[x_{t+τ}] = 1 − V[f_t(τ)]/V[x_{t+τ}] (2.62), valid for optimal forecasts; for empirical forecasts "P(τ)² might even become negative for 'bad' forecasts" (p. 86) — [Modern Time Series Analysis, 2nd, Springer.pdf](file:///C:/Users/whydi/iCloudDrive/26년%202학기%20수업자료/계량2/Modern%20Time%20Series%20Analysis,%202nd,%20Springer.pdf)
- Mincer–Zarnowitz (2.63): regress x_{t+τ} = a₀ + a₁ x̂_t(τ) + ε; forecasts are "consistent" if a₀ = 0, a₁ = 1; "the usual F and t tests can only be used for τ = 1. For τ > 1, the MA(τ−1) process of the forecast errors has to be taken into account" (pp. 86–87).
- MAE(τ), RMSE(τ) and Theil's U(τ) = RMSE of forecast / RMSE of the naïve "no-change" forecast; U < 1 beats naïve (pp. 87–88).
- The book's references for §2.4 list "Francis X. Diebold and Roberto S. Mariano, Comparing Predictive Accuracy, JBES 13 (1995), pp. 253–263" (p. 92) but the DM statistic itself is not derived anywhere in the book (a text search for "Mariano" hits only the reference list and index).
- §5.3 Unit Root Tests pp. 165–181: Dickey–Fuller (5.3.1), ADF (5.3.2) with lag choice k "to ensure" white-noise residuals, structural breaks (5.3.4, Perron), KPSS as the stationarity-null complement (Table 5.3, p. 181). Ch. 6 Cointegration pp. 205–248: Engle–Granger residual-based test with Table 6.1 critical values (p. 216), Johansen (§6.3).

**Quant_Roadmap_Two_Doors (user's own paper)**
- Pillar 2: "cross-validation on dependent data (purged and embargoed, in López de Prado's terms) ... together with the discipline of multiple-testing correction. Harvey, Liu and Zhu's argument that a new factor needs a t-statistic near 3, and Bailey and López de Prado's deflated Sharpe ratio, are the two ideas an interviewer will use to check whether your backtest results are believable" (p. 8) — [Quant_Roadmap_Two_Doors_GEON_KOH_1.pdf](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/Quant_Roadmap_Two_Doors_GEON_KOH_1.pdf)
- Pillar 3: "version control, unit tests, reproducible runs with fixed seeds, a README that lets a stranger run the thing" (p. 8); action item "Rebuild the code base as a package with tests and fixed-seed reproducibility" (p. 9).
- Pillar 4: the KOSPI/KOSDAQ research question is to be "written up with the deflated Sharpe ratio, a walk-forward validation and a discussion of Korea's securities transaction tax" (p. 9); §9 reading table: López de Prado "for purged cross-validation and the deflated Sharpe"; Harvey, Liu & Zhu (2016) and Bailey & López de Prado (2014) "belong in your paper's method section" (p. 28).

**From Radon-Nikodym to Fung-Hsieh (user's own paper)**
- §3.4 p. 9: the physical density "comes from a time series of returns – a kernel density, GARCH-filtered innovations, or a parametric fit – with the familiar caveat that P-estimates of tails need decades of data" — [From_Radon-Nikodym_to_Fung-Hsieh_GEON_KOH_1.pdf](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/From_Radon-Nikodym_to_Fung-Hsieh_GEON_KOH_1.pdf)

**Boyd & Vandenberghe** — not re-read here; the architecture review already extracted what matters for the estimators: ML estimation is a convex problem only when the log-likelihood is concave (7.1.1, pp. 351–352) and local optimisation depends on the start (1.4.1) — [ARCHITECTURE_REVIEW.md §0](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/docs/ARCHITECTURE_REVIEW.md). Consequence for the gate: the GARCH fit is a non-convex local optimisation, so the validation loop must record convergence flags and re-fit from multiple starts at every origin, or the OOS score measures the optimiser as much as the model.

### Inferences
- The course's `tut03_cv.R` scheme (random, region-grouped k-fold) is correct for its own data — a cross-sectional panel where rows are regions and the leakage risk is *within-entity*, not *across time* — and it is exactly the scheme that is wrong for a strategy backtest: random folds put future observations in the training set of a past validation point (Lec 6 pp. 21–22, "we would have used the future"), and with overlapping multi-day labels the training rows adjacent to a validation row share information (the purge/embargo problem the roadmap names). Its transferable lessons are the grouped-fold idea (group by *time block* instead of by region), the seed-sensitivity check (31/50), and "test-set discipline".
- Bergmeir, Hyndman & Koo show standard k-fold *is* valid for a *purely autoregressive* model whose errors are uncorrelated ("as long as the models considered have uncorrelated errors ... Underfitting should be tackled beforehand, e.g. by testing residuals for serial correlation") — [Bergmeir, Hyndman, Koo, working paper, p. 1 and §7](https://robjhyndman.com/papers/cv-wp.pdf). A strategy's P&L series is not such a model (positions are held over several days, so consecutive labels overlap), so the app should use rolling-origin (walk-forward) evaluation for strategies and may use blocked CV only for one-step-ahead fits with white-noise residuals.
- The STAT248 §22.1 noise/bias trade-off is the reason to prefer *many* short OOS blocks over one long hold-out: rolling origins give many test points while each fit uses nearly all preceding data.
- Lec 8's quantile-tracking rule is the natural "REVISE" for a fan whose coverage drifts: it is an online correction, not a model change, and should be reported as such.

### Gaps
- The MTSA book does not present Diebold–Mariano, White, Hansen, Giacomini–White or any density-forecast test; those come from the literature section below.
- Boyd's text was not re-opened for this note; the citations above are second-hand from the architecture review.
- The PDF renderer is missing, so figures (e.g., Lec 8 Fig. 7 PIT shapes) were not seen; the text descriptions were used.

---

## Strategy evaluation: walk-forward, purged CV, multiple testing, Sharpe inference, cost and parameter tests

### Takeaway
The literature converges on: evaluate on rolling origins (Tashman 2000; Bergmeir & Benítez 2012); when cross-validating dependent data, purge overlapping labels and embargo the boundary (López de Prado 2018); correct the Sharpe ratio for the number of trials with the Deflated Sharpe Ratio, whose expected-maximum term is E[max SR] = σ_SR[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne))] (Bailey & López de Prado 2014); estimate the probability of backtest overfitting by combinatorially symmetric CV and reject when PBO > 0.05 (Bailey, Borwein, López de Prado & Zhu 2017); attach a standard error √((1+SR²/2)/T) (Lo 2002) or a studentized circular block-bootstrap CI (Ledoit & Wolf 2008); demand t > 3 for a "new factor" (Harvey, Liu & Zhu 2016); haircut expected performance by 26–58 % (McLean & Pontiff 2016); and, from practice, stress costs at 1.5–2×, demand year-by-year positivity and parameter plateaus, ≥ 30/100/200 trades, and OOS ≥ 50 % of IS (backtest-expert skill).

### Cited Findings

**Rolling-origin evaluation**
- Tashman, "Out-of-sample tests of forecasting accuracy: An analysis and review", *International Journal of Forecasting* 16(4), 2000, 437–450: in rolling-origin evaluation "the forecasting origin is repeatedly moved forward by a fixed number of observations, and forecasts are produced from each origin" — [ResearchGate record](https://www.researchgate.net/publication/223319987_Out-of-sample_tests_of_forecasting_accuracy_An_analysis_and_review); [greybox vignette summarising the procedure](https://cran.r-project.org/web/packages/greybox/vignettes/ro.html)
- Bergmeir & Benítez, "On the use of cross-validation for time series predictor evaluation", *Information Sciences* 191, 2012, 192–213 — [Monash record](https://research.monash.edu/en/publications/on-the-use-of-cross-validation-for-time-series-predictor-evaluati/); cited as the blocked-CV reference in [Bergmeir, Hyndman & Koo](https://robjhyndman.com/papers/cv-wp.pdf) (reference list, p. 18).
- Bergmeir, Hyndman & Koo: "in the case of a purely autoregressive model, the use of standard K-fold CV is possible as long as the models considered have uncorrelated errors"; "In the case of correlated errors, the CV procedure will be biased" — [working paper pp. 1–3, §7](https://robjhyndman.com/papers/cv-wp.pdf)

**Purged / embargoed / combinatorial CV and the probability of backtest overfitting**
- López de Prado, *Advances in Financial Machine Learning*, Wiley, Feb. 2018, 400 pp., ISBN 978-1-119-48208-6 — [Wiley product page](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086). The user's roadmap attributes "purged and embargoed" CV and the deflated Sharpe ratio to this book (Roadmap p. 8, p. 28). Chapter numbering (7 cross-validation in finance; 11 dangers of backtesting; 12 backtesting through CV incl. walk-forward and CPCV; 14 backtest statistics incl. PSR/DSR) is **UNVERIFIED** here: the publisher's and O'Reilly's contents pages refused the fetch.
- Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting", *Journal of Computational Finance* 20(4), 2017, 39–70 — [SSRN 2326253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253); preprint text: PBO := Σ_n Prob[r_n < N/2 | r ∈ Ω*_n] Prob[r ∈ Ω*_n] (Def. 2.2, eq. 2.2), i.e., the probability that the configuration that is optimal in-sample ranks below the median out-of-sample — [davidhbailey.com preprint, p. 10](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
- CSCV algorithm (Algorithm 2.3, pp. 11–12): form the T×N matrix M of P&L series for the N trials; partition the rows into an even number S of equal blocks; form all C(S, S/2) combinations (the paper prints "if S = 16, we will form 12, 780 combinations"; C(16,8) = 12,870); for each combination train = the S/2 chosen blocks, test = the rest; pick n* = argmax IS performance; compute its OOS relative rank ω̄_c = r̄_c(n*)/(N+1) and the logit λ_c = ln(ω̄_c/(1−ω̄_c)); PBO = ∫_{−∞}^{0} f(λ)dλ = the share of combinations in which the IS winner is below the OOS median — [preprint pp. 11–14](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
- Decision rule stated by the authors: "a customary approach would be to reject models for which PBO is estimated to be greater than 0.05" (§3.1, p. 14); also report performance degradation (regression of SR_OOS on SR_IS) and Prob[R_OOS < 0] — "even if φ ≈ 0, Prob[R < 0] could be high" (Fig. 2 caption, p. 15).

**Deflated Sharpe ratio**
- Bailey & López de Prado, "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality", *Journal of Portfolio Management* (front matter: "Forthcoming, 2014") — [SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); [author's PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf). Volume/pages (commonly cited as 40(5), 94–107) **UNVERIFIED** here.
- Expected maximum of N independent trial Sharpe ratios drawn from N(μ_SR, σ²_SR) (eq. 1, p. 7; the paper's own code, p. 15): E[max ŜR] ≈ μ_SR + σ_SR·[(1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e))], γ = 0.5772156649 (Euler–Mascheroni); code: `maxZ=(1-emc)*ss.norm.ppf(1-1./numTrials)+emc*ss.norm.ppf(1-1./(numTrials*np.e))`.
- DSR := PSR(SR₀) with SR₀ = that expected maximum under the null μ_SR = 0 (eq. 2, p. 8: "DSR is a PSR where the rejection threshold is adjusted to reflect the multiplicity of trials", p. 9). PSR uses "the sample length and the first four moments" (p. 8). The PSR formula as quoted by secondary sources of the paper: PSR(SR*) = Φ[ (ŜR − SR*)·√(T−1) / √(1 − γ̂₃·ŜR + ((γ̂₄−1)/4)·ŜR²) ], γ̂₃ skewness, γ̂₄ (non-excess) kurtosis, ŜR per-period — [MetricGate calculator page](https://metricgate.com/docs/deflated-johnson-sharpe-ratio/); [Balaena note](https://medium.com/balaena-quant-insights/deflated-sharpe-ratio-dsr-33412c7dd464). The paper's eq. (2) has this structure ("(ŜR − SR₀)√(T−1) / √(1 − γ̂₃ŜR + (γ̂₄−1)/4·ŜR²)") but its symbols did not survive text extraction, so the denominator is **verified only through secondary sources**.
- Five inputs the paper says a DSR needs: skewness, kurtosis, T, the variance of the trial SRs V[{ŜR_n}], and N (p. 9); worked example uses N = 100, T = 1250, and concludes a strategy with annualised SR 2.5 is not significant (pp. 9–10); Appendix 3 covers dependent trials (p. 7).
- Minimum track-record length (Bailey & López de Prado 2012, "The Sharpe Ratio Efficient Frontier", *Journal of Risk* 15(2)): MinTRL = 1 + [1 − γ̂₃ŜR + ((γ̂₄−1)/4)ŜR²]·(Z_α/(ŜR − SR*))² — **UNVERIFIED** (SSRN refused the fetch; the DSR paper confirms only that PSR "developed in Bailey and López de Prado [2012a]" exists, p. 8).

**Sharpe standard errors and bootstrap CIs**
- Lo, "The Statistics of Sharpe Ratios", *Financial Analysts Journal* 58(4), 2002, 36–52 — [CFA Institute record](https://rpc.cfainstitute.org/research/financial-analysts-journal/2002/the-statistics-of-sharpe-ratios). iid large-sample result: √n(ζ̂ − ζ) → N(0, 1 + ζ²/2), i.e., SE(ŜR) ≈ √((1 + ŜR²/2)/n) for the per-period SR (Two Sigma TR 2018-001, Fact 4, eq. 7, attributing it to Lo 2002 with the caveat that the non-normal extension is Mertens 2002) — [Riondato, Two Sigma Technical Report 2018-001, §2.4](https://www.twosigma.com/wp-content/uploads/sharpe-tr-1.pdf). Under serial correlation the annualisation factor becomes √(q + 2Σ_{k=1}^{q−1}(q−k)ρ_k) instead of √q (eq. 10, §2.5), and GMM/HAC variance applies (Fact 5, citing Lo 2002 and Ledoit–Wolf 2008).
- Ledoit & Wolf, "Robust performance hypothesis testing with the Sharpe ratio", *Journal of Empirical Finance* 15(5), 2008, 850–859: "construct a studentized time series bootstrap confidence interval for the difference of the Sharpe ratios and declare the two ratios different if zero is not contained in the obtained interval"; valid under heavy tails and time-series dependence where Jobson–Korkie/Memmel is not — [IDEAS working-paper abstract](https://ideas.repec.org/p/zur/iewwpx/320.html); [journal record](https://www.sciepub.com/reference/61384). Their block-size rule and replication count were not retrieved (**UNVERIFIED**).
- Riondato §3.3: studentized bootstrap: for each resample compute T = (ζ̂* − ζ̄)/ŝe*, take the empirical quantiles of T and invert — [Two Sigma TR §3.3](https://www.twosigma.com/wp-content/uploads/sharpe-tr-1.pdf)

**Multiple-testing hurdles and post-publication decay**
- Harvey, Liu & Zhu, "... and the Cross-Section of Expected Returns", *Review of Financial Studies* 29(1), 2016, 5–68: "a new factor needs to clear a much higher hurdle, with a t-statistic greater than 3.0" — [RFS record](https://academic.oup.com/rfs/article-abstract/29/1/5/1843824); [NBER w20592](https://www.nber.org/papers/w20592)
- White, "A Reality Check for Data Snooping", *Econometrica* 68(5), 2000, 1097–1126 — [IDEAS record](https://ideas.repec.org/a/ecm/emetrp/v68y2000i5p1097-1126.html); Hansen, "A Test for Superior Predictive Ability", *JBES* 23, 2005, 365–380 — [IDEAS record](https://ideas.repec.org/a/bes/jnlbes/v23y2005p365-380.html). Only the bibliographic records were retrieved; the test constructions (bootstrap of the maximum loss differential over all models; Hansen's studentisation and recentring) are **UNVERIFIED** here.
- McLean & Pontiff, "Does Academic Research Destroy Stock Return Predictability?", *Journal of Finance* 71(1), 2016, 5–32: across 97 predictors "portfolio returns are 26% lower out-of-sample and 58% lower post-publication"; the 26 % is "an upper bound estimate of data mining effects" — [Wiley record](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12365); [IDEAS](https://ideas.repec.org/a/bla/jfinan/v71y2016i1p5-32.html)

**Forecast comparison tests**
- Diebold & Mariano, "Comparing Predictive Accuracy", *JBES* 13, 1995, 253–263 — cited in the user's MTSA book, p. 92 (see above). The app already implements the DM-type statistic: the loss differential averaged across tickers at each origin, then a Newey–West (Bartlett) t-statistic with lag h/21 — [`docs/drift_study.py` lines 89–100, 193–210](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/docs/drift_study.py)
- Giacomini & White, "Tests of Conditional Predictive Ability", *Econometrica* 74(6), 2006, 1545–1578: a framework for out-of-sample comparison under misspecification that "handles forecasts from nested and non-nested models while accounting for estimation uncertainty" and allows conditional (state-dependent) comparison — [IDEAS record](https://ideas.repec.org/a/ecm/emetrp/v74y2006i6p1545-1578.html)

**Practice: the backtest-expert skill**
- Only `SKILL.md` exists on disk; `references/methodology.md` and `references/failed_tests.md` are referenced but **absent** from `...\skills\backtest-expert\` — [SKILL.md](file:///C:/Users/whydi/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/3b2fac86-5256-44cc-bbca-c136b186f8bd/2fc68a35-282c-4a76-8971-5819ceca9423/skills/backtest-expert/SKILL.md)
- Its rules: state the hypothesis in one sentence; codify rules with zero discretion (entry, exit, sizing, filters, universe); backtest "Minimum 5 years (preferably 10+)" across regimes with "commissions + conservative slippage"; stress: stops at 50–150 % and targets at 80–120 % of baseline, "Increase slippage to 1.5–2x typical estimates", worst-case fills; "Require positive expectancy in majority of years"; sample size "Absolute minimum: 30 trades, Preferred: 100+, High confidence: 200+"; walk-forward with warning signs "Out-of-sample <50% of in-sample performance", "Need frequent parameter re-optimization"; "Seek plateaus, not peaks" ("Good: stop loss anywhere from 1.5% to 3.0%; Bad: only at exactly 2.13%"); verdicts Deploy / Refine / Abandon; "5% edge per trade needs 100+ trades to distinguish from luck".

**What the app already has**
- `core/quant/backtest.py`: positions from close t earn from t+1; every position change pays `cost_bps` of traded notional; reports Sharpe = mean·252/vol, max drawdown, benchmark drawdown, n_trades — [backtest.py lines 15, 107–153](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/core/quant/backtest.py). No standard error, no OOS split, no trial count.
- The FX carry backtest "ranks on rates known at t and earns from t+1" and the tests check "costs only hurt" — [README](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/README.md).

### Inferences
- Sample-size arithmetic from Lo's SE (per-day SR = SR_ann/√252; SE_ann ≈ √(252/T) for small daily SR): a one-sided 90 % CI excludes zero only if T > 252·(1.645/SR_ann)² sessions — SR 1.5: ≈ 300 sessions; SR 1.0: ≈ 680 sessions (2.7 years); SR 0.5: ≈ 2,730 sessions (10.8 years). A two-year OOS record cannot certify anything below SR ≈ 1.2. (Computed here; it is the MinTRL logic with γ₃ = 0, γ₄ = 3.)
- Every parameter combination tried, every REVISE loop, every regime filter added after seeing results is a trial: N in the DSR must count them, and PBO must be computed on the whole trial matrix, not on the winner alone.
- The DM machinery in `drift_study.py` transfers unchanged to strategy comparison (loss = negative P&L or a utility) and to density-score comparison (loss = −log score or CRPS).
- The backtest-expert thresholds (2× costs, majority of years, 30/100/200 trades, OOS/IS ≥ 0.5, plateau) are practitioner rules without a citation trail; they are adopted in the gate as *engineering* checks, with the statistical checks (CI, DSR, PBO) as the *inferential* ones.

### Gaps
- The exact DSR denominator and the MinTRL formula are confirmed only through secondary sources; the primary PDF's mathematics did not extract. Before coding, open the PDF (or the SSRN HTML) and confirm eq. (2).
- Ledoit–Wolf's automatic block-length selection was not retrieved; the gate fixes b = 10 sessions and asks for a sensitivity check over b ∈ {5, 10, 20}.
- White's reality check and Hansen's SPA are cited but their bootstrap constructions were not verified; PBO + DSR cover the same purpose for a small personal trial set, so the gate does not require SPA.
- The Korean securities transaction tax (mentioned in the roadmap) was not researched; the cost model must take it as an input.

---

## Distributional evaluation: VaR exceedance, coverage, PIT, density scores, and reuse of `drift_study.py`

### Takeaway
A VaR/fan model is scored on three properties the literature makes testable: unconditional coverage (Kupiec 1995 LR_uc ~ χ²₁; Basel traffic light 0–4 / 5–9 / ≥10 exceptions of 99 % VaR in 250 days), independence and conditional coverage (Christoffersen 1998 LR_ind, LR_cc = LR_uc + LR_ind ~ χ²₂), and full-distribution calibration through the PIT z_t = F_t(y_t) which must be iid U(0,1) (Diebold, Gunther & Tay 1998; Berkowitz 2001 on Φ⁻¹(z)), ranked across models with strictly proper scores — log score and CRPS(F,x) = E_F|X−x| − ½E_F|X−X′| (Gneiting & Raftery 2007). All of these are low-power at 250 days (Kupiec: 65 % power to catch a 3 %-for-1 % VaR in one year, ≈90 % in two), so the loop must run over hundreds of origins; `docs/drift_study.py` already supplies the origins, the caching, the results file and the DM test, and needs only its constant-vol band replaced by each model's simulated quantiles.

### Cited Findings

**Unconditional coverage**
- Kupiec, "Techniques for Verifying the Accuracy of Risk Measurement Models", *Journal of Derivatives* 3, 1995, 73–84 (full citation from the Fed review's bibliography). POF statistic on T observations with I(α) = Σ_t I_t(α) violations and α̂ = I(α)/T: POF = 2·log[ ((1−α̂)/(1−α))^{T−I(α)} · (α̂/α)^{I(α)} ] (Campbell 2005 eq. 5), zero when α̂ = α; Wald form z = √T(α̂ − α)/√(α(1−α)) ≈ N(0,1) (eq. 6), which is "well-defined in the case that no VaR violations occur" while "Kupiec's POF test is undefined in this case" — [Campbell, "A Review of Backtesting and Backtesting Procedures", FEDS 2005-21, pp. 5–7](https://www.federalreserve.gov/pubs/feds/2005/200521/200521pap.pdf). Under H₀ the LR is asymptotically χ²(1) — [AnalystPrep summary](https://analystprep.com/study-notes/frm/part-2/market-risk-measurement-and-management/backtesting-var/)
- Power: "Kupiec (1995) ... reports that when the threshold of 8 violations in one year is used ... the chance of detecting a VaR measure that reports the 3% VaR instead of the required 1% VaR ... is only 65%"; "increasing the sample period from one year to two years increases the chance ... from 65% to roughly 90%" — [Campbell pp. 7](https://www.federalreserve.gov/pubs/feds/2005/200521/200521pap.pdf)
- Basel traffic light (1996 framework, 99 % one-day VaR, 250 days): green 0–4, yellow 5–9, red ≥ 10 exceptions; zones defined by cumulative binomial probability: green F ≤ 0.95, yellow 0.95 < F ≤ 0.9999, red beyond — [MathWorks `varbacktest.tl` doc citing Basel Committee, "Supervisory Framework for the Use of 'Backtesting' in Conjunction with the Internal Models Approach to Market Risk Capital Requirements", Jan. 1996](https://www.mathworks.com/help/risk/varbacktest.tl.html); consistent with Campbell: the multiplier "begins to increase after four violations of the 1% VaR ... in the previous 250 days" (POF = 0.76, exceeded "roughly 38% of the time" by an accurate model) and ten violations ⇒ "maximal value of 4.0" (POF = 12.95, "much less than 1% of the time") — [Campbell p. 6](https://www.federalreserve.gov/pubs/feds/2005/200521/200521pap.pdf). The BIS PDF itself (bcbs22) was not fetched (the server returned only the landing page; document dated 4 Jan 1996, status superseded) — [BIS page](https://www.bis.org/publ/bcbs22.pdf).

**Independence and conditional coverage**
- Christoffersen, "Evaluating Interval Forecasts", *International Economic Review* 39, 1998, 841–862 (citation from Campbell's bibliography). Markov test: 2×2 table of adjacent-day hits; H₀: N₁/(N₁+N₃) = N₂/(N₂+N₄), i.e., the violation rate after a violation equals the rate after a non-violation — [Campbell §3.2, p. 8](https://www.federalreserve.gov/pubs/feds/2005/200521/200521pap.pdf)
- Explicit LR form (transition counts n₀₀, n₀₁, n₁₀, n₁₁): π̂₀₁ = n₀₁/(n₀₀+n₀₁), π̂₁₁ = n₁₁/(n₁₀+n₁₁), π̂ = (n₀₁+n₁₁)/(n₀₀+n₀₁+n₁₀+n₁₁); LR_ind = −2·ln[ (1−π̂)^{n₀₀+n₁₀} π̂^{n₀₁+n₁₁} ] + 2·ln[ (1−π̂₀₁)^{n₀₀} π̂₀₁^{n₀₁} (1−π̂₁₁)^{n₁₀} π̂₁₁^{n₁₁} ] ~ χ²(1), critical values 3.841 (5 %) / 6.635 (1 %) — [value-at-risk.net §14.5](https://www.value-at-risk.net/backtesting-independence-tests/); LR_cc = LR_uc + LR_ind (~χ²(2)) — [AnalystPrep summary](https://analystprep.com/study-notes/frm/part-2/market-risk-measurement-and-management/backtesting-var/)
- Power comparison in Campbell: in one year the joint Markov test catches a misspecified VaR 50 % of the time, the independence-only test 56 %; "either unconditional coverage or independence tests alone are preferable to joint tests when prior considerations are informative" (p. 13); Christoffersen & Pelletier's duration test raised detection from 28 % to 46 % in one setting (p. 9).

**Density (PIT) evaluation**
- Diebold, Gunther & Tay, "Evaluating Density Forecasts with Applications to Financial Risk Management", *International Economic Review* 39, 1998, 863–883: z_t = F(y_t | Ω_t); under a correct density forecast "the z_t sequence is i.i.d. U(0,1)"; diagnostics are the histogram of z and correlograms of (z − z̄) and its powers; the KS test is mentioned with a warning about low finite-sample power; simulations use T = 250 — [NYU archive copy](https://archive.nyu.edu/bitstream/2451/14779/1/SOR-98-6.pdf); Campbell restates the two properties, uniformity and independence, "z_t iid ~ U(0,1)" (eq. 8, p. 12) and notes the informational cost: one needs "the entire conditional quantile function" (p. 12) — [Campbell](https://www.federalreserve.gov/pubs/feds/2005/200521/200521pap.pdf)
- Berkowitz, "Testing Density Forecasts, With Applications to Risk Management", *JBES* 19, 2001, 465–474 (citation from Campbell). The standard form of his test — transform u_t → z_t = Φ⁻¹(u_t), fit z_t = μ + ρ z_{t−1} + ε_t, ε ~ N(0,σ²), and test H₀: μ = 0, σ² = 1, ρ = 0 by LR ~ χ²(3) — is stated from general knowledge; **UNVERIFIED** against the paper text.
- Campbell's Pearson-Q multi-quantile test on bins [0, .01], [.01, .05], [.05, .10], [.10, 1] had more power than Kupiec against a systematically under-reported VaR: at 5 % under-reporting 13.5 % vs 6.3 %, at 25 % 94.2 % vs 79.7 % (Table 3, p. 23).

**Scoring rules**
- Gneiting & Raftery, "Strictly Proper Scoring Rules, Prediction, and Estimation", *JASA* 102(477), March 2007, 359–378, DOI 10.1198/016214506000001437: a rule is proper if S(Q,Q) ≥ S(P,Q), strictly proper if equality only at P = Q (eq. 1); the logarithmic score S(p, i) = log p_i is strictly proper (Example 3) and "has been criticized for its unboundedness"; CRPS: "CRPS*(F, x) = E_F|X − x| − ½E_F|X − X′|" (negative orientation of eq. 21), "reported in the same unit as the observations, and it generalizes the absolute error to which it reduces if F is a ... point measure"; strictly proper on distributions with finite first moment; the divergence is ∫(F − G)² dy (Cramér–von Mises type) — [author's PDF, §4.2](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

**Reusing `docs/drift_study.py`**
- The loop: origins every STEP = 21 SPY sessions; each ticker uses its last session on or before; horizons (21, 63, 126, 252); requires MIN_SESSIONS = 2000 per ticker and 1,260 prior returns + 252 forward sessions per origin (pass_1260) — [`drift_study.py` lines 27–30, 103–157](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/docs/drift_study.py)
- Its coverage column is `abs(R − Fh) <= Z90·σ_504·√(h/252)` — a constant-vol band (line 148), which is the B5 flaw: "the default GARCH-t fan ... has never been checked for the one property a fan must have" — [ARCHITECTURE_REVIEW.md B5](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/docs/ARCHITECTURE_REVIEW.md)
- Results discipline already in place: every quoted number is in `results.csv` with an md5 printed on re-run (lines 329–333, 349–352); prices cached as CSV so re-runs are offline.
- The review's stated gate: "a model becomes or stays the default only if its VaR95 exceedance rate over ≥ 200 origins is within ±2 binomial SE of 5 % and its PIT histogram passes a uniformity check" (B5); D1 asks for automated pre-fit data checks (zero returns, |r| > 0.5, duplicate dates, gaps, staleness) — [ARCHITECTURE_REVIEW.md B5, D1, §4.1](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/docs/ARCHITECTURE_REVIEW.md)

### Inferences
- With STEP = 21 the drift study yields ≈ 12 origins per ticker-year; for one-day VaR tests that is far too few, and origins should step daily (h = 1), every 5 sessions (h = 5) and every 21 (h = 21) — re-fitting at every origin as Lec 6 requires. The h-day PITs from overlapping origins are serially dependent; the KS and Christoffersen tests need h = 1 or non-overlapping origins, while CRPS/log-score DM comparisons can use overlapping origins with a Newey–West lag of h−1 (the study's existing convention).
- Binomial arithmetic for the ±2 SE band at target p = 5 %: SE = √(p(1−p)/n) = 1.54 pts at n = 200 (band 1.9–8.1 %), 0.97 pts at n = 500 (3.1–6.9 %), 0.69 pts at n = 1000 (3.6–6.4 %). Power (normal approximation, one-sided 5 %, 80 %) to detect a true 8 % rate against 5 %: n ≈ [(1.645·√(.05·.95) + 0.84·√(.08·.92))/0.03]² ≈ 340; two-sided ≈ 480. To detect 2 % against 1 % (VaR99): ≈ 1,000. So ≥ 500 one-day origins (≈ 2 years) is the floor for VaR95 and ≥ 1,000 for VaR99 — which agrees with Kupiec's own 65 % → 90 % remark.
- CRPS on a simulated fan is one line: with M sorted draws x_(i), CRPS = mean|x_i − r| − (1/(2M²))Σ_iΣ_j|x_i − x_j|, the double sum computable in O(M log M) from the sorted sample. The log score needs a density: analytic for GBM, a Gaussian-kernel density on the M draws otherwise.
- The PIT for the GARCH-t fan at h = 1 is analytic (Student-t CDF of r/σ_{T+1}); for h > 1 it is the empirical CDF of the simulated h-day return evaluated at the realised one. Seeded paths make the PIT reproducible to Monte Carlo error.

### Gaps
- Berkowitz's exact LR construction and Christoffersen's original notation are cited from secondary sources; the primary IER/JBES texts were not opened.
- The BIS 1996 PDF was not read; the zone table is from MathWorks and Campbell, which agree.
- No source was found (within this session's budget) for a recommended KS sample size for PIT tests; DGT's warning about low finite-sample power at T = 250 is the only guidance, hence the ≥ 500 origin floor.

---

## Minimum data, and what to do with short Korean histories

### Takeaway
The statistical floors are: ≥ 500 one-day origins for VaR95, ≥ 1,000 for VaR99, ≥ 100 non-overlapping origins per horizon for PIT/coverage at h = 21 (≈ 8.5 years) — or overlapping origins with HAC-corrected score comparisons only; for strategies ≥ 100 OOS trades, ≥ 5 years spanning at least two regimes, and an OOS length that satisfies T > 252·(1.645/SR)². KIS delivers ~100 rows per call, so years of Korean history are slow but possible; pykrx (`get_market_ohlcv`, adjusted=True, 1-second delay) and Yahoo `.KS` tickers (already used for 005930.KS since 2005 in the drift study) are the long-history routes.

### Cited Findings
- KIS daily OHLCV is paged at roughly 100 rows per call (task context; the app's `history.py` routes 6-digit codes to KIS) — [README data table](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/README.md)
- pykrx scrapes KRX and Naver; `get_market_ohlcv(start_date, end_date, ticker, frequency='d', adjusted=True)` returns daily OHLCV; the README warns that "excessive requests to the KRX server may result in blocking" and its examples insert 1-second delays — [sharebook-kr/pykrx](https://github.com/sharebook-kr/pykrx)
- The drift study already downloads `005930.KS` and `EWY` through yfinance from 2005 with `auto_adjust=True` and keeps tickers with ≥ 2,000 sessions — [`drift_study.py` lines 36–41, 53–69](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/docs/drift_study.py)
- "P-estimates of tails need decades of data" — [RN→FH §3.4 p. 9](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/From_Radon-Nikodym_to_Fung-Hsieh_GEON_KOH_1.pdf); the review adds "ν from 503 sessions is a tail estimate from two years" (B2).
- Kupiec's one-year power of 65 % rising to ≈ 90 % at two years — [Campbell p. 7](https://www.federalreserve.gov/pubs/feds/2005/200521/200521pap.pdf); backtest-expert: ≥ 5 years, 30/100/200 trades — [SKILL.md](file:///C:/Users/whydi/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/3b2fac86-5256-44cc-bbca-c136b186f8bd/2fc68a35-282c-4a76-8971-5819ceca9423/skills/backtest-expert/SKILL.md)

### Inferences
- For a Korean single name the validation loop should *not* run on KIS: pull once through pykrx or Yahoo `.KS`, cache to CSV under the scratchpad exactly as `drift_study.py` does, and reserve KIS for the live quote and the last 100 sessions. The card must record which source produced the validation history and which produces the live series, and the D1 data checks must run on both (adjusted-price conventions differ between sources; the review's A3 dividend-convention flag applies).
- When the history is shorter than the floor, the gate cannot PASS; it can only return "INSUFFICIENT DATA" with the number of origins/trades still missing — a fourth label the UI should show rather than a grey PASS.

### Gaps
- The exact KIS page size and rate limit were not measured in this session (the "~100 rows" figure is from the task statement).
- pykrx's license text was not visible on the fetched page.

---

## Decision rule: what the gate should compute and how to label the outcome

### Takeaway
One shared module, two loops. A strategy passes on an inferential triple (bootstrap CI of the walk-forward net Sharpe excludes 0; DSR ≥ 0.95 given N trials; PBO ≤ 0.05) plus engineering checks (OOS/IS ≥ 0.5, positive in ≥ 60 % of years, survives 2× costs, plateau, ≥ 100 trades). A distributional model passes on Kupiec and Christoffersen p > 0.05 at 95 % (and 99 % where n ≥ 1,000), 90 % coverage within ±2 binomial SE, PIT KS p > 0.05 with clean correlograms, and it *replaces* the incumbent only if its CRPS/log-score DM t < −1.96. REVISE names the component to change; REJECT is final for that hypothesis; every REVISE increments N.

### Cited Findings
- The review's own gate proposal (VaR95 within ±2 SE of 5 % over ≥ 200 origins + PIT uniformity) — [ARCHITECTURE_REVIEW.md B5](file:///C:/Users/whydi/OneDrive/Desktop/QUANTGEN/docs/ARCHITECTURE_REVIEW.md); the PBO authors' "reject models for which PBO is estimated to be greater than 0.05" — [PBO preprint §3.1](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf); Ledoit–Wolf's "declare the two ratios different if zero is not contained in the obtained interval" — [IDEAS abstract](https://ideas.repec.org/p/zur/iewwpx/320.html); backtest-expert's Deploy / Refine / Abandon with "Refine: Core logic sound but needs parameter adjustment" — [SKILL.md](file:///C:/Users/whydi/AppData/Roaming/Claude/local-agent-mode-sessions/skills-plugin/3b2fac86-5256-44cc-bbca-c136b186f8bd/2fc68a35-282c-4a76-8971-5819ceca9423/skills/backtest-expert/SKILL.md); Lec 8's PIT-shape diagnosis (U ⇒ too narrow, inverted-U ⇒ too wide) and quantile tracking as the online fix — [Lecture008.pdf pp. 10–11](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/Introduction%20to%20Time%20Series%20(UC%20Berkeley)/Lecture008.pdf); Occam's razor among near-equal models — [Lecture006.pdf p. 22](file:///C:/Users/whydi/iCloudDrive/퀀트%20학습%20자료/Introduction%20to%20Time%20Series%20(UC%20Berkeley)/Lecture006.pdf)

### Inferences
- The thresholds below are choices, not quotations: 0.95 for DSR is a one-sided 5 % confidence level; 0.05 for PBO is the authors' customary rule; 0.5 for OOS/IS and 2× costs are the backtest-expert practice; 60 % of years is a slightly stricter reading of "majority of years"; ±2 SE is the review's rule. They are all recorded on the model card so a later reader can see which number bit.

### Gaps
- No source prescribes the REVISE taxonomy; it is derived from what each failed test measures (see the gate).

---

## Recommended gate for QUANTGEN

Implementation constraint: numpy / scipy / statsmodels only, daily data, laptop. Everything below
is O(n_origins × fit cost) and reuses `docs/drift_study.py` (origins, CSV cache, results.csv
with md5, `newey_west_t`) and `core/quant/backtest.py` (positions, costs, Sharpe, drawdown).

### 0. Common rules
- **Register before testing.** The card (schema below) is created with hypothesis, rules, universe, data source and dates, cost model, seed and the *planned* parameter grid before the first backtest. N_trials is initialised to the grid size and incremented on every later change.
- **Data checks (review D1)** run first on the validation history: zero-return share, any |r| > 0.5, duplicate dates, gaps > 5 sessions, last date older than 5 days, adjusted-price convention. Any failure ⇒ INSUFFICIENT DATA, not a fit.
- **Rolling origin, whole procedure.** At every origin the *entire* procedure (parameter selection, model fit, multi-start, convergence flags) is re-run on data ≤ origin (Lec 6 pp. 21–22). Purge: no training label whose holding window overlaps the test block; embargo: skip `embargo` sessions (default = holding period) after each test block before training resumes.
- **Seed.** One `seed` per run; simulated fans use common random numbers across models (review D2).
- **Every number lands in `results.csv`** (long form: model/strategy, asset, horizon, metric, value, n) with the md5 printed; the card stores the md5.

### 1. Strategy loop (walk-forward)
Inputs: daily closes (≥ 5 years, ≥ 1,260 sessions; ≥ 2 regimes), strategy rules with a parameter grid of size G, cost_bps (base) and tax_bps, holding period H.

Procedure:
1. IS window W_IS = 756 sessions (min 504), OOS block W_OOS = 126 sessions, step = 126, embargo = H. At each origin choose θ* = argmax_θ SR_IS(θ) on the grid; record the whole IS grid vector (G Sharpes) — this is the CSCV matrix column set.
2. Concatenate OOS daily net P&L across blocks ⇒ series p_t, length T_OOS; count trades n_trades; recompute at 2× (cost_bps + tax_bps).
3. Statistics (annualise with √252 unless stated):
   - SR_OOS = mean(p)/sd(p)·√252; SR_IS = mean over origins of the winner's IS Sharpe.
   - SE_Lo = √((1 + ŜR_d²/2)/T_OOS)·√252, ŜR_d the daily SR.
   - Bootstrap 90 % CI: circular block bootstrap of p_t, block b = 10 sessions (report b ∈ {5, 20} too), B = 2,000, studentized: T* = (SR* − ŜR)/SE_Lo*, CI = [ŜR − t*_{0.95}·SE_Lo, ŜR − t*_{0.05}·SE_Lo].
   - DSR: per-day inputs ŜR_d, T_OOS, skew γ̂₃, kurtosis γ̂₄ of p_t; N = N_trials; σ_SR = sd of the IS grid Sharpes (daily units) pooled over origins; SR₀ = σ_SR·[(1−γ)Φ⁻¹(1−1/N) + γΦ⁻¹(1−1/(Ne))], γ = 0.5772156649; DSR = Φ[ (ŜR_d − SR₀)√(T_OOS−1) / √(1 − γ̂₃ŜR_d + ((γ̂₄−1)/4)ŜR_d²) ] (denominator as in the secondary sources; confirm against the paper before release).
   - PBO by CSCV on the T×G daily P&L matrix of all grid configurations over the full sample: S = 8 (70 combinations) when T < 2,000, S = 16 (12,870) otherwise; λ_c = ln(ω̄_c/(1−ω̄_c)); PBO = share of λ_c < 0; also the slope of SR_OOS on SR_IS across combinations and Prob[SR_OOS < 0].
   - Ratio OOS/IS = SR_OOS / SR_IS.
   - Years: share of calendar years with positive net OOS P&L; max single-year share of total P&L.
   - Cost stress: SR_OOS at 2× costs; turnover = mean |Δposition| per session ×252.
   - Plateau: on the last IS grid, fraction of the ±1-step neighbours of θ* whose SR ≥ 0.5·SR(θ*); flag if θ* on a grid edge.
   - Regime split: SR_OOS in high-vol vs low-vol halves (trailing 63-day realised vol above/below its median) and in up/down benchmark halves.
   - Benchmark (if the claim is "beats buy-and-hold"): Ledoit–Wolf difference-of-Sharpe bootstrap CI (same block bootstrap, paired) must exclude 0.
   - Haircut: expected live SR = 0.6 × SR_OOS (McLean–Pontiff 26–58 % decay ⇒ a 30–50 % haircut; 40 % chosen); record the haircut used.
4. Minimum samples: n_trades ≥ 100 (30 absolute floor ⇒ INSUFFICIENT), T_OOS ≥ 252·(1.645/SR_OOS_ann)² (the CI cannot exclude zero otherwise ⇒ INSUFFICIENT rather than REJECT), ≥ 5 OOS years.
5. Decision:
   - **PASS**: bootstrap 90 % CI lower bound > 0 **and** DSR ≥ 0.95 **and** PBO ≤ 0.05 **and** OOS/IS ≥ 0.5 **and** positive in ≥ 60 % of years **and** SR_OOS(2× costs) > 0 **and** plateau ≥ 0.5 with θ* not on an edge **and** n_trades ≥ 100.
   - **REVISE** (hard triple passes or is borderline; at least one engineering check fails). The failed check names the change, and each change is one more trial (N += 1):
     - OOS/IS < 0.5 or 0.05 < PBO ≤ 0.20 ⇒ over-search: coarsen the grid or fix a parameter at the plateau centre; lengthen W_IS; do not add parameters.
     - fails 2× costs or turnover > 2× the hypothesis' implied turnover ⇒ execution: lengthen H, add a hysteresis band or rebalance threshold; costs are never re-estimated downward.
     - years < 60 % or a regime half < 0 ⇒ only if the hypothesis already contained a regime condition may it be tightened; otherwise REJECT (a post-hoc filter is a new hypothesis, not a revision).
     - plateau < 0.5 or edge ⇒ widen the grid (edge) or reject the isolated optimum in favour of the plateau centre (re-run walk-forward with θ fixed to the plateau centre).
     - CI includes 0 but DSR ≥ 0.95 and PBO ≤ 0.05 ⇒ INSUFFICIENT DATA: extend history (pykrx / Yahoo .KS), do not touch rules.
   - **REJECT**: DSR < 0.95, or PBO > 0.20, or SR_OOS(2× costs) ≤ 0 with the CI including 0, or benchmark CI includes 0 when beating the benchmark is the claim, or two consecutive REVISE rounds fail the same check. A rejected hypothesis stays on the card ledger so that N is honest for its siblings.

### 2. Distributional-model loop (rolling-origin VaR / coverage / PIT)
Inputs: model ∈ {GBM, GARCH-t, jump, bootstrap, GJR (candidate), …}, asset class, horizons h ∈ {1, 5, 21, 63}, trailing window 504 sessions, n_paths = 5,000 (seeded).

Procedure:
1. Origins: every session for h = 1; every 5 for h = 5; every 21 for h = 21 and 63 (non-overlapping for h ≤ 21; h = 63 is overlapping ⇒ HAC only). Require ≥ 2,000 sessions of history per asset.
2. At each origin fit on the trailing window (multi-start, convergence flags), simulate the h-session fan in *zero-drift* mode (the drift study shows nothing beats zero; drift is scored separately), and record for the realised h-day log return r: hit95 = 1{r ≤ q_{0.05}}, hit99 = 1{r ≤ q_{0.01}}, inband90 = 1{q_{0.05} ≤ r ≤ q_{0.95}}, PIT u = F̂(r) (analytic at h = 1 for GBM and GARCH-t; empirical CDF of the paths otherwise), log score = log f̂(r) (analytic or Gaussian KDE on the paths), CRPS = mean|x_i − r| − (1/(2M²))Σ|x_i − x_j|, and the fit flags.
3. Tests per (model, class, h) over n origins:
   - Exceedance rate p̂ = mean(hit95); binomial SE = √(0.05·0.95/n); Kupiec LR_uc = −2ln[(0.95)^{n−x}(0.05)^x] + 2ln[(1−p̂)^{n−x}p̂^x] ~ χ²₁ (Wald z when x = 0). Same at 1 % when n ≥ 1,000.
   - Christoffersen LR_ind (transition counts) and LR_cc = LR_uc + LR_ind ~ χ²₂, h = 1 only.
   - Traffic light: exceptions of the 99 % VaR in the last 250 one-day origins: green ≤ 4, yellow 5–9, red ≥ 10.
   - 90 % coverage: |mean(inband90) − 0.90| ≤ 2·√(0.9·0.1/n).
   - PIT: KS test of u against U(0,1) (`scipy.stats.kstest`), 10-bin histogram with χ²₉, Berkowitz LR on Φ⁻¹(u) (μ = 0, σ² = 1, ρ = 0; χ²₃), DGT correlograms of (u − ū)^k, k = 1..4, at lags 1, 5, 20 within ±2/√n. PIT tests at h > 1 only on non-overlapping origins.
   - Score ranking: DM on d_t = CRPS_A − CRPS_B (and on log-score differences) with `newey_west_t(d, lag = h − 1)`; report per class and pooled.
4. Minimum samples: n ≥ 500 one-day origins for the 95 % tests, n ≥ 1,000 for the 99 % tests, n ≥ 100 non-overlapping origins for h = 21 (≈ 8.5 years; else report h = 21 as "indicative only").
5. Decision (per model, class, horizon):
   - **PASS**: Kupiec p > 0.05 at 95 % **and** Christoffersen LR_cc p > 0.05 (h = 1) **and** 90 % coverage within ±2 SE **and** PIT KS p > 0.05 with no correlogram bar outside ±2/√n **and** traffic light green.
   - **REVISE** — the failed diagnostic names the component:
     - exceedance above target / U-shaped PIT ⇒ tails too thin: t innovations (if normal), lower the ν floor, add the GJR leverage term (review B8), or lengthen the window; inverted-U ⇒ too wide: shorter window, or the bounded-innovation variance gap (review A2 bound_note) is the cause.
     - Kupiec passes but LR_ind fails / correlogram of (u − ū)² fails ⇒ volatility dynamics missing: GBM → GARCH; GARCH → GJR or a longer half-life; bootstrap → longer blocks (review C1).
     - PIT mean ≠ 0.5 (Berkowitz μ ≠ 0) ⇒ centring: the drift mode, or the dividend / FX-rate conventions (review A3, A4).
     - h = 1 passes, h = 21 fails ⇒ horizon aggregation: unconditional-variance target or the ½σ²_t correction (review A1).
     - Coverage drifts in time ⇒ report the online quantile-tracking correction (Lec 8 §3.1, η = 0.01 in return units) as a labelled overlay, never as the model.
   - **REJECT** (the model is not offered as a default for that class/horizon): exceedance ≥ 2× target (≥ 10 % at 95 %), or red zone, or PIT KS p < 0.01, or non-convergence at > 5 % of origins.
   - **Replacing the incumbent default**: challenger must PASS *and* have DM t < −1.96 on CRPS (or on log score) against the incumbent; if |t| ≤ 1.96, keep the simpler model (Occam, Lec 6 p. 22).

### 3. Model card (one JSON per strategy or model; the UI shows it next to the result)
```
card_id, created, updated, author
hypothesis            : one sentence, the edge or the distributional claim
kind                  : "strategy" | "distribution"
rules                 : entry/exit/sizing/filters (strategy) or model family + parameter bounds (distribution)
universe              : symbols, asset class, venue, currency
data                  : {source, adjusted (bool), dividend_convention, start, end, sessions, cache_md5}
costs                 : {cost_bps, tax_bps, slippage_model, stress_multiplier}
protocol              : {W_IS, W_OOS, step, embargo, window, horizons, n_paths, origins_per_h}
trials                : {N_planned, N_total, ledger: [ {change, date, reason} ]}
seed                  : int
is_stats              : {SR_IS, grid_sd_SR}
oos_stats             : {SR_OOS, SE_Lo, CI90_boot (b=5/10/20), MDD, n_trades, turnover, years_positive_share,
                         max_year_share, SR_OOS_2x, plateau_share, edge_flag, regime_split}
tests                 : {DSR, PBO, PBO_slope, Prob_loss_OOS, benchmark_CI, kupiec_p95, kupiec_p99,
                         christoffersen_ind_p, cc_p, coverage90, coverage90_se, pit_ks_p, pit_chi2_p,
                         berkowitz_p, pit_acf_flags, traffic_light, crps, logscore, dm_t_vs_incumbent}
decay_haircut         : {factor, source: "McLean-Pontiff 2016 26-58%"}
decision              : PASS | REVISE | REJECT | INSUFFICIENT_DATA
decision_reason       : the first failed criterion, in one plain sentence
revise_target         : component to change (or null)
results_file          : path + md5
```

Plain-language rendering rule (the user cannot judge silent failures): each test line in the UI shows the number, the threshold, the sample size behind it, and one sentence of the form "the fan said a 5 % day would happen 5 % of the time; it happened 7.8 % of the time over 612 days, which is 2.9 standard errors too often".

---

## Methods table

| Name | Source (locator) | What it tests | Formula | When to use | Implementation notes | User-material reference |
|---|---|---|---|---|---|---|
| Hold-out / k-fold CV | CS229 §9.3 pp. 140–142 | Generalisation error of a model class | k-fold: average over j of ε̂_{S_j}(h_{ij}); hold-out 70/30 | iid data; single-step fits with white-noise residuals | `np.array_split`; never for overlapping labels | CS229 pp. 139–142; tut03_cv.R |
| Time-series CV / rolling origin | Lec 6 §5.2 p. 21; Tashman 2000 IJF 16(4); Bergmeir & Benítez 2012 Info. Sci. 191 | Predictive accuracy of the *whole procedure* | CVMSE = (1/(n−t₀)) Σ_{t>t₀} (x̂_{t\|t−h} − x_t)² | Every strategy and every fan | Re-run selection at each origin; `drift_study.py` loop | Lec 6 pp. 21–22; Lec 4 p. 6 |
| Purged & embargoed walk-forward; CSCV/PBO | Roadmap p. 8; PBO preprint Alg. 2.3, Def. 2.2, §3.1 | Probability the IS winner is below the OOS median | PBO = ∫_{−∞}^0 f(λ)dλ, λ_c = ln(ω̄_c/(1−ω̄_c)), ω̄_c = r̄_c(n*)/(N+1) over C(S,S/2) splits | Any parameter search (G > 1) | S = 8 or 16; `itertools.combinations`; needs the full T×G P&L matrix | Roadmap Pillar 2 |
| Deflated Sharpe ratio | DSR paper eq. 1–2, code p. 15 (JPM 2014) | Significance of the best of N trials | SR₀ = σ_SR[(1−γ)Φ⁻¹(1−1/N)+γΦ⁻¹(1−1/(Ne))]; DSR = Φ[(ŜR−SR₀)√(T−1)/√(1−γ̂₃ŜR+((γ̂₄−1)/4)ŜR²)] | Reporting any selected strategy | `scipy.stats.norm`, `scipy.stats.skew/kurtosis(fisher=False)`; per-period SR | Roadmap pp. 8, 28 |
| Sharpe SE (Lo) | Lo 2002 FAJ 58(4) via Two Sigma TR Fact 4 eq. 7 | Sampling error of ŜR | SE ≈ √((1+ŜR²/2)/T) (iid); HAC/GMM under dependence | Always shown next to a Sharpe | Annualise SE by √252; MinTRL: T > 252(1.645/SR_ann)² | STAT248 §21.2.3 (asymptotics) |
| Studentized block-bootstrap CI | Ledoit & Wolf 2008 JEF 15(5); Two Sigma §3.3 | CI for SR or for a difference of SRs | T* = (SR*−ŜR)/ŝe*, CI from quantiles of T* | Heavy tails, autocorrelated P&L | Circular blocks b = 10, B = 2,000, numpy only | — |
| HLZ hurdle | Harvey, Liu & Zhu 2016 RFS 29(1) | Multiple-testing hurdle for a "new factor" | t > 3.0 | Cross-sectional factor claims | Report t = ŜR_ann·√(T/252) alongside DSR | Roadmap p. 8 |
| Reality check / SPA | White 2000 Econometrica 68(5); Hansen 2005 JBES 23 | Best-of-many vs benchmark under data snooping | Bootstrap of max loss differential (construction UNVERIFIED) | Large trial sets; optional | Not required by the gate (PBO+DSR cover the personal case) | — |
| Diebold–Mariano | DM 1995 JBES 13 (cited MTSA p. 92); `drift_study.py` 89–100 | Equal predictive accuracy of two forecasts/scores | DM = d̄/√(NW-var(d)/T), d_t = L₁,t − L₂,t | Ranking models on CRPS/log score; strategy vs benchmark loss | `newey_west_t(d, lag=h−1)` | MTSA §2.4.3 |
| Giacomini–White | GW 2006 Econometrica 74(6) | Conditional predictive ability, rolling windows, nested models | (construction not retrieved) | When the comparison is state-dependent (regimes) | Regress d_t on lagged regime indicators, Wald test | — |
| Mincer–Zarnowitz | MTSA eq. 2.63 pp. 86–87 | Forecast consistency / bias | x_{t+τ} = a₀ + a₁x̂_t(τ) + ε; H₀: a₀=0, a₁=1 | Point forecasts, τ = 1 (HAC for τ > 1) | `statsmodels.OLS` with `cov_type='HAC'` | 계량2 |
| RMSE, MAE, Theil's U, P(τ)² | MTSA pp. 85–88 | Point-forecast loss vs naïve | U = RMSE_model / RMSE_naïve | Drift/level forecasts | Already in `drift_study.metrics` (rmse, mae, skill_vs_zero) | 계량2 |
| Post-publication haircut | McLean & Pontiff 2016 JF 71(1) | Expected decay of a documented edge | 26 % OOS, 58 % post-publication ⇒ haircut 30–50 % | Card field `decay_haircut` | Multiply SR_OOS by 0.6 | Roadmap p. 9 (live-vs-backtest gap) |
| Cost stress, year-by-year, trades, plateau, OOS/IS | backtest-expert SKILL.md §4–5 | Fragility to friction, regime, search | 1.5–2× slippage; majority of years > 0; 30/100/200 trades; OOS/IS ≥ 0.5; plateau not peak | Every strategy | Grid neighbours ±1 step; edge flag | — |
| Unconditional coverage (Kupiec) | Kupiec 1995 J. Deriv. 3; Campbell 2005 eq. 5–6 | VaR hit rate = α | LR_uc = 2ln[((1−α̂)/(1−α))^{T−x}(α̂/α)^x] ~ χ²₁; z = √T(α̂−α)/√(α(1−α)) | Every VaR level, every horizon | `scipy.stats.chi2.sf(LR,1)`; use z when x = 0 | Review B5 |
| Traffic light | Basel 1996 via MathWorks tl doc; Campbell p. 6 | Regulatory zone of 99 % VaR over 250 days | green ≤ 4, yellow 5–9, red ≥ 10 | Last 250 one-day origins | `scipy.stats.binom.cdf` | — |
| Independence / conditional coverage (Christoffersen) | Christoffersen 1998 IER 39; value-at-risk.net §14.5 | Clustering of exceptions | LR_ind from (n₀₀,n₀₁,n₁₀,n₁₁) ~ χ²₁; LR_cc = LR_uc+LR_ind ~ χ²₂ | h = 1 hit series | `np.bincount` on 2·hit_{t−1}+hit_t | Lec 3 §3.5 (residual ACF idea) |
| Empirical coverage of a PI | Lec 8 §3 p. 9 | Band covers 1−α of the time | Coverage = (1/(n−t₀))Σ1{x_t ∈ I} | 90 % fan band | ±2√(0.9·0.1/n) tolerance | Lec 8; drift_study coverage_90 |
| Quantile tracking | Lec 8 §3.1 p. 10 (Angelopoulos et al. 2023) | Online repair of coverage | q_{t+1} = q_t + η(1−α) on miss, q_t − ηα on hit | When coverage drifts; overlay only | 3 lines of numpy | Lec 8 |
| PIT calibration (DGT) | Lec 8 §3.2 p. 11; DGT 1998 IER 39 | Whole predictive distribution | u_t = F_t(x_t) iid U(0,1); histogram; correlograms of (u−ū)^k | Every fan, h = 1 primarily | `kstest(u,'uniform')`, `chisquare` on 10 bins, ACF via `statsmodels.tsa.stattools.acf` | Lec 8 §3.2 |
| Berkowitz LR | Berkowitz 2001 JBES 19 (form UNVERIFIED) | Normality + independence of Φ⁻¹(u) | z = Φ⁻¹(u); AR(1) with (μ,σ²,ρ); LR ~ χ²₃ | Complements KS with more power in small n | `statsmodels.tsa.ar_model` or closed-form OLS | — |
| Log score, CRPS | Gneiting & Raftery 2007 JASA 102(477) §4.2, Ex. 3 | Strictly proper density scores | log f(x); CRPS = E|X−x| − ½E|X−X′| | Ranking fans across models | Sorted-sample O(M log M) CRPS; KDE for log score | — |
| AIC / BIC | STAT248 §21.2 p. 96, §22.1 p. 106, §22.4 p. 111 | In-sample proxy of OOS log-likelihood | AIC = −2ℓ̂ + 2p | Pre-screen only; never the gate | Count μ consistently (review B4) | STAT248 |
| MLE asymptotics / sandwich | STAT248 §21.2.3 pp. 98–101 | Standard errors of fitted parameters | √n(θ̂−θ*) → N(0, I⁻¹) (well-specified); sandwich otherwise | Card `is_stats` for GARCH (ν, α, β) | Numerical Hessian at optimum (review B2) | STAT248 |
| Residual diagnostics | Lec 6 §3.5 p. 12; Lec 3 §3.5 | Model adequacy before OOS | ACF of z_t and z_t² within ±2/√T | Every fit at every origin | `acf` at lags 1, 5, 20 (review B6) | Lec 6 |
| Unit-root / cointegration | MTSA §5.3 pp. 165–181, ch. 6 pp. 205–248 | Stationarity of inputs; spread stationarity for pairs | ADF, KPSS; Engle–Granger residual ADF with Table 6.1 CVs; Johansen | Pairs / carry spreads before backtesting | `statsmodels.tsa.stattools.adfuller, kpss, coint` | 계량2 |
| Fixed-seed reproducibility | Roadmap Pillar 3 p. 8 | Same inputs ⇒ same results.csv md5 | md5(results.csv) | Every run | Already in `drift_study.py` | Roadmap |
