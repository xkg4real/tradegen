# QUANTGEN context brief (read this first)

As of 2 October 2026 (Asia/Seoul). This brief is shared by every researcher on this project. It describes the application the research is for, what it has already tested, the prior design the research must confirm or correct, and the output format every researcher must follow.

## 1. What QUANTGEN is

QUANTGEN is the owner's (GEON, Korea University economics student) open-source, **read-only** quant research desk for individual investors, written in Python (numpy/scipy, Flet desktop app). It simulates prices, tests strategies against a statistical gate fixed before the test, and publishes what fails. **It has no order path**: no order, cancel, withdrawal or transfer code exists. Outputs are model cards, a simulated order book, costed backtests and a displayed exposure recommendation.

Data it can read: KIS Open API quotes (KRX stocks and ETFs, KOSPI200 futures and options, KTB/USD futures, KRW yields, US yields/indices/stocks, USD/KRW fixing, investor-type flows, short-sale data), KRX marketplace, OpenDART filings, FRED, FMP daily closes, Yahoo, Upbit/Binance/CoinGecko public crypto data. Horizons: daily swing (decide at the close) and intraday (KIS quotes). Target markets: Korea first, US second, crypto, then other global equity markets with **per-market signal weights**.

### Three rules written into the code
1. Read-only by construction.
2. **Decide at the close of day t, earn from day t+1.** Costs are charged on every unit of turnover at pre-registered rates and every result is re-run at 2x:

| Venue | Per side | 2x stress |
|---|---|---|
| KRX ETF | 3 bp | 6 bp |
| KRX stock | 35 bp (covers the sell-side securities transaction tax) | 70 bp |
| US shares via KIS | 50 bp | 100 bp |
| Crypto | 10 bp | 20 bp |
| Futures | 5 bp | 10 bp |
| FX | 10 bp | 20 bp |

3. **The gate decides, not the author.** Nine steps, fixed before the test, give PASS / REVISE / REJECT / INSUFFICIENT DATA: (1) purged walk-forward 756 in-sample / 126 out-of-sample sessions, embargo = holding period; (2) Lo (2002) Sharpe SE + 90% block bootstrap (2,000 x 10-session blocks), interval must clear zero; (3) deflated Sharpe >= 0.95 with every revision counted as a trial; (4) PBO via CSCV (<= 0.05, or the in-sample winner loses in <= 10% of splits; PBO > 0.2 with the winner losing = REJECT); (5) beat the benchmark on the same days, one-sided p <= 0.10; (6) Sharpe > 0 at 2x costs; (7) plateau: >= 50% of neighbouring configurations keep half the Sharpe; (8) >= 60% of calendar years positive; (9) a 60% live haircut (McLean-Pontiff decay), reported, not gated.

### QUANTGEN's own record (study run 2026-09-27, seed 11): 34 cards, 5 PASS / 11 REVISE / 18 REJECT
The 16 trading-strategy cards (OOS Sharpe [90% CI], benchmark Sharpe, p, Sharpe at 2x costs, turnover/yr):
- C3 crypto trend, KRW-BTC, long or flat (sign votes over 7-28 day lookbacks + price/MA ratios with hysteresis): **PASS**, 1.22 [0.62, 1.77] vs buy-and-hold 0.79, p 0.04, 1.17 at 2x, 13.7x/yr. BTC-USD: **PASS**, 1.19 vs 0.89, p 0.07.
- E8 pairs KODEX/TIGER trackers: REVISE (0.55; loses at 2x costs; half-life one session = bid-ask bounce).
- E1 trend switch, US ETF sleeves: **REJECT**, 0.84 [0.47, 1.20] vs 0.95, p 0.75; protects (max DD -15% vs -27%) but does not outperform. KRX ETF sleeves: REJECT, 0.52 [-0.03, 1.04] vs 0.74.
- E2 volatility targeting SPY: REJECT, 0.63 vs 0.56, p 0.18. KODEX 200: REJECT, 0.53 vs 0.66.
- E3 risk parity unlevered, US sleeves: REJECT (0.89 vs 0.86, p 0.25).
- E5 sector momentum, nine sector SPDRs: **REJECT**, 0.48 vs 0.63; after 50 bp per side below buy-and-hold.
- B3 time-series momentum, ten continuous futures: **REJECT**, 0.08 [-0.27, 0.43]; "no measurable edge after 2009".
- S6 pairs Samsung common/preferred: REJECT (0.83 vs 0.85). Hyundai/Kia: REJECT (DSR 0.86).
- E8 pairs GLD/IAU: REJECT (-2.28; costs eat the spread).
- V1 VIX roll-down hedged: REJECT (-0.14). V3 FX momentum G10: REJECT (-0.59). V4 dollar carry: REJECT (too few trades).
- Quant Lab: GARCH(1,1)-t fan on SPY breaches a 5% VaR on 6.6% of days (PIT p 0.003) -> REJECT.

**There is no stock-level cross-sectional technical or fundamental card yet** (no stock momentum, reversal, value, quality, earnings drift, RSI/MACD/Bollinger, etc.). This research designs that layer.

## 2. Prior design to confirm or correct ("QUANTGEN Signal & Macro Map", 1 Oct 2026)

Proposed signal families (daily-swing, from OHLCV unless stated): time-series momentum/trend (sign of 20/60/120/250-day return or price vs MA; vol-scaled; "0.4-0.8 per asset, ~1.0 diversified"); quality/profitability (GP/A, ROE, low accruals, low leverage; "most consistent sign of any fundamental factor"; 0.3-0.5 L/S); volatility-scaled sizing ("+0.1 to +0.3 Sharpe uplift on nearly every strategy" — already corrected by the macro research: robust only for momentum); short-term reversal with a volume filter (5-day z-score when volume/20d avg > 1.5; "0.5-1.0 gross, costs take half or more").

Prior per-market weights (0-3 scale): US XS-mom 3, ST-rev 1, value 1, quality 3, low-vol 2, flow 1, earnings drift 2, TS-mom 3. Europe 3/1/2/3/2/1/2/3. Japan 0/2/3/2/3/1/1/2. **Korea 1/3/2/1/2/3/3/2** (strong: 1-5 day reversal, earnings-announcement drift, foreign net-buying flow; weak: momentum, size). Taiwan 1/3/1/1/1/3/2/2. China A 0/3/1/1/1/3/1/1. India 3/1/2/3/2/2/2/2. EM 3/1/2/2/1/2/1/3. Crypto 1/2/0/0/0/2/0/3. Futures/FX: TS-mom and carry strong, XS-mom weak.

## 3. What the companion macro research (2 Oct 2026) already decided — do not re-litigate, but flag conflicts
- Macro variables never generate direction; they only size risk. Overlay multipliers lie in [0.5, 1.0]; nothing above 1.0.
- Momentum sleeves get own-volatility scaling (sigma126, 12% target, cap 1.0) + a Daniel-Moskowitz bear-state gate (floor 0.5). US momentum Sharpe 0.40 -> 0.80 gross (French data).
- Reversal and quality sleeves are held at 1.0x (never up-weighted in stress, never cut by macro).
- Korea gets a local 20-day vol target capped at 1.0; Samsung + SK hynix concentration caps; strict point-in-time data.
- US 12-1 momentum Sharpe 0.33 since 1990, 0.02 since 2008 (French WML). Korean 12-1 momentum literature: negative in high-turnover stocks; 1-month reversal -2.95%/month (t -3.77, 1999-2021).
- Decay haircuts (Ilmanen et al. 2021): value -49%, momentum -23% (n.s.), multifactor -18%.

## 4. How this research is organised
Two simulated panels of **fictional composite personas** (never impersonate a real person; cite real published research by real people and firms freely):
- **Professors** (academic knowledge: university courses, peer-reviewed papers, NBER/SSRN/arXiv, theses; TradingView strategies are examined as practitioner claims to be tested).
- **Finance career executives** (senior people with backgrounds at JPMorgan-, Morgan Stanley-, Goldman-, BofA-style firms, NYSE trading, CTAs, multi-strategy funds, investment banking, Korean securities firms). They argue from practice and must check their opinions against historical data.

A separate data lab is testing claims on real data in parallel: KRX all-stock daily data 1995-2026 (marcap, survivorship-free, OHLCV + market cap), Shiller monthly S&P 500 1871-2026, SPY daily 1998-2021, VIX daily 1990-2026, Ken French monthly factors 1926-2018. Where your claim could be checked on such data, state the exact test you would run ("data-check request").

## 5. Source standards
- Weight heavily: university pages and course materials (Stanford, MIT, Chicago Booth, Wharton, Harvard, Yale, NYU Stern, LSE, Oxford, KAIST, SNU, Korea University), peer-reviewed journals (JF, JFE, RFS, JFQA, Management Science, RAPS, JEF, JFM), NBER/SSRN/arXiv working papers, central banks/FRED/regulators (Fed, BoK, SEC, KRX, FSC), published research of large banks and asset managers (J.P. Morgan, Morgan Stanley, Goldman Sachs, BofA, Deutsche Bank, AQR, Man Group/AHL, Research Affiliates, Robeco, MSCI, S&P DJI, Dimensional, Two Sigma), index providers' factsheets.
- Do not rely on Wikipedia, Reddit, Medium, Investopedia, YouTube or forums as evidence (at most for a definition when nothing better exists, labelled T3).
- Open (fetch) the page you take a number from; a search snippet is not a source. Give the URL.
- Paraphrase; quote at most a short phrase (under 15 words), at most once per source.
- Distinguish in-sample vs out-of-sample, gross vs net of costs, pre- vs post-publication, and the market and period of every number.

## 6. Required output structure for every researcher's note
1. Persona line (role, background, the lens they argue from).
2. Position summary (5-10 sentences: what works, what does not, what QUANTGEN should do).
3. Evidence sections by topic, each with numbers, periods, markets and URLs.
4. **Where and when it failed** — dated episodes with numbers (mandatory).
5. Data-check requests for the data lab (exact tests).
6. **Claims ledger** (mandatory, a markdown table) with columns: `ID` (e.g. P2-C07 or E3-C04) | `Claim (one sentence)` | `Evidence (numbers, market, period, IS/OOS, gross/net)` | `Source(s) with URL` | `Tier` (T1 academic/official, T2 bank/asset-manager/major press/index provider, T3 other) | `Robustness` (replicated? post-publication? OOS? costs?) | `Failure cases` | `QUANTGEN implication` (BUILD-candidate / BACKLOG / DROP / CONTEXT + one-line reason). Aim for 15-30 claims.
7. Source list with URLs.
