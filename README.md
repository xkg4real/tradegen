# TRADEGEN

TRADEGEN is the trading program split off QUANTGEN on 2026-10-23, as a byte copy
of all 959 files. QUANTGEN stays pure quant research that goes no further than
paper trading. TRADEGEN is where trading for the owner's own account is designed,
inside Korean law.

- **Status (2026-10-23): no order path exists.** Everything after the line below
  is inherited QUANTGEN text and still describes this copy: read-only data
  clients, the simulated engine and the P0 read-only guards. Those guards are
  retired only through TRADEGEN's own safety design: a Korean compliance gate,
  execution the owner arms per session, hard loss limits, a kill switch and an
  order audit log.
- **Not legal, tax or investment advice.** The software and its author are not a
  licensed advisor.
- **Honest odds.** Turning $30 into $30,000 in a month has at most about a 0.1%
  chance in theory, and realistically 0.01% or less. Every plan must show its
  P(reaching the target) and its P(losing the stake).
- **Lawful set.** This is research, not legal advice; see
  `reports/Korean resident trading venue legality.md`. Prediction markets are
  unlawful for Korean residents, so GrokBot (`grokteam/`) and the LAZYOWEN
  accounts stay paper and research only.
- **Frozen studies are QUANTGEN's.** Both one-look readouts belong to QUANTGEN:
  the GrokBot forward look and the paper_live H2 holdout. Its baseline is
  `eacd57d`, which QUANTGEN tags `studies-of-record-2026-10-23`. Here
  `grokteam/` is permanently blinded: it never lists, fetches, replays or prints
  an event decided after the freeze, and it cannot re-freeze.
  `REPLAY_HOLDOUT=1 python -m paper_live.replay` is refused. Never restore
  `grokteam/out/frozen_book` over `grokteam/book.py`: the frozen copy unblinds
  the look and caches under `~/.nextgen`.
- **State.** Mutable state lives in `~/.tradegen` (move it with `TRADEGEN_HOME`),
  never in QUANTGEN's `~/.nextgen` or its repository folder.
  `config.refuse_quantgen()` refuses any path inside either. It checks both the
  resolved path and file identity, so `\\?\`, UNC and junction aliases are caught
  too. It runs in the path resolver, in every ledger and governance-log writer,
  and on `--macro-dir`. The overrides are `TRADEGEN_MACRO_DIR`,
  `TRADEGEN_TRADING_DIR`, `TRADEGEN_RUNS_DIR`, `TRADEGEN_FICC_CACHE`,
  `TRADEGEN_GROKTEAM_DATA` and `TRADEGEN_GROKTEAM_LEDGER_DIR`. QUANTGEN's state
  variable names are ignored.
- **Seeded ledgers.** `~/.tradegen/macro/ledgers` started as a byte copy of
  QUANTGEN's GROKTEAM-BOOK, LAZYOWEN, C3, QG-CORE and QG-TACTICAL families (50
  rows, 2026-10-23). TRADEGEN appends fork those hash chains. Its global N counts
  QUANTGEN's earlier trials, and their rows are UNVERSIONED, so step 3 refuses a
  card whose span they touch.
- **Shared keys.** `.env` is still a copy of QUANTGEN's, so both programs share
  one KIS app key, its token issuance and its rate limit, plus the FMP, OpenDART,
  KRX and Anthropic quotas. Give TRADEGEN its own keys, or blank the ones it does
  not need yet.
- **Python.** Use `.venv` (3.13, with numpy 2.3.5, scipy 1.18.0 and pandas 2.3.3,
  pinned in `constraints.txt`). Never `pip install` into the global Python:
  QUANTGEN's frozen studies pin it.

---

The upgraded, personal-use successor to NEXTGEN. Same body — the rule engine,
simulated order book, KRX data layer, and skill cockpit all survive intact —
with the one organ the client build was contractually forbidden from having:
**an opinion**. QUANTGEN computes analysis, ranks outcomes, and recommends. On
the macro overlay it recommends only what a frozen gate has passed, and today
nothing has: see
[Macro integration](#macro-integration-quant-council-specification-v20).

Version 2 widens the desk. The equity surfaces (Quant Lab, Portfolio, Signals)
stay as they were; five FICC surfaces now sit first in the rail, built for the
world the OTM FICC & Quant curriculum lives in — rates and FX derivatives,
treasuries and credit, pricing, structuring, and the weekly rates/FX strategy
read.

Version 3 widens the asset coverage and adds the gate that decides what is
offered. Four surfaces — **Derivatives, ETF, Crypto, Strategy Lab** — sit on
the KIS asset domains the stock-account key already quotes (ETF NAV, KOSPI 200
futures and options, KTB and USD futures, KRW benchmark yields, overseas
prices) and on keyless Upbit / Binance / CoinGecko data. Every strategy and
distributional model was validated on real history by one pre-registered
gate; what failed is shown as a refusal, not hidden. See
[The expansion surfaces](#the-expansion-surfaces-version-3).

The macro integration builds the Quant Council's Macro Integration
Specification v2.0 into the desk: a risk-sizing overlay with point-in-time
data, per-book risk states, model cards and a gate package that is frozen
before any card runs. Macro sizes risk and never sets direction; nothing
exceeds 1.0×; nothing places an order. Beside it sits the tech-fund research
register. Both live inside the Macro page; neither added a rail entry.

This is a personal instrument, not a client deliverable. It is not for
commercial distribution, and every trading decision it informs remains the
operator's own.

---

## The FICC surfaces

### Macro — the sheet, the descriptive read, the reports, the v2 views

A view selector at the top of the page switches between **Macro sheet** (the
default, described here), **Overlay state**, **Model cards** and **Research
register** (see [Macro integration](#macro-integration-quant-council-specification-v20)
and [Tech-fund research register](#tech-fund-research-register)).

Eighteen cross-asset indicators (2y/10y/30y, 2s10s, 10y real and breakeven,
SOFR and Fed funds, IG and HY OAS, the broad dollar, EUR/JPY/KRW fixings, VIX,
WTI, the 10y note future, gold), each with 1d/1w/1m/3m changes, a one-year
z-score and percentile. A descriptive read on top — curve (bull/bear steepener
or flattener, parallel), risk (VIX and HY OAS z-scores), dollar, inflation,
real rates — labelled "Descriptive read — not a regime model (P19)": it is
threshold rules on z-scores and 20-session changes, it feeds nothing (no book,
no signal, no engine), and it is never shown beside the v2 volatility labels.
The z-score colouring is display only. Two buttons write the club's homework:
**Daily market commentary** and **Weekly rates/FX strategy** — a local
narrative immediately, and the Claude deep read with a strategist's report
format when a key is set.

### Rates — curve, swaps, swaptions, short-rate simulation

| Tool | What it does |
|---|---|
| **Yield curve** | Bootstraps the Treasury par curve to continuously-compounded zeros, fits Nelson-Siegel or Svensson, reports 2s10s / 5s30s / 3m10y / the 2-5-10 fly / 1y1y / 2y1y / 5y5y, names the shape and the 20-session regime, and runs PCA on daily curve changes (level, slope, curvature with explained variance) |
| **Swap pricer** | Par rate, PV, DV01 and key-rate DV01 for spot or forward-starting swaps (`10y`, `5y5y`), carry and roll-down, the forward-rate table |
| **Swaption / cap-floor** | Black-76 (lognormal) and Bachelier (normal) with premium in currency and bp of notional, delta, gamma, vega, theta, and the implied vol in the other model; caps and floors as caplet strips |
| **Rate simulation** | Vasicek, CIR and Hull-White calibrated on SOFR (OLS on daily changes; HW's θ(t) fitted to the live curve), seeded paths, the terminal distribution, and the horizon P&L distribution of a bond or swap revalued on each path's model curve |

### Bonds — price, risk, scenarios, hedge

Price ↔ yield, Macaulay and modified duration, convexity, DV01, key-rate DV01
across the nine key tenors, z-spread to the curve, carry and roll-down with the
breakeven move. Nine curve scenarios revalue the bond in full (parallel ±25/±100,
bear/bull steepeners and flatteners, the 2-5-10 fly) so convexity shows up as
the asymmetry it is. A futures hedge ratio from position DV01, CTD DV01 and the
conversion factor.

### FX — forwards, options, smiles, carry

| Tool | What it does |
|---|---|
| **Spot, forward & carry** | Covered-interest-parity forwards and points from the two funding rates (pulled live: SOFR, ECB deposit rate, SONIA, and the OECD monthly series for the rest), carry for the position, and the implied cross-currency basis if a market forward is supplied |
| **Option & smile** | Garman-Kohlhagen with spot and forward delta, gamma, vega, theta, both rhos, vanna and volga; strikes from deltas; a smile built from ATM / 25Δ risk reversal / 25Δ butterfly quotes and fitted with Hagan's SABR |
| **Carry basket** | G10 + KRW versus USD: carry, realised vol, carry-to-vol and momentum per currency, and a long-top-3 / short-bottom-3 backtest that ranks on rates known at *t* and earns from *t+1* |

### Structuring — the pitchbook, with the hedge

Four products decomposed into legs and priced off the same curve and option
engines: **principal-protected note** (zero + participation in an ATM call),
**reverse convertible** (bond + short put, coupon solved for the issue price),
**dual-currency deposit** (deposit + short FX option, enhanced yield and the
conversion strike), and **steepener note** (coupon on the 10y–2y forward
spread, priced off forwards with a loud note that it carries no convexity
adjustment). Every product reports fair value against issue price, the
distributor margin, its Greeks, a payoff chart, and a hedge sheet sized in
spot, vanillas, swaps and futures.

### Conventions the whole FICC core shares

Rates, spreads and vols are decimals in the core and percent or basis points
only in the UI. Tenors are years; `3m`, `10y`, `5y5y` all parse. Zeros are
continuously compounded, discount factor `exp(−z·t)`. Day count is ACT/365
simple. **Single-curve**: one curve projects and discounts, so a floating leg
at inception is `N·(DF(start) − DF(end))`; an OIS-discounting upgrade slots in
behind `YieldCurve` without touching a caller. DV01 is currency per basis
point for the stated notional, positive for a long bond or a payer swap that
gains from higher rates. Every random draw is seeded.

---

## The equity surfaces

### Quant Lab — Monte Carlo simulation

Names a symbol, calibrates on daily history, and draws thousands of forward
paths under one of four models:

| Model | What it assumes | When it's the right one |
|---|---|---|
| **GARCH(1,1)-t** (default) | Volatility clustering (ω, α, β fitted by L-BFGS-B maximum likelihood) with Student-t innovations; the tail is fitted as 1/ν on [0, 0.4], so the normal (1/ν = 0) is nested and the "LR t vs normal" statistic is never negative, with its 5 % line at the boundary-mixture value 2.706. The mean is the sample mean, fixed. Simulated innovations are bounded at ±`Z_BOUND` (a t draw beyond it is redrawn from the t restricted to the bound), because an unbounded t gives the price no finite mean; the bound was chosen by `docs/bounded_innovation_sweep.py`. Every fit carries its precision: 95 % Wald intervals for α, β and the persistence from the observed information (the half-life interval is the persistence one mapped through), a profile-likelihood interval for ν that reaches "normal" exactly when the LR tile is below 2.706, "SE undefined" with the reason when the information matrix fails, and a chip naming every interval that reaches a bound; the unconditional vol gets no interval because the delta method was measured to cover 42–100 % depending on persistence (`docs/B2_FIX_BULLETIN.md`) | The baseline: today's conditional vol, where it settles (unconditional), the half-life in sessions, and the tail — with every guardrail (not converged, near-integrated, ν at a bound) said out loud |
| **GBM** | Lognormal returns at the sample drift and volatility | Smooth regimes; the benchmark GARCH is tested against (LR, ΔAIC) |
| **Jump diffusion** (Merton) | Diffusion plus Poisson jumps, calibrated from the sample's >3σ days | Names with gap risk — earnings, headlines |
| **Block bootstrap** | Nothing — resamples actual return blocks | When the empirical distribution (fat tails, clustering) is the point |

Every run is seeded and reproducible. Results: percentile fan over history,
terminal distribution, horizon VaR/CVaR, probability of loss, probability of
reaching a target, and for GARCH the conditional-vol path against realised vol.

**Drift is an assumption, not a calibration.** An out-of-sample study on
17 instruments over 2005–2026 (`docs/drift_study/`) found the trailing
two-year sample mean has a correlation of −0.01 with the next year's return
and loses to a flat zero at every horizon. Every model therefore draws
zero-mean shocks and adds one of four stated drifts, shown with its
arithmetic on the result:

| Drift | μ (annualised log) | Use |
|---|---|---|
| **Risk premium** (default) | rf + ERP, minus each model's exact per-step convexity correction | The forecast view; rf is the live 3-month T-bill from FRED, ERP is your assumption (4% equity, 1% bonds/gold, 0 FX). The mean path grows at rf + ERP under every model |
| **Zero** | 0 | The stress view; nothing beats it significantly |
| **Risk-neutral** | rf, minus the same per-step correction | The pricing measure the structuring pages use; not a forecast. The discounted price is a martingale under every model, including GARCH-t |
| **Sample mean** | mean daily log return × 252 | Kept for transparency; labelled noisy (standard error ≈ σ/√2 on two years) |

The per-step correction c_t = ln E[exp(shock_t)] is ½σ² of the sample variance
for GBM (the lognormal correction), the diffusion half-variance plus the jump
compensator for the jump model, the increments of the empirical block log-MGF
for the bootstrap, and c(σ_t) from each path's own conditional variance for
GARCH-t, tabulated once per (ν, bound). The result reports the effective log
drift, the horizon-average correction, and the arithmetic in words.

**Self-grading (v2, M9).** A strip of PASS / FAIL / NOT RUN chips grades the
lab's own tails: Kupiec, Christoffersen conditional coverage, ES 97.5 % (Z2),
the Basel zone and the fan PIT, from `core.quant.lab` (expanding-window fits,
FHS / GPD tails). `python docs/quant_lab_grading.py --smoke` writes the SMOKE
run to `docs/quant_lab/` (vendor data, gates nothing); the formal grading
refuses (exit 2) until KRX official KOSPI closes (F01) or a listed `^KS11`
file (F13) are in the fixture manifest.

The primer `docs/QUANTGEN_Models_Primer.pdf` explains every model, the
maximum-likelihood fit, each guardrail, and the drift study.

### Portfolio — Markowitz, risk parity, the frontier

Aligns histories on shared dates, then solves all four objectives — max
Sharpe, min volatility, risk parity, equal weight — so the frontier chart can
mark them against each other and against a 1,500-portfolio random cloud, with
weight and risk contribution per asset side by side.

### Signals — the technical read, and the backtest that keeps it honest

A weighted composite of six components with each component's reason and its
dissent visible, above a costed backtest of the same idea against buy-and-hold.
Signals are computed on close *t* and earn returns from *t+1*. The page
carries the notice "Context only — not a v2 signal (DO-NOT-BUILD TF-12).
Nothing here feeds a book."

---

## The expansion surfaces (version 3)

Design and build record: `docs/ASSET_EXPANSION_SPEC.md`. Research:
`reports/QUANTGEN asset coverage expansion.md` and
`research_notes/QUANTGEN asset coverage expansion/`. Plain-language companion:
`docs/QUANTGEN_Expansion_Primer.pdf` (built by
`docs/build_expansion_primer.py` from the study's cards, citing the operator's
own study materials).

### Derivatives — the KOSPI 200 surface before any strategy

The nearest expiry quoted series by series from the keyless KRX master (the
board endpoint stops at its top 100 strikes): futures basis and cost-of-carry
fair value against KIS's theoretical price, the parity-implied forward,
Black-76 inversion of every two-sided quote against KIS's implied vol, put-call
parity residuals, butterfly and vertical arbitrage counts, a raw SVI smile with
the Gatheral–Jacquier g(k) check, the Cboe model-free implied variance, the
Breeden–Litzenberger risk-neutral density and the empirical pricing kernel
against the Quant Lab's GARCH-t terminal density, the box-spread implied KRW
rate, and a delta-hedging P&L simulation (GBM or GARCH-t) that reports the
gamma-weighted break-even volatility. A board captured with the market closed
is last prints struck at different moments: the page says so in red, measures
time to expiry from the last session, and marks every figure indicative.

### ETF — NAV, basket, drag, sleeves

KIS NAV and premium with its ADF and half-life, the constituent basket,
leveraged-fund drag from the Avellaneda–Zhang identity at the last quarter's
realised variance (the study's better reference) and at the GARCH-t variance
term structure, and the trend-switch and vol-target sleeve rules on the fund's
own history — every one with the validation study's verdict beside it.

### Crypto — read-only, keyless

Kimchi premium (Upbit KRW-BTC against the world price at the FRED fixing) with
ADF, half-life and a predictive test; perpetual funding carry with deciles and
a bootstrap; a six-component regime score whose missing components redistribute
their weight; GARCH(1,1)-t on bitcoin with its out-of-sample verdict and the
stationarity share; the ETH/BTC unit-root test; the weekday table; optional
Upbit balances with an asset-inquiry-only key. Refused by construction: any
order, withdrawal, transfer or deposit-address path on any venue; private keys,
seed phrases and wallet secrets; transaction signing; accounts on unregistered
foreign exchanges; the ccxt / web3 / pyupbit dependencies; tax computation.

### Strategy Lab — the scorecard and the families

Every model card of the study (`docs/asset_expansion/cards/*.json`) with its
plain-language test lines, decision and reason; and every strategy family
(trend switch, vol target, cross-sectional momentum, TSMOM, pairs, crypto
trend, risk parity) runnable on any symbols and source through the same gate.
The v2 macro cards are not in this directory: they live under
`docs/macro_overlay/` and show on Macro → Model cards, which a one-line notice
on this page points to.

### The gate

`core/quant/validate.py`, pre-registered and changed nowhere else: purged
walk-forward (IS 756 / OOS 126 sessions, embargo = holding period) on a T × G
P&L matrix; annualised Sharpe with Lo's standard error and a studentised
circular block-bootstrap 90 % interval; the deflated Sharpe ratio for every
trial ever run; PBO by CSCV read together with the probability that the
in-sample winner loses out of sample (PBO is 0.5 by construction on a flat
plateau); OOS/IS; a paired block-bootstrap test against the benchmark when the
claim is "beats"; positive-year share; survival at 2× pre-registered costs
(KRX ETF 3 bp, KRX stock 35 bp, US via KIS 50 bp, crypto 10 bp, futures 5 bp,
FX 10 bp per side; one source, `COST_BP_PER_SIDE`); the parameter plateau and
edge; a regime split; the McLean–Pontiff haircut. Distributional models:
Kupiec, Christoffersen, the Basel traffic light, 90 % coverage, PIT (KS, χ²,
Berkowitz, DGT correlograms), QLIKE against EWMA with Diebold–Mariano.
Decisions PASS / REVISE / REJECT / INSUFFICIENT_DATA (displayed "INSUFFICIENT
DATA"), each line stating the number, the threshold and the sample. The v2
macro cards add the statuses listed under [Statuses](#statuses).

### What the study decided

`docs/asset_expansion_study.py` runs 34 cards on real history and writes
`docs/asset_expansion/results.md`, `results.csv` (md5-stamped on every card)
and `cards/*.json`; `--only id1,id2` re-scores a subset and merges. The run of
record (`docs/asset_expansion/manifest.json`, 2026-09-27, seed 11) decided
5 PASS / 11 REVISE / 18 REJECT. The substantive findings, each on its card
with the numbers:

* **Offered as a signal**: the crypto trend rule on KRW-BTC (PASS: every
  criterion, beats buy-and-hold at p 0.038, survives 2× costs) and on BTC-USD
  (PASS: every criterion, off the grid edge, beats buy-and-hold at p 0.07
  against the 0.10 the claim needs). The Sprint 7 CRY-1 trials re-examined the
  KRW-BTC card; see [Tech-fund research register](#tech-fund-research-register).
* **Offered as monitors**: funding carry (the BIS sign confirmed), the weekday
  table (no return effect, a weekend-volume cost input), the futures basis
  (reconciles with KIS's theoretical price within the dividend band), the
  kimchi premium, the PCA fly, the LETF drag at realised variance.
* **Rejected, and shown as rejected**: the ETF trend switch (protects the
  drawdown, does not beat buy-and-hold on Sharpe), capped vol targeting (the
  Cederburg real-time result — this study's cards on SPY and KODEX 200 at its
  own costs, not a refusal of vol targeting in general and not the Council's
  MACRO-R06 cards, which are listed under
  [Card status](#card-status-as-of-this-build)), unlevered risk parity, sector
  momentum after 50 bp, futures TSMOM on Yahoo continuous contracts, the pairs
  trades (the gold pair and Hyundai/Kia fail the deflated Sharpe; the Samsung
  common/preferred tilt does not beat holding both legs; the KODEX/TIGER
  tracker pair is REVISE because its 1-session half-life is bid-ask bounce
  that loses at 2× costs), the VIX roll-down, G10 FX momentum, dollar carry,
  the Diebold–Li forecast (0/5 maturities beat the random walk), the ETH/BTC
  pair.
* **Volatility fans**: the app's symmetric GARCH-t under-covers the 5 % left
  tail on SPY and KODEX 200 (6.6–6.8 % of days); a GJR leverage term does not
  change the breach count, a Hansen skewed-t innovation does (REVISE on the
  PIT test only, on SPY). Bitcoin's variance is near-integrated in most
  windows, so every bitcoin fan reads REVISE. The Quant Lab shows the measured
  breach rate and the skewed-t verdict beside every fit.

Two harness defects found by the second run and fixed before the third are
recorded in the spec: an "edge" was counted on two-value grid axes, and PBO
alone rejected flat plateaus.

---

## Macro integration (Quant Council specification v2.0)

The Macro Integration Specification v2.0 (Quant Council edition) adds a macro
risk overlay to the desk, built as modules M0–M10: the rules store and the
artifact schemas (M0), the point-in-time data layer, input contracts and
effective-dated calendars (M1), the risk layer with `min()` composition (M2),
the volatility-estimator harness (M3), the factor sleeves (M4), the per-book
engine runtime, look-through caps and the simulated fill model (M5), the
context log and the break trigger (M6), the model cards and the gate package
(M7), forward records, FORWARD-SIM and refusal books and the `macro_daily`
workflow (M8), the Quant Lab self-grading and the scenario library (M9), and
the deferred crypto clock and FX instrument check (M10). Macro sizes risk and
never sets direction; no multiplier anywhere exceeds 1.0×; nothing places an
order.

All panel members in these documents are simulated, fictional composites; nothing speaks for any real firm or person.

Not investment advice: QUANTGEN is a read-only research desk with no order path.

Where it lives:

| What | Where |
|---|---|
| Specification, 129 build tasks, backlog | `QUANTGEN_Quant_Council_2026-10-03/claude_code/` (read in place) |
| The two reports | `reports/QUANTGEN_Quant_Council_Report.md`, `reports/QUANTGEN macro overlay research.md` |
| The two offline pages | `docs/council/QUANTGEN_Quant_Council.html`, `docs/council/QUANTGEN_Macro_Neural_Link.html` (open in any browser, or from Macro → Research register) |
| Rules store (read-only, version 2.0.0) | `data/macro/rules_v2.0.0.json`; series registry `data/macro/series_registry.yaml`; calendars `core/calendars/data/` |
| Code | `core/ficc/` (`pit`, `contracts`, `lag_audit`, `macro_schema`, `macro_artifacts`, `context_log`, `schemas/`), `core/calendars/`, `core/quant/` (`risk_layer`, `vol_estimators`, `forecast_eval`, `sleeves`, `gate_stats`, `gate_ledger`, `cardp`, `gate_package`, `cards`, `instruments`, `forward`, `forward_sim`, `refusal`, `lab`, `scenarios`), `core/engine/books.py`, `core/rules/macro_rules.py`, `core/rules/governance.py`, `core/skills/pipeline.py`, `core/skills/macro_daily.py`, `core/skills/alerts.py` |
| Macro model cards | `docs/macro_overlay/` (`headers/`, `cards/`, `cards/verdicts.jsonl`, `archive/`); runner `docs/macro_overlay_study.py` |
| Mutable state (never in the repo) | `~/.tradegen/macro` (override with `TRADEGEN_MACRO_DIR`): artifacts, books, alerts, run log, governance log, family ledgers |
| Build record | `research_notes/QUANTGEN v2 integration map/` (coordinator rulings, design brief, sprint logs) |

### Status: indicative, nothing formally run

Every verdict and number in the two reports and the two pages is indicative: a
full-sample computation under the specification's thresholds, never a run of
QUANTGEN's own gate. The gate package is built and unit-tested on synthetic
panels and is frozen whole before any card runs — and it is not frozen here
(`gate.package.status = NOT_FROZEN`). The freeze needs the gate-acceptance test
(at most 10 % of 300 circular-shift placebos per family may pass, named
negative controls must fail, one bounded redesign), which needs reference data
that is not on this machine, and a repository under git. No forward record can
raise a verdict. Only PASS and BUILD-AS-INSURANCE cards reach the recommended
book; until a macro card runs formally, the displayed recommendation carries
only the invariants — point-in-time data, the bounds, the Korea caps, the
drawdown ladder and the hedge state (vt enters the recommended book as 1.0
with status `not_run`). Missing owner inputs are typed nulls that fail closed
and are listed under "Open owner actions" on the Macro page.

### Principles P0–P10

**P0. Read-only by construction.** No module of the macro package contains,
imports or calls an order, cancel, withdrawal, deposit-address or transfer path
on any venue; KIS is used for read-only quotations only. Every output is an
artifact, an entry in the simulated order book, a costed backtest or
forward-simulated book, a model card or a displayed exposure recommendation,
and a displayed recommendation may come only from PASS cards (P7). Every other
card is computed, logged and shown as a descriptive sleeve labelled with its
verdict. Static scans (T-RO-01, cockpit test_08 / test_09) hold the line.

**P1. Macro scales risk; it never generates direction.** No macro or overlay
module creates, flips or closes a simulated position on its own. Overlays
output multipliers only; direction comes from the signal families and the
existing composite. Every acting rule states a second-moment mechanism on its
card, and using the level of a stress variable as a mean gate is a principle
change that goes to the owner (D3).

**P2. Bounded multipliers, composed by `min()`.** Overlay multipliers lie in
[0.5, 1.0] and compose by `min()`, never by product:
composed = vt × min(1.0, overlays…, ladder, post_rearm_cap), then
gross = min(composed, concentration bound). Outside HALTED, composed ≥ 0.5 × vt
(a binding concentration bound may take gross lower; that is logged, not a
bounds failure). Vol-target and vol-scale weights lie in [0, 1.0] with no
floor, and the vol-target cap of 1.0 is permanent. No multiplier anywhere may
exceed 1.0: the rules store refuses such a rule and `compose()` raises. 0×
comes only from the risk layer — a book's own HALT.

**P3. Stress variables feed sizing, annotations and event blocks; never
means.** VIX term structure, credit, oil, EPU and USD-down-with-equities enter
only through the volatility estimator (behind the staged estimator gate,
R-30), execution-state annotations that change no weight (R-08), new-entry
blocks for scheduled events (R-10), the event calendar, and the Monte Carlo
and historical-replay scenarios (R-16). They are never mean gates and never
cut-and-re-add triggers on existing exposure.

**P4. Korea's risk inputs are local.** Korea gross is driven by KOSPI's own
volatility, concentration and, later, leverage state. US or global macro states
never gate Korea gross; US overnight information enters Korea only as an
opening-gap and volatility input, and the KOSPI trend state is context only
(R-28 has no Korea instance).

**P5. Everything is point-in-time. Decide at the close of day t; earn from day
t+1.** Every datum carries UTC observation, `available_at` and `retrieved_at`
timestamps and a `value_status`. The decision time is the official close of the
decided market from the effective-dated calendar (the close-print bound,
scheduled close + 30 s); a datum enters a decision only if it was available by
then, and the resulting weight earns from the next session. A close-type acting
input must be an `official_close` of the decided session — a provisional
intraday row is a missing input. Lags are calendar-based. Missing, stale,
provisional or synthetic inputs fail closed by role: an acting input leaves the
state unchanged and raises an alert, a risk-model input switches the hedge
credit off, a context input is labelled. Nothing is interpolated and no
synthetic value ever acts.

**P6. Thresholds on changes or percentiles.** Thresholds are defined on
changes or on expanding / trailing percentiles, never on levels calibrated to
today.

**P7. The gate decides.** Every overlay rule that changes exposure is a model
card and passes the nine-step gate (protective rules use the protective
class). Only PASS cards feed the displayed recommendation: a CARD-O PASS as a
recommendation, a CARD-P PASS as insurance (BUILD-AS-INSURANCE). FORWARD-SIM
cards run forward in the specification book, specification-only factors are
labelled with their verdict, and refusal books are display-only and read by no
other book. Nothing becomes a recommendation because a backtest looks good, and
a rejected card is not deleted.

**P8. Every multiplier declares its exposure basis.** `active` scales a
family's long/short or benchmark-relative risk; `total` scales the market
book's gross long exposure. Every multiplier says which.

**P9. Slow macro is context.** Sahm, the yield curve and probit, Taylor
residuals, real yields, term premium, breakevens, credit levels, survey data
and the Street's and the Fed's projections are logged daily in the context log
and never act. So is every indicator of the 18-indicator macro sheet that is
not an acting input, and the v2 context additions (leverage and flow monitors,
VRP, live implied-vol snapshots, turbulence). Acting on any of them requires a
new card.

**P10. Pre-registered costs, always, with a floor.** Every backtest,
forward-simulated book and golden value is charged QUANTGEN's per-side costs
(KRX ETF 3 bp, KRX stock 35 bp, US shares via KIS 50 bp, crypto 10 bp, futures
5 bp, FX 10 bp) on every unit of turnover and is also shown at 2×. The rates
are defined once, in the gate. A tick floor can only raise a cost:
cost_side = max(table rate, commission + ½·tick/price + tax_side), so 252670
at ₩69 is charged at least 72 bp per side. A card declares its instrument book,
notional, rebalance rule and no-trade band before it runs; a different
instrument book is a new card. Lowering a cost is never a permitted fix.

P11–P19 are the council's red lines, adopted as principles (one gate package,
adopted once and blind; a single path neither promotes nor rejects; every
selection is counted; forward months are falsification alarms, never
validation; verdicts are book-specific; nothing may freeze or quietly shrink
the book; no exposure path the gate never sees; no acting decision on a
provisional, intraday or stale input, and no risk-model-only input can HALT;
no regime-model state, acting or displayed). See section 1 of the
specification.

### Where it shows in the app

Inside the Macro page, through its view selector (no new rail entry):

* **Overlay state** — a Market selector and an Artifacts selector (Live =
  the macro directory, Dry run = its `dry_run/` sub-directory); per market: the
  run chips (market, decided session, run mode, read-only, data snapshot), one tile per book (`recommended:<m>`,
  `specification:<m>`) with its engine state, `composed`, `gross` and binding
  factor, a HALT banner under any HALTED book until it is acknowledged, the
  composition line printed with its numbers beside the multiplier bar (fill at
  `composed`, ticks at `vt` and at the 0.5 × vt floor, cap 1.0 drawn), the
  overlays table, the vol strip with the two volatility labels marked "display
  only", the flags, the alerts with Acknowledge, the inputs table, the open
  owner actions and decisions, the context log and the event calendar
  (collapsed), and the provenance footer. No artifact: an empty state with the
  dry-run button. An invalid or quarantined artifact: an error notice and no
  numbers.
* **Model cards** — every macro card with its verdict chip, disposition chip,
  reason code and label verbatim; refusal and FORWARD-SIM books in their own
  group, "not a recommendation"; the gate package status; the tech-fund card
  drafts (NOT RUN, with their reasons) and the CRY-1 control results under their
  vendor-data label.
* **Research register** — see
  [Tech-fund research register](#tech-fund-research-register); buttons open the
  two offline council pages.

Every view re-reads its artifacts on its own Refresh; long work runs off the
UI thread. The UI renders validated artifacts only and never computes
exposure.

### Card status (as of this build)

Every macro card is NOT RUN. The formal-run preflight
(`python docs/macro_overlay_study.py --preflight`) refuses, for every card:
`gate.package.status NOT_FROZEN` (the runner refuses before the freeze, P11);
`anchor UNVERSIONED` (the owner must place the repository under git); and the
R-34 positive control (fixture `KR_SOX_KRW_gate_B3`) not run because its
reference data is absent. Each draft header also lists its own typed nulls
(`python docs/macro_overlay_study.py` prints them: OWNER `notional_nav`, REFDATA
history files, the COUNCIL index list of R-14).

| Card | Class | Rule | Book | Verdict | Label and status |
|---|---|---|---|---|---|
| `MACRO-R06-KR-ETF` | CARD-P | R-06 | specification | NOT RUN | "Crisis-clustering insurance: reduces drawdown in volatility-clustering crises (1997–98, 2008, 2026); no help against gap shocks from calm states (2018-10, 2020-02, 2024-08); Sharpe non-inferiority is marginal — it pays a premium in calm decades (2016–25 alone: tail 0.95, ΔSR −0.079) and is short the post-crash rebound premium; not expected to outperform; cap 1.0 permanent." On current evidence the formal run is expected to return INSUFFICIENT DATA (`underpowered`), so the card is not expected to build: it stays a labelled control in the specification book, re-gated only when new history adds an objective episode; no forward-record route |
| `MACRO-R03-US-MOM` | CARD-O | R-03 | build now | NOT RUN | "indicative PASS; step 3 borderline" (0.98 at N_equiv 6.3; 0.947 at linear N̂ 12.6) |
| `MACRO-R04-US-DM` | CARD-O | R-04 | specification | NOT RUN | "step 3 FAIL (indicative)" (0.77): a floored heuristic, not the published rule; specification book only |
| `MACRO-R14-MULTI-TREND` | CARD-O | R-14 | build now | NOT RUN | no label until its index list exists (the 12-index list is not in the specification) |
| `MACRO-R31-KR-ETF` | CARD-P | R-31 | specification | NOT RUN | −8 % / −12 % ladder steps time-boxed at 21 sessions; specification book until PASS; the −15 % hard stop is a governance event |
| `MACRO-STACK-KR` | CARD-P | R-02 | specification | NOT RUN | the generated stack card for joining de-risk factors |
| `MACRO-R28-US-TREND` | CARD-P | R-28 | FORWARD-SIM | NOT RUN | "FORWARD-SIM until a US sleeve exists (D5)": protective-only monthly SMA10m, 0.5× below trend; never in the recommended book |
| `MACRO-R06-US-FUT` | CARD-P | R-29 | FORWARD-SIM | NOT RUN | "FORWARD-SIM pending the 1926+ settling run and D5": passes on 1990–2026 only on a knife edge (11 of 44 start dates) |
| `MACRO-R06-US` | CARD-P | R-06 | registered record | REJECT | "REJECT (instrument: US shares via KIS, 50 bp, daily)", `rerun: false`: a fact about trading it in single US shares at 50 bp, not evidence against vol targeting |
| `MACRO-R11-KR-KRW` | CARD-P | R-11 | refusal book | REJECT | "RETIRED: REJECT at every timing on KOSPI 1997-04 -> 2026-10 (refusal book, display only)" (council record, not reproduced on this machine) |
| `MACRO-R12-US-RATES` | CARD-P | R-12 | refusal book | REJECT | "RETIRED: REJECT at every timing and cost on US 1990-02 -> 2026-09 (refusal book, display only)" (council record, not reproduced on this machine) |

**FORWARD-SIM and refusal books.** `forward_sim:R-28` and `forward_sim:R-29`
(US decisions), `refusal:R-11` (KR) and `refusal:R-12` (US) are display-only
books. Their values reach `macro_state.forward_sim`, `macro_state.refusal_books`
and the `forward_sim[]` / `refusal[]` entries of each `overlay_decision`; they
are never an argument of a weight book's `compose()`, never feed the engine,
never sit in the same stat strip as the recommended book, and are always
labelled "not a recommendation". R-08 (VIX ≥ VIX3M) is an execution annotation,
not an entry block and not a multiplier.

### Statuses

Beside the four decisions of the existing gate:

| Status | Meaning |
|---|---|
| NOT RUN | No authenticated formal result. Never counted as PASS. Also a test status (below) |
| INSUFFICIENT DATA | Gate enum `INSUFFICIENT_DATA`, displayed with a space. Every verdict carries a reason code: `sufficiency`, `inconclusive`, `underpowered`, `do_no_harm`, `timing_fragile`, `stability`, `claim_not_shown`, `estimator_calibration`, or the failed check's id |
| UNVERIFIED | A claim or prior not yet checked (the Korea reversal prior; the app's GJR study until its script and seed are published) |
| BUILD-AS-INSURANCE | Disposition of a CARD-P on a formal PASS, shown as a second chip beside the verdict, with its insurance label. Not a fifth verdict |
| RECOMMENDATION / INVARIANT | A CARD-O PASS; an invariant step |
| SPECIFICATION BOOK | A labelled control: computed and shown in the specification book only |
| FORWARD-SIM · not a recommendation | Runs forward in its own book; never raises a verdict; never in the recommended book |
| REFUSAL BOOK · not a recommendation | A RETIRED REJECT kept as a display-only book that no other book reads |
| DISARMED / ARMED / HALTED, per book | Each book (`recommended:<m>`, `specification:<m>`, `forward_sim:<rule>`, `refusal:<rule>`, `card:<id>:<on\|off\|S>`) has its own runtime state. HALT class RISK (the book's hard stop or a risk limit): 0× for ten decisions, then an automatic re-arm with references reset and a 0.5 post-re-arm cap inside `min()` for the next ten. HALT class OPS (an acting input bound to that book failing repeatedly, its own artifact's validation, feed heartbeat): re-arms when the cause clears; lag-audit and acting-schema HALTs need an operator re-arm. Risk-model and context failures never HALT. The inherited Execution engine keeps its own single DISARMED→ARMED→HALTED state |
| Input statuses | `ok`, `warmup`, `disputed`, `stale`, `stale_missed_release`, `missing`, `provisional_rejected`, `session_mismatch`, `synthetic_rejected`, `fail_closed`, `not_run` |
| calm / normal / elevated / stressed | Volatility labels, display only; never gating, never a regime state |
| DRY RUN | "VENDOR DATA · DRY RUN · not an official close · not a card run" (see [Dry run](#dry-run)) |

Every chip carries its word; colour never carries meaning alone. DO-NOT-BUILD
entries (the council's items 1–37 and DNB-TF-01..17) are labelled harm, null or
inconclusive, never "refuted".

### Owner decisions D1–D6 (values in force)

| D | Subject | Value in force | Store key | Status |
|---|---|---|---|---|
| D1 | Korea concentration template | MSCI 25/50 (`msci_25_50`) | `risk_layer.korea_caps.template` | default |
| D2 | Hard-stop level | −15 % of book NAV from the high-water mark since the last re-arm | `risk_layer.drawdown.hard_stop.level` | default |
| D3 | Calm-state reversal down-weight | not adopted (P3 stands) | `families.reversal.calm_state_downweight` | default |
| D4 | Book-level false-demotion budget | ≤ 10 % a year | `monitoring.false_demotion_budget_per_year` | default |
| D5 | US sleeve | none until decided: R-28 and R-29 stay FORWARD-SIM | `sleeves.US.line` | pending |
| D6 | CDaR-guard calibration | the lowest-placebo-false-pass rule, frozen with the package | `gate.acceptance_test.cdar_guard.calibration` | default |

### Data limitations

* One price vendor. Korea history is Yahoo `^KS11`, a price index without
  dividends and without a second source before 2015; the formal Korea run needs
  KRX official closes.
* Not on this machine: KRX official KOSPI closes (F01), the French Data Library
  daily Mkt-RF / RF file from 1926 (HTTP 403 when the council tried), the French
  monthly file and trend indices, the KRX all-stock panel, and the other
  reference datasets the specification cites. Every golden, formal-run and
  out-of-sample clause that needs them is a test that reports NOT_RUN naming the
  missing file — never faked, never counted as PASS.
* The frozen package's data cut-off is KR 2026-10-02 and US 2026-10-01; later
  data enters only through a re-gate. The local vendor caches
  (`docs/asset_expansion/cache/`, Yahoo / FRED to 2026-09-25) feed the labelled
  dry run only.
* The calendar files are unsigned, so every live run refuses
  (`CalendarUnsigned`) and the missed-decision check at app start reports itself
  unavailable.

### Open owner actions

* Sign the calendar set (`core/calendars/data/*.yaml`, including
  `kr_regime_tags.yaml`).
* Place the repository under git (the freeze, header commits and the verdict
  filter refuse `UNVERSIONED`).
* Set `sleeves.KR.notional_nav` and `sleeves.US.notional_nav`; decide D5.
* For the US futures card: the Micro ES contract multiplier, the
  `nav_fx.conversion_instant` and the futures roll calendar; acquire and
  license the French daily 1926+ file for the settling run.
* Data providers: the KODEX 200 PDF basket, the 15:30 KST USD/KRW snapshot or
  ECOS 15:30 close, the KIS US 10y quote, SPX month-end closes, the KRX official
  closes and the KRX all-stock panel.
* Run the KIS quote-field check (`docs/kis_quote_check.py`, with KIS
  credentials, around the close).
* Deferred sleeves: a CRYPTO venue row and notional, the
  `FX_KRX_USD_futures` contract multiplier and roll calendar.
* Scenario library: the 2022 oil-shock t0 and the latest SEP Table 2.
* Tech-fund: register a KR momentum paper series for FS-2; rule on the
  proposals pending owner confirmation (XS-01..22, OQ-01..15).

### Dry run

The pipeline can be exercised end to end on the local vendor caches. In the
app: Macro → View "Overlay state" → **Run macro_daily** "Dry run (local vendor
data)" (the default) → **Run** (or the empty state's "Dry run (local vendor
data)" button); the view then switches its Artifacts selector to Dry run. The
"Live (needs KIS, signed calendars)" option stays disabled, its tooltip naming
what is missing.
From a shell:

```bash
python -m core.skills.macro_daily --mode dry_run                     # both markets
python -m core.skills.macro_daily --market KR --mode dry_run --macro-dir <scratch dir>
python -m core.skills.macro_daily --market KR --mode live            # refuses today: CalendarUnsigned (exit 2)
```

A dry run ingests `docs/asset_expansion/cache` as `vendor_close` rows (source
Yahoo / FRED), runs with `run_mode = backtest`, and writes its artifacts under
`<macro dir>/dry_run/` (`macro_state/`, `overlay_decision/`, `context_log/`);
without `--macro-dir` that is `~/.tradegen/macro/dry_run/`. Every artifact
carries `extras.dry_run` and is shown with the red chip "VENDOR DATA · DRY RUN ·
not an official close · not a card run". Books stay DISARMED (no acting input
is an `official_close`), the engine feed is blocked, and no verdict is ever
written. Exit codes: 0 ok, 1 run status not ok, 2 refused. Related runners:
`python docs/macro_overlay_study.py` (card listing; `--preflight` prints why a
formal run is refused), `python docs/techfund_study.py`, and
`python docs/quant_lab_grading.py --smoke`.

---

## Tech-fund research register

The R3 technical-and-fundamental signals programme
(`research_notes/QUANTGEN technical and fundamental signals/README.md`; source
bundle `QUANTGEN_techfund_research_bundle/`). Its integration specification was
never delivered, so the R3 register, weights, goldens, DO-NOT-BUILD list,
backlog, QA corrections and the coordinator's rulings are the binding text, and
the Council specification v2.0 governs every conflict. Nothing in it changes an
acting parameter of the macro package or feeds a book.

**Built (read-only data and libraries).** `data/techfund/` (15 shipped files
and a sha256 manifest: the weight tables, the go/no-go register G-01..G-77,
nodes and edges, goldens, pair-share series, and the DNB-TF, BL-TF, OQ, XS and
CA items) read through `core/techfund.py`, whose loaders refuse on a manifest
mismatch; the DNB-TF-01..17 predicates in the rules store
(`do_not_build.tf_items`); the backlog registry `data/backlog_registry.json`
(`core/rules/backlog_registry.py`); the screen, book and governance libraries
`core/quant/tf_screens.py`, `tf_books.py` and `tf_gov.py`; the card drafts
`docs/techfund/{SCR-1,SCR-2,FS-1..FS-5}.draft.json` with their runner
`docs/techfund_study.py` and the declared schema amendment
`docs/techfund/SCHEMA_AMENDMENT.md`; the scenario library
`core/quant/scenarios.py`; the DATA-6 investor-flow log
`core/ficc/flows_log.py` (context only; no provider wired).

**Card status.** Every KRX tech-fund card is NOT RUN: SCR-1, SCR-2, FS-2, FS-3
and FS-5 need the KRX all-stock daily panel 1995–2026
(`data/techfund/marcap/`, absent); FS-1 needs the KRX official KOSPI closes;
FS-4 is PENDING (no L0 composite card exists yet).

**Display only.** The weight table carries its caption: "Weights are 0-3 design
priors, not gate results; any weight of 2 or more still needs a PASS card
before it can feed the displayed book. Proposed normalisation base_weight =
w / 3 (never above 1.0x)." The `w / 3` column is the XS-21 proposal only; the
Council's base weights (`IV_m × 1/K_m`) govern. Also display only: the go/no-go
register, the RISK-1 pair-cap proposal (0.35 pair cap, 0.45 trigger, semis
≤ 0.50; Council D1 governs), the planning haircuts beside the Council values,
the factor-tilt threshold, and every open question and cross-spec amendment,
each shown as a proposal pending owner confirmation.

**CRY-1 controls.** The only runnable item ran as labelled trials on the local
vendor crypto caches ("vendor data, labelled trial, not a formal card run"),
each registered in the R-23 family ledger of card C3 (N 11 + 3 = 14): a
vol-scaled long-only control, a split at 2024-01-10, and an ETH replication;
the cut-time sensitivity is NOT RUN (no intraday candles). Against the control,
C3 on upbit KRW-BTC reads PASS (ΔSR +0.496, p 0.028) and on binance BTCUSDT
REJECT (ΔSR +0.182, p 0.243); after the 2024-01-10 split the Binance ΔSR is
−0.049 (p 0.586), which meets R3's "what would change it" condition and is
reported to the owner; the ETH replication is REJECT (SR 0.722 against
buy-and-hold 0.736, p 0.541). Card C3 keeps its stored PASS by ruling (D-24); a
Bonferroni note is printed, not applied. Results: `docs/techfund/cry1_*.json`.

---

## AI-generated analysis, two layers

Every result ends in an **Analysis** card:

1. **Local narrative** (always) — a deterministic written read of the computed
   numbers. No network, no key, and it never invents a number that wasn't
   computed upstream. The FICC narratives speak the desk's language: the curve
   regime in basis points, the swaption premium in bp of notional, the carry
   long and its funder with carry-to-vol.
2. **Deep analysis** (with `ANTHROPIC_API_KEY`) — the same structured payload
   goes to the Claude API for a generative read in the voice of a sell-side
   rates/FX strategist: cross-metric tensions, sensitivity, the trade
   expression, what would invalidate the view. The Macro page's two report
   buttons append a report format (headline, rates, FX, positioning with
   levels) to whatever question you attach.

Model defaults to `claude-sonnet-5`; override with `QUANTGEN_AI_MODEL`.

## Data sources

| Source | Serves | Needs |
|---|---|---|
| **FRED** | Treasury par curve (1m–30y), SOFR, Fed funds, ECB deposit rate, SONIA, OECD short rates, real yields, breakevens, IG/HY OAS, dollar index, FX fixings, VIX, WTI | nothing — keyless |
| **Yahoo Finance** | FX spot histories (EURUSD, USDJPY, USDKRW, …), 10y note future, gold | nothing — keyless |
| FMP | US (and plan-permitting international) daily EOD, closes adjusted for splits **and dividends** (`/historical-price-eod/dividend-adjusted`) | `FMP_API_KEY` |
| KIS | KRX daily OHLCV (6-digit codes route here automatically); **version 3**: ETF NAV / premium / constituents, KOSPI 200 futures and the option chain, KTB and USD futures (market `CF`), KRW benchmark yields (`Y0101`…`Y0117`, CD 91d), US yields, USD/KRW fixing, overseas prices (`NAS:AAPL`), exchange-traded KTBs, investor flows and short sales — all quotation-only, one stock-account key | `KIS_APP_KEY` + `KIS_APP_SECRET` |
| **Upbit / Binance / CoinGecko** | KRW-BTC daily candles since 2017, USDT spot klines, perpetual funding history, premium index, open interest, the top-N list; `KRW-BTC` / `BTCUSDT` route here automatically | nothing — keyless (`UPBIT_ACCESS_KEY` / `UPBIT_SECRET_KEY`, asset-inquiry scope, only for the balance tile) |
| Synthetic | Seeded per-symbol series, curves and rates | nothing |

FICC fetches are cached on disk (`~/.tradegen/ficc_cache`, six hours by default)
so a page refresh does not re-download two years of the curve. The same cache
now holds every price history that goes through `load_history` (FMP, KIS,
Yahoo, Upbit, Binance), so re-running Quant Lab, Signals, Portfolio or Strategy
Lab does not spend provider quota on unchanged bars; a series served from disk
says `cached <time>` in its note, which each page shows beside the source. A
series fetched while its market may be trading ends in a running price, so it
is kept for ten minutes only; fetched with the market closed it is kept for the
full TTL. `NEXTGEN_FICC_CACHE_TTL=0` switches the cache off, and deleting the
`HIST_*.json` files forces a refetch.

Price adjustment, by provider: Yahoo and FMP closes are adjusted for splits and
dividends (total return). KIS 수정주가 is adjusted for splits and rights only —
cash dividends are not reinvested — so a 6-digit KRX code is a price-return
series; ask for `005930.KS` with source `yfinance` when you need total return.
Portfolio and Strategy Lab warn when one panel mixes the two conventions.

The history and analysis clients share one HTTP session (`data/net.py`) that
retries a failed GET twice (connection errors and 502/503/504 only; never a 429
or 500, and never a POST that reached the server). KIS calls are also paced to
about eight a second, because KIS rejects a burst with its per-second-limit
error. The engine's quote path makes one attempt per pass instead: there,
a quote that goes missing for a reason that can clear by itself is skipped for
up to `NEXTGEN_NO_DATA_GRACE` passes (default 3), the Execution page names the
symbol while it lasts, and only then does the engine halt. A plan refusal,
missing key or stale quote still halts at once, and a halt still needs a manual
acknowledge and re-arm. With zero keys
and no network, every page still works on synthetic data — and says so in a
loud banner, because a swaption priced off a simulated curve is a toy and must
look like one. An explicitly chosen provider that fails **raises**; only
`auto` falls back, and only with the provider named in the note. The macro
overlay never lets a synthetic or degraded value act (P5).

## gs_quant integration

Two tiers, reported honestly on Settings:

* **Offline** (active whenever `gs-quant` is installed): realized volatility
  and max drawdown in the equity risk module route through `gs_quant.timeseries`.
* **Session** (with `GS_CLIENT_ID`/`GS_CLIENT_SECRET`): opens a Marquee
  `GsSession` for instrument resolution and pricing. gs_quant's rates and FX
  functions (swap rates, swaption vols, FX smiles) all need this session, which
  is why the FICC core prices locally.

## Everything inherited from NEXTGEN

Execution, Rules, Workflows, Skills, KRX, Runs, and Settings are the NEXTGEN
surfaces, unchanged: the DISARMED→ARMED→HALTED engine, frozen rules with
edit-revokes-confirmation, the simulated order book (there is still **no
broker order path** in this repository), the 72-skill cockpit, and the
KIS/OpenDART/KRX data layer. The macro overlay does not run through this
engine: each v2 book has its own runtime state (see [Statuses](#statuses)).
The navigation rail scrolls, so all nineteen entries are reachable at the
620 px minimum window height.

## Setup

1. Python 3.13: `python -m venv .venv`
2. `.venv/Scripts/python -m pip install -r requirements.txt -r requirements-dev.txt -c constraints.txt`
   (the constraints keep numpy 2.3.5, scipy 1.18.0 and pandas 2.3.3)
3. `cp .env.example .env` and fill in what you have (everything is optional —
   the FICC pages need nothing)
4. `.venv/Scripts/python main.py`

Optional: `TRADEGEN_MACRO_DIR` moves the macro state out of `~/.tradegen/macro`.

## Verification

```bash
.venv/Scripts/python tests/run_all.py                  # every suite; writes qa/acceptance_results.json
.venv/Scripts/python tests/run_all.py --suite macro    # one suite: cockpit, engine, ui, quant, ficc, expansion, macro, paper, grokteam or compliance
.venv/Scripts/python tests/run_all.py --milestone M8   # the exit set of a milestone (tests/macro_registry.csv)
.venv/Scripts/python -m tests.macro_acceptance         # resync the registry's implemented_in column
```

A test has one of three statuses: PASS, FAIL, or NOT_RUN — a test that raises
`tests.notrun.NotRun(reason)` because its reference data (REFDATA), an owner
input (OWNER) or an unbuilt dependency (PENDING) is missing. NOT_RUN is counted
separately, names what is missing, never counts as PASS and never changes the
exit code; the exit code is 0 only when nothing failed. The summary line reads
`<passed>/<total> passed, <failed> failed, <not run> not run`.

| Group | Suite | What it covers | Checks |
|---|---|---|---|
| cockpit | `tests/acceptance.py` | The inherited NEXTGEN cockpit, including the read-only scans (no order path, no account credentials requested, Settings shows presence not values) | 47 PASS |
| engine | `tests/engine_acceptance.py` | The DISARMED→ARMED→HALTED engine, rules, the simulated order book, the quote path, one live order per rule, a cap-rejected trigger retrying once its cap clears | 92 PASS |
| ui | `tests/flet_api_guard.py` | Every `page.<method>()`, every checked Flet control keyword and attribute, and every `pal.<token>` in `ui/*.py` exists in Flet 0.85.2 and the palette | 4 PASS |
| quant | `tests/quant_acceptance.py` | Monte Carlo, optimizer, signal and backtest invariants; GARCH parameter recovery, unit-variance t shocks, guardrail flags, likelihood ordering against GBM and normal-GARCH, forecast convergence, the drift modes, the bounded-innovation and martingale checks, the LR null size, interval coverage, every chart renders | 53 PASS |
| ficc | `tests/ficc_acceptance.py` | Bootstrap round-trips, monotone discount factors, Nelson-Siegel fits, PCA, duration and KRD, carry and roll, scenario convexity, swap and swaption parity, Black ↔ Bachelier, caps and floors, Garman-Kohlhagen, SABR, CIP, the carry backtest, CIR and Hull-White, structured products, narratives, every chart renders | 56 PASS |
| expansion | `tests/expansion_acceptance.py` | Fake KIS and crypto transports for every new asset domain, the gate's own checks (a planted edge passes, noise is rejected, the deflated Sharpe orders them, the distribution loop calibrates), the t+1 causality of every strategy family, the five-year rule counted in whole years, the table cost floor and the Strategy Lab's withheld verdict below it, the module self-checks | 19 PASS |
| macro | `tests/macro_acceptance.py` over `tests/macro_*.py` | The v2 build, below | 419 PASS / 121 NOT_RUN |
| paper | `tests/paper_live_acceptance.py` | The paper_live harness after the 2026-10-18/19 fixes, offline: costs from QUANTGEN's table and KRX ETF tick floor, LSE refused rather than proxied, the per-account cost gate in `Engine._open`, the 5-minute C3 account retired, no resume from another config's state, frozen price snapshots (exact round trip, sha refusal), post-session prices by window dates, session hours from `core.markets` across clock changes and holidays, only complete pulls frozen, the same-day replay's archived code, the power line, one ledger trial per configuration, the pre-registered gate and fidelity tests, the Strategy Lab ledger, concurrent ledger appends, the refused late freeze and the report outcomes block | 21 PASS |
| grokteam | `grokteam/selfcheck.py` | The GROKTEAM BOOK desk (Kalshi KXBTCD paper benchmark of the Grok trading-team guide), offline: the Kalshi fee and payoff with the fee inside the stake, SIZE (half Kelly, 6% cap, $50 floor), the GARCH-t digital, no look-ahead in hourly bars or quotes, the 30-minute quote lookback, the stationarity warning not skipping, each account's entry rule, the cluster t and the one-sided skill p, the verdict precedence, the TRADEGEN copy permanently blinded (no event decided after the freeze is listed, fetched or replayed at any date; no re-freeze), Python patch updates not voiding the freeze, the sha-checked cache and the new ledger family | 17 PASS |
| compliance | `tests/compliance_acceptance.py` over `tests/compliance_*.py` | The compliance gate, offline: the strict YAML loader (duplicate keys, anchors, native dates, 256 KB cap), the rules table, instrument map and venue file with the 38-row coverage and the monthly review cadence, the derived classes, the `decide()` kernel (conduct and hard-coded floor, fail-closed inputs, exits that stay open under D11, the OKX grey row with its cap, acknowledgement and 2026-12-03 auto-off at the Asia/Seoul boundary, D15 and D16 refusals), permits and plan screening, purity, the Ed25519 owner log (chain, anchors, key rotation, system halts), D12 tighten-now/loosen-tomorrow, the approved-version store and signed code hash, `load_context`, the `--check` exit codes 0-4 and the alert template, the owner-kept signer's refusals and key file, and the isolation residual (links, junctions, hard links, final-target checks) | 327 PASS |
| **Total** | `tests/run_all.py` | | 1055/1176 passed, 0 failed, 121 not run (2026-10-29, TRADEGEN `.venv`) |

The macro group (new in v2) discovers every `tests/macro_*.py` module,
wraps each test in a hermetic guard, and brackets the run with T-HERM-01 (every
network touchpoint raises) and T-HERM-02 (the shipped read-only trees and
`~/.tradegen/macro` are byte-identical before and after). Every test id of the
specification is a row of `tests/macro_registry.csv` (tier, the milestone it
runs from, its clause deferrals, the tests that implement it); fixtures are
md5-listed in `tests/fixtures/macro/MANIFEST.csv`.

| Modules | Covers | Checks (PASS / NOT_RUN) |
|---|---|---|
| `macro_m0_*` (harness, instruments, integration, rules, schemas) | Rules store, DO-NOT-BUILD predicates, schemas and validator, instrument books and tick floors, read-only scans | 37 / 2 |
| `macro_m1_*` (books, calendars, fixtures, integration, pit) | Point-in-time store, contracts and staleness, effective-dated calendars, lag audit | 68 / 14 |
| `macro_m2_*` (costed, risk) | `min()` composition and bounds, hedge state, concentration, ladder, costed paths | 24 / 21 |
| `macro_m3_estimators` | The seven estimators, QLIKE / DM / MCS, the B5 and estimator gates | 12 / 8 |
| `macro_m4_*` (integration, sleeves) | Family tags, sleeve vol scale, the D&M gate, base and inverse-vol weights | 19 / 7 |
| `macro_m5_*` (books, fills_events, integration) | Per-book runtime, HALT and re-arm, look-through caps, the fill model, events and annotations | 25 / 13 |
| `macro_m6_context` | Context log isolation, break trigger | 14 / 2 |
| `macro_m7_*` (cardp, cards, integration, ledger, stats) | Gate statistics, family ledger, CARD-P evaluation, card headers, verdict chain, the gate package | 61 / 35 |
| `macro_m8_*` (forward, integration, pipeline) | `macro_daily`, alerts, replay, app start, forward records and demotion, FORWARD-SIM and refusal books | 40 / 7 |
| `macro_m9_*` (lab, scenarios) | Quant Lab self-grading, scenario library, SEP band | 17 / 8 |
| `macro_tf_*` (data, gov, integration, screens) | Tech-fund data and manifest, DNB-TF predicates, screens and books, governance, CRY-1 | 59 / 4 |
| `macro_ui_*` | The v2 tokens and shared components, the Macro page views, the README claims, the effective rules store | 40 / 0 |

The whole suite is hermetic: it patches the network touchpoints to raise, so
it can never spend a quota or call the Claude API, and it proves that `auto`
degrades to a labeled synthetic series when the provider is gone. Run one
suite at a time on a busy host.

## Charts

Flet 0.85 ships no chart controls, so every chart renders through matplotlib
(Agg) into base64 data-URI images, painted with the app palette: seven equity
charts in `ui/qcharts.py` (price with moving averages, the Monte Carlo fan,
the terminal histogram, equity, the frontier, the correlation heatmap, the
conditional-vol path), fifteen FICC charts in `ui/fcharts.py` (curve with
par/zero/forward and the NS fit, curve history, PCA loadings, key-rate DV01
bars, scenario P&L, price/yield with the duration tangent, smile with market
points, FX spot with the forward curve, carry equity, carry bars, caplets,
payoff diagrams, rate fans, horizon P&L histograms, macro z-scores; its
self-check renders sixteen images), and six in `ui/xcharts.py` (lines, implied
vol smile, risk-neutral density, equity against a benchmark, horizontal bars,
price against NAV). The skill-insight bars (`ui/charts.py`) and the v2
multiplier bar (`ui/components.py`) are drawn with containers, not matplotlib.

## Regulatory note

QUANTGEN is built for the operator's personal use only. It intentionally does
not implement the recommendation-abstinence constraints of the NEXTGEN client
build, and it is not designed to satisfy Korean FSCMA or US SEC requirements
for commercial financial software. Do not distribute it as a product.
