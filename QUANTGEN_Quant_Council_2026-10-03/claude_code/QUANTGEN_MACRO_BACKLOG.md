# QUANTGEN — Macro Backlog (v2.0, Quant Council edition)

**As of:** 2026-10-02 (Asia/Seoul).
**Companion to:** `QUANTGEN_MACRO_INTEGRATION.md` v2.0, adversarial review complete (the spec; its rule and module numbers follow `council/QC_modules.csv`). v1.2 is kept unchanged as `.v1.2_BACKLOG_backup.md`, and v1.0 as `.v1.0_BACKLOG_backup.md`.
**Council sources** (`research_notes/QUANTGEN macro overlay research/council/`): `QC_COUNCIL_RESOLUTIONS.md` (resolutions, the council's owner decisions D1–D5, settling tests, red lines), `QC_ledger.csv` (361 items with final classes), `QC_modules.csv` (the 34 SPEC v2.0 modules) and `QC_errata.csv`. Appendix C logs the round. The spec's adversarial review is in `council/ASPEC_*.md` (summary: `ASPEC_DEBATE_SUMMARY.md`).
**Owner decisions:** the canonical values of D1–D6 are the spec's owner-decision registry (its Quick start table; `owner_decisions.D<n>` in spec §7). This file does not restate them (§1.6).

---

## Changelog: v2.0 — aligned with spec after adversarial review (rounds 1–4; round 4 a confirmation, with two clarifications applied)

The spec's adversarial review (`council/ASPEC_*.md`; rulings C-1 to C-9, R2-C1 to R2-C7, R3-1 to R3-3) changed no backlog item's evidence, settling test or priority. Its round-2 and round-3 syntheses flagged §1.6 as out of line with the spec. This alignment:
- **Owner decisions.** §1.6 now covers D1–D6 and references the spec's canonical owner-decision registry instead of restating values; the options, evidence and consequences stay, and an option the council voted for is marked "the council's choice". D6, the CDaR-guard calibration, is added; its default rule is frozen with the gate package (R2-C2). The header, §1's reading notes, ST-10, §1.7's CDaR row, §6.10, §8, Appendix Q.2 and Appendix C.4 point to the registry in the same way.
- **The Korea card (R2-C1).** §1.7's Korea row, §7 question 13 and the R-06 rows of the council queue (§1.2, CQ-01 to CQ-04, whose US rows enter the family-wide reading of f) state the spec's expectation: on current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build, and no convention may be changed to rescue it.
- **Open implementation tasks.** The spec's §9.4 items 15–17 are listed at the end of §1.7, and §8 points to them.

## Changelog v1.2 → v2.0 (Quant Council)

The Quant Council round (QF audit papers → QX cross-examinations and data labs → QC council) ruled on 361 items. This edition carries those rulings into the backlog. Evidence numbers carried from v1.2 are unchanged unless a council erratum corrected them. Every new number is quoted from the council files, the data labs or the QF papers, and its source is named next to it.

1. **Starting point.** The base is v1.2 plus the 66 BACKLOG `REPLACE` rows of `QC_errata.csv`, all applied; one of them deletes the Ilmanen "30%" row of §6.6 (QCE-225). 41 corrected texts stand (40 verbatim plus the QCE-225 deletion). The other 25 sit in sections this edition or its spec alignment rewrites: BL-S01, BL-S02, BL-C04, BL-C10, BL-G03, BL-G04, the §5 rows BL-D03, D04, D13 and D14, and §8, plus §7 question 13 (QCE-230), which the spec alignment rewrote. Their corrected figures are carried into the new text, and no superseded v1.2 text returns. The four BACKLOG `SPEC-REWRITE` rows are absorbed in this edition:
   - **QCE-170:** BL-S01 and BL-S02 move to the failure archive (§6.7);
   - **QCE-200:** new research items. The regime-engine head-to-head, the Korean cross-asset futures sleeve and the GMM scenarios are all deferred; calm-state reversal goes to the owner (§1);
   - **QCE-213:** BL-G01's settling test and BL-C04's race are rewritten around SPEC v2.0 R-30's staged estimator gate;
   - **QCE-236:** Appendix Q.2 #1, #3 and #4 are answered.
2. **§0 Status board (new).** Every BL item is re-statused against the ledger. Of the 46 research and integration items:
   - 2 are RETIRED;
   - 2 are RESOLVED;
   - 2 stay CLOSED;
   - 4 MOVED into SPEC v2.0;
   - 1 is an OWNER-DECISION;
   - 1 is record-only;
   - 34 remain OPEN.

   The 20 data items are carried into §5.
3. **§1 Council queue (new; it replaces the v1.x FORWARD-SIM → re-gate queue).** It holds 22 ledger items: 7 VALID-SHADOW, 3 CONTESTED, 9 CONTEXT-ONLY and 3 OWNER-DECISION. Each comes with:
   - its votes (P / E / Q), data-lab verdict and focus;
   - a settling test, giving data, window, metric, threshold and owner.

   §1 also sets out the five owner decisions D1–D5 (options, defaults and consequences) and lists the other settling tests the council named.
4. **Retired.** BL-S01 (the USD/KRW leg, R-11) and BL-S02 (the US rates leg, R-12) leave the re-gate queue on their long-history REJECTs (§6.7):
   - S1: 54 strict-H.10 and 74 value-timing onsets;
   - S2: 71 onsets at every timing.
5. **Resolved and moved.**
   - BL-C04 → R-30: COMB is the registered challenger; SMA20 stays acting.
   - BL-C10 → R-28: a FORWARD-SIM protective trend card for US and other non-Korean sleeves; Korea stays context.
   - BL-G01 → R-30.
   - BL-G02 → R-21–R-24 and R-34.
   - BL-G03 → R-29 and R-26.
   - BL-G05 → R-01.
   - BL-O08 becomes owner decision D3.
6. **Failure archive.** New sections §6.7–§6.11 add:
   - the two retired legs;
   - the demoted rules and the closed route: R-08 as a sizing rule, R-04's A-provisional route, max(SMA20, implied) sizing and the leveraged-ETF volume proxy;
   - the three INVALID council items (QF3-M6, QF7-M3, QF3-A1b);
   - the v1.2 mechanisms that failed as written;
   - the failures recorded in the QF papers' failure logs.
7. **§5 Data acquisitions v2.** 31 rows:
   - the 20 v1.2 rows, updated (needs that only S1 had are dropped; priorities follow the council's rulings);
   - 11 new rows: KRX official closes; calendars and regime tags; the 1926+ US daily file for R-29; KOSPI 200 futures; KTB and USD futures; US index futures; KOSPI 200 option-board snapshots and EOD history; VIX/VIX3M live snapshots; ETF baskets; the Korean call rate.
8. **§5a Data-quality log (new).** It records the 2-Oct intraday-print incident and its patch (`results/QF0_data_patch_20261002.csv`), plus the vendor caveats the QF members found.
9. **§7 and §8.**
   - Each open question carries a v2.0 status.
   - §7b adds 15 questions from the QF papers that the council left open.
   - The priority summary is rewritten.
10. **Rules for this file.** They now point to the v2.0 gate (R-21–R-25, R-34), the family trial ledger (R-23) and the card-header fields (R-26, R-32).
11. **Appendices.** Appendix C (the council log) is new, and Appendix Q.2 records the council's answers.

**Unchanged:**
- the backlog's priority scale (P1–P3);
- every OPEN item's settling test, which is now judged by the v2.0 gate;
- Appendix V and the Q.1 edit log, which are historical records and keep the values that matched at the time.

## Changelog v1.1 → v1.2 (independent QA)

No item's evidence, settling test or priority changed. An independent QA pass recomputed the headline numbers from the result files and the raw data, corrected labels and internal contradictions in the spec, this backlog and the research report, and recorded the open questions that need the owner's decision. Every edit is logged in **Appendix Q** (end of file), with its old text, new text, reason and source. In this file: the Appendix V row W40 (a malformed check) is corrected, BL-C06 and open question 5 carry period and cap labels, and Appendix Q is new.

## Changelog v1.0 → v1.1

v1.0 was written without knowledge of QUANTGEN's code. v1.1 adapts the backlog to the real application: a read-only research desk with a simulated order book, a nine-step gate with four verdicts, model cards and pre-registered costs. **No item's evidence or settling logic was weakened.**

1. **Read-only design.** QUANTGEN has no order path, so "shadow trading", "live" books and "KIS fill logs" no longer exist as such. Each was rewritten:
   - Forward-simulated books with timestamped artifacts replace the shadow and live books.
   - KIS quote snapshots replace fill logs, wherever quotes can answer the question.
   - Items that would genuinely need a broker path move to the new **§5c Blocked by read-only design**. That covers order routing, order cancellation, reconciliation of real positions, and slippage from real fills.
2. **Governance in gate terms.**
   - "Promotion", "kill" and "Tier A/B" are restated as card verdicts: PASS, REVISE, REJECT, INSUFFICIENT DATA.
   - The protective-overlay card class (spec §8.7) is the test for every de-risk item.
   - Settling tests now name the gate step or protective check they feed.
3. **Costs.**
   - Every settling test uses QUANTGEN's pre-registered per-side costs: KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10, futures 5, FX 10, and a 2× stress.
   - v1.0's "0.35% round trip" for Korea is replaced by 35 bp per side, i.e. 70 bp round trip.
   - **R4 numbers were gross.** R4b net values are added where they change a conclusion: BL-S01, BL-S02 and BL-C04.
4. **Timing.**
   - Strict H.15 timing for a US close decision is +2 business days. Under it the BL-S02 full-sample gross edge is −0.000.
   - Strict H.10 publication timing is added. Under it the BL-S01 gross edge is +0.001.
5. **New items BL-G01 to BL-G09** (§5b): the B5 vol-gate dependency, the protective-card harness, the cost-aware vol-target card, the timestamped KRW history, frozen test fixtures, the 18-indicator sheet mapping, the composite mapping, the futures instrument book, and a placeholder recording that a broker path is out of scope.
6. **Appendix V — v1.1 verification log.** 214 numbers from the v1.0 spec were traced to `results/*.csv` or to a note line: 201 MATCH, 11 TRACED-NOTE, 2 MISMATCH (both corrected in spec §2.2). Another 52 new numbers typed into v1.1 were self-checked against R4b, and all 52 match. The log also records the labelling and timing corrections that were not numeric mismatches.

---

This file holds everything that is **not** a module of SPEC v2.0:
- open research items;
- the council's queue and the owner's decisions;
- data still to acquire, and the data-quality log;
- the failure archive.

Each research item names:
- its v2.0 status (§0);
- its hypothesis;
- the panel, panels or council chairs that hold it;
- the evidence so far;
- why it is not in the spec;
- the exact test that would settle it, and the gate check that test feeds;
- the data still needed;
- a priority.

**Status vocabulary (v2.0):**

| Status | Meaning |
|---|---|
| **OPEN** | The item keeps its settling test, which runs as a model card under the v2.0 gate |
| **MOVED** | The substance is now a SPEC v2.0 module (named). Any residual task stays here |
| **RESOLVED** | The council settled the question. The answer is a SPEC v2.0 module, a FORWARD-SIM card or a context-only display |
| **CLOSED** | Settled before v2.0 (v1.2 and the council errata); kept for the record |
| **RETIRED** | Refused on evidence and moved to the failure archive (§6) |
| **OWNER-DECISION** | Waits on the owner (§1.6) |
| **Record only** | Nothing can be built in a read-only app |

**Priority scale:**
- **P1**: start now. Data logging can begin immediately, or the result changes a card in the spec.
- **P2**: next quarter.
- **P3**: opportunistic.

**Rules for this file:**
- **Every test here is a model card under the SPEC v2.0 gate.**
  - Its header is committed before the study run (R-32). The header declares the instrument book, notional, rebalance rule, no-trade band, cash convention and start band (R-26).
  - Every configuration run is logged and hashed in its family trial ledger, research phase included. Step 3 uses N_eff = max(N_clusters, N_equiv), and a card without a ledger hash is refused (R-23).
  - It is decided by one of two routes:
    - the nine-step gate for CARD-O. Step 3 there follows R-23: deflated ΔSR vs overlay-off ≥ 0.95;
    - the CARD-P gate v2 for de-risk items (R-21). Its parts are PC-1′ tail legs, PC-2 with a CI, a binding PC-3 and the do-no-harm cap.

    Both routes add R-22's conventions (objective market-own episodes, excess returns with local cash, a declared start band, regime lines), R-24's power/MDE line and R-34's timing-fragility gate. The package is adopted once, blind, before the first formal card run.
  - It is costed at QUANTGEN's pre-registered rates, with the 2× stress and the tick floor (R-26). There is no venue switch after results.
- **Forward records are falsification alarms only** (R-25). No forward record can raise a card's verdict.
- **Nothing in §6 (failure archive) may be re-proposed without new evidence** of the kind its "reopen only if" line names. This now includes the retired legs, the demoted rules and the INVALID council items (§6.7–§6.11).
- **Gross and net.**
  - Numbers marked "R4" (and all earlier rounds) are **gross** of costs.
  - "R4b" marks v1.1's net-of-cost or strict-timing recomputation (`results/R4b_golden_values_net.csv`).
  - "DL-A" / "DL-B" (test IDs DLA-…, DLB-…) are the council's two data labs (`QX_DLA_…`, `QX_DLB_…`). They ran after the 2-Oct data patch.
  - "Share" is the fraction of paired block-bootstrap resamples in which the rule beats its base.
- **Abbreviations.**
  - "N-xx" refers to the R4 neural-link nodes.
  - "PC/PX/PR-P" are professor-panel items; "EC/EX/ER-E" are executive-panel items.
  - Council IDs (QF1-A3, QF5-M2, X-EX2-N5, …) are rows of `council/QC_ledger.csv`.
  - Votes are written P / E / Q: the Professors', Executives' and QF chairs.
  - "R-xx" is a SPEC v2.0 rule or module.
  - "spec §x" in text carried from v1.x points to SPEC v1.2.
- **Two priority scales.**
  - Backlog rows use the backlog scale above (P1–P3).
  - Council-queue rows (§1) carry the council's own priority (P0–P2). It ranks SPEC v2.0 work and is not the backlog scale.
- **Read-only.** QUANTGEN never places orders. "Forward record" means the simulated order book's forward-running books in `core/engine`, with timestamped `macro_state` and `overlay_decision` artifacts.

---

## 0. Status board v2.0 (every BL item re-statused against the council ledger)

**Counts.** The board covers 46 research and integration items:

| Status | Items | Which |
|---|---|---|
| OPEN | 34 | Listed below |
| MOVED | 4 | BL-G01, G02, G03, G05 |
| RETIRED | 2 | BL-S01, BL-S02 |
| RESOLVED | 2 | BL-C04, BL-C10 |
| CLOSED | 2 | BL-C12, BL-U04 |
| OWNER-DECISION | 1 | BL-O08 = D3 |
| Record only | 1 | BL-G09 |

The 20 data items (BL-D01–D20) are carried into §5, which now has 31 rows. The council's own open items (22) are in §1.

| ID | Item | v1.2 | v2.0 status | Where it lives now | Council items |
|---|---|---|---|---|---|
| BL-S01 | USD/KRW leg (S1) | P3, refusal book | **RETIRED** → §6.7 #30 | R-11 RETIRED: labelled, display-only refusal book | QF2-A8, QF2-M8, QF4-A3, QF3-A24 |
| BL-S02 | US rates-stress leg (S2) | P3, refusal book | **RETIRED** → §6.7 #31 | R-12 RETIRED: labelled, display-only refusal book | QF2-A7, QF2-M7, QF3-A24, QF4-A18 |
| BL-C01 | D&M floor | P2 | **OPEN · P2.** Informs only R-04's floor in the specification book | R-04 DEMOTED | QF5-A3, QF5-M6 |
| BL-C02 | Reversal in fast stress | P1 | **OPEN · P1.** Waits on the milestone-1 KIS quote check | R-26 stress-cost line (reported, not gated); R-27 fills | QF1-A5, A7, A12, A13, A25 |
| BL-C03 | Credit spreads | P3 | **OPEN · P3** | — | — |
| BL-C04 | Vol-estimator speed, implied vol | P2 | **RESOLVED** | R-30 (COMB the registered challenger; SMA20 acting); R-13 (implied vol as context) | QF6-M1, M2, A1–A4, A15, A19, A20; QF7-M2, A22; X-PX1-N6; QF6-M6 |
| BL-C05 | Korea discrete flags, time-stops | P2 | **OPEN · P2** | R-10 keeps no gross rule; R-27 prices stress-day fills | QF1-A14 (evidence) |
| BL-C06 | Foreign and institutional flows | P1 | **OPEN · P1** (logging) | R-13 context_log (BL-D01) | — |
| BL-C07 | Rate- and inflation-conditioned de-risking | (a) P2, (b) P2, (c) P3 | **OPEN** (unchanged) | R-18 trigger (i) would govern (b) | — |
| BL-C08 | Duration tilts under real-rate shocks | P3 | **OPEN · P3** | — | — |
| BL-C09 | Policy-communication states | P3 | **OPEN · P3** (log only) | — | — |
| BL-C10 | Trend axis for market gross | P3 (band) | **RESOLVED** | R-28 FORWARD-SIM for US and other non-Korean sleeves; Korea CONTEXT-ONLY; the band is a logged trial | QF5-A10, QF5-M2 (§1), QF5-A8, X-PX2-N1 |
| BL-C11 | Oil-shock event rule | P3 | **OPEN · P3** | — | — |
| BL-C12 | Evidence tier for prior-backed effects | closed | **CLOSED** (uniform hurdle) | R-23 (step 3) | QF3-A18, QF5-A2, QF5-M6 |
| BL-C13 | Yen shock, Japanese exporters | P3 | **OPEN · P3** | — | — |
| BL-C14 | Positioning-based crowding cut | P3 | **OPEN · P3** | R-13 logs the inputs (context) | QF4-A23, QF4-M8 (§1) |
| BL-O01 | Regional momentum priors | P2 | **OPEN · P2.** Re-scoped to admissibility | R-15 | QF5-M4, QF4-M5 |
| BL-O02 | Momentum size-down on decision days | P3 | **OPEN · P3** | — | — |
| BL-O03 | Korean supply screens | P2 | **OPEN · P2** | — | — |
| BL-O04 | Buyback-and-cancel feature | P3 | **OPEN · P3** | — | — |
| BL-O05 | Political-shock flag | P3 | **OPEN · P3** | — | — |
| BL-O06 | Stock-level microstructure | P3 | **OPEN · P3** | — | — |
| BL-O07 | Factor-momentum gate | P3 | **OPEN · P3** (confirmed) | — | QF5-A25 |
| BL-O08 | Calm-state reversal down-weight | P3 | **OWNER-DECISION D3** (stays P3) | §1.6 D3 | QF5-M10, QF5-A13 |
| BL-O09 | Macro priors on real-time vintages | P3 | **OPEN · P3.** Vintage storage moved to R-13 | R-13 (first print, current value, vintage date) | QF2-M6, QF2-A19, QF7-A24 |
| BL-O10 | KOSPI–China partial correlation | P3 | **OPEN · P3** | — | — |
| BL-O11 | Dollar gate for EM/Asia momentum | P3 | **OPEN · P3** | — | — |
| BL-O12 | E5's system-level limits | P2 | **OPEN · P2** | — | — |
| BL-O13 | Stock–bond regime variable, JPY hedge | P3 | **OPEN · P3** (risk model only) | R-09 | X-EX1-N6 |
| BL-O14 | Other professor items | P3 | **OPEN · P3.** The change-point exit feature moves to the context log | R-18 research log | QF7-M4 (§1) |
| BL-U01 | Korea leverage / flow / semis-cycle state | P1 | **OPEN · P1** | R-13 logs the inputs | QF1-M5, QF4-M8 (§1); QF1-A22, A23 |
| BL-U02 | Korea factor priors | P1 | **OPEN · P1** | R-15: Korea reversal prior 1 (UNVERIFIED) until this runs | QF5-A14, QF5-A8 |
| BL-U03 | Macro-surprise → next-open volatility | P2 | **OPEN · P2.** First step runnable now | R-10 measurement | QF7-A28 |
| BL-U04 | Overnight information, open-to-close | closed | **CLOSED** (tested) | — | QF1-A11, QF2-A9 |
| BL-U05 | Drivers for markets without a sleeve | P3 | **OPEN · P3** | — | — |
| BL-U06 | Crypto microstructure | P3 | **OPEN · P3** | R-17 crypto clock | QF2-M9 |
| BL-U07 | Why the gold level broke | P3 | **OPEN · P3** (context) | — | — |
| BL-G01 | B5 volatility-gate dependency | P1 | **MOVED** → R-30 (residual task P2) | R-30 Stage 1; R-16 envelope | QF6-A20, QF6-A25, QF6-M1, X-PX1-N6 |
| BL-G02 | Protective-card harness | P1 | **MOVED** → R-21–R-24, R-34 | M7, frozen before the first card run | QF3-A5, M1, M2, M3, M7, M8; X-PX1-N2, N3; X-EX1-N4; QF2-M2; QF4-M6 |
| BL-G03 | Cost-aware vol-target cards | P2 | **MOVED** → R-29 (FORWARD-SIM) and R-26 | §1 ST-01 | QF1-A1, A10, M2; QF4-A2, A21; QF5-A23; QF6-A8, M5 |
| BL-G04 | Timestamped USD/KRW history | P3 | **OPEN · P3** (formality) | BL-D13 | QF2-A8, QF2-M8, QF4-A3 |
| BL-G05 | Frozen fixtures | P1 | **MOVED** → R-01 | M1 (T-FIX-01, T-PROV-01) | QF4-A12, QF6-M11, QF1-A24 |
| BL-G06 | 18-indicator sheet mapping | P1 | **OPEN · P1** (blocks M6) | — | — |
| BL-G07 | Composite-to-family mapping | P2 | **OPEN · P2** | — | — |
| BL-G08 | KOSPI 200 futures instrument book | P3 | **OPEN · P3.** The rule moved | R-26 granularity floor; R-06 KR futures line; notional declaration (D5) | X-EX2-N3 |
| BL-G09 | Broker path | none | **Record only** | — | — |
| BL-D01–D20 | Data acquisitions | P1–P3 | Carried into §5 v2, plus 11 new rows | §5 | — |

---

## 1. Council queue (new in v2.0; replaces the v1.x FORWARD-SIM → re-gate queue)

The council (round QC) classed 361 ledger items. Of these, 22 are neither built nor refused, and they wait here, each with a settling test:

| Class | Items | Meaning |
|---|---|---|
| VALID-SHADOW | 7 | Accepted, but runs only in the specification book or FORWARD-SIM until a named test passes or a sleeve exists |
| CONTESTED | 3 | The chairs split, or all three deferred |
| CONTEXT-ONLY | 9 | Logged or displayed; never acts |
| OWNER-DECISION | 3 | A principle change, a risk-appetite level or a product choice |

The v1.x §1 held BL-S01 and BL-S02. Both are retired to §6.7.

**How to read the tables:**
- **Votes** are P / E / Q (Professors', Executives' and QF chairs):
  - A = ACCEPT; AC = ACCEPT-WITH-CONDITIONS; R = REJECT; D = DEFER;
  - CX = CONTEXT-ONLY; PC = PRINCIPLE-CHANGE;
  - c = a consent item to which that chair raised no objection.
- **Lab** is the data labs' replication verdict.
- **Focus** counts how many of the 13 contributors raised or tested the item: QF1–QF7, PX1, PX2, EX1, EX2, DLA and DLB.
- **Pri** is the council's priority (P0–P2).
- **Owner** says who runs the test (Claude Code, with milestone and module). Where the decision is not a gate verdict, it also says who decides (the owner, D1–D6).

### 1.1 Settling tests

| ST | Question | Data | Window | Metric | Threshold | Owner |
|---|---|---|---|---|---|---|
| **ST-01** | US index-futures vol target, MACRO-R06-US-FUT (R-29) | Kenneth R. French daily Mkt-RF and RF (BL-D23; DL-A's fetch was refused, HTTP 403). Futures book at 5 bp. Objective ≥ 15% S&P episodes | 1926-07 → 2026-08; decade-spaced starts. The 1990–2007 line is printed (≈ 0) | v2 CARD-P (R-21): PC-1′ (ΔES95 of 21- and 126-session returns vs S, one-sided stationary-bootstrap p ≤ 0.10, blocks ≥ 250 sessions), PC-2 with a CI, PC-3. Judged under the blind v2 package | PC-1′ holds at 1× and 2×, and the card passes at ≥ 80% of decade-spaced starts. Promotion to BUILD-AS-INSURANCE also needs either a US sleeve in which one Micro ES (≈ ₩52m) is ≤ ~5% of declared notional (≈ ₩1bn), or another executable line the owner declares (D5) | Claude Code · M8 (R-29). Promotion: owner (D5) |
| **ST-02** | Protective trend card, monthly SMA10m 0.5× (R-28) | French monthly US market (local, 1927+). Each non-Korean sleeve's own official closes. A pooled-onset rule declared before any run | US 1927–2026; a PASS needs pre-1970 data (DLB-T3c). Each sleeve's longest history | Increment stacked on the vol target (ΔES and ΔMDD). v2 CARD-P at 5 and 50 bp. GJR-null percentile and snooping haircut printed. No Sharpe claim | Increment ≥ 3 pp, plus a formal v2 PASS. Tier A via the pooled-onset rule (the US alone has 45 de-clustered onsets). BUILD-AS-INSURANCE only once such a sleeve exists | Claude Code · M8 (R-28). Sleeve: owner (D5) |
| **ST-03** | COMB = ½(GJR-t + log-HAR-range) as the estimator challenger (R-30) | KOSPI and US daily OHLC with open-quality flags. Range proxies: overnight² + Garman–Klass (KOSPI); Parkinson (US, because ^GSPC opens are unreliable before ~2008). Formal cards use KRX official closes | Out of sample: 2001-01-02 → 2026-09 for KOSPI (6,342 origins) and 1995-01-03 → 2026-09 for the US (7,985 origins). 2016–26 and 2026 printed separately | R-30's staged gate. Stage 1: calibration at h = 21 (FHS exceedance, 21-day fan PIT, Christoffersen CC). Stage 2: 90% QLIKE MCS at h = 21. Stage 3: vol-of-vol, ΔMDD and PC-2, net of turnover at the declared book | Passes Stage 1; is inside the MCS; has the lowest vol-of-vol with ΔSR non-inferior (overlapping CIs are ties and go to the simplest surviving model). Adopted on a card only as a counted revision that passes the full v2 CARD-P. ETF and futures books only; fails closed to SMA20 | Claude Code · M3 (R-30); the card switch is a counted revision at M7 |
| **ST-04** | Jump-model regime engine (SJM, λ = 50) | Official daily closes of the S&P 500, STOXX50E and TWII (the last two never used in design). λ ledger with ≥ 5 values | 2027–28, forward, pre-registered | SJM50 vs BAND200 vs VT15 at 50 bp: ΔMDD and turnover | An SJM card may be proposed only if its ΔMDD is ≥ the band's at no more turnover (ties go to the band). Korea is excluded. Nothing acts or is displayed in v2 | Claude Code: register in the family ledger now; forward books in 2027–28 |
| **ST-05** | Korean cross-asset futures trend sleeve | KIS KOSPI 200, KTB 3y/10y and USD futures history (BL-D24, BL-D25), with declared roll calendars. Professors' design: a 1/3/12-month blend at 10% vol | 2006–26, at 5 bp | Correlation with KOSPI; ΔMDD of KOSPI plus the sleeve; sign in the KOSPI bear markets | Correlation < 0.3; ΔMDD ≥ 3 pp; positive in ≥ 3 of 5 KOSPI bears | Claude Code, after the data are acquired; verdict by the v2 gate |
| **ST-06** | GMM scenario regimes for the Quant Lab | Replay library with regime metadata (R-16, QF4-M9). GMM fits seeded and frozen | 2008–26 | 99% ES coverage of the scenarios vs the replays; label agreement across refits | GMM beats the replays on 99% ES coverage, with ≥ 90% label agreement across refits. Never shown as a current regime | Claude Code · M9 (R-16), after the replay library |
| **ST-07** | Can the leverage, flow and crowding context ever act? | KOFIA margin debt; KRX single-stock and index leveraged/inverse ETF AUM and value traded (BL-D02); investor flows (BL-D01); absorption ratio and turbulence | Daily, 2015–2026 or from the earliest available date. The 16-Jul-2026 rule break is flagged | BL-U01: lead over KOSPI rv21, and the Korea vol target's ΔMDD by episode. BL-C14: lead over own-factor vol, and the increment to vol-scaled sizing | BL-U01: leads rv21 by ≥ 5 days and improves VT20's ΔMDD in ≥ 3 Korean episodes, with no episode above 50%; any multiplier needs ≥ 30 events and Tier B bounds [0.5, 1.0]. BL-C14: leads by ≥ 5 days in ≥ 3 of 5 episodes and adds to vol-scaled sizing | Claude Code · M6 (R-13 logging); tests BL-U01 and BL-C14 |
| **ST-08** | Turbulence as a stressed-covariance input | Turbulence and absorption ratio; the stock–bond-regime input (X-EX1-N6, R-09) | Not named by the council; declare it on the header | Not named; declare it on the header | Must beat the stock–bond-regime input in a pre-registered test. Until then display only, never a multiplier | Claude Code (R-09 risk model) |
| **ST-09** | Implied volatility as a sizing input | VIX and VIX3M at 16:00 ET (BL-D29); KOSPI 200 model-free implied variance at 15:30 KST (BL-D27); VKOSPI history (BL-D12) | About two years of logged KOSPI 200 option boards for the Korean test (QF6) | Only inside HAR-IV, and only through R-30's staged gate (as ST-03) | HAR-IV must win the race. max(SMA20, implied) stays retired (§6.8 #34) | Claude Code · M3/M6 (R-30, R-13) |
| **ST-10** | D1: Korea concentration template | n = 1 (July 2026). For information only: forward-simulated CARD-P books of the templates on KRX stock-level data (KIS), with pre-registered episodes (QF4; EX2) | — | — | No statistical settling test. The template is risk appetite, and one episode cannot choose | Owner (D1). Default in force: the spec's owner-decision registry (§1.6) |
| **ST-11** | D3: calm-state reversal down-weight | KRX stock-level reversal (KIS, BL-D03), net of 35 bp plus the 0.20% sell tax. Calm = VIX ≤ 20 | 2010–17 and 2018–26 | Reversal at 0.5× in calm vs 1.0× | One-sided p ≤ 0.10 in both sub-periods | Run: Claude Code. Decision: owner (D3). The council recommends keeping design principle P3 |

### 1.2 VALID-SHADOW — 7 items

| CQ | Item | Title | P / E / Q | Lab | Focus | Pri | Lives in | Test |
|---|---|---|---|---|---|---|---|---|
| CQ-01 | QF1-A1 | US 50 bp REJECT is an instrument fact; the futures-line card is registered separately | AC / AC / AC | DLA-U2 PARTIALLY REPLICATED; DLA-U1 REPLICATED | 12 | P1 | R-06 US relabel; R-29 | ST-01 |
| CQ-02 | QF4-A2 | US VT REJECT reflects the instrument book, not the rule | AC / AC / AC | DLA-U2 PARTIALLY REPLICATED; DLA-U3, DLA-U1 REPLICATED | 12 | P1 | R-06 US relabel; R-29 | ST-01 |
| CQ-03 | QF5-A23 | US 50 bp REJECT is instrument-specific | AC / AC / AC | DLA-U1 REPLICATED | 12 | P1 | R-06 US relabel; R-29 | ST-01 |
| CQ-04 | QF6-A8 | US VT at 50 bp: a slower or banded variant is a new card | AC / AC / AC | DLA-U2, DLB-T1h PARTIALLY REPLICATED; DLA-U1 REPLICATED | 12 | P1 | R-06 US; R-29 | ST-01 |
| CQ-05 | QF5-A10 | Trend axis wrongly filed as data-mined; the protective claim survives | AC / AC / AC | DLB-T3a REPLICATED; DLB-T3c, T3f PARTIALLY REPLICATED | 6 | P1 | R-28; BL-C10 | ST-02 |
| CQ-06 | QF5-M2 | Monthly SMA10m de-risk as a protective trend card | AC / AC / AC | DLB-T3a, T3b, T3e REPLICATED; DLB-T3f PARTIALLY REPLICATED | 6 | P1 | R-28; BL-C10 | ST-02 |
| CQ-07 | QF6-M2 | Range-based HAR and COMB as volatility challengers | AC / AC / AC | DLB-T1d CORRECTED | 11 | P1 | R-30 | ST-03 |

**Conditions the council attached:**
- **CQ-01 to CQ-04 (Resolution 2).**
  - The registered card stays **REJECT (instrument: US shares via KIS, 50 bp, daily)**: a book-specific REJECT, never "an artefact". Under v2's PC-1′ it would read INSUFFICIENT, and it is not re-run.
  - MACRO-R06-US-FUT (index futures, 5 bp, daily, SMA20, target 0.15, cap 1.0) is a new card and one more trial in the R-06 family ledger. It runs FORWARD-SIM in the specification book.
  - Monthly and banded 50 bp variants are logged trials, never rescues (DNB #23). The monthly variant is post hoc and INSUFFICIENT (GFC share 0.56–0.67).
  - **Evidence.**
    - DLA-U2: futures at 5 bp on 1990–2026 give +3.6 pp (2×: +3.2), p_ni 0.002, PASS. But only 11 of 44 quarterly starts PASS (9 REVISE, 24 REJECT); every start from 1994-11 to 2000-08 REJECTs; and 1990–2007 gives +0.3 pp.
    - DLA-U5: ΔES99 z 2.37; ΔES95 of 21-day returns z 1.85; ΔMDD bootstrap SD 7.8 pp.
    - DLB-T1h: on 1995–2026 at 5 bp, SMA20 gives +2.5 pp (REJECT), while GARCH +4.9, log-HAR +4.8 and COMB +3.9 pp PASS.
  - **Spec alignment (adversarial review; R2-C1).** These US rows (DLA-U1–U5, DLB-T1h) are seed rows of the R-06 family ledger and enter the family-wide reading of R-06 KR's selection factor (indicative f 2.87; spec §8.9, §9.5). For the Korea card, on current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build, and no convention may be changed to rescue it (§1.7).
- **CQ-05 and CQ-06 (Resolution 9).**
  - The rule is monthly SMA10m, with gross at 0.5× below trend from t+1, composed by `min()` with the vol target and the ladder.
  - The claim is "slow-bear protection via the volatility state". It is judged stacked on the vol target (≥ 3 pp), with the GJR-null percentile printed and the pooling rule declared first.
  - It is registered for US and other non-Korean equity sleeves, one card per sleeve (scope 2–1; the Executives' "US" is the first instance). Korea: CONTEXT-ONLY.
  - **Evidence.**
    - DLB-T3a: US 1927–2026 gives ΔSR +0.083 [0.019, 0.134], ΔMDD +15.9 pp, 45 onsets.
    - DLB-T3f: 94 of 94 variants keep ΔMDD ≥ 3 pp, but the Sharpe gain's deflated probability is 0.43–0.59.
- **CQ-07 (Resolution 3).**
  - Registered for ETF and futures books only, never the 35 bp stock book. Range proxies carry OHLC open-quality flags, with a fail-closed fallback to SMA20.
  - The vote is unanimous on registration. The default stays SMA20, 2–1: the Professors would make COMB the default for new cards.
  - **Evidence** (DLB-T1g): COMB cuts vol-of-vol by 22.2%, improves ΔMDD by 2.8 pp, and leaves ΔSR at −0.000 (KOSPI 2001–26, 3 bp).

### 1.3 CONTESTED — 3 items (new backlog research items, QCE-200)

| CQ | Item | Title | P / E / Q | Lab | Focus | Pri | Lives in | Test |
|---|---|---|---|---|---|---|---|---|
| CQ-08 | QF5-M8 | Korean cross-asset futures trend sleeve | D / D / D | not tested | 3 | P2 | Backlog | ST-05 |
| CQ-09 | QF5-M9 | GMM regime scenarios for the Quant Lab | D / D / D | not tested | 6 | P2 | Backlog, behind R-16's replay library | ST-06 |
| CQ-10 | QF7-M1 | Jump-model regime engine (SJM λ = 50) | D / R / D | DLB-T4c, T4e, T4f REPLICATED | 6 | P2 | Backlog; nothing in SPEC v2.0 (R-33 prohibits a regime state, acting or displayed) | ST-04 |

**Why each is contested:**
- **CQ-08.** All three chairs defer it: there is no local data, the sleeve needs rolls, and contract granularity matters for a small desk.
- **CQ-09.** All three defer it. The Executives' red line E1 binds the wording: no regime label is ever displayed.
- **CQ-10.** The chairs split on the destination: the Professors and QF defer it as research; the Executives REJECT it to the archive. Every chair agrees on the v2 outcome: no regime module and no regime state.
  - **Evidence** (DLB-T4c/T4e):
    - US SJM50 runs at 1.26 switches a year, with ΔMDD +13.9 pp but INSUFFICIENT (17 onsets). The protection is λ-robust (+12.8 / +13.4 / +13.9 pp at λ 25 / 50 / 100); the Sharpe effect is not.
    - KOSPI has no λ plateau (+2.3 / +3.1 / −0.7 pp) and fails PC-3.
    - BAND200 dominates on the full US sample (+16.5 vs +13.9 pp; ΔSR +0.107 vs +0.056 at 50 bp) and in the clean 2024–26 holdout.
    - λ = 50 was learned on the S&P, DAX and Nikkei over 1990–2023 (X-PX1-N5).
  - **QF's counterpoint:** in the clean FTSE and HSI holdouts, SJM beat the band (+11.6 / +7.5 vs +6.8 / +5.1 pp).
  - **The record (QF7-A5, VALID-ERRATA, unanimous).** Jump models are not a failed class; unpenalised Markov switching failed. §6.4 #19 now says so (QCE-223), and the build implication is declined (Resolution 10). The Korea exclusion reason is no λ plateau, late flags and a PC-3 failure, not the guard-driven −4.7 pp.

### 1.4 CONTEXT-ONLY — 9 items (logged or displayed; never act)

| CQ | Item | Title | P / E / Q | Lab | Focus | Pri | Lives in | Test |
|---|---|---|---|---|---|---|---|---|
| CQ-11 | QF1-M5 | Leveraged-product AUM monitor as context only | CX / CX / CX | not tested | 7 | P2 | R-13; BL-U01 data | ST-07 |
| CQ-12 | QF4-A23 | Crowding stays context; log margin debt and leveraged-ETF AUM | c / c / c | not tested | 7 | P2 | R-13; BL-C14 | ST-07 |
| CQ-13 | QF4-M8 | Korea leverage and crowding indicators as context | CX / CX / CX | not tested | 7 | P2 | R-13 context_log | ST-07 |
| CQ-14 | QF5-M7 | Turbulence index as a stressed-covariance input | CX / AC / CX | not tested | 7 | P2 | R-13 display; R-09 | ST-08 |
| CQ-15 | QF6-M6 | Live-timed implied-vol inputs as context | CX / CX / CX | not tested | 5 | P2 | R-13; max(SMA20, IV) retired from R-06 | ST-09 |
| CQ-16 | QF6-M10 | Variance risk premium as context | CX / CX / CX | not tested | 5 | P2 | R-13 context_log | None named: context permanently |
| CQ-17 | QF7-M4 | BOCPD change-point flag for scale breaks | AC / D / AC | not tested | 4 | P2 | R-18 research log | None named: log only |
| CQ-18 | QF7-M7 | Curriculum-based reading list for the owner | AC / CX / AC | not tested | 3 | P2 | `docs/` reading list | None (documentation) |
| CQ-19 | X-EX2-N6 | KRW hedge credit as a display | CX / CX / CX | not tested | 4 | P2 | R-09 display | None named: display only |

**What each logs, and why it never acts:**
- **CQ-11 to CQ-13: the Korea leverage and crowding inputs.** They log, with timestamps:
  - KOFIA margin debt;
  - index and single-stock leveraged-ETF AUM and value traded;
  - the leveraged share, the absorption ratio and turbulence.

  The 16-Jul-2026 rule break is flagged. Every proxy tested so far was negative: the absorption-ratio shift gave t −0.19, the leveraged share had the wrong sign, and the volume proxy failed out of sample (DM t ≤ 0.73; §6.8 #35). Any card would need ≥ 30 onsets.
- **CQ-14: turbulence and the absorption ratio.** Display only, never a multiplier. Two chairs class it CONTEXT-ONLY; the Executives accept it with the same display-only conditions.
- **CQ-15: implied vol.**
  - Logged live: VIX/VIX3M at 16:00 ET and KOSPI 200 MFIV at 15:30 KST.
  - The implied-vol gain is pre-2008 only (0.615 vs 0.614 since 2010), and VKOSPI is not available at 06:30Z.
- **CQ-16: the VRP.** Its out-of-sample R² is negative (US 1-month −10.7%; KOSPI −4.7%).
- **CQ-17: BOCPD.**
  - It uses a declared hazard (1/250) and prior. It is never acting, never displayed as a regime state, and has no R-18 dependency. The Giacomini–Rossi breakdown is printed on card forecasts.
  - The Executives' DEFER and their red line E1 bind the wording.
- **CQ-18: the reading list.** Documentation only. It carries the KWH preface caveat, Sheppard ch. 8 and tick-loss scoring.
- **CQ-19: `fx_hedge_credit`.**
  - It gives no credit while the trailing KOSPI–KRW correlation is ≥ 0 (it was +0.05 on 2 Oct). It has no gross effect and no card.
  - The won failed as a hedge in Jul-2026, and the trailing state has no forecasting power.

### 1.5 OWNER-DECISION — 3 items

| CQ | Item | Title | P / E / Q | Lab | Focus | Pri | Lives in | Test |
|---|---|---|---|---|---|---|---|---|
| CQ-20 | QF4-A10 | The Korea pair-cap trigger was calibrated inside the regime it targets | AC / AC / AC | not tested | 5 | P1 | D1; R-07 | ST-10 |
| CQ-21 | X-EX2-N5 | Korean fund concentration rule as a template option | AC / A / A | not tested | 5 | P1 | D1; R-07; R-27 limit-lock flag (built) | ST-10 |
| CQ-22 | QF5-M10 | Calm-state reversal down-weight (principle change) | R / PC / PC | not tested | 5 | P2 | D3; BL-O08 stays P3 | ST-11 |

### 1.6 The owner decisions (D1–D6)

**Values live in the spec, not here.** The canonical statement of D1–D6, their defaults in force and their rules-store keys is the spec's owner-decision registry: its Quick start table, mirrored as `owner_decisions.D<n>` in spec §7 (procedure and evidence in spec §8.10). Implement and display the registry's values; an owner ruling changes the registry only. This section keeps the options, the evidence and the consequences. Where an option is marked "the council's choice", that records the council's vote (`QC_COUNCIL_RESOLUTIONS.md` §d), not the value in force. The council routed D1–D5 to the owner; D6, the CDaR-guard calibration, was added by the spec's adversarial review, with its default rule frozen with the gate package (R2-C2).

#### D1 — Korea concentration template (risk appetite)

- **Items:** QF4-A10 and X-EX2-N5 (CQ-20, CQ-21); QF4-M4.
- **Already decided** (Resolution 12; R-07):
  - the caps apply on look-through, computed daily from the ETF baskets, with leveraged products at × L;
  - the single-name cap is active: w_i − g·b̃_i ≤ 0.05 of NAV against the capped benchmark b̃;
  - a binding cap is met first by lowering the ETF line's weight;
  - the 0.45 → 0.35 trigger is dropped;
  - the semiconductor cap of 0.50 is unchanged.

| Option | Rule | Consequence at today's ≈ 51% pair share |
|---|---|---|
| (a) Domestic fund rule | Any name ≤ max(10%, its market-cap weight) | No overweight, and no concentration control beyond the benchmark |
| **(b) MSCI 25/50 — the council's choice** (Executives, QF; the Professors accept (a) or (b)) | A single name ≤ 22.5% after the buffer; names above 4.5% ≤ 45% in aggregate; reviewed quarterly and on breach | A public methodology, with no level calibrated inside the 2026 regime. The absolute gross-route bound 22.5 / 29.8 = 0.755 does not bind at vt 0.694, but the active single-name bound (at most 0.685) does, in both books (spec §8.10, §11) |
| (c) 35% pair cap | Samsung + SK hynix ≤ 35% of the Korea long book (the 0.45 trigger dropped) | A deliberate underweight of ≈ 16 pp |

- **Evidence (n = 1, so it cannot choose).**
  - July-2026 crash: −36.3% under 25/50, −33.9% under the 35% pair cap and −38.6% for KOSPI.
  - H1-2026: +95.2%, +86.6% and +101.1%.
  - The pair is ≈ 51% of KOSPI (51–54% by anchor) and 53.8% of KODEX 200 on look-through. It carries ≈ 75% of KOSPI's 63-day variance.
- **Also for the owner: the basket route.** It would give full Korea beta at the cap through a 35 bp ex-pair basket; QF4's worked example is ₩52.4m of KODEX 200 plus a ₩17.0m basket. The Executives would open this route only after a stock-book card passes and limit-lock flags exist.

#### D2 — Drawdown hard-stop level (risk appetite)

- **Items:** QF4-M3 (Resolution 6).
- **Already decided:** the re-arm sequence, `min()` composition and the time-boxed steps.

| Option | Level | Consequence (hard stop with the re-arm only; the Executives' check C2 on DL-A's curves) |
|---|---|---|
| **(a) −15% of book NAV — the council's choice** (Professors, QF; the v1.2 governance level) | A fixed % of NAV from the high-water mark since the last re-arm | KOSPI VT20, 1997–2026: 24 HALTs; Sharpe 0.457 vs 0.46 with no ladder; MDD −56.4% vs −45.3%. US VT15, 1990–2026: 13 HALTs; Sharpe 0.584 vs 0.592; MDD −46.3% vs −50.3% |
| (b) −1.5 σ_book (Executives) | σ_book is the book's declared target vol; failing that, trailing-756 realised vol frozen at each re-arm. That gives −15% for a 10%-vol book, −30% for KOSPI VT20 and −22.5% for US VT15 | KOSPI VT20 at −30%: 6 HALTs; Sharpe 0.471; MDD −44.8%. US VT15 at −22.5%: 4 HALTs; Sharpe 0.589; MDD −53.0% |

- **Either way** the hard stop is a governance review event, not a protection claim.
- **On a single-market Korea book,** option (a) fires about four times as often, and on the one path tested it deepened the drawdown.

#### D3 — QF5-M10: calm-state reversal down-weight (principle change)

- **Items:** QF5-M10 (CQ-22); BL-O08; QF5-A13.
- **The principle at stake.** Using a VIX level as a mean gate on the reversal family would break design principle P3: macro and stress variables size risk, never set direction.
- **Evidence.** It is US, gross and one regime: VIX ≤ 20 gives −1.15% a year. There is no Korean net-of-cost test. The Professors REJECT the change; the Executives and QF route it to the owner as a principle change. All three recommend against adopting it in v2.
- **Options:**
  - (a) Keep design principle P3. **This is the council's recommendation** (the default in force: the spec's registry).
  - (b) Reopen only after ST-11 passes: a KRX stock-reversal test net of 35 bp plus 0.20% tax, in which 0.5× in calm beats 1.0× at one-sided p ≤ 0.10 in both 2010–17 and 2018–26.
- **Consequence.** BL-O08 stays at backlog priority P3 until then (QF5-A13).

#### D4 — Book-level false-demotion budget (risk appetite)

- **Items:** QF3-M5, QF5-M3, X-EX1-N3 (module R-25).
- **Default:** set by the council; its value is the spec's registry entry (`monitoring.false_demotion_budget_per_year`; mechanics in spec §8.8 and R-25), not restated here.
- **Options:** keep the default, or tighten it. The owner may tighten it.
- **Consequences (context).**
  - Twelve forward months can detect only catastrophic decay: the calibrated 2.5% thresholds are −0.20, −0.39 and −0.73 Sharpe.
  - A CUSUM needs about 40 months to detect flat performance.
  - The triggers as written fired in 30–69% of years.
  - Operational and integrity triggers (a lag-audit violation, an acting-parameter edit outside a revision) demote immediately, whatever the budget.

#### D5 — Whether, and on which line, to run a US sleeve (product choice)

- **Items:** QF1-A1, QF4-A2, QF6-A8 (CQ-01 to CQ-04), QF5-M2 (CQ-06); modules R-28 and R-29.

| Option | What it requires | Consequence |
|---|---|---|
| (a) Index futures | Micro ES ≈ ₩52m a contract. It needs a declared notional of about ₩1bn or more, so that one contract is ≤ ~5% of the sleeve | Tracking error 7.5%/yr at ₩0.1bn vs 0.7% at ₩1bn. R-29 can be promoted once ST-01 passes, and R-28 once ST-02 passes |
| (b) A KRX-listed S&P ETF line (the Executives' alternative) | Only with FX and NAV lag modelled. DL-A's "KRX ETF 3 bp" US book is a cost bucket that models neither FX, NAV lag nor KST trading hours | A new instrument book, declared before any run (no venue switch after results) |
| (c) No US sleeve | — | R-28 and R-29 remain FORWARD-SIM records and never enter the recommended book |

- **Default:** the council set none; the default in force is the spec's registry entry (`sleeves.US.line`).
- **The same notional declaration** also decides whether the Korea card may use the futures line instead of the ETF line (X-EX2-N3; BL-G08). Mini KOSPI200 is ≈ ₩56m: one contract is 56% of a ₩0.1bn sleeve (7.5%/yr tracking error) and 5.6% of a ₩1bn sleeve (0.7%/yr).

#### D6 — CDaR-guard calibration (gate sub-point; added by the spec's adversarial review)

- **Items:** X-EX1-N4; Resolution 4's one open sub-point, which the council left open (moot unless a negative control passes the gate-acceptance test). Rule: spec R-21 9(d); key `gate.acceptance_test.cdar_guard.calibration`.
- **Already decided** (Resolution 4; R-21): the guard is added only if a negative control passes the acceptance test, and then before any card runs; the fixed −5 pp margin is withdrawn; the candidates are judged on placebo results only, never on a card's numbers.
- **Options** (the council's three candidates):
  - (a) the Professors' CDaR guard, tested at one-sided 5% under the bootstrap;
  - (b) the Executives' CDaR95 guard, with its margin at the placebo distribution's 10th percentile;
  - (c) QF's CDaR leg with a blind margin.
- **Default:** a selection rule over the three candidates that reads placebo results only, frozen with the gate package before any control or card runs (R2-C2). Its wording is the spec registry's (Quick start table, D6; R-21 9(d)) and is not restated here.
- **Owner ruling.** Optional. A ruling naming one candidate is accepted only before the first acceptance attempt; any later change is a new package version and a counted trial.
- **Consequences.** On existing numbers no negative control passes, so the guard is not expected to be needed (QF chair §0.3). If a control passes and no candidate brings every negative control to REJECT or INSUFFICIENT DATA, the acceptance attempt fails (R-21 9(a)): the package may be redesigned once, and a second failure, counted across all 2.x versions, ends card evaluation under v2 (R2-C3).

### 1.7 Other settling tests the council named (run in SPEC v2.0 milestones, or as backlog tasks)

| Open question | Settling test | Items | Where it runs |
|---|---|---|---|
| Korea VT20 promotion | The formal v2 run of Resolution 1 on KRX official closes. PASS needs four things: the full span; the ETF-era line to 2025-12; no REJECT and ≥ 2/3 PASS across the monthly starts 1997-05…1999-12; and no REJECT in either midpoint half. **Expected outcome (spec R-06, §8.9; R2-C1):** on current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build. f is computed from the R-06 family ledger and the maximum over the defensible row-set readings binds (indicative 1.26 on R4's three rows alone, 1.49 with the DL-A grid, 2.87 family-wide), while PC-3 needs p_ni × f ≤ 0.10, i.e. f ≤ 1.282 at the indicative p_ni 0.078. The status stays BUILD-AS-INSURANCE on a formal PASS, and no convention may be changed to rescue it | QF4-M1 and the Resolution 1 items | R-06 KR, M7 (needs BL-D21, BL-D31) |
| Is the gate package sound? | The gate-acceptance test, run before any card: at most 10% of 300 circular-shift placebos per family and at most 2 of 20 per card may pass; the negative controls must come out REJECT or INSUFFICIENT | QF3-A5, QF3-M3, X-EX1-N4 | R-21, M7 |
| CDaR guard calibration (only if a control passes) | Owner decision D6 (§1.6): its default rule is frozen with the gate package before any control or card runs (R2-C2) and is applied inside the acceptance test only if a control passes | X-EX1-N4 | R-21 9(d), M7 |
| Horizon-matched PC-2 | EX1's placebo test: daily vs horizon PC-2 on every pre-registered CARD-P plus 20 placebos. Adopt if the false-pass rate is ≤ 10% | QF5-A12, QF5-M5 | R-21, M7 |
| Step-3 rule for v3 | Size and power of N_equiv deflation vs linear-N̂ deflation vs PX1's z rule, under QF3 §4.4's DGP. Keep size ≤ 10%, with the most power at Δ 0.10–0.30 | QF3-M1, X-EX1-N1 | Backlog research (v3) |
| BLdP eq. 9 reading | Read eq. 9 and Exhibit 4 in the printed paper (DL-B's confidence: Med-High) | X-PX1-N1, QF3-C1 | Backlog task |
| R-18 statistical break leg | On 1990–2026: ≤ 1 false break a decade, and flags within 6 months of the 2012 and 2020 framework changes | QF7-M6, QF7-A19 | R-18; trigger (ii) is logged only until it passes |
| KIS quote fields | Bid/ask for 069500 and 005930 at 15:19:59 KST on 20 sessions; exchange vs receipt timestamps | QF1-A25 | Milestone-1 task (BL-C02, BL-D03) |
| The app's B5 study | Publish `docs/vol_backtest.py` and its seed; rerun B5 on SPY and KODEX 200, 2016–26 | QF6-A25 | BL-G01 residual task |
| Holiday-gap VaR display | Pre-registered 2027–28 out-of-sample breach rates | X-EX2-N2 | R-10 / R-16 display, forward |
| Korea reversal prior | BL-U02, net of 35 bp plus tax | QF5-A14 | BL-U02 |
| R-10 opening-gap flag | An event-conditional variance test (DM on the squared gap), run before R-10's flag is kept as "log only" | QF7-A28 | BL-U03, first step |
| S1 on ECOS 15:30 history | The ECOS rerun: a P3 formality that cannot change the REJECT | QF2-M8 | BL-G04 |

**Open implementation tasks from the spec's adversarial review** (spec §9.4 items 15–17; recorded in round 3 from the risk officer's notes 3, 6 and 7; not blocking). Each closes when its milestone's code does it:
- **15. Anchored timestamps** (M7, before the freeze). The `gate.step3.spec_versions` publication instants and every ledger seed row's `run_utc` cite a git commit or an external anchor, never a hand-entered time, because they decide the f = 1 route (R-23).
- **16. An archived snapshot per formal card** (M7). The rows behind each formal card's `data_snapshot_id` are archived with the card and md5-listed, because `verdict_filter` re-derives the snapshot from the store (R-35).
- **17. Atomic `engine_feed` per book** (M8). Each book's weights for a decision are delivered all or none; an interrupted delivery leaves the book on its previous weights (spec §3.9).

---

## 2. CONTESTED items (v1.x panel classes; re-statused in v2.0)

### BL-C01 — Daniel–Moskowitz floor: 0 vs 0.25 vs 0.5, and robustness without 2008–09 (N-08; PX-P-02, EX-E-05; executive K2)

**Status v2.0: OPEN · P2.** The test now informs only R-04's floor in the specification book. SPEC v2.0 demotes R-04 ("step 3 FAIL"; deflated add-on 0.77 at N_equiv 6.3) and closes its A-provisional route (QF5-M6; §6.8 #33). The decision rule was fixed per QF5-A3: ≥ 3 of the 5 samples, and a single-spell sample is INSUFFICIENT.

**Positions:**
- **Toward 0×** (P3, Q1b): the 0× gate gives +0.26, and D&M's own dynamic weights go to zero or below.
- **0.5×** (E5) or **0.25–0.5×** (E1): the overlay must never be 0×; P6 found 0.5/1 rules beat 0/1 rules for every estimator; at 0× the gate cost −32.2% relative over May–Nov 2008.
- **The spec builds 0.5.**

**Evidence:**
- **P2 says it is fragile.** With spells merged at gaps of ≤ 21 days, the 2008–10 spell supplies 101% of the 1990–2026 gain; without it the gain is +0.03. On monthly 1927–2026 data there are 20 spells; dropping 1932–33 and 2009 takes ΔSR from +0.29 to +0.12.
- **Q1b says it is robust enough.** Excluding Sep-2008–Dec-2009 still leaves +0.11 (share 0.93); 1990–2007 gives +0.22; 2020–26 gives +0.19.
- **R4 at floor 0.5:** alone +0.138; on top of capped vol scaling +0.084 (0.996); ex-2008–09 +0.056 (0.97); 2013-04 onward +0.055 (0.94). There are 7 spell onsets since 1990.

**Settling test:**
- **Spell definition:** one frozen definition (merge rule ≤ 21 days, exclusion window Sep-2008–Dec-2009, daily construction).
- **Samples:** US 1927–2026 monthly, US 1990–2026 daily, and the three international daily WML series (Japan, Europe, Asia-Pacific ex-Japan) over 2016–2026, which have never been used in design.
- **Floors tested:** 0, 0.25 and 0.5.
- **Output:** an episode table showing each spell's share of the gain.
- **Decision:** adopt the **lowest floor whose ex-top-spell ΔSR is > 0 with a one-sided 90% interval in ≥ 3 of the 5 samples**, with a pre-registered cap on the worst 6-month loss relative to R-03 (level declared on the card); a single-spell sample counts as INSUFFICIENT, not as a pass. A floor below 0.5 also needs an amendment to the spec's P2 bound, through a spec revision and a new card.
- **In gate terms (v1.1):** this was the Tier A-provisional route for the R-04 card (spec §8.3). That route is closed: the pre-registered BL-C12 holdout passed in 1 of 3 regions, and R-04's deflated add-on is 0.77 at N_equiv 6.3. Pooled onsets (34 across four regions) meet sufficiency, but a pooled-Tier-A card would be a new revision counted as a trial; R-04 stays in the specification book at 0.5. R4b net of 50 bp on both legs: add-on +0.072 (share 0.983).

**Data needed.** None; the French files are local.

**Priority: P2.** It is cheap. BL-C12 has resolved (holdout 1 of 3 regions), so this test now informs only the floor, not R-04's route.

### BL-C02 — Should reversal be blocked in fast stress? (N-10; EX-E-01; executive SHADOW S5)

**Status v2.0: OPEN · P1.** It is blocked on the milestone-1 task: confirm the KIS level-1 quote fields (QF1-A25; §1.7). Its stress-day quote snapshots also calibrate R-26's state-dependent stress-cost line, which is reported and never gated until then (QF1-A7). R-27 prices simulated stress-day fills at the close, with limit-lock flags. Errata QF1-A5, A12 and A13 are applied.

**Positions:**
- **Block it** (E5). KRX execution binds: ±30% price limits; 41 sidecars from 2 Jan to 24 Jul 2026 (≈ 30 in H1); 4 circuit breakers and 15 sidecars in Jul-2026. Spreads widen about 2.5×, and E-mini depth fell 68% in Apr-2025. The intraday reversal leg loses money. Short-term trading programmes lost 0.9% in Apr-2025.
- **Keep 1.0×** (Q1b, E1, and the professors' PC-P-06 "never cut").
  - On the true VIX ≥ VIX3M flag, gross reversal earned 59.2% a year at 34.8% vol (Sharpe 1.70) vs 1.8% at 12.3% (Sharpe 0.15) otherwise; the 2.35 / 1.11 figures spliced in a VIX > 30 proxy before 2007-12.
  - On the KOSPI index, the day after a −5% day averaged +1.71%, and the next 5 days +4.25%, in 2015–26 (n = 23); over 1997–2026 (n = 81) they averaged −0.01% and +2.85%. The next-day rebound is a 2015–26 feature.

**Mixed evidence.** By KOSPI volatility tercile, the high-vol tercile reversal Sharpe is 0.44 (t 1.05), while the mid-vol tercile shows continuation (t −2.74).

**Settling test:**
- Run reversal at 1.0× through stress in the forward-simulated book, costing every simulated entry at QUANTGEN's KRX stock rate (35 bp per side; 70 bp stress). Measure stress-day spreads from KIS quote snapshots. **Fill logs do not exist in a read-only app (§5c).**
- **Decision rule:** block reversal in fast stress if the stress-day cost exceeds the gross stress-day edge, where the cost is either the measured all-in cost (median quoted half-spread + commission + half the sell tax) or the table's 35 bp per side, never their sum (35 bp is already all-in); report both lines against the edge. That would be a REVISE of the reversal card's stress subsample.
- Also run a stock-level test by VKOSPI tercile, 2015–26.

**Data needed.** KIS stock-level OHLCV, minute bars and quote snapshots (BL-D03). First milestone task: confirm that KIS level-1 quotes carry bid/ask (pull 069500 and 005930 at 15:19:59 KST on 20 sessions; check exchange vs receipt timestamps). If they do not, BL-C02 needs another quote source; it cannot settle before this.

**Priority: P1.** It decides whether R-05 needs a Korea exception.

### BL-C03 — The role of credit spreads (N-13; PC-P-08, EX-E-06; executive K3)

**Status v2.0: OPEN · P3** (no council ruling). The test is judged under the v2.0 gate.

**Positions:**
- **Professors:** credit is a late, mean-free variance input. It may enter only a variance composite, tested with Politis–White blocks and a Holm correction.
- **E5:** a slow HY +50 bp / 21-day flag should scale existing exposure.
- **E1 / Q1b:** block new entries only, or leave it in the backlog.

**Evidence:**
- **Baa−10y +50 bp / 21 days:** fired in 8 episodes since 1986 (1.5% of days), after a median 57% of the coming 12-month drawdown had already happened. Forward 63-day return afterwards +0.8%.
- **Top-decile credit gate on momentum:** +0.13 in 1990–2007, +0.02 in 2008–26, −0.05 in 2020–26.
- **HY +50 bp / 21 days:** fired on 5 Aug 2024 (+66 bp) and from 11 Mar to 7 Apr 2025 (max +164 bp).
- **Baa never fired** in 2022 (+48 bp), 2025 (+41 bp) or 2026 (+20 bp).
- **HY on FRED** goes back only to 2023-10, which gives 2 clusters.
- **Sep-2026:** +47 bp. During the Jul-2026 KOSPI crash, HY only moved from 2.75 to 3.12.

**Settling test:**
- License ICE HY OAS history from 1997.
- Compare (a) scaling existing exposure, (b) blocking new entries only, and (c) a variance-composite input, each with leave-one-crisis-out.
- **Pass:** a Tier A onset count (≥ 30); ΔMDD ≤ 0; deflated ΔSR ≥ 0; and a benefit that is **not concentrated in 1990–2007**.

**Data needed.** ICE HY OAS from 1997 (BL-D07).

**Priority: P3.** 2026 is a rates-stress regime, not a credit-stress regime.

### BL-C04 — Vol-estimator speed and an implied-vol input (N-15; EX-E-02; executive SHADOW S4)

**Status v2.0: RESOLVED.** The question now lives in three places in SPEC v2.0:
- **R-30**, the volatility-estimator selection gate, in which COMB is the registered challenger;
- **R-06**, where SMA20 stays the acting default and the displayed baseline (2–1);
- **R-13**, where implied vol is logged as live context.

This section was rewritten per QCE-213. Council items: QF6-M1, QF6-M2 (VALID-SHADOW, CQ-07), QF6-A1–A4, QF6-A15, QF6-A19, QF6-A20, QF7-M2, QF7-A22, X-PX1-N6, and QF6-M6 (CONTEXT-ONLY, CQ-15).

**Positions (v1.x):**
- **E5: slow.** Blend 10- and 60-day half-lives, floor at 60-day realised vol, and cap the daily weight change at 20%.
- **E1: fast to restore.** E5's estimator took 214, 121, 68 and 62 sessions to re-enter, vs 88, 40, 29 and 27 for a 20-day target. US 2020–26 Sharpe was 0.61 for E5's estimator vs 0.73 for VT20 (buy-and-hold 0.65).

**Other evidence (v1.x):**
- KOSPI: SMA60 0.550 vs SMA20 0.638; EWMA (half-life 10) 0.607.
- Harvey et al. (2018) found the Sharpe ratio insensitive to the half-life ("not very sensitive to the choice of volatility estimate"); tracking error, turnover and vol-of-vol are not.
- **R4b (v1.1).** Both SMA20 and EWMA(0.94) pass a B5-style check (FHS form) on KOSPI, SPY and the US market (BL-G01).
  - Net of costs, EWMA has lower turnover. US: 2.23 vs 2.52 a year; SR 0.520 vs 0.505 at 50 bp. KOSPI: 1.37 vs 1.50; SR 0.573 vs 0.605 at 35 bp (SMA20 better).
  - This is one trial each, not significant.
  - v1.2's declared rule kept SMA20 as the default and made EWMA(0.94) the registered challenger. SMA20 is not a validated default: it is outside the 90% QLIKE model confidence set at 1, 5 and 21 days in both markets (p ≤ 0.0005), and B5 passes 9 of 12 forecasters, so B5 cannot choose; selection moves to R-30's three-stage gate (calibration, then the QLIKE MCS screen at the sizing horizon, then the choice priced at the declared book).
- Long-window GARCH-t and GJR-t already pass B5 in FHS form (KOSPI 2001–26, US 1995–2026), and log-HAR on daily ranges is admitted at the sizing horizon, so all of them can enter R-30's race.

*(The R4 values 0.550, 0.607 and 0.573 above were not recomputed after the 2-Oct patch; the pre-patch R4 pair is kept for the comparison with SMA20's 0.638, `QC_errata_notes.md`.)*

**Council evidence (data lab DL-B):**
- **DLB-T1a/T1b.**
  - SMA20 is outside the 90% QLIKE MCS at 1, 5 and 21 days in KOSPI and the US (p ≤ 0.0005). This also holds with T_R, with 63-day blocks and on 2016–26 alone.
  - Under MSE it stays inside the MCS (the US at all horizons; KOSPI at 21 days). The dominance is QLIKE-specific.
- **DLB-T1f.**
  - B5 passes 7 of 9 KOSPI models and 8–9 of 9 US models, so it cannot select.
  - SMA20's KOSPI breaches cluster: Christoffersen p < 0.0001 on 2001–26 and 0.0006 on 2016–26. Only log-HAR-range (p 0.16) and COMB (p 0.17) pass independence.
  - COMB is the only model inside the 90% MCS in all six cells. Its QLIKE as a multiple of SMA20 is 0.944 / 0.809 / 0.691 in KOSPI and 0.916 / 0.723 / 0.642 in the US.
- **DLB-T1g** (KOSPI 2001–26, 3 bp).
  - COMB cuts vol-of-vol by 22.2% and improves ΔMDD by 2.8 pp at ΔSR −0.000 [−0.042, +0.039]. The gains halve on 2016–26.
  - At 35 bp, log-HAR costs −0.063 Sharpe (the CI excludes 0) and COMB −0.030.
- **DLB-T1d.**
  - The 1-day HAR failure came from QF6's log-r² design. With the range target, log-HAR gives 0.947 / 0.921 × SMA20 at h = 1.
  - Log-HAR-range narrowly misses KOSPI's 1-day B5 (5.58% vs a 5.56% band).
- **DLB-T1h** (1995–2026, 5 bp). SMA20 gives +2.5 pp (REJECT), while GARCH (+4.9), log-HAR (+4.8) and COMB (+3.9 pp) PASS. The US futures card's verdict flips with the estimator.
- **DL-A bridge.** An EWMA(0.94) switch would turn the Korea card INSUFFICIENT on PC-4 (0.51) under §8.6. An estimator change can flip a knife edge.
- **Implied vol.**
  - `max(σ̂_SMA20, implied)` is retired (§6.8 #34): it embeds the variance risk premium, and it de-grosses (ΔSR −0.166 at 50 bp, turnover 6.0 a year, US 1995–2026).
  - The implied-vol gain is pre-2008 only (0.615 vs 0.614 since 2010).
  - VKOSPI closes at 15:45 KST, after the decision.

**Settling rule (SPEC v2.0 R-30; replaces v1.2's race between "one pre-registered asymmetric estimator, VT20 and E5's estimator").** A challenger may replace SMA20 for a card only through a counted card revision that passes the full v2 CARD-P and the staged estimator gate:
- **Stage 1 (calibration, necessary)** at the 21-day sizing horizon: FHS VaR exceedance, the 21-day fan PIT and Christoffersen conditional coverage.
  - The 1-day Kupiec/Christoffersen lines and ES 97.5% Z2 are printed.
  - 1-day VaR is displayed only from models that pass the 1-day B5.
- **Stage 2 (screen):** membership of the 90% QLIKE MCS at h = 21. The MSE MCS is printed.
- **Stage 3 (choice):** the lowest vol-of-vol, with ΔMDD and PC-2, net of turnover at the declared instrument book, with ΔSR non-inferior.
  - Overlapping bootstrap CIs count as ties and go to the simplest surviving model.
- **Who may enter.**
  - COMB = ½(GJR-t + log-HAR-range), fitted on expanding windows, is the registered challenger for ETF and futures books only, never for the 35 bp stock book.
  - A GJR fit outside its bounds, or a tripped OHLC open-quality flag, falls back to SMA20 (fail-closed).
  - The registered Korea card keeps SMA20.
- **Other candidates.** EWMA(0.94), E5's asymmetric blend and any other candidate enter only through this gate, and every configuration run is logged in the family ledger (R-23). Range-based log-HAR is admitted; ML vol-state classifiers stay prohibited (§6.9 #36).
- **The choice is a tracking and drawdown decision, never a Sharpe claim.**
- **Implied vol** acts only inside HAR-IV, and only if HAR-IV wins this race (ST-09). Until then VIX/VIX3M (16:00 ET) and KOSPI 200 MFIV (15:30 KST) are logged as live snapshots (R-13; QF6-M6).

**Dissent recorded.** The Professors would retire SMA20 as the sizing default for new cards; they expect COMB to win on ETF and futures books. The Executives and QF keep SMA20 acting (2–1).

**Data needed.** VKOSPI history (BL-D12); KOSPI 200 option-board snapshots (BL-D27); OHLC open-quality flags (R-01; §5a DQ-03).

**Priority: resolved.** The race is SPEC v2.0 R-30 (milestone M3). COMB's card switch is tracked as ST-03 (§1).

### BL-C05 — Korea discrete local flags and time-stops (N-20; EX-E-03, EX-E-07; executive SHADOW S6, K4)

**Status v2.0: OPEN · P2** (no council ruling on a gross rule). R-10 keeps no gross cut on sidecar or circuit-breaker days, and R-27 prices simulated stress-day fills at the close with limit-lock flags (QF1-A14). Both settling tests are judged under the v2.0 gate: objective episodes (R-22), PC-1′ (R-21) and the timing-fragility gate (R-34).

**Positions:**
- **E2:** local time-stops. A −5% KOSPI day → 0.5× for 3 sessions; a sidecar → 0.5×; a circuit breaker → 0.25×.
- **E3 and R2-E3:** continuous control only.
- **On levels vs percentiles:** E5 wants absolute levels; E1 wants scale-free percentiles plus re-anchoring.

**Evidence:**
- The time-stop gave **+0.55 in 2026** (share 0.99) but **−0.06 in 2016–25** (share 0.004). The 10-day version gives −0.035.
- An absolute VKOSPI-type flag ≥ 30 was on for 88% of 2026 days (86% of the Jan–May rally), vs 0–20% in 2015–25.
- Even a trailing 3-year 90th percentile of KOSPI rv21 was exceeded on 72% of 2026 days (10% in 2015–25). QF6's recomputation gives 72.8% and 13.6%; the council did not rule on the difference.
- **New (QF1-A14).** Over 26 circuit-breaker-proxy days (low ≤ −8%) in 1997–2026:
  - VT20's weight on the 2026 ones averaged 0.31 (Jul: 0.27), and the change decided at those closes was 3.1 pp (Jul: 1.4 pp). The vol target had already de-risked.
  - KOSPI gapped up +0.99% the next morning on average, so a sale at the crash-day close cost about 17 bp of NAV per event versus the next open.
- **New (X-EX2-N2).** Multi-session holiday gaps break the 1-day VaR. The FHS 95% breach rate is 12.2% after 2 US sessions and 17.4% after ≥ 3 (2001–26). R-10 tags these sessions for display only, with no gross rule until one is pre-registered and tested.

**Settling tests:**
- **(a) Conditional time-stop:** active only while 21-day realised vol exceeds its trailing 80th percentile. Test it as a protective card on 2016–25 and in the forward record, with leave-one-crisis-out. 2026 may supply no more than 50% of the benefit (PC-4).
- **(b) Absolute vs scale-free flags:** compare them, with re-anchoring, on KOSPI, TAIEX and Nikkei over 2015–26, with leave-one-crisis-out. Report the share of rally days flagged, coverage of the 10 worst days, and ΔMDD.

**Data needed.** KIS minute data for the intraday sidecar rows.

**Priority: P2.**

### BL-C06 — Are foreign/institutional flows still informative for KOSPI? (N-21; PX-P-09, EC-E-25)

**Status v2.0: OPEN · P1** (no council ruling). Investor-type flows are logged as context from day one, with timestamps (BL-D01; R-13 `context_log`, as in v1.2), and they never act. The test is judged under the v2.0 gate.

**Positions:**
- **Yes** (P3, from Hong & Lee 1998–2010: foreigners and institutions are informed). The June-2026 turn fits: a ₩2.12tn net buy on a +4.63% day.
- **No longer** (P2, T1, the executives):
  - in H1-2026 foreigners sold ₩148.3tn while KOSPI rose ≈ 101%;
  - in Sep-2026 they sold ₩21.5tn, and over Q3 USD/KRW fell 12.4% (0.9% in September itself);
  - retail bought a record ₩8.54tn on the −9.99% day;
  - flows are same-day and positive-feedback (Richards, RBA RDP 2004-05; Choe–Kho–Stulz).

**Settling test:**
- **Data:** KIS/KRX daily investor-type net buys, 2015–2026, lagged to t−1 (or intraday preliminary figures with their timestamps).
- **Target:** KOSPI open-to-close returns.
- **Split:** before and after May-2026, when single-stock leveraged ETFs listed.
- **Decision:** the sign and t-statistic of the foreign-flow coefficient in each sub-period.
- Also test a regime label (foreign-led vs domestic-leverage) as an input to BL-U01.

**Data needed.** KRX flows (BL-D01). The spec logs them from day one.

**Priority: P1** (start logging now).

### BL-C07 — Rate- and inflation-conditioned de-risking beyond S2 (N-25)

**Status v2.0: OPEN** ((a) P2; (b) P2, needs 2027+ data; (c) P3); no council ruling. If (b) is ever built, R-18's trigger (i) applies: an official framework change shrinks every macro-conditioned multiplier to 1.0 and starts a forward record.

**(a) US rates stress as a Korea/Asia input** (EX-E-04; executive K1)
- **Evidence for:**
  - an exploratory UST10 20-day > +25 bp rule at 0.5× gave +0.115 (share 0.994; 5th percentile +0.03), +0.067 ex-2022, and +0.042 ex-2022 and ex-2026;
  - KOSPI averaged −30% annualised on flag days vs +16% otherwise.
- **Evidence against:**
  - the +40 bp version has 12 KOSPI onsets and scores +0.002 in 2024–26;
  - it lost in low-inflation years (2017 −1.2 pp; 2025 −3.7 pp);
  - KOSPI's β to 10y changes has R² 0.015 (2025–26);
  - the Jul-2026 crash was not rates-driven (ER-E-15).
- **Test:** one pooled trial on KOSPI, TAIEX and Nikkei, conditional on core PCE ≥ 3% or a positive 63-day stock–bond correlation; open-to-close returns; 2022 may supply no more than 50% of the benefit.

**(b) Macro-conditioned overlay floor** (PX-P-03)
- **Proposal (P1):** floor 0.5 when core PCE ≥ 3% or the Fed is tightening; 0.75 otherwise.
- **Evidence for:**

  | Regime | EWMA de-risk ΔSR | Real-time Markov 0.5/1 ΔSR |
  |---|---|---|
  | Core PCE ≥ 3% | +0.14 | +0.22 |
  | Core PCE < 3% | +0.05 | −0.01 |
  | Fed tightening | +0.11 | +0.10 |

- **Evidence against (P6):** every one of those intervals includes 0; the high-inflation sample is essentially 1990–91 and 2021–23; KOSPI rose 68% (31 Mar–30 Jun 2026) while the Fed turned hawkish.
- **Test:** a locked 2027+ holdout on US daily and KOSPI data. Core PCE lagged 2 months; Fed funds 6-month change lagged 1 month. Paired stationary bootstrap. Success requires the paired ΔSR interval to exclude 0 in the high-inflation cell, with no deterioration in the low-inflation cell. It counts as one trial.

**(c) Market-implied repricing: 2y +25 bp over 20 days → 0.75×** (EX-E-08; executive K5)
- **Evidence:** +0.02 on the Nasdaq-100 (share 0.90), +0.04 on SOX (0.93), +0.03 on KOSDAQ (0.93). In 2026 market pricing moved two meetings earlier than the SEP, but at a one-year horizon the market did not beat the SEP.
- **Test:** its added value over S2 in a joint model, with leave-one-crisis-out.

**Priority:** (a) P2; (b) P2, but it needs 2027+ data; (c) P3.

### BL-C08 — Duration-sensitive tilts under real-rate shocks (N-27; PX-P-06, EX-E-11; executive K9)

**Status v2.0: OPEN · P3** (no council ruling).

**Evidence:**
- **NDX tilt conditional on a rising USD:** +0.10 (share 0.98–0.99) over 2007–26, but −0.01 / −0.04 in 2024–26. On KOSDAQ: −0.11 (share 0.02).
- **RMW at 1.5× under rates stress:** +0.094 (2020–26, share 0.98). The credit-gated version scores −0.01.
- **HML and real yields:** contemporaneous +2.45%/month per pp (t 2.3, ex-2022), but lagged t only 0.62 (2003–19).
- **Maloney–Moskowitz:** rate links to factors are "not robust".

**Settling test:**
- **Data:** US duration-sorted portfolios (or growth-vs-value proxies), 2003–2026.
- **Method:** one pre-registered cell on ΔDFII10 (+50 bp over 63 days) with a breakeven-direction split. Test whether Δ5y5y adds to ΔDFII10 out of sample. Holdout 2023–26.
- **Keep only if** the effect exists solely in the rising-real-yield / flat-breakeven subsample.
- **Implementation constraint:** only as a within-family tilt ≤ 1.0, with leave-one-crisis-out excluding 2022.

**Priority: P3.**

### BL-C09 — Policy-communication state variables (N-32; PX-P-07, PX-P-08, PX-P-11; PR-P-31)

**Status v2.0: OPEN · P3** (no council ruling; interim: log only).

**(a) Δbreakeven/Δnominal as a credibility gauge**
- **Evidence:** the yearly all-day β read 0.16 in 2022 and 0.07 in 2013 — "anchored" in exactly the real-rate-shock years. Its Spearman correlation with the stock–bond correlation is −0.48 (p 0.03).
- **Test:** 30-minute TIPS and nominal futures moves on CPI and FOMC days, 2004–2026. Keep the "contested" reading only if it predicts the stock–bond sign and equity drawdowns **beyond** the all-day real-rate share.

**(b) FOMC policy/information classes as equity-gross rules**
- **Evidence:** HAWK days (n = 16) were followed by +0.93% over 10 days; INFO_NEG days (n = 5) by +3.99%, all 5 positive. The 16-Sep-2026 HAWK day was followed by S&P +1.5% and KOSPI +3.4%.
- **Test:** a 30-minute Jarociński–Karadi replication over 1994–2026, with surprises orthogonalised on pre-meeting news (Bauer–Swanson). Outcomes: 1–20-day S&P drift and KOSPI opening-gap drift by class. Adopt only if the INFO_NEG/HAWK drift is negative and significant net of the Fed-put rebound.

**(c) The "good news is bad news" sign**
- **Evidence:** the payroll-day correlation of Δ2y with the S&P was −0.74 (2017), +0.14 (2022) and −0.73 (2026). Twelve releases cannot estimate a sign.
- **Test:** pooled CPI, payroll and ISM consensus surprises in a 24-month window, 2000–2026. The sign must predict the next 6 months' sign out of sample with a hit rate ≥ 65%.

**Also here:** the FOMC dissent-migration indicator (T1-C2; n = 2).

**Data needed.** Intraday futures; a consensus feed (BL-D05, BL-D06).

**Priority: P3.** Interim: log only.

### BL-C10 — A trend axis with hysteresis for market gross (N-34; EC-E-09; executive SHADOW S3)

**Status v2.0: RESOLVED** (Resolution 9). The question now lives in SPEC v2.0 as follows:
- **R-28** is a protective-only CARD-P on a monthly SMA10m rule for US and other non-Korean equity sleeves. It runs FORWARD-SIM in the specification book until such a sleeve exists (VALID-SHADOW, CQ-05 and CQ-06, ST-02).
- **Korea is CONTEXT-ONLY:** the KOSPI trend state is displayed and never acts.
- **E5's band (this item)** is a logged trial in R-28's family ledger: kept as the US alternative, demoted for Korea.

Council items: QF5-A10, QF5-M2, QF5-A8, X-PX2-N1.

**Proposal (v1.x).** E5's band: 0.98/1.02 × the 200-day average, 3 confirming closes and a 10-day minimum dwell. The exit is keyed to the market's own EWMA-10 vol falling below its 1-year median, rather than to the VIX flag. One trial.

**Evidence for (v1.x):** hysteresis cuts switches per year from 6.0 (plain) to 3.4, 2.45 and 0.89.

**Evidence against (v1.x):**
- the axis was silent in Mar-2026 (US) and Jul-2026 (KOSPI, minimum 0.978 × its 200-day average);
- with a VIX-conditioned exit, risk-on returned only on 30 Apr 2020 (+30% off the low) and 1 May 2025 (+12.5%);
- the professors call 200-day rules data-mined for outperformance (Zakamulin), not for protection: the protective claim survives a 94-variant snooping haircut, the Sharpe gain does not; and P6's 200-day conjunction removed all Q3-2026 protection (−38.1% vs −9.6%).

**Council evidence (data lab DL-B; QF5; QF7):**
- **US monthly SMA10m 0.5× (DLB-T3a).**
  - 1927–2026 at 5 bp: ΔSR +0.083 [0.019, 0.134], ΔMDD +15.9 pp, tail ratio 0.78, 9 of 10 bears, 45 de-clustered onsets. PASS at both 5 and 50 bp.
  - It is robust to the cash yield (T3b).
  - It PASSes for starts up to 1960. From 1970 it is INSUFFICIENT on onsets, while ΔMDD stays at +12 to +16 pp (T3c).
- **Other indices (T3e).** ΔMDD is > 0 in all 7: S&P +17.5, DAX +14.0, TAIEX +12.0, KOSDAQ +9.8, HSI +8.0, FTSE +7.4, Nikkei +4.2 pp.
- **Snooping haircut (T3f).**
  - 94 of 94 variants keep ΔMDD ≥ 3 pp (median +16.4). SMA10 ranks 51st on ΔMDD.
  - The Sharpe gain's deflated probability is 0.59 at N̂ 30.7 and 0.43 at N 94.
- **Mechanism.**
  - Below the SMA, the next month's |r| is higher (t 4.75) and its mean is not lower (t −0.77).
  - White's RC p 0.20; SPA 0.23; GJR-null percentile 87th.
  - Stacked on US VT15, it adds +14.9 pp.
- **KOSPI (T3d).**
  - The daily tail ratio of 0.929 fails PC-2 (0.853 at 21 days).
  - It adds +2.2 pp on VT20 and −2.3 pp on 2016–26.
- **This band (BAND200).** +16.5 pp and ΔSR +0.107 on US data at 50 bp (QF7), but −0.7 / +0.7 pp on KOSPI.

**Ruling (SPEC v2.0 R-28).**
- **The rule.** At each month-end close, if the sleeve's index closes below its 10-month SMA, market gross is × 0.5 for the next month. It is composed by `min()` with the vol target and the ladder.
- **The claim.** Slow-bear protection via the volatility state; never a Sharpe or return claim.
- **How it is judged.**
  - Incrementally, on the vol-targeted book: stacked ΔES and ΔMDD, ≥ 3 pp.
  - The GJR-null percentile and the snooping haircut are printed.
  - Tier A via a pooled-onset rule declared before any run.
- **Scope and promotion.** One card per US or other non-Korean equity sleeve (scope 2–1; the Executives' "US" is the first instance). It is BUILD-AS-INSURANCE on a formal PASS once such a sleeve exists (D5).
- **No PC-2 rescue.** A horizon-matched PC-2 may not rescue the KOSPI trend.

**What v1.1's re-gate becomes.** The v1.1 route (Tier A count of 88 US switches, KOSPI borderline at 52; 12 months of forward record; demotion on 2× the switch budget) is superseded:
- the forward record is a falsification alarm only (R-25);
- E1, QUANTGEN's trend switch, was REJECTED for outperformance while protecting, which is why R-28 is registered as a protective card from the start.

**Priority: resolved.** R-28 is FORWARD-SIM (§1, ST-02). This band variant is a logged trial in R-28's ledger: it is demoted for Korea (−0.7 pp) and kept as the logged US alternative.

### BL-C11 — An oil-shock event rule scaling KOSPI gross (N-45; PX-P-05)

**Status v2.0: OPEN · P3** (no council ruling).

**Evidence for:** in Mar-2026, within 20 days, KOSPI fell 15.5%, the S&P 7.8%, and USD/KRW rose 5.2%.

**Evidence against:**
- across 22 Brent +30% episodes, forward 63-day returns equalled the unconditional (2.67% vs 2.66%, p 0.50);
- Nikkei and KOSPI forward 3-month returns were *above* average (2.31% vs 1.67%; 3.21% vs 2.66%);
- KOSPI then rose 68% while oil stayed high;
- in 2022 the S&P rose 7.0% over the same window;
- the 20-day version is refuted (ER-E-12), and E3's 5-day version is untested — it would also have fired only after 3–4 Mar.

**Settling test:**
- **Data:** an event study over 1988–2026, with Dated Brent spot and front-month futures named separately.
- **Triggers:** Brent 5-day > +15% or 20-day > +30%, conditional on real-yield direction.
- **Outcomes:** KOSPI, Nikkei and S&P forward 5/20/63-day returns and realised vol, measured **incrementally to own-vol scaling**.
- **Adopt only if** the vol-adjusted forward drawdown falls in ≥ 3 of 4 importer episodes without forfeiting the subsequent rebound.

**Data needed.** Long front-month futures history; locally, BZ=F only goes back to 2015 (BL-D11).

**Priority: P3.**

### BL-C12 — A separate evidence tier for prior-backed effects (N-51; PX-P-01)

**Status v2.0: CLOSED** (resolved: the uniform hurdle applies). Step 3 is now SPEC v2.0 R-23. CARD-O passes when the deflated ΔSR vs overlay-off is ≥ 0.95 at N_eff = max(N_clusters, N_equiv); CARD-P prints DSR and PSR but does not gate on them. R-04's A-provisional route is closed (§6.8 #33).

**Positions:**
- **P2:** one multiplicity hurdle for every cell.
- **P3:** a non-inferiority tier for published, replicated effects.
- **Executives:** tiers defined by event count (Tier A needs ≥ 30 onsets). By that rule the D&M gate, with 7 spells since 1990 (R4), would not qualify.

**Evidence:**
- Barroso–Santa-Clara vol scaling: z 3.84 / 3.29 / 2.99 for the spec rule (cap 1, net; 10 / 63 / 240-session blocks), so it clears the one-sided ≤ 8-cell hurdle (2.50) at every block length and Bonferroni-120 (3.34) only with short blocks; 4.83 / 4.31 / 3.93 for the research rule (cap 2, gross).
- The D&M gate has z 1.8–2.0 on daily data and 2.82 on 1929–2026 monthly data, but exceeds 1.96 in **0 of 18** ten-year windows.

**Settling test:**
- pre-registered 2016–2026 holdouts on daily WML for Japan, Europe and Asia-Pacific ex-Japan, never used in design;
- paired stationary bootstrap with Politis–White blocks;
- **Decision:** adopt the separate tier if the D&M gate is non-inferior (ΔSR ≥ 0, one-sided 90%) in ≥ 2 of 3 regions with no episode above 50%. Otherwise the uniform hurdle applies.

**Resolved (pre-registered run).** The holdout passed in 1 of 3 regions (Japan +0.017, p 0.30, a single spell; Europe +0.147, p 0.006; APxJ +0.041, p 0.24), so the uniform hurdle applies. R-04 stays in the specification book; a pooled-Tier-A card would be a new revision counted as a trial.

**Priority: closed** (resolved: the uniform hurdle applies).

### BL-C13 — Yen shock → block new Japanese exporter longs (N-53; EX-E-09; executive K11)

**Status v2.0: OPEN · P3** (no Japan sleeve; no council ruling).

**Evidence:**
- after 18 yen-shock episodes, the next 10 days averaged −0.23% vs +0.55% unconditional; the rule fired on 17 Jul 2024;
- but ΔSR was −0.05 (share 0.17), and −0.13 in 2024–26;
- its hold period lapsed the day before the Nikkei's −12.4% day (5 Aug 2024) and re-engaged for the +10.2% rebound.

**Test:** re-specify it to block new Japanese exporter longs, with the hold timed from the last extreme-vol day (3–5 sessions). Run it forward once a Japan sleeve exists.

**Priority: P3** (no Japan sleeve yet).

### BL-C14 — A pre-emptive, positioning-based crowding cut (N-57; PX-P-10)

**Status v2.0: OPEN · P3.** Crowding stays context (QF4-A23, CQ-12). R-13 logs KOFIA margin debt and KRX single-stock leveraged-ETF AUM and value traded (QF4-M8, CQ-13). The settling test is unchanged (ST-07).

**Positions:**
- **For** (P4): unwinds have strategic complementarity (Stein 2009; Morris–Shin). Speculative yen shorts were near a record ≈ ¥2tn before Aug-2024 (BIS Bulletin 90).
- **Against** (P3):
  - public triggers come late: US momentum lost 5.9% between 11 Jul and 2 Aug 2024, *before* the trigger, and gained 6.5% between 6 and 30 Aug, the window a cut would have removed;
  - own-factor vol already tracks crowding: the momentum vol-scaling weight was 0.53 in Jul-2026 and 0.31 in Nov-2020.
- **Council evidence (QF4-A23):**
  - the absorption-ratio shift adds nothing to a HAR forecast of KOSPI 21-day vol (t −0.19);
  - turbulence adds t 1.33 incrementally (t 5.26 alone);
  - the KODEX leveraged/inverse value-traded share has t −3.59, with the wrong sign (2017–26);
  - the 2026 leverage sat in single-stock leveraged ETFs (14 products, ₩13.02tn on 8 Jul), which index-ETF data cannot see.

**Settling test:**
- **Data:** CFTC positioning, KRX margin and leveraged-ETF data.
- **Episodes:** Feb-2018, Mar-2020, Aug-2024, Apr-2025 and Jul-2026.
- **Question:** does the crowding score lead own-factor vol by ≥ 5 days in ≥ 3 of 5 episodes, **and** add to vol-scaled sizing?

**Priority: P3.**

---

## 3. ONE-SIDED items (v1.x panel classes; re-statused in v2.0)

### BL-O01 — Verify the regional cross-sectional momentum priors (N-35; professors only)

**Status v2.0: OPEN · P2, re-scoped to admissibility (R-15).** The 0–3 priors are now admissibility filters with equal risk budgets: base_weight(m, f) = IV_m × 1/K_m over the admissible families (prior ≥ 1 and card not REJECT). The conversion step below (weight = max(0, rolling-10y Sharpe)) is superseded. In a 2000–26 walk-forward over 6 regions × 5 factors, equal weights scored 1.337 against 1.068 for this rolling-Sharpe rule (shrinkage 1.152; QF5, re-run by PX2). The decision rule stands as an admissibility test: the Japan prior moves from 0 to 1 only if its own-data post-2016 CI excludes 0.

**Evidence:**
- **French WML Sharpe, 1990–2026:** US 0.33 (t 2.0), Japan 0.07 (t 0.4), Asia-Pacific ex-Japan 0.71, Europe 0.78, Developed ex-US 0.67, Emerging 0.93. After 2008: US 0.02, Japan −0.02.
- **AMP Table I (Japan):** factor column momentum 0.13, value 0.77, combination 0.88; P3−P1 column 0.09 / 0.79 / 0.78.
- **US mean break** in Oct-2002 (QLR p 0.041 from a 1963 start; 0.10–0.11 from 1927 or 1990): a descriptive, searched break.
- **R4, vol scaling with cap 1:** Japan 0.196; Europe 1.143; APxJ 1.125, but in 2016–26 0.897 vs 0.921 static; Developed ex-US 0.996.

**Test:**
- Build QUANTGEN's own vol-scaled cross-sectional momentum on each universe it reads, as a CARD-O per market.
- Report full-sample, rolling 10-year, post-2008 and post-2016 Sharpe.
- Convert to weights with the prior design's rule (weight = max(0, rolling-10y Sharpe), normalised per market), after the factor-specific haircuts (momentum −23%).
- **Decision:** the Japan prior moves from 0 to 1 only if the own-data post-2016 vol-scaled Sharpe confidence interval excludes 0.

**Priority: P2.**

### BL-O02 — Momentum new-entry size-down on scheduled decision days (N-39; professors only, PC-P-22)

**Status v2.0: OPEN · P3.** QF5 reproduced the evidence and kept P3, because there is no power. Over 46 FOMC days in 2021–2026 the S&P averaged +1.4 bp vs +5.6 bp on other days, with |r| of 97.0 vs 73.6 bp.

**Evidence:**
- **For a size-down:** FOMC days in 2021–26 had an abs(r) of 97 bp vs 74 bp (1.3× the risk) with no premium (+0.6 vs +5.3 bp).
- **Against** (executives): S&P FOMC-day mean +5.5 vs +5.1 bp over 2015–26.
- **Statistical power:** payroll days 1990–2026 show +10.0 vs +3.4 bp (t 1.15). About 105 years of data would be needed for t = 2.

**Test:**
- Use QUANTGEN's own announcement-day P&L and beta from the forward-simulated book (2027 onward).
- Compare new-entry momentum P&L on FOMC, CPI, NFP and BoK days with other days, net of costs.
- Adopt × 0.5–0.7 only if event-day new-entry risk-adjusted P&L is significantly worse (t ≤ −2).

**Priority: P3.**

### BL-O03 — Korean supply screens that exclude names (N-59; executives only)

**Status v2.0: OPEN · P2** (no council ruling). QF7 notes that published replication failures cluster in microcap and trading-friction anomalies, which supports excluding illiquid Korean names.

**Candidates:**
- a 60-session long-book exclusion after a rights offering;
- the first 20 sessions after a listing excluded from momentum ranks;
- lock-up expiries: no new longs from T−5 to T+2;
- block-trade exclusion;
- an FSC delisting flag;
- a KOSPI200 constituent-history event study (executive K16).

The KOSPI200/MSCI change calendar is already in the spec, as a log-only flag.

**Evidence:**
- **US literature (via E6):** IPOs underperform by −24.7% over 3 years (2011–24 cohorts); lock-up expiries −1.8%; accelerated bookbuilds −2.55%.
- **Korea:** untested. In H1-2026 KOSPI rose 101% while paid-in issuance fell 55.5%.

**Test:**
- Korean event studies, 2010–2026, using DART timestamps.
- At least 30 events per screen.
- Abnormal returns net of costs.
- **Pass:** the exclusion improves the family's Sharpe or drawdown with paired-bootstrap share ≥ 0.95.

**Priority: P2.** These are cheap risk screens; the executives triaged them as BUILD NOW.

### BL-O04 — Buyback-and-cancel eligibility as a fundamental-family feature (executive SHADOW S7)

**Status v2.0: OPEN · P3** (no council ruling).

- **Evidence:** n = 1 locally. The day after its announcement, SK hynix rose 12.7% vs KOSPI +5.9%.
- **Test:** ≥ 30 events with DART timestamps.
- **Priority: P3.**

### BL-O05 — Political/geopolitical shock flag, exposure cut only (executive K12; E4-R6, with the × 1.5 leg deleted)

**Status v2.0: OPEN · P3** (no council ruling).

- **Evidence:** in the Dec-2024 martial-law episode no day moved more than ±3%, and the peak-to-trough was −5.6%.
- **Test episodes:** THAAD 2017, North Korea 2017, Dec-2024, Apr-2025.
- **Priority: P3.**

### BL-O06 — Stock-level microstructure (executive K13)

**Status v2.0: OPEN · P3** (no council ruling). KIS minute bars are in BL-D03. R-27 fixes the bar convention: `bar_end` stamps, with the closing auction as its own bar.

**Candidates:**
- last-10-minute reversal on expiry days (KDI found last-10-minute variance ≈ 7× normal on option expiries);
- Korea's overnight vs intraday split;
- reversal after volatility interruptions.

**Note:** the index-level expiry fade is refuted (§6).

**Data needed.** KIS minute data.

**Priority: P3.**

### BL-O07 — Factor momentum: each family's own trailing 12-month sign as a gate (executive K15; E5-C7)

**Status v2.0: OPEN · P3 (CONFIRMED by QF5-A25).** Gross, the 12-month factor-momentum de-risk gate raised Sharpe in 28 of 32 factor-region cells (mean +0.062), and in 21 of 32 after the 2019 publications. Net of 50 bp it is negative in 5 of 6 regions: gate turnover (≈ 2–3 switches a year × 2 legs) costs more than the gain. Macro factor timing stays prohibited.

- **Source:** Ehsani & Linnainmaa (NBER w25551).
- **Test:** on QUANTGEN's five families, with the result de-risk only (≥ 0.5).
- **Priority: P3.**

### BL-O08 — Calm-state reversal down-weight (the dissent recorded in PC-P-06)

**Status v2.0: OWNER-DECISION D3; stays P3** (QF5-M10, CQ-22; QF5-A13). See §1.6 D3.

**The principle at stake.** Using a VIX level as a mean gate on the reversal family would break design principle P3: macro and stress variables size risk, never set direction.

**The vote.** The Professors REJECT the change; the Executives and QF route it to the owner as a principle change. All three recommend against adopting it in v2.

**Evidence:**
- **v1.x.** ST_Rev returned −1.2%/yr when VIX ≤ 20, vs 23.2%/yr otherwise (2008–26).
- **Council restatement.**
  - On the true VIX ≥ VIX3M flag (t−1 timing, 2007-12 → 2026-08), reversal earned 59.2%/yr at 34.8% vol, vs 1.8% at 12.3% otherwise. The μ/σ² ratio is 4.1× (QF5), so mean-variance would up-weight in stress, which design principle P2 forbids.
  - Reversal's 1.0× rests on P2, not on μ/σ² (QF5-A13). "Never cut in stress" is strongly supported; "1.0× in calm" is the weak cell.
  - The evidence is US, gross and one regime (VIX ≤ 20: −1.15% a year).
  - There is no Korean net-of-cost test.

**Test (ST-11).** One pre-registered cell (0.5–1.0 multiplier when VIX ≤ 20):
- run as a KRX stock-reversal test, net of 35 bp plus the 0.20% sell tax;
- 0.5× in calm must beat 1.0× at one-sided p ≤ 0.10 in both 2010–17 and 2018–26.

The owner may reopen the principle only after this passes.

**Data needed.** KIS stock-level data (BL-D03).

**Priority: P3** (it is not raised to P2 before the owner rules; QF5-A13).

### BL-O09 — Re-run macro priors on real-time vintages (executive K17; T1-C2)

**Status v2.0: OPEN · P3; vintage storage moved to R-13.** R-13 stores the first print, the current value and the vintage date for revised series (QF2-M6), taken from ALFRED (BL-D04, P1). Why it matters (QF2-A19): 2025 payrolls averaged +119.4k a month in first prints vs +9.7k in the current vintage, and the current-vintage Sahm rule triggers 1–2 months earlier in 1980, 1990 and 2008 and adds a 2003-07 false trigger. The re-runs listed below stay P3.

**Scope:**
- ALFRED re-runs of Sahm, the curve probit and Taylor rules;
- SPF dispersion vs volatility;
- the macro-nowcast EPS gap;
- an FOMC dissent count.

**Priority: P3.**

### BL-O10 — KOSPI–China partial correlation (executive K18)

**Status v2.0: OPEN · P3** (no council ruling).

- **Question:** what is the KOSPI–China correlation once the overnight SOX and Nikkei moves are controlled for? This is risk-model research.
- **Evidence:** the daily KOSPI–Shanghai correlation reached 0.56 in 2026, the sample high.
- **Priority: P3.**

### BL-O11 — Dollar gate for EM/Asia momentum (executive K19; Q1b-C12)

**Status v2.0: OPEN · P3 (confirmed).** QF5 reproduced it: 3.32% vs 16.63% a year, t −2.63 with HAC (the artifacts give −2.76), using the t−1 three-month change of the monthly-average broad dollar. The same-month version gives t −0.85, so the result is specification-fragile.

**Evidence:**
- With the USD trend defined as the monthly-average 3-month change, EM WML earned 3.3% in USD-up months vs 16.6% in USD-down months (t −2.76). A 0.5× gate gives EM +0.24 (share 0.96) and APxJ +0.18 (0.95).
- With the month-end DTWEXBGS 60-day change instead, the effect **vanishes** (EM +0.03).

**Test:** pre-register one definition and test it out of sample.

**Priority: P3.**

### BL-O12 — E5's system-level limits (E5 round 1; only the single-name cap and the drawdown ladder were ratified)

**Status v2.0: OPEN · P2** (no council ruling). Related SPEC v2.0 rules: R-07 (Korea caps on look-through; the hard stop with an explicit re-arm) and R-26 (leveraged and inverse ETF instrument rules).

**Proposed limits:**
- KOSPI200 futures delta ≤ 1.0 × NAV;
- Korean small/mid caps ≤ 25% of gross;
- options: no net short gamma beyond 0.5% of NAV per 1% index move;
- API heartbeat lost for > 60 s → cancel orders and stop new entries;
- position-reconciliation failure at 15:45 KST → flatten intraday sleeves.

**Action (v1.1):** these were drafted for a book with a broker connection. Mapped onto QUANTGEN:
- **Simulated-book risk limits in `core/quant/risk`:** KOSPI200 futures delta ≤ 1.0 × NAV; small/mid caps ≤ 25% of gross; the net short-gamma limit, shown on the Derivatives page.
- **Feed heartbeat lost > 60 s:** engine HALTED (spec §3.8).
- **Blocked by read-only design (§5c):** "cancel orders" and "flatten intraday sleeves after a reconciliation failure". There are no real orders or positions.

**Priority: P2.**

### BL-O13 — Stock–bond regime variable and JPY hedge conditioning (PC-P-18 caveat; Q1a backlog item 6; professors' ledger)

**Status v2.0: OPEN · P3.** Cross-asset regimes belong in the risk model only (X-EX1-N6; R-09). A turbulence-based stressed covariance must beat the stock–bond-regime input in a pre-registered test before it is used (QF5-M7; ST-08).

- **Questions:** is inflation *volatility* (rolling std of monthly core PCE) a better stock–bond regime variable than inflation *level*? Should the JPY hedge be conditioned on the direction of real yields?
- **Evidence:** the stock–bond correlation was positive in 1990–99 even with core PCE below 2%. USD/JPY rose 27.4% in 2022.
- **Priority: P3.**

### BL-O14 — Other professor items

**Status v2.0: OPEN · P3.** The change-point exit feature (P6-C4) is now CONTEXT-ONLY. A BOCPD scale-break probability (hazard 1/250, declared prior) is written to R-18's research log only: never acting, never displayed (QF7-M4, CQ-17; R-33). NTFS and the ACM vs Kim–Wright cross-check are unchanged.

- **P1's near-term forward spread (NTFS) ±10% tilt** (dissent recorded in PC-P-15): untested.
- **Change-point detection as an exit feature** (P6-C4).
- **ACM vs Kim–Wright term premium cross-check** (Q1a backlog item 4).

**Priority: P3.**

---

## 4. UNTESTED items (re-statused in v2.0)

### BL-U01 — Korea leverage / flow / semis-cycle state (N-19) — the most important open item

**Status v2.0: OPEN · P1.** The inputs are logged as context from day one (R-13; QF1-M5, QF4-M8; CQ-11 to CQ-13), with timestamps: KOFIA margin debt, index and single-stock leveraged-ETF AUM and value traded, the leveraged share, the absorption ratio and turbulence. The 16-Jul-2026 rule break is flagged. QF1's mechanical-flow monitor is Σ AUM_i × L_i(L_i − 1), as a % of KOSPI200 closing-auction value (Tuzun 2013). Whether daily AUM history exists decides whether this state can be built before 2027 (QF1). The settling test is unchanged (ST-07), and any card needs ≥ 30 onsets.

**Hypothesis.** A Korea-local state built from leverage, flows and semiconductor-cycle inputs would have seen the 2026 deleveraging that every US input missed. Candidate inputs:
- KRX margin debt;
- leveraged single-stock ETF AUM;
- investor-type flows;
- the deceleration in DRAM contract-price guidance;
- an AI-financing monitor;
- a mega-supply flag.

**Why it matters:**
- 22 Jun–30 Jul 2026: KOSPI −38.6% with no US-sourced flag firing.
- KOSPI rv21 was above 30% on 88% of 2026 days.
- The drivers were single-stock leveraged ETFs (listed May-2026) and a margin-called AI fund.
- 4 circuit breakers and 15 sidecars fired in July.
- Retail bought a record ₩8.54tn on 23 Jun 2026, the −9.99% day.
- From 16 Jul 2026 new single-stock leveraged ETF listings were suspended, the investor deposit rose from ₩10m to ₩30m and the LP divergence limit fell from 3% to 2%: a structural break for this state, logged in `context_log`.

**Evidence so far (all n = 1):**
- DRAM contract guides slowed from +93–98% to +58–63% to +13–18% while the index topped in June.
- AI debt rose from ≈ 7% to ≈ 18% of US investment-grade issuance, with new-issue concessions up to 20 bp (published bank research dated 3 Aug 2026: https://www.goldmansachs.com/insights/goldman-sachs-exchanges/how-ai-debt-is-reshaping-the-credit-market).
- The mega-supply flag (SpaceX IPO 11 Jun, KOSPI peak 22 Jun, SK hynix ADR 9 Jul) fired on 10 Jul, after −20%, and saved 3.2 pp.
- The *level* version of the semis gate (E4's AI-hardware gate) is refuted: it stayed on through the crash and turned off at the trough.
- A trading-volume proxy for leverage fails out of sample (2014–26: MSE change −2.1% to +1.6%, Diebold–Mariano t ≤ 0.73), so margin debt and AUM / shares outstanding must be logged directly (BL-D02); do not build a volume proxy.

**Settling test:**
1. Build daily series for 2015–2026, or from the earliest available date.
2. Test whether the state leads KOSPI rv21 by ≥ 5 days.
3. Test whether it improves the ΔMDD of the Korea vol target (VT20) in ≥ 3 Korean episodes (2018Q4, 2020, 2022, Aug-2024, Jul-2026), with no episode above 50%.
4. Any multiplier needs ≥ 30 events and Tier B bounds ([0.5, 1.0]). It is registered as a protective card (spec §8.7); its forward record starts from the header commit.

For DRAM guides: use the TrendForce guide history for 2015–26 (≈ 45 quarterly observations), lagged to publication, against KOSPI's forward 20–60-day returns.

**Data needed.** BL-D01, BL-D02, BL-D10.

**Priority: P1.**

### BL-U02 — Korea factor priors (N-36)

**Status v2.0: OPEN · P1.** Until it runs net of 35 bp plus tax, R-15 stores the Korea reversal prior as 1 (UNVERIFIED), down from 3 (QF5-A14). The same KRX stock-level data feed owner decision D3's test (ST-11).

**Evidence (literature only, P3-C22):**
- Korean 12-1 momentum was significantly negative in high-turnover stocks (Jul-2000 to Jun-2019).
- Over 1999–2021, the Fama–MacBeth coefficient on the prior-month return was −2.950 (t −3.77), a regression slope, not a strategy return, and pret(12,7) 0.531% a month: Korean momentum profit is reversal carry-over.
- Locally, KOSPI index trend is weak protection, not a return source: SMA10m vs the same-exposure static book gives ΔSR +0.076 and ΔMDD +4.1 pp, but its daily tail ratio 0.93 fails PC-2, it adds +2.2 pp on VT20 and −2.3 pp on 2016–26. (The earlier "long/flat 0.47 vs buy-and-hold 0.52" priced flat months at 0% with no static comparator.)

**Test:**
- **Data:** KIS stock-level data, 2000–2026 or as available.
- **Signals:** 12-1, 12-7 and residual momentum; 1–5-day and 1–2-month reversal; flow.
- **Costs:** QUANTGEN's KRX stock rate, 35 bp per side (70 bp round trip; it covers the 0.20% sell tax), and the 2× stress at 70 bp per side.
- **Splits:** by turnover and by VKOSPI tercile.
- **Also test:** the D&M gate on the KOSPI market state.
- **Pass:** gate PASS for each family card (interval clears zero, deflated Sharpe ≥ 0.95, Sharpe > 0 at 2× costs).

**Data needed.** BL-D03.

**Priority: P1.** Spec R-15 is currently UNVERIFIED for Korea.

### BL-U03 — Macro-surprise |z| → next-open volatility forecast (N-42; EC-E-18; executive K6)

**Status v2.0: OPEN · P2; the first step is runnable now.** Hourly bars (^KS11, 069500.KS; 730 days) and daily ^KS11 opens back to 1996 are local, so the variance content of the opening-gap night flag is testable (first-hour range, |open gap|). Run QF7-A28's event-conditional variance test (DM on the squared gap) before R-10's flag is kept as "log only". A related question (QF6): with 39% of KOSPI variance overnight, would an overnight-US input inside the vol forecast fix the Korea vol target's 2016–25 tail ratio of 0.95?

**Evidence:**
- surprises are priced in ≈ 5 ms;
- consensus puts ≈ 30% weight on the prior print, and up to 25% of the "surprise" is predictable;
- 7 of 21 US releases drift in the 30 minutes before publication.

**Test:**
- **Measure:** the KOSPI200 futures opening gap and first-30-minute realised vol on high-|z| vs low-|z| US release nights, 2016–26, using an anchoring-adjusted |z|.
- **Pass:** both measures are significantly larger (t ≥ 2) on high-|z| nights, **and** a |z|-scaled vol forecast reduces sizing error relative to the SMA20 forecast.

**Data needed.** BL-D05; KOSPI200 futures intraday data.

**Priority: P2.**

### BL-U04 — Overnight information used legitimately on KOSPI open-to-close returns (Q1b open question 2)

**Status v2.0: CLOSED** (tested; QF1-A11, QF2-A9).

- **Tested on vendor OHLC; closed as a research note, not a signal.** The prior US session explains the opening gap (R² 0.32) but not the open-to-close return (R² 0.003 in 2016–26, 0.031 in 2005–16, 2.5% over 1997–2026). On tradable KODEX 200 the open-to-close reversal (t −2.6 after 2016; +5.6 bp net per trade) is absent in 2008–16, so it is fragile. Use the gap as a gap and volatility input only (P4); do not reopen the SOX gate.
- **Priority: closed.**

### BL-U05 — Drivers for markets QUANTGEN has no sleeve for (prior design, Part 2)

**Status v2.0: OPEN · P3** (no council ruling).

- **Candidates:** Europe BTP–Bund spread and TTF gas; China credit impulse, policy calendar and northbound flows; India FII flows and RBI; PMI-based tilts.
- **Status:** untested; needs data (PMI licensing).
- **Priority: P3.**

### BL-U06 — Crypto microstructure (prior design)

**Status v2.0: OPEN · P3.** R-17 specifies the crypto clock for the deferred sleeve: `decision_time_utc('CRYPTO', d)` = the 00:00:00Z venue bar close, with annualisation at 365 (QF2-M9).

- **Candidates:** funding-rate extremes as a reversal trigger; exchange flows; stablecoin supply.
- **Status:** untested.
- **Priority: P3** (sleeve not built).

### BL-U07 — Why the gold level broke (Q1a)

**Status v2.0: OPEN · P3** (context only; no council ruling).

- **Evidence:** the 2006–21 level fit implies $626 vs $4,187 actual. Official-sector buying is unverified as the cause.
- **Data needed.** WGC/IMF central-bank purchase data.
- **Priority: P3** (context only).

---

## 5. Data acquisitions v2 (consolidated from v1.2, the QF papers and the data labs)

**What changed from v1.2.**
- **Kept:** the 20 v1.2 rows (BL-D01–D20), updated.
- **Dropped:** needs that only S1 had (the KRW regime split; the TWD and JPY closes for pooling).
- **Re-set:** priorities follow the council's rulings.
- **Added:** 11 rows (BL-D21–D31) from the QF papers' data lists (QF1 §8, QF2 §4.4 and §7, QF4 §9, QF5 §8, QF6 §4.7) and the data labs' caveats (DL-A §8).

**Columns.**
- "Source" stays "to verify", as in v1.2.
- "Licence / access" quotes only what the files record; "not recorded" means the files say nothing.
- "Needed by" names the SPEC v2.0 module, the backlog item or the §1 settling test.

| ID | Data (and its timing rule) | Source (to verify) | Frequency | Licence / access (as recorded) | Needed by | Priority |
|---|---|---|---|---|---|---|
| BL-D01 | KRX investor-type daily net buys (foreign / institution / individual), lagged to t−1; intraday preliminary figures with their timestamps | KIS Developers / KRX data portal | Daily (+ intraday preliminary) | Not recorded | R-13 context_log (flows); BL-C06; BL-U01; ST-07 | **P1**: log from day one |
| BL-D02 | KOFIA margin debt; KRX single-stock and index leveraged/inverse ETF AUM, creations/redemptions, value traded and prices (single-stock ±2× products listed 27 May 2026) | KRX / KOFIA / issuers | Daily | Not recorded. Historical availability is unknown (QF1 open question): it decides whether BL-U01 can be built before 2027 | R-13 (QF1-M5, QF4-M8); R-26 leveraged/inverse instrument rules (QF6-M9); R-07 look-through at × L; BL-U01; BL-C14; ST-07 | **P1** |
| BL-D03 | KIS stock-level OHLCV (KOSPI/KOSDAQ universes, survivorship-free); 1- or 5-minute bars (KOSPI, KOSPI 200, KODEX 200); level-1 quote snapshots with bid/ask and exchange vs receipt timestamps (069500 and 005930 at 15:19:59 KST; KODEX 200 bid/ask and the closing auction's expected price and imbalance on stress days). No fill logs exist (§5c) | KIS Open API | Daily; intraday; snapshots | The first milestone task is to confirm the KIS level-1 quote fields (QF1-A25) | BL-C02; BL-U02; BL-O06; ST-11 (D3); R-08 annotation (spread snapshots on flag days); R-26 stress-cost line; R-27 fill model; R-10 measurement; a HAR-RV challenger (R-30) | **P1** |
| BL-D04 | ALFRED vintages for UNRATE, PAYEMS, GDPC1, GDPPOT, NROU, PCEPILFE, CPIAUCSL | St. Louis Fed ALFRED; FRED API `output_type=4` (initial release only) and `vintage_dates` | Per release | API limit of 1,000–2,000 vintage dates per request; "an hour of work" (QF2) | R-13 (first print + current value + vintage date; QF2-M6); BL-O09 | **P1** (cheap) |
| BL-D05 | Consensus forecasts with survey-close timestamps (CPI, NFP, ISM) | A licensed consensus feed | Per release | Licensed | BL-U03; BL-C09(c) | P2 |
| BL-D06 | 30-minute TIPS and nominal futures around CPI/FOMC, 2004–2026 | Intraday futures vendor | Intraday | Vendor | BL-C09(a)(b) | P3 |
| BL-D07 | ICE BofA HY OAS from 1997 | ICE | Daily | ICE licence (the FRED copy starts 2023-10) | BL-C03 | P3 |
| BL-D08 | CFTC Commitments of Traders | CFTC | Weekly report | Not recorded | BL-C14; the FX sleeve's positioning leg | P3 |
| BL-D09 | PMI (ISM / S&P Global) | Licensed | Monthly | Licensed | BL-U05 | P3 |
| BL-D10 | TrendForce DRAM contract-price guide history (≈ 45 quarterly observations, 2015–26); an AI-debt / new-issue-concession tracker | TrendForce; build or scrape | Quarterly guides; event | Not recorded for TrendForce; AI-basket spreads would need a licensed source (ICE/Bloomberg; E6) | BL-U01 | P2 |
| BL-D11 | Long front-month Brent futures history (not continuous-adjusted), with Dated Brent spot named separately | Exchange / vendor | Daily | Not recorded | BL-C11 | P3 |
| BL-D12 | VKOSPI daily history. It closes at 15:45 KST, after the 15:30 decision: use K−1 or a 15:30 live snapshot | KRX Data Marketplace (data.krx.co.kr), index statistics | Daily | Not recorded | ST-09 (HAR-IV via R-30); R-13 VRP context; BL-C05 | P2 |
| BL-D13 | BoK ECOS USD/KRW 15:30 close: 731Y003, item 0000003, daily 1990-03-02 → 2026-10-01; also the "종가" series (2024-07+). A KRW input is a timestamped 15:30:00 KST snapshot (versioned; 15:00 before Aug-2016). DEXKOUS is a labelled proxy only. (TWD and JPY closes dropped with S1) | BoK ECOS API (= BL-G04; a new ECOS provider in `core/ficc/data`, proposed) | Daily | Free key | R-11 refusal book (a P3 formality rerun; QF2-M8); R-09 display-only `fx_hedge_credit` (KRW input timing; X-EX2-N4) | P3 |
| BL-D14 | US 10y yields: the KIS US 10y yield quote with timestamps (KIS already quotes US yields); the U.S. Treasury daily par yield curve (quotes "at or near 3:30 PM"; "usually available … by 6:00 PM Eastern Time"; "may be delayed") with a logged posting time, as the history and end-of-day source; ^TNX as the live proxy. Log both channels (Treasury, H.15) to verify identical values and the actual posting times | KIS Open API; U.S. Treasury (https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/treasury-yield-curve-methodology); Yahoo | Daily | Treasury: free and published (QF2-A7) | R-19 publication calendar (Treasury ≈ 18:00 ET); R-09 `hedge_state` (corr63 on date-aligned pairs); the registry (QF2-M7); R-12 refusal-book display | **P1**: posting-time logging starts now. It is needed before the Treasury channel is called compliant for 1990–2009 (QF2) |
| BL-D15 | KOSPI200 constituent history 2010–26; MSCI Korea change history | KRX / MSCI | Event | Not recorded | BL-O03 | P2 |
| BL-D16 | DART / KIND filings: rights offerings, listings, lock-ups, buybacks | DART OpenAPI, KIND | Event | Not recorded | BL-O03, BL-O04 | P2 |
| BL-D17 | Korea CPI after 2023-11 (the local copy ends there); the BoK base-rate series | ECOS / KOSIS | Monthly; event | Not recorded | R-13 context log | P2 |
| BL-D18 | ACM term premium | NY Fed | Not recorded | Not recorded | BL-O14 | P3 |
| BL-D19 | SPF dispersion | Philadelphia Fed | Not recorded | Not recorded | BL-O09 | P3 |
| BL-D20 | WGC/IMF official gold purchases | WGC, IMF | Not recorded | Not recorded | BL-U07 | P3 |
| **BL-D21** (new) | **KRX official daily closes:** KOSPI from 1997-04, with the Saturday sessions before 1998-12-12 included; KODEX 200 and constituents; timestamped. Also the ETF iNAV at the close, for R-27's LP-exempt check (QF1-M6's version flags a KODEX pair residual above 30 bp) | KRX data marketplace, or the KIS history loader (QF4 open question: "KIS / FMP / KRX marketplace") | Daily | Not recorded | R-01 (official close primary; vendor secondary within 1 bp for indices, exact for stocks; QF2-M4); R-06 KR formal run (Level-2 tolerance against the vendor file; Resolution 1); R-22 objective episodes; R-27 | **P1**: blocks the R-06 KR formal run |
| **BL-D22** (new) | **Effective-dated calendars and regime tags.** KRX sessions: the 15:00 close before 2016-08-01; the CSAT-day close at 07:30Z; first-trading-day 10:00 opens; Saturday sessions to 1998-12-12; the lunch break to 2000-05; the random end, conditional until 2015-06-15 and unconditional ≤ 30 s since; the NXT 15:40–20:00 and KRX 16:00–20:00 after-markets (KRX from 2026-09-14). NYSE early closes; Fed and SIFMA holidays; Korean substitute holidays. Publication calendars: H.15 16:15 ET on D+1; H.10 Mondays 16:15 ET, or the next business day after a Fed holiday; Treasury ≈ 18:00 ET; BLS 08:30 ET; BoK decision ≈ 09:50 KST and press conference ≈ 11:10 KST. Korean regime tags: price limits (±6% Apr-1995, ±8% Nov-1996, ±12% Mar-1998, ±15% Dec-1998, ±30% 15-Jun-2015); the 1997 won peg; short-sale-ban regimes; sell tax 0.30 → 0.15 → 0.20%; no ETF before Oct-2002 | KRX notices; Fed H.10/H.15 pages; Treasury; BLS schedules; SIFMA; KASI's holiday calendar; `exchange_calendars` XKRX (T3, open source) as a cross-check; press and broker notices for the regime dates (etoday, Shinhan, Hankook Ilbo, Herald Economy; Eom et al.) | Effective-dated | `exchange_calendars` is open source; the rest is not recorded | R-20; R-19; R-10; R-22 regime lines; T-AVAIL-01; T-CLOSE-02 | **P1** (R-20 is P0, M1) |
| **BL-D23** (new) | **Kenneth R. French daily Mkt-RF and RF, 1926-07 → 2026-08** | Kenneth R. French Data Library | Daily | DL-A's fetch was refused (HTTP 403). The local daily files start 1990-01-02 (DLA-U6) | ST-01: the R-29 settling run | **P1**: blocks ST-01 |
| **BL-D24** (new) | **KOSPI 200 futures and mini KOSPI200:** daily OHLC and settlement, front month, roll-adjusted with roll dates, back to 1996 if available | KRX / KIS | Daily | Not recorded | R-26 granularity floor and roll-cost line (QF1-A17); the R-06 KR futures line (only above the notional floor); BL-G08; ST-05 | P2. QF6 proposed P1, but the council made the futures line conditional on the notional floor (X-EX2-N3; D5) |
| **BL-D25** (new) | **KTB 3y/10y futures and KRX USD futures,** daily history from 2006, with roll calendars | KIS (QUANTGEN's KIS feed carries KOSPI200, KTB and USD futures; QF5) | Daily | Not recorded | ST-05 (QF5-M8); the R-17 FX sleeve's declared instrument (KRX USD futures) | P2 |
| **BL-D26** (new) | **US index futures** (Micro E-mini ≈ ₩52m a contract; E-mini): quotes via KIS (to confirm; QF5 open question) and CME front-month history with a declared roll calendar | KIS / CME | Daily | Not recorded | The R-29 instrument book (D5 option (a)); the R-26 roll-cost line | P2: promotion waits on D5 |
| **BL-D27** (new) | **KOSPI 200 option-board snapshots:** QUANTGEN's own model-free implied variance and ATM/25Δ vols at 15:30 KST (`timing: live`) | KIS option board (already read by the Derivatives page) | Daily (+ intraday optional) | "Costs nothing" (QF6) | R-13 live implied-vol snapshots (QF6-M6); VRP context (QF6-M10); R-16 implied mode; ST-09 (≈ 2 years of boards needed) | **P1**: start logging now |
| **BL-D28** (new) | **KOSPI 200 options EOD:** settlement prices, IV by strike/expiry, open interest | KRX Data Marketplace | Daily | Not recorded | R-16 surface history and skew; MFIV reconstruction; the short-vol card's history (the public page withholds that card "until a history of boards exists") | P2 |
| **BL-D29** (new) | **VIX and VIX3M live snapshots at 16:00 ET** | Cboe, via a licensed or delayed feed | Daily | Licensed or delayed feed (QF6) | R-13 (QF6-M6); ST-09 | P2 |
| **BL-D30** (new) | **Daily ETF constituent baskets (PDF)** for KODEX 200 and the leveraged products | KIS or KRX (to confirm; QF4 open question) | Daily | Not recorded | R-07 look-through caps (QF4-M4; leveraged products at × L) | **P1** (R-07 is P0, M5) |
| **BL-D31** (new) | **Korean call rate, daily,** for the excess-return cash convention. Korean rates ran at 16–25% in 1997–98, so a raw Sharpe with cash at 0 is not a Sharpe ratio (X-PX2-N5) | BoK ECOS (to verify) | Daily | Not recorded (an ECOS API key, as for BL-D13) | R-22 excess returns; the R-06 KR formal run | **P1**: blocks the R-06 KR convention. The research files used the monthly CD rate from the end of its own month (PX2: a small lag issue) |

**Count: 31 acquisitions.** By priority:
- **P1 (11):** D01, D02, D03, D04, D14, D21, D22, D23, D27, D30, D31. BL-D03 includes the milestone-1 quote-field check.
- **P2 (11):** D05, D10, D12, D15, D16, D17, D24, D25, D26, D28, D29.
- **P3 (9):** D06, D07, D08, D09, D11, D13, D18, D19, D20.

---

## 5a. Data-quality log (new in v2.0)

These are data problems found during the council round, with their evidence and the SPEC v2.0 control that stops each one recurring. The rule behind every control:
- the official KRX or KIS close is primary;
- the vendor is secondary, accepted within 1 bp for indices and exactly for stocks;
- provisional, stale-carry and bar-derived rows are rejected;
- nothing is auto-corrected: a mismatch raises an alert and fails closed (QF2-M4; R-01).

| ID | Series / source | Problem (evidence) | Found by | Status and v2.0 control |
|---|---|---|---|---|
| **DQ-01** | `yahoo_daily/`, every Asian 2-Oct-2026 row | **The 2-Oct intraday-print incident.** The file was written at 10:56:46 KST on 2 Oct, mid-session. KOSPI's "close" of 6,943.66 was an intraday print (volume 99,651 against a final 227,641, i.e. a ~10:30 KST print). The official close is **7,003.74** (+0.46%, not −0.40%). Other rows: KOSDAQ 893.82 → 893.29; Samsung ₩273,750 → ₩276,000; SK hynix ₩1,832,000 → ₩1,841,000; Nikkei 68,219.06 → 68,309.46; TAIEX 48,223.71 → 48,475.74; HSI 23,938.95 → 23,945.02. HSI was intraday in both files, because Hong Kong closes at 17:00 KST. The SPEC's v1.2 PIT audit accepted the row (available 01:30Z ≤ 06:30Z): nothing distinguished a provisional value from an official one | QF1-A3, QF2-A1, QF4-A12, QF6-A12 (Hankyung 15:38 KST; SBS 15:52 KST) | Patched (DQ-02). **R-01:** `value_status`, `session_date`, `retrieved_at_utc` and a provisional-row guard. **T-PROV-01:** MissingInput at 10:31 KST; 7,003.74 at 16:00 KST. **T-FIX-01:** refuses a fixture whose last row was retrieved before the official close + 10 min |
| **DQ-02** | **The patch: 2026-10-02 17:20 KST.** Log: `quantgen_macro_data/results/QF0_data_patch_20261002.csv` | **60 actions** (55 on 2 Oct; on 3 Oct, 3 duplicate-date drops and 2 provisional `yahoo_long` rows). 7 closes were replaced in `yahoo_daily` (^KS11, ^KQ11, 005930.KS, 000660.KS, ^N225, ^TWII, ^HSI), and 1 in `yahoo_long` (^HSI, 23,936.93 → 23,945.02). Provisional 2-Oct bars of 24-hour instruments were dropped: in `yahoo_daily`, KRW=X, JPY=X, CNY=X, EURUSD=X, TWD=X and BTC-USD; in `yahoo_long`, KRW=X and JPY=X, and on 3 Oct CL=F (91.90) and GC=F (4,211.0), whose 2-Oct bars came from the 15:55 KST fetch, mid-Globex. The partial-month 2026-10 row was dropped from 39 `yahoo_monthly` files, so month-end series now end 2026-09. The official closes came from Yahoo `regularMarketTime`, after each session's close (`CATALOG.md`). Pre-patch files are kept in `_snapshots/` (`yahoo_daily_as_fetched_20261002_1056KST`, `yahoo_long_as_fetched_20261002_1555KST`, `yahoo_monthly_as_fetched_20261002_1056KST`) | Patch log (`CATALOG.md`); recomputed by DL-A §7 | **Effects (DL-A §7): 24 values corrected, 12 unchanged, no verdict changed.** Examples: the drawdown from the peak is −23.2% (not −23.8%); close / 200-day 1.107 (not 1.098); rv20 28.8% (not 28.9%); vt decided at the 2-Oct close 0.694 (PAGE `w_next` 0.691 → 0.694); G-KR-01 0.637; G-KR-02 0.641 / 0.638 / 0.609; §8.9 p_ni at 10-session blocks 0.246; pair share ≈ 53.6%; KRW=X now ends 1 Oct at 1,356.84 (20-observation change −0.11%, not 1,360.63 / +0.38%), and the S1 flag stays OFF. The corrected values reach SPEC, REPORT and PAGE through `QC_errata.csv`. **Not recomputed after the patch:** cap-1.5 VT Sharpe 0.534, SMA60 0.550, EWMA (half-life 10) 0.607, EWMA at 35 bp 0.573, the Korea stock-book 2× ΔSR −0.061 and the R-11 protective rows. Their rerun is a SPEC-REWRITE §9.3 item. **UNVERIFIED:** Seoul Shinmun reports the 2-Oct USD/KRW close as 1,350.6 (search snippet only). GC=F's duplicated 1-Oct row 4,177.2 was provisional; the 3-Oct patch keeps the settled 4,202.3 (likewise CL=F 92.87 and DX-Y.NYB), and A12 was regenerated. **Before freezing fixtures,** regenerate the R4/R4b golden values on the official closes (BL-G05 → R-01) |
| **DQ-03** | ^GSPC opens (Yahoo) | The open equals the previous close on 41% of days: 97–100% in 1996–2005, 25–78% in 1990–95 and 2006–07, near 0 after 2008. DL-B puts it at 94–98% of 1996–2005 days. Garman–Klass, Rogers–Satchell and Yang–Zhang are invalid for the US index before ~2008; Parkinson is not affected. The problem was not flagged in `QF0_yahoo_long_quality.csv` | QF1 §4.8; QF6 §4.8; DL-B | **OHLC open-quality flags** (QF6-M11; R-01). Use SPY for any open-based US work (QF1). A tripped flag sends R-30's range estimators back to SMA20 (fail-closed) |
| **DQ-04** | JPY=X (Yahoo) | A vendor error on 2008-12-08 (+17.7%) | QF5 (filtered in its pilots) | Add to the QF0 quality table and exclude it. The FX OHLC is unreliable: use the close only (`CATALOG.md`) |
| **DQ-05** | 069500.KS, KODEX 200 (Yahoo) | An **800-day hole, 2007-02-08 → 2009-04-17**, so the GFC is missing; 578 NaN-close rows are dropped by the loader | QF1-A24; `CATALOG.md` | Listed in the QF0 table (QF1-A24). Formal Korea runs use KRX official closes (BL-D21) |
| **DQ-06** | 000660.KS, SK hynix (Yahoo) | `adjclose` is **negative on 778 rows up to 2002-12-26**. The raw close has split-type jumps (use adjclose otherwise) | QF1-A24; `CATALOG.md` | Listed in the QF0 table. Never stored as a close (R-01) |
| **DQ-07** | KRX hourly bars (Yahoo, last ~730 days) | **The closing auction is missing.** On 727 of 729 days the last bar is 14:00–15:00. The 15:00–15:30 segment, auction included, is absent; the stub bar appears only on the fetch day. Last-bar close vs official close: median 13.7 bp, p95 59 bp, max 205 bp (2026-06-23); for Samsung, median 26.5 bp and max 388 bp. On CSAT days the bars stop at 15:00, although trading ran to 16:30 | QF2-A23 (QF2-C2); confirmed by EX2 | **R-27 bar convention:** `bar_end` timestamps, with the closing auction as its own bar. A daily close is never derived from bars (R-01) |
| **DQ-08** | KOSPI before 1998-12-12 (Yahoo) | **Saturday sessions are omitted.** 1997–98 Monday returns therefore span two sessions: the Monday / Tue–Fri variance ratio is 2.30, against 1.33 / 1.15 / 1.11 in later regimes | EX2 (X-EX2-N1) | R-20 regime tag `saturday_session`. Formal Korea runs use KRX official closes with the Saturday sessions included (Resolution 1; BL-D21) |
| **DQ-09** | KRX daily price-limit regimes | ±6% (Apr-1995), ±8% (Nov-1996), ±12% (Mar-1998), ±15% (Dec-1998), ±30% (15-Jun-2015). Pre-2002-10 episodes ran under different limits | EX2 (X-EX2-N1; etoday, Shinhan notice) | R-20 tag `price_limit`; per-regime lines on every long-sample card (R-22); regime metadata in the R-16 replay library |
| **DQ-10** | Other Korean market-structure breaks in long samples | A lunch break until May-2000. A 15:00 close until 2016-08-01, so 142 sessions of the golden sample closed at 06:00Z. The conditional random end until 2015-06-15, unconditional and ≤ 30 s since. The CSAT-day close at 07:30Z; 10:00 opens on first trading days. The won pegged near 914–915 until late Oct-1997. No ETF before Oct-2002. Four short-sale-ban regimes. The after-markets (NXT 15:40–20:00; KRX 16:00–20:00 from 2026-09-14) | QF2-A12, QF2-A13; QF1-A4; EX2 (X-EX2-N1) | R-20 tags. **T-CLOSE-02** tests the special closes; KRX `available_at` is bounded at 06:30:30Z. A vendor "last" after 15:30 is never stored as the close (QF2-A13) |
| **DQ-11** | ^KS11 (Yahoo) | Flat zero-volume rows on 2024-09-12 and 2026-06-29. The 29-Jun close is valid (8,394.65, SEDaily), but its OHLC is missing. There is no close on 2011-10-04, a real session | QF1-A24; QF2 §4.5 | Flat rows are dropped from OHLC-based statistics (QF1-A24). R-01 never stores a flat zero-volume close as a close |
| **DQ-12** | 005930.KS, Samsung (Yahoo) | **Stale-carry rows** (flat OHLC, zero volume) on real sessions: 2020-03-09, 2020-03-12, 2017-09-26, 2022-01-26 and 10 more Jan–Mar 2022 rows. **The 50:1 split:** Yahoo's close is already split-adjusted (2018-04-27 = 53,000). The halt rows 2018-04-30 → 05-03 are flat with zero volume | QF2 §4.5, §4.6 | QF2-M4 rejects stale-carry rows. A corporate-action table flags halt rows, which are not read as zero returns |
| **DQ-13** | 252670.KS, KODEX 200 Futures Inverse 2X | It traded at ₩62–130 in 2026 (₩69), so one tick is 77–161 bp. Daily returns are quantised in 1–1.45% steps on 42% of 2026 sessions. It returned −99.3% over 2016–2026 | QF1-A6; QF6 §4.8 | **R-26 tick floor** (T-COST-02: 252670 at ₩69 is charged ≥ 72 bp per side). It is unusable as a return series without a tick-noise filter |
| **DQ-14** | Yahoo FX daily bars | Stamped at UK midnight, so lag them for the KRX and US closes. FX and GC=F OHLC are unreliable: use the close only | QF5 §9; `CATALOG.md` | R-19 / R-20 availability. KRW inputs are the ECOS 15:30 close or a 15:30:00 KST snapshot (Resolution 8; BL-D13) |
| **DQ-15** | DEXKOUS (FRED H.10, noon New York) | It differs from the ECOS 15:30 Seoul close by up to +5.8% in a crisis (30-Dec-1997). It prints on Seoul holidays (18-Dec-1997). Policy froze the onshore price (the Sep–Oct 1997 peg) | EX2 (X-EX2-N4) | A labelled proxy only. Any FX-based rule records the FX regime as metadata (X-EX2-N4) |
| **DQ-16** | Cross-market close times | The Nikkei close moved from 15:00 to 15:30 JST on 2024-11-05, so it now falls at the same instant as the KRX close (06:30Z). Shanghai (≈ 16:00 KST) and HKEX (≈ 17:00 KST) close after the KRX close (UNVERIFIED) | QF2-A21; QF5 | A general `usable_at` rule: a datum is usable only if official_close_utc(market, D) + buffer < decision_utc (R-19) |
| **DQ-17** | FRED SAHMCURRENT / SAHMREALTIME | Vendor values span the missing Oct-2025 observation. SAHMCURRENT shows 0.25 for Oct-2025, although UNRATE Oct-2025 is missing; SAHMREALTIME for Nov-2025 is 0.43 (0.35 current) | QF2-A20 | R-13 computes Sahm in-house (a gap gives NaN); T-MISS-01 |
| **DQ-18** | Research-dataset vintages | French factor returns "differ substantially depending on when the data were downloaded" (Akey–Robertson–Simutin) | QF2-C14 | Every fixture is hashed; golden values are vintage-bound (R-01) |
| **DQ-19** | Narrative macro numbers | Payroll benchmark revisions were quoted at preliminary values (−818k for 2024, −911k for 2025). The finals are −598k NSA (2024) and −898k SA / −862k NSA (2025). 2025 payrolls averaged 119.4k a month in first prints vs 9.7k in the current vintage | QF2-A18, QF2-A19 | Erratum applied (§6.6). R-13 stores the first release and the final with vintage dates (BL-D04) |
| **DQ-20** | Press numbers typed by hand | JoongAng printed 6,917.35 for 1 Oct, where its own points and percent imply 6,971.35 | QF2 §4.5 | An internal-consistency check (level, points, %) for any number typed from the press (QF2-M4) |
| **DQ-21** | Korean cash rate in research scripts | `qf5_common.rf_daily_kr` uses the monthly CD rate from the end of its own month, a small lag issue. Korean CD rates are monthly only | PX2; QF5 | A daily call rate (BL-D31) for R-22's excess returns |
| **DQ-22** | Checked and found sound, or UNVERIFIED | **Sound.** Crash-day closes reconcile with the press: 4 Mar 2026 5,093.54; 23 Jun 8,203.84; 31 Jul 6,595.45; 5 Aug 2024 2,441.55. The zero-return day 2018-10-16 is genuine (2,145.12). **UNVERIFIED.** Treasury's 2026 par-yield row for 7 Jul (10y) looks like a transcription error by the fetch tool; 4 of 5 checked dates match DGS10 exactly | QF2 §4.5, §8 | No action for the sound rows. The Treasury row is covered by the posting-time and two-channel log (BL-D14) |

---

## 5b. Gate and integration items (new in v1.1; re-statused in v2.0)

### BL-G01 — B5 volatility-gate dependency for every vol-target card (moved to SPEC v2.0 R-30)

**Status v2.0: MOVED** to:
- **R-30**, where B5 becomes Stage 1 (calibration) of the staged estimator gate (BUILD, milestone M3);
- **R-16**, the Quant Lab envelope max(fast FHS, GJR-EVT).

v1.2's single-rule decision is withdrawn: "SMA20 if it passes; else EWMA(0.94); else provisional, with the card verdict capped at REVISE". B5 passes 7 of 9 KOSPI and 8–9 of 9 US forecasters (DLB-T1f), so it is necessary, not selective.

This section was rewritten per QCE-213 (items QF6-M1, QF6-A20, QF6-A25, X-PX1-N6, QF6-M2, QF6-M5).

**What (v1.1, kept for the record).** A vol-target card (spec R-06, the crypto vol cap in R-17, any per-market VT) could reach PASS only while its estimator passed B5. B5 is the architecture review's gate for the Quant Lab. It requires:
- rolling-origin 1-day 5% VaR exceedance within ±2 binomial SE of 5% over ≥ 200 origins;
- PIT uniformity.

Long-window GARCH(1,1)-t and GJR-t already pass B5 in the FHS form used for SMA20 (KOSPI 2001–26: 5.38% / 5.42%, PIT p 0.98 / 0.87; US 1995–2026: 5.17% / 4.91%). B5 is a calibration check: it passes 9 of 12 forecasters on KOSPI, so it cannot choose between them.

**Evidence so far (R4b, FHS form, daily origins):**
- **SMA20 passes on all three samples:**
  - KOSPI 2016–26: 4.70% exceedance, PIT p 0.11.
  - SPY 2016–26: 4.99%, p 0.57.
  - US 1991–2026: 5.31%, p 0.98.
- **EWMA(0.94) passes too:** 4.90% / 5.22% / 5.31%.
- **Normal form:** every estimator fails PIT (fat tails).
- **GARCH(1,1)-t on SPY** (refit every 7 sessions, 504-session window) breaches on 6.3% of days with PIT p < 0.001. That is consistent with the app's own REJECT (6.6%, PIT p 0.003; UNVERIFIED until `docs/vol_backtest.py` and its seed are published). Both are t-quantile (fan-tail) results; in FHS form only this 504-window GARCH fails on SPY (6.19%).
- **Caveat:** KOSPI SMA20 on the every-7th-session subsample breaches 7.55% (371 origins), just outside its band (2.74–7.26%).
- **Council (DL-B, DL-A):**
  - SMA20's KOSPI breaches cluster: Christoffersen p < 0.0001 on 2001–26 and 0.0006 on 2016–26 (DLB-T1f).
  - KOSPI 1997–2026: 5.04%, PIT p 0.46 (pass); Christoffersen p 4e-6 (DLA-G1).

**Settling rule (v2.0; SPEC R-30).** Stage 1 (calibration, necessary) is evaluated at the 21-day sizing horizon:
- FHS VaR exceedance, the 21-day fan PIT and Christoffersen conditional coverage;
- 95% and 99% VaR with Kupiec and Christoffersen CC, and ES 97.5% Z2 (QF6-A20; X-PX1-N6);
- 2016–26 and 2026 reported separately. GJR-EVT fails ES on 2016–26 (p 0.0125), while 2026 favours fast SMA20-FHS;
- 1-day VaR displayed only from models that pass the 1-day B5;
- VaR and labels scored with a strictly consistent score, tick loss (X-PX1-N4).

Stage 2 (the QLIKE MCS at h = 21) and Stage 3 (the economic choice) follow as written under BL-C04.

**Residual backlog task (P2).**
1. Publish `docs/vol_backtest.py` (proposed; the review's name) with its seed.
2. Run EX2's settling test: rerun B5 on SPY and KODEX 200 for 2016–26 and reproduce the app's 6.6% breaches and PIT p 0.003 (QF6-A25). Until then the app's GJR-on-SPY result is cited as UNVERIFIED.

**Data needed.** None beyond QUANTGEN's history loader: use the full available history, since 504 closes are too short for ≥ 200 origins on a long window. OHLC open-quality flags are needed for range proxies (R-01; §5a DQ-03).

**Priority: moved** (R-30, M3). The residual task is P2.

### BL-G02 — Protective-card harness in `core/quant/backtest` (moved to SPEC v2.0 R-21–R-24, R-34)

**Status v2.0: MOVED** to the v2 gate package. It is adopted once, blind, and frozen before the first formal card run (milestone M7):

| Module | What it contains |
|---|---|
| **R-21** | CARD-P gate v2: PC-1′ tail legs, PC-2 with a CI, a binding PC-3, the do-no-harm cap and the gate-acceptance test |
| **R-22** | Evaluation conventions: objective market-own episodes, excess returns, a declared start band, regime lines and the post-trough window |
| **R-23** | Step 3: the family trial ledger and N_eff = max(N_clusters, N_equiv) |
| **R-24** | Statistics and power harness: studentized bootstrap, SE ladder, power/MDE line, PBO on the card's own claim, Lo-adjusted Sharpe |
| **R-34** | Timing-fragility gate: a timing profile with a look-ahead positive control on every card |

Council items: QF3-A5, QF3-M1, QF3-M2, QF3-M3, QF3-M7, QF3-M8, X-PX1-N2, X-PX1-N3, X-EX1-N4, QF2-M2, QF4-M6, X-PX2-N5.

**What (v1.1, now inside those modules).** The pieces the gate needs for protective cards:
- overlay-on vs overlay-off on the same costed engine;
- the static same-average-exposure comparator S;
- PC-1..PC-7 (spec §8.7), with PC-1 replaced by PC-1′ and ΔMDD printed, never gated (R-21);
- the §8.6 episode table, which becomes a printed shock-type table beside the objective episodes (R-22);
- Politis–White block lengths on d and d² (R-24's block rule);
- one card per rule, through `docs/macro_overlay_study.py` (proposed).

**Acceptance.**
- **v1.1 regression check (kept).** The harness reproduces R4b's §8.9 numbers on the frozen fixtures within Level-1 tolerance. Examples: KOSPI VT20 at 3 bp, ΔMDD vs S +4.4 pp, tail ratio 0.82, p_ni 0.25; US VT15 at 50 bp, ΔMDD +0.2 pp.
- **Reference implementation.** DL-A's independent harness reproduces all 385 published R4b quantities to |diff| ≤ 1e-9 (DLA-T1).
- **v2.0 acceptance (R-21), run once with the results md5-frozen:**
  - at most 10% of 300 circular-shift placebos per family, and at most 2 of 20 per card, pass;
  - the negative controls all return REJECT or INSUFFICIENT: the US VT 5-day and 10-day at 50 bp, the post-shock-day and post-shock-week 0.5× rules, and a stale VT with σ lag 252;
  - on the US VT15 50 bp fixture the v2 verdict is INSUFFICIENT (ES21 +1.65 pp, ES126 +3.8 pp, p_ni 0.15);
  - the 5-day VT is REJECTed by the PC-3 point (ΔSR −0.29).

**Priority: moved.** It is P0 on the council's scale (M7, before any card runs).

### BL-G03 — A cost-aware vol-target card for the US (and the Korea stock book) (moved to SPEC v2.0 R-29 and R-26)

**Status v2.0: MOVED.** It now lives in two modules:
- **R-29, MACRO-R06-US-FUT:** the US index-futures vol target, a new card run FORWARD-SIM until the 1926+ settling run and a US sleeve exist (VALID-SHADOW, CQ-01 to CQ-04, ST-01; Resolution 2).
- **R-26:** the instrument book, declared notional, rebalance rule and no-trade band become pre-registered header fields. It adds a tick floor, a contract-granularity floor and no venue switch after results.

Council items: QF1-A1, QF1-A10, QF1-M2, QF4-A2, QF4-A21, QF5-A23, QF6-A8, QF6-M5, X-EX2-N3.

**Why (v1.2).**
- **US.** At QUANTGEN's 50 bp per side, the pre-registered US VT15 (SMA20, daily rebalancing) loses its drawdown benefit against a same-exposure static book: ΔMDD +0.2 pp, −3.4 pp at 2×. Its indicative verdict is REJECT (instrument: US shares via KIS, 50 bp, daily): a book-specific REJECT on a single-path PC-1 (ΔMDD bootstrap SD 7.8 pp; ΔES99 daily z 2.37), not proof that the rule does not protect. Under v2's PC-1′ it would read INSUFFICIENT, and it is not re-run (Resolution 2).
- **Korea stock book.** The Korea VT20 run as a KRX stock book (35 bp) fails the plateau check (0.375).

**Proposal: one new card per market (not a revision of the rejected one); instrument book first, band second.**
- **First, the instrument book (US).** A card on an index-futures line at 5 bp, declared before the run and counted as one more trial, run as FORWARD-SIM: indicative PASS on 1990–2026 on a knife edge (PC-1 margin +0.6 pp; 11 of 44 starts pass; 1990–2007 ≈ 0). Micro ES is about ₩52m, so it needs a sleeve of about ₩1bn. The band does not substitute for it.
  - **v2.0:** this is R-29.
  - It becomes BUILD-AS-INSURANCE only when (i) a US sleeve exists with one Micro ES ≤ ~5% of declared notional, or the owner declares another executable line (D5), (ii) ST-01 passes, and (iii) the blind v2 package applies.
- **Second, the holding period** (the gate's permitted fix vocabulary). The candidates:
  - a no-trade band (trade only when |Δw| > 0.10); or
  - a slower estimator (SMA40 / SMA60).
- **v2.0 (QF1-M2, QF6-M5): the band.**
  - It is permitted only on stock and US-share books. It is fixed at 0.10, declared ex ante, counted as one trial and never tuned.
  - It is not used on ETF or futures lines: there it gives no gain at 3–5 bp, and it cost 2016–26 crash protection (+4.4 → +3.2 pp).
  - At 50 bp a 0.10 band is still REJECT (+1.8 pp; 2×: −0.2 pp; DLA-U4). The instrument book decides the outcome, not the rebalancing rule.
  - Monthly and banded 50 bp variants are logged trials, never rescues (DNB #23).
- **Korea stock book (QF1-M2, QF4-A21).**
  - The band lowers p_ni from 0.173 to 0.074.
  - The weekly and monthly stock-book PASSes hold only under QF4's episode list. They are INSUFFICIENT under §8.6 (PC-4 0.50–0.56) and are re-run under the objective episodes once those are adopted (R-22).
  - A weekly stock-book card is an optional counted trial.
  - The 35 bp stock book is always a separate card, never a market-gross scalar (R-26).

**Post-hoc warning.** R4b's plateau grid shows slower windows doing better net of 50 bp in the US: window 40, ΔMDD +4.1 pp, ΔSR +0.02. That grid was computed after seeing the result. It is a reason to register the card, not evidence for it. All of its cells are counted in the family ledger (R-23).

**Priority: moved.** R-29 is P1 on the council's scale and runs at M8; R-26 is P0 and runs at M0. ST-01 tracks the settling run.

### BL-G04 — Timestamped USD/KRW history for the formal S1 card (P3; = BL-D13)

**Status v2.0: OPEN · P3.** This is a formality: S1 is retired (§6.7 #30). The ECOS 15:30 rerun is a P3 formality that cannot change the REJECT (QF2-M8; Resolution 8).

**Why (v1.2).** The KRW leg's gross edge depends on timing:
- +0.032 on DEXKOUS by value date;
- +0.016 at +1 session or on Yahoo timing;
- **+0.001 under strict H.10 publication.**

Production would have read the KIS fixing. The honest backtest therefore needs the ECOS 15:30 KST close history (a new provider in `core/ficc/data`, proposed), or a KIS fixing history if one exists.

**Not needed to decide S1.** S1 is a REJECT on the existing 1997–2026 history (54 strict-H.10 onsets; ΔMDD −1.3 pp; tail ratio 1.00), and an ECOS spot-check shows the proxy does not decide it. The history remains a cheap download (ECOS 731Y003/0000003, free key).

**Timing caveats (QF2-A24; X-EX2-N4).**
- The FX close moved from 15:00 to 15:30 on 2016-08-01.
- Onshore USD/KRW has traded 24 hours since 6 Jul 2026. A KRW input is therefore a timestamped 15:30:00 KST snapshot, versioned (15:00 before Aug-2016).
- DEXKOUS (New York noon) and the ECOS 15:30 close differ by up to +5.8% in a crisis (30-Dec-1997), and DEXKOUS prints on Seoul holidays.

**Priority: P3.**

### BL-G05 — Frozen fixtures for hermetic golden tests (moved to SPEC v2.0 R-01)

**Status v2.0: MOVED** to **R-01** (point-in-time discipline; BUILD, milestone M1, P0 on the council's scale). Its tests:
- **T-FIX-01:** a fixture whose last row has `retrieved_at_utc` < official_close_utc + 10 min is refused.
- **T-PROV-01:** on the 2-Oct fixture the store returns `MissingInput(provisional_intraday)` at 10:31 KST and 7,003.74 [`value_status=official_close`] at 16:00 KST.

Council items: QF4-A12, QF6-M11, QF1-A24, QF2-M1, QF2-M4.

**What (v1.1, kept).** Extract the §9.3 reference series into `tests/fixtures/macro/` with an md5 per file: French daily Mom/ST_Rev/5-factor/regional, the monthly F-F factors, ^KS11, ^GSPC, SPY, KRW=X, ^TNX, ^RUT, DGS10, DEXKOUS, VIXCLS, VXVCLS, PCEPILFE, CPIAUCSL and DTWEXBGS.

`tests/run_all.py` patches the network to raise, so golden tests must run from these files. Extract them only from post-close files, with `retrieved_at_utc` stored; a fixture check rejects any last row retrieved before the session's official close (the 2-Oct `^KS11` row in the research snapshot was an intraday print, in a file written at 10:56 KST).

**Added by the council:**
- **Regenerate before freezing.** The golden values computed before the 17:20 KST patch must be regenerated on the official closes before they are frozen (§5a DQ-01, DQ-02).
- **Extend the QF0 quality table (QF1-A24)** with:
  - 069500's 800-day hole;
  - 000660's negative adjclose rows;
  - the flat ^KS11 rows;
  - the intraday last rows;
  - the Saturday sessions before 1998-12-12.

  Flat rows are dropped from OHLC-based statistics.
- **OHLC open-quality flags (QF6-M11).** For example, the ^GSPC open equals the prior close on 41% of days.
- **Hash every fixture.** Golden values are vintage-bound: French factor files "differ substantially depending on when the data were downloaded" (QF2-C14).

**Priority: moved** (R-01, M1).

### BL-G06 — Map the existing 18-indicator macro sheet (P1)

**Status v2.0: OPEN · P1** (it blocks M6, which in SPEC v2.0 holds R-13 and R-18). The mapping must also record whether the sheet's regime read is a regime-model state. If it is, SPEC v2.0 forbids acting on it or displaying it (Resolution 10; R-33). Volatility display labels are not regime states and stay.

**What.** The sources show an 18-indicator sheet with z-scores and a regime read in `core/ficc/macro`, but not the list. Fill spec §3.6's mapping table from the code. Each indicator gets:
- its role: CONTEXT by default, acting only if it is listed in §3.6;
- its timing rule;
- whether its z-score window is causal;
- whether the regime read uses smoothed or filtered probabilities. Smoothed must become filtered, even for display.

**Priority: P1** (blocks M6).

### BL-G07 — Map the 6-component signal composite to families (P2)

**Status v2.0: OPEN · P2** (no council ruling).

**What.** Tag each of `core/quant/signals`' six components with a family (momentum, reversal, flow, quality, ts_trend) or none. Overlays attach only through tags (spec §3.7).

**Priority: P2.**

### BL-G08 — KOSPI200 futures as the Korea market-gross instrument book (P3)

**Status v2.0: OPEN · P3; the rule moved.** Two modules now carry it:
- **R-26:** a futures line is refused when one contract exceeds ~5% of the declared notional. The example is a mini KOSPI200 (≈ ₩56m) on a ₩0.1bn sleeve.
- **R-06 KR:** the Korea card may use a futures line only where one mini contract is ≤ ~5% of the declared notional (≈ ₩1bn or more). Otherwise it uses the KRX ETF line at 3 bp.

The owner's notional declaration (D5) decides whether this line exists (X-EX2-N3).

**What (v1.1).** QUANTGEN reads KOSPI 200 futures quotes and pre-registers futures at 5 bp per side. A Korea vol-target card on a futures line would sit between the ETF book (3 bp) and the stock book (35 bp). Compute its golden values and register it only as a separate card.

**Council evidence (EX2; QF1).**
- **Contract notionals:**
  - KOSPI200 futures ₩250,000 × index ≈ ₩280m;
  - mini KOSPI200 ₩50,000 × index ≈ ₩56m.
- **Simulated VT20 on integer mini contracts (2016–26).** Tracking error vs target falls with sleeve size, and a full KOSPI200 contract needs about ₩3bn or more:

| Sleeve | One contract, % of sleeve | Tracking error |
|---|---|---|
| ₩0.1bn | 56% | 7.5%/yr |
| ₩0.5bn | 11% | 1.6%/yr |
| ₩1bn | 5.6% | 0.7%/yr |
| ₩3bn | 1.9% | 0.17%/yr |

- **Last trading day.** The expiring contract closes at 15:20 KST, before the cash close.
- **Costs.** Futures at 5 bp is confirmed. A roll calendar and a roll-cost line are added (QF1-A17).
- **What would settle it** (QF1, answering E5's basis, roll and margin objection): a futures-line card on actual KOSPI200 front-month data with a declared roll calendar and price-limit days.

**Data needed.** KOSPI 200 futures daily OHLC and settlement, front month, roll-adjusted with roll dates (BL-D24).

**Priority: P3** until the owner declares a Korea notional that clears the floor (D5).

### BL-G09 — Broker path: out of scope (record only)

**Status v2.0: Record only** (unchanged).

**Status.** QUANTGEN is read-only by construction, and this programme designs no order path. Spec §3.10 records what would have to remain true if the owner ever decided otherwise: PASS cards only, fail-closed, its own forward record through the gate, and the same costs. Nothing in this backlog may be built on the assumption that a broker path exists.

**Priority:** none.

## 5c. Blocked by read-only design (moved here in v1.1)

These items or item-parts need real orders, real fills or real positions. They cannot be built in QUANTGEN as it is. They are kept for the record only; spec §3.10 applies if that ever changes.

| Origin | What is blocked | What replaces it now |
|---|---|---|
| Spec v1.0 R-05, R-10 | Limit orders into the KRX 15:20–15:30 closing auction; opening-auction limit orders | Daily simulated entries priced at the official close of t, earning from t+1. SPEC v2.0 R-27 fixes the simulated fill model: decide at ≈ 15:19 KST and fill at the official close; random end ≤ 30 s; limit-lock flags; an LP-exempt ETF close vs iNAV check |
| Spec v1.0 R-10 | Sidecar / circuit-breaker order handling: queue orders, no market orders, cancel resting orders at a halt | Evaluator blocks new simulated entries for 30 minutes after a reopening; quotes during halts are marked indicative |
| Spec v1.0 §4.1 | Tuning the decision time "by comparing slippage in fill logs" | Decision at the official close (spec §4.1); no tuning |
| Spec v1.0 R-10 measurement; BL-C02; BL-D03 (part) | KIS fill logs and realised slippage | KIS quote snapshots (spread, 1-minute range) around windows and on stress days, if KIS quotes carry bid/ask (to be confirmed in `kis_client.py`). Confirming the quote fields is the first milestone task (QF1-A25) |
| BL-O12 (parts) | "API heartbeat lost > 60 s → cancel orders"; "position-reconciliation failure at 15:45 KST → flatten intraday sleeves" | Feed heartbeat loss → engine HALTED for the simulated book (spec §3.8); there are no real positions to reconcile |
| Spec v1.0 §8.6 | "Shadow book beats live by > 2% of NAV" against a live capital book | Forward-simulated overlay-off vs overlay-on books (spec §8.8). R-25: calibrated alarms on whole-book NAV, for falsification only |

---

## 6. Failure archive — ideas that failed the burden of proof: harm, null or inconclusive (do not re-propose without new evidence)

Each entry gives: the idea and who proposed it → the evidence against it → why it failed → **reopen only if**.

### 6.1 Overlay design

1. **Prior design: four-state trend × stress table** (momentum 1.5×/0×, reversal 0.5×/1.5×, quality 1.5×) (N-03; PR-P-14, ER-E-05).
   - **Against:** book −0.07 (share 0.23); −0.18 in 1990–2007; reversal −0.20 (share 0.02). Relative losses −21.3% (Oct-2020 → Apr-2021) and −12.4% (Jan–Jul 2025). Momentum weight turned over 12 times a year.
   - **Why:** the upward multipliers levered momentum into crowded calm periods (1.425× into Nov-2020, 1.50× into Jul-2026), and the table cut reversal in the state where it had its best Sharpe.
   - **Reopen only if:** never in its upward form. A de-risk-only version would be a new Tier A pre-registration. Q1b's de-risk-only variant scored +0.10 full sample but −0.04 in 2020–26.
2. **Any multiplier above 1.0** (N-03; PR-P-12/13, ER-E-04). This covers momentum 1.5× in risk-on, reversal 1.5× or 2×, quality / low-vol / min-vol 1.5×, Korea gross 1.5×, flow × 1.5, and AAII-reversal × 1.25.
   - **Against:** reversal 1.5× −0.05 to −0.20; RMW 1.5× −0.01; min-vol −0.4% a month in the "Heating Up" cell; betting-against-beta −3% real in inflation regimes.
   - **Reopen only if:** never (Tier C).
3. **VIX term structure as a momentum or direction switch**, including halving momentum the same day and the post-clear 0.5× schedule (N-05; PR-P-09, ER-E-03, ER-E-18).
   - **Against:** −0.15 in 2020–26 (share 0.05); −0.19 on top of vol scaling. 2020: momentum −16.5% with the rule vs −11.0% static. One extra day of lag *improves* it (whipsaw). Post-clear schedule −0.158.
   - **Reopen only if:** a new mechanism with Tier A evidence that survives 2020–26.
4. **Cut-and-re-add "boundary behaviour"** (N-04; ER-E-19).
   - **Against:** −0.088 (share 0.02); −0.185 in 2020–26. In Mar-2020 the gate returned to 1.0 only on 8 May, +32.4% off the trough.
   - **Reopen only if:** a re-entry rule that beats SMA20 on re-entry lag (see BL-C04).

### 6.2 Korea

5. **The prior Korea gate: SOX 60-day trend × USD/KRW 20-day change** (N-18; PR-P-20, ER-E-01).
   - **Against:** +0.31 came from look-ahead (the US session closes after KOSPI's close). Implementable: +0.05 (share 0.67), and −0.16 in 2024–26. Relative losses −26.3% (Mar–Jun 2020), −14.5% (Jun–Sep 2026), −8.0% (Dec-2024 → Mar-2025).
   - **Reopen only if:** never in this form.
6. **SOX trend as a Korea exposure gate** (N-18; ER-E-02).
   - **Against:** −0.02 overall; −0.22 in 2024–26 (share 0.02). The SOX 20-day version scored 0.000 in 2024–26 (5th percentile −0.31).
   - **Instead:** SOX(t−1) is an opening-gap input.
   - **Reopen only if:** an open-to-close test (BL-U04) shows value.
7. **E4's AI-hardware gate** (SOX 20-day > 0, DRAM guide ≥ +5%, UST10 20-day < +40 bp; momentum × 0.25 when off) (N-18; ER-E-10).
   - **Against:** on through 22–23 Jun, 1 Jul and 13 Jul 2026; off from 28 Jul — the trough — including the +17.9% day. +0.009 at 0.5× and −0.054 at 0.25× (2024–26).
   - **Reopen only if:** a *deceleration*-based version passes BL-U01.
8. **The US stress row applied to KOSPI**; **refined KRW gates** (two-speed, residual filter, dollar regime B, three-way conjunction) (N-18; ER-E-06, ER-E-16).
   - **Against:** US stress row on KOSPI −0.15 (2024–26). Two-speed gate +0.03 vs +0.07 for the plain leg; with the residual filter −0.03. Regime B was on for 1% of days and missed Apr-2025. The three-way rule −0.001 in 2024–26.
   - **Reopen only if:** never (superseded by BL-S01).
9. **Korean foreign flow as a direction signal**; flow weight up in foreign-buying regimes (N-21; ER-E-23).
   - **Against:** flows are same-day and positive-feedback. Foreigners sold ₩148.3tn in H1-2026 while KOSPI rose ≈ 101%.
   - **Reopen only if:** BL-C06 finds a predictive coefficient after May-2026.
10. **"The Jul-2026 crash was US rates and oil"; "Korea is a US real-yield proxy"** (ER-E-15).
    - **Against:** 22 Jun–30 Jul: UST10 +17 bp, Dated Brent 76.5 → 91.9, KOSPI −38.6%. Afterwards: UST10 +61 bp, Brent above $100, KOSPI +22.3%. KOSPI's β to 10y changes has R² 0.015.
    - **Reopen only if:** never (factual).

### 6.3 Macro gates on factors or gross

11. **Curve re-steepening gross cut; "bull steepener ⇒ risk-off"; "bear steepener ⇒ cut"** (N-11; PR-P-15, ER-E-11).
    - **Against:** −0.09 (share 0.00). Bull steepeners came before NDX +12.9% and +26.7%; −0.09 in 2024–26; fired on 41 days in 2024. Bear steepener on KOSPI −0.054 (share 0.004).
    - **Why:** re-steepening coincides with high factor premia (momentum SR 1.33, ST_Rev 2.12, RMW 1.30 in those months).
    - **Reopen only if:** never.
12. **Real rates as a level state; a real-rate gate on momentum; momentum 0.5× under rates stress; level triggers** (10y > 5.25%, MOVE variant) (N-11; PR-P-11, ER-E-17).
    - **Against:** momentum SR 0.88 when real rates jumped vs 0.02 otherwise; −0.04; cut momentum during its 2022 rally (−7.2%); −0.065 (share 0.03). The 10y > 5.25% level was true on 93.6% of 1990s days and on none in 2008–25 (−0.032). The MOVE variant has fired once.
    - **Reopen only if:** never in level form (see BL-C08 for tilts).
13. **Credit-triggered factor weights** (momentum 0.5×, quality 1.5×) (N-11).
    - **Against:** −0.05 (2020–26); RMW −0.01.
    - **Reopen only if:** BL-C03.
14. **Macro-variable factor timing in general** (growth, inflation, quadrant) (N-11; PC-P-07).
    - **Against:** Ilmanen et al. find "little reliable relation"; timing IR 0.25–0.50 vs a break-even cost of 1.8–1.9 bp per $ traded. The term spread's OOS R² is −0.57% (1980+) and −1.28% (2010+).
    - **Reopen only if:** an OOS R² > 0 gate on point-in-time vintages.

### 6.4 Oil, liquidity, models and methods

15. **Oil gates on equity gross** (Brent +30%/63d; 20-day > +25%; India's +15% one-month gate); "oil hits inflation-sensitive exposure, not equity beta" (N-43; PR-P-10, ER-E-12).
    - **Against:** 22 episodes: 2.67% vs 2.66%. First fired on 6 Mar 2026, after the −12.06% day. −0.05 (share 0.08). On flag days, next-day KOSPI returns were +35.6% annualised vs +13.0% otherwise.
    - **Reopen only if:** BL-C11, which is an *event* rule, not a lagged gate.
16. **Net liquidity or M2 for crypto or the S&P** (N-55; ER-E-13).
    - **Against:** −0.01 (share 0.50); −0.20 in 2023–26. Correlation ranged from −0.45 to +0.77. BTC fell 53% while net liquidity rose $41bn. S&P on WALCL: t 25.1 in levels vs −0.40 in differences.
    - **Reopen only if:** never in level form.
17. **Fixed-coefficient Okun, Phillips, sacrifice-ratio and M2 → CPI relations** (N-31; PR-P-16, PR-P-17).
    - **Against:** Okun −0.407 → −0.05 (break ≈ 2011). 2020 was 2.2× the Okun prediction (not 2.5×). Phillips +0.04 (2011–25); OOS RMSE 2.15 vs 1.79. Sacrifice ratio: 5.5 pp-years implied vs −1.57 realised. M2 coefficient +0.18 / −0.07 / +0.19 across eras.
    - **Reopen only if:** break-robust estimation with a Bai–Perron log, and then only as context.
18. **Sahm, curve-inversion, probit and quadrant gates; 10y–2y as a prior** (N-30).
    - **Against:** Sahm caught 9 of 9 recessions since 1960 but fires a median +2 months late (range −4 to +3); Jul-2024 was followed by 26 months without recession. A 534-day inversion; probit 0.744 with no recession. 10y–2y false in 1982, 1998 and 2022–24; missed 2020.
    - **Reopen only if:** never as gates.
19. **Smoothed regime probabilities; unpenalised daily HMM / Markov-switching gates; "complexity" macro ML timing; pre-cutoff LLM backtests** (N-49).
    - **Against:** real-time US Markov switching changes state 16.9 times a year, and 49% of its episodes have no overlap with the same model's smoothed path (against ex-post ≥ 10% drawdowns, 78% of real-time and 68% of smoothed flags are false); KOSPI 30.8 a year with 77% (2-year initial training window; 9.75–9.95 a year with long training, whose turbulent state is anchored at 41–44% vol). The spec-compliant 0.5/1 switch earns Sharpe 0.554 vs buy-and-hold 0.539 net of 10 bp (0/1: 0.390) but 0.285 at QUANTGEN's 50 bp (8.3 units of turnover a year). Complexity timing: RFF forecasts correlate 0.93 with Nagel's kernel forecasts (a recency- and volatility-weighted average of past returns); IR 0.388 vs RFF 0.255; RFF alpha t −0.12 after the kernel strategy.
    - **Reopen only if:** filtered states with a pre-declared jump penalty, ≥ 10 years of training, a leave-one-crisis-out pass; LLM signals only after ≥ 12 months of forward-simulated record. Persistence-penalised jump models are not part of this failed class: outside Korea they protect (Shu–Yu–Mulvey: Sharpe 0.68 vs HMM 0.54 vs buy-and-hold 0.48), but the 200-day band dominates them and Korea fails, so they stay a research item, not a build.

### 6.5 Forecasts, surveys, events and calendars

20. **Street forecasts and house views as inputs; FMS / Bull & Bear / AAII / COT timing; post-trigger crowding cuts; consensus-surprise entries** (N-56; ER-E-08/09, PR-P-23).
    - **Against:** consensus abs error 17.13% (correlation 0.17, n = 4). 2026: cuts forecast vs a hike; Brent forecast $56–58 vs a $93 average; 10y forecast 4.0–4.35% vs 5.29%. The 2023 recession call scored a Brier of 0.49. FMS Aug-2026 was published after KOSPI's −25.4% fall. AAII Sharpe 0.29 vs 0.36. COT does not predict next-week moves. Aug-2024: momentum −5.9% before the crowding trigger and +6.5% after.
    - **Reopen only if:** never as timing (they remain context with publication timestamps).
21. **24-hour pre-event blackouts and swing blackouts; KRX quad-witching blackout; index expiry-close fade** (N-38; ER-E-07, ER-E-22).
    - **Against:** the pre-FOMC drift fell from 44.5 to 9.2 bp (not significant); FOMC lands at 03:00/04:00 KST; BoK days run at 0.82× normal abs(r); quad witching t −0.38; the day after expiry continues (+0.33); fade t −2.13. A full-day blackout would have skipped KOSPI's +2.66% on 18 Sep 2026.
    - **Reopen only if:** BL-O02 (size-down only, never a blackout).
22. **Calendar tilts** (KRW April seasonality; quarter-end momentum 0.75× / reversal 1.25×; export-print tilt); **aggregate-issuance and IPO-window multipliers; buyback-blackout multiplier; Korean issuance volume as sentiment** (N-58; ER-E-21; EC-E-24).
    - **Against:** April KRW mean −0.36% (t −0.64). Quarter-end continues (KOSPI +0.24; fade t −1.26). The export print is a turn-of-month effect (Nikkei 1.27×, S&P 1.02×), and exports lag KOSPI by 4–7 months. Detrended IPO counts t −0.3 to −1.4. SSGA finds buyback blackouts have no effect (p > 0.05); local t −0.26.
    - **Reopen only if:** never.
23. **USD-down-with-equities-down ⇒ stress +1 notch (de-risk)** (PR-P-21).
    - **Against:** weekly (n = 14) +7.27% over 13 weeks vs +2.84%; daily (n = 86) +2.19% over 20 days with 73% positive.
    - **Instead:** it is a hedge-failure flag only.
24. **"FX intervention ⇒ vol compression, no reversal"** (PR-P-22).
    - **Against:** vol rose in 4 of 5 cases; USD/JPY was lower 60 days later in 5 of 5; the Oct-2022 level was not re-breached within 60 days.
25. **P4's credibility-state rule as specified** (double inflation-surprise weight; contested-state blackouts) (PR-P-31).
    - **Against:** the gauge read "anchored" during the 2022 punishment phase.
    - **Reopen only if:** BL-C09(a).
26. **P6's 200-day-average conjunction on the vol target** (PR-P-29).
    - **Against:** it removed the bull tax (+76.7%) but also all Q3 protection (−38.1% vs −9.6%).
27. **2022–26 as a clean "touched-once" holdout** (ER-E-24).
    - **Against:** it has been dissected episode by episode; SE(ΔSR) ≈ 0.08–0.09.
    - **Instead:** it is a stress-report set only.
28. **KRW UIP and carry misstatements** ("Fama β 0.26", "carry skew −4.06, worst quarter −58.6%", "carry not live") (PR-P-27).
    - **Correct values:** post-float β −1.63; skew −2.38 and worst quarter −36.9% on monthly-average FX (on quarter-end point-in-time FX, used for tail calibration: skew −1.80, worst quarter −43.8%); the rate differential is −0.75 pp.
29. **China PMI/CNY as a Korea signal; CESI as an equity feature** (executive DROP list).
    - **Instead:** keep China in the covariance only.

### 6.6 Numbers that must not propagate

| Item | Wrong | Correct |
|---|---|---|
| D&M momentum Sharpe | "1.43 vs 0.71" | 0.682 → 1.041 → 1.194 (*JFE* 2016, Table 7, 1934–2013) |
| KOSPI Q3-2026 / peak | −18.8% / ~9,386 | −19.33% / 9,114.55 (closing, 22 Jun) |
| Brent | $127 / $114 read as futures | Those are Dated spot; futures were $118.35 / $102.59 |
| BoK 27 Aug 2026 vote | "unanimous" | 6–1; base rate 3.00% |
| US 10y 5.29% | "19-year high" | Highest close since 14 May 2002 |
| Taylor gap | −1.4 pp | −0.89 pp central (range 0.4–2.3) |
| H.10 FX | daily, T+1 | Weekly, Mondays 16:15 ET |
| AMP Japan (Table I) | either column quoted without naming it | Both are printed: factor column 0.13 / 0.77 / 0.88; P3−P1 column 0.09 / 0.79 / 0.78 (momentum / value / combo). Name the column |
| 2022 profitability factor | −10.1% | French RMW +8.4% |
| KOSPI 9 Mar 2026 | −8.11% | −5.96% close (−8.11% was an intraday print) |
| NXT after-market | from 15:30 | 15:40–20:00 |
| KOSPI 15 Jan–29 May 2026 | +69.8% | +76.7% |
| Okun 2020 multiple | 2.5× | 2.2× (quarterly averages) |
| Intervention line | "migrates to ~165" | Actions at 160.23 (Apr) and 163.86 (Jul) |
| R4 golden values | "net of costs" (implicit) | Gross; net values are in R4b (`R4b_golden_values_net.csv`) |
| Strict H.15 timing for a US close decision | +1 business day | +2 business days (DGS10(D) posts 16:15 ET on D+1, after the 16:00 close) |
| Rates-leg timing chain | "+0.041 → +0.010 (R4)" | +0.038 (R4, value timing) → +0.010 (+1 business day) → −0.000 (+2 business days, R4b); +0.041 is the R2 construction |
| KRW leg, strict timing | "+0.016" | +0.016 is +1 session or Yahoo timing; strict H.10 publication gives +0.001 (R4b) |
| Constant-vol scaling "since 2020" | HML −0.03, CMA −0.06 | HML −0.08, CMA −0.16 since 2020 (−0.03 / −0.06 are full sample) |
| Real-time Markov 0.5/1 vs 0/1 Sharpe | unlabelled | 0.554 vs 0.390 (US) and 0.442 vs 0.137 (KOSPI, 2-year initial training) are net of 10 bp |
| KOSPI close, 2 Oct 2026 | 6,943.66 (−0.40%; −23.8% from the peak; 1.098 × 200-day) | 7,003.74 official close (+0.46%; −23.2%; 1.107 ×); 6,943.66 was an intraday print (about 10:30 KST, in a file written at 10:56 KST) |
| KRX sidecars, 2026 | "41 in H1-2026" | 41 from 2 Jan to 24 Jul 2026 (≈ 30 in H1); 7 circuit breakers |
| Payroll benchmark revisions | −818k (2024) / −911k (2025) as final | Preliminary; finals −598k NSA (2024) and −898k SA / −862k NSA (2025) |
| SE(ΔSR) and years to detect +0.05 | 0.034 / 0.052; 33–44 years | Market vol targets vs S: 0.061 (US) / 0.130 (KOSPI); about 150–330 years. 0.034 / 0.052 hold only for add-on legs |
| Vol-scaled momentum by year | "lifts Sharpe in 86% of years" | Cap 1 binds in 20 of 37 years; higher Sharpe in 15 of them (75%) gross and 11 (55%) net of 50 bp; the other 17 are ties. 86% is the cap-2, vol-matched research rule |
| Trial count N̂ = M/(1+(M−1)ρ̄) | "BLdP eq. 9" | Kish's design effect, not eq. 9; never gate on it. Eq. 9 is linear, N̂ = ρ̂ + (1 − ρ̂)M (12.6 on the momentum family); the gate uses N_equiv (6.3) |
| KOSPI Markov switching | "30.8 switches a year" (unqualified) | 30.8 a year with a 2-year initial training window; 9.75–9.95 a year with long training |
| Korean 1-month reversal | "−2.950% a month" as a return | Fama–MacBeth coefficient −2.950 (t −3.77), not a strategy return |
| PBO citation | SSRN 2460551 | SSRN 2326253 (2460551 is the deflated Sharpe ratio paper) |
| Complexity timing ρ 0.93 | "with vol-timed momentum" | RFF forecasts vs Nagel's kernel forecasts |
| Goyal–Welch–Zafirov | "1/3 of 46 predictors" | Over a third of the 29 post-2008 predictors lose in-sample significance; half of the survivors fail out of sample |
| D&M Table 1 WML Sharpe | "0.71 (Table 1)" | Table 1 prints 0.60 (17.9 / 30.0); the text states 0.71 |
| R-04 trigger | "exactly the published one" | A floored binary heuristic inspired by D&M (2016); the published rule is continuous; expected add-on ≈ +0.07 |

### 6.7 Retired FORWARD-SIM legs (council round QC; formerly §1 BL-S01 and BL-S02)

The council voted unanimously on both legs (Resolution 8). Each leg leaves the FORWARD-SIM re-gate queue with its REJECT recorded on long history. It may persist only as a labelled, display-only refusal book that no recommended or specification book reads (I-03). QF3-A24 and QF4-A18 (CONFIRMED) re-checked that both REJECTs are genuine.

30. **BL-S01 — the USD/KRW leg (S1): 20-day dlog > +3% → Korea gross × 0.75** (spec v1.x R-11; node N-22).
    - **Proposed by:** the Executives (EC-E-10, moderate support). The Professors were split (PX-P-04): Q1b and P1 kept it "on probation", while P6 and P2 were against.
    - **Hypothesis.** Sharp won weakness marks sudden-stop states. De-risking Korea gross to 0.75× reduces drawdown, compared with a same-exposure static book, with no Sharpe loss.
    - **Evidence against, 2016–26 (v1.x):**
      - R4 at value timing: +0.032 (0.967) gross; on VT20 +0.042 (0.977).
      - Strict H.10 publication (R4b): +0.001 (0.53); on VT20 +0.013 (0.74); 26 onsets.
      - Net of the 35 bp KRX stock cost: −0.008 (0.32).
      - PC-1 fails (ΔMDD +1.1 pp at value timing and 35 bp; +0.1 pp strict at 3 bp). PC-2 fails (tail ratio 0.99–1.00).
      - Near-zero coverage of the worst days in Aug-2024, Dec-2024 and Apr-2025.
      - Silent during the Jul-2026 crash, when the won *strengthened* 7.4%.
      - Its 28 trigger episodes were followed by +0.48% over 20 days, vs +1.10% unconditional (57% negative).
    - **Evidence against, 1997–2026** (DL-A, KOSPI 1997-04 → 2026-10, on VT20):

      | Timing | Onsets (de-clustered at 20 sessions) | ETF 3 bp: ΔMDD / tail / ΔSR | Stock 35 bp: ΔMDD / ΔSR | Verdict |
      |---|---|---|---|---|
      | Value (DEXKOUS D ≤ K−1) | **74** | −1.7 pp / 0.996 / −0.015 | −1.7 pp / −0.048 | REJECT (PC-1, PC-2) |
      | Strict H.10 | **54** | −1.3 pp / 1.004 / −0.022 | −1.4 pp / −0.036 | REJECT |
      | Strict H.10, holiday-aware | 54 | −1.3 pp / 1.004 / −0.027 | −1.5 pp / −0.041 | REJECT |
      | Yahoo KRW=X lagged 2 sessions (2004+) | 69 | +0.3 pp / 0.996 / −0.006 | −0.4 pp / −0.059 | REJECT |

      - The tier is met at every timing, and PC-1 and PC-2 fail at every timing. The timestamped history is no longer needed to decide it. Only the 2016–26 strict-timing sample (22–26 onsets) is INSUFFICIENT by tier.
      - The 1997–2015 holdout (strict) has 31 onsets, ΔSR −0.039 and tail ratio 1.00: REJECT (QF4).
      - The 2016–26 value-timing gain (+0.038 on VT20) does not replicate before 2016.
      - The leg lost 1.5 pp vs the static book in the 1997–98 won crisis (QF2).
      - The proxy does not decide the verdict. On the ECOS 15:30 history the first 1997 firing falls on 28 Oct 1997, with 56–58% of the fall already done; the won was pegged near 914–915 until late Oct-1997 (EX2).
    - **Why it failed.** KRW stress coincides with high KOSPI volatility, which VT20 already prices (QF4). The leg fires after the equity drawdown is under way (QF2).
    - **v2.0 disposition.**
      - R-11 is RETIRED: its REJECT is recorded, and it may run only as a labelled refusal book. That book keeps accruing a forward record from its header commit. The Professors withdrew PX-P-04's probation (QF4-A3).
      - BL-G04 / BL-D13 drop to P3.
      - KRW hedge validity is a separate, display-only question (`fx_hedge_credit`, CQ-19).
    - **Reopen only if:** new evidence, not a re-timing or a new proxy. The ECOS 15:30 rerun is a P3 formality that cannot change the REJECT (QF2-M8).
31. **BL-S02 — the US rates-stress leg (S2): 10y +40 bp over 20 days → US duration-sensitive gross × 0.5** (spec v1.x R-12; node N-24).
    - **Proposed by:** the Executives (EC-E-11, moderate support; E1 would keep it in the backlog and E5 would run it forward). The Professors were silent on this leg.
    - **Hypothesis.** A persistent long-end sell-off is a hostile state for US duration-sensitive equities: while the flag is on, the US market earned −15% a year (Sharpe −0.78). Halving gross in that state reduces drawdown, compared with a same-exposure static book, with no Sharpe loss.
    - **Evidence against (v1.x):**
      - The full sample gives +0.041 (0.99) in the R2 construction, but a nine-cell threshold grid has a median of ≈ +0.01 (15 trials; it fails a BHY haircut).
      - The forward 60-day max DD after onsets is −7.07% vs −7.17% unconditional, which fails E1's own falsification test.
      - The timing chain is +0.038 (R4, value timing; non-compliant) → +0.010 (+1 business day; compliant via the Treasury par-yield channel with a logged posting time) → −0.000 (+2 business days, strict H.15, R4b).
      - Net of 50 bp at strict timing: −0.103 (0.00). Turnover is 3.60 a year, which costs 1.80% a year.
      - R4b protective checks (strict, 50 bp): ΔMDD −3.5 pp; tail ratio 0.99; ΔSR −0.12.
      - The flag was off in Aug-2024, Apr-2025 and Jul-2026, and on for only 2 days in Mar-2026, near the low.
    - **Evidence against, 1990–2026** (DL-A, US 1990-02 → 2026-09, on VT15). There are **71 onsets at every timing** (39 in 1990–2007, 32 in 2008–26):

      | Timing | Status | 50 bp: ΔMDD / ΔSR | 5 bp: ΔMDD / ΔSR | Gross: ΔMDD / ΔSR | Tail | Verdict |
      |---|---|---|---|---|---|---|
      | Value (DGS10(D) at the close of D) | Non-compliant | −0.8 pp / −0.076 | +1.1 pp / +0.026 | +1.2 pp / +0.037 | 0.99 | REJECT |
      | +1 business day via Treasury | Compliant via Treasury | −3.1 pp / −0.105 | +0.1 pp / −0.002 | +0.3 pp / +0.009 | 0.99 | REJECT (also PC-4 2/11) |
      | +2 business days, strict H.15 | Compliant | −3.5 pp / −0.120 | +0.8 pp / −0.019 | +0.9 pp / −0.007 | 0.995 | REJECT |
      | ^TNX at the close of D (live proxy) | Value | −1.5 pp / −0.090 | +1.4 pp / +0.016 | +1.5 pp / +0.027 | 0.99 | REJECT |

      - ΔSR −0.120 ± 0.022 at 50 bp is a powered rejection.
      - The leg loses 75% of its edge with one extra session of lag (QF2). R-34's timing-fragility gate flags it (fragility ratio 0.75 > the declared 0.5).
    - **Why it failed.**
      - The edge is concentrated in the first day.
      - Support was one-sided, and the cells are multiple.
      - The tail ratio is 0.99–0.995, so the leg does not de-risk the worst days.
      - At QUANTGEN's US cost it pays 1.80% a year for no drawdown benefit.
    - **v2.0 disposition.**
      - R-12 is RETIRED: its REJECT is recorded at every timing and cost, and it may run only as a labelled refusal book. That book keeps running; the flag has been on in data dated from 23 Sep 2026 (strict H.15: applied from the 25 Sep close).
      - G-US-02a is relabelled "compliant via Treasury with logged posting time".
    - **Reopen only if:** a separate, lower-turnover card (e.g. a minimum 10-session hold), counted in the family ledger, on the US instrument book declared before the run. At 50 bp every timing is negative, so this is moot unless turnover falls sharply. The leg is never extended to KOSPI here (BL-C07(a)).

### 6.8 Demoted rules and closed routes (SPEC v2.0)

32. **R-08 as a sizing rule: the VIX ≥ VIX3M entry block** (v1.x R-08; CARD-P). When VIX(D) ≥ VIX3M(D), the rule blocked weight increases (w = min(target, w_prev)) in the momentum and vol-target books.
    - **Evidence against** (DLB-T6; FRED 2007-12-04 → 2026-09-30, 4,735 days; strict timing, so the flag on D blocks the weight earning from D+2):
      - **Flag anatomy.** Flagged on 10.1% of days, with 14.0 transitions a year. 132 spells, with a median of 1 day: **50.8% last one day**, and 15.9% last ≥ 5 days. Onsets are 64 / 40 / 24 at 20 / 60 / 126 sessions, so the Tier A count is met.
      - **Cards.**
        - ΔMDD vs S: US VT15 +0.9 / +0.6 pp (50 / 5 bp); KOSPI VT20 +0.3 / +0.4 pp (3 / 35 bp); momentum R-03 +0.0 pp. With 5-close clearing: −0.1 to +1.3 pp.
        - Tail ratio 0.996–0.999.
        - **PC-1 and PC-2 fail in 10 of 10 cells.** The block binds on 3.1–9.3% of days.
      - **Korea.** It was usable on 0 of 28 KRX sessions in Jul-2026 and 0 of 5 in Dec-2024, because Korean shocks were local (QF6).
      - **Timing.** A median 79% of the drawdown had already happened at flag-on (72 E5 episodes; 70% for episodes deeper than 10%).
    - **Why it failed.** The flag is coincident. It only stops weight increases, on a few days, so it cannot cut drawdown.
    - **v2.0 disposition** (QF6-M7; QF6-A9 CONFIRMED; QF6-A10; unanimous). R-08 is DEMOTED to a CONVENTION annotation of an execution-cost state, with a stated clearing rule. On flag days the evaluator writes an annotation and requests KIS spread snapshots; no book's exposure changes (assertion).
    - **Reopen only if:** as an execution control (never a protective claim), and only if KIS quote-snapshot spreads on flag days exceed the gross edge of the entries it would block (QF6's settling test; R-10 measurement).
33. **R-04's Tier A-provisional route, and any pooled route for the card already run** (the Daniel–Moskowitz bear-state gate, floor 0.5).
    - **Proposed by:**
      - P3, through the BL-C12 tier for published, replicated effects;
      - QF3-A18 and QF5-M6, through a pooled-onset Tier A revision.
    - **Evidence against:**
      - **BL-C12 holdout.** The pre-registered holdout passed in **1 of 3** regions: Japan +0.017 (p 0.30, a single spell); Europe +0.147 (p 0.006); APxJ +0.041 (p 0.24).
      - **Step 3 at an honest N.**
        - The deflated add-on is **0.77** at N_equiv 6.3 (0.767–0.79 across the checks) and 0.56–0.84 at the linear N̂ (PX1).
        - The analytic z is 2.06, against the Professors' N_eff Bonferroni bar of 2.15; the Executives and QF put it at 2.08, below 2.50.
        - The earlier "0.95 at N̂ 1.81" rested on the Kish formula (#38).
      - **Pooled onsets.** There are 34 (US 6, Europe 10, Japan 8, APxJ 10). The pooled add-on is +0.080 (SE 0.023, p 0.0002), and the 2016–26 holdout gives +0.037 (p 0.07). They meet sufficiency, but the pooling rule would be declared after the data.
      - **Size.** R4b net of 50 bp gives an add-on of +0.072 (share 0.983). The rule is a floored binary heuristic inspired by D&M (2016), not the published continuous rule (QF5-A1).
    - **Why it failed.** The add-on is small relative to the selection behind it, and there are few bear-state spells (7 onsets since 1990). In the 2016–26 holdout only Europe was significant, consistent with post-publication decay or rarer bear states (QF3).
    - **v2.0 disposition** (QF5-M6, QF3-A18).
      - R-04 is DEMOTED to the specification book only, labelled "step 3 FAIL". The recommended-book builder refuses it (I-03), and card validation rejects any A-provisional or pooled route for a card already run.
      - The trial goes instead to the variance-scaled R-03 revision (X-PX2-N3: +0.126 vs +0.072 net).
      - BL-C01 informs only the specification-book floor.
    - **Reopen only if:** data never used in design (e.g. 2027+ across regions) supports it at step 3 with deflated ΔSR ≥ 0.95 at N_eff. It may never return through an A-provisional or pooled route for this card (QF red line Q1).
34. **`max(σ̂_SMA20, implied vol)` as the vol-target estimator** (v1.x R-06 logged alternative; the BL-C04 alternative).
    - **Evidence against:**
      - US 1995–2026 at 50 bp: ΔSR −0.166, turnover 6.0 a year (QF6).
      - It de-grosses permanently (QF6-A15).
      - The implied-vol gain is pre-2008 only (0.615 vs 0.614 since 2010).
      - VKOSPI closes at 15:45 KST, after the KRX decision.
    - **Why it failed.** The variance risk premium biases it, and implied-vol noise adds turnover.
    - **v2.0 disposition.** It is retired from R-06's logged alternatives and listed in R-33's DO-NOT-BUILD list. Implied vol is logged as live context (R-13; CQ-15).
    - **Reopen only if:** HAR-IV passes R-30's staged gate as a counted revision (ST-09).
35. **A trading-volume proxy for Korean leverage** (index leveraged-ETF volume / the leveraged share as a fragility gauge; a shortcut for BL-U01).
    - **Evidence against:**
      - Out of sample 2014–26, the MSE change is −2.1% to +1.6%, with Diebold–Mariano t ≤ 0.73 and Bonferroni p = 1.0.
      - On 21-day drawdowns of ≥ 10%, its AUC is 0.654–0.675 vs a 0.679 baseline.
      - On 19 Jun 2026, before the crash, the leveraged share stood at the 4th percentile (QF1-A22).
      - The KODEX leveraged/inverse value-traded share has t −3.59 with the wrong sign (2017–26), and the absorption-ratio shift adds nothing to a HAR forecast (t −0.19) (QF4-A23).
    - **Why it failed.** The leverage migrated to single-stock 2× products (listed 27 May 2026), margin and swaps. Index-LETF share fell as KODEX 200 volume exploded.
    - **v2.0 disposition.** The volume proxy stays archived (QF1-M5). AUM and KOFIA margin debt are logged directly as context (R-13; BL-D02; CQ-11 to CQ-13).
    - **Reopen only if:** never as a volume proxy. A leverage state needs direct AUM and margin data and BL-U01's test; any card needs ≥ 30 onsets.

### 6.9 INVALID council items (refuted or withdrawn; `QC_ledger.csv`)

36. **QF3-M6 — an ML vol-state challenger pipeline.**
    - **Proposal.** Elastic-net and GBM classifiers of P(next-21-day vol > its expanding 80th percentile). Purged and embargoed walk-forward; CPCV tuning; kept as a logged challenger.
    - **Votes:** R / R / R. Focus 3.
    - **Evidence against** (QF3; PX1's nested re-run):
      - **The EWMA rule wins in 3 of 4 settings.**
        - KOSPI 2009–26: Brier 0.0387 vs 0.0571 (elastic net) and 0.0755 (GBM). GBM's Brier skill is −0.27, worse than climatology, with a reliability slope of 0.13.
        - S&P 2000–26: 0.1149 vs 0.1225 / 0.1307.
        - Only S&P 2013–26 with VIX/VIX3M features favours elastic net (0.1040 vs 0.1073), with DM +0.93, not significant.
      - **With PX1's nested fairness feature,** elastic net improves (KOSPI 0.0588 → 0.0558; S&P 0.1306 → 0.1205), but the EWMA rule still wins (DM −2.52 and −1.11).
      - **Economics, S&P at 50 bp:** ΔSR −0.093 (elastic net) and −0.131 (GBM), on turnover of 3.5–4.6 a year. 40 configurations were counted.
    - **Why it failed.** Own volatility already carries the signal. ML overfits a 6% base rate, and noisy probabilities trade too much at KIS cost.
    - **v2.0 disposition.** Archived. No maintained pipeline (R-33). The harness script is kept in `docs/`. ML vol-state classifiers stay prohibited, while range-based HAR is admitted (R-30).
    - **Reopen only if:** intraday realised variance exists, and a nested design is used.
37. **QF7-M3 — Mondrian conformal calibration of the display labels.**
    - **Proposal.** Label-conditional calibrated risk bands for the calm / normal / elevated / stressed labels (adaptive conformal, γ = 0.005).
    - **Votes:** CX / R / R. Focus 8.
    - **Evidence against** (PX1):
      - Per-label coverage is algorithmic: a *constant* σ̂ passes per-label Kupiec (p 0.20 / 0.59 / 0.10 / 0.45).
      - By a strictly consistent score (tick loss × 1e4), Mondrian ACI equals plain FHS-SMA20 (16.152 vs 16.151). FHS-GARCH with no conformal step is best (16.005) and already calibrated in 3 of 4 labels. A constant-σ̂ ACI scores 17.05.
    - **Why it failed.** A band that any σ̂ passes certifies nothing about σ̂. The label miscalibration is SMA20's lag (FHS 6.48 / 6.91 / 3.43 / 3.38% by label on KOSPI).
    - **v2.0 disposition.** Archived (R-33 DO-NOT-BUILD: "a Mondrian conformal label layer"). Per-label coverage reporting is kept (QF7-A23), and VaR is scored with tick loss (X-PX1-N4).
    - **Reopen only if:** FHS-GARCH labels still miss coverage. Even then, the Professors' "display at most" applies.
38. **QF3-A1b — the Kish form N̂ = M/(1 + (M − 1)ρ̄) as the step-3 trial count.**
    - **Votes:** A / A / R. The Professors and Executives accept the overturn, and QF rejects its own statement, so all three agree it is withdrawn. DLB-T2b CORRECTED.
    - **Evidence against:**
      - It is Kish's design effect, not Bailey–López de Prado's eq. 9, which is linear: N̂ = ρ̂ + (1 − ρ̂)M. On QF3's 26-trial family, eq. 9 gives 12.6 (differences) and 4.3 (returns), against Kish's 1.81 and 1.14.
      - It can be gamed. Padding the ledger with 80 near-duplicates moves Kish from 1.81 to 1.20 and lifts R-04 from 0.951 to 0.986, while N_equiv moves only from 6.33 to 6.59.
      - At N 1.14 the Euler–Mascheroni approximation gives E[max Z] = −0.22, a negative hurdle.
    - **v2.0 disposition.** Withdrawn from every QF table. Under R-23 the gate uses N_eff = max(N_clusters, N_equiv), the linear N̂ is printed as the conservative bound, and no code path computes the Kish N̂.
    - **Reopen only if:** never.

### 6.10 v1.2 mechanisms that failed as written (replaced in SPEC v2.0)

Each of these rules was in SPEC v1.2 and failed on the council's evidence. None may return in its v1.2 form.

| Mechanism (v1.2) | Evidence it failed | Replaced by (SPEC v2.0) |
|---|---|---|
| Drawdown ladder: −15% → HALTED, with no new drawdown reference after a re-arm (R-07, §3.8) | It never leaves HALTED. KOSPI from 1997-09/10, at 1.3% average exposure (714–715 halt cycles); the US from 1990-09 (907 cycles) or 2000-10-13 (653) (DLA-D1) | R-07's explicit re-arm (refused for 10 sessions; reference reset to NAV at re-arm; 0.5× for 10 sessions); an I-04 re-entry regression test; the level is D2 |
| Product composition of overlays and the ladder (§3.3) | It makes the −12% step a 0.25× step (DLA-D2). Total exposure is ≤ 0.25× on 31.0% of KOSPI days, vs 11.2% under `min()` (EX1) | R-02 `min()` composition; a product-composed path is refused; a stack CARD-P once ≥ 2 de-risk factors act |
| Fixed-age staleness defaults (§4.1), with "stale > 1 decision → HALTED" | H.10 inputs (DTWEXBGS, DEXKOUS) are stale at 100% of US-close decisions (98.6% at the KRX close), and strict-H.15 DGS10 at 99.52%. A literal build halts every day (QF2-A3; DLA-S1) | R-19 schedule-aware staleness (0.33–0.89% flagged, every hit on a source-skipped date) with role-based failure actions. Risk-model inputs never HALT |
| PC-1, single-path ΔMDD, as a gate (§8.7) | ΔMDD's bootstrap SD stays at 7.4–7.8 pp (US) from 10 to 100 years. The same Korea card gives +12.7 / +3.8 / +10.6 pp by start date. A zero-cost vol target is REJECTed 55–73% of the time (resampling DGP; DLB-T5b). ΔMDD ≥ 3 pp certifies 3 of 20 timing-free KOSPI placebos (EX1) | R-21's PC-1′ (ΔES95 of 21- and 126-session returns); ΔMDD and ΔCDaR printed, never gated; a do-no-harm cap |
| The 12-month forward route to promote the Korea card (§8.8, §8.9) | Twelve forward months add only 3–10% of the information. The calibrated 2.5% thresholds (−0.20 / −0.39 / −0.73 Sharpe) detect only catastrophic decay (QF3) | A formal run on long KRX history (R-06 KR, Resolution 1). Forward records are falsification alarms only (R-25) |
| The §8.6 named windows as the episode set | There is no window before 2008, so every 1997–2015 holdout is INSUFFICIENT on sufficiency (DLA-K9). The windows also admit non-drawdowns: Sep-2026 was KOSPI +0.26%, with a −6.0% low | R-22's objective market-own episodes (KOSPI: 18 on 1997–2026, 12 before 2008; the S&P: 16 at 15%). §8.6 is printed as a shock-type table |
| Demotion triggers as written (§8.8) | A sign error, and they fire on noise. The CARD-O 2%/6-month trigger fires on 9.9% of month-ends (29.7% of years); the CARD-P trigger on 21.2% (KOSPI VT; 50.0% of years) and 31.7% (US VT; 69.4%) (QF3 §4.9) | R-25's calibrated alarms on whole-book NAV; a book-level false-demotion budget (D4) |
| An absolute 0.05-of-NAV single-name cap (R-07) | It forces the pair to ≤ 10% of NAV: a −39 pp underweight (the rest of KOSPI returned +30.6% vs +101.1% in H1-2026). It cannot be met on an ETF book (Samsung is 20.7% of NAV at g 0.694) | R-07's active cap w_i − g·b̃_i ≤ 0.05 NAV against a capped benchmark, on look-through |
| The triggered 0.45 → 0.35 pair cap (R-07) | It was calibrated inside the regime it targets: first crossed in 2026 (n = 1). It bound during the rally it was built for (+86.6% vs +101.1%, H1-2026) | An aggregate template from a public rule (D1; default in force: the spec's owner-decision registry, §1.6) |
| The R-18 scale-break trigger (60-session persistence) | It fired after the trough (KOSPI 2008, 2026; the US 2009, 2019, 2020) (QF7) | R-18 rewritten (QF7-A18); re-anchoring only on declared events; BOCPD logged only (CQ-17) |

### 6.11 Failures recorded in the QF papers' failure logs

These methods and rules were tested in round QF and failed. The council did not rule on them separately. They are recorded so that they are not re-proposed without new evidence.

| Idea | Evidence against | Source | Instead (v2.0) |
|---|---|---|---|
| Daily-OHLC spread estimators (Roll, Corwin–Schultz, Abdi–Ranaldo, EDGE) as cost validators | A zero-spread placebo on ^KS11 reads 23–40 bp; SPY (true ≈ 1 bp) reads 20–40 bp; KODEX 200 reads 19–30 bp against a 0.45–1.8 bp tick floor. Daily range and volatility dominate the spread signal | QF1 (C6, failure log) | Pre-registered costs plus the tick floor (R-26); KIS quote snapshots (BL-D03). Never use these estimators to set or defend a 3 bp cost |
| A Grossman–Zhou drawdown scaler (D 25%, k 4) on KOSPI VT20 | Cash lock: exposure 0.30, CAGR 1.6% (a ratchet floor plus a long underwater period) | QF4 | R-07 hard stop with an explicit re-arm; R-31 time-boxed steps |
| HRP and minimum-variance cross-market weights | −0.02 to −0.11 Sharpe vs inverse-vol on 7 equity indices, 2000–2026; max min-variance weight 0.43–0.52 (estimation error, concentration) | QF4 | Inverse-vol across markets (R-15) |
| Rolling-Sharpe (ROLL10) prior weights | Japan 2000–26: −0.62 vs equal weights. Walk-forward over 6 regions × 5 factors: 1.068 vs 1.337 for equal weights (shrinkage 1.152) | QF5; PX2 | Priors as admissibility filters with equal risk budgets (R-15) |
| A turbulence flag as a de-risk rule on KOSPI | On from Feb-2026: +65.9% vs +101.1% in H1-2026. Turbulence is symmetric, so big up-moves are "unusual" too | QF5 | Display only (CQ-14) |
| The absorption ratio as an early warning | Never flagged in Mar-2026, Aug-2024 or Apr-2025. Its shift adds nothing to a HAR forecast of KOSPI 21-day vol (t −0.19) | QF5; QF4 | Context only (CQ-13) |
| The variance risk premium as a return predictor | OOS R²: US 1-month −10.7% and KOSPI −4.7% (council); daily-RV VRP −6.6% (1 month) and −11.3% (3 months), US 2000–26 (QF7) | QF6; QF7 | Context only (CQ-16) |
| Economic policy uncertainty (EPU) as a return predictor | OOS R² −5.7% (US ex-2020) and −0.7% (KOSPI ex 2020 and 2025–26): a two-episode effect | QF7 | — |
| HAR with VIX3M (term structure) | US 2010–26: no gain at 21 days (0.732 vs 0.615): collinear with VIX; OLS overfit | QF6 | Implied vol only inside HAR-IV through R-30 (ST-09) |
| Quant Lab models fitted on 504 closes (GBM, historical, jump; GARCH-t) | KOSPI 2026: 95% VaR breached on 16–17% of days, because of a constant-σ calibration on the calmer 2024–25 window. GARCH-t QLIKE is 1.52 × SMA20 at h = 21, with persistence going from 0.78 to 1.00 within six months | QF6 | R-16 expanding (≥ 10-year) fits, and the envelope max(fast FHS, GJR-EVT) |
| A naive CUSUM (k 0.25, h 8) on forward books | 10–13 alarms a decade on in-control backtests | QF3 | R-25: CUSUM with an in-control ARL ≥ 20 years, with h set by bootstrap |
| Multiplicity corrections at a bootstrap p floor | Bonferroni / Holm on 199 variants leaves 0 survivors, because the bootstrap p floor is 1/B (B = 1,000–2,000) | QF3 | R-24: no p printed as 0 (it prints < 1/B); enough resamples for adjusted p-values |
| A jump model with a drawdown-ratio guard (Korea) | KOSPI 1999–2003: off through the 2000 crash (−53%); the guard cannot fire in a uniformly high-vol era. DL-B traced QF7's KOSPI −4.7 pp to this guard | QF7; DLB-T4d | Nothing acting or displayed in v2 (CQ-10) |
| BOCPD / EWMA regime flags with an expanding-median threshold | KOSPI 2003–2026: in stress on only 7.5% of days, at −1 to −1.5 pp ΔMDD. The thresholds are anchored on 1997–2002 vol (a scale break) | QF7 | BOCPD logged only (CQ-17); R-18 re-anchoring only on declared events |

---

## 7. Open research questions

1. **Korea concentration and leverage state** (BL-U01).
   - Which observable leads Korean deleveraging: margin debt, leveraged-ETF AUM, retail flows, or the pair's share of KOSPI?
   - Can such a state remove the Korea vol target's 2016–25 Sharpe cost (ΔSR −0.077 gross, share 0.06; −0.106 net of 35 bp) while keeping its crash protection (−12.2% vs −38.6%)?
   - *Status v2.0: open.*
     - The concentration half is answered: caps apply on look-through with an active single-name cap, and the aggregate template is owner decision D1 (R-07).
     - The leverage half waits on BL-U01's data (BL-D01, BL-D02), logged as context from now on (R-13).
2. **Leading indicators for the semiconductor cycle.**
   - Do changes in DRAM contract guidance, hyperscaler capex revisions or AI-credit concessions lead KOSPI volatility or drawdowns once lagged to publication?
   - So far n = 1, and every *level* version failed.
   - *Status v2.0: open* (BL-U01; BL-D10).
3. **An inflation-conditional overlay floor** (BL-C07(b)).
   - Is the higher de-risk value in high-inflation regimes real (+0.14 vs +0.05), or a two-episode artefact (1990–91 and 2021–23)? It needs the 2027+ holdout.
   - *Status v2.0: open.* If a macro-conditioned floor is ever built, R-18's trigger (i) applies: an official framework change shrinks every macro-conditioned multiplier to 1.0 and starts a forward record.
4. **The Korean foreign-flow regime under 2026 market structure** (BL-C06).
   - Since single-stock leveraged ETFs listed in May-2026, have foreign flows become uninformative, or simply a different regime?
   - What drove the Q3-2026 won (+12.4%): exporter conversions, BoK hikes, or the NPS swap line?
   - *Status v2.0: open.* Flows are logged as context from day one (R-13; BL-D01).
5. **Post-publication decay of vol-scaled momentum.** Under the spec's cap, the gain is +0.31 over 1990–2026 but +0.20 in 2012–26. 1990–2007 was also +0.20 under cap 1, so the visible decay (+0.66 in 1990–2011 → +0.26 in 2012–26) is a cap-2 result, and the cap-1 full-sample gain leans on 2008–09 (R4). Is APxJ's negative 2016–26 result (−0.023) noise or the start of decay elsewhere?
   - *Status v2.0: open.* R-03 keeps an indicative PASS labelled "step 3 borderline" (0.98 at N_equiv 6.3; 0.947 at the linear N̂ 12.6). Its two counted revisions, a scale-free target and variance scaling, are registered in the family ledger (R-03, R-23).
6. **Does the D&M gate work on Korean stock momentum?** It is untested on KRX data, and Korean 12-1 momentum may be negative to begin with.
   - *Status v2.0: open* (BL-U02). R-04 is in the specification book only.
7. **Scale-break re-anchoring.** Can a pre-declared re-anchoring rule fix discrete Korea flags, when even trailing percentiles flagged 72% of 2026?
   - *Status v2.0: partly answered.* R-18's 60-session scale-break trigger fired after troughs and is rewritten (QF7-A18). Re-anchoring happens only on declared events, and BOCPD is logged only (CQ-17). The Korea flags themselves stay with BL-C05.
8. **A live-feed rates leg.** With strict H.15 timing for a close decision (+2 business days), the long-sample edge vanishes (−0.000, R4b); via the Treasury par-yield channel +1 business day is compliant with a logged posting time (+0.010), and the protective card is REJECT at every timing and cost, gross included (DL-A). 2015–26 keeps +0.053 strict and +0.071 on the ^TNX live proxy (gross). Is the 1990–2007 sensitivity a feature of slower markets, or noise? At 50 bp per side every timing is negative, so the question is moot for QUANTGEN unless turnover falls sharply (BL-G03).
   - *Status v2.0: closed.* S2 is retired (§6.7 #31).
9. **The stock–bond regime variable.** Inflation level, inflation volatility, or the real-rate share of yield moves?
   - *Status v2.0: open* (BL-O13). Cross-asset regimes belong in the risk model only (X-EX1-N6; R-09). Turbulence may become a stressed-covariance input only if it beats the stock–bond-regime input (ST-08).
10. **The cost of Korean reversal under the 0.20% sell tax.** What is its capacity and net Sharpe, and does it survive stress-day spreads (BL-C02)?
    - *Status v2.0: open* (BL-C02; BL-U02; owner decision D3's test, ST-11).
11. **Quant Lab tail model for the 2026 regime.** GARCH-t, jump-diffusion, or a regime-mixture? Seeded and validated against 2026, with 2015–24 out of sample.
    - *Status v2.0: answered* in SPEC v2.0 R-16:
      - expanding (≥ 10-year) fits;
      - a displayed envelope max(fast FHS, GJR-EVT), with Kupiec, Christoffersen and ES Z2 lines;
      - 2016–26 and 2026 reported separately;
      - a replay library with regime metadata.

      Regime-mixture (GMM) scenarios are CONTESTED (ST-06).
12. **Statistical-power policy.** Should QUANTGEN formally adopt the non-inferiority tier for replicated effects (BL-C12), given that a +0.05 Sharpe effect needs about 150–330 years to detect for a market vol target (SE(ΔSR) vs S 0.061 / 0.130; 33–44 years held only for add-on legs)? v1.1 already adopts a protective card class (spec §8.7) with a 0.10 Sharpe non-inferiority margin. Is 0.10 the right margin, and is 3 pp the right drawdown threshold? They were fixed before any macro card ran and may change only through a spec revision, never per card.
    - *Status v2.0: answered by the council.*
      - The non-inferiority margin stays δ = 0.10, with a binding PC-3.
      - PC-1's 3 pp single-path ΔMDD threshold no longer gates. ΔMDD is printed, the PC-1′ tail legs gate, and a do-no-harm cap applies (R-21).
      - Every card prints SE, MDE80 and power. UNDERPOWERED may convert only a failed step-5 or PC-3 p-value (R-24).
      - Step 3 uses N_eff (R-23). The BL-C12 tier is closed.
13. **Can a Korea protective card ever reach PASS on history alone?** Answered on v1.2's checks: yes, on the long history. DL-A (KOSPI 1997-04 → 2026-10, 3 bp book): ΔMDD +12.7 pp, tail ratio 0.68, ΔSR +0.026, p_ni 0.052, an indicative PASS that is fragile (largest episode share 0.493 against 0.50; 2016–25 REJECT; 1997–2015 INSUFFICIENT on sufficiency). The 2016–26 card alone stays inconclusive (p_ni 0.25). Twelve forward months add only 3–10% of the information, so the forward record is a falsification alarm, not the route.
    - *Status v2.0:* the formal route is now Resolution 1's v2 run on KRX official closes (R-06 KR). PASS requires all four of:
      - the full span;
      - the ETF-era line to 2025-12;
      - the 1997-05…1999-12 start band, with no REJECT and ≥ 2/3 PASS;
      - no REJECT in either midpoint half.

      PASS → BUILD-AS-INSURANCE, cap 1.0 permanent.

      **Expected outcome under v2 (R2-C1; spec R-06, §8.9).** On current evidence the formal run is expected to return INSUFFICIENT DATA, so the card is not expected to build: the selection factor f is computed from the R-06 family ledger as the maximum over the defensible row-set readings, and every indicative reading that includes the DL-A seed (1.49 with the DL-A grid, 2.87 family-wide) is above the 1.282 that PC-3 (p_ni × f ≤ 0.10) tolerates at the indicative p_ni 0.078. The card would stay a labelled control in the specification book, re-gated only when new history adds an objective episode, and no convention may be changed to rescue it.
14. **Cost-aware sizing.** How much protection survives when the rebalancing rule is designed for the cost? Candidates: a no-trade band, a slower estimator, or an ETF or futures line instead of a stock book (BL-G03, BL-G08).
    - *Status v2.0: answered.*
      - The instrument book comes first (R-26); a futures line is allowed only above the contract-granularity floor.
      - The band comes second, and only on stock and US-share books (QF1-M2).
      - The US futures card is R-29 (ST-01).

### 7b. Questions carried from the QF round (still open after the council)

1. **ECOS under 24-hour trading.** Onshore USD/KRW has traded 24 hours since 2026-07-06. Which timestamp does ECOS's "종가" use, and does the 15:30 series continue unchanged? (QF2) → BL-D13.
2. **A vendor "last" after the KRX after-market.** Does KRX disseminate KOSPI during its new after-market (from 2026-09-14)? Will vendors report a post-16:00 "last" as the day's value? (QF2) → the R-01 provisional-row guard.
3. **KIS quote fields.** Do KIS quotes carry level-1 bid/ask, and are they stamped with exchange or receipt time? (QF1, QF2) → the milestone-1 task (BL-D03).
4. **The post-close closing-price session.** Did KRX's post-close closing-price session (15:40–16:00) survive the 14–15 Sep 2026 extension? It is UNVERIFIED in the council's rulings; the random end itself is settled at ≤ 30 s since 2015-06-15. (QF1) → R-27.
5. **Treasury posting before 2010.** How reliable is Treasury's "usually by 6:00 PM" before 2010? (QF2) → the BL-D14 posting-time log.
6. **Golden-value vintages.** Should golden values be re-baselined when the French files are re-downloaded, or frozen forever as fixtures? (QF2) R-01 hashes the fixtures; the re-baselining policy is not yet written.
7. **A momentum sleeve net of constituent turnover.** What is the absolute net Sharpe of a Korean or US momentum sleeve once constituent turnover is costed at 35 / 50 bp per side? R-15's US prior of 2 depends on it. (QF5)
8. **The pooling rule.** Which markets, and which weights, give Tier A in price-state cards? The rule must be declared before any run (QF3-M4; R-28). (QF5)
9. **Korean implied variance.** Does QUANTGEN's own KOSPI 200 model-free implied variance improve log-HAR-range at 21 days? It needs about two years of logged boards. (QF6) → ST-09, BL-D27.
10. **The Korea vol target's worst days, 2016–25.** Why did the Korea vol target fail to de-risk the worst days of 2016–25 (tail ratio 0.95)? With 39% of KOSPI variance overnight, would an overnight-US input inside the vol forecast fix it? (QF6) → BL-U03.
11. **Fan acceptance.** For 126–252-session fans, which drift and which overlapping-origin test define acceptance? (QF6) → R-16.
12. **Leveraged-ETF carry and the leverage state.** Is KODEX Leverage's −3.7% a year carry stable across rate regimes? How should single-stock leveraged/inverse ETFs enter the Korea leverage state? (QF6) → BL-U01.
13. **A faster persistence model for Korea.** Shorter feature half-lives (5/10), a continuous jump model, or BOCPD on downside deviation? Each is a new trial, with a budget of at most two (QF7). This is research only: nothing acts or is displayed in v2 (R-33).
14. **D&M's post-2016 weakness.** Is the D&M add-on's post-2016 weakness (pooled +0.037, p 0.07) decay or sampling? It needs 2027+ data across regions. (QF3)
15. **The absorption-ratio rise of Apr–Jun 2026.** Is it a repeatable fragility signal (n = 1)? It is logged forward (QF5; R-13).

---

## 8. Priority summary (v2.0)

| Priority | Items |
|---|---|
| **P1 (start now)** | BL-C02 (reversal in fast stress; first milestone task: confirm the KIS level-1 quote fields) · BL-C06 (flows, logging) · BL-U01 (Korea leverage state) · BL-U02 (Korea factor priors; R-15's Korea reversal prior stays 1 until it runs) · BL-G06 (18-indicator sheet mapping; blocks M6) · data BL-D01, D02, D03, D04, D14, D21, D22, D23, D27, D30, D31 |
| **P2 (next quarter)** | BL-C01 (D&M floor; informs R-04's specification-book floor only) · BL-C05 (Korea flags) · BL-C07(a)(b) · BL-O01 (regional priors, as admissibility under R-15) · BL-O03 (supply screens) · BL-O12 (simulated-book limits) · BL-U03 (first step runnable now: QF7-A28's event-variance test) · BL-G01 residual task (publish `docs/vol_backtest.py` and its seed; EX2's B5 rerun) · BL-G07 (composite mapping) · data BL-D05, D10, D12, D15, D16, D17, D24, D25, D26, D28, D29 |
| **P3 (opportunistic)** | BL-C03, C07(c), C08, C09, C11, C13, C14 · BL-O02, O04–O07, O09–O11, O13, O14 · BL-U05–U07 · BL-G04 (ECOS formality) · BL-G08 (futures book; waits on the notional declaration) · data BL-D06, D07, D08, D09, D11, D13, D18, D19, D20 |
| **Council queue (§1; council priority)** | P1: ST-01 (the R-29 settling run; needs BL-D23), ST-02 (R-28), ST-03 (R-30, COMB) · P2: ST-04 to ST-06 (CONTESTED), ST-07 to ST-09 (context graduation tests) |
| **Owner decisions (§1.6; values in the spec's registry)** | D1 concentration template · D2 hard-stop level · D3 calm-state reversal (BL-O08) · D4 false-demotion budget · D5 whether, and on which line, to run a US sleeve · D6 CDaR-guard calibration (default frozen with the gate package; a ruling only before the first acceptance attempt) |
| **Open implementation tasks (§1.7; spec §9.4 items 15–17)** | 15 anchored timestamps (M7, before the freeze) · 16 an archived snapshot per formal card (M7) · 17 atomic `engine_feed` per book (M8) |
| **Resolved, moved or closed** | BL-C04 → R-30 · BL-C10 → R-28 · BL-G01 → R-30 · BL-G02 → R-21–R-24, R-34 · BL-G03 → R-29, R-26 · BL-G05 → R-01 · BL-C12 and BL-U04 closed |
| **Retired (§6.7)** | BL-S01 (R-11) and BL-S02 (R-12): labelled refusal books only |
| **Blocked by read-only design** | §5c (closing-auction routing, order handling at halts, fill-log slippage, order cancellation and reconciliation). BL-G09 records that a broker path is out of scope |

---

## Appendix V — v1.1 verification log

**What was checked.** Every golden value in spec §9.3 (R4, gross), every headline evidence number in spec §0.4, §2 and §5, and the whole current-state snapshot (spec §11) were traced to their source.

**How.** `scripts/r4b_verify_spec.py` reads each number as printed in the v1.0 text and looks up the source row in `results/*.csv`. If the number exists only in a note, it records the note file and line. A value is a MATCH when it equals the source at the printed rounding. Output: `results/R4b_verification_log.csv`.

**Result:** 266 checks. **v1.0 numbers (V, S and N rows):** 214 checks: 201 MATCH, 11 TRACED-NOTE, 2 MISMATCH, 0 NOT-FOUND. **New v1.1 numbers (W rows; self-check of R4b values typed into the v1.1 spec):** 52 checks: 52 MATCH, 0 MISMATCH. (Post-patch note, council errata: rows S05, V81, V82, V97e, V114, V142, N01 and W01–W03 matched values computed on the intraday KOSPI print of 2 Oct (in a file written at 10:56 KST); the official-close values are in spec §9.3 and §11.)

**Mismatches and how v1.1 fixed them:**
- **V140c, V140d** (spec §2.2). The constant-vol scaling line said "since 2020: … HML −0.03, CMA −0.06". Those are the full-sample 1990–2026 values. Since 2020 the values are HML −0.080 and CMA −0.162 (`B1b_robustness.csv`, `c_constvol_other_families`, start 2020-01-01). v1.1 prints both periods.

**Labelling and timing corrections** (the numbers matched, but their label was wrong):
- **V128–V131c.** v1.0 called DGS10 "+1 business day" the strict H.15 timing. For a decision at the 16:00 ET close it is 15 minutes early. Strict is +2 business days, which gives a full-sample ΔSR of −0.000 (R4b, `US_net`, "rates0.5 +2bd [v1.1 strict]").
- **R-01 evidence line.** v1.0's "+0.041 → +0.010" compared the R2 construction (+0.041) with R4's +1-day variant (+0.010). The R4-consistent chain is +0.038 → +0.010 → −0.000.
- **V113–V116.** The KRW-leg golden values use DEXKOUS by value date. That is a live-feed proxy, not H.10 publication timing, so they are labelled VALUE in spec §9.3. The strict value (+0.001) is added.
- **V29.** The Markov 0.554 / 0.390 and 0.442 / 0.137 Sharpe ratios are net of 10 bp. They are now labelled.
- **V111b.** v1.0 printed the 2–3% core-PCE stock–bond correlation as "−0.11 to −0.13". The source has pooled −0.114 and mean rolling-252 +0.040. No −0.13 was found, so v1.1 prints −0.11.
- **§11 S2 state.** "ON since 23 Sep 2026" is the data date. Under strict H.15 the forward book applies the flag from the close of 25 Sep, earning from 28 Sep (R4b `state_strict`).

| # | Number as printed (v1.0 text for V/S/N rows; v1.1 text for W rows) | Where in spec | Source (file / row, or note:line) | Source value | Status |
|---|---|---|---|---|---|
| V01 | t = 7.17 / t = 0.04 | §0.4; §13 N-04 | Q1a_data_lab_models_vs_reality.md:150 |  | TRACED-NOTE |
| V02 | 0.31 | §0.4; §2.4; R-01 | B3_korea_gate_backtest.csv G1pre_LOOKAHEAD 2016-2026 dSR | 0.3075 | MATCH |
| V03 | 0.4 | §0.4 (US momentum static SR) | R4 US_momentum static 1990-2026 sharpe | 0.3995 | MATCH |
| V04 | 0.8 | §0.4 (spec stack SR) | R4 US_momentum VS x DM 1990-2026 sharpe | 0.7978 | MATCH |
| V05 | -63 | §0.4 (static max DD %) | R4 static max_dd | -63.2882 | MATCH |
| V06 | -21 | §0.4 (stack max DD %) | R4 VS x DM max_dd | -20.9432 | MATCH |
| V07 | -38.6 | §0.4; R-06; §11 (KOSPI 22 Jun-30 Jul 2026 %) | R4 Korea_episodes BH Jul-2026 | -38.6304 | MATCH |
| V08 | -12.2 | §0.4; R-06; G-KR-03 | R4 Korea_episodes VT20 Jul-2026 | -12.2487 | MATCH |
| V09 | 33-44 years to detect +0.05 | §0.4; §8.4 | R2_E1_reviews_E5.md:34 |  | TRACED-NOTE |
| V10 | 0.33 | §2.1 (US 12-1 SR since 1990) | B2_intl_wml_by_decade.csv US full sharpe | 0.3292 | MATCH |
| V11 | 0.02 | §2.1 (US 12-1 SR since 2008) | B2_intl_wml_rules.csv US post-2008 base_sharpe | 0.016 | MATCH |
| V12 | 0.534 | §2.1; R-02; G-KR-06 (KOSPI VT cap 1.5 SR) | R4 Korea ref VT20_cap1.5 2016-2026 sharpe | 0.5342 | MATCH |
| V13 | -9.7 | §2.1 (Aug-2024 cap 1.5 %) | R4 Korea_episodes cap1.5 Aug-2024 | -9.6545 | MATCH |
| V14 | 0.07 | §2.2 (Japan WML SR) | B2_intl_wml_by_decade.csv Japan full | 0.0664 | MATCH |
| V15 | 0.4 | §2.2 (Japan WML t) | B2_intl_wml_by_decade.csv Japan full t_stat | 0.3976 | MATCH |
| V16 | 0.78 | §2.2 (Europe WML SR) | B2 Europe full | 0.7816 | MATCH |
| V17 | 0.71 | §2.2 (APxJ WML SR) | B2 AsiaPac_ex_JP full | 0.712 | MATCH |
| V18 | 0.196 | §2.2; R-03; G-INTL-01 (Japan VS) | R4 Intl WML Japan VS full | 0.1956 | MATCH |
| V19 | -0.023 | §2.2; R-03 (APxJ 2016-26 dSR) | R4 Intl APxJ VS 2016-2026 dSR_vs_static | -0.0231 | MATCH |
| V20 | -0.07 | §2.5; §10.1 (four-state book dSR) | B1_overlay_stats.csv viii_4state BOOK full dSR | -0.0729 | MATCH |
| V21 | 0.23 | §10.1 (four-state share) | B1_overlay_stats.csv viii_4state BOOK full share | 0.233 | MATCH |
| V22 | -12.0 | §2.5; R-04; G-MOM-06 (Nov-2020 static %) | R4 Mom episodes static 2020-11 | -12.0045 | MATCH |
| V23 | -10.9 | §2.5; R-04; G-MOM-06 (Jul-2026 static %) | R4 Mom episodes static 2026-07 | -10.8935 | MATCH |
| V24 | 0.05 | R-01; §10.5 (Korea gate implementable dSR) | B3 G1_prior_doc 2016-2026 dSR | 0.0467 | MATCH |
| V25 | 0.07 | R-01 (KRW 0.5x on DEXKOUS dates) | B3 G3_KRW_only_0.5x 2016-2026 dSR | 0.071 | MATCH |
| V26 | 0.03 | R-01 (KRW 0.5x Yahoo timing) | B3 G3y_KRW_only_0.5x_yahoo 2016-2026 dSR | 0.0301 | MATCH |
| V27 | 3.35 | R-01; §4.1; T-MISS-01; §11 (CPI YoY Aug-2026 %) | R4 state CPI calendar lag | 3.353 | MATCH |
| V28 | 3.71 | R-01; §4.1; §11 (wrong positional CPI %) | R4 state CPI positional | 3.713 | MATCH |
| V29 | Markov 0.5/1 vs 0/1: 0.554 vs 0.390 (US); 0.442 vs 0.137 (KOSPI) | R-02; §13 N-02 | R2_P1_reviews_P5_P6.md:72 |  | TRACED-NOTE |
| V30 | 0.399 | R-03; G-MOM-01 | R4 static sharpe | 0.3995 | MATCH |
| V31 | -63.3 | R-03; G-MOM-01 (%) | R4 static max_dd | -63.2882 | MATCH |
| V32 | 0.714 | R-03; G-MOM-02 | R4 VS sharpe | 0.7139 | MATCH |
| V33 | -27.9 | R-03; G-MOM-02 (%) | R4 VS max_dd | -27.9494 | MATCH |
| V34 | 0.87 | G-MOM-02 (avg weight) | R4 VS avg_weight | 0.8696 | MATCH |
| V35 | 60.6 | G-MOM-02 (% days at cap) | R4 VS pct_days_cap_binding | 60.5762 | MATCH |
| V36 | 0.907 | R-03; G-MOM-07 (cap 2) | R4 ref VS_cap2 sharpe | 0.9074 | MATCH |
| V37 | -0.19 | R-03 (cap cost full sample) | R4 VS dSR_vs_VS_cap2 1990-2026 | -0.1935 | MATCH |
| V38 | -0.23 | R-03 (cap cost 1990-2007) | R4 VS dSR_vs_VS_cap2 1990-2007 | -0.2302 | MATCH |
| V39 | 0.0 | R-03 (cap cost 2020-26) | R4 VS dSR_vs_VS_cap2 2020-2026 | 0.0001 | MATCH |
| V40 | 0.798 | R-04; G-MOM-03 | R4 VS x DM sharpe | 0.7978 | MATCH |
| V41 | -20.9 | G-MOM-03 (%) | R4 VS x DM max_dd | -20.9432 | MATCH |
| V42 | -30.5 | G-MOM-03 (vol-matched %) | R4 VS x DM max_dd_volmatched | -30.5402 | MATCH |
| V43 | 0.138 | R-04 (DM alone dSR) | R4 DM_floor0.5 dSR_vs_static | 0.1382 | MATCH |
| V44 | 0.998 | R-04 (DM alone share) | R4 DM_floor0.5 share | 0.998 | MATCH |
| V45 | 0.084 | R-04; G-MOM-04 | R4 VSxDM dSR_vs_VS_cap1 full | 0.0839 | MATCH |
| V46 | 0.996 | R-04; G-MOM-04 (share) | R4 VSxDM share_beats_VS_cap1 full | 0.996 | MATCH |
| V47 | 0.056 | R-04; G-MOM-04 (ex 2008-09) | R4 VSxDM dSR_vs_VS_cap1 ex | 0.0561 | MATCH |
| V48 | 0.055 | R-04; G-MOM-04 (2013-04+) | R4 VSxDM dSR_vs_VS_cap1 2013-04.. | 0.0551 | MATCH |
| V49 | 0.101 | G-MOM-04 (2020-26) | R4 VSxDM dSR_vs_VS_cap1 2020-2026 | 0.101 | MATCH |
| V50 | 10.6 | R-04; G-MOM-05 (% days on) | R4 DM pct_days_gate_on | 10.5924 | MATCH |
| V51 | 7 | R-04; G-MOM-05 (spell onsets) | R4 DM raw_spell_onsets | 7.0 | MATCH |
| V52 | 0.38 | R-04; G-MOM-05; §8.6 (transitions/yr) | R4 switch_budget DM | 0.3819 | MATCH |
| V53 | -21.9 | R-04; G-MOM-06 (Jan-2001 static %) | R4 Mom episodes static 2001-01 | -21.8517 | MATCH |
| V54 | -15.7 | G-MOM-06 (Jan-2001 stack %) | R4 Mom episodes VSxDM 2001-01 | -15.6707 | MATCH |
| V55 | -26.8 | G-MOM-06 (Apr-2009 static %) | R4 Mom episodes static 2009-04 | -26.7655 | MATCH |
| V56 | -4.2 | G-MOM-06 (Apr-2009 stack %) | R4 Mom episodes VSxDM 2009-04 | -4.187 | MATCH |
| V57 | -45.6 | G-MOM-06 (Mar-May 2009 static %) | R4 Mom episodes static 2009-03..05 | -45.638 | MATCH |
| V58 | -8.0 | G-MOM-06 (Mar-May 2009 stack %) | R4 Mom episodes VSxDM 2009-03..05 | -8.0133 | MATCH |
| V59 | -3.9 | G-MOM-06 (Nov-2020 stack %) | R4 Mom episodes VSxDM 2020-11 | -3.8851 | MATCH |
| V60 | -13.7 | G-MOM-06 (Jan-2023 static %) | R4 Mom episodes static 2023-01 | -13.7287 | MATCH |
| V61 | -3.8 | G-MOM-06 (Jan-2023 stack %) | R4 Mom episodes VSxDM 2023-01 | -3.7941 | MATCH |
| V62 | -5.9 | G-MOM-06 (Jul-2026 stack %) | R4 Mom episodes VSxDM 2026-07 | -5.9104 | MATCH |
| V63 | -11.0 | G-MOM-06 (2020 static %) | R4 Mom episodes static 2020 calendar | -11.0026 | MATCH |
| V64 | 3.1 | G-MOM-06 (2020 stack %) | R4 Mom episodes VSxDM 2020 calendar | 3.1436 | MATCH |
| V65 | 17.4 | G-MOM-06 (2022 static %) | R4 Mom episodes static 2022 | 17.4012 | MATCH |
| V66 | 12.3 | G-MOM-06 (2022 stack %) | R4 Mom episodes VSxDM 2022 | 12.3275 | MATCH |
| V67 | 21.8 | R-04; G-MOM-06 (May-Nov 2008 static %) | R4 Mom episodes static 2008-05..11 | 21.8074 | MATCH |
| V68 | 9.5 | R-04; G-MOM-06 (May-Nov 2008 stack %) | R4 Mom episodes VSxDM 2008-05..11 | 9.5273 | MATCH |
| V69 | 0.657 | G-MOM-07 (DM 0x) | R4 ref DM_0x sharpe | 0.6571 | MATCH |
| V70 | 1.358 | G-BOOK-01 (static) | R4 US_factor_book static | 1.3579 | MATCH |
| V71 | 1.753 | G-BOOK-01 (spec) | R4 US_factor_book spec | 1.7531 | MATCH |
| V72 | 0.4 | G-BOOK-01 (2020-26 static) | R4 book static 2020-2026 | 0.4001 | MATCH |
| V73 | 0.618 | G-BOOK-01 (2020-26 spec) | R4 book spec 2020-2026 | 0.6177 | MATCH |
| V74 | 1.253 | G-BOOK-01 (ST_Rev static) | R4 US_factor_baselines ST_Rev | 1.2535 | MATCH |
| V75 | 0.48 | G-BOOK-01 (RMW static) | R4 US_factor_baselines RMW | 0.4797 | MATCH |
| V76a | 0.073 | R-03; G-INTL-01 (Japan static) | R4 Intl Japan static full | 0.0734 | MATCH |
| V76b | 0.196 | R-03; G-INTL-01 (Japan VS) | R4 Intl Japan VS full | 0.1956 | MATCH |
| V77a | 0.843 | R-03; G-INTL-01 (Europe static) | R4 Intl Europe static full | 0.8427 | MATCH |
| V77b | 1.143 | R-03; G-INTL-01 (Europe VS) | R4 Intl Europe VS full | 1.1426 | MATCH |
| V78a | 0.924 | R-03; G-INTL-01 (AsiaPac_ex_JP static) | R4 Intl AsiaPac_ex_JP static full | 0.9243 | MATCH |
| V78b | 1.125 | R-03; G-INTL-01 (AsiaPac_ex_JP VS) | R4 Intl AsiaPac_ex_JP VS full | 1.1254 | MATCH |
| V79a | 0.799 | R-03; G-INTL-01 (Dev_ex_US static) | R4 Intl Dev_ex_US static full | 0.7995 | MATCH |
| V79b | 0.996 | R-03; G-INTL-01 (Dev_ex_US VS) | R4 Intl Dev_ex_US VS full | 0.9962 | MATCH |
| V80a | 0.921 | G-INTL-01 (APxJ 2016-26 static) | R4 Intl APxJ static 2016-2026 | 0.9205 | MATCH |
| V80b | 0.897 | G-INTL-01 (APxJ 2016-26 VS) | R4 Intl APxJ VS 2016-2026 | 0.8974 | MATCH |
| V81 | 0.638 | R-06; G-KR-02 | R4 Korea VT20 2016-2026 sharpe | 0.6378 | MATCH |
| V82 | 0.634 | R-06; G-KR-01 | R4 Korea BH 2016-2026 sharpe | 0.6337 | MATCH |
| V83 | -36.8 | R-06; G-KR-02 (%) | R4 Korea VT20 max_dd | -36.8186 | MATCH |
| V84 | -43.9 | R-06; G-KR-01 (%) | R4 Korea BH max_dd | -43.8979 | MATCH |
| V85 | -0.077 | R-06; §7 Q1 backlog (2016-25 dSR) | R4 Korea VT20 2016-2025 dSR_vs_BH | -0.0769 | MATCH |
| V86 | 0.06 | R-06 (2016-25 share) | R4 Korea VT20 2016-2025 share | 0.056 | MATCH |
| V87 | -0.123 | R-06 (2018-24 dSR) | R4 Korea VT20 2018-2024 dSR_vs_BH | -0.1226 | MATCH |
| V88 | 0.457 | G-KR-02 (2016-25 VT SR) | R4 Korea VT20 2016-2025 sharpe | 0.4572 | MATCH |
| V89 | -0.052 | G-KR-02 (2018-24 VT SR) | R4 Korea VT20 2018-2024 sharpe | -0.0517 | MATCH |
| V90a | -19.9 | R-06; G-KR-03 (Mar-2026 BH %) | R4 Korea_episodes BH Mar-2026 | -19.8947 | MATCH |
| V90b | -7.9 | R-06; G-KR-03 (Mar-2026 VT %) | R4 Korea_episodes VT20 Mar-2026 | -7.9056 | MATCH |
| V91a | -5.5 | R-06; G-KR-03 (Aug-2024 BH %) | R4 Korea_episodes BH Aug-2024 | -5.4693 | MATCH |
| V91b | -7.9 | R-06; G-KR-03 (Aug-2024 VT %) | R4 Korea_episodes VT20 Aug-2024 | -7.8925 | MATCH |
| V92a | -12.0 | R-06; G-KR-03 (Apr-2025 BH %) | R4 Korea_episodes BH Apr-2025 | -12.0227 | MATCH |
| V92b | -11.7 | R-06; G-KR-03 (Apr-2025 VT %) | R4 Korea_episodes VT20 Apr-2025 | -11.6867 | MATCH |
| V93a | -34.1 | R-06; G-KR-03 (2020 crash BH %) | R4 Korea_episodes BH 2020 crash | -34.0536 | MATCH |
| V93b | -25.8 | R-06; G-KR-03 (2020 crash VT %) | R4 Korea_episodes VT20 2020 crash | -25.8158 | MATCH |
| V94a | 49.9 | R-06; G-KR-03 (2020 rebound BH %) | R4 Korea_episodes BH 2020 rebound | 49.8511 | MATCH |
| V94b | 25.9 | R-06; G-KR-03 (2020 rebound VT %) | R4 Korea_episodes VT20 2020 rebound | 25.858 | MATCH |
| V95a | 101.1 | R-06; G-KR-03 (H1-2026 BH %) | R4 Korea_episodes BH H1-2026 | 101.142 | MATCH |
| V95b | 51.7 | R-06; G-KR-03 (H1-2026 VT %) | R4 Korea_episodes VT20 H1-2026 | 51.6797 | MATCH |
| V96a | 22.2 | R-06; G-KR-03 (post-crash BH %) | R4 Korea_episodes BH post-crash | 22.2484 | MATCH |
| V96b | 5.9 | R-06; G-KR-03 (post-crash VT %) | R4 Korea_episodes VT20 post-crash | 5.8716 | MATCH |
| V97a | 0.3 | R-06; G-KR-04; §11 (weight 2026-06-22) | R4 Korea_state 2026-06-22 | 0.3024 | MATCH |
| V97b | 0.33 | R-06; G-KR-04; §11 (weight 2026-06-23) | R4 Korea_state 2026-06-23 | 0.3309 | MATCH |
| V97c | 0.25 | R-06; G-KR-04; §11 (weight 2026-07-30) | R4 Korea_state 2026-07-30 | 0.2484 | MATCH |
| V97d | 0.61 | R-06; G-KR-04; §11 (weight 2026-10-02) | R4 Korea_state 2026-10-02 | 0.6124 | MATCH |
| V97e | 0.69 | R-06; G-KR-04; §11 (weight next session after 2026-10-02) | R4 Korea_state next session after 2026-10-02 | 0.6913 | MATCH |
| V98 | 28.9 | G-KR-04; §11 (KOSPI rv20 %) | R4 Korea_state rv20 | 28.9307 | MATCH |
| V99 | -46.2 | G-KR-06 (cap 1.5 max DD %) | R4 Korea ref cap1.5 max_dd | -46.175 | MATCH |
| V100 | 0.55 | R-06; BL-C04 (SMA60 SR) | R3_CHAIR_E_checks.txt SR_2016-26 SMA60 | 0.55 | MATCH |
| V101 | 0.602 | R-06; G-US-01 | R4 US VT15 sharpe | 0.6016 | MATCH |
| V102 | 0.534 | R-06; G-US-01 (BH) | R4 US BH sharpe | 0.5337 | MATCH |
| V103 | -49.9 | R-06; G-US-01 (VT max DD %) | R4 US VT15 max_dd | -49.9071 | MATCH |
| V104 | -59.2 | R-06; G-US-01 (BH max DD %) | R4 US BH max_dd | -59.1708 | MATCH |
| V105a | -20.9 | R-06 (GFC VT %) | R4 US_market_episodes VT15 GFC | -20.9086 | MATCH |
| V105b | -46.5 | R-06 (GFC BH %) | R4 US_market_episodes BH GFC | -46.5153 | MATCH |
| V106 | corr(vol, fwd 22d) +0.32 (KOSPI 2018-24) | R-06 failure modes | R2_P1_reviews_P5_P6.md:69 |  | TRACED-NOTE |
| V107 | 10.1 | R-08 (% days VIX>=VIX3M) | R4 switch_budget entry block pct | 10.095 | MATCH |
| V108 | 14.0 | R-08; §8.6 (transitions/yr) | R4 switch_budget entry block | 14.0256 | MATCH |
| V109 | next-5-day realised vol 36.3% vs 13.6% | R-08 evidence | Q1b_data_lab_overlay_and_markets.md:50 |  | TRACED-NOTE |
| V110 | cut-and-re-add -0.088 | R-08; §10.4 | R2_E5_reviews_E1_E6.md:63 |  | TRACED-NOTE |
| V111a | -0.29 | R-09 (stock-bond corr, core PCE < 2%) | A8_corr_by_inflation_bucket.csv <2% pooled_daily_corr | -0.2922 | MATCH |
| V111b | -0.11 | R-09 (stock-bond corr, 2-3%; printed -0.11 to -0.13) | A8 2-3% pooled_daily_corr | -0.1143 | MATCH |
| V111c | 0.21 | R-09 (stock-bond corr, >= 3%) | A8 >3% pooled_daily_corr | 0.2107 | MATCH |
| V112 | +7.27% over 13 weeks vs +2.84% (n = 14) | R-09; §10.15 | Q1a_data_lab_models_vs_reality.md:54 |  | TRACED-NOTE |
| V113 | 0.032 | R-11; G-KR-05 | R4 Korea KRW0.75 dSR_vs_BH | 0.0323 | MATCH |
| V114 | 0.965 | R-11; G-KR-05 (share) | R4 Korea KRW0.75 share | 0.965 | MATCH |
| V115 | 0.042 | R-11; G-KR-05 (on VT20) | R4 Korea stack dSR_vs_VT20 | 0.0423 | MATCH |
| V116 | 0.977 | R-11; G-KR-05 (on VT20 share) | R4 Korea stack share_vs_VT20 | 0.977 | MATCH |
| V117a | 0.016 | R-11 (+1 session) | R4 Korea rob +1 session dSR | 0.0165 | MATCH |
| V117b | 0.016 | R-11 (Yahoo timing) | R4 Korea rob Yahoo dSR | 0.0163 | MATCH |
| V118 | 9.0 | R-11; G-KR-05 (% days on) | R4 Korea KRW pct_days_on | 8.9666 | MATCH |
| V119a | 65 | R-11 (raw onsets) | R4 Korea KRW raw_onsets | 65.0 | MATCH |
| V119b | 35 | R-11 (de-clustered onsets) | R4 Korea KRW onsets_declustered_20s | 35.0 | MATCH |
| V120 | 11.1 | R-11; §8.6 (transitions/yr) | R4 switch_budget KRW | 11.0733 | MATCH |
| V121 | 0.06 | R-11 (0.5x reference) | R4 Korea ref KRW0.5 dSR | 0.0601 | MATCH |
| V122 | 4 Dec -1.44%, 9 Dec -2.78% (2024) | R-11 failure modes | R3_CHAIR_E_checks.txt:31 |  | TRACED-NOTE |
| V123 | 0.038 | R-12; G-US-02 | R4 US rates dSR_vs_BH | 0.0384 | MATCH |
| V124 | 0.98 | R-12; G-US-02 (share) | R4 US rates share | 0.98 | MATCH |
| V125 | 0.037 | R-12; G-US-02 (on VT15) | R4 US stack dSR_vs_VT15 | 0.037 | MATCH |
| V126 | 0.132 | R-12 (2020-26 on VT) | R4 US stack 2020-2026 dSR_vs_VT15 | 0.1319 | MATCH |
| V127 | 0.025 | R-12 (ex-2022) | R4 US rates ex-2022 | 0.0246 | MATCH |
| V128 | 0.01 | R-01; R-12; G-US-02 (+1 day) | R4 US rob +1 day dSR | 0.0096 | MATCH |
| V129 | 0.67 | R-12; G-US-02 (+1 day share) | R4 US rob +1 day share | 0.668 | MATCH |
| V130 | -0.017 | R-12 (+1 day, 1990-2007) | R4 US rob +1 day 1990-2007 | -0.0174 | MATCH |
| V131a | 0.066 | R-12; G-US-03 (DGS10 timing 2015-26) | R4 US_market_timing DGS10 | 0.066 | MATCH |
| V131b | 0.071 | R-12; G-US-03 (^TNX 2015-26) | R4 US_market_timing TNX | 0.0713 | MATCH |
| V131c | 0.071 | R-12; G-US-03 (+1 day 2015-26) | R4 US_market_timing +1 day | 0.0714 | MATCH |
| V132 | 6.2 | R-12; G-US-02 (% days on) | R4 US rates pct_days_on | 6.1735 | MATCH |
| V133 | 50 | R-12; G-US-02 (onsets, 60-session) | R4 US rates onsets_declustered_60s | 50.0 | MATCH |
| V134 | 7.2 | R-12; §8.6 (transitions/yr) | R4 switch_budget rates | 7.2008 | MATCH |
| V135a | 0.039 | R-12 (NDX 2008-26) | R4 US_duration_proxies NDX | 0.0391 | MATCH |
| V135b | 0.058 | R-12 (Russell 2000 2015-26) | R4 US_duration_proxies RUT | 0.0576 | MATCH |
| V136 | post-onset 60-day max DD -7.07% vs -7.17% | R-12 failure modes | R2_E5_reviews_E1_E6.md:50 |  | TRACED-NOTE |
| S01 | 23.9 | §11 US Mom sigma126 % | R4 state_2026-10-02 "Mom sigma126 (ann.)" | 23.9187 | MATCH |
| S02 | 0.5 | §11 vs | R4 state_2026-10-02 "Mom VS weight next day (cap 1, target 12%)" | 0.5017 | MATCH |
| S03 | 39.7 | §11 24m return % | R4 state_2026-10-02 "US 24m market return (last month-end)" | 39.7495 | MATCH |
| S04 | 14.3 | §11 mkt vol126 % | R4 state_2026-10-02 "US mkt vol126 (ann.)" | 14.2868 | MATCH |
| S05 | 6943.66 | §11 KOSPI close | R4 state_2026-10-02 "KOSPI close" | 6943.66 | MATCH |
| S06 | -23.8 | §11 KOSPI from peak % | R4 state_2026-10-02 "KOSPI drawdown from closing peak 9114.55" | -23.8179 | MATCH |
| S07 | 1.098 | §11 KOSPI/200d | R4 state_2026-10-02 "KOSPI / 200DMA" | 1.0979 | MATCH |
| S08 | 7666.45 | §11 S&P close | R4 state_2026-10-02 "S&P 500 close" | 7666.45 | MATCH |
| S09 | 1.062 | §11 S&P/200d | R4 state_2026-10-02 "S&P / 200DMA" | 1.0616 | MATCH |
| S10 | 10.7 | §11 S&P rv20 % | R4 state_2026-10-02 "US rv20 ann." | 10.7164 | MATCH |
| S11 | 16.34 | §11 VIX | R4 state_2026-10-02 "VIX" | 16.34 | MATCH |
| S12 | 18.37 | §11 VIX3M | R4 state_2026-10-02 "VIX3M" | 18.37 | MATCH |
| S13 | 3.12 | §11 HY OAS | R4 state_2026-10-02 "HY OAS" | 3.12 | MATCH |
| S14 | 47 | §11 HY 21d bp | R4 state_2026-10-02 "HY OAS 21d change bp" | 47.0 | MATCH |
| S15 | 1.47 | §11 Baa-10y | R4 state_2026-10-02 "BAA10Y" | 1.47 | MATCH |
| S16 | -12 | §11 Baa 21d bp | R4 state_2026-10-02 "BAA10Y 21d change bp" | -12.0 | MATCH |
| S17 | 5.29 | §11 10y | R4 state_2026-10-02 "DGS10" | 5.29 | MATCH |
| S18 | 50 | §11 10y 20d bp | R4 state_2026-10-02 "DGS10 20d change bp" | 50.0 | MATCH |
| S19 | 1356.51 | §11 DEXKOUS | R4 state_2026-10-02 "USD/KRW DEXKOUS" | 1356.51 | MATCH |
| S20 | -1.81 | §11 DEXKOUS dlog % | R4 state_2026-10-02 "DEXKOUS 20-obs dlog %" | -1.8074 | MATCH |
| S21 | 1360.63 | §11 KRW=X | R4 state_2026-10-02 "USD/KRW Yahoo KRW=X" | 1360.63 | MATCH |
| S22 | 0.38 | §11 KRW=X dlog % | R4 state_2026-10-02 "KRW=X 20-obs dlog %" | 0.3844 | MATCH |
| S23 | 3.01 | §11 core PCE | R4 state_2026-10-02 "Core PCE YoY % (calendar lag)" | 3.0076 | MATCH |
| S24 | 0.53 | §11 corr63 | R4 state_2026-10-02 "stock-bond corr63 (S&P vs -dDGS10)" | 0.5331 | MATCH |
| S25 | 0.33 | §11 corr252 | R4 state_2026-10-02 "stock-bond corr252" | 0.3259 | MATCH |
| S26 | 120.33 | §11 broad USD | R4 state_2026-10-02 "Broad USD DTWEXBGS" | 120.33 | MATCH |
| S27 | 1.67 | §11 broad USD 20d % | R4 state_2026-10-02 "Broad USD 20d change %" | 1.6659 | MATCH |
| S28 | 2.93 | §11 TIPS | R4 state_2026-10-02 "DFII10" | 2.93 | MATCH |
| S29 | 2.36 | §11 breakeven | R4 state_2026-10-02 "T10YIE" | 2.36 | MATCH |
| S30 | 2.36 | §11 5y5y | R4 state_2026-10-02 "T5YIFR" | 2.36 | MATCH |
| S31 | 1.02 | §11 KW TP | R4 state_2026-10-02 "THREEFYTP10" | 1.0203 | MATCH |
| S32 | 108.1 | §11 MOVE | R4 state_2026-10-02 "MOVE" | 108.125 | MATCH |
| S33 | 1.07 | §11 10y-3m | R4 state_2026-10-02 "T10Y3M" | 1.07 | MATCH |
| S34 | 0.46 | §11 10y-2y | R4 state_2026-10-02 "T10Y2Y" | 0.46 | MATCH |
| S35 | -0.07 | §11 Sahm | R4 state_2026-10-02 "SAHMREALTIME" | -0.07 | MATCH |
| S36 | 4.1 | §11 U-3 | R4 state_2026-10-02 "UNRATE" | 4.1 | MATCH |
| S37 | 113.96 | §11 Dated Brent | R4 state_2026-10-02 "DCOILBRENTEU" | 113.96 | MATCH |
| S38 | 102.59 | §11 BZ=F | R4 state_2026-10-02 "Brent front-month futures BZ=F" | 102.59 | MATCH |
| S39 | 157.18 | §11 USD/JPY | R4 state_2026-10-02 "USD/JPY DEXJPUS" | 157.18 | MATCH |
| S40 | 17.4 | §11 DM 2/3 quantile % | R4 state note (expanding 2/3 quantile) | 17.36 | MATCH |
| S41 | rv21 31.9% at the 73rd percentile | §11 KOSPI rv21 | R3_CHAIR_E_checks.txt:23 |  | TRACED-NOTE |
| S42 | probit last read 0.095 | §11; §6.4 example | Q1a_data_lab_models_vs_reality.md:30 |  | TRACED-NOTE |
| S43 | 1.0 | §11 vt_US | R4 US_state VT15 next session | 1.0 | MATCH |
| N01 | 0.638 | G-KR-02 gross reproduction (R4b) | R4b Korea_net gross VT20 | 0.6378 | MATCH |
| N02 | 0.032 | G-KR-05 gross reproduction (R4b) | R4b Korea_net gross KRW value | 0.0323 | MATCH |
| N03 | 0.01 | G-US-02 +1 day reproduction (R4b) | R4b US_net gross +1bd | 0.0096 | MATCH |
| N04 | 0.084 | G-MOM-04 gross reproduction (R4b) | R4b US_momentum_net gross DM on VS | 0.0839 | MATCH |
| V140a | -0.31 | §2.2 (constant-vol scaling dSR "since 2020") | B1b_robustness.csv constvol126_cap2 ST_Rev 2020-01-01 | -0.3105 | MATCH |
| V140b | -0.1 | §2.2 (constant-vol scaling dSR "since 2020") | B1b_robustness.csv constvol126_cap2 RMW 2020-01-01 | -0.1023 | MATCH |
| V140c | -0.03 | §2.2 (constant-vol scaling dSR "since 2020") | B1b_robustness.csv constvol126_cap2 HML 2020-01-01 | -0.0798 | MISMATCH |
| V140d | -0.06 | §2.2 (constant-vol scaling dSR "since 2020") | B1b_robustness.csv constvol126_cap2 CMA 2020-01-01 | -0.1624 | MISMATCH |
| V141 | 0.93 | §2.2 (EM WML SR) | B2_intl_wml_by_decade.csv Emerging full | 0.9281 | MATCH |
| V142 | 53.7 | R-07; §11 (Samsung + SK hynix implied share 2 Oct 2026 %) | B3_samsung_hynix_implied_weight_weekly.csv 2026-10-02 both | 53.66 | MATCH |
| V143 | 0.55 | R-06; BL-C04 (SMA60 VT SR, 3 decimals) | recomputed: KOSPI VT SMA60 20% cap1 gross 2016-2026 | 0.5505 | MATCH |
| W01 | 0.635 | v1.1 §9.3 G-KR-02 (ETF 3 bp SR) | R4b_golden_values_net.csv | 0.635 | MATCH |
| W02 | 0.605 | v1.1 §5 R-06; §9.3 (stock 35 bp SR) | R4b_golden_values_net.csv | 0.6054 | MATCH |
| W03 | 0.573 | v1.1 §9.3 (stock 70 bp SR) | R4b_golden_values_net.csv | 0.5731 | MATCH |
| W04 | -37.2 | v1.1 §5 R-06 (stock max DD %) | R4b_golden_values_net.csv | -37.169 | MATCH |
| W05 | -0.028 | v1.1 §5 R-06 (stock dSR vs BH) | R4b_golden_values_net.csv | -0.0283 | MATCH |
| W06 | -0.106 | v1.1 §5 R-06 (2016-25 at 35 bp) | R4b_golden_values_net.csv | -0.1058 | MATCH |
| W07 | -0.154 | v1.1 §5 R-06 (2018-24 at 35 bp) | R4b_golden_values_net.csv | -0.1536 | MATCH |
| W08 | -41.3 | v1.1 §0.4; §9.3 G-KR-02c (static same-exposure MDD %) | R4b_golden_values_net.csv | -41.2875 | MATCH |
| W09 | 4.4 | v1.1 §8.9 (KR ETF dMDD pp) | R4b_golden_values_net.csv | 4.4388 | MATCH |
| W10 | 4.1 | v1.1 §8.9 (KR stock dMDD pp) | R4b_golden_values_net.csv | 4.1185 | MATCH |
| W11 | 3.8 | v1.1 §8.9 (KR stock 2x dMDD pp) | R4b_golden_values_net.csv | 3.77 | MATCH |
| W12 | 0.82 | v1.1 §8.9 (KR tail ratio) | R4b_golden_values_net.csv | 0.818 | MATCH |
| W13 | 0.24 | v1.1 §8.9 (KR ETF p_ni) | R4b_golden_values_net.csv | 0.2445 | MATCH |
| W14 | 0.32 | v1.1 §8.9 (KR stock p_ni) | R4b_golden_values_net.csv | 0.319 | MATCH |
| W15 | 0.59 | v1.1 §8.9 (Jul-2026 share of benefit) | R4b_golden_values_net.csv | 0.5907 | MATCH |
| W16 | 0.375 | v1.1 §8.9 (KR stock plateau) | R4b_golden_values_net.csv | 0.375 | MATCH |
| W17 | -0.008 | v1.1 §0.4; R-11 (KRW value, 35 bp) | R4b_golden_values_net.csv | -0.0078 | MATCH |
| W18 | 0.001 | v1.1 R-01; R-11 (KRW strict H.10 gross) | R4b_golden_values_net.csv | 0.0014 | MATCH |
| W19 | 0.013 | v1.1 R-11 (KRW strict on VT20 gross) | R4b_golden_values_net.csv | 0.0134 | MATCH |
| W20 | 26 | v1.1 R-11 (strict onsets, 20-session) | R4b_golden_values_net.csv | 26.0 | MATCH |
| W21 | 0.029 | v1.1 R-11 (KRW value, ETF 3 bp) | R4b_golden_values_net.csv | 0.0289 | MATCH |
| W22 | 1.1 | v1.1 §8.9 (KRW value 35 bp dMDD pp) | R4b_golden_values_net.csv | 1.1266 | MATCH |
| W23 | 0.505 | v1.1 R-06 US (50 bp SR) | R4b_golden_values_net.csv | 0.5053 | MATCH |
| W24 | -53.8 | v1.1 R-06 US (50 bp max DD %) | R4b_golden_values_net.csv | -53.7757 | MATCH |
| W25 | -54.0 | v1.1 R-06 US (static same-exposure MDD %) | R4b_golden_values_net.csv | -53.9552 | MATCH |
| W26 | 0.2 | v1.1 §8.9 (US dMDD pp) | R4b_golden_values_net.csv | 0.1795 | MATCH |
| W27 | -3.4 | v1.1 §8.9 (US 2x dMDD pp) | R4b_golden_values_net.csv | -3.3915 | MATCH |
| W28 | 0.79 | v1.1 §8.9 (US tail ratio) | R4b_golden_values_net.csv | 0.7938 | MATCH |
| W29 | 0.52 | v1.1 R-06 (US EWMA 50 bp SR) | R4b_golden_values_net.csv | 0.5197 | MATCH |
| W30 | -0.0 | v1.1 §0 changelog; R-01; R-12 (strict +2bd gross) | R4b_golden_values_net.csv | -0.0 | MATCH |
| W31 | -0.103 | v1.1 R-12 (strict, 50 bp) | R4b_golden_values_net.csv | -0.1026 | MATCH |
| W32 | 0.053 | v1.1 R-12 (strict 2015-26 gross) | R4b_golden_values_net.csv | 0.0529 | MATCH |
| W33 | 0.084 | v1.1 R-12 (strict 2020-26 gross) | R4b_golden_values_net.csv | 0.0842 | MATCH |
| W34 | -3.5 | v1.1 §8.9 (rates strict dMDD pp) | R4b_golden_values_net.csv | -3.5229 | MATCH |
| W35 | 3.6 | v1.1 R-12 (turnover/yr) | R4b_golden_values_net.csv | 3.6007 | MATCH |
| W36 | 1.26 | v1.1 §0.4 (US VT cost drag %/yr) | R4b_golden_values_net.csv | 1.2597 | MATCH |
| W37 | 1.8 | v1.1 §0.4 (rates cost drag %/yr) | R4b_golden_values_net.csv | 1.8003 | MATCH |
| W38 | 0.672 | v1.1 R-03 (50 bp SR) | R4b_golden_values_net.csv | 0.6723 | MATCH |
| W39 | 0.745 | v1.1 §9.3 G-MOM-03 (50 bp SR) | R4b_golden_values_net.csv | 0.7447 | MATCH |
| W40 | 0.74 | v1.1 §0.4 printed "0.74" (W39 rounded to 2 decimals; v1.2 corrected this row, which had compared 0.074 with 0.0745) | R4b_golden_values_net.csv | 0.7447 | MATCH |
| W41 | 0.072 | v1.1 R-04 (DM add-on 50 bp) | R4b_golden_values_net.csv | 0.0724 | MATCH |
| W42 | 0.273 | v1.1 R-03 (VS vs static 50 bp) | R4b_golden_values_net.csv | 0.2728 | MATCH |
| W43 | 4.7 | v1.1 R-06; G-B5-01 (KOSPI SMA20 FHS %) | R4b_golden_values_net.csv | 4.7032 | MATCH |
| W44 | 4.99 | v1.1 G-B5-02 (SPY SMA20 FHS %) | R4b_golden_values_net.csv | 4.9944 | MATCH |
| W45 | 5.31 | v1.1 G-B5-03 (US SMA20 FHS %) | R4b_golden_values_net.csv | 5.3119 | MATCH |
| W46 | 6.33 | v1.1 G-B5-02 (SPY GARCH-t t-quantile %) | R4b_golden_values_net.csv | 6.3268 | MATCH |
| W47 | 7.55 | v1.1 G-B5-01 (KOSPI SMA20 every-7 %) | R4b_golden_values_net.csv | 7.5472 | MATCH |
| W48 | 0.12 | v1.1 G-B5-01 (KOSPI SMA20 PIT p) | R4b_golden_values_net.csv | 0.1174 | MATCH |
| W49 | elevated | v1.1 R-06; §11 (display label) | R4b display_labels | elevated | MATCH |
| W50 | normal | v1.1 R-06; §11 (display label) | R4b display_labels | normal | MATCH |
| W51 | 2026-09-25 | v1.1 §11; T-H10-02 / T-H15-01 | R4b state_strict | 2026-09-25 | MATCH |
| W52 | 2026-09-28 | v1.1 §11; T-H10-02 / T-H15-01 | R4b state_strict | 2026-09-28 | MATCH |

## Appendix Q — independent QA log (v1.2)

**Scope.** An independent reviewer, who had not seen how the deliverables were produced, re-checked the spec, this backlog, the research report and the published report's template on 2026-10-02. Headline numbers were recomputed from the raw data (French daily factors, `^KS11`, `^GSPC`, FRED `DGS10`) with code written for the review, not with the project's own functions: US momentum (0.3995 / 0.7139 / 0.7978; net 50 bp 0.675 / 0.748, within the ±0.01 Level-1 tolerance of R4b's 0.672 / 0.745), the Korea vol target (Sharpe, max DD, static same-exposure comparator, crash and bull windows, weights), the US vol target and the rates leg at three timings. All reproduced R4 / R4b. The full validation report, with the spot-check table, is `research_notes/QUANTGEN macro overlay research/R5_independent_QA_report.md`.

**Rule for edits.** Only objective fixes were applied: a wrong number against its source, a wrong label, a broken cross-reference, an internal contradiction with a clear correct answer, and the missing quick start. No rule, parameter, bound, priority or verdict class was changed. The HTML template was not edited (its fixes are listed in the QA report for the coordinator).

### Q.1 Edit log

| # | Location | Old | New | Reason | Source |
|---|---|---|---|---|---|
| Q01 | Spec header | "(v1.1)"; companion "(v1.1)" | "(v1.2)"; companion "(v1.2)" with Appendix Q | Version bump for the QA pass | — |
| Q02 | Spec, new block after the header | (absent) | "Quick start for Claude Code": reading order, milestone → section map, PR invariants, binding vs informative, open points | A 211 KB spec had no entry point for the implementer | Spec §0.3, §12 |
| Q03 | Spec, new "Changelog v1.1 → v1.2" | (absent) | Nine-item list of v1.2 corrections | Traceability | This log |
| Q04 | Spec §0.3 item 5 | "…to their source rows." | "…; Appendix Q logs the v1.2 independent QA corrections." | Cross-reference | — |
| Q05 | Spec R-03, failure modes | "Gains decay after publication: +0.66 (1990–2011) → +0.26 (2012–26)." | Labelled "with cap 2 (R2-P2)"; adds the cap-1 values +0.20 (1990–2007), +0.20 (2012–26), +0.26 (2020–26) | The quoted decay is from the cap-2 rule; under the spec's cap-1 rule no decay is visible between 1990–2007 and 2012–26 | `R2_P2_reviews_P1_P3.md:171` (cap 2); `R4_golden_values.csv` US_momentum, VS_cap1_t12, dSR_vs_static 0.2043 / 0.2037 / 0.2634 |
| Q06 | Spec R-06, estimator row | B5 = exceedance band + "PIT uniformity" (no threshold) | Adds "PIT χ² (10 equal bins) p ≥ 0.01", the app's own cut-off, and notes that FHS exceedance is partly self-calibrating | Undefined parameter for the implementer | Public page line 120 ("a PIT p below 0.01 … makes the first a REJECT"); `r4b_golden_net.py` docstring §4 |
| Q07 | Spec R-06, card row | "non-inferiority p 0.24 / 0.32 with 101-session blocks" | "…(the larger of the 10-session and 101-session block results; 0.21 / 0.29 with 101-session blocks alone)" | Mislabel: 0.24 / 0.32 are the 10-session values; R4b reports the maximum | `R4b_golden_values_net.csv` protective: PC3_p_ni_block10 0.2445 / 0.319; PC3_p_ni_blockPW 0.207 / 0.292; PC3_block_used 101 |
| Q08 | Spec §8.9, R-06 Korea ETF row | "p_ni 0.24 (101-session blocks)" | "p_ni 0.24 (larger of 10- and 101-session blocks; 0.21 at 101)" | Same as Q07 | Same as Q07 |
| Q09 | Spec R-11, card row | "Indicative REJECT on the protective claim at both timings." | REJECT under value timing (35 onsets); INSUFFICIENT DATA by tier under strict H.10 (26 onsets), with PC-1 and PC-2 failing at both | Contradicted the §8.7 verdict order, which decides sufficiency (PC-7) first | Spec §8.7; `R4b_golden_values_net.csv` Korea_net onsets_declustered_20s: value 35, strict 26 |
| Q10 | Spec §6.2, `overlay_decision` example | US momentum record carried `forward_sim` S2-RATES and an S2 reason | `forward_sim: []`; S2 reason removed; note that S2 belongs in the `market_gross` record | Contradicted R-12's scope (momentum excluded) and T-BASIS-01 | Spec R-12, T-BASIS-01 |
| Q11 | Spec §8.6, new note | (absent) | Lists the return dates behind four KOSPI golden windows that include the start-date return (Aug-2024, Apr-2025, Mar-2026, H1-2026), the truncated 2015–16 window and the omission of Sep-2026 for Korea | The table's convention ("returns after the start close") would fail G-KR-03 at Level-1 tolerance (H1-2026 buy-and-hold +96.7% vs golden +101.1%; Aug-2024 −6.6% vs −5.5%) | `r4_golden_values.py` lines 228–233; `r4b_golden_net.py` lines 287–291; QA recomputation on `^KS11` |
| Q12 | Spec §10 item 14 | "Q3-2026: KRW +12.4% with ₩21.5tn of foreign selling." | "Q3-2026: USD/KRW −12.4% (the won stronger), while foreigners sold ₩21.5tn in September alone." | Mixed periods: −12.4% is Q3 (DEXKOUS 1,548.78 → 1,356.51); September alone was −0.9% | FRED `DEXKOUS`; report (₩21.5tn = September) |
| Q13 | Spec §13 N-50 | "every one of 26 overlay CIs straddles 0" | "…26 market-level de-risk overlays (13 US, 13 KOSPI) … (momentum vol scaling, R-03, is not among them)" | Unscoped, it contradicted R-03 (one-sided p ≤ 0.001) | `R3_CHAIR_professors_resolution.md:263` |
| Q14 | Spec §7 YAML | `version: "1.1.0"`; `estimator_gate` without a PIT threshold | `version: "1.2.0"`; adds `pit_test: chi2_10_bins, pit_p_min: 0.01` | Same as Q06 | Same as Q06 |
| Q15 | Backlog header and changelog | "(v1.1)"; companion spec v1.1 | "(v1.2)"; companion spec v1.2; new "Changelog v1.1 → v1.2" | Version bump | — |
| Q16 | Backlog Appendix V, row W40 | "0.074 … (x0.1 scale check of W39) … 0.0745 … MATCH" | "0.74 … (W39 rounded to 2 decimals) … 0.7447 … MATCH" | Malformed check: compared a rescaled number with a rescaled source instead of the printed 0.74 with 0.7447 | `R4b_golden_values_net.csv` US_momentum_net, US_KIS_50bp, VS_cap1 x DM0.5, Sharpe 0.7447 |
| Q17 | Backlog BL-C06 | "in Sep-2026 they sold ₩21.5tn while the won rose 12%" | "in Sep-2026 they sold ₩21.5tn, and over Q3 USD/KRW fell 12.4% (0.9% in September itself)" | Period mismatch | FRED `DEXKOUS` 2026-06-30, 2026-08-31, 2026-09-25 |
| Q18 | Backlog §7, open question 5 | "+0.31 over 1990–2026 but +0.20 in 2012–26" | Adds that 1990–2007 was also +0.20 under cap 1 and that the visible decay is a cap-2 result | The original framing implied a decay that the cap-1 data do not show | `R4_golden_values.csv` (as Q05) |
| Q19 | Backlog, new Appendix Q | (absent) | This appendix | QA log | — |
| Q20 | Report, executive summary | "both in shadow mode" | "both only as shadow (forward-simulated) cards" | v1.1 terminology (FORWARD-SIM) | Spec §5 |
| Q21 | Report, executive summary (last sentence) | Ended at "drawdown-first claim type." | Adds that spec v1.1 defines it and gives the indicative verdicts at QUANTGEN's costs | The report pre-dated v1.1's net-of-cost results | Spec §8.7, §8.9 |
| Q22 | Report, Korea section | "…TAIEX 16.4% and the Nikkei 15.1%." | "…the Nikkei 14.5% (15.1% to its 29 Jul low)." | Number did not match the stated 22 Jun–30 Jul window | Yahoo `^N225`: 72,353.96 → 61,867.43 = −14.49%; low 61,434.19 on 29 Jul = −15.09% |
| Q23 | Report, Korea section | "…then fell 12.4% to 1,356.5 by 25 Sep" (after the 5 Jun 1,555.96 high) | "…then fell to 1,356.5 by 25 Sep: −12.8% from that high and −12.4% over Q3" | −12.4% is the Q3 change, not the change from the 5 Jun high | FRED `DEXKOUS` |
| Q24 | Report, state table | "Shadow rates leg ON since 23 Sep" | "ON in data dated 23 Sep; under strict H.15 timing it applies from the 25 Sep close" | v1.1 strict H.15 rule | `R4b_golden_values_net.csv` state_strict |
| Q25 | Report, "Where the models work" | "Its local gain fell from +0.66 … to +0.26" | "Its local gain (with a 2× leverage cap) fell…" | Cap label (as Q05) | `R2_P2_reviews_P1_P3.md:171` |
| Q26 | Report, disputes (reversal) | "Neither side has KIS fill data, so the question goes to a shadow test (BL-C02)." | "A read-only desk has no fill data, so the question goes to a forward-simulated test priced with KIS quote snapshots (BL-C02)." | v1.1 (backlog §5c, BL-C02) | Backlog BL-C02 |
| Q27 | Report, corrected-anchors table, KRW row | "+0.03 with honest timing" | "+0.03 (0.5× leg) with Yahoo timing; … the spec's 0.75× leg gives +0.016 with one extra session and +0.001 under strict H.10 publication" | v1.1 shows Yahoo or value timing is not strict publication timing | `R4_golden_values.csv` +1 session 0.0165; `R4b_golden_values_net.csv` strict-H.10 0.0014 |
| Q28 | Report, corrected-anchors table, rates row | "+0.010 with the H.15 next-business-day posting lag; 2015–26 robust at +0.066 to +0.071" | Full chain: +0.041 (R2) / +0.038 value / +0.010 at +1 business day (15 minutes early) / −0.000 strict; 2015–26 +0.053 strict | Contradicted v1.1's strict H.15 rule | `R4b_golden_values_net.csv` US_net: +2bd −0.0000, 2015–26 +0.0529 |
| Q29 | Report, neural-link section | "SOX beta rose from 0.17 to 0.56 in 2026" | "…from 0.17 (2015–19) to 0.56 in 2026 (0.25 over the full 2015–26 sample)" | Baseline label; the spec quotes 0.247 | Q1b-C13 |
| Q30 | Report, round-4 golden paragraph | KRW "+0.032 … +0.042" unlabelled; "rates leg +0.010 under strict H.15 timing" | KRW labelled gross / value timing, with strict +0.001 and net −0.008; rates +0.010 is the one-day lag, strict −0.000 | Contradicted v1.1 | `R4b_golden_values_net.csv` |
| Q31 | Report, settling-test table rows N-22, N-24 | "ΔSR ≥ 0 … 12 months of shadow"; "Tier A count met; 12 months of shadow" | v1.1 protective-check settling tests (BL-S01, BL-S02) | Superseded by v1.1 | Backlog BL-S01, BL-S02 |
| Q32 | Report, settling-test table row N-10 | "KIS fill logs: stress-day slippage + spread + tax vs gross edge" | Forward-simulated reversal at 35 bp with KIS quote-snapshot spreads | No fill logs in a read-only app | Backlog §5c |
| Q33 | Report, read-only section | "The spec was written as if QUANTGEN routes capital." | "Spec v1.0 was written as if…; v1.1 re-maps it…" | Version scope | Spec changelog v1.0 → v1.1 |
| Q34 | Report, read-only section | BUILD NOW "allowed to size strategy cards" | Adds that only PASS cards feed the displayed recommendation | v1.1 P7 | Spec P7 |
| Q35 | Report, "first gap" paragraph | "mirrors the governance in spec §8 (Tiers A/B/C, shadow book and kill criteria)" | "Spec v1.1 §8.7 now defines exactly this class (CARD-P, PC-1..PC-7), alongside … forward-simulated books and demotion rules"; decay labelled 2× cap | Superseded terms | Spec §8.7, §8.8 |
| Q36 | Report, "second gap" paragraph | "The panels and the spec assumed a 0.35% Korean round trip"; "Every factor result in this report is gross of costs." | "…spec v1.0 assumed…; spec v1.1 adopts the desk's own costs"; "…in the body … the Addendum gives the net values." | v1.1 costs | Spec P10 |
| Q37 | Report, build-order sentence | "data layer, … falsification pipeline, shadow legs, … Quant Lab" | v1.1 milestones M0–M10 | Superseded build order | Spec §12 |
| Q38 | Report, day-one table | "Rates shadow leg: ON since 23 Sep" | "ON in data dated 23 Sep; applies from the 25 Sep close (strict H.15)" | As Q24 | As Q24 |
| Q39 | Report, limitations | French-gross sentence; "The spec's execution conventions…" | Adds the Addendum reference and that constituent turnover stays uncosted; scopes the conventions to v1.0 and states v1.1's treatment | Superseded | Spec R-05, R-10 |
| Q40 | Report, new section before Sources | (absent) | "Addendum — implications at QUANTGEN's own costs (spec v1.1)" | The report did not reflect v1.1's net-of-cost results or the protective card class | `R4b_golden_values_net.csv`; spec §8.7, §8.9 |
| Q41 | Report, "Two more spec rules apply now" paragraph | "…puts the shadow legs, the reversal fill test, Korean flows, …first." | Lists v1.1's P1 gate and data items first, then the shadow legs and "the reversal stress test on KIS quote snapshots" | Superseded priority list; no fill logs in a read-only app | Backlog §8 priority summary |

### Q.2 Open points for the owner (recorded, not edited)

These are judgment calls. The spec's quick start tells Claude Code not to guess them. **v2.0:** the council has answered all five. The answers live in SPEC v2.0 and are recorded below (#1, #3 and #4 per QCE-236).

1. **Drawdown-ladder composition (R-07).** Are the steps cumulative? At −12%, does the −8% "gross × 0.5" remain in force while the overlay is forced to 0.5 (net 0.25), or does the −12% step replace it? The bound P2 allows both.
   - **Answered (council, Resolution 6; SPEC v2.0 R-07, R-02, R-31):**
     - **Composition.** The steps are not cumulative. The ladder is one risk-layer function on whole-book NAV, composed by `min()`: final = vt × min(overlay₁, …, overlayₖ, ladder). Outside HALTED, final ≥ 0.5 × vt, and a product-composed path is refused.
     - **Steps.** −8% → 0.5×; −12% → 0.5× plus a new-entry block. Each step lasts at most 21 sessions, after which its reference resets. Where the steps bind on more than 10% of days (≈ 19% for KOSPI VT20), they act only in the specification book until the step-down CARD-P (R-31) passes.
     - **Hard stop.** A level of book NAV from the HWM since the last re-arm (owner decision D2: the council's options are −15% and −1.5 σ_book; the value in force is the spec's registry, §1.6): HALTED, with re-arm refused for 10 sessions. At re-arm the hard-stop reference resets to NAV, and exposure is 0.5× for the next 10 sessions. I-04 gains a re-entry regression test.
2. **Staleness of slow, risk-model-only inputs (§4.1, §3.8, R-09).** The default maximum staleness for weekly series is 3 days, but H.10 publishes weekly; read literally, both readings fail: by observation age a weekly H.10 `hedge_state` input is stale at every decision, and by release age it is stale from Thursday to Monday every week, and "stale for more than one decision" moves the engine to HALTED (0×). R-09 says `hedge_state` has no exposure effect. A conservative alternative: a stale `hedge_state` input sets `hedge_credit_off = TRUE` and raises an alert without halting. **Answered (council):** schedule-aware staleness (expected availability + grace) with role-based failure actions; risk-model-only inputs never HALT; DTWEXBGS moves to context, with a labelled live proxy acting.
3. **Korea concentration caps on an ETF instrument book (R-07, R-06).** §8.9 prefers the KRX ETF line, but a KOSPI ETF carries the index's ≈ 54% Samsung + SK hynix weight on look-through, above the 0.35 pair cap. Decide whether caps apply on look-through and, if so, how an ETF-line vol target satisfies them. Also state the scope of the 0.05-of-NAV single-name cap, which would make the 0.35 pair cap redundant in a stock book.
   - **Answered (council, Resolution 12; SPEC v2.0 R-07):**
     - **Look-through.** The caps apply on look-through, computed daily from the ETF baskets, with leveraged products at × L.
     - **Single-name cap.** It is active: w_i − g·b̃_i ≤ 0.05 of NAV against the capped benchmark b̃.
     - **Aggregate template.** It is the owner's (D1; the value in force is the spec's registry, §1.6), and the 0.45 → 0.35 trigger is dropped.
     - **Meeting a binding cap.** First lower the ETF line's weight: g_KR ≤ min(vt, limit_k / look-through share_k). An ex-pair basket is used only if the owner asks for full Korea beta at the cap, a stock-book card has passed and limit-lock flags exist.
     - **Unchanged.** The semiconductor cap of 0.50.
4. **Normalising the 0–3 priors (R-15, §3.3).** `active_budget = base_weight(m,f) × …` uses priors on a 0–3 scale. State the conversion (for example, per-market normalisation to sum 1, as BL-O01's weight rule implies) so that no weight exceeds 1.0.
   - **Answered (council, Resolution 12; SPEC v2.0 R-15):**
     - **Weights.** base_weight(m, f) = IV_m × 1/K_m over the admissible families of market m (prior ≥ 1 and card not REJECT). Family weights sum to 1 per market and Σ IV_m = 1, so no weight exceeds 1.0.
     - **Priors.** The 0–3 integers are for admissibility and display only. A bounded tilt is allowed only after a family's own card passes, as a registered revision.
     - **Across markets.** Inverse-vol on weekly returns (EWMA 0.97 or Ledoit–Wolf 156 weeks).
     - **Korea.** The reversal prior is 1 (UNVERIFIED) until BL-U02 runs net of 35 bp plus tax.
5. **Sep-2026 as a Korea drawdown episode (§8.6).** R4b omitted it for Korea; the card header should declare it either way. **Answered (council):** Sep-2026 is not a Korea episode (KOSPI +0.26% over the window, drawdown −6.0%; S&P −0.45%, −2.5%). Episodes come from a pre-registered objective rule on each market's own closes (≥ 20% bear markets for KOSPI, ≥ 15% for the S&P).

## Appendix C — Council log (round QF → QX → QC, 2026-10-02)

**Scope.** This appendix records what the Quant Council round did, in order, and the files behind each step. All paths are under `research_notes/QUANTGEN macro overlay research/` unless stated. Every persona behind the papers, reviews and chairs is simulated: a fictional composite citing public sources only.

### C.1 Sequence

| Step | What happened | Output | Files |
|---|---|---|---|
| **QF: audit papers** | Seven quant-finance members audited SPEC v1.2, BACKLOG v1.2, the REPORT and the PAGE in their own lanes, with pilots on local data. Each paper has an audit register, proposals, a claims register, a failure log, expected disagreements and open questions | 180 audit items, 60 proposals, 96 claims, and one split row (QF3-A1b). By member (audits / proposals / claims): QF1 Kestrel, execution and KRX microstructure, 25 / 6 / 14; QF2 Ostrava, point-in-time data, 28 / 9 / 14; QF3 Halcyon, statistical validation and ML, 24 / 8 / 13; QF4 Meridian, portfolio risk, 23 / 9 / 12; QF5 Larkspur, factor and multi-asset, 27 / 10 / 16; QF6 Vireo, volatility and the Quant Lab, 25 / 11 / 15; QF7 Corvid, methods, regimes and curricula, 28 / 7 / 12 | `00_QF_BRIEFING.md`, `00_QF_AUDIT_PROTOCOL.md`, `00_QF_DOC_MAP.md`; `QF1_market_making_microstructure.md` … `QF7_methods_regimes_curricula.md` |
| **Data patch** (17:20 KST) | The original `yahoo_daily/` download had stored mid-session prints as 2-Oct closes. They were replaced by official closes, and provisional and partial-month rows were dropped (§5a DQ-01, DQ-02); on 3 Oct, 3 duplicate-date rows and 2 more provisional rows followed | 60 logged actions (55 on 2 Oct, 5 on 3 Oct) | `quantgen_macro_data/results/QF0_data_patch_20261002.csv`; `quantgen_macro_data/CATALOG.md`; `_snapshots/` |
| **QX: cross-examination** | The Professors (PX1 methods, PX2 pricing) and the Executives (EX1 risk, EX2 trading) judged every QF item (UPHELD / UPHELD-QUALIFIED / OVERTURNED / UNRESOLVED, with support scores). Each review added six new points | 24 new points (X-PX1-N1 … X-EX2-N6) | `00_QX_CROSS_EXAM_PROTOCOL.md`; `QX_PX1_professors_methods_review.md`, `QX_PX2_professors_pricing_review.md`, `QX_EX1_executives_risk_review.md`, `QX_EX2_executives_trading_review.md` |
| **QX: data labs** | **DL-A** independently replicated the protective cards and the governance findings: its harness reproduces all 385 R4b quantities exactly, and its master table has 62 rows. **DL-B** replicated the estimator race, the R-03 statistics, the trend axis, the regime models, gate power and R-08: 19 REPLICATED, 6 PARTIALLY REPLICATED, 0 NOT REPLICATED, 3 CORRECTED | Settled facts for the council (C.3) | `QX_DLA_data_lab_protective_cards.md`; `QX_DLB_data_lab_estimators_regimes.md`; `quantgen_macro_data/results/QX_DLA_*.csv`, `QX_DLB_*.csv` |
| **QC: docket** | 355 items: 142 consent, 77 qualified, 23 contested, 113 unreviewed (claims rows and new points) | The docket | `council/QC_docket.csv`; `00_QC_COUNCIL_PROTOCOL.md` |
| **QC: chairs** | Three chairs (Professors, Executives, QF) ruled on every qualified and contested item, all 60 proposals and every new point. Each set at most five red lines, ranked a top 10 and answered the owner's open questions | 149 merged rulings | `council/QC_P_professors_chair.md`, `council/QC_E_executives_chair.md`, `council/QC_Q_quant_chair.md`, `council/QC_chair_votes_merged.csv` |
| **QC: secretary** | Final classes for each item, twelve headline resolutions, the 15 red lines (all respected; two bound a sub-point against a majority), five owner decisions and the settling tests | A 361-row ledger (the 355 docket items plus PX1's six new points); 34 SPEC v2.0 modules (16 CHANGED, 14 NEW, 2 DEMOTED, 2 RETIRED; 16 P0, 14 P1, 4 P2) | `council/QC_COUNCIL_RESOLUTIONS.md`, `council/QC_ledger.csv`, `council/QC_modules.csv` |
| **QC: errata** | Old-text → new-text corrections for the four artifacts, with a verifier | 348 rows: 269 REPLACE (SPEC 125, BACKLOG 66, REPORT 59, PAGE_HTML 19); 48 SPEC-REWRITE (SPEC 44, BACKLOG 4); 31 REGENERATE (PAGE_JSON) | `council/QC_errata.csv`, `council/QC_errata_notes.md`, `council/QC_errata_verify.py` |
| **This backlog, v2.0** | The 66 BACKLOG REPLACE rows applied; the 4 BACKLOG SPEC-REWRITE rows absorbed (QCE-170, -200, -213, -236); 46 BL items re-statused; the council queue; failure-archive additions; data acquisitions v2; the data-quality log | — | This file; `deliverables/.v1.2_BACKLOG_backup.md` (pristine v1.2) |

### C.2 Outcome by final class (`QC_ledger.csv`)

| Class | Items | audit | proposal | new point | claim | other | Where it lands in this backlog |
|---|---|---|---|---|---|---|---|
| VALID-BUILD | 140 | 76 | 45 | 19 | 0 | 0 | SPEC v2.0 modules. Here: re-statused BL items (§0) and data needs (§5) |
| VALID-ERRATA | 67 | 63 | 0 | 3 | 1 | 0 | Corrections applied: the 66 BACKLOG errata rows here; the rest in SPEC, REPORT and PAGE |
| VALID-SHADOW | 7 | 5 | 2 | 0 | 0 | 0 | §1.2 (CQ-01 to CQ-07) |
| CONTEXT-ONLY | 9 | 1 | 7 | 1 | 0 | 0 | §1.4 (CQ-11 to CQ-19) |
| CONTESTED | 3 | 0 | 3 | 0 | 0 | 0 | §1.3 (CQ-08 to CQ-10) |
| INVALID | 3 | 0 | 2 | 0 | 0 | 1 | §6.9 (#36 to #38) |
| OWNER-DECISION | 3 | 1 | 1 | 1 | 0 | 0 | §1.5 and §1.6 (D1, D3) |
| CONFIRMED | 34 | 34 | 0 | 0 | 0 | 0 | The statements stand (e.g. QF5-A25 for BL-O07; QF3-A24 and QF4-A18 for §6.7) |
| INFO | 95 | 0 | 0 | 0 | 95 | 0 | Summarised by their parent items |
| **Total** | **361** | 180 | 60 | 24 | 96 | 1 | |

Of the 265 ruled or consent items (claims aside), 213 are accepted for action: 59 at P0, 81 at P1 and 73 at P2.

### C.3 The twelve headline resolutions (`QC_COUNCIL_RESOLUTIONS.md` §b)

1. **Korea vol target (R-06 KR):** BUILD-AS-INSURANCE on a formal PASS on long KRX history; labelled crisis-clustering insurance; cap 1.0 permanent.
2. **US vol targets:** the 50 bp card stays REJECT, relabelled by instrument. MACRO-R06-US-FUT (R-29) is FORWARD-SIM, pending a 1926+ settling run and a US sleeve.
3. **Estimator:** SMA20 stays acting (2–1). COMB is the registered challenger for ETF and futures books, behind a staged gate (R-30).
4. **PC-1 → PC-1′:** the tail legs gate and drawdown is printed. A do-no-harm cap and a gate-acceptance test are added (R-21).
5. **Step 3:** N_eff = max(N_clusters, N_equiv). R-03 PASSes (borderline); R-04 FAILs (R-23).
6. **Drawdown ladder:** `min()` composition, an explicit re-arm and time-boxed steps. The hard-stop level is D2 (R-07, R-02, R-31).
7. **Staleness** is judged against the publication schedule and the input's role; risk-model inputs never HALT (R-19).
8. **Refusals:** R-08 is demoted to an annotation. R-11 and R-12 are retired as labelled REJECTs.
9. **Trend:** a protective-only SMA10m card for US and other non-Korean sleeves (R-28); Korea is context.
10. **Regime engine:** nothing acting or displayed in v2. The jump model is CONTESTED.
11. **Episode table:** objective market-own episodes, extended before 2008 (R-22).
12. **Korea concentration caps** (look-through; an active 0.05 cap; the template is D1), **priors normalisation** (R-15), and **Sep-2026** is not an episode.

**Data-lab facts treated as settled** (`00_QC_COUNCIL_PROTOCOL.md`), not to be relitigated without new evidence:
- The 2-Oct "close" 6,943.66 was an intraday print.
- The literal drawdown ladder never leaves HALTED after its first −15% breach.
- The §4.1 defaults make H.10 inputs stale at 100% of decisions.
- R-11 and R-12 are REJECT on long data, with ≥ 54 / 71 onsets.
- R-08 is a protective failure.
- SMA20 is outside the QLIKE model confidence set, but not under MSE.
- QF3's N̂ formula is not the cited paper's.
- The Korea vol target is an indicative but fragile PASS on 1997-04 → 2026-10.
- The US 50 bp card is REJECT, and the futures card is a marginal PASS that flips with start date and estimator.
- The §8.6 episode table has no window before 2008.

### C.4 Where to find each council output in this file

| Council output | Here |
|---|---|
| Re-status of the v1.2 backlog | §0 |
| VALID-SHADOW, CONTESTED, CONTEXT-ONLY and OWNER-DECISION items, with settling tests | §1.1–§1.5 |
| Owner decisions D1–D6 (the council's D1–D5, plus D6 from the spec's adversarial review; values in the spec's registry) | §1.6 |
| Other named settling tests; the spec's open implementation tasks (§9.4 items 15–17) | §1.7 |
| R-08, R-11, R-12 and R-04's route; the INVALID items | §6.7–§6.9 |
| The v1.2 mechanisms replaced, and the QF failure logs | §6.10–§6.11 |
| Data needs (QF lists and the data labs' caveats) | §5 |
| The 2-Oct incident and the vendor caveats | §5a |
| The QF open questions left open | §7b |
| The answers to the owner's v1.2 questions | Appendix Q.2 |

*End of backlog.*
