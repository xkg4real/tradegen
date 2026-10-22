# Korean domestic securities and exchange-traded derivatives for a retail individual with ~KRW 42,000

Scope: a South Korean national living in Korea (university student), about KRW 42,000 (~USD 30) of capital, as of 2026-10-22. These notes describe what the rules and reporting say. They are not legal advice. Status labels: legal / legal_with_conditions / grey / illegal / blocked_by_platform / unknown.

Method caveat: 17 searches/fetches were run. law.go.kr statute text and KRX/KOFIA rulebooks were not fetched directly, so most rule figures below come from FSC-attributed press coverage, broker product pages and news. Wherever an article number is given from general knowledge and was not opened in this session, it is marked **[article no. unverified]**.

## KRX stocks (KOSPI, KOSDAQ, KONEX): price limit, VI, fees and tax, credit, short selling

### Takeaway
Cash buying of KOSPI and KOSDAQ shares is the only instrument in this file that is clearly lawful and clearly reachable with KRW 42,000. Prices can move at most ±30% per day (KONEX ±15%), VI auctions interrupt fast moves, and the 2026 securities transaction tax is 0.20% of the sale amount on both KOSPI (0.05% tax + 0.15% special rural tax) and KOSDAQ. Short selling resumed in full on 2025-03-31, with retail stock-borrowing collateral cut to 105%. Credit (margin) trading needs a broker-set deposit of 40-60% and 140% maintenance collateral, so on this account it adds at most about 2.5x, and probably nothing, because brokers set minimums.

### Cited Findings
**Price limit**
- KRX widened the daily price limit for KOSPI and KOSDAQ shares, DRs, ETFs, ETNs and beneficiary certificates from ±15% to ±30% of the reference price, effective 2015-06-15. KONEX shares kept ±15%. — [eToday 2015](https://www.etoday.co.kr/news/view/1127429); [eToday: business-rule amendment approved by FSC](https://www.etoday.co.kr/news/view/1117388)
- The same package added an individual-stock static VI (a 2-minute cooling-off period on a move of 10% or more from the last single-price) and changed the circuit breaker to stages at -8%, -15% and -20%. — [eToday 2015](https://www.etoday.co.kr/news/view/1127429)

**Volatility interruption (VI)**
- Dynamic VI measures the move from the last traded price. It fires at ±3% for KOSPI200 constituents and ±6% for other KOSPI and KOSDAQ names during the regular session, and at 2% and 4% in the closing window (15:20-15:30). — [KB Think VI guide](https://kbthink.com/stock/vi.html); [Newsis 2026-07-24](https://www.newsis.com/view/NISX20260724_0003722742)
- Static VI fires on a cumulative ±10% move from the reference (single-price/prior-close) price. Either VI switches the stock to a 2-minute single-price call auction, and it can fire more than once per day. — [KB Think](https://kbthink.com/investment/101/vi.html); [Newsis 2022](https://www.newsis.com/view/NISX20220519_0001878246)
- Nextrade (NXT, the alternative trading system) was reported to add static VI from 2026-09-14 and to replace its old "halt on VI" with a 2-minute single-price auction, the same as KRX. — [Economist (Korea) 2026-08-31](https://economist.co.kr/article/view/ecn202608310071); [Metro Seoul 2026-08-07](https://www.metroseoul.co.kr/article/20260807500193)

**Securities transaction tax (2026)**
- From 2026-01-01, KOSPI sales are taxed at 0.20% in total (securities transaction tax 0.05% + special rural tax 0.15%). KOSDAQ and K-OTC sales are taxed at 0.20% with no rural tax. — [Segye 2026-01-05](https://www.segye.com/newsView/20260105516769); [Economist (Korea) 2025-12-22](https://economist.co.kr/article/view/ecn202512220061); [Tax Times](https://www.taxtimes.co.kr/news/article.html?no=272624)
- The KOSPI all-in rate went 0.20% (2023) → 0.18% (2024) → 0.15% (2025) → 0.20% (2026). The tax applies only on sale and is due whether the trade made or lost money. — [Segye](https://www.segye.com/newsView/20260105516769); [studygov.kr summary](https://studygov.kr/blog/0335-2026-stock-market-policy-changes/)
- Legal basis: Securities Transaction Tax Act (증권거래세법) Art. 8 (rates) and its Enforcement Decree; Special Rural Development Tax Act (농어촌특별세법) Art. 5 **[article nos. unverified]**.

**Credit / margin trading (신용거래)**
- Broker credit-trading guides show margin deposit rates (보증금률) set per stock in a 40-60% band (one broker: 45% cash, 35% substitute securities possible) and a maintenance collateral ratio of 140%, with margin calls below that. — [Samsung Securities credit guide](https://www.samsungpop.com/mbw/bankingLoan/creditGuide/guide.pop); [Korea Investment credit-trading explanation (PDF)](https://file.koreainvestment.com/updata/namo/02104847신용거래설명서_신구.pdf); [Mirae Asset](https://securities.miraeasset.com/hki/hki3035/n01.do)
- A KRW 1,000,000 minimum collateral was confirmed only for a capital-company linked-credit product (NH Capital 연계신용), not for ordinary broker credit. — [NH Capital linked-credit PDF](https://www.creontrade.com/nsl/download/creon/nh_capitalSC.pdf)
- Legal basis: FSCMA (자본시장법) Art. 72 (credit extension by investment traders/brokers) and the Financial Investment Business Regulation (금융투자업규정) credit-extension chapter **[article nos. unverified]**.

**Short selling (공매도)**
- The FSC resumed short selling for all stocks on 2025-03-31, after a record 17-month ban. KOSPI200/KOSDAQ150 names resumed after 17 months and the rest after about 5 years. — [Metro Seoul 2025-03-21](https://www.metroseoul.co.kr/article/20250321500400); [FSC](https://fsc.go.kr/no010101/84216?curPage=95)
- Retail stock-borrowing (대주) collateral was cut from 120% to 105%, and the retail repayment period was aligned with institutional securities lending (90 days, up to 12 months with extensions). — [Metro Seoul 2025-03-21](https://www.metroseoul.co.kr/article/20250321500400)
- Intentional naked short selling now carries fines of 4-6x the illicit gain, plus aggravated prison terms where the gain is KRW 500M or more. Short sellers also face limits on acquiring CBs/BWs. — [Metro Seoul 2025-03-21](https://www.metroseoul.co.kr/article/20250321500400)
- Under the 2021 regime, first-time retail short sellers had to finish a 30-minute KOFIA pre-education course and 1 hour of KRX mock trading. Borrowing limits were KRW 30M for new investors and KRW 70M after 5+ trades and KRW 50M+ cumulative borrowing. Experience was not shared between brokers. — [Kyunghyang 2021-05-02](https://www.khan.co.kr/article/202105021409001); [inews24](https://www.inews24.com/view/1362874)
- Legal basis: FSCMA Art. 180 (restriction on short selling) **[article no. unverified]**.

### Inferences
- The ±30% limit and the VI auctions cap intraday convexity. Even a stock that hits the upper limit every day gains at most 30% per session.
- At KRW 42,000, one KOSPI round trip costs about KRW 84 in sell-side tax, plus broker and exchange fees. That is negligible per trade, but a strategy that turns the book over daily for 21 sessions loses roughly 21 × 0.2% ≈ 4.3% to tax alone.
- Even at a 40% margin deposit, credit at most lifts exposure to about KRW 105,000 (2.5x). Brokers' own minimum-collateral and eligibility screens (credit score, account age) are likely to make it unavailable. Status: legal_with_conditions, reachability unclear.
- Retail short selling is legally open, but 105% collateral means a KRW 42,000 account can short at most about KRW 40,000 notional. Gains on a short are capped at 100% per position. It offers no upside convexity toward a 1,000x target.

### Gaps
- No primary text (KRX 유가증권시장/코스닥시장 업무규정 article numbers) was retrieved for the price limit or VI. The figures come from news and broker explainers.
- Brokerage commission and exchange/depository fee rates for 2026 were not confirmed. Many brokers advertise near-zero online fees, but no 2026 schedule was opened. [Brunch 2026 Toss fee comparison](https://brunch.co.kr/@coygray/618) was found but not fetched.
- The KONEX 2026 transaction-tax rate was not confirmed.
- No source confirmed whether a KRW 1,000,000 minimum deposit for ordinary 신용거래 exists in KOFIA rules or is broker policy.
- Not confirmed: whether the 2021 retail short-selling pre-education (30 min) and mock trading (1 h), and the KRW 30M/70M experience tiers, survive unchanged after the 2025 resumption. No 2025 source mentioned them.
- KRX market-surveillance designations (투자주의/경고/위험, trading suspensions after consecutive surges) were not researched. They would interrupt any run of consecutive limit-up days.

## Domestic leveraged / inverse ETF and ETN: mandatory pre-education and basic deposit

### Takeaway
Domestic leveraged ETPs (ETF/ETN) require 1 hour of KOFIA/금융투자교육원 online pre-education plus a basic deposit of at least KRW 10,000,000, so they are out of reach at KRW 42,000. Single-stock leveraged ETF/ETNs (first listed 2026-05-27) were tightened from 2026-07-31: the deposit is KRW 30,000,000 in cash only, education is 3 hours in total, new listings are halted, and a 20-unit minimum trading lot is planned.

### Cited Findings
- As of November 2025, trading domestic leveraged ETPs or domestic derivatives required the education plus a basic deposit of at least KRW 10,000,000. Without KRW 10M in the account, a trade cannot even be attempted. — [BizWatch 2025-11-17](https://news.bizwatch.co.kr/article/market/2025/11/17/0025)
- Before July 2026, the basic deposit could be met with cash plus 70% of the market value of substitute securities (stocks, non-leveraged ETFs, bonds). — [MTN 2026-07-16](https://news.mtn.co.kr/news-detail/2026071616232262750); [Daum/News1 2026-07-16](https://v.daum.net/v/20260716163952724)
- **Single-stock leveraged ETF/ETN (단일종목 레버리지):** announced 2026-07-16 by the FSC, FSS, BOK and MOEF after a meeting chaired by Deputy PM Koo Yun-cheol:
  - Deposit raised from KRW 10M (cash + substitutes) to **KRW 30M, cash only**. It must be met before every new or additional purchase, and brokers can no longer relax it for experienced clients.
  - Pre-education goes from 2 hours (1 h basic + 1 h advanced) to **3 hours**, adding a 1-hour case-based course, with quizzes and a 60-point pass mark per chapter.
  - New listings suspended provisionally. Advertising and event marketing banned.
  - LP premium/discount (괴리율) standard tightened from 3% to 2%.
  - Domestic trading unit to change from **1 unit to 20 units (provisional)** once broker systems are ready.
  - Source: [MTN 2026-07-16](https://news.mtn.co.kr/news-detail/2026071616232262750)
- On 2026-07-24 the FSC announced early implementation. Only investors holding KRW 30M+ in cash can make new or additional purchases from **2026-07-31**, and substitute securities are no longer counted. These products listed on 2026-05-27, and market cap and turnover grew quickly. — [FSC notice via KDI EIEC](https://eiec.kdi.re.kr/policy/materialView.do?num=284654); [NewsTomato](https://newstomato.com/ReadNews.aspx?no=1308112); [SBS Biz](https://biz.sbs.co.kr/amp/article/20000325011); [News Seoul](https://newsseoul.co.kr/news/view/1065577216778838)
- One report said investment requirements tighten from August and the trading unit expands from November, and that this also applies to existing holders' additional buys. — [kbmaeil 2026-07-17](https://kbmaeil.com/article/20260717500059) (as summarised in search results; not fetched)
- **Overseas leveraged ETPs** (context for the parallel research): from 2025-12-15, new buyers need 1 hour of KOFIA pre-education (fee KRW 3,000). Overseas derivatives need 1 h education plus 3 h mock trading, with more hours for investors aged 65+ or below the "very-high-risk" profile. No basic deposit applies. — [BizWatch 2025-11-17](https://news.bizwatch.co.kr/article/market/2025/11/17/0025). An early-2026 blog claimed a KRW 10M deposit would be introduced for overseas leveraged products; this was not corroborated by an official source. — [wikidocs blog](https://wikidocs.net/blog/@changeui/6861/)
- ETFs and ETNs are under the same ±30% daily price limit regime as shares since 2015. — [eToday 2015](https://www.etoday.co.kr/news/view/1127429)

### Inferences
- **Leveraged ETPs (general, 2x / -2x):** status legal_with_conditions, not reachable. The KRW 10M deposit is about 238x the available capital.
- **Single-stock leveraged ETPs:** status legal_with_conditions, not reachable. The deposit is KRW 30M in cash.
- **Plain 1x ETFs/ETNs, including plain 1x inverse:** reachable with no deposit, but they offer no more convexity than a stock (inference: the 2020 deposit and education regime targets products with multiples above 1x). Confirm against the broker before relying on this for -1x inverse.

### Gaps
- No primary rule text (금융투자업규정 or KRX 유가증권시장 업무규정 시행세칙 article numbers) was retrieved for the ETP basic deposit. The press reports attribute it to the FSC/KRX.
- Not confirmed whether the 20-unit trading lot for single-stock leveraged products has actually taken effect as of 2026-10-22.
- Not confirmed whether leveraged ETFs get a price limit scaled by their multiple. Most sources speak only of ±30%.
- Not confirmed whether ordinary (non-single-stock) leveraged ETP education is 1 hour or 2 hours in 2026. MTN says single-stock education was 2 h and general-leverage education stays 1 h.

## KOSPI 200 futures and options, mini futures, weekly options, ELW: retail entry requirements

### Takeaway
All KRX-listed derivatives sit behind 1 hour of pre-education, 3 hours of mock trading and a tiered basic deposit: Stage 1 at KRW 10M+ and Stage 2 (option selling, volatility futures) at KRW 20M+. ELW requires online education and, for new clients, a KRW 15M basic deposit. None is reachable at KRW 42,000. No 2026 easing was found; the only 2026 changes found were tightening.

### Cited Findings
- The FSC's 2019 derivatives-market development plan cut retail entry requirements from 20 h + 10 h of pre-education and 50 h of mock trading to **1 h of pre-education and 3 h of mock trading**. It set the general retail basic deposit at **Stage 1: KRW 10M or more; Stage 2: KRW 20M or more**. Stage 2 covers volatility-index futures and option-selling trades. — [FSC 2019 파생상품시장 발전방안 (PDF mirror)](https://www.smallake.kr/wp-content/uploads/2019/06/2019년-파생상품시장-발전방안.pdf); [NewDaily 2019-05-30](https://biz.newdaily.co.kr/site/data/html/2019/05/30/2019053000097.amp.html)
- In November 2025 the KRW 10M minimum deposit for domestic derivatives was still described as in force. — [BizWatch 2025-11-17](https://news.bizwatch.co.kr/article/market/2025/11/17/0025)
- Broker guides state that the basic deposit is tiered by stage and must be checked before depositing. — [Samsung Securities futures/options guide](https://www.samsungpop.com/ux/kor/trading/giftoption/cmelinkgiftglobalmarket/futureOptionGuide.pop); [Yuanta MyAsset](https://www.myasset.com/myasset/static/trading/TR_1700000_P1.jsp)
- **ELW:** trading requires an investment-profile assessment and 금융투자교육원 online pre-education. New clients need a basic deposit of **at least KRW 15,000,000**. When the rule started in 2011, existing ELW holders with a balance were grandfathered. — [Dealsite](https://dealsite.co.kr/articles/92106); [Asiae 2025-05-19](https://view.asiae.co.kr/article/2025051915092780637); [Ajunews 2011](https://www.ajunews.com/view/20110523000542)
- ELWs can lose up to 100% of principal at expiry. — [Asiae 2025-06-18](https://view.asiae.co.kr/article/2025061815190151500)
- A search for 2026 easing of derivatives entry rules found none. The 2026 measures found were tightening, aimed at single-stock leveraged ETPs. — [NewsTomato](https://newstomato.com/ReadNews.aspx?no=1308112); [FSC via KDI EIEC](https://eiec.kdi.re.kr/policy/materialView.do?num=284654)

### Inferences
- **KOSPI200 futures, mini KOSPI200 futures, KOSPI200 options (including weekly), ELW:** status legal_with_conditions, reachable: no. The binding constraint is the deposit (KRW 10M to 20M, or KRW 15M for ELW), not the education.
- Once someone does qualify, far out-of-the-money weekly KOSPI200 options are the domestic instrument with the highest theoretical convexity. That is irrelevant at KRW 42,000 because the deposit blocks entry.

### Gaps
- KRX contract specs were not verified in this session: multipliers (KOSPI200 options assumed KRW 250,000 per point, mini futures KRW 50,000 per point), minimum ticks, and the weekly-option expiry days (Mon/Thu). They are therefore not stated as fact.
- No primary text of the KRX 파생상품시장 업무규정 or 시행세칙 article setting the basic deposit was retrieved **[article no. unverified]**.
- The exact assignment of mini futures and weekly options to Stage 1 or Stage 2 was not confirmed.
- ELW education hours (1 h is commonly cited) and the 2026 deposit were not confirmed from a primary source. The 2025 articles repeat the KRW 15M figure.

## FX margin trading (FX마진거래) and CFD

### Takeaway
Domestic FX margin is legal through licensed Korean brokers. The standard contract is 100,000 units of the base currency, with 10% initial margin (US$10,000 per lot, 10x leverage) and 50% maintenance, so it is unreachable at KRW 42,000. CFDs are restricted to individual professional investors, with a 40% minimum margin (max 2.5x) made permanent in 2023 and entry thresholds starting at KRW 50M in financial assets. Both are unreachable.

### Cited Findings
**FX margin**
- Kiwoom states that the basic FX-margin trading unit is 100,000 units of the base currency. Initial margin is 10% of that, US$10,000 (10x). Maintenance margin is US$5,000, and falling below it triggers forced liquidation of all open positions. — [Kiwoom FX margin page](https://www.kiwoom.com/h/foreign/fofx/VFxMainView)
- Regulators raised the margin ratio from 2% (50x) to 5% (20x) in September 2009, after heavy retail losses (about 90% of investors losing) and widespread illegal operators. — [NewDaily 2011](https://biz.newdaily.co.kr/site/data/html/2011/07/03/2011070310017.html); [Ajunews 2009](https://www.ajunews.com/view/20090716000204)
- Korea Investment offers an FX-margin mock-trading system. — [Korea Investment (truefriend)](https://www.truefriend.com/main/bond/foreign/_static/TF03dg030001.jsp)

**CFD**
- In October 2021, major brokers raised the CFD minimum margin from 10% to 40%. Commentators noted it then had no statutory force. — [Economist (Korea) 2021-10-01](https://economist.co.kr/article/view/ecn202110010022)
- After the 2023 SG Securities crash, the FSS administrative guidance setting a 40% minimum margin was made permanent, and CFD exposure was counted in brokers' credit-extension limit (within 100% of equity). — [Metro Seoul 2023-05-29](https://www.metroseoul.co.kr/article/20230529500165); [Maeil 2023-05-29](https://www.imaeil.com/page/view/2023052915104379887)
- Individual professional-investor eligibility (2019): at least KRW 50M in financial-investment products, plus annual income of KRW 100M (KRW 150M combined with a spouse) or net assets of KRW 500M. The 2023 tightening barred CFD use without high-risk product experience, required face-to-face or video ID verification on first designation, and requires brokers to re-verify every 2 years. — [Bizhankook](https://bizhankook.com/articles/25572.html); [Kukinews 2023-05-10](https://www.kukinews.com/article/view/kuk202305100037); [YTN 2023-05-29](https://www.ytn.co.kr/_ln/0102_202305291215196149)
- Legal basis for professional-investor status: FSCMA Art. 9(5) and Enforcement Decree Art. 10 **[article nos. unverified]**.

### Inferences
- **Domestic FX margin:** status legal_with_conditions, not reachable. One standard lot needs about US$10,000 (roughly KRW 14M) of initial margin, about 330x the available capital.
- **Offshore FX/CFD brokers soliciting Korean residents** are outside this file's scope. Unlicensed financial-investment business is prohibited under FSCMA Art. 11 **[article no. unverified]**, so such venues are likely illegal or grey for the user. The parallel offshore-venue research should confirm this.
- **CFD:** status legal_with_conditions (professional investors only), not reachable. Maximum leverage is 2.5x at 40% margin.

### Gaps
- No current (2026) primary source was found for: whether domestic FX margin carries its own basic deposit or the 1 h education + 3 h mock-trading requirement; the statutory margin floor (believed to be in 금융투자업규정); or which Korean brokers still offer FX margin in 2026. Most sources are from 2009 to 2013.
- The current CFD minimum-margin rule was not checked against the latest 금융투자업규정 text.

## Reachability at KRW 42,000 and maximum convexity

### Takeaway
At KRW 42,000 the only reachable instruments are cash KOSPI/KOSDAQ/KONEX shares (on KRX or NXT), plain 1x ETF/ETNs, and in principle tiny retail short sales and tiny credit positions. None has leverage above about 1x in practice. The theoretical maximum for a stock that hits +30% in all 21 sessions is 1.3^21 ≈ 247x, about KRW 10.4M before tax and fees. A 1,000x outcome (USD 30 → USD 30,000) would need about 26.3 consecutive limit-up sessions, more than exist in a month, so it is arithmetically impossible on any lawful domestic instrument reachable with this capital.

### Cited Findings
- Daily price limit ±30% (KOSPI/KOSDAQ shares, ETF, ETN) and ±15% (KONEX). — [eToday 2015](https://www.etoday.co.kr/news/view/1127429)
- Leveraged ETPs need a KRW 10M deposit, or KRW 30M cash for single-stock leveraged products. — [BizWatch](https://news.bizwatch.co.kr/article/market/2025/11/17/0025); [FSC via KDI EIEC](https://eiec.kdi.re.kr/policy/materialView.do?num=284654)
- Derivatives need a KRW 10M deposit for Stage 1 and KRW 20M for Stage 2. — [FSC 2019 plan](https://www.smallake.kr/wp-content/uploads/2019/06/2019년-파생상품시장-발전방안.pdf); [BizWatch](https://news.bizwatch.co.kr/article/market/2025/11/17/0025)
- ELW needs a KRW 15M deposit. — [Dealsite](https://dealsite.co.kr/articles/92106)
- FX margin needs US$10,000 per lot. — [Kiwoom](https://www.kiwoom.com/h/foreign/fofx/VFxMainView)
- CFD is for professional investors only, who need KRW 50M+ in financial assets. — [Bizhankook](https://bizhankook.com/articles/25572.html)
- Retail short collateral is 105%. — [Metro Seoul](https://www.metroseoul.co.kr/article/20250321500400)
- The 2026 sell-side tax is 0.20%. — [Segye](https://www.segye.com/newsView/20260105516769)

### Inferences
**Arithmetic** (computed here, not sourced):
- 1.3^21 = 247.06, so KRW 42,000 × 247.06 ≈ KRW 10.38M. Holding through the whole run means only one sale, so the 0.20% tax costs about KRW 20,800.
- 1.3^20 = 190.05, for a 20-session month.
- Sessions needed for 1,000x = ln(1000) / ln(1.3) = 6.908 / 0.2624 ≈ 26.3.
- Even with 2.5x credit, if any were granted, a −40% day ends the account. Credit does not change the limit-up compounding ceiling on the underlying.

**Practical ceiling.** Real paths are far below 247x. Static and dynamic VI auctions, KRX market-warning designations and trading suspensions interrupt consecutive limit-up runs (designation thresholds not researched here; see Gaps). Fills are also uncertain: limit-up queues often leave buy orders unfilled.

**Venue table for the designer:**

| Venue / instrument | Status for a KR-resident individual | Reachable with KRW 42k | Min ticket | Max leverage for this person | Main barrier / rule |
|---|---|---|---|---|---|
| KOSPI/KOSDAQ cash stocks (KRX, NXT) | legal | yes | 1 share | 1x | ±30%/day; VI; 0.20% sell tax (2026) |
| KONEX cash stocks | legal_with_conditions (KONEX historically had a separate basic-deposit rule; not verified for 2026) | unclear | 1 share | 1x | ±15%/day |
| Plain 1x ETF/ETN (incl. 1x inverse) | legal | yes | 1 unit | 1x | ±30%/day |
| Credit/margin (신용) | legal_with_conditions | unclear (broker minimums) | broker-set | ≈2.5x at 40% deposit | FSCMA Art. 72 [unverified]; 140% maintenance |
| Retail short selling (대주) | legal_with_conditions | technically yes, tiny | broker-set | <1x (105% collateral) | Resumed 2025-03-31; 2021-era education/mock-trading rules possibly still apply |
| Leveraged ETF/ETN (2x) | legal_with_conditions | no | KRW 10M deposit | 2x | 1 h education + KRW 10M deposit |
| Single-stock leveraged ETF/ETN | legal_with_conditions | no | KRW 30M cash deposit; 20-unit lot planned | 2x | From 2026-07-31; 3 h education |
| KOSPI200 futures / mini futures / options / weekly options | legal_with_conditions | no | KRW 10M (Stage 1) / KRW 20M (Stage 2) | high (exchange margin) | 1 h education + 3 h mock trading + deposit |
| ELW | legal_with_conditions | no | KRW 15M deposit (new clients) | embedded | Education + deposit |
| Domestic FX margin | legal_with_conditions | no | US$10,000 per lot | 10x | 10% initial / 50% maintenance |
| CFD | legal_with_conditions (professional investors only) | no | KRW 50M+ asset test | 2.5x (40% margin) | FSS guidance made permanent 2023 |

### Gaps
- The exact number of KRX sessions between 2026-10-23 and 2026-11-22 was not checked against the KRX holiday calendar (about 21 assumed).
- KRX market-surveillance rules (investment caution/warning/risk designations, single-price trading, suspension triggers after consecutive surges) were not researched. They are the main practical cap on consecutive limit-up compounding.
- Domestic fractional-share trading (소수점 거래) minimum tickets were not researched.
- NXT (Nextrade) session hours and fee schedule were not verified.
- KONEX basic-deposit status in 2026 was not verified.
