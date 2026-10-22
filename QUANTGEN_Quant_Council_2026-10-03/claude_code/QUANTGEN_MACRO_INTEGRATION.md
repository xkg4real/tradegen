# QUANTGEN — Macro Integration Specification (v2.0)

| Field | Value |
|---|---|
| **As of** | 2026-10-02 (Asia/Seoul) |
| **Status** | **v2.0 (adversarial review complete: rounds 1–4; round 4 a confirmation, with two clarifications applied), the Quant Council edition.** Implementation-ready for QUANTGEN as it is actually built. Adversarial-spec rounds 1 to 3 (four opponent reviews each, plus the coordinator's binding rules and rulings, `council/ASPEC_R1_*.md` to `council/ASPEC_R3_*.md`; syntheses in `council/ASPEC_R1_synthesis.md`, `council/ASPEC_R2_synthesis.md` and `council/ASPEC_R3_synthesis.md`) are applied in place, as are round 4's two clarifications (`council/ASPEC_R4_risk_officer.md`, notes 1–2); see the first four changelogs below. It rebuilds v1.2 on the council's resolutions (`council/QC_COUNCIL_RESOLUTIONS.md`): 34 new, changed, demoted or retired modules (`council/QC_modules.csv`), the 125 SPEC errata already applied in place and the 44 SPEC section rewrites of `council/QC_errata.csv`. It supersedes v1.2 (kept unchanged as `.v1.2_INTEGRATION_backup.md`), v1.1, v1.0 (kept as `.v1.0_INTEGRATION_backup.md`) and the macro sections of the prior design, "QUANTGEN Signal & Macro Map". |
| **Audience** | Claude Code, building inside the QUANTGEN repository: the Flet desktop app whose entry point is `main.py`. |
| **Companion file** | `QUANTGEN_MACRO_BACKLOG.md`: everything not built here, with its settling test, plus Appendix V (the v1.1 verification log) and Appendix Q (the v1.2 independent QA log). The council's owner decisions and settling tests are summarised in the Quick start and §0.4 below. |
| **Council sources** | `research_notes/QUANTGEN macro overlay research/council/` (resolutions, modules, errata, ledger and the three chair files), the data labs `QX_DLA_data_lab_protective_cards.md` and `QX_DLB_data_lab_estimators_regimes.md`, the four cross-examinations `QX_PX1`, `QX_PX2`, `QX_EX1`, `QX_EX2`, and the seven QF papers `QF1`–`QF7` (§13). |
| **Codebase sources** | (1) the owner's *QUANTGEN Architecture Review* (written 2026-09-14, fetched 2026-09-20), including its ASCII map of the whole application; (2) the app's public page text (2026-09-29). Where this file names a path or an interface those two sources do not show, it is marked **proposed**. |

---

## Quick start for Claude Code (v2.0)

**Entry point.** Do not read this file front to back before starting. Read in this order, then build one milestone at a time:

1. **§1 (P0–P19) and §10 (DO-NOT-BUILD v2).** These are the hard constraints. Any code that violates them is wrong even if a test passes.
2. **The build order below and §12.** Each milestone names its modules, package, acceptance tests (§9) and golden values (§9.3). A milestone also passes the test table inside every rule it builds (R-19 to R-31, R-34; §9.0 maps each module to its tests). **Every test carries `runs_from: M<k>`**, the first milestone at which every module it depends on exists (§9.0a). A milestone's exit tests are exactly the tests and test clauses whose `runs_from` is that milestone or earlier; a clause whose dependencies arrive later runs from that later milestone and never blocks an earlier one. No test runs a formal card before the M7 freeze (P11). Do not start M(k+1) until M(k)'s exit tests pass in `tests/run_all.py`.
3. **Per milestone, read only the sections it lists, plus the §9 rows of its exit tests, §9.0b and, for golden values, the §9.3.1 construction rules and tolerances and §9.3.3.** Rules R-19 to R-35 are specified in full at the end of §5; §8 is the gate.
4. **§2, the evidence rows of §5 and §13** are background: why each rule exists. Consult them; do not implement from them.
5. **Reference data.** The datasets, scripts and results behind every golden value live outside the QUANTGEN repository, in `/home/claude/quantgen_macro_data/` (`CATALOG.md`, `scripts/`, `results/`). Golden-value fixtures are generated once, at M1's exit, by QUANTGEN's own data layer from the frozen reference files (values unchanged; provenance fields and `value_status` added) and md5-frozen; every later milestone reads that generation, and a regeneration before the M7 freeze must reproduce the same md5s or is a fixture change logged in the manifest with the tests it re-baselines; the fixture manifest (§9.5) maps every file to the tests that read it.

**Terms used before their definition.** CARD-O / CARD-P: model cards with an outperformance / protective claim (§8.2). S: the static comparator at the overlay's average exposure (§8.7). Books: recommended (the only displayed one), specification, FORWARD-SIM and refusal books (§8.1.2); every book has its own runtime state (§3.8). BUILD-AS-INSURANCE: a build status on a CARD-P PASS, never a verdict (§8.1.2). PC-1′: the tail-loss legs of CARD-P v2 (R-21). N_eff: the step-3 trial count (R-23). UNDERPOWERED: R-24's reason code. Stack card: the CARD-P that gates two or more de-risk factors acting together (R-02, §8.7). "P0–P2" in a module row is a council priority; "P0–P19" are the §1 principles; council red lines are written "red line P1/E1/Q1" (§13).

**Build order (council order M0 → M10).**

| Milestone | Modules (`QC_modules.csv`) | Read | Exit tests (§9) |
|---|---|---|---|
| **M0** Scaffolding | R-26 instrument book, notional and cost fields; R-32 schemas v2; R-33 DO-NOT-BUILD v2 (rules-store validation, rule objects §7.1); the R-02 bounds | §1, §3.1–3.5, the §5 preamble (build statuses, rule kinds), §6, §7 (with §7.1), §8.1.2, §8.2, §8.4, §10, R-26, R-32, R-33 | T-RO-01, T-HERM-01/02, T-SCHEMA-01/02/03, T-CAP-01, T-BASIS-01, T-REPRO-01a, T-COST-02/03, T-BOOK-01 (header clauses), T-DNB-01, T-OWNER-01 |
| **M1** Data layer | **First task, run in parallel:** start the KIS quote-field check (QF1-A25; below). Then R-01 point-in-time store, R-19 data contracts and staleness, R-20 effective-dated calendars | §3.8 (book ids, runtime states, the OPS class), §4, R-01, R-19, R-20 | T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01/02, T-AVAIL-01, T-STALE-01, T-ROLE-01/02, T-LAG-01/02, T-SYN-01, T-TZ-01/02, T-MISS-01/02, T-SER-01/02, T-PRINT-01, T-H10-01/02, T-H15-01, T-VIX-01, T-SAT-01, T-REGIME-01, T-XMKT-01, T-CAL-01/02, T-RO-02, G-POST-01 (data rows; §9.0b) |
| **M2** Risk layer | R-02 composition by `min()`; R-09 hedge state; the `market_vol_target` function of R-06 (its card runs in M7) | §3.3, R-02, R-06 (formula, labels), R-09 | T-CAP-02 (its stack-card clause runs from M7), T-VT-01, T-CORR-01, T-HEDGE-01, T-COST-01, T-LABEL-01, I-02; G-KR-01..04, G-KR-02b/02c, G-US-01/01b/01c; G-KR-06 (reference mode, once §9.4 item 2's rerun is md5-frozen) |
| **M3** Estimator harness | R-30 estimator selection gate and forecast-evaluation harness | R-06 (estimator row), R-16(2), R-30 | T-B5-01, I-10, T-EST-01/02/04 (their Stage-3, bootstrap-CI and counted-revision clauses run from M7); G-B5-01..04, G-EST-01..04 |
| **M4** Factor sleeves | R-03 (the sleeve-scale function; its formal card runs in M7), R-04 (specification book only), R-05 (unchanged), R-15 | §3.3, §3.7, R-03, R-04, R-05, R-15 | T-R03-01 (sleeve-scale and years clauses), T-PRIOR-01; G-MOM-01..06, G-MOM-08, G-INTL-01, G-BOOK-01; G-MOM-07 (reference mode) |
| **M5** Engine and events | R-07 caps and hard stop, R-08 annotation, R-10 events, R-27 simulated fill model | §3.8, §6.3, R-07, R-08, R-10, R-27 | I-04, I-04b, I-06, I-06b, I-06c, T-CAPS-01, T-ANNOT-01, T-FILL-01..03, T-BAR-01 (R-27 clause), T-HALT-01, T-STEP-05, T-BOOK-03, T-MONO-01; G-LAD-01..03 (reference mode, §9.3.3) |
| **M6** Context and breaks | R-13 context log, R-18 policy and scale breaks | §3.6, §6.4, R-13, R-18 | T-CTX-01/02, T-BREAK-01 |
| **M7** Cards | **The gate package R-21, R-22, R-23, R-24 and R-34 is built and frozen first** (below). Then the formal headers of R-06 KR, R-03 (with its two revisions), R-14, R-31, R-28 and R-29 are committed blind, and R-06 KR, R-03, R-14 and R-31 run. R-28 and R-29 start their FORWARD-SIM books in M8 from the headers committed here | §8 (all), R-03, R-06, R-14, R-21–R-24, R-31, R-34 | The harness tests of §8.1.3 step 1 (T-DSR-01/02, T-NEFF-01, T-STEP3-01/02, T-SEL-01, T-LEDGER-01, T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01, T-EXCESS-01, T-BAND-01, T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01, T-PLACEBO-01/02, T-GATE-04) and I-05; then I-08 (gate acceptance; T-GATE-01/03) and the freeze; then I-09, I-07, I-15, I-16, T-GATE-02, T-EPIS-02, T-TROUGH-01, T-ES-02, T-RLAYER-01, T-R03-01, T-R04-01, T-R14-01, T-R06-US-01, T-CARD-01/02, T-REPRO-01b, T-BOOK-02, T-STEP-01..04 and every clause deferred to M7 (§9.0a); G-KR-L*, G-US-F*, G-PWR-*, G-DSR-01/02 |
| **M8** Forward records and workflow | R-25 forward monitoring; R-28 trend card and R-29 US futures card (FORWARD-SIM); R-11 and R-12 retirement; R-35 workflow | §3.8, §3.9, §8.8, R-11, R-12, R-25, R-28, R-29, R-35 | I-01, I-03, I-12, I-13, I-14, T-REF-01/02, T-REPLAY-01, T-SCOPE-01, T-OBS-01..05, T-CARD-03, T-BASIS-01 (S2 clause); G-KR-05/05s, G-TR-*, G-REF-* |
| **M9** Quant Lab | R-16 | R-16 | I-11: out-of-sample 99% VaR, ES 97.5% and fan PIT on 2016–26 against the thresholds of §12 M9 (the 2026-only lines are reported, not gated; QCE-146); T-REPRO-01c |
| **M10** Deferred | R-17 crypto clock and FX instrument (when those sleeves exist) | R-17 | T-CRYPTO-01, T-FX-01 |

**What to build first.**
- **M0** lays the fields every later module needs: the cost table reference with the tick floor, the instrument-book, notional and rebalance fields (R-26), the v2 schemas (R-32) and the DO-NOT-BUILD checks in rules-store validation (R-33).
- **M1 starts the KIS quote-field check and runs it in parallel:** pull KIS bid/ask for 069500 and 005930 at 15:19:59 KST on 20 sessions; confirm the level-1 fields, exchange vs receipt timestamps, the market-division code and price field that return the KRX regular-session official close (not an NXT or integrated print), and whether the app key can trade (QF1-A25; backlog BL-C02, BL-D03; R-01, T-RO-02). It needs the owner's KIS credentials and about 20 live sessions. It gates only code that reads KIS bid/ask or quote timestamps (R-27 snapshots, R-08 spread snapshots, the R-26 stress-line calibration), not the rest of M1 or M1's exit; without KIS access it is recorded as "not run" and those features stay labelled UNVERIFIED. Meanwhile build the point-in-time store with `value_status`, schedule-aware staleness by role and the effective-dated calendars. Nothing downstream may run on a store without them (P16, P18).

**The gate package is frozen before any formal card run (P11).**
1. Build R-21 (CARD-P gate v2), R-22 (evaluation conventions), R-23 (family trial ledger and N_eff), R-24 (statistics and power harness) and R-34 (timing-fragility gate).
2. Run the gate-acceptance test (I-08; T-GATE-01..04 in R-21): at most 10% of 300 circular-shift placebos per family pass PC-1′, at most 2 of 20 per card pass PC-1′, and every named negative control (US VT 5-day and 10-day at 50 bp; post-shock-day and post-shock-week 0.5×; stale VT with σ lag 252) comes out REJECT or INSUFFICIENT DATA. Every attempt is logged and counts in the package-level ledger (R-21 9(e)). A failed test freezes nothing and blocks every card run; the package may be redesigned once, on the per-family panels and the negative controls only, with fresh seeds fixed before the re-run, and after a second failure, counted across all 2.x versions, no card can be evaluated under v2 (R-21 9(a); R2-C3; T-GATE-04).
3. If a control passes, add a null-calibrated CDaR95 guard **before** any card runs. Its calibration is owner decision D6 (below), whose default rule is written into the package before any control or card runs, so it is never chosen after seeing which control passed or any card's numbers (R2-C2). The fixed −5 pp margin is withdrawn.
4. md5-freeze the results with the package version (`gate.package`, §7; §8.1.3). Only then commit the formal headers and run R-06 KR, R-03, R-14, R-31 or any other formal card.
5. Nothing in the package changes after a card result has been seen. A change is a new package version, re-run on every card, with the flips disclosed.

**The Korea card (R-06 KR), stated plainly (R2-C1).** On current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build: f takes the maximum over the defensible row-set readings, every reading that includes the DL-A seed of §9.5 gives f above 1.282 (indicative f 1.26 on R4's three rows alone, 1.49 with the DL-A grid, 2.87 family-wide), and PC-3 needs p_ni × f ≤ 0.10 at the indicative p_ni 0.078. The status stays BUILD-AS-INSURANCE on a formal PASS (Resolution 1), and no convention may be changed to rescue it (R2-C1; §8.9).

**What never to build** (full list in §10, enforced by rules-store validation, R-33):
- any order, cancel, withdrawal, deposit-address or transfer path (P0; item 21);
- any multiplier or vol-target cap above 1.0 (cap 1.0 is permanent; item 2);
- a product-composed de-risk stack (composition is `min()`; item 31);
- a regime-model state, acting or displayed (jump model, Markov switching, GMM label, change-point "regime"; item 27);
- `max(SMA20, implied)` sizing, ML vol-state classifiers, a maintained ML challenger pipeline, Mondrian conformal labels (items 30, 11, 29, 28);
- a stock book as a market-gross scalar, or a venue switch after results (items 33, 32, 23);
- R-11 or R-12 in any book other than a display-only refusal book; R-04 in the recommended book; any FORWARD-SIM multiplier in the recommended book (item 22);
- the Kish trial count; a forward record presented as validation (items 36, 35).

**Owner decisions: implement the stated default and flag it.** The council routed five decisions to the owner (QC resolutions §d); D6, the CDaR-guard calibration, has a default frozen with the gate package and is applied only if a negative control passes. **This table is the canonical statement of D1–D6 and their defaults; §7, §8.10, §11 and the backlog refer to it and do not restate values.** Implement the default now. Each decision has one canonical rules-store key, written as a plain scalar. The machine-readable registry is `owner_decisions.D<n> = {key, value, default, options, status, effective_from, rationale, refs}` in §7 (the JSON store has no comments, so no marker lives in a comment). Where a rule's config block needs the value (D2 in R-31; D5 in R-26, R-28 and R-29), it holds a reference `{ref: <canonical key>}` resolved at load, never a literal copy; a literal copy that differs is refused (T-OWNER-01), and a `{ref: <key>}` object has exactly one key (any other shape is refused at load). The Macro page lists every open owner decision. An owner ruling is a logged governance event (§8.10): it is not an edit of an acting parameter outside a revision, so it never demotes a card; a card whose header depends on the key (D2 for R-31) gets a new counted revision before its next run.

| ID | Decision | Default implemented in v2.0 | Rules-store key |
|---|---|---|---|
| D1 | Korea concentration template (risk appetite) | **MSCI 25/50**: single name ≤ 22.5% after the buffer; names above 4.5% ≤ 45% in aggregate; checked quarterly and on breach. Options: (a) domestic max(10%, market weight); (c) a 35% pair cap without the 0.45 trigger | `risk_layer.korea_caps.template` |
| D2 | Drawdown hard-stop level (risk appetite) | **−15% of book NAV** from the high-water mark since the last re-arm. Option (b): −1.5 σ_book | `risk_layer.drawdown.hard_stop.level` |
| D3 | Calm-state reversal down-weight, QF5-M10 (principle change) | **Not adopted: P3 stands** (council recommendation). Reopen only after the KRX net test in 2010–17 and 2018–26 | `families.reversal.calm_state_downweight` |
| D4 | Book-level false-demotion budget (risk appetite) | **≤ 10% a year** across all statistical demotion triggers, split equally across active cards, each split verified on a 20-shift placebo panel | `monitoring.false_demotion_budget_per_year` |
| D5 | Whether, and on which line, to run a US sleeve (product choice) | **No US sleeve until decided**: R-28 and R-29 stay FORWARD-SIM and never enter the recommended book. Options: index futures (Micro ES, notional ≈ ₩1bn or more); a KRX-listed S&P ETF line with FX and NAV lag modelled; no US sleeve. Scope: D5 governs the US market-gross line (R-06 US, R-28, R-29); QUANTGEN's existing factor sleeves on US shares (R-03's momentum sleeve) are not a US sleeve in D5's sense | `sleeves.US.line` |
| D6 | CDaR-guard calibration (applied only if a negative control passes the acceptance test; Resolution 4's one open sub-point) | **Frozen with the package now (R2-C2): the lowest-placebo-false-pass rule.** If a negative control passes, the guard is calibrated by the one of the three council candidates (the Professors' bootstrap test at one-sided 5%, the Executives' placebo-10th-percentile margin, QF's blind margin) with the lowest per-family placebo false-pass rate among those that bring every negative control to REJECT or INSUFFICIENT DATA; ties go to the Professors' test (default, judgment; placebo results only, never a card's numbers). If no candidate does, the attempt fails (R-21 9(a)). An owner ruling naming one candidate is accepted only before the first acceptance attempt; any later change is a new package version and a counted trial | `gate.acceptance_test.cdar_guard.calibration` |

**Owner actions the build needs (inputs, not decisions with a default).** (1) M1: sign the calendar files in `core/calendars/data/` (T-CAL-01), with the KRX facts the spec cannot give: the pre-2015-06-15 conditional random-end extensions, Saturday-session close times before 1998-12-12, the lunch-break dates, the pre-2016 CSAT session window and the ETF tick table; sign the 2027 calendars before 2026-11-01 (T-CAL-02). (2) M1: KIS credentials for the quote-field check. (3) Before the M7 header commit: each sleeve's notional, `sleeves.<market>.notional_nav` (R-26), and the ECOS code of `BOK_CALL_RATE` and its observation calendar (§4.2). (4) Optional, and only before the first acceptance attempt: a D6 ruling naming one candidate (otherwise its default rule stands).

**Invariants to check in every pull request:**
- No order, cancel, withdrawal, deposit-address or transfer path; KIS is read-only (P0, T-RO-01).
- No multiplier or weight above 1.0. Overlays lie in [0.5, 1.0]; vt and vs lie in [0, 1.0]. Composition is composed(m) = vt × min(1.0, overlay₁, …, overlayₖ, ladder, post_rearm_cap), never a product; outside HALTED, composed(m) ≥ 0.5 × vt (P2, T-CAP-01, T-CAP-02). The concentration bound and the risk-layer caps act after this and may take gross lower; the floor assertion is on composed(m), never on gross or final weights.
- Every acting input is read through `pit_value` with `available_at_utc ≤ decision_utc`. A close-type acting input needs `value_status = official_close` for the decided session. No synthetic, provisional, bar-derived or stale acting input (P5, P18, T-PROV-01).
- HALTED is scoped per book (§3.8). Among data inputs, only an `acting_exposure` input bound to a book can HALT that book; an input bound only to the specification, FORWARD-SIM or refusal books fails that book closed and never HALTs the recommended book. A stale or failing `risk_model` input, or an exception inside `hedge_state`, sets `hedge_credit_off = TRUE` and never HALTs (P16, P18, T-ROLE-01, T-SCOPE-01). The other triggers (hard stop, risk-limit breach, lag audit, schema or bounds, heartbeat) are listed in §3.8 with their class (RISK or OPS) and scope.
- Only PASS cards feed the recommended (displayed) book, as a recommendation (CARD-O) or as insurance (CARD-P, BUILD-AS-INSURANCE). Specification-only factors (R-04; R-31 steps whose binding share exceeds 0.10), FORWARD-SIM cards (R-28, R-29) and refusal books (R-11, R-12) never do (P7, I-03). R-31 steps with a binding share ≤ 0.10 act in the recommended book as part of the R-07 invariant (Resolution 6), with disposition `INVARIANT_STEP`.
- Every artifact and card validates against its §6 schema; a field a rule writes is declared in that schema (T-SCHEMA-03).
- Costs are read from the gate's table with the tick floor applied, never lowered, and every result also runs at 2×. Every card header declares its instrument book, notional NAV, rebalance rule and no-trade band (P10, P15, T-COST-02/03, T-BOOK-01).
- The gate package is frozen before any formal card run (P11, I-08).
- Macro tests are hermetic and read frozen post-close fixtures only (T-HERM-01, T-FIX-01).

**Binding vs informative.** Field names, parameters, bounds, formulas, test thresholds and the council's final wording quoted in §5 are binding. Paths and function names marked **proposed** may be renamed to fit the codebase. Evidence numbers are informative, except where a §9 test or a §9.3 golden value cites them. Where this file is silent, take the conservative reading: no exposure change, specification book only, fail closed.

**The four v1.2 open points are answered** (QCE-001):
- **Ladder composition:** non-cumulative steps, one risk-layer function composed with the overlays by `min()`, an explicit re-arm, steps time-boxed at 21 sessions (R-02, R-07, R-31). Only the hard-stop level is open (D2).
- **Staleness of weekly or slow inputs:** schedule-aware staleness with failure actions by role; risk-model inputs never HALT (§4.1, R-19).
- **Korea caps on an ETF line:** caps apply on look-through; 0.05 becomes an active single-name cap against the capped benchmark; the aggregate template is the owner's (R-07, D1).
- **Priors → base weights:** the 0–3 integers are admissibility filters; base_weight(m, f) = IV_m × 1/K_m over admissible families (R-15).

**Still open, and why nothing in v2 waits for them.**
- CONTESTED, with settling tests in the backlog; nothing in v2 either way: the jump-model regime engine (QF7-M1), the Korean cross-asset futures sleeve (QF5-M8) and GMM scenario regimes (QF5-M9).
- One sub-point of the CARD-P gate: how a CDaR guard would be calibrated. It matters only if a negative control passes the acceptance test (step 3 above); owner decision D6's default rule is frozen with the package before any control runs (R2-C2).

---

## Changelog: v2.0 adversarial review (round 4)

Round 4 was a confirmation: the risk officer re-checked the three round-3 majors, found no regressions and agreed, so all four reviewers stand at AGREE (`council/ASPEC_R4_risk_officer.md`; `council/ASPEC_DEBATE_SUMMARY.md`). The coordinator applied his two clarifying notes; notes 3 and 4 restate §9.4 items 15–17 and §8.9, so they needed no edit. No council decision is reversed.
- **Note 1, commit timing.** A header registered after the freeze ends at the last month-end official close before its commit, a rule-fixed end (R-22).
- **Note 2, FORWARD-SIM NAV failures.** A FORWARD-SIM book never HALTs on a NAV-input failure: the decision is marked failed-closed, printed and counted toward §8.8 (b)'s 10% budget (§3.8).

## Changelog: v2.0 adversarial review (round 3)

**Why.** Round 3 is the convergence check (round 4, above, confirmed it). The QA engineer, the data engineer and the junior developer agree. The risk officer found three majors, all gaming routes left by the round-2 remedies, and no blockers; the coordinator accepted his patches and the listed non-blocking notes (`council/ASPEC_R3_*.md`; rulings in `council/ASPEC_R3_claude_critique.md`). `council/ASPEC_R3_synthesis.md` lists every item and its decision. No council decision is reversed: book-scoped HALT, R-06 KR's status and its expected outcome (R2-C1) stand.

**What changed.**
- **An operator kill cannot blind the forward alarm (R3-1).** A kill of a card's forward books is an operational integrity trigger, and every HALTED or DISARMED decision of those books counts toward §8.8 (b)'s 10% budget; the gap is still excluded from both sides of the comparison, and book scope is unchanged (§3.8, §8.8, R-25, T-DEMOTE-04).
- **Every try is a row (R3-2).** A ledger row is a distinct `config_id`: the rule and every parameter (signal, threshold, target, lookback, multiplier and lag included), plus estimator, window, cap, book, rebalance rule, timing class and start convention (R-23, `gate.step3.row_set.key`, T-SEL-01 (h)).
- **The data cut-off is fixed now (R3-3).** `gate.evaluation.data_cutoff` is KR 2026-10-02 and US 2026-10-01, the last official closes in the frozen reference data and the span of the council's definitive cell; later data enters only through the §8.8 re-gate (R-22, §8.4).
- **Also:**
  - where f changes between the acceptance report and a card run, the larger binds and both are printed (T-SEL-01 (e));
  - redesign failures count across all 2.x versions, and T-GATE-04 tests the bounded-redesign path;
  - a breach's limit is met when the post-action target weights satisfy it, and the post-re-arm cap starts at the actual re-arm decision;
  - each book's NAV price inputs are bound (`NAV_LINE_CLOSES`);
  - `consumer` is the binding's consumer key;
  - the warm-up of `market_vol_target` and `sleeve_vol_scale` is mapped per book;
  - the `vol` display labels are display fields, and the top-level `halt` fields restate `causes[0]`;
  - the covariance carry is stated everywhere, the ECOS calendar is declared, and a replay restores the prior runtime state;
  - I-08 prints p_ni; a typo and a misplaced YAML comment are fixed.
- **Open implementation tasks** (§9.4 items 15–17): anchored timestamps for the f = 1 route, an archived snapshot per formal card, and atomic `engine_feed` delivery per book.

## Changelog: v2.0 adversarial review (round 2)

**Why.** Round 2 found no blockers. The four opponent reviews (`council/ASPEC_R2_*.md`: 19 major and 46 minor issues, 178 patch rows) and the coordinator's binding rulings R2-C1 to R2-C7 (`council/ASPEC_R2_claude_critique.md`) found result-aware choices left in the M7 freeze, runtime paths that failed open, binding tests that a correct implementation would fail, and a cash leg that could not be built. `council/ASPEC_R2_synthesis.md` lists every issue, its sources and its decision. No council decision is reversed; book-scoped HALT stays as ruled in round 1.

**What changed.**
- **The Korea card, stated plainly (R2-C1).** Ledger rows are the distinct configurations seen before the freeze, enumerated in the §9.5 seed (R-23, T-SEL-01). On current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build: f takes the maximum over the defensible row-set readings, every reading that includes the DL-A seed of §9.5 gives f above 1.282 (indicative f 1.26 on R4's three rows alone, 1.49 with the DL-A grid, 2.87 family-wide), and PC-3 needs p_ni × f ≤ 0.10 at the indicative p_ni 0.078. The status stays BUILD-AS-INSURANCE on a formal PASS (Resolution 1), and no convention may be changed to rescue it (R2-C1; §8.9).
- **D6 frozen now (R2-C2).** Its default, the lowest-placebo-false-pass rule over the three council candidates (placebo results only), is written into the package before any control or card runs; an owner ruling is accepted only before the first acceptance attempt, and a later change is a new package version and a counted trial (Quick start, R-21 9(d), §7).
- **Bounded redesign (R2-C3).** A failed acceptance test may be redesigned once per package version, on frozen-items-table items only, justified on the per-family panels and negative controls, with fresh seeds fixed before the re-run; after a second failure no card is evaluated under v2 and the owner is notified. Every attempt counts in the package-level ledger and is printed beside later verdicts (R-21 9(a), 9(e)).
- **Authenticated verdicts, append-only forward records, no fail-open paths (R2-C4).** `cards/verdicts.jsonl` is hash-chained and `verdict_filter` checks the results md5, the frozen package md5, a reproducible snapshot and the harness commit (T-CARD-03). Forward records are append-only, with the age counted from first registration. Bindings follow admission. An errored acting step fails the books it serves closed and pages (T-OBS-04/05). A breach re-arms only once its limit is met, and references reset only after the hard stop. A HALT keeps every cause (`halt.causes[]`). Warm-up applies only before a book's first ARMED decision. Field classes are exhaustive, and an unclassified field is acting. A failed covariance input is carried, labelled, before it is dropped.
- **The cash leg (R2-C5).** c_t follows the series' unit: an annual rate (`BOK_CALL_RATE`, DTB3) accrues act/365 from the latest rate dated on or before the previous session, and French RF is a per-period return used as published. The series is read from the card's frozen snapshot, and a missing cash day is defined on the series' own calendar (R-22 rule 3, T-EXCESS-01).
- **Build order (R2-C6).** §9.0b gives clause-level `runs_from`. M1 builds a minimal per-book runtime (OPS), so its HALT tests run there. The builders stay in M6, and earlier tests assert function outputs (§12).
- **Tests and clocks (R2-C7).** One quarantine anchor, `close_print_bound_utc` + 10 minutes, with a T-CLOSE-01 boundary case. CSAT-day cross-market cases, and close-print bounds for JP, CN, HK and TW. Research-script statistics become tolerance-checked reproductions of named fixtures (v1.2-check or reference mode); the frozen-package values are computed and md5-frozen at their first run (§9.4). T-PBO-01 follows QF3's recipe.
- **Also:**
  - a data cut-off shared by the drafts, panels and headers;
  - council questions on frozen items answered before the first attempt;
  - panels for a CARD-P registered after the freeze;
  - the KOSPI close bound to the specification book until R-06 KR passes;
  - `nav_fx` bindings;
  - an append-only fetch log;
  - close-type row selection;
  - channel-specific VIX timing;
  - one artifact per decision;
  - the `governance_event` record (§6.6);
  - closed result containers;
  - formal card ids;
  - aligned exit lists.

**Not adopted (`council/ASPEC_R2_synthesis.md`):**
- removing G-LAD-02/03 from M5's exits (round 1 made them reference-mode exits; the other lists were aligned instead);
- leaving D6 without a default (superseded by R2-C2);
- coupling every HALT of a card's on, off and S books (book scope stays; gaps are excluded from both sides of the comparison instead);
- treating an unmarked field as display (an unclassified field is acting, R2-C4);
- a narrower row set for f as an open council question (the maximum over the readings binds).

## Changelog: v2.0 adversarial review (round 1)

**Why.** Four opponent reviews (QA engineer, data engineer, junior developer, risk officer; `council/ASPEC_R1_*.md`) and the coordinator's binding rules C-1 to C-9 (`council/ASPEC_R1_claude_critique.md`) found that v2.0 could not be built as written: HALT had no book scope; the §6 schemas rejected fields the rules write; the gate package left the card-book convention and the selection factor to the author; milestone exit tests depended on later milestones; and R-34's positive control needed look-ahead that four binding rules forbid. `council/ASPEC_R1_synthesis.md` lists every issue, its sources and its decision. No council decision is reversed, and every new number comes from the review or research files (new defaults are marked "default, judgment").

**What changed.**
- **HALT is per book (C-1).** RISK and OPS classes, scoped to the books whose own NAV, artifact or bound acting input failed; risk-model inputs, `hedge_state` exceptions, context artifacts and display-field schema failures never HALT; the RISK re-arm is automatic and idempotent; `gap_sessions = 0` is valid (§3.8, R-19, R-32; T-SCOPE-01, T-HALT-01, I-06c).
- **Card books and the selection factor (C-2).** Card books exclude the R-07 hard stop and caps, which the stack card judges on the composed recommended book (R-22 rule 6; VT20 MDD −45.3% without, −56.4% with). f is computed from the family ledger under `any_overlap`, never declared (R-23, T-SEL-01). §8.9 shows that any f > 1.28 turns R-06 KR's PC-3 into INSUFFICIENT DATA; the card is never passed by convention.
- **`runs_from` (C-3).** Every test runs from the first milestone at which its modules exist (§9.0a); R-03's formal card runs in M7, after the freeze.
- **The `timing_probe` sandbox (C-4)** holds R-34's look-ahead rows, tagged `synthetic_lookahead`, with one-line exceptions in P5, R-01, §3.5 and T-LAG-01/02 (T-PLACEBO-02).
- **Clocks and staleness (C-5, C-6).** Effective-dated KRX close-print bounds (06:00:30Z for 2015-06-15 … 2016-07-29, 06:30:30Z after, the close + 30 s tolerance before), a NYSE bound of 16:00 ET + 30 s, CRYPTO at d+1; every staleness statement keys on the next-due instant.
- **Schemas are the contract (C-7).** §6 rebuilt: the common provenance fields, `runtime[]`, structured alerts, the event-calendar envelope, a header schema and a card schema closed by `unevaluatedProperties`, one registry keyed by `$id`; every example validates (T-SCHEMA-01/03).
- **Owner decisions (C-8).** The Quick start table is canonical; §7 holds a machine-readable registry and rule blocks reference it (T-OWNER-01); D6 (the CDaR-guard calibration) exists only if a negative control passes.
- **Reference data (C-9)** is named in the Quick start; a fixture manifest, ledger seeds and an acquisition register are added (§9.5).
- **Also:** bitemporal reads with a pinned `knowledge_utc`; value-status assignment and per-consumer registry bindings; the frozen PC-6 axes, start-band shapes and integer stability floor; open episodes; the ledger hash chain; forward-record integrity; the binding-share rule and `INVARIANT_STEP`; the §7.1 rule-object schema; test tiers, tolerances, reference mode and v1.2-check mode (§9.3.3).

**Not adopted, or routed to the owner or council (§8.10):** a card-local placebo cap (council question Q5); a fallback timing-fragility statistic for Sharpe-neutral cards; a rule-based primary out-of-sample line; counting `INVARIANT_STEP` steps as de-risk factors on the stack card; lifting R-18 spells only at their end; a new trial-ledger vocabulary; a decision-scoped snapshot id; renaming the red lines.

## Changelog v1.2 → v2.0 (Quant Council)

**Why.** The Quant Council (round QC, 2 Oct 2026, after the 17:20 KST data patch) ruled on the QF audits and proposals, four cross-examinations and two data labs. Its ledger holds 361 items; of the 265 ruled or consent items (claims aside), 213 were accepted for action. The data labs found that v1.2:
- could freeze itself: its staleness defaults mark H.10 inputs stale at 100% of decisions, and its literal −15% ladder step never re-arms (the KOSPI book stays HALTED from 1997-10, 714 halt cycles; DL-A);
- admitted a provisional intraday row as the 2-Oct close (6,943.66 against the official 7,003.74);
- gated protective cards on single-path ΔMDD, whose bootstrap SD is 7.4–7.8 pp against a 3 pp threshold;
- counted trials with a mis-cited formula (the Kish form, not Bailey–López de Prado's eq. 9).

They also found that the Korea vol target is decidable on long KRX history now, without waiting for forward months.

**How.**
- The 125 SPEC REPLACE rows of `QC_errata.csv` were machine-applied before this rewrite (pristine v1.2: `.v1.2_INTEGRATION_backup.md`).
- The 44 SPEC-REWRITE rows are absorbed in the sections they name. The eight §8 rows (QCE-102, 103, 105, 106, 108, 109, 111, 113) are absorbed by the replacement §8.
- Every module of `QC_modules.csv` is below, one line each: change type, class, priority, milestone, then its source items.
- **R-05 is the only rule the council left unchanged.**

**Modules.**
- **R-01** CHANGED · INVARIANT · P0 · M1. Point-in-time discipline: `value_status`, `session_date`, `retrieved_at_utc`, provisional-row guard, post-close fixtures. *QF2-M1, QF2-M4, QF2-A2, QF1-A3, QF2-A1, QF4-A12, QF6-A12, QF6-M11, QF1-A24, QF2-A23.*
- **R-02** CHANGED · INVARIANT · P0 · M2. Overlay bounds and composition by `min()`; recommended-book stack card. *X-EX1-N2, QF4-A6, QF4-M3.*
- **R-03** CHANGED · CARD-O · P0 · M4. Momentum own-vol scaling: indicative-PASS relabel, scale-free target revision, variance-scaled trial. *QF3-A2, QF5-M1, X-PX2-N3, QF5-A4, QF5-A5, QF5-A6, X-PX2-N4, QF3-A14, QF6-A23.*
- **R-04** DEMOTED · CARD-O · P1 · M4. Daniel–Moskowitz gate: specification book only, A-provisional route closed. *QF3-A18, QF5-M6, QF5-A1, QF5-A2, QF5-A3, QF5-A16.*
- **R-06** CHANGED · CARD-P · P0 · M7. Per-market vol target: Korea formal card (BUILD-AS-INSURANCE on PASS); US 50 bp card relabelled; cap 1.0 permanent; dual labels. *QF4-M1, QF4-A1, QF1-A2, QF6-A7, QF6-M4, QF7-M5, QF7-A21, QF3-A6, QF5-A24, X-EX1-N5, X-PX2-N2, X-PX2-N5, QF1-A1, QF3-A4, QF4-A2, QF5-A23, QF6-A18, QF6-M8, QF6-A13, QF6-A15.*
- **R-07** CHANGED · INVARIANT · P0 · M5. Korea caps on look-through with an active single-name cap; drawdown hard stop with explicit re-arm. *QF4-M3, QF4-A5, QF4-A6, QF4-M4, QF4-A9, QF4-A10, X-EX2-N5, QF6-M9.*
- **R-08** DEMOTED · CONVENTION · P1 · M5. VIX ≥ VIX3M flag demoted to an execution-state annotation with a stated clearing rule. *QF6-M7, QF6-A9, QF6-A10.*
- **R-09** CHANGED · INVARIANT · P1 · M2. Hedge-validity state: date-aligned corr63, never-HALT risk-model inputs, display-only `fx_hedge_credit`. *QF2-A5, X-EX1-N6, X-EX2-N6, QF5-M7, QF4-M7.*
- **R-10** CHANGED · CONVENTION · P1 · M5. Event calendar: multi-session gap tags, √n VaR display scaling, BoK decision and press conference as separate events. *X-EX2-N2, QF2-A14, QF7-A28, QF1-A14.*
- **R-11** RETIRED · CARD-P · P1 · M8. USD/KRW leg (S1) retired from FORWARD-SIM; REJECT recorded; labelled refusal book only. *QF2-A8, QF2-M8, QF4-A3, QF2-A24, X-EX2-N4.*
- **R-12** RETIRED · CARD-P · P1 · M8. US rates-stress leg (S2) retired from FORWARD-SIM; REJECT recorded at every timing. *QF2-A7, QF2-M7, QF3-A24, QF4-A18.*
- **R-13** CHANGED · CONTEXT · P1 · M6. Context log: vintages and first prints, leverage/flow, VRP, live implied-vol snapshots, turbulence. *QF2-M6, QF7-A24, QF1-M5, QF4-M8, QF6-M6, QF6-M10, QF5-M7, QF2-A20, QF4-A23.*
- **R-14** CHANGED · CARD-O · P2 · M7. TS-trend sleeve: declared instrument book and diversification claim at cap 1. *QF5-A26, QF5-A11, QF5-A9, QF5-A8.*
- **R-15** CHANGED · CONVENTION · P0 · M4. Priors as admissibility filters; equal risk budgets over admissible families; inverse-vol across markets. *QF5-M4, QF4-A15, QF4-M5, QF5-A14.*
- **R-16** CHANGED · CONTEXT · P1 · M9. Quant Lab: expanding-window fits, FHS/EVT envelope, replay library with regime metadata, range-HAR admitted. *QF6-M3, QF6-A5, QF6-A20, QF4-M9, QF6-A14, QF6-M8, QF7-A23, X-PX1-N4, X-EX2-N2, QF6-A3, QF3-A23.*
- **R-17** CHANGED · CONVENTION · P2 · M10. Planned sleeves: crypto 24/7 clock and declared FX instrument. *QF2-M9, QF2-A22, QF1-A18, QF5-A19, QF5-A20.*
- **R-18** CHANGED · GOVERNANCE · P2 · M6. Policy and scale breaks: official-framework trigger now; statistical and BOCPD flags logged only; market-structure break log. *QF7-M6, QF7-A19, QF7-A18, QF7-M4, X-PX2-N6.*
- **R-19** NEW · INVARIANT · P0 · M1. Data contracts: schedule-aware staleness with role-based failure actions. *QF2-A3, QF2-M3, QF4-M7, QF4-A11, QF2-A4, QF2-A6, QF2-A10, QF2-A21.*
- **R-20** NEW · INVARIANT · P0 · M1. Effective-dated market calendars and regime tags (KRX, NYSE, Fed, SIFMA). *QF2-A12, QF2-M5, X-EX2-N1, X-PX2-N6, QF1-A4, QF2-A11.*
- **R-21** NEW · GOVERNANCE · P0 · M7 (frozen before the first card run). CARD-P gate v2: PC-1′ tail legs, PC-2 with CI, binding PC-3, do-no-harm cap, gate-acceptance test. *QF3-A5, QF3-M3, X-PX1-N2, X-PX1-N3, X-EX1-N4, QF5-A12, QF5-M5, X-PX2-N1, QF4-A22.*
- **R-22** NEW · GOVERNANCE · P0 · M7 (frozen before the first card run). Evaluation conventions: objective market-own episodes, excess returns, declared start band, regime lines, post-trough window. *QF4-M6, QF4-A8, QF7-A20, X-PX2-N5, X-EX2-N1, QF5-A24.*
- **R-23** NEW · GOVERNANCE · P0 · M7 (frozen before the first card run). Step 3: family trial ledger and N_eff = max(N_clusters, N_equiv). *QF3-A1, QF3-M1, X-EX1-N1, X-PX1-N1, QF3-A20, QF3-C1, QF3-A1b.*
- **R-24** NEW · GOVERNANCE · P0 · M7. Statistics and power harness: studentized bootstrap, SE ladder, power/MDE line, PBO on the card claim, Lo-adjusted Sharpe. *QF3-M2, QF3-A19, QF3-M7, QF3-M8, QF3-A8, QF3-A9, QF3-A10, QF3-A11, QF3-A21, QF3-A3, QF4-A7.*
- **R-25** NEW · GOVERNANCE · P0 · M8. Forward-record monitoring and demotion v2: whole-book NAV, calibrated alarms, operational triggers. *QF3-A7, QF3-M5, QF5-A7, QF5-M3, X-EX1-N3, QF3-A6.*
- **R-26** NEW · INVARIANT · P0 · M0. Instrument book, notional and cost realism: tick floor, granularity floor, header fields, execution variants. *QF1-M1, QF1-M3, QF1-A6, QF1-A7, QF1-A16, QF1-A17, X-EX2-N3, QF4-M2, QF4-A14, QF6-M9, QF6-A21, QF1-M4, QF1-A9, QF1-M2, QF6-M5.*
- **R-27** NEW · CONVENTION · P2 · M5. KRX/NYSE simulated fill model: close-auction fill, random end, limit-lock, LP-exempt iNAV check, bar convention. *QF1-M6, QF1-A8, QF1-A14, X-EX2-N5, QF2-A23.*
- **R-28** NEW · CARD-P · P1 · M8. Trend-axis protective card (US and non-Korean sleeves): monthly SMA10m, 0.5× below trend, FORWARD-SIM. *QF5-M2, QF5-A10, X-PX2-N1, QF5-A8.*
- **R-29** NEW · CARD-P · P1 · M8. MACRO-R06-US-FUT: US index-futures vol target (new card), FORWARD-SIM pending a 1926+ settling run. *QF1-A1, QF4-A2, QF5-A23, QF6-A8, QF3-A4.*
- **R-30** NEW · GOVERNANCE · P1 · M3. Volatility-estimator selection gate and forecast-evaluation harness; COMB registered challenger. *QF6-M1, QF6-M2, QF6-A1, QF6-A2, QF6-A3, QF6-A4, QF6-A20, QF7-M2, QF7-A22, X-PX1-N6, X-PX1-N4, QF3-A23, QF6-A25.*
- **R-31** NEW · CARD-P · P1 · M7. Drawdown step-down card: −8% and −12% steps, time-boxed at 21 sessions, specification book until PASS. *QF4-M3, QF4-A4, X-EX1-N2.*
- **R-32** CHANGED · GOVERNANCE · P0 · M0. Card header and artifact schemas v2 (`model_card.macro`, `macro_state`, `context_log`). *QF3-A1, QF3-M2, QF4-M2, X-EX2-N3, QF2-A2, QF7-A24, QF2-M2.*
- **R-33** CHANGED · GOVERNANCE · P1 · M0. DO-NOT-BUILD list v2. *QF3-A23, QF6-A3, QF7-M1, QF7-M3, QF3-M6, QF6-M6, X-EX1-N2, QF4-M2, QF1-M1, QF3-A17.*
- **R-34** NEW · GOVERNANCE · P0 · M7 (frozen before the first card run). Timing-fragility gate: timing profile with a look-ahead positive control on every card. *QF2-M2, QF2-A25, QF2-A16, QF2-A17.*
- **R-35** CHANGED · GOVERNANCE · P1 · M8. `macro_daily` workflow gates aligned with v2 (roles, verdict filter, refusal and FORWARD-SIM books). *QF2-M3, QF4-M7, QF2-M8, QF1-A3.*

Totals, as in the council file: 16 CHANGED, 14 NEW, 2 DEMOTED, 2 RETIRED; 16 P0, 14 P1, 4 P2.

**Document changes.**
- **Header, Quick start, this changelog:** v2.0 status; council build order; gate-freeze rule; owner-decision defaults; the four v1.2 open points answered (QCE-001).
- **§0.4:** conclusions restated after the council.
- **§1:** P0–P10 kept, with v2 wording (`min()` composition in P2, value status in P5, the tick floor and instrument book in P10). New principles P11–P19 come from the council's red lines.
- **§2:** a v2.0 note plus the rows the council changed.
- **§3:** composition by `min()` and base weights (§3.3); a v2 module map that places R-01 to R-35 (§3.4); `PITValue` v2 and the new interfaces (§3.5); engine states, re-arm, fill model and books (§3.8); the workflow (§3.9, R-35).
- **§4:** effective-dated clocks; the 06:30:30Z KRX close bound; the provisional-row guard; H.15, H.10 and Treasury availability on the Fed business-day calendar; the ECOS 15:30 KRW close; staleness by schedule and role (R-19). The v1.2 staleness defaults are removed. The §4.2 registry gains publication schedules and roles.
- **§5:** R-01 to R-18 rewritten per `QC_modules.csv` and the resolutions. R-19 to R-35 are inserted after R-18 from a separate part.
- **§6:** schemas 2.0 (`schema_version` "2.0").
- **§7:** rules-store YAML 2.0.0: `owner_decision` markers with one canonical key per decision, the config blocks of R-19 to R-31 and R-34 reproduced verbatim, and a `do_not_build` block.
- **§8:** replaced in full by the council's gate (a separate part).
- **§9:** test plan v2 covering every module acceptance test, with post-patch golden values and new golden values from DL-A and DL-B.
- **§10:** DO-NOT-BUILD v2: items 1–26 kept and labelled harm / null / inconclusive with their basis; item 11 split; items 27–37 new; the rules-store refusals (§10.3).
- **§11:** post-patch snapshot on the official 2-Oct close, with the risk layer, calendar and refusal books.
- **§12:** build order v2 (M1 starts with the KIS quote check; calendars, data contracts and the forecast registry; M9 out-of-sample acceptance).
- **§13:** v2.0 ID conventions and the Quant Council sources.

**SPEC-REWRITE rows absorbed outside §8.**
- QCE-001 → Quick start.
- QCE-013 → P5, §3.5, R-01.
- QCE-014 → P10.
- QCE-021 → §3.3.
- QCE-022 → §3.8.
- QCE-023 to QCE-027 → §4.1.
- QCE-028 → §4.2.
- QCE-032 → R-03.
- QCE-036 → R-04.
- QCE-042, 046, 049, 053, 059, 060 → R-06.
- QCE-061 → R-07.
- QCE-064 → R-08.
- QCE-066 → R-09.
- QCE-067 → R-10.
- QCE-071 → R-11.
- QCE-076 → R-12.
- QCE-080 → R-13.
- QCE-082 → R-14 (the protective trend card is R-28).
- QCE-085 → R-15.
- QCE-087 → R-16.
- QCE-094 → R-18.
- QCE-095 → §6.
- QCE-100 → §7.
- QCE-124 and QCE-126 → §9.
- QCE-136 → §10.
- QCE-146 → §12.

---

## Changelog v1.1 → v1.2 (independent QA)

v1.2 changes no rule, parameter, bound or verdict. It corrects labels and internal contradictions found by an independent QA pass; every edit is logged with its source in the backlog's Appendix Q.

1. Added the **Quick start for Claude Code** above.
2. **R-06 and §8.9:** the Korea non-inferiority p-values 0.25 / 0.32 (0.24 / 0.32 before the 2-Oct official-close patch) are the larger of the 10-session and 101-session block results (0.21 / 0.29 with 101-session blocks alone); v1.1 labelled them "101-session".
3. **R-06 and §7:** the B5 PIT threshold is now stated (χ² on 10 bins, p ≥ 0.01, the app's own cut-off and R4b's declared rule). v1.1 left it undefined.
4. **R-03:** the post-publication decay figures (+0.66 → +0.26) are labelled as cap-2 results; under the spec's cap 1 the gain is +0.20 in both 1990–2007 and 2012–26 (R4).
5. **R-11:** the indicative verdict now follows §8.7's verdict order: REJECT under value timing (35 onsets); INSUFFICIENT DATA by tier under strict H.10 (26 onsets), with PC-1 and PC-2 failing in both. (Council erratum: on the 1997–2026 DEXKOUS history the tier is met at every timing, 54 strict-H.10 onsets, and R-11 is a REJECT.)
6. **§6.2:** the `overlay_decision` example for the US momentum family no longer carries the S2 rates leg (S2 excludes momentum; T-BASIS-01).
7. **§8.6:** the exact return dates used by the Korea golden windows are listed; four of them include the start-date return.
8. **§10 item 14 and §13 N-50:** period and scope labels corrected (₩21.5tn is September selling; the 26 straddling CIs are market-level de-risk overlays).
9. YAML `version` is "1.2.0" (one key added: `estimator_gate.pit_p_min`). JSON `schema_version` stays "1.1": no schema changed.

## Changelog v1.0 → v1.1

v1.0 was written from the research alone, without knowledge of QUANTGEN's code. v1.1 adapts it to the real application. **The evidence, the rule definitions, the bounds and the DO-NOT-BUILD list are unchanged unless listed here.**

1. **Architecture re-mapped to the real packages (§3).**
   - v1.0's suggested `quantgen/macro/...` tree is gone.
   - Each component now names the existing package it extends: `core/ficc/data`, `core/ficc/macro`, `core/quant/risk`, `core/quant/signals`, `core/quant/backtest`, `core/engine`, `core/rules`, `core/skills/workflows`, `core/calendars`, `core/markets`, `config.py`, `tests/run_all.py` and `docs/`.
   - New files and interfaces are labelled **proposed**.
   - §3.6 reconciles the spec with the existing 18-indicator macro sheet and regime read. §3.7 reconciles it with the 6-component signal composite.
2. **Read-only by construction (P0, §3.8, §3.10).**
   - QUANTGEN has no order path. Every v1.0 statement about capital, live trading, execution or fills now refers to one of four things: the simulated order book in `core/engine`, the costed backtest in `core/quant/backtest`, the displayed exposure recommendation, or a Strategy Lab card.
   - v1.0's "live shadow" becomes **FORWARD-SIM**: a forward-running simulated book that writes timestamped artifacts.
   - "0× only from the fail-closed risk engine" now maps to two places: the risk layer in backtests and the runtime's **HALTED** state in the simulated book. Stress "entry blocks" map to **evaluator decisions**.
   - §3.10 records what would have to hold if a broker path were ever added. It does not design one.
3. **Governance now runs through the existing nine-step gate and its four verdicts (§8). v1.0's parallel promotion process is gone.**
   - Every overlay rule is a model card.
   - A pre-registered **protective-overlay card class** is defined in §8.7. Its claim is drawdown protection with Sharpe non-inferiority.
   - The class exists because a de-risk overlay is worth 0.00 to +0.10 Sharpe and cannot pass a benchmark-difference test. Detecting +0.05 needs about 150–330 years for a market vol target (SE(ΔSR) vs S 0.061 US, 0.130 KOSPI); 33–44 years holds only for add-on legs. QUANTGEN's own card E1 shows the problem: it protected (max DD −15% vs −27%) and was still rejected, because its claim was outperformance.
   - Tiers A, B and C are kept and restated in gate terms (§8.3).
   - Indicative verdicts for the current rules, from local reference data, are in §8.9. They are not a run of the app's gate.
4. **QUANTGEN's pre-registered costs apply to every acceptance test (P10, §8.5, §9.3).**
   - The costs are per side, with a 2× stress: KRX ETF 3 bp, KRX stock 35 bp, US shares via KIS 50 bp, crypto 10 bp, futures 5 bp, FX 10 bp.
   - **The R4 golden values were gross.** `r4_golden_values.py` applies no cost term.
   - v1.1 adds net values from `scripts/r4b_golden_net.py` → `results/R4b_golden_values_net.csv`. §9.3 shows gross, net 1× and net 2× side by side.
   - Three conclusions change at these costs. The KRW leg at KRX-stock cost and both US legs at 50 bp lose their gross edge. The Korea vol target keeps its drawdown benefit.
5. **Volatility estimator (R-06, §8.5, BL-G01).**
   - A B5-style check (rolling-origin 5% VaR exceedance within ±2 binomial SE, plus PIT uniformity) was run with filtered historical simulation. SMA20 passes on KOSPI, SPY and the US market. So does EWMA(0.94).
   - Under the rule declared before the run, **SMA20 stays the default in both markets** and EWMA(0.94) is the registered challenger. (Council erratum: SMA20 is not a validated default. It is outside the 90% QLIKE model confidence set at 1, 5 and 21 days in both markets, p ≤ 0.0005, though inside the MSE set in the US; it stays the displayed baseline.)
   - GARCH-t or GJR may replace SMA20 only after passing B5. (Council erratum: in the FHS form used for SMA20, long-window GARCH-t and GJR-t already pass B5 on KOSPI 2001–26 and the US 1995–2026; the SPY REJECT is the t-quantile fan-tail form.)
   - The calm / normal / elevated / stressed labels are display-only and computed causally.
6. **Timing convention (§4.1, §9.3).** Every rule now follows "decide at the close of day t, earn from day t+1".
   - `decision_utc` is the official close. The v1.0 15:15 KST close proxy existed only for closing-auction orders, which QUANTGEN does not place, so it is removed.
   - **Strict H.15 timing is +2 business days for a US close decision.** v1.0's "+1 day" was 15 minutes early via H.15: DGS10(D) posts at 16:15 ET on D+1, after the 16:00 close. (Council erratum: via the Treasury par-yield channel, "usually available … by 6:00 PM Eastern Time" on D, +1 business day is compliant when the posting time is logged; the rates-leg verdict is unchanged.) Under strict timing the rates leg's full-sample gross edge is −0.000 (share 0.53).
   - **Strict H.10 publication timing is added.** Under it the KRW leg's gross edge is +0.001 (share 0.53).
   - Golden values computed on value timing are flagged in §9.3.
7. **Numbers corrected (Appendix V of the backlog).** 214 checks of v1.0 numbers: 201 MATCH, 11 traced to a note line, 2 MISMATCH. Another 52 new v1.1 numbers were self-checked against R4b, and all match. The corrections are:
   - §2.2 constant-vol line: HML and CMA "since 2020" are −0.08 and −0.16. v1.0 printed the full-sample −0.03 and −0.06.
   - R-01 and R-12 timing chain: "+0.041 → +0.010" mixed an R2 figure with an R4 figure. It now reads +0.038 (value timing) → +0.010 (+1 business day) → −0.000 (strict).
   - S2 is "ON since 23 Sep" by data date. In the forward book it applies from the decision at the close of 25 Sep (strict H.15).
   - The Markov 0.554 / 0.390 figures are labelled as net of 10 bp.
8. **Backlog** (v1.1): items needing a broker path or fill logs move to a new "blocked by read-only design" section. New items cover the gate (BL-G01 to BL-G09). Appendix V is the verification log.

---

## 0. Header

### 0.1 Purpose

This file specifies how macroeconomic and cross-asset information enters QUANTGEN, an open-source, **read-only** quant research desk. It covers:

- which inputs to ingest, how to timestamp them, and when a value counts as stale or provisional;
- which overlay rules to register as model cards and with which instrument book;
- which rules to build as insurance on a formal PASS, which to run only in the specification book or forward in the simulated book, which to keep as labelled refusals, and which never to build;
- exact formulas and parameters, JSON artifacts and rules-store entries;
- how each rule passes through QUANTGEN's nine-step gate and the council's protective-card package (§8);
- tests with numeric acceptance values ("golden values"), gross and net of QUANTGEN's pre-registered costs.

### 0.2 Scope

**What QUANTGEN reads, and therefore what the overlays can act on in its simulated books:**
- Korean equities and ETFs, KOSPI200 futures and options, KTB and USD futures, KRW benchmark yields, the USD/KRW fixing, and investor flows. All of these come as quotes through the KIS Open API. The KRX marketplace (session close) and OpenDART filings are also read.
- US yields, indices and stocks (KIS, FMP, FRED, Yahoo). US exposure and factor sleeves remain the reference market where most of the evidence was measured. Whether QUANTGEN runs a US sleeve at all, and on which line, is owner decision D5.
- Crypto, from public exchange data only (Upbit, Binance, CoinGecko).

**What "act" means here.** QUANTGEN has no order path. An overlay changes only these things:
- the weights in the simulated order book of `core/engine`;
- the costed backtests in `core/quant/backtest`;
- the model cards in the Strategy Lab;
- the exposure recommendation shown on screen.

**Planned** (specified, dormant until the sleeve exists): an FX sleeve, a crypto sleeve and further equity markets (R-17). The crypto desk already exists, so R-17 reconciles with its crypto trend cards: C3 on KRW-BTC is a PASS.

### 0.3 How to use this file

1. Read §1 (non-negotiables P0–P19, including P0 read-only) and §10 (DO-NOT-BUILD v2) before writing any code.
2. Implement in the milestone order of §12 (the Quick start shows it in one table). Each milestone has acceptance criteria, which point to the tests in §9 and the golden values in §9.3. The gate package (R-21–R-24, R-34) is frozen before any formal card run.
3. **Extend QUANTGEN's existing packages and conventions.** §3 names them. They are:
   - Python with numpy/scipy;
   - decimals inside the core, with % and bp only in the UI;
   - the routing rule that an explicit provider which fails **raises**, and only "auto" degrades to labelled synthetic data;
   - immutable rule models with no financial defaults;
   - seeded, reproducible runs;
   - hermetic tests.

   Paths and interfaces marked **proposed** are this file's inference and may be renamed. Field names, parameters, bounds and tests are binding.
4. Every parameter lives in the rules store (`core/rules`, one JSON file with edit history) or in `config.py`.
   - An acting parameter may change only through a new card revision (§8.4), which counts as a trial in the card's family ledger (R-23).
   - **Lowering a pre-registered cost is never a permitted change.**
   - The owner-decision keys hold the council default until the owner rules; the Quick start table is canonical, and the §7 registry `owner_decisions` is its machine-readable form.
5. Nothing in this file needs the research notes, except the frozen fixture and ledger-seed files listed in the fixture manifest (§9.5). Every number cites its evidence in §13: by node ID (N-xx) for the v1.x research, and by council item (QFn-Ax/Mx, X-PX/EX-Nn), data-lab test (DLA-xx, DLB-Tx) or resolution for v2.0. Appendix V of the backlog traces the v1.1 numbers; Appendix Q logs the v1.2 QA corrections; `council/QC_errata.csv` logs the v2.0 errata.

### 0.4 What the research concluded

**Who studied it.** Two independent panels studied the question:
- **professors** in macro, econometrics, asset pricing, game theory, curricula and quant ML;
- **senior practitioners** from IB, NYSE trading, rates/FX, strategy, risk, systematic PM and research.

Their work was checked against local data from 1926–2026 (Ken French, FRED, Yahoo, KOSPI). A third round followed:
- seven quantitative-finance specialists (QF1–QF7) audited v1.2;
- four reviewers cross-examined them (PX1, PX2, EX1, EX2);
- two independent data labs re-ran the numbers (DL-A, DL-B);
- a council of three chairs (professors, executives, QF) ruled on all of it; its ledger holds 361 items (`council/QC_COUNCIL_RESOLUTIONS.md`).

v2.0 implements those rulings.

**The core finding stands: macro cannot forecast direction at QUANTGEN's horizons, but it can size risk.**

- **Lagged macro quantities do not lead returns.** Implied-vol and credit-spread changes carry incremental out-of-sample variance information for US horizons up to one month. No stress variable forecasts lower returns out of sample: none survives a BH-10% correction, EPU included. The VIX level forecasts US variance, and the VIX/VIX3M slope adds a little (t = 7.17 alone, about 4 given current realised vol, vs t = 0.04 for next-21-day returns). Neither is a KOSPI vol input beyond KOSPI's own vol.
- **Nearly every macro rule in the prior design failed on honest data.** This includes:
  - the four-state table and all multipliers above 1.0;
  - the VIX-term-structure momentum switch;
  - the SOX×KRW Korea gate, whose +0.31 Sharpe came from look-ahead;
  - the curve, real-rate and credit gates, and the oil gate;
  - the net-liquidity crypto rule and the 24-hour event blackouts.
- **The two macro legs that v1.x ran forward are REJECTs on long history and are retired** as labelled, display-only refusal books (R-11, R-12):
  - the USD/KRW leg: 54 strict-H.10 onsets on 1997–2026, ΔMDD −1.3 pp vs the same-exposure static book, tail-exposure ratio 1.00;
  - the US rates leg: 71 onsets, REJECT at every timing and every cost, including the compliant Treasury +1-business-day channel.

**What survives in v2.0:**

1. **Momentum sized by its own risk state (R-03).**
   - Own-volatility scaling at cap 1 lifts US momentum Sharpe from 0.40 to 0.71 gross and 0.67 net of 50 bp on both legs. Max drawdown improves from −63% to −28%.
   - Indicative PASS. Step 3 passes at N_equiv 6.3 (deflated ΔSR 0.98) and is borderline at the linear N̂ 12.6 (0.947).
   - The floored Daniel–Moskowitz gate lifts the stack to 0.80 gross / 0.74 net, but it fails step 3 (0.77) and stays in the specification book (R-04).
2. **Reversal and quality held at 1.0× (R-05).**
3. **A per-market continuous volatility target, cap 1.0 permanent, on Korea-local inputs (R-06).**
   - In the 22 Jun–30 Jul 2026 KOSPI crash it cut the loss from −38.6% to −12.2% (−12.3% net of 35 bp). No US-sourced indicator saw that crash.
   - On KOSPI 1997–2026 on the KRX ETF line it is an indicative PASS under v1.2's checks: ΔMDD +12.7 pp vs the same-exposure static book, tail ratio 0.68, p_ni 0.052.
   - The PASS is fragile: 2016–25 alone is a REJECT, and 1997–2002 alone is a REJECT.
   - v2.0 builds it as **crisis-clustering insurance (BUILD-AS-INSURANCE) only on a formal PASS on long KRX history**, under conditions fixed before the run. It is Sharpe-neutral, charges a bull-market tax and is short the post-crash rebound premium.
   - On current evidence that formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build: the computed selection factor exceeds the 1.28 that PC-3 tolerates at the indicative p_ni 0.078, and no convention may be changed to rescue it (R2-C1; §8.9).
   - The US card at 50 bp per side is a **REJECT about its instrument book** (US shares via KIS, daily), not evidence against vol targeting. An index-futures card (R-29) runs FORWARD-SIM.
4. **Samsung + SK hynix concentration limits on look-through exposure (R-07):** an active single-name cap and an owner-chosen aggregate template (D1).
5. **Strict point-in-time, cross-time-zone data handling (R-01, R-19, R-20).** Timing errors were the largest source of fake edge in the whole programme. v2.0 adds value status, session dates and post-close fixtures, because the "2-Oct close" in v1.2 was an intraday print. It also adds effective-dated calendars and staleness measured against each source's publication schedule.
6. **A hedge-validity state (R-09).** Do not count bond or dollar hedges when inflation is high or the stock–bond correlation is positive. A stale input assumes the hedge fails; it never HALTs any book.
7. **Event handling with short intraday windows instead of blackouts (R-10),** plus tags for multi-session holiday gaps.
8. **Slow macro as logged context only (R-13):** Sahm, the yield curve, Taylor residuals, real yields and term premium, now with first prints and vintages.

**What the Quant Council changed (v2.0).**
1. **The engine can no longer freeze itself.**
   - Staleness is measured against each source's publication schedule. A risk-model input never HALTs; it sets `hedge_credit_off = TRUE`.
   - The drawdown ladder composes by `min()`, re-arms explicitly and time-boxes its steps.
2. **One gate package, adopted once and blind, before any formal card runs.**
   - Single-path ΔMDD stops gating. PC-1′ (expected shortfall of 21- and 126-session returns) gates instead, and PC-3 stays binding.
   - A do-no-harm cap replaces drawdown REJECTs.
   - Step 3 counts trials on a family ledger with N_eff = max(N_clusters, N_equiv).
   - Episodes are objective and market-own, and returns are excess returns with local cash.
   - A timing-fragility gate and a power/MDE line apply to every card.
   - All of it sits behind a placebo and negative-control acceptance test (§8; R-21–R-24, R-34).
3. **Every card declares its instrument book, notional, rebalance rule and band before the run.** A tick floor raises costs where ticks are coarse (R-26).
4. **The estimator stays SMA20 for the first formal runs.** COMB = ½(GJR-t + log-HAR-range) is the registered challenger behind a staged, counted, fail-closed gate (R-30).
5. **Refusals and demotions:**
   - R-08 is an execution-state annotation;
   - R-11 and R-12 are retired as labelled REJECTs;
   - R-04 is specification book only;
   - no regime-model state is acted on or displayed.
6. **Trend:** a protective-only monthly SMA10m card for US and non-Korean sleeves runs FORWARD-SIM (R-28). The Korean trend state is context only.

**Expectations.**
- A de-risk overlay is worth 0.00 to +0.10 Sharpe, and a backtest cannot prove it. Detecting +0.05 needs about 150–330 years for a market vol target (SE(ΔSR) vs S 0.061 US, 0.130 KOSPI).
- Twelve forward months add only 3–10% of the information. Forward records are falsification alarms, never validation (P14, R-25).
- So the overlays are judged as **protective** cards: on tail legs and drawdown lines against a static book with the same average exposure, with Sharpe non-inferiority (§8).
- Card E1 shows the same tension. It protected and was rejected for outperformance, because outperformance was its claim.

### 0.5 What QUANTGEN already is (the facts this file builds on)

From the architecture review and the public page:

- **Three rules written into the code.**
  1. Read-only by construction: no order, cancel, withdrawal, deposit-address or transfer path on any venue, and nothing to switch on.
  2. Decide at the close of day t, earn from day t+1, with pre-registered per-side costs and every result re-run at 2×.
  3. The gate decides, not the author. Its four verdicts are PASS / REVISE / REJECT / INSUFFICIENT DATA.
- **The nine-step gate.**
  1. Purged walk-forward, 756 in-sample / 126 out-of-sample sessions, embargo = holding period.
  2. Lo (2002) Sharpe SE plus a 90% block bootstrap (2,000 resamples × 10-session blocks); the interval must clear zero.
  3. Deflated Sharpe ≥ 0.95, with every revision counted as a trial.
  4. PBO via CSCV: PBO ≤ 0.05, or the in-sample winner loses in ≤ 10% of splits. PBO > 0.2 with the winner losing is a REJECT.
  5. Benchmark difference, one-sided p ≤ 0.10.
  6. Sharpe > 0 at 2× costs.
  7. Plateau: ≥ 50% of neighbouring configurations keep half the Sharpe.
  8. ≥ 60% of calendar years positive.
  9. Live haircut 40% (`live_sharpe_multiplier: 0.60` on out-of-sample Sharpe), reported but not gated; each card also prints its own Harvey–Liu haircut.
- **Model cards.** Each card holds a hypothesis, a rule, a data span, pre-registered costs, a seed, every test line, the decision and an md5 of the results. A REVISE names the first failed check and the only permitted fix: widen the grid, lengthen the holding period, or extend the history. Every revision counts as another trial.
- **Strategy Lab.** The record holds 34 cards: 5 PASS, 11 REVISE, 18 REJECT and 0 INSUFFICIENT DATA (study run 2026-09-27, seed 11). Rejected families still run, labelled. Card E1 (trend switch) is kept on the ETF page as a descriptive sleeve with its verdict.
- **Quant Lab.**
  - Models: GBM, jump diffusion, block bootstrap and GARCH(1,1)-t.
  - Path colours carry the conditional-vol quartile labels calm / normal / elevated / stressed. (v2.0 renames them "path-vol quartile"; R-06's display labels are a different object; R-16.)
  - The lab grades its own VaR. GARCH-t on SPY breached a 5% VaR on 6.6% of days with PIT p 0.003, so it is a REJECT. GJR on SPY also sits at 6.6%, with PIT p 0.014. The skewed-t stays out of the menu. These are t-quantile (fan-tail) results from the app's own study, UNVERIFIED until `docs/vol_backtest.py` and its seed are published; in the FHS form used for sizing, long-window GARCH-t and GJR-t pass B5.
- **Desk pages.** Each states what it withholds. The ETF page withholds "trend, vol target, risk parity and sector momentum as signals". The Volatility page withholds the VIX roll-down trade (out-of-sample Sharpe −0.14). The Rates page shows the Diebold-Li factors as a description, because the forecast beat the random walk at 0 of 5 maturities.

---

## 1. Design principles (non-negotiable)

These are enforced in code, as assertions, schema bounds and rules-store validation, not by convention. P0–P10 carry over from v1.2 with v2.0 wording. P11–P19 are the council's red lines (QC resolutions §c), adopted as principles. A request that would change any of them is a principle change and goes to the owner (D3 is the only one open in v2.0).

**P0. Read-only by construction.**
- No module in this spec may contain, import or call an order, cancel, withdrawal, deposit-address or transfer path on any venue. KIS is used for read-only quotations only.
- Every output is one of the following:
  - an artifact (§6);
  - an entry in the **simulated order book** of `core/engine` (orders module: "simulated order book — NO broker order path");
  - a costed backtest or forward-simulated book in `core/quant/backtest`;
  - a **model card**;
  - a **displayed exposure recommendation**.
- A displayed recommendation may come only from cards whose verdict is PASS (P7). Every other card is computed, logged and shown as a descriptive sleeve labelled with its verdict. This is the treatment card E1 gets on the ETF page.
- Evidence: QUANTGEN rule 01 ("There is no code path that sends an order, on any venue, and nothing to switch on").

**P1. Macro scales risk; it never generates direction.**
- No macro or overlay module may create, flip or close a simulated position on its own.
- Overlays output multipliers only. Signals come from the signal families and the existing composite (`core/quant/signals`, §3.7).
- Every acting rule states a second-moment mechanism on its card (council red line P5). A level of a stress variable used as a mean gate is a principle change (D3).
- Evidence: N-01, N-04.

**P2. Bounded multipliers, composed by `min()`.**
- **Overlay multipliers** (family or market-gross) must lie in **[0.5, 1.0]**.
- **Composition (v2.0).** Overlays at one level compose by `min()`, never by product. At market level the drawdown ladder and the post-re-arm cap join the same `min()`: composed(m) = vt × min(1.0, overlay₁, …, overlayₖ, ladder, post_rearm_cap) (§3.3, R-02). A product-composed path is refused.
- **Floor outside HALTED.** Every overlay floors at 0.5, so composed(m) ≥ 0.5 × vt on every day that is not HALTED. The floor binds `composed(m)` (§3.3), not `gross(m)` or final weights: a binding concentration bound or active single-name cap (R-07) may take gross below 0.5 × vt; it is logged in `binding` and is never a bounds failure (`bounds_ok` checks `composed`).
- **Vol-target and vol-scale weights** must lie in **[0, 1.0]**. They are risk-layer sizing, not overlay multipliers. They have no floor, because a floor would undo the crash protection: the Korea weight was 0.30–0.33 on 22–23 Jun 2026. The vol-target cap of 1.0 is permanent (R-06).
- **No multiplier anywhere may exceed 1.0.** The rules store rejects a rule whose output can exceed 1.0; this is Tier C (§8.3).
- **0× comes only from the risk layer.**
  - In backtests: `core/quant/risk` limits and the hard stop (R-07).
  - In the simulated order book: the `core/engine` runtime entering **HALTED** for the book concerned (§3.8: every book has its own runtime state), triggered by that book's hard stop (−15% of book NAV, D2) or risk-limit breach (class RISK), or by an operational failure of something that book reads: repeated failure of an acting input bound to it, its own artifact's acting-field validation, a lag-audit violation, feed heartbeat loss (class OPS). A risk-model or context failure never HALTs.
  - The overlay can never output a value below 0.5.
- Evidence: N-02, N-03; product stacks sit at ≤ 0.25× total exposure on 31.0% of KOSPI days vs 11.2% under `min()` (EX1).

**P3. Stress variables feed sizing, annotations and event blocks; never means.**
- VIX term structure, credit, oil, EPU and USD-down-with-equities enter only through these channels:
  - the volatility estimator, and only through the staged estimator gate (R-30): implied vol enters only inside HAR-IV if it wins the race, read live at the decision time. `max(SMA20, implied)` is retired (§10);
  - **execution-state annotations** (R-08), which change no weight;
  - **new-entry blocks for scheduled events** (R-10), which are `core/engine` evaluator decisions in the simulated order book and the same rule in backtests;
  - the event calendar;
  - Monte Carlo scenarios and the historical-replay library (R-16).
- They are never mean gates, and never cut-and-re-add triggers on existing exposure. QF5-M10 (a VIX level as a mean gate on reversal) is not adopted (D3).
- Evidence: N-04, N-05.

**P4. Korea's risk inputs are local.**
- Korea gross is driven by KOSPI's own volatility, concentration and (later) leverage state.
- US or global macro states never gate Korea gross.
- US overnight information enters Korea only as an opening-gap and volatility input. The KOSPI trend state is context only (R-28 has no Korea instance).
- Evidence: N-16, N-18, N-40.

**P5. Everything is point-in-time. Decide at the close of day t; earn from day t+1.**
- **Timestamps.** Every datum carries a UTC observation timestamp, a UTC `available_at` (publication) timestamp, a UTC `retrieved_at` (knowledge) timestamp and a `value_status` (R-01).
- **Decision time.** `decision_utc` is the official close of the market being decided, from the effective-dated calendar (§4.1, R-20). For KRX since 2015-06-15 it is the close-print bound, the scheduled close + 30 s: 06:00:30Z through 2016-07-29, 06:30:30Z from 2016-08-01, and the CSAT close + 30 s on CSAT days. Before 2015-06-15 it is the scheduled close plus the declared print tolerance (30 s). For NYSE it is the scheduled close + 30 s (DST-aware; R-20).
- **The availability rule.** A datum may enter a decision only if `available_at_utc ≤ decision_utc`. The resulting weight earns from the next session. *Single exception:* R-34's `timing_probe` sandbox, which re-times inputs on purpose for the L ≤ 0 rows and the look-ahead positive control; its rows are tagged `synthetic_lookahead = true`, never write a production artifact and never feed a verdict (R-34).
- **The value-status rule (v2.0).** A close-type acting input must have `value_status = official_close` and `session_date` equal to the decided session. A provisional intraday row is a missing input, even when its `available_at_utc` precedes the decision.
- **Lags.** Lags are calendar-based, never positional. Publication business days come from the publisher's calendar (Fed, SIFMA), not the equity trading-day index.
- **Missing, stale, provisional or synthetic inputs fail closed** by role (R-19):
  - an acting input leaves the state unchanged and raises an alert;
  - a risk-model input of `hedge_state` sets `hedge_credit_off = TRUE`; a covariance-only input is carried, labelled stale, for up to 5 decisions and then dropped from the covariance and labelled (R-19 rule 4);
  - a context input is labelled.
  - Nothing is ever silently interpolated.
  - Staleness is measured against the source's publication schedule, not the observation's age.
- **No synthetic data for acting inputs.** `core/ficc/data` lets an "auto" provider degrade to labelled synthetic data. For an acting input that degrade is forbidden: a synthetic or degraded value is treated as a missing input.
- **Vintages and names.** Revised series are stored with vintages and first prints. Every series is named (no unnamed "Brent").
- Evidence: N-46, N-47; QUANTGEN rule 02; QF2-A1/A2/A3 (the 2-Oct provisional row; H.10 inputs stale at 100% of decisions under v1.2's defaults).

**P6. Thresholds on changes or percentiles.**
- Thresholds are defined on changes or on expanding/trailing percentiles, never on levels calibrated to today.
- Evidence: N-12.

**P7. The gate decides.**
- Every overlay rule that changes exposure is a model card and passes through the nine-step gate (§8.1). Protective rules use the protective class (§8.7).
- **Only PASS cards feed the displayed recommendation:**
  - a CARD-O PASS as a recommendation;
  - a CARD-P PASS as insurance (BUILD-AS-INSURANCE, with its insurance label).
- **Everything else stays out of the recommended book:**
  - FORWARD-SIM cards (R-28, R-29) run forward in the specification book;
  - specification-only factors (R-04; ladder steps whose binding share exceeds 0.10, until R-31 passes) are labelled with their verdict;
  - refusal books (R-11, R-12) are display-only and read by no other book.
- Nothing becomes a recommendation because a backtest looks good, and a rejected card is not deleted.
- Evidence: N-50; QUANTGEN rule 03.

**P8. Every multiplier declares its exposure basis.**
- `active` means it scales a family's long/short or benchmark-relative risk.
- `total` means it scales the market book's gross long exposure.
- Evidence: N-02. The executives traced a misreading of the 9 Apr 2025 momentum result to exactly this confusion.

**P9. Slow macro is context.**
- Sahm, the yield curve and probit, Taylor residuals, real yields, term premium, breakevens, credit levels, survey data, and the Street's and the Fed's projections are logged daily and never act.
- This includes every indicator of the existing 18-indicator macro sheet that is not an acting input (§3.6), and the v2.0 context additions: leverage and flow monitors, VRP, live implied-vol snapshots and turbulence (R-13).
- Acting on any of them requires a new card.
- Evidence: N-26, N-30, N-56.

**P10. Pre-registered costs, always, with a floor.**
- **Rates.** Every backtest, forward-simulated book and golden value is charged QUANTGEN's per-side costs on every unit of turnover, and every result is also shown at 2×:

  | Venue | Per side | 2× stress |
  |---|---|---|
  | KRX ETF | 3 bp | 6 bp |
  | KRX stock | 35 bp | 70 bp |
  | US shares via KIS | 50 bp | 100 bp |
  | Crypto | 10 bp | 20 bp |
  | Futures | 5 bp | 10 bp |
  | FX | 10 bp | 20 bp |

- **Where the rates live.** Costs are defined once, in the gate's code. This spec reads them from there and never redefines them.
- **Tick floor (v2.0, INVARIANT, R-26).** The charged rate is cost_side = max(table rate, commission + ½·tick/price + tax_side). It can only raise a cost. Example: 252670 at ₩69 is charged at least 72 bp per side (T-COST-02); 252670 traded at ₩62–579 in 2026, about 10–82 bp per side.
- **Lines printed beside the 2× run, not gating:**
  - a state-dependent stress-cost line, until it is calibrated on KIS quote snapshots;
  - a futures roll-cost line;
  - turnover by regime.
- **Cost classes.** Leveraged and inverse ETFs carry their own class, read from the gate. An FX card declares its instrument: KRX USD futures or broker spot (R-17). The 50 bp US-shares rate is valid for single names, never for a market scalar.
- **Instrument book, declared before the run (v2.0, R-26).** A card declares its instrument book, notional NAV, rebalance rule and no-trade band in its header.
  - A futures line is allowed only if one contract is ≤ ~5% of the declared notional (mini KOSPI200 ≈ ₩56m; Micro ES ≈ ₩52m); otherwise the ETF line is used.
  - A market-gross scalar never runs on a stock book.
  - A different instrument book is a new card (P15).
- **No lowering.** Lowering a cost is never a permitted fix.
- Evidence: QUANTGEN rule 02; R4b (§9.3); QF1-M1, QF1-M3, QF1-A6, X-EX2-N3.

**P11. One gate package, adopted once and blind.** *(red lines P2, E2, Q1)*
- The CARD-P gate v2, the evaluation conventions, the step-3 ledger rule, the statistics harness and the timing-fragility gate (R-21–R-24, R-34) are fixed for every card before the first formal run. The gate-acceptance test results are md5-frozen with the package version.
- No gate rule, threshold or convention is chosen after seeing the card it decides. A change is a new package version, applied to every card, with its flips disclosed.
- No pooled or A-provisional route opens for a card already run (R-04, the jump model, KOSPI trend).
- Evidence: QC resolutions 4, 5 and 11.

**P12. A single path neither promotes nor rejects.** *(red lines P1, Q2)*
- **Promotion** needs all of:
  - objective market-own episodes;
  - no episode above 50% of the benefit;
  - no REJECT at any start of the declared start band, or in either pre-declared midpoint half;
  - per-regime lines.
- **Rejection.** Single-path drawdown statistics (ΔMDD, ΔCDaR95) are printed with bootstrap bands and never REJECT on their own. Through the do-no-harm cap they can at most cap a card at INSUFFICIENT DATA (R-21).
- Evidence: the bootstrap SD of ΔMDD is 7.4–7.8 pp and flat from 10 to 100 years; the same Korea card shows +12.7 / +3.8 / +10.6 pp by start date (X-PX1-N2); July 2026 carried 0.493 of the v1.2 PC-4 benefit.

**P13. Every selection is counted.** *(red line P4)*
- Every configuration ever run in a card's family, research phase included, is logged in a hashed family ledger with its timing class. A card without a ledger hash is refused.
- Step 3 deflates with N_eff = max(N_clusters, N_equiv). The Kish form is never used, and revision counts are not the trial count (R-23).
- Evidence: the Kish N̂ falls from 1.81 to 1.20 when 80 near-duplicates pad the ledger; N_equiv moves from 6.33 to 6.59.

**P14. Forward-simulated months are falsification alarms, never validation.** *(red lines P3, Q3)*
- A forward record can demote a card. It can never raise a verdict, or turn INSUFFICIENT DATA into PASS (R-25).
- UNDERPOWERED may convert only a failed step-5 or PC-3 p-value. It never waives PC-1′, PC-2 or the PC-3 point REJECT (R-24).
- Evidence: twelve months move SE(ΔSR) by ≤ 5%; 12-month triggers fire as often on a timing-free placebo as on the real Korea vol target (22% vs 22%).

**P15. Verdicts are book-specific; the book is declared before the run.** *(red lines Q4, E5)*
- A verdict belongs to the instrument book, notional, rebalance rule and band named in the header.
- A different venue or book is a new card, never a revision. A market-gross scalar is never judged on, or generalised from, a stock book.
- No instrument is used that the desk cannot execute at the declared cost and size (R-26).
- Evidence: the same US rule is REJECT at 50 bp and PASS at 3–5 bp; the Korea stock book is INSUFFICIENT where the ETF line passes; integer contracts give 7.5% a year of tracking error at a ₩0.1bn sleeve and 0.7% at ₩1bn.

**P16. Nothing may freeze, or quietly shrink, the book.** *(red line Q5)*
- Every hard stop has an explicit, automatic re-arm (R-07). Only the hard stop and risk-limit breaches (class RISK) carry the 10-session refusal and the 0.5× cooling-off; an operational HALT clears when its cause clears (§3.8).
- A HALT is scoped to the book whose own trigger fired; other books continue (§3.8).
- Staleness is schedule-aware and role-based (R-19).
- De-risk factors compose by `min()`, with a 0.5 × vt floor outside HALTED (R-02).
- Evidence: the literal v1.2 ladder never leaves HALTED (KOSPI from 1997-10, 714 halt cycles; DL-A); the v1.2 staleness defaults mark H.10 inputs stale at 100% of decisions; product composition sits at ≤ 0.25× on 31.0% of KOSPI days.

**P17. No exposure path the gate never sees.** *(red line E3)*
- Each new overlay is judged incrementally on the current recommended book.
- Once two or more de-risk factors act in the recommended book, the book is gated as one stack CARD-P (R-02, §8.7).
- Ladder steps that bind on more than 10% of days act only in the specification book until their CARD-P passes (R-31).

**P18. No acting decision on a provisional, intraday, bar-derived or stale input; no risk-model-only input can HALT.** *(red line E4)*
- Official closes are primary and are reconciled against a second source.
- Daily closes are never derived from intraday bars.
- Among data inputs, only `acting_exposure` inputs can escalate to HALTED, and only for the books they are bound to (R-01, R-19, R-27; scope in §3.8). The other triggers (hard stop, risk-limit breach, lag audit, schema or bounds, heartbeat) are listed in §3.8 with their class and scope. A `risk_model`, `context`, `forward_sim` or `history` input never HALTs a recommended book.

**P19. No regime-model state, acting or displayed.** *(red line E1)*
- No jump-model, Markov-switching, GMM or change-point "regime" state acts on exposure or is shown on any QUANTGEN page in v2.0.
- The σ̂ display labels (R-06) are volatility labels, not regime states, and stay.
- A BOCPD scale-break probability may be written to the R-18 research log only: never acting, never displayed (R-18, R-33).

---

## 2. Changes vs the prior design ("QUANTGEN Signal & Macro Map")

**v2.0 note.** The tables below record the v1.1 decisions against the prior design. Where the Quant Council changed a decision, the row says so after "v2.0:". Under v2.0 the 0–3 integers in §2.2 and R-15 are admissibility filters and display scores, not weights (R-15). The council's own changes are listed module by module in the v1.2 → v2.0 changelog.

**How to read the table.**
- **Decision codes:**
  - KEEP: unchanged.
  - MODIFY: changed as stated.
  - DROP: never build (see §10).
  - BACKLOG: not built; see the backlog file.
  - FORWARD-SIM (v1.0: SHADOW): runs forward in the specification book as a card; never a recommendation until re-gated.
  - BUILD-AS-INSURANCE (v2.0): built in the recommended book as labelled insurance, only on a formal CARD-P PASS.
  - RETIRED (v2.0): a REJECT recorded on long history; kept only as a labelled, display-only refusal book.
- **Notation in the Evidence column:**
  - "R4" marks a golden value recomputed under this spec's parameters (gross, §9.3).
  - "R4b" marks v1.1's net-of-cost or strict-timing recomputation.
  - "SR" is Sharpe ratio.
  - "share" is the fraction of bootstrap resamples in which the rule beats its base.

### 2.1 "Do this first" plumbing

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| Directional signal layer: one module per family, JSON artifact per asset | **KEEP** (mapped onto `core/quant/signals`) | Families are tagged components of the existing composite (§3.7, proposed) | — |
| Two simplest families: XS momentum 12-1 and 5-day reversal, on KR + US | **MODIFY** | US 12-1 runs only with own-vol scaling plus the D&M gate. Korea adds a 12-7 / residual momentum variant (UNVERIFIED prior) and keeps 1–5-day reversal. All tests are net of QUANTGEN's KRX stock cost, 35 bp per side, which covers the 0.20% sell tax. The 2× stress is 70 bp. | N-06; N-36. US 12-1 SR 0.33 since 1990, 0.02 since 2008. Korean 1-month reversal: Fama–MacBeth coefficient on r(t−1) −2.950 (t −3.77), a regression slope, not a strategy return; no return evidence yet nets 35 bp plus the sell tax. |
| Move volatility from signal to sizing: position = target vol / forecast vol | **KEEP, strengthened** | Weight = min(1.0, target/σ̂): a cap of 1.0, no levering up. Estimator SMA20 as the displayed baseline (it passes the B5-style calibration check but sits outside the 90% QLIKE model confidence set; selection by the staged estimator gate, R-30). v2.0: cap 1.0 is permanent; the Korea vol target is BUILD-AS-INSURANCE on a formal PASS on long KRX history (R-06); on current evidence that formal run is expected to return INSUFFICIENT DATA, so it is not expected to build (R2-C1; §8.9). | N-02, N-14. KOSPI vol target with cap 1.5: SR 0.534 vs 0.638 at cap 1.0 (R4, 2016–26). Long samples, cap 1.0 / 1.5 / 2.0: KOSPI 1997–2026 0.454 / 0.430 / 0.403; US 1990–2026 0.588 / 0.569 / 0.545. Aug-2024 −9.7% vs −7.9% (R4). |
| Per-market × per-family weight table as config | **KEEP** (v2.0: **MODIFY**) | Priors updated (§5 R-15); stored in the rules store. v2.0: the 0–3 priors are admissibility filters; base_weight(m, f) = IV_m × 1/K_m over admissible families, inverse-vol across markets (R-15) | N-35, N-36, N-33; QF5-M4, QF4-M5 |
| Regime-multiplier hook (default 1.0) read by the risk engine | **MODIFY** | Bounds [0.5, 1.0]; exposure basis declared; clipping logged; read by `core/quant/risk` and the engine evaluator. v2.0: overlays and the ladder compose by `min()`, never by product (R-02) | N-02; X-EX1-N2 |
| Falsification pipeline, net of 0.35% KR round trip | **MODIFY → the nine-step gate** | Every rule is a model card. A protective class is added (§8.7). Tiers are restated in gate terms. Costs are QUANTGEN's pre-registered ones (KRX stock 35 bp per side = 70 bp round trip; 2× stress). v2.0: the CARD-P gate v2, objective episodes, the family trial ledger, the power line and the timing gate, adopted once and blind (R-21–R-24, R-34) | N-50, N-51; QUANTGEN rules 02–03 |

### 2.2 Part 1 — signal families and the starting weight matrix

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| US XS momentum weight 3 | **MODIFY → 2 if vol-scaled with the D&M gate (1 if unscaled)** | Momentum is sized by R-03 and R-04 | N-35. Mean break in Oct-2002 (11.4%/yr before, 0.2% after): a descriptive, searched break that holds only from a 1963 start (QLR p 0.041; 0.10–0.11 from 1927 or 1990). R4: SR 0.40 → 0.80 with the spec stack (R4b net of 50 bp on overlay turnover: 0.74). |
| Japan XS momentum 0 | **KEEP 0** | It may rise to 1 if QUANTGEN's own vol-scaled card passes | N-35. Japan WML SR 0.07 (t 0.4). R4 vol-scaled: 0.196. |
| Europe / EM / APxJ XS momentum 3 | **KEEP** (prior only) | — | N-35. SR 0.78 / 0.93 / 0.71. APxJ vol scaling negative in 2016–26 (R4 −0.023). |
| Korea XS momentum 1 ("fragile, crash-prone") | **MODIFY** | 12-1 → 0. 12-7 / residual momentum → 1 (UNVERIFIED). | N-36 |
| Korea reversal 3; Korea flow 3 | **KEEP** (v2.0: reversal prior 3 → 1) | Reversal must clear the net-of-cost test at 35 bp per side and 2×. Flow weight stays, but with no flow-conditioned multiplier. v2.0: the Korea reversal prior is 1 (UNVERIFIED) until BL-U02 runs net of 35 bp plus tax (R-15) | N-09, N-21; QF5-A14 |
| TS momentum, per index | **MODIFY** | KOSPI 2 → 1; KOSDAQ → 0; Europe 3 → 0–1 (STOXX50 0, DAX 1, FTSE 0–1); Japan 2 → 1–2; Taiwan 2 → 1–2; China A 1 → 0; India 2 → 1; US 3 (keep); crypto 3 → 2 with BTC's own vol cap | N-33. Q1b B5 per-index 12-1 Sharpe and bootstrap. |
| "Vol-scaled sizing gives +0.1 to +0.3 Sharpe on nearly every strategy" | **MODIFY** | Robust only for momentum. Index vol targeting is risk control, not alpha. | N-06, N-14. Constant-vol scaling (cap 2) since 2020: ST_Rev −0.31, RMW −0.10, HML −0.08, CMA −0.16. Full sample 1990–2026: ST_Rev +0.13, RMW +0.02, HML −0.03, CMA −0.06 (Q1b B1b). **v1.1 correction:** v1.0 printed the full-sample HML and CMA values under "since 2020". |
| Reversal "strongest after a volume spike" (5-day z with vol/20d avg > 1.5) | **KEEP as signal spec; UNTESTED** | Not evaluated by either panel | — |
| Value–momentum hedge assumed universal | **MODIFY** | Measure it on QUANTGEN's own sleeves | N-35. French ρ −0.17 vs AMP −0.65 over the same window. |
| Published Sharpe ratios as priors | **MODIFY** | Haircut published premia by factor-specific out-of-sample declines: value −49%, momentum −23% (n.s.), carry ≈ −25%, defensive 0, multifactor −18%. One-sided (professors). The gate's own live haircut (40% off out-of-sample Sharpe; `live_sharpe_multiplier: 0.60`) is reported on every card in addition, with the card's Harvey–Liu haircut beside it. | N-60; PR-P-02 |

### 2.3 Part 2 — global macro variables

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| Real 10y: momentum weight down when the 3-month change > +50 bp | **DROP** | Real-yield changes go to the context log and risk attribution | N-11. Momentum SR 0.88 when real rates rose > 50 bp vs 0.02 otherwise; gate ΔSR −0.04. |
| Curve: gross cut when it re-steepens from inversion | **DROP** | 10y–3m is logged as a prior | N-11, N-30. Book ΔSR −0.09 (share 0.00). |
| Broad USD: per-market exposure scaled by rolling USD beta | **MODIFY** | Context plus hedge-validity state (R-09). The USD gate for EM momentum goes to backlog. v2.0: DTWEXBGS is context; a labelled live USD proxy feeds `hedge_state` as a risk-model input that never HALTs (R-09, R-19) | N-29. USD up in 10 of 11 drawdowns; failed Apr-2025. |
| VIX term structure: momentum off, reversal on when inverted | **DROP as a switch** | v1.1: a new-entry block card (R-08) and a logged vol-estimator alternative. v2.0: an execution-state annotation that changes no weight (R-08, CONVENTION); the logged `max(σ̂, implied)` alternative is retired and implied vol is context (R-13) | N-04, N-05. Momentum ΔSR −0.15 (2020–26). As a CARD-P the block fails PC-1 and PC-2 in 10 of 10 cells (DLB-T6b). |
| Credit (HY OAS): quality weight up on +50 bp | **DROP** | Credit is context only; its use is in backlog BL-C03 | N-11, N-13. RMW 1.5× ΔSR −0.01. |
| Global PMI: value weight tied to PMI slope | **DROP** (backlog data acquisition) | No local PMI; macro factor timing fails | N-11 |
| Fed liquidity: crypto allocation scaled by the 13-week net-liquidity change | **DROP** | The planned crypto sleeve uses BTC's own trend plus vol target; QUANTGEN's crypto trend card C3 already covers the trend part | N-55. ΔSR −0.01; −0.20 in 2023–26. |
| Overlay range "0.5× to 1.5× (family), 0× to 1× (gross)" | **MODIFY → [0.5, 1.0] for both; 0× only from the risk layer (backtest) or HALTED (simulated book)** | — | N-02, N-03 |

### 2.4 Part 2 — market-specific variables

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| US: ISM / 2y tilts | **DROP** (2y repricing → backlog) | — | N-11, N-25 |
| Europe: BTP-Bund, TTF gates | **BACKLOG (UNTESTED)** | — | — |
| Japan: momentum off and value/low-vol up around BoJ meetings | **DROP** | Up-weights are forbidden; BoJ hikes were muted (Jun/Sep 2026 Nikkei +0.13% / +1.38%) | N-03; PC-P-20 |
| Korea: momentum gate on SOX 60-day trend | **DROP** | SOX(t−1) becomes an opening-gap input | N-18, N-40. Look-ahead +0.31 → +0.05 implementable; SOX leg −0.22 in 2024–26. |
| Korea: gross cut when USD/KRW 20-day change > +3% | **MODIFY → FORWARD-SIM 0.75×, one-sided, honest lag** (v2.0: **RETIRED**) | R-11. v2.0: REJECT on 1997–2026 at every timing (54 strict-H.10 onsets; ΔMDD −1.3 pp; tail-exposure ratio 1.00); labelled refusal book only | N-22. R4 (value timing, gross): +0.032 (share 0.967); +0.042 on top of VT20. R4b: strict H.10 +0.001 gross; −0.008 net of KRX stock 35 bp. |
| Korea: flow weight up in foreign-buying regimes | **DROP** | Investor flows are logged from day one (KIS) | N-21. Foreigners sold ₩148.3tn in H1-2026 while KOSPI rose ≈ 101%. |
| Taiwan: same semis gate as Korea | **DROP** | — | N-18 |
| China: credit-impulse / policy-meeting gates | **BACKLOG (UNTESTED)** | China stays in the Korea covariance only | N-17 |
| India: momentum down when Brent 1-month change > +15% | **DROP** | Oil goes to the calendar and Monte Carlo | N-43, N-44 |
| EM: country momentum gated on the USD trend | **BACKLOG** (specification-fragile) | — | N-29; Q1b-C12 |
| Crypto: net liquidity, funding-rate extremes | **DROP** (net liquidity); funding rate **BACKLOG** | QUANTGEN's crypto desk already shows funding carry descriptively | N-55 |

### 2.5 Part 2 — overlay design, events, data, next steps

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| Four-state regime (trend × stress) with family multipliers per state | **DROP** | — | N-03. Book −0.07. Momentum at 1.425× into Nov-2020 (−12.0%) and 1.50× into Jul-2026 (−10.9%). |
| Market gross 0–1 from two local drivers (Korea: SOX × KRW) | **MODIFY** | v1.1: market gross = own vol target (cap 1.0) × bounded FORWARD-SIM legs. v2.0: own vol target (cap 1.0 permanent; BUILD-AS-INSURANCE on a formal PASS) composed by `min()` with the ladder; both legs retired as refusal books (R-06, R-11, R-12) | N-14, N-16, N-22 |
| Event blackout: no new positions 24 h before FOMC/BoJ/BoK/PBoC/Korean exports | **DROP** | Short intraday windows (R-10), as evaluator blocks on simulated entries | N-37, N-38. FOMC lands at 03:00/04:00 KST, so a 24 h blackout swallows the preceding KRX session. |
| Falsification: 1,000-path block bootstrap; multiplier → 1× if it fails | **MODIFY** | The nine-step gate (2,000 × 10-session blocks) plus the protective class (§8.7), deciding on the longer of 10 sessions and the Politis–White length. v2.0: PC-1′ tail legs gate, single-path drawdown is printed, objective market-own episodes (R-21, R-22) | N-50 |
| Data: CBOE via yfinance ^VIX/^VIX3M; FRED DEXKOUS as daily FX | **MODIFY** | CBOE via FRED VIXCLS/VXVCLS. H.10 FX is weekly, so production reads a timestamped 15:30:00 KST USD/KRW snapshot (`USDKRW_1530_SNAPSHOT`) or the ECOS 15:30 close. H.15 is posted the next business day at 16:15 ET, so production uses a KIS US 10y quote and strict backtests lag DGS10 by two business days. v2.0: Treasury par yields ("usually available … by 6:00 PM Eastern Time", posting time logged) make +1 business day compliant (R-12 is still a REJECT); KRW history uses the ECOS 15:30 close (§4.2) | N-46, N-47; R4 and R4b H.15 findings |
| Next steps: build the four-state classifier and the Korea SOX×KRW scalar | **DROP** | Replaced by milestones M0–M10 (§12) | — |

---

## 3. Architecture (re-mapped to QUANTGEN's packages)

### 3.1 Where the macro work lives in QUANTGEN

The map below is the architecture review's application map (§1.1 of that review). It is reduced to the parts this spec touches, and v2.0 places the council's modules R-01 to R-35 on it (§3.4 lists them all).

- `[+]` marks an extension of an existing module.
- `[new, proposed]` marks a file the sources do not show.

```
 QUANTGEN (Flet desktop app; entry point main.py; read-only: no order path)
 ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │ UI ui/*.py   Macro · Rates · Bonds · FX · Structuring │ Quant Lab · Portfolio · Signals │               │
 │              Execution · Rules · Workflows · Skills · KRX · Runs · Settings                             │
 │   [+] Macro page: macro_state panel, overlay_decision table, card verdict and disposition badges,       │
 │       relative and absolute vol labels, event calendar, context log, owner decisions D1–D5              │
 │       (proposed). No regime-model state is displayed (P19).                                             │
 └──────────────┬──────────────────────────────┬───────────────────────────────┬───────────────────────────┘
 ┌──────────────▼───────────────┐ ┌────────────▼─────────────────┐ ┌───────────▼───────────────────────────┐
 │ core/ficc                    │ │ core/quant                   │ │ core/engine · core/rules · core/skills│
 │  data   FRED|Yahoo|synthetic │ │  history FMP|KIS|synthetic   │ │  runtime DISARMED→ARMED→HALTED        │
 │   [+] PIT store (R-01):      │ │   [+] official close primary │ │   [+] HALTED per book (§3.8);         │
 │       available_at,          │ │  risk    vol, DD, VaR/CVaR   │ │       RISK re-arm after 10 sessions   │
 │       retrieved_at,          │ │   [+] vol_target (R-06),     │ │  feed    QuoteFeed via core/markets   │
 │       value_status, session, │ │       min() composition,     │ │  evaluator (rule, quote) → decision   │
 │       vintages, lag audit;   │ │       look-through caps, hard│ │   [+] BLOCKED: R-10 windows, −12%     │
 │       contracts, staleness   │ │       stop, hedge_state      │ │       step; R-08 annotates only       │
 │       by role (R-19); no     │ │  signals 6-component compos. │ │  orders  simulated order book, NO     │
 │       synthetic, no provi-   │ │   [+] family tags, priors as │ │          broker order path            │
 │       sional acting input    │ │       filters (R-15), basis  │ │   [+] fill model (R-27); books:       │
 │  macro  18-indicator sheet,  │ │  backtest costed, no look-   │ │       recommended / specification     │
 │         z-scores, regime     │ │          ahead               │ │  state   persisted trigger counts     │
 │         read, daily/weekly   │ │   [+] CARD-P v2, ledger,     │ │   [+] switch counts, forward alarms   │
 │         brief                │ │       episodes, power, timing│ │  rules   model (immutable, no fin.    │
 │   [+] macro_state,           │ │       gate (R-21–R-24, R-34),│ │          defaults), validation, store │
 │       overlay_decision,      │ │       forward alarms (R-25)  │ │   [+] rule objects (§7), owner-       │
 │       context_log (R-13),    │ │  garch, montecarlo           │ │       decision keys, DNB (R-33)       │
 │       R-18 break log         │ │   [+] estimator gate (R-30); │ │  skills  72-entry manifest, runner,   │
 │  ratesim Vasicek|CIR|HW      │ │       R-16 lab and replays   │ │          runs, workflows (YAML, gates)│
 │   [+] SEP-band rate paths    │ │                              │ │   [+] macro_daily workflow (R-35)     │
 │       (R-16)                 │ │                              │ │                                       │
 └──────────────┬───────────────┘ └────────────┬─────────────────┘ └───────────┬───────────────────────────┘
                │      core/markets (venue → provider, session) · core/calendars [+] effective-dated sessions
                │      and regime tags (R-20), publication calendars (R-19), event calendar and gap tags (R-10)
 ┌──────────────▼──────────────────────────────▼───────────────────────────────▼───────────────────────────┐
 │ Providers (read-only): KIS Open API quotes (KRX, KOSPI200 fut/opt, KTB/USD fut, KRW yields,             │
 │ US yields/indices/stocks, USD/KRW fixing, investor flows) · FRED · Yahoo · FMP · KRX marketplace        │
 │ · OpenDART · Claude API (narrative only, never decides) · gs_quant · [new, proposed] BoK ECOS           │
 │ (731Y003 15:30 close) · US Treasury par yields (posting time logged) · KRX/KOFIA leverage data          │
 │ config.py: credentials by family, ~/.nextgen/ficc_cache (6 h; read-through cache of the PIT store),     │
 │            trading dir for rules JSON, skill env  [+] macro artifact dir, cost table reference          │
 └─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
 tests/run_all.py [+] macro tests, hermetic (network touchpoints patched to raise; post-close fixtures, md5 per file)
 docs/ [+] macro_overlay_study.py → one JSON model card per rule; vol_backtest.py (B5; script and seed published)
```

### 3.2 Daily data flow (one decision per market per close)

```
 official close of t, from the effective-dated calendar (R-20):
   KRX 15:30 KST; decision_utc = close_print_bound_utc = scheduled close + 30 s (06:30:30Z from 2016-08-01;
       06:00:30Z before; CSAT close + 30 s; before 2015-06-15 scheduled close + the 30 s print tolerance)
   NYSE 16:00 ET = 20:00Z EDT / 21:00Z EST; decision_utc = scheduled close + 30 s
        │
        ▼
 core/ficc/data  [+] PIT snapshot at decision_utc (knowledge_utc pinned for the run) ── value_status / session check
        │            ── staleness by role (R-19; data_ok gate) ── lag audit (independent re-derivation of usable_at)
        │            acting input missing / stale / provisional / synthetic → its component fails closed (state carried,
        │              alert); repeated failure HALTs only the books the input is bound to (§3.8)
        │            risk_model input stale or failing → hedge_credit_off = TRUE (never HALTED) · context input stale → label
        │
        ├──► core/ficc/macro [+] context_log (never acts; isolation guard)                 ─► Macro page, weekly brief
        │
        ├──► core/quant/risk [+] σ̂ (SMA20), vt(m), sleeve_vol_scale vs, hedge_state, look-through caps, ladder state,
        │            │            compose(): vt × min(1.0, overlays, ladder, post_rearm_cap) ≥ 0.5 × vt
        │            ▼
        │    core/quant/signals [+] base weights (R-15), family overlays, exposure basis (apply_overlays)
        │    core/quant/optimize [+] inverse_vol_weights (IV_m); covariance inputs honour hedge_credit_off
        │            │
        │            ▼
        │    core/ficc/macro [+] build macro_state, overlay_decision (each factor tagged with its card verdict and disposition);
        │            │            bounds_ok then validates the built artifacts (R-32)
        ├──► core/calendars [+] event windows, KR opening-gap nights, multi-session gap tags (R-10)
        │            │
        ▼            ▼
 core/engine: evaluator (BLOCKED new entries: R-10 windows, ladder −12% step; R-08 writes an annotation only)
        │      ─► orders: simulated order book: recommended book and specification book; fills per R-27,
        │         priced at the official close of t, earning from t+1, costed per P10 (tick floor applied)
        ▼
 runtime, one state per book: DISARMED │ ARMED │ HALTED (0× for that book only; §3.8)
        │   RISK class (hard stop −15% of book NAV (D2); risk-limit breach): re-arm refused for 10 sessions, automatic
        │     re-arm (a breach: once its limit is met), references reset after a hard stop only, then post_rearm_cap 0.5
        │     inside min() for 10 sessions from the actual re-arm
        │   OPS class (acting-input failure beyond its misses, own artifact failure, lag audit, heartbeat, …): clears with its cause
        │
        ├──► forward evaluator (core/quant/backtest + core/engine/state): FORWARD-SIM books (R-28, R-29),
        │    refusal books (R-11, R-12; display only), forward alarms on whole-book NAV (R-25)
        ▼
 docs/macro_overlay_study.py + core/quant/backtest ─► model cards (frozen gate package, §8) ─► Strategy Lab
```

The workflow `core/skills/workflows/macro_daily.yaml` (§3.9, R-35) runs this pipeline after each close. It is **proposed**: the sources show that YAML workflows with decision gates exist, but not this one.

### 3.3 Exposure composition

The composition rule below is **binding** in v2.0 (R-02; QC resolution 6). The evidence fixes each factor separately. The council fixed how they combine: by `min()`, never by product, because v1.2's product form made the ladder's steps cumulative by accident (0.5 × 0.5 = 0.25 × vt; DLA-D2) and left product stacks at ≤ 0.25× total exposure on 31.0% of KOSPI days, against 11.2% under `min()` (EX1).

For market m, family f and instrument i, decided at the close of t (`decision_utc`), effective from t+1:

```
# base weights (R-15)                                      core/rules + core/quant/optimize [+]
IV_m               = inverse-vol weight of market m on weekly returns
                     (EWMA λ 0.97 acting; a Ledoit–Wolf 156-week line printed); Σ_m IV_m = 1
A_m                = { f : prior(m,f) ≥ 1  and  card(m,f).verdict ≠ REJECT }      # admissible families
base_weight(m,f)   = IV_m × 1/|A_m|  if f ∈ A_m, else 0                          # Σ_f base_weight(m,f) = IV_m
                   # R-15: a range prior resolves to its lower bound; a family with no registered prior is not
                   # admissible; ts_trend is admissible in the recommended book only on its own PASS (R-14)

# family level (exposure_basis = active)                   core/quant/signals [+]
active_budget(m,f) = base_weight(m,f)
                   × vs(m,f)                               # own-vol scale, in [0,1] (R-03; momentum only, else 1.0)
                   × min(1.0, family_overlay_1(m,f), …)    # each in [0.5,1]; empty = 1.0 (R-04: specification book only)

# market level (exposure_basis = total)                    core/quant/risk [+]
composed(m)        = vt(m)                                 # market vol target, in [0,1] (R-06)
                   × min(1.0, gross_overlay_1(m), …, ladder(m), post_rearm_cap(m))   # each in [0.5,1]; ladder, post_rearm_cap ∈ {1.0, 0.5} (R-07, R-31)
gross(m)           = min(composed(m), concentration_bound(m))     # look-through limit (R-07); a risk limit, not an overlay
# HALTED (a RISK or OPS trigger of this book, §3.8) sets this book to 0×; it is never an argument of min(); other books continue

target_weights     = composite_weights(i | active_budget, gross)               # core/quant/signals
final_weights      = risk_layer(target_weights)              # caps, single-name active cap; hedge_state (risk model only)
simulated_orders   = engine.orders(final_weights)            # recommended and specification books (§3.8)
```

**Invariant (T-CAP-02).** For any overlay vector in [0.5, 1]^k, ladder step in {1.0, 0.5} and post-re-arm cap in {1.0, 0.5}, composed(m) = vt(m) × min(1.0, overlays, ladder, post_rearm_cap), and composed(m) ≥ 0.5 × vt(m) on every non-HALTED day (written as a product, so vt = 0 needs no division). The floor applies to composed(m): a concentration bound or risk-layer cap may take gross(m) lower without a bounds failure. A product-composed path raises: `bounds_ok` recomputes composed(m) from the recorded factors, and the rules store refuses `combine ≠ min`.

**Invariant (T-MONO-01): no reallocation.** Lowering any multiplier (vt, vs, an overlay, the ladder, the post-re-arm cap, a concentration bound) never raises gross(m′), active_budget(m′, f′) or the active risk of any other market m′ or family f′, and never raises gross(m) or active_budget(m, f) itself. `composite_weights` and `risk_layer` never renormalise freed budget across families or markets: freed active budget moves toward the benchmark (long-only) or zero (long/short), and freed total exposure moves to cash. The one documented exception is R-15's admissibility rule: a family-card REJECT shrinks K_m and raises the other families' base weights by K/(K−1) from the next decision; it is logged as a governance event and printed.

**Books (P0, P7).**
- **Recommended book.** It applies only the factors whose card is PASS: disposition `RECOMMENDATION` (CARD-O) or `BUILD_AS_INSURANCE` (CARD-P). Every other factor enters as 1.0. The invariants always apply: point-in-time data, bounds, look-through caps, the hard stop and the hedge state. R-31 steps with a binding share ≤ 0.10 act here as part of the R-07 invariant (disposition `INVARIANT_STEP`, R-31). This is the only book whose weights are shown as a recommendation. While R-06 KR is NOT_RUN, vt enters as 1.0, so the Korea recommended book's gross is set by the concentration bound (§11).
- **Specification book.** It applies every BUILD NOW factor, whatever its verdict, labelled with each factor's verdict. That includes the specification-only factors: R-04 at floor 0.5, and the R-31 ladder steps while they bind on more than 10% of days.
- **FORWARD-SIM books.** Each FORWARD-SIM card (R-28, R-29) runs its own forward book: the specification book with that card's factor applied, on the card's declared instrument book and notional.
- **Refusal books.** R-11 and R-12 may persist as labelled, display-only books. No recommended or specification book reads their multipliers (I-03).
- **Stack card (R-02).** Once two or more de-risk factors act in the recommended book, the book is gated as one stack CARD-P (§8.7). It prints the share of days at ≤ 0.25× total exposure and the rebound capture. Each new overlay is judged incrementally on the current recommended book (P17).

**Notes on the formula:**
- **Active budget.** Scaling a long-only sleeve's active budget moves weights toward the benchmark, not toward cash. Scaling a long/short sleeve moves it toward zero. For a long-only momentum sleeve, vs is computed on the paper unit-gross long/short series and applied to the active budget (R-03).
- **What `vt(m)` covers.** It scales the market's long book. It does **not** scale long/short factor sleeves, which have their own `vs(m,f)`. It does **not** scale the TS-trend sleeve, which is vol-scaled per asset and exempt from overlays (R-14).
- **Instrument book.** In Korea, `vt(m)` is implemented on the KRX ETF line (KODEX 200, 3 bp, tick floor applied). A KOSPI200 futures line is allowed only where one mini contract (≈ ₩56m) is ≤ ~5% of the declared notional. A stock book is never used as a market-gross scalar (R-26). The card declares its book before it is run (P10, P15).
- **Concentration bound.** On the ETF line, a binding look-through limit is met by lowering the line's weight: g ≤ limit_k / look-through share_k (R-07). On 2 Oct 2026, under the default template (D1, MSCI 25/50), the absolute single-name bound is 22.5 / 29.8 = 0.755 and the active single-name bound is 0.05 / (0.298 − 0.225) = 0.685 (an upper bound: it takes b̃ for Samsung at the 22.5% cap; the risk layer computes b̃ on the day's basket). Both are printed per book (§11): at vt 0.694 the active bound binds in the specification book; in the recommended book, where vt enters as 1.0 while R-06 KR is NOT_RUN, both bounds bind, the active one first.
- **Binding is logged.** Whenever `min()` or a limit binds, the binding factor is recorded in `overlay_decision.reasons`. Each card prints the binding share of every factor.

### 3.4 Module map

**v1.0 component → QUANTGEN package** (kept for traceability; v2.0 changes in the third column):

| v1.0 component | QUANTGEN package (exists per the sources) | What v1.1 / v2.0 add | Status |
|---|---|---|---|
| `data_layer/registry.yaml`, `ingest.py` | `core/ficc/data` (FRED, Yahoo, synthetic; explicit provider that fails raises); `core/quant/history` (FMP, KIS, synthetic); provider clients (e.g., `kis_client.py`) | Series registry (§4.2) as a data file next to `core/ficc/data`, with publication schedules and roles (v2.0, R-19). New providers: BoK ECOS (731Y003, USD/KRW 15:30 KST close) and US Treasury par yields (v2.0) | registry file **proposed**; ECOS and Treasury **proposed** |
| `timestamps.py`, `pit.py`, `vintages.py`, `lag_audit.py` | `core/ficc/data` | `PITValue` v2 and `pit_value()` (§3.5): `available_at`, `retrieved_at`, `value_status`, `session_date`, vintages and first prints; append-only as-of reads; provisional-row guard; two-source close reconciliation; lag audit; **no synthetic degrade for acting inputs** (R-01) | functions **proposed** inside the existing package |
| `context/context_log.py` | `core/ficc/macro` (18-indicator sheet, z-scores, regime read, daily/weekly brief) | `context_log` builder with vintages (R-13); reconciliation of the existing sheet (§3.6); `macro_state` and `overlay_decision` builders; R-18 break log | builders **proposed** |
| `vol/estimators.py`, `vol/targets.py` | `core/quant/risk` (vol, drawdown, 1-day VaR/CVaR; `risk.py` is cited in the review) | `sma_vol`, `ewma_vol`, `market_vol_target()`, `sleeve_vol_scale()`, relative and absolute display labels (R-06); estimator registry and challenger COMB (R-30, `core/quant/garch`) | **proposed** functions |
| `overlay/family.py` (D&M), `overlay/bounds.py` | `core/quant/signals` (6-component composite) | Family tags, `dm_gate()` (specification book only), bounds, exposure-basis validation, `min()` composition and binding log (R-02), base weights (R-15) | **proposed** |
| `overlay/market_gross.py` (S1, S2) | `core/quant/risk` + `core/engine/orders` | v2.0: S1 and S2 retired; at most display-only refusal books (R-11, R-12) | **proposed** |
| `overlay/hedge_state.py` | `core/quant/risk` (and `core/quant/optimize`, which uses covariances) | `hedge_state()` with date-aligned corr63; `max(corr, 0)` for equity–duration pairs when `hedge_credit_off`; stale risk-model input → `hedge_credit_off`; display-only `fx_hedge_credit` (R-09) | **proposed** |
| Korea caps, drawdown ladder | `core/quant/risk`; `core/engine/runtime`, `core/engine/evaluator` | v2.0: caps on look-through with an active single-name cap and an owner template (R-07, D1); hard stop with explicit re-arm (R-07, D2); steps time-boxed and composed by `min()` (R-31) | **proposed** |
| `events/calendar.py`, `events/entry_blocks.py` | `core/calendars`; `core/markets` (venue → provider, suffix, currency, session); `core/engine/evaluator` | Event store with status; window generator; KR opening-gap nights and multi-session gap tags (R-10); effective-dated sessions and regime tags (R-20); `usable_at()`; BLOCKED evaluator decisions; R-08 annotation | **proposed** |
| `falsification/*` (registry, trials, bootstrap, DSR, PBO, episodes, shadow book, report) | The existing gate (nine steps, four verdicts, model cards with md5) and `core/quant/backtest` (costed, no look-ahead) | v2.0 gate package: CARD-P v2 (R-21), evaluation conventions (R-22), family ledger and N_eff (R-23), statistics and power (R-24), forward monitoring (R-25), timing gate (R-34); overlay-on vs overlay-off on the same costed engine; static same-exposure comparator S | harness **proposed**; the gate itself **exists** |
| `schemas/*.schema.json` | (none shown) | JSON Schemas 2.0 of §6 next to the builders (R-32) | **proposed** |
| `config/macro.yaml` | `core/rules` (immutable model, no financial defaults, validation, one JSON store with edit history); `config.py` | Rule objects in the rules store (§7), owner-decision markers, cost-table reference and instrument metadata (R-26), DO-NOT-BUILD validation (R-33) | **proposed** entries |
| Daily run | `core/skills` (72-entry YAML manifest, runner as subprocess with env-only credentials, runs, workflows as YAML pipelines with decision gates) | Macro skills and `workflows/macro_daily.yaml` (§3.9, R-35) | **proposed** |
| Study scripts | `docs/` (`build_models_primer.py`, `drift_study.py`; `asset_expansion_study.py` writes one JSON card per model) | `docs/macro_overlay_study.py` (one JSON card per rule, v2 gate package); `docs/vol_backtest.py` for B5 and the estimator harness, published with its seed (R-30, BL-G01) | **proposed** |
| Tests | `tests/run_all.py`: engine + quant + FICC acceptance, hermetic (network touchpoints patched to raise) | Macro unit, integration and golden tests on frozen post-close fixtures (§9) | **proposed** |

**v2.0 module map (`QC_modules.csv`).** Every council module, where it lives, and where this file specifies it. R-05 is unchanged and keeps its v1.2 place.

| Module | Short name | Package / module | Change · class · priority | Milestone | Specified in |
|---|---|---|---|---|---|
| R-01 | Point-in-time discipline | `core/ficc/data`; `core/quant/history`; `tests/run_all.py` | CHANGED · INVARIANT · P0 | M1 | §4.1, §5 R-01 |
| R-02 | Bounds and `min()` composition; stack card | `core/quant/signals`; `core/quant/risk`; `core/rules` | CHANGED · INVARIANT · P0 | M2 | §3.3, §5 R-02 |
| R-03 | Momentum own-vol scaling | `core/quant/risk` (`sleeve_vol_scale`); `core/quant/signals` | CHANGED · CARD-O · P0 | M4 | §5 R-03 |
| R-04 | Daniel–Moskowitz gate | `core/quant/signals` (`dm_gate`) | DEMOTED · CARD-O · P1 | M4 | §5 R-04 |
| R-05 | Reversal and quality at 1.0× | `core/quant/signals` | unchanged · CONVENTION | M4 | §5 R-05 |
| R-06 | Per-market vol target | `core/quant/risk` (`market_vol_target`); `core/quant/backtest` | CHANGED · CARD-P · P0 | M7 (function in M2) | §5 R-06 |
| R-07 | Look-through caps; hard stop with re-arm | `core/quant/risk`; `core/engine` (runtime, evaluator); `core/rules` | CHANGED · INVARIANT · P0 | M5 | §5 R-07 |
| R-08 | VIX ≥ VIX3M annotation | `core/engine` (evaluator annotation); `core/ficc/macro` | DEMOTED · CONVENTION · P1 | M5 | §5 R-08 |
| R-09 | Hedge-validity state | `core/quant/risk` (`hedge_state`); `core/quant/optimize` | CHANGED · INVARIANT · P1 | M2 | §5 R-09 |
| R-10 | Event calendar and gap tags | `core/calendars`; `core/quant/risk` (display) | CHANGED · CONVENTION · P1 | M5 | §5 R-10, §6.3 |
| R-11 | USD/KRW leg (S1) | `core/quant/risk` (`fwd_krw_leg`); `core/engine` (books) | RETIRED · CARD-P · P1 | M8 | §5 R-11 |
| R-12 | US rates leg (S2) | `core/quant/risk` (`fwd_rates_leg`); `core/engine` (books) | RETIRED · CARD-P · P1 | M8 | §5 R-12 |
| R-13 | Context log | `core/ficc/macro` (`build_context_log`); `core/ficc/data` | CHANGED · CONTEXT · P1 | M6 | §5 R-13, §6.4 |
| R-14 | TS-trend sleeve | `core/quant/signals` | CHANGED · CARD-O · P2 | M7 | §5 R-14 |
| R-15 | Priors as admissibility filters | `core/rules`; `core/quant/signals`; `core/quant/optimize` | CHANGED · CONVENTION · P0 | M4 | §3.3, §5 R-15 |
| R-16 | Quant Lab | `core/quant/garch`; `core/quant/montecarlo`; `core/ficc/ratesim` | CHANGED · CONTEXT · P1 | M9 | §5 R-16 |
| R-17 | Planned sleeves | `core/calendars`; `core/rules` | CHANGED · CONVENTION · P2 | M10 | §4.1, §5 R-17 |
| R-18 | Policy and scale breaks | `core/ficc/macro`; `core/calendars`; `core/rules` | CHANGED · GOVERNANCE · P2 | M6 | §5 R-18 |
| R-19 | Data contracts and staleness by role | `core/ficc/data`; `core/calendars`; `core/engine` (runtime) | NEW · INVARIANT · P0 | M1 | §4.1, §4.2, §5 R-19 |
| R-20 | Effective-dated calendars and regime tags | `core/calendars` | NEW · INVARIANT · P0 | M1 | §4.1, §5 R-20 |
| R-21 | CARD-P gate v2 | `core/quant/backtest`; `core/rules` | NEW · GOVERNANCE · P0 | M7, frozen first | §5 R-21, §8 |
| R-22 | Evaluation conventions | `core/quant/backtest`; `core/rules` (registry) | NEW · GOVERNANCE · P0 | M7, frozen first | §5 R-22, §8 |
| R-23 | Family trial ledger and N_eff | `core/quant/backtest`; `core/rules` | NEW · GOVERNANCE · P0 | M7, frozen first | §5 R-23, §8 |
| R-24 | Statistics and power harness | `core/quant/backtest` | NEW · GOVERNANCE · P0 | M7, frozen first | §5 R-24, §8 |
| R-25 | Forward monitoring and demotion v2 | `core/engine` (state); `core/quant/backtest` | NEW · GOVERNANCE · P0 | M8 | §5 R-25, §8 |
| R-26 | Instrument book, notional, cost realism | `core/rules` (cost table, instrument metadata); `core/quant/backtest` | NEW · INVARIANT · P0 | M0 | P10, §5 R-26 |
| R-27 | Simulated fill model | `core/engine` (orders) | NEW · CONVENTION · P2 | M5 | §3.8, §5 R-27 |
| R-28 | Trend-axis protective card | `core/quant/signals` (gross overlay); `core/quant/backtest` | NEW · CARD-P · P1 | M8 | §5 R-28 |
| R-29 | MACRO-R06-US-FUT | `core/quant/risk`; `core/quant/backtest` | NEW · CARD-P · P1 | M8 | §5 R-29 |
| R-30 | Estimator selection gate and harness | `core/quant/garch`; `core/quant/backtest` (loss registry, MCS) | NEW · GOVERNANCE · P1 | M3 | §5 R-30 |
| R-31 | Drawdown step-down card | `core/quant/risk` (`drawdown_ladder`); `core/engine` (evaluator) | NEW · CARD-P · P1 | M7 | §5 R-31 |
| R-32 | Schemas v2 | `core/ficc/macro` (schemas); `core/rules` | CHANGED · GOVERNANCE · P0 | M0 | §6, §5 R-32 |
| R-33 | DO-NOT-BUILD v2 | `core/rules` (validation); `docs` | CHANGED · GOVERNANCE · P1 | M0 | §10, §5 R-33 |
| R-34 | Timing-fragility gate | `core/quant/backtest`; `tests/run_all.py` | NEW · GOVERNANCE · P0 | M7, frozen first | §5 R-34, §8 |
| R-35 | `macro_daily` workflow gates | `core/skills` (`workflows/macro_daily.yaml`) | CHANGED · GOVERNANCE · P1 | M8 | §3.9, §5 R-35 |

### 3.5 Core interfaces

These are binding in semantics; the rule texts (R-xx) bind any detail not shown here. Rename them to match the codebase if necessary. Every location is **proposed** unless the comment says "exists".

```python
# core/ficc/data  (exists; these types and functions proposed)  — R-01, R-19
@dataclass(frozen=True)
class PITValue:
    series_id: str
    value: float
    obs_date: date                    # market or local date the value refers to (monthly series: first day of the month, §4.1)
    session_date: date | None         # exchange session the value belongs to (required for close-type inputs)
    obs_utc: datetime                 # when the observation was made (e.g. the scheduled close)
    obs_kind: Literal["close", "quote_snapshot", "release", "bar", "derived"]   # "close-type" means obs_kind == "close"
    value_status: Literal["official_close", "vendor_close", "live_snapshot", "provisional_intraday", "first_release",
                          "revised", "vendor_derived", "vendor_derived_across_gap"]
    dispute: bool                     # True: official value used, two-source mismatch alerted (R-01 (3)); never a failure
    available_at_utc: datetime        # when the market or publisher released it
    available_at_source: Literal["published", "calendar_bound", "inferred_from_retrieval"]
    retrieved_at_utc: datetime        # when QUANTGEN first saw it (knowledge clock; first-seen, §4.1)
    vintage: date | None              # FRED/ALFRED realtime_start of this value; None for unrevised market prices
    source: str                       # provider: KIS, KRX, FRED, ALFRED, Treasury, ECOS, Yahoo, FMP
    channel: str | None               # e.g. "H.15", "Treasury par yield", "ECOS 731Y003/0000003", "KIS live"
    provider_mode: Literal["explicit", "auto"]
    synthetic: bool                   # True is never accepted for an acting input -> MissingInput
    content_hash: str                 # md5 of the record; feeds data_snapshot_id
    role: Literal["acting_exposure", "forward_sim", "risk_model", "context", "history"]   # of the calling consumer's binding (§4.2, R-19 rule 5)
    books: tuple[str, ...]            # the books that binding feeds: the HALT scope (§3.8)

@dataclass(frozen=True)
class MissingInput:
    series_id: str
    reason: Literal["missing", "stale", "provisional_intraday", "session_mismatch",
                    "synthetic_rejected"]          # "disputed" and "warmup" are statuses of a used value, never failures
    role: Literal["acting_exposure", "forward_sim", "risk_model", "context", "history"]
    books: tuple[str, ...]

def pit_value(series_id: str, decision_utc: datetime, knowledge_utc: datetime, consumer: str,
              require_session: date | None = None) -> PITValue | MissingInput
#   as-of read of an append-only store: only records with available_at_utc <= decision_utc and
#   retrieved_at_utc <= knowledge_utc are visible; corrections are new rows. knowledge_utc is pinned once per run and
#   never defaults to "now" (run_mode live: the end of the pit_snapshot fetches; backtest: the card's data snapshot;
#   replay: the artifact's knowledge_utc); it is written to every artifact. consumer selects the binding (role, books).
#   Among the visible rows of one (series_id, obs_date): the highest value_status rank (official_close > revised >
#   first_release > vendor_close > vendor_derived > vendor_derived_across_gap > live_snapshot > provisional_intraday), then registry source
#   precedence, then the latest available_at_utc, then the latest retrieved_at_utc.
#   A close-type acting read returns MissingInput("provisional_intraday") unless value_status == "official_close"
#   (any other status), and MissingInput("session_mismatch") unless session_date == require_session (T-PROV-01).
#   A close-type read selects among the visible rows with obs_date == require_session: none visible -> MissingInput("missing")
#   (T-PROV-01 at 10:31 KST, even when the previous session's close is visible); session_mismatch means the selected row
#   carries another session_date (a mis-dated row).
#   require_session is mandatory for close-type acting reads (calling without it raises). A backtest may read
#   vendor_close rows only when its card header declares that vendor as data.source (§4.1).
def data_snapshot_id(knowledge_utc: datetime) -> str    # md5 of the sorted content hashes visible at knowledge_utc
def expected_available_utc(series_id: str, last_obs: date) -> datetime   # R-19 step 3: when the NEXT observation after
                                                        # last_obs is due = publication_instant(series, next_expected_obs(series,
                                                        # last_obs)); never the availability of last_obs itself
def is_stale(series_id: str, decision_utc: datetime, knowledge_utc: datetime) -> StaleCheck   # Fresh | Stale("missing") | Stale("missed_release")
#   stale iff decision_utc > stale_deadline_utc = expected_available_utc(series, last_obs) + grace (one publication
#   business day): the due time of the next observation, never the age of last_obs (R-19 step 3 is normative)
# further R-19 functions: contract, on_input_failure, usable_cross_market, pit_last, add_publication_bdays

# core/calendars (exists; these functions proposed)  — R-20, R-10, R-17
def decision_time_utc(market: str, session_date: date) -> datetime   # the scheduled official close, NOT decision_utc (that is
                                                                      # close_print_bound_utc); API unchanged from v1.2: KR 06:00Z before
                                                                      # 2016-08-01, 06:30Z after; CSAT close per calendar (07:30Z from
                                                                      # 2016-08-01); US 20:00Z / 21:00Z, early closes 13:00 ET (17:00Z
                                                                      # EDT / 18:00Z EST); CRYPTO 00:00:00Z of d+1 (R-17)
def close_print_bound_utc(market: str, session_date: date) -> datetime   # scheduled close + print bound: KR from 2015-06-15
                                                                      # + 30 s (06:00:30Z to 2016-07-29, 06:30:30Z after, CSAT close + 30 s);
                                                                      # KR before 2015-06-15 + the 30 s print tolerance; US + 30 s
                                                                      # (calendars.US.close_print_bound_s); JP, CN, HK, TW + their
                                                                      # calendars.<m>.close_print_bound_s (0 s default); the decision instant
                                                                      # (macro_state.decision_utc) and the lag-audit instant
# further calendar functions (is_session, session, fed_business_day, sifma_status, nyse_holiday,
# publication_instant, next_expected_obs): R-20. Market identifiers are the §6.1 enum (KR, US, JP, …, CRYPTO, FX);
# venue codes (KRX, NYSE, TSE) are used only inside core/markets.
def usable_at(series_id: str, obs_date: date, market: str) -> datetime  # first decision_utc that may use it (§4.1)
def regime_tags(market: str, d: date) -> dict          # price_limit, saturday_session, close_time, random_end,
                                                        # short_ban, fx_regime, sell_tax, lunch_break (R-20)
def gap_sessions(market: str, session_date: date) -> int   # n_US >= 0: US sessions since the previous KRX close (R-10)

# core/quant/risk (exists: risk.py; these functions proposed)
def market_vol_target(market: str, decision_utc: datetime, estimator: str = "sma20") -> VTResult
#   sigma_ann, weight in [0,1] (cap 1.0 permanent), display_label_rel, display_label_abs, inputs, status (R-06):
#   fewer than 20 valid returns -> status "insufficient_history"; each book it feeds maps that to "warmup", weight 1.0, before the
#   book's first ARMED decision and to MissingInput("missing") afterwards (T-VT-01); sigma 0 or not finite -> MissingInput
def sleeve_vol_scale(market: str, family: str, decision_utc: datetime, revision: int) -> VSResult
#   sigma126 on the paper unit-gross long/short series; revision selects fixed / scale-free / variance-scaled (R-03);
#   fewer than 126 valid observations -> "insufficient_history", mapped per book as above (vs = 1.0 "warmup", then MissingInput)
def hedge_state(decision_utc: datetime) -> HedgeState  # hedge_credit_off, hedge_failure, classic_risk_off,
                                                       # fx_hedge_credit (display only), stale inputs (R-09)
def lookthrough_exposure(book: Book, decision_utc: datetime) -> Exposure   # daily ETF baskets; L/I ETFs at × L (R-07)
def concentration_bound(market: str, decision_utc: datetime, template: str) -> ConcentrationBound   # {absolute_bound, active_bound, aggregate_bound, semis_bound, bound = their min, binding_factor}; per book: gross = min(composed, bound), binding_factor 'none' when composed <= bound (R-07)
def drawdown_ladder(nav_path, decision_utc: datetime) -> LadderState
#   LadderState{hwm_hard, ref_step, step_mult in {1.0, 0.5}, dwell_left, block_new_entries: bool, halted: bool,
#               rearm_not_before, post_rearm_left, binding_share}  (R-07, R-31; R-31's names are binding)
def compose(vt: float, overlays: list[float], ladder: float, post_rearm_cap: float) -> float   # vt * min([1.0] + overlays + [ladder, post_rearm_cap]); raises on product

# core/quant/signals (exists; these functions proposed)
def base_weights(decision_utc: datetime) -> dict[tuple[str, str], float]   # IV_m * 1/K_m over admissible families (R-15)
def dm_gate(market: str, decision_utc: datetime) -> Multiplier             # value in {0.5, 1.0}; specification book only (R-04)
def apply_overlays(composite, multipliers, basis) -> Weights               # bounds P2, min() composition, basis P8, binding log

# core/quant/optimize (exists; this function proposed)
def inverse_vol_weights(markets: list[str], decision_utc: datetime, cov: str = "ewma_weekly_0.97") -> dict[str, float]

# refusal books (core/quant/risk; proposed). Display only; no other book may read them (I-03)
def refusal_krw_leg(decision_utc: datetime) -> Multiplier     # R-11; value in {0.75, 1.0}; status="REFUSAL"
def refusal_rates_leg(decision_utc: datetime) -> Multiplier   # R-12; value in {0.5, 1.0};  status="REFUSAL"

# core/ficc/macro (exists; these builders proposed)
def build_macro_state(market: str, decision_utc: datetime) -> dict      # validates against macro_state 2.0
def build_overlay_decisions(market: str, decision_utc: datetime) -> list[dict]
def build_context_log(decision_utc: datetime) -> dict                   # items carry vintage and retrieved_at_utc
def log_break(event: BreakEvent) -> None                                 # R-18 break log (research log, never read by acting code)

# core/engine (exists; these hooks proposed)
def evaluator_block(rule_id: str, decision: Decision, state: MacroState) -> Decision   # → BLOCKED(reason), new entries only
def evaluator_annotate(rule_id: str, state: MacroState) -> Annotation                  # R-08: annotation + KIS snapshot request
def runtime_halt(book_id: str, cls: Literal["RISK", "OPS"], reason: str) -> None   # → HALTED for that book only; idempotent per cause; a new cause joins halt.causes[]
                                                   # while HALTED (never extends rearm_not_before, never resets a reference);
                                                   # logged as a governance event (§3.8)
def runtime_rearm(book_id: str, mode: Literal["auto", "operator"], operator: str | None = None) -> None
                                                   # RISK: auto at the decision after the 10-session refusal, references reset,
                                                   # 0.5× inside min() for 10 sessions; OPS: when the cause clears, no reset, no cap
def simulated_fill(order: SimOrder, venue: str, session_date: date) -> SimFill          # R-27 fill model

# core/quant/backtest (exists; these functions proposed) — the v2 gate package (§8)
def overlay_card_eval(card: CardHeader, ledger: FamilyLedger) -> CardResult  # on/off books, comparator S, v2 checks
def episodes(market: str, rule: str = "bear_bull_own_closes", threshold: float = 0.20) -> list[Episode]  # R-22
def family_ledger(family_id: str) -> FamilyLedger      # every configuration ever run, with timing class; ledger_hash
def n_eff(ledger: FamilyLedger, draws: int = 200_000, seed: int = 11) -> NResult   # max(N_clusters, N_equiv) (R-23)
def timing_profile(card: CardHeader) -> TimingProfile  # L in {-1, 0, 1, 2, 3} + publication-strict; the L <= 0 rows run
                                                       # only in the timing_probe sandbox (R-34)
def power_line(card: CardHeader) -> PowerLine          # SE ladder, MDE80, power (R-24)
def gate_acceptance_test(package_version: str) -> AcceptanceResult   # run once; results md5-frozen (R-21)
def forward_monitor(card_id: str, book_nav) -> list[Alarm]           # whole-book NAV; calibrated alarms (R-25)

# core/quant/garch + core/quant/backtest (forecast evaluation; proposed) — R-30
def estimator_gate(market: str, instrument_book: str, horizon: int = 21) -> EstimatorSelection
```

**Rules every interface must follow:**
- Every function takes `decision_utc` and the run's pinned `knowledge_utc` (R-01; as parameters or in one `RunContext{decision_utc, knowledge_utc, run_mode}`, never "now") and reads data only through `pit_value`, with `consumer` = the binding's `consumer` key in `data_contracts.roles`: a rule id such as 'R-06', or a named component such as 'corr63' (R-09), 'korea_covariance', 'nav', 'nav_fx' or 'R-28_R-29'; an entry without a `consumer` key binds every consumer of the series, and a bare book kind in `books` means that kind's book in the series' market. The one exception is R-34's `timing_probe` sandbox (P5).
- No function reads a raw DataFrame of a series directly. The lag audit enforces this.
- **Missing, stale, provisional or synthetic inputs, by role (R-19):**
  - an **acting** input makes the function return the previous state with the component's `fail_closed = true` and the input's status code, and raise an alert; it never interpolates. Status codes: `MissingInput.reason` missing / stale / provisional_intraday / session_mismatch / synthetic_rejected maps to `macro_state.inputs[].status` missing / stale_missed_release / provisional_rejected / session_mismatch / synthetic_rejected (the §6.1 enum; the same map applies to risk_model and forward_sim inputs, and a stale context input is `stale`); R-19's `Stale("missing")` and `Stale("missed_release")` map to missing and stale_missed_release. Only these statuses count as failures;
  - a **risk-model** input makes `hedge_state` return `hedge_credit_off = TRUE`; so does an exception inside `hedge_state` (never HALTED);
  - a **context** input is labelled "stale" (status `stale`, value shown).
- **Warm-up (before a book's first ARMED decision) and disputes are not failures.** A warm-up returns the factor's neutral value (1.0) with status `warmup` only while the book has never been ARMED; on a book that has been ARMED, fewer valid observations than the factor's minimum is `MissingInput("missing")`, a failure, so a store loss or a truncated history never resets a de-risk factor to 1.0; a disputed official close returns the official value with `dispute = true` and status `disputed`. Neither increments a consecutive-failure counter (R-19).
- No function in this list may import an order-submission client (T-RO-01).
- No acting function may read `context_log`, the R-18 break log or a refusal book (T-CTX-01, I-03).

### 3.6 Reconciliation with the existing macro sheet (`core/ficc/macro`)

**What exists.** An 18-indicator sheet, z-scores, a "regime read" and a daily/weekly brief.

**What the sources do not give.** The list of the 18 indicators, the z-score windows and the regime-read method. The reconciliation below is therefore given as **rules plus a proposed mapping**. It must be completed against the actual indicator list (backlog BL-G06).

**Rules (binding):**
1. **Every indicator in the sheet becomes a CONTEXT item.** It is logged in `context_log` with `obs_date`, `available_at_utc`, `retrieved_at_utc`, `vintage` and source, unless it is one of the acting or risk-model inputs below.
2. **Z-scores stay display-only.** They are computed causally, on expanding or trailing windows ending at `decision_utc`, and never thresholded for exposure (P6, P9).
3. **The regime read (v2.0, P19).**
   - If BL-G06 finds that the regime read comes from a regime model (Markov switching, HMM, jump model, mixture or change-point), it is removed from every page in v2.0.
   - Otherwise it may stay in the brief as a descriptive text summary of the indicators, computed causally from filtered values. It is never presented as a regime state, never reuses the calm / normal / elevated / stressed names (they belong to R-06's volatility labels), and never feeds `core/quant/signals`, `core/quant/risk` or the engine.
4. **The brief gains a macro_state section.** It shows:
   - the vt and vs weights and the relative and absolute vol labels;
   - the flags and annotations;
   - each card's verdict and disposition;
   - FORWARD-SIM cards and refusal books, marked "not a recommendation";
   - the open owner decisions;
   - the event calendar.

**Acting and risk-model inputs, the only series that feed sizing or the risk model:**

| Input | Role (R-19) | Feeds | Rule |
|---|---|---|---|
| KOSPI and S&P 500 (or US sleeve) official closes | acting_exposure, bound to its market's specification book, and to its recommended book only once that market's vt card is PASS (the US close is bound to no book while D5 = none; R-19 rule 5) | `vt(m)` via SMA20 σ̂ | R-06 |
| Momentum sleeve daily returns (paper unit-gross long/short series) | acting_exposure, specification book until R-03 PASSes | `vs(m, momentum)` | R-03 |
| Market 24-month return and 126-day realised vol | acting_exposure (specification book only) | D&M gate | R-04 |
| Samsung + SK hynix and KOSPI market caps; daily KODEX 200 basket (PDF) from KIS or KRX | acting_exposure | look-through caps (risk layer) | R-07 (invariant) |
| Core PCE YoY; stock–bond corr63 on date-aligned pairs; labelled live broad-USD proxy | risk_model | `hedge_state` (risk model only; no exposure effect; never HALTs) | R-09 (invariant) |
| Monthly index closes of a US or other non-Korean sleeve | forward_sim (FORWARD-SIM book only; never HALTs another book) | trend-axis card | R-28 |

**Inputs that act on nothing:**
- VIXCLS / VXVCLS feed the R-08 annotation (context role; no exposure effect).
- USD/KRW (ECOS 15:30 close or a timestamped 15:30:00 KST snapshot) feeds the R-11 refusal book (context role) and is the `nav_fx` series of non-KRW books (R-26, R-29), bound with the role of the book it values (R-19 rule 5).
- The US 10y (KIS quote; Treasury par yields for history) has two bindings: `risk_model` for corr63 and `context` for the R-12 refusal book (R-19 rule 5).

**Proposed mapping of typical sheet indicators.** This applies if and only if an indicator is present in the sheet:

| Indicator class | Role in v2.0 | Why |
|---|---|---|
| Policy rates (Fed funds, BoK, BoJ), 2y, 10y, 30y, curve slopes (10y–3m, 10y–2y) | CONTEXT; the 10y is also a risk-model input to corr63 and the R-12 refusal book's input | N-11, N-30 |
| Real yields, breakevens, 5y5y, term premium | CONTEXT | N-26 |
| Credit spreads (HY OAS, Baa−10y) | CONTEXT | N-13 (BL-C03) |
| Broad USD, DXY, USD/JPY, USD/KRW | CONTEXT (DTWEXBGS included). The labelled live USD proxy is a risk-model input to `hedge_state`. USD/KRW feeds only the R-11 refusal book | N-29, N-22; QF2-A3 |
| Oil (named series), gold, copper | CONTEXT; oil feeds Monte Carlo scenarios and replays | N-43, N-44 |
| VIX, VIX3M, MOVE, VKOSPI | CONTEXT. VIX/VIX3M feed the R-08 annotation (no exposure effect) and are logged live at 16:00 ET; KOSPI200 MFIV is logged at 15:30 KST (R-13) | N-04; QF6-M6 |
| CPI, core PCE, unemployment, payrolls, claims, Sahm | CONTEXT with first prints and vintages (Sahm computed in-house; a gap gives NaN); core PCE is a risk-model input to `hedge_state` | N-30, N-28; QF2-M6 |
| PMI, GDP, surveys, Street forecasts | CONTEXT (forecasts never as inputs) | N-56 |
| Leverage and flow (margin debt, leveraged-ETF AUM, investor flows), VRP, turbulence and absorption ratio | CONTEXT (R-13); turbulence may enter a stressed covariance only through a pre-registered test against the stock–bond-regime input | QF4-M8, QF6-M10, QF5-M7 |

### 3.7 Reconciliation with the signal composite (`core/quant/signals`)

**What exists.** A 6-component composite. Its components are not listed in the sources.

**Rule (binding).** Overlays attach to components through a **family tag**: momentum, reversal, flow, quality or ts_trend. A component with no family tag receives no family overlay (multiplier 1.0) and is still subject to `vt(m)` and the risk layer. A family receives a base weight in market m only if it is admissible there: its prior is ≥ 1 and its card is not REJECT (R-15). The mapping of the six components to families is **proposed** and must be filled from the code (backlog BL-G07).

**Implication.** Overlays never create a new component and never change a component's sign (P1).

### 3.8 Engine mapping (simulated order book, runtime states, evaluator decisions)

| Concept | QUANTGEN mechanism (v2.0) |
|---|---|
| "Execution", "orders", "positions" | `core/engine/orders`: the simulated order book. **Primary convention:** a daily decision is taken on the official close of t and earns from t+1 (QUANTGEN rule 02). Every simulated fill is charged the pre-registered cost, with the tick floor applied (P10). **Fill model (R-27):** <br>• KRX daily weights fill at the official close (closing call; random end ≤ 30 s). The executable variant, a ≈ 15:19 KST decision snapshot filled at the close, is printed as a tracking-error line. <br>• A limit-locked name is non-fillable at the close (e.g. SK hynix, +29.95% on 31 Jul 2026). <br>• An ETF close vs iNAV residual above 30 bp is flagged, because LPs carry no quoting duty in the closing auction. <br>• NYSE fills are MOC-equivalent at the official close. <br>• Intraday simulated entries are priced at the quote that triggered them, with the quote timestamp. <br>• No daily close is ever derived from intraday bars. |
| "0× only from the fail-closed risk engine" | **Backtests:** `core/quant/risk` returns 0 only for a risk-limit breach, the hard stop, or a data or system failure, and only in the books whose convention applies them (card evaluation books follow R-22 rule 6). A limit met by lowering g is a binding bound, never a breach, and never returns 0. **Simulated book:** `core/engine/runtime` holds one runtime state per book (the recommended and the specification book of each market, each FORWARD-SIM book, each card's forward on / off / S books). A HALT sets **that book's** target exposure to 0 and records `halt.class` and `halt.reason_code` in that book's `macro_state.runtime[]` entry; other books continue. <br>**Scope (binding; C-1 of the adversarial round).** A trigger HALTs only the books whose own NAV breached, whose own artifact failed acting-field validation, or that read the failed input or component through an `acting_exposure` binding (R-19 rule 5). The recommended book is never HALTed by a factor or input it does not read (I-03). A global failure (the PIT store, the calendars, the `core/engine` QuoteFeed) HALTs every book that reads it; it never HALTs "the engine" as such. `macro_state.flags.engine_state` reports the market's recommended book; `macro_state.runtime[]` reports every book (§6.1). <br>**HALTED triggers, by class:** <br>• **RISK:** the hard stop, −15% of the book's NAV from the high-water mark since the last re-arm (default; D2); a risk-limit breach: an R-07 limit that its prescribed action (lowering g on the ETF line; carrying a limit-locked order, R-27) cannot meet by the next decision. A look-through input that fails beyond its declared misses is an OPS trigger (R-19 rule 4), not a breach. <br>• **OPS:** a lag-audit violation at runtime; an acting-field schema or bounds failure in the book's own `macro_state` or `overlay_decision` (R-32); an `acting_exposure` input bound to the book that fails closed on more consecutive decisions than its declared limit (default: more than one; the book's counter, R-19 rule 4), or an error in an acting workflow step counted on that counter (`run_error`, §3.9); feed heartbeat loss > 60 s during a session (new intraday simulated entries are BLOCKED at once; the book re-arms automatically once the feed has been restored for 5 minutes, default, judgment; a HALT cleared before the next decision changes no weight); an exception in an acting risk-layer function (`market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose`); whole-book NAV unavailable on more than 2 consecutive decisions (R-25); a decision date outside calendar coverage (T-CAL-02); an operator kill. <br>**Never a HALTED trigger:** a stale or failing `risk_model` or `context` input; an exception inside `hedge_state` (→ `hedge_credit_off = TRUE`); a `disputed` input, or a `warmup` input before the book's first ARMED decision (R-01, R-19; afterwards a shortfall is a failure, §3.5); a failure of an input not bound to the book (an input bound only to the specification book fails that book closed and HALTs it alone at its limit, R-19 rule 4, T-SCOPE-01 (a); an input bound only to FORWARD-SIM or refusal books fails that FORWARD-SIM book closed, or labels the refusal book's input, and never HALTs); a validation failure confined to display or context fields, or of a `context_log` or `event_calendar` artifact (labelled and alerted; R-32). <br>**Effective time.** A HALT decided at the close of t sets the weights decided at t to 0 (the book earns 0 from t+1); a HALT raised intraday (heartbeat) blocks new intraday entries at once and applies to the weights decided at that session's close. |
| Re-arm (R-07) | Two classes, recorded in `halt.class`. <br>**RISK** (the hard stop; a risk-limit breach), counted in sessions of the book's primary-market calendar (KRX for a KR book; a whole-book NAV spanning markets uses the book's declared primary market): the HALT decided at the close of t earns 0 on sessions t+1 … t+10; re-arm is **automatic** at the decision at the close of t+10, in every book, backtest and forward alike (I-04b), and the operator's acknowledgement is logged but never required. After a hard-stop HALT the hard-stop and step references reset to the NAV at re-arm; after a risk-limit breach they do not reset, and the book re-arms only at the first decision at or after the close of t+10 at which the limit is met: the target weights the book would hold on re-arming, after the prescribed action (lowering g; carrying a limit-locked order, R-27), satisfy the limit, so a HALTED book's zero exposure never counts as meeting it. In both cases `post_rearm_cap` = 0.5 joins the `min()` of §3.3 for the weights decided at the actual re-arm decision and the 9 decisions after it (the closes of t+10 … t+19, earning on t+11 … t+20, when the book re-arms at t+10; exposure ≤ 0.5 × vt, not an absolute 0.5); then normal running. <br>**OPS** (every other trigger): HALTED until the cause clears (input fresh, heartbeat restored, artifact valid, NAV available, calendar signed); the book re-arms automatically at the first decision at which the cause has cleared, except after a lag-audit violation or an acting-artifact schema failure, which needs an operator re-arm once the fix's test passes. No refusal window, **no reference reset**, no post-re-arm cap. <br>A HALT raised while the book is already HALTED is idempotent for its own cause: it never extends `rearm_not_before` and never resets a reference. A different cause is added to `halt.causes[]` ({class, reason_code, since_utc, rearm_mode, rearm_not_before, cleared_utc}); the top-level `class`, `reason_code` and `since_utc` restate `causes[0]`, and the top-level `rearm_mode` is `operator` while any uncleared cause needs the operator, else `auto`; the book re-arms only when every cause has cleared under its own rule (a RISK cause after its refusal window and, for a breach, its cure; an OPS cause when cleared; an operator-mode cause by the operator). References reset only if a hard-stop cause was in the set, and `post_rearm_cap` applies if any RISK cause was, its window starting at the actual re-arm decision however late another cause made it; the ladder is not evaluated while HALTED (R-31). Every HALT and re-arm is a governance event (`governance_events.jsonl`, §3.9). I-04b requires the book to re-enter after every HALT. The hard stop makes no protection claim. |
| Runtime states (per book) | **DISARMED**: the initial state of every book and the state of a retired book; it holds no simulated position, its artifacts carry `engine_state: DISARMED`, and no forward record runs. **DISARMED → ARMED**: automatic, from the initial state only (a book that has never been ARMED), at the first decision at which every acting input bound to the book is fresh and past warm-up, the calendars cover ≥ 60 sessions ahead (T-CAL-02) and, for card books, the header is committed; logged as a governance event. **ARMED → HALTED**: the triggers above, by class and scope. **HALTED → ARMED**: the re-arm rules above. **ARMED or HALTED → DISARMED**: owner action only (retiring a book), logged. A retired book never re-arms; a card's books restart only under a new card revision, with R-25's lockout. A card's forward on, off and S books are retired together, never singly, and an operator kill of one of them kills all three; such a kill is an operational integrity trigger (R-25), because it blinds the record's alarms (the gap is still excluded). Every other HALT stays book-scoped, and every HALTED or DISARMED decision of the three books counts toward §8.8 (b)'s 10% budget (once per decision, however many of the three it affects). Retiring them while the card's factor acts in the recommended book first removes the factor from that book (a governance event, treated as a demotion for R-25's lockout). **Forward records are append-only (R2-C4):** a forward record never spans a DISARMED period; within a card revision its alarm state (CUSUM, rolling windows, counts) is never reset; a reset happens only with a new card revision, as a logged governance event with its reason, and the record's age still counts from the card's first registration. Every HALTED or DISARMED gap of any of the three books is marked and excluded from both sides of every forward comparison. Book ids: `recommended:<market>`, `specification:<market>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<card_id>:<on\|off\|S>`. |
| NAV valuation | Whole-book NAV (the NAV of one book id, all of its sleeves included; in v2.0 only R-14's `multi_line` card books span markets) for R-07, R-31 and R-25 is evaluated at each decision instant from the latest official closes usable at that instant (point-in-time; bound per book through `NAV_LINE_CLOSES`, R-19 rule 5), converted to KRW through the book's declared `nav_fx` (R-26), with per-market attribution printed. A NAV-input failure HALTs (OPS) only a book whose `NAV_LINE_CLOSES` binding has role `acting_exposure`; a FORWARD-SIM book (display-only, role `forward_sim`) never HALTs on it: the decision is marked failed-closed, printed, and counted toward §8.8 (b)'s 10% budget (ASPEC round 4 note 2). |
| Ladder steps (R-31) | −8% from the step reference → 0.5×; −12% → 0.5× plus an evaluator block on new entries. Multipliers are totals, never cumulative, and compose with the overlays by `min()` (R-02). A step lasts at most 21 sessions, after which its reference resets to the current NAV; the hard-stop reference does not reset. Where the steps bind on more than 10% of days on the declared book (≈ 19% for KOSPI VT20), they act only in the specification book until the R-31 CARD-P passes. |
| "Entry blocks" | `core/engine/evaluator(rule, quote) → decision` returns `BLOCKED(rule_id, reason)` for any **new-entry** decision while an R-10 event window or the −12% step is active. Holds and exits are never blocked. The backtest applies the same rule at daily resolution. **R-08 is no longer a block:** on a flag day the evaluator writes an annotation and requests KIS spread snapshots, and no book's exposure changes. |
| Books | Recommended book and specification book: fed through `macro.engine_feed`. FORWARD-SIM books (R-28, R-29) and refusal books (R-11, R-12; display only): computed by the forward evaluator in `core/quant/backtest` and recorded in `core/engine/state`; they never pass through `engine_feed` (R-35). Every book has its own runtime state (above). |
| "Live shadow book" | **FORWARD-SIM**: forward books that run from the date the card header is committed and write timestamped `macro_state` and `overlay_decision` artifacts. In v2.0 they are falsification alarms only (P14, R-25). |
| "Kill", "manual override" | Two different things. An **operator kill** is `runtime_halt(book_id, "OPS", "operator_kill")`: logged as a governance event and re-armed by the operator; it is never a demotion, except that a kill of a card's forward books is an operational integrity trigger (runtime states above; R-25). A **card kill** is card demotion (§8.8, R-25): any edit of an acting parameter outside a card revision appears in the rules store's edit history, demotes the card immediately and opens a new revision. An owner ruling (§8.10) is not such an edit. |
| Trigger and switch counts | `core/engine/state` persists trigger counts, per-card switch counts, the ladder state (references, step, dwell left, re-arm and cooling-off dates), each book's runtime state and consecutive-failure counters, and forward alarms (**proposed**). |

### 3.9 The daily workflow (`core/skills/workflows/macro_daily.yaml`, proposed; R-35)

```yaml
# proposed; YAML pipelines with decision gates exist in core/skills/workflows
name: macro_daily
runs: [after_close: KRX, after_close: NYSE]   # decision_utc = close_print_bound_utc from the calendar (R-20); the run starts
                                              # no earlier than close_print_bound_utc + 10 min (06:40:30Z for KRX today), so no provisional row is read (R-01)
run_mode: live                                # live | backtest | replay: selects production vs history channels (§4.2)
steps:
  - skill: macro.pit_snapshot          # core/ficc/data: retries missing inputs per data.ingest until they arrive or
                                       #   data.ingest.decision_deadline passes, then pins knowledge_utc for the run (one artifact per
                                       #   decision: a later run for the same decision is a replay, never a second forward decision); pit_value for every registry binding at
                                       #   decision_utc, with value_status and session_date checks (R-01)
  - gate: data_ok                      # by role and book (R-19; §3.8):
                                       #   acting_exposure missing/stale/provisional/synthetic -> that component fail_closed=true,
                                       #     alert, previous state carried; the bound books' counters +1; at the declared limit ->
                                       #     those books HALTED (OPS); books the input is not bound to are untouched
                                       #   forward_sim failing -> that FORWARD-SIM book fails closed; never HALTs another book
                                       #   risk_model stale or failing -> hedge_credit_off=TRUE, alert (operator alert after two
                                       #     missed releases); the gate PASSES
                                       #   context stale -> labelled "stale"; the gate PASSES
  - skill: macro.lag_audit             # independent of pit_value: for every acting and risk-model input, recompute
                                       #   usable_at(series, obs_date, market) from core/calendars and the registry; require
                                       #   usable_at <= decision_utc, available_at_utc >= publication_instant(series, obs_date)
                                       #   (closes: >= the scheduled close; a derived input: each input of its lineage), retrieved_at_utc <= knowledge_utc and the R-01 status
                                       #   and session checks; acting violation -> HALT (OPS) of the books it feeds (T-LAG-01);
                                       #   risk-model violation -> hedge_credit_off + alert, never HALT (a covariance-only binding: carried, then
                                       #   dropped, R-19 rule 4); the record is written
                                       #   to macro_state.lag_audit
  - skill: macro.vol_and_overlays      # core/quant/risk + core/quant/signals + core/quant/optimize: vt, vs, base weights,
                                       #   hedge_state, look-through caps, ladder state; composition by min()
  - skill: macro.build_artifacts       # macro_state, overlay_decision (verdict and disposition per factor), context_log,
                                       #   event windows and gap tags, R-08 annotation; always written, also when a gate failed
  - gate: bounds_ok                    # validates the built artifacts: schema 2.0 + P2 bounds + exposure basis + min()
                                       #   composition recomputed from the recorded factors (T-CAP-02). An acting-field failure
                                       #   -> HALT (OPS) of the books the artifact describes; the artifact goes to
                                       #   <artifact_dir>/quarantine/ with its errors. A display- or context-field failure ->
                                       #   written with extras.validation_errors and an alert; a context_log / event_calendar
                                       #   failure -> refused and quarantined with its errors, alerted; never a HALT (R-32)
  - gate: verdict_filter               # PASS factors with disposition RECOMMENDATION or BUILD_AS_INSURANCE, and R-31 steps with
                                       #   disposition INVARIANT_STEP, enter the recommended book; everything else -> specification book;
                                       #   each verdict is authenticated first (cards/verdicts.jsonl; R-35, T-CARD-03)
  - skill: macro.engine_feed           # recommended and specification books -> core/engine (simulated order book only);
                                       #   BLOCKED rules; never a FORWARD-SIM or refusal book
  - skill: macro.forward_books         # FORWARD-SIM books (R-28, R-29) and, if kept, refusal books (R-11, R-12)
                                       #   -> forward evaluator; display only
  - skill: macro.forward_monitor       # R-25 alarms on whole-book NAV; integrity triggers demote immediately
  - skill: macro.brief                 # Macro page and weekly brief section; open owner decisions listed
  - skill: macro.run_record            # appends {run_id, market, session_date, decision_utc, knowledge_utc, started_utc,
                                       #   finished_utc, step results with errors, git_hash, config_hash, data_snapshot_id, late}
                                       #   to run_log.jsonl; a step that raises still writes its record (status = error) and
                                       #   raises RUN_ERROR (page). An error in an acting step (pit_snapshot through
                                       #   verdict_filter) blocks engine_feed for that run: the books carry their weights,
                                       #   build_artifacts writes a fail_closed artifact, and every book the step serves
                                       #   counts a failed decision (book counter +1; OPS HALT run_error at the limit,
                                       #   R-19 rule 4). A forward_monitor error is re-run for each skipped decision at the
                                       #   next successful run.
# On app start and at every scheduled run, macro.missed_decisions compares the calendar's expected decisions with
#   run_log.jsonl; each missing decision, and each decision whose run record has status = error in an acting step, raises MISSED_DECISION (severity page) and the books carry their weights (§8.8).
# Alert sinks: a Macro-page banner (always; page alerts persist until acknowledged), an OS notification, an optional
#   e-mail skill. HALT, re-arm, demotion, package freeze, header commit, owner-decision and calendar changes are appended
#   to governance_events.jsonl (append-only, hash-chained; one §6.6 record per line, verified at app start, T-OBS-05) and summarised in the weekly brief.
```

Credentials stay env-only, as in the existing runner. The Claude API, when a key is set, receives the computed numbers only and never decides (QUANTGEN FAQ).

### 3.10 If a broker path were ever added

QUANTGEN has none, and its first rule says there is nothing to switch on. Adding one would change the project's founding rule. That is a decision for the owner, not for this spec. This spec therefore does not design one. It records only what would have to remain true:

1. Only cards with a **PASS** verdict (RECOMMENDATION or BUILD-AS-INSURANCE) could drive it. The pre-registered costs (P10), the tick floor and the 2× stress would still apply, on the instrument book the card declared.
2. It would have to be **fail-closed**. HALTED, any lag-audit or schema failure, and any stale acting input would block submission. 0× would still come only from the risk layer, and the hard stop would keep its explicit re-arm.
3. Its own forward record would be gated like any card. No backtest alone could enable it.
4. Nothing in §5 would change. The overlays would still output bounded multipliers only.

Every backlog item that would need a real order path or fills is listed in the backlog's "blocked by read-only design" section.

---

## 4. Data layer specification (`core/ficc/data`, `core/quant/history`, `core/calendars`, `core/markets`)

### 4.1 Time rules

**Storage (R-01).**
- All timestamps are stored in UTC, as ISO-8601 with a "Z" suffix.
- Every record carries:
  - `obs_date`: the market/local date the value refers to;
  - `session_date`: the exchange session it belongs to (required for close-type inputs);
  - `obs_utc`: when the observation was made;
  - `available_at_utc`: when it was published or became usable, with `available_at_source` (published, calendar bound, or inferred from retrieval when a vendor gives no publication time). **Backfilled history** (rows fetched after their publication window, e.g. a 1997–2026 download) is stamped `calendar_bound` from the registry's publication rule for each `obs_date`, never `inferred_from_retrieval`, which is for live rows only. **ALFRED vintages:** `available_at_utc` = the vintage's `realtime_start` date at the publisher's scheduled release time (BLS/BEA 08:30 ET), `calendar_bound`; observations older than the series' first ALFRED vintage are stored with `vintage = null`, `value_status = revised` and the label `pre_vintage_history`, which every backtest that reads them prints. Unrevised daily market series (DGS10, DEXKOUS, VIXCLS) take `available_at_utc` from the publication calendar, not from ALFRED. Where production reads a re-posting channel (FRED for VIXCLS or DTWEXBGS), the publication instant is that channel's posting time (FRED `last_updated` when live; a declared lag in history), not the primary source's;
  - `retrieved_at_utc`: when QUANTGEN first saw it (first-seen). Store rows are never mutated: a fetch that returns unchanged content is recorded only in the append-only fetch log (`fetch_log.jsonl`: series_id, fetch_utc, provider, status, content-hash digest);
  - `value_status` ∈ {official_close, vendor_close, live_snapshot, provisional_intraday, first_release, revised, vendor_derived, vendor_derived_across_gap} (assignment rule under "Value status" below);
  - `vintage` and `content_hash`.
- The store is append-only. Corrections are new rows; reads are as-of reads at a knowledge time pinned once per run (§3.5). **Derived series** (σ̂, rv20, YoY and 3-month changes, corr63, z-scores, the paper momentum series, contract notionals) are PIT records with `obs_kind = derived`: `available_at_utc` = the latest `available_at_utc` of their inputs; `value_status` = the weakest input status (the rank of §3.5); `content_hash` covers the inputs' content hashes (lineage). A derived value is recomputed whenever an input row changes and is never served from the cache; a derived acting value with any non-`official_close` close-type input is `MissingInput("provisional_intraday")`.
- The 6-hour `~/.nextgen/ficc_cache` becomes the store's read-through cache. A cached value keeps its `retrieved_at_utc`. At a decision it may be served only if its `retrieved_at_utc` is later than the series' most recent due publication instant ≤ `decision_utc` (for a close-type series: later than `close_print_bound_utc` + 10 min of the decided session); otherwise the store re-fetches, and a failed re-fetch is a `MissingInput`, never the cached row (the 2-Oct provisional row came from a pre-close file). The cache never holds derived values of acting inputs. Ingestion follows `data.ingest` (§7): fetches at the `pit_snapshot` step and on each series' publication schedule, retries up to a decision deadline, and appends a row only when its content changes.

**Market clocks (effective-dated, R-20).** `core/markets` holds the session; `core/calendars` holds the holidays, DST and every effective-dated rule. `decision_time_utc` (the scheduled close), `close_print_bound_utc` (the decision instant) and `usable_at` are calendar lookups, never constants.

| Market | Time zone | Regular session (today) | Official close in UTC (today) | Effective-dated rules |
|---|---|---|---|---|
| KRX | KST = UTC+9, no daylight saving | 09:00–15:30 | Scheduled 06:30:00Z. The close prints by **06:30:30Z**, the close-print bound (scheduled close + 30 s): the random end has been unconditional and ≤ 30 s on every call auction since 2015-06-15, and the bound was 06:00:30Z from 2015-06-15 to 2016-07-29 | • Close 15:00 KST (06:00Z) before 2016-08-01. <br>• CSAT days 10:00–16:30 from 2016-08-01 (close 07:30Z, bound 07:30:30Z); the pre-2016 CSAT window comes from the KRX notice. <br>• The first trading day of the year opens at 10:00. <br>• Lunch break until 2000-05; Saturday sessions until 1998-12-12, with their own close time from the KRX notice. <br>• Conditional random end before 2015-06-15: the bound is the scheduled close + the 30 s print tolerance, plus any extension the KRX notice records for a session. <br>• Price limits ±6% (Apr-1995), ±8% (Nov-1996), ±12% (Mar-1998), ±15% (Dec-1998), ±30% (2015-06-15). <br>• Closing auction 15:20–15:30 KST. <br>• NXT after-market 15:40–20:00 and KRX after-market 16:00–20:00 (from 2026-09-14) are excluded from signals; a vendor "last" after 15:30 is never stored as the close. |
| NYSE | ET (IANA America/New_York via zoneinfo: EDT = UTC−4, EST = UTC−5; DST from the second Sunday of March to the first Sunday of November since 2007, from the first Sunday of April to the last Sunday of October before; never a fixed month rule) | 09:30–16:00 | 20:00Z (EDT) / 21:00Z (EST); close-print bound + 30 s | Early closes at 13:00 ET: 17:00Z in EDT (e.g. 2025-07-03), 18:00Z in EST (e.g. 2026-11-27). The 16:00 ET close is 05:00/06:00 KST the next day. |
| CRYPTO (planned, R-17) | UTC | 24/7 | Venue daily bar close: the bar dated d closes at 00:00:00Z on d+1, declared per venue | 365-day annualisation; weekday macro data joined as-of with staleness labels; FRED's 17:00 PT stamp is never mixed with UTC candles. |

**Event and publication times.**

| Event | Local time | KST / note |
|---|---|---|
| US CPI / NFP (BLS) | 08:30 ET | 21:30/22:30 KST the same day |
| FOMC statement | 14:00 ET | 03:00/04:00 KST the next day |
| H.15 (DGS10 and other daily rates) | 16:15 ET on the **next Fed business day** after D | 05:15/06:15 KST |
| US Treasury daily par-yield curve (CMT) | "usually available … by 6:00 PM Eastern Time" on D ("may be delayed"); the posting time is logged | 07:00/08:00 KST on D+1 |
| H.10 (DEXKOUS, DEXJPUS, DTWEXBGS) | Mondays 16:15 ET, for the previous business week; the next business day when Monday is a Federal holiday | Tuesday 05:15/06:15 KST |
| VIX / VIX3M official close | 16:15 ET | 05:15/06:15 KST the next day |
| BoK rate decision | ≈ 09:50 KST | stored as its own event (R-10) |
| BoK governor's press conference | ≈ 11:10 KST | stored as a separate event |
| Onshore USD/KRW close (BoK ECOS 731Y003, item 0000003, "원/달러(종가 15:30)") | 15:30 KST (15:00 before 2016-08-01) | Onshore USD/KRW trades 24 hours from 6 Jul 2026 (Mon 06:00 → Sat 06:00), so the input is a timestamped 15:30:00 KST snapshot, never "the close" |

**Decision time (binding): decide at the close of day t; earn from day t+1.**
- `decision_utc` is the **official close** of the session being decided: `close_print_bound_utc(m, t)` from the effective-dated calendar (R-20; `decision_time_utc(m, t)` keeps its v1.2 meaning, the scheduled close). Its values:
  - KRX since 2015-06-15: the scheduled close plus the ≤ 30 s random end, i.e. 06:00:30Z through 2016-07-29 and 06:30:30Z from 2016-08-01; on CSAT days the CSAT close + 30 s (07:30:30Z from 2016-08-01; the pre-2016 CSAT close comes from the KRX notice). Before 2015-06-15 there was no unconditional random end: the bound is the scheduled close (06:00Z) plus the declared print tolerance of 30 s, and a session whose conditional random end was triggered carries its extension from the KRX notice in the calendar data. Saturday sessions before 1998-12-12 use their own close time from the KRX notice.
  - NYSE: the scheduled close (16:00 ET: 20:00Z in EDT, 21:00Z in EST; 13:00 ET on early-close days: 17:00Z in EDT, e.g. 2025-07-03, and 18:00Z in EST, e.g. 2026-11-27) plus the declared print bound `calendars.US.close_print_bound_s` = 30 s, DST-aware.
  - M1 confirms both bounds against logged exchange timestamps; a change is a signed calendar revision. Each bound also covers the dissemination of the series actually read (an index close is computed after its constituents' closing prints). A close whose logged print time is later than its bound fails closed and raises a calendar-review alert; it is never re-stamped.
- An official close's `available_at_utc` is its exchange print time, ≤ `close_print_bound_utc` (06:30:30Z for KRX today). When the exchange print time is not logged, the calendar bound is used (`available_at_source = calendar_bound`). A receipt timestamp is stored only as `retrieved_at_utc`, never as `available_at_utc`, so an official close with no logged print time that is retrieved at 06:45Z, after the 10-minute quarantine below, is stored with `available_at_utc` 06:30:30Z (`calendar_bound`) and accepted for that day's decision, while the same row retrieved at 06:31Z is never stored as a close (T-CLOSE-01, T-FIX-01; QF1-A25 records which KIS fields carry the exchange time).
- The workflow runs no earlier than `close_print_bound_utc` + 10 minutes (06:40:30Z for KRX today; §3.9). It may read only inputs with `available_at_utc ≤ decision_utc` and, for close-type acting inputs, `value_status = official_close`.
- The resulting weights are priced at the close of t in the simulated order book and earn the return from close(t) to close(t+1). The executable variants (R-26, R-27) are printed as card lines.
- **History of the rule.** v1.0 decided at 15:15 KST, a proxy for the closing auction. v1.1 and v1.2 used 06:30:00Z, which a literal lag audit would reject on every day the random end runs (QF1-A4; EX2: every day since 2015-06-15).

**Value status and the provisional-row guard (binding, R-01).**
- A close-type acting input must have `value_status = official_close` and `session_date` equal to the decided session. Otherwise `pit_value` returns `MissingInput("provisional_intraday")` (non-official status) or `MissingInput("session_mismatch")` (session mismatch), even if its `available_at_utc` precedes the decision.
- The official close from KIS or KRX is primary; a vendor file is secondary. **Status assignment (binding):** `official_close` only for the KRX-session close field of KIS (R-01 failure modes) or the KRX marketplace, retrieved ≥ `close_print_bound_utc` + 10 min; a vendor daily row retrieved after that time is `vendor_close`; a quote read during or after the session is `live_snapshot` (`obs_kind = quote_snapshot`). Live and forward decisions accept only `official_close` for close-type acting inputs. A backtest may read `vendor_close` only when its card header declares that vendor as `data.source` (the §9.3 regression goldens and I-07 do; the formal R-06 KR card does not), and the card prints that label.
  - Tolerance: |Δ| ≤ 1 bp for indices, exact for stocks. Reconciliation compares like with like: vendor stock histories are split-adjusted, so stocks reconcile on a declared `adjustment_basis` (raw official closes plus effective-dated corporate-action factors from KRX or DART, stored with their announcement `available_at_utc`), never raw against adjusted. A vendor row absent on a KRX session (e.g. Yahoo's Saturdays before 1998-12-12) is `vendor_missing`, not a dispute.
  - Otherwise the value is disputed: the official value is used with `dispute = true` (status `disputed`, never a failure), an alert is raised and the dispute is logged.
  - **Never auto-correct.**
- A row retrieved before `close_print_bound_utc` + 10 minutes of its session (06:40:30Z for KRX today) is never stored as a close. Every "close + 10 minutes" in this spec (§3.9, `data.reject_rows_retrieved_before_close_plus_minutes`, `data.fixtures`, T-FIX-01) uses this anchor.
- A flat-OHLC, zero-volume row on a session day is a stale carry: flagged and alerted, never read as a zero return.
- **Bar convention.** Bars carry `bar_end` timestamps, the closing auction is its own bar, and `available_at = bar_end + latency`. A daily close is never derived from bars: on 727 of 729 days the vendor's last KRX hourly bar is the 14:00–15:00 bar, so the 15:00–15:30 segment, including the closing auction, is missing. The last-bar close differs from the official close by a median 13.7 bp (max 205 bp).
- **Open-quality flags.** An OHLC open equal to the prior close is flagged; ^GSPC shows this on 41% of days. Range-based estimators use a per-series open-quality ratio (R-30).
- **Worked example (T-PROV-01).** The vendor row 6,943.66 on 2 Oct 2026 was a ~10:30 KST print (volume 99,651 against 227,641 final). The official close was 7,003.74.
  - v1.2's audit accepted the row (available 01:30Z ≤ 06:30Z).
  - The v2.0 store, read for the 2-Oct decision, returns `MissingInput("missing")` at knowledge time 10:31 KST (the 10:56 KST file is not yet seen), `MissingInput("provisional_intraday")` at 11:00 KST and 7,003.74 [official_close] at 16:00 KST (T-PROV-01).
  - The 24 values the patch corrected are in §11 and DLA §7.

**Cross-time-zone rule (binding).**
- **US data for KRX decisions.** A US- or New-York-dated datum dated D (New York date) may enter the KRX decision at the close of Korea date K only if **D ≤ K − 1 calendar day** and its `available_at_utc` ≤ the KRX `decision_utc` on K.
- **The US session as an input.** The US session dated D closes at 05:00/06:00 KST on D+1, so it is usable at the KRX close of the next KRX session (K = D+1 or later). It is an **opening-gap input** for KRX date D+1 and an input to the close-of-(D+1) decision, which earns close(D+1) → close(D+2).
- **The forbidden case.** Never use the US session dated K for a KRX close-to-close return dated K. That mistake produced a fake +0.31 Sharpe (N-47); it is now the positive control of T-PLACEBO-01 (R-34).
- **General cross-market rule (v2.0, QF2-A21).** A close of market M dated D is usable at a decision only if `close_print_bound_utc(M, D) + buffer < decision_utc`, with the bound from the calendar registry and `buffer_s` 60 (`data_contracts.cross_market`; R-19, T-XMKT-01).
  - The TSE has closed at 15:30 JST since 2024-11-05, the same instant as the KRX close.
  - Shanghai (15:00 CST = 07:00Z) and HKEX (16:00 HKT = 08:00Z) close after the KRX close on normal days (standard hours; UNVERIFIED in QF2); TWSE (13:30 TST = 05:30Z) closes before it. On CSAT days the KRX bound is 07:30:30Z (from 2016-08-01), after the Shanghai and TSE closes.
  - So on normal days the same-date Asian closes that enter a KRX decision are TAIEX's (every weekday session) and the TSE's on sessions from 2016-08-01 through 2024-11-04, which printed 30 minutes before the KRX close; on CSAT days the general rule also admits the same-date TSE close and, from 2016-08-01, the Shanghai close (T-XMKT-01). Only the Korea covariance reads these closes (R-07 (7)). Before 2016-08-01 both markets closed at 06:00Z, and the TSE close is not usable (06:00Z + 60 s > the 06:00:30Z bound). Covariances use synchronous or lagged returns, never a same-date join across asynchronous closes.
- **Multi-session gaps (v2.0, R-10).** When the KRX is closed and the NYSE is open, more than one US session passes between two KRX closes. `gap_sessions(KR, K)` = n_US is tagged on the next KRX session. n_US is 0 when the NYSE was closed on the weekday that followed a KRX session (e.g. the KRX session of 2026-11-27, after Thanksgiving): no gap event, and the displayed VaR is unscaled (R-10).
- **H.15 (DGS10 and every H.15-based series; v2.0, QF2-A6/A11).** DGS10(D) is posted at 16:15 ET on the **next Fed business day** after D. Business days come from the Fed calendar for publication and from the NYSE or KRX calendar for decisions.
  - **US decision.** The first US close after the posting instant. Normally that is the close of the second business day after D (strict H.15). On Columbus Day and Veterans Day the NYSE is open while the Board is closed.
  - **KRX decision.** The first KRX close after the posting instant. v1.2's "Korea date D+2 calendar days" leaked on 599 of 2,938 observations (every Friday and pre-holiday date). Example: DGS10 dated Fri 2015-01-02 is usable from the KRX close of Tue 2015-01-06, not Mon 2015-01-05.
- **Treasury par-yield channel (v2.0, QF2-A7/M7).** The par yield for D is "usually available … by 6:00 PM Eastern Time" on D ("may be delayed"). With the posting time logged, it is usable from the first close after that time: +1 business day for a US close decision. This is compliant. It does not change R-12's REJECT.
- **H.10 (DEXKOUS, DEXJPUS, DTWEXBGS; v2.0, QF2-A10).** A value dated D (Monday–Friday) is published the following Monday at 16:15 ET, or on the next business day when that Monday is a Federal holiday. It is usable from the first KRX close after publication (normally Tuesday KST) and from the first US close after it. Example (T-AVAIL-01): the DEXKOUS week of 2026-10-05 is usable from the KRX close of Wed 2026-10-14, because Mon 2026-10-12 is Columbus Day.
- **Two timing regimes.** A backtest declares which one each input uses, and every lag it tries goes into the family ledger (R-23, R-34).
  - **Value timing (live-feed proxy).** The value is used from the first decision after its observation time. This is legitimate only when production reads a live, timestamped feed of the same quantity: the KIS US 10y quote, the ECOS 15:30 close, or a timestamped 15:30:00 KST USD/KRW snapshot. The backtest result must then be labelled "value timing".
  - **Publication timing (strict).** The value is used from the first decision after its official publication. This is mandatory whenever the production source is the published series itself.

**Monthly series.**
- Store them on an explicit monthly index keyed by the first day of the reference month (FRED's convention); that day is the value's `obs_date`.
- Compute YoY and 3-month changes by **calendar offset**, never by positional `shift`.
- A missing month (Oct-2025 CPI and household survey, never collected) makes NaN every derived value that uses it as an input: an endpoint or a member of an averaging window (YoY for Oct-2025 and Oct-2026, MoM for Oct and Nov 2025, Sahm's 3-month means). An endpoint change whose window merely contains it is computed (Aug-2026 YoY = 3.35%).
- Derived series (Sahm, YoY, the Taylor range) are computed in-house. A vendor value that spans a gap is tagged `vendor_derived_across_gap`; FRED's SAHMCURRENT shows 0.25 for Oct-2025 although UNRATE for Oct-2025 is missing.
- Test value: Aug-2026 CPI YoY is **3.35%**. A positional `shift(12)` gives 3.71%, which is wrong.

**Staleness (v2.0, R-19; replaces the v1.2 defaults).** v1.2's defaults are removed: 1 trading day for daily series, 3 days for weekly, 1 release cycle for monthly. They marked DTWEXBGS and DEXKOUS stale at 100% of US-close decisions (98.6% at the KRX close) and strict-H.15 DGS10 at 99.52%, so a literal build halted every day (DLA-S1). The rule is now:
- **When a series is stale.** It is stale when `decision_utc > stale_deadline_utc`, where `stale_deadline_utc = expected_available_utc(series, last_obs) + grace` and `expected_available_utc(series, last_obs)` is the publication instant of the **next** expected observation after `last_obs`, i.e. `publication_instant(series, next_expected_obs(series, last_obs))` (R-19 step 3, normative). Staleness is never measured from the age of `last_obs` or from `last_obs`'s own release: read that way, the rule flags the weekly H.10 series stale on about 80% of decisions and monthly series for most of each month (the v1.2 freeze).
  - Expected times come from the effective-dated publication calendar, with Fed, SIFMA and NYSE holidays whitelisted: H.10 on Mondays at 16:15 ET (or the next business day after a Federal holiday); H.15 at 16:15 ET on the next Fed business day; Treasury par yields by about 18:00 ET on D, with posting times logged; BLS at 08:30 ET; market closes per the calendar.
  - Grace is one publication business day.
- **Failure action by role**, declared in the registry (§4.2):
  - **acting_exposure:** fail closed (state unchanged, `fail_closed = true`, alert). HALTED (OPS, §3.8), for the books the input is bound to only, after the declared number of consecutive missed decisions; the default is more than one.
  - **risk_model** (every `hedge_state` input, R-09): `hedge_credit_off = TRUE`, with `hedge_failure` computed from the labelled live USD proxy. An operator alert follows two missed releases. **Never HALTED.**
  - **context:** labelled "stale" only.
  - **forward_sim:** fails its FORWARD-SIM book closed; never HALTs another book. **history:** read by the card harness only; a card whose cash or history series does not cover its span is refused (R-22).
- **Evidence.** Schedule-aware staleness flags 0.33–0.89% of decisions over 2016-01-04 → 2026-09-25 (VIXCLS 0%). Every hit's missed observation date is a date the source legitimately skipped: Good Fridays, 2018-12-05, 2017-01-20, 2020-11-27, 2020-12-24 and the DC storm closures.
- **Unscheduled delays** (e.g. the 2025 government shutdown) are handled through event `status = delayed`: each series names its release event (`release_event_type`, §4.2), whose `delayed` or `cancelled` status moves or removes the expected instant.
- DTWEXBGS is never an acting input. The full data contract (schema, range, monotone dates, cross-source tolerance, role and N) is specified in R-19.

**Vintages.**
- Every fetch is stored with its retrieval time.
- Backtests of revised macro series (payrolls, unemployment, GDP, PCE) must use ALFRED vintages.
- Revised context series store the first release, the current value and the vintage date (FRED `output_type=4` gives initial releases). Example: 2025 payrolls averaged +119.4k a month in first prints and +9.7k in the current vintage (R-13).
- Acting rules use only market-priced series, which are not revised. Vintages matter for context items, the narrative in the brief and research.

**Named series.**
- Every series ID is explicit. "Brent" must be either `DCOILBRENTEU` (Dated Brent spot, FRED/EIA) or `BZ=F` (ICE front-month futures, Yahoo).
- Continuous-futures returns across rolls are forbidden. Yahoo's BZ=F printed a "−14.5%" roll artefact on 1 Apr 2026. Futures books use a fixed roll calendar; the expiring KOSPI200 contract stops trading at 15:20 KST.

**Closes, not intraday prints.**
- Use KRX regular-session official closes, never a circuit-breaker print or a bar-derived value.
- Example: on 9 Mar 2026 the KOSPI close was 5,251.87 (−5.96%). The −8.11% figure was a 10:31 circuit-breaker print, not a close.

**Price convention.** The core history loader does not state whether "adjusted" closes include dividends (architecture review, finding A3). The golden values use ^KS11 **price** returns and French total/excess returns as stated in §9.3. A vol target is insensitive to this, but backtest returns are not, so every card records the convention. v2.0 card statistics use excess returns over local cash (R-22).

### 4.2 Series registry (a data file next to `core/ficc/data`, proposed)

**Registry fields (v2.0, R-19).** Each series declares:
- `series_id`, `source` and `channel`;
- `frequency`, `obs_calendar` (the dates on which an observation exists: KRX, NYSE, FED, SIFMA, CBOE, JPX, SSE, HKEX, TWSE, CME or ECOS, the BoK ECOS business days of `BOK_CALL_RATE`) and `publication_schedule` (a calendar id, a local time and an IANA time zone, e.g. `{calendar: FED, time: "16:15", tz: America/New_York}`), which give `next_expected_obs` and `expected_available_utc`; `release_event_type` (the R-10 event whose `delayed` or `cancelled` status moves or removes the expected instant); the time zone of `obs_date`;
- `grace_publication_bdays` (1, from `data_contracts`, §7);
- `bindings`: one entry per consumer, `{consumer, role, books}`, with `role` from `data_contracts.roles`; each consumer applies its own role's failure action (R-19 rule 5); for acting bindings, `halt_after_consecutive_decisions` (2, i.e. more than one; `data_contracts.on_failure`); `timing_class` (live, publication or value_proxy), `production_channel` and `history_channel` (selected by `run_mode`, §3.9); `adjustment_basis` for prices; `obs_kind`;
- range checks per series (e.g. |r_KOSPI| ≤ 30%, VIX ∈ [5, 150], US Treasury yields ∈ [−1, 20]%, Korean call and CD rates ∈ [−1, 40]%: Korean rates ran at 16–25% in 1997–98);
- the cross-source tolerance.

**Role codes** (the staleness role of R-19 in brackets):
- **A**: acting input of a BUILD NOW card or invariant [acting_exposure].
- **R**: risk-model input; `hedge_state` and covariances only [risk_model; never HALTs; a covariance-only input that fails is carried, labelled stale, for up to 5 decisions, then dropped from the covariance and labelled (`risk_model_covariance`)].
- **F**: input of a FORWARD-SIM card [forward_sim]. It acts only inside that card's forward book; a failure fails that book closed and never HALTs another book.
- **X**: input of a refusal book (display only) [context].
- **C**: context only [context].
- **H**: history or backtest only [history]: read by the card harness, never by a weight decision; a gap in its span refuses the card.
- **P**: planned (not registered; no binding).

**Korea**

| Series | Source / ID (QUANTGEN provider) | Freq | Publication / available_at rule | Role |
|---|---|---|---|---|
| KOSPI, KOSPI200, constituents OHLCV | KIS Open API quotes (KRX official) and the KRX marketplace (session close), primary; vendor files (Yahoo) secondary, for reconciliation only | daily | official close print ≤ `close_print_bound_utc` (calendar; 06:30:30Z today); `value_status = official_close` only from the KRX regular-session close field (R-01 failure modes); rows retrieved before the close + 10 min are rejected | A |
| Samsung (005930), SK hynix (000660) prices and market caps; KOSPI total market cap | KIS / KRX marketplace | daily | KRX close (as above) | A (look-through caps) |
| KODEX 200 (069500) daily basket (PDF) and price; leveraged and inverse ETF metadata (L, tick, price) | KIS or KRX (proposed) | daily | Publication instant **measured in M1** beside the KIS quote check. Until then `expected_available_utc` = 08:00 KST on the next KRX session (default, judgment), so the decision at the close of t reads the basket dated t−1; `halt_after_consecutive_decisions: 5`; meanwhile the last basket is carried, its age is printed and the bound is recomputed on current prices | A (look-through caps, R-07; books: recommended, specification; tick floor and cost class, R-26) |
| KOSPI investor-type net buys (foreign / institution / individual) | KIS ("investor flows") | daily (final after close) | after the close; preliminary intraday figures are stamped with their own time | C (log from day one; backlog BL-C06) |
| KRX margin debt; leveraged and single-stock leveraged-ETF AUM and value traded | KRX / KOFIA (new provider, proposed) | daily | per source | C once acquired (R-13; BL-U01); P until then |
| USD/KRW | **Input, if ever needed:** BoK ECOS 731Y003 item 0000003 ("원/달러(종가 15:30)", daily, 1990-03-02 onward), or a timestamped 15:30:00 KST snapshot after 6 Jul 2026. **Proxy:** FRED `DEXKOUS` (H.10, noon New York), labelled as a proxy | daily | ECOS close observed at 15:30 KST on K (15:00 before 2016-08-01); its `available_at_utc` is ECOS's posting time (`inferred_from_retrieval` when read live), so an ECOS read is value timing for the same-day KRX decision. Backfilled ECOS history is stamped `calendar_bound` at its observation instant (15:30:00 KST of K; 15:00:00 before 2016-08-01) with `timing = value_proxy`, and every backtest that reads it is labelled value timing (§4.1, two timing regimes). DEXKOUS dated D is published the following Monday 16:15 ET (next business day after a holiday Monday). Production never reads DEXKOUS. FX-regime metadata (the 1997 peg, bands, smoothing) is recorded with every KRW input | X (R-11 refusal book); C (context; `fx_hedge_credit` display, R-09); `nav_fx` of non-KRW books, with the role of the book it values (F for R-29's FORWARD-SIM book; R-26, R-19 rule 5) |
| BoK base rate; Korea CPI | BoK ECOS / KOSIS | event / monthly | release timestamp | C |
| Korea overnight call rate `BOK_CALL_RATE` (its ECOS statistic code and item are written into the registry before the gate freeze; the CD 91-day rate is a separate context series) | BoK ECOS (proposed) | daily | release timestamp | H (cash leg of excess returns for Korea cards, R-22) |
| VKOSPI; KOSPI200 model-free implied variance at 15:30 KST | KRX; QUANTGEN's Derivatives page | daily | close; the MFIV snapshot is stamped `live` | C (R-13) |
| DART filings (rights offerings, listings); KIND; KOSPI200 / MSCI index-change announcements | OpenDART; KIND; KRX / MSCI | event | filing timestamp | C (calendar flag); exclusions in backlog |

**United States**

| Series | Source / ID (QUANTGEN provider) | Freq | Publication / available_at rule | Role |
|---|---|---|---|---|
| US equity sleeves and index (S&P 500 or the sleeve's own returns) | KIS quotes; FMP EOD history; Yahoo (secondary) | daily | US close | A, bound to the US recommended book only once D5 creates a US sleeve and a PASS card uses it (no binding to any recommended book while D5 = none); F for R-28 and R-29; R for corr63 (`SPX_OFFICIAL_CLOSE`) |
| Index futures: CME E-mini / Micro E-mini S&P 500; KOSPI200 and mini KOSPI200 front months | KIS read-only quotes (whether KIS quotes CME futures is UNVERIFIED); fixed roll calendar | daily | venue close; no continuous-contract returns across rolls | F (R-29); A only for a futures-line card that passes |
| VIX, VIX3M | FRED `VIXCLS`, `VXVCLS` (CBOE); Yahoo `^VIX`, `^VIX3M`; live snapshot at 16:00 ET | daily | Official close of D is 16:15 ET. Read from Cboe or Yahoo at that close (value timing, labelled), it is usable at the US close of D+1 and at the KRX close of K ≥ D+1; read from FRED, it is usable from the first decision after FRED's logged posting time (`last_updated`, logged for 20 sessions in M1; history uses that measured lag, declared in the registry). The registry names the production channel of the R-08 annotation. The 16:00 ET snapshot is stamped `live` | C (R-08 annotation; R-13) |
| US 10y yield | **Production:** KIS US 10y yield quote stamped ≤ the US close. **History and end of day:** US Treasury daily par-yield curve (CMT; posting time logged); FRED `DGS10` (H.15); `^TNX` (Yahoo) as a live-feed proxy from 2015 | daily | Treasury: "usually available … by 6:00 PM Eastern Time" on D, so usable +1 business day with a logged posting time. H.15: posted 16:15 ET on the next Fed business day, so strict +2 business days for a US close decision | R (corr63, R-09); X (R-12 refusal book); C |
| DFII10 (10y TIPS), T10YIE, T5YIFR (5y5y), DGS2, DGS30, T10Y3M, T10Y2Y | FRED (H.15-based; same posting rule); Treasury par and real par yields for the CMT legs | daily | H.15 rule, or the Treasury rule with a logged posting time | C |
| Kim–Wright 10y term premium | FRED `THREEFYTP10` (name the model; do not mix it with ACM) | daily (posted with a lag) | as posted | C |
| MOVE | Yahoo `^MOVE` | daily | close | C |
| Broad USD | FRED `DTWEXBGS` (H.10; weekly publication) **and** a labelled live proxy, `USD_LIVE_PROXY`, named in the registry before M2 (default, judgment: the ICE US Dollar Index, Yahoo `DX-Y.NYB`) and read as a quote snapshot stamped ≤ the decision instant (`obs_kind = quote_snapshot`); a vendor daily "close" stamped after the decision instant is never used | daily | H.10 weekly rule; the live proxy at the US close | DTWEXBGS: C. Live proxy: R (`hedge_state`, R-09) |
| USD/JPY | FRED `DEXJPUS` (history); KIS or Yahoo live quote | daily | H.10 rule / live | C; P (FX sleeve) |
| HY OAS; Baa−10y | FRED `BAMLH0A0HYM2` (posts with ≈ 1-day lag; on FRED only since 2023-10); `BAA10Y` | daily | next day | C (backlog BL-C03) |
| Brent | `DCOILBRENTEU` (Dated spot) **and** `BZ=F` (front-month futures); always name which | daily | per source | C; Monte Carlo scenarios and replays |
| Core PCE, PCE, CPI, core CPI | FRED `PCEPILFE`, `PCEPI`, `CPIAUCSL`, `CPILFESL`, with ALFRED vintages; first release (`output_type=4`) and current value | monthly | BEA/BLS release time (BLS 08:30 ET); Oct-2025 CPI is missing | C; core PCE YoY: R (`hedge_state`) |
| UNRATE, SAHMREALTIME, PAYEMS, ICSA | FRED / ALFRED; Sahm also computed in-house from UNRATE (a gap gives NaN) | monthly / weekly | release time; Oct-2025 household data missing | C (first print, current value, vintage date) |
| FEDFUNDS / DFEDTARU; FOMC statements and calendar; SEP Table 2 | Fed; FRED | event | statement time (14:00 ET) | Calendar; C; Monte Carlo priors |
| US EPU (daily) | FRED `USEPUINDXD` | daily | as posted | C |
| VRP inputs (VIX², 21-day realised variance) | derived in-house | daily | inputs' rules | C (R-13) |
| US cash `US_RF`: French daily `RF` (one-month T-bill) for cards on French data (R-28 goldens, R-29 settling run); FRED `DTB3` (3-month T-bill, H.15, converted from its discount basis to a daily accrual) for cards on QUANTGEN's own US data; each card's `cash_convention.cash_series` names one (French `RF` is a per-period return used as published, so its card header omits `cash_convention.day_count`; `DTB3` is an annual rate accrued act_365; R-22 rule 3) | French Data Library; FRED (already QUANTGEN's risk-free source) | daily | H.15 rule (DTB3); as posted (French) | H (cash leg of excess returns for US cards, R-22) |

**Other**

| Series | Source / ID | Freq | Publication / available_at rule | Role |
|---|---|---|---|---|
| Ken French factor files (US daily 5-factor, Mom, ST_Rev; regional Mom daily; monthly 1926+) | French Data Library | daily / monthly | as posted | H (benchmarks, golden values; frozen in test fixtures, md5 per file). The daily Mkt-RF file from 1926-07 is needed for the R-29 settling run (DL-A could not fetch it: HTTP 403) |
| SOX, S&P 500, Nikkei, TAIEX, Shanghai, HSI | KIS (US indices); Yahoo | daily | close, per the general cross-market rule | R (Korea covariance only, `risk_model_covariance`: a failing series is carried, labelled stale, for up to 5 decisions, then dropped from the covariance and labelled; synchronous or lagged returns); C (opening-gap log) |
| US release calendar (BLS/BEA), BoJ/BoK/ECB calendars, hyperscaler earnings dates | official calendars; company IR | event | scheduled time plus status | Calendar (`core/calendars`) |
| Fed, SIFMA, NYSE, KRX, Cboe, CME, JPX, SSE, HKEX and TWSE holiday calendars; KRX session regimes and market-structure dates | official notices; `exchange_calendars` XKRX as a cross-check | effective-dated | each change needs an owner sign-off and one test | Calendar (R-20) |

---

## 5. Rule specifications

**Build status** (what to implement now):
- **BUILD NOW**: implement in v2.0, in the milestone of §12.
- **BUILD-AS-INSURANCE** (v2.0): build the card, its specification-book factor and its forward record now. The factor enters the recommended book only on a formal CARD-P PASS under conditions fixed before the run (R-06 KR).
- **SPECIFICATION BOOK ONLY** (v2.0): computed, labelled with its verdict, never in the recommended book until its card passes (R-04; the R-31 steps while they bind on more than 10% of days).
- **FORWARD-SIM**: a separate forward book in the specification book. Never a recommendation until the card's stated build conditions hold (R-28, R-29).
- **RETIRED** (v2.0): a REJECT recorded on long history. At most a labelled, display-only refusal book that no other book reads (R-11, R-12).
- **DEFERRED**: specified, dormant until the planned sleeve exists.

**Rule kind** (how the gate treats it):
- **INVARIANT**: data discipline, a bound, a risk limit or a risk-model assumption. It is enforced in every operating book (recommended, specification, FORWARD-SIM); inside card evaluation books it follows R-22 rule 6, frozen with the package. It is not a model card and makes no performance claim.
- **CARD-O**: a model card with an outperformance claim. It goes through the standard nine-step gate (§8.1).
- **CARD-P**: a model card with a protective claim. It goes through the protective class, CARD-P gate v2 (§8.7, R-21).
- **CONVENTION**: delays, annotates or prices simulated entries, or sets a sizing default. It is logged and measured, and never claimed as performance.
- **CONTEXT**: logged, never acts.
- **GOVERNANCE** (v2.0): a gate, a schema, a workflow or a break protocol. It governs how cards are built and judged and makes no performance claim (R-18, R-21–R-25, R-30, R-32–R-35).

**The v2.0 row.** Every rule opens with a **v2.0** row:
- its change type, class, priority and milestone from `QC_modules.csv`;
- its acceptance tests (§9);
- its council source items.

**Indicative verdicts.**
- Each card carries the indicative verdict that the data labs (DL-A, DL-B) and R4b point to.
- Where the council stated it, the card also carries its reading under the v2 package. §8.9 gives the full table.
- None of these is a run of QUANTGEN's gate. The formal verdict comes from `docs/macro_overlay_study.py` on QUANTGEN's own data and engine, under the frozen v2 package (P11).

Every rule writes its inputs (with `available_at_utc`, `retrieved_at_utc` and `value_status`), its outputs, its reasons and its card verdict and disposition into the artifacts of §6.

**Timing note for every rule.** Weights are decided at the close of t from inputs available by then, and earn from t+1 (P5, §4.1). The R4 golden values were computed on exactly this convention: a weight built from data through the close of t−1 is applied to the return of t. The exceptions are flagged in §9.3.

### R-01 Point-in-time discipline — BUILD NOW · INVARIANT

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · INVARIANT · P0 · M1. Acceptance: T-PROV-01, T-FIX-01, T-BAR-01, G-POST-01 (§9). Sources: QF2-M1, QF2-M4, QF2-A2, QF1-A3, QF2-A1, QF4-A12, QF6-A12, QF6-M11, QF1-A24, QF2-A23. |
| **Purpose** | Remove the largest source of fake edge, and close the provisional-row hole that the 2-Oct data patch exposed |
| **Where** | `core/ficc/data` (point-in-time store, lag audit, reconciliation); `core/quant/history` (official-close loader); `core/calendars` (`decision_time_utc`, `usable_at`); `tests/run_all.py` (post-close fixtures) |
| **Inputs** | Every series in §4 |
| **Rule** | (1) **Availability.** For every acting input, `available_at_utc ≤ decision_utc`, the official close from the calendar (KRX: `close_print_bound_utc`, 06:30:30Z today). Lags are calendar-based. For Korea apply D ≤ K − 1; for any other market apply the general cross-market rule. H.15, H.10 and Treasury availability come from the Fed business-day calendar (§4.1). <br>(2) **Value status.** A close-type acting input needs `value_status = official_close` and `session_date` equal to the decided session. Otherwise it is `MissingInput("provisional_intraday")` for a non-official status and `MissingInput("session_mismatch")` for a session mismatch. <br>(3) **Official close primary.** KIS/KRX first, vendor second. Reconciliation tolerance is 1 bp (index) or exact (stock); otherwise the value is disputed: the official value is used with `dispute = true` (never a failure; T-BAR-02), an alert is raised, never auto-corrected. A row retrieved before the session close + 10 min, a flat-OHLC zero-volume row on a session day, or a bar-derived value is never stored as a close. <br>(4) **Store.** Append-only and bitemporal (`obs_utc`, `available_at_utc`, `retrieved_at_utc`), with `value_status`, `session_date`, `vintage` and `content_hash`. Reads are as-of a knowledge time. `data_snapshot_id` = md5 of the content hashes visible at that time. <br>(5) **Fixtures.** Frozen only from post-close files, with an md5 per file. A fixture any of whose close-type rows has `retrieved_at_utc` < `close_print_bound_utc` of its session + 10 min, or any of whose publication-timed rows was retrieved before its `publication_instant`, is refused; synthetic store fixtures built by a test (T-PROV-01) are labelled and exempt. <br>(6) **Failure.** A missing, stale, provisional or synthetic input triggers the action of its role (R-19). For an acting input: state unchanged, alert, `fail_closed=true` in `macro_state` for that component; beyond the declared number of consecutive misses → HALTED. <br>(7) **Deterministic replay** of a past decision from the store at its knowledge time, after restoring the runtime state from before it (T-REPLAY-01) is council priority P2 (runs from M8, §9.0a). The priority-P0 core is (2)–(5). |
| **Output** | `macro_state.inputs[]` with `value_status`, `session_date`, `available_at_utc`, `retrieved_at_utc` and role; a `lag_audit` record in every backtest result and on every card |
| **Evidence** | N-46, N-47. Korea gate +0.31 (look-ahead) → +0.05; KRW 0.5× leg +0.07 on DEXKOUS dates → +0.03 with Yahoo timing. Rates leg (R4, gross): +0.038 value timing → +0.010 at +1 business day (compliant via the Treasury par-yield channel) → **−0.000 (share 0.53) at the strict +2 business days (R4b)**. KRW 0.75× leg (gross): +0.032 value timing → **+0.001 (share 0.53) at strict H.10 publication (R4b)**. CPI 3.71% vs 3.35%. **The 2-Oct provisional row (v2.0):** <br>• the vendor row 6,943.66 came from a file written at 10:56 KST, mid-session; its volume (99,651 vs 227,641 final) dates it to about 10:30 KST and passed v1.2's audit; the official close is 7,003.74; <br>• 24 printed values changed (DLA §7), e.g. drawdown from the peak −23.8% → −23.2%, close / 200-day average 1.098 → 1.107, rv20 28.9% → 28.8%, vt decided at the 2-Oct close 0.691 → 0.694. <br>**Other vendor defects:** <br>• Samsung stale-carry rows on 2020-03-09, 2020-03-12 and 2022-01-26, plus 10 more in Jan–Mar 2022; <br>• ^KS11 has no close on 2011-10-04, a real session; <br>• Yahoo omits the Saturday sessions before 1998-12-12; <br>• 069500 has an 800-day hole from 2007-02-08 (QF1-A24). <br>The v1.2 KRX mapping of H.15 leaked on 599 of 2,938 DGS10 observations (QF2-A6). |
| **Failure modes** | Silent forward-fill of weekly H.10 data; positional lags; unnamed series; the "auto" provider silently returning synthetic data for an acting input; vendor publication times unknown (then `available_at_source = inferred_from_retrieval`, an upper bound); KIS stamping receive time rather than exchange time (open question, settled by the first M1 task, QF1-A25); the KIS market-division code and price field that return the KRX regular-session official close, as opposed to an NXT or integrated last price (NXT trades from 15:40 KST, the same instant as the close + 10 min retrieval rule, so retrieval time cannot tell them apart; the code values are UNVERIFIED and are recorded by the same M1 task). Only that field is ever stamped `official_close`; a current-price read is `obs_kind = quote_snapshot`; the OHLC used by range estimators (R-30) is KRX regular-session OHLC from the same field set; an official-source outage (fail closed; never fall back to a vendor intraday print); a two-source tolerance too tight on index rebalancing days |
| **On violation** | Any lag-audit violation invalidates the backtest result or forward record it touches. The card study refuses to write the card. At runtime it HALTs (OPS) the books the input feeds (§3.8). A provisional row reaching an acting input counts as a lag-audit violation. *Exception:* the L ≤ 0 rows of R-34's `timing_probe` sandbox, tagged `synthetic_lookahead = true`, record their violations instead of raising and never write a card verdict or a production artifact (R-34). |

### R-02 Overlay bounds and composition by `min()` — BUILD NOW · INVARIANT

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · INVARIANT · P0 · M2. Acceptance: T-CAP-01, T-CAP-02 (§9). Sources: X-EX1-N2, QF4-A6, QF4-M3. |
| **Purpose** | Enforce P2, P8 and P17 |
| **Where** | `core/rules` validation (rule objects); `core/quant/signals` (`apply_overlays`); `core/quant/risk` (`compose`); artifact schemas (§6) |
| **Rule** | Implement §3.3. <br>(1) `assert 0.5 <= overlay_multiplier <= 1.0`, `assert 0.0 <= vt <= 1.0` and `assert 0.0 <= vs <= 1.0` at the schema, rules-store and code level. <br>(2) **Composition by `min()`:** composed = vt × min(1.0, overlay₁, …, overlayₖ, ladder, post_rearm_cap). A product-composed path raises. Outside HALTED, composed ≥ 0.5 × vt; the floor binds composed, not gross or final weights (P2). <br>(3) Every multiplier record has `exposure_basis ∈ {active, total}`. <br>(4) The overlay layer cannot emit 0; 0× exists only in the risk layer and in HALTED. <br>(5) Each new overlay is judged incrementally on the current recommended book. <br>(6) **Stack card.** Once two or more de-risk factors act in the recommended book, a stack CARD-P is generated and gated (§8.7). It prints the share of days at ≤ 0.25× total exposure and the rebound capture. A **de-risk factor** is a market-level (`exposure_basis = total`) factor carried by a card that can take a value < 1.0 in the recommended book: vt (R-06 KR), R-28, R-29 and the R-31 steps once their card PASSes. Invariants (look-through caps, the hard stop, the post-re-arm cap, R-31 steps acting as `INVARIANT_STEP`) and family-level vs (R-03) are not de-risk factors; the stack card's composed book includes them and prints their binding shares. When several factors pass in one batch, they join in header-commit order, fixed before the run. |
| **Evidence** | N-02, N-03. Four-state table −0.07. Partial de-risking beats hard switching: real-time Markov 0.5/1 vs 0/1, SR 0.554 vs 0.390 (US) and 0.442 vs 0.137 (KOSPI, 2-year initial training window), both net of 10 bp (R2 re-run). R4 KOSPI vol target cap 1.5: SR 0.534 vs 0.638 at cap 1.0 (2016–26, pre-patch R4 pair; 1997–2026: 0.430 vs 0.454). **Composition (v2.0):** <br>• the §3.3 product form made the −12% ladder step 0.25× vt (DLA-D2); <br>• on KOSPI, product stacks sit at ≤ 0.25× total exposure on 31.0% of days vs 11.2% under `min()` (EX1); <br>• product composition captured 7.6% of a 47.3% rebound. |
| **On violation** | Not applicable (invariant): the rules store refuses the rule. At runtime a product-composed path fails the `bounds_ok` gate and HALTs (OPS) the books whose artifact it is (§3.8). |

### R-03 Momentum own-volatility scaling — BUILD NOW · CARD-O (indicative PASS on French data; step 3 borderline)

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · CARD-O · P0 · M4. Acceptance: T-R03-01 (§9). Sources: QF3-A2, QF5-M1, X-PX2-N3, QF5-A4, QF5-A5, QF5-A6, X-PX2-N4, QF3-A14, QF6-A23. |
| **Purpose** | Size every cross-sectional momentum sleeve by its own risk. This is the strongest, most replicated overlay. |
| **Where** | `core/quant/risk.sleeve_vol_scale`; applied in `core/quant/signals` |
| **Inputs (v2.0)** | The daily returns of the sleeve's **paper unit-gross long/short series**: long leg +1 and short leg −1 notional, same ranking as the sleeve. vs is applied to the sleeve's budget; for a long-only sleeve (KIS cannot short), to its long-only active budget. **vs is never computed on the benchmark-relative active series.** On that series the 12% target is inert: long-only active vol is about half the long/short vol (median σ126 5.1% vs 10.1%), and vs falls below 1 on 9.8% of days (average weight 0.978) against 39.4% (0.868) for the golden long/short series (QF5-A4). |
| **Formula (revision 1, registered)** | `σ126(t) = stdev(r_LS[t−125 … t]) × √252` (mean-adjusted sample SD, ddof = 1), using returns through the close of t. The weight decided at the close of t and earning from t+1 is `vs = min(1.0, 0.12 / σ126(t))`. Minimum 126 valid observations, the window extending past excluded days to the last 126 valid returns (as R-06's does); before the book's first ARMED decision `vs = 1.0` and the state is flagged `WARMUP`; afterwards a shortfall is `MissingInput` (§3.5). |
| **Revisions (v2.0)** | Two counted revisions in the R-03 family ledger (R-23). Each has its header md5 committed before its run, is one trial, and passes step 3 at N_eff or fails. <br>• **Revision 2, scale-free target (QF5-M1):** target = the expanding median of σ126 on the same paper long/short series (minimum 252 observations), cap 1.0. <br>• **Revision 3, variance-scaled (X-PX2-N3):** `vs = min(1, (0.12/σ126)²)` on the same series. It takes the trial that a pooled R-04 revision would have used. <br>• If more than one registered revision PASSes, the lowest PASSing revision number acts; this rule is declared before the runs. |
| **Parameters** | Window 126 days; target 0.12 annualised (Barroso–Santa-Clara's published target, chosen ex ante and declared as a card parameter, so any change is a revision; under cap 1 the target sets exposure, and R-03's daily recomputation raises turnover relative to the published monthly scheme); cap 1.0; no floor. |
| **Output** | `overlay_decision.vol_scale`, with `exposure_basis=active` |
| **Evidence (gross)** | N-06. US French Mom 1990–2026: static SR 0.399 → **0.714** (R4, cap 1.0) (+0.31, share 1.00); max DD −63.3% → −27.9%. With cap 2.0, Q1b found 0.907, so the cap costs −0.19 over the full sample, −0.23 in 1990–2007 and 0.000 in 2020–26. Regions (R4, cap 1): Japan 0.073 → 0.196; Europe 0.843 → 1.143; APxJ 0.924 → 1.125, but −0.023 in 2016–26; Developed ex-US 0.799 → 0.996. Literature: D&M *JFE* 2016 Table 7, constant-vol 1.041 vs static 0.682 (1934–2013). |
| **Evidence (net, R4b)** | US shares via KIS, 50 bp per side on the overlay's own turnover (both legs; 0.85 units a year): SR **0.672** (2×: 0.631); ΔSR vs static +0.273 (share 1.00); gate-style one-sided p ≤ 0.001 with 10-session and Politis–White (251-session) blocks; 70% of calendar years positive. French Mom is gross of its own constituent turnover. Leaving that turnover uncosted favours the static sleeve, so the comparison is conservative for the overlay. |
| **Evidence (revisions)** | Scale-free target (QF5-M1 pilot): US full-sample ΔSR +0.380 vs +0.303 for the fixed target; post-2015 +0.278 vs +0.240; Europe +0.268 vs +0.141; Developed ex-US +0.260 vs +0.077; Japan +0.119 vs +0.105; APxJ −0.026 vs −0.047. Variance scaling: +0.126 net, against the D&M gate's +0.072 (PX2). Neither is a verdict: each is a registered trial. |
| **Failure modes** | Lags fast recoveries after vol spikes: May–Nov 2008 relative −17.1%; Apr–Oct 2000 −12.0%. Gains decay after publication with cap 2 (R2-P2): +0.66 (1990–2011) → +0.26 (2012–26). Under this spec's cap 1 (R4) the gain is +0.20 in 1990–2007, +0.20 in 2012–26 and +0.26 in 2020–26: the cap removes most of the pre-publication gain, and the full-sample +0.31 leans on 2008–09. APxJ was negative in the 2020s. |
| **Card** | CARD-O. Benchmark: the same sleeve unscaled, on the same costed engine. **Indicative PASS on the French series, with step 3 borderline.** <br>• Deflated ΔSR 0.98 at N_equiv 6.3, and 0.947 at the linear eq. 9 N̂ 12.6 (break-even N ≈ 11.9). <br>• z 3.84 / 3.29 / 2.99 with 10 / 63 / 240-session blocks, above the one-sided ≤ 8-cell hurdle of 2.50. <br>• Plateau 100% of neighbours; PBO 0.00 (family) and 0.009 (grid). <br>**Years line (v2.0):** the scaled and unscaled sleeves are identical in 17 of 37 calendar years (vs = 1.0 all year). In the other 20, the scaled sleeve had the higher Sharpe in 15 (75%) gross and 11 (55%) net of 50 bp. 70% of calendar years are positive (step 8). The "86%" (a cap-2 statistic) and "40.5%" (ties counted as losses) are withdrawn. <br>The formal card runs on QUANTGEN's own momentum sleeve (US shares via KIS, 50 bp on both legs, as in its evidence; a factor sleeve on US shares is not a US sleeve in D5's sense) in M7, after the package freeze (§8.1.3); the sleeve-scale function is built in M4. Demotion: R-25 (falsification alarms on whole-book NAV); review if the 2016+ ΔSR is below 0 in ≥ 2 regions. |

### R-04 Daniel–Moskowitz bear-state gate, floor 0.5 — SPECIFICATION BOOK ONLY · CARD-O add-on (step 3 FAIL)

| Item | Specification |
|---|---|
| **v2.0** | DEMOTED · CARD-O · P1 · M4. Acceptance: T-R04-01, I-03 (§9). Sources: QF3-A18, QF5-M6, QF5-A1, QF5-A2, QF5-A3, QF5-A16. |
| **Purpose** | De-risk momentum in bear, high-volatility states, where loser rebounds crush the short side |
| **Where** | `core/quant/signals.dm_gate`; specification book only |
| **Inputs** | The sleeve market's index: 24-month total return as of the last month-end on or before t, and 126-day daily realised volatility through the close of t |
| **Formula** | `bear24 = (Π_{24 months}(1 + r_month) − 1) < 0`. `hivol = σ126_mkt(t) > Q_{2/3}(σ126_mkt over [start … t])`, an expanding quantile with at least 252 observations. `dm = 0.5 if (bear24 and hivol) else 1.0`, decided at the close of t, earning from t+1. |
| **Parameters** | 24 months; 126 days; quantile 2/3; multiplier 0.5; `exposure_basis=active`. The trigger is a floored binary heuristic inspired by Daniel–Moskowitz (2016), not the published rule (the paper's dynamic weight is continuous); its expected add-on is about +0.07, not the paper's +0.15. A 200-day moving average is **not** a substitute. |
| **Output** | A family overlay multiplier for momentum, in the specification book |
| **Evidence (gross)** | N-07. *JFE* 2016 Table 7 (1934–2013): dynamic OOS 1.194 vs constant-vol 1.041 vs static 0.682. International (Table 11, the paper's full dynamic strategy, not this floored gate): Europe 0.462 → 1.130, Japan 0.067 → 0.416, UK 0.465 → 0.891. **R4 at floor 0.5:** alone +0.138 (share 0.998). On top of R-03: **+0.084 (0.996)**; ex Sep-2008–Dec-2009 +0.056 (0.97); 2013-04 → 2026-08 +0.055 (0.94). Gate on 10.6% of days; 7 spell onsets since 1990; 0.38 transitions a year. |
| **Evidence (net, R4b)** | 50 bp per side, both legs: add-on +0.072 (share 0.983; 2×: +0.061, 0.958); 2013-04 onward +0.044 (0.92). Gate-style one-sided p 0.018 (10-session blocks) and 0.010 (Politis–White, 229 sessions). |
| **Failure modes** | Misses crashes that follow bull markets: Nov-2020 −12.0%, Jul-2026 −10.9%, Jan-2001 −21.9%, all with the gate at 1.0. Slow: May–Nov 2008 +9.5% vs +21.8% static (R4). Evidence is concentrated in 2 crash regimes per century. Untested on KRX stock data. |
| **Card** | CARD-O add-on. Benchmark: the R-03 sleeve. **Verdict label: "step 3 FAIL".** <br>• On the R-03 family ledger the deflated add-on is 0.77 at N_equiv 6.3 (z 2.08 < 2.50). <br>• The pre-registered BL-C12 holdout passed in 1 of 3 regions. <br>• Onset sufficiency was never the reason: pooled across the US, Europe, Japan and APxJ the trigger has 34 de-clustered onsets (pooled add-on +0.080, p 0.0002, net of 50 bp). <br>**The A-provisional route is closed and no pooled-Tier-A revision is registered:** card validation rejects any A-provisional or pooled route for a card already run (P11). The trial goes to the variance-scaled R-03 revision instead. <br>R-04 runs in the specification book at floor 0.5, labelled. The recommended-book builder refuses it (I-03). The floor stays contested (0 vs 0.25 vs 0.5; BL-C01). |

### R-05 Reversal and quality fixed at 1.0× — BUILD NOW · CONVENTION

| Item | Specification |
|---|---|
| **v2.0** | Unchanged; R-05 is the only rule not in `QC_modules.csv`. Two related council outcomes: the Korea reversal prior moves to 1 (R-15), and owner decision D3 defaults to "not adopted", so QF5-M10's calm-state down-weight stays out (P3). |
| **Purpose** | Keep the liquidity-provision and quality premia without levering into their worst variance |
| **Rule** | The reversal and quality families have **no overlay multiplier** (the value is fixed at 1.0) in every state. They are never up-weighted in stress, and never cut by macro or stress flags. Reversal simulated daily entries are decided at the official close of t and earn from t+1. There is no intraday reversal leg. (v1.0's "limit orders into the closing auction" has no object in a read-only app.) |
| **Evidence** | N-09. On the true VIX ≥ VIX3M flag (2007-12 → 2026-08), ST_Rev earned 59.2%/yr at 34.8% vol (SR 1.70) vs 1.8% at 12.3% otherwise (SR 0.15). μ/σ² is 4.90 vs 1.20, so mean-variance would up-weight in stress, which P2 forbids: the 1.0× rests on P2, not on μ/σ². (The 72% / 13% figures spliced in a VIX > 30 proxy before 2007-12.) 1.5× rules: ΔSR −0.05 to −0.20, and −20.0% relative over Sep-2019 → Mar-2020. RMW at 1.5×: ΔSR −0.01. RMW market beta −0.099 (HAC t −3.0); RMW +8.4% in 2022. Overnight vs intraday reversal: +0.93% vs −1.05% a month (US, 1993–2013). |
| **Net-of-cost requirement** | The reversal family's own card (outside this spec) must clear QUANTGEN's KRX stock cost of 35 bp per side and stay positive at 70 bp. Whether to block reversal in fast stress is contested (backlog BL-C02). v1.0's KIS fill-log test is blocked by the read-only design; BL-C02 now uses KIS quote snapshots. |

### R-06 Per-market continuous volatility target, cap 1.0 — BUILD-AS-INSURANCE (Korea, on a formal PASS) · CARD-P (US 50 bp: REJECT, instrument-specific)

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · CARD-P · P0 · M7 (the `market_vol_target` function is built in M2). Acceptance: I-16 (Korea formal card), T-R06-US-01, T-CAP-01, T-LABEL-01 (§9). Sources: QF4-M1, QF4-A1, QF1-A2, QF6-A7, QF6-M4, QF7-M5, QF7-A21, QF3-A6, QF5-A24, X-EX1-N5, X-PX2-N2, X-PX2-N5, QF1-A1, QF3-A4, QF4-A2, QF5-A23, QF6-A18, QF6-M8, QF6-A13, QF6-A15. |
| **Purpose** | The primary risk control, especially for Korea. It is insurance, not an alpha source: its claim is protective (§8.7), and it is short the post-crash rebound premium. |
| **Where** | `core/quant/risk.market_vol_target`; `core/quant/backtest` (cards); the instrument book is declared on each card (P10, P15, R-26) |
| **Estimator (v2.0; QC resolution 3)** | **SMA20 realised volatility remains the acting sizing estimator and the displayed baseline:** `σ̂_m(t) = stdev(r_m[t−19 … t]) × √252` on daily simple close-to-close returns through the close of t: the mean-adjusted sample SD (ddof = 1, R-30's "sample variance"; it reproduces rv20 28.82% and vt 0.694 on 2 Oct). A flagged stale-carry day is excluded and the window extends to the last 20 valid returns. The registered Korea card and its first formal run use it. <br>**"Validated default" is struck.** SMA20 passes B5, but it sits outside the 90% QLIKE model confidence set at 1, 5 and 21 days in both markets (p ≤ 0.0005), while staying inside the MSE set. Its KOSPI VaR breaches cluster (Christoffersen p 0.0006 on 2016–26, < 0.0001 on 2001–26). B5 is necessary, not selective: it passes 7 of 9 KOSPI and 8–9 of 9 US forecasters. <br>**A challenger replaces SMA20 for a card only through a counted card revision that passes the full v2 CARD-P and the staged estimator gate (R-30):** <br>• Stage 1, calibration at the 21-day sizing horizon: FHS VaR exceedance, 21-day fan PIT, Christoffersen conditional coverage; 1-day Kupiec/Christoffersen and ES 97.5% Z2 printed. <br>• Stage 2, screen: membership of the 90% QLIKE MCS at h = 21 (MSE MCS printed). <br>• Stage 3, choice: lowest vol-of-vol, with ΔMDD and PC-2, net of turnover at the declared book, ΔSR non-inferior. Overlapping bootstrap CIs are ties and go to the simplest surviving model. <br>**COMB = ½(GJR-t + log-HAR-range)** on expanding windows is the registered challenger, for ETF and futures books only, never for the 35 bp stock book. A GJR fit outside its bounds, or a tripped OHLC open-quality flag, falls back to SMA20 (fail-closed). The choice is a tracking and drawdown decision, never a Sharpe claim. <br>**B5 (kept).** B5 pass = 5% VaR exceedance within ±2 binomial SE of 5% over ≥ 200 origins **and** a PIT χ² test (10 equal bins) with p ≥ 0.01. SMA20 in FHS form: <br>• KOSPI 2016–26: 4.70% of 2,594 origins (band 4.14–5.86%), PIT p 0.11; <br>• SPY 2016–26: 4.99% (PIT p 0.57); <br>• US market 1991–2026: 5.31% of 8,961 (band 4.54–5.46%), PIT p 0.98; <br>• KOSPI 1997–2026: 5.04%, PIT p 0.46. <br>EWMA(0.94) also passes everywhere. Long-window GARCH(1,1)-t and GJR-t pass in the same FHS form (KOSPI 2001–26: 5.38% / 5.42%, PIT p 0.98 / 0.87; US 1995–2026: 5.17% / 4.91%). The app's own SPY REJECT (6.6% breaches, PIT p 0.003) is the t-quantile fan-tail form, UNVERIFIED until `docs/vol_backtest.py` and its seed are published; R4b's re-fit agrees (6.3%, PIT p < 0.001). Under a normal quantile every estimator fails PIT, so a σ̂ is never shown as a normal VaR. |
| **Formula** | `vt_m = min(1.0, target_m / σ̂_m(t))`, decided at the close of t (KRX `decision_utc` = `close_print_bound_utc(KR, t)`, 06:30:30Z today), earning from t+1. Composed with the overlays and the ladder by `min()` (§3.3). **Warm-up and degenerate inputs:** with fewer than 20 valid returns `market_vol_target` returns status `insufficient_history`, which each book it feeds maps to weight 1.0 with status `warmup` (not a failure) before that book's first ARMED decision, and to `MissingInput` afterwards (§3.5; card books start after the warm-up); a σ̂ that is 0 or not finite with 20 valid returns is a contract violation, so the component fails closed and counts toward its books' HALT limit (T-VT-01). |
| **Parameters** | Korea: target 0.20, window 20, cap 1.0. US: target 0.15, window 20, cap 1.0. **The cap of 1.0 is permanent**: any vt > 1.0 fails validation. Other markets must be pre-registered per market on their card before they run (**default, judgment**: start from the market's long-run median realised vol). No floor. `exposure_basis=total`. |
| **Instrument book and rebalancing (v2.0, R-26)** | Declared in the header before the run, each as a header field and each variant as one trial: `instrument_book`, `notional_nav`, `rebalance` (daily), `no_trade_band`. <br>• **Korea book:** the KRX ETF line (KODEX 200, 3 bp; the tick floor applies). A KOSPI200 futures line is allowed only where one mini contract (≈ ₩56m) is ≤ ~5% of the declared notional (≈ ₩1bn or more). <br>• **The KRX stock book (35 bp) is not an admissible instrument book for a market-gross scalar** (R-26, §10). Its line is computed for reference only: INSUFFICIENT DATA on 1997–2026, p_ni 0.141. <br>• **No-trade band:** 0.10, declared ex ante, permitted only on stock and US-share books and counted as one trial. Not for ETF or futures lines (no gain at 3–5 bp). Its fast-crash cost is printed (2016–26: +4.4 → +3.2 pp). <br>• The venue is never switched after results (P15, §10 item 23). |
| **Display labels (v2.0)** | Two volatility labels, display only, never gating: <br>• `display_label_rel`: σ̂ against the quartiles of its own trailing 756 sessions; <br>• `display_label_abs`: σ̂ against the quartiles of its expanding full history (≥ 10 years). <br>Both are computed causally from filtered, never smoothed, values. They are volatility labels, not regime states (P19). <br>**Per-label coverage is reported.** On KOSPI 2000–26, SMA20-FHS 5% VaR breaches by label are 6.48 / 6.91 / 3.43 / 3.38% (Kupiec p ≤ 0.004), against 4.7 / 6.6 / 4.6 / 5.0% for FHS-GARCH. The cure for miscalibration is a better σ̂ through R-30, judged by tick loss, never a conformal label layer (§10). <br>The Quant Lab's path colours are renamed "path-vol quartile" (R-16). <br>On 2 Oct 2026 KOSPI was **elevated** (relative: σ̂ 28.8%, 70th percentile; trailing quartiles 15.7 / 18.6 / 33.6%) and **stressed** (absolute). The US was **normal** (relative: 10.7%, 28th percentile). |
| **Inputs** | KRX official closes (Korea); US close (US). Local inputs only. Close-type inputs need `value_status = official_close` (R-01). |
| **Evidence (Korea, gross)** | N-14, N-16. **R4, KOSPI 2016-01 → 2026-10-02:** SR **0.641 vs 0.637** buy-and-hold; max DD −36.8% vs −43.9%. 22 Jun → 30 Jul 2026: **−12.2% vs −38.6%**. Mar-2026: −7.9% vs −19.9%. 2020 crash: −25.8% vs −34.1%. |
| **Evidence (Korea, net, R4b)** | Turnover 1.50 units a year. KRX ETF book (3 bp): SR 0.638 (2×: 0.635), max DD −36.8%. KRX stock book (35 bp): SR **0.609** (2×: 0.576), ΔSR vs buy-and-hold −0.029 (share 0.36), max DD −37.2%. Static book with the same average exposure (0.925): max DD −41.3%, so **ΔMDD +4.4 pp (ETF) / +4.1 pp (stock)**. Jul-2026 window net of 35 bp: −12.3% vs −38.6%. |
| **Evidence (Korea, long history; DL-A, EX1, EX2, PX2)** | **Definitive cell** (1997-04-01 → 2026-10-02, KRX ETF 3 bp, v1.2 checks; DLA-K8): ΔMDD +12.7 pp (2×: +12.5); tail ratio 0.68; ΔSR +0.026 (2×: +0.021); p_ni 0.052; years 70%; plateau 0.875; B5 passes. Indicative PASS, fragile, on v1.2 checks; under v2 the expected verdict is INSUFFICIENT DATA through f (Card row below; §8.9). Futures 5 bp: PASS (+12.6 pp). Stock 35 bp: INSUFFICIENT (p_ni 0.141). <br>**Episodes.** Under the §8.6 table July 2026 carries 0.493 of the PC-4 benefit. Under the objective bear-20 episodes, 14 of 18 are positive (maximum share 0.174), including 10 of the 12 bears before 2008. <br>**Tail metrics 1997–2026:** ΔES99 +1.95 pp (z 4.3); ΔES95 of 21-day returns +2.9 pp (z 2.3); ΔCDaR95 +7.1 pp. SE(ΔSR) 0.066. <br>**Start robustness:** <br>• 71 of 72 monthly starts 1997-02 → 2003-01 PASS; <br>• 23 of 40 quarterly starts PASS, with 0 REJECT (EX1); <br>• ΔMDD ranges from +3.7 to +12.7 pp by start: a 1998-01 start misses the June-1997 peak and gives +3.8 pp. <br>**Conventions:** <br>• excess returns with call-rate cash: ΔSR +0.006, p_ni 0.078, 70% of 33 starts pass (PX2); <br>• ETF era 2002-10 → 2025-12 without 2026: ΔMDD +11.9 pp, p_ni 0.040, PASS (EX2). <br>**Sub-samples:** <br>• 1997–2002 alone: REJECT (ΔSR −0.20; EX2); <br>• 1997–2015: INSUFFICIENT (sufficiency: only 3 §8.6 windows); <br>• 2016–26: INSUFFICIENT; under v2's PC-1′ it moves from passing PC-1 to INSUFFICIENT (ES z 1.82 / 1.13), disclosed and with no build consequence; <br>• 2016–25 alone: REJECT (tail 0.95, ΔSR −0.079). <br>**Other lines:** rolling decades 2 PASS / 3 REJECT / 15 INSUFFICIENT (EX1); timing return −1.8% a year at variance ratio 0.59 (PX2); median re-entry lag after troughs 17 sessions. |
| **Evidence (US)** | **R4 gross, US Mkt-RF 1990-02 → 2026-09:** SR 0.602 vs 0.534; max DD −49.9% vs −59.2%. GFC window −20.9% vs −46.5%. **Net of 50 bp (R4b):** turnover 2.52 a year costs 1.26% a year; SR **0.505** (2×: 0.409), ΔSR −0.028 (share 0.29); max DD −53.8% vs −54.0% for the same-exposure (0.890) static book. <br>**DL-A, US shares via KIS, 50 bp, daily:** ΔMDD +0.2 pp (2×: −3.4), ΔSR −0.028, p_ni 0.146: REJECT on PC-1, a single-path statistic (ΔMDD bootstrap SD 7.8 pp). ΔES99 z 2.37 and ΔES95 (21-day) z 1.85 show protection. <br>**Futures 5 bp (the new card, R-29):** +3.6 pp (2×: +3.2), p_ni 0.002, PASS on 1990–2026. It is a knife edge: 11 PASS / 9 REVISE / 24 REJECT over 44 quarterly starts; 1995+ is a REJECT (+2.9 pp); 1990–2007 gives +0.3 pp. <br>**Rescues that fail:** monthly rebalancing is INSUFFICIENT in every book (GFC share 0.56–0.67); a 0.10 band at 50 bp is a REJECT (+1.8 pp). |
| **Costs (always reported)** | Korea 2016–25 ΔSR −0.077 gross (share 0.06), −0.106 at 35 bp; 2018–24 −0.123 gross (0.03), −0.154 at 35 bp. H1-2026 bull tax: +51.7% vs +101.1% gross (+50.5% at 35 bp). Aug-2024: −7.9% vs −5.5% (missed the rebound). 2020 rebound: +25.9% vs +49.9%. Post-crash 30 Jul–30 Sep 2026: +5.9% vs +22.2%. Cost episodes vs S on 1997–2026: 2009 rebound −6.9 pp, 2020 rebound −15.5 pp, H1-2026 −31.5 pp. |
| **Failure modes** | KOSPI's vol–forward-return correlation is non-negative in most periods (+0.07 in 1997–2017, +0.15 in 2001–26, +0.27 to +0.34 in 2018–24), so the vol target is insurance, never a Sharpe source; it is implicitly short the rebound premium (timing return about −1.8% a year). No help against gap shocks from calm states (2018-10, 2020-02, 2024-08). Slow re-entry after V-rebounds. A 60-day window is worse (KOSPI SR 0.550; pre-patch R4). In the US at 50 bp per side, daily rebalancing of small weight changes eats the drawdown benefit. |
| **Logged alternatives (v2.0)** | **`max(σ̂_SMA20, implied)` is retired.** It embeds the variance risk premium and de-grosses permanently (ΔSR −0.166 at 50 bp). Implied vol is context: VIX/VIX3M at 16:00 ET and KOSPI200 MFIV at 15:30 KST, stamped `live` (R-13). It may enter sizing only inside HAR-IV, and only if HAR-IV wins the R-30 race, read live at the decision time. The asymmetric estimator (slow to cut, fast to restore) stays a logged alternative (BL-C04). Range-based log-HAR and COMB are challengers through R-30, not logged alternatives. |
| **Card (Korea): BUILD-AS-INSURANCE on a formal PASS** | QC resolution 1, binding wording. <br>**Registration.** R-06 KR is registered once, blind, before any v2 card runs, with its header md5 committed: SMA20 σ̂, 20-day window, target 0.20, cap 1.0 (permanent), daily, decided at the KRX close (`available_at` ≤ `close_print_bound_utc(KR, t)`: 06:30:30Z today, 06:00:30Z before 2016-08-01) and earning from t+1. <br>**Book.** The KRX ETF line at 3 bp (tick floor applies). A futures line only where one mini contract is ≤ ~5% of the declared notional (≈ ₩1bn or more). <br>**Data.** KRX official closes (Level-2 tolerance against the vendor file: the raw-flag v1.2-check reproduction on official closes vs G-KR-L01, I-16's data check; R-01's 1 bp / exact reconciliation governs row-level data), Saturday sessions included before 1998-12-12. Start = first close + 20-session warm-up; the history's first close is fixed in the header and the registry (1997-04-01, the definitive cell's; `gate.evaluation.history_start`), so the band of (iii) follows from it. <br>**Conventions.** Excess returns with idle cash at the call rate; objective market-own episodes (KOSPI ≥ 20%) with the §8.6 windows printed; p_ni = max(p₁₀, p_PW); 8-neighbour plateau; the v2 CARD-P gate (R-21–R-24, R-34). <br>**PASS requires all of:** <br>(i) a v2 PASS on the full span; <br>(ii) a v2 PASS on the ETF-era line, from the first full month after KODEX 200's October-2002 listing to 2025-12 (exact date from the KRX listing record, written in the header); <br>(iii) no REJECT at any monthly start 1997-05…1999-12 (32 starts), and a PASS in at least 2/3 of them (at least 22, compared as integers: 3·n_pass ≥ 2·n_starts); <br>(iv) no REJECT in either pre-declared calendar-midpoint half. <br>**Printed, not gated:** the 2002-10 → 2015-12 pre-design line; the ETF-era line to the present; 1997–2002 and 2016–25 alone; rolling decades; PC-4 under §8.6; the EWMA(0.94) line; timing return, years lagging S, the H1-2026 bull tax and the median re-entry lag (17 sessions); the per-regime table (price limits, Saturday sessions, the 1997 peg, ETF availability). <br>**Label:** "Crisis-clustering insurance: reduces drawdown in volatility-clustering crises (1997–98, 2008, 2026); no help against gap shocks from calm states (2018-10, 2020-02, 2024-08); Sharpe non-inferiority is marginal — it pays a premium in calm decades (2016–25 alone: tail 0.95, ΔSR −0.079) and is short the post-crash rebound premium; not expected to outperform; cap 1.0 permanent." <br>**Outcomes.** PASS → BUILD-AS-INSURANCE in the recommended book. INSUFFICIENT → a labelled control in the specification book, re-gated only when new history adds an objective episode (no forward-record route). REJECT → archive. The forward record is a falsification alarm only (R-25). <br>**Selection factor and card-book convention (frozen with the package).** f is computed from the R-06 family ledger by `step3()`, never declared; R4's comparisons of the window (20 vs 60 sessions) and the cap (1.0 vs 1.5) on 2016–26, made before SPEC v1.1, are R-06 ledger rows on part of the evaluation span, so f = N_eff (R-23), taken as the maximum over the defensible row-set readings, and the card prints its verdict at f = 1 and at f = N_eff (§8.9 shows the sensitivity). <br>**Expected outcome (R2-C1).** On current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build: f takes the maximum over the defensible row-set readings, every reading that includes the DL-A seed of §9.5 gives f above 1.282 (indicative f 1.26 on R4's three rows alone, 1.49 with the DL-A grid, 2.87 family-wide), and PC-3 needs p_ni × f ≤ 0.10 at the indicative p_ni 0.078. The status stays BUILD-AS-INSURANCE on a formal PASS (Resolution 1), and no convention may be changed to rescue it (R2-C1; §8.9). The card book excludes the R-07 hard stop and caps and prints a `with_risk_layer` line (R-22 rule 6). <br>**Until the formal run,** `vt(KR)` runs in the specification book and is displayed as a descriptive control with its indicative verdict. The recommended book carries the invariants only. |
| **Card (US): REJECT, instrument-specific** | The registered card stays **REJECT (instrument: US shares via KIS, 50 bp, daily)**. It is a statement about a beta scalar executed in single US shares at retail cost, not about vol targeting. Under v2's PC-1′ it would read INSUFFICIENT DATA (inconclusive: ES21 +1.65 pp, ES126 +3.8 pp, p_ni 0.15). It is **never re-run** and never built. <br>The index-futures card is a new card, **MACRO-R06-US-FUT (R-29)**: one more trial in the R-06 family ledger, run FORWARD-SIM. Monthly and banded 50 bp variants are logged trials, never rescues (§10 item 23). Whether a US sleeve exists at all is owner decision D5. |
| **Demotion** | R-25. Forward records are falsification alarms on whole-book NAV. The CARD-P sign is fixed: forward ΔMDD vs S ≤ 0 means no protection. The false-demotion budget is D4. A bull-market lag alone is the insurance premium, not a demotion trigger. |

### R-07 Korea concentration limits on look-through, and the hard stop — BUILD NOW · INVARIANT (risk limits)

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · INVARIANT · P0 · M5. Acceptance: T-CAPS-01, I-04, I-04b (§9). Owner decisions: D1 (concentration template), D2 (hard-stop level). Sources: QF4-M3, QF4-A5, QF4-A6, QF4-M4, QF4-A9, QF4-A10, X-EX2-N5, QF6-M9. |
| **Purpose** | Control the dominant Korean risk (KOSPI behaves like a two-stock memory-semiconductor book), and give the book a hard stop that can never freeze it |
| **Where** | `core/quant/risk` (look-through exposure, caps, ladder state); `core/engine/runtime` (HALTED, re-arm); `core/engine/evaluator` (the −12% step block, via R-31); `core/rules` (template, instrument metadata) |
| **Concentration limits (QC resolution 12)** | (1) **Look-through.** Korea concentration limits apply to look-through exposure, computed daily from the ETF baskets (the KODEX 200 PDF from KIS or KRX). Leveraged and inverse products count at × L. <br>(2) **Active single-name cap:** w_i − g·b̃_i ≤ 0.05 of NAV, against the benchmark b̃ capped under the template. <br>(3) **Aggregate template** (owner decision D1), read from the rules store. Default **MSCI 25/50**: single name ≤ 22.5% after the buffer; names above 4.5% ≤ 45% in aggregate; checked quarterly and on breach. The daily bound g uses the target levels (22.5% / 45%) on every decision; a "breach" is a look-through weight above the hard levels (25% / 50%) after the prescribed action, which is logged and is the R-07 risk-limit breach of §3.8. On an ETF line every template share, the pair cap of (c) included, is a share of Korea sleeve NAV on look-through (cash in the denominator), met through g as in (4). Alternatives: (a) the domestic fund rule, any name ≤ max(10%, its market-cap weight); (c) a 35% pair cap (Samsung + SK hynix ≤ 35% of the Korea long book), without v1.2's 0.45 trigger. <br>(4) **Meeting a binding cap.** First lower the ETF line's weight: g_KR ≤ min(vt, limit_k / look-through share_k, 0.05 / (s_i − b̃_i) for every name i with s_i > b̃_i), where s_i is name i's look-through share of the line and b̃_i its capped-benchmark weight (the active cap of (2)). An ex-pair stock basket is used only if the owner asks for full Korea beta at the cap, a stock-book card has passed and limit-lock flags exist (R-27). <br>(5) **Semiconductor cap** ≤ 0.50 of Korea sleeve NAV on look-through (cash counts in the denominator), level unchanged (**default, judgment**; reviewed when the pair's share falls below 0.35). On the ETF line it is met like (4): g_KR ≤ 0.50 ⁄ look-through semiconductor share. It is never measured as a share of the invested long book, which an ETF line cannot change (the pair alone is 53.8% of KODEX 200), so it is never a standing breach. <br>(6) **Reported:** the pair's look-through share and risk contribution, on every card and in `macro_state`, with each bound and the binding factor per book (`concentration.by_book`, §6.1). <br>(7) Treat Korea gross as semiconductor exposure in the covariance. Shanghai, HSI, TAIEX and Nikkei stay in the Korea covariance, on synchronous or lagged returns (§4.1). |
| **Hard stop (QC resolution 6)** | At **−15% of book NAV** from the high-water mark since the last re-arm (owner decision D2), the book whose NAV breached enters **HALTED** (0×; class RISK) and logs a governance review event. D2's option (b) is −1.5 σ_book, where σ_book is the book's declared target vol, else its trailing-756 realised vol frozen at each re-arm. <br>**Re-arm (class RISK, §3.8).** It is refused for 10 sessions of the book's primary-market calendar, counted from the first HALTED session, and is then automatic, in backtests and at runtime alike. At re-arm the hard-stop and step references reset to the NAV at re-arm, and for the next 10 sessions a factor `post_rearm_cap` = 0.5 joins the `min()` of R-02 (exposure ≤ 0.5 × vt, not an absolute 0.5 cap); then normal running. A second trigger while HALTED changes nothing. The hard stop is evaluated on the NAV of the book it belongs to, and its HALT applies to that book only (§3.8). <br>The ladder is one risk-layer function on **whole-book NAV**: the NAV of the book id it runs in (§3.8), all of that book's sleeves included, never one sleeve's NAV; per-market attribution is printed only for a book that spans markets. **The hard stop makes no protection claim.** |
| **Steps (R-31)** | −8% from the step reference → 0.5×; −12% → 0.5× plus a new-entry block in the evaluator. Multipliers are totals, never cumulative, composed by `min()` (R-02). Each step lasts at most 21 sessions, after which its reference resets to the current NAV; the hard-stop reference does not reset. The binding share is printed on every card. Where the steps bind on more than 10% of days on the declared book (≈ 19% for KOSPI VT20), they act only in the specification book until the step-down CARD-P (R-31) passes. |
| **Evidence (caps)** | N-17, N-16. The pair was 55.5% of KOSPI market cap (22% at end-2023) and 51.5% of KOSPI200 (13 May 2026). It supplied ≈ 65–69% of the 2025–26 index-point move and 76.6% of September 2026 foreign selling. <br>**On 2 Oct 2026** the pair was ≈ 51% of KOSPI (51–54% by anchor: 51.2% on the Sedaily anchor, 53.6% on the 25-Oct-2024 KRX-weight anchor; re-anchor monthly to an official KRX figure), ≈ 54% of KODEX 200 on look-through (53.8%), and ≈ 75% of KOSPI's 63-day variance. KOSPI–Shanghai daily correlation reached 0.56 in 2026. <br>**Why the v1.2 caps changed.** As an absolute cap, 0.05 of NAV forces the pair to ≤ 10% of NAV: a −39 pp underweight, while the rest of KOSPI returned +30.6% vs +101.1% in H1-2026. On an ETF book it cannot be met at all (Samsung is 20.7% of NAV at g 0.694). The 0.45 trigger was set inside the regime it targets. <br>**History cannot choose the template** (n = 1): Jul-2026 crash −36.3% (25/50), −33.9% (35% pair), −38.6% (KOSPI); H1-2026 +95.2%, +86.6%, +101.1%. Under 25/50 on 2 Oct the gross-route bound is 22.5 / 29.8 = 0.755 and does not bind at vt 0.694; the active single-name bound, at most 0.05 / (0.298 − 0.225) = 0.685, does (§11). |
| **Evidence (hard stop)** | **The literal v1.2 rule never leaves HALTED** (DLA-D1). No new drawdown reference is defined and the NAV is flat while HALTED, so the KOSPI book stays HALTED from 1997-09/10 (714–715 halt cycles; average exposure 1.3%), and the US book from 1990-09 or 2000-10-13 (653–907 cycles). <br>**Hard stop only, with the re-arm** (Executives' check C2): <br>• KOSPI VT20 1997–2026 at −15%: 24 HALTs, Sharpe 0.457 vs 0.46 without a ladder, MDD −56.4% vs −45.3%; at −30% (= −1.5 × 0.20): 6 HALTs, Sharpe 0.471, MDD −44.8%. <br>• US VT15 1990–2026 at −15%: 13 HALTs, Sharpe 0.584 vs 0.592, MDD −46.3% vs −50.3%; at −22.5%: 4 HALTs, Sharpe 0.589, MDD −53.0%. <br>On a single-market Korea book the default fires about four times as often and, on the one path tested, deepened the drawdown; hence a governance event, not a protection claim. <br>**Persistence** (the Kaminski–Lo condition): after an activation, KOSPI's next 21 sessions returned −0.57% vs +0.98% unconditionally; the US +0.57% vs +0.78%. Levels come from the executive panel's risk officer (EC-E-05, B4). |
| **Review** | Not an alpha rule, so not a card; the step-down part is a card (R-31). Card evaluation books exclude the hard stop and caps and print a `with_risk_layer` line (R-22 rule 6); the stack card evaluates them on the composed recommended book (§8.7). The template and the hard-stop level are owner decisions (D1, D2); a change is a logged rules-store revision. Cap levels are reviewed yearly through a rules-store revision. |

### R-08 VIX ≥ VIX3M execution-state annotation — BUILD NOW · CONVENTION (demoted; REJECT as a CARD-P)

| Item | Specification |
|---|---|
| **v2.0** | DEMOTED · CONVENTION · P1 · M5. Acceptance: T-ANNOT-01 (§9). Sources: QF6-M7, QF6-A9, QF6-A10. |
| **Purpose** | Mark the market-priced stress state as an execution-cost state, and measure what it costs to trade in it. It changes no exposure. |
| **Where** | `core/engine/evaluator` (annotation); `core/ficc/macro` (`macro_state.annotations`, context log) |
| **Inputs** | FRED `VIXCLS` and `VXVCLS` (the official close of D is 16:15 ET, §4.1); the VIX/VIX3M snapshot at 16:00 ET, stamped `live` (R-13) |
| **Flag and clearing rule (stated, v2.0)** | `flag(D) = VIX(D) ≥ VIX3M(D)`. The threshold is fixed at parity and **never tuned**. **Clearing rule: the raw parity flag.** The annotation is on for every input date D with VIX(D) ≥ VIX3M(D) and clears at the first D with VIX(D) < VIX3M(D), with no hysteresis. It applies from the first decision after the 16:15 ET VIX close: the US close of D+1 and the KRX close of K ≥ D+1. |
| **Effect** | On every flag day the evaluator writes an annotation (`macro_state.annotations.vix_ge_vix3m`) and requests KIS spread snapshots for the traded lines (subject to the KIS quote-field check, QF1-A25). **No book's weights change**: no BLOCKED decision, no cut, no re-add (an assertion in the book builder). |
| **Evidence** | N-04. After VIX ≥ VIX3M, next-5-day realised vol averaged 36.3% vs 13.6%; next-5-day return +0.50% vs +0.22% (t 1.2, not significant). Forward 21-day realised vol after a flag is 32.9% vs 22.6% on VIX-decile-matched days: a real but small variance signal (QF6). <br>**Flag anatomy** (DLB-T6a, 2007-12-04 → 2026-09-30, 4,735 days): on 10.1% of days; 132 spells, 50.8% of them one day long and 15.9% five days or more; 14.0 transitions a year; de-clustered onsets 64 / 40 / 24 at 20 / 60 / 126 sessions. <br>**The v1.2 evidence rows used a different clearing rule:** 5 consecutive non-inverted closes (72 spells, median 8 days). The "median 79% of the episode drawdown at flag-on" and "cleared 14 Aug 2024" figures belong to that rule; under the raw flag, FRED shows the flag off from 8 Aug 2024. <br>Cut-and-re-add gates: −0.088 Sharpe (−0.185 in 2020–26). |
| **Card (record)** | CARD-P, **REJECT**, computed (QF6; replicated by DL-B). PC-1 and PC-2 fail in 10 of 10 cells, under both clearing rules: <br>• ΔMDD vs S +0.9 / +0.6 pp (US VT15 at 50 / 5 bp), +0.3 / +0.4 pp (KOSPI VT20 at 3 / 35 bp), +0.0 pp (US momentum); −0.1 to +1.3 pp with 5-close clearing; <br>• tail ratio 0.996–0.999; <br>• the block binds on 3.1–9.3% of days (DL-B). <br>A block-only rule cannot cut drawdown much once most of the drawdown has already happened. The flag stays on screen and in logs as an annotation. Switches above 2× the budget of 14 a year are logged for review (a logging rule for this annotation only; card switch triggers follow R-25's 99th-percentile rule). |

### R-09 Hedge-validity state — BUILD NOW · INVARIANT (risk-model assumption)

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · INVARIANT · P1 · M2. Acceptance: T-CORR-01, T-HEDGE-01 (§9). Sources: QF2-A5, X-EX1-N6, X-EX2-N6, QF5-M7, QF4-M7. |
| **Purpose** | Do not count on bond or dollar hedges in the regimes where they fail |
| **Where** | `core/quant/risk.hedge_state`; consumed by VaR/CVaR, stress, and the `core/quant/optimize` covariance inputs |
| **Inputs (v2.0)** | All are `risk_model` inputs (R-19): <br>• core PCE YoY (`PCEPILFE`, calendar lag, available at its release; today's 3.008% sits within revision noise of the 3.0 threshold); <br>• `corr63`, the 63-day correlation of daily US equity returns with −Δ10y, **computed on date-aligned pairs (r_eq(D), −Δy(D)) for D ≤ the last 10y date usable at `decision_utc`; the statistic is lagged, never one leg**. The 10y is the KIS quote at the close in production; in backtests it is DGS10 per strict H.15, or Treasury par yields per the Treasury channel (§4.1); <br>• the labelled live broad-USD proxy `USD_LIVE_PROXY` (§4.2; DTWEXBGS is context); <br>• the equity daily return (`SPX_OFFICIAL_CLOSE`, also corr63's equity leg) and the 10y change. |
| **States** | `hedge_credit_off = (corePCE_yoy ≥ 0.030) or (corr63 > 0) or (any hedge_state input stale or failing; a risk_model_covariance binding never sets it, R-19 rule 4) or (an exception inside hedge_state)` (decimals in the core, §0.3: 0.030 is 3.0%). <br>`hedge_failure = (equity_1d < −1.5%) and (USD_proxy_1d < 0)` (daily), or the weekly version: S&P week < −2% and the `USD_LIVE_PROXY` week < 0 (never DTWEXBGS). <br>`classic_risk_off = (equity_1d < −1.5%) and (USD_1d > 0) and (UST10_1d < 0)`. <br>**`fx_hedge_credit` (display only, v2.0):** no credit while the trailing 26-week correlation of weekly KOSPI returns with ΔUSD/KRW is ≥ 0 (+0.05 on 2 Oct 2026; weeks anchored on the Friday KRX close and the ECOS 15:30 USD/KRW close). |
| **Effect** | When `hedge_credit_off`, the risk layer gives **no diversification credit** to duration-type hedges: it uses `max(estimated corr, 0)` between equity and bond/duration legs in VaR, stress, optimiser inputs and sizing. When `hedge_failure`, it also removes USD/JPY-hedge credit. **No equity-gross effect in any case.** <br>**A stale or failing risk-model input, or an exception inside `hedge_state`, never moves any book to HALTED.** It sets `hedge_credit_off = TRUE` and raises an alert; an operator alert follows two missed releases. `fx_hedge_credit` changes no exposure. <br>Cross-asset regimes (turbulence, absorption ratio) stay in the risk model and the display, never as multipliers. A turbulence-based stressed covariance may replace the stock–bond-regime input only if it beats it in a pre-registered test. |
| **Evidence** | N-28, N-29. Pooled stock–bond correlation (1990–2026) by core PCE: −0.29 (< 2%), −0.11 (2–3%), +0.21 (≥ 3%). Bonds rallied +6.4 bp on the worst 5% of equity days in 2000–20 vs 0.0 bp in 2021–26. USD rose in 10 of 11 S&P drawdowns, but in Apr-2025 the DXY fell 3.9%, the 10y rose 28 bp and the S&P fell 5.4%. After USD↓ and equities↓ weeks (n = 14), the S&P returned +7.27% over 13 weeks vs +2.84% unconditional, so this is **not** a de-risk signal. <br>**v2.0:** <br>• corr63 on date-aligned pairs is +0.542, against −0.094 under v1.2's literal series-lag reading; the two readings agree on the state on only 53.6% of days (QF2-A5). Recomputed: +0.53 (S&P vs −ΔDGS10, 30 Sep 2026). <br>• The conservative default is right: bonds lost in 65% of US equity-down months after a positive trailing stock–bond correlation, against 27% otherwise (EX1). <br>• The won as a hedge: the weekly KOSPI–ΔUSD/KRW correlation was −0.31 (1990s), −0.43 (2000s), −0.53 (2010s) and −0.35 (2020s). The won weakened in 12 of 16 KOSPI bear markets but failed in 1998, 2002–03 and Jul-2026, and the trailing state has no forecasting power (EX2). <br>• Turbulence predicts realised vol, but not given past realised vol (t −1.4 to +0.6; QF5). |
| **Failure modes** | 1990–99 had positive correlation even with core PCE below 2%. corr63 is noisy. QUANTGEN has no bond sleeve, so the effect is mainly on risk-model assumptions (the Bonds and Rates pages and the Portfolio optimiser). |

### R-10 Event calendar, entry windows, opening-gap nights and multi-session gaps — BUILD NOW · CONVENTION

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · CONVENTION · P1 · M5. Acceptance: I-06, I-06b (§9). Sources: X-EX2-N2, QF2-A14, QF7-A28, QF1-A14. |
| **Purpose** | Handle scheduled risk with short no-new-entry windows, not blackouts, and tag the sessions whose risk a 1-day model understates |
| **Where** | `core/calendars` (event store, windows, KR opening-gap nights, gap tags); `core/engine/evaluator` (BLOCKED decisions on simulated intraday entries); `core/quant/risk` (VaR display scaling); the Macro and Derivatives pages (annotations) |
| **Calendar entries** | `{event_id, type, region, scheduled_utc, status ∈ {scheduled, released, cancelled, delayed}, source}`. Windows expire automatically when an event is cancelled. Example: the Oct-2025 CPI was never published. |
| **US CPI / NFP (08:30 ET)** | No new US intraday simulated entries 08:25–10:00 ET; entries resume at 10:00 ET. For releases with documented pre-release drift (ISM, consumer confidence, IP, GDP preliminary and others), the window starts 30 minutes before the release. No simulated stops are placed inside the window. Daily book unchanged. |
| **FOMC (14:00 ET)** | No new US intraday simulated entries 13:45–15:00 ET. Resume at 15:00 if VIX < its pre-14:00 level, else at 15:30. No pre-FOMC long. Daily book unchanged. The same windows apply to KOSPI200 night futures. |
| **BoK decision and press conference (v2.0: two events)** | KOSPI200 futures: no new simulated entries 09:45–10:15 KST around the rate decision (released at about 09:50 KST) and 11:00–11:45 KST around the governor's press conference (about 11:10 KST). The decision and the press conference are stored as **two separate events, each with its own status**. The two windows cover two events; the release times do not conflict. Equity daily book unchanged: BoK days run at 0.82× normal abs(r). |
| **Every KRX day** | No new intraday simulated entries in the first 30 minutes of the regular session (09:00–09:30 KST; 10:00–10:30 KST on 10:00-open days: the first trading day of the year and CSAT days), per `time.markets.KR.open_no_entry_minutes`. Signals use KRX regular-session prints only. Daily decisions are taken at the official close (P5). v1.0's opening-auction limit orders and closing-auction routing have no object in a read-only app. |
| **Korea opening-gap event nights** | US CPI/NFP nights, FOMC nights (03:00/04:00 KST) and hyperscaler capex/earnings nights. The next KRX session gets `kr_open_gap_event=true`. The overnight SOX, S&P, ΔUST10 and USD/KRW moves are logged as opening-gap inputs. **No exposure change.** The flag and the realised opening gap feed backlog BL-U03. |
| **Multi-session gaps (v2.0)** | A KRX session that follows more than one US session since the previous KRX close (Seollal, Chuseok, substitute and election holidays) carries `gap_sessions = n_US ≥ 2`, `kr_open_gap_event = true` and a `KRX_HOLIDAY_GAP` calendar event. Its displayed 1-day VaR scales σ by √max(n_US, 1). A KRX session with n_US = 0 (the NYSE was closed, e.g. the KRX session of 2026-11-27 after Thanksgiving) carries `gap_sessions` = 0, no gap event and an unscaled VaR. Post-holiday sessions are reported separately in the Quant Lab backtests (R-16). **No gross rule.** The 2027–28 out-of-sample breach check is pre-registered. |
| **Sidecar / circuit breaker** | No new simulated entries for 30 minutes after a circuit-breaker reopening. Quotes read during a halt are marked indicative, as the Derivatives page already does for a board read while the market is closed. A limit-locked name is non-fillable at the close (R-27). **No gross cut** (contested; backlog BL-C05). v1.0's "queue orders, no market orders, cancel resting orders" needs a broker path and moves to the backlog's blocked section. |
| **Oil / geopolitical** | Scheduled or known risk windows (OPEC, weekend escalations) are calendar entries with a `scenario_tag` for Monte Carlo and the replay library (R-16). No exposure gate. |
| **Invariant (v2.0)** | **No event tag changes any weight.** Windows produce BLOCKED decisions for new intraday entries only; tags and gap flags are annotations and display inputs (an assertion in the book builder). |
| **Not built** | 24-hour blackouts; daily-book blackouts; quad-witching blackout; momentum decision-day size-down (backlog BL-O02). |
| **Evidence** | N-37, N-38, N-40, N-41, N-44. S&P on FOMC days +5.5 vs +5.1 bp (2015–26). Pre-FOMC drift 44.5 → 9.2 bp (not significant). FOMC days 2021–26: abs(r) 97 vs 74 bp. Day after FOMC, KOSPI abs(r) 0.78% vs 0.92%. Quad witching abs(r) 0.851% vs 0.894% (t −0.38). The prior US session explains ≈ 15% of KOSPI variance jointly (SOX, S&P, ΔUST10, ΔVIX, Brent; ≈ 10% for the S&P alone); SOX(t−1) β 0.247 (0.559 in 2026); ΔUST10(t−1) t −3.8. 80.9% of 9–10am volatility interruptions fire in the first 30 minutes. KOSPI +17.91% on 31 Jul 2026 after a capex reaffirmation. <br>**Multi-session gaps (EX2, 2001–26):** <br>• n_US = 1 (5,620 sessions): mean z² 1.18, FHS 95% VaR breach 4.8%; <br>• n_US = 2 (180 sessions): z² 2.06, breach 12.2% (Kupiec p 0.0002); <br>• n_US ≥ 3 (46 sessions): z² 2.47, breaches 17.4% at 95% and 8.7% at 99%. <br>Welch t on z² 4.78. Example: 3 Mar 2026, after weekend strikes and the 2-Mar substitute holiday: −7.24%, then −12.06% the next day. |
| **Measurement** | Log every window hit and every evaluator BLOCKED decision. Log the KIS quote spread and 1-minute range around each window once the KIS quote-field check confirms bid/ask and timestamps (QF1-A25). Print the overnight/intraday attribution line on every card (R-26). Before the opening-gap flag is kept as "log only", run an event-conditional variance test (DM on the squared gap) on the local hourly bars and daily opens (QF7-A28; backlog). Review after 12 months of logs (backlog BL-C02 and BL-O06). |

### R-11 S1: USD/KRW leg — RETIRED · CARD-P (REJECT on 1997–2026 at every timing; refusal book only)

| Item | Specification |
|---|---|
| **v2.0** | RETIRED · CARD-P · P1 · M8. Acceptance: T-REF-01, I-03 (§9). Sources: QF2-A8, QF2-M8, QF4-A3, QF2-A24, X-EX2-N4. |
| **Status** | **Retired from FORWARD-SIM with its REJECT recorded on long history** (QC resolution 8). It leaves the re-gate queue: BL-S01 is closed, and BL-G04 and BL-D13 drop to P3. It may persist only as a labelled, display-only refusal book that no recommended or specification book reads (I-03). |
| **Definition (kept for the record)** | `krw20(t) = ln(USDKRW(t) / USDKRW(t−20 obs))` on a timestamped 15:30:00 KST snapshot or the ECOS 15:30 close, stamped ≤ the KRX close of t. `flag = krw20 > 0.03`. Multiplier `0.75` on Korea market gross (`exposure_basis=total`), decided at the KRX close of t and earning from t+1, **in the refusal book only**. **One-sided**: no action when the KRW strengthens. |
| **Inputs, if ever needed** | The ECOS 15:30 close (731Y003, item 0000003; 15:00 before 2016-08-01), or a timestamped 15:30:00 KST snapshot, because onshore USD/KRW trades 24 hours from 6 Jul 2026. DEXKOUS is a labelled proxy only: it differed from the Seoul close by up to +5.8% in a crisis (30 Dec 1997), and it prints on Seoul holidays. FX-regime metadata (the 1997 peg, bands, smoothing) is recorded with the input. |
| **Record (REJECT; DL-A, KOSPI 1997-04 → 2026-10)** | REJECT at every timing, in both books, on PC-1 and PC-2: <br>• strict H.10: 54 de-clustered onsets, ΔMDD vs the static book −1.3 pp, tail-exposure ratio 1.004; <br>• holiday-aware strict H.10: 54 onsets, −1.3 pp; <br>• value timing: 74 onsets, −1.7 pp; <br>• Yahoo KRW=X lagged two sessions (2004+): 69 onsets, +0.3 pp. <br>The ECOS 15:30 history moves the first 1997 firing by one session, to 28 Oct 1997, with 56–58% of the fall already done; it cannot change the verdict. Under the timing gate (R-34) its fragility ratio is 0.49: borderline, and moot. |
| **Golden (R4, gross, value timing; traceability)** | ΔSR vs buy-and-hold **+0.032 (share 0.967)**; on top of VT20 **+0.042 (0.977)**; +1-session or Yahoo timing **+0.016 (0.76–0.78)**. On 9.0% of days; 65 raw / 35 de-clustered onsets (2015–26); 11.1 transitions a year. The 0.5× reference reproduces +0.060. |
| **Golden (R4b; traceability)** | **Strict H.10, gross:** +0.001 (share 0.53) on buy-and-hold; +0.013 (0.74) on VT20; 26 onsets de-clustered at 20 sessions. **Net, value timing:** KRX ETF 3 bp +0.029 (0.94); KRX stock 35 bp **−0.008 (0.32)**; on VT20 at 35 bp −0.007 (0.34); at 70 bp −0.057 (0.01). Turnover 2.51 a year. |
| **Failure modes** | Near-zero coverage of the worst days of Aug-2024, Dec-2024 and Apr-2025. Off on 4 Dec (−1.44%) and 9 Dec 2024 (−2.78%). Silent in Jul-2026, when the KRW strengthened 7.4% during the −38.6% crash. Its 28 triggers since 2015 (R2 episode rule) were followed by +0.48% over 20 days vs +1.10% unconditional, so it is neither a capitulation nor a continuation signal. It also failed in the 1997–98 won crisis, where it fired late (QF2). |
| **Evidence** | N-22 (CONTESTED in v1.x: professors split on timing and sign stability; executives Moderate). Settled by the long history: QF2-A8, QF4-A3, DLA-L1. |

### R-12 S2: US rates-stress leg — RETIRED · CARD-P (REJECT at every timing and cost; refusal book only)

| Item | Specification |
|---|---|
| **v2.0** | RETIRED · CARD-P · P1 · M8. Acceptance: T-REF-02, I-03, T-PLACEBO-01 (R-12 flagged timing-fragile) (§9). Sources: QF2-A7, QF2-M7, QF3-A24, QF4-A18. |
| **Status** | **Retired from FORWARD-SIM with its REJECT recorded at every timing** (QC resolution 8). BL-S02 is closed. It may persist only as a labelled, display-only refusal book that no recommended or specification book reads (I-03). The Treasury par-yield channel is recorded in the registry (§4.2). |
| **Definition (kept for the record)** | `d10(t) = y10(t) − y10(t−20 obs)`, in percentage points, on the **KIS US 10y quote** stamped ≤ the US close of t. `flag = d10 > 0.40`. Multiplier `0.5` on **US duration-sensitive gross** (`exposure_basis=total`), decided at the close of t and earning from t+1, **in the refusal book only**. Scope: all US long-only equity exposure. Excluded: momentum and other long/short factor sleeves (momentum 0.5× under rates stress: −0.065), and Korea (only 12 onsets; +0.002 in 2024–26; backlog BL-C07). |
| **Backtest timing** | DGS10 (H.15/FRED) dated D is posted at 16:15 ET on the next Fed business day, after that day's close, so strict H.15 timing uses it from the close of **D+2 business days**. Treasury's daily par yield for D is "usually available … by 6:00 PM Eastern Time" on D ("may be delayed"), so with a logged posting time it is usable from the close of **D+1 business day**: compliant via the Treasury par-yield channel. The ^TNX close dated D is a live-feed proxy (2015+). |
| **Record (REJECT; DL-A, US 1990-02 → 2026-09)** | 71 onsets at every timing (39 in 1990–2007, 32 in 2008–26). REJECT at every timing and every cost, including gross: <br>• strict +2 business days: ΔMDD −3.5 pp at 50 bp (ΔSR −0.120), +0.8 pp at 5 bp, +0.9 pp gross; tail 0.995; <br>• Treasury +1 business day (compliant): −3.1 pp at 50 bp (ΔSR −0.105), +0.1 pp at 5 bp, +0.3 pp gross; 2 of 11 episodes; <br>• value timing: −0.8 pp at 50 bp; <br>• ^TNX live proxy: −1.5 pp at 50 bp. <br>Tail ratio 0.99–0.995 throughout. ΔSR −0.120 ± 0.022 at 50 bp is a powered rejection (MDE80 0.046). **Timing-fragile:** it loses 75% of its edge with one extra session of lag (fragility ratio 0.75 in QF2; 0.74 from its printed L-grid; either way > the declared 0.5); the timing gate flags it (R-34). G-US-02a reads "compliant via Treasury with logged posting time". |
| **Golden (R4, gross; traceability)** | US 1990-02 → 2026-09, value timing (**not compliant**: DGS10(D) at the close of D): ΔSR vs buy-and-hold **+0.038 (share 0.98)**; on top of VT15 cap 1 **+0.037 (0.97)**; 2020–26 on VT +0.132 (0.999); ex-2022 +0.025. +1 business day (compliant via the Treasury par-yield channel): **+0.010 (0.67)** over the full sample, of which −0.017 in 1990–2007. 2015–26: DGS10 timing +0.066 (0.98), ^TNX live proxy +0.071 (0.97), +1 day +0.071 (0.94). On 6.2% of days; 50 onsets de-clustered at 60 sessions (71 at 20 sessions); 7.2 transitions a year. Proxies (value timing): NDX 2008–26 +0.039 (0.94); Russell 2000 2015–26 +0.058 (0.97). |
| **Golden (R4b; traceability)** | **Strict +2 business days, gross:** full sample **−0.000 (share 0.53)**; 1990–2007 −0.034; 2008–26 +0.025 (0.77); 2015–26 +0.053 (0.90); 2020–26 +0.084 (0.92); on VT15 −0.007 (0.39), 2020–26 +0.106 (0.94). **Net of 50 bp** (turnover 3.60 a year = 1.80% a year): value −0.065, strict **−0.103 (share 0.00)**; ^TNX 2015–26 −0.020 (0.31); on VT15 strict −0.120. |
| **Failure modes** | Off in Aug-2024 (10y −21 bp), Apr-2025 (move too fast for a 20-day window) and Jul-2026 (+30 bp max). On for only 2 days in Mar-2026, near the low. Post-onset 60-day max DD −7.07% vs −7.17% unconditional: it works through persistence, not prediction. Threshold grid median ≈ +0.01. **State (refusal book only):** the flag is on in data dated 23 Sep 2026 (+50 bp to 30 Sep). Under strict timing the refusal book applies it from the decision at the close of 25 Sep, earning from 28 Sep. |
| **Evidence** | N-24 (ONE-SIDED in v1.x: executives Moderate; the professors' real-yield regime finding, N-26, is consistent with it, but they did not test this leg). Settled: QF2-A7, QF3-A24, QF4-A18, DLA-L2. |

### R-13 Context log — BUILD NOW · CONTEXT (never acts)

**v2.0.** CHANGED · CONTEXT · P1 · M6. Acceptance: T-CTX-01, T-CTX-02 (§9). Sources: QF2-M6, QF7-A24, QF1-M5, QF4-M8, QF6-M6, QF6-M10, QF5-M7, QF2-A20, QF4-A23.

**Scope.**
- The log is computed daily in `core/ficc/macro`, written to `context_log` (§6.4), and never read by any acting module. The lag audit and an import guard (T-CTX-01) enforce this.
- It absorbs the existing 18-indicator sheet under §3.6.
- **Every item carries `vintage` and `retrieved_at_utc` (v2.0).** Revised series store the first print, the current value and the vintage date.

| Item | Definition | Why it is context, not a gate |
|---|---|---|
| Sahm (real-time) | `SAHMREALTIME`, plus Sahm computed in-house from UNRATE (a gap gives NaN), the U-3 3-month change and the ICSA 4-week average | Caught 9 of 9 recessions since 1960, with a median lag of +2 months after the start (range −4 to +3 months). Jul-2024 0.53 was followed by 26 months without recession (N-30). FRED's Sahm series (real-time and current vintage) span the missing Oct-2025 observation (SAHMCURRENT shows 0.25 for Oct-2025), so their values across the gap are tagged `vendor_derived_across_gap`. |
| 10y–3m and recession probit | `T10Y3M`. Probit `P = Φ(−0.6045 − 0.7374 × spread)`, where spread = monthly GS10 − TB3MS converted to bond-equivalent (Estrella–Trubin published coefficients, 1959–2005). Do **not** log 10y–2y as a prior. | 534-day inversion; P = 0.744 in May-2023 with no recession. 10y–2y was false in 1982, 1998 and 2022–24 and missed 2020 (N-30). |
| Taylor-rule residual range | EFFR minus a family of rules `R = r* + π + 0.5(π − 2) + a·gap`, with π = core PCE YoY, r* ∈ {0.5, 1.0, 2.0}, gap ∈ {Okun 2×(NROU − UNRATE), CBO 100×(GDPC1/GDPPOT − 1)}, a ∈ {0.5, 1.0}. Report the min–max range only. | The residual is smaller than its specification uncertainty. Currently 0.4–2.3 pp below the rules; central −0.9 pp (N-30). |
| Real yield and term premium | `DFII10` level and 20/63-day change; `THREEFYTP10` (named "Kim–Wright"); `MOVE`; 2y, 10y, 30y | 2026 is a real-yield / term-premium regime: TIPS +100 bp vs breakeven +11 bp YTD (N-26) |
| Breakevens | `T10YIE`, `T5YIFR`; yearly all-day Δbreakeven / Δnominal β | An anchoring monitor (N-26, N-32) |
| Credit | HY OAS and BAA10Y levels and 21-day changes | Late, no mean content (N-13) |
| FX | Broad USD (DTWEXBGS plus live proxy), DXY, USD/JPY and its distance to the 160–164 zone, USD/KRW (ECOS 15:30 or a timestamped 15:30:00 KST snapshot) | N-29, N-52 |
| Oil | Dated Brent, BZ=F and their spread | N-44 |
| Inflation and labour | Core PCE YoY, CPI YoY, core CPI YoY (calendar lag); payrolls and unemployment with first prints and vintage dates | Hedge state uses core PCE (R-09). 2025 payrolls averaged +119.4k a month in first prints and +9.7k in the current vintage, with 1 vs 6 negative months: the brief shows "known then" and "known now" (QF2-M6) |
| Korea | Pair share of KOSPI (and KODEX 200 look-through); KOSPI rv21 and its trailing-3-year percentile; investor-type flows; BoK rate; the KOSPI trend state (SMA10m) | N-17, N-19, N-21. The KOSPI trend state is context only (R-28 has no Korea instance) |
| **Leverage and flow (v2.0)** | KOFIA margin debt; single-stock and index leveraged-ETF AUM and value traded; the leveraged share; once acquired (BL-U01). The 16 Jul 2026 rule change is logged as a structural break: new single-stock leveraged-ETF listings suspended, deposit raised from ₩10m to ₩30m, LP divergence limit cut from 3% to 2% | Every proxy is uninformative today: absorption-ratio shift t −0.19; turbulence t 1.33 incremental; KODEX leveraged share t −3.59, the wrong sign. The volume version of the leveraged-ETF monitor failed out of sample (QF1, QF4) |
| **Variance risk premium (v2.0)** | VRP = VIX²/12 − 21-day realised variance; KOSPI MFIV² − RV once logged | US 1-month out-of-sample R² −10.7% (daily RV); KOSPI 1-month −4.7% (QF6-M10) |
| **Live implied-vol snapshots (v2.0)** | VIX/VIX3M at 16:00 ET; KOSPI200 model-free implied variance at 15:30 KST; both stamped `live` | Implied vol may enter sizing only inside HAR-IV if HAR-IV wins the R-30 race, read live at the decision time; `max(SMA20, implied)` is retired (R-06) |
| **Turbulence and absorption ratio (v2.0)** | Kritzman turbulence and absorption ratio (500-day window, half-life 250, N/5 eigenvectors), display only | Turbulence predicts realised vol (t 3.5–6.2) but not given past realised vol (t −1.4 to +0.6). As an overlay on top of the vol target it is REJECT or INSUFFICIENT everywhere (QF5-M7). Never a multiplier; a stressed-covariance use needs a pre-registered win (R-09) |
| Policy | FOMC decision, vote split and dissent direction; SEP Table-2 error bands (when released) | N-30, N-56. SEP bands feed Monte Carlo priors (R-16). |
| EPU | `USEPUINDXD` | Variance only (N-04) |
| Existing sheet items | Each of the 18 indicators of `core/ficc/macro` not listed above, with its causal z-score | §3.6 rule 1 |

### R-14 Time-series trend sleeve — BUILD NOW (family configuration) · CARD-O (diversification claim; not computed)

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · CARD-O · P2 · M7. Acceptance: T-R14-01 (§9). Sources: QF5-A26, QF5-A11, QF5-A9, QF5-A8. |
| **Rule** | A diversified, vol-scaled TS-trend sleeve: 12-1 month sign, monthly rebalance. Per-asset weight `= min(1.0, 0.15 / σ_12m)`, with σ_12m the mean-adjusted SD of the last 12 monthly returns × √12 (both default, judgment: Q1b used 15% with cap 2.0; this spec caps at 1.0 per P2). Base weights per §5 R-15. **Exempt** from all overlay multipliers and from the market vol target. Subject to risk-layer caps and the hard stop. Costs per venue (P10). |
| **Header (v2.0)** | The card declares, before the run: <br>• its **instrument book**: `multi_line`, with `instrument_lines[]` naming each index's futures or ETF line and its venue cost, never a stock book; <br>• its **claim: CARD-O, diversification**, i.e. correlation and drawdown behaviour against the equal-weight long-only basket, not outperformance. <br>A header without both is refused. |
| **Evidence** | N-33. An equal-weight vol-scaled 12-equity trend book: SR 0.449 at this spec's cap 1, correlation with the S&P 0.03 (SR 0.49 and correlation 0.08 at cap 2; 0.60 with 16 assets; 2001–26); the correlation is 0.34–0.36 in 2013–26, so "genuine diversifier" is not a standing claim. KOSPI SMA10m vs the same-exposure static book: ΔSR +0.076, ΔMDD +4.1 pp, but the daily tail ratio 0.93 fails PC-2, it adds +2.2 pp on VT20 and −2.3 pp on 2016–26: weak protection, context only. (The earlier "long/flat 0.47 vs buy-and-hold 0.52" priced flat months at 0% with no static comparator.) KOSDAQ ≈ 0. Trend dead in Europe, the UK and India since 2013. |
| **Failure modes** | 2020: −16.7% vs S&P +16.3%. KOSDAQ was fully long into −39.7% (Feb–Jul 2026). It is not fast-crash protection; it is slow-bear protection with century-long evidence (US 1927–2026: ΔMDD +15.9 pp). |
| **Card** | CARD-O, benchmark = the equal-weight long-only basket of the same indices. QUANTGEN's card E1 (trend switch on US ETF sleeves) was REJECTED on an outperformance test: OOS Sharpe 0.84 vs 0.95, p 0.75. The ETF page withholds trend as a signal, so this sleeve is displayed descriptively until its own card passes. v2.0 registers the diversification claim as the card's claim. The protective trend axis is a separate CARD-P for US and non-Korean sleeves (R-28); the KOSPI trend state is context only. |

### R-15 Per-market factor priors — admissibility filters and base weights · CONVENTION

**v2.0.** CHANGED · CONVENTION · P0 · M4. Acceptance: T-PRIOR-01 (§9). Sources: QF5-M4, QF4-A15, QF4-M5, QF5-A14.

**Mapping (binding; QC resolution 12).**
- **Base weight.** base_weight(m, f) = IV_m × 1/K_m over the admissible families of market m.
  - A family is **admissible** in market m if its prior is ≥ 1 and its card is not REJECT.
  - K_m is the number of admissible families.
- **Sums.** The family weights 1/K_m sum to 1 in each market, and Σ_m IV_m = 1, so no weight exceeds 1.0.
- **IV_m.** Inverse-vol weights on weekly returns from EWMA λ 0.97; a Ledoit–Wolf 156-week line is printed beside it. No HRP or minimum-variance; ERC only for multi-asset sleeves. IV_m spans the markets whose sleeves exist in the composite (`core/quant/optimize`); D5 = none removes no existing factor sleeve, only the US market-gross line.
- **The integers.** The 0–3 values below are admissibility filters and display scores only.
- **Resolving the table.** A range prior "a–b" not resolved per index resolves to its lower bound for admissibility and is printed as the range. Flow and quality have no column: flow takes §2.2's prior where one exists (Korea 3); a family with no registered prior in a market is not admissible there until a prior is registered as a rules-store revision (to be confirmed by the owner or council before M4; §8.10). A family whose card is NOT_RUN stays admissible, except ts_trend, which enters the recommended book only on its own PASS (R-14).
- **Tilts.** A bounded tilt is allowed only after the family's own card passes, as a registered revision. Rules-store validation refuses a tilt without a PASSed family card.
- **Verdict changes.** A card verdict change updates admissibility from the next decision. A family-card REJECT shrinks K_m and raises the other families' base weights by K/(K−1): the one place a verdict raises a weight. It is logged as a governance event and printed (T-MONO-01).

| Market | XS momentum | ST reversal | TS trend | Flag |
|---|---|---|---|---|
| US | 2 if vol-scaled with the D&M gate, else 1 | 1 (prior) | 3 | ONE-SIDED (N-35) |
| Europe | 3 | 1 (prior) | 0–1 (STOXX50 0, DAX 1, FTSE 0–1) | ONE-SIDED (N-35); TS trend CORE (N-33) |
| Japan | 0 (vol-scaled R4 SR 0.196: may rise to 1 if verified) | 2 (prior) | 1–2 | ONE-SIDED |
| Korea | 12-1: 0; 12-7 / residual: 1 | **1 (v2.0; was 3)**: UNVERIFIED until BL-U02 runs net of 35 bp plus the 0.20% sell tax | KOSPI 1, KOSDAQ 0 | **UNVERIFIED** (N-36): no KRX stock-level test yet. The −2.950 Fama–MacBeth coefficient is a regression slope, not a strategy return |
| Taiwan | 1 (prior) | 3 (prior) | 1–2 | TS trend CORE (N-33) |
| China A | 0 (prior) | 3 (prior) | 0 | TS trend CORE (N-33) |
| India | 3 (prior) | 1 (prior) | 1 | TS trend CORE (N-33) |
| EM broad | 3 | 1 (prior) | — | ONE-SIDED (N-35) |
| Crypto | 1 (prior) | 2 (prior) | 2 (own trend plus vol cap; QUANTGEN's card C3 is the trend part) | N-54 (deferred) |

**Evidence for the mapping.**
- Walk-forward 2000–26 over 6 regions × 5 factors: equal weights reach Sharpe 1.337, against 1.068 for the rolling-Sharpe rule (BL-O01) and 1.152 for shrinkage. This is DeMiguel–Garlappi–Uppal's 1/N result applied to factor families.
- Across markets, inverse-vol ≈ equal weight (0.421 vs 0.434); minimum-variance gives 0.326.

**Prior calibration (one-sided, professors).** When converting published Sharpe ratios into priors, haircut them by the factor-specific out-of-sample declines in Ilmanen et al. (2021): value −49%, momentum −23% (not significant), carry ≈ −25%, defensive no decline, multifactor −18%. The gate's live haircut (40% off out-of-sample Sharpe; `live_sharpe_multiplier: 0.60`) is printed on every card in addition, with the card's Harvey–Liu haircut.

**Owner decision D3.** A calm-state down-weight of reversal (QF5-M10: reversal × 0.5 when VIX(t−1) ≤ 20) would make a stress variable a mean gate and break P3. The default is **not adopted**; BL-O08 stays P3. It may be reopened only after a KRX stock-reversal test net of 35 bp plus the 0.20% tax shows 0.5× in calm beating 1.0× at one-sided p ≤ 0.10 in both 2010–17 and 2018–26.

### R-16 Quant Lab calibration, tails, grading and replays — BUILD NOW (Quant Lab; `core/quant/garch`, `core/quant/montecarlo`, `core/ficc/ratesim`) · CONTEXT

| Item | Specification |
|---|---|
| **v2.0** | CHANGED · CONTEXT · P1 · M9. Acceptance: I-11 (§9). Sources: QF6-M3, QF6-A5, QF6-A20, QF4-M9, QF6-A14, QF6-M8, QF7-A23, X-PX1-N4, X-EX2-N2, QF6-A3, QF3-A23. |
| **Rules** | (1) **Fits on expanding windows.** GARCH and GJR parameters are fitted on expanding windows of at least 10 years, with tails by FHS and a GPD on the lower 10% of standardised residuals (McNeil–Frey). QUANTGEN's 504-close window ending 2026-09 is regime-captured: GARCH-t persistence ranges 0.27–1.00 across 303 monthly refits, and the latest fit implies a 61% unconditional vol. A 2015–24 fit understates 2026 tails: KOSPI rv21 was above 30% on 88% of 2026 days (mean 56.5%, max 102.6%), vs 8.6–14.5% of days in 2024–25. <br>(2) **One estimator family sizes: SMA20 (R-06).** It changes only through the staged gate (R-30). The GARCH(1,1)-t fan keeps its own label (REJECT on SPY in the t-quantile form; UNVERIFIED until `docs/vol_backtest.py` and its seed are published, BL-G01). EWMA ≈ GARCH for KOSPI at one day; a long-window GARCH is better at 5–21 days, and the 504-window GARCH is worse than both. Log-HAR on daily ranges (range-target design, with an overnight leg for KOSPI and Parkinson for the US, whose index open is unreliable before about 2008) is admitted to the R-30 race at the 21-day sizing horizon. A 1-day VaR display comes only from a model that passes 1-day B5 (log-HAR-range narrowly misses it on KOSPI: 5.58% vs 5.56%). Intraday realised variance is an upgrade, not a prerequisite. **ML vol-state classifiers stay prohibited** (§10 item 11). <br>(3) **Display and self-grading.** The lab shows the envelope max(fast FHS, GJR-EVT), with Kupiec and Christoffersen conditional-coverage lines at 95% and 99%, the ES 97.5% Z2 line (simulated critical values), Basel zones and fan PIT at h = 21 and 126. It reports 2016–26 and 2026 separately. It reports post-holiday sessions separately, and scales the displayed 1-day VaR by √n_US after multi-session gaps (R-10). It reports per-label coverage of the vol labels (R-06), scored by tick loss. Path colours are renamed "path-vol quartile". <br>(4) **Scenario library, all seeded and reproducible:** <br>• (a) the 2026 vs 2022 oil-shock replays at +20 days (2026: KOSPI −15.5%, USD/KRW +5.2%, 10y real +32 bp; 2022: KOSPI +0.4%, USD/KRW +2.1%, 10y real −4 bp); <br>• (b) the Jul-2026 KOSPI leverage unwind (−38.6% in 27 sessions); <br>• (c) the Aug-2024 carry unwind; <br>• (d) the Apr-2025 tariffs; <br>• (e) SEP Table-2 short-rate error bands as rate-path uncertainty (±1.4 pp at 1 year, Dec-2023 SEP; an RMSE band of about 70% coverage, so a 90% fan needs about ±2.2 pp; read the latest SEP). <br>Rate paths go through `core/ficc/ratesim` (Vasicek / CIR / Hull-White), not through a log-return price model (architecture review C3). Every scenario names its Brent series. <br>(5) **Historical-replay library (v2.0)**, run on the current simulated book with regime metadata (price limits, the 1997 peg) attached to each replay: 1997-11/12, 1998-03→06, 2000-04-17, 2001-09-12, 2008-10, 2020-03, 2026-03-04 and 2026-06-23→07-30. GMM scenario regimes stay deferred behind it (CONTESTED, QF5-M9) and are never labelled as a current regime (P19). <br>(6) **Outputs are descriptive.** No lab output is read by a sizing module. |
| **Evidence** | N-48, N-44; architecture review B5, C3; public page "the lab grades itself". **v2.0 pilot** (QF6-M3, KOSPI 2001–26, 6,346 days): <br>• GJR-EVT: 99% VaR breaches 0.91% (Kupiec p 0.47), conditional-coverage p 0.19, ES Z2 −0.07 (p 0.23), Basel red 0 / yellow 2; <br>• the lab's GARCH-t-504: 1.48%, Z2 −0.47; <br>• the lab's GBM-504: 2.25%, 5 red. <br>At h = 21 every fan sits within ±2 SE; at h = 126 the lab models fail PIT (p 0.001–0.007). In 2026 every slow model under-covered (GJR-EVT 95% 6.5%, 99% 2.7%), and fast SMA20-FHS did best. After multi-session gaps, FHS 95% breaches reach 12.2% (n_US = 2) and 17.4% (n_US ≥ 3), against 4.8% (EX2). |

### R-17 Planned sleeves — DEFERRED (specified now; build when the sleeve exists) · CONVENTION

**v2.0.** CHANGED · CONVENTION · P2 · M10. Acceptance: T-CRYPTO-01, T-FX-01 (§9). Sources: QF2-M9, QF2-A22, QF1-A18, QF5-A19, QF5-A20.

**Clocks and instruments (v2.0).**
- **CRYPTO clock.** `decision_time_utc('CRYPTO', d)` = 00:00:00Z on d+1, the close of the venue's daily bar dated d (that bar opens at 00:00:00Z on d), declared per venue (Upbit, Binance, CoinGecko). Annualisation uses 365 days. Weekday macro data are joined as-of, with staleness labels. FRED's CBBTCUSD is stamped at 5 PM Pacific and is never mixed with UTC candles.
- **FX instrument.** An FX sleeve card declares its instrument, KRX USD futures or broker spot, before the run. A card without it is refused. FX costs 10 bp per side (P10).

**FX sleeve (N-52).** QUANTGEN's Rates & FX page currently withholds FX momentum and dollar carry as signals. Any FX sleeve is a new card set at FX cost (10 bp per side), on its declared instrument.
- **Never forecast FX direction from rate differentials.** USD/JPY Fama b was −1.92 (1991–2007) and 0.11 with R² 0.000 (2008–26). USD/KRW monthly R² was 0.022.
- **Carry is a crash-prone premium.** Size it small. De-risk it on:
  - a USD/JPY trend break (0× below the 50-day average reduced the 10 Jul → 5 Aug 2024 loss from −10.6% to −2.9%, but ΔSR was −0.07 in 2015–26: a cost in calm years). That 0× belongs to a sleeve-level risk limit, not to an overlay (P2).
  - JPY rv21 in its top quintile → 0.5× (+0.06 in 2008–26; +0.09 in 2015–26).
  - **Not** on VIX, which read 12.85–16.36 until 31 Jul 2024.
- **Confirmed intervention:**
  - FX momentum × 0.5 for 20 sessions, and simulated stops × 1.5;
  - no bet on a re-breach;
  - USD/JPY 160–164 is the hazard zone (flag at the prior intervention maximum − 1.5%).
- **Long-KRW carry:** skew −2.38, worst quarter −36.9% (Q4-1997) on monthly-average FX; on quarter-end point-in-time FX, which tail calibration must use, skew −1.80 and worst quarter −43.8%; the current rate differential is −0.75 pp (negative carry).

**Crypto sleeve (N-54).** QUANTGEN's crypto desk already has a trend rule that passed the gate: card C3 on KRW-BTC, plus the BTC-USD card. The macro overlay adds only:
- an own risk bucket: BTC's own vol target as a CARD-P plus a hard gross cap (risk layer), on the 24/7 clock above;
- the BTC–equity β, estimated on rolling data; the weekly BTC–NDX correlation was 0.09, 0.47–0.50 and 0.22–0.24 across the three sub-periods on Wednesday-anchored weeks (0.06, 0.28 and 0.25 on Friday-anchored weeks; BTC trades at weekends, so the card declares its anchor);
- no net-liquidity or M2 input (§10).

### R-18 Policy-break, scale-break and market-structure protocol — BUILD NOW · GOVERNANCE

**v2.0.** CHANGED · GOVERNANCE (was INVARIANT) · P2 · M6. Acceptance: T-BREAK-01 (§9). Sources: QF7-M6, QF7-A19, QF7-A18, QF7-M4, X-PX2-N6.

**Policy breaks (v2.0).**
- **Trigger (i), acting now: an official framework change.** Examples: a central bank's statement on longer-run goals and strategy changing its reaction-function framework, or the end of yield-curve control. On such an event, every **macro-conditioned** multiplier is shrunk to 1.0 and a forward record starts; there is no historical re-gate. In v2.0 no macro-conditioned multiplier acts in any book, so the trigger applies to future cards.
- **Removed as a trigger: "a sign flip in the policy direction."** A direction flip is cyclical, not a framework break; the FEDFUNDS series shows at least 10 reversals since 1990. "A new chair is not a new rule": policy-direction states must allow sign flips.
- **Trigger (ii), logged only: a statistical break flag** on the reaction-function residual (CUSUM or BOCPD on EFFR minus the midpoint of the Taylor range logged in R-13). It is written to the R-18 research log. It becomes a trigger only after EX1's test: ≤ 1 false break a decade on 1990–2026, with flags within 6 months of the 2012 and 2020 framework changes (backlog).
- Evidence: N-50; PC-P-29; QF7-A19.

**Scale breaks (v2.0).**
- Thresholds re-anchor **only on declared events**: an R-18 log entry for a market-structure or framework change, effective-dated in the calendar (R-20), with the re-anchoring window stated on the affected card's header. Re-anchoring is logged as a counted card revision under the full package, with no lockout of its own; it never lifts a demotion or an R-25 lockout, and only events whose effective date follows the header commit qualify.
- The v1.2 statistical trigger (realised vol above 2× its trailing 3-year median for 60 sessions) is demoted to a logged flag. It fired twice in KOSPI 1999–2026 (2008-12-10, 2026-08-11) and 4 times in the US since 1990, after the episode trough in 5 of the 6 cases.
- **BOCPD research log.** A BOCPD scale-break probability (hazard 1/250, declared prior) may be written to the R-18 research log. It is never acting, never displayed, and nothing in R-18 depends on it (P19). It over-fires on fat tails; in 4 of 6 historical cases it flagged 63–119 sessions before the v1.2 trigger.
- Percentiles alone do not cure a scale break: a trailing 3-year p90 of KOSPI rv21 was still exceeded on 72% of 2026 days. The relative display-label quartiles (R-06) use a trailing 756-session window and re-anchor automatically; they are display only.

**Market-structure break log (v2.0, X-PX2-N6).**
- Korean market-structure breaks become effective-dated tags in `core/calendars` (R-20) and R-18 log entries: short-sale bans, the sell tax (0.30% → 0.15% → 0.20%), tick-size reforms, leveraged-ETF rules (16 Jul 2026), and session changes.
- A card whose sample straddles a break prints the split.
- Futures cards print a ban-period basis line.
- **No gross rule:** EX2 found no index-level short-ban break.

<!-- SPEC v2.0 (Quant Council edition), part B1: rule specifications R-19 … R-35.
     Insert at the end of §5, after R-18. Sources of truth: council/QC_modules.csv (ids, names, classes, priorities,
     milestones, acceptance tests), council/QC_COUNCIL_RESOLUTIONS.md (Resolutions 1–12, red lines, owner decisions D1–D5),
     the chair files, the data labs QX_DLA / QX_DLB and the papers QF1–QF7. -->

### Rules added or rewritten by the Quant Council (R-19 … R-35)

**How to read these entries.**
- The heading gives the build status (BUILD NOW, FORWARD-SIM or SPECIFICATION BOOK; defined in §8.1.2), the class (INVARIANT, CONVENTION, CARD-O, CARD-P or GOVERNANCE; §8.2), the council priority and the milestone of §12.
- Every entry has the same fields, in this order: Purpose · Package / module and functions · Inputs (PIT fields) · Rule / algorithm · Config keys · Outputs and schema fields · Fail-closed behaviour · Acceptance tests · Source items · Evidence.
- **Config keys** are written as YAML for the rules store and must be merged into §7. Every number is explicit, because the store has no financial defaults. An owner decision is written `owner_decision: D<n>` with the council default; the default applies until the owner rules.
- Function and file names marked **proposed** may be renamed. Fields, thresholds, formulas and tests are binding.
- **Acceptance tests** go into `tests/run_all.py` and are hermetic (frozen fixtures, §9). Numbers quoted in them are the data labs' values. Tolerances are Level 1 (§9.3) unless stated.
- R-21, R-22, R-23, R-24 and R-34 form the **v2 gate package**. It is frozen and adopted blind, once, before any formal card run (§8.1.3).
- R-32, R-33 and R-35 are short entries. Their content is materialised in §6, §10 and §3.9.

### R-19 Data contracts: schedule-aware staleness with role-based failure actions — BUILD NOW · INVARIANT · P0 · M1

**Purpose.** *NEW in v2.0.* The v1.2 staleness defaults (1 trading day, 3 days, 1 release cycle) measured staleness from the observation date. Under them, the H.10 inputs are stale at 100% of decisions, so a literal build that HALTs on a stale input halts every day. R-19 does two things:
- it measures staleness against each source's **publication schedule**;
- it makes the failure action depend on the input's **role** and on the **books** it is bound to, so that only an acting-exposure input can ever HALT a book, and only a book it feeds (§3.8).

This answers owner question Q.2 #2 of the backlog: both of its readings fail (Resolution 7).

**Package / module and functions.**
- `core/ficc/data`, the per-series data contract (`contracts.yaml` next to the series registry, **proposed**):
  - `contract(series_id) -> DataContract`;
  - `expected_available_utc(series_id, last_obs_date) -> datetime`;
  - `is_stale(series_id, decision_utc, knowledge_utc) -> StaleCheck`;
  - `on_input_failure(series_id, check) -> FailureAction`;
  - `usable_cross_market(market, obs_date, decision_utc) -> bool`.
- `core/calendars`: publication calendars and source-exception lists (R-20).
- `core/quant/risk.hedge_state`: reads the conservative default (R-09).
- `core/engine/runtime`: the HALTED trigger reads the role and a per-series consecutive-failure counter kept in `core/engine/state`.

**Inputs (PIT fields).**
- From the registry row: `series_id`, `source`, `channel` (e.g. `FRED_H15`, `TREASURY_PAR`, `KIS_LIVE`, `ECOS_1530`), `bindings` (per consumer: `role ∈ {acting_exposure, forward_sim, risk_model, context, history}` and `books`), `schedule_id`, `grace_pub_bdays`.
- From the PIT record (R-01): `obs_date`, `session_date`, `available_at_utc`, `retrieved_at_utc`, `value_status`, `vintage`.
- The decision instant `decision_utc`, which for a decision at a close is the close-print bound of R-20.

**Rule / algorithm.**
1. **Contract.** Every registered series has a contract with these fields:
   - schema: dtype, unit, decimals in the core;
   - range: e.g. |r_KOSPI| ≤ 30%, VIX ∈ [5, 150], yields ∈ [−1, 20]% (QF2-M3);
   - monotone `obs_date`;
   - publication schedule and grace;
   - cross-source tolerance (R-01's two-source reconciliation);
   - role and failure action.

   An acting input without a contract cannot be registered: rules-store validation refuses it.
2. **Expected availability.** The expected instant comes from the effective-dated publication calendar (R-20):
   - **H.15** (DGS10 and every H.15 series): 16:15 ET on the next **Fed** business day after D (QF2-A6);
   - **H.10** (DEXKOUS, DTWEXBGS, DEXJPUS): the week's observations are published at 16:15 ET on the following Monday, or on the next Fed business day when that Monday is a federal holiday (QF2-A10);
   - **Treasury par-yield curve**: about 18:00 ET on D ("usually available … by 6:00 PM Eastern Time"; "may be delayed"). The scheduled 18:00 ET is the expected instant for staleness; the logged (first-seen) posting time is the record's `available_at_utc`;
   - **BLS**: 08:30 ET. **BEA**: its release calendar;
   - **market closes**: the session's close-print bound (R-20).

   Some dates are legitimately skipped by the source: the Good-Friday bond-market closures, 2017-01-20, 2018-12-05, 2020-11-27, 2020-12-24, and the DC storm closures of 2016-01-22 and 2018-03-02 (QF2-A3, DLA-S1). They sit in a versioned, owner-signed exception list in `core/calendars` and generate no expected observation.
3. **Staleness.**
   ```python
   def is_stale(series, decision_utc, knowledge_utc):
       rec = pit_last(series, decision_utc, knowledge_utc)   # latest record with available_at_utc <= decision_utc, retrieved_at_utc <= knowledge_utc
       if rec is None:
           return Stale("missing")
       d_next = cal.next_expected_obs(series, rec.obs_date)        # skips source-exception dates
       due = cal.publication_instant(series, d_next)               # schedule rule of step 2
       deadline = cal.add_publication_bdays(series, due, contract(series).grace_pub_bdays)   # default 1
       return Stale("missed_release") if decision_utc > deadline else Fresh()
   ```
4. **Failure action by role.** The role is declared in the registry (Resolution 7):
   - **`acting_exposure`:**
     - the input returns `MissingInput`; the component's state is unchanged; `fail_closed = true`; an alert is raised;
     - the runtime keeps, for every book the input is bound to, an input counter (consecutive decisions at which that input failed closed; reset at its next fresh decision) and a book counter (consecutive decisions at which any acting input bound to the book with the default limit failed closed; reset at a decision at which all of them are fresh);
     - the book enters HALTED (class OPS, §3.8) when an input counter reaches that binding's `halt_after_consecutive_decisions` (default 2, i.e. "more than one decision"; the KODEX 200 basket declares 5) or the book counter reaches 2, so two inputs failing on alternate decisions still HALT the book;
     - only books the input is bound to count: an acting input bound to no recommended book (the US close while D5 = none) never HALTs a recommended book (P4), and an input bound only to the specification book HALTs the specification book only.
   - **`risk_model`** (every `hedge_state` input, R-09):
     - `hedge_credit_off = TRUE`;
     - `hedge_failure` is computed from the labelled live USD proxy;
     - an alert is raised, with operator escalation after 2 missed releases;
     - the input **never** moves any book to HALTED; an exception inside `hedge_state` takes the same conservative default;
     - a binding used only in a covariance (`risk_model_covariance`, e.g. the Asian indices in the Korea covariance) carries the series' last valid covariance terms, labelled stale, for up to 5 decisions (default, judgment), then drops the series and labels it; the displayed risk prints the covariance status.
   - **`context`:** the item is labelled `stale` in `context_log`. Nothing else happens.
   - **`forward_sim`:** that FORWARD-SIM book fails closed (its multiplier is carried) and alerts; it never HALTs another book. **`history`:** read by the card harness only, never by a weight decision; a span the series does not cover refuses the card (R-22).
   - **Not failures:** a `warmup` input, before the book's first ARMED decision only (the factor's neutral value 1.0, status `warmup`; afterwards a shortfall is `MissingInput`, §3.5) and a disputed official close (the official value with `dispute = true`, status `disputed`) never increment a counter (§3.5).

   A contract violation is treated as a missing input, with the same role-based action. Contract violations are: a value out of range, a schema error, a non-monotone date, or a provisional row for a close-type input (R-01).
5. **Role assignments (binding):**
   - KRX and NYSE official closes that feed `vt` → `acting_exposure`, bound to their market's specification book, and to its recommended book only while that market's vt card is PASS (R-06 KR: BUILD_AS_INSURANCE); while it is NOT_RUN or INSUFFICIENT, vt enters the recommended book as 1.0, so the close is not bound to it (§3.8: a book is never HALTed by an input it does not read). The US close is bound to no book while `sleeves.US.line = none` (D5);
   - the labelled live broad-USD proxy, core PCE YoY, and the equity and 10y inputs of corr63 (the KIS 10y quote in production; DGS10 history in backtests) → `risk_model`;
   - **DTWEXBGS → `context`; it is never an acting input**;
   - the R-11 inputs (DEXKOUS, `ECOS_1530_CLOSE`, `USDKRW_1530_SNAPSHOT`) → `context` (refusal book); `USDKRW_1530_SNAPSHOT` (live) and `ECOS_1530_CLOSE` (history) also carry a `nav_fx` binding for every book holding a non-KRW instrument (R-26), with the role of the book it values: `forward_sim` for R-29's FORWARD-SIM book, `acting_exposure` for a recommended or specification book once D5 creates a US line; the R-12 input, the US 10y, has a `context` binding for its refusal book beside its `risk_model` binding for corr63;
   - each book's NAV price inputs (§3.8, NAV valuation): the official close of every instrument line the book holds (e.g. KODEX 200, 069500, for the KR ETF line), declared as the registry group `NAV_LINE_CLOSES` and bound with consumer `nav` to every book that holds the line, with the role of the book it values (`forward_sim` for a FORWARD-SIM book, otherwise `acting_exposure`), as `nav_fx` is. Their failure is §3.8's whole-book-NAV trigger, an OPS HALT after more than 2 consecutive decisions (`halt_after_consecutive_decisions: 3`; R-25), and `pit_value` never raises for the NAV consumer (T-SER-02);
   - FORWARD-SIM inputs (the S&P close for R-28 and R-29; R-28's non-Korean month-end closes) → `forward_sim`; R-22's cash series → `history`; the KODEX 200 basket and the pair and KOSPI market caps → `acting_exposure` (recommended and specification books); R-03's paper long/short series and R-04's inputs → `acting_exposure`, bound to the specification book. **Bindings follow admission (R2-C4).** A factor input bound to the specification book is also bound to the recommended book while `verdict_filter` admits that factor there (R-03's series; the KOSPI close for R-06 KR): the runtime derives each binding's book list at every decision from the admissions, without editing the `roles` entry, and every change of a derived binding (an admission or a demotion) is logged as a governance event in the same run. A load-time assertion refuses any book that reads a factor whose acting inputs are not bound to it (T-ROLE-02, T-SCOPE-01 (g)).

   Roles are bound per (series, consumer, books), never per series: a series with several consumers has several bindings, each with its own failure action (the S&P close: R-28 and R-29 → `forward_sim`; corr63 → `risk_model`). A scalar entry in `data_contracts.roles` means its market's recommended and specification books; an acting or forward_sim mapping entry without an explicit `books` list is refused at registration (T-ROLE-02); an explicit `books: []` registers a dormant binding and is allowed. A series with no binding may be read only by a `context` consumer (R-13); `pit_value` raises for any other consumer that has no binding for the series (T-SER-02). A group id in `roles` (`ASIA_INDEX_CLOSES`, `KRX_MARKET_CAPS_005930_000660_KOSPI`, `NON_KR_INDEX_MONTH_END_CLOSES`, `NAV_LINE_CLOSES`) or a range-group name in `ranges` (`US_TREASURY`, `KR_CALL_CD`) is declared as a group in the registry, and T-SER-02 resolves it to its member series ids; a group name is never a series id.
6. **General cross-market availability (QF2-A21).** A close of market M dated D is usable at `decision_utc` if and only if `close_print_bound_utc(M, D) + buffer < decision_utc` (R-20).
   - Example: from 2024-11-05 the TSE closes at 15:30 JST, which is 06:30Z, the same instant as the KRX close. A same-date TSE close is therefore never usable at the KRX close on a normal day; on a CSAT day the CSAT bound (07:30:30Z) admits it (T-XMKT-01).
   - Covariances use synchronous or lagged returns only.

**Config keys** (merge into §7; this replaces v1.2's `time.max_staleness`):
```yaml
data_contracts:                                      # R-19
  staleness_rule: schedule_aware                     # stale iff decision_utc > expected_available_utc(series, last_obs) + grace, where
                                                     #   expected_available_utc = when the NEXT obs after last_obs is due (R-19 step 3)
  grace_publication_bdays: 1                         # Resolution 7
  source_exceptions: core/calendars/data/source_skipped.yaml   # owner-signed, versioned
  on_failure:
    acting_exposure: {action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books,
                      book_counter_halt_after: 2}   # "more than one decision"; per (book, series) and per book (R-19 rule 4)
    risk_model:      {action: conservative_default, set: {hedge_credit_off: true},
                      hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never,
                      also_on: hedge_state_exception}
    context:         {action: label_stale}
    forward_sim:     {action: fail_closed_that_book, alert: true, halt: never}
    history:         {action: refuse_card_if_span_not_covered, alert: true, read_by_weight_decisions: false}
    risk_model_covariance: {action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never,
                            sets_hedge_credit_off: false}   # default, judgment (R-19 rule 4)
    not_failures:    [warmup_before_first_armed_decision, disputed]
  cross_market: {rule: "close_print_bound_utc(m, D) + buffer < decision_utc", buffer_s: 60}    # buffer: default, judgment
  ranges: {abs_daily_return_max: {KOSPI: 0.30}, VIXCLS: [5, 150], yields_pct: {US_TREASURY: [-1, 20], KR_CALL_CD: [-1, 40]}}   # Korean rates ran at 16-25% in 1997-98
  roles:                                             # bindings per (series, consumer, books); a scalar acting entry means its
                                                     #   market's [recommended, specification] books (R-19 rule 5)
    KOSPI_OFFICIAL_CLOSE: {role: acting_exposure, books: [specification]}   # + the recommended book while verdict_filter admits R-06 KR (R-19 rule 5); vt enters it as 1.0 until then
    US_SLEEVE_OFFICIAL_CLOSE: {role: acting_exposure, books: []}      # no US sleeve while sleeves.US.line = none (D5)
    NAV_LINE_CLOSES: [{role: acting_exposure, consumer: nav, books: [recommended, specification], halt_after_consecutive_decisions: 3},
                      {role: forward_sim, consumer: nav, books: ["forward_sim:R-28", "forward_sim:R-29"]}]   # group (registry): each held line's official close, e.g. KODEX 200 (069500); a card's books bind their lines the same way (R-19 rule 5)
    SPX_OFFICIAL_CLOSE: [{role: forward_sim, consumer: R-28_R-29, books: ["forward_sim:R-28", "forward_sim:R-29"]},
                         {role: risk_model, consumer: corr63},
                         {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}]
    SOX_CLOSE: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}
    KODEX200_PDF: {role: acting_exposure, books: [recommended, specification], halt_after_consecutive_decisions: 5}
    KRX_MARKET_CAPS_005930_000660_KOSPI: {role: acting_exposure, books: [recommended, specification]}
    MOM_PAPER_LS_SERIES: {role: acting_exposure, books: [specification]}   # + the recommended book while verdict_filter admits R-03 (R-19 rule 5)
    DM_MKT_RET_24M: {role: acting_exposure, books: [specification]}        # R-04
    DM_MKT_VOL_126: {role: acting_exposure, books: [specification]}        # R-04
    NON_KR_INDEX_MONTH_END_CLOSES: {role: forward_sim, books: ["forward_sim:R-28"]}
    USD_LIVE_PROXY: risk_model                       # one named series (§4.2), read as a quote snapshot stamped <= the decision instant
    PCEPILFE: risk_model
    US10Y_KIS_QUOTE: [{role: risk_model, consumer: corr63}, {role: context, consumer: R-12_refusal_book}]   # production
    DGS10: [{role: risk_model, consumer: corr63_backtests}, {role: context, consumer: R-12_refusal_book}]   # strict H.15
    ASIA_INDEX_CLOSES: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}   # Nikkei, Shanghai, HSI, TAIEX
    DTWEXBGS: context                                # never acting
    DEXKOUS: context                                 # R-11 retired; labelled proxy
    ECOS_1530_CLOSE: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx_backtests, books: ["forward_sim:R-29"]}]   # nav_fx history (R-26)
    USDKRW_1530_SNAPSHOT: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx, books: ["forward_sim:R-29"]}]   # nav_fx (R-26, R-29)
    BOK_CALL_RATE: history                           # R-22 cash leg (card harness only)
    US_RF: history                                   # R-22 cash leg (card harness only)
```

**Outputs and schema fields** (schemas in §6, R-32).
- `macro_state.inputs[]` gains `role`, `expected_available_utc` and `stale_deadline_utc`, and its `status` enum gains `stale_missed_release`.
- `macro_state.fail_closed` and `alerts[]`.
- `macro_state.flags.hedge_reasons[]` ⊆ {ok, risk_model_input_stale, risk_model_exception, corr_positive, core_pce_ge_3} (causes can co-occur).
- `context_log.items[].stale`.
- The runtime's per-book `halt = {class: OPS, reason_code: "acting_input_stale:<series_id>", …}` in `macro_state.runtime[]` (§6.1).

**Fail-closed behaviour.**
- The role-based actions of rule 4 apply.
- An acting input with no contract is refused at registration.
- If the publication calendar cannot be read, every acting input fails closed and every risk-model input takes its conservative default. There is never a fallback to observation-age staleness.
- A risk-model, context, forward_sim or history input can never HALT a recommended book (T-ROLE-01, T-SCOPE-01).

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-STALE-01 | Schedule-aware staleness on decisions 2016-01-04 → 2026-09-25, US and KRX closes | (a) Without the source-exception list, DTWEXBGS and DEXKOUS are stale on ≤ 1% of decisions (0.42–0.89% expected; DLA-S1), and every hit's missed observation date (`d_next`) is in the source-skipped list. The v1.2 rule gives 100% (98.6% at the KRX close). (b) With the list loaded, those dates raise no flag. (c) DGS10 under strict H.15: ≤ 1% (0.33% expected). VIXCLS: 0%. (d) Deleting one H.10 release from the fixture flags the next decision after the grace. (e) Negative control: reading `expected_available_utc` as the availability of `last_obs` itself flags DEXKOUS stale on about 80% of decisions (79.8% of KRX weekday closes 2016–26 on a synthetic Fed calendar); the implementation must not. |
| T-ROLE-01 | Failure actions by role | A stale acting input → `fail_closed = true` and an alert, with the state unchanged: miss 1 → fail closed; miss 2 → its books HALTED (OPS); a fresh decision resets the counter; two acting inputs bound to one book failing on alternate decisions HALT it at the 2nd decision; an unreadable publication calendar fails every acting input closed and sets every risk-model default. A stale risk-model input → `hedge_credit_off = TRUE`, an alert, operator escalation after 2 missed releases, and never HALTED, however long it stays stale. A stale context input → the label only. |
| T-H15-01 (v2) | H.15 on the Fed business-day calendar | DGS10 dated Fri 2015-01-02 is usable at the KRX close of Tue 2015-01-06, not Mon 2015-01-05. DGS10 dated 2026-10-09 is usable at the US close of 2026-10-14 (Columbus Day). |
| T-H10-02 (v2) | H.10 holiday Monday | DEXKOUS for the week of 2026-10-05 is usable from the KRX close of Wed 2026-10-14, not before |
| T-XMKT-01 | Same-instant closes | For every non-CSAT date D ≥ 2024-11-05 on which both KRX and TSE trade, the TSE close of D is not usable at the KRX close of D. For such dates from 2016-08-01 through 2024-11-04 (TSE close 06:00Z; KRX bound 06:30:30Z), it is usable. For such non-CSAT dates before 2016-08-01 (both closes at 06:00Z; KRX bound 06:00:30Z < 06:00Z + 60 s), it is not. CSAT days apply the same rule at the CSAT bound: at 07:30:30Z on 2025-11-13 the same-date TSE close (06:30Z) and Shanghai close (07:00Z) are usable; on a pre-2016 CSAT day the result follows the signed CSAT bound (with the configured 16:00 KST close, the TSE close is usable and the Shanghai close is not). The same-date TAIEX close (13:30 TST = 05:30Z) is usable at every weekday KRX close (Saturday sessions follow their signed close times); a same-date HKEX close (16:00 HKT = 08:00Z or later) never is. |
| T-HEDGE-01 | Conservative default | A stale DTWEXBGS alone (context) changes no hedge flag. With the live USD proxy and DTWEXBGS both stale, `hedge_credit_off = TRUE`, no acting component of the KR or US books fails closed (`fail_closed` false; asserted on the built `macro_state` from M6, §9.0b), and `vt` is unchanged |
| T-ROLE-02 | Bindings and contracts | The Dec-1997 Korean call rate passes its contract (`KR_CALL_CD` range [−1, 40]%), and a missing cash day refuses the card (never cash = 0). A missing cash day is a day of the cash series' own observation calendar, declared in the registry (the ECOS business-day calendar for `BOK_CALL_RATE`), without a value (R-22 rule 3); a KRX session on a day that calendar is closed, such as a Saturday before 1998-12-12 if ECOS has no print for it, accrues the latest prior rate. An acting or forward_sim binding without a `books` key is refused at registration; an explicit empty list (`books: []`, e.g. `US_SLEEVE_OFFICIAL_CLOSE` while D5 = none) is valid and binds no book. The S&P close failing on 3 decisions fails the R-28 and R-29 FORWARD-SIM books closed, sets `hedge_credit_off` through its corr63 binding, and HALTs no recommended book. |

**Source items.** QF2-A3; QF2-M3; QF4-M7; QF4-A11; QF2-A4; QF2-A6; QF2-A10; QF2-A21.

**Evidence.**
- Resolution 7.
- DLA §6 (`results/QX_DLA_staleness.csv`):
  - DTWEXBGS is stale at 100.0% / 98.6% of US / KRX decisions under "1 trading day", against 0.89% / 0.80% schedule-aware;
  - DEXKOUS 0.52% / 0.42%;
  - DGS10 (strict) 99.52% against 0.33%;
  - VIXCLS 0%.
- QF2-M5 counts: 599 of 2,938 DGS10 observations leak under the v1.2 KRX mapping; 75 holiday Mondays; 85 Fed-holiday decisions.
- Why the conservative default is right: bonds lost in 65% of US equity-down months after a positive trailing stock–bond correlation, against 27% otherwise (EX1).

### R-20 Effective-dated market calendars and regime tags (KRX, NYSE, Fed, SIFMA) — BUILD NOW · INVARIANT · P0 · M1

**Purpose.** *NEW in v2.0.* Decision times and data availability are derived from versioned calendars, not from constants. Long samples carry their market-structure regime as dated tags.
- The KRX clock is not a constant. The close moved from 15:00 to 15:30 on 2016-08-01. CSAT days close at 16:30 from 2016-08-01 (the earlier CSAT close comes from the KRX notice). The random end has been unconditional and ≤ 30 s since 2015-06-15.
- 1997–2002 KOSPI was a different market: price limits of ±8 / 12 / 15%, Saturday sessions, a pegged won and no ETF.

**Package / module and functions.**
- `core/calendars`, with versioned data under `core/calendars/data/` (**proposed**). Every change carries the official source, the retrieval date and an owner sign-off.
  - `decision_time_utc(market, session_date) -> datetime`: the scheduled official close (the API is unchanged from v1.2 and T-CLOSE-01 still holds);
  - `close_print_bound_utc(market, session_date) -> datetime`: the scheduled close plus the random-end bound;
  - `is_session(market, date)`, `session(market, date) -> Session` (open, close, closing call, special flags);
  - `fed_business_day(date)`, `sifma_status(date)`, `nyse_holiday(date)`: three separate holiday sets;
  - `publication_instant(series, obs_date)` and `next_expected_obs(series, obs_date)`, used by R-19;
  - `regime_tags(market, date) -> dict`.
- `core/markets`: session metadata per venue.
- `config.py`: the decision constants become calendar lookups.

**Inputs (PIT fields).**
- Calendar data files, each row with `effective_from`, `effective_to`, `source_url` (or the notice reference), `retrieved_at_utc` and `signed_off_by`.
- Official sources: KRX notices; the Fed holiday schedule; SIFMA recommendations; the NYSE holiday and early-close list; the BoK, ECOS, BLS and BEA calendars; FSC / KCMI notices for short-sale bans; tax notices.
- `exchange_calendars` XKRX serves as a cross-check only, never as the source.

**Rule / algorithm.**
1. **KRX session rules (effective-dated):**

   | Item | Rule |
   |---|---|
   | Regular close | 15:00 KST (06:00Z) through 2016-07-31; 15:30 KST (06:30Z) from 2016-08-01 |
   | Closing call | 14:50–15:00 KST before 2016-08-01; 15:20–15:30 KST from 2016-08-01 |
   | Random end | Conditional until 2015-06-14. **Unconditional, ≤ 30 s, from 2015-06-15**, so the close prints within 30 s of the scheduled close (15:00:00–15:00:30 KST through 2016-07-29; 15:30:00–15:30:30 KST from 2016-08-01). Before 2015-06-15 the bound is the scheduled close + the 30 s print tolerance, plus any extension the KRX notice records for a session whose conditional random end was triggered |
   | CSAT day | Session 10:00–16:30 KST from 2016-08-01, close 07:30Z (e.g. 2025-11-13); before 2016-08-01 the CSAT window comes from the KRX notice (calendar data; UNVERIFIED until signed) |
   | First trading day of the year | 10:00 KST open |
   | Saturday sessions | Present on non-holiday Saturdays before 1998-12-12, with their own (half-day) close time from the KRX notice (`saturday_session_close_kst`), so `decision_time_utc` and `close_print_bound_utc` are defined for them. The Yahoo ^KS11 file omits them. |
   | Lunch break | Until May-2000; the exact date comes from the official notice |
   | Excluded from signals | NXT after-market 15:40–20:00; KRX after-market 16:00–20:00 from 2026-09-14 |
   | KOSPI200 futures | The expiring contract stops at 15:20 KST on its last trading day (R-26 roll rule) |

2. **Other markets:**
   - NYSE: close 16:00 ET with DST (IANA America/New_York), and early closes at 13:00 ET (17:00Z in EDT, e.g. 2025-07-03; 18:00Z in EST, e.g. 2026-11-27); close-print bound = scheduled close + `close_print_bound_s` (30 s);
   - TSE: close 15:00 JST (06:00Z) through 2024-11-04, and 15:30 JST (06:30Z) from 2024-11-05.
   - SSE (CN), HKEX (HK) and TWSE (TW), read only across markets: close times from the exchange notices, effective-dated and owner-signed with the calendars at M1 (SSE 15:00 CST, HKEX 16:00 HKT and TWSE 13:30 TST today). For JP, CN, HK and TW the close-print bound = scheduled close + the market's `close_print_bound_s` (0 s, default, judgment: the 60 s cross-market buffer of R-19 rule 6 covers dissemination).
   - The Fed, SIFMA and NYSE holiday sets are separate. On Columbus and Veterans Day the NYSE is open and the Fed is closed (R-19's H.15 / H.10 rules).
3. **Close stamps.** An official close of session d is stored with:
   - `obs_utc = decision_time_utc(m, d)` (the scheduled close);
   - `available_at_utc ≤ close_print_bound_utc(m, d)`.

   For KRX from 2015-06-15, that bound is the scheduled close + 30 s: 06:00:30Z through 2016-07-29 (including the 142 golden-sample sessions of 2016), 06:30:30Z from 2016-08-01, and the CSAT close + 30 s on CSAT days (07:30:30Z from 2016-08-01). Before 2015-06-15 there was no unconditional random end: the bound is the scheduled close + the declared 30 s print tolerance, extended for a session whose conditional random end was triggered by the extension the KRX notice records (calendar data). NYSE: the scheduled close + 30 s, DST-aware.

   `available_at_utc` is the exchange print time when it is logged, else the bound (`calendar_bound`); a receipt time is only ever `retrieved_at_utc`. A close whose logged print time exceeds its bound fails closed with a calendar-review alert and is never re-stamped.

   The lag audit of a decision at the close of d uses `close_print_bound_utc(m, d)` as the decision instant. A KRX record whose `available_at_utc` is 06:31Z is still rejected for that day's decision (T-CLOSE-01).
4. **Regime tags.** `regime_tags('KR', date)` returns the effective value of each tag. Dates given to the month come from the review sources. The exact day is taken from the official notice when the calendar file is signed off.

   | Tag | Effective-dated values |
   |---|---|
   | `price_limit` | ±6% from Apr-1995; ±8% from Nov-1996; ±12% from Mar-1998; ±15% from Dec-1998; ±30% from 2015-06-15 |
   | `saturday_session` | true before 1998-12-12 |
   | `close_time_kst`, `closing_call`, `random_end`, `lunch_break` | as rule 1 |
   | `fx_regime` | `peg_1997` for 1997-09-22 → 1997-10-17 (won at 912.3–914.9 on the ECOS 15:30 close; the band broke in late Oct-1997); otherwise the regime recorded from BoK sources |
   | `etf_available` | true from KODEX 200's listing in Oct-2002 (the exact date is in the KRX listing record) |
   | `short_sale_ban` | 2008-10 → 2009; 2011-08 → 2011; 2020-03 → 2021-05; 2023-11 → 2025-03 (KCMI; exact dates from the FSC notices) |
   | `sell_tax_pct` | Anchors 0.30 (2019), 0.15 (2025), 0.20 (2026; 0.05% transaction tax + 0.15% rural special tax). ETFs are exempt. The full step schedule comes from the official notices. |
   | `tick_regime` | stocks reformed 2023-01-25; ETFs ₩1 tick below ₩2,000 from 2023-12-11 |
   | `letf_rules` | single-stock leveraged-ETF rules of 2026-05-27 and 2026-07-16 |
   | `usdkrw_onshore_hours` | close 15:00 KST → 15:30 KST (2016-08-01) → 02:00 KST next day (Jul-2024) → 24 hours (from 2026-07-06) |

5. **Uses of the tags.**
   - Every long-sample card prints its checks per regime and declares one primary out-of-sample line (R-22).
   - R-18 logs a market-structure break when a tag changes; any card whose evidence straddles the break prints the split.
   - Futures-line books print a ban-period basis line (R-26).
6. **Change control.** A calendar change is a new version of the data file, with the owner's sign-off and a new test case. An unsigned change is refused.

**Config keys** (merge into §7):
```yaml
calendars:                                           # R-20; data files in core/calendars/data/ (owner-signed)
  KR:
    close_kst: [{to: "2016-07-31", time: "15:00"}, {from: "2016-08-01", time: "15:30"}]
    closing_call_kst: [{to: "2016-07-31", window: ["14:50", "15:00"]}, {from: "2016-08-01", window: ["15:20", "15:30"]}]
    random_end: [{to: "2015-06-14", kind: conditional, print_tolerance_s: 30, triggered_extensions: from_krx_notice},
                 {from: "2015-06-15", kind: unconditional, max_s: 30}]   # bound = scheduled close + max_s, or + print_tolerance_s before 2015-06-15
    csat_session_kst: [{to: "2016-07-31", window: ["10:00", "16:00"]}, {from: "2016-08-01", window: ["10:00", "16:30"]}]   # pre-2016 window UNVERIFIED: confirm from the KRX notice at the M1 sign-off
    csat_closing_call_kst: [{to: "2016-07-31", window: from_krx_notice}, {from: "2016-08-01", window: ["16:20", "16:30"]}]   # R-27 CSAT snapshot; confirm at the M1 sign-off
    first_trading_day_open_kst: "10:00"
    saturday_sessions_before: "1998-12-12"
    saturday_session_close_kst: from_krx_notice       # owner-signed at M1; decision_time_utc and the bound exist for Saturdays
    excluded_sessions: [{venue: NXT, window_kst: ["15:40", "20:00"]}, {venue: KRX_after_market, from: "2026-09-14", window_kst: ["16:00", "20:00"]}]
  US: {close_et: "16:00", early_close_et: "13:00", holiday_set: NYSE, tz: America/New_York, close_print_bound_s: 30}   # M1 confirms the bound from logged print times
  JP: {close_jst: [{to: "2024-11-04", time: "15:00"}, {from: "2024-11-05", time: "15:30"}], close_print_bound_s: 0}   # default, judgment: the 60 s buffer covers dissemination
  CN: {close_cst: from_sse_notices, close_print_bound_s: 0}          # SSE 15:00 CST today; effective-dated, owner-signed at M1 (§9.5)
  HK: {close_hkt: from_hkex_notices, close_print_bound_s: 0}         # HKEX 16:00 HKT today (closing auction from the notices)
  TW: {close_tst: from_twse_notices, close_print_bound_s: 0}         # TWSE 13:30 TST today (earlier hours from the notices)
  holiday_sets: [KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS]   # kept separate (QF2-A11); every registered input's obs_calendar
  regime_tags_file: core/calendars/data/kr_regime_tags.yaml
  change_control: {owner_sign_off: required, test_per_change: required}
  coverage: {min_sessions_ahead: 60, warn_at_sessions_left: 60, page_at_sessions_left: 20, outside_coverage: OPS_HALT}   # T-CAL-02
```

**Outputs and schema fields.**
- `macro_state.decision_utc` (the close-print bound) and `effective_session`.
- `macro_state.extras.regime_tags` on every KR record.
- `model_card.macro.regime_line_results[]` (R-22, R-32).
- `event_calendar` entries' `kr_open_gap_session` and `gap_sessions`, multi-session aware (R-10); `macro_state.flags.kr_open_gap_event` and `gap_sessions` (n_US ≥ 0).

**Fail-closed behaviour.**
- `decision_time_utc` on a non-session raises `NotASession`; it never rolls silently to the next day.
- A missing or unsigned calendar version makes every acting input of that market fail closed (R-19).
- A tag requested for a date the file does not cover raises. A card whose span is not fully covered by the regime-tag file is refused.
- **Coverage horizon.** Every calendar, regime-tag and publication-schedule file covers ≥ 60 sessions of its market beyond the decision date; a `warn` alert fires at 60 sessions left and a `page` at 20; a decision date outside coverage is an OPS HALT with `reason = calendar_coverage`, never a silent `NotASession` (T-CAL-02).

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-CLOSE-02 | Effective-dated KRX and NYSE clocks | `decision_time_utc('KR', 2016-07-29)` = 06:00Z. `('KR', 2016-08-01)` = 06:30Z. `close_print_bound_utc('KR', 2026-10-02)` = 06:30:30Z. `close_print_bound_utc('KR', 2016-07-29)` = 06:00:30Z. `close_print_bound_utc('KR', 2025-11-13)` = 07:30:30Z (CSAT). `decision_time_utc('KR', 2025-11-13)` = 07:30Z (CSAT). A pre-2016 CSAT date and a pre-1998-12-12 Saturday return the signed calendar's close and bound. `decision_time_utc('KR', 2026-10-05)` raises `NotASession`. `decision_time_utc('US', 2026-11-27)` = 18:00Z (early close, EST); `('US', 2025-07-03)` = 17:00Z (early close, EDT). `close_print_bound_utc('US', 2026-10-01)` = 20:00:30Z. |
| T-SAT-01 | Saturday sessions | `is_session('KR', d)` is true for every non-holiday Saturday d < 1998-12-12 and false for every Saturday from 1998-12-12 on. A KOSPI fixture that lacks those Saturdays fails the completeness check: every `is_session` date has exactly one close row (the Monday / Tue–Fri variance ratio 2.30 in 1997–98 is printed; EX2). |
| T-REGIME-01 | Regime tags for any date | `regime_tags('KR', 1997-06-02).price_limit` = 0.08; `(1998-06-01)` = 0.12; `(1999-06-01)` = 0.15; `(2015-06-15)` = 0.30. `fx_regime` on 1997-10-01 = `peg_1997`. `etf_available` on 2002-01-02 = false. `short_sale_ban` on 2024-06-03 = true. `sell_tax_pct` on 2026-10-02 = 0.20. Every date from 1995-01-01 to 2026-12-31 returns a full tag set, equal to a committed expected-values file built from the official notices (including `price_limit` before Apr-1995). |
| T-AVAIL-01 | Golden availability fixtures built from official calendars | Exact match: DGS10 dated Fri 2015-01-02 → KRX close of Tue 2015-01-06; DEXKOUS for the week of 2026-10-05 → KRX close of Wed 2026-10-14; DGS10 dated 2026-10-09 → US close of 2026-10-14; the CSAT close of 2025-11-13 at 07:30Z. An injected registry error (e.g. H.15 posted at D, not D+1) makes the test fail (R-34). |
| T-CAL-01 | Change control | A calendar file without `signed_off_by` is refused at load, and every KR acting input fails closed |
| T-CAL-02 | Coverage horizon | Every calendar, regime-tag and publication-schedule file covers at least 60 sessions of its market beyond the decision date. At 60 sessions left a `warn` alert fires; at 20 it pages. A decision date outside coverage fails closed as an OPS HALT with `reason = calendar_coverage`, never a silent `NotASession`. The 2027 KRX, NYSE, Fed and SIFMA files are signed off before 2026-11-01 (default, judgment). |

**Source items.** QF2-A12; QF2-M5; X-EX2-N1; X-PX2-N6; QF1-A4; QF2-A11.

**Evidence.**
- QF2-A12: the 2016-08-01 close change, under which 142 golden-sample sessions closed at 06:00Z, and the CSAT close at 07:30Z.
- QF2-M5: 599 / 2,938 DGS10 leaks; 85 Fed-holiday decisions; 75 holiday Mondays; 10 CSAT days a decade; 86 KRX-only and 156 NYSE-only sessions in 2016–26.
- EX2 §1(2) and X-EX2-N1:
  - the unconditional random end since 2015-06-15 (Eom et al.; the Shinhan notice);
  - the price-limit and Saturday-session regimes;
  - 1997–2002 alone is a REJECT for VT20 (ΔSR −0.204), while the ETF era passes.
- X-PX2-N6: short-sale bans, the sell tax and tick reforms as structure breaks.
- QF1-A4: the KRX close is bounded at the scheduled close + 30 s (06:30:30Z from 2016-08-01).

### R-21 CARD-P gate v2: PC-1′ tail legs, PC-2 with CI, binding PC-3, do-no-harm cap, gate-acceptance test — BUILD NOW · GOVERNANCE · P0 · M7 (frozen before the first card run)

**Purpose.** *NEW in v2.0.* PC-1 used the single-path ΔMDD, and that statistic cannot gate:
- its bootstrap SD is 7.4–7.8 pp at every sample length from 10 to 100 years;
- the same Korea card shows ΔMDD of +12.7, +3.8 or +10.6 pp depending only on the start date;
- a zero-cost vol target is REJECTed 55–70% of the time at 11–36 years.

R-21 replaces it with tail legs whose sampling error shrinks with the sample. It keeps PC-3 binding. It caps a drawdown-line failure at INSUFFICIENT DATA. It proves the size and power of the whole package once, on placebos and negative controls, **before any card runs** (Resolution 4). Chair red lines P2, E2 and Q1 (no rule adopted after seeing the card it decides) and Q2 (no REJECT on single-path drawdown) bind it.

**Package / module and functions** (`core/quant/backtest`, **proposed**; the macro additions to the existing gate):
- `cardp_evaluate(header, books) -> CardPResult`: runs PC-1′…PC-7, applies the caps and the verdict order (§8.7);
- `es_h(x, h, level=0.95)` and `pc1_prime(x_rule, x_S, horizons=(21, 126))`;
- `tail_exposure_ratio(m, x_off, q=0.05, horizon=1)`, with a bootstrap CI;
- `pc3_noninferiority(x_rule, x_S, delta=0.10)`, using R-24's studentized bootstrap;
- `placebo_panel(header, n=20)` and `gjr_null_percentile(header, n_paths=1000)`;
- `gate_acceptance_test(families, controls) -> AcceptanceReport`;
- `core/rules`: the gate-package block, with its version and md5 (§8.1.3).

**Inputs (PIT fields).** The card harness reads frozen fixtures or the PIT store only:
- closes with `value_status = official_close` and `session_date` (R-01);
- cash rates with their `available_at_utc` (R-22);
- the cost model (R-26);
- the episode list (R-22); N_eff and the selection factor (R-23); the power line (R-24).

Books, all on R-22's excess-return convention:
- the rule book x_on;
- the overlay-off book x_off;
- the multiplier series m;
- the comparator **S**: x_S = m̄ · x_off, i.e. the overlay-off book scaled by the overlay's average exposure (constant, same days, uncosted). For a card judged incrementally (the trend card, the step-down card, the stack card), "overlay-off" means the book without the factor under test.
- **Card books exclude the R-07 hard stop and caps** (R-22 rule 6, frozen with the package; C-2). Those are book-level invariants, judged on the composed recommended book by the §8.7 stack card once one exists; until then no card gates them (G-LAD-04 prints them). Every card prints a `with_risk_layer` line for its on and S books, never gated.

**Rule / algorithm.**
1. **Expected shortfall at a horizon.**
   - R_h(t) = Π_{j=t−h+1..t}(1 + x_j) − 1 are the overlapping h-session returns.
   - ES95_h(x) = −mean of the lowest 5% of R_h. It is a positive loss.
   - **ΔES_h = ES95_h(S) − ES95_h(rule). A positive value means protection.**
   - On a monthly card, h = 21 and 126 sessions become 1 and 6 months (default, judgment).
2. **PC-1′ (gates).**
   - Compute ΔES_21 and ΔES_126 net of 1× cost.
   - p_h = share of B = 2,000 stationary-bootstrap resamples (Politis–Romano, mean block 250 sessions, Resolution 4's floor used exactly: another value is a new package version; seed 11) with ΔES*_h ≤ 0, i.e. the percentile p of the uncentred bootstrap distribution. z_h = ΔES_h ⁄ SD*(ΔES_h) is printed beside it and never decides. A value of 0 is printed "< 1/B".
   - Each leg passes if its point estimate is > 0 and p_h × f ≤ 0.10, where f is the selection factor that R-23's `step3()` computes from the family ledger (1, or N_eff; never declared by the card). A point ≤ 0 at 1× is a REJECT; both points > 0 with a p_h × f above 0.10 is INSUFFICIENT DATA (inconclusive; Resolution 4).
   - The same legs at 2× cost feed the REVISE path.
3. **PC-2 (gates).** Tail-exposure ratio TR = mean(m on the worst 5% of overlay-off days) ÷ mean(m on all days). It passes when **TR ≤ 0.90** (point, at 1×). Its 90% bootstrap CI is printed.
   - The daily ratio is always printed.
   - The **horizon-matched** ratio (worst 5% of h-session windows at the rule's decision horizon; h = 21 for monthly rules) replaces the daily ratio for **every** CARD-P only if the placebo test of rule 9 passes. Flips are disclosed. KOSPI trend stays context whatever it shows.
4. **PC-3 (gates, unchanged in substance).** ΔSR = SR(x_on) − SR(x_S), with non-inferiority margin δ = 0.10.
   - p_ni = max(p_10, p_PW): one-sided p of {ΔSR* ≤ −δ} from R-24's studentized circular-block bootstrap, with 10-session blocks and with max(21, PW(ψ))-session blocks. Each p is multiplied by f.
   - A point ΔSR < −δ at 1× is a **REJECT**. At 2× it is a REVISE.
5. **PC-4 … PC-7.**
   - **PC-4:** on R-22's objective episodes, ≥ 3 episodes with a positive benefit vs S, and no episode above 50% of the summed positive benefit.
   - **PC-5:** ≥ 60% of calendar years positive for the overlaid book. The share of years lagging S is printed.
   - **PC-6:** ≥ 50% of the neighbours keep ≥ half of the centre's ΔES_21 and ΔES_126, and a PC-3 point ≥ −δ. The neighbours are the 8 Moore neighbours of a two-axis grid, or the 2 axis neighbours of a one-axis rule. The axes and their steps are frozen per rule type in `gate.card_p_v2.pc6_axes` (default, judgment): a vol target uses window × {0.5, 1, 2} and target × {0.75, 1, 1.25} (R-06 KR: {10, 20, 40} sessions × {0.15, 0.20, 0.25}, the DL-A grid); a threshold rule uses its threshold × {0.75, 1, 1.25} and its lookback or dwell × {0.5, 1, 2}; a monthly trend rule uses its lookback {8, 10, 12} months (QF5's SMA8m / SMA12m neighbours). A card never declares its own axes or steps.
   - **PC-7 (sufficiency):** discrete rules need ≥ 30 onsets de-clustered at their own lookback; continuous rules need ≥ 5 objective episodes in the sample. Both need ≥ 756 + 126 sessions.
6. **Caps.** A cap lowers a verdict to the level in its row (INSUFFICIENT DATA, or REVISE for the estimator cap), in the order REJECT < INSUFFICIENT DATA < REVISE < PASS (§8.7). It never raises a verdict and never turns anything into a REJECT.
   - **Do-no-harm:** if ΔMDD < 0 **and** ΔCDaR95 < 0 at 1× (the rule is deeper and longer under water than S), the card is capped at INSUFFICIENT DATA. A drawdown line alone never REJECTs.
   - **Timing-fragile (R-34):** capped at INSUFFICIENT DATA (Tier B treatment).
   - **Estimator calibration failure (R-30 rule 8):** SMA20 must keep passing B5; a challenger estimator must pass R-30's Stage 1. A failure caps the card at REVISE, with the permitted fix "lengthen the holding period" (a counted revision).
7. **UNDERPOWERED (R-24).** It may turn only a failed PC-3 p-value into INSUFFICIENT DATA (underpowered). It never waives PC-1′, PC-2 or the PC-3 point REJECT.
8. **Verdict order.** INSUFFICIENT (sufficiency) → REJECT → INSUFFICIENT (inconclusive) → REVISE → caps → PASS. §8.7 writes it out in full. It is coded once, in `cardp_evaluate`.
9. **Gate-acceptance test.** It runs once, before any card, on placebos and negative controls only; no real card's verdict is computed in it. Its results are md5-frozen.
   - **(a) Size.** Placebo = the card's multiplier series circularly shifted by τ sessions against its returns (timing-free).
     - Per family: 300 placebos, τ uniform on [252, T − 252] (seed 11). At most 10% may pass PC-1′.
     - Per card: 20 placebos at τ_k = round(252 + k·(T − 504) ⁄ 19), k = 0…19, i.e. evenly spaced on [252, T − 252]. At most 2 may pass PC-1′.
     - A placebo **passes PC-1′** when both legs pass at 1× under the card's own rule (points > 0 and p_h × f ≤ 0.10). The per-family and per-card counts use this one definition.
     - **Population.** The families and cards are those of the CARD-P headers drafted for §8.1.3 (R-06 KR, R-28, R-29, R-31), each on its declared book and span; the R-06 family panel uses the R-06 KR ETF-line series. In a family with several cards, the per-family panel shifts each card's own multiplier series (300 per card) and pools them. Each panel is built from the card's drafted header, whose md5 the acceptance report cites (§8.1.3).
     - **Failure path.** A per-family or per-card count above its limit fails the acceptance test: the package is not frozen and no card runs. Whether a per-card excess should instead cap only that card at INSUFFICIENT DATA is council question Q5 (§8.10); until it is answered, this conservative reading stands.
     - **Bounded redesign (R2-C3).** A failed package may be redesigned once per package version. Failures count across all 2.x versions in the attempts log, and a version bump never resets the count. The re-attempt may change only items of §8.1.3's frozen-items table; each change is recorded in the attempts log with the manifest diff and a rationale that cites the per-family panels and the negative controls only, never a named card's panel or its indicative numbers. It uses fresh placebo and negative-control seeds, fixed and logged before the run, and re-runs every panel and control. A per-card excess is resolved only by the answer to council question Q5, never by editing the τ grid, the placebo construction, the pass definition or the PC-1′ definition. After a second failure, in any 2.x version, no card can be evaluated under v2: every card keeps its current indicative status (NOT_RUN in every book), and the owner is notified (a governance event and a page).
   - **(b) Power against known-bad rules.** Each of these must come out REJECT or INSUFFICIENT DATA under the package:
     - the US VT 5-day and 10-day rules at 50 bp (PX1);
     - EX1's post-shock-day and post-shock-week 0.5× rules;
     - a stale VT with σ̂ lagged 252 sessions (EX1).
   - **(c) Horizon-matched PC-2.** Run on every pre-registered CARD-P plus 20 placebos each. Adopt it for all cards if the placebo false-pass rate is ≤ 10%.
   - **(d) CDaR guard.** Only if a control in (b) would pass, add a null-calibrated CDaR95 guard before any card runs. Its calibration is the one open sub-point of Resolution 4: the Professors' bootstrap test at one-sided 5%, the Executives' placebo-10th-percentile margin, or QF's blind margin. The choice is owner decision D6 (Quick start). Its default, the lowest-placebo-false-pass rule (of the three candidates, the one with the lowest per-family placebo false-pass rate among those that bring every negative control to REJECT or INSUFFICIENT DATA; ties go to the Professors' test; placebo results only), is written into the package before any control or card runs: `owner_decisions.D6` is listed in the `definitions_md5` manifest and the attempts log. An owner ruling naming one candidate is accepted only before the first acceptance attempt; any later change is a new package version and a counted trial in every family ledger (R2-C2). If a control passes, the harness applies the recorded rule, prints the three candidates' placebo results (never a real card's numbers) and re-runs the test; if no candidate brings every control to REJECT or INSUFFICIENT DATA, the attempt fails (9(a)). The fixed −5 pp margin is withdrawn.
   - **(e) Attempts log.** Every acceptance-test attempt, passing or not, is appended to `gate/acceptance_runs.jsonl` (append-only and hash-chained: each row carries the previous row's md5), the package-level ledger: each attempt counts as a trial of the package, and every attempt and its outcome is printed beside any verdict produced later (R2-C3). The frozen report lists every attempt. Later `tests/run_all.py` runs only re-verify `acceptance_report_md5` and `definitions_md5`; they never re-run the test (§9 test tiers).
10. **Printed, never gated:**
    - ΔMDD, ΔCDaR95 and daily ΔES99, each with a bootstrap band;
    - the **GJR-null percentile**: a GJR-GARCH(1,1)-t with constant mean is fitted on the card's market over the declared span; 1,000 paths are simulated (seed 11; default, judgment); the card's rule runs on each path; the observed ΔMDD and ΔES_21 are reported as percentiles of that null;
    - the 20-shift placebo panel;
    - time under water, re-entry lag and the post-trough window (R-22);
    - rolling 5-year block comparisons against S (QF4-A22);
    - DSR vs 0 and PSR vs S (R-23).

**Config keys** (merge into §7 under `gate`; frozen in `gate.package`):
```yaml
gate:
  card_p_v2:                                         # R-21
    comparator: S_same_average_exposure              # m_bar x overlay-off; constant; same days; uncosted
    pc1_prime: {horizons_sessions: [21, 126], es_level: 0.95, overlapping: true, gate_cost: 1x,
                point_must_exceed: 0.0, p_max: 0.10, p_form: uncentred_bootstrap_percentile, z_printed: true, bootstrap: stationary, mean_block_sessions: 250,
                resamples: 2000, seed: 11, two_x: revise_path, monthly_cards_horizons_months: [1, 6]}
    pc2: {tail_quantile: 0.05, ratio_max: 0.90, default_horizon: daily, ci: printed,
          horizon_matched: {adopt_if_placebo_false_pass_max: 0.10, placebos_per_card: 20, decided_in: acceptance_test}}
    pc3: {delta: 0.10, p_max: 0.10, p_ni: "max(p_block10, p_block_max21_PWpsi)", point_below_minus_delta: {at_1x: REJECT, at_2x: REVISE}}
    pc4: {episodes: objective_market_own, min_positive: 3, max_share: 0.50}
    pc5: {years_positive_min: 0.60}
    pc6: {neighbourhood: moore_8_or_2_axis_neighbours, keep_share_min: 0.50}
    pc6_axes:                                        # frozen per rule type; a card never declares axes or steps (default, judgment)
      vol_target: {window_mult: [0.5, 1, 2], target_mult: [0.75, 1, 1.25]}           # R-06 KR: {10, 20, 40} x {0.15, 0.20, 0.25}
      threshold_rule: {threshold_mult: [0.75, 1, 1.25], lookback_or_dwell_mult: [0.5, 1, 2]}
      monthly_trend_rule: {lookback_months: [8, 10, 12]}                              # one axis, 2 neighbours (QF5)
    pc7: {discrete_min_onsets: 30, decluster_gap: own_lookback, continuous_min_objective_episodes: 5, min_sessions: 882}
    caps: {do_no_harm: INSUFFICIENT_DATA, timing_fragile: INSUFFICIENT_DATA, estimator_calibration_fail: REVISE}   # SMA20: B5; challenger: R-30 Stage 1
    underpowered: {applies_if_mde80_gt: 0.10, converts: [pc3_p_value], never_waives: [pc1_prime, pc2, pc3_point]}
    gjr_null: {paths: 1000, seed: 11, mean: constant}                 # printed only
  acceptance_test:
    placebo: {construction: circular_shift_of_multiplier, per_family: 300, per_family_false_pass_max: 0.10,
              tau_min_sessions: 252, per_card: 20, per_card_passes_max: 2, seed: 11,
              per_card_tau: "round(252 + k*(T - 504)/19), k = 0..19", pass: pc1_prime_both_legs_1x_with_f,
              population: drafted_card_p_headers, family_pooling: own_series_300_per_card, on_excess: acceptance_fails}   # Q5 open (§8.10)
    negative_controls: [US_VT_5d_50bp, US_VT_10d_50bp, post_shock_day_0p5, post_shock_week_0p5, VT_sigma_lag_252]
    controls_allowed_verdicts: [REJECT, INSUFFICIENT_DATA]
    cdar_guard: {added_only_if_a_control_passes: true, calibration: lowest_placebo_false_pass_rule, fixed_margin_minus_5pp: withdrawn}   # calibration: canonical key of D6, frozen with the package (R2-C2)
    attempts_log: {path: gate/acceptance_runs.jsonl, append_only: true, hash_chain: prev_row_md5, listed_in_report: true,
                   counts_as: package_trial, printed_beside_every_verdict: true}   # R2-C3
    redesign: {max_per_package_version: 1, changes_limited_to: frozen_items_table, rationale_cites: [family_panels, negative_controls],
               fresh_seeds_fixed_before_run: true, per_card_excess: council_q5_only, failure_count: across_all_2x_versions_never_reset,
               after_second_failure: no_card_evaluated_under_v2_owner_notified}   # R2-C3; T-GATE-04
```

**Outputs and schema fields** (§6.5, R-32).
- `model_card.macro.tests.PC1p = {legs: [{h, dES, z, p, p_adj, pass}], two_x: [...]}`.
- `tests.PC2 = {ratio_daily, ratio_horizon, ci90, horizon_used, pass}` and `tests.PC3 = {dSR, p10, pPW, block_PW, p_ni, p_adj, point_2x, pass}`.
- `tests.PC4..PC7`.
- `caps_applied[]`, `verdict`, `verdict_reason`.
- `printed = {dMDD, dCDaR95, dES99, bands, placebo_panel: {n, passes}, tuw, reentry_lag, post_trough, rolling_5y, with_risk_layer}` and the top-level `gjr_null_pct` (§6.5); `verdict_at_f1` and `verdict_at_f_neff` (R-23).
- The gate package's `acceptance_report.json` and its md5.

**Fail-closed behaviour.**
- No CARD-P can be evaluated before the acceptance test has passed and the package is frozen; `docs/macro_overlay_study.py` refuses to run.
- A card whose header cites a package version or md5 other than the frozen one is refused (T-CARD-01).
- If a bootstrap, the comparator or the episode list fails, no card is written. Partial verdicts are never written.
- If a negative control returns PASS or REVISE, the package is not frozen until rule 9(d) is applied and the test is re-run.
- A per-family or per-card placebo count above its limit fails the test in the same way (rule 9(a)). Every attempt stays in the attempts log.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-GATE-01 | Gate-acceptance test (md5-frozen; at most one bounded redesign, T-GATE-04) | ≤ 10% of 300 circular-shift placebos per family pass PC-1′, and ≤ 2 of 20 per card pass PC-1′ (pass definition, population and τ grid as in rule 9(a)). All five negative controls (US VT 5-day and 10-day at 50 bp; post-shock-day and post-shock-week 0.5×; stale VT with σ lag 252) return REJECT or INSUFFICIENT DATA. The report's md5 is written to `core/rules` and cited by every card header. |
| T-GATE-02 | US VT15, US shares via KIS at 50 bp, daily (fixture `U1`, 1990–2026) | The v2 verdict is **INSUFFICIENT DATA**, asserted as a class: ES21 +1.65 pp and ES126 +3.8 pp (points, ± 0.2 pp). p_ni is printed: 0.146 is R4b's percentile `gate_boot` value; R-24's studentized p is a different statistic and is not asserted against it. The 2× line shows ΔSR −0.125. The card's recorded label stays "REJECT (instrument: US shares via KIS, 50 bp, daily)" and the card is not re-run (R-06). |
| T-GATE-03 | Negative controls in detail | Each control's verdict ∈ {REJECT, INSUFFICIENT DATA}. Printed and informative, never asserted as points (they sit within Level-1 tolerance of their thresholds): the 5-day VT's PC-3 point ΔSR −0.29; the 10-day VT's ΔSR −0.106; the post-shock-week rule's ES21 z 1.278 (its p_21 decides, rule 2), ΔSR −0.093 and its drawdown lines (ΔMDD −9.1 pp, ΔCDaR −11.1 pp; the do-no-harm cap). |
| T-GATE-04 | Bounded-redesign path (R2-C3; synthetic) | On a synthetic panel that fails rule 9(a): nothing is frozen and no card runs. One redesign is accepted only if its manifest diff touches frozen-items-table items alone and its fresh placebo and control seeds were logged before the run; any other diff, or seeds logged after the run, is refused. A second failure leaves every card NOT_RUN in every book, writes a `package_redesign` governance event and pages the owner. A third attempt is refused, also after a 2.x version bump (failures count across all 2.x versions and never reset). Every attempt and its outcome is in `gate/acceptance_runs.jsonl`. |
| T-DNH-01 | Do-no-harm cap | Synthetic card passing every gate with ΔMDD < 0 and ΔCDaR95 < 0 → INSUFFICIENT DATA. With only ΔMDD < 0 → PASS. No drawdown-line value ever produces REJECT. |
| T-ORDER-01 | Verdict order and caps | A discrete rule with 26 de-clustered onsets that fails PC-2 → INSUFFICIENT DATA (sufficiency is decided first). A 54-onset rule with a PC-1′ point ≤ 0 → REJECT; the same rule with both points > 0 and a p × f > 0.10 → INSUFFICIENT DATA (inconclusive). A timing-fragile card meeting a REJECT condition stays REJECT (caps only lower). |
| T-ES-01 | Sign convention | A continuous rule identical to S, on a sample with ≥ 5 objective episodes and ≥ 882 sessions (so sufficiency passes first), gives ΔES_21 = ΔES_126 = 0 → REJECT (point not > 0). Halving exposure on the worst 5% of 21-session windows gives ΔES_21 > 0. |
| T-ES-02 | Korea long-history ES lines (fixture with the R4b raw-return flag, 1997-04 → 2026-10, ETF 3 bp) | Reproduces DLA-K10's points: ΔES99 daily +1.95 pp; ΔES95 of 21-day returns +2.9 pp; ΔCDaR95 +7.1 pp. Its z values (4.3; 2.3) come from a fixed 250-session circular bootstrap with B = 1,000 (`qf3_alt_metrics`) and are reproduced in reference mode only; R-21's stationary-bootstrap z is printed, never asserted against them (EX1's method gives z 2.16 for the 21-day leg) |

**Source items.** QF3-A5; QF3-M3; X-PX1-N2; X-PX1-N3; X-EX1-N4; QF5-A12; QF5-M5; X-PX2-N1; QF4-A22.

**Evidence.**
- Resolution 4 and the red lines P2 / E2 / Q1 / Q2.
- X-PX1-N2: ΔMDD bootstrap SD is flat at 7.4–7.8 pp (US) from 10 to 100 years, while the fixed-horizon ES SD falls from 0.052 to 0.020.
- X-PX1-N3: Spearman(ΔES_h, ΔMDD) is −0.43 at h 1 and +0.35 (US) / +0.64 (KOSPI) at h 126. The 5-day VT at 50 bp passes daily ES with ΔMDD −12.5 pp and ΔCDaR −19.5 pp.
- EX1: ΔMDD ≥ 3 pp certifies 3 of 20 timing-free KOSPI placebos; three-leg ES certifies 0 of 60; the post-shock-week rule reaches z 1.278.
- PX1: ES placebos pass at 0% (US) and ≤ 5.3% (KOSPI) of 300.
- DLB-T5b: a zero-cost VT is REJECTed 55–73% of the time in the resampling DGP.
- DLA-U5: US ΔMDD SD 7.8 pp; ΔES99 z 2.37; ΔES95 (21-day) z 1.85.
- DLA-K10 (Korea).
- PX2 (`qx_px2_01`): trend GJR-null percentile 87th.
- QF chair §0.3: 5-day ΔSR −0.292; 10-day −0.106.

### R-22 Evaluation conventions: objective market-own episodes, excess returns, declared start band, regime lines, post-trough window — BUILD NOW · GOVERNANCE · P0 · M7 (frozen before the first card run)

**Purpose.** *NEW in v2.0.* Fix, once and for every card, the conventions that moved the Korea verdict:
- the start date: ΔMDD +12.7 pp or +3.8 pp, depending only on whether the sample holds the June-1997 peak;
- the cash convention: p_ni 0.051 on raw returns, 0.078 on excess returns;
- the episode list: PC-4's maximum share is 0.493 under the v1.2 label windows and 0.174 under objective episodes.

The conventions are declared before any formal run and adopted blind, including for the cards they hurt. They count as one revision in every family ledger (Resolution 11). The forking path, that the episode rule rescues Korea's PC-4, is disclosed rather than hidden (§8.6).

**Package / module and functions** (`core/quant/backtest`, **proposed**):
- `episodes(market, closes, theta) -> list[Episode]`;
- `episode_benefits(x_rule, x_S, episodes)` and `post_trough_window(x_rule, x_S, episode, n=63)`;
- `excess_returns(weights, r, cash)`;
- `start_band(header) -> list[date]`, `midpoint_halves(header)`, `regime_lines(header)`;
- `core/rules` (registry): θ per market, the low-volatility declaration and the cash series per market.

**Inputs (PIT fields).**
- Official closes of the card's market (`value_status = official_close`, `session_date`).
- The local short rate: `BOK_CALL_RATE` (BoK ECOS; an annual rate); `US_RF` (§4.2; French `RF` is a per-period return, `DTB3` an annual rate). Role `history` (R-19): read from the card's frozen data snapshot; its `available_at_utc` is recorded, never used as an availability filter (rule 3).
- The R-20 regime tags.

**Rule / algorithm.**
1. **Objective market-own episodes.** Episodes are alternating bear / bull phases on the market's own official closes.
   ```python
   def episodes(close, theta):        # theta: 0.20 (KOSPI and the default); 0.15 for the S&P 500 and indices the frozen theta rule declares low-volatility
       state, peak, peak_d = "bull", close.iloc[0], close.index[0]
       for d, v in close.items():
           if state == "bull":
               if v > peak:
                   peak, peak_d = v, d
               elif v <= peak * (1 - theta):
                   state, trough, trough_d = "bear", v, d
           else:
               if v < trough:
                   trough, trough_d = v, d
               elif v >= trough * (1 + theta):           # bear confirmed over by a theta rally
                   emit(Episode(peak_d, trough_d, trough / peak - 1))
                   state, peak, peak_d = "bull", v, d
       if state == "bear":
           emit(Episode(peak_d, trough_d, trough / peak - 1, open=True))
   # episode window = from the first return after the peak close to the trough date
   ```
   - Dating starts at the first close of the declared history file.
   - Any market other than KOSPI and the S&P 500 has θ written in the registry before its first card run, by the frozen rule θ = 0.15 if the market's long-run median SMA20 vol is < 0.18, else 0.20 (default, judgment).
   - The benefit of episode e is B_e = Π_{t∈e}(1 + x_rule,t) − Π_{t∈e}(1 + x_S,t).
   - PC-4 uses the count of B_e > 0 and the maximum share max B_e ⁄ Σ_{B_e>0} B_e (R-21).
   - Each episode carries the regime tags of its peak date (R-20).
   - An open episode (`open=True`: a bear not yet confirmed over by a θ rally) is printed and never counts toward PC-4, PC-7 or a re-gate. A re-gate on a new objective episode runs on data ending at the episode's confirmation close plus the 63-session post-trough window, fixed by rule, never at a date the author chooses.
   - **Sep-2026 is not an episode in any market.** This is an assertion on the rule's output (T-EPIS-01), never an override inside the builder.
   - The §8.6 named windows remain a printed shock-type table, used for leave-one-crisis-out reporting.
2. **Post-trough window (printed, never gated in v2).**
   - For every objective episode, the rule-vs-S return from the trough to 63 sessions after it.
   - The three cost episodes: the 2009 rebound (2009-03-09 → 2009-06-30), the 2020 rebound (2020-03-23 → 2020-06-08; KOSPI from 2020-03-19) and H1-2026 (2026-01-02 → 2026-06-30).
   - None of them enters PC-4 (QF7-A20; chair majority).
3. **Excess returns.** Every card statistic uses excess returns:
   - x_t = w_t·(r_t − c_t) − cost_t, i.e. the book's return with its idle cash earning the local short rate, minus that rate;
   - Korea: `BOK_CALL_RATE`; US: `US_RF` (the card's `cash_convention.cash_series` names it; §4.2);
   - the daily c_t by the cash series' unit: for an annual-rate series (`BOK_CALL_RATE`; `DTB3` after its discount-basis conversion, §4.2) c_t = the latest rate dated on or before the previous session (the accrual start; a day on which the rate's own calendar is closed carries the prior rate) × (calendar days since the previous session) ⁄ 365 (default, judgment); for a per-period return series (French daily `RF`; French monthly `RF` on monthly cards) c_t = the series' own return for period t, used as published, with no day count. The cash series has role `history`: the card harness reads it point-in-time from the card's frozen data snapshot (pinned at the run's `knowledge_utc`), never through `pit_value`'s per-decision availability filter, because it is an accounting input and never a weight decision (a rate posted after the session it accrues for is not a look-ahead; French RF is posted monthly, DTB3 on the next Fed business day). A missing cash day is a day of the series' own calendar without a value;
   - zero-investment long / short series, such as French Mom, are already excess returns and get no cash term;
   - price-index returns (^KS11) omit dividends, and the card prints that convention.

   A reproduction test may set the flag `returns: raw` (cash at 0, R4b) to match a legacy golden value. A formal card never does: a raw-flag run produces harness outputs, never a card record (`cash_convention.returns` is `excess` in the schema).
4. **Start and start band.**
   - Every card starts at the first available close of its declared history, plus the estimator's warm-up (20 sessions for SMA20). The start is never chosen: each market's declared history is fixed in the registry before the freeze (`gate.evaluation.history_start`; KR: 1997-04-01, R-06), and a card cannot truncate it except through a regime line. The span end is a date fixed before any run. For the CARD-P headers drafted for §8.1.3 it is `gate.evaluation.data_cutoff[market]`, fixed now at the last official close in the frozen reference data (KR 2026-10-02, US 2026-10-01; §9.3.1), the span of the council's definitive cell, never set by the drafting date (a card whose data file ends earlier, such as the French files at 2026-08-31, ends at that file's last date, written in the fixture manifest); the drafts, their acceptance panels and the committed headers carry the same date, and it is listed in the `definitions_md5` manifest. For a header registered after the freeze it is the last month-end official close before its commit (a rule-fixed end, never chosen; ASPEC round 4 note 1). A later end is a re-gate under §8.8.
   - A card that is to act in the recommended book on a long sample declares in its header (red line P1):
     - a **start band** of a shape frozen in `gate.evaluation.start_band_shapes`, never declared by a card: by default the monthly starts over the first 33 months of the span; R-06 KR's band is Resolution 1's binding band, the 32 monthly starts 1997-05 … 1999-12 (they follow from its history start); R-29's is decade-spaced (daily spans of ≥ 80 years: the declared start, then the first session of January of each decade year at least 10 years before the span end, i.e. 1930 … 2010 on R-29's span: 10 starts);
     - **calendar-midpoint halves**, with the split date written in the header (it follows from the history start and the fixed span end).
   - **Stability floor (gated), the same three clauses for every band shape:** no REJECT at any start in the band; PASS in ≥ 2/3 of the band's starts (≥ 80% for the decade-spaced shape), compared as integer counts (3·n_pass ≥ 2·n_starts: R-06 KR ≥ 22 of 32; 5·n_pass ≥ 4·n_starts: R-29 ≥ 8 of 10), never as a float; no REJECT in either midpoint half.
   - Printed: the PASS share, the range of ΔMDD and ΔES across starts, and rolling-decade results.
5. **Regime lines.**
   - A long-sample card prints its checks per R-20 regime (Korea: pre-ETF 1997 → 2002-10; the ETF era; ±30% limits from 2015-06-15).
   - Its header declares **one primary out-of-sample line**. R-06 KR's is the ETF-era line, which gates per Resolution 1; its 2002-10 → 2015-12 pre-design line is printed.
6. **Risk layer inside card books (frozen with the package; C-2).** Card books (on, off and S, in backtests and in forward records) apply the data invariants (R-01, R-19, R-20, R-26) and the bounds (R-02). They exclude the R-07 hard stop with its re-arm, the R-07 concentration caps and the semiconductor cap, except for a card whose claim concerns them (R-31 includes the hard stop, as stated there). Those invariants are judged on the composed recommended book by the §8.7 stack card once one exists (two or more de-risk factors in a market's recommended book); until then no card gates them, and the invariants-only book is printed with and without them (G-LAD-04). Each card prints a `with_risk_layer` line (hard stop and caps) for its on and S books, never gated. The indicative numbers follow this convention: KOSPI VT20's maximum drawdown is −45.3% without the hard stop and −56.4% with it, over 24 HALTs (Check C2), which is why the convention is frozen, not chosen per card. Key: `gate.evaluation.risk_layer_in_card_books`.

**Config keys** (merge into §7; frozen in `gate.package`):
```yaml
gate:
  evaluation:                                        # R-22
    episode_rule: {name: alternating_bear_bull, version: "1", prices: own_official_closes,
                   theta: {default: 0.20, KR: 0.20, US_SPX: 0.15}, low_vol_declared: [US_SPX],
                   others: {rule: "0.15 if long-run median SMA20 vol < 0.18 else 0.20", written_before_first_run: true},
                   window: first_return_after_peak_close_to_trough, sep_2026: asserted_not_an_episode}
    shock_type_table: "§8.6 named windows (printed only)"
    post_trough_window_sessions: 63                  # printed, not gated
    cost_episodes: {rebound_2009: ["2009-03-09", "2009-06-30"], rebound_2020: ["2020-03-23", "2020-06-08"],
                    h1_2026: ["2026-01-02", "2026-06-30"]}
    returns: excess
    cash: {KR: BOK_CALL_RATE, US: US_RF, other: registry_before_first_run}
    cash_day_count: act_365                          # default, judgment
    cash_rate_date: latest_rate_dated_on_or_before_previous_session   # R-22 rule 3; a closed day of the rate's own calendar carries the prior rate
    cash_units: {annual_rate: act_365, per_period_return: as_published}   # French RF is a per-period return (R2-C5)
    cash_read: frozen_card_snapshot_available_at_recorded_never_filtered   # role history; a missing cash day refuses the card
    start: first_close_plus_estimator_warmup
    history_start: {KR: "1997-04-01", default: first_close_of_frozen_fixture}   # fixed before the freeze; a card never truncates it
    span_end: {drafted_cards: data_cutoff, later_cards: last_official_close_before_header_commit}
    data_cutoff: {KR: "2026-10-02", US: "2026-10-01"}   # the last official closes in the frozen reference data (§9.3.1), fixed now; in the manifest
    start_band_shapes:                               # frozen; a card declares neither its band nor its pass share
      default: {months: 33, step: month, pass_share_min: "2/3"}
      R-06_KR: {from: "1997-05", to: "1999-12", step: month, starts: 32, pass_share_min: "2/3"}   # Resolution 1
      decade_spaced: {min_span_years: 80, starts: declared_start_then_january_of_each_decade, last_start_min_years_before_end: 10, pass_share_min: "4/5"}   # R-29
    stability_floor: {no_reject_at_any_band_start: true, pass_share_min: from_band_shape, compare: integer_counts,
                      no_reject_in_midpoint_halves: true, applies_to_every_shape: true}
    midpoint_halves: {split: calendar_midpoint_of_fixed_span, split_date_in_header: true}
    regime_lines: from_R20_tags
    primary_oos_line: declare_on_card
    risk_layer_in_card_books: {hard_stop: excluded_printed, caps: excluded_printed, except: card_claim_concerns_them}   # rule 6
```

**Outputs and schema fields** (§6.5).
- `model_card.macro.episode_rule_version` and `episodes[] = {peak, trough, depth, window, benefit_vs_S, share, regime_tags, post_trough_63, open}`.
- `tests.PC4 = {positive, n, max_share}` and the printed `pc4_section_8_6 = {positive, n, max_share}`.
- Header fields: `cash_convention`, `history_first_close`, `data_span` (with its fixed end), `start_band` (the frozen shape and its dates), `midpoint_halves` (the split date), `regime_lines`, `primary_oos_line`.
- Result fields: `start_band_results = {starts[], verdicts[], n_pass, n_starts, n_reject, floor_pass}`, `midpoint_halves_results = {h1, h2}`, `regime_line_results[]`, `cost_episodes[]`, `printed.with_risk_layer`.

**Fail-closed behaviour.**
- A card is refused if its header lacks `episode_rule_version`, `cash_convention` or `start`.
- An acting long-sample card is also refused if it lacks `start_band` or `midpoint_halves` (T-SCHEMA-02).
- A card whose cash series does not cover its span is refused. There is no silent cash = 0.
- Episodes built from vendor-derived or provisional closes are refused (R-01).

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-EPIS-01 | Objective episode builder | 18 alternating ≥ 20% KOSPI episodes on 1997–2026, 12 of them with troughs before 2008. 4 on 2016–26. 16 S&P episodes at 15% on 1990–2026. No Sep-2026 episode in either market, with the builder run without any override. An open bear at the end of a synthetic series is printed with `open = true` and counts toward neither PC-4 nor PC-7. |
| T-EPIS-02 | PC-4 on the Korea definitive cell (1997-04 → 2026-10, ETF 3 bp, R4b raw-return flag) | Objective episodes: 14 of 18 positive, maximum share 0.174 ± 0.01. The printed §8.6 line shows 0.493 (4 of 11). |
| T-EXCESS-01 | Excess-return convention | Reproduction in v1.2-check mode (§9.3.3) on PX2's cash fixture (FRED `IRSTCI01KRM156N`, monthly, ÷ 252, used from the month after; `qx_px2_02`): the same cell on excess returns gives ΔSR +0.006 and p_ni 0.078 ± 0.01, and the raw flag reproduces +0.026 and 0.052. Under the frozen conventions (R-22 rule 3: daily `BOK_CALL_RATE`, the latest rate dated on or before the previous session, act/365; R-24's studentized PC-3) the cell's values are computed, printed and md5-frozen at their first run (§9.4), never asserted against these. Units: the call rate enters as the latest rate dated ≤ t−1, × days ⁄ 365; a US session on which the Fed is closed (e.g. Columbus Day) accrues at the prior DTB3 rate; French daily RF enters as RF_t unchanged (a monthly card uses monthly RF unchanged); no cash read is filtered by publication time, and a missing cash day (a day of the series' own calendar without a value) refuses the card. |
| T-TROUGH-01 | Post-trough and cost episodes | Every card prints a trough → +63-session window per episode and the three cost episodes. The Korea cell (raw flag) shows, vs S: 2009 rebound −6.9 pp; 2020 rebound −15.5 pp; H1-2026 −31.5 pp. None of them enters PC-4. |
| T-BAND-01 | Stability floor and band shapes | R-06 KR's band has 32 monthly starts, 1997-05 … 1999-12 (Resolution 1), asserted as a pair with `history_start` KR 1997-04-01; the floor needs ≥ 22 PASS (3·n_pass ≥ 2·n_starts, integers), and the midpoint split date follows from the fixed span end. R-29's decade band has 10 starts and needs ≥ 8, with no REJECT at any of them. A synthetic band result with one REJECT start fails the floor even with a PASS share ≥ 2/3. A REJECT in either midpoint half fails it as well. |
| T-RLAYER-01 | Card-book convention (rule 6) | R-06 KR's on, off and S books on the 1997–2026 fixture follow rule 6. The `with_risk_layer` line reproduces Check C2 for the on-book within Level-1 tolerance (24 HALTs, maximum drawdown −56.4%, against −45.3% without the hard stop). Running a card with the convention flipped is refused (`gate.evaluation.risk_layer_in_card_books` is in the package md5). |

**Source items.** QF4-M6; QF4-A8; QF7-A20; X-PX2-N5; X-EX2-N1; QF5-A24.

**Evidence.**
- Resolutions 11 and 1.
- DLA §2.1:
  - the start sweep: 71 of 72 monthly starts from 1997-02 to 2003-01 PASS; ΔMDD ranges from +3.7 to +12.7 pp; S's worst drawdown is the 1997–98 crash only if the sample holds the June-1997 peak;
  - the PC-4 sensitivity: 0.493 against 0.174;
  - the cost episodes.
- PX2 (`qx_px2_04` S1): 97% of 33 starts pass PC-3 on raw returns against 70% on excess returns; ΔSR +0.025 → +0.006; p_ni 0.051 → 0.078.
- QF4-M6 counts (18 / 4 / 16).
- QF7-A20: exits 46–179 sessions after troughs; +57% missed in 2020.
- EX2 regime table: 1997–2002 alone REJECT; ETF era without 2026 PASS (p_ni 0.040).

### R-23 Step 3: family trial ledger and N_eff = max(N_clusters, N_equiv) — BUILD NOW · GOVERNANCE · P0 · M7 (frozen before the first card run)

**Purpose.** *NEW in v2.0.* Gate step 3 ("count every try") was undefined for macro cards:
- no rule fixed N, V or the benchmark;
- the figure cited as Bailey–López de Prado's eq. 9 was the Kish design effect, which padding with near-duplicates games (1.81 → 1.20);
- no script in the programme computed a deflated Sharpe at all.

R-23 fixes all of this blind (Resolution 5). The outcome: **R-03 passes (0.98), borderline (0.947) under the linear N̂; R-04 fails (0.77).**

**Package / module and functions** (`core/quant/backtest`, **proposed**):
- `ledger.append(family_id, config)` and `ledger.hash(family_id)`;
- `diff_corr(family_id) -> C`;
- `emax_sim(C, draws=200_000, seed=11)` and `emax_iid(N)`;
- `n_equiv(emax)`, `n_clusters(C)`;
- `deflated_dsr(dsr, se_obs, se_null, hurdle)`;
- `step3(card) -> Step3Result`.

`core/rules` stores the ledger hash per family. As in the QF3-A20 rename, the code uses `delta_sr` and `boot_delta_sr` for Sharpe differences; "DSR" is reserved for the deflated Sharpe ratio.

**Inputs (PIT fields).**
- The family ledger. `family_id` is assigned by rule, never chosen by the author: the module's family in `QC_modules.csv` (e.g. R-06 for every market vol target). A new card whose difference series correlates ≥ 0.5 (the cluster cut) with any existing family's rows on the common window is filed in that family, or refused. Rows are appended by `core/quant/backtest` itself on every run of a registered rule's code path, research scripts included, never by hand. Null-distribution runs (acceptance placebos, the 20-shift panel, GJR-null paths, D4 panels) are not configurations: they append no row and are logged in the attempts or evaluation log of their card. Each row carries `prev_row_md5` (a hash chain), the family hash is committed to the repository with every header, and a ledger whose chain does not verify is refused. Test runs write to a temporary copy (T-HERM-02). One row per configuration ever run, research phase included: `config_id`, `rule`, `params`, `timing_class ∈ {VALUE, NON-COMPLIANT, COMPLIANT}`, `span`, `instrument_book`, `cost`, `phase ∈ {research, card}`, `run_utc`, `script`, `results_md5`, and a reference to the stored difference series.
- The card's own daily excess-return books (R-22).

**Rule / algorithm.**
```python
ledger_hash  = md5(canonical_json(sorted(ledger_rows)))       # at registration and again after the run; a card without it is refused
N_raw        = len(ledger_rows)                                 # revision counts are never N
d_k          = x_k - x_comparator_k                             # comparator: overlay-off (CARD-O); S (CARD-P)
C            = corr([d_k for k in ledger])                      # on the common window
rho_bar      = mean_offdiag(C)
N_hat_linear     = rho_bar + (1 - rho_bar) * N_raw                  # BLdP eq. 9 (linear); printed bound
N_clusters   = n_clusters(C)                                    # average linkage on sqrt(0.5 * (1 - rho)), cut at sqrt(0.25), i.e. rho >= 0.5
E_sim        = mean(max_k Z_k), Z ~ N(0, C)                     # >= 200,000 draws, seed 11

def e(N):                                                       # expected max of N iid N(0,1)
    if N <= 1: return 0.0
    if N < 2:  return emax_iid_exact(N)                         # integral of x * N * phi(x) * Phi(x)**(N - 1); never Euler-Mascheroni below 2
    return (1 - g) * Phi_inv(1 - 1/N) + g * Phi_inv(1 - 1/(N * math.e))   # BLdP closed form, g = 0.5772156649

N_equiv      = e_inverse(E_sim)                                 # bisection on N in [1, 1e6]; e(N) drops at N = 2 from the exact 0.564 to
                                                                #   the closed form 0.520, so any E_sim in [0.520, 0.564] gives N_equiv = 2
N_eff        = max(N_clusters, N_equiv)
hurdle       = e(N_eff)                                         # = E_sim whenever N_equiv >= N_clusters
SE_obs       = Ledoit-Wolf HAC SE of the card's delta_SR vs its comparator (R-24)
SE_null      = median LW-HAC SE of delta_SR over the ledger's rebuilt trials of the same statistic   # if fewer than 2: SE_obs
               # if the ledger holds >= 30 independent trials, V = cross-trial variance of delta_SR (BLdP's V); both are printed
deflated     = Phi((delta_SR - SE_null * hurdle) / SE_obs)
```
- **CARD-O:** step 3 passes if and only if `deflated ≥ 0.95`.
- **CARD-P:** step 3 is not a superiority test.
  - DSR vs 0 and PSR vs S are printed but **not gated**.
  - Selection is controlled by four things: the ledger, the PC-6 plateau, step-4 PBO on the protective objective, and the **selection factor** f applied to the PC-1′ and PC-3 p-values (R-21).
  - f = N_eff (Bonferroni) for a configuration selected as the best of ≥ 2 ledger configurations evaluated on any part of the evaluation span. Holm-adjusted p-values across the run variants are printed.
  - f = 1 only for a configuration fixed in a committed header (md5 externally anchored, §8.1.3) or in a published SPEC version before any configuration of the family was evaluated on the card's evaluation span, overlap judged by the frozen `gate.step3.card_p.overlap_rule` = `any_overlap` (any family ledger row whose span intersects the evaluation span; Resolution 5's "factor 1 if declared before the sample existed"); otherwise f = N_eff. Sensitivity rows run after that commit do not count as selection. **Row set (frozen; R2-C1).** A ledger row is a distinct configuration of the family (a distinct `config_id`: the rule and every parameter in its `params`, signal, threshold, target, lookback, multiplier and lag included, plus estimator, window, cap, book, rebalance rule, timing class and start convention) whose result anyone saw before the v2 freeze, plus every configuration registered since, in the snapshot named by `ledger_hash_at_registration`; for R-06 KR the seed is every configuration whose Korean-data result was seen (R4's and R4b's comparisons and the QF, QX and DL variants, enumerated in §9.5). It never contains the rows the card's own run appends (its R-34 lags and variant lines, which count for later cards) or null-distribution runs (below). Where readings of the row set differ (the card's market only, or the whole family across markets as Resolution 5's "every configuration ever run in a card's family" reads, with any card whose family filing is contested counted both ways), f is computed under each defensible reading and the **maximum** binds (the red line "no gate rule chosen after seeing the card it decides"). The published-SPEC-version route reads the SPEC publication instants from `gate.step3.spec_versions`. For each CARD-P drafted for §8.1.3, the acceptance report prints f under each reading with N_raw, N_clusters, N_equiv and E_sim on the frozen seed (§9.5), before any card runs; the card run recomputes f; where it differs from the report's (a family row registered in between), the larger f binds and both are printed (T-SEL-01 (e)).
  - **f is computed, never declared (C-2).** `step3()` derives it from the ledger rows' `span` and `run_utc` and the header's commit time; a header that declares a value is refused. Every CARD-P prints its verdict at f = 1 and at f = N_eff, and f under each row-set reading; the binding f is the maximum under the frozen overlap rule (T-SEL-01). Example: R-06 KR's 20-session window and cap 1.0 were compared with a 60-session window and cap 1.5 on 2016–26 (R4) before SPEC v1.1, so its f is N_eff (§8.9 shows the sensitivity).
- **Printed on every card:**
  - N_raw, N_hat_linear, N_clusters, N_equiv, N_eff, E_sim, SE_obs, SE_null and V_trials;
  - the deflated value at N_raw and at N_hat_linear, with the flag **"step 3 borderline"** if the value at N_hat_linear is < 0.95;
  - the break-even N;
  - the one-sided z-check (z ≥ 2.50 for ≤ 8 pre-registered cells; 3.34 one-sided Bonferroni beyond);
  - a BY q-value from the global ledger (R-24).
- **Never:** the Kish form M ⁄ (1 + (M − 1)ρ̄), or a revision count used as N. A static check enforces both.
- **Every lag of the timing profile (R-34) and every variant run (instrument book, rebalance, band, estimator) is a ledger row.**

**Config keys** (merge into §7; frozen in `gate.package`):
```yaml
gate:
  step3:                                             # R-23
    ledger: {required: true, hash: md5_canonical_json, research_phase_included: true, timing_class_required: true,
             family_id: by_rule_QC_modules, filing_cluster_rho: 0.5, appended_by: harness_only, hash_chain: prev_row_md5,
             hash_at: [registration, run]}
    basis: difference_series                         # rule minus comparator (overlay-off for CARD-O, S for CARD-P)
    n_gate: "max(N_clusters, N_equiv)"
    emax: {simulated_draws: 200000, seed: 11, below_2: exact_integral, from_2: bldp_closed_form}
    clusters: {linkage: average, rho_min: 0.5}
    variance: {default: V_null, se_null: median_lw_hac_of_family_trials, use_trials_if_independent_ge: 30, print_both: true}
    card_o_bar: 0.95
    card_p: {gated: false, selection_factor: bonferroni_N_eff, factor_one_if: config_fixed_before_any_run_on_span,
             overlap_rule: any_overlap, computed_by: step3, declared_on_header: refused, print_both: [f_1, f_N_eff],
             holm_across_variants: printed}
    row_set: {unit: distinct_configuration, key: [rule, params, estimator, window, cap, book, rebalance, timing_class, start_convention], readings: [market_scoped, family_wide], combine: max,
              snapshot: ledger_hash_at_registration, excludes: [own_run_rows, null_distribution_runs]}   # R2-C1
    spec_versions: publication_utc_listed_in_manifest   # the f = 1 route (a published SPEC version)
    printed: [N_raw, N_hat_linear_eq9, N_clusters, N_equiv, N_eff, break_even_N, z_check_one_sided_2p50_le_8_cells, by_q_global, dsr_vs0, psr_vs_S]
    forbidden: [kish_design_effect, revision_count_as_N]
```

**Outputs and schema fields** (§6.5).
- Header: `family_id`, `ledger_hash_at_registration`, `N_raw` at registration.
- Result: `ledger_hash_at_run`, `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `E_max_sim`, `V_null`, `V_trials` and `selection_factor = {value, rule: computed_by_step3, alt_value}`.
- `tests.step3 = {deflated_dSR, at_N_raw, at_N_hat_linear, borderline, break_even_N, z_check, by_q, dsr_vs0, psr_vs_S, selection_factor, pass}`.

**Fail-closed behaviour.**
- A header without `ledger_hash_at_registration` is refused. After the run, `ledger_hash_at_run` (the ledger including the run's own rows, e.g. the R-34 lags) must match the stored ledger, or the card is not written.
- A ledger whose hash chain does not verify, or a row not appended by the harness, is refused.
- A ledger row without a timing class is refused.
- If the correlation matrix cannot be built (a missing difference series), step 3 fails closed: CARD-O → no verdict is written; CARD-P → the selection factor defaults to N_raw.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-DSR-01 | DSR implementation | Reproduces Bailey–López de Prado's worked example: 0.9505 at N 46 and 0.9004 at N 100 (paper inputs frozen in the fixture, mapped as delta_SR = 2.5 ⁄ √250, SE_obs = √((1 + 3·SR + 9⁄4·SR²) ⁄ (T − 1)) with T 1,250, and SE_null·hurdle = √(0.5 ⁄ 250)·e(N); checked to reproduce both values) |
| T-DSR-02 | Units | The DSR API takes the Sharpe ratio and T in one declared unit (`units ∈ {daily, monthly}`: per-period SR with that period's count T). The same card's DSR computed on daily and on monthly data agrees within 0.1. An annualised SR passed with a daily T raises. |
| T-NEFF-01 | N_equiv on QF3's 26-trial difference-series matrix (`QX_EX1_qf3_trial_corr_diff.csv`, seed 11) | E_sim = 1.33 ± 0.01. N_equiv = 6.3 ± 0.4. N_clusters = 5. N_hat_linear = 12.6 ± 0.1. Padding with 80 near-duplicates of R-03 (ρ 0.99) moves N_equiv by < 0.5 (6.33 → 6.59). |
| T-STEP3-01 | R-03 and R-04 outcomes (QF3 inputs: R-03 ΔSR 0.2729, SE_obs 0.0716, SE_null 0.0935; R-04 0.0724 / 0.0349 / 0.0349) | R-03: 0.98 ± 0.01, PASS; at N_hat_linear 0.947 ± 0.01, flagged "step 3 borderline". R-04: 0.77 ± 0.02, FAIL. |
| T-STEP3-02 | Refusals | A card without a ledger hash is refused. A static scan finds no implementation of M ⁄ (1 + (M − 1)ρ̄). |
| T-SEL-01 | Selection factor computed | (a) Configuration A and variant B are run on 2016–26, then A's header is committed and A runs on 1997–2026: f = N_eff under `any_overlap`. (b) A configuration committed before any family row touches its span: f = 1. (c) A header that declares `selection_factor` is refused. (d) The card prints both verdicts (f = 1 and f = N_eff). (e) The card run recomputes f; where it differs from the acceptance report's f for its draft (a family row registered in between), the larger f binds and both are printed, and the run is never refused for the difference. (f) A placebo, shift-panel or GJR-null run appends no ledger row, and the card's own lag rows do not enter its f. (g) With two defensible row-set readings giving f 1.3 and 2.9, the card's binding f is 2.9 (the maximum; R2-C1). (h) Two configurations that differ only in target, threshold, multiplier or lag are two rows; QF3's 26 trials stay 26 rows (T-NEFF-01). |
| T-LEDGER-01 | Ledger integrity | A hand-edited row breaks the hash chain and the ledger is refused. A run of a registered rule's code path from a research script appends its row. A card whose `ledger_hash_at_run` differs from the stored ledger is not written. |

**Source items.** QF3-A1; QF3-M1; X-EX1-N1; X-PX1-N1; QF3-A20; QF3-C1; QF3-A1b (INVALID; withdrawn).

**Evidence.**
- Resolution 5.
- EX1 §4.1 (`qx_ex1_dsr_nhat.py`): N_equiv 6.3; R-03 0.981; R-04 0.772; the padding test (Kish 1.81 → 1.20 and R-04 0.951 → 0.986; linear 12.6 → 19.0; N_equiv 6.33 → 6.59).
- QF chair §0.3: E[max Z] 1.329; deflated R-03 0.982 at 6.3, 0.951 at the break-even 11.9, 0.947 at 12.6.
- DLB-T2b / T2c: eq. 9 is linear; own DSR code reproduces 0.9505 / 0.9004.
- DLA-G2: the Korea card's DSR vs 0 is 0.99 / 0.81 / 0.63 at N 1 / 10 / 34, so DSR is the wrong object for CARD-P.
- Note on the E[max] function: at N 12.6 the BLdP closed form gives 1.688 (deflated 0.946); the exact iid integral gives 1.653 (0.951). The printed bound therefore uses the paper's closed form above N = 2, as every council computation did.

### R-24 Statistics and power harness: studentized bootstrap, SE ladder, power/MDE line, PBO on the card claim, Lo-adjusted Sharpe — BUILD NOW · GOVERNANCE · P0 · M7

**Purpose.** *NEW in v2.0.* Several gate statistics were under-specified:
- the block length targeted the wrong object;
- the percentile bootstrap printed p = 0;
- 2,000 resamples cannot resolve multiplicity-adjusted p-values;
- PBO was never computed, because every card declared no searched parameter;
- no card carried power.

R-24 fixes all of these. Its definitions are frozen with the gate package (§8.1.3).

**Package / module and functions** (`core/quant/backtest`, **proposed**):
- `lw_studentized_boot(x_a, x_b, block, B, seed)`;
- `pw_block_psi(x_a, x_b)`;
- `se_ladder(x_a, x_b, blocks=(10, 21, 63, 126, 250))`;
- `power_line(se, deltas=(0.05, 0.10))`;
- `pbo_cscv(configs, objective, S=16)` and `pbo_null(...)`;
- `lo_adjusted_sr(x, lags)`;
- `by_qvalue(global_ledger)`;
- `harvey_liu_haircut(z, M)`.

**Inputs (PIT fields).** The card's daily excess-return books (R-22); the family ledger (R-23) and the frozen PC-6 grid (R-21); the global ledger of tested variants (for BY).

**Rule / algorithm.**
1. **Bootstrap for step 2, step 5 and PC-3.**
   - Ledoit–Wolf studentized circular-block bootstrap with a null-centred t*. The HAC p-value is printed beside it.
   - B = 2,000, seed 11.
   - A p-value of 0 is printed "< 1/B".
2. **Block length.**
   - Politis–White on the **influence function ψ of ΔSR** (not on d or d²), with a floor of 21 sessions.
   - PC-3's p_ni = max(p_10, p_max(21, PW(ψ))) (R-21).
   - The **SE ladder**: SE(ΔSR) from LW-HAC and from the block bootstrap at 10, 21, 63, 126 and 250 sessions. **SE_plateau = the maximum.** The curve and the block count T ⁄ b are printed.
3. **Power line on every card.**
   - MDE80 = (z₀.₉₀ + z₀.₈₀)·SE_plateau = 2.1232·SE_plateau (one-sided 10%, 80% power).
   - Power at Δ = +0.05 and +0.10: Φ(Δ ⁄ SE − 1.2816).
   - CARD-P also prints PC-3 power at a true ΔSR of 0, Φ(δ ⁄ SE − 1.2816), and the years needed to detect +0.05: T_years·(2.1232·SE ⁄ 0.05)², with T_years = sessions ⁄ 252 and SE = SE_plateau (KOSPI 2016–26: ≈ 10.4 years; at SE 0.130 → 317, at the plateau's NW10 0.132 → 327; calendar years would give more).
4. **UNDERPOWERED.** If MDE80 > 0.10 (the top of the de-risk base rate), a failed step-5 p-value (CARD-O) or a failed PC-3 p-value (CARD-P) maps to INSUFFICIENT DATA, with reason code `underpowered`. It never waives a PC-1′ failure, a PC-2 failure or the PC-3 point REJECT, and never touches step 3.
5. **Multiplicity.**
   - Run it on analytic HAC / LW p-values, or with B ≥ 20·M ⁄ α when bootstrap p-values are used.
   - Every card prints a BY q-value from the global ledger and the Harvey–Liu haircut, beside `live_sharpe_multiplier: 0.60` ("take 40% off"; step 9).
   - Sidedness is one convention throughout: one-sided 2.50 (≤ 8 cells) and 3.34 (Bonferroni-120).
6. **PBO (step 4).**
   - The configuration set is the family ledger ∪ the frozen PC-6 grid of the card's rule type (`gate.card_p_v2.pc6_axes`, R-21); no card declares its own grid.
   - The objective is the card's own claim:
     - CARD-O: paired ΔSR vs overlay-off;
     - CARD-P: a block-wise tail-loss statistic (ΔES95 of 21-session returns within each CSCV block), **never MDD on concatenated half-samples**.
   - CSCV uses S = 16 blocks (12,870 splits).
   - "The winner loses" means the in-sample best configuration's out-of-sample objective is below the comparator's (overlay-off, or S) in more than 10% of splits.
   - The step runs when ≥ 10 configurations exist; with fewer, the card prints "PBO not run (n < 10)" and the reason. PBO > 0.2 with the winner losing is a REJECT (unchanged).
   - Printed beside it: the null-calibrated PBO (the same CSCV on ≥ 10 pure-noise configurations) and the degradation slope.
7. **Lo-adjusted annual Sharpe.** Printed at 20 lags and at all lags, with its lag sensitivity. Sharpe ratios are compared within one market only, and this line never gates.

**Config keys** (merge into §7; frozen in `gate.package`):
```yaml
gate:
  stats:                                             # R-24
    bootstrap: {method: ledoit_wolf_studentized_circular_block, null_centred: true, resamples: 2000, seed: 11,
                p_zero_print: "< 1/B", hac_p_printed: true}
    block: {rule: politis_white_on_influence_function, floor_sessions: 21, pc3_also_block_10: true}
    se_ladder_blocks: [10, 21, 63, 126, 250]         # SE_plateau = max (incl. LW-HAC)
    power: {alpha_one_sided: 0.10, power: 0.80, mde_factor: 2.1232, deltas: [0.05, 0.10], t_years: sessions_over_252, se: se_plateau}
    underpowered: {mde80_gt: 0.10, converts: [step5_p_value, pc3_p_value]}
    multiplicity: {p_source: analytic_hac_lw, bootstrap_resamples_if_used: "20*M/alpha", by_q_from_global_ledger: true,
                   one_sided_z: {le_8_cells: 2.50, bonferroni_120: 3.34}}
    pbo: {configs: ledger_union_frozen_pc6_grid, min_configs: 10, cscv_blocks: 16,
          objective: {CARD_O: paired_dSR_vs_off, CARD_P: blockwise_dES95_21}, winner_loses_share_gt: 0.10,
          reject_if: "PBO > 0.2 and winner_loses", null_calibration: printed}
    lo_adjusted_sr: {lags: [20, all], printed: true, gated: false}
    live_sharpe_multiplier: 0.60                     # take 40% off; HL haircut printed beside it
```

**Outputs and schema fields** (§6.5).
- `model_card.macro.power = {se_hac, se_blk250, se_plateau, se_curve, mde80, power_at_0p05, power_at_0p10, pc3_power_at_0, years_to_detect_0p05}`.
- `tests.step2`, `tests.step5` and `tests.PC3` carry `{p_lw, p_hac, block, n_blocks}`; in `tests.PC3` these sit beside R-21's fields: `p_lw`, `block` and `n_blocks` are those of the leg whose p sets p_ni (the larger of p10 and pPW), and R-21's `block_PW` is the Politis–White leg's block.
- `tests.step4 = {pbo, winner_loses_share, pbo_null, slope, n_configs}`.
- `printed = {lo_sr_20, lo_sr_all, by_q, hl_haircut}`.
- `verdict_reason` may hold `underpowered`.

**Fail-closed behaviour.**
- A card without a power block is refused (T-SCHEMA-02).
- If the block length cannot be computed, the 250-session block is used, and the event is logged.
- PBO is not run with fewer than 10 configurations, and that is stated on the card. It is never imputed.
- The UNDERPOWERED code applied to any check outside rule 4 raises.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-POWER-01 | SE fixtures | SE(ΔSR) 0.061 ± 0.005 for US VT15 vs S (50 bp, 1990–2026) and 0.130 ± 0.01 for KOSPI VT20 vs S (3 bp, 2016–26). MDE80 0.13 / 0.28. Years to detect +0.05 (T_years = sessions ⁄ 252, SE = SE_plateau of the named fixture): inside G-PWR-01's ranges, 241–246 / 319–330, restated to a point before the freeze (§9.4). PC-3 power at true 0 for KOSPI 2016–26: 0.30 ± 0.02. |
| T-POWER-02 | Power block on every card | Every card prints SE (HAC and 250-block), MDE80 and power. A card without them is refused. |
| T-UNDERPOW-01 | Scope of UNDERPOWERED | With MDE80 > 0.10: a failed PC-3 p-value → INSUFFICIENT DATA (`underpowered`). A PC-3 point below −0.10, a PC-1′ failure or a PC-2 failure keep their REJECT or INSUFFICIENT path unchanged. |
| T-PZERO-01 | No p = 0 | A resample count of 0 prints "< 1/B". No card field holds p = 0. |
| T-PBO-01 | PBO definition | The configuration set is ledger ∪ the frozen PC-6 grid, on the card's own objective. The KOSPI VT grid's Sharpe-objective PBO (0.28) is printed. The protective-objective value is the one the step uses. The noise control follows QF3's recipe exactly (`qf3_pbo_cscv.py`): the first draw of `numpy.random.default_rng(11)`, `normal(0, 0.01, size=(2600, 10))`, truncated to 2,592 rows, 16 contiguous blocks, Sharpe with ddof = 1: PBO 0.536 (± 0.001). Its calibration is checked on 200 such panels (child seeds of `SeedSequence(11)`): mean PBO in [0.45, 0.55]. A single panel is never asserted against [0.4, 0.6] (its SD is ≈ 0.22). |
| T-SE-01 | SE ladder | R-03 vs unscaled (50 bp): LW-HAC 0.072, 250-block 0.091 (± 0.005). z falls from 3.81 to 3.0 and still passes 2.50. |

**Source items.** QF3-M2; QF3-A19; QF3-M7; QF3-M8; QF3-A8; QF3-A9; QF3-A10; QF3-A11; QF3-A21; QF3-A3; QF4-A7.

**Evidence.**
- QF3 §4.3: the SE table and PW(ψ) 2–62 against PW(d²) 42–251.
- QF3 §4.2: PBO pilot (momentum family 0.000; R-03 grid 0.009; KOSPI VT grid 0.282 / 0.364; noise 0.536).
- QF3 §4.4: CARD-P power (P(REJECT) ≈ 0.6 at a true ΔSR of 0).
- QF3-A11: 11 of 199 variants at the 1 ⁄ B floor.
- QF3-A21: Lo η ⁄ √252 is 0.838 at 20 lags against 0.951 at all lags.
- DLB-T5a: SE 0.061 / 0.130; MDE80 0.128 / 0.276.
- DLA-K11: Korea 1997–2026 SE 0.066.
- PX1 §3.2: 12 forward months move SE 0.130 → 0.124 and PC-3 power 0.305 → 0.317.

### R-25 Forward-record monitoring and demotion v2: whole-book NAV, calibrated alarms, operational triggers — BUILD NOW · GOVERNANCE · P0 · M8

**Purpose.** *NEW in v2.0.* The v1.2 demotion triggers fail in three ways:
- they fire on noise (in 30% of years for R-03, 50% for KOSPI VT and 69% for US VT);
- they carry a sign error that demotes protective cards;
- they cannot tell a real vol target from a timing-free placebo in 12 months (22% vs 22% on KOSPI).

In v2, forward records are **falsification alarms and integrity checks only**. A forward record can lower a verdict and never raise one (red lines P3 and Q3). Every statistical trigger runs on whole-book NAV and sits under a calibrated, book-level false-demotion budget.

**Package / module and functions.**
- `core/engine/state`: forward-book state, switch counts, alarm state, CUSUM state.
- `core/quant/backtest`, **proposed**:
  - `calibrate_alarms(card) -> AlarmThresholds` (on the design sample);
  - `cusum_monitor(...)`;
  - `false_demotion_rate(card, shifts=20)`;
  - `demote(card, reason)`.
- `core/engine/runtime`: the hard stop (R-07) remains the kill at book level. It is a review event, not a demotion trigger.

**Inputs (PIT fields).**
- Forward books from the header commit: the rule book, the overlay-off book and S (for CARD-P), each written with `macro_state` / `overlay_decision` artifacts (`decision_utc`, inputs with `available_at_utc` and `value_status`).
- The whole simulated-book NAV across sleeves, with per-card attribution.
- The lag-audit log, the rules-store edit history and the per-card switch counts.

**Rule / algorithm.**
1. **Denominator.** Every statistical trigger uses **whole-book NAV**, with per-card attribution printed. Sleeve NAV is never the denominator.
2. **Operational and integrity triggers** demote immediately, outside the budget:
   - any lag-audit violation in the forward record;
   - an acting-parameter edit outside a card revision (rules-store edit history);
   - a provisional or stale input that reached an acting decision (R-01, R-19);
   - an operator kill of a card's forward books (§3.8; R3-1);
   - more than 10% of a card's scheduled decisions in any rolling 12 months late, missed, failed closed, or HALTED or DISARMED (§8.8 (b));
   - switches above the 99th percentile of the card's Poisson or negative-binomial fit on the design sample (Poisson unless a likelihood-ratio test at 5% prefers the negative binomial; default, judgment). This replaces "2× the budget".
3. **Catastrophic bound** (statistical; inside the budget). Thresholds are calibrated by bootstrap on the card's full design sample.
   - **CARD-P:** all three of the following over a rolling 12 months.
     - Forward ΔMDD vs S ≤ 0. **That means "no protection".** It is the corrected sign of v1.2 §8.8.
     - Forward ΔES95 of 21-session returns vs S ≤ 0.
     - Forward ΔSR vs S below the design sample's 2.5th percentile of rolling 12-month ΔSR. The calibrated 2.5% thresholds are −0.39 for KOSPI VT and −0.73 for US VT (QF3-A7).
   - **CARD-O:** either of the following.
     - The 6-month gap (comparator − on) on book NAV exceeds 2σ of its tracking distribution, pre-registered on the design sample (QF5-M3).
     - The 12-month ΔSR vs the comparator falls below the design sample's 2.5th percentile (R-03: −0.20).
4. **Sequential trigger** (statistical; inside the budget).
   - A one-sided CUSUM on monthly paired differences: z_m = (d_m − μ_design) ⁄ σ_design; S_m = max(0, S_{m−1} − z_m − k); alarm when S_m ≥ h.
   - k = 0.25. h is the smallest value whose in-control ARL is ≥ 20 years under a stationary bootstrap of the design sample's monthly paired differences (B = 2,000, seed 11, mean block 12 months; default, judgment). The naive h 8 alarms 10–13 times a decade.
5. **Book-level false-demotion budget.**
   - The default is ≤ 10% a year across all statistical triggers (D4). It is split equally across active cards (≈ 5% each with two cards). "Active cards" are cards with disposition RECOMMENDATION or BUILD_AS_INSURANCE whose forward record is running. A card's split and its calibrated thresholds are fixed when its forward record starts and are never recalibrated when the number of active cards changes; a later card receives an equal share of the budget then unallocated, and the book-level total is printed. A card whose panel exceeds its split before its start tightens h, then its quantile thresholds, until it passes; the result is recorded in its header.
   - Each card's split is verified on a **20-shift panel**: the card's design-sample paired series, circularly shifted by 20 evenly spaced offsets (≥ 252 sessions apart, so ≥ 20 × 252 = 5,040 sessions are needed; a shorter design sample uses ⌊T ⁄ 252⌋ offsets and prints the count). The calibrated triggers run on each shifted record (seed 11). The alarms per record-year must be ≤ the card's split.
   - The owner may tighten the budget (D4).
6. **What a forward record may do.**
   - It may demote; integrity checks and catastrophe alarms are its only jobs.
   - It may **never raise a verdict** and never turn INSUFFICIENT DATA into PASS.
   - A card is re-gated upward only when **new history** adds an objective episode (continuous rules) or brings de-clustered onsets to the tier count (discrete rules). The re-gate runs the full v2 package on the extended sample as one counted revision. The forward window's own statistics are printed and never used to raise.
7. **After a demotion.**
   - The card's output leaves the recommended book.
   - It gets a new revision with a new header and a 6-month lockout. The verdict is set by rule (default, judgment; council to confirm): an operational or integrity trigger → REVISE (permitted fix: repair, then a counted re-run under the same package); a catastrophic or CUSUM trigger → REJECT. The lockout applies to the family × market: no new card, revision, instrument book or R-18 re-anchoring of that family in that market enters the recommended book during it.
   - Demoting a CARD-P never removes the risk-layer invariants.
   - A pre-declared R-18 re-anchoring is not a new card.
   - A bull-market lag alone is the insurance premium. It never demotes.
8. **Honesty line** on every card page: "12 months of forward record can only detect catastrophic decay." Beside it, the card's calibrated 2.5% threshold (−0.20 / −0.39 / −0.73 Sharpe for R-03 / KOSPI VT / US VT).

**Config keys** (merge into §7; this replaces v1.2's `gate.demotion`):
```yaml
monitoring:                                          # R-25
  denominator: whole_book_nav
  operational_triggers: [lag_audit_violation, acting_param_edit_outside_revision, provisional_or_stale_input_reached_acting_decision,
                         switches_gt_p99_poisson_negbin, operator_kill_of_forward_books,
                         decision_gaps_gt_10pct_rolling_12m]          # immediate; outside the budget (§3.8, §8.8 (b))
  catastrophic:
    card_p: {all_of: ["fwd_dMDD_vs_S <= 0", "fwd_dES95_21_vs_S <= 0", "fwd_dSR_12m_vs_S < design_p2.5"], window_months: 12}
    card_o: {any_of: ["gap6m_comparator_minus_on_book_nav > 2 * sigma_design", "fwd_dSR_12m_vs_comparator < design_p2.5"]}
  cusum: {frequency: monthly, k: 0.25, h: bootstrap_calibrated, in_control_arl_years_min: 20}
  false_demotion_budget_per_year: 0.10              # canonical key of D4 (owner_decisions.D4, Quick start)
  false_demotion_budget_split: {rule: equal_across_active_cards, fixed_at_record_start: true, recalibrated_on_new_card: false}
  budget_check: {panel: circular_shift, shifts: 20, min_offset_sessions: 252, short_sample: floor_T_over_252_offsets, seed: 11}
  cusum_calibration: {bootstrap: stationary, resamples: 2000, seed: 11, mean_block_months: 12}   # default, judgment
  switch_model: {default: poisson, negbin_if_lr_test_p_lt: 0.05}                                   # default, judgment
  demotion_verdict: {operational_or_integrity: REVISE, catastrophic_or_cusum: REJECT}              # default, judgment
  lockout_scope: family_x_market
  nav_unavailable_ops_halt_after_decisions: 2
  forward_record_can_raise_verdict: false
  regate_up_only_on_new_history: {continuous: new_objective_episode, discrete: tier_onset_count}
  lockout_months_after_demotion: 6
  bull_lag_alone_demotes: false
```

**Outputs and schema fields** (§6.5).
- `model_card.macro.forward_record = {start_utc, first_registered_utc, months, dSR_vs_S, dES21, dMDD, cusum_S, alarms[], switches, switch_p99, lag_audit_violations, demoted: bool, demotion_reason, honesty_line, missed_decisions, gaps[]}` (the age counts from `first_registered_utc`; gaps are excluded from both sides, §3.8).
- `monitoring_report` (weekly brief; monthly card page).

**Fail-closed behaviour.**
- If the whole-book NAV is unavailable, statistical triggers are suspended and alerted, and operational triggers stay live. NAV unavailable on more than 2 consecutive decisions is an OPS HALT of the books it values (the hard stop cannot be evaluated without it), and the forward record marks the gap.
- A card with no calibrated thresholds (no design sample) cannot start a forward record in the recommended book.
- Any attempt to use forward statistics to change a verdict upward raises.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-DEMOTE-01 | Sign and wording | The CARD-P trigger text reads "forward ΔMDD vs S ≤ 0 = no protection". A synthetic forward record with ΔMDD > 0 and ES protection never demotes. |
| T-DEMOTE-02 | Denominator | Every statistical trigger reads whole-book NAV. A card at 20% of the book with sleeve-level noise does not fire on the seeded fixture (seed 11; EX1: the 6-month 2% rule fires in 3.3% of 12-month records at 20% of NAV, against 31% at sleeve level). |
| T-DEMOTE-03 | Budget on the 20-shift panel | The book-level false-demotion rate is ≤ the declared budget (default 10% a year, D4). Each card is ≤ its equal split. |
| T-DEMOTE-04 | Operational triggers | An injected lag-audit violation, or an acting-parameter edit outside a revision, demotes immediately, even with the budget unused; so does an operator kill of a card's forward books (its gap still excluded), and 26 HALTED decisions of a card's books in 12 months trip §8.8 (b)'s 10% budget |
| T-DEMOTE-05 | No upward route | No forward record can raise a card's verdict. An INSUFFICIENT card with 12 strong forward months stays INSUFFICIENT until new history adds an objective episode. |

**Source items.** QF3-A7; QF3-M5; QF5-A7; QF5-M3; X-EX1-N3; QF3-A6.

**Evidence.**
- QF3 §4.9: fixed triggers fire in 29.7% / 50.0% / 69.4% of years; the calibrated 2.5% thresholds are −0.20 / −0.39 / −0.73.
- EX1 §2(1) (`QX_EX1_demotion.csv`):
  - SPEC CARD-P on KOSPI: 22% real vs 22% placebo;
  - US: 42% vs 34%;
  - calibrated: 0.6% vs 1.1%;
  - sleeve-level 31% vs book-level 3.3%.
- Philips–Yashchin–Stein: CUSUM detects flat-to-benchmark performance in ≈ 40 months.
- PX1 §3.2: 12 months add 3–10% of the information.
- Executives' chair §5.6; owner decision D4.

### R-26 Instrument book, notional and cost realism: tick floor, granularity floor, header fields, execution variants — BUILD NOW · INVARIANT · P0 · M0

**Purpose.** *NEW in v2.0.* Verdicts depend on the book, so the book must be one the desk can execute at the declared cost and size (red lines E5 and Q4).
- The same US rule is a REJECT at 50 bp on US shares and a PASS at 5 bp on futures.
- A ₩69 inverse ETF costs ≈ 74 bp per side, not the table's 3 bp.
- A ₩0.1bn sleeve cannot track a vol target with integer futures contracts (7.5% a year tracking error).

R-26 makes the instrument book, rebalance rule, band and notional pre-registered header fields. It adds a cost floor that can only raise costs, and it refuses books that misrepresent execution.

**Package / module and functions.**
- `core/rules`: the cost table (read from the gate; never redefined here) and header validation, via `validate_card_header(header)`.
- `core/markets`: the instrument table (**proposed** fields): `type`, `leverage L`, an effective-dated `tick_table`, `tax_side`, `cost_class`, `contract_multiplier`, `eligibility`.
- `core/quant/backtest`, **proposed**:
  - `cost_per_side(instrument, date, price, side)`;
  - `stress_cost_line(...)`;
  - `exec_variants(card) -> {A, B, C}`;
  - `overnight_intraday_attribution(card)`;
  - `turnover_by_regime(card)`;
  - `roll_calendar(future)` and `roll_cost_line(card)`;
  - `ban_basis_line(card)`.

**Inputs (PIT fields).**
- Instrument prices: official closes and opens, with `value_status` and `session_date`.
- The effective-dated tick tables and tax regime (R-20 `tick_regime`, `sell_tax_pct`).
- Contract specifications.
- The sleeve's `notional_nav` (`sleeves.<market>.notional_nav`, owner-signed) and, for a non-KRW book, its `nav_fx` series.
- The KIS quote snapshots, once verified (QF1-A25), to calibrate the stress line.

**Rule / algorithm.**
1. **Cost floor (INVARIANT).** It can only raise the table rate, never lower it:
   ```
   cost_side(i, t) = max( table_rate(cost_class(i)),
                          commission + 0.5 * tick(i, P_t) / P_t + tax_side(i, t) )
   ```
   - The commission is the declared broker rate, 1.4 bp by default (the EX2 desk quote; the owner confirms it against the broker schedule).
   - `tax_side` is the sell tax on stock sells, 0.20% in 2026. ETFs are exempt.
   - Examples: KODEX 200 at ₩112,060 gives a floor of ≈ 1.6 bp, so the 3 bp table rate applies. 252670 at ₩69 has a half tick of 72.5 bp and a floor of 73.9 bp.
   - Lowering any cost in a header raises an error (DNB #23).
2. **Leveraged and inverse ETFs.**
   - Eligible only if the tick is ≤ 10 bp of the price.
   - Their own cost class, `KRX_LI_ETF`, is read from the gate and never lower than the floor. If the gate's table has no `KRX_LI_ETF` class, its table rate is the KRX ETF rate (3 bp) and the tick floor governs (default, judgment). The ETF tick table is effective-dated: ₩1 below ₩2,000 and ₩5 at ₩2,000 or more from 2023-12-11; earlier ticks come from the KRX notices (owner action, Quick start).
   - Look-through exposure is multiplied by L in R-07's caps.
   - Korean investor-eligibility rules (deposit and education requirements, tightened on 2026-07-16) are stored as metadata.
   - The Quant Lab path formula is ln(1 + R_L) = L·ln(1 + R) − ½(L² − L)·Σr² − carry (R-16).
3. **Header fields (pre-registered, required on every card).**
   - `instrument_book` ∈ {`KRX_ETF_line`, `KRX_stock_book`, `KOSPI200_futures`, `mini_KOSPI200_futures`, `CME_micro_ES`, `US_shares_KIS`, `KRX_listed_SP500_ETF` (D5 only, with FX and NAV lag modelled), `crypto_venue`, `FX_KRX_USD_futures`, `FX_broker_spot`, `multi_line` (with `instrument_lines[]`, one declared line per market; R-14)};
   - `rebalance ∈ {daily, weekly, monthly}`;
   - `no_trade_band ∈ {0, 0.10}`. The 0.10 band is permitted only on stock and US-share books; it is declared ex ante, never tuned, and counted as one trial;
   - `notional_nav` in KRW, read from the sleeve's owner-signed, effective-dated key `sleeves.<market>.notional_nav` (one value per sleeve, shared by every card of that sleeve, logged like an owner decision). A card cannot declare its own notional. A change of the sleeve notional is a governance event that re-checks every futures-line card against the granularity floor; it never re-opens a verdict, and a futures-line card registered after the change is a new card counted in its family ledger;
   - `nav_fx`, for any book holding a non-KRW instrument: the named USD/KRW series (the timestamped 15:30:00 KST snapshot `USDKRW_1530_SNAPSHOT`, or `ECOS_1530_CLOSE` for history), its conversion instant and its role, which is the role of the book it values (R-19 rule 5): `acting_exposure` for a recommended or specification book, whose hard stop and ladder read the NAV (R-07, R-31); `forward_sim` for a FORWARD-SIM book such as R-29's;
   - `fill_model` (R-27);
   - `roll_calendar` (futures books).
   - A different instrument book, rebalance rule or band is a **new card** in the family ledger. A venue is never switched after results (DNB #23).
4. **Granularity floor.** A futures line is allowed only if one contract's notional, evaluated at the header commit (price × the effective-dated multiplier × `nav_fx`), is ≤ 5% of the sleeve notional (exactly 5% is allowed); otherwise the ETF line is the book. Contract notionals as of 2026-10-02 (EX2; a header check only, never a backtest constant):
   - KOSPI200 ≈ ₩280m;
   - mini KOSPI200 ≈ ₩56m;
   - Micro E-mini S&P 500 ≈ ₩52m.

   So a futures line needs a sleeve of about ₩1bn or more (mini K200 ≥ ₩1.12bn; Micro ES ≥ ₩1.04bn). Integer-contract tracking error for VT20 is 7.5% a year at ₩0.1bn, 1.6% at ₩0.5bn, 0.7% at ₩1bn and 0.17% at ₩3bn.
5. **No stock book as a market-gross scalar.** A market-level multiplier (`exposure_basis = total`, e.g. `vt`) is executed on the cheapest delta-one line declared ex ante, never by scaling every stock position. The 50 bp US-shares rate is valid for single names, never for a market scalar.

   Already-computed records (R-06 KR's 35 bp stock book; the US 50 bp card) stay on file as labelled lines. They cannot act.

   An ex-pair stock basket used to meet a concentration cap (R-07, D1) is not a market scalar, and this rule does not refuse it.
6. **Lines printed on every card (reported, never gated):**
   - **Execution variants:** A same close, B next open (the overnight gap at the old weight), C a one-session lag.
   - **Overnight / intraday attribution** of returns and of the overlay's benefit. Any KRX intraday long card must clear the −11% a year open-to-close drift.
   - **Turnover by regime**, e.g. KOSPI VT20 at 3.12 a year in 1997–2015 against 1.50 in 2016–26.
   - **Stress-cost line:** cost × clip(σ20 ⁄ σ_median, 1, 5), plus 10 bp per side on ETF-line close fills on days with |r| ≥ 3%. It stays printed and non-gating until it is calibrated on KIS quote snapshots (the settling test: 069500 and 005930 bid / ask at 15:19:59 KST on 20 sessions).
   - **Futures books:** the roll calendar (roll before expiry; the expiring KOSPI200 contract stops at 15:20 KST on its last day), a roll-cost line, and a basis line for short-sale-ban periods (R-20 tags).

**Config keys** (merge into §7; costs themselves stay in the gate's table, P10):
```yaml
instruments:                                         # R-26
  cost_floor: {formula: "max(table_rate, commission + 0.5*tick/price + tax_side)", commission_bp: 1.4,
               lower_than_table: forbidden}          # commission: EX2 quote; owner confirms vs broker schedule
  li_etf: {max_tick_bp_of_price: 10, cost_class: KRX_LI_ETF, lookthrough_multiplier: L, eligibility_rules: metadata}
  header_required: [instrument_book, rebalance, no_trade_band, notional_nav, fill_model, nav_fx_if_non_krw]
  notional_source: sleeves.<market>.notional_nav     # owner-signed, effective-dated; a card never declares its own
  no_trade_band: {allowed_values: [0.0, 0.10], allowed_books: [KRX_stock_book, US_shares_KIS], tuned: false}
  futures_granularity: {max_contract_share_of_sleeve: 0.05,
                        contract_notional_krw: {KOSPI200: 280e6, mini_KOSPI200: 56e6, CME_micro_ES: 52e6, as_of: "2026-10-02", use: header_check_only}}   # backtests compute notional PIT: price x effective-dated multiplier x nav_fx
  market_scalar_on_stock_book: refused
  us_shares_50bp: single_names_only
  printed_lines: [exec_variants_ABC, overnight_intraday, turnover_by_regime, stress_cost_line, roll_cost, ban_period_basis]
  stress_line: {multiplier: "clip(sigma20/sigma_median, 1, 5)", etf_close_extra_bp_if_abs_ret_ge_3pct: 10, gated: false}
  us_line_choice: {ref: sleeves.US.line}            # D5 (Quick start): CME_micro_ES, KRX_listed_SP500_ETF or none
```

**Outputs and schema fields** (§6.5).
- `model_card.macro.instrument_book` (with `instrument_lines[]` for `multi_line`), `rebalance`, `no_trade_band`, `notional_nav`, `nav_fx`, `fill_model` and `roll_calendar`.
- `costs_per_side = {table_bp, floor_bp, applied_bp, stress_line, roll_cost_line}` (one name per field, §6.5).
- `printed = {exec_variants: {A, B, C}, overnight_intraday, turnover_by_regime, stress_cost, roll_cost, ban_basis}`.
- `overlay_decision.extras = {instrument_book, contracts, w_target, w_held, band}`.

**Fail-closed behaviour.**
- A header missing any required field is refused.
- A futures line above the granularity floor is refused.
- A stock book used as a market scalar is refused.
- A cost below the floor raises.
- An instrument whose tick table cannot be read for the date is not tradable in the simulated book.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-COST-02 | Tick floor | 252670 at ₩69 is charged ≥ 72 bp per side (73.9 bp with the 1.4 bp commission). KODEX 200 at ₩112,060 is charged the 3 bp table rate. |
| T-COST-03 | No lowering | Lowering a cost in a card header raises. The stress line can only raise a cost. |
| T-BOOK-01 | Header and books | A card without `instrument_book`, `rebalance`, `no_trade_band` and `notional_nav` is refused. A futures line whose one contract exceeds 5% of the sleeve notional is refused (mini KOSPI200 ≈ ₩56m on a ₩0.1bn sleeve); exactly 5% is allowed. A header whose `notional_nav` differs from `sleeves.<market>.notional_nav` at commit is refused. A stock book used as a market-gross scalar is refused. |
| T-BOOK-02 | Printed lines | Every card prints execution variants A / B / C and the overnight / intraday attribution. KOSPI VT20, 3 bp, 1997–2026: SR 0.448 / 0.450 / 0.465 (± 0.01). |
| T-BOOK-03 | Leveraged / inverse ETFs | A product whose tick exceeds 10 bp of its price is ineligible. Look-through counts × L in R-07. |

**Source items.** QF1-M1; QF1-M3; QF1-A6; QF1-A7; QF1-A16; QF1-A17; X-EX2-N3; QF4-M2; QF4-A14; QF6-M9; QF6-A21; QF1-M4; QF1-A9; QF1-M2; QF6-M5.

**Evidence.**
- PX2 F4 and EX2 §1(1):
  - 252670 at ₩69 costs 73.9 bp; its 2026 range was ₩62–579 (10–82 bp per side); its floor exceeded 50 bp on 46% of 2026 sessions;
  - KODEX 200 costs 1.6 bp.
- QF1-M1 (`qf1` pilot): US VT15 on futures at 5 bp, ΔMDD +3.6 pp (2×: +3.2), PASS; at 50 bp, +0.2 pp, REJECT.
- X-EX2-N3: the tracking-error table.
- QF1-M4: execution variants; the Jul-2026 benefit came entirely from the intraday leg.
- QF1-A7: turnover by regime.
- QF1-M2 / QF6-M5: the band helps only the stock and US-share books (the Korea stock book's p_ni goes from 0.173 to 0.074; US 50 bp still fails PC-1 at +1.8 pp).
- QF6-M9: leveraged-ETF decay (KODEX Leverage −68.4% in the Jul-2026 crash against −81.6% naive).

### R-27 KRX/NYSE simulated fill model: close-auction fill, random end, limit-lock, LP-exempt iNAV check, bar convention — BUILD NOW · CONVENTION · P2 · M5

**Purpose.** *NEW in v2.0.* "Priced at the close of t" is an idealisation. R-27 names the fill model per venue, so that the simulated order book is realistic and flags the stress-day cases where a close fill was impossible. It never changes a card's gate statistics, which keep the decide-at-the-close convention and print the execution variants of R-26.

**Package / module and functions.**
- `core/engine/orders`: simulated fills only, never a broker path. `fill_model(venue) -> FillModel` and `simulate_fill(order, session) -> Fill | NonFillable(reason)`.
- `core/markets`: session metadata (closing call, random end, LP duties).
- `core/quant/history`: the bar convention and the loader's refusal of bar-derived closes.

**Inputs (PIT fields).**
- The last continuous-session price at the snapshot time (KIS quote with exchange timestamp, once verified; QF1-A25).
- The official close (`value_status = official_close`).
- Daily price limits (R-20 `price_limit`).
- ETF iNAV or the index-implied NAV.
- Bar records with `bar_end`.

**Rule / algorithm.**
1. **KRX daily decision.**
   - Snapshot one minute before the closing call opens, on the last continuous price: 15:19 KST since 2016-08-01 (closing call 15:20–15:30), 14:49 KST before (closing call 14:50–15:00), and the CSAT-day equivalent from the calendar (R-20). The fill is at the **official close**, the closing-call print between 15:30:00 and 15:30:30 under the random end.
   - Fallback: the post-close closing-price session. Its status after 2026-09-14 is UNVERIFIED until it is checked.
   - The simulated book prints the tracking error between the snapshot decision and an official-close decision.
2. **ETF closes.**
   - Each ETF close is flagged `LP_exempt_auction`, because LPs have no quoting duty from 15:20 to 15:30.
   - The close-vs-iNAV residual is computed, and |residual| > 30 bp is flagged.
   - A closing-noise allowance is printed: a median |closing-auction move| of 0.12–0.14%, p95 0.6%, max 2.0–2.3%.
3. **Limit-lock.**
   - A stock at its daily limit at the close is **non-fillable at the close** in the stock book: limit-up for buys, limit-down for sells. The order carries to the next session and is logged.
   - "At its limit" means the official close equals the session's limit price: the previous close × (1 ± `price_limit`), rounded to the tick toward the previous close (R-20 `price_limit`, the effective-dated tick table). A `|r| ≥ limit` test is never used: a tick-rounded limit print is below the nominal limit (SK hynix closed at +29.95%).
   - Example: SK hynix closed at +29.95% on 2026-07-31, the day the vol target re-risked.
   - ETF and futures lines stay fillable unless they are themselves limit-locked.
   - No gross rule follows from limit-locks. The next-morning gap (+0.99%, t 2.0, n 26) is recorded as weak evidence only.
4. **NYSE.** Snapshot at 15:50 ET (the MOC cut-off); fill at the official close (MOC-equivalent). The KIS order type stays UNVERIFIED and is irrelevant to a read-only app.
5. **Futures.**
   - KOSPI200 futures trade until 15:45 KST, so a decision taken at the cash close can execute in the same session.
   - The expiring contract stops at 15:20 KST on its last trading day, so books roll before expiry (R-26).
6. **Bar convention.**
   - Every intraday bar carries `bar_end` (UTC); the closing auction is its own bar; `available_at_utc = bar_end + latency`.
   - **A daily close is never derived from intraday bars.** Only official closes are stored as `official_close` (R-01).
7. **Intraday entries.** Entries inside R-10's windows keep the v1.2 rule: priced at the triggering quote, with its timestamp.

**Config keys** (merge into §7):
```yaml
fill_model:                                          # R-27 (simulated book only)
  KRX: {snapshot: closing_call_start_minus_1min, snapshot_kst_since_2016-08-01: "15:19", fill: official_close, random_end_max_s: 30,
        fallback: post_close_session_UNVERIFIED, limit_price: tick_rounded_toward_prev_close,
        etf: {flag: LP_exempt_auction, inav_residual_flag_bp: 30}, limit_lock: non_fillable_at_close}
  NYSE: {snapshot_et: "15:50", fill: official_close_moc_equivalent}
  KOSPI200_futures: {trades_until_kst: "15:45", expiry_day_stop_kst: "15:20"}
  bars: {stamp: bar_end_utc, closing_auction_bar: separate, available_at: "bar_end + latency", daily_close_from_bars: forbidden}
```

**Outputs and schema fields.**
- `overlay_decision.extras.fill_model`, `decision_price_source ∈ {snapshot_1519, official_close}`, `fill_status ∈ {filled, non_fillable_limit_lock, carried}` and `flags[]` (`LP_exempt_auction`, `inav_residual_gt_30bp`).
- `model_card.macro.printed.fill_tracking_error`.

**Fail-closed behaviour.**
- If no official close exists for the session, there is no fill; the order is carried and an alert raised.
- A bar-derived close is refused by the loader.
- An unverified KIS quote field cannot drive a snapshot. The snapshot then falls back to the official-close decision, and this is labelled.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-FILL-01 | Snapshot vs close | A ≈ 15:19 KST snapshot decision filled at the official close reproduces QF1's tracking error against an official-close decision (0.19% a year on KOSPI; mean \|Δw\| 0.0013) within ±0.05 pp |
| T-FILL-02 | Limit-lock | SK hynix on 2026-07-31 (+29.95%: its close equals the tick-rounded limit price) is non-fillable at the close in a stock book. The KODEX 200 line fills. |
| T-FILL-03 | iNAV check | An ETF close-vs-iNAV residual above 30 bp is flagged |
| T-BAR-01 | Bar convention | No daily close is derived from intraday bars. A fixture whose last hourly KRX bar ends at 15:00 is refused as a close source. |

**Source items.** QF1-M6; QF1-A8; QF1-A14; X-EX2-N5; QF2-A23.

**Evidence.**
- QF1 §4.2 / M6: the snapshot vs the official close gives mean |Δw| 0.0013 and tracking error of 0.19% (KOSPI), 0.16% (KODEX 200) and 0.12% (SPY, 15:30 ET) a year; closing-auction moves as in rule 2.
- EX2 §1(1)–(2): KCGI on LP exemption; SK hynix limit-up; the random end (Eom et al.; the Shinhan notice).
- QF2-A23: the last KRX hourly bar is 14:00–15:00 on 727 of 729 days; last bar vs close: median 13.7 bp, max 205 bp.

### R-28 Trend-axis protective card (US and non-Korean sleeves): monthly SMA10m, 0.5× below trend, FORWARD-SIM — FORWARD-SIM · CARD-P · P1 · M8

**Purpose.** *NEW in v2.0.* The daily vol target misses slow bears. US VT 1990–2007 shows ≈ +0.3 pp; the 2000–02 bear is the case. A monthly trend axis gives slow-bear protection **through the volatility state**:
- below the SMA, next-month |r| is higher (t 4.75) and the mean is not lower (t −0.77);
- the Sharpe gain does not survive data-snooping deflation.

The card therefore claims protection only (Resolution 9).

**Package / module and functions.**
- `core/quant/signals`, the gross overlay: `trend_axis(market, decision_utc) -> Multiplier` with value ∈ {0.5, 1.0} and `exposure_basis = total`.
- `core/quant/backtest`: the card, judged incrementally on the vol-targeted book.
- `core/engine`: a FORWARD-SIM book (the specification book × the trend multiplier). It never reaches `engine_feed` (R-35).

**Inputs (PIT fields).**
- The sleeve index's official month-end closes (`value_status = official_close`, `session_date` = the last session of the month).
- The vol target `vt` of the same market (R-06, R-29).
- Cash at the local short rate (R-22).

**Rule / algorithm.**
1. At each month-end official close t_m: SMA10m(t_m) = the mean of the last 10 month-end closes, including t_m. flag = close(t_m) < SMA10m(t_m).
2. trend(t_m) = 0.5 if flag, else 1.0. It is decided at the close of t_m and holds from t_m + 1 session to the next month-end decision.
3. Composition by `min()` (R-02): composed = vt × min(trend, other overlays, ladder, post_rearm_cap). Outside HALTED, composed ≥ 0.5 × vt.
4. **Claim**, registered verbatim: "slow-bear protection via the volatility state". There is no Sharpe, return or predictability claim.
5. **Judged incrementally** on the vol-targeted book:
   - the overlay-off book is the VT book without the trend axis; for the US instance it is R-29's futures vt book (`CME_micro_ES`, 5 bp, daily vt), so both FORWARD-SIM cards share one book (D5 scope);
   - S = that book × the trend's mean multiplier;
   - PC-1′ to PC-7 run under the frozen package (R-21). On monthly data the horizons are 1 and 6 months.
   - The header also declares a **claim line**: stacked ΔMDD on VT ≥ 3 pp. It is printed with its bootstrap band. If it is missed, the card is capped at INSUFFICIENT DATA ("claim not shown"). It never REJECTs, because drawdown lines never gate a REJECT (R-21).
6. **Tier A via a pooled-onset rule declared in the header before any run.**
   - Onsets are de-clustered at the rule's own lookback (10 months).
   - They are pooled across the declared non-Korean index set. Default: the six non-Korean indices of DLB-T3e (S&P 500, Nikkei 225, HSI, DAX, FTSE 100, TAIEX).
   - The own-market estimate is always printed. An own-market PC-1′ or PC-2 failure vetoes a pooled pass (QF3-M4).
   - The US instance alone has 45 de-clustered onsets on 1927–2026.
7. **Printed lines:**
   - the GJR-null percentile;
   - the snooping haircut over the trend family (94 variants: ΔMDD ≥ 3 pp in all; Sharpe deflated probability 0.43–0.59);
   - the daily and horizon-matched PC-2 (the horizon ratio gates only if adopted under R-21 rule 9).
8. **Scope.**
   - One card per US or other non-Korean equity sleeve. The US is the first instance.
   - **A Korea instance is refused** by rules-store validation; the KOSPI trend state is displayed as context only (R-13). A horizon-matched PC-2 may never be used to rescue KOSPI trend.
   - The 200-day band (BAND200) is a logged trial in the same ledger, never a second card.
9. **Status.**
   - FORWARD-SIM in the specification book until a US or other non-Korean sleeve exists (D5). Then BUILD-AS-INSURANCE on a formal v2 PASS.
   - The forward record is a falsification alarm only (R-25).

**Config keys** (merge into §7):
```yaml
cards:
  R-28_trend_axis:
    rule: {signal: month_end_close_below_sma10m, multiplier_below: 0.5, multiplier_above: 1.0,
           decided: month_end_close, applies: next_month, composition: min, exposure_basis: total}
    claim: "slow-bear protection via the volatility state"
    judged: {incremental_on: vol_targeted_book, comparator: S_of_VT_book, claim_line_stacked_dMDD_min_pp: 3.0,
             claim_line_failure: cap_INSUFFICIENT}
    pooling: {decluster_gap_months: 10, indices: [SPX, N225, HSI, DAX, FTSE100, TAIEX], own_market_veto: true,
              declared_before_any_run: true}
    markets_allowed: [US, other_non_korean]
    markets_refused: [KR]
    logged_trials_same_ledger: [BAND200]
    status: FORWARD_SIM
    us_sleeve: {ref: sleeves.US.line}                # D5 (Quick start); FORWARD-SIM while none
    instrument_book: CME_micro_ES                    # US instance: incremental on R-29's futures vt book
    rebalance: monthly
    no_trade_band: 0.0
    notional_nav: {ref: sleeves.US.notional_nav}
    fill_model: NYSE_moc
```

**Outputs and schema fields.**
- `macro_state.forward_sim.R28_below_sma10m` (display) and `overlay_decision.forward_sim[]` with `rule_id: R-28` while the card is FORWARD-SIM (`multipliers[]` with `exposure_basis: total` once promoted), each with `card: {class: CARD-P, verdict, disposition, displayed_as}`.
- `model_card.macro.claim_lines` (header: the declared claim line) and `claim_line_results = {stacked_dMDD, band, pass}`, `pooling = {rule, n_onsets_own, n_onsets_pooled}`, `gjr_null_pct`, `snooping = {n_variants, share_dMDD_ge_3pp, deflated_prob_sr}`.

**Fail-closed behaviour.**
- A missing month-end official close leaves the multiplier unchanged and fails closed (R-19).
- A Korea instance, a header without a pooling rule, or a header with a Sharpe claim is refused.
- The FORWARD-SIM book is never read by the recommended book (I-03).

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-TREND-01 | Header | Declares monthly SMA10m, gross 0.5× below trend, `min()` composition, the claim "slow-bear protection via the volatility state" and a pooled-onset rule, all before the run. A header missing any of them is refused. |
| T-TREND-02 | French monthly 1927–2026 fixture; daily US VT15 fixture 1991–2026 | Stacked ΔMDD on VT ≥ 3 pp (+14.9 pp on the daily US VT15 book, 1991–2026: PX2's re-run of QF5's card). On the French monthly 1927–2026 fixture, DLB-T3a reproduced at Level-1 tolerance: ΔSR +0.083 at 5 bp and +0.059 at 50 bp; ΔMDD +15.9 pp; tail 0.78; 9 of 10 episodes; 45 de-clustered onsets; PASS at 5 and 50 bp under the v1.2 checks. The GJR-null percentile prints 87th (± 5). The v2 verdict is computed blind and printed; a difference from PASS is reported as a disclosed flip (R-21), never tuned. |
| T-TREND-03 | Korea refused | Registering the card for KR raises. The KOSPI trend state appears only in `context_log`. |
| T-TREND-04 | FORWARD-SIM isolation | Until a US sleeve exists (D5), the R-28 multiplier appears only in its FORWARD-SIM book and never in `engine_feed` |

**Source items.** QF5-M2; QF5-A10; X-PX2-N1; QF5-A8.

**Evidence.**
- Resolution 9.
- DLB-T3a: US 1927–2026 at 5 bp, ΔSR +0.083 [0.019, 0.134], p_ni 0.000, ΔMDD +15.9 pp, tail 0.78, 9 of 10, years 68%, 73 / 45 onsets, plateau 1.0.
- DLB-T3c: PASS for every start up to 1960; from 1970 INSUFFICIENT on onsets, with ΔMDD still +12–16 pp.
- DLB-T3e: ΔMDD > 0 in all 7 indices.
- DLB-T3f: 94 of 94 variants keep ΔMDD ≥ 3 pp (median +16.4); deflated Sharpe probability 0.59 at N̂ 30.7 and 0.43 at N 94.
- PX2 (`qx_px2_01`):
  - the mechanism (|r| t 4.75; r t −0.77);
  - GJR null: median +7.0 pp, observed at the 87th percentile;
  - White RC p 0.199, SPA p 0.228;
  - stacked on US VT15 +14.9 pp; on KOSPI VT20 +2.2 pp.
- QF5-M5: KOSPI daily tail ratio 0.929 (0.853 at 21 days); US 0.832 → 0.767.

### R-29 MACRO-R06-US-FUT: US index-futures vol target (new card), FORWARD-SIM pending a 1926+ settling run — FORWARD-SIM · CARD-P · P1 · M8

**Purpose.** *NEW in v2.0.* The registered US card (US shares via KIS at 50 bp, daily) is a REJECT, and that REJECT is a fact about the instrument, not about vol targeting. A beta scalar belongs on index futures. R-29 registers that line as a **new card**, one more trial in the R-06 family ledger, never a revision or a rescue of the 50 bp card (DNB #23).

The card's 1990–2026 PASS is knife-edge, so a 1926+ daily-history run decides it, not forward months (Resolution 2).

**Package / module and functions.**
- `core/quant/risk.market_vol_target`, US instance, futures book.
- `core/quant/backtest`: the card and the settling run (`settling_run(card, data='FF_daily_1926', starts='decade')`).
- `core/engine`: a FORWARD-SIM book on the index (no US sleeve exists), with integer-contract sizing when a notional is declared.

**Inputs (PIT fields).**
- US official closes (`value_status = official_close`). The NYSE decision instant is `close_print_bound_utc('US', t)`: the scheduled close (20:00Z in EDT, 21:00Z in EST; 17:00Z / 18:00Z on early closes) + 30 s (R-20).
- US RF cash (R-22).
- Micro ES contract specifications and the roll calendar (R-26).
- For the settling run: French daily Mkt-RF and RF, 1926-07-01 → 2026-08-31, frozen with an md5 once acquired. The DLA fetch failed with HTTP 403 (DLA-U6), so the acquisition is a data task.

**Rule / algorithm.**
1. vt_US(t) = min(1.0, 0.15 ⁄ σ̂_SMA20(t)), daily, decided at the US close of t and earning from t+1. Cap 1.0, no floor. The estimator is SMA20, fixed before the run; R-30's challenger can enter only through a counted revision.
2. **Book:** `CME_micro_ES` at 5 bp per side (futures cost class); `rebalance: daily`; `no_trade_band: 0`; `notional_nav` declared.
   - Live use requires one contract (≈ ₩52m) to be ≤ 5% of the notional (R-26), i.e. a sleeve of ≈ ₩1bn or more.
   - Contracts = round_half_away_from_zero(vt × notional_nav_KRW ⁄ (multiplier_USD × index level × USDKRW_t)), with USDKRW_t the book's `nav_fx` series at the decision (the latest `USDKRW_1530_SNAPSHOT` usable then; `ECOS_1530_CLOSE` for history), recorded in `overlay_decision.extras`.
   - Roll before expiry on a fixed calendar, with a roll-cost line.
3. **Episodes:** objective ≥ 15% S&P episodes (R-22).
4. **Settling run.** On French daily Mkt-RF 1926-07 → 2026-08 at 5 bp, the card returns PASS only if both hold:
   - PC-1′ holds at 1× **and** 2× (both legs, points > 0, p_h × f ≤ 0.10; R-21);
   - the card PASSes at ≥ 80% of the 10 decade-spaced starts (≥ 8; R-22's frozen `decade_spaced` shape): the declared start (first close + 20-session warm-up), then the first session of January 1930, 1940, … 2010. R-22's other floor clauses apply: no REJECT at any of these starts and no REJECT in either calendar-midpoint half.
5. **Promotion to BUILD-AS-INSURANCE** requires all of:
   - (1) a US sleeve exists with a declared notional at which one Micro ES is ≤ ~5% of the sleeve (≈ ₩1bn), or the owner declares another executable line (D5: a KRX-listed S&P ETF line with FX and NAV lag modelled);
   - (2) the settling run of rule 4 passes;
   - (3) the card's v2 verdict on its full settling-run span (the declared start of the 1926+ file to 2026-08), under the blind package with objective ≥ 15% S&P episodes, is PASS, with no REJECT at any decade-spaced start (the R-22 stability floor). The settling-run conditions of rule 4 are necessary, not sufficient; the card's recorded verdict is the full-span verdict after the caps.
6. **Logged trials, never rescues:** the monthly 50 bp and banded 50 bp variants (R-23 ledger).
7. **Until promotion:** FORWARD-SIM in the specification book; a falsification alarm only (R-25).

**Config keys** (merge into §7):
```yaml
cards:
  R-29_US_FUT:
    card_id: MACRO-R06-US-FUT
    family: R-06                                     # one new trial in the R-06 ledger
    rule: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, floor: none, rebalance: daily, exposure_basis: total}
    instrument_book: CME_micro_ES
    cost_class: futures                              # 5 bp per side, read from the gate
    no_trade_band: 0.0
    notional_nav: {ref: sleeves.US.notional_nav}   # live only if one contract <= 5% of it (R-26 granularity floor, checked at the header commit)   # ~KRW 1bn; never declared on the card
    nav_fx: {series: USDKRW_1530_SNAPSHOT, history: ECOS_1530_CLOSE}
    episodes: {theta: 0.15}
    settling_run: {data: FF_daily_MktRF_1926-07_to_2026-08, cost_bp: 5, pc1_prime_at: [1x, 2x],
                   starts: decade_spaced, pass_share_min: from_band_shape, no_reject_at_any_start: true,
                   no_reject_in_midpoint_halves: true, full_span_must_pass: true}
    promotion: {requires: [us_sleeve_or_owner_line, settling_run_pass, v2_package_pass]}
    us_sleeve_and_line: {ref: sleeves.US.line}       # D5 (Quick start): CME_micro_ES, KRX_listed_SP500_ETF or none
    logged_trials: [monthly_50bp, band_0p10_50bp]
    status: FORWARD_SIM
```

**Outputs and schema fields.**
- `model_card.macro` with `card_id: MACRO-R06-US-FUT`, `instrument_book`, `notional_nav`, `contracts_path`, `settling_run = {span, verdict, pc1_prime_1x, pc1_prime_2x, starts[], n_pass, n_starts, n_reject, midpoint_halves}` and `start_band_results`.
- `overlay_decision.forward_sim[]` with `rule_id: R-29`.

**Fail-closed behaviour.**
- The settling run cannot run without the frozen 1926 fixture. Its absence keeps the card FORWARD-SIM; it never falls back to the 1990 file.
- A header without `notional_nav` is refused.
- A live book below the granularity floor is refused (R-26).
- The FORWARD-SIM multiplier never reaches `engine_feed` (R-35).

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-USFUT-01 | Registration | Registered once as a new card (one ledger trial), with a Micro ES 5 bp book and a notional field. A second registration under the same family with a 50 bp book raises (DNB #23). |
| T-USFUT-02 | Settling-run logic | On the 1926-07 → 2026-08 fixture the run returns PASS only if PC-1′ holds at 1× and 2× and the card passes at ≥ 80% of decade-spaced starts. A synthetic 70% share returns no PASS, and so does a synthetic 9-of-10 result with one REJECT start. |
| T-USFUT-03 | Promotion guard | The card stays FORWARD-SIM unless the settling run passes **and** a US sleeve with notional ≥ ~₩1bn (or a D5 line) exists |
| T-USFUT-04 | Logged variants | The monthly and banded 50 bp variants appear as ledger trials of the R-06 family and never as a revision of this card |
| T-USFUT-05 | 1990–2026 reproduction (fixture U1, v1.2 checks) | DLA-U2 within Level-1 tolerance: ΔMDD +3.6 pp (2×: +3.2), p_ni 0.002, 6 of 11 episodes (max 0.46), plateau 0.875; the 44 quarterly-start verdicts match G-US-F08 (11 PASS / 9 REVISE / 24 REJECT), except that a start whose deciding statistic lies within tolerance of its threshold is asserted as a class, and the counts as the implied ranges |

**Source items.** QF1-A1; QF4-A2; QF5-A23; QF6-A8; QF3-A4.

**Evidence.**
- Resolution 2.
- DLA-U2: the knife edge.
  - PC-1 margin +0.6 pp (+0.2 at 2×);
  - every start from 1994-11 to 2000-08 is a REJECT;
  - 1995+ is a REJECT (+2.9 pp); 1990–2007 shows +0.3 pp.
- DLA-U5 at 5 bp: ΔES99 z 2.38; ΔES95 (21-day) z 2.05.
- DLB-T1h: on 1995–2026 at 5 bp the PC-1 verdict flips with the estimator (SMA20 +2.5 pp REJECT; GARCH +4.9, log-HAR +4.8 and COMB +3.9 pp PASS).
- DLA-U3 / U4: monthly rebalancing is INSUFFICIENT (GFC share 0.56–0.67); the 0.10 band at 50 bp is a REJECT (+1.8 pp).
- X-EX2-N3: Micro ES ≈ ₩52m; tracking error 7.5% a year at ₩0.1bn.
- DLA-U6: the 1926 fetch failed (HTTP 403).

### R-30 Volatility-estimator selection gate and forecast-evaluation harness; COMB registered challenger — BUILD NOW · GOVERNANCE · P1 · M3

**Purpose.** *NEW in v2.0.* B5 calibration cannot choose an estimator: it passes 7 of 9 KOSPI forecasters and 8–9 of 9 US ones. SMA20 is outside the 90% QLIKE model confidence set at 1, 5 and 21 days in both markets (p ≤ 0.0005), though inside the MSE set, and its KOSPI VaR breaches cluster.

R-30 builds a forecast-evaluation harness and a staged, counted, fail-closed selection gate (Resolution 3).
- **SMA20 stays the acting sizing estimator and the displayed baseline** (2–1). The text "validated default" is struck.
- **COMB = ½(GJR-t + log-HAR-range)** is the registered challenger, for ETF and futures books only.
- An estimator choice is a tracking and drawdown decision, never a Sharpe claim.

**Package / module and functions.**
- `core/quant/garch`, the estimators:
  - `sma(window)`, `ewma(lam)`;
  - `garch_t()`, `gjr_t()`: GJR-GARCH(1,1)-t with constant mean on expanding windows of ≥ 10 years, refit every 21 origins;
  - `range_proxy(market)`, `log_har_range()`, `comb()`.
- `core/quant/backtest`, the forecast-evaluation harness, **proposed**:
  - `loss_registry` (QLIKE, MSE, tick loss);
  - `dm_test` (HAC with lags max(10, 2h), Harvey–Leybourne–Newbold factor), `cw_test`, `gw_test`;
  - `mcs(losses, stat='T_max', block=max(10, 2h), B=2000, seed=11)`;
  - `kupiec`, `christoffersen_cc`, `es_z2` (Acerbi–Székely, simulated critical values), `fan_pit(h)`, `reliability_table`;
  - `estimator_gate(card) -> GateResult`.
- `macro_state.vol` fields (§6.1).

**Inputs (PIT fields).**
- Daily OHLC with `value_status` and the open-quality and range-quality flags (QF6-M11); official closes.
- The target y[t, h] = Σ_{j=1..h} r²_{t+j}, with forecasts made at the close of t from data through t.
- The card's declared instrument book and cost (R-26).

**Rule / algorithm.**
1. **Registry.** Every forecaster and every "X predicts Y" claim is registered with its target, horizon, loss, benchmark and test (QF7-M2). The selection loss is pre-declared as QLIKE.
2. **Estimators, as defined in DLB §1:**
   - **SMA20** = h × the sample variance of the last 20 returns;
   - **EWMA(λ)**, RiskMetrics recursion;
   - **GARCH-t** and **GJR-t**, constrained to α + β + γ⁄2 ≤ 0.9999;
   - **log-HAR-range**, a direct h-step OLS of log(mean p over the next h) on [1, log p_t, log mean p_{t−4..t}, log mean p_{t−21..t}], rescaled to r² units by the expanding ratio Σr² ⁄ Σp. The range proxy p is overnight² + Garman–Klass for KOSPI and Parkinson for the US;
   - **COMB** = ½(GJR-t + log-HAR-range), in variance units.
3. **Stage 1 (calibration; necessary for a challenger)**, at the **21-day sizing horizon**:
   - FHS VaR exceedance at h = 21, the 21-day fan PIT and Christoffersen conditional coverage;
   - printed: the 1-day Kupiec and Christoffersen CC at 95% and 99%, and the ES 97.5% Z2;
   - a 1-day VaR is displayed only from a model that passes the 1-day B5.
4. **Stage 2 (screen):** membership of the 90% QLIKE MCS at h = 21. The MSE MCS is printed.
5. **Stage 3 (choice).** Each survivor's sized book is built at the card's declared instrument book and cost.
   - Eligible survivors: ΔSR vs the SMA20 book non-inferior at δ = 0.10 (R-24 bootstrap), ΔMDD vs SMA20 ≥ 0 and PC-2 ≤ 0.90.
   - The **lowest vol-of-vol** wins. Vol-of-vol is the SD of the book's rolling 63-session annualised realised vol.
   - Overlapping bootstrap CIs are **ties**, and a tie goes to the simplest surviving model, in the order SMA20 < EWMA(0.94) < EWMA(0.97) < GARCH-t < GJR-t < log-HAR-range < COMB.
6. **Switching rule.** A challenger replaces SMA20 on a card only through a **counted card revision** (an R-23 ledger trial) that passes Stages 1–3 **and** the full v2 CARD-P.
   - Never on the 35 bp stock book (log-HAR costs −0.063 Sharpe there, COMB −0.030).
   - Never on the registered R-06 KR card, which keeps SMA20 as its primary configuration.
7. **Fail-closed fallback** to SMA20 for the decision, logged:
   - a GJR fit outside its bounds (ω > 0, α ≥ 0, α + γ ≥ 0, β ≥ 0, α + β + γ⁄2 ≤ 0.9999, ν ∈ (2, 100], converged);
   - the declared range proxy's quality flag tripping: opens equal to the prior close on > 5% of the trailing 252 sessions for Garman–Klass and the overnight leg; high = low on > 5% for Parkinson (thresholds: default, judgment).

   Forecasts are never blended with SMA20 as a partial fallback.
8. **The incumbent's calibration status** feeds R-21's cap. SMA20 must keep passing B5: 5% FHS VaR exceedance within ±2 binomial SE over ≥ 200 origins, and PIT χ² p ≥ 0.01 (the v1.2 rule). Its Stage-1 lines are printed as disclosure ("its KOSPI VaR breaches cluster"). A challenger must pass Stage 1. A failure caps the card at REVISE.

**Config keys** (merge into §7 under `vol_target`):
```yaml
vol_target:
  estimator_gate:                                    # R-30 (replaces v1.2 B5-only selection)
    acting_default: sma20                            # also the displayed baseline
    challenger: {name: comb, definition: "0.5*(gjr_t + log_har_range)", books_allowed: [KRX_ETF_line, KOSPI200_futures,
                 mini_KOSPI200_futures, CME_micro_ES], books_refused: [KRX_stock_book]}
    fit: {window: expanding, min_years: 10, refit_every_origins: 21}
    range_proxy: {KR: overnight_sq_plus_garman_klass, US: parkinson}
    stage1: {horizon_days: 21, tests: [fhs_var_exceedance_h21, fan_pit_h21, christoffersen_cc], printed: [kupiec_1d, cc_1d_95_99, es975_z2]}
    stage2: {loss: qlike, mcs_level: 0.90, stat: T_max, block: "max(10, 2h)", resamples: 2000, seed: 11, mse_mcs: printed}
    stage3: {objective: min_vol_of_vol_rolling63, eligibility: [dSR_noninferior_vs_sma20_delta_0p10, dMDD_vs_sma20_ge_0, pc2_le_0p90],
             ties: overlapping_bootstrap_ci, tie_break: simplest_surviving,
             complexity_order: [sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb]}
    switch: {counted_revision: true, full_v2_card_p: true}
    fallback_to_sma20: {gjr_bounds: {persistence_max: 0.9999, nu: [2, 100]}, open_quality_max_share: 0.05,
                        flat_range_max_share: 0.05, window_sessions: 252}       # thresholds: default, judgment
    incumbent_calibration: {name: B5, var_level: 0.05, band: "+-2 binomial SE", min_origins: 200, pit: chi2_10_bins, pit_p_min: 0.01}
```

**Outputs and schema fields** (§6.1, §6.5).
- `macro_state.vol.estimator ∈ {sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb}`.
- `macro_state.vol.estimator_gate = {status, stage1, stage2_mcs_p, stage3_rank, fallback_used, reason}`, with `status ∈ {registered_default, challenger_selected, fallback_to_sma20, NOT_RUN}`.
- `model_card.macro.forecast_eval = {qlike_mcs_p[h], mse_mcs_p[h], christoffersen_p, es_z2, fan_pit_p, vol_of_vol, dMDD_vs_sma20, dSR_vs_sma20}`.

**Fail-closed behaviour.**
- Any failure in the challenger path (fit, proxy, data) → SMA20 for that decision, logged. Never a stale challenger forecast.
- An estimator switch without a counted revision is refused.
- COMB or log-HAR on a stock book is refused.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-EST-01 | DLB-T1a reproduction (KOSPI OOS 2001–26; US OOS 1995–2026) | SMA20 is outside the 90% QLIKE MCS at h 1, 5 and 21 (MCS p ≤ 0.0005). COMB is inside the 90% MCS in all six cells. SMA20's MSE MCS p printed: KOSPI 0.036 / 0.066 / 0.141; US 0.112 / 0.112 / 0.290. |
| T-EST-02 | Stage-1 report | Contains the 21-day FHS exceedance, the 21-day fan PIT and Christoffersen CC. The 1-day lines show KOSPI 2001–26 Christoffersen independence p < 0.0001 for SMA20, 0.17 for COMB and 0.16 for log-HAR-range. |
| T-EST-03 | COMB sized book (KOSPI 2001–26, 3 bp, target 20%, cap 1) | Vol-of-vol −22% ± 2 pp vs SMA20 (0.0347 vs 0.0446); ΔMDD +2.8 pp; ΔSR −0.000 with 90% CI [−0.042, +0.039] |
| T-EST-04 | Fallback | A GJR fit with α + β + γ⁄2 > 0.9999 (or non-convergence), or a tripped OHLC quality flag, makes σ̂ come from SMA20 for that decision, logged. No blend. |
| T-EST-05 | Counted switch | An estimator change without a new card revision and ledger row is refused. COMB declared on a `KRX_stock_book` card is refused. |

**Source items.** QF6-M1; QF6-M2; QF6-A1; QF6-A2; QF6-A3; QF6-A4; QF6-A20; QF7-M2; QF7-A22; X-PX1-N6; X-PX1-N4; QF3-A23; QF6-A25.

**Evidence.**
- Resolution 3.
- DLB §1:
  - QLIKE × SMA20 for COMB: 0.944 / 0.809 / 0.691 (KOSPI) and 0.916 / 0.723 / 0.642 (US);
  - B5 passes 7 of 9 (KOSPI) and 8–9 of 9 (US) models;
  - the sized books table; at 35 bp, log-HAR −0.063 (CI excludes 0) and COMB −0.030;
  - the gains halve on 2016–26.
- DLB-T1d: the 1-day HAR failure came from QF6's log-r² design; the range target gives 0.947 / 0.921 × SMA20; log-HAR-range narrowly misses the KOSPI 1-day B5 (5.58% vs 5.56%).
- DLA bridge: an EWMA(0.94) switch would turn the Korea card INSUFFICIENT on PC-4 (0.51) under §8.6, so an estimator change can flip a knife edge.
- QF6-A25: the app's own GJR / GARCH-t SPY B5 study is UNVERIFIED until `docs/vol_backtest.py` and its seed are published.

### R-31 Drawdown step-down card: −8% and −12% steps, time-boxed at 21 sessions, specification book until PASS — SPECIFICATION BOOK · CARD-P · P1 · M7

**Purpose.** *NEW in v2.0.* With a re-arm, the ladder's steps bind on 23–56% of days, and 62–66% of those days fall outside bear markets. They become a de facto sizing rule that no card gates (red line E3).

v2 time-boxes each step at 21 sessions. Wherever the steps bind on more than 10% of days on the declared book, they act **only in the specification book** until this CARD-P passes (Resolution 6).

The −15% hard stop is not part of this card. It stays an INVARIANT governance event in R-07, with its re-arm and its level under owner decision D2, and it makes no protection claim.

**Package / module and functions.**
- `core/quant/risk.drawdown_ladder` → `LadderState{hwm_hard, ref_step, step_mult, dwell_left, block_new_entries, halted, rearm_not_before, post_rearm_left, binding_share}` (§3.5).
- `core/engine/evaluator`: the new-entry block at the −12% step.
- `core/quant/backtest`: the step-down card and the binding share.

**Inputs (PIT fields).** The whole simulated-book NAV after the close of t (built from official closes); R-07's state (HALTED, re-arm and its 10-session 0.5× cooling-off); the book's other multipliers.

**Rule / algorithm.** Levels are in % of **whole-book NAV**. Multipliers are totals, never cumulative. Composition is by `min()`.
```python
# at the decision at the close of t, setting the multiplier for t+1 (the hard-stop part is R-07's, shown for the references)
hwm_hard = max(hwm_hard, nav_t)                       # resets only at re-arm (R-07)
if dwell_left == 0:
    ref_step = max(ref_step, nav_t)                   # running peak since the last reset
dd_hard = nav_t / hwm_hard - 1
dd_step = nav_t / ref_step - 1
if book.halted:                                       # not evaluated while HALTED; references frozen until re-arm (R-07)
    pass
elif dd_hard <= hard_stop_level:                      # default -0.15 (D2) -> R-07 HALTED (RISK), review event; halt() is idempotent
    halt(); clear_steps()
elif dwell_left > 0:                                  # inside a 21-session time box
    step_mult = 0.5
    dwell_left -= 1
    if dd_step <= -0.12:
        block_new_entries = True                      # escalation adds the block; sizing and clock unchanged
    if dwell_left == 0:
        ref_step = nav_t                              # step spent: its reference resets; the hard-stop reference does not
elif dd_step <= -0.12:
    step_mult, block_new_entries, dwell_left = 0.5, True, DWELL - 1     # DWELL = 21 sessions incl. the first
elif dd_step <= -0.08:
    step_mult, block_new_entries, dwell_left = 0.5, False, DWELL - 1
else:
    step_mult, block_new_entries = 1.0, False      # the block, like the 0.5x, covers the session after the last dwell decision
composed = vt * min(overlay_1, ..., overlay_k, step_mult if steps_act_in_book else 1.0, post_rearm_cap)
```
- At re-arm (R-07), both references reset to the NAV at re-arm.
- **Binding share** = n_bind ⁄ n_sessions, the share of sessions with `step_mult < 1` on the declared book over its declared history. It is printed on every card. For the recommended book it is computed per market book on the book's current composition without the steps (the invariants plus the PASS factors, each market on its declared instrument book; whole-book NAV), over the full declared history, at the R-31 header commit. It is frozen with that header and recomputed only through a new counted R-31 revision when the recommended book's composition changes (a card promotion or demotion, a D1 or D2 ruling), logged as a governance event. It is never computed on a trailing window, so the steps cannot flap in and out of the recommended book.
  - ≤ 10%: the steps act as part of the R-07 invariant in the recommended book, with disposition `INVARIANT_STEP` (R-35, §6.2).
  - > 10%: they act only in the specification book until this card PASSes. The Executives' "every step must earn a CARD-P" is recorded as dissent.
- **Card.** CARD-P, judged incrementally on the declared book with the hard stop and every other factor, minus the steps. S = that book × the steps' mean multiplier. The checks are the frozen v2 package (R-21). Claim: "protection in persistent drawdowns; time-boxed; no Sharpe claim".
- **Mechanism check (printed).** The Kaminski–Lo persistence condition: after an activation, the next 21 sessions returned −0.57% vs +0.98% unconditional on KOSPI, and +0.57% vs +0.78% in the US.
- Levels stay in % of NAV (2–1). The Executives' σ-scaled steps are recorded as dissent.

**Config keys** (merged into §7 at `cards.R-31_step_down`; `risk_layer.drawdown.steps` points to it):
```yaml
cards:
  R-31_step_down:
    steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}]   # totals, non-cumulative
    dwell_sessions: 21
    step_reference: running_peak_since_last_reset    # resets at dwell end and at re-arm
    hard_stop_reference_resets_at_dwell_end: false   # R-07 reference; resets only at re-arm
    composition: min
    denominator: whole_book_nav
    binding_share_threshold: 0.10                    # > 0.10 -> specification book until PASS
    binding_share: {book: recommended_without_steps, span: declared_history, computed_at: [header_commit, composition_change],
                    window: full_never_trailing, compare: "n_bind / n_sessions > 0.10", disposition_if_le: INVARIANT_STEP}
    judged: {incremental_on: declared_book_without_steps, comparator: S}
    claim: "protection in persistent drawdowns; time-boxed; no Sharpe claim"
    hard_stop_level: {ref: risk_layer.drawdown.hard_stop.level}   # D2 (Quick start); never a literal copy (T-OWNER-01)
    status: SPECIFICATION_BOOK
```

**Outputs and schema fields.**
- `macro_state.flags.ladder_step ∈ {none, step_-8, step_-12, hard_stop_-15}`, `flags.ladder_dwell_left` and `flags.block_new_entries`; `hwm_hard` and `ref_step` per book in `macro_state.runtime[]` (§6.1).
- `overlay_decision.multipliers[]` with `rule_id: R-31` and its card verdict.
- `model_card.macro.printed = {binding_share, n_halts, persistence_check}`.

**Fail-closed behaviour.**
- If the whole-book NAV is unavailable, the step state is held and an alert raised. The hard stop (R-07) stays armed.
- A ladder path composed by product raises (R-02).
- With a binding share > 10% and no PASS, the recommended-book builder refuses the step multiplier (I-03).

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-STEP-01 | References | On a synthetic NAV path, a −9% drawdown gives 0.5× for exactly 21 sessions, and a −13% drawdown gives 0.5× and the new-entry block for exactly 21 sessions each. Then `ref_step` resets to the NAV and `hwm_hard` does not. A later −15% from `hwm_hard` triggers HALTED even though `dd_step` is shallower. |
| T-STEP-02 | Binding share (KOSPI VT20, 3 bp, 1997-04-15 → 2026-10-02; US VT15, 5 bp, 1990-04-02 → 2026-09-30) | ≈ 19% and ≈ 10% of days (± 3 pp). The fixtures come from EX1 L5, whose single shared reference R-31 separates, hence the tolerance. Printed on the card. |
| T-STEP-03 | Sharpe effect | ΔSR vs the same book without steps is printed and matches the R-31 reference run (§9.4: to be computed with the separate `hwm_hard` / `ref_step` references; EX1 L5's +0.005 / +0.006 used one shared reference and is informative) |
| T-STEP-04 | Book placement | KOSPI binding share > 10% and no PASS: the step multiplier appears only in the specification book. The recommended book carries the hard stop (R-07) only. US: moot while D5 keeps no US sleeve; once it enables one, placement uses the exact share computed on the declared book, never T-STEP-02's ≈ 10% ± 3 pp fixture, which straddles the threshold. |
| T-STEP-05 | Idempotent HALT | NAV flat at −16% for 30 sessions after a breach at the close of t sets `rearm_not_before` once (t + 10 sessions). The book re-arms automatically at the close of t+10, re-enters at t+11 under the 0.5 post-re-arm cap (weights decided at t+10 … t+19), and a second `halt()` while HALTED changes nothing (no later re-arm date, no reference reset). |

**Source items.** QF4-M3; QF4-A4; X-EX1-N2.

**Evidence.**
- Resolution 6.
- EX1 §2(3) (`QX_EX1_ladder.csv`): L2 binds 53% / 29%; L5 19% / 10% with ΔSR +0.005 / +0.006, ΔMDD +4.8 / +1.5 pp and 3 / 0 HALTs; L6 6% / 4%.
- DLA-D1 / D3: the literal ladder halts forever (714–907 cycles); QF4's fix binds 52% / 29%.
- QF4 §5.3: the Kaminski–Lo diagnostic.
- Executives' check C2 (for D2): a −15% hard stop on KOSPI VT20 fires 24 times and deepens MDD from −45.3% to −56.4%; at −30%, 6 HALTs and MDD −44.8%.
- EX1 stack: product composition sits at ≤ 0.25× on 31.0% of KOSPI days, against 11.2% under `min()`.

### R-32 Card header and artifact schemas v2 (model_card.macro, macro_state, context_log) — BUILD NOW · GOVERNANCE · P0 · M0

**Rule.** *CHANGED.* Every model card and every artifact validates against the v2 JSON Schemas, which are materialised in **§6.1 (`macro_state`), §6.4 (`context_log`) and §6.5 (`model_card.macro`)**, with `schema_version` "2.0".
- `model_card.macro` validates only with these fields: `family_id`, `ledger_hash_at_registration` (header) and `ledger_hash_at_run` (result), `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `V_null`, `power {se_hac, se_blk250, se_plateau, mde80, …}`, `timing_profile` (result), `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`, `cash_convention`, `start_band` (acting long-sample cards), `episode_rule_version`, the stability lines (`start_band_results`, `midpoint_halves_results`), `gjr_null_pct`, and the reproducibility fields `git_hash`, `config_hash`, `data_snapshot_id` and `knowledge_utc`.
- `macro_state` inputs carry `value_status`, `session_date` and every common provenance field (§6 conventions).
- `context_log` items carry `vintage` and `retrieved_at_utc`.

The header semantics, including `gate_package_version` and its md5, are in §8.4. Two card schemas exist: `model_card_header.macro` (the §8.4 header fields, validated by `validate_card_header` at commit, before any run) and `model_card.macro` = header ∪ results (validated when the card is written). A card that fails validation is not written. Where a rule's "Outputs and schema fields" list and §6 differ, the rule governs and §6 is fixed, as §7 states for config; every field a rule writes is declared in §6 (C-7).

**Validation-failure scope (C-1).** A `macro_state` or `overlay_decision` artifact whose acting fields (classified exhaustively below) fail validation trips the `bounds_ok` gate and HALTs (OPS) the books it describes; it is written to `<artifact_dir>/quarantine/` with its errors (§3.9). A failure confined to display or context fields (gap tags, annotations, context items, refusal and FORWARD-SIM blocks, `owner_decisions`, `alerts`, the `vol` display labels) writes the artifact with `extras.validation_errors`, raises an alert and never HALTs. **Field classes (exhaustive; R2-C4).** The display properties are: in `macro_state`, `owner_decisions`, `alerts`, `annotations`, `refusal_books`, `forward_sim` and the `flags` that set no exposure (`gap_sessions`, `kr_open_gap_event`, `var_display_scale`, and the hedge-state flags `hedge_credit_off`, `hedge_failure`, `classic_risk_off`, `fx_hedge_credit`, `hedge_reasons` and `hedge_stale_inputs`, which never HALT, R-09); in `macro_state.vol`, `display_label_rel`, `display_label_abs`, `label_method_rel`, `label_method_abs` and `alt_sigma_logged`; in `overlay_decision`, `reasons`, `refusal` and `forward_sim`; in both, the `inputs` entries whose role is not `acting_exposure`. Every other property is acting: among them the `acting_exposure` entries of `inputs`, the rest of `vol`, `concentration`, `runtime`, `lag_audit`, `fail_closed`, the ladder and hard-stop flags, and every weight, multiplier and composition field. A property added later is acting until it is classified here, so an unclassified field fails closed. R-26's per-instrument weights (`extras.w_target`, `extras.w_held`) are checked by `bounds_ok` in code, in [0, 1], because `extras` is never schema-validated. A `context_log`, `event_calendar` or `model_card` artifact that fails validation is refused: it is not written to the artifact directory, it is written to `<artifact_dir>/quarantine/` with its errors (so the audit trail and replays keep it), an alert is raised, and it never HALTs (P9, P18).

**Acceptance.** T-SCHEMA-01: every example in this spec validates against its §6 schema (a `<…>` placeholder stands for a value of the declared type and is replaced by a typed sample). T-SCHEMA-02: as above, with each listed field removed in turn → refused. T-SCHEMA-03: one synthetic artifact or card built from each rule's Outputs list validates. T-SCOPE-01 (f): a `context_log` schema failure HALTs nothing; I-06c: an acting-field schema error HALTs.

**Source items.** QF3-A1; QF3-M2; QF4-M2; X-EX2-N3; QF2-A2; QF7-A24; QF2-M2. **Evidence:** Resolutions 4, 5, 11; QCE-095.

### R-33 DO-NOT-BUILD list v2 — BUILD NOW · GOVERNANCE · P1 · M0

**Rule.** *CHANGED.* The DO-NOT-BUILD list, **materialised in §10**, is enforced by rules-store validation, not by convention. Each refused shape is a predicate over the rule-object schema of §7.1.
- **Item 11 is split.** ML vol-state classifiers stay prohibited; the negative result is archived (QF3-M6). Range-based HAR is admitted to R-30's race.
- **New entries, refused by validation:**
  - (a) a regime-model state (jump model, Markov switching, GMM label, change-point "regime") acting on exposure or **displayed** on any page;
  - (b) a Mondrian conformal label layer;
  - (c) a maintained ML challenger pipeline;
  - (d) max(SMA20, implied) sizing (ΔSR −0.166 at 50 bp);
  - (e) product-composed de-risk stacks;
  - (f) a venue switch after results;
  - (g) a stock book used as a market-gross scalar.
- Every entry carries a label: harm, null or inconclusive (QF3-A17).
- The σ̂ display labels of R-06 are volatility labels, not regime states, and stay. A BOCPD probability may be written only to the R-18 research log, never displayed.

**Acceptance.** Each new entry (a)–(g), submitted as a §7.1 rule object, is refused by `core/rules` validation with the §10 item number in the error. Every §10 item has a label.

**Source items.** QF3-A23; QF6-A3; QF7-M1; QF7-M3; QF3-M6; QF6-M6; X-EX1-N2; QF4-M2; QF1-M1; QF3-A17. **Evidence:** Resolution 10 (red line E1, binding); DLB-T4; QF3 §4.7.

### R-34 Timing-fragility gate: timing profile with a look-ahead positive control on every card — BUILD NOW · GOVERNANCE · P0 · M7 (frozen before the first card run)

**Purpose.** *NEW in v2.0.* Timing errors were the largest source of fake edge in the programme: the Korea SOX×KRW gate's +0.31 Sharpe came from look-ahead (+0.05 implementable).

The v1.2 lag tests (T-LAG-01/02) cannot fail on registry errors, because they trust the registry's own `available_at`. R-12 loses 75% of its edge with one extra session and still passes both. R-34 adds two things:
- a performance-based **timing profile** on every card, with a positive control so that the detector itself can fail;
- golden availability fixtures (T-AVAIL-01, R-20).

**Package / module and functions.**
- `core/quant/backtest.timing_profile(card) -> TimingProfile`, **proposed**.
- `docs/macro_overlay_study.py` writes `model_card.macro.timing_profile`.
- `tests/run_all.py`: T-PLACEBO-01 and T-AVAIL-01.

**Inputs (PIT fields).**
- The card's rule with its acting inputs re-timed.
- L = the number of sessions between the last information close used and the first session the weight earns:
  - **L = 1 is the honest convention** (decide at the close of t, earn from t+1);
  - L = 0 uses the same session's close (look-ahead);
  - L = −1 uses the next session's (gross look-ahead).
- Plus the **publication-strict** timing of R-19 for every published series.

**Rule / algorithm.**
```python
for L in (-1, 0, 1, 2, 3, "strict"):
    book = run(card, lag=L)
    dSR[L] = SR(book) - SR(comparator(book))          # overlay-off (CARD-O) or S (CARD-P)
    dMDD[L], dES21[L] = drawdown_and_es_lines(book)   # printed
    ledger.append(card.family_id, {**card.config, "lag": L, "timing_class": "NON-COMPLIANT" if L in (-1, 0) else "COMPLIANT"})   # R-23
assert abs(dSR[1] - card.reported_dSR) < 1e-9          # harness integrity: the L = 1 row is the card's own result
LP = dSR[0] - dSR[1]                                   # look-ahead premium
LF = dSR[1] - dSR[2]                                   # lag fragility
FR = LF / dSR[1] if dSR[1] > 0 else None               # printed "n/m" when dSR[1] <= 0
fragile = (FR is not None and FR > 0.5) or (dSR[1] != 0 and sign(dSR[2]) == -sign(dSR[1]))
```
- **Timing-fragile** cards are capped at INSUFFICIENT DATA (Tier B treatment; a cap only lowers, so a REJECT stays a REJECT; R-21). Their header must name a live, time-stamped production feed for every acting input.
- **Positive control:** the prior Korea SOX×KRW gate fixture (DO-NOT-BUILD, R4 B3) must show LP ≥ 0.20. Otherwise T-PLACEBO-01 fails, which means the detector is broken. The fixture `KR_SOX_KRW_gate_B3` carries the R4 B3 inputs (SOX and USD/KRW closes) and the gate's rule (thresholds and multiplier, quoted from R4 B3), so `run(card, lag=L)` re-times its inputs.
- The threshold FR 0.5 is declared once, before any card runs. Slow (monthly) rules show LF ≈ 0 trivially: it is reported, not rewarded.
- **Look-ahead rows run only in the hermetic `timing_probe` sandbox (C-4).** The L ≤ 0 rows and the positive control re-time inputs outside `pit_value`, inside `core/quant/backtest.timing_profile` only, called from `tests/` or the R-34 sandbox. Everything they produce is tagged `synthetic_lookahead = true` and never written as a production artifact, book or card field other than `timing_profile.lags[]`. The lag audit records their violations in `timing_profile.lags[].lag_audit` instead of raising. The rows enter the family ledger with `timing_class: NON-COMPLIANT`, and nothing but LP reads them. `lag_audit_violations` (§6.5) counts the L ≥ 1 and strict rows only. `timing_probe` cannot be enabled by the runtime, a book builder or a card's verdict path (T-PLACEBO-02). This is the one exception to the no-look-ahead rules (P5, R-01, the §3.5 interface rules, T-LAG-01/02), and each of them says so.

**Config keys** (merge into §7; frozen in `gate.package`):
```yaml
gate:
  timing:                                            # R-34
    lags_sessions: [-1, 0, 1, 2, 3]
    plus_publication_strict: true
    honest_lag: 1
    fragility_ratio_max: 0.5                         # declared once, before any card runs
    sign_flip_by_lag: 2
    consequence: {verdict_cap: INSUFFICIENT_DATA, tier_cap: B, require_live_timestamped_feed: true}
    positive_control: {fixture: KR_SOX_KRW_gate_B3, contents: R4_B3_inputs_and_rule, look_ahead_premium_min: 0.20}   # observed 0.28
    every_lag_in_family_ledger: true
    lookahead_rows: {mode: timing_probe, scope: [tests, r34_sandbox], tag: synthetic_lookahead, ledger_timing_class: NON-COMPLIANT,
                     production_writes: forbidden}
```

**Outputs and schema fields.** `model_card.macro.timing_profile`, a result field covered by `results_md5` and never written to the header: `{lags: [{L, dSR, dMDD, dES21, lag_audit, timing_class}], strict: {...}, LP, LF, FR, label ∈ {robust, timing_fragile}, live_feeds[]}` (§6.5).

**Fail-closed behaviour.**
- A card without a timing profile is refused.
- If the positive control does not trip, every card run is blocked.
- A timing-fragile card without named live feeds is refused.

**Acceptance tests.**

| ID | Test | Pass condition |
|---|---|---|
| T-PLACEBO-01 | Timing profile with positive control | The look-ahead control (Korea SOX×KRW gate, in the `timing_probe` sandbox) is flagged: LP 0.28 ≥ 0.20 (L0 +0.317; L1 +0.035). R-12 is flagged (FR 0.74 from the printed grid, 0.75 in QF2; > 0.5). R-03 (FR 0.03) and R-04 (FR ≈ 0) pass. R-06 KR's row runs on the QF2 2016–26 fixture with the raw-return flag and is printed, not asserted (ΔSR 0.004 at L1 lies within the Level-1 Sharpe tolerance of 0, where R-34's sign-flip clause decides; 0.022 at L2); the formal card's own profile comes from its 1997–2026 excess-return run. R-11's FR is printed (0.49 in QF2; within tolerance of the 0.5 threshold, so its flag is not asserted). Every lag tried is written to the family ledger (in tests, its temporary copy; T-HERM-02), the L ≤ 0 rows with `timing_class: NON-COMPLIANT`. |
| T-PLACEBO-02 | Probe isolation | A static check finds no call into `timing_probe` outside `timing_profile()`. Enabling it from the runtime or a book builder raises. A card whose gate statistics read an L ≤ 0 row is refused. Everything written in probe mode carries `synthetic_lookahead = true` and lands outside the production artifact directory. The positive control's L0 row is computed and its LP recorded. |
| T-AVAIL-01 | Registry errors | The golden availability fixtures (R-20) fail on an injected registry error, e.g. H.15 posted at D instead of D+1 16:15 ET |

**Source items.** QF2-M2; QF2-A25; QF2-A16; QF2-A17.

**Evidence.**
- QF2 §4.2 (`qf2_03`, `qf2_05` P-C): the L-grid table.
  - R-03 0.348 / 0.314 / 0.306 / 0.304 gross; 0.273 net at L1;
  - R-04 flat 0.081–0.088;
  - R-06 KR 0.062 / 0.004 / 0.022 / 0.028, with ΔMDD 5.8 / 4.5 / 4.2 / 4.0 pp;
  - R-11 0.083 / 0.032 / 0.016 / −0.016;
  - R-12 0.054 / 0.038 / 0.010 / −0.000;
  - control 0.317 / 0.035.
- QF2-A25: R-12 passes T-LAG-01/02.
- QF2-A16 / A17 (CONFIRMED).
- Ghysels–Horan–Moench (RFS 2018).

### R-35 macro_daily workflow gates aligned with v2 (roles, verdict filter, refusal and FORWARD-SIM books) — BUILD NOW · GOVERNANCE · P1 · M8

**Rule.** *CHANGED.* `core/skills/workflows/macro_daily.yaml` is **materialised in §3.9**. It runs after the close-print bound of each market (R-20) and uses the official close (R-01).
- **`data_ok`** applies R-19's roles:
  - acting inputs fail closed and HALT only the books they are bound to, at the binding's limit (default the 2nd consecutive failed decision; 5 for the KODEX basket) or at the book's counter (R-19 rule 4);
  - risk-model inputs set `hedge_credit_off` and never HALT;
  - forward_sim inputs fail their FORWARD-SIM books closed; history inputs refuse a card whose span they do not cover; neither touches the recommended book;
  - context inputs are labelled.
- **`verdict_filter`** admits a factor to the recommended book only if its card's verdict is **PASS**, with build status BUILD NOW or BUILD-AS-INSURANCE (§8.1.2), or if it is an R-31 step with disposition `INVARIANT_STEP` (binding share ≤ 0.10, frozen with the R-31 header). A card whose `build_status_on_pass` is BUILD_AS_INSURANCE but whose verdict is NOT_RUN or INSUFFICIENT DATA (R-06 KR today) is refused. **Verdict integrity (R2-C4).** `docs/macro_overlay_study.py` appends every formal result to `cards/verdicts.jsonl` (append-only, hash-chained: `card_id`, revision, `header_md5`, `results_md5`, verdict, disposition, `gate_package_md5`, `data_snapshot_id`, `git_hash`, `ledger_hash_at_run`, `prev_row_md5`) and commits it with the card file. `verdict_filter` admits a factor only if (i) its card file re-hashes to the committed `results_md5` and the chain verifies; (ii) the card's `gate_package_md5` equals the frozen package's `definitions_md5`; and (iii) its snapshot is reproducible (`data_snapshot_id` recomputed from the store at the card's `knowledge_utc` matches) and its `git_hash` is a commit whose harness sources hash to the package manifest's entries. Otherwise the factor stays in the specification book and VERDICT_INTEGRITY (severity page) is raised (T-CARD-03).
- **FORWARD-SIM cards** (R-28, R-29) run their own forward books. **Refusal books** (R-11, R-12) are display-only. Neither ever reaches `engine_feed`. The I-03 assertion is extended to both.
- The recommended book composes by `min()` (R-02). Once two or more de-risk factors act in it, it is gated as one stack CARD-P.

**Acceptance.**
- I-01 on 2026-10-02 uses the official close 7,003.74.
- The `data_ok` gate passes a stale risk-model input with `hedge_credit_off` set, and fails closed on a stale acting input, for the books that input is bound to only (T-SCOPE-01).
- `verdict_filter` admits a card to the recommended book only if its verdict is PASS (build status BUILD NOW or BUILD-AS-INSURANCE); a card whose `build_status_on_pass` is BUILD_AS_INSURANCE but whose verdict is NOT_RUN or INSUFFICIENT DATA (R-06 KR today) is refused. R-31 steps enter only as `INVARIANT_STEP`.
- The refusal books (R-11, R-12) and the FORWARD-SIM cards (R-28, R-29) never reach `engine_feed`.

**Source items.** QF2-M3; QF4-M7; QF2-M8; QF1-A3. **Evidence:** Resolutions 7 and 8; DLA §7 (official close).

---

## 6. JSON artifact schemas 2.0 (written by `core/ficc/macro` builders; schemas next to them, proposed; R-32)

**Schemas are the contract (C-7).** Every field a rule writes is declared in the schema of the artifact it writes. Where a rule's "Outputs and schema fields" list and this section differ, the rule governs and this section is fixed in the same change (R-32). T-SCHEMA-01 validates every example in this spec against its schema; T-SCHEMA-03 builds one synthetic artifact or card from each rule's Outputs list and validates it.

Common conventions:
- JSON Schema draft 2020-12. All schemas are loaded into **one registry keyed by `$id`**; a cross-schema `$ref` is relative to the `$id` base `quantgen/` (e.g. `macro_state.v2.0#/$defs/input`).
- All times are ISO-8601 UTC with a "Z" suffix. Dates are ISO dates (a monthly series uses the first day of its reference month, §4.1).
- Every artifact carries `schema`, `schema_version` ("2.0"), `generated_at_utc`, `knowledge_utc` (the run's pinned knowledge instant, R-01), `git_hash`, `config_hash` (hash of the rules-store state), `data_snapshot_id` (md5 of the sorted content hashes visible at `knowledge_utc`, R-01) and `read_only: true`. Every schema below declares these fields in `properties` and `required`: an `event_calendar` file carries them once, in its envelope, and a model card carries them in its result part (§6.5); a `governance_event` line (§6.6) is a log record, not an artifact, and carries only its own fields.
- **Closed objects.** `additionalProperties: false` applies to every object schema that declares `properties`, except `extras` (always open), a map (an object that declares its own `additionalProperties`), a schema that declares `unevaluatedProperties`, and the card header's shared field set `model_card_header.macro.v2.0#/$defs/fields`, which the two card schemas of §6.5 close through `unevaluatedProperties: false`. The listings omit the keyword for brevity; the schema loader adds it under exactly this rule, and T-SCHEMA-01 runs with it.
- **Placeholders.** In the examples, a string written `<…>` stands for a value of the declared type (a hash, an instant, a date, a number); T-SCHEMA-01 replaces it by a typed sample before validating. Every other value is literal.
- No artifact contains an order instruction. Weights are targets for the simulated order book only.
- **Version history.** v1.1 and v1.2 artifacts used `schema_version` "1.1". The fields added in v2.0 are listed at the head of each subsection; "(round 1)" marks the adversarial-round additions.

### 6.1 `macro_state` (one per market per decision time)

**New in 2.0:**
- every input carries `value_status`, `session_date`, `available_at_source`, `retrieved_at_utc` (required) and its staleness `role`;
- `vol` carries the instrument book and both volatility labels;
- `flags` carry the hard stop, the step state, gap sessions and `fx_hedge_credit`;
- new blocks: `annotations` (R-08), `refusal_books` and `forward_sim` (display only), `concentration` (R-07) and `owner_decisions`;
- (round 1) `knowledge_utc`, `decided_session` and `run_mode`; inputs carry `obs_kind`, `dispute`, `books`, `expected_available_utc` (the next-due instant), `stale_deadline_utc` and `content_hash` (R-01, R-19); the `lag_audit` record (§3.9); `vol.estimator_gate` as an object, R-30's estimator names, `vt_status` and `vt_weight_recommended_book`; `flags.hedge_reasons`, `gap_sessions ≥ 0` and `var_display_scale`; R-31's ladder names; `concentration.by_book`; structured `alerts`; `runtime[]`, one entry per book (§3.8).

```json
{
  "$id": "quantgen/macro_state.v2.0",
  "type": "object",
  "required": ["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id",
               "decision_utc","decided_session","effective_session","market","run_mode","inputs","lag_audit","vol","flags","annotations",
               "concentration","owner_decisions","runtime","fail_closed","alerts"],
  "properties": {
    "schema": {"const": "quantgen.macro_state"}, "schema_version": {"const": "2.0"}, "read_only": {"const": true},
    "generated_at_utc": {"type": "string", "format": "date-time"},
    "knowledge_utc": {"type": "string", "format": "date-time", "description": "the run's pinned knowledge instant (R-01)"},
    "git_hash": {"type": "string"}, "config_hash": {"type": "string"}, "data_snapshot_id": {"type": "string"},
    "decision_utc": {"type": "string", "format": "date-time", "description": "close_print_bound_utc(market, decided_session) from the calendar (R-20)"},
    "decided_session": {"type": "string", "format": "date", "description": "the session whose official close is decided on (t)"},
    "effective_session": {"type": "string", "format": "date", "description": "the session whose return the decision earns (t+1)"},
    "market": {"enum": ["KR","US","JP","EU","TW","CN","HK","IN","EM","CRYPTO","FX"]},
    "run_mode": {"enum": ["live","backtest","replay"]},
    "inputs": {"type": "array", "items": {"$ref": "#/$defs/input"}},
    "lag_audit": {"type": "object", "required": ["checked","violations"], "properties": {
        "checked": {"type": "integer", "minimum": 0},
        "violations": {"type": "array", "items": {"type": "object",
          "required": ["series_id","obs_date","check","expected_usable_at_utc","stamped_available_at_utc"],
          "properties": {"series_id": {"type": "string"}, "obs_date": {"type": "string", "format": "date"}, "check": {"type": "string"},
            "expected_usable_at_utc": {"type": "string", "format": "date-time"},
            "stamped_available_at_utc": {"type": "string", "format": "date-time"}}}}}},
    "vol": {"type": "object", "properties": {
        "estimator": {"enum": ["sma20","ewma094","ewma097","garch_t","gjr_t","log_har_range","comb"], "description": "R-30; the sma60 reference line goes in extras (§9.4)"},
        "estimator_b5": {"enum": ["PASS","FAIL","NOT_RUN"]},
        "estimator_gate": {"type": "object", "required": ["status","fallback_used"], "properties": {
            "status": {"enum": ["registered_default","challenger_selected","fallback_to_sma20","NOT_RUN"]},
            "stage1": {"type": ["object","null"]}, "stage2_mcs_p": {"type": ["number","null"]}, "stage3_rank": {"type": ["integer","null"]},
            "fallback_used": {"type": "boolean"}, "reason": {"type": ["string","null"]}}},
        "vt_status": {"enum": ["ok","warmup","fail_closed"], "description": "R-06: a warm-up returns 1.0 and is not a failure"},
        "sigma_ann": {"type": ["number","null"], "minimum": 0},
        "target_ann": {"type": "number", "exclusiveMinimum": 0},
        "vt_weight_next": {"type": "number", "minimum": 0, "maximum": 1, "description": "specification book"},
        "vt_weight_recommended_book": {"type": "number", "minimum": 0, "maximum": 1, "description": "= vt_weight_next once R-06's card is PASS; 1.0 while NOT_RUN or INSUFFICIENT"},
        "instrument_book": {"type": "string"}, "rebalance": {"enum": ["daily","weekly","monthly"]},
        "no_trade_band": {"type": ["number","null"], "minimum": 0},
        "display_label_rel": {"enum": ["calm","normal","elevated","stressed"]},
        "label_method_rel": {"const": "trailing756_quartiles_causal_filtered"},
        "display_label_abs": {"enum": ["calm","normal","elevated","stressed"]},
        "label_method_abs": {"const": "expanding_full_history_quartiles_causal_filtered"},
        "alt_sigma_logged": {"type": ["number","null"], "description": "asymmetric estimator only (BL-C04); max(SMA20, implied) is retired"}},
      "required": ["estimator","estimator_b5","estimator_gate","vt_status","sigma_ann","target_ann","vt_weight_next","vt_weight_recommended_book",
                   "instrument_book","display_label_rel","label_method_rel","display_label_abs","label_method_abs"]},
    "flags": {"type": "object", "properties": {
        "dm_bear_state": {"type": "boolean", "description": "specification book only (R-04)"},
        "hedge_credit_off": {"type": "boolean"}, "hedge_failure": {"type": "boolean"}, "classic_risk_off": {"type": "boolean"},
        "hedge_reasons": {"type": "array", "items": {"enum": ["ok","risk_model_input_stale","risk_model_exception","corr_positive","core_pce_ge_3"]}, "description": "causes can co-occur (R-09, R-19)"},
        "hedge_stale_inputs": {"type": "array", "items": {"type": "string"}},
        "fx_hedge_credit": {"type": ["boolean","null"], "description": "display only (R-09)"},
        "kr_open_gap_event": {"type": "boolean"},
        "gap_sessions": {"type": "integer", "minimum": 0, "description": "n_US: US sessions since the previous KRX close; 0 after a US-only holiday (R-10)"},
        "var_display_scale": {"type": "number", "minimum": 1, "description": "sqrt(max(n_US, 1)); display only (R-10)"},
        "ladder_step": {"enum": ["none","step_-8","step_-12","hard_stop_-15"]},
        "ladder_dwell_left": {"type": "integer", "minimum": 0},
        "block_new_entries": {"type": "boolean", "description": "the -12% step's evaluator block (R-31)"},
        "ladder_steps_act_in": {"enum": ["recommended","specification"], "description": "recommended only as INVARIANT_STEP (binding share <= 0.10)"},
        "hard_stop": {"enum": ["armed","halted","rearm_refused","post_rearm_cap"]},
        "hard_stop_level": {"type": "number", "description": "owner decision D2 (risk_layer.drawdown.hard_stop.level)"},
        "engine_state": {"enum": ["DISARMED","ARMED","HALTED"], "description": "the market's recommended book; every book is in runtime[]"}},
      "required": ["hedge_credit_off","hedge_failure","classic_risk_off","hedge_reasons","kr_open_gap_event","gap_sessions","var_display_scale",
                   "ladder_step","ladder_dwell_left","block_new_entries","hard_stop","engine_state"]},
    "annotations": {"type": "object", "properties": {"vix_ge_vix3m": {"type": "boolean", "description": "R-08; changes no weight"}, "notes": {"type": "array", "items": {"type": "string"}}},
      "required": ["vix_ge_vix3m"]},
    "refusal_books": {"type": "object", "description": "display only; read by no book (R-11, R-12)",
      "properties": {"S1_krw_flag": {"type": ["boolean","null"]}, "S2_rates_flag": {"type": ["boolean","null"]}}},
    "forward_sim": {"type": "object", "description": "FORWARD-SIM cards (R-28, R-29); never the recommended book",
      "properties": {"R28_below_sma10m": {"type": ["boolean","null"]}, "R29_vt_weight_next": {"type": ["number","null"], "minimum": 0, "maximum": 1}}},
    "concentration": {"type": "object", "properties": {
        "template": {"enum": ["domestic_max10_or_weight","msci_25_50","pair_35"], "description": "owner decision D1"},
        "pair_share_kospi": {"type": ["number","null"]}, "pair_lookthrough_share": {"type": ["number","null"]},
        "pair_risk_contribution": {"type": ["number","null"]},
        "absolute_bound": {"type": ["number","null"], "description": "template single-name level / look-through share (R-07 (4))"},
        "active_bound": {"type": ["number","null"], "description": "min over names of 0.05 / (s_i - b_tilde_i) (R-07 (2), (4))"},
        "aggregate_bound": {"type": ["number","null"], "description": "aggregate template limit / look-through share of names above 4.5% (R-07 (3), (4))"},
        "semis_bound": {"type": ["number","null"], "description": "0.50 / look-through semiconductor share of sleeve NAV (R-07 (5))"},
        "by_book": {"type": "object", "additionalProperties": {"type": "object", "required": ["composed","gross","binding_factor"],
          "properties": {"composed": {"type": "number", "minimum": 0, "maximum": 1}, "gross": {"type": "number", "minimum": 0, "maximum": 1},
            "binding_factor": {"enum": ["none","absolute_single_name","active_single_name","aggregate","semis"]}}}}},
      "required": ["template","by_book"]},
    "owner_decisions": {"type": "object", "description": "every decision whose canonical key a rule of this market reads, plus every decision with status pending", "additionalProperties": {"type": "object",
        "required": ["decision","value","status"],
        "properties": {"decision": {"enum": ["D1","D2","D3","D4","D5","D6"]}, "value": {}, "status": {"enum": ["default","owner_set","pending"]}}}},
    "runtime": {"type": "array", "items": {"type": "object", "required": ["book_id","engine_state","halt","consecutive_failures","book_counter"],
      "properties": {"book_id": {"type": "string", "description": "recommended:<market>, specification:<market>, forward_sim:<rule>, refusal:<rule>, card:<card_id>:<on|off|S>"},
        "engine_state": {"enum": ["DISARMED","ARMED","HALTED"]},
        "halt": {"type": ["object","null"], "required": ["class","reason_code","since_utc","rearm_mode","causes"],
          "properties": {"class": {"enum": ["RISK","OPS"]}, "reason_code": {"type": "string"},
            "component": {"type": ["string","null"]}, "series_id": {"type": ["string","null"]}, "since_utc": {"type": "string", "format": "date-time"},
            "rearm_not_before": {"type": ["string","null"], "format": "date", "description": "RISK: the decided_session (t+10) of the earliest automatic re-arm decision (a breach re-arms only once its limit is met); null for OPS"}, "rearm_mode": {"enum": ["auto","operator"]},
            "causes": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["class","reason_code","since_utc","rearm_mode"],
              "properties": {"class": {"enum": ["RISK","OPS"]}, "reason_code": {"type": "string"}, "since_utc": {"type": "string", "format": "date-time"},
                "rearm_mode": {"enum": ["auto","operator"]}, "rearm_not_before": {"type": ["string","null"], "format": "date"},
                "cleared_utc": {"type": ["string","null"], "format": "date-time"}}}},
            "ack_by": {"type": ["string","null"]}, "ack_utc": {"type": ["string","null"], "format": "date-time"}}},
        "post_rearm_cap_until": {"type": ["string","null"], "format": "date", "description": "the last decided_session whose weights carry post_rearm_cap 0.5: the actual re-arm decision + 9 sessions (t+19 after an automatic re-arm at t+10)"}, "nav": {"type": ["number","null"]},
        "hwm_hard": {"type": ["number","null"]}, "ref_step": {"type": ["number","null"]},
        "consecutive_failures": {"type": "object", "additionalProperties": {"type": "integer", "minimum": 0}, "description": "per acting series bound to the book (R-19 rule 4)"},
        "book_counter": {"type": "integer", "minimum": 0, "description": "R-19 rule 4"}}}},
    "fail_closed": {"type": "boolean"},
    "alerts": {"type": "array", "items": {"type": "object", "required": ["alert_id","code","severity","component","first_seen_utc","count"],
      "properties": {"alert_id": {"type": "string"}, "code": {"type": "string"}, "severity": {"enum": ["info","warn","page"]},
        "component": {"type": "string"}, "series_id": {"type": ["string","null"]}, "books": {"type": "array", "items": {"type": "string"}},
        "first_seen_utc": {"type": "string", "format": "date-time"}, "count": {"type": "integer", "minimum": 1},
        "escalated": {"type": "boolean"}, "ack_utc": {"type": ["string","null"], "format": "date-time"}}}},
    "extras": {"type": "object", "description": "open: e.g. regime_tags (R-20), validation_errors (R-32), the sma60 reference line"}
  },
  "$defs": {"input": {"type": "object",
    "required": ["name","series_id","source","obs_date","session_date","obs_kind","value","value_status","dispute","available_at_utc","available_at_source",
                 "retrieved_at_utc","expected_available_utc","stale_deadline_utc","vintage","timing","role","books","status","content_hash"],
    "properties": {"name": {"type": "string"}, "series_id": {"type": "string"}, "source": {"type": "string"}, "channel": {"type": ["string","null"]},
      "obs_date": {"type": "string", "format": "date"}, "session_date": {"type": ["string","null"], "format": "date"},
      "obs_kind": {"enum": ["close","quote_snapshot","release","bar","derived"]},
      "value": {"type": ["number","null"]},
      "value_status": {"enum": ["official_close","vendor_close","live_snapshot","provisional_intraday","first_release","revised","vendor_derived","vendor_derived_across_gap"]},
      "dispute": {"type": "boolean", "description": "official value used, two-source mismatch alerted (R-01 (3)); never a failure"},
      "available_at_utc": {"type": "string", "format": "date-time"},
      "available_at_source": {"enum": ["published","calendar_bound","inferred_from_retrieval"]},
      "retrieved_at_utc": {"type": "string", "format": "date-time"},
      "expected_available_utc": {"type": ["string","null"], "format": "date-time", "description": "R-19: the instant the next observation after obs_date is due"},
      "stale_deadline_utc": {"type": ["string","null"], "format": "date-time", "description": "expected_available_utc + grace (one publication business day)"},
      "vintage": {"type": ["string","null"], "format": "date", "description": "ALFRED realtime_start of this value; null for unrevised market prices"},
      "timing": {"enum": ["live","publication","value_proxy"]},
      "role": {"enum": ["acting_exposure","forward_sim","risk_model","context","history"]},
      "books": {"type": "array", "items": {"type": "string"}, "description": "the books this binding feeds: the HALT scope (§3.8)"},
      "status": {"enum": ["ok","stale","stale_missed_release","missing","provisional_rejected","session_mismatch","synthetic_rejected","disputed","warmup"]},
      "content_hash": {"type": "string"}}}}
}
```

Example: KR, decided at the official close of 2 Oct 2026, earning in the next KRX session (6 Oct; 5 Oct is a substitute holiday).

```json
{"schema":"quantgen.macro_state","schema_version":"2.0","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","knowledge_utc":"2026-10-02T06:40:50Z",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>",
 "decision_utc":"2026-10-02T06:30:30Z","decided_session":"2026-10-02","effective_session":"2026-10-06","market":"KR","run_mode":"live",
 "inputs":[{"name":"KOSPI official close","series_id":"KOSPI_OFFICIAL_CLOSE","source":"KIS","channel":"KRX official close","obs_date":"2026-10-02","session_date":"2026-10-02",
            "obs_kind":"close","value":7003.74,"value_status":"official_close","dispute":false,"available_at_utc":"2026-10-02T06:30:30Z","available_at_source":"calendar_bound",
            "retrieved_at_utc":"2026-10-02T06:40:45Z","expected_available_utc":"2026-10-06T06:30:30Z","stale_deadline_utc":"2026-10-07T06:30:30Z","vintage":null,
            "timing":"live","role":"acting_exposure","books":["specification:KR"],"status":"ok","content_hash":"<md5>"},
           {"name":"USD/KRW DEXKOUS (labelled proxy; R-11 refusal book and context)","series_id":"DEXKOUS","source":"FRED","channel":"H.10","obs_date":"2026-09-25","session_date":null,
            "obs_kind":"release","value":1356.51,"value_status":"first_release","dispute":false,"available_at_utc":"2026-09-28T20:15:00Z","available_at_source":"published",
            "retrieved_at_utc":"2026-10-02T06:40:45Z","expected_available_utc":"2026-10-05T20:15:00Z","stale_deadline_utc":"2026-10-06T20:15:00Z","vintage":null,
            "timing":"publication","role":"context","books":[],"status":"ok","content_hash":"<md5>"}],
 "lag_audit":{"checked":1,"violations":[]},
 "vol":{"estimator":"sma20","estimator_b5":"PASS",
        "estimator_gate":{"status":"registered_default","stage1":null,"stage2_mcs_p":null,"stage3_rank":null,"fallback_used":false,"reason":null},
        "vt_status":"ok","sigma_ann":0.2882,"target_ann":0.20,"vt_weight_next":0.694,"vt_weight_recommended_book":1.0,
        "instrument_book":"KRX_ETF_line","rebalance":"daily","no_trade_band":0.0,
        "display_label_rel":"elevated","label_method_rel":"trailing756_quartiles_causal_filtered",
        "display_label_abs":"stressed","label_method_abs":"expanding_full_history_quartiles_causal_filtered","alt_sigma_logged":null},
 "flags":{"dm_bear_state":false,"hedge_credit_off":true,"hedge_failure":false,"classic_risk_off":false,"hedge_reasons":["corr_positive","core_pce_ge_3"],
          "hedge_stale_inputs":[],"fx_hedge_credit":false,"kr_open_gap_event":true,"gap_sessions":2,"var_display_scale":1.4142,
          "ladder_step":"none","ladder_dwell_left":0,"block_new_entries":false,"ladder_steps_act_in":"specification",
          "hard_stop":"armed","hard_stop_level":-0.15,"engine_state":"ARMED"},
 "annotations":{"vix_ge_vix3m":false,"notes":[]},
 "refusal_books":{"S1_krw_flag":false,"S2_rates_flag":null},
 "forward_sim":{"R28_below_sma10m":null,"R29_vt_weight_next":null},
 "concentration":{"template":"msci_25_50","pair_share_kospi":0.51,"pair_lookthrough_share":0.538,"pair_risk_contribution":0.75,
                  "absolute_bound":0.755,"active_bound":0.685,"semis_bound":null,
                  "by_book":{"recommended:KR":{"composed":1.0,"gross":0.685,"binding_factor":"active_single_name"},
                             "specification:KR":{"composed":0.694,"gross":0.685,"binding_factor":"active_single_name"}}},
 "owner_decisions":{"risk_layer.korea_caps.template":{"decision":"D1","value":"msci_25_50","status":"default"},
                    "risk_layer.drawdown.hard_stop.level":{"decision":"D2","value":-0.15,"status":"default"}},
 "runtime":[{"book_id":"recommended:KR","engine_state":"ARMED","halt":null,"post_rearm_cap_until":null,"nav":null,"hwm_hard":null,"ref_step":null,
             "consecutive_failures":{},"book_counter":0},
            {"book_id":"specification:KR","engine_state":"ARMED","halt":null,"post_rearm_cap_until":null,"nav":null,"hwm_hard":null,"ref_step":null,
             "consecutive_failures":{},"book_counter":0}],
 "fail_closed":false,"alerts":[]}
```

**Notes on the example.**
- **Decision time.** The decision is stamped at the KRX close-print bound for the session, `close_print_bound_utc('KR', 2026-10-02)` = 06:30:30Z (06:00:30Z before 2016-08-01; R-20). The workflow ran at 06:41Z, after the close + 10 minutes, and pinned `knowledge_utc` at the end of its fetches (06:40:50Z), so no provisional row could be read. Every input has `available_at_utc ≤ decision_utc` and `retrieved_at_utc ≤ knowledge_utc`. A record stamped after 06:30:30Z must be rejected by the lag audit (T-LAG-01, T-CLOSE-01).
- **The official close.** The KOSPI row carries `value_status = official_close` for the decided session. The vendor row 6,943.66, from a file written at 10:56 KST, mid-session, would have returned `MissingInput("provisional_intraday")` (T-PROV-01).
- **Staleness fields.** `expected_available_utc` is when the **next** observation is due, never the availability of the row itself (R-19 step 3): the KOSPI close of the next session (6 Oct, 06:30:30Z) and the next H.10 release (Monday 5 Oct, 16:15 ET = 20:15Z). `stale_deadline_utc` adds one publication business day of grace.
- **Effective session and gap flags.** The next KRX session is 6 Oct, because 5 Oct is a substitute holiday. The US Sep NFP (2 Oct 21:30 KST) makes it an opening-gap event session, and the US sessions of 2 Oct and 5 Oct make it a multi-session gap session (`gap_sessions` 2). Its displayed 1-day VaR is scaled by √2 = 1.4142 (R-10). After a US-only holiday `gap_sessions` is 0 and the scale is 1 (I-06c).
- **H.10 timestamp.** The DEXKOUS row carries the H.10 weekly publication time: Monday 28 Sep 2026, 16:15 ET = 20:15Z. It is a context row and the R-11 refusal book's labelled proxy; it is bound to no book, and no book acts on it.
- **Hedge state.** `hedge_credit_off` is TRUE for two co-occurring reasons: corr63 +0.53 > 0 and core PCE YoY 3.008% ≥ 3.0% (R-09; §11).
- **Inputs abbreviated.** `inputs[]` shows 2 of the decision's inputs, and `lag_audit.checked` counts the one audited row shown (the KOSPI close; DEXKOUS is context, which the audit skips, §3.9). A full record lists, and the audit counts, every acting and risk-model input the decision reads: here also the KODEX 200 basket and the pair and KOSPI market caps (acting), and the corr63, core PCE and USD-proxy inputs and any Korea-covariance closes (risk model).
- **Data snapshot.** `vt_weight_next` 0.694 and both labels are computed from the official 2 Oct close (7,003.74). R4/R4b had used an intraday print (about 10:30 KST, in a file written at 10:56 KST) (6,943.66; weight 0.691); fixtures are re-frozen from post-close files (T-FIX-01).
- **Concentration, per book.** Under the default template (D1, MSCI 25/50) the absolute single-name bound is 22.5 / 29.8 = 0.755 and the active single-name bound is at most 0.05 / (0.298 − 0.225) = 0.685 (the risk layer computes b̃ on the day's basket). In the specification book, composed = vt = 0.694 and the active bound takes gross to 0.685; in the recommended book, where vt enters as 1.0 while R-06 KR is NOT_RUN, both bounds bind and the active one is lower (§3.3, §11). The pair's share is anchor-dependent (51–54%).
- **Ladder and runtime.** `ladder_steps_act_in = "specification"` because the Korea steps bind on more than 10% of days on the declared book until R-31 passes. The hard stop (D2 default) is armed. Each book has its own `runtime[]` entry; NAV fields are null until the simulated books start.

### 6.2 `overlay_decision` (one per market × family per decision)

**New in 2.0:**
- `composition` is `min`, and `overlay_min` replaces `overlay_product`;
- the market-gross record carries the `ladder` multiplier;
- each card carries a `disposition` and a `label`;
- new lists: `refusal` (display only) and `binding`;
- (round 1) the common provenance fields; `inputs` typed as the `macro_state` input; the `post_rearm_cap` factor; the `INVARIANT_STEP` disposition; `extras` (R-26, R-27, R-32).

```json
{
  "$id": "quantgen/overlay_decision.v2.0", "type": "object",
  "required": ["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id",
               "decision_utc","effective_session","market","family","exposure_basis","vol_scale","vol_scale_recommended_book","multipliers","composition",
               "overlay_min","overlay_floor","overlay_cap","overlay_applied_spec_book","overlay_applied_recommended_book","forward_sim","refusal","binding",
               "reasons","inputs","rule_versions"],
  "properties": {
    "schema": {"const": "quantgen.overlay_decision"}, "schema_version": {"const": "2.0"}, "read_only": {"const": true},
    "generated_at_utc": {"type": "string", "format": "date-time"}, "knowledge_utc": {"type": "string", "format": "date-time"},
    "git_hash": {"type": "string"}, "config_hash": {"type": "string"}, "data_snapshot_id": {"type": "string"},
    "decision_utc": {"type": "string", "format": "date-time"}, "effective_session": {"type": "string", "format": "date"},
    "market": {"enum": ["KR","US","JP","EU","TW","CN","HK","IN","EM","CRYPTO","FX"]},
    "family": {"enum": ["momentum","reversal","flow","quality","ts_trend","market_gross"]},
    "exposure_basis": {"enum": ["active","total"]},
    "vol_scale": {"type": "number", "minimum": 0, "maximum": 1, "description": "specification book (vs; vt for market_gross)"},
    "vol_scale_recommended_book": {"type": "number", "minimum": 0, "maximum": 1, "description": "= vol_scale if its card is PASS, else 1.0"},
    "vol_scale_card": {"$ref": "#/$defs/card"},
    "multipliers": {"type": "array", "items": {"type": "object", "required": ["rule_id","value","exposure_basis","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                      "exposure_basis": {"enum": ["active","total"]}, "card": {"$ref": "#/$defs/card"}}}},
    "ladder": {"enum": [0.5, 1.0, null], "description": "market_gross only (R-07, R-31)"},
    "post_rearm_cap": {"enum": [0.5, 1.0, null], "description": "market_gross only; an argument of min() for 10 sessions after a RISK re-arm (R-07)"},
    "composition": {"const": "min"},
    "overlay_min": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "overlay_floor": {"const": 0.5}, "overlay_cap": {"const": 1.0},
    "overlay_applied_spec_book": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "overlay_applied_recommended_book": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "forward_sim": {"type": "array", "items": {"type": "object", "required": ["rule_id","value","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0, "maximum": 1.0},
                      "would_apply_to": {"type": "string"}, "card": {"$ref": "#/$defs/card"}}}},
    "refusal": {"type": "array", "description": "display only; read by no book (R-11, R-12)", "items": {"type": "object", "required": ["rule_id","value","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                      "would_apply_to": {"type": "string"}, "card": {"$ref": "#/$defs/card"}}}},
    "binding": {"type": "array", "items": {"type": "string"}, "description": "factors at which min() or a limit bound"},
    "reasons": {"type": "array", "items": {"type": "string"}},
    "inputs": {"type": "array", "items": {"$ref": "macro_state.v2.0#/$defs/input"}},
    "rule_versions": {"type": "object", "additionalProperties": {"type": "string"}},
    "extras": {"type": "object", "description": "open: R-26 {instrument_book, contracts, w_target, w_held, band, usdkrw}, R-27 {fill_model, decision_price_source, fill_status, flags}, R-32 validation_errors"}
  },
  "$defs": {"card": {"type": "object", "required": ["card_id","class","verdict","disposition","displayed_as","results_md5"],
     "properties": {"card_id": {"type": "string"}, "class": {"enum": ["CARD-O","CARD-P"]},
       "verdict": {"enum": ["PASS","REVISE","REJECT","INSUFFICIENT_DATA","NOT_RUN"]},
       "disposition": {"enum": ["RECOMMENDATION","BUILD_AS_INSURANCE","INVARIANT_STEP","SPECIFICATION_ONLY","FORWARD_SIM","REFUSAL_BOOK","DESCRIPTIVE"]},
       "displayed_as": {"enum": ["recommendation","insurance","invariant","descriptive","refusal"]},
       "label": {"type": ["string","null"]}, "results_md5": {"type": ["string","null"]}}}}
}
```

**Rules.**
- `displayed_as ∈ {"recommendation", "insurance"}` iff `verdict = "PASS"` and `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}`.
- `displayed_as = "invariant"` iff `disposition = INVARIANT_STEP`: an R-31 step whose binding share is ≤ 0.10, frozen with the R-31 header. It needs no PASS and acts as part of the R-07 invariant (Resolution 6; R-31, R-35).
- `vol_scale_recommended_book` and `overlay_applied_recommended_book` use only those factors; every other factor enters as 1.0.
- The recommended-book builder refuses any factor with disposition `SPECIFICATION_ONLY`, `FORWARD_SIM` or `REFUSAL_BOOK`, and any card whose `build_status_on_pass` is BUILD_AS_INSURANCE while its verdict is NOT_RUN or INSUFFICIENT_DATA (I-03, R-35).
- A validation failure confined to display or context fields writes the record with `extras.validation_errors` and an alert, and never HALTs; an acting-field failure HALTs (OPS) the books the record describes (R-32).

Example, before the first card run. Every verdict is `NOT_RUN`, so the recommended book carries no overlay factor; the risk-layer invariants still apply:

```json
{"schema":"quantgen.overlay_decision","schema_version":"2.0","read_only":true,"generated_at_utc":"<run time>","knowledge_utc":"<pinned knowledge instant>",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>","decision_utc":"2026-10-01T20:00:30Z","effective_session":"2026-10-02",
 "market":"US","family":"momentum","exposure_basis":"active","vol_scale":0.50,"vol_scale_recommended_book":1.0,
 "vol_scale_card":{"card_id":"MACRO-R03-US-MOM","class":"CARD-O","verdict":"NOT_RUN","disposition":"DESCRIPTIVE","displayed_as":"descriptive",
                   "label":"indicative PASS; step 3 borderline","results_md5":null},
 "multipliers":[{"rule_id":"R-04-DM","value":1.0,"exposure_basis":"active",
                 "card":{"card_id":"MACRO-R04-US-DM","class":"CARD-O","verdict":"NOT_RUN","disposition":"SPECIFICATION_ONLY","displayed_as":"descriptive",
                         "label":"step 3 FAIL (indicative)","results_md5":null}}],
 "ladder":null,"post_rearm_cap":null,"composition":"min","overlay_min":1.0,"overlay_floor":0.5,"overlay_cap":1.0,
 "overlay_applied_spec_book":1.0,"overlay_applied_recommended_book":1.0,
 "forward_sim":[],"refusal":[],"binding":[],
 "reasons":["DM: 24m market return +39.7% >= 0 -> 1.0 (specification book only)","VS: sigma126 23.9% -> min(1, 0.12/0.239)=0.50"],
 "inputs":[{"name":"Mom sigma126","series_id":"MOM_PAPER_LS_SERIES","source":"French Data Library","channel":"Mom daily (research snapshot)","obs_date":"2026-08-31","session_date":null,
            "obs_kind":"derived","value":0.239,"value_status":"vendor_derived","dispute":false,"available_at_utc":"2026-09-30T00:00:00Z","available_at_source":"published",
            "retrieved_at_utc":"<retrieved_at_utc>","expected_available_utc":null,"stale_deadline_utc":null,"vintage":null,
            "timing":"publication","role":"acting_exposure","books":["specification:US"],"status":"ok","content_hash":"<md5>"}],
 "rule_versions":{"R-03":"2.0","R-04":"2.0"}}
```

**Notes on the example.**
- **Decision time.** The US decision is stamped at `close_print_bound_utc('US', 2026-10-01)` = 16:00:00 ET + 30 s = 20:00:30Z (R-20).
- **Where the values come from.** They are illustrative and come from the research snapshot, which uses the French Mom file through Aug-2026; the research file carries no publication schedule for the derived σ126, so its staleness fields are null. In production, σ126 is computed on QUANTGEN's own paper unit-gross long/short series through the close of t (R-03), and R-19 fills both fields; an `obs_date` a month old would be stale and would fail closed. The binding feeds the specification book only until R-03 PASSes (R-19 rule 5). `NOT_RUN` turns into the card's verdict after the first `docs/macro_overlay_study.py` run under the frozen package.
- **Where the S2 entry belongs.** `refusal` is empty here because S2 excluded momentum (R-12; T-BASIS-01). The S2 refusal entry belongs in the US record with `family: "market_gross"` and `exposure_basis: "total"`, e.g. `{"rule_id":"R-12-S2","value":0.5,"would_apply_to":"US duration-sensitive gross (refusal book)","card":{"card_id":"MACRO-R12-US-RATES","class":"CARD-P","verdict":"REJECT","disposition":"REFUSAL_BOOK","displayed_as":"refusal",...}}`. Its reason reads: "S2 refusal book: strict-H.15 flag on from the close of 2026-09-25 (data date 2026-09-23); display only".

### 6.3 `event_calendar` (one file per calendar version; entries per event; `core/calendars`)

**New in 2.0:**
- the BoK decision and the press conference are separate event types;
- a `KRX_HOLIDAY_GAP` type, with `gap_sessions` and `var_display_scale`;
- the `annotate_only` window action;
- (round 1) a file envelope that carries the common provenance fields once; `gap_sessions ≥ 0`.

```json
{"$id":"quantgen/event_calendar.v2.0","type":"object",
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id","calendar_version","events"],
 "properties":{"schema":{"const":"quantgen.event_calendar"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "calendar_version":{"type":"string","description":"the owner-signed core/calendars data version (T-CAL-01)"},
  "events":{"type":"array","items":{"$ref":"#/$defs/event"}}},
 "$defs":{"event":{"type":"object",
  "required":["event_id","type","region","scheduled_utc","status","source","windows"],
  "properties":{"event_id":{"type":"string"},
   "type":{"enum":["FOMC","US_CPI","US_NFP","US_OTHER_RELEASE","BOK_DECISION","BOK_PRESS_CONFERENCE","BOJ","ECB","KOSPI200_EXPIRY","INDEX_CHANGE","HYPERSCALER_EARNINGS","OIL_GEO","FX_INTERVENTION","KRX_HOLIDAY_GAP","POLICY_FRAMEWORK_CHANGE","MARKET_STRUCTURE_CHANGE","OTHER"]},
   "region":{"type":"string"},"scheduled_utc":{"type":"string","format":"date-time"},
   "status":{"enum":["scheduled","released","cancelled","delayed"]},"released_utc":{"type":["string","null"],"format":"date-time"},
   "source":{"type":"string"},
   "windows":{"type":"array","items":{"type":"object","required":["market","action","start_utc","end_utc"],
      "properties":{"market":{"type":"string"},"action":{"enum":["evaluator_block_new_intraday_entries","evaluator_block_new_futures_entries","annotate_only"]},
                    "start_utc":{"type":"string","format":"date-time"},"end_utc":{"type":"string","format":"date-time"},
                    "resume_condition":{"type":["string","null"]}}}},
   "kr_open_gap_session":{"type":["string","null"],"format":"date"},
   "gap_sessions":{"type":["integer","null"],"minimum":0},
   "var_display_scale":{"type":["number","null"],"description":"sqrt(max(n_US, 1)) for multi-session gaps; display only"},
   "scenario_tag":{"type":["string","null"]},"notes":{"type":"string"}}}}}
```

The file envelope (its `events` hold entries like the two below):

```json
{"schema":"quantgen.event_calendar","schema_version":"2.0","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","knowledge_utc":"2026-10-02T06:40:50Z",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>","calendar_version":"<signed version>","events":[]}
```

Example entry: FOMC on 28 Oct 2026, 14:00 EDT = 18:00 UTC = 03:00 KST on 29 Oct.

```json
{"event_id":"FOMC-2026-10-28","type":"FOMC","region":"US","scheduled_utc":"2026-10-28T18:00:00Z","status":"scheduled","released_utc":null,
 "source":"federalreserve.gov FOMC calendar",
 "windows":[{"market":"US","action":"evaluator_block_new_intraday_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":"VIX < pre-14:00 ET level else 19:30Z"},
            {"market":"KR_FUT_NIGHT","action":"evaluator_block_new_futures_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":null}],
 "kr_open_gap_session":"2026-10-29","gap_sessions":null,"var_display_scale":null,"scenario_tag":null,"notes":"KR opening-gap event night"}
```

Example entry: the US Sep NFP (2 Oct 2026, 08:30 EDT = 12:30 UTC = 21:30 KST). The entry block runs 08:25–10:00 ET (R-10). KRX is closed on 5 Oct, so the next KRX session is 6 Oct.

```json
{"event_id":"US-NFP-2026-10-02","type":"US_NFP","region":"US","scheduled_utc":"2026-10-02T12:30:00Z","status":"scheduled","released_utc":null,
 "source":"bls.gov Employment Situation schedule",
 "windows":[{"market":"US","action":"evaluator_block_new_intraday_entries","start_utc":"2026-10-02T12:25:00Z","end_utc":"2026-10-02T14:00:00Z","resume_condition":"10:00 ET"}],
 "kr_open_gap_session":"2026-10-06","gap_sessions":null,"var_display_scale":null,"scenario_tag":null,"notes":"KR opening-gap event; the 6 Oct session is also tagged KRX_HOLIDAY_GAP"}
```

### 6.4 `context_log` (one per decision; `core/ficc/macro`)

**New in 2.0:**
- items require `vintage` (null for unrevised series) and `retrieved_at_utc`;
- revised series carry `first_release`, `latest` and `vintage_date`;
- each item carries its timing and a stale label;
- (round 1) the common provenance fields and `decision_utc`; items require `series_id`, `value_status` and `stale`. `vintage` is the vintage of `value`; `latest` and `vintage_date` are the latest vintage visible at `knowledge_utc`; `as_of_utc` is the run's `decision_utc` (one log per decision). A `context_log` that fails validation is refused, labelled and alerted, and never HALTs (R-32).

```json
{"$id":"quantgen/context_log.v2.0","type":"object",
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id","decision_utc","as_of_utc","items","acts"],
 "properties":{"schema":{"const":"quantgen.context_log"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "decision_utc":{"type":"string","format":"date-time"},
  "as_of_utc":{"type":"string","format":"date-time","description":"= decision_utc (one log per decision)"},
  "acts":{"const":false},
  "items":{"type":"array","items":{"type":"object",
     "required":["name","series_id","value","obs_date","available_at_utc","retrieved_at_utc","vintage","source","timing","value_status","stale"],
     "properties":{"name":{"type":"string"},"series_id":{"type":"string"},"value":{"type":["number","string","null"]},
        "obs_date":{"type":"string","format":"date"},
        "available_at_utc":{"type":"string","format":"date-time"},"retrieved_at_utc":{"type":"string","format":"date-time"},
        "vintage":{"type":["string","null"],"format":"date","description":"the vintage of value (ALFRED realtime_start); null for unrevised series"},
        "first_release":{"type":["number","null"]},"latest":{"type":["number","null"]},
        "vintage_date":{"type":["string","null"],"format":"date","description":"the latest vintage visible at knowledge_utc"},
        "value_status":{"enum":["official_close","vendor_close","live_snapshot","provisional_intraday","first_release","revised","vendor_derived","vendor_derived_across_gap"]},
        "source":{"type":"string"},"timing":{"enum":["live","publication","value_proxy"]},"stale":{"type":"boolean"},
        "zscore_causal":{"type":["number","null"]},"zscore_window":{"type":["string","null"]},
        "from_sheet":{"type":"boolean","description":"true for the existing 18-indicator sheet items"},
        "range":{"type":["array","null"],"items":{"type":"number"}},"note":{"type":"string"}}}},
  "extras":{"type":"object"}}}
```

Example (three items; `<…>` values are typed placeholders):

```json
{"schema":"quantgen.context_log","schema_version":"2.0","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","knowledge_utc":"2026-10-02T06:40:50Z",
 "git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"<md5>","decision_utc":"2026-10-02T06:30:30Z","as_of_utc":"2026-10-02T06:30:30Z","acts":false,
 "items":[
  {"name":"Taylor residual range (pp)","series_id":"TAYLOR_RESIDUAL_RANGE","value":null,"range":[-2.3,-0.4],"obs_date":"2026-08-01",
   "available_at_utc":"<latest input release>","retrieved_at_utc":"<retrieved>","vintage":"<vintage date>",
   "source":"FRED PCEPILFE/UNRATE/NROU/GDPPOT; EFFR 3.875 mid","timing":"publication","value_status":"vendor_derived","stale":false,"note":"never thresholded"},
  {"name":"Recession probit (E-T coefficients)","series_id":"RECESSION_PROBIT_ET","value":0.095,"obs_date":"<last input date>",
   "available_at_utc":"<latest input release>","retrieved_at_utc":"<retrieved>","vintage":null,
   "source":"FRED T10Y3M; published coefficients","timing":"publication","value_status":"vendor_derived","stale":false,"note":"last read in Q1a"},
  {"name":"Payrolls, 2025 monthly average (k)","series_id":"PAYEMS","value":9.7,"first_release":119.4,"latest":9.7,"obs_date":"2025-12-01",
   "available_at_utc":"<release instant>","retrieved_at_utc":"<retrieved>","vintage":"<vintage date>","vintage_date":"<vintage date>",
   "source":"FRED/ALFRED PAYEMS","timing":"publication","value_status":"revised","stale":false,"note":"known then vs known now"}]}
```

### 6.5 `model_card_header.macro` and `model_card.macro` (one per card per revision; R-32)

QUANTGEN's cards already hold a hypothesis, a rule, a data span, pre-registered costs, a seed, every test line, the decision and an md5 of the results (public page). These schemas are a **proposed** superset for macro cards. Map them onto the app's actual card format; do not run a parallel registry.

**Two schemas, one field set (round 1).** The **header** (the §8.4 pre-registration) is validated against `model_card_header.macro` by `validate_card_header` at commit, before any run; `header_md5` covers the header fields only. The **card** is header ∪ results and is validated against `model_card.macro` when it is written; `results_md5` covers the result fields. Both close through `unevaluatedProperties: false`, so a header that carries a result field (`selection_factor`, `timing_profile`, `forward_record`, …) is refused, and a card cannot carry an undeclared field.

**New in 2.0** (a card validates only with all of them):
- `family_id`, `ledger_hash_at_registration` (header) and `ledger_hash_at_run`, `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `V_null` and `selection_factor` = {value, rule: computed_by_step3, alt_value} (result; R-23);
- `power {se_hac, se_blk250, se_plateau, mde80, power_at_0p05, power_at_0p10, …}` (R-24);
- `timing_profile` (a result; R-34);
- `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`, `nav_fx` (R-26);
- `cash_convention`, `history_first_close`, `data_span` with a fixed end, `start_band`, `midpoint_halves`, `episode_rule_version` (R-22);
- the stability results `start_band_results`, `midpoint_halves_results`, `regime_line_results`, and `gjr_null_pct`;
- `gate_package_version` and `gate_package_md5`, `build_status_on_pass`, `disposition`, `label`, `owner_decisions`;
- the remaining header fields of §8.4: `claim` (verbatim text) with `claim_type`, `estimator`, `fill_model` (and `roll_calendar` for futures), `costs`, `data`, `regime_lines`, `primary_oos_line`, `printed_lines`, `comparator`, `benchmarks`, `checks` and `outcomes`;
- the reproducibility fields `git_hash`, `config_hash`, `data_snapshot_id` and `knowledge_utc` (T-REPRO-01a).

```json
{"$id":"quantgen/model_card_header.macro.v2.0","type":"object","$ref":"#/$defs/fields","unevaluatedProperties":false,
 "$defs":{"fields":{"type":"object",
  "required":["card_id","family_id","rule_id","revision","class","claim","claim_type","label","build_status_on_pass","tier","created_utc","header_md5",
              "gate_package_version","gate_package_md5","hypothesis","mechanism","rule","parameters","searched_parameters","estimator",
              "instrument_book","rebalance","no_trade_band","notional_nav","fill_model","costs","data","history_first_close","data_span",
              "cash_convention","episode_rule_version","start_band","midpoint_halves","regime_lines","primary_oos_line","printed_lines",
              "comparator","benchmarks","checks","ledger_hash_at_registration","N_raw_at_registration","timing","outcomes","seed"],
  "properties":{
   "card_id":{"type":"string"},"family_id":{"type":"string","description":"assigned by rule (R-23)"},"rule_id":{"type":"string"},
   "revision":{"type":"integer","minimum":1},"class":{"enum":["CARD-O","CARD-P"]},
   "claim":{"type":"string","description":"verbatim claim text (§8.4)"},"claim_type":{"enum":["outperformance","protection","diversification"]},
   "label":{"type":["string","null"],"description":"the text displayed with the verdict, byte-identical to the rule's label"},
   "build_status_on_pass":{"enum":["BUILD_NOW","BUILD_AS_INSURANCE"]},"tier":{"enum":["A","B","C"]},
   "created_utc":{"type":"string","format":"date-time"},
   "header_md5":{"type":"string","description":"md5 of the header fields, committed before the run"},
   "gate_package_version":{"type":"string","description":"the frozen v2 package (§7 gate.package.version)"},
   "gate_package_md5":{"type":"string","description":"gate.package.definitions_md5 at the freeze (§8.1.3)"},
   "hypothesis":{"type":"string"},"mechanism":{"type":"string","description":"the second-moment mechanism (red line P5)"},
   "rule":{"type":"string"},"parameters":{"type":"object"},"searched_parameters":{"type":"array","items":{"type":"string"}},
   "estimator":{"type":"string","description":"e.g. sma20; a change is a counted revision (R-30)"},
   "instrument_book":{"enum":["KRX_ETF_line","KRX_stock_book","KOSPI200_futures","mini_KOSPI200_futures","CME_micro_ES","US_shares_KIS","KRX_listed_SP500_ETF","crypto_venue","FX_KRX_USD_futures","FX_broker_spot","multi_line"],
                      "description":"R-26; KRX_stock_book is never a market-gross scalar; KRX_listed_SP500_ETF only under D5"},
   "instrument_lines":{"type":["array","null"],"items":{"type":"object","required":["market","instrument_book"],
      "properties":{"market":{"type":"string"},"instrument_book":{"type":"string"}}}},
   "rebalance":{"enum":["daily","weekly","monthly"]},
   "no_trade_band":{"enum":[0.0,0.10],"description":"0.10 only on KRX_stock_book and US_shares_KIS (R-26)"},
   "notional_nav":{"type":"number","exclusiveMinimum":0,"description":"KRW; = sleeves.<market>.notional_nav at commit (R-26)"},
   "nav_fx":{"type":["object","null"],"properties":{"series":{"type":"string"},"history":{"type":"string"},"conversion_instant":{"type":"string"},
      "role":{"enum":["acting_exposure","forward_sim"],"description":"the role of the book it values (R-19 rule 5)"}}},
   "fill_model":{"type":"string","description":"R-27, e.g. KRX_close_auction"},
   "roll_calendar":{"type":["object","null"],"description":"futures books only"},
   "costs":{"type":"object","required":["per_side","floor","stress","stress_line"],
      "properties":{"per_side":{"const":"read_from_gate"},"floor":{"const":"tick_floor"},"stress":{"const":2.0},"stress_line":{"const":"printed"},
        "schedule":{"type":["array","null"],"items":{"type":"object","required":["cost_class"],
           "properties":{"from":{"type":"string","format":"date"},"to":{"type":"string","format":"date"},"cost_class":{"type":"string"}}}},
        "printed_lines":{"type":"array","items":{"type":"string"}}}},
   "data":{"type":"object","required":["source","value_status"],
      "properties":{"source":{"type":"string"},"value_status":{"enum":["official_close","vendor_close"]},"history_file":{"type":"string"},
        "reconciliation":{"type":"string"},"golden_tolerance":{"type":"string"},"saturday_sessions_before":{"type":["string","null"],"format":"date"}}},
   "history_first_close":{"type":"string","format":"date","description":"gate.evaluation.history_start of the card's market (R-22)"},
   "data_span":{"type":"object","required":["start","end"],"properties":{"start":{"type":"string"},
      "end":{"type":"string","format":"date","description":"the last official close before the header commit; never 'latest'"}}},
   "cash_convention":{"type":"object","required":["returns","cash_series"],
      "properties":{"returns":{"const":"excess"},"cash_series":{"type":"string"},"day_count":{"const":"act_365"}}},
   "episode_rule_version":{"type":"string"},
   "start_band":{"type":["object","null"],"required":["shape","starts","require"],
      "properties":{"shape":{"enum":["default","R-06_KR","decade_spaced"]},"from":{"type":"string"},"to":{"type":"string"},
        "step":{"enum":["month","decade"]},"starts":{"type":"integer","minimum":1},
        "require":{"type":"object","properties":{"no_reject":{"const":true},"pass_share_min":{"enum":["2/3","4/5"]}}}}},
   "midpoint_halves":{"type":["object","null"],"required":["split","split_date","require"],
      "properties":{"split":{"const":"calendar_midpoint"},"split_date":{"type":"string","format":"date"},"require":{"const":"no_reject"}}},
   "gating_lines":{"type":["object","null"],"additionalProperties":{"type":["string","object"]}},
   "regime_lines":{"const":"from_R20_tags"},
   "primary_oos_line":{"type":"string"},
   "printed_lines":{"type":"array","items":{"type":"string"}},
   "comparator":{"enum":["S_same_average_exposure","overlay_off"]},
   "benchmarks":{"type":"array","items":{"enum":["buy_and_hold","overlay_off","static_same_avg_exposure","ewma_derisk","current_recommended_book"]}},
   "checks":{"type":"string","description":"gate_package_<version>"},
   "claim_lines":{"type":["array","null"],"items":{"type":"object"}},
   "pooling_rule":{"type":["object","null"]},
   "ledger_hash_at_registration":{"type":"string"},"N_raw_at_registration":{"type":"integer","minimum":1},
   "timing":{"type":"object","required":["decision","inputs"],"properties":{"decision":{"const":"close_t_earn_t_plus_1"},"inputs":{"type":"object"}}},
   "live_feeds":{"type":["array","null"],"items":{"type":"string"}},
   "outcomes":{"type":"object","description":"what PASS, INSUFFICIENT_DATA and REJECT lead to"},
   "owner_decisions":{"type":"object","description":"owner-decision keys the card depends on, with their values"},
   "seed":{"type":"integer"}}}}}
```

```json
{"$id":"quantgen/model_card.macro.v2.0","type":"object",
 "allOf":[{"$ref":"model_card_header.macro.v2.0#/$defs/fields"}],
 "required":["schema","schema_version","read_only","generated_at_utc","knowledge_utc","git_hash","config_hash","data_snapshot_id",
             "verdict","verdict_reason","caps_applied","verdict_at_f1","verdict_at_f_neff","disposition","first_failed_check","permitted_fix",
             "ledger_hash_at_run","N_raw","N_clusters","N_equiv","N_hat_linear","N_eff","E_max_sim","V_null","V_trials","selection_factor",
             "power","timing_profile","episodes","start_band_results","midpoint_halves_results","regime_line_results","gjr_null_pct",
             "costs_per_side","cost_stress","tests","printed","lag_audit_violations","results_md5"],
 "properties":{
  "schema":{"const":"quantgen.model_card.macro"},"schema_version":{"const":"2.0"},"read_only":{"const":true},
  "generated_at_utc":{"type":"string","format":"date-time"},"knowledge_utc":{"type":"string","format":"date-time"},
  "git_hash":{"type":"string"},"config_hash":{"type":"string"},"data_snapshot_id":{"type":"string"},
  "verdict":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
  "verdict_reason":{"type":["string","null"],"description":"a §8.1.1 reason code or the failed check's id"},
  "caps_applied":{"type":"array","items":{"type":"string"}},
  "verdict_at_f1":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
  "verdict_at_f_neff":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
  "disposition":{"enum":["RECOMMENDATION","BUILD_AS_INSURANCE","INVARIANT_STEP","SPECIFICATION_ONLY","FORWARD_SIM","REFUSAL_BOOK","DESCRIPTIVE"]},
  "first_failed_check":{"type":["string","null"]},
  "permitted_fix":{"enum":[null,"widen_grid","lengthen_holding","extend_history","repair_rerun"]},
  "ledger_hash_at_run":{"type":"string"},
  "N_raw":{"type":"integer","minimum":1},"N_clusters":{"type":"integer","minimum":1},"N_equiv":{"type":"number","minimum":1},
  "N_hat_linear":{"type":"number","minimum":1},"N_eff":{"type":"number","minimum":1},"E_max_sim":{"type":"number"},
  "V_null":{"type":"number","exclusiveMinimum":0},"V_trials":{"type":["number","null"]},
  "selection_factor":{"type":"object","required":["value","rule","alt_value"],
     "properties":{"value":{"type":"number","minimum":1},"rule":{"const":"computed_by_step3"},"alt_value":{"type":"number","minimum":1}}},
  "power":{"type":"object","required":["se_hac","se_blk250","se_plateau","mde80","power_at_0p05","power_at_0p10"],
     "properties":{"se_hac":{"type":"number"},"se_blk250":{"type":"number"},"se_plateau":{"type":"number"},"se_curve":{"type":["object","array"]},
       "mde80":{"type":"number"},"power_at_0p05":{"type":"number"},"power_at_0p10":{"type":"number"},"pc3_power_at_0":{"type":["number","null"]},
       "years_to_detect_0p05":{"type":["number","null"]},"underpowered":{"type":"boolean"}}},
  "timing_profile":{"type":"object","required":["lags","strict","LP","LF","FR","label","live_feeds"],
     "properties":{"lags":{"type":"array","items":{"type":"object","required":["L","dSR","dMDD","dES21","timing_class"],
         "properties":{"L":{"type":"integer","minimum":-1,"maximum":3},"dSR":{"type":"number"},"dMDD":{"type":"number"},"dES21":{"type":"number"},
           "lag_audit":{"type":["object","null"]},"timing_class":{"enum":["VALUE","NON-COMPLIANT","COMPLIANT"]}}}},
       "strict":{"type":["object","null"]},"LP":{"type":"number"},"LF":{"type":["number","null"]},"FR":{"type":["number","null"]},
       "label":{"enum":["robust","timing_fragile"]},"live_feeds":{"type":"array","items":{"type":"string"}}}},
  "episodes":{"type":"array","items":{"type":"object","required":["peak","trough","depth","open"],
     "properties":{"peak":{"type":"string","format":"date"},"trough":{"type":"string","format":"date"},"depth":{"type":"number"},
       "window":{"type":"array","items":{"type":"string","format":"date"}},"benefit_vs_S":{"type":["number","null"]},"share":{"type":["number","null"]},
       "regime_tags":{"type":"object"},"post_trough_63":{"type":["number","null"]},"open":{"type":"boolean"}}}},
  "cost_episodes":{"type":"array","items":{"type":"object"}},
  "pc4_section_8_6":{"type":["object","null"]},
  "start_band_results":{"type":["object","null"],"required":["starts","verdicts","n_pass","n_starts","n_reject","floor_pass"],
     "properties":{"starts":{"type":"array","items":{"type":"string"}},"verdicts":{"type":"array","items":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]}},
       "n_pass":{"type":"integer","minimum":0},"n_starts":{"type":"integer","minimum":1},"n_reject":{"type":"integer","minimum":0},"floor_pass":{"type":"boolean"}}},
  "midpoint_halves_results":{"type":["object","null"],"required":["h1","h2"],
     "properties":{"h1":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},"h2":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]}}},
  "regime_line_results":{"type":"array","items":{"type":"object","required":["line","span","verdict","gated"],
     "properties":{"line":{"type":"string"},"span":{"type":"string"},"verdict":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
       "numbers":{"type":"object"},"gated":{"type":"boolean"}}}},
  "gjr_null_pct":{"type":["number","null"],"minimum":0,"maximum":100},
  "costs_per_side":{"type":"object","required":["table_bp","floor_bp","applied_bp"],
     "properties":{"table_bp":{"type":"number"},"floor_bp":{"type":"number"},"applied_bp":{"type":"number"},
       "stress_line":{"type":["object","null"]},"roll_cost_line":{"type":["object","null"]}}},
  "cost_stress":{"const":2.0},
  "claim_line_results":{"type":["object","null"],"properties":{"stacked_dMDD":{"type":"number"},"band":{"type":"array","items":{"type":"number"}},"pass":{"type":"boolean"}}},
  "pooling":{"type":["object","null"],"properties":{"rule":{"type":"string"},"n_onsets_own":{"type":"integer"},"n_onsets_pooled":{"type":"integer"}}},
  "snooping":{"type":["object","null"],"properties":{"n_variants":{"type":"integer"},"share_dMDD_ge_3pp":{"type":"number"},"deflated_prob_sr":{}}},
  "settling_run":{"type":["object","null"],"properties":{"span":{"type":"string"},"verdict":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
     "pc1_prime_1x":{"type":"boolean"},"pc1_prime_2x":{"type":"boolean"},"starts":{"type":"array","items":{"type":"string"}},
     "n_pass":{"type":"integer"},"n_starts":{"type":"integer"},"n_reject":{"type":"integer"},"midpoint_halves":{"type":["object","null"]}}},
  "contracts_path":{"type":["array","null"]},
  "forecast_eval":{"type":["object","null"],"properties":{"qlike_mcs_p":{"type":"object","additionalProperties":{"type":"number"}},
     "mse_mcs_p":{"type":"object","additionalProperties":{"type":"number"}},"christoffersen_p":{"type":["number","null"]},"es_z2":{"type":["number","null"]},
     "fan_pit_p":{"type":["number","null"]},"vol_of_vol":{"type":["number","null"]},"dMDD_vs_sma20":{"type":["number","null"]},"dSR_vs_sma20":{"type":["number","null"]}}},
  "forward_record":{"type":["object","null"],"description":"falsification alarms only (R-25); can never raise the verdict","properties":{
     "start_utc":{"type":"string","format":"date-time"},"first_registered_utc":{"type":"string","format":"date-time"},"months":{"type":"number"},
     "dSR_vs_S":{"type":["number","null"]},"dES21":{"type":["number","null"]},"dMDD":{"type":["number","null"]},"cusum_S":{"type":["number","null"]},
     "alarms":{"type":"array","items":{"type":"object"}},"switches":{"type":["integer","null"]},"switch_p99":{"type":["number","null"]},
     "lag_audit_violations":{"type":"integer","minimum":0},"demoted":{"type":"boolean"},"demotion_reason":{"type":["string","null"]},
     "honesty_line":{"type":"string"},"missed_decisions":{"type":"integer","minimum":0},"gaps":{"type":"array","items":{"type":"object"}}}},
  "tests":{"type":"object","description":"one entry per gate step (1-9) and per protective check (§8.7); the key set is closed, and so is every entry whose fields a rule enumerates (R-21, R-22, R-23, R-24)","properties":{
     "step1":{"type":"object"},"step2":{"type":"object"},
     "step3":{"type":"object","properties":{"deflated_dSR":{},"at_N_raw":{},"at_N_hat_linear":{},"borderline":{},"break_even_N":{},"z_check":{},"by_q":{},"dsr_vs0":{},"psr_vs_S":{},"selection_factor":{},"pass":{}}},
     "step4":{"type":"object","properties":{"pbo":{},"winner_loses_share":{},"pbo_null":{},"slope":{},"n_configs":{}}},
     "step5":{"type":"object"},"step6":{"type":"object"},"step7":{"type":"object"},"step8":{"type":"object"},"step9":{"type":"object"},
     "PC1p":{"type":"object","properties":{"legs":{"type":"array","items":{"type":"object","properties":{"h":{},"dES":{},"z":{},"p":{},"p_adj":{},"pass":{}}}},
       "two_x":{"type":"array","items":{"type":"object","properties":{"h":{},"dES":{},"z":{},"p":{},"p_adj":{},"pass":{}}}}}},
     "PC2":{"type":"object","properties":{"ratio_daily":{},"ratio_horizon":{},"ci90":{},"horizon_used":{},"pass":{}}},
     "PC3":{"type":"object","properties":{"dSR":{},"p10":{},"pPW":{},"block_PW":{},"p_ni":{},"p_adj":{},"point_2x":{},"pass":{},"p_lw":{},"p_hac":{},"block":{},"n_blocks":{}}},
     "PC4":{"type":"object","properties":{"positive":{},"n":{},"max_share":{}}},
     "PC5":{"type":"object"},"PC6":{"type":"object"},"PC7":{"type":"object"}}},
  "printed":{"type":"object","description":"never gated","properties":{
     "dMDD":{},"dCDaR95":{},"dES99":{},"bands":{},"placebo_panel":{},"tuw":{},"reentry_lag":{},"post_trough":{},"rolling_5y":{},
     "with_risk_layer":{},"lo_sr_20":{},"lo_sr_all":{},"by_q":{},"hl_haircut":{},"exec_variants":{},"overnight_intraday":{},
     "turnover_by_regime":{},"stress_cost":{},"roll_cost":{},"ban_basis":{},"fill_tracking_error":{},"binding_share":{},
     "binding_shares":{},"n_halts":{},"persistence_check":{}}},
  "lag_audit_violations":{"const":0,"description":"L >= 1 and strict rows only (R-34)"},
  "results_md5":{"type":"string"}},
 "unevaluatedProperties":false}
```

**Validation rules (T-SCHEMA-02, T-CARD-01, T-BOOK-01).**
- **Refused headers:** a header without `ledger_hash_at_registration`; one missing any of `instrument_book`, `rebalance`, `no_trade_band` or `notional_nav`, or whose `notional_nav` differs from `sleeves.<market>.notional_nav` at commit; a stock book used as a market-gross scalar; a futures line whose one contract exceeds 5% of `notional_nav`; a non-KRW book without `nav_fx`; a header that declares `selection_factor` or any other result field; an acting long-sample card whose `start_band` or `midpoint_halves` is null (R-22; both are null on other cards).
- **Dispositions:** `disposition ∈ {RECOMMENDATION, BUILD_AS_INSURANCE}` iff `verdict = PASS`. On a PASS, `build_status_on_pass = BUILD_NOW` gives RECOMMENDATION and `BUILD_AS_INSURANCE` gives BUILD_AS_INSURANCE (a build status, not a verdict; §8.1.2). BUILD_AS_INSURANCE requires `class = CARD-P` and a non-null `label`. `INVARIANT_STEP` is reserved for R-31 (binding share ≤ 0.10).
- **Costs:** the header's cost policy (`costs`: read from the gate, tick floor, stress 2.0, with an optional effective-dated `schedule` that may only raise a cost) resolves into `costs_per_side` and `cost_stress`.
- **Selection factor and verdicts:** `selection_factor` is computed by `step3()` (R-23); `verdict_at_f1` and `verdict_at_f_neff` are both printed, and `verdict` is the one at the binding f: the frozen overlap rule, at the maximum over the row-set readings (R-23).
- **The Kish N̂ is never a field.** `N_hat_linear` is the linear eq. 9 value, printed as a bound.

### 6.6 `governance_event` (one JSON line per event in `governance_events.jsonl`; §3.8, §3.9)

Every HALT and re-arm, book-state change, demotion, package freeze or redesign, header commit, owner ruling, calendar or notional change, R-15 admissibility re-weighting, R-31 binding-share recompute, change of a derived binding (R-19 rule 5), forward-record reset and verdict-integrity failure writes one line. Each line carries the md5 of the previous line (`prev_row_md5`, null only on the first), as `gate/acceptance_runs.jsonl` does; the chain is verified at app start (T-OBS-05). `core/rules` (M0) owns the appender; T-OWNER-01 writes the first event.

```json
{"$id":"quantgen/governance_event.v2.0","type":"object",
 "required":["schema","schema_version","event_id","utc","kind","book_id","rule_id","key","actor","reason","refs","prev_row_md5"],
 "properties":{
  "schema":{"const":"quantgen.governance_event"},"schema_version":{"const":"2.0"},
  "event_id":{"type":"string"},"utc":{"type":"string","format":"date-time"},
  "kind":{"enum":["halt","rearm","book_state","demotion","package_freeze","package_redesign","header_commit","owner_ruling","calendar_change",
                  "notional_change","admissibility_reweight","binding_share_recompute","binding_change","record_reset","verdict_integrity"]},
  "book_id":{"type":["string","null"]},"rule_id":{"type":["string","null"]},"key":{"type":["string","null"]},
  "old":{"description":"the value before the event (any JSON type)"},"new":{"description":"the value after the event (any JSON type)"},
  "actor":{"enum":["owner","operator","runtime","harness","council"]},
  "reason":{"type":"string"},"refs":{"type":"array","items":{"type":"string"}},
  "prev_row_md5":{"type":["string","null"],"description":"md5 of the previous line; null only on the first line"}}}
```

Example line (a book's first arming):

```json
{"schema":"quantgen.governance_event","schema_version":"2.0","event_id":"<uuid>","utc":"2026-10-02T06:41:05Z","kind":"book_state",
 "book_id":"recommended:KR","rule_id":null,"key":"engine_state","old":"DISARMED","new":"ARMED","actor":"runtime",
 "reason":"every acting input bound to the book fresh and past warm-up; calendars cover 60 sessions or more","refs":["§3.8"],"prev_row_md5":"<md5>"}
```

---

## 7. Rules-store entries (`core/rules` JSON store; YAML shown for readability)

**Where things live.**
- `config.py` keeps what it already holds: credentials by family, `~/.nextgen/ficc_cache`, the trading directory for the rules JSON, and the skill environment. It gains the macro artifact directory (**proposed**). Decision times are calendar lookups (R-20), not constants.
- The parameters below become **rule objects in the rules store**. The store's model is immutable and has no financial defaults, so every number below must be written explicitly.
- Validation enforces P2, the exposure basis, `min()` composition, the header fields of R-26 and the DO-NOT-BUILD list (R-33). The store's edit history is the revision log: an edit to an acting parameter is a new card revision (§8.4).
- Costs are **not** stored here. They are read from the gate's pre-registered table (P10); only the floor formula and the instrument metadata live here.
- **Owner-decision keys (C-8).** The Quick start table is the canonical statement of D1–D6 and their defaults; this listing does not restate them anywhere else. Each decision has one canonical key holding a plain scalar (the council default until the owner rules). The machine-readable registry is `owner_decisions.D<n> = {key, value, default, options, status, effective_from, rationale, refs}`; its `status` turns from `default` or `pending` to `owner_set` when the owner rules, which is a logged governance event (§8.10). A rule block that needs the value holds a reference `{ref: <canonical key>}`, resolved at load; a literal copy that differs from its key is refused (T-OWNER-01).
- **Rule objects** follow the schema of §7.1; the DO-NOT-BUILD shapes of §10.3 are predicates over it.
- **Rule blocks.** The config keys specified in R-19 to R-31 and R-34 are reproduced here verbatim: `calendars` (R-20), `data_contracts` (R-19), `vol_target.estimator_gate` (R-30), `fill_model` (R-27), `instruments` (R-26), `cards` (R-28, R-29, R-31), `monitoring` (R-25), and `gate.card_p_v2`, `gate.acceptance_test`, `gate.evaluation`, `gate.step3`, `gate.stats` and `gate.timing` (R-21–R-24, R-34). If a rule and this listing ever differ, the rule governs and this listing is fixed.

```yaml
version: "2.0.0"                         # v2.0: Quant Council edition (v1.2.0 → 2.0.0)
as_of: "2026-10-02"
read_only: true                          # no order path; nothing here can enable one
owner_decisions:                         # canonical statement: the Quick start table (C-8); status: default | owner_set | pending
  # one canonical key per decision, a plain scalar; a rule block holds {ref: <key>}, never a literal copy (T-OWNER-01)
  D1: {key: risk_layer.korea_caps.template, value: msci_25_50, default: msci_25_50, options: [domestic_max10_or_weight, msci_25_50, pair_35],
       status: default, effective_from: null, rationale: null, refs: []}
  D2: {key: risk_layer.drawdown.hard_stop.level, value: -0.15, default: -0.15, options: [-0.15, "-1.5*sigma_book"], status: default,
       effective_from: null, rationale: null, refs: [cards.R-31_step_down.hard_stop_level]}   # a ruling gives R-31 a counted revision
  D3: {key: families.reversal.calm_state_downweight, value: not_adopted, default: not_adopted, options: [not_adopted, reopen_after_krx_net_test],
       status: default, effective_from: null, rationale: null, refs: []}
  D4: {key: monitoring.false_demotion_budget_per_year, value: 0.10, default: 0.10, options: [tighten_only_le_0p10], status: default,
       effective_from: null, rationale: null, refs: []}
  D5: {key: sleeves.US.line, value: none, default: none, options: [CME_micro_ES, KRX_listed_SP500_ETF, none], status: pending,
       effective_from: null, rationale: null, refs: [instruments.us_line_choice, cards.R-28_trend_axis.us_sleeve, cards.R-29_US_FUT.us_sleeve_and_line]}
  D6: {key: gate.acceptance_test.cdar_guard.calibration, value: lowest_placebo_false_pass_rule, default: lowest_placebo_false_pass_rule,
       options: [lowest_placebo_false_pass_rule, professors_bootstrap_one_sided_5pct, executives_placebo_p10_margin, qf_blind_margin], status: default,
       effective_from: null, rationale: null, refs: []}   # frozen with the package (R2-C2); applied only if a negative control passes (R-21 9(d)); a ruling only before the first attempt
time:
  storage_tz: UTC
  decision: close_t_earn_t_plus_1        # QUANTGEN rule 02
  calendars: effective_dated             # R-20: decision_time_utc() (the scheduled close), close_print_bound_utc() and usable_at() are calendar lookups
  decision_instant: close_print_bound_utc   # macro_state.decision_utc and the lag-audit instant: KRX scheduled close + 30 s (06:00:30Z
                                            #   2015-06-15..2016-07-29, 06:30:30Z after); NYSE 16:00 ET + 30 s, DST-aware (R-20)
  markets:
    KR:  {tz: Asia/Seoul, session: calendars.KR, scheduled_close_utc: calendar_lookup, close_print_bound_utc: calendar_lookup,   # today 06:30:00Z / 06:30:30Z; never read as constants
          session_rules: calendars.KR, regime_tags: calendars.regime_tags_file, open_no_entry_minutes: 30}
    US:  {tz: America/New_York, session: ["09:30","16:00"], decision_utc: close_print_bound_utc, session_rules: calendars.US}   # scheduled close + calendars.US.close_print_bound_s
    CRYPTO: {tz: UTC, decision_utc: "00:00:00Z of d+1", venue_declared: true, annualisation_days: 365}   # the bar dated d closes at 00:00:00Z on d+1 (R-17; deferred)
  cross_tz_rule: "us_dated_D_usable_for_KR_close_K_iff_D_le_K_minus_1_and_available_at_le_decision"
  cross_market_rule: data_contracts.cross_market   # R-19
  business_days: {publication: fed_sifma_calendar, decision: exchange_calendar}
  publication:
    H15: {posted: "16:15 ET on the next Fed business day"}
    H10: {posted: "Monday 16:15 ET; next business day if Monday is a Federal holiday"}
    TREASURY_PAR: {posted: "usually by 18:00 ET on D", log_posting_time: true, us_close_decision_bdays: 1}
    VIXCLS: {official_close: "16:15 ET", us_close_decision_bdays: 1}
    BLS: {posted: "08:30 ET"}
    ECOS_USDKRW: {close_kst: "15:30", close_1500_until: "2016-08-01", snapshot_1530_from: "2026-07-06"}
calendars:                                           # R-20; data files in core/calendars/data/ (owner-signed)
  KR:
    close_kst: [{to: "2016-07-31", time: "15:00"}, {from: "2016-08-01", time: "15:30"}]
    closing_call_kst: [{to: "2016-07-31", window: ["14:50", "15:00"]}, {from: "2016-08-01", window: ["15:20", "15:30"]}]
    random_end: [{to: "2015-06-14", kind: conditional, print_tolerance_s: 30, triggered_extensions: from_krx_notice},
                 {from: "2015-06-15", kind: unconditional, max_s: 30}]   # bound = scheduled close + max_s, or + print_tolerance_s before 2015-06-15
    csat_session_kst: [{to: "2016-07-31", window: ["10:00", "16:00"]}, {from: "2016-08-01", window: ["10:00", "16:30"]}]   # pre-2016 window UNVERIFIED: confirm from the KRX notice at the M1 sign-off
    csat_closing_call_kst: [{to: "2016-07-31", window: from_krx_notice}, {from: "2016-08-01", window: ["16:20", "16:30"]}]   # R-27 CSAT snapshot; confirm at the M1 sign-off
    first_trading_day_open_kst: "10:00"
    saturday_sessions_before: "1998-12-12"
    saturday_session_close_kst: from_krx_notice       # owner-signed at M1; decision_time_utc and the bound exist for Saturdays
    excluded_sessions: [{venue: NXT, window_kst: ["15:40", "20:00"]}, {venue: KRX_after_market, from: "2026-09-14", window_kst: ["16:00", "20:00"]}]
  US: {close_et: "16:00", early_close_et: "13:00", holiday_set: NYSE, tz: America/New_York, close_print_bound_s: 30}   # M1 confirms the bound from logged print times
  JP: {close_jst: [{to: "2024-11-04", time: "15:00"}, {from: "2024-11-05", time: "15:30"}], close_print_bound_s: 0}   # default, judgment: the 60 s buffer covers dissemination
  CN: {close_cst: from_sse_notices, close_print_bound_s: 0}          # SSE 15:00 CST today; effective-dated, owner-signed at M1 (§9.5)
  HK: {close_hkt: from_hkex_notices, close_print_bound_s: 0}         # HKEX 16:00 HKT today (closing auction from the notices)
  TW: {close_tst: from_twse_notices, close_print_bound_s: 0}         # TWSE 13:30 TST today (earlier hours from the notices)
  holiday_sets: [KRX, NYSE, FED, SIFMA, CBOE, CME, JPX, SSE, HKEX, TWSE, ECOS]   # kept separate (QF2-A11); every registered input's obs_calendar
  regime_tags_file: core/calendars/data/kr_regime_tags.yaml
  change_control: {owner_sign_off: required, test_per_change: required}
  coverage: {min_sessions_ahead: 60, warn_at_sessions_left: 60, page_at_sessions_left: 20, outside_coverage: OPS_HALT}   # T-CAL-02
data:
  store: {append_only: true, bitemporal: true, as_of_reads: true, snapshot_id: md5_of_visible_content_hashes}
  knowledge_utc: {pinned_once_per_run: true, defaults_to_now: false, written_to_every_artifact: true}   # R-01, §3.5
  run_mode: {values: [live, backtest, replay], selects: [production_channel, history_channel]}        # §3.9, §4.2
  value_status_rank: [official_close, revised, first_release, vendor_close, vendor_derived, vendor_derived_across_gap, live_snapshot, provisional_intraday]
  vendor_close_in_backtests: only_if_card_header_declares_the_vendor_as_data_source   # §4.1
  ingest: {trigger: [pit_snapshot, publication_schedule], retries_min: [1, 5, 15, 60], decision_deadline: next_session_open_minus_30min,
           dedupe_key: [series_id, obs_date, vintage, source, value, value_status], first_seen_is_retrieved_at: true, fetch_log: fetch_log.jsonl, rows_mutated: never,
           posting_time_pollers: {TREASURY_PAR: "17:30-21:00 ET every 5 min", FRED_REPOSTS: last_updated}}   # deadline and poll window: default, judgment
  value_status_required_for_close_inputs: official_close
  require_session_match: true
  reject_rows_retrieved_before_close_plus_minutes: 10   # anchor: close_print_bound_utc of the row's session (R-01, T-FIX-01)
  reconciliation: {primary: [KIS, KRX], secondary: vendor, tol_index_bp: 1, tol_stock: exact,
                   on_mismatch: disputed_use_official_and_alert, auto_correct: false}
  stale_carry_flag: flat_ohlc_zero_volume_on_session_day
  daily_close_from_bars: forbidden
  bars: {stamp: bar_end, closing_auction_own_bar: true, available_at: bar_end_plus_latency}
  open_quality_flag: open_equals_prior_close
  fixtures: {post_close_only: true, min_minutes_after_close: 10, md5_per_file: true}
  fail_closed_on_missing_acting_input: true
  synthetic_for_acting_inputs: forbidden # 'auto' provider degrade -> MissingInput
  interpolate: false
  monthly_lag_method: calendar           # never positional
  vintages: {source: alfred, store_first_release: true, store_latest: true}
  derived_series_in_house: [sahm, yoy, taylor_range]   # a gap gives NaN
  named_series_required: true
  brent_series: {spot: DCOILBRENTEU, futures: BZ=F}
  usdkrw: {input: [ECOS_1530_CLOSE, USDKRW_1530_SNAPSHOT], proxy: DEXKOUS, proxy_timing: H10_publication, production_reads_dexkous: false,
           record_fx_regime: true}
  us10y: {production: US10Y_KIS_QUOTE, history: [TREASURY_PAR, DGS10], dgs10_strict_lag_bdays: 2, treasury_lag_bdays: 1, live_proxy_history: "^TNX"}   # lag counts document the usual case only; code uses usable_at() (first close after the publication instant); counted on NYSE days the DGS10 count leaks on Columbus and Veterans Day
data_contracts:                                      # R-19
  staleness_rule: schedule_aware                     # stale iff decision_utc > expected_available_utc(series, last_obs) + grace, where
                                                     #   expected_available_utc = when the NEXT obs after last_obs is due (R-19 step 3)
  grace_publication_bdays: 1                         # Resolution 7
  source_exceptions: core/calendars/data/source_skipped.yaml   # owner-signed, versioned
  on_failure:
    acting_exposure: {action: fail_closed, alert: true, halt_after_consecutive_decisions: 2, scope: bound_books,
                      book_counter_halt_after: 2}   # "more than one decision"; per (book, series) and per book (R-19 rule 4)
    risk_model:      {action: conservative_default, set: {hedge_credit_off: true},
                      hedge_failure_from: USD_LIVE_PROXY, operator_alert_after_missed_releases: 2, halt: never,
                      also_on: hedge_state_exception}
    context:         {action: label_stale}
    forward_sim:     {action: fail_closed_that_book, alert: true, halt: never}
    history:         {action: refuse_card_if_span_not_covered, alert: true, read_by_weight_decisions: false}
    risk_model_covariance: {action: carry_last_valid_terms_stale_then_drop, carry_max_decisions: 5, alert: true, halt: never,
                            sets_hedge_credit_off: false}   # default, judgment (R-19 rule 4)
    not_failures:    [warmup_before_first_armed_decision, disputed]
  cross_market: {rule: "close_print_bound_utc(m, D) + buffer < decision_utc", buffer_s: 60}    # buffer: default, judgment
  ranges: {abs_daily_return_max: {KOSPI: 0.30}, VIXCLS: [5, 150], yields_pct: {US_TREASURY: [-1, 20], KR_CALL_CD: [-1, 40]}}   # Korean rates ran at 16-25% in 1997-98
  roles:                                             # bindings per (series, consumer, books); a scalar acting entry means its
                                                     #   market's [recommended, specification] books (R-19 rule 5)
    KOSPI_OFFICIAL_CLOSE: {role: acting_exposure, books: [specification]}   # + the recommended book while verdict_filter admits R-06 KR (R-19 rule 5); vt enters it as 1.0 until then
    US_SLEEVE_OFFICIAL_CLOSE: {role: acting_exposure, books: []}      # no US sleeve while sleeves.US.line = none (D5)
    NAV_LINE_CLOSES: [{role: acting_exposure, consumer: nav, books: [recommended, specification], halt_after_consecutive_decisions: 3},
                      {role: forward_sim, consumer: nav, books: ["forward_sim:R-28", "forward_sim:R-29"]}]   # group (registry): each held line's official close, e.g. KODEX 200 (069500); a card's books bind their lines the same way (R-19 rule 5)
    SPX_OFFICIAL_CLOSE: [{role: forward_sim, consumer: R-28_R-29, books: ["forward_sim:R-28", "forward_sim:R-29"]},
                         {role: risk_model, consumer: corr63},
                         {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}]
    SOX_CLOSE: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}
    KODEX200_PDF: {role: acting_exposure, books: [recommended, specification], halt_after_consecutive_decisions: 5}
    KRX_MARKET_CAPS_005930_000660_KOSPI: {role: acting_exposure, books: [recommended, specification]}
    MOM_PAPER_LS_SERIES: {role: acting_exposure, books: [specification]}   # + the recommended book while verdict_filter admits R-03 (R-19 rule 5)
    DM_MKT_RET_24M: {role: acting_exposure, books: [specification]}        # R-04
    DM_MKT_VOL_126: {role: acting_exposure, books: [specification]}        # R-04
    NON_KR_INDEX_MONTH_END_CLOSES: {role: forward_sim, books: ["forward_sim:R-28"]}
    USD_LIVE_PROXY: risk_model                       # one named series (§4.2), read as a quote snapshot stamped <= the decision instant
    PCEPILFE: risk_model
    US10Y_KIS_QUOTE: [{role: risk_model, consumer: corr63}, {role: context, consumer: R-12_refusal_book}]   # production
    DGS10: [{role: risk_model, consumer: corr63_backtests}, {role: context, consumer: R-12_refusal_book}]   # strict H.15
    ASIA_INDEX_CLOSES: {role: risk_model, consumer: korea_covariance, action: risk_model_covariance}   # Nikkei, Shanghai, HSI, TAIEX
    DTWEXBGS: context                                # never acting
    DEXKOUS: context                                 # R-11 retired; labelled proxy
    ECOS_1530_CLOSE: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx_backtests, books: ["forward_sim:R-29"]}]   # nav_fx history (R-26)
    USDKRW_1530_SNAPSHOT: [{role: context, consumer: R-11_refusal_book}, {role: forward_sim, consumer: nav_fx, books: ["forward_sim:R-29"]}]   # nav_fx (R-26, R-29)
    BOK_CALL_RATE: history                           # R-22 cash leg (card harness only)
    US_RF: history                                   # R-22 cash leg (card harness only)
  unscheduled_delay: event_status_delayed
overlay:
  floor: 0.5
  cap: 1.0
  combine: min                           # R-02; a product-composed path raises
  floor_vs_vt_outside_halted: 0.5        # composed >= 0.5 x vt on every non-HALTED day (T-CAP-02)
  zero_only_in: [risk_layer, book_HALTED]           # per book (§3.8)
  books: [recommended, specification, forward_sim_per_card, refusal_display_only]
  recommended_dispositions: [RECOMMENDATION, BUILD_AS_INSURANCE, INVARIANT_STEP]   # the first two need verdict PASS; INVARIANT_STEP: R-31 at binding share <= 0.10
  stack_card: {when_de_risk_factors_ge: 2, class: CARD-P, spec: "§8.7"}   # R-02
base_weights:                            # R-15
  cross_market: {method: inverse_vol, returns: weekly, cov_acting: ewma_0.97, cov_printed: ledoit_wolf_156w, spans: markets_with_sleeves}   # no HRP, no min-variance; ERC only for multi-asset sleeves
  family: {admissible_if: {prior_min: 1, card_verdict_not: REJECT}, weight: one_over_K, range_prior: lower_bound,
           no_registered_prior: not_admissible, not_run_admissible_except: [ts_trend], reject_reweight: logged_governance_event}   # R-15
  tilt_requires_family_card_pass: true
vol_target:                              # R-06 (cap 1.0 permanent, no floor)
  KR: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, cap_permanent: true, exposure_basis: total,
       instrument_book: KRX_ETF_line, notional_nav: {ref: sleeves.KR.notional_nav}, rebalance: daily, no_trade_band: 0.0, fill_model: KRX_close_auction,
       card: {card_id: MACRO-R06-KR-ETF, build_status_on_pass: BUILD_AS_INSURANCE, conditions: see_R-06_card_korea, forward_record: falsification_only}}
  US: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, cap_permanent: true, exposure_basis: total,
       registered_card: {instrument_book: US_shares_KIS, verdict: REJECT, label: "REJECT (instrument: US shares via KIS, 50 bp, daily)", rerun: false},
       futures_card: cards.R-29_US_FUT}
  other_markets: {estimator: sma, window: 20, target_ann: null, cap: 1.0}   # pre-register per market on its card
  estimator_gate:                                    # R-30 (replaces v1.2 B5-only selection)
    acting_default: sma20                            # also the displayed baseline
    challenger: {name: comb, definition: "0.5*(gjr_t + log_har_range)", books_allowed: [KRX_ETF_line, KOSPI200_futures,
                 mini_KOSPI200_futures, CME_micro_ES], books_refused: [KRX_stock_book]}
    fit: {window: expanding, min_years: 10, refit_every_origins: 21}
    range_proxy: {KR: overnight_sq_plus_garman_klass, US: parkinson}
    stage1: {horizon_days: 21, tests: [fhs_var_exceedance_h21, fan_pit_h21, christoffersen_cc], printed: [kupiec_1d, cc_1d_95_99, es975_z2]}
    stage2: {loss: qlike, mcs_level: 0.90, stat: T_max, block: "max(10, 2h)", resamples: 2000, seed: 11, mse_mcs: printed}
    stage3: {objective: min_vol_of_vol_rolling63, eligibility: [dSR_noninferior_vs_sma20_delta_0p10, dMDD_vs_sma20_ge_0, pc2_le_0p90],
             ties: overlapping_bootstrap_ci, tie_break: simplest_surviving,
             complexity_order: [sma20, ewma094, ewma097, garch_t, gjr_t, log_har_range, comb]}
    switch: {counted_revision: true, full_v2_card_p: true}
    fallback_to_sma20: {gjr_bounds: {persistence_max: 0.9999, nu: [2, 100]}, open_quality_max_share: 0.05,
                        flat_range_max_share: 0.05, window_sessions: 252}       # thresholds: default, judgment
    incumbent_calibration: {name: B5, var_level: 0.05, band: "+-2 binomial SE", min_origins: 200, pit: chi2_10_bins, pit_p_min: 0.01}
  annualisation_days: 252
  sigma: {returns: simple, ddof: 1, mean_adjusted: true, stale_carry_days: excluded_window_extends}   # R-06
  warmup: {min_valid_returns: 20, value: 1.0, status: warmup, counts_as_failure: false, only_before_first_armed_decision: true, after_armed: MissingInput, degenerate_sigma: MissingInput}   # T-VT-01
  display_labels: {rel: {method: trailing_756_quartiles}, abs: {method: expanding_full_history_quartiles, min_years: 10},
                   values: [calm, normal, elevated, stressed], filtered_only: true, acts: false,
                   per_label_coverage: reported, scoring: tick_loss}
  logged_alt_estimators: [asymmetric_slow_cut_fast_restore]   # BL-C04; max(sma20, implied) retired
families:
  momentum:
    own_vol_scale: {window: 126, target_ann: 0.12, cap: 1.0, floor: 0.0, min_obs: 126, exposure_basis: active,
                    series: paper_unit_gross_long_short, apply_to: sleeve_budget,
                    revisions: {2: {target: expanding_median_sigma126, min_obs: 252}, 3: {vs: "min(1, (0.12/sigma126)^2)"}}}
    dm_gate: {market_return_months: 24, market_vol_window: 126, vol_quantile: 0.6667, quantile_min_obs: 252,
              multiplier: 0.5, exposure_basis: active, books: [specification], label: "step 3 FAIL", a_provisional_route: closed, pooled_revision: none}
  reversal: {overlay: fixed_1.0, intraday_leg: false, calm_state_downweight: not_adopted}   # canonical key of D3 (Quick start)
  quality:  {overlay: fixed_1.0}
  flow:     {overlay: fixed_1.0}
  ts_trend: {signal: sign_12_1, rebalance: monthly, vol_window_months: 12, target_ann: 0.15, cap: 1.0, overlay_exempt: true,
             card: {class: CARD-O, claim: diversification, instrument_book: multi_line}}   # one declared line per market (R-14, R-26); target: default, judgment
weights_prior: see_R-15                  # 0-3 integers: admissibility filter and display only
prior_haircuts: {value: 0.49, momentum: 0.23, carry: 0.25, defensive: 0.0, multifactor: 0.18}   # one-sided (prof); live_sharpe_multiplier 0.60 (take 40% off) printed too
risk_layer:                              # core/quant/risk + core/engine
  korea_caps:
    lookthrough: {source: daily_etf_pdf, leveraged_multiplier: L}
    template: msci_25_50                 # canonical key of D1 (Quick start)
    templates:
      msci_25_50: {single_name_max: 0.225, names_above: 0.045, aggregate_max: 0.45, review: [quarterly, on_breach],
                   breach_single_name: 0.25, breach_aggregate: 0.50}   # targets bound g daily; a breach is above the hard levels after the action
      domestic_max10_or_weight: {single_name_max: "max(0.10, market_cap_weight)"}
      pair_35: {pair_max_share_of_sleeve_nav: 0.35}    # look-through, cash in the denominator (R-07 (3))
    active_single_name_cap_nav: 0.05     # w_i - g * b_capped_i <= 0.05 NAV
    active_bound: "0.05 / (s_i - b_capped_i) for every name with s_i > b_capped_i"   # R-07 (4)
    semis_max_share_of_sleeve_nav: 0.50  # default, judgment; look-through, cash in the denominator (R-07 (5))
    report_by_book: true                 # concentration.by_book (§6.1)
    meet_cap_order: [lower_etf_line_weight, ex_pair_basket_only_if_owner_and_stock_card_pass_and_limit_lock_flags]
    report: [pair_lookthrough_share, pair_risk_contribution]
  drawdown:
    reference: whole_book_nav            # per-market attribution printed
    composition: min                     # with the overlays (R-02)
    steps: cards.R-31_step_down          # -8% / -12% totals, 21-session dwell; specification book while the binding share > 0.10
    hard_stop: {level: -0.15, alt: "-1.5*sigma_book", reference: hwm_since_last_rearm, action: book_HALTED, class: RISK,   # level: canonical key of D2
                scope: own_book_nav, rearm: automatic, rearm_refused_sessions: 10, rearm_calendar: book_primary_market,
                rearm_resets: [hwm_hard, ref_step], post_rearm_cap: 0.5, post_rearm_sessions: 10, post_rearm_cap_in_min: true,
                idempotent_while_halted: true, log: governance_review_event, protection_claim: false}
  halt_scope: per_book                  # C-1: only the books whose own NAV, artifact or bound acting input failed (§3.8)
  halted_triggers:
    RISK: [hard_stop, risk_limit_breach]   # breach: re-arm after 10 sessions only once the post-action target weights meet the limit; no reference reset; post_rearm_cap 0.5 from the actual re-arm
    OPS: [lag_audit_violation, acting_field_schema_or_bounds_failure, acting_input_fail_closed_beyond_declared_misses,
          feed_heartbeat_loss_60s, acting_risk_layer_exception, whole_book_nav_unavailable_gt_2_decisions, calendar_coverage, operator_kill,
          acting_step_error_beyond_limit]   # run_error (§3.9)
  heartbeat: {loss_s: 60, blocks_new_intraday_entries: immediately, auto_rearm_after_restored_min: 5}   # default, judgment
  ops_rearm: {when: cause_cleared, operator_required_after: [lag_audit_violation, acting_field_schema_or_bounds_failure],
              reference_reset: false, post_rearm_cap: false}
  never_halt_on: [risk_model_input_stale_or_failing, hedge_state_exception, context_input_stale, disputed_input, warmup_input_before_first_armed_decision,
                  input_bound_only_to_other_books, display_or_context_field_validation_failure, context_log_or_event_calendar_validation_failure]
  korea_covariance_extra: [SHANGHAI, HSI, TAIEX, NIKKEI]   # synchronous or lagged returns
  hedge_state: {core_pce_yoy_threshold: 0.030, corr_window: 63, corr_threshold: 0.0, corr_pairs: date_aligned, lag: statistic_not_leg,
                stale_input: hedge_credit_off, exception: hedge_credit_off, usd_input: USD_LIVE_PROXY, reasons_field: flags.hedge_reasons,
                hedge_failure_daily: {equity_ret_lt: -0.015, usd_ret_lt: 0.0},
                hedge_failure_weekly: {equity_ret_lt: -0.02, usd_ret_lt: 0.0},
                fx_hedge_credit: {display_only: true, window_weeks: 26, credit_if_corr_lt: 0.0},
                stressed_covariance_from_turbulence: only_after_preregistered_win}
annotations:                             # core/engine/evaluator; no exposure effect (R-08)
  vix_ts: {condition: "VIXCLS >= VXVCLS", threshold: 1.0, tuned: false, clearing: raw_parity_flag, action: annotate_only,
           request_kis_spread_snapshots: true, from: "first decision after the 16:15 ET VIX close", switch_budget_per_year: 14.0}   # logging only (R-08); card switch triggers follow R-25
events:                                  # core/calendars; evaluator blocks on simulated entries only (R-10)
  us_cpi_nfp: {block_new_intraday_entries_et: ["08:25","10:00"], resume_et: "10:00"}
  us_leaky_releases_pre_minutes: 30
  fomc: {block_new_intraday_entries_et: ["13:45","15:00"], resume_rule: "VIX<pre14 else 15:30", pre_fomc_long: false}
  bok_decision: {kospi200_futures_block_kst: ["09:45","10:15"], equity_daily_change: none}
  bok_press_conference: {kospi200_futures_block_kst: ["11:00","11:45"], equity_daily_change: none}
  kr_open: {block_first_session_minutes: 30, window_kst: ["09:00","09:30"], late_open_window_kst: ["10:00","10:30"],
            late_open_days: [first_trading_day_of_year, csat]}   # = time.markets.KR.open_no_entry_minutes (R-10)
  kr_open_gap_event_types: [US_CPI, US_NFP, FOMC, HYPERSCALER_EARNINGS]
  multi_session_gap: {tag: gap_sessions, gap_sessions_min: 0, var_display_scale: "sqrt(max(n_us, 1))", report_separately: true, gross_rule: false}
  sidecar_cb: {block_new_entries_minutes_after_cb_reopen: 30, quotes_during_halt: indicative, gross_cut: false}
  daily_book_blackouts: false
  tags_change_weights: false
fill_model:                                          # R-27 (simulated book only)
  KRX: {snapshot: closing_call_start_minus_1min, snapshot_kst_since_2016-08-01: "15:19", fill: official_close, random_end_max_s: 30,
        fallback: post_close_session_UNVERIFIED, limit_price: tick_rounded_toward_prev_close,
        etf: {flag: LP_exempt_auction, inav_residual_flag_bp: 30}, limit_lock: non_fillable_at_close}
  NYSE: {snapshot_et: "15:50", fill: official_close_moc_equivalent}
  KOSPI200_futures: {trades_until_kst: "15:45", expiry_day_stop_kst: "15:20"}
  bars: {stamp: bar_end_utc, closing_auction_bar: separate, available_at: "bar_end + latency", daily_close_from_bars: forbidden}
instruments:                                         # R-26
  cost_floor: {formula: "max(table_rate, commission + 0.5*tick/price + tax_side)", commission_bp: 1.4,
               lower_than_table: forbidden}          # commission: EX2 quote; owner confirms vs broker schedule
  li_etf: {max_tick_bp_of_price: 10, cost_class: KRX_LI_ETF, lookthrough_multiplier: L, eligibility_rules: metadata}
  header_required: [instrument_book, rebalance, no_trade_band, notional_nav, fill_model, nav_fx_if_non_krw]
  notional_source: sleeves.<market>.notional_nav     # owner-signed, effective-dated; a card never declares its own
  no_trade_band: {allowed_values: [0.0, 0.10], allowed_books: [KRX_stock_book, US_shares_KIS], tuned: false}
  futures_granularity: {max_contract_share_of_sleeve: 0.05,
                        contract_notional_krw: {KOSPI200: 280e6, mini_KOSPI200: 56e6, CME_micro_ES: 52e6, as_of: "2026-10-02", use: header_check_only}}   # backtests compute notional PIT: price x effective-dated multiplier x nav_fx
  market_scalar_on_stock_book: refused
  us_shares_50bp: single_names_only
  printed_lines: [exec_variants_ABC, overnight_intraday, turnover_by_regime, stress_cost_line, roll_cost, ban_period_basis]
  stress_line: {multiplier: "clip(sigma20/sigma_median, 1, 5)", etf_close_extra_bp_if_abs_ret_ge_3pct: 10, gated: false}
  us_line_choice: {ref: sleeves.US.line}            # D5 (Quick start): CME_micro_ES, KRX_listed_SP500_ETF or none
refusal_books:                           # R-11, R-12: REJECT recorded; display only; read by no book; off the re-gate queue
  S1_krw: {lookback_obs: 20, threshold_dlog: 0.03, multiplier: 0.75, target: KR_market_gross, one_sided: true, verdict: REJECT, regate_queue: false}
  S2_rates: {lookback_obs: 20, threshold_pp: 0.40, multiplier: 0.5, target: US_duration_sensitive_gross,
             excludes: [momentum, ls_factor_sleeves, KR], verdict: REJECT, regate_queue: false}
cards:                                   # R-28, R-29 (FORWARD-SIM) and R-31 (specification book until PASS)
  R-28_trend_axis:
    rule: {signal: month_end_close_below_sma10m, multiplier_below: 0.5, multiplier_above: 1.0,
           decided: month_end_close, applies: next_month, composition: min, exposure_basis: total}
    claim: "slow-bear protection via the volatility state"
    judged: {incremental_on: vol_targeted_book, comparator: S_of_VT_book, claim_line_stacked_dMDD_min_pp: 3.0,
             claim_line_failure: cap_INSUFFICIENT}
    pooling: {decluster_gap_months: 10, indices: [SPX, N225, HSI, DAX, FTSE100, TAIEX], own_market_veto: true,
              declared_before_any_run: true}
    markets_allowed: [US, other_non_korean]
    markets_refused: [KR]
    logged_trials_same_ledger: [BAND200]
    status: FORWARD_SIM
    us_sleeve: {ref: sleeves.US.line}                # D5 (Quick start); FORWARD-SIM while none
    instrument_book: CME_micro_ES                    # US instance: incremental on R-29's futures vt book
    rebalance: monthly
    no_trade_band: 0.0
    notional_nav: {ref: sleeves.US.notional_nav}
    fill_model: NYSE_moc
  R-29_US_FUT:
    card_id: MACRO-R06-US-FUT
    family: R-06                                     # one new trial in the R-06 ledger
    rule: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, floor: none, rebalance: daily, exposure_basis: total}
    instrument_book: CME_micro_ES
    cost_class: futures                              # 5 bp per side, read from the gate
    no_trade_band: 0.0
    notional_nav: {ref: sleeves.US.notional_nav}   # live only if one contract <= 5% of it (R-26 granularity floor, checked at the header commit)   # ~KRW 1bn; never declared on the card
    nav_fx: {series: USDKRW_1530_SNAPSHOT, history: ECOS_1530_CLOSE}
    episodes: {theta: 0.15}
    settling_run: {data: FF_daily_MktRF_1926-07_to_2026-08, cost_bp: 5, pc1_prime_at: [1x, 2x],
                   starts: decade_spaced, pass_share_min: from_band_shape, no_reject_at_any_start: true,
                   no_reject_in_midpoint_halves: true, full_span_must_pass: true}
    promotion: {requires: [us_sleeve_or_owner_line, settling_run_pass, v2_package_pass]}
    us_sleeve_and_line: {ref: sleeves.US.line}       # D5 (Quick start): CME_micro_ES, KRX_listed_SP500_ETF or none
    logged_trials: [monthly_50bp, band_0p10_50bp]
    status: FORWARD_SIM
  R-31_step_down:
    steps: [{dd: -0.08, mult: 0.5}, {dd: -0.12, mult: 0.5, evaluator_block_new_entries: true}]   # totals, non-cumulative
    dwell_sessions: 21
    step_reference: running_peak_since_last_reset    # resets at dwell end and at re-arm
    hard_stop_reference_resets_at_dwell_end: false   # R-07 reference; resets only at re-arm
    composition: min
    denominator: whole_book_nav
    binding_share_threshold: 0.10                    # > 0.10 -> specification book until PASS
    binding_share: {book: recommended_without_steps, span: declared_history, computed_at: [header_commit, composition_change],
                    window: full_never_trailing, compare: "n_bind / n_sessions > 0.10", disposition_if_le: INVARIANT_STEP}
    judged: {incremental_on: declared_book_without_steps, comparator: S}
    claim: "protection in persistent drawdowns; time-boxed; no Sharpe claim"
    hard_stop_level: {ref: risk_layer.drawdown.hard_stop.level}   # D2 (Quick start); never a literal copy (T-OWNER-01)
    status: SPECIFICATION_BOOK
sleeves:                                 # notional_nav: owner-signed, effective-dated, one value per sleeve (R-26); set before the M7 header commit
  US: {line: none, notional_nav: null}   # line: canonical key of D5 (pending)
  KR: {notional_nav: null}
context_log:
  probit: {alpha: -0.6045, beta: -0.7374, spread: "GS10 - TB3MS (bond-equivalent), monthly"}
  taylor_family: {r_star: [0.5, 1.0, 2.0], gap: [okun_2x, cbo], a: [0.5, 1.0], pi: core_pce_yoy, pi_star: 2.0}
  existing_sheet: {all_items_context_unless_acting: true, zscores: causal_display_only, regime_read: removed_if_regime_model_else_text_only}
  vintages_required: true
  additions: [leverage_and_flow, vrp, live_implied_vol_snapshots, turbulence_and_absorption_ratio]
breaks:                                  # R-18
  policy_trigger: official_framework_change      # shrink macro-conditioned multipliers to 1.0 + start a forward record
  statistical_trigger: log_only                  # active only after the 1990-2026 false-break test
  scale_reanchor: declared_events_only           # v1.2's 2x-3y-median/60-session rule is a logged flag only
  bocpd: {hazard: "1/250", prior: declared, log_only: true, displayed: false}
  market_structure_log: true
monitoring:                                          # R-25
  denominator: whole_book_nav
  operational_triggers: [lag_audit_violation, acting_param_edit_outside_revision, provisional_or_stale_input_reached_acting_decision,
                         switches_gt_p99_poisson_negbin, operator_kill_of_forward_books,
                         decision_gaps_gt_10pct_rolling_12m]          # immediate; outside the budget (§3.8, §8.8 (b))
  catastrophic:
    card_p: {all_of: ["fwd_dMDD_vs_S <= 0", "fwd_dES95_21_vs_S <= 0", "fwd_dSR_12m_vs_S < design_p2.5"], window_months: 12}
    card_o: {any_of: ["gap6m_comparator_minus_on_book_nav > 2 * sigma_design", "fwd_dSR_12m_vs_comparator < design_p2.5"]}
  cusum: {frequency: monthly, k: 0.25, h: bootstrap_calibrated, in_control_arl_years_min: 20}
  false_demotion_budget_per_year: 0.10              # canonical key of D4 (owner_decisions.D4, Quick start)
  false_demotion_budget_split: {rule: equal_across_active_cards, fixed_at_record_start: true, recalibrated_on_new_card: false}
  budget_check: {panel: circular_shift, shifts: 20, min_offset_sessions: 252, short_sample: floor_T_over_252_offsets, seed: 11}
  cusum_calibration: {bootstrap: stationary, resamples: 2000, seed: 11, mean_block_months: 12}   # default, judgment
  switch_model: {default: poisson, negbin_if_lr_test_p_lt: 0.05}                                   # default, judgment
  demotion_verdict: {operational_or_integrity: REVISE, catastrophic_or_cusum: REJECT}              # default, judgment
  lockout_scope: family_x_market
  nav_unavailable_ops_halt_after_decisions: 2
  forward_record_can_raise_verdict: false
  regate_up_only_on_new_history: {continuous: new_objective_episode, discrete: tier_onset_count}
  lockout_months_after_demotion: 6
  bull_lag_alone_demotes: false
gate:                                    # the existing nine-step gate plus the frozen v2 package (§8; R-21-R-24, R-34)
  package: {version: "2.0.0", definitions_md5: written_at_freeze, acceptance_report_md5: written_at_freeze, frozen_utc: written_at_freeze,
            manifest: [gate_blocks_canonical_json, harness_source_files, acceptance_fixture_md5s, seeds],
            anchor: repository_commit_before_any_card_run, rehash_at_every_card_run: true}   # §8.1.3; T-CARD-02
  frozen_before_first_card_run: true
  card_classes: [CARD-O, CARD-P]
  card_p_v2:                                         # R-21
    comparator: S_same_average_exposure              # m_bar x overlay-off; constant; same days; uncosted
    pc1_prime: {horizons_sessions: [21, 126], es_level: 0.95, overlapping: true, gate_cost: 1x,
                point_must_exceed: 0.0, p_max: 0.10, p_form: uncentred_bootstrap_percentile, z_printed: true, bootstrap: stationary, mean_block_sessions: 250,
                resamples: 2000, seed: 11, two_x: revise_path, monthly_cards_horizons_months: [1, 6]}
    pc2: {tail_quantile: 0.05, ratio_max: 0.90, default_horizon: daily, ci: printed,
          horizon_matched: {adopt_if_placebo_false_pass_max: 0.10, placebos_per_card: 20, decided_in: acceptance_test}}
    pc3: {delta: 0.10, p_max: 0.10, p_ni: "max(p_block10, p_block_max21_PWpsi)", point_below_minus_delta: {at_1x: REJECT, at_2x: REVISE}}
    pc4: {episodes: objective_market_own, min_positive: 3, max_share: 0.50}
    pc5: {years_positive_min: 0.60}
    pc6: {neighbourhood: moore_8_or_2_axis_neighbours, keep_share_min: 0.50}
    pc6_axes:                                        # frozen per rule type; a card never declares axes or steps (default, judgment)
      vol_target: {window_mult: [0.5, 1, 2], target_mult: [0.75, 1, 1.25]}           # R-06 KR: {10, 20, 40} x {0.15, 0.20, 0.25}
      threshold_rule: {threshold_mult: [0.75, 1, 1.25], lookback_or_dwell_mult: [0.5, 1, 2]}
      monthly_trend_rule: {lookback_months: [8, 10, 12]}                              # one axis, 2 neighbours (QF5)
    pc7: {discrete_min_onsets: 30, decluster_gap: own_lookback, continuous_min_objective_episodes: 5, min_sessions: 882}
    caps: {do_no_harm: INSUFFICIENT_DATA, timing_fragile: INSUFFICIENT_DATA, estimator_calibration_fail: REVISE}   # SMA20: B5; challenger: R-30 Stage 1
    underpowered: {applies_if_mde80_gt: 0.10, converts: [pc3_p_value], never_waives: [pc1_prime, pc2, pc3_point]}
    gjr_null: {paths: 1000, seed: 11, mean: constant}                 # printed only
  acceptance_test:
    placebo: {construction: circular_shift_of_multiplier, per_family: 300, per_family_false_pass_max: 0.10,
              tau_min_sessions: 252, per_card: 20, per_card_passes_max: 2, seed: 11,
              per_card_tau: "round(252 + k*(T - 504)/19), k = 0..19", pass: pc1_prime_both_legs_1x_with_f,
              population: drafted_card_p_headers, family_pooling: own_series_300_per_card, on_excess: acceptance_fails}   # Q5 open (§8.10)
    negative_controls: [US_VT_5d_50bp, US_VT_10d_50bp, post_shock_day_0p5, post_shock_week_0p5, VT_sigma_lag_252]
    controls_allowed_verdicts: [REJECT, INSUFFICIENT_DATA]
    cdar_guard: {added_only_if_a_control_passes: true, calibration: lowest_placebo_false_pass_rule, fixed_margin_minus_5pp: withdrawn}   # calibration: canonical key of D6, frozen with the package (R2-C2)
    attempts_log: {path: gate/acceptance_runs.jsonl, append_only: true, hash_chain: prev_row_md5, listed_in_report: true,
                   counts_as: package_trial, printed_beside_every_verdict: true}   # R2-C3
    redesign: {max_per_package_version: 1, changes_limited_to: frozen_items_table, rationale_cites: [family_panels, negative_controls],
               fresh_seeds_fixed_before_run: true, per_card_excess: council_q5_only, failure_count: across_all_2x_versions_never_reset,
               after_second_failure: no_card_evaluated_under_v2_owner_notified}   # R2-C3; T-GATE-04
  evaluation:                                        # R-22
    episode_rule: {name: alternating_bear_bull, version: "1", prices: own_official_closes,
                   theta: {default: 0.20, KR: 0.20, US_SPX: 0.15}, low_vol_declared: [US_SPX],
                   others: {rule: "0.15 if long-run median SMA20 vol < 0.18 else 0.20", written_before_first_run: true},
                   window: first_return_after_peak_close_to_trough, sep_2026: asserted_not_an_episode}
    shock_type_table: "§8.6 named windows (printed only)"
    post_trough_window_sessions: 63                  # printed, not gated
    cost_episodes: {rebound_2009: ["2009-03-09", "2009-06-30"], rebound_2020: ["2020-03-23", "2020-06-08"],
                    h1_2026: ["2026-01-02", "2026-06-30"]}
    returns: excess
    cash: {KR: BOK_CALL_RATE, US: US_RF, other: registry_before_first_run}
    cash_day_count: act_365                          # default, judgment
    cash_rate_date: latest_rate_dated_on_or_before_previous_session   # R-22 rule 3; a closed day of the rate's own calendar carries the prior rate
    cash_units: {annual_rate: act_365, per_period_return: as_published}   # French RF is a per-period return (R2-C5)
    cash_read: frozen_card_snapshot_available_at_recorded_never_filtered   # role history; a missing cash day refuses the card
    start: first_close_plus_estimator_warmup
    history_start: {KR: "1997-04-01", default: first_close_of_frozen_fixture}   # fixed before the freeze; a card never truncates it
    span_end: {drafted_cards: data_cutoff, later_cards: last_official_close_before_header_commit}
    data_cutoff: {KR: "2026-10-02", US: "2026-10-01"}   # the last official closes in the frozen reference data (§9.3.1), fixed now; in the manifest
    start_band_shapes:                               # frozen; a card declares neither its band nor its pass share
      default: {months: 33, step: month, pass_share_min: "2/3"}
      R-06_KR: {from: "1997-05", to: "1999-12", step: month, starts: 32, pass_share_min: "2/3"}   # Resolution 1
      decade_spaced: {min_span_years: 80, starts: declared_start_then_january_of_each_decade, last_start_min_years_before_end: 10, pass_share_min: "4/5"}   # R-29
    stability_floor: {no_reject_at_any_band_start: true, pass_share_min: from_band_shape, compare: integer_counts,
                      no_reject_in_midpoint_halves: true, applies_to_every_shape: true}
    midpoint_halves: {split: calendar_midpoint_of_fixed_span, split_date_in_header: true}
    regime_lines: from_R20_tags
    primary_oos_line: declare_on_card
    risk_layer_in_card_books: {hard_stop: excluded_printed, caps: excluded_printed, except: card_claim_concerns_them}   # rule 6
  step3:                                             # R-23
    ledger: {required: true, hash: md5_canonical_json, research_phase_included: true, timing_class_required: true,
             family_id: by_rule_QC_modules, filing_cluster_rho: 0.5, appended_by: harness_only, hash_chain: prev_row_md5,
             hash_at: [registration, run]}
    basis: difference_series                         # rule minus comparator (overlay-off for CARD-O, S for CARD-P)
    n_gate: "max(N_clusters, N_equiv)"
    emax: {simulated_draws: 200000, seed: 11, below_2: exact_integral, from_2: bldp_closed_form}
    clusters: {linkage: average, rho_min: 0.5}
    variance: {default: V_null, se_null: median_lw_hac_of_family_trials, use_trials_if_independent_ge: 30, print_both: true}
    card_o_bar: 0.95
    card_p: {gated: false, selection_factor: bonferroni_N_eff, factor_one_if: config_fixed_before_any_run_on_span,
             overlap_rule: any_overlap, computed_by: step3, declared_on_header: refused, print_both: [f_1, f_N_eff],
             holm_across_variants: printed}
    row_set: {unit: distinct_configuration, key: [rule, params, estimator, window, cap, book, rebalance, timing_class, start_convention], readings: [market_scoped, family_wide], combine: max,
              snapshot: ledger_hash_at_registration, excludes: [own_run_rows, null_distribution_runs]}   # R2-C1
    spec_versions: publication_utc_listed_in_manifest   # the f = 1 route (a published SPEC version)
    printed: [N_raw, N_hat_linear_eq9, N_clusters, N_equiv, N_eff, break_even_N, z_check_one_sided_2p50_le_8_cells, by_q_global, dsr_vs0, psr_vs_S]
    forbidden: [kish_design_effect, revision_count_as_N]
  stats:                                             # R-24
    bootstrap: {method: ledoit_wolf_studentized_circular_block, null_centred: true, resamples: 2000, seed: 11,
                p_zero_print: "< 1/B", hac_p_printed: true}
    block: {rule: politis_white_on_influence_function, floor_sessions: 21, pc3_also_block_10: true}
    se_ladder_blocks: [10, 21, 63, 126, 250]         # SE_plateau = max (incl. LW-HAC)
    power: {alpha_one_sided: 0.10, power: 0.80, mde_factor: 2.1232, deltas: [0.05, 0.10], t_years: sessions_over_252, se: se_plateau}
    underpowered: {mde80_gt: 0.10, converts: [step5_p_value, pc3_p_value]}
    multiplicity: {p_source: analytic_hac_lw, bootstrap_resamples_if_used: "20*M/alpha", by_q_from_global_ledger: true,
                   one_sided_z: {le_8_cells: 2.50, bonferroni_120: 3.34}}
    pbo: {configs: ledger_union_frozen_pc6_grid, min_configs: 10, cscv_blocks: 16,
          objective: {CARD_O: paired_dSR_vs_off, CARD_P: blockwise_dES95_21}, winner_loses_share_gt: 0.10,
          reject_if: "PBO > 0.2 and winner_loses", null_calibration: printed}
    lo_adjusted_sr: {lags: [20, all], printed: true, gated: false}
    live_sharpe_multiplier: 0.60                     # take 40% off; HL haircut printed beside it
  timing:                                            # R-34
    lags_sessions: [-1, 0, 1, 2, 3]
    plus_publication_strict: true
    honest_lag: 1
    fragility_ratio_max: 0.5                         # declared once, before any card runs
    sign_flip_by_lag: 2
    consequence: {verdict_cap: INSUFFICIENT_DATA, tier_cap: B, require_live_timestamped_feed: true}
    positive_control: {fixture: KR_SOX_KRW_gate_B3, contents: R4_B3_inputs_and_rule, look_ahead_premium_min: 0.20}   # observed 0.28
    every_lag_in_family_ledger: true
    lookahead_rows: {mode: timing_probe, scope: [tests, r34_sandbox], tag: synthetic_lookahead, ledger_timing_class: NON-COMPLIANT,
                     production_writes: forbidden}
  tiers: {A: {min_onsets_declustered: 30, decluster_gap: own_lookback, min_stress_episodes_in_sample: 3, min_oos_episodes: 1,
              pooled_rule: declare_before_any_market_is_run},
          A_provisional: closed,          # BL-C12 resolved; no pooled or A-provisional route for a card already run
          B: {bounds: [0.5, 1.0], external_params: true, verdict_from_backtest: INSUFFICIENT_DATA, forward_record: falsification_only},
          C: {allowed: false}}
  parameter_budget_searched: 8
  stress_report_window: ["2022-01-01", "2026-10-02"]      # reported, not a holdout
  locked_holdout_start: "2027-01-01"
  costs: read_from_gate                  # KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10, futures 5, FX 10; x2 stress
  card_header_required: [instrument_book, notional_nav, rebalance, no_trade_band, fill_model, cash_convention, episode_rule_version,
                         family_id, ledger_hash_at_registration, history_first_close, data_span]   # start_band, midpoint_halves: acting long-sample cards (R-22)
  card_result_required: [timing_profile, ledger_hash_at_run, selection_factor, results_md5]          # §6.5
do_not_build:                            # R-33; §10. Validation refuses a matching entry, card header or book configuration (T-DNB-01)
  labels: [harm, null, inconclusive]
  basis: {B: qf3_bootstrap_class_or_share_lt_0.05, E: item_evidence_provisional, G: breaks_P0_P19_or_red_line}
  items:                                 # one label per item, or per variant where they differ (§10.2)
    1: inconclusive_B
    2: harm_B
    3: inconclusive_B
    4: harm_E
    5: inconclusive_B
    6: {curve_resteepening: harm_B, real_rate: null_B, credit_weights: inconclusive_B, mom_under_rates_stress: inconclusive_E, level_thresholds: inconclusive_E}
    7: null_E
    8: inconclusive_B
    9: {forecasts_surveys_positioning: inconclusive_E, crowding_cuts: inconclusive_E, consensus_surprise_entries: null_E}
    10: inconclusive_E
    11: {11a_ml_vol_state_classifiers: harm_E, 11b_range_log_har: admitted, smoothed_regime_probabilities: harm_G,
         unpenalised_hmm_ms_gates: harm_E, complexity_rff_timing: null_E, llm_text_pre_cutoff_backtests: harm_G}
    12: {event_blackouts_24h_and_swing: inconclusive_E, quad_witching_blackout: null_E, expiry_close_fade: inconclusive_E}
    13: inconclusive_E
    14: {rate_differential_models: null_E, foreign_flow_rules: inconclusive_E}
    15: inconclusive_E
    16: inconclusive_E
    17: inconclusive_E
    18: harm_G
    19: harm_G
    20: inconclusive_E
    21: harm_G
    22: harm_G
    23: harm_G
    24: harm_G
    25: harm_G
    26: harm_G
    27: {jump_model: inconclusive_E, markov_switching: harm_E, gmm_and_change_point_states: inconclusive_E, prohibition: binding_red_line_E1}
    28: null_E
    29: harm_E
    30: harm_B
    31: harm_G
    32: harm_G
    33: harm_G
    34: harm_G
    35: harm_G
    36: harm_G
    37: inconclusive_E
  refused_shapes:                        # §10.3
    order_path_or_broker_adapter: 21
    multiplier_weight_or_cap_above_1: [2, 8]
    composition_not_min: 31
    regime_model_source_acting_or_displayed: [11, 24, 27]
    smoothed_or_forward_looking_label: 24
    ml_classifier_estimator_gate_or_label: [11, 29]
    conformal_label_layer: 28
    sizing_estimator_max_over_implied: 30
    estimator_change_outside_r30_revision: 25
    header_edit_after_results_md5: [23, 32]   # instrument_book, notional_nav, rebalance, no_trade_band, cost_bp
    krx_stock_book_on_market_gross_scalar: 33
    pooled_or_a_provisional_tier_after_results: 34
    forward_record_cited_as_validation: 35
    kish_or_other_n_eff_rule: 36
    r28_instance_market_kr: 37
    recommended_book_reads_non_pass_multiplier: 22
    value_timed_or_provisional_acting_input: [19, 26]
reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002,
                  record: [git_hash, config_hash, data_snapshot_id, knowledge_utc, seed, results_md5, gate_package_version, gate_package_md5,
                           ledger_hash_at_registration, ledger_hash_at_run],
                  determinism: {canonical_json: sorted_keys_repr_floats_no_whitespace, volatile_fields: [generated_at_utc, git_hash],
                                rng: numpy_pcg64_seedsequence_spawned_children, blas_threads: 1, relative_tol: 1.0e-12}}   # T-REPRO-01a/b/c
```

### 7.1 Rule-object schema (rules-store validation; R-33)

Every rule in the store is one object with the fields below (**proposed**; map them onto the store's actual model). Validation refuses an object whose fields match a §10.3 shape; each shape is a predicate over these fields (T-DNB-01), and the error names the §10 item.

| Field | Values | Refused when (§10 item) |
|---|---|---|
| `rule_id`, `kind` | string; `kind` ∈ {INVARIANT, CONVENTION, CARD-O, CARD-P, CONTEXT, GOVERNANCE} | — |
| `output_range` | [lo, hi] | hi > 1.0, an overlay outside [0.5, 1.0], vt or vs outside [0, 1.0] (2, 8) |
| `exposure_basis` | active, total | missing on an acting rule (P8) |
| `applies_to` | the §6.2 `family` enum (momentum, reversal, flow, quality, ts_trend, market_gross) | a vt (R-06) rule on anything but `market_gross`; any multiplier on `ts_trend` (R-14 is exempt from overlays; P8, T-BASIS-01; its runtime check runs from M4 and M7, §9.0b) |
| `composition` | min | anything but `min` (31) |
| `books[]` | recommended, specification, forward_sim, refusal | the recommended book reading a non-PASS, FORWARD-SIM or refusal multiplier (22); `INVARIANT_STEP` only for R-31 |
| `inputs[]` | `{series_id, role, books, timing, source_kind}`; `source_kind` ∈ {market_price, published_series, derived, implied_vol, regime_model, ml_classifier} | a `regime_model` source acting or displayed, or a smoothed or forward-looking label (11, 24, 27); an `ml_classifier` source (11, 29); a value-timed or provisional acting input (19, 26); an acting input without a contract or binding (R-19) |
| `estimator` | `{name, kind}`; `kind` ∈ {sma, ewma, garch, har, comb, ml} | `ml` (11, 29); max(SMA20, implied) sizing (30); a change outside an R-30 counted revision (25) |
| `label_layer` | none, conformal | conformal (28) |
| `instrument_book`, `market` | the §6.5 and §6.1 enums | a KRX stock book as a market-gross scalar (33); an R-28 instance with market KR (37) |
| `card_id`, `tier`, `header_md5`, `results_md5` | strings or null | a header edit after `results_md5` exists (23, 32); a pooled or A-provisional tier added after results (34) |
| `n_rule` | the R-23 rule | the Kish form or any other N_eff rule (36) |
| any field | — | an order, cancel, withdrawal, deposit-address or transfer path, or a broker adapter (21); a forward record cited as validation (35) |

---

## 8. Governance v2: the gate package, model cards and the protective class

This section is a complete replacement for v1.2 §8. The subsection numbers are kept, because the rest of the spec cites §8.4, §8.6, §8.7, §8.8 and §8.9.

Every overlay rule that changes exposure is still a QUANTGEN model card, decided by the existing nine-step gate and its four verdicts. v1.1 removed v1.0's parallel promotion process, and v2.0 does not bring it back. What v2.0 changes is the **macro additions** to the gate. The council found that several v1.2 additions were statistically invalid or undefined:
- PC-1's single-path ΔMDD;
- an undefined step 3;
- label-defined episodes;
- demotion triggers that fire on noise;
- a forward-record route that cannot add information.

The replacements form **one package**. It is adopted once, blind to every card, before any formal card run (Quant Council Resolutions 4, 5, 7, 11; `council/QC_COUNCIL_RESOLUTIONS.md`).

**What changed from v1.2, in one list.**

| # | v1.2 | v2.0 | Rule |
|---|---|---|---|
| 1 | PC-1 (ΔMDD ≥ 3 pp vs S) gates; drawdown failures REJECT | PC-1′ gates: ΔES95 of 21- and 126-session returns. ΔMDD, ΔCDaR95 and daily ES99 are printed. A do-no-harm cap limits a drawdown failure to INSUFFICIENT DATA. | R-21 |
| 2 | PC-2 point only | PC-2 with a bootstrap CI. A horizon-matched ratio is adopted only through a placebo test before any run. | R-21 |
| 3 | Step 3: "global N" undefined | Family trial ledger; N_eff = max(N_clusters, N_equiv); CARD-O gate at deflated ΔSR ≥ 0.95; CARD-P prints DSR | R-23 |
| 4 | §8.6 label windows (none before 2008; Sep-2026 listed) | Objective market-own episodes (≥ 20%; ≥ 15% for the S&P); the windows are printed by shock type | R-22 |
| 5 | Raw returns, cash 0, undeclared start | Excess returns with local cash; start = first close + warm-up; declared start band and stability floor; regime lines | R-22 |
| 6 | No power line | SE ladder, MDE80 and power on every card; UNDERPOWERED may convert only a failed step-5 or PC-3 p-value | R-24 |
| 7 | Lag tests that trust the registry | A timing profile with a look-ahead positive control on every card; timing-fragile cards are capped | R-34 |
| 8 | Forward months as a re-gate route; triggers on sleeve NAV with a sign error | Forward records falsify and never validate; calibrated alarms on whole-book NAV under a book-level budget (D4) | R-25 |
| 9 | Instrument book declared loosely; costs flat | Instrument book, rebalance rule, band and notional are header fields; tick floor; granularity floor; verdicts are book-specific | R-26 |

**Red lines that bind this section.** The three council chairs each set at most five red lines, and the v2 rules respect all fifteen (council §c).

| Chair | Red line | Where §8 honours it |
|---|---|---|
| Professors P1 | No promotion on a single path or a single crisis | Objective episodes (§8.6); stability floor and regime lines (§8.7); R-06 KR conditions (§8.9) |
| Professors P2 · Executives E2 · QF Q1 | No gate rule chosen after seeing the card it decides | Package frozen blind before any formal run (§8.1.3) |
| Professors P3 · QF Q3 | No forward record presented as validation | §8.8 (R-25) |
| Professors P4 | No selection without counted multiplicity | §8.1 step 3, §8.4 ledger (R-23) |
| Professors P5 | Macro sizes risk; nothing above 1.0; a second-moment mechanism for every rule | §8.3 Tier C; the mechanism is a header field (§8.4) |
| Executives E1 | No regime-model state, acting or displayed | §10 (R-33); no regime card exists in §8.9 |
| Executives E3 | No exposure path the gate never sees | Stack card and step-down card (§8.7, §8.9) |
| Executives E4 | No acting decision on a provisional, stale or bar-derived input; no risk-model input that can HALT | R-01, R-19, R-27 (referenced from §8.4) |
| Executives E5 · QF Q4 | Book-specific verdicts on executable books | §8.2, §8.4 (R-26) |
| QF Q2 | No REJECT on single-path drawdown | §8.7 caps |
| QF Q5 | No mechanism may freeze or quietly shrink the book | `min()` composition, explicit re-arm (R-02, R-07, R-31) |

### 8.1 The gate (as QUANTGEN implements it) and the v2 package

#### 8.1.1 The nine steps

The fixed settings are QUANTGEN's own (architecture review; public page). The two right-hand columns are the v2 macro additions.

| Step | Check | Fixed setting (QUANTGEN) | CARD-O: v2 macro addition | CARD-P: v2 path (§8.7) |
|---|---|---|---|---|
| 1 | Choose in the past, test in the future | Purged walk-forward, 756 in-sample / 126 out-of-sample sessions, embargo = holding period | With no searched parameter the walk-forward reduces to the full sample, and the card says so. Every configuration run enters the family ledger (R-23). | Same |
| 2 | The interval must clear zero | Lo (2002) SE and a 90% block bootstrap, 2,000 × 10-session blocks | Ledoit–Wolf studentized circular-block bootstrap with blocks of max(21, PW on the ΔSR influence function); SE ladder; HAC p printed; p = 0 printed as "< 1⁄B" (R-24) | Replaced by **PC-3** (binding non-inferiority). The book's own interval is printed. |
| 3 | Count every try | Deflated Sharpe ≥ 0.95; every revision adds to N | Family ledger; **N_eff = max(N_clusters, N_equiv)**; **deflated ΔSR vs overlay-off ≥ 0.95** with V_null. Printed: the linear eq. 9 N̂ (with "step 3 borderline" if < 0.95 there), N_raw, the one-sided z-check (2.50 for ≤ 8 cells) and a BY q-value (R-23). Kish is never used. | DSR vs 0 and PSR vs S are printed, **not gated**. A **selection factor** f, computed by `step3()` from the family ledger and never declared (1, or N_eff for a configuration selected on the evaluation sample), multiplies the PC-1′ and PC-3 p-values (R-23). |
| 4 | Not over-searched | PBO via CSCV: PBO ≤ 0.05, or the winner loses in ≤ 10% of splits. PBO > 0.2 with the winner losing is a REJECT. | Configuration set = ledger ∪ the frozen PC-6 grid of the rule type (R-21). Objective = paired ΔSR vs overlay-off. Null-calibrated PBO printed. Run only with ≥ 10 configurations (R-24). | Objective = block-wise ΔES95 of 21-session returns, never MDD on concatenated half-samples |
| 5 | Beat the benchmark on the same days | Bootstrapped Sharpe difference, one-sided p ≤ 0.10 | Benchmark = overlay-off on the same costed engine. If MDE80 > 0.10, a failed p maps to INSUFFICIENT DATA (underpowered) (R-24). | Replaced by **PC-1′**, **PC-2** and **PC-4** |
| 6 | Survive twice the costs | Rebuilt at 2×; Sharpe > 0; losing at 2× is a REJECT only when the interval includes zero, otherwise a REVISE | Tick floor applied; stress-cost line printed, not gated (R-26) | The PC-1′ points and the PC-3 point at 2× feed **REVISE** |
| 7 | A plateau, not a peak | ≥ 50% of neighbours keep ≥ half the Sharpe | Unchanged | **PC-6**: ≥ 50% of the neighbours on the frozen axes of the rule type keep ≥ half of the centre's ΔES legs and a PC-3 point ≥ −δ |
| 8 | Most years, not one lucky year | ≥ 60% of calendar years positive; top-year share printed | Unchanged. Tied years are printed as ties (e.g. R-03: "active in 20 of 37 years, higher Sharpe in 15"). | **PC-5**, with the share of years lagging S printed |
| 9 | Then take 40% off | `live_sharpe_multiplier: 0.60` on out-of-sample Sharpe; reported, not gated | The card's Harvey–Liu haircut printed beside it (R-24) | Also prints 60% of the ΔES legs and of ΔMDD |

Two gates sit beside the nine steps on every card:
- the **timing-fragility gate** (R-34): a timing profile at lags −1…3 with a positive control. A timing-fragile card is capped at INSUFFICIENT DATA;
- the **estimator-calibration requirement** (R-30): SMA20 must keep passing B5, and a challenger estimator must pass Stage 1. A failure caps the card at REVISE.

**Verdicts** are PASS / REVISE / REJECT / INSUFFICIENT DATA, defined once in code. There is no fifth verdict.
- A REVISE names the first failed check and the only permitted fix: widen the grid, lengthen the holding period, or extend the history.
  - In v2, a holding-period fix that changes the rebalance rule, band, instrument book or estimator is a **new card** or a **counted revision** (R-26, R-30).
  - Lowering a cost is never permitted.
- A REJECT stays on the record, with the same card and the same weight as a PASS.
- Every verdict carries a reason code: `sufficiency`, `inconclusive`, `underpowered`, `do_no_harm`, `timing_fragile`, `stability`, `claim_not_shown`, `estimator_calibration`, or the failed check's id.

#### 8.1.2 Build statuses and books

| Build status | Meaning | Members in v2 |
|---|---|---|
| **BUILD NOW** | Implemented in v2. An INVARIANT or CONVENTION applies in every book. A card's factor enters the recommended book only once its card's verdict is **PASS**. | R-01, R-02, R-03, R-05, R-07, R-08 (annotation), R-09, R-10, R-14, R-15, R-18, R-19–R-27, R-30, R-32–R-35 |
| **BUILD-AS-INSURANCE** | The build status of a **CARD-P with a formal v2 PASS** whose header declares an insurance claim. It enters the recommended book with its insurance label and premium shown beside it, and its forward record is a falsification alarm only. **It is not a fifth verdict.** | R-06 KR on a formal PASS; R-28 and R-29 once promoted |
| **FORWARD-SIM** | Implemented as a forward-running simulated book only: the specification book × the card's factor. It never reaches the recommended book or `engine_feed` until its card's promotion conditions hold. | R-28, R-29 |
| **SPECIFICATION BOOK** | Applies only in the specification book, labelled with its verdict. Covers every card that is NOT_RUN or INSUFFICIENT, and every factor held there by rule. | R-04; R-31 while its binding share is > 10%; R-06 KR while NOT_RUN or INSUFFICIENT |
| **RETIRED (refusal book)** | REJECT recorded on long history. A labelled, display-only book that no recommended or specification book reads. | R-11, R-12 |
| **DEFERRED / CONTEXT** | Specified but dormant until a sleeve exists / built, but never acts | R-17 / R-13, R-16; KOSPI trend state |

**Books.**
- The **recommended book**, the only book whose weights are shown as a recommendation, holds the invariants plus the factors of PASS cards, composed by `min()`: composed = vt × min(1.0, overlay₁ … overlayₖ, ladder, post_rearm_cap). Outside HALTED, composed ≥ 0.5 × vt (R-02); the concentration bound may take gross lower. R-31 steps with a binding share ≤ 0.10 act here as `INVARIANT_STEP`. Once two or more de-risk factors act in it, the book is gated as one **stack CARD-P** (§8.7).
- The **specification book** holds every BUILD NOW and SPECIFICATION BOOK factor, each labelled with its card verdict.
- Each FORWARD-SIM card has its own book, and each retired card has its refusal book.
- The I-03 assertion covers all of them: the recommended book never reads a non-PASS factor, a FORWARD-SIM multiplier or a refusal book.
- Every book has its own runtime state; a HALT applies to one book, never to the engine as a whole (§3.8, C-1).

#### 8.1.3 The v2 gate package: contents, freeze and adoption order

The package is what Professors' red line P2, Executives' E2 and QF's Q1 protect. It is **frozen and adopted blind, once, before any formal card run.**

| Component | Rule | Frozen items |
|---|---|---|
| CARD-P checks | R-21 | PC-1′ legs (21 and 126 sessions, ES95, mean block 250, the uncentred bootstrap percentile p ≤ 0.10, z printed); PC-2 (≤ 0.90, CI; the horizon-matched decision); PC-3 (δ 0.10, p_ni = max(p₁₀, p_PW)); PC-4…PC-7, with the PC-6 axes per rule type; caps; the UNDERPOWERED scope; printed lines |
| Gate-acceptance test | R-21 | Placebo construction and counts (300 per family, 20 per card), the pass definition, the population and the τ grid; the five negative controls; the CDaR-guard rule (D6, its default frozen now); the attempts log (the package-level ledger); the bounded-redesign rule; the results md5 |
| Evaluation conventions | R-22 | Episode rule and θ by market (the frozen θ rule for other markets; open episodes); excess returns, the cash series, its unit and the rate date; the start rule, each market's history start, the fixed span end and the drafted cards' data cut-off; the frozen start-band shapes and the integer stability floor; regime lines; post-trough window; the risk layer inside card books (rule 6) |
| Step 3 | R-23 | Ledger rules (family by rule, hash chain, harness-only rows); N_eff; the E[max] function; the V rule; the CARD-O bar; the CARD-P selection factor, computed under `any_overlap` over the frozen row set, the maximum over the defensible readings (R2-C1) |
| Statistics and power | R-24 | Bootstrap, block rule, SE ladder, MDE / power, PBO definition, multiplicity, Lo-adjusted Sharpe |
| Timing gate | R-34 | Lags −1…3 plus strict; FR threshold 0.5; sign-flip rule; the positive control (LP ≥ 0.20) |

**Freeze procedure (milestone M7, in this order).**
1. **Build and unit-test the harness.** These tests must pass (§9.0a, "M7, before the freeze"): T-DSR-01/02, T-NEFF-01, T-STEP3-01/02, T-SEL-01, T-LEDGER-01, T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01, T-EXCESS-01, T-BAND-01, T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01, T-PLACEBO-01/02, T-GATE-04, T-AVAIL-01 and I-05. They run on synthetic data, frozen fixtures and the hermetic `timing_probe` sandbox, and write to temporary copies of the ledgers (T-HERM-02).
2. **Run the gate-acceptance test** (T-GATE-01…03) on placebos and negative controls only. No real card's verdict is computed before the freeze.
   - The per-card placebo panels are built from the CARD-P headers drafted for step 4 (R-06 KR, R-28, R-29, R-31), each with its span ending at `gate.evaluation.data_cutoff` (R-22); the acceptance report cites each draft's md5 (the header fields without the package citation). The header committed in step 4 must match its draft. A CARD-P registered after the freeze (a changed header, the generated stack card, another market's card) runs its own panels under the frozen rule 9(a) at its header commit, before its formal run: its 300 shifted placebos (≤ 10% passing PC-1′) and its 20 per-card placebos (≤ 2 passing). An excess leaves that card NOT_RUN pending council question Q5; the panels' results are md5-frozen with its header, and no package version is created.
   - The placebo rule of R-21 9(c) decides whether the horizon-matched PC-2 is adopted.
   - If any negative control would pass, the CDaR guard is added with the calibration fixed by owner decision D6 before any control or card ran (its default rule, or an owner ruling recorded before the first attempt; R-21 9(d)); the report prints the three council candidates' placebo results only (never a real card's numbers), and the test is re-run.
   - A per-family or per-card placebo count above its limit fails the test; nothing is frozen (R-21 9(a); council question Q5, §8.10). One bounded redesign per package version is allowed, under the rules of R-21 9(a); a second failure, counted across all 2.x versions, ends evaluation under v2 and notifies the owner (R2-C3; T-GATE-04).
   - Every attempt, passing or not, is appended to `gate/acceptance_runs.jsonl` (append-only, hash-chained); the frozen report lists every attempt.
3. **Freeze.** Write `gate.package = {version: "2.0.0", definitions_md5, acceptance_report_md5, frozen_utc}` to the rules store. `definitions_md5` is the md5 of a manifest listing: (a) the canonical JSON of every `gate.*` block; (b) the source files of every harness function of R-21–R-24 and R-34 (`cardp_evaluate`, `episodes`, `family_ledger`, `n_eff`, `step3`, the bootstrap and block-length code, `timing_profile`, `power_line`, `gate_acceptance_test`); (c) the md5 of every fixture the acceptance test reads; (d) the seeds; (e) each family ledger's hash at the freeze, the §9.5 seed files and the difference series they reference; (f) `gate.evaluation.data_cutoff`, the D6 rule and the recorded answers to §8.10's freeze-relevant council questions. The manifest, both md5s and the acceptance report are committed to the repository, an external, timestamped anchor, before any card is run. `docs/macro_overlay_study.py` re-hashes the manifest at every card run and refuses to run on a mismatch (T-CARD-02). Adoption counts as one revision in every family ledger.
4. **Commit every formal card header, blind, with its header md5:**
   - R-06 KR (ETF line; `MACRO-R06-KR-ETF`);
   - R-03 on QUANTGEN's own sleeve, with its two registered revisions (scale-free target; variance-scaled): card_id `MACRO-R03-US-MOM`, market US, US shares via KIS at 50 bp on both legs, the sleeve's paper long/short series over its declared history (history start and span written in the header); T-R03-01's M7 clauses test the harness on the French fixture, not this card;
   - R-14 (`MACRO-R14-MULTI-TREND`, one `multi_line` card), R-31 (`MACRO-R31-KR-ETF`: one card, on the KR book, the only v2.0 book whose steps bind on more than 10% of days; a US card is registered only once D5 creates a US sleeve), R-28 (`MACRO-R28-US-TREND`) and R-29 (`MACRO-R06-US-FUT`). The card ids are proposed and fixed in the drafts.

   Each header cites the package version and md5 and carries its `ledger_hash_at_registration`; a CARD-P header must match its step-2 draft.
5. **Run the formal cards** and publish the verdicts, each appended to the hash-chained `cards/verdicts.jsonl` (R-35), with the disclosed flips below.
6. **After the first formal run,** the package can change only as a **new package version**. A new version re-runs every card and counts in every family ledger. No change may be justified by the card it flips.

**Disclosed flips, accepted blind.**
- **US VT15 on US shares at 50 bp:** a REJECT under v1.2's PC-1; it reads INSUFFICIENT DATA (inconclusive) under PC-1′. The registered card is not re-run and keeps its instrument-labelled REJECT (§8.9).
- **KOSPI VT20 on 2016–26:** it passed PC-1; under PC-1′ it reads INSUFFICIENT DATA (ES z 1.82 / 1.13; EX1). No build decision changes, because the long-history card decides Korea.
- **Episodes:** the objective rule rescues the Korea card's PC-4 (maximum share 0.493 → 0.174). The §8.6 result is printed beside it (§8.6).
- **Step 3:** the N_equiv rule was chosen after seeing that R-03 passes under it and is borderline under the linear N̂. Both numbers are printed.
- **PC-2:** the horizon-matched ratio would flip only KOSPI trend (0.929 → 0.853), which stays context whatever it shows.
- **Estimator:** an EWMA(0.94) switch would turn the Korea card INSUFFICIENT on PC-4 under §8.6 (0.51). The estimator (SMA20) is fixed before the run.
- **Selection factor (C-2, R2-C1):** R-06 KR's f is computed from its ledger and exceeds 1, because R4 compared windows and caps on 2016–26 before SPEC v1.1; the maximum over the defensible row-set readings binds. On the indicative excess-return numbers any f > 1.28 turns its PC-3 into INSUFFICIENT DATA (§8.9). On current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build: f takes the maximum over the defensible row-set readings, every reading that includes the DL-A seed of §9.5 gives f above 1.282 (indicative f 1.26 on R4's three rows alone, 1.49 with the DL-A grid, 2.87 family-wide), and PC-3 needs p_ni × f ≤ 0.10 at the indicative p_ni 0.078. The status stays BUILD-AS-INSURANCE on a formal PASS (Resolution 1), and no convention may be changed to rescue it (R2-C1; §8.9).
- **Card books (C-2):** the hard stop and caps are excluded from card books and judged on the composed recommended book (R-22 rule 6). For KOSPI VT20 the maximum drawdown is −45.3% without the hard stop and −56.4% with it (24 HALTs; Check C2).

### 8.2 Card classes

| Kind | Claim | Gate path | v2 members |
|---|---|---|---|
| **CARD-O** | Outperformance of the overlay-on book vs the overlay-off book (same costed engine, same data) | Steps 1–9 with R-23 and R-24 | R-03, with two registered revisions (scale-free target; variance-scaled trial); R-04 (specification book; step 3 FAIL); R-14 (diversification claim) |
| **CARD-P** | Protection (PC-1′ tail legs, PC-2 coverage) with Sharpe non-inferiority vs S | §8.7 | R-06 KR (ETF line; the stock-book line is on record); R-06 US 50 bp (recorded REJECT); R-29; R-28; R-31; the stack card (R-02); R-08 (recorded REJECT, demoted); R-11, R-12 (retired); crypto vol cap (R-17, deferred) |
| INVARIANT | None: a bound, a data rule, a risk limit, a risk-model assumption | Not gated; its effect is reported on every card's books | R-01, R-02, R-07 (caps; hard stop with re-arm), R-09, R-19, R-20, R-26 |
| CONVENTION | None: delays, annotates or allocates by rule | Not gated; logged and measured | R-05, R-08 (annotation), R-10, R-15, R-17, R-27 |
| GOVERNANCE | None: defines how cards are judged and monitored | Frozen with the package where listed; never a card | R-18, R-21–R-25, R-30, R-32–R-35 |
| CONTEXT | None | Never acts | R-13, R-16 |

- **The claim is a header field, fixed before the run.** A trend or regime card states a second-moment mechanism, e.g. "slow-bear protection via the volatility state". A Sharpe or predictability claim on a protective rule is refused. Changing the claim after results is a **new card**, counted in the ledger.
- **Verdicts are book-specific** (R-26). A verdict holds for the declared instrument book, rebalance rule, band and notional. Another venue is a new card, never a revision (DNB #23).
- A market-gross scalar is never judged on a stock book used as the scalar.

### 8.3 Evidence tiers in gate terms

The tiers decide **which verdicts a backtest alone can produce.**

| Tier | Applies to | In gate terms |
|---|---|---|
| **A** | Discrete rules with ≥ 30 onsets per market, de-clustered at the rule's own lookback; or onsets pooled under a rule **declared in the header before any market is run**. Continuous rules with ≥ 5 objective episodes (R-22) in the sample. | Any verdict. Multiplicity printed: one-sided z ≥ 2.50 for ≤ 8 pre-registered cells (3.34 Bonferroni-120 beyond); a BY q-value; N_eff |
| **A-provisional** | **Closed.** R-04's pre-registered out-of-region holdout (BL-C12) passed in 1 of 3 regions. | A published, replicated effect now goes through Tier A (pooling declared before any run), or through an empirical-Bayes pooling registered as a revision before any run. **No pooled route exists for a card already run** (R-04, the jump model, KOSPI trend). |
| **B** | Bounded de-risk rules with < 30 onsets and externally fixed parameters; **timing-fragile cards** (R-34) | **INSUFFICIENT DATA by construction.** Sufficiency is decided first; the timing-fragile cap only lowers, so a REJECT stays a REJECT. The route is new history: re-gate when the extended sample reaches the tier count, as one counted revision. Forward-window statistics never decide it (§8.8). |
| **C** | Anything that raises risk (a multiplier above 1.0) | REJECT by construction. The rules store refuses the rule. |

**Pooled-onset rule** (QF3-M4; council Q1):
- the rule is declared before any market is run;
- the own-market estimate and the cross-market dispersion τ are printed;
- an own-market PC-1′ or PC-2 failure vetoes a pooled pass;
- pooling never rescues a card that has already been run.

The trend card (R-28) declares its rule before its run. Its US instance alone has 45 de-clustered onsets on 1927–2026.

### 8.4 Pre-registration = the card header v2

**The header** is written before the study run, its md5 (`header_md5`) is committed, and it is immutable once committed. It is the pre-registration. It validates against `model_card_header.macro` (§6.5, R-32) at commit; run outputs (`selection_factor`, `timing_profile`, the stability results, `forward_record`) belong to the card's result block, never to the header. Every field below is required unless marked optional.

| Group | Fields |
|---|---|
| Identity | `card_id`, `family_id` (assigned by rule, R-23), `rule_id`, `revision`, `class`, `claim` (verbatim text) and `claim_type`, `build_status_on_pass` (BUILD_NOW or BUILD_AS_INSURANCE), `tier`, `created_utc`, `header_md5`, `gate_package_version` and `gate_package_md5` |
| Rule | `hypothesis`, `mechanism` (a second-moment mechanism; red line P5), `rule`, `parameters`, `searched_parameters`, `estimator` |
| Book (R-26) | `instrument_book` (with `instrument_lines[]` for `multi_line`), `rebalance`, `no_trade_band`, `notional_nav` (= `sleeves.<market>.notional_nav` at commit), `nav_fx` (non-KRW books), `fill_model`, `roll_calendar` (futures), `costs: {per_side: read_from_gate, floor: tick_floor, stress: 2.0, stress_line: printed, schedule (optional; it may only raise a cost)}` |
| Data and conventions (R-22, R-20) | `data` (source and `value_status = official_close`), `history_first_close` (the registry's history start), `data_span` (start = first close + estimator warm-up; end = `gate.evaluation.data_cutoff` for a CARD-P drafted for the freeze, else the last official close before the commit, as a date), `cash_convention`, `episode_rule_version`, `start_band` (a frozen shape) and `midpoint_halves` (with the split date), both null unless the card is an acting long-sample card, `gating_lines` (optional), `regime_lines`, `primary_oos_line`, `printed_lines` |
| Multiplicity (R-23) | `ledger_hash_at_registration`, `N_raw_at_registration`. `selection_factor` is computed by `step3()` at the run, never declared: a header that declares it is refused |
| Timing (R-34, R-19) | `timing`: the decision convention and every acting input with its series, channel, `available_at` rule and timing class; `live_feeds` (required if the card is timing-fragile). The `timing_profile` is computed by the run and written to the card's result block (covered by `results_md5`), never to the header; `header_md5` covers header fields only. |
| Checks | `comparator` (S, or overlay-off for CARD-O), `benchmarks`, `checks: gate_package_<version>`, any card-specific claim lines (`claim_lines`, e.g. R-28's stacked ΔMDD ≥ 3 pp) and pooling rule (`pooling_rule`) |
| Outcomes | What PASS, INSUFFICIENT DATA and REJECT lead to (e.g. R-06 KR: BUILD-AS-INSURANCE / labelled control re-gated on a new objective episode / archive) |
| Label and seed | `label` (the text displayed with the verdict), `seed: 11` |

**Revisions and new cards.**
- These changes are a **new revision**, counted in N: any threshold, window, multiplier, timing, universe, estimator, class, cash convention, start band or episode rule, and the adoption of a new gate-package version.
- These changes are a **new card**, also counted: a different claim, a different instrument book, rebalance rule, band or venue (DNB #23).
- Every configuration ever run in a family, research phase included, is a ledger row (R-23). Revision counts are never the trial count.
- An edit to an acting parameter in the rules store outside a revision demotes the card (R-25).
- **Expect the grid median, not the best cell.** For the rates leg the grid median was ≈ +0.01, not +0.04.
- **Parameter budget.** All macro cards together may have at most **8 searched parameters**. Conventions declared before any backtest do not count.

**Example header** (R-06 KR, the formal long-history card; Resolution 1). It validates against `model_card_header.macro` (T-SCHEMA-01); `<…>` values are typed placeholders filled at commit:

```yaml
card_id: MACRO-R06-KR-ETF
family_id: R-06                               # assigned by rule (QC_modules.csv; R-23)
rule_id: R-06-KR-VT20
revision: 2                                   # v1.2's 2016-26 card was revision 1; new span and conventions
class: CARD-P
claim: &label "Crisis-clustering insurance: reduces drawdown in volatility-clustering crises (1997–98, 2008, 2026); no help against gap shocks from calm states (2018-10, 2020-02, 2024-08); Sharpe non-inferiority is marginal — it pays a premium in calm decades (2016–25 alone: tail 0.95, ΔSR −0.079) and is short the post-crash rebound premium; not expected to outperform; cap 1.0 permanent."
label: *label                                 # byte-identical to the R-06 label (UTF-8)
claim_type: protection
build_status_on_pass: BUILD_AS_INSURANCE
tier: A                                       # continuous; objective episodes (18 on 1997-2026)
created_utc: "<commit time>"
header_md5: "<md5 of the header fields, committed before the run>"
gate_package_version: "2.0.0"
gate_package_md5: "<gate.package.definitions_md5 at the freeze>"
hypothesis: "VT20 lowers tail losses vs a same-average-exposure static book without a Sharpe loss beyond 0.10"
mechanism: "variance reduction (variance ratio 0.59); implicitly short the rebound premium (timing return -1.8%/yr)"
rule: "vt = min(1.0, 0.20 / sigma_SMA20(t)); decided at the KRX close of t (available_at <= close_print_bound_utc(KR, t)); earns from t+1"
parameters: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, floor: none}
searched_parameters: []                       # PC-6 neighbours come from the frozen pc6_axes, never from the header (R-21)
estimator: sma20                              # a COMB revision would be a new counted revision (R-30)
instrument_book: KRX_ETF_line                 # KODEX 200; tick floor applies
notional_nav: "<sleeves.KR.notional_nav at commit, KRW>"   # owner-signed (R-26); a futures line only if one mini contract <= 5% (about KRW 1bn+)
rebalance: daily
no_trade_band: 0.0                            # bands only on stock and US-share books
fill_model: KRX_close_auction                 # R-27
costs:
  per_side: read_from_gate
  floor: tick_floor
  stress: 2.0
  stress_line: printed
  schedule:                                   # no ETF existed before Oct-2002; a declared cost may only rise (P10)
    - {to: "<the day before the KODEX 200 listing, from the KRX listing record>", cost_class: futures}
    - {from: "<the KODEX 200 listing date>", cost_class: krx_etf}
  printed_lines: [krx_etf_3bp_throughout]     # the DLA-K8 / G-KR-L01 convention, printed for comparison
data: {source: KRX_official_closes, value_status: official_close, history_file: "<the frozen KRX official-close fixture>",
       reconciliation: "R-01: index 1 bp, stocks exact", golden_tolerance: "Level-2, only for I-16's raw-flag data check vs G-KR-L01; the formal run's differences are printed, never gated",
       saturday_sessions_before: "1998-12-12"}
history_first_close: "1997-04-01"             # gate.evaluation.history_start KR (R-22)
data_span: {start: first_close_plus_20_session_warmup, end: "2026-10-02"}   # gate.evaluation.data_cutoff.KR (R-22): fixed now, never "latest"
cash_convention: {returns: excess, cash_series: BOK_CALL_RATE, day_count: act_365}
episode_rule_version: "1"                     # alternating >= 20% on KOSPI's own closes; Sep-2026 is not an episode
gating_lines:
  full_span: v2_PASS
  etf_era: {from: "<the first day of the first full month after the KODEX 200 listing>", to: "2025-12-31", require: v2_PASS}
start_band: {shape: R-06_KR, from: "1997-05", to: "1999-12", step: month, starts: 32, require: {no_reject: true, pass_share_min: "2/3"}}
midpoint_halves: {split: calendar_midpoint, split_date: "<the calendar midpoint of the fixed span>", require: no_reject}
regime_lines: from_R20_tags
printed_lines: [etf_era_to_present, pre_design_2002-10_to_2015-12, "1997_to_2002_alone", "2016_to_2025_alone",
                rolling_decades, pc4_under_section_8_6, ewma094_line, timing_return, years_lagging_S,
                h1_2026_bull_tax, median_reentry_lag, per_regime_table, with_risk_layer]
primary_oos_line: etf_era
comparator: S_same_average_exposure
benchmarks: [buy_and_hold, overlay_off, static_same_avg_exposure, ewma_derisk]
checks: gate_package_2.0.0
ledger_hash_at_registration: "<md5 of the R-06 family ledger at commit>"
N_raw_at_registration: "<R-06 ledger row count at commit>"
# selection_factor: never declared here; step3() computes it at the run and the card prints f = 1 and f = N_eff (R-23)
timing:
  decision: close_t_earn_t_plus_1
  inputs: {KOSPI: {series: KOSPI_OFFICIAL_CLOSE, value_status: official_close, available_at: "<= close_print_bound_utc(KR, t)"}}
outcomes: {PASS: BUILD-AS-INSURANCE, INSUFFICIENT_DATA: specification_book_control_regated_on_new_objective_episode,
           REJECT: archive}               # the forward record is a falsification alarm only (R-25)
owner_decisions: {risk_layer.korea_caps.template: msci_25_50}   # D1; caps are excluded from the card books and printed (R-22 rule 6)
seed: 11
```

### 8.5 Benchmarks, statistics, power and costs

**Benchmarks, always all four.** All four run on the same costed engine and the same data, and use R-22's excess-return convention.
1. Buy-and-hold.
2. The **overlay-off** book: the rule switched off. This is the CARD-O comparator.
3. **S**, the static book at the overlay's average exposure: overlay-off × the mean multiplier, constant, same days, uncosted. This is the CARD-P comparator. For an incremental card (the trend card, the step-down card, the stack card), "overlay-off" means the book without the factor under test.
4. EWMA de-risk: the market vol target with EWMA(0.94), the same target and cap 1.0. It is printed; on the R-06 cards it is the "EWMA(0.94) line".

**Return convention (R-22).** Every card statistic uses excess returns: x_t = w_t·(r_t − c_t) − cost_t, with idle cash earning the local short rate (Korea: `BOK_CALL_RATE`, the latest annual rate dated on or before the previous session; US: `US_RF`, French RF as a per-period return or DTB3 as an annual rate; R-22 rule 3).
- Raw returns with cash at 0 do not give Sharpe ratios: Korean rates ran at 16–25% in 1997–98 (X-PX2-N5). The convention moves the Korea card: ΔSR +0.025 → +0.006, p_ni 0.051 → 0.078, and the share of 33 starts that pass falls from 97% to 70% (PX2). PX2's raw baseline is its own replication (ΔSR +0.0254, p_ni 0.051); DLA-K8's definitive cell prints +0.026 and 0.052, which T-EXCESS-01's raw flag reproduces.
- The start is the first available close plus the estimator's warm-up. It is never chosen: each market's history start is fixed in the registry before the freeze, and the span end is fixed at the header commit.
- An acting long-sample card also carries a start band of a frozen shape and calendar-midpoint halves, and must pass the stability floor (§8.7).
- A reproduction test may set `returns: raw` to match a legacy golden value. A formal card never does.

**Primary statistics.**

| Class | Gating statistics | Printed beside them |
|---|---|---|
| CARD-O | Paired ΔSR vs overlay-off (steps 2 and 5); deflated ΔSR vs overlay-off ≥ 0.95 (step 3) | The N lines (R-23), PBO, plateau, years, the Lo-adjusted Sharpe, the Harvey–Liu haircut, the power line |
| CARD-P | PC-1′ (ΔES95 of 21- and 126-session returns vs S); PC-2 (tail-exposure ratio); PC-3 (ΔSR vs S, non-inferiority); PC-4 … PC-7 (§8.7) | ΔMDD, ΔCDaR95 and daily ΔES99 with bootstrap bands; CVaR(5%); time under water; worst-day coverage; re-entry lag; GJR-null percentile; placebo panel; DSR vs 0 and PSR vs S; the power line |

**Bootstrap and block length (R-24).**
- **Steps 2 and 5 and PC-3:** a Ledoit–Wolf studentized circular-block bootstrap, null-centred, with 2,000 resamples and seed 11. The HAC p-value is printed beside it.
- **Block length:** Politis–White computed on the influence function ψ of ΔSR, with a floor of 21 sessions. PC-3 uses p_ni = max(p₁₀, p_max(21, PW(ψ))).
  - v1.2 computed Politis–White on dₜ and dₜ². That rule is withdrawn: PW(d²) gave 42–251 sessions, against 2–62 sessions for PW(ψ) (QF3 §4.3).
- **PC-1′:** a stationary bootstrap with a mean block of 250 sessions; p is the uncentred bootstrap percentile, and z is printed beside it (R-21).
- **SE ladder:** the LW-HAC SE and the block SE at 10, 21, 63, 126 and 250 sessions are all printed. SE_plateau is the largest of them.
  - Example (T-SE-01): R-03 vs unscaled has LW-HAC 0.072 and 250-block 0.091. Its z falls from 3.81 to 3.0.
- **No zero p-values:** a p-value of 0 is printed "< 1/B".

**Multiplicity and selection (R-23, R-24).**
- **One sidedness convention throughout:** one-sided z 2.50 for ≤ 8 pre-registered cells; 3.34 (Bonferroni-120) beyond that.
- **Where the p-values come from:** multiplicity runs on analytic HAC / LW p-values, or on B ≥ 20·M ⁄ α resamples. With B = 2,000, 11 of 199 variants sat at the 1 ⁄ B floor (QF3-A11).
- **Printed beside `live_sharpe_multiplier: 0.60`** (step 9): a BY q-value from the global ledger and the Harvey–Liu haircut.
- **PBO (step 4):**
  - The configuration set is the family ledger ∪ the frozen PC-6 grid of the rule type (R-21).
  - The objective is the card's own claim: paired ΔSR for CARD-O; the block-wise ΔES95 of 21-session returns for CARD-P.
  - CSCV uses 16 blocks. The step runs only when there are ≥ 10 configurations. The null-calibrated PBO is printed.
  - Pilot values (QF3 §4.2): momentum family 0.000; R-03 grid 0.009; KOSPI VT grid 0.282 / 0.364 on the Sharpe objective, which is printed but does not decide (the protective objective decides); ten noise configurations 0.536.
- **Lo-adjusted annual Sharpe:** printed at 20 lags and at all lags, and never gated. For R-03, η ⁄ √252 is 0.838 at 20 lags and 0.951 at all lags (QF3-A21; PX1).

**Power line and UNDERPOWERED (R-24).** Every card prints:
- SE (HAC and 250-block);
- MDE80 = 2.1232 × SE_plateau (one-sided 10%, 80% power);
- the power at Δ = +0.05 and at Δ = +0.10;
- for a CARD-P, the power of PC-3 at a true ΔSR of 0, and the years needed to detect +0.05 (T_years = sessions ⁄ 252, SE = SE_plateau).

**UNDERPOWERED.** If MDE80 > 0.10, a failed step-5 p-value (CARD-O) or a failed PC-3 p-value (CARD-P) maps to INSUFFICIENT DATA, with reason code `underpowered`. It never waives PC-1′, PC-2, the PC-3 point REJECT or step 3 (red line P3).

**Costs (P10, R-26).**
- **Rates and turnover.**
  - Per-side rates are read from the gate's cost table and never redefined here.
  - Turnover is |Δw| per day, charged on the day the new weight earns. Long/short sleeves are charged on both legs.
  - Buy-and-hold and S carry no cost.
- **Tick floor (INVARIANT).** cost_side = max(table rate, commission + ½·tick ⁄ price + tax_side). It can only raise a cost.
  - KODEX 200 at ₩112,060 floors at ≈ 1.6 bp, so the 3 bp table rate applies.
  - 252670 at ₩69 floors at 73.9 bp (EX2; PX2 F4).
- **Declared schedules.** A header may declare an effective-dated cost schedule, which can only raise a cost. R-06 KR declares the futures rate before the KODEX 200 listing and the ETF rate after (no ETF existed before Oct-2002), and prints the ETF-3-bp-throughout line of DLA-K8 and G-KR-L01 for comparison.
- **Stress.**
  - Every card also runs at 2× cost (step 6).
  - The stress-cost line is printed and never gated until it has been calibrated on KIS quote snapshots: cost × clip(σ20 ⁄ σ_median, 1, 5), plus 10 bp per side on ETF close fills on days with |r| ≥ 3%.
- **Granularity.** A futures line is allowed only if one contract, valued at the header commit, is ≤ 5% of the sleeve notional (`sleeves.<market>.notional_nav`, owner-signed), i.e. about ₩1bn or more.
  - Contract sizes: KOSPI200 ≈ ₩280m; mini KOSPI200 ≈ ₩56m; Micro ES ≈ ₩52m.
  - Integer-contract tracking error for VT20 is 7.5% a year at ₩0.1bn and 0.7% at ₩1bn (X-EX2-N3).
- **Printed lines:**
  - execution variants A (same close), B (next open) and C (one-session lag); for KOSPI VT20 at 3 bp on 1997–2026, SR 0.448 / 0.450 / 0.465;
  - overnight / intraday attribution;
  - turnover by regime;
  - roll-cost and ban-period basis lines on futures books.
- **Turnover and cost drag** (R4b unless stated):

| Rule | Turnover a year | Cost drag a year |
|---|---|---|
| KOSPI VT20 (SMA20) | 1.50 on 2016–26; 3.12 on 1997–2015 (QF1-A7) | 0.05% at 3 bp; 0.53% at 35 bp (2016–26) |
| KOSPI VT20 with the COMB challenger (2001–26) | 3.48, against 2.25 for SMA20 on the same sample (DLB) | — |
| US VT15 | 2.52 | 1.26% at 50 bp |
| KRW leg (retired) | 2.51 on value timing; 1.12 on strict H.10 | — |
| Rates leg (retired) | 3.60 | 1.80% at 50 bp |
| Momentum vol scale | 0.85 on both legs | — |

**Estimator requirement (R-30).** SMA20 stays the acting sizing estimator and the displayed baseline. The text "validated default" is struck.
- **SMA20 passes B5:**
  - KOSPI 4.70% of 2,594 origins (PIT p 0.107); SPY 4.99% (PIT p 0.566); US 5.31% of 8,961 (PIT p 0.976) (DLB-T1e);
  - KOSPI 1997–2026 5.04% (PIT p 0.46; DLA-G1).
- **B5 cannot choose an estimator:**
  - it passes 7 of 9 KOSPI forecasters and 8–9 of 9 US ones;
  - SMA20 is outside the 90% QLIKE model confidence set at 1, 5 and 21 days in both markets (p ≤ 0.0005), though it is inside the MSE set;
  - its KOSPI breaches cluster (Christoffersen p 0.0006 on 2016–26 and < 0.0001 on 2001–26) (DLB-T1a, T1b, T1f).
- **COMB = ½(GJR-t + log-HAR-range)** is the registered challenger, for ETF and futures books only.
  - It is inside the 90% MCS in all six cells. Its QLIKE as a multiple of SMA20's is 0.944 / 0.809 / 0.691 (KOSPI) and 0.916 / 0.723 / 0.642 (US). Its Christoffersen p is 0.17.
  - On KOSPI 2001–26 at 3 bp it cuts vol-of-vol by 22.2% and improves ΔMDD by 2.8 pp, at ΔSR −0.000 [−0.042, +0.039]. The gains halve on 2016–26 (DLB-T1g).
- **Switching.** A switch is a counted card revision that passes R-30's Stages 1–3 and the full v2 CARD-P.
  - Never on the 35 bp stock book, where log-HAR costs −0.063 Sharpe and COMB −0.030.
  - Never on the registered R-06 KR card.
- **Cap.** SMA20 must keep passing B5, and a challenger must pass Stage 1 (calibration at the 21-day sizing horizon). A failure caps the card at REVISE (`estimator_calibration`). The only permitted fix is "lengthen the holding period", as a counted revision.
- The estimator choice is a tracking and drawdown decision, never a Sharpe claim.

**Expectation setting.**
- **SE(ΔSR) vs S:**
  - ≈ 0.061 for the US vol target over 36 years, and 0.130 for the KOSPI vol target over 10.4 years (LW-HAC; overlay–base correlation 0.89–0.92);
  - 0.066 for KOSPI over 1997–2026 (DLA-K11).
  - v1.2's 0.034 ⁄ 0.052 hold only for add-on legs, where the correlation is ≈ 0.98: KRW 0.021, rates 0.022, R-04 0.035 (QF3-A3; QF4-A7; DLB-T5a).
- **Detecting a +0.05 Sharpe effect needs about 150–330 years of data:**
  - 146 ⁄ 190 years at one-sided 5% and 50% power (the basis v1.2 used);
  - 244 ⁄ 317 years at the gate's one-sided 10% and 80% power (SE 0.061 ⁄ 0.130, T_years = sessions ⁄ 252; G-PWR-01 gives 241–246 ⁄ 319–330 across SE estimators).
- **MDE80** is 0.13 (US) and 0.28 (KOSPI). PC-3's power at a true ΔSR of 0 is 0.30 on KOSPI 2016–26 (PX1).
- **Under v1.2's PC-1, a vol target with zero true Sharpe cost was REJECTed ≈ 55–70% of the time at 11–36 years** (DLB-T5b). In a GJR-t world the rate falls with history: US 67% → 28%, KOSPI 57% → 14%.
- **Base rate for a de-risk overlay:** 0.00 to +0.10 Sharpe, and 3–6 pp of max drawdown. Expect the grid median, not the best cell.
- **Consequence.** A de-risk overlay can almost never show outperformance. Its protective claim is judged by the CARD-P class (§8.7), never by step 5.

### 8.6 Episodes v2: objective market-own episodes, the shock-type table and leave-one-crisis-out

**The gate's episodes (R-22; Resolution 11).** PC-4 and PC-7 use **objective market-own episodes**. These replace the v1.2 label windows as the gate's input.
- **Rule.** An episode is an alternating bear / bull phase of at least θ, measured on the market's own official closes.
  - θ = 0.20 for KOSPI and by default.
  - θ = 0.15 for the S&P 500 and for any index that the frozen rule below declares low-volatility in the registry.
  - Any other market's θ is written before its first card run by the frozen rule θ = 0.15 if its long-run median SMA20 vol is < 0.18, else 0.20 (R-22; default, judgment).
  - Dating starts at the first close of the declared history.
  - An episode window runs from the first return after the peak close to the trough.
  - An open episode (a bear not yet confirmed over by a θ rally) is printed and counts toward neither PC-4, PC-7 nor a re-gate.
  - The rule is adopted once, for every card, before any formal run, and counts as one revision in every family ledger.
- **Counts** (QF4-M6; T-EPIS-01):
  - KOSPI 1997–2026: 18 episodes, 12 of them with troughs before 2008;
  - KOSPI 2016–26: 4 episodes (the v1.2 table listed 9 windows);
  - S&P 1990–2026 at 15%: 16 episodes.
- **Sufficiency.** A continuous rule needs at least 5 objective episodes in its sample (PC-7). A Korean card on 2016–26 alone is therefore INSUFFICIENT DATA by construction (4 episodes), and the long history decides Korea (§8.9).
- **Sep-2026 is not an episode in any market** (Resolution 12). Card headers declare the exclusion; it is asserted on the rule's output (T-EPIS-01), never coded as an override.
  - KOSPI rose 0.26% from 31-Aug to 30-Sep. Its worst intra-window point was −6.0%, less than one monthly σ at rv20 ≈ 32%.
  - The S&P fell 0.45%, with a worst point of −2.5%.
- **Regime tags.** Every episode carries the R-20 tags of its peak date. Korean episodes before 2002-10 show:
  - the ±8 / 12 / 15% price limits;
  - Saturday sessions (before 1998-12-12);
  - the 1997 FX peg;
  - no ETF.

**What the rule does to the Korea card: the forking path, disclosed.** The rule rescues the card's PC-4.
- **The definitive cell** (1997-04 → 2026-10, ETF 3 bp; DLA §2.2):
  - objective episodes: 14 of 18 positive, maximum share 0.174;
  - the v1.2 table: 4 of 11 positive, maximum share 0.493 (July 2026, against a limit of 0.50).
- **Before 2008**, 10 of the 12 bears are positive (11 of 13 with the 2007–08 bear). Examples: 1997-H2 +14.5 pp; 1998-H1 +19.9 pp; 2000 +10.2 and +7.9 pp.
- **The 1997–2015 holdout** has 12 of 14 objective episodes positive. Under the v1.2 table it was INSUFFICIENT DATA, because only 3 windows fall inside it (DLA-K9).
- **Why it was adopted anyway.** All three chairs adopted the rule on design grounds, blind to every card, including the cards it hurts:
  - the v1.2 table had no window before 2008;
  - it admitted non-drawdowns such as Sep-2026;
  - a ≥ 20% bear market is the conventional definition, not a tuned threshold.
- **Printed beside it.** Every card prints the §8.6-table result next to the gate's result (`pc4_section_8_6`).

**Shock-type table (printed only; used for leave-one-crisis-out).** The v1.2 named windows stay as a fixed, printed sensitivity. None of them enters PC-4 or PC-7 in v2. The last column is the definitive Korea cell's return vs S in each window (DLA §2.2; raw-return flag, ETF 3 bp).

| Window | Dates (returns after the start close) | Shock type | Role in v2 | R-06 KR cell vs S (pp) |
|---|---|---|---|---|
| GFC | 2008-09-01 → 2009-03-09 | credit recession | printed | +9.1 |
| 2009 rebound | 2009-03-09 → 2009-06-30 | V-rebound (momentum crash) | cost episode (printed) | −6.9 |
| 2011 | 2011-07-22 → 2011-10-03 | policy / sovereign | printed | −0.6 |
| 2015–16 | 2015-08-10 → 2016-02-11 | China / EM / oil | printed | −1.3 |
| 2018Q4 | 2018-09-20 → 2018-12-24 | rates / policy | printed | −1.6 |
| 2020 crash | 2020-02-19 → 2020-03-23 (KOSPI → 2020-03-19) | pandemic | printed | +3.9 |
| 2020 rebound | 2020-03-23 → 2020-06-08 (KOSPI from 2020-03-19) | V-rebound | cost episode (printed) | −15.5 |
| 2022 | 2022-01-03 → 2022-10-12 (KOSPI → 2022-09-30) | inflation tightening | printed | −3.8 |
| Aug-2024 | US 2024-07-16 → 2024-08-05; KOSPI 2024-07-31 → 2024-08-09 | carry / leverage unwind | printed | −3.3 |
| Dec-2024 (KR) | 2024-12-03 → 2024-12-09 | domestic political | printed | −0.8 |
| Apr-2025 | US 2025-02-19 → 2025-04-08; KOSPI 2025-03-28 → 2025-04-09 | policy (tariffs) | printed | −1.4 |
| Mar-2026 | 2026-02-27 → 2026-03-31 | oil / geopolitical | printed | +9.0 |
| H1-2026 bull (KR) | 2026-01-02 → 2026-06-30 | bull-tax check | cost episode (printed) | −31.5 |
| Jul-2026 | 2026-06-22 → 2026-07-30 | Korea leverage unwind / momentum crash | printed | +21.4 |
| Sep-2026 | 2026-08-31 → 2026-09-30 | rates (term premium) | **not an episode** in any market (Resolutions 11 and 12); kept for the record | — |

- **Return dates behind the golden values** (v1.2 note, unchanged).
  - The convention "returns after the start close" holds for every US window and most KOSPI windows.
  - Four KOSPI windows include the start-date return:
    - Aug-2024 uses returns dated 2024-07-31 → 2024-08-09;
    - Apr-2025 uses 2025-03-28 → 2025-04-09;
    - Mar-2026 uses 2026-02-27 → 2026-03-31;
    - H1-2026 uses 2026-01-02 → 2026-06-30, the calendar half-year from the 2025 year-end close.
  - Golden tests and the printed shock-type lines must use these return dates. Under the strict reading, buy-and-hold would differ by more than the Level-1 tolerance: H1-2026 would read +96.7% instead of +101.1%, and Aug-2024 −6.6% instead of −5.5%.
  - On a sample that starts in 2016, the KOSPI 2015–16 window is truncated to 2016-01-04 → 2016-02-11.
- **Leave-one-crisis-out by shock type** is printed for six groups: credit recession, inflation tightening, policy shock, leverage unwind, oil / geopolitical, pandemic.

**Post-trough window and cost episodes (printed, never gated in v2).**
- **What every card prints:**
  - for each objective episode, the rule-vs-S return from the trough to 63 sessions after it;
  - the three cost episodes: the 2009 rebound, the 2020 rebound and H1-2026.
- **Why.** Benefits are measured from peak to trough, so the cost of exiting and re-entering is invisible to PC-4 (QF7-A20).
  - The jump model's US exits came 46–179 sessions after the troughs, missing +15% to +57% (2020: 111 sessions, +57%).
  - The Korea card's median re-entry lag is 17 sessions. Its cost lines read −6.9 / −15.5 / −31.5 pp, and −13.2 pp from the July-2026 trough to 30 Sep (DLA §2.2).
- **Not in PC-4 in v2.** Adding the window to PC-4 was proposed (QF7-A20) and not adopted (chair majority). A later package version may adopt it only blind, as a new version that re-runs every card (§8.1.3).

**Holdouts, and what counts as out of sample.**
- **2022–26 is a reported stress-test set, not a holdout.** It has been dissected episode by episode.
  - Its SE(ΔSR) of ≈ 0.08–0.09 was computed at the add-on-leg correlation (≈ 0.98; R2-E1).
  - A market vol target's SE over the same span is larger: for KOSPI VT20 vs S it is 0.130 over 10.4 years.
- **The header names the out-of-sample line.** A long-sample card declares one primary out-of-sample line in its header. For R-06 KR, the ETF era to 2025-12 is gated, and the 2002-10 → 2015-12 pre-design line is printed.
- **Forward records are falsification alarms, never validation** (§8.8). An upward re-gate needs new history: a new, confirmed objective episode for a continuous rule (the data end at its confirmation close plus the 63-session post-trough window; R-22), or the tier onset count for a discrete rule.
- **The locked holdout from 2027-01-01** remains for the inflation-conditional hypotheses (BACKLOG).
- **The pre-registered 2027–28 forward head-to-heads** are settling tests for research questions. They validate no card.
  - SJM50 vs BAND200 vs VT15 at 50 bp on the US and on the never-used STOXX50E and TWII. Its only outcome is whether an SJM card may be *proposed*; that card is then judged on history.
  - The breach rates of the holiday-gap VaR display (§8.10).

**Forking-path disclosure, printed on every affected card.** Two v2 conventions were chosen after their effect on a card was visible:
- the episode rule (Korea's PC-4, 0.493 → 0.174);
- the step-3 N rule (R-03 passes at N_equiv and is borderline at the linear N̂).

Both were adopted on design grounds, blind to every card, and the alternative result is printed for both. No further convention may be adopted under this package version (§8.1.3).

### 8.7 The protective-overlay card class (CARD-P) v2

**Why the class exists.**
- **Outperformance is the wrong claim.** A de-risk overlay is worth 0.00 to +0.10 Sharpe. With SE(ΔSR) vs S of ≈ 0.061–0.130 for the market vol targets, detecting +0.05 needs about 150–330 years, so step 5 can pass only by luck. That says nothing about whether the rule protects.
- **QUANTGEN's own precedent.** Card E1 (trend switch, US ETF sleeves) cut max drawdown to −15% against −27%, and was still REJECTED because its claim was outperformance: out-of-sample Sharpe 0.84 vs 0.95, p 0.75. The app keeps it on the ETF page as a descriptive sleeve "because the drawdown line is worth seeing".
- **v1.2's drawdown gate could not decide protection either** (X-PX1-N2; EX1; DLB-T5b):
  - single-path ΔMDD has a bootstrap SD of 7.4–7.8 pp (US) at every length from 10 to 100 years;
  - the same Korea card shows +12.7, +3.8 or +10.6 pp depending only on the start date;
  - ΔMDD ≥ 3 pp certifies 3 of 20 timing-free KOSPI placebos;
  - a zero-cost vol target was REJECTed ≈ 55–70% of the time at 11–36 years.
- **v2 keeps the class and changes its evidence.**
  - Protection is shown on fixed-horizon tail losses, whose sampling error shrinks with the sample (US SD 0.052 → 0.020 from 10 to 100 years).
  - Sharpe non-inferiority stays binding.
  - Drawdown lines are printed, not gated.
  - The class applies only to rules whose output never exceeds 1.0. It is stated once, before any macro card runs (§8.1.3).

**Comparator S.** S is the overlay-off book × the mean multiplier: constant weight, same days, no cost. Any constant de-gearing lowers drawdown and tail loss, so protection must be shown against S, not against buy-and-hold.

For an incremental card, "overlay-off" is the book without the factor under test:
- the vol-targeted book, for the trend card (R-28);
- the declared book without the steps, for the step-down card (R-31);
- the invariants-only book, for the stack card.

**Card books (R-22 rule 6, frozen; C-2).** A card's on, off and S books apply the data invariants and the bounds, and exclude the R-07 hard stop and caps, except where the card's claim concerns them (R-31 includes the hard stop). Every card prints a `with_risk_layer` line. The hard stop and caps are judged once, on the composed recommended book, by the stack card below. For KOSPI VT20 the two conventions differ materially: maximum drawdown −45.3% without the hard stop, −56.4% with it over 24 HALTs (Check C2).

**Checks.** The checks are frozen in the package; R-21 holds their definitions. f is the selection factor that R-23's `step3()` computes from the family ledger; a card never declares it.

| ID | Check | Pass condition (at 1× cost unless stated) | Replaces / extends gate step | A failure leads to |
|---|---|---|---|---|
| **PC-1′** | Tail legs | ΔES95 of overlapping 21-session **and** 126-session returns, rule vs S. Each point must be > 0, with a one-sided stationary-bootstrap p × f ≤ 0.10 (mean block 250 sessions; p is the uncentred bootstrap percentile, z printed). Monthly cards use 1 and 6 months | step 5 | A point ≤ 0 → REJECT. Both points > 0 but a p × f > 0.10 → INSUFFICIENT DATA (inconclusive). A leg that fails only at 2× → REVISE |
| **PC-2** | Coverage | Tail-exposure ratio ≤ 0.90 (point), with its 90% bootstrap CI printed. The daily ratio is used, unless the acceptance test adopted the horizon-matched ratio for every card | step 5 | REJECT |
| **PC-3** | Sharpe non-inferiority vs S | δ = 0.10, the top of the de-risk base rate. p_ni = max(p₁₀, p_max(21, PW(ψ))) × f ≤ 0.10, from the studentized bootstrap | step 2 (the book's own interval is printed) | A point < −δ at 1× → REJECT; at 2× → REVISE. A p_ni × f > 0.10 → INSUFFICIENT DATA (`inconclusive`; `underpowered` if MDE80 > 0.10) |
| **PC-4** | Episodes | On objective market-own episodes (§8.6): ≥ 3 with a positive benefit vs S, and no episode above 50% of the summed positive benefit | step 5 + leave-one-crisis-out | Fewer than 3 positive → REJECT. Concentration alone → INSUFFICIENT DATA (inconclusive) |
| **PC-5** | Years | ≥ 60% of calendar years positive for the overlaid book. The share of years lagging S is printed | step 8 | REVISE (extend the history) |
| **PC-6** | Plateau | ≥ 50% of the neighbours (the 8 Moore neighbours on the frozen two-axis grid of the rule type; the 2 axis neighbours on a one-axis rule; `gate.card_p_v2.pc6_axes`) keep ≥ half of the centre's ΔES_21 and ΔES_126, and a PC-3 point ≥ −δ | step 7 | REVISE (widen the grid) |
| **PC-7** | Sufficiency | Discrete rules: ≥ 30 onsets, de-clustered at the rule's own lookback (or a pooled-onset rule declared before any run, §8.3). Continuous rules: ≥ 5 objective episodes. Both: ≥ 756 + 126 sessions | decided first | INSUFFICIENT DATA (sufficiency) |

Steps 1, 3, 4 and 9 apply as in §8.1.1:
- **Step 1:** walk-forward when anything is searched.
- **Step 3:** DSR vs 0 and PSR vs S are printed. The selection factor applies to PC-1′ and PC-3.
- **Step 4:** PBO on the protective objective. PBO > 0.2 with the winner losing is a REJECT.
- **Step 9:** 60% of the ΔES legs and of ΔMDD are printed.

**Caps.** A cap only lowers a verdict. It never raises one, and it never creates a REJECT.

| Cap | Trigger | Caps the card at | Reason code |
|---|---|---|---|
| Do-no-harm | ΔMDD < 0 **and** ΔCDaR95 < 0 at 1×: the rule is deeper and longer under water than S | INSUFFICIENT DATA | `do_no_harm` |
| Timing-fragile (R-34) | FR > 0.5, or ΔSR changes sign by lag 2 | INSUFFICIENT DATA (Tier B treatment; live, time-stamped feeds required) | `timing_fragile` |
| Claim line | The card misses a claim line declared in its header (R-28: stacked ΔMDD on VT ≥ 3 pp) | INSUFFICIENT DATA | `claim_not_shown` |
| Stability floor (acting long-sample cards, R-22) | A REJECT at any start in the band (a frozen shape); a PASS count below the shape's integer floor (R-06 KR: 22 of 32; R-29: 8 of 10 decade starts); or a REJECT in either calendar-midpoint half | INSUFFICIENT DATA | `stability` |
| Estimator calibration (R-30) | SMA20 fails B5, or a challenger fails Stage 1 | REVISE | `estimator_calibration` |

A drawdown line on its own never REJECTs (red line Q2). The acceptance test's CDaR guard exists only if a negative control would pass (§8.1.3).

**Gating lines.** Some headers declare more than one gating line; R-06 KR declares the full span and the ETF-era line to 2025-12. Such a card receives the **worst** of its gating lines' verdicts, in the order REJECT < INSUFFICIENT DATA < REVISE < PASS. Printed lines never gate.

**Verdict order.** It is coded once, in `cardp_evaluate` (R-21).
1. **INSUFFICIENT DATA (sufficiency).** PC-7 fails: too few onsets (Tier B), too few objective episodes, or too short a history.
   - Route: new history only. The card is re-gated, as one counted revision, when the extended sample reaches the tier count (§8.8).
2. **REJECT**, at 1× cost, on any of:
   - a PC-1′ point ≤ 0;
   - PC-2 above 0.90;
   - the PC-3 point ΔSR < −δ;
   - fewer than 3 positive objective episodes;
   - PBO > 0.2 with the winner losing.

   The data say the rule does not protect, or protects at too high a price. No cap can lift a REJECT.
3. **INSUFFICIENT DATA (inconclusive or underpowered).** No REJECT condition holds, but a PC-1′ p-value or p_ni, multiplied by f, exceeds 0.10, or PC-4 fails on concentration alone.
   - Route: new history only. The card is re-gated when new history adds an objective episode (continuous rules) or onsets (discrete rules).
   - There is no forward-record route.
4. **REVISE.** Everything holds at 1×, but one of these fails:
   - a PC-1′ leg or the PC-3 point at 2× cost. Permitted fix: **lengthen the holding period** with a slower estimator, or a banded or less frequent rebalance. Each is a new card or a counted revision under R-26 and R-30. Never lower the cost.
   - PC-6. Permitted fix: **widen the grid**.
   - PC-5. Permitted fix: **extend the history**.
5. **Caps** (table above) are applied to a PASS or a REVISE.
6. **PASS.** Everything above holds.
   - The card's registered label is shown with the verdict. The default label is "protective: reduces tail losses vs a same-exposure static book; not expected to outperform".
   - The insurance premium is shown beside it: the share of years lagging S, the timing return and the bull tax.
   - The card's build status is the header's `build_status_on_pass` (§8.1.2).

**Printed, never gated** (R-21):
- ΔMDD, ΔCDaR95 and daily ΔES99, with bootstrap bands;
- the GJR-null percentile;
- the 20-shift placebo panel;
- time under water, worst-day coverage, CVaR(5%) and the re-entry lag;
- the post-trough window and the cost episodes (§8.6);
- rolling 5-year block comparisons against S;
- DSR vs 0 and PSR vs S;
- the timing profile (R-34);
- the execution variants and the stress-cost line (R-26).

**The gate-acceptance test** (R-21 rule 9). It runs once, inside the freeze procedure of §8.1.3. On existing numbers the package is expected to pass it:
- **Size.**
  - Under PX1's legs, ES-leg placebos pass at 0% (US) and at ≤ 5.3% (KOSPI) of 300 placebos; across all the PC-1 replacements PX1 tested, false passes stay ≤ 6.3%. A placebo passes when both PC-1′ legs pass at 1× (R-21 9(a)).
  - EX1's three-leg version passed 0 of 60.
- **Power.**
  - The US 5-day VT at 50 bp is a REJECT through the PC-3 point (ΔSR −0.29), even though its ΔES21 is +1.30 pp, with ΔMDD −12.46 pp and ΔCDaR −19.45 pp.
  - The 10-day VT is a REJECT (ΔSR −0.106).
  - EX1's post-shock-week rule is expected to read INSUFFICIENT DATA: its p_21 is expected above 0.10 (z 1.278 is printed; it sits within tolerance of 1.2816, so it is not asserted as a point), its ΔSR is −0.093, and the do-no-harm cap applies (ΔMDD −9.1 pp, ΔCDaR −11.1 pp).
  - No control passes, so the CDaR guard is not expected to be needed (QF chair §0.3).

These are expectations, not results. Only the frozen acceptance report counts.

**The stack card** (R-02; red line E3; X-EX1-N2). Several de-risk factors acting together form an exposure path that no single card sees. The three chairs' conditions are merged:
- **When.** The book builder generates a stack CARD-P before a second (or further) de-risk factor joins the recommended book of a market. When several factors pass in one batch, they join in header-commit order, fixed before the run. "De-risk factor" is defined in R-02 (6); invariants, `INVARIANT_STEP` steps included, are not de-risk factors.
- **What is judged.** Both of these, under the frozen package:
  - (a) the joining factor, judged incrementally on the current recommended book (its own card, where that is its declared book);
  - (b) the composed book, composed = vt × min(1.0, overlay₁ … overlayₖ, ladder, post_rearm_cap), with the hard stop and caps applied (with R-31, whose claim concerns the hard stop, the only card evaluations that include them; R-22 rule 6), as one CARD-P against the invariants-only book, with S = that book × the stack's mean multiplier.
- **Printed.** The share of days at ≤ 0.25× total exposure, and rebound capture in the cost episodes (§8.6).
- **Consequence.** The joining factor acts in the recommended book only if both (a) and (b) read PASS. Otherwise it stays in the specification book, labelled with the stack verdict. The rules store refuses a product-composed stack (R-02, §10).
- **Evidence** (EX1, KOSPI at 3 bp; buy-and-hold made +47.3% in the 2020 rebound):

| Book | Sharpe | MDD | Average exposure | Days at ≤ 0.25× | 2020 rebound |
|---|---|---|---|---|---|
| VT20 | 0.454 | −45.3% | 0.85 | 0.8% | +23.9% |
| VT20 × SMA10m | 0.538 | −35.6% | 0.69 | 8.2% | +15.5% |
| VT20 × SMA10m × ladder (product) | 0.574 | −31.8% | 0.54 | 31.0% | +7.6% |
| VT20 × min(SMA10m, ladder) | 0.535 | −36.3% | 0.59 | 11.2% | +12.6% |

In the US, the product stack sits at ≤ 0.25× on 17.9% of days and captures +4.5% of a +46.9% 2020 rebound.

**Claims registered on the v2 CARD-P cards.**
- **R-06 KR:** crisis-clustering insurance (the label is in §8.4). PASS requires the four conditions in §8.9.
- **R-28:** "slow-bear protection via the volatility state".
  - Judged stacked on the vol target, with the claim line ΔMDD ≥ 3 pp (a cap, never a REJECT).
  - The GJR-null percentile and the snooping haircut are printed.
  - There is never a Sharpe claim.
- **R-29:** settled on daily history from 1926: PC-1′ at 1× and 2×, a PASS at ≥ 8 of the 10 decade-spaced starts with no REJECT at any of them, and a full-span v2 PASS.
- **R-31:** "protection in persistent drawdowns; time-boxed; no Sharpe claim".
- **Any protective rule:** a Sharpe or predictability claim is refused (§8.2).

### 8.8 Forward records, re-gating and demotion v2 (R-25)

**Forward books.**
- From its header commit, every card runs in `core/engine`'s simulated order book as three books: overlay-on, overlay-off and, for a CARD-P, S.
- Each FORWARD-SIM card (R-28, R-29) and each refusal book (R-11, R-12) has its own book. The recommended book reads none of them (I-03; R-35).
- Each decision writes timestamped `macro_state` and `overlay_decision` artifacts: `decision_utc`, and every input with its `available_at_utc` and `value_status`. The record is therefore reproducible and auditable.
- **Integrity rules (binding).**
  - (a) A forward record starts at the first decision written by the live `macro_daily` workflow after the header commit, so never before M8. It is never backfilled; replays (T-REPLAY-01) are audits only.
  - (b) A decision whose artifact has `generated_at_utc` after the opening of that market's next session is `late`. The forward books carry the previous weights for that session, and the late artifact is display-only. A missed decision carries the previous weights the same way. Late and missed decisions, decisions whose acting or forward_sim input failed closed, and every HALTED or DISARMED decision of the card's forward books are counted and printed on the card page; more than 10% of a card's scheduled decisions in any rolling 12 months (default, judgment) is an operational integrity trigger (R-25).
  - (c) A change of `git_hash` or `config_hash` between consecutive forward decisions is a governance event. A change inside the card's acting-code manifest outside a registered revision is an integrity trigger.
  - (d) The forward S book uses the design-sample m̄ written in the header, never the forward realised mean (which is printed beside it).
  - (e) Forward on, off and S books follow the card-book risk-layer convention of R-22 rule 6.

**What a forward record can and cannot do** (red lines P3 and Q3).
- **It can:** act as a falsification alarm and an integrity check, and demote a card.
- **It cannot:** raise a verdict, turn INSUFFICIENT DATA into PASS, or count toward sufficiency.
- **Why:**
  - Twelve forward months add only 3–10% of the information. PX1: the KOSPI SE moves from 0.130 to 0.124 and PC-3 power from 0.305 to 0.317. On the long Korea sample, one more year moves the SE from 0.066 to 0.065.
  - The v1.2 CARD-P trigger fired in 22% of real KOSPI vol-target records and in 22% of timing-free placebos (US: 42% vs 34%; EX1).
- **Honesty line**, on every card page: "12 months of forward record can only detect catastrophic decay." Beside it is the card's calibrated 2.5% threshold: −0.20 Sharpe for R-03, −0.39 for the KOSPI vol target, −0.73 for the US vol target (QF3-A7).

**Re-gating upward: new history only.**
- **When:**
  - a continuous rule is re-gated when new history adds an objective episode (§8.6) in its market;
  - a discrete rule is re-gated when the extended sample brings its de-clustered onsets to the tier count (§8.3).
- **How:** the re-gate runs the full frozen package on the extended sample, as one counted revision. The forward window's own statistics are printed and are never used to raise a verdict.
- **The v1.2 checklist is withdrawn as a route.** It required ≥ 12 forward months, switches within budget, zero lag-audit violations and a re-run with the forward record appended. Its integrity items are now demotion triggers.

**Demotion triggers.** Every statistical trigger uses **whole-book NAV**, with per-card attribution printed. Sleeve NAV is never the denominator.

| Kind | Trigger | Budget |
|---|---|---|
| Operational and integrity | Any of: a lag-audit violation; an edit to an acting parameter outside a card revision; a provisional or stale input reaching an acting decision (R-01, R-19); switches above the 99th percentile of the card's Poisson or negative-binomial fit on the design sample (this replaces "2× the budget") | Immediate; outside the budget |
| Catastrophic bound, CARD-P | All three over a rolling 12 months: forward ΔMDD vs S ≤ 0, which means **no protection** (v1.2 printed the sign the wrong way round, "≥ 0"); forward ΔES95 of 21-session returns vs S ≤ 0; forward 12-month ΔSR vs S below the design sample's 2.5th percentile | Inside the budget |
| Catastrophic bound, CARD-O | Either of: the 6-month gap (comparator minus on) on book NAV exceeds 2σ of its tracking distribution, pre-registered on the design sample; the 12-month ΔSR vs the comparator falls below the design sample's 2.5th percentile | Inside the budget |
| Sequential | A one-sided monthly CUSUM on the paired differences, with k = 0.25 and h calibrated by bootstrap for an in-control ARL of ≥ 20 years (a naive h = 8 alarms 10–13 times a decade) | Inside the budget |

- **Book-level false-demotion budget (owner decision D4).**
  - At most 10% a year across all statistical triggers, split equally across active cards (≈ 5% each with two cards). A card's split and its thresholds are fixed when its forward record starts and are never recalibrated when cards are added (R-25).
  - Each card's split is verified on a 20-shift panel of its design-sample record before its forward record starts.
  - The owner may tighten the budget.
- **Why v1.2's triggers were replaced:**
  - fixed triggers fired in 29.7%, 50.0% and 69.4% of years for R-03, the KOSPI vol target and the US vol target (QF3 §4.9);
  - at sleeve level, the 6-month 2% rule fired in 31% of 12-month records, against 3.3% for a card at 20% of book NAV (EX1);
  - a CUSUM needs about 40 months to detect performance that is flat to its benchmark.
- **Never a demotion trigger:**
  - a bull-market lag alone, which is the insurance premium;
  - the hard stop. The R-07 hard stop is the book-level kill: a governance review event with an automatic, rule-defined re-arm (§3.8). It is not a demotion, and it makes no protection claim.

**After a demotion.**
- The card's output leaves the recommended book.
- The card gets a new revision with a new header and a 6-month lockout. The verdict is set by rule (default, judgment; council to confirm): REVISE after an operational or integrity trigger (repair, then a counted re-run), REJECT after a catastrophic or CUSUM trigger. The lockout applies to the family × market (R-25).
- Whole-book NAV unavailable on more than 2 consecutive decisions is an OPS HALT of the books it values; the forward record marks the gap (R-25).
- Demoting a CARD-P never removes the risk-layer invariants.
- A pre-declared R-18 re-anchoring is not a new card.

**Weekly brief and monthly card page.**
- ΔSR, ΔES21 and ΔMDD vs S (or vs overlay-off), with the CUSUM state and any alarms;
- time under water, worst-day coverage and the re-entry lag;
- the bull tax for Korea, and switch counts against the card's 99th percentile;
- lag-audit status and the rules-store edit log;
- the honesty line;
- forward-on, forward-off and S simulated P&L.

### 8.9 Indicative verdicts v2 (not a run of QUANTGEN's gate)

**What this table is.** For every card, it gives the verdict that the v2 rules imply from numbers the research programme has already computed:
- R4b;
- the QF papers;
- the two data labs (DLA, DLB);
- the cross-examinations (PX1, PX2, EX1, EX2).

All of these ran on local reference data. Each number carries its source. Where a v2 leg has not been computed, the cell says so. Nothing in the table was computed for this spec.

**What it is not.** The formal verdicts come from `docs/macro_overlay_study.py`, run on QUANTGEN's own data, engine and walk-forward under the frozen package (§8.1.3). Until then every macro card is NOT_RUN.

Unless noted, the numbers use R4b's raw-return convention (cash at 0). The formal cards use excess returns (R-22).

| Card | Class / tier | Book · cost | Key numbers (source) | Indicative v2 verdict | Build status and route |
|---|---|---|---|---|---|
| **R-03** momentum own-vol scaling (US; French Mom) | CARD-O / A | US shares via KIS, 50 bp, both legs (turnover 0.85) | ΔSR vs unscaled +0.273; one-sided p ≤ 0.001 at 10- and 251-session blocks; SR at 2× 0.631 (R4b). Years: 70.3% positive net. The books are identical in 17 of 37 years (cap binding); in the other 20, R-03 had the higher Sharpe in 15 gross and 11 net (DLB-T2d). Step 3: deflated ΔSR 0.98 at N_equiv 6.3 and 0.947 at linear N̂ 12.6, break-even N ≈ 11.9; z 3.84 / 3.29 / 2.99 ≥ 2.50 (Resolution 5; EX1; QF chair). SE ladder 0.072 → 0.091, z 3.81 → 3.0 (QF3 §4.3). PBO 0.000 (family) / 0.009 (grid); plateau 100% (QF3 §4.2). Timing FR 0.03 (QF2) | **PASS** (indicative), flagged "step 3 borderline" | BUILD NOW. The sleeve-scale function is built in M4; the formal card runs on QUANTGEN's own sleeve in M7, after the package freeze (§8.1.3 steps 4–5), and stays indicative until then. Its factor enters the recommended book on a formal PASS |
| R-03 revision: scale-free target (expanding-median σ126; QF5-M1) | CARD-O / A | As R-03 | Research phase, already ledger rows. On a long-only active proxy the fixed 12% target binds on 9.8% of days, the scale-free target on 71% (QF5-A4, M1). US full-sample ΔSR +0.380, against +0.303 at the fixed target (QF5) | NOT_RUN | Header committed blind (§8.1.3 step 4). One more trial in the R-03 ledger; step 3 is recomputed on the enlarged ledger |
| R-03 revision: variance scaling, min(1, (0.12 ⁄ σ)²) (X-PX2-N3) | CARD-O / A | As R-03 | Research phase: +0.126 net Sharpe over R-03. The D&M gate adds +0.072, of which the pure mean-forecast increment is +0.039 (p 0.07) (PX2) | NOT_RUN | As above. Registered "instead of the D&M gate" |
| **R-04** D&M bear-state gate on R-03 | CARD-O / A-provisional (route closed) | 50 bp, both legs | ΔSR +0.072 (p 0.018 / 0.010; R4b). 7 US spell onsets; 34 pooled across four regions (pooled add-on +0.080, p 0.0002). Deflated add-on 0.77 at N_equiv 6.3 (0.767–0.79 across checks); z 2.06–2.08, below both the N_eff Bonferroni bar of 2.15 and the ≤ 8-cell bar of 2.50. The BL-C12 out-of-region holdout passed in 1 of 3 regions (Resolution 5; QCE-115) | **step 3 FAIL**; not recommended | SPECIFICATION BOOK, floor 0.5, labelled "step 3 FAIL". No pooled route exists for a card already run; a pooled card would be a new counted revision |
| **R-06 KR** VT20, formal long-history card (revision 2) | CARD-P / A (18 objective episodes) | KRX ETF line, 3 bp (futures line, 5 bp, declared before Oct-2002) | **v1.2 checks, 1997-04 → 2026-10** (DLA-K8): ΔMDD +12.7 pp (2×: +12.5); tail 0.68; ΔSR +0.026 (2×: +0.021); p_ni 0.052; years 70%; plateau 0.875; B5 passes; the futures book at 5 bp also PASSes. **PC-4:** 14 of 18 objective episodes positive, max share 0.174 (0.493 on the §8.6 table). **v2 legs:** ΔES95 of 21-day returns +2.9 pp, z 2.3 (DLA-K10; EX1: z 2.16); the 126-session leg +6.4 pp, z not yet computed (PX1, via the QF chair); ΔES99 daily z 4.3; ΔCDaR95 +7.1 pp. **Excess returns:** ΔSR +0.006, p_ni 0.078 (PX2). SE 0.066 (DLA-K11). **Resolution 1 conditions:** (ii) the ETF era 2002-10 → 2025-12 PASSes on v1.2 checks (ΔMDD +11.9 pp, p_ni 0.040; EX2); (iii) p_ni ≤ 0.10 at 70% of PX2's 33 starts (PX2's set; the declared band has 32), with no REJECT in 72 monthly or 40 quarterly starts (DLA; EX1); (iv) both calendar-midpoint halves INSUFFICIENT with no REJECT condition (ΔMDD +8.2 / +5.1 pp; p_ni 0.11 / 0.21; QF6 pilot). **Printed:** 1997–2002 REJECT (ΔSR −0.20; EX2); 2016–25 REJECT (tail 0.95, ΔSR −0.079); rolling decades 2 PASS / 3 REJECT / 15 INSUFFICIENT (EX1); timing return −1.8%/yr at variance ratio 0.59 (PX2); the EWMA(0.94) line INSUFFICIENT (PC-4 0.51 on the §8.6 table). **Card-book convention:** these numbers exclude the hard stop and caps (R-22 rule 6); with the hard stop, VT20's MDD is −56.4% over 24 HALTs, against −45.3% (Check C2) | **Expected v2 verdict: INSUFFICIENT DATA** (through f; R2-C1). **PASS** (indicative, fragile) on v1.2 checks only. f is computed from the R-06 ledger and exceeds 1 (R4 compared 20- vs 60-session windows and caps 1.0 vs 1.5 on 2016–26 before SPEC v1.1), and the maximum over the defensible row-set readings binds (R-23). Indicative f on Yahoo 2016–26 difference series vs S (`council/ASPEC_R2_risk_officer.md` §6): 1.26–1.30 on R4's rows alone, 1.49 with the DL-A grid, 2.87 family-wide with the US VT15 rows (N_clusters 2). PC-3 needs p_ni × f ≤ 0.10: on the indicative excess-return p_ni 0.078, any f > 1.28 gives INSUFFICIENT DATA (`underpowered`, since MDE80 = 2.1232 × 0.066 = 0.14 > 0.10), so with the DL-A seed of §9.5 R-06 KR reads INSUFFICIENT DATA under every reading. The 126-session leg's p and step-4 PBO on the protective objective are also not computed (the Sharpe-objective grid PBO 0.28 / 0.36 is printed) | NOT_RUN, so SPECIFICATION BOOK. The status stands: a formal v2 PASS on all four conditions, at the computed f → **BUILD-AS-INSURANCE**, with the crisis-clustering label (§8.4). On current evidence the formal run is expected to return INSUFFICIENT DATA (previous column), so the card is not expected to build: it stays a labelled control in the specification book, re-gated only when new history adds an objective episode, and no convention may be changed to rescue it (R2-C1). REJECT → archive. The forward record is a falsification alarm only |
| R-06 KR VT20, stock book | CARD-P / A | KRX stocks, 35 bp | 1997–2026 (DLA-K8 grid): ΔMDD +10.9 pp (2×: +8.3); ΔSR −0.020 (2×: −0.071); p_ni 0.141; plateau 0.625. 2016–26 (R4b; QCE-117): ΔMDD +4.1 pp (2×: +3.8); ΔSR −0.029 (2×: −0.061); p_ni 0.32; plateau 0.375 | **INSUFFICIENT DATA** (inconclusive: p_ni 0.141) | On record only; it never acts, because a stock book cannot carry a market-gross scalar (R-26) |
| R-06 KR VT20, 2016–26 (the v1.2 card, revision 1) | CARD-P / 4 objective episodes | KRX ETF line, 3 bp | ΔMDD +4.4 pp (2×: +4.4); tail 0.82; ΔSR +0.001; p_ni 0.25 (0.246 on the official close; DLA §7); 3 of 9 v1.2 windows positive, with July 2026 = 59% of the benefit; years 73%; plateau 0.625 (R4b). PC-1′: ES z 1.82 / 1.13 (Resolution 4). SE 0.130; MDE80 0.28; PC-3 power at a true 0 of 0.30 (DLB-T5a; PX1) | **INSUFFICIENT DATA**: sufficiency (4 objective episodes, < 5), and also inconclusive on PC-1′. Under v1.2's PC-1 it passed: a disclosed flip | Superseded by revision 2, on which it is printed as a line, together with 2016–25 alone (REJECT: tail 0.95, ΔSR −0.079) |
| **R-06 US** VT15, registered card | CARD-P / A | US shares via KIS, 50 bp, daily | ΔMDD +0.2 pp (2×: −3.4); tail 0.79; ΔSR −0.028 (2×: −0.125); p_ni 0.146; plateau 0.375 (DLA-U1). ΔMDD bootstrap SD 7.8 pp; ΔES99 daily z 2.37; ΔES95 of 21-day returns z 1.85 (DLA-U5). PC-1′ legs: ES21 +1.65 pp, ES126 +3.8 pp (PX1). SE 0.061, MDE80 0.13 (DLB-T5a). A 0.10 band gives +1.8 pp, still REJECT; monthly rebalancing is INSUFFICIENT (GFC share 0.56–0.67) (DLA-U3, U4) | Recorded: **REJECT (instrument: US shares via KIS, 50 bp, daily)**. Under v2 it would read INSUFFICIENT DATA (inconclusive: p_ni 0.15). That is a disclosed flip; the card is not re-run | Never built. The label is a fact about executing a beta scalar in single US shares at retail cost, not evidence against vol targeting. Its variants are ledger trials, never rescues (DNB #23) |
| **R-29** MACRO-R06-US-FUT | CARD-P / A pending | CME Micro ES, 5 bp, daily; declared notional ≥ ≈ ₩1bn | **1990–2026 on v1.2 checks** (DLA-U2): ΔMDD +3.6 pp (2×: +3.2); p_ni 0.002; 6 of 11 windows (max 0.46); plateau 0.875 → PASS. **On a knife edge:** 11 PASS / 9 REVISE / 24 REJECT over 44 quarterly starts; every start from 1994-11 to 2000-08 is a REJECT; 1995+ is a REJECT (+2.9 pp); 1990–2007 shows +0.3 pp. **ES at 5 bp:** ΔES99 z 2.38; ΔES95 of 21-day returns z 2.05 (DLA-U5). **Estimator dependence:** on 1995–2026 the verdict flips with the estimator: SMA20 +2.5 pp REJECT; GARCH +4.9, log-HAR +4.8 and COMB +3.9 pp PASS (DLB-T1h). The settling run on French daily data 1926-07 → 2026-08 has not run (HTTP 403; DLA-U6) | Knife-edge **PASS** on 1990–2026 (v1.2 checks). The settling run decides the v2 verdict | **FORWARD-SIM** in the specification book. BUILD-AS-INSURANCE only when all three hold: (1) a US sleeve exists in which one Micro ES is ≤ 5% of notional, or another line is declared under D5; (2) the settling run passes PC-1′ at 1× and 2× and at ≥ 8 of the 10 decade-spaced starts, with no REJECT at any of them; (3) the card's full-span v2 verdict under the blind package, on ≥ 15% S&P episodes, is PASS |
| **R-08** VIX ≥ VIX3M entry block | CARD-P / A (64 / 40 / 24 onsets at 20 / 60 / 126 sessions) | Per book | ΔMDD vs S +0.0 to +0.9 pp (US VT15 at 50 bp +0.9; KOSPI VT20 at 3 bp +0.3; US momentum +0.0); tail ratio 0.996–0.999. 132 spells, 50.8% of them one day long; 14.0 transitions a year (DLB-T6a, T6b). A median 79% of the drawdown happened before the flag came on (QF6) | **REJECT**: PC-1 and PC-2 in 10 of 10 cells. Under v2, PC-2 alone REJECTs | Demoted to a CONVENTION: an execution-state annotation with a stated clearing rule. No book's exposure changes (R-08) |
| **R-11** USD/KRW leg (S1) on VT20 | CARD-P / A on 1997–2026 | KRX ETF line, 3 bp (strict); KRX stocks, 35 bp (value timing) | Onsets: 54 strict-H.10, 74 at value timing, 69 on KRW=X lagged two sessions (2004+). ΔMDD −1.3 pp (strict), −1.7 pp (value), +0.3 pp (KRW=X); tail 1.004 (DLA-L1). The ECOS 15:30 check moves the 1997 firing by one session (first firing 28-Oct-1997), with 56–58% of the fall already done (EX2). Timing FR 0.49 (QF2) | **REJECT** at every timing (PC-1, PC-2). Under v2, PC-2 alone REJECTs | **RETIRED**: a labelled, display-only refusal book. BL-S01 is closed; BL-G04 and BL-D13 drop to P3 |
| **R-12** US rates-stress leg (S2) on VT15 | CARD-P / A (71 onsets) | US shares via KIS, 50 bp; strict +2 business days | Strict +2 bd: ΔMDD −3.5 pp at 50 bp, +0.8 at 5 bp, +0.9 gross. Treasury +1 bd (compliant): −3.1 / +0.1 / +0.3 pp, with 2 of 11 windows positive. Tail 0.99–0.995 (DLA-L2). ΔSR at 50 bp: −0.120 ± 0.022 (strict) and −0.105 (Treasury); the add-on SE is 0.022 and MDE80 0.046, so this is a powered rejection (QF3). Timing FR 0.75 in QF2 (0.74 from its printed L-grid), i.e. timing-fragile | **REJECT** at every timing and cost (PC-1, PC-2, the PC-3 point). Under v2, PC-2 and the PC-3 point REJECT; the timing cap only lowers, so it does not change this | **RETIRED**: a refusal book. BL-S02 is closed. G-US-02a is compliant via the Treasury channel, with posting times logged |
| **R-28** trend axis (US is the first instance) | CARD-P / A via the pooled-onset rule (the US alone has 45 de-clustered onsets) | US instance: incremental on R-29's futures vt book (CME Micro ES, 5 bp; D5); lab lines at 5 and 50 bp | **French monthly 1927–2026 at 5 bp** (DLB-T3a): ΔSR +0.083 [0.019, 0.134]; p_ni below 1/B; ΔMDD +15.9 pp (2×: +15.9); tail 0.78; 9 of 10 episodes (max 0.21); years 68%; plateau 1.0. At 50 bp, ΔSR +0.059. **Stacked on the daily US VT15 book (1991–2026):** +14.9 pp; GJR-null percentile 87th; White RC p 0.20, SPA 0.23 (PX2). **Snooping haircut:** 94 of 94 variants keep ΔMDD ≥ 3 pp (median +16.4), but the Sharpe gain's deflated probability is only 0.59 at N̂ 30.7 and 0.43 at N 94 (DLB-T3f). **Robustness:** starts from 1970 are INSUFFICIENT on onsets, with ΔMDD still +12 to +16 pp (DLB-T3c); ΔMDD > 0 in 7 of 7 indices (DLB-T3e) | **PASS** (indicative, v1.2 checks) on the protective claim; no Sharpe claim. The v2 verdict is computed blind at the formal run | **FORWARD-SIM** until a US or other non-Korean sleeve exists (D5), then BUILD-AS-INSURANCE on a formal v2 PASS. **Korea is CONTEXT-ONLY** and refused as a card: daily tail 0.929 (0.853 at 21 days); +2.2 pp on VT20; −2.3 pp on 2016–26 |
| **R-31** drawdown step-down card | CARD-P / declared on the card | The declared book: KOSPI VT20 at 3 bp; US VT15 at 5 bp | **EX1's ladder table.** With re-arm alone (L2) the steps bind on 53% / 29% of days, 62–66% of them outside bear markets. Time-boxed at 21 sessions (L5): binding 19% / 10%; ΔSR +0.005 / +0.006; ΔMDD +4.8 / +1.5 pp; 3 / 0 HALTs. **Kaminski–Lo:** after an activation, the next 21 sessions returned −0.57% vs +0.98% unconditional on KOSPI, and +0.57% vs +0.78% in the US (QF4 §5.3) | NOT_RUN | **SPECIFICATION BOOK** while the binding share is > 10% (KOSPI ≈ 19%). At ≤ 10% the steps act inside the R-07 invariant. The US (≈ 10%) sits at the threshold; that is moot while no US sleeve exists |
| **R-14** TS-trend sleeve | CARD-O / A | Instrument book declared on the card | At cap 1: SR 0.449; correlation with the S&P 0.027 over 2001–26, but 0.34–0.36 over 2013–26 (QF5-A11). The related card E1 (trend switch) is a REJECT | NOT_RUN. Claim: diversification ("not fast-crash protection") | BUILD NOW (family configuration). Header committed blind (§8.1.3 step 4). The factor acts only on a formal PASS |
| **Stack card** (R-02) | CARD-P / generated | The recommended book of a market | EX1, KOSPI at 3 bp. Days at ≤ 0.25× exposure: 0.8% for VT20 alone, 31.0% for the product stack VT20 × SMA10m × ladder, 11.2% under `min()`. 2020 rebound: +23.9% / +7.6% / +12.6%, against buy-and-hold +47.3%. The US product stack: 17.9% of days, and +4.5% of a +46.9% rebound | NOT_RUN (no stack acts yet) | Generated before a second de-risk factor joins a recommended book (§8.7). Product composition is refused |
| **R-17** crypto vol target | CARD-P / — | The declared crypto venue (24/7 clock: 00:00Z bar close; 365-day annualisation) | None | NOT_RUN | **DEFERRED** until a crypto sleeve exists. It is then registered as a new card with its declared instrument (R-17) |
| **R-07** hard stop (evidence for D2) | INVARIANT; not a card | Whole-book NAV | **The literal v1.2 ladder never leaves HALTED:** KOSPI from 1997-10 (714 cycles, 1.3% average exposure); US 907 or 653 cycles (DLA-D1). **Hard stop with the re-arm only** (Executives' check C2): KOSPI VT20 1997–2026 at −15%: 24 HALTs, Sharpe 0.457 vs 0.46 without a ladder, MDD −56.4% vs −45.3%; at −30% (= −1.5 σ_book): 6 HALTs, Sharpe 0.471, MDD −44.8%. US VT15 1990–2026 at −15%: 13 HALTs, Sharpe 0.584 vs 0.592, MDD −46.3% vs −50.3%; at −22.5%: 4 HALTs, Sharpe 0.589, MDD −53.0% | No verdict. It is a governance review event and makes no protection claim | BUILD NOW in every recommended and specification book; card and FORWARD-SIM books exclude it (R-22 rule 6). The level is owner decision D2 (default −15%). I-04b is the re-entry regression test |

**Which cards would read INSUFFICIENT DATA under v2.**
- **The R-06 KR 2016–26 line:** sufficiency, and inconclusive on PC-1′. It is printed on the long-history card and decides nothing.
- **The R-06 KR stock book:** inconclusive. It stays on record and never acts.
- **R-06 US at 50 bp, if it were re-run:** inconclusive. It is not re-run, and its recorded label stays the instrument REJECT.
- **Any single-market R-28 instance:** each index alone has 15–21 de-clustered onsets, and US starts from 1970 also fall short. The route to Tier A is the pooled-onset rule declared before the run; an own-market PC-1′ or PC-2 failure vetoes a pooled pass.
- **R-06 KR itself: expected on current evidence**, through the selection factor (every row-set reading with the DL-A seed gives f above 1.28 at the indicative p_ni 0.078; R2-C1). Any other condition that misses without a REJECT (a 126-session leg with p × f > 0.10, a band start that REJECTs) has the same effect. It then stays a labelled control in the specification book until new history adds an objective episode; no convention may be changed to rescue it.
- **Every BACKLOG candidate without local data.** The v1.2 list was BL-U01–U03, BL-C02, BL-C03, BL-C05–C07, BL-C11, BL-C13 and BL-O02–O04.
- **No longer on the list:**
  - R-04: it meets sufficiency on 34 pooled onsets, but fails step 3 and the BL-C12 holdout;
  - the Korea long-history card's v1.2-check result: an indicative PASS, which no longer decides it (its v2 expectation is above);
  - R-11: it is a REJECT on 1997–2026, with 54 strict onsets.

QUANTGEN's last study run recorded **0** INSUFFICIENT DATA cards, and the macro cards will add several. That is the honest label: the gate defines this verdict for exactly this case.

**What this means for the displayed recommendation today.**
- **Before the package is frozen and the formal cards run, every macro card is NOT_RUN.** The recommended book therefore carries only the invariants:
  - point-in-time data and data contracts (R-01, R-19, R-20);
  - bounds and `min()` composition (R-02);
  - Korea concentration caps on look-through (R-07; template D1);
  - the −15% hard stop with its re-arm (R-07; D2);
  - the hedge state (R-09);
  - instrument and cost realism (R-26).

  The ladder steps act in the recommended book only where they bind on ≤ 10% of days, which excludes KOSPI VT20 (≈ 19%).
- **The specification book shows the full set**, each factor labelled with its card status:
  - vt (R-06 KR): NOT_RUN; indicative PASS on v1.2 checks, fragile; expected INSUFFICIENT DATA under v2 (through f; R2-C1);
  - vs (R-03): NOT_RUN; indicative PASS, step 3 borderline;
  - the D&M gate (R-04): step 3 FAIL;
  - the step-down (R-31): NOT_RUN.
- **If the formal runs confirm the indicative verdicts:**
  - R-03 becomes the first macro factor in the recommended book, with its "step 3 borderline" flag;
  - R-06 KR stays a labelled control in the specification book (expected INSUFFICIENT DATA through f; R2-C1); it would enter as BUILD-AS-INSURANCE, with its crisis-clustering label and its premium beside it, only on a formal PASS;
  - if two such factors would act on the same market book, the stack card runs before the second one joins (§8.7).
- **Everything else:**
  - R-28 and R-29 keep running as FORWARD-SIM books;
  - R-11 and R-12 keep running as labelled refusal books, as card E1 does;
  - the US vol target on US shares at 50 bp stays an instrument-specific REJECT;
  - R-08 is an annotation.

### 8.10 Owner decisions and settling tests

**Owner decisions** (Resolutions §d). The Quick start table is the canonical statement of D1–D6 and their defaults (C-8); this section gives the evidence and the procedure and does not restate the values.
- **Storage.** The registry `owner_decisions.D<n> = {key, value, default, options, status, effective_from, rationale, refs}` (§7). Each decision has one canonical scalar key; rule blocks reference it and never copy it (T-OWNER-01). Every card prints the values in force.
- **No new package version.** None of the decisions belongs to the gate package, so a ruling never creates a new package version.
- **Book changes.** A ruling that changes a book (D1, D2) is logged as a governance event, and the affected cards' printed lines are re-run (binding share, HALT count). It is not an edit of any card's acting parameter, so it never demotes a card. R-31's header depends on D2, so a D2 ruling gives R-31 a counted revision before its next run, which also recomputes its binding share (R-31). Card books exclude the hard stop and caps (R-22 rule 6), so D1 and D2 act on the recommended book only; G-LAD-04 (§9.4) prints that book with and without the hard stop beside D2.

| # | Decision | Kind | Council default | Evidence | Where it binds |
|---|---|---|---|---|---|
| D1 | Korea concentration template | Risk appetite | Quick start table (council option (b), MSCI 25/50; alternatives (a) the domestic fund rule, (c) a 35% pair cap) | n = 1, so it cannot choose: July 2026 −36.3% (25/50), −33.9% (35% pair), −38.6% (KOSPI); H1-2026 +95.2%, +86.6%, +101.1%. On 2 Oct the absolute bound 22.5 ⁄ 29.8 = 0.755 does not bind at vt 0.694; the active single-name bound (at most 0.685) does, in both books (§3.3, §11). Also open: whether to allow the 35 bp ex-pair basket route, which opens only after a stock-book card passes and limit-lock flags exist | R-07 caps (the template is read from the rules store) |
| D2 | Hard-stop level | Risk appetite | Quick start table (council option (a); alternative (b): −1.5 σ_book, i.e. −30% for KOSPI VT20 and −22.5% for US VT15) | Check C2 (§8.9): at −15%, KOSPI VT20 fires 24 times and deepens MDD from −45.3% to −56.4%; at −30% it fires 6 times, with MDD −44.8%. On a single-market Korea book, (a) fires about four times as often as (b) | R-07; R-31 (`hard_stop_level`) |
| D3 | QF5-M10: calm-state reversal down-weight | Principle change (P3) | Quick start table (council option (a): keep P3) | The evidence is US, gross and from one regime (VIX ≤ 20: −1.15%/yr), with no Korean net-of-cost test. (b) Reopen only after a KRX stock-reversal test, net of 35 bp + 0.20% tax, shows 0.5× in calm beating 1.0× at one-sided p ≤ 0.10 in both 2010–17 and 2018–26 | R-15; BL-O08 stays at P3 |
| D4 | Book-level false-demotion budget | Risk appetite | Quick start table (council default; the owner may only tighten it) | 12 forward months detect only catastrophic decay (calibrated 2.5% thresholds: −0.20 / −0.39 / −0.73 Sharpe). A CUSUM needs about 40 months to detect flat performance | R-25 (`false_demotion_budget_per_year`) |
| D5 | Whether to run a US sleeve, and on which line | Product choice | Quick start table (no US sleeve until the owner decides; R-28 and R-29 stay FORWARD-SIM) | (a) **Index futures:** Micro ES ≈ ₩52m, so the notional must be about ₩1bn or more (tracking error 7.5% a year at ₩0.1bn vs 0.7% at ₩1bn). (b) **A KRX-listed S&P ETF line:** only with FX and NAV lag modelled; DLA's "KRX ETF 3 bp" US book models neither. (c) **No US sleeve** | R-26 (`us_line_choice`), R-28, R-29. The same notional decides whether the Korea card may use the futures line (X-EX2-N3) |
| D6 | CDaR-guard calibration | Gate sub-point (Resolution 4) | Quick start table (default rule frozen with the package; an owner ruling only before the first acceptance attempt; applied only if triggered) | Needed only if a negative control passes the acceptance test; on existing numbers none does (QF chair §0.3). The candidates are judged on placebo results only | R-21 9(d); `gate.acceptance_test.cdar_guard.calibration` |

**Open owner and council questions** (adversarial rounds 1 and 2; `council/ASPEC_R1_synthesis.md`, `council/ASPEC_R2_synthesis.md`). The spec states its conservative reading for each until an answer is recorded. A question that touches a frozen package item (Q5; the timing fragility of a Sharpe-neutral card; the primary out-of-sample line of future cards) is answered, or recorded as "stands as written for 2.0.0", before the first acceptance attempt, and the record is listed in the `definitions_md5` manifest. An answer recorded later enters only a later package version, adopted with a rationale that cites no card result, with every flip disclosed (§8.1.3 step 6). Until the timing question is answered, every card prints FR with a paired-bootstrap 90% interval beside it (never gating).
- **Q5 (council): per-card placebo excess.** A per-card panel above 2 of 20 currently fails the acceptance test, so nothing is frozen (R-21 9(a)). The alternative, a card-local cap at INSUFFICIENT DATA, would change Resolution 4's acceptance test and needs the council.
- **Timing fragility of a Sharpe-neutral card (council).** FR = LF ⁄ ΔSR(L1) is ill-posed when ΔSR(L1) ≈ 0 (R-06 KR: 0.004). The council's formula stands in package 2.0.0; a fallback statistic (the gating tail leg) can only be adopted blind, before the first acceptance attempt or as a new package version (above).
- **The primary out-of-sample line of future cards (council).** R-06 KR's is fixed by Resolution 1; for other long-sample cards the header still declares it (R-22 rule 5).
- **Flow and quality priors (owner or council, before M4).** Until registered, a family with no prior in a market is not admissible there (R-15).
- **D1 and D2 timing (owner).** Whether a ruling needs a notice period, and whether it may take effect while a book is HALTED or near its hard-stop level.
- **R-18 policy break mid-spell (council).** Whether a framework event lifts an active de-risk spell at once (current text) or lets it run out.
- **Demotion verdict by trigger (council).** The R-25 default (operational → REVISE; catastrophic or CUSUM → REJECT) is judgment.
- **Owner inputs, not decisions:** each sleeve's `notional_nav`; the KRX notice facts (the pre-2016 CSAT window and its closing call, Saturday close times, pre-2015 random-end extensions, the ETF tick table before 2023-12-11); the SSE, HKEX and TWSE close times (signed with the calendars at M1); the ECOS code of `BOK_CALL_RATE` and its observation calendar; the choice of `USD_LIVE_PROXY`; the KIS credentials. M1 measures the KODEX 200 basket's publication time, confirms the NYSE 30 s print bound and logs FRED's VIX posting time for 20 sessions.

**Settling tests the council has named** (Resolutions §d). Each test decides only what its row says. A verdict changes only through the routes of §8.8 and §8.1.3: new history, a new card or a new package version.

| Open question | Settling test | What it can change |
|---|---|---|
| Is the gate package sound? | The gate-acceptance test, before any card: ≤ 10% of 300 circular-shift placebos per family and ≤ 2 of 20 per card pass PC-1′; the five negative controls come out REJECT or INSUFFICIENT | Freezes package 2.0.0, or blocks every card run |
| How is the CDaR guard calibrated? | Default rule frozen with the package before any control runs (D6; placebo results only); applied inside the test only if a control passes | Adds a null-calibrated guard before any card runs |
| Horizon-matched PC-2 | EX1's placebo test: daily vs horizon PC-2 on every pre-registered CARD-P, plus 20 placebos each. Adopt if false-pass ≤ 10% | PC-2 for every CARD-P (KOSPI trend stays context) |
| Korea VT20 promotion | The formal v2 run of Resolution 1 on KRX official closes | R-06 KR: BUILD-AS-INSURANCE, labelled control or archive (expected on current evidence: a labelled control, INSUFFICIENT DATA through f; §8.9) |
| US futures vol target | French daily Mkt-RF 1926-07 → 2026-08 at 5 bp: PC-1′ at 1× and 2×; ≥ 8 of 10 decade-spaced starts with no REJECT; a full-span v2 PASS | R-29's promotion, together with D5 |
| Step-3 rule for v3 | Size and power of N_equiv deflation vs linear-N̂ deflation vs PX1's z rule, under QF3 §4.4's DGP. Keep size ≤ 10% with the most power at Δ 0.10–0.30 | A v3 package (a new version re-runs every card) |
| How to read BLdP eq. 9 | Read eq. 9 and Exhibit 4 on the printed paper | The printed bound and its "step 3 borderline" flag; not the gate |
| Jump-model regime engine (CONTESTED) | A pre-registered 2027–28 head-to-head, SJM50 vs BAND200 vs VT15 at 50 bp, on the US, STOXX50E and TWII. Ties go to the band; the λ ledger holds ≥ 5 values | Whether an SJM card may be proposed (it would then be judged on history). Never a displayed regime. Korea excluded |
| GMM scenario regimes (CONTESTED) | After the replay library exists: beat the replays on 99% ES coverage over 2008–26, with ≥ 90% label agreement across refits | Context only; never labelled as a current regime |
| Korean cross-asset futures sleeve (CONTESTED) | KIS KOSPI200, KTB 3y/10y and USD futures 2006–26 at 5 bp: correlation with KOSPI < 0.3, ΔMDD ≥ 3 pp, positive in ≥ 3 of 5 KOSPI bears | Whether a card is registered |
| R-18 statistical break leg | 1990–2026: ≤ 1 false break a decade; flags within 6 months of the 2012 and 2020 framework changes | Whether the statistical leg may become a trigger (it is log-only in v2) |
| Calm-state reversal (D3) | The KRX net test in 2010–17 and 2018–26 | Reopens D3 |
| KIS quote fields | 069500 and 005930 bid / ask at 15:19:59 KST on 20 sessions | Calibrates the stress-cost line (R-26) |
| The app's B5 study | Publish `docs/vol_backtest.py` and its seed; rerun B5 on SPY and KODEX 200 for 2016–26 | The app's GJR / GARCH-t B5 claim, which stays UNVERIFIED until then (R-30) |
| Holiday-gap VaR display | Pre-registered 2027–28 out-of-sample breach rates | The √n display scaling (R-10) |
| Korea reversal prior | BL-U02, net of 35 bp plus tax | The R-15 prior (1, UNVERIFIED, until then) |
| S1 on ECOS 15:30 history | An ECOS rerun (a P3 formality) | Nothing: it cannot change the REJECT |

## 9. Test plan v2 (`tests/run_all.py`, hermetic)

**Hermetic rule (existing).** `tests/run_all.py` runs the engine, quant and FICC acceptance suites with every network touchpoint patched to raise. Macro tests follow the same rule:
- They read **frozen post-close fixtures** only (**proposed**: `tests/fixtures/macro/`). The fixtures are extracts of the §9.3 reference data as of 2026-10-02, re-frozen after the 17:20 KST data patch, with an md5 per file, listed in the fixture manifest (§9.5). Golden-value fixtures are generated once, at M1's exit, by QUANTGEN's own data layer from the frozen reference files (values unchanged; provenance fields and `value_status` added) and md5-frozen; every later milestone reads that generation, and a regeneration before the M7 freeze must reproduce the same md5s or is a fixture change logged in the manifest with the tests it re-baselines; the reference datasets, scripts and results behind them live in `/home/claude/quantgen_macro_data/` (Quick start). A fixture any of whose close-type rows was retrieved before its session's close-print bound + 10 minutes is refused (T-FIX-01).
- No macro test may reach FRED, Yahoo, KIS, FMP, ECOS, Treasury or any other provider (T-HERM-01).
- The gate-acceptance test (I-08) runs once, before any formal card run. Its results are md5-frozen with the gate package version; later `run_all.py` runs only re-verify the md5s.
- **No production state.** Tests write only to temporary copies of the rules store, the family ledgers and the artifact directory (T-HERM-02).
- **Test tiers.** `fast` (unit tests; ≤ 10 minutes in total), `golden` (fixture reproductions; ≤ 2 hours) and `freeze` (I-08, the formal runs of I-07 and I-16, the GJR-null paths, PBO). The freeze tier runs only in the M7 freeze job and at formal card runs; `tests/run_all.py` verifies its md5s and never recomputes it. Budgets: default, judgment. Every row names its tier in the test registry.
- **`runs_from`.** Every test carries the first milestone at which it can run (§9.0a).
- **Reference mode and v1.2-check mode** are reachable only from `tests/reference/` and `docs/` (§9.3.3).
- **Verdicts near a threshold.** A verdict derived from a statistic within tolerance of its threshold is asserted as a class (e.g. "REJECT or INSUFFICIENT DATA"), never as a point.

### 9.0 Module acceptance tests (every module of `QC_modules.csv`)

Each module's pass condition is copied verbatim from the council file. The test IDs point to the rows of §9.1 and §9.2 and, for R-19 to R-31 and R-34, to the acceptance-test table inside each rule (§5). For R-03, "20 binding years" means the 20 years in which the scaled and unscaled books differ; in the other 17, vs = 1.0 all year.

**Adversarial round 1.** The council's wording below is not edited. Where round 1 refined a test under the same ID, the refined row in §9.1, §9.2 or the rule's table governs for every such ID, listed here or not, and a row below is never an independent pass condition. Beyond the list: T-STALE-01 (each hit's `d_next`, not the decision date, is in the source-skipped list), T-CAPS-01 (the active bound 0.685 binds in both books), I-01 (`verdict_filter` admits a PASS verdict or `INVARIANT_STEP`), I-12 and T-TREND-02 (+14.9 pp is the daily US VT15 book's) and T-CRYPTO-01 (00:00:00Z on d+1). The list: T-PROV-01 and T-FIX-01 (exact clocks and fields), T-CAP-02 (a property test on composed(m)), T-CLOSE-02 (effective-dated bounds), T-BAND-01 (32 starts; an integer floor), T-GATE-01/03 (the pass definition; class assertions), T-PLACEBO-01 (the `timing_probe` sandbox; R-11's FR printed), T-POWER-01, T-STEP-03, T-SCHEMA-02 (the §6.5 names), I-04b (the automatic RISK re-arm), I-06b (√max(n_US, 1)), I-08, I-13, I-15 and I-16; every HALT is per book (C-1). §9.0a gives each test's `runs_from`.

| Module | Milestone | Test IDs | Pass condition (`QC_modules.csv`, verbatim) |
|---|---|---|---|
| R-01 | M1 | T-PROV-01, T-FIX-01, T-BAR-01, G-POST-01 | T-PROV-01: on the 2-Oct fixture the store returns MissingInput(provisional_intraday) at 10:31 KST and 7,003.74 [value_status=official_close] at 16:00 KST; T-FIX-01: a fixture whose last row has retrieved_at_utc < official_close_utc + 10 min is refused; DLA §7's corrected values regenerate at Level-1 tolerance (−23.2% from peak, 1.107× 200-day, rv20 28.8%, vt 0.694); a bar-derived or flat zero-volume close is never stored as a close. |
| R-02 | M2 | T-CAP-02 | T-CAP-02: for any overlay vector in [0.5, 1]^k and ladder step in {1.0, 0.5}, final = vt × min(overlays, ladder) and final/vt ≥ 0.5 on every non-HALTED day; a product-composed path raises; the card prints the share of days at ≤ 0.25× total exposure and rebound capture (EX1 on KOSPI: 31.0% under product composition vs 11.2% under min()); once ≥ 2 de-risk factors act in the recommended book a stack CARD-P is generated and gated. |
| R-03 | M4 | T-R03-01 | On the French Mom fixture (50 bp, both legs) the card prints ΔSR +0.273 ± 0.01, deflated ΔSR 0.98 ± 0.01 at N_equiv 6.3 (PASS) and 0.947 ± 0.01 at linear N̂ 12.6 flagged 'step 3 borderline'; the scale-free (expanding-median σ126) and variance-scaled revisions each carry a committed header md5 before their runs and increment the R-03 family ledger; the years line prints 20 binding years with 15 higher gross / 11 net. |
| R-04 | M4 | T-R04-01, I-03 | The card computes step 3 on the R-03 family ledger and reports deflated add-on 0.77 ± 0.02 at N_equiv 6.3 → 'step 3 FAIL'; the recommended-book builder refuses R-04 (I-03 assertion); card validation rejects any A-provisional or pooled route for a card already run. |
| R-06 | M7 | I-16, T-R06-US-01, T-CAP-01 | Korea formal card on KRX official closes from the first close + 20-session warm-up, ETF 3 bp, SMA20/0.20/cap 1, excess returns: verdict PASS only if (i) v2 CARD-P PASS on the full span, (ii) PASS on the ETF-era line to 2025-12, (iii) no REJECT at any monthly start 1997-05…1999-12 and PASS in ≥ 2/3 of them, (iv) no REJECT in either midpoint half; card prints the insurance label, timing return and per-regime table. US 50 bp card shows 'REJECT (instrument: US shares via KIS, 50 bp, daily)' and is never re-run. Any vt > 1.0 fails validation. |
| R-07 | M5 | I-04b, T-CAPS-01 | I-04b: a −15% book-NAV breach (default level; owner decision D2) sets HALTED, refuses re-arm for 10 sessions, resets the hard-stop reference to NAV at re-arm and runs 0.5× for 10 sessions; on the KOSPI 1997–2026 fixture the book re-enters after every HALT (literal v1.2 rule: permanently HALTED from 1997-10, 714 cycles). Caps: daily KODEX 200 basket applied; w_i − g·b̃_i ≤ 0.05 NAV enforced; template read from the rules store; on 2 Oct under 25/50 the gross bound is 22.5/29.8 = 0.755 and does not bind at vt 0.694. |
| R-08 | M5 | T-ANNOT-01 | With the flag on, no book's weights change (assertion in the book builder); each flag day writes an annotation and a KIS spread-snapshot request; the fixture reproduces 132 spells with 50.8% lasting one day (DLB-T6a). |
| R-09 | M2 | T-CORR-01, T-HEDGE-01 | T-CORR-01: corr63 computed on date-aligned (r_eq(D), −Δy(D)) pairs reproduces +0.53 at 2026-09-30; a risk-model input that misses two expected releases sets hedge_credit_off = TRUE, raises an operator alert and never moves the runtime to HALTED; fx_hedge_credit (no credit while trailing KOSPI–KRW correlation ≥ 0) changes no exposure. |
| R-10 | M5 | I-06b | I-06b: a KRX session after a multi-day US closure carries gap_sessions ≥ 2 and its displayed 1-day VaR is scaled by √n_US; BoK decision and press conference are separate events with status; no event tag changes any weight (assertion). |
| R-11 | M8 | T-REF-01, I-03 | S1 is absent from the FORWARD-SIM re-gate queue (BL-S01 closed; BL-G04/BL-D13 at P3); its card records REJECT (54 strict-H.10 onsets, ΔMDD −1.3 pp, tail 1.00); I-03 asserts no recommended or specification book reads its multiplier. |
| R-12 | M8 | T-REF-02 | S2 is absent from the FORWARD-SIM queue (BL-S02 closed); its card records REJECT with 71 onsets, including the compliant Treasury +1 business-day timing (ΔMDD −3.1 pp at 50 bp) and strict +2 days (−3.5 pp); G-US-02a reads 'compliant via Treasury with logged posting time'. |
| R-13 | M6 | T-CTX-02 (and T-CTX-01) | Every context_log item carries vintage and retrieved_at_utc; revised series store first print + current value + vintage date; LETF AUM, KOFIA margin debt, VRP, VIX/VIX3M (16:00 ET) and KOSPI200 MFIV (15:30 KST) snapshots stamped 'live'; T-CTX-01 still passes (no acting module reads any of them). |
| R-14 | M7 | T-R14-01 | The R-14 card header declares instrument book and claim (CARD-O, diversification) and is refused without them; golden values restated at cap 1 with sub-period correlations; failure-mode text reads 'not fast-crash protection'. |
| R-15 | M4 | T-PRIOR-01 | base_weight(m,f) = IV_m × 1/K_m over families with prior ≥ 1 and card not REJECT; family weights sum to 1 per market and Σ IV_m = 1 (assertions); the Korea reversal prior is stored as 1 (UNVERIFIED); a tilt without a PASSed family card is refused by rules-store validation. |
| R-16 | M9 | I-11 | GARCH/GJR parameters fitted on expanding (≥ 10-year) windows; the lab shows max(fast FHS, GJR-EVT) with Kupiec, Christoffersen and ES Z2 lines, 2016–26 and 2026 reported separately; the replay library reproduces the Jul-2026 KOSPI path (−38.6% in 27 sessions) on the current book with regime metadata; no lab output is read by a sizing module. |
| R-17 | M10 | T-CRYPTO-01, T-FX-01 | decision_time_utc('CRYPTO', d) = 00:00:00Z venue bar close; annualisation 365; weekday macro data joined as-of with staleness labels; an FX sleeve card without a declared instrument (KRX USD futures or broker spot) is refused. |
| R-18 | M6 | T-BREAK-01 | An official framework-change event shrinks every macro-conditioned multiplier to 1.0 and starts a forward record; the statistical-break flag and the BOCPD probability (hazard 1/250) are logged with no reader in any acting module or display; scale-break re-anchoring occurs only on declared events; the statistical leg activates only after EX1's test (≤ 1 false break a decade on 1990–2026; flags within 6 months of 2012 and 2020). |
| R-19 | M1 | T-STALE-01, T-ROLE-01, T-XMKT-01, T-HEDGE-01 | T-STALE-01: over decisions 2016-01-04 → 2026-09-25, DTWEXBGS and DEXKOUS are flagged stale on ≤ 1% of decisions (0.42–0.89% expected; DGS10's 0.33% is G-STALE-01's) and every hit falls on a whitelisted source-skipped date (the v1.2 rule gives 100%); T-ROLE-01: stale acting input → fail closed + alert, HALTED only after the declared N; stale risk_model input → hedge_credit_off, never HALTED; stale context input → label only. |
| R-20 | M1 | T-CLOSE-02, T-SAT-01, T-REGIME-01, T-AVAIL-01, T-CAL-01 | T-CLOSE-02: a KRX session before 2016-08-01 maps to a 06:00Z close, from 2016-08-01 to 06:30Z with available_at bounded at 06:30:30Z (random end unconditional from 2015-06-15); CSAT-day close 07:30Z; Saturday sessions before 1998-12-12 are present; regime tags (±8/12/15/30% limits, 1997 FX peg, short-sale bans, sell-tax 0.30 → 0.15 → 0.20%) are returned for any date; T-AVAIL-01 availability fixtures are built from official calendars. |
| R-21 | M7 (frozen before the first card run) | I-08, T-GATE-01..04, T-DNH-01, T-ORDER-01, T-ES-01/02 | Gate-acceptance test run once, results md5-frozen: ≤ 10% false-pass over 300 circular-shift placebos per family and ≤ 2 of 20 per card; negative controls (US VT 5-day and 10-day at 50 bp; post-shock-day and post-shock-week 0.5×; stale VT with σ lag 252) all return REJECT or INSUFFICIENT; on the US VT15 50 bp fixture the v2 verdict is INSUFFICIENT (ES21 +1.65 pp, ES126 +3.8 pp, p_ni 0.15), and the 5-day VT is REJECTed by the PC-3 point (ΔSR −0.29). |
| R-22 | M7 (frozen before the first card run) | I-09, T-EPIS-01/02, T-EXCESS-01, T-TROUGH-01, T-BAND-01 | The episode builder returns 18 alternating ≥ 20% KOSPI episodes on 1997–2026 (12 with troughs before 2008) and 4 on 2016–26, 16 S&P episodes at 15% on 1990–2026, and no Sep-2026 episode; the Korea definitive cell's PC-4 maximum share is 0.174 ± 0.01 (0.493 under §8.6, printed); card statistics use excess returns with call-rate / RF cash (Korea p_ni 0.078 ± 0.01); every card prints a trough → +63-session window, not gated. |
| R-23 | M7 (frozen before the first card run) | T-DSR-01/02, T-NEFF-01, T-STEP3-01/02 | T-DSR-01 reproduces BLdP's example (0.9505 at N 46; 0.9004 at N 100); T-NEFF-01: on QF3's 26-trial difference-series correlation matrix (seed 11) E[max Z] = 1.33 ± 0.01 and N_equiv = 6.3 ± 0.4; padding with 80 near-duplicates moves N_equiv by < 0.5 (6.33 → 6.59); R-03 → 0.98 ± 0.01 PASS, R-04 → 0.77 ± 0.02 FAIL; a card without a ledger hash is refused; no code path computes the Kish N̂. |
| R-24 | M7 | T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01 | Every card prints SE (HAC and block-250), MDE80 and power; the fixture reproduces SE(ΔSR) 0.061 ± 0.005 (US VT15) and 0.130 ± 0.01 (KOSPI VT20, 2016–26); the UNDERPOWERED code can convert only a failed step-5 or PC-3 p-value (a PC-3 point REJECT, PC-1′ or PC-2 failure is never waived); no p-value is printed as 0 (prints < 1/B); PBO uses ledger ∪ neighbour grid and the card's own objective. |
| R-25 | M8 | I-14, T-DEMOTE-01..05 | CARD-P demotion reads 'forward ΔMDD vs S ≤ 0 = no protection'; all statistical triggers use whole-book NAV; on a 20-shift placebo panel the book-level false-demotion rate is ≤ the declared budget (default 10%/yr, owner decision D4); an injected lag-audit violation or an acting-parameter edit outside a revision demotes immediately; no forward record can raise a card's verdict. |
| R-26 | M0 | T-COST-02/03, T-BOOK-01..03 | T-COST-02: 252670 at ₩69 is charged ≥ 72 bp per side; T-COST-03: lowering a cost in a header raises; T-BOOK-01: a card without instrument_book, rebalance, no_trade_band and notional_nav is refused, a futures line whose one contract exceeds 5% of declared notional is refused (mini KOSPI200 ≈ ₩56m on a ₩0.1bn sleeve), and a stock book used as a market-gross scalar is refused; every card prints execution variants A/B/C and overnight/intraday attribution. |
| R-27 | M5 | T-FILL-01..03, T-BAR-01 | A ≈15:19 KST decision snapshot filled at the official close reproduces QF1's tracking error vs an official-close decision (0.19%/yr on KOSPI, mean \|Δw\| 0.0013) within ±0.05 pp; a limit-locked name (SK hynix, 31-Jul-2026, +29.95%) is non-fillable at the close; an ETF close vs iNAV residual above 30 bp is flagged; no daily close is derived from intraday bars. |
| R-28 | M8 | I-12, T-TREND-01..04 | Header declares monthly SMA10m, gross 0.5× below trend, min() composition, claim 'slow-bear protection via the volatility state' and a pooled-onset rule before the run; on the French monthly 1927–2026 fixture it shows stacked ΔMDD on VT ≥ 3 pp (+14.9 pp), PASS at 5 and 50 bp with 45 de-clustered onsets, and prints its GJR-null percentile (87th); a Korea instance is refused; it runs FORWARD-SIM until a US sleeve exists. |
| R-29 | M8 | I-13, T-USFUT-01..05 | Registered once as a new card (one trial) with a Micro ES 5 bp book and notional field; the settling run on French daily Mkt-RF 1926-07 → 2026-08 at 5 bp returns PASS only if PC-1′ holds at 1× and 2× and the card passes at ≥ 80% of decade-spaced starts; it is promoted only if that run passes and a US sleeve with notional ≥ ~₩1bn exists; monthly and banded 50 bp variants are logged as trials. |
| R-30 | M3 | I-10, T-EST-01..05 | On the KOSPI and US fixtures the harness reproduces DLB-T1a (SMA20 outside the 90% QLIKE MCS at h 1/5/21, p ≤ 0.0005; COMB inside all six cells); Stage 1 reports 21-day FHS exceedance, fan PIT and Christoffersen CC; COMB on KOSPI 2001–26 at 3 bp shows vol-of-vol −22% ± 2 pp vs SMA20; a GJR fit outside bounds or a tripped OHLC quality flag falls back to SMA20; an estimator switch without a counted revision is refused. |
| R-31 | M7 | I-15, T-STEP-01..04 | Step references reset after 21 sessions while the hard-stop reference does not; the binding share is printed (≈ 19% KOSPI VT20, 10% US VT15 per EX1 L5); where it exceeds 10% of days the steps act only in the specification book until this CARD-P passes; ΔSR vs no steps within ±0.01 on the fixtures. |
| R-32 | M0 | T-SCHEMA-02 | T-SCHEMA-02: model_card.macro validates only with family_id, ledger_hash, N_raw, N_clusters, N_equiv, linear N̂, V_null, power {se, mde80}, timing_profile, instrument_book, rebalance, no_trade_band, notional_nav, cash_convention, start_band, episode_rule_version, stability lines and gjr_null_pct; macro_state inputs carry value_status and session_date; context_log items carry vintage and retrieved_at_utc. |
| R-33 | M0 | T-DNB-01 | §10 item 11 split (ML vol-state classifiers prohibited; range-based HAR admitted); new entries refused by rules-store validation: a regime-model state acting or displayed, a Mondrian conformal label layer, a maintained ML challenger pipeline, max(SMA20, implied) sizing, product-composed de-risk stacks, a venue switch after results, a stock book as a market-gross scalar; each entry labelled harm / null / inconclusive. |
| R-34 | M7 (frozen before the first card run) | T-PLACEBO-01, T-AVAIL-01 | T-PLACEBO-01: the look-ahead positive control (Korea SOX×KRW gate, +0.28 Sharpe from look-ahead) is flagged; R-12 is flagged (fragility ratio 0.75 > the declared 0.5) while R-03, R-04 and R-06 KR pass; every lag tried is written to the family ledger; T-AVAIL-01 fails on an injected registry error. |
| R-35 | M8 | I-01 | I-01 on 2026-10-02 uses the official close 7,003.74; the data_ok gate passes a stale risk-model input with hedge_credit_off set and fails closed on a stale acting input; verdict_filter admits only PASS and BUILD-AS-INSURANCE cards to the recommended book; refusal books (R-11, R-12) and FORWARD-SIM cards (R-28, R-29) never reach engine_feed. |

### 9.0a When each test runs (`runs_from`)

Every test carries `runs_from: M<k>`, the first milestone at which every module it depends on exists (C-3). A milestone's exit runs exactly the tests and clauses whose `runs_from` is that milestone or earlier, so a clause never blocks an earlier milestone. No test computes a real card's verdict before the M7 freeze (P11). This table and §9.0b are the authoritative exit lists. The Quick start and §12 cells abbreviate them (a rule's own test table counts with the rule); where they differ, these tables govern.

| runs_from | Tests and clauses |
|---|---|
| M0 | T-RO-01, T-HERM-01/02, T-SCHEMA-01/02/03, T-CAP-01, T-BASIS-01 (its S2 clause from M8), T-REPRO-01a, T-COST-02/03, T-BOOK-01 (header clauses; its printed-line clause from M7), T-DNB-01, T-OWNER-01 |
| M1 | T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01/02, T-AVAIL-01, T-STALE-01, T-ROLE-01/02, T-XMKT-01, T-LAG-01/02, T-SYN-01, T-TZ-01/02, T-MISS-01/02, T-SER-01/02, T-PRINT-01, T-H10-01/02, T-H15-01, T-VIX-01, T-SAT-01, T-REGIME-01, T-CAL-01/02, T-RO-02, G-POST-01 (its data rows; the other rows and the deferred clauses of these tests per §9.0b) |
| M2 | T-CAP-02 (its stack-card clause from M7), T-VT-01, T-CORR-01, T-HEDGE-01, T-COST-01, T-LABEL-01, I-02; G-KR-01..04, G-KR-02b/02c, G-US-01/01b/01c; G-KR-06 (reference mode, only once §9.4 item 2's rerun is md5-frozen); deferred clauses per §9.0b |
| M3 | T-B5-01 (its "cannot be PASS" clause from M7), I-10, T-EST-01/02/04 (their Stage-3, bootstrap-CI and counted-revision clauses, T-EST-03 and T-EST-05 from M7); G-B5-01..04, G-EST-01..04 |
| M4 | T-R03-01 (sleeve-scale and years clauses; ΔSR +0.273 on the French fixture as research-phase ledger rows), T-PRIOR-01; G-MOM-01..06, G-MOM-08, G-INTL-01, G-BOOK-01; G-MOM-07 (reference mode) |
| M5 | I-04, I-04b, I-06, I-06b, I-06c, T-CAPS-01, T-ANNOT-01, T-FILL-01..03, T-BAR-01 (R-27 clause), T-HALT-01, T-STEP-05, T-BOOK-03, T-MONO-01; G-LAD-01..03 (reference mode, §9.3.3) |
| M6 | T-CTX-01/02, T-BREAK-01 |
| M7, before the freeze | The harness tests of §8.1.3 step 1: T-DSR-01/02, T-NEFF-01, T-STEP3-01/02, T-SEL-01, T-LEDGER-01, T-ES-01, T-DNH-01, T-ORDER-01, T-EPIS-01, T-EXCESS-01, T-BAND-01, T-POWER-01/02, T-UNDERPOW-01, T-PZERO-01, T-PBO-01, T-SE-01, T-PLACEBO-01/02, T-GATE-04; I-05; then I-08 with T-GATE-01 and T-GATE-03 (the acceptance test) |
| M7, after the freeze | I-08's US VT15 clause and T-GATE-02; I-09, I-07, I-15, I-16, T-EPIS-02, T-TROUGH-01, T-ES-02, T-RLAYER-01, T-R03-01 (step-3 and header clauses), T-R04-01, T-R14-01, T-R06-US-01, T-CARD-01/02, T-REPRO-01b, T-BOOK-02, T-STEP-01..04 and every clause deferred above; G-KR-L*, G-US-F*, G-PWR-*, G-DSR-01/02 |
| M8 | I-01, I-03, I-12, I-13, I-14, T-REF-01/02, T-REPLAY-01, T-SCOPE-01, T-OBS-01..05, T-CARD-03, T-DEMOTE-01..05, T-TREND-01..04, T-USFUT-01..05, T-BASIS-01 (S2 clause); G-KR-05/05s, G-TR-*, G-REF-* |
| M9 | I-11, T-REPRO-01c |
| M10 | T-CRYPTO-01, T-FX-01 |

### 9.0b Clauses that run later than their test

A test listed at milestone k in §9.0a runs at k without the clauses below. Each clause joins its test at the milestone given. A rule-table version of a test (the §9.1 note) follows the same split.

| Test (its §9.0a row) | Clause | runs_from |
|---|---|---|
| T-BASIS-01 (M0) | "vt is not applied to L/S sleeves or to TS trend" | M0 as a rules-store predicate on §7.1 `applies_to`; the runtime check M4 (L/S sleeves) and M7 (R-14) |
| T-CAP-01 (M0) | "The overlay layer cannot emit 0." | M2 |
| T-OWNER-01 (M0) | "the ruling is written to `governance_events.jsonl`" | M0 (the §6.6 appender is an M0 deliverable) |
| T-FIX-01 / G-POST-01 (M1) | Rows: KOSPI close and return, drawdown from the 9,114.55 peak, close / 200-day average, Samsung / SK hynix closes, the KRW=X row | M1 |
| | Rows: rv20, vt, G-KR-01, G-KR-02, G-KR-02b. "Unchanged" items: the 22 Jun / 23 Jun / 30 Jul / 2 Oct weights, the relative label and rv21, turnover, G-KR-02c, and G-KR-02b gross and at 3 bp | M2 |
| | Row: G-B5-01 PIT p | M3 |
| | Row: Samsung + SK hynix implied share (B3a anchor) | M5 |
| | Rows: R-06 KR 3 bp p_ni and R-06 KR 35 bp ΔSR (v1.2-check mode, §9.3.3) | M7, after the freeze |
| | Row: G-KR-05 share. "Unchanged" items: G-KR-05s and G-KR-05 on VT20 | M8 |
| T-ROLE-01 (M1; both tables) | The risk-model clause; "sets every risk-model default" | M2 |
| T-ROLE-02 (M1) | "sets `hedge_credit_off` through its corr63 binding" | M2 |
| | "a missing cash day refuses the card (never cash = 0)" | M7 |
| | "fails the R-28 and R-29 FORWARD-SIM books closed … and HALTs no recommended book" | M8 |
| T-LAG-01 (M1) | "refuses to write the card"; the `timing_probe` exception | M7 |
| T-LAG-02 (M1) | "Re-running a rule … must change the result" (on R-06's vt) | M2 |
| | The `timing_probe` clause | M7 |
| T-MISS-02 (M1) | The risk_model clause; the exceptions in `hedge_state`, `market_vol_target` and `compose` | M2 |
| | The exceptions in `concentration_bound` and `drawdown_ladder` | M5 |
| T-RO-02 (M1) | "I-01 runs with the HTTP transport patched …" | M8 |
| T-CLOSE-01 (M1) | "the workflow never starts before 06:40:30Z (§3.9)" | M8 (the R-35 workflow) |
| T-SEL-01 (M7, before the freeze) | (e) "The card run recomputes f; where it differs from the acceptance report's f …" | M7, after the freeze |
| T-HEDGE-01, R-19 table (M2) | The assertion on a built `macro_state` | M6 |
| T-COST-01 (M2) | "both legs for L/S sleeves" | M4 |
| | "a 2× run exists for every card" | M7 |
| G-US-01c (M2) | The EWMA(0.94) challenger | M3 (R-30 builds `ewma094`) |
| I-06c (M5) | "`macro_state` validates" | M6 |
| | "an acting-field schema error HALTs (OPS) the books the artifact describes" | M8 (`bounds_ok`) |

The HALT clauses of T-ROLE-01, T-LAG-01 and T-MISS-02 stay at M1, because M1 builds the OPS-only per-book runtime (§12 M1; R2-C6).

### 9.1 Unit tests

**Tests defined inside the rules.** R-19 to R-31 and R-34 each carry an acceptance-test table (§5). Those tests belong to this plan, run from the milestone §9.0a gives and are not repeated here: T-BAND-01, T-BOOK-02, T-BOOK-03, T-CAL-01, T-CAL-02, T-DEMOTE-01, T-DEMOTE-02, T-DEMOTE-03, T-DEMOTE-04, T-DEMOTE-05, T-DNH-01, T-DSR-02, T-EPIS-01, T-EPIS-02, T-ES-01, T-ES-02, T-EST-01, T-EST-02, T-EST-03, T-EST-04, T-EST-05, T-EXCESS-01, T-FILL-02, T-FILL-03, T-GATE-01, T-GATE-02, T-GATE-03, T-GATE-04, T-LEDGER-01, T-ORDER-01, T-PBO-01, T-PLACEBO-02, T-POWER-02, T-PZERO-01, T-REGIME-01, T-RLAYER-01, T-ROLE-02, T-SAT-01, T-SE-01, T-SEL-01, T-STEP-01, T-STEP-02, T-STEP-03, T-STEP-04, T-STEP-05, T-STEP3-01, T-STEP3-02, T-TREND-01, T-TREND-02, T-TREND-03, T-TREND-04, T-TROUGH-01, T-UNDERPOW-01, T-USFUT-01, T-USFUT-02, T-USFUT-03, T-USFUT-04, T-USFUT-05, T-XMKT-01. Sixteen IDs appear both below and in a rule table (T-AVAIL-01, T-BAR-01, T-BOOK-01, T-CLOSE-02, T-COST-02, T-COST-03, T-DSR-01, T-FILL-01, T-H10-02, T-H15-01, T-HEDGE-01, T-NEFF-01, T-PLACEBO-01, T-POWER-01, T-ROLE-01, T-STALE-01). Both statements must pass; the rule's table carries the detail.

| ID | Test | Pass condition |
|---|---|---|
| T-RO-01 | Read-only | A static scan of the whole repository, including `core/skills` scripts and the commands of every workflow YAML, finds no order, cancel, withdrawal, deposit-address or transfer call and no import of an order-submission client (the forbidden symbols and AST patterns are listed in the test). `core/engine/orders` is reached only through the simulated order book API. Every artifact has `read_only: true`. |
| T-RO-02 | Runtime read-only guard | The KIS client accepts only an allowlist of quotation endpoints, frozen in `config.py`; any trading or account path raises before a request is built. I-01 runs with the HTTP transport patched to record every request, and the recording shows zero non-allowlisted requests. Whether the KIS app key can trade is checked in M1, beside the quote-field check, and recorded. The Claude API is called without tools, and its text is never parsed by an acting module. |
| T-HERM-01 | Hermetic | The macro test suite passes with all network touchpoints patched to raise |
| T-HERM-02 | No production state | After `tests/run_all.py`, `core/rules` and every family ledger are byte-identical to their pre-run state; tests write only to temporary copies of the rules store, the ledgers and the artifact directory. |
| T-LAG-01 | Lag audit | Inject a datum with `available_at_utc > decision_utc` into any acting input → the backtest raises `LookAheadError` and refuses to write the card. At runtime the books the input feeds go HALTED (OPS; §3.8). A provisional row reaching an acting input is treated the same way. The audit recomputes `usable_at` from the calendars and the registry, independently of `pit_value` (§3.9). The one exception is R-34's `timing_probe` sandbox, which records the violation in `timing_profile.lags[].lag_audit` instead (C-4). |
| T-LAG-02 | Leakage sensitivity | Re-running a rule with the input deliberately shifted one period *earlier* (introducing look-ahead) must change the result and trip T-LAG-01 everywhere outside R-34's `timing_probe` mode; inside it the violation is recorded, not raised. Positional `shift` on a series with gaps must be rejected by the linter / audit. |
| T-SYN-01 | No synthetic acting input | An "auto" provider that degrades to labelled synthetic data for an acting input → `MissingInput`, `status="synthetic_rejected"`, `fail_closed=true`. The same provider for a context item is allowed and labelled. |
| T-PROV-01 (R-01) | Provisional-row guard | On the 2-Oct fixture (vendor row 6,943.66: obs_utc 01:30Z, available_at_utc 01:30Z, retrieved_at_utc 01:56Z, provisional_intraday; KIS row 7,003.74: available_at_utc 06:30:30Z (calendar_bound), retrieved_at_utc 06:40:45Z, official_close), `pit_value('KOSPI_OFFICIAL_CLOSE', decision_utc=2026-10-02T06:30:30Z, knowledge_utc=…, consumer='R-06', require_session=2026-10-02)` returns `MissingInput("missing")` at knowledge_utc 01:31Z (10:31 KST), `MissingInput("provisional_intraday")` at knowledge_utc 02:00Z (11:00 KST) and 7,003.74 [official_close] at knowledge_utc 07:00Z (16:00 KST). The fixture is a synthetic store file, exempt from the post-close-file rule. |
| T-FIX-01 (R-01) | Post-close fixtures | A fixture any of whose close-type rows has `retrieved_at_utc < official_close_utc + 10 min` (`official_close_utc` ≡ `close_print_bound_utc` of that row's session), or any of whose publication-timed rows was retrieved before its `publication_instant`, is refused. The DLA §7 corrected values regenerate at Level-1 tolerance (G-POST-01), each row from the milestone §9.0b gives it. |
| T-BAR-01 (R-01) | Closes are official | A bar-derived close, or a flat-OHLC zero-volume row on a session day, is never stored as a close. A two-source mismatch above 1 bp (index) or any mismatch (stock) is marked `disputed`, uses the official value and raises an alert. Nothing is auto-corrected. |
| T-BAR-02 (R-01) | Disputes are not failures | A disputed official close is returned as a `PITValue` with `dispute = true` and status `disputed`, passes the provisional guard, raises an alert and increments no failure counter. A vendor row absent on a KRX session is `vendor_missing`, not `disputed` (§4.1). |
| T-REPLAY-01 (R-01, P2) | Deterministic replay | Re-running a past decision from the store at its `knowledge_utc` reproduces the artifact byte for byte after canonicalisation (UTF-8 JSON, sorted keys, floats printed with repr, no insignificant whitespace), excluding only `generated_at_utc` and `git_hash`. A replay first restores the runtime state from before the decision (per-book counters, `halt.causes`, the derived bindings and each covariance input's carry count) from the previous decision's artifacts and the governance log; the carry count is derived from the input's stale labels in at most the last 5 artifacts. `data_snapshot_id` is the md5 of the sorted content hashes visible at `knowledge_utc`, so it is order-invariant and unchanged when a later correction is appended. |
| T-CLOSE-01 | Decision time | `decision_time_utc("KR", 2026-10-02)` = 06:30Z, the scheduled close (API unchanged from v1.2), and `close_print_bound_utc("KR", 2026-10-02)` = 06:30:30Z, the decision instant used by the lag audit and stamped as `macro_state.decision_utc`. An official close with exchange print time (available_at_utc) 06:30:20Z is accepted; a record with available_at_utc 06:31Z is rejected for that decision. A receipt timestamp is stored only as retrieved_at_utc; with no exchange print time, available_at_utc is the calendar bound (available_at_source = calendar_bound), so an official close retrieved at 06:45Z with no exchange print time is stored with available_at_utc 06:30:30Z and accepted. Quarantine boundary (`close_print_bound_utc` + 10 min = 06:40:30Z): a KIS close row retrieved at 06:40:29Z is never `official_close` (the decision's read returns `MissingInput`), and one retrieved at 06:40:30Z is; the workflow never starts before 06:40:30Z (§3.9). `decision_time_utc("US", 2026-10-01)` = 20:00Z (EDT) and `close_print_bound_utc("US", 2026-10-01)` = 20:00:30Z, the US decision instant; a US official close stamped 20:00:02Z is accepted for that decision. `decision_time_utc("US", 2026-01-15)` = 21:00Z (EST). |
| T-CLOSE-02 (R-20) | Effective-dated calendar | A KRX session before 2016-08-01 maps to a 06:00Z close; from 2016-08-01 to 06:30Z. `available_at` is bounded by `close_print_bound_utc`: 06:00:30Z for 2015-06-15 … 2016-07-29 (e.g. 2016-07-29), 06:30:30Z from 2016-08-01, and the scheduled close + 30 s print tolerance before 2015-06-15. The CSAT-day close is 07:30Z, bound 07:30:30Z (e.g. 2025-11-13). `decision_time_utc("KR", 2026-10-05)` raises `NotASession`. `decision_time_utc("US", 2026-11-27)` = 18:00Z (early close, EST); `("US", 2025-07-03)` = 17:00Z (early close, EDT). Saturday sessions before 1998-12-12 are present. Regime tags (±8/12/15/30% limits, the 1997 FX peg, short-sale bans, the sell tax 0.30 → 0.15 → 0.20%) are returned for any date. |
| T-AVAIL-01 (R-20, R-34) | Availability fixtures | Golden availability table built from official calendars, exact match: <br>• DGS10 dated Fri 2015-01-02 → KRX close Tue 2015-01-06; <br>• DEXKOUS week of 2026-10-05 → KRX close Wed 2026-10-14; <br>• DGS10 dated 2026-10-09 → US close 2026-10-14; <br>• CSAT 2025-11-13 close 07:30Z. <br>The test fails on an injected registry error. |
| T-STALE-01 (R-19) | Schedule-aware staleness | Over decisions 2016-01-04 → 2026-09-25, DTWEXBGS and DEXKOUS are flagged stale on ≤ 1% of decisions (0.42–0.89% expected; DGS10's 0.33% is G-STALE-01's), and every hit's missed observation date (`d_next`) is in the source-skipped list. The v1.2 rule gives 100% (G-STALE-01). |
| T-ROLE-01 (R-19) | Failure action by role | A stale acting input → fail closed + alert: miss 1 → fail closed; miss 2 → the books it is bound to HALTED (OPS), and no other book; a fresh decision resets the counter. A stale risk_model input → `hedge_credit_off`, never HALTED. A stale context input → label only. |
| T-TZ-01 | Cross-time-zone (KST/ET, DST) | For the KOSPI return dated 2026-10-02 (decided at the KRX close of 2026-10-01), the latest usable US close is dated 2026-09-30. For the return dated 2026-10-01 it is 2026-09-29. The NYSE close of 2026-01-15 (EST) maps to 06:00 KST on 2026-01-16; the close of 2026-07-15 (EDT) maps to 05:00 KST on 2026-07-16. On non-CSAT days no same-date Shanghai or HKEX close enters a KRX decision, nor a same-date TSE close outside 2016-08-01 → 2024-11-04; the same-date TAIEX close does on weekdays, and CSAT days follow the general rule at the CSAT bound (T-XMKT-01). Pre-2007 DST: the NYSE close of 2006-03-20 is 21:00Z and that of 2006-04-03 is 20:00Z. |
| T-TZ-02 | FOMC mapping | The 2026-09-16 statement (14:00 EDT) is 2026-09-17 03:00 KST, so `kr_open_gap_session = 2026-09-17`. The Sep NFP (2026-10-02 08:30 EDT) maps to `kr_open_gap_session = 2026-10-06`. |
| T-MISS-01 | Missing month | CPI YoY for Aug-2026 = **3.353% ± 0.01** (calendar lag). The positional version (3.713%) must not be produced. Derived values that use the Oct-2025 observation as an input (as an endpoint or inside an averaging window: YoY for Oct-2025 and Oct-2026, MoM for Oct and Nov 2025, Sahm's 3-month means) are NaN and flagged; an endpoint YoY whose window merely contains Oct-2025 (Aug-2026) is computed; a vendor value across the gap is tagged `vendor_derived_across_gap`. |
| T-MISS-02 | Fail-closed | An acting input missing or stale → state unchanged, `fail_closed=true`, alert raised, no interpolation; the same failure for more than one decision → HALTED. A stale risk_model input → `hedge_credit_off = TRUE`, never HALTED. An exception in an acting risk-layer function (`market_vol_target`, `concentration_bound`, `drawdown_ladder`, `compose`) → HALTED (OPS) for the books it feeds; an exception in `hedge_state` → `hedge_credit_off = TRUE`, an alert, never HALTED (red line E4). |
| T-CAP-01 | Multiplier bounds | Any overlay multiplier outside [0.5, 1.0], or any vt/vs > 1.0, fails schema validation and rules-store validation. The overlay layer cannot emit 0. |
| T-CAP-02 (R-02) | Composition by `min()` | For 10,000 seeded draws (seed 11) of k ∈ {0, …, 5}, overlays in [0.5, 1]^k (endpoints included), vt ∈ [0, 1] (0 and 1 included), ladder ∈ {1.0, 0.5} and post-re-arm cap ∈ {1.0, 0.5}: composed = vt × min(1.0, overlays, ladder, post_rearm_cap) and composed ≥ 0.5 × vt on every non-HALTED day. The floor applies to `composed`; a risk limit may take `gross` below it without HALTing. 0.75 and 0.5 compose to 0.5 (never 0.375), and the binding factor is logged. A product-composed path raises. The stack card prints the share of days at ≤ 0.25× total exposure and the rebound capture. |
| T-BASIS-01 | Exposure basis | Every multiplier has `exposure_basis`. S2 applied to momentum raises an error. vt is not applied to L/S sleeves or to TS trend. |
| T-SER-01 | Named series | An unnamed "Brent" raises. A BZ=F roll day (2026-04-01, −14.5%) is flagged and excluded from return computations. |
| T-SER-02 | Registered ids | Every series id referenced by the rules store, `data_contracts.roles`, card headers and §4.2 exists in the registry with a contract; an unknown id fails validation. A group id in `roles` or a range-group name in `ranges` resolves through the registry to its member series ids, each of which must exist; a group name used as a series id fails validation. `pit_value` raises when a consumer other than a `context` consumer reads a series it has no binding for (R-19 rule 5). |
| T-PRINT-01 | Closes | The KOSPI close on 2026-03-09 is 5,251.87 (−5.96%). The intraday −8.11% is never stored as a close. |
| T-H10-01 | H.10 production rule | In `run_mode = live`, an attempt to read DEXKOUS for an acting or risk-model input raises. DEXKOUS is a labelled proxy only. |
| T-H10-02 | H.10 strict publication | DEXKOUS dated 2026-09-25 (Friday) is usable from the KRX close of Tuesday 2026-09-29 (KST) and not before. At the KRX close of 2026-10-02 the latest usable DEXKOUS is dated 2026-09-25 (R4b state row). Holiday case: the week of 2026-10-05 is usable from the KRX close of Wed 2026-10-14 (Columbus Day). |
| T-H15-01 | H.15 strict rule | DGS10 dated D has `available_at` = 16:15 ET on the next Fed business day after D. It is usable at the first US close and at the first KRX close after that instant (Fri 2015-01-02 → KRX Tue 2015-01-06, not Mon 2015-01-05). The Treasury par-yield channel with a logged posting time is usable +1 business day. The R4b state row: the flag first on in data dated 2026-09-23 earns in the strict book from 2026-09-28. |
| T-VIX-01 | VIX close timing | On the registry's production channel: VIX(D) read at its 16:15 ET official close (Cboe or Yahoo; value timing) is not usable at the US close of D, and is usable at the US close of D+1 and at the KRX close of K ≥ D+1; FRED `VIXCLS(D)` is usable from the first decision after the logged (live) or declared (history) FRED posting time |
| T-CORR-01 (R-09) | Date-aligned corr63 | corr63 computed on date-aligned (r_eq(D), −Δy(D)) pairs reproduces +0.53 at 2026-09-30 (± 0.01). A series-lag implementation fails (it gives −0.094). |
| T-HEDGE-01 (R-09) | Hedge state never HALTs | A risk-model input that misses two expected releases sets `hedge_credit_off = TRUE`, raises an operator alert and never HALTs any book. `fx_hedge_credit` (no credit while the trailing KOSPI–KRW correlation is ≥ 0) changes no exposure. Core PCE YoY is read through `pit_value` at the decision's `knowledge_utc` from its ALFRED vintages: replaying a decision after a later revision is loaded leaves its `hedge_reasons` unchanged. |
| T-COST-01 | Costs | Turnover \|Δw\| is charged at the gate's pre-registered rate on the day the new weight earns; both legs for L/S sleeves; a 2× run exists for every card. Changing the rate in a card header raises. Reproduce R4b: KOSPI VT20 at 35 bp SR 0.609 ± 0.01; US VT15 at 50 bp SR 0.505 ± 0.01. |
| T-COST-02 (R-26) | Tick floor | 252670 at ₩69 is charged ≥ 72 bp per side. The floor never lowers a table rate. |
| T-COST-03 (R-26) | No lowering | Lowering a cost in a header raises. |
| T-BOOK-01 (R-26) | Header fields | A card without `instrument_book`, `rebalance`, `no_trade_band` and `notional_nav` is refused. A futures line whose one contract exceeds 5% of the sleeve notional is refused (mini KOSPI200 ≈ ₩56m on a ₩0.1bn sleeve); exactly 5% is allowed. A header whose `notional_nav` differs from `sleeves.<market>.notional_nav` at commit is refused. A stock book used as a market-gross scalar is refused. Every card prints execution variants A/B/C and the overnight/intraday attribution. |
| T-B5-01 | Estimator gate (B5 line) | The B5 harness on the fixture reproduces SMA20 FHS exceedance 4.70% ± 0.3 pp on KOSPI 2016-03 → 2026-10 and PASS (PIT p 0.11). A synthetic estimator with σ̂ × 0.7 fails. A vol-target card whose estimator is FAIL cannot be PASS. An estimator switch without a counted revision is refused (R-30). |
| T-LABEL-01 | Causal display labels | Both labels on date t use only σ̂ through t: the relative label the trailing 756 values, the absolute label the expanding history; never smoothed. A value exactly on a quartile boundary takes the higher label (default, judgment). Recomputing after appending future data does not change past labels. KOSPI on 2026-10-02 = "elevated" (relative) and "stressed" (absolute); US on 2026-10-01 = "normal" (relative). |
| T-R03-01 (R-03) | R-03 card lines | On the French Mom fixture (50 bp, both legs) the card prints ΔSR +0.273 ± 0.01, deflated ΔSR 0.98 ± 0.01 at N_equiv 6.3 (PASS) and 0.947 ± 0.01 at linear N̂ 12.6, flagged "step 3 borderline". The scale-free and variance-scaled revisions each carry a committed header md5 before their runs and increment the R-03 family ledger. The years line prints the 20 differing years, with 15 higher gross / 11 net. |
| T-R04-01 (R-04) | R-04 demoted | The card computes step 3 on the R-03 family ledger and reports a deflated add-on of 0.77 ± 0.02 at N_equiv 6.3 → "step 3 FAIL". Card validation rejects any A-provisional or pooled route for a card already run. |
| T-R06-US-01 (R-06) | US 50 bp card | The registered US card shows "REJECT (instrument: US shares via KIS, 50 bp, daily)" and is never re-run. Any vt > 1.0 fails validation. |
| T-R14-01 (R-14) | Trend sleeve header | The R-14 header declares its instrument book and its claim (CARD-O, diversification) and is refused without them. Golden values are restated at cap 1 with sub-period correlations. The failure-mode text reads "not fast-crash protection". |
| T-PRIOR-01 (R-15) | Base weights | base_weight(m, f) = IV_m × 1/K_m over the families with prior ≥ 1 and card not REJECT. Family weights sum to 1 per market and Σ IV_m = 1 (assertions). The Korea reversal prior is stored as 1 (UNVERIFIED). A tilt without a PASSed family card is refused by rules-store validation. |
| T-CAPS-01 (R-07) | Look-through caps | The daily KODEX 200 basket is applied. w_i − g·b̃_i ≤ 0.05 NAV is enforced. The template is read from the rules store (D1). On 2 Oct, under 25/50, the absolute bound is 22.5 / 29.8 = 0.755 and the active-cap bound is at most 0.05 / (0.298 − 0.225) = 0.685; the test asserts the gross and the binding factor in each book (specification and recommended; `concentration.by_book`). Leveraged products count at × L. |
| T-ANNOT-01 (R-08) | R-08 annotation | With the flag on, no book's weights change (an assertion in the book builder). Each flag day writes an annotation and a KIS spread-snapshot request. The fixture reproduces 132 spells, 50.8% of them one day long (DLB-T6a). |
| T-FILL-01 (R-27) | Fill model | A ≈ 15:19 KST decision snapshot filled at the official close reproduces QF1's tracking error vs an official-close decision (0.19% a year on KOSPI; mean \|Δw\| 0.0013) within ±0.05 pp. A limit-locked name (SK hynix, 31 Jul 2026, +29.95%) is non-fillable at the close. An ETF close vs iNAV residual above 30 bp is flagged. No daily close is derived from intraday bars. |
| T-REF-01 (R-11) | S1 retired | S1 is absent from the FORWARD-SIM re-gate queue (BL-S01 closed; BL-G04/BL-D13 at P3). Its card records REJECT (54 strict-H.10 onsets, ΔMDD −1.3 pp, tail 1.00). |
| T-REF-02 (R-12) | S2 retired | S2 is absent from the FORWARD-SIM queue (BL-S02 closed). Its card records REJECT with 71 onsets, including the compliant Treasury +1-business-day timing (ΔMDD −3.1 pp at 50 bp) and strict +2 days (−3.5 pp). G-US-02a reads "compliant via Treasury with logged posting time". |
| T-CTX-01 | Context isolation | No acting module imports or reads `context_log`, the 18-indicator sheet's values, the R-18 break log or a refusal book (static import check plus a runtime guard) |
| T-CTX-02 (R-13) | Context additions | Every `context_log` item carries `vintage` and `retrieved_at_utc`. Revised series store the first print, the current value and the vintage date. LETF AUM, KOFIA margin debt, VRP, the VIX/VIX3M snapshot (16:00 ET) and the KOSPI200 MFIV snapshot (15:30 KST) are stamped `live`. T-CTX-01 still passes. |
| T-BREAK-01 (R-18) | Breaks | An official framework-change event shrinks every macro-conditioned multiplier to 1.0 and starts a forward record. The statistical-break flag and the BOCPD probability (hazard 1/250) are logged with no reader in any acting module or display. Scale-break re-anchoring occurs only on declared events. The statistical leg activates only after EX1's test (≤ 1 false break a decade on 1990–2026; flags within 6 months of 2012 and 2020). |
| T-CRYPTO-01 (R-17) | Crypto clock | `decision_time_utc('CRYPTO', d)` = 00:00:00Z on d+1, the close of the venue's daily bar dated d; annualisation 365; weekday macro data joined as-of with staleness labels. |
| T-FX-01 (R-17) | FX instrument | An FX sleeve card without a declared instrument (KRX USD futures or broker spot) is refused. |
| T-DSR-01 (R-23) | DSR code | Reproduces Bailey–López de Prado's example: 0.9505 at N 46; 0.9004 at N 100 (G-DSR-01). |
| T-NEFF-01 (R-23) | N_eff | On QF3's 26-trial difference-series correlation matrix (seed 11; fixture `QX_EX1_qf3_trial_corr_diff.csv`): E[max Z] = 1.33 ± 0.01 and N_equiv = 6.3 ± 0.4. Padding with 80 near-duplicates moves N_equiv by < 0.5 (6.33 → 6.59). R-03 → 0.98 ± 0.01 PASS; R-04 → 0.77 ± 0.02 FAIL. A card without a ledger hash is refused. No code path computes the Kish N̂. |
| T-POWER-01 (R-24) | Power line | Every card prints SE (HAC and block-250), MDE80 and power. The fixture reproduces SE(ΔSR) 0.061 ± 0.005 (US VT15) and 0.130 ± 0.01 (KOSPI VT20, 2016–26). The UNDERPOWERED code converts only a failed step-5 or PC-3 p-value (a PC-3 point REJECT, PC-1′ or PC-2 failure is never waived). No p-value is printed as 0 (it prints < 1/B). PBO uses the ledger ∪ the frozen PC-6 grid and the card's own objective. |
| T-PLACEBO-01 (R-34) | Timing gate | The look-ahead positive control (the Korea SOX×KRW gate, +0.28 Sharpe from look-ahead) is flagged; its L ≤ 0 rows run only in the `timing_probe` sandbox (C-4). R-12 is flagged (fragility ratio 0.74–0.75 > the declared 0.5) while R-03 and R-04 pass; R-06 KR's 2016–26 raw-flag row and R-11's FR are printed, not asserted (each sits within tolerance of a fragility boundary). Every lag tried is written to the family ledger (its temporary copy in tests). |
| T-CARD-01 | Card integrity | A card whose header md5 differs from the committed header is refused. A class or claim change creates a new revision and increments the family ledger. A card without a ledger hash or the R-26 header fields is refused. `displayed_as ∈ {recommendation, insurance}` iff verdict = PASS. |
| T-CARD-02 (R-21) | Package anchor | `docs/macro_overlay_study.py` re-hashes the package manifest (§8.1.3 step 3) at every card run and refuses to run on a mismatch; an edit to any `gate.*` block, harness source file, acceptance fixture or seed after the freeze is detected. |
| T-CARD-03 (R-35) | Verdict integrity | A card file whose verdict is edited to PASS after its run is refused by `verdict_filter`: the factor stays in the specification book and VERDICT_INTEGRITY pages. A hand-edited `cards/verdicts.jsonl` row breaks the chain and blocks every admission until it is restored. A verdict whose `gate_package_md5` differs from the frozen package's, or whose `data_snapshot_id` does not reproduce from the store, is refused the same way (R2-C4). |
| T-REPRO-01a | Reproducibility: metadata (M0) | Every artifact and card records the seed, `git_hash`, `config_hash`, `data_snapshot_id`, `knowledge_utc`, the ledger hashes and `results_md5` (§6, §7 `reproducibility.record`). |
| T-REPRO-01b | Reproducibility: statistics (M7) | The same seed, rules-store hash, data snapshot and gate package version give identical bootstrap and GJR-null outputs (relative difference ≤ 1e-12 on the same platform and library versions, single-threaded BLAS, NumPy PCG64 seeded through SeedSequence, with spawned child seeds for parallel workers). |
| T-REPRO-01c | Reproducibility: Monte Carlo (M9) | The same holds for the R-16 Monte Carlo paths. |
| T-SCHEMA-01 | Schemas | Every example in this spec validates against its §6 schema: the §6 examples and the §8.4 header (against `model_card_header.macro`), a `<…>` placeholder being replaced by a typed sample first. The schemas load into one registry keyed by `$id`, with the closed-object rule of §6. A missing required field fails; an undeclared field fails. |
| T-SCHEMA-02 (R-32) | Schema 2.0 fields | `model_card.macro` validates only with `family_id`, `ledger_hash_at_registration` and `ledger_hash_at_run`, `N_raw`, `N_clusters`, `N_equiv`, `N_hat_linear`, `N_eff`, `V_null`, `selection_factor`, `power {se_hac, se_blk250, se_plateau, mde80, power_at_0p05, power_at_0p10}`, `timing_profile`, `instrument_book`, `rebalance`, `no_trade_band`, `notional_nav`, `cash_convention`, `start_band` (acting long-sample cards), `episode_rule_version`, `start_band_results`, `midpoint_halves_results`, `gjr_null_pct` and the reproducibility fields; each removed in turn → refused. `macro_state` inputs carry `value_status`, `session_date` and the provenance fields. `context_log` items carry `series_id`, `vintage`, `retrieved_at_utc`, `value_status` and `stale`. |
| T-SCHEMA-03 (R-32) | Every rule output is declared | One synthetic artifact or card per rule, built from that rule's "Outputs and schema fields" list, validates against its §6 schema; a field a rule writes that its schema lacks fails the test. |
| T-OWNER-01 | Owner-decision registry | Each D1–D6 canonical key exists and holds a scalar equal to `owner_decisions.D<n>.value`, and every `{ref: …}` resolves to it. An owner edit flips `status` to `owner_set`, every reference resolves to the new value, and the ruling is written to `governance_events.jsonl`; a literal copy in a rules-store block that differs from its key is refused at load. A card header's `owner_decisions` records the values at commit and is checked only at commit; a later ruling gives a dependent card a counted revision (Quick start). |
| T-VT-01 (R-06) | Vol-target warm-up and degenerate σ̂ | With fewer than 20 valid returns, `market_vol_target` returns status `insufficient_history`, which a book before its first ARMED decision maps to weight 1.0 with status `warmup`, counted as no failure; a flagged stale-carry day is excluded and the window extends; σ̂ = 0 or not finite returns `MissingInput`. On a book that has been ARMED, a store truncated to 15 valid returns gives `MissingInput("missing")`, a failure that counts toward the HALT limit, never weight 1.0. σ̂ uses simple returns with ddof = 1 and reproduces rv20 28.82% and vt 0.694 on 2 Oct. |
| T-HALT-01 (R-07) | HALT sequence by class | A synthetic NAV path breaching exactly −15.00% at the close of t (`<=`): HALTED (RISK) with exposure 0 on sessions t+1 … t+10; automatic re-arm at the decision at the close of t+10; both references reset to the NAV at re-arm; `post_rearm_cap` 0.5 inside `min()` for the weights decided at t+10 … t+19 (earning t+11 … t+20); then normal running. An OPS HALT (a stale acting input) clears at the first decision with the input fresh, with no refusal window, no reference reset and no cap. A risk-limit-breach HALT whose limit-locked stock-book order persists past t+10 stays HALTED at t+10 and re-arms at the first later decision at which the target weights after the prescribed action meet the limit, with no reference reset and the 0.5 cap for the weights decided at that re-arm decision and the 9 after it; a KODEX-basket failure beyond its 5 misses is OPS. A lag-audit violation raised during a RISK HALT keeps the book HALTED after t+10 until the operator re-arms (`halt.causes[]`), and the cap window starts at the operator's re-arm decision. Sessions are those of the book's primary-market calendar. |
| T-SCOPE-01 | HALT scope (C-1) | (a) The R-04 inputs and R-03's paper long/short series failing on 3 consecutive decisions HALT the specification book only; the recommended book stays ARMED with unchanged weights. (b) A missing S&P close on 3 decisions fails the R-28/R-29 FORWARD-SIM books closed and leaves the KR recommended book ARMED. (c) A specification-book NAV at −16% HALTs the specification book only. (d) A recommended-book NAV at −16% HALTs the recommended book (RISK). (e) An exception inside hedge_state sets hedge_credit_off and HALTs nothing. (f) A context_log schema failure HALTs nothing. (g) Once `verdict_filter` admits R-03's factor to the recommended book, `MOM_PAPER_LS_SERIES` is bound to that book in the same run (a governance event), and the series failing on 3 decisions HALTs the recommended book too; a book that reads a factor whose acting inputs are not bound to it is refused at load. (h) While R-06 KR is NOT_RUN, a KOSPI close missing on 3 consecutive decisions, every other input fresh, HALTs `specification:KR` only; `recommended:KR` stays ARMED (vt enters it as 1.0). |
| T-MONO-01 (R-02) | No reallocation | For random multiplier vectors m ≤ m′ elementwise on the I-01 fixtures (seed 11), every market's gross and every family's active budget is weakly monotone in its own multipliers, and every cross-partial is 0; the R-15 K/(K−1) admissibility re-weighting is the one exception, logged as a governance event. |
| T-OBS-01 | HALT records | Each HALT class writes the `runtime[].halt` block of its book and a governance event. |
| T-OBS-02 | Missed decisions | A skipped scheduled run raises MISSED_DECISION (severity page) at the next app start, and the books carry their weights. |
| T-OBS-03 | Alert persistence | Page-severity alerts persist until acknowledged. |
| T-OBS-04 | Errored runs | An exception injected in each acting step writes status = error, raises RUN_ERROR (page), blocks engine_feed, adds 1 to the counter of every book the step serves and HALTs them (OPS, `run_error`) at the limit; the errored decision counts for MISSED_DECISION. An exception in `forward_monitor` is re-evaluated for every skipped decision at the next successful run. |
| T-OBS-05 | Governance log integrity | At app start the `governance_events.jsonl` hash chain is verified; a hand-edited row raises GOVERNANCE_LOG_BROKEN (page). |
| T-DNB-01 (R-33) | DO-NOT-BUILD v2 | §10 item 11 is split (ML vol-state classifiers prohibited; range-based HAR admitted). Rules-store validation refuses: a regime-model state, acting or displayed; a Mondrian conformal label layer; a maintained ML challenger pipeline; `max(SMA20, implied)` sizing; product-composed de-risk stacks; a venue switch after results; a stock book as a market-gross scalar. Each §10 entry is labelled harm / null / inconclusive. |

### 9.2 Integration tests

| ID | Test | Pass condition |
|---|---|---|
| I-01 (R-35) | End-to-end `macro_daily` workflow on post-close fixtures for the KR decisions of 2026-07-30 and 2026-10-02 and the US decisions of 2026-07-30 and 2026-10-01 (the last US close in the fixtures) | All five artifacts are produced and valid against schema 2.0. The 2026-10-02 run uses the official close 7,003.74, and its flags match §11; the 2026-07-30 KR run reproduces vt 0.25 (G-KR-04). The HTTP transport records zero non-allowlisted KIS requests (T-RO-02). The `data_ok` gate passes a stale risk-model input with `hedge_credit_off` set and fails closed on a stale acting input. `verdict_filter` admits only PASS factors (RECOMMENDATION or BUILD_AS_INSURANCE) and R-31 steps with disposition `INVARIANT_STEP` to the recommended book; R-06 KR, BUILD_AS_INSURANCE on PASS but NOT_RUN today, is refused. Refusal books (R-11, R-12) and FORWARD-SIM cards (R-28, R-29) never reach `engine_feed`. Decision gates fire on injected failures. |
| I-02 | Episode replay: 2024-07-31 → 2024-08-09 and 2026-06-22 → 2026-07-30 | Korea vt weights and window returns match §9.3.1 (G-KR-03 and G-KR-04), gross and net |
| I-03 | Book separation | The recommended book never reads a FORWARD-SIM multiplier, a refusal-book multiplier or a non-PASS factor (an assertion on the book builder). It refuses R-04. No recommended or specification book reads the R-11 or R-12 multiplier. |
| I-04 | Ladder steps | With the overlay at 1.0 and a whole-book NAV drawdown of −12% from the step reference: evaluator BLOCKED for new entries, and the step multiplier 0.5 composed by `min()` (never 0.25 × vt). After 21 sessions in a step, the step reference resets to the current NAV; the hard-stop reference does not. Where the steps bind on more than 10% of days on the declared book, they act only in the specification book. |
| I-04b (R-07) | Hard stop and re-arm | A −15% book-NAV breach (default level; owner decision D2) sets that book HALTED (RISK), refuses re-arm for 10 sessions, re-arms automatically, resets both references to the NAV at re-arm and caps exposure at 0.5 × vt (inside `min()`) for 10 sessions (T-HALT-01). The KOSPI VT20 1997–2026 HALT count under this rule is pinned once computed (§9.4). On the KOSPI 1997–2026 fixture the book re-enters after every HALT; the literal v1.2 rule stays permanently HALTED from 1997-10, with 714 cycles (G-LAD-01). |
| I-05 | Full-sample lag audit | Zero violations across every backtest used for golden values that are flagged COMPLIANT in §9.3 |
| I-06 | Event calendar | A cancelled event (Oct-2025 CPI) produces no window. A delayed event moves its window. A US CPI night sets the KR opening-gap flag for the next KRX session. The BoK decision and the press conference are separate events with status. Window hits produce BLOCKED evaluator decisions only for new intraday entries. |
| I-06b (R-10) | Multi-session gaps | A KRX session that follows two or more US sessions since the previous KRX close carries `gap_sessions ≥ 2`, and its displayed 1-day VaR is scaled by √max(n_US, 1). Example: 2026-10-06, after the 5-Oct substitute holiday. The BoK decision and the press conference are separate events with status. No event tag changes any weight (an assertion). <br>`QC_modules.csv` words this as "a KRX session after a multi-day US closure". The gap actually arises when the KRX is closed while US sessions continue (EX2), and this test follows that reading. |
| I-06c (R-10, C-1) | Zero-gap session | The KR decision of 2026-11-26 (effective session 2026-11-27; the NYSE was closed on 2026-11-26): `gap_sessions` = 0, VaR scale 1, `kr_open_gap_event` false; `macro_state` validates; the books stay ARMED. An out-of-schema context field never HALTs; an acting-field schema error HALTs (OPS) the books the artifact describes. |
| I-07 | Card study | `docs/macro_overlay_study.py` on fixtures, under the frozen package, writes one card per rule with all nine gate lines, the CARD-P v2 checks, the power line, the timing profile and the ledger hash. In v1.2-check mode (§9.3.3) on the Yahoo fixture, the R-06 KR long-history computation reproduces G-KR-L01 to G-KR-L08 within Level-1 tolerance. |
| I-08 (R-21) | Gate-acceptance test | Run once, with at most one bounded redesign (R-21 9(a), T-GATE-04); results md5-frozen; every attempt logged. At most 10% of 300 circular-shift placebos per family pass PC-1′ (both legs: point > 0 and p × f ≤ 0.10 at 1×), and at most 2 of 20 per card pass PC-1′. Families, multiplier series, markets, spans, costs and fixtures are listed in the acceptance report (the CARD-P headers drafted for §8.1.3). Per-card τ_k = round(252 + k·(T − 504)/19), k = 0…19. The negative controls (US VT 5-day and 10-day at 50 bp; post-shock-day and post-shock-week 0.5×; stale VT with σ lag 252) all return REJECT or INSUFFICIENT DATA; the 5-day VT is REJECTed by the PC-3 point (ΔSR −0.29). Every attempt runs with the D6 rule recorded in the package; if a control passes, the recorded D6 guard is added and the test is re-run. Later `run_all.py` runs only re-verify `acceptance_report_md5` and `definitions_md5`. After the freeze: on the US VT15 50 bp fixture the v2 verdict is INSUFFICIENT (ES21 +1.65 pp, ES126 +3.8 pp, p_ni printed; T-GATE-02). |
| I-09 (R-22) | Episodes and conventions | The episode builder returns 18 alternating ≥ 20% KOSPI episodes on 1997–2026 (12 with troughs before 2008) and 4 on 2016–26; 16 S&P episodes at 15% on 1990–2026; and no Sep-2026 episode. The Korea definitive cell's PC-4 maximum share is 0.174 ± 0.01 (0.493 under §8.6, printed; G-KR-L09). Card statistics use excess returns with call-rate / RF cash (Korea p_ni 0.078 ± 0.01 on PX2's cash fixture in v1.2-check mode; T-EXCESS-01). Every card prints a trough → +63-session window, not gated. |
| I-10 (R-30) | Estimator harness | On the KOSPI and US fixtures the harness reproduces DLB-T1a: SMA20 outside the 90% QLIKE MCS at h 1/5/21 (p ≤ 0.0005), COMB inside all six cells (G-EST-01). Stage 1 reports 21-day FHS exceedance, fan PIT and Christoffersen CC. COMB on KOSPI 2001–26 at 3 bp shows vol-of-vol −22% ± 2 pp vs SMA20 (G-EST-04). A GJR fit outside bounds or a tripped OHLC quality flag falls back to SMA20. An estimator switch without a counted revision is refused. |
| I-11 (R-16) | Quant Lab | GARCH/GJR parameters are fitted on expanding (≥ 10-year) windows. The lab shows max(fast FHS, GJR-EVT) with Kupiec, Christoffersen and ES Z2 lines, and reports 2016–26 and 2026 separately. The replay library reproduces the Jul-2026 KOSPI path (−38.6% in 27 sessions) on the current book with regime metadata. No lab output is read by a sizing module. M9 acceptance is out-of-sample on 2016–26: 99% VaR with Kupiec p ≥ 0.05 and Christoffersen CC p ≥ 0.05; ES 97.5% Z2 not rejected at 5% (simulated critical values); fan PIT χ² p ≥ 0.01 at h = 21 (thresholds: default, judgment). The 2026-only lines are reported, not gated. |
| I-12 (R-28) | Trend-axis card | The header declares monthly SMA10m, gross 0.5× below trend, `min()` composition, the claim "slow-bear protection via the volatility state" and a pooled-onset rule, all before the run. It shows stacked ΔMDD on VT ≥ 3 pp (+14.9 pp on the daily US VT15 book, 1991–2026; PX2) and, on the French monthly 1927–2026 fixture, PASS at 5 and 50 bp with 45 de-clustered onsets (G-TR-01), and prints its GJR-null percentile (87th). A Korea instance is refused. It runs FORWARD-SIM until a US sleeve exists. |
| I-13 (R-29) | US futures card | Registered once as a new card (one trial), with a Micro ES 5 bp book and a notional field. The settling run on French daily Mkt-RF 1926-07 → 2026-08 at 5 bp returns PASS only if PC-1′ holds at 1× and 2× and the card passes at ≥ 8 of the 10 decade-spaced starts with no REJECT at any of them; the card's recorded verdict is its full-span v2 verdict (R-29). It is promoted only if that run passes and a US sleeve with notional ≥ ~₩1bn exists (D5). Monthly and banded 50 bp variants are logged as trials. |
| I-14 (R-25) | Forward monitoring | CARD-P demotion reads "forward ΔMDD vs S ≤ 0 = no protection". All statistical triggers use whole-book NAV. On a 20-shift placebo panel the book-level false-demotion rate is ≤ the declared budget (default 10% a year; D4). An injected lag-audit violation, or an acting-parameter edit outside a revision, demotes immediately. No forward record can raise a card's verdict. |
| I-15 (R-31) | Step-down card | Step references reset after 21 sessions; the hard-stop reference does not. The binding share is printed (≈ 19% for KOSPI VT20 and 10% for US VT15, per EX1 L5). Where it exceeds 10% of days, the steps act only in the specification book until this CARD-P passes. ΔSR vs no steps is printed and matches the R-31 reference run (§9.4; EX1 L5's +0.005 / +0.006 used one shared reference and is informative). |
| I-16 (R-06) | Korea formal card | On KRX official closes, from the first close + 20-session warm-up; ETF 3 bp; SMA20, target 0.20, cap 1; excess returns. The verdict is PASS only if: (i) a v2 CARD-P PASS on the full span; (ii) a PASS on the ETF-era line to 2025-12; (iii) no REJECT at any of the 32 monthly starts 1997-05…1999-12 and a PASS in ≥ 22 of them; (iv) no REJECT in either midpoint half, all at the computed selection factor (both verdicts printed). The card prints the insurance label, the timing return and the per-regime table. The run prints its differences from G-KR-L01 (Yahoo, cash 0, v1.2 checks), with the expected direction of each convention change (excess returns: ΔSR +0.026 → +0.006, p_ni 0.052 → 0.078; T-EXCESS-01). The comparison is informative, never a pass condition and never a reason to change the package (P11). Data check (v1.2-check mode, §9.3.3): the raw-flag run on the KRX official-close fixture reproduces G-KR-L01 within Level-2 tolerance, each deviation explained in the acceptance report; it tests the data source, never the card. Pass conditions: the verdict function returns PASS iff (i)–(iv) hold, tested with injected sub-verdicts for each failing branch; the formal verdict, header md5 and results md5 are written. |

### 9.3 Golden values

#### 9.3.1 Regression goldens: gross R4, net R4b (v1.2 conventions; post-patch where DL-A recomputed)

**Reference data definitions:**
- Ken French daily files (Mom, ST_Rev, 5-factor 2×3, regional Mom) through 2026-08-31, and the monthly F-F factors for the 24-month market return;
- FRED series as downloaded on 2026-10-02 (latest vintage);
- Yahoo daily closes (^KS11, ^GSPC, SPY, KRW=X, ^TNX, ^RUT) through each market's last official close before the 17:20 KST freeze (KRX 2026-10-02; US 2026-10-01; KRW=X 2026-10-01);
- FRED NASDAQ100.

All of these are frozen in the test fixtures.

**Construction rules.**
- Returns are simple daily returns.
- The US market is French Mkt-RF through 2026-08, spliced with the ^GSPC price return for Sep-2026. Korea uses ^KS11 price returns (no dividends).
- **Timing:** a weight built from information through the close of t−1 earns the return of t, which is "decide at the close of t, earn from t+1". The exceptions are flagged in the Timing column.
- **Research bootstrap:** circular, 63-day blocks, 1,000 resamples, seed 20261002 (R4-comparable). Gate-style statistics for the cards use §8.5.
- **Costs (R4b):** per side × |Δw|, charged on the day the weight earns. Initial entry not charged. Buy-and-hold uncosted. Momentum: the overlay's own turnover on both legs, with French Mom gross of its constituent turnover.

**v2.0 note.**
- These goldens test the harness on the v1.2 conventions: Korea with cash at 0, the US on Mkt-RF excess returns, the §8.6 windows.
- v2.0 card statistics use excess returns over local cash and objective episodes (R-22). The formal runs under the frozen package produce new results, md5-frozen at their first run.
- Values that DL-A recomputed after the 2-Oct patch appear here in their post-patch form; the full before/after list is G-POST-01 (§9.3.2).
- Values DL-A did not recompute are kept as **pre-patch R4/R4b** and labelled so. Their rerun is pending (§9.4).

**Tolerances:**
- **Level 1**, a reference implementation on these definitions: Sharpe ±0.01; max DD ±1 pp; window returns ±1 pp; weights ±0.02; bootstrap shares ±0.03.
- **Level 1, other statistics** (default, judgment): p-values ±0.01 (p ≥ 0.05) and ±0.005 (p < 0.05); z ±0.05; ES, CDaR and ΔES ±0.2 pp; deterministic counts exact; bootstrap-dependent counts ±1; percentiles ±5; QLIKE ratios ±0.005; SE ±0.005; vol levels ±0.1 pp; other ratios ±0.01; prices exact.
- **Level 2**, QUANTGEN production feeds (e.g., KIS KOSPI official closes): Sharpe ±0.03; window returns ±2 pp; max DD ±2 pp; p-values ±0.02 (default, judgment). Every deviation must be explained in the acceptance report.
- **Thresholds.** A verdict derived from a statistic within tolerance of its threshold is asserted as a class, never as a point (§9).

**Timing flags:**
- **COMPLIANT**: the computation obeys §4.1 for a decision at the close.
- **VALUE**: the input is used at its observation time, as a live-feed proxy; compliant only if production reads a live timestamped feed of the same quantity.
- **NON-COMPLIANT**: the input is used before its publication or official close. Kept only for traceability; superseded by the strict row.

**US momentum (French Mom daily, 1990-01-02 → 2026-08-31). Net = 50 bp per side (US shares via KIS) on the overlay's own turnover, both legs.**

| ID | Quantity | Gross (R4) | Net 1× (R4b) | Net 2× (R4b) | Timing |
|---|---|---|---|---|---|
| G-MOM-01 | Static Mom: Sharpe / max DD | 0.399 / −63.3% | 0.399 / −63.3% (no overlay turnover) | same | COMPLIANT |
| G-MOM-02 | R-03 vol scale (σ126, 12%, cap 1): Sharpe / max DD / avg weight / % days at cap | **0.714** / −27.9% / 0.870 / 60.6% | 0.672 / −28.7% | 0.631 / −29.4% | COMPLIANT |
| G-MOM-03 | R-03 × R-04 (DM 0.5): Sharpe / max DD / vol-matched max DD | **0.798** / −20.9% / −30.5% | 0.745 / −21.6% | 0.691 / −22.7% | COMPLIANT |
| G-MOM-04 | DM add-on over R-03: full / ex Sep-2008–Dec-2009 / 2013-04 → 2026-08 / 2020–26 | +0.084 (0.996) / +0.056 (0.97) / +0.055 (0.94) / +0.101 (0.93) | full +0.072 (0.983); 2013-04+ +0.044 (0.92); 2020–26 +0.080 (0.91) | full +0.061 (0.958) | COMPLIANT |
| G-MOM-05 | DM gate: % of days on / spell onsets / transitions a year | 10.6% / 7 / 0.38 | — | — | COMPLIANT |
| G-MOM-06 | Episodes, static → spec stack (gross) | Apr-2009 −26.8% → −4.2%; Mar–May 2009 −45.6% → −8.0%; Jan-2001 −21.9% → −15.7%; Nov-2020 −12.0% → −3.9%; Jan-2023 −13.7% → −3.8%; Jul-2026 −10.9% → −5.9%; calendar 2020 −11.0% → +3.1%; calendar 2022 +17.4% → +12.3%; May–Nov 2008 +21.8% → +9.5% | — | — | COMPLIANT |
| G-MOM-07 | Reference (not spec; `reference_only`, §9.3.3) | Vol scale cap 2: 0.907; DM 0×: 0.657 | — | — | COMPLIANT |
| G-MOM-08 | R-03 card statistics (vs unscaled, 50 bp) | — | ΔSR +0.273 (share 1.00); one-sided p 0.0005 (10-session) / 0.000 (251-session PW); 70% of years positive | ΔSR +0.231 (0.998) | COMPLIANT |
| G-BOOK-01 | (Mom + ST_Rev + RMW)/3: static → spec | 1.358 → **1.753**; 2020–26 0.400 → 0.618. ST_Rev static 1.253; RMW static 0.480. | not recomputed (factor turnover not modelled) | — | COMPLIANT |

**International momentum (French regional WML, daily)**

| ID | Quantity | Gross (R4) | Timing |
|---|---|---|---|
| G-INTL-01 | Vol scale cap 1, 12% (full sample from 127 days after start) | Japan 0.073 → 0.196; Europe 0.843 → 1.143; APxJ 0.924 → 1.125 (2016–26: 0.921 → 0.897); Developed ex-US 0.799 → 0.996 | COMPLIANT |

Net values are not computed: QUANTGEN has no regional momentum sleeve. A card for one would use its venue's cost.

**Korea (^KS11, 2016-01-04 → 2026-10-02). Net: KRX ETF book 3 bp; KRX stock book 35 bp; 2× = 6 / 70 bp.**

| ID | Quantity | Gross (R4) | Net ETF 3 bp | Net stock 35 bp | Net 2× (6 / 70 bp) | Timing |
|---|---|---|---|---|---|---|
| G-KR-01 | Buy-and-hold: Sharpe / max DD | 0.637 / −43.9% | same (uncosted) | same | same | COMPLIANT |
| G-KR-02 | R-06 vol target (SMA20, 20%, cap 1): Sharpe / max DD | **0.641** / −36.8%. 2016–25: 0.457 vs 0.534. 2018–24: −0.052 vs 0.071. | 0.638 / −36.8% | **0.609** / −37.2%; 2016–25 0.428; 2018–24 −0.083 | 0.635 / −36.9%; 0.576 / −37.5% | COMPLIANT |
| G-KR-02b | R-06 ΔSR vs buy-and-hold (share): 2016–26 / 2016–25 / 2018–24 | +0.004 (0.45) / −0.077 (0.06) / −0.123 (0.03) | +0.001 (0.44) / −0.079 (0.05) / −0.125 (0.03) | −0.029 (0.36) / −0.106 (0.02) / −0.154 (0.01) | −0.001 / −0.061 (0.28) at 70 bp (−0.061: **pre-patch R4b**) | COMPLIANT |
| G-KR-02c | Static book with VT20's average exposure (0.925): max DD; ΔMDD of VT20 vs it | −41.3%; +4.5 pp | +4.4 pp | +4.1 pp | +4.4 / +3.8 pp | COMPLIANT |
| G-KR-03 | R-06 windows (vt vs buy-and-hold) | Jul-2026 crash −12.2% vs −38.6%; Mar-2026 −7.9% vs −19.9%; Aug-2024 −7.9% vs −5.5%; Apr-2025 −11.7% vs −12.0%; 2020 crash −25.8% vs −34.1%; 2020 rebound +25.9% vs +49.9%; H1-2026 +51.7% vs +101.1%; 30 Jul → 30 Sep 2026 +5.9% vs +22.2% | Jul-2026 −12.3%; Mar-2026 −7.9%; Aug-2024 −7.9%; 2020 crash −25.8%; H1-2026 +51.6% | Jul-2026 −12.3%; Mar-2026 −8.0%; Aug-2024 −8.0%; Apr-2025 −11.8%; 2020 crash −26.0%; 2020 rebound +25.4%; H1-2026 +50.5%; post-crash +5.6% | — | COMPLIANT |
| G-KR-04 | R-06 weights | 22 Jun 2026 0.30; 23 Jun 0.33; 30 Jul 0.25; earning on 2 Oct 0.61; decided at the 2 Oct close for the next session 0.69 (0.694; rv20 28.8%) | same | same | same | COMPLIANT |
| G-KR-05 | S1 KRW 0.75× (DEXKOUS, D ≤ K−1): ΔSR vs buy-and-hold / on VT20 / % days on | +0.032 (0.967) / +0.042 (0.977) / 9.0% | +0.029 (0.94) / +0.038 (0.96) | **−0.008 (0.32)** / −0.007 (0.34) | +0.025 / +0.034 at 6 bp; −0.048 / −0.057 at 70 bp | **VALUE** (H.10 publication ignored) |
| G-KR-05s | S1 strict H.10 publication: ΔSR vs buy-and-hold / on VT20 / % days on / onsets (20-session) | **+0.001 (0.53)** / +0.013 (0.74) / 9.1% / 26 | −0.000 (0.49) / +0.012 (0.70) | −0.016 (0.22) / −0.007 (0.34) | −0.002 / +0.010 at 6 bp; −0.034 / −0.027 at 70 bp | COMPLIANT |
| G-KR-06 | Reference vol target cap 1.5 (prohibited; §10 item 2; `reference_only`, §9.3.3) | Sharpe 0.534; max DD −46.2% (**pre-patch R4**; not recomputed on the official close) | — | — | — | COMPLIANT |

G-KR-05 and G-KR-05s are the R-11 refusal book, kept for traceability (R-11 is retired as a REJECT on 1997–2026; §9.3.2 G-REF-01).

**US market (Mkt-RF + ^GSPC Sep-2026, 1990-02-01 → 2026-09-30). Net: US shares via KIS 50 bp; 2× = 100 bp.**

| ID | Quantity | Gross (R4 / R4b) | Net 50 bp | Net 100 bp | Timing |
|---|---|---|---|---|---|
| G-US-01 | Buy-and-hold vs R-06 (SMA20, 15%, cap 1): Sharpe / max DD | 0.534 / −59.2% vs **0.602** / −49.9% | VT15 **0.505** / −53.8%; ΔSR −0.028 (0.29) | 0.409 / −57.3%; ΔSR −0.125 (0.03) | COMPLIANT |
| G-US-01b | Static book with VT15's average exposure (0.890): max DD; ΔMDD of VT15 vs it | −54.0%; +4.1 pp | +0.2 pp | −3.4 pp | COMPLIANT |
| G-US-01c | Challenger EWMA(0.94), same target: Sharpe | 0.605 | 0.520 | 0.434 | COMPLIANT |
| G-US-02 | S2 rates 0.5×, **value timing**: ΔSR vs buy-and-hold / on VT15 / % days on / onsets (60-session) | +0.038 (0.98) / +0.037 (0.97) / 6.2% / 50 | −0.065 (0.00) / — | −0.168 / — | **NON-COMPLIANT** (DGS10(D) used at the close of D) |
| G-US-02a | S2 at +1 business day (v1.0 "strict") | +0.010 (0.67); 1990–2007 −0.017 | −0.093 (0.00) | −0.196 | **COMPLIANT via the Treasury par-yield channel** with a logged posting time ("usually available … by 6:00 PM Eastern Time"; "may be delayed"); **NON-COMPLIANT via H.15/FRED** by 15 minutes (DGS10(D) posts 16:15 ET on D+1) |
| G-US-02s | **S2 strict H.15 (+2 business days)**: ΔSR vs buy-and-hold / on VT15 / 1990–2007 / 2008–26 / 2020–26 | **−0.000 (0.53)** / −0.007 (0.39) / −0.034 / +0.025 (0.77) / +0.084 (0.92) | **−0.103 (0.00)** / −0.120 (0.00) | −0.206 / −0.233 | COMPLIANT |
| G-US-03 | S2, 2015–26 by timing | DGS10 +0.066 (NON-COMPLIANT); ^TNX +0.071 (VALUE, live proxy); +1 day +0.071 (COMPLIANT via Treasury with a logged posting time; NON-COMPLIANT via H.15 by 15 min); **+2 business days +0.053 (0.90)** (COMPLIANT) | ^TNX −0.020 (0.31); +2 bd −0.032 (0.20) | ^TNX −0.111; +2 bd −0.118 | as listed |
| G-US-04 | S2 duration proxies (value timing) | NDX 2008–26 +0.039 (0.94); Russell 2000 2015–26 +0.058 (0.97); small-cap proxy 1990–26 +0.025 (0.89) | not recomputed | — | **NON-COMPLIANT** (value timing on DGS10) |

G-US-02 to G-US-04 are the R-12 refusal book, kept for traceability (R-12 is retired as a REJECT at every timing and cost; §9.3.2 G-REF-02). G-US-01 to G-US-01c are the registered 50 bp card (REJECT, instrument-specific); the futures-line book is G-US-F02.

**B5-style estimator check (R4b; daily origins; FHS form unless stated).** The 5% VaR exceedance band is ±2 binomial SE.

| ID | Market / window | SMA20 | EWMA(0.94) | GARCH(1,1)-t, refit 7 / window 504 (informational) |
|---|---|---|---|---|
| G-B5-01 | KOSPI 2016-03 → 2026-10 (2,594 origins; band 4.14–5.86%) | 4.70%, PIT p 0.11 → **PASS**; normal form 6.75%, PIT p < 0.001 → FAIL; every-7th-session subsample 7.55% (371 origins; band 2.74–7.26%) → outside | 4.90%, PIT p 0.03 → **PASS** | t-quantile 6.92% → FAIL; FHS 5.42% → PASS (2,123 origins) |
| G-B5-02 | SPY 2016-03 → 2026-10 (2,663 origins; band 4.16–5.84%) | 4.99%, PIT p 0.57 → **PASS** | 5.22%, PIT p 0.79 → **PASS** | t-quantile 6.33%, PIT p < 0.001 → FAIL (the app's own study: 6.6%, PIT p 0.003, REJECT) |
| G-B5-03 | US market 1991-03 → 2026-10 (8,961 origins; band 4.54–5.46%) | 5.31%, PIT p 0.98 → **PASS** | 5.31%, PIT p 0.93 → **PASS** | not run |
| G-B5-04 | Display labels on 2 Oct 2026 | Relative (trailing 756): KOSPI **elevated** (σ̂ 28.8%; quartiles 15.7 / 18.6 / 33.6%; 70th percentile); US **normal** (10.7%; 10.5 / 12.7 / 15.2%; 28th percentile). Absolute (expanding full history): KOSPI **stressed** | — | — |

**Current state.** §11 values, post-patch (Level-1 tolerance).

#### 9.3.2 New golden values (v2.0; DL-A and DL-B)

**Scope.**
- Every number below appears in `QX_DLA_data_lab_protective_cards.md` or `QX_DLB_data_lab_estimators_regimes.md`; the CSV results are named in each file.
- They are **indicative computations under the v1.2 checks on local reference data** (Yahoo ^KS11 price, Korea cash 0; French Mkt-RF for the US). The harness must reproduce them at Level-1 tolerance in v1.2-check mode (§9.3.3); rows that need a refused configuration run in reference mode.
- The formal v2 runs on KRX official closes with excess returns are compared with these rows informatively (I-16), never as a pass condition; their verdicts come from the frozen package, not from these rows.

**G-POST-01: post-patch values** (DLA §7, `QX_DLA_postpatch.csv`; the 2-Oct official close). T-FIX-01 regenerates the right-hand column, each row from the milestone §9.0b gives it.

| Item | Printed in v1.2 (pre-patch) | Golden (post-patch) |
|---|---|---|
| KOSPI close, 2 Oct | 6,943.66 (intraday print) | **7,003.74** |
| KOSPI return, 2 Oct | −0.40% | **+0.46%** |
| Drawdown from the 9,114.55 peak | −23.8% | **−23.2%** (−23.16%) |
| Close / 200-day average | 1.098 | **1.107** |
| rv20 (SMA20) | 28.9% | **28.8%** (28.82%) |
| vt decided at the 2-Oct close | 0.691 | **0.694** |
| G-KR-01 buy-and-hold Sharpe (MDD unchanged) | 0.634 | **0.637** |
| G-KR-02 VT20 Sharpe, gross / 3 / 35 / 6 / 70 bp (MDD unchanged) | 0.638 / 0.635 / 0.605 / 0.632 / 0.573 | **0.641 / 0.638 / 0.609 / 0.635 / 0.576** |
| G-KR-02b at 35 bp | −0.028 (0.37) | **−0.029 (0.36)** |
| R-06 KR 3 bp: p_ni at 10-session / PW blocks | 0.24 / 0.21 | **0.25** (0.246) / 0.21 (0.208) |
| R-06 KR 35 bp: ΔSR | −0.028 | **−0.029** (p_ni 0.32 / 0.29 unchanged) |
| G-KR-05 KRW value timing (share) | +0.032 (0.965) | +0.032 (**0.967**) |
| G-B5-01 KOSPI SMA20 FHS PIT p (exceedance 4.70% unchanged) | 0.12 | **0.11** (0.107) |
| Samsung + SK hynix implied share (B3a anchor) | ≈ 53.7% | **≈ 53.6%** (Samsung 29.8% + hynix 23.8%) |
| Samsung / SK hynix close | ₩273,750 / ₩1,832,000 | **₩276,000 / ₩1,841,000** |
| KRW=X last row; 20-observation change | 1,360.63 (2 Oct); +0.38% | **1,356.84 (1 Oct); −0.11%** (provisional 2-Oct row dropped) |

Unchanged at the printed precision:
- the weights on 22 Jun / 23 Jun / 30 Jul 2026 (0.30 / 0.33 / 0.25), and the weight earning on 2 Oct (0.61);
- the relative label "elevated" (quartiles 15.7 / 18.55 / 33.6%; 70th percentile), and rv21 31.9% at the 73rd percentile;
- turnover 1.50;
- G-KR-02c, G-KR-02b gross and at 3 bp, G-KR-05s, and G-KR-05 on VT20.

**Korea vol target on long history** (DL-A grid, `QX_DLA_korea_grid.csv`; KRX ETF 3 bp unless stated; v1.2 checks; columns ΔMDD vs S (2×) · tail ratio · ΔSR (2×) · p_ni (10 / PW) · episodes + / n (max share) · years · plateau → verdict):

| ID | Sample / book | Values | v1.2-check verdict |
|---|---|---|---|
| G-KR-L01 | 1997-04 → 2026-10, ETF 3 bp (definitive cell) | +12.7 (+12.5) · 0.68 · +0.026 (+0.021) · 0.052 / 0.029 (PW block 183) · 4/11 (0.493) · 0.70 · 0.875; B5 5.04%, PIT p 0.46 | PASS (fragile) |
| G-KR-L02 | 1997-04 → 2026-10, futures 5 bp | +12.6 (+12.3) · 0.68 · +0.023 (+0.015) · 0.055 / 0.030 · 4/11 (0.493) · 0.70 · 0.875 | PASS |
| G-KR-L03 | 1997-04 → 2026-10, stock 35 bp (reference line; not an admissible book for R-06) | +10.9 (+8.3) · 0.68 · −0.020 (−0.071) · 0.141 / 0.129 · 4/11 (0.503) · 0.70 · 0.625 | INSUFFICIENT |
| G-KR-L04 | 1998-01 → 2026-10 | +3.8 (+3.7) · 0.70 · +0.001 (−0.003) · 0.082 / 0.055 · 4/11 (0.492) · 0.72 · 0.625 | PASS (thin) |
| G-KR-L05 | 2002-01 → 2026-10 | +11.0 (+10.8) · 0.82 · +0.030 (+0.026) · 0.038 / 0.010 · 5/11 (0.466) · 0.72 · 1.000 | PASS |
| G-KR-L06 | 1997-04 → 2015-12 | +10.6 · 0.68 · +0.025 · 0.086 · 1/3 (GFC) · 0.68 · 0.75 | INSUFFICIENT (sufficiency: 3 §8.6 windows) |
| G-KR-L07 | 2016-01 → 2025-12 | +5.7 · 0.95 · −0.079 · 0.400 · 1/7 · 0.70 · 0.25 | REJECT (PC-2, PC-4) |
| G-KR-L08 | 2016-01 → 2026-10 | +4.4 · 0.82 · +0.001 · 0.246 · 3/9 (0.59) · 0.73 · 0.625 | INSUFFICIENT |
| G-KR-L09 | Episode-set sensitivity, definitive cell | §8.6 + Sep-2026: 5/12 (max 0.490); objective bear-20: **14/18 (max 0.174)**; on bear-20, 10 of the 12 bears with troughs before 2008 are positive (e.g. 1997-H2 +14.5 pp, 1998-H1 +19.9 pp, 2000 +10.2 and +7.9 pp) | — |
| G-KR-L10 | Start sweep, monthly starts 1997-02 → 2003-01 | 71 of 72 PASS; the 1998-10 start (p_ni 0.103, within tolerance of 0.10) is asserted as PASS or INSUFFICIENT, so the count is 71–72; ΔMDD +3.7 to +12.7 pp | — |
| G-KR-L11 | Episode benefits vs S, definitive cell (pp) | GFC +9.1; 2011 −0.6; 2015–16 −1.3; 2018Q4 −1.6; 2020 crash +3.9; 2022 −3.8; Aug-2024 −3.3; Dec-2024 −0.8; Apr-2025 −1.4; Mar-2026 +9.0; Jul-2026 +21.4. Cost episodes (not gated): 2009 rebound −6.9; 2020 rebound −15.5; H1-2026 −31.5; 30 Jul → 30 Sep 2026 −13.2 | — |
| G-KR-L12 | Tail and other metrics, 1997–2026 | ΔES99 +1.95 pp (z 4.3); ΔES95 of 21-day returns +2.9 pp (z 2.3); ΔCDaR95 +7.1 pp (z 1.26); bootstrap SD of ΔSR 0.066, 90% CI [−0.082, +0.131]; CVaR(5%) −2.64% vs −3.58% for S; mean multiplier on the worst 1% of days ÷ overall 0.54, on the 10 worst days 0.46; longest time under water 1,492 vs 1,478 sessions; median re-entry lag 17 sessions; PSR vs S 0.55; DSR vs 0: 0.99 / 0.81 / 0.63 at N 1 / 10 / 34 | — |
| G-KR-L13 | Variants of the definitive cell | Target 0.15 / 0.25: +16.5 / +8.9 pp, INSUFFICIENT / INSUFFICIENT. EWMA(0.94): +12.4 pp, p_ni 0.070, PC-4 0.51 → INSUFFICIENT. Cap 1.5 (prohibited): +20.5 pp → INSUFFICIENT. 0.10 band / monthly at 3 bp: +12.6 / +8.0 pp → INSUFFICIENT (PC-4). Own expanding-median target: −3.4 pp → REJECT (PC-1) | — |

**US vol target by instrument book** (DL-A, U1 = French Mkt-RF + ^GSPC Sep-2026; same columns):

| ID | Sample / book | Values | v1.2-check verdict |
|---|---|---|---|
| G-US-F01 | 1990–2026 daily, US shares via KIS 50 bp (the registered card) | +0.2 (−3.4) · 0.79 · −0.028 · 0.146 · 6/11 (0.49) · plateau 0.375 | REJECT (PC-1) |
| G-US-F02 | 1990–2026 daily, futures 5 bp (R-29) | +3.6 (+3.2) · 0.79 · +0.058 · 0.002 · 6/11 (0.46) · 0.875 | PASS |
| G-US-F03 | 1990–2026 daily, KRX S&P ETF proxy 3 bp (a cost bucket; FX, NAV lag and KST hours not modelled) | +3.8 (+3.6) · 0.79 · +0.062 · 0.002 · 6/11 (0.46) · 0.875 | PASS |
| G-US-F04 | 1990–2026 monthly, 50 / 5 / 3 bp | +7.6 / +9.3 / +9.4 · 0.81 · +0.045 / +0.078 / +0.079 · ≤ 0.002 · 8/11 (0.58 / 0.56 / 0.56) · 1.0 | INSUFFICIENT (PC-4, GFC) |
| G-US-F05 | 1990–2026 band 0.10, 50 / 5 / 3 bp | +1.8 / +3.7 / +3.8 · 0.81 · +0.017 / +0.059 / +0.061 · 0.023 / 0.002 / 0.002 | REJECT / PASS / PASS |
| G-US-F06 | 1995–2026 daily, 5 bp / 3 bp | +2.9 / +3.1 (2×: +2.9) · 0.78 · +0.058 / +0.063 · 0.007 | REJECT (PC-1) / REVISE (2×) |
| G-US-F07 | 1990–2007 / 2008–2026 daily, 5 bp | +0.3 (0 §8.6 episodes) / +17.5 | INSUFFICIENT (sufficiency) / PASS |
| G-US-F08 | Start sweep, 44 quarterly starts 1990-02 → 2000-11, futures 5 bp | 11 PASS (1990-02 to 1992-05, and 2000-11) / 9 REVISE (1992-08 to 1994-08) / 24 REJECT (1994-11 to 2000-08) | — |
| G-US-F09 | Expected-shortfall metrics, 1990–2026, 250-session blocks | Daily at 50 bp: ΔES99 +1.1 pp (z 2.37, P 1.00); ΔES95 of 21-day returns +1.7 pp (z 1.85, P 0.99); ΔCDaR95 −4.7 pp; ΔMDD bootstrap SD 7.8 pp. Daily at 5 bp: ΔES99 z 2.38; ΔES95 (21-day) z 2.05. Monthly at 5 bp: ΔMDD +9.3 pp (z 1.42); ΔCDaR95 +6.1 pp; ΔES99 z 1.86 | — |
| G-US-F10 | Estimator choice, 1995–2026 (DLB-T1h) | At 50 bp every estimator is REJECT or INSUFFICIENT (SMA20 ΔMDD −0.8 pp). At 5 bp: SMA20 +2.5 pp (REJECT); GARCH +4.9, log-HAR +4.8, COMB +3.9 pp (PASS) | — |

**G-REF-01: R-11 refusal record** (DL-A, KOSPI 1997-04 → 2026-10, 0.75× on VT20):

| Timing | Onsets (de-clustered at 20) | ETF 3 bp: ΔMDD / tail / ΔSR | Stock 35 bp: ΔMDD / ΔSR | Verdict |
|---|---|---|---|---|
| Value (DEXKOUS D ≤ K−1) | 74 | −1.7 / 0.996 / −0.015 | −1.7 / −0.048 | REJECT (PC-1, PC-2) |
| Strict H.10 | 54 | −1.3 / 1.004 / −0.022 | −1.4 / −0.036 | REJECT |
| Strict H.10, holiday-aware | 54 | −1.3 / 1.004 / −0.027 | −1.5 / −0.041 | REJECT |
| Yahoo KRW=X lagged 2 sessions (2004+) | 69 | +0.3 / 0.996 / −0.006 | −0.4 / −0.059 | REJECT |

**G-REF-02: R-12 refusal record** (DL-A, US 1990-02 → 2026-09, 0.5× on VT15; 71 onsets at every timing, 39 in 1990–2007 and 32 in 2008–26):

| Timing | Status | 50 bp: ΔMDD / ΔSR | 5 bp: ΔMDD / ΔSR | Gross: ΔMDD / ΔSR | Tail | Verdict |
|---|---|---|---|---|---|---|
| Value (DGS10(D) at the close of D) | NON-COMPLIANT | −0.8 / −0.076 | +1.1 / +0.026 | +1.2 / +0.037 | 0.99 | REJECT |
| +1 business day via Treasury | COMPLIANT via Treasury | −3.1 / −0.105 | +0.1 / −0.002 | +0.3 / +0.009 | 0.99 | REJECT (also PC-4 2/11) |
| +2 business days, strict H.15 | COMPLIANT | −3.5 / −0.120 | +0.8 / −0.019 | +0.9 / −0.007 | 0.995 | REJECT |
| ^TNX close of D (live proxy) | VALUE | −1.5 / −0.090 | +1.4 / +0.016 | +1.5 / +0.027 | 0.99 | REJECT |

**Drawdown ladder** (DL-A, `QX_DLA_ladder.csv`; KOSPI 3 bp from 1997-04-15; US at 5 bp from 1990-04-02):

| ID | Case | Values |
|---|---|---|
| G-LAD-01 | Literal v1.2 rule (the I-04b counter-example) | KOSPI, buy-and-hold or VT20: permanently HALTED from 1997-10-17 under the cumulative reading (average exposure 1.3%; 714 halt cycles), from 1997-09-30 under the non-cumulative one (1.3%; 715 cycles). US, buy-and-hold or VT15: from 2000-10-13 (20–22%; 653 cycles) / from 1990-09-25 or -28 (1.1%; 907 cycles) |
| G-LAD-02 | QF4's fix with an 11-session halt (reference only; v2 adds the 10-session refusal, the 0.5× cooling-off and the 21-session time-box) | KOSPI VT20: Sharpe 0.532, max DD −42.0%, days reduced 52%, 16 HALTs, ΔSR vs no ladder +0.078, ΔMDD vs S +3.9 pp. KOSPI buy-and-hold: 0.453, −50.9%, 52%, 31, +0.025, +0.4 pp. US VT15: 0.522, −42.5%, 29%, 8, −0.066, +5.7 pp. US buy-and-hold: 0.523, −51.2%, 23%, 17, −0.008, +2.0 pp |
| G-LAD-03 | Sensitivity to unspecified details (reference only) | The 0.5× cooling-off clause moves US VT15 to 0.538 / −37.8%. A 10-session halt instead of 11 moves the KOSPI buy-and-hold cumulative Sharpe from 0.553 to 0.595 |

**G-STALE-01: staleness** (DLA-S1, decisions 2016-01-04 → 2026-09-25; T-STALE-01):

| Series | Decision | Stale under "1 trading day" | Stale under "3 days" | Schedule-aware | Median / max age (days) |
|---|---|---|---|---|---|
| DTWEXBGS (H.10) | US close / KRX close | 100.0% / 98.6% | 100% / 100% | 0.89% / 0.80% | 6 / 12 |
| DEXKOUS (H.10) | US close / KRX close | 100.0% / 98.6% | 100% / 100% | 0.52% / 0.42% | 6 / 12 |
| DGS10 (strict H.15) | US close / KRX close | 99.52% / 95.9% | 42.0% / 42.4% | 0.33% / 0.34% | 2 / 5 |
| VIXCLS (16:15 ET) | US close / KRX close | 0.0% / 2.1% | 1.9% / 2.0% | 0% / 0% | 1 / 4 |

**Volatility estimators** (DL-B; KOSPI ^KS11 from 1996-12, out of sample from 2001-01-02, 6,342 origins; US ^GSPC from 1990, out of sample from 1995-01-03, 7,985 origins; target Σ r² over the next h days; refit every 21 origins on an expanding window):

**G-EST-01: QLIKE relative to SMA20**, with the MCS p-value in brackets (T_max; stationary bootstrap, mean block max(10, 2h); B 2,000):

| Model | KOSPI h1 | h5 | h21 | US h1 | h5 | h21 |
|---|---|---|---|---|---|---|
| SMA20 | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.000) | 1.000 (0.0005) |
| EWMA 0.94 | 0.966 (0.002) | 0.867 (0.075) | 0.749 (0.462) | 0.965 (0.000) | 0.870 (0.000) | 0.814 (0.002) |
| EWMA 0.97 | 0.976 (0.001) | 0.895 (0.016) | 0.742 (0.692) | 0.980 (0.000) | 0.907 (0.000) | 0.828 (0.017) |
| GARCH(1,1)-t | 0.957 (0.002) | 0.837 (0.185) | 0.683 (1.000) | 0.949 (0.000) | 0.809 (0.000) | 0.670 (0.657) |
| GJR-t | 0.952 (0.032) | 0.841 (0.185) | 0.718 (0.692) | 0.926 (0.081) | 0.757 (0.105) | 0.652 (0.668) |
| log-HAR-range | 0.947 (0.142) | 0.818 (0.185) | 0.715 (0.692) | 0.921 (0.081) | 0.744 (0.105) | 0.695 (0.657) |
| COMB | 0.944 (1.000) | 0.809 (1.000) | 0.691 (0.692) | 0.916 (1.000) | 0.723 (1.000) | 0.642 (1.000) |

**G-EST-02: MSE MCS p for SMA20.** KOSPI 0.036 / 0.066 / 0.141; US 0.112 / 0.112 / 0.290. The QLIKE dominance is loss-specific.

**G-EST-03: calibration lines.**
- B5 (SPEC definition): KOSPI 4.70% of 2,594 (PIT p 0.107); SPY 4.99% (0.566); US 5.31% of 8,961 (0.976). EWMA 4.90% / 5.22% / 5.31%.
- B5 passes 7 of 9 KOSPI forecasters and 8–9 of 9 US forecasters. Log-HAR-range narrowly fails KOSPI 1-day B5 (5.58% vs the band's upper bound 5.56%).
- Christoffersen independence, KOSPI 2001–26: SMA20 < 0.0001, EWMA94 0.0007, EWMA97 < 0.0001, GARCH-t 0.026, GJR-t 0.032, log-HAR-range 0.16, COMB 0.17. SMA20 on 2016–26: 0.0006. No US model fails.
- The h = 1 HAR result depends on the design: the range target gives 0.947 / 0.921 × SMA20 (KOSPI / US); QF6's log-r² design gives 1.390 / 1.242.

**G-EST-04: sizing books** (KOSPI 2001–26, 3 bp; σ̂ from each model's 21-day forecast; target 20%; cap 1):

| Book | Sharpe | Max DD | Turnover/yr | Vol-of-vol | ΔSR vs SMA20 [90% CI] | ΔMDD vs SMA20 |
|---|---|---|---|---|---|---|
| Buy and hold | 0.563 | −54.5% | 0 | 0.111 | — | — |
| SMA20 | 0.571 | −40.0% | 2.25 | 0.0446 | — | — |
| EWMA 0.94 | 0.547 | −42.1% | 1.92 | 0.0425 (−4.7%) | −0.024 [−0.053, +0.005] | −2.1 pp |
| GARCH-t | 0.550 | −40.5% | 2.49 | 0.0375 (−16.0%) | −0.022 [−0.054, +0.011] | −0.5 pp |
| GJR-t | 0.556 | −40.5% | 2.54 | 0.0373 (−16.4%) | −0.016 [−0.053, +0.020] | −0.6 pp |
| log-HAR-range | 0.578 | −35.0% | 5.28 | 0.0338 (−24.2%) | +0.006 [−0.045, +0.056] | +5.0 pp |
| COMB | 0.571 | −37.2% | 3.48 | 0.0347 (−22.2%) | −0.000 [−0.042, +0.039] | +2.8 pp |

On 2016–26 the gains halve: vol-of-vol −9% to −12%, ΔMDD +1.6 to +2.1 pp. At 35 bp, log-HAR costs ΔSR −0.063 (CI −0.114 to −0.013) and COMB −0.030.

**R-03 statistics** (DL-B, `QX_DLB_r03_dsr.csv`, `QX_DLB_r03_years.csv`):
- **G-DSR-01:** DL-B's DSR code reproduces Bailey–López de Prado's example: 0.9505 at N 46; 0.9004 at N 100 (T-DSR-01).
- **G-DSR-02:** R-03 net of 50 bp on both legs: SR 0.6723, T 9,233, skew −0.687, kurtosis 6.948; ΔSR vs unscaled +0.2729, HAC SE 0.0716 (NW-250 0.093).
  - DSR vs 0 with V_trials / V_null: 0.886 / 0.984 at N 12; 0.668 / 0.947 at N 34.
  - At BLdP eq. 9 N̂ = ρ̂ + (1 − ρ̂)M = 12.5 (differences, M 26, DL-B's ρ̂; PX1's ρ̄ 0.535 gives 12.6, the value R-03 and T-NEFF-01 quote, within T-NEFF-01's ± 0.1): DSR 0.880 / 0.983, deflated ΔSR 0.947.
  - At M 34 (N̂ 16.2): deflated ΔSR 0.927.
  - The N_equiv values (6.3 → 0.98; R-04 0.77) are tested by T-NEFF-01.
- **G-YRS-01:** cap 1, 1990–2026, 37 calendar years.
  - Per-year Sharpe higher than static: 15/37 = 40.5% gross, with 17 identical years. Excluding those: 15/20 = 75% gross, 11/20 = 55% net.
  - Own return > 0 (step 8): 73.0% gross, 70.3% net.
  - Cap 2: per-year higher Sharpe 73.0% (net 43.2%). Log return above the vol-matched static book: 86.5% (cap 2) and 78.4% (cap 1).

**Trend axis** (DL-B, `QX_DLB_trend_cards.csv`; R-28 and §10):

| ID | Case | Values |
|---|---|---|
| G-TR-01 | US monthly 1927–2026, SMA10m 0.5×, cash = RF | 5 bp: ΔSR +0.083 [0.019, 0.134], p_ni 0.000, ΔMDD +15.9 pp (2×: +15.9), tail 0.78, 9/10 episodes (max 0.21), years 68%, onsets 73 raw / 45 de-clustered, plateau 1.0 → PASS. 50 bp: ΔSR +0.059 [−0.007, 0.113], ΔMDD +15.8 (+15.6) pp, 9/10 (0.22) → PASS. Cash 0: +0.078 / +15.2 pp (5 bp) and +0.055 / +15.0 (+14.8) pp (50 bp) → PASS |
| G-TR-02 | Start dates (5 bp) | Starts 1930 / 1940 / 1950 / 1960: ΔSR +0.081 / +0.052 / +0.063 / +0.058; ΔMDD +21.4 / +15.3 / +15.5 / +15.2 pp → PASS. Starts 1970 / 1980 / 1990 / 2000 / 2008: ΔMDD +15.3 / +15.8 / +15.8 / +15.2 / +16.2 pp, onsets 27 / 22 / 17 / 13 / 10 → INSUFFICIENT (sufficiency) |
| G-TR-03 | Snooping haircut, 94 variants (SMA 2–24 m, TS 1–24 m, 0.5× and 0×; eq. 9 N̂ 30.7) | 94/94 variants ΔMDD ≥ 3 pp (median +16.4 pp); SMA10 ranks 33rd on ΔSR and 51st on ΔMDD; deflated ΔSR probability 0.99 (N 1), 0.59 (N̂ 30.7), 0.43 (N 94), 0.07 (N 7,846) |
| G-TR-04 | Other indices (price, cash 0, 5 bp), ΔMDD vs S | S&P +17.5, Nikkei +4.2, HSI +8.0, DAX +14.0, FTSE +7.4, TAIEX +12.0, KOSDAQ +9.8 pp; each index alone has 15–21 de-clustered onsets |
| G-TR-05 | KOSPI daily 1998–2026, 3 bp (no Korea instance; context only) | Cash 0: ΔSR +0.070, ΔMDD +3.6 pp; tail 0.929 daily / 0.853 at 21 days; 17 de-clustered onsets → INSUFFICIENT. From 2016: −2.3 pp (tail 1.02) |

**Gate power** (DL-B, `QX_DLB_power_se.csv`, `QX_DLB_power_sim.csv`):

| ID | Case | Values |
|---|---|---|
| G-PWR-01 | SE(ΔSR) of vol-target cards vs S | US VT15, 50 bp, 1990–2026: NW10 0.061 (QS 0.0605; bootstrap 0.060–0.061; ρ 0.920) → 241–246 years for +0.05 at 80% power. KOSPI VT20, 3 bp, 2016–26: NW10 0.132 (QS 0.130) → 319–330 years. KOSPI VT20, 1997–2026: NW10 0.075 → 295–311 years. MDE80 0.128 (US) / 0.276 (KOSPI) |
| G-PWR-02 | P(REJECT) when the true ΔSR vs S is 0 (300 paths per cell): QF3's definition · the SPEC's order · P(PC-1 at 1×) | Resampling, US VT15 50 bp: 0.69 · 0.58 · 0.44 (11 y); 0.61 · 0.45 · 0.55 (36 y); 0.62 · 0.43 · 0.57 (100 y). Resampling, KOSPI VT20 3 bp: 0.55 · 0.54 · 0.57; 0.63 · 0.63 · 0.41; 0.73 · 0.72 · 0.28. GJR-t, US: 0.72 · 0.67 · 0.43; 0.64 · 0.52 · 0.56; 0.46 · 0.28 · 0.74. GJR-t, KOSPI: 0.57 · 0.57 · 0.57; 0.27 · 0.26 · 0.81; 0.14 · 0.14 · 0.88 |

**R-08 VIX ≥ VIX3M** (DL-B, `QX_DLB_r08.csv`; FRED 2007-12-04 → 2026-09-30):

| ID | Case | Values |
|---|---|---|
| G-R08-01 | Flag anatomy (raw parity flag; T-ANNOT-01) | 4,735 days; 10.1% flagged; 132 spells; 50.8% one-day; 15.9% ≥ 5 days; 14.0 transitions a year; de-clustered onsets 64 / 40 / 24 at 20 / 60 / 126 sessions. 5-close clearing: 72 spells, median 8 days |
| G-R08-02 | Block as a CARD-P (record only) | ΔMDD vs S, raw flag / 5-close clearing: US VT15 at 50 / 5 bp +0.9 / +0.6 pp and +1.3 / +0.6 pp; KOSPI VT20 at 3 / 35 bp +0.3 / +0.4 pp and −0.1 / +0.1 pp; US momentum +0.0 / −0.0 pp. Tail ratio 0.996–0.999. REJECT in 10 of 10 cells |

#### 9.3.3 v1.2-check mode and reference mode (reproduction only; never a verdict)

**v1.2-check mode.** The §9.3.1 goldens and the "v1.2 checks" columns of §9.3.2 are reproduced with the v1.2 protective checks of `.v1.2_INTEGRATION_backup.md` §8.7, never with the v2 package:
- PC-1: MDD(rule) − MDD(S) ≥ +3.0 pp at 1× **and** 2× costs, and MDD(rule) better than MDD(overlay-off);
- PC-2: the tail-exposure ratio ≤ 0.90;
- PC-3: margin δ = 0.10, one-sided percentile bootstrap p of {ΔSR* ≤ −δ} (circular blocks, R4b's `gate_boot`) ≤ 0.10, with p_ni = max(p at 10-session blocks, p at max(10, PW(d), PW(d²))-session blocks) as the R4b and DL-A goldens report it (G-KR-L01: 0.052 / 0.029 at PW block 183), 2,000 resamples, seed 11, Bonferroni × the configurations searched as recorded in each golden's source row (G-KR-L01's PASS at 0.052 implies a factor of 1); the point ΔSR ≥ −δ also at 2×;
- PC-4: on the §8.6 drawdown windows, ≥ 3 with a positive benefit vs S and none above 50% of the summed positive benefit;
- PC-5: ≥ 60% of calendar years positive; PC-6: ≥ 50% of the neighbouring cells (8 neighbours, one step on each declared axis) keep ≥ half of the centre's PC-1 improvement and the PC-3 point; PC-7: ≥ 30 de-clustered onsets for discrete rules, ≥ 5 §8.6 windows, ≥ 756 + 126 sessions;
- raw returns with cash at 0 (for T-EXCESS-01 and I-09 only, PX2's excess-return cash fixture instead: FRED `IRSTCI01KRM156N`, monthly, ÷ 252, used from the month after), and the v1.2 verdict order (sufficiency, REJECT, inconclusive, REVISE, PASS).

**Reference mode.** `core/quant/backtest` may compute configurations the rules store refuses (a cap above 1, the DM gate at 0×, product stacks, the literal v1.2 ladder) only when called from `tests/reference/` or `docs/` with `reference_only=True`; `core/` cannot import that code. Such results never enter a book, a card or an artifact, and T-CAP-01 and T-DNB-01 apply to the rules store and the books, not to this mode. The goldens marked `reference_only` are G-KR-06, G-MOM-07, the cap-1.5 variant of G-KR-L13, G-LAD-01 (the literal ladder: the cumulative and the non-cumulative readings), G-LAD-02 (QF4's 11-session halt) and G-LAD-03. "Never re-run" (R-06 US) means that no new card record is written; a reference reproduction such as G-US-F01 is not a card run.

### 9.4 Pending recomputations (not golden values yet)

These are listed so that no number is invented in their place. Each becomes a golden value, md5-frozen, when its run is done. Items 15–17 are open implementation tasks from adversarial round 3, not recomputations; each closes when its milestone's code does it.

1. **Excess-return restatement.** Every regression golden of §9.3.1 restated under the excess-return convention (R-22). Only one Korea value exists so far: p_ni 0.078 with call-rate cash (PX2's monthly cash fixture; T-EXCESS-01 and I-09 reproduce it in v1.2-check mode, and the frozen-convention value is item 14).
2. **Official-close reruns of values DL-A did not recompute after the 2-Oct patch:** cap-1.5 VT Sharpe 0.534 (G-KR-06), SMA60 0.550, EWMA (half-life 10) 0.607, EWMA at 35 bp 0.573, and the Korea stock-book 2× ΔSR −0.061. They stay labelled pre-patch R4/R4b until then.
3. **The R-29 settling run** on French daily Mkt-RF 1926-07 → 2026-08 at 5 bp. DL-A could not fetch the file (HTTP 403).
4. **The Korea card's ES126 z.** ES126 is +6.4 pp in PX1's horizon file, but its z has not been computed.
5. **The formal R-06 KR card** on KRX official closes (I-16), and every formal card under the frozen v2 package.
6. **The event-conditional variance test** for the opening-gap flag (QF7-A28), and the 2027–28 out-of-sample post-holiday VaR breach check (R-10).
7. **Bootstraps for the §10 E labels.** The book-level variant behind every §10 item labelled on basis E, bootstrapped as `qf3_dnb_classes.py` does (63-day blocks, 1,000 resamples). Each result replaces the item's E label with a B label.
8. **The R-31 reference run** with separate `hwm_hard` and `ref_step` references (T-STEP-03, I-15); EX1 L5 used one shared reference.
9. **I-04b's KOSPI VT20 1997–2026 HALT count** under the v2 rule (automatic RISK re-arm; Check C2 printed 24 under its re-arm).
10. **G-LAD-04**: the invariants-only recommended KOSPI book (ETF line, caps), with and without the −15% hard stop: HALT count, MDD and Sharpe, printed beside D2 (§8.10).
11. **T-POWER-01's years line** restated to a point (T_years = sessions ⁄ 252, SE = SE_plateau of the named fixture; G-PWR-01 gives 241–246 ⁄ 319–330).
12. **The R-06 KR selection factor.** The R-06 family ledger seeded from the research phase (§9.5) and f computed under `any_overlap` for every defensible row-set reading, the maximum binding (R-23; R2-C1); the acceptance report prints each reading's f before any card runs, and §8.9's f sensitivity then becomes a computed value.
13. **M1 measurements:** the KODEX 200 basket's publication instant, the NYSE print bound (default 30 s) from logged print times, and FRED's VIX posting lag (`last_updated`, logged for 20 sessions).
14. **Frozen-package values of the research-script goldens (R2-C7):** the excess-return cell of T-EXCESS-01 and I-09 under R-22's cash and R-24's studentized PC-3; T-GATE-02's p_ni and T-ES-02's z under R-21's stationary bootstrap. Each is computed at its first run, printed beside the research value and md5-frozen, and never asserted against the research number.
15. **Open implementation task (M7, before the freeze): anchored timestamps.** The `gate.step3.spec_versions` publication instants and every seed row's `run_utc` cite a git commit or an external anchor, never a hand-entered time, because they decide the f = 1 route (R-23).
16. **Open implementation task (M7): archive each formal card's snapshot.** The rows behind each formal card's `data_snapshot_id` are archived with the card and md5-listed, because `verdict_filter`'s check (iii) re-derives the snapshot from the store (R-35); a store migration that lost them would drop every admission at once and step exposure up to the invariants-only level.
17. **Open implementation task (M8): atomic `engine_feed` per book.** Each book's weights for a decision are delivered all or none; an interrupted delivery leaves the book on its previous weights (§3.9).

### 9.5 Fixture manifest and data-acquisition register

**Fixture manifest** (`tests/fixtures/macro/MANIFEST.csv`, **proposed**). One row per file: file, source (a path under `/home/claude/quantgen_macro_data/`, per its `CATALOG.md`, or under `research_notes/…/council/`), series, span, `retrieved_at_utc`, the `value_status` and `available_at_source` rule, md5, and the tests that read it. It lists every file: KRX official closes, the ECOS call rate, the KODEX 200 PDF and constituents, iNAV, the 15:19 snapshots, daily opens, VIXCLS / VXVCLS, SOX, the six trend indices, the French files (daily and monthly; the 1926+ daily file when acquired), the Yahoo ^KS11, ^GSPC, SPY, KRW=X, ^TNX and ^RUT files, the FRED snapshot of 2026-10-02, PX2's excess-return cash fixture (FRED `IRSTCI01KRM156N`, monthly, read by T-EXCESS-01 and I-09; produced by `scripts/qx_px2_02_vt_assetpricing.py`), `QX_DLA_postpatch.csv`, `QX_DLA_korea_grid.csv`, `QX_EX1_qf3_trial_corr_diff.csv`, the DLB CSVs, the source-skipped list, and the synthetic store fixture of T-PROV-01. Historical close-type vendor rows carry `available_at_source = calendar_bound`. Every stochastic golden names its seed, B and block rule.

**Research-phase ledger seeds.** Each family ledger starts from its research-phase rows, frozen with the fixtures: R-03's 26 trials; R-06's rows, enumerated one per distinct configuration in `tests/fixtures/macro/ledger_seed_R-06.csv` (row id, source file and row, market, span, run_utc, params, timing class, book, cost, results md5, stored difference series): every configuration whose Korean-data result was seen before the v2 freeze (R4's and R4b's comparisons, among them the window and cap comparisons on 2016–26 that make R-06 KR's f exceed 1; the DL-A Korea grid; the QF, QX and DL variants) and the family's other-market rows for the family-wide reading (the US VT15 rows DLA-U1–U5, DLB-T1h); R-28's 94 DLB-T3f variants; R-31's EX1 L1–L6 ladders. Every family's seed is enumerated the same way, one row per configuration, and every seed file and series is md5-listed in the `definitions_md5` manifest; a seed row whose series is missing is regenerated by the harness from its config before the freeze (R2-C1).

**Data-acquisition register** (series · source · depth · licence · milestone · owner · md5):

| Series | Source | Depth | Needed by |
|---|---|---|---|
| KRX official KOSPI daily closes, Saturday sessions included | KRX marketplace | from 1997-01-03 | M1 (I-16 at M7) |
| KODEX 200 PDF history | KIS or KRX | as available | M5 |
| French daily Mkt-RF and RF | French Data Library (DL-A: HTTP 403) | from 1926-07 | M8 (R-29 settling run) |
| The ECOS code of `BOK_CALL_RATE` | BoK ECOS | from 1997 | before the M7 freeze |
| `USD_LIVE_PROXY` (named, default `DX-Y.NYB`) | registry | — | M2 |
| The 16:00 ET VIX / VIX3M snapshot source | vendor or KIS | — | M6 |
| The hyperscaler list | company IR | — | M5 |
| JPX, SSE, HKEX, TWSE, CME and Cboe calendars | official notices | effective-dated | M1 |

Licence, owner and md5 columns are filled when each file is acquired; a file without them is not a fixture.

---

## 10. DO-NOT-BUILD list v2

Never implement any of these unless a new model card passes the gate (§8) with new evidence. Each item names its node and the evidence against it. "One-sided" means refuted by one panel plus the data, with the other panel silent.

**v2.0 (R-33; QC resolutions 3 and 10; QCE-136).**
- Items 1–26 keep their v1.2 numbers, because other sections cite them. Item 11 is split (ML vol-state classifiers stay prohibited; range-based HAR is admitted). Items 17, 19 and 22–25 gain v2.0 notes.
- Items 27–37 are new. Seven come from the council's modules (R-33); four restate binding red lines and resolutions that other modules also enforce.
- Every item carries a label (§10.1). Rules-store validation refuses every listed shape (§10.3, T-DNB-01).

### 10.1 Labels: harm, null or inconclusive (QF3-A17)

The list stands on the burden of proof. An idea is listed because it failed to show a benefit at QUANTGEN's timing and cost, not because each item was shown to do harm; "refuted every flagship rule" overstated the record. Each item, or each variant where they differ, carries one label and the basis for it.

| Label | Meaning |
|---|---|
| `harm` | Building it makes things worse: the book-level ΔSR 90% bootstrap interval lies below 0 (basis B); or every estimate the item cites at implementable timing and cost is negative, in more than one sample or sub-period (E); or it breaks a non-negotiable (G) |
| `null` | No material effect: the interval lies within ±0.10 (B); or the item's cited conditional outcome, fit or incremental effect is nil at the precision cited (E) |
| `inconclusive` | Neither: the interval straddles 0 and is wider than ±0.10 (B); or the evidence is a single estimate, a single episode or path (P12), mixed in sign, one-sided or untested (E) |

| Basis | Source and rule |
|---|---|
| **B** | QF3's 53 bootstrapped variants (`qf3_dnb_classes.py` → `results/QF3_dnb_evidence_classes.csv`; 63-day blocks, 1,000 resamples; 7 harm, 12 null, 28 inconclusive, 6 benefit), or the bootstrap share of positive ΔSR draws cited with the item (a share below 0.05 means the 90% interval lies below 0). The item's book-level variant decides; other legs are noted. |
| **E** | The item's own cited evidence, under the thresholds above. An E label is provisional and weaker than a B label. It is replaced when the item's variant is bootstrapped (§9.4). |
| **G** | Governance: the item breaks one of P0–P19 or a council red line. The harm is to the programme's safety or to the validity of the gate, whatever the item's Sharpe. |

**How to read a label.**
- QF3 classified test variants, not these items (QC errata notes). The mapping below is this specification's, made with the rule above.
- A label never lifts a prohibition. An `inconclusive` item reopens only through a new card with new evidence (§8), like any other.
- A G item reopens only if the principle it breaks is changed. That is an owner decision, never a card result.
- Two benefit-class variants sit behind listed items:
  - the four-state de-risk-only variant (+0.10, 90% CI [0.034, 0.164]) survives BH but not BY, and is recorded `inconclusive` (item 1);
  - the KRW-only 0.5× gate on KOSPI (+0.071 [0.012, 0.139]) reads DEXKOUS by data date, before H.10 publishes it. At strict H.10 publication the leg earns +0.001 (R4b), and R-11 is retired to a refusal book (item 22).

### 10.2 The list

**Overlay design**

1. `inconclusive · B` **The prior four-state trend × stress classifier and its multiplier table** (N-03). Book −0.07 (share 0.23). It held momentum at 1.425× into Nov-2020 (−12.0%) and 1.50× into Jul-2026 (−10.9%). *Label:* BOOK ΔSR −0.073, 90% CI [−0.252, +0.093]: unsupported, not refuted. Its reversal leg is `harm` (−0.199 [−0.338, −0.046]; item 2).
2. `harm · B` **Any multiplier above 1.0.** This includes momentum 1.5× in "risk-on", reversal 1.5× or 2×, quality / low-vol / min-vol 1.5×, Korea gross 1.5×, flow ×1.5, AAII-reversal ×1.25, and vol-target caps above 1 (N-03, N-02). Reversal 1.5×: −0.05 to −0.20. RMW 1.5×: −0.01. KOSPI vol target with cap 1.5: Sharpe 0.534 vs 0.638 (R4, 2016–26). Long samples agree: cap 1.0 → 1.5 → 2.0 gives KOSPI 1997–2026 0.454 → 0.430 → 0.403 and US 1990–2026 0.588 → 0.569 → 0.545, with deeper drawdowns, before any financing cost. *Label:* the bootstrapped reversal 1.5× legs lie below 0 (four-state −0.199 [−0.338, −0.046]; VIX-TS proxy −0.090 [−0.159, −0.007]), and every cap above 1 loses Sharpe in every sample cited. It also breaks P2 (G); cap 1.0 is permanent (R-06).
3. `inconclusive · B` **A VIX-term-structure switch for momentum (0× or halved) or for reversal (1.5×), and the post-stress-clear 0.5× momentum schedule** (N-05). −0.15 in 2020–26 (share 0.05); −0.19 on top of vol scaling; schedule −0.158. *Label:* momentum ΔSR +0.012 [−0.105, +0.129], BOOK +0.004 [−0.138, +0.125]: unsupported, not refuted. The reversal 1.5× leg is `harm` and falls under item 2.
4. `harm · E` **Cut-and-re-add gates on existing exposure** (desk "boundary behaviour") (N-04). −0.088 Sharpe; −0.185 in 2020–26. *Label:* negative over the full sample and in 2020–26; no interval computed.

**Korea gates**

5. `inconclusive · B` **Korea gates built from US or global inputs** (N-18):
   - the SOX 60-day trend × USD/KRW 20-day gate;
   - the SOX trend gate;
   - the AI-hardware gate;
   - the US stress row applied to KOSPI;
   - the two-speed and residual KRW gates, dollar "regime B", and the three-way KRW conjunction.
   
   Evidence: +0.31 only with look-ahead, +0.05 implementable, −0.16 in 2024–26. SOX leg −0.22. The AI-hardware gate was on through the crash and off at the trough. US stress row on KOSPI −0.15. *Label:* on buy-and-hold KOSPI at implementable timing (2016+): the prior-document gate +0.047 [−0.119, +0.230]; SOX-only 0.5× −0.021 [−0.162, +0.122]; both legs together, 0× +0.009 [−0.081, +0.104]. The +0.31 needs US-session data that KOSPI's close cannot see (item 19).

**Macro gates on factors or gross**

6. **Macro-variable factor or gross gates** (N-11, N-12), labelled by variant (bootstrapped on BOOK where available). These include:
   - `harm · B` curve re-steepening, and bull or bear steepener rules (−0.089 [−0.157, −0.024]; the 252-day variant −0.062 [−0.120, −0.010]);
   - `null · B` a real-rate level state, or a 63-day real-rate gate on momentum (the bootstrapped real-rate gate −0.027 [−0.066, +0.012]);
   - `inconclusive · B` credit-triggered factor weights (momentum 0.5×, quality 1.5×) (+0.055 [−0.007, +0.117]; the quality 1.5× leg is also item 2);
   - `inconclusive · E` momentum 0.5× under rates stress (one estimate);
   - `inconclusive · E` level thresholds (10y > 5.25%, the MOVE variant) (one estimate).
   
   Evidence: −0.09 (share 0.00); −0.04; −0.05 (2020–26); −0.065; −0.032.
7. `null · E` **A lagged oil-price gate on equity or KOSPI gross** (Brent +30% over 63 days, or 20-day > +25%) (N-43). Across 22 episodes, forward 63-day returns were 2.67% vs 2.66% unconditional. The gate first fired after the −12.06% day. *Label:* the conditional return equals the unconditional one.
8. `inconclusive · B` **Net-liquidity (WALCL − TGA − RRP) or M2 rules for crypto or equities** (N-55). −0.01; −0.20 in 2023–26. BTC fell 53% while net liquidity rose $41bn. *Label:* on BTC, the symmetric 1.5/0.5 rule −0.008 [−0.254, +0.236] and the de-risk-only rule +0.023 [−0.149, +0.191]. The symmetric form also breaks item 2.

**Forecasts, surveys and macro models**

9. **Street point forecasts, house views, recession odds and target dispersion as inputs**; FMS, Bull & Bear, AAII and COT timing rules; post-trigger crowding cuts; consensus-surprise entries at retail latency (N-56). Labelled by variant:
   - `inconclusive · E` forecasts, house views, surveys and positioning timing rules: S&P consensus abs error 17.13%; 2026 forecasts called for cuts against an actual hike; FMS Aug-2026 published after KOSPI's −25.4% fall. These are forecast errors and late publication, with no overlay test;
   - `inconclusive · E` post-trigger crowding cuts: in Aug-2024 momentum lost −5.9% before the crowding trigger and gained +6.5% after it (one episode);
   - `null · E` consensus-surprise entries at retail latency: surprises are priced within ≈ 5 ms, so nothing is left at retail latency.
10. `inconclusive · E` **Sahm, curve, probit or growth × inflation-quadrant gates**; fixed-coefficient Okun, Phillips, sacrifice-ratio or M2 → CPI relations (N-30; N-31 one-sided).
    - 26 months without recession after the Sahm trigger.
    - 534-day inversion.
    - Okun β −0.407 → −0.05.
    - Phillips OOS RMSE 2.15 vs 1.79.
    
    *Label:* false alarms and drifting coefficients, with no overlay test.
11. **Methodological shortcuts** (N-49, one-sided). Split in v2.0 (QF3-A23, QF6-A3, QF3-M6, QF7-A5; QC resolution 3):
    - **11a.** `harm · E` **ML vol-state classifiers stay prohibited:** elastic-net, gradient-boosting or any other ML classifier of the next-month volatility state, as a sizing, gating or display input. The 2-parameter EWMA rule wins on Brier: KOSPI 2009–26 0.0387 vs 0.0571 (elastic net) and 0.0755 (GBM), DM t −2.55 / −3.64 on log loss. With the nested feature log(EWMA/q80) the elastic net improves to 0.0558 and still loses (DM −2.52). GBM is worse than climatology on KOSPI (Brier skill −0.27). At 50 bp on the S&P, de-risking by the classifiers costs ΔSR −0.093 (elastic net) and −0.131 (GBM), against −0.014 for the EWMA rule. *Label:* every cited forecast comparison and every cited economic estimate is at or below the incumbent rule. The result is archived as a negative result (item 29).
    - **11b. Admitted, not prohibited: range-based log-HAR.** v1.2's "no HAR until intraday realised variance" is struck. Log-HAR on daily ranges (range-target design; an overnight leg for KOSPI; Parkinson for the US, whose index open is unreliable before about 2008) joins the R-30 estimator race at the 21-day sizing horizon. A 1-day VaR display comes only from a model that passes 1-day B5; log-HAR-range narrowly misses it on KOSPI (5.58% vs 5.56%). The 1-day HAR failure was the log-r² design: the range target gives 0.947 / 0.921 × SMA20 at h = 1 (DLB-T1d). COMB = ½(GJR-t + log-HAR-range) is the registered challenger for ETF and futures books (R-30). Intraday realised variance is an upgrade, not a prerequisite.
    - **11c.** The other shortcuts stay prohibited, labelled by variant:
      - `harm · G` smoothed regime probabilities (P5: look-ahead; the smoothed path's Sharpe 1.518 uses future data);
      - `harm · E` unpenalised daily HMM / Markov-switching gates (the spec-compliant switch earns Sharpe 0.285 at 50 bp vs 0.539 for buy-and-hold; ΔSR −0.244 at 50 bp in DLB-T4a; item 27);
      - `null · E` "complexity" / random-feature macro ML timing (forecasts correlate 0.93 with Nagel's kernel forecasts; alpha t −0.12 after the kernel strategy);
      - `harm · G` LLM or text signals backtested over periods before the model's training cutoff (P5: look-ahead by construction).
    
    Evidence: real-time US Markov switching changes state 16.9 times a year, and 49% of its episodes have no overlap with the same model's smoothed path (against ex-post ≥ 10% drawdowns, 78% of real-time and 68% of smoothed flags are false). The spec-compliant 0.5/1 switch earns Sharpe 0.554 vs 0.539 buy-and-hold net of 10 bp (0/1: 0.390; smoothed 1.518 is look-ahead), but 0.285 at QUANTGEN's 50 bp (8.3 units of turnover a year). Complexity timing: RFF forecasts correlate 0.93 with Nagel's kernel forecasts; RFF alpha t −0.12 after the kernel strategy.
    
    **Jump models are not a failed class (QF7-A5).** Unpenalised Markov switching failed. The jump model (SJM, λ = 50) is a research item with a pre-registered 2027–28 settling test in the backlog (QC resolution 10). In v2 no regime state acts or is displayed (item 27).

**Events, calendars and data**

12. **24-hour pre-event blackouts; swing-book blackouts around FOMC, CPI, NFP, BoK or export prints; a KRX quad-witching blackout; the index expiry-close fade** (N-38, N-58). Labelled by variant:
    - `inconclusive · E` the 24-hour and swing-book blackouts: a 24 h FOMC blackout covers the whole preceding KRX session (a design cost, not an estimate);
    - `null · E` the quad-witching blackout: quad witching t −0.38;
    - `inconclusive · E` the expiry-close fade: the day after expiry continues rather than reverses (correlation +0.33; one sample).
13. `inconclusive · E` **Calendar and supply-timing tilts** (N-58, one-sided): quarter-end tilts, KRW April seasonality, export-print tilts, aggregate issuance or IPO-window multipliers, buyback-blackout multipliers, Korean issuance volume as sentiment.
    - April KRW t −0.64; quarter-end fade t −1.26; detrended IPO counts t −0.3 to −1.4; buyback blackouts t −0.26.
    
    *Label:* small, imprecise and one-sided.
14. **Rate-differential models of USD/KRW direction; a hard-wired "foreign selling ⇒ weak KRW"; Korean foreign flow as a direction signal or a flow-regime up-weight** (N-23, N-21). Labelled by variant:
    - `null · E` rate-differential models: R² 0.022;
    - `inconclusive · E` the flow rules: in Q3-2026, USD/KRW fell 12.4% (the won stronger) while foreigners sold ₩21.5tn in September alone (one episode against the rule).
15. `inconclusive · E` **"USD down and equities down" as an equity de-risk trigger** (N-29). It was followed by +7.27% over 13 weeks vs +2.84% unconditional. *Label:* one sample, against the rule.
16. `inconclusive · E` **A credibility-state blackout rule (contested-state blackouts of all families)** (N-32). The gauge read "anchored" in 2022. *Label:* one episode.
17. `inconclusive · E` **A 200-day-average conjunction on the vol target** (P6's fix) (N-14). It removed the bull tax but also all Q3-2026 protection: −38.1% vs −9.6%. *Label:* one episode, against the rule; a single path neither promotes nor rejects (P12). The R-28 trend card is a different object: a stand-alone, pre-registered CARD-P composed by `min()`.
18. `harm · G` **Treating 2022–26 as a clean holdout** (N-50). Those years were seen during the research. The locked holdout starts on 2027-01-01, and 2022-01-01 → 2026-10-02 is a reported stress window, not a holdout (§7 `gate`; P11).
19. `harm · G` **Data shortcuts** (N-46, N-47; P5, P18):
    - Yahoo continuous-futures returns across rolls;
    - an unnamed "Brent";
    - intraday circuit-breaker prints as closes;
    - positional lags on monthly series with gaps;
    - H.10 or H.15 data used as if same-day;
    - US-session data on KOSPI close-to-close returns of the same date;
    - *(v2.0)* a provisional, intraday or bar-derived row as an acting close, such as the 2-Oct vendor row 6,943.66 (R-01, R-27).
    
    *Label:* each shortcut inflated a cited result: look-ahead +0.31 → +0.05 implementable; the KRW leg +0.032 → +0.001 at strict H.10; the rates leg +0.038 → −0.000 at strict H.15; CPI 3.71% vs 3.35%.
20. `inconclusive · E` **China PMI or CNY as a Korea signal** (China stays in the covariance only); **CESI as an equity feature** (executive DROP list; one-sided). *Label:* no estimate cited.

**Read-only design and governance (v1.1; extended in v2.0)**

21. `harm · G` **Any order, cancel, withdrawal, deposit-address or transfer path, or a broker execution adapter, inside this programme** (P0; QUANTGEN rule 01). §3.10 records what would have to hold if the owner ever decided otherwise. It is not a design.
22. `harm · G` **Offering a non-PASS card's output as a recommendation**, or letting a FORWARD-SIM multiplier reach the recommended book (P7; QUANTGEN rule 03). *v2.0 (P7, P14):* this includes:
    - the R-28 and R-29 FORWARD-SIM cards, until their build conditions hold;
    - R-04 (DEMOTED: specification book only, "step 3 FAIL");
    - a ladder step that binds on more than 10% of days before its CARD-P passes (R-31);
    - R-11 or R-12 in any book other than its display-only refusal book.
    
    Both refusal legs are REJECT at every timing on long history. R-11: ΔMDD vs the static book −1.3 pp and tail-exposure ratio 1.004 at strict H.10. R-12: ΔSR −0.103 (share 0.00; R4b) and −0.120 (DL-A) net of 50 bp at strict timing, and timing-fragile (fragility ratio 0.75).
23. `harm · G` **Lowering a pre-registered cost, or switching a card's instrument book after seeing results**, to make a card pass (P10). An instrument-book change is a new card. *v2.0 (P11, P15; QF4-M2, QF1-M1):*
    - the instrument book, notional NAV, rebalance rule and no-trade band are header fields fixed before the run (R-26);
    - each variant is a new card counted in the family ledger (R-23);
    - monthly and banded 50 bp variants of the US card are logged trials, never rescues;
    - the cost floor raises costs and never lowers them.
24. `harm · G` **Smoothed or forward-looking calm / normal / elevated / stressed labels, or using those labels (or the existing regime read or sheet z-scores) as gates** (§3.6, R-06; N-49; P5, P19). *v2.0:* the R-06 display labels (relative and absolute) are causal volatility labels, display only; they are not regime states. A calibration layer on them is item 28.
25. `harm · G` **Any model as the sizing estimator, except through the staged estimator gate (R-30) as a counted card revision that passes the full v2 CARD-P** (R-06, R-16, R-30; architecture review B5; P11, P13).
    - B5 in the same FHS form as SMA20 is necessary but cannot select: it passes 7 of 9 KOSPI and 8–9 of 9 US models (DLB-T1f).
    - Long-window GARCH-t and GJR-t already pass it on KOSPI 2001–26 and the US 1995–2026; the skewed-t is untested. The app's own SPY REJECT applies to the t-quantile fan tail only.
    - A GJR fit outside its bounds, or a tripped OHLC open-quality flag, falls back to SMA20 (fail-closed).
    
    *Label:* an estimator change can flip a knife-edge card (an EWMA(0.94) switch turns the Korea card INSUFFICIENT on PC-4 under §8.6's windows, at 0.51), so it is a selection, and it is counted.
26. `harm · G` **Value-timing golden values presented as compliant** (P5). H.10 and H.15 series used before publication must be labelled VALUE or NON-COMPLIANT (§9.3), and a production rule may not read the published series in their place. *Label:* see item 19 (KRW leg +0.032 → +0.001; rates leg +0.038 → −0.000).

**New in v2.0 (R-33; QC resolutions and red lines)**

27. **A regime-model state, acting or displayed** (P19; red line E1, binding; QC resolution 10; QF7-M1 CONTESTED, QF7-A5, X-PX1-N5, QF5-M9, QF7-M4). Labelled by variant; the prohibition binds whatever the label (G).
    - **Rule.** No regime-model state (jump model, Markov switching, GMM label or change-point "regime") acts on exposure or is displayed on any QUANTGEN page in v2.
    - Unpenalised daily Markov switching stays prohibited (item 11). The "30.8 switches a year" figure is quoted only with "2-year initial training; ≈ 9.75–9.95 a year with long training".
    - A BOCPD scale-break probability (hazard 1/250, declared prior) may be written to the R-18 research log only: never acting, never displayed, no R-18 dependency.
    - GMM scenarios stay deferred behind the replay library and are never labelled as a current regime (R-16).
    - The R-06 σ̂ display labels are volatility labels and stay.
    
    *Labels by variant:*
    - `inconclusive · E` the jump model (SJM50). In the US it switches 1.26 times a year, with ΔMDD +13.9 pp but INSUFFICIENT (17 onsets). Protection is λ-robust (+12.8 / +13.4 / +13.9 pp at λ 25 / 50 / 100, 50 bp); Sharpe is not (+0.011 / +0.040 / +0.014). KOSPI has no λ plateau (+2.3 / +3.1 / −0.7 pp) and fails PC-3. July 2026 was flagged at the trough. In 2020 the exit came 111 sessions after the trough (+57% missed). BAND200 dominates on the full US sample (+16.5 vs +13.9 pp; ΔSR +0.107 vs +0.056 at 50 bp) and in the clean 2024–26 holdout (ΔSR vs S −0.070 vs −0.128); λ = 50 was learned on S&P, DAX and Nikkei over 1990–2023. In the clean FTSE and HSI holdouts SJM beat the band (+11.6 / +7.5 vs +6.8 / +5.1 pp).
    - `harm · E` Markov switching: US 16.68 switches a year, ΔSR −0.244 at 50 bp, 4.2% a year lost to turnover (DLB-T4a); KOSPI's 30.78 a year is a 2-year-training artefact (9.75 a year on the long file).
    - `inconclusive · E` GMM scenario labels and change-point "regimes": untested as states.
    
    **Settling test (backlog).** A pre-registered 2027–28 forward head-to-head of SJM50 vs BAND200 vs VT15 at 50 bp, on the US and the never-used STOXX50E and TWII. An SJM card may be proposed only if its ΔMDD is at least the band's at no more turnover (ties go to the band), with a λ ledger of at least five values. Korea is excluded. The head-to-head decides only whether a card may be proposed; the card itself goes through §8 (P14).
28. `null · E` **A Mondrian conformal label layer on the display labels** (QF7-M3, INVALID; archived). Per-label coverage is algorithmic: a constant σ̂ passes it. Tick loss ties plain FHS (16.152 vs 16.151). Per-label coverage reporting stays (R-06). The cure for miscalibrated labels is a better σ̂ through R-30. Reopen only if FHS-GARCH labels still miss coverage.
29. `harm · E` **A maintained ML challenger pipeline** (QF3-M6, INVALID; unanimous REJECT). No ML volatility-state model is kept running, re-tuned or re-scored as a challenger. The negative result is archived: the EWMA rule beats the elastic net and GBM even with the nested feature (KOSPI Brier 0.0387 vs 0.0558; item 11a). The harness script is kept in `docs/` as the record. Reopen only with intraday realised variance and a nested design.
30. `harm · B` **`max(σ̂_SMA20, implied)` sizing** (QF6-A15, DESIGN-DEFECT; QF6-M6; P3).
    - An implied vol carries the variance risk premium, so the max() de-grosses permanently: US average weight 0.79 vs 0.88, turnover 6.0 vs 2.7 a year, ΔSR −0.166 at 50 bp (share 0.00).
    - VKOSPI is not available at the KRX decision: KOSPI 200 options close at 15:45 KST, 15 minutes after the equity close.
    - Implied vol is context, logged as live snapshots (VIX/VIX3M at 16:00 ET; QUANTGEN's KOSPI 200 MFIV at 15:30 KST; R-13).
    - It may enter sizing only inside HAR-IV, and only if HAR-IV wins the R-30 race. Its forecast gain is concentrated in 1995–2007 (none since 2010: 0.615 vs 0.614).
31. `harm · G` **Product-composed de-risk stacks** (P2, P16, P17; X-EX1-N2; DLA-D2).
    - Composition is final = vt × min(overlay₁, …, overlayₖ, ladder). A product of de-risk multipliers is refused.
    - On KOSPI at 3 bp, the product VT20 × SMA10m × ladder sits at ≤ 0.25× on 31.0% of days (11.2% with `min()`) and captures +7.6% of the +47.3% 2020 rebound (+12.6% with `min()`). In the US it sits at ≤ 0.25× on 17.9% of days and captures +4.5% of a +46.9% rebound.
    - Its Sharpe is not the reason (0.574 vs 0.535 with `min()` on KOSPI). The stack is an exposure path no card gated, and it quietly shrinks the book.
    - Once two or more de-risk factors act, the recommended book is gated as one stack CARD-P (R-02, §8.7).
32. `harm · G` **A venue switch after results** (P11, P15; red line E5; QF4-M2). It extends item 23 to every header field of R-26. A verdict speaks only for its declared book: the US 50 bp REJECT is labelled by instrument, and MACRO-R06-US-FUT is a new card (R-29), not a revision.
33. `harm · G` **A stock book as a market-gross scalar** (P10, P15; red line E5; QF1-M1; R-26).
    - Market scalars trade on the cheapest delta-one line declared ex ante: the KRX ETF line (3 bp; the tick floor applies), or index futures where one contract is ≤ ~5% of the sleeve (≈ ₩1bn or more for mini KOSPI200). Integer mini contracts give 7.5% a year tracking error at ₩0.1bn vs 0.7% at ₩1bn (EX2).
    - The R-06 KR line at 35 bp is printed for reference only (1997–2026: p_ni 0.141, INSUFFICIENT).
    - An ex-pair stock basket under the Korea caps is a separate card. It opens only on the R-07 conditions: the owner asks for full Korea beta at the cap, a stock-book card has passed and limit-lock flags exist (D1).
34. `harm · G` **A pooled or A-provisional route for a card already run** (P11; red line Q1; QF5-M6).
    - A pooling rule must be declared before any market is run (§7 `gate.tiers`). No pooled route is open to R-04, the jump model or the KOSPI trend card.
    - R-04's A-provisional route is closed: it stays in the specification book labelled "step 3 FAIL" (deflated add-on 0.77 at N_equiv; BL-C12 passed in 1 of 3 regions).
35. `harm · G` **A forward record presented as validation** (P14; red lines P3, Q3; R-25).
    - Forward books are falsification alarms only: a forward record can demote a card, never raise its verdict.
    - An INSUFFICIENT Korea card has no forward-record route; it is re-gated only when new history adds an objective episode.
    - The US futures card is settled on 1926+ history (R-29).
36. `harm · G` **The Kish trial count** (P13; R-23; QF3-A1b withdrawn). N_eff = max(N_clusters, N_equiv) with the exact E[max]; Kish is not computed. Kish can be gamed: padding a 26-trial ledger with 80 near-duplicates lowers Kish N 1.81 → 1.20 and lifts R-04's deflated score 0.951 → 0.986.
37. `inconclusive · E` **A KOSPI trend card that acts** (QC resolution 9; R-28).
    - The SMA10m trend card is registered for the US and other non-Korean sleeves only. In Korea the trend state is CONTEXT-ONLY: displayed, never acting.
    - KOSPI evidence (DLB-T3d): the daily tail ratio 0.929 fails PC-2 (0.853 at 21 days); +2.2 pp on VT20 but −2.3 pp on 2016–26; BAND200 −0.7 / +0.7 pp.
    - *Label:* mixed in sign.

### 10.3 Enforcement: rules-store validation (R-33; T-DNB-01)

`core/rules/validation` refuses a rules-store entry, card header or book-builder configuration whose shape matches a row below; each shape is a predicate over the rule-object fields of §7.1. The refusal names the item and its label. It is logged in the store's edit history, and nothing is written. The keys are in §7 (`do_not_build`).

| Refused shape | Items | Check |
|---|---|---|
| An order, cancel, withdrawal, deposit-address or transfer path; a broker execution adapter | 21 | T-RO-01 (static scan), T-RO-02 (runtime guard) |
| A multiplier, weight or vol-target cap above 1.0 | 2, 8 | T-CAP-01 |
| A composition other than `min()`; a product of de-risk multipliers | 31 | T-CAP-02 |
| An acting or displayed field whose source is a regime model (`source_kind: regime_model`), or a smoothed or forward-looking label | 11c, 24, 27 | T-DNB-01 |
| An ML classifier as an estimator, gate or label source; a challenger entry of kind `ml` | 11a, 29 | T-DNB-01 |
| A conformal calibration layer on the display labels | 28 | T-DNB-01 |
| A sizing estimator that takes `max()` over an implied-vol series | 30 | T-DNB-01 |
| An estimator change outside a counted R-30 revision | 25 | T-DNB-01, I-10 |
| An edit to `instrument_book`, `notional_nav`, `rebalance`, `no_trade_band` or a cost after a card's `results_md5` exists (a new card id is required) | 23, 32 | T-DNB-01, T-BOOK-01 |
| `instrument_book: KRX_stock_book` on a market-gross scalar (`instruments.market_scalar_on_stock_book: refused`) | 33 | T-DNB-01, T-BOOK-01 |
| A pooled or A-provisional tier declared after any market's result exists | 34 | T-DNB-01 |
| A card whose evidence field cites a forward book as validation | 35 | T-DNB-01, I-14 |
| A Kish computation (`kish_design_effect` is in `gate.step3.forbidden`), or an N rule other than `gate.step3.n_gate: max(N_clusters, N_equiv)` | 36 | T-DNB-01, T-NEFF-01, T-STEP3-02 |
| An R-28 instance with `market: KR` | 37 | T-DNB-01 |
| A recommended book reading a FORWARD-SIM, refusal-book or specification-only multiplier (an R-31 step with disposition `INVARIANT_STEP`, binding share ≤ 0.10, is not specification-only; Resolution 6) | 22 | I-03 |
| A production rule reading a value-timed or unpublished series; a provisional or bar-derived acting close | 19, 26 | T-LAG-01, T-PROV-01, T-BAR-01 |

Items without a row (1, 3–7, 9, 10, 12–18, 20) are design prohibitions with no configuration shape of their own. Code review enforces them against this list, and reopening one needs a new card with new evidence (§8).

### 10.4 Not on this list

- **Range-based log-HAR and COMB** are admitted to the estimator race (item 11b; R-30).
- **The R-06 σ̂ display labels**, relative and absolute, stay. They are volatility labels, not regime states.
- **The BOCPD scale-break probability** is a research-log entry (R-18), never acting or displayed.
- **The KOSPI trend state** is displayed as context (R-28).
- **D3 (QF5-M10, a calm-state reversal down-weight)** is an owner decision, not a prohibition. The default (not adopted; P3 stands) is enforced by `families.reversal.calm_state_downweight: not_adopted` with its `owner_decision: D3` marker (§7).

---

## 11. Current state snapshot (2026-10-02, post-patch)

Use this on day one to sanity-check the implementation, at the Level-1 tolerance.

**Sources:**
- **v2.0:** the post-patch recomputation on the official 2-Oct close (DL-A §7, `QX_DLA_postpatch.csv`; QF2 `qf2_02`). It replaces every value that read the 6,943.66 vendor row;
- the council's concentration and calendar facts (QC resolution 12; QF2 §4.3; X-EX2-N2) and the dual volatility labels (QF6-M8);
- the R4 recomputation (`R4_golden_values.csv`) and the R4b strict-timing and label rows (`R4b_golden_values_net.csv`), for values the patch does not touch;
- Executive Chair Appendix A (`R3_CHAIR_E_checks.txt`).

The v1.1 values were traced in Appendix V of the backlog, and the post-patch values in DL-A §7.

**How to read the snapshot.**
- "Data date" is the date the value refers to.
- The decision that may use a value follows §4.1. The KRX decision of 2 Oct is stamped 06:30:30Z and earns from the next KRX session, **6 Oct** (5 Oct is a substitute holiday).
- No card has been formally run, and the gate package is not frozen yet. So every row's recommended-book value is the invariant-only value (§8). The outputs below are specification-book values unless a row says otherwise.
- Owner decisions are at their defaults (the Quick start table).

**The 2-Oct data patch (R-01; QF1-A3, QF2-A1, QF4-A12, QF6-A12; DL-A §7)**

| Item | v1.2 (vendor row) | v2.0 (official close) |
|---|---|---|
| KOSPI close, 2 Oct | 6,943.66 (from a file written at 10:56 KST, mid-session) | **7,003.74** (+0.46%; `value_status = official_close`) |
| Drawdown from the 9,114.55 peak | −23.8% | **−23.2%** (−23.16%) |
| Close / 200-day average | 1.098 | **1.107** |
| rv20 (SMA20) | 28.9% | **28.8%** (28.82%) |
| vt decided at the 2-Oct close | 0.691 | **0.694** |
| KRW=X | 1,360.63 (2 Oct, provisional); 20-observation change +0.38% | **1,356.84 (1 Oct)**; change −0.11%. The provisional 2-Oct row is dropped. |
| Samsung + SK hynix implied share (B3a anchor) | ≈ 53.7% | ≈ 53.6%. The gap to the Sedaily-anchored 51.2% is anchor drift, not the patch. |

No verdict changes. Unchanged at print precision: the weight earning on 2 Oct (0.61), the relative label "elevated", and rv21 31.9% at the 73rd percentile.

**Momentum and vol targets**

| Input | Value (data date) | Specification-book output | Display labels |
|---|---|---|---|
| US Mom σ126 | 23.9% (2026-08-31) | **vs = 0.50** (R-03; indicative PASS; step 3 passes at N_equiv 6.3 (0.98) and is borderline at the linear N̂ 12.6 (0.947)) | — |
| US 24-month market return | +39.7% (end-Aug-2026) | D&M bear state **OFF** (R-04: specification book only, "step 3 FAIL"). Mkt vol126 14.3% vs its 2/3 quantile 17.4%. | — |
| KOSPI close | 7,003.74 (2026-10-02, official close; +0.46%); −23.2% from the 9,114.55 closing peak; 1.107 × 200-day average | — | — |
| KOSPI rv20 (SMA20) | 28.8% (2026-10-02) | **vt_KR earning on 2 Oct = 0.61; decided at the 2 Oct close for the next session (6 Oct) = 0.694** (SMA20, target 0.20, cap 1.0, KRX ETF line). rv21 31.9% sits at the 73rd percentile of the trailing 3 years. | **elevated** (relative: 70th percentile; quartiles 15.7 / 18.6 / 33.6%) · **stressed** (absolute) |
| S&P 500 | 7,666.45 (2026-10-01); 1.062 × 200-day average; rv20 10.7% | **vt_US = 1.00.** The registered US card is REJECT by instrument (US shares via KIS, 50 bp). MACRO-R06-US-FUT (R-29) and the R-28 trend card run FORWARD-SIM. With no US sleeve (D5), neither can reach the recommended book. | **normal** (relative: 28th percentile) |

**Risk layer (R-07, R-10, R-31; invariants)**

| Input | Value (data date) | Output |
|---|---|---|
| Samsung + SK hynix | ≈ 51% of KOSPI (51–54% by anchor: 51.2% Sedaily-anchored, 53.6% on the 25-Oct-2024 KRX-weight anchor; 2 Oct 2026; 55.5% reported in 2026; re-anchor monthly to an official KRX figure). 53.8% of KODEX 200 on look-through. ≈ 75% of KOSPI's 63-day variance. | Template MSCI 25/50 (D1 default): absolute single-name bound 22.5 / 29.8 = **0.755**; active-cap bound at most 0.05 / (0.298 − 0.225) = **0.685**. Specification book: gross min(0.694, 0.755, 0.685) = 0.685; recommended book (vt NOT_RUN enters as 1.0): gross min(1.0, 0.755, 0.685) = 0.685. The active bound binds in both books; the binding factor is printed per book (`concentration.by_book`). The pair's risk contribution is printed. The semiconductor cap 0.50 is unchanged. |
| Drawdown ladder and hard stop | — | Ladder steps act in the specification book only until R-31's CARD-P passes (Korea VT20 binding share ≈ 19%). Hard stop **armed** at −15% of book NAV (D2 default). Both KR books **ARMED** (each book has its own runtime state, §3.8). |
| Next KRX session | Tue 6 Oct | `gap_sessions` 2 (the US sessions of 2 and 5 Oct): tagged KRX_HOLIDAY_GAP; the displayed 1-day VaR is scaled by √2 (R-10). The Sep NFP (2 Oct 08:30 ET = 21:30 KST) sets `kr_open_gap_session` = 6 Oct. Annotations only: no tag changes any weight. |
| The next two weeks | Hangul Day Fri 9 Oct; Columbus Day Mon 12 Oct | 12 Oct is the second multi-session gap session (the US sessions of 8 and 9 Oct). On Columbus Day the NYSE is open and the Federal Reserve Board is closed, so the H.10 release for the week of 5 Oct is usable from the KRX close of Wed 14 Oct (T-H10-02). |

**Stress inputs**

| Input | Value (data date) | Output |
|---|---|---|
| VIX / VIX3M | 16.34 / 18.37 (2026-09-30) | Annotation **OFF** (R-08 annotates and never acts; usable from the 2026-10-01 US close; §4.1) |
| HY OAS | 3.12%; 21-day change +47 bp (2026-09-30) | Context (just under +50 bp) |
| Baa−10y | 1.47; 21-day change −12 bp | Context |

**Refusal books (display only; read by no book; R-11 and R-12 RETIRED)**

| Input | Value (data date) | Output |
|---|---|---|
| US 10y | 5.29% (2026-09-30), the highest close since 14 May 2002; 20-day change **+50 bp** | **S2 flag on in data dated 23 Sep 2026.** Under strict H.15 the refusal book applies it from the decision at the close of 25 Sep (earning from 28 Sep), and it was still on at the last US date in data (1 Oct). REJECT recorded at every timing and cost (DL-A). |
| USD/KRW | DEXKOUS 1,356.51 (2026-09-25), 20-observation dlog −1.81%. KRW=X 1,356.84 (2026-10-01; the provisional 2-Oct row is dropped), 20-observation dlog −0.11%. | **S1 flag OFF** on both timings. Under strict H.10, the latest DEXKOUS usable at the 2 Oct KRX close is dated 25 Sep (published Mon 28 Sep, 16:15 ET). REJECT recorded on 1997–2026. In production the refusal book reads the ECOS 15:30 close or a timestamped 15:30:00 KST snapshot (R-11); DEXKOUS is a labelled proxy. |

**Hedge state (risk model only; R-09)**

| Input | Value (data date) | Output |
|---|---|---|
| Core PCE YoY | 3.01% (Aug-2026, calendar lag; 3.008%, within revision noise of the 3.0 threshold) | Contributes to `hedge_credit_off` |
| Stock–bond correlation, 63 / 252 days | +0.53 / +0.33 (2026-09-30; S&P vs −ΔDGS10 on date-aligned pairs) | **`hedge_credit_off = TRUE`**; `hedge_reasons` = [corr_positive, core_pce_ge_3] (both causes hold) |
| Broad USD | 120.33 (2026-09-25); 20-day change +1.67% | `hedge_failure` FALSE (the USD is up). This DTWEXBGS line is context; R-09 computes `hedge_failure` from `USD_LIVE_PROXY`'s 1-day change, which M2 reproduces |
| Weekly KOSPI vs ΔUSD/KRW, trailing 26 weeks | +0.05 (2026-10-02) | `fx_hedge_credit` FALSE: no credit (display only) |

**Context**

| Input | Value (data date) |
|---|---|
| 10y TIPS / 10y breakeven / 5y5y | 2.93% / 2.36% / 2.36% |
| Kim–Wright term premium | 1.02 (2026-09-25); first reading ≥ 1.0 since 2010 |
| MOVE | 108.1 (2026-10-01) |
| 10y–3m / 10y–2y | +1.07 / +0.46 (2026-10-01). The probit (published coefficients) last read 0.095 (Q1a). |
| Sahm (real-time) / U-3 | −0.07 / 4.1% (Aug-2026) |
| CPI YoY | **3.35%** with the correct calendar lag; 3.71% with the wrong positional lag (this is a test value) |
| Taylor residual | Policy 0.4–2.3 pp below the rules; central −0.9 pp; Fed range 3.75–4.00% after the 16 Sep 2026 hike |
| Brent | Dated spot $113.96 (2026-09-29); BZ=F futures $102.59 (2026-10-01) |
| USD/JPY | 157.18 (DEXJPUS, 2026-09-25); 160–164 is the intervention hazard zone |
| BoK base rate | 3.00% (hikes on 16 Jul and 27 Aug 2026, the latter 6–1) |

---

## 12. Build order v2 (mapped to QUANTGEN packages)

The order is the council's (QC resolutions, module table). It matches the Quick start. Do not start M(k+1) until M(k)'s acceptance tests pass in `tests/run_all.py`. Each milestone's acceptance also includes the test table inside every rule it builds (R-19 to R-31, R-34); §9.0 maps every module to its tests. A test runs from the milestone of its `runs_from` (§9.0a), so a milestone's acceptance is exactly the tests whose `runs_from` is that milestone or earlier, without the clauses §9.0b defers. The gate package is built and frozen in M7 before any formal card runs (P11). **v2.0 changes (QCE-146):** M1 starts the KIS quote check, in parallel; calendars, data contracts and the forecast registry are milestone deliverables; M9's acceptance is out-of-sample 99% VaR, ES 97.5% and fan PIT against the thresholds of I-11.

| Milestone | Modules | Scope (package) | Acceptance criteria |
|---|---|---|---|
| **M0** Scaffolding | R-26, R-32, R-33; the R-02 bounds | `core/rules`: rules-store entries (§7) and rule objects (§7.1) with validation, the owner-decision registry, the cost-table reference with the tick floor, and the instrument-book, notional, rebalance and no-trade-band header fields (R-26). DO-NOT-BUILD checks (R-33, §10.3). JSON Schemas 2.0 (§6, R-32). Bounds. An artifact writer with git, config, snapshot, gate-package and ledger hashes, and the `governance_events.jsonl` appender (§6.6; T-OWNER-01 writes the first event). Macro fixtures under `tests/fixtures/macro/` (proposed), frozen from post-close files. | T-RO-01, T-HERM-01/02, T-SCHEMA-01/02/03, T-CAP-01, T-BASIS-01, T-REPRO-01a, T-COST-02/03, T-BOOK-01 (header clauses), T-DNB-01 and T-OWNER-01 pass |
| **M1** Data layer | R-01, R-19, R-20 | **First task, run in parallel:** pull KIS bid/ask for 069500 and 005930 at 15:19:59 KST on 20 sessions; confirm the level-1 fields, the exchange vs receipt timestamps, the field that returns the KRX regular-session official close and whether the app key can trade (QF1-A25; BL-C02, BL-D03; T-RO-02). It gates only code that reads KIS bid/ask or quote timestamps, not the rest of M1; without KIS access it is recorded as "not run". If the fields are missing, BL-C02 needs another quote source. <br>Then `core/ficc/data`, the point-in-time layer: <br>• the registry with publication schedules and roles (§4.2); <br>• `pit_value` returning PITValue v2 (`value_status`, `session_date`, `retrieved_at_utc`, …) with the provisional-row guard (R-01); <br>• **data contracts** and schedule-aware staleness by role (R-19; QF2-M3); <br>• vintages, the lag audit, and no synthetic acting inputs. <br>Then `core/calendars` and `core/markets`: **effective-dated calendars** for KRX, NYSE, the Fed and SIFMA, with Korean regime dates (price limits, Saturday sessions, close times, the random end, substitute and election holidays; R-20; QF2-M5); DST; `decision_time_utc` (the scheduled close) and `close_print_bound_utc` (the decision instant: the KRX scheduled close + 30 s, 06:00:30Z for 2015-06-15 … 2016-07-29 and 06:30:30Z after; the NYSE close + 30 s); `usable_at`. ECOS provider (proposed). <br>Then a minimal per-book `core/engine/runtime` (§3.8): the book ids, DISARMED/ARMED/HALTED, the R-19 input and book counters, and `runtime_halt` / `runtime_rearm` for class OPS (automatic re-arm when the cause clears), so M1's HALT-scope tests run on it (R2-C6). M5 adds the RISK class, the operator re-arm cases and the heartbeat. | T-PROV-01, T-FIX-01, T-BAR-01/02, T-CLOSE-01/02, T-AVAIL-01, T-STALE-01, T-ROLE-01/02, T-XMKT-01, T-LAG-01/02, T-SYN-01, T-TZ-01/02, T-MISS-01/02, T-SER-01/02, T-PRINT-01, T-H10-01/02, T-H15-01, T-VIX-01, T-SAT-01, T-REGIME-01, T-CAL-01/02, T-RO-02 and G-POST-01's data rows pass, without the clauses §9.0b defers. CPI Aug-2026 YoY = 3.353%. The KIS quote check result is recorded. |
| **M2** Risk layer | R-02, R-09; the R-06 sizing function | `core/quant/risk`: SMA20 σ̂ and `market_vol_target` (R-06 formula; relative and absolute display labels); `compose` by `min()` with the 0.5 × vt floor outside HALTED (R-02); the R-09 hedge state with date-aligned corr63 and `fx_hedge_credit`. Optimiser inputs honour `hedge_credit_off`. The research bootstrap of §9.3.1 (circular, 63-day blocks, 1,000 resamples, seed 20261002), used by the G-KR and G-US shares. | G-KR-01..04 and G-KR-02b/02c, G-US-01/01b/01c within Level-1 tolerance, gross and net, on post-patch values (DL-A §7); G-KR-06 (reference mode) only once §9.4 item 2's rerun is md5-frozen (§9.0a); G-KR-05/05s at M8. T-CAP-02 (its stack-card clause from M7), T-VT-01, T-CORR-01, T-HEDGE-01, T-COST-01, T-LABEL-01 and I-02 pass. §11's `hedge_credit_off` is reproduced from R-09's inputs, with core PCE read as of its vintage at the decision; `hedge_failure` uses the live USD proxy's 1-day change. |
| **M3** Estimator harness | R-30 | `docs/vol_backtest.py` (B5, rolling origins, FHS and model forms, PIT), published with its seed. The forecast-evaluation harness in `core/quant/backtest` (proposed) with its **forecast registry**: losses declared in advance (QLIKE; tick loss), DM, Clark–West, Giacomini–White and MCS, Kupiec and Christoffersen, reliability tables (QF7-M2). The staged estimator gate (R-30). Estimator status returned by `estimator_gate()`; the M6 builder writes it to `macro_state.vol.estimator_b5` and `vol.estimator_gate`. | G-B5-01..04 and G-EST-01..04 reproduced; T-B5-01, I-10 and T-EST-01/02/04 pass (their Stage-3, bootstrap-CI and counted-revision clauses run from M7) |
| **M4** Factor sleeves | R-03, R-04, R-05, R-15 | `core/quant/signals`: family tags on the composite (§3.7); R-03 own-vol scaling with revisions 2 and 3 as counted trials; R-04 in the specification book only; R-05; R-15 base weights IV_m × 1/K_m. The exposure basis is wired through; recommended vs specification books. | G-MOM-01..06, G-MOM-08, G-BOOK-01 and G-INTL-01 within tolerance (G-MOM-07 in reference mode); T-R03-01's sleeve-scale and years clauses and T-PRIOR-01 pass. T-R04-01, G-DSR-02 and T-R03-01's step-3 and header clauses run in M7, after the freeze |
| **M5** Engine and events | R-07, R-08, R-10, R-27 | `core/engine`: evaluator BLOCKED decisions; on the M1 per-book runtime: the RISK class (hard stop, risk-limit breach), the remaining OPS triggers (heartbeat, NAV, calendar coverage, operator kill) and the operator re-arm cases (§3.8); the hard stop with its automatic, rule-defined re-arm (R-07, §3.8); per-card switch counts; the simulated fill model with the bar convention and limit-lock flags (R-27); overlay-on/off and FORWARD-SIM simulated books. `core/quant/risk`: Korea look-through caps with the active single-name cap (R-07, D1). R-08 as an annotation. `core/calendars` event store: the BoK decision and press conference as separate events with status, opening-gap nights and multi-session gaps (R-10). | I-04, I-04b, I-06, I-06b and I-06c pass; T-CAPS-01, T-ANNOT-01, T-FILL-01..03, T-HALT-01, T-STEP-05, T-BOOK-03 and T-MONO-01 pass; G-LAD-01..03 reproduced in reference mode (§9.3.3); the FOMC → KST mapping test passes; window hits and BLOCKED decisions are logged |
| **M6** Context and breaks | R-13, R-18 | `core/ficc/macro`: R-13 items with vintages (leverage and flow, VRP, live implied-vol snapshots, turbulence); the probit, the Taylor range and the isolation guard; reconciliation of the 18-indicator sheet with no regime-model state displayed (§3.6; BL-G06; P19); R-18 policy trigger (acting) and the statistical, scale-break and BOCPD logs (log only). The `macro_state` and `overlay_decision` builders. Until M6, tests assert the outputs of the functions that fill these artifacts (`market_vol_target`, `hedge_state`, `estimator_gate`, `concentration_bound`, the runtime), never a built artifact (§9.0b). The Macro page panel, listing every open owner decision. | T-CTX-01/02 and T-BREAK-01 pass; §11's context values are reproduced; every sheet item appears in `context_log` with `from_sheet=true` |
| **M7** Cards | R-21, R-22, R-23, R-24, R-34 (frozen first); then the formal headers of R-06 KR, R-03 (with its two revisions), R-14, R-31, R-28 and R-29, and the runs of R-06 KR, R-03, R-14 and R-31 | `core/quant/backtest`: the v2 gate package (CARD-P legs, PC-2 with CI, binding PC-3, the do-no-harm cap; objective episodes, excess returns and the start band; the family ledger and N_eff; power and MDE; the timing-fragility gate). **Run the gate-acceptance test (at most one bounded redesign, R-21 9(a)) and md5-freeze it in `gate.package` (version, definitions md5, acceptance-report md5; §8.1.3).** Only then does `docs/macro_overlay_study.py` write one model card per rule through the existing nine-step gate, with the overlay-on/off paired evaluation and the static same-exposure comparator. Open implementation tasks: §9.4 items 15 (anchored timestamps, before the freeze) and 16 (an archived snapshot per formal card). | The harness tests of §8.1.3 step 1 and I-05 pass; then I-08 passes and its results md5 is written (every attempt logged). Then I-09, I-07, I-15 and I-16 pass; T-GATE-02, T-RLAYER-01, T-R03-01, T-R04-01, T-R14-01, T-R06-US-01, T-CARD-01/02 and T-REPRO-01b pass; G-KR-L*, G-US-F*, G-PWR-* and G-DSR-01/02 reproduced. Header md5 and results md5 are written for every card. |
| **M8** Forward records and workflow | R-25, R-28, R-29, R-11 and R-12 retirement, R-35 | `core/skills/workflows/macro_daily.yaml` (proposed) with its decision gates (R-35), running after each close. Forward monitoring on whole-book NAV with calibrated alarms (R-25). The R-28 and R-29 FORWARD-SIM books with committed card headers. R-11 and R-12 retired to display-only refusal books. Open implementation task: §9.4 item 17 (atomic `engine_feed` per book). | I-01, I-03, I-12, I-13 and I-14 pass; T-REF-01/02, T-REPLAY-01, T-SCOPE-01, T-OBS-01..05, T-CARD-03 and T-BASIS-01's S2 clause pass; G-KR-05/05s, G-TR-* and G-REF-* reproduced. The recommended book reads no FORWARD-SIM, refusal-book or specification-only multiplier. |
| **M9** Quant Lab | R-16 | Expanding-window (≥ 10-year) GARCH and GJR fits; FHS/EVT tails and the envelope max(fast FHS, GJR-EVT); the historical-replay library with regime metadata; seeded scenarios; SEP-band rate paths via `core/ficc/ratesim`. The GARCH-t fan keeps its B5 label. | I-11 passes against its out-of-sample thresholds on 2016–26: 99% VaR with Kupiec and Christoffersen CC p ≥ 0.05; ES 97.5% Z2 not rejected at 5% (simulated critical values); fan PIT χ² p ≥ 0.01 at h = 21; h = 126 and the 2026-only lines are reported, not gated (QF6-A5, QF6-M3). T-REPRO-01c passes. |
| **M10** (deferred) | R-17 | FX and crypto sleeves | When those sleeves exist: T-CRYPTO-01 and T-FX-01 pass; card headers committed; FORWARD-SIM first |

---

## 13. Compact evidence appendix

**ID conventions.**
- "N-xx": nodes in `R4_neural_link_matrix.csv`.
- "PC/PX/PR-P": professor-panel items. "EC/EX/ER-E": executive-panel items.
- "Q1a/Q1b": data labs. "R4": the gross recomputation, `scripts/r4_golden_values.py` → `results/R4_golden_values.csv`.
- "R4b": v1.1's net-of-cost, strict-timing, protective-check and B5-style recomputation, `scripts/r4b_golden_net.py` → `results/R4b_golden_values_net.csv`; verification log `scripts/r4b_verify_spec.py` → `results/R4b_verification_log.csv` (backlog Appendix V).
- "AR" / "PP": the QUANTGEN Architecture Review (2026-09-14, fetched 2026-09-20) and the QUANTGEN public page (2026-09-29).

**v2.0 ID conventions.**
- "R-01"–"R-35": rules and modules (`QC_modules.csv`; R-05 is unchanged and has no council row).
- "QFn-An", "QFn-Mn", "QFn-Cn": audit findings, module proposals and claims in the seven QF papers, QF1–QF7.
- "X-PX1-Nn", "X-PX2-Nn", "X-EX1-Nn", "X-EX2-Nn": new points raised in the four cross-examinations.
- "DLA-xx" (DL-A) and "DLB-Txx" (DL-B): runs of Data Lab A (protective cards) and Data Lab B (estimators and regimes).
- "QC resolution n": the council's resolutions 1–12. "QCE-nnn": a row of `QC_errata.csv`. "D1"–"D6": owner decisions (D6's default rule is frozen with the package and applied only if a negative control passes).
- "C-1"–"C-9": the coordinator's binding rules of adversarial round 1 (`council/ASPEC_R1_claude_critique.md`). The opponents' patch ids (QA engineer "Pnn" and junior developer "Pnn", written "QA Pnn" and "JD Pnn" in the synthesis; data engineer "DE-nn"; risk officer "AS-nn") are mapped to the synthesis issues S-nn in `council/ASPEC_R1_synthesis.md`.
- "R2-C1"–"R2-C7": the coordinator's binding rulings of adversarial round 2 (`council/ASPEC_R2_claude_critique.md`). The round-2 patch ids (QA engineer "Qnn", data engineer "DE2-nn", junior developer "Pnn", written "JD2 Pnn" in the synthesis, risk officer "P2-nn") are mapped to the synthesis issues S2-nn in `council/ASPEC_R2_synthesis.md`.
- "R3-1"–"R3-3": the risk officer's round-3 majors, accepted in the coordinator's round-3 rulings (`council/ASPEC_R3_claude_critique.md`). Their patches are "P3-nn"; the reviewers' numbered round-3 notes are cited as "JD N1"–"JD N6", "DE n", "QA n" and "RO n" in `council/ASPEC_R3_synthesis.md`.
- Red lines are written "red line P1" (Professors), "red line E1" (Executives) and "red line Q1" (QF). A bare "P" number is a §1 principle.
- "BL-xxx": backlog items (`QUANTGEN_MACRO_BACKLOG.md`).

**Rules built now**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-01 macro quantities lag | PC-P-01; EC-E-23, ER-E-21 | Returns → ΔIP p = 2e-8 vs ΔIP → returns p = 0.04. KOSPI leads exports by 4–7 months (corr 0.52 at k = −5). Goyal–Welch–Zafirov: over a third of the 29 post-2008 predictors lose in-sample significance, and half of the survivors fail out of sample. | R2_P3 Granger tests; Q1b B3; Goyal–Welch (via P2) |
| N-02 / N-03 bounds; no multipliers above 1 | PC-P-05, PR-P-12/13/14; EC-E-01, ER-E-04/05/20 | Four-state −0.07. Momentum 1.425× / 1.50× into the 2020 and 2026 crashes. Markov 0.5/1 vs 0/1: 0.554 vs 0.390. R4 KOSPI vol target cap 1.5: 0.534. | Q1b B1; `r2_P1_p6_checks.py`; R4 |
| N-04 stress → variance | PC-P-02; EC-E-05/06, ER-E-19 | VIX-TS → realised vol t 7.17 (R² 0.385; about 4 given current realised vol) vs → return t 0.04. Only implied vol and credit-spread changes add OOS variance information (US, ≤ 1 month); no return predictor survives BH-10%. Cut-and-re-add −0.088. Brent +30% episodes: 2.67% vs 2.66%. EPU +1 SD → +1.80% over 3 months. | `r2_P2_p3_checks.py`; `r2_E5_e1_tests.py`; Johnson 2017 (via P3) |
| N-06 vol scaling | PC-P-03; EC-E-07 | 0.40 → 0.91 (cap 2) / **0.71 (cap 1, R4)**; **0.67 net of 50 bp on both legs (R4b)**. Decay +0.66 → +0.26 (cap 2). z 3.84 / 3.29 / 2.99 for the spec rule (cap 1, net; 10 / 63 / 240-session blocks) against one-sided hurdles 2.50 (≤ 8 cells) and 3.34 (Bonferroni-120); 4.83 / 4.31 / 3.93 for the research rule (cap 2, gross). | Barroso & Santa-Clara 2015, *JFE* 116(1) (https://novaresearch.unl.pt/en/publications/momentum-has-its-moments/); Daniel & Moskowitz 2016, *JFE* 122, Table 7 (https://www.kentdaniel.net/papers/published/jfe_16.pdf); Moreira & Muir 2017 (https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf); Cederburg et al. 2020 (https://experts.arizona.edu/en/publications/on-the-performance-of-volatility-managed-portfolios/) |
| N-07 D&M gate | PC-P-04; EC-E-07 | *JFE* T7 (1934:01–2013:03): **0.682 → 1.041 → 1.194** (dynamic OOS; in-sample 1.202). Table 1 (1927–2013) prints WML 0.60 (17.9 / 30.0); the text states 0.71. Do not pair 0.71 with Table 7; the "1.43" figure appears nowhere in the paper. T11 (the full dynamic strategy, not the floored gate): Europe 0.462 → 1.130, Japan 0.067 → 0.416, UK 0.465 → 0.891. R4 add-on +0.084. | Same D&M PDF; Q1b B1; R4 |
| N-09 reversal and quality 1.0× | PC-P-06; EC-E-08 | 59.2%/yr at 34.8% vol (SR 1.70) vs 1.8% at 12.3% (SR 0.15) on the true VIX ≥ VIX3M flag; μ/σ² 4.90 vs 1.20, so 1.0× rests on P2. RMW β −0.099 (HAC t −3.0). RMW 2022 +8.4%. Overnight +0.93% vs intraday −1.05% a month. | Nagel 2012, NBER w17653 (https://www.nber.org/system/files/working_papers/w17653/w17653.pdf); Lou–Polk–Skouras (https://personal.lse.ac.uk/polk/research/TugOfWar.pdf); `r3_chair_P_checks.py` |
| N-14 / N-16 / N-17 Korea | PC-P-23/24/10; EC-E-02/03/04/15 | KOSPI −38.6% (22 Jun–30 Jul 2026) vs S&P −0.5%, KRW +7.4%. VT20 −12.2% (−12.3% net of 35 bp, R4b). VT20 max DD −36.8% vs −41.3% for the same-exposure static book (R4b). Pair 55.5% of KOSPI. SOX β 0.247 → 0.559 (2026). 88% of 2026 days with rv21 > 30%. SMA20 passes a B5-style calibration check on KOSPI (4.70% exceedance; R4b) but is outside the 90% QLIKE model confidence set (p ≤ 0.0005). | Q1a-C16; Q1b B3; `r3_CHAIR_E_checks.py`; R4; SEDaily 27 May 2026 (https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi); KEIA (https://keia.org/analysis/explaining-south-koreas-stock-market-boom/) |
| N-28 / N-29 hedge state | PC-P-18/19; EC-E-12/13 | Correlation −0.29 / +0.21 by core PCE. Apr-2025: DXY −3.9%, 10y +28 bp, S&P −5.4%. +7.27% over 13 weeks after USD↓ & equities↓. | Campbell–Pflueger–Viceira, NBER w20070 (https://www.nber.org/papers/w20070); Q1a A8, A11; `r2_P3_p4_checks.py` |
| N-33 TS trend | PC-P-27; EC-E-09 | Book SR 0.449, corr 0.03 at cap 1 (0.49 / 0.08 at cap 2; 2013–26 corr 0.34–0.36); KOSPI SMA10m vs static: ΔSR +0.076, ΔMDD +4.1 pp, daily tail 0.93 (fails PC-2); 2020 −16.7% | Moskowitz–Ooi–Pedersen 2012 (https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf); Q1b B5; Zakamulin (https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html) |
| N-37 / N-38 / N-40 / N-41 events | PC-P-13/22, PR-P-24; EC-E-15/16/17/19, ER-E-07/22 | Pre-FOMC drift 44.5 → 9.2 bp. FOMC days +0.6 vs +5.3 bp at 1.3× risk. BoK 0.82×. Quad witching t −0.38. 80.9% of volatility interruptions in the first 30 minutes. ≈ 15% of KOSPI variance from the prior US session jointly (≈ 10% from the S&P alone). | Savor–Wilson (https://faculty.wharton.upenn.edu/wp-content/uploads/2013/06/draft20130612pp-full.pdf); Lucca–Moench (https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.html); Knox–Vissing-Jørgensen FEDS 2026-023 (https://www.federalreserve.gov/econres/feds/files/2026023pap.pdf); Kurov et al., ECB WP 1901 (https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1901.en.pdf); SEDaily 7 May 2026 (https://en.sedaily.com/finance/2026/05/07/kospi-volatility-interruptions-double-in-early-trading-hours); `r2_E2_event_days.py` |
| N-44 / N-48 oil and Monte Carlo | PC-P-02/23/24, PX-P-05; EC-E-20/21 | 2026 vs 2022 at +20 days: KOSPI −15.5% vs +0.4%. Spot–futures gap ≈ $29 (7 Apr 2026). SEP 1-year short-rate band ±1.4 pp (about a 70% band; ±2.2 pp for a 90% fan). | Q1a A10; T1-C6; IEA 11 Mar 2026 (https://www.iea.org/news/iea-member-countries-to-carry-out-largest-ever-oil-stock-release-amid-market-disruptions-from-middle-east-conflict); Fed SEP 13 Dec 2023 (https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20231213.htm) |
| N-46 / N-47 data hygiene | PC-P-12/13, PR-P-04/08; EC-E-26/27 | CPI 3.71% vs 3.35%. Real-time Sahm 0.53 vs 0.50. Payroll benchmarks −818k / −911k preliminary (final −598k NSA for 2024; −898k SA, −862k NSA for 2025; BLS cesbmart). Look-ahead +0.31 → +0.05. H.10 weekly: KRW leg +0.032 → +0.001 at strict publication (R4b). **H.15 posted 16:15 ET the next business day: rates leg +0.038 (value) → +0.010 (+1 business day, R4; compliant via the Treasury par-yield channel) → −0.000 (+2 business days, strict H.15 for a close decision, R4b).** | Richmond Fed on the Oct-2025 data gap (https://www.richmondfed.org/research/national_economy/macro_minute/2025/phantom_figures_missing_data_in_october); Fed H.10 (https://www.federalreserve.gov/releases/h10/20250414/); Fed H.15 (https://www.federalreserve.gov/releases/h15/, fetched 2026-10-02); Q1b-C27 |
| N-50 governance | PC-P-11/29, PR-P-30; EC-E-02/29, ER-E-24 | SE(ΔSR) vs S 0.061 (US VT) / 0.130 (KOSPI VT), 0.02–0.035 for add-on legs; about 150–330 years needed to detect +0.05 for a vol target (MDE80 0.13 / 0.28); 21 stress clusters in 12 years; every one of 26 market-level de-risk overlays (13 US, 13 KOSPI) has a 95% CI that straddles 0 (momentum vol scaling, R-03, is not among them) | Politis & White 2004 (https://public.econ.duke.edu/~ap172/Politis_White_2004.pdf); Patton, Politis & White 2009 (https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf); Bailey & López de Prado DSR (https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf); PBO (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253); Harvey & Liu 2015 (https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF); Harvey–Liu–Zhu (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314); Harvey et al. 2018 (https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf) |

**FORWARD-SIM legs (v1.0: shadow legs)**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-22 KRW leg | PX-P-04, PR-P-08; EC-E-10, ER-E-14 | 0.5×: +0.06 to +0.07. **0.75×: +0.032; +0.042 on VT20 (R4, value timing).** +1 session or Yahoo timing: +0.016. **Strict H.10: +0.001 (R4b). Net of KRX stock 35 bp: −0.008 (R4b).** Protective checks: ΔMDD vs static +1.1 pp, tail ratio 0.99 (R4b). | Q1b B3; `r2_E3_tests.py` S2; R4 |
| N-24 rates leg | PC-P-17; EC-E-11 | +0.041 (0.99, R2 construction); 2020–26 +0.109; ex-2022 +0.028; grid median ≈ +0.01. **R4: +0.038 on buy-and-hold, +0.037 on VT15 cap 1 (value timing); +0.010 at +1 business day. R4b: −0.000 at the strict +2 business days; −0.103 net of 50 bp.** | `r2_E5_e1_tests.py` T1; R4 |

**Context and planned sleeves**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-26 / N-30 context | PC-P-15/16/17, PR-P-06/07/19; EC-E-19/23 | Sahm 9 of 9 recessions, but a median +2 months late (range −4 to +3); Jul-2024 trigger then 26 months without recession. Probit 0.744 in May-2023. Inversion 534 days. 10y +111 bp YTD (TIPS +100, BE +11). KW term premium 1.02. 10y **5.29% = highest close since 14 May 2002**. Policy 0.4–2.3 pp below the Taylor rules. | Sahm 2019 (https://www.hamiltonproject.org/assets/files/Sahm_web_20190506.pdf); Estrella–Trubin (https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci12-5.pdf); Fed policy rules page (https://www.federalreserve.gov/monetarypolicy/policy-rules-and-how-policymakers-use-them.htm); FRED THREEFYTP10 (https://fred.stlouisfed.org/series/THREEFYTP10); Q1a A2, A5, A6, A7 |
| N-52 FX sleeve | PC-P-20/21, PR-P-22/27; EC-E-30 | USD/JPY Fama b −1.92 / 0.11. Carry −10.6% (Jul–Aug 2024). Vol rose in 4 of 5 interventions. Long-KRW carry skew −2.38, worst quarter −36.9% on monthly-average FX (quarter-end point-in-time: −1.80 / −43.8%). | Fama 1984 (https://ideas.repec.org/a/eee/moneco/v14y1984i3p319-338.html); Brunnermeier–Nagel–Pedersen, NBER w14473 (https://www.nber.org/papers/w14473); BIS Bulletin 90 (https://www.bis.org/publ/bisbull90.pdf); MoF intervention data (https://www.mof.go.jp/policy/international_policy/reference/feio/foreign_exchange_intervention_operations.csv) |
| N-54 / N-55 crypto | PC-P-30; ER-E-13 | Net-liquidity rule −0.01 / −0.20. BTC −53% while net liquidity rose $41bn. BTC–NDX correlation 0.09 / 0.47–0.50 / 0.22–0.24 (Wednesday weeks; 0.06 / 0.28 / 0.25 on Friday weeks). | Q1b B6 |

**Prohibitions**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-11 / N-18 / N-43 / N-56 / N-58 | See §10 | See §10 | Q1b B1–B4; R2 executive scripts; E7 street-forecast audit (`results/E7_street_forecast_audit.csv`); Ilmanen et al. 2021, JOIM (https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence) |
| N-49 methods | PC-P-09/28 | Real-time Markov switching (local, `r2_P1_p6_checks.py`): 16.9 switches a year; 49% of episodes do not overlap the smoothed path. Complexity timing: RFF forecasts ρ 0.93 with Nagel's kernel forecasts. Shu–Yu–Mulvey (S&P 1982–2023): HMM 8.5 shifts a year unfiltered, 2.0 with k = 20; jump model Sharpe 0.68 vs HMM 0.54 vs buy-and-hold 0.48. | `r2_P1_p6_checks.py` (16.9 / 49%); Shu–Yu–Mulvey, arXiv 2402.05272 (https://arxiv.org/html/2402.05272v3), for the jump-model / HMM comparison; Nagel, NBER w34104 (https://www.nber.org/papers/w34104), for ρ 0.93; Gu–Kelly–Xiu (https://dachxiu.chicagobooth.edu/download/ML.pdf); Chen–Pelger–Zhu (https://economics.yale.edu/sites/default/files/deep_learning_in_asset_pricing.pdf) |
| N-31 textbook relations | PC-P-14, PR-P-16/17 | Okun −0.407 → −0.05. Phillips +0.04 (2011–25). Sacrifice ratio 5.5 implied vs −1.57 realised. | Ball–Leigh–Loungani, NBER w18668 (https://www.nber.org/system/files/working_papers/w18668/w18668.pdf); Hazell et al., NBER w28005 (https://www.nber.org/papers/w28005); Q1a A3, A4 |

**Corrected anchors (N-60).** Use these values and no others:
- D&M *JFE* 2016, Table 7: **0.682 → 1.041 → 1.194** (1934–2013).
- Ilmanen et al. out-of-sample declines: value **−49%**, momentum **−23% (n.s.)**, carry ≈ −25%, multifactor −18%. The authors' own summary reports a ≈ 30% average drop in estimated premia out of sample (AQR page; attributed to overfitting); priors use the factor-specific figures.
- KOSPI closing peak **9,114.55 on 22 Jun 2026**; Q3-2026 **−19.33%**; peak-to-trough −38.6% in 27 sessions.
- KOSPI close on 2 Oct 2026 **7,003.74** (official; 6,943.66 was an intraday print (about 10:30 KST, in a file written at 10:56 KST)).
- BoK base rate **3.00%** (27 Aug 2026 vote 6–1).
- US 10y **5.29% = highest close since May 2002** (not "19 years").
- Brent $127 / $114 are Dated spot; front-month futures were $118.35 / $102.59.
- Taylor gap: −0.89 pp (central), not −1.4 pp.
- AMP Japan (Table I): factor column momentum 0.13, value 0.77, combination 0.88; P3−P1 column 0.09 / 0.79 / 0.78. Name the column.
- RMW β t-statistic: HAC −3.0.

**QUANTGEN codebase and governance sources (v1.1)**

| Item | Key facts used | Source |
|---|---|---|
| Application map and target architecture | Flet app (`main.py`); `core/ficc` {curves, swaps, bonds, fx, ratesim, structured, macro, insights, data}; `core/quant` {history, garch, montecarlo, risk, optimize, signals, backtest, insights, gsq}; `core/engine` {runtime DISARMED→ARMED→HALTED, feed, evaluator, orders = simulated order book with no broker path, state}; `core/rules` {model, validation, store}; `core/skills` {72-entry manifest, runner, workflows}; `core/markets`, `core/calendars`; `config.py`; providers; `tests/run_all.py` hermetic; `docs/` | AR §1.1 |
| Vol backtest gate B5 | Rolling-origin VaR95 exceedance within ±2 binomial SE of 5% over ≥ 200 origins and PIT uniformity; GJR only if it passes | AR B5, B8, §4.1 |
| Read-only, timing, costs, gate | No order path; decide at the close of t, earn from t+1; per-side costs KRX ETF 3 / KRX stock 35 / US via KIS 50 / crypto 10 / futures 5 / FX 10 bp, all at 2×; nine steps; four verdicts; REVISE fixes | PP "Three rules", "The gate", "Fixed settings" |
| Strategy Lab record and E1 | 34 cards: 5 PASS / 11 REVISE / 18 REJECT / 0 INSUFFICIENT DATA; E1 OOS Sharpe 0.84 [0.47, 1.20] vs 0.95, p 0.75, max DD −15% vs −27%, kept as a descriptive sleeve | PP "The record", "Card E1" |
| Quant Lab self-grading | GARCH-t on SPY: 6.6% breaches, PIT p 0.003 → REJECT; GJR 6.6%, PIT p 0.014; skewed-t 5.2% (SPY), 6.3% (KODEX 200), 5.8% (bitcoin), withheld. t-quantile (fan-tail) form; UNVERIFIED until `docs/vol_backtest.py` and its seed are published | PP "The lab grades itself" |
| Net-of-cost and strict-timing golden values; protective checks; B5-style estimator check | See §9.3 and §8.9 | R4b (`scripts/r4b_golden_net.py`) |

**Quant Council sources (v2.0).** Notes are under `research_notes/QUANTGEN macro overlay research/`; scripts and results are under `quantgen_macro_data/`.

| Source | What it holds | Used in |
|---|---|---|
| `council/QC_COUNCIL_RESOLUTIONS.md` | The twelve resolutions with votes and final wording; the module table and build order; the red lines and how v2 respects them (§c); owner decisions D1–D5 (§d) | Quick start, §0.4, §1 (P11–P19), §5, §8, §10, §12 |
| `council/QC_modules.csv` | The 34 modules: name, package, change type, class, priority, milestone, acceptance test and source items | Changelog, §3.4, §9.0 |
| `council/QC_errata.csv`, `QC_errata_notes.md`, `QC_errata_verify.py` | Old-text → new-text errata (the 125 SPEC rows applied in place) and the 44 SPEC-REWRITE rows absorbed in v2.0 | Changelog; every section |
| `council/QC_ledger.csv`, `QC_docket.csv`, `QC_chair_votes_merged.csv` | The 361 docket items with each chair's vote, disposition, priority and target | Changelog source items |
| `council/QC_P_professors_chair.md`, `QC_E_executives_chair.md`, `QC_Q_quant_chair.md` | The chairs' positions, red lines and dissents | §1, §5, §8 |
| `council/00_ASPEC_ROUND_BRIEF.md`, `ASPEC_R1_qa_engineer.md`, `ASPEC_R1_data_engineer.md`, `ASPEC_R1_junior_developer.md`, `ASPEC_R1_risk_officer.md`, `ASPEC_R1_claude_critique.md`, `ASPEC_R1_synthesis.md` | Adversarial round 1: the brief, the four opponent reviews with their patch tables, the coordinator's binding rules C-1 to C-9, and the synthesis (deduplicated issues, decisions, verification, open points) | Round-1 changelog; §3.8, §6, §7.1, §8.10, §9.0a, §9.5 |
| `council/ASPEC_R2_qa_engineer.md`, `ASPEC_R2_data_engineer.md`, `ASPEC_R2_junior_developer.md`, `ASPEC_R2_risk_officer.md`, `ASPEC_R2_claude_critique.md`, `ASPEC_R2_synthesis.md` | Adversarial round 2: the four opponent reviews with their patch tables (the risk officer's §6 holds the indicative f row sets), the coordinator's rulings R2-C1 to R2-C7, and the synthesis | Round-2 changelog; R-06, R-21, R-22, R-23, §3.8, §6.6, §8.9, §9.0b |
| `council/ASPEC_R3_qa_engineer.md`, `ASPEC_R3_data_engineer.md`, `ASPEC_R3_junior_developer.md`, `ASPEC_R3_risk_officer.md`, `ASPEC_R3_claude_critique.md`, `ASPEC_R3_synthesis.md` | Adversarial round 3: three agreements, the risk officer's three majors with patches P3-01 to P3-03 and his notes, the coordinator's rulings, and the synthesis | Round-3 changelog; §3.8, §8.8, R-19, R-21, R-22, R-23, R-25, R-32, §9.4 |
| `QX_DLA_data_lab_protective_cards.md`; `scripts/dla_*.py`; `results/QX_DLA_*.csv` | The Korea and US vol-target cards on long history, the FORWARD-SIM legs, the drawdown ladder, staleness, and the post-patch recomputation (§7, `QX_DLA_postpatch.csv`) | R-06, R-07, R-11, R-12, R-19, R-29, §9.3.2, §11 |
| `QX_DLB_data_lab_estimators_regimes.md`; `results/QX_DLB_*.csv` | The estimator race (QLIKE and MSE MCS, B5), R-03 statistics, the trend axis, regime models, gate power and R-08 | R-03, R-08, R-16, R-28, R-30, §9.3.2, §10 items 11 and 27 |
| `QX_PX1_professors_methods_review.md`, `QX_PX2_professors_pricing_review.md`, `QX_EX1_executives_risk_review.md`, `QX_EX2_executives_trading_review.md` | The four cross-examinations of the QF papers, with their new points | §5, §10 items 29, 31 and 33, §11 |
| `QF1_market_making_microstructure.md`, `QF2_data_engineering_pit.md`, `QF3_statistical_validation_ml.md`, `QF4_portfolio_risk_construction.md`, `QF5_factor_multiasset_allocation.md`, `QF6_volatility_derivatives.md`, `QF7_methods_regimes_curricula.md` | The seven QF audits (A), module proposals (M) and claims (C) | Throughout: the source items of every module |
| `results/QF3_dnb_evidence_classes.csv` (`scripts/qf3_dnb_classes.py`) | The 53 bootstrapped variants behind the DO-NOT-BUILD list: 7 harm, 12 null, 28 inconclusive, 6 benefit | §10.1 (basis B) |

*End of specification.*
