# E2 — Microstructure and execution: which short-horizon technical edges survive realistic costs at retail latency (US and Korea)

As of 2 October 2026. Every number carries market, period, in-sample (IS) or out-of-sample (OOS), and gross or net where the source states it. "Desk view" marks practitioner opinion. Each opinion is tied to a cited source or listed as a data-check request.

---

## 1. Persona

**E2, a fictional composite.** E2 was an NYSE floor specialist and later a designated market maker (DMM). That job meant running manual opens, reopens and closing auctions, and later trading under limit-up/limit-down (LULD) rules. E2 then became Head of Electronic Trading at a Morgan Stanley-style bulge-bracket bank, covering VWAP, TWAP and implementation-shortfall algorithms, the closing-auction desk and transaction-cost analysis. E2 is not a real person and does not speak for NYSE, Morgan Stanley or any other firm.

**Lens: cost first, signal second.** Every short-horizon "edge" is a claim about who sits on the other side of the trade and what you pay them. To count as an edge, it has to survive four things:
- the spread (or the tick)
- the tax
- the market impact
- honest fill rules, meaning no fills on a mere touch and no stop-loss fills at the stop price

---

## 2. Position summary

1. **The documented intraday edges are real but tiny, a few basis points per trade.** This covers market intraday momentum, end-of-day reversal, half-hour periodicity, the overnight drift and opening-range breakouts (ORB). They are earned by liquidity providers and by professionals who pay institutional costs:
   - market intraday momentum on SPY: about 2.6 bp per trade-day gross, 1993-2013
   - overnight drift in E-mini futures: 1.48 bp/day, 1998-2020
   - ORB on QQQ: about 7 cents/share gross, break-even near 2.2 cents/share of slippage
2. **QUANTGEN's pre-registered costs are 25-50 times larger than those edges.** QUANTGEN charges 35 bp per side on KRX stocks and 50 bp per side on US shares via KIS. On KRX alone, the 0.20% sell tax (2026) plus one tick of spread (5-25 bp of price) puts a floor of about 25-45 bp on a round trip before commission and impact. **No intraday technical rule should be a BUILD candidate.** Market intraday momentum, ORB, VWAP-cross, gap-and-go and intraday S/R bounces should be DROPPED, or at most logged as context.
3. **QUANTGEN also cannot test intraday rules honestly.** It is read-only, has no order path and no intraday history beyond what it records itself from KIS quotes. The gate needs 756 in-sample plus 126 out-of-sample sessions of intraday data. That is at least 3.5 years of self-recorded quotes, with queue position and fill uncertainty unknown.
4. **What does survive realistic costs is slow.** Strategies with one-sided monthly turnover below about 50% generally keep significant net returns. One-month reversal at about 91% monthly turnover goes from +0.37%/month gross to −1.28%/month net (US, 1963-2012). Live execution data from one large institutional manager show reversal does not survive costs at reasonable size.
5. **What the desk sees behind support/resistance, gaps and stops is order flow, not geometry.**
   - Support/resistance: take-profit orders and resting liquidity cluster at round numbers. Stop-loss orders cluster just beyond them, so trends stall at levels and accelerate once a level breaks. Bank-published S/R levels beat arbitrary levels by only about 4.6 points of hit rate (60.8% vs 56.2%), with predictive power lasting at least five business days at most firms.
   - Gaps: an opening gap is overnight news plus the imbalance cleared in the opening auction.
   - Stops: a stop is a market order waiting to fire at the worst moment, as on 6 May 2010 and 24 August 2015.
6. **For daily-close decisions, the closing auction is the right execution venue and the right price convention.**
   - US closing auctions were about 9-9.4% of consolidated notional in 2024, about 10.5-14% of NYSE-listed volume (depending on source and measure), and more than 34% of daily notional on Russell reconstitution day.
   - But closing prices carry transient auction pressure (8.1 bp average absolute deviation) that reverses overnight.
   - So any close-to-close reversal signal must also be tested with a one-day skip, and with entry at the close or open of t+1.
7. **QUANTGEN should:**
   - keep its "decide at close t" rule but report both fill conventions: close t, and close t+1 as a conservative bound
   - add a tick-based spread floor and a square-root impact term to every card
   - never fill a simulated stop at the stop price
   - flag KRX price-limit, VI and overheating days as unfillable
   - use only KRX official closing prices, not Nextrade or after-market prints
   - put any reversal card through skip-day, liquidity-filter and buy/hold-band tests before it is even a BACKLOG candidate
8. **Conflict with the prior design (Korea short-term reversal weight 3).** After 70 bp round-trip costs, 1-5 day reversal in Korea is unproven. I would carry it at weight 1-2 until the data lab's net test (DC-E2-02 and DC-E2-03) passes.

---

## 3. Evidence by key question

### 3.1 KQ1: Intraday patterns. Do they exist, do they persist, and do they survive costs?

#### Takeaway
The intraday regularities are statistically real in the original samples. In-sample R² values are 1-2%, and these patterns are worth 1.5-7 bp per day. Two leading mechanisms explain them: hedging and rebalancing flows near the close, and an overnight/intraday clientele split. Some patterns have weakened (US intraday momentum after 2007, APAC during COVID), and the Korean evidence is weak. None of them clears retail costs. Two published ORB results that report high returns either assume no slippage or turn to roughly zero in independent replications.

#### Cited Findings
- **Market intraday momentum, US.** Gao, Han, Li and Zhou (JFE 2018) used SPY from Feb 1993 to Dec 2013. The first half-hour return predicts the last half-hour return.
  - In-sample R² is 1.6% and out-of-sample R² is 1.4%. Adding the 12th half-hour raises these to 2.6% IS and 2.0% OOS.
  - The timing strategy earns 6.67%/yr, Sharpe 1.08, hit rate 54.37%, gross. Buy-and-hold earns 6.04%/yr, Sharpe 0.29.
  - After a bid-ask spread adjustment (post-decimalization), the strategy return falls to 4.46%/yr.
  - Predictability is higher on high-volatility days (R² 3.3% vs 0.6%), high-volume days (3.1%), in recessions (6.6% vs 1.0%) and on FOMC days (11.0%).
  - OOS R² across ten other ETFs ranges from 0.70% to 6.53%.
  - Proposed causes: infrequent rebalancing and late-informed trading. — [Gao-Han-Li-Zhou, author-hosted PDF](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf)
- **16 developed markets, Oct 2005 to Dec 2017.** First-to-last half-hour predictability is significant in-sample in 12 of the 16 markets. Country strategies earn alphas of 2.66-7.45%/yr against always-long. Global portfolio Sharpe ratios range from 1.01 to 1.77. **No transaction-cost analysis.** — [Li, Sakkas, Urquhart, FoFI 2020 conference paper](http://wp.lancs.ac.uk/fofi2020/files/2020/04/FoFI-2020-092-Zeming-Li.pdf)
- **APAC, including Korea.** Limkriangkrai, Chai and Zheng (Pacific-Basin Finance Journal 2023) find strong intraday momentum in China and Japan and none in Hong Kong or Singapore. **South Korea is weak.**
  - Korea data: the KOSEF 200 ETF (102110), Apr 2008 to Apr 2021.
  - First-half-hour coefficient 2.06 (p = 0.084). In-sample R² 1.9%, out-of-sample R² 0.9%.
  - The effect weakened in APAC during COVID (14 Feb to 31 Mar 2020) and disappeared in China.
  - No costs or Sharpe ratios reported. — [Limkriangkrai et al. 2023, Monash repository](https://researchmgt.monash.edu/ws/files/519509174/494419119_oa.pdf)
- **Mechanism: hedging demand.** Baltussen, Da, Lammers and Martens (JFE 2021) studied more than 60 futures on equities, bonds, commodities and currencies, 1974-2020. Option market makers and leveraged-ETF providers who are short gamma must trade in the direction of price moves. This makes the last 30 minutes predictable from earlier returns, followed by reversal over the next days. — [SSRN 3760365](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365)
- **Gamma effect at the stock level.** Park and Zhao (2025 working paper) find that market makers' short-gamma exposure raises stock-level intraday momentum by about 68% on average. Breaches of the gamma-theta break-even range add about 91%. Costs are not quantified. — [NFA portal](https://portal.northernfinanceassociation.org/viewp.php?n=2240183764)
- **Decay.** Zhang and Hua (Risks 2024) studied SPY and QQQ, Aug 2007 to Jul 2018, with a 2022-2024 extension. Classic overnight and intraday-momentum predictors weakened over the window. *Conflict:* Baltussen et al. still find strong effects through 2020 in futures. — [Zhang and Hua, MDPI Risks 12(11):180](https://www.mdpi.com/2227-9091/12/11/180)
- **End-of-day reversal (cross-section).** Baltussen, Da and Soebhag (EFMA 2024 working paper) studied US stocks, 1993-2019. Stocks that fell intraday outperform intraday winners in the last 30 minutes.
  - Value-weighted: 3.45 bp/day (8.7%/yr). Equal-weighted: 4.45 bp/day (11.2%/yr). Gross.
  - Rolling estimates stay negative through the end of the sample.
  - Main driver: short-sellers covering. Secondary: retail contrarian buying.
  - This runs opposite to market-level intraday momentum. — [EFMA 2024 PDF](http://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2024-Lisbon/papers/EndofDayReversal_withnames.pdf)
- **Intraday periodicity.** Heston, Korajczyk and Sadka (JF 2010) studied 1,715 NYSE firms, 2001-2005, in 13 half-hour intervals per day.
  - Winners minus losers in a given half-hour earn 3.01 bp at the same half-hour the next day.
  - The effect stays significant for up to 40 days.
  - **Not a profit opportunity after bid-ask spreads.**
  - The authors attribute it to autocorrelated fund flows and trading algorithms. — [HKS, arXiv/ar5iv 1005.3535](https://ar5iv.arxiv.org/html/1005.3535)
- **Overnight vs intraday split ("tug of war").** Lou, Polk and Skouras (JFE 2019) studied US stocks, 1993-2013, excluding microcaps.
  - Momentum's CAPM alpha is 0.98%/month overnight (t = 3.84) and −0.02%/month intraday.
  - Overnight momentum Sharpe is 0.77 vs 0.31 close-to-close.
  - Size, value, ROE, investment and idiosyncratic-volatility premia are earned intraday (e.g., ROE −0.95% overnight vs +1.42% intraday per month).
  - Short-term reversal, industry momentum, earnings momentum and time-series momentum are earned overnight.
  - The tug of war persists for up to 60 months.
  - Small trades cluster near the open and large trades near the close (TAQ data, 1993-2000).
  - The authors say costs make direct exploitation "much less attractive". — [LSE PDF](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf)
- **Overnight drift in US index futures.** Boyarchenko, Larsen and Whelan (FRBNY Staff Report 917) studied S&P 500 E-mini futures, 1998-2020.
  - The 2:00-3:00 a.m. ET hour, around the European open, averages 3.7% annualized (1.48 bp/day).
  - More than half of the 5.9% close-to-close return accrues overnight, and the 2-3 a.m. hour is about half of that.
  - After selloffs into the US close (negative closing imbalance), the 2-3 a.m. hour earns 17% annualized.
  - **The unconditional strategy's Sharpe is 1.1 gross and −0.5 after bid-ask spreads.** A conditional "buy the dip" version keeps a net Sharpe of 1.1. — [FRBNY SR 917 PDF](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf); [abstract page](https://www.newyorkfed.org/research/staff_reports/sr917)
- **Night effect in index ETFs.** Kelly and Clark (Journal of Asset Management 2011) studied broad index ETFs, 1999-2006. QQQQ's close-to-open risk premium is +23.7%/yr and its open-to-close premium is −23.3%/yr. Overnight returns are less volatile. — [Springer](https://link.springer.com/article/10.1057/jam.2011.2)
- **Cliff, Cooper and Gulen, "Return Differences between Trading and Non-trading Hours: Like Night and Day".** This won the best-paper award at the 2008 UC Davis/Financial Management conference. Its numbers could not be retrieved because SSRN rate-limited every attempt (see Gaps). — [Gulen's website](https://www.huseyingulen.com/); [SSRN 1004081](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1004081)
- **5-minute ORB on QQQ.** Zarattini and Aziz (2023, SSRN 4416622) report a 1,484% total return over 2016-2023, vs 169% for QQQ, and a 33% annualized alpha net of commissions, using QQQ and TQQQ. This is the authors' firm's summary. — [Concretum summary](https://concretumgroup.com/can-day-trading-really-be-profitable/); [SSRN 4416622](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622)
- **Independent replication of the QQQ ORB** (Jan 2016 to Feb 2023):
  - 1,775 trades vs the paper's 1,795; Sharpe 1.06 vs 1.12.
  - The gross edge is $0.070/share. **Net profit hits zero at about 2.2 cents/share of entry slippage**, while QQQ's spread is about 1 cent.
  - With 2 cents of slippage, Sharpe falls to 0.23.
  - An NQ-futures filter is significant per trade (t = 2.05), but **76% of its P&L comes from 2022**.
  - The bootstrap Sharpe interval [0.05, 1.41] overlaps buy-and-hold QQQ's [−0.03, 1.47].
  - Position sizing: 1% risk per trade with a 4x leverage cap. — [GitHub replication (T3)](https://github.com/giovannibrusco/zarattini-2023-orb-qqq)
- **ORB replication on five CFD index markets** (NQ, SPX, Dow, DAX, FTSE; Jan 2015 to Jun 2026). The gross result is reproduced (NQ +0.13R, hit rate about 23%). **Net results:** NQ +0.002R, and the other four markets lose money, using round-trip costs of 0.8-4.0 index points. — [MQL5 blog, 25 Sep 2026 (T3)](https://www.mql5.com/en/blogs/post/776235)
- **ORB on "stocks in play".** Zarattini, Barbon and Aziz (2024) studied about 7,000 US stocks, 2016-2023.
  - Top 20 by relative volume: Sharpe 2.81, total return 1,637%, annualized alpha 35.8%, volatility 14.8%.
  - Full-universe base strategy: Sharpe 0.48, total return 29%.
  - Assumptions: commission $0.0035/share, **no explicit slippage**, 4x leverage, stops at 10% of ATR, flat by 4 pm. — [SSRN 4729284](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284); [St. Gallen PDF](https://alexandria.unisg.ch/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/download)
- **SPY intraday momentum with trailing stops.** Zarattini, Aziz and Barbon (2024) report 1,985% net total return over 2007 to early 2024, 19.6%/yr, Sharpe 1.33. The abstract mentions a commission and slippage analysis without numbers. — [SSRN 4824172](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172)

#### Inferences
- **Break-even arithmetic (my calculation from the cited numbers):**
  - Intraday momentum on SPY trades every day, so about 504 sides per year. A 6.67%/yr gross return means a break-even cost of about **1.3 bp per side**. The paper's spread adjustment (6.67% to 4.46%) implies about 0.44 bp per side of SPY half-spread.
  - At QUANTGEN's 50 bp per side for US shares, annual cost would be about 252%, more than 37 times the gross return.
  - The overnight drift (1.48 bp/day) breaks even at about 0.7 bp per side.
  - End-of-day reversal (3.45 bp/day) and the HKS periodicity (3.01 bp) break even at under 2 bp per side. If both legs of the long-short pay a full round trip (four sides per day), break-even falls to about 0.75-0.9 bp per side.
  - The QQQ ORB breaks even at about 2.2 cents/share of entry slippage, which is on the order of 1 bp of price (roughly 0.5-2 bp across QQQ's 2016-2023 price range; my arithmetic).
  - **All of these are institutional-cost edges.**
- **Desk view.** I read intraday momentum and end-of-day reversal as the footprints of scheduled, price-insensitive flow: gamma hedging, leveraged-ETF rebalancing, short covering and MOC orders. A desk with the imbalance feed and sub-bp costs harvests that flow by supplying liquidity into it. A retail rule that waits for the pattern to show on a chart ends up demanding liquidity from that same desk.
- **The Lou-Polk-Skouras split matters for QUANTGEN's execution convention** even though it is not tradable directly. Momentum's premium accrues overnight. A momentum card filled at the next open captures less of it than one filled in the closing auction of the decision day. Value and quality premia are earned intraday, so the fill convention matters less for them. This is why DC-E2-01 runs the split on KRX data.
- **Korea is the weakest of the intraday-momentum markets studied** (out-of-sample R² 0.9%, p = 0.084). The Korean last half-hour also contains the 15:20-15:30 closing call auction, with dynamic VI at 2%/4% (see KQ4). A first-half-hour to last-half-hour rule on KRX is therefore partly a bet on the auction's clearing price.

#### Gaps
- Cliff, Cooper and Gulen (2008): magnitudes, sample and instruments were not retrieved (SSRN returned 429 on four attempts). The night effect is instead supported by Kelly and Clark (2011), Lou, Polk and Skouras (2019) and Boyarchenko et al. (2022).
- No peer-reviewed post-2020 replication of Gao et al. with realistic retail costs was found. The two ORB replications are T3 (GitHub and MQL5 blog), though their methods are transparent.
- No Korean study of ORB, VWAP-cross or opening-gap rules with KRX costs was found. Korean intraday evidence after 2021, and especially after Nextrade launched in March 2025, is missing.

---

### 3.2 KQ2: Execution realities. Impact, costs, reversal, closing auctions, VWAP, stops, round numbers

#### Takeaway
- **Impact** follows a near-universal square-root law: impact is roughly Y·σ·√(Q/ADV), with Y about 1. That makes size the enemy and the spread the floor.
- **Institutional costs** are far below academic estimates. Even so, high-turnover strategies such as short-term reversal die at reasonable size.
- **Reversal profits** are pay for providing liquidity, and they peak when the VIX is high.
- **Closing auctions** are the deepest liquidity event of the day, but their prices carry noise that reverses overnight.
- **S/R and round numbers** have a real order-placement basis, but the effects are small and intraday.
- **Stop orders** become market orders and fill far from the stop in fast markets.

#### Cited Findings
- **Square-root impact law.** Toth et al. (Physical Review X 2011) state impact as Y·σ·√(Q/V), with Y "of order unity". The concave law is reported across:
  - Citigroup US equity orders (exponent about 0.6)
  - Madrid (0.5) and London (0.7)
  - CFM's own futures trades, about 500,000 of them, Jun 2007 to Dec 2010 (0.5-0.6)
  - It holds for Q/V from a few 10⁻⁴ to a few percent. — [arXiv 1105.1694 (PDF)](https://arxiv.org/pdf/1105.1694); [abstract](https://arxiv.org/abs/1105.1694)
- **Universality on Tokyo data.** Sato and Kanazawa (Physical Review Letters 2025) used eight years of complete Tokyo Stock Exchange data covering all liquid stocks and all accounts. The impact exponent is 1/2 within about ±0.1, at both stock and trader level, and they reject the non-universal alternatives. — [arXiv 2411.13965](https://arxiv.org/abs/2411.13965)
- **Linear-to-square-root crossover.** Bucci et al. (PRL 2019) used 8 million US institutional trades: impact is linear for very small orders and square-root at intermediate sizes. — [arXiv 1811.05230](https://arxiv.org/abs/1811.05230)
- **Almgren-Chriss** (Journal of Risk 2001):
  - Separates permanent impact (shifts the equilibrium price) from temporary impact (imbalance-driven).
  - Builds a mean-variance efficient frontier of execution schedules, with a trade "half-life" θ = 1/κ.
  - Worked example: 1 million shares at $50 over 5 days, 30% volatility, 5 million shares ADV, κ about 0.6/day. — [hosted PDF](https://www.smallake.kr/wp-content/uploads/2016/03/optliq.pdf)
- **Actual institutional costs.** Frazzini, Israel and Moskowitz (2018) used $1.7 trillion of live executions across 21 developed markets over 19 years. Real costs are about an order of magnitude below earlier academic estimates, and their calibrated model wins out-of-sample. — [SSRN 3229719](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3229719); [AQR page](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs)
- **Costs by anomaly.** Frazzini, Israel and Moskowitz, "Trading Costs of Asset Pricing Anomalies" (AQR working paper) used about $1 trillion of trades across 19 markets, 1998-2011. Value, momentum and size survive costs at very large size. **Short-term reversal does not survive at reasonable size** and gains little from optimization. — [AQR](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies)
- **Turnover threshold.** Novy-Marx and Velikov (RFS 2016) studied US stocks, Jul 1963 to Dec 2012, using Hasbrouck-style effective-spread estimates.
  - Anomalies with one-sided monthly turnover below 50% mostly keep significant net spreads. Few above that level do.
  - **Short-term reversal:** turnover 90.87% per month; gross 0.37%/month (t = 1.71); **net −1.28%/month (t = −6.02)**. That implies about 1.65 percentage points per month of cost (gross minus net, my arithmetic).
  - A 10%/50% buy/hold band cuts turnover by 41% and costs by 42% for high-turnover strategies. Reversal still loses −0.72%/month (t = −3.78). — [NBER w20721 PDF](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf); [NBER abstract](https://www.nber.org/papers/w20721)
- **Reversal is pay for providing liquidity.** Nagel (RFS 2012) shows short-term reversal returns vary strongly over time and are predictable with the VIX. Expected returns and conditional Sharpe ratios rose sharply in 2007-09. Industry reversal, which usually underperforms, did well when the VIX was high. — [NBER w17653](https://www.nber.org/papers/w17653)
- **Closing auctions grew and carry noise.** Bogousslavsky and Muravyev (Journal of Financial Markets 2023):
  - The US closing auction's share of daily volume rose from 3.1% (2010) to 7.5% (2018), about $15.2bn/day in 2018.
  - The average absolute price deviation is 8.1 bp. The auction price equals the pre-close bid or ask 68.5% of the time. Deviations exceed 63 bp in 1% of cases.
  - Deviations reverse quickly and almost completely overnight. Where after-hours liquidity exists, one-third to one-half reverses within 30 minutes.
  - One percentage point more passive mutual-fund ownership goes with 3.7% more closing-auction turnover. S&P 500 inclusion permanently raises auction volume by about 20%. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1386418123000502)
- **Recent auction scale.** These four sources report different denominators and are not directly comparable:
  - NYSE, Aug 2024: record US closing auctions in Q2 2024 of $55.5bn/day, 9.44% of consolidated notional and 10.52% of NYSE-listed volume. Floor-broker D-orders were more than 46% of NYSE closing-auction volume. — [NYSE](https://www.nyse.com/data-insights/nyse-closing-auction-price-discovery-opportunities-reach-new-highs)
  - BMLL, Jun 2025: about $50bn/day in 2024, roughly 9% of daily volume; about 20% on rebalance and expiry days; more than 34% of daily notional on Russell reconstitution day, 28 Jun 2024. — [BMLL](https://www.bmlltech.com/news/market-insight/into-the-close-unpacking-u-s-closing-auction-dynamics-and-the-impact-of-the-russell-reconstitution)
  - Tethys, Dec 2024: six-month median closing-auction share of 12.48% for NYSE (14.18% notional-weighted) and 10.08% for Nasdaq (9.31%). Opening auctions are only 0.68-1.32%. — [Tethys](https://www.tethystech.com/wp-content/uploads/2024/12/Auction-Volume-Report-Americas.pdf)
  - NYSE, Apr 2026: Q1 2026 NYSE closing auction averaged 605.5m shares/day (about $43bn). Record day 20 Mar 2026: 3.57bn shares ($230.5bn). Unfilled interest is about 3.3% of executed volume. — [NYSE Insights](https://www.nyse.com/research/insights/behind-the-record-volumes-a-hidden-opportunity)
- **How the close works.**
  - NYSE schedule: MOC/LOC entry cutoff and start of per-second imbalance publication at 3:50 p.m.; MOC/LOC cancels rejected after 3:50; D-orders accepted until 3:59:50; auction at 4:00. — [NYSE closing auction guide](https://www.nyse.com/article/nyse-closing-auction-insiders-guide)
  - In Sep 2025, for NYSE-listed S&P 500 names, D-orders were about 60% of auction volume, with MOC about 20% and LOC about 20%. More than 60% of D-orders arrive after 3:57:30. D-orders in the last 10 seconds rose from 4.45% to 13.4% between Aug 2024 and Sep 2025. — [NYSE, Nov 2025](https://www.nyse.com/research/insights/nyse-closing-auction-timing-shifts-and-marketability-trends)
  - NYSE assigns one DMM per listed security, obliged to keep markets fair and orderly and to run opens, closes and imbalances. Current DMM firms: Citadel Securities, Virtu and GTS. — [NYSE market model](https://www.nyse.com/market-model)
- **VWAP as an execution benchmark.** Busseti and Boyd (2015) treat VWAP as a benchmark for risk-averse brokers splitting large orders. Modelling volume uncertainty reduces VWAP tracking error (RMSE) by about 10%. — [arXiv 1509.08503](https://arxiv.org/abs/1509.08503)
- **Support/resistance in FX.** Osler (FRBNY Economic Policy Review, July 2000) used S/R levels published by six firms for USD/DEM, USD/JPY and GBP/USD, Jan 1996 to Mar 1998.
  - Published levels stopped intraday trends 60.8% of the time on average, vs 56.2% for arbitrary levels.
  - For most firms, predictive power lasted at least five business days.
  - More than 70% of levels end in 0, and 96% end in 0 or 5. — [EPR PDF](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf)
- **Stop and take-profit clustering.** Osler (JF 2003; FRBNY Staff Report 125) used orders at a major FX dealing bank. Both stops and take-profits cluster at round numbers. Take-profits tend to reverse trends at levels; stops intensify trends once levels are crossed. — [FRBNY SR 125](https://www.newyorkfed.org/research/staff_reports/sr125.html)
- **Stop cascades.** Osler (JIMF 2005; FRBNY Staff Report 150): stop-loss orders produce self-reinforcing price cascades. Their effects are larger and longer-lasting than take-profit effects and help explain fat tails. — [FRBNY SR 150](https://www.newyorkfed.org/research/staff_reports/sr150.html)
- **Round numbers in US stocks.** Bhattacharya, Holden and Jacobsen (Management Science 2012) used more than 100 million trades.
  - Liquidity demanders buy too much one penny below round numbers and sell too much one penny above.
  - The effect is largest at whole dollars and stronger when approaching a round number than when crossing it.
  - These trades lose close to $1bn per year. — [RePEc/IDEAS](https://ideas.repec.org/a/inm/ormnsc/v58y2012i2p413-431.html)
- **Stop orders, regulator view.** A stop order becomes a market order once the stop price is reached. The fill can be "markedly different" from the stop price in fast markets. Brief price swings can trigger stops, and stop-limit orders may not execute at all. — [FINRA](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets); [SEC Investor.gov](https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order)
- **US tick reform.** On 18 Sep 2024 the SEC adopted a $0.005 tick for qualifying NMS stocks priced at $1 or more, assigned by time-weighted average quoted spread. Access-fee caps fall to $0.001/share. Compliance: Nov 2025 (odd-lot information May 2026). — [SEC press release 2024-137](https://www.sec.gov/newsroom/press-releases/2024-137)
- **Retail execution quality varies.** Schwarz, Barber, Huang, Jorion and Odean (2022) placed 85,000 simultaneous market orders through six accounts at five brokers. Mean round-trip cost ranged from −0.07% to −0.46%, excluding commissions. Differences in payment for order flow do not explain the spread in execution quality. — [SSRN 4189239](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4189239)

#### Inferences
- **Impact sizing for QUANTGEN cards (my arithmetic, using the square-root law with Y = 1):**

| Daily vol σ_d | Order / 20-day ADV | Impact estimate |
|---|---|---|
| 2% (large cap) | 0.1% | ≈ 6 bp |
| 2% | 1% | ≈ 20 bp |
| 2% | 10% | ≈ 63 bp |
| 3% (small cap) | 1% | ≈ 30 bp |
| 3% | 10% | ≈ 95 bp |

  At individual-investor size in KOSPI 200 names, impact is negligible and **the tick plus the tax are the binding costs**. In small or thin KOSDAQ names, an order of 10 million KRW or more can be a meaningful share of ADV, and impact can exceed the 35 bp per-side budget on its own.
- **Desk view on support/resistance.** S/R is the visible residue of where resting limit orders, take-profits and stops cluster: round numbers, prior highs and lows, and levels other people have published. Market makers know the obvious levels as well as chartists do. Osler's 4.6-point hit-rate edge and the Bhattacharya-Holden-Jacobsen losses together suggest that traders who visibly trade at levels transfer money to liquidity providers. A daily-close system should treat levels as places where stop cascades happen, not as entry signals.
- **Desk view on gaps.** The open is set by an auction that clears overnight information plus accumulated imbalance: KRX publishes an indicative price from 08:40, and NYSE DMMs run the open. Boyarchenko et al. show selloffs into the close tend to revert overnight. That is a liquidity-provision trade, not a "gap continuation" trade. No primary evidence on "gap fills" was found (see Gaps), so it goes to the data lab as DC-E2-07.
- **Desk view on stops.** Simulating a stop fill at the stop price is the single most common way backtests overstate short-horizon P&L. The honest fill is the next available price: the next open after a gap, or no fill during a limit-down lock or a 2-minute VI auction.
- **The 8.1 bp average and 63 bp tail closing-auction deviation** (Bogousslavsky-Muravyev) means close-to-close reversal measured on official closes partly harvests auction noise. You can only capture that noise by trading in the auction. That is why every reversal card needs a skip-day variant.

#### Gaps
- Frazzini-Israel-Moskowitz's numeric impact parameters, average bp costs and per-strategy break-even fund sizes could not be retrieved; the full PDFs were unavailable or rate-limited.
- No quantitative study of average stop-order slippage for US or KRX equities was found. DC-E2-08 proposes a KRX proxy.
- No peer-reviewed evidence was found that retail "VWAP-cross" or "VWAP-reclaim" rules earn returns net of costs. VWAP appears in the literature only as an execution benchmark.
- An exact 2015 closing-auction share for the US was not found; the series runs 2010, 2018, 2024 and Q1 2026. No closing-auction share was found for KRX at all.

---

### 3.3 KQ3: Retail day-trader outcomes (Taiwan, Brazil, Korea, US/Robinhood)

#### Takeaway
Across every complete-population dataset found, short-horizon retail trading loses money in aggregate. Losses come mainly from taxes, commissions and aggressive (liquidity-taking) orders. Fewer than about 1% of day traders are reliably profitable net of fees. Korea's 2020 retail boom showed the same pattern: very high turnover, more than half of trading done intraday, and negative net returns for new investors in a rising market.

#### Cited Findings
- **Taiwan, day traders.** Barber, Lee, Liu and Odean (Journal of Financial Markets 2014) used all Taiwan Stock Exchange trades, 1992-2006 (3.7bn trades).
  - Day trading is about 17% of volume, almost all by individuals.
  - **Fewer than 1% of day traders predictably earn positive abnormal returns net of fees**, about 4,000 of roughly 450,000 per year.
  - Top 500: 61.3 bp/day gross, 37.9 bp/day net. Bottom-ranked: 11.5 bp/day gross, **−28.9 bp/day net**.
  - Costs: a 30 bp tax on sales plus 5-14.25 bp commission per side. — [Berkeley PDF](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/The%20Cross-Section%20of%20Speculator%20Skill.pdf)
- **Taiwan, learning and persistence** (same authors, 1992-2006).
  - About 140,000 people day trade in an average month, just under 1% of adults.
  - More than 75% quit within two years, yet experienced unprofitable traders keep going.
  - Aggregate day-trader performance net of fees is negative in every one of the 15 years. The net figure extracted was about −23.9 bp/day after 10 bp commissions and the 30 bp tax. — [Berkeley PDF](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf)
- **Taiwan, all individual trading.** Barber, Lee, Liu and Odean (RFS 2009) studied 1995-1999.
  - Individuals' trading cuts their returns by 3.8 points per year, equal to 2.2% of GDP or 2.8% of personal income.
  - Breakdown of losses: transaction taxes 34%, commissions 32%, trading losses 27%, market timing 7%.
  - **Virtually all trading losses trace to aggressive orders.**
  - Institutions earn +1.5 points per year after costs, and foreigners take nearly half of institutional profits. — [Berkeley PDF](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/JustHowMuchDoIndividualInvestorsLose_RFS_2009.pdf)
- **Brazil.** Chague, De Losso and Giovannetti studied equity-index futures day traders, 2013-2015.
  - 97% of individuals who kept trading more than 300 days lost money.
  - Only 1.1% earned more than the minimum wage, and 0.5% more than a bank teller's starting salary.
  - The authors call day trading for a living "virtually impossible". — [SSRN 3423101](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101)
- **Korea, 2020.** Kim and Kim (KCMI issue report 21-11, June 2021) studied 204,004 investors at four large brokers, Mar-Oct 2020. About 30% (60,446) were new investors.
  - **60% of new investors lost money.**
  - Intraday round trips were 55.4% of trading overall, 80.8% for investors in their 20s or younger, and 76.8% for small accounts. Daily turnover was 6.8%.
  - Costs (commissions plus a 25 bp sell tax) cut returns by 4.0 points over the period.
  - Overall portfolio return was 18.4% gross and 14.4% net. Existing investors earned 15.0% net; **new investors earned −1.2% net**. — [KCMI report 1243](https://www.kcmi.re.kr/report/report_view?report_no=1243)
- **Korea, 2020, by investor group.** A Financial News report on the KCMI webinar (14 Apr 2021) says 46% of all investors lost money (62% of new, 39% of existing). Higher turnover, more intraday trading and more frequent stock switching went with lower daily excess returns. Lottery-type stocks were 38.2% of excess trading value in the highest-turnover group. — [Financial News](https://www.fnnews.com/news/202104131912345956)
- **Korea, behavioural biases.** Kim and Kim (KCMI, Feb 2022) put Korean retail annual turnover at about 1,600% in 2020. For frequent traders, stocks bought underperformed stocks sold. Lottery preference went with worse performance, and herding was followed by reversals. — [KCMI report 1481](https://www.kcmi.re.kr/report/report_view?report_no=1481)
- **Korea, overseas investing.** Kang and Kim (KCMI research report 26-04, Feb 2026) studied 102,380 individuals investing abroad, 2020-2022.
  - Investors in their 20s turned over overseas stocks 14.9 times a year.
  - High-multiple leveraged ETFs (e.g., UltraPro QQQ) were among top holdings.
  - After costs, losers outnumbered winners, and few beat the benchmark. — [KCMI report 2254](https://www.kcmi.re.kr/report/report_view?report_no=2254)
- **Korea, foreign vs domestic investors.** Choe, Kho and Stulz (RFS 2005; NBER w8073) studied Korea, Dec 1996 to Nov 1998. Foreign investors traded at worse prices than residents, especially on large trades, small caps and sales. Domestic individuals had a short-lived private-information edge. — [NBER w8073](https://www.nber.org/papers/w8073)
- **US, Robinhood herding.** Barber, Huang, Odean and Schwarz (JF 2022) find that stocks with intense Robinhood herding earn an average 20-day abnormal return of −4.7%. — [SSRN 3715077](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3715077)
- **US, conflicting evidence.** Welch (JF 2022) finds the Robinhood crowd bought into the March 2020 crash and that its consensus portfolio did well from mid-2018 to mid-2020. — [NBER w27866](https://www.nber.org/papers/w27866)
- **US, the January 2021 meme episode.** The SEC staff report (Oct 2021) on GameStop:
  - GME's off-exchange share was 62.6% on 21 Jan 2021, and the top three wholesalers executed 88% of internalized volume.
  - Short interest reached 122.97% of float. The price rose about 2,700% intraday from 8 to 28 Jan, peaked at $483 on 28 Jan, then fell more than 86%.
  - Accounts trading GME went from under 10,000 to about 900,000. NSCC issued $6.9bn of intraday margin calls on 27 Jan.
  - Staff found no evidence of a gamma squeeze. — [SEC staff report](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf)

#### Inferences
- **The base rate for QUANTGEN's audience is losing.** Any card or UI that nudges users toward short-horizon technical trading contradicts the evidence. The Taiwan breakdown (66% of losses from taxes plus commissions) maps directly onto Korea's sell tax of 0.15-0.25% over 2020-2026.
- **The "aggressive orders" finding** (Barber et al. 2009) is the retail mirror of the desk view in KQ2. Retail traders lose by crossing the spread into professionals' quotes, at round numbers and on visible breakouts.
- **The Robinhood evidence conflicts** (Welch vs Barber et al.). Holding a buy-and-hold crowd portfolio and chasing attention spikes are different behaviours. Only the second resembles short-horizon technical trading.

#### Gaps
- A peer-reviewed, complete-population study of Korean day traders specifically (like the Taiwan studies) was not found in this session. The KCMI evidence covers broker samples (4 brokers, 8 months).
- No Korean data on retail outcomes after Nextrade's extended hours (2025-2026) were found.

---

### 3.4 KQ4: Korea microstructure. Auctions, VI, ±30% limits, Nextrade, tax, tick sizes

#### Takeaway
KRX's market design interrupts exactly the intraday dynamics that technical rules rely on:
- 2-minute VI call auctions at ±3% or ±6% (dynamic) and ±10% (static) from the reference price
- a random-end closing call auction (15:20-15:30)
- ±30% daily limits
- 3-day periodic-call regimes for overheated stocks

Coarse ticks of 5-25 bp of price plus a 0.20% sell tax (2026) set a high cost floor. Nextrade (since March 2025) adds 12-hour trading, midpoint and stop-limit orders, and cheaper fees. But its stock list shifts quarterly under a volume cap of 15% of KRX, and its and KRX's after-hours sessions are thinner, separate markets from the official close.

#### Cited Findings
- **KRX trading hours** (KRX global site, accessed 2 Oct 2026):
  - Regular session 09:00-15:30.
  - Pre-hours closing-price trading 08:30-08:40.
  - After-hours closing-price trading 15:40-16:00.
  - After-market 16:00-20:00.
  - Block/basket trading 08:00-09:00 and 15:40-20:00.
  - Settlement T+2. — [KRX trading hours](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T1.jsp)
- **Opening and closing auctions.**
  - The opening price is set from orders taken 08:30-09:00, and the indicative price is published from 08:40. — [KRX quotation publication](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T6.jsp)
  - Limit-on-close orders convert to market orders at 15:20, when the closing call auction starts taking orders. — [KRX order types](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T2.jsp)
  - Call auctions close at a random time within 30 seconds after the closing point. — [KRX call auction](https://global.krx.co.kr/contents/GLB/06/0602/0602010202/GLB0602010202T1.jsp)
- **KRX after-hours detail page** describes "after-market single price trading" at 16:00-20:00. It gives the price band as the previous day's close ±30% and calls the method continuous trading. A single-price session described as continuous, with a band anchored to the previous day's close, is internally inconsistent. This needs checking against the Korean-language rules. — [KRX off-hours page](https://global.krx.co.kr/contents/GLB/06/0602/0602010203/GLB0602010203T1.jsp)
- **Daily price limits.** ±30% of the base price since 15 Jun 2015. Earlier: 6% (Apr 1995), 8% (Nov 1996), 12% (Mar 1998), 15% (Dec 1998). Leveraged ETFs' limits scale with leverage. — [KRX price limits](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T5.jsp)
- **Volatility interruption (VI).**
  - Dynamic VI: 3% for KOSPI 200 constituents during continuous trading and the after-market, 2% in the closing auction. Other KOSPI/KOSDAQ stocks: 6% and 4%. (A 1% special rate applies on the final trading day for derivative underlyings.)
  - Static VI: 10%.
  - A triggered VI runs a 2-minute call auction. There is no daily limit on triggers. — [KRX VI rules](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T9.jsp)
- **Overheating measure** (since 5 Nov 2012). It triggers when three conditions all hold:
  - the close is at least 30% above the 40-day average close
  - the 2-day average turnover is at least 500% of the 40-day average
  - 2-day volatility is at least 50% above the 40-day average
  - After a notice sequence, the stock trades in a 3-day periodic call auction. — [KRX overheat measures](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T8.jsp)
- **Circuit breakers.** KOSPI −8%: 20-minute halt. −15% plus a further 1%: 20-minute halt. −20% plus a further 1%: market closes for the day. Levels 1 and 2 cannot trigger in the last 40 minutes. — [KRX circuit breakers](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T2.jsp)
- **Sidecar.** If KOSPI 200 futures move ±5% from base for 1 minute, program-trading orders are suspended for 5 minutes. Not applied in the last 40 minutes. — [KRX sidecar](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T4.jsp)
- **Tick sizes.** One tick ranges from 0.05% to 0.25% of price:

| Price band (KRW) | Tick (KRW) |
|---|---|
| below 2,000 | 1 |
| 2,000-5,000 | 5 |
| 5,000-20,000 | 10 |
| 20,000-50,000 | 50 |
| 50,000-200,000 | 100 |
| 200,000-500,000 | 500 |
| 500,000 and above | 1,000 |

  — [KRX tick sizes](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp)
- **Securities transaction tax** on KOSPI and KOSDAQ shares, including the rural development special tax:
  - 0.18% (2024), 0.15% (2025), **0.20% from 1 Jan 2026**. — [PwC tax summaries](https://taxsummaries.pwc.com/republic-of-korea/corporate/other-taxes)
  - EY confirms the 2026 increase to 0.20%; the split into components was ambiguous in the extracted text. — [EY tax news, Jan 2026](https://taxnews.ey.com/news/2026-0126-korea-enacts-2026-tax-reform-bill)
  - KCMI's 2020 study assumed a 25 bp sell tax. — [KCMI report 1243](https://www.kcmi.re.kr/report/report_view?report_no=1243)
- **Nextrade (NXT) design.**
  - Launched March 2025, trading 08:00-20:00. — [Korea Times, 19 Nov 2025](https://www.koreatimes.co.kr/economy/policy/20251119/koreas-alternative-stock-exchange-faces-foreign-investor-complaints-over-15-trading-cap)
  - Sessions: pre-market 08:00-08:50, main 09:00:30-15:20, after-market 15:40-20:00. Offers midpoint and stop-limit orders. About 601 stocks traded in the main market on 2 Oct 2026. — [Nextrade home](https://www.nextrade.co.kr/)
  - Twelve hours of trading, 5.5 more than KRX's regular session. Fees 20-40% below KRX. Same price limits, market measures, surveillance, clearing and settlement as KRX; short selling is managed jointly. — [Nextrade market overview](https://www.nextrade.co.kr/marketOverview/content.do)
  - Fees: maker (including closing-price and block trades) 0.00134%, taker 0.00182%, single-price 0.00158%. Fees were waived in Mar-Apr 2025. — [Nextrade fees](https://www.nextrade.co.kr/html/charge-info.html)
- **Nextrade volume cap and stock list.**
  - By law, an alternative trading system's 6-month average daily volume may not exceed 15% of KRX volume.
  - Nextrade dropped 32 stocks from 1 Jul 2026, leaving 610 eligible (338 KOSPI, 272 KOSDAQ). Its volume share topped 20% on 12 Jun 2026. — [Seoul Economic Daily, 26 Jun 2026](https://en.sedaily.com/finance/2026/06/26/nextrade-drops-32-stocks-including-kakao-korean-air-from-q3)
  - It suspended stocks four times in 2025 (20 Aug, 1 Sep, 22 Sep, 5 Nov), cutting the list from about 800 to 630. Foreign investors' share rose from 0.4% (Mar) to about 9% (Jun 2025), and retail is more than 80%. — [Korea Times](https://www.koreatimes.co.kr/economy/policy/20251119/koreas-alternative-stock-exchange-faces-foreign-investor-complaints-over-15-trading-cap)
- **Nextrade market share.** Trading value relative to KRX: 26.9% (Apr 2025), 49.4% (Oct 2025), 31.3% (1-12 Dec), and 21.3% in the five days after KRX cut fees on 15 Jan. Volume share fell from 11.7% to 9.7%. KRX moved from a flat 0.0023% fee to a tiered schedule matching Nextrade's for 15 Jan to 13 Feb. *Caution:* the page is dated 21 Dec 2025 but reports January data, so the dates are internally inconsistent. — [Seoul Economic Daily](https://en.sedaily.com/finance/2025/12/21/nextrade-market-share-shrinks-as-korea-exchange-cuts-fees)
- **After KRX opened its own after-hours market** (late Sep 2026), Nextrade's daily share fell from 10.64% to 9.10%. KOSDAQ stocks are about 80% of KRX after-hours volume. This is a T3 aggregator citing Seoul Economic Daily. — [Archynewsy, 27 Sep 2026](https://www.archynewsy.com/nextrade-market-share-falls-after-korea-exchange-opens-after-hours-market/)
- **Korean intraday momentum is weak** (KOSEF 200 ETF, 2008-2021). — [Limkriangkrai et al. 2023](https://researchmgt.monash.edu/ws/files/519509174/494419119_oa.pdf)

#### Inferences
- **How KRX rules break intraday technical rules:**
  - Breakouts: a fast breakout above an opening range or prior high can trigger a 2-minute call auction. That happens if it jumps past the dynamic VI threshold relative to its reference price (3% for KOSPI 200 names, 6% for other stocks), or past the 10% static VI threshold. The rule's "entry on break" price then stops existing, and the fill is the auction price.
  - The close: in the closing auction the dynamic VI tightens to 2% or 4%, so a last-half-hour momentum push can trigger a VI mid-auction.
  - Overheated names: a 3-day periodic-call regime makes intraday rules impossible to run.
  - Limit locks: in a lock at ±30%, a simulated stop or entry may not fill at all.
- **Cost floor (my arithmetic).** One tick is 5-25 bp of price. Crossing a one-tick spread both ways costs one tick, plus 20 bp tax, for a round trip of about **25-45 bp before commission and impact**. QUANTGEN's 35 bp per side (70 bp round trip) leaves roughly 25-45 bp for commission, wider spreads and impact. That is adequate for liquid KOSPI 200 names but thin for low-priced or thin KOSDAQ names, where spreads are often several ticks (needs checking, see DC-E2-06).
- **Nextrade does not change the daily-close design but adds data-hygiene risks:**
  1. The KRX closing auction (15:20-15:30) remains the official close: Nextrade's main market ends at 15:20 and its after-market starts at 15:40.
  2. Prints after 15:30 on Nextrade or the KRX after-market are a different, thinner market. They must not overwrite the decision-day close.
  3. Nextrade-eligible stocks change quarterly, so any rule using extended hours carries venue-availability risk.
  4. Nextrade's stop-limit and midpoint orders make retail stop placement more visible to the market, not less (desk view).
- **The tax path matters for backtests.** At least 0.25% (2020), 0.18% (2024), 0.15% (2025) and 0.20% (2026). A flat 35 bp per side over 1995-2026 is roughly right on average but should be checked against the time-varying statutory schedule.

#### Gaps
- No share of KRX volume executed in the opening or closing auctions was found.
- The exact design of KRX's 2026 after-market (continuous vs periodic call, price band, eligible stocks, start date) needs the Korean-language KRX notice. The English page is inconsistent.
- No Korean empirical study of how VI, the closing auction or Nextrade affects intraday returns was found.
- Whether Nextrade's 30% per-stock cap exists, as some reports suggest, was not verified. Only the 15% market-wide rule was sourced.
- The English KRX VI page gives thresholds and the 2-minute auction length but not the reference prices. Practitioners commonly describe them as the immediately preceding trade for dynamic VI and the last single-price auction price for static VI, but this was not confirmed from an official source here.
- Whether KIS Open API daily or "current price" fields mix Nextrade prints into the close is unverified (see DC-E2-10).

---

### 3.5 KQ5: QUANTGEN translation. Should intraday rules be in QUANTGEN? Which daily-close constructs avoid microstructure traps? What should every short-horizon card carry?

#### Takeaway
**No intraday technical rule should be a BUILD candidate.** The edges are 1-7 bp gross against 70-100 bp round-trip costs. QUANTGEN has no order path and no intraday history long enough for the gate, and KRX's VI, auction and limit rules break the mechanics of entering on a break.

What QUANTGEN can test credibly is daily-close constructs that:
- trade at most weekly
- keep one-sided monthly turnover below about 50%
- are run under two fill conventions: closing auction t, and close t+1
- carry a tick-floor-plus-impact cost model
- treat stops as next-available-price fills

The one short-horizon family worth a BACKLOG slot is **volatility-conditioned, liquidity-filtered weekly reversal**. It must be skip-day tested and banded.

#### Cited Findings
- **QUANTGEN's own record already shows the trap.**
  - Card E8 (KODEX/TIGER pairs) is REVISE: Sharpe 0.55, loses at 2x costs, and its half-life of one session is bid-ask bounce.
  - E8 GLD/IAU pairs: Sharpe −2.28 because costs eat the spread.
  - E5 sector momentum: below buy-and-hold after 50 bp per side. — [QUANTGEN context brief, study run 2026-09-27](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/00_QUANTGEN_context.md)
- **Turnover threshold** of about 50% one-sided per month for net survival; reversal net −1.28%/month (US, 1963-2012). — [Novy-Marx and Velikov](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf)
- **Reversal pay is highest when the VIX is high** (2007-09). — [Nagel 2012](https://www.nber.org/papers/w17653)
- **Closing-auction prices deviate** by 8.1 bp on average (63 bp tail) and revert overnight. — [Bogousslavsky and Muravyev 2023](https://www.sciencedirect.com/science/article/abs/pii/S1386418123000502)
- **Momentum is earned overnight; value, quality and size intraday** (US, 1993-2013). — [Lou, Polk, Skouras](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf)
- **Impact scales as √(Q/V).** — [Toth et al. 2011](https://arxiv.org/pdf/1105.1694); [Sato and Kanazawa 2025](https://arxiv.org/abs/2411.13965)
- **Stops become market orders** and can fill far from the stop. — [FINRA](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)
- **KRX VI, limits, overheating and random-end auctions** (see KQ4). — [KRX VI](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T9.jsp); [KRX limits](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T5.jsp)

#### Inferences: my recommendations as E2

**A. Keep out of BUILD (DROP, or CONTEXT only):**
- market intraday momentum
- ORB on any instrument
- VWAP-cross and VWAP-reclaim
- intraday S/R bounces and round-number fades
- gap-and-go and opening-gap fades (unless a daily data-check passes)
- overnight-hold (night-effect) strategies
- end-of-day cross-sectional reversal
- half-hour periodicity

Reasons: break-even costs of 0.7-2 bp per side against 35-50 bp, no order path, and no gate-length intraday history. If an intraday module is ever wanted, it should only record KIS quotes prospectively, flagged "INSUFFICIENT DATA until 882 recorded sessions" (756 in-sample plus 126 out-of-sample).

**B. Daily-close constructs that avoid the traps:**
1. **Two fill conventions on every card.**
   - (a) Fill in the closing auction of t. This is realistic only if the signal can be computed from a pre-auction snapshot, about 15:19 KST on KRX or before the 15:50 ET MOC cutoff on NYSE. Add an auction-slippage term of at least 8 bp, per Bogousslavsky-Muravyev.
   - (b) Fill at close t+1 as a conservative bound.
   - Report both. If performance depends on (a), the edge lives in the last print.
2. **Skip-day variants for every reversal or short-horizon signal.** Signal at t, entry at close t+1 or open t+1. This removes bid-ask bounce and auction-pressure reversal, which is the cause of QUANTGEN's own E8 result.
3. **Unfillable-day rules.** No entry or exit at a close that is limit-up or limit-down. Flag days with closing-auction VI or an overheating designation. During halts, the simulated position cannot be changed.
4. **Liquidity and tick screens.** Universe of the top N stocks by 20-day median trading value. Add half the tick-to-price ratio as a minimum half-spread. Exclude names where one tick is more than about 0.25% of price, or charge more for them.
5. **Turnover discipline.**
   - Hold for at least 5 sessions.
   - Use a buy/hold band, for example enter at the top decile and exit only below the top three deciles, per Novy-Marx-Velikov.
   - Target one-sided monthly turnover of 50% or less.
6. **Exits evaluated at the close.** Never use touch-based intraday stops on daily bars. If a stop is modelled, fill at the worse of the stop price and the next open. During a limit lock or VI, there is no fill until the lock clears.
7. **Momentum entries at the close, not the next open**, given the overnight accrual of momentum (to be confirmed on KRX by DC-E2-01). Value and quality cards are less sensitive to this.
8. **Data source.** Use only KRX official closing prices as decision and fill prices. Exclude Nextrade or after-market prints after 15:30 from close-based signals. Record the snapshot timestamp.

**C. What every short-horizon card should carry (a proposed card header):**

| Field | Content |
|---|---|
| Decision timestamp and data source | e.g., "KRX official close 15:30 KST", or a pre-auction snapshot time |
| Fill convention | closing auction t + slippage, close t+1, or open t+1 + gap |
| Per-side cost, itemized | commission; sell tax using the time-varying schedule; half-spread floor of tick/2 by price band; impact Y·σ_d·√(Q/ADV₂₀) with Y = 1; then the 2x stress |
| Turnover and break-even | one-sided monthly turnover; break-even per-side cost = gross annual return / (2 × annual turnover). A card whose break-even is below 2x its pre-registered cost is REJECTED before the gate. |
| Capacity | position size at most 1% of 20-day ADV, or the impact term made explicit |
| Latency class | "close-auction" or "next-session". No intraday latency is ever assumed. |
| Fill rules | limit orders fill only on trade-through, never on touch; stops fill at the next available price; no fills on locked limit days |
| Regime flags | ±15%→±30% limit (15 Jun 2015); tick-table changes; tax schedule; Nextrade era (Mar 2025-); KRX after-market launch (2026); US half-penny tick (Nov 2025) |

**D. Conflicts with the prior design to flag:**
1. **Korea short-term reversal weight 3 is not supported net of 70 bp round trips** by any evidence found here. Arithmetic: daily reversal at 100% daily turnover costs 2 × 35 bp × 252, about **176%/yr**. Weekly reversal costs about 36%/yr. A monthly reversal at 90% monthly turnover costs about 0.63%/month. The latter could survive the −2.95%/month Korean 1-month reversal cited in the context brief, but only if that gross figure holds value-weighted in a liquid universe. **My suggestion: weight 1-2 until DC-E2-02 and DC-E2-03 pass.**
2. **The prior design's "volume/20-day average > 1.5" reversal filter** should be tested in both directions (DC-E2-02). I could not verify in this session which direction the literature supports.
3. **Consistent with the macro research:** holding reversal at 1.0x and never cutting it in stress fits Nagel's finding that reversal pays most when the VIX is high. Up-weighting it in stress would ignore the wider spreads that come with high VIX.

#### Gaps
- KIS Open API's latency, rate limits and whether its quotes include Nextrade prints were not sourced.
- No direct evidence on KRX closing-auction price pressure, comparable to Bogousslavsky-Muravyev for the US, was found. DC-E2-11 is only a partial proxy.
- **Coverage limits of this note.** The session-wide web-search quota (200) ran out partway through, and SSRN rate-limited repeated fetches. Several sources therefore come from abstract pages or author-hosted PDFs, and some primary documents (Cliff-Cooper-Gulen; Frazzini-Israel-Moskowitz full text; Korean-language KRX and Nextrade rules) could not be opened.

---

## 4. Where and when it failed (dated episodes)

| Date / period | Episode | Numbers | Lesson for short-horizon rules | Source |
|---|---|---|---|---|
| 6 May 2010 | US flash crash | A 75,000-contract E-mini sell algorithm (~$4.1bn) targeting 9% of volume. E-mini and SPY fell ~5-6% in about 4 minutes. More than 20,000 trades in 300+ securities executed over 60% away from prices moments earlier, all broken. Stub-quote fills at $0.01 and $100,000. Retail stop-loss orders added to the selling. | Stops become market orders at the worst moment. Simulated stops at the stop price are fiction. | [SEC-CFTC report](https://www.sec.gov/news/studies/2010/marketevents-report.pdf) |
| 24 Aug 2015 | US opening dislocation | 1,278 LULD halts in 471 securities, 83% ETPs. SPY opened −5.2% and was −7.8% by 9:35. IVV fell 20% or more, below its NAV. QQQ was about −17% by 9:31. MDT fell −16.5% in 39 seconds and JPM −13.3% in 65 seconds. By 9:35 only 38% of NYSE S&P 500 names had opened. 19.2% of ETPs fell 20% or more. | Gap-through stops and opening-auction failures. ETF fills can be far from NAV. | [SEC staff paper](https://www.sec.gov/marketstructure/research/equity_market_volatility.pdf) |
| Jan 2021 | GME / meme-stock episode | Short interest 122.97% of float. Price up ~2,700% intraday from 8 to 28 Jan, peak $483, then down more than 86%. Robinhood restricted trading 28 Jan to 5 Feb. NSCC intraday margin calls $6.9bn. | Attention-driven retail order flow, broker restrictions and margin calls can stop a technical strategy from executing at all. | [SEC staff report](https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf) |
| 5 Aug 2024 | Carry-trade unwind | TOPIX −12% in one day. KOSPI's worst decline since 2008. VIX above 60 pre-market, closed below 40. S&P 500 −3.0%, recovered by 9 Aug. Japan Securities Clearing Corp raised index initial margins 60-80%. | Gap opens through every stop. The VIX spike was larger than returns justified, so volatility-triggered rules over-react. | [BIS Bulletin 90](https://www.bis.org/publ/bisbull90.pdf); [BIS Quarterly Review, Sep 2024](https://www.bis.org/publ/qtrpdf/r_qt2409a.htm) |
| 1963-2012 | US one-month reversal | Gross +0.37%/month becomes net −1.28%/month; still −0.72%/month with a buy/hold band. | Turnover of ~91%/month cannot survive costs. | [Novy-Marx and Velikov](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) |
| 1998-2020 | Unconditional overnight drift, E-mini | Sharpe 1.1 gross, −0.5 after spreads. | 1.48 bp/day edges die at any retail cost. | [FRBNY SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf) |
| 14 Feb-31 Mar 2020 | APAC intraday momentum during COVID | Effect weakened across APAC and disappeared in China. | Intraday patterns change by regime. | [Limkriangkrai et al.](https://researchmgt.monash.edu/ws/files/519509174/494419119_oa.pdf) |
| 2007-2018 | US intraday momentum (SPY/QQQ) | Classic intraday-momentum and overnight predictors weakened over time. | Possible decay after publication; conflicts with Baltussen et al. | [Zhang and Hua 2024](https://www.mdpi.com/2227-9091/12/11/180) |
| 2016-2023 | QQQ 5-minute ORB (replication) | Breaks even at ~2.2 cents/share of slippage. Sharpe 0.23 with 2 cents of slippage. Filtered version loses in 2017, 2020 and early 2023, with 76% of P&L from 2022. | A headline "1,484%" result vanishes once fills are realistic. | [GitHub replication](https://github.com/giovannibrusco/zarattini-2023-orb-qqq) |
| 2015-2026 | ORB on five CFD index markets | Gross +0.13R becomes net about 0 (NQ +0.002R; four markets negative). | Spreads take the whole edge. | [MQL5 blog (T3)](https://www.mql5.com/en/blogs/post/776235) |
| 1992-2006 | Taiwan day traders | Aggregate net return negative in every one of 15 years. Fewer than 1% predictably profitable. | The base rate for retail short-horizon trading. | [Barber et al.](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf) |
| 2013-2015 | Brazil index-futures day traders | 97% of those trading more than 300 days lost money. | Persistence does not mean skill. | [Chague et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101) |
| Mar-Oct 2020 | Korean new retail investors | Net −1.2% vs +15.0% for existing investors. 55.4% of trading intraday. Costs took −4.0 points. | High turnover in a rising market still loses. | [KCMI 21-11](https://www.kcmi.re.kr/report/report_view?report_no=1243) |
| 20 Aug, 1 Sep, 22 Sep, 5 Nov 2025; 1 Jul 2026 | Nextrade stock removals | List cut from ~800 to 630 stocks in 2025; 32 more removed for Q3 2026 (610 eligible). | Extended-hours rules face venue-availability risk. | [Korea Times](https://www.koreatimes.co.kr/economy/policy/20251119/koreas-alternative-stock-exchange-faces-foreign-investor-complaints-over-15-trading-cap); [Seoul Economic Daily](https://en.sedaily.com/finance/2026/06/26/nextrade-drops-32-stocks-including-kakao-korean-air-from-q3) |
| QUANTGEN run 2026-09-27 | E8 KODEX/TIGER pairs; GLD/IAU pairs | KODEX/TIGER: REVISE, half-life one session (bid-ask bounce), loses at 2x costs. GLD/IAU: Sharpe −2.28. | QUANTGEN's own evidence of the bounce trap. | [QUANTGEN context brief](file:///home/claude/research_notes/QUANTGEN%20technical%20and%20fundamental%20signals/00_QUANTGEN_context.md) |

---

## 5. Data-check requests (exact tests for the data lab)

The available datasets are the KRX marcap daily file (1995-2026, survivorship-free OHLCV plus market cap), SPY daily (1998-2021), VIX daily (1990-2026), Ken French monthly factors and Shiller monthly data. **No intraday data are available, so ORB, intraday momentum and VWAP tests are INSUFFICIENT DATA by construction.**

- **DC-E2-01: KRX overnight vs intraday split (Lou-Polk-Skouras on Korea).**
  - For every stock-day, compute r_night = O_t/C_{t−1} − 1 and r_day = C_t/O_t − 1. Drop days with corporate actions or base-price resets, or use adjusted prices if available.
  - Report value-weighted and equal-weighted means, t-statistics and Sharpe ratios by size quintile and by period. Breakpoints: before and after 15 Jun 2015 (limits 15%→30%), before and after the 2023 tick-table change, and before and after Mar 2025 (Nextrade).
  - Repeat for 12-1 momentum and 1-month reversal decile spreads, split into night and day components.
  - Question: does Korean momentum or reversal accrue overnight as in the US?
- **DC-E2-02: Net short-term reversal on KRX.**
  - Signals: 1-day, 5-day and 21-day reversal deciles. Universes: all stocks; top 200 by 20-day median trading value; KOSPI 200 proxy (top 200 by market cap).
  - Volume conditioning in both directions: volume/20-day average above 1.5 (prior design) and below 0.67.
  - Report gross returns, net at 35 bp per side and at 70 bp per side, one-sided monthly turnover, break-even per-side cost, and the effect of a buy/hold band (enter at decile 1, exit above decile 3).
  - Pass condition: net Sharpe > 0 at 70 bp per side in the liquid universe.
- **DC-E2-03: Bounce and auction-noise test.** Repeat DC-E2-02 with (a) a one-day skip (signal at close t, enter at close t+1) and (b) entry at open t+1. If returns fall by more than half with the skip, classify the effect as microstructure, not a tradable edge.
- **DC-E2-04: Limit-hit behaviour.**
  - Stocks closing at the upper or lower limit (±15% before 15 Jun 2015, ±30% after): measure the next-day open gap and close-to-close returns at 1, 5 and 20 days.
  - Treat entry at a locked close as unfillable and compare results with and without that constraint.
- **DC-E2-05: Round numbers and tick-band edges on KRX.**
  - Count how often daily highs, lows and closes land on round prices (multiples of 1,000, 5,000 and 10,000 KRW) vs neighbouring prices.
  - Measure next-day returns for closes one tick below vs one tick above a round number, the Bhattacharya-Holden-Jacobsen analogue.
  - Test for discontinuities at the tick-band boundaries (2,000; 5,000; 20,000; 50,000; 200,000; 500,000 KRW).
- **DC-E2-06: Tick-cost floor by price band.**
  - Using daily closes, compute each stock-day's tick-to-price ratio under the tick table in force on that date.
  - Report the cross-sectional distribution of half-tick cost, weighted by trading value, for top-200 names vs the rest.
  - Question: what share of KRX stocks has a one-tick round trip above 20 bp?
- **DC-E2-07: Gap fade vs gap continuation, daily.**
  - SPY 1998-2021 and KRX top 200: when |O_t/C_{t−1} − 1| exceeds 1% (and 2%), measure the sign and size of the open-to-close return.
  - Report gross results, net of 2 × 50 bp (US via KIS) or 2 × 35 bp (KRX), and by VIX tercile.
- **DC-E2-08: Stop gap-through slippage.**
  - For hypothetical long positions entered at close t with stops 5%, 7% and 10% below entry, find every day the next open is already below the stop.
  - Record the fill at the open, and no fill on lower-limit-locked days.
  - Report the distribution of slippage beyond the stop by size quintile and period. Compare with a naive "fill at stop" backtest.
- **DC-E2-09: VIX-conditioned reversal (Nagel test).** Split DC-E2-02's weekly reversal by the VIX at t−1 (terciles, and VIX above 30). Use VKOSPI if it is available; otherwise VIX. Report net results by state.
- **DC-E2-10: Close-source integrity.**
  - For a sample of 50 stocks over 20 days after Mar 2025, compare QUANTGEN's KIS-derived "close" with the KRX official close in the marcap data.
  - Flag any mismatch caused by Nextrade or after-market prints. Required before any Korean card runs after Mar 2025.
- **DC-E2-11: Close-pressure reversal proxy on KRX.**
  - Measure the reversal from close t to open t+1 conditional on the size of the |close t / close t−1 − 1| move and the share of the day's range made late. Use (C−L)/(H−L) as a crude proxy, since there are no intraday data.
  - Purpose: a rough check for closing-auction pressure.
- **DC-E2-12: Overnight-hold strategy, SPY, cost kill test.**
  - Compute the SPY close-to-open and open-to-close series (1998-2021) and their Sharpe ratios.
  - Show the net result of a buy-at-close, sell-at-open strategy at 0.5 bp, 5 bp and 50 bp per side.
  - Purpose: demonstrate in QUANTGEN's own framework that the night effect survives only at institutional costs.

---

## 6. Claims ledger

| ID | Claim (one sentence) | Evidence (numbers, market, period, IS/OOS, gross/net) | Source(s) with URL | Tier | Robustness | Failure cases | QUANTGEN implication |
|---|---|---|---|---|---|---|---|
| E2-C01 | The US market's first half-hour return predicts its last half-hour return. | SPY 1993-2013: R² 1.6% IS / 1.4% OOS; timing strategy 6.67%/yr, Sharpe 1.08 gross; 4.46%/yr after spread; FOMC-day R² 11%. | [Gao-Han-Li-Zhou JFE 2018](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf) | T1 | Replicated in 16 developed markets 2005-2017 and in futures 1974-2020; OOS R² positive; costs only via spread. | Weakened 2007-2018 in SPY/QQQ; APAC during COVID. | DROP: break-even ≈1.3 bp per side vs 50 bp (US) / 35 bp (KRX). |
| E2-C02 | Korean market intraday momentum is weak. | KOSEF 200 ETF, Apr 2008-Apr 2021: coefficient 2.06 (p 0.084); R² 1.9% IS / 0.9% OOS. | [Limkriangkrai et al. PBFJ 2023](https://researchmgt.monash.edu/ws/files/519509174/494419119_oa.pdf) | T1 | Single study; no costs. | COVID 2020 weakening across APAC. | DROP for Korea. |
| E2-C03 | Intraday momentum is driven by short-gamma hedging and leveraged-ETF flows, and reverses over the next days. | 60+ futures 1974-2020; stock-level short gamma raises momentum ~68%, gamma-theta range breaches ~91%. | [Baltussen et al. JFE 2021](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365); [Park-Zhao 2025](https://portal.northernfinanceassociation.org/viewp.php?n=2240183764) | T1 | Two independent datasets; mechanism-based. | Depends on dealer positioning, which changes over time. | CONTEXT: don't chase flow-driven closes; expect partial reversal. |
| E2-C04 | US stocks show a cross-sectional end-of-day reversal worth only a few bp. | 1993-2019: VW 3.45 bp/day (8.7%/yr), EW 4.45 bp/day, gross; stable over time. | [Baltussen-Da-Soebhag EFMA 2024](http://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2024-Lisbon/papers/EndofDayReversal_withnames.pdf) | T1 (WP) | Not yet peer-reviewed; gross only. | None reported in sample. | DROP: needs intraday execution at bp-level cost. |
| E2-C05 | Half-hour return periodicity is real but not profitable after spreads. | NYSE 2001-2005: 3.01 bp same half-hour next day, significant up to 40 days; not profitable net. | [Heston-Korajczyk-Sadka JF 2010](https://ar5iv.arxiv.org/html/1005.3535) | T1 | Authors' own cost test. | Net of spread. | DROP; CONTEXT (algorithmic flow periodicity). |
| E2-C06 | US momentum is earned overnight, while value, profitability, investment and size premia are earned intraday. | US 1993-2013 excluding microcaps: momentum 0.98%/month overnight (t 3.84) vs −0.02% intraday; ROE −0.95% overnight vs +1.42% intraday. | [Lou-Polk-Skouras JFE 2019](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf) | T1 | Nine international markets; persistence up to 60 months. | Not tradable directly (costs). | BUILD-design: fill momentum cards in the closing auction; test on KRX (DC-E2-01). |
| E2-C07 | The overnight drift in E-mini futures disappears after spreads, except a conditional buy-the-dip version. | ES 1998-2020: 2-3 a.m. ET 3.7% annualized (1.48 bp/day); Sharpe 1.1 gross → −0.5 net; conditional version 1.1 net. | [FRBNY SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf) | T1 | Long sample; costed by the authors. | Unconditional version fails net. | DROP (no 2 a.m. execution); CONTEXT: selloffs into the close revert overnight. |
| E2-C08 | Index-ETF returns concentrate overnight. | QQQQ 1999-2006: close-to-open +23.7%/yr vs open-to-close −23.3%/yr. | [Kelly-Clark JAM 2011](https://link.springer.com/article/10.1057/jam.2011.2) | T1 | Consistent with E2-C06 and E2-C07; Cliff-Cooper-Gulen numbers not retrieved. | Two trades per day; costs not analysed. | DROP as a strategy; CONTEXT for DC-E2-12. |
| E2-C09 | The QQQ 5-minute ORB's headline result does not survive realistic slippage. | Paper: 1,484% 2016-2023, 33% alpha net of commissions. Replication: break-even ~2.2¢/share; Sharpe 0.23 at 2¢; 76% of filtered P&L in 2022; bootstrap CI overlaps QQQ. | [Concretum](https://concretumgroup.com/can-day-trading-really-be-profitable/); [GitHub replication](https://github.com/giovannibrusco/zarattini-2023-orb-qqq) | T3 (practitioner) | Gross replicates; net does not. | 2017, 2020, early 2023 losses; concentrated in 2022. | DROP. |
| E2-C10 | ORB on "stocks in play" reports Sharpe 2.81 only under no-slippage, 4x-leverage assumptions. | US 2016-2023: top-20 Sharpe 2.81, 1,637%; full universe Sharpe 0.48; $0.0035/share commission, no slippage, stops at 10% ATR. | [SSRN 4729284](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284); [St. Gallen PDF](https://alexandria.unisg.ch/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/download) | T1-WP (practitioner co-authors) | Not independently replicated; top-20 selection is a design choice. | Stop slippage ignored. | DROP (needs real-time intraday execution). |
| E2-C11 | ORB's gross signal (~0.13R) is eaten by CFD spreads across five index markets. | NQ, SPX, Dow, DAX, FTSE CFDs, Jan 2015-Jun 2026: net NQ +0.002R, four markets negative. | [MQL5 blog](https://www.mql5.com/en/blogs/post/776235) | T3 | Transparent method; blog. | All five markets. | DROP. |
| E2-C12 | Price impact scales with the square root of order size relative to volume. | Impact ≈ Yσ√(Q/V), Y ~1, for Q/V from 10⁻⁴ to a few %; TSE 8 years: exponent 0.5 ± 0.1; 8m US institutional trades: linear-to-square-root crossover. | [Toth et al. 2011](https://arxiv.org/pdf/1105.1694); [Sato-Kanazawa 2025](https://arxiv.org/abs/2411.13965); [Bucci et al. 2019](https://arxiv.org/abs/1811.05230) | T1 | Many markets; universality test. | Linear for very small orders. | BUILD (cost model): impact term plus a 1% of ADV cap on every card. |
| E2-C13 | Institutional costs are far below academic estimates, yet short-term reversal still fails at reasonable size. | $1.7tn, 21 markets, 19 years: costs about 10x below prior estimates; ~$1tn, 19 markets, 1998-2011: reversal does not survive. | [FIM 2018](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3229719); [AQR anomalies WP](https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies) | T1/T2 | Live execution data; single manager. | Reversal at scale. | CONTEXT: retail costs (35-50 bp) are far above institutional, so never import gross academic results for high-turnover cards. |
| E2-C14 | Strategies with one-sided monthly turnover above ~50% rarely survive costs; one-month reversal turns strongly negative net. | US 1963-2012: reversal turnover 90.87%/month; gross 0.37%/month (t 1.71), net −1.28%/month (t −6.02); with buy/hold band −0.72%/month. | [Novy-Marx-Velikov RFS 2016](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf) | T1 | Long sample; effective-spread estimates. | Persistent net losses. | BUILD (gate rule): turnover ≤50%/month target plus break-even screen; Korean reversal goes to BACKLOG until DC-E2-02/03 pass. |
| E2-C15 | Reversal returns are pay for providing liquidity and peak when the VIX is high. | Reversal expected returns and Sharpe rose sharply in 2007-09; predictable with VIX. | [Nagel RFS 2012](https://www.nber.org/papers/w17653) | T1 | Widely cited; mechanism-based. | Spreads also widen in stress. | BACKLOG: VIX-conditioned weekly reversal (DC-E2-09); keep the 1.0x hold. |
| E2-C16 | Closing auctions are the deepest liquidity event of the US day and keep growing. | 3.1% (2010) → 7.5% (2018) of volume; ~9-9.44% of consolidated notional (2024); NYSE-listed 10.5-14.2% depending on source and measure; >34% on Russell day 2024; NYSE Q1 2026 605.5m shares/day, record 3.57bn on 20 Mar 2026. | [Bogousslavsky-Muravyev 2023](https://www.sciencedirect.com/science/article/abs/pii/S1386418123000502); [NYSE 2024](https://www.nyse.com/data-insights/nyse-closing-auction-price-discovery-opportunities-reach-new-highs); [BMLL](https://www.bmlltech.com/news/market-insight/into-the-close-unpacking-u-s-closing-auction-dynamics-and-the-impact-of-the-russell-reconstitution); [NYSE 2026](https://www.nyse.com/research/insights/behind-the-record-volumes-a-hidden-opportunity) | T1/T2 | Multiple sources; denominators differ. | Unfilled ~3.3%; worse in small caps. | BUILD (execution convention): closing-auction fill as default for daily-close cards. |
| E2-C17 | Closing prices carry transient auction pressure that reverses overnight. | US: average absolute deviation 8.1 bp; >63 bp in 1% of cases; almost complete overnight reversal. | [Bogousslavsky-Muravyev 2023](https://www.sciencedirect.com/science/article/abs/pii/S1386418123000502) | T1 | Peer-reviewed; US only. | KRX not studied. | BUILD (test rule): skip-day and t+1 fill variants for every reversal card (DC-E2-03, DC-E2-11). |
| E2-C18 | Support/resistance has an order-placement basis, but the measured effect on intraday trend interruptions is small. | FX Jan 1996-Mar 1998: published levels 60.8% vs arbitrary 56.2%; lasts ≥5 days; 70% of levels end in 0, 96% in 0 or 5. Stops cluster beyond round numbers, take-profits at them; stop cascades. | [Osler 2000](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf); [Osler SR 125 (JF 2003)](https://www.newyorkfed.org/research/staff_reports/sr125.html); [Osler SR 150 (JIMF 2005)](https://www.newyorkfed.org/research/staff_reports/sr150.html) | T1 | FX order data from one bank; not equities. | Effect varies by firm and currency. | CONTEXT: avoid round-number stop placement; no S/R entry card. |
| E2-C19 | US retail liquidity demanders systematically lose around round numbers. | >100m trades: over-buying one penny below and over-selling one penny above round numbers; losses close to $1bn/yr. | [Bhattacharya-Holden-Jacobsen 2012](https://ideas.repec.org/a/inm/ormnsc/v58y2012i2p413-431.html) | T1 | Large sample. | Pre-2024 US tick regime. | BACKLOG data-check on KRX (DC-E2-05); never simulate fills at round numbers on touch. |
| E2-C20 | Stop orders fill far from the stop in fast markets. | Stops become market orders. 6 May 2010: >20,000 trades >60% away. 24 Aug 2015: SPY open −5.2%, IVV −20%+, JPM −13.3% in 65 s. | [FINRA](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets); [SEC-CFTC 2010](https://www.sec.gov/news/studies/2010/marketevents-report.pdf); [SEC 2015](https://www.sec.gov/marketstructure/research/equity_market_volatility.pdf) | T1 | Official reports. | Repeated in 2010, 2015, 2024. | BUILD (fill rule): stops fill at the next available price; no fill while limit-locked (DC-E2-08). |
| E2-C21 | Fewer than 1% of day traders are reliably profitable after fees, and aggregate day trading loses every year. | Taiwan 1992-2006: bottom-ranked traders 11.5 bp/day gross → −28.9 net; net negative in all 15 years; >75% quit within 2 years. Taiwan 1995-1999: individuals lose 3.8 points/yr, mainly via taxes (34%) and commissions (32%). | [Barber et al. JFM 2014](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/The%20Cross-Section%20of%20Speculator%20Skill.pdf); [learning paper](https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf); [RFS 2009](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/JustHowMuchDoIndividualInvestorsLose_RFS_2009.pdf) | T1 | Complete population data. | Every year 1992-2006. | CONTEXT: base rate; no intraday-trading UI nudges. |
| E2-C22 | Day trading for a living is virtually impossible in Brazil. | Index futures 2013-2015: 97% of 300+ day persisters lost; 1.1% earned above minimum wage. | [Chague et al.](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101) | T1 (WP) | Complete population. | Entire sample. | CONTEXT. |
| E2-C23 | Korea's 2020 retail boom showed very high turnover, mostly intraday trading, and negative net returns for new investors. | 204,004 accounts, Mar-Oct 2020: new investors net −1.2% vs existing +15.0%; 55.4% of trading intraday; costs −4.0 points; turnover ~1,600%/yr; 46% of all investors lost. | [KCMI 21-11](https://www.kcmi.re.kr/report/report_view?report_no=1243); [KCMI 2022](https://www.kcmi.re.kr/report/report_view?report_no=1481); [Financial News](https://www.fnnews.com/news/202104131912345956) | T1/T2 | Four large brokers, eight months. | Bull market 2020. | CONTEXT: QUANTGEN's audience base rate argues against intraday features. |
| E2-C24 | Robinhood-era retail evidence is mixed, and retail execution costs vary widely. | Herding stocks −4.7% 20-day abnormal return; crowd portfolio did well 2018-2020; round-trip execution −0.07% to −0.46% excluding commissions. | [Barber et al. JF 2022](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3715077); [Welch JF 2022](https://www.nber.org/papers/w27866); [Schwarz et al. 2022](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4189239) | T1 | Conflicting findings across samples. | Jan 2021 GME. | CONTEXT: 50 bp per side for US via KIS is a plausible conservative stress. |
| E2-C25 | KRX VI, limit and auction rules interrupt intraday technical mechanics. | Dynamic VI 3%/6% (2%/4% in the closing auction), static 10%, 2-minute call; ±30% limit since 15 Jun 2015; closing call 15:20-15:30 with random end ≤30 s; overheating triggers a 3-day periodic call. | [KRX VI](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T9.jsp); [limits](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T5.jsp); [call auction](https://global.krx.co.kr/contents/GLB/06/0602/0602010202/GLB0602010202T1.jsp); [overheat](https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T8.jsp) | T1 | Official rules. | Limit locks; VI during the close. | BUILD (data hygiene): unfillable-day flags; regime flags at 2015. |
| E2-C26 | KRX's coarse ticks plus the 0.20% sell tax set a round-trip floor of about 25-45 bp before commission and impact. | Ticks 0.05-0.25% of price by band; tax 0.18% (2024), 0.15% (2025), 0.20% (2026); 0.25% assumed for 2020. | [KRX ticks](https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp); [PwC](https://taxsummaries.pwc.com/republic-of-korea/corporate/other-taxes); [EY](https://taxnews.ey.com/news/2026-0126-korea-enacts-2026-tax-reform-bill) | T1/T2 | Official schedule; floor is my arithmetic. | Small caps with multi-tick spreads cost more. | BUILD (cost model): tick-band spread floor; 35 bp per side adequate for liquid names only (DC-E2-06). |
| E2-C27 | Nextrade extends Korean trading to 12 hours with cheaper fees, but its stock list and share are unstable. | Launched Mar 2025; sessions 08:00-08:50 / 09:00:30-15:20 / 15:40-20:00; fees 20-40% lower; 15% cap; stocks 800→630 (2025)→610 (Q3 2026); value ratio vs KRX 26.9%→49.4%→~21%; share 10.64%→9.10% after KRX after-hours launch. | [Nextrade](https://www.nextrade.co.kr/); [overview](https://www.nextrade.co.kr/marketOverview/content.do); [Korea Times](https://www.koreatimes.co.kr/economy/policy/20251119/koreas-alternative-stock-exchange-faces-foreign-investor-complaints-over-15-trading-cap); [Seoul Economic Daily](https://en.sedaily.com/finance/2026/06/26/nextrade-drops-32-stocks-including-kakao-korean-air-from-q3); [Archynewsy (T3)](https://www.archynewsy.com/nextrade-market-share-falls-after-korea-exchange-opens-after-hours-market/) | T1/T2/T3 | Fast-changing; one source has a date inconsistency. | Four suspension rounds in 2025. | BUILD (data hygiene): KRX official close only; verify the KIS close source (DC-E2-10). |
| E2-C28 | The US half-penny tick (Nov 2025) lowers spread costs for tick-constrained names but doesn't change retail broker costs. | SEC 18 Sep 2024: $0.005 tick for qualifying stocks ≥$1; access fee cap $0.001; compliance Nov 2025. | [SEC 2024-137](https://www.sec.gov/newsroom/press-releases/2024-137) | T1 | Official. | Not yet studied empirically. | CONTEXT: regime flag for US cards after Nov 2025. |
| E2-C29 | Classic US intraday predictors may have decayed after publication. | SPY/QQQ 2007-2018: intraday momentum and overnight effects diminished; conflicts with futures evidence through 2020. | [Zhang-Hua 2024](https://www.mdpi.com/2227-9091/12/11/180); [Baltussen et al. 2021](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365) | T1 (lower-tier journal) | Conflicting results. | 2007-2018 weakening. | CONTEXT: apply the 60% haircut; another reason to drop. |
| E2-C30 | Every short-horizon card should report a break-even per-side cost and be rejected before the gate if it is below 2x the pre-registered cost. | Break-even = gross annual return / (2 × annual turnover). Examples: SPY intraday momentum ≈1.3 bp, overnight drift ≈0.7 bp, QQQ ORB ≈0.5-2 bp, against 35-50 bp. | E2 inference from [Novy-Marx-Velikov](https://www.nber.org/system/files/working_papers/w20721/w20721.pdf), [Gao et al.](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf), [FRBNY SR 917](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf) | Inference | Arithmetic on cited numbers. | n/a | BUILD (card header field plus pre-gate screen). |

---

## 7. Source list

**Intraday patterns and overnight returns**
- Gao, Han, Li, Zhou (2018), Market Intraday Momentum, JFE — https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf
- Li, Sakkas, Urquhart, Intraday Time Series Momentum: International Evidence (FoFI 2020) — http://wp.lancs.ac.uk/fofi2020/files/2020/04/FoFI-2020-092-Zeming-Li.pdf
- Limkriangkrai, Chai, Zheng (2023), Market Intraday Momentum: APAC Evidence, PBFJ 80 — https://researchmgt.monash.edu/ws/files/519509174/494419119_oa.pdf
- Baltussen, Da, Lammers, Martens (2021), Hedging Demand and Market Intraday Momentum, JFE — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3760365
- Park, Zhao (2025), Inelastic Hedging Demand and Intraday Momentum — https://portal.northernfinanceassociation.org/viewp.php?n=2240183764
- Zhang, Hua (2024), Market Predictability Before the Closing Bell Rings, Risks — https://www.mdpi.com/2227-9091/12/11/180
- Baltussen, Da, Soebhag, End-of-Day Reversal (EFMA 2024) — http://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2024-Lisbon/papers/EndofDayReversal_withnames.pdf
- Heston, Korajczyk, Sadka (2010), Intraday Patterns in the Cross-section of Stock Returns, JF — https://ar5iv.arxiv.org/html/1005.3535
- Lou, Polk, Skouras (2019), A Tug of War, JFE — https://personal.lse.ac.uk/polk/research/TugOfWar.pdf
- Boyarchenko, Larsen, Whelan, The Overnight Drift, FRBNY SR 917 — https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf ; https://www.newyorkfed.org/research/staff_reports/sr917
- Kelly, Clark (2011), Returns in trading versus non-trading hours, JAM — https://link.springer.com/article/10.1057/jam.2011.2
- Cliff, Cooper, Gulen, Like Night and Day (title and award only) — https://www.huseyingulen.com/ ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1004081

**Opening-range breakout and practitioner intraday strategies**
- Zarattini, Aziz (2023), Can Day Trading Really Be Profitable? — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622 ; https://concretumgroup.com/can-day-trading-really-be-profitable/
- Zarattini, Barbon, Aziz (2024), A Profitable Day Trading Strategy for the U.S. Equity Market — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284 ; https://alexandria.unisg.ch/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/download
- Zarattini, Aziz, Barbon (2024), Beat the Market: Intraday Momentum for SPY — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172
- ORB QQQ replication (GitHub) — https://github.com/giovannibrusco/zarattini-2023-orb-qqq
- ORB five-index CFD replication (MQL5 blog, 25 Sep 2026) — https://www.mql5.com/en/blogs/post/776235

**Market impact and trading costs**
- Toth et al. (2011), Anomalous price impact, PRX — https://arxiv.org/abs/1105.1694 ; https://arxiv.org/pdf/1105.1694
- Sato, Kanazawa (2025), Strict universality of the square-root law, PRL — https://arxiv.org/abs/2411.13965
- Bucci, Benzaquen, Lillo, Bouchaud (2019), Crossover from linear to square-root impact, PRL — https://arxiv.org/abs/1811.05230
- Almgren, Chriss (2001), Optimal Execution of Portfolio Transactions, J. Risk (hosted copy) — https://www.smallake.kr/wp-content/uploads/2016/03/optliq.pdf
- Frazzini, Israel, Moskowitz (2018), Trading Costs — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3229719 ; https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs
- Frazzini, Israel, Moskowitz, Trading Costs of Asset Pricing Anomalies — https://www.aqr.com/Insights/Research/Working-Paper/Trading-Costs-of-Asset-Pricing-Anomalies
- Novy-Marx, Velikov (2016), A Taxonomy of Anomalies and their Trading Costs, RFS — https://www.nber.org/papers/w20721 ; https://www.nber.org/system/files/working_papers/w20721/w20721.pdf
- Nagel (2012), Evaporating Liquidity, RFS — https://www.nber.org/papers/w17653
- Busseti, Boyd (2015), VWAP Optimal Execution — https://arxiv.org/abs/1509.08503

**Closing auctions and NYSE market model**
- Bogousslavsky, Muravyev (2023), Who trades at the close?, JFM — https://www.sciencedirect.com/science/article/abs/pii/S1386418123000502
- NYSE (Aug 2024), Closing auction price discovery reaches new highs — https://www.nyse.com/data-insights/nyse-closing-auction-price-discovery-opportunities-reach-new-highs
- NYSE (Nov 2025), Closing auction timing shifts — https://www.nyse.com/research/insights/nyse-closing-auction-timing-shifts-and-marketability-trends
- NYSE (Apr 2026), Behind the Record Volumes — https://www.nyse.com/research/insights/behind-the-record-volumes-a-hidden-opportunity
- NYSE Closing Auction insider's guide (schedule) — https://www.nyse.com/article/nyse-closing-auction-insiders-guide
- NYSE market model (DMMs) — https://www.nyse.com/market-model
- BMLL (Jun 2025), Into the Close — https://www.bmlltech.com/news/market-insight/into-the-close-unpacking-u-s-closing-auction-dynamics-and-the-impact-of-the-russell-reconstitution
- Tethys (Dec 2024), Auction Volume Report: Americas — https://www.tethystech.com/wp-content/uploads/2024/12/Auction-Volume-Report-Americas.pdf

**Support/resistance, round numbers and stop orders**
- Osler (2000), Support for Resistance, FRBNY EPR — https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf
- Osler, Currency Orders and Exchange-Rate Dynamics, SR 125 (JF 2003) — https://www.newyorkfed.org/research/staff_reports/sr125.html
- Osler, Stop-Loss Orders and Price Cascades, SR 150 (JIMF 2005) — https://www.newyorkfed.org/research/staff_reports/sr150.html
- Bhattacharya, Holden, Jacobsen (2012), Penny Wise, Dollar Foolish, Management Science — https://ideas.repec.org/a/inm/ormnsc/v58y2012i2p413-431.html
- FINRA, Stop orders in volatile markets — https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets
- SEC Investor.gov, Stop order — https://www.investor.gov/introduction-investing/investing-basics/glossary/stop-order

**US regulators and stress episodes**
- SEC (2024), Reg NMS tick/access fee amendments — https://www.sec.gov/newsroom/press-releases/2024-137
- SEC-CFTC (2010), Findings regarding the market events of May 6, 2010 — https://www.sec.gov/news/studies/2010/marketevents-report.pdf
- SEC staff, Equity market volatility on August 24, 2015 — https://www.sec.gov/marketstructure/research/equity_market_volatility.pdf
- SEC staff (2021), Equity and options market structure conditions in early 2021 — https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf
- BIS Bulletin 90 (Aug 2024) — https://www.bis.org/publ/bisbull90.pdf ; https://www.bis.org/publ/bisbull90.htm
- BIS Quarterly Review (Sep 2024), Carry off, carry on — https://www.bis.org/publ/qtrpdf/r_qt2409a.htm

**Retail trader outcomes**
- Barber, Lee, Liu, Odean (2014), The Cross-Section of Speculator Skill, JFM — https://faculty.haas.berkeley.edu/odean/papers/day%20traders/The%20Cross-Section%20of%20Speculator%20Skill.pdf
- Barber, Lee, Liu, Odean, Day trading and learning (Taiwan) — https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trading%20and%20Learning%20110217.pdf
- Barber, Lee, Liu, Odean (2009), Just How Much Do Individual Investors Lose by Trading?, RFS — https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/JustHowMuchDoIndividualInvestorsLose_RFS_2009.pdf ; https://academic.oup.com/rfs/article-abstract/22/2/609/1595677
- Chague, De Losso, Giovannetti, Day Trading for a Living? — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101
- Barber, Huang, Odean, Schwarz (2022), Attention-Induced Trading and Returns, JF — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3715077
- Welch (2022), The Wisdom of the Robinhood Crowd, JF — https://www.nber.org/papers/w27866
- Schwarz, Barber, Huang, Jorion, Odean (2022), The 'Actual Retail Price' of Equity Trades — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4189239
- Choe, Kho, Stulz (2005), Do domestic investors have an edge? (Korea), RFS — https://www.nber.org/papers/w8073

**Korea: retail studies, KRX rules, tax and Nextrade**
- KCMI (Kim and Kim 2021), 코로나19 국면의 개인투자자 — https://www.kcmi.re.kr/report/report_view?report_no=1243
- KCMI (Kim and Kim 2022), 국내 개인투자자의 행태적 편의와 거래행태 — https://www.kcmi.re.kr/report/report_view?report_no=1481
- KCMI (Kang and Kim 2026), 개인투자자의 해외투자 특징 및 성과 분석 — https://www.kcmi.re.kr/report/report_view?report_no=2254
- Financial News (14 Apr 2021) on the KCMI webinar — https://www.fnnews.com/news/202104131912345956
- KRX trading hours — https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T1.jsp
- KRX order types (LOC→MOC at 15:20) — https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T2.jsp
- KRX tick sizes — https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T3.jsp
- KRX daily price limits — https://global.krx.co.kr/contents/GLB/06/0602/0602010201/GLB0602010201T5.jsp
- KRX call auction / random end — https://global.krx.co.kr/contents/GLB/06/0602/0602010202/GLB0602010202T1.jsp
- KRX off-hours and after-market — https://global.krx.co.kr/contents/GLB/06/0602/0602010203/GLB0602010203T1.jsp
- KRX circuit breakers — https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T2.jsp
- KRX sidecar — https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T4.jsp
- KRX quotation publication (opening auction 08:30-09:00, indicative price from 08:40) — https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T6.jsp
- KRX overheating measures — https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T8.jsp
- KRX volatility interruption — https://global.krx.co.kr/contents/GLB/06/0602/0602010204/GLB0602010204T9.jsp
- PwC Korea other taxes (securities transaction tax) — https://taxsummaries.pwc.com/republic-of-korea/corporate/other-taxes
- EY (Jan 2026), Korea enacts 2026 tax reform bill — https://taxnews.ey.com/news/2026-0126-korea-enacts-2026-tax-reform-bill
- Nextrade home (sessions, stock count) — https://www.nextrade.co.kr/
- Nextrade market overview — https://www.nextrade.co.kr/marketOverview/content.do
- Nextrade fee guide — https://www.nextrade.co.kr/html/charge-info.html
- Korea Times (19 Nov 2025), Nextrade 15% cap complaints — https://www.koreatimes.co.kr/economy/policy/20251119/koreas-alternative-stock-exchange-faces-foreign-investor-complaints-over-15-trading-cap
- Seoul Economic Daily (Dec 2025/Jan 2026), Nextrade share shrinks as KRX cuts fees — https://en.sedaily.com/finance/2025/12/21/nextrade-market-share-shrinks-as-korea-exchange-cuts-fees
- Seoul Economic Daily (26 Jun 2026), Nextrade drops 32 stocks — https://en.sedaily.com/finance/2026/06/26/nextrade-drops-32-stocks-including-kakao-korean-air-from-q3
- Archynewsy (27 Sep 2026; T3 aggregator) — https://www.archynewsy.com/nextrade-market-share-falls-after-korea-exchange-opens-after-hours-market/

**Project-internal**
- QUANTGEN context brief (costs, gate, 2026-09-27 record) — /home/claude/research_notes/QUANTGEN technical and fundamental signals/00_QUANTGEN_context.md
