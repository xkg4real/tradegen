# QUANTGEN version 3 — asset-coverage expansion: design and build record

Written 2026-09-26. This is the contract the build followed for the four steps the
operator set: (1) what the linked KIS account can reach and which credible models
to build on it, (2) crypto without KIS, (3) other assets, (4) validation that decides
what is embedded. The research behind it is in `reports/QUANTGEN asset coverage
expansion.md` (55-candidate shortlist with the operator's own study-material
citations) and `research_notes/QUANTGEN asset coverage expansion/*.md` (ten notes,
every claim with a locator or marked UNVERIFIED).

## 1. What the KIS key reaches — probed live 2026-09-25

The operator's app key was issued against a stock account (no derivatives account, no
overseas agreement). Every quotation endpoint below answered. Nothing in this
repository submits an order; the client stays read-only by construction.

| Domain | Endpoint (tr_id) | Probe result | Rows / call, paging | Module |
|---|---|---|---|---|
| ETF NAV | `etfetn/inquire-price` FHPST02400000, `nav-comparison-daily-trend` FHPST02440200, `inquire-component-stock-price` FHKST121600C0 | NAV 113,214.24 for 069500, 괴리율, tracking error, LP holdings; 100 sessions per call; 30 constituents with weights | 100, move DATE_2 back | `data/kis_markets.py::etf_*` |
| KOSPI200 futures | `domestic-futureoption/inquire-price` FHMIF10000000 (market `F`), `inquire-daily-fuopchartprice` FHKIF03020100 | A01612 at 1127.75 with basis 6.66, KIS theoretical 1132.78, OI 134,791; daily history back to listing (2025-12-01) and expired 101W12 still queryable | 100, DATE_2 | `futures_quote`, `futures_daily`, `continuous_futures` |
| Mini futures board | `display-board-futures` FHPIF05030200 (MKI) | six monthly contracts with theo, bid/ask, OI | list | `futures_board` |
| Option board | `display-board-option-list` FHPIO056104C0, `display-board-callput` FHPIF05030100 | 11 expiries; per expiry 100 calls + 100 puts with strike, bid/ask, KIS IV, delta/gamma/vega/theta/rho, OI, theoretical price | snapshot only, no chain history | `option_expiries`, `option_board` |
| KTB / USD futures | same endpoints with market **`CF`** (undocumented in the samples) | 3y A65612 at 102.420, 10y A67612 at 104.760, USD A75612 at 1350.0; 69 sessions since listing | 100, DATE_2 | `futures_market` chooses F vs CF |
| KRW benchmark yields | `overseas-price/inquire-daily-chartprice` FHKST03030100 with market **`I`** and codes `Y0101` (KTB 3y) … `Y0117` (30y), `Y0112` (CD 91d), `Y0114` (call), `Y0102` (corp AA−); `comp-interest` FHPST07020000 (`I`, 20702) for today's 19-row snapshot | 국고채 3년 4.014 %, CD 91d 3.21 %; history pages back 100 sessions per call (tested to 2025-12) | 100, DATE_2 | `krw_yield_daily`, `krw_yields_snapshot`, `core/ficc/curve_models.krw_curve_panel` |
| US yields | same, `Y0202` (10y), `Y0201` (30y), `Y0204` (Fed funds) | 5.18 %, 5.47 %, 3.88 % | 100 | `overseas_chart("I", …)` |
| 원/달러 fixing | market `X`, `FX@KRW` (KMB) or `FX@KRWKFTC` | 1,369.0 on 2026-09-24; 100 per call | 100 | `usdkrw_daily` |
| Overseas stock | `overseas-price/price` HHDFS00000300, `dailyprice` HHDFS76240000 (MODP=1 adjusted) | NAS:AAPL 337.20; 100 sessions per call paged by BYMD | 100 | `overseas_quote`, `overseas_daily` |
| Overseas indices | market `N`, `SPX`, `.DJI` | S&P 500 7,712.65 with 100 sessions | 100 | `overseas_chart("N", …)` |
| Overseas futures | `overseas-futureoption/daily-ccnl` HHDFC55020100, `inquire-price` HHDFC55010000, `search-contract-detail` HHDFC55200000 | **VXV26@CBOE, DXZ26@ICE, BTCU26@CME answer** (40 rows per call, INDEX_KEY paging); **ESZ26, MESZ26, NQZ26, ZNZ26, 6EZ26, GCZ26, CLX26, SR3Z26 return HTTP 500** on this key although `search-contract-detail` lists them (settlement 7759.50 for ES) — a data-entitlement gate, not a symbol error | 40, QRY_TP=P | `ovf_daily`, `ovf_contract_detail` |
| Exchange-traded bonds | `domestic-bond/inquire-price` FHKBJ773400C0, `inquire-daily-price` FHKBJ773404C0, `search-bond-info` CTPF1114R | 국고03250-2903 at 9,823.00 with yield 3.30 %; 69 sessions in one call (to 2024-07) | one call | `bond_quote`, `bond_daily`, `bond_info`, `ktb_issues()` from the bond master |
| Domestic flows | `investor-trade-by-stock-daily` FHPTJ04160001, `daily-short-sale` FHPST04830000 | 30 rows per call (foreign / individual / institution net quantities); short volume and ratio by date range | 30, DATE_1 | `investor_daily`, `short_sale_daily` |
| Symbol truth | keyless masters at `new.real.download.dws.co.kr/common/master/` | `fo_idx_code_mts` (A01612 = KOSPI200 Dec 2026, order 1), `fo_com_code` (A65612 3y KTB, A75707 front USD), `bond_code` (548 KTB rows) | — | `load_master`, `front_contract`, `index_futures_contracts`, `commodity_futures_contracts`, `ktb_issues` |

Account prerequisites, verified by the probe: **quoting needs only the app key**;
trading KOSPI200 or KTB futures needs a 선물옵션 account (기본예탁금 1천만/2천만 KRW,
1 h education, 3 h mock trading), and overseas F/O needs the 모의거래 course — none of
which QUANTGEN uses, because it never trades. Token rules are unchanged (24 h, one
issuance per minute, EGW00133), 20 requests per second; the client throttles at ~2 per
second in the probes.

What KIS still does not give: option-chain history (boards must be stored daily),
futures investor flows, CME ES/NQ/ZN/6E/GC/CL bars (Yahoo continuous contracts remain
the research feed, with their undocumented roll), and any crypto (FSC January 2024
stance on overseas spot ETFs unchanged; CME bitcoin futures quotes only since
2025-10-21).

## 2. Crypto without KIS — what was built and what is refused

Built (`data/crypto/crypto_client.py`, probed live 2026-09-26 from the operator's
network): Upbit public daily candles (KRW-BTC from 2017-09-25, 200 per call, 450
sessions in three calls), Binance public spot klines through `data-api.binance.vision`
(reachable; `api.binance.com` is the fallback), USDⓈ-M funding history (1,200 8-hourly
rows in two windowed calls), the premium index and the 30-day open-interest history,
CoinGecko's top-N list, and an optional Upbit balance read with a stdlib HS512 JWT
(`UPBIT_ACCESS_KEY` / `UPBIT_SECRET_KEY`, 자산조회 scope only). The Settings page probes
all three hosts.

Refused, in the module docstring and by construction: order, cancel, withdrawal,
deposit-address and transfer endpoints on any venue; private keys, seed phrases,
keystores, hardware-wallet secrets; transaction signing; any account on an unregistered
foreign exchange (Binance is data only); ccxt / web3 / pyupbit dependencies; tax
liability computation. The regulatory record (FIU-registered venues, the 2026 app and
site blocks of unregistered exchanges, the Travel Rule change of 2026-08-11, the 22 %
virtual-asset tax from 2027-01-01) is in the research report §3 with dates and sources.

## 3. Other assets — build versus document

Built as data-and-model surfaces (all keyless): VIX term structure and the hedged
roll-down trade (`core/ficc/vol_products.py`, Yahoo ^VIX / ^VIX3M / VIXY / SPY, KIS VX
for the live contract), FX cross-sectional momentum and dollar carry as extensions of
the carry basket (`core/ficc/fx_styles.py`), the KOSPI200 box-spread implied KRW rate
(`core/ficc/equity_deriv.box_rate`), the US Treasury 2-5-10 PCA butterfly and the
Diebold–Li forecast (`core/ficc/curve_models.py`). Documented only, with the reason in
the report: IBKR (regulatory grey for individuals), prediction markets (declared
gambling 2026-08), KAU carbon (closed to individuals until ≥ 2028), US closed-end funds
(no keyless NAV feed), merger and SPAC arbitrage (parsers of complexity 5), convertible
arbitrage (no data), KRX gold spot (no KIS endpoint; the ETF NAV is the proxy).

## 4. The gate and what it decided

`core/quant/validate.py` implements the protocol from the validation survey: purged
walk-forward (IS 756 / OOS 126 / embargo = holding period) on a T × G P&L matrix of
every configuration; annualised Sharpe with Lo's SE and a studentised circular block
bootstrap 90 % interval; the deflated Sharpe ratio for N trials; PBO by CSCV (S = 8 or
16); OOS/IS; positive-year share; survival at 2× costs; the parameter plateau; a regime
split; the McLean–Pontiff haircut. Distributional models: Kupiec, Christoffersen, the
Basel traffic light, 90 % coverage, PIT KS / χ² / Berkowitz and DGT correlograms, CRPS
and Diebold–Mariano. Every card renders each test as one plain sentence with the
number, the threshold and the sample size, because the operator has said they cannot
judge a silent fitting failure themselves.

`docs/asset_expansion_study.py` runs 34 cards on real history and writes
`docs/asset_expansion/results.md`, `results.csv` (md5 on every card) and
`cards/*.json`; `--only` re-scores a subset and merges it with the untouched cards.
**The decisions in that file are what the app offers**: a strategy whose card says
PASS is listed as available in Strategy Lab; REVISE shows with its revise target;
REJECT and INSUFFICIENT_DATA are listed under "not offered" with the first failed
criterion. The study is re-runnable offline from its price cache and its numbers are
traceable to `results.csv` by md5.

### 4.1 Four runs, two harness corrections, one grid correction

The study was run four times (2026-09-26 to 2026-09-27). Run 1 exposed harness
weaknesses that were fixed before run 2 (PBO meaningless on grids of fewer than eight
configurations, no benchmark test, KRX sleeves too short, the option board truncated
at its top 100 strikes, VIX hedge turnover of 55× a year). Run 2 exposed two more,
both in the plateau/PBO logic, fixed before run 3:

| Defect | Symptom in run 2 | Correction (`core/quant/validate.py`) |
|---|---|---|
| An "edge" was counted on two-value grid axes | every strategy on a 2×N grid failed the plateau check by construction | an edge only exists on an axis with ≥ 3 values; a value declared as the parameter's natural limit (`domain`) is not an edge either |
| PBO alone rejected flat plateaus | S_E1_trend_us: plateau 100 %, PBO 0.59, the in-sample winner losing OOS in 0 % of splits, CSCV slope −0.9 — the signature of near-identical configurations, not of over-search (complementary halves flip the luckiest column's rank) | over-search passes when PBO ≤ 0.05 **or** the winner loses OOS in ≤ 10 % of splits; REJECT needs PBO > 0.20 **and** a losing winner (Bailey et al. 2017 read PBO, probability of loss and degradation together) |

Neither correction moved a card to PASS on its own: every strategy the PBO rule
released was then rejected by the benchmark test. Run 3 also found that the crypto
trend grid `hysteresis ∈ {0.05 … 0.5}` was three rules in six costumes (the composite is
the mean of nine sign votes and lives on the lattice k/9), so run 4 scored the complete
lattice `{0, 2/9, 4/9, 6/9, 8/9}` with its ends declared as the domain and the trial
count raised to 11 for the deflated Sharpe; the ledger on both cards records it.

Two data corrections came from the live board: after the 15:45 close KIS shows the
closing auction's unmatched orders as a book (a 1.7-point bid under a 34-point option,
`aspr_acpt_hour` 154500), and every last print and KIS implied vol belongs to the last
session, not to today. `_top_of_book` now reports such a book as empty, the study and
the Derivatives page measure T from the last session, and a closed-market board is
labelled indicative. The first snapshot's 51 % ATM implied vol became 39.5 %, the
median gap to KIS's vol 2.2 points (from 26), and the butterfly violations 0 (from 61).

### 4.2 What was decided (run 4, 2026-09-27, results.csv md5 `ca757e25f508…`; 5 PASS, 11 REVISE, 18 REJECT)

| Family | Cards | Decision | The number that decided it |
|---|---|---|---|
| Crypto trend (sign votes + price/MA, long/flat) | KRW-BTC, BTC-USD | **PASS** both | OOS Sharpe 1.22 [0.62, 1.77] and 1.19 [0.72, 1.64]; beats buy-and-hold at p 0.04 / 0.07; DSR 1.00 after 11 trials; 2× costs 1.17 / 1.16; drawdown −49 % / −53 % vs −74 % / −83 %; haircut Sharpe 0.73 / 0.71 |
| Funding carry | M_C4 | PASS | BIS sign confirmed, bootstrap p 0.00 |
| Weekday table | M_C7 | PASS | no return effect after Bonferroni (p 0.18); weekend volume p 3e−35 → a cost input |
| Futures basis | M_O2 | PASS | fair value within 1.16 pts of KIS's theoretical (the dividend-point convention) |
| ETF trend switch | US, KRX | REJECT | does not beat buy-and-hold on Sharpe (p 0.75; KRX DSR 0.84); drawdown −15 % vs −27 % is the surviving, ungated claim |
| Vol targeting | SPY, KODEX 200 | REJECT | +0.08 Sharpe at p 0.18 (Cederburg's real-time result); KODEX −0.13 |
| Risk parity (unlevered) | US | REJECT | +0.03 at p 0.25: it is the benchmark |
| Sector momentum | SPDRs | REJECT | −0.15 vs the basket after 50 bp per side |
| TSMOM | 10 Yahoo futures | REJECT | OOS Sharpe 0.08, DSR 0.27 |
| Pairs | GLD/IAU, Samsung pref, Hyundai/Kia | REJECT | GLD/IAU −2.28 at 50 bp; Samsung tilt does not beat holding both (p 0.61); Hyundai/Kia DSR 0.86 |
| Pairs | KODEX/TIGER | REVISE (execution) | Sharpe 0.55 at 3 bp but −0.32 at 2× costs: a 1-session half-life is bid-ask bounce, the edge is inside the spread |
| VIX roll-down | VIXY/SPY | REJECT | OOS Sharpe −0.14, 341 position changes |
| FX momentum, dollar carry | G10 | REJECT | −0.59 (decayed); 0.27 on 68 trades |
| Diebold–Li forecast | KTB/UST | REJECT | 0/5 maturities beat the random walk |
| PCA fly | UST 2-5-10 | REVISE | ADF p 0.008 but half-life 104 sessions and a 39 % hit rate: a richness tile, not a trade |
| LETF drag forecast | KODEX 레버리지 | REVISE | GARCH-path MAE 136 bp vs last-quarter 91 bp: the ETF page quotes the realised-variance drag first |
| Kimchi premium | Upbit/FRED | REVISE | half-life 15 days; the predictive slope is +0.0003 per z (t +6.2, economically nil): descriptive |
| ETH/BTC | Binance | REJECT | ADF p 0.14, the expected null |
| GARCH(1,1)-t fan | SPY, KODEX 200 | REJECT | 5 % VaR breached on 6.6 % / 6.8 % of days; PIT KS p 0.003 / 0.0004 |
| GJR-t fan | SPY, KODEX 200 | REVISE / REJECT | breach count unchanged (6.6 %): the asymmetry is in the innovation, not the variance |
| GJR skew-t fan | SPY | REVISE | 5 % breaches 5.2 % (p 0.57), 1 % 1.22 %, Christoffersen p 0.85, coverage 89.7 %, KS p 0.07; only the χ² bin test and two correlogram lags fail; λ −0.19 |
| GJR skew-t fan | KODEX 200 | REVISE | 6.3 % breaches, 87.1 % coverage, yellow light over the last 250 days: the fan is too narrow in the 2025–26 regime, both tails |
| Bitcoin fans (t, GJR, skew-t) | BTC-USD | REVISE ×3 | γ ≈ 0, λ ≈ 0, ν ≈ 3, persistence on the stationarity guardrail at 75 % of origins; exceptions cluster (Christoffersen p 0.01) |
| Option board | KOSPI 200 Oct-26 | REVISE | captured with the market closed: last prints only; re-run 09:00–15:45 KST |

What the app does with it: the crypto trend rule is the one offered signal (Strategy
Lab, Crypto page); funding, weekday, basis, kimchi, fly and LETF drag are monitors with
their verdicts; every REJECT is listed as a refusal with its first failed line; the
Quant Lab shows the measured breach rates and the skew-t verdict beside every GARCH
fit; the Derivatives page labels a closed-market board indicative.

## 5. Modules added

| Module | Purpose | Reuses |
|---|---|---|
| `data/kis_markets.py` | read-only KIS asset domains, masters, probe | `KISClient._get`, token cache |
| `data/crypto/crypto_client.py` | Upbit / Binance / CoinGecko public data, Upbit balance | stdlib only |
| `core/quant/history.py` (extended) | routing by symbol shape: KRX code, `KRW-BTC`, `BTCUSDT`, Yahoo shapes, `NAS:AAPL`, KRX derivative codes, ISINs, `Y0101` | `core.ficc.data._yf_fetch` |
| `core/quant/validate.py` | the gate, model cards | `drift_study` conventions |
| `core/quant/strategies.py` | trend switch, vol target, xs momentum, TSMOM, pairs, crypto trend, risk parity; costed simulator; grid runner | `core.quant.optimize` |
| `core/ficc/equity_deriv.py` | futures fair value / basis, chain inversion, parity, static arbitrage, SVI, MFIV, RND, pricing kernel, box rate, hedge P&L, LETF drag | `core.ficc.swaps.black76`, `core.quant.garch` |
| `core/ficc/curve_models.py` | Diebold–Li, PCA butterfly, bond carry, KRW curve panel | `core.ficc.curves` |
| `core/ficc/fx_styles.py` | FX momentum, dollar carry, Fama regression | `core.ficc.fx` |
| `core/ficc/vol_products.py` | VIX term structure, roll-down, ETP drift | `core.quant.strategies.simulate` |
| `core/crypto/analytics.py` | kimchi premium, funding carry, regime score, ETH/BTC, weekday, GARCH / GJR / skew-t scorecard | `core.quant.garch`, `validate` |
| `core/quant/gjr.py` | GJR-GARCH(1,1) with t, normal or Hansen skewed-t innovations (fit, next variance, skew-t CDF/quantile) | `core.quant.garch` bounds and guardrails |
| `docs/build_expansion_primer.py`, `docs/primer_kit.py` | the plain-language companion PDF built from the cards | reportlab kit shared with the models primer's conventions |
| `ui/derivatives_page.py`, `ui/etf_page.py`, `ui/crypto_page.py`, `ui/strategy_lab_page.py` | the four new surfaces | `ai_panel`, `components`, chart helpers |
| `tests/expansion_acceptance.py` | hermetic checks + every module's self-check | `run_all.py` |

Conventions kept: decimals in the core, percent / bp / vol points in the UI; explicit
provider that fails raises, only `auto` degrades to a labelled synthetic; every random
draw seeded; no order path anywhere.
