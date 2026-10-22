# Crypto holding venues and read-only connectivity for QUANTGEN (Korean resident, September 2026)

Research date: 2026-09-25. Every legal statement carries a source and date. "UNVERIFIED" marks anything I could not confirm from a fetched primary page in this session; "LIVE PROBE" marks a value read directly from a public endpoint on 2026-09-25 through the fetch tool (which runs outside Korea, so it proves the endpoint works, not that it is reachable from a Korean residential IP). The session's web-search budget ran out after the third round, so a few late items rest on direct fetches only.

Context read first: `README.md` (data-source table, "no broker order path"), `docs/ARCHITECTURE_REVIEW.md` §1 (providers sit behind `core/*/data`; explicit provider that fails RAISES, only `auto` degrades to labelled synthetic), `data/krx/kis_client.py` (scope-boundary docstring, token cache holds a token never the key, errors never carry a credential, presence-only `status()`), `config.py` (`_clean`/`_present`, per-family `*_ready()`, `*_provider_status()` returns presence only).

---

## Key question 1 — Korean custodial exchanges (Upbit, Bithumb, Coinone, Korbit→DigitalX, Gopax): legal status, KRW coverage, API auth, keyless endpoints, limits, history depth, libraries

### Takeaway
All five are FIU-registered VASPs; a Korean resident opens an account with a bank real-name account and trades KRW pairs. Every one of them exposes keyless candle/ticker/orderbook REST endpoints (Upbit and Bithumb share an identical `/v1/candles/days` shape, 200 candles per call), and Upbit's KRW-BTC daily history reaches back to 2017-09-25. A read-only balance needs a user-issued key (Upbit: HS512 JWT, "자산조회" scope, 1-year validity, IP whitelist); pyupbit/python-bithumb exist but are unnecessary because the JWT is ~10 lines of stdlib.

### Cited Findings

Legal framework (custodial venues)
- Registration duty: 특정금융정보법 §7 requires VASPs to report (register) with the FIU; §6② extends this to foreign operators doing business in Korea — [FSC press release 2025-03-26](https://www.fsc.go.kr/no010101/84237)
- Only 28 entities are FIU-registered VASPs (Upbit, Bithumb, Coinone, Korbit, Gopax, …); "이를 제외한 나머지 사업자가 한국인을 대상으로 영업하는 행위는 특금법상 모두 불법"; transactions must run through a bank's 실명확인 입출금계정; unregistered operation carries up to 5 years' imprisonment or a ₩50m fine; the newsletter assigns no liability to individual users — [BKL Legal Update, 2026-06-25](https://www.bkl.co.kr/law/insight/newsletter/6614)
- Same count (28 registered) and the FIU line that anything else is illegal; the article says 40 unregistered operators were referred to police on 2026-06-25 — [Nate/뉴스 2026-06-24](https://m.news.nate.com/view/20260624n26549); a search summary of the same event said "12곳 추가 적발" — the two numbers conflict; I could not resolve which is the count for that day.
- Travel Rule: from 2022-03-25 a VASP transferring ≥ ₩1,000,000 of virtual assets to another VASP must send sender/recipient names and addresses with the transfer; records kept 5 years; fines up to ₩30m — [Financial News 2022-03-24](https://www.fnnews.com/news/202203241052270055); FSC press release [3.25일 특정금융정보법상 트래블룰이 시행됩니다](https://www.fsc.go.kr/no010101/77579) (title from search results; page not fetched)
- 가상자산이용자보호법 in force 2024-07-19: user deposits held at a bank, deposit-usage fees paid to users, segregation of user and exchange coins with like-kind holdings, statutory basis to investigate and punish unfair trading, FSS inspection and FSC sanctions — [FSC press release](https://www.fsc.go.kr/no010101/82682); law text at [law.go.kr lsiSeq=261099](https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=261099)
- FIU supervisory-regulation amendment (notice period from 2026-08-20): transfers from an exchange to a personal wallet only to a "본인명의 확인 지갑" (own-name verified wallet); a three-tier risk classification of foreign exchanges; effective date not given in the article — [Nate/뉴스 2026-08-24](https://m.news.nate.com/view/20260824n35558)

Upbit
- Daily candles: `GET https://api.upbit.com/v1/candles/days?market=KRW-BTC&to=<ISO8601>&count=<≤200>`; `count` max 200, default 1; fields `candle_date_time_utc/kst, opening_price, high_price, low_price, trade_price, candle_acc_trade_price, candle_acc_trade_volume, prev_closing_price, change_rate`; no API key; "초당 최대 10회" per IP shared across the candle group — [docs.upbit.com list-candles-days](https://docs.upbit.com/kr/reference/list-candles-days)
- Rate limits: all quotation (public) endpoints 10 req/s per IP in five groups (`market, candle, trade, ticker, orderbook`); exchange (private) `default` group 30 req/s per pocket (covers balance), `order` 12/s; header `Remaining-Req: group=default; min=1800; sec=29` (`min` deprecated) — [docs.upbit.com rate-limits](https://docs.upbit.com/kr/reference/rate-limits)
- Auth for private calls: JWT, HS512 recommended; payload `access_key`, `nonce` (fresh UUID per request), `query_hash` (SHA512 of the query string, only when parameters exist), `query_hash_alg` (defaults to SHA512); header `Authorization: Bearer <jwt>`; "API Key per maximum 10 IPs can be registered"; secret shown only at issuance — [docs.upbit.com auth](https://docs.upbit.com/kr/reference/auth)
- Balance: `GET /v1/accounts`, JWT required, needs the `[자산조회]` key scope, 30 req/s (exchange default group); fields `currency, balance, locked, avg_buy_price, unit_currency` — [docs.upbit.com 전체 계좌 조회](https://docs.upbit.com/kr/reference/전체-계좌-조회)
- IP registration is mandatory when a key is issued with 주문하기 (order) or 출금하기 (withdraw) scope; existing keys usable "until their expiration date" — [Upbit changelog notice (dated 3/12, year not shown on page)](https://docs.upbit.com/kr/v1.5.9/changelog/안내-open-api-키-발급-변경-사항-안내-주문하기-출금하기-사용-시-ip주소-등록-필수)
- Key validity: "Open API Key 토큰의 유효 기간은 1년이며 연장은 불가합니다" — [Upbit support article 4403180359705](https://support.upbit.com/hc/ko/articles/4403180359705-Open-API%EB%A5%BC-%EC%82%AC%EC%9A%A9%ED%95%98%EA%B3%A0-%EC%8B%B6%EC%96%B4%EC%9A%94) (quoted from the search snippet; direct fetch returned HTTP 403)
- LIVE PROBE history depth: `…/v1/candles/days?market=KRW-BTC&to=2017-10-05T00:00:00Z&count=200` returned 10 rows, earliest `candle_date_time_utc` 2017-09-25, close ₩4,322,000 — [api.upbit.com](https://api.upbit.com/v1/candles/days?market=KRW-BTC&to=2017-10-05T00:00:00Z&count=200). Upbit itself launched 2017-10-24 — [Wikipedia](https://en.wikipedia.org/wiki/Upbit); the pre-launch month is presumably imported data.
- LIVE PROBE markets: `GET /v1/market/all?is_details=false` returned 861 market codes; `KRW-BTC`, `USDT-BTC` and `KRW-USDT` all exist — [api.upbit.com](https://api.upbit.com/v1/market/all?is_details=false). The fetch summariser reported exactly 287 codes for each of the KRW-/BTC-/USDT- prefixes; an identical three-way split is implausible and should be recounted locally before quoting.
- LIVE PROBE ticker 2026-09-25 (~07:21 UTC): KRW-BTC `trade_price` 115,142,000; USDT-BTC 84,407.43; KRW-USDT 1,365.00; fields include `trade_price, acc_trade_price_24h, timestamp` — [api.upbit.com ticker](https://api.upbit.com/v1/ticker?markets=KRW-BTC,USDT-BTC,KRW-USDT)
- pyupbit: `pip install pyupbit` plus `pyjwt >= 2.0`; `pyupbit.get_ohlcv("KRW-BTC", count=5, interval="day", to="20201010")` returns a pandas DataFrame (intervals `day, minute1…minute240, week, month`, default count 200); `pyupbit.Upbit(access, secret).get_balances()` — [pyupbit README](https://raw.githubusercontent.com/sharebook-kr/pyupbit/master/README.md)

Bithumb (API 2.0)
- Daily candles: `GET https://api.bithumb.com/v1/candles/days?market=KRW-BTC&to=<yyyy-MM-dd HH:mm:ss, KST>&count=<≤200>`; same field names as Upbit; public, no key; rows newest-first — [apidocs.bithumb.com 일(Day) 캔들 조회](https://apidocs.bithumb.com/reference/일day-캔들-조회.md)
- Limits: public API "분류 항목별 150회" per second per IP; private "분류 항목별 140회"; exceeding "일시적으로 제한" with no documented status code — [apidocs.bithumb.com API 요청 수 제한 안내](https://apidocs.bithumb.com/docs/api-요청-수-제한-안내). Public limit was raised from 135/s to 150/s on 2023-11-02 — [Bithumb changelog 23/11/03](https://apidocs.bithumb.com/changelog/빗썸-api-docs-업데이트-안내-231103)
- Auth: JWT HS256; payload `access_key`, `nonce` (UUID), `timestamp` (ms), plus `query_hash` (SHA-512 of the query string) and `query_hash_alg: "SHA512"` when parameters exist; `Authorization: Bearer <jwt>`; error `NotAllowIP` (401) means the caller IP is not on the key's registered list — [apidocs.bithumb.com 인증 토큰 생성하기](https://apidocs.bithumb.com/docs/인증-토큰-생성하기.md)
- LIVE PROBE: `GET https://api.bithumb.com/v1/market/all?isDetails=false` answers keylessly; `KRW-BTC` is the first entry — [api.bithumb.com](https://api.bithumb.com/v1/market/all?isDetails=false). The summariser counted 1,019 KRW- entries, which looks too high; recount locally.
- python-bithumb on PyPI wraps price, candle, order, balance calls — [PyPI python-bithumb](https://pypi.org/project/python-bithumb/)

Coinone
- Candles: `GET https://api.coinone.co.kr/public/v2/chart/{quote_currency}/{target_currency}?interval=<1m…1d,1w,1mon>&timestamp=<ms>&size=<1–500, default 200>`; public; rate limit not stated on the page — [docs.coinone.co.kr chart](https://docs.coinone.co.kr/reference/chart)
- LIVE PROBE: `GET https://api.coinone.co.kr/public/v2/markets/KRW` → `result: "success"`, BTC listed with `trade_status: 1` — [api.coinone.co.kr](https://api.coinone.co.kr/public/v2/markets/KRW) (summariser counted 481 KRW markets; treat as approximate)

Korbit → DigitalX (Mirae Asset)
- `https://docs.korbit.co.kr/` now 302-redirects to `https://docs.digitalx.miraeasset.com/`; the docs say the former address `https://api.korbit.co.kr` still serves the same API; candles `GET https://api.digitalx.miraeasset.com/v2/candles?symbol=&interval=<1,5,15,30,60,240,1D,1W>&limit=<≤200>&start=&end=`; public, 50 req/s per IP; private auth HMAC-SHA256 or ED25519 with `timestamp`, `signature`, optional `recvWindow` — [docs.digitalx.miraeasset.com](https://docs.digitalx.miraeasset.com/). Rebranding date: UNVERIFIED (not stated on the page).

Gopax
- `GET https://api.gopax.co.kr/trading-pairs/<pair>/candles?start=<ms>&end=<ms>&interval=<1|5|30|1440>&limit=<default 1024>`; public; 20 req/s per IP (orderbook 1/s); response rows `[timestamp, low, high, open, close, volume]`; private auth HMAC-SHA512 over `"t"+timestamp+METHOD+path[+recvWindow][+body]` with headers `api-key, timestamp, signature` — [gopax.github.io/API](https://gopax.github.io/API/)
- Binance holds 67% of Gopax (bought Feb 2023); the FIU accepted the executive-change filing recognising Binance as Gopax's major shareholder on 2025-10-15 — [edaily](https://www.edaily.co.kr/News/Read?newsId=03903206642333576&mediaCodeNo=257), [Money Today 2025-10-16](https://www.mt.co.kr/stock/2025/10/16/2025101611002149440)

### Inferences
- The exchange layer QUANTGEN needs (daily/minute candles, ticker) is keyless on every Korean venue, so no credential is required for KRW price history. Upbit and Bithumb even share a wire format, so one parser serves both.
- A read-only balance is the only reason to hold an exchange key. Upbit's scope model lets the operator issue a key with nothing but "자산조회"; Bithumb's docs show IP enforcement (`NotAllowIP`) for private calls; whether an Upbit 자산조회-only key can skip IP registration is not stated — register the IP regardless.
- Upbit keys die after one year; Settings must surface expiry (see design) or the balance card will fail silently a year later.
- The 2026-08 FIU rule on own-name verified personal wallets affects moving coins to a MetaMask/Ledger address, not reading it; a read-only integration is untouched.

### Gaps
- Trading fees and spreads for each Korean exchange: UNVERIFIED (no fee page was fetched; the search budget ran out). Check each venue's 수수료 page before the note is quoted.
- Whether an Upbit key with only 자산조회 scope can be issued without an IP (the changelog names only order/withdraw as mandatory): UNVERIFIED.
- Upbit `GET /v1/api_keys` (a list of the account's keys with `expire_at`) exists in my memory of the API but was not fetched: UNVERIFIED; if real it is the right way to show key expiry on Settings.
- Coinone rate limit: not stated on the fetched page.
- Bithumb daily-history depth: not probed.

---

## Key question 2 — Global exchanges (Binance, Bybit, OKX, Coinbase, Kraken): can a Korean resident hold an account in 2026; keyless kline/funding/OI/premium endpoints; reachability; ccxt

### Takeaway
None of the five is FIU-registered, so serving Korean residents is unlawful for the operator (특금법 §6②/§7); the FIU has escalated from app-store blocks (2025-03/04, 2026-01) to an agreed plan for pre-emptive site blocking (2026-09-23) and a bill for direct enforcement powers (2026-08-21), but no fetched source assigns liability to the individual user, and the FIU said in January 2026 that web use of Binance remains possible. For QUANTGEN the point is moot: Binance's spot klines (from 2017-08-17), funding history (from 2019-09-10), open interest and premium index are all keyless, and `data-api.binance.vision` is a separate market-data host. ccxt (v4.5.84, 104 exchanges) is not needed for two endpoints.

### Cited Findings

Legal / access status
- 2025-03-25: at the FIU's request Google blocked the Google Play apps of 17 unregistered foreign VASPs (KuCoin, MEXC, Phemex, XT.com, Bitrue, CoinW, CoinEX, ZoomEX, Poloniex, BTCC, DigiFinex, Pionex, Blofin, Apex Pro, CoinCatch, WEEX, BitMart); basis 특금법 §7 and §6②; "users are not penalised" but are advised to check the FIU list and withdraw assets from unregistered platforms — [FSC press release 2025-03-26](https://www.fsc.go.kr/no010101/84237); list of names from [Money Today 2025-03-26](https://www.mt.co.kr/stock/2025/03/26/2025032616073587057)
- 2025-04-11: Apple blocked 14 unregistered foreign VASP apps including KuCoin and MEXC — [FSC press release (title from search results, not fetched)](https://www.fsc.go.kr/no010101/84367); [Digital Asset](https://www.digitalasset.works/news/articleView.html?idxno=26862)
- 2026-01-15: Google announced that from 2026-01-28 only FIU-registered VASPs may distribute exchange apps on Google Play in Korea; Binance, OKX, Bybit, MEXC named; the FIU: "앱을 다운받을 수 없는 것이지, PC 등 웹에서는 바이낸스 이용이 가능하다"; the FIU distinguishes exchange apps from non-custodial wallets (MetaMask, Trust Wallet), which are exempt; Apple "확인 중" — [ZDNet Korea 2026-01-15](https://zdnet.co.kr/view/?no=20260115160058)
- 2026-02-21: the Google block "실제 조치는 적용되지 않았고 21일 현재도 바이낸스 등 주요 해외 거래소 앱은 계속 다운로드가 가능한 상태" — [Daum/뉴스 2026-02-21](https://v.daum.net/v/20260221090206561). Whether it was applied later in 2026: UNVERIFIED.
- 2026-08-21: the FIU proposed a 특금법 amendment giving it direct enforcement powers (site blocking, investigation) over unregistered VASPs; it is a bill, not law — [Nate/뉴스 2026-08-21](https://m.news.nate.com/view/20260821n23844)
- 2026-09-23: the KCSC (방심위) and FIU agreed to block unregistered foreign exchange sites without waiting for a fraud case ("위법성과 예방 조치 필요성만 인정되면 차단 절차에 들어가겠다"); standards to be set "이르면 이달 중"; no statement on user liability — [Asia Economy 2026-09-23](https://view.asiae.co.kr/article/2026092214243195647)
- FIU statement that referrals to foreign exchanges are "미신고 영업 조력" and criminally punishable — [Digital Asset](https://www.digitalasset.works/news/articleView.html?idxno=41616) (search result; not fetched)
- Binance is not FIU-registered and "cannot lawfully serve residents of South Korea" — [wherelegalcrypto.com](https://wherelegalcrypto.com/exchanges/binance/south-korea/) (aggregator; the primary basis is the FSC/BKL material above)

Binance endpoints (all keyless)
- Spot klines `GET /api/v3/klines?symbol=&interval=<1s…1M>&startTime=&endTime=&timeZone=&limit=<default 500, max 1000>`; IP weight 2; base URLs `https://api.binance.com`, `api-gcp`, `api1…api4.binance.com`, `https://data-api.binance.vision` — [Binance spot market-data docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)
- Limits: HTTP 429 with `Retry-After`; repeated violations → HTTP 418 IP ban scaling "from 2 minutes to 3 days"; header `X-MBX-USED-WEIGHT-(intervalNum)(intervalLetter)`; `/api/v3/exchangeInfo` publishes `rateLimits` — [Binance limits docs](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits)
- LIVE PROBE `exchangeInfo`: `REQUEST_WEIGHT` 6,000 per minute; `RAW_REQUESTS` 300,000 per 5 minutes; `ORDERS` 100/10 s and 200,000/day — [data-api.binance.vision exchangeInfo](https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT)
- LIVE PROBE history depth: `klines?symbol=BTCUSDT&interval=1d&startTime=0&limit=1` → first open time 1502928000000 ms = 2017-08-17 00:00 UTC, open 4261.48 — [data-api.binance.vision klines](https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime=0&limit=1)
- USDⓈ-M funding history `GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=&startTime=&endTime=&limit=<default 100, max 1000>`; shares a 500 req / 5 min per-IP limit with `/fapi/v1/fundingInfo`; without times "the most recent 200 records are returned" — [Binance funding-rate-history docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History)
- LIVE PROBE funding depth: with `startTime=1568000000000&endTime=1570000000000` the first record is `fundingTime` 1568102400000 (= 2019-09-10 08:00 UTC), rate 0.00010000 — [fapi.binance.com](https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1568000000000&endTime=1570000000000&limit=5). With `startTime=0` the same endpoint returned the newest records (fundingTime ≈ 1790208000002 = 2026-09-24) — `startTime=0` is treated as unset, so page with explicit windows.
- Open interest: current `GET /fapi/v1/openInterest?symbol=`; history `GET /futures/data/openInterestHist?symbol=&period=<5m…1d>&limit=<≤500, default 30>&startTime=&endTime=` — "Only the data of the latest 1 month is available"; no auth — [Binance open-interest-statistics docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics)
- Premium index `GET https://fapi.binance.com/fapi/v1/premiumIndex?symbol=` → `markPrice, indexPrice, lastFundingRate, nextFundingTime, interestRate, estimatedSettlePrice`; weight 1 with symbol, 10 without — [Binance mark-price docs](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price)

Other global venues (keyless candles)
- Bybit `GET /v5/market/kline?category=<spot|linear|inverse>&symbol=&interval=<1…720,D,W,M>&start=&end=&limit=<1–1000, default 200>`, no auth — [Bybit kline docs](https://bybit-exchange.github.io/docs/v5/market/kline); production bases `https://api.bybit.com`, `https://api.bytick.com` — [Bybit guide](https://bybit-exchange.github.io/docs/v5/guide); IP limit "600 requests within a 5-second window per IP", excess → "403, access too frequent", wait 10 minutes — [Bybit rate-limit docs](https://bybit-exchange.github.io/docs/v5/rate-limit)
- OKX `GET /api/v5/market/candles?instId=&bar=&after=&before=&limit=<≤300>` and `/api/v5/market/history-candles` (limit ≤100); 20 req / 2 s; no auth for public data — [OKX docs](https://www.okx.com/docs-v5/en/). The fetched summary gave the base as `https://openapi.okx.com`; OKX's long-standing documented base is `https://www.okx.com` — which is current: UNVERIFIED.
- Kraken `GET https://api.kraken.com/0/public/OHLC?pair=&interval=<1…21600 min>&since=` — "Returns up to 720 of the most recent entries (older data cannot be retrieved, regardless of the value of since)"; public — [Kraken OHLC docs](https://docs.kraken.com/api/docs/rest-api/get-ohlc-data)
- Coinbase Exchange `GET https://api.exchange.coinbase.com/products/{product_id}/candles?granularity=<60|300|900|3600|21600|86400>&start=&end=` — max 300 candles per request; public (`security: []`) — [Coinbase Exchange candles docs](https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles); rate-limit numbers: UNVERIFIED (page fetched had none)
- ccxt: version 4.5.84 on PyPI, "104 cryptocurrency exchange markets", Python 3 — [PyPI ccxt](https://pypi.org/project/ccxt/); its dependency list: UNVERIFIED (setup.py fetch 404)

Academic background
- Makarov & Schoar (2020), "Trading and arbitrage in cryptocurrency markets", JFE 135(2) 293–319: arbitrage deviations are much larger across countries than within, persist for days to weeks, open up during bitcoin appreciations, and point to capital controls as the segmentation friction — [IDEAS/RePEc record](https://ideas.repec.org/a/eee/jfinec/v135y2020i2p293-319.html); [MIT Sloan summary](https://mitsloan.mit.edu/cfi/trading-and-arbitrage-cryptocurrency-markets)

### Inferences
- For a Korean resident the *operator* side is unlawful and access is being narrowed month by month (apps 2025–26, sites planned 2026-09); holding a Binance account is therefore a shrinking, legally exposed path, and the FIU's own advice (2025-03-26) is to withdraw from unregistered platforms. QUANTGEN should not depend on the user holding one.
- Nothing in the QUANTGEN design needs a global-exchange account: klines, funding, OI and premium index are keyless, and the USDT-quoted series can be paired with Upbit's KRW series and QUANTGEN's existing USDKRW fixing to compute the kimchi premium as a cross-market basis — the Makarov–Schoar object.
- Reachability risk is real: if the KCSC blocks `binance.com` domains, `api.binance.com` may go with it. `data-api.binance.vision` is a distinct host and Binance lists it as a market-data base; whether a Korean block would include it is unknowable in advance, so the client must treat Binance as an explicit provider that RAISES on failure (the repo's existing rule), with Upbit as the always-available KRW source.
- ccxt adds a 100-exchange abstraction (and a large dependency surface) to wrap two GET calls; skip it.

### Gaps
- Reachability of `api.binance.com` / `fapi.binance.com` / `data-api.binance.vision` from a Korean residential IP on 2026-09-25: UNVERIFIED (fetch tool is outside Korea). Add a Settings probe (see design).
- Whether the Google Play block was ultimately applied after 2026-02-21, and Apple's 2026 stance: UNVERIFIED.
- Any Korean statute penalising an individual for *using* an unregistered exchange: none found in fetched sources; absence of evidence, not evidence of absence.
- Global-exchange fees: UNVERIFIED.

---

## Key question 3 — Non-custodial wallets (MetaMask, Rabby, Phantom), hardware wallets (Ledger, Trezor), read-only on-chain access, DeFi venues

### Takeaway
A wallet's public address (or a hardware wallet's xpub) is all a read-only integration needs: `eth_getBalance` via any JSON-RPC provider, token balances/transfers via Etherscan-style explorer APIs (free key: 3 calls/s, 100k/day), Solana balances via the public RPC (100 req/10 s per IP), and Hyperliquid positions via an unauthenticated `POST /info` with the address. The app must never hold a private key or seed phrase; the FIU treats non-custodial wallets as outside the VASP app blocks, and its August 2026 rule only touches transfers *to* personal wallets.

### Cited Findings

EVM (MetaMask, Rabby, Ledger/Trezor EVM accounts)
- `eth_getBalance` JSON-RPC: `{"jsonrpc":"2.0","method":"eth_getBalance","params":["0x<address>","latest"],"id":1}`; Alchemy endpoint `https://eth-mainnet.g.alchemy.com/v2/{apiKey}`; 20 compute units per call — [Alchemy eth_getBalance reference](https://www.alchemy.com/docs/reference/eth-getbalance)
- Alchemy free tier: "Free 30M CU per month", 25 requests/s, 500 CU/s — [Alchemy pricing](https://www.alchemy.com/pricing)
- Etherscan API free plan: "3 calls/second, up to 100,000 calls/day, selected chains only" — [docs.etherscan.io rate-limits](https://docs.etherscan.io/resources/rate-limits). (A search summary of an older page said 5 calls/s; the fetched page says 3 — use 3.) V2 URL pattern `https://api.etherscan.io/v2/api?chainid={CHAIN_ID}&module={MODULE}&action={ACTION}&…&apikey={API_KEY}` — [search summary citing docs.etherscan.io](https://docs.etherscan.io/etherscan-v2/rate-limits) (pattern not confirmed on a fetched page: UNVERIFIED); the docs index lists "Get Native Balance for an Address", "Get ERC20-Token Account Balance", "Get ERC20 Token Transfers by Address" — [docs.etherscan.io llms.txt](https://docs.etherscan.io/llms.txt)
- web3.py: `pip install web3`; `w3 = Web3(Web3.HTTPProvider('https://<your-provider-url>'))` — [web3.py quickstart](https://web3py.readthedocs.io/en/stable/quickstart.html); `Eth.get_balance(account, block_identifier=…)` returns wei; `web3.from_wei(balance, 'ether')` — [web3.py eth API](https://web3py.readthedocs.io/en/stable/web3.eth.html)

Solana (Phantom)
- Public mainnet RPC `https://api.mainnet.solana.com`: 100 requests / 10 s per IP, 40 / 10 s for a single RPC method, 40 concurrent connections; "not intended for production applications" — [solana.com clusters](https://solana.com/docs/references/clusters). (The legacy hostname `api.mainnet-beta.solana.com` was not on the fetched page: UNVERIFIED whether it still resolves.)
- `getTokenAccountsByOwner(ownerPubkey, {programId}, {encoding:"jsonParsed"})` returns SPL token accounts for an address — [solana.com RPC docs](https://solana.com/docs/rpc/http/gettokenaccountsbyowner)

Hardware wallets (Ledger, Trezor)
- Ledger Live: Edit account → "Advanced logs" shows the account xpub; Trezor Suite shows the xpub in account details as text and QR — [Koinly help centre](https://support.koinly.io/en/articles/9489974-how-to-get-the-xpub-from-different-wallets-brd-ledger-jaxx-etc), [Koinly hardware-wallet import guide](https://support.koinly.io/en/articles/9489983-how-to-import-data-from-hardware-wallets-ledger-trezor-etc) (secondary sources; Ledger/Trezor primary pages not fetched); watch-only discussion — [Trezor forum](https://forum.trezor.io/t/watch-only-wallet/8142)
- Bitcoin Core issue on importing an xpub from Trezor/Ledger for watch-only use — [bitcoin/bitcoin #12449](https://github.com/bitcoin/bitcoin/issues/12449)

Korean regulatory treatment of self-custody
- FIU: non-custodial wallet services (MetaMask, Trust Wallet) are exempt from the January 2026 app restrictions, which target apps "where operators control user assets" — [ZDNet Korea 2026-01-15](https://zdnet.co.kr/view/?no=20260115160058)
- Exchange → personal-wallet transfers restricted to own-name verified wallets under the FIU's 2026-08 supervisory-regulation amendment — [Nate/뉴스 2026-08-24](https://m.news.nate.com/view/20260824n35558)

DeFi venues
- Hyperliquid: `POST https://api.hyperliquid.xyz/info` with `Content-Type: application/json`; types include `allMids, l2Book, candleSnapshot, userFills, openOrders, portfolio, historicalOrders`; user-specific types take a 42-char hex address; no authentication; time-range responses return at most 500 elements — [Hyperliquid info endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint); perps types `metaAndAssetCtxs` (funding, openInterest, markPx, oraclePx), `clearinghouseState` (address → marginSummary, assetPositions), `fundingHistory` (coin, startTime, endTime), `predictedFundings`, `userFunding` — no auth — [Hyperliquid perpetuals info](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals)
- Hyperliquid is not on the FIU's 28-entity register (the register is exhaustive per BKL 2026-06-25 above); no fetched source names Hyperliquid in an enforcement action: its Korean status is "unregistered foreign platform", user-side consequences UNVERIFIED.
- dYdX v4 indexer, Uniswap/Aave subgraphs on The Graph: not fetched (dYdX docs URL 404) — endpoint patterns UNVERIFIED.

### Inferences
- Everything a read-only integration needs is derivable from a public address; there is no legitimate reason for the app to ever see a private key, seed phrase, or keystore file. The only "credential" is an optional explorer/provider API key for higher limits.
- Hyperliquid's `clearinghouseState` gives perp positions, margin and unrealised P&L from an address alone — the same keyless model as on-chain balances, so a DeFi "position card" costs nothing in credentials.
- For a Korean resident, self-custody is currently the least regulated holding path (no VASP intermediary once coins are off-exchange), but the on-ramp is an FIU-registered exchange and the 2026-08 own-name-wallet rule governs the off-ramp.

### Gaps
- Free-tier public EVM RPCs (PublicNode, LlamaRPC, Cloudflare) were not fetched; their URLs and limits are UNVERIFIED.
- Blockscout REST API as a keyless Etherscan alternative: UNVERIFIED.
- Ledger/Trezor primary documentation on xpub export: not fetched (secondary Koinly guides only).
- Effective date and thresholds of the 2026-08 FIU own-name-wallet rule: not in the fetched article.

---

## Key question 4 — Wallet-free exposure: US spot ETFs, CME futures, Korean crypto equities, Korean spot bitcoin ETF

### Takeaway
As of 2026-09-25 a Korean broker still may not broker overseas spot bitcoin/ether ETFs (FSC, January 2024; reconfirmed when brokers were told in November 2025 to halt GDLC/EZPZ), and bitcoin derivatives including CME futures have been off-limits to Korean brokers since 2017-12-06; futures-based ETFs are the tolerated exception. The government committed on 2026-07-14 to amend the Capital Markets Act in H2 2026 for a domestic spot BTC ETF, but as of 2026-09-01 the bill was drafted, not submitted. Meanwhile crypto-beta equities (한화투자증권 9.84% and 우리기술투자 7.20% of Dunamu) trade on KRX through KIS.

### Cited Findings
- 2017-12-06: FSC — bitcoin is not an underlying asset under the Capital Markets Act, so securities firms may not broker bitcoin-based derivatives; brokers cancelled CME-futures seminars ahead of the 2017-12-18 CME listing — [Newsis 2017-12-06](https://www.newsis.com/view/NISX20171206_0000169057), [Hankook Ilbo 2017-12-06](https://www.hankookilbo.com/news/article/201712061841650267), [YTN](https://www.ytn.co.kr/_ln/0102_201712061450321497)
- January 2024: FSC — "국내 증권사가 해외상장된 비트코인 현물 ETF를 중개하는 것은 가상자산에 대한 기존의 정부 입장 및 자본시장법에 위배될 소지가 있다"; futures ETFs are not in breach — [FSC 보도참고 "미 비트코인 현물 ETF 관련"](https://www.fsc.go.kr/no010101/81456) (title from search results; not fetched), [edaily "현물 ETF 금지… 선물 ETF는 허용"](https://edaily.co.kr/News/Read?mediaCodeNo=257&newsId=01590806638757720), [BeInCrypto Korea](https://kr.beincrypto.com/etf-42/)
- November 2025: brokers' systems had let clients buy Grayscale Crypto Index 5 (GDLC) and Franklin Crypto Index (EZPZ); the FSS told brokers to halt trading, no penalties; "before legislative amendments, supervisory authorities have limited scope to act" — [Invest Chosun 2025-11-21](https://www.investchosun.com/site/data/html_dir/2025/11/20/2025112080229.html)
- 2026-01-09: FSC says a domestic spot BTC ETF is planned for this year and a digital-asset act with a stablecoin framework is forthcoming — [News1 2026-01-09](https://www.news1.kr/finance/blockchain-fintech/6033809)
- 2026-07-14: in the "2026년 하반기 경제성장전략" the FSC will amend the Capital Markets Act in H2 2026 to admit virtual assets as ETF underlying assets; investors would buy through existing securities accounts; the article notes brokers had earlier halted new purchases of overseas spot BTC ETFs — [Hankyung 2026-07-14](https://www.hankyung.com/article/2026071450031); also [ET News](https://www.etnews.com/20260714000493), [SEN TV](https://www.sentv.co.kr/article/view/sentv202607160105)
- 2026-09-01: the bill is drafted but not yet submitted to the National Assembly; listing could follow within 2–3 months of approval; hurdles: custody/DVP, kimchi premium distorting NAV, OTC settlement depth — [Nate/뉴스 2026-09-01](https://m.news.nate.com/view/20260901n33876)
- Korean crypto-beta equities: 한화투자증권 raised its Dunamu (Upbit operator) stake from 5.94% to 9.84%, third-largest holder after 송치형 25.51% and 김형년 13.11% — [Dealsite](https://dealsite.co.kr/articles/162264), [Bizwatch 2026-05-21](https://news.bizwatch.co.kr/article/market/2026/05/21/0003); 우리기술투자 holds 7.20% — [edaily (리서치알음)](https://www.edaily.co.kr/news/read?newsId=01653126628983976&cateNo=&mediaCodeNo=257)

### Inferences
- Through KIS the user can already hold crypto beta three ways without a wallet: KRX equities with Dunamu stakes (KIS domestic), US crypto operating companies such as Coinbase (COIN) and Strategy/MicroStrategy (MSTR) as ordinary overseas stocks (they are equities, not ETFs, so the 2024 guidance does not reach them — this reading is mine; no regulator statement on COIN/MSTR was found), and US bitcoin *futures* ETFs, which the FSC treated as permissible in January 2024. Whether KIS's overseas-stock service currently lists BITO or restricts COIN/MSTR: UNVERIFIED.
- QUANTGEN already has the plumbing for all of these: KRX codes route to `KISClient.daily`, US tickers to FMP/Yahoo. Nothing new to build; the crypto client only adds the direct-coin series.
- A Korean spot BTC ETF is a 2027 story in practice (bill not yet tabled as of September 2026); when it lists it will be a KRX code and flow through the existing KIS path.

### Gaps
- KIS's current handling of COIN/MSTR/BITO orders: UNVERIFIED (not researched; broker-specific).
- Exact FSC document text for the January 2024 guidance: press-release page not fetched (title and quote via edaily/BeInCrypto).
- Status of the Capital Markets Act amendment after 2026-09-01: UNVERIFIED.

---

## Key question 5 — Korean crypto tax status

### Takeaway
Taxation of residents' virtual-asset income starts 2027-01-01 (deferred from 2025 by a December 2024 amendment): 기타소득, ₩2.5m annual deduction, 20% national (22% with local tax), gain = proceeds − actual cost − expenses, with pre-2027 holdings stepped up to max(actual cost, 2026-12-31 market value). Further-deferral bills (to 2029 and 2030) and a 50,000-signature petition were live in August–September 2026, while the finance-minister nominee said 2027 should stand.

### Cited Findings
- Start date 2027-01-01 (postponed two years by the December 2024 amendment); 기타소득 separately taxed; ₩2,500,000 annual deduction; rate 20%; gain = "양도(매매, 교환)·대여의 대가에서 그 양도되는 가상자산의 실제 취득가액과 부대비용을 차감"; assets held on 2026-12-31 take "2026년 12월 31일 당시의 시가와 그 가상자산의 취득가액 중에서 큰 금액" as cost; filed with the May comprehensive return — [National Tax Service](https://www.nts.go.kr/nts/cm/cntnts/cntntsView.do?mi=40370&cntntsId=238935)
- "국회 본회의에서 가상자산 과세 유예를 담은 소득세법 개정안이 의결"; 22% including local tax; formula (profit − ₩2.5m) × 22% — [KB Think](https://kbthink.com/crypto/crypto-tax.html)
- 2026: 김상훈 (국민의힘) bill to defer to 2029 — [Nate/뉴스 2026-08-28](https://m.news.nate.com/view/20260828n30671); 정성국 bill to defer to 2030 — [News1](https://www.news1.kr/finance/blockchain-fintech/6253899); petition for a two-year delay passed 50,000 signatures — [Nate/뉴스 2026-09-14](https://m.news.nate.com/view/20260914n28082); nominee 이형일: "예정대로 2027년부터 과세를 시행하는 것이 바람직" — [The Fact](https://news.tf.co.kr/read/economy/2369328.htm) (all four from search summaries; not individually fetched)

### Inferences
- From 2027 a per-lot cost basis becomes a tax fact. A read-only Upbit client that stores `avg_buy_price` snapshots (and later trade history) is the cheapest way for the user to keep a basis record; this is a legitimate reason to build the read-only balance card beyond portfolio display.

### Gaps
- Exact plenary date of the December 2024 amendment: UNVERIFIED (the two fetched pages say "December 2024" without the day).
- Whether any of the 2026 deferral bills advanced in committee by 2026-09-25: UNVERIFIED.

---

## Key question 6 — Integration design for QUANTGEN (module boundary, key storage, Settings, refusals)

### Takeaway
Mirror `data/krx/kis_client.py`: one module, read-only by construction, keyless first. Phase 1 needs no credentials at all (Upbit + Binance public data); phase 2 adds a read-only Upbit balance behind `UPBIT_ACCESS_KEY`/`UPBIT_SECRET_KEY` with a stdlib HS512 JWT; phase 3 is address-based on-chain/Hyperliquid reads. No ccxt, no web3, no pyupbit: every call is `requests.get` plus ~10 lines of `hmac`.

### Cited Findings
- Repository conventions this design follows: KIS client "exposes exactly four read-only quotation endpoints… Adding an order path would require a new module, a new credential (account number), and an explicit decision"; token cache "holds a token, never the appkey/appsecret"; `KISError` "Never carries a credential in its message"; `status()` is presence-only — `data/krx/kis_client.py` (local file, lines 1–25, 44–46, 258–263)
- `config.py` keeps credential families apart, `_clean` rejects `<placeholder>` values, `*_provider_status()` returns `{"id","label","ready","vars","note"}` with no values — `config.py` (local file, lines 33–45, 196–209, 280–290)
- Routing rule: "explicit provider that fails RAISES; only 'auto' degrades to labeled synthetic" — `docs/ARCHITECTURE_REVIEW.md` §1.1 (local file, line 86)
- The Upbit JWT needs only HS512 over `{access_key, nonce, query_hash, query_hash_alg}` — [docs.upbit.com auth](https://docs.upbit.com/kr/reference/auth); pyupbit's only extra dependency is `pyjwt >= 2.0` — [pyupbit README](https://raw.githubusercontent.com/sharebook-kr/pyupbit/master/README.md)

### Inferences (the design)

Module: `data/crypto/crypto_client.py` (one file; parallel to `data/krx/kis_client.py`). Three thin classes, construction does no network:

```
UpbitPublic   .daily(market, since)      GET /v1/candles/days   pages by `to`, 200/call, sleeps to stay ≤10/s
              .ticker(markets)           GET /v1/ticker
BinancePublic .daily(symbol, since)      GET /api/v3/klines     1000/call, base data-api.binance.vision, fallback api.binance.com
              .funding(symbol, since)    GET /fapi/v1/fundingRate  explicit startTime windows (startTime=0 is ignored)
              .premium(symbol)           GET /fapi/v1/premiumIndex
              .open_interest(symbol)     GET /fapi/v1/openInterest (+ /futures/data/openInterestHist, 1-month window)
UpbitAccount  .balances()                GET /v1/accounts       HS512 JWT via hmac/hashlib/base64/uuid; scope 자산조회 only
```

Scope-boundary docstring, verbatim in spirit from the KIS client: "This client exposes exactly N read-only endpoints. No order, cancel, withdrawal, deposit-address or transfer path exists here or anywhere in this repository. Adding one would require a new module, a key with 주문하기/출금하기 scope, and an explicit decision."

Key storage: `.env` → `UPBIT_ACCESS_KEY`, `UPBIT_SECRET_KEY` read through `config._clean`; add `upbit_ready()`, `upbit_credentials()` and a `crypto_provider_status()` list in `config.py` beside `krx_provider_status()`. No token cache is needed (Upbit JWTs are per-request, unlike the KIS 24-hour bearer). Never log, never put a key in an exception, never write a key to `~/.nextgen`.

History and caching: Upbit KRW-BTC daily from 2017-09-25 (~3,300 rows → ~17 calls, 2 s at 10/s); Binance BTCUSDT from 2017-08-17 (4 calls at 1000/call). Reuse the FICC disk cache (`config.ficc_cache_dir()`, 6-hour TTL) rather than a new cache.

Wiring: register `KRW-BTC`-style and `BTCUSDT`-style symbols in `core/markets` so `history.load_history` can route a crypto symbol to `UpbitPublic`/`BinancePublic` exactly as 6-digit codes route to KIS; Quant Lab's GARCH-t pipeline then works on crypto unchanged. New surfaces stay small: a "Crypto" card (or a row on Macro) showing (a) kimchi premium = Upbit KRW-BTC ÷ (Binance BTCUSDT × USDKRW from the existing FRED/Yahoo fixing) − 1, in bp, with its one-year z-score like the other Macro indicators; (b) Binance funding rate, annualised as an implied carry (rate × 3 × 365) in percent, with the premium index; (c) optional Upbit balances with `avg_buy_price` as a cost-basis record for the 2027 tax regime.

Settings page reports (presence and probes only, never values):
- "Upbit public data — keyless — last probe OK/FAIL at <time>" (probe = `GET /v1/market/all`)
- "Binance public data — keyless — data-api.binance.vision OK/FAIL, api.binance.com OK/FAIL" (the reachability question the research could not answer from outside Korea)
- "Upbit account (read-only balances) — UPBIT_ACCESS_KEY / UPBIT_SECRET_KEY present: yes/no — scope must be 자산조회 only; IP must be on the key's allowlist; keys expire one year after issuance" (if `GET /v1/api_keys` exists, show `expire_at`; else show the `.env` set date the operator types in)
- One fixed line: "No order, withdrawal or transfer path exists in this repository."

Tests (hermetic, like `tests/run_all.py`): patch `requests.get` to raise and assert `auto` degrades to a labelled synthetic series while explicit `upbit`/`binance` RAISE; a JWT self-check that decodes the stdlib token and finds `access_key`, `nonce`, `query_hash_alg == "SHA512"`; a paging check that `daily(since=2017-09-01)` requests `to` cursors that never overlap.

### Gaps
- Whether Upbit's `/v1/api_keys` endpoint exists with `expire_at`: UNVERIFIED (see KQ1).
- Whether the FICC cache module accepts non-FICC keys without modification: not checked in this session (small local read).

---

## Options for QUANTGEN

### Option A — Upbit public data (KRW pairs)
- kind: custodial_exchange (public data only)
- region: Korea
- auth model: none for quotation endpoints
- public keyless endpoints and rate limits: `GET https://api.upbit.com/v1/candles/days?market=&to=&count=≤200`; `/v1/candles/minutes/{1,3,5,15,30,60,240}`; `/v1/ticker?markets=`; `/v1/orderbook?markets=`; `/v1/market/all`; 10 req/s per IP per group (market, candle, trade, ticker, orderbook)
- private endpoints needed for a read-only balance: none in this option
- Python library: `requests` (installed); pyupbit not needed
- history depth: KRW-BTC daily from 2017-09-25 (LIVE PROBE)
- Korean regulation status: Upbit is one of 28 FIU-registered VASPs; public data use is unregulated — [BKL 2026-06-25](https://www.bkl.co.kr/law/insight/newsletter/6614)
- fees and spreads: not applicable to data; trading fee UNVERIFIED
- QUANTGEN connection design: `data/crypto/crypto_client.py::UpbitPublic`; no key; Settings shows "keyless, last probe"; UI: KRW-BTC/ETH histories into Quant Lab, kimchi-premium numerator
- risks: 200-row paging and the 10/s ceiling (throttle in client); market list is large (861 codes) — whitelist a handful
- verified from: https://docs.upbit.com/kr/reference/list-candles-days ; https://docs.upbit.com/kr/reference/rate-limits ; https://api.upbit.com/v1/candles/days?market=KRW-BTC&to=2017-10-05T00:00:00Z&count=200 ; https://api.upbit.com/v1/ticker?markets=KRW-BTC,USDT-BTC,KRW-USDT

### Option B — Binance public data (USDT spot + USDⓈ-M perps)
- kind: custodial_exchange (public data only; no account)
- region: global (unregistered in Korea)
- auth model: none for market data
- public keyless endpoints and rate limits: `GET https://data-api.binance.vision/api/v3/klines?symbol=&interval=&startTime=&endTime=&limit=≤1000` (weight 2; 6,000 weight/min, 300,000 raw req/5 min per IP; 429 → 418 bans 2 min–3 days); `GET https://fapi.binance.com/fapi/v1/fundingRate` (≤1000/call, 500 req/5 min shared with fundingInfo); `/fapi/v1/premiumIndex` (weight 1); `/fapi/v1/openInterest`; `/futures/data/openInterestHist` (≤500, last 1 month only)
- private endpoints needed for a read-only balance: none — and the design deliberately never adds a Binance account key
- Python library: `requests`; ccxt not needed
- history depth: BTCUSDT daily from 2017-08-17; funding from 2019-09-10 08:00 UTC (both LIVE PROBE); OI history 1 month
- Korean regulation status: Binance is not FIU-registered; app blocks 2026-01-28 (announced, not applied by 2026-02-21); KCSC/FIU agreed on pre-emptive site blocking 2026-09-23; FIU (2026-01-15) said web use remains possible; no user-side penalty found — [ZDNet 2026-01-15](https://zdnet.co.kr/view/?no=20260115160058), [Asia Economy 2026-09-23](https://view.asiae.co.kr/article/2026092214243195647), [FSC 2025-03-26](https://www.fsc.go.kr/no010101/84237)
- fees and spreads: not applicable to data
- QUANTGEN connection design: `BinancePublic`; explicit provider RAISES on failure; Settings probes both hosts; UI: kimchi-premium denominator, funding-as-carry, premium index, OI
- risks: possible Korean network block of binance.com domains (data-api.binance.vision may or may not be included) — mitigated by the Settings probe and Upbit as the always-on KRW source; `startTime=0` ignored on fundingRate (page with explicit windows)
- verified from: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints ; https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits ; https://data-api.binance.vision/api/v3/exchangeInfo?symbol=BTCUSDT ; https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime=0&limit=1 ; https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History ; https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&startTime=1568000000000&endTime=1570000000000&limit=5 ; https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Open-Interest-Statistics ; https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price

### Option C — Upbit read-only account balance
- kind: custodial_exchange (private, read-only)
- region: Korea
- auth model: HS512 JWT `{access_key, nonce(UUID), query_hash(SHA512), query_hash_alg}` in `Authorization: Bearer`; key issued in Upbit web with scope 자산조회 only; up to 10 allow-listed IPs; key valid 1 year, not extendable
- public keyless endpoints: as Option A
- private endpoints needed for a read-only balance: `GET https://api.upbit.com/v1/accounts` (30 req/s, exchange default group) → `currency, balance, locked, avg_buy_price, unit_currency`
- Python library: stdlib `hmac`, `hashlib`, `base64`, `json`, `uuid` + `requests`; pyupbit/pyjwt not needed
- history depth: snapshot only (no history from this endpoint)
- Korean regulation status: holder must be a real-name-account customer of an FIU-registered VASP (특금법; 이용자보호법 2024-07-19 protects deposits and segregation) — [FSC 2024-07-19](https://www.fsc.go.kr/no010101/82682), [BKL 2026-06-25](https://www.bkl.co.kr/law/insight/newsletter/6614)
- fees and spreads: none for the query
- QUANTGEN connection design: `UpbitAccount.balances()`; `.env` `UPBIT_ACCESS_KEY`/`UPBIT_SECRET_KEY`; `config.upbit_ready()`; Settings: presence, scope reminder, IP reminder, expiry; UI: holdings card with `avg_buy_price` (cost-basis record for 2027 tax)
- risks: key expiry after 12 months; allow-list breaks when the home IP changes; a key accidentally issued with 주문하기 scope would be a live order credential on disk — Settings must tell the operator to issue 자산조회-only and the client must never implement an order path even if the key allows it
- verified from: https://docs.upbit.com/kr/reference/auth ; https://docs.upbit.com/kr/reference/전체-계좌-조회 ; https://docs.upbit.com/kr/reference/rate-limits ; https://support.upbit.com/hc/ko/articles/4403180359705 (via search snippet)

### Option D — Bithumb / Coinone / DigitalX(Korbit) / Gopax public data
- kind: custodial_exchange (public data)
- region: Korea
- auth model: none for candles/ticker
- public keyless endpoints and rate limits: Bithumb `GET https://api.bithumb.com/v1/candles/days?market=&to=&count=≤200` (150 req/s per category per IP); Coinone `GET https://api.coinone.co.kr/public/v2/chart/KRW/BTC?interval=1d&size=≤500`; DigitalX `GET https://api.digitalx.miraeasset.com/v2/candles?symbol=&interval=1D&limit=≤200` (50 req/s; `api.korbit.co.kr` still served); Gopax `GET https://api.gopax.co.kr/trading-pairs/BTC-KRW/candles?start=&end=&interval=1440` (20 req/s)
- private endpoints needed for a read-only balance: Bithumb HS256 JWT (`access_key, nonce, timestamp, query_hash`) with IP allow-list; DigitalX HMAC-SHA256/ED25519; Gopax HMAC-SHA512 — none built in the recommendation
- Python library: `requests`; python-bithumb exists
- history depth: UNVERIFIED (not probed)
- Korean regulation status: all FIU-registered — [BKL 2026-06-25](https://www.bkl.co.kr/law/insight/newsletter/6614); Gopax's major shareholder Binance recognised by the FIU 2025-10-15 — [edaily](https://www.edaily.co.kr/News/Read?newsId=03903206642333576&mediaCodeNo=257)
- fees and spreads: UNVERIFIED
- QUANTGEN connection design: not in phase 1; Bithumb is a drop-in second KRW source (identical `/v1/candles/days` shape) for a cross-exchange KRW basis if ever wanted
- risks: four more parsers for little analytical gain; Upbit already carries the KRW reference
- verified from: https://apidocs.bithumb.com/reference/일day-캔들-조회.md ; https://apidocs.bithumb.com/docs/인증-토큰-생성하기.md ; https://apidocs.bithumb.com/docs/api-요청-수-제한-안내 ; https://docs.coinone.co.kr/reference/chart ; https://docs.digitalx.miraeasset.com/ ; https://gopax.github.io/API/

### Option E — Bybit / OKX / Kraken / Coinbase public data
- kind: custodial_exchange (public data)
- region: global (none FIU-registered; Bybit and OKX named in the 2026-01 Google Play policy)
- auth model: none for candles
- public keyless endpoints and rate limits: Bybit `GET https://api.bybit.com/v5/market/kline?category=&symbol=&interval=&limit=≤1000` (600 req/5 s per IP); OKX `GET /api/v5/market/candles?instId=&bar=&limit=≤300` (20 req/2 s; base host UNVERIFIED); Kraken `GET https://api.kraken.com/0/public/OHLC?pair=&interval=` (last 720 candles only); Coinbase `GET https://api.exchange.coinbase.com/products/{id}/candles?granularity=` (≤300/call; limit UNVERIFIED)
- private endpoints needed for a read-only balance: not applicable (no account recommended)
- Python library: `requests`
- history depth: Kraken 720 rows max; others UNVERIFIED
- Korean regulation status: as Option B
- fees and spreads: not applicable
- QUANTGEN connection design: none — Binance covers the USD reference; add Coinbase (USD, not USDT) only if a USD-vs-USDT basis is ever wanted
- risks: same blocking risk as Binance; Kraken's 720-row cap makes it useless for GARCH calibration history
- verified from: https://bybit-exchange.github.io/docs/v5/market/kline ; https://bybit-exchange.github.io/docs/v5/rate-limit ; https://www.okx.com/docs-v5/en/ ; https://docs.kraken.com/api/docs/rest-api/get-ohlc-data ; https://docs.cdp.coinbase.com/exchange/reference/exchangerestapi_getproductcandles

### Option F — On-chain read-only (MetaMask / Rabby / Ledger / Trezor EVM address; Phantom Solana address)
- kind: onchain_rpc (covers noncustodial_wallet and hardware_wallet holdings)
- region: chain-native; wallet software exempt from Korean VASP app blocks (FIU, 2026-01-15)
- auth model: none for JSON-RPC balance reads on public RPCs; optional provider key (Alchemy: 30M CU/month, 25 rps free) or explorer key (Etherscan free: 3 calls/s, 100k/day) for token lists and transfers
- public keyless endpoints and rate limits: EVM `eth_getBalance` on any RPC (Alchemy `https://eth-mainnet.g.alchemy.com/v2/{key}`, 20 CU); Solana `https://api.mainnet.solana.com` `getBalance` / `getTokenAccountsByOwner` (100 req/10 s per IP, not for production); Etherscan V2 `…/v2/api?chainid=&module=account&action=balance|tokenbalance|tokentx` (pattern UNVERIFIED on a fetched page)
- private endpoints needed for a read-only balance: none — a public address or xpub is the whole input
- Python library: `requests` with raw JSON-RPC (web3.py not needed for `eth_getBalance`; `web3.from_wei` is a division by 1e18)
- history depth: full chain history via explorer `tokentx`/`txlist`; balance is a point read
- Korean regulation status: reading is unregulated; moving coins to the wallet is governed by the Travel Rule (≥ ₩1m, 2022-03-25) and the 2026-08 own-name verified wallet rule — [FNN 2022-03-24](https://www.fnnews.com/news/202203241052270055), [Nate 2026-08-24](https://m.news.nate.com/view/20260824n35558)
- fees and spreads: none for reads
- QUANTGEN connection design: phase 3; `.env` `CRYPTO_WATCH_ADDRESSES` (public addresses only; comma-separated `eth:0x…`, `sol:…`), optional `ALCHEMY_API_KEY`/`ETHERSCAN_API_KEY`; Settings shows count of watched addresses and provider presence; UI: holdings valued with Binance/Upbit prices
- risks: address privacy (an address in `.env` is a public identifier — fine, but never a key); public RPC throttling; token pricing for long-tail assets
- verified from: https://www.alchemy.com/docs/reference/eth-getbalance ; https://www.alchemy.com/pricing ; https://docs.etherscan.io/resources/rate-limits ; https://solana.com/docs/references/clusters ; https://solana.com/docs/rpc/http/gettokenaccountsbyowner ; https://web3py.readthedocs.io/en/stable/web3.eth.html ; https://support.koinly.io/en/articles/9489974-how-to-get-the-xpub-from-different-wallets-brd-ledger-jaxx-etc

### Option G — Hyperliquid perps (DeFi) read-only
- kind: defi
- region: on-chain (Hyperliquid L1); not FIU-registered
- auth model: none — `POST https://api.hyperliquid.xyz/info` with `Content-Type: application/json`
- public keyless endpoints and rate limits: `{"type":"metaAndAssetCtxs"}` (funding, openInterest, markPx, oraclePx), `{"type":"candleSnapshot",…}`, `{"type":"fundingHistory","coin":…}`, `{"type":"predictedFundings"}`, `{"type":"clearinghouseState","user":"0x…"}` (marginSummary, assetPositions), `{"type":"userFunding",…}`; time-range responses capped at 500 elements
- private endpoints needed for a read-only balance: none (address-based)
- Python library: `requests`
- history depth: UNVERIFIED (paging by time windows, 500 per response)
- Korean regulation status: unregistered foreign platform; user-side consequences UNVERIFIED; the 2026-09-23 site-blocking plan targets "unregistered foreign exchange sites" generally
- fees and spreads: not applicable to reads
- QUANTGEN connection design: phase 3, only if the user holds a position; a "DeFi position" card from `clearinghouseState`; cross-venue funding comparison vs Binance
- risks: blocking risk; the app must never hold the wallet key that controls the Hyperliquid account
- verified from: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint ; https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals

### Option H — Wallet-free exposure through KIS (KRX crypto-beta equities, US crypto equities, US futures ETFs; Korean spot ETF when listed)
- kind: broker_etf
- region: Korea (KRX) and US via overseas-stock service
- auth model: existing `KIS_APP_KEY`/`KIS_APP_SECRET` (read-only quotations already implemented); FMP/Yahoo for US tickers
- public keyless endpoints and rate limits: Yahoo Finance via yfinance for US tickers (already in the app)
- private endpoints needed for a read-only balance: none new
- Python library: existing `KISClient`, yfinance
- history depth: KIS daily (existing), Yahoo full history
- Korean regulation status: overseas spot BTC/ETH ETFs may not be brokered (FSC Jan 2024; FSS halt of GDLC/EZPZ Nov 2025); bitcoin derivatives incl. CME futures barred for brokers since 2017-12-06; futures ETFs tolerated (Jan 2024); domestic spot ETF bill drafted, not submitted as of 2026-09-01 — sources in KQ4
- fees and spreads: broker commissions (KIS schedule not researched)
- QUANTGEN connection design: nothing to build; document in the Crypto card that 한화투자증권 (Dunamu 9.84%) and 우리기술투자 (7.20%) are the KRX proxies and that a KRX spot ETF will route through `KISClient` automatically
- risks: proxy beta is noisy; the ETF path can change with one FSC amendment
- verified from: https://www.hankyung.com/article/2026071450031 ; https://m.news.nate.com/view/20260901n33876 ; https://www.investchosun.com/site/data/html_dir/2025/11/20/2025112080229.html ; https://www.newsis.com/view/NISX20171206_0000169057 ; https://dealsite.co.kr/articles/162264

---

## Recommendation

Build order

1. **Phase 1 — keyless public data (Options A + B).** One module `data/crypto/crypto_client.py` with `UpbitPublic` and `BinancePublic`; register crypto symbols in `core/markets`; reuse the FICC disk cache. Ship the kimchi premium (Upbit KRW-BTC vs Binance BTCUSDT × USDKRW), funding-as-carry, premium index and OI on a Crypto card; let Quant Lab calibrate GARCH-t on KRW-BTC and BTCUSDT. Zero credentials, zero new dependencies, and a Settings probe that answers the one question this research could not: whether Binance's hosts are reachable from the user's Korean IP.
2. **Phase 2 — Upbit read-only balance (Option C).** `UpbitAccount.balances()` with a stdlib HS512 JWT; `.env` keys; Settings shows presence, the 자산조회-only and IP-allow-list reminders, and key expiry. Justified twice over: holdings display, and an `avg_buy_price` record before the 2027-01-01 tax start.
3. **Phase 3 — address-based reads (Options F, G), only when the user actually self-custodies or holds a Hyperliquid position.** Public addresses in `.env`, optional Alchemy/Etherscan keys, raw JSON-RPC.
4. **Do not build** Options D and E (extra exchanges) unless a specific cross-venue basis question arises; Bithumb is the natural second KRW source if it does.

Explicit refusals (write them into the module docstring and the Settings page)

- **No order submission, cancellation, withdrawal, deposit-address or transfer endpoint** on any exchange — Upbit `/v1/orders`, `/v1/withdraws`, Binance `/api/v3/order`, Bithumb order/withdraw, Hyperliquid `/exchange` — none of them, on any key, ever. The client must not implement an order path even when the supplied key carries 주문하기 scope; Settings tells the operator to issue 자산조회-only keys.
- **No private key, seed phrase, keystore file, hardware-wallet PIN or passphrase is ever requested, stored, parsed or transmitted.** The only wallet input the app accepts is a public address or xpub. This is a hard refusal, not a configuration.
- **No transaction signing** of any kind (EVM, Solana, Hyperliquid, dYdX): the app is read-only by construction, like the simulated order book in `core/engine`.
- **No account on an unregistered foreign exchange is assumed or encouraged.** Global-venue integration is public data only; the app never asks for a Binance/Bybit/OKX API key.
- **No ccxt, no web3, no pyupbit** — three `requests.get` patterns and ten lines of `hmac` cover every endpoint above; the dependencies would be pure weight.
- **No fee or tax computation presented as advice**: the Crypto card may show a cost-basis snapshot and cite the NTS page; it does not compute a tax liability.
