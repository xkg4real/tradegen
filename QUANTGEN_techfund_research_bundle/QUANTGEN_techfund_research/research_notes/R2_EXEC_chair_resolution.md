# R2 Executives' panel: chair's triage and resolution

**Chair:** "Chair of the Executives' panel", a fictional composite (former global head of markets risk and trading at a bulge-bracket bank). The chair and the seven panelists (E1-E7) are fictional personas. None of them is a real person, and none speaks for a real firm.
**As of:** 3 Oct 2026, 00:35 KST.
**Panel independence:** the chair did not open the professors' papers (P1-P7), their working notes or resolution, or any `prof_*` verification file. The two panels meet only at the synthesis step.
**Status of inputs:** a first draft used the round-2 lab's interim result files. The lab then wrote `/home/claude/datalab/r2/R2_KR_summary.md` and `/home/claude/datalab/r2/R2_IDX_summary.md` (00:16 KST), and the chair read both before finalising this file.
- Numbers labelled **R2** come from those summaries or from their result files in `/home/claude/datalab/r2/{kr,idx}/results/`.
- Where the lab's final reading differs from the chair's, both readings are shown. The main case is low volatility (EX-T-06).
- The chair also ran one new test on the lab's own books: c12, low volatility against a same-beta static book.
**Macro decisions:** P0-P10, R-03..R-15 and §8.7 of `QUANTGEN_MACRO_INTEGRATION.md` were not re-litigated. Where the panel's evidence bears on them, this file flags the conflict (section 6.2) and leaves the decision to the coordinator.

**Companion files**
- Claim matrix (60 propositions X01-X60 covering all 205 panel claims): `/home/claude/datalab/r2/verification/exec_claim_matrix.csv`
- Verification log (103 rows): `/home/claude/datalab/r2/verification/exec_verification_log.csv`
- Chair's recomputation scripts and outputs: `/home/claude/datalab/r2/verification/exec_chair_checks/` (c00-c13; c12 is the same-beta low-vol test on the R2 books, c13 patches the claim matrix with the final R2 summaries)
- Extraction notes: `/home/claude/research_notes/QUANTGEN technical and fundamental signals/R2_EXEC_working_notes.md`

**Triage labels**
- **BUILD NOW**: implement now. This covers conventions, data layers and reporting. A screen or card built now still feeds the displayed book only after it passes the gate (P7).
- **FORWARD-SIM**: run in the forward-simulation book only (P7: it never feeds the displayed book).
- **BACKLOG**: needs data or another prerequisite first.
- **DROP**: do not build.
- **CONTEXT**: display, prior or governance only.

**Number conventions:** "net35" means net of 35 bp per side and "net70" means the 2x stress case. Unless a line says otherwise, Korean stock results are in-sample (IS) and price-only.

---

## 1. Summary (10 sentences)

1. The executives' panel filed 205 claims. The chair mapped them into 60 propositions, cross-examined each paper through its assigned reviewer, and re-checked 103 printed numbers against local data, official sources and the round-2 lab's final summaries and result files.
2. Of the 103 checks, 77 matched, 12 mismatched, 11 were traced with a note and 3 could not be verified. Most mismatches change magnitudes, not decisions. Four change a decision:
   - Dynamic momentum doubles Sharpe; it does not quadruple it.
   - Bounding trend to [0.5, 1.0] does not halve its protection measured against the same exposure, although it gives back absolute protection in slow bears.
   - Korean low volatility fails an exposure-matched drawdown test, so the chair reads it as de-gearing rather than a crash hedge. The lab reads it as protective against the market; this is contested.
   - The 82 bp insider anchor is a long-short one-month result, so it cannot support a long-only overlay.
3. The panel reached consensus on 28 items, left 14 contested, and refuted or withdrew 12.
4. The strongest consensus is negative and cost-driven:
   - Intraday rules and daily/weekly KRX reversal are DROP.
   - The prior Korea weights of 3 for short-term reversal, investor flows and earnings drift are withdrawn.
   - Raw Korean 12-1 momentum stays at 0.
5. The robust, implementable Korean edge is subtractive. Lottery/turnover/volatility and dilution exclusion screens add about 2-4%/yr net35 on equal-weight and selection books (R2: lottery composite +3.1%/yr, t 8.3; dilution +2.3%/yr, t 3.9) and +6-8%/yr inside momentum winners, but roughly nothing on cap-weighted books. They are BUILD NOW as screen cards, gated against the unscreened book. The attention-event screen, by contrast, does not work as a monthly filter.
6. Execution conventions are BUILD NOW:
   - fills at the KRX official close, with a t+1 bound;
   - no entry at a locked limit-up close, and limit-down exits carried forward at 2x cost;
   - stops filled at the next available price;
   - momentum entries at the close (KRX overnight +18.4%/yr vs intraday −7.9%);
   - itemised costs with a break-even pre-gate screen, and buy/hold bands;
   - eligibility tested on lagged data, and adjusted returns.
7. In risk:
   - Own-volatility scaling (R-03) extends to every momentum sleeve, including KRX.
   - Name-level stops are dropped: a 15% stop cuts KRX momentum net Sharpe from 0.04/0.28 (EW/VW) to −0.15/0.07.
   - The R-07 ladder is clarified as book-level only, non-cumulative, and re-armed at 0.5 from a reset peak. Using the all-time peak as the reference re-halts 22.8 times a year.
8. Single-index trend is a protective tool (CARD-P), never an alpha card.
   - On KOSPI, the bounded trend overlay times VT20 passes the protective scorecard indicatively in R2 (PC-1 +15.4 pp, tail ratio 0.64), so P2 need not be reopened. VT20 is the robust component; the trend evidence rests on 1997-2001.
   - US trend at 50 bp per side fails, and a US weight of 3 needs a futures-cost instrument.
9. Fundamentals become a small point-in-time composite, with gross profitability and net issuance as the core and value as a low-weight partner. US PEAD, US event drifts, sell-side levels, 13F cloning, product composites, factor-ETF rotation and valuation timing are DROP, and quality is not a hedge.
10. The main open conflicts with the macro spec are:
    - the ladder's threshold units and re-arm rule;
    - the undefined pair-share denominator;
    - R-14's class and speed;
    - the macro KEEP 3 for Korean flows and reversal;
    - the step-9 haircut wording.

    The main data gaps are OpenDART fundamentals, EDGAR Form 4, quote data and historical investor flows.

---

## 2. CONSENSUS items (EC-T-01 .. EC-T-28)

Each item lists its statement, its claim-matrix propositions (Xnn) and supporting claim IDs, key numbers (market, period, gross/net), verification status, and triage with a one-line reason.

### EC-T-01: Intraday technical rules are DROP
- **Statement:** Drop all intraday technical rules: intraday momentum, opening-range breakout, VWAP crosses, gap rules, support/resistance bounces, overnight holds, end-of-day reversal and half-hour periodicity.
- **Claims:** X17. E2-C01..C11, E2-C18, C19, C21-C24, C29; E7-C06, C07, C12.
- **Key numbers:**
  - US: SPY first-to-last half-hour momentum earned 6.67%/yr gross, and 4.46% after the spread (1993-2013), so break-even is about 1.3 bp per side. E-mini overnight drift was 1.48 bp/day, Sharpe 1.1 gross but −0.5 net (1998-2020). A QQQ 5-minute ORB breaks even at about 2.2c/share.
  - KRX: the round-trip floor is 25-46 bp (0.20% sell tax plus one tick of 5.1-25.8 bp, p1-p99). New retail traders in 2020 netted −1.2% (KCMI).
- **Verification:** CONFIRMED (E2-D1 arithmetic, E2-C26 and E2-C17 MATCH; E2-C23 traced across papers).
- **Triage:** DROP. The edges are 1-7 bp against round trips of 70-100 bp, there is no intraday order path (read-only), and there is no gate-length intraday history (fewer than 882 recorded sessions).

### EC-T-02: Daily/weekly KRX short-term reversal is DROP; monthly reversal is conditioning only
- **Statement:** The prior Korea ST-reversal weight of 3 is withdrawn. Daily and weekly reversal go to 0, and monthly reversal goes to 1 as a conditioning input only. A volume filter does not rescue it.
- **Claims:** X18. E2 position 8, E2-C13, C14, E2-D1; E7-C19; E5-C28; lab R1.
- **Key numbers:**
  - Lab R1 (KR ALL, 1996-2026), 1-week reversal L/S EW: +19.9%/yr gross (Sharpe 0.99) at 159x/yr turnover. Break-even is 12.5 bp per side (22.2 bp VW), and net35 Sharpe is −1.78.
  - E7 weekly reversal, 2015-19: +18.8% gross becomes −39.7% net.
  - R2, 1-month reversal on ALL EW deciles (1996-2026): +17.2%/yr gross (t 3.1), +2.7% net35 (t 0.5), and −6.7% net35 in 2016-26, at about 41x/yr turnover.
  - R2, value-weighted ex-microcap: +0.57%/mo gross (t 0.9), −0.68% net, negative net in every VW cut after 2005. The lab keeps Korean ST reversal at 0-1.
  - US (NMV 1963-2012): 0.37%/mo gross becomes −1.28%/mo net.
- **Verification:** CONFIRMED (E2-C14, E2-D1 MATCH; R2 consistent).
- **Triage:** DROP for KRX stocks; CONTEXT for monthly conditioning. VIX-conditioned weekly reversal on venues costing 5 bp or less goes to BACKLOG (DC-E2-09). This conflicts with macro §2.2 KEEP 3 and R-15 (section 6.2, MC-09).

### EC-T-03: Execution conventions (close fills, limit states, stop fills)
- **Statement:**
  - Decide at close t.
  - Fill at the KRX official close (closing call), and report a close t+1 fill as a conservative bound.
  - Run skip-day variants for holdings shorter than a month.
  - Never use NXT or after-hours prints.
  - Never enter at a locked limit-up close; move that entry to the t+1 open.
  - Carry an exit at a locked limit-down close to the first unlocked session at 2x cost.
  - Flag VI, circuit-breaker and overheating days.
  - Fill stops at the next available price, never at the stop.
  - Exclude locked limit-downs from reversal books.
- **Claims:** X09, X10, X23. E2-C16, C17, C20, C25, C27, E2 B1-B3, B6, B8; E7-C01, C02, C03, C12, E7 constraint 3.
- **Key numbers:**
  - US close prices carry 8.1 bp of average absolute auction pressure, and more than 63 bp in 1% of cases.
  - KRX limit-up next-open entry earns −394 bp (t+5) and −579 bp (t+20) vs the EW liquid universe (n 11,186, date-clustered t −14.6/−11.2, 2015-06..2026-09). A close entry would earn +328 bp at t+1, but it cannot be filled.
  - Locked limit-downs return −630 bp at t+1 and −1,036 bp at t+20 (n 815).
  - NXT took 9.1-10.6% of volume in 2025-26.
  - R2 limit-lock audit: 6.3% of EW-universe entries would be bought at a locked limit-up close, and 2.1% of exits sold at a locked limit-down close (1.9% / 1.4% with the F4 screen).
- **Verification:** CONFIRMED (E7-C02/C03 MATCH after the chair's benchmark fix, row 86).
- **Triage:** BUILD NOW (convention). Fills at prices no one could get are the most common way backtests mislead.

### EC-T-04: Itemised costs, card header, break-even pre-gate screen and buy/hold bands
- **Statement:**
  - Every stock-level card reports an itemised cost: commission, the date-varying sell tax, a half-tick spread floor, sqrt(Q/ADV) impact, and a capacity cap of 1-2% of 20-day ADV.
  - It reports turnover, net results at 1x and 2x cost, and the break-even per-side cost, defined as gross annual return ÷ (2 × annual one-way turnover).
  - A card is rejected before the gate if its break-even is below 2x its pre-registered cost.
  - Buy/hold bands are mandatory on monthly stock cards.
  - 35 bp is adequate only for liquid names.
- **Claims:** X04, X05, X11. E2-C12, C14, C26, C28, C30; E1-C26; E4 cost arithmetic; E5 RL-3, RL-4; E7-C11, E7 constraint 6.
- **Key numbers:**
  - A KRX tick is 5.1-25.8 bp (p1-p99), and 11% of stock-days have a tick above 20 bp.
  - The sell tax was 0.18% (2024), 0.15% (2025) and 0.20% (2026; on KOSPI, 0.05% STT plus 0.15% rural special tax).
  - Banded US reversal still loses −0.72%/mo (NMV).
  - Cost drag formula: 2 × monthly one-way turnover × 12 × cost. At 35%/mo turnover this is 2.94%/yr at 35 bp, or 4.20%/yr at 50 bp.
- **Verification:** CONFIRMED (E2-C26, E4-cost, E2-C30 MATCH; E7 desk view of 15-25 bp UNVERIFIABLE).
- **Triage:** BUILD NOW (card header plus pre-gate screen). It is cheap, and it removes doomed cards before they use up gate trials.

### EC-T-05: Eligibility, adjusted returns and regime flags
- **Statement:**
  - Universe: common shares; price ≥ ₩1,000; cap and ADV floors.
  - Exclude administrative/caution designations, SPACs, preferreds, young listings and DART rights/merger windows.
  - Evaluate eligibility on data up to t−1.
  - Use corporate-action-adjusted returns, and dividends where available.
  - Flag the Korean regime breaks: short-sale bans, Value-up, CB rules, insider pre-disclosure, treasury-share cancellation, dividend reform and the tax path.
  - Event cards that depend on a post-reform regime are INSUFFICIENT DATA until about 2028.
- **Claims:** X12, X15. E5 RL-3; E7 constraint 4, E7-C08, C16, C27; E2 B4; E6 DC0/DC5, E6 position 6, E6-C16..C24; E4-C30.
- **Key numbers:**
  - R2: unadjusted closes fabricate a −136%/yr high-turnover momentum spread, against +17.1%/yr on adjusted prices.
  - Short-sale bans ran 1 Oct 2008-31 May 2009, 11 Aug-9 Nov 2011, 16 Mar 2020 (partial lift 3 May 2021) and 6 Nov 2023-30 Mar 2025.
  - KOSPI fell −3.00% on 31 Mar 2025 and −10.0% in 2024.
  - The chair's own first-pass event study used same-day eligibility and produced a +27.7%/yr EW benchmark. With eligibility lagged one day the benchmark is +0.5%/yr.
- **Verification:** CONFIRMED (E7-C08 MATCH; E6-C22 minor MISMATCH −2.93 → −3.00%; chair error traced, row 86).
- **Triage:** BUILD NOW (screens and flags); CONTEXT for the regime-dependent event cards.

### EC-T-06: Long-only realism, pre-registered benchmarks and the pair denominator
- **Statement:**
  - Every Korea stock card is gated long-only. Long-short spreads are reported only as overpricing diagnostics, because the short leg cannot be implemented in ban years or by a retail account.
  - Benchmarks are pre-registered per card: EW, CW, CW ex-pair, and concentration-capped CW.
  - The Samsung + SK hynix pair-share series uses one pre-registered denominator.
- **Claims:** X06, X07, X08. E7-C09, C10, C22, C23, C24, C26; E4-C25, E4 sec.6; E5 RL-11; E1-C21.
- **Key numbers:**
  - H1-2026 (30 Dec 2025-22 Jun 2026), KOSPI common shares: CW +117.1% vs EW +3.4%; median −8.7%; 64.9% of names fell; CW ex-pair +41.7%.
  - 2026 YTD to 29 Sep: CW +63.6% vs median −8.9%. Only 6.4% of 829 names beat CW, and the pair contributed +50.9 pp.
  - Pair share on all lines: 26.9% at end-2023, 34.0% at end-2025, a peak of 57.1% on 25 Jun 2026, and 50.8% on 29 Sep. On common shares only it is 52.6%; with the Samsung preferred in the numerator, 53.7%.
  - The pair took 42.8% of 2026 KOSPI traded value.
  - Lab R1: long-only top quintiles are within noise of the universe, because the spreads come from the short leg.
- **Verification:** CONFIRMED (E7-C22/C23/C24 MATCH; E4-sec6 TRACED, since E4's universe includes preferred lines).
- **Triage:** BUILD NOW. Without pre-registered benchmarks, Korean and US verdicts are benchmark artefacts.

### EC-T-07: Own-volatility scaling (R-03) on every momentum sleeve in every market, including KRX
- **Statement:** R-03 (σ126, 12% target, cap 1.0) applies to every momentum-family sleeve. Value, quality and reversal get no vol scaling, consistent with R-05.
- **Claims:** X24. E5-C04, C05, E5 F8; E1-C13, C16; E4-C28; E7 rank 3.
- **Key numbers:**
  - US French Mom (1949-2017/03): Sharpe 0.62 → 0.77; MDD −57.6% → −28.5%; Mar-May 2009 −49.3% → −24.4%.
  - KR top-500 WML net35 (2000-2026), with a 1997 warm-up:
    - EW: Sharpe 0.07 → 0.25-0.30 and MDD −81.8% → −55%, against a same-exposure static book (0.56x) at 0.07 and −59.4%.
    - VW: Sharpe 0.30 → 0.38-0.41 and MDD −79.8% → −40% to −42%, against a static book (0.39x) at −43.0%.
  - 23 Jun-30 Jul 2026 window: scaled VW −10.3% vs static −22.6%.
  - Weights on 23 Jun 2026: 0.34 (EW) and 0.20 (VW).
  - Scaling hurts reversal: KR STR EW net35 goes from −0.29 to −0.59.
- **R2 final (12-1 L/S, ALL quintiles, 1996-2026):**
  - Net Sharpe rises with vol scaling: EW 0.20 → 0.27, VW 0.25 → 0.31.
  - Vol scaling had already cut exposure before July 2026 (weights 0.55 EW / 0.27 VW on 22 Jun). In the crash window the scaled VW sleeve lost −10.5% vs −22.9% for a static book at the same exposure.
  - In 2016-26, however, scaling lowered net Sharpe (EW −0.20 → −0.24; VW 0.32 → 0.23), because it cut exposure during the 2026 melt-up.
- **Verification:** CONFIRMED (E5-C04, E5-mom MATCH; R2 reproduces E5's scaling weights exactly). The chair's first pass used a too-short warm-up; this was corrected in c05b.
- **Triage:** BUILD NOW. This is already decided; the scope now explicitly includes KRX sleeves. It is a risk control, not a source of return: it does not rescue Korean 12-1 momentum.

### EC-T-08: Korean raw 12-1 momentum weight is 0
- **Statement:** Raw 12-1 momentum has no net edge in Korea. Value-weighted Korean momentum after 2016 is a two-stock concentration artefact.
- **Claims:** X25. E5 F6, E5-C18, C19; E7 weights; E1 F3.
- **Key numbers:**
  - Top-500 D10-D1, 2000-2026: EW gross Sharpe 0.26-0.30 and net35 0.04-0.07, with 2016-26 net35 at −0.13. VW net35 is 0.28-0.30, but a 5% name cap cuts 2016-26 net to 0.02.
  - July 2026 WML: −28.0% (EW) and −30.0% (VW). The pair made up 85% of the VW winner decile in July 2026.
  - Lab R1: long-only excess is −1.3% EW (t −0.6).
- **Verification:** CONFIRMED for the decision. E5's printed levels are a MISMATCH (rows 55, 67).
- **Triage:** DROP (raw 12-1, Korea). The macro R-15 value of 0 stands.

### EC-T-09: No name-level stops; signal exits; statistical review triggers
- **Statement:**
  - Name-level stop-losses destroy Sharpe on KRX sleeves, because the Kaminski-Lo condition fails.
  - Trend cards use their own signal exit, not a separate stop layer.
  - Pod-style hard stops are a manager-selection device. Replace them with statistical review triggers and never auto-liquidate.
- **Claims:** X37, X38. E5-C07, C08, C09, C13, C14, E5 RL-8; E3-C28; E2-C20.
- **Key numbers:**
  - 15% stop (close trigger, exit at next close, 70 bp per stopped round trip), R2, top-500 WML 2000-26:
    - EW: gross 0.26 → 0.17, net35 0.04 → −0.15.
    - VW: gross 0.44 → 0.30, net35 0.28 → 0.07.
  - ALL quintiles EW: net35 0.20 → −0.20. A 10% stop is worse.
  - Kaminski-Lo test for KR WML EW: monthly AR(1) −0.009 vs monthly Sharpe 0.117, so the condition fails.
  - Brownian check: a book with 8% vol and Sharpe 0.5 hits −8% in 38% of years.
- **Verification:** CONFIRMED (E5-C07, E5-KL, E5-C14, E5-C13 MATCH; the chair and R2 agree).
- **Triage:** DROP name-level stops on KRX. BUILD NOW the review triggers (forward drawdown beyond the 95th percentile of simulation, or 12-month Sharpe below its 90% CI) and the signal-exit convention. A US HZZ-style stop goes to BACKLOG as its own CARD-O.

### EC-T-10: Drawdown-ladder rules: scope, re-arm and step arithmetic
- **Statement:**
  - Apply R-07's ladder to total book NAV after the book volatility target, never per sleeve.
  - Steps are non-cumulative.
  - After a HALT, re-arm at 0.5 with the reference peak reset, never against the all-time high-water mark. Return to 1.0 after a gain of +0.5σ or 60 sessions without a new −1σ breach.
  - Threshold units are disputed (EX-T-11).
- **Claims:** X39. E5-C14, C15, C16, C17, E5 RL-7.
- **Key numbers (KOSPI CW, 2000-26, 35 bp, re-arm 0.5 with reset):**
  - Sharpe 0.42 → 0.40; MDD −55.8% → −41.3%; 0.69 halts/yr.
  - July 2026: −38.6% → −21.3%. H1-2026: +101.1% → +49.0%.
  - Below full exposure on 61% of days.
  - With the all-time-peak reference: 22.8 halts/yr and Sharpe −1.65.
  - Per-sleeve ladder on vol-scaled VW WML: 0.38 → 0.16.
  - VT20 plus ladder: 0.40 → 0.35, with MDD −47.4% → −34.8%.
  - Step arithmetic is mixed. Cumulative steps helped KOSPI in variant 1 (0.39/−49.3% vs non-cumulative 0.34/−53.6%, 26 halts), but E5 reports they wrecked SPY (0.41 → 0.02; 2009 rebound +35.0% → +2.1%). The chair did not re-run SPY.
- **Verification:** CONFIRMED (E5-C15, C16, C17 MATCH).
- **Triage:** BUILD NOW for scope, re-arm with reset, non-cumulative steps, and no per-sleeve ladders. These clarify R-07's open points; they do not overturn it.

### EC-T-11: Korea caps and neutral construction
- **Statement:**
  - Selection sleeves: single name ≤ 5% of NAV; VW legs name-capped at 5% of the leg.
  - Sector ≤ benchmark +10 pp (long-only active ±5 pp).
  - Market and ETF books: R-07's pair cap of 0.35 applies on look-through when the pair share exceeds 0.45. Semis ≤ 0.50.
  - Neutral construction for any long-short diagnostic.
- **Claims:** X40. E5-C11, C19, C26, E5 RL-1, RL-2; E7 constraint 8; E1-C21; E4 F1.
- **Key numbers:**
  - VW WML with a 5% cap: 2016-26 net35 Sharpe 0.30 → 0.02; May 2026 +71.5% → +9.0%; July 2026 −30.0% → −32.5% (chair).
  - Pair cap of 0.35 on KOSPI CW: it bound on 98 sessions from 7 May 2026. Costs were −15.0 pp in the melt-up, +4.6 pp in the crash, −1.8 pp in the rebound and −2.2 pp for 2026 YTD.
  - US analogue: MTUM had 53.2% in IT (30 Jun 2026).
- **Verification:** CONFIRMED (E5-C19, E5-xep MATCH; the cap-cost figures are the chair's own, c07).
- **Triage:** BUILD NOW. The caps cost little over a cycle and turn a pair bet into a factor bet.

### EC-T-12: Lottery/turnover/volatility exclusion screens are the robust Korean edge
- **Statement:** Excluding the most lottery-like names (high turnover, high volatility, high MAX) from equal-weight, small-cap and momentum books adds a small, steady return after costs. On cap-weighted books it adds about nothing. Attention chasing also loses over 5-20 days in every sub-period. That event evidence is handled as an entry-day execution exclusion (EC-T-03, RX-03), not as a monthly screen (EX-T-04).
- **Claims:** X19, X21. Lab R1 headline 3; E7 constraint 5, E7-C02, C04, C06; E1-C21.
- **Key numbers (R2, 366 months 1996-03..2026-09, long-only, monthly; both books net of their own turnover):**
  - EW ALL book:
    - lottery composite (F4) +3.1%/yr net35 (IR 1.53, t 8.3; +2.8% at 70 bp; 90% of years positive);
    - high-turnover exclusion +4.3% (t 6.6);
    - high-vol +3.6% (t 5.7);
    - MAX +2.4% (t 5.0).
  - Capped VW book: F4 +0.85% (t 3.9). Top-200 capped VW: +0.49% (t 2.3).
  - Momentum top quintile: high-turnover exclusion +7.8% (t 6.2); F4 +6.1% (t 7.5).
  - Indicative gate for B1/F4 and B4/F4: 7 of 8 steps pass, so both are REVISE. Only the pooled deflated Sharpe over 176 trials misses (0.94 and 0.56, below 0.95).
  - Chair's attention+MAX book (2015-07..2026-08): +2.06%/yr net35 (t 2.64), +1.34% at 70 bp, 83% of years positive.
  - Event evidence: limit-up next-open −579 bp at t+20; volume spike −93 bp; +50% run-up −95 bp.
- **R2 final verdicts:**
  - B1 (EW universe): BUILD candidate as a filter. F4 at a 10% cut has the best IR and the smallest exclusion. It is positive in all three sub-periods (1996-2005 +4.3%, 2006-15 +2.8%, 2016-26 +2.2%).
  - B4 (momentum winners): BUILD as a construction rule for any long-only momentum or small-cap sleeve.
  - B2 (capped VW): REVISE; carry it as a hygiene filter, not an alpha claim.
  - B3 (top 200): REJECT.
  - The best of all 176 trials has a deflated Sharpe of 0.979 on the pooled variance.
  - Limit-lock audit: 6.3% of B1 entries would be bought at a locked limit-up close (1.9% with F4).
- **Verification:** CONFIRMED (R2 final; E7 events MATCH; lab R1).
- **Triage:** BUILD NOW, as a screen card (F4 lottery composite at a 10% cut; F1 when a larger mean matters more than tracking error), gated against the unscreened book on the same days. It needs almost no turnover and survives 70 bp. Any Korean EW, small-cap or momentum sleeve should inherit it as a construction rule once it passes. It does not apply to top-200 or cap-weighted books.

### EC-T-13: Korean dilution / net-issuance exclusion screen
- **Statement:** Excluding heavy issuers pays after costs: rights offerings, third-party allotments and CB/BW conversions, measured from share counts. The effect is decaying.
- **Claims:** X45. E6-C19, E6 #6/#7, DC3; E4 DC-1, E4 ranked table #2.
- **Key numbers:**
  - Chair: ISS = Δln(marcap) − Δcumulative log price over 252 sessions, EW quintiles, 2001-2026, net35. Q5 earns −13.4%/yr (t −10.3). The universe ex-Q5 earns +3.0%/yr (t 9.2), positive in 85% of years, and +1.5% in 2016-26 (t 3.3).
  - Issuance events (new-share listings ≥ 3%, n 10,855, 2005-2025): 12-month BHAR −25.3% size-matched (−21.6% vs EW). By period: 2005-14 −34.4%, 2015-24 −17.6%, Dec-2024 onward −5.1% (n 314).
  - R2 F6 on the EW book: +2.3%/yr (t 3.9), unchanged at 70 bp. On capped VW books: +0.3% to +0.7%, not significant.
- **Verification:** CONFIRMED (E4-DC1, E6-C19, E6-#6 TRACED-NOTE with supporting results).
- **Triage:** BUILD NOW, as a screen on EW and selection books gated against the unscreened book. Pre-register the decay check (post-2015 sub-period).

### EC-T-14: Point-in-time event and fundamental layer, forward archives, and a small composite core
- **Statement:**
  - Key every fundamental and event input to its public timestamp. EDGAR acceptance at or before 15:30 ET is usable at close d, otherwise at d+1. OpenDART `rcept_dt` is date-only, so a Korean event is usable from the close of rcept_dt + 1 trading day.
  - Start forward archives now: consensus, opinions, flows and quotes.
  - Composite core: gross profitability (GP/A) and net issuance, with value as a low-weight partner.
- **Claims:** X14, X43, X44. E4-C17, C22, C24, C29, E4 DC-9; E6-C27; E7 DC9; E1 F2, gaps; E4-C19, C20, C21; E1-C17, C18, C19.
- **Key numbers:**
  - EDGAR acceptance stamps are to the second (e.g. 06:01:36). OpenDART's list API returns rcept_dt as a date only, with about 20,000 calls/day. DART fnlttSinglAcntAll data start in 2015. The KIND time column returned HTTP 403.
  - Power: IR 0.3 needs about 18 years at one-sided p ≤ 0.10. A DART-only history detects only IR ≥ 0.41-0.48.
  - US HML Sharpe: 0.60 (1963-2006) vs −0.17 (2007-2017/03). The 50/50 HML+UMD mix: −0.13 in 2007-17.
- **Verification:** CONFIRMED (E6-C27, E4-power, E4-C19/C21 MATCH; KIND UNVERIFIABLE).
- **Triage:** BUILD NOW for the PIT layer and archives. BACKLOG for the OpenDART composite card, which needs the data pull. Expect REVISE or INSUFFICIENT DATA on DART-only history.

### EC-T-15: Single-index trend is CARD-P, never CARD-O; KOSPI trend × VT20 goes to FORWARD-SIM
- **Statement:** Single-index trend protects in slow bears and loses in long bull runs. It was fully long into the Jun-Jul 2026 KOSPI crash, where VT20 protected. On the KOSPI ETF line, trend × VT20 is the credible equity protective card.
- **Claims:** X30, X31. E3-C03, C04, C05, C19, C20, C21, C22; E1-C06, E1 T1.
- **Key numbers:**
  - KOSPI 1996-2026 at 3-5 bp, ensemble long/flat vs static S (chair): Sharpe 0.58 vs 0.40; MDD −34.5% vs −45.2%.
  - The ensemble lost in 2009-19 (0.18 vs 0.47), and its 2013-26 PC-1 is −3.4 pp.
  - 22 Jun-30 Jul 2026 crash: ensemble −31.3% vs −38.6% (exposure 1.00 on the first crash day); VT20 −12.3%; ensemble × VT20 −9.8%.
  - R2 scorecard (KRX ETF, 3 bp):
    - ensemble vote-share sleeve: PASS (PC-1 +8.9 pp, tail ratio 0.77, PC-5 0.60);
    - unbounded ensemble × VT20: REVISE (PC-1 +11.3 pp, tail 0.55, 11/13 episodes, PC-5 0.57);
    - clip[0.5,1](ensemble) × VT20: PASS (PC-1 +15.4 pp, tail 0.64, PC-5 0.63);
    - 12M sign monthly (the R-14 rule): INSUFFICIENT DATA (PC-1 +4.7 pp).
  - SPY 200-day long/flat (1999-2021): Sharpe 0.34 vs 0.37; MDD −30.0% vs −56.5% (S −43.7%).
  - R2 final start-date sweep (KOSPI, 3 bp):
    - VT20 alone passes from every start from 1996 to 2006, with PC-1 between +4.4 and +11.6 pp.
    - The trend rules' advantage rests on 1997-2001. The ensemble is PASS from 1996-09 and 1997, REVISE from 1999, INSUFFICIENT DATA from 2001 and 2006, and REJECT from 2011 and 2016 (PC-1 −3.5 and −2.9 pp). The trend × VT20 product is REJECT from 2011.
    - Trend protected in slow bears (GFC, 2020, 2022) but not in the fast 2026 crashes: the ensemble's benefit vs S was −9.9 pp in March 2026 and −7.5 pp in July 2026.
- **Verification:** CONFIRMED for the class rule (E3-a/b/c also CONFIRMED by R2). QUALIFIED for the levels: the chair's values are 0.02-0.04 Sharpe below E3's (E3-C19, C20, C21 rows). The robustness note is a TRACED-NOTE (row E3-C20(robust)).
- **Triage:** CONTEXT for the class rule. FORWARD-SIM for the KOSPI protective cell: pre-register floored clip[0.5,1](ensemble) × VT20 as primary (P2- and R-06-compliant; R2 has not yet evaluated its plateau) and the unbounded sleeve as the comparison. VT20 (R-06) is the protective workhorse. Trend adds slow-bear protection that may not recur, so its own protective weight is 1; the product is weight 2.

### EC-T-16: Shiller month-average data rule
- **Statement:** Shiller's monthly-average prices inflate timing backtests. Use month-end data, or a one-month skip.
- **Claims:** X16. E3-C26; E1-C06 lag control; US lab §4.
- **Key numbers:**
  - SPY 1998-2021 monthly AC(1): 0.057 with month-end prices vs 0.206 with month averages.
  - Shiller 1872-2026: 12-month L/S Sharpe 0.51 → 0.30 with a skip; 10-month SMA 0.76 → 0.59.
  - R2: SPY 1999-2014 rule return/vol 0.62 on month-end prices vs 1.04 on Shiller averages.
  - R2 final rules of thumb:
    - Averaging inflates Sharpe by +0.10-0.19 for the 10-month SMA and +0.23-0.25 for the 12-month sign.
    - Use the LAG1 number for the SMA, and LAG1 minus about 0.13 for 12-month momentum.
    - Treat averaged drawdowns as understated by up to 5 pp.
- **Verification:** CONFIRMED (E3-C26 MATCH; R2 E3-e and E1-a CONFIRMED).
- **Triage:** BUILD NOW (data rule).

### EC-T-17: Valuation timing is DROP; valuation stays as CONTEXT
- **Statement:** CAPE, forward P/E and the Fed model explain long horizons in sample but fail as one-year timing signals, and failed out of sample after 1990.
- **Claims:** X55. E1-C07, C08, C09, C11, C18.
- **Key numbers:**
  - Shiller CAPE R²: 0.05 / 0.16 / 0.29 at 1 / 5 / 10 years. Post-1990 10-year R² is 0.86 in sample but −0.56 (fixed fit) or −0.25 (expanding fit) out of sample, with correlation +0.93.
  - The June 2013 forecast was 2.9%/yr real; the realised return was 9.5%.
  - CAPE > 30 (102 months to Sep 2023): forward one-year return +3.0%, positive 58% of the time, vs +6.5% and 65% unconditionally. The S&P rose +208% from Sep 2017 to Sep 2026.
  - Forward P/E one-year R² is 5-8% (JPM GTM).
- **Verification:** CONFIRMED (E1-C08, C11 MATCH).
- **Triage:** DROP as timing; CONTEXT as a display that shows its residual drift.

### EC-T-18: Product composites, factor-ETF rotation, ML, sell-side levels and 13F cloning are DROP
- **Statement:**
  - DROP: CANSLIM/IBD, SEPA/VCP, factor-ETF rotation, ML or alternative-data alpha, recommendation levels and target upside, LTG levels, and 13F cloning.
  - BACKLOG: estimate revisions, which need a forward archive first.
  - Short interest is used only as a filter on longs.
  - Aggregate short interest is CONTEXT.
- **Claims:** X49, X54. E4-C05..C10, C13..C16, C26, C27; E1-C20, C23, C24, E1 X1/X2; E6-C26; E5-C23, C26.
- **Key numbers:**
  - FFTY returned 3.52%/yr from Apr 2015 vs 13-14% for the S&P. GURU lagged by about 3 pp/yr over 10 years.
  - AIEQ: 4.18% vs SPY 12.65% over 5 years.
  - iShares 10-year excess return vs IVV: MTUM +2.1, QUAL −1.0, VLUE −0.0, USMV −5.9 pp/yr.
  - 2000-01 recommendation levels: the top group returned −7.06%/yr vs +13.44% for the bottom group.
- **Verification:** CONFIRMED (E4-C26 MATCH; E1-C20/C21 minor MISMATCH on the IT weight only).
- **Triage:** DROP. BACKLOG for the revisions archive.

### EC-T-19: Long-only quality is not a crash hedge (US quality 3 → 2)
- **Statement:** Quality is a composite member, not a hedge, and must not be counted as one in any risk budget.
- **Claims:** X46. E4-C18; E1-C19, C20.
- **Key numbers:**
  - QUAL −34.1% vs S&P −33.9% (19 Feb-23 Mar 2020); QUAL beta 0.99.
  - MSCI USA Quality −20.3% vs −18.1% in 2022.
- **Verification:** QUALIFIED. These are T3 figures from E4's own check and were not re-fetched; they are accepted on cross-paper consistency.
- **Triage:** CONTEXT, plus a weight change (section 5).

### EC-T-20: US PEAD standalone card is DROP (US earnings drift 2 → 1)
- **Claims:** X48. E4-C01..C04.
- **Key numbers:**
  - NMV: PEAD earns 0.72%/mo gross and 0.26%/mo net (t 1.60), at 35%/mo turnover.
  - Large-cap drift has been about 0 since 2006.
  - SUE net Sharpe was 0.55 vs UMD 0.33 (1975-2012).
- **Verification:** CONFIRMED (E4-C04, C02 MATCH).
- **Triage:** DROP standalone. Earnings drift survives only as a confirmation input.

### EC-T-21: US event drifts are DROP as cards and stay as flags
- **Statement:** DROP as cards: S&P inclusion, buybacks, SEOs, dividend initiation/omission and merger arbitrage.
- **Claims:** X52. E6-C03, C06, C07, C09..C14; E6-C08 (non-US buybacks, Korea BACKLOG).
- **Key numbers:**
  - The S&P 500 inclusion effect fell from 7.3% (1990s) to 0.8%, not significant (2010s).
  - Buyback and SEO drifts disappeared over 2003-12. Repeat-buyback drift fell from 2.51% to 0.89%.
- **Verification:** CONFIRMED (E6-C14 MATCH).
- **Triage:** DROP as cards; CONTEXT as calendar flags.

### EC-T-22: Event Calendar and Risk Screen layer
- **Statement:** One layer that can only exclude names or scale exposure to at most 1.0. It covers lock-ups, index effective dates, pinned cash targets, Korean insider pre-disclosed sales, record dates and short-sale regimes. Each screen is gated against the unscreened card on the same days.
- **Claims:** X53. E6 architecture, E6-C05, C15, C20, C23, C24, C28; E4.
- **Key numbers:**
  - Lock-up expiry: −0.97% over [−1, +1] (2005-06).
  - KOSPI 200 additions earned +2.24% before the effective date (1995-2008), but the 2012 pre-reconstitution L/S lost −2.53%.
  - Value-up plans: +1.5% on day 0, about +1% retained.
- **Verification:** CONFIRMED (E6-C18 MATCH; design item).
- **Triage:** BUILD NOW (convention). It is consistent with P1/P2, because it never adds exposure.

### EC-T-23: Korean investor flows: weight 3 → 1; log flows now; no direction rule
- **Statement:** Foreign flows are positive-feedback, with contemporaneous and permanent price impact. The aggregate sign broke in 2026.
- **Claims:** X56. E7-C13, C14; E6 conflicts (regime dummies).
- **Key numbers:**
  - Foreigners sold ₩148.3tn net in H1 2026 while KOSPI rose about 101%.
  - They bought +₩231.2bn on the −12.06% day (4 Mar 2026).
  - Flow autocorrelation is 0.43, with impact 0.119 (t 11.9), permanent (Richards).
- **Verification:** CONFIRMED (E7-C14 MATCH).
- **Triage:** BACKLOG, logging final KIS flows at t−1 from now. This conflicts with macro §2.2 KEEP 3 (MC-08).

### EC-T-24: Crowding is display-only; R-08 is not factor-crash protection
- **Claims:** X41 (display), X42. E5-C10, C12, C20..C23, E5 F7; E1-C10, C12, C13, C28; E7-C29.
- **Key numbers:**
  - VIX at factor-crash onsets ranged from 12.9 to 25.8 (all 19 printed VIX closes match).
  - GS's record crowding reading (Nov 2023) was followed by further outperformance.
  - Korea on 27 May 2026: margin loans ₩36.25tn and VKOSPI 70.83.
- **Verification:** CONFIRMED (E4/E5-VIX, E5-C20, E7-C29 MATCH).
- **Triage:** CONTEXT. A crowding multiplier is contested (EX-T-07).

### EC-T-25: Stress-window table and worst five-week relative loss on every stock-level card
- **Claims:** X28. E1-C13, C14, C28; E5-C01, C27, E5 RL-10.
- **Key numbers:**
  - MTUM −18.0% vs SPY −2.0% (22 Jun-29 Jul 2026).
  - KR WML July 2026: −28.0% (EW) and −30.0% (VW).
  - French Mom April 2009: −34.6% (monthly file).
- **Verification:** CONFIRMED (E1-C14, E5-windows MATCH).
- **Triage:** BUILD NOW (reporting).

### EC-T-26: Momentum entries fill at the close
- **Claims:** X13. E2-C06, E2 B7.
- **Key numbers:**
  - US: momentum earns 0.98%/mo overnight (t 3.84) vs −0.02% intraday.
  - KRX top-500 EW 12-1 D10-D1, 2002-2026 (chair c06): +18.4%/yr overnight (t 8.7) vs −7.9%/yr intraday (t −1.8). In 2015-26: +26.0% vs −21.9%.
- **Verification:** CONFIRMED, with a new KRX test (E2-C06 TRACED-NOTE).
- **Triage:** BUILD NOW (convention). A next-open fill gives up the overnight leg, which is where Korean momentum is earned.

### EC-T-27: Korean technical stock-selection rules are DROP
- **Statement:** DROP for KRX stocks: golden/dead crosses, MA alignment (정배열), price-above-MA200 selection, limit-up chasing, volume-spike buying, size tilts and RSI/%B.
- **Claims:** X22. E7-C05, C21, E7 DROP list; lab R1.
- **Key numbers:**
  - Crosses: 17 bp or less, t about 0.
  - 정배열 state: −5.3% gross / −10.9% net (2015-19); −48.7% in the crash vs −27.1%.
  - Size L/S: −26.9% in 2025 and −26.5% in 2026.
  - RSI14 and %B correlate 0.92-0.95 with 1-month reversal.
- **Verification:** CONFIRMED (lab R1; E7 numbers not re-run individually).
- **Triage:** DROP.

### EC-T-28: Governance: haircut published priors, respect power, pre-register
- **Statement:**
  - Headline backtests from banks and asset managers overstate live results, so haircut them before they become priors.
  - Single-market stock and trend cards cannot detect realistic Sharpe ratios, so expect INSUFFICIENT DATA or REVISE.
  - Pre-register 4-5 features at most.
  - Count MA and TSMOM variants as one family.
- **Claims:** X01, X03. E1-C01, C05, C15, C22, C25; E3-C06, C15, C16, C27; E4 power table, E4-C23; E2-C29, E2 KQ5; E5-C24; E6 (882-session rule).
- **Key numbers:**
  - Power: t ≈ IR × √years. IR 0.3 needs about 18 years.
  - R2 final gate simulation (KOSPI-bootstrap innovations, 15% vol):
    - At true Sharpe 0, the joint pass rate for steps 2+3+5+8 is 0.5% at 10 years, but step 8 alone passes 24-31% of zero-Sharpe strategies over 10 years.
    - A true Sharpe of 0.5 passes step 2 half the time after 10.5 years (80% after 25.7). With 9 counted trials, step 3 needs 39.5 years.
    - An IR of 0.3 against a 0.4-Sharpe benchmark passes step 5 half the time after about 18 years, and 80% of the time only after about 50.
    - Ten-session bootstrap blocks are too short for index-like returns: step 2 falsely passes 6.9% of the time instead of 5%, and step 5 12.8% instead of 10%.
  - E4's "IR 0.3 needs ~18 years" is therefore the 50%-power horizon (R2 rates it PARTLY).
  - 85.59% of US large-cap funds lag over 10 years (SPIVA). 64% of 447 anomalies are insignificant (HXZ). Post-publication decay is about 50%.
  - AQMIX: 5.44%/yr over 10 years vs T-bills 2.42%, at 9.96% vol, so Sharpe ≈ 0.30.
- **Verification:** CONFIRMED (E4-power, E1-C05 MATCH).
- **Triage:** CONTEXT (governance). The haircut arithmetic is contested (EX-T-12).

---

## 3. CONTESTED items (EX-T-01 .. EX-T-14)

### EX-T-01: Trend as a signal sleeve that can go to 0, or as an overlay bounded to [0.5, 1.0]?
- **Positions:**
  - E3 treats trend as a signal family that may reach 0, and says bounding to [0.5, 1.0] halves protection (PC-1 +8.1 vs +17.3 pp).
  - The macro spec (P2) treats trend as an overlay bounded to [0.5, 1.0].
  - The chair and R2 recomputed.
- **Claims:** X32, X33. E3 §6 F3, E3-C23.
- **Key numbers (KOSPI, 3 bp):**
  - Chair: floor applied after VT gives +9.2 pp; floor before VT gives +15.0 pp; long/flat gives +12.0 pp.
  - R2: clip[0.5,1] × VT20 PASS (PC-1 +15.4, tail 0.64, PC-5 0.63); 0.5+0.5x × VT20 PASS (+13.0, 0.65, 0.67); unbounded × VT20 REVISE (+11.3, 0.55, PC-5 0.57).
  - Bounded trend without VT fails PC-2 (tail 0.91-0.92 vs 0.77 unbounded).
  - Absolute MDD worsens from −27.7% to −29.4% (clip) or −36.2% (linear).
  - R2 final: the plain ensemble's MDD is −34.1% as a sleeve vs −39.2% / −44.8% floored. In the 1997-98 crash the sleeve lost −6.9% vs −39.2% / −40.4% floored.
- **Verification:** E3's halving claim (+17.3 → +8.1 pp) is REFUTED; R2 rates E3-d NOT REPRODUCED (ER-T-02). E3's underlying point is upheld by R2: the floor gives back absolute protection in slow bears, and a plain floored trend fails PC-2. With VT20 on top, the floored trend passes every evaluated check.
- **Triage:** FORWARD-SIM both cells, with floored trend × VT20 as primary. P2 stands, because the floored trend × VT20 cell "fits both P2 and the protective class" (R2).
- **Residual dispute:** E3 keeps the 0-allowed sleeve as a pre-registered comparison and asks the coordinator to classify trend formally as signal or overlay (MC-07). The chair records that the classification matters only for slow bears and only where no vol target sits on top.

### EX-T-02: R-14 class and speed
- **Positions:**
  - The panel (E3, E1): single-index trend is CARD-P. Diversified futures trend should be re-registered (≥ 25 markets, fixed multi-speed ensemble) with a diversifier claim measured against cash plus portfolio uplift. Speed should depend on the venue.
  - Macro R-14: 12-1 sign, monthly, CARD-O against an EW long-only basket, exempt from the overlay.
- **Claims:** X33, X35. E3-C01..C03, C07, C08, C09, C10..C14, C17, C27, C29, C30; E1-C01..C05.
- **Key numbers:**
  - KOSPI at 3 bp: the 12M-sign sleeve's PC-1 is +4.7 pp, INSUFFICIENT DATA (REVISE if sufficient). The multi-speed vote-share sleeve's PC-1 is +8.9 pp, PASS.
  - SPY at 50 bp: the multi-speed ensemble's PC-1 is −10.7 pp (REJECT). The 12M sign's PC-1 is +11.0 pp, but only 2 of 5 episodes are positive, so it is INSUFFICIENT DATA and REJECT if sufficient.
  - The Barclay Systematic index returned 6.98%/yr in 2000-08 (9/9 years positive) and −0.30% in 2009-18 (3/10 positive).
- **Verification:** CONFIRMED (E3-C09 MATCH; R2).
- **Triage:** FORWARD-SIM a venue-dependent speed cell beside R-14's 12-1. BACKLOG the B3 re-registration, which needs gate-class approval. R-14 stands as decided (MC-06).

### EX-T-03: US single-index trend protection weight 3 vs 50 bp costs
- **Positions:**
  - E3 gives weight 3; its checks ran at 5 bp.
  - The chair and E5 point out that QUANTGEN's US equity cost is 50 bp per side through KIS.
- **Claims:** X33, X34. E3 §6 D table, E3-C19.
- **Key numbers (R2, SPY 1999-2021):**
  - At 50 bp, every rule fails:
    - The ensemble, VT15 and their product REJECT. All multi-speed sleeves and overlays have PC-1 between −10.7 and +1.3 pp.
    - SMA200 and the 12M sign are INSUFFICIENT DATA, and would be REJECT if sufficient.
    - Trend turnover of 7.3-11.9 units a year costs 3.7-6.0% a year.
  - Futures at 5 bp: INSUFFICIENT DATA (inconclusive), with PC-1 +11 to +15 pp; 53-56% of the benefit comes from the GFC.
- **Verification:** QUALIFIED (E3-C19(cost) TRACED-NOTE).
- **Triage:** Weight 3 → 2 (protective), pending a decision on the instrument book (P10: costs are declared before the run). Weight 3 is restored only with an instrument costing 5 bp or less. BACKLOG.

### EX-T-04: Attention-fade as a standalone card (E7 rank 1, weight 3) or not at all as a monthly screen?
- **Positions:**
  - E7: standalone exclusion card, weight 3.
  - Chair and lab: the data reject it as a monthly screen.
  - E2 (reviewer): the event results are real, but locked limit days are already handled as an execution exclusion.
- **Claims:** X20. E7 §9 rank 1 (K-AF).
- **Key numbers (R2 final):**
  - F5 on the EW book: +1.40%/yr net35 (IR 0.49), but −0.08% at 70 bp, the weakest of the eight filters.
  - Negative on capped VW (−0.35%) and top-200 (−0.54%). On the momentum quintile: +1.70% (IR 0.29).
  - Adding F5 to the composite (F8 = F4|F5|F6) lowers the IR from 1.53 to 0.67.
  - The lab's reasons: the events matter over 5-20 days, and a month-end screen with 20 sessions of memory flags about 23% of names and raises turnover.
  - The chair's attention+MAX book earned +2.06% (t 2.64), with MAX carrying most of it.
- **Verification:** QUALIFIED. The event studies are CONFIRMED; the monthly screen fails.
- **Triage:** DROP as a standalone or composite monthly screen. Attention and limit events stay as an execution exclusion at entry (RX-03): no new long within 5 sessions of a locked limit-up or volume spike. That is a BUILD NOW convention, not a card. A daily-entry K-AF card for sleeves that trade daily goes to BACKLOG. Dissent recorded: E7 keeps rank 1 for short-horizon use.

### EX-T-05: Which Korean momentum variant earns weight 1?
- **Positions:**
  - E7: low-turnover winners (+3.1%/yr net).
  - E5: residual, 12-7 or sector-neutral momentum, replacing 0 only if the 2016-26 90% CI excludes 0.
  - Macro R-15 already gives 12-7/residual a weight of 1 (UNVERIFIED).
- **Claims:** X26. E7-C17, C18; E5-C25, E5 DC-03.
- **Key numbers (R2 final):**
  - E7's construction reproduces at +2.9% (t 0.75); the lab verdict is CONFIRMED. In the ALL universe over E7's 2015-24 window it is −0.1%. The chair gets +2.3%.
  - Over the full sample (ALL, EW, 1996-2026), long-only winners vs the EW universe net35 are:
    - low turnover: +9.7%/yr (t 2.8);
    - mid turnover: +6.3% (t 2.7);
    - high turnover: −11.6% (t −4.2).
  - 2015-24 was a weak decade for every momentum construction (EW L/S gross −2.7%/yr). In 2016-26, low-turnover winners earned +3.7% (t 1.0).
  - Momentum quintile ex highest-turnover quintile: +7.8%/yr vs the unfiltered quintile (t 6.2), Sharpe 0.18 → 0.45. The lab calls this a BUILD construction rule. ALL ex high-turnover already has Sharpe 0.38, so the exclusion does much of the work.
  - 12-7 L/S EW net35 Sharpe: 0.20 on quintiles, 0.60 on deciles. Long-only is untested.
- **Verification:** CONFIRMED for E7's number (E7-C18 MATCH). QUALIFIED for robustness: the sign depends on the decade, and E7's window is the weak one.
- **Triage:** FORWARD-SIM one pre-registered variant at weight 1: momentum quintile (12-1 or 12-7) ex the highest-turnover quintile or the F4 composite, vol-scaled (R-03), capped, long-only. The exclusion is a mandatory construction rule (EC-T-12) for any Korean momentum sleeve. Raw 12-1 stays at 0.

### EX-T-06: Low volatility in Korea: protective card, screen, or alpha?
- **Positions:**
  - E7: K-LV as a protective card (−0.8% in the crash vs −25.4%), weight 2.
  - E1: US low-vol stays at 2 only if DC9 shows alpha net of beta.
  - Chair and E5 (reviewer of E7's risk numbers): the protection is de-gearing.
- **Claims:** X57. E7-C20, E7 rank 2; E1 conflicts.
- **Key numbers:**
  - Chair c08 (E7 universe, 2015-07..2026-09): K-LV MDD −54.3% vs a same-beta static book (0.63x EWM) at −43.9%, so ΔMDD is −10.5 pp. ΔSharpe is +0.08.
  - R2 final, low-vol Q1 vs the VW market (1996-2026, net35):
    - beta 0.63 (EW) / 0.74 (VW); alpha +2.2% (t 0.8) / +0.7%;
    - it beat the VW market in 6 of 7 (EW) and 7 of 7 (VW) crash windows, and lagged in 9 of 10 rebounds (2026 melt-up: −110 pp / −102 pp);
    - EW MDD −74% vs market −70%;
    - lab verdict: "protective card, not alpha", to be judged on drawdown-first, Sharpe non-inferiority terms.
  - Chair c12 on the lab's own books, against a same-beta static book (β × market + cash, net35, 1996-2026):
    - EW book: MDD −73.9% vs −51.5% with the VW-market comparator (ΔMDD −22.4 pp), and vs −61.6% with the EW-universe comparator (−12.2 pp).
    - VW book: −64.9% vs −57.8% (−7.1 pp).
    - Tail ratio 0.97-0.99, so the PC-2 analogue fails.
    - Sharpe 0.41 vs 0.36 (VW comparator) and 0.24 (EW comparator), so Sharpe is non-inferior.
    - Crash windows vs the static book: EW wins 4 of 7 and VW wins 5 of 7. The large gains come in 2000 and 2026; it loses in 1997-98, the GFC and COVID (EW).
- **Verification:** CONTESTED between the lab and the chair. The chair reads the protective claim as REFUTED on the CARD-P definition (ER-T-03): the drawdown is no better than plain de-gearing. The lab reads it as protective against the market. The screen use is CONFIRMED: excluding the high-vol quintile adds +3.6%/yr (t 5.7).
- **Triage:**
  - BUILD NOW as a screen input (F2 / F4).
  - FORWARD-SIM K-LV as a descriptive sleeve, with the same-beta static comparator and Sharpe non-inferiority pre-registered.
  - The comparator definition for stock-level protective sleeves goes to the coordinator (MC-11).
  - BACKLOG US DC9.

### EX-T-07: Crowding multiplier
- **Positions:**
  - E1 wants crowding and comomentum tested as a sizing multiplier in [0.5, 1].
  - E5 says crowding describes crashes but does not time them. A multiplier must add value beyond own-vol scaling out of sample, and holdings-based crowding never acts.
- **Claims:** X41. E1 C1 card, E1-C12, C13; E5-C10, C21, C22.
- **Key numbers:** VIX was 12.9-25.8 at onsets. GS's Nov 2023 crowding record was followed by further gains. No Korean comomentum series has been computed.
- **Verification:** UNVERIFIED (no data).
- **Triage:** BACKLOG (BL-C14/DC5). It stays CONTEXT until a test shows value beyond R-03.

### EX-T-08: Extend the Daniel-Moskowitz bear gate (R-04) to earnings-momentum and revision sleeves?
- **Positions:**
  - E4 says yes: SUE also crashed in spring 2009.
  - E5 says no: R-04 itself has too few onsets.
- **Claims:** X27. E4-C28; E5-C03, C18, C29; E7-C25.
- **Key numbers:**
  - KR gate: on 4.1% of days, with 3 onsets since 2000 (2001-01-04, 2008-10-31, 2020-03-20).
  - It missed the October 2019, November 2020 and July 2026 crashes (24-month KOSPI return +227% on 22 Jun 2026).
  - Sharpe improves only 0.30 → 0.34 (EW) and 0.48 → 0.52 (VW).
- **Verification:** CONFIRMED in direction; E5-C29 is a minor MISMATCH.
- **Triage:** BACKLOG. Use the spec book only. No extension while R-04 is INSUFFICIENT DATA (MC-10).

### EX-T-09: Korean earnings-announcement drift weight: E4/E7 say 2, chair says 1
- **Claims:** X47. E4 sec.1 item 2, E4 weights, DC-2/DC-3; E7 weights.
- **Key numbers:**
  - E4 found no Korean drift evidence in the literature.
  - The chair ran E4's DC-3 information-event proxy (volume ≥ 4x the 60-day average and |abnormal return| ≥ 3σ, 2006-2026):
    - positive events: −1.34% over 60 days (t −4.2);
    - negative events: −2.68% (t −7.6).
  - In 1999-2005, positive events earned +9.5% (t 1.6) but had a median of −6.3%.
- **Verification:** UNVERIFIED for direct drift. The proxy points the other way.
- **Triage:** Weight 1. BACKLOG (DC-2, OpenDART with rcept_dt + 1). Dissent recorded: E4 and E7 hold 2.

### EX-T-10: Korean value weight: E4 says 2 (with a Value-up regime split), E7 says 1 until an OpenDART PIT test
- **Claims:** X58. E4 weights; E7 weights, E7-C15, C16.
- **Key numbers:**
  - E7's long-term-reversal value proxy: +0.2% net (2015-24); the chair gets −1.2%.
  - The RISE Korea Value-Up ETF holds SK hynix 20.9% and Samsung 17.5%, with 50.8% in IT. Its performance is chip beta, not value evidence.
- **Verification:** UNVERIFIED (no PIT fundamentals).
- **Triage:** Weight 1. BACKLOG (DC-8/DC10). Dissent recorded: E4 holds 2.

### EX-T-11: Ladder threshold units: σ-scaled (E5) or fixed % (macro R-07)?
- **Positions:**
  - E5: thresholds of −1.0σ / −1.5σ / −1.9σ of the declared book vol target. At 8% book vol these equal −8/−12/−15%. E5 also proposes a book vol target of 8% or less.
  - Macro R-07: fixed −8/−12/−15%.
- **Claims:** X39. E5-C14, E5 RL-6, RL-7.
- **Key numbers:**
  - Brownian check at Sharpe 0.5, probability of hitting −15% within 10 years: 0.66 at 8% vol; 0.97 at 12% vol.
  - KOSPI VT20 with a σ-scaled ladder (E5's figure; the chair did not re-run it): Sharpe 0.40, MDD −37.4%, 1 halt in total.
  - KOSPI VT20 with the fixed ladder (chair): Sharpe 0.40 → 0.35, MDD −47.4% → −34.8%, 0.50 halts/yr.
- **Verification:** CONFIRMED (E5-C14 MATCH).
- **Triage:** FORWARD-SIM both unit conventions. If the declared book vol is 8% or less, the two coincide (MC-01, MC-16).

### EX-T-12: Haircut multiplier and double counting
- **Positions:**
  - E1 and E4 apply ×0.4 at the live stage ("60% live haircut").
  - Macro §8.1 step 9 says expected live = 0.6 × OOS ("take 40% off").
  - The chair adds that applying publication decay and the gate haircut to the same published number double counts.
  - E1 still wants headline bank/AM backtests multiplied by 0.4-0.5 before they become priors.
- **Claims:** X01, X02. E1 KQ5, E1-C25; E4 sec.1 item 9.
- **Key numbers:**
  - E1's F1 chain is 0.26 × 0.51 × 0.4 ≈ 0.05. Corrected, the prior is 0.26 × 0.51 = 0.13, and ×0.6 applies only to the card's own OOS result.
  - E4's live IR of 0.12-0.2 corrects to 0.18-0.30.
- **Verification:** REFUTED (method) for the ×0.4 gate multiplier (E1-KQ5, E4-sec1 MISMATCH).
- **Triage:** CONTEXT (corrected anchor), with one haircut per stage. The context brief's "60% live haircut" wording is flagged (MC-12).

### EX-T-13: US opportunistic insider purchases (Form 4) as a gated BUILD candidate
- **Positions:**
  - E6 and E4: a buys-only overlay held about 126 days, value-weighted.
  - Chair, after verification: the anchor does not support that construction. E6 itself had warned that the holding period was unverified.
- **Claims:** X50. E6-C25, E6 #22, DC10; E4-C11, C12.
- **Key numbers:** Cohen-Malloy-Pomorski (1986-2007) report 82 bp/mo VW (t 2.15) and 180 bp EW (t 6.07). This is a long-short portfolio (opportunistic buys minus sells), held one month, measured as five-factor alpha. Routine trades earn about 0.
- **Verification:** QUALIFIED. The numbers MATCH; the construction is a MISMATCH.
- **Triage:** BACKLOG (DC10: buys-only, long-only, 126 days, timed by EDGAR acceptance). FORWARD-SIM only if DC10 passes.

### EX-T-14: US IPO-age exclusion screen
- **Positions:**
  - E6: BUILD candidate; exclude unprofitable issuers and those with sales below $50m for 36 months.
  - Chair: there is no US stock-level sleeve to screen yet.
- **Claims:** X51. E6-C01, C02, C04, E6 #1.
- **Key numbers:**
  - Ritter: 1980-2024 IPOs underperform by −20.5% vs the market and −8.9% style-adjusted over 3 years. The 2011-24 cohorts: −24.7% and −16.4%.
  - Unprofitable issuers: −23.4% vs +1.8% for profitable ones. Sales below $10m: −34.0%.
- **Verification:** CONFIRMED (E6-C01, C02 MATCH).
- **Triage:** BACKLOG. Build it with the first US stock card.

---

## 4. REFUTED / WITHDRAWN items (ER-T-01 .. ER-T-12)

| ID | Claim (holder) | What the check found | Claims / rows | Triage |
|---|---|---|---|---|
| ER-T-01 | Dynamic momentum "roughly quadruples" Sharpe (E1-C16) | The NBER w20439 abstract says it "approximately doubles". JFE Table 7: 0.682 → 1.041 → 1.194; static WML 0.71. | X27; log row 6 | CONTEXT (corrected anchor). R-03/R-04 are unchanged. |
| ER-T-02 | Bounding trend to [0.5, 1.0] keeps "about half" the protection (E3-C23) | PC-1 against the same-exposure S rises rather than halves: chair +9.2 to +15.0 pp vs +12.0; R2 +13.0 / +15.4 vs +11.3; R2 rates E3-d NOT REPRODUCED. E3's underlying concern is upheld: the floor gives back absolute slow-bear protection (1997-98: −6.9% sleeve vs −39.2% floored) and a plain floored trend fails PC-2 (tail 0.91). Floored trend × VT20 passes. | X32; row 33 | Withdrawn as stated. P2 stands with VT20 (EX-T-01). |
| ER-T-03 | Korean low-vol is a crash hedge, so a protective card at weight 2 (E7-C20) | Against a same-beta static book its MDD is worse: c08 (2015-26) −10.5 pp; c12 on the R2 books (1996-2026) −22.4 pp EW (VW-market comparator), −12.2 pp (EW comparator), −7.1 pp VW. Tail ratio 0.97-0.99. It lagged in 9 of 10 rebounds. The R2 lab reads it as protective against the market (contested, EX-T-06). | X57; row 90 | Withdrawn as a CARD-P protective claim. Screen input; descriptive FORWARD-SIM. |
| ER-T-04 | 82 bp/mo insider buys as a long-only 126-day overlay (E4-C11 use; E6-C25) | The anchor is a long-short (buys minus sells), one-month, five-factor alpha. | X50; rows 49, 75 | BACKLOG (DC10). |
| ER-T-05 | Prior design weights of 3 for Korea ST reversal, investor flows and earnings drift | Reversal does not survive 35 bp (weekly net35 Sharpe −1.78; monthly +2.7%/yr, t 0.5). The flow sign broke in 2026. There is no Korean drift evidence, and the proxy is negative. | X18, X47, X56 | Withdrawn: reversal 0 (1 monthly conditioning), flows 1, drift 1-2 |
| ER-T-06 | Korean VW momentum is an edge after 2016, and E5's 0.43 EW level | With a 5% name cap, 2016-26 net35 is 0.02. Levels: EW 0.26-0.30 gross, not 0.43. | X25; rows 55, 67 | Withdrawn (EC-T-08). |
| ER-T-07 | The brief's "Korean reversal −2.95%/month" (via E7-C17) | −2.950 is a regression coefficient (t −3.77, Jan 1999-Feb 2021), not a monthly return. The R2 lab reads the figure as an equal-weighted small-cap number. Either way, an implementable book earns nothing: R2 VW ex-microcap 1-month reversal +0.57%/mo gross (t 0.9), −0.68% net; lab R1 EW +1.41%/mo gross, +0.20% net (1999-2021). | E7-C17; row E7-C17 | Corrected anchor. |
| ER-T-08 | KEIA "pair = 22% of KOSPI at end-2023" (also in the macro R-07 evidence text) | Local marcap gives 26.9% (all lines) and 27.8% (common-only). | X08; E7-C24 | Corrected anchor (MC-15). |
| ER-T-09 | A T3 blog figure: GS high-beta momentum basket "−37% in July 2026" (E1 KQ3) | Only "worst month since November 2000" is verifiable (Yahoo/Bloomberg). The magnitude rests on Benzinga/TradingView. | row 11 | Withdrawn as a number. |
| ER-T-10 | Prior design: "+0.1 to +0.3 Sharpe from vol-scaled sizing on nearly every strategy" | The gain is robust only for momentum. Scaling makes KR STR net35 go from −0.29 to −0.59. KOSPI VT20 long-only scores 0.38 vs S 0.40. | X60; rows E5-C04, E3-VT20 | Withdrawn (already corrected by macro R-05). |
| ER-T-11 | The brief's "Korean momentum is negative among high-turnover stocks" (long-short, after Eom et al.) | R2 final: NOT REPRODUCED. The same design on adjusted returns gives +1.43%/month (t 3.3); unadjusted holding returns give −11.4%/month (t −5.4). The whole effect comes from capital reductions and reverse splits on 0.09% of stock-days. However, the long-only high-turnover winner leg does lag EW, by −11.6%/yr net (t −4.2, 1996-2026). EC-T-12 and EX-T-05 handle that leg. | X12; lab R1, R2 | Withdrawn as stated. |
| ER-T-12 | Name-level 15% stops on KRX sleeves | Net35 Sharpe falls (EW 0.04 → −0.15; VW 0.28 → 0.07), and the Kaminski-Lo condition fails. | X37; row E5-C07 | DROP (EC-T-09). |

---

## 4b. Corrected anchors (use these numbers from now on)

| # | Anchor | Corrected value | Source of correction |
|---|---|---|---|
| A1 | Daniel-Moskowitz dynamic momentum | "approximately doubles" Sharpe; JFE Table 7: 0.682 → 1.041 → 1.194 | NBER w20439 abstract; macro anchor |
| A2 | Gate step 9 | expected live Sharpe = 0.6 × OOS ("take 40% off"). E1's F1 prior is 0.13 before the gate. E4's composite live IR is 0.18-0.30. | macro §8.1 |
| A3 | Sim & Kim −2.950 | regression coefficient (t −3.77), not %/month | Emerald abstract |
| A4 | Pair share at end-2023 | 26.9% (all lines) / 27.8% (common-only), not 22% | chair c04 |
| A5 | Pair share, denominators | 29 Sep 2026: 50.8% (all lines), 52.6% (common-only), 53.7% (all lines with Samsung pref in the numerator). Peak 57.1% / 58.9% on 25 Jun 2026. First above 0.45 on 7 May 2026. | chair c04, c07 |
| A6 | CMP opportunistic insiders | long-short buys minus sells, one-month hold, five-factor alpha: 82 bp VW / 180 bp EW (1986-2007) | NBER w16454 |
| A7 | KR top-500 12-1 WML, 2000-26 | EW Sharpe ≈ 0.26-0.30 gross / 0.04-0.07 net35 on deciles; top-500 quintiles give 0.39 gross (R2). VW ≈ 0.44-0.48 / 0.28-0.30. 2016-26: EW net −0.13, VW net 0.30 (0.02 with a 5% cap). July 2026: −30.0% EW / −29.8% VW (R2). | chair c05; R2 final |
| A8 | Trend bounding (KOSPI) | PC-1 vs own S: +11.3 (unbounded × VT20) → +13.0 (linear) / +15.4 (clip). Absolute MDD −27.7% → −36.2% / −29.4%. | R2 |
| A9 | SPY trend at 50 bp | All multi-speed cells REJECT. At futures cost (5 bp): INSUFFICIENT DATA. | R2 |
| A10 | KOSPI 24-month return on 22 Jun 2026 | +227% (daily) / +222% (month-end), not +235% | chair c02 |
| A11 | KOSPI on 31 Mar 2025 | −3.00%, not −2.93% | chair c02 |
| A12 | MTUM IT weight (30 Jun 2026 factsheet) | 53.22%; 54.3% is the 29 Sep page | iShares |
| A13 | Korean low-turnover momentum, long-only excess vs EW | 2015-24: +2.9% (E7 universe) / −0.1% (ALL). 1996-2026 (ALL): +9.7%/yr net (t 2.8). High-turnover winners: −11.6%/yr (t −4.2). | R2 final |
| A14 | Korean low-vol | beta 0.63 (EW) / 0.74 (VW) vs the VW market. Against a same-beta static book, MDD is worse by 7-22 pp (1996-2026) and the tail ratio is 0.97-0.99. Sharpe 0.41 vs 0.24-0.36. | chair c08, c12; R2 |
| A15 | GS high-beta momentum basket, July 2026 | "worst month since November 2000". The −37% is unverified. | Yahoo/Bloomberg |
| A16 | KOSPI crash, 22 Jun-30 Jul 2026 | −38.6% (rebuilt index and official levels), not −38.0% | chair c02 |
| A17 | Korean high-turnover momentum W−L | positive on adjusted prices. The negative sign is an artefact of unadjusted prices. | lab R1; R2 |
| A18 | AQMIX | 10-year 5.44% vs T-bills 2.42%, vol 9.96%, so Sharpe ≈ 0.30 | E1-C05 check |
| A19 | E7 KRX event studies | stand as printed (−394/−579 bp; −43/−93 bp; −630 bp). The chair's first-pass −308 bp was the chair's own benchmark error. | c06b-c06d |
| A20 | KR D-M gate | 3 onsets since 2000 (2001-01-04, 2008-10-31, 2020-03-20), active on 4.1% of days. R2: 9 onsets in 1996-2026 (9.8% of days), mostly 1997-99. It never fires in a bull-market crash. | chair c05; R2 final |
| A21 | KOSPI trend protection | concentrated in 1997-2001: the multi-speed ensemble is REJECT from 2011 and 2016 starts. VT20 alone passes CARD-P from every start between 1996 and 2006 (PC-1 +4.4 to +11.6 pp). | R2 final, IDX sec.3 |
| A22 | Gate behaviour | Step 8 (≥ 60% of years positive) passes 24-31% of zero-Sharpe strategies over 10 years. Ten-session blocks over-reject: step 2 falsely passes 6.9% (not 5%) and step 5 12.8% (not 10%). E4's "IR 0.3 needs 18 years" is the 50%-power horizon; 80% power needs ~50 years. | R2 final, IDX sec.7 |

---

## 5. Consolidated weight table (0-3), alpha vs protective, old → new

**How to read the table**
- *Alpha* is the prior strength for a CARD-O return claim.
- *Protective* is the prior for a CARD-P drawdown claim, or for a de-gearing claim that must beat a same-beta static book.
- *Screen* is the priority, on the same 0-3 scale, of a subtractive screen gated against its unscreened book.
- *Prior design* is the original weight. *Macro now* is R-14/R-15 or §2.2 where they exist.
- Single-index trend has a return prior only; its gate class is CARD-P (EC-T-15).

### 5.1 United States (US equities via KIS, 50 bp per side)

| Family | Prior design | Macro now | Exec alpha | Exec protective / screen | Triage | Reason |
|---|---|---|---|---|---|---|
| XS momentum (stock) | 3 | R-03, R-04 | **2** | 0 | BACKLOG (no US stock sleeve yet) | French Mom Sharpe −0.16 in 2008-17; large-cap L/S prior ~0.25 gross; MTUM +2.1 pp/yr over 10y with −15/−17 pp years; cost drag ~3.6%/yr at 50 bp. Chair proposal from panel evidence, not disputed (X29). |
| ST reversal | 1 | R-05 1.0x | **0** | – | DROP | 0.37%/mo gross → −1.28%/mo net (NMV); break-even far below 50 bp |
| Value | 1 | – | 1 | – | composite member | HML 0.60 → −0.17 (2007-17); 50/50 mix −0.13 (X43) |
| Quality / profitability | 3 | R-05 1.0x | **2** | 0 (not a hedge) | composite member | QUAL −34.1 vs −33.9 (COVID), beta 0.99 (EC-T-19) |
| Low volatility | 2 | – | **1** (pending DC9) | 1 (must beat same-beta static) | BACKLOG DC9 | USMV −5.9 pp/yr vs IVV over 10y; Korean test shows de-gearing (EX-T-06) |
| Investor flow | 1 | – | 1 (display only) | – | CONTEXT | no executive evidence either way; macro never generates direction (P1) |
| Earnings drift | 2 | – | **1** | – | DROP standalone; confirmation input | PEAD 0.26%/mo net (t 1.60); large caps ≈ 0 since 2006 (EC-T-20) |
| TS trend, single index (SPY) | 3 | R-14: 3 | 1 (return prior) | **2** (3 only at ≤ 5 bp) | BACKLOG (instrument book) | R2 at 50 bp: REJECT across multi-speed cells; futures 5 bp INSUFFICIENT DATA (EX-T-03) |
| Net issuance (new) | – | – | **2** | – | BACKLOG (PIT share data) | E4 ranked #2; strong Korean analogue (EC-T-13) |
| Opportunistic insider buys (new) | – | – | **0-1** | – | BACKLOG DC10 | anchor is long-short, one month (ER-T-04) |
| IPO-age exclusion (new) | – | – | – | screen **2** | BACKLOG | Ritter −16.4% style-adj (2011-24); unprofitable −23.4% (EX-T-14) |

### 5.2 Korea (KRX stock 35 bp per side, KRX ETF 3 bp)

| Family | Prior design | Macro now | Exec alpha | Exec protective / screen | Triage | Reason |
|---|---|---|---|---|---|---|
| Raw 12-1 momentum | 1 | R-15: 0 | **0** | – | DROP | net35 Sharpe 0.04-0.07 (EW, 2000-26), −0.13 in 2016-26; VW 2016-26 drops to 0.02 with a 5% cap (EC-T-08) |
| Momentum variant (Q5 ex highest-turnover or ex F4; 12-1 or 12-7; vol-scaled, capped, long-only) | – | R-15: 1 (UNVERIFIED) | **1** | – | FORWARD-SIM | Q5 ex highest-turnover +7.8%/yr vs Q5 (t 6.2), which the lab calls a BUILD construction rule; low-turnover winners +9.7%/yr vs EW over 1996-2026 (t 2.8) but about 0 in 2015-24 (EX-T-05) |
| ST reversal, daily/weekly | 3 | R-15: 3; §2.2 KEEP 3 | **0** | – | DROP | weekly net35 Sharpe −1.78; break-even 12.5 / 22.2 bp (EC-T-02) |
| ST reversal, monthly | (3) | as above | 1 (conditioning input only) | – | CONTEXT | +2.7%/yr net35 (t 0.5); −6.7% in 2016-26 (R2) |
| Value | 2 | – | **1** (E4: 2) | – | BACKLOG (OpenDART PIT) | proxy +0.2% / −1.2% net; Value-up ETF = chip beta (EX-T-10) |
| Quality | 1 | – | 1 | – | BACKLOG (OpenDART PIT) | no PIT test yet |
| Low volatility | 2 | – | **0-1** | protective **1** (descriptive) + screen input | FORWARD-SIM; screen BUILD NOW | alpha vs VW +2.2% (t 0.8), vs EW +3.3% (t 1.9); same-beta static has 7-22 pp better MDD (c12); the lab reads it as protective vs the market (EX-T-06) |
| Investor flows | 3 | §2.2 KEEP 3 | **1** | – | BACKLOG (log flows now) | sign broke in 2026 (−₩148.3tn in H1 while KOSPI ~+101%) (EC-T-23) |
| Earnings drift | 3 | – | **1** (E4/E7: 2) | – | BACKLOG DC-2 | proxy: positive info events −1.34% over 60d (t −4.2), 2006-26 (EX-T-09) |
| TS trend, KOSPI (ETF line) | 2 | R-14: 1; R-06 VT20 | 1 (return prior) | **2** as floored trend × VT20; 1 for trend alone | FORWARD-SIM (floored trend × VT20) | R2: floored × VT20 PASS (indicative); VT20 alone PASS from every start 1996-2006; trend alone REJECT from 2011 starts (EC-T-15) |
| TS trend, KOSDAQ | – | R-14: 0 | 0 | 1 | BACKLOG | untested |
| Lottery / turnover / vol exclusion composite (new) | – | – | – | screen **3** | BUILD NOW | EW book +3.1%/yr net35 (t 8.3, IR 1.53); capped VW +0.5-0.9% (EC-T-12) |
| Dilution / net-issuance exclusion (new) | – | – | – | screen **3** | BUILD NOW | ex-Q5 +3.0%/yr (t 9.2); R2 F6 +2.3% (t 3.9), same at 70 bp (EC-T-13) |
| Attention-fade events (new; E7 asked for 3) | – | – | – | screen **0**; entry-day execution exclusion (convention) | DROP as a monthly screen | R2: weakest filter (+1.4% net35, −0.08% at 70 bp; negative on VW books); adding it to F4 lowers IR from 1.53 to 0.67 (EX-T-04) |
| 52-week-high proximity | – | – | 1 | – | BACKLOG (quarterly variant) | +1.0%/yr net in E7's run, +1.6% in the chair's; 64% of years positive (X59) |
| Size | (implicit) | – | **0** | – | DROP | L/S −26.9% (2025), −26.5% (2026) |

### 5.3 Other markets (time-series trend; E3's evidence only, not re-checked by the chair)

| Market / book | Prior design | Macro now (R-14) | Exec alpha | Exec protective | Triage | Reason |
|---|---|---|---|---|---|---|
| Crypto (BTC, ETH), C3 | – | 2 | 2 | 2 | keep C3; add a vol-scaled long-only control, a sub-period table and ETH replication | E3-C25 UNVERIFIABLE (no local crypto data); edge shrank in 2022-26 (X36) |
| Japan | – | 1-2 | 1 | 2 | BACKLOG | untested |
| Europe | – | 0-1 | 0-1 | 1-2 | BACKLOG | untested |
| Taiwan / China A / India | – | 1-2 / 0 / 1 | unchanged | unchanged | – | no executive evidence |
| Diversified futures (B3 re-registration) | – | B3 REJECT | 1-2 (diversifier claim) | 3 | BACKLOG (≥ 25 markets; gate-class approval) | live net Sharpe 0.3-0.6; Barclay Systematic −0.30%/yr in 2009-18 (EX-T-02) |
| FX / rates / commodities trend | – | – | 0-1 / 1-2 / 1-2 | 1 / 2 / 2 | BACKLOG | E3 |
| Carry | – | – | BACKLOG | – | BACKLOG | E3-C29 |

---

## 6. Risk-layer and execution conventions for stock-level sleeves

### 6.1 Conventions (all BUILD NOW unless marked)

| # | Convention | Rule | Evidence |
|---|---|---|---|
| RX-01 | Decision and fill timing | Decide at close t on data up to t. Primary fill: KRX official close t (closing call 15:20-15:30). Conservative bound: close t+1. Skip-day variant for holdings under one month. Never use NXT or after-hours prints. US: closing auction via KIS. | EC-T-03 |
| RX-02 | Momentum and trend entries | At the close, not the next open | KRX overnight +18.4%/yr vs intraday −7.9% (EC-T-26) |
| RX-03 | Limit-locked days | No entry at a locked limit-up close; fill at the t+1 open. A locked limit-down exit carries to the first unlocked session at 2x cost. VI, circuit-breaker, overheating and halt days are flagged unfillable. Locked limit-downs are excluded from reversal books. | −579 bp (t+20) for next-open buys after a lock; limit-down −1,036 bp (t+20) |
| RX-04 | Stops and exit fills | Fill at the worse of the stop and the next open, never at the stop. No name-level stops on KRX sleeves; signal exits only. | EC-T-09 |
| RX-05 | Eligibility | KOSPI+KOSDAQ common shares (code ending 0); price ≥ ₩1,000; cap ≥ ₩100bn or top 500 by prior month-end cap; 20-day ADV ≥ ₩1bn (₩3bn capacity variant); listed ≥ 60 sessions. Exclude administrative, caution and warning designations, SPACs, preferreds, REITs/funds, halted names, DART rights/merger windows and IPO/relisting days. Eligibility for books and benchmarks uses data up to t−1. US: price ≥ $5, ADV ≥ $5m. | EC-T-05 |
| RX-06 | Returns | Corporate-action-adjusted, with dividends where available. Flag |Δln shares| > 1% (DC0). | unadjusted closes fabricate −136%/yr |
| RX-07 | Capacity and impact | Position ≤ 1-2% of 20-day ADV. Impact = Y·σ_d·√(Q/ADV20), with Y ≈ 1. | EC-T-04 |
| RX-08 | Cost buckets | KRX ETF 3 bp. KRX stock 35 bp per side, itemised (commission, sell tax by date at 0.18 / 0.15 / 0.20% for 2024 / 25 / 26, half-tick floor, impact). 2x stress at 70 bp. US via KIS 50 bp; futures 5; crypto 10; FX 10. Costs are never lowered (P10); E7's 15-25 bp view for KOSPI200 names is unverified. | EC-T-04 |
| RX-09 | Turnover discipline | Monthly rebalance with buy/hold bands (enter the top decile or quintile, exit below the top 3 deciles or the quintile). One-way turnover target ≤ 30%/month, hard limit 50%. Report break-even per-side cost = gross / (2 × annual one-way turnover). Reject before the gate if break-even < 2x the pre-registered cost. | EC-T-04 |
| RX-10 | Caps | Single name ≤ 5% of NAV (selection sleeves). VW legs ≤ 5% of the leg. Sector ≤ benchmark +10 pp (long-only active ±5 pp). Pair cap 0.35 on look-through when pair share > 0.45 (market and ETF books). Semis ≤ 0.50. | EC-T-11 |
| RX-11 | Momentum risk | R-03 on every momentum sleeve, including KRX. No vol scaling for value, quality or reversal. R-04 on the spec book only. | EC-T-07, EX-T-08 |
| RX-12 | Book-level risk | Ladder on total book NAV only. Steps non-cumulative. Re-arm at 0.5 with the reference peak reset. Back to 1.0 after +0.5σ or 60 sessions. Never re-arm against the all-time HWM; never per sleeve. Threshold units are contested (EX-T-11). | EC-T-10 |
| RX-13 | Review triggers | Forward drawdown beyond the 95th percentile of simulation, or 12-month Sharpe below its 90% CI, triggers a REVIEW. Never auto-liquidate. | EC-T-09 |
| RX-14 | Long-only realism | Korea stock cards gated long-only. Pre-registered benchmarks: EW, CW, CW ex-pair, capped CW. Short-regime flag 0/1/2 (open / partial ban / full ban). L/S results only as diagnostics. | EC-T-06 |
| RX-15 | Reporting | Fixed stress windows: Aug 2007; Mar-May 2009; Oct 2019 (KR); Nov 2020; Jan 2021; Aug 2024; Apr 2025; Oct 2025 (KR); Mar 2026; 22 Jun-30 Jul 2026 and the rebound. Also report the worst five-week relative loss, cap-binding frequency, and correlation to the pair. | EC-T-25 |
| RX-16 | Event timestamps | EDGAR acceptance ≤ 15:30 ET is usable at close d, otherwise d+1. OpenDART rcept_dt is usable at the close of rcept_dt + 1 trading day. The event layer can only exclude names or scale exposure to ≤ 1.0. | EC-T-14, EC-T-22 |

### 6.2 Conflicts with the macro specification (flagged, not re-litigated)

| # | Macro item | Panel evidence / position | Recommended coordinator action |
|---|---|---|---|
| MC-01 | R-07 ladder thresholds fixed at −8 / −12 / −15% | E5 wants σ units. At 12% book vol and Sharpe 0.5, P(−15% within 10 years) = 0.97; at 8%, 0.66. | Pre-register both unit conventions (EX-T-11), or declare book vol ≤ 8% |
| MC-02 | R-07 re-arm reference (open point) | An all-time-peak reference re-halts 22.8 times a year (KOSPI Sharpe −1.65). A reset peak with re-arm at 0.5 gives 0.69 halts/yr. | Adopt reset and 0.5 (EC-T-10) |
| MC-03 | R-07 cumulative steps (open point) | Evidence is mixed: cumulative helped KOSPI in variant 1 and hurt SPY per E5. Non-cumulative steps with reset are robust. | Adopt non-cumulative steps |
| MC-04 | R-07: 0.05 single name vs 0.35 pair (open point) | The answer depends on book type: 0.05 for selection sleeves; 0.35 pair cap on look-through for market and ETF lines | Write the rule by book type (EC-T-11) |
| MC-05 | R-07 pair-share denominator (undefined) | On 29 Sep 2026: 50.8 / 52.6 / 53.7% depending on denominator; first above 0.45 on 7 May 2026 | Pre-register one denominator |
| MC-06 | R-14 class (CARD-O vs EW basket) and speed (12-1 monthly) | Single index belongs in CARD-P. Speed is venue-dependent (KOSPI 3 bp: 12M sign PC-1 +4.7 vs ensemble +8.9). | Keep R-14; add a CARD-P cell and a speed cell (EX-T-02) |
| MC-07 | P2 bounds for trend | R2: the floor gives back absolute slow-bear protection (1997-98: −6.9% sleeve vs −39.2% floored; plain floored trend tail 0.91, fails PC-2). With VT20 on top, the floored trend passes every evaluated check. | No change to P2 when VT20 is applied. The coordinator should still classify trend as signal or overlay for books without a vol target (EX-T-01). |
| MC-08 | §2.2 KEEP Korea flow 3 | Panel says 1: the sign broke in 2026; there is no t−1 history to test | Coordinator decides; log flows now |
| MC-09 | §2.2 KEEP / R-15 Korea ST-reversal 3 | Panel says 0 for daily/weekly and 1 for monthly conditioning; net35 tests fail | Coordinator decides; the R-15 net-of-cost test already fails on lab data |
| MC-10 | R-04 scope | E4 asks to extend it to earnings-momentum and revision sleeves; R-04 has only 3 Korean onsets | Spec book only (EX-T-08) |
| MC-11 | §8.7 CARD-P scope | §8.7 covers rules whose output never exceeds 1.0. A low-vol stock sleeve is not an exposure rule, so its protective claim needs a same-beta static comparator. | Add this comparator definition |
| MC-12 | Step-9 wording | The context brief says "60% live haircut"; the spec says live = 0.6 × OOS. Two panelists used ×0.4. | Fix the brief's wording (EX-T-12) |
| MC-13 | R-14 US weight 3 | It assumes futures-like costs; at 50 bp, R2 shows REJECT | Weight 2 pending the instrument book (EX-T-03) |
| MC-14 | R-08 (market stress gauges) | Quiet at most factor-crash onsets (VIX 12.9-25.8) | Do not count R-08 as factor-crash protection (EC-T-24) |
| MC-15 | R-07 evidence text "22% at end-2023" | Local data give 26.9% (all lines) / 27.8% (common-only) | Correct the text (ER-T-08) |
| MC-16 | Book vol target (not in the spec) | E5 proposes ≤ 8%/yr (judgment) | Coordinator decision; at ≤ 8% the MC-01 conflict disappears |
| MC-17 | R-06 Korea VT20 (indicative INSUFFICIENT DATA on the 2016-26 card) | R2 final: KOSPI VT20 is PASS on 1996-09..2026-09 (PC-1 +6.5 pp, tail 0.70, 70% of years) and from every start between 1996 and 2006; INSUFFICIENT from 2011/2016 starts. R4b's card is reproduced. | Information for the coordinator. The executives' panel supports VT20 as the protective workhorse (EC-T-15). |
| MC-18 | Gate steps 2, 5 and 8 | R2 final: 10-session blocks over-reject the null for index-like returns (step 2 6.9%, step 5 12.8%). Step 8 alone passes 24-31% of zero-Sharpe strategies over 10 years. | Use max(10, Politis-White) blocks in the outperformance gate as the macro cards already do; do not rely on step 8 alone (EC-T-28) |

---

## 7. Debate record (14 disputes)

Reviewer pairs as assigned:
- E1 and E4 review each other.
- E2 and E7 review each other.
- E3 and E5 review each other.
- E4 reviews E6.
- E5 reviews E7's risk numbers.
- E7 reviews E3's KOSPI numbers.
- E1 reviews E6.

The chair recomputed every contested number it could reach from local data.

### D1. Trend: signal sleeve or bounded overlay; speed and venue (EX-T-01, EX-T-02, EX-T-03, ER-T-02, EC-T-15)
- **E3:** single-index trend is protective. Bounding to [0.5, 1.0] halves protection. Use multi-speed daily ensembles. The US protective weight should be 3.
- **E1:** agrees on protective use. Trend is a sizing tool of at most 1.0, and its live alpha prior is 0.3-0.4 at most.
- **E7 (KOSPI numbers):** re-derived E3's KOSPI levels with the chair. They are slightly lower (ensemble long/flat 0.58 vs 0.40; −34.5% vs −45.2%), and the conclusion holds. E7 stressed that trend was fully long into the July 2026 crash and only VT20 protected.
- **E5 (reviewer):** challenged the halving claim and the 5 bp cost assumption for the US.
- **Recomputation:**
  - Chair: floor placement gives +9.2 or +15.0 pp, vs +12.0 for long/flat.
  - R2 final: bounded × VT20 PASS (PC-1 +15.4 / +13.0); unbounded × VT20 REVISE (PC-5 0.57). Bounded trend without VT fails PC-2 (tail 0.91-0.92). Absolute MDD worsens (1997-98 crash: −6.9% sleeve vs −39.2% floored). E3-d is NOT REPRODUCED.
  - R2 start-date sweep: trend's KOSPI evidence rests on 1997-2001 (REJECT from 2011), while VT20 passes from every start 1996-2006.
  - SPY at 50 bp: every rule fails. Futures at 5 bp: INSUFFICIENT DATA, with 53-56% of the benefit from the GFC.
- **Resolution:**
  - E3 conceded that bounding does not halve protection relative to the same exposure. E3 kept two points: bounding worsens absolute drawdown, and a bounded trend overlay without VT is weak on tail days.
  - P2 stands where VT20 is applied. KOSPI floored trend × VT20 goes to FORWARD-SIM as the primary CARD-P cell. Trend alone gets protective weight 1, because its evidence is old.
  - The US protective weight is 2 until there is a futures-cost instrument.
  - R-14's class and speed are flagged.

### D2. Name-level stops vs signal exits (EC-T-09, ER-T-12)
- **E5:** name-level stops fail on KRX, because the Kaminski-Lo condition is not met. Pod hard stops are a manager-selection device. Use review triggers instead.
- **E3:** in trend systems the signal exit is the stop, so a separate stop layer double counts.
- **E2:** stops fill far from the stop (6 May 2010: more than 20,000 trades over 60% away; 24 Aug 2015: SPY opened −5.2%).
- **E3 (reviewer of E5):** asked whether stops help anywhere. E5 named the US HZZ evidence for momentum; it goes to BACKLOG as its own CARD-O.
- **Recomputation (chair and R2):** stops lower net Sharpe in every variant, including "exit at the same close", which cannot be filled. ALL quintiles EW net35 goes from 0.20 to −0.20. Kaminski-Lo for KR WML EW: AR(1) −0.009 vs Sharpe 0.117.
- **Resolution:** DROP name-level stops on KRX. BUILD NOW review triggers and the signal-exit convention. No dissent.

### D3. Ladder corrections (EC-T-10, EX-T-11)
- **E5:** the macro ladder is sound only as a book-level tail device. Use σ units, re-arm at 0.5 from a reset peak, non-cumulative steps, never per sleeve, and a book vol target of 8% or less.
- **E3 (reviewer):** questioned whether a ladder adds anything on top of VT20. On KOSPI, VT20 plus ladder moves Sharpe 0.40 → 0.35 and MDD −47.4% → −34.8%, with 0.50 halts/yr. It cuts drawdown, at a cost in Sharpe.
- **Recomputation (chair):**
  - Variant 3 reproduced exactly: 0.42 → 0.40; MDD −55.8% → −41.3%; 0.69 halts/yr.
  - All-time-peak reference: 22.8 halts/yr, Sharpe −1.65.
  - Variant 1, KOSPI: cumulative 0.39 / −49.3% vs non-cumulative 0.34 / −53.6%.
  - Per-sleeve ladder on vol-scaled VW WML: 0.38 → 0.16.
  - Brownian false alarms match E5's table.
- **Resolution:** scope, reset re-arm at 0.5, non-cumulative steps and no per-sleeve ladders are BUILD NOW, as clarifications of R-07's open points. Threshold units remain contested between E5 and the macro spec. Pre-register both; they coincide at 8% book vol.

### D4. Korea concentration caps and what they cost (EC-T-06, EC-T-11)
- **Positions:** E4, E5 and E7 agree that a CW Korean benchmark or VW sleeve is a pair bet unless capped. The open questions were the denominator and how the 0.05 single-name cap interacts with the 0.35 pair cap.
- **E1 (reviewer of E4's table):** the numbers match; E4's 2026 YTD figures include preferred lines. **E2 (reviewer of E7's series):** matches. E5 used a common-only series.
- **Recomputation:**
  - Pair share on 29 Sep 2026: 50.8% (all lines), 52.6% (common-only), 53.7% (with Samsung preferred). End-2023: 26.9%, not KEIA's 22%.
  - The pair cap first bound on 7 May 2026. It cost −15.0 pp in the melt-up and −2.2 pp YTD, and saved +4.6 pp in the crash.
  - A 5% cap on VW momentum cuts 2016-26 net Sharpe from 0.30 to 0.02.
- **Resolution:** caps by book type, BUILD NOW. Pre-register the denominator. Correct the macro evidence text.

### D5. Attention-fade vs reversal vs lottery screens (EC-T-12, EX-T-04, EC-T-02)
- **E7:** attention chasing loses, so an attention-fade exclusion is rank 1 at weight 3. Daily/weekly reversal is dead.
- **E2:** reversal is dead after costs; any short-horizon card needs skip-day and band rules.
- **E2 (reviewer of E7):** the events were re-derived independently. The chair's first pass disagreed (−308 bp), which was traced to the chair's same-day-eligibility benchmark (+27.7%/yr). With eligibility lagged one day: −394 / −579 bp, −43 / −93 bp and −630 bp, all MATCH. Re-running E7's own pipeline reproduced −98.4 bp.
- **R2 final horse race (366 months):**
  - lottery composite F4: IR 1.53, the strongest;
  - turnover exclusion: +4.3%/yr;
  - attention-only F5: weakest, +1.4%, then −0.08% at 70 bp, and negative on VW books. Adding F5 to F4 lowers the IR to 0.67.
  - The lab: F5's events matter over 5-20 days, so a monthly screen with 20 sessions of memory flags 23% of names and raises turnover.
  - The chair's attention+MAX book (+2.06%) owes most of its gain to MAX.
- **Resolution:**
  - The F4 lottery composite (with F1 as an alternative) is BUILD NOW.
  - The attention screen is DROP as a monthly filter. Attention and limit events remain an entry-day execution exclusion (RX-03).
  - A daily-entry K-AF card goes to BACKLOG.
  - E7 dissents and keeps rank 1 for short-horizon use; recorded.

### D6. Korean investor flows (EC-T-23, MC-08)
- **E7:** flows are positive-feedback with permanent impact. The aggregate foreign sign broke in 2026 (foreigners net sold ₩148.3tn in H1 while KOSPI rose about 101%). Weight 3 → 1.
- **E6:** a flow card needs short-sale regime dummies.
- **E2 (reviewer):** KEIA and Korea Herald figures verified (MATCH).
- **No recomputation was possible:** there is no historical t−1 final-flow series locally.
- **Resolution:** the panel's consensus is 1, with no direction rule and logging from now. This conflicts with the macro KEEP 3, which goes to the coordinator.

### D7. Intraday and short-horizon technicals (EC-T-01, EC-T-02, EC-T-26)
- **E2:** intraday edges are 1-7 bp against costs 25-50x larger. Only slow strategies survive (one-sided turnover under about 50% a month).
- **E7:** Korean retail day trading loses; daily/weekly reversal is DROP.
- **E7 (reviewer of E2):** the KRX tick table (5.1-25.8 bp) and tax path (0.18 / 0.15 / 0.20%) MATCH. The cost arithmetic (176%/yr daily, 36%/yr weekly, 0.63%/mo monthly) MATCHES.
- **New KRX test:** momentum is earned overnight (+18.4%/yr vs −7.9% intraday). This supports close fills.
- **Resolution:** DROP intraday; DROP KRX daily/weekly reversal; momentum fills at the close. No dissent.

### D8. Insider, IPO and dilution events (EC-T-13, EX-T-13, EX-T-14, ER-T-04)
- **E6:** US opportunistic insider purchases are the only event signal worth gating (82 bp/mo, with a caveat that the holding period was unverified). Add a US IPO-age screen and a Korean dilution screen.
- **E4:** insider buys as an overlay, buys only.
- **E1 (reviewer of E4 and E6):** fetched NBER w16454. The 82 bp is a long-short (buys minus sells), one-month, five-factor alpha. That construction cannot support a long-only overlay held about 126 days. Ritter's IPO numbers MATCH.
- **E4 (reviewer of E6):** KOSPI on 31 Mar 2025 was −3.00%, not −2.93%.
- **Chair:**
  - Korean issuance quintiles: Q5 −13.4%/yr (t −10.3); ex-Q5 +3.0%/yr (t 9.2).
  - Issuance events: 12-month BHAR −25.3% size-matched, decaying from −34.4% (2005-14) to −17.6% (2015-24).
  - R2 F6: +2.3%/yr on the EW book.
- **Resolution:** the dilution screen is BUILD NOW. Insider buys go to BACKLOG (DC10). The US IPO screen goes to BACKLOG until a US stock sleeve exists. E6 accepted. E4 holds a weight of 1 for insiders once DC10 passes.

### D9. Korean momentum variants (EC-T-08, EX-T-05, ER-T-06, ER-T-11)
- **E5:** raw 12-1 → 0 is supported. A neutral variant (residual, 12-7 or sector-neutral) replaces it only if its 2016-26 90% CI excludes 0.
- **E7:** low-turnover winners are the only family positive at 2x cost.
- **E3 (reviewer of E5):** E5's levels do not reproduce (EW 0.43 printed vs 0.26-0.30), but 2016-26 matches and the decision stands.
- **E2 (reviewer of E7):** low-turnover momentum reproduces on E7's own universe (+2.9%, t 0.75) and vanishes in the ALL universe (−0.1%).
- **R2 final:**
  - E7's claim is CONFIRMED on its own construction. E5's claim is PARTLY confirmed: VW reproduces; EW 0.43 does not (top-500 quintiles give 0.39).
  - Full-sample long-only low-turnover winners beat EW by +9.7%/yr (t 2.8), and high-turnover winners lose by −11.6%/yr (t −4.2). 2015-24 was weak for every construction.
  - Momentum quintile ex highest-turnover: +7.8%/yr vs unfiltered (t 6.2). The lab calls this a BUILD construction rule.
  - 12-7 L/S net35 Sharpe is 0.20 on quintiles and 0.60 on deciles; long-only is untested.
  - The brief's "negative momentum among high-turnover stocks" comes only from unadjusted prices (capital reductions on 0.09% of stock-days).
- **Resolution:** raw 12-1 stays at 0 (DROP). One variant goes to FORWARD-SIM at weight 1: momentum quintile ex highest-turnover or ex F4, vol-scaled, capped, long-only. The exclusion is mandatory in any Korean momentum sleeve. E7 and E5 accept.

### D10. Low volatility: protective card or screen? (EX-T-06, ER-T-03)
- **E7:** K-LV lost only −0.8% (chair: −2.0%) in the July 2026 crash vs −25.4% for EWM, so it is protective at weight 2.
- **E5 (reviewer of E7's risk numbers):** that is beta. Compare against a same-beta static book.
- **E1:** US low-vol stays at 2 only if DC9 shows alpha net of beta.
- **Recomputation:**
  - Chair c08: same-beta static MDD is −43.9% vs K-LV −54.3%.
  - R2 final: alpha +2.2%/yr (t 0.8). K-LV beat the VW market in 6-7 of 7 crash windows and lagged in 9 of 10 rebounds. The lab's verdict is "protective card, not alpha", judged against the market.
  - Chair c12 on the lab's own books against a same-beta static book: MDD worse by 7-22 pp, tail ratio 0.97-0.99, Sharpe non-inferior.
  - §8.7 applies to exposure rules of at most 1.0, so a stock sleeve needs a same-beta comparator (MC-11).
- **Resolution:** low-vol becomes a screen input (BUILD NOW) and a descriptive FORWARD-SIM sleeve with a protective weight of 1 at most. E7 and the lab keep the market-relative reading; E5 and the chair keep the exposure-matched one. The comparator definition goes to the coordinator.

### D11. Crowding: monitor or multiplier? (EC-T-24, EX-T-07)
- **E1:** crowding and valuation are sizing context in [0.5, 1.0]. E1 proposes a tested multiplier (C1, BACKLOG).
- **E5:** crowding measures describe crashes but do not time them. VIX was quiet at onsets. Holdings-based crowding never acts.
- **E4 (reviewer of E1):** the November 2023 GS record was followed by further gains (T2), which is consistent with E5.
- **No Korean comomentum series was available** to the chair.
- **Resolution:** display only. The multiplier goes to BACKLOG and must beat R-03 out of sample.

### D12. Point-in-time data, Korean earnings drift and Korean value (EC-T-14, EX-T-09, EX-T-10)
- **E4:** build the PIT layer. Korean drift 3 → 2 pending DC-2; Korean value 2 with a Value-up split.
- **E7:** value 1 until OpenDART; drift 2.
- **E6:** Korean events are usable from rcept_dt + 1.
- **E1 (reviewer of E4):** the power table matches (IR 0.3 needs about 18 years).
- **Recomputation:**
  - The chair ran DC-3 (information-event proxy). Positive events lose −1.34% over 60 days in 2006-26, so there is no drift.
  - KIND's time column returned HTTP 403.
- **Resolution:** the PIT layer is BUILD NOW. Korean drift is 1 and Korean value is 1, both BACKLOG. Dissents recorded: E4 and E7 hold 2 for drift; E4 holds 2 for value.

### D13. Haircuts and double counting (EX-T-12, EC-T-28)
- **E1:** haircut bank/AM backtests by 50-60%, then subtract 2 × cost × turnover. F1 chain: ×0.51 publication decay, then ×0.4.
- **E4:** live IR 0.12-0.2 after "the 60% haircut".
- **Cross-review (E1 ↔ E4):** both used ×0.4, while the spec says live = 0.6 × OOS. Applying publication decay and the gate haircut to the same published number double counts.
- **Resolution:** use one haircut per stage. Corrected anchors: F1 prior 0.13, with ×0.6 applying only to the card's own OOS; composite live IR 0.18-0.30. E1 keeps the prior-calibration rule for headline bank backtests, applied before any OOS evidence exists. This is accepted as CONTEXT.

### D14. Product composites, factor-ETF rotation and valuation timing (EC-T-17, EC-T-18)
- **E1 and E4** both recommend DROP. No panelist defended these products. E4 passed VCP to the technical panel.
- **Cross-checks:**
  - E4 checked E1's Shiller numbers: CAPE R² 0.05 / 0.16 / 0.29 MATCH; out-of-sample −0.56 / −0.25; CAPE > 30 forward return +3.0%.
  - E1 checked E4's FFTY figure (3.52%/yr): MATCH.
- **Resolution:** DROP as timing or alpha; CONTEXT displays only.

---

## 8. Cross-examination verdicts per paper (key claims)

| Paper (reviewer) | Claim | Verdict | Basis |
|---|---|---|---|
| E1 (E4) | C06: S&P 12m long/flat return/vol 1.32 vs 0.81 (1992-2014); 1.02 vs 1.16 (2015-26) | CONFIRMED | Shiller recompute; R2 e1 checks |
| E1 (E4) | C08: CAPE R² and out-of-sample failure | CONFIRMED | Shiller recompute |
| E1 (E4) | C11: CAPE > 30 forward returns | CONFIRMED | Shiller recompute |
| E1 (E4) | C14: MTUM −18.0% vs SPY −2.0% (Jun-Jul 2026) | CONFIRMED | Stocklake |
| E1 (E4) | C05: AQMIX net trend prior | CONFIRMED | vol 9.96%, so Sharpe ≈ 0.30 |
| E1 (E4) | C16: dynamic momentum "quadruples" Sharpe | REFUTED (magnitude) | NBER abstract: "approximately doubles" |
| E1 (E4) | C20/C21: smart-beta ETF record | QUALIFIED | IT weight 53.22% (not 54.3%) on the cited date |
| E1 (E4) | KQ3: GS basket −37% (T3) | UNVERIFIED | only "worst month since Nov 2000" is verifiable |
| E1 (E4) | KQ5: haircut chain ×0.4 | REFUTED (method) | spec ×0.6; double counting |
| E2 (E7) | D1: cost arithmetic 176% / 36% / 0.63% | CONFIRMED | recomputed |
| E2 (E7) | C26: KRX tick and tax floor 25-45 bp | CONFIRMED | tick table c06; PwC tax |
| E2 (E7) | C14: NMV reversal net −1.28%/mo | CONFIRMED | NBER w20721 |
| E2 (E7) | C17: close pressure 8.1 bp | CONFIRMED | source |
| E2 (E7) | C06: momentum is earned overnight | CONFIRMED; extended to KRX | c06 |
| E2 (E7) | C30: break-even formula | CONFIRMED | lab R1 12.5 / 22.2 bp |
| E2 (E7) | C25: KRX VI / limit rules | CONFIRMED | source |
| E3 (E5; E7 on KOSPI) | C09: industry trend record post-2009 | CONFIRMED | Barclay figures |
| E3 (E5) | C26: Shiller averaging bias | CONFIRMED | AC 0.057 vs 0.206; 0.51 → 0.30 |
| E3 (E5) | C19: SPY 200d protection at 5 bp | CONFIRMED | 0.34 vs 0.37; −30.0 vs −56.5 |
| E3 (E7) | C20: KOSPI ensemble long/flat vs S | CONFIRMED (R2 E3-a CONFIRMED); robustness TRACED | 0.58 vs 0.40; −34.5 vs −45.2; 2013-26 PC-1 −3.4; R2: PASS from 1996-09, REJECT from 2011 starts |
| E3 (E7) | C21: trend × VT20 KOSPI | QUALIFIED | 0.61; −29.0 vs −41.0; unbounded REVISE (PC-5 0.57) |
| E3 (E5) | C23: bounding halves protection | REFUTED as stated (R2: NOT REPRODUCED); the concern about absolute slow-bear protection is upheld | chair and R2 |
| E3 (E5) | C19: US protection weight 3 | QUALIFIED | 50 bp REJECT |
| E3 (E5) | C25: crypto C3 edge | UNVERIFIED | no local data |
| E3 (E5) | C28: signal exit = stop | CONFIRMED | consistent with the stop tests |
| E4 (E1) | C19 / C20 / C21: French value and momentum splits | CONFIRMED | linearmodels / arch |
| E4 (E1) | sec.6: Korean concentration and breadth | CONFIRMED (TRACED universe) | c04, c09 |
| E4 (E1) | C04 / C02: NMV table; PEAD ≈ 0 for large caps | CONFIRMED | NBER w20721 |
| E4 (E1) | C26: FFTY 3.52% | CONFIRMED | source |
| E4 (E1) | C11: insider 82 bp as a long-only overlay | QUALIFIED (numbers right, construction wrong for this use) | NBER w16454 |
| E4 (E1) | sec.1: live IR 0.12-0.2 | REFUTED | ×0.6 gives 0.18-0.30 |
| E4 (E1) | Power table | CONFIRMED (arithmetic); R2 adds that 18 years is the 50%-power horizon | arithmetic; R2 E4-a PARTLY |
| E4 (E1) | DC-1: Korean heavy issuers underperform | CONFIRMED | chair c06 |
| E4 (E1) | "No Korean earnings-drift evidence" | CONFIRMED (proxy negative) | chair c07 |
| E5 (E3) | C18: KR WML levels | QUALIFIED (R2: PARTLY) | EW levels lower (top-500 quintiles 0.39); VW, 2016-26 and the decision match |
| E5 (E3) | C07: KRX stops lower Sharpe | CONFIRMED | chair and R2 |
| E5 (E3) | C04: KRX vol scaling | CONFIRMED | after the chair's warm-up fix |
| E5 (E3) | C15: ladder variant 3 | CONFIRMED | exact |
| E5 (E3) | C14: Brownian false alarms | CONFIRMED | simulation |
| E5 (E3) | C19: 5% cap removes the 2016-26 VW edge | CONFIRMED | 0.30 → 0.02 |
| E5 (E3) | C29: D-M gate in Korea | QUALIFIED | 3 onsets, not about 5 |
| E5 (E3) | C20 / C13 / KL / French Mom | CONFIRMED | VIX 19/19; sources; French |
| E6 (E4, E1) | C01 / C02: IPO underperformance | CONFIRMED | Ritter |
| E6 (E4) | C14: S&P inclusion effect gone | CONFIRMED | source |
| E6 (E1) | C25: insider 82 bp signal | QUALIFIED | long-short, one month |
| E6 (E4) | C27: EDGAR / OpenDART timestamps | CONFIRMED | sources; KIND UNVERIFIED (403) |
| E6 (E4) | C22: KOSPI −2.93% on 31 Mar 2025 | QUALIFIED | −3.00% |
| E6 (E4) | C19: Korean SEOs about −31% over 12 months | CONFIRMED in direction | proxy −25.3% size-matched; decaying |
| E6 (E1) | #6: dilution screen survives costs | CONFIRMED (EW books only) | c06; R2 F6 |
| E6 (E4) | C18: Value-up day-0 effect | CONFIRMED | source |
| E7 (E2) | C02 / C04 / C03: attention and limit events | CONFIRMED | c06d after the chair's fix |
| E7 (E2) | Long-only factor table, 2015-24 | CONFIRMED (approx.) | within 1-3 pp/yr; LTR net sign differs |
| E7 (E2) | C18: low-turnover momentum +3.1% net | CONFIRMED (number; R2 CONFIRMED); QUALIFIED (robustness) | E7-exact +2.9%; ALL 2015-24 −0.1%; 1996-2026 +9.7%/yr (t 2.8) |
| E7 (E5) | C20: low-vol is protective | REFUTED on the CARD-P comparator (contested: R2 reads it as protective vs the market) | c08, c12 same-beta static |
| E7 (E5) | C22 / C23: breadth and pair share | CONFIRMED | c04, c09 |
| E7 (E2) | C24: KEIA 22% is wrong | CONFIRMED | 26.9% |
| E7 (E2) | C17: Sim & Kim coefficient | CONFIRMED | Emerald abstract |
| E7 (E2) | C14 / C29 / C15: flows, Sedaily, RISE ETF | CONFIRMED | sources |
| E7 (E5) | Records and crash path (−12.06%, −9.99%, +17.91%; −38.6%) | CONFIRMED | c02 |
| E7 (E2) | Desk view: 15-25 bp costs for KOSPI200 names | UNVERIFIED | needs quotes |

---

## 9. Verification-log summary

**File:** `/home/claude/datalab/r2/verification/exec_verification_log.csv`. It has 103 rows with columns row, claim ID, paper, reviewer, number as printed, how checked, value found, status, consequence and source tier.

**Status counts:** 77 MATCH (75%), 12 MISMATCH, 11 TRACED-NOTE, 3 UNVERIFIABLE.

| Paper | Rows | MATCH | MISMATCH | TRACED-NOTE | UNVERIFIABLE |
|---|---|---|---|---|---|
| E1 | 14 | 10 | 3 | 1 | 0 |
| E2 | 10 | 8 | 0 | 2 | 0 |
| E3 | 16 | 12 | 1 | 2 | 1 |
| E4 | 16 | 11 | 2 | 3 | 0 |
| E5 | 17 | 14 | 3 | 0 | 0 |
| E6 | 11 | 6 | 2 | 2 | 1 |
| E7 | 19 | 16 | 1 | 1 | 1 |

**Rows by reviewer:** E4 21, E1 20, E7 18, E3 17, E5 14, E2 12, chair 1.

**How numbers were checked:** local recomputation (Shiller, SPY, French via linearmodels/arch, VIX, marcap KRX cache; c12 also ran on the R2 lab's engine), WebFetch of known URLs, and the R2 lab's final summaries and result files.

**Every MISMATCH and its correction**

| # | Row | Claim | Printed | Correction |
|---|---|---|---|---|
| 1 | 6 | E1-C16 | Dynamic momentum "roughly quadruples" Sharpe (1.18 vs ~0.3) | "Approximately doubles". JFE Table 7: 0.682 → 1.041 → 1.194; static WML 0.71. |
| 2 | 12 | E1-C20/C21 | MTUM IT 54.3% (30 Jun 2026) | 53.22% on the 30 Jun factsheet. The other figures match (10y 17.58%; P/E 46.12x; 2021 lag 15.2, 2023 lag 17.2 pp). |
| 3 | 14 | E1-KQ5 | F1 prior × 0.4 gate haircut ≈ 0.05-0.10 | The gate multiplier is ×0.6 and applies to own OOS. The prior is 0.26 × 0.51 = 0.13; no stacking. |
| 4 | 33 | E3-C23 | Long/half × VT20 keeps about half the protection (PC-1 +8.1 vs +17.3 pp) | Chair +9.2 / +15.0 vs +12.0. R2 +13.0 / +15.4 vs +11.3 (NOT REPRODUCED). Bounded × VT20 PASS (indicative). The floor does cost absolute slow-bear protection (1997-98: −6.9% vs −39.2%). |
| 5 | 49 | E4-C11 | Insider 82 bp/mo used as a long-only buys-only overlay | Long-short (buys minus sells), one-month hold, five-factor alpha |
| 6 | 52 | E4-sec1 | Composite live IR 0.12-0.2 | 0.18-0.30 (×0.6) |
| 7 | 55 | E5-C18 | KR WML EW gross 0.43 / net 0.20; VW 0.52 / 0.36; July 2026 −24.8% / −29.6% | Chair EW 0.30 / 0.07, VW 0.48 / 0.30, July −28.0% / −30.0%. R2 EW 0.26 / 0.04 (quintiles 0.39), VW 0.44 / 0.28, July −30.0% / −29.8%; R2 rates it PARTLY. 2016-26 matches. |
| 8 | 64 | E5-C29 | D-M gate on 3.9% of days, about 5 onsets; Sharpe 0.43 → 0.45 / 0.52 → 0.55 | 4.1% of days; 3 onsets (2001-01-04, 2008-10-31, 2020-03-20); 0.30 → 0.34 / 0.48 → 0.52 |
| 9 | 67 | E5-C18 (24m) | KOSPI 24-month return +235% on 22 Jun 2026 | +227% (daily) / +222% (month-end) |
| 10 | 75 | E6-C25 | Insider 82 bp/mo as a ~126-day signal | Long-short, one month; BACKLOG DC10 |
| 11 | 78 | E6-C22 | KOSPI −2.93% on 31 Mar 2025 | −3.00% |
| 12 | 90 | E7-C20 | Low-vol is a crash hedge (K-LV) | Same-beta static MDD −43.9% vs −54.3% (c08, 2015-26). On the R2 books (c12, 1996-2026), the static book is shallower by 7-22 pp and the tail ratio is 0.97-0.99. R2 alpha +2.2%/yr (t 0.8). R2 reads it as protective vs the market (contested). |

**TRACED-NOTE rows (11)**
- E1-KQ3: T3 −37% → "worst month since Nov 2000".
- E2-C06: new KRX overnight-momentum evidence.
- E2-C23: KCMI, cross-paper.
- E3-C19(cost): the US at 50 bp REJECTs.
- E4-sec6: universe difference.
- E4-DC1: issuance supports.
- E4-DC3: drift proxy negative.
- E6-C19: dilution BHAR proxy.
- E6-#6: R2 F6.
- E7-CHAIR: the chair's own benchmark error, corrected.
- E3-C20(robust): KOSPI trend protection rests on 1997-2001 (R2 start-date sweep).

**Status changed after the R2 summaries:** E7-C18 moved from MISMATCH to MATCH. The lab reproduces E7's printed +3.1% at +2.9% and rates it CONFIRMED; the robustness question moved to the consequence column.

**UNVERIFIABLE rows (3)**
- E3-C25: crypto, no local data.
- E7 desk view: 15-25 bp, needs quotes.
- E6-KIND: time-of-day column returned HTTP 403 on 3 Oct 2026.

**Chair errors found and corrected (2)**
1. KRX vol-scaling warm-up: the first pass understated VW scaled Sharpe as 0.13 instead of 0.38-0.41.
2. Event-study benchmark: same-day eligibility inflated the benchmark to +27.7%/yr. Both are documented in c05b and c06b-c06d.

**Fetch failures:**
- KIND returned HTTP 403.
- The EY tax page came back garbled, so PwC was used.
- WebSearch was not used, because the session budget was exhausted.

---

## 10. Gaps

1. **R2 summaries arrived late (00:16 KST) and were incorporated.** Their own caveats carry over: everything is in-sample; the plateau of floored trend × VT20 was not evaluated; E5's scripts were not saved; dividends and the risk-free rate are excluded. The lab and the chair still disagree on low volatility (EX-T-06).
2. **No OpenDART pull.** This blocks the Korean value and quality tests, Korean earnings drift (DC-2) and the GP/A composite (EX-T-09, EX-T-10, EC-T-14).
3. **No EDGAR Form 4 or US stock-level panel.** This blocks DC10 (insiders), US net issuance, the US IPO-age screen and US low-vol DC9.
4. **No quote or order-book data.** KRX spread and impact calibration, E7's 15-25 bp view and NXT effects cannot be tested. Costs stay at 35 bp per side.
5. **No historical t−1 final investor-flow series.** The Korean flow card cannot be tested; logging should start now.
6. **Price-only Korean returns.** Dividends are missing, which understates low-vol and value sleeves by perhaps 1-2%/yr. Momentum is mostly unaffected.
7. **No crypto history locally.** E3's C3 numbers are unverified.
8. **KIND time-of-day unverified (HTTP 403).** The Korean availability rule stays at rcept_dt + 1.
9. **No Korean comomentum or crowding series.** EX-T-07 is untested.
10. **Multiple testing.** Every chair and R2 number is in sample. E3 tried about 40 configurations, and the R2 exclusion race used 176 trials. Indicative PASS/REVISE readings are not gate results.
11. **Chair recomputation risk.** Two chair errors were found and fixed. No second independent re-run of the chair's scripts was done.
12. **SPY ladder results** (cumulative vs non-cumulative) were taken from E5 and not re-run by the chair.
13. **Panel independence.** The professors' panel resolution was not read. The synthesis step must reconcile overlapping items, especially Korean reversal, momentum variants, low-vol and trend bounding.
