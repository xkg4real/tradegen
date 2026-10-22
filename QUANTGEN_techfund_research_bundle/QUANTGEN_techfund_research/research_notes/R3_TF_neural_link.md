# R3 "Neural Link": technical and fundamental signals for QUANTGEN, one map of both panels and the data labs

Round 3 synthesis, 2026-10-03. Author: synthesis lead (round 3). The panels (professors P1-P7, executives E1-E7) are fictional composite personas; their claims are treated as claims, and every number below is either traced to a lab or verification file or marked as not traced.

Outputs of this round (all paths absolute):
- This report: `/home/claude/research_notes/QUANTGEN technical and fundamental signals/R3_TF_neural_link.md`
- Node and edge map: `/home/claude/datalab/r3/R3_TF_nodes.csv` (70 nodes), `/home/claude/datalab/r3/R3_TF_edges.csv` (85 edges)
- Chart-ready JSON: `/home/claude/datalab/r3/charts/focus_map.json`, `weights_final.json`, `go_nogo.json`, `golden_values.json`
- Supporting tables: `/home/claude/datalab/r3/results/` (r3_weights_final.csv, r3_weights_other_markets.csv, r3_go_nogo.csv, r3_golden_values.csv, r3_pair_share*.csv, r3_ledger_claims.json, r3_focus_by_theme.json); scripts in `/home/claude/datalab/r3/scripts/` (r3_00 .. r3_06); working notes `/home/claude/datalab/r3/R3_working_notes.md`.

Labelling convention. Every number carries market, period, gross/net and a source. "net 35" = net of 35 bp per side (KRX stock, tax included); "net 70" = the 2x stress; "net 3 bp" = KRX ETF line; "50 bp" = US via KIS. KRX lab Sharpe ratios are raw (risk-free rate 0) and lab returns are price returns without dividends. File references: "line n" is the line in the CSV file (header = line 1); "exec row n" is the `row` field of `r2/verification/exec_verification_log.csv` (file line n+1); "V0nn" is a `log_id` in `r2/verification/prof_verification_log.csv`; lab paths are relative to `/home/claude/datalab/`. "R2_PROF" and "R2_EXEC" are the two chair resolutions in the research-notes folder.

## 1. Summary

This round merged 414 panel claims (209 professors, 205 executives), all 120 claim-matrix propositions (60 per panel), all 115 chair items (61 professors, 54 executives) and the four data labs into one map of 70 single-proposition nodes (TF-01..TF-70) joined by 85 edges. Final classes: 29 CORE-LINK, 18 CORE-PROHIBITION, 11 CONTESTED, 8 ONE-SIDED and 4 UNTESTED; the mechanical class rule gave 28/16/11/11/4, and three coordinator rulings moved a node (CR-06: attention-fade screen to prohibition; CR-08: attribution block to core; CR-11: macro x signal terms to prohibition).

What both panels support and the data confirm is mostly plumbing and risk discipline: decide at the close and fill at the KRX official close, locked-limit rules, point-in-time and corporate-action hygiene, a long-only primary statistic against a declared benchmark set, an itemised cost header with a break-even pre-gate screen, turnover bands, no name-level stops, stress tables, macro R-03 vol scaling on every momentum sleeve, and Korea caps with one pair-share denominator. The only Korean stock-level return sources that both panels support and the labs confirm net of costs are subtractive screens: excluding the lottery composite adds +3.08%/yr net 35 on the equal-weighted KRX book (IR 1.53, 1996-03..2026-09; r2/kr/results/r2_kr_excl_summary.csv line 11) and excluding heavy issuers adds +2.34%/yr net 35 (IR 0.65; line 17); both are BUILD NOW as screen cards gated as CARD-O, weight 3 on equal-weighted and small/mid books, 1 on capped cap-weighted books and 0 on the top-200 book, with an indicative gate of 7 of 8 steps (REVISE) because the deflated Sharpe pooled over 176 trials is 0.94 (r2_kr_excl_gate.csv line 2). On the index side, the KOSPI 20-day vol target (macro R-06) is the protective workhorse (rebuilt KOSPI 1996-09-02..2026-09-29, net 3 bp: max-drawdown gain +6.5 pp over the same-exposure static book, tail ratio 0.70, CARD-P PASS; r2/idx/results/r2_idx_protective_scorecard.csv line 5), floored trend x VT20 runs as FORWARD-SIM, and single-index trend is CARD-P only with alpha weight 0. The DO-NOT-BUILD headline: Korean daily/weekly reversal (weekly L/S net-35 Sharpe -1.78, KRX ALL EW 1996-2026, kr/results/kr_key_numbers.csv line 30; break-even 12.5 bp per side), raw Korean 12-1 momentum, low volatility as Korean alpha, size, investor-flow direction rules, US PEAD and event drifts as cards, US single-index trend at 50 bp, classic technical and TradingView rules (Hansen SPA p 0.880 over 303 KOSPI timing rules, 1996-2026, 3 bp), intraday and short-horizon technical trading, deep/LLM strategies, macro x stock-signal terms and crypto reversal. Fundamentals are the main hole: a Korean value-quality composite (KR-VQ) and a US value-quality composite (US-VQ) have support from both panels at weight 2 but stay UNTESTED until point-in-time OpenDART and FMP/EDGAR stores exist, so they are BACKLOG BUILD-candidates, not spec items.

Final Korea weights: raw 12-1 momentum 0, constrained momentum 1 (FORWARD-SIM), 52-week high 1 (feature), daily/weekly reversal 0 with a monthly guard 1, value 1, quality 1, KR-VQ 2 (pending PIT), investor flow 1 (logging only), earnings drift 1, low volatility 0 as alpha and 0 as protection (screen input only), size 0, KOSPI trend 0 alpha / 1 protective, VT20 2 protective, floored trend x VT20 2 (FORWARD-SIM), lottery and dilution screens 3/1/0 by book type. Final US weights: stock momentum 1, reversal 0, value 1 inside US-VQ, quality 2 as a composite leg, US-VQ 2 (pending PIT data), low volatility 1 alpha and 1 protective (BACKLOG, judged against S_beta), flows 1 (display), PEAD 0 standalone, and SPY trend 0 alpha with protection 0 at 50 bp and 1 at futures cost (BACKLOG).

Attention did not follow evidence: executives spent their most claims on short-horizon technical trading (TF-61, 23 claims, refuted) and product composites (TF-47, 19), professors on classic technical rules (TF-60, 25, refuted) and the US value-quality composite (TF-43, 16), while the two screens that survived drew 9 (TF-12) and 6 (TF-13) claims. The spec's acceptance tests get 523 golden values (497 traced to a file and line, 20 derived by stated arithmetic, 6 not traced: the plateau and start-date sweep of the floored trend x VT20 cell, any ridge-combiner number, the new C3 controls, E5's sigma-ladder and SPY cumulative-step figures, and step 9 at 0.6 x OOS). The macro spec owner receives 22 cross-spec amendments (among them Korea reversal 3 -> 0 and flows 3 -> 1 as supersessions of R-15/section 2.2, the CR-07 pair share of 53.71% on 2026-09-29 from the KRX daily file, S_beta in section 8.7, and CARD-P and speed cells for R-14) and 15 open questions, led by the ladder's threshold units.


## 2. Coordinator rulings (verbatim) and how they were applied

> CR-01 Low volatility (MC-11, EX-T-06, professors' "protective low-vol sleeve at 2"): the pre-registered protective class requires protection to be shown against a static book with the same average exposure, because constant de-gearing lowers drawdown by itself. For a stock-selection sleeve the analogue is the same-beta static book S_beta = beta_hat x market + (1 - beta_hat) x cash, beta_hat pre-registered. On that comparator Korean low-vol fails PC-1 (ΔMDD -7 to -22 pp) and PC-2 (tail ratio 0.97-0.99). So low-vol is neither an alpha card nor a protective card: it enters as a screen input (the high-volatility tail exclusion inside the lottery screen) and, at most, a FORWARD-SIM descriptive sleeve with S_beta pre-registered. Add S_beta to governance as the CARD-P comparator for stock-level sleeves. US low-vol stays BACKLOG (alpha net of beta untested).

Applied: TF-16 stays CONTESTED and goes to FS-3 (descriptive); TF-17 low-vol alpha is CORE-PROHIBITION (DNB-TF-02); low-vol enters SCR-1 as the high-volatility tail; S_beta is GOV-11 (TF-59) and cross-spec XS-12; Korea low-vol weights alpha 0, protective 0, screen input; US low-vol BACKLOG (BL-TF-03).

> CR-02 Trend (EX-T-01, MC-06, MC-07): a standalone index trend sleeve (its own capital line, long/flat ETF or futures) is a strategy card and may hold 0, like card C3; when trend scales any other book it is an overlay bounded to [0.5, 1.0] (macro P2). Single-index trend is CARD-P only, never CARD-O. The 20-day volatility target (macro R-06) is the robust protective workhorse; KOSPI floored trend x VT20 runs as FORWARD-SIM; trend alone has protective weight 1 (its KOSPI evidence rests on 1997-2001); US single-index trend at 50 bp per side is REJECT, futures cost only, BACKLOG. Propose to the macro spec owner: R-14 gets a CARD-P cell and a speed cell.

Applied: TF-30 (IDX-0 class rule), TF-31 (IDX-1 = R-06), TF-32 (FS-1), TF-33 resolved as a class rule, TF-34 (DNB-TF-05 at 50 bp; BL-TF-08 at futures cost); KOSPI trend alpha 0 / protective 1, VT20 2, floored product 2; XS-09.

> CR-03 Korean short-term reversal and investor flows (MC-08, MC-09): this programme owns signal-family weights; the macro spec deferred reversal to its own net-of-cost test, which now fails. Korea ST-reversal alpha 3 -> 0 (daily/weekly DROP; monthly reversal only as a conditioning guard of weight 1: do not buy last month's top-decile winners). Korea investor flow 3 -> 1 (log flows now with timestamps; no direction rule; t-1 history required). Record these as supersessions of macro R-15 / §2.2 for the owner to confirm.

Applied: TF-41 CORE-PROHIBITION (DNB-TF-07); TF-42 guard as FS-5; TF-39 flow direction CORE-PROHIBITION (DNB-TF-06); TF-40 flow logging as DATA-6; XS-01, XS-02 recorded as supersessions.

> CR-04 Korean value, quality, earnings drift: individual weights 1 until a point-in-time OpenDART test exists (INSUFFICIENT DATA today); one pre-registered KR-VQ composite (value + profitability + net issuance) carries weight 2 as a BUILD-candidate pending the PIT store. US: US-VQ composite weight 2 pending FMP/EDGAR PIT data; US PEAD standalone DROP.

Applied: TF-36 (KR-VQ, weight 2, BL-TF-10), TF-37 and TF-38 (weights 1), TF-43 (US-VQ, weight 2, BL-TF-12), TF-45 (US PEAD and event drifts, DNB-TF-09).

> CR-05 Korean momentum: raw 12-1 card DROP (alpha 0). A constrained variant (12-1 or 12-7, excluding the highest-turnover/lottery names, own-vol-scaled, capped, long-only) is a FORWARD-SIM card at weight 1; momentum sleeves in every market get macro R-03 vol scaling as a risk control; the Daniel-Moskowitz gate (R-04) stays on the specification book only.

Applied: TF-20 (DNB-TF-04), TF-21 (FS-2), TF-22 (MOM-1), TF-23 (MOM-2 spec book only); SCR-3 construction rule; XS-10, XS-15, XS-18.

> CR-06 Exclusion screens: the lottery composite (volatility + MAX + turnover) and the net-issuance/dilution screen are BUILD NOW as screen cards gated as CARD-O against the unscreened base book on the same days (no new class needed), declared per book type: weight 3 on equal-weighted and small/mid books, 1 (hygiene) on capped cap-weighted books, 0 for the top-200 book (REJECT there). The attention-fade event screen is DROP as a monthly screen but becomes an execution INVARIANT: never enter at a locked limit-up close.

Applied: TF-12 (SCR-1), TF-13 (SCR-2), TF-15 (SCR-3); TF-14 moved from ONE-SIDED to CORE-PROHIBITION (DNB-TF-01) with its entry-day part in INV-2.

> CR-07 Drawdown ladder (MC-01..MC-05, MC-16): this programme does not change macro R-07 thresholds. It proposes answers to the macro backlog's open points for the owner: steps non-cumulative; applied to total book NAV only; re-arm at 0.5 with the reference peak reset; caps by book type (0.05 single name in selection sleeves; 0.35 pair cap on look-through for market/ETF books); one pre-registered pair-share denominator: numerator = market cap of 005930 + 005935 + 000660, denominator = total market cap of all KOSPI-listed shares in the KRX daily all-stock file (compute the 2026-09-29 value from /home/claude/data_raw/marcap/data/marcap-2026.parquet and report alternatives). Threshold units (fixed % vs book-volatility units, or a book-vol ceiling) are an owner decision: record the evidence (P(-15% within 10 years) 0.97 at 12% vol and Sharpe 0.5; 0.66 at 8%).

Applied: Pair share computed (section 11.1): 53.71% on 2026-09-29; TF-26 (RISK-1), TF-27 (XS-08 proposal), TF-28 (OQ-01); XS-06, XS-07, XS-22.

> CR-08 Gate amendments: tightening or reporting only, never loosening: block length max(10, Politis-White on d and d^2) for steps 2 and 5 on every card (10-session blocks gave 7-8% / 13% false passes at nominal 5% / 10%); a family gate (Hansen SPA or StepM within a technical-rule family; BH-FDR across a release, reported); a trial registry with a global N for the deflated Sharpe; an attribution block on every card (beta, Jensen's alpha with Newey-West t, FF5+Mom for US cards, local KRX factors for Korea; "factor tilt" label when alpha disappears); long-only primary statistic and declared benchmark for KRX cards; S_beta comparator (CR-01); a break-even pre-gate screen (reject before the gate if break-even per-side cost < 2x the pre-registered cost); step 8 and step 9 unchanged (report step 8's stand-alone weakness; an alpha-only haircut may be printed as an extra line).

Applied: GOV-1..GOV-7 and GOV-11 (TF-06, TF-07, TF-50, TF-51, TF-53, TF-55, TF-59); TF-50 moved from ONE-SIDED to CORE-LINK; tiered hurdles (TF-52) and the Jensen-alpha step-5 variant are not adopted (OQ-05, OQ-10); XS-11, XS-13.

> CR-09 Execution conventions are INVARIANTS: decide at the close t; fill at the KRX official close t (bound: close t+1); never NXT/after-hours prints; locked limit-up: no entry; locked limit-down exits carry to the first unlocked session at 2x cost; VI/circuit-breaker/halt days unfillable; no name-level stops (signal exits; stops on trend sleeves only via the signal); corporate-action-adjusted returns with |Δln shares| > 1% flagged; capacity <= 1-2% of 20-day ADV; buy/hold bands and a turnover limit.

Applied: INV-1..INV-5 (TF-01, TF-02, TF-03, TF-08, TF-10).

> CR-10 Crypto: C3 stays PASS; add a vol-scaled long-only control, a pre-registered split at the US spot-ETF date (2024-01-10) and an ETH replication; crypto short-term reversal 2 -> 0 (short-horizon crypto evidence is momentum); CTREND-lite technical composite BACKLOG.

Applied: TF-67 (CRY-1), TF-68 (DNB-TF-16), TF-69 (BL-TF-19); XS-17.

> CR-11 ML: an equal-weight z-score composite is the baseline combiner (BUILD with the first composite card); a ridge/Fama-MacBeth challenger shrunk to priors runs FORWARD-SIM; gradient boosting and small nets BACKLOG; deep price-pattern, order-book and LLM-news strategies DROP; macro variables never interact with stock signals.

Applied: TF-63 (ML-1 and FS-4), TF-64 (BL-TF-18), TF-65 (DNB-TF-14); TF-66 moved from ONE-SIDED to CORE-PROHIBITION (DNB-TF-15).

> CR-12 Valuation timing (CAPE, Fed model, forward P/E) is CONTEXT only; classic technical index-timing rules (RSI, MACD, Bollinger, Donchian, golden/dead cross, candlesticks, Fibonacci, Elliott, chart patterns, TradingView-sourced strategies) are DO-NOT-BUILD as signals unless they pass the family gate and the nine-step gate as a new card.

Applied: TF-48 (DNB-TF-11, CONTEXT display), TF-60 (DNB-TF-12).

## 3. Method

**Inputs, in order.** 00_QUANTGEN_context.md; the two chair resolutions (R2_PROF, R2_EXEC); the claim matrices and verification logs (`r2/verification/`); the four lab summaries and their result CSVs (KR R1, US R1, R2 KR, R2 IDX, plus the exec chair checks c01-c12); the 14 round-1 papers only to look up wording or URLs; the macro spec v1.2 (project doc `claude/QUANTGEN_MACRO_INTEGRATION.md`) for conflicts and naming. Extracts are in `R3_working_notes.md` (sections A-H).

**Nodes.** Each node states one proposition, written so that a panel can support or refute it. Every proposition of both claim matrices (60 + 60) and every chair item (115) maps onto at least one node; a proposition maps as primary to one node and may map as secondary to others, either whole or by named claims (e.g. `X27:E7-C25,E5-C03`).

**Focus intensity fp / fe.** The number of distinct professor (fp) and executive (fe) claims mapped to the node: all ledger claims (supporting and qualifying, claim ranges expanded) of its primary propositions, plus only the named claims of secondary mappings, plus distinct non-ledger references. Chair and lab conclusions never add to fp or fe. Claims can sit on more than one node, so column totals exceed 209 / 205.

**Panel strength (ps, es).** Strong: a chair consensus item with three or more supporting members and verification MATCH (or chair re-computation). Moderate: one or two members, or consensus reached after qualification or cross-examination. Weak: one member, unverified or heavily qualified. Split: members disagree and the chair records a contested item. Silent: no claim from that panel. Refuted: the chair refuted or withdrew the item.

**Data column.** Supports: lab or chair re-computations agree with the node at QUANTGEN net costs. Mixed: some books, periods or designs agree and others do not, or only gross support exists. Refutes: the data contradict the node. Untested: no local data.

**Class rule, in order of precedence (checked mechanically; 0 mismatches between the stated and computed rule class):**
1. CORE-PROHIBITION: both panels Refuted, or one Refuted with data Refutes and the other Silent.
2. ONE-SIDED: one panel Silent (and rule 1 does not apply).
3. CORE-LINK: both panels Moderate or Strong, and data Supports or Mixed; if data Refutes the node is CONTESTED; if data is Untested for an empirical claim it is UNTESTED (design rules TF-04, TF-40 and TF-63 are exempt).
4. CONTESTED: a panel is Split, or the panels disagree (Refuted against Weak or better).
5. ONE-SIDED: Moderate or Strong against Weak; Weak against Weak with no data is UNTESTED.
Coordinator rulings override the rule where they speak; the three overrides are listed in section 4.

**Edges.** Four types: supports, refutes, qualifies, conflicts; each has a one-line reason with its evidence (Appendix B and R3_TF_edges.csv).

**Weight rules (0-3 priors; not gate results).** W1: a coordinator ruling decides where it speaks. W2: otherwise, if the panels agree, that value. W3: otherwise the lower panel value, unless lab data at QUANTGEN net costs support the higher one (the gate is never loosened). W4: a cell only one panel reviewed keeps that panel's value, flagged * (it cannot feed any book until a card passes). W5: cells no panel reviewed keep the prior, flagged n.r. Proposed normalisation for macro R-15: base_weight = w / 3, so a weight of 3 equals 1.0x and no weight implies a multiplier above 1.0.

**Golden values.** Read programmatically from the named file and row (`scripts/r3_03_golden_values.py`); "derived" values state their arithmetic; "not traced" values give the reason. Chair-resolution text lines used as sources are checked for the quoted string.

## 4. Node counts by class

| Class | Final | Rule-based (before rulings) | Nodes |
|---|---|---|---|
| CORE-LINK | 29 | 28 | TF-01, TF-02, TF-03, TF-04, TF-05, TF-06, TF-07, TF-08, TF-10, TF-11, TF-12, TF-13, TF-15, TF-22, TF-26, TF-30, TF-31, TF-32, TF-40, TF-42, TF-50, TF-51, TF-53, TF-54, TF-56, TF-58, TF-59, TF-63, TF-67 |
| CORE-PROHIBITION | 18 | 16 | TF-14, TF-17, TF-18, TF-19, TF-20, TF-34, TF-39, TF-41, TF-44, TF-45, TF-47, TF-48, TF-57, TF-60, TF-61, TF-65, TF-66, TF-68 |
| CONTESTED | 11 | 11 | TF-09, TF-16, TF-21, TF-23, TF-24, TF-29, TF-33, TF-37, TF-38, TF-55, TF-70 |
| ONE-SIDED | 8 | 11 | TF-25, TF-27, TF-28, TF-46, TF-49, TF-52, TF-62, TF-69 |
| UNTESTED | 4 | 4 | TF-35, TF-36, TF-43, TF-64 |
| Total | 70 | 70 |  |

Rulings that changed a class: TF-14 ONE-SIDED -> CORE-PROHIBITION (CR-06); TF-50 ONE-SIDED -> CORE-LINK (CR-08); TF-66 ONE-SIDED -> CORE-PROHIBITION (CR-11).

| Theme | Nodes | CORE-LINK | CORE-PROHIBITION | CONTESTED | ONE-SIDED | UNTESTED | fp (sum) | fe (sum) |
|---|---|---|---|---|---|---|---|---|
| A. Data hygiene and execution | 11 | 10 | 0 | 1 | 0 | 0 | 52 | 101 |
| B. Screens | 7 | 3 | 3 | 1 | 0 | 0 | 19 | 20 |
| C. Momentum and portfolio risk | 11 | 2 | 2 | 4 | 3 | 0 | 29 | 63 |
| D. Protective index rules | 6 | 3 | 1 | 1 | 0 | 1 | 14 | 39 |
| E. Fundamentals, flows and reversal | 14 | 2 | 6 | 2 | 2 | 2 | 84 | 93 |
| F. Governance and technical-rule standards | 13 | 7 | 3 | 1 | 2 | 0 | 97 | 49 |
| G. ML combiners | 4 | 1 | 2 | 0 | 0 | 1 | 28 | 7 |
| H. Crypto and FX | 4 | 1 | 1 | 1 | 1 | 0 | 19 | 3 |

## 5. CORE-LINK list (both panels support; data supports or is not contrary) -> integration spec

Each entry gives the node, focus intensity (fp, fe), panel strength, data, key numbers with sources, the chair items behind it and the destination; member claim IDs and URLs are in R3_TF_nodes.csv.

Spec destinations proposed for the Claude Code integration spec: section TF-1 execution invariants (INV-1..INV-5), TF-2 data (DATA-1..DATA-6), TF-3 screens (SCR-1..SCR-3), TF-4 momentum risk and concentration (MOM-1, MOM-2, RISK-1), TF-5 index protective rules (IDX-0, IDX-1), TF-6 fundamentals (FUND-1 KR-VQ and FUND-2 US-VQ, activated only when the point-in-time stores exist), TF-7 governance (GOV-1..GOV-11), TF-8 ML (ML-1), TF-9 crypto (CRY-1); FORWARD-SIM cells FS-1..FS-5. Proposed package placement, following macro section 3 (the integration spec decides): fills, costs and the gate in core/quant/backtest; screens and the composite in core/quant/signals (family tags); vol scaling, caps and the ladder in core/quant/risk (macro R-03, R-07); regime flags in core/calendars and the point-in-time data layer; card headers and pre-registration in core/rules; FORWARD-SIM cells in the third (forward) book, never in the displayed book.

### 5.1 Data hygiene and execution

**TF-01** (fp 0, fe 7; professors Moderate, executives Strong; data Supports). Decide at the close of t and fill at the KRX official close of t (conservative bound: close t+1; never NXT or after-hours prints); momentum and trend entries fill at the close because KRX momentum is earned overnight.

- Key numbers: KRX top-500 EW 12-1 D10-D1 2002-2026, gross: overnight +18.4%/yr (t 8.7) vs intraday -7.9%/yr (t -1.8); 2015-26 +26.0% vs -21.9% (exec row 21). US close auction deviation 8.1 bp average, >63 bp in 1% (exec row 20). NXT 9.1-10.6% of KRX volume 2025-26 (EC-T-03).
- Sources: exec_verification_log.csv rows 20-21 (c06 overnight test); R1/R2 engines decide at t, earn t+1
- Chair items: context rule 2; PROF 5.3 (decide at close t); PROF 5.1-7 next-open for holds <= 5 sessions (qualifies), EC-T-03, EC-T-26, RX-01, RX-02
- Destination: SPEC §TF-1 INV-1 (INVARIANT); ruling CR-09

**TF-02** (fp 1, fe 10; professors Moderate, executives Strong; data Supports). Locked-limit rules: no entry at a locked limit-up close; an exit at a locked limit-down close carries to the first unlocked session at 2x cost; VI, circuit-breaker and halt days are unfillable; locked limit-downs are excluded from reversal books.

- Key numbers: KRX 2015-06..2026-09, gross vs EW liquid universe: next-open buy after a locked limit-up -394 bp (t+5) / -579 bp (t+20), n 11,186, date-clustered t -14.6 / -11.2; locked limit-down -630 / -722 / -1,036 bp at t+1 / t+5 / t+20 (n 815); volume spike -43 / -93 bp; +50% run-up -95 bp at t+20. R2 audit (1996-2026): 6.3% of EW-book entries at a locked limit-up close, 2.1% of exits at a locked limit-down close; 1.9% / 1.4% with the F4 screen.
- Sources: exec_verification_log.csv rows 82-85 (c06d events); r2_kr_excl_limitlock.csv
- Chair items: PC-T-14 (no fills at locked limits), EC-T-03, RX-03, EX-T-04 (entry-day exclusion)
- Destination: SPEC §TF-1 INV-2 (INVARIANT); ruling CR-09, CR-06

**TF-03** (fp 2, fe 7; professors Strong, executives Strong; data Supports). Data hygiene for every card: eligibility and universe screens evaluated on data up to t-1; corporate-action-adjusted returns with |dln shares| > 1% flagged; monthly timing tests on month-end prices, never on Shiller month averages.

- Key numbers: KRX Eom design 2000-07..2019-06 gross, high-turnover W-L: +1.43%/month (t 3.3) on adjusted returns vs -11.37%/month on unadjusted closes (r2_kr_mom_claims_long.csv); unadjusted closes fabricate -136%/yr vs +17.1%/yr (EC-T-05). Same-day eligibility inflated an EW benchmark to +27.7%/yr vs +0.5%/yr lagged (exec row 86). SPY 1999-2021 month-average prices inflate Sharpe +0.10 (SMA10) and +0.23 (12-month sign); lag-1 autocorrelation 0.206 vs 0.057 month-end.
- Sources: r2_kr_mom_claims_long.csv; exec_verification_log.csv row 86; r2_idx_averaging_bias.csv; r2_idx_averaging_autocorr.csv; kr_validation.csv V1b
- Chair items: PC-T-14 (universe hygiene), PR-T-01 (mechanism), PC-T-23 (averaging bias), EC-T-05, EC-T-16, RX-05, RX-06
- Destination: SPEC §TF-2 DATA-1..3 (INVARIANT); ruling CR-09

**TF-04** (fp 3, fe 6; professors Strong, executives Strong; data Supports). Point-in-time fundamental and event layer: OpenDART data usable from the close of rcept_dt + 1 session with first-filed values; EDGAR acceptance <= 15:30 ET usable at close d, else d+1; delisting stress at -30% and -100%; forward archives (consensus, revisions, flows, quotes) start now.

- Key numbers: OpenDART full statements from business year 2015; rcept_dt is date-only; about 20,000 API calls/day (V051, exec row 77). EDGAR acceptance stamped to the second (exec row 76). KRX delisting bias bounded at 1.4%/yr for the worst quintile book (R1). A DART-only history detects IR >= 0.41-0.48 (EC-T-14).
- Sources: prof_verification_log.csv V051, V075; exec_verification_log.csv rows 76-77; kr_delisting_exposure_monthly.csv
- Chair items: PC-T-15, EC-T-14, RX-16
- Destination: SPEC §TF-2 DATA-4 (BUILD NOW (data layer))

**TF-05** (fp 8, fe 17; professors Strong, executives Strong; data Supports). Korean regime and event flags on every KRX card (short-sale regimes, the 2024-02-26 Value-up split, the sell-tax path, CB, insider pre-disclosure and cancellation reforms); the event layer may only exclude names or scale exposure to <= 1.0; regime-dependent event cards are INSUFFICIENT DATA until about 2028.

- Key numbers: Short-sale bans 2008-10-01..2009-05-31, 2011-08-11..11-09, 2020-03-16..2021-05-02 (index stocks only to 2023-11-05), 2023-11-06..2025-03-30; resumed 2025-03-31. Price limits +-30% since 2015-06-15. Sell tax 0.18% (2024), 0.15% (2025), 0.20% (2026). KOSDAQ up-limit closes 51.1 per 10,000 stock-days in 2026 vs 24.5-26.8 in 2024-25. Value-up plans +1.5% day 0, about +1% retained.
- Sources: prof_verification_log.csv V061, V062, V095; exec_verification_log.csv rows 18, 24, 78, 99
- Chair items: PC-T-12, PC-T-14, EC-T-05, EC-T-22
- Destination: SPEC §TF-2 DATA-5 (flags); event cards BL-TF-14 (BUILD NOW (flags); BACKLOG (event cards))

**TF-06** (fp 10, fe 8; professors Strong, executives Strong; data Supports). Every KRX stock card is gated on long-only net excess return against a pre-registered benchmark set (EW, CW, CW ex-pair, capped CW); long-short is a diagnostic only; EW and capped-VW results are reported together and a sign split means REVISE.

- Key numbers: KRX ALL EW 1996-2026, net 35 bp: L/S low turnover +23.1%/yr gross but best-quintile long-only excess +1.7% (t 0.9), low vol +1.1% (t 0.5), 12-1 -1.3% (t -0.6) (kr_key_numbers.csv lines 14, 10, 2). KOSPI H1-2026: CW +117.1% vs EW +3.4%, CW ex-pair +41.7%, 64.9% of names fell (exec row 91).
- Sources: kr_key_numbers.csv (LO vs LS legs); exec c09 breadth (exec_verification_log.csv row 91)
- Chair items: PC-T-02, PC-T-05, PROF 5.1-5, EC-T-06, RX-14
- Destination: SPEC §TF-7 GOV-1 (GOVERNANCE); ruling CR-08

**TF-07** (fp 10, fe 12; professors Moderate, executives Strong; data Supports). Every stock-level card prints an itemised cost header (commission, date-varying sell tax, half-tick floor, sqrt impact) and its break-even per-side cost; a card whose break-even is below 2x its pre-registered cost is rejected before the gate.

- Key numbers: KRX 1996-2026: weekly reversal L/S break-even 12.5 bp/side EW, 22.2 bp VW (gross/turnover); 12-1 L/S EW about 64 bp < 70 bp. Exclusion screens, break-even per side = gross diff / extra turnover: F4 380 bp (B1), F6 1,057 bp (B1), but F5 attention screen 68 bp (B1) -> rejected before the gate. KRX tick 5.1-25.8 bp (p1-p99); round-trip floor 25-46 bp with the 0.20% tax.
- Sources: kr_key_numbers.csv lines 30-31 (break-even); r3_golden_values.csv (derived break-evens)
- Chair items: PC-T-04 (break-even, DROP high turnover), EC-T-04, RX-08, RX-09
- Destination: SPEC §TF-7 GOV-7 (GOVERNANCE); ruling CR-08

**TF-08** (fp 10, fe 11; professors Strong, executives Strong; data Supports). Turnover discipline on monthly stock cards: buy/hold bands (enter the top 20%, exit below the top 40%), one-way turnover target <= 30%/month with a 50% hard limit, and capacity <= 1-2% of 20-day ADV.

- Key numbers: Average anomaly about 4 bp/month net after costs (Chen-Velikov, JFQA 2023, 204 anomalies). NMV US 1963-2012: banded value+momentum+profitability 1.02%/month net (t 6.19) with turnover cut 27% -> 11.6%. Cost drag at 35%/month one-way turnover: 2.94%/yr at 35 bp, 4.20%/yr at 50 bp. Capacity: impact not modelled in the labs (gap).
- Sources: kr_key_numbers.csv (turnover columns); NMV via prof_verification_log.csv V059
- Chair items: PC-T-04, EC-T-04, RX-07, RX-09
- Destination: SPEC §TF-1 INV-4 (INVARIANT); ruling CR-09

**TF-10** (fp 1, fe 8; professors Moderate, executives Strong; data Supports). No name-level stop-losses on KRX sleeves: exits come from the signal (trend sleeves stop through their own signal); hard stops are replaced by statistical review triggers that never auto-liquidate.

- Key numbers: KRX top-500 12-1 deciles 2000-01..2026-09, net 35 bp, 15% stop (close trigger, exit next close): EW Sharpe 0.04 -> -0.15; VW 0.28 -> 0.07; ALL quintiles EW 0.20 -> -0.20; 10% stop worse (r2_kr_stoploss.csv). Kaminski-Lo condition fails (monthly AR(1) -0.002 vs Sharpe 0.085).
- Sources: r2_kr_stoploss.csv; exec_verification_log.csv rows 56, 62, 71
- Chair items: PC-T-24/PM43 (stops only on trend sleeves; ATR as risk input), EC-T-09, ER-T-12, RX-04, RX-13
- Destination: SPEC §TF-1 INV-5 (review triggers: GOV option, exec-only) (INVARIANT); ruling CR-09

**TF-11** (fp 4, fe 8; professors Strong, executives Strong; data Supports). Every stock-level card reports a fixed stress-window table, including a replay of the winner-led 2026-06-22..07-30 Korean momentum crash, and its worst rolling 21/63-session and 5-week relative loss.

- Key numbers: KRX ALL EW, 2026-06-22..07-30, gross: 12-1 winners -36.6%, losers -13.0%, EW universe -18.2%, L/S -24.4%; top 200 winners -49.6%, losers -3.0%. July 2026 L/S -17.2% (ALL), -27.3% (top 500), -33.1% (top 200). US WML 1932 (-60.98% / -74.36%) and 2009 (-42.28% / -45.52%) were loser rebounds. MTUM -18.0% vs SPY -2.0% (2026-06-22..07-29).
- Sources: kr_event_windows.csv; r2_kr_crash_windows.csv
- Chair items: PC-T-10, PROF 5.1-11, EC-T-25, RX-15, ER-T-09 (anchor: GS basket -37% unverified)
- Destination: SPEC §TF-7 GOV-9 (GOVERNANCE (reporting))

### 5.2 Screens

**TF-12** (fp 7, fe 2; professors Strong, executives Strong; data Supports). Excluding the lottery composite (worst decile of volatility + MAX + turnover ranks) from equal-weighted, small/mid and momentum books adds a small, steady return net of costs; capped cap-weighted books get hygiene only and the top 200 nothing.

- Key numbers: KRX 1996-03..2026-09 (366 formations), filtered minus unfiltered: B1 EW +3.39%/yr gross, +3.08% net 35, +2.76% net 70 (IR 1.53, t 8.3, boot p 0.0005, 90% of years; 4.31 / 2.81 / 2.20%/yr by decade); B2 capped VW +0.85% net 35 (IR 0.68); B3 top 200 +0.49% (IR 0.39, REJECT); B4 momentum Q5 +6.13% (IR 1.24). Indicative gate B1/F4 7/8 steps (pooled DSR 0.94 over 176 trials) -> REVISE.
- Sources: r2_kr_excl_summary.csv, r2_kr_excl_gate.csv, r2_kr_excl_long.csv; kr_key_numbers.csv lines 10, 14
- Chair items: PC-T-07, EC-T-12
- Destination: SPEC §TF-3 SCR-1 (BUILD NOW (screen card)); ruling CR-06

**TF-13** (fp 2, fe 4; professors Moderate, executives Strong; data Supports). Excluding heavy issuers (252-session share growth > 10%: rights offerings, third-party allotments, CB/BW conversions) from equal-weighted and selection books pays after costs, but the effect is decaying and about zero on cap-weighted books.

- Key numbers: KRX 1996-03..2026-09: B1 EW +2.34%/yr net 35, +2.26% net 70 (IR 0.65, boot p 0.0005, 81% of years); 2016-26 +1.34%/yr (IR 1.43); B2 capped VW +0.69% (IR 0.15, p 0.24); B3 +0.29%; B4 +4.23% (IR 0.57). Chair c06 (2001-2026 net 35): heavy-issuer quintile -13.4%/yr (t -10.3); universe ex-Q5 +3.0%/yr (t 9.2). Long-only tilt IR 0.48-0.54 (not 0.84); 2017-26 0.35-0.38; about 0 at 70 bp in 2017-26. Issuance-event 12-month BHAR -25.3% size-matched (2005-14 -34.4%, 2015-24 -17.6%).
- Sources: r2_kr_excl_summary.csv (F6); prof_verification_log.csv V046-V048, V114; exec_verification_log.csv rows 53, 79, 81
- Chair items: PC-T-13, PR-T-11, EC-T-13
- Destination: SPEC §TF-3 SCR-2 (BUILD NOW (screen card)); ruling CR-06

**TF-15** (fp 1, fe 3; professors Moderate, executives Strong; data Supports). Excluding the highest-turnover or lottery names is a mandatory construction rule for any Korean momentum or small-cap long-only sleeve.

- Key numbers: KRX 1996-2026, net 35: inside the 12-1 top quintile (B4) F1 +7.81%/yr (IR 1.02, t 6.2), F4 +6.13%/yr (IR 1.24, t 7.5); B4 Sharpe 0.18 -> 0.45 (F1). High-turnover 12-1 winners minus EW universe -11.6%/yr (t -4.2); low-turnover +9.7%/yr (t 2.8).
- Sources: r2_kr_excl_summary.csv (B4); r2_kr_mom_grid_long.csv
- Chair items: PC-T-09 (any momentum book must exclude highest-turnover/lottery names), EC-T-12 (B4 construction rule), EX-T-05
- Destination: SPEC §TF-3 SCR-3 (construction rule inherited by MOM sleeves) (BUILD NOW (construction rule)); ruling CR-05, CR-06

### 5.3 Momentum risk and concentration

**TF-22** (fp 4, fe 9; professors Strong, executives Strong; data Supports). Own-volatility scaling (macro R-03: sigma126, 12% target, cap 1) is a risk control for every momentum sleeve in every market, including KRX; it is not a general Sharpe booster (the prior "+0.1 to +0.3 on nearly every strategy" is withdrawn).

- Key numbers: KRX 12-1 L/S ALL quintiles 1996-2026 net 35: Sharpe EW 0.20 -> 0.27, VW 0.25 -> 0.31; VW max DD -74% -> -44%; weights on 2026-06-22 0.55 (EW) / 0.27 (VW); crash window VW -10.5% vs -40.3% static and -22.9% for a static book at the same average exposure; 2016-26 Sharpe lower (EW -0.20 -> -0.24; VW 0.32 -> 0.23). Scaling hurts reversal (KR STR EW net -0.29 -> -0.59). US French Mom 1949-2017/03: 0.62 -> 0.77.
- Sources: r2_kr_crash_controls.csv, r2_kr_crash_windows.csv, r2_kr_crash_exposure_2026.csv
- Chair items: PC-T-10, PR-T-16, EC-T-07, ER-T-10, RX-11
- Destination: SPEC §TF-4 MOM-1; cross-spec XS-10 (R-03 scope) (BUILD NOW (risk control)); ruling CR-05

**TF-26** (fp 1, fe 11; professors Moderate, executives Strong; data Supports). Korean concentration caps are set by book type (single name <= 5% of NAV in selection sleeves, VW legs capped at 5%, sector bands; pair cap 0.35 on look-through for market/ETF books when the pair share exceeds 0.45; semis <= 0.50) and use one pre-registered pair-share denominator.

- Key numbers: CR-07 pair share (005930+005935+000660 over all KOSPI lines) 53.71% on 2026-09-29 (alternatives 50.82% / 52.59% / 53.96%); first above 0.45 on 2026-05-06; peak 59.69% on 2026-06-25; 99 of 181 sessions above 0.45 in 2026. End-2023: 29.29% (CR-07), 26.88% / 27.79% (not 22%). Pair cap 0.35 on KOSPI CW cost -15.0 pp in the melt-up, saved +4.6 pp in the crash, -2.2 pp 2026 YTD (c07). A 5% name cap cuts VW WML 2016-26 net Sharpe 0.30 -> 0.02.
- Sources: exec_chair_checks/c04_concentration_stdout.txt, c07_stdout.txt; r3_pair_share.csv
- Chair items: PC-T-14 (capped and ex-pair benchmarks), PC-T-09 (caps on momentum), corrected anchor (state date and denominator), EC-T-11, EC-T-06, ER-T-08, MC-04, MC-05
- Destination: SPEC §TF-4 RISK-1; cross-spec XS-06, XS-07, XS-22 (INVARIANT (owner to confirm cap scope and denominator)); ruling CR-07

### 5.4 Protective index rules

**TF-30** (fp 4, fe 10; professors Strong, executives Strong; data Supports). Single-index trend is a protective tool judged as CARD-P, never an alpha card (alpha 0); on KOSPI its protective weight is 1 because its evidence rests on 1997-2001; macro R-14 should gain a CARD-P cell and a venue-dependent speed cell.

- Key numbers: KOSPI 303 timing rules 1996-2026 (3 bp): Hansen SPA consistent p 0.880; SMA200 CAGR 8.1% vs 7.2% but mean excess -1.1%/yr (t -0.3). R2 (3 bp): multi-speed trend sleeve PASS on 1996-09..2026-09 (PC-1 +8.9 pp) but REJECT from 2011 and 2016 starts; SMA200 and 12-month sign INSUFFICIENT DATA (16 and 11 onsets); trend fully long into the 2026 crash (-31.3% to -38.6%). Venue: 12-month sign PC-1 +4.7 pp vs multi-speed +8.9 pp at 3 bp.
- Sources: kr_index_spa.csv; r2_idx_protective_scorecard.csv; r2_idx_start_date_sensitivity.csv; r2_idx_outperformance.csv
- Chair items: PC-T-22, PC-T-23, EC-T-15, EX-T-02, MC-06
- Destination: SPEC §TF-5 IDX-0 (class rule); cross-spec XS-09 (R-14) (GOVERNANCE (class rule)); ruling CR-02

**TF-31** (fp 1, fe 2; professors Strong, executives Strong; data Supports). The KOSPI 20-day volatility target (macro R-06, VT20) is the robust protective workhorse: it passes the protective class over 1996-2026 and from every start up to 2006.

- Key numbers: KOSPI rebuilt 1996-09-02..2026-09-29, KRX ETF 3 bp: dMDD vs S +6.5 pp (+6.4 at 2x), tail ratio 0.70, dSR -0.001 (p_ni 0.051, block 186), 6 of 13 episodes (largest 38%), 70% of years, plateau 1.00 -> PASS; PASS from the 1996-06 .. 2006 starts (PC-1 +4.4 to +11.6 pp), INSUFFICIENT from 2011/2016; spec 2016-26 golden values reproduced 30/30; crash 2026-06-22..07-30 -12.2% vs -38.6%; fails CARD-O step 5 (p 0.51).
- Sources: r2_idx_protective_scorecard.csv; r2_idx_start_date_sensitivity.csv; r2_idx_golden_values.csv; r2_idx_r4b_crosscheck.csv
- Chair items: PC-T-23 (protective 2), EC-T-15, MC-17
- Destination: SPEC §TF-5 IDX-1 (= macro R-06, unchanged) (BUILD NOW (macro R-06; CARD-P)); ruling CR-02

**TF-32** (fp 0, fe 3; professors Moderate, executives Strong; data Supports). On the KOSPI ETF line, trend floored to [0.5, 1] and multiplied by VT20 is the credible equity protective cell and should run as a FORWARD-SIM CARD-P (unbounded product as comparison).

- Key numbers: KOSPI 1996-09..2026-09, 3 bp: clip[0.5,1](trend) x VT20 average exposure 0.61, max DD -29.4%, dMDD vs own S +15.4 pp, tail 0.64, dSR +0.156, 63% of years -> PASS (plateau and start-date sweep not evaluated); unbounded trend x VT20 +11.3 pp, tail 0.55, 57% of years -> REVISE, and REJECT from 2011 starts; 2026 crash -9.8% vs -38.6%.
- Sources: r2_idx_overlay_vs_sleeve.csv; r2_idx_windows.csv
- Chair items: PC-T-23 (flagged: floored trend x VT passed every check), EC-T-15, EX-T-01
- Destination: FS-1 (FORWARD-SIM); ruling CR-02

### 5.5 Fundamentals, flows and reversal (no fundamental composite reaches CORE-LINK: both are UNTESTED, section 7)

**TF-40** (fp 2, fe 3; professors Moderate, executives Strong; data Untested). Log final KRX investor-type flows with timestamps from now, so that a t-1 history exists for an open-leg test; no flow direction rule.

- Key numbers: Design rule; flow weight 3 -> 1 (CR-03). Flow autocorrelation 0.43 and impact 0.119 (t 11.9), permanent (Richards).
- Chair items: PC-T-34 (log as state variable; open-leg test BACKLOG), EC-T-23 (log flows now)
- Destination: SPEC §TF-2 DATA-6 (BUILD NOW (logging)); ruling CR-03

**TF-42** (fp 5, fe 7; professors Moderate, executives Moderate; data Mixed). A monthly reversal guard (do not buy last month's top-decile winners) is worth keeping as a weight-1 conditioning input.

- Key numbers: KRX 1-month reversal EW deciles 1996-2026 +1.43%/month gross (t 3.1) but VW ex-microcap +0.57% (t 0.9) and about 0 after 2005; the guard itself was not tested as an exclusion screen.
- Sources: r2_kr_reversal.csv; kr_key_numbers.csv line 6
- Chair items: PC-T-06 (keep the guard; protective 1), EC-T-02 (monthly reversal 1 as conditioning)
- Settling test: R2-style horse race: exclude last month's top-decile winners from B1 and B4 at 35/70 bp; keep only if it adds to SCR-1.
- Destination: FS-5 (screen variant, gated like SCR-1) (FORWARD-SIM (screen variant)); ruling CR-03

### 5.6 Governance

**TF-50** (fp 12, fe 0; professors Strong, executives Silent; data Supports). Every card carries an attribution block: beta, Jensen's alpha against a beta-matched benchmark with Newey-West t, FF5+Mom for US cards, local KRX factors (incl. a Samsung/SK hynix SEMI factor) for Korea, and a "factor tilt" label when alpha disappears; beta itself is a risk tool, not a signal.

- Key numbers: US 1954-2017/03 Fama-MacBeth beta slope +0.46%/yr (t 0.17) vs market 7.2%/yr; KR 1997-2026 +1.1%/yr (t 0.19) vs 10.9%; GRS rejects CAPM, FF3 and FF3+Mom (p < 0.01); KR low-vol Q1 CAPM alpha +2.2% (t 0.8) -> "factor tilt / no alpha".
- Sources: us_C_factors.csv (FM slope, GRS); r2_kr_lowvol.csv; prof_v09 (V002)
- Chair items: PC-T-01
- Destination: SPEC §TF-7 GOV-3 (GOVERNANCE (BUILD NOW)); ruling CR-08

**TF-51** (fp 10, fe 1; professors Strong, executives Moderate; data Supports). Multiplicity control: a family gate (studentised SPA / Reality Check with StepM or Romano-Wolf inside a rule family), Benjamini-Hochberg FDR across a release (reported), and a trial registry with a global N for the deflated Sharpe.

- Key numbers: KOSPI 303 rules SPA p 0.880; SPY 322 rules 0.82-0.97 (0 of 322 beat SPY after 2010); best of 176 R2 exclusion trials DSR 0.979 pooled, B1/F4 0.94 -> REVISE; 34 cards at p <= 0.10 imply about 3.4 false passes if all null; C3 fails Bonferroni across 16 trading cards (0.006) on p 0.04 but its Sharpe t 3.49 survives.
- Sources: kr_index_spa.csv; us_B_family.csv; r2_kr_excl_gate.csv, r2_kr_excl_trials.csv
- Chair items: PC-T-31, PROF 5.1-1..3, EC-T-28 (count MA/TSMOM variants as one family; pre-register <= 4-5 features)
- Destination: SPEC §TF-7 GOV-2 (GOVERNANCE (BUILD NOW)); ruling CR-08

**TF-53** (fp 2, fe 0; professors Strong, executives Moderate; data Supports). Gate steps 2 and 5 use bootstrap blocks of max(10, Politis-White on d and d^2) sessions on every card, not 10-session blocks.

- Key numbers: KOSPI-bootstrap innovations, true Sharpe 0, 10-session blocks: step 2 false-pass 8.0% (10 y) / 6.9% (18 y) vs 5.0% with the dependence removed; step 5 with no edge 13.7% / 12.8% / 13.2% (10/18/30 y) at nominal 10%.
- Sources: r2_idx_gate_sim.csv; r2_idx_gate_step5_calibration.csv
- Chair items: PC-T-31, PROF 5.1-10, MC-18
- Destination: SPEC §TF-7 GOV-4; cross-spec XS-11 (GOVERNANCE (BUILD NOW)); ruling CR-08

**TF-54** (fp 4, fe 5; professors Strong, executives Strong; data Supports). The gate is structurally underpowered for realistic tilts: never loosen it, report the minimum track-record length, and return INSUFFICIENT DATA (not REJECT) when it exceeds the history.

- Key numbers: True Sharpe 0.4 passes step 2 half the time after 15.8 years and 80% after 40.3 (KOSPI bootstrap); Sharpe 0.5 with 9 counted trials needs 39.5 years for 50% at step 3; IR 0.3 vs a 0.4-Sharpe benchmark passes step 5 half the time after about 18 years, 80% only near 50; joint false pass of steps 2+3+5+8 at Sharpe 0 is 0.5% at 10 years.
- Sources: r2_idx_gate_sim.csv; r2_idx_gate_power_years.csv
- Chair items: PC-T-32, EC-T-28
- Destination: SPEC §TF-7 GOV-5 (GOVERNANCE); ruling CR-08

**TF-56** (fp 8, fe 14; professors Strong, executives Strong; data Supports). Published and bank/asset-manager backtest numbers are haircut once per stage before they become priors, and planning haircuts are replaced by measured local decay where 20+ years of data exist.

- Key numbers: US: -26% out of sample, -58% post-publication (97 predictors); only the US declines reliably (241 anomalies, 39 markets). KRX local decay: 1-month reversal 1.12 / 0.27 / 0.08%/month (2001-09 / 2010-19 / 2020-26, gross); issuance L/S Sharpe 1.14-1.20 -> 0.71-0.74. AQMIX 10-year Sharpe about 0.30 vs a 1.21 bank backtest. One haircut per stage: E1 prior 0.26 x 0.51 = 0.13; x0.6 only on a card's own OOS.
- Sources: prof_v01/v03 (V031, V048, V084); exec rows 7, 14, 52
- Chair items: PC-T-03, PX-T-10, PR-T-12 (anchor: 4 bp not 8 bp), EC-T-28, EX-T-12
- Destination: SPEC §TF-7 GOV-8 (prior calibration) (GOVERNANCE)

**TF-58** (fp 2, fe 0; professors Moderate, executives Moderate; data Supports). Validation design: keep a contamination log of every family and date range the labs examined, treat the historical holdout as used up for those families, and use prospective incubation (FORWARD-SIM, >= 252 sessions from 2026-10-01) as the clean out-of-sample test; CPCV is reported, not gating.

- Key numbers: The R1/R2 labs examined 1996-2026 for 12-1, 6-1 and 12-7 momentum, 1-month and weekly reversal, volatility, MAX, turnover, 52-week high, price/SMA200, RSI, %B and more than 600 index rules; CPCV advantage shown only on synthetic data (P4-C08, unverified).
- Sources: R1/R2 lab coverage (1996-2026 for MOM, REV, VOL, MAX, TURN, 52wH, RSI, %B, >600 index rules)
- Chair items: PX-T-06 (chair ruling), FORWARD-SIM triage throughout (P7 forward book)
- Destination: SPEC §TF-7 GOV-10 (GOVERNANCE)

**TF-59** (fp 3, fe 3; professors Strong, executives Strong; data Supports). Protective claims are judged on the CARD-P checks against a static comparator with the same average exposure (S for exposure rules; the same-beta static book S_beta for stock-level sleeves), never on step-5 outperformance alone.

- Key numbers: KOSPI VT20 fails CARD-O step 5 (dSR -0.001, p 0.51) yet passes CARD-P (dMDD +6.5 pp vs S); KR low-vol beats the market in crashes but not S_beta (dMDD -7.1 to -22.4 pp; tail 0.97-0.99).
- Sources: r2_idx_protective_scorecard.csv; r2_idx_outperformance.csv; exec_chair_checks/c12_lowvol_samebeta.csv
- Chair items: PROF 5.1-10a, EC-T-15 (class rule), MC-11
- Destination: SPEC §TF-7 GOV-11; cross-spec XS-12 (§8.7 S_beta) (GOVERNANCE (BUILD NOW)); ruling CR-01, CR-08

### 5.7 ML

**TF-63** (fp 4, fe 5; professors Strong, executives Moderate; data Untested). The baseline combiner is an equal-weight z-score composite with signs fixed in advance (L0); a ridge/Fama-MacBeth challenger shrunk toward L0 runs forward only (L1), inside an ML harness (purge/embargo >= 63 sessions, <= 12 configurations per family).

- Key numbers: Detecting a +0.10 Sharpe uplift over an EW composite needs 27 / 54 / 108 years at correlations 0.95 / 0.90 / 0.80; 1-month-horizon ML has netted about 0 since 2004.
- Sources: prof_verification_log.csv V076 (power), V071
- Chair items: PC-T-30, EC-T-14 (small composite core), EC-T-28
- Destination: SPEC §TF-8 ML-1 (L0 with the first composite card); FS-4 (ridge) (BUILD with the first composite card (L0); FORWARD-SIM (L1)); ruling CR-11

### 5.8 Crypto

**TF-67** (fp 6, fe 2; professors Strong, executives Moderate; data Supports). Keep crypto trend card C3 (PASS) and add a vol-scaled long-only control, a pre-registered split at the US spot-ETF date (2024-01-10), an ETH replication and a daily cut-time sensitivity test.

- Key numbers: C3 KRW-BTC: OOS Sharpe 1.22 [0.62, 1.77] vs buy-and-hold 0.79, p 0.04, 1.17 at 2x costs, 13.7x/yr (QUANTGEN 2026-09-27); BTC-USD 1.19 vs 0.89, p 0.07. Bitcoin 2010-07..2018-01: price-to-MA OOS R2 1.17-3.66%; break-even one-way cost 1.12-3.96%.
- Sources: QUANTGEN gate record (00_QUANTGEN_context.md line 28); no local crypto data
- Chair items: PC-T-27, X36 (E3), weight table 5.3
- Destination: SPEC §TF-9 CRY-1 (governance additions to C3) (KEEP + GOVERNANCE); ruling CR-10

## 6. CORE-PROHIBITION list -> DO-NOT-BUILD

Each entry states the refuted proposition. DNB-TF ids are proposed additions to macro section 10 (overlaps noted in XS-19). TF-19 and TF-57 are anchors that must not propagate (section 12).

**Anchor / TF-19** (fp 8, fe 1; professors Refuted, executives Refuted; data Refutes). Refuted proposition: The context brief's Korean anchors hold as stated: 1-month reversal "-2.95%/month (t -3.77)" and 12-1 momentum "negative in high-turnover stocks (-6.13%/month)".

- Key numbers: -2.950 is a Fama-MacBeth slope on r(-1) (about -0.30% next month per +10% last month), Jan-1999..Feb-2021. Measured EW decile spread 1999-2021 +1.41%/month gross, +0.20% net 35 (R1). KJFS -6.13%/month not reproduced: adjusted returns +1.43%/month (t 3.3) all caps, +1.66% ex-bottom-20%; the sign appears only with unadjusted closes (-11.37%/month), driven by capital reductions on 0.09% of stock-days.
- Sources: r2_kr_mom_claims_long.csv; kr_crosschecks.csv; prof_verification_log.csv V082-V083, V086-V087, V110
- Chair items: PR-T-01, PR-T-02, ER-T-07, ER-T-11
- Destination: Corrected anchors CA-01, CA-02; cross-spec XS-02 (DROP (anchors))

**Anchor / TF-57** (fp 2, fe 0; professors Refuted, executives Silent; data Refutes). Refuted proposition: The per-factor out-of-sample haircuts "value -49%, momentum -23%, multifactor -18%" are verifiable from Ilmanen et al. (2021).

- Key numbers: AQR's article page reports only an average 30% out-of-sample drop and no factor-specific figures (V107 UNVERIFIABLE). Planning values: 0.5 (in sample / overlapping) or 0.3 (fully post-publication); 0.75 for drift-like signals.
- Sources: prof_verification_log.csv V107 (source check)
- Chair items: PR-T-13, PX-T-10
- Destination: Corrected anchor CA-04; cross-spec XS-05 (R-15, §7 prior_haircuts, §13 N-60) (DROP (anchor))

**DNB-TF-01 / TF-14** (fp 0, fe 4; professors Silent, executives Split; data Refutes). Refuted proposition: An attention-fade screen (exclude names with a volume spike, locked limit-up or +50% run-up in the last 20 sessions) works as a monthly exclusion screen or standalone card (E7 rank 1, weight 3).

- Key numbers: KRX 1996-2026: B1 F5 +1.40%/yr net 35 but -0.08% net 70 (IR 0.49), break-even 68 bp/side < 70 bp; B2 -0.35%, B3 -0.54%; adding F5 to F4 (F8) lowers IR 1.53 -> 0.67; a 20-session memory flags about 23% of names.
- Sources: r2_kr_excl_summary.csv (F5, F8); r3_golden_values.csv (F5 break-even)
- Chair items: EX-T-04 (dissent E7)
- Destination: DNB-TF-01 (monthly screen); INV-2 (entry-day exclusion) (DROP as screen; INVARIANT at entry); ruling CR-06

**DNB-TF-02 / TF-17** (fp 3, fe 3; professors Refuted, executives Refuted; data Refutes). Refuted proposition: A low-volatility or low-beta tilt is a long-only alpha source in Korea (prior weight 2).

- Key numbers: KRX 1996-2026 net 35: low-vol top quintile long-only excess +1.1%/yr EW (t 0.5), -1.8% VW (t -0.6); VW tilt -40.1 / -44.1 points vs the VW universe in 2025 / 2026 YTD; Korean SML 1997-2026 flat (+1.1%/yr, t 0.19); low-beta raw alpha -1.0%/yr (t -0.26) EW.
- Sources: kr_key_numbers.csv lines 10-11; r2_kr_lowvol.csv; prof_v09 (V002)
- Chair items: PC-T-08, PR-T-05, EX-T-06 (alpha 0-1, "not alpha")
- Destination: DNB-TF-02 (DROP); ruling CR-01

**DNB-TF-03 / TF-18** (fp 2, fe 1; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Size (small minus big) is a usable return signal in Korea or the US.

- Key numbers: KRX size L/S EW gross Sharpe 0.39 (1996-2026) but -0.05 in 2016-26; -26.9% (2025) and -26.5% (2026 YTD); top 200 -0.23. Korea SMB 2002-15 0.16%/month (t 0.45). US SMB 1981-2018 1.1%/yr (t 0.6).
- Sources: kr_key_numbers.csv lines 18-19; KR_datalab_summary.md; us_C_factors.csv
- Chair items: PC-T-11, EC-T-27 (size tilts DROP)
- Destination: DNB-TF-03 (size stays a risk control and attribution factor) (DROP)

**DNB-TF-04 / TF-20** (fp 3, fe 5; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Raw Korean 12-1 momentum is a viable standalone stock card at 35 bp per side.

- Key numbers: KRX ALL quintiles 1996-2026: L/S EW +9.3%/yr gross (Sharpe 0.45), net 35 Sharpe 0.20, net 70 -0.04, 2016-26 net -0.20; long-only excess -1.3%/yr (t -0.6); break-even about 64 bp/side. Top-500 deciles 2000-26: EW net Sharpe 0.04; VW 0.28, but 0.02 in 2016-26 with a 5% name cap.
- Sources: kr_key_numbers.csv line 2; r2_kr_mom_grid_long.csv; r2_kr_crash_controls.csv
- Chair items: PC-T-09, EC-T-08, ER-T-06
- Destination: DNB-TF-04 (DROP); ruling CR-05

**DNB-TF-05 / TF-34** (fp 1, fe 5; professors Refuted, executives Refuted; data Refutes). Refuted proposition: US single-index trend or volatility targeting on SPY is a viable protective card at QUANTGEN's 50 bp per side (prior US TS-mom weight 3).

- Key numbers: SPY 1999-05..2021-03 at 50 bp: multi-speed trend REJECT (PC-1 -10.7 pp), VT15 REJECT (+0.3 pp), trend x VT REJECT (-7.9 pp); SMA200 and 12-month sign INSUFFICIENT (REJECT if sufficient); trend turnover 7.3-11.9 units/yr costs 3.7-6.0%/yr. At 5 bp all INSUFFICIENT (PC-1 +3.8 to +14.7 pp; 53-56% of the benefit from the GFC). SPY SMA200 Sharpe 0.39 gross -> 0.07 at 50 bp.
- Sources: r2_idx_protective_scorecard.csv (SPY rows); us/results/us_B_daily.csv
- Chair items: PC-T-23 (SPY at 50 bp every rule fails), EX-T-03, MC-13
- Destination: DNB-TF-05 (at 50 bp); BL-TF-08 (futures-cost instrument) (DROP at 50 bp; BACKLOG at futures cost); ruling CR-02

**DNB-TF-06 / TF-39** (fp 2, fe 3; professors Refuted, executives Refuted; data Untested). Refuted proposition: Korean foreign/institutional net buying is a close-to-close direction signal (prior weight 3).

- Key numbers: 2003-11: lagged foreign/institutional buying negative for the next close-to-close return, positive for the next close-to-open; copying foreign buying underperformed KOSPI 2004-10. Foreigners sold KRW148.3tn net in H1 2026 while KOSPI rose about 101%; they bought +KRW231.2bn on the -12.06% day (2026-03-04).
- Sources: no t-1 flow history; exec_verification_log.csv row 95 (KEIA, Korea Herald)
- Chair items: PC-T-34, PR-T-07, EC-T-23, ER-T-05, MC-08
- Destination: DNB-TF-06; cross-spec XS-01 (DROP (direction rule)); ruling CR-03

**DNB-TF-07 / TF-41** (fp 11, fe 7; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Korean stock-level short-term reversal (daily, weekly or 1-month, with or without the 5d/20d volume filter) is a viable alpha card at 35 bp per side (prior weight 3).

- Key numbers: KRX 1996-2026: weekly reversal L/S +19.9%/yr gross (Sharpe 0.99) at 159x/yr turnover, net 35 Sharpe -1.78 EW / -0.82 VW, break-even 12.5 / 22.2 bp; volume-filter designs -0.92 to -1.33%/week net; 1-month reversal VW ex-microcap deciles +0.57%/month gross (t 0.9), -0.68% net 35, negative net in every sub-period after 2005; EW deciles +1.43% gross, +0.23% net (t 0.5).
- Sources: kr_key_numbers.csv lines 6-7, 30-37; r2_kr_reversal.csv; prof_v04_weekly_reversal.csv
- Chair items: PC-T-06, PR-T-03, PR-T-09, EC-T-02, ER-T-05, MC-09
- Destination: DNB-TF-07; cross-spec XS-02, XS-03, XS-04 (DROP); ruling CR-03

**DNB-TF-08 / TF-44** (fp 8, fe 4; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Quality/profitability is "the most consistent factor" and a crash hedge (prior weight 3).

- Key numbers: US 1926-63: profitability 0.09%/month (t 0.86), investment 0.02 (t 0.14), value 0.43 (t 2.09); RMW -16.44% over the 12 months to Aug-2026; QUAL -34.1% vs S&P -33.9% (2020-02-19..03-23), beta 0.99; MSCI USA Quality -20.3% vs -18.1% in 2022.
- Sources: prof_verification_log.csv V009, V012; exec EC-T-19 (QUAL, T3, not re-fetched)
- Chair items: PC-T-16, PR-T-04, EC-T-19
- Destination: DNB-TF-08 (never count quality as a hedge); quality 2 as a composite leg (DROP (as hedge/weight 3))

**DNB-TF-09 / TF-45** (fp 11, fe 14; professors Refuted, executives Refuted; data Untested). Refuted proposition: US post-earnings drift and US corporate-event drifts (S&P inclusion, buybacks, SEOs, dividend initiation/omission, merger arbitrage) are viable standalone cards.

- Key numbers: NMV US 1963-2012: SUE drift 0.72 -> 0.26%/month net (t 1.60) at 35% monthly turnover; large-cap drift about 0 since 2006 (Martineau); expected net Sharpe at 50 bp -0.51. S&P 500 additions 7.3% (1990s) -> 0.8% n.s. (2010s); repeat-buyback drift 2.51% -> 0.89%.
- Sources: literature only (prof_verification_log.csv V038-V044; exec rows 46-47, 74)
- Chair items: PC-T-20, EC-T-20, EC-T-21
- Destination: DNB-TF-09 (event flags only) (DROP); ruling CR-04

**DNB-TF-10 / TF-47** (fp 1, fe 19; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Product composites (CANSLIM/IBD, SEPA/VCP), factor-ETF rotation, sell-side recommendation/target/LTG levels and 13F cloning are acting signals.

- Key numbers: FFTY 3.52%/yr since Apr-2015 vs 13-14% for the S&P; AIEQ 4.18% vs SPY 12.65% over 5 years; iShares 10-year excess vs IVV: MTUM +2.1, QUAL -1.0, VLUE -0.0, USMV -5.9 pp/yr; 2000-01 top recommendation group -7.06%/yr vs +13.44% bottom.
- Sources: exec_verification_log.csv rows 12, 48 (live fund records)
- Chair items: PC-T-29 (no rigorous OOS test found for CANSLIM/VCP), EC-T-18
- Destination: DNB-TF-10 (DROP (estimate revisions BACKLOG via the archive))

**DNB-TF-11 / TF-48** (fp 4, fe 5; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Market valuation (CAPE, the Fed model, forward P/E) is a usable 1-year timing signal.

- Key numbers: Shiller: 1-year R2 of log CAPE 0.05 in sample; out of sample 1990-2022 -0.18 (US lab) / -16.5% (chair); 10-year OOS R2 1990-2013 -0.25; Fed model after 1965 R2 0.01; point-in-time CAPE de-risking -1.8 pp/yr (1891-2023), -4.5 pp/yr (1990-2023); CAPE > 30: forward 1-year +3.0% vs +6.5% unconditional.
- Sources: us_A4_valuation.csv; exec c01 (rows 3-5)
- Chair items: PC-T-21, EC-T-17
- Destination: DNB-TF-11; CONTEXT display only (CONTEXT); ruling CR-12

**DNB-TF-12 / TF-60** (fp 25, fe 1; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Classic technical indicators and rules (RSI, MACD, Bollinger, Donchian, golden/dead cross, candlesticks, Fibonacci, Elliott, chart patterns) and TradingView/CMT/retail-sourced strategies are usable signals in their own right (oscillators being independent of short-term reversal).

- Key numbers: 49 markets 2001-07 (5,806 rules): best Korean rule p 0.298 -> 0.942 after data-snooping adjustment; KOSPI 303 rules SPA p 0.880; SPY 322 rules p 0.82-0.97; KOSPI Connors RSI(2) / Bollinger CAGR 2.8% / 2.4% vs 7.2%; KRX RSI14 vs 1-month reversal correlation 0.92, %B 0.87; RSI14 / %B contrarian net-35 Sharpe -0.15 / -0.32; > 95% of TradingView indicators repaint.
- Sources: kr_index_spa.csv, kr_index_timing.csv; us_B_family.csv; kr_ls_correlations.csv
- Chair items: PC-T-22, PC-T-24, PC-T-29, EC-T-27 (RSI/%B = reversal), X17 data (US lab negative at 50 bp)
- Destination: DNB-TF-12 (unless family gate + nine-step gate as a new card, via the porting protocol) (DO-NOT-BUILD); ruling CR-12

**DNB-TF-13 / TF-61** (fp 8, fe 23; professors Refuted, executives Refuted; data Refutes). Refuted proposition: Short-horizon technical trading is viable at QUANTGEN costs: intraday rules (momentum, opening-range breakout, VWAP crosses, gaps, support/resistance) and KRX stock-level crosses, MA alignment (jeongbaeyeol), price-above-MA200 selection, limit-up chasing and volume-spike buying.

- Key numbers: Intraday edges 1-7 bp vs round trips of 25-46 bp on KRX (0.20% tax + one tick of 5.1-25.8 bp) and 70-100 bp at QUANTGEN costs; < 882 recorded intraday sessions. KRX price/SMA200 selection L/S Sharpe -0.05, long-only excess -5.6%/yr (net 35); crosses <= 17 bp (t about 0); MA-alignment state -10.9% net (2015-19), -48.7% in the 2026 crash.
- Sources: kr_key_numbers.csv lines 20-21; exec_verification_log.csv rows 15-17
- Chair items: PC-T-22 (stock-level MA timing DROP), PC-T-24 (intraday S/R research BACKLOG only), EC-T-01, EC-T-27
- Destination: DNB-TF-13 (DROP)

**DNB-TF-14 / TF-65** (fp 10, fe 1; professors Refuted, executives Refuted; data Untested). Refuted proposition: Deep price-pattern (chart-image CNN), order-book deep learning and LLM-news strategies are viable for QUANTGEN.

- Key numbers: Krauss-Do-Huck: 0.45%/day before costs, 0.25% after, negative in 2010-15; ChatGPT news strategy Sharpe 6.54 -> 1.22 (late 2021 to 2024), unprofitable at a 20 bp round trip; in-window LLM backtests are contaminated.
- Sources: literature (prof_verification_log.csv V073-V074)
- Chair items: PC-T-30 (DROP L5), X54 / E1-C23 (alternative-data alpha DROP)
- Destination: DNB-TF-14 (DROP); ruling CR-11

**DNB-TF-15 / TF-66** (fp 1, fe 0; professors Refuted, executives Silent; data Untested). Refuted proposition: Macro variables may interact with stock-level signals (macro x characteristic terms) in a combiner.

- Key numbers: Design rule protecting macro P1 (macro sizes risk, never directs).
- Chair items: PC-T-30, PROF 5.1-13
- Destination: DNB-TF-15 (DROP); ruling CR-11

**DNB-TF-16 / TF-68** (fp 5, fe 1; professors Refuted, executives Refuted; data Untested). Refuted proposition: Crypto short-term reversal deserves weight 2 (prior design).

- Key numbers: Liu-Tsyvinski-Wu 2014-18: 1- to 4-week cross-sectional momentum 2.7 / 3.3 / 4.1 / 2.5% per week; 8-16 weeks not significant (Grobys-Sapkota find nothing).
- Sources: literature (prof_verification_log.csv V100)
- Chair items: PC-T-28, PR-T-08, E3-C24 (short-horizon crypto momentum)
- Destination: DNB-TF-16 (DROP (weight 0)); ruling CR-10

Headline: on QUANTGEN costs nothing short-horizon survives (KRX round trip 25-46 bp before impact; weekly reversal breaks even at 12.5 bp per side), no single-index timing rule beats buy-and-hold after a data-snooping control, and Korean low volatility, size and raw momentum are factor tilts or cost-eaten spreads rather than alpha.

## 7. CONTESTED, ONE-SIDED and UNTESTED lists (-> backlog, with settling tests)

### 7.1 CONTESTED (11 nodes; panels disagree or a panel is split)

**TF-09** (fp 3, fe 7; professors Split, executives Moderate; data Untested). KRX per-name costs should come from liquidity buckets calibrated on quotes (P4 8/15/30/50 bp non-tax vs P6 tiers vs the 35 bp flat rate); until calibrated a bucket may raise a name's cost, never lower it below 35 bp.

- Key numbers: Corwin-Schultz KRX spreads Jan-2024..Sep-2026: 99-117 bp (negatives zeroed first) or 22-57 bp by cap bucket / 16.5-47 bp by traded value (monthly mean then floor) (V096). E7 desk view 15-25 bp for KOSPI200 names UNVERIFIABLE.
- Sources: prof_v07/v07b Corwin-Schultz (prof_verification_log.csv V096 MISMATCH); no KIS quotes
- Chair items: PX-T-07, PR-T-14, EC-T-04 (35 bp adequate only for liquid names), RX-08
- Settling test: Calibrate half-spread and impact on KIS quote snapshots (P4 D3 / DC-P6-05) by 20-day traded-value bucket; adopt only buckets >= 35 bp per side.
- Destination: BL-TF-01 (BACKLOG)

**TF-16** (fp 4, fe 3; professors Moderate, executives Split; data Mixed). Low-volatility stock sleeves give drawdown protection beyond plain de-gearing (Korea tested against a same-beta static book S_beta; US untested at QUANTGEN cost).

- Key numbers: KRX 1996-2026 net 35, lowest-VOL quintile: beta 0.63 EW / 0.74 VW; CAPM alpha +2.2% (t 0.8) / +0.7% (t 0.3), rf 0; beat the VW market in 6/7 (EW) and 7/7 (VW) crash windows (2026 crash: +6.3% VW book vs -38.5%); lagged 9 of 10 rebounds (2026 melt-up -102 pp VW). Against S_beta (beta x market + cash): MDD -73.9% vs -51.5% (EW book, dMDD -22.4 pp), -64.9% vs -57.8% (VW, -7.1 pp), -12.2 pp vs the EW-universe comparator; tail ratio 0.97-0.99 (PC-2 analogue fails); Sharpe 0.41 vs 0.36. US: low-beta tercile Sharpe 0.65 vs 0.41 (1954-2017, gross); USMV -5.9 pp/yr vs IVV over 10 years.
- Sources: r2_kr_lowvol.csv, r2_kr_lowvol_windows.csv; exec_chair_checks/c12_lowvol_samebeta.csv, c08
- Chair items: PC-T-08 (protective candidate 2), PROF 4.2, EX-T-06, ER-T-03 (contested with the lab)
- Settling test: KR: run the sleeve forward against a pre-registered S_beta (beta estimated over the prior 252 sessions at the header); US: DC9 alpha net of beta with FF5+Mom and S_beta at 50 bp.
- Destination: FS-3 (KR descriptive sleeve with S_beta); BL-TF-03 (US DC9); screen input to SCR-1 (FORWARD-SIM descriptive (KR); BACKLOG (US)); ruling CR-01

**TF-21** (fp 3, fe 3; professors Split, executives Moderate; data Mixed). A constrained Korean momentum card (12-1 or 12-7 top quintile excluding the highest-turnover/lottery names, own-vol scaled, capped, long-only) deserves weight 1.

- Key numbers: KRX 1996-2026 net 35: momentum Q5 ex highest-turnover quintile +7.81%/yr vs unfiltered Q5 (IR 1.02); low-turnover winners minus EW universe +9.7%/yr (t 2.8) but -0.1% in 2015-07..2024-12; 12-7 L/S quintiles EW net Sharpe 0.20 (= 12-1), -0.01 in 2016-26; 12-7 deciles from 2001 net 0.60. Sim-Kim 12-7 FF5 alpha 0.531%/month (t 2.05).
- Sources: r2_kr_mom_grid_long.csv; r2_kr_excl_summary.csv (B4)
- Chair items: PX-T-11, EX-T-05
- Settling test: Pre-register one variant (Q5 12-1 ex F4, R-03 scaled, 5% name cap, long-only vs EW universe) and run >= 252 sessions forward; gate with the 2026 crash replay; expected REVISE/REJECT on step 6 after 2010.
- Destination: FS-2 (FORWARD-SIM (weight 1)); ruling CR-05

**TF-23** (fp 2, fe 6; professors Moderate, executives Split; data Refutes). Further momentum crash controls protect Korean momentum: the Daniel-Moskowitz bear gate (R-04) applied beyond the specification book (and to earnings-momentum sleeves), and a 52-week-high-neutral construction.

- Key numbers: KOSPI D-M gate 1996-2026: 9 onsets (1997-05-31 .. 2020-03-20), on 9.8% of days; 3 onsets since 2000; off on 2026-06-22 (24-month KOSPI +227%); crash window unchanged (-40.3% VW static); adds only 0.30 -> 0.34 (EW) and 0.48 -> 0.52 (VW) in Sharpe on KRX top-500 WML, 2000-26 (R2_EXEC EX-T-08, chair c05; cost basis as printed there). 52wH-neutral WML*: US 1930-2022 worst month -23.66% vs -74.06% (not a max drawdown); untested on KRX.
- Sources: r2_kr_crash_controls.csv; r2_kr_dm_gate_onsets.csv; r2_kr_crash_exposure_2026.csv
- Chair items: PC-T-10 (D-M gate as mandatory control), PX-T-09 (52wH-neutral untested), PR-T-10, EX-T-08, ER-T-01
- Settling test: 52wH-neutral and Samsung/SK hynix-capped momentum on KRX with the 2026 crash replay (P2 DC-J); D-M extension only after R-04 leaves INSUFFICIENT DATA.
- Destination: R-04 spec book only; BL-TF-04 (52wH-neutral) (SPEC BOOK ONLY (D-M); BACKLOG (52wH-neutral)); ruling CR-05

**TF-24** (fp 4, fe 2; professors Split, executives Refuted; data Mixed). Nearness to the 52-week high deserves a weight-2 tilt in Korean equal-weighted small/mid books, rather than a weight-1 composite feature.

- Key numbers: KRX EW top quintile minus EW universe, net 35: +0.33%/month (t 2.14) from 2001-03 but +0.13%/month (t 0.81) from 1996-03; +0.07 at 70 bp; capped VW +0.06%/month (t 0.40); long-only excess +1.6%/yr (t 0.8); 52wH L/S lost 20.6% after the 2026 crash.
- Sources: kr_key_numbers.csv lines 8-9; prof_verification_log.csv V028, V089
- Chair items: PX-T-03, X59 (BACKLOG weight 1, quarterly variant)
- Settling test: One pre-registered Tier A test inside the constrained-momentum card (start date fixed in the header), quarterly rebalance variant, 2x costs.
- Destination: BL-TF-05 (feature weight 1; one Tier A test) (BACKLOG)

**TF-29** (fp 4, fe 3; professors Refuted, executives Moderate; data Mixed). US stock-level 12-1 momentum deserves weight 2 (executives) rather than 1 (professors) at 50 bp per side.

- Key numbers: French WML Sharpe 0.36 (1990-2017/03), -0.16 (2008-2017/03); US lab Mom 0.04 (2000s), 0.25 (2010-17); NMV momentum 1.33%/month gross -> 0.68 net (US 1963-2012); MTUM +2.1 pp/yr vs IVV over 10 years with -15.2 / -17.2 pp lags (2021, 2023).
- Sources: us_C_factors.csv; us/US_datalab_summary.md §C3
- Chair items: PC-T-19, weight table 5.1 (chair proposal, X29)
- Settling test: Run R-03-scaled US momentum as a composite leg at 50 bp per side on an FMP universe once a US stock panel exists.
- Destination: BL-TF-07; weight table (final 1); cross-spec XS-16 (BACKLOG)

**TF-33** (fp 0, fe 2; professors Refuted, executives Split; data Mixed). Trend should run as a standalone sleeve that may hold 0 rather than as an overlay bounded to [0.5, 1] (E3: bounding halves the protection).

- Key numbers: KOSPI 3 bp: absolute max DD -34.1% (sleeve) vs -39.2% (clip) / -44.8% (0.5+0.5x); 1997-98 -6.9% vs -39.2% / -40.4%; tail ratio 0.77 -> 0.91 (PC-2 fails); dMDD vs own S rises (+8.9 -> +10.8 / +9.9 pp), so the "halving" claim (+17.3 -> +8.1 pp) is NOT REPRODUCED; with VT20 on top the floored trend passes.
- Sources: r2_idx_overlay_vs_sleeve.csv; r2_idx_e3_checks.csv
- Chair items: PC-T-23 flag (floor gives back slow-bear protection), EX-T-01, ER-T-02, MC-07
- Settling test: Resolved by CR-02: standalone index trend sleeve = strategy card that may hold 0 (CARD-P); trend scaling another book = overlay in [0.5, 1].
- Destination: SPEC §TF-5 IDX-0 class rule (standalone sleeve may hold 0; overlay bounded); comparison cell in FS-1 (GOVERNANCE (resolved by CR-02)); ruling CR-02

**TF-37** (fp 5, fe 4; professors Split, executives Split; data Untested). Korean value and quality deserve standalone weights of 2 each (rather than 1) before a point-in-time test.

- Key numbers: E7 long-term-reversal value proxy +0.2%/yr net (2015-24); chair -1.2%. RISE Korea Value-Up ETF: SK hynix 20.9%, Samsung 17.5%, IT 50.8% (chip beta, not value evidence). RMWq 0.65%/month (t 2.75, 2002-15) vs profitability replication 5.0% (2000-19).
- Sources: E7 quickchecks part 8 (value proxy); exec_verification_log.csv row 97 (RISE Value-Up ETF)
- Chair items: PX-T-01 (quality 1 vs 2), PC-T-12 (value 2), EX-T-10 (E4 2 vs E7 1)
- Settling test: OpenDART PIT test; value may rise to 2-3 only after a PIT pass that survives the 2024-02-26 split.
- Destination: Weight table (1 each); BL-TF-10 (BACKLOG (weight 1)); ruling CR-04

**TF-38** (fp 4, fe 3; professors Split, executives Split; data Refutes). Korean earnings-announcement drift deserves weight 2 (P6, E4, E7) rather than 1.

- Key numbers: Shin et al. Korea 2002Q4-2017Q4: 60-day drift 4.80% (t 9.35), market-adjusted, gross; about 2.9%/yr cost at 35 bp if fully turned over. Chair information-event proxy 2006-2026 (gross): positive events -1.34% over 60 days (t -4.2), negative -2.68% (t -7.6).
- Sources: exec_chair_checks/c07_stdout.txt (DC-3 proxy); exec_verification_log.csv row 54; prof_verification_log.csv V092
- Chair items: PX-T-02, PR-T-07, EX-T-09, ER-T-05
- Settling test: DART-timestamped test: CAR[-1,+1] sign, entry at rcept_dt + 1 session, top two size terciles, must pass at 2x costs; then 2.
- Destination: BL-TF-11 (weight 1) (BACKLOG (weight 1)); ruling CR-04

**TF-55** (fp 7, fe 2; professors Split, executives Split; data Mixed). Gate steps 8 and 9 should change (step 8 report-only or replaced by a 2-of-3-subperiod rule; step 9 an alpha-only haircut of 0.5/0.3 instead of the flat 60% Sharpe haircut).

- Key numbers: Step 8 alone passes 23.8% (KOSPI bootstrap), 31.2% (sign-flip), 29.5% (iid) of zero-Sharpe strategies at 10 years (not 36-38%). Step 9: spec expected live Sharpe = 0.6 x OOS; E1/E4 and the R2 KR lab printed 0.4 x (lab B1/F4 +1.23%/yr instead of +1.85%).
- Sources: r2_idx_gate_sim.csv (step 8); r2_kr_excl_gate.csv (step-9 column)
- Chair items: PX-T-04, PX-T-05, PR-T-15, EX-T-12, MC-12
- Settling test: Resolved by CR-08: both steps unchanged; print step 8's stand-alone weakness and, optionally, an alpha-only haircut line.
- Destination: Steps 8 and 9 unchanged (CR-08); reporting lines GOV-6 (GOVERNANCE (unchanged + reporting)); ruling CR-08

**TF-70** (fp 6, fe 0; professors Refuted, executives Weak; data Refutes). G10 FX technical rules deserve a weight above 0 (executives: FX trend 0-1).

- Key numbers: 388 FX technical portfolios: mean Sharpe 0.66 (1980-98, in sample) -> 0.06 (1999-2020, out of sample), not surviving modest costs; QUANTGEN V3 FX momentum OOS Sharpe -0.59 (REJECT).
- Sources: QUANTGEN V3 REJECT (context); prof_verification_log.csv V103
- Chair items: PC-T-26, weight table 5.3 (FX trend alpha 0-1, BACKLOG)
- Settling test: One pre-registered USD/KRW slow-trend test at 10 bp per side.
- Destination: Weight 0; BL-TF-20 (one USD/KRW slow-trend test at FX cost) (BACKLOG (weight 0))

### 7.2 ONE-SIDED (8 nodes; only one panel holds the proposition)

**TF-25** (fp 0, fe 13; professors Silent, executives Split; data Refutes). Crowding and market-stress gauges (comomentum, holdings crowding, VIX/R-08) time factor crashes well enough to drive a [0.5, 1.0] sizing multiplier.

- Key numbers: VIX at 19 factor-crash onsets 12.9-25.8; GS record crowding (Nov 2023, 70% of longs in top-10) followed by further outperformance; no Korean comomentum series computed. KOSPI 2026-05-27: margin loans KRW36.25tn, VKOSPI 70.83.
- Sources: exec_verification_log.csv rows 8, 69 (VIX at onsets)
- Chair items: EC-T-24, EX-T-07
- Settling test: A comomentum multiplier must beat R-03 out of sample on a pre-registered KRX/US sleeve; until then display only.
- Destination: BL-TF-06 (multiplier test); CONTEXT display; cross-spec XS-14 (R-08) (BACKLOG / CONTEXT)

**TF-27** (fp 0, fe 5; professors Silent, executives Strong; data Supports). The macro R-07 drawdown ladder applies to total book NAV only, with non-cumulative steps, re-armed at 0.5 from a reset reference peak (never the all-time high-water mark), and never per sleeve.

- Key numbers: KOSPI CW 2000-26 net 35, re-arm 0.5 with reset: Sharpe 0.42 -> 0.40; max DD -55.8% -> -41.3%; 0.69 halts/yr; July 2026 -38.6% -> -21.3%; H1-2026 +101.1% -> +49.0%. All-time-peak reference: 22.8 halts/yr, Sharpe -1.65. Per-sleeve ladder on vol-scaled VW WML 0.38 -> 0.16. VT20 + ladder: 0.40 -> 0.35, max DD -47.4% -> -34.8%.
- Sources: exec_verification_log.csv rows 58-61 (c02)
- Chair items: EC-T-10, MC-02, MC-03
- Settling test: Owner confirms the four clarifications; the professors did not review the ladder.
- Destination: Cross-spec XS-08 (proposal to the owner) (OWNER DECISION (proposal)); ruling CR-07

**TF-28** (fp 0, fe 5; professors Silent, executives Split; data Mixed). Ladder thresholds should be set in units of the declared book volatility (-1.0/-1.5/-1.9 sigma; a book vol ceiling of 8%) rather than at fixed -8/-12/-15%.

- Key numbers: Brownian check, Sharpe 0.5: P(-15% within 10 years) 0.97 at 12% book vol, 0.66 at 8%; P(-8% within 1 year) 0.38 at 8% vol. KOSPI VT20 + fixed ladder 0.40 -> 0.35, 0.50 halts/yr (chair); sigma-scaled ladder 0.40, max DD -37.4%, 1 halt (E5, not re-run).
- Sources: exec_verification_log.csv row 62 (Brownian check), row 61
- Chair items: EX-T-11, MC-01, MC-16
- Settling test: Owner chooses fixed % or sigma units, or declares a book-vol ceiling <= 8% (at which the two coincide).
- Destination: Owner decision OQ-01; FORWARD-SIM both conventions (OWNER DECISION); ruling CR-07

**TF-46** (fp 0, fe 8; professors Silent, executives Split; data Untested). US event candidates that need a US stock panel and EDGAR data (opportunistic insider purchases held about 126 days; an IPO-age exclusion screen) deserve gated tests.

- Key numbers: Cohen-Malloy-Pomorski 1986-2007: 82 bp/month VW (t 2.15), 180 bp EW (t 6.07), but long-short (buys minus sells), one-month hold, five-factor alpha. Ritter 1980-2024 IPOs -20.5% vs market, -8.9% style-adjusted over 3 years (2011-24: -24.7% / -16.4%); unprofitable -23.4% vs +1.8%.
- Sources: exec_verification_log.csv rows 49, 72-73, 75
- Chair items: EX-T-13, EX-T-14, ER-T-04
- Settling test: DC10 (buys-only, long-only, 126 days, EDGAR acceptance timing) and the IPO screen with the first US stock card.
- Destination: BL-TF-13 (BACKLOG)

**TF-49** (fp 11, fe 0; professors Strong, executives Weak; data Untested). Markets without a QUANTGEN data path (Japan, Taiwan, China A, India, broad EM, Europe) carry CONTEXT-only weights until a data path exists.

- Key numbers: Japan WML Sharpe 0.067 static, 0.416 with dynamic scaling; China A 1-month reversal CAPM alpha 1.49%/month (2000-16), momentum 0.04%/month (t 0.11, 2008-20).
- Chair items: PC-T-33, PX-T-08, weight table 5.3 (Japan/Europe BACKLOG; others unchanged)
- Settling test: Add a data path per market; until then the rows are priors only.
- Destination: Weight table (CONTEXT rows); BL-TF-15 (data paths) (CONTEXT)

**TF-52** (fp 7, fe 0; professors Strong, executives Silent; data Untested). Tiered t-hurdles: Tier A (single-configuration replication of a published, internationally replicated anomaly) t >= 2.0; new signals t >= 3.0 plus SPA; > 100 configurations or TradingView-sourced ideas t >= 3.4-3.8.

- Key numbers: Harvey-Liu-Zhu: 316 factors, t thresholds 3.39-3.78 by 2012; Hou-Xue-Zhang: 64% of 447 anomalies insignificant at 5%, 85% at t = 3; deflated Sharpe implies required t 3.17 (9 configurations) and 3.67 (27).
- Sources: literature (prof_verification_log.csv V005-V006, V053-V054)
- Chair items: PC-T-02, PROF 5.1-6
- Settling test: Owner adopts or declines; it only tightens the gate.
- Destination: BL-TF-16 (owner: a tightening, allowed under CR-08) (BACKLOG)

**TF-62** (fp 7, fe 0; professors Strong, executives Weak; data Supports). Build one point-in-time feature library of price primitives (trend/position, short-term reversal, range volatility, abnormal volume, 52-week high, MA distance, capital-gains overhang), every variant counted as a trial.

- Key numbers: KRX L/S correlations 1996-2026: three clusters - low-risk (VOL-TURN 0.90), trend (PMA200-HIGH52 0.88), contrarian (RSI-%B 0.95, REV-RSI 0.92); George-Hwang 52wH US 1963-2001 0.45%/month (1.23% ex-January, t 7.06).
- Sources: kr_ls_correlations.csv (three clusters)
- Chair items: PC-T-24, EC-T-28 (pre-register <= 4-5 features per card) - implicit
- Settling test: Owner decides scope; features enter only through pre-registered cards.
- Destination: BL-TF-17 (build features as cards need them) (BACKLOG)

**TF-69** (fp 2, fe 0; professors Moderate, executives Silent; data Untested). A CTREND-lite crypto technical composite (long-only vs BTC, 10/20 bp) and a down-only funding/basis multiplier in [0.5, 1] are worth testing.

- Key numbers: CTREND numbers UNVERIFIABLE (V101); crypto carry averaged > 10%/yr, peaked near 60%, and predicts price declines (BIS WP 1087, V102).
- Chair items: PC-T-28
- Settling test: Local crypto panel (Upbit/Binance/CoinGecko) with point-in-time universe; long-only vs BTC at 10/20 bp.
- Destination: BL-TF-19 (BACKLOG); ruling CR-10

### 7.3 UNTESTED (4 nodes; both panels lean the same way but no local data exist)

**TF-35** (fp 8, fe 17; professors Moderate, executives Moderate; data Untested). A broad, long-lookback diversified futures trend book (B3 re-registered with >= 25 markets) carries a real but small premium (alpha about 0.0-0.3 after 2009, not the prior "0.4-0.8 per asset, about 1.0 diversified").

- Key numbers: 67 markets 1880-2013: net Sharpe 0.77 after 2/20; trend excess 6.3%/yr (2000-09) vs 0.4%/yr over T-bills (2010-18); Barclay Systematic 6.98%/yr 2000-08 (9/9 years) vs -0.30% 2009-18 (3/10); QUANTGEN B3 OOS Sharpe 0.08; AQMIX 10-year Sharpe about 0.30.
- Sources: no local futures panel; QUANTGEN B3 card (context); prof_verification_log.csv V025, V104; exec row 25
- Chair items: PC-T-25, PR-T-06, EX-T-02 (B3 re-registration)
- Settling test: Continuous-futures panel for >= 25 markets, fixed multi-speed ensemble, diversifier claim vs cash plus portfolio uplift; gate-class approval.
- Destination: BL-TF-09 (BACKLOG)

**TF-36** (fp 4, fe 5; professors Moderate, executives Moderate; data Untested). A Korean value-quality composite (value + profitability + net issuance, OpenDART point-in-time, split at 2024-02-26) deserves weight 2 as the Korean fundamental BUILD-candidate.

- Key numbers: Korea Jul-2002..Jun-2015 (gross, in sample): HML 1.05%/month (t 3.41), RMWq 0.65 (t 2.75), CMA 0.66 (t 3.57); 2000-19 replication: value 69.2%, profitability 5.0%; KOSPI P/B about 0.99. Net issuance (KRX-only) already built as SCR-2.
- Sources: no KR fundamentals in the labs; prof_verification_log.csv V016-V017, V052
- Chair items: PC-T-12, EC-T-14 (GP/A + issuance core, value low-weight partner)
- Settling test: Build the OpenDART PIT store (statements from BY2015, rcept_dt + 1), then test the pre-registered composite at 35/70 bp, EW and capped VW, split at 2024-02-26; expect INSUFFICIENT DATA or REVISE.
- Destination: BL-TF-10 -> SPEC §TF-6 FUND-1 when the PIT store exists (BACKLOG (BUILD-candidate, weight 2)); ruling CR-04

**TF-43** (fp 16, fe 11; professors Strong, executives Moderate; data Untested). A US value + profitability + investment + issuance composite (value only inside it; combined with momentum at sleeve level, not as a single high-turnover card) is the US fundamental BUILD-candidate at weight 2.

- Key numbers: NMV US 1963-2012, gross -> net: value + profitability 0.82 -> 0.77%/month (t 4.82); investment 0.56 -> 0.46 (t 3.60); net issuance 0.57 -> 0.37 (t 2.43). Expected net L/S Sharpe after decay at 50 bp 0.42 (0.37 at 2x; 0.17 after the 60% haircut). US HML Sharpe -0.23 (2010-18); HML-Mom correlation -0.18 (1949-2017); 50/50 HML+UMD -0.13 (2007-2017/03).
- Sources: no US fundamentals locally; us_C_factors.csv (HML, Mom history); prof_verification_log.csv V037, V041-V042
- Chair items: PC-T-16, PC-T-17, PC-T-18, X43, X44 (EC-T-14 composite core)
- Settling test: EDGAR acceptance + 1 session PIT store and FMP prices; sector-neutral, banded; 15+ years of XBRL; expect REVISE first.
- Destination: BL-TF-12 -> SPEC §TF-6 FUND-2 when FMP/EDGAR PIT data exist (BACKLOG (BUILD-candidate, weight 2)); ruling CR-04

**TF-64** (fp 13, fe 1; professors Weak, executives Weak; data Untested). Gradient boosting or small neural nets add net value over a linear composite at QUANTGEN costs.

- Key numbers: Gu-Kelly-Xiu US 1987-2016 (gross): NN3 R2 0.40% vs OLS-3 0.16%; VW L/S Sharpe 1.35 vs 0.61; gains concentrate in microcaps and high turnover.
- Sources: literature (prof_verification_log.csv V069-V072)
- Chair items: PC-T-30 (shadows only), X54 / E1-C24 (BACKLOG with liquidity filters and 2x costs)
- Settling test: Shadow runs only after L0/L1 exist; never enter displayed exposure.
- Destination: BL-TF-18 (shadow challengers, non-gating) (BACKLOG); ruling CR-11

## 8. Focus map: where attention went

| Rank | Node | Proposition (shortened) | fp | fe | Professor share | Class | Destination |
|---|---|---|---|---|---|---|---|
| 1 | TF-61 | Short-horizon technical trading is viable at QUANTGEN costs: intraday rules (momentum, opening-range breakout,... | 8 | 23 | 26% | CORE-PROHIBITION | DNB-TF-13 |
| 2 | TF-43 | A US value + profitability + investment + issuance composite (value only inside it; combined with momentum at ... | 16 | 11 | 59% | UNTESTED | BL-TF-12 -> SPEC §TF-6 FUND-2 when FMP/EDGAR PIT data exist |
| 3 | TF-60 | Classic technical indicators and rules (RSI, MACD, Bollinger, Donchian, golden/dead cross, candlesticks, Fibon... | 25 | 1 | 96% | CORE-PROHIBITION | DNB-TF-12 (unless family gate + nine-step gate as a new card, via the porting protocol) |
| 4 | TF-05 | Korean regime and event flags on every KRX card (short-sale regimes, the 2024-02-26 Value-up split, the sell-t... | 8 | 17 | 32% | CORE-LINK | SPEC §TF-2 DATA-5 (flags); event cards BL-TF-14 |
| 5 | TF-35 | A broad, long-lookback diversified futures trend book (B3 re-registered with >= 25 markets) carries a real but... | 8 | 17 | 32% | UNTESTED | BL-TF-09 |
| 6 | TF-45 | US post-earnings drift and US corporate-event drifts (S&P inclusion, buybacks, SEOs, dividend initiation/omiss... | 11 | 14 | 44% | CORE-PROHIBITION | DNB-TF-09 (event flags only) |
| 7 | TF-56 | Published and bank/asset-manager backtest numbers are haircut once per stage before they become priors, and pl... | 8 | 14 | 36% | CORE-LINK | SPEC §TF-7 GOV-8 (prior calibration) |
| 8 | TF-07 | Every stock-level card prints an itemised cost header (commission, date-varying sell tax, half-tick floor, sqr... | 10 | 12 | 45% | CORE-LINK | SPEC §TF-7 GOV-7 |
| 9 | TF-08 | Turnover discipline on monthly stock cards: buy/hold bands (enter the top 20%, exit below the top 40%), one-wa... | 10 | 11 | 48% | CORE-LINK | SPEC §TF-1 INV-4 |
| 10 | TF-47 | Product composites (CANSLIM/IBD, SEPA/VCP), factor-ETF rotation, sell-side recommendation/target/LTG levels an... | 1 | 19 | 5% | CORE-PROHIBITION | DNB-TF-10 |
| 11 | TF-06 | Every KRX stock card is gated on long-only net excess return against a pre-registered benchmark set (EW, CW, C... | 10 | 8 | 56% | CORE-LINK | SPEC §TF-7 GOV-1 |
| 12 | TF-41 | Korean stock-level short-term reversal (daily, weekly or 1-month, with or without the 5d/20d volume filter) is... | 11 | 7 | 61% | CORE-PROHIBITION | DNB-TF-07; cross-spec XS-02, XS-03, XS-04 |
| 13 | TF-30 | Single-index trend is a protective tool judged as CARD-P, never an alpha card (alpha 0); on KOSPI its protecti... | 4 | 10 | 29% | CORE-LINK | SPEC §TF-5 IDX-0 (class rule); cross-spec XS-09 (R-14) |
| 14 | TF-64 | Gradient boosting or small neural nets add net value over a linear composite at QUANTGEN costs. | 13 | 1 | 93% | UNTESTED | BL-TF-18 (shadow challengers, non-gating) |
| 15 | TF-25 | Crowding and market-stress gauges (comomentum, holdings crowding, VIX/R-08) time factor crashes well enough to... | 0 | 13 | 0% | ONE-SIDED | BL-TF-06 (multiplier test); CONTEXT display; cross-spec XS-14 (R-08) |

Totals: fp 342 and fe 375 across the 70 nodes (claims mapped to more than one node count once per node). Of the top 15, 6 are CORE-LINK, 5 CORE-PROHIBITION and 3 UNTESTED.

Where attention went:
- Executives concentrated on execution and data (theme A: fe 101 vs fp 52), momentum crashes and concentration (C: 63 vs 29), events and products (E), and short-horizon trading (TF-61: 23 claims). Professors concentrated on governance and technical-rule standards (F: fp 97 vs fe 49), fundamentals (E: 84) and ML (G: 28 vs 7).
- Professor-dominated nodes (fp at least 3x fe, total >= 6): TF-60 (25/1, CORE-PROHIBITION), TF-64 (13/1, UNTESTED), TF-50 (12/0, CORE-LINK), TF-65 (10/1, CORE-PROHIBITION), TF-51 (10/1, CORE-LINK), TF-49 (11/0, ONE-SIDED), TF-12 (7/2, CORE-LINK), TF-19 (8/1, CORE-PROHIBITION), TF-55 (7/2, CONTESTED), TF-67 (6/2, CORE-LINK), TF-52 (7/0, ONE-SIDED), TF-62 (7/0, ONE-SIDED), TF-68 (5/1, CORE-PROHIBITION), TF-70 (6/0, CONTESTED).
- Executive-dominated nodes (fe at least 3x fp, total >= 6): TF-47 (1/19, CORE-PROHIBITION), TF-25 (0/13, ONE-SIDED), TF-26 (1/11, CORE-LINK), TF-02 (1/10, CORE-LINK), TF-10 (1/8, CORE-LINK), TF-03 (2/7, CORE-LINK), TF-46 (0/8, ONE-SIDED), TF-23 (2/6, CONTESTED), TF-01 (0/7, CORE-LINK), TF-34 (1/5, CORE-PROHIBITION).
- Attention and evidence diverge: the two BUILD NOW screens drew 9 (TF-12) and 6 (TF-13) claims, the VT20 workhorse 3 (TF-31) and the floored trend x VT20 cell 3 (TF-32), while three of the four most-discussed nodes ended refuted or untested (TF-61, TF-60 refuted; TF-43 untested).
- Both panels converged where the labs could compute: execution, hygiene, costs and crash risk are CORE-LINK with Strong support on both sides; disagreement is concentrated where data are missing (fundamental weights, drift, 52-week high, cost buckets) or where the question is a design convention (sleeve vs overlay, step 8/9).

The full focus map (all 70 nodes with fp, fe, class, label and destination, plus edges) is `charts/focus_map.json`; theme totals are in `results/r3_focus_by_theme.json`.

## 9. Weight table (per market x family; alpha / protective / screen)

Weights are 0-3 design priors, not gate results; any weight of 2 or more still needs a PASS card before it can feed the displayed book. Proposed normalisation base_weight = w / 3 (never above 1.0x). Rules W1-W5 in section 3; * = one panel only; n.r. = no panel reviewed.

### 9.1 Korea

| Family | Column | Prior | Professors | Executives | Final | Rule | Reason (market, period, gross/net, source) | Nodes |
|---|---|---|---|---|---|---|---|---|
| XS momentum: raw 12-1 card | alpha | 1 | 1 (12-7 / 52wH features only; no 12-1 card) | 0 | 0 | W1 CR-05 | KRX ALL quintiles 1996-04..2026-09, net 35: L/S Sharpe 0.20, 2016-26 -0.20 (r2_kr_crash_controls.csv lines 44/70); long-only excess -1.34%/yr (kr_key_numbers.csv line 2); break-even about 64 bp/side (derived, r3_golden_values.csv) | TF-20 |
| XS momentum: constrained variant (Q5 12-1/12-7 ex lottery, R-03, capped, long-only) | alpha | - (macro R-15: 12-7/residual 1, UNVERIFIED) | 1 (one Tier A card allowed) | 1 (FORWARD-SIM) | 1 (FORWARD-SIM) | W1 CR-05 | KRX 1996-03..2026-09, net 35: Q5 ex highest-turnover quintile +7.81%/yr vs Q5 (IR 1.02; r2_kr_excl_summary.csv line 398); low-turnover winners -0.08%/yr vs EW in 2015-07..2024-12 (r2_kr_mom_grid_long.csv line 1158) | TF-21 |
| 52-week-high nearness (feature) | alpha | - | 1 (P6: 2) | 1 | 1 (feature only) | W2 | KRX EW top quintile minus EW universe, net 35: +0.33%/month from 2001-03 vs +0.13%/month from 1996-03 (KR lab daily series; R2_PROF PX-T-03) | TF-24 |
| Short-term reversal, daily/weekly | alpha | 3 | 0 | 0 | 0 | W1 CR-03 | KRX ALL EW 1996-2026: weekly L/S net-35 Sharpe -1.78 (kr_key_numbers.csv line 30); break-even 12.5 bp/side (derived) | TF-41 |
| Short-term reversal, monthly guard (no top-decile winners) | screen | (3) | 1 (protective guard) | 1 (conditioning) | 1 | W1 CR-03 | KRX ALL EW deciles 1996-04..2026-09: 1-month reversal +1.43%/month gross, +0.23% net 35 (r2_kr_reversal.csv lines 47/52); untested as a screen (FS-5) | TF-42 |
| Value (standalone) | alpha | 2 | 2 (3 only after a PIT test) | 1 (E4: 2) | 1 | W1 CR-04 | no point-in-time test (no OpenDART store); RISE Korea Value-Up ETF is 50.8% IT, i.e. chip beta (exec_verification_log.csv row 97) | TF-37 |
| Quality / profitability (standalone) | alpha | 1 | 2 (composite only; contested) | 1 | 1 | W1 CR-04 | Korea RMWq 0.65%/month (t 2.75), 2002-07..2015-06, gross, vs a 5.0% profitability replication rate (2000-19) (R2_PROF PC-T-12); no PIT test | TF-37 |
| KR-VQ composite (value + profitability + net issuance) | alpha | - | 2 | composite core (no number) | 2 (BUILD-candidate pending PIT store) | W1 CR-04 | Korea HML 1.05%/month (t 3.41), 2002-07..2015-06, gross, in sample (R2_PROF PC-T-12); untested locally | TF-36 |
| Net issuance / dilution exclusion | screen | - | 2 (EW or capped) | 3 | 3 EW and small/mid; 1 capped CW; 0 top 200 | W1 CR-06 | KRX 1996-03..2026-09, net 35: B1 EW +2.34%/yr (IR 0.65), B2 capped VW +0.69% (p 0.24), B3 top 200 +0.29% (r2_kr_excl_summary.csv lines 17/149/281) | TF-13 |
| Lottery composite exclusion (vol + MAX + turnover) | screen | - (low-vol 2 as a tilt) | 3 EW/small-mid; 1 cap-weighted; 0 top 200 | 3 EW/selection/momentum; hygiene capped; 0 top 200 | 3 EW and small/mid; 1 capped CW; 0 top 200 | W1 CR-06 | KRX 1996-03..2026-09, net 35: B1 +3.08%/yr (IR 1.53), B2 +0.85%, B3 +0.49% with gate REJECT (r2_kr_excl_summary.csv lines 11/143/275; r2_kr_excl_gate.csv line 6) | TF-12 |
| Low volatility | alpha | 2 | 1 EW / 0 cap-weighted | 0-1 | 0 | W1 CR-01 | KRX 1996-2026, net 35: low-vol long-only excess +1.08%/yr EW (kr_key_numbers.csv line 10); CAPM alpha +2.23%/yr (t 0.80), rf 0 (r2_kr_lowvol.csv line 14) | TF-17 |
| Low volatility | protective | - | 2 | 1 (descriptive) | 0 (descriptive FORWARD-SIM vs S_beta; not counted) | W1 CR-01 | KRX 1996-2026, net 35: dMDD vs S_beta -7.1 to -22.4 pp; tail ratio 0.97-0.99 (c12_lowvol_samebeta.csv lines 2/6/10) | TF-16 |
| Low volatility | screen | - | inside the lottery composite | screen input (F2/F4) | input to SCR-1 (weight carried by the composite) | W1 CR-01 | KRX B1 1996-03..2026-09, net 35: high-vol quintile exclusion (F2) +3.64%/yr (r2_kr_excl_summary.csv line 5) | TF-12, TF-16 |
| Investor flow (foreign/institutional) | alpha | 3 | 1 | 1 | 1 (log only; no direction rule; t-1 history required) | W1 CR-03 | Korea 2003-11: lagged flows predict the next open, not the next close (R2_PROF PC-T-34); H1-2026 foreigners sold KRW148.3tn net while KOSPI rose about 101% (R2_EXEC EC-T-23) | TF-39, TF-40 |
| Earnings-announcement drift | alpha | 3 | 1 (P6: 2) | 1 (E4/E7: 2) | 1 | W1 CR-04 | Korea 2002Q4-2017Q4: +4.80% over 60 days, gross, market-adjusted (prof_verification_log.csv V092); KRX information-event proxy 2006-2026: -1.34% over 60 days (t -4.2), gross (R2_EXEC EX-T-09, chair c07) | TF-38 |
| Size | alpha | (implicit) | 0 | 0 | 0 | W2 | KRX ALL EW: size L/S gross Sharpe 0.39 over 1996-2026 (kr_key_numbers.csv line 18) but -0.05 in 2016-26; -26.9% (2025), -26.5% (2026 YTD) (KR_datalab_summary.md; R2_PROF PC-T-11) | TF-18 |
| TS trend, KOSPI single index | alpha | 2 | 0 | 1 (return prior; class CARD-P) | 0 | W1 CR-02 | KOSPI 1996-2026, 3 bp: Hansen SPA p 0.880 over 303 timing rules (kr/results/kr_index_spa.csv); CR-02: CARD-P only, never CARD-O | TF-30 |
| TS trend, KOSPI trend alone | protective | - | 1 | 1 | 1 | W2 (CR-02) | KOSPI rebuilt, net 3 bp: multi-speed sleeve PASS 1996-09..2026-09 (PC-1 +8.9 pp; r2_idx_protective_scorecard.csv line 3) but REJECT from 2011/2016 starts (r2_idx_start_date_sensitivity.csv lines 33/38) | TF-30 |
| KOSPI 20-day vol target (macro R-06) | protective | - (macro R-06 BUILD NOW) | 2 | workhorse (product 2) | 2 | W2 (CR-02) | KOSPI rebuilt 1996-09..2026-09, net 3 bp: PC-1 +6.5 pp, tail 0.70, PASS (r2_idx_protective_scorecard.csv line 5); PASS from every start 1996-2006 (r2_idx_start_date_sensitivity.csv) | TF-31 |
| KOSPI floored trend x VT20 | protective | - | implied by trend overlay 1 x VT 2 (flagged) | 2 | 2 (FORWARD-SIM) | W1 CR-02 | KOSPI rebuilt 1996-09..2026-09, net 3 bp: PC-1 +15.4 pp vs own S, tail 0.64, PASS (r2_idx_overlay_vs_sleeve.csv line 12); plateau and start-date sweep not evaluated | TF-32 |
| TS trend, KOSDAQ | protective | - (macro R-14: 0) | n.r. | 1 (BACKLOG, untested) | 0 (BACKLOG) | W3 (macro R-14 0; no data) | untested locally; E3 reports KOSDAQ fully long into a -39.7% fall (Feb-Jul 2026, E3 paper, unverified) | - |
| Momentum own-vol scaling (macro R-03) | protective | - (macro R-03) | mandatory control | BUILD NOW | risk control on every momentum sleeve (not a weight) | W1 CR-05 | KRX 12-1 L/S VW, 2026-06-22..07-30, net 35: -10.52% scaled vs -22.95% static at the same average exposure (r2_kr_crash_windows.csv lines 68/76) | TF-22 |

### 9.2 US

| Family | Column | Prior | Professors | Executives | Final | Rule | Reason (market, period, gross/net, source) | Nodes |
|---|---|---|---|---|---|---|---|---|
| XS momentum (stock level) | alpha | 3 | 1 | 2 | 1 | W3 | US French WML Sharpe -0.16 (2008..2017-03, gross; us/results/us_C_factors.csv); momentum 1.33 -> 0.68%/month gross -> net (US 1963-2012, Novy-Marx-Velikov; R2_PROF PC-T-04); conflicts with macro R-15 (2 if vol-scaled + D-M) | TF-29 |
| Short-term reversal | alpha | 1 | 0 | 0 | 0 | W2 | US 1963-2012: 0.37 -> -1.28%/month gross -> net (Novy-Marx-Velikov; R2_PROF PC-T-04) | - |
| Value | alpha | 1 | 1 (composite only) | 1 (composite member) | 1 (inside US-VQ) | W2 | US HML Sharpe -0.23 (2010-18, gross; us_C_factors.csv); HML -55% Jan-2007..Jun-2020 (R2_PROF PC-T-17) | TF-43 |
| Quality / profitability | alpha | 3 | 2 | 2 | 2 (composite leg; not a hedge) | W2 | US RMW -16.44% over the 12 months to Aug-2026 (R2_PROF PC-T-16); QUAL beta 0.99 in 2020-02-19..03-23 (R2_EXEC EC-T-19) | TF-43, TF-44 |
| US-VQ composite (value + profitability + investment + issuance) | alpha | - | 2 | composite (GP/A core, value low weight) | 2 (BUILD-candidate pending FMP/EDGAR PIT) | W1 CR-04 | US 1963-2012: value + profitability 0.82 -> 0.77%/month gross -> net (t 4.82) (Novy-Marx-Velikov; R2_PROF PC-T-18); untested locally | TF-43 |
| Net issuance | alpha | - | 2 (inside US-VQ) | 2 | inside US-VQ | W2 | US 1963-2012: 0.57 -> 0.37%/month gross -> net (t 2.43) (Novy-Marx-Velikov; R2_PROF PC-T-18) | TF-43 |
| Low volatility | alpha | 2 | 1 | 1 (pending DC9) | 1 | W2 (CR-01 BACKLOG) | US 1954..2017-03: low-beta tercile Sharpe 0.65 vs 0.41 high-beta, gross (us_C_factors.csv); USMV -5.9 pp/yr vs IVV over 10 years (R2_EXEC EC-T-18) | TF-16 |
| Low volatility | protective | - | 2 | 1 (must beat S_beta) | 1 (BACKLOG; S_beta comparator) | W3 + CR-01 | Korean S_beta test shows de-gearing (c12_lowvol_samebeta.csv); US untested at 50 bp | TF-16 |
| Investor flow | alpha | 1 | 1 (n.r.) | 1 (display only) | 1 (display) | W5 (prior kept; executives agree) | no evidence either way; macro never directs (P1) | - |
| Earnings drift (PEAD) | alpha | 2 | 0 | 1 (confirmation input) | 0 standalone | W1 CR-04 + W3 | US 1963-2012: SUE drift 0.72 -> 0.26%/month gross -> net (t 1.60) (Novy-Marx-Velikov; R2_PROF PC-T-20); large caps about 0 since 2006 | TF-45 |
| TS trend, SPY single index | alpha | 3 | 0 | 1 (return prior) | 0 | W1 CR-02 | SPY 1999-2021: 322 timing rules, SPA p 0.82-0.97 (us/results/us_B_family.csv); CR-02: CARD-P only | TF-30 |
| TS trend, SPY single index | protective | - | 1 (futures cost only) | 2 (3 at <= 5 bp) | 0 at 50 bp (REJECT); 1 at futures cost (BACKLOG) | W1 CR-02 + W3 | SPY 1999-05..2021-03: multi-speed PC-1 -10.7 pp at 50 bp (REJECT), +14.7 pp at 5 bp (INSUFFICIENT DATA) (r2_idx_protective_scorecard.csv lines 10/17) | TF-34 |
| SPY vol target (macro R-06 US) | protective | - (macro R-06) | 1 (futures cost only) | REJECT at 50 bp | 0 at 50 bp; 1 at futures cost (BACKLOG) | W1 CR-02 | SPY 1999-05..2021-03, 50 bp: VT15 PC-1 +0.3 pp, REJECT (r2_idx_protective_scorecard.csv line 12) | TF-34 |
| Opportunistic insider buys | alpha | - | Silent | 0-1 | 0 (BACKLOG DC10) | W3 | US 1986-2007: 82 bp/month VW, but long-short, one-month, five-factor alpha (NBER w16454; exec_verification_log.csv row 49) | TF-46 |
| IPO-age exclusion | screen | - | Silent | 2 | 2* (one-sided; inactive until a US stock card exists) | W4 | US IPO cohorts 2011-24: -16.4% style-adjusted over 3 years (Ritter; exec_verification_log.csv rows 72-73) | TF-46 |
| Lottery exclusion | screen | - | 1 (untested) | Silent | 1* (one-sided, untested) | W4 | no US stock panel; KRX analogue only | TF-12 |
| Distress / M-score exclusion | screen | - | exclusion use only (no number) | Silent | - (BACKLOG with US-VQ) | W4 | US 1963-2012: failure probability 0.85 -> 0.24%/month gross -> net (t 0.73) (Novy-Marx-Velikov; R2_PROF PC-T-20) | TF-45 |

### 9.3 Crypto

| Family | Column | Prior | Professors | Executives | Final | Rule | Reason (market, period, gross/net, source) | Nodes |
|---|---|---|---|---|---|---|---|---|
| TS trend (card C3) | alpha | 3 | 3 | 2 (protective 2) | 2 | W3 (macro R-15: 2; OQ-09) | KRW-BTC OOS Sharpe 1.22 [0.62, 1.77] vs 0.79, p 0.04, net 10 bp per side (QUANTGEN record 2026-09-27; 00_QUANTGEN_context.md line 28); edge shrinking 2022-26 unverified | TF-67 |
| Short-term reversal | alpha | 2 | 0 | refutes (E3-C24: momentum) | 0 | W1 CR-10 | crypto 2014-18: 1-4-week cross-sectional momentum 2.5-4.1%/week, gross (Liu-Tsyvinski-Wu; prof_verification_log.csv V100) | TF-68 |
| XS momentum | alpha | 1 | 1 | Silent | 1* | W4 | crypto 2014-18 momentum (Liu-Tsyvinski-Wu; V100); Grobys-Sapkota find none | TF-68 |
| CTREND-lite technical composite | alpha | - | 2 (provisional) | Silent | 2* (provisional, BACKLOG) | W1 CR-10 + W4 | CTREND numbers unverifiable (prof_verification_log.csv V101) | TF-69 |
| Funding/basis down-only multiplier | protective | 2 (flow prior) | 1 | Silent | 1* (BACKLOG; multiplier in [0.5, 1]) | W4 | crypto carry > 10%/yr predicts price declines (BIS WP 1087; prof_verification_log.csv V102) | TF-69 |
| Value / quality / low-vol / drift | alpha | 0 | 0 | - | 0 | W2 | no data path | - |

### 9.4 Futures/FX

| Family | Column | Prior | Professors | Executives | Final | Rule | Reason (market, period, gross/net, source) | Nodes |
|---|---|---|---|---|---|---|---|---|
| Diversified futures TS-mom (B3 re-registration) | alpha | "strong" | 1 (broad, long lookbacks) | 1-2 (diversifier) | 1 | W3 | trend excess 0.4%/yr over T-bills 2010-18 (AQR 2019; R2_PROF PC-T-25); QUANTGEN B3 OOS Sharpe 0.08 (00_QUANTGEN_context.md) | TF-35 |
| Diversified futures TS-mom | protective | - | n.r. | 3 | 3* (one-sided, untested; BACKLOG) | W4 | 67 markets 1880-2013: 8 of the 10 largest 60/40 drawdowns had positive trend returns, gross (R2_PROF PC-T-25) | TF-35 |
| Futures XS momentum | alpha | "weak" | 0 | - | 0 | W4 (prof only, matches prior) | professors 0 (matches the prior "weak"); executives silent | - |
| G10 FX technical rules | alpha | - | 0 | 0-1 (FX trend) | 0 (one USD/KRW slow-trend test BACKLOG) | W3 | 388 FX portfolios: Sharpe 0.66 (1980-98) -> 0.06 (1999-2020), gross (prof_verification_log.csv V103); QUANTGEN V3 OOS Sharpe -0.59 | TF-70 |
| Carry | alpha | "strong" | n.r. (V4 REJECT) | BACKLOG | - (BACKLOG) | W5 | QUANTGEN V4 dollar carry REJECT (too few trades; 00_QUANTGEN_context.md) | - |

### 9.5 Markets without a QUANTGEN data path (CONTEXT only; professors' consolidated row, executives' trend cell; TF-49)

| market | XS-mom | ST-rev | value | quality | low-vol | flow | earn drift | TS-mom | exec TS trend alpha / protective |
|---|---|---|---|---|---|---|---|---|---|
| Europe | 2 | 0 | 2 | 2 | 1 | 1 (n.r.) | 2 (n.r.) | 0 (protective 2) | 0-1 / 1-2 |
| Japan | 0 (value-paired hedge only) | 1 | 3 | 1 | 2 | 1 | 1 | 0 (protective 2) | 1 / 2 |
| Taiwan | 0 | 2 | 2 | 1 | 1 | 1 | 2 | 0 (protective 2) | unchanged |
| China A | 0 | 3 | 2 | 2 | 3 | 1 | 1 | 0 (protective 1) | unchanged (0) |
| India | 3 (n.r.) | 1 (n.r.) | 2 (n.r.) | 3 (n.r.) | 2 (n.r.) | 2 (n.r.) | 2 (n.r.) | 2 (n.r.) | unchanged |
| EM broad | 2 | 1 | 2 | 2 | 2 | 1 | 1 | 0 (protective 2) | - |

Final Korea row (one line): raw 12-1 0 | constrained momentum 1 (FS-2) | 52-week high 1 (feature) | reversal daily/weekly 0, monthly guard 1 (FS-5) | value 1 | quality 1 | KR-VQ 2 (pending PIT) | lottery screen 3 / 1 / 0 and dilution screen 3 / 1 / 0 (EW and small/mid / capped CW / top 200) | low-vol alpha 0, protective 0, screen input | flow 1 (logging) | drift 1 | size 0 | KOSPI trend alpha 0, protective 1 | VT20 protective 2 | floored trend x VT20 protective 2 (FS-1) | KOSDAQ trend 0 | R-03 on every momentum sleeve.

Final US row (one line): stock momentum 1 | reversal 0 | value 1 (inside US-VQ) | quality 2 (composite leg, not a hedge) | US-VQ 2 (pending FMP/EDGAR PIT) | net issuance inside US-VQ | low-vol alpha 1, protective 1 (BACKLOG, vs S_beta) | flow 1 (display) | PEAD 0 standalone | SPY trend alpha 0, protective 0 at 50 bp / 1 at futures cost (BACKLOG) | SPY VT15 0 at 50 bp / 1 at futures cost | insiders 0 (BACKLOG) | IPO-age screen 2* (inactive) | lottery screen 1* | distress screen BACKLOG.

## 10. Go / no-go register

77 items. Columns: evidence for, evidence against, indicative gate outcome, and what would change the decision. Full register: `results/r3_go_nogo.csv` and `charts/go_nogo.json`. Numbers here are short forms of labelled values given in the node entries (sections 5-7) and the golden values (section 11): unless stated otherwise, KRX screen figures are 1996-03..2026-09 at net 35 (r2/kr/results/r2_kr_excl_*.csv), KRX signal figures 1996-2026 at net 35 (kr/results, r2/kr/results), KOSPI index figures 1996-09-02..2026-09-29 at net 3 bp and SPY figures 1999-05..2021-03 (r2/idx/results); B1-B4 are the four base books defined in section 11.2.

### 10.1 BUILD NOW, INVARIANT and GOVERNANCE

| ID | Card or rule | Market | Decision (ruling) | Evidence for | Evidence against | Indicative gate | What would change it | Nodes | Target |
|---|---|---|---|---|---|---|---|---|---|
| G-01 | SCR-1 lottery composite exclusion screen card (F4, worst decile of vol + MAX + turnover ranks), gated as CARD-O against the unscreened book on the same days | KRX | BUILD NOW (CR-06) | B1 EW +3.08%/yr net 35 (IR 1.53, t 8.3, boot p 0.0005, 90% of years, all three decades positive); B4 momentum Q5 +6.13%/yr; break-even 380 bp/side | pooled DSR 0.94 < 0.95 over 176 trials; lags melt-ups (B1 -0.6 pp in the 2026 melt-up, -2.6 pp after the crash); B2 gain mostly 1996-2005; impact and dividends not modelled | B1/F4 7 of 8 steps -> REVISE; B2/F4 7/8 -> REVISE; B3/F4 6/8 -> REJECT; B4/F4 7/8 -> REVISE | forward IR <= 0 over 252 sessions of incubation; quote-calibrated impact pushing the break-even below 70 bp | TF-12 | §TF-3 SCR-1 |
| G-02 | SCR-2 dilution / net-issuance exclusion screen card (F6: 252-session share growth > 10%) | KRX | BUILD NOW (CR-06) | B1 +2.34%/yr net 35 (IR 0.65, p 0.0005), unchanged at 70 bp; ex-Q5 +3.0%/yr (t 9.2, chair c06); issuance BHAR -25.3% | decaying (2017-26 tilt IR 0.35-0.38; BHAR -34.4% -> -17.6% -> -5.1%); B2 +0.69% (p 0.24); 20% of literal split-rule flags not confirmed by KRX adjustment factors | not run through the 8-step harness; expected REVISE (2x-cost step fails in 2017-26 for the tilt form) | post-2015 decay check pre-registered; drop to hygiene if 2016+ forward IR <= 0 | TF-13 | §TF-3 SCR-2 |
| G-03 | SCR-3 construction rule: any KRX momentum or small-cap long-only sleeve excludes the highest-turnover quintile or the F4 names | KRX | BUILD NOW (rule) (CR-05, CR-06) | B4 F1 +7.81%/yr (IR 1.02), F4 +6.13%/yr (IR 1.24); high-turnover winners -11.6%/yr vs EW (t -4.2) | in-sample, same 176-trial race; momentum itself is weak 2015-24 | B4 7/8 -> REVISE | if the constrained momentum card (FS-2) is dropped, the rule stays for small-cap sleeves only | TF-15 | §TF-3 SCR-3 |
| G-04 | INV-1 decide at the close of t; fill at the KRX official close t (bound close t+1); never NXT/after-hours prints; momentum/trend entries at the close | KRX/US | INVARIANT (CR-09) | KRX momentum overnight +18.4%/yr vs intraday -7.9%; official close = closing call | short holds (<= 5 sessions) were to use next-open fills in the professors' encoding; moot because short-horizon KRX cards are dropped | n/a (invariant) | none (convention) | TF-01 | §TF-1 INV-1 |
| G-05 | INV-2 locked limits: never enter at a locked limit-up close; locked limit-down exits carry to the first unlocked session at 2x cost; VI/circuit-breaker/halt days unfillable; locked limit-downs out of reversal books | KRX | INVARIANT (CR-09, CR-06) | next-open buys after locked limit-ups -579 bp at t+20 (n 11,186); locked limit-downs continue -1,036 bp at t+20; 6.3% of EW-book entries hit a locked close | the 2x cost on a carried limit-down exit is an assumption, not measured; needs daily limit-state flags | n/a | none (convention); a 5-session no-new-long window only if BL-TF-02 supports it | TF-02, TF-14 | §TF-1 INV-2 |
| G-06 | INV-3 data hygiene: eligibility on t-1 data; corporate-action-adjusted returns with \|dln shares\| > 1% flagged; month-end prices for monthly timing tests | KRX/US | INVARIANT (CR-09) | unadjusted closes flip KJFS momentum to -11.4%/month; same-day eligibility inflated a benchmark to +27.7%/yr; averaging inflates trend Sharpe +0.10/+0.23 | flag calibration: 20% of literal split-rule flags in the dilution test were not confirmed by KRX adjustment factors | n/a | none | TF-03 | §TF-2 DATA-1..3 |
| G-07 | INV-4 bands (enter top 20%, exit below top 40%), one-way turnover target <= 30%/month (hard 50%), capacity <= 1-2% of ADV20 | KRX/US | INVARIANT (CR-09) | banded value+momentum+profitability 1.02%/month net; cost drag 2.94%/yr at 35%/month turnover | impact model absent | n/a | KIS quote calibration may tighten capacity | TF-08 | §TF-1 INV-4 |
| G-08 | INV-5 no name-level stops; signal exits only; trend sleeves stop through their signal | KRX | INVARIANT (CR-09) | 15% stop: top-500 EW net Sharpe 0.04 -> -0.15, VW 0.28 -> 0.07; Kaminski-Lo condition fails | US HZZ stops helped in-sample (separate BACKLOG CARD-O) | n/a | a US stop card passing as CARD-O | TF-10 | §TF-1 INV-5 |
| G-09 | DATA-4 point-in-time layer (OpenDART rcept_dt + 1; EDGAR acceptance rule), delisting stress -30%/-100%, forward archives (consensus, revisions, flows, quotes) | KRX/US | BUILD NOW | both panels; prerequisite for KR-VQ, US-VQ, drift, insiders, revisions | OpenDART statements only from BY2015 (DART-only history detects IR >= 0.41-0.48) | n/a | none (prerequisite); build order is an owner decision (OQ-08) | TF-04 | §TF-2 DATA-4 |
| G-10 | DATA-5 Korean regime and event flags (short-sale regimes, 2024-02-26 Value-up split, tax path, reforms); event layer may only exclude or scale <= 1.0 | KRX | BUILD NOW (flags) | both panels; dates verified (V061, V062; exec rows 18, 24, 78) | event cards need post-reform history (INSUFFICIENT DATA until about 2028) | n/a | none for the flags; event cards leave INSUFFICIENT DATA after about 5 years of post-reform history | TF-05 | §TF-2 DATA-5 |
| G-11 | DATA-6 log final investor-type flows with timestamps (t-1 history); no direction rule | KRX | BUILD NOW (logging) (CR-03) | no local t-1 history exists; flows predict the next open, not the close | logging carries no return claim; KIS flow access and timestamps still to be verified | n/a | an open-leg test after >= 3 years of logs | TF-40 | §TF-2 DATA-6 |
| G-12 | MOM-1 macro R-03 own-vol scaling on every momentum sleeve (KRX included) as a risk control | all | BUILD NOW (risk control) (CR-05) | de-risked before the 2026 crash (0.55 EW / 0.27 VW); VW L/S -10.5% vs -22.9% same-exposure static; full-sample net Sharpe up | 2016-26 net Sharpe lower (EW -0.20 -> -0.24; VW 0.32 -> 0.23); not a return source | macro R-03 indicative PASS on French data | forward 2016+ dSR < 0 in >= 2 regions (macro demotion rule) | TF-22 | §TF-4 MOM-1 |
| G-13 | MOM-2 Daniel-Moskowitz bear gate (macro R-04) on the specification book only; no extension to earnings-momentum sleeves | all | SPEC BOOK ONLY (CR-05) | right sign in loser-rebound crashes (US 2009) | KOSPI: 9 onsets in 30 years, off on 2026-06-22; never fires in a bull-market crash | macro R-04 INSUFFICIENT DATA (7 US onsets) | R-04 leaving INSUFFICIENT DATA via out-of-region holdouts | TF-23 | §TF-4 MOM-2 (= macro R-04) |
| G-14 | RISK-1 Korea caps by book type (5% single name in selection sleeves; VW legs capped; sector bands; 0.35 pair cap on look-through for market/ETF books when the pair share > 0.45; semis <= 0.50) with the CR-07 pair-share denominator | KRX | INVARIANT (owner to confirm) (CR-07) | CR-07 share 53.71% on 2026-09-29; cap bound 99 sessions in 2026; cost -2.2 pp YTD, +4.6 pp in the crash | pair cap cost -15.0 pp in the H1-2026 melt-up | n/a | owner choice of denominator (alternatives 50.82% / 52.59% / 53.96%) | TF-26 | §TF-4 RISK-1; macro R-07 |
| G-15 | GOV-1 long-only primary statistic against a pre-registered benchmark set (EW, CW, CW ex-pair, capped CW); L/S diagnostic; EW and capped VW reported together | KRX | GOVERNANCE (CR-08) | spreads live in the short leg; H1-2026 CW +117.1% vs EW +3.4% | cards will look weaker than their long-short versions (by design) | n/a | none; benchmarks may be added, never removed | TF-06 | §TF-7 GOV-1 |
| G-16 | GOV-2 multiplicity: family gate (SPA/StepM within a technical-rule family), BH-FDR across a release (reported), trial registry with a global N | all | GOVERNANCE (CR-08) | SPA p 0.880 (303 KOSPI rules), 0.82-0.97 (322 SPY rules); pooled DSR exposes 176-trial searches | more REVISE / INSUFFICIENT verdicts | n/a | none; family membership is pre-registered per release | TF-51 | §TF-7 GOV-2 |
| G-17 | GOV-3 attribution block on every card (beta, Jensen alpha with NW t, FF5+Mom US, local KRX factors incl. SEMI; "factor tilt" label) | all | GOVERNANCE (BUILD NOW) (CR-08) | flat SML (US +0.46%/yr, t 0.17; KR +1.1%/yr, t 0.19); KR low-vol alpha t 0.8 | executives silent | n/a | none; owner fixes the "factor tilt" threshold (proposal: Newey-West alpha t below 2.0) | TF-50 | §TF-7 GOV-3 |
| G-18 | GOV-4 bootstrap blocks max(10, Politis-White on d and d^2) for steps 2 and 5 on every card | all | GOVERNANCE (CR-08) | 10-session blocks: step-2 false pass 8.0% (nominal 5%), step-5 13.7% (nominal 10%) on KOSPI-like returns | longer blocks widen intervals; some cards may move from PASS to REVISE (a tightening, allowed by CR-08) | n/a | none | TF-53 | §TF-7 GOV-4 |
| G-19 | GOV-5 power reporting: minimum track record at the tier hurdle; INSUFFICIENT DATA when it exceeds the history; never loosen the gate | all | GOVERNANCE (CR-08) | Sharpe 0.4 needs 15.8 / 40.3 years for 50% / 80% power at step 2 | many realistic tilts will print INSUFFICIENT DATA instead of PASS or REJECT | n/a | none; the gate is never loosened | TF-54 | §TF-7 GOV-5 |
| G-20 | GOV-6 steps 8 and 9 unchanged; print step 8's stand-alone weakness and optionally an alpha-only haircut line; fix "x0.4" prints to 0.6 x OOS | all | GOVERNANCE (CR-08) | joint false pass 0.5% at 10 years; spec step 9 = 0.6 x OOS | step 8 alone passes 24-31% of zero-Sharpe strategies | n/a | owner may add the 2-of-3-subperiod rule (a tightening) | TF-55 | §TF-7 GOV-6 |
| G-21 | GOV-7 itemised cost header and break-even pre-gate screen (reject if break-even < 2x pre-registered cost); flat 35/70 bp binding until quote calibration | all | GOVERNANCE (CR-08) | rejects weekly reversal (12.5 bp), raw 12-1 (about 64 bp) and the F5 screen (68 bp) before they spend gate trials | flat 35 bp may overstate costs for KOSPI 200 names (E7: 15-25 bp, unverified) and understate them for small caps | n/a | quote calibration (BL-TF-01) may raise a name's cost, never lower it below 35 bp | TF-07, TF-09 | §TF-7 GOV-7 |
| G-22 | GOV-8 prior calibration: one haircut per stage; plan with 0.5 (in sample) / 0.3 (post-publication) / 0.75 (drift-like); replace with measured local decay | all | GOVERNANCE | KRX 1-month reversal decayed about 90% (2001-09 -> 2020-26); AQMIX 0.30 vs a 1.21 backtest | Ilmanen per-factor haircuts unverifiable | n/a | measured local decay replaces the planning haircut where 20+ years of data exist | TF-56, TF-57 | §TF-7 GOV-8 |
| G-23 | GOV-9 stress table on every stock card (incl. 2026-06-22..07-30 replay; worst rolling 21/63-session and 5-week relative loss) | all | GOVERNANCE (reporting) | winner-led 2026 crash (L/S -24.4% ALL, -33.1% top 200 in July) | reporting only; no pass/fail threshold | n/a | none | TF-11 | §TF-7 GOV-9 |
| G-24 | GOV-10 contamination log and prospective incubation (FORWARD-SIM >= 252 sessions from 2026-10-01); CPCV reported, not gating | all | GOVERNANCE | the labs have seen 1996-2026 for every family discussed | CPCV gating contested (P4); gate-size simulation incl. steps 1, 4, 7 not run | n/a | P4 D14 full gate-size simulation | TF-58 | §TF-7 GOV-10 |
| G-25 | GOV-11 protective claims judged on CARD-P vs a same-exposure static comparator: S for exposure rules, S_beta = beta_hat x market + (1 - beta_hat) x cash for stock-level sleeves | all | GOVERNANCE (CR-01, CR-08) | VT20 fails step 5 (p 0.51) yet passes CARD-P; low-vol beats the market but not S_beta | beta_hat window must be pre-registered; a mis-estimated beta changes the verdict | n/a | owner choice of the beta_hat window (OQ-03) | TF-59 | §TF-7 GOV-11; macro §8.7 |
| G-26 | IDX-0 class rule: single-index trend is CARD-P only (never CARD-O); a standalone index trend sleeve may hold 0; trend scaling another book is an overlay in [0.5, 1] | all | GOVERNANCE (CR-02) | no trend rule beats buy-and-hold after data-snooping control; protection is the honest claim | E3 keeps the 0-allowed sleeve (slow-bear protection) | n/a | only an owner revision of CR-02 | TF-30, TF-33 | §TF-5 IDX-0; macro R-14 |
| G-27 | IDX-1 KOSPI VT20 (macro R-06) as the protective workhorse | KRX ETF | BUILD NOW (macro R-06) (CR-02) | CARD-P PASS 1996-09..2026-09 (dMDD +6.5 pp, tail 0.70, p_ni 0.051); PASS from every start 1996-2006 | INSUFFICIENT from 2011/2016 starts (2016-26 card = macro indicative INSUFFICIENT); bull tax (H1-2026 +51.7% vs +101.1%) | PASS (1996 start) / INSUFFICIENT (2016 start) | owner declares the card history (1996 rebuilt KOSPI vs 2016) | TF-31 | §TF-5 IDX-1 (= macro R-06) |
| G-28 | ML-1 equal-weight z-score composite (L0) with signs fixed in advance | all | BUILD (with the first composite card) (CR-11) | simple combinations are hard to beat; uplift undetectable (27-108 years) | equal weights ignore differences in signal strength; no local test | not run (built with the first composite card) | the ridge challenger (FS-4) beating L0 out of sample over >= 252 sessions without leakage findings | TF-63 | §TF-8 ML-1 |
| G-29 | CRY-1 keep C3 PASS; add a vol-scaled long-only control, a 2024-01-10 split, an ETH replication and a cut-time test (3 extra trials) | crypto | KEEP + GOVERNANCE (CR-10) | C3 1.22 [0.62, 1.77] vs 0.79 (p 0.04), 1.17 at 2x | p 0.04 fails Bonferroni across 16 cards (0.006); edge shrinking 2022-26 unverified; no local crypto data | PASS (QUANTGEN record) | post-ETF sub-period dSR <= 0 | TF-67 | §TF-9 CRY-1 |

### 10.2 FORWARD-SIM

| ID | Card or rule | Market | Decision (ruling) | Evidence for | Evidence against | Indicative gate | What would change it | Nodes | Target |
|---|---|---|---|---|---|---|---|---|---|
| G-30 | FS-1 KOSPI floored trend x VT20 (clip[0.5,1] trend x VT20) CARD-P; unbounded product and plain sleeve as comparison cells | KRX ETF | FORWARD-SIM (CR-02) | PASS full sample (+15.4 pp vs own S, tail 0.64, 63% of years); crash 2026 -9.8% | plateau and start-date sweep not evaluated; unbounded product REJECT from 2011 starts; trend evidence in 1997-2001 | indicative PASS (1996-09 start, plateau n/e) | start-date sweep REJECT from 2011, or plateau < 0.5 | TF-32 | FS-1 |
| G-31 | FS-2 constrained KRX momentum card (Q5 12-1 or 12-7 ex F4/highest-turnover, R-03, 5% cap, long-only), weight 1 | KRX | FORWARD-SIM (CR-05) | Q5 ex highest-turnover +7.81%/yr vs Q5; low-turnover winners +9.7%/yr (t 2.8) 1996-2026 | about 0 in 2015-24; 12-7 2016-26 net Sharpe -0.01; step 6 expected to fail after 2010 | expected REVISE / REJECT | forward net excess <= 0 after 252 sessions; 2026-type crash loss beyond the replay | TF-21 | FS-2 |
| G-32 | FS-3 KRX low-vol descriptive sleeve vs S_beta (beta_hat pre-registered) | KRX | FORWARD-SIM (descriptive) (CR-01) | beat the VW market in 7/7 crash windows (VW book); Sharpe non-inferior vs S_beta | dMDD vs S_beta -7.1 to -22.4 pp; tail ratio 0.97-0.99 (PC-2 fails) | fails PC-1 / PC-2 vs S_beta | forward PC-1 and PC-2 pass vs S_beta | TF-16 | FS-3 |
| G-33 | FS-4 ridge / Fama-MacBeth challenger shrunk toward L0 (inside the ML harness: purge/embargo >= 63 sessions, <= 12 configurations) | all | FORWARD-SIM (CR-11) | shrinkage keeps it close to L0 | no local test; uplift undetectable | not run | forward net uplift over L0 > 0 for >= 252 sessions with no leakage findings -> gated card | TF-63 | FS-4 |
| G-34 | FS-5 monthly reversal guard (exclude last month's top-decile winners) as a screen variant, weight 1 | KRX | FORWARD-SIM (screen variant) (CR-03) | gross 1-month reversal real in EW books | about 0 VW after 2005; untested as a screen | not run | R2-style race on B1/B4 at 35/70 bp | TF-42 | FS-5 |

### 10.3 BACKLOG

| ID | Card or rule | Market | Decision (ruling) | Evidence for | Evidence against | Indicative gate | What would change it | Nodes | Target |
|---|---|---|---|---|---|---|---|---|---|
| G-35 | KR-VQ composite (value + profitability + net issuance), weight 2 | KRX | BACKLOG (BUILD-candidate pending PIT store) (CR-04) | Kang 2002-15 HML 1.05%/month, RMWq 0.65%/month; value replicates in 69% of tests | profitability replicates in 5%; statements only from 2015; Value-up regime break | expected INSUFFICIENT DATA / REVISE | OpenDART PIT store built and tested | TF-36 | BL-TF-10 |
| G-36 | US-VQ composite (value + profitability + investment + issuance), weight 2 | US | BACKLOG (BUILD-candidate pending PIT data) (CR-04) | NMV value+prof 0.77%/month net (t 4.82) | no US fundamentals locally; HML -0.23 (2010-18) | expected REVISE | FMP/EDGAR PIT store | TF-43 | BL-TF-12 |
| G-37 | Korean value and quality individual weights (1 each until a PIT test) | KRX | BACKLOG (CR-04) | see KR-VQ | contested 1 vs 2 | not run (no PIT data) | PIT pass surviving the 2024-02-26 split | TF-37 | BL-TF-10 |
| G-38 | Korean earnings drift DART-timestamped test (weight 1) | KRX | BACKLOG (CR-04) | 4.80% over 60 days (gross, 2002-17) | proxy -1.34% (t -4.2, 2006-26) | not run (no DART-timestamped test) | pass at 2x costs in the top two size terciles -> 2 | TF-38 | BL-TF-11 |
| G-39 | KRX cost-bucket calibration on KIS quotes | KRX | BACKLOG | Corwin-Schultz is convention-sensitive (22-57 vs 99-117 bp) | no KIS quote history yet | n/a (calibration) | buckets may raise, never lower, the 35 bp | TF-09 | BL-TF-01 |
| G-40 | Daily-entry attention card (K-AF) and a 5-session no-new-long rule after locked limit-ups or volume spikes | KRX | BACKLOG (CR-06) | event effects -93 to -579 bp over 5-20 sessions | not tested as a daily card; CR-06 adopted only the locked-close invariant | not run | a daily-entry test passing at 35/70 bp adds a 5-session no-new-long rule to INV-2 | TF-14 | BL-TF-02 |
| G-41 | US low-vol DC9 (alpha net of beta; S_beta comparator) | US | BACKLOG (CR-01) | low-beta Sharpe 0.65 vs 0.41 | USMV -5.9 pp/yr | not run (no US stock panel) | a US stock panel and a pass against S_beta at 50 bp | TF-16 | BL-TF-03 |
| G-42 | 52-week-high-neutral momentum and capped momentum crash test on KRX | KRX | BACKLOG (CR-05) | US worst month -23.66% vs -74.06% | untested on KRX | not run | a KRX test with crash losses below the R-03-scaled book | TF-23 | BL-TF-04 |
| G-43 | 52-week high: one Tier A test inside FS-2 (quarterly variant) | KRX | BACKLOG | +0.33%/month from 2001 | +0.13 from 1996; -20.6% after the 2026 crash | not run as a card | a pass inside FS-2 from both the 1996 and 2001 starts | TF-24 | BL-TF-05 |
| G-44 | Crowding / comomentum multiplier (must beat R-03 out of sample) | all | BACKLOG | E1 proposal | VIX 12.9-25.8 at onsets; crowding records followed by gains | not run (no KRX comomentum series) | beating R-03 out of sample | TF-25 | BL-TF-06 |
| G-45 | US stock-level momentum as an R-03-scaled composite leg (weight 1) | US | BACKLOG | French WML 0.36 (1990-2017) | -0.16 (2008-17); 50 bp costs | not run (no US stock sleeve) | a US stock panel and a pass at 50 bp as an R-03-scaled composite leg | TF-29 | BL-TF-07 |
| G-46 | US single-index trend / VT on a futures-cost instrument (5 bp) | US | BACKLOG (CR-02) | PC-1 +3.8 to +14.7 pp at 5 bp | INSUFFICIENT (53-56% of benefit from the GFC) | INSUFFICIENT DATA | pooled markets for sufficiency | TF-34 | BL-TF-08 |
| G-47 | Diversified futures trend (B3 re-registration, >= 25 markets, fixed multi-speed, diversifier claim) | futures | BACKLOG | 135-year crisis alpha | 0.4%/yr excess 2010-18; B3 0.08 | old B3 registration REJECT (OOS 0.08) | gate-class approval and a futures panel | TF-35 | BL-TF-09 |
| G-48 | US opportunistic insider buys (DC10) and IPO-age exclusion | US | BACKLOG | CMP 82 bp/month (L/S); Ritter -16.4% | anchor is long-short one-month; no US stock sleeve | not run | EDGAR Form 4 and a US panel; DC10 pass as a long-only buys-only test | TF-46 | BL-TF-13 |
| G-49 | Korean event cards (treasury-share cancellation, buybacks, Value-up disclosures) | KRX | BACKLOG | Value-up +1.5% day 0 | 32 months of post-reform data | INSUFFICIENT DATA until about 2028 | about 5 years of post-reform event history | TF-05 | BL-TF-14 |
| G-50 | Tiered t-hurdles (A 2.0; B 3.0 + SPA; B+ 3.4-3.8) | all | BACKLOG (owner; tightening) | HLZ / HXZ thresholds | executives silent | n/a (governance) | owner adoption (a tightening only) | TF-52 | BL-TF-16 |
| G-51 | Feature primitive library | all | BACKLOG | three KRX clusters | executives: <= 4-5 features per card | n/a | built when a card needs a primitive; every variant counts as a trial | TF-62 | BL-TF-17 |
| G-52 | Gradient boosting / small nets as shadow combiners | all | BACKLOG (CR-11) | GKX NN3 0.40% vs 0.16% R2 (gross) | nets about 0 at 1-month after 2004 | not run | a shadow run beating L0/L1 net of costs over >= 252 sessions | TF-64 | BL-TF-18 |
| G-53 | CTREND-lite crypto composite and a down-only funding/basis multiplier | crypto | BACKLOG (CR-10) | CTREND survives costs (abstract) | numbers unverifiable; no local data | not run (no local crypto data) | a local crypto panel and a pass at 10/20 bp | TF-69 | BL-TF-19 |
| G-54 | One USD/KRW slow-trend test at FX cost | FX | BACKLOG | slow trend least decayed | G10 FX technical 0.06 OOS | prior QUANTGEN V3 FX card REJECT (-0.59) | one pre-registered USD/KRW slow-trend card passing at 10 bp | TF-70 | BL-TF-20 |

### 10.4 OWNER DECISION and CONTEXT

| ID | Card or rule | Market | Decision (ruling) | Evidence for | Evidence against | Indicative gate | What would change it | Nodes | Target |
|---|---|---|---|---|---|---|---|---|---|
| G-55 | Statistical review triggers (forward DD beyond the 95th simulated percentile, or 12-month Sharpe below its 90% CI; never auto-liquidate) | all | GOVERNANCE option (owner) | Brownian: an 8%-vol book hits -8% in 38% of years | professors silent | n/a | owner adoption | TF-10 | GOV option |
| G-56 | R-07 ladder clarifications (total book NAV only; non-cumulative; re-arm 0.5 with reset peak; no per-sleeve ladders) | KRX/US | OWNER DECISION (proposal) (CR-07) | all-time-peak reference re-halts 22.8 times/yr | cumulative steps helped KOSPI in one variant | n/a | owner decision; a re-run of E5's cumulative-step SPY result | TF-27 | XS-08 |
| G-57 | R-07 threshold units (fixed % vs sigma units / book vol ceiling <= 8%) | KRX/US | OWNER DECISION (CR-07) | P(-15% within 10 y) 0.97 at 12% vol, 0.66 at 8% | sigma ladder result not re-run | n/a | owner decision on units or a book-vol ceiling | TF-28 | OQ-01 |
| G-58 | Market valuation (CAPE, Fed model, forward P/E) as a display with its residual drift | US | CONTEXT (CR-12) | long-horizon R2 0.29 in sample | 1-year OOS R2 negative | n/a (CONTEXT) | only a family-gate and nine-step pass as a new card (CR-12) | TF-48 | context log |
| G-59 | Markets without a data path (Japan, Taiwan, China A, India, EM, Europe) | other | CONTEXT | literature priors | no data path | n/a | a data path per market | TF-49 | weight table |
| G-60 | Crowding display; R-08 not counted as factor-crash protection | all | CONTEXT | crowding levels are informative as a display | VIX 12.9-25.8 at factor-crash onsets (R-08 quiet) | n/a | a crowding multiplier beating R-03 out of sample (G-44) | TF-25 | macro R-08 |

### 10.5 DROP and DO-NOT-BUILD

| ID | Card or rule | Market | Decision (ruling) | Evidence for | Evidence against | Indicative gate | What would change it | Nodes | Target |
|---|---|---|---|---|---|---|---|---|---|
| G-61 | KRX stock-level short-term reversal (daily/weekly/1-month; with or without volume filter) | KRX | DROP (CR-03) | gross reversal real | net 35 Sharpe -1.78 (weekly); break-even 12.5 bp | pre-gate REJECT | a venue at <= 5 bp per side (VIX-conditioned weekly reversal on ETFs/futures is BACKLOG DC-E2-09) | TF-41 | DNB-TF-07 |
| G-62 | Raw Korean 12-1 momentum standalone card | KRX | DROP (CR-05) | positive gross (+9.3%/yr) | net 35 Sharpe 0.20, -0.20 in 2016-26 | pre-gate REJECT (about 64 bp) | none for the raw card; the constrained variant runs as FS-2 | TF-20 | DNB-TF-04 |
| G-63 | Korean low-vol / low-beta alpha tilt | KRX | DROP (CR-01) | beta 0.63-0.74; beat the market in crash windows | LO excess +1.1% (t 0.5) | CAPM alpha t 0.8 (EW) / 0.3 (VW) | long-only excess with t >= 2 net of 35 bp after beta attribution | TF-17 | DNB-TF-02 |
| G-64 | Attention-fade monthly exclusion screen (F5) or standalone card | KRX | DROP (CR-06) | events real over 5-20 days | B1 +1.40% net 35, -0.08% at 70 bp; break-even 68 bp | pre-gate REJECT | a daily-entry card test (BL-TF-02) | TF-14 | DNB-TF-01 |
| G-65 | Size as a signal | KRX/US | DROP | 1996-2026 EW L/S gross Sharpe 0.39 | 2016-26 Sharpe -0.05 | n/a | none (risk control and attribution factor only) | TF-18 | DNB-TF-03 |
| G-66 | Korean flow direction rule (foreign/institutional net buying) | KRX | DROP (CR-03) | lagged flows predict the next open (2003-11) | predicts next open only; 2026 sign break | not run (no t-1 history) | an open-leg test on >= 3 years of logged flows (G-11) | TF-39 | DNB-TF-06 |
| G-67 | US PEAD and US event drifts as standalone cards | US | DROP (CR-04) | PEAD was real historically (0.72%/month gross) | 0.26%/month net (t 1.60); inclusion effect 0.8% n.s. | n/a (no US stock panel) | none standalone; events stay as flags and confirmation inputs | TF-45 | DNB-TF-09 |
| G-68 | Quality counted as a crash hedge (weight 3) | US | DROP | quality is a sound composite leg (GP/A 0.37%/month net) | QUAL -34.1% vs -33.9% | n/a | none; quality stays a composite leg at weight 2 | TF-44 | DNB-TF-08 |
| G-69 | Product composites, factor-ETF rotation, sell-side levels, 13F cloning | US | DROP | investable, well-documented products | FFTY 3.52%/yr vs 13-14% | n/a | estimate revisions only, via the forward archive (BACKLOG) | TF-47 | DNB-TF-10 |
| G-70 | Classic technical indicators/rules and TradingView/CMT/retail-sourced strategies as signals | all | DO-NOT-BUILD (CR-12) | large practitioner literature; RSI14 contrarian gross Sharpe 0.36 on KRX (it is short-term reversal) | SPA p 0.880 / 0.82-0.97 | no rule family passes a data-snooping test | only via family gate + nine-step gate as a new card | TF-60 | DNB-TF-12 |
| G-71 | Short-horizon technical trading (intraday rules; KRX crosses, MA alignment, P > MA200 selection, limit-up chasing, volume-spike buying) | KRX/US | DROP | gross edges exist (SPY first-to-last half-hour 6.67%/yr gross) | 1-7 bp edges vs 25-46 bp round trips | pre-gate REJECT (break-even about 1-2 bp) | none at QUANTGEN costs | TF-61 | DNB-TF-13 |
| G-72 | US single-index trend / VT at 50 bp per side via KIS | US | DROP (REJECT) (CR-02) | protection is real at futures cost (PC-1 +3.8 to +14.7 pp at 5 bp) | PC-1 -10.7 pp (trend), +0.3 pp (VT15) | REJECT | futures-cost instrument (G-46) | TF-34 | DNB-TF-05 |
| G-73 | Deep price-pattern, order-book DL and LLM-news strategies | all | DROP (CR-11) | large gross Sharpes in papers (ChatGPT news 6.54 before costs) | decayed; unprofitable at 20 bp RT | n/a | none | TF-65 | DNB-TF-14 |
| G-74 | Macro x stock-signal interactions in a combiner | all | DROP (CR-11) | interaction terms raise in-sample fit | violates macro P1 | n/a | none (macro P1) | TF-66 | DNB-TF-15 |
| G-75 | Crypto short-term reversal (prior 2) | crypto | DROP (weight 0) (CR-10) | none locally | short-horizon evidence is momentum | n/a | a local crypto test showing 1-4-week reversal net of 10/20 bp | TF-68 | DNB-TF-16 |
| G-76 | G10 FX technical rules | FX | DROP (weight 0) | 1980-98 mean Sharpe 0.66 across 388 portfolios | 0.66 -> 0.06 OOS; V3 REJECT | QUANTGEN V3 REJECT | USD/KRW test (G-54) | TF-70 | DNB-TF-17 |
| G-77 | Context-brief anchors (-2.95%/month reversal; -6.13%/month high-turnover momentum) and Ilmanen per-factor haircuts | KRX/all | DROP (corrected anchors) | the figures are printed in the cited papers (as a slope / with unadjusted closes) | slope not spread; not reproduced; unverifiable | n/a | none | TF-19, TF-57 | CA-01, CA-02, CA-04 |

## 11. Golden values for the spec's acceptance tests

523 values in `results/r3_golden_values.csv` and `charts/golden_values.json` (497 traced, 20 derived, 6 not traced). The table below lists the values every BUILD NOW and FORWARD-SIM item must reproduce, plus the reference values that pin the engines; the CSV holds the rest under the same GV ids. Tolerance proposal: reproduce traced values to the printed precision (Level 1), derived values within 1 bp, and verdict strings exactly.

### 11.1 Pair-share computation for CR-07 (KRX daily all-stock file)

Source: `/home/claude/data_raw/marcap/data/marcap-2023..2026.parquet`, Market == KOSPI, all listed lines; common lines are codes ending in 0. Script `scripts/r3_01_pair_share.py`; outputs `results/r3_pair_share.csv`, `r3_pair_share_summary.csv`, `r3_pair_share_2026_daily.csv` (all four definitions, daily 2026).

| Date | KOSPI lines | Common lines | CR-07: (005930+005935+000660) / all lines | (005930+000660) / all lines | (005930+000660) / common lines | (005930+005935+000660) / (common + 005935) |
|---|---|---|---|---|---|---|
| 2023-12-28 | 953 | 839 | 29.29% | 26.88% | 27.79% | 29.55% |
| 2024-12-30 | 961 | 848 | 24.48% | 22.62% | 23.28% | 24.72% |
| 2025-12-30 | 958 | 847 | 36.13% | 34.04% | 35.05% | 36.42% |
| 2026-05-07 | 948 | 838 | 47.49% | 45.06% | 46.47% | 47.77% |
| 2026-06-22 | 946 | 836 | 58.08% | 55.67% | 57.31% | 58.34% |
| 2026-06-25 | 946 | 836 | 59.69% | 57.11% | 58.88% | 59.95% |
| 2026-06-30 | 945 | 835 | 57.89% | 55.43% | 57.10% | 58.15% |
| 2026-09-29 | 942 | 831 | 53.71% | 50.82% | 52.59% | 53.96% |

2026 series (r3_pair_share_summary.csv, file line = row + 1):

| Line | Item | Value |
|---|---|---|
| 2 | CR-07 share on 2026-09-29 | 0.537062 |
| 3 | CR-07 first session > 0.45 in 2026 | 2026-05-06 |
| 4 | CR-07 share on first session > 0.45 | 0.470159 |
| 5 | CR-07 2026 peak date | 2026-06-25 |
| 6 | CR-07 2026 peak share | 0.596875 |
| 7 | CR-07 sessions > 0.45 in 2026 (to 2026-09-29) | 99 |
| 8 | sessions in 2026 file (to 2026-09-29) | 181 |
| 9 | alt_pair_common_over_all_lines: first session > 0.45 in 2026 | 2026-05-07 |
| 10 | alt_pair_common_over_all_lines: 2026 peak date / share | 2026-06-25 / 0.571082 |
| 11 | alt_pair_common_over_all_lines: sessions > 0.45 in 2026 | 98 |
| 12 | alt_pair_common_over_common_only: first session > 0.45 in 2026 | 2026-05-06 |
| 13 | alt_pair_common_over_common_only: 2026 peak date / share | 2026-06-25 / 0.588825 |
| 14 | alt_pair_common_over_common_only: sessions > 0.45 in 2026 | 99 |
| 15 | alt_pair_incl_pref_over_common_plus_pref: first session > 0.45 in 2026 | 2026-05-06 |
| 16 | alt_pair_incl_pref_over_common_plus_pref: 2026 peak date / share | 2026-06-25 / 0.599477 |
| 17 | alt_pair_incl_pref_over_common_plus_pref: sessions > 0.45 in 2026 | 99 |

The executives' chair date "first above 0.45 on 7 May 2026" (R2_EXEC A5) belongs to the common-lines-over-all-lines definition; under CR-07 the cap first binds one session earlier, on 2026-05-06.

Golden values for RISK-1: GV-219..240 (r3_pair_share.csv lines 2-9; r3_pair_share_summary.csv lines 2-9).

### 11.2 Screens: SCR-1 (F4 lottery composite), SCR-2 (F6 dilution), SCR-3 (F1 highest-turnover quintile) and the dropped F5

KRX, 366 monthly formations 1996-03..2026-09, filtered minus unfiltered book, %/yr. B1 = EW ALL book; B2 = VW ALL 5%-capped; B3 = top-200 VW 5%-capped; B4 = 12-1 momentum top quintile EW. IR, t, years and drawdown at net 35; break-even = gross difference / extra one-way turnover (derived); sub-periods at net 35; gate = indicative steps passed of 8, verdict, deflated Sharpe pooled over 176 trials.

| Screen | Book | Gross | Net 35 | Net 70 | IR | NW t | Years + | dMDD | Break-even bp/side | Sub-periods 96-05 / 06-15 / 16-26 | Gate | GV ids | Source lines |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SCR-1 F4 | B1 | +3.39% | +3.08% | +2.76% | 1.53 | 8.34 | 0.90 | +1.70% | 380 | +4.31% / +2.81% / +2.20% | 7/8 REVISE, DSR 0.939 | GV-001..005, GV-007, GV-010, GV-105, GV-117..119, GV-126..128 | r2_kr_excl_summary.csv 13/11/12; r2_kr_excl_long.csv 637/652/667; r2_kr_excl_gate.csv 2 |
| SCR-1 F4 | B2 | +0.99% | +0.85% | +0.72% | 0.68 | 3.87 | 0.77 | +1.03% | 255 | - | 7/8 REVISE, DSR 0.001 | GV-027..031, GV-033, GV-036, GV-108, GV-132..134 | r2_kr_excl_summary.csv 145/143/144; r2_kr_excl_gate.csv 4 |
| SCR-1 F4 | B3 | +0.57% | +0.49% | +0.40% | 0.39 | 2.32 | 0.61 | +0.76% | 234 | - | 6/8 REJECT, DSR 0.000 | GV-053..057, GV-059, GV-062, GV-111, GV-138..140 | r2_kr_excl_summary.csv 277/275/276; r2_kr_excl_gate.csv 6 |
| SCR-1 F4 | B4 | +6.76% | +6.13% | +5.50% | 1.24 | 7.53 | 0.97 | +2.93% | 375 | +6.82% / +6.65% / +5.01% | 7/8 REVISE, DSR 0.563 | GV-079..083, GV-085, GV-088, GV-114, GV-123..125, GV-144..146 | r2_kr_excl_summary.csv 409/407/408; r2_kr_excl_long.csv 27565/27580/27595; r2_kr_excl_gate.csv 8 |
| SCR-2 F6 | B1 | +2.42% | +2.34% | +2.26% | 0.65 | 3.93 | 0.81 | +0.36% | 1057 | +2.92% / +2.83% / +1.34% | - | GV-014..018, GV-020, GV-023, GV-107, GV-120..122 | r2_kr_excl_summary.csv 19/17/18; r2_kr_excl_long.csv 1045/1060/1075 |
| SCR-2 F6 | B2 | +0.79% | +0.69% | +0.58% | 0.15 | 0.83 | 0.81 | +0.22% | 265 | - | - | GV-040..044, GV-046, GV-049, GV-110 | r2_kr_excl_summary.csv 151/149/150 |
| SCR-2 F6 | B3 | +0.41% | +0.29% | +0.18% | 0.06 | 0.32 | 0.61 | -0.13% | 124 | - | - | GV-066..070, GV-072, GV-075, GV-113 | r2_kr_excl_summary.csv 283/281/282 |
| SCR-2 F6 | B4 | +4.41% | +4.23% | +4.05% | 0.57 | 3.31 | 0.90 | +1.88% | 862 | - | - | GV-092..096, GV-098, GV-101, GV-116 | r2_kr_excl_summary.csv 415/413/414 |
| SCR-3 F1 | B1 | +4.78% | +4.28% | +3.78% | 1.15 | 6.62 | 0.94 | +2.41% | - | - | 7/8 REVISE, DSR 0.410 | GV-151..160 | r2_kr_excl_summary.csv 4/2/3; r2_kr_excl_gate.csv 3 |
| SCR-3 F1 | B4 | +8.62% | +7.81% | +7.00% | 1.02 | 6.20 | 0.94 | +6.38% | - | - | 7/8 REVISE, DSR 0.209 | GV-161..170 | r2_kr_excl_summary.csv 400/398/399; r2_kr_excl_gate.csv 9 |
| F5 (DROP) | B1 | - | - | - | - | - | - | - | 68 | - | - | GV-106 | r2_kr_excl_summary.csv 16/14 |
| F5 (DROP) | B2 | - | - | - | - | - | - | - | 21 | - | - | GV-109 | r2_kr_excl_summary.csv 148/146 |
| F5 (DROP) | B3 | - | - | - | - | - | - | - | 10 | - | - | GV-112 | r2_kr_excl_summary.csv 280/278 |
| F5 (DROP) | B4 | - | - | - | - | - | - | - | 76 | - | - | GV-115 | r2_kr_excl_summary.csv 412/410 |

Best of the 176 exclusion trials (B1, F4 at a 5% cut): pooled deflated Sharpe 0.979 (GV-150; r2_kr_excl_dsr_best.csv 2). The lab's step-9 column prints 0.4 x diff (B1/F4 +1.23%/yr, r2_kr_excl_gate.csv line 2); the spec's step 9 is 0.6 x OOS (section 12, CA-21).

### 11.3 Index protective scorecards (CARD-P checks vs the same-exposure static book S)

| Cell | Market | Period | Cost | PC-1 1x | PC-1 2x | PC-2 tail | PC-3 dSR | p non-inf. | PC-5 years | PC-6 plateau | Verdict | GV ids | Source lines |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KOSPI VT20 | KOSPI (rebuilt) | 1996-09-02..2026-09-29 | net KRX ETF 3bp | +6.5 | +6.4 | 0.70 | -0.001 | 0.051 | 0.70 | 1.00 | PASS | GV-303..310 | r2_idx_protective_scorecard.csv 5 |
| KOSPI multi-speed trend sleeve | KOSPI (rebuilt) | 1996-09-02..2026-09-29 | net KRX ETF 3bp | +8.9 | +8.4 | 0.77 | 0.186 | 0.008 | 0.60 | 0.75 | PASS | GV-311..318 | r2_idx_protective_scorecard.csv 3 |
| KOSPI unbounded trend x VT20 | KOSPI (rebuilt) | 1996-09-02..2026-09-29 | net KRX ETF 3bp | +11.3 | +9.4 | 0.55 | 0.231 | 0.007 | 0.57 | 0.88 | REVISE | GV-319..326 | r2_idx_protective_scorecard.csv 6 |
| KOSPI SMA200 | KOSPI (rebuilt) | 1996-09-02..2026-09-29 | net KRX ETF 3bp | +1.9 | -0.2 | 0.73 | 0.121 | 0.051 | 0.43 | 0.60 | INSUFFICIENT DATA (sufficiency) | GV-327..334 | r2_idx_protective_scorecard.csv 2 |
| KOSPI 12-month sign | KOSPI (rebuilt) | 1996-09-02..2026-09-29 | net KRX ETF 3bp | +4.7 | +4.6 | 0.88 | 0.082 | 0.083 | 0.63 | 0.20 | INSUFFICIENT DATA (sufficiency) | GV-335..342 | r2_idx_protective_scorecard.csv 4 |
| SPY VT15 at 50 bp | SPY | 1999-05-03..2021-03-31 | net US via KIS 50bp | +0.3 | -3.9 | 0.76 | -0.071 | 0.425 | 0.68 | 0.50 | REJECT | GV-343..350 | r2_idx_protective_scorecard.csv 12 |
| SPY trend sleeve at 50 bp | SPY | 1999-05-03..2021-03-31 | net US via KIS 50bp | -10.7 | -44.3 | 0.54 | -0.530 | 0.999 | 0.45 | 0.00 | REJECT | GV-351..358 | r2_idx_protective_scorecard.csv 10 |
| SPY trend x VT15 at 50 bp | SPY | 1999-05-03..2021-03-31 | net US via KIS 50bp | -7.9 | -43.9 | 0.47 | -0.541 | 0.998 | 0.50 | 0.00 | REJECT | GV-359..366 | r2_idx_protective_scorecard.csv 13 |
| SPY trend sleeve at 5 bp | SPY | 1999-05-03..2021-03-31 | net Futures 5bp | +14.7 | +13.2 | 0.54 | 0.012 | 0.257 | 0.59 | 0.62 | INSUFFICIENT DATA (inconclusive) | GV-367..374 | r2_idx_protective_scorecard.csv 17 |

### 11.4 FS-1 floored trend x VT20 and its comparison cells (KOSPI rebuilt 1996-09-02..2026-09-29, net 3 bp per side)

| Cell | Avg exposure | Max DD | PC-1 vs own S | PC-2 tail | dSR | Years + | Verdict | 1997-98 | 2026 crash | GV ids | Source lines |
|---|---|---|---|---|---|---|---|---|---|---|---|
| KOSPI ENSxVT overlay clip[0.5,1] | 0.61 | -29.39% | +15.4 | 0.64 | 0.156 | 0.63 | PASS | -28.62% | -9.78% | GV-375..383 | r2_idx_overlay_vs_sleeve.csv 12 |
| KOSPI ENSxVT sleeve (0 allowed) | 0.51 | -27.72% | +11.3 | 0.55 | 0.231 | 0.57 | REVISE | -9.68% | -9.78% | GV-384..392 | r2_idx_overlay_vs_sleeve.csv 11 |
| KOSPI ENSxVT overlay 0.5+0.5x (E3 long/half) | 0.68 | -36.19% | +13.0 | 0.65 | 0.115 | 0.67 | PASS | -30.84% | -11.02% | GV-393..401 | r2_idx_overlay_vs_sleeve.csv 13 |
| KOSPI ENS sleeve (0 allowed) | 0.58 | -34.15% | +8.9 | 0.77 | 0.186 | 0.60 | PASS | -6.89% | -31.30% | GV-402..410 | r2_idx_overlay_vs_sleeve.csv 2 |
| KOSPI ENS overlay clip[0.5,1] | 0.70 | -39.16% | +10.8 | 0.91 | 0.124 | 0.67 | REJECT | -39.16% | -31.30% | GV-411..419 | r2_idx_overlay_vs_sleeve.csv 3 |

Not evaluated: plateau (PC-6) and start-date sweep of the floored product (GV-518). The first FORWARD-SIM release must add the plateau (PC-6) and the start-date sweep for the primary cell.

### 11.5 Start-date sensitivity (KOSPI rebuilt, net 3 bp; verdict and PC-1 in pp)

| Start | KOSPI VT20 | KOSPI trend sleeve | KOSPI unbounded trend x VT20 | GV ids | Source lines |
|---|---|---|---|---|---|
| 1996-06-03 | PASS (+5.7) | REVISE (+11.0) | REVISE (+13.3) | GV-420..422 | r2_idx_start_date_sensitivity.csv 5/3/6 |
| 2001-01-02 | PASS (+10.6) | INSUFFICIENT DATA (inconclusive) (+6.1) | REVISE (+7.2) | GV-423..425 | r2_idx_start_date_sensitivity.csv 25/23/26 |
| 2006-01-02 | PASS (+11.6) | INSUFFICIENT DATA (inconclusive) (+5.7) | INSUFFICIENT DATA (inconclusive) (+7.3) | GV-426..428 | r2_idx_start_date_sensitivity.csv 30/28/31 |
| 2011-01-03 | INSUFFICIENT DATA (inconclusive) (+4.8) | REJECT (-3.5) | REJECT (-1.4) | GV-429..431 | r2_idx_start_date_sensitivity.csv 35/33/36 |
| 2016-01-04 | INSUFFICIENT DATA (inconclusive) (+4.4) | REJECT (-2.9) | REJECT (+0.9) | GV-432..434 | r2_idx_start_date_sensitivity.csv 40/38/41 |

### 11.6 FS-3 Korean low volatility against the same-beta static book S_beta (KRX 1996-2026, net 35, rf 0)

| Comparison | Beta | Max DD book | Max DD S_beta | dMDD (pp) | Sharpe book | Sharpe S_beta | Tail ratio | GV ids | Source lines |
|---|---|---|---|---|---|---|---|---|---|
| low-vol Q1 EW vs VW ALL universe | 0.631 | -73.87% | -51.50% | -22.4 | 0.412 | 0.357 | 0.985 | GV-469..475 | c12_lowvol_samebeta.csv 2 |
| low-vol Q1 VW vs VW ALL universe | 0.742 | -64.88% | -57.76% | -7.1 | 0.331 | 0.357 | 0.978 | GV-476..482 | c12_lowvol_samebeta.csv 6 |
| low-vol Q1 EW vs EW ALL universe | 0.702 | -73.87% | -61.64% | -12.2 | 0.412 | 0.244 | 0.967 | GV-483..489 | c12_lowvol_samebeta.csv 10 |

### 11.7 MOM-1 (R-03 on KRX momentum) and MOM-2

KRX 12-1 momentum, ALL quintiles, net 35 Sharpe:

| Sleeve and control | 1996-04..2026-09 | 2016-01..2026-09 | GV ids | Source lines |
|---|---|---|---|---|
| LS_EW (ALL quintiles) static | 0.20 | -0.20 | GV-251..252 | r2_kr_crash_controls.csv 44/70 |
| LS_EW (ALL quintiles) VS (own vol, 12%, cap 1) | 0.27 | -0.24 | GV-253..254 | r2_kr_crash_controls.csv 158/184 |
| LS_EW (ALL quintiles) VS x DM | 0.31 | -0.28 | GV-255..256 | r2_kr_crash_controls.csv 386/412 |
| LS_VW (ALL quintiles) static | 0.25 | 0.32 | GV-257..258 | r2_kr_crash_controls.csv 500/526 |
| LS_VW (ALL quintiles) VS (own vol, 12%, cap 1) | 0.31 | 0.23 | GV-259..260 | r2_kr_crash_controls.csv 614/640 |
| LS_VW (ALL quintiles) VS x DM | 0.37 | 0.25 | GV-261..262 | r2_kr_crash_controls.csv 842/868 |

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line |
|---|---|---|---|---|---|---|---|
| GV-241 | 12-1 L/S VW static: cumulative return 2026-06-22..07-30 | KRX | 2026-06-22..07-30 | net 35 bp/side | -40.29% | r2/kr/results/r2_kr_crash_windows.csv | 60 |
| GV-242 | 12-1 L/S VW own-vol scaled (R-03): cumulative return 2026-06-22..07-30 | KRX | 2026-06-22..07-30 | net 35 bp/side | -10.52% | r2/kr/results/r2_kr_crash_windows.csv | 68 |
| GV-243 | 12-1 L/S VW static at the same average exposure (0.53): cumulative return 2026-06-22..07-30 | KRX | 2026-06-22..07-30 | net 35 bp/side | -22.95% | r2/kr/results/r2_kr_crash_windows.csv | 76 |
| GV-244 | 12-1 L/S EW static: cumulative return 2026-06-22..07-30 | KRX | 2026-06-22..07-30 | net 35 bp/side | -24.77% | r2/kr/results/r2_kr_crash_windows.csv | 7 |
| GV-245 | 12-1 L/S EW own-vol scaled (R-03): cumulative return 2026-06-22..07-30 | KRX | 2026-06-22..07-30 | net 35 bp/side | -12.55% | r2/kr/results/r2_kr_crash_windows.csv | 15 |
| GV-246 | 12-1 long-only EW excess, own-vol scaled: cumulative return 2026-06-22..07-30 | KRX | 2026-06-22..07-30 | net 35 bp/side | -13.73% | r2/kr/results/r2_kr_crash_windows.csv | 121 |
| GV-247 | LS_EW (ALL quintiles): R-03 weight on 2026-06-22 | KRX | 2026-06-22 | weight | 0.55 | r2/kr/results/r2_kr_crash_exposure_2026.csv | 3 |
| GV-248 | LS_VW (ALL quintiles): R-03 weight on 2026-06-22 | KRX | 2026-06-22 | weight | 0.27 | r2/kr/results/r2_kr_crash_exposure_2026.csv | 7 |
| GV-249 | E5 top500 D10-D1 EW: R-03 weight on 2026-06-22 | KRX | 2026-06-22 | weight | 0.35 | r2/kr/results/r2_kr_crash_exposure_2026.csv | 19 |
| GV-250 | E5 top500 D10-D1 VW: R-03 weight on 2026-06-22 | KRX | 2026-06-22 | weight | 0.20 | r2/kr/results/r2_kr_crash_exposure_2026.csv | 23 |
| GV-263 | number of D-M gate onsets on the rebuilt KOSPI | KRX | 1996-2026 | count | 9 | r2/kr/results/r2_kr_dm_gate_onsets.csv | 2-10 |

### 11.8 IDX-1 KOSPI VT20: reproduction of the macro spec's golden values (rebuilt KOSPI 2016-01-04..2026-09-29; values are fractions as printed in the file; gross unless the quantity says net)

| GV | Quantity | Value | Line (r2_idx_golden_values.csv) | Check against the spec |
|---|---|---|---|---|
| GV-273 | VT20 Sharpe (gross) | 0.6329 | 2 | spec value 0.638; within Level-1 True |
| GV-274 | Buy-and-hold Sharpe | 0.6284 | 3 | spec value 0.634; within Level-1 True |
| GV-275 | VT20 max DD (gross) | -0.3700 | 4 | spec value -0.368; within Level-1 True |
| GV-276 | Buy-and-hold max DD | -0.4405 | 5 | spec value -0.439; within Level-1 True |
| GV-277 | VT20 average exposure | 0.9255 | 6 | spec value 0.925; within Level-1 True |
| GV-278 | Static S max DD | -0.4145 | 7 | spec value -0.413; within Level-1 True |
| GV-279 | dMDD VT20 vs S, gross (pp) | 4.4581 | 8 | spec value 4.5; within Level-1 True |
| GV-280 | VT20 Sharpe net 3 bp | 0.6301 | 9 | spec value 0.635; within Level-1 True |
| GV-281 | VT20 Sharpe net 6 bp | 0.6274 | 10 | spec value 0.632; within Level-1 True |
| GV-282 | dMDD VT20 vs S, net 3 bp (pp) | 4.4281 | 11 | spec value 4.4; within Level-1 True |
| GV-283 | dSR VT20 - buy-and-hold (gross) | 0.0045 | 12 | spec value 0.004; within Level-1 True |
| GV-300 | VT20 weight earning on 2026-06-22 | 0.3025 | 29 | spec value 0.3024; within Level-1 True |
| GV-301 | VT20 weight earning on 2026-06-23 | 0.3310 | 30 | spec value 0.3309; within Level-1 True |
| GV-302 | VT20 weight earning on 2026-07-30 | 0.2485 | 31 | spec value 0.2484; within Level-1 True |

| Window | VT20 | Buy-and-hold | GV ids | Source lines |
|---|---|---|---|---|
| Jul-2026 crash | -0.1224 | -0.3861 | GV-284..285 | r2_idx_golden_values.csv 13/14 |
| Mar-2026 | -0.0791 | -0.1988 | GV-286..287 | r2_idx_golden_values.csv 15/16 |
| Aug-2024 | -0.0788 | -0.0546 | GV-288..289 | r2_idx_golden_values.csv 17/18 |
| Apr-2025 | -0.1167 | -0.1201 | GV-290..291 | r2_idx_golden_values.csv 19/20 |
| 2020 crash | -0.2582 | -0.3405 | GV-292..293 | r2_idx_golden_values.csv 21/22 |
| 2020 rebound | 0.2584 | 0.4980 | GV-294..295 | r2_idx_golden_values.csv 23/24 |
| H1-2026 | 0.5170 | 1.0108 | GV-296..297 | r2_idx_golden_values.csv 25/26 |
| 30 Jul-30 Sep 2026 | 0.0619 | 0.2282 | GV-298..299 | r2_idx_golden_values.csv 27/28 |

### 11.9 INV-5 evidence: name-level stops on KRX top-500 12-1 deciles (2000-01..2026-09, net 35 Sharpe)

| Weighting | no stop | 15% stop, exit next close | 15% stop, exit same close | 10% stop, exit next close | GV ids | Source lines |
|---|---|---|---|---|---|---|
| EW | 0.04 | -0.15 | -0.11 | -0.19 | GV-509..512 | r2_kr_stoploss.csv 3/5/7/9 |
| VW | 0.28 | 0.07 | 0.08 | 0.01 | GV-513..516 | r2_kr_stoploss.csv 11/13/15/17 |

### 11.10 INV-1 / INV-2 execution invariants (KRX)

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-171 | B1 none: share of entries bought at a locked limit-up close | KRX | 1996-03..2026-09 | count share | 6.30% | r2/kr/results/r2_kr_excl_limitlock.csv | 2 | traced |
| GV-172 | B1 none: share of exits sold at a locked limit-down close | KRX | 1996-03..2026-09 | count share | 2.06% | r2/kr/results/r2_kr_excl_limitlock.csv | 2 | traced |
| GV-173 | B1 F4: share of entries bought at a locked limit-up close | KRX | 1996-03..2026-09 | count share | 1.94% | r2/kr/results/r2_kr_excl_limitlock.csv | 3 | traced |
| GV-174 | B1 F4: share of exits sold at a locked limit-down close | KRX | 1996-03..2026-09 | count share | 1.39% | r2/kr/results/r2_kr_excl_limitlock.csv | 3 | traced |
| GV-197 | locked limit-up, next-open entry, excess vs EW liquid universe: t+5 / t+20 (bp), n | KRX | 2015-06..2026-09 (events); 2002-2026 (overnight) | gross event returns | -394 / -579 bp, t -14.6 / -11.2, n 11,186; +328 bp; E7 pipeline reproduces -98.4 bp volume-spike figure exactly | r2/verification/exec_verification_log.csv | 83 | traced |
| GV-198 | locked limit-down: t+1 / t+5 / t+20 (bp), n | KRX | 2015-06..2026-09 (events); 2002-2026 (overnight) | gross event returns | -630 / -722 / -1,036 bp, n 815 | r2/verification/exec_verification_log.csv | 85 | traced |
| GV-199 | volume spike (>= 5x, r >= +5%): t+5 / t+20 (bp) | KRX | 2015-06..2026-09 (events); 2002-2026 (overnight) | gross event returns | -43 / -93 bp, t -4.9 / -6.5; -106 / -74 / -144 bp | r2/verification/exec_verification_log.csv | 84 | traced |
| GV-200 | 20-day run-up >= +50%: t+20 (bp) | KRX | 2015-06..2026-09 (events); 2002-2026 (overnight) | gross event returns | -95 bp (median -757) | r2/verification/exec_verification_log.csv | 86 | traced |
| GV-201 | KRX top-500 EW 12-1 D10-D1: overnight vs intraday %/yr | KRX | 2015-06..2026-09 (events); 2002-2026 (overnight) | gross event returns | overnight +18.4%/yr (t 8.7), intraday -7.9%/yr (t -1.8); 2015-26 +26.0% vs -21.9% | r2/verification/exec_verification_log.csv | 22 | traced |
| GV-202 | eligibility same-day vs lagged one day: EW benchmark %/yr | KRX | 2015-06..2026-09 (events); 2002-2026 (overnight) | gross event returns | corrected benchmark (eligibility at t-1) +0.5%/yr; event numbers above | r2/verification/exec_verification_log.csv | 87 | traced |

### 11.11 DATA-2, DATA-3 and the rebuilt-KOSPI check

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-203 | Eom design, adjusted returns, all caps, high-turnover W-L, %/month | KRX | 2000-07..2019-06 | gross | +1.43 | r2/kr/results/r2_kr_mom_claims_long.csv | 15 | traced |
| GV-204 | Eom design, adjusted returns, all caps, high-turnover W-L, NW t | KRX | 2000-07..2019-06 | gross | 3.26 | r2/kr/results/r2_kr_mom_claims_long.csv | 7 | traced |
| GV-205 | same with unadjusted closes, %/month | KRX | 2000-07..2019-06 | gross | -11.37 | r2/kr/results/r2_kr_mom_claims_long.csv | 183 | traced |
| GV-206 | same with unadjusted closes, NW t | KRX | 2000-07..2019-06 | gross | -5.42 | r2/kr/results/r2_kr_mom_claims_long.csv | 175 | traced |
| GV-207 | adjusted, ex-bottom-20% caps, %/month | KRX | 2000-07..2019-06 | gross | +1.66 | r2/kr/results/r2_kr_mom_claims_long.csv | 51 | traced |
| GV-208 | adjusted, ex-bottom-20% caps, NW t | KRX | 2000-07..2019-06 | gross | 4.50 | r2/kr/results/r2_kr_mom_claims_long.csv | 43 | traced |
| GV-209 | share of kept daily returns where \|Close/prevClose-1 - r\| > 0.5% (KRX base-price adjustments) | KRX | 1995-2026 | count | 12,186 of 13,949,140 = 0.0874% | kr/results/kr_validation.csv | 15 | traced |
| GV-463 | SPY 1999-03..2021-03 SMA10: Sharpe inflation from month-average prices | US | 1999-03..2021-03 | gross | +0.10 | r2/idx/results/r2_idx_averaging_bias.csv | 2 | traced |
| GV-464 | SPY 1999-03..2021-03 TSM12: Sharpe inflation from month-average prices | US | 1999-03..2021-03 | gross | +0.23 | r2/idx/results/r2_idx_averaging_bias.csv | 7 | traced |
| GV-465 | S&P 500 2000-03..2018-12 SMA10: Sharpe inflation from month-average prices | US | 2000-03..2018-12 | gross | +0.19 | r2/idx/results/r2_idx_averaging_bias.csv | 3 | traced |
| GV-466 | S&P 500 2000-03..2018-12 TSM12: Sharpe inflation from month-average prices | US | 2000-03..2018-12 | gross | +0.25 | r2/idx/results/r2_idx_averaging_bias.csv | 8 | traced |
| GV-467 | SPY monthly lag-1 autocorrelation, acf1_month_end | US | 1998-02..2021-03 | gross | 0.057 | r2/idx/results/r2_idx_averaging_autocorr.csv | 2 | traced |
| GV-468 | SPY monthly lag-1 autocorrelation, acf1_month_average | US | 1998-02..2021-03 | gross | 0.206 | r2/idx/results/r2_idx_averaging_autocorr.csv | 2 | traced |
| GV-440 | rebuilt / official KOSPI change ratio 2007-10-31..2020-03-19 | KOSPI | 2007-10-31..2020-03-19 | price index | 0.9999 | kr/results/kr_index_sanity.csv | 2 | traced |
| GV-441 | rebuilt / official KOSPI change ratio 2007-10-31..2021-07-06 | KOSPI | 2007-10-31..2021-07-06 | price index | 0.9987 | kr/results/kr_index_sanity.csv | 3 | traced |
| GV-442 | rebuilt / official KOSPI change ratio 2007-10-31..2026-06-22 | KOSPI | 2007-10-31..2026-06-22 | price index | 1.0006 | kr/results/kr_index_sanity.csv | 4 | traced |
| GV-443 | rebuilt / official KOSPI change ratio 2007-10-31..2026-07-30 | KOSPI | 2007-10-31..2026-07-30 | price index | 1.0010 | kr/results/kr_index_sanity.csv | 5 | traced |
| GV-444 | rebuilt / official KOSPI change ratio 2020-03-19..2021-07-06 | KOSPI | 2020-03-19..2021-07-06 | price index | 0.9989 | kr/results/kr_index_sanity.csv | 6 | traced |
| GV-445 | rebuilt / official KOSPI change ratio 2020-03-19..2026-06-22 | KOSPI | 2020-03-19..2026-06-22 | price index | 1.0007 | kr/results/kr_index_sanity.csv | 7 | traced |
| GV-446 | rebuilt / official KOSPI change ratio 2020-03-19..2026-07-30 | KOSPI | 2020-03-19..2026-07-30 | price index | 1.0011 | kr/results/kr_index_sanity.csv | 8 | traced |
| GV-447 | rebuilt / official KOSPI change ratio 2021-07-06..2026-06-22 | KOSPI | 2021-07-06..2026-06-22 | price index | 1.0019 | kr/results/kr_index_sanity.csv | 9 | traced |
| GV-448 | rebuilt / official KOSPI change ratio 2021-07-06..2026-07-30 | KOSPI | 2021-07-06..2026-07-30 | price index | 1.0023 | kr/results/kr_index_sanity.csv | 10 | traced |
| GV-449 | rebuilt / official KOSPI change ratio 2026-06-22..2026-07-30 | KOSPI | 2026-06-22..2026-07-30 | price index | 1.0004 | kr/results/kr_index_sanity.csv | 11 | traced |

### 11.12 DATA-5 regime flags

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-210 | full short-sale ban regime (first ban day; resumption) | KRX | as stated | dates / rates | Ban announced 2023-11-03 (first ban day 2023-11-06); resumption 2025-03-31; NSDS, 105%, 90 days/12 months | r2/verification/prof_verification_log.csv | 62 | traced |
| GV-211 | sell tax path (status MATCH; value as printed and confirmed) | KRX | as stated | dates / rates | Sell tax 0.20% on KOSPI (0.05 + 0.15 rural) and KOSDAQ from 2026-01-01; 0.15% in 2025; about 0.30% in 2019 | r2/verification/prof_verification_log.csv | 63 | traced |
| GV-212 | KOSDAQ up-limit closes per 10,000 stock-days | KRX | as stated | dates / rates | 51.1 (2026); 24.5 (2024); 26.8 (2025); KOSPI 27.5 (2026) | r2/verification/prof_verification_log.csv | 96 | traced |
| GV-213 | sell tax by year (incl. rural special tax) | KRX | as stated | dates / rates | KOSPI and KOSDAQ 0.18 / 0.15 / 0.20% incl. rural special tax | r2/verification/exec_verification_log.csv | 19 | traced |
| GV-214 | daily price limit widened to +-30% | KRX | as stated | dates / rates | 15 Jun 2015 | r2/verification/exec_verification_log.csv | 25 | traced |
| GV-215 | KOSPI return on 2025-03-31 (short-sale resumption day) | KRX | as stated | dates / rates | -3.00% | r2/verification/exec_verification_log.csv | 79 | traced |
| GV-216 | short-sale ban regimes | KRX | as stated | dates | 1 Oct 2008-31 May 2009; 11 Aug-9 Nov 2011; 16 Mar 2020 (partial lift 3 May 2021); 6 Nov 2023-30 Mar 2025 | research_notes/QUANTGEN technical and fundamental signals/R2_EXEC_chair_resolution.md | 142 | traced |
| GV-217 | short-sale regimes incl. index-only period | KRX | as stated | dates | 2020-03-16..2021-05-02 full, then index stocks only until 2023-11-05; full ban 2023-11-06..2025-03-30; resumed 2025-03-31 | research_notes/QUANTGEN technical and fundamental signals/R2_PROF_chair_resolution.md | 205 | traced |
| GV-218 | Value-up regime split date for Korean value/payout tests | KRX | as stated | dates | 2024-02-26 | research_notes/QUANTGEN technical and fundamental signals/R2_PROF_chair_resolution.md | 187 | traced |

### 11.13 FS-2 constrained KRX momentum (FORWARD-SIM)

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-264 | low-turnover 12-1 winners minus EW universe, %/yr | KRX | full | net 35 bp/side | +9.69% | r2/kr/results/r2_kr_mom_grid_long.csv | 1120 | traced |
| GV-265 | same, NW t | KRX | full | net 35 bp/side | 2.77 | r2/kr/results/r2_kr_mom_grid_long.csv | 1123 | traced |
| GV-266 | high-turnover 12-1 winners minus EW universe, %/yr | KRX | full | net 35 bp/side | -11.57% | r2/kr/results/r2_kr_mom_grid_long.csv | 2856 | traced |
| GV-267 | same, NW t | KRX | full | net 35 bp/side | -4.18 | r2/kr/results/r2_kr_mom_grid_long.csv | 2859 | traced |
| GV-268 | low-turnover winners minus EW universe, 2015-07..2024-12 | KRX | 2015-07..2024-12 | net 35 bp/side | -0.08% | r2/kr/results/r2_kr_mom_grid_long.csv | 1158 | traced |
| GV-269 | 12-7 L/S quintiles EW net-35 Sharpe | KRX | full | net 35 bp/side | 0.20 | r2/kr/results/r2_kr_mom_grid_long.csv | 6144 | traced |
| GV-270 | same 2016-2026 | KRX | 2016-01..2026-09 | net 35 bp/side | -0.01 | r2/kr/results/r2_kr_mom_grid_long.csv | 6194 | traced |
| GV-271 | 12-1 L/S quintiles EW net-35 Sharpe | KRX | full | net 35 bp/side | 0.20 | r2/kr/results/r2_kr_mom_grid_long.csv | 68 | traced |
| GV-272 | same 2016-2026 | KRX | 2016-01..2026-09 | net 35 bp/side | -0.20 | r2/kr/results/r2_kr_mom_grid_long.csv | 118 | traced |

### 11.14 Index crash window 2026-06-22..07-30

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-435 | KOSPI buy-and-hold: 2026-06-22..07-30 return | KOSPI (rebuilt) | 2026-06-23..2026-07-30 returns | net 3 bp/side | -38.61% | r2/idx/results/r2_idx_windows.csv | 3 | traced |
| GV-436 | KOSPI VT: 2026-06-22..07-30 return | KOSPI (rebuilt) | 2026-06-23..2026-07-30 returns | net 3 bp/side | -12.25% | r2/idx/results/r2_idx_windows.csv | 83 | traced |
| GV-437 | KOSPI ENSxVT: 2026-06-22..07-30 return | KOSPI (rebuilt) | 2026-06-23..2026-07-30 returns | net 3 bp/side | -9.78% | r2/idx/results/r2_idx_windows.csv | 103 | traced |
| GV-438 | KOSPI SMA200: 2026-06-22..07-30 return | KOSPI (rebuilt) | 2026-06-23..2026-07-30 returns | net 3 bp/side | -37.86% | r2/idx/results/r2_idx_windows.csv | 23 | traced |
| GV-439 | KOSPI ENS: 2026-06-22..07-30 return | KOSPI (rebuilt) | 2026-06-23..2026-07-30 returns | net 3 bp/side | -31.30% | r2/idx/results/r2_idx_windows.csv | 43 | traced |

### 11.15 GOV-3 attribution, GOV-4 / GOV-5 gate harness, GOV-7 break-even screen

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-490 | low-vol Q1 EW: beta to VW market | KRX | 1996-2026 | net 35 bp/side | 0.63 | r2/kr/results/r2_kr_lowvol.csv | 14 | traced |
| GV-491 | low-vol Q1 EW: CAPM alpha, rf = 0 | KRX | 1996-2026 | net 35 bp/side | +2.23% | r2/kr/results/r2_kr_lowvol.csv | 14 | traced |
| GV-492 | low-vol Q1 EW: alpha t | KRX | 1996-2026 | net 35 bp/side | 0.80 | r2/kr/results/r2_kr_lowvol.csv | 14 | traced |
| GV-493 | low-vol Q1 VW: beta to VW market | KRX | 1996-2026 | net 35 bp/side | 0.74 | r2/kr/results/r2_kr_lowvol.csv | 38 | traced |
| GV-494 | low-vol Q1 VW: CAPM alpha, rf = 0 | KRX | 1996-2026 | net 35 bp/side | +0.73% | r2/kr/results/r2_kr_lowvol.csv | 38 | traced |
| GV-495 | low-vol Q1 VW: alpha t | KRX | 1996-2026 | net 35 bp/side | 0.34 | r2/kr/results/r2_kr_lowvol.csv | 38 | traced |
| GV-496 | US Fama-MacBeth beta slope, %/yr (28 portfolios) | US | 1954-01..2017-03 | gross | +0.46% | us/results/us_C_factors.csv | 31 | traced |
| GV-450 | kospi_cbb126: false-pass rate of step2_bootstrap at true Sharpe 0, 10 years (10-session blocks) | simulated | 10 years | gross | 8.0% | r2/idx/results/r2_idx_gate_sim.csv | 522 | traced |
| GV-451 | kospi_cbb126: false-pass rate of step8_years at true Sharpe 0, 10 years (10-session blocks) | simulated | 10 years | gross | 23.8% | r2/idx/results/r2_idx_gate_sim.csv | 524 | traced |
| GV-452 | kospi_cbb126_signflip: false-pass rate of step2_bootstrap at true Sharpe 0, 10 years (10-session blocks) | simulated | 10 years | gross | 5.0% | r2/idx/results/r2_idx_gate_sim.csv | 3382 | traced |
| GV-453 | kospi_cbb126_signflip: false-pass rate of step8_years at true Sharpe 0, 10 years (10-session blocks) | simulated | 10 years | gross | 31.2% | r2/idx/results/r2_idx_gate_sim.csv | 3384 | traced |
| GV-454 | iid_normal: false-pass rate of step2_bootstrap at true Sharpe 0, 10 years (10-session blocks) | simulated | 10 years | gross | 3.9% | r2/idx/results/r2_idx_gate_sim.csv | 6242 | traced |
| GV-455 | iid_normal: false-pass rate of step8_years at true Sharpe 0, 10 years (10-session blocks) | simulated | 10 years | gross | 29.5% | r2/idx/results/r2_idx_gate_sim.csv | 6244 | traced |
| GV-457 | kospi_cbb126: step-5 pass rate with NO edge (strategy Sharpe 0.4 = benchmark 0.4, rho 0.5), 10 years, nominal 10% | simulated | 10 years | gross | 13.7% | r2/idx/results/r2_idx_gate_sim.csv | 616 | traced |
| GV-458 | kospi_cbb126: step-5 pass rate with NO edge (strategy Sharpe 0.4 = benchmark 0.4, rho 0.5), 18 years, nominal 10% | simulated | 18 years | gross | 12.8% | r2/idx/results/r2_idx_gate_sim.csv | 1396 | traced |
| GV-459 | kospi_cbb126: step-5 pass rate with NO edge (strategy Sharpe 0.4 = benchmark 0.4, rho 0.5), 30 years, nominal 10% | simulated | 30 years | gross | 13.2% | r2/idx/results/r2_idx_gate_sim.csv | 2176 | traced |
| GV-456 | kospi_cbb126: joint steps 2+3+5+8 (N 1, rho 0.5) false-pass rate at true Sharpe 0, 10 years | simulated | 10 years | gross | 0.5% | r2/idx/results/r2_idx_gate_sim.csv | 539 | traced |
| GV-460 | true Sharpe 0.3: years to 50% / 80% power at step 2 | simulated | - | gross | 28.7 / >50 | r2/idx/results/r2_idx_gate_power_years.csv | 337 | traced |
| GV-461 | true Sharpe 0.4: years to 50% / 80% power at step 2 | simulated | - | gross | 15.8 / 40.3 | r2/idx/results/r2_idx_gate_power_years.csv | 363 | traced |
| GV-462 | true Sharpe 0.5: years to 50% / 80% power at step 2 | simulated | - | gross | 10.5 / 25.7 | r2/idx/results/r2_idx_gate_power_years.csv | 389 | traced |
| GV-189 | REV_1W EW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 12.5 | kr/results/kr_key_numbers.csv | 30 | derived |
| GV-190 | REV_1W VW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 22.2 | kr/results/kr_key_numbers.csv | 31 | derived |
| GV-191 | REV_1M EW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 29.6 | kr/results/kr_key_numbers.csv | 6 | derived |
| GV-192 | MOM_12_1 EW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 63.7 | kr/results/kr_key_numbers.csv | 2 | derived |
| GV-193 | HIGH52 EW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 56.4 | kr/results/kr_key_numbers.csv | 8 | derived |
| GV-194 | VOL_3M EW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 137.2 | kr/results/kr_key_numbers.csv | 10 | derived |
| GV-195 | TURN_1M_LOW EW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 141.8 | kr/results/kr_key_numbers.csv | 14 | derived |
| GV-196 | MAX_1M EW L/S quintiles: break-even cost per side (bp) = gross /yr / turnover /yr (both legs) | KRX | 1996-03..2026-09 | derived | 61.2 | kr/results/kr_key_numbers.csv | 12 | derived |

### 11.16 R1 KRX engine regression (reference values the rebuilt engine must reproduce)

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-175 | TURN_1M_LOW EW: universe minus highest-turnover quintile, excess over EW universe | KRX | 1996-03..2026-09 | net 35 bp/side | +3.62% | kr/results/kr_key_numbers.csv | 14 | traced |
| GV-176 | TURN_1M_LOW EW: same, NW t | KRX | 1996-03..2026-09 | net 35 bp/side | 5.63 | kr/results/kr_key_numbers.csv | 14 | traced |
| GV-177 | VOL_3M EW: universe minus most volatile quintile, excess over EW universe | KRX | 1996-03..2026-09 | net 35 bp/side | +2.98% | kr/results/kr_key_numbers.csv | 10 | traced |
| GV-178 | VOL_3M EW: same, NW t | KRX | 1996-03..2026-09 | net 35 bp/side | 4.67 | kr/results/kr_key_numbers.csv | 10 | traced |
| GV-179 | MOM_12_1 EW: 12-1 momentum L/S quintiles, gross %/yr | KRX | 1996-03..2026-09 | gross | +9.34% | kr/results/kr_key_numbers.csv | 2 | traced |
| GV-180 | MOM_12_1 EW: same, gross Sharpe | KRX | 1996-03..2026-09 | gross | 0.447 | kr/results/kr_key_numbers.csv | 2 | traced |
| GV-181 | MOM_12_1 EW: same, net-35 Sharpe | KRX | 1996-03..2026-09 | net 35 bp/side | 0.201 | kr/results/kr_key_numbers.csv | 2 | traced |
| GV-182 | MOM_12_1 EW: 12-1 long-only top quintile excess over EW universe | KRX | 1996-03..2026-09 | net 35 bp/side | -1.34% | kr/results/kr_key_numbers.csv | 2 | traced |
| GV-183 | REV_1W EW: weekly reversal L/S net-35 Sharpe | KRX | 1996-03..2026-09 | net 35 bp/side | -1.782 | kr/results/kr_key_numbers.csv | 30 | traced |
| GV-184 | REV_1W VW: weekly reversal L/S net-35 Sharpe (VW) | KRX | 1996-03..2026-09 | net 35 bp/side | -0.825 | kr/results/kr_key_numbers.csv | 31 | traced |
| GV-185 | REV_1M EW: 1-month reversal L/S net-35 Sharpe | KRX | 1996-03..2026-09 | net 35 bp/side | -0.082 | kr/results/kr_key_numbers.csv | 6 | traced |
| GV-186 | REV_1M VW: 1-month reversal L/S net-35 Sharpe (VW) | KRX | 1996-03..2026-09 | net 35 bp/side | -0.450 | kr/results/kr_key_numbers.csv | 7 | traced |
| GV-187 | VOL_3M EW: low-vol long-only top quintile excess over EW universe | KRX | 1996-03..2026-09 | net 35 bp/side | +1.08% | kr/results/kr_key_numbers.csv | 10 | traced |
| GV-188 | VOL_3M VW: low-vol long-only top quintile excess over VW universe | KRX | 1996-03..2026-09 | net 35 bp/side | -1.78% | kr/results/kr_key_numbers.csv | 11 | traced |

### 11.17 DROP evidence kept as regression values (KRX reversal) and CRY-1

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-503 | ALL VW deciles: 1-month reversal losers minus winners, %/month (NW t) | KRX | 1996-04..2026-09 | gross | +0.57 (0.9) | r2/kr/results/r2_kr_reversal.csv | 17 | traced |
| GV-504 | ALL VW deciles: 1-month reversal losers minus winners, %/month (NW t) | KRX | 1996-04..2026-09 | net35 | -0.68 (-1.1) | r2/kr/results/r2_kr_reversal.csv | 22 | traced |
| GV-505 | ALL EW deciles: 1-month reversal losers minus winners, %/month (NW t) | KRX | 1996-04..2026-09 | gross | +1.43 (3.1) | r2/kr/results/r2_kr_reversal.csv | 47 | traced |
| GV-506 | ALL EW deciles: 1-month reversal losers minus winners, %/month (NW t) | KRX | 1996-04..2026-09 | net35 | +0.23 (0.5) | r2/kr/results/r2_kr_reversal.csv | 52 | traced |
| GV-507 | ALL VW quintiles: 1-month reversal losers minus winners, %/month (NW t) | KRX | 1996-04..2026-09 | net35 | -1.10 (-2.5) | r2/kr/results/r2_kr_reversal.csv | 7 | traced |
| GV-508 | LARGE VW deciles: 1-month reversal losers minus winners, %/month (NW t) | KRX | 1996-04..2026-09 | net35 | -1.06 (-1.6) | r2/kr/results/r2_kr_reversal.csv | 82 | traced |
| GV-517 | C3 KRW-BTC OOS Sharpe [90% CI] vs buy-and-hold; p; Sharpe at 2x; turnover | crypto | QUANTGEN study 2026-09-27 | net 10 bp/side (2x 20 bp) | 1.22 [0.62, 1.77] vs 0.79; p 0.04; 1.17 at 2x; 13.7x/yr | research_notes/QUANTGEN technical and fundamental signals/00_QUANTGEN_context.md | 28 | traced |

### 11.18 Chair verification references

| GV | Quantity | Market | Period | Gross/net | Value | Source file | Line | Status |
|---|---|---|---|---|---|---|---|---|
| GV-497 | KR Fama-MacBeth beta slope and low/high-beta alphas (chair prof_v09) | KRX | see value | see value | KR Fama-MacBeth slope +1.1%/yr (t 0.19) vs market 10.9%/yr; low-beta quintile raw alpha -1.0%/yr (t -0.26) EW, -2.4% (t -0.71) VW; high-beta EW alpha -7.0% (t -1.72); US lab +0.46%/yr (t 0.17) | r2/verification/prof_verification_log.csv | 3 | traced |
| GV-498 | chair lottery composite (prof_v02): %/month net 35 bp | KRX | see value | see value | +0.236 (t 7.65) from 2001; +0.248 (t 8.02) from 1996; 2x +0.21; 87-88% years +; worst 2015 -1.45 | r2/verification/prof_verification_log.csv | 92 | traced |
| GV-499 | KR-ISS long-only net information ratio (prof_v03) | KRX | see value | see value | gross 2.8-3.1%/yr IR 0.75-0.82; net35 1.8-2.1%/yr IR 0.48-0.54, 65-68% years +; net70 IR 0.21-0.27 | r2/verification/prof_verification_log.csv | 48 | traced |
| GV-500 | R2 lottery exclusion EW book | KRX | see value | see value | +3.08%/yr net35 (IR 1.53, bootstrap p 0.0005), +2.76% at 70 bp, 90% of years positive, positive in all three sub-periods; indicative gate 7/8 (only pooled DSR over 176 trials 0.94 misses) -> REVISE; capped VW (B2) +0.85%/yr REVISE; top 200 (B3) +0.49%/yr REJECT | r2/verification/prof_verification_log.csv | 112 | traced |
| GV-501 | R2 issuance exclusion books | KRX | see value | see value | B1 (EW) +2.34%/yr net35 (IR 0.65, p 0.0005, 81% years +), 2016-26 +1.34% (IR 1.43); B4 +4.23%; B2 (capped VW) +0.69% (IR 0.15) | r2/verification/prof_verification_log.csv | 113 | traced |
| GV-502 | 1-month reversal VW ex-microcap | KRX | see value | see value | VW deciles ALL +0.57%/m gross (t 0.9), -0.68 net; VW quintiles +0.08 gross; EW deciles +1.43 (t 3.1), +0.23 net; top 200 VW about 0 gross and negative net after 2005 | r2/verification/prof_verification_log.csv | 116 | traced |

### 11.19 Values that could not be traced

| GV | Item | Quantity | Why not traced |
|---|---|---|---|
| GV-518 | FS-1 floored trend x VT20 | plateau (PC-6) and start-date sweep of the floored product | not evaluated by R2 IDX (only the unbounded product was swept) |
| GV-519 | FS-4 ridge / Fama-MacBeth challenger | any performance number | no lab test exists |
| GV-520 | CRY-1 C3 controls | vol-scaled long-only control, 2024-01-10 split, ETH replication | no local crypto data (E3-C25 UNVERIFIABLE) |
| GV-521 | RISK-2 ladder (owner decision) | sigma-scaled ladder on KOSPI VT20: Sharpe 0.40, MDD -37.4%, 1 halt | E5 figure, not re-run by the chair (R2_EXEC EX-T-11) |
| GV-522 | RISK-2 ladder (owner decision) | SPY cumulative vs non-cumulative steps (0.41 -> 0.02) | E5 figure, not re-run (R2_EXEC EC-T-10) |
| GV-523 | SCR-1/SCR-2 step 9 | expected live diff = 0.6 x OOS (+1.85%/yr for B1/F4) | lab printed 0.4 x (+1.23%); 0.6 x 3.08% = 1.85% is arithmetic, not a lab output |

Shown above: 463 of 523. Items without a numeric golden value: ML-1 (structural test: signs fixed in the header, equal weights, z-scores cross-sectional), DATA-4 (structural: rcept_dt + 1 availability, first-filed values), DATA-6 (logging), FS-4 and FS-5 (no lab test; their settling tests define the first golden values).

## 12. Corrected anchors (numbers that must not propagate)

| ID | Number in circulation (where) | Correct value or reading (market, period, gross/net) | Source |
|---|---|---|---|
| CA-01 | Korean 1-month reversal "-2.95%/month (t -3.77)" (context brief; macro anchors; E7-C17) | A Fama-MacBeth slope on r(-1), Jan-1999..Feb-2021: about -0.30% next month per +10% last month, not a spread. Implementable spreads: EW quintiles 0.52%/month gross (2001-26), 0.08% (2020-26), negative net; KRX EW deciles 1999-2021 +1.41%/month gross, +0.20% net 35 (R1); VW ex-microcap deciles 1996-04..2026-09 +0.57%/month gross (t 0.9), -0.68% net 35 | Sim and Kim (2021) JDQS 29(3); prof_v01; r2_kr_reversal.csv lines 17/22; R2_PROF PR-T-02, R2_EXEC ER-T-07 |
| CA-02 | Korean momentum "-6.13%/month in high-turnover stocks" (context brief; KJFS) | Not reproduced: +0.78 (t 2.57) / +1.22 (t 3.26) (prof chair), +0.58 / +1.42 (P6), +1.44 (t 3.41, R1 high-turnover tercile), +1.43%/month (t 3.26) all caps and +1.66% (t 4.50) ex-bottom-20% (KRX 2000-07..2019-06, gross, adjusted returns); the sign appears only with unadjusted closes (-11.37%/month, t -5.42). The long-only high-turnover winner leg does lag: -11.57%/yr vs EW, net 35, 1996-2026 (t -4.18) | e-kjfs.org; prof_v02; r2_kr_mom_claims_long.csv lines 15/7/183/175/51/43; r2_kr_mom_grid_long.csv line 2856 |
| CA-03 | KR-ISS long-only net information ratio 0.84 (P3) | 0.48-0.54 full sample net 35 (1996-06..2026-09); 0.35-0.38 in 2017-26; about 0 at 70 bp in 2017-26 | prof_v03 (prof_verification_log.csv line 48) |
| CA-04 | Ilmanen et al. per-factor out-of-sample haircuts value -49%, momentum -23%, multifactor -18% (macro R-15, section 7 prior_haircuts, section 13 N-60) | Only an average 30% out-of-sample drop is verifiable; use planning haircuts 0.5 / 0.3 / 0.75 and measured local decay (GOV-8) | AQR article page; V107 UNVERIFIABLE; R2_PROF PR-T-13 |
| CA-05 | Average anomaly "8 bp/month net" | 4 bp/month (204 anomalies) | Chen and Velikov, JFQA 2023 abstract; R2_PROF PR-T-12 |
| CA-06 | Step-8 false pass "36-38% at 8-10 years" (P4) | 23.8% (KOSPI bootstrap), 29.5% (iid), 31.2% (sign-flip) at true Sharpe 0 over 10 years; the joint false-pass rate of steps 2+3+5+8 is 0.5% | r2_idx_gate_sim.csv lines 524/6244/3384/539 |
| CA-07 | "18 OOS years for Sharpe 0.4" (P1); "IR 0.3 needs 18 years" (E4) | About the 50%-power horizon: Sharpe 0.4 reaches 50% power at step 2 after 15.8 years and 80% after 40.3; step 5 needs about 50 years for 80% | r2_idx_gate_power_years.csv line 363; R2_EXEC A22 |
| CA-08 | Jeon-Byun "max drawdown -23.7% vs -74.1%" | Worst monthly returns (-23.66% vs -74.06%), not drawdowns | Marquette e-Publications; R2_PROF PR-T-10 |
| CA-09 | P4 "SE 0.188" (Sharpe 1.5, 60 months) | Annualised SE about 0.47 | Lo (2002) formula; R2_PROF PR-T-15 |
| CA-10 | Volume-filtered weekly reversal 0.44%/week (P2), 0.03%/week (P6) | Design-dependent -0.05 to +0.31%/week gross (2001-26); 0.14-0.26%/week in the top 500 (1996-2026); always negative net (-0.92 to -1.33%/week net 35) | prof_v04_weekly_reversal.csv; R2_PROF PR-T-03 |
| CA-11 | Corwin-Schultz KRX spreads 39-79 bp (P6) | 22-57 bp (cap buckets) or 99-117 bp (negatives zeroed first), Jan-2024..Sep-2026; not a calibration source | prof_v07, prof_v07b (V096 MISMATCH) |
| CA-12 | "Samsung + SK hynix = 55.5% of KOSPI" (undated; macro R-07 text) and "22% at end-2023" (KEIA) | Always give date and denominator. CR-07 definition: 53.71% (2026-09-29), 59.69% peak (2026-06-25), 29.29% (2023-12-28). Alternatives on 2026-09-29: 50.82% (common lines / all lines), 52.59% (common / common), 53.96% (incl. preferred / common + preferred). End-2023: 26.88% / 27.79%, not 22%. MSCI Korea (free float, Aug-2026) 60.8% | r3_pair_share.csv lines 2/7/9; R2_EXEC A4-A5; P1-C27 |
| CA-13 | Korea 52-week high "+0.34%/month net (t 2.31)" | +0.33%/month (t 2.14) from 2001-03; +0.13%/month (t 0.81) from 1996-03 (EW top quintile minus EW universe, net 35); state the start date | KR lab daily series; R2_PROF PX-T-03 |
| CA-14 | Korea 12-7 momentum "net-of-35-bp Sharpe 0.54" | 0.60 (deciles, from 2001), 0.19-0.20 (from 1996; EW quintiles 0.20), -0.01 in 2016-26; negative at 70 bp after 2010 | prof_v02; r2_kr_mom_grid_long.csv lines 6144/6194 |
| CA-15 | CAPE 1-year out-of-sample R2 "-2.4% (1950-) / -11.1% (1990-)" | -4.8% / -16.5% (prof chair), -4% / -18% (US lab); all negative | prof_v06; us/results/us_A4_valuation.csv |
| CA-16 | P6 value-weighted low-risk tilt "-20.3 points in 2025" | Single-signal VW top quintiles lost 35-40 points in 2025 | KR lab daily series; R2_PROF section 3 |
| CA-17 | "US 12-1 momentum Sharpe 0.02 since 2008" (context brief) | -0.16 for 2008..2017-03 (French WML; local file ends 2017-03); not verifiable to 2026 here | us/results/us_C_factors.csv |
| CA-18 | "ChatGPT strategy unprofitable at 20 bp" | 20 bp round trip (10 bp per side) | Lopez-Lira and Tang, arXiv v6 |
| CA-19 | "Trend following 2010-18: 0.4%/yr" | Excess over T-bills (AQR 2019, Exhibit 1); total return 1.6%/yr. Do not swap the two | AQR 2019 |
| CA-20 | Dynamic momentum "roughly quadruples" Sharpe (E1-C16) | "Approximately doubles": JFE Table 7 0.682 -> 1.041 -> 1.194; static WML 0.71 | NBER w20439; R2_EXEC ER-T-01, A1 |
| CA-21 | Step 9 as "x 0.4" (two panelists; R2 KR gate column g9 prints 0.4 x diff, e.g. B1/F4 +1.23%/yr) | Expected live Sharpe = 0.6 x OOS ("take 40% off"); E1 F1 prior 0.13 before the gate; E4 composite live IR 0.18-0.30; B1/F4 at 0.6 x 3.08% = +1.85%/yr (arithmetic) | macro section 8.1; r2_kr_excl_gate.csv line 2; R2_EXEC A2 |
| CA-22 | KOSPI 24-month return "+235%" on 2026-06-22 | +227% (daily) / +222% (month-end) | exec chair c02; R2_EXEC A10 |
| CA-23 | KOSPI on 2025-03-31 "-2.93%" | -3.00% | exec_verification_log.csv row 78 |
| CA-24 | MTUM IT weight "54.3%" (2026-06-30 factsheet) | 53.22%; 54.3% is the 2026-09-29 page | iShares; R2_EXEC A12 |
| CA-25 | Korean top-500 12-1 WML Sharpe 0.43 EW (E5) | EW 0.26-0.30 gross / 0.04-0.07 net 35 (deciles, 2000-26); VW 0.44-0.48 / 0.28-0.30; 2016-26 EW net -0.13, VW 0.30 (0.02 with a 5% cap); July 2026 -30.0% EW / -29.8% VW | exec chair c05; R2 KR; R2_EXEC A7, ER-T-06 |
| CA-26 | Bounding trend to [0.5, 1] "keeps about half the protection" (E3-C23) | PC-1 vs own S rises: +11.3 pp (unbounded x VT20) -> +13.0 (0.5+0.5x) / +15.4 (clip); absolute max DD -27.7% -> -36.2% / -29.4% (KOSPI 1996-09..2026-09, net 3 bp) | r2_idx_overlay_vs_sleeve.csv lines 11-13; R2_EXEC ER-T-02, A8 |
| CA-27 | The Daniel-Moskowitz gate protects Korean momentum crashes | 3 onsets since 2000 (2001-01-04, 2008-10-31, 2020-03-20), on 4.1% of days; 9 onsets 1996-2026 (9.8% of days), mostly 1997-99; off on 2026-06-22 | r2_kr_dm_gate_onsets.csv lines 2-10; R2_EXEC A20 |
| CA-28 | Insider buys "82 bp/month" as a long-only 126-day overlay | Long-short (buys minus sells), one-month hold, five-factor alpha: 82 bp VW (t 2.15) / 180 bp EW (t 6.07), 1986-2007 | NBER w16454; R2_EXEC A6, ER-T-04 |
| CA-29 | GS high-beta momentum basket "-37% in July 2026" | Unverified; only "worst month since November 2000" is verifiable | Yahoo/Bloomberg; R2_EXEC ER-T-09, A15 |
| CA-30 | KOSPI crash 2026-06-22..07-30 "-38.0%" | -38.61% (rebuilt index and official levels) | r2_idx_windows.csv line 3; R2_EXEC A16 |
| CA-31 | Korean low-turnover momentum long-only excess "+2.9%" | +2.9% (E7 universe, 2015-24), -0.1% (ALL, 2015-24), +9.69%/yr (t 2.77; ALL, 1996-2026, net 35); high-turnover winners -11.57%/yr (t -4.18) | r2_kr_mom_grid_long.csv lines 1120/2856; R2_EXEC A13 |
| CA-32 | "Korean low volatility is a crash hedge" (E7-C20; professors' protective 2) | Beta 0.63 (EW) / 0.74 (VW); against S_beta max DD worse by 7.1-22.4 pp and tail ratio 0.97-0.99 (KRX 1996-2026, net 35) | c12_lowvol_samebeta.csv lines 2/6/10; R2_EXEC A14 |
| CA-33 | KOSPI trend protection read as a full-sample property | Concentrated in 1997-2001: the multi-speed sleeve is REJECT from 2011 and 2016 starts (PC-1 -3.5 / -2.9 pp); VT20 alone passes from every start 1996-2006 (PC-1 +4.4 to +11.6 pp) | r2_idx_start_date_sensitivity.csv; R2_EXEC A21 |
| CA-34 | Nominal sizes of gate steps 2 and 5 with 10-session blocks | Step 2 false pass 6.9-8.0% (nominal 5%); step 5 12.8-13.7% (nominal 10%), KOSPI-like returns | r2_idx_gate_sim.csv lines 522/616/1396; R2_EXEC A22 |
| CA-35 | Vol-scaled sizing adds "+0.1 to +0.3 Sharpe on nearly every strategy" (prior design) | Robust only for momentum: Korean reversal EW net -0.29 -> -0.59 when scaled; KOSPI VT20 long-only 0.38 vs S 0.40 | R2_EXEC ER-T-10; R2_PROF PR-T-16 |
| CA-36 | AQMIX as evidence of a 1.2-Sharpe trend book | 10-year return 5.44% vs T-bills 2.42%, volatility 9.96%: Sharpe about 0.30 | R2_EXEC A18 (E1-C05 check) |
| CA-37 | KRX limit-up event return "-308 bp" (chair first pass) | The chair's own benchmark error; E7's -394 / -579 bp (t+5 / t+20) stand | exec_verification_log.csv rows 82-86; R2_EXEC A19 |
| CA-38 | US single-index trend weight 3 (prior; macro R-14) | At 50 bp all multi-speed cells REJECT (PC-1 -10.7 pp); at 5 bp INSUFFICIENT DATA (PC-1 +14.7 pp, 53-56% of the benefit from the GFC) | r2_idx_protective_scorecard.csv lines 10/17; R2_EXEC A9 |

## 13. Cross-spec amendments for the macro spec owner

Types: Supersession (this programme owns signal-family weights; owner confirms), Correction (a number or wording in the spec is wrong), Proposal (answers an open point), Tightening (gate change allowed by CR-08), Clarification, Information, Conflict (owner decides).

| ID | Macro item | Proposed change and evidence | Basis | Type |
|---|---|---|---|---|
| XS-01 | Section 2.2 KEEP Korea flow 3; R-15 flow prior | Korea investor flow 3 -> 1: log final investor-type flows with timestamps now (DATA-6); no direction rule; t-1 history required before an open-leg test. Foreigners sold KRW148.3tn net in H1-2026 while KOSPI rose about 101% (R2_EXEC EC-T-23) | CR-03; TF-39, TF-40 | Supersession |
| XS-02 | R-15 Korea ST reversal 3 and section 2.2 KEEP 3 ("Korea keeps 1-5-day reversal") | 3 -> 0 for daily/weekly reversal; monthly reversal only as a conditioning guard of weight 1 (FS-5). The required net-of-cost test fails: weekly L/S net-35 Sharpe -1.78 (KRX ALL EW 1996-2026; kr_key_numbers.csv line 30), break-even 12.5 bp per side; 1-month VW ex-microcap deciles -0.68%/month net 35 (1996-04..2026-09; r2_kr_reversal.csv line 22). Delete the 1-5-day sentence | CR-03; TF-41, TF-42 | Supersession |
| XS-03 | Section 2.2 volume-spike reversal "KEEP as signal spec; UNTESTED" | DROP: volume-filtered weekly reversal -0.05 to +0.31%/week gross (2001-26), -0.92 to -1.33%/week net 35 (prof_v04); volume-spike buying -43 / -93 bp at t+5 / t+20 (KRX 2015-06..2026-09, gross; exec row 83) | TF-41, TF-61; R2_PROF PR-T-03 | Proposal |
| XS-04 | R-05 (reversal and quality held at 1.0x; reversal card must clear 35 bp and stay positive at 70 bp) | Record that the reversal family fails its own test (XS-02); the 1.0x convention stays for any future reversal sleeve on a venue of 5 bp or less (BACKLOG DC-E2-09); vol scaling hurts reversal (KR STR EW net -0.29 -> -0.59) | TF-41, TF-22 | Information |
| XS-05 | R-15 prior calibration; section 7 YAML prior_haircuts; section 13 N-60 ("use these values and no others") | Replace the per-factor Ilmanen haircuts (unverifiable; only a 30% average drop is published) with one haircut per stage: planning 0.5 in sample, 0.3 post-publication, 0.75 drift-like, replaced by measured local decay where 20+ years exist (GOV-8); withdraw N-60 | R2_PROF PR-T-13; TF-56, TF-57; CA-04 | Correction |
| XS-06 | R-07 evidence text "55.5% of KOSPI (22% at end-2023)" | Dated, denominated values: 53.71% on 2026-09-29 and 29.29% on 2023-12-28 under CR-07; end-2023 alternatives 26.88% / 27.79%, not 22% | CA-12; r3_pair_share.csv | Correction |
| XS-07 | R-07 pair-share denominator (undefined) | CR-07 definition (005930 + 005935 + 000660 over all KOSPI lines in the KRX daily file): 53.71% on 2026-09-29; first above 0.45 on 2026-05-06 (0.4702); 99 of 181 sessions above 0.45 in 2026; peak 59.69% on 2026-06-25; alternatives 50.82% / 52.59% / 53.96% on 2026-09-29 | CR-07; TF-26; section 11.1 | Proposal |
| XS-08 | R-07 ladder open points (cumulative steps; re-arm reference) | Steps non-cumulative; total book NAV only (never per sleeve); re-arm at 0.5 with the reference peak reset (never the all-time high-water mark); thresholds unchanged. Evidence: KOSPI CW 2000-26 net 35, reset with 0.5 re-arm: Sharpe 0.42 -> 0.40, max DD -55.8% -> -41.3%, 0.69 halts/yr; all-time-peak reference 22.8 halts/yr and Sharpe -1.65; per-sleeve ladder on vol-scaled VW WML 0.38 -> 0.16 (exec rows 58-61) | CR-07; TF-27 | Proposal |
| XS-09 | R-14 TS trend sleeve (CARD-O vs EW basket; 12-1 sign monthly; US weight 3) | Add a CARD-P cell (single-index trend judged on PC-1..PC-7 vs S; never CARD-O) and a speed cell (KOSPI 3 bp: 12-month sign PC-1 +4.7 pp, INSUFFICIENT DATA, vs multi-speed +8.9 pp, PASS; r2_idx_protective_scorecard.csv lines 4/3). US single-index trend: protective 0 at 50 bp (REJECT, PC-1 -10.7 pp, line 10), 1 at futures cost (BACKLOG) | CR-02; TF-30, TF-34 | Proposal |
| XS-10 | R-03 scope | State that R-03 applies to every momentum sleeve in every market, KRX stock sleeves included, as a risk control and not a return claim; on KRX it lowered 2016-26 Sharpe (EW L/S -0.20 -> -0.24, VW 0.32 -> 0.23; r2_kr_crash_controls.csv lines 70/184/526/640) | CR-05; TF-22 | Clarification |
| XS-11 | Section 8.5 blocks (macro cards only) vs section 8.1 step 2 (10-session blocks) | max(10, Politis-White on d and d^2) for steps 2 and 5 on every card; 10-session blocks gave false passes of 8.0% at nominal 5% (step 2, 10 years) and 13.7% at nominal 10% (step 5) on KOSPI-like returns (r2_idx_gate_sim.csv lines 522/616) | CR-08; TF-53 | Tightening |
| XS-12 | Section 8.7 CARD-P comparator ("applies only to rules whose output never exceeds 1.0") | Add S_beta = beta_hat x market + (1 - beta_hat) x cash, beta_hat pre-registered, as the CARD-P comparator for stock-level sleeves (estimation window: OQ-03) | CR-01; TF-59 | Proposal |
| XS-13 | Section 8.1 step-9 wording; context brief "60% live haircut" | One wording: expected live Sharpe = 0.6 x OOS ("take 40% off"); fix harness prints that use 0.4 x (R2 KR g9 column: B1/F4 +1.23%/yr printed, +1.85%/yr intended) | CR-08; TF-55; CA-21 | Correction |
| XS-14 | R-08 market stress gauges | Do not count R-08 as factor-crash protection: VIX was 12.9-25.8 at 19 factor-crash onsets (exec rows 8, 69) | TF-25 | Information |
| XS-15 | R-04 Daniel-Moskowitz gate scope | Specification book only; no extension to earnings-momentum or revision sleeves; on KOSPI 9 onsets in 1996-2026 and off on 2026-06-22 (r2_kr_dm_gate_onsets.csv) | CR-05; TF-23 | Information |
| XS-16 | R-15 US XS momentum ("2 if vol-scaled + D-M, else 1") | This programme's final weight is 1 (professors 1, executives 2, rule W3; no US stock sleeve at 50 bp; French WML Sharpe -0.16 in 2008..2017-03) | TF-29 | Conflict (OQ-06) |
| XS-17 | R-15 crypto ST reversal 2 | 2 -> 0 (short-horizon crypto evidence is momentum) | CR-10; TF-68 | Supersession |
| XS-18 | R-15 Korea 12-7 / residual momentum 1 (UNVERIFIED) | Replace with the constrained momentum card FS-2 (weight 1, FORWARD-SIM: Q5 12-1 or 12-7 excluding lottery/highest-turnover names, R-03, 5% cap, long-only). 12-7 L/S EW net-35 Sharpe 0.20 (1996-2026) and -0.01 (2016-26) (r2_kr_mom_grid_long.csv lines 6144/6194); residual momentum untested | CR-05; TF-21 | Supersession |
| XS-19 | Section 10 DO-NOT-BUILD (items 1-26) | Add DNB-TF-01..17 (section 6). Overlaps: DNB-TF-06 repeats item 14 (flow direction); DNB-TF-11 matches item 26 (value timing presented as compliant); DNB-TF-14/15 extend item 11. Clarify item 13: the aggregate issuance-timing ban does not cover the firm-level dilution exclusion screen SCR-2 | CR-06, CR-11, CR-12 | Proposal |
| XS-20 | R-06 Korea card evidence (indicative INSUFFICIENT DATA on the 2016-26 card) | R2: PASS on 1996-09..2026-09 (PC-1 +6.5 pp, tail 0.70) and from every start 1996-2006; INSUFFICIENT from 2011/2016; the spec's 2016-26 golden values reproduce (r2_idx_golden_values.csv). Owner declares the judged history (OQ-07) | TF-31 | Information |
| XS-21 | R-15 0-3 normalisation into base_weight (open point) | base_weight = w / 3 (weight 3 = 1.0x; never above 1.0); one-sided (*) cells cannot feed any book until a card passes | Weight rules W1-W5 | Proposal |
| XS-22 | R-07 caps: 0.05 single name vs 0.35 pair (open point) | By book type: 0.05 single name in selection sleeves (VW legs capped at 5% of the leg); 0.35 pair cap on look-through for market and ETF books when the pair share exceeds 0.45; semis <= 0.50. Pair cap on KOSPI CW cost -15.0 pp in the H1-2026 melt-up, saved +4.6 pp in the crash, -2.2 pp 2026 YTD (exec chair c07) | CR-07; TF-26 | Proposal |

## 14. Open questions for the owner

- **OQ-01** Ladder threshold units (CR-07): keep fixed -8 / -12 / -15%, move to book-volatility units (-1.0 / -1.5 / -1.9 sigma), or declare a book-vol ceiling of 8% at which the two coincide? Evidence: Brownian check at Sharpe 0.5, P(-15% within 10 years) = 0.97 at 12% book vol and 0.66 at 8% (exec row 62); E5's sigma ladder on KOSPI VT20 (Sharpe 0.40, max DD -37.4%, 1 halt) was not re-run. Suggested: FORWARD-SIM both conventions.
- **OQ-02** Confirm the CR-07 pair-share denominator (preferred line in the numerator, all KOSPI lines in the denominator). The cap first binds on 2026-05-06 under CR-07 and on 2026-05-07 under the common-over-all-lines definition.
- **OQ-03** S_beta beta_hat: which window? Proposal: OLS beta of daily returns on the declared market over the prior 252 sessions, frozen in the card header at each formation; a full-period beta only as a descriptive check (the c12 check used full-period monthly OLS betas of 0.631-0.742; exec_chair_checks/c12_lowvol_samebeta.py).
- **OQ-04** Step 8 stays (CR-08). Add the professors' "positive in at least 2 of 3 sub-periods" and a short-sale-regime split as extra checks (both tighten)?
- **OQ-05** The professors' Jensen-alpha step-5 variant was not adopted because for beta < 1 cards it can loosen step 5. Print it as a report line only?
- **OQ-06** US stock momentum prior: 1 (this programme) or macro R-15's "2 if vol-scaled + D-M"?
- **OQ-07** R-06 Korea card: judge it on the rebuilt KOSPI from 1996-09 (PASS) or from 2016-01 (INSUFFICIENT DATA)?
- **OQ-08** Build order of the data stores: OpenDART PIT (unblocks KR-VQ, drift, value and quality), FMP/EDGAR PIT (US-VQ, insiders, IPO screen), KIS quote snapshots (cost buckets, impact), t-1 investor flows (open-leg test).
- **OQ-09** Crypto C3 prior weight 2 (macro R-15, executives) or 3 (prior design, professors)? The card's own PASS governs the card; only base_weight changes.
- **OQ-10** Tiered t-hurdles (professors only): Tier A t >= 2.0, new signals t >= 3.0 plus SPA, > 100 configurations or TradingView-sourced t >= 3.4-3.8. Adopt as a tightening?
- **OQ-11** Statistical review triggers (executives only): a forward drawdown beyond the 95th simulated percentile, or a 12-month Sharpe below its 90% CI, triggers a review and never an automatic liquidation. Adopt as a governance option?
- **OQ-12** CR-06 adopted only "never enter at a locked limit-up close". Add the executives' five-session no-new-long window after locked limit-ups or volume spikes once BL-TF-02 tests it?
- **OQ-13** KOSDAQ trend: keep macro R-14's 0 until a KOSDAQ index rebuild and test exist (executives proposed protective 1, untested)?
- **OQ-14** SCR-1 primary definition: the F4 10% cut (best IR 1.53, smallest exclusion) or F1 highest-turnover quintile (larger mean, +4.28%/yr net 35 on B1, IR 1.15)? Run SCR-1 and SCR-2 as two cards or one combined screen (flag overlap Jaccard 0.13)?
- **OQ-15** Threshold for the attribution block's "factor tilt" label. Proposal: Newey-West alpha t below 2.0 after attribution.

## 15. Gaps

- No point-in-time fundamentals locally (OpenDART, FMP/EDGAR): KR-VQ, US-VQ, Korean drift, value and quality weights, insiders and the IPO screen are untested.
- No KIS quote history: half-spreads, impact and capacity are unmeasured; the flat 35 / 70 bp per side is used throughout.
- No t-1 investor-flow history; no local crypto, futures or US single-stock panels (C3 controls, CTREND-lite, diversified futures trend, US stock cards and US low-vol vs S_beta are untested).
- KRX lab returns are price returns without dividends and Sharpe ratios use rf = 0; low-vol, value and low-beta results are understated by roughly 1-2%/yr.
- No price-impact model in the R2 races; capacity is a rule (<= 1-2% of ADV20), not a measurement.
- All lab verdicts are in sample on 1996-2026; the contamination log treats the historical holdout as used for every family discussed, so FORWARD-SIM incubation from 2026-10-01 is the clean test.
- The floored trend x VT20 cell has no plateau (PC-6) or start-date sweep; only the unbounded product was swept.
- No local test of the L0 composite or the ridge challenger; 52-week-high-neutral and capped momentum crash tests were not run on KRX.
- The gate-size simulation covers steps 2, 3, 5 and 8; steps 1, 4 and 7 and CPCV are untested.
- E5's sigma-ladder and SPY cumulative-step results were not re-run (scripts not saved).
- The R2 KR gate harness prints step 9 as 0.4 x diff (spec: 0.6 x OOS).
- fp / fe count member claims only; 94 professor claims and part of the executive ledger remain unverified by the chairs; India was not reviewed by either panel and other markets are CONTEXT only.
- "US 12-1 momentum Sharpe 0.02 since 2008" cannot be checked past 2017-03 with the local French file.

## Appendix A. Node index (all 70 nodes; propositions are in sections 5-7)

| Node | Theme | Class | fp | fe | Professors | Executives | Data | Destination | Decision |
|---|---|---|---|---|---|---|---|---|---|
| TF-01 | A | CORE-LINK | 0 | 7 | Moderate | Strong | Supports | SPEC §TF-1 INV-1 | INVARIANT |
| TF-02 | A | CORE-LINK | 1 | 10 | Moderate | Strong | Supports | SPEC §TF-1 INV-2 | INVARIANT |
| TF-03 | A | CORE-LINK | 2 | 7 | Strong | Strong | Supports | SPEC §TF-2 DATA-1..3 | INVARIANT |
| TF-04 | A | CORE-LINK | 3 | 6 | Strong | Strong | Supports | SPEC §TF-2 DATA-4 | BUILD NOW (data layer) |
| TF-05 | A | CORE-LINK | 8 | 17 | Strong | Strong | Supports | SPEC §TF-2 DATA-5 (flags); event cards BL-TF-14 | BUILD NOW (flags); BACKLOG (event cards) |
| TF-06 | A | CORE-LINK | 10 | 8 | Strong | Strong | Supports | SPEC §TF-7 GOV-1 | GOVERNANCE |
| TF-07 | A | CORE-LINK | 10 | 12 | Moderate | Strong | Supports | SPEC §TF-7 GOV-7 | GOVERNANCE |
| TF-08 | A | CORE-LINK | 10 | 11 | Strong | Strong | Supports | SPEC §TF-1 INV-4 | INVARIANT |
| TF-09 | A | CONTESTED | 3 | 7 | Split | Moderate | Untested | BL-TF-01 | BACKLOG |
| TF-10 | A | CORE-LINK | 1 | 8 | Moderate | Strong | Supports | SPEC §TF-1 INV-5 (review triggers: GOV option, exec-only) | INVARIANT |
| TF-11 | A | CORE-LINK | 4 | 8 | Strong | Strong | Supports | SPEC §TF-7 GOV-9 | GOVERNANCE (reporting) |
| TF-12 | B | CORE-LINK | 7 | 2 | Strong | Strong | Supports | SPEC §TF-3 SCR-1 | BUILD NOW (screen card) |
| TF-13 | B | CORE-LINK | 2 | 4 | Moderate | Strong | Supports | SPEC §TF-3 SCR-2 | BUILD NOW (screen card) |
| TF-14 | B | CORE-PROHIBITION | 0 | 4 | Silent | Split | Refutes | DNB-TF-01 (monthly screen); INV-2 (entry-day exclusion) | DROP as screen; INVARIANT at entry |
| TF-15 | B | CORE-LINK | 1 | 3 | Moderate | Strong | Supports | SPEC §TF-3 SCR-3 (construction rule inherited by MOM sleeves) | BUILD NOW (construction rule) |
| TF-16 | B | CONTESTED | 4 | 3 | Moderate | Split | Mixed | FS-3 (KR descriptive sleeve with S_beta); BL-TF-03 (US DC9); screen input to SCR-1 | FORWARD-SIM descriptive (KR); BACKLOG (US) |
| TF-17 | B | CORE-PROHIBITION | 3 | 3 | Refuted | Refuted | Refutes | DNB-TF-02 | DROP |
| TF-18 | B | CORE-PROHIBITION | 2 | 1 | Refuted | Refuted | Refutes | DNB-TF-03 (size stays a risk control and attribution factor) | DROP |
| TF-19 | C | CORE-PROHIBITION | 8 | 1 | Refuted | Refuted | Refutes | Corrected anchors CA-01, CA-02; cross-spec XS-02 | DROP (anchors) |
| TF-20 | C | CORE-PROHIBITION | 3 | 5 | Refuted | Refuted | Refutes | DNB-TF-04 | DROP |
| TF-21 | C | CONTESTED | 3 | 3 | Split | Moderate | Mixed | FS-2 | FORWARD-SIM (weight 1) |
| TF-22 | C | CORE-LINK | 4 | 9 | Strong | Strong | Supports | SPEC §TF-4 MOM-1; cross-spec XS-10 (R-03 scope) | BUILD NOW (risk control) |
| TF-23 | C | CONTESTED | 2 | 6 | Moderate | Split | Refutes | R-04 spec book only; BL-TF-04 (52wH-neutral) | SPEC BOOK ONLY (D-M); BACKLOG (52wH-neutral) |
| TF-24 | C | CONTESTED | 4 | 2 | Split | Refuted | Mixed | BL-TF-05 (feature weight 1; one Tier A test) | BACKLOG |
| TF-25 | C | ONE-SIDED | 0 | 13 | Silent | Split | Refutes | BL-TF-06 (multiplier test); CONTEXT display; cross-spec XS-14 (R-08) | BACKLOG / CONTEXT |
| TF-26 | C | CORE-LINK | 1 | 11 | Moderate | Strong | Supports | SPEC §TF-4 RISK-1; cross-spec XS-06, XS-07, XS-22 | INVARIANT (owner to confirm cap scope and denominator) |
| TF-27 | C | ONE-SIDED | 0 | 5 | Silent | Strong | Supports | Cross-spec XS-08 (proposal to the owner) | OWNER DECISION (proposal) |
| TF-28 | C | ONE-SIDED | 0 | 5 | Silent | Split | Mixed | Owner decision OQ-01; FORWARD-SIM both conventions | OWNER DECISION |
| TF-29 | C | CONTESTED | 4 | 3 | Refuted | Moderate | Mixed | BL-TF-07; weight table (final 1); cross-spec XS-16 | BACKLOG |
| TF-30 | D | CORE-LINK | 4 | 10 | Strong | Strong | Supports | SPEC §TF-5 IDX-0 (class rule); cross-spec XS-09 (R-14) | GOVERNANCE (class rule) |
| TF-31 | D | CORE-LINK | 1 | 2 | Strong | Strong | Supports | SPEC §TF-5 IDX-1 (= macro R-06, unchanged) | BUILD NOW (macro R-06; CARD-P) |
| TF-32 | D | CORE-LINK | 0 | 3 | Moderate | Strong | Supports | FS-1 | FORWARD-SIM |
| TF-33 | D | CONTESTED | 0 | 2 | Refuted | Split | Mixed | SPEC §TF-5 IDX-0 class rule (standalone sleeve may hold 0; overlay bounded); comparison cell in FS-1 | GOVERNANCE (resolved by CR-02) |
| TF-34 | D | CORE-PROHIBITION | 1 | 5 | Refuted | Refuted | Refutes | DNB-TF-05 (at 50 bp); BL-TF-08 (futures-cost instrument) | DROP at 50 bp; BACKLOG at futures cost |
| TF-35 | D | UNTESTED | 8 | 17 | Moderate | Moderate | Untested | BL-TF-09 | BACKLOG |
| TF-36 | E | UNTESTED | 4 | 5 | Moderate | Moderate | Untested | BL-TF-10 -> SPEC §TF-6 FUND-1 when the PIT store exists | BACKLOG (BUILD-candidate, weight 2) |
| TF-37 | E | CONTESTED | 5 | 4 | Split | Split | Untested | Weight table (1 each); BL-TF-10 | BACKLOG (weight 1) |
| TF-38 | E | CONTESTED | 4 | 3 | Split | Split | Refutes | BL-TF-11 (weight 1) | BACKLOG (weight 1) |
| TF-39 | E | CORE-PROHIBITION | 2 | 3 | Refuted | Refuted | Untested | DNB-TF-06; cross-spec XS-01 | DROP (direction rule) |
| TF-40 | E | CORE-LINK | 2 | 3 | Moderate | Strong | Untested | SPEC §TF-2 DATA-6 | BUILD NOW (logging) |
| TF-41 | E | CORE-PROHIBITION | 11 | 7 | Refuted | Refuted | Refutes | DNB-TF-07; cross-spec XS-02, XS-03, XS-04 | DROP |
| TF-42 | E | CORE-LINK | 5 | 7 | Moderate | Moderate | Mixed | FS-5 (screen variant, gated like SCR-1) | FORWARD-SIM (screen variant) |
| TF-43 | E | UNTESTED | 16 | 11 | Strong | Moderate | Untested | BL-TF-12 -> SPEC §TF-6 FUND-2 when FMP/EDGAR PIT data exist | BACKLOG (BUILD-candidate, weight 2) |
| TF-44 | E | CORE-PROHIBITION | 8 | 4 | Refuted | Refuted | Refutes | DNB-TF-08 (never count quality as a hedge); quality 2 as a composite leg | DROP (as hedge/weight 3) |
| TF-45 | E | CORE-PROHIBITION | 11 | 14 | Refuted | Refuted | Untested | DNB-TF-09 (event flags only) | DROP |
| TF-46 | E | ONE-SIDED | 0 | 8 | Silent | Split | Untested | BL-TF-13 | BACKLOG |
| TF-47 | E | CORE-PROHIBITION | 1 | 19 | Refuted | Refuted | Refutes | DNB-TF-10 | DROP (estimate revisions BACKLOG via the archive) |
| TF-48 | E | CORE-PROHIBITION | 4 | 5 | Refuted | Refuted | Refutes | DNB-TF-11; CONTEXT display only | CONTEXT |
| TF-49 | E | ONE-SIDED | 11 | 0 | Strong | Weak | Untested | Weight table (CONTEXT rows); BL-TF-15 (data paths) | CONTEXT |
| TF-50 | F | CORE-LINK | 12 | 0 | Strong | Silent | Supports | SPEC §TF-7 GOV-3 | GOVERNANCE (BUILD NOW) |
| TF-51 | F | CORE-LINK | 10 | 1 | Strong | Moderate | Supports | SPEC §TF-7 GOV-2 | GOVERNANCE (BUILD NOW) |
| TF-52 | F | ONE-SIDED | 7 | 0 | Strong | Silent | Untested | BL-TF-16 (owner: a tightening, allowed under CR-08) | BACKLOG |
| TF-53 | F | CORE-LINK | 2 | 0 | Strong | Moderate | Supports | SPEC §TF-7 GOV-4; cross-spec XS-11 | GOVERNANCE (BUILD NOW) |
| TF-54 | F | CORE-LINK | 4 | 5 | Strong | Strong | Supports | SPEC §TF-7 GOV-5 | GOVERNANCE |
| TF-55 | F | CONTESTED | 7 | 2 | Split | Split | Mixed | Steps 8 and 9 unchanged (CR-08); reporting lines GOV-6 | GOVERNANCE (unchanged + reporting) |
| TF-56 | F | CORE-LINK | 8 | 14 | Strong | Strong | Supports | SPEC §TF-7 GOV-8 (prior calibration) | GOVERNANCE |
| TF-57 | F | CORE-PROHIBITION | 2 | 0 | Refuted | Silent | Refutes | Corrected anchor CA-04; cross-spec XS-05 (R-15, §7 prior_haircuts, §13 N-60) | DROP (anchor) |
| TF-58 | F | CORE-LINK | 2 | 0 | Moderate | Moderate | Supports | SPEC §TF-7 GOV-10 | GOVERNANCE |
| TF-59 | F | CORE-LINK | 3 | 3 | Strong | Strong | Supports | SPEC §TF-7 GOV-11; cross-spec XS-12 (§8.7 S_beta) | GOVERNANCE (BUILD NOW) |
| TF-60 | F | CORE-PROHIBITION | 25 | 1 | Refuted | Refuted | Refutes | DNB-TF-12 (unless family gate + nine-step gate as a new card, via the porting protocol) | DO-NOT-BUILD |
| TF-61 | F | CORE-PROHIBITION | 8 | 23 | Refuted | Refuted | Refutes | DNB-TF-13 | DROP |
| TF-62 | F | ONE-SIDED | 7 | 0 | Strong | Weak | Supports | BL-TF-17 (build features as cards need them) | BACKLOG |
| TF-63 | G | CORE-LINK | 4 | 5 | Strong | Moderate | Untested | SPEC §TF-8 ML-1 (L0 with the first composite card); FS-4 (ridge) | BUILD with the first composite card (L0); FORWARD-SIM (L1) |
| TF-64 | G | UNTESTED | 13 | 1 | Weak | Weak | Untested | BL-TF-18 (shadow challengers, non-gating) | BACKLOG |
| TF-65 | G | CORE-PROHIBITION | 10 | 1 | Refuted | Refuted | Untested | DNB-TF-14 | DROP |
| TF-66 | G | CORE-PROHIBITION | 1 | 0 | Refuted | Silent | Untested | DNB-TF-15 | DROP |
| TF-67 | H | CORE-LINK | 6 | 2 | Strong | Moderate | Supports | SPEC §TF-9 CRY-1 (governance additions to C3) | KEEP + GOVERNANCE |
| TF-68 | H | CORE-PROHIBITION | 5 | 1 | Refuted | Refuted | Untested | DNB-TF-16 | DROP (weight 0) |
| TF-69 | H | ONE-SIDED | 2 | 0 | Moderate | Silent | Untested | BL-TF-19 | BACKLOG |
| TF-70 | H | CONTESTED | 6 | 0 | Refuted | Weak | Refutes | Weight 0; BL-TF-20 (one USD/KRW slow-trend test at FX cost) | BACKLOG (weight 0) |

Per-node claim IDs, chair items, propositions, URLs and settling tests are in `R3_TF_nodes.csv` (columns prof_claims, exec_claims, prof_chair_items, exec_chair_items, prof_props, exec_props, urls, settling_test).

## Appendix B. Edges

85 edges: qualifies 50, supports 18, refutes 15, conflicts 2. Refutes and conflicts edges:

| Edge | From | To | Type | Reason |
|---|---|---|---|---|
| E-001 | TF-03 | TF-19 | refutes | KRX-adjusted holding returns give +1.43%/month (t 3.3); the KJFS sign appears only with unadjusted closes (-11.37%/month). |
| E-006 | TF-07 | TF-41 | refutes | Weekly reversal break-even is 12.5 bp per side (22.2 bp VW), far below 2 x 35 bp: rejected before the gate. |
| E-007 | TF-07 | TF-14 | refutes | The F5 attention screen breaks even at 68 bp per side on the EW book, below 70 bp: rejected before the gate. |
| E-008 | TF-07 | TF-20 | refutes | Raw 12-1 L/S quintiles break even near 64 bp per side, below 70 bp. |
| E-009 | TF-07 | TF-61 | refutes | Intraday edges of 1-7 bp cannot pay a 25-46 bp KRX round trip. |
| E-010 | TF-07 | TF-34 | refutes | SPY trend turnover of 7.3-11.9 units/yr costs 3.7-6.0%/yr at 50 bp per side. |
| E-025 | TF-06 | TF-17 | refutes | Long-only low-vol top quintile excess is +1.1%/yr (t 0.5) EW and -1.8% VW. |
| E-026 | TF-06 | TF-20 | refutes | Long-only 12-1 top-quintile excess is -1.3%/yr (t -0.6). |
| E-032 | TF-14 | TF-12 | conflicts | Adding the attention screen to the composite (F8) lowers the IR from 1.53 to 0.67. |
| E-035 | TF-59 | TF-16 | refutes | Against the same-beta static book S_beta, Korean low-vol drawdowns are 7-22 pp worse and the tail ratio is 0.97-0.99. |
| E-036 | TF-50 | TF-17 | refutes | Low-vol CAPM alpha is +2.2% (t 0.8) EW, +0.7% (t 0.3) VW: a factor tilt, not alpha. |
| E-038 | TF-19 | TF-41 | refutes | The -2.95 anchor that justified reversal weight 3 is a regression slope, not a spread. |
| E-057 | TF-51 | TF-60 | refutes | Family tests reject classic rules: SPA p 0.880 over 303 KOSPI rules; 0.82-0.97 over 322 SPY rules. |
| E-067 | TF-56 | TF-47 | refutes | Live records undercut headline backtests: FFTY 3.52%/yr vs 13-14% for the S&P; AIEQ 4.18% vs 12.65%. |
| E-072 | TF-57 | TF-56 | conflicts | The per-factor Ilmanen haircuts in the macro spec are unverifiable; plan with 0.5 / 0.3 and measured local decay. |
| E-080 | TF-58 | TF-65 | refutes | In-window LLM backtests are contaminated; only point-in-time models are honest. |
| E-081 | TF-69 | TF-68 | refutes | Short-horizon crypto cross-sectional evidence is momentum (1-4 weeks), not reversal. |

All supports and qualifies edges are in `R3_TF_edges.csv`.

