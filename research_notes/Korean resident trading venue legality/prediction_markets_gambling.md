# Prediction markets and gambling law for a South Korean resident (as of 2026-10-22)

Scope: a South Korean national living in South Korea (Korea University student), about USD 30 / KRW 42,000 of capital. These notes describe what statutes, court rulings, regulator decisions and platform terms say. They are not legal advice. Anything not confirmed from a primary source, or that may have changed after mid-2026, is marked UNCERTAIN.

Status vocabulary used below: legal / legal_with_conditions / grey / illegal / blocked_by_platform / unknown.

## Q1. Which prediction-market venues accept a Korean resident, and has Korea blocked any of them?

### Takeaway
Polymarket has been blocked in Korea since 18 Aug 2026: the content regulator (방송미디어통신심의위원회, 방미심위) found that it supplies illegal gambling information under the Criminal Act and the National Sports Promotion Act. Polymarket's own docs list South Korea as close-only on the web frontend. Kalshi does not appear on its own restricted list, according to a secondary tracker that cites the Member Agreement revised 1 Oct 2026, and no Korean block of Kalshi was found. The regulator's reasoning about Polymarket would apply to Kalshi just as well, so Kalshi is grey at best for this person and its sports contracts are high-risk. Robinhood and Crypto.com event contracts are US-only. The offshore crypto venues (Limitless, Myriad, Opinion, Predict.fun) are unlicensed and get a lot of Korean traffic. I could not retrieve their ToS jurisdiction lists.

### Cited Findings

**Polymarket: Korean regulator decision**
- On 2026-08-18 the 통신심의소위원회 of 방미심위 voted to order access blocking (접속차단, a 시정요구) of Polymarket. It held that the site carries information aiding gambling or aimed at opening a gambling venue under the Criminal Act (형법), and information on "similar acts" (유사행위) under the 국민체육진흥법. The article cites no article numbers. — [Newsis, 2026-08-18](https://www.newsis.com/view/NISX20260818_0003752716)
- The regulator's reasoning had three parts. First, a winner-takes-all payoff on events users cannot control (politics, economy, sports, elections, weather) encourages gambling (사행심). Second, Polymarket sets market and trading rules, runs crypto deposit, withdrawal and settlement, and earns fees on share trades. Third, it listed Korea-specific markets such as "August rainfall in Seoul." — [Newsis](https://www.newsis.com/view/NISX20260818_0003752716); [Wikitree](https://www.wikitree.co.kr/articles/1153222)
- The 경찰청, 사행산업통합감독위원회 (사감위) and 국민체육진흥공단 all submitted opinions that the operation could amount to opening a gambling venue and to gambling offences under domestic law. — [Newsis](https://www.newsis.com/view/NISX20260818_0003752716)
- Polymarket put forward three defences: it had removed its Korean-language service and accepts no KRW payments; it is non-custodial P2P on smart contracts and so is not a "주재자" (operator); and it neither collects funds nor issues betting tickets. The regulator rejected all three, saying that dropping Korean-language service or using decentralized technology cannot avoid domestic law. — [Newsis](https://www.newsis.com/view/NISX20260818_0003752716)
- The article reports no criminal case against Korean users and does not mention VPNs. It says the block is meant to protect domestic users. — [Newsis](https://www.newsis.com/view/NISX20260818_0003752716)
- Korea is reported as one of 30-odd countries that restrict Polymarket. France blocked it from 2026-07-16, Australia in Aug 2025 and Germany in Sep 2025. — [Wikitree](https://www.wikitree.co.kr/articles/1153222); [Newsis](https://www.newsis.com/view/NISX20260818_0003752716)

**Polymarket: platform-side geoblock (primary: Polymarket docs)**
- Polymarket's developer docs list South Korea (KR) under "Close-only (frontend only; API not restricted)" together with Ireland, Japan, Malta (sports only) and the Netherlands. Close-only means existing positions can be closed but no new ones opened. — [Polymarket docs: Geographic Restrictions](https://docs.polymarket.com/api-reference/geoblock)
- `GET https://polymarket.com/api/geoblock` returns `blocked`, `ip`, `country` and `region`. The docs advise checking it before placing orders, since orders from blocked regions are rejected. — [Polymarket docs](https://docs.polymarket.com/api-reference/geoblock)
- Fully blocked (OFAC) jurisdictions are Iran, Syria, Cuba, North Korea, and Crimea, Donetsk and Luhansk. The US, UK, France, Germany, Italy, Singapore, Taiwan, Thailand, Australia and others are close-only on both frontend and API. — [Polymarket docs](https://docs.polymarket.com/api-reference/geoblock)
- Third-party lists of Polymarket restrictions disagree with each other (counts of 39 to 41 countries) and with the official docs. — [Coinrithm](https://www.coinrithm.com/en/blog/polymarket-countries-and-availability); [Datawallet](https://www.datawallet.com/crypto/polymarket-restricted-countries)

**Kalshi**
- Kalshi opened to traders outside the US in Oct 2025 and says it is live in more than 140 countries. — [CDC Gaming](https://cdcgaming.com/brief/kalshi-expands-to-140-countries-announces-funding-5-billion-valuation/); [Coinperps](https://www.coinperps.com/learn/kalshi-restricted-countries-prediction-market-perps)
- A secondary tracker says the restricted list sits in Section VI of the Kalshi Member Agreement "last revised on 1 October 2026." The list has 55 jurisdictions plus US-sanctioned territories. The Asia-Pacific entries are Afghanistan, Australia, China, India, Laos, Myanmar, New Zealand, North Korea, Singapore, Taiwan and Thailand. **South Korea is not listed.** India was added on 2026-06-17. — [Coinperps](https://www.coinperps.com/learn/kalshi-restricted-countries-prediction-market-perps)
- CONFLICT: one aggregated search result said a source lists South Korea as restricted for Kalshi, while others say it is absent. Counts of restricted jurisdictions range from 38 (an older agreement) to 52-55. — [Kalshi Legal Countries (Laika Labs)](https://laikalabs.ai/prediction-markets/kalshi-legal-supported-restricted-countries); [Datawallet](https://www.datawallet.com/crypto/kalshi-explained); [Coinperps](https://www.coinperps.com/learn/kalshi-restricted-countries)
- Restrictions are reported to attach to location or domicile, not nationality. A Kalshi spokesperson is reported as saying that verified members with an address in an unrestricted country can keep trading while travelling, which conflicts with a strict location rule. — [Coinperps (RU)](https://www.coinperps.com/ru/learn/kalshi-restricted-countries)
- Funding and limits (secondary): $10 minimum deposit; $1,000 minimum for international wires; non-US deposits by Visa/Mastercard debit, wire or crypto (USDC, BTC, SOL, XRP and others, converted to USD); withdrawals by debit card or crypto only; all balances held in USD. KYC requires a live photo ID, sometimes a selfie, a residential address, age 18+, and on request proof of address or source of funds. — [Coinperps](https://www.coinperps.com/learn/kalshi-restricted-countries-prediction-market-perps)
- Fees (primary PDF): the general taker fee is round_up(0.07 × C × P × (1−P)). The maker fee uses 0.0175. Some product families have their own schedules. — [Kalshi fee schedule PDF](https://kalshi.com/docs/kalshi-fee-schedule.pdf?); worked example: 100 contracts at $0.50 cost about $1.75 in taker fees — [Allium](https://allium.so/blog/kalshi-fees-why-the-cost-peaks-near-50-cents/)
- Kalshi perps are available only to US-based members with a margin account. Leverage on US perps runs from 2.2x to 15.8x (BTC 6.8x) as of 2026-10-19. **Non-US users get no perps and no leverage.** — [Coinperps](https://www.coinperps.com/learn/kalshi-restricted-countries-prediction-market-perps)
- My Korean-language search found no report of a Korean block of Kalshi. Taiwan blocked the Kalshi and Coinbase websites by court approval ahead of its 28 Nov local elections, and the mobile apps reportedly kept working. — [Wikitree (Taiwan)](https://www.wikitree.co.kr/articles/1166594); [Sigma](https://sigma.world/news/taiwan-blocks-kalshi-coinbase-election-betting-2026/)
- Kalshi is a US federal (CFTC) licensee and does not hold local licences in most other countries. — [Predictionnews](https://predictionnews.com/news/kalshi-tests-limits-of-global-reach-regulatory-hurdles-loom/)

**Robinhood / Crypto.com event contracts**
- Robinhood began routing football event contracts to Crypto.com's prediction platform on 2026-09-08 for eligible US customers. It also routes to Kalshi, ForecastEx and Rothera. Crypto.com offers prediction contracts through Crypto.com Derivatives North America, a CFTC-regulated DCO/DCM, and launched the standalone OG platform in Feb 2026. — [The Block, 2026-09-08](https://www.theblock.co/news/markets/2026-09-08-robinhood-expands-prediction-markets-crypto-com-og-partnerships-nfl-season-413832); [Robinhood newsroom](https://robinhood.com/us/en/newsroom/robinhood-cryptocom)

**Offshore crypto-native prediction markets**
- Similarweb traffic (as of Mar 2026): Myriad (Cayman; owned by DASTAN/Decrypt) gets 31.8% of its traffic from South Korea, its #1 source. Predict.fun (BVI) gets 10.9% (#2). Limitless (Panama; Coinbase Ventures) gets 9.1% (#4) and has a dedicated South Korea section on its website. Opinion (Panama; Jump Crypto) has no Korean figure in the top five. The author describes all four as offshore, with ownership and location not clearly disclosed. — [TradeInformer, 2026-03-02](https://tradeinformer.com/newsletter/limitless-predict-opinion-myriad-offshore-prediction-markets-are-already-here)
- Myriad's site says "There are Points and USD₮ markets available, depending on your country". That suggests real-money markets are geo-gated, but the ToS page could not be read. — [Myriad](https://myriad.markets/terms)
- Limitless runs on Base; Myriad uses an AMM. Both are described as unregulated (secondary). — [pm.wiki comparison](https://pm.wiki/compare/limitless-exchange-vs-myriad)
- Drift BET ("Bullish on Everything") launched in Aug 2024 on Solana, inside the Drift perps DEX. An Apr 2026 comparison describes BET as sharing cross-margin with Drift perps and having thin liquidity per event. — [The Block, 2024](https://www.theblock.co/post/311888/solana-based-drift-protocol-launches-prediction-market); [pm.wiki](https://pm.wiki/compare/drift-protocol-vs-polymarket)

**Venue matrix (Korean-resident individual, KRW ~42,000)**

| Venue / instrument | Status for KR resident | Reachable with ~KRW 42k? | Min ticket | Fees | Max leverage for this person | Rule relied on |
|---|---|---|---|---|---|---|
| Polymarket (intl) | **illegal** (방미심위 block, 2026-08-18) **+ blocked_by_platform** (KR close-only on frontend; API not restricted per docs) | Technically yes via API/USDC; legally no | UNCERTAIN (not verified) | UNCERTAIN (not verified) | none (fully funded binary) | 방미심위 decision (형법 도박/도박장소개설 information; 국민체육진흥법 유사행위); [docs](https://docs.polymarket.com/api-reference/geoblock) |
| Kalshi event contracts, non-sports | **grey** (platform reportedly allows KR; Korean characterization untested; same "winner-takes-all on uncontrollable events" logic used against Polymarket) | Yes ($10 card minimum), but KR-issued card acceptance UNCERTAIN | $10 deposit; contracts priced $0.01-$0.99 (contract granularity not verified) | taker 0.07·C·P(1−P), maker 0.0175·… | none (perps US-only) | 형법 제246조①; 방미심위 Polymarket reasoning by analogy; Kalshi Member Agreement §VI (secondary) |
| Kalshi sports event contracts | **illegal (high risk)** | Same as above | Same | Same | none | 국민체육진흥법 제26조①, 제48조3호; 대법원 2022도6462 |
| Kalshi perps | **blocked_by_platform** (US-only) | No | n/a | 0.12% taker / 0.02% maker (US) | n/a for KR | Coinperps |
| Robinhood / Crypto.com / OG event contracts | **blocked_by_platform** (US eligible customers; international availability not found) | No | n/a | n/a | n/a | The Block 2026-09-08 |
| PredictIt | **unknown** (not researched successfully; historically US-focused) | UNCERTAIN | UNCERTAIN | UNCERTAIN | n/a | none found |
| Limitless / Myriad / Opinion / Predict.fun / Drift BET | **grey → likely illegal** (unlicensed offshore; 방미심위 said decentralization does not avoid Korean law; ToS lists not retrieved) | Technically yes (USDC/USDT on-chain) | UNCERTAIN | UNCERTAIN | Drift BET cross-margined with perps (level unverified) | 형법 제246조; 국민체육진흥법 제48조3호 for sports; 방미심위 reasoning |
| Sports Toto via Betman (betman.co.kr) | **legal_with_conditions** | Yes | KRW 1,000 (프로토 승부식) | payout rate not verified | none | 국민체육진흥법 (licensed issuer); 회차당 KRW 100,000 cap |
| Lotto 6/45 online (동행복권) | **legal_with_conditions** | Yes | KRW 1,000/game | n/a | none | KRW 5,000 per draw per person (PC+mobile) |

### Inferences
- The 방미심위 reasoning does not depend on Polymarket's crypto rails. It rests on (a) a winner-takes-all payoff on events the user cannot control, (b) an operator that sets rules, settles and takes fees, and (c) Korea-relevant markets. Kalshi meets (a) and (b) and lists sports and other markets Koreans can bet on. The absence of a Kalshi block is therefore probably a matter of enforcement priority, not a finding that Kalshi is lawful for Korean users. This is my inference; no Korean authority has ruled on Kalshi.
- Polymarket's "API not restricted" for KR is a platform-side technical gap. Korean law still treats the user's conduct the same way (see Q2/Q3), so a trading tool should not route KR-resident orders through the API.
- Binary event contracts have no margin, but a $0.05 contract that settles at $1 pays 20x. This embedded convexity is the only "leverage" a non-US user gets on Kalshi, and it is the same payoff structure the regulator called 사행성.
- For a product designer: geo/eligibility gating should key on residence (KYC address), not IP. Kalshi's rule is location-or-domicile, and Korean criminal law follows nationality and territory (Q2), not IP.

### Gaps
- I could not read Kalshi's restricted list from Kalshi's own site (help center or Member Agreement PDF). The "KR not restricted" claim rests on a secondary tracker, and one other aggregator conflicts with it. UNCERTAIN.
- Whether Kalshi accepts Korean-issued Visa/Mastercard debit cards, and whether Korean exchanges (Upbit, Bithumb) allow USDC withdrawals to Kalshi's payment partner or to Polymarket wallets, was not researched. Travel-rule and KoFIU rules on unregistered foreign VASPs may block this route. UNCERTAIN.
- Polymarket's minimum order size and fees, and the date when KR was added to its close-only list, were not confirmed.
- PredictIt eligibility for non-US residents: no source found.
- Terms of Service for Limitless, Myriad, Opinion and Predict.fun could not be retrieved (404 or empty Notion page). Whether South Korea is on their restricted lists is unknown. Drift BET's 2026 operating status is unconfirmed.
- No source found on whether 방미심위 has acted against Kalshi, Limitless, Myriad or other prediction markets after 2026-08-18.
- Whether Kalshi contracts might instead be classed as overseas derivatives under 자본시장법 (which would require trading through a domestic licensed 투자중개업자) was not researched. UNCERTAIN.

## Q2. Criminal Act Arts. 246, 247 and 3, the 일시오락 exception, and Supreme Court case law: would event contracts or crypto prediction markets be gambling?

### Takeaway
Gambling (도박) is punishable by a fine of up to KRW 10M, or up to 3 years' imprisonment or a KRW 20M fine if habitual (상습). There is an exception for 일시오락 (momentary amusement), judged by time, place, stake size and the participant's status and wealth. Korean nationals are covered abroad (Art. 3). The Supreme Court has held that gambling at a casino that is legal where it operates is not thereby justified. No court ruling on event contracts or prediction markets was found. The 방미심위 decision is the only official Korean characterization, and it treats Polymarket as gambling.

### Cited Findings
- **형법 제246조①**: "도박을 한 사람은 1천만원 이하의 벌금에 처한다. 다만, 일시오락 정도에 불과한 경우에는 예외로 한다." **②**: "상습으로 제1항의 죄를 범한 사람은 3년 이하의 징역 또는 2천만원 이하의 벌금에 처한다." (전문개정 2013.4.5) — [law.go.kr 형법 제246조](https://www.law.go.kr/lsLinkProc.do?lsClsCd=L&lsNm=%ED%98%95%EB%B2%95&lsId=detc20130926&joNo=024600000&efYd=20130926&mode=11)
- **형법 제247조**: "영리의 목적으로 도박을 하는 장소나 공간을 개설한 사람은 5년 이하의 징역 또는 3천만원 이하의 벌금에 처한다." The Criminal Act was most recently amended by Act No. 22007 (2026-09-29, effective 2026-10-02). The page does not say whether Art. 247 changed. — [law.go.kr 형법 제247조](https://www.law.go.kr/lsLinkProc.do?lsClsCd=L&lsNm=%ED%98%95%EB%B2%95&joNo=024700000&mode=11)
- **형법 제3조**: "본법은 대한민국영역외에서 죄를 범한 내국인에게 적용한다." — [law.go.kr 형법 제3조](https://www.law.go.kr/lsLinkProc.do?lsClsCd=L&lsNm=%ED%98%95%EB%B2%95&joNo=000300000&mode=11)
- 일시오락 test: courts weigh the time and place of the gambling, the value of the stakes, and the participants' status and wealth. Listed rulings include 대법원 2014. 3. 13. 선고 2014도212. — [CaseNote 형법 제246조](https://casenote.kr/%EB%B2%95%EB%A0%B9/%ED%98%95%EB%B2%95/%EC%A0%9C246%EC%A1%B0) (secondary DB; judgment text not read)
- Domestic 일시오락 precedents: 85도2096 (1985-11-12) and 89도1992 (1990-02-09). One example is stakes of KRW 1,000-7,000 in a 100-won-per-point 고스톱 game. No income-based threshold is stated. "우연" is defined as an outcome the parties cannot foresee with certainty or freely control (2006도736, 2008-10-23). — [Lawtalk](https://www.lawtalk.co.kr/posts/176567) (secondary summary)
- Constitutional Court 2011헌마592 is reported as holding that betting that amounts only to 일시오락 within social norms has its wrongfulness negated. — reported in search summary of [CaseNote 형법 제246조](https://casenote.kr/%EB%B2%95%EB%A0%B9/%ED%98%95%EB%B2%95/%EC%A0%9C246%EC%A1%B0); NOT verified against the decision text.
- **Overseas casino rulings**: 대법원 2001. 9. 25. 선고 99도3337 (Philippine casino) held that a Korean who gambled where the casino was lawful remains subject to Korean law under Art. 3. 대법원 2004. 4. 23. 선고 2002도2518 is summarized as holding that gambling at Kangwon Land, which is permitted by special statute, is justified as an act under law, but "도박죄를 처벌하지 않는 외국 카지노에서의 도박이라는 사정만으로는 위법성이 조각된다고 할 수 없다." — [Lawtalk](https://www.lawtalk.co.kr/posts/176567) (paraphrases; original judgment text not read)
- Practice note: one-off overseas casino visits are often not prosecuted. Prosecution becomes more likely with repeated trips for gambling or with 환치기 (illicit FX) funding. — summarized in search results citing [Kyunghyang](https://www.khan.co.kr/article/201402260009311) and [Lawtalk](https://www.lawtalk.co.kr/posts/66122) (secondary)
- Kangwon Land is the only domestic casino open to Korean nationals. — [Lawtalk](https://www.lawtalk.co.kr/posts/176567) (secondary)
- 방미심위 classified Polymarket as information aiding gambling or a gambling venue under the 형법. This is the closest official Korean characterization of a prediction market. — [Newsis](https://www.newsis.com/view/NISX20260818_0003752716)

### Inferences
- Art. 246 elements are staking property (재물) on an outcome decided by chance (우연). A binary event contract on an election, weather or sports result fits that description on its face. The regulator has already applied this reading to Polymarket. A Korean court would plausibly treat trading Kalshi or offshore crypto prediction contracts the same way, but no court has ruled on this. UNCERTAIN.
- 일시오락 analysis: KRW 42,000 is small in absolute terms. But the stated plan is aggressive and repeated trading aimed at a roughly 1,000x return over a month, by a student with limited wealth. That pattern fits the factors courts weigh against 일시오락 (repetition, stakes relative to wealth) and could support 상습 (Art. 246②). This is an inference, not a finding.
- Art. 3 means that trading from abroad, or with an IP made to look foreign, does not take the conduct outside Korean criminal law for a Korean national. Trading from inside Korea is also covered territorially. I did not fetch Art. 2 text.
- Art. 247 exposure applies to anyone who, for profit, opens a "place or space" for gambling. A TRADEGEN feature that pooled other people's money into prediction markets, or ran a market for others, would raise operator-side risk far beyond user-side risk. This is my inference.

### Gaps
- I did not read the original Supreme Court judgment texts for 99도3337, 2002도2518, 2014도212 or 2011헌마592 (glaw.scourt.go.kr). The holdings above are secondary paraphrases.
- No Korean court decision on event contracts, binary options-style prediction markets, or Polymarket or Kalshi users was found.
- I did not obtain 형법 제2조 text or confirm whether the 2026-09-29 amendment touched Arts. 246-247.
- No statistics were found on prosecution of individual Polymarket users in Korea.

## Q3. National Sports Promotion Act: penalties for users of illegal sports-betting sites, and what is legally available (Sports Toto / Betman, lotteries)

### Takeaway
Under the 국민체육진흥법, only the designated issuer (Sports Toto, sold online only via Betman) may run sports-result betting. A user who bets through any "similar act," including a foreign-operated site accessed from Korea, faces up to 5 years' imprisonment or a KRW 50M fine. That is much heavier than the Criminal Act's gambling fine, and the Supreme Court confirmed in 2022 that it applies to foreign sites. Sports contracts on Kalshi or Polymarket would plausibly be "similar acts"; 방미심위 already cited this Act against Polymarket. Legal options are small and capped: Betman at KRW 100,000 per round, and online Lotto at KRW 5,000 per draw.

### Cited Findings
- **국민체육진흥법 제26조①**: only the designated public corporation and its contractors may issue sports lottery tickets or similar items (online included) and pay out on correct predictions. Anything else is a "유사행위." **제47조2호**: operating in breach is punishable by up to 7 years or KRW 70M. **제48조3호**: "제26조 제1항의 금지행위를 이용하여 도박을 한 자" is punishable by up to 5 years or KRW 50M. — [law.go.kr 판례 2022도6462 (statute text as quoted)](https://law.go.kr/LSW/precInfoP.do?mode=0&precSeq=232585)
- **대법원 2022. 11. 30. 선고 2022도6462**: a person in Korea who bets on an overseas sports betting site is punishable under 제48조3호 **even if a foreigner operates the site from outside Korea**. The court reasoned that online sports betting easily evades regulation by linking to networks in lax jurisdictions. The defendant, who exchanged money and supplied site IDs, was convicted of aiding (방조). — [law.go.kr](https://law.go.kr/LSW/precInfoP.do?mode=0&precSeq=232585); [대법원 판례속보](https://www.scourt.go.kr/portal/news/NewsViewAction.work;jsessionid=3JQE1ANTbZ7t6BQwVaGaDXk4lXhRIuq4OukRCh0oXGICCeHubQwMQoE7wUxtKUEn.BJEUWS05_servlet_SCWWW?pageIndex=1&searchWord=&searchOption=&gubun=4&type=5&seqnum=8942)
- **대법원 2022. 7. 14. 선고 2021도15134**: if the game used is not a "유사행위" (for example a non-sports ladder or odd/even game), 제48조3호 does not apply. Ordinary Criminal Act gambling may still apply. — [CaseNote 2021도15134](https://casenote.kr/%EB%8C%80%EB%B2%95%EC%9B%90/2021%EB%8F%8415134)
- A law-firm blog states that someone who only browses or watches without staking money is not "a person who gambled." — [Daehan Law](https://www.daehanlaw.com/articles/6a2b93a9c159897cddee32de) (secondary). One firm blog gives a 3-year figure for users. That conflicts with the statute text quoted in 2022도6462 (5 years / KRW 50M). — [Ehyun blog](https://blog.ehyun.co.kr/participation-penalties-national-sport-act)
- 방미심위's Polymarket decision expressly relied on the 국민체육진흥법 "유사행위" ground. — [Newsis](https://www.newsis.com/view/NISX20260818_0003752716)
- **Betman (legal)**: since 2025-03-13 the online purchase cap on Betman matches retail at **KRW 100,000 per round** (회차당). Before that, the online cap was KRW 50,000. — [The Fact](https://news.tf.co.kr/read/toto/2184980.htm); [Daum](https://v.daum.net/v/0PSHGq3I7B). Only Sports Toto and Betman are legal; look-alike sites are illegal. — [Ilgan Sports](https://isplus.com/article/view/isp202401310134)
- Proto 승부식 can be bought for as little as **KRW 1,000**. — [Sports Kyunghyang, 2023](https://sports.khan.co.kr/article/202302201513003)
- **Lotto 6/45 online (동행복권)**: **KRW 5,000 per person per draw**, PC and mobile combined. Mobile sales began 2026-02-09 and run weekdays only (Mon 06:00 to Fri 24:00). Total online sales are capped at 5% of the prior year's Lotto sales, and sales can stop when the weekly cap is hit. — [Daum/News1, 2026-02-06](https://v.daum.net/v/20260206134735534); [MTN](https://news.mtn.co.kr/news-detail/2026020616413658375)

### Inferences
- A Kalshi or Polymarket contract on a KBO, EPL or NBA result issues a payout for predicting a sports result, which is close to the 제26조① definition. Under 2022도6462 a user in Korea is exposed to 제48조3호 (up to 5 years or KRW 50M) whoever operates the site. This is the highest-penalty path for a KR-resident user and should be hard-excluded in any tool. This is an inference; no case on event contracts exists.
- The legal options cannot plausibly turn KRW 42,000 into a large sum except through lottery-style odds. Both are capped, and both are negative-expected-value products by design (payout rates not verified here). Neither has leverage.
- Unlike 형법 제246조, the 제48조3호 text quoted in 2022도6462 has no 일시오락 proviso, so a small stake is not an obvious defence. UNCERTAIN: whether courts apply a general 사회상규 (형법 제20조) defence here was not researched.

### Gaps
- I did not fetch the full 국민체육진흥법 text from law.go.kr. The article text above is as quoted inside the 2022도6462 page. The current version and any 2026 amendment were not checked.
- Payout (환급) rates for Sports Toto products and Lotto were not found.
- 연금복권720+ online purchase limit: not found.
- A claimed offline Lotto cap of KRW 100,000 per month per person comes only from a low-quality blog (gusle.kr) and is excluded.

## Q4. Legal and ToS consequences of using a VPN to bypass a geoblock

### Takeaway
I found no Korean statute that criminalizes VPN use as such. A VPN does not change the legal analysis, though: Korean criminal law reaches nationals anywhere (Art. 3), and 2022도6462 focuses on the user's conduct in Korea. On the platform side, Polymarket has reportedly blocked VPN IP ranges and required identity checks since mid-2026. Secondary sources say circumventing a geoblock breaches its ToS and can lead to frozen funds or closure. Kalshi's KYC binds eligibility to residential address, so a VPN would not make a Korean-domiciled user eligible anywhere they are not already.

### Cited Findings
- Polymarket "blocks certain IP addresses tied to VPN services" and asks some users to verify identity. Users with unusually large positions or rapid high-value money cycles get KYC/AML requests. The article does not quote the ToS. — [Gizmodo, 2026-05-30](https://gizmodo.com/polymarket-cracks-down-on-vpn-users-as-legal-pressure-intensifies-in-dozens-of-countries-2000765379)
- Secondary sources state that using a VPN to bypass Polymarket geo-restrictions violates its Terms of Use and can result in frozen funds or permanent account closure. The specific clause is not quoted. One source reports checks for mismatches between IP geolocation and on-chain wallet patterns. — [Benzinga](https://www.benzinga.com/money/best-vpn-for-accessing-polymarket-in-the-u-s); [CardPlayer](https://www.cardplayer.com/poker-news/1664455-like-post-black-friday-online-poker-sites-polymarket-cracks-down-on-vpns)
- Polymarket's docs say orders from blocked regions are rejected and tell developers to check `/api/geoblock` before ordering. — [Polymarket docs](https://docs.polymarket.com/api-reference/geoblock)
- Kalshi restrictions apply to anyone "located or domiciled" in a listed country. KYC requires a live photo ID and a residential address, and may require proof of address or source of funds. — [Coinperps](https://www.coinperps.com/learn/kalshi-restricted-countries-prediction-market-perps)
- 대법원 2022도6462 grounds punishability on the bettor accessing from within Korea, regardless of where the operator is. — [law.go.kr](https://law.go.kr/LSW/precInfoP.do?mode=0&precSeq=232585)
- 방미심위 rejected Polymarket's argument that removing Korean-language service and KRW payments placed it outside Korean law. — [Newsis](https://www.newsis.com/view/NISX20260818_0003752716)

### Inferences
- In Korea a VPN mainly affects whether the 방미심위/ISP block holds technically and whether the platform's ToS is breached. It does not affect whether the underlying betting is lawful under 형법 제246조 or 국민체육진흥법 제48조3호. It may also be read as evidence of knowing evasion. This is my inference.
- Platform risk is concrete for a USD 30 account. A ToS breach found at withdrawal (KYC address = KR) could freeze the whole balance. A tool should treat "VPN + restricted venue" as a hard block, not a configurable option.

### Gaps
- I did not obtain the verbatim VPN clauses of Polymarket's or Kalshi's Terms of Service.
- No Korean statute, court ruling or regulator guidance specifically on VPN use to access blocked gambling sites was found. The absence of a VPN-specific offence is "not found," not "confirmed absent."
- I did not quote 정보통신망법 제44조의7 (the illegal-information provision that the 방미심위 block likely rests on). The fetch returned 제44조 only. The law's latest version is effective 2026-10-02 (법률 제21988호). — [law.go.kr](https://www.law.go.kr/lsLinkProc.do?lsClsCd=L&lsNm=%EC%A0%95%EB%B3%B4%ED%86%B5%EC%8B%A0%EB%A7%9D%20%EC%9D%B4%EC%9A%A9%EC%B4%89%EC%A7%84%20%EB%B0%8F%20%EC%A0%95%EB%B3%B4%EB%B3%B4%ED%98%B8%20%EB%93%B1%EC%97%90%20%EA%B4%80%ED%95%9C%20%EB%B2%95%EB%A5%A0&joNo=004400700&mode=11)
