# -*- coding: utf-8 -*-
"""Writes the R3 synthesis report R3_TF_neural_link.md from the R3 data products
(nodes, edges, weights, go/no-go register, golden values, pair share) plus the hand-written sections below.
Tables are generated from the CSVs so that the report and the machine-readable outputs cannot drift apart."""
import pandas as pd, json, re, os
R3='/home/claude/datalab/r3/'
OUT='/home/claude/research_notes/QUANTGEN technical and fundamental signals/R3_TF_neural_link.md'
rd=lambda p: pd.read_csv(p,keep_default_na=False)
N=rd(R3+'R3_TF_nodes.csv'); E=rd(R3+'R3_TF_edges.csv'); W=rd(R3+'results/r3_weights_final.csv')
WO=rd(R3+'results/r3_weights_other_markets.csv'); G=rd(R3+'results/r3_go_nogo.csv'); GV=rd(R3+'results/r3_golden_values.csv')
PS=rd(R3+'results/r3_pair_share.csv'); PSS=rd(R3+'results/r3_pair_share_summary.csv')
for c in ['fp','fe']: N[c]=N[c].astype(int)
def esc(x):
    return str(x).replace('|','\\|').replace('\n',' ').strip()
def table(rows, headers):
    out=['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']
    for r in rows: out.append('| '+' | '.join(esc(v) for v in r)+' |')
    return '\n'.join(out)
L=[]  # report lines
def P(s=''): L.append(s)
cnt=N.cls.value_counts().to_dict(); cntm=N.class_mechanical.value_counts().to_dict()
CLS=['CORE-LINK','CORE-PROHIBITION','CONTESTED','ONE-SIDED','UNTESTED']
ngv=len(GV); gvs=GV.status.value_counts().to_dict()
# ------------------------------------------------------------------ header
P('# R3 "Neural Link": technical and fundamental signals for QUANTGEN, one map of both panels and the data labs')
P()
P('Round 3 synthesis, 2026-10-03. Author: synthesis lead (round 3). The panels (professors P1-P7, executives E1-E7) are fictional composite personas; their claims are treated as claims, and every number below is either traced to a lab or verification file or marked as not traced.')
P()
P('Outputs of this round (all paths absolute):')
P('- This report: `/home/claude/research_notes/QUANTGEN technical and fundamental signals/R3_TF_neural_link.md`')
P('- Node and edge map: `/home/claude/datalab/r3/R3_TF_nodes.csv` (70 nodes), `/home/claude/datalab/r3/R3_TF_edges.csv` (85 edges)')
P('- Chart-ready JSON: `/home/claude/datalab/r3/charts/focus_map.json`, `weights_final.json`, `go_nogo.json`, `golden_values.json`')
P('- Supporting tables: `/home/claude/datalab/r3/results/` (r3_weights_final.csv, r3_weights_other_markets.csv, r3_go_nogo.csv, r3_golden_values.csv, r3_pair_share*.csv, r3_ledger_claims.json, r3_focus_by_theme.json); scripts in `/home/claude/datalab/r3/scripts/` (r3_00 .. r3_06); working notes `/home/claude/datalab/r3/R3_working_notes.md`.')
P()
P('Labelling convention. Every number carries market, period, gross/net and a source. "net 35" = net of 35 bp per side (KRX stock, tax included); "net 70" = the 2x stress; "net 3 bp" = KRX ETF line; "50 bp" = US via KIS. KRX lab Sharpe ratios are raw (risk-free rate 0) and lab returns are price returns without dividends. File references: "line n" is the line in the CSV file (header = line 1); "exec row n" is the `row` field of `r2/verification/exec_verification_log.csv` (file line n+1); "V0nn" is a `log_id` in `r2/verification/prof_verification_log.csv`; lab paths are relative to `/home/claude/datalab/`. "R2_PROF" and "R2_EXEC" are the two chair resolutions in the research-notes folder.')
P()
# ------------------------------------------------------------------ 1 summary
P('## 1. Summary')
P()
summary=[
"This round merged 414 panel claims (209 professors, 205 executives), all 120 claim-matrix propositions (60 per panel), all 115 chair items (61 professors, 54 executives) and the four data labs into one map of 70 single-proposition nodes (TF-01..TF-70) joined by 85 edges.",
f"Final classes: {cnt.get('CORE-LINK',0)} CORE-LINK, {cnt.get('CORE-PROHIBITION',0)} CORE-PROHIBITION, {cnt.get('CONTESTED',0)} CONTESTED, {cnt.get('ONE-SIDED',0)} ONE-SIDED and {cnt.get('UNTESTED',0)} UNTESTED; the mechanical class rule gave {cntm.get('CORE-LINK',0)}/{cntm.get('CORE-PROHIBITION',0)}/{cntm.get('CONTESTED',0)}/{cntm.get('ONE-SIDED',0)}/{cntm.get('UNTESTED',0)}, and three coordinator rulings moved a node (CR-06: attention-fade screen to prohibition; CR-08: attribution block to core; CR-11: macro x signal terms to prohibition).",
"What both panels support and the data confirm is mostly plumbing and risk discipline: decide at the close and fill at the KRX official close, locked-limit rules, point-in-time and corporate-action hygiene, a long-only primary statistic against a declared benchmark set, an itemised cost header with a break-even pre-gate screen, turnover bands, no name-level stops, stress tables, macro R-03 vol scaling on every momentum sleeve, and Korea caps with one pair-share denominator.",
"The only Korean stock-level return sources that both panels support and the labs confirm net of costs are subtractive screens: excluding the lottery composite adds +3.08%/yr net 35 on the equal-weighted KRX book (IR 1.53, 1996-03..2026-09; r2/kr/results/r2_kr_excl_summary.csv line 11) and excluding heavy issuers adds +2.34%/yr net 35 (IR 0.65; line 17); both are BUILD NOW as screen cards gated as CARD-O, weight 3 on equal-weighted and small/mid books, 1 on capped cap-weighted books and 0 on the top-200 book, with an indicative gate of 7 of 8 steps (REVISE) because the deflated Sharpe pooled over 176 trials is 0.94 (r2_kr_excl_gate.csv line 2).",
"On the index side, the KOSPI 20-day vol target (macro R-06) is the protective workhorse (rebuilt KOSPI 1996-09-02..2026-09-29, net 3 bp: max-drawdown gain +6.5 pp over the same-exposure static book, tail ratio 0.70, CARD-P PASS; r2/idx/results/r2_idx_protective_scorecard.csv line 5), floored trend x VT20 runs as FORWARD-SIM, and single-index trend is CARD-P only with alpha weight 0.",
"The DO-NOT-BUILD headline: Korean daily/weekly reversal (weekly L/S net-35 Sharpe -1.78, KRX ALL EW 1996-2026, kr/results/kr_key_numbers.csv line 30; break-even 12.5 bp per side), raw Korean 12-1 momentum, low volatility as Korean alpha, size, investor-flow direction rules, US PEAD and event drifts as cards, US single-index trend at 50 bp, classic technical and TradingView rules (Hansen SPA p 0.880 over 303 KOSPI timing rules, 1996-2026, 3 bp), intraday and short-horizon technical trading, deep/LLM strategies, macro x stock-signal terms and crypto reversal.",
"Fundamentals are the main hole: a Korean value-quality composite (KR-VQ) and a US value-quality composite (US-VQ) have support from both panels at weight 2 but stay UNTESTED until point-in-time OpenDART and FMP/EDGAR stores exist, so they are BACKLOG BUILD-candidates, not spec items.",
"Final Korea weights: raw 12-1 momentum 0, constrained momentum 1 (FORWARD-SIM), 52-week high 1 (feature), daily/weekly reversal 0 with a monthly guard 1, value 1, quality 1, KR-VQ 2 (pending PIT), investor flow 1 (logging only), earnings drift 1, low volatility 0 as alpha and 0 as protection (screen input only), size 0, KOSPI trend 0 alpha / 1 protective, VT20 2 protective, floored trend x VT20 2 (FORWARD-SIM), lottery and dilution screens 3/1/0 by book type.",
"Final US weights: stock momentum 1, reversal 0, value 1 inside US-VQ, quality 2 as a composite leg, US-VQ 2 (pending PIT data), low volatility 1 alpha and 1 protective (BACKLOG, judged against S_beta), flows 1 (display), PEAD 0 standalone, and SPY trend 0 alpha with protection 0 at 50 bp and 1 at futures cost (BACKLOG).",
"Attention did not follow evidence: executives spent their most claims on short-horizon technical trading (TF-61, 23 claims, refuted) and product composites (TF-47, 19), professors on classic technical rules (TF-60, 25, refuted) and the US value-quality composite (TF-43, 16), while the two screens that survived drew 9 (TF-12) and 6 (TF-13) claims.",
f"The spec's acceptance tests get {ngv} golden values ({gvs.get('traced',0)} traced to a file and line, {gvs.get('derived',0)} derived by stated arithmetic, {gvs.get('not traced',0)} not traced: the plateau and start-date sweep of the floored trend x VT20 cell, any ridge-combiner number, the new C3 controls, E5's sigma-ladder and SPY cumulative-step figures, and step 9 at 0.6 x OOS).",
"The macro spec owner receives 22 cross-spec amendments (among them Korea reversal 3 -> 0 and flows 3 -> 1 as supersessions of R-15/section 2.2, the CR-07 pair share of 53.71% on 2026-09-29 from the KRX daily file, S_beta in section 8.7, and CARD-P and speed cells for R-14) and 15 open questions, led by the ladder's threshold units.",
]
assert 10<=len(summary)<=12
for grp in [summary[0:2],summary[2:7],summary[7:9],summary[9:]]:
    P(' '.join(grp)); P()
P()
# ------------------------------------------------------------------ 2 rulings
P('## 2. Coordinator rulings (verbatim) and how they were applied')
P()
CR=[
('CR-01','CR-01 Low volatility (MC-11, EX-T-06, professors\' "protective low-vol sleeve at 2"): the pre-registered protective class requires protection to be shown against a static book with the same average exposure, because constant de-gearing lowers drawdown by itself. For a stock-selection sleeve the analogue is the same-beta static book S_beta = beta_hat x market + (1 - beta_hat) x cash, beta_hat pre-registered. On that comparator Korean low-vol fails PC-1 (ΔMDD -7 to -22 pp) and PC-2 (tail ratio 0.97-0.99). So low-vol is neither an alpha card nor a protective card: it enters as a screen input (the high-volatility tail exclusion inside the lottery screen) and, at most, a FORWARD-SIM descriptive sleeve with S_beta pre-registered. Add S_beta to governance as the CARD-P comparator for stock-level sleeves. US low-vol stays BACKLOG (alpha net of beta untested).',
 'TF-16 stays CONTESTED and goes to FS-3 (descriptive); TF-17 low-vol alpha is CORE-PROHIBITION (DNB-TF-02); low-vol enters SCR-1 as the high-volatility tail; S_beta is GOV-11 (TF-59) and cross-spec XS-12; Korea low-vol weights alpha 0, protective 0, screen input; US low-vol BACKLOG (BL-TF-03).'),
('CR-02','CR-02 Trend (EX-T-01, MC-06, MC-07): a standalone index trend sleeve (its own capital line, long/flat ETF or futures) is a strategy card and may hold 0, like card C3; when trend scales any other book it is an overlay bounded to [0.5, 1.0] (macro P2). Single-index trend is CARD-P only, never CARD-O. The 20-day volatility target (macro R-06) is the robust protective workhorse; KOSPI floored trend x VT20 runs as FORWARD-SIM; trend alone has protective weight 1 (its KOSPI evidence rests on 1997-2001); US single-index trend at 50 bp per side is REJECT, futures cost only, BACKLOG. Propose to the macro spec owner: R-14 gets a CARD-P cell and a speed cell.',
 'TF-30 (IDX-0 class rule), TF-31 (IDX-1 = R-06), TF-32 (FS-1), TF-33 resolved as a class rule, TF-34 (DNB-TF-05 at 50 bp; BL-TF-08 at futures cost); KOSPI trend alpha 0 / protective 1, VT20 2, floored product 2; XS-09.'),
('CR-03','CR-03 Korean short-term reversal and investor flows (MC-08, MC-09): this programme owns signal-family weights; the macro spec deferred reversal to its own net-of-cost test, which now fails. Korea ST-reversal alpha 3 -> 0 (daily/weekly DROP; monthly reversal only as a conditioning guard of weight 1: do not buy last month\'s top-decile winners). Korea investor flow 3 -> 1 (log flows now with timestamps; no direction rule; t-1 history required). Record these as supersessions of macro R-15 / §2.2 for the owner to confirm.',
 'TF-41 CORE-PROHIBITION (DNB-TF-07); TF-42 guard as FS-5; TF-39 flow direction CORE-PROHIBITION (DNB-TF-06); TF-40 flow logging as DATA-6; XS-01, XS-02 recorded as supersessions.'),
('CR-04','CR-04 Korean value, quality, earnings drift: individual weights 1 until a point-in-time OpenDART test exists (INSUFFICIENT DATA today); one pre-registered KR-VQ composite (value + profitability + net issuance) carries weight 2 as a BUILD-candidate pending the PIT store. US: US-VQ composite weight 2 pending FMP/EDGAR PIT data; US PEAD standalone DROP.',
 'TF-36 (KR-VQ, weight 2, BL-TF-10), TF-37 and TF-38 (weights 1), TF-43 (US-VQ, weight 2, BL-TF-12), TF-45 (US PEAD and event drifts, DNB-TF-09).'),
('CR-05','CR-05 Korean momentum: raw 12-1 card DROP (alpha 0). A constrained variant (12-1 or 12-7, excluding the highest-turnover/lottery names, own-vol-scaled, capped, long-only) is a FORWARD-SIM card at weight 1; momentum sleeves in every market get macro R-03 vol scaling as a risk control; the Daniel-Moskowitz gate (R-04) stays on the specification book only.',
 'TF-20 (DNB-TF-04), TF-21 (FS-2), TF-22 (MOM-1), TF-23 (MOM-2 spec book only); SCR-3 construction rule; XS-10, XS-15, XS-18.'),
('CR-06','CR-06 Exclusion screens: the lottery composite (volatility + MAX + turnover) and the net-issuance/dilution screen are BUILD NOW as screen cards gated as CARD-O against the unscreened base book on the same days (no new class needed), declared per book type: weight 3 on equal-weighted and small/mid books, 1 (hygiene) on capped cap-weighted books, 0 for the top-200 book (REJECT there). The attention-fade event screen is DROP as a monthly screen but becomes an execution INVARIANT: never enter at a locked limit-up close.',
 'TF-12 (SCR-1), TF-13 (SCR-2), TF-15 (SCR-3); TF-14 moved from ONE-SIDED to CORE-PROHIBITION (DNB-TF-01) with its entry-day part in INV-2.'),
('CR-07','CR-07 Drawdown ladder (MC-01..MC-05, MC-16): this programme does not change macro R-07 thresholds. It proposes answers to the macro backlog\'s open points for the owner: steps non-cumulative; applied to total book NAV only; re-arm at 0.5 with the reference peak reset; caps by book type (0.05 single name in selection sleeves; 0.35 pair cap on look-through for market/ETF books); one pre-registered pair-share denominator: numerator = market cap of 005930 + 005935 + 000660, denominator = total market cap of all KOSPI-listed shares in the KRX daily all-stock file (compute the 2026-09-29 value from /home/claude/data_raw/marcap/data/marcap-2026.parquet and report alternatives). Threshold units (fixed % vs book-volatility units, or a book-vol ceiling) are an owner decision: record the evidence (P(-15% within 10 years) 0.97 at 12% vol and Sharpe 0.5; 0.66 at 8%).',
 'Pair share computed (section 11.1): 53.71% on 2026-09-29; TF-26 (RISK-1), TF-27 (XS-08 proposal), TF-28 (OQ-01); XS-06, XS-07, XS-22.'),
('CR-08','CR-08 Gate amendments: tightening or reporting only, never loosening: block length max(10, Politis-White on d and d^2) for steps 2 and 5 on every card (10-session blocks gave 7-8% / 13% false passes at nominal 5% / 10%); a family gate (Hansen SPA or StepM within a technical-rule family; BH-FDR across a release, reported); a trial registry with a global N for the deflated Sharpe; an attribution block on every card (beta, Jensen\'s alpha with Newey-West t, FF5+Mom for US cards, local KRX factors for Korea; "factor tilt" label when alpha disappears); long-only primary statistic and declared benchmark for KRX cards; S_beta comparator (CR-01); a break-even pre-gate screen (reject before the gate if break-even per-side cost < 2x the pre-registered cost); step 8 and step 9 unchanged (report step 8\'s stand-alone weakness; an alpha-only haircut may be printed as an extra line).',
 'GOV-1..GOV-7 and GOV-11 (TF-06, TF-07, TF-50, TF-51, TF-53, TF-55, TF-59); TF-50 moved from ONE-SIDED to CORE-LINK; tiered hurdles (TF-52) and the Jensen-alpha step-5 variant are not adopted (OQ-05, OQ-10); XS-11, XS-13.'),
('CR-09','CR-09 Execution conventions are INVARIANTS: decide at the close t; fill at the KRX official close t (bound: close t+1); never NXT/after-hours prints; locked limit-up: no entry; locked limit-down exits carry to the first unlocked session at 2x cost; VI/circuit-breaker/halt days unfillable; no name-level stops (signal exits; stops on trend sleeves only via the signal); corporate-action-adjusted returns with |Δln shares| > 1% flagged; capacity <= 1-2% of 20-day ADV; buy/hold bands and a turnover limit.',
 'INV-1..INV-5 (TF-01, TF-02, TF-03, TF-08, TF-10).'),
('CR-10','CR-10 Crypto: C3 stays PASS; add a vol-scaled long-only control, a pre-registered split at the US spot-ETF date (2024-01-10) and an ETH replication; crypto short-term reversal 2 -> 0 (short-horizon crypto evidence is momentum); CTREND-lite technical composite BACKLOG.',
 'TF-67 (CRY-1), TF-68 (DNB-TF-16), TF-69 (BL-TF-19); XS-17.'),
('CR-11','CR-11 ML: an equal-weight z-score composite is the baseline combiner (BUILD with the first composite card); a ridge/Fama-MacBeth challenger shrunk to priors runs FORWARD-SIM; gradient boosting and small nets BACKLOG; deep price-pattern, order-book and LLM-news strategies DROP; macro variables never interact with stock signals.',
 'TF-63 (ML-1 and FS-4), TF-64 (BL-TF-18), TF-65 (DNB-TF-14); TF-66 moved from ONE-SIDED to CORE-PROHIBITION (DNB-TF-15).'),
('CR-12','CR-12 Valuation timing (CAPE, Fed model, forward P/E) is CONTEXT only; classic technical index-timing rules (RSI, MACD, Bollinger, Donchian, golden/dead cross, candlesticks, Fibonacci, Elliott, chart patterns, TradingView-sourced strategies) are DO-NOT-BUILD as signals unless they pass the family gate and the nine-step gate as a new card.',
 'TF-48 (DNB-TF-11, CONTEXT display), TF-60 (DNB-TF-12).'),
]
for cid,txt,app in CR:
    P('> '+txt)
    P()
    P('Applied: '+app)
    P()
# ------------------------------------------------------------------ 3 method
P('## 3. Method')
P()
P('**Inputs, in order.** 00_QUANTGEN_context.md; the two chair resolutions (R2_PROF, R2_EXEC); the claim matrices and verification logs (`r2/verification/`); the four lab summaries and their result CSVs (KR R1, US R1, R2 KR, R2 IDX, plus the exec chair checks c01-c12); the 14 round-1 papers only to look up wording or URLs; the macro spec v1.2 (project doc `claude/QUANTGEN_MACRO_INTEGRATION.md`) for conflicts and naming. Extracts are in `R3_working_notes.md` (sections A-H).')
P()
P('**Nodes.** Each node states one proposition, written so that a panel can support or refute it. Every proposition of both claim matrices (60 + 60) and every chair item (115) maps onto at least one node; a proposition maps as primary to one node and may map as secondary to others, either whole or by named claims (e.g. `X27:E7-C25,E5-C03`).')
P()
P('**Focus intensity fp / fe.** The number of distinct professor (fp) and executive (fe) claims mapped to the node: all ledger claims (supporting and qualifying, claim ranges expanded) of its primary propositions, plus only the named claims of secondary mappings, plus distinct non-ledger references. Chair and lab conclusions never add to fp or fe. Claims can sit on more than one node, so column totals exceed 209 / 205.')
P()
P('**Panel strength (ps, es).** Strong: a chair consensus item with three or more supporting members and verification MATCH (or chair re-computation). Moderate: one or two members, or consensus reached after qualification or cross-examination. Weak: one member, unverified or heavily qualified. Split: members disagree and the chair records a contested item. Silent: no claim from that panel. Refuted: the chair refuted or withdrew the item.')
P()
P('**Data column.** Supports: lab or chair re-computations agree with the node at QUANTGEN net costs. Mixed: some books, periods or designs agree and others do not, or only gross support exists. Refutes: the data contradict the node. Untested: no local data.')
P()
P('**Class rule, in order of precedence (checked mechanically; 0 mismatches between the stated and computed rule class):**')
P('1. CORE-PROHIBITION: both panels Refuted, or one Refuted with data Refutes and the other Silent.')
P('2. ONE-SIDED: one panel Silent (and rule 1 does not apply).')
P('3. CORE-LINK: both panels Moderate or Strong, and data Supports or Mixed; if data Refutes the node is CONTESTED; if data is Untested for an empirical claim it is UNTESTED (design rules TF-04, TF-40 and TF-63 are exempt).')
P('4. CONTESTED: a panel is Split, or the panels disagree (Refuted against Weak or better).')
P('5. ONE-SIDED: Moderate or Strong against Weak; Weak against Weak with no data is UNTESTED.')
P('Coordinator rulings override the rule where they speak; the three overrides are listed in section 4.')
P()
P('**Edges.** Four types: supports, refutes, qualifies, conflicts; each has a one-line reason with its evidence (Appendix B and R3_TF_edges.csv).')
P()
P('**Weight rules (0-3 priors; not gate results).** W1: a coordinator ruling decides where it speaks. W2: otherwise, if the panels agree, that value. W3: otherwise the lower panel value, unless lab data at QUANTGEN net costs support the higher one (the gate is never loosened). W4: a cell only one panel reviewed keeps that panel\'s value, flagged * (it cannot feed any book until a card passes). W5: cells no panel reviewed keep the prior, flagged n.r. Proposed normalisation for macro R-15: base_weight = w / 3, so a weight of 3 equals 1.0x and no weight implies a multiplier above 1.0.')
P()
P('**Golden values.** Read programmatically from the named file and row (`scripts/r3_03_golden_values.py`); "derived" values state their arithmetic; "not traced" values give the reason. Chair-resolution text lines used as sources are checked for the quoted string.')
P()
# ------------------------------------------------------------------ 4 counts
P('## 4. Node counts by class')
P()
rows=[]
for c in CLS:
    rows.append([c, cnt.get(c,0), cntm.get(c,0), ', '.join(N[N.cls==c].node_id.tolist())])
rows.append(['Total', len(N), len(N), ''])
P(table(rows,['Class','Final','Rule-based (before rulings)','Nodes']))
P()
ch=N[N.class_changed_by_ruling.astype(str)=='True']
P('Rulings that changed a class: '+'; '.join(f"{r.node_id} {r.class_mechanical} -> {r.cls} ({r.ruling})" for _,r in ch.iterrows())+'.')
P()
th=N.groupby('theme').agg(n=('node_id','count'),fp=('fp','sum'),fe=('fe','sum')).reset_index()
rows=[]
for _,r in th.iterrows():
    sub=N[N.theme==r.theme]
    rows.append([r.theme,r.n]+[int((sub.cls==c).sum()) for c in CLS]+[r.fp,r.fe])
P(table(rows,['Theme','Nodes']+CLS+['fp (sum)','fe (sum)']))
P()
# ------------------------------------------------------------------ 5 core-link
P('## 5. CORE-LINK list (both panels support; data supports or is not contrary) -> integration spec')
P()
P('Each entry gives the node, focus intensity (fp, fe), panel strength, data, key numbers with sources, the chair items behind it and the destination; member claim IDs and URLs are in R3_TF_nodes.csv.')
P()
P('Spec destinations proposed for the Claude Code integration spec: section TF-1 execution invariants (INV-1..INV-5), TF-2 data (DATA-1..DATA-6), TF-3 screens (SCR-1..SCR-3), TF-4 momentum risk and concentration (MOM-1, MOM-2, RISK-1), TF-5 index protective rules (IDX-0, IDX-1), TF-6 fundamentals (FUND-1 KR-VQ and FUND-2 US-VQ, activated only when the point-in-time stores exist), TF-7 governance (GOV-1..GOV-11), TF-8 ML (ML-1), TF-9 crypto (CRY-1); FORWARD-SIM cells FS-1..FS-5. Proposed package placement, following macro section 3 (the integration spec decides): fills, costs and the gate in core/quant/backtest; screens and the composite in core/quant/signals (family tags); vol scaling, caps and the ladder in core/quant/risk (macro R-03, R-07); regime flags in core/calendars and the point-in-time data layer; card headers and pre-registration in core/rules; FORWARD-SIM cells in the third (forward) book, never in the displayed book.')
P()
order=['A. Data hygiene and execution','B. Screens','C. Momentum and portfolio risk','D. Protective index rules','E. Fundamentals, flows and reversal','F. Governance and technical-rule standards','G. ML combiners','H. Crypto and FX']
titles={'A. Data hygiene and execution':'5.1 Data hygiene and execution','B. Screens':'5.2 Screens','C. Momentum and portfolio risk':'5.3 Momentum risk and concentration',
        'D. Protective index rules':'5.4 Protective index rules','E. Fundamentals, flows and reversal':'5.5 Fundamentals, flows and reversal (no fundamental composite reaches CORE-LINK: both are UNTESTED, section 7)',
        'F. Governance and technical-rule standards':'5.6 Governance','G. ML combiners':'5.7 ML','H. Crypto and FX':'5.8 Crypto'}
def node_block(r, prohib=False, tag=''):
    head=f"**{tag}{r['node_id']}** (fp {r['fp']}, fe {r['fe']}; professors {r['ps']}, executives {r['es']}; data {r['data']})"
    P(f"{head}. {'Refuted proposition: ' if prohib else ''}{r['label']}")
    P()
    if r['key_numbers']: P(f"- Key numbers: {r['key_numbers']}")
    if r['data_files'] and r['data_files']!='-': P(f"- Sources: {r['data_files']}")
    ci=', '.join(x for x in [r['prof_chair_items'], r['exec_chair_items']] if x and not x.strip().startswith('-'))
    if ci: P(f"- Chair items: {ci}")
    if r['settling_test'] and not prohib: P(f"- Settling test: {r['settling_test']}")
    P(f"- Destination: {r['destination']} ({r['decision']})" + (f"; ruling {r['ruling']}" if r['ruling'] else ''))
    P()
for t in order:
    sub=N[(N.theme==t)&(N.cls=='CORE-LINK')]
    if len(sub)==0: continue
    P('### '+titles[t]); P()
    for _,r in sub.iterrows(): node_block(r)
# ------------------------------------------------------------------ 6 prohibition
P('## 6. CORE-PROHIBITION list -> DO-NOT-BUILD')
P()
P('Each entry states the refuted proposition. DNB-TF ids are proposed additions to macro section 10 (overlaps noted in XS-19). TF-19 and TF-57 are anchors that must not propagate (section 12).')
P()
pro=N[N.cls=='CORE-PROHIBITION'].copy()
pro['dnb']=[ (re.search(r'DNB-TF-\d\d',d).group(0) if re.search(r'DNB-TF-\d\d',d) else 'CA') for d in pro.destination]
pro=pro.sort_values(['dnb','node_id'])
for _,r in pro.iterrows():
    node_block(r, prohib=True, tag=(r['dnb']+' / ' if r['dnb']!='CA' else 'Anchor / '))
P('Headline: on QUANTGEN costs nothing short-horizon survives (KRX round trip 25-46 bp before impact; weekly reversal breaks even at 12.5 bp per side), no single-index timing rule beats buy-and-hold after a data-snooping control, and Korean low volatility, size and raw momentum are factor tilts or cost-eaten spreads rather than alpha.')
P()
# ------------------------------------------------------------------ 7 contested etc
P('## 7. CONTESTED, ONE-SIDED and UNTESTED lists (-> backlog, with settling tests)')
P()
for c,txt in [('CONTESTED','panels disagree or a panel is split'),('ONE-SIDED','only one panel holds the proposition'),('UNTESTED','both panels lean the same way but no local data exist')]:
    P(f'### 7.{CLS.index(c)-1} {c} ({cnt.get(c,0)} nodes; {txt})')
    P()
    for _,r in N[N.cls==c].iterrows(): node_block(r)
# ------------------------------------------------------------------ 8 focus map
P('## 8. Focus map: where attention went')
P()
N['tot']=N.fp+N.fe
top=N.sort_values(['tot','fe'],ascending=False).head(15)
rows=[[i+1,r.node_id,r.label[:110]+('...' if len(r.label)>110 else ''),r.fp,r.fe,f"{r.fp/(r.tot):.0%}" if r.tot else '-',r.cls,r.destination] for i,(_,r) in enumerate(top.iterrows())]
P(table(rows,['Rank','Node','Proposition (shortened)','fp','fe','Professor share','Class','Destination']))
P()
P(f"Totals: fp {N.fp.sum()} and fe {N.fe.sum()} across the 70 nodes (claims mapped to more than one node count once per node). Of the top 15, {int((top.cls=='CORE-LINK').sum())} are CORE-LINK, {int((top.cls=='CORE-PROHIBITION').sum())} CORE-PROHIBITION and {int((top.cls=='UNTESTED').sum())} UNTESTED.")
P()
P('Where attention went:')
P('- Executives concentrated on execution and data (theme A: fe 101 vs fp 52), momentum crashes and concentration (C: 63 vs 29), events and products (E), and short-horizon trading (TF-61: 23 claims). Professors concentrated on governance and technical-rule standards (F: fp 97 vs fe 49), fundamentals (E: 84) and ML (G: 28 vs 7).')
lop_p=N[(N.tot>=6)&(N.fp>=3*N.fe.clip(lower=1))].sort_values('tot',ascending=False)
lop_e=N[(N.tot>=6)&(N.fe>=3*N.fp.clip(lower=1))].sort_values('tot',ascending=False)
P('- Professor-dominated nodes (fp at least 3x fe, total >= 6): '+', '.join(f"{r.node_id} ({r.fp}/{r.fe}, {r.cls})" for _,r in lop_p.iterrows())+'.')
P('- Executive-dominated nodes (fe at least 3x fp, total >= 6): '+', '.join(f"{r.node_id} ({r.fp}/{r.fe}, {r.cls})" for _,r in lop_e.iterrows())+'.')
P('- Attention and evidence diverge: the two BUILD NOW screens drew 9 (TF-12) and 6 (TF-13) claims, the VT20 workhorse 3 (TF-31) and the floored trend x VT20 cell 3 (TF-32), while three of the four most-discussed nodes ended refuted or untested (TF-61, TF-60 refuted; TF-43 untested).')
P('- Both panels converged where the labs could compute: execution, hygiene, costs and crash risk are CORE-LINK with Strong support on both sides; disagreement is concentrated where data are missing (fundamental weights, drift, 52-week high, cost buckets) or where the question is a design convention (sleeve vs overlay, step 8/9).')
P()
P('The full focus map (all 70 nodes with fp, fe, class, label and destination, plus edges) is `charts/focus_map.json`; theme totals are in `results/r3_focus_by_theme.json`.')
P()
# ------------------------------------------------------------------ 9 weights
P('## 9. Weight table (per market x family; alpha / protective / screen)')
P()
P('Weights are 0-3 design priors, not gate results; any weight of 2 or more still needs a PASS card before it can feed the displayed book. Proposed normalisation base_weight = w / 3 (never above 1.0x). Rules W1-W5 in section 3; * = one panel only; n.r. = no panel reviewed.')
P()
for mk in ['Korea','US','Crypto','Futures/FX']:
    sub=W[W.market==mk]
    P(f'### 9.{["Korea","US","Crypto","Futures/FX"].index(mk)+1} {mk}')
    P()
    rows=[[r.family,r.column,r.prior,r.professors,r.executives,r.final,r.rule,r.reason,r.nodes] for _,r in sub.iterrows()]
    P(table(rows,['Family','Column','Prior','Professors','Executives','Final','Rule','Reason (market, period, gross/net, source)','Nodes']))
    P()
P('### 9.5 Markets without a QUANTGEN data path (CONTEXT only; professors\' consolidated row, executives\' trend cell; TF-49)')
P()
P(table(WO.values.tolist(),list(WO.columns)))
P()
P('Final Korea row (one line): raw 12-1 0 | constrained momentum 1 (FS-2) | 52-week high 1 (feature) | reversal daily/weekly 0, monthly guard 1 (FS-5) | value 1 | quality 1 | KR-VQ 2 (pending PIT) | lottery screen 3 / 1 / 0 and dilution screen 3 / 1 / 0 (EW and small/mid / capped CW / top 200) | low-vol alpha 0, protective 0, screen input | flow 1 (logging) | drift 1 | size 0 | KOSPI trend alpha 0, protective 1 | VT20 protective 2 | floored trend x VT20 protective 2 (FS-1) | KOSDAQ trend 0 | R-03 on every momentum sleeve.')
P()
P('Final US row (one line): stock momentum 1 | reversal 0 | value 1 (inside US-VQ) | quality 2 (composite leg, not a hedge) | US-VQ 2 (pending FMP/EDGAR PIT) | net issuance inside US-VQ | low-vol alpha 1, protective 1 (BACKLOG, vs S_beta) | flow 1 (display) | PEAD 0 standalone | SPY trend alpha 0, protective 0 at 50 bp / 1 at futures cost (BACKLOG) | SPY VT15 0 at 50 bp / 1 at futures cost | insiders 0 (BACKLOG) | IPO-age screen 2* (inactive) | lottery screen 1* | distress screen BACKLOG.')
P()
# ------------------------------------------------------------------ 10 go/no-go
P('## 10. Go / no-go register')
P()
dc=G.decision.value_counts()
groups=[('10.1 BUILD NOW, INVARIANT and GOVERNANCE',lambda d: d.startswith('BUILD') or d.startswith('INVARIANT') or d.startswith('GOVERNANCE') or d.startswith('KEEP') or d.startswith('SPEC BOOK')),
        ('10.2 FORWARD-SIM',lambda d: d.startswith('FORWARD-SIM')),
        ('10.3 BACKLOG',lambda d: d.startswith('BACKLOG')),
        ('10.4 OWNER DECISION and CONTEXT',lambda d: d.startswith('OWNER') or d.startswith('CONTEXT') or d.startswith('GOVERNANCE option')),
        ('10.5 DROP and DO-NOT-BUILD',lambda d: d.startswith('DROP') or d.startswith('DO-NOT'))]
used=set()
P(f'{len(G)} items. Columns: evidence for, evidence against, indicative gate outcome, and what would change the decision. Full register: `results/r3_go_nogo.csv` and `charts/go_nogo.json`. '
  'Numbers here are short forms of labelled values given in the node entries (sections 5-7) and the golden values (section 11): unless stated otherwise, KRX screen figures are 1996-03..2026-09 at net 35 (r2/kr/results/r2_kr_excl_*.csv), KRX signal figures 1996-2026 at net 35 (kr/results, r2/kr/results), KOSPI index figures 1996-09-02..2026-09-29 at net 3 bp and SPY figures 1999-05..2021-03 (r2/idx/results); B1-B4 are the four base books defined in section 11.2.')
P()
for title,f in groups:
    sub=G[[f(d) and i not in used for i,d in zip(G.id,G.decision)]]
    if title.startswith('10.1'): sub=sub[~sub.decision.str.startswith('GOVERNANCE option')]
    used|=set(sub.id)
    P('### '+title); P()
    rows=[[r['id'],r['item'],r['market'],r['decision']+(f" ({r['ruling']})" if r['ruling'] not in ('','-') else ''),r['evidence_for'],r['evidence_against'],r['indicative_gate'],r['what_would_change_it'],r['nodes'],r['target']] for _,r in sub.iterrows()]
    P(table(rows,['ID','Card or rule','Market','Decision (ruling)','Evidence for','Evidence against','Indicative gate','What would change it','Nodes','Target']))
    P()
assert used==set(G.id), set(G.id)-used
# ------------------------------------------------------------------ 11 golden values
P('## 11. Golden values for the spec\'s acceptance tests')
P()
P(f'{ngv} values in `results/r3_golden_values.csv` and `charts/golden_values.json` ({gvs.get("traced",0)} traced, {gvs.get("derived",0)} derived, {gvs.get("not traced",0)} not traced). The table below lists the values every BUILD NOW and FORWARD-SIM item must reproduce, plus the reference values that pin the engines; the CSV holds the rest under the same GV ids. Tolerance proposal: reproduce traced values to the printed precision (Level 1), derived values within 1 bp, and verdict strings exactly.')
P()
import warnings; warnings.filterwarnings('ignore')
shown=set()
def ids_compact(ids):
    nums=sorted(int(i.split('-')[1]) for i in ids)
    out=[]; s=p=None
    for n in nums:
        if s is None: s=p=n
        elif n==p+1: p=n
        else: out.append((s,p)); s=p=n
    if s is not None: out.append((s,p))
    return ', '.join(f"GV-{a:03d}" if a==b else f"GV-{a:03d}..{b:03d}" for a,b in out)
def one(cards, qre, gn=None, per=None):
    m=GV.card_or_rule.isin(cards)&GV.quantity.str.contains(qre,regex=True)
    if gn: m&=GV.gross_net.str.contains(gn,regex=False)
    if per: m&=(GV.period==per)
    x=GV[m]
    if len(x)==0: return None
    assert len(x)==1,(cards,qre,gn,per,len(x))
    return x.iloc[0]
def cellv(rows_used, row):
    if row is None: return '-'
    rows_used.append(row); shown.add(row['gv_id']); return row['value']
def lines_of(rows_used):
    d={}
    for r in rows_used:
        for part in str(r['line']).split(';'): d.setdefault(r['source_file'].split('/')[-1],[]).append(part)
    return '; '.join(f"{k} {'/'.join(dict.fromkeys(v))}" for k,v in d.items())
# --- pair share (CR-07)
P('### 11.1 Pair-share computation for CR-07 (KRX daily all-stock file)')
P()
P('Source: `/home/claude/data_raw/marcap/data/marcap-2023..2026.parquet`, Market == KOSPI, all listed lines; common lines are codes ending in 0. Script `scripts/r3_01_pair_share.py`; outputs `results/r3_pair_share.csv`, `r3_pair_share_summary.csv`, `r3_pair_share_2026_daily.csv` (all four definitions, daily 2026).')
P()
cols=['date','n_kospi_lines','n_common_lines','CR07_pair_incl_pref_over_all_lines','alt_pair_common_over_all_lines','alt_pair_common_over_common_only','alt_pair_incl_pref_over_common_plus_pref']
rows=[[r['date'],r['n_kospi_lines'],r['n_common_lines']]+[f"{float(r[c]):.2%}" for c in cols[3:]] for _,r in PS.iterrows()]
P(table(rows,['Date','KOSPI lines','Common lines','CR-07: (005930+005935+000660) / all lines','(005930+000660) / all lines','(005930+000660) / common lines','(005930+005935+000660) / (common + 005935)']))
P()
P('2026 series (r3_pair_share_summary.csv, file line = row + 1):')
P()
P(table([[i+2,r['item'],r['value']] for i,(_,r) in enumerate(PSS.iterrows())],['Line','Item','Value']))
P()
P('The executives\' chair date "first above 0.45 on 7 May 2026" (R2_EXEC A5) belongs to the common-lines-over-all-lines definition; under CR-07 the cap first binds one session earlier, on 2026-05-06.')
P()
rs=GV[GV.card_or_rule=='RISK-1 pair-share series (R-07 pair cap)']
shown|=set(rs.gv_id)
P(f"Golden values for RISK-1: {ids_compact(rs.gv_id)} (r3_pair_share.csv lines 2-9; r3_pair_share_summary.csv lines 2-9).")
P()
# --- (a) screens pivot
P('### 11.2 Screens: SCR-1 (F4 lottery composite), SCR-2 (F6 dilution), SCR-3 (F1 highest-turnover quintile) and the dropped F5')
P()
P('KRX, 366 monthly formations 1996-03..2026-09, filtered minus unfiltered book, %/yr. B1 = EW ALL book; B2 = VW ALL 5%-capped; B3 = top-200 VW 5%-capped; B4 = 12-1 momentum top quintile EW. IR, t, years and drawdown at net 35; break-even = gross difference / extra one-way turnover (derived); sub-periods at net 35; gate = indicative steps passed of 8, verdict, deflated Sharpe pooled over 176 trials.')
P()
SCR=[('SCR-1 F4',['SCR-1 lottery composite exclusion (F4, worst decile of vol+MAX+turnover ranks)','SCR-1 lottery composite'],['B1','B2','B3','B4']),
     ('SCR-2 F6',['SCR-2 dilution exclusion (F6, 252-session share growth > 10%)','SCR-2 dilution screen'],['B1','B2','B3','B4']),
     ('SCR-3 F1',['SCR-3 construction rule (F1, highest-turnover quintile excluded)'],['B1','B4']),
     ('F5 (DROP)',['F5 attention-fade monthly screen (DROP)'],['B1','B2','B3','B4'])]
rows=[]
for nm,cards,books in SCR:
    for b in books:
        u=[]
        g=cellv(u,one(cards,rf'^{b} \(.*filtered minus unfiltered','gross')); n35=cellv(u,one(cards,rf'^{b} \(.*filtered minus unfiltered','net 35')); n70=cellv(u,one(cards,rf'^{b} \(.*filtered minus unfiltered','net 70'))
        ir=cellv(u,one(cards,rf'^{b}(/F\d)?: information ratio')); t=cellv(u,one(cards,rf'^{b}(/F\d)?: Newey-West t')); yrs=cellv(u,one(cards,rf'^{b}(/F\d)?: share of years positive'))
        dd=cellv(u,one(cards,rf'^{b}(/F\d)?: max DD filtered')); be=cellv(u,one(cards,rf'^{b}: break-even'))
        sp=' / '.join(cellv(u,one(cards,rf'^{b}: diff %/yr, sub-period',per=p)) for p in ['1996-2005','2006-2015','2016-2026-09'])
        st=cellv(u,one(cards,rf'^{b}/F\d: indicative gate steps')); vd=cellv(u,one(cards,rf'^{b}/F\d: indicative verdict')); ds=cellv(u,one(cards,rf'^{b}/F\d: deflated Sharpe'))
        gate='-' if st=='-' else f"{st}/8 {vd}, DSR {ds}"
        if not u: continue
        rows.append([nm,b,g,n35,n70,ir,t,yrs,dd,be,sp if sp!='- / - / -' else '-',gate,ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P(table(rows,['Screen','Book','Gross','Net 35','Net 70','IR','NW t','Years +','dMDD','Break-even bp/side','Sub-periods 96-05 / 06-15 / 16-26','Gate','GV ids','Source lines']))
P()
u=[]; v=cellv(u,one(['SCR-1 lottery composite'],r'best of 176'))
P(f"Best of the 176 exclusion trials (B1, F4 at a 5% cut): pooled deflated Sharpe {v} ({ids_compact([r['gv_id'] for r in u])}; {lines_of(u)}). The lab's step-9 column prints 0.4 x diff (B1/F4 +1.23%/yr, r2_kr_excl_gate.csv line 2); the spec's step 9 is 0.6 x OOS (section 12, CA-21).")
P()
# --- (b) CARD-P scorecards pivot
P('### 11.3 Index protective scorecards (CARD-P checks vs the same-exposure static book S)')
P()
cards=['IDX-1 index vol target','IDX trend sleeve','IDX trend x vol target','IDX SMA200','IDX 12-month sign']
sub=GV[GV.card_or_rule.isin(cards)].copy(); sub['cell']=sub.quantity.str.split(':').str[0]; sub['metric']=sub.quantity.str.split(': ').str[1]
mets=['PC-1 dMDD vs S at 1x (pp)','PC-1 dMDD vs S at 2x (pp)','PC-2 tail-exposure ratio','PC-3 dSR vs S','PC-3 non-inferiority p','PC-5 share of years positive','PC-6 plateau share','CARD-P verdict']
rows=[]
for cell,x in sub.groupby('cell',sort=False):
    u=[]; vals=[]
    for mt in mets:
        y=x[x.metric==mt]
        if len(y)==1: vals.append(cellv(u,y.iloc[0]))
        else: vals.append('-')
    r0=x.iloc[0]
    rows.append([cell,r0['market'],r0['period'],r0['gross_net']]+vals+[ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P(table(rows,['Cell','Market','Period','Cost']+['PC-1 1x','PC-1 2x','PC-2 tail','PC-3 dSR','p non-inf.','PC-5 years','PC-6 plateau','Verdict']+['GV ids','Source lines']))
P()
# --- (c) FS-1 cells pivot
P('### 11.4 FS-1 floored trend x VT20 and its comparison cells (KOSPI rebuilt 1996-09-02..2026-09-29, net 3 bp per side)')
P()
cards=['FS-1 KOSPI floored trend x VT20 (primary)','FS-1 comparison cells']
sub=GV[GV.card_or_rule.isin(cards)].copy(); sub['cell']=sub.quantity.str.split(':').str[0]; sub['metric']=sub.quantity.str.split(': ').str[1]
mets=[('average exposure','Avg exposure'),('max DD','Max DD'),('PC-1 dMDD vs own S (pp)','PC-1 vs own S'),('PC-2 tail ratio','PC-2 tail'),('dSR vs S','dSR'),('share of years positive','Years +'),('indicative CARD-P verdict','Verdict'),('1997-98 episode return','1997-98'),('2026-06-22..07-30 crash return','2026 crash')]
rows=[]
for cell,x in sub.groupby('cell',sort=False):
    u=[]; vals=[]
    for mt,_ in mets:
        y=x[x.metric==mt]; vals.append(cellv(u,y.iloc[0]) if len(y)==1 else '-')
    rows.append([cell]+vals+[ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P(table(rows,['Cell']+[h for _,h in mets]+['GV ids','Source lines']))
P()
nt1=GV[(GV.status=='not traced')&GV.card_or_rule.str.startswith('FS-1')]
P(f"Not evaluated: {'; '.join(nt1.quantity)} ({', '.join(nt1.gv_id)}). The first FORWARD-SIM release must add the plateau (PC-6) and the start-date sweep for the primary cell.")
P()
# --- (d) start-date pivot
P('### 11.5 Start-date sensitivity (KOSPI rebuilt, net 3 bp; verdict and PC-1 in pp)')
P()
sub=GV[GV.card_or_rule=='IDX start-date sensitivity'].copy()
sub['cell']=sub.quantity.str.extract(r'^(.*) from ')[0]; sub['start']=sub.quantity.str.extract(r' from (\d{4}-\d\d-\d\d)')[0]
cells=list(dict.fromkeys(sub.cell)); rows=[]
for st,x in sub.groupby('start'):
    u=[]; vals=[]
    for c in cells:
        y=x[x.cell==c]; vals.append(cellv(u,y.iloc[0]) if len(y)==1 else '-')
    rows.append([st]+vals+[ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P(table(rows,['Start']+cells+['GV ids','Source lines']))
P()
# --- (e) low-vol vs S_beta pivot
P('### 11.6 FS-3 Korean low volatility against the same-beta static book S_beta (KRX 1996-2026, net 35, rf 0)')
P()
sub=GV[GV.card_or_rule=='FS-3 KRX low-vol descriptive sleeve vs S_beta'].copy(); sub['cell']=sub.quantity.str.split(':').str[0]; sub['metric']=sub.quantity.str.split(': ').str[1]
mets=[('beta','Beta'),('max DD book','Max DD book'),('max DD same-beta static S_beta','Max DD S_beta'),('dMDD vs S_beta (pp)','dMDD (pp)'),('Sharpe book','Sharpe book'),('Sharpe S_beta','Sharpe S_beta'),('tail ratio vs S_beta','Tail ratio')]
rows=[]
for cell,x in sub.groupby('cell',sort=False):
    u=[]; vals=[]
    for mt,_ in mets:
        y=x[x.metric==mt]; vals.append(cellv(u,y.iloc[0]) if len(y)==1 else '-')
    rows.append([cell]+vals+[ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P(table(rows,['Comparison']+[h for _,h in mets]+['GV ids','Source lines']))
P()
# --- (f) momentum controls pivot
P('### 11.7 MOM-1 (R-03 on KRX momentum) and MOM-2')
P()
sub=GV[(GV.card_or_rule=='MOM-1 R-03 own-vol scaling on KRX momentum sleeves')&GV.quantity.str.contains(': Sharpe$',regex=True)].copy()
sub['cell']=sub.quantity.str.replace(': Sharpe','',regex=False)
rows=[]
for cell,x in sub.groupby('cell',sort=False):
    u=[]; full=x[x.period.str.startswith('full')]; rec=x[x.period.str.startswith('2016')]
    rows.append([cell,cellv(u,full.iloc[0]) if len(full) else '-',cellv(u,rec.iloc[0]) if len(rec) else '-',ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P('KRX 12-1 momentum, ALL quintiles, net 35 Sharpe:')
P()
P(table(rows,['Sleeve and control','1996-04..2026-09','2016-01..2026-09','GV ids','Source lines']))
P()
rest=GV[GV.card_or_rule.isin(['MOM-1 R-03 own-vol scaling on KRX momentum sleeves','MOM-2 Daniel-Moskowitz gate (spec book only)'])&~GV.gv_id.isin(shown)]
P(table([[r['gv_id'],r['quantity'],r['market'],r['period'],r['gross_net'],r['value'],r['source_file'],r['line']] for _,r in rest.iterrows()],['GV','Quantity','Market','Period','Gross/net','Value','Source file','Line']))
shown|=set(rest.gv_id)
P()
# --- (g) VT20 reproduction pivot
P('### 11.8 IDX-1 KOSPI VT20: reproduction of the macro spec\'s golden values (rebuilt KOSPI 2016-01-04..2026-09-29; values are fractions as printed in the file; gross unless the quantity says net)')
P()
sub=GV[GV.card_or_rule=='IDX-1 KOSPI VT20 (macro R-06) reproduction'].copy()
win=sub[sub.quantity.str.startswith('window ')].copy(); oth=sub[~sub.quantity.str.startswith('window ')]
P(table([[r['gv_id'],r['quantity'],r['value'],r['line'],r['note']] for _,r in oth.iterrows()],['GV','Quantity','Value','Line (r2_idx_golden_values.csv)','Check against the spec']))
shown|=set(oth.gv_id)
P()
win['w']=win.quantity.str.extract(r'^window (.*): ')[0]; win['s']=win.quantity.str.extract(r': (.*)$')[0]
rows=[]
for w,x in win.groupby('w',sort=False):
    u=[]; a=x[x.s=='VT20']; b=x[x.s=='buy-and-hold']
    rows.append([w,cellv(u,a.iloc[0]) if len(a) else '-',cellv(u,b.iloc[0]) if len(b) else '-',ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P(table(rows,['Window','VT20','Buy-and-hold','GV ids','Source lines']))
P()
# --- (h) stops pivot
sub=GV[GV.card_or_rule=='INV-5 no name-level stops (evidence)'].copy()
sub['w']=sub.quantity.str.extract(r'deciles (EW|VW) ')[0]; sub['v']=sub.quantity.str.extract(r'deciles (?:EW|VW) (.*): Sharpe')[0]
vs=list(dict.fromkeys(sub.v)); rows=[]
for w,x in sub.groupby('w'):
    u=[]; vals=[]
    for v in vs:
        y=x[x.v==v]; vals.append(cellv(u,y.iloc[0]) if len(y)==1 else '-')
    rows.append([w]+vals+[ids_compact([r['gv_id'] for r in u]),lines_of(u)])
P('### 11.9 INV-5 evidence: name-level stops on KRX top-500 12-1 deciles (2000-01..2026-09, net 35 Sharpe)')
P()
P(table(rows,['Weighting']+vs+['GV ids','Source lines']))
P()
# --- (i) row-wise groups
def sel(card, qre=None):
    m=(GV.card_or_rule==card)
    if qre: m&=GV.quantity.str.contains(qre,regex=True)
    return GV[m]
SEL=[
 ('11.10 INV-1 / INV-2 execution invariants (KRX)',[('INV-2 limit-lock rule',None),('INV-1/INV-2 close fills and limit-lock rule',None)]),
 ('11.11 DATA-2, DATA-3 and the rebuilt-KOSPI check',[('DATA-2 corporate-action-adjusted returns',None),('DATA-3 month-end data rule (no Shiller averages)',None),('DATA rebuilt KOSPI check',None)]),
 ('11.12 DATA-5 regime flags',[('DATA-5 Korean regime and event flags',None)]),
 ('11.13 FS-2 constrained KRX momentum (FORWARD-SIM)',[('FS-2 constrained KRX momentum card',None)]),
 ('11.14 Index crash window 2026-06-22..07-30',[('IDX crash window',None)]),
 ('11.15 GOV-3 attribution, GOV-4 / GOV-5 gate harness, GOV-7 break-even screen',[('GOV-3 attribution block (low-vol example)',None),('GOV-3 attribution block (SML check)',None),('GOV-4 block length max(10, PW) for steps 2 and 5',None),('GOV-5 gate power and size',None),('GOV-7 break-even pre-gate screen',None)]),
 ('11.16 R1 KRX engine regression (reference values the rebuilt engine must reproduce)',[('R1 KRX panel regression (engine check)',None)]),
 ('11.17 DROP evidence kept as regression values (KRX reversal) and CRY-1',[('DNB-4 KRX stock-level short-term reversal (evidence)',None),('CRY-1 card C3 (keep PASS)',None)]),
 ('11.18 Chair verification references',[('verification log reference',None)]),
]
for title,rules in SEL:
    sub=pd.concat([sel(c,q) for c,q in rules]).drop_duplicates('gv_id')
    sub=sub[~sub.gv_id.isin(shown)]
    if len(sub)==0: continue
    shown|=set(sub.gv_id)
    P('### '+title); P()
    rows=[[r['gv_id'],r['quantity'],r['market'],r['period'],r['gross_net'],r['value'],r['source_file'],r['line'],r['status']] for _,r in sub.iterrows()]
    P(table(rows,['GV','Quantity','Market','Period','Gross/net','Value','Source file','Line','Status']))
    P()
nt=GV[GV.status=='not traced']
P('### 11.19 Values that could not be traced')
P()
P(table([[r['gv_id'],r['card_or_rule'],r['quantity'],r['note']] for _,r in nt.iterrows()],['GV','Item','Quantity','Why not traced']))
shown|=set(nt.gv_id)
P()
P(f'Shown above: {len(shown)} of {ngv}. Items without a numeric golden value: ML-1 (structural test: signs fixed in the header, equal weights, z-scores cross-sectional), DATA-4 (structural: rcept_dt + 1 availability, first-filed values), DATA-6 (logging), FS-4 and FS-5 (no lab test; their settling tests define the first golden values).')
P()
# ------------------------------------------------------------------ 12 corrected anchors
P('## 12. Corrected anchors (numbers that must not propagate)')
P()
CA=[
('CA-01','Korean 1-month reversal "-2.95%/month (t -3.77)" (context brief; macro anchors; E7-C17)','A Fama-MacBeth slope on r(-1), Jan-1999..Feb-2021: about -0.30% next month per +10% last month, not a spread. Implementable spreads: EW quintiles 0.52%/month gross (2001-26), 0.08% (2020-26), negative net; KRX EW deciles 1999-2021 +1.41%/month gross, +0.20% net 35 (R1); VW ex-microcap deciles 1996-04..2026-09 +0.57%/month gross (t 0.9), -0.68% net 35','Sim and Kim (2021) JDQS 29(3); prof_v01; r2_kr_reversal.csv lines 17/22; R2_PROF PR-T-02, R2_EXEC ER-T-07'),
('CA-02','Korean momentum "-6.13%/month in high-turnover stocks" (context brief; KJFS)','Not reproduced: +0.78 (t 2.57) / +1.22 (t 3.26) (prof chair), +0.58 / +1.42 (P6), +1.44 (t 3.41, R1 high-turnover tercile), +1.43%/month (t 3.26) all caps and +1.66% (t 4.50) ex-bottom-20% (KRX 2000-07..2019-06, gross, adjusted returns); the sign appears only with unadjusted closes (-11.37%/month, t -5.42). The long-only high-turnover winner leg does lag: -11.57%/yr vs EW, net 35, 1996-2026 (t -4.18)','e-kjfs.org; prof_v02; r2_kr_mom_claims_long.csv lines 15/7/183/175/51/43; r2_kr_mom_grid_long.csv line 2856'),
('CA-03','KR-ISS long-only net information ratio 0.84 (P3)','0.48-0.54 full sample net 35 (1996-06..2026-09); 0.35-0.38 in 2017-26; about 0 at 70 bp in 2017-26','prof_v03 (prof_verification_log.csv line 48)'),
('CA-04','Ilmanen et al. per-factor out-of-sample haircuts value -49%, momentum -23%, multifactor -18% (macro R-15, section 7 prior_haircuts, section 13 N-60)','Only an average 30% out-of-sample drop is verifiable; use planning haircuts 0.5 / 0.3 / 0.75 and measured local decay (GOV-8)','AQR article page; V107 UNVERIFIABLE; R2_PROF PR-T-13'),
('CA-05','Average anomaly "8 bp/month net"','4 bp/month (204 anomalies)','Chen and Velikov, JFQA 2023 abstract; R2_PROF PR-T-12'),
('CA-06','Step-8 false pass "36-38% at 8-10 years" (P4)','23.8% (KOSPI bootstrap), 29.5% (iid), 31.2% (sign-flip) at true Sharpe 0 over 10 years; the joint false-pass rate of steps 2+3+5+8 is 0.5%','r2_idx_gate_sim.csv lines 524/6244/3384/539'),
('CA-07','"18 OOS years for Sharpe 0.4" (P1); "IR 0.3 needs 18 years" (E4)','About the 50%-power horizon: Sharpe 0.4 reaches 50% power at step 2 after 15.8 years and 80% after 40.3; step 5 needs about 50 years for 80%','r2_idx_gate_power_years.csv line 363; R2_EXEC A22'),
('CA-08','Jeon-Byun "max drawdown -23.7% vs -74.1%"','Worst monthly returns (-23.66% vs -74.06%), not drawdowns','Marquette e-Publications; R2_PROF PR-T-10'),
('CA-09','P4 "SE 0.188" (Sharpe 1.5, 60 months)','Annualised SE about 0.47','Lo (2002) formula; R2_PROF PR-T-15'),
('CA-10','Volume-filtered weekly reversal 0.44%/week (P2), 0.03%/week (P6)','Design-dependent -0.05 to +0.31%/week gross (2001-26); 0.14-0.26%/week in the top 500 (1996-2026); always negative net (-0.92 to -1.33%/week net 35)','prof_v04_weekly_reversal.csv; R2_PROF PR-T-03'),
('CA-11','Corwin-Schultz KRX spreads 39-79 bp (P6)','22-57 bp (cap buckets) or 99-117 bp (negatives zeroed first), Jan-2024..Sep-2026; not a calibration source','prof_v07, prof_v07b (V096 MISMATCH)'),
('CA-12','"Samsung + SK hynix = 55.5% of KOSPI" (undated; macro R-07 text) and "22% at end-2023" (KEIA)','Always give date and denominator. CR-07 definition: 53.71% (2026-09-29), 59.69% peak (2026-06-25), 29.29% (2023-12-28). Alternatives on 2026-09-29: 50.82% (common lines / all lines), 52.59% (common / common), 53.96% (incl. preferred / common + preferred). End-2023: 26.88% / 27.79%, not 22%. MSCI Korea (free float, Aug-2026) 60.8%','r3_pair_share.csv lines 2/7/9; R2_EXEC A4-A5; P1-C27'),
('CA-13','Korea 52-week high "+0.34%/month net (t 2.31)"','+0.33%/month (t 2.14) from 2001-03; +0.13%/month (t 0.81) from 1996-03 (EW top quintile minus EW universe, net 35); state the start date','KR lab daily series; R2_PROF PX-T-03'),
('CA-14','Korea 12-7 momentum "net-of-35-bp Sharpe 0.54"','0.60 (deciles, from 2001), 0.19-0.20 (from 1996; EW quintiles 0.20), -0.01 in 2016-26; negative at 70 bp after 2010','prof_v02; r2_kr_mom_grid_long.csv lines 6144/6194'),
('CA-15','CAPE 1-year out-of-sample R2 "-2.4% (1950-) / -11.1% (1990-)"','-4.8% / -16.5% (prof chair), -4% / -18% (US lab); all negative','prof_v06; us/results/us_A4_valuation.csv'),
('CA-16','P6 value-weighted low-risk tilt "-20.3 points in 2025"','Single-signal VW top quintiles lost 35-40 points in 2025','KR lab daily series; R2_PROF section 3'),
('CA-17','"US 12-1 momentum Sharpe 0.02 since 2008" (context brief)','-0.16 for 2008..2017-03 (French WML; local file ends 2017-03); not verifiable to 2026 here','us/results/us_C_factors.csv'),
('CA-18','"ChatGPT strategy unprofitable at 20 bp"','20 bp round trip (10 bp per side)','Lopez-Lira and Tang, arXiv v6'),
('CA-19','"Trend following 2010-18: 0.4%/yr"','Excess over T-bills (AQR 2019, Exhibit 1); total return 1.6%/yr. Do not swap the two','AQR 2019'),
('CA-20','Dynamic momentum "roughly quadruples" Sharpe (E1-C16)','"Approximately doubles": JFE Table 7 0.682 -> 1.041 -> 1.194; static WML 0.71','NBER w20439; R2_EXEC ER-T-01, A1'),
('CA-21','Step 9 as "x 0.4" (two panelists; R2 KR gate column g9 prints 0.4 x diff, e.g. B1/F4 +1.23%/yr)','Expected live Sharpe = 0.6 x OOS ("take 40% off"); E1 F1 prior 0.13 before the gate; E4 composite live IR 0.18-0.30; B1/F4 at 0.6 x 3.08% = +1.85%/yr (arithmetic)','macro section 8.1; r2_kr_excl_gate.csv line 2; R2_EXEC A2'),
('CA-22','KOSPI 24-month return "+235%" on 2026-06-22','+227% (daily) / +222% (month-end)','exec chair c02; R2_EXEC A10'),
('CA-23','KOSPI on 2025-03-31 "-2.93%"','-3.00%','exec_verification_log.csv row 78'),
('CA-24','MTUM IT weight "54.3%" (2026-06-30 factsheet)','53.22%; 54.3% is the 2026-09-29 page','iShares; R2_EXEC A12'),
('CA-25','Korean top-500 12-1 WML Sharpe 0.43 EW (E5)','EW 0.26-0.30 gross / 0.04-0.07 net 35 (deciles, 2000-26); VW 0.44-0.48 / 0.28-0.30; 2016-26 EW net -0.13, VW 0.30 (0.02 with a 5% cap); July 2026 -30.0% EW / -29.8% VW','exec chair c05; R2 KR; R2_EXEC A7, ER-T-06'),
('CA-26','Bounding trend to [0.5, 1] "keeps about half the protection" (E3-C23)','PC-1 vs own S rises: +11.3 pp (unbounded x VT20) -> +13.0 (0.5+0.5x) / +15.4 (clip); absolute max DD -27.7% -> -36.2% / -29.4% (KOSPI 1996-09..2026-09, net 3 bp)','r2_idx_overlay_vs_sleeve.csv lines 11-13; R2_EXEC ER-T-02, A8'),
('CA-27','The Daniel-Moskowitz gate protects Korean momentum crashes','3 onsets since 2000 (2001-01-04, 2008-10-31, 2020-03-20), on 4.1% of days; 9 onsets 1996-2026 (9.8% of days), mostly 1997-99; off on 2026-06-22','r2_kr_dm_gate_onsets.csv lines 2-10; R2_EXEC A20'),
('CA-28','Insider buys "82 bp/month" as a long-only 126-day overlay','Long-short (buys minus sells), one-month hold, five-factor alpha: 82 bp VW (t 2.15) / 180 bp EW (t 6.07), 1986-2007','NBER w16454; R2_EXEC A6, ER-T-04'),
('CA-29','GS high-beta momentum basket "-37% in July 2026"','Unverified; only "worst month since November 2000" is verifiable','Yahoo/Bloomberg; R2_EXEC ER-T-09, A15'),
('CA-30','KOSPI crash 2026-06-22..07-30 "-38.0%"','-38.61% (rebuilt index and official levels)','r2_idx_windows.csv line 3; R2_EXEC A16'),
('CA-31','Korean low-turnover momentum long-only excess "+2.9%"','+2.9% (E7 universe, 2015-24), -0.1% (ALL, 2015-24), +9.69%/yr (t 2.77; ALL, 1996-2026, net 35); high-turnover winners -11.57%/yr (t -4.18)','r2_kr_mom_grid_long.csv lines 1120/2856; R2_EXEC A13'),
('CA-32','"Korean low volatility is a crash hedge" (E7-C20; professors\' protective 2)','Beta 0.63 (EW) / 0.74 (VW); against S_beta max DD worse by 7.1-22.4 pp and tail ratio 0.97-0.99 (KRX 1996-2026, net 35)','c12_lowvol_samebeta.csv lines 2/6/10; R2_EXEC A14'),
('CA-33','KOSPI trend protection read as a full-sample property','Concentrated in 1997-2001: the multi-speed sleeve is REJECT from 2011 and 2016 starts (PC-1 -3.5 / -2.9 pp); VT20 alone passes from every start 1996-2006 (PC-1 +4.4 to +11.6 pp)','r2_idx_start_date_sensitivity.csv; R2_EXEC A21'),
('CA-34','Nominal sizes of gate steps 2 and 5 with 10-session blocks','Step 2 false pass 6.9-8.0% (nominal 5%); step 5 12.8-13.7% (nominal 10%), KOSPI-like returns','r2_idx_gate_sim.csv lines 522/616/1396; R2_EXEC A22'),
('CA-35','Vol-scaled sizing adds "+0.1 to +0.3 Sharpe on nearly every strategy" (prior design)','Robust only for momentum: Korean reversal EW net -0.29 -> -0.59 when scaled; KOSPI VT20 long-only 0.38 vs S 0.40','R2_EXEC ER-T-10; R2_PROF PR-T-16'),
('CA-36','AQMIX as evidence of a 1.2-Sharpe trend book','10-year return 5.44% vs T-bills 2.42%, volatility 9.96%: Sharpe about 0.30','R2_EXEC A18 (E1-C05 check)'),
('CA-37','KRX limit-up event return "-308 bp" (chair first pass)','The chair\'s own benchmark error; E7\'s -394 / -579 bp (t+5 / t+20) stand','exec_verification_log.csv rows 82-86; R2_EXEC A19'),
('CA-38','US single-index trend weight 3 (prior; macro R-14)','At 50 bp all multi-speed cells REJECT (PC-1 -10.7 pp); at 5 bp INSUFFICIENT DATA (PC-1 +14.7 pp, 53-56% of the benefit from the GFC)','r2_idx_protective_scorecard.csv lines 10/17; R2_EXEC A9'),
]
P(table(CA,['ID','Number in circulation (where)','Correct value or reading (market, period, gross/net)','Source']))
P()
# ------------------------------------------------------------------ 13 cross-spec
P('## 13. Cross-spec amendments for the macro spec owner')
P()
P('Types: Supersession (this programme owns signal-family weights; owner confirms), Correction (a number or wording in the spec is wrong), Proposal (answers an open point), Tightening (gate change allowed by CR-08), Clarification, Information, Conflict (owner decides).')
P()
XS=[
('XS-01','Section 2.2 KEEP Korea flow 3; R-15 flow prior','Korea investor flow 3 -> 1: log final investor-type flows with timestamps now (DATA-6); no direction rule; t-1 history required before an open-leg test. Foreigners sold KRW148.3tn net in H1-2026 while KOSPI rose about 101% (R2_EXEC EC-T-23)','CR-03; TF-39, TF-40','Supersession'),
('XS-02','R-15 Korea ST reversal 3 and section 2.2 KEEP 3 ("Korea keeps 1-5-day reversal")','3 -> 0 for daily/weekly reversal; monthly reversal only as a conditioning guard of weight 1 (FS-5). The required net-of-cost test fails: weekly L/S net-35 Sharpe -1.78 (KRX ALL EW 1996-2026; kr_key_numbers.csv line 30), break-even 12.5 bp per side; 1-month VW ex-microcap deciles -0.68%/month net 35 (1996-04..2026-09; r2_kr_reversal.csv line 22). Delete the 1-5-day sentence','CR-03; TF-41, TF-42','Supersession'),
('XS-03','Section 2.2 volume-spike reversal "KEEP as signal spec; UNTESTED"','DROP: volume-filtered weekly reversal -0.05 to +0.31%/week gross (2001-26), -0.92 to -1.33%/week net 35 (prof_v04); volume-spike buying -43 / -93 bp at t+5 / t+20 (KRX 2015-06..2026-09, gross; exec row 83)','TF-41, TF-61; R2_PROF PR-T-03','Proposal'),
('XS-04','R-05 (reversal and quality held at 1.0x; reversal card must clear 35 bp and stay positive at 70 bp)','Record that the reversal family fails its own test (XS-02); the 1.0x convention stays for any future reversal sleeve on a venue of 5 bp or less (BACKLOG DC-E2-09); vol scaling hurts reversal (KR STR EW net -0.29 -> -0.59)','TF-41, TF-22','Information'),
('XS-05','R-15 prior calibration; section 7 YAML prior_haircuts; section 13 N-60 ("use these values and no others")','Replace the per-factor Ilmanen haircuts (unverifiable; only a 30% average drop is published) with one haircut per stage: planning 0.5 in sample, 0.3 post-publication, 0.75 drift-like, replaced by measured local decay where 20+ years exist (GOV-8); withdraw N-60','R2_PROF PR-T-13; TF-56, TF-57; CA-04','Correction'),
('XS-06','R-07 evidence text "55.5% of KOSPI (22% at end-2023)"','Dated, denominated values: 53.71% on 2026-09-29 and 29.29% on 2023-12-28 under CR-07; end-2023 alternatives 26.88% / 27.79%, not 22%','CA-12; r3_pair_share.csv','Correction'),
('XS-07','R-07 pair-share denominator (undefined)','CR-07 definition (005930 + 005935 + 000660 over all KOSPI lines in the KRX daily file): 53.71% on 2026-09-29; first above 0.45 on 2026-05-06 (0.4702); 99 of 181 sessions above 0.45 in 2026; peak 59.69% on 2026-06-25; alternatives 50.82% / 52.59% / 53.96% on 2026-09-29','CR-07; TF-26; section 11.1','Proposal'),
('XS-08','R-07 ladder open points (cumulative steps; re-arm reference)','Steps non-cumulative; total book NAV only (never per sleeve); re-arm at 0.5 with the reference peak reset (never the all-time high-water mark); thresholds unchanged. Evidence: KOSPI CW 2000-26 net 35, reset with 0.5 re-arm: Sharpe 0.42 -> 0.40, max DD -55.8% -> -41.3%, 0.69 halts/yr; all-time-peak reference 22.8 halts/yr and Sharpe -1.65; per-sleeve ladder on vol-scaled VW WML 0.38 -> 0.16 (exec rows 58-61)','CR-07; TF-27','Proposal'),
('XS-09','R-14 TS trend sleeve (CARD-O vs EW basket; 12-1 sign monthly; US weight 3)','Add a CARD-P cell (single-index trend judged on PC-1..PC-7 vs S; never CARD-O) and a speed cell (KOSPI 3 bp: 12-month sign PC-1 +4.7 pp, INSUFFICIENT DATA, vs multi-speed +8.9 pp, PASS; r2_idx_protective_scorecard.csv lines 4/3). US single-index trend: protective 0 at 50 bp (REJECT, PC-1 -10.7 pp, line 10), 1 at futures cost (BACKLOG)','CR-02; TF-30, TF-34','Proposal'),
('XS-10','R-03 scope','State that R-03 applies to every momentum sleeve in every market, KRX stock sleeves included, as a risk control and not a return claim; on KRX it lowered 2016-26 Sharpe (EW L/S -0.20 -> -0.24, VW 0.32 -> 0.23; r2_kr_crash_controls.csv lines 70/184/526/640)','CR-05; TF-22','Clarification'),
('XS-11','Section 8.5 blocks (macro cards only) vs section 8.1 step 2 (10-session blocks)','max(10, Politis-White on d and d^2) for steps 2 and 5 on every card; 10-session blocks gave false passes of 8.0% at nominal 5% (step 2, 10 years) and 13.7% at nominal 10% (step 5) on KOSPI-like returns (r2_idx_gate_sim.csv lines 522/616)','CR-08; TF-53','Tightening'),
('XS-12','Section 8.7 CARD-P comparator ("applies only to rules whose output never exceeds 1.0")','Add S_beta = beta_hat x market + (1 - beta_hat) x cash, beta_hat pre-registered, as the CARD-P comparator for stock-level sleeves (estimation window: OQ-03)','CR-01; TF-59','Proposal'),
('XS-13','Section 8.1 step-9 wording; context brief "60% live haircut"','One wording: expected live Sharpe = 0.6 x OOS ("take 40% off"); fix harness prints that use 0.4 x (R2 KR g9 column: B1/F4 +1.23%/yr printed, +1.85%/yr intended)','CR-08; TF-55; CA-21','Correction'),
('XS-14','R-08 market stress gauges','Do not count R-08 as factor-crash protection: VIX was 12.9-25.8 at 19 factor-crash onsets (exec rows 8, 69)','TF-25','Information'),
('XS-15','R-04 Daniel-Moskowitz gate scope','Specification book only; no extension to earnings-momentum or revision sleeves; on KOSPI 9 onsets in 1996-2026 and off on 2026-06-22 (r2_kr_dm_gate_onsets.csv)','CR-05; TF-23','Information'),
('XS-16','R-15 US XS momentum ("2 if vol-scaled + D-M, else 1")','This programme\'s final weight is 1 (professors 1, executives 2, rule W3; no US stock sleeve at 50 bp; French WML Sharpe -0.16 in 2008..2017-03)','TF-29','Conflict (OQ-06)'),
('XS-17','R-15 crypto ST reversal 2','2 -> 0 (short-horizon crypto evidence is momentum)','CR-10; TF-68','Supersession'),
('XS-18','R-15 Korea 12-7 / residual momentum 1 (UNVERIFIED)','Replace with the constrained momentum card FS-2 (weight 1, FORWARD-SIM: Q5 12-1 or 12-7 excluding lottery/highest-turnover names, R-03, 5% cap, long-only). 12-7 L/S EW net-35 Sharpe 0.20 (1996-2026) and -0.01 (2016-26) (r2_kr_mom_grid_long.csv lines 6144/6194); residual momentum untested','CR-05; TF-21','Supersession'),
('XS-19','Section 10 DO-NOT-BUILD (items 1-26)','Add DNB-TF-01..17 (section 6). Overlaps: DNB-TF-06 repeats item 14 (flow direction); DNB-TF-11 matches item 26 (value timing presented as compliant); DNB-TF-14/15 extend item 11. Clarify item 13: the aggregate issuance-timing ban does not cover the firm-level dilution exclusion screen SCR-2','CR-06, CR-11, CR-12','Proposal'),
('XS-20','R-06 Korea card evidence (indicative INSUFFICIENT DATA on the 2016-26 card)','R2: PASS on 1996-09..2026-09 (PC-1 +6.5 pp, tail 0.70) and from every start 1996-2006; INSUFFICIENT from 2011/2016; the spec\'s 2016-26 golden values reproduce (r2_idx_golden_values.csv). Owner declares the judged history (OQ-07)','TF-31','Information'),
('XS-21','R-15 0-3 normalisation into base_weight (open point)','base_weight = w / 3 (weight 3 = 1.0x; never above 1.0); one-sided (*) cells cannot feed any book until a card passes','Weight rules W1-W5','Proposal'),
('XS-22','R-07 caps: 0.05 single name vs 0.35 pair (open point)','By book type: 0.05 single name in selection sleeves (VW legs capped at 5% of the leg); 0.35 pair cap on look-through for market and ETF books when the pair share exceeds 0.45; semis <= 0.50. Pair cap on KOSPI CW cost -15.0 pp in the H1-2026 melt-up, saved +4.6 pp in the crash, -2.2 pp 2026 YTD (exec chair c07)','CR-07; TF-26','Proposal'),
]
P(table(XS,['ID','Macro item','Proposed change and evidence','Basis','Type']))
P()
# ------------------------------------------------------------------ 14 open questions
P('## 14. Open questions for the owner')
P()
OQ=[
('OQ-01','Ladder threshold units (CR-07): keep fixed -8 / -12 / -15%, move to book-volatility units (-1.0 / -1.5 / -1.9 sigma), or declare a book-vol ceiling of 8% at which the two coincide? Evidence: Brownian check at Sharpe 0.5, P(-15% within 10 years) = 0.97 at 12% book vol and 0.66 at 8% (exec row 62); E5\'s sigma ladder on KOSPI VT20 (Sharpe 0.40, max DD -37.4%, 1 halt) was not re-run. Suggested: FORWARD-SIM both conventions.'),
('OQ-02','Confirm the CR-07 pair-share denominator (preferred line in the numerator, all KOSPI lines in the denominator). The cap first binds on 2026-05-06 under CR-07 and on 2026-05-07 under the common-over-all-lines definition.'),
('OQ-03','S_beta beta_hat: which window? Proposal: OLS beta of daily returns on the declared market over the prior 252 sessions, frozen in the card header at each formation; a full-period beta only as a descriptive check (the c12 check used full-period monthly OLS betas of 0.631-0.742; exec_chair_checks/c12_lowvol_samebeta.py).'),
('OQ-04','Step 8 stays (CR-08). Add the professors\' "positive in at least 2 of 3 sub-periods" and a short-sale-regime split as extra checks (both tighten)?'),
('OQ-05','The professors\' Jensen-alpha step-5 variant was not adopted because for beta < 1 cards it can loosen step 5. Print it as a report line only?'),
('OQ-06','US stock momentum prior: 1 (this programme) or macro R-15\'s "2 if vol-scaled + D-M"?'),
('OQ-07','R-06 Korea card: judge it on the rebuilt KOSPI from 1996-09 (PASS) or from 2016-01 (INSUFFICIENT DATA)?'),
('OQ-08','Build order of the data stores: OpenDART PIT (unblocks KR-VQ, drift, value and quality), FMP/EDGAR PIT (US-VQ, insiders, IPO screen), KIS quote snapshots (cost buckets, impact), t-1 investor flows (open-leg test).'),
('OQ-09','Crypto C3 prior weight 2 (macro R-15, executives) or 3 (prior design, professors)? The card\'s own PASS governs the card; only base_weight changes.'),
('OQ-10','Tiered t-hurdles (professors only): Tier A t >= 2.0, new signals t >= 3.0 plus SPA, > 100 configurations or TradingView-sourced t >= 3.4-3.8. Adopt as a tightening?'),
('OQ-11','Statistical review triggers (executives only): a forward drawdown beyond the 95th simulated percentile, or a 12-month Sharpe below its 90% CI, triggers a review and never an automatic liquidation. Adopt as a governance option?'),
('OQ-12','CR-06 adopted only "never enter at a locked limit-up close". Add the executives\' five-session no-new-long window after locked limit-ups or volume spikes once BL-TF-02 tests it?'),
('OQ-13','KOSDAQ trend: keep macro R-14\'s 0 until a KOSDAQ index rebuild and test exist (executives proposed protective 1, untested)?'),
('OQ-14','SCR-1 primary definition: the F4 10% cut (best IR 1.53, smallest exclusion) or F1 highest-turnover quintile (larger mean, +4.28%/yr net 35 on B1, IR 1.15)? Run SCR-1 and SCR-2 as two cards or one combined screen (flag overlap Jaccard 0.13)?'),
('OQ-15','Threshold for the attribution block\'s "factor tilt" label. Proposal: Newey-West alpha t below 2.0 after attribution.'),
]
for k,v in OQ: P(f'- **{k}** {v}')
P()
# ------------------------------------------------------------------ 15 gaps
P('## 15. Gaps')
P()
gaps=[
'No point-in-time fundamentals locally (OpenDART, FMP/EDGAR): KR-VQ, US-VQ, Korean drift, value and quality weights, insiders and the IPO screen are untested.',
'No KIS quote history: half-spreads, impact and capacity are unmeasured; the flat 35 / 70 bp per side is used throughout.',
'No t-1 investor-flow history; no local crypto, futures or US single-stock panels (C3 controls, CTREND-lite, diversified futures trend, US stock cards and US low-vol vs S_beta are untested).',
'KRX lab returns are price returns without dividends and Sharpe ratios use rf = 0; low-vol, value and low-beta results are understated by roughly 1-2%/yr.',
'No price-impact model in the R2 races; capacity is a rule (<= 1-2% of ADV20), not a measurement.',
'All lab verdicts are in sample on 1996-2026; the contamination log treats the historical holdout as used for every family discussed, so FORWARD-SIM incubation from 2026-10-01 is the clean test.',
'The floored trend x VT20 cell has no plateau (PC-6) or start-date sweep; only the unbounded product was swept.',
'No local test of the L0 composite or the ridge challenger; 52-week-high-neutral and capped momentum crash tests were not run on KRX.',
'The gate-size simulation covers steps 2, 3, 5 and 8; steps 1, 4 and 7 and CPCV are untested.',
'E5\'s sigma-ladder and SPY cumulative-step results were not re-run (scripts not saved).',
'The R2 KR gate harness prints step 9 as 0.4 x diff (spec: 0.6 x OOS).',
'fp / fe count member claims only; 94 professor claims and part of the executive ledger remain unverified by the chairs; India was not reviewed by either panel and other markets are CONTEXT only.',
'"US 12-1 momentum Sharpe 0.02 since 2008" cannot be checked past 2017-03 with the local French file.',
]
for g in gaps: P('- '+g)
P()
# ------------------------------------------------------------------ appendices
P('## Appendix A. Node index (all 70 nodes; propositions are in sections 5-7)')
P()
rows=[[r['node_id'],r['theme'].split('. ')[0],r['cls'],r['fp'],r['fe'],r['ps'],r['es'],r['data'],r['destination'],r['decision']] for _,r in N.iterrows()]
P(table(rows,['Node','Theme','Class','fp','fe','Professors','Executives','Data','Destination','Decision']))
P()
P('Per-node claim IDs, chair items, propositions, URLs and settling tests are in `R3_TF_nodes.csv` (columns prof_claims, exec_claims, prof_chair_items, exec_chair_items, prof_props, exec_props, urls, settling_test).')
P()
P('## Appendix B. Edges')
P()
ec=E['type'].value_counts().to_dict()
P(f"{len(E)} edges: "+', '.join(f"{k} {v}" for k,v in ec.items())+'. Refutes and conflicts edges:')
P()
sub=E[E['type'].isin(['refutes','conflicts'])]
P(table([[r.edge_id,r.source,r.target,r['type'],r.reason] for _,r in sub.iterrows()],['Edge','From','To','Type','Reason']))
P()
P('All supports and qualifies edges are in `R3_TF_edges.csv`.')
P()
open(OUT,'w',encoding='utf-8').write('\n'.join(L)+'\n')
print('wrote',OUT,len('\n'.join(L)),'chars;',len(L),'lines')
