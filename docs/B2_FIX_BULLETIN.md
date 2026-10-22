# QUANTGEN B2 Fix Justification Briefing

## 🔍 Executive Summary
* **Status:** Implemented 2026-09-25, steps 1 to 6 (Appendix E). Acceptance suite 229/229; the shipped code reproduces the prototype's table B.4 (ν intervals to the last digit, standard errors to two figures); adversarial review outcome in E.7, including one real defect it found (a stalled optimiser start) and its fix.
* **Timeline:** Done, including the primer (rebuilt 2026-09-25: new sections 5.8 and 6.5, figure 6 redrawn around the profile likelihood, chapters 6, 7, 9 and 10 updated for B1 and B2).
* **Risk:** Medium. Intervals are honest only when the innovation family is right.

## 🚀 Key Accomplishments
* **Flaw measured:** On 500 sessions a fitted ν of 5.2 carries a 95 % interval of 3.4 to 8.9.
* **Coverage, T = 500:** Wald intervals cover α 91 %, β 93 %, η 93 %, ω 97 % where they exist.
* **Coverage, T = 2000:** 94 % to 97 % for every parameter; every fit has an interval.
* **Profile interval:** Covers η 93 % at T = 500 on all fits; ν 11 to normal on the GBM demo.
* **Sandwich tested:** Median standard errors within 12 % of the Hessian's in every design.
* **Cost measured:** Prototype: covariance 7 to 12 ms, profile 0.3 to 0.4 s on a 57 ms fit. Shipped (E.5): the demo fit goes from 60 ms to 149 ms with the profile.

## ⚠️ Current Roadblocks
* **Wrong family:** Under skewed innovations η is biased by 1.1 SE; coverage falls to 76 %.
* **Near-integrated fits:** 4.5 % of T = 500 fits get no covariance; a step crosses the stationarity cap.
* **Unconditional vol:** Delta-method intervals cover 42 % to 100 % by persistence bucket; none usable.
* **Small samples:** α covers 91 % at T = 500; β estimates spread 2.2 times their median SE.
* **Boundary cut:** The profile end at η = 0 must use the mixture cut 1.35, matching the LR chip.
* **Response time:** The GARCH-t Monte Carlo run is now about twice the GBM run (291 ms against 135 ms at 5,000 paths × 252 sessions).

## 📅 Next Steps
* **Done (step 1):** Observed-information covariance at the optimum (`_hessian`, `_covariance` in `garch.py`); `GarchFit.se` empty and `se_note` set when it fails.
* **Done (step 2):** Profile interval for η (`_profile_eta`), cut 1.92 inside, 1.353 at η = 0, ramped across the first grid cell; the ν tile shows a range.
* **Done (step 3):** Delta-method interval for the persistence; the half-life interval is that interval mapped through the half-life (same coverage, never negative); no interval on the unconditional vol.
* **Done (step 4):** Tiles show "value (low to high)"; chips "SE undefined", "interval touches a bound: …" (α, β, ν) and a muted "persistence interval reaches 1"; narrative and Claude payload carry the same.
* **Done (step 5):** No sandwich.
* **Done (step 6):** `test_interval_coverage_on_simulated_t_garch`: 50 fits at T = 1,000, α, β, η Wald and η profile coverage ≥ 85 % (measured 96 / 96 / 90 / 90 %).
* **Done (primer):** `docs/build_models_primer.py` rewritten for B1 and B2 and `docs/QUANTGEN_Models_Primer.pdf` rebuilt on live AAPL data; see E.8 for what is left as it is.

## 💡 Context & LLM Instructions
* **Audience:** The QUANTGEN operator; also OTM interview preparation.
* **Tone:** Technical, evidential, candid.
* **Action:** FYI. The primer rebuild is the one remaining item and needs the user's go-ahead.

---

## Appendix A. What B2 is, and what the fix does

* **The flaw.** The GARCH strip shows α = 0.176, β = 0.655, ν = 3.1 to three decimals, and the chips say only whether a parameter sits on a bound. Nothing on the screen says how precisely 503 sessions determine any of them. STAT248 21.2.3 gives the answer the fit already has in hand: for a maximum-likelihood estimate, √n (θ̂ − θ) → N(0, I(θ)⁻¹), where I is the Fisher information, equal to minus the expected Hessian of the log-likelihood in the well-specified case. *From Radon-Nikodym to Fung-Hsieh* 3.4 adds the practical warning that P-estimates of tails need decades of data; ν from two years is a tail estimate from two years.
* **The fix, three parts.** (1) The observed information: the negative numerical Hessian of the log-likelihood at the optimum, in the fitted coordinates (ω, α, β, η = 1/ν); its inverse gives standard errors and Wald intervals ±1.96 SE. (2) A profile-likelihood interval for η: the set of η at which the log-likelihood, re-maximised over ω, α, β, stays within a cut of the maximum. Inside the domain the cut is 1.92 (half the χ²₁ 95 % point); at the boundary η = 0 the relevant null is the mixture ½δ₀ + ½χ²₁ that the B1 fix adopted for the LR tile, so the cut there is 1.35 (half of 2.706), and the interval reaches "normal" exactly when the tile says the t did not beat the normal. It maps to ν by 1/η. (3) A delta-method interval for the persistence α + β from the Wald covariance, and the half-life interval obtained by mapping that interval through the (monotone) half-life, so it inherits the persistence coverage and can never go negative (E.2).
* **Why this fix and not a bigger one.** The sandwich (misspecified-model) covariance of STAT248 21.2.3 was prototyped as well; its median standard errors are within 12 % of the Hessian's in every design, including the misspecified one, because misspecification of the innovation family shows up mostly as bias in η, not as a wrong variance. Bootstrapping the fit (hundreds of refits) would cost minutes per series. The profile interval is the one addition that materially changes what the operator sees, because it is the only one that behaves where the guardrails bite: at η = 0 and at ν = 2.5.

## Appendix B. Evidence (prototype `docs/b2_evidence/b2_experiment.py`, 263 s, plus the follow-up runs in `b2_followup.json` and `b2_uncond_buckets.json`)

Method: the app's shipped estimator (`fit_garch`, η parameterisation) on simulated GARCH(1,1) series; standard errors from a central-difference Hessian (forward differences in a coordinate on a bound), sandwich from per-observation scores, profile interval on a 41-point η grid with warm starts and linear refinement of the ends. Truth: ω 2e-6, α 0.08, β 0.90, ν 6 (η 0.1667), persistence 0.98, unconditional vol 15.9 %. Coverage is the share of 95 % intervals containing the truth.

**B.1 Correctly specified t innovations**

| | T = 500 (200 series) | T = 2000 (100 series) |
|---|---|---|
| Fits without a Wald covariance | 4.5 % (all 9 near-integrated: persistence 0.996 to 0.9993, stationarity flag set) | 0 % |
| Wald coverage ω / α / β / η, Hessian, where it exists | 97 % / 91 % / 93 % / 93 % | 97 % / 94 % / 97 % / 95 % |
| Same, counting a missing interval as a miss | 93 % / 87 % / 89 % / 89 % | unchanged |
| Wald coverage ω / α / β / η, sandwich | 96 % / 91 % / 90 % / 91 % | 96 % / 94 % / 97 % / 97 % |
| Profile coverage of η (and so of ν), all fits | 93 % | 97 % |
| Persistence α + β, delta method | 98 % | 97 % |
| Median SE α / β / η (Hessian) | 0.030 / 0.039 / 0.043 | 0.014 / 0.018 / 0.022 |
| Spread of the estimates α / β / η across series | 0.043 / 0.085 / 0.051 | 0.014 / 0.019 / 0.020 |
| Median ν interval from the profile (T = 500) | 3.95 to 11.9 around a truth of 6 | not tabulated |
| Profile reaching η = 0 ("to normal") | 2.0 % with cut 1.92; 0.0 % with the mixture cut 1.35 | 0 % |
| Cost: covariance / profile | 7 ms / 368 ms | 12 ms / 298 ms |

Reading: at the app's window the intervals are close to nominal for ω, β and η and short for α (91 %, 87 % if a missing interval counts as a miss); at four times the data everything is within sampling error of 95 %. The spread of β across series (0.085) is 2.2 times the median SE (0.039): 8.5 % of fits land more than 0.1 from the truth, most of them near-integrated. Those fits carry large standard errors themselves (90th percentile 0.079, maximum 0.82), which is why coverage holds; the SE describes the fit at hand, not the spread of fits one might have obtained. Excluding the fits without a covariance leaves the spread unchanged (0.0855), so the far-off fits are interior ones, not the excluded ones.

**B.2 Misspecified innovations (skewed normal mixture; the t is the wrong family), T = 1000, 150 series**

| | Hessian | Sandwich | Profile |
|---|---|---|---|
| Coverage α / β | 92 % / 95 % | 92 % / 92 % | — |
| Coverage η | 76 % | 77 % | 83 % |
| Persistence | 99 % | 99 % | — |

The fitted η averages 0.135 against 0.167, a bias of −0.032, which is 1.1 median standard errors (0.028); the spread of the estimates (0.028) equals the SE, so the standard error is the right size and the interval is centred in the wrong place. The sandwich cannot repair that; the profile recovers part of it through its asymmetric shape. This is the limit of the fix and the reason B6 (residual diagnostics) stays a separate finding.

**B.3 Delta-method intervals for the unconditional vol, by fitted persistence (T = 500)**

| Fitted persistence | Fits | Median fitted unconditional vol | Median SE | Coverage of the true 15.9 % |
|---|---|---|---|---|
| below 0.95 | 40 | 13.5 % | 0.012 | 42 % |
| 0.95 to 0.98 | 82 | 14.9 % | 0.026 | 85 % |
| 0.98 to 0.995 | 57 | 17.7 % | 0.071 | 95 % |
| 0.995 and above | 21 (12 with an SE) | 46.7 % | 2.97 | 100 % |

Reading: the interval is too narrow when persistence is underestimated (the point estimate is low and so is its SE) and absurdly wide when it is near 1 (a median SE of 297 vol points). No threshold rescues it, which is why step 3 gives the unconditional-vol tile no interval and leaves the existing "near-integrated" chip to carry the message. Persistence itself is covered 92 % to 100 % in every bucket.

**B.4 Series the operator will recognise**

| Series (three are simulated, truth in brackets) | Fit | Wald SE (ω, α, β, η) | ν interval (profile) | Note |
|---|---|---|---|---|
| Recovery-test series, 3,000 obs [α .08, β .90, ν 6] | α 0.072, β 0.910, ν 6.03 | 5.7e-7, 0.010, 0.012, 0.017 | 5.0 to 7.5 | persistence ± 0.006 |
| GBM demo `synthetic_history("AAPL")` (the app's series) | α 0.008, β 0.843, ν 491 | undefined: information matrix not positive definite (smallest eigenvalue −6.2) at an interior near-normal fit | 11.2 to normal | only the profile speaks |
| t(3) series, 500 obs [α .10, β .80, ν 3] | α 0.046, β 0.948, ν 2.74 (persistence 0.994 against a true 0.90) | 4.8e-7, 0.025, 0.031, 0.048 (shipped code: 4.6e-7, 0.024, 0.030, 0.048, see E.3) | 2.50 to 3.66, touching the bound | uncond vol 15 % with SE 0.28: meaningless |
| t(6) series, 500 obs [α .08, β .90, ν 6] | α 0.062, β 0.880, ν 5.17 | 4.4e-6, 0.028, 0.048, 0.045 | 3.45 to 8.93 | persistence ± 0.035 |

**B.5 Sandwich against Hessian.** Median ratios of sandwich to Hessian SE over (ω, α, β, η): 0.88 to 0.95 (T = 500), 0.97 to 1.03 (T = 2000), 0.96 to 0.99 (misspecified). On single series the ratio reaches 0.72 (t(6) series, β), so the two agree in aggregate coverage (differences of 3 points at most), not on every fit.

## Appendix C. Drawbacks, in detail

* **Intervals assume the family is right.** B.2 shows 76 to 83 % coverage of η under a skewed innovation, from a bias of 1.1 SE. The screen would show "ν = 5.2 (3.4 to 8.9)" with the same confidence on a series whose true tail is something the t cannot represent. The interval has to be read next to B6's residual check; it is not a substitute for it.
* **The covariance can fail, and the failure is informative.** At T = 500, 4.5 % of fits had no covariance; every one was near-integrated (persistence above 0.995) and the finite-difference step crossed the stationarity cap into the penalty region. On the GBM demo the information matrix is not positive definite at an interior, effectively-normal fit. Both cases already carry a chip ("near-integrated", "normal innovations"); the tiles need an explicit "SE undefined" state next to it, and the profile interval, which exists in both cases, must be the fallback rather than an option.
* **Derived quantities do not inherit the guarantee.** B.3: the delta method for ω/(1 − α − β) fails in both directions, too narrow below persistence 0.95 (42 % coverage) and useless above 0.995 (SE of 297 vol points). Persistence is fine (92 to 100 %), and the half-life interval, being the persistence interval mapped through a monotone function, has the same coverage. The rule "no interval on the unconditional vol" is measured, not chosen.
* **Small-sample behaviour.** α covers 91 % at T = 500 (87 % counting missing intervals as misses) against 95 %; the Wald interval is symmetric where the sampling distribution of a positive parameter near 0 is not. A profile interval for α would fix it at another 0.3 s; not proposed now. The spread of β across series is 2.2 times the median SE, a fact about how variable a 500-session fit is that no single interval can convey.
* **Boundary consistency.** With the textbook cut 1.92 at η = 0 the profile interval would say "to normal" on 2 % of null-free series where the LR chip, which uses the mixture cut 2.706, says the t beats the normal. Using 1.35 at that end (0 % in the same series) keeps tile and chip consistent; its calibration at the boundary is not tested by B.1, whose truth is interior.
* **Cost.** The covariance is free (about 10 ms); the profile interval adds 90 to 150 ms to a fit of 60 to 90 ms (E.5; the prototype's scan without early stopping cost 0.3 to 0.4 s), so the Quant Lab's GARCH-t run is about twice the GBM run. Acceptable for an interactive lab; the primer's rebuild and the acceptance suite both grow (the coverage test alone is 20 to 30 s).
* **Numerical fragility.** Finite-difference Hessians depend on step sizes (relative 1e-3 in ω, 1e-4 in α, β, η here) and on staying inside the domain; the prototype's first bound test used an absolute tolerance that miscounted small ω as "on the floor" (recorded in the script). The implementation must catch every failure and say "SE undefined" rather than print a number.
* **Display and vocabulary.** ν's interval is asymmetric and can be one-sided, so the tile shows a range, not ±; three new chips join a strip that already has five; the narrative gains one precision sentence covering every parameter; primer sections 5.1, 6.3 and 7.6 must be rewritten; the interval logic added about 210 lines to `garch.py` (the estimate here was 120).
* **What the fix does not change.** Identification of ν on 500 sessions is what it is: a median interval of 4 to 12 around a true 6 is the point. B2 makes the fragility visible; it cannot remove it.

## Appendix D. Sources

* STAT248 *Applied Time Series* notes, §21.2.3: MLE asymptotics, the Fisher information as minus the expected Hessian, and the misspecified (sandwich) covariance.
* Primer 5.1 and 6.3 (the tiles and the reading of ν), 6.4 (the LR test the profile interval inverts), 7.6 (the guardrail table the chips extend).
* *From Radon-Nikodym to Fung-Hsieh*, §3.4: P-estimates of tails need decades of data.
* `docs/ARCHITECTURE_REVIEW.md`, finding B2; `docs/B1_FIX_BULLETIN.md` for the η parameterisation and the mixture cut the intervals are built on; the 57 ms fit time is Appendix E there.
* Prototype and raw results: `docs/b2_evidence/b2_experiment.py`, `b2_results.json` (main run), `b2_followup.json` (GBM diagnosis, misspecification bias, ν interval ends and boundary cuts), `b2_uncond_buckets.json` (unconditional-vol coverage by persistence).
* A bounded reviewer agent checked the first draft against the raw results (2026-09-21); its corrections (the bound-versus-no-covariance conflation, the spread explanation, the ν gloss, the series labels, the GBM diagnosis, the vol level, the boundary cut, the unconditional-vol rule) are incorporated with the follow-up measurements above.

## Appendix E. Implementation (2026-09-25) and what the app now does

**E.1 What landed.** `core/quant/garch.py`: `_ll_or_none` (the log-likelihood or None outside the domain, so the finite −10¹⁰ stationarity penalty never enters a difference quotient), `_hessian` (central differences in the optimiser's scaled coordinates, ω × 10⁶; one-sided away from the bound in any coordinate that sits on one), `_covariance` (Cholesky test, inverse, mapped back to natural units), `_fit_fixed_eta` and `_profile_eta` (the profile scan), `_half_life`; `GarchFit` gained `se`, `se_note`, `eta_interval`, `interval_at_bound`, `interval(name)`, `nu_interval`, `half_life_interval`; `fit_garch(profile=True)` computes all of it and puts ± and the ν range into `note`. `ui/quant_lab_page.py`: tiles "value (low to high)" for α, β, α+β, half-life and ν, tooltips naming the method, chips "SE undefined" (with the reason), "interval touches a bound: …" and "persistence interval reaches 1", five new payload fields. `core/quant/insights.py`: one precision sentence in the calibration paragraph. `tests/quant_acceptance.py`: the coverage test of step 6 plus interval assertions in three existing tests; `profile=False` in the 200-fit null test. `README.md` and `docs/ARCHITECTURE_REVIEW.md` §1.3 record the change.

**E.2 Where the implementation departs from the approved wording, and why.**
* *Half-life interval.* Step 3 said "delta-method intervals for persistence and half-life". The persistence interval is the delta-method one; the half-life interval is that interval mapped through h(p) = ln ½ / ln p, which is monotone, so it has exactly the persistence coverage (97–100 % in B.1) and can never go negative, which a delta-method interval on h itself does near h = 0 and cannot avoid.
* *The boundary cut is ramped, not stepped.* With a cut of 1.92 inside and 1.353 at η = 0, a series whose LR lies between 2.706 and 3.841 has a not-rejected set that is open at 0. The implementation ramps the cut linearly across the first grid cell (0 to 0.01), so the lower end is continuous in the data and the interval reaches 0 exactly when LR ≤ 2.706 (`fit.lr_t_vs_normal <= LR_5PCT`): tile and chip cannot disagree.
* *ω is not in the bound chip.* On six live series ω's interval reached 0 in four, and in 28 % of the T = 1,000 simulations; ω has no tile, so the chip would have named a number the operator cannot see. Its standard error stays in `se` and in the payload.
* *Persistence gets its own chip.* The persistence interval reaches 1 on all six live series and 84 % of T = 1,000 simulations with a true persistence of 0.98: a two-year sample rarely excludes an integrated variance. As part of the error chip it would have made the chip permanent; it is a muted chip with the tooltip "an integrated variance is not excluded at 95 %".
* *A `profile` knob.* The profile interval costs 90 to 150 ms on 500 sessions; `fit_garch(profile=False)` exists for callers that fit in loops (the null-size test's 200 fits would otherwise take 20 to 30 s longer).
* *A second start at the decisive points.* Rebuilding the primer's figure 6 (the full profile curve of the demo series) showed a notch: warm-started along that series' flat α = 0 ridge, the fixed-η refits stalled between η = 0.07 and 0.10 and the curve dropped and jumped back. A profile is the maximum of a smooth function and must be continuous, so this is an optimiser failure; in the app's own scan a stalled refit outside the cut would narrow the interval or stop the scan early. Each refit that lands outside the cut is therefore retried from the joint optimum and the better result kept (`_fit_fixed_eta` takes a list of starts). No interval on the reference series changed; the figure is smooth.
* *The Hessian is taken in scaled coordinates.* The first cut divided instead of multiplying by the scale and printed an ω standard error of 5.7 × 10⁵; the recovery-series smoke test caught it (the prototype's value is 5.7 × 10⁻⁷) and the acceptance test now pins that series' standard errors to the prototype's independent numbers within 15 %, two-sided.
* *The profile scan doubles as a check on the joint fit.* The review (E.7) found that on some 500-session seeds the joint optimiser stalled below the maximum (seed 7012: ν 3.3 with an interval of 3.0 to 15.6 and "SE undefined", while the scan's own refit at η = 0.20 was 6.7 log-likelihood units higher). The cause was pre-existing: the third default start, β₀ = 0.95 with α₀ = 0.05, sat exactly on the stationarity penalty with ω₀ = 0, so it was dead. It is now β₀ = 0.94, and `_profile_eta` returns any refit that beats the joint fit, from which `fit_garch` re-seeds the fit (at most twice). Seed 7012 now gives ν 5.0 (3.5 to 7.9) with every interval defined. On the demo series the live third start moved the fit along the flat ridge of an iid series from (α 0.008, β 0.843) to (α 0, β 0.991), 0.011 log-likelihood units higher; α = 0 leaves β unidentified, and the narrative now says so ("alpha at 0: no reaction to shocks, so beta and the half-life are not identified") where it used to show a half-life of 4 sessions without a caveat.

**E.3 Agreement with the prototype (table B.4).** `docs/b2_evidence/b2_app_reference.json`.

| Series | Prototype SE (ω, α, β, η) and ν interval | Shipped code |
|---|---|---|
| Recovery, 3,000 obs | 5.7e-7, 0.010, 0.012, 0.017; 5.0 to 7.5 | 5.72e-7, 0.0102, 0.0117, 0.0175; 4.97 to 7.50; half-life 38 (22 to 122) |
| GBM demo | undefined (not positive definite); 11.2 to normal | undefined, same reason; 10.9 to normal; LR 0.0; the fit itself moved to α = 0 (E.2, last bullet) |
| t(3), 500 obs | 4.8e-7, 0.025, 0.031, 0.048; 2.50 to 3.66 | 4.62e-7, 0.0243, 0.0299, 0.0482; 2.50 to 3.66; chips: α, β, ν, persistence |
| t(6), 500 obs | 4.4e-6, 0.028, 0.048, 0.045; 3.45 to 8.93 | 4.4e-6, 0.0276, 0.0477, 0.0455; 3.45 to 8.93; chip: persistence |

The t(3) standard errors differ by 3 to 4 % because that fit sits on the ν bound and the app takes a one-sided difference there where the prototype stepped across the bound.

**E.4 Coverage at the acceptance test's design (50 series, T = 1,000, truth ω 2e-6, α 0.08, β 0.90, ν 6).** `docs/b2_evidence/b2_app_coverage_T1000.json`.

| | ω | α | β | η | persistence | η by profile |
|---|---|---|---|---|---|---|
| Coverage of the 95 % interval | 96 % | 96 % | 96 % | 90 % | 100 % | 90 % |
| Median standard error | 1.0e-6 | 0.021 | 0.025 | 0.030 | 0.013 | — |
| Spread of the estimates | — | 0.018 | 0.024 | 0.035 | — | — |

No fit lacked a covariance; 4 % carried the near-integrated flag. The median ν interval is 4.3 to 9.0 around a truth of 6; none reached the normal (no LR at or below 2.706 in 50 series, as it should be on a ν = 6 truth). The persistence interval reached 1 in 84 % of fits and ω's reached 0 in 28 % (hence E.2). At n = 50 one interval is 2 points, so η's 90 % is within sampling error of the 93 to 95 % of B.1.

**E.5 Cost, measured alone on a quiet machine after every fix (best of five; `docs/b2_evidence/b2_app_timing.json`).**

| | Fit without profile | Fit with profile | Monte Carlo, 5,000 paths × 252 sessions |
|---|---|---|---|
| Demo series (503 obs, effectively normal) | 60 ms | 149 ms | GARCH-t 291 ms (GBM 135 ms) |
| t(6) series, 500 obs | 89 ms | 239 ms | — |
| Recovery series, 3,000 obs | — | 351 ms | — |

The profile costs 90 to 150 ms on 500 sessions (the early stop and warm starts make it cheaper than the prototype's 0.3 to 0.4 s; the second start at the points outside the cut, added while rebuilding the primer, is 25 to 60 ms of that), the covariance about 10 ms, and the live third start about 10 ms; the Quant Lab's GARCH-t run is about twice the GBM run. Figures quoted earlier in this appendix's first draft (79 → 216 ms) were taken while the review agents were running their own fits on the same machine.

**E.6 Six live series through the Quant Lab (2026-09-25, 503 sessions each, 5,000 paths, 63-session horizon).** `docs/b2_evidence/b2_real_series.json`. The columns are what the tiles show.

| Symbol | Source | α (95 %) | β (95 %) | α+β (95 %) | Half-life, sessions | ν (profile) | LR | Chips: interval reaches | Cond / uncond vol | Run, ms |
|---|---|---|---|---|---|---|---|---|---|---|
| AAPL | FMP | 0.183 (−0.013 to 0.380) | 0.645 (0.283 to 1.007) | 0.829 (0.566 to 1.092) | 4 (1 to inf) | 3.1 (2.5 to 4.4) | 85.0 | α, β, ν; persistence | 24.3 % / 33.1 % | 571 |
| MSFT | FMP | 0.110 (0.001 to 0.220) | 0.844 (0.692 to 0.996) | 0.954 (0.849 to 1.060) | 15 (4 to inf) | 3.2 (2.6 to 4.4) | 149.6 | persistence | 24.7 % / 35.4 % | 666 |
| NVDA | FMP | 0.056 (−0.024 to 0.135) | 0.889 (0.699 to 1.079) | 0.945 (0.823 to 1.067) | 12 (4 to inf) | 6.4 (4.2 to 11.2) | 39.5 | α, β; persistence | 37.0 % / 42.0 % | 573 |
| SPY | FMP | 0.120 (0.036 to 0.203) | 0.804 (0.693 to 0.914) | 0.923 (0.838 to 1.009) | 9 (4 to inf) | 4.2 (3.0 to 6.5) | 59.5 | persistence | 13.1 % / 15.7 % | 863 |
| 005930 | KIS | 0.105 (0.034 to 0.176) | 0.882 (0.805 to 0.960) | 0.987 (0.953 to 1.022) | 55 (14 to inf) | 6.5 (4.2 to 13.8) | 16.4 | persistence | 52.3 % / 62.3 % | 1,198 |
| 000660 | KIS | 0.090 (0.033 to 0.146) | 0.887 (0.818 to 0.955) | 0.976 (0.940 to 1.012) | 29 (11 to inf) | 8.3 (4.5 to 28.7) | 8.2 | persistence | 61.9 % / 72.3 % | 776 |

Reading. Every live fit has a covariance (the "SE undefined" state appeared only on the effectively-normal demo series). The tail is the best-determined thing on the US names: AAPL's ν = 3.1 sits in 2.5 to 4.4 with an LR of 85, so "heavy tails" is not in doubt; what the intervals expose is the dynamics: AAPL's α of 0.183 comes with an interval that includes 0, its β of 0.645 with one from 0.28 to 1.0, and its half-life of 4 sessions is "1 to inf". The two KRX names are the opposite case: α and β are determined to ±0.04 and ±0.08 but the tail is not (ν 8.3 in 4.5 to 28.7 on SK hynix, an LR of 8.2 that clears 2.706 without much to spare). No live series reaches "normal". The persistence chip is on for all six, which is the honest statement that 503 sessions do not exclude an integrated variance at 95 %; the near-integrated (> 0.995) flag is on for none.

**E.7 Adversarial review (2026-09-25).** Five reviewer agents, one dimension each (numerical covariance, profile interval, operator-facing surface, tests, documentation), produced 27 findings; each was judged by three refuter agents with distinct lenses (reproduce, read the code, spec conformance). Because the fixes were applied while the refuters ran, most verdicts read "refuted: already in the file"; the list below is what changed as a result, by reviewer.
* *Profile.* (high) The stalled-optimiser defect above; fixed at the root (the dead start) and guarded (re-seed from the scan). (low) The boundary decision and the LR chip must be the same floating-point expression, or the two can disagree within one ulp of the line: the first draft tested `ll_normal >= ll_max − 1.353`; the refuters then showed that even with the chip's expression in place the ramp's numerator, written `ll_max − 1.353 − ll_normal`, rounds to exactly 0 for one double value of the LR per binade (they found the case at LR = 2.706000000000131) and would put the lower end at 0 while the chip says the t won. Both now derive from the one value `lr = max(0, 2(ll_max − ll_normal))`: the test is `lr <= 2.706` and the ramp numerator `(lr − 2.706)/2`, which is positive exactly when the test fails; the lower end is also clamped strictly above 0 on that branch. Probability per fit of the order of 10⁻¹³; a correctness-of-promise fix, not an observed one.
* *Covariance.* (low) One-sided differences at a bound reused the central step 10⁻⁴, whose O(h) truncation inflated the standard errors by about 6 % on a fit with ν at 2.5; the one-sided step is now 10⁻⁵. (low) `GarchFit.interval("eta")` raised because there is no `eta` attribute; handled.
* *Surface.* (medium) The green "GARCH guardrails clear" chip was decided before the "SE undefined" and "interval touches a bound" chips existed, so it sat next to a red one; the order now matches the note's "no guardrail hit" rule. (medium) The narrative printed the persistence interval at three decimals, so an upper end of 0.9997 read "1.000" while the tile said 0.9997 and the half-life was finite; four decimals now. (low) With α at its bound the LR tile is greyed but the ν range, which inverts the same boundary null, was not; it is greyed with the same tooltip and the narrative carries the caveat. (low) The narrative's precision sentence had no test; it has five assertions now.
* *Tests.* (high) The boundary rule was only exercised at LR ≈ 0 and LR > 9, never in the band (2.706, 3.841] where the mixture cut and the interior cut disagree; the null-size test now refits, with the profile on, the first two null seeds inside the band and two below the line, and asserts the range says "normal" exactly when the chip does. (high) Standard errors were pinned only from below (an interval that contains the truth); the recovery series is now pinned two-sided to the prototype's numbers. (medium) Nothing asserted that an interval reaching a bound is flagged; a new test uses the t(3) series of B.4. (low) A dead assignment in the coverage test and two assertions that could not fail were tightened.
* *Documentation.* Eleven stale statements (status, the half-life wording, the 57 ms figure, the t(3) row, the ramp, the size estimates, §1.3, the B2 finding's closing note, the README counts, the module docstring, and the note listing the persistence next to the bound names) were corrected; every one of them is either in this appendix or in the files named.
* *Not changed.* The reviewers confirmed, by independent finite differences in natural units, that the shipped standard errors on the recovery series match the prototype's, that the four reference series reproduce table B.4, that the headless driver runs clean, that the payload serialises, and that a missing covariance counts as a miss in the coverage test.

**E.8 Left as it is.**
* The primer was rebuilt on 2026-09-25 for B1 and B2 (sections 5.8 and 6.5 added; 6.3, 6.4, 7.3, 7.5, 7.6, 7.7, 7.8, 9.3, 9.5 and chapter 10 rewritten; figure 6 redrawn as the profile likelihood of both series; the tile and chip strings in chapter 9 are taken from the UI function itself). The A1/A2 material was touched only where the text transcribed code that had changed (the `_draw_z` listing and the cap in 6.2, one sentence in 3.2, the drift-mode formulas in 8.6 and 10.2, the bound-note row in 9.5); the drift chapter has not been rewritten around the per-model correction.
* α's Wald interval is symmetric where α's sampling distribution near 0 is not (AAPL and NVDA above show negative lower ends): the chip flags it; a profile interval for α would fix it at another 0.15 s and was not proposed.
* The intervals assume the t is the right family (B.2: 76 to 83 % coverage of η under a skewed innovation). B6, the residual diagnostic, remains the finding that would tell the operator when that assumption fails.
* The chosen cut at the boundary (1.353, ramped) is consistent with the LR tile by construction; its finite-sample calibration at the boundary is not tested by B.1 or E.4, whose truths are interior. The null-size test of B1 covers the LR chip, and the profile's lower end is tied to it, so the two cannot drift apart.
