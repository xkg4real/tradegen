# QUANTGEN — Macro Integration Specification (v1.2)

| Field | Value |
|---|---|
| **As of** | 2026-10-02 (Asia/Seoul) |
| **Status** | Implementation-ready for QUANTGEN as it is actually built. It supersedes v1.1 (v1.2 is an independent-QA correction pass; see the changelog below), v1.0 (kept unchanged as `.v1.0_INTEGRATION_backup.md`) and the macro sections of the prior design, "QUANTGEN Signal & Macro Map". |
| **Audience** | Claude Code, building inside the QUANTGEN repository: the Flet desktop app whose entry point is `main.py`. |
| **Companion file** | `QUANTGEN_MACRO_BACKLOG.md` (v1.2): everything not built here, with its settling test, plus Appendix V (the v1.1 verification log) and Appendix Q (the v1.2 independent QA log, including the open questions to settle with the owner). |
| **Codebase sources** | (1) the owner's *QUANTGEN Architecture Review* (written 2026-09-14, fetched 2026-09-20), including its ASCII map of the whole application; (2) the app's public page text (2026-09-29). Where this file names a path or an interface those two sources do not show, it is marked **proposed**. |

---

## Quick start for Claude Code

**Entry point.** Do not read this file front to back before starting. Read in this order, then build one milestone at a time:

1. **§1 (P0–P10) and §10 (DO-NOT-BUILD).** These are the hard constraints. Any code that violates them is wrong even if a test passes.
2. **§12 (build order M0–M10).** Each milestone names its package, its acceptance tests (§9) and its golden values (§9.3). Work milestone by milestone; do not start M(k+1) until M(k)'s tests pass in `tests/run_all.py`.
3. **Per milestone, read only the sections it needs:**

   | Milestone | Read |
   |---|---|
   | M0 scaffolding | §3.1–3.5, §6 (schemas), §7 (rules-store YAML), §9.1 T-RO-01, T-HERM-01, T-SCHEMA-01, T-CAP-01, T-BASIS-01, T-REPRO-01 |
   | M1 data layer | §4.1–4.2, R-01, §9.1 time and data tests |
   | M2 vol and risk | R-06, R-07, R-09, §3.3, §9.3 Korea and US tables |
   | M3 estimator gate | R-06 (estimator row), R-16, §9.3 B5 table, backlog BL-G01 |
   | M4 momentum | R-03, R-04, R-05, §3.7, §9.3 momentum tables |
   | M5 engine and events | §3.8, R-08, R-10, §6.3 |
   | M6 context | §3.6, R-13, §6.4 |
   | M7 cards | §8 (all), §9.2 I-07, backlog BL-G02 |
   | M8 workflow and FORWARD-SIM | §3.9, R-11, R-12, §8.8 |
   | M9 Quant Lab | R-16 |

4. **§2, §5 evidence rows and §13** are background: why each rule exists. Consult them; do not implement from them.

**Invariants to check in every pull request:**
- No order, cancel, withdrawal, deposit-address or transfer path; KIS is read-only (P0, T-RO-01).
- No multiplier or weight above 1.0 anywhere. Overlay multipliers lie in [0.5, 1.0]; vol-target and vol-scale weights lie in [0, 1.0]; 0× only from the risk layer (backtests) or HALTED (simulated book) (P2).
- Every acting input is read through `pit_value` with `available_at_utc ≤ decision_utc`; decide at the close of t, earn from t+1; no synthetic data for acting inputs (P5).
- Only PASS cards feed the recommended (displayed) book. FORWARD-SIM legs (R-11, R-12) never feed it (P7, I-03).
- Costs are read from the gate's pre-registered table and never lowered; every result also runs at 2× (P10).
- Macro tests are hermetic and read frozen fixtures only (T-HERM-01).

**Binding vs informative.** Field names, parameters, bounds, formulas and test thresholds are binding. Paths and function names marked **proposed** may be renamed to fit the codebase. Evidence numbers are informative, except where a §9 test or a §9.3 golden value cites them.

**Open points to confirm with the owner before coding them** (listed in the backlog's Appendix Q; do not guess):
- how the drawdown-ladder steps combine (−8% gross × 0.5, then −12% overlay forced to 0.5: cumulative or not) — R-07;
- the maximum-staleness rule for weekly or slow inputs that feed only the risk model (`hedge_state`), and whether their staleness should trigger HALTED — §4.1, §3.8;
- whether the Korea concentration caps (R-07) apply on look-through when the Korea book is a KRX ETF line, and how the 0.05 single-name cap interacts with the 0.35 pair cap;
- how the 0–3 prior scale (R-15) is normalised into `base_weight(m,f)` in §3.3.

---

## Changelog v1.1 → v1.2 (independent QA)

v1.2 changes no rule, parameter, bound or verdict. It corrects labels and internal contradictions found by an independent QA pass; every edit is logged with its source in the backlog's Appendix Q.

1. Added the **Quick start for Claude Code** above.
2. **R-06 and §8.9:** the Korea non-inferiority p-values 0.24 / 0.32 are the larger of the 10-session and 101-session block results (0.21 / 0.29 with 101-session blocks alone); v1.1 labelled them "101-session".
3. **R-06 and §7:** the B5 PIT threshold is now stated (χ² on 10 bins, p ≥ 0.01, the app's own cut-off and R4b's declared rule). v1.1 left it undefined.
4. **R-03:** the post-publication decay figures (+0.66 → +0.26) are labelled as cap-2 results; under the spec's cap 1 the gain is +0.20 in both 1990–2007 and 2012–26 (R4).
5. **R-11:** the indicative verdict now follows §8.7's verdict order: REJECT under value timing (35 onsets); INSUFFICIENT DATA by tier under strict H.10 (26 onsets), with PC-1 and PC-2 failing in both.
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
   - The class exists because a de-risk overlay is worth 0.00 to +0.10 Sharpe and cannot pass a benchmark-difference test. Detecting +0.05 needs 33–44 years. QUANTGEN's own card E1 shows the problem: it protected (max DD −15% vs −27%) and was still rejected, because its claim was outperformance.
   - Tiers A, B and C are kept and restated in gate terms (§8.3).
   - Indicative verdicts for the current rules, from local reference data, are in §8.9. They are not a run of the app's gate.
4. **QUANTGEN's pre-registered costs apply to every acceptance test (P10, §8.5, §9.3).**
   - The costs are per side, with a 2× stress: KRX ETF 3 bp, KRX stock 35 bp, US shares via KIS 50 bp, crypto 10 bp, futures 5 bp, FX 10 bp.
   - **The R4 golden values were gross.** `r4_golden_values.py` applies no cost term.
   - v1.1 adds net values from `scripts/r4b_golden_net.py` → `results/R4b_golden_values_net.csv`. §9.3 shows gross, net 1× and net 2× side by side.
   - Three conclusions change at these costs. The KRW leg at KRX-stock cost and both US legs at 50 bp lose their gross edge. The Korea vol target keeps its drawdown benefit.
5. **Volatility estimator (R-06, §8.5, BL-G01).**
   - A B5-style check (rolling-origin 5% VaR exceedance within ±2 binomial SE, plus PIT uniformity) was run with filtered historical simulation. SMA20 passes on KOSPI, SPY and the US market. So does EWMA(0.94).
   - Under the rule declared before the run, **SMA20 stays the default in both markets** and EWMA(0.94) is the registered challenger.
   - GARCH-t or GJR may replace SMA20 only after passing B5.
   - The calm / normal / elevated / stressed labels are display-only and computed causally.
6. **Timing convention (§4.1, §9.3).** Every rule now follows "decide at the close of day t, earn from day t+1".
   - `decision_utc` is the official close. The v1.0 15:15 KST close proxy existed only for closing-auction orders, which QUANTGEN does not place, so it is removed.
   - **Strict H.15 timing is +2 business days for a US close decision.** v1.0's "+1 day" was 15 minutes early: DGS10(D) posts at 16:15 ET on D+1, after the 16:00 close. Under strict timing the rates leg's full-sample gross edge is −0.000 (share 0.53).
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

- which inputs to ingest and how to timestamp them;
- which overlay rules to register as model cards, which to run forward in the simulated book, and which never to build;
- exact formulas and parameters, JSON artifacts and rules-store entries;
- how each rule passes through QUANTGEN's nine-step gate;
- tests with numeric acceptance values ("golden values"), gross and net of QUANTGEN's pre-registered costs.

### 0.2 Scope

**What QUANTGEN reads, and therefore what the overlays can act on in its simulated books:**
- Korean equities and ETFs, KOSPI200 futures and options, KTB and USD futures, KRW benchmark yields, the USD/KRW fixing, and investor flows. All of these come as quotes through the KIS Open API. The KRX marketplace (session close) and OpenDART filings are also read.
- US yields, indices and stocks (KIS, FMP, FRED, Yahoo). US exposure and factor sleeves remain the reference market where most of the evidence was measured.
- Crypto, from public exchange data only (Upbit, Binance, CoinGecko).

**What "act" means here.** QUANTGEN has no order path. An overlay changes only these things:
- the weights in the simulated order book of `core/engine`;
- the costed backtests in `core/quant/backtest`;
- the model cards in the Strategy Lab;
- the exposure recommendation shown on screen.

**Planned** (specified, dormant until the sleeve exists): an FX sleeve, a crypto sleeve and further equity markets. The crypto desk already exists, so §5 R-17 reconciles with its crypto trend cards: C3 on KRW-BTC is a PASS.

### 0.3 How to use this file

1. Read §1 (non-negotiables, including P0 read-only) and §10 (DO-NOT-BUILD) before writing any code.
2. Implement in the milestone order of §12. Each milestone has acceptance criteria, which point to the tests in §9 and the golden values in §9.3.
3. **Extend QUANTGEN's existing packages and conventions.** §3 names them. They are:
   - Python with numpy/scipy;
   - decimals inside the core, with % and bp only in the UI;
   - the routing rule that an explicit provider which fails **raises**, and only "auto" degrades to labelled synthetic data;
   - immutable rule models with no financial defaults;
   - seeded, reproducible runs;
   - hermetic tests.

   Paths and interfaces marked **proposed** are this file's inference and may be renamed. Field names, parameters, bounds and tests are binding.
4. Every parameter lives in the rules store (`core/rules`, one JSON file with edit history) or in `config.py`. An acting parameter may change only through a new card revision (§8.4), which counts as a trial. **Lowering a pre-registered cost is never a permitted change.**
5. Nothing in this file needs the research notes. Every number cites its evidence in §13 by node ID (N-xx), source and result. Appendix V of the backlog traces 214 of them, plus 52 new v1.1 numbers, to their source rows; Appendix Q logs the v1.2 independent QA corrections.

### 0.4 What the research concluded

Two independent panels studied the question:
- **professors** in macro, econometrics, asset pricing, game theory, curricula and quant ML;
- **senior practitioners** from IB, NYSE trading, rates/FX, strategy, risk, systematic PM and research.

Their work was checked against local data from 1926–2026 (Ken French, FRED, Yahoo, KOSPI).

The panels agree that **macro cannot be used to forecast direction at QUANTGEN's horizons, but it can be used to size risk**:

- **Lagged macro quantities do not lead returns.** Market-priced stress variables forecast volatility, not mean returns. The VIX/VIX3M slope predicts 21-day realised vol with t = 7.17, but next-21-day returns with t = 0.04.
- **Nearly every macro rule in the prior design failed on honest data.** This includes:
  - the four-state table and all multipliers above 1.0;
  - the VIX-term-structure momentum switch;
  - the SOX×KRW Korea gate, whose +0.31 Sharpe came from look-ahead;
  - the curve, real-rate and credit gates, and the oil gate;
  - the net-liquidity crypto rule and the 24-hour event blackouts.

**What survives:**

1. **Momentum sized by its own risk state.**
   - Own-volatility scaling, plus a floored Daniel–Moskowitz bear-state gate.
   - Under this spec's caps, US momentum Sharpe rises from 0.40 to 0.80 gross and maximum drawdown improves from −63% to −21%.
   - Net of 50 bp per side on the overlay's own turnover (both legs), Sharpe rises to 0.74.
2. **Reversal and quality held at 1.0×.**
3. **A per-market continuous volatility target, capped at 1.0, using Korea-local inputs.**
   - In the 22 Jun–30 Jul 2026 KOSPI crash it cut the loss from −38.6% to −12.2%. No US-sourced indicator saw that crash. Net of 35 bp per side the loss was −12.3%.
   - It is Sharpe-neutral, and it charges a bull-market tax.
4. **Samsung + SK hynix concentration caps.**
5. **Strict point-in-time, cross-time-zone data handling.** Timing errors were the largest source of fake edge in the whole programme. v1.1 tightens two publication rules, H.15 and H.10 (§4.1).
6. **A hedge-validity state.** Do not count bond or dollar hedges when inflation is high or the stock–bond correlation is positive.
7. **Event handling with short intraday windows instead of blackouts.**
8. **Slow macro as logged context only:** Sahm, the yield curve, Taylor residuals, real yields and term premium.

**Two macro legs run only as forward-simulated cards (FORWARD-SIM).** They never change the displayed recommendation:
- USD/KRW 20-day change > +3% → Korea gross × 0.75;
- US 10y yield +40 bp over 20 days → US duration-sensitive gross × 0.5.

**v1.1 finding at QUANTGEN's costs.**
- **Korea vol target.** Its drawdown benefit holds at both KRX ETF and KRX stock cost: max DD −36.8% / −37.2% against −41.3% for a static book with the same 0.925 average exposure.
- **KRW leg at KRX-stock cost.** It turns negative: ΔSR −0.008 at 35 bp. Under strict H.10 timing it is +0.001 even gross.
- **US legs at 50 bp per side.** The US vol target and the rates leg lose their gross edge, because their turnover costs 1.26% and 1.80% a year.

**Expectations.**
- A de-risk overlay is worth 0.00 to +0.10 Sharpe, and a backtest cannot prove it: detecting +0.05 needs 33–44 years.
- So the overlays are judged as **protective** cards (§8.7): on drawdown, against a static book with the same average exposure, with Sharpe non-inferiority.
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
  9. A 60% live haircut, reported but not gated.
- **Model cards.** Each card holds a hypothesis, a rule, a data span, pre-registered costs, a seed, every test line, the decision and an md5 of the results. A REVISE names the first failed check and the only permitted fix: widen the grid, lengthen the holding period, or extend the history. Every revision counts as another trial.
- **Strategy Lab.** The record holds 34 cards: 5 PASS, 11 REVISE, 18 REJECT and 0 INSUFFICIENT DATA (study run 2026-09-27, seed 11). Rejected families still run, labelled. Card E1 (trend switch) is kept on the ETF page as a descriptive sleeve with its verdict.
- **Quant Lab.**
  - Models: GBM, jump diffusion, block bootstrap and GARCH(1,1)-t.
  - Path colours carry the conditional-vol quartile labels calm / normal / elevated / stressed.
  - The lab grades its own VaR. GARCH-t on SPY breached a 5% VaR on 6.6% of days with PIT p 0.003, so it is a REJECT. GJR on SPY also sits at 6.6%, with PIT p 0.014. The skewed-t stays out of the menu.
- **Desk pages.** Each states what it withholds. The ETF page withholds "trend, vol target, risk parity and sector momentum as signals". The Volatility page withholds the VIX roll-down trade (out-of-sample Sharpe −0.14). The Rates page shows the Diebold-Li factors as a description, because the forecast beat the random walk at 0 of 5 maturities.

---

## 1. Design principles (non-negotiable)

These are enforced in code, as assertions, schema bounds and rules-store validation, not by convention.

**P0. Read-only by construction.**
- No module in this spec may contain, import or call an order, cancel, withdrawal, deposit-address or transfer path on any venue. KIS is used for read-only quotations only.
- Every output is one of the following:
  - an artifact (§6);
  - an entry in the **simulated order book** of `core/engine` (orders module: "simulated order book — NO broker order path");
  - a costed backtest or forward-simulated book in `core/quant/backtest`;
  - a **model card**;
  - a **displayed exposure recommendation**.
- A displayed recommendation may come only from cards whose verdict is PASS. Every other card is computed, logged and shown as a descriptive sleeve labelled with its verdict. This is the treatment card E1 gets on the ETF page.
- Evidence: QUANTGEN rule 01 ("There is no code path that sends an order, on any venue, and nothing to switch on").

**P1. Macro scales risk; it never generates direction.**
- No macro or overlay module may create, flip or close a simulated position on its own.
- Overlays output multipliers only. Signals come from the signal families and the existing composite (`core/quant/signals`, §3.7).
- Evidence: N-01, N-04.

**P2. Bounded multipliers.**
- **Overlay multipliers** (family or market-gross) must lie in **[0.5, 1.0]**. The product of all overlay multipliers acting at one level is clipped to [0.5, 1.0].
- **Vol-target and vol-scale weights** must lie in **[0, 1.0]**. They are risk-layer sizing, not overlay multipliers. They have no floor, because a floor would undo the crash protection: the Korea weight was 0.30–0.33 on 22–23 Jun 2026.
- **No multiplier anywhere may exceed 1.0.** The rules store rejects a rule whose output can exceed 1.0; this is Tier C (§8.3).
- **0× comes only from the risk layer.** In backtests that means `core/quant/risk` limits and the drawdown ladder. In the simulated order book it means the `core/engine` runtime entering **HALTED** (§3.8): risk limit, drawdown ladder −15% step, or data or system failure. The overlay can never output a value below 0.5.
- Evidence: N-02, N-03.

**P3. Stress variables feed sizing and entry blocks.**
- VIX term structure, credit, oil, EPU and USD-down-with-equities enter only through these channels:
  - the volatility estimator (as a logged alternative only; §5 R-06);
  - **new-entry blocks**, which are `core/engine` evaluator decisions in the simulated order book and the same rule in backtests;
  - the event calendar;
  - Monte Carlo scenarios.
- They are never mean gates, and never cut-and-re-add triggers on existing exposure.
- Evidence: N-04, N-05.

**P4. Korea's risk inputs are local.**
- Korea gross is driven by KOSPI's own volatility, concentration and (later) leverage state.
- US or global macro states never gate Korea gross.
- US overnight information enters Korea only as an opening-gap and volatility input.
- Evidence: N-16, N-18, N-40.

**P5. Everything is point-in-time. Decide at the close of day t; earn from day t+1.**
- **Timestamps.** Every datum carries a UTC observation timestamp and a UTC `available_at` (publication) timestamp.
- **Decision time.** `decision_utc` is the official close of the market being decided (§4.1).
- **The availability rule.** A datum may enter a decision only if `available_at_utc ≤ decision_utc`. The resulting weight earns from the next session.
- **Lags.** Lags are calendar-based, never positional.
- **Missing or stale inputs fail closed.** The state is left unchanged, an alert is raised, and nothing is ever silently interpolated.
- **No synthetic data for acting inputs.** `core/ficc/data` lets an "auto" provider degrade to labelled synthetic data. For an acting input that degrade is forbidden: a synthetic or degraded value is treated as a missing input.
- **Vintages and names.** Revised series are stored with vintages. Every series is named (no unnamed "Brent").
- Evidence: N-46, N-47; QUANTGEN rule 02.

**P6. Thresholds on changes or percentiles.**
- Thresholds are defined on changes or on expanding/trailing percentiles, never on levels calibrated to today.
- Evidence: N-12.

**P7. The gate decides.**
- Every overlay rule that changes exposure is a model card and passes through the nine-step gate (§8.1). Protective rules use the protective class (§8.7).
- Only PASS cards feed the displayed recommendation. FORWARD-SIM cards run forward in the simulated book and are re-gated with that record (§8.8).
- Nothing becomes a recommendation because a backtest looks good, and a rejected card is not deleted.
- Evidence: N-50; QUANTGEN rule 03.

**P8. Every multiplier declares its exposure basis.**
- `active` means it scales a family's long/short or benchmark-relative risk.
- `total` means it scales the market book's gross long exposure.
- Evidence: N-02. The executives traced a misreading of the 9 Apr 2025 momentum result to exactly this confusion.

**P9. Slow macro is context.**
- Sahm, the yield curve and probit, Taylor residuals, real yields, term premium, breakevens, credit levels, survey data, and the Street's and the Fed's projections are logged daily and never act.
- This includes every indicator of the existing 18-indicator macro sheet that is not an acting input (§3.6).
- Acting on any of them requires a new card.
- Evidence: N-26, N-30, N-56.

**P10. Pre-registered costs, always.**
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
- **Instrument book.** A card declares its instrument book before it is run. Example: Korea market gross via a KRX ETF line, or by scaling every stock position.
- **No lowering.** Lowering a cost is never a permitted fix.
- Evidence: QUANTGEN rule 02; R4b (§9.3).

---

## 2. Changes vs the prior design ("QUANTGEN Signal & Macro Map")

**How to read the table.**
- **Decision codes:**
  - KEEP: unchanged.
  - MODIFY: changed as stated.
  - DROP: never build (see §10).
  - BACKLOG: not built; see the backlog file.
  - FORWARD-SIM (v1.0: SHADOW): runs forward in the simulated book as a card; never a recommendation until re-gated.
- **Notation in the Evidence column:**
  - "R4" marks a golden value recomputed under this spec's parameters (gross, §9.3).
  - "R4b" marks v1.1's net-of-cost or strict-timing recomputation.
  - "SR" is Sharpe ratio.
  - "share" is the fraction of bootstrap resamples in which the rule beats its base.

### 2.1 "Do this first" plumbing

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| Directional signal layer: one module per family, JSON artifact per asset | **KEEP** (mapped onto `core/quant/signals`) | Families are tagged components of the existing composite (§3.7, proposed) | — |
| Two simplest families: XS momentum 12-1 and 5-day reversal, on KR + US | **MODIFY** | US 12-1 runs only with own-vol scaling plus the D&M gate. Korea adds a 12-7 / residual momentum variant (UNVERIFIED prior) and keeps 1–5-day reversal. All tests are net of QUANTGEN's KRX stock cost, 35 bp per side, which covers the 0.20% sell tax. The 2× stress is 70 bp. | N-06; N-36. US 12-1 SR 0.33 since 1990, 0.02 since 2008. Korean 1-month reversal −2.950%/month (t −3.77). |
| Move volatility from signal to sizing: position = target vol / forecast vol | **KEEP, strengthened** | Weight = min(1.0, target/σ̂): a cap of 1.0, no levering up. Estimator SMA20 (passes B5-style check; §5 R-06). | N-02, N-14. KOSPI vol target with cap 1.5: SR 0.534 vs 0.638 at cap 1.0. Aug-2024 −9.7% vs −7.9% (R4). |
| Per-market × per-family weight table as config | **KEEP** | Priors updated (§5 R-15); stored in the rules store | N-35, N-36, N-33 |
| Regime-multiplier hook (default 1.0) read by the risk engine | **MODIFY** | Bounds [0.5, 1.0]; exposure basis declared; clipping logged; read by `core/quant/risk` and the engine evaluator | N-02 |
| Falsification pipeline, net of 0.35% KR round trip | **MODIFY → the nine-step gate** | Every rule is a model card. A protective class is added (§8.7). Tiers are restated in gate terms. Costs are QUANTGEN's pre-registered ones (KRX stock 35 bp per side = 70 bp round trip; 2× stress). | N-50, N-51; QUANTGEN rules 02–03 |

### 2.2 Part 1 — signal families and the starting weight matrix

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| US XS momentum weight 3 | **MODIFY → 2 if vol-scaled with the D&M gate (1 if unscaled)** | Momentum is sized by R-03 and R-04 | N-35. Mean break in Oct-2002 (11.4%/yr before, 0.2% after). R4: SR 0.40 → 0.80 with the spec stack (R4b net of 50 bp on overlay turnover: 0.74). |
| Japan XS momentum 0 | **KEEP 0** | It may rise to 1 if QUANTGEN's own vol-scaled card passes | N-35. Japan WML SR 0.07 (t 0.4). R4 vol-scaled: 0.196. |
| Europe / EM / APxJ XS momentum 3 | **KEEP** (prior only) | — | N-35. SR 0.78 / 0.93 / 0.71. APxJ vol scaling negative in 2016–26 (R4 −0.023). |
| Korea XS momentum 1 ("fragile, crash-prone") | **MODIFY** | 12-1 → 0. 12-7 / residual momentum → 1 (UNVERIFIED). | N-36 |
| Korea reversal 3; Korea flow 3 | **KEEP** | Reversal must clear the net-of-cost test at 35 bp per side and 2×. Flow weight stays, but with no flow-conditioned multiplier. | N-09, N-21 |
| TS momentum, per index | **MODIFY** | KOSPI 2 → 1; KOSDAQ → 0; Europe 3 → 0–1 (STOXX50 0, DAX 1, FTSE 0–1); Japan 2 → 1–2; Taiwan 2 → 1–2; China A 1 → 0; India 2 → 1; US 3 (keep); crypto 3 → 2 with BTC's own vol cap | N-33. Q1b B5 per-index 12-1 Sharpe and bootstrap. |
| "Vol-scaled sizing gives +0.1 to +0.3 Sharpe on nearly every strategy" | **MODIFY** | Robust only for momentum. Index vol targeting is risk control, not alpha. | N-06, N-14. Constant-vol scaling (cap 2) since 2020: ST_Rev −0.31, RMW −0.10, HML −0.08, CMA −0.16. Full sample 1990–2026: ST_Rev +0.13, RMW +0.02, HML −0.03, CMA −0.06 (Q1b B1b). **v1.1 correction:** v1.0 printed the full-sample HML and CMA values under "since 2020". |
| Reversal "strongest after a volume spike" (5-day z with vol/20d avg > 1.5) | **KEEP as signal spec; UNTESTED** | Not evaluated by either panel | — |
| Value–momentum hedge assumed universal | **MODIFY** | Measure it on QUANTGEN's own sleeves | N-35. French ρ −0.17 vs AMP −0.65 over the same window. |
| Published Sharpe ratios as priors | **MODIFY** | Haircut published premia by factor-specific out-of-sample declines: value −49%, momentum −23% (n.s.), carry ≈ −25%, defensive 0, multifactor −18%. One-sided (professors). The gate's own 60% live haircut is reported on every card in addition. | N-60; PR-P-02 |

### 2.3 Part 2 — global macro variables

| Prior element | Decision | New spec | Evidence |
|---|---|---|---|
| Real 10y: momentum weight down when the 3-month change > +50 bp | **DROP** | Real-yield changes go to the context log and risk attribution | N-11. Momentum SR 0.88 when real rates rose > 50 bp vs 0.02 otherwise; gate ΔSR −0.04. |
| Curve: gross cut when it re-steepens from inversion | **DROP** | 10y–3m is logged as a prior | N-11, N-30. Book ΔSR −0.09 (share 0.00). |
| Broad USD: per-market exposure scaled by rolling USD beta | **MODIFY** | Context plus hedge-validity state (R-09). The USD gate for EM momentum goes to backlog. | N-29. USD up in 10 of 11 drawdowns; failed Apr-2025. |
| VIX term structure: momentum off, reversal on when inverted | **DROP as a switch** | Becomes a new-entry block card (R-08, an evaluator decision) and a logged vol-estimator alternative | N-04, N-05. Momentum ΔSR −0.15 (2020–26). |
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
| Korea: gross cut when USD/KRW 20-day change > +3% | **MODIFY → FORWARD-SIM 0.75×, one-sided, honest lag** | R-11 | N-22. R4 (value timing, gross): +0.032 (share 0.965); +0.042 on top of VT20. R4b: strict H.10 +0.001 gross; −0.008 net of KRX stock 35 bp. |
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
| Market gross 0–1 from two local drivers (Korea: SOX × KRW) | **MODIFY** | Market gross = own vol target (cap 1.0) × bounded FORWARD-SIM legs (the legs never touch the recommendation until PASS) | N-14, N-16, N-22 |
| Event blackout: no new positions 24 h before FOMC/BoJ/BoK/PBoC/Korean exports | **DROP** | Short intraday windows (R-10), as evaluator blocks on simulated entries | N-37, N-38. FOMC lands at 03:00/04:00 KST, so a 24 h blackout swallows the preceding KRX session. |
| Falsification: 1,000-path block bootstrap; multiplier → 1× if it fails | **MODIFY** | The nine-step gate (2,000 × 10-session blocks) plus the protective class (§8.7), deciding on the longer of 10 sessions and the Politis–White length | N-50 |
| Data: CBOE via yfinance ^VIX/^VIX3M; FRED DEXKOUS as daily FX | **MODIFY** | CBOE via FRED VIXCLS/VXVCLS. H.10 FX is weekly, so production uses the KIS USD/KRW fixing. H.15 is posted the next business day at 16:15 ET, so production uses a KIS US 10y quote and strict backtests lag DGS10 by two business days. | N-46, N-47; R4 and R4b H.15 findings |
| Next steps: build the four-state classifier and the Korea SOX×KRW scalar | **DROP** | Replaced by milestones M0–M10 (§12) | — |

---

## 3. Architecture (re-mapped to QUANTGEN's packages)

### 3.1 Where the macro work lives in QUANTGEN

The map below is the architecture review's application map (§1.1 of that review). It is reduced to the parts this spec touches.

- `[+]` marks an extension of an existing module.
- `[new, proposed]` marks a file the sources do not show.

```
 QUANTGEN (Flet desktop app; entry point main.py; read-only: no order path)
 ┌──────────────────────────────────────────────────────────────────────────────────────────────┐
 │ UI ui/*.py   Macro · Rates · Bonds · FX · Structuring │ Quant Lab · Portfolio · Signals │       │
 │              Execution · Rules · Workflows · Skills · KRX · Runs · Settings                   │
 │   [+] Macro page: macro_state panel, overlay_decision table, card verdict badges,            │
 │       calm/normal/elevated/stressed display label, event calendar, context log (proposed)     │
 └──────────────┬──────────────────────────────┬───────────────────────────────┬─────────────────┘
 ┌──────────────▼───────────────┐ ┌────────────▼─────────────────┐ ┌───────────▼──────────────────────────┐
 │ core/ficc                    │ │ core/quant                   │ │ core/engine · core/rules · core/skills│
 │  data   FRED|Yahoo|synthetic │ │  history FMP|KIS|synthetic   │ │  runtime DISARMED→ARMED→HALTED        │
 │   [+] PIT layer: obs/avail-  │ │  risk    vol, DD, VaR/CVaR   │ │   [+] HALTED = 0× authority (§3.8)    │
 │       able_at stamps, vint-  │ │   [+] vol_target, drawdown   │ │  feed    QuoteFeed via core/markets   │
 │       ages, publication lags,│ │       ladder, hedge_state,   │ │  evaluator (rule, quote) → decision   │
 │       lag audit, no synthetic│ │       Korea caps             │ │   [+] BLOCKED decisions: R-08, R-10,  │
 │       for acting inputs      │ │  signals 6-component compos. │ │       ladder −12%                     │
 │  macro  18-indicator sheet,  │ │   [+] family tags, bounded   │ │  orders  simulated order book, NO     │
 │         z-scores, regime     │ │       multipliers, exposure  │ │          broker order path            │
 │         read, daily/weekly   │ │       basis                  │ │   [+] overlay-on / overlay-off books  │
 │         brief                │ │  backtest costed, no look-   │ │  state   persisted trigger counts     │
 │   [+] macro_state,           │ │          ahead               │ │   [+] switch counts per card          │
 │       overlay_decision,      │ │   [+] overlay-on vs off on   │ │  rules   model (immutable, no fin.    │
 │       context_log builders;  │ │       the same engine, static│ │          defaults), validation, store │
 │       sheet reconciliation   │ │       same-exposure compara- │ │   [+] overlay rule objects (§7)       │
 │  ratesim Vasicek|CIR|HW      │ │       tor, episode table,    │ │  skills  72-entry manifest, runner,   │
 │   [+] SEP-band rate paths    │ │       protective checks      │ │          runs, workflows (YAML, gates)│
 │       (R-16)                 │ │  garch, montecarlo           │ │   [+] macro skills + macro_daily      │
 │                              │ │   [+] R-16 scenarios         │ │       workflow (proposed)             │
 └──────────────┬───────────────┘ └────────────┬─────────────────┘ └───────────┬──────────────────────────┘
                │      core/markets (venue → provider, session) · core/calendars [+] event calendar,
                │      KRX/NYSE sessions and holidays, cross-time-zone availability (proposed)
 ┌──────────────▼───────────────────────────────▼───────────────────────────────▼─────────────────┐
 │ Providers (read-only): KIS Open API quotes (KRX, KOSPI200 fut/opt, KTB/USD fut, KRW yields,      │
 │ US yields/indices/stocks, USD/KRW fixing, investor flows) · FRED · Yahoo · FMP · KRX marketplace │
 │ · OpenDART · Claude API (narrative only, never decides) · gs_quant · [new, proposed] BoK ECOS    │
 │ config.py: credentials by family, ~/.nextgen/ficc_cache (6 h), trading dir for rules JSON,       │
 │            skill env  [+] macro artifact dir, cost table reference (proposed)                    │
 └──────────────────────────────────────────────────────────────────────────────────────────────────┘
 tests/run_all.py [+] macro tests, hermetic (network touchpoints patched to raise; frozen fixtures)
 docs/ [+] macro_overlay_study.py → one JSON model card per overlay rule; vol_backtest.py (B5) (proposed)
```

### 3.2 Daily data flow (one decision per market per close)

```
 official close of t (KRX 15:30 KST = 06:30Z; NYSE 16:00 ET = 20:00Z EDT / 21:00Z EST)
        │
        ▼
 core/ficc/data  [+] PIT snapshot at decision_utc ── lag audit ── fail closed on missing/stale/synthetic acting input
        │
        ├──► core/ficc/macro [+] context_log (never acts; isolation guard)           ─► Macro page, weekly brief
        │
        ├──► core/quant/risk [+] σ̂ (SMA20), vt(m), vs(m,f), hedge_state, caps, ladder
        │            │
        │            ▼
        │    core/quant/signals [+] family multipliers (D&M gate; rev/qual fixed 1.0), exposure basis, clip [0.5,1]
        │            │
        │            ▼
        │    core/ficc/macro [+] build macro_state, overlay_decision (each multiplier tagged with its card verdict)
        │            │
        ├──► core/calendars [+] event windows, KR opening-gap nights
        │            │
        ▼            ▼
 core/engine: evaluator (BLOCKED decisions) ─► orders: simulated order book, two books per card (overlay on / off)
        │                                        priced at the official close of t, earning from t+1, costed per P10
        ▼
 runtime: ARMED │ HALTED (0×: ladder −15%, risk-limit breach, data/system failure)
        │
        ▼
 docs/macro_overlay_study.py + core/quant/backtest ─► model cards (nine-step gate; protective class §8.7) ─► Strategy Lab
```

The workflow `core/skills/workflows/macro_daily.yaml` (§3.9) runs this pipeline after each close. It is **proposed**: the sources show that YAML workflows with decision gates exist, but not this one.

### 3.3 Exposure composition

The composition rule below is **default, judgment**. The evidence fixes each factor separately. How the factors are combined is a design choice, made conservatively; it can only be changed by a new card revision (§8.4).

For market m, family f and instrument i, decided at the close of t (`decision_utc`), effective from t+1:

```
# family level (exposure_basis = active)            core/quant/signals [+]
active_budget(m,f)  = base_weight(m,f)                         # rules-store prior, §7 / R-15
                    × vs(m,f)                                  # own-vol scale of the sleeve, in [0,1]   (R-03; momentum only)
                    × clip( Π family_overlays(m,f), 0.5, 1.0 ) # e.g. D&M gate          (R-04)

# market level (exposure_basis = total)             core/quant/risk [+]
gross(m)            = vt(m)                                    # market vol target, in [0,1]             (R-06)
                    × clip( Π gross_overlays(m), 0.5, 1.0 )    # v1.1: empty product = 1.0 (S1/S2 are FORWARD-SIM)

target_weights      = composite_weights(i | active_budget, gross)                 # core/quant/signals
final_weights       = risk_layer(target_weights)               # caps, ladder, hedge_state; 0× only here (backtest)
simulated_orders    = engine.orders(final_weights)             # or HALTED → 0× (simulated book)
```

**Two books for every card (P0, P7).**
- **Recommended book.** Applies only the factors whose card verdict is PASS. All other factors are set to 1.0, and the risk-layer invariants still apply. This is the only book whose weights are shown as a recommendation.
- **Specification book.** Applies every BUILD NOW factor, whatever its verdict. It is labelled with the verdict of each factor.

Every FORWARD-SIM leg runs a third book of its own: the specification book × the leg.

**Notes on the formula:**
- **Active budget.** Scaling a long-only sleeve's active budget moves weights toward the benchmark, not toward cash. Scaling a long/short sleeve moves it toward zero.
- **What `vt(m)` covers.** It scales the market's long book. It does **not** scale long/short factor sleeves, which have their own `vs(m,f)`. It does **not** scale the TS-trend sleeve, which is vol-scaled per asset and exempt from overlays (R-14).
- **Instrument book.** In Korea, `vt(m)` may be implemented on the market ETF line (KRX ETF, 3 bp) or by scaling every stock position (KRX stock, 35 bp). The card declares which before it is run (P10). §9.3 gives both sets of golden values.
- **Clipping is logged.** Whenever a clip binds, it is recorded in `overlay_decision.reasons`.

### 3.4 Module map: v1.0 component → QUANTGEN package

| v1.0 component | QUANTGEN package (exists per the sources) | What v1.1 adds | Status |
|---|---|---|---|
| `data_layer/registry.yaml`, `ingest.py` | `core/ficc/data` (FRED, Yahoo, synthetic; explicit provider that fails raises); `core/quant/history` (FMP, KIS, synthetic); provider clients (e.g., `kis_client.py`) | Series registry (§4.2) as a data file next to `core/ficc/data`; new provider BoK ECOS (USD/KRW 15:30 KST history) | registry file **proposed**; ECOS **proposed** |
| `timestamps.py`, `pit.py`, `vintages.py`, `lag_audit.py` | `core/ficc/data` | `PITValue`, `pit_value()`, `available_at` rules per series, publication lags (H.15, H.10, BEA/BLS), vintages (ALFRED), `retrieved_at_utc` on every cached record (`~/.nextgen/ficc_cache`), lag audit, **no synthetic degrade for acting inputs** | functions **proposed** inside the existing package |
| `context/context_log.py` | `core/ficc/macro` (18-indicator sheet, z-scores, regime read, daily/weekly brief) | `context_log` builder; reconciliation of the existing sheet (§3.6); `macro_state` and `overlay_decision` builders | builders **proposed** |
| `vol/estimators.py`, `vol/targets.py` | `core/quant/risk` (vol, drawdown, 1-day VaR/CVaR; `risk.py` is cited in the review) | `sma_vol`, `ewma_vol`, `market_vol_target()`, `sleeve_vol_scale()`, causal display label | **proposed** functions in `risk.py` |
| `overlay/family.py` (D&M), `overlay/bounds.py` | `core/quant/signals` (6-component composite) | Family tags on components, `dm_gate()`, bounds and exposure-basis validation, clipping log | **proposed** |
| `overlay/market_gross.py` (S1, S2) | `core/quant/risk` + `core/engine/orders` | FORWARD-SIM legs as separate simulated books | **proposed** |
| `overlay/hedge_state.py` | `core/quant/risk` (and `core/quant/optimize`, which uses covariances) | `hedge_state()`; `max(corr, 0)` for equity–duration pairs in VaR, stress and optimiser inputs when `hedge_credit_off` | **proposed** |
| Korea caps, drawdown ladder | `core/quant/risk`; `core/engine/runtime`, `core/engine/evaluator` | Caps as portfolio constraints; ladder steps −8% (gross × 0.5), −12% (evaluator blocks new entries, overlay forced to 0.5), −15% (runtime HALTED) | **proposed** |
| `events/calendar.py`, `events/entry_blocks.py` | `core/calendars`; `core/markets` (venue → provider, suffix, currency, session); `core/engine/evaluator` | Event store with status; window generator; KR opening-gap nights; cross-time-zone `usable_at()`; BLOCKED evaluator decisions | **proposed** |
| `falsification/*` (registry, trials, bootstrap, DSR, PBO, episodes, shadow book, report) | The existing gate (nine steps, four verdicts, model cards with md5) and `core/quant/backtest` (costed, no look-ahead) | Overlay-on vs overlay-off paired evaluation on the same costed engine; static same-average-exposure comparator; protective checks (§8.7); episode table (§8.6); forward-simulated record (§8.8) | harness **proposed**; the gate itself **exists** |
| `schemas/*.schema.json` | (none shown) | JSON Schemas of §6 next to the builders | **proposed** |
| `config/macro.yaml` | `core/rules` (immutable model, no financial defaults, validation, one JSON store with edit history); `config.py` (credentials, cache, trading dir for rules JSON, skill env) | Overlay rule objects in the rules store (§7); paths and decision-time constants in `config.py` | **proposed** entries |
| Daily run | `core/skills` (72-entry YAML manifest, runner as subprocess with env-only credentials, runs, workflows as YAML pipelines with decision gates) | Macro skills and `workflows/macro_daily.yaml` (§3.9) | **proposed** |
| Study scripts | `docs/` (`build_models_primer.py`, `drift_study.py`; `asset_expansion_study.py` writes one JSON card per model) | `docs/macro_overlay_study.py` (one JSON card per overlay rule); `docs/vol_backtest.py` for B5 (the review's name for the rolling-origin VaR study) | **proposed** |
| Tests | `tests/run_all.py`: engine + quant + FICC acceptance, hermetic (network touchpoints patched to raise) | Macro unit, integration and golden tests on frozen fixtures (§9) | **proposed** |

### 3.5 Core interfaces

These are binding in semantics. Rename them to match the codebase if necessary. Every location is **proposed** unless the column says "exists".

```python
# core/ficc/data  (exists; these functions proposed)
def pit_value(series_id: str, decision_utc: datetime) -> PITValue | MissingInput
#   PITValue(value: float, obs_date: date, obs_utc: datetime, available_at_utc: datetime,
#            retrieved_at_utc: datetime, vintage: str|None, source: str, provider_mode: Literal["explicit","auto"],
#            synthetic: bool)   # synthetic=True is never accepted for an acting input -> MissingInput
def decision_time_utc(market: str, session_date: date) -> datetime          # the official close (P5)

# core/calendars (exists; proposed)
def usable_at(series_id: str, obs_date: date, market: str) -> datetime        # first decision_utc that may use it (§4.1)

# core/quant/risk (exists: risk.py; proposed functions)
def market_vol_target(market: str, decision_utc: datetime) -> VTResult        # sigma_ann (SMA20), weight in [0,1], label, inputs
def sleeve_vol_scale(market: str, family: str, decision_utc: datetime) -> VSResult
def hedge_state(decision_utc: datetime) -> HedgeState
def drawdown_ladder(nav_path, decision_utc: datetime) -> LadderState           # step in {none, -8, -12, -15}

# core/quant/signals (exists; proposed)
def dm_gate(market: str, decision_utc: datetime) -> Multiplier               # value in {0.5, 1.0}
def apply_overlays(composite, multipliers, basis) -> Weights                  # bounds P2, exposure basis P8, clip log

# FORWARD-SIM legs (core/quant/risk; proposed)
def fwd_krw_leg(decision_utc: datetime) -> Multiplier                         # value in {0.75, 1.0}; status="FORWARD-SIM"
def fwd_rates_leg(decision_utc: datetime) -> Multiplier                       # value in {0.5, 1.0};  status="FORWARD-SIM"

# core/ficc/macro (exists; proposed builders)
def build_macro_state(market: str, decision_utc: datetime) -> dict           # validates against macro_state schema
def build_overlay_decisions(market: str, decision_utc: datetime) -> list[dict]
def build_context_log(decision_utc: datetime) -> dict

# core/engine (exists; proposed hooks)
def evaluator_block(rule_id: str, decision: Decision, state: MacroState) -> Decision   # → BLOCKED(reason) for new entries only
def runtime_halt(reason: str) -> None                                          # → HALTED; re-arm refused during cooling-off

# core/quant/backtest (exists; proposed)
def overlay_card_eval(card: CardHeader) -> CardResult                          # on/off books, static comparator, §8.7 checks
```

**Rules every interface must follow:**
- Every function takes `decision_utc` and reads data only through `pit_value`.
- No function reads a raw DataFrame of a series directly. The lag audit enforces this.
- If any **acting** input is missing, stale, or synthetic, the function returns the previous state with `status="STALE_INPUT"` and raises an alert. It never interpolates.
- No function in this list may import an order-submission client (T-RO-01).

### 3.6 Reconciliation with the existing macro sheet (`core/ficc/macro`)

**What exists.** An 18-indicator sheet, z-scores, a "regime read" and a daily/weekly brief.

**What the sources do not give.** The list of the 18 indicators, the z-score windows and the regime-read method. The reconciliation below is therefore given as **rules plus a proposed mapping**. It must be completed against the actual indicator list (backlog BL-G06).

**Rules (binding):**
1. **Every indicator in the sheet becomes a CONTEXT item.** It is logged in `context_log` with `obs_date`, `available_at_utc` and source, unless it is one of the acting inputs below.
2. **Z-scores stay display-only.** They are computed causally, on expanding or trailing windows ending at `decision_utc`, and never thresholded for exposure (P6, P9).
3. **The regime read becomes a display label in the brief.**
   - It may not feed `core/quant/signals`, `core/quant/risk` or the engine unless it is registered as a card and passes.
   - If it uses smoothed regime probabilities, it must switch to filtered probabilities even for display (§10 item 11).
   - Its label must not reuse the calm / normal / elevated / stressed names. Those names belong to the volatility display label of §5 R-06.
4. **The brief gains a macro_state section.** It shows the vt and vs weights, the flags, each card's verdict, the FORWARD-SIM legs (marked "not a recommendation") and the event calendar.

**Acting inputs, the only series that feed sizing:**

| Input | Feeds | Card |
|---|---|---|
| KOSPI and S&P 500 (or US sleeve) official closes | `vt(m)` via SMA20 σ̂ | R-06 |
| Momentum sleeve daily returns | `vs(m, momentum)` | R-03 |
| Market 24-month return and 126-day realised vol | D&M gate | R-04 |
| VIXCLS / VXVCLS | new-entry block (evaluator) | R-08 |
| Samsung + SK hynix and KOSPI market caps | Korea caps (risk layer) | R-07 (invariant) |
| Core PCE YoY, stock–bond corr63, daily broad-USD change | `hedge_state` (risk model only; no exposure effect) | R-09 (invariant) |
| USD/KRW (KIS fixing; ECOS 15:30 KST history) | FORWARD-SIM book only | R-11 |
| US 10y (KIS quote at the close) | FORWARD-SIM book only | R-12 |

**Proposed mapping of typical sheet indicators.** This applies if and only if an indicator is present in the sheet:

| Indicator class | Role in v1.1 | Why |
|---|---|---|
| Policy rates (Fed funds, BoK, BoJ), 2y, 10y, 30y, curve slopes (10y–3m, 10y–2y) | CONTEXT (10y also feeds the R-12 FORWARD-SIM book) | N-11, N-30 |
| Real yields, breakevens, 5y5y, term premium | CONTEXT | N-26 |
| Credit spreads (HY OAS, Baa−10y) | CONTEXT | N-13 (BL-C03) |
| Broad USD, DXY, USD/JPY, USD/KRW | CONTEXT; broad USD daily change feeds `hedge_state`; USD/KRW feeds the R-11 FORWARD-SIM book | N-29, N-22 |
| Oil (named series), gold, copper | CONTEXT; oil feeds Monte Carlo scenarios | N-43, N-44 |
| VIX, VIX3M, MOVE, VKOSPI | VIX/VIX3M acting (R-08 entry block); MOVE and VKOSPI CONTEXT | N-04 |
| CPI, core PCE, unemployment, payrolls, claims, Sahm | CONTEXT; core PCE feeds `hedge_state` | N-30, N-28 |
| PMI, GDP, surveys, Street forecasts | CONTEXT (forecasts never as inputs) | N-56 |

### 3.7 Reconciliation with the signal composite (`core/quant/signals`)

**What exists.** A 6-component composite. Its components are not listed in the sources.

**Rule (binding).** Overlays attach to components through a **family tag**: momentum, reversal, flow, quality or ts_trend. A component with no family tag receives no family overlay (multiplier 1.0) and is still subject to `vt(m)` and the risk layer. The mapping of the six components to families is **proposed** and must be filled from the code (backlog BL-G07).

**Implication.** Overlays never create a new component and never change a component's sign (P1).

### 3.8 Engine mapping (simulated order book, runtime states, evaluator decisions)

| v1.0 concept | QUANTGEN mechanism |
|---|---|
| "Execution", "orders", "positions" | `core/engine/orders`: the simulated order book. Daily decisions are priced at the official close of t and earn from t+1 (QUANTGEN rule 02). Intraday simulated entries (evaluated on KIS quotes by the runtime) are priced at the quote that triggered them, with the quote timestamp. Every simulated fill is charged the pre-registered cost (P10). |
| "0× only from the fail-closed risk engine" | **Backtests:** `core/quant/risk` returns 0 only for a risk-limit breach, the ladder's −15% step, or a data or system failure. **Simulated book:** `core/engine/runtime` enters **HALTED**, which sets target exposure 0 from the next decision and records `halt_reason`. Leaving HALTED requires an operator re-arm (DISARMED → ARMED). Re-arm is refused for 10 sessions after a ladder −15% halt. HALTED triggers (**proposed** list): ladder −15%; risk-limit breach; lag-audit violation at runtime; schema or bounds failure in a macro artifact; an acting input stale beyond its maximum staleness for more than 1 decision; feed heartbeat loss > 60 s during a session. |
| "Entry blocks" (R-08 stress block, R-10 event windows, ladder −12%) | `core/engine/evaluator(rule, quote) → decision` returns `BLOCKED(rule_id, reason)` for any **new-entry** decision while the block is active. Holds and exits are never blocked. The backtest applies the same rule at daily resolution. |
| "Live shadow book" | **FORWARD-SIM**: separate simulated books (overlay-on and overlay-off; one more per FORWARD-SIM leg) that run forward from the date the card header is committed. Each writes timestamped `macro_state` and `overlay_decision` artifacts. |
| "Kill", "manual override" | Card demotion (§8.8). Any edit of an acting parameter outside a card revision appears in the rules store's edit history; it demotes the card and opens a new revision. |
| Trigger and switch counts | `core/engine/state` (persisted trigger counts) also persists per-card switch counts against the switch budgets (§8.8) (**proposed**). |

### 3.9 The daily workflow (`core/skills/workflows/macro_daily.yaml`, proposed)

```yaml
# proposed; YAML pipelines with decision gates exist in core/skills/workflows
name: macro_daily
runs: [after_close: KRX, after_close: NYSE]   # decision_utc = official close; run starts after the publication buffer
steps:
  - skill: macro.pit_snapshot          # core/ficc/data: pit_value for every registry series at decision_utc
  - gate: data_ok                      # decision gate: any acting input missing/stale/synthetic → fail_closed=true, alert,
                                       #   previous state carried; repeated → engine HALTED
  - skill: macro.lag_audit             # every acting input: available_at_utc <= decision_utc, else HALT (T-LAG-01)
  - skill: macro.vol_and_overlays      # core/quant/risk + core/quant/signals: vt, vs, D&M, hedge_state, caps, ladder
  - gate: bounds_ok                    # schema + P2 bounds + exposure basis; failure → HALTED
  - skill: macro.build_artifacts       # macro_state, overlay_decision (with card verdicts), context_log, event windows
  - gate: verdict_filter               # only PASS-card factors enter the recommended book; others → descriptive book
  - skill: macro.engine_feed           # push weights / BLOCKED rules to core/engine (simulated order book only)
  - skill: macro.brief                 # Macro page and weekly brief section
```

Credentials stay env-only, as in the existing runner. The Claude API, when a key is set, receives the computed numbers only and never decides (QUANTGEN FAQ).

### 3.10 If a broker path were ever added

QUANTGEN has none, and its first rule says there is nothing to switch on. Adding one would change the project's founding rule. That is a decision for the owner, not for this spec. This spec therefore does not design one. It records only what would have to remain true:

1. Only cards with a **PASS** verdict could drive it. The pre-registered costs (P10) and the 2× stress would still apply.
2. It would have to be **fail-closed**. HALTED, any lag-audit or schema failure, and any stale acting input would block submission. 0× would still come only from the risk layer.
3. Its own forward record would be gated like any card. No backtest alone could enable it.
4. Nothing in §5 would change. The overlays would still output bounded multipliers only.

Every backlog item that would need a real order path or fills is listed in the backlog's "blocked by read-only design" section.

---

## 4. Data layer specification (`core/ficc/data`, `core/quant/history`, `core/calendars`, `core/markets`)

### 4.1 Time rules

**Storage.**
- All timestamps are stored in UTC, as ISO-8601 with a "Z" suffix.
- Every record carries four dates:
  - `obs_date`: the market/local date the value refers to;
  - `obs_utc`: when the observation was made;
  - `available_at_utc`: when it was published or became usable;
  - `retrieved_at_utc`: when QUANTGEN fetched it. The 6-hour `~/.nextgen/ficc_cache` keeps this stamp, and a cached value is never served past its maximum staleness.

**Market clocks** (`core/markets` holds the session; `core/calendars` the holidays and DST).

| Market | Time zone | Regular session | Official close in UTC | Other |
|---|---|---|---|---|
| KRX | KST = UTC+9, no daylight saving | 09:00–15:30 | 06:30 UTC | Closing auction 15:20–15:30 KST. NXT after-market 15:40–20:00 and KRX after-hours 16:00–20:00 are excluded from signals. |
| NYSE | ET (EDT = UTC−4 from Mar to Nov; EST = UTC−5) | 09:30–16:00 | 20:00 UTC (EDT) / 21:00 UTC (EST) | The 16:00 ET close is 05:00/06:00 KST the next day. |

**Event times.**

| Event | Local time | KST |
|---|---|---|
| US CPI / NFP | 08:30 ET | 21:30/22:30 KST the same day |
| FOMC statement | 14:00 ET | 03:00/04:00 KST the next day |
| H.15 (DGS10 and other daily rates) | 16:15 ET on the **next business day** | 05:15/06:15 KST two calendar days after D |
| H.10 (DEXKOUS, DEXJPUS, DTWEXBGS) | Mondays 16:15 ET, for the previous business week | Tuesday 05:15/06:15 KST |
| VIX / VIX3M official close | 16:15 ET | 05:15/06:15 KST the next day |

**Decision time (binding): decide at the close of day t; earn from day t+1.**
- `decision_utc` is the **official close** of the session being decided: KRX 06:30Z; NYSE 20:00Z in EDT or 21:00Z in EST.
- The workflow runs after the close (§3.9). It may read only inputs with `available_at_utc ≤ decision_utc`.
- The resulting weights are priced at the close of t in the simulated order book and earn the return from close(t) to close(t+1).
- **Change from v1.0.** v1.0 decided at 15:15 KST and used the 15:15 price as a proxy for the close, so that real orders could reach the closing auction. QUANTGEN places no orders, so the proxy is removed and the official close is used.

**Cross-time-zone rule (binding).**
- **US data for KRX decisions.** A US- or New-York-dated datum dated D (New York date) may enter the KRX decision at the close of Korea date K only if **D ≤ K − 1 calendar day** and its `available_at_utc` ≤ 06:30Z on K.
- **The US session as an input.** The US session dated D closes at 05:00/06:00 KST on D+1, so it is usable at the KRX close of the next KRX session (K = D+1 or later). It is an **opening-gap input** for KRX date D+1 and an input to the close-of-(D+1) decision, which earns close(D+1) → close(D+2).
- **The forbidden case.** Never use the US session dated K for a KRX close-to-close return dated K. That mistake produced a fake +0.31 Sharpe (N-47).
- **H.15 (DGS10 and every H.15-based series).** DGS10(D) is posted at 16:15 ET on D+1.
  - **US decision.** That is after the 16:00 ET close of D+1, so the first US decision that may use it is the close of **D+2 business days**.
  - **KRX decision.** The first decision that may use it is the KRX close on Korea date D+2 calendar days (05:15/06:15 KST on D+2 precedes 06:30Z).
  - **v1.1 correction.** v1.0 called "+1 business day" strict. It is 15 minutes early for a decision at the close.
- **H.10 (DEXKOUS, DEXJPUS, DTWEXBGS).** A value dated D (Monday–Friday) is published the following Monday at 16:15 ET, which is Tuesday 05:15/06:15 KST. It is usable from the KRX close on that Tuesday and from the US close of the business day after that Monday (publication at 16:15 ET is after that Monday's close). Holiday Mondays shift publication by one day.
- **Two timing regimes.** A backtest declares which one each input uses.
  - **Value timing (live-feed proxy).** The value is used from the first decision after its observation time. This is legitimate only when production reads a live, timestamped feed of the same quantity: the KIS USD/KRW fixing, the KIS US 10y quote or the ECOS 15:30 KST close. The backtest result must then be labelled "value timing".
  - **Publication timing (strict).** The value is used from the first decision after its official publication. This is mandatory whenever the production source is the published series itself.

**Monthly series.**
- Store them on an explicit monthly index.
- Compute YoY and 3-month changes by **calendar offset**, never by positional `shift`.
- A missing month (Oct-2025 CPI and household survey, never collected) makes every derived value that spans it NaN.
- Test value: Aug-2026 CPI YoY is **3.35%**. A positional `shift(12)` gives 3.71%, which is wrong.

**Missing, stale or synthetic acting input.** The state stays unchanged, `status="STALE_INPUT"`, an alert is raised, and nothing is interpolated. A value from the "auto" provider's synthetic fallback counts as missing. Repeated failure for more than one decision moves the engine to HALTED (§3.8). Default maximum staleness:
- 1 trading day for daily market series;
- 3 days for weekly series;
- 1 release cycle for monthly series.

**Vintages.**
- Every fetch is stored with its retrieval time.
- Backtests of revised macro series (payrolls, unemployment, GDP, PCE) must use ALFRED vintages.
- Acting rules use only market-priced series, which are not revised. Vintages matter for context items and research.

**Named series.**
- Every series ID is explicit. "Brent" must be either `DCOILBRENTEU` (Dated Brent spot, FRED/EIA) or `BZ=F` (ICE front-month futures, Yahoo).
- Continuous-futures returns across rolls are forbidden. Yahoo's BZ=F printed a "−14.5%" roll artefact on 1 Apr 2026.

**Closes, not intraday prints.**
- Use KRX regular-session official closes.
- Example: on 9 Mar 2026 the KOSPI close was 5,251.87 (−5.96%). The −8.11% figure was a 10:31 circuit-breaker print, not a close.

**Price convention.** The core history loader does not state whether "adjusted" closes include dividends (architecture review, finding A3). The golden values use ^KS11 **price** returns and French total/excess returns as stated in §9.3. A vol target is insensitive to this, but backtest returns are not, so every card records the convention.

### 4.2 Series registry (a data file next to `core/ficc/data`, proposed)

**Role codes:**
- **A**: acting input of a BUILD NOW card or invariant.
- **F**: input of a FORWARD-SIM card only.
- **C**: context only.
- **H**: history or backtest only.
- **P**: planned.

**Korea**

| Series | Source / ID (QUANTGEN provider) | Freq | Publication / available_at rule | Role |
|---|---|---|---|---|
| KOSPI, KOSPI200, constituents OHLCV | KIS Open API quotes (KRX official); KRX marketplace (session close) | daily | the official close, 15:30 KST = 06:30Z | A |
| Samsung (005930), SK hynix (000660) prices and market caps; KOSPI total market cap | KIS / KRX marketplace | daily | KRX close | A (concentration caps) |
| KOSPI investor-type net buys (foreign / institution / individual) | KIS ("investor flows") | daily (final after close) | after the close; preliminary intraday figures are stamped with their own time | C (log from day one; backlog BL-C06) |
| KRX margin debt; leveraged single-stock ETF AUM | KRX / KOFIA (new provider, proposed) | daily | per source | P (backlog BL-U01) |
| USD/KRW | **Production:** KIS USD/KRW fixing quote stamped ≤ 06:30Z on K. **History:** BoK ECOS 15:30 KST close (new provider, proposed; BL-D13), else FRED `DEXKOUS` (H.10 noon New York). | daily | ECOS close available from 15:30 KST on K. **DEXKOUS dated D is published the following Monday 16:15 ET** and is usable under strict timing from the KRX close of the Tuesday (KST) after that week. Value timing (D ≤ K−1) is a live-feed proxy and must be labelled. Production never reads DEXKOUS. | F (R-11); C |
| BoK base rate; Korea CPI | BoK ECOS / KOSIS | event / monthly | release timestamp | C |
| VKOSPI | KRX | daily | close | C (logged vol-estimator alternative) |
| DART filings (rights offerings, listings); KIND; KOSPI200 / MSCI index-change announcements | OpenDART; KIND; KRX / MSCI | event | filing timestamp | C (calendar flag); exclusions in backlog |

**United States**

| Series | Source / ID (QUANTGEN provider) | Freq | Publication / available_at rule | Role |
|---|---|---|---|---|
| US equity sleeves and index (S&P 500 or the sleeve's own returns) | KIS quotes; FMP EOD history; Yahoo | daily | US close | A |
| VIX, VIX3M | FRED `VIXCLS`, `VXVCLS` (CBOE); Yahoo `^VIX`, `^VIX3M` | daily | Official close of D is 16:15 ET. Usable at the US close of D+1 and at the KRX close of K ≥ D+1. | A (R-08 entry block) |
| US 10y yield | **Production:** KIS US 10y yield quote stamped ≤ the US close. **History:** FRED `DGS10` (H.15), and `^TNX` (Yahoo) as a live-feed proxy from 2015. | daily | **H.15 posts DGS10(D) at 16:15 ET on D+1.** A strict backtest of a US close decision uses DGS10(D) from the close of D+2 business days. Fed H.15 page fetched 2026-10-02. | F (R-12); C |
| DFII10 (10y TIPS), T10YIE, T5YIFR (5y5y), DGS2, DGS30, T10Y3M, T10Y2Y | FRED (H.15-based; same posting rule) | daily | next business day, 16:15 ET | C |
| Kim–Wright 10y term premium | FRED `THREEFYTP10` (name the model; do not mix it with ACM) | daily (posted with a lag) | as posted | C |
| MOVE | Yahoo `^MOVE` | daily | close | C |
| Broad USD | FRED `DTWEXBGS` (H.10; weekly publication) **plus a live proxy** (e.g., DXY close, labelled as such) | daily | H.10 weekly rule | A (`hedge_state`, risk model only); C |
| USD/JPY | FRED `DEXJPUS` (history); KIS or Yahoo live quote | daily | H.10 rule / live | C; P (FX sleeve) |
| HY OAS; Baa−10y | FRED `BAMLH0A0HYM2` (posts with ≈ 1-day lag; on FRED only since 2023-10); `BAA10Y` | daily | next day | C (backlog BL-C03) |
| Brent | `DCOILBRENTEU` (Dated spot) **and** `BZ=F` (front-month futures); always name which | daily | per source | C; Monte Carlo scenarios |
| Core PCE, PCE, CPI, core CPI | FRED `PCEPILFE`, `PCEPI`, `CPIAUCSL`, `CPILFESL`, with ALFRED vintages | monthly | BEA/BLS release time; Oct-2025 CPI is missing | C; core PCE YoY feeds `hedge_state` |
| UNRATE, SAHMREALTIME, PAYEMS, ICSA | FRED / ALFRED | monthly / weekly | release time; Oct-2025 household data missing | C |
| FEDFUNDS / DFEDTARU; FOMC statements and calendar; SEP Table 2 | Fed; FRED | event | statement time (14:00 ET) | Calendar; C; Monte Carlo priors |
| US EPU (daily) | FRED `USEPUINDXD` | daily | as posted | C |
| 3-month T-bill (risk-free rate) | FRED (already QUANTGEN's risk-free source) | daily | H.15 rule | H (Sharpe on excess returns where stated) |

**Other**

| Series | Source / ID | Freq | Publication / available_at rule | Role |
|---|---|---|---|---|
| Ken French factor files (US daily 5-factor, Mom, ST_Rev; regional Mom daily; monthly 1926+) | French Data Library | daily / monthly | as posted | H (benchmarks, golden values; frozen in test fixtures) |
| SOX, S&P 500, Nikkei, TAIEX, Shanghai, HSI | KIS (US indices); Yahoo | daily | close | A (opening-gap input; Korea covariance) |
| US release calendar (BLS/BEA), BoJ/BoK/ECB calendars, hyperscaler earnings dates | official calendars; company IR | event | scheduled time plus status | Calendar (`core/calendars`) |

---

## 5. Rule specifications

**Build status** (what to implement now):
- **BUILD NOW**: implement in v1.1.
- **FORWARD-SIM** (v1.0: SHADOW): implement in v1.1 as a separate simulated book only. It never feeds the recommended book until re-gated (§8.8).
- **DEFERRED**: specified, dormant until the planned sleeve exists.

**Rule kind** (how the gate treats it):
- **INVARIANT**: data discipline, a bound, a risk limit or a risk-model assumption. It is enforced in every book, it is not a model card, and it makes no performance claim.
- **CARD-O**: a model card with an outperformance claim. It goes through the standard nine-step gate (§8.1).
- **CARD-P**: a model card with a protective claim. It goes through the protective class (§8.7).
- **CONVENTION**: delays or annotates simulated entries only. It is logged and measured, and never claimed as performance.
- **CONTEXT**: logged, never acts.

**Indicative verdict.** Each card below carries the verdict that R4b's local reference computation points to (§8.9). It is **not** a run of QUANTGEN's gate. The formal verdict comes from `docs/macro_overlay_study.py` on QUANTGEN's data and engine.

Every rule writes its inputs (with `available_at_utc`), its outputs, its reasons and its card verdict into the artifacts of §6.

**Timing note for every rule.** Weights are decided at the close of t from inputs available by then, and earn from t+1 (P5, §4.1). The R4 golden values were computed on exactly this convention: a weight built from data through the close of t−1 is applied to the return of t. The exceptions are flagged in §9.3.

### R-01 Point-in-time and cross-time-zone discipline — BUILD NOW · INVARIANT

| Item | Specification |
|---|---|
| **Purpose** | Remove the largest source of fake edge |
| **Where** | `core/ficc/data` (PIT layer, lag audit); `core/calendars` (`usable_at`) |
| **Inputs** | Every series in §4 |
| **Rule** | For every acting input, `available_at_utc ≤ decision_utc` (the official close). Lags are calendar-based. For Korea, apply the D ≤ K − 1 rule. Apply the strict H.15 (+2 business days for a US close decision) and H.10 publication rules whenever the production source is the published series. If a required input is missing, stale or synthetic: state unchanged, alert, and `fail_closed=true` in `macro_state` for that component; repeated → HALTED. |
| **Output** | `macro_state.inputs[]` with timestamps; a `lag_audit` record in every backtest result and on every card |
| **Evidence** | N-46, N-47. Korea gate +0.31 (look-ahead) → +0.05; KRW 0.5× leg +0.07 on DEXKOUS dates → +0.03 with Yahoo timing. Rates leg (R4, gross): +0.038 value timing → +0.010 at +1 business day → **−0.000 (share 0.53) at the strict +2 business days (R4b)**. KRW 0.75× leg (gross): +0.032 value timing → **+0.001 (share 0.53) at strict H.10 publication (R4b)**. CPI 3.71% vs 3.35%. |
| **Failure modes** | Silent forward-fill of weekly H.10 data; positional lags; unnamed series; the "auto" provider silently returning synthetic data for an acting input |
| **On violation** | Any lag-audit violation invalidates the backtest result or forward record it touches. The card study refuses to write the card. At runtime it moves the engine to HALTED. |

### R-02 Overlay bounds and composition — BUILD NOW · INVARIANT

| Item | Specification |
|---|---|
| **Purpose** | Enforce P2 and P8 |
| **Where** | `core/rules` validation (rule objects); `core/quant/signals` (`apply_overlays`); artifact schemas (§6) |
| **Rule** | Implement §3.3. `assert 0.5 <= overlay_multiplier <= 1.0` and `assert 0.0 <= vt, vs <= 1.0` at the schema, rules-store and code level. Every multiplier record has `exposure_basis ∈ {active, total}`. The overlay layer cannot emit 0; 0× exists only in the risk layer and in HALTED. |
| **Evidence** | N-02, N-03. Four-state table −0.07. Partial de-risking beats hard switching: real-time Markov 0.5/1 vs 0/1, SR 0.554 vs 0.390 (US) and 0.442 vs 0.137 (KOSPI), both net of 10 bp (R2 re-run). R4 KOSPI vol target cap 1.5: SR 0.534 vs 0.638 at cap 1.0. |
| **On violation** | Not applicable (invariant): the rules store refuses the rule |

### R-03 Momentum own-volatility scaling — BUILD NOW · CARD-O (indicative: PASS on French data)

| Item | Specification |
|---|---|
| **Purpose** | Size every cross-sectional momentum sleeve by its own risk. This is the strongest, most replicated overlay. |
| **Where** | `core/quant/risk.sleeve_vol_scale`; applied in `core/quant/signals` |
| **Inputs** | The daily returns of the sleeve's unit-gross long/short factor series: long leg +1 and short leg −1 notional, same construction as the sleeve but scaled to unit gross. For a long-only sleeve (KIS cannot short), the benchmark-relative active return series. |
| **Formula** | `σ126(t) = stdev(r_sleeve[t−125 … t]) × √252`, using returns through the close of t. The weight decided at the close of t and earning from t+1 is `vs = min(1.0, 0.12 / σ126(t))`. Minimum 126 observations; before that, `vs = 1.0` and the state is flagged `WARMUP`. |
| **Parameters** | Window 126 days; target 0.12 annualised (Barroso–Santa-Clara's published target, chosen ex ante); cap 1.0; no floor. Fallback when a unit-gross long/short series cannot be built: target = the sleeve's expanding median σ126, scale-free. That fallback must be declared on the card before the study. |
| **Output** | `overlay_decision.vol_scale`, with `exposure_basis=active` |
| **Evidence (gross)** | N-06. US French Mom 1990–2026: static SR 0.399 → **0.714** (R4, cap 1.0) (+0.31, share 1.00); max DD −63.3% → −27.9%. With cap 2.0, Q1b found 0.907, so the cap costs −0.19 over the full sample, −0.23 in 1990–2007 and 0.000 in 2020–26. Regions (R4, cap 1): Japan 0.073 → 0.196; Europe 0.843 → 1.143; APxJ 0.924 → 1.125, but −0.023 in 2016–26; Developed ex-US 0.799 → 0.996. Literature: D&M *JFE* 2016 Table 7, constant-vol 1.041 vs static 0.682 (1934–2013). |
| **Evidence (net, R4b)** | US shares via KIS, 50 bp per side on the overlay's own turnover (both legs; 0.85 units a year): SR **0.672** (2×: 0.631); ΔSR vs static +0.273 (share 1.00); gate-style one-sided p ≤ 0.001 with 10-session and Politis–White (251-session) blocks; 70% of calendar years positive. French Mom is gross of its own constituent turnover. Leaving that turnover uncosted favours the static sleeve, so the comparison is conservative for the overlay. |
| **Failure modes** | Lags fast recoveries after vol spikes: May–Nov 2008 relative −17.1%; Apr–Oct 2000 −12.0%. Gains decay after publication with cap 2 (R2-P2): +0.66 (1990–2011) → +0.26 (2012–26). Under this spec's cap 1 (R4) the gain is +0.20 in 1990–2007, +0.20 in 2012–26 and +0.26 in 2020–26: the cap removes most of the pre-publication gain, and the full-sample +0.31 leans on 2008–09. APxJ was negative in the 2020s. |
| **Card** | CARD-O. Benchmark: the same sleeve unscaled, on the same costed engine. Indicative PASS on the French series. The formal card must run on QUANTGEN's own sleeve. Demotion: §8.8, and review if the 2016+ ΔSR is below 0 in ≥ 2 regions. |

### R-04 Daniel–Moskowitz bear-state gate, floor 0.5 — BUILD NOW · CARD-O add-on (indicative: INSUFFICIENT DATA)

| Item | Specification |
|---|---|
| **Purpose** | De-risk momentum in bear, high-volatility states, where loser rebounds crush the short side |
| **Where** | `core/quant/signals.dm_gate` |
| **Inputs** | The sleeve market's index: 24-month total return as of the last month-end on or before t, and 126-day daily realised volatility through the close of t |
| **Formula** | `bear24 = (Π_{24 months}(1 + r_month) − 1) < 0`. `hivol = σ126_mkt(t) > Q_{2/3}(σ126_mkt over [start … t])`, an expanding quantile with at least 252 observations. `dm = 0.5 if (bear24 and hivol) else 1.0`, decided at the close of t, earning from t+1. |
| **Parameters** | 24 months; 126 days; quantile 2/3; multiplier 0.5; `exposure_basis=active`. The trigger is exactly the published one. A 200-day moving average is **not** a substitute. |
| **Output** | A family overlay multiplier for momentum |
| **Evidence (gross)** | N-07. *JFE* 2016 Table 7 (1934–2013): dynamic OOS 1.194 vs constant-vol 1.041 vs static 0.682. International: Europe 0.462 → 1.130, Japan 0.067 → 0.416, UK 0.465 → 0.891. **R4 at floor 0.5:** alone +0.138 (share 0.998). On top of R-03: **+0.084 (0.996)**; ex Sep-2008–Dec-2009 +0.056 (0.97); 2013-04 → 2026-08 +0.055 (0.94). Gate on 10.6% of days; 7 spell onsets since 1990; 0.38 transitions a year. |
| **Evidence (net, R4b)** | 50 bp per side, both legs: add-on +0.072 (share 0.983; 2×: +0.061, 0.958); 2013-04 onward +0.044 (0.92). Gate-style one-sided p 0.018 (10-session blocks) and 0.010 (Politis–White, 229 sessions). |
| **Failure modes** | Misses crashes that follow bull markets: Nov-2020 −12.0%, Jul-2026 −10.9%, Jan-2001 −21.9%, all with the gate at 1.0. Slow: May–Nov 2008 +9.5% vs +21.8% static (R4). Evidence is concentrated in 2 crash regimes per century. Untested on KRX stock data. |
| **Card** | CARD-O add-on. Benchmark: the R-03 sleeve. **Indicative verdict INSUFFICIENT DATA**: 7 spell onsets (6 de-clustered at 126 sessions) is far below the Tier A count of 30. The route out is the Tier A-provisional holdout (§8.3; backlog BL-C01 and BL-C12). The floor is contested (0 vs 0.25 vs 0.5; BL-C01). It runs in the specification book at 0.5. It enters the recommended book only on PASS. |

### R-05 Reversal and quality fixed at 1.0× — BUILD NOW · CONVENTION

| Item | Specification |
|---|---|
| **Purpose** | Keep the liquidity-provision and quality premia without levering into their worst variance |
| **Rule** | The reversal and quality families have **no overlay multiplier** (the value is fixed at 1.0) in every state. They are never up-weighted in stress, and never cut by macro or stress flags. Reversal simulated daily entries are decided at the official close of t and earn from t+1. There is no intraday reversal leg. (v1.0's "limit orders into the closing auction" has no object in a read-only app.) |
| **Evidence** | N-09. ST_Rev on VIX-inverted days earned 72%/yr at 30.6% vol, vs 13% at 11.7% otherwise (SR 2.35 vs 1.11), so the mean-variance weight is ≈ 0.8×. 1.5× rules: ΔSR −0.05 to −0.20, and −20.0% relative over Sep-2019 → Mar-2020. RMW at 1.5×: ΔSR −0.01. RMW market beta −0.099 (HAC t −3.0); RMW +8.4% in 2022. Overnight vs intraday reversal: +0.93% vs −1.05% a month (US, 1993–2013). |
| **Net-of-cost requirement** | The reversal family's own card (outside this spec) must clear QUANTGEN's KRX stock cost of 35 bp per side and stay positive at 70 bp. Whether to block reversal in fast stress is contested (backlog BL-C02). v1.0's KIS fill-log test is blocked by the read-only design; BL-C02 now uses KIS quote snapshots. |

### R-06 Per-market continuous volatility target, cap 1.0 — BUILD NOW · CARD-P (indicative: Korea INSUFFICIENT DATA; US REJECT at 50 bp)

| Item | Specification |
|---|---|
| **Purpose** | The primary risk control, especially for Korea. It is not an alpha source; its claim is protective (§8.7). |
| **Where** | `core/quant/risk.market_vol_target`; Korea instrument book declared on the card (P10) |
| **Estimator (v1.1 decision)** | **SMA20 realised volatility** in both Korea and the US: `σ̂_m(t) = stdev(r_m[t−19 … t]) × √252` on daily close-to-close returns through the close of t. B5 pass (v1.2 wording) = 5% VaR exceedance within ±2 binomial SE of 5% over ≥ 200 origins **and** a PIT χ² test (10 equal bins) with p ≥ 0.01. The 0.01 cut-off is the app's own (public page: a PIT p below 0.01 makes GARCH-t on SPY a REJECT) and the rule R4b declared before its run. In FHS form the exceedance rate is partly self-calibrating, so the PIT line is the discriminating check. Basis (R4b B5-style check, declared rule): SMA20 passes the B5 gate in filtered-historical-simulation form on KOSPI 2016–26 (5% VaR exceeded on 4.70% of 2,594 origins, band ±2 SE 4.14–5.86%, PIT χ² p 0.12), on SPY 2016–26 (4.99%, p 0.57) and on the US market 1991–2026 (5.31% of 8,961, band 4.54–5.46%, p 0.98). EWMA(λ = 0.94) also passes everywhere and is the registered challenger (BL-C04): it has lower turnover; in the US, net of 50 bp, SR 0.520 vs 0.505. **GARCH(1,1)-t or GJR may replace SMA20 only after passing B5** in `docs/vol_backtest.py`. The app's own study rejects GARCH-t on SPY (6.6% breaches, PIT p 0.003). R4b's independent re-fit agrees (6.3%, PIT p < 0.001). Under a normal quantile every estimator fails PIT (fat tails), so a σ̂ is never shown as a normal VaR. |
| **Formula** | `vt_m = min(1.0, target_m / σ̂_m(t))`, decided at the close of t, earning from t+1. |
| **Parameters** | Korea: target 0.20, window 20, cap 1.0. US: target 0.15, window 20, cap 1.0. Other markets must be pre-registered per market on their card before they run (**default, judgment**: start from the market's long-run median realised vol). No floor. `exposure_basis=total`. |
| **Display label** | calm / normal / elevated / stressed = σ̂ against the quartiles of its own trailing 756 sessions, computed causally from filtered (never smoothed) values. These are the Quant Lab's conditional-vol labels, reused **for display only**; they never gate anything. On 2 Oct 2026 KOSPI was **elevated** (σ̂ 28.9%, 70th percentile; quartiles 15.7 / 18.6 / 33.6%) and the US **normal** (10.7%, 28th percentile). |
| **Inputs** | KRX official closes (Korea); US close (US). Local inputs only. |
| **Evidence (Korea, gross)** | N-14, N-16. **R4, KOSPI 2016-01 → 2026-10-02:** SR **0.638 vs 0.634** buy-and-hold; max DD −36.8% vs −43.9%. 22 Jun → 30 Jul 2026: **−12.2% vs −38.6%**. Mar-2026: −7.9% vs −19.9%. 2020 crash: −25.8% vs −34.1%. |
| **Evidence (Korea, net, R4b)** | Turnover 1.50 units a year. KRX ETF book (3 bp): SR 0.635 (2×: 0.632), max DD −36.8%. KRX stock book (35 bp): SR **0.605** (2×: 0.573), ΔSR vs buy-and-hold −0.028 (share 0.37), max DD −37.2%. Static book with the same average exposure (0.925): max DD −41.3%, so **ΔMDD +4.4 pp (ETF) / +4.1 pp (stock)**. Jul-2026 window net of 35 bp: −12.3% vs −38.6%. |
| **Evidence (US)** | **R4 gross, US Mkt-RF 1990-02 → 2026-09:** SR 0.602 vs 0.534; max DD −49.9% vs −59.2%. GFC window −20.9% vs −46.5%. **Net of 50 bp (R4b):** turnover 2.52 a year costs 1.26% a year; SR **0.505** (2×: 0.409), ΔSR −0.028 (share 0.29); max DD −53.8% vs −54.0% for the same-exposure (0.890) static book. |
| **Costs (always reported)** | Korea 2016–25 ΔSR −0.077 gross (share 0.06), −0.106 at 35 bp; 2018–24 −0.123 gross (0.03), −0.154 at 35 bp. H1-2026 bull tax: +51.7% vs +101.1% gross (+50.5% at 35 bp). Aug-2024: −7.9% vs −5.5% (missed the rebound). 2020 rebound: +25.9% vs +49.9%. Post-crash 30 Jul–30 Sep 2026: +5.9% vs +22.2%. |
| **Failure modes** | When volatility predicts higher returns (KOSPI 2018–24: corr(vol, forward 22-day return) +0.32), the target costs Sharpe. Slow re-entry after V-rebounds. A 60-day window is worse (KOSPI SR 0.550). In the US at 50 bp per side, daily rebalancing of small weight changes eats the drawdown benefit. |
| **Logged alternatives (never acting)** | (a) `σ̂_alt = max(σ̂_SMA20, implied_proxy)`, with VIX/100 for the US and VKOSPI/100 for Korea. (b) An asymmetric estimator: slow to cut, fast to restore. Both are logged and settled in backlog BL-C04. |
| **Card** | CARD-P (§8.7). **Korea, indicative INSUFFICIENT DATA** at both costs. PC-1 (ΔMDD ≥ 3 pp, also at 2×) and PC-2 (tail-exposure ratio 0.82) pass. PC-3 is inconclusive: point ΔSR vs static +0.001 (ETF) / −0.028 (stock), but non-inferiority p 0.24 / 0.32 (the larger of the 10-session and 101-session block results; 0.21 / 0.29 with 101-session blocks alone). PC-4 benefits concentrate in Jul-2026 (59% of the positive benefit; 3 of 9 episodes positive). At 35 bp the plateau also fails (0.375). **US, indicative REJECT** at 50 bp: PC-1 fails at 1× (+0.2 pp). A slower or banded variant (window 40–60, or a no-trade band) is a **new card** (BL-G03), not a revision of this one. Until a PASS, `vt(m)` runs in the specification book and is displayed as a descriptive control with its verdict. The recommended book carries the invariants (caps, ladder) only. Demotion (§8.8) is judged on drawdown: forward ΔMDD vs the static comparator ≥ 0 **and** forward ΔSR worse than the 2018–24 reference (−0.123 gross / −0.154 at 35 bp). |

### R-07 Korea concentration caps and drawdown ladder — BUILD NOW · INVARIANT (risk limits)

| Item | Specification |
|---|---|
| **Purpose** | Control the dominant Korean risk: KOSPI behaves like a two-stock memory-semiconductor book |
| **Where** | `core/quant/risk` (caps, ladder state); `core/engine/evaluator` (−12% step); `core/engine/runtime` (−15% step → HALTED) |
| **Rules** | (1) **Pair cap:** if the combined Samsung + SK hynix share of KOSPI market cap exceeds **0.45**, their combined weight in the Korea long book is ≤ **0.35**. (2) **Semis cap:** total semiconductor exposure ≤ **0.50** of the Korea long book (**default, judgment**: the evidence calls for a semis cap but gives no level; the level is pre-registered in the rules store and reviewed when the pair's share falls below 0.35). (3) **Single name** ≤ **0.05** of the simulated book's NAV. (4) **Drawdown ladder** on the simulated book's NAV from its running peak: −8% → risk-layer gross × 0.5; −12% → the evaluator blocks new entries and the overlay is forced to 0.5; −15% → **HALTED** (target 0×), operator review, re-arm refused for 10 sessions. (5) Treat Korea gross as semiconductor exposure in the covariance. Shanghai, HSI, TAIEX and Nikkei stay in the Korea covariance. |
| **Evidence** | N-17, N-16. The pair was 55.5% of KOSPI market cap (22% at end-2023) and 51.5% of KOSPI200 (13 May 2026). It supplied ≈ 65–69% of the 2025–26 index-point move and 76.6% of September 2026 foreign selling. Implied share on 2 Oct 2026: ≈ 53.7%. KOSPI–Shanghai daily correlation reached 0.56 in 2026. Ladder levels come from the executive panel's risk officer (EC-E-05, B4). |
| **Review** | Not an alpha rule, so not a card. Its effect on every card's books is reported. Cap levels are reviewed yearly through a rules-store revision. |

### R-08 Stress entry block: VIX ≥ VIX3M — BUILD NOW · CARD-P (indicative: not computed; expected PC-1 failure on v1.0 evidence)

| Item | Specification |
|---|---|
| **Purpose** | Do not open new simulated risk while the market-priced stress state is on. Existing exposure is left to R-06 and R-07. |
| **Where** | `core/engine/evaluator` (BLOCKED decisions); the same rule in `core/quant/backtest` at daily resolution |
| **Inputs** | FRED `VIXCLS` and `VXVCLS`. The official close of D is 16:15 ET (§4.1). |
| **Formula** | `flag = VIX(D) ≥ VIX3M(D)`. The threshold is fixed at parity and **never tuned**. |
| **Effect** | US: the evaluator blocks new cross-sectional momentum entries and all new intraday simulated entries from the session after D. Daily decisions are blocked from the close of D+1, the first US close after the 16:15 ET VIX close. Korea: the same blocks from the KRX session D+1 and its close. Daily reversal entries are **not** blocked (R-05). Nothing is cut and nothing is re-added. |
| **Evidence** | N-04. After VIX ≥ VIX3M, next-5-day realised vol averaged 36.3% vs 13.6%; next-5-day return +0.50% vs +0.22% (t 1.2, not significant). Cut-and-re-add gates: −0.088 Sharpe (−0.185 in 2020–26). The block-only variant is Sharpe-neutral (0.000). The flag is on 10.1% of days, with 14.0 transitions a year (R4), and 64–72 onsets (Tier A count met). **Timing flag:** the R2 tests used VIX(D) for the US return of D+1, i.e. the 16:15 ET value at the 16:00 ET close of D. That is 15 minutes early for a close decision, so the card must be re-run with the D+1-close rule. |
| **Failure modes** | Late: a median 79% of the episode drawdown had already happened at flag-on. It was on for **zero days** in the Jul-2026 KOSPI crash and in the Sep-2026 rates shock. Aug-2024 whipsaw: on 2 Aug, cleared 14 Aug, and the blocked momentum gained +5.0%. |
| **Card** | CARD-P. Not computed in R4b. A block-only rule cannot cut drawdown much once 79% of it has happened, so PC-1 is expected to fail. Until a gate run, the flag is displayed as a stress-state annotation and applied only in the specification book. Switches above 2× the budget of 14 a year → review. |

### R-09 Hedge-validity state — BUILD NOW · INVARIANT (risk-model assumption)

| Item | Specification |
|---|---|
| **Purpose** | Do not count on bond or dollar hedges in the regimes where they fail |
| **Where** | `core/quant/risk.hedge_state`; consumed by VaR/CVaR, stress, and the `core/quant/optimize` covariance inputs |
| **Inputs** | Core PCE YoY (`PCEPILFE`, calendar lag, available at its release). `corr63` = 63-day correlation of daily US equity returns with −Δ10y, where the 10y is the KIS quote at the close; in backtests DGS10 lagged per strict H.15. Daily broad-USD proxy change; equity daily return; 10y change. |
| **States** | `hedge_credit_off = (corePCE_yoy ≥ 3.0) or (corr63 > 0)`. `hedge_failure = (equity_1d < −1.5%) and (USD_1d < 0)` (daily), or the weekly version: S&P week < −2% and broad USD week < 0. `classic_risk_off = (equity_1d < −1.5%) and (USD_1d > 0) and (UST10_1d < 0)`. |
| **Effect** | When `hedge_credit_off`, the risk layer gives **no diversification credit** to duration-type hedges: it uses `max(estimated corr, 0)` between equity and bond/duration legs in VaR, stress, optimiser inputs and sizing. When `hedge_failure`, it also removes USD/JPY-hedge credit. **No equity-gross effect in either case.** |
| **Evidence** | N-28, N-29. Pooled stock–bond correlation (1990–2026) by core PCE: −0.29 (< 2%), −0.11 (2–3%), +0.21 (≥ 3%). Bonds rallied +6.4 bp on the worst 5% of equity days in 2000–20 vs 0.0 bp in 2021–26. USD rose in 10 of 11 S&P drawdowns, but in Apr-2025 the DXY fell 3.9%, the 10y rose 28 bp and the S&P fell 5.4%. After USD↓ and equities↓ weeks (n = 14), the S&P returned +7.27% over 13 weeks vs +2.84% unconditional, so this is **not** a de-risk signal. |
| **Failure modes** | 1990–99 had positive correlation even with core PCE below 2%. corr63 is noisy. QUANTGEN has no bond sleeve, so the effect is mainly on risk-model assumptions (the Bonds and Rates pages and the Portfolio optimiser). |

### R-10 Event calendar, entry windows and opening-gap nights — BUILD NOW · CONVENTION

| Item | Specification |
|---|---|
| **Purpose** | Handle scheduled risk with short no-new-entry windows, not blackouts |
| **Where** | `core/calendars` (event store, windows, KR opening-gap nights); `core/engine/evaluator` (BLOCKED decisions on simulated intraday entries); the Macro and Derivatives pages (annotations) |
| **Calendar entries** | `{event_id, type, region, scheduled_utc, status ∈ {scheduled, released, cancelled, delayed}, source}`. Windows expire automatically when an event is cancelled. Example: the Oct-2025 CPI was never published. |
| **US CPI / NFP (08:30 ET)** | No new US intraday simulated entries 08:25–09:45 ET. Resume at 10:00 ET. For releases with documented pre-release drift (ISM, consumer confidence, IP, GDP preliminary and others), the window starts 30 minutes before the release. No simulated stops are placed inside the window. Daily book unchanged. |
| **FOMC (14:00 ET)** | No new US intraday simulated entries 13:45–15:00 ET. Resume at 15:00 if VIX < its pre-14:00 level, else at 15:30. No pre-FOMC long. Daily book unchanged. The same windows apply to KOSPI200 night futures. |
| **BoK decision** | KOSPI200 futures: no new simulated entries 09:45–10:15 and 11:00–11:45 KST (two windows, because published release times conflict). Equity daily book unchanged: BoK days run at 0.82× normal abs(r). |
| **Every KRX day** | No new intraday simulated entries 09:00–09:30 KST. Signals use KRX regular-session prints only. Daily decisions are taken at the official close (P5). v1.0's opening-auction limit orders and closing-auction routing have no object in a read-only app. |
| **Korea opening-gap event nights** | US CPI/NFP nights, FOMC nights (03:00/04:00 KST) and hyperscaler capex/earnings nights. The next KRX session gets `kr_open_gap_event=true`. The overnight SOX, S&P, ΔUST10 and USD/KRW moves are logged as opening-gap inputs. **No exposure change.** The flag and the realised opening gap feed backlog BL-U03. |
| **Sidecar / circuit breaker** | No new simulated entries for 30 minutes after a circuit-breaker reopening. Quotes read during a halt are marked indicative, as the Derivatives page already does for a board read while the market is closed. **No gross cut** (contested; backlog BL-C05). v1.0's "queue orders, no market orders, cancel resting orders" needs a broker path and moves to the backlog's blocked section. |
| **Oil / geopolitical** | Scheduled or known risk windows (OPEC, weekend escalations) are calendar entries with a `scenario_tag` for Monte Carlo (R-16). No exposure gate. |
| **Not built** | 24-hour blackouts; daily-book blackouts; quad-witching blackout; momentum decision-day size-down (backlog BL-O02). |
| **Evidence** | N-37, N-38, N-40, N-41, N-44. S&P on FOMC days +5.5 vs +5.1 bp (2015–26). Pre-FOMC drift 44.5 → 9.2 bp (not significant). FOMC days 2021–26: abs(r) 97 vs 74 bp. Day after FOMC, KOSPI abs(r) 0.78% vs 0.92%. Quad witching abs(r) 0.851% vs 0.894% (t −0.38). The prior US session explains ≈ 15% of KOSPI variance; SOX(t−1) β 0.247 (0.559 in 2026); ΔUST10(t−1) t −3.8. 80.9% of 9–10am volatility interruptions fire in the first 30 minutes. KOSPI +17.91% on 31 Jul 2026 after a capex reaffirmation. |
| **Measurement** | The windows cannot be tested on local data (no minute bars), and a read-only app has no fills. Log every window hit and every evaluator BLOCKED decision. Also log the KIS quote spread and 1-minute range around each window, if KIS quotes carry bid/ask (**proposed**; to be confirmed against `kis_client.py`). Review after 12 months of logs (backlog BL-C02 and BL-O06). |

### R-11 FORWARD-SIM S1: USD/KRW leg — FORWARD-SIM · CARD-P (indicative: REJECT on protection; Tier B under strict timing)

| Item | Specification |
|---|---|
| **Definition** | `krw20(t) = ln(USDKRW(t) / USDKRW(t−20 obs))` on the **production series**: the KIS USD/KRW fixing quote, or the ECOS 15:30 KST close, stamped ≤ the KRX close of t. `flag = krw20 > 0.03`. Multiplier `0.75` on Korea market gross (`exposure_basis=total`), decided at the KRX close of t and earning from t+1, **in the S1 forward book only**. **One-sided**: no action when the KRW strengthens. Within the overlay floor 0.5. |
| **Backtest timing** | Strict: H.10 publication (DEXKOUS dated D usable from the KRX close of the Tuesday after D's week), or ECOS 15:30 KST history at value timing (BL-D13). Value timing on DEXKOUS (D ≤ K − 1) is a live-feed proxy and is labelled so. Robustness: one extra session of lag, or Yahoo `KRW=X` lagged 2 sessions. |
| **Golden (R4, gross, value timing)** | ΔSR vs buy-and-hold **+0.032 (share 0.965)**; on top of VT20 **+0.042 (0.977)**; +1-session or Yahoo timing **+0.016 (0.76–0.78)**. On 9.0% of days; 65 raw / 35 de-clustered onsets (2015–26); 11.1 transitions a year. The 0.5× reference reproduces +0.060. |
| **Golden (R4b)** | **Strict H.10, gross:** +0.001 (share 0.53) on buy-and-hold; +0.013 (0.74) on VT20; 26 onsets de-clustered at 20 sessions. **Net, value timing:** KRX ETF 3 bp +0.029 (0.94); KRX stock 35 bp **−0.008 (0.32)**; on VT20 at 35 bp −0.007 (0.34); at 70 bp −0.057 (0.01). Turnover 2.51 a year. |
| **Failure modes** | Near-zero coverage of the worst days of Aug-2024, Dec-2024 and Apr-2025. Off on 4 Dec (−1.44%) and 9 Dec 2024 (−2.78%). Silent in Jul-2026, when the KRW strengthened 7.4% during the −38.6% crash. Its 28 triggers since 2015 (R2 episode rule) were followed by +0.48% over 20 days vs +1.10% unconditional, so it is neither a capitulation nor a continuation signal. |
| **Card** | CARD-P, Tier B under strict timing. PC-1 fails at both timings: ΔMDD vs the same-exposure static book +1.1 pp (value, 35 bp) and +0.1 pp (strict, 3 bp). PC-2 fails at both: tail-exposure ratio 0.99–1.00, i.e. the leg is not de-risked on the worst days. Indicative verdict, following the §8.7 order (sufficiency is decided first): **REJECT** under value timing (35 de-clustered onsets); **INSUFFICIENT DATA by tier** under strict H.10 (26 onsets < 30), with the protective checks already failing. Its formal card needs the timestamped ECOS/KIS history (BL-D13). Until then it is INSUFFICIENT DATA by tier. It keeps running as a labelled forward book (QUANTGEN keeps rejected families running, labelled). Re-gate: backlog BL-S01. |
| **Evidence** | N-22 (CONTESTED: professors split on timing and sign stability; executives Moderate) |

### R-12 FORWARD-SIM S2: US rates-stress leg — FORWARD-SIM · CARD-P (indicative: REJECT at 50 bp and under strict timing)

| Item | Specification |
|---|---|
| **Definition** | `d10(t) = y10(t) − y10(t−20 obs)`, in percentage points, on the **KIS US 10y quote** stamped ≤ the US close of t. `flag = d10 > 0.40`. Multiplier `0.5` on **US duration-sensitive gross** (`exposure_basis=total`), decided at the close of t and earning from t+1, **in the S2 forward book only**. |
| **Scope** | Default, judgment: all US long-only equity exposure; tested on the market, Nasdaq-100, Russell 2000 and small-cap proxies. **Excluded:** momentum and other long/short factor sleeves (momentum 0.5× under rates stress: −0.065), and Korea (only 12 onsets; +0.002 in 2024–26; backlog BL-C07). |
| **Backtest timing** | DGS10 dated D is posted at 16:15 ET on D+1, after the close of D+1, so strict timing uses it from the close of **D+2 business days**. The ^TNX close dated D is a live-feed proxy (2015+). |
| **Golden (R4, gross)** | US 1990-02 → 2026-09, value timing (**not compliant**: DGS10(D) at the close of D): ΔSR vs buy-and-hold **+0.038 (share 0.98)**; on top of VT15 cap 1 **+0.037 (0.97)**; 2020–26 on VT +0.132 (0.999); ex-2022 +0.025. +1 business day: **+0.010 (0.67)** over the full sample, of which −0.017 in 1990–2007. 2015–26: DGS10 timing +0.066 (0.98), ^TNX live proxy +0.071 (0.97), +1 day +0.071 (0.94). On 6.2% of days; 50 onsets de-clustered at 60 sessions (71 at 20 sessions); 7.2 transitions a year. Proxies (value timing): NDX 2008–26 +0.039 (0.94); Russell 2000 2015–26 +0.058 (0.97). |
| **Golden (R4b)** | **Strict +2 business days, gross:** full sample **−0.000 (share 0.53)**; 1990–2007 −0.034; 2008–26 +0.025 (0.77); 2015–26 +0.053 (0.90); 2020–26 +0.084 (0.92); on VT15 −0.007 (0.39), 2020–26 +0.106 (0.94). **Net of 50 bp** (turnover 3.60 a year = 1.80% a year): value −0.065, strict **−0.103 (share 0.00)**; ^TNX 2015–26 −0.020 (0.31); on VT15 strict −0.120. |
| **Failure modes** | Off in Aug-2024 (10y −21 bp), Apr-2025 (move too fast for a 20-day window) and Jul-2026 (+30 bp max). On for only 2 days in Mar-2026, near the low. Post-onset 60-day max DD −7.07% vs −7.17% unconditional: it works through persistence, not prediction. Threshold grid median ≈ +0.01. **State:** the flag is on in data dated 23 Sep 2026 (+50 bp to 30 Sep). Under strict timing the S2 book applies it from the decision at the close of 25 Sep, earning from 28 Sep. |
| **Card** | CARD-P (Tier A count met: 50–71 onsets). Indicative **REJECT** at 50 bp under strict timing. PC-1 fails: ΔMDD −3.5 pp vs the static comparator. PC-2 fails: ratio 0.99. PC-3's point estimate −0.12 is below the −0.10 margin. It keeps running as a labelled forward book. Re-gate: backlog BL-S02. |
| **Evidence** | N-24 (ONE-SIDED: executives Moderate; the professors' real-yield regime finding, N-26, is consistent with it, but they did not test this leg) |

### R-13 Context log — BUILD NOW · CONTEXT (never acts)

Computed daily in `core/ficc/macro`, written to `context_log` (§6.4) and never read by any acting module. The lag audit and an import guard (T-CTX-01) enforce this. It absorbs the existing 18-indicator sheet under §3.6.

| Item | Definition | Why it is context, not a gate |
|---|---|---|
| Sahm (real-time) | `SAHMREALTIME` (and U-3 3-month change, ICSA 4-week average) | Fires a median +2 months after the recession start. Jul-2024 0.53 was followed by 26 months without recession (N-30). |
| 10y–3m and recession probit | `T10Y3M`. Probit `P = Φ(−0.6045 − 0.7374 × spread)`, where spread = monthly GS10 − TB3MS converted to bond-equivalent (Estrella–Trubin published coefficients, 1959–2005). Do **not** log 10y–2y as a prior. | 534-day inversion; P = 0.744 in May-2023 with no recession. 10y–2y was false in 1982, 1998 and 2022–24 and missed 2020 (N-30). |
| Taylor-rule residual range | EFFR minus a family of rules `R = r* + π + 0.5(π − 2) + a·gap`, with π = core PCE YoY, r* ∈ {0.5, 1.0, 2.0}, gap ∈ {Okun 2×(NROU − UNRATE), CBO 100×(GDPC1/GDPPOT − 1)}, a ∈ {0.5, 1.0}. Report the min–max range only. | The residual is smaller than its specification uncertainty. Currently 0.4–2.3 pp below the rules; central −0.9 pp (N-30). |
| Real yield and term premium | `DFII10` level and 20/63-day change; `THREEFYTP10` (named "Kim–Wright"); `MOVE`; 2y, 10y, 30y | 2026 is a real-yield / term-premium regime: TIPS +100 bp vs breakeven +11 bp YTD (N-26) |
| Breakevens | `T10YIE`, `T5YIFR`; yearly all-day Δbreakeven / Δnominal β | An anchoring monitor (N-26, N-32) |
| Credit | HY OAS and BAA10Y levels and 21-day changes | Late, no mean content (N-13) |
| FX | Broad USD (DTWEXBGS plus live proxy), DXY, USD/JPY and its distance to the 160–164 zone, USD/KRW | N-29, N-52 |
| Oil | Dated Brent, BZ=F and their spread | N-44 |
| Inflation | Core PCE YoY, CPI YoY, core CPI YoY (calendar lag) | Hedge state uses core PCE (R-09) |
| Korea | Pair share of KOSPI; KOSPI rv21 and its trailing-3-year percentile; investor-type flows; BoK rate | N-17, N-19, N-21 |
| Policy | FOMC decision, vote split and dissent direction; SEP Table-2 error bands (when released) | N-30, N-56. SEP bands feed Monte Carlo priors (R-16). |
| EPU | `USEPUINDXD` | Variance only (N-04) |
| Existing sheet items | Each of the 18 indicators of `core/ficc/macro` not listed above, with its causal z-score | §3.6 rule 1 |

### R-14 Time-series trend sleeve — BUILD NOW (family configuration) · CARD-O (not computed; card E1 is the nearest prior)

| Item | Specification |
|---|---|
| **Rule** | A diversified, vol-scaled TS-trend sleeve: 12-1 month sign, monthly rebalance. Per-asset weight `= min(1.0, 0.15 / σ_12m)` (default, judgment: Q1b used 15% with cap 2.0; this spec caps at 1.0 per P2). Per-index base weights per §5 R-15. **Exempt** from all overlay multipliers and from the market vol target. Subject to risk-layer caps and the drawdown ladder. Costs per venue (P10). |
| **Evidence** | N-33. An equal-weight vol-scaled 12-equity trend book: SR 0.49 (2001–26; 0.60 with 16 assets), correlation with the S&P 0.08. KOSPI long/flat 0.47 vs buy-and-hold 0.52. KOSDAQ ≈ 0. Trend dead in Europe, the UK and India since 2013. |
| **Failure modes** | 2020: −16.7% vs S&P +16.3%. KOSDAQ was fully long into −39.7% (Feb–Jul 2026). It is not crash protection. |
| **Card** | CARD-O, benchmark = the equal-weight long-only basket of the same indices. QUANTGEN's card E1 (trend switch on US ETF sleeves) was REJECTED on exactly this kind of test: OOS Sharpe 0.84 vs 0.95, p 0.75. The ETF page withholds trend as a signal. So this sleeve is displayed descriptively until its own card passes. Expect the same outcome unless the diversification claim is registered as the card's claim. |

### R-15 Per-market factor priors — rules-store defaults (flagged)

These are starting values for the per-market × per-family weight table, on the prior design's 0–3 scale. Every cell remains a hypothesis to be tested by a card, and every change is a card revision.

| Market | XS momentum | ST reversal | TS trend | Flag |
|---|---|---|---|---|
| US | 2 if vol-scaled with the D&M gate, else 1 | 1 (prior) | 3 | ONE-SIDED (N-35) |
| Europe | 3 | 1 (prior) | 0–1 (STOXX50 0, DAX 1, FTSE 0–1) | ONE-SIDED (N-35); TS trend CORE (N-33) |
| Japan | 0 (vol-scaled R4 SR 0.196: may rise to 1 if verified) | 2 (prior) | 1–2 | ONE-SIDED |
| Korea | 12-1: 0; 12-7 / residual: 1 | 3 (net-of-cost test at 35 bp required) | KOSPI 1, KOSDAQ 0 | **UNVERIFIED** (N-36): no KRX stock-level test yet |
| Taiwan | 1 (prior) | 3 (prior) | 1–2 | TS trend CORE (N-33) |
| China A | 0 (prior) | 3 (prior) | 0 | TS trend CORE (N-33) |
| India | 3 (prior) | 1 (prior) | 1 | TS trend CORE (N-33) |
| EM broad | 3 | 1 (prior) | — | ONE-SIDED (N-35) |
| Crypto | 1 (prior) | 2 (prior) | 2 (own trend plus vol cap; QUANTGEN's card C3 is the trend part) | N-54 (deferred) |

**Prior calibration (one-sided, professors).** When converting published Sharpe ratios into priors, haircut them by the factor-specific out-of-sample declines in Ilmanen et al. (2021): value −49%, momentum −23% (not significant), carry ≈ −25%, defensive no decline, multifactor −18%. The gate's 60% live haircut is printed on every card in addition.

### R-16 Quant Lab calibration and stress scenarios — BUILD NOW (Quant Lab; `core/quant/montecarlo`, `core/quant/garch`, `core/ficc/ratesim`)

| Item | Specification |
|---|---|
| **Rules** | (1) The GARCH/EWMA calibration window must include 2026. QUANTGEN's 504-close window ending 2026-09 already does. A 2015–24 fit understates 2026 tails: KOSPI rv21 was above 30% on 88% of 2026 days, with mean 56.5% and max 102.6%, vs 8.6–14.5% of days in 2024–25. (2) **One volatility estimator family serves sizing: SMA20 (R-06).** The Quant Lab's GARCH(1,1)-t fan keeps its own B5 result label (REJECT on SPY). **No model replaces the sizing estimator unless it passes B5** (`docs/vol_backtest.py`, rolling-origin 5% VaR exceedance within ±2 binomial SE over ≥ 200 origins, PIT uniformity; backlog BL-G01). EWMA ≈ GARCH for KOSPI. GJR is optional for the US and only through B5. No HAR or ML vol models until intraday realised variance exists. (3) Scenario library, all seeded and reproducible: (a) the 2026 vs 2022 oil-shock replays at +20 days (2026: KOSPI −15.5%, USD/KRW +5.2%, 10y real +32 bp; 2022: KOSPI +0.4%, USD/KRW +2.1%, 10y real −4 bp); (b) the Jul-2026 KOSPI leverage unwind (−38.6% in 27 sessions); (c) Aug-2024 carry unwind; (d) Apr-2025 tariffs; (e) SEP Table-2 short-rate error bands (±1.4 pp at 1 year, Dec-2023 SEP) as rate-path uncertainty. Rate paths go through `core/ficc/ratesim` (Vasicek / CIR / Hull-White), not through a log-return price model (architecture review C3). Every scenario names its Brent series. (4) Scenario outputs are descriptive. They never set a weight. |
| **Evidence** | N-48, N-44; architecture review B5, C3; public page "the lab grades itself" |

### R-17 Planned sleeves — DEFERRED (specified now; build when the sleeve exists)

**FX sleeve (N-52).** QUANTGEN's Rates & FX page currently withholds FX momentum and dollar carry as signals. Any FX sleeve is a new card set at FX cost (10 bp per side).
- **Never forecast FX direction from rate differentials.** USD/JPY Fama b was −1.92 (1991–2007) and 0.11 with R² 0.000 (2008–26). USD/KRW monthly R² was 0.022.
- **Carry is a crash-prone premium.** Size it small. De-risk it on:
  - a USD/JPY trend break (0× below the 50-day average reduced the 10 Jul → 5 Aug 2024 loss from −10.6% to −2.9%, but ΔSR was −0.07 in 2015–26: a cost in calm years). That 0× belongs to a sleeve-level risk limit, not to an overlay (P2).
  - JPY rv21 in its top quintile → 0.5× (+0.06 in 2008–26; +0.09 in 2015–26).
  - **Not** on VIX, which read 12.85–16.36 until 31 Jul 2024.
- **Confirmed intervention:**
  - FX momentum × 0.5 for 20 sessions, and simulated stops × 1.5;
  - no bet on a re-breach;
  - USD/JPY 160–164 is the hazard zone (flag at the prior intervention maximum − 1.5%).
- **Long-KRW carry:** skew −2.38, worst quarter −36.9% (Q4-1997); the current rate differential is −0.75 pp (negative carry).

**Crypto sleeve (N-54).** QUANTGEN's crypto desk already has a trend rule that passed the gate: card C3 on KRW-BTC, plus the BTC-USD card. The macro overlay adds only:
- an own risk bucket: BTC's own vol target as a CARD-P plus a hard gross cap (risk layer);
- the BTC–equity β, estimated on rolling data; the weekly BTC–NDX correlation was 0.09, 0.50 and 0.22 across the three sub-periods;
- no net-liquidity or M2 input (§10).

### R-18 Policy-break and scale-break protocol — BUILD NOW · INVARIANT (governance)

**Policy breaks.** After a declared policy-framework break, every **macro-conditioned** multiplier is shrunk to 1.0 and its card is re-gated as a new revision. Such breaks include:
- a central bank changing its reaction-function framework, or ending yield-curve control;
- a sign flip in the policy direction (Fed: −175 bp, then +25 bp in Sep-2026; BoK: −100 bp, then +50 bp).

"A new chair is not a new rule": policy-direction states must allow sign flips. In v1.1 no macro-conditioned multiplier is in the recommended book, so this applies to S1 and S2 if they ever pass. Evidence: N-50; PC-P-29.

**Scale breaks.** If a market's realised vol stays above 2× its trailing 3-year median for 60 sessions, percentile thresholds for that market re-anchor. Re-anchoring is logged as a card revision, with no lockout. Percentiles alone do not cure a scale break: a trailing 3-year p90 of KOSPI rv21 was still exceeded on 72% of 2026 days. The display-label quartiles (R-06) use a trailing 756-session window and re-anchor automatically. They are display-only.

---

## 6. JSON artifact schemas (written by `core/ficc/macro` builders; schemas next to them, proposed)

Common conventions:
- JSON Schema draft 2020-12.
- All times are ISO-8601 UTC with a "Z" suffix.
- Every artifact carries `schema`, `schema_version` ("1.1"), `generated_at_utc`, `git_hash`, `config_hash` (hash of the rules-store state), `data_snapshot_id` and `read_only: true`.
- `additionalProperties: false`, except inside `extras`.
- No artifact contains an order instruction. Weights are targets for the simulated order book only.

### 6.1 `macro_state` (one per market per decision time)

```json
{
  "$id": "quantgen/macro_state.v1.1",
  "type": "object",
  "required": ["schema","schema_version","read_only","generated_at_utc","decision_utc","effective_session","market","git_hash","config_hash","data_snapshot_id","inputs","vol","flags","fail_closed","alerts"],
  "properties": {
    "schema": {"const": "quantgen.macro_state"}, "schema_version": {"const": "1.1"}, "read_only": {"const": true},
    "generated_at_utc": {"type": "string", "format": "date-time"},
    "decision_utc": {"type": "string", "format": "date-time", "description": "official close of the decided session"},
    "effective_session": {"type": "string", "description": "the session whose return the decision earns (t+1)"},
    "market": {"enum": ["KR","US","JP","EU","TW","CN","IN","EM","CRYPTO","FX"]},
    "git_hash": {"type": "string"}, "config_hash": {"type": "string"}, "data_snapshot_id": {"type": "string"},
    "inputs": {"type": "array", "items": {"$ref": "#/$defs/input"}},
    "vol": {"type": "object", "properties": {
        "estimator": {"enum": ["sma20","ewma094","sma60","garch_t","gjr_t"]},
        "estimator_b5": {"enum": ["PASS","FAIL","NOT_RUN"]},
        "sigma_ann": {"type": "number", "minimum": 0},
        "target_ann": {"type": "number", "exclusiveMinimum": 0}, "vt_weight_next": {"type": "number", "minimum": 0, "maximum": 1},
        "display_label": {"enum": ["calm","normal","elevated","stressed"]},
        "label_method": {"const": "trailing756_quartiles_causal_filtered"},
        "alt_sigma_logged": {"type": ["number","null"]}},
      "required": ["estimator","estimator_b5","sigma_ann","target_ann","vt_weight_next","display_label","label_method"]},
    "flags": {"type": "object", "properties": {
        "vix_ge_vix3m": {"type": "boolean"}, "dm_bear_state": {"type": "boolean"},
        "krw_leg_fwdsim": {"type": ["boolean","null"]}, "rates_leg_fwdsim": {"type": ["boolean","null"]},
        "hedge_credit_off": {"type": "boolean"}, "hedge_failure": {"type": "boolean"}, "classic_risk_off": {"type": "boolean"},
        "kr_open_gap_event": {"type": "boolean"}, "ladder_step": {"enum": ["none","-8","-12","-15"]},
        "engine_state": {"enum": ["DISARMED","ARMED","HALTED"]}}},
    "fail_closed": {"type": "boolean"},
    "alerts": {"type": "array", "items": {"type": "string"}},
    "extras": {"type": "object"}
  },
  "$defs": {"input": {"type": "object", "required": ["name","series_id","source","obs_date","value","available_at_utc","timing","status"],
    "properties": {"name": {"type": "string"}, "series_id": {"type": "string"}, "source": {"type": "string"},
      "obs_date": {"type": "string", "format": "date"}, "value": {"type": ["number","null"]},
      "available_at_utc": {"type": "string", "format": "date-time"}, "retrieved_at_utc": {"type": "string", "format": "date-time"},
      "vintage": {"type": ["string","null"]}, "timing": {"enum": ["live","publication","value_proxy"]},
      "status": {"enum": ["ok","stale","missing","synthetic_rejected","warmup"]}}}}
}
```

Example: KR, decided at the official close of 2 Oct 2026, earning in the next KRX session.

```json
{"schema":"quantgen.macro_state","schema_version":"1.1","read_only":true,"generated_at_utc":"2026-10-02T06:41:07Z","decision_utc":"2026-10-02T06:30:00Z",
 "effective_session":"KRX next session after 2026-10-02","market":"KR","git_hash":"<sha>","config_hash":"<sha>","data_snapshot_id":"2026-10-02T06:30Z",
 "inputs":[{"name":"KOSPI official close","series_id":"KOSPI","source":"KIS","obs_date":"2026-10-02","value":6943.66,"available_at_utc":"2026-10-02T06:30:00Z","timing":"live","vintage":null,"status":"ok"},
           {"name":"USD/KRW fixing (FORWARD-SIM S1 input)","series_id":"USDKRW_KIS_FIX","source":"KIS","obs_date":"2026-10-02","value":null,"available_at_utc":"2026-10-02T06:30:00Z","timing":"live","vintage":null,"status":"ok"},
           {"name":"USD/KRW DEXKOUS (history reference)","series_id":"DEXKOUS","source":"FRED H.10","obs_date":"2026-09-25","value":1356.51,"available_at_utc":"2026-09-28T20:15:00Z","timing":"publication","vintage":null,"status":"ok"}],
 "vol":{"estimator":"sma20","estimator_b5":"PASS","sigma_ann":0.2893,"target_ann":0.20,"vt_weight_next":0.691,"display_label":"elevated","label_method":"trailing756_quartiles_causal_filtered","alt_sigma_logged":null},
 "flags":{"vix_ge_vix3m":false,"dm_bear_state":false,"krw_leg_fwdsim":false,"rates_leg_fwdsim":null,"hedge_credit_off":true,"hedge_failure":false,"classic_risk_off":false,"kr_open_gap_event":false,"ladder_step":"none","engine_state":"ARMED"},
 "fail_closed":false,"alerts":[]}
```

**Notes on the example.**
- **Decision time.** The decision is stamped at the official KRX close (06:30Z), and the workflow ran at 06:41Z. Every input has `available_at_utc ≤ decision_utc`. A record stamped after 06:30Z must be rejected by the lag audit (T-LAG-01). v1.0's 15:15 KST close proxy is removed (§4.1).
- **USD/KRW fixing value.** It is `null` in this example only because the research snapshot holds no KIS data.
- **Rates flag.** `rates_leg_fwdsim` is `null` because S2 applies to US exposure only.
- **H.10 timestamp.** The DEXKOUS row carries the H.10 weekly publication time: Monday 28 Sep 2026, 16:15 ET = 20:15Z. It is a reference row; S1 reads the KIS fixing.
- **Data snapshot.** `vt_weight_next` 0.691 and `display_label` "elevated" are the R4/R4b values computed from the 2 Oct close.

### 6.2 `overlay_decision` (one per market × family per decision)

```json
{
  "$id": "quantgen/overlay_decision.v1.1", "type": "object",
  "required": ["schema","schema_version","read_only","decision_utc","effective_session","market","family","exposure_basis","vol_scale","vol_scale_recommended_book","multipliers","overlay_product","overlay_floor","overlay_cap","overlay_applied_spec_book","overlay_applied_recommended_book","forward_sim","reasons","inputs","rule_versions","git_hash"],
  "properties": {
    "schema": {"const": "quantgen.overlay_decision"}, "schema_version": {"const": "1.1"}, "read_only": {"const": true},
    "decision_utc": {"type": "string", "format": "date-time"}, "effective_session": {"type": "string"},
    "market": {"type": "string"}, "family": {"enum": ["momentum","reversal","flow","quality","ts_trend","market_gross"]},
    "exposure_basis": {"enum": ["active","total"]},
    "vol_scale": {"type": "number", "minimum": 0, "maximum": 1, "description": "specification book"},
    "vol_scale_recommended_book": {"type": "number", "minimum": 0, "maximum": 1, "description": "= vol_scale if its card is PASS, else 1.0"},
    "vol_scale_card": {"$ref": "#/$defs/card"},
    "multipliers": {"type": "array", "items": {"type": "object", "required": ["rule_id","value","exposure_basis","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                      "exposure_basis": {"enum": ["active","total"]}, "card": {"$ref": "#/$defs/card"}}}},
    "overlay_product": {"type": "number", "minimum": 0, "maximum": 1},
    "overlay_floor": {"const": 0.5}, "overlay_cap": {"const": 1.0},
    "overlay_applied_spec_book": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "overlay_applied_recommended_book": {"type": "number", "minimum": 0.5, "maximum": 1.0},
    "forward_sim": {"type": "array", "items": {"type": "object", "required": ["rule_id","value","card"],
       "properties": {"rule_id": {"type": "string"}, "value": {"type": "number", "minimum": 0.5, "maximum": 1.0},
                      "would_apply_to": {"type": "string"}, "card": {"$ref": "#/$defs/card"}}}},
    "reasons": {"type": "array", "items": {"type": "string"}},
    "inputs": {"type": "array", "items": {"type": "object"}},
    "rule_versions": {"type": "object"}, "git_hash": {"type": "string"}
  },
  "$defs": {"card": {"type": "object", "required": ["card_id","class","verdict","displayed_as","results_md5"],
     "properties": {"card_id": {"type": "string"}, "class": {"enum": ["CARD-O","CARD-P"]},
       "verdict": {"enum": ["PASS","REVISE","REJECT","INSUFFICIENT_DATA","NOT_RUN"]},
       "displayed_as": {"enum": ["recommendation","descriptive"]}, "results_md5": {"type": ["string","null"]}}}}
}
```

Rule: `displayed_as = "recommendation"` iff `verdict = "PASS"`. `vol_scale_recommended_book` and `overlay_applied_recommended_book` use only the factors whose card is PASS (others enter as 1.0).

Example, before the first card run. Every verdict is `NOT_RUN`, so the recommended book carries no overlay factor; the risk-layer invariants still apply:

```json
{"schema":"quantgen.overlay_decision","schema_version":"1.1","read_only":true,"decision_utc":"2026-10-01T20:00:00Z","effective_session":"NYSE 2026-10-02",
 "market":"US","family":"momentum","exposure_basis":"active","vol_scale":0.50,"vol_scale_recommended_book":1.0,
 "vol_scale_card":{"card_id":"MACRO-R03-US-MOM","class":"CARD-O","verdict":"NOT_RUN","displayed_as":"descriptive","results_md5":null},
 "multipliers":[{"rule_id":"R-04-DM","value":1.0,"exposure_basis":"active",
                 "card":{"card_id":"MACRO-R04-US-DM","class":"CARD-O","verdict":"NOT_RUN","displayed_as":"descriptive","results_md5":null}}],
 "overlay_product":1.0,"overlay_floor":0.5,"overlay_cap":1.0,"overlay_applied_spec_book":1.0,"overlay_applied_recommended_book":1.0,
 "forward_sim":[],
 "reasons":["DM: 24m market return +39.7% >= 0 -> 1.0","VS: sigma126 23.9% -> min(1, 0.12/0.239)=0.50"],
 "inputs":[{"name":"Mom sigma126","value":0.239,"obs_date":"2026-08-31","available_at_utc":"2026-09-30T00:00:00Z"}],
 "rule_versions":{"R-03":"1.1","R-04":"1.1"},"git_hash":"<sha>"}
```

The values are illustrative and come from the research snapshot, which uses the French Mom file through Aug-2026. In production, σ126 is computed on QUANTGEN's own sleeve returns through the close of t (an `obs_date` a month old would be stale under §4.1 and would fail closed). `NOT_RUN` turns into the card's verdict after the first `docs/macro_overlay_study.py` run.

**v1.2 correction.** `forward_sim` is empty here because S2 excludes momentum (R-12 scope; T-BASIS-01). The S2 entry belongs in the US record with `family: "market_gross"`, `exposure_basis: "total"`, e.g. `{"rule_id":"S2-RATES","value":0.5,"would_apply_to":"US duration-sensitive gross","card":{"card_id":"MACRO-R12-US-RATES",...}}`, with the reason "S2: strict-H.15 flag on from the close of 2026-09-25 (data date 2026-09-23); forward book only".

### 6.3 `event_calendar` (one entry per event; `core/calendars`)

```json
{"$id":"quantgen/event.v1.1","type":"object",
 "required":["event_id","type","region","scheduled_utc","status","source","windows"],
 "properties":{"event_id":{"type":"string"},
  "type":{"enum":["FOMC","US_CPI","US_NFP","US_OTHER_RELEASE","BOK","BOJ","ECB","KOSPI200_EXPIRY","INDEX_CHANGE","HYPERSCALER_EARNINGS","OIL_GEO","FX_INTERVENTION","OTHER"]},
  "region":{"type":"string"},"scheduled_utc":{"type":"string","format":"date-time"},
  "status":{"enum":["scheduled","released","cancelled","delayed"]},"released_utc":{"type":["string","null"],"format":"date-time"},
  "source":{"type":"string"},
  "windows":{"type":"array","items":{"type":"object","required":["market","action","start_utc","end_utc"],
     "properties":{"market":{"type":"string"},"action":{"enum":["evaluator_block_new_intraday_entries","evaluator_block_new_futures_entries","annotate_only"]},
                   "start_utc":{"type":"string","format":"date-time"},"end_utc":{"type":"string","format":"date-time"},
                   "resume_condition":{"type":["string","null"]}}}},
  "kr_open_gap_session":{"type":["string","null"],"format":"date"},
  "scenario_tag":{"type":["string","null"]},"notes":{"type":"string"}}}
```

Example: FOMC on 28 Oct 2026, 14:00 EDT = 18:00 UTC = 03:00 KST on 29 Oct.

```json
{"event_id":"FOMC-2026-10-28","type":"FOMC","region":"US","scheduled_utc":"2026-10-28T18:00:00Z","status":"scheduled","released_utc":null,
 "source":"federalreserve.gov FOMC calendar",
 "windows":[{"market":"US","action":"evaluator_block_new_intraday_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":"VIX < pre-14:00 ET level else 19:30Z"},
            {"market":"KR_FUT_NIGHT","action":"evaluator_block_new_futures_entries","start_utc":"2026-10-28T17:45:00Z","end_utc":"2026-10-28T19:00:00Z","resume_condition":null}],
 "kr_open_gap_session":"2026-10-29","scenario_tag":null,"notes":"KR opening-gap event night"}
```

### 6.4 `context_log` (daily; `core/ficc/macro`)

```json
{"$id":"quantgen/context_log.v1.1","type":"object","required":["schema","schema_version","read_only","as_of_utc","items","acts"],
 "properties":{"schema":{"const":"quantgen.context_log"},"schema_version":{"const":"1.1"},"read_only":{"const":true},
  "as_of_utc":{"type":"string","format":"date-time"},
  "acts":{"const":false},
  "items":{"type":"array","items":{"type":"object","required":["name","value","obs_date","available_at_utc","source"],
     "properties":{"name":{"type":"string"},"value":{"type":["number","string","null"]},"obs_date":{"type":"string"},
        "available_at_utc":{"type":"string","format":"date-time"},"source":{"type":"string"},
        "zscore_causal":{"type":["number","null"]},"zscore_window":{"type":["string","null"]},
        "from_sheet":{"type":"boolean","description":"true for the existing 18-indicator sheet items"},
        "range":{"type":["array","null"],"items":{"type":"number"}},"note":{"type":"string"}}}}}}
```

Example items:
- `{"name":"Taylor residual range (pp)","value":null,"range":[-2.3,-0.4],"obs_date":"2026-08","source":"FRED PCEPILFE/UNRATE/NROU/GDPPOT; EFFR 3.875 mid","note":"never thresholded"}`
- `{"name":"Recession probit (E-T coefficients)","value":0.095,...}`

### 6.5 `model_card.macro` (one per overlay card per revision; replaces v1.0's `trial_registry`)

QUANTGEN's cards already hold a hypothesis, a rule, a data span, pre-registered costs, a seed, every test line, the decision and an md5 of the results (public page). This schema is a **proposed** superset for macro overlay cards. Map it onto the app's actual card format; do not run a parallel registry.

```json
{"$id":"quantgen/model_card.macro.v1.1","type":"object",
 "required":["card_id","rule_id","revision","class","tier","created_utc","header_md5","hypothesis","claim","rule","parameters","searched_parameters",
             "instrument_book","costs_per_side","cost_stress","timing","data_span","seed","benchmarks","tests","verdict","first_failed_check",
             "permitted_fix","global_trial_count","results_md5"],
 "properties":{"card_id":{"type":"string"},"rule_id":{"type":"string"},"revision":{"type":"integer","minimum":1},
  "class":{"enum":["CARD-O","CARD-P"]},"tier":{"enum":["A","A-provisional","B","C"]},
  "created_utc":{"type":"string","format":"date-time"},"header_md5":{"type":"string","description":"md5 of the header, committed before the study run"},
  "hypothesis":{"type":"string"},"claim":{"enum":["outperformance","protection"]},
  "rule":{"type":"string"},"parameters":{"type":"object"},"searched_parameters":{"type":"array","items":{"type":"string"}},
  "instrument_book":{"type":"string","description":"e.g. KRX ETF line / KRX stock book / US shares via KIS"},
  "costs_per_side":{"type":"number"},"cost_stress":{"const":2.0},
  "timing":{"type":"object","properties":{"decision":{"const":"close_t_earn_t_plus_1"},"inputs":{"type":"object"}}},
  "data_span":{"type":"object"},"seed":{"type":"integer"},
  "benchmarks":{"type":"array","items":{"enum":["buy_and_hold","overlay_off","static_same_avg_exposure","ewma_derisk"]}},
  "tests":{"type":"object","description":"one entry per gate step (1-9) and per protective check (PC-1..PC-7): value, threshold, pass"},
  "episodes":{"type":"array"},"forward_record":{"type":["object","null"]},
  "verdict":{"enum":["PASS","REVISE","REJECT","INSUFFICIENT_DATA"]},
  "first_failed_check":{"type":["string","null"]},"permitted_fix":{"enum":[null,"widen_grid","lengthen_holding","extend_history"]},
  "lag_audit_violations":{"const":0},"global_trial_count":{"type":"integer","minimum":1},"results_md5":{"type":"string"}}}
```

---

## 7. Rules-store entries (`core/rules` JSON store; YAML shown for readability)

**Where things live.**
- `config.py` keeps what it already holds: credentials by family, `~/.nextgen/ficc_cache`, the trading directory for the rules JSON, and the skill environment. It gains the macro artifact directory and the decision-time constants (**proposed**).
- The overlay parameters below become **rule objects in the rules store**. The store's model is immutable and has no financial defaults, so every number below must be written explicitly. Validation enforces P2 and the exposure basis. The store's edit history is the revision log: an edit to an acting parameter is a new card revision (§8.4).
- Costs are **not** stored here. They are read from the gate's pre-registered table (P10).

```yaml
version: "1.2.0"                         # v1.2: adds estimator_gate.pit_p_min only
as_of: "2026-10-02"
read_only: true                          # no order path; nothing here can enable one
time:
  storage_tz: UTC
  decision: close_t_earn_t_plus_1        # QUANTGEN rule 02
  markets:
    KR:  {tz: Asia/Seoul,       session: ["09:00","15:30"], decision_utc: official_close, open_no_entry_minutes: 30}
    US:  {tz: America/New_York, session: ["09:30","16:00"], decision_utc: official_close}
  cross_tz_rule: "us_dated_D_usable_for_KR_close_K_iff_D_le_K_minus_1_and_available_at_le_close"
  publication_lags: {H15: {posted: "D+1 16:15 ET", us_close_decision_bdays: 2}, H10: {posted: "following Monday 16:15 ET"},
                     VIXCLS: {official_close: "16:15 ET", us_close_decision_bdays: 1}}
  max_staleness: {daily_market: 1, weekly: 3, monthly_release_cycles: 1}   # trading days / days / cycles; default, judgment
data:
  fail_closed_on_missing_acting_input: true
  synthetic_for_acting_inputs: forbidden # 'auto' provider degrade -> MissingInput
  interpolate: false
  monthly_lag_method: calendar           # never positional
  vintages: alfred                       # for revised macro series
  named_series_required: true
  brent_series: {spot: DCOILBRENTEU, futures: BZ=F}
  usdkrw: {production: KIS_USDKRW_FIXING, history: ECOS_1530_CLOSE, history_fallback: DEXKOUS, history_fallback_timing: H10_publication}
  us10y: {production: KIS_US10Y_QUOTE, history: DGS10, history_strict_lag_bdays: 2, live_proxy_history: "^TNX"}
overlay:
  floor: 0.5
  cap: 1.0
  combine: product_then_clip             # default, judgment (§3.3)
  zero_only_in: [risk_layer, engine_HALTED]
  books: [recommended_PASS_only, specification, forward_sim_per_leg]
vol_target:                              # R-06 (cap 1.0, no floor)
  KR: {estimator: sma, window: 20, target_ann: 0.20, cap: 1.0, exposure_basis: total, instrument_book: declare_on_card}
  US: {estimator: sma, window: 20, target_ann: 0.15, cap: 1.0, exposure_basis: total, instrument_book: us_shares_via_kis}
  other_markets: {estimator: sma, window: 20, target_ann: null, cap: 1.0}   # pre-register per market on its card
  estimator_gate: {name: B5, requires: [var95_exceedance_within_2se_over_200_origins, pit_uniformity], challenger: ewma_0.94,
                   pit_test: chi2_10_bins, pit_p_min: 0.01,   # v1.2: the app's own PIT cut-off (public page) = R4b's declared rule
                   garch_t_or_gjr: only_after_B5_pass}
  annualisation_days: 252
  display_label: {method: trailing_756_quartiles, values: [calm, normal, elevated, stressed], filtered_only: true, acts: false}
  logged_alt_estimators: [max_sma20_implied, asymmetric_slow_cut_fast_restore]   # BL-C04
families:
  momentum:
    own_vol_scale: {window: 126, target_ann: 0.12, cap: 1.0, floor: 0.0, min_obs: 126, exposure_basis: active,
                    fallback_target: expanding_median_sigma126}   # fallback only if no unit-gross L/S series
    dm_gate: {market_return_months: 24, market_vol_window: 126, vol_quantile: 0.6667, quantile_min_obs: 252,
              multiplier: 0.5, exposure_basis: active, tier: A-provisional}
  reversal: {overlay: fixed_1.0, intraday_leg: false}
  quality:  {overlay: fixed_1.0}
  flow:     {overlay: fixed_1.0}
  ts_trend: {signal: sign_12_1, rebalance: monthly, vol_window_months: 12, target_ann: 0.15, cap: 1.0, overlay_exempt: true}  # target: default, judgment
weights_prior: see_R-15                  # per-market x per-family table (0-3 scale)
prior_haircuts: {value: 0.49, momentum: 0.23, carry: 0.25, defensive: 0.0, multifactor: 0.18}   # one-sided (prof); gate haircut 0.6 printed too
risk_layer:                              # core/quant/risk + core/engine
  korea_caps: {pair_trigger_share_of_kospi: 0.45, pair_max_share_of_long_book: 0.35,
               semis_max_share_of_long_book: 0.50,    # default, judgment — pre-register
               single_name_max_nav: 0.05}
  drawdown_ladder: [{dd: -0.08, action: risk_layer_gross_x0.5}, {dd: -0.12, action: evaluator_block_new_entries_overlay_0.5},
                    {dd: -0.15, action: engine_HALTED, rearm_refused_sessions: 10}]
  halted_triggers: [ladder_-15, risk_limit_breach, lag_audit_violation, artifact_schema_failure, acting_input_stale_gt_1_decision, feed_heartbeat_loss_60s]
  korea_covariance_extra: [SHANGHAI, HSI, TAIEX, NIKKEI]
  hedge_state: {core_pce_threshold: 3.0, corr_window: 63, corr_threshold: 0.0,
                hedge_failure_daily: {equity_ret_lt: -0.015, usd_ret_lt: 0.0},
                hedge_failure_weekly: {equity_ret_lt: -0.02, usd_ret_lt: 0.0}}
entry_blocks:                            # core/engine/evaluator -> BLOCKED(rule_id)
  vix_ts: {condition: "VIXCLS >= VXVCLS", threshold: 1.0, tuned: false,
           blocks: [new_xs_momentum_entries, new_intraday_entries], from: "first decision after the 16:15 ET VIX close"}
events:                                  # core/calendars; evaluator blocks on simulated entries only
  us_cpi_nfp: {block_new_intraday_entries_et: ["08:25","09:45"], resume_et: "10:00"}
  us_leaky_releases_pre_minutes: 30
  fomc: {block_new_intraday_entries_et: ["13:45","15:00"], resume_rule: "VIX<pre14 else 15:30", pre_fomc_long: false}
  bok: {kospi200_futures_block_kst: [["09:45","10:15"],["11:00","11:45"]], equity_daily_change: none}
  kr_open: {block_new_intraday_entries_kst: ["09:00","09:30"]}
  kr_open_gap_event_types: [US_CPI, US_NFP, FOMC, HYPERSCALER_EARNINGS]
  sidecar_cb: {block_new_entries_minutes_after_cb_reopen: 30, quotes_during_halt: indicative, gross_cut: false}
  daily_book_blackouts: false
forward_sim:                             # v1.0 'shadow'
  S1_krw: {lookback_obs: 20, threshold_dlog: 0.03, multiplier: 0.75, target: KR_market_gross, one_sided: true, switch_budget_per_year: 11.1,
           card_class: CARD-P, tier: B}
  S2_rates: {lookback_obs: 20, threshold_pp: 0.40, multiplier: 0.5, target: US_duration_sensitive_gross,
             excludes: [momentum, ls_factor_sleeves, KR], switch_budget_per_year: 7.2, card_class: CARD-P, tier: A}
context_log:
  probit: {alpha: -0.6045, beta: -0.7374, spread: "GS10 - TB3MS (bond-equivalent), monthly"}
  taylor_family: {r_star: [0.5, 1.0, 2.0], gap: [okun_2x, cbo], a: [0.5, 1.0], pi: core_pce_yoy, pi_star: 2.0}
  existing_sheet: {all_items_context_unless_acting: true, zscores: causal_display_only, regime_read: display_only_filtered}
gate:                                    # the existing nine-step gate; macro additions only
  card_classes: [CARD-O, CARD-P]
  protective: {ni_margin_sharpe: 0.10, ni_p_max: 0.10, dmdd_min_pp: 3.0, tail_exposure_ratio_max: 0.90, tail_quantile: 0.05,
               min_positive_episodes: 3, max_episode_share: 0.5, min_episodes_in_sample: 5, years_positive_min: 0.60,
               plateau_share_min: 0.5, block: "max(10, PW(d), PW(d^2))", resamples: 2000, seed: 11}
  tiers: {A: {min_onsets_declustered: 30, decluster_gap: own_lookback, min_stress_episodes_in_sample: 3, min_oos_episodes: 1},
          A_provisional: {criteria: published_replicated_3_regions_mechanism, holdout_noninferiority_regions: "2 of 3"},
          B: {bounds: [0.5, 1.0], external_params: true, verdict_from_backtest: INSUFFICIENT_DATA, min_forward_months: 12},
          C: {allowed: false}}
  parameter_budget_searched: 8
  multiplicity_reported: {z_preregistered: 2.7, z_bonferroni_120: 3.35, methods: [BHY, DSR]}
  pbo_min_configs: 10
  stress_report_window: ["2022-01-01", "2026-10-02"]      # reported, not a holdout
  locked_holdout_start: "2027-01-01"
  demotion: {outperf_off_beats_on_6m_nav: 0.02, outperf_sr_below_boot_p10_months: 12, protective_forward_dmdd_ge_0_and_dsr_lt: -0.10,
             switch_multiple: 2.0, unregistered_param_edit: demote, lag_audit_violation: demote}
  lockout_months_after_demotion: 6
  scale_reanchor: {vol_multiple_of_3y_median: 2.0, sessions: 60}
  costs: read_from_gate                  # KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10, futures 5, FX 10; x2 stress
reproducibility: {seed_study: 11, seed_research_bootstrap: 20261002, record: [git_hash, config_hash, data_snapshot_id, seed, results_md5]}
```

---

## 8. Governance: the nine-step gate, model cards and the protective class

v1.0 had its own falsification pipeline: tiers, a pre-registration file, a trial registry, a shadow book, promotion and kill. v1.1 removes that parallel process. **Every overlay rule that changes exposure is a QUANTGEN model card, decided by the existing gate.** The research's additional disciplines are kept only where the gate does not already contain them:
- the static same-exposure benchmark;
- Politis–White blocks;
- the episode table;
- tiers;
- forward records.

### 8.1 The gate (as QUANTGEN implements it)

| Step | Check | Fixed setting | Macro addition (v1.1) |
|---|---|---|---|
| 1 | Choose in the past, test in the future | Purged walk-forward 756 in-sample / 126 out-of-sample sessions; embargo = holding period | With zero searched parameters the walk-forward reduces to the full sample. The card states this. |
| 2 | The interval must clear zero | Lo (2002) Sharpe SE and a 90% block bootstrap, 2,000 resamples × 10-session blocks | Protective cards replace this step with PC-3 (non-inferiority, §8.7) and still print the book's own interval |
| 3 | Count every try | Deflated Sharpe ≥ 0.95; every revision adds to N | The global N includes every macro card revision |
| 4 | Not over-searched | PBO via CSCV: PBO ≤ 0.05, or the winner loses in ≤ 10% of splits; PBO > 0.2 with the winner losing = REJECT | Only when ≥ 10 configurations were tried; protective cards compute it on the ΔMDD objective |
| 5 | Beat the benchmark on the same days | Bootstrapped difference of Sharpe ratios, one-sided p ≤ 0.10 | CARD-O benchmark = the same book with the overlay off. Protective cards replace this step with PC-1, PC-2 and PC-4. |
| 6 | Survive twice the costs | Whole test rebuilt at 2× costs; Sharpe > 0; annual turnover printed. Losing money at 2× is a REJECT only when the interval includes zero, otherwise a REVISE. | Protective cards also require PC-1 and the PC-3 point estimate to hold at 2× |
| 7 | A plateau, not a peak | ≥ 50% of neighbouring configurations keep ≥ half the Sharpe; best not at the edge of an axis | Protective cards: half the ΔMDD improvement plus the PC-3 point estimate |
| 8 | Most years, not one lucky year | ≥ 60% of calendar years positive; top-year share printed | Protective cards also print the share of years in which the overlay lags the static book (the insurance premium), not gated |
| 9 | Then take 40% off | Expected live Sharpe = 60% of out-of-sample; reported, not gated | Protective cards also print 60% of ΔMDD |

**Verdicts.** PASS / REVISE / REJECT / INSUFFICIENT DATA, defined once in code.
- A REVISE names the first failed check and the only permitted fix: widen the grid, lengthen the holding period, or extend the history.
- Lowering a cost is never allowed. Every revision is logged on the card and counted as another trial.
- A REJECT stays on the record, with the same card and the same weight as a PASS.

### 8.2 Card classes

| Kind | Claim | Gate path | Examples |
|---|---|---|---|
| **CARD-O** | Outperformance of the overlay-on book vs the overlay-off book (same costed engine, same data) | Steps 1–9 unchanged | R-03, R-04, R-14 |
| **CARD-P** | Drawdown protection with Sharpe non-inferiority vs a static book with the same average exposure | §8.7 | R-06, R-08, R-11, R-12, crypto vol cap (R-17) |
| INVARIANT | None (a bound, a data rule, a risk limit, a risk-model assumption) | Not gated; its effect is reported on every card's books | R-01, R-02, R-07, R-09, R-18 |
| CONVENTION | None (delays or annotates simulated entries) | Not gated; logged and measured | R-05, R-10 |
| CONTEXT | None | Never acts | R-13 |

A card's class is part of its header and is fixed before the study run. Changing the claim after seeing results is a **new card**, counted as a trial.

### 8.3 Evidence tiers in gate terms

The tiers decide **which verdicts a backtest alone can produce**.

| Tier | Applies to | In gate terms |
|---|---|---|
| **A** | Daily price-state rules with ≥ 30 de-clustered onsets per market (an onset within the rule's own lookback of the previous onset is the same onset), or pooled under a rule declared on the card; ≥ 3 non-overlapping stress episodes in sample and ≥ 1 out of sample. Continuous rules qualify with ≥ 5 pre-registered drawdown episodes in the sample (§8.6). | The backtest can reach any verdict. Multiplicity is printed on the card: z ≥ 2.7 if ≤ 8 pre-registered cells, else z ≥ 3.35 (Bonferroni-120), or BHY / DSR. |
| **A-provisional** | Published, replicated in ≥ 3 regions, with an ex-ante mechanism (e.g., R-04) | Own-market sufficiency is still printed. If it fails, the card is INSUFFICIENT DATA until a pre-registered out-of-region holdout is run (backlog BL-C01, BL-C12). Non-inferiority (ΔSR ≥ 0, one-sided 90%) in ≥ 2 of 3 held-out regions with no episode > 50% then counts as the card's step-5 / PC evidence. |
| **B** | Bounded de-risk rules with < 30 onsets and parameters taken from external or pooled long-history evidence (e.g., S1 under strict timing) | **The verdict from the backtest is INSUFFICIENT DATA by construction.** The card runs as FORWARD-SIM and is re-gated after ≥ 12 months of forward simulated running, or ≥ 2 slow-flag episodes, whichever is later. The forward record is appended to the evaluation as a revision. |
| **C** | Anything that raises risk (a multiplier > 1.0) | REJECT by construction. The rules store refuses the rule. |

### 8.4 Pre-registration = the card header

- **The header.** It is written before the study run: hypothesis, claim, class, tier, rule, parameters, searched parameters, instrument book and costs, timing of every input, data span, seed, benchmarks, episodes and decision rule. Its md5 (`header_md5`) is stored. The header is immutable once committed.
- **Revisions.**
  - Any change is a new revision, including a threshold, window, multiplier, timing, universe, instrument book, class or the forward-record append.
  - Each revision adds to the global trial count N, which feeds the deflated Sharpe ratio and BHY.
  - Edits to an acting parameter in the rules store without a revision demote the card (§8.8).
- **Expect the grid median, not the best cell.** For the rates leg the grid median is ≈ +0.01, not +0.04.
- **Parameter budget.** All macro cards together may have at most **8 searched parameters**. Conventions declared before any backtest do not count. If parameters must be cut, cut absolute Korea flags and credit-exit legs first.
- **Example header** (S1, revision 1):

```yaml
card_id: MACRO-R11-KR-KRW
rule_id: S1-KRW
revision: 1
class: CARD-P          # claim: protection, not outperformance
tier: B
created_utc: 2026-10-05T00:00:00Z
author: GEON
hypothesis: "USD/KRW 20d dlog > +3% marks sudden-stop states; de-risking Korea gross to 0.75x reduces drawdown vs a same-exposure static book without Sharpe loss"
mechanism: "sudden-stop channel; KRW weakening on 79% (2020) / 87% (2021-22) of KOSPI high-vol days"
inputs: [{series: USDKRW_KIS_FIX, timing: live, available_at_rule: "<= KRX close"}, {series: ECOS_1530_CLOSE, timing: live, use: history}]
formula: "flag = ln(FX_t/FX_{t-20}) > 0.03 ; mult = 0.75 if flag else 1.0 ; decided at the KRX close of t, earning from t+1"
parameters: {lookback: 20, threshold: 0.03, multiplier: 0.75}
searched_parameters: []          # none searched; all from prior evidence
instrument_book: "KRX ETF line (3 bp per side)"   # declared before the run; the KRX stock book (35 bp) is a separate card
costs: {per_side: read_from_gate, stress: 2.0}
exposure_basis: total
markets: [KR]
benchmarks: [buy_and_hold, overlay_off, static_same_avg_exposure, ewma_derisk]
protective_checks: "§8.7 PC-1..PC-7, thresholds as declared there"
samples: {design: "2016-01..2024-12", stress_report: "2022-01..2026-10", forward: "header commit + 12m"}
episodes: [2018Q4, 2020, 2022, 2024-08, 2024-12, 2025-04, 2026-03, 2026-07]
seed: 11
neighbours_tried: ["0.5x (R2-E3)", "+1 session lag", "Yahoo timing", "strict H.10 (R4b)"]
trial_count_at_registration: <int>
```

### 8.5 Benchmarks, statistics and costs

**Benchmarks, always all four:**
1. buy-and-hold;
2. the overlay-off book: the same costed engine, the same data, the rule off;
3. a static book with the overlay's **average** exposure (overlay-off × mean multiplier, constant);
4. EWMA de-risk: the market vol target with EWMA(0.94), the same target and cap 1.0.

**Primary metrics for protective cards:** ΔMDD vs (3), tail-exposure ratio, time under water, worst-day coverage, re-entry lag and CVaR.
**Primary metric for outperformance cards:** paired ΔSR vs (2).

**Bootstrap.**
- The gate's circular block bootstrap: 2,000 resamples, seed 11.
- For macro cards the block length is the **longer** of 10 sessions and the Politis–White automatic length computed on dₜ and dₜ² (Politis & White 2004; Patton, Politis & White 2009).
- In this research the Politis–White lengths were 14–16 days on dₜ and 214–245 days on dₜ². The 240-day blocks lowered the D&M z-statistic from 2.01 to 1.80. R4b's macro cards used 25–251-session blocks.
- Report the 90% interval and the share of resamples in which the rule beats its comparator.

**Sharpe statistics.**
- Deflated Sharpe (Bailey & López de Prado 2014) with the global N.
- PSR vs the benchmark.
- PBO (CSCV) whenever ≥ 10 configurations were tried.

**Costs (P10).**
- **Rate and turnover.** Turnover is |Δw| per day, charged on the day the new weight earns. Long/short sleeves are charged on both legs. Buy-and-hold and constant-weight static books carry no cost.
- **Stress run.** Every card also runs at 2× costs.
- **Annual turnover per rule (R4b):**

  | Rule | Turnover a year | Cost drag a year |
  |---|---|---|
  | KOSPI VT20 | 1.50 | 0.05% at 3 bp; 0.53% at 35 bp |
  | US VT15 | 2.52 | 1.26% at 50 bp |
  | KRW leg | 2.51 on value timing; 1.12 on strict H.10 | — |
  | Rates leg | 3.60 | 1.80% at 50 bp |
  | Momentum vol scale | 0.85 on both legs | — |

**Estimator gate.** A vol-target card may reach PASS only while its estimator passes B5 (§5 R-06; backlog BL-G01). If the estimator fails B5, the card's verdict is capped at REVISE, and the only permitted fix is "lengthen the holding period" (a slower or banded estimator, registered as a new revision).

**Expectation setting.**
- SE(ΔSR) is ≈ 0.034 for the US over 36 years and 0.052 for KOSPI over 11 years.
- A +0.05 Sharpe effect needs 33–44 years of data to detect.
- The base rate for a de-risk overlay is 0.00 to +0.10 Sharpe and 3–6 points of max drawdown.

### 8.6 Episode table and leave-one-crisis-out

Every card reports returns per episode, grouped by shock type, using these windows. They are fixed; do not tune them.

| Episode | Window (start → end, returns after the start close) | Shock type | Drawdown episode (PC-4)? |
|---|---|---|---|
| GFC | 2008-09-01 → 2009-03-09 | credit recession | yes |
| 2009 rebound | 2009-03-09 → 2009-06-30 | V-rebound (momentum crash) | no (cost episode) |
| 2011 | 2011-07-22 → 2011-10-03 | policy / sovereign | yes |
| 2015–16 | 2015-08-10 → 2016-02-11 | China / EM / oil | yes |
| 2018Q4 | 2018-09-20 → 2018-12-24 | rates / policy | yes |
| 2020 crash | 2020-02-19 → 2020-03-23 (KOSPI → 2020-03-19) | pandemic | yes |
| 2020 rebound | 2020-03-23 → 2020-06-08 (KOSPI from 2020-03-19) | V-rebound | no (cost episode) |
| 2022 | 2022-01-03 → 2022-10-12 (KOSPI → 2022-09-30) | inflation tightening | yes |
| Aug-2024 | US 2024-07-16 → 2024-08-05; KOSPI 2024-07-31 → 2024-08-09 | carry / leverage unwind | yes |
| Dec-2024 (KR) | 2024-12-03 → 2024-12-09 | domestic political | yes |
| Apr-2025 | US 2025-02-19 → 2025-04-08; KOSPI 2025-03-28 → 2025-04-09 | policy (tariffs) | yes |
| Mar-2026 | 2026-02-27 → 2026-03-31 | oil / geopolitical | yes |
| H1-2026 bull (KR) | 2026-01-02 → 2026-06-30 | bull-tax check | no (cost episode) |
| Jul-2026 | 2026-06-22 → 2026-07-30 | Korea leverage unwind / momentum crash | yes |
| Sep-2026 | 2026-08-31 → 2026-09-30 | rates (term premium) | yes |

- **Return dates behind the golden values (v1.2 note).** The convention above ("returns after the start close") holds for every US window and most KOSPI windows. Four KOSPI windows in R4/R4b include the start-date return: Aug-2024 uses returns dated 2024-07-31 → 2024-08-09; Apr-2025 2025-03-28 → 2025-04-09; Mar-2026 2026-02-27 → 2026-03-31; H1-2026 2026-01-02 → 2026-06-30 (the calendar half-year from the 2025 year-end close). Golden tests G-KR-03 and the PC-4 episode checks must use these return dates; under the strict "after the start close" reading, buy-and-hold would differ by more than the Level-1 tolerance (e.g., H1-2026 +96.7% instead of +101.1%; Aug-2024 −6.6% instead of −5.5%). The KOSPI 2015–16 window is truncated to 2016-01-04 → 2016-02-11 in the 2016–26 Korea sample, and R4b's Korea PC-4 set omits Sep-2026 (it was computed for the US only), which leaves the 9 Korea drawdown episodes quoted in §8.9. Whether Sep-2026 should count for Korea is for the card header to declare.
- **Leave-one-crisis-out by shock type:** credit recession, inflation tightening, policy shock, leverage unwind, oil/geopolitical, pandemic.
- **No single episode** may supply more than 50% of the benefit (PC-4).
- **2022–26 is a reported stress-test set, not a holdout.** It has been dissected episode by episode, and its SE(ΔSR) is ≈ 0.08–0.09.
- **The true out-of-sample tests** are the forward-simulated record from each card's header commit, and a locked holdout from 2027-01-01 onward for the inflation-conditional hypotheses.

### 8.7 The protective-overlay card class (CARD-P), pre-registered

**Why it exists.**
- **The research finding.** A de-risk overlay is worth 0.00 to +0.10 Sharpe. With SE(ΔSR) ≈ 0.034–0.052, detecting +0.05 needs 33–44 years. So a de-risk overlay cannot pass gate step 5 (benchmark difference, one-sided p ≤ 0.10) except by luck. That says nothing about whether it protects.
- **QUANTGEN's own precedent.** Card E1 (trend switch, US ETF sleeves) cut max drawdown to −15% vs −27%, yet was REJECTED: out-of-sample Sharpe 0.84 vs 0.95, p 0.75. The claim on the card was outperformance. The app keeps E1 on the ETF page as a descriptive sleeve "because the drawdown line is worth seeing".
- **What follows.** The macro overlays in this spec are the same kind of object. Their honest claim is protection. This class states that claim, and the checks that test it, **once and before any macro card is run**. It applies only to rules whose output never exceeds 1.0.

**Comparator S.** The overlay-off book scaled by the overlay's average exposure: constant weight, same days, no cost. Any constant de-gearing lowers drawdown, so protection must be shown against S, not against buy-and-hold.

**Checks.** The thresholds are fixed here. They were declared in `scripts/r4b_golden_net.py` before its first run.

| ID | Check | Pass condition | Replaces / extends gate step |
|---|---|---|---|
| **PC-1** | Drawdown reduction | MDD(rule) − MDD(S) ≥ **+3.0 pp** at 1× **and** at 2× costs, and MDD(rule) better than MDD(overlay-off). 3 pp is the low end of the documented 3–6 pp base rate. | step 5 |
| **PC-2** | Coverage of drawdown days | Tail-exposure ratio = mean multiplier on the worst 5% of overlay-off days ÷ mean multiplier on all days **≤ 0.90** | step 5 |
| **PC-3** | Sharpe non-inferiority vs S | Margin δ = **0.10**, the top of the de-risk base-rate range: a protective overlay may cost at most what a good one would earn. One-sided bootstrap p of {ΔSR* ≤ −δ} **≤ 0.10**, with blocks of max(10, PW(d), PW(d²)) sessions, 2,000 resamples, seed 11, Bonferroni × the number of configurations searched. The point estimate ΔSR ≥ −δ must also hold at 2× costs. | step 2 (the book's own Lo-SE interval is still printed) |
| **PC-4** | Episode table | Over the §8.6 drawdown episodes of the card's market: ≥ **3** episodes with a positive benefit vs S, and no episode > **50%** of the summed positive benefit | step 5 + leave-one-crisis-out |
| **PC-5** | Years | ≥ 60% of calendar years positive for the overlaid book (unchanged); share of years lagging S printed | step 8 |
| **PC-6** | Plateau | ≥ 50% of neighbouring cells (one step on each declared axis, e.g., window {10, 20, 40, 60} × target ±0.05) keep ≥ half of the centre's PC-1 improvement and the PC-3 point estimate | step 7 |
| **PC-7** | Data sufficiency | Discrete rules ≥ 30 de-clustered onsets (Tier A); ≥ 5 §8.6 drawdown episodes in the sample; ≥ 756 + 126 sessions | decided first |

Steps 1, 3, 4 and 9 apply unchanged: walk-forward when anything is searched, count every try, PBO when ≥ 10 configurations, haircut reported.

**Verdict mapping.** The verdict is decided in this order:

1. **INSUFFICIENT DATA (sufficiency).** PC-7 fails: too few onsets (Tier B), too few episodes, or too short a history. Route: forward simulated running (§8.8) or more history.
2. **REJECT.** At 1× costs, any of these: PC-1 fails; PC-2 fails; the PC-3 point estimate ΔSR < −δ; fewer than 3 of the ≥ 5 drawdown episodes show a benefit; PBO > 0.2 with the winner losing. The data say the rule does not protect, or protects at too high a price.
3. **INSUFFICIENT DATA (inconclusive).** No REJECT condition holds, but either the PC-3 p > 0.10 with the point estimate ≥ −δ (the history cannot yet confirm non-inferiority), or PC-4 fails only on concentration (> 50% from one episode). Route: ≥ 12 months of forward simulated running, then re-gate with the forward record appended (one revision).
4. **REVISE.** Everything holds at 1×, but one of these fails:
   - PC-1 or the PC-3 point estimate at 2× costs. Permitted fix: **lengthen the holding period**, e.g., a no-trade band or a slower estimator. Never lower the cost.
   - PC-6. Permitted fix: **widen the grid**.
   - PC-5. Permitted fix: **extend the history**.
5. **PASS.** All of the above hold. The card becomes a recommendation, labelled **"protective: reduces drawdown; not expected to outperform"**, with its insurance premium (years lagging S) shown beside it.

### 8.8 Forward-simulated running, re-gating and demotion (v1.0: live shadow, promotion, kill)

**Forward books.**
- From the header commit, every card runs in `core/engine`'s simulated order book as two books: overlay-on and overlay-off. Every FORWARD-SIM leg has its own book.
- Each decision writes timestamped `macro_state` and `overlay_decision` artifacts, so the forward record is reproducible and auditable. That is the only out-of-sample evidence that accrues without waiting for new history.

**Re-gate checklist.** All must hold before a FORWARD-SIM or INSUFFICIENT DATA card is re-gated:
1. the tier's sufficiency is met (pooled onsets or forward months);
2. ≥ 12 months of forward record, with no demotion trigger;
3. zero lag-audit violations in the forward record;
4. switches within the budget, which is set per market from the full sample (R4: D&M 0.38 a year, KRW 11.1, rates 7.2, VIX block 14.0);
5. the card re-run with the forward record appended (one revision; N + 1) reaches PASS under its class.

**Demotion triggers.** Any one demotes the card: its output leaves the recommended book and the card gets a new revision with verdict REVISE or REJECT under its class.
- **CARD-O:** the overlay-off forward book beats overlay-on by > 2% of NAV over any 6 months; or forward Sharpe sits below the bootstrap 10th percentile for 12 months.
- **CARD-P:** over a rolling 12 months, forward ΔMDD vs S ≥ 0 (no protection) **and** forward ΔSR vs S < −0.10. A bull-market lag alone is the insurance premium, not a demotion trigger.
- **Both:** switches > 2× the budget; any edit of an acting parameter outside a revision; any lag-audit violation.

**After a demotion:** a 6-month lockout and a new header. A pre-declared re-anchoring event (R-18) is not a new card.

**Weekly brief and monthly card page:**
- ΔSR and ΔMDD vs S;
- time under water, worst-day coverage and re-entry lag;
- the bull tax for Korea and switch counts;
- lag-audit status;
- forward-on vs forward-off simulated P&L.

### 8.9 Indicative verdicts for the current rules (R4b; not a run of QUANTGEN's gate)

- **What R4b is.** A full-sample computation on the research's local reference data (French Mom, ^KS11, Mkt-RF + ^GSPC, FRED), with the §8.7 thresholds. No parameter was searched.
- **What it is not.** The formal verdicts come from `docs/macro_overlay_study.py` on QUANTGEN's own data, engine and walk-forward.

| Card | Class / tier | Instrument cost | Key numbers (R4b) | Indicative verdict | Route |
|---|---|---|---|---|---|
| R-03 momentum vol scale (US) | CARD-O / A | 50 bp, both legs | ΔSR vs unscaled +0.273; one-sided p ≤ 0.001 (10-session and 251-session blocks); SR at 2× 0.631; 70% of years positive | **PASS** (French series) | Run on QUANTGEN's own sleeve; long-only variant for KIS |
| R-04 D&M gate on R-03 | CARD-O / A-provisional | 50 bp, both legs | ΔSR +0.072 (p 0.018 / 0.010); **7 spell onsets** (6 de-clustered at 126 sessions) | **INSUFFICIENT DATA** (sufficiency) | BL-C01 + BL-C12 out-of-region holdouts |
| R-06 Korea VT20 | CARD-P / A (continuous; 9 episodes) | KRX ETF 3 bp | ΔMDD vs S **+4.4 pp** (2×: +4.4); tail ratio 0.82; ΔSR +0.001, p_ni 0.24 (larger of 10- and 101-session blocks; 0.21 at 101); 3 of 9 episodes positive, Jul-2026 = 59% of the benefit; years 73%; plateau 0.63 | **INSUFFICIENT DATA** (inconclusive) | 12 months forward; then re-gate |
| R-06 Korea VT20 | CARD-P / A | KRX stock 35 bp | ΔMDD +4.1 pp (2×: +3.8); ΔSR −0.028 (2×: −0.061), p_ni 0.32; plateau 0.375 | **INSUFFICIENT DATA** (inconclusive; plateau would REVISE) | As above; prefer the ETF instrument book (declared on the card) |
| R-06 US VT15 | CARD-P / A (11 episodes) | US via KIS 50 bp | ΔMDD **+0.2 pp** (2×: −3.4); tail ratio 0.79; ΔSR −0.028, p_ni 0.15 | **REJECT** (PC-1 at 1×) | New card BL-G03 (banded or slower estimator) |
| R-08 VIX ≥ VIX3M entry block | CARD-P / A (64–72 onsets) | per book | Not computed. Block-only Sharpe-neutral; a median 79% of the drawdown happened before flag-on. | **not computed**; PC-1 expected to fail | Run in the study; display as an annotation meanwhile |
| R-11 KRW leg on VT20 | CARD-P / B under strict H.10 (26 onsets) | KRX stock 35 bp (value timing); KRX ETF 3 bp (strict) | ΔMDD +1.1 pp / +0.1 pp; tail ratio 0.99 / 1.00; ΔSR −0.007 / +0.012 | **REJECT** on protection (PC-1, PC-2); formally INSUFFICIENT DATA until the ECOS/KIS history exists | BL-S01 |
| R-12 rates leg on VT15 | CARD-P / A (50–71 onsets) | US via KIS 50 bp, strict +2 business days | ΔMDD **−3.5 pp**; tail ratio 0.99; ΔSR −0.12 | **REJECT** (PC-1, PC-2, PC-3 point estimate) | BL-S02 |
| R-14 TS trend sleeve | CARD-O / A | per venue | Not computed; card E1 (related rule) REJECT | **not computed** | Study run |

**Which current rules would likely get INSUFFICIENT DATA.**
- **R-04** (7 onsets).
- **R-06 Korea**. Eleven years of KOSPI cannot confirm non-inferiority, and the Jul-2026 crash carries 59% of the benefit.
- **R-11** under strict timing (Tier B; formally, until timestamped KRW history exists).
- **Every backlog item without local data:**
  - BL-U01 (leverage state), BL-U02 (Korea factor priors) and BL-U03;
  - BL-C02 (reversal in stress) and BL-C03 (credit: 2 HY clusters on FRED);
  - BL-C05 (Korea flags; 2026 dominates), BL-C06 (flows) and BL-C07(a) (12 KOSPI onsets);
  - BL-C07(b) (needs the 2027+ holdout), BL-C11 (oil events), BL-C13 (yen shock; no Japan sleeve yet);
  - BL-O02 and BL-O03/O04 (< 30 events).

QUANTGEN's last study run recorded **0** INSUFFICIENT DATA cards. The macro cards will add several. That is the honest label, and it is the verdict the gate defines for exactly this case.

**What this means for the displayed recommendation today.** Before any formal run, every macro card is NOT_RUN, so the recommended book carries only the invariants: point-in-time data, bounds, Korea caps, the drawdown ladder and the hedge state. The specification book shows the full stack (vt, vs, D&M, entry block), labelled with verdicts. If the indicative verdicts hold:
- R-03 becomes the first macro factor in the recommended book.
- The Korea vol target stays a labelled descriptive control while its forward record accrues.
- The US vol target and both FORWARD-SIM legs stay labelled refusals that keep running, as card E1 does.

---

## 9. Test plan (`tests/run_all.py`, hermetic)

**Hermetic rule (existing).** `tests/run_all.py` runs the engine, quant and FICC acceptance suites with every network touchpoint patched to raise. Macro tests follow the same rule:
- They read **frozen fixtures** only (**proposed**: `tests/fixtures/macro/`). The fixtures are extracts of the §9.3 reference data as of 2026-10-02, with an md5 per file.
- No macro test may reach FRED, Yahoo, KIS, FMP, ECOS or any other provider (T-HERM-01).

### 9.1 Unit tests

| ID | Test | Pass condition |
|---|---|---|
| T-RO-01 | Read-only | A static scan of every module added by this spec finds no order, cancel, withdrawal, deposit-address or transfer call and no import of an order-submission client. `core/engine/orders` is reached only through the simulated order book API. Every artifact has `read_only: true`. |
| T-HERM-01 | Hermetic | The macro test suite passes with all network touchpoints patched to raise |
| T-LAG-01 | Lag audit | Inject a datum with `available_at_utc > decision_utc` into any acting input → the backtest raises `LookAheadError` and refuses to write the card. At runtime the engine goes HALTED. |
| T-LAG-02 | Leakage sensitivity | Re-running a rule with the input deliberately shifted one period *earlier* (introducing look-ahead) must change the result and trip T-LAG-01. Positional `shift` on a series with gaps must be rejected by the linter / audit. |
| T-SYN-01 | No synthetic acting input | An "auto" provider that degrades to labelled synthetic data for an acting input → `MissingInput`, `status="synthetic_rejected"`, `fail_closed=true`. The same provider for a context item is allowed and labelled. |
| T-CLOSE-01 | Decision time | `decision_time_utc("KR", 2026-10-02)` = 06:30Z; `decision_time_utc("US", 2026-10-01)` = 20:00Z (EDT); `decision_time_utc("US", 2026-01-15)` = 21:00Z (EST). A KRX record stamped 06:31Z is rejected for the 2026-10-02 decision. |
| T-TZ-01 | Cross-time-zone (KST/ET, DST) | For the KOSPI return dated 2026-10-02 (decided at the KRX close of 2026-10-01), the latest usable US close is dated 2026-09-30. For the return dated 2026-10-01 it is 2026-09-29. The NYSE close of 2026-01-15 (EST) maps to 06:00 KST on 2026-01-16; the close of 2026-07-15 (EDT) maps to 05:00 KST on 2026-07-16. |
| T-TZ-02 | FOMC mapping | The 2026-09-16 statement (14:00 EDT) is 2026-09-17 03:00 KST, so `kr_open_gap_session = 2026-09-17` |
| T-MISS-01 | Missing month | CPI YoY for Aug-2026 = **3.353% ± 0.01** (calendar lag). The positional version (3.713%) must not be produced. Derived values spanning Oct-2025 are NaN and flagged. |
| T-MISS-02 | Fail-closed | An acting input missing or stale → state unchanged, `fail_closed=true`, alert raised, no interpolation. The same failure for more than one decision → HALTED. A risk-layer exception → HALTED. |
| T-CAP-01 | Multiplier bounds | Any overlay multiplier outside [0.5, 1.0], or any vt/vs > 1.0, fails schema validation and rules-store validation. A product of 0.75 × 0.5 = 0.375 is clipped to 0.5 and the clip is logged. The overlay layer cannot emit 0. |
| T-BASIS-01 | Exposure basis | Every multiplier has `exposure_basis`. S2 applied to momentum raises an error. vt is not applied to L/S sleeves or to TS trend. |
| T-SER-01 | Named series | An unnamed "Brent" raises. A BZ=F roll day (2026-04-01, −14.5%) is flagged and excluded from return computations. |
| T-PRINT-01 | Closes | The KOSPI close on 2026-03-09 is 5,251.87 (−5.96%). The intraday −8.11% is never stored as a close. |
| T-H10-01 | H.10 production rule | In production mode, an attempt to read DEXKOUS for S1 raises (the KIS fixing is required) |
| T-H10-02 | H.10 strict publication | DEXKOUS dated 2026-09-25 (Friday) is usable from the KRX close of Tuesday 2026-09-29 (KST) and not before. At the KRX close of 2026-10-02 the latest usable DEXKOUS is dated 2026-09-25 (R4b state row). |
| T-H15-01 | H.15 strict rule | DGS10 dated D has `available_at` = D+1 16:15 ET. It is usable at the US close of D+2 business days and at the KRX close of Korea date D+2. The R4b state row: the flag first on in data dated 2026-09-23 earns in the strict book from 2026-09-28. |
| T-VIX-01 | VIX close timing | VIXCLS(D) (official close 16:15 ET) is not usable at the US close of D, and is usable at the US close of D+1 and at the KRX close of K ≥ D+1 |
| T-COST-01 | Costs | Turnover \|Δw\| is charged at the gate's pre-registered rate on the day the new weight earns; both legs for L/S sleeves; a 2× run exists for every card. Changing the rate in a card header raises. Reproduce R4b: KOSPI VT20 at 35 bp SR 0.605 ± 0.01; US VT15 at 50 bp SR 0.505 ± 0.01. |
| T-B5-01 | Estimator gate | The B5 harness on the fixture reproduces SMA20 FHS exceedance 4.70% ± 0.3 pp on KOSPI 2016-03 → 2026-10 and PASS. A synthetic estimator with σ̂ × 0.7 fails. A vol-target card whose estimator is FAIL cannot be PASS. |
| T-LABEL-01 | Causal display label | The label on date t uses only σ̂ through t and the trailing 756 values (never smoothed). Recomputing after appending future data does not change past labels. KOSPI on 2026-10-02 = "elevated"; US on 2026-10-01 = "normal". |
| T-CARD-01 | Card integrity | A card whose header md5 differs from the committed header is refused. A class or claim change creates a new revision and increments N. `displayed_as = recommendation` iff verdict = PASS. |
| T-REPRO-01 | Reproducibility | The same seed, rules-store hash and data snapshot give identical bootstrap and Monte Carlo outputs (to 1e-12). Artifacts record the seed, git hash, config hash, snapshot id and results md5. |
| T-SCHEMA-01 | Schemas | The examples in §6 validate. Missing required fields fail. |
| T-CTX-01 | Context isolation | No acting module imports or reads `context_log` or the 18-indicator sheet's values (static import check plus a runtime guard) |

### 9.2 Integration tests

| ID | Test | Pass condition |
|---|---|---|
| I-01 | End-to-end `macro_daily` workflow for 2026-07-30 and 2026-10-02 (KR and US) on fixtures | All five artifacts are produced and schema-valid. The flags match §11. Decision gates fire on injected failures. |
| I-02 | Episode replay: 2024-07-31 → 2024-08-09 and 2026-06-22 → 2026-07-30 | Korea vt weights and window returns match §9.3 (G-KR-*), gross and net |
| I-03 | Book separation | The FORWARD-SIM S1 and S2 books are computed every day. The recommended book never reads a FORWARD-SIM multiplier or a non-PASS factor (assertion on the book builder). |
| I-04 | Risk-layer last word | Overlay at 1.0 with simulated NAV drawdown −12% → evaluator BLOCKED for new entries and overlay forced to 0.5. At −15% → engine HALTED, target 0×, re-arm refused for 10 sessions. |
| I-05 | Full-sample lag audit | Zero violations across every backtest used for golden values that are flagged COMPLIANT in §9.3 |
| I-06 | Event calendar | A cancelled event (Oct-2025 CPI) produces no window. A delayed event moves its window. A US CPI night sets the KR opening-gap flag for the next KRX session. Window hits produce BLOCKED evaluator decisions only for new intraday entries. |
| I-07 | Card study | `docs/macro_overlay_study.py` on fixtures writes one card per overlay rule, with all nine gate lines and PC-1..PC-7 for CARD-P. The R-06 KR card's PC values reproduce §8.9 within Level-1 tolerance. |

### 9.3 Acceptance tests: golden values (gross R4, net R4b)

**Reference data definitions:**
- Ken French daily files (Mom, ST_Rev, 5-factor 2×3, regional Mom) through 2026-08-31, and the monthly F-F factors for the 24-month market return;
- FRED series as downloaded on 2026-10-02 (latest vintage);
- Yahoo daily closes (^KS11, ^GSPC, SPY, KRW=X, ^TNX, ^RUT) through 2026-10-02;
- FRED NASDAQ100.

All of these are frozen in the test fixtures.

**Construction rules.**
- Returns are simple daily returns.
- The US market is French Mkt-RF through 2026-08, spliced with the ^GSPC price return for Sep-2026. Korea uses ^KS11 price returns (no dividends).
- **Timing:** a weight built from information through the close of t−1 earns the return of t, which is "decide at the close of t, earn from t+1". The exceptions are flagged in the Timing column.
- **Research bootstrap:** circular, 63-day blocks, 1,000 resamples, seed 20261002 (R4-comparable). Gate-style statistics for the cards use §8.5.
- **Costs (R4b):** per side × |Δw|, charged on the day the weight earns. Initial entry not charged. Buy-and-hold uncosted. Momentum: the overlay's own turnover on both legs, with French Mom gross of its constituent turnover.

**Tolerances:**
- **Level 1**, a reference implementation on these definitions: Sharpe ±0.01; max DD ±1 pp; window returns ±1 pp; weights ±0.02; bootstrap shares ±0.03.
- **Level 2**, QUANTGEN production feeds (e.g., KIS KOSPI official closes): Sharpe ±0.03; window returns ±2 pp. Every deviation must be explained in the acceptance report.

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
| G-MOM-07 | Reference (not spec) | Vol scale cap 2: 0.907; DM 0×: 0.657 | — | — | COMPLIANT |
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
| G-KR-01 | Buy-and-hold: Sharpe / max DD | 0.634 / −43.9% | same (uncosted) | same | same | COMPLIANT |
| G-KR-02 | R-06 vol target (SMA20, 20%, cap 1): Sharpe / max DD | **0.638** / −36.8%. 2016–25: 0.457 vs 0.534. 2018–24: −0.052 vs 0.071. | 0.635 / −36.8% | **0.605** / −37.2%; 2016–25 0.428; 2018–24 −0.083 | 0.632 / −36.9%; 0.573 / −37.5% | COMPLIANT |
| G-KR-02b | R-06 ΔSR vs buy-and-hold (share): 2016–26 / 2016–25 / 2018–24 | +0.004 (0.45) / −0.077 (0.06) / −0.123 (0.03) | +0.001 (0.44) / −0.079 (0.05) / −0.125 (0.03) | −0.028 (0.37) / −0.106 (0.02) / −0.154 (0.01) | −0.001 / −0.061 (0.28) at 70 bp | COMPLIANT |
| G-KR-02c | Static book with VT20's average exposure (0.925): max DD; ΔMDD of VT20 vs it | −41.3%; +4.5 pp | +4.4 pp | +4.1 pp | +4.4 / +3.8 pp | COMPLIANT |
| G-KR-03 | R-06 windows (vt vs buy-and-hold) | Jul-2026 crash −12.2% vs −38.6%; Mar-2026 −7.9% vs −19.9%; Aug-2024 −7.9% vs −5.5%; Apr-2025 −11.7% vs −12.0%; 2020 crash −25.8% vs −34.1%; 2020 rebound +25.9% vs +49.9%; H1-2026 +51.7% vs +101.1%; 30 Jul → 30 Sep 2026 +5.9% vs +22.2% | Jul-2026 −12.3%; Mar-2026 −7.9%; Aug-2024 −7.9%; 2020 crash −25.8%; H1-2026 +51.6% | Jul-2026 −12.3%; Mar-2026 −8.0%; Aug-2024 −8.0%; Apr-2025 −11.8%; 2020 crash −26.0%; 2020 rebound +25.4%; H1-2026 +50.5%; post-crash +5.6% | — | COMPLIANT |
| G-KR-04 | R-06 weights | 22 Jun 2026 0.30; 23 Jun 0.33; 30 Jul 0.25; earning on 2 Oct 0.61; decided at the 2 Oct close for the next session 0.69 (rv20 28.9%) | same | same | same | COMPLIANT |
| G-KR-05 | S1 KRW 0.75× (DEXKOUS, D ≤ K−1): ΔSR vs buy-and-hold / on VT20 / % days on | +0.032 (0.965) / +0.042 (0.977) / 9.0% | +0.029 (0.94) / +0.038 (0.96) | **−0.008 (0.32)** / −0.007 (0.34) | +0.025 / +0.034 at 6 bp; −0.048 / −0.057 at 70 bp | **VALUE** (H.10 publication ignored) |
| G-KR-05s | S1 strict H.10 publication: ΔSR vs buy-and-hold / on VT20 / % days on / onsets (20-session) | **+0.001 (0.53)** / +0.013 (0.74) / 9.1% / 26 | −0.000 (0.49) / +0.012 (0.70) | −0.016 (0.22) / −0.007 (0.34) | −0.002 / +0.010 at 6 bp; −0.034 / −0.027 at 70 bp | COMPLIANT |
| G-KR-06 | Reference vol target cap 1.5 | Sharpe 0.534; max DD −46.2% | — | — | — | COMPLIANT |

**US market (Mkt-RF + ^GSPC Sep-2026, 1990-02-01 → 2026-09-30). Net: US shares via KIS 50 bp; 2× = 100 bp.**

| ID | Quantity | Gross (R4 / R4b) | Net 50 bp | Net 100 bp | Timing |
|---|---|---|---|---|---|
| G-US-01 | Buy-and-hold vs R-06 (SMA20, 15%, cap 1): Sharpe / max DD | 0.534 / −59.2% vs **0.602** / −49.9% | VT15 **0.505** / −53.8%; ΔSR −0.028 (0.29) | 0.409 / −57.3%; ΔSR −0.125 (0.03) | COMPLIANT |
| G-US-01b | Static book with VT15's average exposure (0.890): max DD; ΔMDD of VT15 vs it | −54.0%; +4.1 pp | +0.2 pp | −3.4 pp | COMPLIANT |
| G-US-01c | Challenger EWMA(0.94), same target: Sharpe | 0.605 | 0.520 | 0.434 | COMPLIANT |
| G-US-02 | S2 rates 0.5×, **value timing**: ΔSR vs buy-and-hold / on VT15 / % days on / onsets (60-session) | +0.038 (0.98) / +0.037 (0.97) / 6.2% / 50 | −0.065 (0.00) / — | −0.168 / — | **NON-COMPLIANT** (DGS10(D) used at the close of D) |
| G-US-02a | S2 at +1 business day (v1.0 "strict") | +0.010 (0.67); 1990–2007 −0.017 | −0.093 (0.00) | −0.196 | **NON-COMPLIANT** by 15 minutes (DGS10(D) posts 16:15 ET on D+1) |
| G-US-02s | **S2 strict H.15 (+2 business days)**: ΔSR vs buy-and-hold / on VT15 / 1990–2007 / 2008–26 / 2020–26 | **−0.000 (0.53)** / −0.007 (0.39) / −0.034 / +0.025 (0.77) / +0.084 (0.92) | **−0.103 (0.00)** / −0.120 (0.00) | −0.206 / −0.233 | COMPLIANT |
| G-US-03 | S2, 2015–26 by timing | DGS10 +0.066 (NON-COMPLIANT); ^TNX +0.071 (VALUE, live proxy); +1 day +0.071 (NON-COMPLIANT by 15 min); **+2 business days +0.053 (0.90)** (COMPLIANT) | ^TNX −0.020 (0.31); +2 bd −0.032 (0.20) | ^TNX −0.111; +2 bd −0.118 | as listed |
| G-US-04 | S2 duration proxies (value timing) | NDX 2008–26 +0.039 (0.94); Russell 2000 2015–26 +0.058 (0.97); small-cap proxy 1990–26 +0.025 (0.89) | not recomputed | — | **NON-COMPLIANT** (value timing on DGS10) |

**B5-style estimator check (R4b; daily origins; FHS form unless stated).** The 5% VaR exceedance band is ±2 binomial SE.

| ID | Market / window | SMA20 | EWMA(0.94) | GARCH(1,1)-t, refit 7 / window 504 (informational) |
|---|---|---|---|---|
| G-B5-01 | KOSPI 2016-03 → 2026-10 (2,594 origins; band 4.14–5.86%) | 4.70%, PIT p 0.12 → **PASS**; normal form 6.75%, PIT p < 0.001 → FAIL; every-7th-session subsample 7.55% (371 origins; band 2.74–7.26%) → outside | 4.90%, PIT p 0.03 → **PASS** | t-quantile 6.92% → FAIL; FHS 5.42% → PASS (2,123 origins) |
| G-B5-02 | SPY 2016-03 → 2026-10 (2,663 origins; band 4.16–5.84%) | 4.99%, PIT p 0.57 → **PASS** | 5.22%, PIT p 0.79 → **PASS** | t-quantile 6.33%, PIT p < 0.001 → FAIL (the app's own study: 6.6%, PIT p 0.003, REJECT) |
| G-B5-03 | US market 1991-03 → 2026-10 (8,961 origins; band 4.54–5.46%) | 5.31%, PIT p 0.98 → **PASS** | 5.31%, PIT p 0.93 → **PASS** | not run |
| G-B5-04 | Display labels on 2 Oct 2026 | KOSPI **elevated** (σ̂ 28.9%; trailing-756 quartiles 15.7 / 18.6 / 33.6%; 70th percentile); US **normal** (10.7%; 10.5 / 12.7 / 15.2%; 28th percentile) | — | — |

**Current state.** §11 values (Level-1 tolerance).

---

## 10. DO-NOT-BUILD list

Never implement any of these unless a new model card passes the gate (§8) with new evidence. Each item names its node and the evidence against it. "One-sided" means refuted by one panel plus the data, with the other panel silent.

**Overlay design**

1. **The prior four-state trend × stress classifier and its multiplier table** (N-03). Book −0.07 (share 0.23). It held momentum at 1.425× into Nov-2020 (−12.0%) and 1.50× into Jul-2026 (−10.9%).
2. **Any multiplier above 1.0.** This includes momentum 1.5× in "risk-on", reversal 1.5× or 2×, quality / low-vol / min-vol 1.5×, Korea gross 1.5×, flow ×1.5, AAII-reversal ×1.25, and vol-target caps above 1 (N-03, N-02). Reversal 1.5×: −0.05 to −0.20. RMW 1.5×: −0.01. KOSPI vol target with cap 1.5: Sharpe 0.534 vs 0.638.
3. **A VIX-term-structure switch for momentum (0× or halved) or for reversal (1.5×), and the post-stress-clear 0.5× momentum schedule** (N-05). −0.15 in 2020–26 (share 0.05); −0.19 on top of vol scaling; schedule −0.158.
4. **Cut-and-re-add gates on existing exposure** (desk "boundary behaviour") (N-04). −0.088 Sharpe; −0.185 in 2020–26.

**Korea gates**

5. **Korea gates built from US or global inputs** (N-18):
   - the SOX 60-day trend × USD/KRW 20-day gate;
   - the SOX trend gate;
   - the AI-hardware gate;
   - the US stress row applied to KOSPI;
   - the two-speed and residual KRW gates, dollar "regime B", and the three-way KRW conjunction.
   
   Evidence: +0.31 only with look-ahead, +0.05 implementable, −0.16 in 2024–26. SOX leg −0.22. The AI-hardware gate was on through the crash and off at the trough. US stress row on KOSPI −0.15.

**Macro gates on factors or gross**

6. **Macro-variable factor or gross gates** (N-11, N-12). These include:
   - curve re-steepening, and bull or bear steepener rules;
   - a real-rate level state, or a 63-day real-rate gate on momentum;
   - credit-triggered factor weights (momentum 0.5×, quality 1.5×);
   - momentum 0.5× under rates stress;
   - level thresholds (10y > 5.25%, the MOVE variant).
   
   Evidence: −0.09 (share 0.00); −0.04; −0.05 (2020–26); −0.065; −0.032.
7. **A lagged oil-price gate on equity or KOSPI gross** (Brent +30% over 63 days, or 20-day > +25%) (N-43). Across 22 episodes, forward 63-day returns were 2.67% vs 2.66% unconditional. The gate first fired after the −12.06% day.
8. **Net-liquidity (WALCL − TGA − RRP) or M2 rules for crypto or equities** (N-55). −0.01; −0.20 in 2023–26. BTC fell 53% while net liquidity rose $41bn.

**Forecasts, surveys and macro models**

9. **Street point forecasts, house views, recession odds and target dispersion as inputs**; FMS, Bull & Bear, AAII and COT timing rules; post-trigger crowding cuts; consensus-surprise entries at retail latency (N-56).
   - S&P consensus abs error 17.13%; 2026 forecasts called for cuts against an actual hike; FMS Aug-2026 published after KOSPI's −25.4% fall.
   - Aug-2024: momentum lost −5.9% before the crowding trigger and gained +6.5% after it.
   - Surprises are priced within ≈ 5 ms.
10. **Sahm, curve, probit or growth × inflation-quadrant gates**; fixed-coefficient Okun, Phillips, sacrifice-ratio or M2 → CPI relations (N-30; N-31 one-sided).
    - 26 months without recession after the Sahm trigger.
    - 534-day inversion.
    - Okun β −0.407 → −0.05.
    - Phillips OOS RMSE 2.15 vs 1.79.
11. **Methodological shortcuts** (N-49, one-sided):
    - smoothed regime probabilities;
    - unpenalised daily HMM / Markov-switching gates;
    - "complexity" / random-feature macro ML timing;
    - LLM or text signals backtested over periods before the model's training cutoff.
    
    Evidence: real-time switching 16.9 a year with 49% false episodes; Sharpe smoothed 1.518 vs real-time 0.390 vs buy-and-hold 0.539; complexity timing ρ 0.93 with vol-timed momentum.

**Events, calendars and data**

12. **24-hour pre-event blackouts; swing-book blackouts around FOMC, CPI, NFP, BoK or export prints; a KRX quad-witching blackout; the index expiry-close fade** (N-38, N-58).
    - A 24 h FOMC blackout covers the whole preceding KRX session.
    - Quad witching t −0.38.
    - The day after expiry continues rather than reverses (correlation +0.33).
13. **Calendar and supply-timing tilts** (N-58, one-sided): quarter-end tilts, KRW April seasonality, export-print tilts, aggregate issuance or IPO-window multipliers, buyback-blackout multipliers, Korean issuance volume as sentiment.
    - April KRW t −0.64; quarter-end fade t −1.26; detrended IPO counts t −0.3 to −1.4; buyback blackouts t −0.26.
14. **Rate-differential models of USD/KRW direction; a hard-wired "foreign selling ⇒ weak KRW"; Korean foreign flow as a direction signal or a flow-regime up-weight** (N-23, N-21).
    - Rate-differential R² 0.022.
    - Q3-2026: USD/KRW −12.4% (the won stronger), while foreigners sold ₩21.5tn in September alone.
15. **"USD down and equities down" as an equity de-risk trigger** (N-29). It was followed by +7.27% over 13 weeks vs +2.84% unconditional.
16. **A credibility-state blackout rule (contested-state blackouts of all families)** (N-32). The gauge read "anchored" in 2022.
17. **A 200-day-average conjunction on the vol target** (P6's fix) (N-14). It removed the bull tax but also all Q3-2026 protection: −38.1% vs −9.6%.
18. **Treating 2022–26 as a clean holdout** (N-50).
19. **Data shortcuts** (N-46, N-47):
    - Yahoo continuous-futures returns across rolls;
    - an unnamed "Brent";
    - intraday circuit-breaker prints as closes;
    - positional lags on monthly series with gaps;
    - H.10 or H.15 data used as if same-day;
    - US-session data on KOSPI close-to-close returns of the same date.
20. **China PMI or CNY as a Korea signal** (China stays in the covariance only); **CESI as an equity feature** (executive DROP list; one-sided).

**Read-only design and governance (v1.1)**

21. **Any order, cancel, withdrawal, deposit-address or transfer path, or a broker execution adapter, inside this programme** (P0; QUANTGEN rule 01). §3.10 records what would have to hold if the owner ever decided otherwise. It is not a design.
22. **Offering a non-PASS card's output as a recommendation**, or letting a FORWARD-SIM multiplier reach the recommended book (P7; QUANTGEN rule 03).
23. **Lowering a pre-registered cost, or switching a card's instrument book after seeing results**, to make a card pass (P10). An instrument-book change is a new card.
24. **Smoothed or forward-looking calm / normal / elevated / stressed labels, or using those labels (or the existing regime read or sheet z-scores) as gates** (§3.6, R-06; N-49).
25. **GARCH-t, GJR, skewed-t or any model as the sizing estimator before it passes B5** (R-06, R-16; architecture review B5; the app's own SPY REJECT).
26. **Value-timing golden values presented as compliant.** H.10 and H.15 series used before publication must be labelled VALUE or NON-COMPLIANT (§9.3), and a production rule may not read the published series in their place.

---

## 11. Current state snapshot (2026-10-02)

Use this on day one to sanity-check the implementation, at the Level-1 tolerance.

**Sources:**
- the R4 recomputation (`R4_golden_values.csv`);
- the R4b strict-timing and label rows (`R4b_golden_values_net.csv`);
- Executive Chair Appendix A (`R3_CHAIR_E_checks.txt`).

All values were traced in Appendix V of the backlog.

**How to read the snapshot.**
- "Data date" is the date the value refers to.
- The decision that may use a value follows §4.1.
- No card has been formally run, so every row's recommended-book value is the invariant-only value (§8.9).

**Momentum and vol targets**

| Input | Value (data date) | Specification-book output | Display label |
|---|---|---|---|
| US Mom σ126 | 23.9% (2026-08-31) | **vs = 0.50** (R-03; indicative PASS) | — |
| US 24-month market return | +39.7% (end-Aug-2026) | D&M bear state **OFF**. Mkt vol126 14.3% vs its 2/3 quantile 17.4%. | — |
| KOSPI close | 6,943.66 (2026-10-02); −23.8% from the 9,114.55 closing peak; 1.098 × 200-day average | — | — |
| KOSPI rv20 (SMA20) | 28.9% (2026-10-02) | **vt_KR earning on 2 Oct = 0.61; decided at the 2 Oct close for the next session = 0.69.** rv21 31.9% sits at the 73rd percentile of the trailing 3 years. | **elevated** |
| S&P 500 | 7,666.45 (2026-10-01); 1.062 × 200-day average; rv20 10.7% | **vt_US = 1.00** | **normal** |

**Stress inputs**

| Input | Value (data date) | Output |
|---|---|---|
| VIX / VIX3M | 16.34 / 18.37 (2026-09-30) | Entry block **OFF** (usable from the 2026-10-01 US close; §4.1) |
| HY OAS | 3.12%; 21-day change +47 bp (2026-09-30) | Context (just under +50 bp) |
| Baa−10y | 1.47; 21-day change −12 bp | Context |

**FORWARD-SIM legs (never in the recommended book)**

| Input | Value (data date) | Output |
|---|---|---|
| US 10y | 5.29% (2026-09-30), the highest close since 14 May 2002; 20-day change **+50 bp** | **S2 flag on in data dated 23 Sep 2026.** Under strict H.15 the S2 book applies it from the decision at the close of 25 Sep (earning from 28 Sep), and it was still on at the last US date in data (1 Oct). Indicative card verdict: REJECT at 50 bp. |
| USD/KRW | DEXKOUS 1,356.51 (2026-09-25), 20-observation dlog −1.81%. KRW=X 1,360.63 (2026-10-02), 20-observation dlog +0.38%. | **S1 flag OFF** on both timings. Under strict H.10, the latest DEXKOUS usable at the 2 Oct KRX close is dated 25 Sep. Production reads the KIS fixing. |

**Hedge state (risk model only)**

| Input | Value (data date) | Output |
|---|---|---|
| Core PCE YoY | 3.01% (Aug-2026, calendar lag) | Contributes to `hedge_credit_off` |
| Stock–bond correlation, 63 / 252 days | +0.53 / +0.33 (2026-09-30; S&P vs −ΔDGS10 on data dates) | **`hedge_credit_off = TRUE`** |
| Broad USD | 120.33 (2026-09-25); 20-day change +1.67% | `hedge_failure` FALSE (the USD is up) |

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
| Samsung + SK hynix share of KOSPI | ≈ 53.7% implied (2 Oct 2026; 55.5% reported in 2026) → **pair cap active** (> 45%) |

---

## 12. Build order (mapped to QUANTGEN packages)

| Milestone | Scope (package) | Acceptance criteria |
|---|---|---|
| **M0** Scaffolding | Rules-store entries (§7) with validation (`core/rules`); JSON Schemas (§6); bounds; artifact writer with git, config and snapshot hashes; macro fixtures under `tests/fixtures/macro/` (proposed) | T-RO-01, T-HERM-01, T-SCHEMA-01, T-CAP-01, T-BASIS-01 and T-REPRO-01 pass |
| **M1** Data layer | `core/ficc/data` PIT layer: registry, `pit_value`, `available_at` and publication rules (H.15, H.10, VIX close, BEA/BLS), vintages, `retrieved_at` on the cache, lag audit, no synthetic acting inputs; `core/calendars` and `core/markets`: KRX/NYSE sessions, holidays, DST, `decision_time_utc`, `usable_at`; ECOS provider (proposed) | T-LAG-01/02, T-SYN-01, T-CLOSE-01, T-TZ-01/02, T-MISS-01/02, T-SER-01, T-PRINT-01, T-H10-01/02, T-H15-01, T-VIX-01 pass. CPI Aug-2026 YoY = 3.353%. |
| **M2** Vol and risk layer | `core/quant/risk`: SMA20 σ̂, R-06 (KR, US), display label, R-07 caps and ladder, R-09 hedge state; optimiser inputs honour `hedge_credit_off` | G-KR-01..04, G-KR-02b/c, G-KR-06, G-US-01/01b within Level-1 tolerance, gross and net; T-COST-01 and T-LABEL-01 pass; §11 hedge-state values reproduced |
| **M3** Estimator gate | `docs/vol_backtest.py` (B5, rolling origins, FHS and model forms, PIT); estimator status written to `macro_state.vol.estimator_b5` | G-B5-01..04 reproduced; T-B5-01 passes |
| **M4** Momentum sizing and fixed families | `core/quant/signals`: family tags on the composite (§3.7), R-03, R-04, R-05; exposure basis wired through; recommended vs specification books | G-MOM-01..08, G-BOOK-01 and G-INTL-01 within tolerance |
| **M5** Engine and events | `core/engine`: evaluator BLOCKED decisions (R-08, R-10, ladder −12%), HALTED triggers and re-arm cooling-off, per-card switch counts, overlay-on/off and FORWARD-SIM simulated books; `core/calendars` event store with status, windows and opening-gap nights | I-03, I-04, I-06 pass; the FOMC → KST mapping test passes; window hits and BLOCKED decisions are logged |
| **M6** Context and the macro sheet | `core/ficc/macro`: R-13 items, probit, Taylor range, isolation guard; reconciliation of the 18-indicator sheet (§3.6; BL-G06); `macro_state` and `overlay_decision` builders; Macro page panel | T-CTX-01 passes; §11 context values reproduced; every sheet item appears in `context_log` with `from_sheet=true` |
| **M7** Cards through the gate | `docs/macro_overlay_study.py` writes one model card per overlay rule through the existing nine-step gate; `core/quant/backtest` gains the overlay-on/off paired evaluation, the static same-exposure comparator, the §8.6 episode table and PC-1..PC-7 | I-07 passes; R4b's §8.9 numbers are reproduced on fixtures; header md5 and results md5 are written; T-CARD-01 passes |
| **M8** Workflow and FORWARD-SIM | `core/skills/workflows/macro_daily.yaml` (proposed) with its decision gates, running after each close; S1 and S2 forward books with committed card headers | I-01 passes; G-KR-05/05s and G-US-02/02a/02s/03 within tolerance; I-03 passes: the recommended book reads no FORWARD-SIM multiplier |
| **M9** Quant Lab | R-16 scenarios (seeded), SEP-band rate paths via `core/ficc/ratesim`; GARCH-t fan keeps its B5 label | Seeded runs are reproducible. The 2026-inclusive fit shows higher tail quantiles than the 2015–24 fit (report both). |
| **M10** (deferred) | R-17 FX and crypto sleeves | When those sleeves exist: card headers committed, FORWARD-SIM first |

---

## 13. Compact evidence appendix

**ID conventions.**
- "N-xx": nodes in `R4_neural_link_matrix.csv`.
- "PC/PX/PR-P": professor-panel items. "EC/EX/ER-E": executive-panel items.
- "Q1a/Q1b": data labs. "R4": the gross recomputation, `scripts/r4_golden_values.py` → `results/R4_golden_values.csv`.
- "R4b": v1.1's net-of-cost, strict-timing, protective-check and B5-style recomputation, `scripts/r4b_golden_net.py` → `results/R4b_golden_values_net.csv`; verification log `scripts/r4b_verify_spec.py` → `results/R4b_verification_log.csv` (backlog Appendix V).
- "AR" / "PP": the QUANTGEN Architecture Review (2026-09-14, fetched 2026-09-20) and the QUANTGEN public page (2026-09-29).

**Rules built now**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-01 macro quantities lag | PC-P-01; EC-E-23, ER-E-21 | Returns → ΔIP p = 2e-8 vs ΔIP → returns p = 0.04. KOSPI leads exports by 4–7 months (corr 0.52 at k = −5). Goyal–Welch–Zafirov: more than 1/3 of 46 predictors lose significance. | R2_P3 Granger tests; Q1b B3; Goyal–Welch (via P2) |
| N-02 / N-03 bounds; no multipliers above 1 | PC-P-05, PR-P-12/13/14; EC-E-01, ER-E-04/05/20 | Four-state −0.07. Momentum 1.425× / 1.50× into the 2020 and 2026 crashes. Markov 0.5/1 vs 0/1: 0.554 vs 0.390. R4 KOSPI vol target cap 1.5: 0.534. | Q1b B1; `r2_P1_p6_checks.py`; R4 |
| N-04 stress → variance | PC-P-02; EC-E-05/06, ER-E-19 | VIX-TS → realised vol t 7.17 (R² 0.385) vs → return t 0.04. Cut-and-re-add −0.088. Brent +30% episodes: 2.67% vs 2.66%. EPU +1 SD → +1.80% over 3 months. | `r2_P2_p3_checks.py`; `r2_E5_e1_tests.py`; Johnson 2017 (via P3) |
| N-06 vol scaling | PC-P-03; EC-E-07 | 0.40 → 0.91 (cap 2) / **0.71 (cap 1, R4)**; **0.67 net of 50 bp on both legs (R4b)**. Decay +0.66 → +0.26. z 3.9–4.35. | Barroso & Santa-Clara 2015, *JFE* 116(1) (https://novaresearch.unl.pt/en/publications/momentum-has-its-moments/); Daniel & Moskowitz 2016, *JFE* 122, Table 7 (https://www.kentdaniel.net/papers/published/jfe_16.pdf); Moreira & Muir 2017 (https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf); Cederburg et al. 2020 (https://experts.arizona.edu/en/publications/on-the-performance-of-volatility-managed-portfolios/) |
| N-07 D&M gate | PC-P-04; EC-E-07 | *JFE* T7 (1934:01–2013:03): **0.682 → 1.041 → 1.194** (dynamic OOS; in-sample 1.202). Table 1 (1927–2013): WML 0.71. Do not pair 0.71 with Table 7; the "1.43" figure appears nowhere in the paper. T11: Europe 0.462 → 1.130, Japan 0.067 → 0.416, UK 0.465 → 0.891. R4 add-on +0.084. | Same D&M PDF; Q1b B1; R4 |
| N-09 reversal and quality 1.0× | PC-P-06; EC-E-08 | 72%/yr at 30.6% vol vs 13% at 11.7% → ≈ 0.8×. RMW β −0.099 (HAC t −3.0). RMW 2022 +8.4%. Overnight +0.93% vs intraday −1.05% a month. | Nagel 2012, NBER w17653 (https://www.nber.org/system/files/working_papers/w17653/w17653.pdf); Lou–Polk–Skouras (https://personal.lse.ac.uk/polk/research/TugOfWar.pdf); `r3_chair_P_checks.py` |
| N-14 / N-16 / N-17 Korea | PC-P-23/24/10; EC-E-02/03/04/15 | KOSPI −38.6% (22 Jun–30 Jul 2026) vs S&P −0.5%, KRW +7.4%. VT20 −12.2% (−12.3% net of 35 bp, R4b). VT20 max DD −36.8% vs −41.3% for the same-exposure static book (R4b). Pair 55.5% of KOSPI. SOX β 0.247 → 0.559 (2026). 88% of 2026 days with rv21 > 30%. SMA20 passes a B5-style check on KOSPI (4.70% exceedance; R4b). | Q1a-C16; Q1b B3; `r3_CHAIR_E_checks.py`; R4; SEDaily 27 May 2026 (https://en.sedaily.com/finance/2026/05/27/samsung-sk-hynix-surge-alone-as-chip-duo-tops-half-of-kospi); KEIA (https://keia.org/analysis/explaining-south-koreas-stock-market-boom/) |
| N-28 / N-29 hedge state | PC-P-18/19; EC-E-12/13 | Correlation −0.29 / +0.21 by core PCE. Apr-2025: DXY −3.9%, 10y +28 bp, S&P −5.4%. +7.27% over 13 weeks after USD↓ & equities↓. | Campbell–Pflueger–Viceira, NBER w20070 (https://www.nber.org/papers/w20070); Q1a A8, A11; `r2_P3_p4_checks.py` |
| N-33 TS trend | PC-P-27; EC-E-09 | Book SR 0.49 (corr 0.08); KOSPI long/flat 0.47 vs 0.52; 2020 −16.7% | Moskowitz–Ooi–Pedersen 2012 (https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf); Q1b B5; Zakamulin (https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html) |
| N-37 / N-38 / N-40 / N-41 events | PC-P-13/22, PR-P-24; EC-E-15/16/17/19, ER-E-07/22 | Pre-FOMC drift 44.5 → 9.2 bp. FOMC days +0.6 vs +5.3 bp at 1.3× risk. BoK 0.82×. Quad witching t −0.38. 80.9% of volatility interruptions in the first 30 minutes. ≈ 15% of KOSPI variance from the prior US session. | Savor–Wilson (https://faculty.wharton.upenn.edu/wp-content/uploads/2013/06/draft20130612pp-full.pdf); Lucca–Moench (https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.html); Knox–Vissing-Jørgensen FEDS 2026-023 (https://www.federalreserve.gov/econres/feds/files/2026023pap.pdf); Kurov et al., ECB WP 1901 (https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1901.en.pdf); SEDaily 7 May 2026 (https://en.sedaily.com/finance/2026/05/07/kospi-volatility-interruptions-double-in-early-trading-hours); `r2_E2_event_days.py` |
| N-44 / N-48 oil and Monte Carlo | PC-P-02/23/24, PX-P-05; EC-E-20/21 | 2026 vs 2022 at +20 days: KOSPI −15.5% vs +0.4%. Spot–futures gap ≈ $29 (7 Apr 2026). SEP 1-year short-rate band ±1.4 pp. | Q1a A10; T1-C6; IEA 11 Mar 2026 (https://www.iea.org/news/iea-member-countries-to-carry-out-largest-ever-oil-stock-release-amid-market-disruptions-from-middle-east-conflict); Fed SEP 13 Dec 2023 (https://www.federalreserve.gov/monetarypolicy/fomcprojtabl20231213.htm) |
| N-46 / N-47 data hygiene | PC-P-12/13, PR-P-04/08; EC-E-26/27 | CPI 3.71% vs 3.35%. Real-time Sahm 0.53 vs 0.50. Payroll benchmarks −818k / −911k. Look-ahead +0.31 → +0.05. H.10 weekly: KRW leg +0.032 → +0.001 at strict publication (R4b). **H.15 posted 16:15 ET the next business day: rates leg +0.038 (value) → +0.010 (+1 business day, R4) → −0.000 (+2 business days, strict for a close decision, R4b).** | Richmond Fed on the Oct-2025 data gap (https://www.richmondfed.org/research/national_economy/macro_minute/2025/phantom_figures_missing_data_in_october); Fed H.10 (https://www.federalreserve.gov/releases/h10/20250414/); Fed H.15 (https://www.federalreserve.gov/releases/h15/, fetched 2026-10-02); Q1b-C27 |
| N-50 governance | PC-P-11/29, PR-P-30; EC-E-02/29, ER-E-24 | SE(ΔSR) 0.034 / 0.052; 33–44 years needed to detect +0.05; 21 stress clusters in 12 years; every one of 26 market-level de-risk overlays (13 US, 13 KOSPI) has a 95% CI that straddles 0 (momentum vol scaling, R-03, is not among them) | Politis & White 2004 (https://public.econ.duke.edu/~ap172/Politis_White_2004.pdf); Patton, Politis & White 2009 (https://public.econ.duke.edu/~ap172/Patton_Politis_White_2009.pdf); Bailey & López de Prado DSR (https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf); PBO (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551); Harvey & Liu 2015 (https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF); Harvey–Liu–Zhu (https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2249314); Harvey et al. 2018 (https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf) |

**FORWARD-SIM legs (v1.0: shadow legs)**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-22 KRW leg | PX-P-04, PR-P-08; EC-E-10, ER-E-14 | 0.5×: +0.06 to +0.07. **0.75×: +0.032; +0.042 on VT20 (R4, value timing).** +1 session or Yahoo timing: +0.016. **Strict H.10: +0.001 (R4b). Net of KRX stock 35 bp: −0.008 (R4b).** Protective checks: ΔMDD vs static +1.1 pp, tail ratio 0.99 (R4b). | Q1b B3; `r2_E3_tests.py` S2; R4 |
| N-24 rates leg | PC-P-17; EC-E-11 | +0.041 (0.99, R2 construction); 2020–26 +0.109; ex-2022 +0.028; grid median ≈ +0.01. **R4: +0.038 on buy-and-hold, +0.037 on VT15 cap 1 (value timing); +0.010 at +1 business day. R4b: −0.000 at the strict +2 business days; −0.103 net of 50 bp.** | `r2_E5_e1_tests.py` T1; R4 |

**Context and planned sleeves**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-26 / N-30 context | PC-P-15/16/17, PR-P-06/07/19; EC-E-19/23 | Sahm 9 of 9 recessions, but a median +2 months late; Jul-2024 trigger then 26 months without recession. Probit 0.744 in May-2023. Inversion 534 days. 10y +111 bp YTD (TIPS +100, BE +11). KW term premium 1.02. 10y **5.29% = highest close since 14 May 2002**. Policy 0.4–2.3 pp below the Taylor rules. | Sahm 2019 (https://www.hamiltonproject.org/assets/files/Sahm_web_20190506.pdf); Estrella–Trubin (https://www.newyorkfed.org/medialibrary/media/research/current_issues/ci12-5.pdf); Fed policy rules page (https://www.federalreserve.gov/monetarypolicy/policy-rules-and-how-policymakers-use-them.htm); FRED THREEFYTP10 (https://fred.stlouisfed.org/series/THREEFYTP10); Q1a A2, A5, A6, A7 |
| N-52 FX sleeve | PC-P-20/21, PR-P-22/27; EC-E-30 | USD/JPY Fama b −1.92 / 0.11. Carry −10.6% (Jul–Aug 2024). Vol rose in 4 of 5 interventions. Long-KRW carry skew −2.38, worst quarter −36.9%. | Fama 1984 (https://ideas.repec.org/a/eee/moneco/v14y1984i3p319-338.html); Brunnermeier–Nagel–Pedersen, NBER w14473 (https://www.nber.org/papers/w14473); BIS Bulletin 90 (https://www.bis.org/publ/bisbull90.pdf); MoF intervention data (https://www.mof.go.jp/policy/international_policy/reference/feio/foreign_exchange_intervention_operations.csv) |
| N-54 / N-55 crypto | PC-P-30; ER-E-13 | Net-liquidity rule −0.01 / −0.20. BTC −53% while net liquidity rose $41bn. BTC–NDX correlation 0.09 / 0.50 / 0.22. | Q1b B6 |

**Prohibitions**

| Node | Panel items | Key numbers | Sources |
|---|---|---|---|
| N-11 / N-18 / N-43 / N-56 / N-58 | See §10 | See §10 | Q1b B1–B4; R2 executive scripts; E7 street-forecast audit (`results/E7_street_forecast_audit.csv`); Ilmanen et al. 2021, JOIM (https://www.aqr.com/Insights/Research/Journal-Article/How-Do-Factor-Premia-Vary-Over-Time-A-Century-of-Evidence) |
| N-49 methods | PC-P-09/28 | Real-time Markov switching: 16.9 switches a year, 49% false. Complexity timing ρ 0.93. | Shu–Yu–Mulvey, arXiv 2402.05272 (https://arxiv.org/html/2402.05272v3); Gu–Kelly–Xiu (https://dachxiu.chicagobooth.edu/download/ML.pdf); Chen–Pelger–Zhu (https://economics.yale.edu/sites/default/files/deep_learning_in_asset_pricing.pdf) |
| N-31 textbook relations | PC-P-14, PR-P-16/17 | Okun −0.407 → −0.05. Phillips +0.04 (2011–25). Sacrifice ratio 5.5 implied vs −1.57 realised. | Ball–Leigh–Loungani, NBER w18668 (https://www.nber.org/system/files/working_papers/w18668/w18668.pdf); Hazell et al., NBER w28005 (https://www.nber.org/papers/w28005); Q1a A3, A4 |

**Corrected anchors (N-60).** Use these values and no others:
- D&M *JFE* 2016, Table 7: **0.682 → 1.041 → 1.194** (1934–2013).
- Ilmanen et al. out-of-sample declines: value **−49%**, momentum **−23% (n.s.)**, carry ≈ −25%, multifactor −18%.
- KOSPI closing peak **9,114.55 on 22 Jun 2026**; Q3-2026 **−19.33%**; peak-to-trough −38.6% in 27 sessions.
- BoK base rate **3.00%** (27 Aug 2026 vote 6–1).
- US 10y **5.29% = highest close since May 2002** (not "19 years").
- Brent $127 / $114 are Dated spot; front-month futures were $118.35 / $102.59.
- Taylor gap: −0.89 pp (central), not −1.4 pp.
- AMP Japan: momentum 0.13, value 0.77.
- RMW β t-statistic: HAC −3.0.

**QUANTGEN codebase and governance sources (v1.1)**

| Item | Key facts used | Source |
|---|---|---|
| Application map and target architecture | Flet app (`main.py`); `core/ficc` {curves, swaps, bonds, fx, ratesim, structured, macro, insights, data}; `core/quant` {history, garch, montecarlo, risk, optimize, signals, backtest, insights, gsq}; `core/engine` {runtime DISARMED→ARMED→HALTED, feed, evaluator, orders = simulated order book with no broker path, state}; `core/rules` {model, validation, store}; `core/skills` {72-entry manifest, runner, workflows}; `core/markets`, `core/calendars`; `config.py`; providers; `tests/run_all.py` hermetic; `docs/` | AR §1.1 |
| Vol backtest gate B5 | Rolling-origin VaR95 exceedance within ±2 binomial SE of 5% over ≥ 200 origins and PIT uniformity; GJR only if it passes | AR B5, B8, §4.1 |
| Read-only, timing, costs, gate | No order path; decide at the close of t, earn from t+1; per-side costs KRX ETF 3 / KRX stock 35 / US via KIS 50 / crypto 10 / futures 5 / FX 10 bp, all at 2×; nine steps; four verdicts; REVISE fixes | PP "Three rules", "The gate", "Fixed settings" |
| Strategy Lab record and E1 | 34 cards: 5 PASS / 11 REVISE / 18 REJECT / 0 INSUFFICIENT DATA; E1 OOS Sharpe 0.84 [0.47, 1.20] vs 0.95, p 0.75, max DD −15% vs −27%, kept as a descriptive sleeve | PP "The record", "Card E1" |
| Quant Lab self-grading | GARCH-t on SPY: 6.6% breaches, PIT p 0.003 → REJECT; GJR 6.6%, PIT p 0.014; skewed-t 5.2% (SPY), 6.3% (KODEX 200), 5.8% (bitcoin), withheld | PP "The lab grades itself" |
| Net-of-cost and strict-timing golden values; protective checks; B5-style estimator check | See §9.3 and §8.9 | R4b (`scripts/r4b_golden_net.py`) |

*End of specification.*
