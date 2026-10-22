# E5: Factor crashes, crowding and the risk layer for QUANTGEN's stock-level sleeves (Aug 2007 → 2 Oct 2026)

**Persona.** E5 is a fictional composite: the Chief Risk Officer of a multi-strategy, pod-based hedge fund. The career behind it sets pod drawdown limits, factor-exposure budgets and de-grossing playbooks at Citadel- and Millennium-style platforms. E5 is not a real person and speaks for no firm. E5 argues from one lens: every crowded factor is eventually sold by somebody else's risk limit, so the job is to stay small, diversified and still invested for the rebound. Each habit below is checked against published evidence and against QUANTGEN's own data.

**Conventions used throughout**
- **Gross and net.** These refer to QUANTGEN's pre-registered costs: 35 bp per side for KRX stocks and 50 bp per side for US shares.
- **"Local".** A result marked local was computed in this session, either from the data lab's raw files or from Stocklake daily closes. The raw files are KRX marcap 1995–2026 (common shares), CBOE VIX 1990–2026, SPY 1998–2021, and French factor vintages bundled with Python packages (monthly 1949–2017 and 1926–2018). Every local result is an in-sample (IS) descriptive statistic, and none has passed the gate.
- **"Korean factor sleeves".**
  - Universe: KOSPI and KOSDAQ common shares, the top 500 by market cap at the prior month-end, with price ≥ ₩1,000.
  - Portfolio: decile D10 minus D1, rebalanced monthly and held buy-and-hold day by day within the month.
  - Timing: decided at the month-end close and earning from the next session.
  - Period: 2000-01 → 2026-09.
  - Labels: WML is 12-1 momentum; STR is 1-month reversal. EW means equal-weighted; VW means weighted by market cap.
- **"Macro".** Numbers marked macro come from the companion macro specification (project docs `QUANTGEN_MACRO_INTEGRATION.md` and `QUANTGEN_MACRO_BACKLOG.md`), whose golden values were independently re-verified.

## Position summary

1. **Factor crashes are a recurring operating condition, not a tail curiosity.**
   - From Aug 2007 to Sep 2026 I document 19 dated episodes (§1). Seven of them fall in 2025–26 alone.
   - In Korea, 12-1 momentum lost 24.8% (EW) and 29.6% (VW) in July 2026. That is its worst month since at least 2000 (local, gross).
2. **The mechanism repeats, and forced-selling crashes partly reverse within days.**
   - A crowded, often levered position meets a shock. Other managers' risk limits then force them to sell at the same time: internal volatility targets, pod stop-outs and margin calls. Liquidity providers step back, and prices overshoot.
   - Examples of the reversal:
     - August 2007: the unlevered contrarian book lost 6.85% over three days, then gained 5.92% in one day.
     - August 2024: S&P 500 losses were recovered by 9 Aug.
     - April 2025: a +9.52% intraday reversal.
3. **Controls that demonstrably worked:**
   - **Own-volatility scaling of momentum.**
     - US 1926–2011: Sharpe 0.53 → 0.97, and the worst month went from −79% to −28%.
     - KRX VW, net of 35 bp: Sharpe 0.36 → 0.41. The Jun–Jul 2026 window was −10.1% against −22.6% for a static book with the same average exposure.
   - **Construction that removes unintended factor, sector and single-name bets.** In July 2026 the Korean VW winner decile was 85% Samsung Electronics plus SK hynix.
   - **No leverage, plus liquidity and turnover limits.**
4. **Controls that did not survive scrutiny:**
   - **Name-level stop-losses outside US momentum.** On KRX a 15% stop shrank the worst month, but it cut momentum's Sharpe from 0.43 to 0.26 gross (and to −0.17 net).
   - **Volatility scaling of value, quality and reversal.** Across 103 strategies there was no systematic out-of-sample gain.
   - **Crowding measures used as timing triggers.** They forecast lower returns over one to two years, not the crash date. Holdings-based versions even relate negatively to crash risk.
   - **VIX-type market gates.** The VIX closed between 12.9 and 25.8 at the start of five factor crashes.
5. **Pod-style hard stops are a manager-selection device, not a way to preserve a good strategy.**
   - The rule is: lose 5% and half the capital is taken away; lose 7.5% and the manager is likely out. It suits a platform with 300+ teams that can reallocate capital.
   - Applied to one investor's few sleeves, it mostly fires on noise. At 8% volatility, a strategy whose true Sharpe is 0.5 breaches −8% in 38% of years. It hits −15% with 65% probability within ten years.
6. **The macro spec's drawdown ladder is sound only as a book-level tail device.**
   - The ladder is: −8% → gross × 0.5; −12% → block new entries; −15% → HALT. This persona proposed it in the macro panel.
   - It needs three corrections:
     1. State its thresholds in units of the book's target volatility, or keep book volatility at or below 8%.
     2. Never run it per sleeve. On vol-scaled KRX momentum it takes Sharpe from 0.41 to 0.14.
     3. Specify the re-arm rule: reset the reference peak and re-enter at 0.5. With a high-water-mark reference, the book re-halted 20–22 times a year in my tests (2000–26).
7. **Recommendation: an eleven-part risk layer (§5).**
   - Neutral construction.
   - Name, sector and pair caps.
   - Liquidity limits.
   - Turnover and cost limits.
   - Own-volatility scaling for momentum only (R-03/R-04).
   - A book-level volatility target (R-06).
   - The corrected ladder (R-07).
   - No name-level stops, and statistical review triggers for each card.
   - Crowding and concentration as displayed context.
   - A fixed factor-episode stress table.
   - Squeeze filters for any simulated short leg.

## 1. Where and when it failed: dated factor and technical-strategy episodes, 2007–2026

### Takeaway
Since 2007, technical and fundamental factors have crashed in two distinct ways:
- **Forced-selling unwinds.** Aug 2007, Mar 2025, Aug 2024 and Apr 2025 are examples; they partly reverse within days.
- **Regime and thesis breaks.** The 2009 rebound, the 2018–20 value drawdown, 9 Nov 2020 and Jun–Jul 2026 are examples; they do not reverse quickly.

Three features matter for QUANTGEN:
- Market-level stress gauges were usually quiet at the onset; only the factor's own volatility was elevated.
- Monthly data hide the fastest episodes.
- In Korea, factor crashes coincide with two-stock concentration and market-wide leverage unwinds.

### Cited Findings

**Episode table.** Numbers are as published or computed locally, labelled with market and period. "WML" means the winner-minus-loser momentum portfolio.

| # | Dates | Market | What happened (numbers) | Mechanism | What helped or failed | Sources |
|---|---|---|---|---|---|---|
| E01 | 6–10 Aug 2007, the "quant quake" | US equity market-neutral | Khandani–Lo's contrarian (mean-reversion) book, unlevered: −1.16%, −2.83%, −2.86% on 7, 8 and 9 Aug (−6.85% cumulative), then +5.92% on 10 Aug. At 8:1 leverage: about −25% over the three days, then +23.67%. Press-reported fund losses cited by KL: GS Global Equity Opportunities −30%+ in a week; Highbridge Statistical Opportunities −18%; Renaissance −8.7% month-to-date. **Local:** SPY −0.71% over 7–9 Aug; VIX close 22.94 (6 Aug) and 26.48 (9 Aug). French monthly factors for Aug 2007: Mom +0.09%, HML −2.25%. | Similar market-neutral books were unwound fast. The unwind began in July, starting with financials and with long book-to-market, short earnings-momentum positions. Market making withdrew from 8 Aug. Leverage had risen to offset alpha decay: matching 1998 returns took about 2:1 in 1998 and about 9:1 in 2007. | Invisible at monthly and index frequency. A cut at the 9 Aug close missed the +5.9% day. | [KL 2007](https://web.mit.edu/Alo/www/Papers/august07.pdf); [KL NBER w14465 / JFM 2011](https://www.nber.org/papers/w14465); local |
| E02 | Mar–May 2009 momentum crash | US; Korea | **US, French Mom (monthly vintage):** Mar −11.53%, Apr −34.58%, May −12.33% (−49.3% over Mar–May; calendar 2009 −52.6%) (local). **Daniel–Moskowitz:** losers +163% vs winners +8% while the market rose 26%; their WML lost −42.28% in Mar and −45.52% in Apr. **Barroso–Santa-Clara's WML:** −73.4% over three months. **Korea:** WML Mar −10.8% / Apr −15.6% (EW) and −19.2% / −17.0% (VW), while KOSPI rose +13.5% in each month (local). | Option-like payoff: after a bear market the loser leg is high-beta. In bear markets WML's up-market beta is −1.51 against a down-market beta of −0.70 (t 4.5). | Vol scaling plus the bear-state gate: daily-compounded French Mom over Mar–May 2009 went from −45.6% to −8.0% (macro G-MOM-06). The D-M gate was on in both the US and Korea. | [D-M NBER w20439](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf); [BSC 2015](https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002566); macro; local |
| E03 | Feb–Apr and Nov 2016 | US | French Mom: −4.12%, −5.06%, −6.15% (Feb–Apr) and −4.16% (Nov). Calendar 2016 −17.5%, while HML returned +20.7% (local). | Value–momentum seesaw, then a post-election rotation. | Vol scaling barely helped: a 12%-target monthly proxy lost −16.7%, because volatility was not elevated. | local (French monthly vintage) |
| E04 | Value drawdown 2007–2020 (the "quant winter" of 2018–20) | US | Fama–French value: −39.1% peak to trough over more than 12 years, roughly a 1-in-20 event (AHKL). **Local HML:** −32.1% from Jan 2007 to Sep 2018; 2017 −11.2%; 2018 to Nov −9.0%. **AQR:** the value spread reached the 100th percentile, above the 1999–2000 peak; Q1 2020 was value's worst quarter after adjusting for volatility. | Revaluation, i.e. a widening spread. Migration and profitability were normal (AHKL). | A mechanical drawdown stop would have exited before the recovery. Later: IWD −7.7% vs IWF −29.3% in 2022; VLUE +32.7% in 2025. | [AHKL 2020](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3488748); [AQR 2020](https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead); iShares ([IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf), [IWF](https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf), [VLUE](https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf)); local |
| E05 | Oct 2019 | Korea | WML −18.1% (EW) / −22.6% (VW) in one month, while KOSPI rose +1.0% (local). | Not identified; it looks like an idiosyncratic reversal of winners. | The vol-scale weight was high (0.77 EW, 0.65 VW on 30 Sep) because volatility had been low. The D-M gate was off. This was the vol-scaled sleeve's worst month (−13.1% EW, net). | local |
| E06 | 9 Nov 2020, vaccine day | US / global | MSCI: the momentum factor lost nearly 5% in one day, erasing most of nine months' gains. Bloomberg: the largest intraday drop in its records starting in 2000. French Mom Nov 2020: −12.0% static (macro). **Local:** SPY +1.26%; VIX close 25.75. Korea WML Nov 2020 −6.5% (EW) / −4.5% (VW), while KOSPI rose +14.3%. | Vaccine news flipped the crowded winner and loser legs. Short interest in high-momentum stocks had been more than 3 SD above its mean in early October (MSCI). | Vol scaling (weight 0.31) held Nov 2020 to −3.9% (macro). The D-M gate was off because it was a bull market. | [MSCI 13 Nov 2020](https://www.msci.com/research-and-insights/blog-post/are-momentum-wings-finally-starting-to-melt); [Bloomberg 9 Nov 2020](https://www.bloomberg.com/news/articles/2020-11-09/momentum-trade-plunges-the-most-on-record-in-rotation-frenzy); macro; local |
| E07 | Jan 2021 meme squeeze; Mar 2021 Archegos | US | **GME:** short interest 122.97% of float. Close about $20 on 4 Jan, $347.51 on 27 Jan, intraday high $483 on 28 Jan, then a fall of more than 86%. AMC +301% and KOSS +480% on 27 Jan; XRT had $506m of redemptions (SEC). **Local:** VIX went from 23.8 to 37.2 and SPY fell 2.44% on 27 Jan. Korea WML Jan 2021 −11.0% (EW) / −8.7% (VW). | Crowded shorts met retail attention. Buy-to-cover was a small share of volume, and staff found no gamma squeeze (SEC). **Archegos:** concentrated longs financed with total-return swaps → margin calls → forced sales → bank losses (Fed). | Losses were concentrated in a few short books. The Fed judged the effect on the hedge-fund sector limited. | [SEC staff report 2021](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf); [Fed FSR May 2021](https://www.federalreserve.gov/publications/files/financial-stability-report-20210506.pdf); local |
| E08 | 2022 growth crash; Jan 2023 reversal | US | **2022:** IWF −29.3% vs IWD −7.7%; QUAL −20.4%, MTUM −18.2%, USMV −9.4%, IVV −18.1% (iShares). French RMW +8.4% and Mom +17.4% in 2022 (macro). **Jan 2023:** Mom −13.7% static → −3.8% with the spec stack (macro). | A rates shock. Momentum had rotated into energy and value; its crash came in Jan 2023, when the 2022 losers rebounded. | Vol scaling helped in Jan 2023. | iShares ([MTUM](https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf), [QUAL](https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf), [USMV](https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf), [IVV](https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf)); macro |
| E09 | 2023–24 mega-cap / AI concentration | US | **2023:** IWF +42.5% vs IWD +11.3%; MTUM +9.1% vs IVV +26.3%. **2024:** MTUM +32.9% vs IVV +25.0% (iShares, NAV). **Information-technology weight on 29 Sep 2026:** MTUM 54.3%, VLUE 43.1%, QUAL 38.7%, USMV 33.3% (iShares). | Concentration: factor indices became sector bets. | Sector caps and residual momentum (see §4). | iShares |
| E10 | 11 Jul–5 Aug 2024: rotation, then the carry unwind | US, Japan, Korea | **US momentum:** −5.9% from 11 Jul to 2 Aug, before any VIX trigger, then +6.5% from 6 to 30 Aug (macro). Local VIX close was 12.92 on 11 Jul. **5 Aug (BIS):** TOPIX −12% in a day; S&P 500 −3.0%; VIX above 60 off-hours (local intraday high 65.73, close 38.57). Speculative yen shorts were about ¥2tn. The S&P 500 recovered by 9 Aug. **Korea (local):** KOSPI −12.1% over 2–5 Aug; WML Aug 2024 −8.4% (EW) / −13.6% (VW). | Yen-carry unwind. Leveraged hedge funds de-risked to meet internal volatility targets, not because of margin calls (Fed). Hedge-fund leverage was at or near its highest since 2013. | The R-08 VIX block whipsawed: the momentum it blocked gained +5.0% (macro). | [BIS Bulletin 90](https://www.bis.org/publ/bisbull90.pdf); [Fed FSR Nov 2024](https://www.federalreserve.gov/publications/files/financial-stability-report-20241122.pdf); macro; local |
| E11 | 27 Jan 2025, DeepSeek | US AI complex | Nvidia −17%, a $589bn loss of market value, the largest for a single stock ever. Nasdaq 100 −3%, S&P 500 −1.5%; the chip index had its worst day since Mar 2020 (Bloomberg). **Local:** VIX close 17.90. Korea WML Jan 2025 +4.4% (EW) / +4.6% (VW). | A thesis shock to the crowded AI long, short-lived according to GS. | No factor-level crash in Korea. | [Bloomberg 27 Jan 2025](https://www.bloomberg.com/news/newsletters/2025-01-27/nvidia-loses-589-billion-as-deepseek-batters-stock-evening-briefing-americas); [GS 2025 in review](https://marquee.gs.com/welcome/news/views-from-the-trading-floor/2025-in-review); local |
| E12 | Feb to 10 Mar 2025, "multistrat-mageddon" | US multi-strategy funds | Millennium lost 1.3% in February, its worst month in more than six years; about $900m came from two index-rebalancing PMs (Hedgeweek). GS: 7–10 Mar was one of the worst two-day stretches for hedge funds in years, with a momentum drawdown of more than 4 SD and forced de-risking. | Crowded pod trades plus synchronized pod stop-outs. | Pod limits removed the losing teams but helped propagate the unwind. | [Hedgeweek 10 Mar 2025](https://www.hedgeweek.com/millennium-posts-rare-monthly-loss-amid-index-rebalancing-trades/); [GS 2025](https://marquee.gs.com/welcome/news/views-from-the-trading-floor/2025-in-review) |
| E13 | 2–9 Apr 2025 tariff crash | Global | S&P 500 −13% from 3 to 8 Apr, then a +9.52% intraday reversal on 9 Apr, the sharpest since 2008 (GS). Hedge funds' largest-ever one-day net equity sales in GS prime-brokerage data (which start in 2010), more than 75% of it in North America (Bloomberg). **Local VIX closes:** 45.31 (4 Apr), 52.33 (8 Apr), 33.62 (9 Apr). **Fed:** implied volatility highest since Mar 2020; hedge-fund leverage had hit historical highs in Q3 2024. Korea WML Apr 2025 +12.1% (EW) / +20.9% (VW). | A macro shock plus de-grossing from record leverage. | A HALT at the 8 Apr close would have missed the 9 Apr reversal. | [GS 2025](https://marquee.gs.com/welcome/news/views-from-the-trading-floor/2025-in-review); [Bloomberg 7 Apr 2025](https://www.bloomberg.com/news/articles/2025-04-07/hedge-funds-log-historic-one-day-stock-selloff-in-market-rout); [Fed FSR Apr 2025](https://www.federalreserve.gov/publications/files/financial-stability-report-20250425.pdf); local |
| E14 | Oct–Nov 2025 momentum unwind | US, Europe; Korea | Morgan Stanley's momentum basket −11.3% in five days. Quant long/short funds −1.7% in October. Renaissance's RIEF about −15% through 10 Oct. The reversal spread to quality and low-volatility factors (Hedgeweek). MTUM −6.2% vs SPY −3.6% from 3 to 21 Nov (Stocklake). **Korea, Oct 2025:** WML VW −13.9% and STR VW −32.0%, while KOSPI rose +19.9% (local). | Crowded AI, European bank and precious-metal winners reversed. In Korea the VW sleeves were bets on a few mega-caps. | Name caps (see E17). | [Hedgeweek 27 Oct 2025](https://www.hedgeweek.com/market-reversals-hit-quant-hedge-funds/); Stocklake; local |
| E15 | Jan–Feb 2026 | US | **January:** systematic long/short about −1% in the first ten days; UBS estimated about −2.8% for US quants over two weeks. Losses came from crowded trades and short exposure to high-beta stocks; the Friday before 22 Jan saw the largest one-day deleveraging since late December (Hedgeweek). **4 Feb:** tech-focused hedge funds down as much as 2.78%; multi-strategy equity books −1.9%, their worst day since 9 Apr 2025 (Reuters via Investing.com). **Local:** MTUM −3.66% vs SPY −0.49% on 4 Feb (Stocklake); VIX close 18.64. | A scare that AI would disrupt business models; crowded long exits; squeezes in high-beta shorts. | — | [Hedgeweek 22 Jan 2026](https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind); [Investing.com/Reuters 5 Feb 2026](https://www.investing.com/news/economy-news/hedge-funds-hit-by-ai-selloff-goldman-sachs-says-4487631); Stocklake; local |
| E16 | Mar 2026 oil and geopolitical selloff | US, Korea | From 2 to 30 Mar (Stocklake, price returns): MTUM −8.95%, SPY −7.67%, QUAL −8.60%, USMV −5.75%, IWM −9.01%. **Korea (local):** KOSPI −19.1% in March; WML VW −13.1%. VIX close 30.61 on 30 Mar. | Broad de-risking with little factor dispersion in the US. | Low-volatility stocks held up best. | Stocklake; local |
| E17 | May–Jun 2026 Korean concentration | Korea | Samsung + SK hynix rose from 35.1% of KOSPI common-share market cap (Dec 2025) to 57.1% (Jun 2026). SK hynix was 68.7% of the VW winner decile in May and 72.8% in June. VW WML returned +77.0% in May, against +9.5% for EW. VW STR lost 35.3% in May, its worst month (all local). | A two-stock market turns a VW factor into a single-stock bet. | A 5% name cap cut May from +77.0% to +17.8%. | local |
| E18 | 22 Jun–30 Jul 2026 momentum crash | US; Korea | **US:** GS High Beta Momentum basket had its worst month since Nov 2000 in July (Yahoo, 31 Jul). Long/short momentum lost more than 3% in each of two consecutive weeks, its worst two weeks in more than three years, and momentum positioning was the highest since 2002 (Hedgeweek, 7 Jul). A leveraged AI-focused fund (Situational Awareness) was forced to liquidate. From 22 Jun to 29 Jul: MTUM −18.0% vs SPY −2.0%, USMV +4.3%, QUAL +0.1% (Stocklake). French Mom Jul 2026 −10.9% static → −5.9% with the stack (macro). VIX 19.49 (23 Jun) and 20.66 (29 Jul). **Korea:** KOSPI −38.6% (23 Jun–30 Jul). WML Jul 2026 −24.8% (EW) / −29.6% (VW), the worst month since 2000; the VW winner decile was 85.4% Samsung + SK hynix (local). | A bull-market crash of a record-crowded AI and semiconductor winner trade, plus a leveraged fund's liquidation. In Korea, a leverage unwind. | Own-vol scaling was the only rule switched on: weights 0.35 (EW) and 0.20 (VW) on 22 Jun kept July to −7.5% / −5.2%. The D-M gate was off because KOSPI's 24-month return was +235%. The VIX ≥ VIX3M flag was on for zero days (macro). | [Yahoo 31 Jul 2026](https://finance.yahoo.com/markets/stocks/articles/july-ends-hopeful-note-stocks-222100309.html); [Hedgeweek 7 Jul 2026](https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/); Stocklake; macro; local |
| E19 | 30 Jul–30 Sep 2026 rebound | US, Korea | MTUM +13.3% (29 Jul–1 Oct). KOSPI +22.8%. Korea WML Aug–Sep +15.3% (EW) / −0.6% (VW) (local). | Rebound. | Any rule still de-risked paid a rebound tax: the KOSPI ladder earned +7.9% vs +22.8%. | Stocklake; local |

**Cross-episode facts**
- **Long-run US momentum (local, French monthly vintage, Jan 1949–Mar 2017).**
  - Sharpe 0.62 over the full period, 0.36 for 1990–2017 and −0.16 for 2008–2017.
  - Maximum drawdown −57.6%, from Nov 2008 to Sep 2009.
  - Worst months: Apr 2009 −34.6%, Jan 2001 −25.0%, Nov 2002 −16.3%.
- **The macro programme's daily French Mom series (1990–2026).** Static: Sharpe 0.399, maximum drawdown −63.3%. With R-03 × R-04: 0.798 / −20.9% (gross).
- **Korean 12-1 momentum, Jan 2000–Sep 2026 (local).**

  | Version | Sharpe, full period | Sharpe, 2016–26 | Max drawdown |
  |---|---|---|---|
  | EW, gross | 0.43 | 0.08 | −70.6% |
  | EW, net of 35 bp | 0.20 | −0.13 | −81.2% |
  | VW, gross | 0.52 | 0.47 | −72.8% |
  | VW, net of 35 bp | 0.36 | 0.32 | −78.5% |

- **Factor ETFs, 2026 year to date (to 1 Oct; Stocklake, price only).** MTUM +28.5%, SPY +12.6%, QUAL +12.9%, USMV +4.9%, IWM +13.8%.

### Inferences
- **Clustering.** The 21 months from Jan 2025 to Sep 2026 contain at least seven separately reported crowding episodes. Press attention inflates the count, but the severity is confirmed by data:
  - the GS basket's worst month since 2000;
  - Korean WML's worst month since 2000;
  - MTUM −18.0% vs SPY −2.0% over five weeks.
- **Market-level stress gauges were quiet at onset.** VIX closed at 22.9 (6 Aug 2007), 25.8 (9 Nov 2020), 12.9 (11 Jul 2024), 17.9 (27 Jan 2025) and 19.5 (23 Jun 2026). Only own-factor volatility was elevated beforehand: the Korean VW momentum vol-scale weight was already 0.20 on 22 Jun 2026. So factor-crash protection must come from the sleeve's own risk state, not from market gauges.
- **Two clocks.** Crashes driven by forced selling (E01, E10, E12, E13) reversed within 1–5 sessions; crashes driven by a regime or thesis change (E02 for losers, E04, E06, E18) did not. A rule that cuts at the close of the worst day helps against the second kind and hurts against the first. In real time the two cannot be told apart, which argues for sizing ahead of time (own-vol) rather than cutting afterwards.
- **Korea's profile is different.**
  - Momentum crashes there coincide with market-wide crashes or rebounds (2009, Jul 2026) and with two-stock concentration (2025–26).
  - The VW "factor" in 2026 was mostly Samsung and SK hynix.
  - The D-M bear gate cannot see a bull-market crash (Jul 2026).

### Gaps
- **Prime-brokerage figures not verified.** I could not verify the GS or MS prime-brokerage de-grossing numbers for January 2021 (widely reported as the largest since 2009); Bloomberg blocked access and the GS 2021 review returned 404.
- **DeepSeek-day hedge-fund losses not verified.** Hedge-fund P&L figures for 27 Jan 2025 were not accessible (the Reuters and US News pages were blocked).
- **11 Jul 2024 rotation not quantified.** The Russell 2000 vs Nasdaq 100 move that day was not sourced.
- **2023–24 concentration statistics not fetched.** These are the Magnificent-7 share of S&P 500 returns and weight.
- **March 2026 pod-shop losses not verified.** The source returned 404.
- **French factor data after 2018 not available locally,** because the French site is blocked from this session.
  - For 2018–26 I relied on the macro programme's verified daily values and on iShares ETF returns.
  - ETFs are long-only factor tilts, not long/short factors.
- **Stocklake data are indicative (T3).** The prices are a vendor feed and price-only, and the feed changed source in late July and August 2026 (volume field truncated; "ibkr" source from 12 Aug).
- **Korean momentum returns depend on how they are built.** A monthly-log construction gave slightly different worst months (for example, Oct 2019 −27.5% VW). The figures above use within-month daily buy-and-hold.
- **The driver of the Oct 2019 Korean momentum crash is unidentified.**

## 2. Mechanisms: crowding, leverage, deleveraging cascades and short squeezes

### Takeaway
Factor crashes come from three channels that interact:
1. **Leverage and funding:** margin calls and prime-broker financing (Aug 2007, Archegos 2021).
2. **Synchronous de-risking driven by risk limits:** internal volatility targets, VaR limits and pod stop-outs (Aug 2024, Mar 2025, Jul 2026).
3. **A regime or thesis shock that flips a crowded exposure** (2009 rebound, 9 Nov 2020, DeepSeek).

A short squeeze is channels 1 and 2 acting on a crowded short leg. Crowding is the precondition; the trigger is whatever forces the marginal holder to sell.

### Cited Findings
- **Khandani–Lo: the unwind hypothesis.**
  - Losses arose from the rapid unwinding of one or more large market-neutral portfolios, followed by de-leveraging by others.
  - The unwind began in July 2007, in financials and in long book-to-market, short earnings-momentum exposures.
  - A simulated market-making strategy lost significantly in the week of 6 Aug but earned before and after it: risk capital withdrew from 8 Aug.
  - Rising serial correlation of hedge-fund returns from 2000 to 2007 signalled falling liquidity in the sector.
  - Leverage crept up as alpha decayed. The strategy's average daily return was 0.57% in 1998, when 2:1 leverage reached its target; by 2007 it was 0.13%, needing about 9:1.
  - KL call the 10 Aug rebound "a tell-tale sign of a liquidity trade".
  - Sources: [KL 2007](https://web.mit.edu/Alo/www/Papers/august07.pdf); [NBER w14465](https://www.nber.org/papers/w14465).
- **Daniel–Moskowitz: momentum behaves like a written call.**
  - After bear markets, momentum's payoff resembles a short call on the market: up-market beta −1.51 against down-market beta −0.70.
  - Crashes are partly forecastable from a bear-market, high-volatility state.
  - Source: [D-M NBER w20439](https://www.nber.org/papers/w20439).
- **Lou–Polk.** When comomentum is high, crowded momentum trading pushes prices away from fundamentals, and strong subsequent reversals follow ([RFS 2022](https://econpapers.repec.org/article/ouprfinst/v_3a35_3ay_3a2022_3ai_3a7_3ap_3a3272-3302..htm)).
- **Hanson–Sunderam.** Arbitrage capital in value and momentum, inferred from the cross-section of short interest, grew from the late 1980s and lowered strategy returns. That capital is most limited exactly when the strategies perform best ([RFS 2014](https://econpapers.repec.org/article/ouprfinst/v_3a27_3ay_3a2014_3ai_3a4_3ap_3a1238-1286..htm)).
- **Fed FSR, Nov 2024.**
  - The August 2024 volatility spike appears related to highly leveraged hedge funds that had to deleverage other positions quickly. They did so largely to meet internal volatility targets, not because of margin or funding pressure from creditors (p. 34).
  - Average hedge-fund leverage was at or near the highest since the data began in 2013 (p. 32).
  - Source: [Fed FSR Nov 2024](https://www.federalreserve.gov/publications/files/financial-stability-report-20241122.pdf).
- **BIS Bulletin 90.**
  - On 5 Aug 2024 the VIX spike far exceeded what its historical relationship with the market move implied.
  - Margin requirements were raised, and procyclical deleveraging forced volatility-sensitive strategies to unwind ([BIS](https://www.bis.org/publ/bisbull90.pdf)).
  - The fetched summary put the margin increases at 60–80% for equity-index positions and 43% for JGB futures. I have not checked these against the page.
- **Fed FSR, May 2021: the Archegos chain.** Price declines in concentrated positions financed by total-return swaps triggered margin calls. The resulting sales caused further price declines and substantial bank losses (p. 42). A few hedge funds with large shorts lost money in the January 2021 meme episode, but the sector-wide effect was limited ([Fed FSR May 2021](https://www.federalreserve.gov/publications/files/financial-stability-report-20210506.pdf)).
- **SEC staff report on early 2021.**
  - In GME, short covering contributed to price rises in discrete windows, but buying to cover was a small fraction of total buy volume.
  - Positive sentiment sustained the move, and staff found no evidence of a gamma squeeze.
  - Source: [SEC 2021](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf).
- **GS, March 2025.** The momentum drawdown of 7–10 Mar 2025 exceeded 4 SD and triggered forced de-risking across many kinds of hedge-fund strategy ([GS 2025](https://marquee.gs.com/welcome/news/views-from-the-trading-floor/2025-in-review)).
- **Press, July 2026.**
  - Elevated value-at-risk constraints forced hedge funds to cut exposure as the market rotated out of AI beneficiaries ([Hedgeweek 7 Jul 2026](https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/)).
  - A heavily leveraged AI-focused fund was forced to liquidate its equity portfolio during the July 2026 momentum crash ([Yahoo 31 Jul 2026](https://finance.yahoo.com/markets/stocks/articles/july-ends-hopeful-note-stocks-222100309.html)).
- **Pod mechanics.**
  - A Millennium PM with $1bn who loses 5% has the capital halved. A total loss of 7.5% of the original allocation likely ends the mandate, with occasional exceptions ([Business Insider via AOL, Oct 2024](https://www.aol.com/strategy-69-billion-hedge-fund-193733084.html)).
  - The same 50% cut at 5% and possible dismissal at 7.5% were reported for Millennium's 340+ teams ([Hedgeweek, Mar 2025](https://www.hedgeweek.com/millennium-posts-rare-monthly-loss-amid-index-rebalancing-trades/)).
- **ETFs as a transmission channel.** Through the arbitrage mechanism, ETFs pass liquidity shocks into their underlying stocks. Stocks with high ETF ownership show higher volatility, more negative autocorrelation and a premium of up to 56 bp a month ([Ben-David, Franzoni, Moussawi, JF 2018](https://econpapers.repec.org/article/blajfinan/v_3a73_3ay_3a2018_3ai_3a6_3ap_3a2471-2535.htm)).
- **Liquidity provision pays in stress.**
  - Reversal-strategy returns are predictable with the VIX and surge in stress, as in 2007–09, when intermediaries withdraw ([Nagel, NBER w17653](https://www.nber.org/papers/w17653)).
  - **Local, Korean STR (EW):** +25.8% in Apr 2020 and +4.2% in Jul 2026.
  - **Concentration can flip this.** VW STR lost 32.0% in Oct 2025 and 35.3% in May 2026, because its short leg held the runaway mega-caps (local).

### Inferences
- **"My stop is your crash."** The controls that protect each individual fund are the system's propagation channel: volatility targets, VaR limits and pod stops. QUANTGEN is too small to move prices, but the same events will trip its rules. A rule keyed to drawdown or volatility *after the fact* will therefore sell near the low, alongside the crowd.
- **Reversal and liquidity-provision sleeves are natural shock absorbers in forced-selling unwinds.** This supports R-05: reversal is never cut in stress. The exception is concentration in the short leg, which needs name caps.
- **Squeeze risk belongs to the short leg's crowding and attention, not to the factor.** It needs name-level filters (short interest / float, borrow), not a factor-level rule.
- **Leverage creep (KL) is the slow precondition that turns a shock into a crash.** QUANTGEN's exposure cap of 1.0 (R-01) is its main structural defence.

### Gaps
- No quantitative split of the July 2026 US crash between the leveraged-fund liquidation and broader de-grossing (press only).
- Korean margin debt and leveraged single-stock ETF assets through July 2026 not tested (macro BL-U01).
- The BIS margin-increase percentages and some Fed page references come from fetched summaries, not page-level reading.

## 3. Crowding measures: do they predict crashes or only describe them?

### Takeaway
- **Crowding measures mostly describe, and at best forecast the distribution over months to years; they do not time crashes.**
  - Comomentum has the strongest published predictive evidence: lower post-formation returns and fatter left tails (US 1965–2015).
  - Holdings-based proxies are contested: they relate *negatively* to crash risk in Barroso–Edelen–Karehnke.
  - Short-interest crowding explains long-run decay.
  - 13F is late and long-only.
  - ETF flows raise volatility.
- **The visible pre-crash cases are anecdotes without published hit rates.** Crowding was visibly extreme just before Nov 2020 and Jul 2026.
- **For QUANTGEN:**
  - Crowding is displayed context.
  - Concentration is already an acting cap (R-07).
  - Own volatility already embeds much of the crowding information.

### Cited Findings
- **Lou & Polk, RFS 2022 (US, 1965–2015).**
  - *Definition.* Comomentum is the average pairwise correlation of weekly returns among the extreme momentum deciles over the 52-week formation window. Returns are FF3 residuals, adjusted for industry.
  - *Returns.*
    - In the formation year, momentum earns 2.59% a month more in the top comomentum quintile than in the bottom (t 2.45).
    - In year 2 after formation it earns 1.08% a month less (t −2.75).
    - Years 1–2 together: −1.07% a month (t −3.35); FF5-adjusted −0.95% (t −2.87).
  - *Tail frequency.*
    - In months 1–3, 22.5% of days fall below −1% when comomentum is high, against 8.4% when it is low.
    - In months 1–12, 9.3% of weeks fall below −5%, against 1.5%.
  - *Who drives it.* Comomentum rises with institutional ownership of winners and with hedge-fund AUM. The first principal component of comomentum and its value analogue correlates 0.583 with log hedge-fund AUM.
  - *Placebo.* The pre-1965 sample shows no predictability (0.15%, t 0.33).
  - Sources: [Lou–Polk PDF](https://personal.lse.ac.uk/polk/research/Comomentum.pdf); [RFS record](https://econpapers.repec.org/article/ouprfinst/v_3a35_3ay_3a2022_3ai_3a7_3ap_3a3272-3302..htm).
- **Barroso, Edelen & Karehnke, JFQA 2022.**
  - In their model, crowding predicts crash risk only if arbitrageurs ignore feedback effects.
  - Empirically, crowding proxies built from institutional holdings are generally *negatively* related to expected crash risk.
  - They conclude this casts doubt on crowding as a stand-alone source of tail risk.
  - Source: [EconPapers](https://econpapers.repec.org/article/cupjfinqa/v_3a57_3ay_3a2022_3ai_3a4_3ap_3a1313-1342_5f3.htm).
- **Hanson & Sunderam, RFS 2014.** Arbitrage capital, measured from short interest, grew and lowered value and momentum returns ([EconPapers](https://econpapers.repec.org/article/ouprfinst/v_3a27_3ay_3a2014_3ai_3a4_3ap_3a1238-1286..htm)).
- **Chincarini, Lazo-Paz & Moneta, JBF 2026.**
  - Anomaly alphas come mainly from the *most* crowded long-leg stocks and the *least* crowded short-leg stocks, and this persists after publication.
  - Crowding raises institutions' exposure to crashes.
  - Source: [IDEAS](https://ideas.repec.org/a/eee/jbfina/v182y2026ics0378426625001992.html).
- **MSCI, 13 Nov 2020.**
  - Short interest in the momentum factor had built since early July and exceeded 3 SD above its mean in early October.
  - MSCI's factor crowding model showed momentum and residual volatility as elevated on 6 Nov, three days before the 9 Nov crash.
  - Source: [MSCI](https://www.msci.com/research-and-insights/blog-post/are-momentum-wings-finally-starting-to-melt).
- **Hedgeweek, 7 Jul 2026.** A momentum positioning index hit its highest level since the series began in 2002. This was reported *during* the first two weeks of the crash ([Hedgeweek](https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/)).
- **SEC Form 13F rules.**
  - Filing is due within 45 days after quarter end.
  - Managers with at least $100m in 13(f) securities must file.
  - Short positions are not reported, and must not be netted against longs.
  - Source: [SEC FAQ](https://www.sec.gov/divisions/investment/13ffaq.htm).
- **Ben-David, Franzoni & Moussawi, JF 2018.** ETF ownership raises stock volatility and negative autocorrelation ([EconPapers](https://econpapers.repec.org/article/blajfinan/v_3a73_3ay_3a2018_3ai_3a6_3ap_3a2471-2535.htm)).
- **Factor ETFs carry large sector bets.** Information-technology weights on 29 Sep 2026 were MTUM 54.3%, VLUE 43.1%, QUAL 38.7% and USMV 33.3%. Flows into "different" factor ETFs are partly flows into the same sector ([iShares MTUM](https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf)).
- **Macro BL-C14: public triggers come late.**
  - US momentum lost 5.9% from 11 Jul to 2 Aug 2024, before the trigger. It then gained 6.5% from 6 to 30 Aug, the window a crowding cut would have removed.
  - The factor's own volatility already tracks crowding: the US momentum vol-scale weight was 0.53 in Jul 2026 and 0.31 in Nov 2020.
- **Factor momentum (Ehsani & Linnainmaa).** Factor returns are positively autocorrelated: the average factor earns 1 bp a month after a losing year and 53 bp after a winning year. Factor momentum explains stock momentum ([NBER w25551](https://www.nber.org/papers/w25551)).
- **Local, Korea: two real-time concentration measures, both free of reporting lags.**
  - *Top-two share of the VW winner decile:* 31.2% (Oct 2025), 77.1% (May 2026), 79.9% (Jun 2026), 85.4% (Jul 2026).
  - *Samsung + SK hynix share of KOSPI common-share market cap:* 23.1% (Jun 2025), 35.1% (Dec 2025), 57.1% (Jun 2026), 52.6% (Sep 2026).

### Inferences
- **Predict or describe?** The strongest evidence (Lou–Polk) predicts the *distribution* of returns over the next 1–24 months: a lower mean and a fatter left tail. That makes it a sizing input, not a switch. Given BEK's contrary finding, a crowding score must not act until it passes the pre-registered test already defined in BL-C14: it must lead own-factor volatility by ≥ 5 days in ≥ 3 of 5 episodes, *and* add value beyond vol-scaled sizing.
- **Timeliness:**
  - 13F holdings are up to ~135 days stale and blind to shorts and swaps; Archegos's total-return-swap positions would not have appeared.
  - Vendor crowding models are opaque.
  - Only correlation-based measures (comomentum) and concentration measures can be computed daily from prices that QUANTGEN already reads.
- **Korea.** In 2025–26 the crowding measure that mattered was concentration. R-07 already acts on it at the book level; the sleeves need the same discipline (§5, RL-2).

### Gaps
- No published out-of-sample hit rate for MSCI's crowding model or for bank positioning indices.
- Korean comomentum, short-sale balances and foreign-ownership crowding not tested in this session (DC-06).
- FINRA short-interest reporting frequency and the dates of Korea's short-selling ban and resumption not verified in this session.

## 4. Controls with evidence: what demonstrably worked

### Takeaway
The evidence ranks the controls as follows:
1. **Own-volatility scaling for momentum** is robust in US (1926–2026), international and Korean data. It was the only rule switched on in the July 2026 crash.
2. **Neutral construction plus name and sector caps** is cheap. It removes concentration crashes but does not prevent factor crashes.
3. **A book-level volatility target** is risk control; it is Sharpe-neutral (macro).
4. **Drawdown ladders** are useful only at book level, with thresholds scaled to volatility and an explicit re-arm rule. Applied per sleeve, they destroy value.
5. **Name-level stop-losses** add value only where returns trend (the Kaminski–Lo condition). On KRX they nearly halve momentum's Sharpe.
6. **The Daniel–Moskowitz bear gate** has the right sign, but the sample is thin and it misses crashes that come in bull markets.
7. **Volatility scaling of value, quality or reversal** shows no systematic out-of-sample benefit.

### Cited Findings

**4.1 Stop-loss rules**

**Kaminski & Lo (JFM 2014)**
- **Definition.** The stopping premium is the change in expected return caused by a stop rule.
- **Theory:**
  - Under a random walk, a stop-loss always lowers expected return.
  - Under momentum it can add value. A sufficient condition is that the autocorrelation exceeds the Sharpe ratio.
  - Under mean reversion it hurts.
  - Under regime switching, its value depends on how accurately it identifies the low-return regime.
- **Empirics (MIT open-access manuscript).** US equity futures switching into long Treasuries, daily data from Jan 1993 to Nov 2011:
  - Stop rules over monthly intervals raised return by about 1.5% and cut volatility by about 5%, raising the Sharpe ratio by up to 20%.
  - Short-horizon stop rules had negative stopping premiums across wide parameter ranges.
- Source: [MIT PDF](https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf).

**Han, Zhou & Zhu (SSRN 2407199, revised Sep 2016)**
- **Sample and rule.** US stocks from Jan 1926 to Dec 2013. Each stock in the momentum portfolio has its own stop, monitored daily; a stopped position sits in cash for the rest of the month.
- **At a 10% stop.**
  - The worst month of EW momentum went from −49.79% to −11.36%; of VW momentum, from −64.97% to −23.28%.
  - The Sharpe ratio more than doubled.
- **Working paper, at a 15% stop.**
  - EW: worst month −17.43%; mean return 0.99% → 1.93% a month; monthly Sharpe 0.165 → 0.399.
  - VW: worst month −22.10%; mean return 0.74% → 1.42%; monthly Sharpe 0.107 → 0.251.
  - The break-even trading cost is 3.18–5.71%.
- **Caveats.** In-sample, US only, with intra-month execution at the stop level.
- Sources: [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2407199); [WP PDF](https://smallake.kr/wp-content/uploads/2017/03/SSRN-id2407199.pdf).

**Local KRX replication**
- **Rule.** 15% stop per stock, measured from the formation-month close. Triggered at the close and exited from the next session. About 70 bp is charged per stopped round trip.
- **Sample.** January 2000 to September 2026, in-sample.

| Sleeve | Static gross SR | Stop gross SR | Static net SR | Stop net SR | Worst month, static → stop (gross) | Jul 2026, static → stop (gross) | Mar–May 2009, static → stop (gross) |
|---|---|---|---|---|---|---|---|
| WML EW | 0.43 | 0.26 | 0.20 | −0.17 | −24.8% → −15.4% | −24.8% → −14.2% | −21.3% → −4.3% |
| WML VW | 0.52 | 0.36 | 0.36 | 0.06 | −29.6% → −22.3% | −29.6% → −21.6% | −35.3% → −18.2% |
| STR EW | 0.32 | 0.31 | −0.29 | −0.54 | −19.5% → −17.2% | +4.2% → +0.9% | — |
| STR VW | 0.17 | 0.24 | −0.27 | −0.36 | −35.3% → −23.1% | +7.8% → +9.6% | — |

The stop barely changed maximum drawdown: EW gross −70.6% → −70.4%; VW gross −72.8% → −74.9%.

**Kaminski–Lo condition checked locally (monthly, 2000–2026)**

The condition holds when a sleeve's monthly AR(1) is at least its monthly Sharpe ratio.

| Series | AR(1) | Monthly SR | Condition |
|---|---|---|---|
| KR WML EW | −0.009 | 0.117 | not met |
| KR WML VW | +0.148 | 0.139 | met, but marginal (SE ≈ 0.057) |
| KR STR EW | +0.079 | 0.083 | not met |
| KR STR VW | +0.126 | 0.047 | met |
| US French Mom (1949–2017) | +0.039 | 0.179 | not met |
| US French HML (1949–2017) | +0.159 | 0.129 | met |

Korean individual stocks: the median daily AR(1) is +0.033, but the median weekly AR(1) is −0.024, and 63% of 3,556 stocks have a negative weekly AR(1).

**Other**
- Research Affiliates' "Stop the Losses!" (Oct 2025) reports that stops reduce drawdowns and skewness for alternative risk premia and trend strategies. Its numbers were not accessible ([page](https://www.syzygyassetmanagement.com/insights/publications/articles/1099-stop-the-losses)).

**4.2 Volatility management**

**Barroso & Santa-Clara (JFE 2015): US, Jul 1926 – Dec 2011**
- **Scaling rule.** Scale momentum by its six-month realised variance, targeting 12% volatility.

| Statistic | Plain WML | Scaled WML |
|---|---|---|
| Sharpe | 0.53 | 0.97 |
| Mean return | 14.46% | 16.50% |
| Volatility | 27.53% | 16.95% |
| Skew | −2.47 | −0.42 |
| Excess kurtosis | 18.24 | 2.68 |
| Worst month | −78.96% | −28.40% |
| Maximum drawdown | −96.69% | −45.20% |

- **Why it works.** Momentum's variance is forecastable: out-of-sample R² is 57.82%.
- **Cost.** Monthly turnover is 74% for the plain WML and 75% scaled, so scaling adds little. Round-trip break-even costs are 1.27 and 1.75 pp respectively.
- **Other markets.** Similar results in France, Germany, Japan and the UK (1980–2011).
- Sources: [JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002566); [PDF copy](http://www.snifferquant.com/gyantal/Incode/papers/Momentum%20Has%20Its%20Moments(scaling%20Momentum%20by%20vol),2014.pdf).

**Moreira & Muir (NBER w22208; JF 2017): 1926–2015**
- **Scaling rule.** Scale each factor by the inverse of the prior month's variance.
- **Annualised alphas:**

  | Factor | Alpha |
  |---|---|
  | Momentum | 12.51% |
  | ROE | 5.48% |
  | Market | 4.86% |
  | FX carry | 2.78% |
  | RMW | 2.44% |
  | HML | 1.97% |
  | IA | 1.55% |
  | CMA | 0.38% |
  | SMB | −0.58% |

- **Market factor.** Sharpe +25%; break-even cost 56 bp. Under a 1.5× leverage cap about 45% of the utility gain remains.
- Source: [NBER PDF](https://www.nber.org/system/files/working_papers/w22208/w22208.pdf).

**Cederburg, O'Doherty, Wang & Yan (JFE 2020): 103 strategies**
- **Spanning regressions look good.** Alphas are positive in 77 cases (23 significantly positive, 3 significantly negative).
- **Direct comparisons are a coin toss.** Volatility management wins 53 times and loses 50.
- **Real-time combinations fail.** Real-time combinations lower the certainty-equivalent return in 72 of 103 cases.
- **Why.** The underlying spanning regressions are structurally unstable.
- **Where it does help.** Per a secondary summary (T3), consistent gains are concentrated in momentum, profitability and betting-against-beta.
- Sources: [JFE abstract](https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X); [summary](https://alphaarchitect.com/the-performance-of-volatility-managed-portfolios/).

**Macro programme (verified golden values)**
- **US momentum with R-03** (σ126, 12% target, cap 1): Sharpe 0.399 → 0.714 gross, 0.672 net of 50 bp. Adding R-04 gives 0.798 gross.
- **Constant-volatility scaling of other factors** (cap 2), ΔSharpe:

  | Factor | Since 2020 | Full 1990–2026 |
  |---|---|---|
  | ST_Rev | −0.31 | +0.13 |
  | CMA | −0.16 | −0.06 |
  | RMW | −0.10 | +0.02 |
  | HML | −0.08 | −0.03 |

**Local, US (French monthly, 1949–2017; trailing six-month σ, 12% target, cap 1)**
- Sharpe 0.62 → 0.77; maximum drawdown −57.6% → −28.5%.
- Mar–May 2009: −49.3% → −24.4%.
- Calendar 2016: −17.5% → −16.7%. Without a volatility spike, scaling does not help.

**Local, Korea (σ126 daily, 12% target, cap 1, net of 35 bp, 2000–2026)**

| Sleeve | Sharpe | Max drawdown | July 2026 |
|---|---|---|---|
| WML EW, static → scaled | 0.20 → 0.31 | −81.2% → −55.0% | −25.2% → −7.5% |
| WML EW, same-exposure static (0.58×) | 0.20 | −59.5% | — |
| WML VW, static → scaled | 0.36 → 0.41 | −78.5% → −41.0% | — |
| WML VW, same-exposure static (0.40×) | 0.36 | −42.1% | — |

- **23 Jun – 30 Jul 2026 window.** Scaled EW lost 13.1% against 24.8% for its same-exposure static book; scaled VW lost 10.1% against 22.6%.
- **Reversal.** Scaling does not rescue a sleeve whose net edge is negative: STR EW net Sharpe −0.29 → −0.59.
- **Weights decided at the close.** 22 Jun 2026: 0.35 (EW) and 0.20 (VW). 30 Sep 2019: 0.77 and 0.65. The Oct 2019 crash therefore struck at near-full size, and was the scaled sleeves' worst month (−13.1% EW, −14.3% VW).

**4.3 Bear-state gate (Daniel–Moskowitz)**
- **The published result.** Crash risk sits in bear-market, high-volatility states. The dynamic strategy roughly doubles the Sharpe ratio ([NBER w20439](https://www.nber.org/papers/w20439)).
- **Figures verified by the macro programme** (JFE Table 7, 1934–2013):
  - US: 0.682 static → 1.041 constant volatility → 1.194 dynamic.
  - Europe 0.462 → 1.130; Japan 0.067 → 0.416; UK 0.465 → 0.891.
- **Macro R-04 (floor 0.5).**
  - Add-on Sharpe +0.084 gross and +0.072 net.
  - Seven spell onsets, so the verdict is INSUFFICIENT DATA.
  - It misses bull-market crashes: Nov 2020 −12.0%, Jul 2026 −10.9%, Jan 2001 −21.9%.
- **Local, Korea.**
  - *Gate definition:* KOSPI cap-weighted 24-month return below zero, and σ126 above its expanding two-thirds quantile.
  - *How often it is on:* 3.9% of days since 2000 (245 sessions, about 5 onsets).
  - *Returns while on vs off:* WML EW earns −19.8% a year gross when the gate is on, against +11.9% when off. WML VW earns −47.7% against +21.2%.
  - *Gain at a 0.5 floor:* the Sharpe ratio rises from 0.43 to 0.45 (EW) and from 0.52 to 0.55 (VW), gross.
  - *Misses:* the gate was off in Oct 2019 (σ126 12.8%, below its quantile of 26.3%) and in Jul 2026 (24-month return +235%). Those were the two worst months.

**4.4 Neutral construction and caps**
- **Residual momentum.** Ranking stocks on residual returns roughly doubles risk-adjusted momentum profits, is more consistent over time and is less concentrated in the extremes. Ranking on total returns carries large, time-varying Fama–French exposures ([Blitz, Huij & Martens, JEF 2011](https://econpapers.repec.org/article/eeeempfin/v_3a18_3ay_3a2011_3ai_3a3_3ap_3a506-521.htm)).
- **Momentum's market beta changes with the state.** Its up-market beta of −1.51 against a down-market beta of −0.70 is the time-varying exposure that beta-neutralisation targets (D-M).
- **The August 2007 unwind ran through common exposures:** financials, book-to-market and earnings momentum (KL).
- **After 9 Nov 2020, quants hunted for accidental factor exposures with risk models** ([Bloomberg 22 Nov 2020](https://www.bloomberg.com/news/articles/2020-11-22/chaos-in-factor-land-puts-quants-on-hunt-for-accidental-exposure)).
- **Local, Korea, with a 5% name cap on the VW sleeve:**

  | Measure | Uncapped → capped |
  |---|---|
  | Gross Sharpe | 0.52 → 0.46 |
  | Net Sharpe | 0.36 → 0.27 |
  | Net Sharpe, 2016–26 | → −0.00 |
  | May 2026 | +77.0% → +17.8% |
  | Jul 2026 | −29.6% → −30.7% |
  | Mar–May 2009 | −35.3% → −29.6% |

**4.5 Drawdown-based de-grossing: pod limits and ladders**

**Pod limits**
- At Millennium, a 5% loss halves a team's capital, and a 7.5% loss likely means dismissal.
- Annual staff turnover is about 15–20%; the platform has $69–75bn of AUM and more than 340 teams.
- Sources: [Business Insider via AOL](https://www.aol.com/strategy-69-billion-hedge-fund-193733084.html); [Hedgeweek](https://www.hedgeweek.com/millennium-posts-rare-monthly-loss-amid-index-rebalancing-trades/).

**How deep a normal drawdown is: Rej, Seager & Bouchaud ([arXiv 1707.01457](https://arxiv.org/abs/1707.01457))**
- Managers and investors underestimate how long and how deep drawdowns get, given a strategy's Sharpe ratio.
- For a 10-year track with Sharpe 0.5, there is a 5% chance of a drawdown lasting seven years or more.
- Their fitted 5%-tail scalings:
  - length ≈ 2.14 / SR² years;
  - depth ≈ 1.50 / SR, in units of annual volatility.

**Local Brownian benchmark: probability that the maximum drawdown reaches −8% / −12% / −15%**

| Volatility, true SR | Within 1 year | Within 3 years | Within 10 years |
|---|---|---|---|
| 6%, 0.5 | 0.17 / 0.02 / 0.00 | 0.55 / 0.18 / 0.07 | 0.95 / 0.59 / 0.33 |
| 8%, 0.5 | 0.38 / 0.10 / 0.03 | 0.83 / 0.42 / 0.22 | 1.00 / 0.88 / 0.65 |
| 8%, 0.3 | 0.45 / 0.13 / 0.04 | 0.89 / 0.53 / 0.31 | 1.00 / 0.94 / 0.79 |
| 10%, 0.5 | 0.59 / 0.23 / 0.10 | 0.95 / 0.65 / 0.41 | 1.00 / 0.98 / 0.87 |
| 10%, 1.0 | 0.44 / 0.12 / 0.05 | 0.86 / 0.42 / 0.20 | 1.00 / 0.86 / 0.58 |
| 12%, 0.5 | 0.75 / 0.37 / 0.19 | 0.99 / 0.82 / 0.60 | 1.00 / 1.00 / 0.97 |

**Local ladder tests, in-sample, using the R-07 levels**
- **Ladder A (non-cumulative):** at −8%, exposure × 0.5; at −12%, × 0.5 with no new entries; at −15%, zero for 10 sessions.
- **Ladder B (cumulative):** × 0.25 at −12%.
- Costs are charged on every change in exposure.

*Variant 1: re-arm at 1.0, with the reference peak reset.*

| Book | Sharpe | Max drawdown | Halts | Episode windows |
|---|---|---|---|---|
| KOSPI cap-weighted 2000–26 (35 bp), ladder A | 0.42 → 0.34 | −55.7% → −53.6% | 26 since 2000 (≈1.0 a year) | 23 Jun–30 Jul 2026: −38.6% → −23.9%. 30 Jul–30 Sep 2026: +22.8% → +7.9%. H1 2026: +101.1% → +55.2%. |
| KOSPI, ladder B | 0.42 → 0.39 | −55.7% → −49.3% | — | — |
| SPY 1998–2021 (50 bp), ladder A | 0.41 → 0.25 | −56.5% → −63.9% | — | GFC window: −47.1% → −31.2%. 2020 crash: −34.1% → −15.9%. |
| SPY, ladder B | 0.41 → 0.02 | — | — | 2009 rebound: +35.0% → +2.1% |
| KR WML EW, per sleeve (net) | 0.20 → 0.03 | — | 45 | — |
| KR WML VW, per sleeve (net) | 0.36 → 0.26 | −78.5% → −83.7% | — | — |
| KR STR EW, per sleeve (net) | −0.29 → −0.59 | — | — | — |
| KR WML VW vol-scaled, per sleeve (net) | 0.41 → 0.09 | — | — | — |

*Variant 2: keep the all-time high-water mark as the reference after a HALT.* This is a death spiral:

| Book | Halts a year | Sharpe |
|---|---|---|
| SPY | 21 | −2.55 |
| KOSPI | 22 | −1.69 |
| KOSPI VT8 | 22 | −4.53 |
| KR WML VW vol-scaled | 22 | −5.63 |

*Variant 3: re-arm at 0.5, reset the reference at re-arm, return to 1.0 after a +4% gain from the re-arm NAV.* Results from 2000 onward:

| Book | Sharpe | Max drawdown | Halts a year | Episode windows and notes |
|---|---|---|---|---|
| SPY | 0.34 → 0.21 | −56.5% → −48.8% | 0.38 | GFC: −47.1% → −23.8%. 2009 rebound: +35.0% → +15.2%. 2020 crash: −34.1% → −15.9%. 2020 rebound: +45.0% → +38.3%. |
| KOSPI | 0.42 → 0.40 | −55.7% → −41.3% | 0.67 | Jul 2026 window: −38.6% → −21.3%. H1 2026: +101.1% → +49.0%. Below full exposure on 61% of days. |
| KOSPI VT20 (analogue of macro R-06) | 0.40 → 0.37 | −47.5% → −34.7% | 0.49 | Jul 2026: −12.3% → −11.7%. H1 2026: +50.5% → +41.7%. |
| KOSPI VT20, σ-scaled thresholds | 0.40 | −37.4% | 1 halt in total | Thresholds at −1.0σ / −1.5σ / −1.9σ of trailing 252-day volatility. |
| KOSPI VT8 | 0.23 → 0.29 | −32.6% → −27.7% | 0.15 | — |
| KR WML VW vol-scaled, fixed thresholds | 0.41 → 0.14 | — | — | — |
| KR WML VW vol-scaled, σ-scaled thresholds | 0.41 → 0.27 | — | — | — |
| SPY VT8 | 0.10 → 0.04 | −36.2% → −20.0% | — | Below full exposure on 96% of days: the +4% probation rarely clears in a low-volatility, low-return book. |

*Drawdown deepening (local, 2000 onward; an episode runs from one peak to the next).*

| Series | Reached −15% after −12% | Reached −12% after −8% |
|---|---|---|
| KOSPI | 9 of 10 | 67–75% across the series |
| KR WML EW, net | 7 of 9 | |
| KR WML VW, net | 10 of 12 | |

**4.6 Capacity, liquidity and turnover**
- **Leverage creep signals crowding.** Matching 1998 returns took 2:1 leverage in 1998 and about 9:1 by 2007 (KL).
- **Live trading costs are low.** Live execution data ($1.7 trillion across 21 developed markets over 19 years) put actual costs an order of magnitude below earlier estimates ([Frazzini, Israel & Moskowitz, "Trading Costs", SSRN 3229719](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3229719)). Per-strategy capacity numbers were not fetched.
- **Local, Korea: costs at 35 bp per side.**
  - Average monthly one-way name turnover per leg: WML 30% (long) and 35% (short); STR 89% and 88%.
  - The cost hit to Sharpe:

    | Sleeve | Gross | Net |
    |---|---|---|
    | STR EW | 0.32 | −0.29 |
    | WML EW | 0.43 | 0.20 |
    | WML VW | 0.52 | 0.36 |

**4.7 What Barra- and Axioma-style risk models offer**
- **MSCI's range.**
  - More than 70 equity factor models covering over 90,000 securities, 49 industries and more than 85 countries.
  - Style, sector and macro factors, with long, medium and trading horizons.
  - Single-country models include Korea.
  - Crowding is sold as a separate product.
  - Source: [MSCI](https://www.msci.com/data-and-analytics/factor-investing/equity-factor-models).
- **What they did in Nov 2020.** After 9 Nov 2020, MSCI researchers used risk models to diagnose the small-cap rally. The obvious size and value factors did not explain it well (Bloomberg, 22 Nov 2020).

### Inferences
- **Momentum:** size it by its own volatility (R-03). This is robust, and it was the only rule switched on in July 2026. It does not cover crashes that start from a low-volatility state (Korea Oct 2019, US 2016), so neutral construction and caps are still needed.
- **Stop-losses:** they are justified only where the Kaminski–Lo condition holds *at the level where the stop is applied*. Weekly returns of Korean stocks mean-revert, so name-level stops sell into reversals. The KRX test shows the Sharpe loss even though the worst month shrinks.
- **Ladders:**
  - **A fixed-percentage threshold is really a statement in units of volatility.** −8% is 1σ at 8% volatility, but only 0.3σ for a 25%-volatility sleeve.
  - **They work only as a tail device.** That requires applying them at book level after a volatility target, with thresholds scaled to volatility.
  - **The re-arm rule matters as much as the trigger.**
- **Risk models** decompose exposures and forecast covariance. That is useful for neutrality, caps and attribution. They do not forecast crash dates, and a covariance estimated over calm windows understates crash correlations.
- **Pod limits** are a manager-selection device. Their false-positive rate is acceptable only when capital can be reallocated across hundreds of teams.

### Gaps
- **HZZ's fill assumption was not verified,** i.e. whether stopped positions fill at the stop price or at the next open. No US stock-level replication was possible in this session, for lack of daily US stock data.
- **Research Affiliates' 2025 numbers and Axioma's documentation were not accessible.**
- **The ladder variants are in-sample on single histories.** The re-arm parameters (0.5 exposure, +4% probation) are my judgment, not tuned, and must be pre-registered before any gate run.
- **The Cederburg exception list comes from a T3 summary.** The JFE abstract confirms the 53/50 and 72/103 counts.

## 5. QUANTGEN translation: the risk layer for stock-level technical and fundamental sleeves

### Takeaway
The stock-level sleeves need a risk layer that does three things. It prevents concentration and unintended exposure *by construction*. It sizes momentum by its own volatility. And it keeps every mechanical stop at the book level, where it acts only in the tail.

No name-level price stops are imposed. Crowding is shown, not acted on. Each card is reviewed on statistical evidence, never liquidated automatically, except through the macro HALT.

The layer is consistent with the macro spec (R-03 to R-08). It corrects three under-specified points of R-07: the scope, the threshold units and the re-arm rule.

### Cited Findings (evidence behind each rule)

**Order of operations.** Decide at the close of day t; earn from t+1.
1. **RL-3**: eligibility and liquidity.
2. **RL-1 / RL-2**: build each sleeve neutral, with caps applied.
3. **RL-4**: turnover controls.
4. **RL-5**: sleeve sizing. The momentum family uses R-03 × R-04; reversal and quality are fixed at 1.0 (R-05).
5. Fixed risk budgets across sleeves, from the per-market priors normalised to sum to 1.
6. Book caps: the R-07 Korea pair and semiconductor caps, single names, sectors.
7. **RL-6**: the book-level volatility target (R-06).
8. **RL-7**: the drawdown ladder on book NAV.
9. **R-08**: entry blocks.
10. The costed simulated book.

Monitoring runs alongside: RL-8 (review triggers), RL-9 (crowding display), RL-10 (stress table) and RL-11 (short-leg filters).

| Rule | Class | Specification | Evidence (numbers; see §1–§4) | Status |
|---|---|---|---|---|
| **RL-1 Neutral construction** | Card-definition convention, pre-registered | **Long/short sleeves:**<ul><li>Rank scores within sector (KRX sectors; GICS for the US).</li><li>Make them beta-neutral: rolling 252-day beta, shrunk toward 1, so that the sleeve's ex-ante \|β\| ≤ 0.10.</li><li>Make them size-neutral by taking the score's residual on log market cap.</li><li>Momentum ranks on residual returns (market + sector, 12-1 window).</li></ul>**Long-only sleeves:** active sector weight within ±5 pp of the benchmark, and active beta within ±0.15 *(levels are judgment)*. | Residual momentum roughly doubles risk-adjusted profit (Blitz–Huij–Martens). Momentum's beta asymmetry is −1.51 vs −0.70 (D-M). The Aug 2007 losses ran through common exposures (KL). Quants hunted accidental exposures after Nov 2020. US factor ETFs carry 33–54% IT. | **BUILD** |
| **RL-2 Caps** | INVARIANT | <ul><li>Single name ≤ 5% of NAV (R-07).</li><li>Long/short research sleeves: ≤ 2% of sleeve gross per name, i.e. at least 50 names a side.</li><li>Value-weighted legs: each name capped at 5% of the leg.</li><li>Sector ≤ benchmark weight + 10 pp.</li><li>The R-07 Korea pair cap (0.35 when the pair exceeds 0.45 of KOSPI) and the semiconductor cap (≤ 0.50) apply to the combined Korea long book, on look-through.</li></ul>*(The 2%, 5%-of-leg and +10 pp levels are judgment.)* | Korean VW winner decile: 85.4% Samsung + SK hynix in Jul 2026. A 5% cap took May 2026 from +77.0% to +17.8%, but Jul 2026 was −30.7% vs −29.6%. Pair share 57.1% in Jun 2026. | **BUILD** |
| **RL-3 Liquidity and universe** | INVARIANT | **KRX:**<ul><li>Common shares only.</li><li>Price ≥ ₩1,000.</li><li>Top 500 by market cap, and 20-day ADV ≥ ₩1bn.</li><li>Exclude:<ul><li>administrative and investment-warning designations;</li><li>halted names;</li><li>listings younger than 60 sessions;</li><li>DART rights-offering and merger event windows.</li></ul></li><li>A simulated position may not exceed 2% of 20-day ADV at the declared book notional.</li></ul>**US:** price ≥ $5, and 20-day ADV ≥ $5m.<br>*(Thresholds are judgment.)* | Liquidity withdrawal drives forced-selling losses (KL; Nagel). The Korean sleeves' tested universe is top 500 / ≥ ₩1,000. | **BUILD** |
| **RL-4 Turnover and costs** | INVARIANT | <ul><li>**Monthly sleeves** (momentum, value, quality) use rank buffers: enter in the top decile, exit only below the top quintile. Target one-way turnover ≤ 30% a month.</li><li>**Reversal sleeves** may trade only where the ex-ante edge is at least 2× the round-trip cost (≥ 140 bp at KRX stock cost).</li><li>**Every card reports** turnover, plus net results at 1× and 2× cost.</li></ul>*(The 30% and 2× levels are judgment.)* | Korean STR turns over 88–89% of names a month per leg; Sharpe 0.32 gross → −0.29 net. WML turnover 30–35% per leg. | **BUILD** |
| **RL-5 Momentum own-vol scaling; D-M gate** | R-03 CARD-O; R-04 INSUFFICIENT DATA (spec book only) | <ul><li>Applies to every momentum-family sleeve (cross-sectional 12-1, residual, industry, time-series) in every market.</li><li>Scaling: σ126 of the sleeve's own daily returns, 12% target, cap 1.0.</li><li>D-M gate: floor 0.5, in the spec book only.</li><li>No own-vol scaling for value, quality or reversal (R-05).</li></ul> | <ul><li>US 1926–2011: Sharpe 0.53 → 0.97 (BSC).</li><li>Macro US: 0.399 → 0.714 gross / 0.672 net.</li><li>KRX VW net: 0.36 → 0.41; the Jun–Jul 2026 window −10.1% vs −22.6% for a same-exposure static book.</li><li>Cederburg: no general out-of-sample gain outside momentum, profitability and BAB.</li><li>KRX D-M gate: about 5 onsets, and it missed Jul 2026.</li></ul> | **BUILD** (R-03); **BACKLOG** (R-04 on KRX) |
| **RL-6 Book volatility target** | R-06 CARD-P | Declare a target volatility for the combined stock-sleeve book. Recommended: **≤ 8% a year**, so that the R-07 levels sit at about 1.0σ, 1.5σ and 1.9σ *(judgment)*. Report the realised book volatility. | Brownian false alarms at SR 0.5: P(≥ −15% within 10 years) = 0.65 at 8% volatility, 0.97 at 12%. KOSPI VT8 plus ladder: Sharpe 0.23 → 0.29, max drawdown −32.6% → −27.7%. | **BUILD** |
| **RL-7 Drawdown ladder (R-07, corrected)** | INVARIANT | **(a) Scope:** the total simulated book NAV, after RL-6. Never per sleeve.<br>**(b) Thresholds:** −1.0σ / −1.5σ / −1.9σ of the declared book target (= −8% / −12% / −15% at σ = 8%).<br>**(c) Steps, non-cumulative:**<ul><li>at −1.0σ: gross × 0.5;</li><li>at −1.5σ: × 0.5, with no new entries;</li><li>at −1.9σ: HALT (0×), operator review, re-arm refused for 10 sessions.</li></ul>**(d) Re-arm:**<ul><li>re-enter at 0.5, with the reference peak reset to the NAV at re-arm;</li><li>return to 1.0 after a +0.5σ gain from the re-arm NAV, or after 60 sessions without a new −1.0σ breach *(judgment)*;</li><li>never measure from the all-time high-water mark after a HALT.</li></ul> | <ul><li>A high-water-mark reference re-halts 20–22 times a year.</li><li>Re-arm at 0.5 with reset, on KOSPI: max drawdown −55.7% → −41.3%; Jul 2026 −38.6% → −21.3%; but H1 2026 +101.1% → +49.0%.</li><li>On KOSPI VT20, σ-scaled: 1 halt in 26 years, max drawdown −47.5% → −37.4%.</li><li>Per sleeve: KRX vol-scaled WML Sharpe 0.41 → 0.14.</li><li>Cumulative steps cost the SPY 2009 rebound: +2.1% vs +35.0%.</li></ul> | **BUILD** (resolves backlog open point 1) |
| **RL-8 No name-level stops; statistical review triggers** | CONVENTION | <ul><li>No price stop-loss on individual names in reversal, value, quality or Korean momentum sleeves.</li><li>An HZZ-type stock-level stop on US momentum becomes a backlog CARD-O, tested against the R-03 sleeve at 50 bp with next-open fills.</li><li>**Review trigger** for each forward-simulated card. A card goes to REVIEW when either:<ul><li>its forward drawdown exceeds the 95th percentile of drawdowns simulated from its haircut OOS Sharpe and realised volatility over the elapsed horizon; or</li><li>its forward 12-month Sharpe falls below the card's 90% CI lower bound.</li></ul></li><li>REVIEW means re-gate and report; it never means automatic liquidation.</li></ul> | <ul><li>Kaminski–Lo condition: Korean weekly name AR(1) median −0.024, 63% negative.</li><li>KRX 15% stop: Sharpe 0.43 → 0.26 gross, 0.20 → −0.17 net.</li><li>Rej–Seager–Bouchaud: normal drawdowns are deeper and longer than intuition.</li><li>Value's 2007–20 drawdown (−39%) preceded a strong recovery.</li></ul> | **BUILD** (convention); HZZ-US **BACKLOG** |
| **RL-9 Crowding and concentration display** | CONTEXT | Shown daily:<ul><li>Korea pair share of market cap;</li><li>top-two share of each VW leg;</li><li>comomentum (Korea, US);</li><li>sleeve σ21 / σ126;</li><li>MTUM vs SPY relative drawdown;</li><li>Korean margin debt and leveraged-ETF AUM, when available (BL-U01);</li><li>13F crowding, labelled as up to 135 days stale.</li></ul>No action until BL-C14 passes. | Lou–Polk vs Barroso–Edelen–Karehnke (contested); 13F lag; the macro BL-C14 timing evidence. | **CONTEXT** |
| **RL-10 Factor-episode stress table** | Reporting INVARIANT | Every stock-level card reports daily returns in fixed windows:<ul><li>**2007–2016:** 2007-08-06 → 08-10; 2009-03-09 → 05-29; 2016-02-01 → 04-29; 2016-11-08 → 11-30.</li><li>**2020–2023:** 2020-11-06 → 11-13; 2021-01-22 → 02-05; 2023-01-03 → 01-31.</li><li>**2024–2025:** 2024-07-10 → 08-06; 2025-01-24 → 01-28; 2025-03-06 → 03-11; 2025-04-02 → 04-09; 2025-10-06 → 10-31.</li><li>**2026:** 2026-02-03 → 02-05; 2026-06-22 → 07-30.</li><li>**Korea:** Oct 2019, Apr 2020, Oct 2025, May 2026, Jul 2026.</li></ul>These come on top of the macro §8.6 table. Each card also reports leave-one-episode-out results, and no single episode may supply more than 50% of the benefit. | §1 episode table | **BUILD** |
| **RL-11 Short-leg filters** | INVARIANT for any simulated short | Exclude names where any of these holds:<ul><li>short interest > 20% of float;</li><li>days-to-cover > 10;</li><li>5-day turnover / float in the top 1%.</li></ul>Each short name is capped at 1% of sleeve gross. Korean short legs are research-only until the access regime is verified.<br>*(Levels are judgment.)* | GME short interest 122.97% of float; Jan 2026 losses on short high-beta exposure; losses concentrated in a few short books (SEC; Fed). | **BUILD** |

### Inferences: refinements and conflicts flagged against the macro spec (not re-litigated)
- **F1: R-07's levels are fixed percentages.** They are appropriate only if the book runs at about 8% volatility. Either declare RL-6 at ≤ 8%, or restate the levels in σ units. At a 12% target, the −15% HALT fires by chance with 97% probability within ten years, even for a strategy with a true Sharpe of 0.5.
- **F2: R-07's re-arm rule is under-specified.** It says re-arm is refused for 10 sessions, but not which reference peak applies after the HALT. With the all-time high-water mark, the book loops into HALT (20–22 halts a year in my tests, 2000–26). Reset the reference and re-enter at 0.5.
- **F3: backlog open point 1 (are the steps cumulative?).** Recommend non-cumulative steps, with −12% meaning × 0.5 plus an entry block. The cumulative 0.25 variant lost most of the 2009 rebound on SPY (+2.1% vs +35.0%). It improved KOSPI only modestly (Sharpe 0.39 vs 0.34; max drawdown −49.3% vs −53.6%).
- **F4: the ladder must not be cascaded into sleeves.** Every per-sleeve KRX test lost Sharpe: WML EW 0.20 → 0.03; WML VW 0.36 → 0.26, with a worse maximum drawdown; vol-scaled WML VW 0.41 → 0.09.
- **F5: backlog open point 3 (caps on ETF look-through).** In stock books the binding constraint should be the sleeve-level name caps of RL-2. The 0.35 pair cap matters for long-only and ETF-line books; apply it on look-through.
- **F6: the prior design's Korean momentum weight.** This supports the macro decision "12-1 → 0".
  - The Korean VW 12-1 net Sharpe of 0.32 over 2016–26 is a concentration artefact: with a 5% name cap it is −0.00.
  - The EW version is −0.13 net over 2016–26.
  - The residual and 12-7 variants remain untested (DC-03).
- **F7: R-08 (VIX ≥ VIX3M).** It gives no protection against factor crashes. VIX closed between 12.9 and 25.8 at five crash onsets, and the R-08 flag was on for zero days during the Jul 2026 KOSPI crash (macro). No change is proposed; it simply should not be counted as factor-crash protection.
- **F8: the prior design's claim of "+0.1 to +0.3 Sharpe from vol scaling on nearly every strategy".** E5 concurs with the macro correction. On Korean momentum the net gain is +0.05 (VW) to +0.11 (EW). On reversal it is negative.

### Gaps
- **Several RL levels are judgment** and must be pre-registered before any card runs: the 2% name cap, 5%-of-leg cap, sector +10 pp / ±5 pp, ADV thresholds, rank buffers, the 2× edge rule, the 0.5σ / 60-session re-arm and the short-leg filters.
- **The pod-limit calibrations come from press reports (T2),** not from fund documents.
- **The Korean short-selling access regime (ban and resumption dates) and the retail short-sale rules** were not verified in this session.
- **RL-7 is an INVARIANT,** so its effect must be reported on every card's book. Its σ-scaled version has been tested only in-sample, on KOSPI, SPY and one KRX sleeve.

## 6. Data-check requests for the data lab

All tests use the lab's KRX all-stock daily data (marcap, survivorship-free), unless stated otherwise.

**Common construction**
- **Timing:** decide at the close of t; earn from t+1.
- **Costs:** 35 bp per side, re-run at 70 bp.
- **Statistics:** Sharpe ratios with Lo SEs and a 10-session block bootstrap (2,000 draws).
- **Labelling:** label everything IS and gross or net.

**DC-01: Korean factor-crash anatomy (replication of §1 and §4).**
- **Construction.**
  - Universe: KOSPI + KOSDAQ common shares (code ending in 0), top 500 by prior month-end market cap, price ≥ ₩1,000.
  - Signal: 12-1 momentum, skipping the most recent month.
  - Portfolio: D10–D1, EW and VW, daily buy-and-hold within each month. Period 2000-01 → 2026-09.
- **Report:**
  - the 10 worst months;
  - Mar–May 2009, Oct 2019, Apr 2020, Oct 2025, May 2026 and Jul 2026;
  - maximum drawdown;
  - Sharpe for the full period and for 2016–26.
- **Expected:**
  - Jul 2026: −24.8% (EW) and −29.6% (VW).
  - Sharpe, gross / net: 0.43 / 0.20 (EW) and 0.52 / 0.36 (VW).
  - Also report the sleeve with each name capped at 5% of its leg. Expected: Jul 2026 −30.7%; May 2026 +17.8%.

**DC-02: name-level stop-losses on KRX, and the Kaminski–Lo condition.**
- **Rule variants.**
  - Stop levels: 10% and 15%, measured from the formation close.
  - Triggers: (a) a close-based trigger with exit at the next close; (b) an intraday-low trigger with exit at the next open. Variant (b) bounds the execution assumption.
  - Each stopped name sits in cash until the next rebalance; about 70 bp is charged per stopped round trip.
- **Apply to:** WML and STR, EW and VW.
- **Also report:** for every sleeve, the rolling 10-year monthly AR(1) against its monthly Sharpe.
- **Prediction:**
  - stops lower Sharpe wherever AR(1) < SR;
  - expected WML EW Sharpe 0.43 → 0.26 gross.

**DC-03: crash profile of neutral momentum constructions.**
- **Variants:** (i) residual momentum, from 252-day regressions on the market plus KRX-sector returns; (ii) 12-7 momentum; (iii) sector-neutral 12-1, ranked within KRX sectors.
- **Report for each, raw and with R-03 scaling (σ126, 12%, cap 1):**
  - Sharpe, overall and for 2016–26;
  - maximum drawdown;
  - Jul 2026, Oct 2019 and Mar–May 2009;
  - beta to KOSPI in up and down months.
- **Decision rule:** a variant may replace "12-1 → 0" only if its net Sharpe 90% CI over 2016–26 excludes 0, at 35 bp.

**DC-04: drawdown-ladder calibration (R-07 / RL-7).**
- **Books:**
  - KOSPI buy-and-hold;
  - KOSPI with R-06 (SMA20, 20%, cap 1);
  - KOSPI and US vol-targeted at 8%;
  - the combined stock-sleeve book, once it exists.
- **Grid** (pre-register it, and count every cell as a trial):
  - steps: cumulative vs non-cumulative;
  - re-arm: {reset at 1.0, reset at 0.5 with probation, high-water mark};
  - thresholds: fixed % vs σ-scaled (−1.0 / −1.5 / −1.9 × target or trailing 252-day volatility);
  - probation: +0.5σ vs a 60-session time-out.
- **Report:**
  - ΔSharpe and ΔMDD against a static book with the same average exposure;
  - halts per year, and the share of days below full exposure;
  - the Jul 2026 window, H1 2026, the 2009 rebound and the 2020 rebound.
- **Expected (re-arm at 0.5 with reset, on KOSPI):** Sharpe 0.42 → 0.40; max drawdown −55.7% → −41.3%; 0.67 halts a year.

**DC-05: false-alarm table for the declared book.**
- **Method:**
  - simulate 20,000 paths at the book's declared target volatility, at true Sharpe ratios of 0.3, 0.5 and 1.0;
  - also block-bootstrap the book's own OOS daily returns (20-session blocks).
- **Report:** P(max drawdown ≥ −1.0σ / −1.5σ / −1.9σ) over 1, 3 and 10 years.
- **Expected** (8% volatility, SR 0.5, at −8% / −12% / −15%): 0.38 / 0.10 / 0.03 within 1 year; 1.00 / 0.88 / 0.65 within 10 years.

**DC-06: Korean comomentum and concentration as crowding predictors** (this is the BL-C14 settling test).
- **Measures, computed monthly from 2001:**
  - CoMOM: the average pairwise correlation of weekly residual returns (market + KRX sector) among the D10 and D1 members over the 52-week formation window;
  - the top-two share of the VW winner decile;
  - the Samsung + SK hynix share of market cap.
- **Test** whether the top quintile of each measure predicts:
  1. next-12-month WML return;
  2. the frequency of WML weeks below −5%;
  3. WML σ21 over the next 1–3 months, *beyond* σ126.
- **Pass rule:**
  - it must lead own-factor volatility by ≥ 5 sessions in ≥ 3 of 5 episodes (Oct 2019, Apr 2020, Oct 2025, May 2026, Jul 2026);
  - and it must add Sharpe to vol-scaled sizing out of sample.

**DC-07: state at the onset of factor crashes.**
- **Episodes** (§1): 2007-08-06, 2009-03-09, 2020-11-09, 2024-07-11, 2025-01-27, 2025-03-07, 2025-10-06, 2026-06-23.
- **Report for each onset:**
  - the VIX percentile, versus the unconditional distribution;
  - the sleeve's σ21/σ126 and its R-03 weight;
  - the D-M gate state;
  - the R-08 flag.
- **Expected:**
  - VIX closes were 22.94, 49.68 (9 Mar 2009), 25.75, 12.92, 17.90, — , — , 19.49;
  - the lab should fill in the missing dates.

**DC-08: the Korean analogue of the US quant quakes.**
- **Daily returns of KRX** WML, STR and (where a book-to-price proxy can be built) value L/S, plus KOSPI.
- **Windows:** 2007-08-01 → 08-17 and 2024-07-31 → 08-09.
- **Question:** did the US de-leveraging transmit to Korean factor returns, or only to the index? The KOSPI cap-weighted index fell 12.1% over 2–5 Aug 2024.

**DC-09: US stop-loss replication (HZZ).** This requires daily US stock data that the lab does not hold; the French factors and SPY are not enough. If such data are added:
- replicate the 10% and 15% stops on US momentum, 1990–2026;
- use next-open fills, at 50 / 100 bp per side;
- compare against R-03-scaled momentum.

If the data are not added, the card stays in BACKLOG.

**DC-10: same-exposure comparison for vol scaling, with confidence intervals.**
- **Books:** Korean WML (EW and VW) under R-03, against a static book at the same average weight (0.58 for EW, 0.40 for VW).
- **Report:**
  - ΔSharpe with a block-bootstrap CI;
  - ΔMDD;
  - the Jul 2026 window. Expected: −13.1% vs −24.8% (EW) and −10.1% vs −22.6% (VW).
  - Run at 35 bp and at 70 bp.

**DC-11: how often the caps bind.**
- **Series:** monthly, 2000–2026:
  - the Samsung + SK hynix share of KOSPI common-share market cap (expected: 23.1% in Jun 2025, 57.1% in Jun 2026);
  - how often RL-2 and the R-07 pair and semiconductor caps bind in each sleeve.
- **Question:** what return and turnover cost do the caps carry outside 2025–26?

**DC-12: French momentum vintage and compounding check.**
- **Discrepancy.** Monthly French Mom (vintage to Mar 2017) shows −34.58% for Apr 2009. The macro programme's daily-compounded series shows −26.8%.
- **Check:**
  - confirm against the current French files;
  - fix which construction the RL-10 stress table uses. Recommend the monthly long/short return for monthly sleeves and daily compounding for daily-rebalanced books.

## 7. Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| E5-C01 | Quant equity crashes can be invisible at monthly and index frequency. | **Aug 2007, KL contrarian book, unlevered:** −1.16% / −2.83% / −2.86% on 7–9 Aug, +5.92% on 10 Aug. At 8:1 leverage: about −25%, then +23.67%. **Local:** SPY −0.71% over 7–9 Aug. French monthly Aug 2007: Mom +0.09%, HML −2.25%. US 2007; simulated book, IS. | [KL 2007](https://web.mit.edu/Alo/www/Papers/august07.pdf); [NBER w14465](https://www.nber.org/papers/w14465); local | T1 | A simulated book, not fund P&L, but consistent with reported fund losses (GS GEO −30%+ in a week). Published in JFM 2011. | — | **BUILD**: daily sleeve P&L and daily stress windows (RL-10). Never rely on monthly factor data for risk. |
| E5-C02 | Leverage creep as alpha decays is the precondition for unwinds. | Leverage needed to match 1998 returns: 2:1 in 1998 (0.57%/day) vs about 9:1 in 2007 (0.13%/day). US. | [KL 2007](https://web.mit.edu/Alo/www/Papers/august07.pdf) | T1 | Single strategy, IS. | — | **CONTEXT**: the cap of 1.0 (R-01) is the structural defence. Never lever a decaying signal. |
| E5-C03 | Momentum crashes in rebounds after bear markets, because the loser leg turns high-beta (a short-call payoff). | **US:** losers +163% vs winners +8% over Mar–May 2009; WML −42.3% (Mar 2009) and −45.5% (Apr 2009); up/down beta −1.51 / −0.70 (t 4.5). **Korea:** WML −10.8% (Mar) and −15.6% (Apr 2009, EW) while KOSPI rose 13.5% each month (local, gross). | [D-M](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf); local | T1 | Replicated in the UK, Europe, Japan and other asset classes (D-M). | Bull-market crashes: Nov 2020, Jul 2026, Korea Oct 2019. | **CONTEXT** for R-04, which stays INSUFFICIENT DATA. |
| E5-C04 | Own-volatility scaling is the most robust protection for momentum. | **US 1926–2011 (BSC, IS, gross):** Sharpe 0.53 → 0.97; worst month −79.0% → −28.4%; max drawdown −96.7% → −45.2%. **Macro US 1990–2026:** 0.399 → 0.714 gross; 0.672 net of 50 bp. **KRX 2000–26, net of 35 bp:** VW 0.36 → 0.41, EW 0.20 → 0.31. Jul 2026 window −10.1% vs −22.6% for a same-exposure static book (local). | [BSC](https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002566); [MM](https://www.nber.org/system/files/working_papers/w22208/w22208.pdf); macro; local | T1 | Replicated (MM; Cederburg's exception list; international). Turnover unchanged (74% → 75%). | Crashes from a low-volatility onset: US 2016 (−16.7% vs −17.5%); Korea Oct 2019 (scaled sleeve still −13.1% / −14.3%). | **BUILD**: R-03 on every momentum-family sleeve in every market (RL-5). |
| E5-C05 | Volatility management is not a general improvement outside momentum-like factors. | **103 US strategies:** OOS direct comparisons 53 wins vs 50 losses; real-time combinations lower the CER in 72 of 103; spanning alphas positive in 77 (IS). **Macro, constant-vol since 2020:** ST_Rev −0.31, HML −0.08, CMA −0.16. | [Cederburg et al.](https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X); macro | T1 | OOS, many strategies. | — | **BUILD** (constraint): value, quality and reversal stay at 1.0× (R-05 confirmed). |
| E5-C06 | Stock-level stop-losses truncate US momentum's worst months and doubled its Sharpe in-sample. | **US 1926–2013, 10% stop:** worst month EW −49.79% → −11.36%; VW −64.97% → −23.28%. **15% stop, EW:** monthly Sharpe 0.165 → 0.399. Break-even cost 3.18–5.71%. IS, gross. | [HZZ, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2407199) | T1 (WP) | IS only; fills assumed at stop levels; not replicated at QUANTGEN's costs. | Korea (E5-C07). | **BACKLOG**: a US CARD-O against the R-03 sleeve at 50 bp with next-open fills (DC-09). |
| E5-C07 | On KRX, name-level stops shrink momentum's worst month but roughly halve its Sharpe. | **2000–26, 15% stop, close trigger, exit at t+1:** WML EW Sharpe 0.43 → 0.26 gross, 0.20 → −0.17 net of 35 bp. WML VW 0.52 → 0.36 gross, 0.36 → 0.06 net. EW worst month −24.8% → −15.4%; max drawdown unchanged (−70.6% → −70.4%). | local (KRX marcap) | T3 | IS; one construction. | — | **DROP** name-level stops for Korean sleeves (RL-8). |
| E5-C08 | Stop-losses add value only when the autocorrelation is at least the Sharpe ratio; under mean reversion they hurt. | **Theory, plus US 1993–2011 equities and Treasuries:** monthly-interval stops added +1.5% of return and cut volatility by 5% (Sharpe up to +20%); short-horizon stops had negative premia. **Local:** Korean stocks' weekly AR(1) median −0.024, 63% negative; Korean WML EW AR(1) −0.009 vs SR 0.117. | [Kaminski–Lo](https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf); local | T1 | The theoretical result is general; the empirics are IS. | Trend books and Korean VW momentum meet the condition, but only marginally. | **BUILD** (convention): any stop must be justified by the sleeve's measured AR(1) vs its SR (DC-02). |
| E5-C09 | Value's 2007–2020 drawdown was a revaluation, and a mechanical stop would have exited before the recovery. | **Value drawdown:** FF value −39.1% over 12+ years (about 1-in-20); value spread at the 97th percentile (AHKL) or 100th (AQR). Local HML −32.1% from Jan 2007 to Sep 2018. **After 2020:** IWD −7.7% vs IWF −29.3% (2022); VLUE +32.7% (2025). | [AHKL](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3488748); [AQR](https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead); [iShares IWD](https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf); local | T1/T2 | The post-2020 recovery is out of sample. | Value lagged again in 2023–24 (IWD +11.3% vs IWF +42.5% in 2023). | **BUILD**: statistical review triggers, not mechanical liquidation (RL-8). |
| E5-C10 | The 9 Nov 2020 momentum crash was preceded by visible crowding, but not by market stress. | **The crash:** momentum about −5% in a day (MSCI); the largest intraday drop since 2000 (Bloomberg). **Before it:** short interest in momentum more than 3 SD above its mean in early October; MSCI's crowding model elevated on 6 Nov. **Market that day (local):** VIX 25.75; SPY +1.26%. **French Mom, Nov 2020:** −12.0% static → −3.9% with the stack (macro). | [MSCI](https://www.msci.com/research-and-insights/blog-post/are-momentum-wings-finally-starting-to-melt); [Bloomberg](https://www.bloomberg.com/news/articles/2020-11-09/momentum-trade-plunges-the-most-on-record-in-rotation-frenzy); macro; local | T2 | One episode; a vendor model with no published hit rate. | — | **CONTEXT** (crowding display, RL-9). R-03 already cut the loss. |
| E5-C11 | Squeeze losses concentrate in crowded short books: the risk sits at the name level, not the factor level. | **GME:** short interest 122.97% of float; about +2,700% intraday (8–28 Jan 2021). **Mechanics:** buy-to-cover a small share of volume; no gamma squeeze. **Spillover:** the effect on the hedge-fund sector was limited. | [SEC 2021](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf); [Fed FSR May 2021](https://www.federalreserve.gov/publications/files/financial-stability-report-20210506.pdf) | T1 | Official, ex post. | Losses on short high-beta exposure in Jan 2026 (Hedgeweek). | **BUILD**: RL-11 short-leg filters. |
| E5-C12 | Other funds' risk limits propagate crashes: the Aug 2024 deleveraging was driven by internal volatility targets, and the move reversed within days. | **The move:** TOPIX −12% on 5 Aug; S&P 500 −3.0%; VIX above 60 off-hours (local high 65.73); S&P losses recovered by 9 Aug. **Fed:** funds de-risked to meet internal volatility targets, not margin calls; hedge-fund leverage near its highest since 2013. | [BIS 90](https://www.bis.org/publ/bisbull90.pdf); [Fed FSR Nov 2024](https://www.federalreserve.gov/publications/files/financial-stability-report-20241122.pdf); local | T1 | Official. | The pattern repeated in Mar 2025 and Jul 2026 (GS; Hedgeweek). | **CONTEXT**: avoid rules that cut at the worst close and re-add slowly (R-08 whipsaw, +5.0%). |
| E5-C13 | Pod-style hard stops are a manager-selection device for large platforms. | **Rule:** lose 5% and the capital is halved; at 7.5% the manager is likely out. **Millennium:** a $1bn PM who loses $50m drops to $500m; at $75m of total loss is likely fired. **Platform:** 340+ teams; 15–20% annual staff turnover. | [BI via AOL](https://www.aol.com/strategy-69-billion-hedge-fund-193733084.html); [Hedgeweek](https://www.hedgeweek.com/millennium-posts-rare-monthly-loss-amid-index-rebalancing-trades/) | T2 | Practice as reported by the press; not tested. | Synchronized pod stops amplified Mar 2025 (a 4+ SD momentum drawdown, GS). | **CONTEXT**: adapt as review triggers (RL-8), not as liquidation. |
| E5-C14 | Fixed-percentage drawdown thresholds fire on noise unless the book's volatility is low. | **Brownian, SR 0.5:** P(drawdown ≥ 8% within 1 year) is 0.38 at 8% volatility and 0.75 at 12%; P(≥ 15% within 10 years) is 0.65 and 0.97. **RSB:** a 5% chance that a 10-year SR-0.5 drawdown lasts 7+ years; the 5% depth tail is about 1.5/SR in σ units. | [Rej–Seager–Bouchaud](https://arxiv.org/abs/1707.01457); local simulation | T1 + T3 | An analytic benchmark; fat tails make it worse. | — | **BUILD**: σ-scaled ladder thresholds, or book volatility ≤ 8% (RL-6, RL-7; F1). |
| E5-C15 | The ladder's re-arm rule decides whether it protects or destroys: a high-water-mark reference after a HALT causes a halt loop. | **High-water-mark variant:** 20–22 halts a year (2000–26); Sharpe −1.7 to −5.6 (SPY, KOSPI, KOSPI VT8, Korean WML vol-scaled). **Reset and re-arm at 0.5, KOSPI:** Sharpe 0.42 → 0.40; max drawdown −55.7% → −41.3%; Jul 2026 window −38.6% → −21.3%; H1 2026 +101.1% → +49.0%; 0.67 halts a year. 2000–26, 35 bp, IS. | local | T3 | IS; the parameters are judgment. | A bull-market tax (H1 2026). | **BUILD**: RL-7(d); resolves the R-07 ambiguity (F2). |
| E5-C16 | Run per sleeve, a fixed ladder destroys value on high-volatility factor sleeves. | **KRX, net of 35 bp:** WML EW Sharpe 0.20 → 0.03 (45 halts); WML VW 0.36 → 0.26, with max drawdown worse (−78.5% → −83.7%); vol-scaled WML VW 0.41 → 0.14 (fixed thresholds) or 0.27 (σ-scaled); STR EW −0.29 → −0.59. | local | T3 | IS. | — | **DROP** per-sleeve ladders (F4). |
| E5-C17 | On a volatility-targeted book, the ladder is a cheap tail device. | **KOSPI VT20, fixed thresholds:** Sharpe 0.40 → 0.37; max drawdown −47.5% → −34.7%; 0.49 halts a year. **σ-scaled:** Sharpe 0.40; max drawdown −37.4%; one halt in 26 years. **KOSPI VT8:** Sharpe 0.23 → 0.29; max drawdown −32.6% → −27.7%. 2000–26, 35 bp, IS. | local | T3 | IS; Korean history only. | SPY VT8 with a +4% probation sat below full exposure on 96% of days (a probation-design flaw). | **BUILD**: ladder at book level only, after RL-6. |
| E5-C18 | Korean momentum's July 2026 crash was its worst month since 2000; it came in a bull-market crash, with the D-M gate off. | **The crash (gross):** WML −24.8% (EW) / −29.6% (VW) in Jul 2026. **The market:** KOSPI −22.2% in July and −38.6% from 23 Jun to 30 Jul. **Why the gate was off:** KOSPI's 24-month return was +235% on 22 Jun. | local; macro | T3 | IS; one episode. | — | **BUILD**: rely on R-03 (weights 0.35 / 0.20 on 22 Jun → July −7.5% / −5.2%), not on R-04. |
| E5-C19 | Value-weighting turned Korean momentum into a two-stock bet in 2026; name caps fix the concentration but not the crash. | **The concentration:** SK hynix was 68.7% (May) and 72.8% (Jun) of the VW winner decile; Samsung + SK hynix 85.4% (Jul 2026). **With a 5% cap:** May +77.0% → +17.8%; Jul −29.6% → −30.7%; VW net Sharpe 2016–26 0.32 → −0.00. | local | T3 | IS. | — | **BUILD**: RL-2 caps. Supports a Korean 12-1 weight of 0 (F6). |
| E5-C20 | Market stress gauges were quiet at the onset of most factor crashes. | **VIX closes at onset:** 22.94 (6 Aug 2007), 25.75 (9 Nov 2020), 12.92 (11 Jul 2024), 17.90 (27 Jan 2025), 19.49 (23 Jun 2026). **Macro:** the VIX ≥ VIX3M flag was on for 0 days in the Jul 2026 KOSPI crash. | local (CBOE VIX); macro | T1 data / T3 analysis | Descriptive; 5 onsets. | 2009-03 (VIX 49.7) and Apr 2025 (45–52) were high-VIX episodes. | **BUILD**: use the factor's own risk state (σ21/σ126, R-03) against factor crashes. Do not count R-08 as factor protection (F7). |
| E5-C21 | Comomentum predicts lower post-formation momentum returns and more frequent crash days, over months to years. | **US 1965–2015:** year-2 return −1.08% a month (t −2.75). Over months 1–12, 9.3% vs 1.5% of weeks fell below −5%. Driven by institutional ownership and hedge-fund AUM. The pre-1965 placebo is null. | [Lou–Polk](https://personal.lse.ac.uk/polk/research/Comomentum.pdf) | T1 | Published in RFS; US only; long horizons. | Barroso–Edelen–Karehnke (E5-C22). | **BACKLOG**: Korean comomentum (DC-06); **CONTEXT** display. |
| E5-C22 | Holdings-based crowding proxies do not predict higher crash risk; if anything the relation is negative. | A model plus US evidence: crowding proxies built from institutional holdings are generally negatively related to expected crash risk. | [Barroso–Edelen–Karehnke, JFQA 2022](https://econpapers.repec.org/article/cupjfinqa/v_3a57_3ay_3a2022_3ai_3a4_3ap_3a1313-1342_5f3.htm) | T1 | Published. | Partly contradicts E5-C21. | **DROP** holdings-based crowding as an acting input. |
| E5-C23 | 13F holdings arrive too late, and show too little, to time crashes. | Filed within 45 days after quarter end, by managers with ≥ $100m; short positions are not reported. | [SEC 13F FAQ](https://www.sec.gov/divisions/investment/13ffaq.htm) | T1 | Regulatory fact. | Swaps are invisible (Archegos). | **CONTEXT** only, labelled stale. |
| E5-C24 | The growth of arbitrage capital has lowered value and momentum returns over time. | Arbitrage capital, measured from short interest, grew from the late 1980s and returns fell. That capital is most limited when the strategies perform best (US). | [Hanson–Sunderam](https://econpapers.repec.org/article/ouprfinst/v_3a27_3ay_3a2014_3ai_3a4_3ap_3a1238-1286..htm) | T1 | Published in RFS. | — | **CONTEXT**: keep the factor decay haircuts (macro: value −49%, momentum −23%). |
| E5-C25 | Residual (factor-neutral) momentum roughly doubles risk-adjusted profits and cuts time-varying factor exposure. | US: about 2× the risk-adjusted profit; more consistent over time; less concentrated in the extremes. | [Blitz–Huij–Martens](https://econpapers.repec.org/article/eeeempfin/v_3a18_3ay_3a2011_3ai_3a3_3ap_3a506-521.htm) | T1 | Published in JEF; not tested on KRX here. | — | **BUILD-candidate** for Korean momentum (DC-03; RL-1). |
| E5-C26 | Factor ETFs are concentrated sector bets and a channel for crowding. | **IT weight on 29 Sep 2026:** MTUM 54.3%, VLUE 43.1%, QUAL 38.7%, USMV 33.3%. **ETF ownership** raises volatility and negative autocorrelation, with a premium of up to 56 bp a month. | [iShares MTUM](https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf); [BFM, JF 2018](https://econpapers.repec.org/article/blajfinan/v_3a73_3ay_3a2018_3ai_3a6_3ap_3a2471-2535.htm) | T1/T2 | Published paper plus a factsheet. | — | **BUILD**: sector caps and neutrality (RL-1, RL-2); **CONTEXT** for ETF-based proxies. |
| E5-C27 | 2025–26 produced an unusually dense cluster of momentum and crowding unwinds. | **2025:** a 4+ SD momentum drawdown on 7–10 Mar (GS). In October, MS's momentum basket fell 11.3% in 5 days. **2026:** quant losses on crowded trades in January. On 4 Feb, multi-strategy equity books fell 1.9%, their worst day since 9 Apr 2025. In July, GS High Beta Momentum had its worst month since Nov 2000. MTUM −18.0% vs SPY −2.0% (22 Jun–29 Jul 2026, local). | [GS 2025](https://marquee.gs.com/welcome/news/views-from-the-trading-floor/2025-in-review); [Hedgeweek, Oct 2025](https://www.hedgeweek.com/market-reversals-hit-quant-hedge-funds/); [Hedgeweek, Jan 2026](https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind); [Investing.com/Reuters](https://www.investing.com/news/economy-news/hedge-funds-hit-by-ai-selloff-goldman-sachs-says-4487631); [Yahoo](https://finance.yahoo.com/markets/stocks/articles/july-ends-hopeful-note-stocks-222100309.html); Stocklake | T2/T3 | Press reports plus vendor prices; subject to attention bias. | — | **CONTEXT**: set the stress budget; add the RL-10 windows. |
| E5-C28 | Short-term reversal in Korean large caps is dominated by costs at monthly rebalancing. | **Top 500, 1-month D1–D10, 2000–26:** EW Sharpe 0.32 gross → −0.29 net of 35 bp; monthly name turnover 88–89% per leg; VW 0.17 → −0.27. | local | T3 | IS; monthly frequency only (weekly and volume-filtered versions untested here). | VW legs were hit by mega-cap concentration (−32.0% in Oct 2025, −35.3% in May 2026). | **BUILD**: RL-4 turnover and edge rule. Cross-reference to the reversal researchers. |
| E5-C29 | The Korean D-M bear-state gate has the right sign but too few onsets. | **2000–26:** on 3.9% of days (about 5 onsets). WML VW earned −47.7% a year when on vs +21.2% when off. Sharpe 0.52 → 0.55 gross at a 0.5 floor. The gate was off in Oct 2019 and Jul 2026. | local | T3 | IS; few onsets. | It missed the two worst months. | **BACKLOG**: R-04 remains INSUFFICIENT DATA on KRX. |

## 8. Source list

**Academic and working papers (T1)**
- Khandani, A. & Lo, A. (2007). What Happened to the Quants in August 2007? https://web.mit.edu/Alo/www/Papers/august07.pdf
- Khandani, A. & Lo, A. (2008/2011). NBER WP 14465; *Journal of Financial Markets* 14(1). https://www.nber.org/papers/w14465
- Daniel, K. & Moskowitz, T. (2016). Momentum Crashes, *JFE*; NBER WP 20439. https://www.nber.org/papers/w20439 ; https://www.nber.org/system/files/working_papers/w20439/w20439.pdf
- Barroso, P. & Santa-Clara, P. (2015). Momentum has its moments, *JFE* 116(1).
  - https://www.sciencedirect.com/science/article/abs/pii/S0304405X14002566
  - PDF copy used for the numbers: http://www.snifferquant.com/gyantal/Incode/papers/Momentum%20Has%20Its%20Moments(scaling%20Momentum%20by%20vol),2014.pdf
- Han, Y., Zhou, G. & Zhu, Y. (2016). Taming Momentum Crashes: A Simple Stop-Loss Strategy. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2407199 ; working-paper PDF https://smallake.kr/wp-content/uploads/2017/03/SSRN-id2407199.pdf
- Kaminski, K. & Lo, A. (2014). When do stop-loss rules stop losses? *JFM* 18. https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf ; https://www.sciencedirect.com/science/article/abs/pii/S138641811300030X
- Moreira, A. & Muir, T. (2017). Volatility-Managed Portfolios, *JF*; NBER WP 22208. https://www.nber.org/system/files/working_papers/w22208/w22208.pdf
- Cederburg, S., O'Doherty, M., Wang, F. & Yan, X. (2020). On the performance of volatility-managed portfolios, *JFE* 138(1). https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X
  - Secondary summary, T3: https://alphaarchitect.com/the-performance-of-volatility-managed-portfolios/
- Lou, D. & Polk, C. (2022). Comomentum: Inferring Arbitrage Activity from Return Correlations, *RFS* 35(7). https://personal.lse.ac.uk/polk/research/Comomentum.pdf ; https://econpapers.repec.org/article/ouprfinst/v_3a35_3ay_3a2022_3ai_3a7_3ap_3a3272-3302..htm
- Barroso, P., Edelen, R. & Karehnke, P. (2022). Crowding and Tail Risk in Momentum Returns, *JFQA* 57(4). https://econpapers.repec.org/article/cupjfinqa/v_3a57_3ay_3a2022_3ai_3a4_3ap_3a1313-1342_5f3.htm
- Hanson, S. & Sunderam, A. (2014). The Growth and Limits of Arbitrage: Evidence from Short Interest, *RFS* 27(4). https://econpapers.repec.org/article/ouprfinst/v_3a27_3ay_3a2014_3ai_3a4_3ap_3a1238-1286..htm
- Chincarini, L., Lazo-Paz, R. & Moneta, F. (2026). Crowded spaces and anomalies, *JBF* 182. https://ideas.repec.org/a/eee/jbfina/v182y2026ics0378426625001992.html
- Blitz, D., Huij, J. & Martens, M. (2011). Residual momentum, *JEF* 18(3). https://econpapers.repec.org/article/eeeempfin/v_3a18_3ay_3a2011_3ai_3a3_3ap_3a506-521.htm
- Ben-David, I., Franzoni, F. & Moussawi, R. (2018). Do ETFs Increase Volatility? *JF* 73(6). https://econpapers.repec.org/article/blajfinan/v_3a73_3ay_3a2018_3ai_3a6_3ap_3a2471-2535.htm
- Ehsani, S. & Linnainmaa, J. (2019). Factor Momentum and the Momentum Factor, NBER WP 25551. https://www.nber.org/papers/w25551
- Nagel, S. (2011/2012). Evaporating Liquidity, NBER WP 17653. https://www.nber.org/papers/w17653
- Rej, A., Seager, P. & Bouchaud, J.-P. (2017). You are in a drawdown. When should you start worrying? https://arxiv.org/abs/1707.01457
- Arnott, R., Harvey, C., Kalesnik, V. & Linnainmaa, J. (2020). Reports of Value's Death May Be Greatly Exaggerated. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3488748
- Frazzini, A., Israel, R. & Moskowitz, T. (2018). Trading Costs, SSRN 3229719. Only the abstract was read. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3229719

**Official and regulatory (T1)**
- SEC staff, Staff Report on Equity and Options Market Structure Conditions in Early 2021 (Oct 2021). https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf
- SEC, Form 13F FAQ. https://www.sec.gov/divisions/investment/13ffaq.htm
- Federal Reserve, Financial Stability Reports:
  - May 2021: https://www.federalreserve.gov/publications/files/financial-stability-report-20210506.pdf
  - Nov 2024: https://www.federalreserve.gov/publications/files/financial-stability-report-20241122.pdf
  - Apr 2025: https://www.federalreserve.gov/publications/files/financial-stability-report-20250425.pdf
- BIS Bulletin No. 90 (Aug 2024), on the August 2024 market turbulence. https://www.bis.org/publ/bisbull90.pdf

**Banks, asset managers, index providers (T2)**
- AQR (2020). Is (Systematic) Value Investing Dead? https://www.aqr.com/Insights/Perspectives/Is-Systematic-Value-Investing-Dead
- MSCI (13 Nov 2020). Are Momentum's Wings Finally Starting to Melt? https://www.msci.com/research-and-insights/blog-post/are-momentum-wings-finally-starting-to-melt
- MSCI, equity factor models overview. https://www.msci.com/data-and-analytics/factor-investing/equity-factor-models
- Goldman Sachs Marquee, Views from the Trading Floor: 2025 in Review. https://marquee.gs.com/welcome/news/views-from-the-trading-floor/2025-in-review
- Research Affiliates / Syzygy (Oct 2025). Stop the Losses! Only metadata was accessible. https://www.syzygyassetmanagement.com/insights/publications/articles/1099-stop-the-losses
- iShares calendar-year returns and sector weights (fetched 2 Oct 2026):
  - MTUM: https://www.ishares.com/us/products/251614/ishares-msci-usa-momentum-factor-etf
  - QUAL: https://www.ishares.com/us/products/256101/ishares-msci-usa-quality-factor-etf
  - USMV: https://www.ishares.com/us/products/239695/ishares-msci-usa-minimum-volatility-etf
  - VLUE: https://www.ishares.com/us/products/251616/ishares-msci-usa-value-factor-etf
  - IVV: https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf
  - IWF: https://www.ishares.com/us/products/239706/ishares-russell-1000-growth-etf
  - IWD: https://www.ishares.com/us/products/239708/ishares-russell-1000-value-etf

**Major financial press (T2)**
- Bloomberg:
  - 9 Nov 2020, momentum's record plunge: https://www.bloomberg.com/news/articles/2020-11-09/momentum-trade-plunges-the-most-on-record-in-rotation-frenzy
  - 22 Nov 2020, quants hunting accidental exposure: https://www.bloomberg.com/news/articles/2020-11-22/chaos-in-factor-land-puts-quants-on-hunt-for-accidental-exposure
  - 27 Jan 2025, Nvidia loses $589bn: https://www.bloomberg.com/news/newsletters/2025-01-27/nvidia-loses-589-billion-as-deepseek-batters-stock-evening-briefing-americas
  - 7 Apr 2025, hedge funds' historic one-day selloff: https://www.bloomberg.com/news/articles/2025-04-07/hedge-funds-log-historic-one-day-stock-selloff-in-market-rout
- Business Insider, syndicated by AOL (Oct 2024), on Millennium's risk limits: https://www.aol.com/strategy-69-billion-hedge-fund-193733084.html
- Reuters, via Investing.com (5 Feb 2026), hedge funds hit by the AI selloff: https://www.investing.com/news/economy-news/hedge-funds-hit-by-ai-selloff-goldman-sachs-says-4487631
- Yahoo Finance (31 Jul 2026), momentum's biggest wipeout since 2000: https://finance.yahoo.com/markets/stocks/articles/july-ends-hopeful-note-stocks-222100309.html
- Hedgeweek (trade press, T2/T3):
  - 10 Mar 2025, Millennium: https://www.hedgeweek.com/millennium-posts-rare-monthly-loss-amid-index-rebalancing-trades/
  - 27 Oct 2025: https://www.hedgeweek.com/market-reversals-hit-quant-hedge-funds/
  - 22 Jan 2026: https://hedgeweek.com/news/quant-hedge-funds-see-worst-drawdown-since-october-as-crowded-trades-unwind
  - 7 Jul 2026: https://www.hedgeweek.com/quant-funds-suffer-steepest-momentum-drawdown-since-2023-amid-factor-rotation/

**QUANTGEN project and local data (computations in this session, T3, IS)**
- **Project docs:**
  - `claude/QUANTGEN_MACRO_INTEGRATION.md` (R-03 to R-08, golden values G-MOM-*, G-KR-*, §8.6 episodes);
  - `claude/QUANTGEN_MACRO_BACKLOG.md` (BL-C14; open points 1 and 3; numbers that must not propagate).
- **Raw data:**
  - `/home/claude/data_raw/marcap/data/marcap-1995…2026.parquet` (KRX daily, all stocks);
  - `/home/claude/data_raw/us/vix_daily.csv` (CBOE VIX 1990–2026);
  - `/home/claude/data_raw/us/spy_lean_daily.zip` (SPY 1998–2021);
  - French factors as bundled in Python packages (`linearmodels` French dataset, monthly 1949–2017; `arch` frenchdata, monthly 1926–2018). The Ken French website was blocked from this session.
- **Stocklake MCP:** daily closes for MTUM, SPY, QUAL, USMV and IWM, 21 Apr 2025 → 1 Oct 2026. A vendor feed, price-only.
- **Scripts** (session scratchpad, not saved to the project): `kr_e5c.py`, `e5_rearm.py`, `e5_rearm2.py`, `e5_kr_state.py`, `e5_final.py`, `e5_sameexp.py`, `e5_ac.py`, `e5_ladder_us.py`. Their construction is fully described in §6 for the data lab to re-implement.
