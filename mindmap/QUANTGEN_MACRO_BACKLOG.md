# QUANTGEN — Macro Backlog (v1.2)

**As of:** 2026-10-02 (Asia/Seoul).
**Companion to:** `QUANTGEN_MACRO_INTEGRATION.md` v1.2 (the spec). v1.0 is kept unchanged as `.v1.0_BACKLOG_backup.md`.

---

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

This file holds everything that did **not** enter the spec as a BUILD NOW rule. Each item names:
- its hypothesis;
- the panel or panels that hold it;
- the evidence so far;
- why it is not in the spec;
- the exact test that would settle it, and the gate step or protective check that test feeds;
- the data still needed;
- a priority.

**Priority scale:**
- **P1**: start now. Data logging can begin immediately, or the result changes a card in the spec.
- **P2**: next quarter.
- **P3**: opportunistic.

**Rules for this file:**
- **Every test here is a model card.**
  - Its header is committed before the study run (spec §8.4).
  - It counts toward the global trial count N.
  - It is decided by the nine-step gate, or by the protective class for de-risk items (spec §8.7).
  - It is costed at QUANTGEN's pre-registered rates, with the 2× stress.
- **Nothing in §6 (failure archive) may be re-proposed without new evidence** of the kind its "reopen only if" line names.
- **Gross and net.**
  - Numbers marked "R4" (and all earlier rounds) are **gross** of costs.
  - "R4b" marks v1.1's net-of-cost or strict-timing recomputation (`results/R4b_golden_values_net.csv`).
  - "Share" is the fraction of paired block-bootstrap resamples in which the rule beats its base.
- **Abbreviations.** "N-xx" refers to the R4 neural-link nodes. "PC/PX/PR-P" are professor-panel items; "EC/EX/ER-E" are executive-panel items.
- **Read-only.** QUANTGEN never places orders. "Forward record" means the simulated order book's forward-running books in `core/engine`, with timestamped `macro_state` and `overlay_decision` artifacts.

---

## 1. FORWARD-SIM → re-gate queue (v1.0: SHADOW → BUILD promotion queue)

The spec runs two macro legs as forward-simulated cards: S1 and S2, protective class. They have their own simulated books and never enter the recommended book. The executives' other SHADOW items (S3–S7) are contested or one-sided, so they live in §2 and §3 as card candidates.

### BL-S01 — USD/KRW leg: 20-day dlog > +3% → Korea gross × 0.75 (spec R-11; node N-22, CONTESTED)

**Hypothesis (protective claim).** Sharp won weakness marks sudden-stop states. De-risking Korea gross to 0.75× reduces drawdown, compared with a same-exposure static book, with no Sharpe loss.

**Who holds which position:**
- **Professors: split** (PX-P-04).
  - Q1b and P1 would keep it on probation. It is the only leg of the prior Korea gate that survives honest timing, and the won was weakening on 79% (2020) and 87% (2021–22) of KOSPI high-vol days.
  - P6 and P2 would use KOSPI's own market data only. Under Yahoo timing the gain is +0.03, the sign flipped in Q3-2026, and nothing beats buy-and-hold on Sharpe (0.56 vs 0.63).
- **Executives: Moderate support** (EC-E-10).

**Evidence so far:**

| Variant | ΔSR (share) | Notes |
|---|---|---|
| 0.5× | +0.06 (0.95) to +0.07 (0.98), 2016–26 | 2024–26 +0.045; 2026 +0.086; ex-2020 +0.08; ex-2026 +0.08 (gross) |
| 0.5× with Yahoo-timed KRW | +0.03 (0.75) | gross |
| 0.75× (spec), R4, DEXKOUS value timing | **+0.032 (0.965)** | gross; **VALUE timing** (H.10 publication ignored) |
| 0.75× on top of the Korea vol target (VT20), R4 | **+0.042 (0.977)** | gross; 2025–26: −0.022 |
| 0.75× with one extra session of lag or Yahoo timing, R4 | +0.016 (0.76–0.78) | gross |
| **0.75×, strict H.10 publication, R4b** | **+0.001 (0.53)**; on VT20 +0.013 (0.74) | gross; 26 onsets de-clustered at 20 sessions |
| **0.75×, value timing, net of KRX ETF 3 bp, R4b** | +0.029 (0.94); on VT20 +0.038 (0.96) | turnover 2.51 a year |
| **0.75×, value timing, net of KRX stock 35 bp, R4b** | **−0.008 (0.32)**; on VT20 −0.007 (0.34); at 70 bp −0.048 / −0.057 | the edge is smaller than the cost |
| Refinements: two-speed, residual, three-way | +0.002 to +0.033 | All lose to the plain leg |

- **How often it fires.**
  - R4, value timing: on 9.0% of days; 65 raw onsets and 35 de-clustered onsets (20-session gap) over 2015–26; 11.1 transitions a year.
  - R4b, strict H.10: 9.1% of days; 26 de-clustered onsets.
- **Protective checks (R4b, spec §8.7).**
  - PC-1 fails: ΔMDD vs the same-exposure static book is +1.1 pp (value timing, 35 bp) and +0.1 pp (strict, 3 bp).
  - PC-2 fails: tail-exposure ratio 0.99–1.00.
  - In plain words, the leg is not de-risked on the worst days.
- **Failures:**
  - Near-zero coverage of the worst days in Aug-2024, Dec-2024 and Apr-2025. It was off on 4 Dec (−1.44%) and 9 Dec 2024 (−2.78%), then on from 19 Dec to 8 Jan, into the recovery.
  - Silent during the Jul-2026 crash, when the won *strengthened* 7.4%.
  - Its 28 trigger episodes were followed by +0.48% over 20 days vs +1.10% unconditional, with 57% negative. It is neither a capitulation nor a continuation signal.
  - The 60-day correlation of 20-day KOSPI and KRW changes flipped to +0.55 in Jul-2026.

**Why it is not BUILD NOW.**
- The professors are split.
- The effect is small and depends on timing: under strict publication it is zero. At KRX-stock cost it is negative.
- **Indicative card verdict: REJECT on the protective claim.** Formally the verdict is INSUFFICIENT DATA until the timestamped history (BL-G04) exists. It is Tier B under strict timing (26 < 30 onsets).
- It keeps running as a labelled forward book, as QUANTGEN does for rejected families.

**Settling test (a card revision, pre-registered):**
- **Data:**
  - the KIS USD/KRW fixing (production) and the BoK ECOS 15:30 KST close history (BL-G04);
  - KOSPI close-to-close and open-to-close returns, 2016–2026;
  - TWD and JPY closes for pooling;
  - Korean export growth and KRX foreign flows, to label the regime.
- **Method:**
  - one 0.75× leg with the fixed definition;
  - the instrument book declared on the header: the KRX ETF line or the stock book;
  - a split by KRW regime: exporter-earnings vs sudden-stop, identified by export growth and foreign flows;
  - protective checks PC-1..PC-7 with the gate's bootstrap (longer of 10 sessions and Politis–White);
  - leave-one-crisis-out;
  - onsets pooled across KRW, TWD and JPY under a rule declared on the header.
- **PASS requires all of these:**
  - PC-1..PC-6 hold at QUANTGEN's cost and at 2×;
  - ≥ 30 pooled onsets;
  - ≥ 12 months of forward record without a demotion trigger;
  - switches ≤ 2 × 11.1 a year.
- **REJECT is confirmed** if PC-1 or PC-2 fail again with the timestamped history.

**Data needed.** ECOS 15:30 USD/KRW history (BL-D13 = BL-G04); live TWD and JPY closes; KRX foreign flows (BL-D01).

**Priority: P1.** The forward record accrues from the header commit.

### BL-S02 — US rates-stress leg: 10y +40 bp over 20 days → US duration-sensitive gross × 0.5 (spec R-12; node N-24, ONE-SIDED)

**Hypothesis (protective claim).** A persistent long-end sell-off is a hostile state for US duration-sensitive equities. While the flag is on, the US market earned −15% a year (Sharpe −0.78). Halving gross in that state reduces drawdown, compared with a same-exposure static book, with no Sharpe loss.

**Who holds which position:**
- **Executives: Moderate support** (EC-E-11). Its author (E1) would keep it in the backlog; E5 would run it forward.
- **Professors: silent on this leg.** Their real-yield / term-premium regime finding (N-26) is consistent with it, but they tested no gate of this kind.

**Evidence so far (gross unless stated):**

| Test | ΔSR (share) | Notes |
|---|---|---|
| Full sample (R2 construction) | +0.041 (0.99) | — |
| On top of a vol target (cap 1.5) | +0.033 | — |
| 2020–26 | +0.109 | — |
| Ex-2022 | +0.028 | — |
| Nine-cell threshold grid | median ≈ +0.01 | 15 trials in total, which fails a BHY multiple-testing haircut |
| 10-day and 40-day windows | ≈ 0 | — |
| Forward 60-day max DD after onsets | −7.07% vs −7.17% unconditional | Fails E1's own falsification test |
| R4: on buy-and-hold, value timing | +0.038 (0.98) | **NON-COMPLIANT** (DGS10(D) used at the close of D) |
| R4: on the US vol target (VT15, cap 1), value timing | +0.037 (0.97) | NON-COMPLIANT |
| R4: 2020–26 on VT, value timing | +0.132 (0.999) | NON-COMPLIANT |
| R4: DGS10 applied one business day later | +0.010 (0.67) over 1990–2026 | 1990–2007: −0.017. Still 15 minutes early for a close decision. |
| **R4b: strict H.15, two business days** | **−0.000 (0.53)** over 1990–2026 | 1990–2007 −0.034; 2008–26 +0.025 (0.77); 2015–26 +0.053 (0.90); 2020–26 +0.084 (0.92); on VT15 −0.007 (0.39) |
| R4: 2015–26, three timings | DGS10 +0.066; ^TNX +0.071; +1 day +0.071 | ^TNX (live-feed proxy) is the only one usable as-is |
| **R4b: net of 50 bp (US shares via KIS)** | value −0.065 (0.00); strict **−0.103 (0.00)**; ^TNX 2015–26 −0.020 (0.31); on VT15 strict −0.120 | Turnover 3.60 a year = 1.80% a year |
| R4: duration-sensitive proxies (value timing) | NDX +0.039 (0.94); Russell 2000 +0.058 (0.97); small-cap proxy +0.025 (0.89) | NON-COMPLIANT; not recomputed |

- **Onsets and switches:** 50 onsets de-clustered at 60 sessions (71 at 20 sessions); 7.2 transitions a year.
- **Protective checks (R4b, strict, 50 bp):**
  - PC-1 fails: ΔMDD −3.5 pp vs the static comparator.
  - PC-2 fails: tail ratio 0.99.
  - PC-3's point estimate is below the margin: ΔSR −0.12.
- **Episode behaviour:** off in Aug-2024, Apr-2025 and Jul-2026; on for only 2 days in Mar-2026, near the low. **The flag is on in data dated from 23 Sep 2026.** Under strict timing the S2 book applies it from the close of 25 Sep.

**Why it is not BUILD NOW.**
- One-sided support.
- Multiplicity.
- The long-sample edge disappears under strict publication timing.
- At QUANTGEN's US cost the leg pays 1.80% a year for no drawdown benefit.
- **Indicative card verdict: REJECT.** It keeps running as a labelled forward book.

**Settling test (a card revision):**
- **Data:**
  - the KIS US 10y quote stamped ≤ the US close (production);
  - for history, DGS10 at strict H.15 timing (+2 business days) and ^TNX from 2015;
  - QUANTGEN's own US long book at 50 bp per side.
- **Method:**
  - one pre-registered cell (20 days, +40 bp, 0.5×), with no further grid search;
  - protective checks PC-1..PC-7;
  - leave-one-crisis-out, including excluding 2022;
  - DSR computed with the trial count of ≥ 15 already spent.
- **PASS requires all of these:**
  - PC-1..PC-6 hold at 50 bp and at 100 bp;
  - ≥ 12 months of forward record without a demotion trigger;
  - switches ≤ 2 × 7.2 a year.
- **A lower-turnover variant** (e.g., a minimum 10-session hold, which is "lengthen the holding period") is a separate card counted in N.
- **Never extend to KOSPI here.** That question is BL-C07(a).

**Data needed.** The KIS US 10y quote with timestamps; ^TNX history.

**Priority: P1.** The flag is on now, so the forward record is informative.

---

## 2. CONTESTED items

### BL-C01 — Daniel–Moskowitz floor: 0 vs 0.25 vs 0.5, and robustness without 2008–09 (N-08; PX-P-02, EX-E-05; executive K2)

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
- **Decision:** adopt the **lowest floor whose ex-top-spell ΔSR is ≥ 0 in ≥ 3 of 4 samples**. A floor below 0.5 also needs an amendment to the spec's P2 bound, through a spec revision and a new card.
- **In gate terms (v1.1):** this is the Tier A-provisional route for the R-04 card (spec §8.3). It is INSUFFICIENT DATA today: 7 spell onsets since 1990. R4b net of 50 bp on both legs: add-on +0.072 (share 0.983).

**Data needed.** None; the French files are local.

**Priority: P2.** It is cheap; run it together with BL-C12.

### BL-C02 — Should reversal be blocked in fast stress? (N-10; EX-E-01; executive SHADOW S5)

**Positions:**
- **Block it** (E5). KRX execution binds: ±30% price limits; 41 sidecars in H1-2026; 4 circuit breakers and 15 sidecars in Jul-2026. Spreads widen about 2.5×, and E-mini depth fell 68% in Apr-2025. The intraday reversal leg loses money. Short-term trading programmes lost 0.9% in Apr-2025.
- **Keep 1.0×** (Q1b, E1, and the professors' PC-P-06 "never cut").
  - Gross reversal Sharpe is 2.35 on VIX-inverted days vs 1.11 otherwise.
  - On the KOSPI index, the day after a −5% day averaged +1.71%, and the next 5 days +4.25% (n = 23).

**Mixed evidence.** By KOSPI volatility tercile, the high-vol tercile reversal Sharpe is 0.44 (t 1.05), while the mid-vol tercile shows continuation (t −2.74).

**Settling test:**
- Run reversal at 1.0× through stress in the forward-simulated book, costing every simulated entry at QUANTGEN's KRX stock rate (35 bp per side; 70 bp stress). Measure stress-day spreads from KIS quote snapshots. **Fill logs do not exist in a read-only app (§5c).**
- **Decision rule:** block reversal in fast stress if the median stress-day quoted half-spread plus the pre-registered 35 bp per side exceeds the gross stress-day edge. That would be a REVISE of the reversal card's stress subsample.
- Also run a stock-level test by VKOSPI tercile, 2015–26.

**Data needed.** KIS stock-level OHLCV, minute bars and quote snapshots (BL-D03).

**Priority: P1.** It decides whether R-05 needs a Korea exception.

### BL-C03 — The role of credit spreads (N-13; PC-P-08, EX-E-06; executive K3)

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

**Positions:**
- **E5: slow.** Blend 10- and 60-day half-lives, floor at 60-day realised vol, and cap the daily weight change at 20%.
- **E1: fast to restore.** E5's estimator took 214, 121, 68 and 62 sessions to re-enter, vs 88, 40, 29 and 27 for a 20-day target. US 2020–26 Sharpe was 0.61 for E5's estimator vs 0.73 for VT20 (buy-and-hold 0.65).

**Other evidence:**
- KOSPI: SMA60 0.550 vs SMA20 0.638; EWMA (half-life 10) 0.607.
- Harvey et al. (2018) found that all half-lives "work".
- **R4b (v1.1).** Both SMA20 and EWMA(0.94) pass a B5-style check (FHS form) on KOSPI, SPY and the US market (BL-G01).
  - Net of costs, EWMA has lower turnover. US: 2.23 vs 2.52 a year; SR 0.520 vs 0.505 at 50 bp. KOSPI: 1.37 vs 1.50; SR 0.573 vs 0.605 at 35 bp (SMA20 better).
  - This is one trial each, not significant.
  - Under the declared rule SMA20 stays the default and EWMA(0.94) is the registered challenger.
- GARCH-t or GJR may enter this race only after passing B5.

**Settling test:**
- One pre-registered asymmetric estimator, compared with VT20 and E5's estimator, on US 1990–2026 and KOSPI 2015–26. The estimator:
  - cuts with `σ̂ = max(0.5·EWMA10 + 0.5·EWMA60, rv60)` and |Δw| ≤ 0.20 a day;
  - restores with the 20-day estimator once flags clear.
- **Decide on max drawdown and re-entry lag together**: the challenger must beat SMA20 on both, net of QUANTGEN's costs and at 2×, while passing B5. Otherwise SMA20 stays.
- The same harness tests the implied-vol input `σ̂_alt = max(σ̂_SMA20, VIX/100)` (US) and VKOSPI/100 (Korea).

**Data needed.** VKOSPI history.

**Priority: P2.**

### BL-C05 — Korea discrete local flags and time-stops (N-20; EX-E-03, EX-E-07; executive SHADOW S6, K4)

**Positions:**
- **E2:** local time-stops. A −5% KOSPI day → 0.5× for 3 sessions; a sidecar → 0.5×; a circuit breaker → 0.25×.
- **E3 and R2-E3:** continuous control only.
- **On levels vs percentiles:** E5 wants absolute levels; E1 wants scale-free percentiles plus re-anchoring.

**Evidence:**
- The time-stop gave **+0.55 in 2026** (share 0.99) but **−0.06 in 2016–25** (share 0.004). The 10-day version gives −0.035.
- An absolute VKOSPI-type flag ≥ 30 was on for 88% of 2026 days (86% of the Jan–May rally), vs 0–20% in 2015–25.
- Even a trailing 3-year 90th percentile of KOSPI rv21 was exceeded on 72% of 2026 days (10% in 2015–25).

**Settling tests:**
- **(a) Conditional time-stop:** active only while 21-day realised vol exceeds its trailing 80th percentile. Test it as a protective card on 2016–25 and in the forward record, with leave-one-crisis-out. 2026 may supply no more than 50% of the benefit (PC-4).
- **(b) Absolute vs scale-free flags:** compare them, with re-anchoring, on KOSPI, TAIEX and Nikkei over 2015–26, with leave-one-crisis-out. Report the share of rally days flagged, coverage of the 10 worst days, and ΔMDD.

**Data needed.** KIS minute data for the intraday sidecar rows.

**Priority: P2.**

### BL-C06 — Are foreign/institutional flows still informative for KOSPI? (N-21; PX-P-09, EC-E-25)

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

**Proposal.** E5's band (0.98/1.02 × the 200-day average, 3 confirming closes, a 10-day minimum dwell), with the exit keyed to the market's own EWMA-10 vol falling below its 1-year median rather than to the VIX flag. One trial.

**Evidence for:** hysteresis cuts switches per year from 6.0 (plain) to 3.4, 2.45 and 0.89.

**Evidence against:**
- the axis was silent in Mar-2026 (US) and Jul-2026 (KOSPI, minimum 0.978 × its 200-day average);
- with a VIX-conditioned exit, risk-on returned only on 30 Apr 2020 (+30% off the low) and 1 May 2025 (+12.5%);
- the professors call 200-day rules data-mined (Zakamulin), and P6's 200-day conjunction removed all Q3-2026 protection (−38.1% vs −9.6%).

**Re-gate (v1.1):**
- Tier A count: 88 US switches (KOSPI borderline at 52).
- 12 months of forward record.
- **Demote** if switches exceed 2× the budget, or if protective checks fail in the forward record (spec §8.8).
- Card E1, QUANTGEN's trend switch, was REJECTED for outperformance while protecting. A trend axis should be registered as a protective card from the start.

**Priority: P3.**

### BL-C11 — An oil-shock event rule scaling KOSPI gross (N-45; PX-P-05)

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

**Positions:**
- **P2:** one multiplicity hurdle for every cell.
- **P3:** a non-inferiority tier for published, replicated effects.
- **Executives:** tiers defined by event count (Tier A needs ≥ 30 onsets). By that rule the D&M gate, with 7 spells since 1990 (R4), would not qualify.

**Evidence:**
- Barroso–Santa-Clara vol scaling passes either way (z 3.9–4.35).
- The D&M gate has z 1.8–2.0 on daily data and 2.82 on 1929–2026 monthly data, but exceeds 1.96 in **0 of 18** ten-year windows.

**Settling test:**
- pre-registered 2016–2026 holdouts on daily WML for Japan, Europe and Asia-Pacific ex-Japan, never used in design;
- paired stationary bootstrap with Politis–White blocks;
- **Decision:** adopt the separate tier if the D&M gate is non-inferior (ΔSR ≥ 0, one-sided 90%) in ≥ 2 of 3 regions with no episode above 50%. Otherwise the uniform hurdle applies.

**Interim.** Report both statistics on the R-04 card (spec §8.3). In gate terms, this item decides whether R-04's INSUFFICIENT DATA can be resolved by the A-provisional holdout route.

**Priority: P2.** Run it together with BL-C01.

### BL-C13 — Yen shock → block new Japanese exporter longs (N-53; EX-E-09; executive K11)

**Evidence:**
- after 18 yen-shock episodes, the next 10 days averaged −0.23% vs +0.55% unconditional; the rule fired on 17 Jul 2024;
- but ΔSR was −0.05 (share 0.17), and −0.13 in 2024–26;
- its hold period lapsed the day before the Nikkei's −12.4% day (5 Aug 2024) and re-engaged for the +10.2% rebound.

**Test:** re-specify it to block new Japanese exporter longs, with the hold timed from the last extreme-vol day (3–5 sessions). Run it forward once a Japan sleeve exists.

**Priority: P3** (no Japan sleeve yet).

### BL-C14 — A pre-emptive, positioning-based crowding cut (N-57; PX-P-10)

**Positions:**
- **For** (P4): unwinds have strategic complementarity (Stein 2009; Morris–Shin). Speculative yen shorts were near a record ≈ ¥2tn before Aug-2024 (BIS Bulletin 90).
- **Against** (P3):
  - public triggers come late: US momentum lost 5.9% between 11 Jul and 2 Aug 2024, *before* the trigger, and gained 6.5% between 6 and 30 Aug, the window a cut would have removed;
  - own-factor vol already tracks crowding: the momentum vol-scaling weight was 0.53 in Jul-2026 and 0.31 in Nov-2020.

**Settling test:**
- **Data:** CFTC positioning, KRX margin and leveraged-ETF data.
- **Episodes:** Feb-2018, Mar-2020, Aug-2024, Apr-2025 and Jul-2026.
- **Question:** does the crowding score lead own-factor vol by ≥ 5 days in ≥ 3 of 5 episodes, **and** add to vol-scaled sizing?

**Priority: P3.**

---

## 3. ONE-SIDED items

### BL-O01 — Verify the regional cross-sectional momentum priors (N-35; professors only)

**Evidence:**
- **French WML Sharpe, 1990–2026:** US 0.33 (t 2.0), Japan 0.07 (t 0.4), Asia-Pacific ex-Japan 0.71, Europe 0.78, Developed ex-US 0.67, Emerging 0.93. After 2008: US 0.02, Japan −0.02.
- **AMP Table I:** Japan momentum 0.13, value 0.77, combination 0.88.
- **US mean break** in Oct-2002 (QLR p 0.041).
- **R4, vol scaling with cap 1:** Japan 0.196; Europe 1.143; APxJ 1.125, but in 2016–26 0.897 vs 0.921 static; Developed ex-US 0.996.

**Test:**
- Build QUANTGEN's own vol-scaled cross-sectional momentum on each universe it reads, as a CARD-O per market.
- Report full-sample, rolling 10-year, post-2008 and post-2016 Sharpe.
- Convert to weights with the prior design's rule (weight = max(0, rolling-10y Sharpe), normalised per market), after the factor-specific haircuts (momentum −23%).
- **Decision:** the Japan prior moves from 0 to 1 only if the own-data post-2016 vol-scaled Sharpe confidence interval excludes 0.

**Priority: P2.**

### BL-O02 — Momentum new-entry size-down on scheduled decision days (N-39; professors only, PC-P-22)

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

- **Evidence:** n = 1 locally. The day after its announcement, SK hynix rose 12.7% vs KOSPI +5.9%.
- **Test:** ≥ 30 events with DART timestamps.
- **Priority: P3.**

### BL-O05 — Political/geopolitical shock flag, exposure cut only (executive K12; E4-R6, with the × 1.5 leg deleted)

- **Evidence:** in the Dec-2024 martial-law episode no day moved more than ±3%, and the peak-to-trough was −5.6%.
- **Test episodes:** THAAD 2017, North Korea 2017, Dec-2024, Apr-2025.
- **Priority: P3.**

### BL-O06 — Stock-level microstructure (executive K13)

**Candidates:**
- last-10-minute reversal on expiry days (KDI found last-10-minute variance ≈ 7× normal on option expiries);
- Korea's overnight vs intraday split;
- reversal after volatility interruptions.

**Note:** the index-level expiry fade is refuted (§6).

**Data needed.** KIS minute data.

**Priority: P3.**

### BL-O07 — Factor momentum: each family's own trailing 12-month sign as a gate (executive K15; E5-C7)

- **Source:** Ehsani & Linnainmaa (NBER w25551).
- **Test:** on QUANTGEN's five families, with the result de-risk only (≥ 0.5).
- **Priority: P3.**

### BL-O08 — Calm-state reversal down-weight (the dissent recorded in PC-P-06)

- **Evidence:** ST_Rev returned −1.2%/yr when VIX ≤ 20, vs 23.2%/yr otherwise (2008–26).
- **Test:** one pre-registered cell (0.5–1.0 multiplier when VIX ≤ 20).
- **Priority: P3.**

### BL-O09 — Re-run macro priors on real-time vintages (executive K17; T1-C2)

**Scope:**
- ALFRED re-runs of Sahm, the curve probit and Taylor rules;
- SPF dispersion vs volatility;
- the macro-nowcast EPS gap;
- an FOMC dissent count.

**Priority: P3.**

### BL-O10 — KOSPI–China partial correlation (executive K18)

- **Question:** what is the KOSPI–China correlation once the overnight SOX and Nikkei moves are controlled for? This is risk-model research.
- **Evidence:** the daily KOSPI–Shanghai correlation reached 0.56 in 2026, the sample high.
- **Priority: P3.**

### BL-O11 — Dollar gate for EM/Asia momentum (executive K19; Q1b-C12)

**Evidence:**
- With the USD trend defined as the monthly-average 3-month change, EM WML earned 3.3% in USD-up months vs 16.6% in USD-down months (t −2.76). A 0.5× gate gives EM +0.24 (share 0.96) and APxJ +0.18 (0.95).
- With the month-end DTWEXBGS 60-day change instead, the effect **vanishes** (EM +0.03).

**Test:** pre-register one definition and test it out of sample.

**Priority: P3.**

### BL-O12 — E5's system-level limits (E5 round 1; only the single-name cap and the drawdown ladder were ratified)

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

- **Questions:** is inflation *volatility* (rolling std of monthly core PCE) a better stock–bond regime variable than inflation *level*? Should the JPY hedge be conditioned on the direction of real yields?
- **Evidence:** the stock–bond correlation was positive in 1990–99 even with core PCE below 2%. USD/JPY rose 27.4% in 2022.
- **Priority: P3.**

### BL-O14 — Other professor items

- **P1's near-term forward spread (NTFS) ±10% tilt** (dissent recorded in PC-P-15): untested.
- **Change-point detection as an exit feature** (P6-C4).
- **ACM vs Kim–Wright term premium cross-check** (Q1a backlog item 4).

**Priority: P3.**

---

## 4. UNTESTED items

### BL-U01 — Korea leverage / flow / semis-cycle state (N-19) — the most important open item

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

**Evidence so far (all n = 1):**
- DRAM contract guides slowed from +93–98% to +58–63% to +13–18% while the index topped in June.
- AI debt rose from ≈ 7% to ≈ 18% of US investment-grade issuance, with new-issue concessions up to 20 bp (published bank research dated 3 Aug 2026: https://www.goldmansachs.com/insights/goldman-sachs-exchanges/how-ai-debt-is-reshaping-the-credit-market).
- The mega-supply flag (SpaceX IPO 11 Jun, KOSPI peak 22 Jun, SK hynix ADR 9 Jul) fired on 10 Jul, after −20%, and saved 3.2 pp.
- The *level* version of the semis gate (E4's AI-hardware gate) is refuted: it stayed on through the crash and turned off at the trough.

**Settling test:**
1. Build daily series for 2015–2026, or from the earliest available date.
2. Test whether the state leads KOSPI rv21 by ≥ 5 days.
3. Test whether it improves the ΔMDD of the Korea vol target (VT20) in ≥ 3 Korean episodes (2018Q4, 2020, 2022, Aug-2024, Jul-2026), with no episode above 50%.
4. Any multiplier needs ≥ 30 events and Tier B bounds ([0.5, 1.0]). It is registered as a protective card (spec §8.7); its forward record starts from the header commit.

For DRAM guides: use the TrendForce guide history for 2015–26 (≈ 45 quarterly observations), lagged to publication, against KOSPI's forward 20–60-day returns.

**Data needed.** BL-D01, BL-D02, BL-D10.

**Priority: P1.**

### BL-U02 — Korea factor priors (N-36)

**Evidence (literature only, P3-C22):**
- Korean 12-1 momentum was significantly negative in high-turnover stocks (Jul-2000 to Jun-2019).
- Over 1999–2021, 1-month reversal earned −2.950% a month (t −3.77) and pret(12,7) 0.531% a month: Korean momentum profit is reversal carry-over.
- Locally, KOSPI index trend is weak: long/flat 0.47 vs buy-and-hold 0.52.

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

- **Test:** with KIS OHLC data, test SOX(t−1), S&P(t−1) and the overnight KRW move on **open-to-close** KOSPI returns. That use is legitimate, because the information is published before the KRX open.
- **Priority: P2.**

### BL-U05 — Drivers for markets QUANTGEN has no sleeve for (prior design, Part 2)

- **Candidates:** Europe BTP–Bund spread and TTF gas; China credit impulse, policy calendar and northbound flows; India FII flows and RBI; PMI-based tilts.
- **Status:** untested; needs data (PMI licensing).
- **Priority: P3.**

### BL-U06 — Crypto microstructure (prior design)

- **Candidates:** funding-rate extremes as a reversal trigger; exchange flows; stablecoin supply.
- **Status:** untested.
- **Priority: P3** (sleeve not built).

### BL-U07 — Why the gold level broke (Q1a)

- **Evidence:** the 2006–21 level fit implies $626 vs $4,187 actual. Official-sector buying is unverified as the cause.
- **Data needed.** WGC/IMF central-bank purchase data.
- **Priority: P3** (context only).

---

## 5. Data acquisitions needed

| ID | Data | Needed for | Source (to verify) | Priority |
|---|---|---|---|---|
| BL-D01 | KRX investor-type daily net buys (foreign / institution / individual); intraday preliminary figures | BL-C06, BL-U01, BL-S01 regime split | KIS Developers / KRX data portal | **P1** — log from day one |
| BL-D02 | KRX margin debt; leveraged single-stock ETF AUM and flows | BL-U01, BL-C14 | KRX / KOFIA | **P1** |
| BL-D03 | KIS stock-level OHLCV (KOSPI/KOSDAQ universes, survivorship-free), minute bars, quote snapshots (bid/ask if available). No fill logs exist (§5c). | BL-C02, BL-U02, BL-O06, spec R-10 measurement | KIS Open API | **P1** |
| BL-D04 | ALFRED vintages for UNRATE, PAYEMS, GDPC1, GDPPOT, NROU, PCEPILFE, CPIAUCSL | BL-O09, context-log correctness | St. Louis Fed ALFRED | P2 |
| BL-D05 | Consensus forecasts with survey-close timestamps (CPI, NFP, ISM) | BL-U03, BL-C09(c) | A licensed consensus feed | P2 |
| BL-D06 | 30-minute TIPS and nominal futures around CPI/FOMC, 2004–2026 | BL-C09(a)(b) | Intraday futures vendor | P3 |
| BL-D07 | ICE BofA HY OAS from 1997 | BL-C03 | ICE licence | P3 |
| BL-D08 | CFTC Commitments of Traders | BL-C14, the FX sleeve's positioning leg | CFTC | P3 |
| BL-D09 | PMI (ISM / S&P Global) | BL-U05 | Licensed | P3 |
| BL-D10 | TrendForce DRAM contract-price guide history; an AI-debt / new-issue-concession tracker | BL-U01 | TrendForce; build or scrape | P2 |
| BL-D11 | Long front-month Brent futures history (not continuous-adjusted) | BL-C11 | Exchange / vendor | P3 |
| BL-D12 | VKOSPI history | BL-C04, BL-C05 | KRX | P2 |
| BL-D13 | BoK ECOS 15:30 USD/KRW history (= BL-G04; a new ECOS provider in `core/ficc/data`, proposed); live TWD and JPY closes | BL-S01 | BoK ECOS; KIS | **P1** |
| BL-D14 | KIS US 10y yield quote with timestamps (KIS already quotes US yields); ^TNX history as the live-feed proxy | BL-S02, spec R-12 | KIS Open API; Yahoo | **P1** |
| BL-D15 | KOSPI200 constituent history 2010–26; MSCI Korea change history | BL-O03 | KRX / MSCI | P2 |
| BL-D16 | DART / KIND filings: rights offerings, listings, lock-ups, buybacks | BL-O03, BL-O04 | DART OpenAPI, KIND | P2 |
| BL-D17 | Korea CPI after 2023-11 (the local copy ends there); BoK base-rate series | Context log | ECOS / KOSIS | P2 |
| BL-D18 | ACM term premium | BL-O14 | NY Fed | P3 |
| BL-D19 | SPF dispersion | BL-O09 | Philadelphia Fed | P3 |
| BL-D20 | WGC/IMF official gold purchases | BL-U07 | WGC, IMF | P3 |

---

## 5b. Gate and integration items (new in v1.1)

### BL-G01 — B5 volatility-gate dependency for every vol-target card (P1)

**What.** A vol-target card (spec R-06, the crypto vol cap in R-17, any per-market VT) may reach PASS only while its estimator passes B5. B5 is the architecture review's gate for the Quant Lab. It requires:
- rolling-origin 1-day 5% VaR exceedance within ±2 binomial SE of 5% over ≥ 200 origins;
- PIT uniformity.

GARCH(1,1)-t or GJR may replace SMA20 only after passing B5.

**Evidence so far (R4b, FHS form, daily origins):**
- **SMA20 passes on all three samples:**
  - KOSPI 2016–26: 4.70% exceedance, PIT p 0.12.
  - SPY 2016–26: 4.99%, p 0.57.
  - US 1991–2026: 5.31%, p 0.98.
- **EWMA(0.94) passes too:** 4.90% / 5.22% / 5.31%.
- **Normal form:** every estimator fails PIT (fat tails).
- **GARCH(1,1)-t on SPY** (refit every 7 sessions, 504-session window) breaches on 6.3% of days with PIT p < 0.001. That is consistent with the app's own REJECT (6.6%, PIT p 0.003).
- **Caveat:** KOSPI SMA20 on the every-7th-session subsample breaches 7.55% (371 origins), just outside its band (2.74–7.26%).

**Settling test.** Run `docs/vol_backtest.py` (proposed; the review's name) on QUANTGEN's data, per market, with the Kupiec, Christoffersen, coverage, PIT and Diebold–Mariano lines the app already reports. Write the estimator status into `macro_state.vol.estimator_b5`. Decide by the rule declared in `r4b_golden_net.py`: SMA20 if it passes; else EWMA(0.94); else provisional, with the card verdict capped at REVISE.

**Data needed.** None beyond QUANTGEN's history loader (504 closes are too short for ≥ 200 origins on a long window; use the full available history).

**Priority: P1** (blocks M3 and every vol-target card).

### BL-G02 — Protective-card harness in `core/quant/backtest` (P1)

**What.** The pieces the gate needs for protective cards:
- overlay-on vs overlay-off on the same costed engine;
- the static same-average-exposure comparator S;
- PC-1..PC-7 (spec §8.7);
- the §8.6 episode table;
- Politis–White block lengths on d and d²;
- one card per rule, through `docs/macro_overlay_study.py` (proposed).

**Acceptance.** It reproduces R4b's §8.9 numbers on the frozen fixtures within Level-1 tolerance. Two examples: KOSPI VT20 at 3 bp, ΔMDD vs S +4.4 pp, tail ratio 0.82, p_ni 0.24; US VT15 at 50 bp, ΔMDD +0.2 pp.

**Priority: P1.**

### BL-G03 — A cost-aware vol-target card for the US (and the Korea stock book) (P2)

**Why.**
- **US.** At QUANTGEN's 50 bp per side, the pre-registered US VT15 (SMA20, daily rebalancing) loses its drawdown benefit against a same-exposure static book: ΔMDD +0.2 pp, −3.4 pp at 2×. Its indicative verdict is REJECT.
- **Korea stock book.** The Korea VT20 run as a KRX stock book (35 bp) fails the plateau check (0.375).

**Proposal: one new card per market (not a revision of the rejected one).** It changes only the holding period, which is the gate's permitted fix vocabulary. The candidates:
- a no-trade band (trade only when |Δw| > 0.10); or
- a slower estimator (SMA40 / SMA60).

**Post-hoc warning.** R4b's plateau grid shows slower windows doing better net of 50 bp in the US: window 40, ΔMDD +4.1 pp, ΔSR +0.02. That grid was computed after seeing the result. It is a reason to register the card, not evidence for it. Count all of its cells in N.

**Priority: P2.**

### BL-G04 — Timestamped USD/KRW history for the formal S1 card (P1; = BL-D13)

**Why.** The KRW leg's gross edge depends on timing:
- +0.032 on DEXKOUS by value date;
- +0.016 at +1 session or on Yahoo timing;
- **+0.001 under strict H.10 publication.**

Production will read the KIS fixing. The honest backtest therefore needs the ECOS 15:30 KST close history (a new provider in `core/ficc/data`, proposed), or a KIS fixing history if one exists.

**Until then** S1 is INSUFFICIENT DATA formally. Its indicative protective checks fail regardless of timing (BL-S01).

**Priority: P1.**

### BL-G05 — Frozen fixtures for hermetic golden tests (P1)

**What.** Extract the §9.3 reference series into `tests/fixtures/macro/` with an md5 per file: French daily Mom/ST_Rev/5-factor/regional, the monthly F-F factors, ^KS11, ^GSPC, SPY, KRW=X, ^TNX, ^RUT, DGS10, DEXKOUS, VIXCLS, VXVCLS, PCEPILFE, CPIAUCSL and DTWEXBGS.

`tests/run_all.py` patches the network to raise, so golden tests must run from these files.

**Priority: P1.**

### BL-G06 — Map the existing 18-indicator macro sheet (P1)

**What.** The sources show an 18-indicator sheet with z-scores and a regime read in `core/ficc/macro`, but not the list. Fill spec §3.6's mapping table from the code. Each indicator gets:
- its role: CONTEXT by default, acting only if it is listed in §3.6;
- its timing rule;
- whether its z-score window is causal;
- whether the regime read uses smoothed or filtered probabilities. Smoothed must become filtered, even for display.

**Priority: P1** (blocks M6).

### BL-G07 — Map the 6-component signal composite to families (P2)

**What.** Tag each of `core/quant/signals`' six components with a family (momentum, reversal, flow, quality, ts_trend) or none. Overlays attach only through tags (spec §3.7).

**Priority: P2.**

### BL-G08 — KOSPI200 futures as the Korea market-gross instrument book (P3)

**What.** QUANTGEN reads KOSPI 200 futures quotes and pre-registers futures at 5 bp per side. A Korea vol-target card on a futures line would sit between the ETF book (3 bp) and the stock book (35 bp). Compute its golden values and register it only as a separate card.

**Priority: P3.**

### BL-G09 — Broker path: out of scope (record only)

**Status.** QUANTGEN is read-only by construction, and this programme designs no order path. Spec §3.10 records what would have to remain true if the owner ever decided otherwise: PASS cards only, fail-closed, its own forward record through the gate, and the same costs. Nothing in this backlog may be built on the assumption that a broker path exists.

**Priority:** none.

## 5c. Blocked by read-only design (moved here in v1.1)

These items or item-parts need real orders, real fills or real positions. They cannot be built in QUANTGEN as it is. They are kept for the record only; spec §3.10 applies if that ever changes.

| Origin | What is blocked | What replaces it now |
|---|---|---|
| Spec v1.0 R-05, R-10 | Limit orders into the KRX 15:20–15:30 closing auction; opening-auction limit orders | Daily simulated entries priced at the official close of t, earning from t+1 |
| Spec v1.0 R-10 | Sidecar / circuit-breaker order handling: queue orders, no market orders, cancel resting orders at a halt | Evaluator blocks new simulated entries for 30 minutes after a reopening; quotes during halts are marked indicative |
| Spec v1.0 §4.1 | Tuning the decision time "by comparing slippage in fill logs" | Decision at the official close (spec §4.1); no tuning |
| Spec v1.0 R-10 measurement; BL-C02; BL-D03 (part) | KIS fill logs and realised slippage | KIS quote snapshots (spread, 1-minute range) around windows and on stress days, if KIS quotes carry bid/ask (to be confirmed in `kis_client.py`) |
| BL-O12 (parts) | "API heartbeat lost > 60 s → cancel orders"; "position-reconciliation failure at 15:45 KST → flatten intraday sleeves" | Feed heartbeat loss → engine HALTED for the simulated book (spec §3.8); there are no real positions to reconcile |
| Spec v1.0 §8.6 | "Shadow book beats live by > 2% of NAV" against a live capital book | Forward-simulated overlay-off vs overlay-on books (spec §8.8) |

---

## 6. Failure archive — refuted ideas (do not re-propose without new evidence)

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
    - **Against:** Sahm fires a median +2 months late; Jul-2024 was followed by 26 months without recession. A 534-day inversion; probit 0.744 with no recession. 10y–2y false in 1982, 1998 and 2022–24; missed 2020.
    - **Reopen only if:** never as gates.
19. **Smoothed regime probabilities; unpenalised daily HMM / Markov-switching gates; "complexity" macro ML timing; pre-cutoff LLM backtests** (N-49).
    - **Against:** real-time switching 16.9 a year with 49% false episodes (US); 30.8 a year with 77% false (KOSPI); SR 0.390 vs buy-and-hold 0.539. Complexity timing has ρ 0.93 with vol-timed momentum (IR 0.388 vs RFF 0.255; RFF alpha t −0.12).
    - **Reopen only if:** filtered states with a pre-declared jump penalty, ≥ 10 years of training, a leave-one-crisis-out pass; LLM signals only after ≥ 12 months of forward-simulated record.

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
    - **Correct values:** post-float β −1.63; skew −2.38; worst quarter −36.9%; the rate differential is −0.75 pp.
29. **China PMI/CNY as a Korea signal; CESI as an equity feature** (executive DROP list).
    - **Instead:** keep China in the covariance only.

### 6.6 Numbers that must not propagate

| Item | Wrong | Correct |
|---|---|---|
| D&M momentum Sharpe | "1.43 vs 0.71" | 0.682 → 1.041 → 1.194 (*JFE* 2016, Table 7, 1934–2013) |
| Ilmanen OOS decline | "30%" | Value −49%, momentum −23% (n.s.) |
| KOSPI Q3-2026 / peak | −18.8% / ~9,386 | −19.33% / 9,114.55 (closing, 22 Jun) |
| Brent | $127 / $114 read as futures | Those are Dated spot; futures were $118.35 / $102.59 |
| BoK 27 Aug 2026 vote | "unanimous" | 6–1; base rate 3.00% |
| US 10y 5.29% | "19-year high" | Highest close since 14 May 2002 |
| Taylor gap | −1.4 pp | −0.89 pp central (range 0.4–2.3) |
| H.10 FX | daily, T+1 | Weekly, Mondays 16:15 ET |
| AMP Japan | 0.09 / 0.79 | 0.13 / 0.77 / 0.88 (momentum / value / combo) |
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
| Real-time Markov 0.5/1 vs 0/1 Sharpe | unlabelled | 0.554 vs 0.390 (US) and 0.442 vs 0.137 (KOSPI) are net of 10 bp |

---

## 7. Open research questions

1. **Korea concentration and leverage state** (BL-U01).
   - Which observable leads Korean deleveraging: margin debt, leveraged-ETF AUM, retail flows, or the pair's share of KOSPI?
   - Can such a state remove the Korea vol target's 2016–25 Sharpe cost (ΔSR −0.077 gross, share 0.06; −0.106 net of 35 bp) while keeping its crash protection (−12.2% vs −38.6%)?
2. **Leading indicators for the semiconductor cycle.**
   - Do changes in DRAM contract guidance, hyperscaler capex revisions or AI-credit concessions lead KOSPI volatility or drawdowns once lagged to publication?
   - So far n = 1, and every *level* version failed.
3. **An inflation-conditional overlay floor** (BL-C07(b)).
   - Is the higher de-risk value in high-inflation regimes real (+0.14 vs +0.05), or a two-episode artefact (1990–91 and 2021–23)? It needs the 2027+ holdout.
4. **The Korean foreign-flow regime under 2026 market structure** (BL-C06).
   - Since single-stock leveraged ETFs listed in May-2026, have foreign flows become uninformative, or simply a different regime?
   - What drove the Q3-2026 won (+12.4%): exporter conversions, BoK hikes, or the NPS swap line?
5. **Post-publication decay of vol-scaled momentum.** Under the spec's cap, the gain is +0.31 over 1990–2026 but +0.20 in 2012–26. 1990–2007 was also +0.20 under cap 1, so the visible decay (+0.66 in 1990–2011 → +0.26 in 2012–26) is a cap-2 result, and the cap-1 full-sample gain leans on 2008–09 (R4). Is APxJ's negative 2016–26 result (−0.023) noise or the start of decay elsewhere?
6. **Does the D&M gate work on Korean stock momentum?** It is untested on KRX data, and Korean 12-1 momentum may be negative to begin with.
7. **Scale-break re-anchoring.** Can a pre-declared re-anchoring rule fix discrete Korea flags, when even trailing percentiles flagged 72% of 2026?
8. **A live-feed rates leg.** With strict H.15 timing for a close decision (+2 business days), the long-sample edge vanishes (−0.000, R4b). 2015–26 keeps +0.053 strict and +0.071 on the ^TNX live proxy (gross). Is the 1990–2007 sensitivity a feature of slower markets, or noise? At 50 bp per side every timing is negative, so the question is moot for QUANTGEN unless turnover falls sharply (BL-G03).
9. **The stock–bond regime variable.** Inflation level, inflation volatility, or the real-rate share of yield moves?
10. **The cost of Korean reversal under the 0.20% sell tax.** What is its capacity and net Sharpe, and does it survive stress-day spreads (BL-C02)?
11. **Quant Lab tail model for the 2026 regime.** GARCH-t, jump-diffusion, or a regime-mixture? Seeded and validated against 2026, with 2015–24 out of sample.
12. **Statistical-power policy.** Should QUANTGEN formally adopt the non-inferiority tier for replicated effects (BL-C12), given that a +0.05 Sharpe effect needs 33–44 years to detect? v1.1 already adopts a protective card class (spec §8.7) with a 0.10 Sharpe non-inferiority margin. Is 0.10 the right margin, and is 3 pp the right drawdown threshold? They were fixed before any macro card ran and may change only through a spec revision, never per card.
13. **Can a Korea protective card ever reach PASS on history alone?** R4b: the KOSPI vol target protects (ΔMDD +4.4 pp vs a same-exposure static book; tail ratio 0.82). But eleven years of KOSPI cannot confirm Sharpe non-inferiority (p 0.24), and one episode (Jul-2026) carries 59% of the benefit. How many forward months, or pooled Asian markets under a declared rule, would it take?
14. **Cost-aware sizing.** How much protection survives when the rebalancing rule is designed for the cost? Candidates: a no-trade band, a slower estimator, or an ETF or futures line instead of a stock book (BL-G03, BL-G08).

---

## 8. Priority summary

| Priority | Items |
|---|---|
| **P1 (start now)** | BL-G01 (B5 vol gate), BL-G02 (protective-card harness), BL-G04 (= BL-D13, timestamped KRW history), BL-G05 (frozen fixtures), BL-G06 (18-indicator sheet mapping) · BL-S01, BL-S02 (FORWARD-SIM legs; S2's flag is on now; both indicative REJECT, still running labelled) · BL-C02 (reversal in fast stress, quote snapshots) · BL-C06 (flows) · BL-U01 (Korea leverage state) · BL-U02 (Korea factor priors) · data BL-D01, D02, D03, D13, D14 |
| **P2 (next quarter)** | BL-G03 (cost-aware vol-target card), BL-G07 (composite mapping) · BL-C01 + BL-C12 (D&M floor and the A-provisional route for R-04) · BL-C04 (vol estimator challenger) · BL-C05 (Korea flags) · BL-C07(a)(b) · BL-O01 (regional priors) · BL-O03 (supply screens) · BL-O12 (simulated-book limits) · BL-U03, BL-U04 · data BL-D04, D05, D10, D12, D15, D16, D17 |
| **P3 (opportunistic)** | BL-G08 (futures instrument book) · BL-C03, C07(c), C08, C09, C10, C11, C13, C14 · BL-O02, O04–O11, O13, O14 · BL-U05–U07 · remaining data |
| **Blocked by read-only design** | §5c (closing-auction routing, order handling at halts, fill-log slippage, order cancellation and reconciliation). BL-G09 records that a broker path is out of scope. |

---

## Appendix V — v1.1 verification log

**What was checked.** Every golden value in spec §9.3 (R4, gross), every headline evidence number in spec §0.4, §2 and §5, and the whole current-state snapshot (spec §11) were traced to their source.

**How.** `scripts/r4b_verify_spec.py` reads each number as printed in the v1.0 text and looks up the source row in `results/*.csv`. If the number exists only in a note, it records the note file and line. A value is a MATCH when it equals the source at the printed rounding. Output: `results/R4b_verification_log.csv`.

**Result:** 266 checks. **v1.0 numbers (V, S and N rows):** 214 checks: 201 MATCH, 11 TRACED-NOTE, 2 MISMATCH, 0 NOT-FOUND. **New v1.1 numbers (W rows; self-check of R4b values typed into the v1.1 spec):** 52 checks: 52 MATCH, 0 MISMATCH.

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

These are judgment calls. The spec's quick start tells Claude Code not to guess them.

1. **Drawdown-ladder composition (R-07).** Are the steps cumulative? At −12%, does the −8% "gross × 0.5" remain in force while the overlay is forced to 0.5 (net 0.25), or does the −12% step replace it? The bound P2 allows both.
2. **Staleness of slow, risk-model-only inputs (§4.1, §3.8, R-09).** The default maximum staleness for weekly series is 3 days, but H.10 publishes weekly; read literally, a weekly `hedge_state` input would be stale from Thursday to Monday every week, and "stale for more than one decision" moves the engine to HALTED (0×). R-09 says `hedge_state` has no exposure effect. A conservative alternative: a stale `hedge_state` input sets `hedge_credit_off = TRUE` and raises an alert without halting.
3. **Korea concentration caps on an ETF instrument book (R-07, R-06).** §8.9 prefers the KRX ETF line, but a KOSPI ETF carries the index's ≈ 54% Samsung + SK hynix weight on look-through, above the 0.35 pair cap. Decide whether caps apply on look-through and, if so, how an ETF-line vol target satisfies them. Also state the scope of the 0.05-of-NAV single-name cap, which would make the 0.35 pair cap redundant in a stock book.
4. **Normalising the 0–3 priors (R-15, §3.3).** `active_budget = base_weight(m,f) × …` uses priors on a 0–3 scale. State the conversion (for example, per-market normalisation to sum 1, as BL-O01's weight rule implies) so that no weight exceeds 1.0.
5. **Sep-2026 as a Korea drawdown episode (§8.6).** R4b omitted it for Korea; the card header should declare it either way.

*End of backlog.*
