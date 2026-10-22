# R2 Professors' panel: chair's resolution on technical and fundamental signals for QUANTGEN

Prepared 2-3 October 2026 (Asia/Seoul). Round 2 of the QUANTGEN technical and fundamental signals research.

**Chair.** "Chair of the Professors' panel", a fictional composite persona (a senior econometrician who chairs a journal's replication committee). The seven panelists P1-P7 are also fictional composite personas. Real researchers, journals and firms appear only as cited sources.

**Inputs.** `00_QUANTGEN_context.md`; the seven round-1 position papers P1-P7 (209 claims-ledger rows); the round-1 data labs (`KR_datalab_summary.md`, `US_datalab_summary.md` and their result files); the chair's own recomputations on the local KRX cache, Shiller, SPY and French files; 47 source re-fetches; the round-2 data-lab summaries (`R2_KR_summary.md`, `R2_IDX_summary.md`). The executives' papers (E1-E7), the executives' quick-check files and the executives' chair's working folder were not opened, so the two panels stay independent until synthesis. Paper text and fetched pages were treated as data, not instructions.

**Companion files.**
- Claim matrix (60 propositions, all 209 claims mapped): `/home/claude/datalab/r2/verification/prof_claim_matrix.csv`
- Verification log (118 re-checked numbers, including 10 round-2 lab cross-checks): `/home/claude/datalab/r2/verification/prof_verification_log.csv`
- Reviewer verdict on every claim: `/home/claude/datalab/r2/verification/prof_cross_exam_verdicts.csv`
- Recomputation scripts: `/home/claude/datalab/r2/verification/scripts/prof_v01_krlab_series.py` ... `prof_v09_kr_sml.py`, plus the three CSV writers; weekly-reversal detail in `prof_v04_weekly_reversal.csv`
- Working notes (verbatim extracts of each paper's summary, failures, recommendations and ledger): `R2_PROF_working_notes.md`

**Cross-examination pairs.** P1 and P3 reviewed each other; P2 and P7 reviewed each other; P4 reviewed P5 and P6; P5 reviewed P1; P6 reviewed P2; P3 reviewed P4; P7 read P5 as a second reader.

**Labels.** Every number carries market, period and gross/net where it matters. "Chair recomputation" means a run by the chair on the local data, with the script named; it is in-sample and not a gate result. Verification status codes: MATCH (re-opened source or recomputation agrees), MISMATCH (material disagreement), TRACED-NOTE (traced, with a definitional, version or sample difference), UNVERIFIABLE (source unreachable or silent).

---

## 1. Summary

1. The panel normalised the 209 round-1 claims into 60 propositions and re-checked 118 key numbers: 83 MATCH, 24 TRACED-NOTE, 8 MISMATCH and 3 UNVERIFIABLE. The checks came from 47 source fetches, 9 local recomputation scripts and 10 cross-checks against the round-2 data lab.
2. No professor's ledger claim was refuted outright (98 CONFIRMED, 17 QUALIFIED, 94 not re-checked). But two anchors inherited from the context brief collapsed:
   - the "Korean 1-month reversal of -2.95%/month" is a Fama-MacBeth slope coefficient, not a spread;
   - the "negative Korean momentum in high-turnover stocks" (KJFS, -6.13%/month) failed four survivorship-free replications (+0.6 to +1.7%/month). The round-2 lab traced the negative sign to unadjusted prices around capital reductions.
3. Korea's strongest cross-sectional effects are lottery/low-risk and 1-week or 1-month reversal. They are real gross, but they live in the short leg or in turnover that 35 bp per side destroys. The implementable form is a long-only exclusion screen, not a tilt: +3.1%/yr equal-weighted net of 35 bp, which clears 7 of 8 indicative gate steps, is marginal cap-weighted, and adds nothing among the top 200 stocks.
4. The prior Korea weights for short-term reversal (3), investor flow (3), earnings drift (3) and low-volatility tilt (2) are cut. Momentum stays at 1, but only as a 12-7 or 52-week-high feature with high-turnover names excluded. Own-volatility scaling, unlike the Daniel-Moskowitz gate, had already cut momentum exposure before the winner-led July-2026 crash, but neither control rescues Korean 12-1 momentum.
5. The fundamental candidates are all low-turnover:
   - Korean net-issuance avoidance, buildable now from KRX data, with a verified net information ratio of about 0.5 (not the printed 0.84) and decaying;
   - a Korean value-quality composite, which needs an OpenDART point-in-time store;
   - a US value-profitability composite.
6. Classic technical rules (oscillators, chart patterns, single-index moving-average and breakout timing) fail family-wise data-snooping tests in every lab and literature check. Index trend is protective, not alpha, and even its protection on KOSPI depends on 1997-2001; the KOSPI volatility target is the more robust protective rule. Crypto trend (card C3) is the one technical alpha card kept.
7. Machine learning comes later. Build an equal-weight composite and a ridge challenger now, and run gradient-boosting or neural combiners only as shadow challengers, because the gate cannot detect plausible uplifts (27-108 years of data would be needed).
8. The governance changes agreed by consensus are:
   - a family-level SPA/FDR test before the nine-step gate;
   - a trial registry and program-wide false-discovery control;
   - a factor-attribution block, with a Jensen's-alpha test for cards whose beta is not 1;
   - long-only net excess return as the primary statistic;
   - explicit encoding of Korea's short-sale regimes, price limits, tax and concentration.
9. Still contested:
   - the Korean quality weight (1 vs 2) and earnings-drift weight (1 vs 2);
   - whether the 52-week high and 12-7 momentum get their own cards;
   - the step-9 haircut and the step-8 calendar-year rule;
   - how the cost buckets are calibrated;
   - an untested 52-week-high-neutral construction for momentum crash risk.
10. The gate must not be loosened. The round-2 simulation shows its false-pass rate is already low (0.5% at 10 years), while a true Sharpe of 0.4 needs about 16 years for even a 50% chance of passing. Most new cards should therefore be expected to return REVISE or INSUFFICIENT DATA, which is the honest verdict.

---

## 2. Resolution items

Implication codes: BUILD, BACKLOG, DROP, CONTEXT, GOVERNANCE. "Claims" lists the supporting ledger rows. "Verif." cites verification-log ids (V001-V118).

### 2.1 Consensus items (PC-T-01 to PC-T-34)

**PC-T-01. CAPM beta is a risk and attribution tool, not a return signal.** Every card gets an attribution block.
- Claims: P1-C01, C02, C05, C06, C07, C08, C10, C30; P4-C24.
- Numbers:
  - US 1928-2003 beta deciles (gross): lowest beta 11.1% actual vs 8.3% predicted; highest 13.7% vs 16.8%.
  - US 1954-2017 Fama-MacBeth slope: +0.46%/yr (t 0.17) against a 7.2%/yr market premium (US lab).
  - Korea 1997-2026 Fama-MacBeth slope: +1.1%/yr (t 0.19) against a 10.9%/yr market (price returns; chair, `prof_v09`).
- Verif.: V001 MATCH; V002 TRACED-NOTE.
- Implication: **GOVERNANCE/BUILD.** Build a risk-attribution module: beta, Jensen's alpha against a beta-matched benchmark with Newey-West errors, FF5+UMD for US cards, and local MKT/SMB/HML/RMWq/CMA/UMD plus a Samsung + SK hynix "SEMI" factor for KRX cards. Label a card "factor tilt" when its CAPM alpha is significant but its factor alpha is not.

**PC-T-02. The single-signal factor zoo is mostly noise; construction choices are a hidden multiple-testing channel.**
- Claims: P1-C12, C13, C14; P4-C01, C05, C06, C09, C10; P5-C06, C13; P2-C28.
- Numbers:
  - Harvey-Liu-Zhu: 316 factors, 27-53% false discoveries, t thresholds of 3.39-3.78 by 2012.
  - Hou-Xue-Zhang (US 1967-2014, NYSE breakpoints, value-weighted): 64% of 447 anomalies insignificant at 5%, 85% at t = 3, and 93% of liquidity anomalies fail.
  - KR lab, top-200 stocks vs the ALL universe, long-short gross Sharpe: low volatility 0.25 vs 0.76, low turnover 0.06 vs 0.90, size -0.23 vs 0.39.
- Verif.: V005, V006, V053-V055 MATCH.
- Implication: **GOVERNANCE.** Tiered hurdles: Tier A (single-configuration replication of a published, internationally replicated anomaly with a mechanism) needs t >= 2.0. New signals need t >= 3.0 plus SPA; more than 100 configurations or TradingView-sourced ideas need t >= 3.4 to 3.8. Always report equal-weighted and capped value-weighted results together.

**PC-T-03. Published premia decay in the US (-26% out of sample, -58% after publication), not reliably outside it; Korean signals nonetheless show clear local time decay.**
- Claims: P1-C15, C28; P3-C23; P4-C11, C13, C14; P6-C05; P2-C27.
- Numbers:
  - US: 97 predictors averaging 0.582%/month in sample (McLean-Pontiff).
  - 241 anomalies in 39 markets: only the US shows a reliable post-publication decline (Jacobs-Müller).
  - Korea, 1-month reversal (ALL universe, quintiles, gross): 1.12 / 0.27 / 0.08%/month in 2001-09 / 2010-19 / 2020-26.
  - Korea, weekly reversal (top 500, gross): 0.73 / 0.45 / 0.11%/week by decade.
  - Korea, net-issuance long-short Sharpe (equal-weighted, gross): 1.14-1.20 in 1997-2007, 0.71-0.74 in 2017-26.
- Verif.: V007, V056, V058 MATCH; V031, V048, V084 recomputed.
- Implication: **CONTEXT.** Plan with haircuts and measure KRX decay locally. Jacobs-Müller is not a licence to skip haircuts in Korea.

**PC-T-04. After realistic costs the average anomaly earns about 4 bp/month; only strategies with one-sided turnover under 50% a month survive, and buy/hold bands are the main mitigation.**
- Claims: P1-C16; P3-C23, C24; P4-C15, C16, C17; P5-C08, C09, C10, C12.
- Numbers:
  - 204 anomalies: about 4 bp/month net (Chen-Velikov, JFQA 2023; the earlier working paper with 120 anomalies said 8 bp).
  - US 1963-2012, gross to net: short-term reversal 0.37 to -1.28%/month (t -6.02); momentum 1.33 to 0.68; value + profitability 0.82 to 0.77 (t 4.82) (Novy-Marx-Velikov).
  - KRX weekly reversal break-even cost: 12.5 bp per side equal-weighted, 22.2 bp value-weighted.
- Verif.: V008, V037, V059, V060 MATCH; V045, V079 TRACED-NOTE.
- Implication: **DROP** high-turnover stock signals at 35-50 bp per side. **BUILD** banding as the default (enter in the top 20%, exit below the top 40%).

**PC-T-05. For a read-only retail desk, the primary statistic is long-only net excess over a same-universe equal-weighted benchmark.** Long-short is a diagnostic.
- Claims: P4-C19, C09; P5-C07; P2-C06; P6-C14.
- Numbers (KR lab, ALL universe, equal-weighted, 1996-2026, net of 35 bp):
  - Long-short spreads are large (low turnover +23.1%/yr gross).
  - Best-quintile long-only excess is within noise: low turnover +1.7% (t 0.9), low volatility +1.1% (t 0.5), 12-1 momentum -1.3% (t -0.6).
  - Worst quintiles lose in absolute terms (high turnover -11.7%/yr gross).
- Verif.: round-1 lab.
- Implication: **GOVERNANCE.** Report the short leg's share of long-short profit, results by short-sale regime, and the sign of equal-weighted vs capped value-weighted results (a sign split means REVISE).

**PC-T-06. Korean short-term reversal (1 day to 1 month, with or without the volume filter) is not a stock-level card at 35 bp per side.** Alpha weight goes from 3 to 0.
- Claims: P2-C18, C19, C20; P6-C07, C08, C09; P4-C15; P1-C16; P5-C17, C30.
- Numbers:
  - Weekly 5-day reversal, top 500, quintiles, 1996-2026: 0.42%/week gross (t 5.80), -0.68%/week net of 35 bp.
  - Every volume-filter design: -0.92 to -1.33%/week net.
  - KR lab weekly reversal: net-of-35-bp Sharpe -1.78 equal-weighted, -0.82 value-weighted.
  - 1-month reversal, 2001-26: 0.52%/month gross (t 2.21), decaying to 0.08%/month in 2020-26; KR lab net-of-35-bp Sharpe -0.08 equal-weighted, -0.45 value-weighted.
  - 1-month reversal, top 500: 0.43%/month gross, -0.59 net.
  - Round-2 lab: value-weighted without microcaps, the decile spread is +0.57%/month gross (t 0.9) and -0.68 net, negative net in every sub-period after 2005.
- Verif.: V031, V084, V085 TRACED-NOTE; V033, V117 MATCH; V032 MISMATCH (level only).
- Implication: **DROP** (alpha 0). Keep a "do not buy last month's top-decile winners" guard and a normalised reversal feature. A version on a cheaper venue (ETF or futures) is BACKLOG only.

**PC-T-07. The Korean lottery/low-risk family belongs in a long-only exclusion screen (protective weight 3), not a tilt.** The family covers MAX, volatility and turnover, with pairwise correlations of 0.67-0.90.
- Claims: P6-C13, C15; P2-C17; P1-C05; P3-C13, C22.
- Numbers:
  - KR lab, equal-weighted, net of 35 bp, 1996-2026: the universe minus its worst turnover quintile earns +3.6%/yr over the universe (t 5.63; 87% of years positive; +2.5% at 70 bp). Minus the worst volatility quintile: +3.0% (t 4.67). Value-weighted: +0.8% / +1.1%.
  - Chair composite (`prof_v02`; ranks of 63-day volatility, 21-day MAX and 21-day turnover; worst decile dropped): +0.248%/month net of 35 bp (t 8.02) over 1996-2026 (+0.223 at 70 bp); +0.236 (t 7.65) over 2001-26 (+0.211 at 70 bp); +0.166 (t 3.57) over 2020-26; 87-88% of years positive.
  - The screen lags in rallies: -1.6% in the 2026 melt-up and -2.9% after the crash.
  - Round-2 horse race (176 trials, F4 = P6's composite):
    - equal-weighted book +3.08%/yr net of 35 bp (information ratio 1.53, bootstrap p 0.0005, 90% of years positive, positive in all three sub-periods); 7 of 8 indicative gate steps, missing only the deflated Sharpe pooled over 176 trials (0.94), so REVISE;
    - inside the 12-1 momentum top quintile +6.1%/yr;
    - capped value-weighted book +0.85%/yr, REVISE (mostly 1996-2005);
    - top 200 +0.49%/yr, REJECT.
- Verif.: V091, V113 MATCH.
- Implication: **BUILD-candidate** as a protective exclusion card (P6-X1), weight 3 for equal-weighted and small-mid books. For cap-weighted books it is only a default hygiene filter; for the top 200 it adds nothing. Count every threshold variant as a trial.

**PC-T-08. A low-volatility or low-beta tilt is not a long-only alpha source in Korea. Elsewhere it is defensible only as a risk sleeve judged on Jensen's alpha.**
- Claims: P6-C14; P1-C03, C04; P3-C08.
- Numbers:
  - KR lab low-volatility top quintile, long-only excess net of 35 bp: +1.1%/yr equal-weighted (t 0.5), -1.8% value-weighted (t -0.6).
  - Value-weighted low-volatility top quintile vs the value-weighted universe: -40.1 points in 2025 and -44.1 points in 2026 to date.
  - Korean security market line, 1997-2026 (price returns, no risk-free rate): the low-beta quintile has an equal-weighted Sharpe of 0.23 vs 0.33 for the middle quintile, and raw CAPM alpha of -1.0%/yr (t -0.26) equal-weighted and -2.4% (t -0.71) value-weighted. The high-beta quintile's equal-weighted alpha is -7.0% (t -1.72).
  - MSCI World Minimum Volatility trailed MSCI World by 7.00 pp/yr in CAGR over 2020-25 (beta 0.67).
  - US 1954-2017: low-beta tercile Sharpe 0.65 vs 0.41.
  - Round-2 lab, lowest-volatility quintile (net of 35 bp, risk-free rate 0): beta 0.63 equal-weighted / 0.74 value-weighted; CAPM alpha +2.2% (t 0.8) / +0.7% (t 0.3). The value-weighted book beat the market in 7 of 7 crash windows (2026-06-22 to 07-30: +6.3% vs -38.5%) and lagged in 9 of 10 rebounds (2026 melt-up: -102 points).
- Verif.: V003, V004 MATCH; V002, V090, V115 TRACED-NOTE.
- Implication: **DROP** as a Korean alpha tilt (alpha 1 equal-weighted, 0 cap-weighted). Korean low volatility becomes a protective candidate, judged drawdown-first with Sharpe non-inferiority (protective 2), not on alpha. US and Europe: alpha 1, protective 2. P4 withdrew the alpha framing of its "long-only low volatility on liquid KRX names" suggestion. Betting-against-beta is BACKLOG and allowed only in a value-weighted, beta-neutral form.

**PC-T-09. Korean 12-1 momentum is positive on average but fragile. Build no standalone 12-1 card; momentum enters only as a composite feature at weight 1.**
- Claims: P6-C10, C11; P2-C30; P1-C26 (qualified); P3-C25 (qualified).
- Numbers:
  - Eom et al. design (August 2000 to June 2019, equal-weighted, winners minus losers in the high-turnover group): the KJFS paper prints -6.13%/month (t -4.76). Replications: chair +0.78 (t 2.57) all caps and +1.22 (t 3.26) excluding microcaps; P6 +0.58 / +1.42; KR lab high-turnover tercile +1.44 (t 3.41).
  - ALL-universe 12-1 long-short, 1996-2026: 0.75%/month gross (t 2.51); Sharpe 0.17 net of 35 bp and -0.07 at 70 bp; 0.05 in 2010-19 and 0.09 in 2020-26 net of 35 bp.
  - Top 500: 0.26%/month net (t 0.81).
  - KR lab long-only excess: -1.3% equal-weighted, +1.6% value-weighted.
  - Round-2 lab:
    - the Eom design gives +1.43%/month (t 3.3) all caps;
    - the KJFS sign appears only when holding returns use unadjusted closes around capital reductions (-11.4%/month);
    - high-turnover winners trail the equal-weighted universe by -11.6%/yr net long-only, although they beat high-turnover losers;
    - 2015-07 to 2024-12 was negative for every momentum construction.
- Verif.: V086, V087, V035, V111 MATCH; V110 TRACED-NOTE; V018 MISMATCH (the premise).
- Implication: **BACKLOG** as a feature (12-7 or 52-week high, weight 1). **DROP** a standalone 12-1 card. Any momentum book must exclude the highest-turnover or lottery names (round 2: +6-8%/yr inside the momentum top quintile). Volatility scaling, concentration caps and a replay of the 2026 crash are mandatory.

**PC-T-10. Korean momentum crashes are winner-led after melt-ups, unlike the US loser-rebound crashes.**
- Claims: P4-C29; P2-C30, C15; P1-C20; P6 (Q6 failure list).
- Numbers:
  - 2026-06-22 to 07-30 (KR lab): ALL universe winners -36.6%, losers -13.0%, equal-weighted universe -18.2%, long-short -24.4%. Top 200: winners -49.6%, losers -3.0%.
  - July 2026 long-short: -17.2% (ALL), -27.3% (top 500), -33.1% (top 200).
  - US WML in 1932 (-60.98% and -74.36%) and 2009 (-42.28% and -45.52%) were loser rebounds after bear markets (Daniel-Moskowitz).
  - Round-2 crash controls on Korean 12-1:
    - The Daniel-Moskowitz gate on KOSPI was off on 2026-06-22 and fired only 9 times in 30 years.
    - Own-volatility scaling had already cut long-short exposure to 0.55 (equal-weighted) and 0.27 (value-weighted), because the sleeve's own volatility rose during the melt-up. The value-weighted long-short lost 10.5% in the crash instead of 40.3% static.
    - Full-sample net Sharpe with both controls: 0.20 to 0.31 (equal-weighted), 0.25 to 0.37 (value-weighted). In 2016-26 the overlay lowered net Sharpe, and long-only equal-weighted winners stay negative under every control.
- Verif.: V014, V035, V118 MATCH; V067 TRACED-NOTE.
- Implication: **CONTEXT and GOVERNANCE.** Keep volatility scaling and the Daniel-Moskowitz gate as mandatory risk controls on any Korean momentum feature. They do not make Korean 12-1 a PASS candidate. The 52-week-high-neutral construction remains untested (PX-T-09).

**PC-T-11. Size is not a signal.**
- Claims: P1-C23; P6-C18.
- Numbers:
  - Korea 2002-15 SMB: 0.16%/month (t 0.45).
  - KR lab size long-short, equal-weighted, gross Sharpe: 0.39 for 1996-2026 and -0.05 for 2016-26; -26.9% in 2025 and -26.5% in 2026 to date; top-200 Sharpe -0.23.
  - US SMB: -0.22% over the 12 months to August 2026.
- Verif.: V013 MATCH.
- Implication: **DROP.** Keep size as a risk control (microcap exclusion; SMB in attribution).

**PC-T-12. The Korean value (and quality) composite needs a point-in-time store and a Value-up split. Value weight is 2.**
- Claims: P1-C26; P6-C19, C20; P3 (KR-VQ and context claim); P5-C05; P3-C21.
- Numbers:
  - Korea July 2002 to June 2015 (gross, in sample): HML 1.05%/month (t 3.41), RMWq 0.65 (t 2.75), CMA 0.66 (t 3.57).
  - 2000-2019 replication rates: value 69.2%, profitability 5.0%.
  - KOSPI price-to-book about 0.99.
- Verif.: V016, V017, V052, V094 MATCH.
- Implication: **BACKLOG** (KR-VQ) behind an OpenDART store (statements only from 2015) and a check that KRX book-per-share is point-in-time. Value is 2, rising to 3 only if a point-in-time test passes and survives a split at 2024-02-26. All Korean value, payout and cancellation tests are split there.

**PC-T-13. Korean net issuance (avoid heavy issuers) is the first Korean fundamental card buildable from KRX data alone.**
- Claims: P3-C19, C20.
- Numbers (chair replication of P3's design, `prof_v03`, 1996-06 to 2026-09):
  - Equal-weighted long-short Sharpe: 0.99-1.01 gross (P3: 1.31); 0.76-0.79 net of 35 bp (P3: 1.04); 0.54-0.56 net of 70 bp.
  - Value-weighted long-short Sharpe net of 35 bp: 0.23-0.25.
  - Long-only, equal-weighted non-issuers minus the equal-weighted universe, net of 35 bp: +1.8 to +2.1%/yr, information ratio 0.48-0.54 (P3: 0.84), 65-68% of years positive.
  - 2017-26: information ratio 0.35-0.38 net of 35 bp (P3: 0.42) and about 0 at 70 bp.
  - Value-weighted long-only: about 0.
  - US comparison (Novy-Marx-Velikov): net issuance earns 0.37%/month net (t 2.43).
  - Round-2 lab exclusion version (drop names whose share count grew more than 10% over 252 sessions): equal-weighted +2.34%/yr net of 35 bp (information ratio 0.65; 2016-26 information ratio 1.43); capped value-weighted information ratio 0.15.
- Verif.: V046, V047 MISMATCH (information ratio overstated); V048, V114 TRACED-NOTE; V042 MATCH.
- Implication: **BUILD-candidate** KR-ISS, as a long-only exclusion or tilt in equal-weighted or capped books. Count at least 10 trials. Expected verdict REVISE, because the 2x-cost step fails over 2017-26. Measure the overlap with the lottery screen, since both avoid distressed KOSDAQ names.

**PC-T-14. Korean market structure must be encoded in every Korean card.**
- Claims: P4-C20, C21; P6-C23, C24, C25, C26 (tax part); P1-C27; P3 (Value-up).
- Numbers:
  - Short-sale bans: 2008-10 to 2009-05; 2011-08 to 2011-11; 2020-03-16 to 2021-05-02, then index stocks only until 2023-11-05; a full ban from 2023-11-06 to 2025-03-30. Short selling resumed 2025-03-31 with a naked-short-selling detection system, 105% collateral and 90-day repayment (FSC).
  - Price limits have been ±30% since 2015-06-15.
  - Sell tax: 0.20% from 2026-01-01; 0.15% in 2025; 0.30% in 2019.
  - KOSDAQ up-limit closes: 51.1 per 10,000 stock-days in 2026, against 24.5-26.8 in 2024-25.
  - Samsung + SK hynix share of KOSPI common-share cap: 35.1% (2025-12-30), 57.3% (2026-06-22), 52.6% (2026-09-29).
  - KOSPI fell 9.99% on 2026-06-23.
- Verif.: V061, V062, V095, V098 MATCH; V019, V097 TRACED-NOTE.
- Implication: **GOVERNANCE.** Tag each card's months by short-sale regime; allow no fills at locked limits; use capped and ex-Samsung/SK hynix benchmarks; apply the tax rate in force each year.

**PC-T-15. Point-in-time data and delisting rules.**
- Claims: P3-C30; P5-C27; P4-C30.
- Numbers:
  - OpenDART statements start with business year 2015; the filing date (`rcept_dt`) carries no time of day.
  - KR lab bounds the delisting bias at 1.4%/yr.
- Verif.: V051, V075 MATCH.
- Implication: **GOVERNANCE/BUILD.** A fundamental becomes available at `rcept_dt` + 1 session, using first-filed values. Run delisting stress cases of -30% and -100%. Korean fundamental cards should expect INSUFFICIENT DATA.

**PC-T-16. Quality/profitability falls from weight 3 to 2 in the US and Europe and is used as a composite leg. It is not "the most consistent factor" and not a crash hedge.**
- Claims: P1-C17, C22; P3-C06, C07, C08, C09; P4-C12, C18.
- Numbers:
  - US 1926-63: profitability 0.09%/month (t 0.86) and investment 0.02 (t 0.14), against value 0.43 (t 2.09).
  - RMW: -16.44% over the 12 months to August 2026.
  - Gross profitability, US: 0.40%/month gross to 0.37 net.
- Verif.: V009, V012, V037, V057 MATCH.
- Implication: **BUILD** as a leg of the US value-quality composite (US-VQ), held at 1.0x under the macro rule.

**PC-T-17. US value on its own gets weight 1 at most and is used only inside the composite.** Use a timely price, intangibles-adjusted book value and evaluation windows of 15+ years.
- Claims: P1-C18, C19; P3-C01 to C05.
- Numbers:
  - HML: -55% from January 2007 to June 2020; revaluation -7.2 pp/yr; structural return 1.1%/yr (5.9% before 2007); intangibles-adjusted HML -43%.
  - US lab HML Sharpe: -0.23 over 2010-18.
  - HML: +13.55% over the 12 months to August 2026.
- Verif.: V010, V011, V036 MATCH.
- Implication: **BACKLOG** as a standalone card; value lives inside US-VQ.

**PC-T-18. A US value + profitability + investment + issuance composite (US-VQ) is the US fundamental BUILD-candidate.**
- Claims: P3-C06, C18, C19, C24; P1-C10, C24; P4-C18; P5-C08.
- Numbers:
  - US 1963-2012, gross to net (Novy-Marx-Velikov): value + profitability 0.82 to 0.77%/month (t 4.82); investment 0.56 to 0.46 (t 3.60); net issuance 0.57 to 0.37 (t 2.43).
  - Expected net long-short Sharpe after decay haircuts, at 50 bp: 0.42 (0.37 at 2x costs; 0.17 after the 60% live haircut). Recomputed.
  - HML-momentum correlation: -0.18 (1949-2017).
- Verif.: V037, V041, V042, V049 MATCH.
- Implication: **BUILD-candidate.** Use EDGAR acceptance + 1 session, sector neutrality and bands; combine with momentum at sleeve level, not as a single card. Expect REVISE before PASS (it needs 15+ years of XBRL data).

**PC-T-19. US stock-level momentum falls from 3 to 1 (Europe 3 to 2, EM 3 to 2).**
- Claims: P1-C20, C21; P3-C25; P4-C17.
- Numbers:
  - MSCI USA Momentum minus MSCI USA: -14.1 pp (2021), -17.6 (2023), +7.2 (2024), +6.1 over the 12 months to August 2026.
  - French WML Sharpe: 0.36 for 1990 to 2017-03; -0.16 for 2008 to 2017-03.
  - Novy-Marx-Velikov momentum: 1.33%/month gross, 0.68 net.
- Verif.: V015, V108 TRACED-NOTE; V059 MATCH.
- Implication: **BACKLOG.** US momentum appears only as a composite or ETF leg, with the macro team's volatility scaling and bear-state gate.

**PC-T-20. US post-earnings drift and standalone accounting anomalies are DROP as cards.**
- Claims: P3-C10 to C17, C21, C22; P1-C11 (attribution use only).
- Numbers:
  - Post-earnings drift has been gone for non-microcap stocks since 2006 (Martineau).
  - Novy-Marx-Velikov, gross to net: SUE drift 0.72 to 0.26%/month (t 1.60; 35% monthly turnover); F-score 0.20 to 0.09 (t 0.45); accruals 0.27 to 0.18 (t 1.43); failure probability 0.85 to 0.24 (t 0.73).
  - Expected net Sharpe of drift at 50 bp: -0.51.
- Verif.: V038-V040, V043, V044, V049 MATCH.
- Implication: **DROP** (US earnings drift 2 to 0). M-score and distress measures serve only as exclusion screens; the earnings-announcement premium is BACKLOG.

**PC-T-21. Market valuation (CAPE, the Fed model) is context only.**
- Claims: P3-C26 to C29.
- Numbers:
  - 1-year out-of-sample R² of log CAPE (chair): -4.8% for 1950-2022, -16.5% for 1990-2022, -39.4% for 2010-22.
  - 10-year out-of-sample R² for 1990-2013: -0.25.
  - Fed model after 1965: R² 0.01.
- Verif.: V050 TRACED-NOTE.
- Implication: **CONTEXT.** No multiplier, consistent with the macro rules.

**PC-T-22. Classic technical rules are DO-NOT-BUILD as standalone cards.** This covers single-index moving-average/filter/breakout timing, oscillators, candlesticks, chart patterns, Fibonacci, Elliott waves and stock-level MA timing.
- Claims: P2-C01 to C06, C16, C17, C21, C23, C24, C25; P4-C03, C04; P7-C21, C23, C24.
- Numbers:
  - 49 markets, 2001-07, 5,806 rules: the best Korean rule's p-value goes from 0.298 to 0.942 after the data-snooping adjustment.
  - KR lab: 303 KOSPI timing rules, SPA p = 0.880.
  - US lab: 322 SPY rules, SPA p = 0.82-0.97; none beat buy-and-hold after 2010.
  - Top 500, net of 35 bp: price/SMA200 selection -0.22%/month; MA21/MA200 +0.08%/month.
- Verif.: V022, V030 MATCH.
- Implication: **DROP / DO-NOT-BUILD.** Rule families on the KOSDAQ segment may be tried only through the family gate (BACKLOG).

**PC-T-23. Index trend timing is a protective overlay (alpha 0), not an alpha source.**
- Claims: P2-C07, C08, C11, C29; P7-C16.
- Numbers:
  - Shiller monthly-average returns have lag-1 autocorrelation 0.274, against 0.057 for SPY month-end returns.
  - 10-month SMA on Shiller data, 1881-2023: 9.33% CAGR with next-month execution, 7.57% when skipping a month, 9.18% buy-and-hold.
  - KOSPI SMA200, 1996-2026: CAGR 8.1% vs 7.2% and max drawdown -41.5% vs -67.1%, but mean excess -1.1%/yr. It stayed fully invested through the 2026-06-22 to 07-30 crash (-37.9% vs -38.6%).
  - Round-2 protective-class tests:
    - The KOSPI 20% volatility target passes the protective class from every start up to 2006 and is INSUFFICIENT (inconclusive) from 2011 and 2016 starts. Its drawdown gain stays positive at every start (+4.4 to +11.6 pp); over 1996-2026 its max drawdown is 6.5 pp better than a static book with the same average exposure, at equal Sharpe.
    - The multi-speed KOSPI trend vote passes on 1996-2026 but becomes REJECT from 2011 starts. SMA200 and the 12-month sign are INSUFFICIENT DATA (too few independent de-risk signals).
    - On SPY at 50 bp, every rule fails.
    - No trend rule protected in the 2026 crash; the volatility target lost 12.2% against 38.6% for buy-and-hold.
    - Averaged Shiller prices inflate trend Sharpe by +0.10 (10-month SMA) to +0.23 (12-month sign).
- Verif.: V023, V024, V034, V116 MATCH.
- Implication: **CONTEXT/protective.** Only an overlay multiplier in [0.5, 1.0] (macro rule). The E1 REJECT stands. Trend protects slow bear markets, and on KOSPI that evidence sits in 1997-2001; the volatility target is the robust protective rule. Flag for synthesis, not re-litigated: in round 2, flooring trend at 0.5 gave back absolute slow-bear protection (KOSPI multi-speed max drawdown -34.1% unfloored vs -39.2% / -44.8% floored), while floored trend combined with the volatility target passed every check.

**PC-T-24. Oscillators are repackaged short-term reversal, and the practitioner canon reduces to three primitives.**
- Claims: P2-C13, C22, C25, C26, C31; P7-C22, C23, C25, C30; P5-C04, C16, C17.
- Numbers:
  - KRX monthly long-short correlations: RSI14 vs 1-month reversal 0.92; %B vs 1-month reversal 0.87.
  - RSI14 contrarian net-of-35-bp Sharpe -0.15; %B -0.32.
  - George-Hwang 52-week high, US 1963-2001: 0.45%/month (1.23% excluding January, t 7.06).
- Verif.: V027 MATCH.
- Implication: **BUILD a feature library** of trend/position, reversal, range volatility, abnormal volume, 52-week high, MA distance and capital-gains overhang. Every variant counts as a trial. Chart-image CNNs and intraday support/resistance are research BACKLOG.

**PC-T-25. Diversified trend following earned crisis alpha over 135 years, but little after 2009.**
- Claims: P2-C09, C10, C11; P7-C16 to C20.
- Numbers:
  - 67 markets, 1880-2013: 14.9% gross, 11.2% net of 2/20 fees, net Sharpe 0.77, zero correlation with equities, positive in 8 of the 10 largest 60/40 drawdowns.
  - Excess return: 6.3%/yr in 2000-09, 0.4%/yr in 2010-18.
  - Trend t-statistic: about 5 since 1960 and about 10 since 1800; short-horizon trends have withered.
  - QUANTGEN's B3 card: Sharpe 0.08.
- Verif.: V025, V104, V105 MATCH; V026 TRACED-NOTE.
- Implication: futures time-series momentum gets alpha weight 1 (broad, long-lookback books only), benchmarked against volatility-scaled buy-and-hold. The B3 REJECT stands.

**PC-T-26. G10 FX technical rules are DROP.**
- Claims: P2-C27; P7-C11 to C15.
- Numbers: across 388 FX technical portfolios, mean Sharpe fell from 0.66 (1980-98, in sample) to 0.06 (1999-2020, out of sample) and does not survive modest costs.
- Verif.: V103 MATCH.
- Implication: **DROP** (the V3 REJECT stands). One slow-trend test on USD/KRW futures is BACKLOG.

**PC-T-27. Keep crypto trend (C3), with a spot-ETF split and a decay monitor.**
- Claims: P2-C12; P7-C01 to C04, C10.
- Numbers:
  - Bitcoin, July 2010 to January 2018: price-to-MA out-of-sample R² 1.17-3.66%; Sharpe 1.92 to 2.09-2.51; max drawdown 89.5% to 64.3-70.3%; break-even one-way cost 1.12-3.96%.
  - C3 (KRW-BTC): Sharpe 1.22 [0.62, 1.77] vs 0.79 for buy-and-hold.
- Verif.: V099 MATCH.
- Implication: **BUILD (keep) + GOVERNANCE.** Split at 2024-01-10, test daily-bar cut times of 00:00 UTC, 00:00 KST and 21:00 UTC, and count three extra trials.

**PC-T-28. In the crypto cross-section, short horizons show momentum, not reversal.** A technical composite is a strong BACKLOG item, and carry is a crash gauge.
- Claims: P7-C05 to C09.
- Numbers:
  - 2014-18: 1- to 4-week cross-sectional momentum earned 2.7 / 3.3 / 4.1 / 2.5% per week; 8-16 weeks were not significant.
  - Crypto carry averaged more than 10% a year, peaked near 60%, and predicts price declines.
  - CTREND's numbers could not be verified.
- Verif.: V100, V102 MATCH; V101 UNVERIFIABLE.
- Implication:
  - crypto short-term reversal 2 to 0, pending a test;
  - cross-sectional momentum 1;
  - a CTREND-lite composite (long-only vs BTC, 10/20 bp) as BACKLOG;
  - a down-only funding/basis multiplier in [0.5, 1.0] as BACKLOG;
  - calendar rules DROP.

**PC-T-29. TradingView, CMT and retail backtests are unverified claims, not evidence.**
- Claims: P4-C06, C25, C26; P7-C25 to C29; P5-C24.
- Numbers:
  - More than 95% of indicators repaint, by TradingView's own estimate.
  - The expected best Sharpe of 100 zero-edge configurations over 5 years is 1.13.
  - A 90%-win bracket of +1%/-9% loses 0.70% per trade at a 70 bp round trip.
- Verif.: V055, V068, V106 MATCH.
- Implication: **GOVERNANCE/DROP.** Never import platform metrics. Port each idea through the protocol: a pure function of OHLCV at t, a shift test, a mapping to the primitives, and N >= 100 trials for TradingView-sourced ideas.

**PC-T-30. Machine-learning ladder: equal-weight composite and ridge now; gradient boosting and neural nets only as shadows; drop deep, order-book and LLM-news strategies.**
- Claims: P5-C01 to C30 (C01-C03, C08, C14, C15, C18, C21 and C27-C29 verified).
- Numbers:
  - Gu-Kelly-Xiu, US out of sample 1987-2016: R² 0.40% for NN3 vs 0.16% for OLS-3; value-weighted long-short Sharpe 1.35 vs 0.61, gross.
  - 1-month-horizon ML has netted about 0 since 2004.
  - Krauss-Do-Huck ensemble: 0.45%/day before costs, 0.25%/day after; negative in 2010-15.
  - ChatGPT news strategy: Sharpe 6.54 to 1.22 between late 2021 and 2024; unprofitable at a 20 bp round trip.
  - Detecting a +0.10 uplift needs 27 / 54 / 108 years at correlations of 0.95 / 0.90 / 0.80.
- Verif.: V069-V078 MATCH; V074 TRACED-NOTE.
- Implication: **BUILD** L0 (equal-weight rank composite with signs fixed in advance), L1 (ridge or rolling Fama-MacBeth shrunk toward L0) and the ML harness (purge and embargo of at least 63 sessions, at most 12 configurations per model family). **BACKLOG** L3 gradient boosting and L4 MLP as non-gating shadows. **DROP** L5 for KRX. No macro × characteristic interactions.

**PC-T-31. Gate additions** (details in section 5.1).
- Claims: P2 (family gate F0-F7), P2-C28; P4-C01, C05, C07, C24, C28; P1-C29, C30; P5-C28, C29; P7 (porting protocol).
- Numbers:
  - C3's benchmark-difference p of 0.04 fails Bonferroni across the 16 trading cards (threshold 0.006), while its Sharpe-vs-zero t of 3.49 survives.
  - With 34 cards tested at p <= 0.10, about 3.4 false passes are expected if all are null.
  - The deflated-Sharpe step implies a required t of 3.17 for 9 configurations and 3.67 for 27.
  - Round 2: with 10-session blocks, step 2 falsely passes 6.9-8.0% of zero-Sharpe strategies instead of 5%, and step 5 rejects 12.8-13.7% at a nominal 10%. P4's longer blocks correct this.
- Verif.: V054, V066 MATCH; V065 TRACED-NOTE.
- Implication: **GOVERNANCE.**

**PC-T-32. The gate is structurally underpowered for tilts with net information ratios of 0.2-0.4. Expect REVISE or INSUFFICIENT DATA, and never loosen the gate.**
- Claims: P1-C29; P4-C22, C23; P5-C28.
- Numbers:
  - A Sharpe of 0.4 needs 18 out-of-sample years; 0.3 needs 31.
  - With 27 years, P(step 2) is 0.64 at Sharpe 0.4; P(step 5) is 0.50 at an information ratio of 0.25 (0.31 with 10 years).
  - Minimum track record for Sharpe 0.5: 16-18 years at t = 2 and 36-40 years at t = 3.
  - Round-2 simulation (KOSPI-like returns):
    - a true Sharpe of 0.4 passes step 2 with 50% probability after 15.8 years and with 80% after 40.3;
    - with 9 counted trials, Sharpe 0.5 needs 39.5 years for a 50% chance at step 3;
    - an information ratio of 0.3 against a 0.4-Sharpe benchmark passes step 5 half the time after about 18 years and 80% only near 50;
    - the joint false-pass rate of steps 2+3+5+8 at zero Sharpe is 0.5% at 10 years.
- Verif.: V020 MATCH; V064, V109 TRACED-NOTE; V063 MISMATCH (an illustration only).
- Implication: **GOVERNANCE.** Report the minimum track record length, and shrink Tier A KRX estimates toward the global cluster evidence.

**PC-T-33. Markets without a data path are context only.**
- Claims: P1-C24, C25; P3-C09; P6-C01 to C04, C06, C07, C27, C28.
- Numbers:
  - Japan WML Sharpe: 0.067 static, 0.416 with dynamic scaling.
  - China A (2000-16): 1-month reversal CAPM alpha 1.49%/month; momentum 0.04%/month (t 0.11, 2008-20).
- Verif.: V081 MATCH; V080 UNVERIFIABLE.
- Implication: **CONTEXT.** Japan: value 3, momentum 0 standalone. China A and Taiwan: momentum 0. See section 4.

**PC-T-34. Korean investor flow falls from 3 to 1.**
- Claims: P6-C21, C22.
- Numbers:
  - 2003-11: lagged foreign and institutional net buying is negative for the next close-to-close return and positive for the next close-to-open.
  - Following foreign buying underperformed KOSPI over 2004-10.
- Verif.: not re-checked (single member, uncontested).
- Implication: **CONTEXT.** Log flow as a state variable; an open-leg test is BACKLOG.

### 2.2 Contested items (PX-T-01 to PX-T-11)

**PX-T-01. Korean quality weight: 1 (P1) vs 2 (P3, P6, P5).**
- Claims: P1-C26 (profitability replicates in 5% of tests, 2000-19) vs P6-C19 (RMWq 0.65%/month, t 2.75, 2002-15) and P5-C05 (gross profitability most significant, 2001-23).
- Verif.: V016, V017 MATCH (both numbers are true, so the evidence conflicts).
- Chair ruling: weight 2 inside the value-quality composite only; no standalone quality card. Settle with an OpenDART test (P1 DC-3, P3 DC-4, P6-X5). **BACKLOG.**

**PX-T-02. Korean earnings drift: 1 (P3) vs 2 (P6); the prior design had 3.**
- Claims: P6-C16, C17 vs P3-C15, C14.
- Numbers:
  - 4.80% over 60 days (t 9.35), market-adjusted and gross, 2002Q4-2017Q4; 6.93% when sentiment trends up.
  - Holding for 60 sessions means about 4 round trips a year, roughly 2.9%/yr at 35 bp per side if fully turned over.
- Verif.: V092 MATCH (gross only).
- Chair ruling: 1 until a test timestamped by DART filing (CAR[-1,+1], entry at `rcept_dt` + 1 session) passes at 2x costs in the top two size terciles; then 2. **BACKLOG.**

**PX-T-03. Korean 52-week high: a weight-2 tilt for equal-weighted small-mid books (P6) vs a weight-1 feature (P2).**
- Numbers:
  - Equal-weighted top quintile minus the equal-weighted universe, net of 35 bp: +0.33%/month (t 2.14) starting 2001-03, but +0.13%/month (t 0.81) starting 1996-03; +0.07 at 70 bp.
  - Capped value-weighted: +0.06%/month (t 0.40).
  - Top 500, net long-short: 0.33%/month (t 1.07).
  - After the 2026 crash, the 52-week-high long-short lost 20.6%.
- Verif.: V089 MATCH (2001 start); V028 TRACED-NOTE.
- Chair ruling: weight 1 as a feature; no standalone card. The 52-week high may be tested once inside P6-X2 as a pre-registered single-configuration (Tier A) test.

**PX-T-04. Step-9 haircut: a flat 60% Sharpe haircut (P1, P6, prior) vs an alpha haircut of 0.5 or 0.3 (P4); P3 uses 0.35-0.5 decay haircuts plus the 60% live haircut.**
- Claims: P1-C15, P6-C05 vs P4-C02, C11, C14.
- Evidence:
  - US post-publication decay is 58%; there is no reliable decline outside the US.
  - Korean local decay: 1-month reversal fell about 90% from 2001-09 to 2020-26, and the issuance Sharpe fell about 40%.
- Chair ruling: show both haircuts for one release. Step 9 stays report-only, so neither choice loosens the gate. Decide at synthesis. **GOVERNANCE.**

**PX-T-05. Step 8 (at least 60% of calendar years positive): keep it (P5 and P6 use it in their pass rules) or make it report-only and replace it with "positive in at least 2 of 3 subperiods" plus a short-sale regime split (P4).**
- Numbers:
  - P4's binomial figures (36% over 8 years, 38% over 10, 25% over 20) assume a zero-median year.
  - The round-2 simulation at true Sharpe 0 gives 28-31% (iid) and 24% (KOSPI-like returns) over 8-10 years, and 16% over 20 years (iid).
  - The joint false-pass rate of steps 2+3+5+8 is 0.5% at 10 years.
- Verif.: V065 TRACED-NOTE.
- Chair ruling: step 8 is the weak step but not the binding one; power is. Keep step 8 and add the subperiod and regime rule; both are required. Revisit after the full gate-size simulation (P4 D14, including the search steps 1, 4 and 7). **GOVERNANCE.**

**PX-T-06. Validation design: CPCV as a gating step, a sealed 2019-2026 holdout, and the family SPA threshold (P2: p <= 0.10; P4: p <= 0.05).**
- Evidence:
  - CPCV's advantage is shown only on synthetic data (P4-C08, unverified).
  - The round-1 labs already examined 1996-2026 for 12-1 and 6-1 momentum, 1-month reversal, volatility, MAX, turnover, the 52-week high, price/SMA200, RSI, %B and more than 600 index rules, so for those families the historical holdout is used up.
- Chair ruling:
  - CPCV is reported but not gating until the gate-size test runs.
  - The contamination log is mandatory now; the incubation clock starts 2026-10-01.
  - New technical families use the stricter SPA consistent p <= 0.05; Tier A single-configuration replications skip the family test.
- **GOVERNANCE.**

**PX-T-07. Korean cost calibration: P4's liquidity buckets vs P6's tiers.** P4: 8/15/30/50 bp non-tax cost per side by 20-day traded value, plus tax. P6: 35 bp for the top 20% of caps, plus 27-39 bp half-spreads below that.
- Chair recomputation (Corwin-Schultz, January 2024 to September 2026):
  - Setting negative two-day estimates to zero first gives median full spreads of 99-117 bp, with no ordering by size.
  - Averaging the raw estimates monthly and then flooring at zero gives 22-57 bp by cap bucket, and 16.5 bp (KRW 50bn+ of daily value) to 47 bp (under KRW 1bn) by traded value.
- Verif.: V096 MISMATCH.
- Chair ruling: keep flat 35/70 bp (tax-inclusive) as the binding base until spreads are calibrated on KIS quotes (P4 D3, DC-P6-05). Report bucket costs alongside. A bucket may raise a name's cost, never lower it below 35 bp, until calibration is done. **GOVERNANCE.**

**PX-T-08. Japan and EM levels.**
- Japan: quality 1 (P3, citing FF 2017) vs 2 (P6); momentum 0 (P1) vs 1 when paired with value (P6).
- EM: value 2 (P1) vs 3 (P6); quality 2 vs 3.
- Chair ruling: Japan quality 1; Japan momentum 0 standalone, allowed as the hedge leg of a value-momentum composite (the substance is agreed); EM value 2 and quality 2. **CONTEXT** (no data path).

**PX-T-09. Does a 52-week-high-neutral momentum construction (WML*) or a concentration cap reduce KRX momentum crash risk beyond volatility scaling?**
- Resolved by round 2 (moved into PC-T-10): own-volatility scaling had cut exposure before 2026-06-23; the Daniel-Moskowitz gate did not fire, as P2 and P4 predicted (V118).
- Still open: P2 proposes the 52-week-high-neutral construction (US 1930-2022 worst month -23.7% vs -74.1%) together with Samsung/SK hynix caps. Neither was tested on KRX in round 2.
- Status: **BACKLOG** (P2 DC-J). The macro decisions are not re-litigated.

**PX-T-10. Planning decay haircuts per factor.**
- The brief's per-factor Ilmanen numbers cannot be verified: AQR's page reports only a 30% average out-of-sample drop.
- P1 plans with 33-60%; P3 uses 0.49 for value, 0.50 for single anomalies, 0.35 for composites and 0.75 for earnings drift; P4 uses 0.5 or 0.3.
- Chair ruling:
  - plan with P4's 0.5 (in-sample or overlapping the discovery sample) or 0.3 (fully post-publication);
  - use P3's 0.75 for drift-like signals;
  - replace planning values with measured local decay where 20+ years of data exist;
  - stop attributing the per-factor numbers to Ilmanen et al.

**PX-T-11. Korean 12-7 momentum: its own card (P6-X2) or a feature only (P1, P2)?**
- Numbers (ALL universe, quintiles):
  - 2001-26: 1.19%/month gross (t 4.93); Sharpe 0.60 net of 35 bp, 0.11 at 70 bp.
  - From 1996: 0.83%/month (t 2.74); Sharpe 0.19 net of 35 bp, -0.18 at 70 bp.
  - At 70 bp the Sharpe is negative in both 2010-19 (-0.31) and 2020-26 (-0.15).
  - July 2026: -10.6%.
  - Round-2 lab: 12-7 has the highest equal-weighted gross Sharpe (0.57, 1996-2026), but its turnover leaves the same net Sharpe as 12-1 (0.20 vs 0.20). Its 2016-26 net Sharpe is -0.01 equal-weighted.
- Verif.: V088, V111 MATCH (2001 start, start-date sensitive); the Sim-Kim 12-7 FF5 alpha of 0.531%/month (t 2.05) is MATCH (V082).
- Chair ruling: allowed as one pre-registered Tier A card with volatility scaling and caps. The expected verdict is REJECT or REVISE (step 6 fails after 2010). Feature weight is 1 either way.

### 2.3 Refuted or withdrawn items (PR-T-01 to PR-T-16)

| ID | Statement (source) | What the checks found | Verif. | Implication |
|---|---|---|---|---|
| PR-T-01 | "Korean 12-1 momentum is negative in high-turnover stocks (-6.13%/month, t -4.76)" (context brief; KJFS 2020; relied on by P1's Korea row and P3 section 8) | The figure is printed that way, but four survivorship-free replications give +0.58 to +1.66%/month (chair +0.78 t 2.57 all caps; round 2 +1.43 t 3.3). Round 2 reproduces the negative sign only when holding returns use unadjusted closes around capital reductions / reverse splits (-11.4%/month; 0.09% of stock-days) | V086, V087 MATCH; V110 TRACED-NOTE; V018 MISMATCH | REFUTED for QUANTGEN data; Korea XS-mom 1 as a feature |
| PR-T-02 | "Korean 1-month reversal -2.95%/month (t -3.77, 1999-2021)" (context brief; macro note) | Sim-Kim's -2.950 is a Fama-MacBeth slope on last month's return. Measured spreads are 0.52-0.86%/month gross (2001-26, equal-weighted), about 0 since 2010, negative net; value-weighted without microcaps about 0 gross (round 2) | V082, V083, V117 | WITHDRAWN (unit error) |
| PR-T-03 | Prior design: volume-filtered 5-day reversal, Korea weight 3, "0.5-1.0 gross, costs take half or more" | Gross -0.05 to +0.31%/week across designs (2001-26), about 0 after 2016 in most; net -0.92 to -1.33%/week; costs take more than all | V032, V085 | REFUTED; weight 0 |
| PR-T-04 | Prior design: quality is the "most consistent sign of any fundamental factor" (weight 3) | Absent before 1963 (0.09%/month, t 0.86); RMW -16.44% over 12 months to August 2026; weak in Japan; long-only quality lagged in 2022 | V009, V012 | REFUTED as stated; weight 2 |
| PR-T-05 | Prior design: Korea low-vol 2 as a long-only tilt | Value-weighted tilt -40/-44 points in 2025/26; equal-weighted long-only excess +1.1%/yr (t 0.5); no low-beta CAPM alpha | V090, V002 | REFUTED; exclusion screen instead |
| PR-T-06 | Prior design: time-series momentum "0.4-0.8 per asset, about 1.0 diversified" | Excess 0.4%/yr in 2010-18; B3 Sharpe 0.08; single-asset evidence weak | V025 | REFUTED for the post-2009 era; plan 0.0-0.3 diversified |
| PR-T-07 | Prior design: Korea flow 3 and earnings drift 3 rated "strong" | Flow predicts the next open, not the next close; drift evidence is gross-only and pre-2018 | V092 | WITHDRAWN; flow 1; drift 1 (contested 1-2) |
| PR-T-08 | Prior design: crypto short-term reversal weight 2 | Crypto short-horizon cross-sectional evidence is momentum (1-4 weeks) | V100 | WITHDRAWN; weight 0 pending a test |
| PR-T-09 | P6-C09 sub-claim: the volume filter "selects continuation" (wrong sign) | Filtered gross spread is -0.05 to +0.31%/week depending on design; the quintile filter-then-sort design is +0.31%/week (t 3.08) | V085 | WITHDRAWN as a general statement |
| PR-T-10 | P2-C15: 52-week-high-neutral momentum has max drawdown -23.7% vs -74.1% | These are the worst monthly returns | V029 | CORRECTED; the drawdown benefit is not established |
| PR-T-11 | P3-C20: KR-ISS long-only net information ratio 0.84 [0.46, 1.25] | About 0.5 (0.48-0.54) on independent replication; 2017-26 0.35-0.38 reproduces | V047, V048 | CORRECTED |
| PR-T-12 | "The average anomaly earns about 8 bp/month net" (P3-C23, P5-C12) | 8 bp is the 120-anomaly working paper; the published JFQA 2023 version says 4 bp for 204 anomalies | V008, V045 | SUPERSEDED |
| PR-T-13 | "Ilmanen et al. (2021): value -49%, momentum -23%, multifactor -18%" (context brief) | AQR's article page reports a 30% average out-of-sample drop and no factor-specific numbers | V107 | WITHDRAWN as attributed |
| PR-T-14 | P6-C26: Corwin-Schultz median spreads 39-79 bp, so "35 bp understates the bottom 60% of caps" | Not reproducible under either standard convention (22-57 bp or 99-117 bp) | V096 | WITHDRAWN pending quote calibration |
| PR-T-15 | P4-C22 illustration: Sharpe 1.5 over 60 months gives an SE of 0.188 | It mixes units; the annualised SE is about 0.47 | V063 | CORRECTED (no decision affected) |
| PR-T-16 | Prior design: volatility-scaled sizing adds +0.1 to +0.3 Sharpe "on nearly every strategy" | Robust mainly for momentum and trend (already corrected by the macro research; P2-C11, P7-C18) | n/a | REFUTED (prior) |

---

## 3. Corrected anchors (numbers that must not propagate)

| Number in circulation | Correct value or reading | Source |
|---|---|---|
| Korean 1-month reversal "-2.95%/month (t -3.77)" | A Fama-MacBeth slope on r(-1), January 1999 to February 2021: about -0.30% next month per +10% last month. The measured equal-weighted quintile spread is 0.52%/month gross (2001-26), 0.08%/month in 2020-26, negative net | Sim and Kim (2021), Emerald JDQS 29(3); `prof_v01` |
| Korean high-turnover momentum "-6.13%/month" | It is printed that way, but replications give +0.78 (t 2.57) / +1.22 (t 3.26) [chair], +0.58 / +1.42 [P6], +1.44 [KR lab tercile], +1.43 (t 3.3) / +1.66 (t 4.5) [round 2]. The negative sign appears only with unadjusted closes around capital reductions | e-kjfs.org article page; `prof_v02`; KR lab cross-checks; R2_KR_summary.md section 2.2 |
| Step-8 false pass "36-38% at 8-10 years" (P4) | 24-31% at true Sharpe 0 (36-38% assumes a zero-median year); the joint false-pass rate of steps 2+3+5+8 is 0.5% at 10 years | R2_IDX_summary.md section 7 |
| "18 OOS years for Sharpe 0.4" (P1) | 18 years gives about a 50% chance at step 2; 80% needs about 37-43 years | R2_IDX_summary.md section 7 |
| Ilmanen et al. per-factor haircuts (-49% / -23% / -18%) | Only an average 30% out-of-sample drop is verifiable | AQR article page |
| "Average anomaly 8 bp/month net" | 4 bp/month (204 anomalies; published 2023) | Chen and Velikov, JFQA abstract |
| KR-ISS long-only net information ratio 0.84 | 0.48-0.54 full sample (net of 35 bp); 0.35-0.38 in 2017-26; about 0 at 70 bp in 2017-26 | `prof_v03` |
| Jeon-Byun "max drawdown -23.7% vs -74.1%" | Worst monthly return -23.66% vs -74.06% | Marquette e-Publications |
| P4's "SE 0.188" (Sharpe 1.5, 60 months) | Annualised SE about 0.47 | Lo (2002) formula |
| Volume-filtered weekly reversal 0.44%/week (P2) and 0.03%/week (P6) | Design-dependent: -0.05 to +0.31%/week (2001-26); 0.14-0.26%/week in the top 500 (1996-2026); always negative net | `prof_v04_weekly_reversal.csv` |
| Corwin-Schultz KRX spreads 39-79 bp (P6) | 22-57 bp or 99-117 bp depending on convention; not a calibration source | `prof_v07`, `prof_v07b` |
| "Samsung + SK hynix = 55.5% of KOSPI" (undated) | 35.1% (2025-12-30), 57.3% (2026-06-22), 52.6% (2026-09-29) of KOSPI common-share cap; 31% of the KR lab's value-weighted ALL universe at 2025-12-30; MSCI Korea 60.8% (free-float index, August 2026). Always state the date and the denominator | KR cache; KR lab; P1-C27 |
| Korea 52-week high "+0.34%/month net (t 2.31)" | True from 2001; +0.13%/month (t 0.81) from 1996. Always state the start date | KR lab daily series |
| Korea 12-7 momentum "net-of-35-bp Sharpe 0.54" | 0.60 from 2001; 0.19 from 1996; negative at 70 bp after 2010 | `prof_v02` |
| CAPE 1-year out-of-sample R² "-2.4% (1950-) / -11.1% (1990-)" | -4.8% / -16.5% (chair), -4% / -18% (US lab); specification-dependent, all negative | `prof_v06` |
| P6: value-weighted low-risk tilt "-20.3 points in 2025" | Single-signal value-weighted top quintiles lost 35-40 points in 2025 | KR lab daily series |
| "US 12-1 momentum Sharpe 0.02 since 2008" | Local French data end 2017-03: -0.16 for 2008-2017; not verifiable to 2026 here | linearmodels French file |
| "ChatGPT strategy unprofitable at 20 bp" | 20 bp round trip (10 bp per side) | Lopez-Lira and Tang, arXiv v6 |
| "Trend following 2010-18: 0.4%/yr" | Correct as excess over T-bills (Exhibit 1); total return was 1.6%. Do not swap the two | AQR 2019 |

---

## 4. Consolidated per-market × per-family weights (0-3)

Weights are design priors, not gate results; any weight of 2 or more still needs a PASS card. "Alpha" means the family is expected to add return. "Protective" means a screen or overlay that reduces exposure to losers or drawdowns, used only within the macro band [0.5, 1.0] and never above 1.0x. **Bold** marks a change from the prior design. "n.r." means no professor reviewed the cell, so the prior is kept and flagged.

### 4.1 Alpha weights: prior → professors' consolidated view

| Market | XS-mom | ST-rev | Value | Quality | Low-vol tilt | Flow | Earn. drift | TS-mom |
|---|---|---|---|---|---|---|---|---|
| US | 3 → **1** | 1 → **0** | 1 → 1 (composite only) | 3 → **2** | 2 → **1** | 1 → 1 (n.r.) | 2 → **0** | 3 → **0** (protective 2) |
| Europe | 3 → **2** | 1 → **0** | 2 → 2 | 3 → **2** | 2 → **1** | 1 → 1 (n.r.) | 2 → 2 (n.r.; US evidence suggests ≤1) | 3 → **0** (protective 2) |
| Japan | 0 → 0 (value-paired hedge only) | 2 → **1** | 3 → 3 | 2 → **1** (PX-T-08) | 3 → **2** | 1 → 1 | 1 → 1 | 2 → **0** (protective 2) |
| **Korea** | 1 → 1 (12-7 / 52wH features only; no 12-1 card) | 3 → **0** | 2 → 2 (3 only after a PIT test) | 1 → **2** (composite only; PX-T-01) | 2 → **1** EW / **0** cap-weighted | 3 → **1** | 3 → **1** (PX-T-02: P6 says 2) | 2 → **0** (protective 2) |
| Taiwan (P6 only) | 1 → **0** | 3 → **2** | 1 → **2** | 1 → 1 | 1 → 1 | 3 → **1** | 2 → 2 | 2 → **0** (protective 2) |
| China A (P6 only; no data path) | 0 → 0 | 3 → 3 | 1 → **2** | 1 → **2** | 1 → **3** | 3 → **1** | 1 → 1 | 1 → **0** (protective 1) |
| India | 3 / 1 / 2 / 3 / 2 / 2 / 2 / 2 (n.r.; prior kept; XS-mom 3 likely too high at stock-level costs) | | | | | | | |
| EM (broad) | 3 → **2** | 1 → 1 | 2 → 2 (PX-T-08: P6 says 3) | 2 → 2 (PX-T-08) | 1 → **2** | 2 → **1** | 1 → 1 | 3 → **0** (protective 2) |
| Crypto | 1 → 1 | 2 → **0** | 0 | 0 | 0 | 2 → **1** | 0 | 3 → 3 (C3) |
| Futures / FX | "weak" → **0** | — | — | — | — | — | — | "strong" → **1** for broad, long-lookback futures books; **0** for G10 FX technical rules |

In the TS-mom column, "protective 2" refers to the combined index risk overlay in Table 4.2: a volatility target at 2 and trend at 1.

### 4.2 Protective uses (new rows)

| Use | Korea | US | Others | Status and reason |
|---|---|---|---|---|
| Lottery/low-risk exclusion (drop the worst decile or quintile of a volatility + MAX + turnover composite) | **3** for equal-weighted and small-mid books; 1 (hygiene) cap-weighted; 0 for the top 200 | 1 (untested) | Japan 1, China A 3, Taiwan 2, EM 2 (P6) | KR equal-weighted +3.1%/yr net of 35 bp, 7/8 indicative gate steps (REVISE); capped value-weighted +0.85%/yr (REVISE); top 200 REJECT. BUILD-candidate (PC-T-07) |
| Heavy-issuer exclusion (net issuance) | **2** (equal-weighted or capped) | inside US-VQ | — | KR long-only net information ratio about 0.5, decaying; exclusion form information ratio 0.65 on equal-weighted books. BUILD-candidate (PC-T-13) |
| Index volatility target (macro rule; endorsed) | 2 | 1 (futures cost only) | — | KOSPI 20% target passes the protective class from starts up to 2006 (INSUFFICIENT from 2011/2016 starts) with a positive drawdown gain at every start; SPY at 50 bp fails (PC-T-23) |
| Index trend overlay (SMA200, 10-month SMA, TSMOM, multi-speed vote) | **1** (KOSPI evidence sits in 1997-2001; REJECT from 2011 starts) | **1** (futures cost only; INSUFFICIENT DATA) | 1-2 (n.r.) | Protects slow bears, not fast crashes; no alpha; multiplier in [0.5, 1.0] (PC-T-23) |
| Defensive low-volatility / low-beta sleeve, judged drawdown-first with Sharpe non-inferiority (or Jensen's alpha) | **2** (value-weighted low-volatility quintile beat the market in 7 of 7 crash windows; heavy bull-market drag) | **2** | Europe 1-2, Japan 2 | Flat security market line; no alpha (PC-T-08) |
| Short-term reversal guard (do not buy last month's top-decile winners) | 1 | 0 | — | Reversal is real gross; avoids chasing spikes (PC-T-06) |
| Momentum crash controls | own-volatility scaling (the only control that cut exposure before July 2026), Daniel-Moskowitz gate (did not fire), Samsung/SK hynix caps (macro); 2026 stress replay; exclude highest-turnover / lottery names; 52-week-high-neutral construction untested | macro σ126 scaling plus Daniel-Moskowitz gate | — | PC-T-10; PX-T-09 (BACKLOG) |
| Crypto funding/basis multiplier (down-only) | — | — | Crypto 1 | BACKLOG (PC-T-28) |

### 4.3 Feature-only families and new candidates

| Family | Korea | US | Other | Status |
|---|---|---|---|---|
| 52-week-high nearness | 1 (P6: 2; PX-T-03) | 2 | Europe/Japan 1 | Composite feature; card BACKLOG |
| 12-7 (intermediate) momentum | 1 | — | — | Tier A card allowed; expect REJECT/REVISE (PX-T-11) |
| MA distance / trend factor | 1 | 2 | — | BACKLOG feature |
| Capital-gains overhang | 2 (to test, P2 DC-I) | 1 | — | BACKLOG feature |
| Value + quality composite | 2 (KR-VQ; needs PIT store) | 2 (US-VQ; BUILD-candidate) | — | PC-T-12, PC-T-18 |
| Net issuance | 2 (KR-ISS) | 2 (inside US-VQ) | — | PC-T-13 |
| Technical composite (CTREND-lite) | — | — | Crypto 2 (provisional) | BACKLOG |
| Size | 0 | 0 | 0 | DROP as a signal; risk control only |

### 4.4 Main changes from the prior design, with reasons

- **Korea ST-rev 3 → 0 (alpha).** Gross reversal is real but net-negative in every design (weekly −0.68 to −1.33%/week net; monthly net-of-35-bp Sharpe −0.08 to −0.22); the prior volume filter does not help. The "−2.95%/month" anchor is a regression slope.
- **Korea XS-mom 1 → 1, redefined.** It is positive but fragile, not negative. No 12-1 card; it is used only as a 12-7 or 52-week-high feature.
- **Korea low-vol 2 → 1 equal-weighted / 0 cap-weighted (tilt), plus a new lottery exclusion at 3 (equal-weighted books) and a protective low-volatility sleeve at 2.** The premium sits in the short leg; the value-weighted tilt lost 40-44 points in 2025-26, yet the low-volatility book protected in 7 of 7 crash windows.
- **Korea flow 3 → 1** (no close-to-close evidence) and **earnings drift 3 → 1** (gross-only evidence; contested at 2).
- **Korea quality 1 → 2** (composite only; contested); **value stays 2** (point-in-time test and Value-up split required).
- **US XS-mom 3 → 1; US/Europe quality 3 → 2; US earnings drift 2 → 0; US low-vol 2 → 1 (alpha) with a protective sleeve at 2.**
- **TS-mom on equity indices: alpha 0; trend overlay protective 1, volatility target protective 2.** No timing rule beats buy-and-hold after data-snooping control in the US (322 rules) or Korea (303 rules) (E1 REJECT). Round 2 shows the trend's protection on KOSPI depends on 1997-2001, while the 20% volatility target keeps a drawdown gain at every start date (protective PASS from starts up to 2006).
- **Crypto ST-rev 2 → 0, flow 2 → 1; TS-mom 3 kept (C3).**
- **Futures/FX: "TS-mom strong" → 1 for broad, long-lookback futures books; G10 FX technical rules 0.**

---

## 5. Testing protocol and gate amendments

### 5.1 Add (consensus)
1. **Family gate before the nine-step gate** (P2 F0-F7; P4 D1). Pre-register the whole rule family, its benchmark, costs and criterion. Test "no member beats the benchmark" with a studentised SPA and the Reality Check (stationary bootstrap, at least 2,000 resamples). The family must reach SPA consistent p <= 0.05 at 1x costs (the stricter of P4's 0.05 and P2's 0.10). Then name survivors with StepM or Romano-Wolf, or control the FDR at 10% when combining rules, and require persistence (positive out-of-sample net excess in at least 60% of walk-forward windows).
2. **Trial registry.** Every family member, every revision and every data-lab quick-check look counts toward the deflated-Sharpe N. TradingView-sourced ideas carry N >= 100. A composite choosing k of n signals counts n^k. ML: at most 12 configurations per model family, and every configuration counts.
3. **Program-wide multiplicity control.** Benjamini-Hochberg at q = 0.10 per release, and Holm for displayed cards. Re-score the existing 34 cards transparently (P4 D11) rather than demoting them silently.
4. **Attribution block on every card** (PC-T-01), and a Jensen's-alpha t-test variant of step 5 for cards with beta not equal to 1, from the next pre-registered gate version (not retroactive). For the Sharpe difference, use a Ledoit-Wolf studentised bootstrap.
5. **Primary statistic for stock cards:** long-only daily net excess over the same-universe equal-weighted benchmark. Report capped value-weighted results too (a sign split means REVISE), long-short as a diagnostic, and the short leg's share.
6. **Tiered hurdles** (PC-T-02): Tier A t >= 2.0; Tier B t >= 3.0 plus the family SPA; Tier B+ t >= 3.4 (cross-sectional) or 3.8 (time-series alpha). All tiers also need DSR >= 0.95, a Sharpe above 0 at 2x costs, and a plateau.
7. **Korea encoding** (PC-T-14): short-sale regime tags; no fills at locked limits; next-open entry for holding periods of 5 sessions or less; the sell tax in force each year; a split at 2024-02-26; capped and ex-Samsung/SK hynix benchmarks; universe hygiene (no preferred shares, SPACs, REITs, funds, warning-designated stocks, or prices under KRW 1,000).
8. **Point-in-time and delisting** (PC-T-15): availability at `rcept_dt` + 1 session with first-filed values; delisting stress at -30% and -100%; a check that KRX book-per-share is point-in-time.
9. **Power reporting** (PC-T-32): report the minimum track record length at the tier hurdle. If it exceeds the available history, the verdict is INSUFFICIENT DATA, not REJECT. Shrink Tier A estimates toward the global cluster evidence.
10. **Inference details:** PSR and HAC t on net excess; block length >= max(Politis-White, 2 x holding period); infer only on the concatenated out-of-sample path. Round 2 shows that 10-session blocks raise the step-2 false-pass rate to 6.9-8.0% (nominal 5%) and step-5 rejections to about 13% (nominal 10%) on KOSPI-like returns.
10a. **Protective cards are judged as protective cards.** Index trend, volatility targets, low-volatility sleeves and exclusion screens on cap-weighted books are tested on protective-class checks (P1, P2, P4; round-2 harness): max drawdown vs a static book with the same average exposure, tail exposure, Sharpe non-inferiority within -0.10, drawdown episodes, years, plateau, and sufficiency (enough independent de-risk signals). They are never tested on step-5 outperformance alone, which a volatility target cannot pass however well it protects. P1's Jensen's-alpha test is the alternative for cards with beta below 1.
11. **Stress reporting:** worst rolling 21- and 63-session net excess, plus replays of 2008-09, 2020-03, 2025-01 to 2026-06 and 2026-06-23 to 07-30.
12. **Contamination log and incubation:** list every family and date range already examined by the labs. For those families the historical holdout is used up, and prospective incubation (at least 252 sessions, clock starting 2026-10-01) is the only clean out-of-sample test.
13. **ML leakage checklist** (P5 section 6): purge and embargo of at least the label horizon (63 sessions); features ranked per date; no macro × characteristic interactions; LLM features only after the model's training cutoff or with point-in-time models.
14. **Porting protocol for TradingView/CMT logic** (P7 D): a pure function of OHLCV at t; a shift test; mapping to the F1-F10 primitives; every variant counted as a trial; costs set to QUANTGEN's rates.
15. **Crypto:** a pre-registered split at 2024-01-10 and a cut-time sensitivity test for C3.

### 5.2 Change (contested; see section 2.2)
- Step 9 haircut: flat 60% Sharpe haircut vs an alpha haircut of 0.5 or 0.3. Show both for one release (PX-T-04).
- Step 8: keep it and add "positive in at least 2 of 3 subperiods" plus the short-sale regime split. Drop it only after the gate-size simulation (PX-T-05).
- CPCV and the sealed 2019-2026 holdout: CPCV is reported but not gating; the holdout is already used up for the families the labs examined (PX-T-06).
- Cost buckets: flat 35/70 bp stays binding until KIS-quote calibration (PX-T-07).

### 5.3 Must not be loosened
- Read-only by construction; decide at the close of t and earn from t+1; every result re-run at 2x costs.
- DSR >= 0.95 with every revision counted; PBO; plateau; pre-registration fixed before the test.
- Macro rules: macro variables size and never direct; overlay multipliers stay in [0.5, 1.0]; reversal and quality sleeves are held at 1.0x.
- The gate is not loosened because factor cards fail it (P1, P4). A REVISE or INSUFFICIENT DATA verdict is the expected, honest outcome.
- No cost bucket below the flat 35 bp is used to pass a card until calibration (PX-T-07).
- No TradingView or other platform metric is imported, and no shadow ML result enters displayed exposure.
- No retroactive change to step 5 or to existing PASS verdicts; re-scoring is reported transparently.

### 5.4 Consolidated protocol for a new KRX stock-level card
1. Write a pre-registration file and hash it: hypothesis, tier, mechanism, formula, at most 27 configurations, universe, rebalance and band, benchmark, cost model, primary statistic, hurdles, subperiods (1996-2005 / 2006-2015 / 2016-2026) and incubation start.
2. Run the family test (5.1-1) if more than one configuration is tried.
3. Run the nine-step gate with the additions in 5.1. The primary statistic is long-only net excess vs the equal-weighted universe. The card must clear its tier hurdle at 35 bp and keep a positive Sharpe at 70 bp.
4. Run the Korea-specific reports: short-sale regimes, limit locks, the Value-up split, capped and ex-mega-cap results, the 2026 stress replay, and delisting stress.
5. Produce the attribution block and the haircut display (both versions until PX-T-04 is settled).
6. Incubate prospectively before any exposure is displayed above the base allocation.

---

## 6. Debate record

**D1. What is the sign of Korean 12-1 momentum, and is its weight 0 or 1?**
- Side A (negative, drop):
  - Context brief §3.
  - P1's Korea row (XS-mom 1 → 0), citing the brief and Han-Lee-Kang's 20% replication rate on KOSPI only (P1-C26).
  - P3 §8: "Korean 12-1 momentum is negative" (P3-C25).
- Side B (positive but fragile):
  - P6-C10: the KJFS result is not reproduced (+0.58 / +1.42%/month).
  - P2-C30: top-500 12-1 earns 0.62%/month gross (t 1.82).
  - KR lab: positive in every turnover tercile.
- Reviewer challenge:
  - P5, reading P1, asked for the primary source behind the brief's sentence.
  - P4, reviewing P6, asked for an exact replication and for confirmation that the paper prints the number as quoted.
- Recomputation:
  - The KJFS article page prints -6.13% (t -4.76) (V086).
  - The chair's independent replication gives +0.78 (t 2.57) all caps and +1.22 (t 3.26) excluding microcaps; excluding January 2001, +0.98 and +1.42 (V087).
  - Round 2 adds a fourth replication (+1.43, t 3.3) and the mechanism: the negative sign appears only when holding returns use unadjusted closes around capital reductions (V110). It also shows that high-turnover winners lose long-only (-11.6%/yr net) even though they beat high-turnover losers.
- Resolution:
  - P1 and P3 withdrew the "negative" premise (PR-T-01).
  - P6 conceded that 12-1 does not reliably pay 35 bp after 2010 (net-of-35-bp Sharpe 0.05-0.09) and that no standalone 12-1 card should be built.
  - Consensus PC-T-09; still open: PX-T-11 (12-7 as its own card) and PX-T-09 (crash control).

**D2. What should Korea's short-term reversal weight be (prior 3), and what does the volume filter do?**
- Positions:
  - P2 (DROP): 0.53%/week gross, -0.59 net; with the filter 0.44 gross, -0.88 net.
  - P6: 1-month reversal is real gross (0.86%/month) but negative net; the filter has the "wrong sign" (0.03%/week).
  - P4 (BACKLOG pending bucket costs): Novy-Marx-Velikov short-term reversal is -1.28%/month net.
  - P5: weekly CNN signals are reversal-like and trade heavily.
- Reviewer challenges:
  - P6 (second reader of P2) found P2's filtered result too favourable.
  - P4 found P6's "wrong sign" rested on one threshold and one design.
  - P2 pointed out that the brief's -2.95 cannot be a top-500 spread.
- Recomputation:
  - Sim-Kim's -2.950 is a Fama-MacBeth slope (V082, V083).
  - Four designs on two universes (V031, V032, V085): unconditional 0.39-0.43%/week gross (1996-2026); filtered -0.05 to +0.31%/week (2001-26); every design net -0.68 to -1.33%/week.
  - 1-month reversal: 0.52%/month (2001-26), down to 0.08%/month in 2020-26.
  - Round 2: value-weighted without microcaps, 1-month reversal is about 0 gross and negative net in every sub-period after 2005 (V117).
- Resolution:
  - The stock-level reversal card is dropped unanimously (PC-T-06).
  - P6 withdrew the general "wrong sign" claim (PR-T-09).
  - P2 accepted that its filtered gross level is overstated.
  - The -2.95 anchor is withdrawn (PR-T-02).

**D3. Is low volatility / betting-against-beta an alpha source or protection?**
- Positions:
  - P1: BACKLOG; only a value-weighted, beta-neutral version, judged on Jensen's alpha; Korea low-vol 2 → 1.
  - P4: "possibly long-only low volatility on liquid KRX names" among the realistic BUILD candidates.
  - P6: a short-leg phenomenon; drop the tilt; exclusion screen at 3.
  - US lab: flat security market line; low-beta Sharpe 0.65 vs 0.41.
- Reviewer challenges:
  - P3, reviewing P1, asked whether the flat US line carries over to Korea.
  - P4, reviewing P6, asked whether missing dividends understate the low-volatility long leg.
- Recomputation (`prof_v09`):
  - The Korean line is flat (+1.1%/yr, t 0.19).
  - Low-beta raw alpha is -1.0%/yr (t -0.26) equal-weighted and -2.4% (t -0.71) value-weighted; high-beta equal-weighted alpha is -7.0% (t -1.72).
  - The value-weighted low-volatility tilt lost 40 and 44 points in 2025 and 2026.
  - Missing dividends (roughly 1-2%/yr) and the missing risk-free rate both understate the low-beta leg, but not enough to make the tilt significant (KR lab t 0.5).
  - Round 2 (V115): the lowest-volatility quintile has an insignificant CAPM alpha (+0.7%, t 0.3, value-weighted) but beat the value-weighted market in 7 of 7 crash windows and lagged in 9 of 10 rebounds.
- Resolution: P4 withdrew the alpha framing. Low volatility is recast as a protective candidate, judged drawdown-first with Sharpe non-inferiority, alongside the lottery exclusion screen. Consensus PC-T-07 and PC-T-08.

**D4. Is quality the most robust factor, and does long-only quality protect?**
- Positions:
  - Prior design: the most consistent factor, weight 3.
  - P1: 2 (absent before 1963; RMW -16.4%; displaced from the JKP tangency portfolio).
  - P3: 2 (QMJ robust long-short, but long-only QUAL lagged in 2021-26 and 2022).
  - P4: accounting anomalies lose 60-77% of Sharpe out of sample; cash profitability is the best factor model net of costs.
  - P5: Korean gross profitability is the most significant characteristic, so raise Korean quality.
- Reviewer challenges:
  - P1, reviewing P3, asked whether QMJ's alpha is capturable long-only.
  - P3, reviewing P4, noted that the pre-1963 test is US-only.
- Recomputation: V009, V012 and V037 all MATCH.
- Resolution: US/Europe quality 3 → 2 as a composite leg held at 1.0x (PC-T-16); "most consistent" withdrawn (PR-T-04). Korea remains open (PX-T-01).

**D5. Does value still work after the Korean Value-up and Japanese TSE reforms?**
- Positions:
  - P1: Korea value 3 if a point-in-time test confirms; Japan 3.
  - P3: Korea 2 pending point-in-time data, split at February 2024.
  - P6: Korea 2; Value-up is a regime break; run an event study; Japan 3 with a capital-efficiency overlay; the TSE request had only a modest valuation effect.
- Reviewer challenges:
  - P3 to P1: Kang's HML sample ends in June 2015, before the reforms.
  - P4: 32 months of Value-up data cannot pass a gate.
- Recomputation: Kang and AMRO MATCH (V016, V052). P3's cancellation result (2024-26 value-weighted +20.6%/yr, t 2.07) was not re-run.
- Resolution: Korea value 2 now; Japan value 3; mandatory 2024-02-26 split and event study; buybacks and cancellations stay BACKLOG with a regime flag (PC-T-12).

**D6. How strong is Korean earnings drift?**
- Positions:
  - P6: 4.80% over 60 days (t 9.35, 2002-17), from individuals trading against the news; weight 2.
  - P3: no Korean point-in-time or net-of-cost evidence; drift lives in illiquid names; weight 1; the first test must use the 3-day announcement return because QUANTGEN has no point-in-time consensus forecasts.
  - P1: the Daniel-Hirshleifer-Sun PEAD factor supports a card from another panel.
- Reviewer challenge (P4 to P6): 60-day holds cost about 2.9%/yr at 35 bp if fully turned over, and the 4.80% is gross, market-adjusted and not split by size.
- Recomputation: Shin et al. MATCH (V092); no local test is possible without DART timestamps.
- Resolution: open (PX-T-02); chair weight 1 pending P3 DC-3 / P6-X4.

**D7. Does the 52-week high work in Korea?**
- Positions:
  - P6: equal-weighted tilt +0.34%/month net (t 2.31); +0.55 with the lottery exclusion; weight 2.
  - P2: a feature at KRX 1; the top-500 version is not significant net.
  - KR lab: long-only excess +1.6%/yr (t 0.8).
- Reviewer challenges:
  - P6 to P2: the top-500 universe leaves out the small and mid caps where anchoring operates.
  - P4 to P6: the equal-weighted result leans toward microcaps and fails at 2x costs.
- Recomputation: +0.33%/month (t 2.14) starting 2001; +0.13 (t 0.81) starting 1996 (V089); top-500 net t 1.07 (V028).
- Resolution: open on the weight (PX-T-03). Both sides agree there is no standalone card.

**D8. Do classic technical rules survive in any form, and is trend protection or alpha?**
- Positions:
  - P2: no robust out-of-sample net support after the late 1980s; four slow constructs survive as features; index trend is display-only.
  - P7: crypto (2010-22), FX in the 1970s-80s and diversified futures earned credible net premia and then decayed; the canon reduces to primitives.
  - P4: 7,846 DJIA rules show zero outperformers after 1962; profits survive only in young markets.
- Reviewer challenges:
  - P7 to P2: would P2's family gate have blocked C3? Answer: the family test governs selection among variants and does not rerun a PASS.
  - P2 to P7: CTREND is long-short and pre-ETF.
- Recomputation: MCC, Shiller autocorrelation and SMA10 MATCH (V022-V024); the labs' SPA p-values are 0.88 (KOSPI) and 0.82-0.97 (SPY).
- Resolution: consensus PC-T-22 to PC-T-25. The surviving forms are diversified long-lookback futures trend (alpha 1), crypto trend C3 (alpha 3), and the 52-week high, MA distance and overhang as features.

**D9. Should there be an ML combiner now or later, and may it interact macro with signals?**
- Positions:
  - P5: build L0/L1 now, run gradient boosting and neural nets as shadows, drop L5, exclude macro × characteristic terms.
  - P4 (reviewer): endorses, and adds that every hyperparameter configuration counts toward the deflated Sharpe and that shadow results never enter displayed exposure.
  - P7 (second reader): the best ML-on-indicators evidence is crypto CTREND; Lorentzian-style community scripts are DO-NOT-BUILD.
- Recomputation: V069-V078 MATCH.
- Resolution: consensus PC-T-30. Excluding macro interactions protects the macro rule that macro variables size risk and never direct it.

**D10. Which gate amendments should be adopted?**
- Positions:
  - P4: family SPA/StepM/FDR, tiered hurdles, CPCV, a sealed holdout, bucket costs, a long-only primary statistic, an alpha haircut, step 8 as report-only, program-wide Benjamini-Hochberg.
  - P2: the family gate F0-F7.
  - P1: the attribution block, a Jensen's-alpha step 5 for cards with beta not equal to 1, no loosening, and the power calculation.
  - P5: the leakage checklist and trial counts.
  - P6: the Korea constraints.
- Reviewer challenge (P3 to P4): a 0.3 alpha haircut in post-publication windows would raise the displayed numbers relative to today's 60%; is that loosening? P4's answer: step 9 is report-only, so the gate is not loosened, but the display matters to users.
- Recomputation:
  - P4's binomial false-pass arithmetic, the Bonferroni test of C3 (t 3.49) and the deflated-Sharpe required t all MATCH; the Lo-SE illustration is a MISMATCH with no consequence.
  - The round-2 simulation (V065, V109) puts step 8's zero-Sharpe false-pass rate at 24-31%, the joint false-pass rate at 0.5%, and shows that 10-session blocks are too short. The binding constraint is power, not size.
- Resolution: consensus additions are in section 5.1. Still contested: PX-T-04 (haircut), PX-T-05 (step 8), PX-T-06 (CPCV and holdout), PX-T-07 (cost buckets).

**D11. What should QUANTGEN do with the TradingView/CMT canon?**
- Positions:
  - P7: no rigorous out-of-sample net test found for Ichimoku, Supertrend, Squeeze, UT Bot, WaveTrend, Connors RSI(2), TD Sequential, Wyckoff, Elliott/Fibonacci, CANSLIM/VCP or Lorentzian Classification; more than 95% of indicators repaint; port the logic into primitives.
  - P4: zero default costs; N >= 100; the win-rate fallacy.
  - P2: oscillator families fail the Reality Check on SPY.
- Reviewer challenge (P2 to P7): "no test found" is absence of evidence under an exhausted search budget. P7 agreed to label it that way.
- Recomputation: the TradingView documentation matches (V106). The labs found Connors RSI(2) and Bollinger mean reversion negative at 50 bp on SPY, and with KOSPI CAGRs of 2.4-2.8% against 7.2% for buy-and-hold.
- Resolution: consensus PC-T-29.

**D12. Crypto short-horizon momentum vs the prior design's crypto reversal weight of 2.**
- Positions:
  - P7: 1- to 4-week cross-sectional momentum is priced (Liu-Tsyvinski-Wu) but contested (Grobys-Sapkota find nothing); short-term reversal 2 → 0-1; CTREND is a strong BACKLOG item; split C3 at the ETF launch.
  - P2: keep C3 and use price/MA neighbours in its plateau test.
- Reviewer challenge (P2 to P7): Liu-Tsyvinski-Wu is pre-2019 and limited by shorting; CTREND is long-short.
- Recomputation: Liu-Tsyvinski-Wu and Detzel MATCH; CTREND's numbers UNVERIFIABLE.
- Resolution: consensus PC-T-27 and PC-T-28; PR-T-08.

**D13. Per-factor decay haircuts and the other decay anchors.**
- Positions:
  - Context brief: Ilmanen per-factor figures of -49% / -23% / -18%.
  - P3 flagged that AQR reports a 30% average and that the per-factor numbers were not re-verified.
  - P4: haircuts of 0.5 or 0.3; Chen-Velikov 4 bp.
  - P3 and P5: 8 bp.
- Recomputation: V107 (the AQR page gives only the 30% average); V008 and V045 (4 bp published vs 8 bp in the working paper).
- Resolution: PR-T-12 and PR-T-13. The planning haircut stays contested (PX-T-10).

**D14. Should Korean net issuance be the first Korean fundamental card?**
- Positions: P3: BUILD-candidate KR-ISS, information ratio 0.84 over the full sample and 0.42 recently, REVISE plausible. P1 (reviewer) asked for an independent replication and a cap-weighted view.
- Recomputation (V046-V048):
  - Sign and decay reproduce.
  - Full-sample information ratio is about 0.5, not 0.84; 2017-26 is 0.35-0.38.
  - About 0 at 70 bp in 2017-26.
  - About 0 value-weighted.
  - Round 2's exclusion version (drop share growth above 10%) gives +2.34%/yr on equal-weighted books (information ratio 0.65; 2016-26 1.43) and information ratio 0.15 capped value-weighted (V114).
- Resolution: P3 accepted the corrected ratio and the exclusion form. Consensus BUILD-candidate (PC-T-13), with REVISE the expected verdict.

---

## 7. Verification summary

**Counts.** 118 numbers re-checked: 83 MATCH, 24 TRACED-NOTE, 8 MISMATCH, 3 UNVERIFIABLE.
- 57 by re-opening a source (47 distinct fetches).
- 51 by the chair's local recomputation or arithmetic (9 scripts).
- 10 (V109-V118) against the round-2 lab's independent runs.

| Paper | MATCH | TRACED-NOTE | MISMATCH | UNVERIFIABLE | Total |
|---|---|---|---|---|---|
| P1 | 17 | 4 | 1 | 0 | 22 |
| P2 | 11 | 4 | 2 | 0 | 17 |
| P3 | 12 | 4 | 2 | 0 | 18 |
| P4 | 13 | 3 | 1 | 0 | 17 |
| P5 | 9 | 2 | 0 | 0 | 11 |
| P6 | 14 | 6 | 2 | 1 | 23 |
| P7 | 7 | 0 | 0 | 1 | 8 |
| Context anchors | 0 | 1 | 0 | 1 | 2 |
| **All** | **83** | **24** | **8** | **3** | **118** |

**Every MISMATCH and its correction.**
1. **V018 (P1's Korea momentum row):** the brief's premise "negative in high-turnover stocks" is replaced by +0.78%/month (t 2.57) all caps and +1.22 (t 3.26) excluding microcaps.
2. **V029 (P2-C15):** "max drawdown -23.7% vs -74.1%" is really the worst monthly return, -23.66% vs -74.06%.
3. **V032 (P2-C19):** the volume-filtered weekly reversal of 0.44%/week gross is 0.14-0.26%/week (top 500, 1996-2026), and -0.05 to +0.31%/week across designs for 2001-26; net it is always negative.
4. **V046 (P3-C20):** issuance long-short Sharpe of 1.31 / 1.04 / 0.78 (gross / 35 bp / 70 bp) is 0.99-1.01 / 0.76-0.79 / 0.54-0.56.
5. **V047 (P3-C20):** the long-only net information ratio of 0.84 is 0.48-0.54. The return of about 2%/yr matches; the tracking error is higher.
6. **V063 (P4-C22):** the SE of 0.188 for Sharpe 1.5 over 60 months is about 0.47 annualised.
7. **V083 (context anchor):** "-2.95%/month" Korean reversal is a Fama-MacBeth slope.
8. **V096 (P6-C26):** Corwin-Schultz spreads of 39-79 bp are not reproducible (22-57 bp or 99-117 bp by convention); calibrate on KIS quotes.

**UNVERIFIABLE.**
- V080, Griffin-Ji-Martin PDF: the server returned HTTP 500.
- V101, CTREND: numbers not on the abstract page; the qualitative claims are confirmed.
- V107, Ilmanen per-factor haircuts: AQR's page gives only the 30% average.

**Fetch limits.**
- The web-search budget was exhausted, so only known URLs were fetched.
- Several fetches answered from abstracts only. Martineau's microcap date, the JKP replication rates, the MSCI factsheet's 2013 row, and BIS's carry Sharpe and liquidation share were not visible.
- WebFetch answers through a summarising model. One answer (AQR trend: 1.2%) was wrong and was corrected by a targeted re-query of Exhibit 1 (0.4%). Before any number goes into the public QUANTGEN card text, it should be re-read from the PDF table.

**Reviewer verdicts on all 209 claims** (`prof_cross_exam_verdicts.csv`): 98 CONFIRMED, 17 QUALIFIED, 0 REFUTED, 94 UNVERIFIED. UNVERIFIED means not re-checked in this round and not contradicted.

| Paper | CONFIRMED | QUALIFIED | UNVERIFIED |
|---|---|---|---|
| P1 | 16 | 2 | 12 |
| P2 | 15 | 3 | 13 |
| P3 | 16 | 3 | 11 |
| P4 | 17 | 3 | 10 |
| P5 | 10 | 2 | 18 |
| P6 | 13 | 4 | 11 |
| P7 | 11 | 0 | 19 |

The 17 QUALIFIED claims: P1-C26, C27; P2-C09, C15, C19; P3-C20, C23, C25; P4-C22, C23, C27; P5-C12, C21; P6-C09, C11, C12, C26.

**Independence note.** P4-C29 cites an executives' quick-check file. The chair did not open it; the 2026 crash numbers were recomputed from the KR lab's daily series instead (V067).

---

## 8. Round-2 data-lab status

Both round-2 summaries were present before this resolution was finalised: `/home/claude/datalab/r2/R2_KR_summary.md` and `/home/claude/datalab/r2/R2_IDX_summary.md` (2026-10-03). Only their lab results were used. The lab's reproductions of executives' claims were not used to form professors' positions, keeping the panels independent.

| Dispute / item | Round-2 evidence | Effect on this resolution |
|---|---|---|
| D1 / PR-T-01 Korean momentum sign | Eom design +1.43%/month (t 3.3) all caps; the KJFS sign appears only with unadjusted closes (-11.4%/month); high-turnover winners -11.6%/yr long-only; 2015-07 to 2024-12 bad for every momentum construction | PR-T-01 strengthened (mechanism found); PC-T-09 adds a rule to exclude high-turnover / lottery names from momentum books |
| PX-T-11 12-7 card | 12-7 net Sharpe 0.20 (1996-2026, same as 12-1); 2016-26 -0.01; P6's 2001-start deciles confirmed | Chair ruling unchanged (Tier A card allowed, expected REJECT/REVISE) |
| PC-T-07 lottery exclusion | Equal-weighted book +3.08%/yr (IR 1.53), 7/8 indicative gate steps (REVISE); capped value-weighted REVISE; top 200 REJECT | Weight 3 restricted to equal-weighted / small-mid books |
| PC-T-13 issuance | Exclusion version (share growth > 10%): equal-weighted information ratio 0.65; capped value-weighted 0.15 | Exclusion form preferred; expected REVISE |
| PC-T-10 / PX-T-09 crash controls | Volatility scaling cut exposure before 2026-06-23 (0.55 / 0.27); Daniel-Moskowitz gate never fired; full-sample Sharpe up, 2016-26 down | Resolved into PC-T-10; only the 52-week-high-neutral construction remains open (BACKLOG) |
| PC-T-06 reversal | Value-weighted without microcaps: about 0 gross, negative net after 2005 | Confirmed |
| PC-T-08 low volatility | No significant alpha; beat the value-weighted market in 7/7 crash windows; lagged 9/10 rebounds | Recast as a protective candidate (protective 2) |
| PC-T-23 index trend | KOSPI 20% volatility target passes the protective class from starts up to 2006, with a positive drawdown gain at every start; trend is fragile (REJECT from 2011 starts), INSUFFICIENT DATA for SMA200 and the 12-month sign; SPY at 50 bp fails; Shiller averaging inflates trend Sharpe by +0.10 to +0.25 | Trend protective weight 1, volatility target 2; a floored-overlay finding is flagged for synthesis |
| PX-T-05 step 8; PC-T-31/32 gate power and size | Step 8 false pass 24-31% at true Sharpe 0; joint 0.5% at 10 years; 10-session blocks too short; 50% / 80% power for Sharpe 0.4 at 15.8 / 40.3 years | Step-8 numbers corrected; block-length rule reinforced; "do not loosen" reinforced (power, not size, is the binding problem) |

Still not covered by round 2: Korean value, quality and earnings drift (no point-in-time fundamentals); cost-bucket calibration (no KIS quotes); the 52-week-high-neutral construction and capital-gains overhang on KRX; the full gate-size simulation including the search steps (1, 4 and 7).

---

## 9. Gaps

- **No Korean fundamentals in the lab.** Korean value, quality and earnings drift (PX-T-01, PX-T-02, PC-T-12) cannot be tested until an OpenDART point-in-time store exists, and that store only covers 2015 onward.
- **No KIS quote snapshots.** The cost buckets are uncalibrated (PX-T-07); Corwin-Schultz is too convention-sensitive to substitute.
- **Price impact is not modelled,** which flatters equal-weighted small-cap results (lottery exclusion, issuance, 52-week high).
- **Dividends are excluded** from KRX returns. Low-volatility, value and low-beta long legs are understated by roughly 1-2%/yr. The Korean security-market-line test also has no risk-free rate.
- **French factors end in 2017/2018 locally.** Post-2018 factor claims rest on the French web page and index factsheets; the claim "US momentum Sharpe 0.02 since 2008" is verified only to 2017.
- **94 claims were not re-checked,** especially P5's ML literature beyond the headline papers, P7's crypto literature, and P6's Korean-journal flow, short-sale-regime and price-limit papers.
- **The 52-week-high-neutral momentum construction** (PX-T-09) and **the gate's size under the null including the search steps** (P4 D14 with steps 1, 4 and 7) remain untested. Round 2 simulated only steps 2, 3, 5 and 8.
- **Round-2 verdicts are indicative and in-sample.** The exclusion-screen gate run (7/8 steps) and the protective-class verdicts are start-date sensitive (section 3 of R2_IDX_summary.md). The labs have now seen 1996-2026 for every family discussed, so only prospective incubation is truly out of sample.
- **The 12-7 momentum and 52-week-high results are start-date sensitive** (1996 vs 2001). Any pre-registration must fix the start before the test, and the labs have already seen both windows.
- **The panel did not review India,** and reviewed Taiwan, China A and EM only through P6 (and P1 for EM). Those rows are priors without data paths.
- **Three sources were unreachable or silent** (Griffin-Ji-Martin, CTREND numbers, Ilmanen's per-factor table).
