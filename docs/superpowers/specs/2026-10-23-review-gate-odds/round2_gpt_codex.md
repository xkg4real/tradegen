# Round 2, GPT via Codex CLI

Run 2026-10-23 on spec rev 2.1 (72a4110) with codex exec --sandbox read-only, from a disposable repo copy (no .git, no .env). The quota note in the brief (exhausted until 2026-10-27) proved stale: a probe call worked.

## Verdict

**REJECT.** Revision 2.1 fixes several round-1 integration errors, but it still cannot support its central guarantees. The KRX simulation can violate daily price limits; the claimed KRX impossibility bound contradicts the supplied research; neither the dynamic-programme bound nor the HIDDEN_EDGE test is certified as specified; and D13 does not prevent a strategy’s backtest edge from being attached to a different strategy. The compliance design also has unresolved eligibility, transfer, exit and owner-authentication problems. These require changes to the specification before implementation.

This was a read-only review of the spec, both round-1 reviews, the supplied research and the cited implementation. No files were created, changed or deleted. Test suites and the backtest runner were not executed because they write files. D13 reproduction and Git tracked/unchanged status were **not** established.

## Round-1 rulings

“Accepted” is often justified as a decision to address a finding, but several entries incorrectly imply that the revised text completes the fix.

| Finding IDs | Assessment |
|---|---|
| **G-1 / L5** | The spot-crypto ETP classification fix is useful, but the broader prohibition conflates spot-backed and futures-backed funds. See Minor 3. |
| **G-2 / G-5 / L10** | Coverage and attribution improved, but the Gopax explanation repeats a claim the verification notes did not confirm. See Minor 3. |
| **G-3 / L2** | Partially fixed: a seven-day cash snapshot cannot implement a current-cash check before every additional purchase. See Major 1. |
| **G-4 / Z8 / L3** | Partially fixed: the withdrawal row exists, but the symbol/class validation rules still make transfers inconsistent. See Major 12. |
| **G-6 / S1 / S-missed-2** | Independent signs and discrete checkpoints fix the original serial-sign and historical-extrema problems. The KRX clipping construction remains invalid. See Major 3. |
| **G-7 / S3** | Constructing KRW returns before normalization fixes the FX issue. Limit-down carry still invalidates the proposed floor argument. See Major 6. |
| **G-8** | Not fixed merely by introducing `L_min`: its definition does not establish a lower bound over delayed liquidation. See Major 6. |
| **G-9 / S2 / S6 / S7** | Pathwise brackets improve the design, but sizing still omits fixed fees and the dynamic programme remains uncertified. See Major 5 and Major 7. |
| **S5** | The empirical-Bernstein replacement uses an unsupported range. See Major 8. |
| **S9** | Model-versus-market wording improved, but the KRX “legal bound” remains false. See Major 4. |
| **G-15 / I2** | The API mismatch is fixed; the symbol-based cost-classification defect remains. See Minor 1. |
| **G-17 / I6** | D13 reasonably identifies eligible artifact types, but eligibility is not reproduction or permission to transfer an edge between strategies. See Major 9 and Minor 2. |
| **G-18 / Z6 / L-missed-2** | D11 is not consistently implemented by the evaluation order and error-handling contracts. See Major 13. |
| **G-19 / Z4 / Z-missed-2 / H-F1** | Hash approval and TTY confirmation improve accidental-misuse protection. They do not authenticate the owner against an agent or script with the same access. See Major 14. |
| **Z1** | Re-running `decide()` is the correct safety improvement, but permit verification and reservation accounting remain inconsistent. See Major 15 and Minor 7. |
| **G-11 / S4 / H-F7 / S-missed-1** | Typical-first presentation is fixed; the average calculation is still wrong when successful paths overshoot the target. See Major 10. |
| **H-missed-4 / H-missed-2 / H-F9** | Copying the research’s conjectured odds does not validate them, and some required owner-facing statements remain false. See Major 11. |
| **G-13 / I4** | Refusing unsigned calendars is sound; the owner’s signing procedure omits required manifest changes. See Minor 4. |

The rejection of **L6** is defensible as fidelity to the report, which explicitly gates KRX derivatives (`reports/Korean resident trading venue legality.md:98`). This does not excuse admitting recourse products into the narrower odds engine.

The rejection of the **G-5 historical-backtest objection** is sound under the stated live-decision meaning of the gate. **G-10 / I-missed-3** is reasonably resolved by single-leg scope, although single-leg FX timestamp alignment still needs definition.

The revised common-random-number design, cosmetic-field exclusion, cost API selection, separate open/close loader, local carry-cost constant, unsigned-calendar refusal, monthly review cadence, warning-hash binding and additional counsel questions are substantive improvements.

The **Clopper–Pearson example and Bonferroni correction in S10 are mathematically sound for fixed, valid bounds**. Common random numbers do not invalidate Bonferroni. The remaining problem is treating an estimated dynamic-programme value as such a bound.

## Major

1. **The per-buy cash eligibility check can authorize purchases using obsolete cash.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:308,469–471,517`; `research_notes/Korean resident trading venue legality/domestic_securities_derivatives.md:62–68`; `research_notes/Korean resident trading venue legality/overseas_via_brokers_verification.md:22`.

   The row requires KRW 30M qualifying cash before every new or additional purchase, but the kernel accepts cash snapshots up to seven days old. Rechecking the same snapshot after purchases or withdrawals does not establish that the cash remains available. The cited FSC material also distinguishes settled cash from unsettled proceeds and requires immediate recognition of purchase deductions. [FSC release](https://fsc.go.kr/eng/pr010101/87405).

   **Concrete fix:** Separate durable eligibility evidence—courses and broker approvals—from current financial state. Require fresh, broker-derived qualifying cash, pending-order reservations and immediate purchase deductions at authorization and send time. Until this evidence exists, return a named refusal. A weekly owner snapshot may support research screening, but cannot establish the live purchase condition.

2. **The domestic lending gate omits current asset restrictions and borrowing constraints.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:287–288,326`; `research_notes/Korean resident trading venue legality/feasibility_base_rates_verification.md:14`; `research_notes/Korean resident trading venue legality/crypto_domestic_and_overseas.md:14–20`.

   Top-20 capitalization or listing on three KRW markets is insufficient. The supplied evidence also excludes trading-caution and suspicious-activity assets and describes collateral and individual borrowing limits. A newly restricted top-20 coin can still satisfy the proposed map. A caller-supplied `leverage=1` does not prove sufficient collateral. These additional requirements are confirmed in the [FSC lending guideline](https://www.fsc.go.kr/no010101/85247).

   **Concrete fix:** Require current venue-confirmed borrowing and collateral eligibility, collateral value, outstanding loans, reserved borrowing and the applicable customer limit. Fail closed on missing evidence. Alternatively, explicitly leave lending unsupported until these facts are representable. Distinguish DAXA/venue requirements from statutory user prohibitions.

3. **The sign-flip bootstrap cannot satisfy the specified KRX daily limits and conditional-martingale claim simultaneously.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:611–627,900–904`; `core/quant/garch.py:674–702`.

   Independently clipping each half-step to `[0.7, 1.3]` allows a session factor of `1.3² = 1.69`.

   This is possible using a valid historical bar: previous close `100`, open `70`, close `100`. Both absolute half-step log moves are `ln(10/7)`. With `k=1`, each clipped sign pair is `{1.3, 0.7}`, with mean one. Two independent positive signs produce a simulated close of `169`, outside that day’s legal band.

   Anchoring clipping to the previous close instead requires normalization conditional on the **current simulated price and fixed daily bounds**, not merely `k(x)`. At the upper daily boundary, a martingale constrained below that boundary must remain there until the boundary changes.

   **Concrete fix:** Specify the daily reference-price interval and a state-dependent transition kernel. Verify conditional means after each possible overnight branch and verify both checkpoints remain inside the same daily interval. Do not repair independent half-step clipping with a final clamp: that changes the expectation again. The GARCH adapter likewise needs its clipped conditional distribution and numerical tolerance explicitly defined.

4. **The claimed KRX market-wide impossibility bound is false.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:81–84,713–716`; `reports/Korean resident trading venue legality.md:165`; `research_notes/Korean resident trading venue legality/domestic_securities_derivatives_verification.md:25`.

   The research explicitly says `1.3^n` is **not a strict ceiling**. Daily limits apply relative to a reference price, not every trader’s purchase price. Buying at `0.7` of that reference and selling at `1.3` gives a gross factor of approximately `1.857`, compatible with open/close trading. IPO and special reference-price regimes introduce further exceptions. This does not establish that such trading is feasible or probable; it disproves the stated upper-bound argument. [KRX reference-price rules](https://regulation.krx.co.kr/contents/RGL/03/03020201/RGL03020201.jsp).

   **Concrete fix:** Restrict `1.3^n` to the holding and reference-price assumptions for which it is proved. Derive any broader structural maximum from allowed entry/re-entry times and applicable instrument regimes. Remove the market-wide “IMPOSSIBLE” refusal until that proof exists.

5. **The stake equations can spend unavailable cash and breach the floor without any gap.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:567–586,661–668`.

   The cash cap `s ≤ W/(1+κ)` leaves no cash for the fixed entry fee `φ`. The general at-risk cut omits both fixed fees. Consequently, fixed-fraction or Kelly sizing can violate the intended floor even when the stop fills exactly. The bold formula also needs refusal rules for nonpositive numerators or a net win coefficient `u−κ(2+u) ≤ 0`.

   A single `κ` cannot simultaneously include a sell-only tax and be applied unchanged to both sides.

   **Concrete fix:** Define separate entry/exit rates and fixed charges. At minimum, enforce:

   \[
   s(1+\kappa_b)+\phi_b\le W,
   \]
   \[
   s[d+\kappa_b+\kappa_s(1-d)]+\phi_b+\phi_s\le W-L.
   \]

   Derive bold sizing from that same ledger; refuse unaffordable or nonpositive-payoff cases. Define the at-risk rule for `bracket=None`, where `d` currently does not exist. Reapply affordability after lot rounding and the selected cost scenario.

6. **`L_min` is defined over one price check, but the ceiling requires a lower bound over the complete liquidation process.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:692–693,707–710`.

   Consider `W=100`, `L=50`, `s=100`, `d=0.30`, without fees. A first limit-down leaves `70`, above the floor, but triggers a stop that the simulator cannot execute. Another limit-down leaves `49`; further blocked exits can reduce wealth again. A one-check bound therefore cannot justify `L_min=L`.

   The text saying worst equity is “at most 0 under limited liability” also reverses the relevant inequality.

   **Concrete fix:** Prove a lower bound on stopped/liquidated wealth across all carried positions, remaining sessions and costs. Use `L_min=0` conservatively for genuinely nonnegative cash/spot wealth unless a stronger bound is established. The formula
   \[
   P(\text{reach }T)\le\frac{W_0-L_{\min}}{T-L_{\min}}
   \]
   is sound once that global lower bound and the supermartingale assumptions actually hold.

7. **`bracket_optimum` is an estimated benchmark, not a certified upper bound.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:617–627,718–727`; `core/quant/garch.py:689–701`.

   `V(w,k)` omits state affecting future brackets: GARCH variance, bootstrap continuation state, the date/reference price, unit constraints and pending liquidation. A fresh unconditional bracket law does not reproduce the simulator’s conditional process.

   Upward wealth rounding addresses one discretization error. It does not bound error in a **simulation-estimated transition law**, which can miss a rare winning branch. Clopper–Pearson intervals on a separate target count do not fix uncertainty in the benchmark.

   **Concrete fix:** Include sufficient market/execution state, or prove that a simpler process is a relaxation of every allowed policy. Include realized payoffs, overshoots and durations. Use simultaneous confidence sets for estimated transitions and optimize over those sets, or label the result an estimated reference and remove it from certified breach checks. Define an actual admissible-stake superset, including fractional stakes.

8. **The HIDDEN_EDGE empirical-Bernstein guarantee does not apply to the specified statistic.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:783–787`; `core/quant/garch.py:594–611,654–670`.

   The test uses
   \[
   X=W_\tau+C_\tau-W_0,
   \]
   but its proposed range only concerns `Wτ`. Cumulative costs must also be bounded. Furthermore, “max overshoot” must be a proven support bound, not the largest simulated observation.

   The supported GARCH implementation switches sufficiently large-ν fits to **unbounded normal innovations**. For unclipped US/crypto paths, there is then no finite deterministic maximum overshoot. The stated empirical-Bernstein theorem requires bounded observations. [Maurer–Pontil, Theorem 4](https://www.cs.mcgill.ca/~colt2009/papers/012.pdf).

   **Concrete fix:** Prove deterministic bounds for the complete tested variable and use its appropriate sample variance. For unbounded cases, use a justified alternative with explicit assumptions, controlled truncation error, or report the diagnostic as unavailable. The displayed detection threshold is not automatically a statistical-power guarantee.

9. **D13 permits an edge to be transferred to an unvalidated strategy, and Kelly’s required confidence bound is undefined.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:547–552,574–577,638–650`; `docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json:4–25,27–38,61–65`; `core/quant/strategies.py:69–90,379–387`.

   The candidate validates a specific KRW-BTC long/flat trend strategy. Its **net strategy P&L** is not a market-price process that can be attached to another symbol or wrapped in arbitrary brackets. Reproducing the original card does not validate those altered rules. Its P&L already contains trading costs, creating further ambiguity when the odds engine charges entries and exits again.

   Kelly requires a lower 95% bound on the OOS **mean**. The card supplies a 90% **Sharpe** interval. The spec does not define the mean-bound estimator, serial-dependence treatment, selection treatment or the conservative return distribution used in optimization.

   **Concrete fix:** Bind the edge reference to the reproduced instrument, strategy, signal timing, execution rules and cost accounting. Changed strategies require new validation. Define and record the mean confidence bound from reproduced OOS returns; do not substitute a Sharpe endpoint. Specify feasible net-return Kelly optimization, with zero exposure when conservative growth is nonpositive.

10. **The report discards successful-path overshoot and leaves compounding outcomes ambiguous.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:620–630,686–690,738–748,783–784`.

   Successful exits fill at actual prices and can exceed `T`, but the reported mean substitutes `P(REACHED) × T`. That understates average wealth and can contradict the actual-fill HIDDEN_EDGE calculation. The remaining paths must also be weighted correctly; a conditional mean over unsuccessful paths cannot simply be added.

   Only moonshot paths stop at `T`. A compounding path can reach `T` and subsequently finish below it or hit the floor. The current four-way partition does not clearly distinguish “ever reached” from terminal status.

   **Concrete fix:** Compute means and standard errors directly from actual terminal liquidation values. Store a separate first-passage indicator for “reached by deadline” and an explicitly disjoint terminal outcome. Define the horizon treatment of positions whose liquidation remains blocked.

11. **The owner-facing claims overstate what the evidence establishes.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:70,92–98,761–762,812–816`; `research_notes/Korean resident trading venue legality/feasibility_base_rates.md:30,160–178`; `reports/Korean resident trading venue legality.md:163`.

   The research found no measured probability for turning this account into 1,000× within a month. Its `0.01%–0.03%` numbers are reasoning-based estimates, yet the spec presents them as “realistic odds” under “checked by direct computation.”

   The caption that the highest target probability **always** comes from betting most and soonest is also false for general conditional martingales. For example, with `W₀=1`, `T=1.99`, independent fair factors `{1.01,0.99}` followed by `{1.99,0.01}`, investing throughout reaches the target with probability 25%; waiting through the first step and then investing reaches it with probability 50%.

   “In every retail group studied, most traders lose” is unsupported: the supplied Korean full-sample loss rate is 46%, and Kalshi’s quoted 32% is an average loss statistic, not a losing-trader frequency.

   **Concrete fix:** Remove or explicitly label the target-odds conjectures. Restrict bold-play optimality to its stated benchmark assumptions. Present historical studies with their populations, dates and actual statistic. Replace “lose the stake” with “hit the loss floor or become unable to trade,” showing recoverable balances separately.

12. **The gate conflates asset classification with transaction action and financing.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:268–294,404–418,450–452,484,547–551,590–592`.

   A symbol maps to one class, but the vocabulary mixes assets with actions. The same coin cannot simultaneously map to `crypto_spot` for trading and `crypto_transfer` for withdrawal. Transfers allow `symbol=None`, yet the evaluation order rejects unknown symbols globally. Likewise, one equity symbol cannot independently be a cash share, `credit_buy` and `retail_short`.

   The odds refusal checks leverage, but `Leg` has no leverage field. Although the instrument map contains product multiples, the kernel explicitly derives only the class; it does not require the caller’s default `leverage=1` to agree with that multiple.

   **Concrete fix:** Separate immutable asset identity/class from transaction action, financing, position direction and product multiple. Define transfer source-asset and destination screening explicitly. Derive product leverage from approved metadata and enforce the odds engine’s supported-product whitelist before constructing a price model.

13. **D11 exits are still subject to contradictory blocking rules.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:141–142,454–462,513–514,953–957`.

   Step 1 blocks every intent for invalid/unapproved tables, maps or a broken owner chain before reaching the exit exception. Other sections say those failures block only new exposure. The exit section first conditions permission on the absence of a hard-block venue row, then says even a hard-block venue row permits an exit.

   The only recognized position close is a sell reducing an existing long. A buy-to-cover is not represented, despite shorting remaining in the gate’s scope. Returning early from the exit branch also needs an explicit statement of which address and destination checks still apply.

   **Concrete fix:** Specify one decision table for new exposure, closing a long, covering a short and domestic withdrawal. Preserve conduct/hard-coded prohibitions. Define the trusted metadata and address evidence required for exits when ordinary approvals are stale or invalid. If corruption makes automated withdrawal unsafe, state the manual recovery path instead of promising unconditional availability.

14. **TTY confirmation and an unkeyed hash chain cannot guarantee that Claude cannot act as the owner.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:241–249,507–527,1029–1030`; `core/quant/gate_ledger.py:291–316,344–361`.

   A random code displayed in a terminal is available to the process controlling that terminal. Windows pseudoconsoles explicitly provide programmatic input and output streams. Thus a TTY check distinguishes a pipe from a console interface, not a human owner from automation. [Microsoft pseudoconsole documentation](https://learn.microsoft.com/en-us/windows/console/createpseudoconsole).

   An unkeyed chain detects unrecomputed edits but cannot authenticate a correctly hashed forged append. Previous email anchors do not prevent a counterfeit append extending the genuine anchored prefix.

   **Concrete fix:** Retain D14 as confirmation UX, but put authoritative owner writes behind an access boundary unavailable to the agent, such as a separately protected signing/approval component. Otherwise narrow the guarantee to accidental automation prevention and explicitly acknowledge that same-user scripts remain able to impersonate the owner. Add authenticated provenance and rollback-resistant state before claiming stronger protection.

15. **Grey-cap verification double-counts the permit being verified, and negative exposure is not explicitly rejected.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:428,444–446,478–479,493–497`.

   Context exposure includes unexpired permits. A KRW 8,400 permit issued against a KRW 8,400 cap passes with initial exposure zero. Once that permit is reserved, verification reruns the calculation as `8,400 + 8,400`, rejecting its own reservation.

   Conversely, finite negative exposure values are not among the explicitly prohibited inputs. Such a value can offset new notional and bypass the numerical cap.

   **Concrete fix:** Require nonnegative, reconciled exposure components. Give reservations stable identities and define verification as replacing or consuming the reservation attributable to the current intent, while retaining all other reservations. Require atomic reservation/update semantics at the execution boundary so concurrent permits cannot each consume the same capacity.

16. **The claimed QUANTGEN isolation does not cover final targets in reused writers.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:151–156,190–191,965`; `config.py:56–62`; `core/isolation.py:13–23`; `data/krx/kis_client.py:52,145–165`; `core/quant/history.py:428–455`.

   The default roots are separated correctly. However, the KIS client validates the state root, then joins `kis_token.json` and later writes that child without checking its final target. A child symlink pointing into `.nextgen` is not caught by validating only the parent root. The inherited history cache has the same final-target gap. New odds-module guards do not protect these reused writers.

   `refuse_quantgen()` itself is a pathname/ancestor check, not an unrestricted filesystem security boundary.

   **Concrete fix:** Audit every reused writer reached by loaders and replay. Check the resolved final target immediately before opening, including sidecars and temporary files, and avoid following prohibited links. For the stronger adversarial guarantee, use filesystem permissions and handle-level protection against path substitution. Keep the current default-root separation, but do not describe it as sufficient by itself.

## Minor

1. **G-15 still routes approved ETFs through an incomplete symbol heuristic.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:166–175`; `core/quant/validate.py:82–107`; `core/quant/instruments.py:140–146,168–182`.

   ETFs outside the small registry/whitelist receive the stock cost class, 35 bp instead of 3 bp. The approved instrument map should determine the cost book and tax treatment. Also, `cost_per_side()` returns `CostQuote`; the numerical equivalent needs its `.bp` field.

   **Concrete fix:** Map approved instrument classes to explicit cost books, define KONEX and unsupported-product behavior, and reserve symbol-shape inference for a labelled fallback or refusal.

2. **D13’s replay artifact contract remains incomplete; the supplied checksum is not proof of reproduction.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:641–650`; `docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json:33–38,140–143`; `docs/asset_expansion_study.py:57–76,107–112,732,764–780`.

   The checksum matches the supplied aggregate `results.csv`, not immutable input prices or per-card OOS returns. The card’s generic Yahoo source description differs from the runner’s Upbit path. The necessary cache is absent from this review copy, and the study runner writes directories/files, including at import.

   **Concrete fix:** Keep `CARD_NOT_REPRODUCED` until a pure replay consumes hashed immutable input and emits canonical OOS returns, turnover, selected parameters, stressed results and a fresh verdict. Define separate input, replay-output and aggregate-report digests. Do not import the original study runner into the odds engine.

3. **Some legal explanations remain broader or more certain than their sources.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:280–281,319,325,757`; `research_notes/QUANTGEN asset coverage expansion/crypto_wallets_connectivity.md:166–178`; `research_notes/Korean resident trading venue legality/crypto_domestic_and_overseas_verification.md:34`; `research_notes/Korean resident trading venue legality/overseas_via_brokers_verification.md:30`.

   The spot-ETF rationale does not establish the same prohibition for futures-backed funds; the FSC’s cited distinction expressly preserved existing overseas bitcoin-futures ETF trading. [FSC statement](https://www.fsc.go.kr/no010101/81466). Gopax’s “indefinitely delayed” renewal was not confirmed by the verification notes. The tax enumeration also does not cover every gate-allowed option/product class.

   **Concrete fix:** Separate stricter owner policy from legal prohibitions, describe unverified status as unverified, and refuse unsupported product/tax combinations instead of inheriting a share-tax template.

4. **Calendar activation and time semantics need a complete procedure.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:158–164,500–502,678–682,997–998`; `core/calendars/store.py:137–164`; `core/calendars/clocks.py:223–229`; `core/calendars/regime.py:62–66`.

   Signing the listed files alone is insufficient: matching manifest hashes, versions, signers, test IDs and row signatures are required. `sessions_between()` includes both endpoints. `regime_tags()` is KR-only and raises `KeyError` for US, not `CalendarUnsigned`.

   **Concrete fix:** Document the complete signed-manifest procedure, exact horizon endpoint convention, timestamp alignment for asset/FX observations, and handling of rule-change dates on non-trading days or during blocked liquidation.

5. **The assumed-edge law is not determined by a win probability.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:636–637,719–720,777–780`.

   Equal bracket win probabilities can accompany different durations, gap payoffs and unresolved mass, producing different monthly target odds. The requested “bets needed to distinguish this from a coin flip” also lacks a specified null, significance level and power; asymmetric brackets need not have a no-edge win probability of 50%.

   **Concrete fix:** Specify the trajectory reweighting/tilting law, treatment of unresolved brackets and refusal for unsupported probabilities. Define any sample-size calculation against the appropriate model null with stated assumptions.

6. **Several reporting and numerical contracts need smaller corrections.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:577,617,623–627,737,764–773,789–791,974`; `core/quant/gate_stats.py:72–77`; `core/quant/garch.py:623–670`.

   `pw_block()` defaults to circular rather than stationary blocks. GARCH correction is numerically approximated, not algebraically exact. GARCH reports should not universally say open-and-close checks. A deterministic no-trade plan’s zero target probability is not a zero-hit Monte Carlo uncertainty. The amber wording “within simulation noise” conflicts with triggering only when a lower confidence bound exceeds the reference.

   **Concrete fix:** Specify the bootstrap kind and numerical tolerances; render checkpoint-specific wording; distinguish structural impossibility from sampling resolution; and describe amber as preliminary statistical evidence, with its per-check error rate. Intraday extrema are not inherently incompatible with martingales—the limitation concerns the proposed reconstruction.

7. **Permit-field verification and approval-version storage need explicit contracts.**

   **Evidence:** `docs/superpowers/specs/2026-10-23-compliance-gate-and-odds-engine-design.md:367–369,438–440,493–503,890–891,958`.

   The verifier explicitly checks intent, session and date, while tests require rejection of a forged permit and the error section says “any mismatch.” It does not explicitly require recomputation/comparison of the permit’s decision, rules and context fields. The promise that the previous approved table stays active also requires retaining its bytes, not merely its hash.

   **Concrete fix:** Define exactly which permit fields must match issuance versus current authorization, and distinguish authorization recomputation from proof of issuance. Persist immutable approved table versions and their active references. Extend the test cases to cover modified unused fields and replacement of a table by an unapproved draft.

**Repository verification record**

These are static verifications, not claims that the proposed packages or tests already pass.

| Requested reference | Verified location and result |
|---|---|
| Configuration and isolation | `config.py:56–62,285–292,388–389`; `core/isolation.py:13–23`. TRADEGEN roots and refusal helper exist; final-target limitations are in Major 16. |
| GARCH | `core/quant/garch.py:446,594–611,654–702`. Fit/simulation APIs exist; simulation returns log returns plus average correction. Normal fallback is unbounded. |
| Statistical helpers | `core/quant/gate_stats.py:72–100,149`. Block helpers exist; `LIVE_SHARPE_MULTIPLIER=0.60`. |
| Validation | `core/quant/validate.py:53–78,87–131,332–381,803–825`. Cost stress is 2.0; `WalkForward` retains P&L/turnover; `ModelCard` has no dedicated mean-LCB field. |
| Instruments | `core/quant/instruments.py:26–28,66–84,155–216`. Four cited books exist; only the ETF tick ladder is shipped; cost and header-check API distinctions are real. |
| Cards and ledger | `core/quant/cards.py:542–561`; `core/quant/gate_ledger.py:122–137,291–316`. Chain reader and packed-ref anchor support exist. Macro verdicts do not supply the proposed OOS return field. |
| History and delisting stress | `core/quant/history.py:55–94,208–224,266–291,439–455`; `core/quant/tf_books.py:36`. History is close-only; stress magnitudes are 0.30 and 1.00. |
| Engine order helpers | `core/engine/orders.py:275,414`. Carry multiplier is 2.0; limit-price helper exists. The multiplier is a modelling assumption. |
| Calendars | `core/calendars/__init__.py:208–229`; `core/calendars/store.py:137–164`; `core/calendars/clocks.py:187–205,223–229`; `core/calendars/regime.py:62–74`. Use signed v2 APIs with the qualifications above. |
| Provenance/context isolation | `core/ficc/macro_artifacts.py:33–34,53–61`; `core/ficc/context_log.py:70–82`. `GIT_HASH` is `UNVERSIONED`; `tree_hash()` is not a whole-repository hash. New acting-module prefixes must be added. |
| Crypto data | `data/crypto/crypto_client.py:66–84,134–164,189–225`. Raw Upbit/Binance candles contain open/close fields; conversion to `History` drops opens. |
| KRX data | `data/krx/kis_client.py:271–304`; `data/krx/gateway.py:88–101`; `data/krx/krx_market_client.py:138–196`; `data/krx/opendart_client.py:155–181`. KIS supplies historical OHLC; the other clients are not interchangeable historical-bar sources. |
| Static read-only guards | `tests/acceptance.py:48–54,169–182`; `tests/macro_m0_harness.py:28–65,76–104,131–159`. New runtime packages are scanned; prohibited text/calls and the orders-import restriction are real. |
| Add-only, hermetic and calendar tests | `tests/macro_m5_integration.py:326–354`; `tests/macro_acceptance.py:52–99,147–154`; `tests/macro_m1_calendars.py:149,245–250,521–540`. `test_s4` is in M5; its diff check depends on the backup. Calendar fixtures write temporary files. |
| D13 candidate | `docs/asset_expansion/cards/S_C3_crypto_trend_krwbtc.json:61–95,140–143`. PASS, Sharpe approximately 1.216, CI approximately `[0.625,1.773]`, stressed Sharpe approximately 1.171 and drawdown approximately −49.34% are present. Reproduction remains unverified. |

## Questions for the owner

1. **D14:** Is console confirmation intended only to prevent accidental automation, or must the system technically prevent an agent running under your account from approving changes? The latter requires an additional protected approval boundary.

2. **D11 recovery:** If the owner log or approved metadata is corrupt, should automation allow only verified position-closing orders using a protected recovery snapshot, with withdrawals handled manually through the broker/exchange?

3. **D13:** Should the tested-edge column be restricted to replaying the exact validated KRW-BTC trend strategy, with changed brackets, symbols or execution rules requiring new validation?

4. **Unsupported eligibility data:** May credit, shorting, leveraged-product purchases and lending remain refused until the gate can obtain the current broker/venue evidence their conditions require?