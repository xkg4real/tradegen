# council_reports — the Quant Council report and the macro overlay research report

Sources, each read in full (2026-10-05; re-read and re-verified 2026-10-06):

| Tag | File | Lines |
|---|---|---|
| BR | `QUANTGEN_Quant_Council_2026-10-03/README.md` | 18 |
| CR | `QUANTGEN_Quant_Council_2026-10-03/reports/QUANTGEN_Quant_Council_Report.md` | 376 (long lines 3, 81 read whole) |
| MR | `QUANTGEN_Quant_Council_2026-10-03/reports/QUANTGEN_macro_overlay_research_report.md` | 384 (long line 13 read whole) |
| SP | `QUANTGEN_Quant_Council_2026-10-03/claude_code/QUANTGEN_MACRO_INTEGRATION.md` | cross-reference only (lines named) |
| RD | `QUANTGEN/README.md` (the app's README) | 398 |

"CR L115" = line 115 of CR. Repo facts were checked on disk on 2026-10-06 (SP line citations, the code lines in C.2/C.5 and the HTML footers in C.1 re-verified the same day).

**Precedence (MR L11).** For findings read CR; for binding rules read SPEC v2.0; "Where either differs from the text below, it governs." So SPEC > CR > MR body. D1–D6 values in force are read from the SPEC Quick start table only (CR L128; SP L69–74), not from CR's option table.

**Evidence status of every number below.** "Verdicts are indicative full-sample computations under the SPEC's thresholds, never runs of QUANTGEN's own gate" (CR L5). "None is a run of QUANTGEN's own gate" (MR L284). "The gate-acceptance test is specified but has not run, and no v2 module has been built" (CR L279). No number in this note may be shown in the app as a formal verdict.

**Tooling note.** `scratchpad/prep/readlines.py` has a syntax error (unterminated string, line 4); the long lines were verified by character count with an inline python read instead.

---

## A. The council

### A.1 Model: who, what, how

Three simulated groups, 20 fictional personas (CR L273): 7 QF archetypes, 6 professors, 7 executives. Owner = GEON (CR L9). Artifacts audited: SPEC v1.2 (2,032 lines), backlog (1,407 lines), the research report, the visual page (CR L9).

| Code | Codename | Fictional archetype | Lane | Audit items | Proposals |
|---|---|---|---|---|---|
| QF1 | Kestrel | ETF and options market maker | Execution, cost realism, KRX microstructure | 25 | 6 |
| QF2 | Ostrava | Low-latency data and infrastructure, crypto market structure | Point-in-time data, timestamps, calendars, vintages | 28 | 9 |
| QF3 | Halcyon | Stat-arb and ML researcher | Gate statistics, multiple testing, ML | 24 | 8 |
| QF4 | Meridian | Multi-strategy pod risk | Vol targeting, drawdown control, concentration, allocation | 23 | 9 |
| QF5 | Larkspur | Multi-asset and factor asset manager | Factor timing, trend, regimes, priors | 27 | 10 |
| QF6 | Vireo | Volatility and derivatives quant | Volatility forecasting, Quant Lab tails, leveraged ETFs | 25 | 11 |
| QF7 | Corvid | Academic quant methods | Forecast evaluation, regime detection, curricula | 28 | 7 |
| Total | | | | 180 | 60 |

(CR L11–20.) Firm-style labels in CR "describe career archetypes only" (CR L5); do not surface firm names in the app.

Other bodies: professors P1–P6 (macro theory, time-series econometrics, asset pricing and factors, game theory and policy, curricula, quant ML methods) and executives E1–E7 (cross-asset strategist, NYSE trader, FX/rates trader, Asia/EM PM focused on Korea, CRO and systematic PM, IB vice-chair, global head of research) (MR L137). Cross-examination delegations PX1 (methods), PX2 (pricing), EX1 (risk and strategy), EX2 (trading and Korea); data labs DL-A (rebuilt the protective-card harness from the SPEC's text) and DL-B (estimator, trend, regime, power tests), "without personas"; chairs QC-P, QC-E, QC-Q; one secretary (CR L36, L99–103).

| Round | Who | Output | Count |
|---|---|---|---|
| QF audit | QF1–QF7 | Audit items · proposals · claims-register rows | 180 · 60 · 96 |
| QX cross-examination | PX1 (114), PX2 (100), EX1 (137), EX2 (121) | UPHELD · UPHELD-QUALIFIED · OVERTURNED · UNRESOLVED | 332 · 127 · 3 · 10 (of 472) |
| | | Reviewers' new points | 24 |
| QX data labs | DL-A | R4b quantities reproduced exactly; master-table rows | 385 of 385; 62 |
| | DL-B | Tests replicated · partially · not replicated · corrected | 19 · 6 · 0 · 3 |
| QC chairs | Professors, executives, QF | Rulings | 145 · 147 · 145 |
| QC secretary | — | Ledger items · SPEC v2.0 modules · errata rows | 361 · 34 · 348 |

(CR L38–46.) Only 3 of 472 verdicts overturned a QF finding, all in one statistics paper (CR L3). "Nothing failed to replicate."

**QF verdict vocabulary (CR L24–32):** FALSE-TRUE 26 · FALSE-ERROR 20 · DESIGN-DEFECT 33 · MISSING 16 · QUALIFIED 47 · CONFIRMED 36 · UNVERIFIABLE 2 (= 180). Severity: Critical (a wrong risk decision, an invalid gate verdict or look-ahead) / Major / Minor (CR L34).
**QX verdict vocabulary (CR L36):** UPHELD, UPHELD-QUALIFIED, OVERTURNED, UNRESOLVED (with a named settling test); proposals scored −2..+2.
**Ledger classes (CR L111):** 140 VALID-BUILD, 67 VALID-ERRATA, 7 VALID-SHADOW, 9 CONTEXT-ONLY, 3 CONTESTED, 3 INVALID, 3 OWNER-DECISION, 34 CONFIRMED, 95 claims-register rows (= 361). 213 accepted for action: 59 P0, 81 P1, 73 P2. 67 corrections → 348 machine-applicable errata rows across SPEC, backlog, report and page.

**Secretary's fixed rules (CR L36):** unanimous → adopted; two-of-three → adopted with the minority's compatible conditions; a red line binds the wording even against a majority; anything else → CONTESTED with a settling test, or to the owner. Chairs set at most five red lines each. Settled facts were frozen so chairs "could not relitigate them without new evidence" (CR L105).

**Protocol constraints that bind the app (CR L9, L22):** nothing proposed may place an order or give investment advice; anything altering a non-negotiable principle carries the label `PRINCIPLE CHANGE`. Conventions: decide at the close of day t, earn from t+1; pre-registered per-side costs KRX ETF 3 bp, KRX stock 35 bp, US shares via KIS 50 bp, futures 5 bp, FX and crypto 10 bp, each also tested at 2×. (Matches RD L210–212; no change.)

**CARD-P as audited (v1.x form; CR L34, MR L284).** A CARD-P rule claims drawdown protection, not outperformance; judged against **S = a static book holding the rule's average exposure**, on seven checks fixed before any run:

| Check | v1.x text | v2 fate (Resolution) |
|---|---|---|
| PC-1 | ΔMDD ≥ 3 pp (MR: at 1× and 2× costs) | replaced by PC-1′ (Res. 4) |
| PC-2 | tail-exposure ratio ≤ 0.90 on the worst 5% of days | kept (SPEC adds CI) |
| PC-3 | Sharpe non-inferiority within 0.10, p_ni ≤ 0.10 | binds; with selection factor: p_ni × f ≤ 0.10 (CR L269) |
| PC-4 | benefit in ≥ 3 drawdown episodes, none supplying more than half | episodes become objective (Res. 11) |
| PC-5 | 60% of years positive | kept |
| PC-6 | a parameter plateau | kept |
| PC-7 | sufficient history (MR: enough onsets, episodes and history) | kept |

### A.2 The twelve resolutions (CR L113–126)

Text and evidence columns are CR's wording; "App change" is this note's mapping onto SPEC modules (ids and milestones from CR L227–239 and SP L197–230).

| # | Resolution (CR text) | Key evidence | Vote | App change |
|---|---|---|---|---|
| 1 | **Korea vol target** becomes BUILD-AS-INSURANCE on a formal v2 PASS on long KRX history, cap 1.0 permanent. A PASS needs: the full span; the ETF-era line (first full month after KODEX 200's October-2002 listing to December 2025); no REJECT and at least two-thirds PASS across monthly starts from May 1997 to December 1999; and no REJECT in either calendar-midpoint half | ΔMDD +12.7 pp; tail 0.68; p_ni 0.052; 14 of 18 objective bear markets positive, maximum share 0.174; 2016–25 REJECT | QF4-M1 unanimous; sub-points 2–1; the professors' red line binds | R-06 (CARD-P, P0, M7). Card carries the insurance label (C.3). Outcomes: PASS → BUILD-AS-INSURANCE in the recommended book; INSUFFICIENT → labelled control in the specification book, re-gated only when new history adds an objective episode; REJECT → archive. No forward-record route. Any vt > 1.0 fails validation (SP L5646). **Expected outcome: INSUFFICIENT DATA, reason `underpowered` (A.8).** |
| 2 | **US vol target**: the 50 bp card stays REJECT, relabelled "instrument: US shares via KIS, 50 bp, daily"; a new index-futures card, MACRO-R06-US-FUT, runs FORWARD-SIM | 50 bp: +0.2 pp; futures: +3.6 pp, but 11 of 44 starts; ES99 z 2.37 | Unanimous | R-06 US label string `"REJECT (instrument: US shares via KIS, 50 bp, daily)"`, `rerun: false` (SP L4291, L5646). R-29 (NEW, M8) forward-sim book, never in the recommended book (D5). R-26 instrument book on every header. |
| 3 | **Estimator**: SMA20 stays the acting default and displayed baseline; COMB = ½(GJR-t + log-HAR-range) is the registered challenger for ETF and futures books, behind a three-stage, counted, fail-closed gate | SMA20 outside the 90% QLIKE confidence set at 1, 5 and 21 days (p ≤ 0.0005) but inside the MSE set; COMB cuts vol-of-vol 22.2% and drawdown 2.8 pp at ΔSR −0.000 | Default 2–1 (professors dissent); staged rule unanimous | R-30 (NEW, M3): estimator-selection gate + forecast-evaluation harness. SMA20 must not be called "validated default" anywhere. |
| 4 | **PC-1 → PC-1′**: expected shortfall (ES95) of 21- and 126-session returns gates; drawdown, CDaR and daily ES99 are printed only; PC-3 binds; a do-no-harm cap applies | ΔMDD's SD flat at 7.4–7.8 pp; a 5-day vol target passes daily ES with ΔMDD −12.46 pp | Legs unanimous; cap 2–1 | R-21 (NEW, M7, frozen before the first card run). Card prints MDD/CDaR/ES99 as non-gating lines. D6 covers the CDaR guard. |
| 5 | **Step 3**: a hashed family ledger; N_eff = max(N_clusters, N_equiv); Kish never used; R-03 PASS (borderline), R-04 FAIL | N_equiv 6.3; R-03 0.98 (0.947 at linear N̂ 12.6); R-04 0.77 | Core unanimous; z-rule printed, 2–1 | R-23 (NEW, M7). R-03 relabelled "indicative PASS", "step 3 borderline" (M4). R-04 DEMOTED to the specification book, "step 3 FAIL" (M4). Both N numbers printed on the card. |
| 6 | **Ladder**: one rule on whole-book NAV composed by `min()`; explicit re-arm; steps time-boxed at 21 sessions; the −15% hard stop is a governance event | The literal rule halts forever; time-boxed steps bind on 19% (KOSPI) and 10% (US) of days at about ±0.01 Sharpe | Structure unanimous; levels 2–1; hard-stop level → D2 | R-02 (`min()` composition, M2), R-07 (hard stop with explicit re-arm, M5), R-31 (NEW step-down card: −8% and −12% steps, 21 sessions, specification book until PASS, M7). A product-composed path raises an error (CR L231). |
| 7 | **Staleness** judged by publication schedule and input role; risk-model inputs never HALT | Stale share falls from 100% to 0.33–0.89% | Unanimous | R-19 (NEW, M1), R-09 (M2), R-20 calendars (M1). Acceptance: H.10 inputs stale on ≤ 1% of decisions (CR L230). |
| 8 | **R-08** (VIX ≥ VIX3M) becomes an execution annotation; **R-11 and R-12** retire as labelled REJECTs | R-08: 132 spells, 50.8% one day long; R-11: 54 onsets, −1.3 pp; R-12: 71 onsets, −3.5 pp | Unanimous; refusal books 2–1 | R-08 DEMOTED (M5): annotation, not an entry block. R-11/R-12 RETIRED (M8): at most labelled, display-only refusal books that no other book reads. |
| 9 | **Trend**: a protective-only monthly SMA10m card (0.5× below trend) for US and other non-Korean sleeves, FORWARD-SIM; Korea context only | US 1927–2026: +15.9 pp, 45 onsets; 94 of 94 variants ≥ 3 pp; the Sharpe gain fails deflation | Unanimous; scope 2–1 | R-28 (NEW, M8) forward-sim book; R-14 trend sleeve (M7). No Korean trend multiplier. |
| 10 | **Regime engine**: no regime state acting or displayed in v2; BOCPD written to a research log; a 2027–28 head-to-head | Band +16.5 vs jump model +13.9 pp; holdout −0.070 vs −0.128 | Outcome unanimous; jump model CONTESTED | R-33 DO-NOT-BUILD v2 (M0); R-18 BOCPD logged only (M6). Not even a logged change-point flag on any screen (CR L107). Affects the existing Macro page regime chips and the Crypto regime score (C.5). |
| 11 | **Episodes**: objective market-own bear and bull phases (≥ 20%; ≥ 15% for the S&P); §8.6 windows printed; Sep-2026 is not an episode | KOSPI 18 episodes (12 before 2008); PC-4 maximum share 0.493 → 0.174 | Unanimous | R-22 (NEW, M7, frozen): objective episodes, excess returns, declared start band. Card prints the §8.6-window number beside the objective one. |
| 12 | **Korea caps and priors**: caps on look-through with an active single-name cap; priors become admissibility filters, with equal risk budgets and inverse-vol weights across markets | The chip pair is ≈ 51% of KOSPI and ≈ 75% of its 63-day variance; equal budgets 1.337 vs rolling-Sharpe tilts 1.068 | Unanimous; template → D1 | R-07 look-through caps (M5), R-15 priors as admissibility filters (M4). Template value from D1. |

**Korea card consequence text (CR L128).** If the formal run returns INSUFFICIENT, "the card becomes a labelled control, re-gated only when new history adds an objective episode; there is no forward-record route, and the forward record is a falsification alarm only".

**Owner decisions.** CR L130–137 lists options and council defaults; values in force are the SPEC Quick start registry (SP L69–74):

| D | Subject | Value in force (SP) | Config key (SP) | CR evidence note |
|---|---|---|---|---|
| D1 | Korea concentration template | **MSCI 25/50**: single name ≤ 22.5% after the buffer; names above 4.5% ≤ 45% in aggregate; checked quarterly and on breach. Options: (a) domestic max(10%, market weight); (c) 35% pair cap | `risk_layer.korea_caps.template` | n = 1. July 2026: −36.3% (25/50), −33.9% (35% pair), −38.6% (KOSPI) |
| D2 | Hard-stop level | **−15% of book NAV** from the high-water mark since the last re-arm. Option (b): −1.5 σ_book | `risk_layer.drawdown.hard_stop.level` | KOSPI VT20: (a) fires 24 times and deepens MDD to −56.4% from −45.3%; at −30%, 6 HALTs and MDD −44.8% |
| D3 | Calm-state reversal down-weight (QF5-M10, PRINCIPLE CHANGE) | **Not adopted: P3 stands** | `families.reversal.calm_state_downweight` | Evidence is US, gross, one regime; no Korean net test |
| D4 | Book-level false-demotion budget | **≤ 10% a year** across all statistical demotion triggers, split equally across active cards | `monitoring.false_demotion_budget_per_year` | Twelve forward months detect only catastrophic decay (−0.20 / −0.39 / −0.73 Sharpe) |
| D5 | US sleeve | **No US sleeve until decided**: R-28 and R-29 stay FORWARD-SIM and never enter the recommended book | `sleeves.US.line` | Micro ES ≈ ₩52m; tracking error 7.5% a year at ₩0.1bn vs 0.7% at ₩1bn |
| D6 | CDaR-guard calibration | **Frozen with the package: the lowest-placebo-false-pass rule** (placebo results only, never a card's numbers) | (see SP L74) | Needed only if a negative control passes the acceptance test |

**Settling tests (CR L139).** 17 named. Three gate builds: (1) the formal Korea run on KRX official closes; (2) a one-time gate-acceptance test — at most 10% of 300 circular-shift placebos per family may pass, and named negative controls must fail; (3) a 1926–2026 daily run for the US futures card (DL-A could not run it: the French daily file returned HTTP 403). Research tests: size/power comparison of trial-count rules; reading equation 9 on the printed page; a pre-registered 2027–28 forward head-to-head (jump model vs 200-day band vs US vol target; US, STOXX 50, TAIEX); a KRX net-of-tax test before calm-state reversal could be reopened.

### A.3 False errors and false trues (CR L52–67, detail L69–93)

FALSE-ERROR = presented as false/refuted/INSUFFICIENT but right, usable or testable. FALSE-TRUE = presented as true/validated but wrong, unsupported or overstated.

| Claim in the old artifacts | QF verdict | Evidence | Final class | What the app must do |
|---|---|---|---|---|
| Korea vol target: "INSUFFICIENT DATA; wait 12 forward months" | FALSE-ERROR | 1997–2026: ΔMDD +12.7 pp, tail 0.68, p_ni 0.051 | VALID-BUILD | Decide on long KRX history, not on forward months (Res. 1) |
| US vol target "REJECT at 50 bp" read as a refusal of the rule | FALSE-ERROR | Futures at 5 bp: +3.6 pp, p_ni 0.002; ES99 z 2.37 | VALID-SHADOW | Relabel as instrument fact; new futures card forward-sim (Res. 2) |
| USD/KRW leg "INSUFFICIENT until a timestamped history exists" | FALSE-ERROR | ECOS 15:30 close from 1990; 53–55 strict onsets; REJECT | VALID-ERRATA; R-11 retired | Refusal book only |
| Rates leg at +1 business day "non-compliant by 15 minutes" | FALSE-ERROR | Treasury par yields posted by about 18:00 ET | VALID-ERRATA; R-12 retired | Refusal book only; log posting times |
| "No HAR until intraday RV"; GARCH barred until B5 | FALSE-ERROR | log-HAR on daily ranges in the KOSPI MCS at 5 and 21 days; long-window GARCH passes B5 | VALID-BUILD | Range-HAR admitted (R-30, R-16) |
| Trend axis "data-mined"; "KOSPI trend does not beat holding" | FALSE-ERROR | US 1927–2026: ΔMDD +15.9 pp, 45 onsets | VALID-SHADOW; VALID-ERRATA | R-28 forward-sim; protection is through volatility; Sharpe gain fails deflation |
| "2 Oct close 6,943.66" | FALSE-TRUE | File written 10:56:46 KST; official close 7,003.74 | VALID-ERRATA | `value_status` + provisional-row guard (R-01); fixture test below |
| SE(ΔSR) 0.034/0.052; "+0.05 needs 33–44 years" | FALSE-TRUE | HAC SE 0.061 / 0.130; 146–330 years | VALID-ERRATA; VALID-BUILD | Power/MDE line on every card (R-24) |
| SMA20 a "validated default" | FALSE-TRUE | Outside the 90% QLIKE set; B5 passes 9 of 12 models | VALID-ERRATA | Wording change + R-30 |
| R-03 "passes easily"; "86% of years" | FALSE-TRUE | Step 3 depends on N; 86% is a cap-2 figure; QF5's 40.5% also wrong (17 tied years counted as losses; 15 of 20 differing years) | VALID-ERRATA | R-03 label "step 3 borderline" |
| Drawdown ladder "not a card"; −15% HALT | FALSE-TRUE; DESIGN-DEFECT Critical | The literal rule halts forever | VALID-BUILD | Explicit re-arm reference (R-07, R-31) |
| Staleness defaults | DESIGN-DEFECT Critical; FALSE-TRUE | H.10 inputs stale at 100% of decisions | VALID-BUILD | Schedule/role staleness (R-19) |
| Markov switching "30.8 switches a year" (KOSPI) | FALSE-TRUE | Artefact of 2-year initial training; 9.95 a year with long training (DL-B: 9.75) | VALID-ERRATA | Text only |
| D&M gate "exactly the published rule" | FALSE-TRUE | The published rule is continuous; half its gain is variance scaling | VALID-ERRATA | Label R-04 "a floored heuristic, not the published rule" (MR L289) |

**Mechanical defects with testable numbers (CR L81).**
- Intraday print: file written 10:56:46 KST; official 2 Oct 2026 KOSPI close **7,003.74** (was 6,943.66). Drawdown from the 9,114.55 peak −23.2% (not −23.8%); next vol-target weight 0.694 (not 0.691). The old lag audit `available_at_utc ≤ decision_utc` would have accepted the print because nothing separated a provisional value from an official close. M1 acceptance: "The 2-Oct fixture returns MissingInput at 10:31 KST and 7,003.74 at 16:00 KST" (CR L230).
- Data patch: 8 closes replaced; 10 provisional, 39 partial-month and 3 duplicate-date rows dropped; 60 logged actions (`QF0_data_patch_20261002.csv`; CR L81, L371). DL-A recomputed 24 dependent values.
- Staleness: under old §4.1 defaults every H.10 input (posted Mondays 4:15 pm) is stale at 100% of decisions and strict-H.15 yields at 99.5%; an input stale for more than one decision moved the engine to HALTED, so "a literal build halts every day". Schedule-aware rule flags 0.3–0.9% of decisions, all on dates the source legitimately skipped.
- Ladder: the −15% hard stop defined no reference after re-arm; NAV is flat while halted so it re-halts at every re-arm: HALTED from 1997 at 1.3% average exposure through 714 cycles on KOSPI. Read literally the −8% and −12% steps were also cumulative (0.25×). M5 acceptance: "The KOSPI 1997–2026 book re-enters after every HALT" (CR L234).

**Power arithmetic (CR L85).** Old SE 0.034/0.052 assume overlay ≈ 0.98 correlated with its base (true for add-on legs). A market vol target correlates 0.89–0.92 with S → HAC SE **0.061 (US), 0.130 (KOSPI)**; +0.05 takes roughly 146–330 years. Single-path MDD has bootstrap SD 7.4–7.8 pp that does not shrink from 10 to 100 years; PC-1 rejects a zero-cost vol target about 55–70% of the time in 11–36-year resampled histories. Hence Res. 4.

**Korea fragility facts the card must be able to print (CR L71–73, L277).** DL-A definitive cell: p_ni 0.052, ΔSR +0.026. Under the SPEC's §8.6 episode table July 2026 carries 0.493 of the benefit against a 0.50 limit (objective episodes: 0.174). 1997–2015 and 2016–26 do not confirm alone; 2016–25 is a REJECT (tail 0.95); 1997–2002 a REJECT (ΔSR −0.20); ETF era Oct 2002–Dec 2025 passes (p_ni 0.040, ΔMDD +11.9 pp). Raw→excess returns (cash at the Korean call rate): ΔSR +0.025 → +0.006, p_ni 0.051 → 0.078, passing share of 33 start dates 97% → 70%. Mean-timing return −1.84% a year, variance ratio 0.59. 71 of 72 monthly starts 1997–2003 pass; ΔMDD ranges +3.7 to +12.7 pp by whether the sample holds the June-1997 peak. Only 2 of 20 rolling decades pass. Twelve more months add 3–10% of the information; PC-3 power at true ΔSR 0 rises only 0.305 → 0.317. EWMA(0.94) line returns INSUFFICIENT on PC-4 (0.51 episode share) (CR L217).

**US futures facts (CR L77).** PASS clears PC-1 by 0.6 pp; passes at 11 of 44 quarterly starts (every start late 1994 to mid-2000 is a REJECT); +0.3 pp on 1990–2007; on 1995–2026 SMA20 gives +2.5 pp (REJECT) while GARCH, log-HAR and a combined forecast pass. One Micro E-mini ≈ ₩52m: a ₩0.1bn sleeve has 7.5% a year tracking error vs 0.7% at ₩1bn.

### A.4 Where QF itself was wrong (CR L87–93) — rules the code must not copy

1. **Trial count.** QF3 used the Kish form N̂ = M/(1 + (M − 1)ρ̄) (gave 1.1–1.8 trials). The paper's equation 9 is linear: **N̂ = ρ̂ + (1 − ρ̂)M**. On QF3's 26-trial family: linear N̂ 12.6 → R-03 at 0.946–0.947, just below the 0.95 bar. Kish yields a negative expected maximum (−0.22) at N̂ 1.14 and is gameable by padding (80 near-duplicates of R-03: 1.81 → 1.20; R-04's deflated add-on 0.951 → 0.986). Council rule: **gate on N_equiv** = the iid trial count with the same simulated expected maximum (6.3 on QF3's family, 6.59 after padding); **print the linear N̂ as a conservative bound**; Kish never used.
2. **Jump model.** λ = 50 was set by Shu, Yu & Mulvey on the S&P 500, DAX and Nikkei 1990–2023, so two of four "held-out" markets were in-sample. Clean US holdout Jan 2024–Sep 2026 at 50 bp: jump model ΔMDD +3.7 pp at Sharpe cost −0.128 vs the 200-day band −0.070; full sample band +16.5 vs +13.9 pp. Korea excluded for: no plateau in λ, flags arriving at the trough, PC-3 failure. FTSE and Hang Seng: jump model beat the band (+11.6, +7.5 vs +6.8, +5.1 pp) → forward head-to-head in the backlog, not the archive.
3. QF chair listed 21 concessions; those that changed a rule (CR L93): R-04's pooled "route to PASS" closed (deflated add-on 0.77 at the honest N; holdout passed 1 of 3 regions); daily ES is not a gate (a 5-day vol target at 50 bp passes it while deepening drawdown 12.5 pp); QF5's "40.5% of years"; **KRX close bound 06:30:30Z, not 06:35Z** (random end unconditional since 2015); "robust" withdrawn as a description of the Korea pass.

### A.5 The three-way debate and its red lines (CR L97–107)

| Group | Red lines (binding wording) |
|---|---|
| Professors (QC-P) | No promotion on a single path or crisis; no rule chosen after seeing its card; no forward record as validation; no selection without counted multiplicity; macro sizes risk, nothing above 1.0 |
| Executives (QC-E) | No regime state acting or displayed; no piecemeal or post-hoc gate change; no exposure path the gate never sees; no acting decision on provisional or stale data, and no risk-model input that can halt the book; no instrument the desk cannot execute |
| QF (QC-Q) | No rule adopted after seeing the card it rescues; no REJECT on single-path drawdown; forward months never validate; verdicts are book-specific; nothing may freeze or quietly shrink the book |

Judgement splits (CR L107): SMA20 kept acting 2–1 (professors wanted it retired for new cards); hard stop −15% kept 2–1 (executives wanted −1.5× target vol) → level to owner (D2); jump model CONTESTED. Two red lines decided sub-points against a majority: professors' "no promotion on a single crisis" added the midpoint-half check and ended the Korea gating line in December 2025; executives' "no regime state" keeps even a logged change-point flag off every screen.

**Disclosed tensions (CR L107) — both alternative numbers are printed on the cards:** (a) the objective episode rule rescues Korea's PC-4 (0.493 → 0.174); (b) N_equiv was chosen after seeing that R-03 passes under it.

Definition traps DL-A resolved (CR L105): start date decides +12.7 vs +3.8 pp; PC-4 counts (14/18, 9/16, 8/16, 8/14) came from each member's own pre-2008 episode list because the SPEC's table had no window before 2008; QF7's p 0.056 becomes 0.082 under the SPEC's block convention; "log-HAR fails at one day" came from regressing the log of a squared return rather than the log range.

### A.6 Practice-gap brief (CR L141–221)

Competitor = public institutional practice (regulators, index/risk-model methodologies, published practitioner research, academic literature), not any firm. 52 gap notes → 33 capabilities in six areas. Scale: 0 absent; 1 specified but defective/partial; 2 specified in v2 with a falsifiable acceptance test, not yet built; 3 parity in operation. "No QUANTGEN capability can score 3 until its module is built and its acceptance test has passed." Scores are "this report's reading", "not a council vote" (CR L147).

| Area | n | v1.2 mean | v2.0 mean | Still 0–1 after v2.0 |
|---|---|---|---|---|
| Data layer | 4 | 1.00 | 2.00 | none |
| Validation statistics | 6 | 0.83 | 2.00 | none |
| Risk and sizing | 6 | 0.67 | 1.67 | Covariance aggregation; funding and crowding data |
| Execution and cost realism | 6 | 0.67 | 1.67 | Own-fill costs; liquidity state |
| Volatility and risk models | 6 | 0.83 | 1.83 | Default estimator |
| Research methods | 5 | 0.60 | 1.20 | Breakdown monitoring; regime models (by choice); cross-asset trend |
| All | 33 | 0.76 | 1.73 | 8 capabilities |

v1.2: 9 absent, 23 weak, 1 adequate. v2.0: 1 absent by choice, 7 weak, 25 specified with acceptance tests (CR L203).

Capability → module map (CR L153–191), for traceability:

| Capability | v1.2 defect | v2 module |
|---|---|---|
| As-of reads, frozen-fixture vintages | lag audit accepted a mid-session print | R-01, R-32 |
| Macro vintages and first prints | latest vintage only | R-13 |
| Calendars, publication schedules, clocks | fixed 06:30Z close; age-based staleness | R-19, R-20 |
| Look-ahead control | lag tests cannot fail on registry errors | R-34 |
| Trial registry feeding N | N undefined; no DSR computed | R-23 |
| Power and robust inference | no power line | R-24 |
| Tail-loss protective metric | single-path drawdown | R-21 |
| Monitoring of forward books | triggers fire in 30–69% of years | R-25 |
| Cross-market replication | per-market counts only | §8.3 pooling rule declared before any run |
| Evidence-based haircut | flat 40% with contradictory wording | multiplier 0.60 plus a per-card Harvey–Liu haircut |
| Loss limits with reference and re-entry | never re-arms | R-07, R-31 |
| Concentration on look-through | vacuous on the ETF book | R-07, D1 |
| Risk budgets before tilts | 0–3 priors, no normalisation | R-15 |
| Covariance / book aggregation | absent | R-15, R-02 (inverse-vol weights only; score 1) |
| Replay and stress scenarios | hand-picked scenarios | R-16 |
| Funding, crowding, mechanical flows | absent | R-13 (context fields; no data source yet; score 1) |
| Cost assumptions | already at or above realistic (score 2) | P10; costs never lowered |
| Costs calibrated on own fills | no fills | KIS quote task; stress line reported (score 1) |
| Market-gross overlays on cheapest delta-one line | 50 bp single shares | R-26, R-29, D5 |
| Turnover control | full daily rebalance | R-26 header fields |
| Liquidity as a state | absent | R-26; R-08 annotation (reported, not gated) |
| Auction, tick, product awareness | close convention only | R-26, R-27, R-20 |
| Estimator chosen against alternatives | calibration test only | R-30 |
| Default sizing estimator | SMA20 | R-30 challenger route (SMA20 still acting; score 1) |
| ES and conditional coverage | 95% VaR and PIT only | R-16, R-30 |
| FHS and long-window calibration | 504-close fits | R-16 |
| Range/RV models with trading speed | HAR banned | R-30 |
| Implied volatility | max(SMA20, implied) | R-13 (live snapshots logged) |
| Outcomes analysis and effective challenge | — | R-21, R-30 |
| Nested-model OOS tests | OOS R² only | R-30 |
| Forecast-breakdown monitoring | absent | R-18 (log-only flags; score 1) |
| Regime models as filtered context | absent | R-33 (0, by choice) |
| Cross-asset trend | equity only | R-14, R-28 (score 1) |

**Positioning (CR L207).** "for an owner who runs it alone, QUANTGEN is a read-only research desk whose pre-registered gate decides and whose refusals stay on the record." It cannot calibrate costs on own fills, see funding/crowding data, or hold index futures cleanly below about ₩1bn notional, "so it must assume conservatively where they measure". "Its distinct position is governance, not scale."

**Strengths (CR L211).** Time handled correctly (weights from data through t−1); the Korea SOX×KRW gate's look-ahead premium of 0.28 Sharpe is now the positive control in every card's timing test (R-34). Cost table conservative: KODEX 200 ≈ 1.6 bp a side vs table 3 bp; Samsung-class stock ≈ 20 bp vs 35 bp, including the 0.20% sell tax in force from January 2026. 40% live haircut is calibrated (McLean–Pontiff: 26% lower OOS, 58% lower post-publication ≈ 43% further decay). **Weaknesses:** no fills, one price vendor, notional too small for index futures, a single maintainer (argues for simplicity).

**Opportunities = logging (CR L215).** KIS bid/ask snapshot at 15:19:59 KST beside the decision price, the closing-auction print and the simulated fill (quote-snapshot TCA); first prints and vintages for revised FRED series (R-13); publish the script and seed of the app's GJR study (`docs/vol_backtest.py`, SP L6458 — UNVERIFIED until then); log KOFIA margin debt and leveraged-product AUM.

**Threats (CR L217).** Korea PASS not expected to survive its formal run; no vol target helps against gap shocks from calm states (2018-10, 2020-02, 2024-08); every trend rule tested was fully long on 23 June 2026 and through July's −38.6%; procedural threat: statistics chosen after results.

**Refuse list (CR L221, L243).** A regime engine; a maintained ML classifier; a conformal label layer (a constant vol forecast passes the per-label coverage test); futures below the granularity floor. R-33 adds/sharpens seven DO-NOT-BUILD entries that rules-store validation now refuses: (1) a regime state, acting or displayed; (2) a Mondrian conformal label layer; (3) a maintained ML challenger pipeline; (4) max(SMA20, implied) sizing; (5) product-composed de-risk stacks; (6) a venue switch after results; (7) a stock book used as a market-gross scalar. §10 item 11 is split: ML volatility-state classifiers stay prohibited, range-based HAR is admitted. Every entry is labelled **harm, null or inconclusive** ("refuted" overstated the archive: of 53 bootstrapped variants 7 harm, 12 no material effect, 28 inconclusive, 6 benefit). The SPEC's 26 DO-NOT-BUILD items also stay.

### A.7 Modules, milestones, principles (CR L223–243)

34 modules = 16 CHANGED + 14 NEW + 2 DEMOTED + 2 RETIRED; 16 at P0 (CR L225). Change types per SP L197–230: NEW = R-19…R-31 and R-34; DEMOTED = R-04, R-08; RETIRED = R-11, R-12; R-05 unchanged; the rest CHANGED.

| Milestone | Modules | Delivers | Acceptance (abridged, CR wording) |
|---|---|---|---|
| M0 scaffolding | R-26 (new), R-32, R-33 | Instrument book, notional, tick floor, execution variants on every card header; v2 schemas; DO-NOT-BUILD v2 | A ₩69 ETF is charged ≥ 72 bp per side; a card without book, rebalance rule, band and notional is refused |
| M1 data layer | R-01, R-19 (new), R-20 (new) | `value_status`, `session_date`, `retrieved_at_utc`; provisional-row guard; staleness by schedule and role; effective-dated KRX, NYSE and Fed calendars with regime tags | 2-Oct fixture returns MissingInput at 10:31 KST and 7,003.74 at 16:00 KST; H.10 inputs stale on ≤ 1% of decisions |
| M2 risk layer | R-02, R-09 | `min()` composition with a floor of 0.5 × vt outside HALTED; date-aligned stock–bond correlation; risk-model inputs never HALT | corr63 reproduces +0.53 on 30 Sep 2026; a product-composed path raises an error |
| M3 estimator harness | R-30 (new) | Staged estimator gate; forecast-evaluation harness; COMB challenger | Reproduces SMA20's MCS exclusion (p ≤ 0.0005) and COMB's −22% vol-of-vol |
| M4 factor sleeves | R-03, R-04 (demoted), R-15 | R-03 relabelled indicative PASS with scale-free and variance-scaled revisions; R-04 confined to the specification book; priors → admissibility filters | R-03's sleeve scale and momentum goldens reproduce; step-3 values (0.98 at N_equiv 6.3; 0.947 "step 3 borderline" at linear N̂; R-04 0.77 "step 3 FAIL") are checked in M7, after the freeze |
| M5 engine and events | R-07, R-08 (demoted), R-10, R-27 (new) | Look-through caps; hard stop with explicit re-arm; R-08 annotation; holiday-gap VaR scaling; simulated KRX/NYSE fill model | KOSPI 1997–2026 book re-enters after every HALT; SK hynix on 31 Jul 2026 (limit-up) cannot fill at the close |
| M6 context and breaks | R-13, R-18 | Vintages, leverage/flow context, live implied vol; official-framework break trigger; BOCPD logged only | No acting module reads any context item |
| M7 cards, gate frozen first | R-21, R-22, R-23, R-24, R-34 (all new); then R-06, R-14, R-31 (new) | PC-1′, objective episodes, excess returns and start bands, trial ledger, power harness, timing-fragility gate; then formal runs (Korea card expected INSUFFICIENT DATA; R-03 card; trend sleeve; step-down card) | ≤ 10% of 300 placebos pass; negative controls fail, with at most one bounded redesign; the look-ahead positive control is flagged |
| M8 forward records | R-25, R-28, R-29 (new); R-11, R-12 (retired); R-35 | Calibrated whole-book demotion; US trend and US futures cards in FORWARD-SIM; refusal books; workflow gates | No forward record can raise a verdict; only PASS and BUILD-AS-INSURANCE cards reach the recommended book |
| M9 Quant Lab | R-16 | Expanding-window fits, FHS/EVT envelope, replay library | The replay reproduces July 2026's −38.6% in 27 sessions on the current book |
| M10 deferred sleeves | R-17 | 24/7 crypto clock; declared FX instrument | A card without a declared FX instrument is refused |

Sequence rationale (CR L225): data and liveness first, then risk-layer composition, estimator harness, factor sleeves, and the cards last, after the gate package is frozen.

**Principles, unchanged (CR L241):** read-only by construction (P0); macro scales risk and never generates direction (P1); overlay multipliers in [0.5, 1.0] and nothing above 1.0 (P2); stress variables never gate means (P3); Korea's risk inputs local (P4); decide at the close of day t, earn from t+1 (P5); thresholds on changes or percentiles (P6); the gate decides (P7); declared exposure bases (P8); slow macro as context (P9); pre-registered costs (P10). Cap 1.0 on every vol target is permanent (R-06). The live haircut is renamed **`live_sharpe_multiplier: 0.60`** to end the "60% haircut" ambiguity. Of 199 bootstrap-tested variants only momentum's own-volatility scaling survived multiple-testing control.

### A.8 Adversarial review of SPEC v2.0 (CR L245–269)

Four opponents (QA engineer, data engineer, junior developer, "fintech CRO + model-risk + on-call" risk officer), preserve-intent mode; four rounds; all at AGREE; "No council decision was reversed."

| Round | Result |
|---|---|
| 1 | 4 × CRITIQUE; 88 deduplicated issues (9 blockers, 45 majors, 33 minors, 1 preference); 3 rejected |
| 2 | 0 blockers, 19 majors; 56 issues; rulings R2-C1 to R2-C7 |
| 3 | 3 × AGREE, 1 × CRITIQUE (risk officer); 3 majors, all accepted; 27 items |
| 4 | Risk officer AGREE; two clarifications: the end date of a card registered after the freeze is fixed by rule; a NAV failure in a FORWARD-SIM book fails closed instead of halting |

Six load-bearing changes (CR L258–265) — each is a build requirement:

| Change | Ruling |
|---|---|
| **HALT is scoped to the book.** Among data inputs, only an acting input bound to a book can halt it; risk-model, context and forward-simulation failures never halt; `halt.causes[]` keeps every cause | C-1 |
| **Schemas are the contract.** §6 JSON schemas declare every rule output, provenance, `knowledge_utc`, hashes and governance events; every example validates | C-7 |
| **The gate package is frozen whole before any control runs**, including D6's default rule, the data cut-off and the redesign budget: a failed acceptance test may be redesigned once; a second failure, counted across all 2.x versions, ends card evaluation under v2 (T-GATE-04) | R2-C2, R2-C3 |
| **The selection factor f is computed, never declared.** `step3()` computes it from the family trial ledger, whose rows are full `config_id`s with every parameter in the key; f = the maximum over the defensible row-set readings; where the acceptance report and a card run differ, the larger binds | C-2, R2-C1, R3-2 |
| **Data cut-off pinned** at the last official closes in the frozen reference data: **KR 2026-10-02, US 2026-10-01**; later data enters only through a re-gate | R3-3 |
| **Verdicts are authenticated; forward records are append-only.** A verdict is accepted only when the package md5, the data snapshot and the code's git hash match; a record's age counts from first registration; every HALTED or DISARMED decision after an operator kill of a card's forward books counts toward the record's 10% integrity budget | R2-C4, R3-1 |

Final-check checksums for the implementer (CR L267): 17 YAML and 14 JSON blocks parse; all 233 test IDs defined; all 43 config keys resolve; config copies match §7. Open, non-blocking tasks (SPEC §9.4 items 15–17): anchored timestamps for `spec_versions` and the ledger seed rows; an archived data snapshot for each formal card; atomic per-book `engine_feed` delivery. M1 must still measure: the NYSE print bound, FRED's VIX posting lag, the KODEX 200 basket time.

**Korea expected outcome arithmetic (CR L269; MR L5).**
```
PC-3 passes iff p_ni * f <= 0.10
indicative excess-return p_ni = 0.078  ->  tolerates f <= 1.282
indicative f: 1.26 (R4's three rows alone) | 1.49 (with the DL-A grid) | 2.87 (family-wide)
every reading that includes the DL-A seed exceeds 1.282; the maximum binds
card MDE80 = 0.14 > 0.10  ->  failed PC-3 p-value maps to INSUFFICIENT DATA, reason `underpowered` (SPEC §8.9, R-24)
```
"On current evidence the formal run is therefore expected to return INSUFFICIENT DATA, so the card is not expected to build." Status stays BUILD-AS-INSURANCE on a formal PASS, "but that route is not expected to trigger, and no convention may be changed to rescue it (R2-C1)". Then: "a labelled control in the specification book, re-gated only when new history adds an objective episode, while the recommended book carries only the invariants."

### A.9 Limitations (CR L271–279)

- Panels are simulated; convergence partly reflects shared inputs; not a practitioner survey.
- One vendor: Korea results use Yahoo `^KS11` (price index, no dividends, no second source before 2015). Yahoo omits the Saturday sessions KRX held before 12 December 1998 (1997–98 Monday returns span two sessions; variance 2.30× Tue–Fri vs 1.11–1.33 later). Files also hold flat zero-volume rows, an 800-day hole in KODEX 200 (Feb 2007–Apr 2009), 778 negative adjusted closes for SK hynix up to Dec 2002, and `^GSPC` open = prior close on 94–98% of 1996–2005 days (US range estimators fall back on Parkinson's high–low form). The formal Korea run needs KRX official closes; the US futures run needs the 1926 daily file (HTTP 403).
- Korea pass fragile (A.3).
- Untested: Korea leverage state and a calm-state reversal test net of 35 bp and the 0.20% tax (no KRX margin, leveraged-product AUM, stock-level data); Korea reversal prior cut from 3 to 1 stays UNVERIFIED; KIS level-1 quote fields, the KRX post-close session's status after 14 September 2026, the app's GJR study on SPY and the printed form of equation 9 are unverified.

---

## B. The macro overlay research report

### B.1 The dated update note (MR L3–11), "Council update (2026-10-03)"

"This report predates the Quant Council and has been corrected by it: all 59 of the council's REPORT errata are applied in place (`council/QC_errata.csv`)." Material reversals:

| # | Reversal | Binding consequence |
|---|---|---|
| 1 | "2 Oct close" was an intraday print: 6,943.66 written 10:56 KST; official close 7,003.74; dependent values recomputed | fixtures and text use 7,003.74 |
| 2 | Korea vol target re-tested on 1997–2026: fragile indicative PASS **at f = 1** (ΔMDD +12.7 pp, tail ratio 0.68, p_ni 0.052; 2016–25 and 1997–2002 alone REJECT). With f: expected INSUFFICIENT DATA; "no convention may be changed to rescue it" | A.8 |
| 3 | US 50 bp REJECT is an instrument fact (single US shares via KIS, daily); index-futures card at 5 bp (MACRO-R06-US-FUT) forward-simulated; passes 1990–2026 only on a knife edge (11 of 44 start dates) | Res. 2 |
| 4 | R-11 and R-12 retired as REJECTs on long data (USD/KRW: 54 strict-H.10 onsets on 1997–2026; rates: 71 onsets, REJECT at every timing and cost); "survive only as labelled, display-only refusal books, which is how the body's 'shadow legs' should now be read" | every "shadow leg" in MR body = refusal book |
| 5 | SMA20 dominated under QLIKE (outside the 90% set at 1, 5, 21 days in both markets, p ≤ 0.0005) but stays the acting estimator and displayed baseline; COMB = ½(GJR-t + log-HAR-range) registered challenger behind a staged, counted, fail-closed gate | Res. 3 |
| 6 | Gate package revised: PC-1′ tail legs (ES of 21- and 126-session returns) replace single-path drawdown; PC-3 binds; trials counted on a family ledger; whole package frozen blind behind a placebo and negative-control acceptance test before any card runs; D6, the data cut-off and the selection-factor rule frozen into the package | Res. 4, 5; A.8 |

### B.2 Conclusions (MR L13, L276–280)

- Macro belongs in QUANTGEN "as a risk-sizing, data-hygiene, hedge-validity and event-handling layer. It should never be a source of direction."
- 60 single-proposition nodes, 240 edges (120 supports, 48 refutes, 44 qualifies, 28 conflicts) from 139 chair items: **27 CORE-LINKs** → spec; **11 CORE-PROHIBITIONs** → DO-NOT-BUILD; 22 → backlog (15 contested, 4 one-sided, 3 untested) (MR L179).
- What works is sizing by own risk state: momentum own-vol scaling (US Sharpe 0.40 → 0.71 at cap 1.0; 0.80 with the D&M gate floored at 0.5; MDD −63% → −21%); Korea-local 20-day vol target (22 Jun–30 Jul 2026 crash −38.6% → −12.2%; −12.3% net of 35 bp).
- Largest fake result was timing: old Korea gate +0.31 Sharpe → +0.05 once US-session data were lagged honestly.
- A de-risk overlay is worth 0.00 to +0.10 Sharpe; +0.05 from a market vol target needs about 150–330 years to detect → overlays need "their own pre-registered, drawdown-first claim type" (CARD-P).
- "the most valuable 'macro' inputs turn out not to be macroeconomic": a strategy's own volatility, Korea's own volatility and concentration, the sign of the stock–bond correlation, and a timestamp. Classic macro models survive "as a reading list for interpreting central banks, not as code".
- Most important open question: what led Korea's 2026 deleveraging; data partly in the KIS feed, not yet logged.

### B.3 Core links (MR L192–200) — rules the build encodes

| Area | Rule (MR wording) |
|---|---|
| Size by own risk | Overlays de-risk-only; multipliers within [0.5, 1.0]; vol-target weight capped at 1.0; only the fail-closed risk engine can go to 0×. Momentum: own-vol scaling and the D&M gate floored at 0.5 (now R-04 DEMOTED, specification book only). Reversal and quality stay at 1.0×. Stress variables feed volatility estimates and new-entry blocks, never cut-and-re-add triggers |
| Korea is its own market | Local 20-day vol target capped at 1.0. Pair rule in MR: if Samsung + SK hynix exceed 45% of KOSPI, held to ≤ 35% of the long book (superseded by D1 = MSCI 25/50, A.2). US overnight moves only as opening-gap inputs (prior US session ≈ 15% of KOSPI daily variance; SOX beta 0.17 (2015–19) → 0.56 in 2026; 0.25 full sample) |
| Data hygiene | Every input carries UTC and publication timestamps; lags calendar-based; Brent always named spot or futures; closes used, never circuit-breaker prints; missing inputs fail closed |
| Macro as context / hedge-validity state | Sahm, curve probit, Taylor ranges, real yields, term premium logged and never act. Hedge credit withdrawn when core PCE ≥ 3% or the 63-day stock–bond correlation is positive |

### B.4 The eleven prohibitions (MR L202)

Upward multipliers and the four-state table; VIX-term-structure momentum switches; macro factor gates (curve, real rate, credit, levels); Korea gates built from US inputs; fixed textbook coefficients; the lagged oil gate; net-liquidity and M2 rules; regime and ML shortcuts (smoothed probabilities, unpenalised HMMs, "complexity" timing, LLM backtests before the model's training cutoff); Street forecasts and surveys as inputs; 24-hour blackouts; calendar and issuance tilts.

### B.5 Errata: corrected anchors that "must not propagate" (MR L159–173)

| Wrong value as first circulated | Corrected value |
|---|---|
| D&M dynamic Sharpe "≈1.43 vs 0.71 static" | 0.682 → 1.041 (constant-vol) → 1.194 (dynamic, OOS), 1934–2013, JFE Table 7. Do not pair 0.71 with Table 7 |
| Prior Korea gate (SOX 60d × USD/KRW 20d) +0.31 Sharpe | +0.05 implementable (share 0.67); −0.16 in 2024–26; SOX leg alone −0.22 |
| KRW leg +0.07 with H.10 as "daily, T+1" | +0.03 (0.5× leg, Yahoo timing); 0.75× leg +0.016 with one extra session; +0.001 under strict H.10 publication (weekly, Mondays 4:15 pm) |
| Rates leg +0.041 | +0.038 value timing; +0.010 at a one-business-day lag (compliant via the Treasury par-yield channel when posting time is logged); −0.000 at the strict two-business-day H.15 lag |
| KOSPI Q3 −18.8%; peak ≈9,386 | −19.3%; closing peak 9,114.55 (22 Jun) |
| Brent $127 / $114 as tradable | Dated spot; futures $118.35 / $102.59 |
| BoK 27 Aug "unanimous" | 6–1, base rate 3.00% |
| 10y 5.29% "19-year high" | Highest close since 14 May 2002 |
| Fed "≈140 bp behind Taylor" | −0.89 pp central; 0.4–2.3 pp range |
| Ilmanen "30% out-of-sample decline" | ≈ 30% is the average; priors use factor-specific declines: value −49%, momentum −23% (n.s.), multifactor −18% |
| KRW carry skew −4.06, worst quarter −58.6% | Skew −2.38, worst −36.9% (monthly-average FX); quarter-end point-in-time FX: skew −1.80, worst −43.8%; post-float Fama β −1.63 |
| 9 Mar 2026 KOSPI −8.11% | Close −5.96%; −8.11% was the intraday circuit-breaker print |
| CPI across the Oct-2025 gap by positional `shift(12)` | Aug-2026 CPI inflation 3.35%, not 3.71% (MR L25) — lags must be calendar-based |

Council-applied corrections inside the body: KOSPI 2 Oct close 7,003.74 and −23.2% from peak (MR L53, L65); SE(ΔSR) 0.061/0.130 and "about 150–330 years", MDE80 0.13 and 0.28 (MR L139); Markov KOSPI 30.8/yr only with a 2-year initial training window, 9.75–9.95 with long training (MR L121); D&M gate expected add-on ≈ +0.07 (local +0.072 net of 50 bp), "a floored binary heuristic inspired by it, not the published rule" (MR L131); R-03 years statistic: cap binds in 20 of 37 years, scaled sleeve higher Sharpe in 15 (75%) gross and 11 (55%) net of 50 bp, other 17 years ties (MR L129).

### B.6 State on 30 Sep–2 Oct 2026 (MR L57–67, L248–256) — day-one readings

| Item | Reading | Overlay meaning |
|---|---|---|
| Fed / BoK / BoJ / ECB | 3.75–4.00% / 3.00% / 1.25% / 2.50% | policy-direction states must allow sign flips |
| UST 10y; 20-day change | 5.29%; +50 bp | rates leg ON in data dated 23 Sep; under strict H.15 timing applies from the 25 Sep close (now a refusal book) |
| 10y TIPS / breakeven / KW term premium | 2.93% / 2.36% / 1.02% | real-yield and term-premium shock |
| Core PCE; stock–bond corr (63d) | 3.01%; +0.53 | `hedge_credit_off` TRUE |
| VIX / VIX3M; HY OAS 21-day change | 16.34 / 18.37; +47 bp | VIX flag OFF; credit just under the +50 bp context threshold |
| USD/KRW 20-day change | −1.8% | KRW leg OFF (refusal book) |
| KOSPI; rv21; Korea vol-target weight | 7,003.74 (−23.2% from peak); 31.9%; 0.61 | local risk control binding |
| Samsung + SK hynix share of KOSPI | ≈51% implied (51–54% by anchor; re-anchored monthly) | pair-concentration cap active (>45%) |
| Dated Brent / front-month futures | $113.96 / $102.59 | name the series in every rule |
| D&M bear state | OFF (24-month market return +39.7%) | |

For v2 acceptance use SPEC §11, not this table (it predates the retirements).

### B.7 Model-failure map → QUANTGEN treatment (MR L108–125)

| Model | Treatment |
|---|---|
| Okun's law | Prohibited as a coefficient; context only |
| Phillips curve / NKPC / sacrifice ratio | Inflation state = realised core momentum + expectations |
| Taylor rule | Range-reported context; never a threshold |
| Sahm rule | Logged prior |
| Yield-curve probit | Prior only; drop 10y–2y |
| Expectations hypothesis / term premium | Track real-yield and TP changes, not the policy direction |
| UIP / carry | No rate-differential FX model; carry gated on FX trend and JPY vol, not VIX |
| Dollar safe haven | Classic risk-off needs USD up AND yields down; USD↓ with equities↓ = hedge-failure flag |
| Gold vs real rates | Short-horizon beta only |
| Stock–bond correlation | Hedge credit off when core PCE ≥ 3% or corr63 > 0 |
| Return predictability | OOS-R² gate before any predictor scales a weight, with Clark–West and Giacomini–White tests reported beside it |
| Markov / HMM without persistence penalty | Filtered states only; no unpenalised daily HMM gates |
| Jump models | Research item only; no regime engine |
| Macro factor timing | Prohibited |
| Street forecasts | Not inputs; SEP error bands (±1.4 pp ≈ 70% band; ±2.2 pp for a 90% fan) as Monte Carlo priors |
| Surveys and positioning | Context with publication timestamps |

Empirical law both panels adopted (MR L106): implied vol and credit-spread changes carry incremental OOS variance information for US horizons up to a month; no stress variable forecasts lower returns OOS (none survives BH-10%). VIX level → US variance t = 7.17 (R² 0.385), vs t = 0.04 for next-21-day returns. Neither is a KOSPI volatility input beyond KOSPI's own volatility.

### B.8 What it means for the app's existing surfaces (MR L224–258)

- **Translation of old triage words (MR L228).** "BUILD NOW" = computed, displayed, allowed to size strategy cards in the Strategy Lab; only a card with a PASS verdict may feed the displayed recommendation; other BUILD NOW cards run as descriptive books labelled with their verdicts. "SHADOW" = computed and logged as a dated, pre-registered card with a forward record, *withheld* as a signal (matches the desk's existing "Withheld" labels). "DO-NOT-BUILD" = REJECT cards that stay on the public record.
- **Macro surface (MR L228).** The 18-indicator sheet with z-scores and a regime read "is the right home for the spec's context log (R-13), on two conditions": z-scores use expanding or trailing windows with publication timestamps, never present-calibrated levels; "nothing in it may feed a signal". "The same applies to the crypto page's six-part regime score."
- **Gap 1, the gate (MR L230–232).** The nine-step gate tests outperformance (step 5: one-sided p ≤ 0.10 vs buy-and-hold). Existing evidence: Strategy Lab card "E1 · trend switch" rejected at OOS Sharpe 0.84 vs 0.95, p = 0.75, though drawdown −27% → −15%. Fix = CARD-P; card reports the bull tax every month; each card prints its own Harvey–Liu haircut; expected live Sharpe at 60% of OOS (`live_sharpe_multiplier: 0.60`).
- **Gap 2, costs (MR L234).** Body numbers are gross; Addendum gives net. KRX stocks 35 bp per side = 70 bp round trip = 140 bp at 2×. Korean reversal and the D&M gate on Korean momentum are untested on KRX data.
- **Gap 3, logging (MR L236).** KIS key already reads USD/KRW fixing, investor flows, short-sale data; log them daily with publication timestamps. KRX margin debt and leveraged-ETF AUM need a separate source; a trading-volume proxy fails out of sample.
- **Quant Lab (MR L240).** GARCH(1,1)-t fan already REJECT on SPY in t-quantile form (6.6% breaches, PIT p 0.003; UNVERIFIED until script and seed published). A 504-close GARCH is captured by its window (persistence 0.27–1.00 across 303 monthly refits; latest fit implies 61% unconditional vol). R-16: parameters on an expanding window of at least ten years, tails by FHS/EVT, acceptance on OOS 99% VaR, ES 97.5% and fan-PIT tests. Named scenario library: 2026 Hormuz path on Dated Brent *and* futures; July 2026 KOSPI unwind; September 2026 rates shock; August 2024 carry unwind; April 2025 "sell America".
- **Rates & FX page (MR L242).** Already withholds FX momentum and dollar carry; no change.
- **Crypto (MR L244).** Record the prohibited net-liquidity rule (−0.20 Sharpe in 2023–26) as a REJECT card rather than build it.
- **Policy-break protocol (MR L258).** R-18 re-validates any macro-conditioned setting after the Warsh transition and the September hike.

### B.9 Addendum: indicative verdicts at QUANTGEN's own costs (MR L284–301)

| Rule | Gross | At cost (2×) | Indicative verdict (wording to keep) |
|---|---|---|---|
| Momentum own-vol scaling (US, 50 bp both legs) | Sharpe 0.714 | 0.672 (0.631) | "PASS on the French series; step 3 borderline" — ΔSharpe vs unscaled +0.273, p ≤ 0.001; 70% of years positive; deflated ΔSharpe 0.98 at N_equiv 6.3, 0.947 at linear 12.6 |
| + D&M gate, floor 0.5 | 0.798 | 0.745 (0.691) | "Not recommended: fails step 3 and the holdout; specification book only" — add-on +0.072, p 0.018; 7 US onsets since 1990, 34 pooled; deflated add-on 0.77; holdout 1 of 3 |
| Korea 20-day vol target (ETF 3 bp / stock 35 bp) | 0.641 | 0.638 / 0.609 (0.635 / 0.576) | "1997–2026: PASS (indicative, fragile; 2016–25 REJECT). 2016–26 alone: INSUFFICIENT DATA" — 2016–26: MDD −36.8% / −37.2% vs −41.3%, +4.4 / +4.1 pp, tail 0.82, p_ni 0.25 / 0.32, July 2026 = 59% of benefit |
| US 15% vol target (US shares via KIS, 50 bp, daily) | 0.602 | 0.505 (0.409) | "REJECT, instrument-specific" — turnover 2.52/yr costs 1.26%/yr; ΔMDD +0.2 pp (−3.4 pp at 2×) |
| USD/KRW leg, 0.75× | +0.032 value timing; +0.001 strict H.10 | +0.029 at 3 bp; −0.008 at 35 bp | "REJECT on 1997–2026 at every timing" (54 strict-H.10 onsets; ΔMDD −1.3 pp; tail ratio 1.00) |
| US rates leg, 0.5× | +0.038 value timing; −0.000 strict H.15 | −0.103 (strict, 50 bp) | "REJECT at every timing (including the compliant Treasury +1 business day) and every cost, gross included" — turnover 3.60/yr costs 1.80%/yr; drawdown 3.5 pp worse than static |

Bullets that bind display (MR L296–301): the KRX ETF line (3 bp) "must be declared on the card before the run"; the forward record "is a falsification alarm, not the route to a verdict"; momentum own-vol scaling is "the only overlay with a clear net benefit, and the only one likely to enter the displayed recommendation once its card runs on QUANTGEN's own sleeve"; SMA20 "stays the displayed baseline, but it is not a validated default" (B5-style check: 5% VaR breached on 4.70% of KOSPI days, 4.99% SPY, 5.31% US-market; 9 of 12 forecasters also pass on KOSPI, so B5 cannot choose); **"Until any macro card runs, the displayed recommendation carries only the invariants: point-in-time data, bounds, the Korea caps, the drawdown ladder and the hedge state."**

### B.10 Open research nodes with settling tests (MR L210–222)

N-22 (KRW leg) and N-24 (rates leg): settled REJECT, archived as refusal books (backlog BL-S01, BL-S02). N-51: settled — uniform hurdle applies (holdouts passed 1 of 3). Still open, no build: N-19 Korea leverage/flow/semis-cycle state (does margin debt or leveraged-ETF AUM lead KOSPI rv21 by ≥ 5 days and improve vol-target ΔMDD in ≥ 3 episodes?); N-08 D&M floor 0/0.25/0.5; N-10 reversal in fast stress (forward-sim with stress-day cost = measured KIS quote-snapshot all-in cost OR 35 bp per side, never their sum); N-45 oil-shock event rule; N-21 foreign flows; N-35/N-36 regional and Korea factor priors; N-39 momentum entries ×0.5–0.7 on decision days (professors only); N-59 Korean supply screens (executives only).

### B.11 Limitations (MR L260–274)

Latest-vintage data (only real-time Sahm is a true vintage); no KRX stock-level, investor-flow, margin or minute data locally; factor tests gross of costs on Ken French factors (constituent turnover uncosted); 63-day circular-block bootstrap shorter than the 214–245-day Politis–White blocks for squared returns (longer blocks lower the D&M gate's z from 2.01 to 1.80); 2022–26 is a reported stress-test set, not a holdout; many 2026 lessons rest on n = 1; panels simulated; v1.0 execution conventions (09:00–09:30 KST no-entry window, closing-auction routing, BoK release windows) are moot for a read-only desk "except as assumptions about which prices are tradable" — v1.1 keeps the windows only as evaluator blocks on simulated entries.

---

## C. What the app must say

### C.1 Standing disclaimers (verbatim sources)

| Where | Text | Source |
|---|---|---|
| Any surface or doc that shows council/panel content | "All panel members in these documents are simulated, fictional composites; nothing speaks for any real firm or person." | BR L18 |
| Same | "Not investment advice: QUANTGEN is a read-only research desk with no order path." | BR L18 |
| Footer form used on the council page | "all panel members are simulated, fictional composites · not investment advice; QUANTGEN is a read-only research desk with no order path." | `pages/QUANTGEN_Quant_Council.html` footer |
| Footer form used on the neural-link page | "research only, not investment advice." / "Verdicts are indicative, computed outside QUANTGEN's own gate." / "Nothing here places an order." | `pages/QUANTGEN_Macro_Neural_Link.html` |
| Report end notes | "All personas are simulated; no statement is attributed to a real firm or person beyond its published work." | CR L375 |

Rules: never attribute a quote, number or internal practice to a real firm (CR L22); archetype labels describe career styles, not firms (CR L5). Keep the existing RD statements "there is still **no broker order path** in this repository" (RD L329–330) and the Regulatory note (RD L393–398).

### C.2 Status vocabulary to display (strings as written in CR/MR/SP)

| String | Meaning | Source |
|---|---|---|
| `PASS`, `REJECT`, `INSUFFICIENT DATA` (reason e.g. `underpowered`) | card verdicts | CR L269 |
| `BUILD-AS-INSURANCE` | Korea vol target status on a formal PASS only | CR L115 |
| `FORWARD-SIM` | forward-simulated book; never raises a verdict; never in the recommended book | CR L116, L237; SP L73 |
| "labelled control" in the "specification book" | Korea card if INSUFFICIENT | CR L128, L269 |
| "recommended book" | only PASS and BUILD-AS-INSURANCE cards reach it | CR L237 |
| "labelled, display-only refusal book" / `RETIRED` | R-11, R-12 | MR L7; SP L4789 |
| "indicative" | any full-sample number not from a formal gate run | CR L5; MR L284 |
| `harm` / `null` / `inconclusive` | label on every DO-NOT-BUILD entry; not "refuted" | CR L243 |
| `PRINCIPLE CHANGE` | label on any proposal altering a principle | CR L9 |
| `UNVERIFIED` | Korea reversal prior; app's GJR study until script and seed published | CR L279; MR L240 |
| `HALTED` per book with `halt.causes[]` | HALT is book-scoped | CR L260 |

The existing gate enum is `INSUFFICIENT_DATA` (`core/quant/validate.py` L50; RD L215–216); the reports write "INSUFFICIENT DATA". See Ambiguities 7.

### C.3 Per-card labels

| Card | Must show | Source |
|---|---|---|
| R-06 KR (Korea 20-day vol target) | Label, verbatim: "Crisis-clustering insurance: reduces drawdown in volatility-clustering crises (1997–98, 2008, 2026); no help against gap shocks from calm states (2018-10, 2020-02, 2024-08); Sharpe non-inferiority is marginal — it pays a premium in calm decades (2016–25 alone: tail 0.95, ΔSR −0.079) and is short the post-crash rebound premium; not expected to outperform; cap 1.0 permanent." | SP L1574, L4906 (CR L128 abridges it) |
| R-06 KR | Expected-outcome line: on current evidence the formal run is expected to return INSUFFICIENT DATA (`underpowered`), so the card is not expected to build; no forward-record route; forward record = falsification alarm only. The risk officer: "an honest outcome of the design" that "belongs in the owner's briefing" | CR L269 |
| R-06 KR | Printed, non-gating: ΔMDD, CDaR, daily ES99; PC-4 under both episode rules (0.493 §8.6 vs 0.174 objective); timing return (−1.84%/yr), bull tax (H1 2026 +51.7% vs +101.1% gross; +50.5% net of 35 bp); p_ni raw 0.051/0.052 and excess 0.078; f readings | CR L73, L107, L118; MR L206, L296 |
| R-06 US 50 bp | `"REJECT (instrument: US shares via KIS, 50 bp, daily)"`; never re-run; "a fact about trading it in single US shares at 50 bp", "not evidence against vol targeting" | CR L3, L116; MR L6; SP L4291, L5646 |
| MACRO-R06-US-FUT (R-29) | FORWARD-SIM; "passes on 1990–2026 only on a knife edge (11 of 44 start dates)"; pending the 1926+ settling run; not in the recommended book | CR L116; MR L6; SP L224 |
| R-03 momentum own-vol scaling | "indicative PASS"; "step 3 borderline"; both numbers: 0.98 at N_equiv 6.3 and 0.947 at linear N̂ 12.6 | CR L119, L233; MR L288 |
| R-04 D&M gate | "a floored heuristic, not the published rule"; "step 3 FAIL" (0.77); "specification book only"; "Not recommended: fails step 3 and the holdout" | CR L233; MR L289 |
| R-08 VIX ≥ VIX3M | "execution annotation" (not an entry block, not a multiplier) | CR L122 |
| R-11 USD/KRW leg, R-12 rates leg | REJECT recorded on long history; display-only refusal book; read by no other book | CR L122; MR L7 |
| R-28 trend | "protective-only" monthly SMA10m, 0.5× below trend, US and other non-Korean sleeves, FORWARD-SIM; Korea context only; protection works through volatility, Sharpe gain fails deflation | CR L123, L59 |
| R-31 step-down | −8% / −12% steps time-boxed at 21 sessions; specification book until PASS; hard stop = governance event | CR L120; SP L226 |
| Volatility estimator | SMA20 = "acting default and displayed baseline", never "validated default"; COMB = "registered challenger" | CR L117; MR L300 |
| Every card header | instrument book, notional, tick floor, execution variants, rebalance rule, band (a card without them is refused); power/MDE line; own Harvey–Liu haircut; `live_sharpe_multiplier: 0.60` (never "60% haircut") | CR L229, L164, L241 |
| Every DO-NOT-BUILD entry | harm / null / inconclusive | CR L243 |

### C.4 Data-truth statements

- A value's status must be visible: provisional/intraday vs official close (`value_status`). The 2 Oct 2026 KOSPI official close is 7,003.74 (CR L81).
- Brent always named "Dated spot" or "front-month futures" (MR L45, L67, L198).
- Closes, never circuit-breaker prints (MR L173, L198).
- One-vendor caveat on Korea history: Yahoo `^KS11`, price index without dividends; formal run needs KRX official closes (CR L275). If KRX official closes are absent, the Korea card cannot be formally run — show it as not formally run, not as a verdict.
- Data cut-off of the frozen package: KR 2026-10-02, US 2026-10-01 (CR L264).

### C.5 What must not be displayed

- No regime state, acting or displayed; no change-point/BOCPD flag on any screen (research log only) (CR L102, L107, L124, L243).
- The existing Macro page shows regime chips (`ui/macro_page.py` L135–141; `core/ficc/macro.py` L38–42, L94: curve / `risk-on`·`risk-off`·`neutral` / dollar / trend, rule-based off five rules). SP §3.6 rule 3 (SP L1124–1126) decides: if it comes from a regime model, remove; otherwise it may stay as a descriptive text summary, never presented as a regime state, never reusing the calm / normal / elevated / stressed names, never feeding signals, risk or the engine. Z-scores stay display-only (SP L1123). Same condition for the Crypto page's six-part regime score (MR L228; `ui/crypto_page.py` L77, L122).
- No context item read by an acting module (CR L235).
- No forward record presented as validation (CR L101, L103).
- No multiplier above 1.0 anywhere (CR L241).

### C.6 What QUANTGEN's README (RD) should now state

Current RD facts: describes app "Version 2" (FICC) and "Version 3" (expansion); says QUANTGEN "computes analysis, ranks outcomes, and recommends" (RD L6); gate vocabulary `PASS / REVISE / REJECT / INSUFFICIENT_DATA` (RD L215); "229 checks" and "245 checks" (RD L347, L379; stale — the runner is at 266 before this build); Regulatory note (RD L393–398). No mention of the macro programme, the council or "not investment advice".

Add (minimal, one new section plus edits):

1. A "Macro integration (Quant Council specification v2.0)" section: macro sizes risk and never sets direction; nothing exceeds 1.0×; nothing places an order (CR L3). List P0–P10 one line each (A.7).
2. The two disclaimers of C.1, verbatim.
3. Honest status: the numbers in the reports are indicative, not runs of QUANTGEN's gate; the gate package is frozen whole before any card runs (placebo test: at most 10% of 300 circular-shift placebos per family may pass; named negative controls must fail; one bounded redesign); no forward record can raise a verdict; only PASS and BUILD-AS-INSURANCE cards reach the recommended book; until a macro card runs the displayed recommendation carries only the invariants (point-in-time data, bounds, the Korea caps, the drawdown ladder, the hedge state).
4. Card status table (C.3), including the Korea expected outcome (INSUFFICIENT DATA, not expected to build) and the US 50 bp instrument label.
5. New statuses beside the existing four decisions: BUILD-AS-INSURANCE, FORWARD-SIM, RETIRED refusal book, labelled control; book-scoped HALTED (RD L328 describes one engine-wide DISARMED→ARMED→HALTED).
6. Data limitations: one price vendor; KRX official closes and the French 1926+ daily file are not in the repo; reference datasets the spec cites are not on this machine; data cut-off KR 2026-10-02 / US 2026-10-01.
7. Pointers: where the two reports and the spec live (section D); DO-NOT-BUILD labels harm/null/inconclusive.
8. Verification count updated to whatever `python tests/run_all.py` prints after the build (do not write a number by hand).
9. Check wording of RD L232–234 ("capped vol targeting (the Cederburg real-time result)" under "Rejected"): that is the asset-expansion study's card, not MACRO-R06; add one clause so it is not read as a refusal of vol targeting in general (CR L75–77).

---

## D. Where the two reports live in the repo

Facts on disk (2026-10-06):
- Bundle sits at repo root: `QUANTGEN_Quant_Council_2026-10-03/{README.md, claude_code/, reports/, pages/}`.
- `reports/` holds one file: `QUANTGEN asset coverage expansion.md`. `research_notes/` holds `QUANTGEN asset coverage expansion/` and `QUANTGEN v2 integration map/`. RD L152–154 documents this convention (`reports/<name>.md` + `research_notes/<name>/`).
- No `research_notes/QUANTGEN macro overlay research/` and no `QC_*` / `ASPEC_*` / `QF*` / `QX_*` file anywhere in the repo.
- The repo is not a git repository.

What the sources cite:
- SP L9, L6461: council sources under `research_notes/QUANTGEN macro overlay research/council/` (resolutions, modules, errata, ledger, three chair files, ASPEC rounds); QF/QX/DL notes one level up; scripts and results under `quantgen_macro_data/`.
- CR L373: the macro report's original path `/home/claude/reports/QUANTGEN macro overlay research.md`; SPEC and backlog at `/home/claude/deliverables/`.
- MR L11: the council report is `QUANTGEN_Quant_Council_Report.md` "(same folder)" — the two reports must stay co-located.
- SP L6018: fixture manifest `tests/fixtures/macro/MANIFEST.csv` (proposed) names sources under `research_notes/…/council/`.

Placement (default; copy, do not move — the bundle stays as delivered):

| Target path | Content | Why |
|---|---|---|
| `reports/QUANTGEN macro overlay research.md` | copy of `…/reports/QUANTGEN_macro_overlay_research_report.md` | matches CR L373 and the existing `reports/` naming |
| `reports/QUANTGEN_Quant_Council_Report.md` | copy of the council report, filename unchanged | MR L11 refers to it by this name, same folder |
| `research_notes/QUANTGEN macro overlay research/council/README.md` | one short pointer file: lists the council working files the spec cites (SP L6465–6472) and states they are not on this machine | keeps the cited path resolvable without fabricating `QC_*.csv` |
| (unchanged) `QUANTGEN_Quant_Council_2026-10-03/pages/*.html` | offline visual pages | already self-contained (BR L16); link from RD |
| (unchanged) `QUANTGEN_Quant_Council_2026-10-03/claude_code/*` | spec, tasks, backlog | implementers read them in place |

Lazier alternative if the coordinator prefers zero duplication: leave both reports in the bundle and add only the RD pointer plus the `council/README.md` stub. Either way do not create empty `QC_*` files; any fixture row or test whose source is under `…/council/` or `/home/claude/quantgen_macro_data/` is unavailable locally and must fail closed or skip with a stated reason.

---

## Ambiguities (conservative reading: no exposure change, specification book only, fail closed)

1. **Ledger arithmetic (CR L111).** Classes sum to 266 non-register items; text says 265 "ruled or consent". VALID-BUILD + ERRATA + SHADOW = 214; text says 213 accepted. Also "355-row docket" (CR L36) vs 361 ledger items. Informative only; do not hard-code.
2. **D1 vs MR pair rule.** MR L196 (and L66) still states ">45% → ≤35% of the long book"; SPEC D1 in force is MSCI 25/50 (SP L69). SPEC governs.
3. **D2 default −15% vs its own evidence** (fires 24 times, deepens MDD on KOSPI VT20; CR L133). Owner decision; build the configured value `risk_layer.drawdown.hard_stop.level`, do not tune.
4. **Korea card cannot be formally run here.** KRX official closes are not in the repo (only Yahoo/FRED caches). Reading: card = labelled control in the specification book, status "formal run not performed" (or INSUFFICIENT DATA only if the frozen gate actually runs on admissible data); never BUILD-AS-INSURANCE; never in the recommended book.
5. **Git hash requirement (CR L265) vs a non-git repo.** A verdict "is accepted only when the package md5, the data snapshot and the code's git hash match." With no git hash, no verdict can be authenticated. Reading: fail closed (verdicts unauthenticated → not accepted) until the owner puts the repo under git; do not substitute another hash silently.
6. **Gate-acceptance test has not run (CR L279)** and needs the reference data. Until it passes, no formal card verdict may be displayed; only indicative numbers labelled as such.
7. **`INSUFFICIENT_DATA` (code enum) vs "INSUFFICIENT DATA" (reports).** Reading: keep the existing enum in `core/quant/validate.py`; use the spec's §6 schema enum for v2 artifacts; display text with a space. Do not rename the existing enum.
8. **Detection horizon:** "146–330 years" (CR L61, L85) vs "about 150–330" (MR L13, L139, L268). MDE80 0.13 / 0.28 (MR L139, US/KOSPI vol targets vs S) vs Korea card MDE80 0.14 (CR L269) — different bases; goldens must come from the SPEC, not from either report.
9. **p_ni variants:** 0.051 (QF4, raw), 0.052 (DL-A definitive cell), 0.078 (excess returns). f tolerance 1.282 (CR L269, MR L5) vs "1.28" (SP L5387); f on R4's rows 1.26 (CR) vs 1.26–1.30 (SP L5387). Informative; f is computed by `step3()`, never typed in.
10. **Korea vol-target weight:** 0.61 (MR L65, L253; the weight earning on 2 Oct) vs 0.694 (CR L81; the next weight after the corrected close). Different quantities; name which in any fixture.
11. **MR body still uses pre-council language:** "two macro legs survived … as shadow" (L13), day-one table "Rates shadow leg ON" / "VIX entry block OFF" (L248–256), build order naming "the B5 estimator gate" and "cards through the nine-step gate" (L246), "Momentum sizing (BUILD NOW)" 0.40 → 0.91 at cap 2 (L91). Read per the update note (MR L7, L11): shadow legs = refusal books; R-08 = annotation; v2 milestones per CR L227–239.
12. **R-03 step-3 value at linear N̂:** "0.946–0.947" (CR L89) vs "0.947" (CR L119, L233; MR L288). Use the SPEC golden.
13. **"Sep-2026 is not an episode" (Res. 11)** vs the Quant Lab scenario library naming "the September 2026 rates shock" (MR L240). Different objects (PC-4 episode vs replay scenario); do not add Sep-2026 to the episode table.
14. **App version naming.** RD calls the app "Version 2" (FICC) and "Version 3" (expansion); the programme is "SPEC v2.0". Reading: in RD name it "Macro Integration Specification v2.0 (Quant Council edition)", do not relabel the app as v2.
15. **Council working files absent.** SP L1798–1799 names `council/QC_modules.csv` and `council/QC_COUNCIL_RESOLUTIONS.md` as sources of truth for §5; they are not on this machine. Reading: the SPEC text itself (already errata-applied, SP L6) is the only binding source; CR's tables are abridged ("Acceptance test (abridged)", CR L227).
16. **Hard-stop "governance event" (Res. 6)** — CR gives no operator-facing text. Reading: per-book HALTED with cause recorded, manual acknowledge and explicit re-arm (as the existing engine already requires, RD L307–308); wording from the SPEC.
17. **Practice-gap scores** are the report author's reading, not a council vote (CR L147); if shown, label them so and never show a 3.
