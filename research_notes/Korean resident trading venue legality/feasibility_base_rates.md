# Feasibility and empirical base rates: USD 30 (about KRW 42,000) to USD 30,000 in about one month, for a South Korean resident

Research date: 2026-10-22/23. Scope: the math of a 1000x target, empirical outcome base rates for convex retail instruments, and which venues a Korean-resident individual can legally reach with about KRW 42,000. This is a description of what laws, regulators and platform terms say, not legal advice. Several items (Polymarket block Aug 2026, FIU website blocks Oct 2026, single-stock leveraged mock-trading rule Aug 2026, Kalshi Member Agreement rev. 1 Oct 2026, pump.fun BOOST Jul 2026) postdate mid-2026 and were confirmed only through news or secondary reporting, not primary text; treat them as **uncertain / may change**.

## Q1. Required growth, number of doublings, and probability bounds (Dubins-Savage, Kelly, risk of ruin)

### Takeaway
1000x needs about 10 doublings: about +39% per KRX session over 21 sessions, or about +26% per calendar day over 30 days for 24/7 crypto. Without a genuine positive edge after costs, no betting strategy can reach the target with probability above 0.1%. The best strategy in a subfair game (bold play) gets close to that ceiling only when costs are near zero; with realistic retail costs the probability falls to the 0.01-0.08% range.

### Cited Findings
- In subfair red-and-black (win probability w < 1/2), Dubins and Savage showed **bold play** (stake min{f, 1-f} of the distance to the goal) maximizes the probability of eventually reaching the goal. Other optimal strategies also exist. Bold play is **not** always optimal once house limits (irrational or non-integer 1/δ), inflation or discounting are added. — [Chen et al., arXiv math/0412362](https://arxiv.org/pdf/math/0412362); [NCCU paper on non-optimality with rational house limit](https://ah.lib.nccu.edu.tw/bitstream/140.119/47289/1/10241038.pdf)
- Yao (2007): bold play stays optimal with limited playing time and discounting when w ≤ 1/2 ≤ r, and that condition is necessary under limited playing time. This is relevant because a one-month deadline is a limited playing time. — [Cambridge J. Appl. Prob. abstract](https://resolve-he.cambridge.org/core/journals/journal-of-applied-probability/article/on-optimality-of-bold-play-for-discounted-dubinssavage-gambling-problems-with-limited-playing-times/8D10E45237E7A79E7B018D2280EA3B6A)

### Inferences
(All arithmetic below is my own calculation. It is not from a source.)
- **Required rate:** 1000^(1/21) = 1.3895, so +38.9% compounded per trading session over 21 KRX sessions. 1000^(1/30) = 1.2589, so +25.9% per day over 30 calendar days. log2(1000) = 9.97, so about **10 doublings** (2^10 = 1024).
- **Hard ceiling (optional-stopping / Markov bound):** if every bet has expected value ≤ 0 after fees, wealth is a non-negative supermartingale. Then P(final wealth ≥ 1000 × start) ≤ start / target = **1/1000 = 0.1%**. This holds for every strategy (martingale, pyramiding, leverage, options) unless the trader has a real positive edge. Costs and negative EV push the ceiling lower.
- **Bold play with even-money bets** (10 straight doublings), probability = p^10:
  - p = 0.49 gives 0.080%
  - p = 0.45 gives 0.034%
  - p = 0.40 gives 0.0105%
  - Even with a real +5% edge (p = 0.525), it gives only 0.16%.
- **One-shot lottery ticket:** take a 1000:1 longshot whose average return is the Kalshi taker average of -32% (Q2). The hit probability is about 0.68/1000 = **0.068%**. Longshots carry the worst bias (favorite-longshot), so the real figure is likely lower.
- **Kelly vs. target-hitting:** with zero or negative edge the Kelly fraction is 0, so Kelly says do not bet at all. Take a real edge of p = 0.525 on even-money bets. Full Kelly f = 0.05 gives expected log-growth of about 0.00125 per bet, so reaching ln(1000) = 6.91 takes about **5,500 bets**. Kelly maximizes long-run growth and minimizes ruin. It does not maximize P(hit 1000x by a deadline), which needs near-bold play and therefore accepts ruin probability above 99.8%.
- **Risk of ruin:** under bold play the probability of losing everything is 1 - P(success), which is above 99.9% for every realistic p in this list.
- **Fixed costs at small size:** at KRW 42,000 (about $30), fixed per-contract commissions dominate. A $2.18 per-side promotional overseas-futures commission (see Q3) costs about 7% of the account per side, or about 14% per round trip. That is a large negative edge before any market move.

### Gaps
- I did not fetch the original Dubins and Savage (1965) monograph text. The optimality claims rest on the follow-up papers above.
- No source was found that computes P(1000x in 30 days) empirically for any retail population.

## Q2. Empirical base rates (lottery options/0DTE, meme coins, leveraged derivatives/perps, prediction markets, Korean retail)

### Takeaway
Every retail population with convex, lottery-like payoffs shows negative average returns and loss rates of 74-97%. Retail buyers of short-dated or high-skew options pay a premium. Kalshi takers lose about 32% on average. About 1-1.5% of pump.fun tokens ever "graduate". Korean individuals lost an average of about KRW 458 billion per year on overseas derivatives from 2020 to H1 2025.

### Cited Findings
**Lottery-like options**
- Boyer and Vorkink, "Stock Options as Lotteries," *Journal of Finance* 69(4), 2014, pp. 1485-1527. They find a strong negative relation between ex-ante total skewness and individual equity option returns. Skewness-sorted option portfolios differ by **10% to 50% in average weekly returns**, even after risk adjustment. The authors read this as a premium paid to intermediaries for supplying lottery-like options. — [IDEAS/RePEc](https://ideas.repec.org/a/bla/jfinan/v69y2014i4p1485-1527.html); sample about 1996-2009, effect strongest near expiration (per working-paper summary, not verified against the published paper) — [CXO Advisory](https://www.cxoadvisory.com/?p=13232)

**0DTE options**
- Beckmeyer, Branger and Gayda, "Retail Traders Love 0DTE Options… But Should They?" (2023):
  - About **75% of retail S&P 500 option trades were 0DTE**.
  - Average retail loss was about **$184k per day** over the sample, rising to **$358k per day** after daily expirations began on 16 May 2022.
  - Total retail losses were above $70M from Jan 2021 to Feb 2023.
  - Long positions lost money and short positions were profitable after fees. About 60% of losses came from transaction costs.
  — [CXO Advisory summary](https://www.cxoadvisory.com/individual-investing/retail-0dte-option-trader-performance); [BNN Bloomberg](https://www.bnnbloomberg.ca/day-traders-lose-358-000-per-day-gambling-on-zero-day-options-1.1910634). Conflicting aggregate: a Neudata review cites $125M total and about $350k per day — [Neudata](https://neudata.co/literature-reviews/zero-day-to-expiry-options-a-losing-bet-for-retail-traders)

**Prediction markets (Kalshi)**
- Bürgi, Deng and Whelan, "Makers and Takers: The Economics of the Kalshi Prediction Market":
  - **Takers lose about 32% on average and makers about 10%.** The average pre-fee contract return is about **-20%**.
  - There is a clear favorite-longshot bias, stronger for takers. The authors attribute it to taker over-optimism and a winner's-curse effect.
  - The authors conclude prices are not unbiased probabilities.
  — [CEPR/VoxEU column](https://cepr.org/voxeu/columns/economics-kalshi-prediction-market); [UCD WP2025/19](https://www.ucd.ie/economics/t4media/WP2025_19.pdf); [CEPR DP20631, Jan 2026](https://cepr.org/publications/dp20631). I did not confirm that the figures are identical across paper versions.

**Meme coins (pump.fun)**
- pump.fun graduation rate (share of launched tokens that reach the bonding-curve threshold and migrate) has historically been about **1.4%** per Dune data. Example: one early-2025 month had 1.7M tokens launched and about 24k graduated. — [Solana Compass](https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex); [The Defiant](https://thedefiant.io/news/defi/pump-fun-token-graduation-rate-plummets)
- The rate spiked to **6.7%** in one week of July 2026 (about 8x June's average), coinciding with the "BOOST" launch mechanism. The Block notes BOOST takes effect after bonding, so the spike may not be durable. **Single-week figure, post-mid-2026, treat as uncertain.** — [The Block, 29 Jul 2026](https://theblock.co/post/409815/pump-fun-token-graduation-rate-jumps-boost-changes-launch-incentives)
- Per Dune dashboards, only about **3% of pump.fun users have ever realized more than $1,000** in profit. — [Unchained](https://unchainedcrypto.com/most-users-keep-losing-money-on-pump-fun-despite-the-protocols-record-profits/) (opinion-led article citing Dune)
- The top tracked trader realized above $41M, and **151 wallets** profited above $1M. The dashboard only counts pre-graduation buys. — [Decrypt](https://decrypt.co/331108/business-memes-inside-solana-meme-coin-pump-fun?amp=1)

**Leveraged CFDs and derivatives (proxy for perpetual futures)**
- EU national regulators found **74-89% of retail CFD accounts lose money**, with average losses of €1,600-€29,000 per client. ESMA's 2018 measures capped retail leverage at 30:1 (major FX) down to **2:1 for crypto**, added negative-balance protection and banned binary options for retail. — [ESMA press release, 23 Mar 2018](https://www.esma.europa.eu/node/84933) (I did not confirm the current status of these limits.)
- India's SEBI reported that nearly **9 in 10 retail equity-derivatives traders lost money in FY26**. — [FOW](https://www.fow.com/insights/nearly-9-out-of-10-retail-equity-derivatives-traders-lose-money-in-fy26-sebi)

**Day trading**
- Chague, De-Losso and Giovannetti studied Brazilian equity-futures day traders (2013-2015) who persisted at least 300 days:
  - **97% lost money**.
  - Only about 0.4-0.5% earned more than a bank teller's starting salary.
  - The best individual earned about US$310 per day.
  - They found no evidence of learning.
  — [FGV repository](https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full); [IDEAS](https://ideas.repec.org/p/fgv/eesptd/525.html)

**Korean retail**
- A KCMI (자본시장연구원) analysis of about 200,000 individual accounts (Mar-Oct 2020) found **about 46% lost money**. Loss rates were **62% for new investors vs. 39% for existing investors**. Frequent trading was linked to poor performance. — [Financial News, 13 Apr 2021](https://www.fnnews.com/news/202104131912345956); [한국교육신문 column](https://www.hangyo.com/mobile/article.html?no=94115)
- FSS (금감원): Korean individuals lost an average of about **KRW 458 billion per year on overseas derivatives from 2020 to H1 2025**, every year regardless of market conditions. A later FSS release reported **KRW 373.5 billion of losses in Jan-Oct** of the reporting year (likely 2025; year not verified). The same release said 49.3% of overseas-stock accounts were in loss. — [데일리안 1588198](https://www.dailian.co.kr/news/view/1588198/); [데일리안 1502047](https://www.dailian.co.kr/news/view/1502047/)

### Inferences
- Across five very different venues (US 0DTE, Kalshi, EU CFDs, Indian F&O, Brazilian futures) and two Korean datasets, the median retail outcome on convex or leveraged products is a loss. For each population the realized frequency of large gains is far below what payoff structures imply. This fits the Q1 supermartingale bound.
- The Kalshi maker/taker gap (about -10% vs. -32%) and the 0DTE buyer/seller asymmetry point the same way. Edge, where it exists, accrues to liquidity *providers* and option *sellers*. Those are the opposite of the convex, long-lottery positions a 1000x goal requires.

### Gaps
- **Bali & Murray** (risk-neutral skewness and option portfolio returns): not retrieved in this pass. I cannot cite figures.
- **Perpetual-futures liquidation rates** (Binance, Bybit, Hyperliquid wallet-level studies): no peer-reviewed or exchange-published retail liquidation share was found. The CFD and SEBI figures above are the closest proxies.
- **KCMI day-trader-specific loss rates** (e.g., 김준석 et al.): the original report was not located. Only the 2020 all-investor 46% figure is confirmed via press.
- **FSS overseas-futures loss-account share** (percent of accounts losing, as opposed to KRW totals): not found.

## Q3. Which instruments are legal and reachable for a Korean resident with about KRW 42,000, how convex they are, and a defensible probability of 1000x

### Takeaway
The instruments that are both clearly legal and reachable with KRW 42,000 are low-convexity:
- KRX cash stocks, capped at a theoretical 247x even with 21 straight limit-ups.
- Domestic spot crypto, with no leverage beyond collateral.
- Overseas leveraged ETPs, after 1 hour of mandatory education.

The high-convexity venues are either gated by deposit requirements (KRX derivatives and domestic leveraged ETFs at KRW 10M, if the 2019/2020 rules still apply), conditionally open (overseas options after 1 hour of education and 3 hours of mock trading), or illegal / blocked (Polymarket, unregistered offshore perpetual exchanges). Defensible P(1000x in a month) is **below 0.1% for every lawful, reachable path**, and for most it is effectively zero.

### Cited Findings
**KRX equities and domestic leveraged ETFs**
- **KRX cash equities:** since **15 Jun 2015** the daily price limit for KOSPI/KOSDAQ shares, DRs, ETFs, ETNs and beneficiary certificates is **±30%** (KONEX ±15%). Static VI (2-minute cooling-off on a 10% move) and staged circuit breakers (CB1 at 8%) were added. — [이투데이, 2015](https://www.etoday.co.kr/news/view/1127429)
- **Domestic leveraged ETF/ETN (KRX 2x):** under the 2020 FSC measure, retail accounts needed **KRW 10M or more in deposit (기본예탁금) plus online pre-education** (금융투자교육원). — [미래에셋 blog, Sep 2020](https://securities.miraeasset.com/public/mw/blog/html/20200916195431.html). **Whether the KRW 10M deposit still applies in Oct 2026 was not confirmed.**
- **New KRX single-stock leveraged products (Aug 2026):** mandatory mock trading of at least 1 hour per day for 5 trading days plus a completion check. A new investor starting on the 19th could trade from the 24th at the earliest. — [비즈워치, 12 Aug 2026](https://news.bizwatch.co.kr/article/market/2026/08/12/0036); [이코노미스트](https://economist.co.kr/article/view/ecn202608120061) (post-mid-2026, uncertain)

**KRX futures and options**
- **KRX futures/options (e.g., KOSPI200 options):** the 2019 FSC derivatives-market reform described the then-current entry rules as basic deposit + 20+ hours pre-education + 50+ hours mock trading. It changed them to: deposit **abolished for individual professional investors**, for general investors set by the broker **at KRW 10M or more**, plus **1 hour pre-education and 3 hours mock trading**. — [2019년 파생상품시장 발전방안 (FSC, via smallake)](https://www.smallake.kr/wp-content/uploads/2019/06/2019년-파생상품시장-발전방안.pdf). The exact current statute or KRX 시행세칙 article was not retrieved.

**Overseas exchange-traded derivatives (CME etc. via a Korean broker)**
- **Entry rules:** from **15 Dec 2025**, first-time individual traders of overseas derivatives must complete **at least 1 hour of pre-education and 3 hours of mock trading**. Overseas leveraged ETPs need **1 hour of pre-education only**, with no mock trading, because losses cannot exceed principal. — [경북매일, 15 Dec 2025](https://kbmaeil.com/article/20251215500253); [데일리안](https://www.dailian.co.kr/news/view/1502047/); broker rule text (1-hour minimum education, 3-hour minimum overseas mock trading) — [한국투자증권](https://www.truefriend.com/main/bond/foreign/_static/TF10da000000.jsp)
- **Deposit:** earlier reporting (2020 National Assembly audit) said overseas derivatives had **no basic-deposit, education or mock-trading duty**, only exchange margin. Education and mock trading were added in Dec 2025. — [딜사이트](https://dealsite.co.kr/articles/65983)
- **Margin and fees:** **micro futures** need about 1/10 the margin of standard contracts. Initial margin per micro contract ranged **$110-$2,310** at the time of reporting. The Kiwoom mock-trading note says positions are liquidated (not topped up) on margin shortfall under daily settlement. — [아시아경제, Aug 2025](https://core.asiae.co.kr/article/2025080409044440846); [키움 모의투자 안내](https://www.kiwoom.com/m/mock/ordinary/VFofuopMockInfoView)
- **Example promotional commission:** Mirae's "$2.18" per-contract overseas futures/options campaign. — [딜사이트](https://dealsite.co.kr/articles/49399)

**Domestic crypto (FIU-registered exchanges)**
- **Spot trading fees:** Upbit KRW-market spot fee is commonly cited as **0.05%**. — [brunch](https://brunch.co.kr/@zeroonedollar/59); [이코노미스트, 2022](https://economist.co.kr/article/view/ecn202205030079) (secondary). **The minimum order size (often cited as KRW 5,000) was not confirmed in this pass.**
- **Lending guideline (FSC, 5 Sep 2025):**
  - Restricts **"leverage" lending exceeding collateral value** and KRW-denominated (금전성) lending.
  - Bans indirect lending via third parties.
  - Requires DAXA education plus a suitability test for new users, with tiered limits.
  - Caps fees at **20% per year**.
  - Limits lendable assets to the **top-20 by market cap**.
  - Bithumb's earlier **up to 4x** lending product was sanctioned. Upbit resumed with a lower collateral cap (KRW 50M to 37.5M).
  - The guideline is administrative guidance ahead of legislation.
  — [한국경제, 5 Sep 2025](https://www.hankyung.com/article/202509055461i); [TF미디어](https://www.tfmedia.co.kr/mobile/article.html?no=194988); [KB Think](https://kbthink.com/crypto/crypto-lending.html)

**Unregistered offshore crypto exchanges (where 50-125x perpetual futures live)**
- **Website blocks (Oct 2026):** on **13 Oct 2026**, the FIU (금융정보분석원), after KCSC review, announced a domestic **website-access block on 27 unregistered VASPs including KuCoin, MEXC and BingX**. This followed earlier app-store install/update blocks (Google Play restrictions from 28 Jan [2025]).
  - Blocks can now be imposed once unregistered business is confirmed, without waiting for user harm or a court ruling.
  - The FIU warned that existing users' withdrawals may be restricted after a block.
  - Unregistered operation carries **up to 5 years' imprisonment or KRW 50M fine**.
  - **Referrers who induce sign-ups may face criminal liability.**
  — [SBS Biz](https://biz.sbs.co.kr/amp/article/20000339576); [블록미디어](https://www.blockmedia.co.kr/archives/1150776); [블록미디어 (Google Play)](https://www.blockmedia.co.kr/archives/1032177). The statute is 특정금융정보법 (registration duty and penalty). Article numbers were not retrieved from law.go.kr in this pass.

**Prediction markets**
- **Polymarket:** on **18 Aug 2026** the KCSC (방송미디어통신심의위원회) voted to **block domestic access to Polymarket**. Its grounds were information aiding gambling or opening a gambling venue under the **Criminal Act (형법)** and "similar acts" under the **National Sports Promotion Act (국민체육진흥법)**. It cited the winner-take-all structure and crypto settlement, and held that the lack of Korean-language service or KRW payment does not exempt the platform. Access was confirmed blocked by the 21st. Gangwon police have been investigating Korean users since June 2026. Polymarket disputes the decision. — [위키트리](https://www.wikitree.co.kr/articles/1153222); [블록미디어](https://www.blockmedia.co.kr/archives/1130311); [주간경향](https://weekly.khan.co.kr/article/202607280600011); [Sigma](https://sigma.world/ko/news/26-polymarket-booked-south-korea-ban/)
- **Criminal Act Art. 246:** gambling is punishable by a **fine of up to KRW 10M**, except for "momentary entertainment" (일시오락). Commentators say the active-personality principle applies the Act to Korean nationals' bets abroad. Sports outcomes fall under the National Sports Promotion Act; elections, rates and events fall under Art. 246. Commentators also note an argument that a product qualifying as a 자본시장법 derivative could be lawful. **No court ruling on a Korean prediction-market user was found.** — [블록미디어 (lawyer Q&A)](https://www.blockmedia.co.kr/archives/1140466); [로톡](https://www.lawtalk.co.kr/posts/176828). Statute text itself was not fetched (see [law.go.kr 형법](https://www.law.go.kr/법령/형법)).
- **Kalshi:**
  - **South Korea is not on Kalshi's restricted list.** The Member Agreement §VI (rev. 1 Oct 2026) lists 55 jurisdictions, including Australia, China, India, North Korea, Singapore, Taiwan, Thailand, UK, France and Canada.
  - **Kalshi perpetual futures are US-only.**
  — [CoinPerps guide](https://www.coinperps.com/learn/kalshi-restricted-countries-prediction-market-perps) (secondary; the Member Agreement itself was not fetched). Kalshi announced international access to about 140 countries in Oct 2025. — [Cointelegraph](https://cointelegraph.com/news/kalshi-300-million-raise-prediction-markets-140-countries)

### Venue table (status for a Korean-resident individual)

| Venue / instrument | Status | Reachable with KRW 42k? | Min ticket | Fees (as found) | Max leverage available | Rule relied on |
|---|---|---|---|---|---|---|
| KRX cash stocks (Kiwoom, Toss, etc.) | legal | yes (1 share; many issues < KRW 42k) | 1 share | broker commission + transaction tax (current rates not verified) | about 1x cash; margin/credit (미수/신용) exists but terms not verified | KRX ±30% daily limit since 15 Jun 2015 ([이투데이](https://www.etoday.co.kr/news/view/1127429)) |
| KRX 2x leveraged ETF/ETN | legal_with_conditions | **no**, if the KRW 10M deposit still applies (unverified) | 1 unit | as stocks | 2x product | 2020 FSC measure: KRW 10M deposit + education ([미래에셋](https://securities.miraeasset.com/public/mw/blog/html/20200916195431.html)) |
| KRX single-stock leveraged products (2026) | legal_with_conditions | unclear (needs 5-day mock trading; deposit unknown) | 1 unit | n/a | 2x | Aug 2026 mock-trading rule ([비즈워치](https://news.bizwatch.co.kr/article/market/2026/08/12/0036)) |
| KRX futures/options (KOSPI200 weeklies etc.) | legal_with_conditions | **no** (deposit at least KRW 10M) | 1 contract | n/a | exchange margin | 2019 reform: deposit KRW 10M+, 1h education + 3h mock ([FSC plan](https://www.smallake.kr/wp-content/uploads/2019/06/2019년-파생상품시장-발전방안.pdf)) |
| Overseas futures (CME micros) via Korean broker | legal_with_conditions | **no** (micro margin $110-$2,310 > $30) | 1 contract | about $2+ per contract | exchange margin (~10x+) | 1h education + 3h mock from 15 Dec 2025 ([경북매일](https://kbmaeil.com/article/20251215500253)) |
| Overseas options, **buying** far-OTM (e.g., options on micro futures) | legal_with_conditions | unclear (a premium under $30 may exist, but per-contract fees take a large share; not verified per product) | 1 contract | about $2+ per contract | premium-only (implicit leverage high) | same as above |
| Overseas leveraged ETPs (e.g., US 2x/3x) | legal_with_conditions | yes, for low-priced ETPs (unverified per ticker) | 1 share | broker FX + commission (not verified) | 2-3x product | 1h pre-education from 15 Dec 2025 ([경북매일](https://kbmaeil.com/article/20251215500253)) |
| US single-stock / 0DTE index options | unknown (domestic broker availability not confirmed; using a foreign broker directly vs. the 자본시장법 시행령 제184조 domestic-intermediary rule not confirmed) | unclear | 1 contract (100 multiplier) | n/a | premium-only | 시행령 제184조 text not retrieved ([search note](https://www.nepla.ai/law/%EC%9E%90%EB%B3%B8%EC%8B%9C%EC%9E%A5%EA%B3%BC%20%EA%B8%88%EC%9C%B5%ED%88%AC%EC%9E%90%EC%97%85%EC%97%90%20%EA%B4%80%ED%95%9C%20%EB%B2%95%EB%A5%A0%20%EC%8B%9C%ED%96%89%EB%A0%B9/20210316)) |
| Domestic crypto spot (Upbit, Bithumb, etc.) | legal | yes | min order not verified (KRW 5,000 commonly cited) | about 0.05% (Upbit) | 1x | 특정금융정보법 registered VASPs |
| Domestic crypto lending (borrow top-20 coins) | legal_with_conditions | unclear (DAXA education + suitability test) | n/a | ≤20% per year | **no leverage beyond collateral** | FSC lending guideline, 5 Sep 2025 ([한경](https://www.hankyung.com/article/202509055461i)) |
| Unregistered offshore exchanges (KuCoin, MEXC, BingX perps, 50-125x) | blocked_by_platform / grey for users (operator liability; asset-freeze risk; referrers exposed) | technically, but access blocked since Oct 2026 | ~$1-5 | n/a | (offshore) very high | FIU block 13 Oct 2026; 특금법 unregistered-operation penalty ([SBS Biz](https://biz.sbs.co.kr/amp/article/20000339576)) |
| Polymarket | illegal (regulator view) / blocked | no (blocked since 18-21 Aug 2026) | about $1 | n/a | n/a | 형법 도박 / 국민체육진흥법; KCSC block ([위키트리](https://www.wikitree.co.kr/articles/1153222)) |
| Kalshi | grey (platform allows KR; Korean 형법 246 risk analogous to Polymarket) | likely yes (USD funding route not verified) | about $0.01-$1 per contract | taker fees apply (schedule not fetched) | 1x (perps US-only) | Kalshi Member Agreement §VI rev. 1 Oct 2026 per [CoinPerps](https://www.coinperps.com/learn/kalshi-restricted-countries-prediction-market-perps); 형법 246 |
| On-chain meme coins (pump.fun via self-custody wallet) | grey / unknown (no specific Korean statute found either way; pump.fun ToS geo-restrictions not checked) | yes (if the on-ramp via a domestic exchange works) | fractions of a dollar + Solana fees | platform/DEX fees (not fetched) | 1x spot (extreme volatility) | none confirmed |

### Inferences (probability estimates are my own reasoning, anchored on Q1 and Q2)
- **KRX cash equities:** 1.3^21 = 247x is the mechanical maximum with 21 consecutive +30% limit-ups. Reaching 1000x needs about **27 consecutive limit-up sessions** (ln 1000 / ln 1.3 = 26.3). **P(1000x) ≈ 0 without leverage.** Margin leverage does not change this materially, given VI/CB mechanisms and margin calls.
- **Overseas leveraged ETPs (2-3x daily):** the underlying would need sustained extreme daily gains. **Effectively 0.** I found no documented 1000x month; not verified.
- **Buying far-OTM overseas options (the most convex lawful path, if reachable):**
  - A single 1000x payoff is possible only in tail events.
  - Boyer-Vorkink and 0DTE evidence say lottery options are overpriced. Per-contract fees of about $2+ on a $30 account are a 7-14% drag per trade.
  - Defensible range: **≤0.05%, and likely 0.01-0.03%**. The supermartingale ceiling is 0.1%.
  - Also requires completing 1h education + 3h mock trading first.
- **Domestic crypto spot (incl. small-cap altcoins on registered exchanges):** no leverage, so 1000x requires a token to rise about 1000x within a month while listed on a registered exchange. **Well below 0.01%** (not sourced; no data found on domestic-listed 1000x months).
- **On-chain meme coins (legal grey):**
  - Graduation (about 1.4%) is necessary but far from sufficient for 1000x.
  - Only about 3% of users ever realized above $1,000 total.
  - **Per-attempt P(1000x) is plausibly on the order of 0.01-0.1%**, but the population of attempts is huge, which drives survivorship-biased stories.
  - Legal status for Korean residents is unconfirmed, and rug-pull/scam risk has no domestic recourse.
- **Prediction markets:**
  - Polymarket is blocked, and 형법 246 exposure is real (police investigations of users).
  - Kalshi is not geo-restricted for Korea by the platform, but the same Korean-law analysis likely applies. That is an inference, as no ruling or regulator statement on Kalshi was found.
  - Even ignoring law, a taker longshot gives about 0.068% or less per 1000:1 ticket.
- **Overall:** for every **lawful and reachable** path, a defensible P(USD 30 to USD 30,000 in a month) is **below 0.1%, and realistically 0.01% or less**. Any design that promises otherwise contradicts the bound in Q1.

### Gaps
- Current (Oct 2026) KRX derivatives and domestic leveraged ETF deposit amounts. The exact KRX 시행세칙 / 금융투자업규정 article numbers were not retrieved from law.go.kr or KRX.
- 자본시장법 시행령 제184조 text (whether a general investor may trade US options through a foreign broker such as IBKR): not retrieved. Status left as unknown.
- Whether Korean brokers currently offer US single-stock / SPX 0DTE options to retail: not confirmed.
- Kalshi: the Member Agreement was not read directly. KRW-to-USD funding routes and Kalshi's KYC acceptance of Korean IDs were not verified. No Korean regulator statement specific to Kalshi was found.
- pump.fun Terms of Service restricted jurisdictions: not checked. No Korean authority statement on DEX meme-coin purchases by individuals was found.
- Domestic FX margin trading (FX마진) and the legal sports-betting monopoly (스포츠토토/베트맨) were not researched.
- Bitget: one search snippet said it restricts South Korea, but the fetched page did not name Korea for other platforms. **Conflicting / unconfirmed.**
- 특정금융정보법 article numbers (registration duty, penalty) were not retrieved from primary text.

## Q4. Documented 100x-1000x small-account cases and survivorship bias

### Takeaway
I found no peer-reviewed study documenting small retail accounts compounding 1000x within a month. What exists are outlier leaderboards (pump.fun: 151 wallets with more than $1M profit and a top trader above $41M) set against populations of millions, where about 97% of persistent day traders lose. This is classic survivorship bias: visible winners are drawn from enormous numbers of failed attempts.

### Cited Findings
- pump.fun: top tracked trader realized above $41M profit, 151 wallets above $1M. The dashboard tracks only pre-graduation buys. — [Decrypt](https://decrypt.co/331108/business-memes-inside-solana-meme-coin-pump-fun?amp=1). Meanwhile about 3% of all users ever earned above $1,000. — [Unchained](https://unchainedcrypto.com/most-users-keep-losing-money-on-pump-fun-despite-the-protocols-record-profits/). A single day saw about 42,000 token launches, with fewer than 2% ever reaching a DEX. — [Solana Compass](https://solanacompass.com/news/pumpfun-launched-42000-tokens-in-one-day-fewer-than-2-will-ever-reach-a-dex)
- Brazil futures day traders persisting 300+ days: 97% lost and only about 0.4-0.5% beat a bank teller's wage. The authors say course providers' claims that one can day-trade for a living are contradicted. — [FGV](https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full). A critique notes the short (about 2-year) window. — [Substack review](https://whatworksintrading.substack.com/p/this-is-why-i-dont-believe-in-day)
- KCMI 2020: new Korean investors lost more often (62%) than existing ones (39%). — [fnnews](https://www.fnnews.com/news/202104131912345956)

### Inferences
- If P(1000x) per attempt is about 0.01-0.1% (Q3), then among 1 million attempts one expects about 100-1,000 visible 1000x winners. That is enough to fill social media with success stories while the expected return of each attempt stays negative. Winner screenshots carry no information about the strategy's edge.
- For product design (TRADEGEN): any backtest or "case study" showing 1000x from a small base should be treated as a selection artifact unless it reports the full denominator of attempts.

### Gaps
- No verified, independently audited case of a USD 30 account reaching USD 30,000 within 30 days was found. Social-media claims were not searched or relied on.
- No Korea-specific study (KCMI/FSS) on the right tail of retail returns (e.g., the share of accounts with more than 10x in a year) was found.
