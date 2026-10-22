# QUANTGEN Architecture Review

Models, measures, estimation and verification of the Quant Lab, reviewed against the
reference material in `C:\Users\whydi\iCloudDrive\퀀트 학습 자료`.

Written 2026-09-14. Review only: no code was changed. Section 1 is the ASCII map of the
whole application that was requested before any revision starts.

---

## 0. Scope, sources and rules of evidence

**What was reviewed.** `docs/QUANTGEN_Models_Primer.pdf` (built 2026-09-08 from
`core/quant/`), the code it was generated from (`core/quant/garch.py`,
`core/quant/montecarlo.py`, `core/quant/history.py`, `docs/drift_study.py`,
`tests/quant_acceptance.py`), and, for the application map, `main.py`, the README and
the module docstrings of every package.

**What counts as evidence.** Every finding carries one of four tags.

| Tag | Meaning |
|---|---|
| `[RUN]` | Measured by running the QUANTGEN code offline on a synthetic series (script and output in Appendix A). |
| `[DOC]` | Stated in the primer or visible in the code, with the section or `file:line`. |
| `[REF]` | Derived from a document in the 퀀트 학습 자료 folder, with the page or section. |
| `[EXT]` | Not derivable from the folder; one web lookup each, listed in Section 5. Only two items needed this. |

**Reference documents used and what each contributed.**

| Document in the folder | Used for |
|---|---|
| Shreve, *Stochastic Calculus for Finance II* (pypdf and pdftotext both fail on its font encoding; pages were rendered and read as images) | Risk-neutral drift with time-varying volatility (5.2.16, 5.2.23, 5.2.24, pp. 214-217); dividends (5.5.6-5.5.8, pp. 235-237); FX under the domestic risk-neutral measure (9.3.16, p. 385); jump models (11.7.1-11.7.5, pp. 505-507; 11.7.17-11.7.19, pp. 512-513); Vasicek and CIR (Examples 4.4.10-4.4.11, pp. 150-151) |
| Shreve, *Stochastic Calculus for Finance I* | The defining property of risk-neutral probabilities: the mean rate of return of every asset equals the money-market rate (pp. 7-8, p. 19) |
| Boyd & Vandenberghe, *Convex Optimization* | Local optimisation depends on the starting point (1.4.1, pp. 9-10); change of variables gives an equivalent problem (4.1.3, p. 130); ML estimation is convex only when the log-likelihood is concave (7.1.1, pp. 351-352) |
| CS229 notes | Selecting a model by training error "does not work"; hold-out and k-fold validation (9.3, pp. 139-142); EM for a mixture of Gaussians (11.1, p. 148) |
| Berkeley *Introduction to Time Series*, lectures 3, 4, 6, 8 | Residual ACF diagnostics (lec 3 §3.5); time-series cross-validation (lec 4 §2.3, lec 6); Box-Jenkins residual check (lec 6); empirical coverage, quantile tracking and PIT calibration of predictive distributions (lec 8 §3) |
| STAT248 *Applied Time Series* notes | Stochastic-volatility models as the alternative to GARCH (§2.2, p. 9); AIC defined on the maximised log-likelihood and the parameter count (§21.2); MLE asymptotics, Fisher information, the misspecified (sandwich) case (§21.2.3, pp. 98-101); quasi-Newton/BFGS (§11.1) |
| Meucci, *P versus Q* | Estimation as the P-world's main challenge (§2); the risk premium as the bridge between measures (§3.1); OU/Vasicek/CIR as the base processes for rates, GARCH and SV for clustering (§3.2, Fig. 3) |
| *From Radon-Nikodym to Fung-Hsieh* (Geon Koh) | Practitioners use implied quantities as early-warning inputs to P-risk (§4.4); P-tail estimates need decades of data (§3.4); the hedger's P&L depends on realised versus hedging variance (§6.7, eq. 34) |
| *Two Doors, One Corridor* (roadmap) | "Rebuild the code base as a package with tests and fixed-seed reproducibility" (Pillar 3); purged cross-validation and multiple-testing discipline (Pillar 2) |

Not used: the EE364A slides (duplicate the book), Berkeley lectures 1, 2, 5, 7 (no
bearing on the findings), and the two empty folders (`Mathematics with Application in
Finance (MIT)`, `Introduction to Probability, Statistics, and Random Processes`).

---

## 1. The whole application, in ASCII

### 1.1 Application map (as built today)

```
                              QUANTGEN  (Flet desktop app; entry point main.py)
                    views built once and cached; rail order is the NAV tuple in main.py
 ┌───────────────────────────────────────────────────────────────────────────────────────────┐
 │  UI  ui/*.py                                                                              │
 │                                                                                           │
 │   FICC surfaces (first in rail)        Equity surfaces          Inherited from NEXTGEN    │
 │   ┌────────┬───────┬───────┬────┬─────────────┐ ┌──────────┬───────────┬─────────┐ ┌──────────┬──────┬──────────┬───────┬─────┬──────┬─────────┐
 │   │ Macro  │ Rates │ Bonds │ FX │ Structuring │ │ Quant Lab│ Portfolio │ Signals │ │Execution │Rules │Workflows │Skills │ KRX │ Runs │Settings │
 │   └───┬────┴───┬───┴───┬───┴─┬──┴──────┬──────┘ └────┬─────┴─────┬─────┴────┬────┘ └────┬─────┴──┬───┴────┬─────┴───┬───┴──┬──┴──┬───┴────┬────┘
 │       │        │       │     │         │             │           │          │          │        │        │         │      │     │        │
 │   shared UI: ai_panel (local narrative + "Deep analysis" → Claude), components, param_form,      │
 │              charts / qcharts / fcharts  (matplotlib Agg → base64 data-URI images; Flet has no chart control)
 └───────┼────────┼───────┼─────┼─────────┼─────────────┼───────────┼──────────┼──────────┼────────┼────────┼─────────┼──────┼─────┼────────┼──────┘
         │        │       │     │         │             │           │          │          │        │        │         │      │     │        │
 ┌───────▼────────▼───────▼─────▼─────────▼──────┐ ┌────▼───────────▼──────────▼─────┐ ┌──▼────────▼────────▼─────────▼──────▼─────▼────────▼──────┐
 │  core/ficc          (decimals inside; % / bp │ │  core/quant                     │ │  core/engine        core/rules        core/skills          │
 │                      only in the UI)         │ │                                 │ │                                                             │
 │  curves     par → zeros (bootstrap), NS /    │ │  history    FMP | KIS | synthetic│ │  runtime   DISARMED→ARMED→HALTED loop on a background thread│
 │             Svensson fit, PCA of curve moves │ │             504 daily closes    │ │  feed      QuoteFeed: symbol → provider via core/markets    │
 │  swaps      par, PV, DV01, KRD, carry/roll   │ │  garch      GARCH(1,1)-t MLE    │ │  evaluator (rule, quote) → decision, atomic per rule         │
 │  bonds      price/yield, duration, convexity,│ │             (L-BFGS-B, guardrails)│ │  orders    simulated order book — NO broker order path      │
 │             DV01, KRD, z-spread, scenarios   │ │  montecarlo GBM | jump | bootstrap│ │  state     persisted trigger counts                        │
 │  fx         CIP forwards/basis, Garman-      │ │             | GARCH-t; 4 drift   │ │                                                             │
 │             Kohlhagen Greeks, RR/BF smile,   │ │             modes; fan, VaR/CVaR │ │  rules     model (immutable, no financial defaults),        │
 │             SABR, carry basket + backtest    │ │  risk       vol, drawdown, 1-day │ │            validation, store (one JSON file, edit history)  │
 │  ratesim    Vasicek | CIR | Hull-White       │ │             VaR/CVaR, skew, kurt │ │                                                             │
 │             (OLS on Δr), fan, horizon P&L    │ │  optimize   max Sharpe, min vol, │ │  skills    index (72-entry YAML manifest), entrypoints,     │
 │  structured PPN, reverse convertible, DCD,   │ │             risk parity, frontier│ │            readiness, params, runner (subprocess, env-only   │
 │             steepener note + hedge sheet     │ │  signals    6-component composite│ │            credentials), runs, workflows (YAML pipelines,   │
 │  macro      18-indicator sheet, z-scores,    │ │  backtest   costed, no look-ahead│ │            decision gates)                                  │
 │             regime read, daily/weekly brief  │ │  insights   local narrative +    │ │                                                             │
 │  insights   FICC narratives (bp, notional)   │ │             Claude payload       │ │  core/markets   venue → provider, suffix, currency, session │
 │  common     tenor parsing, errors            │ │  gsq        gs_quant tiers       │ │  core/calendars, core/theme, core/numfmt                    │
 │  data       FRED | Yahoo | synthetic  ───────┼─┼──── same routing rule: explicit provider that fails RAISES; only "auto" degrades to labeled synthetic
 └──────────────────────┬───────────────────────┘ └───────────────┬─────────────────┘ └───────────────────────────┬─────────────────────────────────┘
                        │                                         │                                               │
 ┌──────────────────────▼─────────────────────────────────────────▼───────────────────────────────────────────────▼─────────────────────────────────┐
 │  Providers and side effects                                                                                                                        │
 │   FRED (keyless)  Yahoo Finance (keyless)  FMP (FMP_API_KEY: EOD history, last price)  KIS (KIS_APP_KEY/SECRET: read-only quotations, adjusted   │
 │   daily closes)  KRX marketplace (keyless, session close)  OpenDART (filings)  Anthropic Claude API (ANTHROPIC_API_KEY, optional; payload = the    │
 │   computed numbers only)  gs_quant (offline timeseries; Marquee session with GS_CLIENT_ID/SECRET)                                                  │
 │   config.py: credentials by family, ~/.nextgen/ficc_cache (6 h), trading dir for rules JSON, skill env                                             │
 └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
   tests/run_all.py: engine + quant + FICC acceptance, hermetic (network touchpoints patched to raise)   docs/: build_models_primer.py, drift_study.py
```

### 1.2 The Quant Lab pipeline (as built today)

```
   symbol, source, model, drift mode, ERP, horizon, paths, target, seed
                       │
                       ▼
   history.load_history ──► History(dates, closes)      FMP adjClose | KIS adjusted close | synthetic GBM
                       │      _clean_rows: drops non-positive closes only
                       ▼
   log_returns r_t = ln(P_t / P_t-1)            (503 returns from 504 closes)
                       │
        ┌──────────────┴──────────────────────────────────────────────┐
        ▼                                                             ▼
   _calibrate: μ̄ = 252·mean(r), σ̄ = √252·sd(r)                fit_garch(r, "t")   [only when model = garch_t]
        │                                                        μ fixed at mean(r); ε = r − μ
        ▼                                                        L-BFGS-B on (ω·1e6, α, β, ν), 3 starts in β
   resolve_drift(mode, μ̄, σ̄, rf, ERP) → μ (annual log drift)      bounds ω≥1e-12, α∈[0,.5], β∈[0,.999], ν∈[2.5,30]
        premium: rf + ERP − ½σ̄²      rf: rf − ½σ̄²                 penalty −1e10 if α+β > 0.9995
        zero: 0                      sample: μ̄                     also fits GARCH-normal → LR; iid-normal → ΔAIC vs GBM
        │                                                        flags: at_bound, converged, stationarity
        ▼                                                             │
   zero-mean shocks per model  ◄──────────────────────────────────────┘
        gbm:       N(0, σ̄²/252)
        jump:      diffusion + Poisson·N(jump_μ, jump_σ²), split at 3σ̄, compound mean removed
        bootstrap: fixed 5-session circular blocks of demeaned r
        garch_t:   σ_t z_t, z_t ~ t_ν scaled to unit variance, recursion from σ²_{T+1}
        │
        ▼   every model: shocks + μ/252 per step
   paths = spot · exp(cumsum)                 (n_paths × horizon)
        │
        ▼
   fan percentiles 5/25/50/75/95, terminal distribution, P(loss), P(target),
   VaR95 / CVaR95 of L = 1 − P_T/spot (clipped at 0), mean_terminal, median_terminal
        │
        ├──► stat strip, chips, three charts (qcharts)
        ├──► local narrative (insights.narrate_monte_carlo)
        └──► Claude payload (same numbers, incl. mean_terminal) → ai_panel
```

Tests today: seeded reproducibility, ordered percentiles, CVaR ≥ VaR, GARCH parameter
recovery on a simulated series (tolerances 0.05 / 0.06 / ν in (4, 10)), unit-variance t
shocks, guardrail flags on a GBM series, likelihood ordering, forecast convergence,
drift-mode ordering. All in-sample or on simulated data; nothing scores a real series
out of sample.

---

## 1.3 Status (2026-09-16): A1 and A2 implemented

Findings A1 and A2 below were fixed after this review was written; the text of
the findings is kept as the record of the problem.

- **A2:** simulated t innovations are bounded at |z| ≤ 22 (`Z_BOUND` in
  `core/quant/garch.py`); a draw beyond the bound is redrawn from the t restricted
  to the bound, nothing is rescaled, so inside the bound the law is the fitted
  density. The bound was chosen by `docs/bounded_innovation_sweep.py` (rule and
  tables in `docs/bounded_innovation_sweep.md`) in two stages. Stage 1, a paired
  sweep over integer bounds, sets the floor: once-a-decade reproducibility of the
  fitted tail needs A ≥ 12, and for ν ≥ 4 every displayed statistic is within one
  5,000-path standard error of the unbounded model from A ≥ 14. Stage 2 sets the
  top: over five seeds and the heaviest tails (ν = 2.5 and 3.1), the signed
  shortfall of the simulated mean against exp(rf·T) stays inside the app's own
  5,000-path standard error up to A = 30 and fails at 35, so the martingale
  property holds at the app's resolution up to 30. The band is 14..30 and 22 is
  its midpoint. For ν below 4 the bound is visible and is reported: at 22 the
  bounded innovation carries 95.4 % of unit variance at ν = 3.1 (79.5 % at 2.5), a
  larger day is expected once per 48 years at ν = 2.5, and CVaR95 sits 2.8 (7.8)
  standard errors below the unbounded model's. Because the innovations are not
  rescaled, the simulated variance mean-reverts to ω/(1 − α·v − β) rather than
  the fit's level; `forecast_variance` and `horizon_vol` take the bounded variance
  so the horizon-vol tile describes the paths drawn, and every GARCH-t run carries
  a `bound_note` (in the narrative and the Claude payload, in every drift mode)
  stating the expected frequency of a capped day, the variance dropped, and the
  vol gap over the horizon.
- **A1:** the premium and rf modes now pass an arithmetic rate and every model
  subtracts its own exact per-step convexity correction: GBM ½σ̄² (unchanged),
  the jump model a closed form for its construction, the bootstrap the
  increments of the empirical block log-MGF, GARCH-t c(σ_t) from each path's
  conditional variance (tabulated per (ν, bound)). Measured on the Appendix A
  series: every model within ±0.01 points of exp(rate·T) under both modes
  (GARCH-t was +0.66). `MCResult` reports `correction_annual` and `z_bound`;
  `mu_annual` is the effective log drift. The rf mode stays available for every
  model.
- **A5 (iii)** is thereby closed (the jump model's correction is exact for its
  construction); A5 (i)-(ii) remain open.
- **B1 (2026-09-21):** implemented as the six steps of `docs/B1_FIX_BULLETIN.md`.
  The tail is fitted as η = 1/ν on [0, 0.4] (η = 0 is the normal); the t fit is
  seeded from the normal optimum and the normal re-fitted from the t's ω, α, β,
  with one more t pass if the normal climbs past it, so the likelihood ratio is
  non-negative by construction and clamped at 0 against optimiser tolerance; the
  t density's constant uses a Stirling expansion above ν = 10,000, where the
  gamma-function form cancels catastrophically (it produced spurious gradients of
  2e-5 at the boundary); ν above 100 is treated as normal in the sampler, the
  correction table and the tiles, with a "normal innovations" chip instead of the
  old "nu at upper bound"; `LR_5PCT` is 2.706 (the 5 % point of ½δ₀ + ½χ²₁) and
  the tile is greyed when α sits at its bound. A null-size acceptance test (200
  normal-innovation series) checks LR ≥ 0, the share at η = 0, and the size.
- **B2 (2026-09-25):** implemented as the six steps of `docs/B2_FIX_BULLETIN.md`
  (Appendix E there records the measurements). Every fit carries the
  observed-information covariance: the numerical Hessian of the log-likelihood at
  the optimum in the optimiser's scaled coordinates (ω × 10⁶), central differences,
  one-sided in a coordinate that sits on a bound, inverted after a Cholesky test
  and mapped back to natural units; `GarchFit.se` holds the Wald standard errors of
  ω, α, β, η and the delta-method standard error of the persistence, and is empty
  with the reason in `se_note` when a difference step leaves the domain
  (near-integrated fits) or the information matrix is not positive definite
  (effectively-normal fits, including the GBM demo). The tail's interval is a
  profile-likelihood interval in η, re-maximised over (ω, α, β) on a 41-point grid
  with warm starts, cut at 1.92 inside the domain and at 1.353 at η = 0 (the
  boundary-mixture null of B1, so the interval reaches "normal" exactly when the LR
  tile is below 2.706; the cut ramps between the two values inside the first grid
  cell so the lower end is continuous). The half-life interval is the persistence
  interval mapped through the half-life; the unconditional vol has no interval by
  measurement (42 % to 100 % coverage by persistence bucket). Tiles show "value
  (low to high)", chips say "SE undefined" and which intervals reach a bound, the
  narrative and the Claude payload carry the same. Cost on the demo series: fit
  60 ms → 149 ms with the profile; `fit_garch(profile=False)` for loops. Coverage
  acceptance test: 50 fits at T = 1,000, α/β/η Wald and η profile ≥ 85 % (measured
  96/96/90/90 %, persistence 100 %). The adversarial review of the change found a
  pre-existing optimiser defect that B2 made visible: the third default start
  (β₀ = 0.95, α₀ = 0.05) sat on the stationarity penalty and was dead, so some
  500-session fits stalled below the maximum; it is β₀ = 0.94 now, and the profile
  scan re-seeds the fit whenever it finds a higher likelihood. On the demo series
  the fit moved along the flat ridge of iid data to α = 0, where β is unidentified,
  and the narrative says so. Rebuilding the primer's profile figure then showed
  that a warm-started fixed-η refit can stall on that ridge, so every refit that
  lands outside the cut is retried from the joint optimum. Suite 229/229. The
  primer (`docs/QUANTGEN_Models_Primer.pdf`) was rebuilt for B1 and B2 on
  2026-09-25.
  B4 (AIC bookkeeping) is unchanged. The primer builder was patched only so it
  still imports; its prose and figures describe the old ν cap.
- New acceptance tests: bounded draws keep the fitted shape and their
  innovations differ from unbounded draws only beyond the bound; the correction
  table matches quadrature to 1e-7; the discounted price is a martingale for every
  model under rf and the mean path grows at rf + ERP under premium; the bound
  note is present in every drift mode; the horizon-vol tile matches the realised
  vol of the bounded paths within 3 % where the unbounded formula is off by more.
  Suite: 226/226. A before/after comparison (old modules snapshotted) shows the
  zero and sample modes bit-identical for every model, GBM identical in every
  mode, and the rate modes moved only where the single-σ̄ correction was wrong.
- Reviewed by three bounded adversarial agents after implementation; their
  findings (table transient of 173 MB, the vol-tile gap, the operator note, the
  noise-driven band edge, stale UI strings, a dead parameter, the divergent
  series behind the jump model's partial sum) were all addressed except the jump
  construction itself, which is finding A5.
- Not done: the primer PDF (`docs/build_models_primer.py`) still describes the
  old single-σ̄ correction in 1.4, 2.6, 3.2, 6.2, 7.7 and 8.6 and must be
  regenerated after its text is updated.

## 2. Findings at a glance

Severity: **High** = a displayed number is wrong or means something other than its
label; **Medium** = a silent estimation or model-selection weakness; **Low** = a
consistency or naming issue.

| ID | Sev. | Flaw | Evidence | Fix (short) |
|---|---|---|---|---|
| A1 | High | The "risk-neutral" and "risk-premium" drift modes deliver the stated mean growth only under GBM; GARCH-t paths grow faster because the ½σ² correction uses the sample vol while the paths run at the conditional vol | `[RUN]` +0.66 pts over 126 sessions; `[DOC]` montecarlo.py:158-186, 221; `[REF]` Shreve II 5.2.16/5.2.24 | Apply the correction per step with σ²_t; restrict the rf label to models where it holds; add a martingale test |
| A2 | High | With Student-t innovations the terminal price has no finite mean; `mean_terminal` is computed anyway and sent to the Claude panel | `[DOC]` primer 7.3 density, quant_lab_page.py:208; `[REF]` primer's own density formula | Report median and quantiles for GARCH-t, or bound the innovations |
| A3 | Medium | Whether closes are dividend-adjusted is unstated; the drift modes assume total-return closes | `[DOC]` history.py:122, kis_client.py:217; `[REF]` Shreve II 5.5.6 | Record the convention on `History`; use r − q when closes are price-only |
| A4 | Medium | For FX pairs the rf mode uses the domestic T-bill; the risk-neutral drift of an exchange rate is r_dom − r_for, which the app's own FX page already implements | `[DOC]` fx.py:57-61 vs montecarlo.py:176; `[REF]` Shreve II 9.3.16 | Route FX symbols to (r_dom − r_for) − ½σ²; test the rf median against `fx.forward` |
| A5 | Low | Jump model: threshold uses the sample σ that includes the jumps; jump sizes are fitted to whole-day returns; mean removal is in log space rather than Shreve's multiplicative compensator (numerically third-order; measured +0.02 pts) | `[DOC]` montecarlo.py:117-144; `[RUN]`; `[REF]` Shreve II 11.7.17-11.7.19 | Estimate the Poisson-normal mixture by EM (CS229 11.1) instead of a threshold |
| A6 | Low | GARCH filtered with ε = r − mean(r) but simulated with a different drift | `[DOC]` garch.py:153, montecarlo.py:209 | Filter with the drift you simulate, or document the 0.06 %/day gap |
| B1 | High | ν bounded at 30 breaks the nesting of the normal inside the t: the LR statistic goes negative (−0.5 in the primer, −1.17 in the check) and the "t vs normal" tile is then meaningless | `[DOC]` primer 6.4; `[RUN]`; `[REF]` Boyd 4.1.3 | Parameterise η = 1/ν ∈ [0, 0.4]; η = 0 is exactly the normal, LR ≥ 0 always. Critical value is then 2.706, not 3.841 `[EXT]` |
| B2 | Medium | No standard errors: α, β, ν are shown to three decimals with no precision, and ν = 3.1 from 503 sessions is a fragile number | `[DOC]` primer 5.1, 6.3; `[REF]` STAT248 21.2.3; RN→FH §3.4 | Inverse Hessian (or sandwich) at the optimum; show ± and flag intervals that touch a bound |
| B3 | Medium | Finite-difference gradient with a hand-scaled ω, a −1e10 penalty region with zero gradient, three starts in β only | `[DOC]` garch.py:93, 118-127; `[REF]` Boyd 1.4.1, 7.1.1; STAT248 11.1 | Analytic score through the recursion; unconstrained reparameterisation (log ω, logit persistence and share); keep the multi-start |
| B4 | Low | AIC counts μ for GBM (k = 2) but not for GARCH-t (k = 4); the GBM log-likelihood uses ddof = 1, so it is not the maximised likelihood the AIC definition requires | `[DOC]` garch.py:107-112, 160-166; `[REF]` STAT248 21.2 | Count μ in both or neither; use the MLE variance |
| B5 | High | Model choice (LR, ΔAIC) and the "typical values" table are in-sample; the drift study is out of sample but scores coverage with constant-vol bands, so the default vol model has never been scored out of sample | `[DOC]` drift_study.py:148, 367; `[REF]` CS229 9.3; Berkeley lec 6, lec 8 §3 | Rolling-origin VaR exceedance, 90 % coverage and PIT calibration for every model; make it the gate for any baseline change |
| B6 | Medium | No residual diagnostics after the fit: the ACF of squared standardised residuals is never checked | `[DOC]` primer 4.2 reports kurtosis only; `[REF]` Berkeley lec 3 §3.5, lec 6 step 3 | ACF of z² at lags 1, 5, 20 with a chip when outside ±2/√T |
| B7 | Medium | The worked fit sits outside the primer's own "typical daily-equity" ranges on α, persistence, half-life and ν, and nothing flags it because no bound binds | `[DOC]` primer 5.7 vs 10.3 | Soft guardrail from the table; list the largest |z_t| days |
| B8 | Medium | No asymmetric (leverage) term; the primer names the miss | `[DOC]` primer 3.6; `[EXT]` GJR form | Add γ·ε²·1{ε<0}; adopt only if B5 improves |
| B9 | Low | Alternative baseline not considered: stochastic volatility | `[REF]` STAT248 §2.2, lectures 16-18; Meucci Fig. 3 | Research comparison via particle filter; not the default |
| C1 | Low | "Stationary block bootstrap" is a fixed-length circular block bootstrap; block length 5 truncates clustering the primer measures out to lag 20 | `[DOC]` montecarlo.py:147-155; primer 4.1 | Block length from the ACF of r², or geometric block lengths |
| C2 | Low | VaR and CVaR clipped at zero | `[DOC]` montecarlo.py:249; risk.py:114 | Signed values, labelled |
| C3 | Medium | The model table offers GARCH-t for "rates series"; a log-return price-path model is the wrong object for a rate level. The app already has Vasicek/CIR/HW in `core/ficc/ratesim.py`, calibrated by OLS with no standard errors and a silent κ clamp | `[DOC]` primer 3.6; ratesim.py:129-133; `[REF]` Shreve II 4.4.10-11; Meucci §3.2 | Route rate levels to ratesim; report OLS standard errors on κ and the half-life |
| C4 | Medium | No channel from the app's implied vols (SABR smile, swaption vols) into the P-fan | `[REF]` RN→FH §4.4; Meucci §3.1 | Optional "implied" start/horizon vol mode, labelled |
| C5 | Medium | P-simulator (Quant Lab) and Q-pricers (FICC) share no path object, so a hedge P&L simulation cannot be built today | `[REF]` RN→FH §6.7 eq. 34 | A shared `Paths` type consumed by both |
| D1 | Medium | Data validation is a manual instruction in the primer | `[DOC]` primer 7.6; history.py:_clean_rows | Automated pre-fit checks (zero returns, split-sized moves, duplicate dates, gaps) |
| D2 | Low | "Same seed" across models is not common random numbers (different draw shapes) | `[DOC]` primer 2.4 | Say so; or draw uniforms once and transform |

---

## 3. Findings in detail

### A. Measure and drift plumbing

#### A1. The rf and premium modes deliver their stated growth only under GBM `[RUN] [DOC] [REF]`

**What the app does.** `resolve_drift` computes one annual log drift from the *sample*
volatility σ̄: `premium: rf + ERP − ½σ̄²`, `rf: rf − ½σ̄²` (montecarlo.py:166-177). Every
model then adds μ/252 to zero-mean shocks (montecarlo.py:221; for GARCH-t the same
`drift_daily` is passed into `simulate_returns`). The primer states the intent in 8.6:
"rf: μ = rf − σ²/2. The risk-neutral log drift: a price that grows at the T-bill rate on
average", and in 1.4 calls this mode "that measure".

**Why it is a flaw.** Shreve II (5.2.16) writes the stock with adapted volatility as
S(t) = S(0) exp{∫σ dW + ∫(α(s) − ½σ²(s)) ds} and, under the risk-neutral measure,
(5.2.24): S(t) = S(0) exp{∫σ dW̃ + ∫(R(s) − ½σ²(s)) ds}. The ½σ² correction is applied
*pointwise in time with the volatility of that step*. The app applies it once with the
sample volatility. When the GARCH conditional and horizon vol differ from σ̄, the mean
growth of the paths is exp((σ²_horizon − σ̄²)/2 · T) away from the label. The same
argument holds for the premium mode's claim that the arithmetic expected return is
rf + ERP. Shreve I (pp. 7-8, 19) states the property that defines the risk-neutral
probabilities: the mean rate of return of the stock equals the money-market rate; a
mode that violates it is not that measure.

**Measured.** On a 1,000-session synthetic GARCH(1,1)-t series (Appendix A) the fit gave
sample vol 16.7 %, conditional vol 22.6 %, horizon vol 23.0 %. Over 126 sessions with
100,000 paths and three seeds:

| mode | model | E[P_T]/spot | target | gap |
|---|---|---|---|---|
| rf | gbm | 1.01512 | 1.01511 | +0.00 pts |
| rf | garch_t | 1.02176 | 1.01511 | **+0.66 pts** |
| rf | jump | 1.01531 | 1.01511 | +0.02 pts |
| rf | bootstrap | 1.01473 | 1.01511 | −0.04 pts |
| premium | gbm | 1.03563 | 1.03562 | +0.00 pts |
| premium | garch_t | 1.04240 | 1.03562 | **+0.68 pts** |

The analytic size of the GARCH gap, ½(0.230² − 0.167²) × 0.5 yr = 0.63 pts, matches the
measurement; the remainder is the t tail. On the primer's AAPL run (sample 28.7 %,
horizon 33.2 %) the same arithmetic predicts ½(0.332² − 0.287²) × 0.5 = +0.70 pts on the
median-to-mean relationship the narrative describes.

**What to do instead.** In `simulate_returns`, add the drift per step as
`r_daily − ½σ²_t` (daily units) for normal innovations, i.e. move the correction inside
the recursion where σ_t is known. For the premium mode, the same with rf + ERP. For
Student-t innovations no finite correction exists (A2); either simulate the rf mode
with the normal-innovation GARCH already fitted for the LR test, or label the rf mode
"not available for GARCH-t". Keep the GBM behaviour, which is exact.

**How to prove it.** An acceptance test: for every model that offers the rf mode,
`|mean(P_T)/spot − exp(rf·T)| < 3 × MC standard error` with 100,000 paths. The script in
Appendix A is that test; today it fails for `garch_t`.

#### A2. Student-t innovations give the terminal price no finite mean `[DOC] [REF]`

**What the app does.** `MCResult.mean_terminal = mean(terminal)` (montecarlo.py:242) and
`expected_return_pct = mean_terminal/spot − 1`; the Quant Lab sends `mean_terminal` in
the Claude payload (quant_lab_page.py:208). The primer's 2.6 describes the standard error
of "a mean" as s/√N.

**Why it is a flaw.** The primer's own per-observation density (7.3) is
c(ν) − ½ ln σ²_t − ((ν+1)/2) ln(1 + ε²/((ν−2)σ²_t)), i.e. a density with polynomial tails
∝ |z|^{−(ν+1)}. The daily price factor is exp(σ_t z). Its expectation
∫ e^{σz} (1 + z²/(ν−2))^{−(ν+1)/2} dz diverges for every σ > 0, because the exponential
grows faster than any polynomial decays. So E[P_T] = ∞ under the default model, the
standard-error formula for a mean does not apply (the variance is infinite too), and
`mean_terminal` is a sample average of a quantity without a population value. Medians,
percentiles, P(loss), VaR and CVaR are unaffected: they are quantile-based or bounded
(L ≤ 1). Rendered in a primer sentence: with ν = 3.1 the *innovation* kurtosis is already
infinite (6.1); the price mean is one step further.

**Why it is invisible.** The divergence comes from draws of |z| in the hundreds, which
5,000 or even 100,000 paths never produce; the sample mean looks stable. That is
precisely why it must be documented rather than discovered.

**What to do instead.** Either drop `mean_terminal` from the GARCH-t result and the
Claude payload (report median and the 5/95 band, which the narrative already leads
with), or bound the innovations (a truncated t at, say, ±8 restores every moment and
makes the exact per-step martingale correction computable by one numerical integral).
State the choice in the primer's chapter 6.

#### A3. Dividend convention is unstated `[DOC] [REF]`

FMP history prefers `adjClose` (history.py:122) and KIS requests adjusted prices
(kis_client.py:203-217, `FID_ORG_ADJ_PRC`); neither the code nor the primer says whether
"adjusted" includes dividends. Shreve II (5.5.6): with a dividend yield A(t), the
risk-neutral dynamics are dS = [R − A] S dt + σ S dW̃, and the discounted price itself is
not a martingale (5.5.7); (5.5.8) gives the log drift r − a − ½σ². For price-only closes
the rf and premium modes are therefore off by the yield (on the primer's TLT and KO the
yield is a few percent a year, the same order as the ERP). Fix: a `total_return: bool`
on `History` set by the loader, and `rf − q − ½σ²` when it is false, with q from the
provider or an input field. Test: a synthetic price-only series with a known yield
recovers it in the rf-mode median.

#### A4. FX pairs: the rf mode uses the wrong rate `[DOC] [REF]`

The drift study runs EURUSD, USDJPY and USDKRW through the same `rf − ½σ²` (with ERP = 0
in premium mode). Shreve II (9.3.16): under the domestic risk-neutral measure the mean
rate of change of the exchange rate is R(t) − R^f(t); the text adds "In particular, it is
not R(t), as would be the case for an asset", and "Under the actual probability measure
P, the mean rate of change of the exchange rate can be anything." The app's own FX
module already prices forwards as S·exp((r_dom − r_for)T) (fx.py:57-61), so the Quant Lab
and the FX page disagree about the same pair. Fix: detect FX symbols (the FX page's
currency table) and use (r_dom − r_for) − ½σ². Test: the GBM rf-mode median at horizon
equals `fx.forward(spot, r_dom, r_for, T)` within Monte Carlo error.

#### A5. Jump-diffusion calibration `[DOC] [RUN] [REF]`

Three issues in `_simulate_jump` (montecarlo.py:117-144). (i) The 3σ split uses the
sample σ that already contains the jumps, so the threshold rises with the very outliers
it is meant to isolate. (ii) The jump-size distribution is fitted to the *whole* return on
jump days (diffusion plus jump), and with one jump day the width is set to half the
jump's size by fiat (line 130). (iii) The compound mean is removed in log space; Shreve II
(11.7.19) shows the price with jumps as S(0) exp{σW + (α − βλ − ½σ²)t} ∏(Y_i + 1) with
β = E[Y] the mean *price* jump (11.7.17), and under the risk-neutral measure the
continuous part drifts at r − λ̃σ (11.7.5). The app's correction differs from that
compensator, but the difference is third order in the jump size and the measured gap is
+0.02 pts (within seed noise), so (iii) is a formal, not a numerical, problem. (i) and
(ii) are the real ones: they make λ and the jump distribution depend on an arbitrary cut.

**What to do instead.** The daily return under Merton's model is a Poisson mixture of
normals; with λ of a few per year, a two-component mixture (no jump / one jump) is the
practical version, and CS229 11.1 gives the EM algorithm for exactly that model
(mixture weights, means, variances, closed-form M-step). EM replaces the threshold with a
maximum-likelihood split and yields λ, jump mean and jump variance jointly with the
diffusion variance. Test: on a simulated Merton series with known λ = 3/yr, EM recovers
λ within its standard error while the 3σ rule is biased.

#### A6. The GARCH filter and the simulation use different means `[DOC]`

`fit_garch` filters ε = r − mean(r) (garch.py:153); the simulation adds the drift mode's
μ instead. The difference is 0.06 %/day against a 1.8 %/day σ, so ε² barely moves. Worth
one sentence in the primer, or filter with the drift actually simulated.

### B. GARCH(1,1)-t estimation and its tests

#### B1. The ν bound breaks the nesting of the normal `[DOC] [RUN] [REF] [EXT]`

The primer (6.4) presents LR = 2(ln L_t − ln L_normal) as a nested test with a χ²₁ 5 %
critical value 3.841, and reports LR = −0.5 on the GBM demo series. A negative LR is
impossible for nested models at their optima: the t at ν → ∞ *is* the normal, so
ln L_t ≥ ln L_normal. With ν capped at 30 the t model no longer contains the normal, the
optimiser stops on the cap, and the tile's "grey below 3.841" rule mixes "normal is
enough" with "the bound got in the way". Re-run on an iid normal series (Appendix A): LR
= −1.17 with ν at 30 and α at 0.

**What to do instead.** Boyd 4.1.3: a one-to-one change of variables gives an
equivalent problem with the same optimal points. Optimise η = 1/ν on [0, 0.4]. η = 0 is
exactly the normal innovation, so the t model contains the normal, LR ≥ 0 by
construction, and the "effectively normal" case is reported as η = 0 rather than as a
bound chip. Two consequences follow. First, the "at bound: nu" chip splits into "η = 0:
normal innovations" (not a failure) and "η at 0.4: tails heavier than the model allows"
(a real warning). Second, the null hypothesis η = 0 now sits on the boundary of the
parameter space, where the χ²₁ result does not hold; this is the one point the folder
does not cover (Section 5): the null distribution is the mixture ½δ₀ + ½χ²₁, whose 5 %
critical value is 2.706. Using 3.841 is conservative (it under-rejects). Update
`LR_5PCT` and the primer's 6.4 together.

**How to prove it.** Test: on 50 iid-normal seeds, LR ≥ 0 always, and the share of LR >
2.706 is within binomial error of 5 %.

#### B2. No standard errors on the fitted parameters `[DOC] [REF]`

The screen shows α = 0.176, β = 0.655, ν = 3.1 and the chips say only whether a bound
binds. STAT248 21.2.3 (pp. 98-101): √n(θ̂ − θ) → N(0, I(θ)⁻¹) with I the Fisher
information, equal to minus the expected Hessian in the well-specified case; in the
misspecified case the covariance is the sandwich (score covariance and Hessian both
enter). *From Radon-Nikodym to Fung-Hsieh* 3.4 makes the practical point: "P-estimates of
tails need decades of data"; ν from 503 sessions is a tail estimate from two years.

**What to do instead.** After the best start, a numerical Hessian at the optimum (SciPy
can return it, or two-sided differences on the analytic gradient of B3) gives SE(α),
SE(β), SE(η); display "ν = 3.1 (2.6 to 4.4)" rather than "3.1", and turn a 95 % interval
that reaches a bound into a chip. The half-life and the unconditional vol inherit their
intervals by the delta method or by re-evaluating on the interval's ends.

**How to prove it.** On the existing simulated recovery series with 50 seeds, the true
(0.08, 0.90, 6) lies inside the 95 % interval in at least 45 of 50 fits.

**Closed 2026-09-25** (§1.3; `docs/B2_FIX_BULLETIN.md` Appendix E). Implemented with two
departures from the text above, both measured: the unconditional vol gets no interval,
because the delta method covers 42 % to 100 % depending on the fitted persistence, and
the ν interval is a profile-likelihood interval rather than a Wald one, because only the
profile behaves at η = 0 and at ν = 2.5. The proof ran as `test_interval_coverage_on_simulated_t_garch`:
50 fits at T = 1,000, coverage 96 / 96 / 90 % for α, β, η by Wald and 90 % for η by profile,
against the 85 % threshold. The sandwich was prototyped and left out (within 12 % of the
Hessian's standard errors in every design).

#### B3. The optimiser is fed a poor surface `[DOC] [REF]`

Three details in `_fit` (garch.py:114-144). The gradient is finite-difference; the code
scales ω by 10⁶ because "the finite-difference gradient in ω swamps the others and
L-BFGS-B stops after a handful of iterations" (comment at line 118). The stationarity
penalty returns a constant −1e10 (garch.py:93), a region with zero gradient that a
quasi-Newton method cannot climb out of. The multi-start varies only β₀ ∈ {0.80, 0.90,
0.95} with α₀ = 0.05 and ν₀ = 8 fixed. Boyd 1.4.1: "This initial guess or starting point
is critical, and can greatly affect the objective value of the local solution
obtained"; 7.1.1: ML estimation is a convex problem only when the log-likelihood is
concave in the parameters, which the GARCH likelihood is not. STAT248 11.1 describes
BFGS as Newton with an approximate Hessian; the approximation is only as good as the
gradients it sees.

**What to do instead.** (1) Analytic score: differentiate the recursion
σ²_t = ω + α ε²_{t−1} + β σ²_{t−1} once per parameter (∂σ²_t/∂θ = ∂x_t/∂θ + β
∂σ²_{t−1}/∂θ, the same IIR filter the variance path uses) and pass `jac=` to
L-BFGS-B; the ω scaling hack disappears. (2) Unconstrained parameterisation (Boyd
4.1.3): ω = e^w, persistence p = α + β = sigmoid(a), share α/p = sigmoid(b), η = 0.4 ·
sigmoid(c). Bounds and the penalty go away; the "at bound" logic becomes "p > 0.995" and
"η ≈ 0", which are the two facts the operator needs. (3) Keep the three starts and add
one in the share, since they are cheap. Test: the existing recovery test passes with
tighter tolerances (0.03 / 0.04) and the iteration count is reported.

#### B4. AIC bookkeeping `[DOC] [REF]`

STAT248 21.2 defines AIC(M) = −2 × (maximised log-likelihood) + 2 × (number of parameters
in M). The app counts k = 2 for GBM (mean and variance) but k = 4 for GARCH-t (ω, α, β,
ν), although GARCH-t also estimates μ (the sample mean, garch.py:153); and
`loglik_iid_normal` uses the ddof = 1 variance (garch.py:110), not the MLE variance, so
its value is below the maximum. Each effect is about 2 AIC units; the primer's rule of
thumb calls "below 2" a tie. Fix: count μ in both models or neither, and use ddof = 0.
The worked ΔAIC of +163.7 does not change its verdict, but the tile's colour rule near
zero does.

#### B5. Model selection is in-sample; the vol model has never been scored out of sample `[DOC] [REF]`

The LR test, ΔAIC and the "typical values" table (primer 5.7) are all computed on the
fitting window. CS229 9.3, on selecting by training error: "This algorithm does not
work"; its remedy is hold-out or k-fold validation. Berkeley lecture 6 states the
time-series version: "an ARMA model is useful if it predicts well. And as before, we can
assess this with time series cross-validation". Lecture 8 §3 gives the two statistics a
*distributional* forecast should be scored on: empirical coverage of the prediction
interval over rolling origins, and PIT calibration (the values F_t(x_t) should look
uniform; a U-shaped histogram means the fan is too narrow, an inverted U too wide). The
drift study already implements the rolling-origin loop (`docs/drift_study.py`: an origin
every 21 SPY sessions, 3,135 (ticker, origin) pairs), but its coverage column uses the
constant-vol band F ± 1.645 σ_504 √(h/252) (line 148, footnote at line 367). So the
default GARCH-t fan, the object the whole primer is about, has never been checked for
the one property a fan must have.

**What to do instead.** Reuse the loop. At each origin fit GBM, GARCH-t (and later GJR,
B8) on the trailing window, simulate h ∈ {1, 5, 21, 63} sessions, and record: the
1-day and h-day VaR95 exceedance rate (target 5 %), 90 % band coverage (target 90 %),
and the PIT value of the realised return. Report per model, per asset class, with
binomial standard errors; add the Diebold-Mariano machinery the study already has on the
quantile loss if a ranking is wanted. Lecture 8 §3.1 (quantile tracking) is the online
fix if coverage drifts: widen the band after a miss, narrow it after a hit.

**How to prove it.** The gate: a model becomes or stays the default only if its VaR95
exceedance rate over ≥ 200 origins is within ±2 binomial SE of 5 % and its PIT histogram
passes a uniformity check. This is the "verification process" the review was asked for;
everything in B8 and B9 should pass through it.

#### B6. Residual diagnostics are missing `[DOC] [REF]`

The primer (4.2) reports that dividing by σ_t lowers the excess kurtosis from 10.23 to
5.17 and stops there. Berkeley lecture 3 §3.5: inspect the autocorrelation function of the
residuals to check the white-noise assumption; lecture 6, step 3 of model building: "Fit
an ARMA model, inspect the residuals: they should look like white noise." For a
variance model the residual is z_t = ε_t/σ_t and the statistic is the ACF of z²_t, the
same quantity the primer uses on r² in 4.1 to motivate GARCH. Fix: compute the ACF of z²
at lags 1, 5 and 20 after every fit; a chip "residual clustering remains (ACF₁ = x)"
when any lies outside ±2/√T. One function, one test on the simulated series (the ACF of
z² must be inside the band when the model is true).

#### B7. The worked fit is atypical by the primer's own table, and nothing says so `[DOC]`

Primer 5.7 gives typical daily-equity ranges: α 0.05-0.10, persistence 0.95-0.99,
half-life 10-70 sessions, ν 4-8. The worked AAPL fit (10.3) has α = 0.176, persistence
0.831, half-life 3.8, ν = 3.1: outside on all four. The table's own advice for a high α
is "a few outliers dominate — look at them, try the jump model", yet no chip fires
because no bound binds. Fix: a soft guardrail built from that table (amber "atypical fit"
chip listing which ranges were left) and a list of the five largest |z_t| with their
dates, so the operator can see whether a handful of sessions (an earnings gap, a policy
day) are driving α and ν. This also feeds A5: those days are the jump model's data.

#### B8. Asymmetry (leverage) `[DOC] [EXT]`

Primer 3.6 lists "asymmetry (down moves raising vol more than up moves)" among what
GARCH(1,1)-t misses. The folder has no asymmetric GARCH; the standard one-parameter
extension (Section 5) adds γ · ε²_{t−1} · 1{ε_{t−1} < 0} to the variance recursion.
Because γ = 0 recovers GARCH(1,1), the existing LR machinery (after B1) tests it for
free, and the persistence becomes α + β + γ/2. Adopt it as the default only if it passes
the B5 gate; the primer's numbers do not establish that it will.

#### B9. Stochastic volatility as an alternative baseline `[REF]`

STAT248 §2.2 introduces the SV model (log-variance as an AR(1) state, returns as
exp(X_t/2) ε_t) with the remark that it "is an alternative to volatility time series
models such as ARCH or GARCH (which are somewhat less natural even though they are
widely used)", and lectures 16-18 give the bootstrap and guided particle filters that
estimate it. Meucci's Figure 3 places GARCH and SV as the discrete- and
continuous-time faces of the same feature. Recommendation: not the default (a particle
filter per fit is a different cost class and its Monte Carlo likelihood makes the LR and
AIC comparisons noisier), but the right research comparison to run through the B5 gate
once it exists.

### C. The other models and the FICC boundary

#### C1. The bootstrap `[DOC]`

`_simulate_bootstrap` samples fixed-length blocks of 5 with wrap-around
(montecarlo.py:147-155); the comment and the primer (3.5) call it the stationary block
bootstrap, which draws *random* (geometric) block lengths. Name it what it is. More
important, the primer's own ACF of r² is 0.222 at lag 1, 0.088 at lag 5 and 0.047 at lag
20 (4.1): clustering persists past the block, so the resampled paths carry less of it than
the sample. Fix: block length from the first lag at which the ACF of r² falls inside
±2/√T, or geometric block lengths with that mean. Test: the ACF of r² at lag 5 across
resampled paths matches the sample's within noise.

#### C2. VaR and CVaR clipped at zero `[DOC]`

`var_pct = max(0, var)` (montecarlo.py:249; risk.py:114). A favourable distribution shows
"VaR 0.0 %", hiding the number, and the coherence test (CVaR ≥ VaR) is partly vacuous on
clipped values. Report signed values with a "gain" label when negative.

#### C3. Rates do not belong in a log-return price-path model `[DOC] [REF]`

Primer 3.6 lists "daily equity, FX and rates series" as the GARCH-t default's domain.
For a *rate level* the log return is the wrong object: Shreve II Example 4.4.10 gives
Vasicek dR = (α − βR) dt + σ dW with the mean-reverting drift "which pushes R(t) back
toward α/β", and notes the model's admitted defect (positive probability of a negative
rate); Example 4.4.11 gives CIR. Meucci §3.2: "two forms of the Ornstein-Uhlenbeck
process, namely the model by Vasicek and the model by Cox, Ingersoll and Ross,
represent the base case sell-side processes to price bonds." The app already has this
family in `core/ficc/ratesim.py` (Vasicek, CIR, Hull-White; OLS on Δr; Feller check).
Two fixes. (1) Routing: the Quant Lab should refuse a rate-level symbol or hand it to
ratesim; a bond ETF (TLT) is a price and stays. (2) Uncertainty: ratesim's OLS returns
`coef` only (ratesim.py:126) and clamps κ at 0.01 with a note (lines 129-133); Berkeley
lecture 3's regression theory gives the standard error of the slope for free, so the
half-life ln 2/κ can be shown with its interval, which is wide on two years of daily
data whenever the clamp is close to biting.

#### C4. No implied-vol channel into the P-fan `[REF]`

*From Radon-Nikodym to Fung-Hsieh* 4.4: risk managers "use option-implied quantities as
early-warning inputs, on the principle that Q reacts to news faster than any estimate of
P can". Meucci 3.1 frames the two measures as linked by the risk premium. The FX page
holds a SABR smile and the Rates page swaption vols, but the fan is built from 504
closes alone. An optional "implied" mode that starts σ_{T+1} at the horizon ATM implied
(or blends it with the GARCH forecast) and is labelled as such gives the operator the
desk's second opinion on width without changing the default.

#### C5. The P-simulator and the Q-pricers do not share a path object `[REF]`

The structuring term project ("Structured Products PitchBook & Hedge Trading") needs
the hedger's P&L identity in *From Radon-Nikodym to Fung-Hsieh* 6.7 (eq. 34): the
replication error of a Black-Scholes hedge along a path is ½∫e^{r(T−t)} Γ S² (σ²_t −
σ²_h) dt, i.e. it needs P-paths with realised variance (the Quant Lab) revalued by the
Q-pricer (the FICC core) step by step. Today `MCResult.paths` and `ratesim` paths are
separate arrays consumed only by their own charts. A shared `Paths` type (dates, price
matrix, per-path realised variance) consumed by both the Quant Lab and the structuring
hedge sheet is the smallest architectural change that makes the project possible.

### D. Verification architecture

#### D1. Data validation is a manual instruction `[DOC]`

Primer 7.6 tells the operator to "check the closes for stale or duplicated prices" and to
"inspect the series for zeros, splits or duplicated closes"; `_clean_rows` drops
non-positive closes only. Automate it before the fit: count of zero returns, any |r| >
0.5 (a split or a bad print, flagged rather than fitted), duplicate dates, gaps longer
than N sessions, a last date older than N days. Refuse the fit or show a red chip. Test: a
series with an injected 2:1 split is flagged and the fit is not run.

#### D2. "Same seed" is not common random numbers `[DOC]`

Primer 2.4 compares GBM and GARCH-t "on the same history and seed". The two models draw
different shapes (normal; t and a recursion), so the paths are not paired and the
comparison carries full Monte Carlo noise on both sides. Either say so in the primer or
draw uniforms once and transform them per model, which makes model-to-model
differences far less noisy at no cost.

---

## 4. Recommended target architecture

### 4.1 The Quant Lab pipeline with the changes above

```
   inputs ──► load_history ──► DATA CHECKS (D1) ──► returns
                                  │ zero returns, split-sized moves, duplicates, gaps, staleness → refuse / red chip
                                  ▼
             ┌────────────────────┴────────────────────────────────────────────┐
             ▼                                                                 ▼
   FIT (per model)                                                    DRIFT (per mode, per asset type)
   GBM: μ̄, σ̄                                                         premium: rf + ERP − ½σ²_t per step (A1)
   GARCH: unconstrained (log ω, logit p, logit share, η = 1/ν)        rf:      rf − ½σ²_t per step; FX: (r_dom − r_for) (A4);
          analytic score, multi-start (B3)                                     price-only closes: − q (A3);
          Hessian → standard errors (B2)                                       not offered for unbounded t (A2)
          η = 0 ⇒ normal, LR ≥ 0, critical value 2.706 (B1)           zero, sample: unchanged
          optional γ asymmetry term (B8)
   jump:  EM on the Poisson-normal mixture (A5)
   bootstrap: block length from ACF of r² (C1)
             │
             ▼
   POST-FIT DIAGNOSTICS ──► chips
     ACF of z² at lags 1/5/20 (B6) · atypical-range chip + largest |z| days (B7) · intervals touching a bound (B2)
             │
             ▼
   SIMULATE with common random numbers across models (D2) ──► paths ──► shared Paths object (C5)
             │                                                              │
             ▼                                                              ▼
   fan, quantiles, P(loss), signed VaR/CVaR (C2); median only for t (A2)    FICC pricers / hedge sheet
             │
             ▼
   narrative + Claude payload (numbers that exist)
   
   OFFLINE GATE (docs/vol_backtest.py, reusing drift_study's rolling origins)  (B5)
     per model, class, horizon: VaR95 exceedance rate, 90 % coverage, PIT histogram
     ─► a model is the default only while it passes; every baseline change (B8, B9, C4) enters through here
   
   ACCEPTANCE TESTS added:  rf-mode martingale test (A1) · LR ≥ 0 and 5 % size (B1) · interval coverage on
     simulated fits (B2) · recovery with tighter tolerances (B3) · ACF of z² in band (B6) · split detection (D1)
     · EM recovers λ (A5) · bootstrap keeps lag-5 ACF (C1) · FX rf median = CIP forward (A4)
```

### 4.2 Order of work, cost and the proof for each

| Step | Change | Size | Proof |
|---|---|---|---|
| 1 | A1 per-step ½σ²_t correction; A2 drop `mean_terminal` for t; A4 FX rate; A3 convention flag | small diff in montecarlo.py / garch.py; primer 1.4, 8.6 and 2.6 rewritten | martingale test; FX forward test |
| 2 | B1 η = 1/ν with the 2.706 critical value; B4 AIC bookkeeping | small diff in garch.py | LR ≥ 0 on 50 normal seeds; size ≈ 5 % |
| 3 | B5 rolling-origin vol backtest; B6 residual ACF; D1 data checks | one script reusing drift_study.py; two small functions | coverage/PIT tables in docs/; chip tests |
| 4 | B2 standard errors; B3 analytic score and unconstrained parameters | medium diff in garch.py | tighter recovery tolerances; interval coverage |
| 5 | B8 asymmetric term, evaluated through step 3 | small diff | passes the gate or stays off |
| 6 | A5 EM jump calibration; C1 bootstrap block length; C2 signed VaR; B7 atypical chip | small diffs | listed above |
| 7 | C3 routing of rate levels to ratesim with OLS standard errors; C4 implied-vol mode; C5 shared Paths | architectural; needed for the structuring project | hedge P&L reproduces eq. 34 on a constant-vol path |
| later | B9 stochastic volatility via particle filter | research | through the gate only |

Steps 1-3 change what the screen says and give the project its first out-of-sample
scorecard; they are the ones to do before any model is swapped. Nothing above requires a
new dependency.

---

## 5. What the folder could not settle

Two points were not derivable from the folder and were checked online, as instructed.

1. **Likelihood-ratio test with the null on the boundary (B1).** With η = 1/ν the null
   η = 0 lies on the edge of the parameter space and Wilks' χ²₁ result does not apply.
   The asymptotic null distribution is the equal mixture ½δ₀ + ½χ²₁ (Self and Liang,
   1987), so the 5 % critical value is 2.706 rather than 3.841. Sources: [Likelihood
   Asymptotics in Nonregular Settings: A Review with Emphasis on the Likelihood Ratio
   (arXiv 2206.15178)](https://arxiv.org/pdf/2206.15178); [A note on the asymptotic
   distribution of the Likelihood Ratio Test statistic under boundary conditions (arXiv
   2509.00223)](https://arxiv.org/pdf/2509.00223); [Non-standard boundary behaviour in
   two-component mixture models (arXiv 2407.20162)](https://arxiv.org/pdf/2407.20162).
2. **Asymmetric GARCH (B8).** The Glosten-Jagannathan-Runkle (1993) variance equation
   adds γ · ε²_{t−1} · 1{ε_{t−1} < 0} to GARCH(1,1). Sources: [The
   Glosten-Jagannathan-Runkle-GARCH approach to the FX forward premium (DergiPark
   PDF)](https://dergipark.org.tr/tr/download/article-file/366223); [Forecasting current
   market turbulence with the GJR-GARCH model
   (SITMO)](https://www.sitmo.com/forecasting-current-market-turbulence-with-the-gjr-garch-model/).

Everything else in this document rests on the folder and on the code.

---

## Appendix A. The offline check `[RUN]`

Script: `docs/verify_drift_check.py` (run from the project root with `PYTHONPATH=.`; no
network, about two minutes).
It builds a 1,000-session GARCH(1,1)-t series with `simulate_garch_series(2e-6, 0.08,
0.90, 6.0, n=1000, seed=3)` plus 0.04 %/day, wraps it in `History`, and calls
`run_monte_carlo` for every model under the rf and premium modes with 100,000 paths and
seeds 7, 8, 9 (rf 3 %, ERP 4 %, 126 sessions).

```
fit: GARCH(1,1)-t on 999 sessions, mu fixed at +0.001%/day: alpha=0.108 beta=0.884
     persistence=0.992 nu=7.5; no guardrail hit.
sample vol 16.655% | cond vol T+1 22.570% | horizon vol 22.988% | uncond 23.673%
rf       gbm        E[P_T]/spot = 1.01512 (+/- 0.00036)  target 1.01511  gap +0.00 pts
rf       garch_t    E[P_T]/spot = 1.02176 (+/- 0.00042)  target 1.01511  gap +0.66 pts
rf       jump       E[P_T]/spot = 1.01531 (+/- 0.00035)  target 1.01511  gap +0.02 pts
rf       bootstrap  E[P_T]/spot = 1.01473 (+/- 0.00068)  target 1.01511  gap -0.04 pts
premium  gbm        E[P_T]/spot = 1.03563 (+/- 0.00037)  target 1.03562  gap +0.00 pts
premium  garch_t    E[P_T]/spot = 1.04240 (+/- 0.00043)  target 1.03562  gap +0.68 pts
premium  jump       E[P_T]/spot = 1.03582 (+/- 0.00035)  target 1.03562  gap +0.02 pts
premium  bootstrap  E[P_T]/spot = 1.03523 (+/- 0.00070)  target 1.03562  gap -0.04 pts
iid-normal series: LR t vs normal = -1.168, nu = 30.0, at_bound = ('alpha', 'nu')
```

Analytic size of the GARCH gap: ½ (0.22988² − 0.16655²) × (126/252) = 0.0063, i.e.
+0.63 pts; the measured +0.66 is that plus the t tail.

## Appendix B. Where each cited passage is

| Citation | Location |
|---|---|
| Shreve II 5.2.15-5.2.16 | pp. 214-215 (PDF pages 229-230) |
| Shreve II 5.2.21, 5.2.23 | p. 216 (PDF 231) |
| Shreve II 5.2.24 and "changes the mean rate of return of the stock but not the volatility" | p. 217 (PDF 232) |
| Shreve II 5.5.1, 5.5.6-5.5.8 | pp. 235-237 (PDF 250-252) |
| Shreve II 9.3.16 and the FX sentences | p. 385 (PDF 400) |
| Shreve II 11.7.1-11.7.5 | pp. 505-507 (PDF 520-522) |
| Shreve II 11.7.17-11.7.19 | pp. 512-513 (PDF 527-528) |
| Shreve II Examples 4.4.10-4.4.11 | pp. 150-151 (PDF 165-166) |
| Shreve I risk-neutral mean rate of return | pp. 7-8, p. 19 |
| Boyd 1.4.1; 4.1.3; 7.1.1 | pp. 9-10; p. 130; pp. 351-352 |
| CS229 9.3; 11.1 | pp. 139-142; p. 148 |
| Berkeley lec 3 §3.5; lec 4 §2.3; lec 6 (model building, TS-CV); lec 8 §3, §3.1, §3.2 | as numbered in the lecture PDFs |
| STAT248 §2.2; §11.1; §21.2; §21.2.3; §22.4 | pp. 9; 46-49; 96-98; 98-101; 111 |
| Meucci §2, §3.1, §3.2 | pp. 3-5 |
| From Radon-Nikodym to Fung-Hsieh §3.4, §4.4, §6.7 | pp. 9, 10, 16 |
| Primer sections | 1.4, 2.4, 2.6, 3.4-3.6, 4.1-4.2, 5.7, 6.1-6.4, 7.3, 7.6, 8.6, 10.3 |
