# Other assets and markets for a Korean-resident retail quant — outside KIS, or non-obvious inside it

Researched 2026-09-25 for QUANTGEN (`C:\Users\whydi\OneDrive\Desktop\QUANTGEN`, Python 3.13 / Flet, read-only, daily frequency). Scope: markets a Korean resident could plausibly trade that the KIS Open API does not reach (IBKR products, FX margin, prediction markets, KRX gold/carbon, CEFs, merger/SPAC/convertible arbitrage, VIX products) plus a few reachable through KIS that are non-obvious (KRX gold, KOSPI200 box spreads, ex-dividend capture, IPOs, dividend-index futures, REITs, ELS as an analysis object). Every legal statement carries a source and a date; anything not confirmed is marked UNVERIFIED. Web-search budget ran out after the third round, so the last fetches were done through the browser pane and local PDF parsing; gaps from that are listed per section.

Conventions used below: "KIS-domestic" = KRX cash/derivatives through the existing KIS key; "KIS-overseas-stock" and "KIS-overseas-futopt" = the `[해외주식]` and `[해외선물옵션]` categories that exist on the KIS API portal ([KIS Open API portal](https://apiportal.koreainvestment.com/apiservice), fetched 2026-09-25: categories `[해외주식]`, `[해외선물옵션]`, `[국내선물옵션]`, `[장내채권]`; named endpoints include `해외주식 기간별시세`, `해외주식 현재가상세`, `해외주식 분봉조회`, `해외선물 분봉조회`, `해외선물 체결추이(일간)`). QUANTGEN's README currently routes KIS only for KRX daily OHLCV, so "reachable via KIS-overseas-*" means the endpoint exists on the portal, not that the app is wired to it.

---

## 1. Interactive Brokers for Korean residents (2026)

### Takeaway
IBKR's own "Available Countries and Territories" list includes "Republic of Korea" (checked 2026-09-25), and its API stack (TWS API / IB Gateway + `ib_async`, Client Portal Gateway) is fully usable read-only — but Korean foreign-exchange regulation (외국환거래규정 제7-33조 제4항) requires a general (individual) investor to route foreign-currency securities trades through a domestic 투자중개업자, and IBKR itself bars Korean residents from KRX equities. Trading foreign securities directly on an offshore account is therefore a regulatory-grey-to-illegal channel for an individual; holding such an account also triggers the 5억원 해외금융계좌 reporting duty. Recommendation: document IBKR as a data/API reference only; do not build QUANTGEN surfaces on it.

### Cited Findings
- IBKR LLC's country list, read in the browser on 2026-09-25, lists "Republic of Korea" among available countries (page title "Available Countries and Territories | Interactive Brokers LLC"; the list is alphabetical and also includes Japan, Hong Kong SAR, Singapore, Taiwan, China; footnote "Excluding Hedge Fund accounts") — [IBKR country list](https://www.interactivebrokers.com/en/accounts/open-account-country-list.php). Which IBKR entity (LLC vs Hong Kong) actually carries a Korean-resident account is not stated on that page — UNVERIFIED.
- IBKR press release dated 2026-05-06 (read via a mirror because interactivebrokers.com returned HTTP 403 to the fetch tool): "Access to equities on the Korea Exchange through Interactive Brokers is not available to residents of Korea, clients of Interactive Brokers Securities Japan Inc., or clients of Interactive Brokers India Pvt. Ltd." The same feed lists "Interactive Brokers Announces Strategic Collaboration with Daol Investment & Securities" dated 2026-08-24 — [StockTitan mirror of IBKR release](https://www.stocktitan.net/news/IBKR/interactive-brokers-launches-access-to-korean-equities-breaking-new-d3fbed2a40vi.html); original at [IBKR media relations 5-7-26](https://www.interactivebrokers.com/en/general/about/mediaRelations/5-7-26.php) (403 to fetch; UNVERIFIED text-for-text).
- Korean FX rule: KCMI Issue Report 23-01 (장근혁·이승호·김한수, PDF created 2022-12-29), p. 16: "외국환거래규정 제7-33조 제4항'에 의해 일반투자자(보통 개인투자자)가 외화증권을 매매하고자 하는 경우에는 증권사(투자중개업자)를 통해 외화증권의 매매를 위탁하여야 한다. 다만, 기관투자자는 이러한 의무대상에 포함되지 않는다." The same page notes investors can "해외 중개기관을 통해 직접 외화증권을 거래할 수 있어 국내 증권사의 역할이 배제되는 경우가 발생" — [KCMI Issue Report 23-01 PDF](https://www.kcmi.re.kr/common/downloadw?fid=25767&fgu=002002&fty=004003).
- Bank of Korea FX-reporting FAQ, item "거주자의 해외주식 취득절차는?": "일반투자자의 경우 투자중개업자등을 통하여 외화증권의 매매를 위탁하여 외국 유가증권시장에 상장되어 있는 증권이나 외국정부등이 발행한 국공채등에 투자할 수 있음" — [BOK 외환거래별 신고 FAQ](https://www.bok.or.kr/portal/bbs/B0000267/list.do?menuNo=200796&pageIndex=3).
- 외국환거래규정 in force from 2024-06-28 (latest amendment shown on the statute page; article text not extractable by the fetch tool) — [국가법령정보센터 외국환거래규정](https://www.law.go.kr/admRulLsInfoP.do?admRulSeq=2100000243188&vSct=%EC%99%B8%EA%B5%AD%ED%99%98%EA%B1%B0%EB%9E%98%EA%B7%9C%EC%A0%95).
- Offshore FX dealing by individuals is stated as illegal by KOFIA: "개인은 국내 투자중개업자를 경유하여 FX마진거래를 하여야 하며 … 해외 금융투자업자와 직접 거래하는 것은 불법", citing 자본시장법 and 외국환거래법령; unlicensed intermediary-site operators face up to 5 years' imprisonment — [KOFIA FX마진불법거래 유형](https://www.kofia.or.kr/wpge/m_75/sub03040403.do).
- 해외금융계좌 신고: any resident whose aggregate overseas financial-account balance exceeded 5억원 on any month-end of the prior year must file between 1–30 June; covers "현금, 주식, 채권, 집합투자증권, 보험상품, 가상자산을 포함한 모든 자산"; penalty 10% of the unreported amount (cap 10억원); above 50억원 criminal liability (up to 2 years or a 13–20% fine); legal basis 국제조세조정에 관한 법률 제52조~제57조, 제90조 — [국세청 해외금융계좌 신고](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?cntntsId=7819&mi=2513); the 2026 filing covered 2025 month-ends and closed 2026-06-30 — [조세일보 2026-06-04](https://www.joseilbo.com/news/htmls/2026/06/20260604569417.html).
- Overseas stock capital gains: 22% (20% + 2% local) on net gains above a 250만원 annual deduction, self-filed in May — [서울신문 2026-03-26](https://www.seoul.co.kr/news/economy/securities/2026/03/26/20260326032001); overseas futures/derivatives gains are taxed under the same 22% / 250만원 규정 per a secondary guide — [stylelife 2026 guide](https://stylelife.kr/2026-%ED%95%B4%EC%99%B8%EC%84%A0%EB%AC%BC-%EC%96%91%EB%8F%84%EC%86%8C%EB%93%9D%EC%84%B8-%EC%8B%A0%EA%B3%A0%EB%B0%A9%EB%B2%95%EF%BD%9C%ED%99%88%ED%83%9D%EC%8A%A4%C2%B7%EC%86%90%ED%83%9D%EC%8A%A4/) (secondary; the exact derivative rule text was not fetched — UNVERIFIED).
- Market data at IBKR (page read in browser 2026-09-25): "IBKR clients receive free real-time streaming market data on all US-listed stocks and ETFs from Cboe One and IEX (Non-consolidated)", "free delayed market data on other products where available", "up to 100 free snapshot quotes per month"; subscriptions are not pro-rated; non-professional subscriber definition given — [IBKR Market Data Pricing](https://www.interactivebrokers.com/en/pricing/market-data-pricing.php). A search-result summary put the "US Securities Snapshot and Futures Value Bundle" at USD 10/month, waived at USD 30 of monthly commissions — that figure was not visible in the fetched page text (collapsed table) — UNVERIFIED.
- `ib_async` (successor to `ib_insync`, renamed after the original author's death in 2024) needs TWS or IB Gateway running with the API port enabled and Python ≥ 3.10; implements the IBKR binary protocol itself; read-only calls include `reqHistoricalData()`, `positions()`, `accountSummary()`, `reqMktData()` — [ib_async README](https://github.com/ib-api-reloaded/ib_async).
- The legacy TWS API docs carry: "This documentation is now deprecated. Please switch to the IBKR Campus"; `reqHistoricalData` takes `durationStr`, `barSizeSetting`, `whatToShow` (TRADES/MIDPOINT/BID/ASK/SCHEDULE) — [TWS API historical bars (legacy)](https://interactivebrokers.github.io/tws-api/historical_bars.html).
- Client Portal Web API: per IBKR's docs summary, retail clients are approved to use the Web API only through the Client Portal Gateway; OAuth 1.0a is institutional; OAuth 2.0 for individuals is "being considered"; OAuth requires a funded IBKR Pro account — [IBKR Web API docs](https://www.interactivebrokers.com/campus/ibkr-api-page/webapi-doc/) (search-result summary; page returned 403 to the fetch tool — UNVERIFIED verbatim).
- Products: a Korean-resident IBKR account's product permissions (US options, futures, spot FX, bonds; CFDs) could not be verified from any IBKR page (403) — UNVERIFIED. IBKR's own FAQ on CFDs by residency was not reachable.

### Inferences
- Opening an IBKR account is possible on paper (Korea is on the list); executing foreign-securities trades on it as an individual conflicts with 외국환거래규정 제7-33조 제4항 as summarised by KCMI and the BOK FAQ. The safe reading for QUANTGEN is: IBKR = documentation only; no data surface depends on it.
- Even a purely read-only use would require a funded account for paid subscriptions, so the "keyless data" test fails; everything IBKR would give (US stocks/ETFs EOD, futures settlements) is available keylessly elsewhere (Yahoo, Cboe CSV, FRED).

### Gaps
- Which IBKR entity onboards Korean residents and what products it enables (CFDs, spot FX, bonds) — pages 403 to the fetch tool; browser read of the country list only.
- Exact text of 외국환거래규정 제7-33조 제4항 (only quoted through KCMI and the BOK FAQ).

---

## 2. FX margin trading and FX strategies beyond the carry basket

### Takeaway
Domestic, KOFIA-regulated FX margin still exists (10% margin, USD 10,000 lots, KRX-brokered) but the market has shrunk >70% since 2020 and KIS and Shinhan exited by early 2025, leaving Hana, Kiwoom and Samsung Futures (status as of 2024-07; 2026 status UNVERIFIED). Offshore OANDA/IG/Saxo accounts are illegal for a Korean individual per KOFIA. For QUANTGEN the FX work should stay in data-and-model mode: FRED H.10 and Yahoo give daily spot; Dukascopy gives free tick history; the academic canon (Fama 1984; Menkhoff–Sarno–Schmeling–Schrimpf JF 2012, JFE 2012, RFS 2017; Lustig–Roussanov–Verdelhan JFE 2014) gives three verified strategy families — FX momentum, FX value, dollar carry — that extend the existing G10+KRW carry basket with the same no-look-ahead backtest.

### Cited Findings
- KOFIA definition page: FX margin is an OTC 외국환거래 under US futures-association or Japanese commodity-exchange rules; standard contract "100,000단위"; "거래대금의 5%" initial margin is quoted on that (generic) page; it is a 장내파생상품 under 자본시장법 제5조; "FX마진거래는 거래소에 의해서 보증되지 않으므로" counterparty (FDM) risk exists — [KOFIA FX마진거래의 정의와 거래구조](https://www.kofia.or.kr/wpge/m_73/sub03040401.do). Note the Korean rule is 10% (see next item); the 5% on KOFIA's page describes the pre-2012 / generic structure.
- Consumer News 2024-07-17: margin rate 10% (raised from 5% in 2012), minimum USD 10,000 initial margin per contract; volume fell from USD 109.1bn (2020) to USD 31.4bn (2023), H1-2024 USD 12bn (−31.0% y/y); 61–73% of accounts loss-making in Q2 2024; Shinhan ended service March 2024; KIS stops new orders/accounts 2024-12-16 and fully terminates 2025-01-16; remaining providers Hana Securities, Kiwoom Securities, Samsung Futures — [소비자가 만드는 신문 2024-07-17](https://www.consumernews.co.kr/news/articleView.html?idxno=710422).
- Offshore direct dealing illegal for individuals; laws cited 자본시장법, 외국환거래법령; operators of unlicensed intermediary sites face up to 5 years — [KOFIA FX마진불법거래 유형](https://www.kofia.or.kr/wpge/m_75/sub03040403.do). FSS/KOFIA joint sweep found 27 firms suspected of unlicensed futures business (2010) — [한국일보 2010-09-05](https://www.hankookilbo.com/news/article/201009051297749454).
- OANDA v20 REST: "To use this API you must have a v20 trading account"; a personal access token is generated in the account portal; practice host `https://api-fxpractice.oanda.com`, live `https://api-fxtrade.oanda.com`; rate limit "120 requests per second … applied against the requesting IP address"; historical pricing back to 2005 — [OANDA v20 introduction](https://developer.oanda.com/rest-live-v20/introduction/), [development guide](https://developer.oanda.com/rest-live-v20/development-guide/). Candles endpoint `v3/instruments/{instrument}/candles` — [oandapyV20 docs](https://oanda-api-v20.readthedocs.io/en/latest/endpoints/instruments/instrumentlist.html).
- Dukascopy: free historical export "through Dukascopy's Historical Data Export tool", from tick to monthly, via JForex demo/live login — [Dukascopy historical data page](https://www.dukascopy.com/swiss/english/marketwatch/historical/); community clients read the same public feed without an account: [dukascopy-node](https://github.com/Leo4815162342/dukascopy-node), [dukascopy-python (PyPI)](https://pypi.org/project/dukascopy-python/).
- FRED H.10: 33 daily series, e.g. DEXKOUS (KRW per USD, noon buying rates in NY, Board of Governors) — [FRED DEXKOUS](https://fred.stlouisfed.org/series/DEXKOUS), [H.10 release on FRED](https://fred.stlouisfed.org/release?rid=17).
- Fama (1984), "Forward and spot exchange rates", Journal of Monetary Economics 14(3), 319–338: forward rates have little forecast power for future spot; the regression of depreciation on the forward premium gives a negative slope (the "Fama puzzle") — [IDEAS entry](https://ideas.repec.org/a/eee/moneco/v14y1984i3p319-338.html).
- Menkhoff, Sarno, Schmeling, Schrimpf (2012a), "Carry Trades and Global Foreign Exchange Volatility", Journal of Finance 67(2), 681–718: carry returns load on global FX volatility risk — [IDEAS entry](https://ideas.repec.org/a/bla/jfinan/v67y2012i2p681-718.html).
- Menkhoff, Sarno, Schmeling, Schrimpf (2012b), "Currency momentum strategies", Journal of Financial Economics 106(3), 660–684: winner-minus-loser spread "up to 10% per annum", not explained by standard risk factors, partly by transaction costs, consistent with under-/over-reaction — [IDEAS entry](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p660-684.html), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1988679).
- Menkhoff, Sarno, Schmeling, Schrimpf (2017), "Currency Value", Review of Financial Studies 30(2), 416–441: real exchange rates predict the cross-section of currency excess returns; adjusting RER for productivity, export quality, NFA and output gap isolates the premium — [IDEAS entry](https://ideas.repec.org/a/oup/rfinst/v30y2017i2p416-441..html).
- Lustig, Roussanov, Verdelhan (2014), "Countercyclical currency risk premia", Journal of Financial Economics 111(3), 527–553: the "dollar carry trade" (long all foreign currencies vs USD when the average forward discount is positive, short otherwise) earns large excess returns uncorrelated with standard carry; the average forward discount and US industrial-production growth forecast up to 25% of dollar-return variation at the one-year horizon — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X1300305X), [NBER w16427](https://www.nber.org/papers/w16427).

### Inferences
- Execution for a Korean retail quant, if ever, would be KRX currency futures (USD/JPY/EUR/CNH futures under KIS-domestic 국내선물옵션) or the three remaining FX-margin brokers; neither is needed for a read-only app. QUANTGEN's carry-basket engine already has the forward-implied excess-return bookkeeping needed for momentum, value and dollar carry.
- A practice (demo) OANDA token used only to pull candles is not "trading with an overseas dealer" in KOFIA's sense, but it is not keyless either; Dukascopy's public feed and FRED are the keyless substitutes.

### Gaps
- 2026 status of Hana/Kiwoom/Samsung Futures FX margin services (last verified 2024-07).
- No fetch of Saxo/IG Korea-specific terms (search budget exhausted); their legality for a Korean individual follows the KOFIA statement regardless.

---

## 3. Closed-end fund discounts (US-listed CEFs)

### Takeaway
The evidence (Lee–Shleifer–Thaler 1991; Pontiff 1995, 1996) is strong and old; US CEFs are ordinary NYSE/NASDAQ listings, so they are reachable through KIS-overseas-stock at daily frequency. The binding constraint is data: prices are keyless (Yahoo), but no documented keyless NAV feed was found (CEFConnect has screens and daily-pricing pages but no public API; CEFA's universe file is on paid Nasdaq Data Link).

### Cited Findings
- Lee, Shleifer, Thaler (1991), "Investor Sentiment and the Closed-End Fund Puzzle", Journal of Finance 46(1), 75–109: discounts co-move across funds, new funds start when seasoned funds trade at premia/small discounts, discounts narrow when small stocks do well — [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1991.tb03746.x), [IDEAS](https://ideas.repec.org/a/bla/jfinan/v46y1991i1p75-109.html).
- Pontiff (1996), "Costly Arbitrage: Evidence from Closed-End Funds", Quarterly Journal of Economics 111(4), 1135–1151: mispricing is larger for funds hard to replicate, paying smaller dividends, with lower market value, and when interest rates are high; these explain about a quarter of cross-sectional variation — [OUP](https://academic.oup.com/qje/article-abstract/111/4/1135/1932203), [author PDF](https://www2.bc.edu/jeffrey-pontiff/Documents/5_costly_arb_QJE.pdf).
- Pontiff (1995), "Closed-end fund premia and returns: Implications for financial market equilibrium", Journal of Financial Economics 37(3), 341–370 (bibliographic record only; abstract not on the page) — [IDEAS](https://ideas.repec.org/a/eee/jfinec/v37y1995i3p341-370.html).
- Data: CEFConnect (Nuveen, Morningstar-supplied) offers a screener and a daily-pricing page — [CEFConnect](https://www.cefconnect.com/), [daily pricing](https://www.cefconnect.com/closed-end-funds-daily-pricing); CEFA "Closed-End Fund Universe Report" (100% of US-listed CEFs, daily after 2018-09-14) is a paid Nasdaq Data Link database — [CEFUR](https://data.nasdaq.com/databases/CEFUR); CEF Advisors' cefdata.com publishes downloadable resources — [cefdata.com](https://cefdata.com/cef-data-page).

### Inferences
- The strategy needs P and NAV daily. Prices via `yfinance`; NAV requires either scraping CEFConnect (terms not checked — UNVERIFIED) or the fund sponsors' pages. Until a keyless NAV source is confirmed, this is a "document + price-only" surface.
- KIS-overseas-stock lists US common stock; CEFs are common stock, so tradability is a reasonable inference but not verified per ticker.

### Gaps
- A keyless, documented CEF NAV endpoint — none found.
- Whether KIS blocks any CEF tickers — UNVERIFIED.

---

## 4. Merger arbitrage, SPAC arbitrage, convertible arbitrage

### Takeaway
Merger arbitrage (Mitchell–Pulvino 2001) and SPAC arbitrage (Klausner–Ohlrogge–Ruan 2022; Gahng–Ritter–Zhang 2023) are executable in US common stock at daily frequency through KIS-overseas-stock, and the deal-document data is keyless through SEC EDGAR full-text search. Convertible arbitrage needs the bonds themselves, which are not reachable via KIS and have no keyless price feed — document only.

### Cited Findings
- Mitchell & Pulvino (2001), "Characteristics of Risk and Return in Risk Arbitrage", Journal of Finance 56(6), 2135–2175: 4,750 mergers 1963–1998; returns positively correlated with the market in severely falling markets and uncorrelated otherwise, i.e. like selling uncovered index puts; after transaction costs, excess returns of about 4% per year — [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00401), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=268144).
- Klausner, Ohlrogge & Ruan (2022), "A Sober Look at SPACs", 39 Yale Journal on Regulation 228: costs embedded in the SPAC structure are opaque and higher than an IPO's; SPACs raise USD 10 per share but "by the time the median SPAC merges with a target, it holds just $6.67 in cash for each outstanding share" — [Yale J. Reg.](https://www.yalejreg.com/print/a-sober-look-at-spacs/), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3720919).
- Gahng, Ritter & Zhang (2023), "SPACs", Review of Financial Studies 36(9), 3463–3501: SPAC IPO investors and sponsors "have earned remarkably high annualized average returns", while post-merger public investors earned very low market-adjusted returns on an equal-weighted basis — [OUP](https://academic.oup.com/rfs/article-abstract/36/9/3463/7067751), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3775847).
- Agarwal, Fung, Loon & Naik (2011), "Risk and return in convertible arbitrage: Evidence from the convertible bond market", Journal of Empirical Finance 18(2), 175–194: a buy-and-hedge (long convertible, hedge equity) strategy explains much of convertible-arbitrage hedge-fund returns; supply of convertibles and extreme market events matter — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=885945).
- EDGAR full-text search API returns JSON: `GET https://efts.sec.gov/LATEST/search-index?q="agreement and plan of merger"&forms=DEFM14A` → keys `took, timed_out, _shards, hits, aggregations, query`; 4,597 total hits at fetch time; hit fields include `ciks, period_ending, file_num, display_names, file_date, form, biz_states, sics, inc_states, file_type, file_description` — [efts.sec.gov](https://efts.sec.gov/LATEST/search-index?q=%22agreement%20and%20plan%20of%20merger%22&forms=DEFM14A).
- Ritter's IPO-data page (updated 2026-03-09) hosts "IPOs 2025 SPACs", "SPACs.pdf" (the RFS paper), "IPOs-Korea.pdf" (1980–2025), "IPOs-International.pdf" (2026 update, 55 countries), "IPOALL.xlsx" (monthly IPO counts and first-day returns 1980–2025) — [Ritter IPO Data](https://site.warrington.ufl.edu/ritter/ipo-data/).

### Inferences
- Merger arb at daily frequency is feasible in read-only mode: EDGAR gives deal announcements (8-K/DEFM14A), Yahoo gives target/acquirer closes, the spread and an implied completion probability can be computed daily. The engineering is the deal parser, not the model.
- SPAC pre-deal arbitrage (buy below trust value, redeem or sell on announcement) is the low-risk leg documented by Gahng–Ritter–Zhang; whether KIS lists SPAC units/warrants (as opposed to common) is UNVERIFIED.
- Convertible arbitrage: no bond access (KIS overseas categories are stocks and futures/options), no keyless convertible pricing — document only.

### Gaps
- Keyless daily merger-spread dataset (none; must be built from EDGAR + prices).
- KIS overseas tradability of SPAC units/warrants and of any specific CEF — UNVERIFIED.

---

## 5. KRX gold, ETN/leveraged-ETP rules, KAU carbon, Korean IPOs, ex-dividend capture, KOSPI200 box spreads, dividend-index futures

### Takeaway
KRX gold is retail-accessible through a 금현물 계좌 at 14 brokers including KIS and Kiwoom, tax-advantaged, and has a structural anchor (LPs must keep the close within 6% of the international price) — a natural data surface (KRX premium vs LBMA×USDKRW). KAU carbon is closed to individuals until at least 2028. Korean IPO first-day returns are large (33–52% averages) but allocation is a broker process, not an API. Ex-dividend capture has Korean evidence that is real but not risk-free. KOSPI200 box spreads are efficiently priced (few arbitrage observations) but give a clean implied funding rate for the rates desk. KRX's "배당지수선물" are futures on the KOSPI 고배당50 / 배당성장50 price indices (multiplier 2,000 KRW), not dividend-point futures.

### Cited Findings
- KRX gold participation: investors open a 일반상품 계좌 at a KRX-member securities firm and trade "주식처럼" via HTS/mobile; 13 securities firms were general members as of 2023-12, 79 실물사업자 as 자기매매회원; LP scheme since 2016-06-29: LPs must restore a bid-ask spread ratio within 3% inside 5 minutes with ≥100g orders, and "종가가 국제금가격과 6% 이내의 괴리율을 유지하도록"; LPs (2022-10) NH, Mirae, Samsung, Shinhan, KIS; account-opening brokers listed: KB, NH, SK, 대신, 미래에셋, 삼성, 신한, 유안타, 유진투자선물, 키움, 하나, 한국투자, 현대차, 한화 — [KRX금시장 투자 및 참여방법](https://open.krx.co.kr/contents/OPN/01/01050203/OPN01050203.jsp).
- KRX gold tax and specs (secondary summaries of KRX/broker pages): 양도소득세·배당소득세·부가가치세 exempt for exchange trading; 1g trading unit; 99.99% purity certified by 한국조폐공사; custody at 한국예탁결제원; 09:00–15:30 — [KRX 금 현물 투자](https://open.krx.co.kr/contents/OPN/01/01050201/OPN01050201.jsp), [신한투자증권 KRX금시장](https://www.shinhansec.com/siw/trading/etc-market/market_krx/contents.do). The 10% VAT on physical withdrawal is widely reported but was not read from a KRX page here — UNVERIFIED verbatim. The KRX leaflet PDF exceeded the fetch size limit — [KRX gold leaflet 2023-12-26](https://regulation.krx.co.kr/contents/RGL/04/04010108/KRX_GOLD_Leaflet_20231226.pdf).
- KRX gold data: "KRX 금 전종목 시세" on the Data Marketplace (keyless web) — [data.krx.co.kr MDC0201060201](https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201060201); KRX Open API needs a free key, ≤10,000 calls/day, data from 2010, non-commercial — [KRX Open API](https://openapi.krx.co.kr/) (search summary), community wrapper [krx-openapi](https://github.com/seokhoonj/krx-openapi).
- Leveraged ETP rules 2026: the FSC extended the 기본예탁금 for single-stock leveraged ETFs/ETNs to overseas-listed products, raising it from 1,000만원 to 3,000만원 cash-only (holdings no longer count); index/sector leveraged products are excluded; rationale: "단일종목 레버리지 상품은 국내외를 막론하고 분산투자 효과가 없는 고위험 상품" and preventing a balloon effect — [파이낸셜뉴스 2026-07-20](https://www.fnnews.com/news/202607201451297089); the FSC's asymmetric-regulation bill page — [FSC](https://www.fsc.go.kr/po010101/86751). Domestic leveraged ETP 기본예탁금/사전교육 regime is described on KIS's ETN site — [TRUE ETN 레버리지 기본예탁금 안내](https://www.trueetn.com/trueetn/nkis/invest/invEtn.jsp?cmd=FR13000) (not fetched; search result).
- Korean VIX ETNs: four issuers listed VIX ETNs in 2018-05, all four were delisted 2019-05; NH, Samsung and Shinhan relisted (Mirae did not) — [시사저널e 2023](https://www.sisajournal-e.com/news/articleView.html?idxno=297938); KIS itself lists "TRUE 인버스 VIX 선물 ETN" (Q570089, −0.5× daily VIX futures) — [TRUE ETN Q570089](https://www.trueetn.com/trueetn/nkis/item/itemEtn.jsp?cmd=FR10800&itemCode=Q570089).
- KAU carbon: the government targets a KAU futures market in 2028 (infrastructure 2026–27); currently only 할당대상업체 and specified financial institutions (insurers, banks; asset managers under review) may trade; individuals cannot trade directly; ETF/ETN access "as early as 2028–2029"; K-MSR from late 2026; 4th planning period 2026–2030 — [이코노믹리뷰 2026-05-19](https://www.econovill.com/news/articleView.html?idxno=740418). Prices are public on the KRX ETS platform — [ETS 시세조회](https://ets.krx.co.kr/contents/ETS/03/03010000/ETS03010000.jsp).
- Korean IPOs: 곽노걸·전상경, "IPO 저가 발행의 저주: 공모주 상장 초기 주가행태 분석", 재무관리연구 32(2), 2015, 143–169: average initial return 33%, yet ~48% of IPO firms trade below the offer price one month after listing; high subscription ratios predict first-day but not one-month performance — [KCI](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002003670). KCMI 김민기, 자본시장포커스 2024-04 (2024-02-19): Korea's average first-day return ≈ 52%, "the highest level among OECD member countries"; small-firm listings add ~10–12 pp; final prices stay inside the band even when 66% of demand is above it — [KCMI](https://www.kcmi.re.kr/publications/pub_detail_view?syear=2024&zcd=002001016&zno=1769&cno=6278). Q3-2024 average first-day return fell to 21.4% — [한국경제 2024-09-18](https://www.hankyung.com/article/2024091827591). Keyless data: KIND "종목별 공모가 대비 주가등락률" — [KIND](https://kind.krx.co.kr/listinvstg/pubprcCmpStkprcByIssue.do?method=pubprcCmpStkprcByIssueMain); Ritter's IPOs-Korea.pdf (1980–2025) — [Ritter IPO Data](https://site.warrington.ufl.edu/ritter/ipo-data/).
- Ex-dividend: 김성민, "현금배당락조치 폐지 이후 배당락일의 주가행태", 재무관리논총 9(1), 2003, 189–219: after the July-1998 abolition of the exchange's cash-dividend ex-adjustment, after-tax holding-period returns around the ex-date rose from 4.7% (1997) to 8.9% (1998–99), with the caveat that the gaps "don't constitute risk-free arbitrage opportunities" — [KoreaScience](https://koreascience.kr/article/JAKO200308508084531.page). Post-ex-date one-month returns 2010–2020 averaged +1.8% (KOSPI) and +6.1% (KOSDAQ) — [경향신문 2021-12-27](https://www.khan.co.kr/article/202112271449001). Related: 배당평판 study (KCI ART002716028) — [KCI](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002716028).
- KOSPI200 box spreads: 이재하(성균관대 SKK GSB)·한덕희(국민연금연구원), "KOSPI200 옵션시장에서의 박스스프레드 차익거래 수익성" (KDA presentation PDF; year not printed, text references "2005년말 현재"): 1-minute data 2003-12 to 2004-06; of 39,445 (38,318) observations for small (large) strike gaps, credit-box arbitrage appeared in 681 (2,293) = 2% (6%), debit-box in 831 (3,098) = 2% (8%); profits shrink sharply with execution delay; conclusion: the market "효율적으로 운영되고 있는 것으로 보인다" — [KDA PDF](https://www.kdajdqs.org/bbs/presentation/295/download/311). Box spreads as a financing instrument (ACT/360 implied rate) — [CME Group 2024](https://www.cmegroup.com/articles/2024/index-options-box-spreads-as-financing-tool.html). Keyless option chains: KRX "만기별 가격표(옵션)" — [data.krx.co.kr MDC0201070206](https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201070206).
- KRX 배당지수선물 (Kiwoom product guide, read in browser 2026-09-25): underlyings 코스피 고배당50 and 코스피 배당성장50 (dividend-yield-weighted price indices); cash-settled; multiplier 2,000원; tick 0.5p (1,000원); 7 expiries (2 quarterly, 2 semi-annual, 3 annual); last trading day the second Thursday of the expiry month; limit-order types only; price limits ±8/15/20% — [키움증권 섹터/배당지수선물](https://www.kiwoom.com/h/help/trade/VHelpFuopSectorView). No KOSPI 200 dividend-point (dividend-swap-style) futures appear on that list.

### Inferences
- KRX gold's LP band (±6% at the close) makes the KRX-vs-international premium a bounded, mean-reverting series — a clean data surface; there is no academic strategy paper for it, so it stays a monitor, not a candidate.
- IPO allocation is a subscription process (청약) outside any API; QUANTGEN can only analyse KIND data (first-day return vs 청약경쟁률, size, market regime).
- Ex-dividend capture is executable via KIS-domestic but its edge is after-tax and small; the 2003 paper's returns pre-date current tax/transaction-cost settings.
- Box-spread implied rates are more useful as a rates-desk indicator (implied KRW funding vs CD/KOFR) than as a trade.

### Gaps
- Current KRX gold fee schedule and VAT text from a KRX page (leaflet too large to fetch).
- A Korean academic paper on the KRX gold premium — none found.
- Current securities-transaction-tax rates for the ex-dividend cost model — not fetched (budget), UNVERIFIED.
- Year/venue of the 이재하·한덕희 paper (PDF has no journal header).

---

## 6. Prediction markets (Polymarket, Kalshi, Manifold)

### Takeaway
For a Korean resident, trading on Polymarket is treated as gambling: the 방송미디어통신심의위원회 voted on 2026-08-18 to block the site as illegal gambling, and Gangwon police have been investigating Korean users under 형법 도박죄 since summer 2026. Polymarket's own geoblock list places KR in the "close-only on frontend" tier. Kalshi says non-US trading is "subject to the Member Agreement"; a secondary source says Korea is not on Kalshi's restricted list, but the same 도박죄 logic applies. The academic literature (Wolfers–Zitzewitz 2004; Snowberg–Wolfers 2010) supports a favourite-longshot bias, and the Polymarket Gamma/CLOB market-data endpoints are public — so this is a data-only surface for QUANTGEN, never a trading one.

### Cited Findings
- Polymarket geoblock documentation: OFAC-blocked (Iran, Syria, Cuba, North Korea, Crimea/Donetsk/Luhansk) — no orders at all; a second tier "Close-Only (Frontend and API)" with ~35 jurisdictions including the United States, United Kingdom, France, Germany, Australia, Belgium, Brazil, Canada (provinces); a third tier "Regulatory-Restricted Jurisdictions (Close-Only on Frontend)" listing KR (South Korea) alongside Ireland, Japan, Malta (sports only), Netherlands; check endpoint `GET https://polymarket.com/api/geoblock` — [Polymarket docs: Geographic Restrictions](https://docs.polymarket.com/api-reference/geoblock). VPN use to evade restrictions violates the ToS — [Polymarket Help Center](https://help.polymarket.com/en/articles/13364163-geographic-restrictions).
- Polymarket public APIs: Gamma (`https://gamma-api.polymarket.com`, market metadata, no credentials), CLOB (`https://clob.polymarket.com`, order books and price history public; orders need wallet-signed L2 credentials), Data API (`https://data-api.polymarket.com`) — [Polymarket API overview](https://docs.polymarket.com/api-reference/introduction) (search-result summary of the official docs).
- Korea block: on 2026-08-18 the 방송미디어통신심의위원회 voted to block access to Polymarket, finding it illegal gambling under the Criminal Code (도박개장) and the 국민체육진흥법; Polymarket's argument that removing Korean-language service and not taking won put it outside Korean law was rejected ("technical characteristics such as decentralized technology cannot be used to evade domestic laws") — [ZDNet Korea 2026-08-18](https://zdnet.co.kr/view/?no=20260818173958); also [이데일리](https://edaily.co.kr/News/Read?mediaCodeNo=257&newsId=01863046645548960).
- Users as suspects: 주간경향 2026-07-28/29: the 강원경찰청 사이버수사대 is investigating Polymarket users under 형법 도박죄; one lawyer estimated "three-digit" consultations; the 2006 Supreme Court 내기골프 precedent ("스스로 지배할 수 없는 우연적 사정이 승패를 좌우하면 도박이 성립") is expected to defeat an "investment" defence; a capital-markets researcher called derivative status for prediction markets "상당히 어렵다" — [주간경향](https://weekly.khan.co.kr/article/202607280600011). Penalties for simple gambling up to 1,000만원 fine, habitual up to 3 years or 2,000만원 (secondary legal summaries) — [블록미디어](https://www.blockmedia.co.kr/archives/1140466), [법률사무소 번화](https://bh-law.kr/ko/news/column/polymarket-korea-legal-issues-defense).
- Kalshi: "Yes, you can trade on Kalshi from many countries. Your eligibility … is subject to the terms of the Kalshi Member Agreement"; identity and country of residence verified at signup (article dated 2026-03-20) — [Kalshi Help Center](https://help.kalshi.com/en/articles/14026044-can-i-trade-on-kalshi-from-outside-the-united-states). First non-US push via XP in Brazil, announced 2026-03-09 — [Bloomberg](https://www.bloomberg.com/news/articles/2026-03-09/kalshi-teams-up-with-brazil-s-xp-for-first-international-push). A secondary tracker quotes Member Agreement v1.6 (2026-06-12) restricted list for Asia as China, Laos, Singapore, Taiwan, Thailand — Korea not enumerated — [coinperps](https://www.coinperps.com/learn/kalshi-restricted-countries) (secondary; the agreement page itself was not reachable — UNVERIFIED). Kalshi API: REST base `https://external-api.kalshi.com/trade-api/v2` (demo `external-api.demo.kalshi.co`), RSA-PSS signed headers for private calls, public market data without auth — [Kalshi API docs](https://docs.kalshi.com/welcome) (search summary).
- Wolfers & Zitzewitz (2004), "Prediction Markets", Journal of Economic Perspectives 18(2), 107–126: market forecasts "are typically fairly accurate and outperform most moderately sophisticated benchmarks" — [AEA](https://www.aeaweb.org/articles?id=10.1257%2F0895330041371321).
- Snowberg & Wolfers (2010), "Explaining the Favorite–Long Shot Bias: Is it Risk-Love or Misperceptions?", Journal of Political Economy 118(4), 723–746: long shots are overbet, favourites underbet; tests using exacta/quinella/trifecta pools favour probability misperception (prospect theory) over risk-love — [JPE](https://www.journals.uchicago.edu/doi/abs/10.1086/655844), [author PDF](http://users.nber.org/~jwolfers/papers/Favorite_Longshot_Bias.pdf).
- Manifold: not researched (budget); play-money platform — UNVERIFIED for 2026 status.

### Inferences
- Reading Polymarket/Kalshi market data is not itself gambling; placing or holding positions from Korea is criminally exposed after 2026-07/08. QUANTGEN should at most ingest probabilities as a macro/event indicator (e.g. FOMC-cut probabilities) and must not model P&L from positions.

### Gaps
- Kalshi's Member Agreement text (page not reachable); Manifold's status.
- Whether Korean ISPs already enforce the 2026-08-18 block on `polymarket.com` and on the API hosts — unknown.

---

## 7. VIX-related products

### Takeaway
Best-evidenced and most accessible item in this note. CFE VIX futures (VX, VIX × USD 1,000, nine consecutive months plus quarterlies) are listed on KIS's overseas-futures product page and the KIS API has `[해외선물옵션]` endpoints; Cboe publishes free per-contract history from 2004. The academic evidence on contango roll-down (Simon–Campasano 2014, Journal of Derivatives — not JPM; Eraker–Wu 2017 JFE) is direct and strong. SVXY/UVXY are ordinary US ETFs reachable via KIS-overseas-stock; the 2026-07 Korean rule tightening applies to single-stock leveraged products only, so no regulatory block was found (per-broker restrictions UNVERIFIED). Domestic alternatives: KIS's own TRUE 인버스 VIX ETN and KRX 변동성지수선물 (V-KOSPI200 futures).

### Cited Findings
- Simon & Campasano (2014), "The VIX Futures Basis: Evidence and Trading Strategies", Journal of Derivatives 21(3), 54–69: the basis has no significant forecast power for spot-VIX changes (2006-01–2011-12) but does forecast VIX-futures price changes; shorting VX in contango / buying in backwardation, hedged with mini-S&P futures, is "highly profitable and robust to transaction costs and out-of-sample hedge ratio forecasts" — [Journal of Derivatives](https://jod.pm-research.com/content/21/3/54.abstract), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2094510). (The assignment cited JPM; the venue is the Journal of Derivatives.)
- Simon (2017), "Trading the VIX Futures Roll and Volatility Premiums with VIX Options", Journal of Futures Markets — [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.21788).
- Eraker & Wu (2017), "Explaining the negative returns to VIX futures and ETNs: An equilibrium approach", Journal of Financial Economics 125(1), 72–98: average returns to long VIX futures and VIX ETNs are negative; the roll yield drives the VXX–VIX return gap and is mostly negative — [IDEAS](https://ideas.repec.org/a/eee/jfinec/v125y2017i1p72-98.html), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2340070).
- KIS overseas futures product page (fetched 2026-09-25): CBOE "VIX [VX]", contract "VIX x $1,000", "최근 연속 9개월물 및 분기월물" — [한국투자증권 해외선물옵션 거래상품안내](https://www.truefriend.com/main/bond/foreign/_static/TF03df040110.jsp); VIX futures trade 08:00–next-day 07:00 KST as "실시간 해외선물" (search summary of KIS pages). Overseas F&O at KIS requires the 모의거래 이수 (simulation course) before trading — [KIS 모의거래 및 이수제도](https://m.koreainvestment.com/main/research/virtual/_static/TF07db010000.jsp) (search result; not fetched).
- Cboe historical data: "CFE Daily Volume and Open Interest from 2004 to Current" and settlement-window files as CSV; per-product/per-year downloads; CSV pattern `https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/[filename].csv`; custom data via Cboe DataShop — [Cboe futures historical data](https://www.cboe.com/us/futures/market_statistics/historical_data/); VIX settlement series page — [Cboe VIX settlement series](https://www.cboe.com/markets/us/futures/market-statistics/vix-settlement-series/); Python helper for term structures — [vix_utils](https://github.com/dougransom/vix_utils).
- Korean leveraged-ETP rule (2026-07-20) covers single-stock leveraged ETF/ETN only; index/sector/VIX-type leveraged products were excluded — [파이낸셜뉴스 2026-07-20](https://www.fnnews.com/news/202607201451297089).
- Korean VIX ETN history (2018 listings, 2019 delistings, partial relisting) and KIS's Q570089 — see Section 5 citations.
- Overseas derivatives gains taxed at 22% above a 250만원 deduction (secondary) — see Section 1.

### Inferences
- The cleanest QUANTGEN surface is a VIX term-structure page: VIX (FRED VIXCLS is already an app input), VX1/VX2 from Cboe CSVs, basis, contango slope, constant-maturity roll yield, and a Simon–Campasano-style costed backtest. Execution via KIS-overseas-futopt is available but leverage and the 22% tax must be in the cost model.
- SVXY/UVXY: the app can model them from the VX term structure (daily −0.5×/+1.5× of the SPVIXSTR-like index), which is exactly the Eraker–Wu decomposition; tradability via KIS-overseas-stock is a reasonable inference, per-broker restrictions UNVERIFIED.

### Gaps
- KIS-specific restrictions on UVXY/SVXY (none found; not confirmed).
- Cboe's exact per-contract CSV file names (the page describes the pattern; a live download was not tested).

---

## 8. Everything else with credible evidence: Korean REITs, ELS/DLS, KRX dividend futures; the user's study materials

### Takeaway
Korean listed REITs trade at deep NAV discounts (P/NAV 0.39–0.46× for two Aegis REITs, 2026-06) — reachable through KIS-domestic with NAV from DART, but there is no Korean academic strategy paper (documented as a data surface). ELS/DLS are the club's structuring object: FSS data give a 95.1조원 outstanding book with S&P500/EuroStoxx50/KOSPI200 as the main underlyings and a 69/31 self-hedge/back-to-back split — an analysis input, not a tradable. Catastrophe bonds, art/wine and P2P were skipped as instructed. On the user's materials: the 재무경제학 folder holds Ch.1–2, 5, 6, 7 slides (risk premium, Sharpe ratio, diversification); CAPM (Ch. 9) is scheduled for 2026-09-28 and 10-19 and the EMH chapter is not on the syllabus, so market-efficiency theory must be cited from the roadmap/Fung–Hsieh papers and the 계량2 stationarity/Ljung–Box material instead.

### Cited Findings
- REITs: 이데일리 2026-06-23: 이지스레지던스리츠 NAV/share 8,610원 vs price 3,445원 (P/NAV ≈ 0.39×; AUM 1.44조원, +63.2% over cost); 이지스밸류플러스리츠 NAV/share 7,104원 vs 3,290원 (≈ 0.46×); 신한알파리츠 appraisal 3.87조원 (+31% over cost) vs market cap 6,144억원; reasons: rates, weak real-estate sentiment — [이데일리](https://edaily.co.kr/News/Read?mediaCodeNo=257&newsId=05129926645484672). Samsung Securities (2021-12-13) attributed part of the discount to the absence of regular asset revaluation — [삼성증권 리츠 note PDF](https://english.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName=2020/20211213125634847_02_05.pdf&contentType=application/pdf) (search result). KAREIT lists 23 listed REITs with total assets ≈ 34조원 (page dated 2026-09-25; price cells rendered as 0 in the fetch) — [한국리츠협회 상장리츠 현황](https://www.kareit.or.kr/invest/page2.php). US evidence that REITs move from IPO premia to NAV discounts ~30 months later — [JABE](https://articlegateway.com/index.php/JABE/article/view/7527).
- ELS/DLS: FSS 2025 figures (reported 2026-05-06): issuance of ELS·DLS·ELB·DLB 94.9조원 (+21.3조원), redemptions 81.2조원, outstanding 95.1조원 (+13.6조원); ELS 21.8조원, DLS 4.0조원, ELB 47.5조원, DLB 21.6조원; index-linked ELS 16.8조원 with S&P500 14.7조원, EuroStoxx50 14.3조원, KOSPI200 13.9조원; ELS realised 7.8% annualised (vs −4.7% prior year); self-hedge 69.4% of outstanding, back-to-back 30.6% (77.5% with foreign counterparties) — [뉴스핌 2026-05-06](https://www.newspim.com/news/view/20260506000814). Q1-2026 issuance 19.6조원, +24.1% y/y — [이데일리](https://edaily.co.kr/News/Read?mediaCodeNo=257&newsId=03837606645512552) (search snippet). BOK Issue Note 2015-11-23 (고경철·김민서): ELS mostly non-principal-protected with multiple underlyings; DLS mostly rate-linked and principal-protected; securities firms' hedge books hold low-liquidity/lower-rated bonds, a settlement-stability risk — [BOK 이슈노트](https://www.bok.or.kr/portal/bbs/P0002353/view.do?nttId=214097&menuNo=200433). KOFIA 모범규준 for issuance/hedging of 파생결합증권 — [금투협 법규정보](https://law.kofia.or.kr/service/law/lawFullScreenContent.do?seq=161&historySeq=460).
- KRX 배당지수선물 — see Section 5 (Kiwoom guide).
- User materials (locators from local PDF text extraction, 2026-09-25):
  - 재무경제학 Syllabus (Econ 354, 2026 Fall): schedule Ch. 1–2 (Sep 7), Ch. 6 (Sep 14), Ch. 7 (Sep 21), Ch. 9 CAPM I/II (Sep 28, Oct 19), Ch. 14 bond prices and yields (Oct 26), Ch. 15 term structure I/II (Nov 2, 9), Ch. 18 equity valuation (Nov 23), Ch. 20 options and forwards (Nov 30); "arbitrage pricing theory" in the description — `26년 2학기 수업자료\재무경제학\Syllabus_Econ354_2026Fall.docx.pdf` pp. 1–2.
  - LectureSlides2_Ch5 p. 7 (Fisher equation), pp. 8–9 (expected return E(r)=Σp(s)r(s), variance/SD); LectureSlides3_Ch6 p. 3 (risk-averse investors consider only prospects with positive risk premiums), p. 17 (reward-to-volatility = Sharpe ratio, slope (15−7)/22); LectureSlides4_Ch7 p. 4 (portfolio variance as weighted covariances), p. 12 (ρ = −1 gives a perfect hedge), p. 22 (Markowitz minimum-variance and efficient frontier).
  - 류거시 econ202_topic02_FinancialMarkets: p. 3 (central bank's role in interest-rate determination), p. 4 (money vs bonds), pp. 16–17 (open-market operations and the central-bank balance sheet).
  - 계량2 ECON_302_Ch1: p. 9 (strict stationarity), p. 11 (autocovariance), p. 13 (white noise vs IID), p. 17 (Box–Pierce and Ljung–Box Q statistics); ECON_302_Ch2: p. 11 (AR(p) in regression form), p. 14 (martingale-difference CLT for OLS on AR models).
  - Shreve II ch. 9, eq. 9.3.16 p. 385 (FX under the domestic risk-neutral measure) and 5.5.6–5.5.8 pp. 235–237 (dividends) — as located in `docs/ARCHITECTURE_REVIEW.md` §0.
  - From_Radon-Nikodym_to_Fung-Hsieh (Geon Koh): §5.1 variance risk premium and the variance swap (p. 11), §5.5 term structure of the premium (p. 13), §6 Fung–Hsieh lookback straddle and PTFS factors (pp. 13–18), §6.9 mean reversion as the mirror image (p. 17), §7 synthesis (p. 18); "carry" pp. 10, 12–13, 18–19; "deflated" Sharpe p. 18.
  - Quant_Roadmap_Two_Doors (Geon Koh): deflated Sharpe pp. 8–9, 23, 28; purged cross-validation pp. 8, 28; multiple testing pp. 12, 28; carry p. 29.

### Inferences
- REIT P/NAV is a KIS-domestic data surface (price via KIS, NAV via DART appraisal disclosures) with the US closed-end-fund literature as the theoretical anchor (Section 3); the Korean-specific academic evidence is missing, so it is "document + monitor".
- ELS: the structuring page already prices reverse convertibles; the FSS underlying mix (S&P500/EuroStoxx50/KOSPI200 worst-of) and the hedge split are the market facts the pitchbook should quote.

### Gaps
- A Korean academic paper on REIT NAV discounts (none found; only a 2016 K-REITs leverage paper — [JKAIS 2016](https://www.kais99.org/jkais/journal/Vol17No11/vol16no11p08.pdf) — UNVERIFIED relevance).
- Catastrophe bonds: not investable for a Korean retail investor through any venue found; skipped per instructions.

---

## Assets for QUANTGEN

Format per asset: asset; explanation; market structure; access from Korea; profit generation; distinguishable facts; keyless data; verified from; then candidates.

### Asset 1 — CFE VIX futures (VX) and VIX-futures ETPs (VXX/UVXY/SVXY; TRUE 인버스 VIX ETN)
- asset: Cboe Futures Exchange VIX futures (VX), and the ETPs that hold rolling 30-day VX positions.
- explanation: VX settles to a special opening quotation of the VIX; F_t(T) is the market's risk-neutral expectation of the VIX at T plus a variance-risk-premium-driven term. ETNs/ETFs (VXX-type) hold a daily-rebalanced mix of VX1 and VX2 with constant 30-day maturity.
- market structure: exchange-traded, cash-settled, nine consecutive monthly contracts plus quarterlies, VIX × USD 1,000; term structure usually in contango (F1 > VIX) except in stress.
- access from Korea: KIS-overseas-futopt lists "VIX [VX]" ([KIS product page](https://www.truefriend.com/main/bond/foreign/_static/TF03df040110.jsp), 2026-09-25); prerequisites: KIS overseas F&O account and the 모의거래 이수 course (KIS page, search result); ETPs via KIS-overseas-stock (US-listed ETF/ETN; per-ticker availability UNVERIFIED); legality: ordinary overseas derivatives/stock trading through a domestic 투자중개업자, gains taxed 22% above 250만원 (secondary, 2026-03). The 2026-07-20 FSC deposit rule covers only single-stock leveraged ETPs ([파이낸셜뉴스 2026-07-20](https://www.fnnews.com/news/202607201451297089)).
- profit generation: harvesting the negative roll yield of long VX (short front future or short VXX-type exposure, hedged with equity futures), or buying VX when the curve inverts.
- distinguishable facts: a persistent negative premium documented in equilibrium (Eraker–Wu 2017); basis forecasts futures changes but not spot VIX (Simon–Campasano 2014); Korea's VIX ETNs were delisted en masse in 2019-05 and relisted by three issuers; KIS's own inverse-VIX ETN (Q570089) exists on KRX.
- keyless data: Cboe per-contract/settlement CSVs from 2004 ([Cboe](https://www.cboe.com/us/futures/market_statistics/historical_data/)); VIX spot from FRED VIXCLS (already in the app) and Yahoo ^VIX; VXX/UVXY/SVXY closes via yfinance; ES/SPY for the hedge.
- verified from: Simon & Campasano 2014 JoD 21(3) 54–69; Eraker & Wu 2017 JFE 125(1) 72–98; Simon 2017 JFM; KIS product page; Cboe data page; 파이낸셜뉴스 2026-07-20.

#### Candidates
1. name: VX contango roll-down, hedged (Simon–Campasano)
   - family: volatility risk premium / term-structure carry.
   - mechanism: daily basis b_t = F1_t/VIX_t − 1 (or F1 − VIX in points); expected daily roll P&L of a short VX1 ≈ (F1_t − VIX_t)/T_1 per day if the curve is static; rule: short 1 VX1 when b_t > b* (e.g. 0.05 or the top tercile) and long when b_t < −b*, hedge with h_t × ES where h_t = β̂ from a rolling 60-day regression of ΔF1 on ΔES (in USD), hold until b_t crosses zero or 5 days before expiry then roll to VX2.
   - sources: Simon & Campasano (2014) JoD 21(3) 54–69 ([abstract](https://jod.pm-research.com/content/21/3/54.abstract)); Eraker & Wu (2017) JFE 125(1) ([IDEAS](https://ideas.repec.org/a/eee/jfinec/v125y2017i1p72-98.html)).
   - user-material refs: From_Radon-Nikodym_to_Fung-Hsieh §5.1 variance risk premium (p. 11) and §5.5 term structure (p. 13); 재무경제학 Ch6 p. 17 (Sharpe ratio as the evaluation metric); 계량2 Ch1 p. 17 (Ljung–Box on strategy residuals); Shreve II 5.2 risk-neutral drift (pp. 214–217, via ARCHITECTURE_REVIEW §0) for the Q-vs-P framing.
   - data needs: VX1/VX2 daily settlements and expiry dates (Cboe CSV), VIX close (FRED), ES or SPY closes (Yahoo).
   - reachable via: KIS-overseas-futopt (VX), KIS-overseas-stock (SVXY/UVXY proxies), yfinance, FRED.
   - backtest design: signal on close t from settlements known at t; position from t+1 settlement; holding until signal flips or forced roll; cost 2 ticks per VX side (0.05 × USD 1,000 = USD 50) + ES 1 tick, plus 22% tax on annual net gains; benchmark: buy-and-hold SVXY and flat; universe: VX1/VX2 2006–present.
   - pre-registered validation criterion: net Sharpe ≥ 0.6 and positive in ≥ 70% of calendar years on 2012–2026 out-of-sample after fitting b* on 2006–2011; deflated-Sharpe (Roadmap pp. 8–9) applied over the grid of b* tried; max drawdown reported around Feb-2018 and Mar-2020.
   - expected edge and decay: the literature reports high Sharpe pre-2012; post-2018 ("Volmageddon") the premium is smaller and the left tail larger; expect a gross carry of roughly the average contango (several % of F1 per month) minus crash losses.
   - implementation complexity: 3 (roll calendar and continuous series construction are the work).
   - caveats: leverage; the short leg can lose multiples of margin in a day (Feb 5 2018); hedge ratio instability; execution hours vs Korean daytime.
2. name: Constant-maturity VIX ETP replication and drift monitor
   - family: model/monitor (Eraker–Wu decomposition) rather than a trade.
   - mechanism: build the 30-day constant-maturity index I_t = w_t F1_t + (1 − w_t) F2_t with w_t = (days to VX2 expiry − 30)/(days between expiries); daily ETP return ≈ ±k × ΔI_t/I_t − fee; report expected drift = −k × roll yield; compare model to VXX/SVXY actuals (tracking error).
   - sources: Eraker & Wu (2017) JFE ([SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2340070)); Gehricke & Zhang (2018) "Modeling VXX", Journal of Futures Markets ([Wiley](https://onlinelibrary.wiley.com/doi/10.1002/fut.21913)).
   - user-material refs: From_Radon-Nikodym_to_Fung-Hsieh §5.1, §6.5 (long convexity payoff, p. 15); QUANTGEN primer (GARCH-t conditional vol vs implied).
   - data needs: as candidate 1 plus ETP closes.
   - reachable via: yfinance, Cboe CSV.
   - backtest design: n/a (monitor); validation = tracking error of the replicated index vs VXX < 0.5%/month.
   - pre-registered validation criterion: replication R² > 0.98 on daily returns 2019–2026.
   - expected edge and decay: none claimed; explanatory.
   - implementation complexity: 2.
   - caveats: ETP fees and intraday rebalancing.

### Asset 2 — G10 (+KRW) FX: momentum, value and dollar carry (extension of the existing carry basket)
- asset: spot FX vs USD, expressed through forwards (covered-interest-parity forwards already computed in the app).
- explanation: excess return rx_{t+1} = f_t − s_{t+1} (logs, USD per unit of foreign currency; f the 1-month forward). Carry sorts on f_t − s_t; momentum on past rx; value on the real exchange rate; dollar carry on the average forward discount.
- market structure: OTC interbank spot/forward; retail Korean access is via KRX currency futures (KIS-domestic) or KOFIA-regulated FX margin (USD 10,000 lots, 10% margin) at Hana/Kiwoom/Samsung Futures (2024-07 status).
- access from Korea: read-only in the app; if executed, KIS-domestic 통화선물 (USD/JPY/EUR/CNH futures) or domestic FX margin; offshore OANDA/IG/Saxo accounts are illegal for individuals per [KOFIA](https://www.kofia.or.kr/wpge/m_75/sub03040403.do) (page current 2026).
- profit generation: cross-sectional premia (carry, momentum, value) and the time-series dollar premium.
- distinguishable facts: the Fama (1984) negative slope; momentum spread up to 10% p.a. gross (Menkhoff et al. 2012b) that is partly transaction costs; dollar-carry uncorrelated with standard carry (LRV 2014).
- keyless data: FRED H.10 daily (DEXKOUS, DEXJPUS, DEXUSEU, …) and Yahoo spot; FRED/OECD policy and short rates (already in app) for forward points; Dukascopy public tick feed for intraday if ever needed; BIS/IMF CPI for real exchange rates (FRED hosts CPI series — not itemised here).
- verified from: Fama 1984 JME; Menkhoff et al. 2012 JF and JFE, 2017 RFS; Lustig, Roussanov, Verdelhan 2014 JFE; KOFIA pages; 소비자가 만드는 신문 2024-07-17.

#### Candidates
1. name: FX cross-sectional momentum (1-1 and 3-1)
   - family: momentum.
   - mechanism: at month-end t compute M_i,t = Σ_{k=0}^{f−1} rx_{i,t−k} for f ∈ {1, 3}; rank the N currencies; long top-⌈N/3⌉, short bottom-⌈N/3⌉, equal weight, hold 1 month; portfolio return = mean(rx_long) − mean(rx_short); net of a bid-ask cost c ≈ 5–10 bp per leg per rebalance (G10) and 20–30 bp for KRW.
   - sources: Menkhoff, Sarno, Schmeling, Schrimpf (2012) JFE 106(3) 660–684 ([IDEAS](https://ideas.repec.org/a/eee/jfinec/v106y2012i3p660-684.html)).
   - user-material refs: From_Radon-Nikodym_to_Fung-Hsieh §6.9 (mean reversion vs trend, p. 17) and §7; Roadmap pp. 8–9 (deflated Sharpe over the (f, h) grid); 계량2 Ch1 pp. 9–17 (stationarity of rx and Ljung–Box on the strategy's returns); 재무경제학 Ch7 p. 4 (portfolio variance from covariances).
   - data needs: monthly spot and 1-month forward (or CIP forward from the app's rates) for G10 + KRW.
   - reachable via: FRED, yfinance (already wired); KIS-domestic 통화선물 for execution.
   - backtest design: rank at close t, earn t+1 (same convention as the existing carry backtest), monthly holding, 10 bp per leg cost, benchmark = existing carry basket and equal-weight long-all; universe G10 + KRW from 1999 (EUR) onward.
   - pre-registered validation criterion: net annualised return > 0 with t-stat > 2 on 2010–2026 after choosing (f, h) on 1999–2009; correlation with the carry basket < 0.3 (LRV/Menkhoff claim of orthogonality).
   - expected edge and decay: 3–6% p.a. gross in the papers' samples; documented decay after publication (2012) is plausible — report the post-2012 sub-sample separately.
   - implementation complexity: 2 (the carry basket code already has the return bookkeeping).
   - caveats: KRW is non-deliverable offshore; forward points for KRW in the app come from CIP, not NDF quotes, so KRW rx is an approximation.
2. name: Dollar carry (LRV 2014)
   - family: time-series carry / macro timing.
   - mechanism: AFD_t = (1/N) Σ_i (f_{i,t} − s_{i,t}) (average forward discount of foreign currencies vs USD, ≈ average foreign short rate minus US short rate); if AFD_t > 0 go long the equal-weight basket of foreign currencies (short USD), else short it; hold 1 month; optional conditioning on US industrial-production growth (FRED INDPRO).
   - sources: Lustig, Roussanov, Verdelhan (2014) JFE 111(3) 527–553 ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X1300305X)); Fama (1984) JME 14(3) for the forward-premium regression as the diagnostic.
   - user-material refs: Shreve II 9.3.16 p. 385 (domestic vs foreign risk-neutral measures — the Q-side of the forward premium); 류거시 topic02 pp. 3, 16 (policy rate as the driver of the short-rate differential); 계량2 Ch2 p. 14 (martingale-difference CLT for the Fama regression's OLS t-stats, with Newey–West in practice).
   - data needs: monthly spot and forward (or short rates) for G10; INDPRO.
   - reachable via: FRED, yfinance.
   - backtest design: sign of AFD at t, earn t+1, monthly, 5 bp per leg, benchmark: always-long-basket and the app's carry basket; also report the Fama β̂ per currency with HAC standard errors.
   - pre-registered validation criterion: out-of-sample (2014–2026, post-publication) Sharpe > 0.3 and correlation with the carry basket < 0.3.
   - expected edge and decay: the paper's dollar-carry Sharpe is comparable to standard carry; post-2014 evidence is mixed — treat as a hypothesis to test.
   - implementation complexity: 2.
   - caveats: one-signal strategy; long stretches of a single sign; exposure to USD crash risk in "bad times" is the priced risk, not a free lunch.
3. name: FX value (real-exchange-rate reversal)
   - family: value.
   - mechanism: q_{i,t} = s_{i,t} + p*_{i,t} − p_t (log RER vs USD using CPI); signal V_{i,t} = q_{i,t} − mean(q_{i,t−60..t−1}) (5-year deviation); long the most undervalued third, short the most overvalued; rebalance monthly; hold 1 month.
   - sources: Menkhoff, Sarno, Schmeling, Schrimpf (2017) RFS 30(2) 416–441 ([IDEAS](https://ideas.repec.org/a/oup/rfinst/v30y2017i2p416-441..html)).
   - user-material refs: 류거시 (PPP/RER is macro-course material; the topic02 file covers money and bonds only — cite as background); Roadmap pp. 12, 28 (multiple testing when choosing the RER window).
   - data needs: monthly CPI per country (FRED hosts OECD CPI series — locate per country; UNVERIFIED which IDs), spot.
   - reachable via: FRED, yfinance.
   - backtest design: as candidate 1; CPI lagged one month to avoid look-ahead on publication.
   - pre-registered validation criterion: positive net return with t > 2 on 2005–2026; low correlation (< 0.3) with carry and momentum legs.
   - expected edge and decay: modest (2–4% p.a. in the paper), slow-moving; low turnover keeps costs small.
   - implementation complexity: 3 (CPI data plumbing).
   - caveats: CPI revisions and release lags; RER window choice is a researcher degree of freedom.

### Asset 3 — US-listed closed-end funds (discount to NAV)
- asset: exchange-listed closed-end funds (equity, muni, taxable-bond).
- explanation: fund shares trade at P_t ≠ NAV_t; discount d_t = P_t/NAV_t − 1.
- market structure: NYSE/NASDAQ common stock; NAV published daily by sponsors; no creation/redemption, so discounts persist; sponsors run buybacks/tender offers at times.
- access from Korea: KIS-overseas-stock (US common stock; tradability per ticker UNVERIFIED); tax 22% on gains above 250만원; dividend withholding per treaty (not researched).
- profit generation: mean reversion of extreme discounts (Pontiff 1995), sentiment cycles (LST 1991), activist/tender catalysts; carry of the NAV yield bought at a discount.
- distinguishable facts: a textbook "limits to arbitrage" market — mispricing is larger where replication is hard, dividends small, funds small, rates high (Pontiff 1996).
- keyless data: prices via yfinance; NAV: CEFConnect pages (no public API found), sponsor sites — the NAV feed is the unresolved item.
- verified from: LST 1991 JF; Pontiff 1995 JFE, 1996 QJE; CEFConnect/cefdata/CEFA pages.

#### Candidates
1. name: Discount z-score reversal
   - family: value / mean reversion.
   - mechanism: z_{i,t} = (d_{i,t} − mean_{252}(d_i))/sd_{252}(d_i); long the decile with the most negative z (largest relative discount), hold 1 month, equal weight; optionally hedge with the fund's asset-class ETF; expected return ≈ κ × (d̄_i − d_{i,t}) + NAV yield, with κ the estimated monthly reversion speed.
   - sources: Pontiff (1995) JFE 37(3) 341–370 ([IDEAS](https://ideas.repec.org/a/eee/jfinec/v37y1995i3p341-370.html)); Pontiff (1996) QJE 111(4) ([OUP](https://academic.oup.com/qje/article-abstract/111/4/1135/1932203)); Lee, Shleifer, Thaler (1991) JF 46(1) ([Wiley](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1991.tb03746.x)).
   - user-material refs: 재무경제학 Ch6 p. 3 (positive risk premium requirement) and Ch7 p. 22 (efficient frontier for the hedged book); 계량2 Ch1 p. 9 (stationarity of d_t is the whole premise — test it with an ADF/Ljung–Box first); Roadmap pp. 8–9 (deflated Sharpe over lookback choices).
   - data needs: daily P and NAV for a universe of ~300 CEFs; asset-class ETF for hedging.
   - reachable via: KIS-overseas-stock, yfinance (prices); NAV: other:<CEFConnect> (UNVERIFIED terms).
   - backtest design: signal at close t from NAV published for t; enter t+1; monthly; cost 25 bp per side (wide CEF spreads) + 22% tax; benchmark: equal-weight CEF universe and the asset-class ETF; universe: US CEFs with market cap > USD 100m.
   - pre-registered validation criterion: net alpha vs the asset-class ETF > 2% p.a. with t > 2 on 2015–2026; alpha must survive excluding 2020-03.
   - expected edge and decay: the literature's ~3–7% p.a. gross; retail spreads and tax eat much of it.
   - implementation complexity: 3 (NAV ingestion) — 4 if scraping.
   - caveats: leverage inside funds; distribution cuts drive discounts; without a keyless NAV feed this stays a document.

### Asset 4 — US merger arbitrage (cash deals)
- asset: target common stock after a definitive cash acquisition agreement.
- explanation: spread S_t = (Offer − P_t)/P_t; expected return = p × S_t − (1 − p) × L where p is completion probability and L the loss on a break.
- market structure: US common stock; deal terms in EDGAR filings (8-K, DEFM14A, SC TO-T); typical durations 3–9 months; regulatory and financing risk.
- access from Korea: KIS-overseas-stock; long-only cash deals need no shorting; tax 22% above 250만원.
- profit generation: harvesting the deal-completion premium; Mitchell–Pulvino: ≈ 4% p.a. excess after costs, with short-put-like exposure in crashes.
- distinguishable facts: return profile resembles writing index puts (non-linear beta); spreads widen in stress — an insurance premium, not an anomaly.
- keyless data: EDGAR full-text search JSON ([efts.sec.gov](https://efts.sec.gov/LATEST/search-index?q=%22agreement%20and%20plan%20of%20merger%22&forms=DEFM14A)) for announcements and proxies; prices via yfinance.
- verified from: Mitchell & Pulvino 2001 JF; EDGAR endpoint test 2026-09-25.

#### Candidates
1. name: Cash-deal spread portfolio (Mitchell–Pulvino replication, long-only)
   - family: event-driven / risk arbitrage.
   - mechanism: on day t+1 after a DEFM14A/8-K with a cash offer, if annualised spread S_t × 365/τ_t > r_f + 3% and market cap > USD 500m, buy target; exit at completion (Offer) or termination (close after the 8-K); position weight 1/n with cap 5%; portfolio return = Σ w_i × r_i.
   - sources: Mitchell & Pulvino (2001) JF 56(6) 2135–2175 ([Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00401)).
   - user-material refs: From_Radon-Nikodym_to_Fung-Hsieh §6.5 (non-linear, option-like payoff profiles) and §2.2 (Z as scenario re-weighting: the deal-break state is where the kernel is high); Roadmap Pillar 2 (multiple testing) for the threshold choice.
   - data needs: deal list (offer, announcement, expected close, outcome), daily prices.
   - reachable via: KIS-overseas-stock, yfinance, other:<EDGAR FTS>.
   - backtest design: entry t+1 after the filing date, exit on outcome, 10 bp per side + 22% tax, benchmark: T-bill + the short-put-like beta (regress on SPY with a piecewise slope), universe: US cash deals ≥ USD 500m, 2010–2026.
   - pre-registered validation criterion: net excess return > 2% p.a. after costs with t > 2; the piecewise beta in down markets must be reported, not hidden.
   - expected edge and decay: ~4% p.a. in 1963–1998; post-2010 spreads are thinner; decay likely.
   - implementation complexity: 5 (deal parser from EDGAR text; outcome labelling).
   - caveats: parser errors dominate; stock deals need shorting (excluded); regulatory-risk deals concentrate the losses.

### Asset 5 — SPACs (pre-deal trust arbitrage)
- asset: SPAC common shares before a business-combination vote.
- explanation: trust holds ≈ USD 10 per share in T-bills; shareholders may redeem at trust value at the merger vote or liquidation; buying below trust value gives a T-bill-like return plus a free option on a good deal.
- market structure: NYSE/NASDAQ; units, common, warrants; redemption right = embedded put.
- access from Korea: KIS-overseas-stock for common (units/warrants UNVERIFIED); tax 22%.
- profit generation: yield to trust value; upside if the announced deal trades above trust.
- distinguishable facts: SPAC IPO investors earned "remarkably high annualized average returns" while post-merger holders lost (Gahng–Ritter–Zhang 2023); structural dilution means the median SPAC holds USD 6.67 of cash per share at merger (Klausner et al. 2022).
- keyless data: Ritter's "IPOs 2025 SPACs" file; EDGAR S-1/424B4 and 8-K; prices via yfinance.
- verified from: Klausner–Ohlrogge–Ruan 2022 Yale J. Reg.; Gahng–Ritter–Zhang 2023 RFS; Ritter data page (2026-03-09).

#### Candidates
1. name: Trust-value yield capture
   - family: event-driven / cash-like carry with an embedded option.
   - mechanism: yield to redemption y_t = (T_t/P_t)^{365/τ_t} − 1 where T_t = trust per share, τ_t = days to the expected vote/deadline; buy when y_t > 3-month T-bill + 100 bp; redeem (or sell at ≥ T) at the vote; never hold through the merger.
   - sources: Gahng, Ritter, Zhang (2023) RFS 36(9) 3463–3501 ([OUP](https://academic.oup.com/rfs/article-abstract/36/9/3463/7067751)); Klausner, Ohlrogge, Ruan (2022) 39 Yale J. Reg. 228 ([Yale J. Reg.](https://www.yalejreg.com/print/a-sober-look-at-spacs/)).
   - user-material refs: Shreve I pp. 7–8 (risk-neutral pricing of a bond-plus-option payoff, via ARCHITECTURE_REVIEW §0); 재무경제학 Ch5 p. 7 (Fisher equation for the T-bill benchmark).
   - data needs: SPAC list with trust per share and deadlines (Ritter file + EDGAR), daily prices, T-bill (FRED DTB3).
   - reachable via: KIS-overseas-stock (common only, UNVERIFIED), yfinance, FRED, other:<EDGAR>.
   - backtest design: monthly screen at close t, buy t+1, exit at the vote or when P > T; 10 bp per side; benchmark: 3-month T-bill; universe: US SPACs 2018–2026.
   - pre-registered validation criterion: net excess over T-bill > 1% p.a. with zero deal-completion losses (positions must be exited before the merger date in 100% of cases in the backtest).
   - expected edge and decay: low single digits over T-bills; the 2020–21 premium episodes are unlikely to recur.
   - implementation complexity: 4 (deadline tracking; redemption mechanics cannot be executed via API — only "sell at ≥ trust").
   - caveats: a Korean retail account cannot tender for redemption programmatically; extension votes move deadlines.

### Asset 6 — KRX gold spot (KRX금시장)
- asset: 1g-unit spot gold on KRX, 99.99% bars custodied at KSD.
- explanation: exchange-traded physical gold priced in KRW/g; international parity P* = XAUUSD × USDKRW / 31.1035.
- market structure: KRX general-commodity market; members are 13 securities firms and 79 bullion dealers (2023-12); LPs must keep the close within ±6% of the international price and spreads ≤ 3%.
- access from Korea: KIS-domestic — a 금현물 계좌 at KIS/Kiwoom/etc. ([KRX participation page](https://open.krx.co.kr/contents/OPN/01/01050203/OPN01050203.jsp)); tax: 양도세·배당세 exempt, VAT exempt unless withdrawn (KRX/broker pages; VAT text UNVERIFIED verbatim). KIS API coverage of 금현물 quotes is UNVERIFIED (portal categories show 국내주식/선물옵션/채권, not 일반상품).
- profit generation: directional gold exposure without the 15.4% dividend-tax drag of ETFs; the KRX premium/discount vs parity is bounded by the LP rule.
- distinguishable facts: a regulatory ±6% band around the international price — a structural, publicly stated mean-reversion constraint.
- keyless data: KRX Data Marketplace gold pages ([data.krx.co.kr](https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201060201), keyless web; POST-JSON internals undocumented); KRX Open API with a free key; GC=F and DEXKOUS (Yahoo/FRED) for parity.
- verified from: KRX participation page (2026-09-25 browser read); KRX gold page; Shinhan page; KRX Open API search summary.

#### Candidates
1. name: KRX gold premium monitor (no trade claim)
   - family: relative value / market segmentation monitor.
   - mechanism: prem_t = P_KRX,t / P*_t − 1; report level, 1y z-score, distance to the ±6% LP band; flag when |prem_t| > 3%.
   - sources: KRX LP rule ([KRX](https://open.krx.co.kr/contents/OPN/01/01050203/OPN01050203.jsp)); no academic paper found (gap).
   - user-material refs: Shreve II 9.3 (quanto/FX parity logic, p. 385); 계량2 Ch1 p. 13 (white-noise test on the premium's changes).
   - data needs: daily KRX gold close, GC=F, USDKRW.
   - reachable via: other:<KRX Data Marketplace>, yfinance, FRED.
   - backtest design: n/a (monitor); a reversal test (buy at prem < −2%, sell at 0) can be run with 0.3% round-trip cost, benchmark: gold parity.
   - pre-registered validation criterion: premium changes show negative first-order autocorrelation (Ljung–Box rejects white noise) — otherwise the monitor is descriptive only.
   - expected edge and decay: none claimed.
   - implementation complexity: 2.
   - caveats: KRX gold trades Korean hours; parity uses a New York noon fixing (H.10) or Yahoo — timing mismatch of several hours.

### Asset 7 — KOSPI 200 options: box-spread implied funding rate
- asset: KOSPI 200 index options (KRX), European, cash-settled.
- explanation: for strikes K1 < K2 and maturity T, the box B = [C(K1) − C(K2)] + [P(K2) − P(K1)] pays K2 − K1 with certainty; the implied continuously-compounded rate is r_box = −ln(B/(K2 − K1))/T (ACT/365, matching the app's convention).
- market structure: one of the world's most liquid index-option markets; liquidity concentrated in OTM strikes; efficiency documented (few box arbitrages, 2–8% of 1-minute observations in 2003–04).
- access from Korea: KIS-domestic 국내선물옵션 (KIS API category exists); prerequisites: derivatives account and the 사전교육/모의거래 regime for retail (not re-verified here).
- profit generation: as a trade, essentially none for retail (efficient); as an indicator, the implied KRW funding rate vs CD91/KOFR is the rates-desk use.
- distinguishable facts: the box is a synthetic zero-coupon bond — the rates desk's "options as funding" idea (CME 2024 note) applied to KOSPI 200.
- keyless data: KRX 만기별 가격표(옵션) ([data.krx.co.kr](https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201070206)); KIS API 국내선물옵션 quotes with the existing key.
- verified from: 이재하·한덕희 KDA paper (PDF parsed 2026-09-25); CME Group 2024 article; Ronn & Ronn (1989) RFS 2, 91–108 cited in that paper's references.

#### Candidates
1. name: Box-implied KRW rate vs money-market curve
   - family: rates indicator / synthetic funding.
   - mechanism: daily, for the front two expiries, choose ATM-bracketing K1, K2 with mid quotes; compute r_box; compare with CD91, KOFR and the app's KRW short rate; report the spread in bp and its 1y z-score.
   - sources: 이재하·한덕희, "KOSPI200 옵션시장에서의 박스스프레드 차익거래 수익성" ([KDA PDF](https://www.kdajdqs.org/bbs/presentation/295/download/311)); CME Group (2024) box-spread financing note ([CME](https://www.cmegroup.com/articles/2024/index-options-box-spreads-as-financing-tool.html)).
   - user-material refs: 재무경제학 syllabus Ch. 20 (options and forwards, Nov 30) and Ch. 15 (term structure); Shreve I pp. 7–8 (no-arbitrage pricing of a riskless payoff); the app's FICC conventions (ACT/365, continuous zeros).
   - data needs: daily option settlement prices by strike and expiry; CD/KOFR (FRED has no KOFR — source from BOK ECOS, key required, or KRX; UNVERIFIED keyless).
   - reachable via: KIS-domestic (국내선물옵션 API), other:<KRX Data Marketplace>.
   - backtest design: n/a; validation is agreement of r_box with CD91 within ±30 bp on median days.
   - pre-registered validation criterion: median |r_box − CD91| < 30 bp over 2024–2026; otherwise the strike/quote selection is wrong.
   - expected edge and decay: indicator only.
   - implementation complexity: 2.
   - caveats: settlement vs mid prices; wide OTM spreads; near-expiry boxes are noisy.

### Asset 8 — Korean ex-dividend capture (KRX cash equities)
- asset: KOSPI/KOSDAQ dividend payers around the year-end (and quarterly) record dates.
- explanation: price-drop ratio PDR = (P_cum − P_ex)/D; if PDR < 1 − τ_d (τ_d the effective dividend tax) a cum-buy/ex-sell earns the difference net of costs.
- market structure: KRX; since July 1998 the exchange no longer sets an ex-adjusted reference price for cash dividends; record-date-before-dividend-decision practice ("깜깜이 배당") has been under reform.
- access from Korea: KIS-domestic (existing key); legal and ordinary; costs: commission, securities-transaction tax (current rates UNVERIFIED here), 15.4% dividend withholding.
- profit generation: incomplete price drop on the ex-date; post-ex-date one-month drift (+1.8% KOSPI, +6.1% KOSDAQ, 2010–2020 averages).
- distinguishable facts: Korean-specific institutional feature (no exchange ex-adjustment since 1998) and a measured after-tax holding-period return of 8.9% in 1998–99 vs 4.7% in 1997 — with the author's own warning that it is not risk-free.
- keyless data: KRX/KIS prices (existing), DART dividend disclosures (existing OpenDART key), KIND for record dates.
- verified from: 김성민 (2003) 재무관리논총 9(1) 189–219; 경향신문 2021-12-27.

#### Candidates
1. name: Cum-to-ex capture with PDR filter
   - family: event-driven / tax-clientele.
   - mechanism: for each stock with announced D and expected yield y = D/P_cum > 3%, buy at close on cum-date t, sell at close on ex-date t+1 (or hold h = 20 days for the drift variant); return = (P_{t+1} + D(1 − 0.154) − P_t)/P_t − costs.
   - sources: 김성민 (2003) ([KoreaScience](https://koreascience.kr/article/JAKO200308508084531.page)); 경향신문 (2021-12-27) for the post-ex drift figures ([경향](https://www.khan.co.kr/article/202112271449001)).
   - user-material refs: Shreve II 5.5 (dividends and the ex-dividend price drop under Q, pp. 235–237, via ARCHITECTURE_REVIEW §0); 재무경제학 Ch5 pp. 8–9 (expected return across scenarios); 계량2 Ch1 p. 17 (Ljung–Box on the event-window residuals).
   - data needs: dividend amounts and record dates (DART/KIND), daily closes.
   - reachable via: KIS-domestic, other:<OpenDART>, other:<KIND>.
   - backtest design: event study, signal known at t (dividend announced before record date — only the post-2024 "배당 후 확정" names qualify without look-ahead), earn t+1; cost 30 bp round trip incl. tax; benchmark: KOSPI over the same window; universe: KOSPI 200 dividend payers 2015–2026.
   - pre-registered validation criterion: mean net event return > 0 with t > 2 across ≥ 200 events; result must hold in both halves of the sample.
   - expected edge and decay: small (tens of bp per event); crowded at year-end.
   - implementation complexity: 3 (record-date calendar and the pre-announcement filter).
   - caveats: many Korean firms still set the record date before the dividend amount is known — using the later-announced D is look-ahead; only announced-before-record-date events are valid.

### Asset 9 — Korean IPOs (공모주) — analysis surface
- asset: KRX new listings; first-day return r_1 = P_close,1/P_offer − 1.
- explanation: underpricing is the documented anomaly (Korea avg 33% in 2006–10-era samples; ≈ 52% long-run average, highest in the OECD per KCMI 2024).
- market structure: bookbuilding with retail 청약 allocation via underwriters; since 2023 the first-day price range is 60–400% of the offer price (KCMI summary; not read verbatim — UNVERIFIED).
- access from Korea: KIS-domestic for secondary trading; allocation is a broker subscription process, not an API action; legal and ordinary.
- profit generation: allocation-to-open flip; short-run reversal thereafter (48% below offer within a month, 곽노걸·전상경 2015).
- distinguishable facts: extreme and persistent underpricing; the first-month reversal.
- keyless data: KIND 공모가 대비 주가등락률 ([KIND](https://kind.krx.co.kr/listinvstg/pubprcCmpStkprcByIssue.do?method=pubprcCmpStkprcByIssueMain)); Ritter IPOs-Korea.pdf.
- verified from: 곽노걸·전상경 2015 재무관리연구; KCMI 2024-02-19; 한국경제 2024-09-18; Ritter data page 2026-03-09.

#### Candidates
1. name: First-day return regression and post-listing reversal study
   - family: event study (analysis only; no executable signal via API).
   - mechanism: r_1 = a + b_1·log(청약경쟁률) + b_2·log(size) + b_3·market_20d + ε; second stage: r_{1→21} on r_1 (reversal test).
   - sources: 곽노걸·전상경 (2015) ([KCI](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002003670)); KCMI 김민기 (2024) ([KCMI](https://www.kcmi.re.kr/publications/pub_detail_view?syear=2024&zcd=002001016&zno=1769&cno=6278)).
   - user-material refs: 계량2 Ch2 p. 11 (regression form and OLS asymptotics); Roadmap pp. 12, 28 (multiple testing across specifications).
   - data needs: KIND table, daily closes for 21 days post-listing.
   - reachable via: other:<KIND>, KIS-domestic.
   - backtest design: n/a (no tradable entry at the offer price through the app); report a "sell at open of day 2 vs hold 21 days" comparison for information.
   - pre-registered validation criterion: the reversal coefficient is negative with t < −2 on 2019–2026.
   - expected edge and decay: n/a.
   - implementation complexity: 2.
   - caveats: allocation is the edge, and it is not modelable.

### Asset 10 — Korean listed REITs (P/NAV)
- asset: 23 KRX-listed REITs (KAREIT, 2026-09-25).
- explanation: P/NAV = price / appraised NAV per share; discounts of 50–60% observed in 2026-06.
- market structure: KRX common stock; NAV from periodic appraisals disclosed on DART; no regular revaluation (Samsung Securities 2021).
- access from Korea: KIS-domestic (existing key); ordinary equity taxation (dividends 15.4%; the REIT 분리과세 regime not researched).
- profit generation: discount narrowing on rate cuts/asset sales/buybacks; high dividend yield while waiting.
- distinguishable facts: discounts far deeper than US CEF norms; no Korean academic evidence on reversion (gap).
- keyless data: prices (KIS/KRX), NAV from DART filings (OpenDART key already in app), KAREIT statistics page.
- verified from: 이데일리 2026-06-23; KAREIT page; Samsung Securities note (search result).

#### Candidates
1. name: P/NAV monitor with US-CEF-style reversal test
   - family: value / monitor.
   - mechanism: as Asset 3 candidate 1 with NAV from DART appraisals (quarterly/semi-annual), interpolated; z-score of P/NAV per REIT.
   - sources: Pontiff (1995, 1996) as the theoretical anchor; 이데일리 (2026-06-23) for the current state ([이데일리](https://edaily.co.kr/News/Read?mediaCodeNo=257&newsId=05129926645484672)).
   - user-material refs: 재무경제학 syllabus Ch. 18 (equity valuation, Nov 23); 류거시 topic02 pp. 3–4 (rates and asset demand).
   - data needs: DART NAV disclosures, daily prices, KOFR/CD for the rate link.
   - reachable via: KIS-domestic, other:<OpenDART>.
   - backtest design: monthly, long bottom-quartile P/NAV, 20 bp round trip, benchmark: equal-weight REIT basket; 2019–2026.
   - pre-registered validation criterion: net alpha vs the basket > 0 with t > 2 — with only 23 names and ~7 years, treat any result as descriptive.
   - expected edge and decay: unknown.
   - implementation complexity: 3 (NAV parsing from DART).
   - caveats: tiny cross-section; NAV appraisal lags; rights issues at discounts dilute.

### Asset 11 — ELS/DLS (structured notes) — analysis object for the structuring page
- asset: Korean autocallable ELS (worst-of on S&P500/EuroStoxx50/KOSPI200), DLS (rate-linked), principal-protected ELB/DLB.
- explanation: retail-distributed notes whose fair value = zero-coupon bond ± embedded (worst-of, knock-in) options; the app already prices reverse convertibles and PPNs.
- market structure: issued by securities firms, public offering, no secondary market; hedged 69.4% in-house and 30.6% back-to-back (77.5% with foreign counterparties) as of end-2025.
- access from Korea: subscription at the issuing broker; not tradable through any API; analysis only.
- profit generation (issuer side): distribution margin and hedge P&L; (investor side): coupon for selling worst-of put/knock-in risk.
- distinguishable facts: 95.1조원 outstanding; underlying concentration S&P500 14.7조원 / EuroStoxx50 14.3조원 / KOSPI200 13.9조원 (2025 issuance); ELS realised 7.8% in 2025 vs −4.7% in 2024.
- keyless data: FSS press releases (via news), KOFIA statistics; index histories via Yahoo.
- verified from: 뉴스핌 2026-05-06 (FSS figures); BOK Issue Note 2015-11-23.

#### Candidates
1. name: Worst-of autocallable pricer and issuer-hedge sheet (structuring term project input)
   - family: pricing/structuring (no P-side edge claimed).
   - mechanism: Monte Carlo under Q with the app's GARCH-t or GBM paths for three indices with a correlation matrix; payoff: early redemption at observation dates if worst-of ≥ barrier_k; knock-in put if worst-of < KI at any observation; fair value vs issue price; Greeks and hedge sheet (delta per index, vega, correlation sensitivity).
   - sources: FSS 2025 data ([뉴스핌 2026-05-06](https://www.newspim.com/news/view/20260506000814)); BOK Issue Note ([BOK](https://www.bok.or.kr/portal/bbs/P0002353/view.do?nttId=214097&menuNo=200433)).
   - user-material refs: Shreve II 5.2 (risk-neutral pricing, pp. 214–217) and 11.7 (jumps, pp. 505–513) via ARCHITECTURE_REVIEW §0; From_Radon-Nikodym_to_Fung-Hsieh §5.4 correlation premium (p. 13) — the worst-of is short correlation; QUANTGEN primer (GARCH-t Monte Carlo, risk-neutral drift mode).
   - data needs: index closes, dividend yields, USD/EUR/KRW rates (app), implied-vol proxies (VIX, V-KOSPI; VSTOXX not keyless — UNVERIFIED).
   - reachable via: yfinance, FRED, app internals.
   - backtest design: n/a; validation: price a plain reverse convertible with one underlying and match the app's closed-form within MC error.
   - pre-registered validation criterion: single-underlying limit reproduces the existing reverse-convertible price within 2 × MC standard error.
   - expected edge and decay: n/a.
   - implementation complexity: 3.
   - caveats: correlation and vol inputs are assumptions, not market quotes; the app must label them as such.

### Asset 12 — Prediction markets (Polymarket, Kalshi) — data-only
- asset: binary event contracts priced 0–1.
- explanation: price ≈ risk-neutral probability of the event; favourite-longshot bias documented.
- market structure: Polymarket = on-chain CLOB (Polygon) with public order-book and price-history endpoints; Kalshi = CFTC-regulated DCM with REST/WebSocket/FIX.
- access from Korea: trading is treated as gambling — 방심위 block vote 2026-08-18, police investigations of users under 형법 도박죄 (2026-07); Polymarket's geoblock lists KR as close-only on the frontend; Kalshi's non-US eligibility is per its Member Agreement (Korea's status UNVERIFIED). Verdict: do not trade; reading public data carries no identified legal issue (inference).
- profit generation (in general): favourite-longshot bias, information aggregation lags — not applicable from Korea.
- distinguishable facts: an explicit 2026 Korean gambling determination; public APIs.
- keyless data: Gamma/CLOB endpoints; Kalshi public market data.
- verified from: Polymarket docs; ZDNet Korea 2026-08-18; 주간경향 2026-07-28; Kalshi help 2026-03-20; Wolfers–Zitzewitz 2004; Snowberg–Wolfers 2010.

#### Candidates
1. name: Event-probability feed for the Macro page (FOMC/BOK/ECB decisions)
   - family: data ingestion / indicator (no positions).
   - mechanism: pull the YES price p_t for rate-decision markets; convert to an implied path; compare with FRED fed-funds futures-implied expectations (not in app; UNVERIFIED keyless) or with the app's SOFR curve; display divergence.
   - sources: Wolfers & Zitzewitz (2004) JEP 18(2) ([AEA](https://www.aeaweb.org/articles?id=10.1257%2F0895330041371321)); Polymarket Gamma/CLOB docs ([docs](https://docs.polymarket.com/api-reference/introduction)).
   - user-material refs: 류거시 topic02 (policy rate determination, pp. 3, 16); 재무경제학 Ch5 p. 8 (probability-weighted scenarios).
   - data needs: market IDs for the relevant events.
   - reachable via: other:<Polymarket Gamma/CLOB, public>.
   - backtest design: n/a.
   - pre-registered validation criterion: Brier score of p_t at T−30 days vs realised outcomes < 0.2 over ≥ 30 resolved macro markets.
   - expected edge and decay: none claimed.
   - implementation complexity: 2.
   - caveats: the Korean block may extend to API hosts; the app must never show a P&L for these.

### Asset 13 — KRX carbon allowances (KAU) — document only
- asset: KAU (allowances), KCU/KOC offsets on the KRX ETS market.
- explanation: compliance market for 할당대상업체; 4th planning period 2026–2030; K-MSR stabiliser from late 2026; futures targeted for 2028.
- market structure: KRX ETS platform; participants restricted to allocated firms and named financial institutions (insurers, banks; asset managers under review).
- access from Korea: individuals cannot trade (2026-05-19 source); ETF/ETN access considered for 2028–29.
- profit generation: n/a for retail.
- distinguishable facts: third-largest ETS by the government's estimate; retail-closed.
- keyless data: ETS platform price pages.
- verified from: 이코노믹리뷰 2026-05-19; KRX ETS platform.
- Candidates: none (not investable); revisit when the 2028 futures/ETF timeline materialises.

### Asset 14 — KRX 배당지수선물 (고배당50 / 배당성장50 futures) — document only
- asset: cash-settled futures on two dividend-tilted KOSPI price indices; multiplier 2,000원; tick 0.5p.
- explanation: not dividend-point futures; they are small-multiplier equity-index futures with a yield tilt.
- market structure: KRX derivatives; 7 expiries; limit orders only.
- access from Korea: KIS-domestic 국내선물옵션.
- profit generation: index exposure; a "dividend factor vs KOSPI 200" spread is possible but liquidity is UNVERIFIED (volume not fetched).
- distinguishable facts: the only KRX product family with "배당" in the name; no KOSPI 200 dividend-point future exists per the broker guide.
- keyless data: KRX Data Marketplace derivatives pages.
- verified from: Kiwoom product guide (2026-09-25).
- Candidates: none pre-registered; a factor-spread study is possible later.

### Asset 15 — Interactive Brokers (channel, not an asset) — document only
- access status (2026-09-25): Korea is on IBKR's country list; KRX equities are excluded for Korean residents (2026-05-06 release); direct foreign-securities trading by an individual bypasses the 외국환거래규정 제7-33조 제4항 broker-routing duty (KCMI, BOK FAQ); 5억원 해외금융계좌 reporting applies; market data needs a funded account and paid subscriptions beyond the free US Cboe One/IEX stream. API: TWS/IB Gateway + `ib_async` (read-only calls documented), Client Portal Gateway for retail Web API.
- QUANTGEN decision: no surface; keep this note as the reference in case the user later opens an account for research subscriptions only.

### Asset 16 — Convertible arbitrage — document only
- Evidence: Agarwal, Fung, Loon, Naik (2011) JEF 18(2) 175–194. Access: convertible bonds are not in KIS's overseas categories (stocks, futures/options; domestic 장내채권 only) and no keyless convertible price feed was found. Candidates: none.

---

## Ranking (accessibility from Korea × strength of evidence)

Scores: accessibility A (3 = existing KIS key or keyless data with a legal, ordinary venue; 2 = reachable but with prerequisites/unverified tickers; 1 = closed, illegal or grey), evidence E (3 = top-journal, direct strategy evidence; 2 = top-journal but indirect or Korean-journal evidence; 1 = news/structural only). Product A×E, ties broken by data readiness and implementation complexity.

| # | Asset / surface | A | E | A×E | Action for QUANTGEN |
|---|---|---|---|---|---|
| 1 | VIX futures term structure and ETP drift (Asset 1) | 3 (KIS-overseas-futopt lists VX; Cboe CSV keyless) | 3 (Simon–Campasano 2014 JoD; Eraker–Wu 2017 JFE) | 9 | Add now: data (Cboe VX settlements + FRED VIX) and model (roll-down backtest, ETP replication). |
| 2 | FX momentum / dollar carry / value (Asset 2) | 3 (FRED/Yahoo already wired; execution via KIS-domestic 통화선물) | 3 (Menkhoff et al. JF/JFE 2012, RFS 2017; LRV 2014 JFE; Fama 1984) | 9 | Add now as model extensions of the carry basket (momentum and dollar carry first; value after CPI plumbing). |
| 3 | KOSPI200 box-spread implied rate (Asset 7) | 3 (KIS-domestic API; KRX data) | 2 (이재하·한덕희; Ronn & Ronn 1989 RFS) | 6 | Add as a Rates-page indicator (small). |
| 4 | Korean ex-dividend capture (Asset 8) | 3 (KIS-domestic, DART, KIND) | 2 (김성민 2003; drift statistics) | 6 | Add as an event-study model with the pre-announcement filter; small expected edge. |
| 5 | US closed-end fund discounts (Asset 3) | 2 (KIS-overseas-stock; NAV feed unresolved) | 3 (LST 1991 JF; Pontiff 1995 JFE, 1996 QJE) | 6 | Document now; add when a keyless NAV source is confirmed. |
| 6 | KRX gold premium monitor (Asset 6) | 3 (KIS 금현물 계좌; KRX data keyless-web) | 1 (LP-band structure; no paper) | 3 | Add as a data surface on the Macro page (cheap); no strategy claim. |
| 7 | Korean IPO first-day study (Asset 9) | 2 (KIND data keyless; allocation not via API) | 3 (곽노걸·전상경 2015; KCMI 2024; Ritter) | 6 | Data/analysis surface only (regression + reversal). |
| 8 | US merger arbitrage (Asset 4) | 2 (KIS-overseas-stock; EDGAR keyless; heavy parsing) | 3 (Mitchell–Pulvino 2001 JF) | 6 | Document; build later (complexity 5). |
| 9 | SPAC trust arbitrage (Asset 5) | 2 (common via KIS UNVERIFIED; redemption not via API) | 3 (Klausner et al. 2022; Gahng–Ritter–Zhang 2023 RFS) | 6 | Document. |
| 10 | Korean REIT P/NAV (Asset 10) | 3 (KIS-domestic, DART) | 1 (news; no Korean paper) | 3 | Data surface (P/NAV from DART) — document the strategy. |
| 11 | ELS/DLS structuring object (Asset 11) | 2 (not tradable; analysis) | 2 (FSS data; BOK note) | 4 | Feed the FSS underlying mix and hedge split into the Structuring page; add a worst-of autocallable pricer (term project). |
| 12 | KRX 배당지수선물 (Asset 14) | 3 | 1 | 3 | Document only. |
| 13 | Prediction markets (Asset 12) | 1 (gambling determination 2026-08; trading exposed) | 3 (Wolfers–Zitzewitz 2004; Snowberg–Wolfers 2010) | 3 | Data-only indicator at most; never positions. |
| 14 | KAU carbon (Asset 13) | 1 (retail closed until ≥ 2028) | 1 | 1 | Document; revisit 2028. |
| 15 | IBKR channel (Asset 15) | 1 (legal grey for individuals; paid data) | n/a | — | Document; no surface. |
| 16 | Convertible arbitrage (Asset 16) | 1 (no bond access, no data) | 3 (Agarwal et al. 2011) | 3 | Document only. |

Two corrections to the assignment's premises, for the report writer: Simon & Campasano (2014) is in the Journal of Derivatives 21(3), not the Journal of Portfolio Management; and the 재무경제학 folder does not yet contain CAPM or market-efficiency slides (CAPM is scheduled 2026-09-28 and 10-19; no EMH chapter is on the syllabus), so those theory citations should point to the syllabus, the 계량2 stationarity/Ljung–Box notes, and the user's two papers rather than to slides that do not exist yet.
