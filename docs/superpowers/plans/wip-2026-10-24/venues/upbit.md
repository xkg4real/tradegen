# Upbit Open API: read-only account inquiry (for E1)

Researched 2026-10-24. This is documentation research only: no key was used and no request was sent to api.upbit.com.
Sources are the official Korean reference at docs.upbit.com/kr (each page carries an `updatedAt` stamp, given as "upd") unless a line is marked **[3rd party]**.
Quotes are short and verbatim (Korean). Field names in backticks are literal schema tokens.
The docs index is at https://docs.upbit.com/llms.txt.

Base: `https://api.upbit.com/v1`. TLS 1.2 or higher. JSON only (https://docs.upbit.com/kr/reference/rest-api-guide, upd 2026-10-06).

---

## 0. Big change since older Upbit docs: "pockets" (포켓)

- An account has one **main pocket** plus user-created **sub pockets**. Each API key is issued **per pocket**, and Exchange rate limits are counted **per pocket**.
  - Source: https://docs.upbit.com/kr/reference/pocket-overview (upd 2026-10-20).
  - Quote: "외부 입출금은 제한됩니다" (sub pockets).
- Pocket count: "최대 5개까지 만들 수 있습니다". The docs do not make clear whether this means 5 sub pockets or 5 pockets in total (same page).
- A sub pocket cannot be renamed or deleted after creation (same page).
- `GET /v1/accounts` returns "포켓이 보유하고 있는 자산 목록과 잔고" (https://docs.upbit.com/kr/reference/get-balance, upd 2026-10-07).
  - The request takes no pocket parameter. I infer, without a doc statement, that the pocket is the one the key was issued from.
- **E1 implication:** if the owner has only a main pocket, a main-pocket key is the only key needed. Sub-pocket balances need a main-pocket key with `포켓관리` (see 4.10).

---

## 1. Authentication and key scopes

### Permission checkboxes (current names)
- Source: https://docs.upbit.com/kr/docs/api-setup (upd 2026-07-07) and pocket-overview (upd 2026-10-20).

| UI name | Machine enum (`permissions`) | Pocket | Read or write |
|---|---|---|---|
| 자산조회 | `view_account` | main + sub | read |
| 주문조회 | `view_orders` | main + sub | read |
| 주문하기 | `make_orders` | main + sub | **write** (orders, cancels, test order) |
| 출금조회 | `view_withdrawals` | main only | read |
| 출금하기 | `withdraw` | main only | **write** |
| 입금조회 | `view_deposits` | main only | read |
| 입금하기 | `deposit` | main only | **write** (KRW deposit, address generation, travel-rule verify) |
| 자산이전 | `transfer` | sub only | **write** |
| 포켓관리 | `manage_pockets` | main only | read **and write** in one scope (lists pockets and also executes transfers) |

- Enum source: https://docs.upbit.com/kr/reference/list-pocket-api-keys (upd 2026-10-07). It lists `view_account`, `view_orders`, `make_orders`, `view_withdrawals`, `withdraw`, `view_deposits`, `deposit`, `transfer`, `manage_pockets`.
- `포켓관리` covers both viewing all pockets' assets and executing transfers (pocket-overview). **Do not grant it to an E1 read-only key.** That leaves sub-pocket balances out of E1 unless the owner accepts this risk.
- At least one permission is mandatory: "최소 하나 이상의 기능을 선택한 후" (https://docs.upbit.com/kr/docs/api-key, upd 2026-07-07).
- Keys are issued on the PC web only, under 마이페이지 > Open API 관리. KYC and 2FA must already be complete (api-key page).
- Max keys: "메인포켓에서 발급가능한 API Key 개수는 최대 10개입니다". Each sub pocket allows 5 (api-key page).
- The secret is shown once: "Secret key는 최초 발급 화면에서만 확인 가능하므로" (api-key page).

### Is an inquiry-only key rejected at the server for order endpoints?
- **Documented as yes.** Every order-write page says "[주문하기] 권한이 설정된 API Key를 사용해야 합니다". Sources:
  - https://docs.upbit.com/kr/reference/new-order (upd 2026-10-07)
  - https://docs.upbit.com/kr/reference/cancel-order
  - https://docs.upbit.com/kr/reference/batch-cancel-orders
- The error is `out_of_scope`: "요청에 필요한 API Key 권한이 없습니다." (rest-api-guide).
- HTTP status varies: "`401 Unauthorized` 또는 `403 Forbidden`으로 다를 수 있습니다" (rest-api-guide). E1 must match on `error.name`, not on the status.
- api-setup says the response is 401 (out_of_scope) when a key lacks a required permission (api-setup page).
- Not empirically verified. The first E1 smoke test could confirm it with `POST /v1/orders/test` using a read-only key, which should fail with `out_of_scope`. That needs the owner's go-ahead (see 9).

### Withdrawal safety lock (출금 안심차단)
- Since 2026-07-09, keys that hold `출금하기` get the lock automatically: "출금 권한이 있으면 자동으로 적용됩니다" (https://docs.upbit.com/kr/changelog/withdrawal-safety-lock).
- The lock can only be removed in the mobile app. The API cannot remove it (same notice).
- The error is `open_api_withdraw_locked`: "Open API 출금이 잠금 상태입니다." (rest-api-guide).
- This is irrelevant to E1 because E1 must not hold `출금하기`.

---

## 2. Token and signature rules, and lifetimes

Source: https://docs.upbit.com/kr/reference/auth (upd 2026-09-22).

### JWT claims
- `access_key`: required.
- `nonce`: required, a new UUID each time. Quote: "매 요청마다 새로운 값을 입력해야 합니다."
- `query_hash`: required when there is a query string or a body.
- `query_hash_alg`: defaults to SHA512. Quote: "기본값은 `SHA512`로".

### Signing
- HMAC over header.payload with the Secret Key used raw. Quote: "Secret Key는 Base64 인코딩 되어있지 않습니다."
- Recommended algorithm: "HS512(HMAC with SHA-512) 사용을 권장합니다." Some WebSocket examples on the same page use HS256, so they are inconsistent with this.

### query_hash
- SHA512 of the query string exactly as sent: same order as sent, no re-sorting.
  - Array parameters repeat the key: `states[]=wait&states[]=watch`.
  - Non-array lists are comma-joined: `pairs=KRW-BTC,KRW-ETH`.
- The auth page says to hash *before* URL encoding. The Java examples on the same page URL-encode first. This is a doc inconsistency. Use the Python SDK's behaviour as the reference (open question).
- The rest-api-guide requires URL-encoding of query params on the wire, except for `[]` in names.

### Header and lifetime
- Header: `Authorization: Bearer <jwt>`.
- **Lifetime:** no `exp` claim and no TTL are documented. Each request needs a fresh token because the nonce is single-use: `nonce_used` "이미 사용된 `nonce` 값입니다." (rest-api-guide). The size or length of the nonce-replay window is not documented.

### Duplicate headers
- From 2026-07-31, a duplicated `Content-Type` "400 오류가 반환될 수 있습니다" (https://docs.upbit.com/kr/changelog/prevent-duplicate-request-headers). Send each header once.

### Key expiry
- `GET /v1/api_keys` returns `expire_at` for each key: "계정의 모든 API Key 목록과 각 Key의 만료일자를 조회합니다." (https://docs.upbit.com/kr/reference/list-api-keys, upd 2026-10-07).
- **A fixed validity period (e.g. one year) is not documented** in any official page I found.
- The only hint is an example in list-pocket-api-keys: `created_at` 2026-05-28T15:17:51+09:00 and `expired_at` 2027-05-27T15:17:51+09:00. That is an implied 1-year period (inference from an example, not a rule).
- An expired key returns `expired_access_key` "API Key가 만료되었습니다." (rest-api-guide).
- **E1 should read `expire_at` itself and alert ahead of expiry.**

---

## 3. IP binding

Source: https://docs.upbit.com/kr/docs/api-key (upd 2026-07-07).

- **Mandatory for every key, including inquiry-only keys:** "'IP 주소 등록'창에 하나 이상의 IP를 입력".
- Public IP only: "사설 IP는 외부 접근이 불가능하므로 등록할 수 없습니다".
- IPv4 only: "IPv4형식의 IP 주소만 지원합니다."
- A static IP is recommended over a dynamic one. The allowed list can be changed later with [변경].
- A wrong IP returns `no_authorization_ip` "API Key에 등록되지 않은 IP에서 요청했습니다." (rest-api-guide). The get-balance example message is "This is not a verified IP."
- `GET /v1/pockets/api_keys` returns `allowed_ips` for each key (list-pocket-api-keys).
- **[3rd party]** fnnews, 2026-10-08, reporting Dunamu: a call from an unregistered IP triggers a KakaoTalk alert to the owner. https://www.fnnews.com/news/202610080852170334
- **E1 risk:** a Korean residential connection usually has a dynamic IP. If the IP changes, every call fails closed with `no_authorization_ip` until the owner updates the allowlist on the PC web.

---

## 4. Read-only endpoints (REST)

Common to all of section 4:
- Rate limit group `default`: "초당 최대 30회 호출할 수 있습니다". Counted per pocket.
- Pages are dated upd 2026-10-07 unless noted.
- All money and quantity values are **decimal strings**.

### 4.1 Balances: `GET /v1/accounts` (자산조회)
- Doc: https://docs.upbit.com/kr/reference/get-balance. Quote: "[자산조회] 권한이 설정된 API Key가 필요합니다."
- Params: none.
- Response: array of:
  - `currency`
  - `balance`: orderable amount
  - `locked`: amount locked for orders or withdrawals
  - `avg_buy_price`
  - `avg_buy_price_modified` (bool)
  - `unit_currency`: the unit of `avg_buy_price` (KRW, BTC or USDT)
- Total holding = `balance` + `locked`.

### 4.2 Market eligibility and fees: `GET /v1/orders/chance` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/available-order-information.
- Required param: `market` (e.g. `KRW-BTC`).
- Fees: `bid_fee`, `ask_fee`, `maker_bid_fee`, `maker_ask_fee`.
- `market` object:
  - `id`, `name`
  - `order_sides`
  - `bid_types`, `ask_types` (`order_types` is deprecated: "지원이 종료될 예정입니다")
  - `bid.min_total`, `ask.min_total`
  - `max_total`
  - `state` (only `active` is documented)
- `bid_account` and `ask_account`: same fields as accounts.
- There is no warnings field. Market warnings come from the public `GET /v1/market/all?is_details=true`, which returns `market_event.warning` and `market_event.caution{PRICE_FLUCTUATIONS, TRADING_VOLUME_SOARING, DEPOSIT_AMOUNT_SOARING, GLOBAL_PRICE_DIFFERENCES, CONCENTRATION_OF_SMALL_ACCOUNTS}`. That endpoint is IP-limited at 10/s (https://docs.upbit.com/kr/reference/list-trading-pairs, upd 2026-07-29).
- Errors: 400 `invalid_parameter`, `notfoundmarket`.

### 4.3 Single order with fills: `GET /v1/order` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/get-order.
- Params: `uuid` or `identifier`. Quote: "uuid 또는 identifier 중 하나는 반드시 포함해야 합니다." If both are sent, uuid wins.
- Fields:
  - `uuid`, `market`, `side`, `ord_type`, `price`
  - `state` (`wait`/`watch`/`done`/`cancel`), `created_at`
  - `volume`, `remaining_volume`, `executed_volume`
  - `reserved_fee`, `remaining_fee`, `paid_fee`
  - `locked`, `trades_count`, `time_in_force`, `identifier`
  - `smp_type`, `prevented_volume`, `prevented_locked`
- **Fills:** `trades[]` with `market`, `uuid`, `price`, `volume`, `funds`, `trend`, `created_at`, `side`.
- `trades[]` appears **only on this single-order call**: "체결 목록 (개별 주문 조회 시 반환)" (list-open-orders schema).
- Error: 404 `order_not_found`.
- **There is no account-wide "my trades" REST endpoint** in the index. Fills come from `GET /v1/order` per order, or from WebSocket `myOrder` (section 5).

### 4.4 Open orders: `GET /v1/orders/open` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/list-open-orders (upd 2026-10-07).
- Params:
  - `market`
  - `state` or `states[]` (`wait`, `watch`; default `wait`). Quote: "state와 states[]는 동시에 사용할 수 없습니다."
  - `page` (default 1)
  - `limit` (default 100, max 100)
  - `order_by` (default `desc`)
- Order fields as in 4.3, but with no `trades[]`.
- **DANGER:** `DELETE /v1/orders/open` on the same path is **cancel-all** (주문하기, group `order-cancel-all`) (https://docs.upbit.com/kr/reference/batch-cancel-orders).

### 4.5 Closed orders: `GET /v1/orders/closed` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/list-closed-orders.
- Params:
  - `market`
  - `state` or `states[]` (`done`, `cancel`)
  - `start_time`, `end_time` (ISO 8601 or ms)
  - `limit` (default 100, max 1000)
  - `order_by`
- The window is at most 7 days. With no times given, it is the 7 days before the request.
- How far back history goes overall is not documented.

### 4.6 Orders by id: `GET /v1/orders/uuids` (주문조회)
- Doc: https://docs.upbit.com/kr/reference/list-orders-by-ids (upd 2026-10-07).
- Params: `uuids[]` or `identifiers[]`, max 100 each, not both. Quote: "두 파라미터를 동시에 사용할 수 없습니다." Optional `market`, `order_by`.
- The callout on the same page spells the parameter `identifier[]`. This is a doc typo.
- **DANGER:** `DELETE /v1/orders/uuids` is cancel-by-ids (https://docs.upbit.com/kr/reference/cancel-orders-by-ids).

### 4.7 Deprecated list endpoint: `GET /v1/orders`
- Deprecated since 2024-06. Quote: "정확한 지원종료 예정일은 추후 공지사항을 통해 다시 안내드리겠습니다" (https://docs.upbit.com/kr/v1.5.9/reference/주문-리스트-조회, older versioned docs).
- **Do not use it in E1.**

### 4.8 Withdrawals (출금조회; main pocket only)
- **`GET /v1/withdraws`** (https://docs.upbit.com/kr/reference/list-withdrawals)
  - Params:
    - `currency`, `state`
    - `uuids[]` or `txids[]` (max 100)
    - `limit` (max 100), `page`, `order_by`
    - cursors `from` / `to` (a uuid)
  - States: `WAITING`, `PROCESSING`, `DONE`, `FAILED`, `CANCELLED`, `REJECTED`.
  - Fields:
    - `type`, `uuid`, `currency`, `net_type`, `txid`, `state`
    - `created_at`, `done_at`
    - `amount`, `fee`
    - `transaction_type` (`default` / `internal`), `is_cancelable`
- **`GET /v1/withdraw`** (https://docs.upbit.com/kr/reference/get-withdrawal)
  - Params: `uuid` / `txid` / `currency`.
  - With no id it returns the latest: "uuid와 txid를 모두 입력하지 않는 경우 최신 출금 정보가 반환됩니다."
  - Error: 404 `withdraw_not_found`.
- **`GET /v1/withdraws/chance`** (https://docs.upbit.com/kr/reference/available-withdrawal-information, upd 2026-10-07)
  - Required params: `currency` and `net_type`.
  - `member_level`:
    - `security_level`, `fee_level`
    - `email_verified`, `identity_auth_verified`, `bank_account_verified`, `two_factor_auth_verified`
    - `locked`, `wallet_locked`
  - `currency`:
    - `code`, `withdraw_fee`, `is_coin`
    - `wallet_state`, `wallet_support` (a list: `deposit` and/or `withdraw`)
  - `account`: same fields as accounts.
  - `withdraw_limit`:
    - `minimum`, `fixed`, `fiat_currency`
    - `remaining_daily_fiat`, `withdraw_delayed_fiat`, `can_withdraw`
    - deprecated: `onetime`, `daily`, `remaining_daily`, `remaining_daily_krw`
- **`GET /v1/withdraws/coin_addresses`**: the registered withdrawal **allowlist** (https://docs.upbit.com/kr/reference/list-withdrawal-addresses, upd 2026-10-07)
  - Params: none.
  - Fields:
    - `currency`
    - `net_type` (must be used in the withdrawal), `network_name` (display only)
    - `withdraw_address`, `secondary_address` (tag/memo, nullable)
    - `beneficiary_name`, `beneficiary_company_name`, `beneficiary_type` (`individual`/`corporate`)
    - `exchange_name` (exchange wallet), `wallet_type` (personal wallet, e.g. 메타마스크)
  - Registration happens on the PC web only (마이페이지 > Open API 관리 > 디지털 자산 출금주소 관리). No registration API is documented.
  - Travel-rule address verification with the counterparty exchange happens at registration. If it fails, withdrawals to that address may be restricted.
  - The doc is inconsistent about whether `beneficiary_name` is null for personal wallets.

### 4.9 Deposits (입금조회; main pocket only)
- **`GET /v1/deposits`** (https://docs.upbit.com/kr/reference/list-deposits, upd 2026-10-07)
  - Params: the same set as withdraws.
  - States:
    - `PROCESSING`, `ACCEPTED`, `CANCELLED`, `REJECTED`
    - `TRAVEL_RULE_SUSPECTED`, `REFUNDING`, `REFUNDED`
  - Fields:
    - `type`, `uuid`, `currency`
    - `net_type` (null for KRW), `txid`, `state`
    - `created_at`, `done_at` (KST)
    - `amount`, `fee`, `transaction_type`
- **`GET /v1/deposit`** (https://docs.upbit.com/kr/reference/get-deposit)
  - Params: `uuid` / `txid` / `currency`. With none, it returns the latest.
  - Error: 404 `deposit_not_found`.
- **`GET /v1/deposits/coin_addresses`** (https://docs.upbit.com/kr/reference/list-deposit-addresses)
  - Params: none.
  - Fields: `currency`, `net_type`, `deposit_address`, `secondary_address`.
- **`GET /v1/deposits/coin_address`** (https://docs.upbit.com/kr/reference/get-deposit-address)
  - Required params: `currency` and `net_type`.
  - `deposit_address` may be null right after generation: "deposit_address 필드가 null로 반환될 수 있습니다."
- **`GET /v1/deposits/chance/coin`** (https://docs.upbit.com/kr/reference/available-deposit-information)
  - Required params: `currency` and `net_type`.
  - Fields:
    - `is_deposit_possible`, `deposit_impossible_reason`
    - `minimum_deposit_amount`, `minimum_deposit_confirmations`, `decimal_precision`
  - Not real time: "서비스 상태를 실시간으로 반영하지 않으며".
- **DANGER:** `POST /v1/deposits/generate_coin_address` is a write call under 입금하기 (https://docs.upbit.com/kr/reference/create-deposit-address). E1 must never call it.

### 4.10 Pockets (포켓관리; main-pocket key only; this scope also allows transfers)
- `GET /v1/pockets`: `uuid`, `name`, `type` (`main` / `user_spot_trading`) (https://docs.upbit.com/kr/reference/list-pockets, upd 2026-10-07).
- `GET /v1/pockets/assets?uuid=`: sub-pocket balances, with the same fields as accounts. Errors: 404 `pocket_not_found` (https://docs.upbit.com/kr/reference/get-sub-pocket-balance).
- `GET /v1/pockets/api_keys` (`uuids[]`, `include_expired`): each key's `access_key`, `permissions`, `allowed_ips`, `created_at`, `expired_at` (https://docs.upbit.com/kr/reference/list-pocket-api-keys).
  - This is the only documented way for a program to read its own key's scopes.
- `GET /v1/pockets/universal_transfers`: transfer history, with a 7-day window (https://docs.upbit.com/kr/reference/list-universal-transfers).

### 4.11 Keys and wallet status (auth, no extra permission)
- **`GET /v1/api_keys`**: "별도 권한은 필요하지 않습니다".
  - Fields: `access_key`, `expire_at` (KST).
  - It does **not** return scopes (https://docs.upbit.com/kr/reference/list-api-keys).
- **`GET /v1/status/wallet`**: "인증이 필요한 API입니다. 별도 권한은 필요하지 않습니다." (https://docs.upbit.com/kr/reference/get-service-status, upd 2026-10-07).
  - Fields:
    - `currency`
    - `wallet_state` (`working`/`withdraw_only`/`deposit_only`/`paused`/`unsupported`)
    - `block_state` (`normal`/`delayed`/`inactive`), `block_height`, `block_updated_at`, `block_elapsed_minutes`
    - `net_type`, `network_name`
  - Not real time: "실시간 상태 조회를 보장하지 않습니다."

### 4.12 Travel rule
- **`GET /v1/travel_rule/vasps`** (입금조회): `vasp_name`, `vasp_uuid`, `depositable`, `withdrawable` (https://docs.upbit.com/kr/reference/list-travelrule-vasps).
- Verification is **not read-only**:
  - `POST /v1/travel_rule/deposit/uuid` takes `deposit_uuid` and `vasp_uuid`. It requires 입금하기, and a deposit can be verified "10분당 최대 1회" (https://docs.upbit.com/kr/reference/verify-travelrule-by-uuid).
  - `POST /v1/travel_rule/deposit/txid` takes `vasp_uuid`, `txid`, `currency`, `net_type`. Same scope and same limit (https://docs.upbit.com/kr/reference/verify-travelrule-by-txid).
  - A successful verification releases a `TRAVEL_RULE_SUSPECTED` deposit (https://docs.upbit.com/kr/reference/travelrule-guide, upd 2026-07-28).
- **E1 can only *see* a `TRAVEL_RULE_SUSPECTED` deposit.** Releasing it is a manual or write step.
- Travel-rule verification for withdrawal addresses happens at address registration on the web (4.8). No API for it is documented.

### 4.13 Withdrawal hold after a KRW deposit
- **Visible through the API only as an amount:** `withdraw_limit.withdraw_delayed_fiat` "출금 지연 제도로 인해 출금이 제한된 금액" (withdraws/chance). The API reports no trigger time or release time.
- Policy, official changelog (https://docs.upbit.com/kr/changelog/안내-24시간-디지털-자산-출금-지연제-도입-안내):
  - Effective 2020-11-28 15:00.
  - Quote: "해당 입금액 가치의 디지털 자산은 24시간 경과 후 출금 가능합니다."
- Upbit support center says the **first** KRW deposit triggers a 72-hour digital-asset withdrawal hold, and later deposits trigger 24 hours each. The page returned HTTP 403 to my fetch, so this comes from a search-result summary only and needs verification: https://support.upbit.com/hc/ko/articles/900005806486

---

## 5. Read-only WebSocket (optional for E1)

Endpoint: `wss://api.upbit.com/websocket/v1/private`, with the JWT in the Authorization header (https://docs.upbit.com/kr/reference/websocket-guide, upd 2026-09-23).

- **`myOrder`** (https://docs.upbit.com/kr/reference/websocket-myorder, upd 2026-10-13)
  - Fills arrive with `state=trade`.
  - Fill fields: `trade_uuid`, `price`, `volume`, `trade_fee`, `is_maker`, `trade_timestamp`.
  - Running totals: `avg_price`, `executed_volume`, `executed_funds`, `paid_fee`.
  - Nothing is sent without activity: "주문 또는 체결이 없으면 데이터가 전송되지 않습니다."
- **`myAsset`** (https://docs.upbit.com/kr/reference/websocket-myasset, upd 2026-09-22)
  - Fields: `assets[{currency, balance, locked}]`, `asset_timestamp`.
  - Pushes only when holdings change.
  - The first push can be delayed by minutes.
- The required permission for either stream is **not documented**.
- The auth error is `INVALID_AUTH`.
- **E1 should poll REST as the source of truth.** WebSocket is at most a hint.

---

## 6. Rate limits

Source: https://docs.upbit.com/kr/reference/rate-limits (upd 2026-10-07).

### Groups

| Group | Limit | Counted per |
|---|---|---|
| Quotation (`market`, `candle`, `trade`, `ticker`, `orderbook`) | 10/s each | IP |
| Exchange `default` (all of section 4) | 30/s | pocket |
| `order` | 12/s (raised from 8/s on 2026-08-21: https://docs.upbit.com/kr/changelog/order-rate-limit-update) | pocket |
| `order-test` | 8/s | pocket |
| `order-cancel-all` | 1 per 2 s | pocket |
| `websocket-connect` | 5/s | IP without auth, pocket with auth |
| `websocket-message` | 5/s and 100/min | connection |

- Quotation or WebSocket requests that carry an `Origin` header are limited to 1 per 10 s.
- The per-minute REST limit no longer applies (order-rate-limit-update notice).

### Remaining-Req header
- Example: `Remaining-Req: group=default; min=1800; sec=29`.
- `min` is deprecated. Use `sec`.

### 429 and 418
- **429**: "API 호출 한도를 초과했습니다." Wait until the next second, then retry.
- **418**: "과도한 요청으로 인해 요청 제한이 적용되었습니다."
  - It is a block per IP, pocket or connection.
  - The response carries the block time.
  - Repeat offences lengthen the block.
- The best-practice page says to stop all calls in the group on a 429 (https://docs.upbit.com/kr/docs/rest-api-best-practice, upd 2026-05-04).

---

## 7. What separates read-only from trading at the protocol level

1. **Permission scope on the key, enforced at the server** (documented). An E1 key should hold only `view_account`, `view_orders`, `view_withdrawals`, `view_deposits`. Order writes need `make_orders` and return `out_of_scope` without it.
2. **HTTP method.** Every E1 call is `GET`. Two pairs share a path with a destructive verb:
   - `GET/DELETE /v1/order`
   - `GET/DELETE /v1/orders/open` (DELETE is cancel-all)
   - `GET /v1/orders/uuids` vs `DELETE` on the same path (cancel-by-ids)

   **The E1 client should hard-code `GET` and refuse any other verb.**
3. `POST` is used only by write endpoints:
   - orders and the test order
   - deposits/krw and generate_coin_address
   - withdraws and withdraws/krw
   - travel_rule verify
   - pocket transfers
4. Rate-limit groups also differ: `default` vs `order*`.
5. Scopes that are not purely read:
   - `포켓관리` mixes read and transfer.
   - Travel-rule verify sits under `입금하기`.

   Keep both off an E1 key.
6. A read-only key **cannot** use `POST /v1/orders/test`, because it needs 주문하기 (https://docs.upbit.com/kr/reference/order-test). So E1 has no dry-run order check.

---

## 8. Sandbox or paper environment

- **None documented.** The llms.txt index has no sandbox page.
- The only test facility is `POST /v1/orders/test`:
  - Quote: "실제 주문을 생성하지 않고 주문 요청 형식과 주문 가능 여부를 검증합니다."
  - It needs `주문하기` and uses the `order-test` group (8/s).
  - It returns 403 `market_offline` for a pair that cannot be traded yet.
  - UUIDs it returns cannot be looked up.
- All read-only calls hit production. With a GET-only client and a view-only key, this is low-risk.

---

## 9. Error codes (auth, permissions, rate limits)

Source: https://docs.upbit.com/kr/reference/rest-api-guide (upd 2026-10-06).

| HTTP | `error.name` | Meaning (quote) |
|---|---|---|
| 401 | `invalid_query_payload` | "JWT 페이로드가 올바르지 않습니다." |
| 401 | `jwt_verification` | "JWT 검증에 실패했습니다." |
| 401 | `expired_access_key` | "API Key가 만료되었습니다." |
| 401 | `nonce_used` | "이미 사용된 `nonce` 값입니다." |
| 401 | `no_authorization_ip` | "API Key에 등록되지 않은 IP에서 요청했습니다." |
| 401 | `no_authorization_token` | No Bearer token |
| 401/403 | `out_of_scope` | "요청에 필요한 API Key 권한이 없습니다." |
| 403 | `open_api_withdraw_locked` | "Open API 출금이 잠금 상태입니다." |
| 404 | `pocket_not_found`, `currency_not_found`, `order_not_found`, `withdraw_not_found`, `deposit_not_found` | Not found |
| 418 | (no name) | Temporary block |
| 429 | (no name) | Rate limit exceeded |
| WS | `INVALID_AUTH`, `TOO_MANY_REQUEST` | WebSocket |

- Error body: `{"error":{"name","message"}}`.
- In the Exchange API `name` is a string. In the Quotation API it is an integer.
- `invalid_access_key` (from older client libraries) is **not** in the current guide.

---

## 10. Open questions

1. Is a one-year key lifetime official policy? It is not documented. The only evidence is an example in list-pocket-api-keys. E1 should read `GET /v1/api_keys` `expire_at`.
2. Does `GET /v1/accounts` on a main-pocket key include sub-pocket assets? The docs only say it returns "포켓이 보유하고 있는 자산".
3. Does the query_hash use URL-encoded or unencoded values? The auth page says "before encoding" and its Java examples encode first. Check against the official Python SDK at https://github.com/upbit-official.
4. Is the HTTP status of `out_of_scope` on order endpoints 401 or 403? Both are documented. Match on `error.name`.
5. Which permissions do WebSocket `myOrder` and `myAsset` need? Not documented.
6. The withdrawal-delay rule (72 h after the first KRW deposit, 24 h after each later one) comes from the support center, which my fetch could not open. The API shows only `withdraw_delayed_fiat` and gives no release time.
7. How far back do `/v1/orders/closed` and `/v1/deposits` / `/v1/withdraws` history go? Not documented beyond the 7-day window per request and the 100-per-page limit.
8. "최대 5개": is the cap 5 sub pockets or 5 pockets in total?
9. How long is the nonce-replay window, and is there a clock-skew rule? Not documented. Since there is no `exp` claim, clock skew probably does not matter, but this is not confirmed.
10. Dynamic residential IP: the docs give no fallback. The owner must re-register the IP on the PC web.
11. Which IP and machine will hold the read-only key? This is an owner decision, and per the hard rules the agent never enters keys.

---

## Verification (skeptic)

Re-checked 2026-10-24 against docs.upbit.com/kr (WebFetch of each page, no API call). Items follow the note's own numerical order (section 0 to 10). Quotes are verbatim and under 15 words. Default is UNVERIFIED when no official sentence was found.

Tally: 4 WRONG (V18, V89, V91, V97), 7 UNVERIFIED (V28, V31, V41, V50, V74, V75, V99), 1 partly UNVERIFIED (V90), the rest CONFIRMED.

### Header
- V0. Base `https://api.upbit.com/v1`, TLS 1.2+. **CONFIRMED** (rest-api-guide): "TLS 1.2 이상 버전만 지원합니다"

### Section 0. Pockets
- V1. Sub pockets: external deposits and withdrawals restricted. **CONFIRMED.** https://docs.upbit.com/kr/reference/pocket-overview: "외부 입출금은 제한됩니다"
- V2. Exchange rate limits are counted per pocket. **CONFIRMED.** pocket-overview: "Rate Limit은 포켓(Pocket) 단위로 적용됩니다"
- V3. Keys are issued per pocket. **CONFIRMED.** https://docs.upbit.com/kr/docs/api-key gives separate caps per pocket, and pocket-overview links "포켓 별 API Key 발급 받으러 가기".
- V4. "최대 5개" is ambiguous. **CONFIRMED as ambiguous.** Full sentence: "메인포켓은 1개, 서브포켓은 필요에 따라 직접 추가할 수 있으며 최대 5개까지 만들 수 있습니다." The most natural reading is 5 sub pockets, but the page does not say so.
- V5. Sub pocket cannot be renamed or deleted. **CONFIRMED.** pocket-overview: "서브포켓 명칭 변경 및 삭제가 불가능하므로"
- V6. `GET /v1/accounts` returns the pocket's assets, with no pocket parameter. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-balance: "포켓이 보유하고 있는 자산 목록과 잔고를 조회합니다." The page lists no parameters. Which pocket is meant is still UNVERIFIED (see V75).

### Section 1. Authentication and key scopes
- V7. The nine UI names and their pocket applicability (자산조회/주문조회/주문하기 main+sub; 입출금 main only; 자산이전 sub; 포켓관리 main). **CONFIRMED.** https://docs.upbit.com/kr/docs/api-setup (upd 2026-07-07) has the table.
- V8. Permissions enum (`view_account` … `manage_pockets`, 9 values). **CONFIRMED.** https://docs.upbit.com/kr/reference/list-pocket-api-keys (upd 2026-10-07) lists all nine.
- V9. 포켓관리 = view all pockets + execute transfers. **CONFIRMED.** pocket-overview: "모든 포켓의 자산 조회, 자산 이전 실행 및 내역 조회"
- V10. At least one permission required. **CONFIRMED.** api-key: "최소 하나 이상의 기능을 선택한 후"
- V11. PC web only, KYC + 2FA first. **CONFIRMED.** api-key: "업비트 API Key 발급은 PC 웹 환경에서만 가능합니다." It also requires 고객 확인 and 2채널 인증(2FA).
- V12. Max 10 keys on main, 5 per sub pocket. **CONFIRMED.** api-key: "서브포켓 당 발급 가능한 API Key 개수는 최대 5개입니다."
- V13. Secret shown once. **CONFIRMED.** api-key: "Secret key는 최초 발급 화면에서만 확인 가능하므로"
- V14. Order writes require 주문하기. **CONFIRMED** on all three pages: https://docs.upbit.com/kr/reference/new-order (`POST /v1/orders`), https://docs.upbit.com/kr/reference/cancel-order (`DELETE /v1/order`) and https://docs.upbit.com/kr/reference/batch-cancel-orders (`DELETE /v1/orders/open`). Each says "[주문하기] 권한이 설정된 API Key를 사용해야 합니다."
- V15. Error `out_of_scope`. **CONFIRMED.** https://docs.upbit.com/kr/reference/rest-api-guide: "요청에 필요한 API Key 권한이 없습니다."
- V16. Status can be 401 or 403. **CONFIRMED.** rest-api-guide: "`401 Unauthorized` 또는 `403 Forbidden`으로 다를 수 있습니다". The guide files it under 403. api-setup lists "401 Unauthorized(out_of_scope)".
- V17. The server refuses read-only keys for orders. **CONFIRMED as documented only.** No official source shows an observed response, so the empirical check is still pending (owner go-ahead).
- V18. Withdrawal safety lock is applied automatically to every key holding 출금하기 since 2026-07-09. **WRONG (overbroad).** https://docs.upbit.com/kr/changelog/withdrawal-safety-lock says it applies to keys **issued** from 2026-07-09 15:00. Older keys keep their current behaviour and can opt in. "출금 권한이 있으면 자동으로 적용됩니다" is still accurate for new keys. No E1 impact.
- V19. The lock cannot be removed through the API. **CONFIRMED.** Same notice: "API를 활용해 출금 안심 차단 해제는 불가능합니다." It is removed in the mobile app under 인증/보안 > Open API 관리.
- V20. Error `open_api_withdraw_locked`. **CONFIRMED.** rest-api-guide: "Open API 출금이 잠금 상태입니다." The changelog itself names no error code.

### Section 2. Token and signature
- V21. Claims `access_key`, `nonce` (fresh each request), `query_hash` (when there is a query or body), `query_hash_alg` default SHA512. **CONFIRMED.** https://docs.upbit.com/kr/reference/auth (upd 2026-09-22): "매 요청마다 새로운 값을 입력해야 합니다."
- V22. Secret not Base64; HS512 recommended. **CONFIRMED.** auth: "Secret Key는 Base64 인코딩 되어있지 않습니다."
- V23. Some WebSocket examples use HS256. **CONFIRMED.** The auth page's Java WebSocket example uses `Algorithm.HMAC256`.
- V24. Hash before URL encoding, and the Java examples encode first. **CONFIRMED, with an addition.** auth: "URL 인코딩되지 않은 쿼리 문자열을 기준으로 Hash 값을 생성해야 합니다." The Python example matches the rule (`unquote(urlencode(params, doseq=True))`). **The Node examples also hash an encoded string**, so it is not only Java. The two forms differ only when values hold reserved characters or spaces. The Python example on the auth page is the safe reference.
- V25. Wire encoding: URL-encode all params except `[]` in names. **CONFIRMED.** rest-api-guide (GET/DELETE query params; brackets of array names left unencoded).
- V26. Header `Authorization: Bearer <jwt>`. **CONFIRMED.** auth.
- V27. No `exp`/TTL documented; nonce single-use. **CONFIRMED (absence).** The auth payload table lists only the 4 claims, and no example sets `exp`. rest-api-guide: "이미 사용된 `nonce` 값입니다."
- V28. Nonce replay window and clock-skew rule. **UNVERIFIED.** Neither is documented (auth, rest-api-guide).
- V29. Duplicate `Content-Type` may cause 400, from 2026-07-31. **CONFIRMED.** https://docs.upbit.com/kr/changelog/prevent-duplicate-request-headers: "400 오류가 반환될 수 있습니다"
- V30. `GET /v1/api_keys` returns `expire_at`, needs no extra permission. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-api-keys: "계정의 모든 API Key 목록과 각 Key의 만료일자를 조회합니다." Note: the schema describes `expire_at` as "해당 Access Key의 Deprecated일시 (KST)". Treat it as the expiry time.
- V31. A fixed 1-year validity. **UNVERIFIED.** No policy sentence was found on api-key, api-setup or auth. The only evidence is the list-pocket-api-keys example (`created_at` 2026-05-28T15:17:51+09:00, `expired_at` 2027-05-27T15:17:51+09:00), which matches the note.
- V32. `expired_access_key`. **CONFIRMED.** rest-api-guide: "API Key가 만료되었습니다."

### Section 3. IP binding
- V33. At least one IP is mandatory for every key. **CONFIRMED.** api-key FAQ: "'IP 주소 등록'창에 하나 이상의 IP를 입력". No exemption exists for inquiry-only keys.
- V34. Public IPv4 only, no private IP. **CONFIRMED.** api-key: "IPv4형식의 IP 주소만 지원합니다."
- V35. Static IP recommended; list editable with [변경]. **CONFIRMED.** api-key: "업비트 API는 유동 IP 환경에서의 이용을 권장하지 않습니다."
- V36. `no_authorization_ip`, and the get-balance example "This is not a verified IP." **CONFIRMED** on rest-api-guide and get-balance.
- V37. `allowed_ips` in `GET /v1/pockets/api_keys`. **CONFIRMED.** list-pocket-api-keys: "API 요청이 허용된 IP 주소 목록"
- V38. KakaoTalk alert on unregistered IP. **CONFIRMED as a third-party report only** (fnnews 2026-10-08): "등록하지 않은 IP에서 API 호출 시도가 발생하면 카카오톡 알림톡". No official doc page found.

### Section 4. Read-only REST endpoints
- V39. `default` group 30/s, per pocket. **CONFIRMED.** https://docs.upbit.com/kr/reference/rate-limits (upd 2026-10-07) and each endpoint page: "초당 최대 30회 호출할 수 있습니다"
- V40. 4.1 `GET /v1/accounts`, 자산조회, fields `currency, balance, locked, avg_buy_price, avg_buy_price_modified, unit_currency`. **CONFIRMED.** get-balance: "[자산조회] 권한이 설정된 API Key가 필요합니다."
- V41. 4.1 "Total = balance + locked". **UNVERIFIED (inference).** It is consistent with the field definitions ("주문 가능 수량 또는 금액", "출금이나 주문 등에 잠겨 있는 잔액"), but no doc sentence states the sum.
- V42. 4.2 `GET /v1/orders/chance`, required `market`, 주문조회, the fee and market fields, `state` enum `active` only, 400 `invalid_parameter`/`notfoundmarket`. **CONFIRMED.** https://docs.upbit.com/kr/reference/available-order-information: "[주문조회] 권한이 설정된 API Key를 사용해야 합니다." `order_types` is marked deprecated ("지원 종료 이후 응답에서 해당 필드가 제거될 예정").
- V43. 4.2 No warnings field; `GET /v1/market/all?is_details=true` gives `market_event.warning` + 5 caution keys, at 10/s per IP. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-trading-pairs (upd 2026-07-29): "초당 최대 10회 호출할 수 있습니다"
- V44. 4.3 `GET /v1/order`, uuid or identifier with uuid winning, fields incl. `smp_type`/`prevented_*`, `trades[]` subfields, 404 `order_not_found`. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-order: "uuid 또는 identifier 중 하나는 반드시 포함해야 합니다."
- V45. 4.3 `trades` only on single-order lookup. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-open-orders schema: "체결 목록 (개별 주문 조회 시 반환)"
- V46. 4.3 No account-wide "my trades" REST endpoint. **CONFIRMED (absence).** The Order section of https://docs.upbit.com/llms.txt lists only order create/test/get/list/cancel pages. The only fills listings are public pair trades and WebSocket MyOrder.
- V47. 4.4 `GET /v1/orders/open`: `state`/`states[]` exclusive, default `wait`, limit 100/100, `order_by` default `desc`. **CONFIRMED.** list-open-orders: "state와 states[]는 동시에 사용할 수 없습니다."
- V48. 4.4 `DELETE /v1/orders/open` = cancel-all, 주문하기, group `order-cancel-all`. **CONFIRMED** (batch-cancel-orders).
- V49. 4.5 `GET /v1/orders/closed`: limit max 1000, 7-day max window, default = previous 7 days. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-closed-orders: "최대 조회 범위는 7일입니다." Also documented: only `start_time` set gives the next 7 days, and only `end_time` set gives the previous 7 days.
- V50. 4.5 Overall history depth. **UNVERIFIED** (not documented).
- V51. 4.6 `GET /v1/orders/uuids`: max 100, not both, and the callout typo `identifier[]`. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-orders-by-ids: "두 파라미터를 동시에 사용할 수 없습니다." Callout: "uuid[] 또는 identifier[]를 반드시 포함해야 합니다". Both `uuid[]` and `identifier[]` are typos there.
- V52. 4.6 `DELETE /v1/orders/uuids` = cancel-by-ids. **CONFIRMED** (https://docs.upbit.com/kr/reference/cancel-orders-by-ids, 주문하기).
- V53. 4.7 `GET /v1/orders` deprecated since 2024-06, no end date. **CONFIRMED.** https://docs.upbit.com/kr/v1.5.9/reference/주문-리스트-조회: header "Deprecated (2024.06~)". Also: "정확한 지원종료 예정일은 추후 공지사항을 통해 다시 안내드리겠습니다".
- V54. 4.8 `GET /v1/withdraws`: params, state enum, fields, `transaction_type` default/internal. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-withdrawals: "uuids와 txids 파라미터는 동시에 사용할 수 없습니다."
- V55. 4.8 Withdrawal and deposit inquiry are main pocket only. **CONFIRMED via api-setup** (입출금 permissions are main pocket only). The endpoint pages themselves do not say so.
- V56. 4.8 `GET /v1/withdraw` returns the latest when there is no id; 404 `withdraw_not_found`. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-withdrawal: "uuid와 txid를 모두 입력하지 않는 경우 최신 출금 정보가 반환됩니다."
- V57. 4.8 `GET /v1/withdraws/chance`: required `currency`+`net_type`, `member_level`/`currency`/`account`/`withdraw_limit` fields, deprecated four. **CONFIRMED** (https://docs.upbit.com/kr/reference/available-withdrawal-information). Small correction: `net_type` is described as required for digital assets.
- V58. 4.8 `GET /v1/withdraws/coin_addresses`: fields, PC-web registration, travel-rule check at registration, `beneficiary_name` inconsistency. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-withdrawal-addresses: "해당 주소를 발급한 상대 거래소로 주소 검증을 요청합니다." On the inconsistency: the field text says null for personal wallets, while the callout and example ("John" on MetaMask) say the member's name.
- V59. 4.9 `GET /v1/deposits` state enum and fields; `net_type` null for KRW. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-deposits: "원화(KRW) 입금의 경우 null로 반환됩니다."
- V60. 4.9 `GET /v1/deposit` returns the latest when there is no id; 404 `deposit_not_found`. **CONFIRMED** (https://docs.upbit.com/kr/reference/get-deposit).
- V61. 4.9 `GET /v1/deposits/coin_addresses` with no params and 4 fields; `GET /v1/deposits/coin_address` with `deposit_address` possibly null. **CONFIRMED** (list-deposit-addresses, get-deposit-address): "응답의 deposit_address 필드가 null로 반환될 수 있습니다."
- V62. 4.9 `GET /v1/deposits/chance/coin`: fields, not real time. **CONFIRMED** (https://docs.upbit.com/kr/reference/available-deposit-information): "서비스 상태를 실시간으로 반영하지 않으며"
- V63. 4.9 `POST /v1/deposits/generate_coin_address` needs 입금하기. **CONFIRMED** (https://docs.upbit.com/kr/reference/create-deposit-address).
- V64. 4.10 `GET /v1/pockets`, main-pocket key only, type `main`/`user_spot_trading`. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-pockets: "메인포켓에서 발급한 API Key만 사용할 수 있으며"
- V65. 4.10 `GET /v1/pockets/assets?uuid=`, 404 `pocket_not_found`. **CONFIRMED, with a doc inconsistency.** The OpenAPI path is `/v1/pockets/assets`, but the flow diagram on https://docs.upbit.com/kr/reference/get-sub-pocket-balance shows `/v1/pockets/asset`. Use the OpenAPI path.
- V66. 4.10 `GET /v1/pockets/api_keys` (`uuids[]`, `include_expired`) needs 포켓관리 on a main-pocket key, and is the only way to read scopes. **CONFIRMED** (list-pocket-api-keys; `GET /v1/api_keys` has no scopes).
- V67. 4.10 `GET /v1/pockets/universal_transfers` has a 7-day window. **CONFIRMED.** https://docs.upbit.com/kr/reference/list-universal-transfers: "전체 기간은 최대 7일을 초과할 수 없습니다." Default limit is 20, max 100.
- V68. 4.11 `GET /v1/status/wallet`: auth needed, no permission, enums, not real time. **CONFIRMED.** https://docs.upbit.com/kr/reference/get-service-status: "인증이 필요한 API입니다. 별도 권한은 필요하지 않습니다."
- V69. 4.12 `GET /v1/travel_rule/vasps` (입금조회) fields. **CONFIRMED** (https://docs.upbit.com/kr/reference/list-travelrule-vasps).
- V70. 4.12 Both verify calls are POST, need 입금하기, and are limited to 1 per 10 min per deposit. **CONFIRMED** (verify-travelrule-by-uuid, verify-travelrule-by-txid): "동일 입금건에 대해서는 10분당 최대 1회 호출할 수 있습니다."
- V71. 4.12 Successful verification releases a `TRAVEL_RULE_SUSPECTED` deposit. **CONFIRMED (paraphrase).** https://docs.upbit.com/kr/reference/travelrule-guide: "입금 반영을 재개할 수 있습니다"
- V72. 4.13 `withdraw_delayed_fiat` is an amount only. **CONFIRMED.** withdraws/chance: "출금 지연 제도로 인해 출금이 제한된 금액"
- V73. 4.13 24 h rule effective 2020-11-28 15:00. **CONFIRMED.** https://docs.upbit.com/kr/changelog/안내-24시간-디지털-자산-출금-지연제-도입-안내: "해당 입금액 가치의 디지털 자산은 24시간 경과 후 출금 가능합니다."
- V74. 4.13 72 h hold after the **first** KRW deposit. **UNVERIFIED.** The support page https://support.upbit.com/hc/ko/articles/900005806486 again returned 403. The official changelog mentions only 24 h. Only third-party blogs mention 72 h, and they disagree with each other.
- V75. Section 0 inference that `GET /v1/accounts` returns the key's own pocket. **UNVERIFIED.** pocket-overview says 자산조회 covers "해당 포켓의 보유자산 및 잔고 조회", which supports the inference but does not name the endpoint.

### Section 5. WebSocket
- V76. Endpoint `wss://api.upbit.com/websocket/v1/private` with JWT in the Authorization header. **CONFIRMED.** https://docs.upbit.com/kr/reference/websocket-guide (upd 2026-09-23).
- V77. `myOrder`: `state=trade`, fill fields, running totals, silent with no activity. **CONFIRMED.** https://docs.upbit.com/kr/reference/websocket-myorder: "주문 또는 체결이 없으면 데이터가 전송되지 않습니다." It also has a `prevented` state that the note omits.
- V78. `myAsset`: push on change only, first push delayed by minutes. **CONFIRMED.** https://docs.upbit.com/kr/reference/websocket-myasset: "초기 수분 동안 데이터 수신이 지연될 수 있습니다"
- V79. Required permission for the private streams not documented. **CONFIRMED (absence)** on all three pages.
- V80. Auth error `INVALID_AUTH`. **CONFIRMED** (websocket-guide).

### Section 6. Rate limits
- V81. Group table (quotation 10/s per IP; default 30, order 12, order-test 8, cancel-all 1 per 2 s per pocket; ws-connect 5/s IP or pocket; ws-message 5/s + 100/min per connection). **CONFIRMED** (rate-limits): "분당 최대 100회"
- V82. order 8 to 12/s from 2026-08-21, and per-minute REST limit gone. **CONFIRMED.** https://docs.upbit.com/kr/changelog/order-rate-limit-update: "분 단위 요청 제한은 더 이상 적용되지 않으며". The precise time is 21:00.
- V83. Origin header gives 1 per 10 s. **CONFIRMED** (rate-limits): "10초당 1회만 허용됩니다"
- V84. `Remaining-Req` example; `min` deprecated. **CONFIRMED** (rate-limits).
- V85. 429 and 418 messages. **CONFIRMED** (rest-api-guide): "API 호출 한도를 초과했습니다." and "과도한 요청으로 인해 요청 제한이 적용되었습니다."
- V86. 418 is per IP/pocket/connection, the response carries the block time, and repeat offences lengthen the block. **CONFIRMED on rate-limits, not on rest-api-guide**: "429 누적으로 일시 차단 (동일 IP·포켓·커넥션 단위)".
- V87. Stop the group's calls on 429. **CONFIRMED.** https://docs.upbit.com/kr/docs/rest-api-best-practice: "즉시 해당 그룹에 속한 API 호출을 중단하고"

### Section 7. Read-only vs trading
- V88. 7.1 Scope enforced at the server. **CONFIRMED as documented** (see V14 to V17). Not observed.
- V89. 7.2 "**Two** pairs share a path with a destructive verb." **WRONG (count).** The note then lists three, and all three are real: `GET`/`DELETE /v1/order` (cancel-order), `GET`/`DELETE /v1/orders/open` (batch-cancel-orders) and `GET`/`DELETE /v1/orders/uuids` (cancel-orders-by-ids). The GET-only rule stands.
- V90. 7.3 POST is used only by writes. **Partly CONFIRMED:** `POST /v1/orders`, `/v1/orders/test`, `/v1/deposits/generate_coin_address` and `/v1/travel_rule/deposit/{uuid,txid}` were checked. **UNVERIFIED:** the exact methods and paths for deposits/krw, withdraws, withdraws/krw and pocket transfers were not re-fetched.
- V91. 7.4 "Rate-limit groups also differ: `default` vs `order*`." **WRONG as a read/write separator.** Single and by-id cancels are trading writes but sit in **`default`**. cancel-order and cancel-orders-by-ids: "[default 그룹] 내에서 요청 가능 횟수를 공유합니다". Only new order, test order and cancel-all are in `order*`. Do not use the group name to classify a call as read-only.
- V92. 7.6 Read-only key cannot use `POST /v1/orders/test`. **CONFIRMED.** https://docs.upbit.com/kr/reference/order-test: "[주문하기] 권한이 설정된 API Key를 사용해야 합니다."

### Section 8. Sandbox
- V93. No sandbox documented. **CONFIRMED (absence)** in llms.txt.
- V94. `/v1/orders/test`: no real order, 8/s, 403 `market_offline`, returned UUID not usable. **CONFIRMED** (order-test): "실제 주문을 생성하지 않고 주문 요청 형식과 주문 가능 여부를 검증합니다." Also: "주문 조회나 취소 요청에 사용할 수 없습니다."

### Section 9. Error codes
- V95. 401 rows: `invalid_query_payload`, `jwt_verification`, `expired_access_key`, `nonce_used`, `no_authorization_ip`, `no_authorization_token`. **CONFIRMED** (rest-api-guide). The `no_authorization_token` text is "인증 토큰이 요청에 포함되지 않았습니다."
- V96. 404 row cited to rest-api-guide. **CONFIRMED, wrong attribution in part.** rest-api-guide lists only `pocket_not_found` and `currency_not_found`. `order_not_found`, `withdraw_not_found` and `deposit_not_found` come from get-order, get-withdrawal and get-deposit.
- V97. WS row lists `TOO_MANY_REQUEST`. **WRONG per current docs.** It is not in rest-api-guide, websocket-guide or rate-limits. The websocket-guide error list is `INVALID_AUTH`, `WRONG_FORMAT`, `NO_TICKET`, `NO_TYPE`, `NO_CODES`, `INVALID_PARAM`. WS rate-limit errors are deferred to rate-limits (418/429).
- V98. Error body; `name` is a string in Exchange and an integer in Quotation; `invalid_access_key` absent. **CONFIRMED** (rest-api-guide): "문자열 형식의 `name` 값을 반환합니다."

### Section 10. Open questions after verification
- V99. Q3 (query_hash encoding): partly resolved. The doc rule and the Python example both use the **unencoded** string, while the Java and Node examples are the outliers. The official SDK repo https://github.com/upbit-official/upbit-sdk-python exists, but its signing code was not read. Status: UNVERIFIED against the SDK.
- V100. Q1, Q2, Q5, Q6, Q7, Q8, Q9: still open (see V31, V75, V79, V74, V50, V4, V28).
