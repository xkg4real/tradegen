# OKX API v5: read-only account inquiry (for TRADEGEN E1)

This is documentation research only. No key was created or used, and no request was signed.

## Sources and versions

| Source | What it is | Date / version seen |
|---|---|---|
| https://www.okx.com/docs-v5/en/ | Official API v5 guide. It is one long page; links below use its section anchors. | Fetched 2026-10-24. The page shows no version number. The newest changelog entry is 2026-09-30. |
| https://www.okx.com/docs-v5/log_en/ | Official changelog | Newest dated entry 2026-09-30. The "Upcoming Changes" items were last updated 2026-10-16. |
| https://www.okx.com/help/terms-of-service | Official Terms of Service | "Last Updated: 22 October 2026" |
| https://www.okx.com/help/risk-compliance-disclosure | Official Risk and Compliance Disclosure (Section 3 is the list of restricted jurisdictions) | "Last Updated: 8 July 2026" |
| Third-party news (labelled where cited) | Korean regulatory context | Dated where cited |

How the docs were read: WebFetch cuts the docs page off at about 400k of its 2.1M characters. So the raw HTML (5.3 MB) was saved to the scratchpad and parsed locally with a stdlib HTML parser. Every endpoint fact below comes from that copy of the official page, fetched 2026-10-24.

---

## 1. Authentication and key scopes

- **Three secrets per key.** The secrets are the API key, the secret key and the passphrase. "We cannot recover the Passphrase if you have lost it." ([#overview-api-key-creation-generating-an-api-key](https://www.okx.com/docs-v5/en/#overview-api-key-creation-generating-an-api-key))
- **Three permissions, combinable:** "One or more permission can be assigned to any key." ([#overview-api-key-creation-api-key-permissions](https://www.okx.com/docs-v5/en/#overview-api-key-creation-api-key-permissions))
  - Read: "Can request and view account info such as bills and order history"
  - Trade: "Can place and cancel orders, funding transfer, make settings"
  - Withdraw: "Can make withdrawals"
  - Note that funds transfer and account settings (for example, account mode or auto-loan) come under **Trade**, not Read. So a Read-only key cannot change the account mode or turn borrowing on.
- **Keys are created in the website UI only**, through "Please refer to my api page" (link `/account/my-api`). The docs describe no REST endpoint that creates a key for the master account. Sub-account key endpoints exist under Sub-account (`#sub-account-rest-api-create-an-api-key-for-a-sub-account`). Their `perm` values include "read_only: Read only".
- **Self-introspection of the key in use.** `GET /api/v5/account/config` returns:
  - `perm`: "The permission of the current requesting API key or Access token". Values are `read_only`, `trade`, `withdraw`, comma-separated, for example `"read_only,withdraw,trade"`.
  - `ip`: "It is an empty string "" if there is no IP bonded."
  - `label`: the API key note.
  ([#trading-account-rest-api-get-account-configuration](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration))
  - **Use for E1:** a startup self-check can refuse to run unless `perm == "read_only"` and `ip` is non-empty.
- **Is a Read-only key rejected by the server on trade endpoints?**
  - The docs **do not state this explicitly** for each endpoint.
  - Per-endpoint "Permission:" lines appear only on 4 newer endpoints (the GLP v2 endpoints and Flexible Loan e-mode info, all "Permission: Read"). The classic endpoints have no such line.
  - The server-side refusal is implied by error code **50120**: "This API key doesn't have permission to use this function" (HTTP 200). Also 50030: "You don't have permission to use this API endpoint". ([#error-code-rest-api-public](https://www.okx.com/docs-v5/en/#error-code-rest-api-public))
  - Status: implied, not documented as a rule. See the open questions.

## 2. Signature rules and lifetimes

- **Required headers on every private REST call:** `OK-ACCESS-KEY`, `OK-ACCESS-SIGN`, `OK-ACCESS-TIMESTAMP`, `OK-ACCESS-PASSPHRASE`. ([#overview-rest-authentication-making-requests](https://www.okx.com/docs-v5/en/#overview-rest-authentication-making-requests))
- **Timestamp:** "ISO 8601 UTC format with millisecond precision, e.g. 2020-12-08T09:08:57.715Z".
- **Timestamp window: 30 seconds.** "differs from server time by more than 30 seconds (error 50102)". The docs advise syncing with `GET /api/v5/public/time`, and say "Always use UTC".
- **Signature:** "Create a pre-hash string of timestamp + method + requestPath + body". The pre-hash is signed with HMAC SHA256 using the SecretKey, then Base64-encoded. ([#overview-rest-authentication-signature](https://www.okx.com/docs-v5/en/#overview-rest-authentication-signature))
  - Method must be uppercase.
  - "`GET` request parameters are counted as requestpath, not body". The query string is part of what gets signed, for example `/api/v5/account/balance?ccy=BTC`.
  - Body is empty for GET.
- **Lifetimes:** there are no session tokens and no refresh. Each request is signed on its own and is valid only inside the 30-second window. The key itself does not expire, except under the inactivity rule in section 3.
- **WebSocket login** (`op: login`) ([#overview-websocket-login](https://www.okx.com/docs-v5/en/#overview-websocket-login)):
  - The timestamp is in **seconds**: "Unix Epoch time, the unit is seconds".
  - Pre-hash is `timestamp + 'GET' + '/users/self/verify'`.
  - "The request will expire 30 seconds after the timestamp."
  - Login failure is code 60009, "Login failed."
- **Optional `expTime` header** (request deadline in milliseconds). It applies only to place and amend order endpoints, so E1 does not need it. ([#overview-transaction-timeouts-rest-api](https://www.okx.com/docs-v5/en/#overview-transaction-timeouts-rest-api))

## 3. IP binding

([#overview-api-key-creation-api-key-security](https://www.okx.com/docs-v5/en/#overview-api-key-creation-api-key-security))

- "we strongly recommend clients linked the API key to IP addresses". It is recommended, not required, in general.
- "Each API key can bind up to 20 IP addresses". Formats are IPv4, IPv6 and network segments.
- **Inactivity expiry:**
  - Applies to keys "not linked to an IP address and have `trade` or `withdraw` permissions".
  - Such keys "will expire after 14 days of inactivity."
  - "The API key of demo trading will not expire".
- **A Read-only key without IP binding is not covered by the 14-day rule**, as the sentence is written. The docs say nothing more about Read-only keys without IP.
- **What counts as "used":**
  - Only calling "an API that requires API key authentication".
  - On WebSocket, "only operation of logging in" counts.
- Usage records for unbound trade/withdraw keys are visible in the Security Center (web).
- **Related errors:**
  - 50110 (HTTP 401): "Your IP {param0} is not included in your API key's IP whitelist."
  - 50035 (HTTP 403): "This endpoint requires that APIKey must be bound to IP".
  - 50121: "You can't access our services through the IP address ({param0})".
  - Which endpoints raise 50035 is **not documented**.

## 4. Rate limits

General rules ([#overview-rate-limits](https://www.okx.com/docs-v5/en/#overview-rate-limits)):

- "Private REST rate limits are based on User ID (sub-accounts have individual User IDs)."
- "Public unauthenticated REST rate limits are based on IP address."
- WebSocket login and subscribe limits are per connection.
- Rejection is error **50011**: "Rate limit reached...". The error table lists 50011 twice: HTTP 200 "Rate limit reached" and HTTP 429 "Too Many Requests".
- 50013 (HTTP 429): "Systems are busy. Please try again later."
- 50061 is the per-sub-account order-rate cap (1000 order requests per 2 s). It applies to placing and amending orders only, so it does not affect E1.

Per-endpoint limits, quoted from each endpoint's "Rate Limit" and "Rate limit rule" headings:

| Endpoint | Limit | Rule |
|---|---|---|
| GET /api/v5/account/balance | 10 requests per 2 seconds | User ID |
| GET /api/v5/account/positions | 10 requests per 2 seconds | User ID |
| GET /api/v5/account/config | 5 requests per 2 seconds | User ID |
| GET /api/v5/account/instruments | 20 requests per 2 seconds | User ID + Instrument Type |
| GET /api/v5/account/bills | 5 requests per second | User ID |
| GET /api/v5/trade/orders-pending | 60 requests per 2 seconds | User ID |
| GET /api/v5/trade/orders-history (7 days) | 40 requests per 2 seconds | User ID |
| GET /api/v5/trade/orders-history-archive (3 months) | 20 requests per 2 seconds | User ID |
| GET /api/v5/trade/fills (3 days) | 60 requests per 2 seconds | User ID |
| GET /api/v5/trade/fills-history (3 months) | 10 requests per 2 seconds | User ID |
| GET /api/v5/asset/currencies | 6 requests per second | User ID |
| GET /api/v5/asset/balances | 6 requests per second | User ID |
| GET /api/v5/asset/non-tradable-assets | 6 requests per second | User ID |
| GET /api/v5/asset/asset-valuation | 1 request per second | User ID |
| GET /api/v5/asset/deposit-address | 6 requests per second | User ID |
| GET /api/v5/asset/deposit-history | 6 requests per second | User ID |
| GET /api/v5/asset/withdrawal-history | 6 requests per second | User ID |
| GET /api/v5/asset/deposit-withdraw-status | 1 request per 2 seconds | User ID |
| GET /api/v5/finance/savings/balance (Simple Earn) | 6 requests per second | User ID |
| GET /api/v5/system/status | 1 request per 5 seconds | rule not stated |

WebSocket limits ([#overview-websocket-connect](https://www.okx.com/docs-v5/en/#overview-websocket-connect), [#overview-websocket-connection-count-limit](https://www.okx.com/docs-v5/en/#overview-websocket-connection-count-limit)):

- "Connection limit: 3 requests per second (based on IP)".
- Subscribe, unsubscribe and login requests are limited to "480 times per hour" per connection.
- 30 connections per private channel per sub-account. This covers the orders, account and positions channels, among others.
- The connection drops after 30 s without data, so the client should send `ping` and expect `pong`.

## 5. Read-only endpoints for E1

All endpoints below are private (signed) GETs on `https://openapi.okx.com`.

- That is the production REST base URL in the docs ([#overview-production-trading-services](https://www.okx.com/docs-v5/en/#overview-production-trading-services)).
- The 2026-05-20 changelog says `www.okx.com` "will continue to work and will not be deprecated".
- Regional domains: US/AU users use `us.okx.com` and EU users use `eea.okx.com`. The docs say "Using openapi.okx.com will not work for the regions below." A Korean account would be on the global entity, but that is **not documented** for Korea specifically.
- All numbers are returned as strings.

### 5.1 Trading account balance: GET /api/v5/account/balance
([#trading-account-rest-api-get-balance](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-balance))

- **Params:**
  - `ccy` (optional). Up to 20 currencies, comma-separated.
- **Account-level fields:**
  - `totalEq` ("Total account assets denominated in USD")
  - `uTime`
  - `adjEq`, `imr`, `mmr`, `mgnRatio`, `borrowFroz`, `notionalUsd`, `notionalUsdForBorrow`, `upl` (margin modes only; "" when not applicable)
- **Per currency (`details[]`):**
  - Holdings: `ccy`, `eq`, `cashBal`, `availBal`, `frozenBal`, `ordFrozen`, `eqUsd`, `uTime`
  - Spot cost basis: `spotBal`, `openAvgPx`, `accAvgPx`, `spotUpl`, `totalPnl`
  - **Borrowing and lending indicators:**
    - `liab` ("Liabilities of currency"; Spot mode, Multi-currency and PM)
    - `crossLiab`, `interest` ("Accrued interest of currency"), `maxLoan`, `twap` (forced-repayment risk 0–5), `frpType`
    - `autoLendStatus` (`unsupported`, `off`, `pending`, `active`) and `autoLendMtAmt` (the auto-lend matched amount)
- **Notes:**
  - "The currency details will not be returned when cashBal and eq is both 0."
  - "" is returned for fields that do not apply to the current account level.

### 5.2 Positions: GET /api/v5/account/positions
([#trading-account-rest-api-get-positions](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-positions))

- **Params:** all optional.
  - `instType`: MARGIN, SWAP, FUTURES, OPTION or EVENTS. SPOT is not a position type.
  - `instId`: up to 10.
  - `posId`: up to 20.
- **Fields:** `instType`, `mgnMode` (cross/isolated), `posId`, `posSide`, `pos`, `availPos`, `avgPx`, `upl`, `lever`, `liqPx`, `liab` ("only applicable to MARGIN"), `liabCcy`, `interest`, `cTime`, `uTime`.
- **Use for E1:** with spot-only holdings this should return an empty list. Any row means margin or derivatives exposure.

### 5.3 Account configuration: GET /api/v5/account/config
([#trading-account-rest-api-get-account-configuration](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-account-configuration))

- **Params:** none.
- **Fields relevant to "no margin, no lending":**
  - `acctLv`: "1: Spot mode / 2: Futures mode / 3: Multi-currency margin / 4: Portfolio margin".
  - `enableSpotBorrow`: "Whether borrow is allowed or not in Spot mode" (true/false).
  - `autoLoan`: "Whether to borrow coins automatically".
  - `spotBorrowAutoRepay`.
  - `mgnIsoMode` and `ctIsoMode` (isolated margin settings).
  - `opAuth`: "Whether the optional trading was activated" (options).
- **Key and identity fields:**
  - `perm`, `ip`, `label` (see sections 1 and 3).
  - `kycLv`: "0: No verification … 3: level 3 completed".
  - `uid` and `mainUid` (whether this is the main account or a sub-account).
  - `type` (0 is the main account).
- **Answer to the brief:**
  - Yes, this endpoint can show whether margin or borrowing is possible.
  - A spot-only, no-borrow account should read `acctLv == "1"` and `enableSpotBorrow == false`. `autoLoan` should be false.
  - The docs do not say whether `autoLoan` applies in Spot mode or only in the margin modes.
  - Spot mode can still borrow when `enableSpotBorrow` is true. The docs use the phrase "Spot mode (enabled borrow)" in several places.
- **Changing the account mode:**
  - Done with `POST /api/v5/account/set-account-level`, which is a write action and so needs a Trade key.
  - Overview: "You need to set on the Web/App for the first set of every account mode." ([#overview-account-mode](https://www.okx.com/docs-v5/en/#overview-account-mode))

### 5.4 Account-level eligibility: GET /api/v5/account/instruments
([#trading-account-rest-api-get-instruments](https://www.okx.com/docs-v5/en/#trading-account-rest-api-get-instruments))

- "Retrieve available instruments info of current account."
- **Params:**
  - `instType` (required): SPOT, MARGIN, SWAP, FUTURES, OPTION or EVENTS.
  - `instFamily` (conditional).
  - `instId` (optional).
- **Fields:** `instId`, `baseCcy`, `quoteCcy`, `state` (live, suspend, …), `minSz`, `lotSz`, `tickSz`, `maxMktAmt`, `lever`, and so on.
- **Use for eligibility:** this is the closest thing OKX documents to a "product eligibility answer". Calling it per `instType` shows what the account may trade.
- What a Korea-resident account gets back for SWAP, FUTURES or MARGIN (an empty list or an error) is **not documented**.

### 5.5 Open orders: GET /api/v5/trade/orders-pending
([#order-book-trading-trade-get-order-list](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-list))

- "Retrieve all incomplete orders under the current account."
- **Params:** all optional.
  - `instType`, `instFamily`, `instId`, `ordType`, `state` (live, partially_filled).
  - `after` and `before` (ordId cursors).
  - `limit`: max 100, default 100.
- **Fields:** `ordId`, `clOrdId`, `instId`, `side`, `ordType`, `px`, `sz`, `accFillSz`, `avgPx`, `state`, `fee`, `feeCcy`, `cTime`, `uTime`.
  - `tdMode` ("Trade mode"). The value `cash` means non-margin spot; `cross` and `isolated` are margin. Use it to check that no order uses margin.
- This endpoint lists order-book orders only. Algo orders are a separate list: `GET /api/v5/trade/orders-algo-pending` (`#order-book-trading-algo-trading-get-algo-order-list`).

### 5.6 Order history: GET /api/v5/trade/orders-history (7 d) and /orders-history-archive (3 months)
([#order-book-trading-trade-get-order-history-last-7-days](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-history-last-7-days), [#order-book-trading-trade-get-order-history-last-3-months](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-order-history-last-3-months))

- **Params:**
  - `instType` is **required** ("yes").
  - Optional: `instId`, `ordType`, `state` (canceled, filled, mmp_canceled).
  - Cursors: `after` and `before`. Time filters on cTime: `begin` and `end` (ms).
  - `limit` up to 100.
- **Caveat:** "The incomplete orders that have been canceled are only reserved for 2 hours."
- **Fields:** the same order fields as 5.5.

### 5.7 Fills: GET /api/v5/trade/fills (3 d) and /fills-history (3 months)
([#order-book-trading-trade-get-transaction-details-last-3-days](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-transaction-details-last-3-days), [#order-book-trading-trade-get-transaction-details-last-3-months](https://www.okx.com/docs-v5/en/#order-book-trading-trade-get-transaction-details-last-3-months))

- **Params:**
  - `instType` is optional for `/fills` and **required** for `/fills-history`.
  - Optional: `instId`, `ordId`, `subType`.
  - Cursors: `after` and `before` are **billId** cursors. `begin` and `end` filter on ts.
  - `limit` up to 100.
- **Fields:** `tradeId`, `ordId`, `clOrdId`, `billId`, `instId`, `side`, `fillPx`, `fillSz`, `execType` (T/M), `fee` (negative means a fee was charged), `feeCcy`, `feeRate` (SPOT/MARGIN only), `ts`, `fillTime`.
- Longer ledger: `GET /api/v5/account/bills` covers 7 d and `/bills-archive` covers 3 months. Fields include `balChg`, `bal`, `type`, `subType`, `mgnMode` (`cash` for non-margin), `interest`. Bills also record transfers and interest.

### 5.8 Funding account balance: GET /api/v5/asset/balances
([#funding-account-rest-api-get-balance](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-balance))

- **Params:** `ccy` (optional, up to 20).
- **Fields:** `ccy`, `bal`, `frozenBal`, `availBal`.
- The funding account is separate from the trading account. E1 must sum both.
- `GET /api/v5/asset/asset-valuation` gives totals for each account: `funding`, `trading`, `earn`, `totalBal`. Its `ccy` parameter accepts **KRW** as the valuation unit.

### 5.9 Lending check (Simple Earn): GET /api/v5/finance/savings/balance
([#financial-product-simple-earn-flexible-get-saving-balance](https://www.okx.com/docs-v5/en/#financial-product-simple-earn-flexible-get-saving-balance))

- **Fields:** `ccy`, `amt`, `earnings`, `rate` ("Minimum annual lending rate"), `loanAmt` ("Lending amount"), `pendingAmt`.
- **Use for E1:** this is the read-only way to confirm that no assets are lent out. Use it together with `autoLendStatus` from 5.1.

### 5.10 Currencies, chains and withdrawal minimums: GET /api/v5/asset/currencies
([#funding-account-rest-api-get-currencies](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-currencies))

- "Retrieve a list of all currencies available which are related to the current account's KYC entity". This makes it an account-specific eligibility signal.
- **Params:** `ccy` (optional).
- **Fields:**
  - `chain` ("Chain name, e.g. USDT-ERC20, USDT-TRC20")
  - `canDep`, `canWd`, `canInternal`
  - `minDep`, `minWd` ("minimum on-chain withdrawal amount"), `maxWd`, `wdTickSz`
  - `fee` ("The fixed withdrawal fee"). `minFee`/`maxFee` are deprecated.
  - `wdQuota` and `usedWdQuota` (24-hour withdrawal limit and amount used, in USD)
  - `needTag`, `mainNet`, `ctAddr`, `minDepArrivalConfirm`, `minWdUnlockConfirm`, `depQuotaFixed`

### 5.11 Deposit address: GET /api/v5/asset/deposit-address
([#funding-account-rest-api-get-deposit-address](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-deposit-address))

- "Retrieve the deposit addresses of currencies, including previously-used addresses."
- **Params:** `ccy` (**required**).
- **Fields:**
  - `addr`, `tag`, `memo`, `pmtId`, `addrEx`, `ccy`
  - `chain` (for example USDT-TRC20)
  - `to` ("6: Funding account 18: Trading account")
  - `selected`, `ctAddr`, `verifiedName`

### 5.12 Deposit history: GET /api/v5/asset/deposit-history
([#funding-account-rest-api-get-deposit-history](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-deposit-history))

- **Params:** all optional.
  - `ccy`, `depId`, `fromWdId`, `txId`.
  - `type`: 3 is internal transfer, 4 is on-chain.
  - `state`: 0 waiting, 1 credited, 2 successful, 8 pending, and others.
  - `after` and `before` are **ts** cursors in ms.
  - `limit` up to 100. "The 100 most recent records are returned by default."
- **Fields:** `ccy`, `chain`, `amt`, `from`, `to`, `txId`, `ts`, `state`, `depId`, `actualDepBlkConfirm`.

### 5.13 Withdrawal history: GET /api/v5/asset/withdrawal-history
([#funding-account-rest-api-get-withdrawal-history](https://www.okx.com/docs-v5/en/#funding-account-rest-api-get-withdrawal-history))

- **Params:** all optional.
  - `ccy`, `wdId`, `clientId`, `txId`, `type` (3 or 4), `state`.
  - `after` and `before` (ts cursors), `limit` up to 100.
- **Fields:** `ccy`, `chain`, `amt`, `ts`, `to` ("Receiving address"), `toAddrType`, `tag`, `memo`, `txId`, `fee`, `feeCcy`, `state`, `wdId`, `nonTradableAsset`, `note`.
- Per-transaction status: `GET /api/v5/asset/deposit-withdraw-status` (1 request per 2 s). Pass `wdId`, or pass `txId` with `ccy`, `to` and `chain`. It returns `estCompleteTime` and `state`.

### 5.14 Withdrawal address book / whitelist: **no list endpoint documented**

- The withdrawal endpoint says: "The API can only make withdrawal to verified addresses/account". It adds: "verified addresses can be set by WEB/APP." ([#funding-account-rest-api-withdrawal](https://www.okx.com/docs-v5/en/#funding-account-rest-api-withdrawal))
- The related error codes are 58207 ("Withdrawal address isn't on the verified address list.") and 58203 ("Please add a withdrawal address.").
- A search of the full page for "address book", "whitelist", "verified address" and "allowlist" found no endpoint that reads the list of verified addresses.
- **What E1 can show instead:** past destinations, from the `to` field of withdrawal history.

### 5.15 System status (public): GET /api/v5/system/status
([#status-get-status](https://www.okx.com/docs-v5/en/#status-get-status))

- Returns maintenance events (`state`, `begin`, `end`, `serviceType`).
- `env` says which environment an event affects: "1: Production Trading / 2: Demo Trading".
- Useful for E1 to tell an outage apart from an auth failure.

### 5.16 WebSocket alternatives (read-only push)

- Private channels: account, positions, balance-and-position, orders, plus deposit-info and withdrawal-info on the business URL.
- They need `login` first. Login counts as "using" the key.
- Whether a Read-only key may log in and subscribe is **not documented explicitly**. It is presumably allowed, since these channels only read data.

## 6. Read-only vs trading at the protocol level

- **The same signing scheme, headers, host and base path apply to read and write calls.** There is no separate read-only host, token type or header. Read calls are GETs and writes are mostly POSTs, but the protocol does not enforce read-only behaviour.
- **The only difference is the key's permission set**, enforced on the server:
  - Read covers "view account info"; Trade covers orders, "funding transfer, make settings"; Withdraw covers withdrawals.
  - A missing permission produces 50120 ("doesn't have permission to use this function"). The docs do not show a per-endpoint mapping.
- **Client-side guards E1 can add:**
  - Startup: check `GET /account/config.perm == "read_only"`, and refuse to start otherwise.
  - Code: allow only GET in the client and keep a path allow-list.
  - Note that `GET /api/v5/account/balance` and `POST /api/v5/trade/order` look the same apart from method and path.
- **IP binding is optional for a Read-only key.** The 14-day inactivity expiry covers only keys with trade or withdraw permission and no IP. So a Read-only key without IP stays valid. That is convenient, but a leaked key is then usable from anywhere, though only to read.

## 7. Sandbox / demo environment

([#overview-demo-trading-services](https://www.okx.com/docs-v5/en/#overview-demo-trading-services))

- **Demo REST base URL:** `https://openapi.okx.com`, the same host as production. Demo WebSocket hosts are `wss://wspap.okx.com/ws/v5/{public,private,business}`.
- **Header:** "`x-simulated-trading: 1` needs to be added to the header of the Demo Trading request."
- **Demo keys:**
  - Demo keys are separate. They are created via "Trade —> Demo Trading —> Personal Center —> Demo Trading API".
  - Error 50101 is "APIKey does not match current environment." That is what happens when a key is used against the wrong environment (demo vs live).
  - "The API key of demo trading will not expire".
- **Limits:**
  - "some functions are not supported, such as withdraw,deposit,purchase/redemption".
  - Error 50038 is "This feature is unavailable in demo trading". So deposit-address and deposit or withdrawal history may not work on demo. Exactly which endpoints fail is **not documented**.
- **Official Python SDK** (linked from the docs as "Python SDK"): the samples use `flag = "1" # Production trading:0 , demo trading:1`.
- **WebSocket port 8443** (changelog "Upcoming Changes", updated 2026-10-16): public-internet connections on `:8443` stop on 2026-10-31. Use URLs without the port.

## 8. Error codes for auth and rate limits

([#error-code-rest-api-public](https://www.okx.com/docs-v5/en/#error-code-rest-api-public))

| Code | HTTP | Message (abridged) |
|---|---|---|
| 50011 | 200 / 429 | Rate limit reached / Too Many Requests |
| 50013 | 429 | Systems are busy. Please try again later. |
| 50030 | 200 | You don't have permission to use this API endpoint |
| 50035 | 403 | This endpoint requires that APIKey must be bound to IP |
| 50038 | 200 | This feature is unavailable in demo trading |
| 50051 | 200 | Due to compliance restrictions in your country or region… |
| 50100 | 400 | API frozen, please contact customer service. |
| 50101 | 401 | APIKey does not match current environment. |
| 50102 | 401 | Timestamp request expired. |
| 50103 / 50104 / 50106 / 50107 | 401 | Header OK-ACCESS-KEY / PASSPHRASE / SIGN / TIMESTAMP cannot be empty |
| 50105 | 401 | Request header "OK-ACCESS-PASSPHRASE" incorrect. |
| 50110 | 401 | Your IP … is not included in your API key's IP whitelist. |
| 50111 | 401 | Invalid OK-ACCESS-KEY. |
| 50112 | 401 | Invalid OK-ACCESS-TIMESTAMP. |
| 50113 | 401 | Invalid signature. |
| 50114 | 401 | Invalid authorization. |
| 50119 | 200 | API key doesn't exist |
| 50120 | 200 | This API key doesn't have permission to use this function |
| 50121 | 200 | You can't access our services through the IP address (…) |
| 51024 | 200 | Several variants, e.g. "trading is not available in your verified country" |
| 60009 (WS) | – | Login failed. |

- Many business errors return **HTTP 200** with a non-zero `code`. A client must check `code`, not just the HTTP status.
- "code and msg represent the request result … when the return data has code". Batch endpoints use `sCode`/`sMsg` instead. ([#overview-general-info](https://www.okx.com/docs-v5/en/#overview-general-info))

## 9. Korea-specific status (as of 2026-10-24)

**Official OKX sources:**

- **The Risk and Compliance Disclosure** (last updated 8 July 2026) lists South Korea among the jurisdictions where OKX "may restrict services". The restriction is "specifically regarding our derivatives-related and P2P services". ([risk-compliance-disclosure, Section 3](https://www.okx.com/help/risk-compliance-disclosure))
  - South Korea is **not** on the full "Restricted Locations" list there. Only North Korea is.
  - So, officially, spot, deposits and withdrawals are not listed as restricted for South Korea, while derivatives and P2P are.
- **The Terms of Service** (last updated 22 October 2026), clause 2.2: "We may not make all of the Services available in all markets". The complete list is deferred to the disclosure above. ([terms-of-service](https://www.okx.com/help/terms-of-service))
- **The API docs** have no Korea-specific text. The compliance hooks relevant to Korea are:
  - `GET /asset/currencies` is scoped to the "current account's KYC entity".
  - `GET /account/instruments` returns the "available instruments info of current account".
  - Error 51024 has a variant "This product isn't available in your country or region…".
  - Error 50051: "Due to compliance restrictions in your country or region, you cannot use this feature."
  - The account-mode precheck can return `compliance_restriction`: "margin trading services are unavailable".
  - What a Korean account actually gets back from these is **not documented**.
- **The API docs say nothing about restricting API access** (as opposed to products) for Korean residents.

**Third-party reports (not OKX, not regulators):**

- **Cryptonomist, 2026-07-28** ([link](https://en.cryptonomist.ch/2026/07/28/south-korea-crypto-app-ban-okx-return/)):
  - The OKX Android app was missing from the Korean Google Play Store from about 24 July and back by 28 July 2026. The reported cause was unregistered-VASP status under Google's own policy.
  - The article says web access was not affected.
- **Blockmedia** ([link](https://www.blockmedia.co.kr/archives/1032177)) reported that Google Play would restrict apps of overseas exchanges not reported to the FIU from 28 January 2026. It said OKX is not on the FIU-registered list. Third party, and written as a forecast.
- **Asiae, 2026-09-23** ([link](https://core.asiae.co.kr/article/2026092214243195647)) reported that KoFIU and the media-communications review commission agreed to block unregistered overseas exchange sites that serve Korean residents. OKX is not named. Third party.
- **SBS Biz** ([link](https://biz.sbs.co.kr/amp/article/20000339576)) reported an earlier block of 27 unregistered VASP sites, including KuCoin and MEXC. OKX was not listed. Third party; the article's date was not confirmed.
- **The Block** ([link](https://www.theblock.co/post/276404/okx-south-korea-probe)) reported a 2024 complaint about OKX operating in Korea without registration. Third party, older background.

**Bottom line for TRADEGEN:**

- OKX is **not a Korean-registered VASP**. Officially, derivatives and P2P may be restricted for Korea.
- A future Korean site block could cut off web and API access with no API-level notice. Treat this as a live venue risk and show it to the owner.
- The legality of using OKX is a question for the project's legal note, not this doc.

## 10. Open questions (verify before relying on them)

1. **Read-only enforcement:** does a Read-only key calling `POST /api/v5/trade/order` get 50120, 50030 or something else? The docs do not map this per endpoint. It could be verified on **demo** with a demo Read-only key, without real money, but only if the owner allows that. No key has been used.
2. **Read-only key on WebSocket:** can it `login` and subscribe to the account, orders and positions channels? Not documented.
3. **Demo coverage:** do `deposit-address`, `deposit-history`, `withdrawal-history` and `asset/currencies` work on demo, or return 50038? Not documented.
4. **Korean account behaviour:** for a Korea-KYC account, what do `GET /account/instruments?instType=SWAP|FUTURES|MARGIN` and `GET /asset/currencies` return: an empty list, error 51024, or error 50051? Not documented.
5. **`autoLoan` in Spot mode:** does it have any effect when `acctLv == 1`, or does only `enableSpotBorrow` matter? The docs do not say. A conservative check requires both to be false.
6. **Which endpoints need IP binding (50035)?** Not documented. Read endpoints are presumably exempt.
7. **No API to list the verified withdrawal-address whitelist.** E1 can only show past destinations from withdrawal history. Confirm there is no hidden or undocumented endpoint (none found in the 2026-10-24 docs).
8. **Regional domain for Korean users:** the docs list special domains only for US/AU (`us.okx.com`) and EU (`eea.okx.com`). The assumption is that a Korean resident is on the global entity and uses `openapi.okx.com` or `www.okx.com`. Not stated for Korea.
9. **The OKX API Agreement** applies ("continued use constitutes acceptance"). Its terms were not reviewed here.

## Verification (skeptic)

An independent pass ran on 2026-10-24. Fresh copies of five official pages were downloaded and searched locally: the API docs page (5.28 MB HTML), the changelog, the ToS, the Risk and Compliance Disclosure, and the help-center API FAQ. No key was created and no request was signed. Every quote is under 15 words. "docs" means https://www.okx.com/docs-v5/en/ plus the anchor given. "FAQ" means https://www.okx.com/help/api-faq (shown as "Updated on Sep 28, 2026").

### Corrections that change E1 (read these first)

1. **WRONG (outdated): "three permissions".** The FAQ now lists three more permissions: Transfer, Loan and Earn. It says "Transfer: Allows the key to transfer funds between your accounts", and also "If your API Key previously had Trade permissions enabled, all three permissions" are switched on automatically. The API docs still list only Read, Trade and Withdraw, and the `perm` values in `account/config` are still documented as `read_only`, `trade` and `withdraw`.
   - **E1 impact:** `perm` may carry values that are not documented. The startup check must be the exact test `perm == "read_only"`, which fails closed on any extra value. It must never be a "contains read_only" test.
   - Whether a Read-only key can carry Transfer is **UNVERIFIED**. The FAQ says Transfer is "Available to all accounts".
2. **Read-only keys are refused for orders: now CONFIRMED (FAQ).** The FAQ says such a key "can retrieve account data but cannot place orders."
   - **The error code is UNVERIFIED, and probably not 50120.** The FAQ links missing Trade permission to **50123**, whose docs text is "This API Key does not have trading permission for the Crypto." (#error-code-rest-api-public). The FAQ gives this in a demo-trading context.
   - E1 should treat 50030, 50120 and 50123 all as permission refusals.
   - Supporting evidence that OKX assigns a permission to each endpoint, from the changelog for 2023-07-05: "Changed the request permission of Position builder from "Trade" to "Read"".
3. **UNVERIFIED (sources conflict): "A Read-only key without an IP is not covered by the 14-day rule".**
   - The docs sentence supports the claim.
   - The FAQ says "Only read-only API keys bound to an IP or specific permissions will not expire." That can be read as saying a Read-only key also needs an IP to avoid expiry.
   - The FAQ also says unbound trade or withdraw keys are "automatically deleted", not merely expired.
   - **Safer choice:** bind an IP to the E1 key anyway.
4. **Partly WRONG: "the docs do not say whether `autoLoan` applies in Spot mode"** (open question 5). The "Set auto loan" endpoint is "Only applicable to Multi-currency margin and Portfolio margin" (#trading-account-rest-api-set-auto-loan). It also says "The default is true".
   - **E1 impact:** in Spot mode, `enableSpotBorrow` is the setting that matters. Still require both to be false.
5. **Overclaim: Simple Earn is "the read-only way to confirm that no assets are lent out", and `account/config` shows "no borrowing".** The docs have other ways to lend, lock or borrow assets:
   - Flexible Loan, which is borrowing against collateral: `GET /api/v5/finance/flexible-loan/loan-info`. The docs call it a loan "without selling off their crypto".
   - On-chain earn: `/finance/staking-defi/orders-active`.
   - ETH and SOL staking: `/finance/staking-defi/{eth,sol}/balance`.
   - Dual investment: `/finance/sfp/dcd/order-status`.
   - OKUSD (`/finance/okusd/account`) and stable rewards (`/finance/stable-rewards/balance`).
   - The `earn` total in `asset/asset-valuation` is the aggregate cross-check. `account/config` does not cover Flexible Loan.
6. **Incomplete: `tdMode` values.** There is also `spot_isolated`, "only applicable to SPOT lead trading". E1 should accept `cash` only and reject every other value. It should not reject only `cross` and `isolated`.
7. **Nuance: "positions should return an empty list".** The docs say a row with zero size can appear: "a position with a position of 0 will be generated" (manual-transfer isolated mode). Treat a row with `pos == "0"` as a separate warning, not as live exposure.
8. **Missing: the `EVENTS` instType is "Event Contracts".** It appears in the positions, instruments and orders endpoints. `account/instruments` also has a `seriesId` parameter, which is required for EVENTS. Because the legal note hard-blocks prediction markets, E1 should flag any EVENTS row.
9. **Correction: `deposit-withdraw-status` with `txId` returns deposit status, not withdrawal status.** The docs say "Hash record of the deposit, use to retrieve deposit status". Withdrawal status needs `wdId`.
10. **Missing: a third regional domain.** The 2026-05-20 changelog entry also lists `tr.okx.com`. The FAQ says error 50119 often means the account's region and the domain don't match.
11. **Nuance (Korea):** the Disclosure's list of partly restricted places is introduced with "including but not limited to". So spot being absent from the list is not a guarantee.

### Claim-by-claim

| # | Claim in these notes | Verdict | Source and quote (under 15 words) |
|---|---|---|---|
| 1.1 | Three secrets per key; a lost passphrase cannot be recovered | CONFIRMED | docs #overview-api-key-creation-generating-an-api-key: "We cannot recover the Passphrase if you have lost it." |
| 1.2 | Read, Trade and Withdraw are the permissions, and they combine | CONFIRMED in the docs, but WRONG as a complete list | docs #overview-api-key-creation-api-key-permissions: "One or more permission can be assigned to any key." The FAQ adds Transfer, Loan and Earn (correction 1). |
| 1.3 | Trade covers orders, funds transfer and settings | CONFIRMED in the docs, superseded for transfer | docs: "Can place and cancel orders, funding transfer, make settings". The FAQ now makes Transfer its own permission. |
| 1.4 | Keys are made in the web UI; there is no REST endpoint for master-account keys | CONFIRMED | docs: "Create an API key on the website before signing any requests." A scan of every `GET /api/v5/users/*` endpoint found key endpoints only under `subaccount/apikey`. |
| 1.5 | Sub-account keys have the `perm` value `read_only` | CONFIRMED | docs #sub-account-rest-api-create-an-api-key-for-a-sub-account: "read_only: Read only" |
| 1.6 | `account/config` returns `perm`, `ip` and `label` | CONFIRMED | docs #trading-account-rest-api-get-account-configuration: "It is an empty string "" if there is no IP bonded." The `perm` description also says "or Access token" (OAuth tokens exist for broker apps), so "no tokens" is true only for self-signed keys. |
| 1.7 | Only 4 endpoints carry a "Permission:" line | CONFIRMED | There are exactly 4: GLP v2 overview, GLP v2 assessment details, GLP v2 performance history, and Flexible Loan e-mode info. |
| 1.8 | 50120 and 50030 are the permission errors | CONFIRMED, but incomplete | docs #error-code-rest-api-public: "This API key doesn't have permission to use this function". 50123 is missing (correction 2). |
| 1.9 | Server-side refusal is only implied | Now CONFIRMED by the FAQ; the error code is UNVERIFIED | FAQ: "can retrieve account data but cannot place orders." |
| 2.1 | The four OK-ACCESS-* headers | CONFIRMED | docs #overview-rest-authentication-making-requests: "All private REST requests must contain the following headers" |
| 2.2 | ISO ms UTC timestamp, 30 s window, error 50102 | CONFIRMED | docs: "differs from server time by more than 30 seconds (error 50102)" |
| 2.3 | Pre-hash, HMAC SHA256, Base64; uppercase method; query string is part of requestPath | CONFIRMED | docs #overview-rest-authentication-signature: "`GET` request parameters are counted as requestpath, not body" |
| 2.4 | No session tokens or refresh; each request is signed | CONFIRMED for API-key auth | The docs describe only per-request signing. See 1.6 for the OAuth caveat. |
| 2.5 | WS login uses seconds, `/users/self/verify` and a 30 s expiry; failure is 60009 | CONFIRMED | docs #overview-websocket-login: "The request will expire 30 seconds after the timestamp." |
| 2.6 | `expTime` applies only to place and amend | CONFIRMED | docs #overview-transaction-timeouts-rest-api covers place and amend (single and batch), plus "Place sub order under signal bot trading". |
| 3.1 | IP binding is recommended, not required | CONFIRMED | docs #overview-api-key-creation-api-key-security: "we strongly recommend clients linked the API key to IP addresses" |
| 3.2 | Up to 20 IPs per key, in IPv4, IPv6 or segment format | CONFIRMED | docs: "Each API key can bind up to 20 IP addresses" |
| 3.3 | 14-day expiry for unbound trade or withdraw keys; demo keys never expire | CONFIRMED | docs: "will expire after 14 days of inactivity." |
| 3.4 | A Read-only key without an IP is exempt | UNVERIFIED (conflict) | See correction 3. |
| 3.5 | Only authenticated calls count as use; on WS, only login counts | CONFIRMED | docs: "only operation of logging in will be considered to have used the API key" |
| 3.6 | Usage records are in the Security Center | CONFIRMED | docs: "get the usage records of the API key ... though Security Center." |
| 3.7 | 50110 (401), 50035 (403), 50121 | CONFIRMED | docs: "This endpoint requires that APIKey must be bound to IP" |
| 3.8 | Which endpoints raise 50035 is not documented | CONFIRMED that it is absent | The changelog does say IP linking is required for sub-account keys with trade or withdraw. That is one likely source of 50035. |
| 4.1 | Private limits are per User ID, public per IP, WS per connection | CONFIRMED | docs #overview-rate-limits: "Private REST rate limits are based on User ID" |
| 4.2 | 50011 appears twice (200 and 429); 50013 is 429 | CONFIRMED | docs #error-code-rest-api-public. Both 50011 rows are present. |
| 4.3 | 50061 is the sub-account order cap of 1000 per 2 s | CONFIRMED | docs #overview-rate-limits-sub-account-rate-limit: "a maximum of 1000 order requests per 2 seconds" |
| 4.4 | All 20 rows of the per-endpoint rate table | CONFIRMED | A script read each endpoint's "Rate Limit:" and "Rate limit rule:" headings. All 20 rows match. `bills-archive` (not in the table) is 5 requests per 2 s. |
| 4.5 | system/status is 1 request per 5 s, with no rule stated | CONFIRMED | docs #status-get-status: "Rate Limit: 1 request per 5 seconds" |
| 4.6 | WS limits: 3 connections per second per IP, 480 requests per hour, 30 connections per channel, 30 s idle timeout | CONFIRMED | docs #overview-websocket-connect: "limited to 480 times per hour." and #overview-websocket-connection-count-limit: "30 WebSocket connections per specific WebSocket channel per sub-account" |
| 5.0a | Production REST host is `openapi.okx.com`; `www.okx.com` is not deprecated | CONFIRMED | docs #overview-production-trading-services: "REST: https://openapi.okx.com". Changelog 2026-05-20: "will continue to work and will not be deprecated" |
| 5.0b | Regional domains are us and eea; nothing for Korea | CONFIRMED, but incomplete | docs: "Using openapi.okx.com will not work for the regions below." `tr.okx.com` is missing (correction 10). |
| 5.0c | All numbers are returned as strings | UNVERIFIED as a general rule | It matches the field tables (typed String), but no sentence in the docs states it. |
| 5.1 | Balance: `ccy` takes up to 20; the field set; `liab`, `twap` and `autoLendStatus`; the two notes | CONFIRMED | docs #trading-account-rest-api-get-balance: "not be returned when cashBal and eq is both 0." Also: "Applicable to Spot mode/Multi-currency margin/Portfolio margin" (`liab`). |
| 5.2 | Positions: parameters and limits; SPOT is not a position type; `liab` is MARGIN only | CONFIRMED | docs #trading-account-rest-api-get-positions: "Liabilities, only applicable to MARGIN." |
| 5.2b | With spot only, the result should be an empty list | Partly WRONG | See correction 7. |
| 5.3 | Config fields `acctLv`, `enableSpotBorrow`, `autoLoan`, `kycLv`, `uid`/`mainUid`, `type` | CONFIRMED | docs: "Whether borrow is allowed or not in Spot mode". `type` 0 is "Main account". |
| 5.3b | `autoLoan` in Spot mode is not documented | Partly WRONG | See correction 4. |
| 5.3c | "Spot mode (enabled borrow)" appears in several places | CONFIRMED (2 occurrences) | docs (borrow and interest sections) |
| 5.3d | Changing mode is `POST set-account-level`; the first switch must be done on Web/App | CONFIRMED | docs #overview-account-mode: "You need to set on the Web/App for the first set" |
| 5.4 | `account/instruments` lists what the account may trade; parameters | CONFIRMED, but incomplete | docs: "Retrieve available instruments info of current account." `seriesId` is missing; `state` also has the values rebase, post_only, preopen and test. |
| 5.4b | What a Korea account gets back | UNVERIFIED | Not in any official source. |
| 5.5 | `orders-pending`: parameters, limit of 100, `tdMode`; algo orders are listed separately | CONFIRMED, but `tdMode` is incomplete | docs: "Retrieve all incomplete orders under the current account." See correction 6. |
| 5.6 | Order history: `instType` is required; canceled orders are kept 2 hours | CONFIRMED | docs: "The incomplete orders that have been canceled are only reserved for 2 hours." |
| 5.7 | Fills: `billId` cursors; fee sign; `feeRate` only for SPOT/MARGIN; `execType` T/M; bills `mgnMode` is `cash` for non-margin | CONFIRMED | docs: "The trading fee deduction is negative". Also: "This field is returned for SPOT and MARGIN only" |
| 5.8 | Funding balance fields; `asset-valuation` accepts KRW and returns funding, trading, earn and totalBal | CONFIRMED | docs #funding-account-rest-api-get-account-asset-valuation lists "USD, CNY, JP, KRW, RUB, EUR". There is also a deprecated `classic` field. |
| 5.9 | Simple Earn balance fields | CONFIRMED | docs: `rate` is "Minimum annual lending rate configured by users" |
| 5.9b | This is "the read-only way" to confirm nothing is lent | Overclaim | See correction 5. |
| 5.10 | `asset/currencies` is scoped to the account's KYC entity; its fields | CONFIRMED | docs: "related to the current account's KYC entity." Also: `fee` is "The fixed withdrawal fee" |
| 5.11 | `deposit-address`: `ccy` is required; `to` is 6 or 18 | CONFIRMED | docs: "6: Funding account 18: Trading account" |
| 5.12 | Deposit history: parameters, ts cursors, 100 by default | CONFIRMED | docs: "The 100 most recent records are returned by default." |
| 5.13 | Withdrawal history fields; `to` is the receiving address | CONFIRMED | docs: "Receiving address" |
| 5.13b | The status endpoint takes `wdId`, or `txId` plus `ccy`, `to` and `chain` | CONFIRMED with a correction | See correction 9. |
| 5.14 | No endpoint lists the verified withdrawal addresses | CONFIRMED | docs #funding-account-rest-api-withdrawal: "verified addresses can be set by WEB/APP." A scan of every `GET /api/v5/asset/*` endpoint found no address list. 58203 and 58207 confirmed. |
| 5.15 | system/status: `env` 1 is production, 2 is demo | CONFIRMED | docs: "1: Production Trading" and "2: Demo Trading" |
| 5.16 | Private WS channels; deposit-info and withdrawal-info are on the business URL | CONFIRMED | docs #funding-account-websocket-deposit-info-channel: "/ws/v5/business (required login)" |
| 5.16b | A Read-only key may log in and subscribe on WS | UNVERIFIED | No official statement found. |
| 6 | Read and write calls use the same host, headers and signing; only the permission differs | CONFIRMED | Same sections as 2.1 to 2.3, and the FAQ statement in 1.9. |
| 7.1 | Demo uses the same REST host, `wspap` for WS, the `x-simulated-trading: 1` header, and separate keys | CONFIRMED | docs #overview-demo-trading-services: "`x-simulated-trading: 1` needs to be added to the header" |
| 7.2 | 50101 is a key used in the wrong environment; demo does not support withdraw or deposit; 50038 | CONFIRMED | docs: "some functions are not supported, such as withdraw,deposit,purchase/redemption" |
| 7.3 | The SDK flag is 0 for production, 1 for demo | CONFIRMED | This is in the docs' own code samples. The "Python SDK" link goes to pypi.org/project/python-okx. |
| 7.4 | Public-internet WS on port 8443 stops on 2026-10-31 | CONFIRMED | changelog #upcoming-changes: "Public internet: October 31, 2026" (last update October 16, 2026) |
| 8 | All 22 error rows: codes, HTTP status and text | CONFIRMED | docs #error-code-rest-api-public. Missing from the table: 50123 (permission) and 50115 (405, "Invalid request method."). |
| 8b | Batch endpoints use `sCode`/`sMsg` | CONFIRMED | docs #overview-general-info: "It is sCode and sMsg that represent the request result" |
| 9.1 | Disclosure (last updated 8 July 2026): South Korea is limited for derivatives and P2P only; North Korea is fully restricted | CONFIRMED, with a nuance | risk-compliance-disclosure: "South Korea (specifically regarding our derivatives-related and P2P services)". See correction 11. |
| 9.2 | ToS (last updated 22 October 2026), clause 2.2 | CONFIRMED | terms-of-service: "We may not make all of the Services available in all markets" |
| 9.3 | `compliance_restriction`, the 51024 country variant, and 50051 | CONFIRMED | docs: "due to compliance restrictions, margin trading services are unavailable" |
| 9.4 | Cryptonomist (2026-07-28): the app was off Korean Google Play from 24 to 28 July; web was unaffected | CONFIRMED (third party) | It is stated in the article. |
| 9.5 | Blockmedia: the Google Play restriction from 28 Jan, written as a forecast; OKX is not FIU-registered | CONFIRMED (third party) | Dated 2026-01-14. OKX is named among the unreported exchanges. |
| 9.6 | Asiae (2026-09-23): KoFIU and the review commission agreed to block | CONFIRMED with a nuance (third party) | The article says "corrective orders", with standards still to be finalized. OKX is not named. |
| 9.7 | SBS Biz and The Block items | UNVERIFIED | Not re-checked in this pass. |

### Status of the open questions after this pass

- **Q1:** partly answered. The refusal itself is confirmed by the FAQ. The exact code (50123 vs 50120 vs 50030) is still unverified.
- **Q5:** partly answered. Set-auto-loan applies only to MCM and PM.
- **Q2, Q3, Q4, Q6, Q8, Q9:** still open.
- **Q7:** confirmed that no list endpoint exists in the 2026-10-24 docs.
- **New questions:**
  - (a) How do the FAQ's Transfer, Loan and Earn permissions show up in `perm`? Can a Read-only key carry Transfer?
  - (b) Does an unbound Read-only key expire? The FAQ and the docs disagree.
