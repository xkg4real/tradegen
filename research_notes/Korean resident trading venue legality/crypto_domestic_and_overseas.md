# Crypto-asset trading for a Korean resident: domestic VASPs, overseas exchanges, DEX and on-chain venues

Scope note: research run on 2026-10-22/23 for a South Korean national living in Korea (university student, about USD 30 = about KRW 42,000). These notes describe what statutes, regulator releases and platform terms say. They are not legal advice. Many figures come from Korean news or law-firm summaries rather than statute text on law.go.kr, which could not be fetched in this run (law.go.kr / Upbit support pages returned JS shells or HTTP 403). Anything marked **[UNVERIFIED]** or **[MAY HAVE CHANGED]** needs checking against a primary source before software relies on it.

## 1. Domestic VASPs (Upbit, Bithumb, Coinone, Korbit, Gopax): permitted products, coin-lending guideline, ticket size, fees, listing speed

### Takeaway
For an individual, registered Korean exchanges offer KRW spot trading only. There are no futures, perpetuals or margin. The only leverage-like product is coin lending (가상자산 대여), and since 2025-09-05 the FSC/DAXA guideline caps it at collateral value, so there is no leverage beyond 1x. The KRW-market minimum order is KRW 5,000 on both Upbit and Bithumb, so KRW 42,000 allows at most about 8 minimum-size orders. Spot fees run from roughly 0.04% to 0.2% per side.

### Cited Findings
- **No derivatives framework.** Korea has no standard for leveraged or derivative trading inside the crypto market. Leveraged products are not offered domestically, and derivative-permitting bills (late 2025) and the Digital Asset Basic Act (디지털자산기본법, "phase-2 legislation") were still pending in the National Assembly's Political Affairs Committee as of July 2026 — [dealsite](https://dealsite.co.kr/articles/165547); [fnnews 2026-07-22](https://www.fnnews.com/news/202607220842073088); [etoday](https://etoday.co.kr/news/view/2597919); [Herald 2025-12-08 (spot ETF / derivatives bills introduced)](https://www.heraldk.com/article/2025120800062552623). **[MAY HAVE CHANGED]** No source confirmed whether the Basic Act passed between July and October 2026.
- **Lending before the guideline.** Before the guideline, Bithumb lent up to 4x collateral value. Upbit lent up to 80% of collateral across three assets (USDT, BTC, XRP). The FSC had already issued administrative guidance to halt new lending services, and Bithumb kept running its service at a lower multiple — [Kyunghyang 2025-09-05](https://www.khan.co.kr/article/202509051633001).
- **FSC/DAXA coin-lending guideline (가상자산 대여 가이드라인), effective 2025-09-05.** It takes the form of DAXA self-regulation. Its main rules — [Kyunghyang](https://www.khan.co.kr/article/202509051633001); [Digital Today](https://www.digitaltoday.co.kr/news/articleView.html?idxno=590005); [Dealsite](https://dealsite.co.kr/articles/147747); [etoday ("사실상 공매도 금지")](https://www.etoday.co.kr/news/view/2503524):
  - **Leverage ban.** Lending above the collateral's value is banned. So-called "monetary lending" (금전성 대여), where the loan is repaid at its KRW value from the lending date, is also restricted or banned.
  - **Operator's own assets.** Only an exchange lending its own assets may offer the service. Indirect lending through third parties or delegation is not allowed (Digital Today and Dealsite summaries).
  - **Eligible coins.** Only coins in the top 20 by market cap, or listed on at least three KRW-market exchanges.
  - **Per-user cap.** KRW 30 million at first, rising to KRW 70 million under each exchange's internal criteria. The design is modelled on retail stock-borrowing (short-sale) limits.
  - **Education and test.** First-time users must complete DAXA's online course and an aptitude test.
  - **Fee cap.** Fees may not exceed 20% a year, the statutory maximum interest rate.
  - **Liquidation and disclosure.** Users must get advance notice when forced liquidation is likely. Operators must disclose fee structures, real-time lending by asset and monthly forced-liquidation data.
  - **Binding force.** As self-regulation it binds less strongly than law, and the FSC said it would legislate.
- **Minimum order size.** The Upbit KRW market minimum is KRW 5,000, and orders below it are rejected. When available KRW is exactly 5,000, the fee can make even a minimum buy fail — [tokennara blog, 2026-10-09](https://www.tokennara.com/blog/upbit-order-available-krw-short-locked-fee-kimp-2026-10-09). This is a secondary source; Upbit's support page returned 403. Bithumb announced its KRW-market minimum would rise from KRW 500 (limit) / KRW 1,000 (market) to KRW 5,000 for both — [Bithumb notice](https://feed.bithumb.com/notice/1644471). That notice is about two years old. **[UNVERIFIED current]**
- **Fees.** These come from search snippets; individual article dates were not verified. **[UNVERIFIED current]** Sources: [Bloomingbit](https://bloomingbit.io/feed/news/26200); [Blockmedia](https://www.blockmedia.co.kr/archives/167649); [Economist (Gopax 0% event 2022)](https://economist.co.kr/article/view/ecn202205030079).
  - Upbit: 0.05% flat in the KRW market.
  - Bithumb: tiered, with a planned 0.04% rate.
  - Coinone: flat 0.2%, with 0.1% on its growth market.
  - Korbit: 0.2% on taker orders, with a historical maker rebate.
  - Gopax: 0.2%.
- **Registered operators and fee comparison.** Only 28 operators are FIU-registered VASPs, including Upbit, Bithumb and Coinone. The FSC said the five major domestic exchanges average a 0.16% fee, against 1.5% to 10% charged by unregistered OTC desks and overseas exchanges referred to police on 2026-06-10 — [FSC press release 2026-06-24](https://www.fsc.go.kr/no010101/87177).
- **Gopax.** The FIU accepted Gopax's executive-change filing on 2025-10-15, which completed Binance's acquisition — [Herald 2025-10-16](https://www.heraldk.com/article/2025101618140727930). Gopax applied to renew its VASP registration at the end of 2024, and as of 2026 the review was reported as indefinitely delayed pending sanctions — [dealsite](https://dealsite.co.kr/articles/163871); [bizwatch](https://news.bizwatch.co.kr/article/mobile/2025/09/10/0017).
- **Bithumb sanction.** In March 2026 the FIU suspended crypto deposits and withdrawals for new Bithumb customers for six months. The stated reason was 45,772 transactions with 18 unregistered overseas VASPs. Bithumb won an injunction, a hearing was held on 2026-10-22, and the next hearing is set for 2027-01-28.
- **Upbit sanction.** Dunamu (Upbit) won at first instance against a similar FIU sanction. The court held that the law explicitly required blocking only for transfers of KRW 1 million or more. The FIU has appealed — [MTN 2026-10-22](https://news.mtn.co.kr/article/2026102222290942305).
- **Listings and meme coins.** DAXA's common listing review covers investor-risk assessment, whether a token is a security, and money-laundering risk. Each exchange may add its own criteria, and listing and delisting decisions are largely unilateral per exchange — [Tiger Research](https://reports.tiger-research.com/p/korea-cex-listing). After the User Protection Act took effect, Upbit listed four meme coins (BRETT, PEPE, MEW, BONK; reported October 2024), drawing criticism that their issuers are unclear. New listings often hit their high on day one and take months or years to recover — [Dailian](https://dailian.co.kr/news/view/1420378); [Dailian](https://www.dailian.co.kr/news/view/1367349/).

### Inferences
- **No leverage on domestic venues.** On a registered Korean VASP, maximum leverage is effectively 1x. Spot is unlevered. Lending gives at most collateral-sized (≤1x) short-style exposure in top-20 coins, after DAXA education and testing. A strategy needing more than 1x cannot run on a domestic venue.
- **Ticket size.** KRW 42,000 covers about 8 orders of KRW 5,000. A round trip at Upbit's 0.05% costs about 0.1% (about KRW 42 on the full balance). At 0.2% venues the round trip is about 0.4%, which a high-turnover strategy at this size would feel.
- **Listing speed.** Meme coins reach Korean KRW markets only after a project is already established elsewhere. New-listing pumps are a known pattern, but chasing them has no legal edge, and coordinated buying would fall under Section 2.

| Venue / instrument | Status for KR resident | Reachable with KRW 42k | Min ticket | Fees | Max leverage | Basis |
|---|---|---|---|---|---|---|
| Upbit KRW spot | legal | yes | KRW 5,000 | 0.05% | 1x | Registered VASP under 특금법 (FSC 2026-06-24 list) |
| Bithumb KRW spot | legal (new-customer transfer suspension under litigation) | yes | KRW 5,000 [UNVERIFIED current] | ~0.04%–0.25% [UNVERIFIED] | 1x | as above; FIU sanction 2026-03 |
| Coinone / Korbit spot | legal | yes | [UNVERIFIED] | ~0.2% [UNVERIFIED] | 1x | as above |
| Gopax spot | legal_with_conditions (registration renewal pending) | yes | [UNVERIFIED] | ~0.2% [UNVERIFIED] | 1x | renewal delayed (dealsite) |
| Domestic coin lending | legal_with_conditions | unclear (min loan size not found) | n/a | ≤20%/yr | ≤1x of collateral | FSC/DAXA guideline 2025-09-05 (self-regulation) |
| Domestic futures/margin/perps | not offered (no legal framework) | n/a | n/a | n/a | n/a | Basic Act pending |

### Gaps
- Upbit and Coinone support pages for current fees and minimums could not be fetched (403). 2026 fee tables for Bithumb, Coinone, Korbit and Gopax were not found.
- Minimum lending amount and current lending terms for Upbit and Bithumb after the guideline were not found. Whether Bithumb's 4x product was fully withdrawn was not confirmed.
- The minimum age for domestic exchange accounts (commonly said to be 19) was not confirmed from a primary source.
- Upbit's new-listing order restrictions (for example buy limits in the first minutes) and any 2025–2026 DAXA listing best-practice revisions were not found.
- Whether the Digital Asset Basic Act or a derivatives law passed after July 2026 is unknown.

## 2. Virtual Asset User Protection Act (가상자산이용자보호법, effective 2024-07-19): unfair trading rules that bind ordinary users

### Takeaway
Article 10 of the Act bans insider trading on material non-public information, market manipulation (wash or matched trades and manipulative genuine trades) and fraudulent or deceptive trading. The manipulation and fraud bans apply to anyone (누구든지), not only exchanges. That means a retail trader joining a coordinated pump group, wash-trading, or spreading false information to move a coin is within criminal scope. Penalties are at least 1 year in prison or a fine of 3–5x the profit, a penalty surcharge of up to 2x the profit, and civil liability.

### Cited Findings
- **Enactment.** The Act is No. 19563, promulgated 2023-07-18. Article 10 is titled "Prohibition of Unfair Trade Practices", Article 17 "Penalty Surcharges for Unfair Trade Practices" and Article 19 "Penalty Provisions" — [KLRI English translation index](https://elaw.klri.re.kr/kor_service/lawViewTitle.do?hseq=63752). It took effect on 2024-07-19, and the authorities treat MNPI use, manipulation, fraudulent trading and VASP self-issued coin trading as investigation targets — [Blockmedia](https://www.blockmedia.co.kr/archives/601945); [Boannews](https://m.boannews.com/html/detail.html?idx=131600).
- **Article 10 (Shin & Kim summary, 2023-07-05)** — [Shin & Kim newsletter](https://www.shinkim.com/kor/media/newsletter/2152):
  - **10(1):** Trading on material non-public information by insiders and quasi-insiders of VASPs or issuers, and by anyone who received the information.
  - **10(2)–(3):** Price manipulation through wash or matched trades, and manipulation through genuine trades.
  - **10(4):** Anyone (누구든지) is barred from fraudulent means, schemes or devices, false statements on material facts, and use of false prices in connection with crypto trading.
  - **10(5):** VASPs may not trade coins issued by themselves or related parties.
  - **10(6):** Violators of 10(1)–(5) must compensate users for losses.
- **Article 17.** The penalty surcharge is up to 2x the profit made or loss avoided, or up to KRW 4 billion where profit is absent or hard to calculate. Criminal fines paid for the same conduct may be deducted — [Shin & Kim](https://www.shinkim.com/kor/media/newsletter/2152).
- **Article 19.** For violations of 10(1)–(4), the penalty is imprisonment of at least 1 year and a fine of 3–5x the profit. Profit of KRW 5 billion or more brings life imprisonment or at least 5 years. Trading self-issued coins carries up to 10 years — [Shin & Kim](https://www.shinkim.com/kor/media/newsletter/2152). The statute's exact "and/or" wording was not checked on law.go.kr. **[UNVERIFIED wording]**
- **Enforcement process.** After an investigation, the virtual-asset investigation deliberation committee decides among five measures: criminal complaint, referral to investigators, penalty surcharge, warning, or caution — [Blockmedia](https://www.blockmedia.co.kr/archives/601945).
- **Promoters.** Influencers who promote unregistered overseas exchanges for referral fees may face criminal liability — [FSC press release 2026-06-24](https://www.fsc.go.kr/no010101/87177).

### Inferences
- **Hard constraint for software.** Any feature that coordinates buying with other users (Telegram or KakaoTalk pump rooms), places self-matching orders across one's own accounts, spoofs or layers to move price, or publishes misleading signals to profit from them maps onto Articles 10(2)–(4). Because these clauses bind anyone, account size does not matter. The penalty floor (at least 1 year in prison) is severe compared with a KRW 42k stake.
- **Legal at small scale.** Purely individual, information-public momentum or meme-coin trading on a registered exchange is not, on its face, unfair trading.
- **Overseas venues.** Whether these provisions reach trades on overseas venues or DEXs was not confirmed. The Act defines its own territorial scope, which was not read in this run.

### Gaps
- Article text from law.go.kr was not retrieved; findings rely on a 2023 law-firm summary of the bill as passed. Any 2025–2026 amendments (for example higher surcharges or the phase-2 Basic Act folding these rules in) are unknown.
- The extraterritorial reach of Article 10 (the Act's application to conduct abroad affecting the domestic market) was not confirmed.
- No court ruling under Article 10 against a retail participant in a pump group was found.

## 3. Overseas exchanges (Binance, Bybit, OKX, MEXC, KuCoin): 특금법 registration duty, KoFIU blocking, user-side legality, Foreign Exchange Transactions Act, travel-rule withdrawal limits

### Takeaway
Any exchange serving Korean customers must register with the FIU under the 특정금융정보법. Running an unregistered service is a crime for the operator: up to 5 years in prison or a KRW 50 million fine. No statute or case was found that punishes an individual merely for using an unregistered overseas exchange. The state instead attacks access:
- App-store blocks: 17 apps in March 2025, and 29 including OKX and Bybit by July 2026 under Google's January 2026 policy.
- A block on 27 exchange websites on 2026-10-13.
- Sanctions on Korean exchanges that let customers transfer to unregistered venues.
- From 2026-12-03, the amended Foreign Exchange Transactions Act requires VASPs doing cross-border crypto transfers to register and report to the Bank of Korea.

The 2026-08 Enforcement Decree removes the KRW 1M travel-rule threshold. It allows transfers to non-"low-risk" overseas exchanges and to personal wallets only when sender and recipient are the same person. Its effective date is reported inconsistently.

### Cited Findings
- **Registration duty and penalty.** Apart from the 28 FIU-registered operators, any virtual asset business serving Korean customers is illegal, overseas exchanges included. Signs of targeting Korea are a Korean-language site, KRW payments and marketing to Koreans. Unregistered operation carries up to 5 years in prison or a KRW 50 million fine.
  - Under the amended 특금법 (effective August 2026), people involved in unregistered operations are barred from becoming major shareholders of domestic VASPs.
  - Registered VASPs that transact with unregistered operators face fines of up to KRW 100 million per violation.
  - Since May 2024, credit cards cannot be used to buy crypto from unregistered operators.
  - The FSC lists user risks: no user-protection or AML safeguards, hacking and data leaks, exposure to tainted funds that may lead to investigation, and fraud. It tells users to withdraw immediately. The release names no penalty for users.
  - Source: [FSC press release 2026-06-24](https://www.fsc.go.kr/no010101/87177). It cites the 특금법 without article numbers. Commonly cited as Art. 7 (registration) and Art. 17 (penalty). **[UNVERIFIED article numbers]**
- **Website block, 2026-10-13.** At the FIU's request, the media and communications deliberation body (decisions on Oct 6–7) blocked 27 websites of unregistered overseas exchanges, including KuCoin, MEXC, Phemex, XT.com, Bitrue, CoinW, Poloniex, BTCC, BingX and BitMart. Sites on Korean servers are terminated and overseas-hosted sites are blocked for users in Korea. The FIU has referred 44 unregistered VASPs to investigators. Users are told to withdraw immediately and can get DAXA guidance if withdrawals are hard — [Blockhead 2026-10-13](https://www.blockhead.co/2026/10/13/south-korea-blocks-websites-of-27-unregistered-overseas-exchanges-including-kucoin-mexc-bingx/); [Finance Magnates](https://www.financemagnates.com/cryptocurrency/south-korea-blocks-27-crypto-exchange-websites-including-kucoin-bitmart/). A VPN can still reach the sites, and existing accounts are not touched by the decision — [aggregated reports in search results; e.g. cryptoticker](https://cryptoticker.io/en/south-korea-fiu-exchange-block-kucoin-mexc-2026/).
- **App-store blocks.**
  - **March 2025:** At the FIU's request, Google Play restricted new installs and updates of 17 overseas exchange apps (including KuCoin, MEXC, Phemex and BitMart), and Apple later followed — [Blockhead](https://www.blockhead.co/2026/10/13/south-korea-blocks-websites-of-27-unregistered-overseas-exchanges-including-kucoin-mexc-bingx/).
  - **July 2026:** 29 of the top 50 derivatives exchanges, including OKX, Bybit, MEXC and KuCoin, could not be newly installed from Korean Google Play. This follows a voluntary Google policy, in effect since January 2026, that halts distribution of apps not registered as VASPs with the FIU. OKX and Bybit were not on the FIU's referral list but are blocked anyway. Binance's app status was not stated. Web access and existing installs are reportedly unaffected — [BigGo Finance 2026-07-26](https://finance.biggo.com/news/84ec048d-c755-4cb1-9e6a-0d38fddb7920).
- **User-side legality.** A lawyer Q&A states no individual has been criminally punished merely for using an overseas exchange — [Lawtalk Q&A](https://www.lawtalk.co.kr/qna/535672). This is not an official source. Criminal referrals have targeted operators, for example 16 overseas exchanges — [The Fact](https://m.tf.co.kr/amp/economy/1959365.htm).
- **Foreign Exchange Transactions Act amendment (cross-border crypto)** — [Lawtimes / Lin](https://www.lawtimes.co.kr/news/articleView.html?idxno=221409); [Lin newsletter](https://www.law-lin.com/ko/newsletter/1526); [Nate/news 2026-05-26](https://m.news.nate.com/view/20260526n32235); [Lawtimes / BKL draft decree](https://www.lawtimes.co.kr/news/articleView.html?idxno=227951); [Seoul Economic Daily](https://m.sedaily.com/article/20098844):
  - Passed on 2026-05-07 and promulgated on 2026-06-02 as Act No. 21714. It takes effect six months after promulgation, reported as 2026-12-03.
  - A VASP doing cross-border virtual-asset transfer business (가상자산이전업무) must register with the Minister of Economy and Finance (재정경제부) and report transfers to the Bank of Korea's FX data network. Unregistered business carries up to 3 years in prison or a KRW 300 million fine (per search summary).
  - The draft Enforcement Decree, pre-announced on 2026-10-07 with comments until 2026-10-26, brings transfers to and from personal wallets into scope.
  - The source does not establish whether individuals bear direct penalties. **[UNVERIFIED]**
- **환치기 risk.** Whether a crypto-based 환치기 (illegal FX settlement) breaches the FX Act depends on purpose, repetition, business-like character and role. Business-like or laundering-linked activity can expose users too — [Decent Law blog](https://blog.decentlaw.io/crypto-foreign-exchange-law).
- **Travel rule, current.** In force since 2022-03-25, it requires information transfer between Korean VASPs for transfers of KRW 1 million or more — [ktradeatlas summary citing FSC/Bithumb](https://ktradeatlas.com/travel-rule/).
  - Since 2025-02-13, Upbit blocks withdrawals under KRW 1M to unverified destinations, except addresses verified through a travel-rule solution or registered personal wallets — [Digital Times 2025-02-09](https://www.dt.co.kr/article/11644222).
  - Upbit's list as of 2026-06-30, in four tiers — [Upbit support (via search)](https://support.upbit.com/hc/ko/articles/5048002559897):
    - Exchanges linked by a travel-rule solution: allowed.
    - Exchanges with account-owner verification: allowed, but only to one's own account for KRW 1M or more.
    - Registered own personal wallets: allowed.
    - Other addresses: under KRW 1M only, individuals only.
  - A secondary table (Upbit list dated 2026-08-27):
    - Upbit classifies Binance, OKX, Bybit and Bitget as "account-owner verification" venues, and Kraken and Coinbase as "risk-assessed overseas VASPs".
    - Bithumb uses CODE ID Connect or the CODE solution for the same exchanges.
    - Source: [ktradeatlas](https://ktradeatlas.com/travel-rule/). **[UNVERIFIED, secondary]**
- **Travel rule, 2026-08 Enforcement Decree amendment** — [m-economynews 2026-08-11](https://www.m-economynews.com/mobile/article.html?no=69656); [etoday 2026-02-05](https://www.etoday.co.kr/news/view/2553140); [ktradeatlas](https://ktradeatlas.com/travel-rule/); [Daum 2026-07-20](https://v.daum.net/v/20260720185536208):
  - Approved by the Cabinet on 2026-08-11.
  - Removes the KRW 1M threshold, so information duties apply to every transfer.
  - Allows only FIU-assessed "low-risk" overseas exchanges. Other overseas exchanges and personal wallets are allowed only when sender and recipient are the same person, and high-risk transfers are banned.
  - Receiving VASPs must request missing information or reject the transfer.
  - The STR-related duty for transfers of KRW 10M or more was softened after consultation.
  - **Effective date conflict:** m-economynews reports 2026-08-20 for travel-rule items, with some entry requirements in February 2027. ktradeatlas reads the addendum as "6 months after promulgation", which it gives as about February 2027. **[CONFLICTING — confirm from 관보/FIU release]**

### Inferences
- **User-side status.** For the individual user, using Binance, OKX or Bybit (not on the FIU referral list but unregistered in Korea) is best labelled **grey**. No user penalty was found, but the operator is acting unlawfully if it targets Koreans. Access is degraded: no new Google Play installs for OKX and Bybit, and same-name-only transfers.
- **Funding path to Binance, OKX or Bybit.** KRW goes into Upbit, the user buys a coin, and withdraws it to an own account verified by owner match. Secondary sources say a KRW deposit triggers a 24-hour withdrawal hold. **[UNVERIFIED]** This path depends on Upbit continuing to allow those venues. The FSC says registered VASPs transacting with unregistered operators face fines of up to KRW 100M per violation, and the Bithumb sanction shows enforcement. Software should treat this path as revocable without notice.
- **Blocked venues.** For KuCoin, MEXC, BingX, Phemex, BitMart, XT.com, Bitrue, CoinW, Poloniex and BTCC, the status is **grey for the user, but in practice blocked**. Websites are blocked in Korea, apps are blocked, and Korean VASPs are under pressure not to send funds there. Reaching them requires a VPN, which the platforms' own terms may forbid. These venues should not be designed in as primary venues.
- **After 2026-12-03.** Cross-border transfers will run only through FX-Act-registered VASPs with Bank of Korea reporting. Individual transfers abroad will become fully traceable, and Korean VASPs will be able to block more.
- **Leverage on overseas perps.** The maximum leverage these venues offer a Korean user was not confirmed. All are perpetual-futures venues offering high leverage, but at KRW 42k, minimum notional and fees matter more.

| Venue | Status for KR resident (user side) | Reachable with KRW 42k | Min ticket | Fees | Max leverage | Basis |
|---|---|---|---|---|---|---|
| Binance spot/perps | grey (operator unregistered in KR) | unclear (Upbit same-name transfer reportedly allowed; app status unknown) | [UNVERIFIED] | [UNVERIFIED] | [UNVERIFIED] | 특금법 registration duty; FSC 2026-06-24 |
| OKX / Bybit / Bitget | grey; blocked_by_platform for new Google Play installs | unclear (web + same-name transfer reportedly allowed) | [UNVERIFIED] | [UNVERIFIED] | [UNVERIFIED] | Google policy Jan 2026; BigGo 2026-07-26 |
| KuCoin / MEXC / BingX / Phemex / BitMart etc. | grey for user; operator referred for crime; websites blocked 2026-10-13 | no (practically blocked; VPN needed) | n/a | n/a | n/a | 특금법; KCSC block 2026-10-13 |
| Moving crypto abroad (individual) | legal_with_conditions (same-name / low-risk venue; travel rule) | yes, via Upbit/Bithumb | withdrawal fee per coin [UNVERIFIED] | — | — | 특금법 시행령 (2026-08 amendment); FX Act Act No. 21714 eff. 2026-12-03 |
| 환치기 / KRW-for-crypto settlement for others | illegal (FX Act) where business-like | n/a | — | — | — | FX Act (article not confirmed) |

### Gaps
- No primary statute text on law.go.kr was read for the 특금법 article numbers (registration Art. 7 and penalty Art. 17 are assumed from common citation and not confirmed) or for the FX Act Act No. 21714 penalty clauses.
- The full list of the 27 blocked websites, and whether Binance is affected by the Google Play policy, were not found.
- Binance, Bybit and OKX terms of service restricted-jurisdiction lists were not checked in this run. Whether any of them lists South Korea is unknown.
- Whether a user's offshore crypto holdings trigger an overseas financial account report (해외금융계좌 신고, threshold over KRW 500M) is out of scope at this capital size and was not verified.
- The effective date of the 2026-08 Enforcement Decree travel-rule changes is conflicting.

## 4. DEX and on-chain venues (Hyperliquid perps, Solana meme coins via Jupiter or pump.fun, Uniswap): geo-restrictions and Korean legal status

### Takeaway
No source found names South Korea as restricted by Hyperliquid or pump.fun. Hyperliquid's terms reportedly restrict the US, Ontario and sanctioned jurisdictions. Pump.fun's perpetuals (powered by Hyperliquid) are unavailable in the US and some other jurisdictions, and its terms ban VPN evasion and require users to be 18+. Korean law has no explicit rule on an individual using a DEX. These venues are not registered VASPs, so for the user they are grey: no penalty found, no protection, and funding must go through a same-name personal-wallet transfer from Upbit or Bithumb under the travel rule. Hyperliquid-based perps offer up to 40x leverage, the only practical source of more than 1x leverage reachable with KRW 42k. This finding comes from secondary sources and needs primary verification.

### Cited Findings
- **Hyperliquid restrictions.** Secondary sources say Hyperliquid's Terms of Use (cited as Section 1.5) restrict people in the US, Ontario, and jurisdictions under US sanctions or export controls. They say the frontend enforces this by IP geofencing while the L1 protocol itself does not geo-block. One listing puts South Korea among supported Asia-Pacific countries — [Datawallet](https://www.datawallet.com/crypto/hyperliquid-supported-and-restricted-countries); [hyperliquidguide](https://hyperliquidguide.com/privacy/hyperliquid-us-availability); [CoinPerps](https://www.coinperps.com/learn/hyperliquid-restricted-countries). Hyperliquid's own terms text was not retrieved. **[UNVERIFIED primary]**
- **Pump.fun terms (last updated 2026-10-17)** — [pump.fun Terms](https://pump.fun/docs/terms-and-conditions):
  - Users must be at least 18 and of legal age in their jurisdiction (§2.1).
  - Using VPNs, proxies or geolocation spoofing to evade jurisdictional or sanctions controls is banned (§21(v)).
  - The Perpetuals Feature is provided via Hyperliquid and is "not available to persons in the United States or certain other jurisdictions". Pump may enforce this with IP, device and wallet signals (§1.6, §30B).
  - The "Prohibited Jurisdiction" list in §32 was in the part of the page not read, so whether it names Korea is unconfirmed. **[UNVERIFIED]**
- **Pump.fun perps leverage.** Pump.fun launched Hyperliquid-powered perpetual futures with up to 40x leverage, also restricted in Ontario — [Bitcoin.com](https://news.bitcoin.com/featured/pump-fun-brings-hyperliquid-perps-to-its-meme-coin-empire/); [BigGo Finance](https://finance.biggo.com/news/0d74032b-8651-46fb-8db3-725b96088101).
- **Funding from Korea.** Upbit permits withdrawals to the user's own registered personal wallet. Under the 2026-08 decree amendment, personal-wallet transfers are allowed only when sender and recipient are the same person, and the new FX Act decree draft brings personal-wallet transfers into its monitoring scope — [Upbit support (via search)](https://support.upbit.com/hc/ko/articles/5048002559897); [m-economynews](https://www.m-economynews.com/mobile/article.html?no=69656); [Lawtimes / BKL](https://www.lawtimes.co.kr/news/articleView.html?idxno=227951).
- **DEXs as a tax gap.** Lawmakers and industry cite overseas exchanges and DEXs as tax blind spots — [Money Today 2026-10-21](https://www.mt.co.kr/politics/2026/10/21/2026102114272831035).

### Inferences
- **Legal status.** Hyperliquid, Jupiter or pump.fun and Uniswap all count as **grey** for a Korean user. No Korean statute bans individual use, and the Korean regulatory perimeter (특금법 registration, the User Protection Act) is built around intermediaries. A DEX frontend is not a registered VASP, so the user gets no protection, and any service targeting Koreans may itself be unregistered.
- **Market manipulation.** Article 10 of the User Protection Act makes no exception for on-chain trading. Manipulative behaviour such as coordinated pump.fun launches or wash trading is risky whatever the venue, but extraterritorial reach is unconfirmed.
- **Reachability with KRW 42k.** The path is Upbit, then a coin such as USDC, SOL or USDT on a cheap network, then a self-registered wallet, then the DEX. Fixed withdrawal and gas costs could take a few percent of the stake. On-chain meme coins are reachable at almost any ticket size, while Hyperliquid perps are reachable if its minimum order notional (believed about USD 10, unverified) fits.
- **Leverage.** On-chain perps are the only route to more than 1x for this person. Up to 40x is advertised for pump.fun or Hyperliquid perps, with leverage varying by asset.

| Venue | Status for KR resident | Reachable with KRW 42k | Min ticket | Fees | Max leverage | Basis |
|---|---|---|---|---|---|---|
| Hyperliquid perps | grey (Korea not reported restricted; not a KR-registered VASP) | yes (via own wallet) | [UNVERIFIED ~USD 10 notional] | [UNVERIFIED] | up to 40x on major assets (via pump.fun integration report) | HL ToS §1.5 per secondary sources; 특금법 perimeter |
| pump.fun spot meme coins | grey; 18+; VPN evasion banned | yes | none found | [UNVERIFIED] | 1x (spot) | pump.fun Terms 2026-10-17 |
| pump.fun perps | grey; may be geo-restricted for "certain other jurisdictions" | unclear | [UNVERIFIED] | [UNVERIFIED] | up to 40x | pump.fun Terms §1.6, §30B |
| Jupiter (Solana) | grey / unknown | yes | none found | [UNVERIFIED] | [UNVERIFIED] | terms not checked |
| Uniswap | grey / unknown | yes, but Ethereum L1 gas may exceed the stake; L2s cheaper | none | [UNVERIFIED] | 1x | terms not checked |

### Gaps
- Primary terms of use were not read for Hyperliquid, Jupiter or the Uniswap Labs interface. Pump.fun's §32 prohibited-jurisdiction list was not read.
- No Korean regulator statement specifically on individual DEX use was found. Whether the FIU treats DEX frontends serving Koreans as unregistered VASPs is unknown.
- Hyperliquid minimum order size, fees and per-asset leverage caps were not confirmed from Hyperliquid documentation.

## 5. Tax: virtual-asset income tax start date and current treatment; spot crypto ETFs in Korea

### Takeaway
Under current law, individuals' gains from trading virtual assets are taxed from 2027-01-01 at 22% (20% plus local tax) on annual gains above KRW 2.5 million, with the first filing in May 2028. Until then, gains are not taxed under this regime. The government's August 2026 tax plan contained no further delay. As of the 2026-10-21/22 audit, however, a fourth postponement is live:
- a 2-year delay bill from Democratic Party lawmaker 박민규 (filed 2026-10-16);
- the PPP's party-line position for delay;
- abolition and 2029/2030 bills.

The outcome will be settled in the year-end tax bill deliberation and is undecided as of this research. Korea has no spot crypto ETFs. The FSC plans to amend the Capital Markets Act in H2 2026 to make virtual assets eligible ETF underlyings, but no passage was found as of September 2026.

### Cited Findings
- **Tax rules under current law.** The tax was introduced in 2020 and postponed three times. Under current law it starts 2027-01-01 at 20% + 2% local tax on annual gains over KRW 2.5 million. Because the start date is fixed in statute, taxation begins automatically unless the National Assembly passes another delay — [Money Today 2026-10-21](https://www.mt.co.kr/politics/2026/10/21/2026102114272831035); [Bloter](https://www.bloter.net/news/articleView.html?idxno=669414); [Upbit Datalab briefing](https://datalab.upbit.com/intelligence/ai-news-briefing/topics/11183).
- **2026 tax plan.** It excluded any postponement. Example: a KRW 5 million gain leaves KRW 2.5 million taxable, about KRW 550,000 in tax. First filing is May 2028 — [Asiae via Nate 2026-08-03](https://m.news.nate.com/view/20260803n28191).
- **Postponement fight, October 2026** — [Money Today](https://www.mt.co.kr/politics/2026/10/21/2026102114272831035); [fnnews 2026-10-21](https://www.fnnews.com/news/202610211506422932); [Dailian](https://www.dailian.co.kr/news/view/1704897/2026-%EA%B5%AD%EA%B0%90-%EA%B0%80%EC%83%81%EC%9E%90%EC%82%B0-%EA%B3%BC%EC%84%B8-%EB%82%B4%EB%85%84-%EC%8B%9C-2026); [Asiae 2026-10-22](https://view.asiae.co.kr/article/2026102211553183551); [Polinews](https://www.polinews.co.kr/news/articleView.html?idxno=746579); [HuffPost Korea](https://www.huffingtonpost.kr/article/261464):
  - DP lawmaker 박민규 filed a 2-year postponement bill on 2026-10-16.
  - The PPP adopted postponement as its party line. PPP lawmaker 송언석 filed an abolition bill, and 김상훈 and 정성국 filed bills delaying the start to 2029 and 2030.
  - The ruling DP leans towards implementing on schedule.
  - At the 2026-10-22 audit, the Deputy PM / Finance Minister said he would decide after weighing all views, and the FSC chair said views are being collected.
  - The implementing notice (고시) is to be finalised by the end of October.
  - Per DP lawmaker 박수영's office, no exchange has finished building its tax-reporting system.
  - **[MAY HAVE CHANGED after 2026-10-22]**
- **Spot ETFs.** In its "H2 2026 economic growth strategy" (2026-07-14), the FSC said it would amend the Capital Markets Act to add virtual assets to eligible ETF underlyings. Under current law, ETF underlyings are limited to financial investment products and currencies, so domestic spot BTC ETFs are impossible. An FSC interpretation and trust-business rules also block them. Even after amendment, custody, pricing, manager authorisation and KRX listing review are still needed, so launch timing is uncertain — [Hankyung 2026-07-14](https://www.hankyung.com/article/2026071450031); [Seoul Economic TV](https://www.sentv.co.kr/article/view/sentv202607160105); [etoday](https://www.etoday.co.kr/news/view/2604026); [Bizwatch 2026-07-15](https://news.bizwatch.co.kr/article/mobile/2026/07/15/0014); [Nate 2026-09-01](https://m.news.nate.com/view/20260901n33876).

### Inferences
- **Tax at this capital size.** For a KRW 42k account, the KRW 2.5M annual deduction means tax is irrelevant unless gains exceed it. Even so, from 2027 (if not postponed), software should log acquisition cost and disposal per lot for a May 2028 filing. Overseas and DEX gains would be self-reported, and lawmakers flag these as blind spots likely to draw scrutiny.
- **ETFs not a 2026 venue.** Spot crypto ETFs are not available in Korea in 2026. A securities-account route to BTC exposure (for example leveraged ETFs) depends on legislation not yet passed.

### Gaps
- The final decision on the 2027 start (postpone or keep) was unknown as of 2026-10-22, and will likely be decided in the December 2026 tax-law vote.
- The acquisition-cost rule (for example a deemed cost based on the 2026-12-31 price) and the 2027 notice details were not verified.
- Whether Korean brokers may currently broker US-listed spot BTC ETFs to retail investors was not verified in this run. Earlier FSC guidance (2024) discouraged it, from memory only. **[UNVERIFIED]**
- Whether the Capital Markets Act ETF amendment was introduced or passed after September 2026 was not found.
