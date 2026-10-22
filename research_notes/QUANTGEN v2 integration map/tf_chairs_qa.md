# tf_chairs_qa — round-2 chair resolutions + independent QA (tech-fund programme)

Digest for the QUANTGEN v2.0 build. Read-only extraction; nothing here is a gate result.

**Sources (all under `QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/`)** and citation keys used below:

| Key | File | Lines read |
|---|---|---|
| `P:L n` | `research_notes/R2_PROF_chair_resolution.md` | 1-912 (complete) |
| `E:L n` | `research_notes/R2_EXEC_chair_resolution.md` | 1-1101 (complete) |
| `Q:L n` | `qa/QA_report.md` | 1-315 (complete; long lines 230/292/295 printed in full) |
| `QR:L n` | `qa/QA_recomputation.md` | 1-74 (complete) |
| `LOG#n` | `qa/qa_edit_log.json` | entry n (1-based) of 107; structure + counts |
| `README` | `README.md` | 1-10 |
| look-ups only | `research_notes/R3_TF_neural_link.md` (`R3:L n`), `research_notes/P2_technical_analysis_evidence.md` (`P2:L n`), `datalab/R2_KR_summary.md` (`KR2:L n`), `datalab/R2_IDX_summary.md` (`IDX2:L n`), `datalab/verification/exec_verification_log.csv` (`XLOG row n`), `datalab/results/r3/*.csv`, `datalab/results/r2_kr/r2_kr_excl_gate.csv` | grep / single lines |

**Standing caveats (bind every number below).**
- All lab numbers are in-sample computations on price returns without dividends, not runs of QUANTGEN's gate (README L10; P:L18, P:L909; E:L25, E:L1098). "Indicative PASS/REVISE readings are not gate results" (E:L1098).
- Chairs and panelists are fictional composite personas (P:L5; E:L3). The two panels were kept independent (P:L7; E:L5); **R3 is the reconciliation** — where sections A and B disagree, R3's ruling governs (see section E for the list).
- Macro decisions P0-P10, R-03..R-15, §8.7 were not re-litigated by either chair (E:L10; P:L472, P:L632).
- Paths printed as `/home/claude/...` do not exist locally. Local equivalents: `datalab/{kr,r2/kr,r2/idx,us}/results` → `datalab/results/{kr,r2_kr,r2_idx,us}`; `datalab/r3/` → `datalab/results/r3/`; `r2/verification/` → `datalab/verification/`.

---

## A. Professors' chair resolution (R2_PROF)

### A.0 Status
- 209 round-1 claims → 60 propositions; 118 numbers re-checked: 83 MATCH, 24 TRACED-NOTE, 8 MISMATCH, 3 UNVERIFIABLE (P:L24, P:L825). Status codes verbatim: `MATCH`, `MISMATCH`, `TRACED-NOTE`, `UNVERIFIABLE` (P:L18).
- Implication codes verbatim: `BUILD`, `BACKLOG`, `DROP`, `CONTEXT`, `GOVERNANCE` (P:L54); also used: `BUILD-candidate`, `DO-NOT-BUILD`.
- Reviewer verdicts on 209 claims: 98 CONFIRMED, 17 QUALIFIED, 0 REFUTED, 94 UNVERIFIED (P:L862).
- "The gate must not be loosened"; most new cards are expected to return `REVISE` or `INSUFFICIENT DATA` (P:L48, P:L633).

### A.1 Consensus items PC-T-01..34 (implication + what an implementer must encode)

| ID | Ruling (verbatim-critical parts) | Code | Lines |
|---|---|---|---|
| PC-T-01 | CAPM beta = risk/attribution tool, not a return signal. **Every card gets an attribution block** (def. in A.5 #4). Label a card `"factor tilt"` when CAPM alpha is significant but factor alpha is not | GOVERNANCE/BUILD | P:L58-65 |
| PC-T-02 | Factor zoo mostly noise; construction choices = hidden multiple testing. **Tiered hurdles** (A.5 #6). Always report equal-weighted and capped value-weighted results together | GOVERNANCE | P:L67-74 |
| PC-T-03 | Decay: US −26% OOS / −58% post-publication; KRX local decay measured (1-month reversal 1.12 / 0.27 / 0.08 %/month in 2001-09 / 2010-19 / 2020-26). Plan with haircuts; measure KRX decay locally | CONTEXT | P:L76-85 |
| PC-T-04 | Average anomaly ≈ 4 bp/month net (not 8). Only one-sided turnover < 50%/month survives. **DROP** high-turnover stock signals at 35-50 bp/side. **BUILD banding as default: enter in the top 20%, exit below the top 40%** | DROP + BUILD | P:L87-94 |
| PC-T-05 | **Primary statistic = long-only net excess over a same-universe equal-weighted benchmark**; long-short is a diagnostic. Report: short leg's share of L/S profit; results by short-sale regime; sign of EW vs capped VW (**sign split ⇒ REVISE**) | GOVERNANCE | P:L96-103 |
| PC-T-06 | Korean short-term reversal (1 day–1 month, with/without volume filter) is not a stock card at 35 bp. Alpha 3 → 0. Keep a `"do not buy last month's top-decile winners"` guard and a normalised reversal feature. Cheaper-venue version BACKLOG only | DROP | P:L105-115 |
| PC-T-07 | Korean lottery/low-risk family (MAX, volatility, turnover; pairwise corr 0.67-0.90) → **long-only exclusion screen, protective weight 3 for EW and small-mid books**; cap-weighted: default hygiene filter only; top 200: adds nothing. **Count every threshold variant as a trial.** Chair composite: ranks of 63-day volatility, 21-day MAX, 21-day turnover; worst decile dropped (`prof_v02`). R2 horse race: 176 trials, F4 = P6 composite; EW +3.08%/yr net 35 (IR 1.53, boot p 0.0005, 90% of years); 7 of 8 indicative steps, pooled DSR 0.94 → REVISE; capped VW +0.85%/yr REVISE; top 200 +0.49%/yr REJECT | BUILD-candidate (P6-X1) | P:L117-129 |
| PC-T-08 | Low-vol / low-beta tilt is not long-only alpha in Korea (alpha 1 EW, 0 cap-weighted). Korean low-vol = protective candidate "judged drawdown-first with Sharpe non-inferiority (protective 2), not on alpha". US/Europe alpha 1, protective 2. BAB = BACKLOG, only value-weighted beta-neutral form | DROP (tilt) | P:L131-141 |
| PC-T-09 | No standalone Korean 12-1 card. Momentum only as composite feature weight 1 (12-7 or 52-week high). **Any momentum book must exclude the highest-turnover or lottery names.** "Volatility scaling, concentration caps and a replay of the 2026 crash are mandatory." | BACKLOG (feature) / DROP (card) | P:L143-156 |
| PC-T-10 | Korean momentum crashes are winner-led after melt-ups. Keep vol scaling + Daniel-Moskowitz gate as mandatory risk controls on any Korean momentum feature; they do not make 12-1 a PASS candidate. D-M gate on KOSPI was off on 2026-06-22, fired 9 times in 30 years; own-vol scaling had cut exposure to 0.55 (EW) / 0.27 (VW) | CONTEXT + GOVERNANCE | P:L158-169 |
| PC-T-11 | Size is not a signal. Keep as risk control (microcap exclusion; SMB in attribution) | DROP | P:L171-178 |
| PC-T-12 | Korean value(+quality) composite needs a PIT store and a Value-up split. Value weight 2 → 3 only if a PIT test passes and survives a split at **2024-02-26**. "All Korean value, payout and cancellation tests are split there." OpenDART statements only from 2015 | BACKLOG (KR-VQ) | P:L180-187 |
| PC-T-13 | Korean net issuance (avoid heavy issuers) = first Korean fundamental card buildable from KRX data alone, as long-only exclusion or tilt in EW or capped books. **Count at least 10 trials.** Expected verdict REVISE (2x-cost step fails over 2017-26). Measure overlap with the lottery screen. R2 exclusion version: drop names whose share count grew more than 10% over 252 sessions → EW +2.34%/yr net 35 (IR 0.65; 2016-26 IR 1.43); capped VW IR 0.15. Long-only IR is ~0.5 (0.48-0.54), **not 0.84** | BUILD-candidate (KR-ISS) | P:L189-200 |
| PC-T-14 | **Korean market structure encoded in every Korean card**: tag months by short-sale regime; no fills at locked limits; capped and ex-Samsung/SK hynix benchmarks; apply the tax rate in force each year. Dates/rates in A.6 | GOVERNANCE | P:L202-212 |
| PC-T-15 | PIT + delisting: a fundamental becomes available at `rcept_dt` + 1 session, **first-filed values**. Delisting stress cases −30% and −100%. Korean fundamental cards should expect INSUFFICIENT DATA. `rcept_dt` carries no time of day; OpenDART statements start business year 2015; KR lab bounds delisting bias at 1.4%/yr | GOVERNANCE/BUILD | P:L214-220 |
| PC-T-16 | Quality 3 → 2 (US/Europe), composite leg only, "held at 1.0x under the macro rule"; not a crash hedge | BUILD (leg of US-VQ) | P:L222-229 |
| PC-T-17 | US value ≤ 1 standalone, only inside composite; timely price, intangibles-adjusted book, 15+ year windows | BACKLOG | P:L231-238 |
| PC-T-18 | US-VQ (value + profitability + investment + issuance) = US fundamental BUILD-candidate. EDGAR acceptance + 1 session, sector neutrality, bands; combine with momentum at sleeve level, not as a single card. Expect REVISE before PASS (needs 15+ years XBRL) | BUILD-candidate | P:L240-247 |
| PC-T-19 | US stock momentum 3 → 1 (Europe 3 → 2, EM 3 → 2); only composite/ETF leg with macro vol scaling + bear-state gate | BACKLOG | P:L249-256 |
| PC-T-20 | US PEAD and standalone accounting anomalies: DROP as cards (US earnings drift 2 → 0). M-score/distress only as exclusion screens; earnings-announcement premium BACKLOG | DROP | P:L258-265 |
| PC-T-21 | CAPE / Fed model: context only. No multiplier | CONTEXT | P:L267-274 |
| PC-T-22 | Classic technical rules DO-NOT-BUILD as standalone cards: single-index MA/filter/breakout timing, oscillators, candlesticks, chart patterns, Fibonacci, Elliott waves, stock-level MA timing. KOSDAQ-segment rule families only through the family gate (BACKLOG). KR lab 303 KOSPI rules SPA p 0.880; US lab 322 SPY rules SPA p 0.82-0.97 | DROP / DO-NOT-BUILD | P:L276-284 |
| PC-T-23 | Index trend timing = protective overlay (alpha 0). "Only an overlay multiplier in [0.5, 1.0] (macro rule)." KOSPI 20% vol target is the robust protective rule. Flag for synthesis: flooring trend at 0.5 gave back absolute slow-bear protection (KOSPI multi-speed MDD −34.1% unfloored vs −39.2% / −44.8% floored); floored trend × vol target passed every check | CONTEXT/protective | P:L286-299 |
| PC-T-24 | Oscillators = repackaged short-term reversal (RSI14 vs 1-month reversal corr 0.92; %B 0.87). **BUILD a feature library**: trend/position, reversal, range volatility, abnormal volume, 52-week high, MA distance, capital-gains overhang. Every variant counts as a trial. Chart-image CNNs / intraday S/R = research BACKLOG | BUILD (features) | P:L301-308 |
| PC-T-25 | Diversified futures TS-momentum alpha weight 1 (broad, long-lookback books only), benchmarked against volatility-scaled buy-and-hold. B3 REJECT stands | — | P:L310-318 |
| PC-T-26 | G10 FX technical rules DROP (V3 REJECT stands). One slow-trend test on USD/KRW futures = BACKLOG | DROP | P:L320-324 |
| PC-T-27 | Keep crypto trend C3. **Split at 2024-01-10; test daily-bar cut times 00:00 UTC, 00:00 KST, 21:00 UTC; count three extra trials** | BUILD (keep) + GOVERNANCE | P:L326-332 |
| PC-T-28 | Crypto cross-section: short horizons = momentum. Crypto ST reversal 2 → 0 pending test; XS momentum 1; CTREND-lite composite (long-only vs BTC, 10/20 bp) BACKLOG; down-only funding/basis multiplier in [0.5, 1.0] BACKLOG; calendar rules DROP | mixed | P:L334-346 |
| PC-T-29 | TradingView/CMT/retail backtests are unverified claims. Never import platform metrics. Port via protocol: pure function of OHLCV at t, a shift test, mapping to the primitives, **N >= 100 trials for TradingView-sourced ideas** | GOVERNANCE/DROP | P:L348-355 |
| PC-T-30 | ML ladder. **BUILD L0** (equal-weight rank composite with signs fixed in advance), **L1** (ridge or rolling Fama-MacBeth shrunk toward L0), and the ML harness (**purge and embargo of at least 63 sessions; at most 12 configurations per model family**). BACKLOG L3 gradient boosting and L4 MLP as non-gating shadows. DROP L5 for KRX. **No macro × characteristic interactions** | BUILD / BACKLOG / DROP | P:L357-366 |
| PC-T-31 | Gate additions (A.5). With 10-session blocks, step 2 falsely passes 6.9-8.0% of zero-Sharpe strategies (nominal 5%); step 5 rejects 12.8-13.7% at nominal 10% | GOVERNANCE | P:L368-376 |
| PC-T-32 | Gate structurally underpowered for tilts with net IR 0.2-0.4. Report minimum track record length; shrink Tier A KRX estimates toward global cluster evidence. Never loosen | GOVERNANCE | P:L378-390 |
| PC-T-33 | Markets without a data path are context only (Japan value 3, momentum 0 standalone; China A, Taiwan momentum 0) | CONTEXT | P:L392-398 |
| PC-T-34 | Korean investor flow 3 → 1. Log flow as a state variable; open-leg test BACKLOG | CONTEXT | P:L400-406 |

### A.2 Contested items PX-T-01..11 (chair ruling = what to encode until R3 says otherwise)

| ID | Dispute | Chair ruling | Lines |
|---|---|---|---|
| PX-T-01 | KR quality weight 1 (P1) vs 2 (P3/P6/P5) | **2 inside the value-quality composite only; no standalone quality card.** Settle with OpenDART test. BACKLOG | P:L410-413 |
| PX-T-02 | KR earnings drift 1 (P3) vs 2 (P6); prior 3 | **1** until a test timestamped by DART filing (CAR[-1,+1], entry at `rcept_dt` + 1 session) passes at 2x costs in the top two size terciles; then 2. BACKLOG | P:L415-421 |
| PX-T-03 | KR 52-week high: weight-2 tilt vs weight-1 feature | **Weight 1 as a feature; no standalone card.** May be tested once inside P6-X2 as a pre-registered single-configuration (Tier A) test. Start-date sensitive: +0.33%/month (t 2.14) from 2001-03, +0.13%/month (t 0.81) from 1996-03 | P:L423-430 |
| PX-T-04 | Step-9 haircut: flat 60% Sharpe haircut vs alpha haircut 0.5 / 0.3 | **Show both haircuts for one release. Step 9 stays report-only.** Decide at synthesis. (See ambiguity F-1: the "60%" wording is the ×0.4 error.) | P:L432-437 |
| PX-T-05 | Step 8 (≥ 60% of calendar years positive): keep vs report-only | **Keep step 8 and add "positive in at least 2 of 3 subperiods" plus a short-sale regime split; both are required.** Revisit after the full gate-size simulation (steps 1, 4, 7) | P:L439-445 |
| PX-T-06 | CPCV gating; sealed 2019-2026 holdout; family SPA threshold | **CPCV reported but not gating. Contamination log mandatory now; incubation clock starts 2026-10-01. New technical families use the stricter SPA consistent p <= 0.05; Tier A single-configuration replications skip the family test.** Historical holdout is used up for: 12-1 and 6-1 momentum, 1-month reversal, volatility, MAX, turnover, 52-week high, price/SMA200, RSI, %B and 600+ index rules (1996-2026) | P:L447-455 |
| PX-T-07 | KR cost calibration: P4 buckets (8/15/30/50 bp non-tax per side by 20-day traded value, plus tax) vs P6 tiers (35 bp top 20% of caps + 27-39 bp half-spreads below) | **Keep flat 35/70 bp (tax-inclusive) as the binding base until spreads are calibrated on KIS quotes. Report bucket costs alongside. A bucket may raise a name's cost, never lower it below 35 bp, until calibration is done.** Corwin-Schultz is not a calibration source (22-57 bp or 99-117 bp by convention) | P:L457-462 |
| PX-T-08 | Japan/EM levels | Japan quality 1; Japan momentum 0 standalone (allowed as hedge leg of value-momentum composite); EM value 2, quality 2. CONTEXT (no data path) | P:L464-467 |
| PX-T-09 | 52-week-high-neutral momentum (WML*) or concentration cap vs KRX crash risk | Own-vol scaling point resolved into PC-T-10. WML* + Samsung/SK hynix caps untested on KRX → BACKLOG (P2 DC-J) | P:L469-472 |
| PX-T-10 | Planning decay haircuts per factor | Plan with **0.5** (in-sample or overlapping the discovery sample) or **0.3** (fully post-publication); **0.75** for drift-like signals; replace planning values with measured local decay where 20+ years of data exist; stop attributing per-factor numbers to Ilmanen et al. | P:L474-481 |
| PX-T-11 | KR 12-7 momentum: own card vs feature only | **Allowed as one pre-registered Tier A card with volatility scaling and caps.** Expected REJECT or REVISE (step 6 fails after 2010). Feature weight 1 either way. Net Sharpe 0.60 (from 2001) / 0.19 (from 1996) at 35 bp; negative at 70 bp after 2010 | P:L483-491 |

### A.3 Refuted / withdrawn PR-T-01..16 (P:L495-512) — numbers that must NOT be coded as facts

| ID | Dead statement | Replacement |
|---|---|---|
| PR-T-01 | "Korean 12-1 momentum is negative in high-turnover stocks (−6.13%/month, t −4.76)" | +0.58 to +1.66%/month on adjusted prices; negative sign only with unadjusted closes around capital reductions / reverse splits (−11.4%/month; 0.09% of stock-days). Korea XS-mom 1 as feature |
| PR-T-02 | "Korean 1-month reversal −2.95%/month (t −3.77, 1999-2021)" | −2.950 is a Fama-MacBeth slope; spreads 0.52-0.86%/month gross (2001-26, EW), ~0 since 2010, negative net |
| PR-T-03 | Volume-filtered 5-day reversal, Korea weight 3 | Weight 0; net −0.92 to −1.33%/week |
| PR-T-04 | Quality "most consistent" (weight 3) | Weight 2 |
| PR-T-05 | Korea low-vol 2 as a long-only tilt | Exclusion screen instead |
| PR-T-06 | TS momentum "0.4-0.8 per asset, about 1.0 diversified" | Plan 0.0-0.3 diversified (post-2009) |
| PR-T-07 | Korea flow 3 and earnings drift 3 "strong" | Flow 1; drift 1 (contested 1-2) |
| PR-T-08 | Crypto ST reversal weight 2 | 0 pending a test |
| PR-T-09 | Volume filter "selects continuation" | Withdrawn as general statement |
| PR-T-10 | WML* "max drawdown −23.7% vs −74.1%" | These are worst monthly returns (−23.66% vs −74.06%) |
| PR-T-11 | KR-ISS long-only net IR 0.84 [0.46, 1.25] | ~0.5 (0.48-0.54); 2017-26 0.35-0.38 |
| PR-T-12 | "Average anomaly ≈ 8 bp/month net" | 4 bp (204 anomalies, JFQA 2023) |
| PR-T-13 | Ilmanen per-factor haircuts −49% / −23% / −18% | Only a 30% average OOS drop is verifiable |
| PR-T-14 | Corwin-Schultz 39-79 bp ⇒ "35 bp understates the bottom 60%" | Withdrawn pending quote calibration |
| PR-T-15 | SE 0.188 for Sharpe 1.5 over 60 months | Annualised SE ≈ 0.47 |
| PR-T-16 | Vol-scaled sizing adds +0.1 to +0.3 Sharpe "on nearly every strategy" | Robust mainly for momentum and trend |

Further corrected anchors (P:L516-538) not already above: step-8 false pass is 24-31% at true Sharpe 0 (not 36-38%); "18 OOS years for Sharpe 0.4" = ~50% power at step 2 (80% needs ~37-43 years); Samsung + SK hynix share must always state date + denominator (35.1% 2025-12-30, 57.3% 2026-06-22, 52.6% 2026-09-29 of KOSPI common-share cap; MSCI Korea 60.8% Aug 2026); KR 52-week high and 12-7 results must always state the start date; "Trend following 2010-18: 0.4%/yr" is excess over T-bills (total 1.6%); "ChatGPT strategy unprofitable at 20 bp" = 20 bp round trip (10 bp per side).

### A.4 Consolidated weights (design priors, 0-3; "any weight of 2 or more still needs a PASS card"; protective uses "only within the macro band [0.5, 1.0] and never above 1.0x") (P:L544)

**Alpha, prior → professors (P:L548-559).** Column order: XS-mom | ST-rev | Value | Quality | Low-vol tilt | Flow | Earn. drift | TS-mom.

| Market | XS-mom | ST-rev | Value | Quality | Low-vol tilt | Flow | Earn. drift | TS-mom |
|---|---|---|---|---|---|---|---|---|
| US | 3→1 | 1→0 | 1→1 (composite only) | 3→2 | 2→1 | 1→1 (n.r.) | 2→0 | 3→0 (protective 2) |
| Europe | 3→2 | 1→0 | 2→2 | 3→2 | 2→1 | 1→1 (n.r.) | 2→2 (n.r.; ≤1 suggested) | 3→0 (protective 2) |
| Japan | 0→0 (value-paired hedge only) | 2→1 | 3→3 | 2→1 | 3→2 | 1→1 | 1→1 | 2→0 (protective 2) |
| **Korea** | 1→1 (12-7 / 52wH features only; no 12-1 card) | 3→0 | 2→2 (3 only after PIT test) | 1→2 (composite only) | 2→1 EW / 0 cap-weighted | 3→1 | 3→1 (P6: 2) | 2→0 (protective 2) |
| Taiwan | 1→0 | 3→2 | 1→2 | 1→1 | 1→1 | 3→1 | 2→2 | 2→0 (protective 2) |
| China A | 0→0 | 3→3 | 1→2 | 1→2 | 1→3 | 3→1 | 1→1 | 1→0 (protective 1) |
| India | 3 / 1 / 2 / 3 / 2 / 2 / 2 / 2 (n.r.; prior kept) | | | | | | | |
| EM | 3→2 | 1→1 | 2→2 | 2→2 | 1→2 | 2→1 | 1→1 | 3→0 (protective 2) |
| Crypto | 1→1 | 2→0 | 0 | 0 | 0 | 2→1 | 0 | 3→3 (C3) |
| Futures / FX | "weak"→0 | — | — | — | — | — | — | "strong"→1 broad long-lookback futures books; 0 G10 FX technical rules |

"protective 2" in TS-mom = combined index risk overlay: **volatility target at 2 and trend at 1** (P:L561).

**Protective uses (P:L565-574).**

| Use | Korea | US | Others |
|---|---|---|---|
| Lottery/low-risk exclusion (drop worst decile or quintile of a volatility + MAX + turnover composite) | 3 EW and small-mid books; 1 (hygiene) cap-weighted; 0 top 200 | 1 (untested) | Japan 1, China A 3, Taiwan 2, EM 2 |
| Heavy-issuer exclusion (net issuance) | 2 (EW or capped) | inside US-VQ | — |
| Index volatility target (macro rule; endorsed) | 2 | 1 (futures cost only) | — |
| Index trend overlay (SMA200, 10-month SMA, TSMOM, multi-speed vote) | 1 | 1 (futures cost only; INSUFFICIENT DATA) | 1-2 (n.r.) |
| Defensive low-vol / low-beta sleeve (drawdown-first, Sharpe non-inferiority or Jensen's alpha) | 2 | 2 | Europe 1-2, Japan 2 |
| ST-reversal guard (do not buy last month's top-decile winners) | 1 | 0 | — |
| Momentum crash controls | own-vol scaling, D-M gate, Samsung/SK hynix caps (macro); 2026 stress replay; exclude highest-turnover / lottery names | macro σ126 scaling plus D-M gate | — |
| Crypto funding/basis multiplier (down-only) | — | — | Crypto 1 (BACKLOG) |

**Feature-only families / candidates (P:L578-587).** 52-week-high nearness KR 1 / US 2 / Europe-Japan 1; 12-7 momentum KR 1 (Tier A card allowed); MA distance / trend factor KR 1 / US 2; capital-gains overhang KR 2 (to test) / US 1; value + quality composite KR 2 (KR-VQ; needs PIT) / US 2 (US-VQ); net issuance KR 2 (KR-ISS) / US 2 (inside US-VQ); CTREND-lite crypto 2 (provisional); size 0 everywhere (risk control only).

### A.5 Testing protocol and gate amendments — exact definitions (P:L603-644)

**5.1 Add (consensus).** Numbering is the source's.

1. **Family gate before the nine-step gate** (P:L606). Pre-register the whole rule family, its benchmark, costs and criterion. Test "no member beats the benchmark" with a **studentised SPA and the Reality Check (stationary bootstrap, at least 2,000 resamples)**. The family must reach **SPA consistent p <= 0.05 at 1x costs**. Then name survivors with **StepM or Romano-Wolf**, or control the **FDR at 10%** when combining rules, and require **persistence: positive out-of-sample net excess in at least 60% of walk-forward windows**. Tier A single-configuration replications skip it (P:L454). A PASS already granted is not rerun by the family test ("governs selection among variants", P:L759).
   - Underlying P2 design F0-F7 (P2:L622-647), for the fields the pre-registration must hold: **F0** family F = rule definitions × parameter grid × universes, K = |F|; benchmark = same-day buy-and-hold (timing rules) / vol-matched buy-and-hold (trend rules) / equal-weighted universe (cross-sectional rules); cost model = QUANTGEN rates at 1x and 2x; criterion = mean net excess return (Sharpe difference secondary); split = purged walk-forward 756/126, embargo = holding period. **F1** OOS walk-forward net excess series for all K rules; SPA + White's RC (P2 printed "mean block 10 sessions, B = 2,000" and p ≤ 0.10 — **overridden by the chair to p <= 0.05 and by the block rule in #10**); fail ⇒ whole family REJECTED, no member carried forward. **F2** stepwise SPA / Romano-Wolf at FWER 10%; FDR 10% (Bajgrowicz-Scaillet) if combining. **F3** persistence ≥ 60% of windows, positive Spearman correlation of IS and OOS ranks. **F4** DSR trials = K plus all earlier trials on the same data. **F5** plateau: at least 50% of parameter neighbours keep half the Sharpe. **F6** new XS technical factors: full-sample t ≥ 3.0 gross and t ≥ 2.0 net at 1x; last decade (2016-2026) net-positive at 1x; report subperiods 1996-2005, 2006-2015, 2016-2026. **F7** month-end prices only; decide at close t, trade at t+1, plus a t+2 robustness run; zero-pad KRX codes and include KOSDAQ GLOBAL; no fills on zero-volume days; long-only primary.
2. **Trial registry** (P:L607). Every family member, every revision and every data-lab quick-check look counts toward the deflated-Sharpe N. TradingView-sourced ideas carry **N >= 100**. A composite choosing k of n signals counts **n^k**. ML: at most **12 configurations per model family**, every configuration counts.
3. **Program-wide multiplicity control** (P:L608). **Benjamini-Hochberg at q = 0.10 per release, and Holm for displayed cards.** Re-score the existing 34 cards transparently rather than demoting them silently.
4. **Attribution block on every card** (P:L609; content P:L65): beta; Jensen's alpha against a beta-matched benchmark with Newey-West errors; FF5+UMD for US cards; local MKT/SMB/HML/RMWq/CMA/UMD plus a Samsung + SK hynix "SEMI" factor for KRX cards. Plus a **Jensen's-alpha t-test variant of step 5 for cards with beta not equal to 1, from the next pre-registered gate version (not retroactive)**. Sharpe difference: **Ledoit-Wolf studentised bootstrap**.
5. **Primary statistic for stock cards** (P:L610): **long-only daily net excess over the same-universe equal-weighted benchmark**. Report capped value-weighted results too (sign split ⇒ REVISE), long-short as a diagnostic, and the short leg's share.
6. **Tiered hurdles** (P:L611; P:L74): **Tier A t >= 2.0** (single-configuration replication of a published, internationally replicated anomaly with a mechanism); **Tier B t >= 3.0 plus the family SPA** (new signals); **Tier B+ t >= 3.4 (cross-sectional) or 3.8 (time-series alpha)** (more than 100 configurations or TradingView-sourced). All tiers also need **DSR >= 0.95, a Sharpe above 0 at 2x costs, and a plateau**.
7. **Korea encoding** (P:L612): short-sale regime tags; no fills at locked limits; **next-open entry for holding periods of 5 sessions or less**; the sell tax in force each year; a split at **2024-02-26**; capped and ex-Samsung/SK hynix benchmarks; universe hygiene (no preferred shares, SPACs, REITs, funds, warning-designated stocks, or prices under KRW 1,000).
8. **Point-in-time and delisting** (P:L613): availability at `rcept_dt` + 1 session with first-filed values; delisting stress at −30% and −100%; a check that KRX book-per-share is point-in-time.
9. **Power reporting** (P:L614): report the minimum track record length at the tier hurdle. **If it exceeds the available history, the verdict is INSUFFICIENT DATA, not REJECT.** Shrink Tier A estimates toward the global cluster evidence.
10. **Inference details** (P:L615): PSR and HAC t on net excess; **block length >= max(Politis-White, 2 x holding period)**; infer only on the concatenated out-of-sample path. (10-session blocks: step-2 false pass 6.9-8.0% vs nominal 5%; step-5 rejections ~13% vs nominal 10%, KOSPI-like returns.)
10a. **Protective cards are judged as protective cards** (P:L616). Index trend, volatility targets, low-volatility sleeves and exclusion screens on cap-weighted books are tested on protective-class checks: **max drawdown vs a static book with the same average exposure, tail exposure, Sharpe non-inferiority within −0.10, drawdown episodes, years, plateau, and sufficiency (enough independent de-risk signals)**. Never tested on step-5 outperformance alone. P1's Jensen's-alpha test is the alternative for cards with beta below 1.
11. **Stress reporting** (P:L617): worst rolling 21- and 63-session net excess, plus replays of 2008-09, 2020-03, 2025-01 to 2026-06 and 2026-06-23 to 07-30.
12. **Contamination log and incubation** (P:L618): list every family and date range already examined by the labs; for those, prospective incubation (**at least 252 sessions, clock starting 2026-10-01**) is the only clean OOS test.
13. **ML leakage checklist** (P:L619): purge and embargo of at least the label horizon (63 sessions); features ranked per date; no macro × characteristic interactions; LLM features only after the model's training cutoff or with point-in-time models.
14. **Porting protocol for TradingView/CMT logic** (P:L620): a pure function of OHLCV at t; a shift test; mapping to the F1-F10 primitives; every variant counted as a trial; costs set to QUANTGEN's rates.
15. **Crypto** (P:L621): pre-registered split at 2024-01-10 and a cut-time sensitivity test for C3.

**5.2 Change (contested)** (P:L623-627): step-9 both haircuts for one release; step 8 kept + "positive in at least 2 of 3 subperiods" + short-sale regime split; CPCV reported, not gating; flat 35/70 bp binding until KIS-quote calibration.

**5.3 Must not be loosened** (P:L629-636), verbatim list:
- Read-only by construction; decide at the close of t and earn from t+1; every result re-run at 2x costs.
- DSR >= 0.95 with every revision counted; PBO; plateau; pre-registration fixed before the test.
- Macro rules: macro variables size and never direct; overlay multipliers stay in [0.5, 1.0]; reversal and quality sleeves are held at 1.0x.
- The gate is not loosened because factor cards fail it.
- No cost bucket below the flat 35 bp is used to pass a card until calibration.
- No TradingView or other platform metric is imported, and no shadow ML result enters displayed exposure.
- No retroactive change to step 5 or to existing PASS verdicts; re-scoring is reported transparently.

**5.4 Consolidated protocol for a new KRX stock-level card** (P:L638-644):
```
1. pre-registration file, hashed. Fields: hypothesis, tier, mechanism, formula,
   at most 27 configurations, universe, rebalance and band, benchmark, cost model,
   primary statistic, hurdles, subperiods (1996-2005 / 2006-2015 / 2016-2026), incubation start
2. family test (5.1-1) if more than one configuration is tried
3. nine-step gate + 5.1 additions; primary statistic = long-only net excess vs the EW universe;
   must clear its tier hurdle at 35 bp AND keep a positive Sharpe at 70 bp
4. Korea reports: short-sale regimes, limit locks, Value-up split, capped and ex-mega-cap results,
   2026 stress replay, delisting stress
5. attribution block + haircut display (both versions until PX-T-04 is settled)
6. incubate prospectively before any exposure is displayed above the base allocation
```

### A.6 Korean market-structure constants as printed by the professors (P:L204-210)
- Short-sale bans: 2008-10 to 2009-05; 2011-08 to 2011-11; 2020-03-16 to 2021-05-02, then index stocks only until 2023-11-05; full ban 2023-11-06 to 2025-03-30. Resumed 2025-03-31 (NSDS, 105% collateral, 90-day repayment).
- Price limits ±30% since 2015-06-15.
- Sell tax: 0.20% from 2026-01-01; 0.15% in 2025; 0.30% in 2019.
- KOSDAQ up-limit closes: 51.1 per 10,000 stock-days in 2026 vs 24.5-26.8 in 2024-25.
- KOSPI −9.99% on 2026-06-23.

### A.7 Gate power / size numbers to display, not to tune (P:L381-388, P:L522-523, P:L894)
True Sharpe 0.4: 50% chance at step 2 after 15.8 years, 80% after 40.3. Nine counted trials: Sharpe 0.5 needs 39.5 years for 50% at step 3. IR 0.3 vs a 0.4-Sharpe benchmark: step 5 passes half the time after ~18 years, 80% only near 50. Joint false-pass of steps 2+3+5+8 at zero Sharpe: 0.5% at 10 years. Step 8 alone at zero Sharpe: 28-31% (iid), 24% (KOSPI-like) over 8-10 years; 16% over 20 years (iid). DSR required t: 3.17 for 9 configurations, 3.67 for 27 (P:L373). C3's benchmark-difference p 0.04 fails Bonferroni across 16 trading cards (threshold 0.006); its Sharpe-vs-zero t 3.49 survives (P:L371).

### A.8 Professors' gaps (P:L900-912)
No Korean fundamentals in the lab (OpenDART PIT store needed, 2015 onward only); no KIS quote snapshots; price impact not modelled (flatters EW small-cap results); dividends excluded (~1-2%/yr understatement of low-vol/value/low-beta long legs); no risk-free rate in the Korean SML test; French factors end 2017/2018 locally; 94 claims not re-checked; WML* and the full gate-size simulation (steps 1, 4, 7) untested; round-2 verdicts indicative, in-sample, start-date sensitive; India not reviewed.

---

## B. Executives' chair resolution (R2_EXEC)

### B.0 Status and labels
- 205 claims → 60 propositions X01-X60; 103 numbers re-checked: 77 MATCH, 12 MISMATCH, 11 TRACED-NOTE, 3 UNVERIFIABLE (E:L31-32, E:L1023). 28 consensus (EC-T), 14 contested (EX-T), 12 refuted/withdrawn (ER-T) (E:L37).
- Triage labels verbatim (E:L18-23): **`BUILD NOW`** (conventions, data layers, reporting; "A screen or card built now still feeds the displayed book only after it passes the gate (P7)"), **`FORWARD-SIM`** (forward-simulation book only; "it never feeds the displayed book"), **`BACKLOG`**, **`DROP`**, **`CONTEXT`**.
- Number conventions: `net35` = net of 35 bp per side; `net70` = the 2x stress case (E:L25).
- Two chair errors were found and fixed (vol-scaling warm-up; same-day-eligibility benchmark); no second independent re-run of the chair's scripts (E:L1076-1078, E:L1099).

### B.1 Conventions RX-01..RX-16 — "all BUILD NOW unless marked" (E:L754-771) — verbatim rules

| # | Convention | Rule |
|---|---|---|
| RX-01 | Decision and fill timing | Decide at close t on data up to t. Primary fill: KRX official close t (closing call 15:20-15:30). Conservative bound: close t+1. Skip-day variant for holdings under one month. Never use NXT or after-hours prints. US: closing auction via KIS. |
| RX-02 | Momentum and trend entries | At the close, not the next open. (KRX overnight +18.4%/yr vs intraday −7.9%) |
| RX-03 | Limit-locked days | No entry at a locked limit-up close; fill at the t+1 open. A locked limit-down exit carries to the first unlocked session at 2x cost. VI, circuit-breaker, overheating and halt days are flagged unfillable. Locked limit-downs are excluded from reversal books. |
| RX-04 | Stops and exit fills | Fill at the worse of the stop and the next open, never at the stop. No name-level stops on KRX sleeves; signal exits only. |
| RX-05 | Eligibility | KOSPI+KOSDAQ common shares (code ending 0); price ≥ ₩1,000; cap ≥ ₩100bn or top 500 by prior month-end cap; 20-day ADV ≥ ₩1bn (₩3bn capacity variant); listed ≥ 60 sessions. Exclude administrative, caution and warning designations, SPACs, preferreds, REITs/funds, halted names, DART rights/merger windows and IPO/relisting days. Eligibility for books and benchmarks uses data up to t−1. US: price ≥ $5, ADV ≥ $5m. |
| RX-06 | Returns | Corporate-action-adjusted, with dividends where available. Flag \|Δln shares\| > 1% (DC0). |
| RX-07 | Capacity and impact | Position ≤ 1-2% of 20-day ADV. Impact = Y·σ_d·√(Q/ADV20), with Y ≈ 1. |
| RX-08 | Cost buckets | KRX ETF 3 bp. KRX stock 35 bp per side, itemised (commission, sell tax by date at 0.18 / 0.15 / 0.20% for 2024 / 25 / 26, half-tick floor, impact). 2x stress at 70 bp. US via KIS 50 bp; futures 5; crypto 10; FX 10. Costs are never lowered (P10); E7's 15-25 bp view for KOSPI200 names is unverified. |
| RX-09 | Turnover discipline | Monthly rebalance with buy/hold bands (enter the top decile or quintile, exit below the top 3 deciles or the quintile). One-way turnover target ≤ 30%/month, hard limit 50%. Report break-even per-side cost = gross / (2 × annual one-way turnover). Reject before the gate if break-even < 2x the pre-registered cost. |
| RX-10 | Caps | Single name ≤ 5% of NAV (selection sleeves). VW legs ≤ 5% of the leg. Sector ≤ benchmark +10 pp (long-only active ±5 pp). Pair cap 0.35 on look-through when pair share > 0.45 (market and ETF books). Semis ≤ 0.50. |
| RX-11 | Momentum risk | R-03 on every momentum sleeve, including KRX. No vol scaling for value, quality or reversal. R-04 on the spec book only. |
| RX-12 | Book-level risk | Ladder on total book NAV only. Steps non-cumulative. Re-arm at 0.5 with the reference peak reset. Back to 1.0 after +0.5σ or 60 sessions. Never re-arm against the all-time HWM; never per sleeve. Threshold units are contested (EX-T-11). |
| RX-13 | Review triggers | Forward drawdown beyond the 95th percentile of simulation, or 12-month Sharpe below its 90% CI, triggers a REVIEW. Never auto-liquidate. |
| RX-14 | Long-only realism | Korea stock cards gated long-only. Pre-registered benchmarks: EW, CW, CW ex-pair, capped CW. Short-regime flag 0/1/2 (open / partial ban / full ban). L/S results only as diagnostics. |
| RX-15 | Reporting | Fixed stress windows: Aug 2007; Mar-May 2009; Oct 2019 (KR); Nov 2020; Jan 2021; Aug 2024; Apr 2025; Oct 2025 (KR); Mar 2026; 22 Jun-30 Jul 2026 and the rebound. Also report the worst five-week relative loss, cap-binding frequency, and correlation to the pair. |
| RX-16 | Event timestamps | EDGAR acceptance ≤ 15:30 ET is usable at close d, otherwise d+1. OpenDART rcept_dt is usable at the close of rcept_dt + 1 trading day. The event layer can only exclude names or scale exposure to ≤ 1.0. |

Additional convention stated outside the RX table: **entry-day execution exclusion — "no new long within 5 sessions of a locked limit-up or volume spike"**, a BUILD NOW convention, not a card (E:L509, tagged RX-03).

### B.2 Exact numbers behind the conventions

**Costs / turnover / break-even (EC-T-04, E:L115-129).**
- Itemised cost per stock-level card: commission, the date-varying sell tax, a half-tick spread floor, sqrt(Q/ADV) impact, capacity cap 1-2% of 20-day ADV.
- Card header reports: turnover, net at 1x and 2x cost, **break-even per-side cost = gross annual return ÷ (2 × annual one-way turnover)**.
- **Pre-gate screen: reject before the gate if break-even < 2x its pre-registered cost.** Buy/hold bands mandatory on monthly stock cards. "35 bp is adequate only for liquid names."
- Cost drag formula: `2 × monthly one-way turnover × 12 × cost` → at 35%/mo: 2.94%/yr at 35 bp, 4.20%/yr at 50 bp.
- KRX tick 5.1-25.8 bp (p1-p99; 2023-01-25 tick regime, XLOG row 17); 11% of stock-days have a tick above 20 bp. Sell tax 0.18% (2024), 0.15% (2025), 0.20% (2026; KOSPI = 0.05% STT + 0.15% rural special tax). KRX round-trip floor 25-46 bp (E:L78).
- Screen-card break-even form used by the lab/QA: `ann_diff(gross) / (turnover_filtered − turnover_unfiltered)` → SCR-1 0.0338837 / (2.78453 − 1.89331) = 380.2 bp (Q:L52; `r3_golden_values.csv` note). L/S form: `gross/yr ÷ turnover/yr (both legs)` → weekly reversal 0.199254 / 159.462 = 12.50 bp (Q:L100; R3:L1176).

**Execution evidence (EC-T-03, E:L94-113; EC-T-26, E:L411-417).** Limit-up next-open entry −394 bp (t+5) / −579 bp (t+20) vs EW liquid universe (n 11,186, 2015-06..2026-09); a close entry +328 bp at t+1 "cannot be filled"; locked limit-downs −630 bp (t+1) / −1,036 bp (t+20), n 815. R2 limit-lock audit: 6.3% of EW-universe entries would be bought at a locked limit-up close, 2.1% of exits sold at a locked limit-down close (1.9% / 1.4% with the F4 screen). NXT took 9.1-10.6% of volume in 2025-26. US close auction pressure 8.1 bp average, > 63 bp in 1% of cases. KRX top-500 EW 12-1 D10-D1 2002-2026: overnight +18.4%/yr (t 8.7) vs intraday −7.9%/yr (t −1.8).

**Eligibility / data hygiene (EC-T-05, E:L131-146).** Evaluate eligibility on data up to t−1 (same-day eligibility inflated an EW benchmark to +27.7%/yr vs +0.5%/yr lagged). Unadjusted closes fabricate a −136%/yr high-turnover momentum spread vs +17.1%/yr adjusted. Regime flags: short-sale bans, Value-up, CB rules, insider pre-disclosure, treasury-share cancellation, dividend reform, tax path. Event cards that depend on a post-reform regime are INSUFFICIENT DATA until about 2028. Short-sale bans as printed: 1 Oct 2008-31 May 2009, 11 Aug-9 Nov 2011, 16 Mar 2020 (partial lift 3 May 2021), 6 Nov 2023-30 Mar 2025.

**Benchmarks / pair (EC-T-06, E:L148-161).** Every Korea stock card gated long-only; benchmarks pre-registered per card: EW, CW, CW ex-pair, concentration-capped CW; the Samsung + SK hynix pair-share series uses **one pre-registered denominator**. Pair share (all lines): 26.9% end-2023, 34.0% end-2025, peak 57.1% on 25 Jun 2026, 50.8% on 29 Sep; common-only 52.6%; with Samsung preferred in the numerator 53.7% (E:L157; anchor A5 E:L669: peak 57.1% / 58.9%; first above 0.45 on 7 May 2026). Breadth 30 Dec 2025-22 Jun 2026: CW +117.1% vs EW +3.4%; median −8.7%; 64.9% of names fell; CW ex-pair +41.7%. 2026 YTD to 29 Sep: CW +63.6% vs median −8.9%; 6.4% of 829 names beat CW; pair contributed +50.9 pp.

**Momentum risk (EC-T-07, E:L163-179).** **R-03 = σ126, 12% target, cap 1.0**, applies to every momentum-family sleeve including KRX; value, quality and reversal get no vol scaling (R-05). R2 final (12-1 L/S, ALL quintiles, 1996-2026): net Sharpe EW 0.20 → 0.27, VW 0.25 → 0.31; weights on 22 Jun 2026 0.55 EW / 0.27 VW; crash window scaled VW −10.5% vs −22.9% static at same exposure; 2016-26 scaling lowered net Sharpe (EW −0.20 → −0.24; VW 0.32 → 0.23). "It is a risk control, not a source of return."

**Stops / review triggers (EC-T-09, E:L191-205).** 15% stop test spec: close trigger, exit at next close, 70 bp per stopped round trip. Top-500 WML 2000-26: EW net35 0.04 → −0.15; VW 0.28 → 0.07; ALL quintiles EW net35 0.20 → −0.20; 10% stop worse. Kaminski-Lo fails (monthly AR(1) −0.009 vs monthly Sharpe 0.117). **DROP name-level stops on KRX. BUILD NOW review triggers** (RX-13) and the signal-exit convention. US HZZ-style stop = BACKLOG as its own CARD-O. Brownian check: 8% vol, Sharpe 0.5 book hits −8% in 38% of years.

**Drawdown ladder (EC-T-10, E:L207-223; EX-T-11, E:L595-605).**
```
scope      : total book NAV, AFTER the book volatility target; never per sleeve
steps      : non-cumulative
after HALT : re-arm at 0.5 with the reference peak RESET (never the all-time high-water mark)
back to 1.0: after a gain of +0.5σ, or 60 sessions without a new −1σ breach
thresholds : CONTESTED — macro R-07 fixed −8 / −12 / −15 %  vs  E5 −1.0σ / −1.5σ / −1.9σ of the
             declared book vol target (identical at 8% book vol); triage = FORWARD-SIM both conventions
```
Evidence (KOSPI CW 2000-26, 35 bp, re-arm 0.5 with reset): Sharpe 0.42 → 0.40; MDD −55.8% → −41.3%; 0.69 halts/yr; below full exposure on 61% of days; July 2026 −38.6% → −21.3%; H1-2026 +101.1% → +49.0%. All-time-peak reference: 22.8 halts/yr, Sharpe −1.65. Per-sleeve ladder on vol-scaled VW WML: 0.38 → 0.16. VT20 + fixed ladder: 0.40 → 0.35, MDD −47.4% → −34.8%, 0.50 halts/yr. Cumulative steps: mixed (helped KOSPI variant 1 0.39/−49.3% vs 0.34/−53.6%; E5 reports they wrecked SPY 0.41 → 0.02 — not re-run). P(−15% within 10 years) at Sharpe 0.5: 0.66 at 8% vol; 0.97 at 12% vol.

**Caps (EC-T-11, E:L225-237).** As RX-10. Cost of the 0.35 pair cap on KOSPI CW: bound on 98 sessions from 7 May 2026; −15.0 pp melt-up, +4.6 pp crash, −1.8 pp rebound, −2.2 pp 2026 YTD. 5% cap on VW WML: 2016-26 net35 Sharpe 0.30 → 0.02.

**Lottery screen (EC-T-12, E:L239-261).** Filter/base definitions (KR2:L117): `F1` highest TURN_1M quintile; `F2` highest VOL_3M quintile; `F3` highest MAX_1M quintile; `F4` P6 lottery composite = bottom decile of pct-rank(−VOL_3M) + pct-rank(−MAX_1M) + pct-rank(−TURN_1M); `F5` E7 attention-fade events in the last 20 sessions (volume >= 5x the previous 20-day average with r >= +5%; locked limit-up close, >= 29.5% from 2015-06-15 and >= 14.5% before, close = high; +50% in 20 days); `F6` 252-session share growth > 10% ignoring split-like days; `F7 = F1|F2|F3`; `F8 = F4|F5|F6`. Bases: `B1` EW ALL; `B2` VW ALL, 5% cap (iterative pro-rata redistribution); `B3` top-200 VW, 5% cap; `B4` 12-1 momentum top quintile EW.
- R2 (366 months 1996-03..2026-09, long-only, monthly; both books net of own turnover): B1/F4 +3.1%/yr net35 (IR 1.53, t 8.3; +2.8% at 70 bp; 90% of years); B1 F1 +4.3% (t 6.6); F2 +3.6% (t 5.7); F3 +2.4% (t 5.0); B2/F4 +0.85% (t 3.9); B3/F4 +0.49% (t 2.3); B4 F1 +7.8% (t 6.2), F4 +6.1% (t 7.5). Sub-periods B1/F4: 1996-2005 +4.3%, 2006-15 +2.8%, 2016-26 +2.2%.
- Indicative gate B1/F4 and B4/F4: 7 of 8 steps, REVISE; pooled DSR over 176 trials 0.94 and 0.56 (< 0.95); best of 176 trials DSR 0.979 on pooled variance.
- Verdicts: B1 BUILD candidate as a filter (**F4 at a 10% cut**; F1 when a larger mean matters more than tracking error); B4 BUILD as a construction rule for any long-only momentum or small-cap sleeve; B2 REVISE (hygiene filter, not alpha); B3 REJECT.
- **Triage: BUILD NOW as a screen card, gated against the unscreened book on the same days.** "Any Korean EW, small-cap or momentum sleeve should inherit it as a construction rule once it passes. It does not apply to top-200 or cap-weighted books."

**Dilution screen (EC-T-13, E:L263-271).** Chair measure: `ISS = Δln(marcap) − Δcumulative log price over 252 sessions`, EW quintiles, 2001-2026, net35: Q5 −13.4%/yr (t −10.3); universe ex-Q5 +3.0%/yr (t 9.2), 85% of years positive, +1.5% in 2016-26 (t 3.3). R2 F6 on EW book +2.3%/yr (t 3.9), unchanged at 70 bp; capped VW +0.3% to +0.7% n.s. Issuance events (new-share listings ≥ 3%, n 10,855, 2005-2025): 12-month BHAR −25.3% size-matched; −34.4% (2005-14), −17.6% (2015-24), −5.1% (Dec-2024 onward, n 314). **BUILD NOW as a screen on EW and selection books gated against the unscreened book. Pre-register the decay check (post-2015 sub-period).**

**PIT layer (EC-T-14, E:L273-284).** As RX-16. Start forward archives now: consensus, opinions, flows, quotes. Composite core: gross profitability (GP/A) and net issuance, value as a low-weight partner. EDGAR stamps to the second; OpenDART list API returns rcept_dt date-only, ~20,000 calls/day; DART `fnlttSinglAcntAll` data start 2015; KIND time column returned HTTP 403. Power: IR 0.3 needs ~18 years at one-sided p ≤ 0.10; DART-only history detects only IR ≥ 0.41-0.48. BUILD NOW (PIT layer + archives); BACKLOG (OpenDART composite card).

**Index protective (EC-T-15, E:L286-304; EX-T-01, E:L454-468).** Single-index trend is `CARD-P`, never `CARD-O`. KOSPI protective cell → **FORWARD-SIM: pre-register floored `clip[0.5,1](ensemble) × VT20` as primary (P2- and R-06-compliant; its plateau not yet evaluated) and the unbounded sleeve as the comparison.** VT20 (R-06) is the protective workhorse; trend's own protective weight 1; product weight 2. R2 scorecard (KRX ETF, 3 bp): ensemble vote-share sleeve PASS (PC-1 +8.9 pp, tail 0.77, PC-5 0.60); unbounded ensemble × VT20 REVISE (PC-1 +11.3 pp, tail 0.55, 11/13 episodes, PC-5 0.57); clip[0.5,1](ensemble) × VT20 PASS (PC-1 +15.4 pp, tail 0.64, PC-5 0.63); 0.5+0.5x × VT20 PASS (+13.0, 0.65, 0.67); 12M sign monthly (R-14 rule) INSUFFICIENT DATA (PC-1 +4.7 pp); bounded trend without VT fails PC-2 (tail 0.91-0.92). Start-date sweep: VT20 alone passes from every start 1996-2006 (PC-1 +4.4 to +11.6 pp); ensemble PASS from 1996-09 and 1997, REVISE from 1999, INSUFFICIENT DATA from 2001 and 2006, REJECT from 2011 and 2016; trend × VT20 product REJECT from 2011. Crash 22 Jun-30 Jul 2026: ensemble −31.3% vs −38.6% (exposure 1.00 on first crash day); VT20 −12.3%; ensemble × VT20 −9.8%. SPY at 50 bp: every rule fails (EX-T-03, E:L487-492).
- Scorecard definitions as used by the lab (IDX2:L42): S = buy-and-hold × the rule's average exposure (no cost); PC-3 p = one-sided circular-block-bootstrap p of dSR* <= −0.10, block = max(10, PW(d), PW(d^2)), 2,000 resamples, seed 11; years = calendar years with >= 126 sessions; plateau = share of declared neighbours keeping half the centre's dMDD and dSR >= −0.10; onsets = de-risk onsets of two-state rules chain-merged within the rule's lookback (Tier A needs 30). Ensemble = "ENS multi-speed vote (20/60/120/250)"; VT = "SMA20 vol; KOSPI 20%, SPY 15%" (IDX2:L54, L56). PC-1 = dMDD vs S at 1x/2x; PC-2 tail; PC-3 dSR; PC-4 episodes (+/n, max share); PC-5 years; PC-6 plateau (IDX2:L44). The authoritative PC definitions are macro §8.7 (not in the files read here).

**Shiller data rule (EC-T-16, E:L306-318).** Use month-end data, or a one-month skip. Averaging inflates Sharpe by +0.10-0.19 (10-month SMA) and +0.23-0.25 (12-month sign); use the LAG1 number for the SMA and LAG1 minus about 0.13 for 12-month momentum; treat averaged drawdowns as understated by up to 5 pp. BUILD NOW (data rule).

**Event Calendar and Risk Screen layer (EC-T-22, E:L373-381).** One layer that "can only exclude names or scale exposure to at most 1.0"; covers lock-ups, index effective dates, pinned cash targets, Korean insider pre-disclosed sales, record dates and short-sale regimes; each screen gated against the unscreened card on the same days. BUILD NOW (convention).

**Reporting (EC-T-25, E:L402-409).** Stress-window table and worst five-week relative loss on every stock-level card. BUILD NOW.

**Governance (EC-T-28, E:L430-448).** Haircut published priors before they become priors; single-market stock/trend cards → expect INSUFFICIENT DATA or REVISE; **pre-register 4-5 features at most; count MA and TSMOM variants as one family.** Power t ≈ IR × √years.

### B.3 Remaining consensus items (decisions only)

| ID | Decision | Lines |
|---|---|---|
| EC-T-01 | DROP all intraday technical rules (intraday momentum, ORB, VWAP crosses, gap rules, S/R bounces, overnight holds, end-of-day reversal, half-hour periodicity); no intraday order path; fewer than 882 recorded sessions | E:L73-80 |
| EC-T-02 | KRX daily/weekly ST reversal 0 (DROP); monthly reversal 1 as conditioning input only (CONTEXT). Weekly: 159x/yr turnover, break-even 12.5 bp/side (22.2 bp VW), net35 Sharpe −1.78. Conflicts with macro §2.2 KEEP 3 and R-15 (MC-09) | E:L82-92 |
| EC-T-08 | Korean raw 12-1 momentum weight 0 (DROP); macro R-15 value of 0 stands | E:L181-189 |
| EC-T-17 | Valuation timing DROP; valuation = CONTEXT display "that shows its residual drift" | E:L320-329 |
| EC-T-18 | DROP: CANSLIM/IBD, SEPA/VCP, factor-ETF rotation, ML or alt-data alpha, recommendation levels and target upside, LTG levels, 13F cloning. BACKLOG: estimate revisions (needs forward archive). Short interest only as a filter on longs; aggregate short interest CONTEXT | E:L331-344 |
| EC-T-19 | Long-only quality is not a crash hedge; must not be counted as one in any risk budget (US quality 3 → 2) | E:L346-353 |
| EC-T-20 | US PEAD standalone DROP (US earnings drift 2 → 1); survives only as confirmation input | E:L355-362 |
| EC-T-21 | US event drifts DROP as cards (S&P inclusion, buybacks, SEOs, dividend initiation/omission, merger arb); CONTEXT as calendar flags | E:L364-371 |
| EC-T-23 | Korean investor flows 3 → 1; no direction rule; BACKLOG, **log final KIS flows at t−1 from now** (conflicts with macro §2.2 KEEP 3, MC-08) | E:L383-391 |
| EC-T-24 | Crowding display-only; R-08 is not factor-crash protection (VIX 12.9-25.8 at onsets) | E:L393-400 |
| EC-T-27 | DROP for KRX stocks: golden/dead crosses, MA alignment (정배열), price-above-MA200 selection, limit-up chasing, volume-spike buying, size tilts, RSI/%B | E:L419-428 |

### B.4 Contested EX-T-01..14 (triage to encode)

| ID | Triage | Lines |
|---|---|---|
| EX-T-01 trend sleeve vs overlay [0.5, 1.0] | FORWARD-SIM both cells, floored trend × VT20 primary. **P2 stands.** Coordinator to classify trend as signal or overlay for books without a vol target (MC-07) | E:L454-468 |
| EX-T-02 R-14 class and speed | FORWARD-SIM a venue-dependent speed cell beside R-14's 12-1. BACKLOG B3 re-registration (≥ 25 markets, fixed multi-speed ensemble; needs gate-class approval). **R-14 stands as decided** (MC-06) | E:L470-480 |
| EX-T-03 US index trend protective weight | 3 → 2 pending the instrument book; 3 restored only with an instrument costing 5 bp or less. BACKLOG | E:L482-494 |
| EX-T-04 attention-fade | **DROP as a standalone or composite monthly screen.** Entry-day execution exclusion stays (5 sessions). Daily-entry K-AF card BACKLOG. F5: +1.40%/yr net35 (IR 0.49), −0.08% at 70 bp; adding F5 to F4 (F8) lowers IR 1.53 → 0.67. E7 dissent recorded | E:L496-509 |
| EX-T-05 KR momentum variant | **FORWARD-SIM one pre-registered variant at weight 1: momentum quintile (12-1 or 12-7) ex the highest-turnover quintile or the F4 composite, vol-scaled (R-03), capped, long-only.** Exclusion is a mandatory construction rule for any Korean momentum sleeve. Raw 12-1 stays 0 | E:L511-527 |
| EX-T-06 KR low volatility | BUILD NOW as a screen input (F2 / F4). FORWARD-SIM K-LV as a **descriptive** sleeve with the **same-beta static comparator (β × market + cash, net35) and Sharpe non-inferiority pre-registered**. Comparator definition → coordinator (MC-11). BACKLOG US DC9. Chair c12: MDD worse than S_beta by 22.4 pp (EW, VW-market comparator), 12.2 pp (EW comparator), 7.1 pp (VW); tail ratio 0.97-0.99; Sharpe 0.41 vs 0.36 / 0.24 | E:L529-553 |
| EX-T-07 crowding multiplier | BACKLOG (BL-C14/DC5); CONTEXT until a test shows value beyond R-03 | E:L555-562 |
| EX-T-08 extend D-M gate (R-04) | BACKLOG. **Use the spec book only. No extension while R-04 is INSUFFICIENT DATA** (MC-10). KR gate on 4.1% of days, 3 onsets since 2000 (2001-01-04, 2008-10-31, 2020-03-20) | E:L564-574 |
| EX-T-09 KR earnings drift | Weight 1. BACKLOG (DC-2, OpenDART rcept_dt + 1). Proxy negative (positive events −1.34% over 60d, t −4.2). Dissent E4/E7: 2 | E:L576-585 |
| EX-T-10 KR value | Weight 1. BACKLOG (DC-8/DC10). Dissent E4: 2 | E:L587-593 |
| EX-T-11 ladder units | FORWARD-SIM both unit conventions (MC-01, MC-16) | E:L595-605 |
| EX-T-12 haircut multiplier | CONTEXT. **One haircut per stage. Expected live = 0.6 × OOS ("take 40% off"); ×0.4 is REFUTED (method).** Publication decay + gate haircut on the same published number double counts (MC-12) | E:L607-618 |
| EX-T-13 US Form 4 insider buys | BACKLOG (DC10: buys-only, long-only, 126 days, timed by EDGAR acceptance); FORWARD-SIM only if DC10 passes | E:L620-627 |
| EX-T-14 US IPO-age exclusion | BACKLOG; build with the first US stock card (exclude unprofitable issuers and those with sales below $50m for 36 months) | E:L629-638 |

### B.5 Refuted/withdrawn ER-T-01..12 and corrected anchors A1-A22 (E:L644-686) — do not encode the left column

| Ref | Wrong | Use |
|---|---|---|
| ER-T-01 / A1 | Dynamic momentum "roughly quadruples" Sharpe | "approximately doubles"; JFE Table 7: 0.682 → 1.041 → 1.194 |
| ER-T-02 / A8 | Bounding trend to [0.5, 1.0] keeps "about half" the protection | PC-1 vs own S: +11.3 (unbounded × VT20) → +13.0 (linear) / +15.4 (clip). Absolute MDD −27.7% → −36.2% / −29.4%. Plain floored trend fails PC-2 (tail 0.91) |
| ER-T-03 / A14 | Korean low-vol is a crash hedge (CARD-P, weight 2) | Withdrawn as CARD-P claim; screen input + descriptive FORWARD-SIM. beta 0.63 (EW) / 0.74 (VW) |
| ER-T-04 / A6 | 82 bp/mo insider buys as long-only 126-day overlay | Long-short buys minus sells, one-month hold, five-factor alpha: 82 bp VW / 180 bp EW (1986-2007) |
| ER-T-05 | Prior weights 3 for Korea ST reversal, flows, earnings drift | Reversal 0 (1 monthly conditioning), flows 1, drift 1-2 |
| ER-T-06 / A7 | Korean VW momentum edge after 2016; E5's 0.43 EW | KR top-500 12-1 WML 2000-26: EW ≈ 0.26-0.30 gross / 0.04-0.07 net35 (deciles); VW ≈ 0.44-0.48 / 0.28-0.30; 2016-26 EW net −0.13, VW net 0.30 (0.02 with a 5% cap); July 2026 −30.0% EW / −29.8% VW (R2) |
| ER-T-07 / A3 | "Korean reversal −2.95%/month" | Regression coefficient (t −3.77), not %/month |
| ER-T-08 / A4 | Pair = 22% of KOSPI at end-2023 (also in macro R-07 evidence text) | 26.9% (all lines) / 27.8% (common-only) (MC-15) |
| ER-T-09 / A15 | GS high-beta momentum basket −37% in July 2026 | Only "worst month since November 2000" verifiable |
| ER-T-10 | "+0.1 to +0.3 Sharpe from vol-scaled sizing on nearly every strategy" | Robust only for momentum; KR STR net35 −0.29 → −0.59 with scaling |
| ER-T-11 / A17 | "Korean momentum is negative among high-turnover stocks" | Positive on adjusted prices (+1.43%/month, t 3.3); long-only high-turnover winner leg does lag EW by −11.6%/yr net (t −4.2) |
| ER-T-12 | Name-level 15% stops on KRX sleeves | DROP |
| A2 | Step 9 ×0.4 | expected live Sharpe = 0.6 × OOS; E1's F1 prior 0.13 before the gate; E4 composite live IR 0.18-0.30 |
| A5 | Pair share denominators | 29 Sep 2026: 50.8% (all lines), 52.6% (common-only), 53.7% (all lines with Samsung pref in numerator); peak 57.1% / 58.9% on 25 Jun 2026; first above 0.45 on 7 May 2026 |
| A9 | SPY trend at 50 bp | All multi-speed cells REJECT; at 5 bp INSUFFICIENT DATA |
| A10 / A11 / A16 | KOSPI 24-month return +235%; 31 Mar 2025 −2.93%; crash −38.0% | +227% (daily) / +222% (month-end); −3.00%; −38.6% (22 Jun-30 Jul 2026) |
| A12 | MTUM IT 54.3% (30 Jun 2026) | 53.22% |
| A13 | KR low-turnover momentum long-only excess | 2015-24: +2.9% (E7 universe) / −0.1% (ALL); 1996-2026 (ALL): +9.7%/yr net (t 2.8); high-turnover winners −11.6%/yr (t −4.2) |
| A18 | AQMIX | 10-year 5.44% vs T-bills 2.42%, vol 9.96% → Sharpe ≈ 0.30 |
| A19 | E7 KRX event studies | stand as printed (−394/−579 bp; −43/−93 bp; −630 bp) |
| A20 | KR D-M gate | 3 onsets since 2000, 4.1% of days (chair); R2: 9 onsets 1996-2026 (9.8% of days), mostly 1997-99; never fires in a bull-market crash |
| A21 | KOSPI trend protection | Concentrated in 1997-2001; ensemble REJECT from 2011 and 2016 starts; VT20 alone passes CARD-P from every start 1996-2006 |
| A22 | Gate behaviour | Step 8 passes 24-31% of zero-Sharpe strategies over 10 years; ten-session blocks: step 2 6.9% (not 5%), step 5 12.8% (not 10%); "IR 0.3 needs 18 years" = 50%-power horizon; 80% needs ~50 years |

### B.6 Executives' weight tables (E:L690-746)

Reading: *Alpha* = prior for a `CARD-O` return claim; *Protective* = prior for a `CARD-P` drawdown claim "or for a de-gearing claim that must beat a same-beta static book"; *Screen* = priority (0-3) of a subtractive screen gated against its unscreened book (E:L692-697).

**US (KIS, 50 bp per side).** XS momentum 3 → **2** (BACKLOG, no US stock sleeve); ST reversal 1 → **0** DROP; value 1 (composite member); quality 3 → **2**, protective 0; low vol 2 → **1** (pending DC9), protective 1 (must beat same-beta static); flow 1 (display only); earnings drift 2 → **1** (DROP standalone; confirmation input); TS trend SPY: alpha 1 (return prior), protective **2** (3 only at ≤ 5 bp), BACKLOG (instrument book); net issuance (new) **2** BACKLOG; insider buys (new) **0-1** BACKLOG DC10; IPO-age exclusion (new) screen **2** BACKLOG.

**Korea (KRX stock 35 bp per side, KRX ETF 3 bp).**

| Family | Prior | Macro now | Exec alpha | Protective / screen | Triage |
|---|---|---|---|---|---|
| Raw 12-1 momentum | 1 | R-15: 0 | 0 | – | DROP |
| Momentum variant (Q5 ex highest-turnover or ex F4; 12-1 or 12-7; vol-scaled, capped, long-only) | – | R-15: 1 (UNVERIFIED) | 1 | – | FORWARD-SIM |
| ST reversal, daily/weekly | 3 | R-15: 3; §2.2 KEEP 3 | 0 | – | DROP |
| ST reversal, monthly | (3) | as above | 1 (conditioning input only) | – | CONTEXT |
| Value | 2 | – | 1 (E4: 2) | – | BACKLOG (OpenDART PIT) |
| Quality | 1 | – | 1 | – | BACKLOG (OpenDART PIT) |
| Low volatility | 2 | – | 0-1 | protective 1 (descriptive) + screen input | FORWARD-SIM; screen BUILD NOW |
| Investor flows | 3 | §2.2 KEEP 3 | 1 | – | BACKLOG (log flows now) |
| Earnings drift | 3 | – | 1 (E4/E7: 2) | – | BACKLOG DC-2 |
| TS trend, KOSPI (ETF line) | 2 | R-14: 1; R-06 VT20 | 1 (return prior) | 2 as floored trend × VT20; 1 for trend alone | FORWARD-SIM |
| TS trend, KOSDAQ | – | R-14: 0 | 0 | 1 | BACKLOG |
| Lottery / turnover / vol exclusion composite (new) | – | – | – | screen 3 | BUILD NOW |
| Dilution / net-issuance exclusion (new) | – | – | – | screen 3 | BUILD NOW |
| Attention-fade events (new) | – | – | – | screen 0; entry-day execution exclusion (convention) | DROP as a monthly screen |
| 52-week-high proximity | – | – | 1 | – | BACKLOG (quarterly variant) |
| Size | (implicit) | – | 0 | – | DROP |

**Other markets (E3 evidence only, not re-checked).** Crypto C3: alpha 2, protective 2 — keep C3; add a vol-scaled long-only control, a sub-period table and ETH replication. Japan 1 / 2 BACKLOG. Europe 0-1 / 1-2 BACKLOG. Diversified futures (B3 re-registration) 1-2 (diversifier claim) / 3, BACKLOG (≥ 25 markets; gate-class approval). FX / rates / commodities trend 0-1 / 1-2 / 1-2 alpha, 1 / 2 / 2 protective, BACKLOG. Carry BACKLOG.

### B.7 Conflicts with the macro spec MC-01..18 (E:L775-794) — "flagged, not re-litigated"; coordinator/owner decisions

| # | Macro item | Recommended coordinator action |
|---|---|---|
| MC-01 | R-07 thresholds fixed at −8 / −12 / −15% | Pre-register both unit conventions, or declare book vol ≤ 8% |
| MC-02 | R-07 re-arm reference (open) | Adopt reset and 0.5 |
| MC-03 | R-07 cumulative steps (open) | Adopt non-cumulative steps |
| MC-04 | R-07 0.05 single name vs 0.35 pair (open) | Rule by book type: 0.05 selection sleeves; 0.35 pair cap on look-through for market and ETF lines |
| MC-05 | R-07 pair-share denominator (undefined) | Pre-register one denominator |
| MC-06 | R-14 class and speed | Keep R-14; add a CARD-P cell and a speed cell |
| MC-07 | P2 bounds for trend | No change to P2 when VT20 is applied; classify trend as signal or overlay for books without a vol target |
| MC-08 | §2.2 KEEP Korea flow 3 | Coordinator decides; log flows now (panel says 1) |
| MC-09 | §2.2 KEEP / R-15 Korea ST-reversal 3 | Coordinator decides (panel: 0 daily/weekly, 1 monthly conditioning); "the R-15 net-of-cost test already fails on lab data" |
| MC-10 | R-04 scope | Spec book only |
| MC-11 | §8.7 CARD-P scope | Add the same-beta static comparator definition for stock-level protective sleeves |
| MC-12 | Step-9 wording | Fix the brief's "60% live haircut"; spec says live = 0.6 × OOS |
| MC-13 | R-14 US weight 3 | Weight 2 pending the instrument book |
| MC-14 | R-08 | Do not count R-08 as factor-crash protection |
| MC-15 | R-07 evidence text "22% at end-2023" | Correct to 26.9% (all lines) / 27.8% (common-only) |
| MC-16 | Book vol target (not in the spec) | Coordinator decision; E5 proposes ≤ 8%/yr |
| MC-17 | R-06 Korea VT20 | Information: KOSPI VT20 PASS on 1996-09..2026-09 (PC-1 +6.5 pp, tail 0.70, 70% of years) and from every start 1996-2006; INSUFFICIENT from 2011/2016 starts |
| MC-18 | Gate steps 2, 5 and 8 | **Use max(10, Politis-White) blocks in the outperformance gate as the macro cards already do; do not rely on step 8 alone** |

### B.8 Chair checks (the "c01-c12" set; E:L15 says c00-c13)

None of the chair-check scripts or outputs ship in the bundle (only `datalab/verification/*.csv`). Mapping reconstructed from E citations, `exec_verification_log.csv` column `how_checked`, and QA citations:

| Check | What it recomputes | Key outputs | Where cited |
|---|---|---|---|
| c00 | not described anywhere in the read files | — | E:L15 |
| c01 | US files: Shiller, SPY, French (linearmodels/arch), CBOE VIX | S&P 12m long/flat R/V 1.32 vs 0.81 (1992-2014), 1.02 vs 1.16 (2015-26); CAPE R² 0.048 / 0.161 / 0.292; OOS −0.56 (fixed) / −0.25 (expanding); Shiller 12m L/S 0.51 → 0.30 with skip, 10m SMA 0.76 → 0.59; SPY AC(1) 0.057 vs 0.206; SPY 200d at 5 bp 0.34 vs 0.37, MDD −30.0% vs −56.5%, S (0.71) −43.7%; HML 0.60 vs −0.17; French Mom 0.62 → 0.77 vol-scaled, MDD −57.6% → −28.5%; VIX 19 of 19 | XLOG rows 1-5, 26-28, 39-43, 68-69 |
| c02 | Rebuilt KOSPI (tracks official closes within 0.23%): trend/VT20 cells, ladder implementation, GBM false-alarm simulation (20,000 / 8,000 paths, seed 11), index levels | ensemble long/flat 0.58 vs 0.40, MDD −34.5% vs S −45.2%; floor placement +9.2 pp (after VT) / +15.0 pp (before VT) vs +12.0; ladder 0.42 → 0.40, −55.8% → −41.3%, 0.69/yr; ATH reference 22.8 halts/yr, Sharpe −1.65; VT20 + ladder 0.40 → 0.35; +227% / +222%; −3.00%; −38.6%; records −12.05%, −9.99%, +17.90% | XLOG rows 30-37, 58-59, 61-62, 66-67, 78, 98-99; E:L674-680 |
| c03 | not referenced | — | — |
| c04 | Pair share / concentration from marcap (`c04_concentration_stdout.txt`) | 26.9% (all lines) / 27.8% (common-only) end-2023; 50.8 / 52.6 / 53.7% on 29 Sep 2026; pair traded-value share 21.6% (2024), 21.0% (2025), 42.8% (2026) | XLOG rows 44, 65, 92-93; E:L668-669 |
| c05 / c05b | KR top-500 WML replication; 15% stop (close trigger, cash from t+1, 70 bp per stopped round trip); 5% cap; D-M gate onsets; Kaminski-Lo; E7 long-only factor table. c05b = vol scaling with a 1997 warm-up (first pass without warm-up was a chair error) and per-sleeve ladder | EW 0.30 / 0.07, VW 0.48 / 0.30; cap 0.30 → 0.02; 3 onsets, 4.1% of days; scaled VW 0.38-0.41, weights 0.34 / 0.20 on 23 Jun 2026; per-sleeve ladder 0.38 → 0.16 | XLOG rows 55-57, 60, 63-64, 71, 87-89; E:L178, L671, L684 |
| c06, c06b-c06e | c06: KRX tick table (2023-01-25 regime); night/day momentum decomposition; ISS quintiles. c06b/c06c: diagnosis of the chair's same-day-eligibility benchmark error; c06d: independent event-study recompute; c06e: SEO / new-share-listing BHAR proxy (listings ≥ 3% without base-price adjustment, bonus issues excluded, 2005-2025, n 10,855) | tick 5.1-25.8 bp, floor 25-46 bp; overnight +18.4%/yr vs intraday −7.9%/yr; Q5 −13.4%/yr, ex-Q5 +3.0%/yr; −394 / −579 bp, −43 / −93 bp, −630 / −722 / −1,036 bp; benchmark +27.7%/yr → +0.5%/yr; 12m BHAR −25.3% size-matched (−21.6% vs EW): −34.4% (2005-14) / −17.6% (2015-24) / −5.1% (Dec-2024 onward, n 314) | XLOG rows 17, 21, 53, 79, 81-86; E:L268, L683 |
| c07 | (a) information-event proxy (volume ≥ 4x 60d average and \|abnormal return\| ≥ 3σ), 1999-2026; (b) pair-cap cost run (`c07_stdout.txt` line 9: uncapped +116.8%, capped +101.9%, −15.0) | positive events −1.34% over 60d (t −4.2), negative −2.68% (t −7.6); cap cost −15.0 / +4.6 / −1.8 / −2.2 pp | XLOG row 54; E:L236, L989; Q:L136; R3:L237, L551 |
| c08 | K-LV vs a same-beta static book (0.63x EWM), E7 universe, 2015-07..2026-09 | MDD −54.3% vs −43.9% (ΔMDD −10.5 pp); ΔSharpe +0.08 | XLOG row 90; E:L536 |
| c09 | Breadth on KOSPI common shares listed on both dates (`c09_stdout.txt` lines 4-5) | 2025-12-30..2026-06-22: 64.9% fell, median −8.7%, EW +3.4%, CW +117.1%, ex-pair +41.7%; 2026 to 29 Sep: +63.6% vs median −8.9%, 6.4% of 829, pair +50.9 pp | XLOG rows 45, 91; Q:L134-135 |
| c10, c11 | not referenced | — | — |
| c12 | Low-vol Q1 vs same-beta static book (β × market + cash, net35, 1996-2026) on the R2 lab's own books (`c12_lowvol_samebeta.py` lines 61-63; `c12_lowvol_samebeta.csv` lines 2/6/10 → GV-469..489) | ΔMDD −22.4 / −7.1 / −12.2 pp; tail 0.985 / 0.978 / 0.967; Sharpe 0.41 vs 0.36 / 0.24; crash windows vs static: EW 4 of 7, VW 5 of 7 | E:L542-547; Q:L155, L180 |
| c13 | Patches the claim matrix with the final R2 summaries | — | E:L15 |

### B.9 Executives' gaps (E:L1087-1101)
Everything in-sample; plateau of floored trend × VT20 not evaluated; E5's scripts not saved; no OpenDART pull; no EDGAR Form 4 / US stock-level panel; no quote or order-book data (costs stay 35 bp per side); no historical t−1 final investor-flow series; price-only Korean returns; no local crypto history (E3's C3 numbers unverified); KIND time-of-day unverified (availability rule stays rcept_dt + 1); no Korean comomentum series; E3 tried ~40 configurations and the R2 exclusion race 176 trials; SPY ladder results taken from E5, not re-run.

---

## C. Independent QA (v1.0 → v1.0.1)

### C.1 Scope and rule
- Reviewed four deliverables: `QUANTGEN_TECHFUND_INTEGRATION.md` (spec, now v1.0.1), `QUANTGEN_TECHFUND_BACKLOG.md` (backlog, now v1.0.1), `QUANTGEN technical and fundamental signals.md` (report, title "Subtraction Beats Prediction at QUANTGEN's Costs"), `quantgen_signal_neural_link.html` (page) (Q:L9, L182). **None of the four is on this machine.**
- Rule: "Only objective fixes were applied; no rule, parameter, bound, weight, classification or verdict was changed" (Q:L3). After coordinator decisions the changelog sentence was narrowed to "No rule, weight, classification or verdict changed", because "the coordinator decisions change a test tolerance and a test expectation" (Q:L296, LOG#105).
- Method: own code (qa01-qa13, later qa17/qa17d), no project function imported; 114 numbers spot-checked by hand; automated traces of all 497 traced golden values, all 523 Appendix T.2 rows, 408 values printed in spec §9.3, 50 weight cells and 6 other-market rows (Q:L11-12). Raw panel: 13,953,730 rows, 7,913 dates 1995-05-02..2026-09-29, 4,301 codes after zero-padding (QR:L9).
- Spot checks: 114 rows; **4 numeric or factual mismatches, all fixed; 4 further rows where the number was right but a label or citation was wrong** (Q:L41).

### C.2 Recomputation results (Q:L17-37; QR:L21-65)

| Quantity | Claimed | QA | In tolerance |
|---|---|---|---|
| SCR-1 (F4 on B1) net 35, %/yr | +3.08 | +3.079 (first build); **3.0764** with exact definitions; gross 3.3884; net 70 2.7645 | Yes |
| SCR-1 IR net 35 | 1.53 | 1.532; **1.5295** exact (monthly basis). **Daily basis (the gate's): +3.12%/yr, IR 1.64** (gross +3.43 / IR 1.82; net-70 +2.80 / IR 1.47) | Yes |
| SCR-1 extras | Sharpe 0.33 vs 0.22; ΔMDD 1.70 pp; turnover 2.78 vs 1.89; 90% of years; sub-periods +4.31 / +2.81 / +2.20; break-even 380 bp | 0.333 vs 0.223; 1.70; 2.783 vs 1.893; 90.3%; 4.31 / 2.82 / 2.20; 381.5 bp (380.2 on lab inputs) | Yes (2006-15 0.01 pp high) |
| SCR-2 (F6 on B1) net 35, %/yr | +2.34 | +2.346 (first build); **2.3363** exact; gross 2.4164; net 70 2.2563 | Yes under ±0.10 pp |
| SCR-2 IR net 35 | 0.65 | 0.648; **0.6453** exact. **Daily basis: +2.48%/yr, IR 1.03** (gross +2.56 / 1.07; net-70 +2.40 / 1.00). Break-even 1,060 bp (printed 1,057) | Yes |
| Rebuilt KOSPI 2020-03-19 / 2026-06-22 / 2026-07-30 | official 1,457.64 / 9,114.55 / 5,593.56 | 1,457.46 (0.99988) / 9,120.19 (1.00062) / 5,599.30 (1.00103) | Yes (range 0.9987-1.0023) |
| Crash 22 Jun → 30 Jul 2026 | about −38.6% (official −38.63%) | −38.605% (VALID-only variant −38.634%) | Yes |
| VT20 vs S, ΔMDD, 1996-09-02..2026-09-29, 3 bp | +6.5 pp | +6.54 pp (2×: +6.44); MDD rule −51.42%, S −57.95%, B&H −64.45%; average exposure 0.854; ΔSR −0.0006 | Yes |
| VT20 tail ratio | 0.70 | 0.705 (mean weight on the worst 5% of buy-and-hold days ÷ mean weight) | Yes |
| VT20 extras | crash −12.2% vs −38.6%; 2016-26 gross Sharpe 0.633 vs 0.628, MDD −37.0% vs −44.1%, S −41.5%, ΔMDD 4.46 | −12.25% vs −38.61%; 0.6329 vs 0.6284; −37.00% vs −44.05%; −41.45%; 4.46 | Yes |
| Weekly 5-day reversal L/S EW ALL gross Sharpe | 0.99 | 0.999 (weekly ×√52); 1.014 (daily) | Yes |
| Weekly reversal net-35 Sharpe | −1.78 | −1.780 **only on weekly period returns ×√52**; daily basis −1.684 (cost first day) or −1.876 (cost spread) | Yes |
| Weekly reversal break-even per side | 12.5 bp | 12.35-12.57 bp; turnover 159.8/yr both legs | Yes |
| Weekly reversal gross mean | +19.9%/yr | 20.08 (weekly ×52); 19.73 (daily ×252) | **No** (0.15 pp; open, low priority) |
| Pair share CR-07 on 2026-09-29 | 53.71% | 53.7062% = (005930 + 005935 + 000660) / all KOSPI lines; 29.2943% on 2023-12-28; alternatives 50.82 / 52.59 / 53.96 and 26.88 / 27.79; first > 0.45 on 2026-05-06 (common-lines definition 2026-05-07); 99 of 181 sessions; peak 59.69% on 2026-06-25 | Yes (exact) |
| FS-1 floored trend × VT20 vs own S, 1996-2026 | ΔMDD +15.4 pp, tail 0.64 | +15.35 pp, 0.639 | Yes |
| ENS vote share vs S | ΔMDD 8.91, tail 0.768 | 8.91, 0.768 | Yes |
| Page chart A (2025-12-30 → 2026-06-22) | B&H +116.2%; VT20 +55.2% (net 3 bp); ENS 0.9865; floored ENS × VT20 0.5092 | +116.20%; +55.20%; 98.65%; 50.92% | Yes |
| Crash window trend / VT20 / floored | −31.3% / −12.2% / −9.8% | −31.30% / −12.25% / −9.78% | Yes |
| Panel check (spec §4.2, GV-209) | 12,186 of 13,949,140 = 0.0874% | 12,186 of 13,949,153 | numerator + ratio exact; denominator +13 rows unexplained |

With exact definitions QA reproduces: ALL universe vs the lab's saved `univ_all` at 366 formations — 0 differences; F6 flags 71,689 = 71,689 (368 members sit exactly at float32 0.1 and are flagged) (QR:L59-60).

### C.3 Tolerances (spec §9.3 as amended; QR:L17; LOG#48-50)

| Quantity | Level 1 | Level 2 |
|---|---|---|
| Sharpe, IR, ΔSR | ±0.01 (macro Level 1) | ±0.03 (macro Level 2) |
| MDD / ΔMDD; window returns | ±1 pp | (not printed in the read files) |
| Shares and tail ratios | ±0.03 | (not printed) |
| Annualised returns and differences (%/yr), other than screen rows | the printed precision (R3's proposal) | ±0.25 pp/yr (default, judgment) |
| **Screen rows (G-TF-SCR, and every SCR-1 / SCR-2 card statistic): annual excess-return difference; IR** | **±0.10 pp/yr; ±0.02, each compared on the same basis as the golden row (monthly with monthly, daily with daily)** | ±0.25 pp/yr; ±0.03 |
| Pair shares, index ratios | printed precision | — |
| Derived values | within 1 bp | — |
| Counts; verdict strings | exact (Q:L315; R3:L898) | — |

"Checks tighter than these bands, such as matching every printed decimal of a %/yr figure, are not a reproducibility requirement: a value inside its band passes. Level 1 is never tighter than the macro Level 1 where the macro gives a band." (LOG#50)

### C.4 Corrections that alter a number or rule an implementer would otherwise copy from R3

| # | What R3 (or the v1.0 spec built from it) says | QA / coordinator correction — implement THIS | Evidence |
|---|---|---|---|
| C4-1 | Screen evidence quoted as "IR 1.53" / "IR 0.65" with no basis (R3:L206, R3:L948) | These are **monthly-basis** IRs (R2 lab). **QUANTGEN's gate computes statistics on daily session returns, so screen cards are gated on daily differences `d_t = r_screened,t − r_base,t`: mean × 252, IR = mean / sd (ddof 1) × √252, each book charged c × its own turnover on the first session its new weights earn.** Daily-basis values: SCR-1 (B1/F4) +3.43 / **+3.12** / +2.80 %/yr (gross / net 35 / net 70), IR 1.82 / **1.64** / 1.47; SCR-2 (B1/F6) +2.56 / **+2.48** / +2.40 %/yr, IR 1.07 / **1.03** / 1.00. The two bases are "not interchangeable". Steps 2, 5 and 8 use d; step 6 rebuilds both books at 2× cost | Q:L248, L253, L268; QR:L63-64; LOG#57, #77 (coordinator F1) |
| C4-2 | Golden values for KRX stock books with no stated statistics convention | Rows labelled "monthly basis (R2 lab)" and every unlabelled R1/R2 KR value: statistics on holding-period returns (**monthly ×12 and √12 with Newey-West 6 lags; weekly ×52 and √52 with 4 lags**); max DD, total return and calendar-year counts on the daily series; a period belongs to the calendar time of its first holding day; costs charged at the formation close (**R_net = R_gross − c × turnover**); L/S period return = R_L − R_S − cost with both legs paying. A `lab_reference` run must reproduce each golden row **on its own basis** | Q:L252-253; LOG#61-62 |
| C4-3 | Dilution flag "252-session share growth > 10%" (R3:L211) read as strict, with test expectation "0.10 → not flagged" (v1.0 T-TF-SCR-02) | **Flag iff the float32-stored DIL_LIT > 0.10 (strict comparison with the float64 constant 0.10); missing ⇒ not flagged. Because 0.10 rounds to float32 0.100000001, a 10.0% increase (s = 1.1) IS flagged: the cut is inclusive at 0.10 to float32 precision** (368 ALL members sit exactly at float32 0.1 over the 366 formations). New test expectation: DIL_LIT 0.11 → flagged; a 10.0% increase → flagged; 0.099 → not flagged; missing → not flagged | Q:L234-236; LOG#43-45 (coordinator F2) |
| C4-4 | Split-like day "\|s_d − 1\| > 5% and \|s_d × Close_d / Close_{d−1} − 1\| ≤ 5%" | A change day with **\|s_d − 1\| > 0.05 (strict) and \|s_d × p_d − 1\| ≤ 0.05 (inclusive), where p_d = Close_d / Close_{d−1} is computed first, in float64 (p_d = 1 when the code did not exist on the previous session)**. Boundary case to test: IHQ (003560) on 2003-12-19, 5:1 reverse split (s = 0.2) with p = 4.75 ⇒ \|s × p − 1\| = 0.05 ⇒ split-like. Share-count change day: `s_d = Stocks_d / Stocks_{d−1}` in float64 when the code exists on d and on the previous KRX session and both counts are positive, else s_d = 1; change day iff **\|s_d − 1\| > 0.001 (strict)**. `DIL_LIT = exp(Σ ln s_d over non-split-like change days in the 252 sessions t−251..t) − 1`, computed as expm1 of the difference of float64 cumulative sums of ln s_d, stored as float32; missing when the code does not exist at t | Q:L232-234, L237; LOG#41-43, #46 |
| C4-5 | Operating-company filter cited as `classify_name` (undefined) | Name classifier (C.5) written out; code padding to six characters before any filter (files dated 1995-05-02..2000-05-26 store codes without leading zeros; `Code.str.zfill(6)`); a code stored as '5930' is read as '005930' | Q:L197, L228-230, L238; LOG#6, #37-39, #47 |
| C4-6 | ALL universe = eligible names with Marcap_t ≥ the 20th percentile (no numeric types) | Lab holds cleaned return r, Close, High, Amount and Marcap as **float32**; the 20th-percentile cut uses `np.quantile`, linear interpolation, on float32 Marcap cast to float64; **ALL iff float32 Marcap_t ≥ cut**; features stored as float32 before ranking | Q:L230; LOG#39 |
| C4-7 | Rebuilt KOSPI "over stocks ... with a valid cleaned return" (ambiguous) | **"Valid cleaned return" = a finite cleaned return r_{i,d} (main variant, steps 1-2), zero-volume days included (it is NOT the VALID set), with Marcap_{i,d−1} > 0, the KOSPI market code at d−1 and a code ending in '0', of any name class.** Scaled to the official close of 2,064.85 on 2007-10-31. Check values 1,457.46 / 9,120.19 / 5,599.30 on 2020-03-19 / 2026-06-22 / 2026-07-30 (restricting to VALID would give 1,450.51 / 9,089.28 / 5,577.72) | Q:L242; LOG#51 (coordinator F3) |
| C4-8 | Weekly reversal feature undefined (R3 only lists GV-183/GV-189) | `REV_1W = exp(CL[t] − CL[t−5]) − 1` at the weekly formation (last trading day on or before Friday); weekly L/S golden values hold quintile 1 long and quintile 5 short. `REV_1M = exp(CL[t] − CL[t−21]) − 1` | Q:L198; LOG#7 |
| C4-9 | Cost application unspecified per basis | Monthly basis: subtracted from the period's compounded gross return, R_net = R_gross − c × turnover. **Daily basis (the gate): subtracted from the return of the first session the new weights earn (t+1).** c = 35 bp per side (70 bp stress), on each book's own turnover | Q:L231; LOG#40 |
| C4-10 | "ChangeCode is absent in the 2026 data" | ChangeCode **4/5 (the old limit codes)** are absent in the 2026 data, which carries only the values 1-3 (affects how `lu_lock` must be derived in 2026) | Q:L147, L199; LOG#8 |
| C4-11 | R3 G-15 / TF-08 label the breadth figures "KOSPI H1-2026" (R3:L169, L812) | Window is **2025-12-30..2026-06-22** (2025 close to the June peak): CW +117.1% vs EW +3.4%, CW ex-pair +41.7%, 64.9% fell. "H1-2026" elsewhere (IDX-1, RISK-2, macro §8.6) is the calendar half-year (KOSPI +101.1%). "The H1-2026 melt-up" for the pair-cap window (2 Jan-22 Jun) was left as an episode name | Q:L134, L164, L195 |
| C4-12 | R3 XS-19: "DNB-TF-11 matches item 26 (value timing presented as compliant)" (R3:L1307) | Macro §10 item 26 is "Value-timing golden values presented as compliant" (H.10/H.15 data timing) — **unrelated** to valuation-based market timing. DNB-TF-11 is a new item, not a duplicate of item 26 | Q:L178 |
| C4-13 | R3 spec destinations "§TF-1..§TF-9" with a fundamentals section TF-6 (FUND-1 KR-VQ, FUND-2 US-VQ) (R3:L128, L652, L1385) | The spec's item sections are **§5.1-§5.9** (mapping in D.2); **FUND-1/FUND-2 are not spec items**: KR-VQ and US-VQ are backlog BL-TF-10 / BL-TF-12 and enter the spec only after the PIT store exists **and the card passes the gate** | Q:L165, L212-221, L314 |
| C4-14 | Step 9 printed by the lab harness as 0.4 × diff (`r2_kr_excl_gate.csv` column `g9_haircut_ann_diff` = 0.0123058 → +1.23%/yr; `r2_kr_04_exclusion.py` line 316 `0.4 * ann_diff`) | **Step 9 = 0.6 × OOS everywhere** (B1/F4: 0.6 × 3.08% = +1.85%/yr, arithmetic, GV-523). The +1.23% print is GV-131 and "must **not** be reproduced by the harness". Local file also carries `g9_haircut_ir` 0.61181 (= 0.4 × 1.5295) — same bug | Q:L63-64, L172, L267 |
| C4-15 | "−2.95%/month (t −3.77)" anchor cited to "macro §2.2 and R-15" | Printed in macro §2.1 (row "Two simplest families") and macro backlog BL-U02; §2.2 and R-15 carry only the reversal weight 3. XS-02 macro item reads "R-15 Korea ST reversal 3; §2.2 KEEP Korea reversal 3; §2.1 'keeps 1-5-day reversal'" | Q:L146, L196, L204 |
| C4-16 | R3 XS-01 cites "R-15 flow prior" (R3:L1289) | Macro R-15's table has no flow column; the flow weight 3 is macro §2.2 KEEP (open finding 10, not edited) | Q:L313 |
| C4-17 | Issuance tilt IR 0.35-0.38 (2017-26) cited to prof log line 48 | V048 = line 49; line 48 = V047 (IR 0.48-0.54, 1996-2026). The circulated 0.84 is wrong (CA-03) | Q:L148-149, L200 |
| C4-18 | Best-variant DSR 0.979 cited to `r2_kr_excl_gate.csv` line 2 | 0.978629 is in `r2_kr_excl_dsr_best.csv` line 2; `r2_kr_excl_gate.csv` line 2 holds the pooled 0.939134 (n_trials 176), PBO 0.0480186 | Q:L60-62, L208 |
| C4-19 | Report: low-vol "beat the value-weighted market in all seven crash windows" | EW book 6 of 7 (1997-98: −42.2% vs −33.1%); VW book 7 of 7; "nine of ten rebounds" = EW 5 of 5 + VW 4 of 5 (R3:L494 already correct) | Q:L110-111, L207 |
| C4-20 | Page: "no rule beat buy-and-hold on return" (303 KOSPI rules) | 44 of 303 rules had a positive mean excess (best MACD(12,26,1) +1.16%/yr, t 0.34); correct wording "no rule beat buy-and-hold once the search is accounted for" (SPA p 0.8805) | Q:L80, L209 |
| C4-21 | SPY 52-week breakout Sharpe 0.39 at 50 bp (from `US_datalab_summary.md` line 73) | 0.3845 → **0.38** (`us_B_daily.csv`). The lab summary still misrounds (0.43 / 0.42 / 0.39 / 0.34 vs 0.425 / 0.421 / 0.385 / 0.343; RSI(14) at 5 bp 0.27 vs 0.2648) — lab file not edited | Q:L124, L210, L308 |
| C4-22 | Crowding paragraph: "Crowded winners then kept outperforming for more than two years" | Removed (a 2023 article cannot support it); restated as a T3-labelled past fact. Source tiers: T1 academic/official, T2 bank and asset-manager research, T3 trade press and aggregators | Q:L286-287, L310 (coordinator F5) |

### C.5 Exact definitions added by QA (verbatim; all now part of the spec's §4.2-§4.4, §4.8, §8.4, §9.3)

**Name classifier (spec §4.3, eligibility condition 2; LOG#39; transcribed from `kr_common.py` lines 61-84).** Delete all whitespace from the row's Name (the row's own Name on day t), then test the patterns below in order (Python `re.search`, unanchored unless the pattern says otherwise). The first match sets the class; a name with no match is an operating company.

```text
1 SPAC        스팩|SPAC|기업인수목적
2 REIT        리츠|코크렙|REIT|리얼티\d*$|^교보메리츠|^유레스메리츠|맥쿼리센트럴
              searched in the name with 메리츠 and 블리츠 replaced by '#'; a name starting with
              교보메리츠 or 유레스메리츠 is searched unmasked; the name 인터리츠 is never REIT
3 INFRA_FUND  맥쿼리인프라|발해인프라|인프라펀드|인프라투융자
4 FUND        선박투자|\d+호|[가-힣]{2,}(?:일|이|삼|사|오|육|칠|팔|구|십|십오)호(?:-?MF)?$|-?MF$|펀드|뮤추얼|경매|베트남(?:개발)?\d$|유전\d|유전$
5 DR_ETN      ETN|KDR
```

Examples (= test cases): 메리츠화재, 블리츠웨이, 두산인프라코어 and 인터리츠 are operating companies; 맥쿼리센트럴 and 교보메리츠 are REIT; 바다로3호 and 박현주1호 are FUND; 맥쿼리인프라 is INFRA_FUND.

**Known fragments of the spec's eligible set (§4.3):** seven conditions; condition 2 = "Operating company: no SPAC, REIT, infrastructure, ship or other fund, KDR or ETN"; condition 7 = "No beyond-limit move without a corporate action in t−29..t"; KONEX rows and non-'0' codes dropped; KOSDAQ ↔ KOSDAQ GLOBAL is the same market; `ALL` = eligible names with Marcap_t ≥ the 20th percentile of eligible Marcap_t (the microcap screen); `LARGE` = the top 200 (Q:L197, L229-230, L238). Conditions 1 and 3-6 are not printed in any file read here.

### C.6 Edit log (`qa/qa_edit_log.json`)
- Structure: JSON list of 107 objects; keys `file`, `location`, `old`, `new`, `reason`, `source`, plus optional `batch`. **There is no severity field.**
- By batch: original v1.0.1 pass (no `batch`) 36; `coordinator F1` 47 (statistic basis labels + daily rows); `coordinator F2` 13 (tie rules, classifier, padding, tolerances, test expectations); `coordinator F3` 1 (index definition); `coordinator F5` 2 (crowding source); `coordinator log` 8.
- By file: spec 65; backlog 7; report 10; page 25.
- Entries that change what an implementer builds or tests: LOG#6, #7, #8, #37-47 (definitions + three test expectations T-TF-SCR-02 / T-TF-CA-01 / T-TF-UNIV-01), #48-50 (tolerances), #51 (index), #40, #57, #61-62, #77 (basis + new golden rows G-TF-SCR-15..16). Everything else is a label, citation, version or log edit.
- Entries #34-36 record that a "## QA log (v1.0.1)" appendix was added to the spec and backlog and a one-paragraph "QA note (v1.0.1)" to the report; the log does not hold their text.

### C.7 Rule scan results (Q:L169-176) — all PASS
- P0: no order path or broker adapter anywhere; the spec's simulated `fill_record` is a simulated-book record; macro §10 item 21 is inherited.
- Overlay multipliers in [0.5, 1.0], nothing above 1.0: every multiplier statement states the bound (T-TF-CAP-01, IDX-0, FS-1, BL-TF-19); vol weights are min(1, ·).
- Step 9 = 0.6 × OOS everywhere; 0.4 × appears only as the flagged lab bug (CA-21, GOV-6, XS-13).
- Costs never lowered: 35 / 70 bp KRX stock, 3 bp ETF, 50 bp US, 10 bp crypto; "futures cost" (5 bp) is the pre-registered futures rate (macro P10), used only for a separate instrument card (BL-TF-08).
- Cross-spec amendments are presented as **owner decisions** (spec §13 header "Each row is an owner decision"; XS table column "Recommended answer (owner decision)").
- No contradiction of the macro spec: every change to a macro weight or text is an XS proposal for the owner; DNB-TF items extend macro §10; R-03/R-04/R-06/R-07 are referenced, not changed.

### C.8 Open QA findings (Q:L300-315)
Resolved by coordinator decision: 1 (F1 basis), 2 (F2 tolerance), 3 (F2 tie rules/classifier), 4 (F3 index), 7 (F5 crowding source). **Still open:**

| # | Finding | Implementer consequence |
|---|---|---|
| 5 | `US_datalab_summary.md` misrounds (line 73: 0.43 / 0.42 / 0.39 / 0.34 vs 0.425 / 0.421 / 0.385 / 0.343; line 69 RSI(14) at 5 bp 0.27 vs 0.2648) | Take US values from `datalab/results/us/us_B_daily.csv`, not the summary |
| 6 | Weekly reversal gross mean +19.93%/yr (lab) vs +20.08% (weekly ×52) / +19.73% (daily ×252) | Do not pin the gross mean at printed precision; pin Sharpe, net Sharpe, turnover, break-even |
| 8 | Report line 106 calls VW 1-month reversal "about zero gross"; lab value +0.57%/month (t 0.94) | Use "insignificant gross (+0.57%/month, t 0.9)" |
| 9 | Spec MOM-1 and §8.10 cite GV-251..260 for rows that print only part of that range | Harmless |
| 10 | XS-01 cites "R-15 flow prior"; R-15 has no flow column (flow weight 3 is macro §2.2 KEEP) | Cite §2.2 |
| 11 | Page JSON nodes TF-36 / TF-43 still read "FUND-1 / FUND-2 when the point-in-time store exists" | Activation also requires a gate PASS |
| 12 | Panel denominator: spec 13,949,140 finite returns vs QA 13,949,153 (+13 rows); same numerator 12,186 and ratio 0.0874% | "Counts are 'exact' in §9.3, so a production build should confirm which rows differ (likely the step-2b′ halt-resumption detail)" |

---

## D. The missing deliverables: `QUANTGEN_TECHFUND_INTEGRATION.md` / `QUANTGEN_TECHFUND_BACKLOG.md`

### D.1 Where they are named
- README L3: "This bundle holds everything behind the three deliverables (QUANTGEN_TECHFUND_INTEGRATION.md, QUANTGEN_TECHFUND_BACKLOG.md, and the research report)." The bundle contains the trail, **not** the deliverables.
- QA_report L9: `/home/claude/deliverables/QUANTGEN_TECHFUND_INTEGRATION.md` (spec, v1.0.1), `/home/claude/deliverables/QUANTGEN_TECHFUND_BACKLOG.md` (backlog, v1.0.1), `/home/claude/reports/QUANTGEN technical and fundamental signals.md`, `/home/claude/page/quantgen_signal_neural_link.html`.
- qa_edit_log.json: 65 spec edits + 7 backlog edits with old/new text.
- Verified: no file matching `*TECHFUND*`, the report, the page or `golden_values.csv` exists under `C:/Users/whydi/OneDrive/Desktop/QUANTGEN` outside the bundle folder name. R3 (`R3:L128`) is the draft the spec was built from.

### D.2 Spec skeleton reconstructed from QA citations

Title: `# QUANTGEN — Technical and Fundamental Signals Integration Specification (v1.0.1)` (LOG#1). Header table with "Companion files": "(1) `QUANTGEN_TECHFUND_BACKLOG.md` (v1.0.1): everything not built here" (LOG#2). Changelog (LOG#3, #98, #105). Ends with "## QA log (v1.0.1)" then "*End of specification.*" (LOG#34).

| Spec § | Content (as far as the QA files reveal) | Evidence |
|---|---|---|
| §0.2 | Scope rule: KR-VQ / US-VQ are not spec items; each enters (as FUND-1 / FUND-2) only after its PIT store exists and its card passes the gate | Q:L217, L221 |
| §0.4 | Headline evidence list; item 2 = SCR-1 (IR 1.53 monthly / 1.64 daily; KRX 1996-03..2026-09; `r2_kr_excl_summary.csv` line 11; GV-002, GV-004) and SCR-2 (IR 0.65 monthly / 1.03 daily; line 17; GV-015, GV-017) | Q:L243-244 |
| §0.5 | Existing card record: C3 1.22 [0.62, 1.77] vs 0.79, p 0.04, 1.17 at 2×, 13.7×/yr; B3 futures TS-mom REJECT 0.08; V3 G10 FX −0.59 | Q:L144-145 |
| §1.2 | Thesis points TP-1..8 (TP-2 = breadth/concentration evidence, line 163) | Q:L134, L180, L195 |
| §2.2 | Weights: prior per market (0-3, context line 46), final Korea / US / crypto / futures, other-market rows; = `r3_weights_final.csv`, `r3_weights_other_markets.csv` | Q:L78, L141-143, L166 |
| §2.3 | Corrected-anchor table (row "Korean 1-month reversal", line 275; VW ex-microcap deciles +0.57%/month (t 0.9), −0.68% net 35) | Q:L109, L146, L196 |
| §4.2 | KRX panel cleaning: "Rows kept" (line 484), segments, transfer resets, steps 2a/2b/2b′/2c, VALID set, DIL inputs; code padding; check value GV-209 | Q:L150, L197, L228; QR:L10 |
| §4.3 | Universe and features: eligible-set table (7 conditions), name classifier, numeric types, ALL / LARGE, features table (REV_1M, REV_1W, …), book mechanics (Costs row), the book engine for B1-B4 | Q:L198, L229-231, L238; QR:L12 |
| §4.4 | Corporate actions / dilution: share-count change day, split-like day, DIL_LIT, F6 flag tie rule | Q:L232-234 |
| §4.5 | Limit-lock flags (`lu_lock`, line 582), ChangeCode | Q:L147, L199 |
| §4.8 | Rebuilt KOSPI definition (variants; scale 2,064.85 on 2007-10-31) and VT20 vs S | Q:L242; QR:L11 |
| §5.1 | Execution invariants (INV-1..INV-5) | Q:L212; R3:L128 |
| §5.2 | Data layer (DATA-1..DATA-6; DATA-6 = investor-flow logging) | Q:L213; R3:L1289 |
| §5.3 | Screens (SCR-1 lottery F4, SCR-2 dilution F6, SCR-3 = F1 turnover screen per golden rows G-TF-SCR-10..11). Each item is a table with rows such as **Formula**, **Evidence (gross and net)**, Failure modes. SCR-1 evidence: B1 EW +3.39% gross, +3.08% net 35, +2.76% net 70; IR 1.53, NW t 8.34; B2 capped VW +0.99 / +0.85 / +0.72, IR 0.68; B3 top-200 +0.57 / +0.49 / +0.40, IR 0.39; B4 momentum Q5 +6.76 / +6.13 / +5.50, IR 1.24; pooled DSR 0.939 over 176 trials; best-variant DSR 0.979; PBO 0.048; step 9 +1.85%/yr; flag overlap Jaccard 0.13. SCR-2 formula: "Flag DIL_LIT > 0.10 on the float32-stored value (a missing DIL_LIT counts as 0, i.e. not flagged) ... Removed at t; the book earns from t+1." SCR-2 evidence: +2.42% gross, +2.34% net 35, +2.26% net 70; IR 0.65, NW t 3.93; 81% of years | Q:L45-66, L235, L245-247, L251 |
| §5.4 | Momentum risk and concentration (MOM-1 vol scaling: crash L/S VW static −40.29%, scaled −10.52%, same exposure −22.95% (0.53); 12-1 L/S EW static Sharpe 0.20 / −0.20 in 2016-26. MOM-2 D-M gate: 9 onsets 1996-2026, 3 since 2000. RISK-1 caps + CR-07 pair share; RISK-2 also exists) | Q:L113, L151-152, L132, L164, L215 |
| §5.5 | Index protective rules (IDX-0 overlay bound; IDX-1 KOSPI VT20: ΔMDD +6.5 pp (2×: +6.44), tail 0.70, p_ni 0.0505, block 186, 6 of 13 episodes, Jul-2026 38%) | Q:L69-71, L171, L216 |
| §5.6 | The five FORWARD-SIM cells FS-1..FS-5 (FS-1 floored trend × VT20: +15.4 pp vs own S, tail 0.64; FS-3 KRX low-vol vs S_beta: ΔMDD −22.4 / −7.1 / −12.2 pp, tail 0.985 / 0.978 / 0.967, CAPM alpha +2.23% (t 0.80) / +0.73% (t 0.34), lagged 9 of 10 rebounds) — section number inferred from the §5.1-§5.9 ordering | Q:L77, L111, L155-156, L221 |
| §5.7 | Combiner (ML-1) | Q:L219 |
| §5.8 | Crypto (CRY-1 = C3) | Q:L144, L220 |
| §5.9 | Governance GOV-1..GOV-11 (GOV-1 long-only primary statistic + benchmark set, line 1047; GOV-5 gate power 15.8 / 40.3 years; GOV-6 step 9; GOV-9 stress reporting — EW universe −18.2% gross in the 2026 crash; GOV-11 protective cards not judged on step 5 — VT20 step-5 p 0.51) | Q:L72, L101-103, L114, L153, L201, L218 |
| §8.4 | Paired evaluation of screen cards (C4-1) | Q:L248 |
| §8.10 | "Indicative verdicts (from the R2 labs; **not a run of the app's gate**)" table; card ids `TF-SCR1-KR-EW`, `TF-SCR2-KR-EW` | Q:L249-251 |
| §9.1 | Acceptance tests `T-TF-*` (D.3) | Q:L236-238 |
| §9.3 | Golden values: reference data and construction (line 1807), tolerance table (C.3), golden tables `G-TF-SCR-01..16`, `G-TF-IDX-*` (G-TF-IDX-23 = VT20 crash −12.2% vs −38.6%); "Every golden value lives in `tests/fixtures/techfund/golden_values.csv` under its GV id, with its source file and line"; 523 = 497 traced + 20 derived + 6 untraced; a `lab_reference` run reproduces each row on its own basis | Q:L73, L157, L202, L239-241, L252-268 |
| §10 | DO-NOT-BUILD list DNB-TF-01..17 (extends macro §10; note on item 26) | Q:L176, L178, L269 |
| §11 | Evidence / regime table (Breadth row, line 2018) | Q:L135, L203 |
| §13 | Cross-spec amendments. §13.1 XS-01..22 ("Each row is an owner decision"; column "Recommended answer (owner decision)"); §13.2 open questions OQ-01..15 (OQ-02 pair-share denominator / first > 0.45 dates; OQ-07 rebuilt/official KOSPI ratio range 0.9987-1.0023; OQ-14 F1 vs F4: F1 B1 +4.28%/yr net 35, IR 1.15) | Q:L65, L67, L132, L175, L204, L270 |
| §14 | Item → evidence trace table (rows such as SCR-1 "+3.08%/yr net 35, IR 1.53 monthly basis (GV-001..013)", SCR-2 "(GV-014..026)") and the fictional-persona statement | Q:L174, L271-272 |

Sections §1.1, §2.1, §3, §4.1, §4.6-§4.7, §6, §7, §8.1-§8.3, §8.5-§8.9, §9.2, §12 are **not cited** in any file read here; their content cannot be reconstructed from these sources (R3:L961 mentions a "section 12, CA-21" corrected-anchor list in R3's own numbering).

Known DNB-TF items (Q:L94-95, L103-106, L269; R3:L1307): DNB-TF-01 attention-fade (F5) as a monthly screen ("adding it to SCR-1 (F8) lowers the monthly-basis IR from 1.53 to 0.67"); DNB-TF-02 low-vol long-only tilt (LO excess +1.1% EW (t 0.5), −1.8% VW (t −0.6)); DNB-TF-03 size (L/S EW gross Sharpe 0.39; top 200 −0.23); DNB-TF-04 raw Korean 12-1 (LO excess −1.3% (t −0.6); L/S +9.3% gross, Sharpe 0.45; net 35 0.20; net 70 −0.04); DNB-TF-06 flow direction (repeats macro item 14); DNB-TF-07 weekly reversal (net-35 Sharpe −1.78, break-even 12.5 bp); DNB-TF-11 valuation-based market timing; DNB-TF-13 price/SMA200 selection (L/S Sharpe −0.05 gross; long-only excess −5.6%/yr net 35); DNB-TF-14/15 extend macro item 11. Full list: R3 section 6.

### D.3 Acceptance tests and golden rows named in the QA files

| Test id | Name | Expectation (verbatim, post-QA) | Evidence |
|---|---|---|---|
| T-TF-SCR-02 | SCR-2 formula | DIL_LIT 0.11 → flagged; a 10.0% increase (s = 1.1, DIL_LIT stored as float32 0.1) → flagged (§4.4 tie rule); 0.099 → not flagged; missing → not flagged | Q:L236 |
| T-TF-CA-01 | corporate-action / DIL_LIT rule (name not printed) | ...a 20% rights issue with the close −5% → not split-like (included); a 5:1 reverse split with the close × 4.75 (\|s × p − 1\| = 0.05) → split-like; DIL_LIT matches exp(Σ ln s) − 1 | Q:L237 |
| T-TF-UNIV-01 | Universe rules | Each of the seven eligibility conditions of §4.3 excludes a constructed name; KONEX rows and non-'0' codes are dropped; a code stored as '5930' is read as '005930' before the filters; the §4.3 classifier returns operating for 메리츠화재 and 인터리츠, REIT for 맥쿼리센트럴, FUND for 바다로3호 and INFRA_FUND for 맥쿼리인프라; ALL = float32 Marcap ≥ the 20th percentile of eligible; LARGE = the top 200 | Q:L238 |
| T-TF-CAP-01 | multiplier bound (name not printed) | every multiplier statement states the bound [0.5, 1.0], nothing above 1.0; vol weights are min(1, ·) | Q:L171 |

Only these four `T-TF-*` ids appear in the files read; the numbering (SCR-02, CA-01, UNIV-01, CAP-01) implies families `T-TF-SCR-*`, `T-TF-CA-*`, `T-TF-UNIV-*`, `T-TF-CAP-*` with more members that are not recoverable here.

Golden table `G-TF-SCR` (KRX, 366 formations 1996-03..2026-09; filtered minus unfiltered; sources `r2_kr_excl_summary.csv`, `r2_kr_excl_long.csv`, `r2_kr_excl_gate.csv`) (Q:L253-268):

| Row | Item | Basis | Values known |
|---|---|---|---|
| G-TF-SCR-01 | SCR-1 F4 / B1 | monthly (R2 lab) | 3.3884 / 3.0764 / 2.7645 %/yr; IR 1.5295 |
| G-TF-SCR-02 | SCR-1 F4 / B1 sub-periods (net 35) | monthly | +4.31 / +2.81 / +2.20 |
| G-TF-SCR-03 | SCR-1 F4 / B2 | monthly | +0.99 / +0.85 / +0.72; IR 0.68 |
| G-TF-SCR-04 | SCR-1 F4 / B3 (reference) | monthly | +0.57 / +0.49 / +0.40; IR 0.39 |
| G-TF-SCR-05 | SCR-1 F4 / B4 | monthly | +6.76 / +6.13 / +5.50; IR 1.24 |
| G-TF-SCR-06 | SCR-2 F6 / B1 | monthly | 2.4164 / 2.3363 / 2.2563; IR 0.6453 |
| G-TF-SCR-07..09 | SCR-2 F6 / B2, B3 (reference), B4 | monthly | in `r2_kr_excl_summary.csv` |
| G-TF-SCR-10..11 | SCR-3 F1 / B1, B4 | monthly | F1/B1 +4.28%/yr net 35, IR 1.15 |
| G-TF-SCR-12 | F5 (DROP) break-evens B1 / B2 / B3 / B4 | monthly | — |
| G-TF-SCR-13 | Best of 176 trials (B1, F4 cut 5%): pooled DSR | monthly | 0.979 |
| G-TF-SCR-14 | Step 9 for B1/F4 = 0.6 × 3.08% (derived; GV-523); the lab's 0.4 × print +1.23% (GV-131) must not be reproduced | monthly | +1.85%/yr |
| G-TF-SCR-15 | SCR-1 F4 / B1 | **daily (QA recomputation)** | +3.43% / +3.12% / +2.80%; IR 1.64 (gross IR 1.82; net-70 IR 1.47) |
| G-TF-SCR-16 | SCR-2 F6 / B1 | **daily (QA recomputation)** | +2.56% / +2.48% / +2.40%; IR 1.03 (gross IR 1.07; net-70 IR 1.00) |

G-TF-SCR-15..16 are QA recomputations (`qa17d_costconv.py` → `qa_exact_costconv.json`, not shipped) and are "not GV rows" (Q:L274).

Local material that can seed the fixtures: `datalab/results/r3/r3_golden_values.csv` (523 rows; columns `gv_id, card_or_rule, decision, quantity, market, period, gross_net, value, raw, source_file, line, status, note`), `datalab/results/r3/r3_go_nogo.csv` (77 rows), `r3_weights_final.csv` (50 cells), `r3_weights_other_markets.csv` (6 rows), `r3_pair_share*.csv`, and the R2 result CSVs. Not shipped: `kr_index_sanity.csv`, `kr_event_windows.csv`, `kr_ls_correlation_ALL_EW.csv`, `kr_chart4_quintiles_2025_2026.json`, `r2_idx_chart_a_kospi_2024_2026.json`, `c12_lowvol_samebeta.csv`, `exec_chair_checks/*`, `/home/claude/qa/*`, the marcap parquet files and `/home/claude/data_raw/us/`.

**Reference implementations that DO ship locally** (`QUANTGEN_techfund_research_bundle/QUANTGEN_techfund_research/scripts/`; line numbers verified against the QA citations): `kr_common.py` lines 61-84 (`classify_name` and its five compiled patterns, `_NOT_REIT = ('인터리츠',)`); `kr_01_build_panel.py` (code `zfill(6)`, float32 panel); `kr_02_signals.py` (features, REV_1W); `r2_kr_01_build_extra.py` lines 180-191 (`s`, `p`, `chg = |s − 1| > 0.001`, `splitlike = chg & (|s − 1| > 0.05) & (|s × p − 1| <= 0.05)`, `lit`, cumulative sums; `p` also requires previous close > 0); `r2_kr_04_exclusion.py` line 84 (`F4 = p6_composite(F, k, U[k], 0.10)`), line 86 (`F6 = np.nan_to_num(DIL_LIT, nan=0.0) > 0.10`), line 87 (`F7 = F1 | F2 | F3`), line 316 (the `0.4 *` step-9 bug in both `g9_haircut_ann_diff` and `g9_haircut_ir` — do not port); `kr_05_index_timing.py` (`build_index(include_vehicles=True)`); `r2_kr_common.py` (statistics conventions, bootstrap, DSR, CSCV). They read the marcap parquet files, which are not on this machine, so they are porting references, not runnable checks.

### D.4 Backlog skeleton
- Title `# QUANTGEN — Technical and Fundamental Signals Backlog (v1.0.1)`; header with companion `QUANTGEN_TECHFUND_INTEGRATION.md` (v1.0.1, "the spec") and the fictional-persona note; ends with "## QA log (v1.0.1)" then "*End of backlog.*" (LOG#14-15, #35; Q:L174).
- **BL-TF items: 44 = S01-S05, 01-21, R01-R02, D01-D16** (Q:L180). Each item carries a priority, a settling test, a weight and a classification (Q:L294). Named: BL-TF-08 (separate instrument card at the 5 bp futures rate), BL-TF-10 (KR-VQ composite: value + profitability + net issuance, weight 2, split at 2024-02-26; has a "PASS requires" field), BL-TF-12 (US-VQ composite: value + profitability + investment + issuance, weight 2), BL-TF-14 (event cards; R3:L165), BL-TF-19 (a multiplier item with the [0.5, 1.0] bound stated).
- §7 failure archive FA-01..24 (FA-01 = attention-fade F5; "adding it to SCR-1 lowers the monthly-basis IR 1.53 → 0.67") (Q:L273).
- §8 note and Appendix D C-1 carry the item-26 mapping (Q:L178).
- Corrected anchors CA-01..38 (CA-03 the 0.84 issuance IR; CA-07 gate power; CA-12 end-2023 pair-share alternatives 26.88 / 27.79%; CA-21 step 9 ×0.6).
- Appendix T: T.2 = all 523 golden values (columns: GV id; item; …); "Screen golden values (GV-001..170) are on the monthly basis (R2 lab)"; rows GV-497..500 and T.3 quote the verification logs verbatim (monthly basis) (Q:L274, L297).

### D.5 ID families the deliverables use (Q:L180) — keep these ids verbatim in code/tests
`XS-01..22`, `OQ-01..15`, `DNB-TF-01..17`, `BL-TF-*` (44), `FA-01..24`, `CA-01..38`, `CR-01..12`, `TP-1..8`, `TF-01..70` (R3 nodes), `GV-001..523`, `G-01..77` (go/no-go register), item prefixes `INV`, `DATA`, `SCR`, `MOM`, `RISK`, `IDX`, `FS`, `ML`, `CRY`, `GOV`, tests `T-TF-*`, golden tables `G-TF-*`.
Register counts: 77 = 29 / 5 / 20 / 6 / 17 by decision label (report); page view 29 go (9 build now, 6 invariants, 14 governance), 28 wait, 3 context, 17 drop; 3 owner decisions (Q:L137-138, L166). Node classes 29 / 18 / 11 / 8 / 4 (by rule 28 / 16 / 11 / 11 / 4) (Q:L139).

---

## E. Cross-panel differences between sections A and B (R3 reconciles; do not pick a side from this note)

| Topic | Professors | Executives |
|---|---|---|
| Entry timing | "next-open entry for holding periods of 5 sessions or less" (P:L612); F7: decide at close t, trade at t+1 (P2:L644) | Primary fill KRX official close t; conservative bound close t+1; momentum/trend entries at the close, not the next open (RX-01, RX-02) |
| Bands | enter top 20%, exit below top 40% (P:L94) | enter top decile or quintile, exit below top 3 deciles or the quintile; turnover target ≤ 30%/month, hard limit 50% (RX-09) |
| Bootstrap block | >= max(Politis-White, 2 x holding period) (P:L615) | max(10, Politis-White) (MC-18); lab used max(10, PW(d), PW(d^2)) (IDX2:L42) |
| Step-9 haircut | "flat 60% Sharpe haircut" / "60% live haircut" used as ×0.4 (P:L244: 0.42 → 0.17) | live = 0.6 × OOS; ×0.4 refuted (E:L617, A2) — QA confirms ×0.6 (Q:L172) |
| KR quality / value / momentum | quality 2 (composite only); value 2; XS-mom 1 as 12-7 / 52wH feature | quality 1; value 1 (E4: 2); raw 12-1 0 + one FORWARD-SIM variant at 1 |
| KR low-vol protective | 2 | 1 (descriptive); CARD-P claim withdrawn vs S_beta |
| KR exclusion screens | lottery protective 3 (EW/small-mid), issuance 2; "BUILD-candidate" | screen 3 and screen 3; "BUILD NOW" (as screen cards, gated) |
| US XS-mom / earnings drift / index trend protective | 1 / 0 / 1 (trend) + 1 (vol target), futures cost only | 2 / 1 / 2 (3 only at ≤ 5 bp) |
| Stress windows | 2008-09, 2020-03, 2025-01 to 2026-06, 2026-06-23 to 07-30; worst rolling 21- and 63-session net excess (P:L617) | RX-15 list; worst five-week relative loss |
| Eligibility | no preferreds, SPACs, REITs, funds, warning-designated stocks, prices under KRW 1,000 (P:L612) | RX-05 adds cap ≥ ₩100bn or top 500, 20-day ADV ≥ ₩1bn, listed ≥ 60 sessions, administrative/caution, halted, DART windows, IPO/relisting days; t−1 data |
| D-M gate onsets (Korea) | 9 in 30 years | 3 since 2000 (chair) / 9 in 1996-2026 (R2) — same fact, different window |
| Sell tax history | 0.30% (2019), 0.15% (2025), 0.20% from 2026-01-01 | 0.18% (2024), 0.15% (2025), 0.20% (2026) |
| Pair share 2026-09-29 | 52.6% (KOSPI common-share cap) | 50.8 / 52.6 / 53.7% by denominator; QA: CR-07 = 53.71% with (005930 + 005935 + 000660) / all KOSPI lines |

---

## F. Ambiguities (conservative reading = no exposure change, specification book only, fail closed)

| # | Issue | Lines | Conservative reading |
|---|---|---|---|
| F-1 | Step-9 multiplier: professors' text says "flat 60% Sharpe haircut" and computes ×0.4; executives, macro §8.1 and QA say expected live = 0.6 × OOS | P:L244, L432, L624; E:L610-617, L666; Q:L172 | Implement 0.6 × OOS only. Step 9 is report-only; if both haircut displays are kept (PX-T-04), label them and never let either feed a verdict or exposure |
| F-2 | Bootstrap block length has three formulas | P:L615; E:L794; IDX2:L42 | Use the largest: max(10, PW(d), PW(d²), 2 × holding period). A longer block can only make steps 2/5 harder to pass |
| F-3 | Family-gate SPA threshold: P2 0.10 vs P4 0.05; P2 F1 printed "mean block 10 sessions" although round 2 shows 10-session blocks over-reject the null | P:L454, L606; P2:L630-631 | p <= 0.05 at 1x costs; block per F-2; at least 2,000 resamples |
| F-4 | Ladder threshold units (fixed % vs σ of declared book vol) and book vol target are owner decisions | E:L595-605, L777, L792 | Keep macro R-07 fixed −8 / −12 / −15% in the displayed/spec book; σ-unit variant only in FORWARD-SIM; no book-vol-target change without owner decision |
| F-5 | Cumulative vs non-cumulative ladder steps: evidence "mixed"; SPY result not re-run by the chair | E:L221, L779, L1100 | Non-cumulative (chair + MC-03), as a clarification of R-07; flag as owner-confirmable |
| F-6 | Pair-share denominator: executives print 50.8 / 52.6 / 53.7% and "first above 0.45 on 7 May 2026", cap "bound on 98 sessions"; QA under CR-07 prints 53.71%, first > 0.45 on 2026-05-06, 99 of 181 sessions, peak 59.69% on 2026-06-25 (vs executives' 57.1% / 58.9%); a fourth alternative 53.96% is not defined in these files | E:L157, L234, L669; Q:L35, L130-133 | Use the CR-07 definition (005930 + 005935 + 000660) / all KOSPI lines — the highest-reading documented denominator among the three defined, so the 0.35 cap binds earliest. R3 G-14 marks it "INVARIANT (owner to confirm)" |
| F-7 | Entry timing conflict (next-open for ≤ 5-session holds vs close fills) | P:L612; E:L756-757 | Simulated books only (no order path). Primary fill at the official close t per RX-01/RX-02; always also report the close t+1 bound and a skip-day variant for holdings under one month; locked limit-up entries move to the t+1 open (RX-03). Defer to R3 INV items |
| F-8 | "No new long within 5 sessions of a locked limit-up or volume spike" appears in EX-T-04 but not in the RX-03 row; "volume spike" threshold not restated there (F5 uses volume >= 5x the previous 20-day average with r >= +5%; the chair's DC-3 proxy uses ≥ 4x the 60-day average) | E:L509, L758, L580; KR2:L117 | Encode the exclusion as a simulated-entry filter using the F5 definition; it can only remove entries, never add exposure |
| F-9 | Buy/hold band parameters differ (20%/40% vs decile-or-quintile / top-3-deciles-or-quintile) | P:L94; E:L764 | Bands must be pre-registered per card; neither is a global default until R3/owner fixes one. Both satisfy "mandatory on monthly stock cards" |
| F-10 | Low-vol protective comparator: lab judges vs the VW market; chair vs a same-beta static book (β × market + cash); MC-11 asks the coordinator to add the definition; β estimation window not stated here (R3 G-32 says "beta_hat pre-registered") | E:L548-552, L787; R3:L834 | Use S_beta (the stricter comparator); K-LV stays descriptive FORWARD-SIM, never a CARD-P pass and never in the displayed book |
| F-11 | Review-trigger inputs undefined: which simulation produces the "95th percentile" of forward drawdown; how the 90% CI of the 12-month Sharpe is computed | E:L205, L768 | Display-only REVIEW flag; never auto-liquidate, never change exposure |
| F-12 | Impact model `Y·σ_d·√(Q/ADV20)` with "Y ≈ 1" and capacity "1-2% of 20-day ADV" are ranges, not values | E:L762 | Y = 1; capacity cap 1% (the tighter); costs may be raised by the itemised model, never lowered below 35 bp (P:L462, E:L763) |
| F-13 | "F1-F10 primitives" for the porting protocol are referenced but not enumerated in the chair resolution (PC-T-24 lists seven feature families) | P:L308, L620 | Enumerate from P7 / R3 before building; until then, ported ideas are spec-book only with N >= 100 trials |
| F-14 | Tier B+ hurdle printed as "t >= 3.4 to 3.8" in PC-T-02 and as 3.4 (cross-sectional) / 3.8 (time-series alpha) in §5.1 | P:L74, L611 | Use the §5.1 split; if the claim type is unclear use 3.8 |
| F-15 | Screen statistic basis: all R3/lab IRs are monthly-basis; the gate is daily-basis | Q:L248 | Gate on daily differences; compare to golden rows only on the same basis (G-TF-SCR-15..16 for daily) |
| F-16 | DIL_LIT boundary depends on float32 storage | Q:L234 | Reproduce the lab rule exactly (float32 DIL_LIT, strict > float64 0.10 ⇒ 10.0% flagged). The inclusive reading excludes more names, i.e. it is also the more conservative screen |
| F-17 | Panel row count 13,949,140 vs 13,949,153 | Q:L315 | Do not hard-assert the denominator; assert numerator 12,186 and ratio 0.0874% and log the denominator |
| F-18 | Chair checks c00, c03, c10, c11 are undocumented; c07 is cited for two different computations; none of the scripts ship | E:L15; XLOG row 54; Q:L136 | Treat chair-only numbers (c04, c07 cap costs, c08, c12) as evidence text, not as reproducible golden values, unless a GV row traces them (c12 → GV-469..489) |
| F-19 | Spec sections not cited by QA (§3, §6, §7, most of §8, §9.2, §12) and the remaining T-TF tests are unrecoverable from these files | D.2, D.3 | Rebuild acceptance tests from R3's register/golden table plus the four known T-TF expectations; mark every reconstructed test id as "reconstructed" rather than claiming the original numbering |
| F-20 | Sell-tax path differs between panels and omits years (2020-2023) | P:L207; E:L125 | Do not hard-code from these notes; the itemised tax must come from an effective-dated table verified against an official source. Flat 35 / 70 bp (tax-inclusive) remains the binding base |
| F-21 | Short-sale regime dates differ in granularity (professors add "index stocks only until 2023-11-05"; executives say "partial lift 3 May 2021") | P:L205; E:L142 | Encode the three-state flag 0/1/2 (open / partial ban / full ban) with the professors' dates: full 2008-10..2009-05 (exec: 1 Oct 2008-31 May 2009), full 2011-08..2011-11 (11 Aug-9 Nov 2011), full 2020-03-16..2021-05-02, partial 2021-05-03..2023-11-05, full 2023-11-06..2025-03-30, open from 2025-03-31 |
| F-22 | Weights of 2 or more "still need a PASS card"; BUILD NOW screens "feed the displayed book only after it passes the gate (P7)" | P:L544; E:L19 | No weight in sections A.4 / B.6 changes displayed exposure by itself; screens ship as gated cards whose indicative lab verdict is REVISE |
