# Grok trading-team guide vs QUANTGEN: benchmark analysis (2026-10-21)

## 1. Straight answer

**No.** Nothing in the evidence supports "significantly high profit," and the guide itself claims none. It has no backtest and no win rate, and its stated goal is to check that the exit rule fires on time. The guide can be benchmarked on paper without touching QUANTGEN's core models. The most likely result of that benchmark is a loss to costs.

| Fact | Number |
|---|---|
| pump.fun tokens that collapsed | 98.6% of 7M+ (Solidus Labs) |
| pump.fun tokens that stopped trading by the next day | 80.37% (CoinGecko) |
| Meme coins with >100% returns that show artificial growth | 82.8% (arXiv 2507.01963) |
| Closest published meme-coin agent | +0.62% per trade gross, costs not counted, negative once the top 3 trades are removed |
| Round trip for a $60 order in a $10k pool | 7.2% on Raydium, 9.1% on PumpSwap. QUANTGEN's crypto cost row assumes 0.2% (`core/quant/validate.py:78`) |
| Average return on Kalshi | takers −31.5%, makers −9.6% (Bürgi, Deng & Whelan) |
| LLM forecasts vs market price | Brier 0.126 vs the market's 0.111 (AIA). No model returned 1.0 per $ even before fees; Grok-4 returned 0.864 (Prophet Arena) |
| Kalshi taker fee on $60 | 3.5% of premium at 50c, 0.5% at 93c |
| LAZYOWEN-NAIVE, 48 sessions | −$6.74 per session (gross −$0.04, costs $6.70); lost on all 48 days |
| Grok subscription | $30 a month, which is 36% a year on a $1,000 account |

The guide's own setup also blocks the prediction desk:
- With the default install, World Monitor returns no data. CHIEF therefore reports "degraded" and BOOK never trades.
- Polymarket returns HTTP 451 from Korea.
- Kalshi reportedly restricts trading by Korean users.

So this can only be a paper benchmark. I recommend running it as a side project rather than moving QUANTGEN over to it.

## 2. What carries over to QUANTGEN

| Guide rule | Portable? | How, or why not |
|---|---|---|
| SCAN $10k liquidity floor | Yes | Use `liquidity.usd`. A missing field (pump.fun bonding curve) means drop |
| SCAN "sells > buys in the last two intervals" | Proxy | m5 AND h1; GeckoTerminal m15 vs m30−m15 as a sensitivity check |
| Holder velocity (the main signal) | No | GeckoTerminal holder counts refresh about once a day, so an hourly ratio comes out ≈1. A buys-based substitute works only on pairs older than 1 h |
| VET: largest wallet > 5% | Weak proxy | The public RPC method limit is 0. GeckoTerminal's top-10 share is stale and includes pool vaults |
| VET: liquidity, age, fees | Yes | V6 = QUANTGEN's cost gate applied to calibrated mean gross return. Not `expected_move`, because meme returns are skewed |
| VET: news check | No | No news input. Always passes, and the pass is logged |
| BOOK: 8 pp gap, max 7 bets, never average down | Yes, on Kalshi | An "own probability" exists only for BTC threshold contracts (a GARCH-t digital) |
| SIZE: Kelly with 6% cap, $50 minimum | BOOK yes, meme no | Meme trades have no probability or payoff, so use a fixed $60. The $50 minimum stops the $1,000 account below $833.33 |
| FILLS: 0.45% fee, $0.95 minimum | Yes | This is an assumed fee, not a venue fee. Exits use exact constant-product proceeds |
| RISK: 4·h6/h24 < 0.2 → close | Yes | Cannot fire on pairs younger than 6 h. There is no price stop |
| CHIEF, World Monitor, Grok's judgment | No | These test bot uptime, have no archive, and cannot be verified. The guide page's install prompt was not run |

## 3. Recommended benchmark: GROKTEAM-BENCH

Statistics are computed on a fixed $60 shadow book with no equity feedback. The literal $1,000 account path is reported separately.

| Account | Market | Signal / probability | Size / exit | Cost model |
|---|---|---|---|---|
| PRED-GATED | Kalshi KXBTCD hourly, decision at close−30m | GARCH-t digital (`garch.py:446`). σ from `forecast_variance` (`:558`), fitted on Binance BTCUSDT 1h bars ending at the decision. Spot = the Binance 1m close at or before the decision. Logistic recalibration on 2025 data. Enter if ask is in [0.80, 0.97], spread ≤3c, and p−ask > 2×fee | Half Kelly with b=(1−m)/m, capped at 6%, nothing under $50. One bet per event, held to settlement | Fill at the next minute's ask, plus fee = ceil(0.07·C·P(1−P)). Stress tests: 2× fee and +1c spread |
| PRED-LIT8 | same | The guide as written: p_raw vs ask/bid gap > 0.08, ask in [0.10, 0.90] | same | same |
| PRED-FLB (registered variant) | same | No model: buy the ask nearest 0.93 within [0.90, 0.95] | Flat $60 | same |
| NB0, null | same | Market mid used as the forecast; this is the skill bar | No trades | none |
| PRED-COIN, null | same | Random side on GATED's entries, computed analytically | same | same |
| MEME-LIT | Solana DEX, recorded forward | SCAN/VET proxies from section 2, V6 skipped | $60. Exits R1/R2/R3, filled at the next poll ≥60 s later. Forced exit 72 h after entry | Per-dexId pool fee (PumpSwap about 1.2% per side), the guide's fee floor, exact price impact, 0.5% MEV per side, priority fee ≥$0.05. Reported as GROSS, MARKET, FULL and 2× columns |
| MEME-GATED | same | Filter on LIT's fills: enter only if the lower 90% bound of the S4 quintile's calibration-window mean gross return beats 2× the FULL round trip | Readout filter only | same |
| MEME-PLACEBO, null | same | 1,000+ seeds drawn from all S1 tokens, stratified by age and liquidity, each sized by its own Z3 limit | Same exits and same censoring | same |
| SOL-HOLD and cash | SOLUSDT | Passive | none | 10 bp per side |

**Dropped:**
- **C3-SOL.** It would be a C3 run that cannot go in the C3 ledger, and it would make only 0–2 trades.
- **Fed/CPI scoring.** QUANTGEN stores no FOMC date history, and there are only about 32 events a year.
- **A Grok-probability arm.** It needs a paid subscription and forward-only logging.

**Data**

| Part | Mode | Detail |
|---|---|---|
| BOOK archive | Backtest, exploratory only | 2025-01-15 to 2026-08-20. Results split by hour of day and spread regime. Fills capped at the volume traded in the decision minute. Events the probes already saw are excluded |
| BOOK forward | Confirmatory | Hourly from the freeze to 2027-01-31. Order-book depth is read before each paper fill |
| Meme | Forward recording only | DexScreener every 5 min. Discovery every 15 min from trending, volume-sorted and promotion feeds, each tagged by source. GeckoTerminal keyless at ≤10 calls/min, holder info once a day. Gzipped jsonl with a sha256 manifest under `~/.nextgen/grokteam/` |

**Verdict rules, frozen before data**
- **GATE:** not run. It needs at least 525 sessions and 5 out-of-sample years (`validate.py:365-367, 586`), so the best possible verdict is PAPER-CANDIDATE.
- **BOOK skill gate:** compute the per-event mean log-loss difference against NB0 with `dm_test`, and require t < 0 and p/2 ≤ 0.10 (that function returns a two-sided p, `forecast_eval.py:155`). Failing this gate means REJECT, whatever the P&L.
- **PAPER-CANDIDATE requires all of:**
  - the 90% day-block bootstrap CI (blocks of ≥5 days, t(G−1)) of net return per $ lies above 0;
  - net stays positive at 2× costs;
  - the account beats its null (FLB/coin for BOOK, the placebo permutation for meme);
  - meme only: still positive after dropping the top 3 trades;
  - n ≥ N*;
  - Holm correction within each desk.
- **REJECT** if the CI's upper bound is below 0. Any other outcome is **INCONCLUSIVE**, reported with its MDE. No extensions; a longer run is a new ledger row.
- **No deflated Sharpe:** no ledger row carries the `sr_sd` input it needs.

**Minimum sample (MDE = 2.4865·sd/√n, one-sided α 0.05 after Holm, 80% power)**

| Desk | N* | Earliest readout |
|---|---|---|
| BOOK, 1% net edge at 93c (sd 0.274 per $) | 4,654 bets. The forward window has ≤2,350 events, so its best possible MDE is 1.4%; with about 600 bets it is 2.8% | Archive (exploratory): about 2026-10-28. Forward: 2027-02-01 |
| Meme, 3% net per trade | 619 trades at sd 30%, 6,870 at sd 100% | 2027-01-26, one look. If the shakedown projects too few trades, the desk is declared UNDERPOWERED before the freeze |

## 4. Implementation plan (new files only)

| Step | File | Lines | Runs |
|---|---|---|---|
| 1 | `grokteam/book.py`: read-only Kalshi client (≤1 req/s), raw Binance klines stamped at bar close with the in-progress bar dropped, GARCH-t refit at every decision (hours where the fit hits a bound are skipped; the desk is INVALID if more than 5% are skipped), fee, accounts, `--archive/--live/--readout` | ~250 | Archive pull about 1 day during KST daytime, then hourly |
| 2 | `grokteam/prereg.py`: hypotheses; sha256 of `grokteam/*.py` and every imported QUANTGEN file; list of data already seen; ledger rows via `gate_ledger` (`:375`, `:379`), dry-run on `temp_copy` (`:927`) first | ~80 | BOOK freeze 2026-10-25; meme freeze after its shakedown |
| 3 | `grokteam/selfcheck.py`: R1 example 0.1422 → CLOSE; $20 order → FEE_FLOOR; 93c fee $0.30; NaN p → no trade; no Binance bar closing after the decision is used; exact sell proceeds never negative; fixed placebo seed reproduces | ~80 | Before the freeze and on every run |
| 4 | `grokteam/record.py`: meme tape | ~200 | Continuous from 2026-11-04 |
| 5 | `grokteam/desk.py`: meme rules, replay, shadow book, placebo, GATED filter, $1,000 path, readout | ~300 | Daily after 14:05Z |

**Ledger**
- **GROKTEAM-BOOK** holds GATED, LIT8 and FLB.
- **GROKTEAM-MEME** holds LIT, plus a GATED-calibration row with the calibration file's sha in `params`.
- **Placebos** are registered as `acceptance_placebo` and write no row (`gate_ledger.py:57`).
- **Every row's `params`** carries the underlying and the code digest.

**What stays untouched**
- **No paper_live code is imported.** `engine.py:30` silences all warnings.
- **No paper_live code is called:** `register_trials`, `download`, `Engine`, `replay`, `grid` and `verdict.freeze` stay off-limits.
- **No out\*/ folder is written**, and `engine.py` and `config.py` are not edited.

The new rows will raise tf_gov's global trial count (`tf_gov.py:373`).

## 5. What the benchmark cannot tell us

- Whether a real Grok desk would do better, because the proxies stand in for Grok's judgment.
- A card PASS, which needs years of data.
- Edges smaller than about 1.4–2.8% per $ on BOOK or about 5–10% per trade on meme coins.
- How results behave outside one November–January window.
- The full meme-coin universe: discovery is sampled and biased toward promoted tokens.
- Real execution: book depth, failed transactions, MEV, and the gap between the BRTI index and Binance prices.
- Anything about whether real-money trading is legal.

## 6. Decisions for you

| Decision | My recommendation |
|---|---|
| 1. When and where the meme recorder runs | Start it 2026-11-04, after the H2 sessions, unless you have an always-on machine. Build BOOK first. |
| 2. Which BOOK events to trade: hourly at close−30m, or the daily 17:00 ET event only | Hourly. The daily event alone gives about 324 bets, an MDE of about 3.2% at 93c. |
| 3. Anchoring the ledger | Run a local `git init` (no remote) before the 10-25 freeze; otherwise every row stays UNVERSIONED. It changes the repo, so it's your call. |

## 7. Sources

- **The guide:** https://lazyowen.com/guides/grok-bot-trading-team-setup and https://lazyowen.com/guide-pdf/grok-bot-trading-team-setup.pdf
- **DexScreener:** https://docs.dexscreener.com/api/reference
- **GeckoTerminal and CoinGecko:** https://api.geckoterminal.com/api/v2 · https://www.geckoterminal.com/dex-api · https://www.coingecko.com/en/api/pricing
- **Solana RPC:** https://solana.com/docs/rpc/http/gettokenlargestaccounts · https://solana.com/docs/references/clusters
- **Kalshi:** https://api.elections.kalshi.com/trade-api/v2 · https://docs.kalshi.com/getting_started/historical_data · https://docs.kalshi.com/getting_started/rate_limits · https://docs.kalshi.com/getting_started/fee_rounding.md · https://www.karlwhelan.com/Papers/Kalshi.pdf
- **Papers:** https://arxiv.org/abs/2606.08232 · https://arxiv.org/abs/2507.01963 · https://arxiv.org/html/2510.17638v2 · https://arxiv.org/html/2511.07678v1 · https://arxiv.org/abs/2512.16030
- **Meme-coin base rates:** https://beincrypto.com/pump-fun-tokens-scams-solidus-labs-report/ · https://blockchain.news/news/pump-fun-memecoins-lifespan-study
- **DEX fees:** https://blockworks.co/news/pumpdotfun-fee-model · https://decrypt.co/337872/pump-funs-new-fee-model-hands-out-2m-to-creators-in-first-24-hours · https://www.theblock.co/post/354038/pumpswap-revenue-tokens · https://docs.raydium.io/products/amm-v4/fees
- **AI trading contest:** https://forklog.com/en/four-out-of-six-ai-models-suffer-losses-in-trading-tournament/
- **Korea access and legal:** https://docs.polymarket.com/api-reference/geoblock · https://www.wikitree.co.kr/articles/1153222 · https://v.daum.net/v/qGHcgsqFZo · https://keia.org/?p=29784
- **Fed paper:** https://www.federalreserve.gov/econres/feds/kalshi-and-the-rise-of-macro-markets.htm
- **Binance data:** https://data-api.binance.vision

## SKEPTIC LEDGER

D1 = rigor-first, D2 = build-first, D3 = edge-hunting.

| Design | Lens | Claim | Why refuted |
|---|---|---|---|
| D1 | stats, costs | KXBTCD hourly decisions with τ 1–24 h, 0–3 bets a day, N* reachable | Hourly events are open only 1 h, so at most 1 bet a day and about 320 test bets: UNDERPOWERED |
| D1 | stats, fit | REJECT via `block_bootstrap_ci` as a one-sided 90% bound on the mean | It gives a two-sided CI on the Sharpe ratio, not the mean |
| D1 | stats, fit | Skill gate uses `dm_test` as one-sided | It returns a two-sided p and ignores the sign |
| D1 | stats, fit | `score_strategy` records INSUFFICIENT_DATA | `walk_forward` raises an error below 525 sessions |
| D1 | stats, fit | Calibration-file sha stored in the `source` field | `source` is not in ROW_SET_KEY, so the duplicate row is dropped and the sha is lost |
| D1 | stats, fit | V6 via `expected_move` clears costs | Its symmetric-move form passes negative-EV skewed trades; its p bars ignore MEV |
| D1 | stats | MEME-LIT −4–7% a trade, $833 floor reached in 1–2 weeks | Gross return is unknown and 10 trades a day has no source; 4–7 days at that rate |
| D1 | stats | GT-BOOK-CAL −1–4% per $ at 0–3 bets a day | No evidence; at most 1 bet a day |
| D1 | stats | NB1 backed by Bürgi et al. | The paper excludes hourly markets, uses last-trade prices, and finds the bias weakening |
| D1 | stats | Polymarket mispricing about 2 pp | The reader's own zero-intercept conversion |
| D1 | stats | Meme N* of 291–1,163 is reachable | sd and trade rate are unmeasured; sd 0.6–1.0 needs 2,615–7,263 trades |
| D1 | stats, costs | Holder velocity from 15-minute GeckoTerminal snapshots | Holder counts are hours stale, so hv = 1 and V3/V4 reject every rising token |
| D1 | stats | Survivorship handled; tracking extended for placebos | Placebos are computed offline, so censoring is asymmetric |
| D1 | stats | 60 s fill delay rules out look-ahead | Exit timing is unspecified, and the linear sell price can go negative |
| D1 | stats | Design-effect term plus day mean handles dependence | Holds span days, and the day-mean and per-trade estimands differ |
| D1 | stats | DSR with n_trials = 2 | `sr_sd_daily` is missing, N ignores the proxy choices, and the Holm family is unlisted |
| D1 | costs | GeckoTerminal at 15/min keyless | The official keyless limit is 10/min; the Demo key is capped at 10k calls a month |
| D1 | costs | The whole meme universe is snapshotted | The new-pool launch rate is far above the call budget, so the universe is sampled |
| D1 | costs | Archive reaches N* unless it is under a year | Archive starts Nov 2024: about 320 test events; `max_close_ts` is ignored |
| D1 | costs | LP fee 0.25% | PumpSwap is about 1.2% per side; priority fees were omitted |
| D1 | fit | σ_τ from `horizon_vol` | It returns an annualised level, overstating σ 3–16× |
| D1 | fit | `power_line` takes new targets | It has no target argument |
| D1 | fit | Freezing rules.py and costs.py pins the rule | Imported code is unpinned, and engine.py unfreezes on 11-03 |
| D1 | fit | Kish design effect for N* | QUANTGEN bans the Kish design effect (gate_ledger.py:6-8) |
| D1 | fit | External anchor defined at `:62` | Wrong line (it is `:68`), and the anchor must be passed explicitly |
| D2 | stats | A 150-trade readout detects a 6–7% edge in 2–4 weeks | The MDE assumed iid trades, α 0.10 and sd 35%; corrected it is 8–32% |
| D2 | stats | H-B2: an 8 pp edge is detectable | Net is about 11.5%, below the 15% MDE; power is 0.37–0.63 |
| D2 | stats | FLB +1–2% a bet, +$15–30 a month | Unsupported for hourly taker fills; the monthly sd is about $115 |
| D2 | stats | LIT −$100 to −$200 | Assumes gross ≈ 0; P(gain) is 13–21% |
| D2 | stats | "56% of rejected tokens fell 50% within 6 h" | Misquoted: 27 of 48 tokens observed for ≥6 h, and these were rejected tokens |
| D2 | stats | DIGITAL −$2 a bet | That is the fee alone without the half-spread: a floor, not an estimate |
| D2 | stats | GATED profit would be the strongest signal | GATED is a re-slice of SHADOW, and hit rate is the wrong measure for skewed returns |
| D2 | stats | The placebo isolates selection | It excludes PASS tokens, and the hv proxy amounts to ranking by age |
| D2 | stats | Frozen before any candle is fetched | kprobe5/kprobe9 had already fetched candles |
| D2 | stats, fit | DSR with N = 43 | `sr_sd` is missing and the units are mixed |
| D2 | stats, fit | Bootstrap tests at 14 days | They return NaN for T < 20 and annualise with √252 |
| D2 | costs | V1 via public RPC with an 80% switch | The method limit is 0, and the fallback data is stale |
| D2 | costs | 8 s GeckoTerminal pacing, 429s under 5% | About half the calls got 429 |
| D2 | costs | Discovery from new_pools pages 1–3 | Those pages show seconds-old pools; pages 4–5 do not help |
| D2 | costs | PumpSwap 0.95%/0.30% fee; 7.23% headline | About 1.2% per side; the headline should be 8.6–9.1% |
| D2 | costs | Answer within 2–4 weeks | The PASS rate is near zero, so the result will likely be underpowered |
| D2 | costs | 15–25 MB a day | Gzip compresses 4×, not 7×: 30–60 MB a day |
| D2 | costs | Only Korean law binds Kalshi use | Kalshi itself restricts Korean users |
| D2 | fit | "Run GATE for completeness" | It crashes |
| D2 | fit | GATED via `expected_move` | Misapplied, and pooling turns it into a global on/off switch |
| D2 | fit | H-M1 via `block_bootstrap_ci` | It bootstraps a Sharpe, not a mean, and returns NaN for T < 20 |
| D2 | fit | GARCH refit at 00:00Z, one-step σ | Gives the wrong hour's variance, about 20 h stale |
| D2 | fit | Binance close at decision via `BinancePublic` | Bars are stamped at open time: a 1 h look-ahead |
| D2 | fit | PREREG hashes 3 files | Imported code is unpinned |
| D2 | fit | C3-SOL unregistered | It is an unregistered C3 run |
| D2 | fit | record.py is stdlib-only and stores raw bytes | `BinancePublic` imports `config` and the requests session, and returns parsed candles |
| D3 | stats, costs | 24/7 hourly events from 2025; 3,100 IS / 7,800 OOS events | 2025 has daytime hours only; counts overstated 1.3–1.6× |
| D3 | stats, costs, fit | GJR fitted on consecutive expiration_values | The series has 8–11 h overnight gaps |
| D3 | stats, fit | S from the previous expiration_value, no look-ahead | Published 3–4.5 min after close; a 2.5 min stale S beats the 0.9c gate on noise alone |
| D3 | stats | +$440 to +$880 a year | The $833 floor freezes 69–88% of simulated paths |
| D3 | stats | Prior 15–25%, under 5% to clear 36% | Not measured, and internally inconsistent (about 9–15%) |
| D3 | stats | FLB "literature range" | Not measured for hourly markets or taker fills |
| D3 | stats | LIT8 −1 to −3% | No evidence; likely worse |
| D3 | stats, costs | Stage 2 PASS is feasible | The DSR bar needs about 2.1% per bet; power is 0.2–0.36 |
| D3 | stats | Stage 3 about 2,000 decisions | That is about 808 bets, MDE 2.05% |
| D3 | stats, costs | Never capacity-bound | IS-era strikes traded about 38 contracts an hour with 7–11c spreads |
| D3 | stats | MEME-LIT 200 trades, loses most of $1,000 | It freezes after about 40 trades |
| D3 | stats, fit | C3-SOL defaults equal the PASS card | The cards chose h of 0.0 and 0.667; the default h 0.2 is untested |
| D3 | stats | Placebo isolates selection | It copies LIT's stake beyond its own cap, and one seed is not a null distribution |
| D3 | stats, costs | Hourly holder velocity from GeckoTerminal | Holder counts refresh about daily |
| D3 | costs | GeckoTerminal at 20/min | The official keyless limit is 10/min |
| D3 | costs | LP 0.25%, MEV counted once, 6.6% round trip | 7.07–8.5% with corrected fees and MEV per side |
| D3 | fit | GJR-t "applies directly" | gjr.py is scoring-only; it hits bounds on hourly data and has no rule for bound fits |
| D3 | fit | Placebo and FICC registered as trials | They should be `acceptance_placebo` and no row; registering them inflates N |
| D3 | fit | DSR with N = 22 + 4 | `sr_sd` is unspecified, and the 22 LAZYOWEN rows are not comparable |
| D3 | fit | Imports only pure helpers | The engine import silences warnings and reads PAPER_PROFILE |
| D3 | fit | FICC event dates from `events.py:167-184` | That is a window function; no date history is stored |
| D3 | fit | One-sided DM test | It is two-sided, and strikes within one event are correlated |

## OPEN/UNVERIFIED

**Kalshi**
- Fee formula at source (the official PDF returned 429), the rounding rule, fee history before 2026, and whether KXBTCD charges makers.
- The rate limit for unauthenticated calls, and whether the API terms allow bulk research pulls.
- When KXBTCD went 24-hour: somewhere between 2025-12-10 and 2026-03-14.
- Exact archive start date, and whether the live endpoints serve the 2026-08-21 to 10-21 window.
- Book depth and half-spread at close−30m.
- The basis between the BRTI index and Binance at the 1-minute scale.
- Whether daily KXBTCD events fall inside Bürgi's "crypto" category.

**Korea and legal**
- Kalshi's restriction on Korean users comes from one News1 report.
- Korean legal and FX-law exposure for DEX use.
- The 2027 tax figures come from secondary sources.

**Solana and DEX data**
- PumpSwap creator-fee tiers (the official table is an image only), Orca, Meteora and DLMM fees, and the size of MEV losses.
- GeckoTerminal's sustained keyless limit (10 or 30 per minute), how often holder counts refresh for new tokens, and whether top-10 share excludes pool vaults.
- Whether keyed RPC providers allow `getTokenLargestAccounts` at the needed rate.
- The meme trade rate and per-trade sd, which drive N*.
- The new-pool launch rate, which so far is extrapolated from one page.
- Whether DexScreener keeps returning data on rugged pairs.
- Whether BONK is listed on Binance or Upbit.

**Literature**
- The 2 pp Polymarket conversion.
- Whether the copy-trading ~3% result (arXiv 2601.08641) is out of sample.
- ForecastBench's projection that LLMs would match markets by August 2026.
- The error tables in the Fed paper.
- Median token lifetime in hours.

**Other**
- The Node ≥20 requirement for World Monitor (not in package.json engines).
- Binance access from Korea is resolved: it returned HTTP 200 on 2026-10-21.

Scratch arithmetic was run with plain `python -c` only. No files were created or changed in QUANTGEN or `~/.nextgen`.