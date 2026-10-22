# QUANTGEN B1 Fix Justification Briefing

## 🔍 Executive Summary
* **Status:** Complete. Six steps shipped 2026-09-21; acceptance suite 227/227.
* **Timeline:** Primer prose still describes the old ν cap; rebuild date TBD.
* **Risk:** Low. Interior-ν estimates unchanged; only the test statistic and labels moved.

## 🚀 Key Accomplishments
* **Flaw measured:** 73 % of 300 normal-innovation fits gave a negative LR; worst −14.7.
* **Nesting restored:** η = 1/ν reaches the normal at η = 0; shipped minimum LR is exactly 0.
* **Null mass matched:** 56 % of 200 null fits land at η = 0; the boundary mixture predicts 50 %.
* **Size measured:** At T = 500, false positives are 3.0 % at 2.706 and 1.0 % at 3.841.
* **Power gained:** Rejection at ν = 12 rose 51 % to 65 %; at ν = 20, 21 % to 30 %.
* **Estimates unchanged:** Reference fit agrees to 3e-4 (α 0.0718, β 0.9098, ν 6.03).

## ⚠️ Current Roadblocks
* **Finite-sample size:** 3.0 % ± 1.2 pt at 200 series; the nominal 5 % is not established.
* **Weak identification:** ν stays poorly determined on 500 sessions; B2 standard errors still open.
* **Boundary asymptotics:** Mixture assumes α, β interior; the tile is greyed when α is at 0.
* **Display cut-off:** ν above 100 is shown as normal; the flat ridge moved, it did not vanish.
* **Stale primer:** Sections 6.3, 6.4 and 7.5 to 7.7 still describe the ν cap of 30 and 3.841.
* **Fit time:** 57 ms per fit against 50 ms before, a 14 % increase from the mutual seeding.

## 📅 Next Steps
* **TBD:** Rewrite primer sections 6.3 to 7.7 for η and 2.706, then rebuild the PDF.
* **TBD:** Decide whether a finite-sample threshold table by T is worth about 35 s per fit.
* **TBD:** Take up B2, standard errors from the Hessian, the remaining identification gap.
* **TBD:** Close the unrelated engine double-place race; a task chip is already open.

## 💡 Context & LLM Instructions
* **Audience:** The QUANTGEN operator; also OTM interview preparation.
* **Tone:** Technical, evidential, candid.
* **Action:** FYI only; the code change is done. The appendices hold the full evidence.

---

## Appendix A. What B1 is, and what the fix does

* **The flaw.** The t fit bounds ν at 30, so the t model never contains the normal it is tested against. The optimiser stops on the cap, the "LR t vs normal" statistic comes out negative (impossible for nested models), and the tile's "grey below 3.841" rule mixes "normal is enough" with "the cap got in the way". Primer 6.4 prints LR = −0.5 on the GBM demo series (the measured value is −0.45, rounded); the self-check series gives −1.17.
* **The fix.** Optimise η = 1/ν on [0, 0.4]. η = 0 is exactly the normal innovation, so the t model contains the normal, and LR ≥ 0 holds by construction when the normal optimum is one of the starts and the normal likelihood is evaluated by the same code path (the prototype used the app's separate normal fit, hence its −3.3e-5 worst case and its spurious +0.073 on the self-check series). Boyd 4.1.3: a one-to-one change of variables yields an equivalent problem with the same optimal points, so nothing about the estimator changes where ν is interior.
* **The consequence.** The null η = 0 sits on the boundary of the parameter space, where Wilks' χ²₁ result does not hold; the asymptotic null distribution is the equal mixture ½δ₀ + ½χ²₁ (Self and Liang, 1987), whose 5 % critical value is 2.706. The current 3.841 has 2.5 % upper-tail probability under that mixture.

## Appendix B. Evidence (prototype `b1_experiment.py`, 203 s)

Method: the app's own likelihood, recursion, bounds on ω, α, β and L-BFGS-B, with ν replaced by η and a fourth start at the normal-GARCH optimum with η = 0. Series from `simulate_garch_series` (ω 2e-6, α 0.08, β 0.90), 500 sessions, the app's window size.

**B.1 Nesting on the two series the primer uses**

| Series | Current LR | Current ν | η fit LR | η fit ν |
|---|---|---|---|---|
| iid normal, 500 obs (self-check; α also at 0) | −1.17 | 30.0 (at bound) | +0.073 at η = 9e-6 | 112,165 |
| GBM demo `synthetic_history("AAPL")` | −0.45 | 30.0 (at bound) | +0.045 | 380 |

The +0.073 is not tail evidence: at η = 9e-6 the t adds 5e-5 to the log-likelihood (B.5); the rest is the η fit finding a better ω, α, β than the app's separate normal fit, which sits at the α bound on this series. Step 2 of the plan removes this by evaluating both likelihoods through one code path.

**B.2 Null distribution, 300 normal-innovation GARCH series (η landing spots from a 120-series follow-up)**

| Statistic | Current fit | η fit | Theory (mixture) |
|---|---|---|---|
| Share of LR < 0 | 73.0 % | 0.7 % (worst −3.3e-5, optimiser tolerance) | 0 |
| Share at η = 0 (η < 1e-6) | not reachable | 53 % | 50 % |
| Share at ν ≤ 100 (η ≥ 0.01) | not measured | 38 % (median LR 0.64) | — |
| 95th percentile of LR | 2.05 | 2.07 | 2.706 (χ²₁: 3.841) |
| Size at 3.841 | 1.7 % | 2.0 % | 2.5 % |
| Size at 2.706 | 3.0 % | 3.3 % (95 % CI 1.3 to 5.4 %) | 5.0 % |

Reading: the current statistic is wrong in sign on most null series but its false-positive rate is not inflated. The η fit reproduces the mixture's point mass (53 % at zero against 50 %). Both measured sizes sit below their asymptotic values, but with 300 series the 3.3 % has a ±1.0 point standard error, so "conservative at T = 500" is suggestive rather than established.

**B.3 Power, 150 t-innovation series per ν, 500 sessions**

| True ν | Current at 3.841 | η fit at 3.841 | η fit at 2.706 |
|---|---|---|---|
| 5 | 100 % | 100 % | 100 % |
| 8 | 86.7 % | 86.7 % | 89.3 % |
| 12 | 51.3 % | 51.3 % | 64.7 % |
| 20 | 21.3 % | 21.3 % | 30.0 % |

Reading: at 3.841 the two fits reach the same decision on every one of the 600 series, so the change of parameterisation itself costs no power. The extra 3 to 13 points come from the lower threshold and are bought with the move in size from 2.0 % to 3.3 %; that is the usual size-for-power trade, made at a threshold that now has a stated justification.

**B.4 Point-estimate equivalence, interior ν (recovery-test series, 3,000 obs)**

| | α | β | ν | log-likelihood |
|---|---|---|---|---|
| Current | 0.071845 | 0.909821 | 6.0337 | 9653.38148 |
| η fit | 0.071842 | 0.909825 | 6.0339 | 9653.38148 |

**B.5 Limit behaviour.** loglik(η) − loglik(normal) on the self-check series: 1.4e-6 at η = 1e-7, 4.7e-5 at 1e-5, 4.2e-3 at 1e-3. The density passes into the normal without a jump, so the optimiser sees one smooth surface ending at the boundary.

## Appendix C. Drawbacks, in detail

* **Size may still be below 5 % at the app's window.** The mixture is an asymptotic result; at T = 500 the measured size at 2.706 is 3.3 % with a ±1.0 point standard error. A parametric bootstrap of the null gives the exact finite-sample threshold (about 2.07 here) but costs roughly 300 fits, about 35 s at the measured 0.11 s per fit, per series: too slow for an interactive lab. A precomputed table by T is possible but the threshold also depends on α and β.
* **A positive LR near η = 0 is not necessarily tail evidence.** The prototype's η fit can improve ω, α, β over the app's separate normal fit (the self-check series: LR +0.073 with η = 9e-6). Unless the normal likelihood is evaluated with the same starts and code path, small positive LRs are optimiser noise; the fix must compute both through one path and clamp at 0.
* **The flat ridge does not disappear; it moves.** Today it ends at ν = 30 with an "at bound" chip. With η it ends at η = 0, where 53 % of null fits land, but 38 % stop at ν ≤ 100 with a median LR of 0.64 and the remainder between ν = 100 and 100,000. The tile must map ν above a cut-off (100 is a natural choice; at ν = 100 the t's excess kurtosis is 0.06) to "normal innovations", or the screen shows absurd numbers.
* **Numerics at extreme η.** `t_density` raises (1 + z²/(ν−2)) to the power −(ν+1)/2; for ν beyond about 10,000 rounding in the base is amplified by the exponent. Simulation, the correction table and kurtosis should route ν above the cut-off to the normal branch rather than evaluate the t formula.
* **Boundary asymptotics need interior nuisance parameters.** Self and Liang's mixture assumes α and β are interior. The self-check series fits α = 0 as well, a doubly-boundary null whose reference distribution differs. The app already flags α at bound; the LR tile should be greyed when it is.
* **Tiny negative LR from optimiser tolerance.** The prototype's worst value is −3.3e-5. Either clamp at 0 or accept; the sign is no longer diagnostic of a failure.
* **Code and documentation surface.** `BOUNDS["nu"]` becomes a bound on η; `at_bound` loses the "nu upper" case and gains "eta upper" (ν = 2.5, the real warning); `_draw_z`, `bounded_t_stats`, `martingale_correction` and `kurtosis_excess` need the ν = ∞ branch; `test_garch_respects_bounds_and_flags_on_gbm_series`, `test_garch_t_beats_normal_and_gbm_on_clustered_series` and the narrative test change; primer sections 6.3, 6.4, 7.5, 7.6 and 7.7 describe the old bound and must be rewritten before the PDF is rebuilt.
* **Fit time.** Measured on 20 series of 500 sessions: 50 ms per fit today, 62 ms with the fourth start, a 24 % increase.
* **What the fix does not change.** Weak identification of ν on 500 sessions is intrinsic: the likelihood is flat in η near 0 whether or not the parameter is bounded, which is why B2 (standard errors) remains a separate finding.

## Appendix E. Implementation record (2026-09-21)

* **Steps 1 to 6 shipped** in `core/quant/garch.py`, `core/quant/montecarlo.py`, `core/quant/insights.py`, `ui/quant_lab_page.py` and `tests/quant_acceptance.py`; acceptance suite 227/227.
* **Two additions the prototype did not have.** (i) After the normal is re-fitted from the t's ω, α, β, if it climbs past the t the t is fitted once more from that normal, so the two models are seeded from each other until neither improves; without this one null seed in 200 gave LR = −1.8e-5. (ii) The t density's normalising constant switches to a Stirling expansion above ν = 10,000: the gamma-function form cancels catastrophically at ν ≈ 1e8, where the finite-difference step from η = 0 lands, and produced spurious gradients of that size.
* **Re-fits use only the seeded start**, so the shipped fit costs 57 ms against 50 ms before (normal 20 ms, t 31 ms, re-fit 6 ms), not the 103 ms a naive re-fit with all starts cost.
* **Measured on the shipped code.** Recovery series: α 0.071842, β 0.909825, ν 6.034, identical to the old fit to 3e-4. GBM demo: ν 491, LR +0.003, chip "normal innovations" (was ν 30 at bound, LR −0.45). Self-check series: ν = ∞, LR 0 (was −1.17). Null over 200 series: minimum LR exactly 0, 56 % at η = 0, size 3.0 % at 2.706 and 1.0 % at 3.841.
* **Not done.** The primer builder was patched only so it still imports (`_NU_RANGE`); its prose and figures on the ν cap, the LR critical value and the guardrail table must be rewritten before the PDF is rebuilt. B4 (AIC bookkeeping) is unchanged.

## Appendix D. Sources

* Primer 6.3 and 6.4 (the bound and the LR tile); `core/quant/garch.py` `_fit` and `fit_garch`.
* Boyd and Vandenberghe, *Convex Optimization*, 4.1.3 (change of variables, equivalent problems).
* Self, S. G. and Liang, K.-Y. (1987), asymptotics of likelihood ratio tests under nonstandard conditions: via [arXiv 2206.15178](https://arxiv.org/pdf/2206.15178) and [arXiv 2509.00223](https://arxiv.org/pdf/2509.00223).
* Prototype and raw results: `docs/b1_evidence/b1_experiment.py`, `docs/b1_evidence/b1_results.json`; the η landing spots and the fit timing are in `docs/b1_evidence/b1_followup.txt`.
* Independent check of this document against the raw results by a bounded reviewer agent (2026-09-21); its three factual corrections (the self-check LR, the doubly-boundary series, the estimate tolerance) and two softened readings (the null's point mass, the size claim) are incorporated.
