# KIS (Korea Investment & Securities) Open API: account inquiry (E1) research

Researched 2026-10-24. Documentation only. No key was used, no account or trading endpoint was called, and nothing was submitted. The only things fetched were public documentation: the portal's API-guide JSON, public forum posts, the error-code page, and files on the official GitHub.

## Source legend and versions

- **[OFF-PORTAL]**: the official KIS Developers API guide. The human page is `https://apiportal.koreainvestment.com/apiservice-apiservice?<path>`. The portal's own page script loads the same data as JSON from `https://apiportal.koreainvestment.com/api/apis/public/detail?accessUrl=<path>` (per API) and `.../api/apis/public/api-list/<collectionId>` (per category). "doc mod" is the `lastModifiedDate` the portal returns for that API entry.
- **[OFF-NOTICE] / [OFF-FAQ]**: official portal posts. Notice board: `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000001/post/<id>`. FAQ board: `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/<id>`. The post date is given with each one.
- **[OFF-ERR]**: the official error-code page `https://apiportal.koreainvestment.com/faq-error-code` (content lastModified 2025-04-25).
- **[OFF-GH]**: the official GitHub `https://github.com/koreainvestment/open-trading-api`, main branch at commit cd63caee6a (2026-10-23). `examples_user/kis_auth.py` last changed 2026-03-09. `examples_user/domestic_stock/domestic_stock_functions.py` last changed 2025-08-21.
- **[3P]**: a third party (not official).

Sections are numbered in the order the task listed them. Endpoints in section 5 are sorted by KIS's official API number.

---

## 0. Short answers to the key questions

| Question | Answer | Basis |
|---|---|---|
| Can an app key be inquiry-only? | **No such option is documented.** One token calls every API, including orders. Individuals have no scope parameter. The only inquiry-only case is an account *type*: IRP (29). | FAQ 58eeac3f, FAQ 0b29069f, tokenP doc |
| How is a key tied to an account? | Keys are issued per 8-digit 종합계좌번호. Every product account under that number (01, 03, 08, 22, 29) uses the same key. Each request carries CANO (8) + ACNT_PRDT_CD (2). Keys are bound to the HTS ID and the account password. | FAQ 34b89bae, FAQ 2b6c34cb, Notice bff7ecdb, FAQ f7f6c853 |
| Access token | `POST /oauth2/tokenP`. Valid 24 h. Calling again within 6 h returns the same token; after 6 h a new token is issued. Issuing is limited to 1 call per minute (EGW00133). Each issuance sends a KakaoTalk alert. Whether a new token revokes the old one is **not documented**. Explicit revoke is `POST /oauth2/revokeP`. | tokenP doc, Notices b9136772 and 7e0da1f9 |
| Two programs on one key | They share one per-key REST budget and one WebSocket session (a second session fails with OPSP8996). Within the 6 h window both receive the same token. If both try to issue, they hit the 1/min limit together. What happens to program A's token when B triggers a fresh issue after 6 h is **not documented**. | Notice d0d1a83f, OFF-ERR, [3P] AlgoLab |
| Real-account rate limit | **18 REST calls/s per account (app key)** as of 2026-04-20 (was 20). New registrations get 3/s for their first 3 days. Stock balance (TTTC8434R) also has a 120 TPS cap across all customers (EGW00215). | Notices d0d1a83f and c1113824, inquire-balance doc |
| Do inquiry endpoints live under `/trading/`? | **Yes, all of them.** Domestic and overseas balance, fills, open orders, buying power, asset summary, margin, and pension all sit under `/uapi/domestic-stock/v1/trading/...` or `/uapi/overseas-stock/v1/trading/...`, the same prefix as `order-cash` and `order`. A guard that bans the `/uapi/.../trading/` string bans all of E1. Only product info (`/quotations/`) and WebSocket fill notices are outside it. | OFF-PORTAL lists, OFF-GH |
| Is there a product-eligibility API? | **No account-level eligibility API is documented** for leveraged/inverse ETP pre-education or 기본예탁금, short selling, derivatives account, or ELW. What exists: order-time rejections (APBK1681: overseas leveraged-ETP 기본예탁금; APBK1943: best-execution disclosure) and product-level flags (`sgle_item_lvrg_etp_yn`, `etp_chas_erng_rt_dbnb`, `etf_chas_erng_rt_dbnb`). | Notices 15abe578 and 0778faf1, product-info docs |
| Mock environment | Yes. Separate domain, app key and mock account. TR ids start with V. **Many account inquiries are "모의투자 미지원"** (not supported in mock). | OFF-PORTAL, FAQ 5c706351 |
| WebSocket fill notices | H0STCNI0 (domestic) and H0GSCNI0 (overseas); mock versions H0STCNI9 / H0GSCNI9. Keyed by **HTS ID**, so notices cover every account under that ID. AES256-encrypted. The client only subscribes and unsubscribes. | OFF-PORTAL, Notice d0d1a83f |
| Deposit/withdrawal address lists | Not applicable: this is a broker, not a crypto venue. No transfer or withdrawal API appears in the documented account lists. | OFF-PORTAL lists |

---

## 1. Authentication and key scopes

1. **One token unlocks everything.** "해당 토큰을 활용하여 조회 및 매수/매도 등 모든 API를 호출할 수 있습니다." [OFF-FAQ 58eeac3f, 2026-04-07] `.../000000000002/post/58eeac3f-f5b5-4f22-a48d-ffd668fac8b4`
2. **Individuals have no scope parameter.** The tokenP request body is only `grant_type`, `appkey` and `appsecret`; grant_type is "client_credentials". [OFF-PORTAL tokenP, doc mod 2025-04-28] `https://apiportal.koreainvestment.com/apiservice-apiservice?/oauth2/tokenP`. The error list does include EGW00109 "scope는 필수입니다." and EGW00110 "유효하지 않은 scope 입니다." [OFF-ERR], but the same doc says partner corporations use the "Authorization Code Grant 절차를 준용" (a different flow). **Whether scopes apply to individual keys is not documented.**
3. **Inquiry-only exists only as an account type.** "IRP(29): 주문은 불가하며, 계좌조회/시세조회만 이용 가능합니다." DC accounts (55) cannot use Open API at all. [OFF-FAQ 0b29069f, 2026-03-26] `.../000000000002/post/0b29069f-812b-4a70-94db-63d07d5ad54c`
4. **Key-to-account binding.** "종합계좌번호(8자리) 단위로 Open API 서비스 신청 및 앱 발급이 되므로". Product accounts under the same 8 digits, such as -01 and -22, use the same key. [OFF-FAQ 34b89bae, 2025-08-11] `.../000000000002/post/34b89bae-7d22-45b4-a8cc-2781fbbcd7aa`
   - CANO and ACNT_PRDT_CD: "CANO에 종합계좌번호 8자리, ACNT_PRDT_CD에 계좌상품코드 2자리". The product code is 01 for stocks (domestic and overseas), 03 for domestic futures/options, 08 for overseas futures/options. [OFF-FAQ 2b6c34cb, 2023-05-10] `.../000000000002/post/2b6c34cb-8067-4efa-a0f2-043644c922ab`
   - The official config file also lists 22 (pension savings) and 29 (retirement pension): `my_prod: "01" # 종합계좌`. [OFF-GH kis_devlp.yaml] `https://github.com/koreainvestment/open-trading-api/blob/main/kis_devlp.yaml`
   - Limits: "실전투자계좌의 경우 최대 89개, 모의투자계좌의 경우 최대 2개까지". [OFF-NOTICE 0d5bc017, 2022-10-27] `.../000000000001/post/0d5bc017-eb8b-431a-98da-a2854f17f110`
   - Only your own accounts: "현재 본인계좌 이외에는 매매가 불가능합니다." [OFF-FAQ 4cd60e0e, 2022-08-05]
5. **Key lifetime.** "유효기간은 1년이며 만료 30일 전부터 앱키를 갱신하실 수 있습니다." and "갱신시 APP Key, APP Secret는 새로 발급됩니다." [OFF-NOTICE 0d5bc017]. A renewal first sends a "해지" (cancelled) notice, then a new-registration notice. [OFF-FAQ 544bdacd, 2025-08-11]
6. **Events that invalidate the key.**
   - Changing the account password: "계좌비밀번호를 변경하신 경우는 기존 앱키, 앱시크리트 사용이 불가합니다." [OFF-FAQ f7f6c853, 2023-08-04]
   - Changing the HTS ID: "기존에 발급받은 API Key는 더 이상 사용하실 수 없으며". From 2026-08-17 this is enforced on overseas balance (TTTS3012R) and overseas open orders (TTTS3018R). [OFF-NOTICE bff7ecdb, 2026-08-03] `.../000000000001/post/bff7ecdb-f13c-40d3-a5e6-403a5a9e0a6b`
   - Manual cancellation at any time: "해지 완료 시 발급되었던 APP Key, APP Secret는 사용이 불가능합니다." [OFF-FAQ 6a66821c, 2023-09-06]
7. **The secret goes on every call.** Every REST request header carries `authorization` (Bearer), `appkey` **and** `appsecret`, plus `tr_id` and `custtype` ("P : 개인"). So any process that reads the account must hold the app secret. The doc's own note on the secret field: "(절대 노출되지 않도록 주의해주세요.)" [OFF-PORTAL inquire-balance, doc mod 2026-07-06] `https://apiportal.koreainvestment.com/apiservice-apiservice?/uapi/domestic-stock/v1/trading/inquire-balance`
8. **HTS ID.** It is needed for WebSocket fill notices (`my_htsid`) [OFF-GH README]. The pension docs state API keys are issued only when "HTS ID에 반드시 연결되어있어야만". [OFF-GH domestic_stock_functions.py, pension section]
9. **Terms of use.** "자신의 보안코드(앱키, 시크릿키)가 유출 및 도용되지 않도록 관리해야". Market data may be used for personal investment only. [OFF-FAQ 1f422ddb, 2026-10-06]

## 2. Token and signature rules and lifetimes

1. **Endpoint.** `POST /oauth2/tokenP` with body `{"grant_type":"client_credentials","appkey":...,"appsecret":...}`. The response carries `access_token`, `token_type` "Bearer", `expires_in` (the example shows 86400) and `access_token_token_expired` ("YYYY-MM-DD HH:MM:SS"). [OFF-PORTAL tokenP, doc mod 2025-04-28]
2. **Lifetime and reissue.** "접근토큰(access_token)의 유효기간은 24시간 이며(1일 1회발급 원칙)" and "갱신발급주기는 6시간 입니다.(6시간 이내는 기존 발급키로 응답)" [OFF-PORTAL tokenP]
   - After 6 h: "6시간 이후에 발급 요청시 토큰값 신규생성 및 결과 값 리턴". [OFF-NOTICE 7e0da1f9, 2023-07-10] `.../000000000001/post/7e0da1f9-9540-4530-8ca9-cb1da1cc68ed`
3. **Issue-rate limit (EGW00133).** "1분당 1회 호출가능, 2회 이상 호출시 오류 리턴", effective 2023-10-27 17:00, `msg_cd: EGW00133`. [OFF-NOTICE b9136772, 2023-10-17 "[수정]"] `.../000000000001/post/b9136772-4f5b-4e72-92c5-bf9429b392fd`
   - Confirmed by [OFF-FAQ a046c19e, 2025-08-11]: "1분 내 2회 이상 호출 시 오류가 반환됩니다." and by the [OFF-GH README]: "토큰 재발급 - 1분당 1회 발급됩니다."
   - **Older or conflicting official statements:**
     - FAQ 0ad7f35e (2023-07-18) says "5분당 1회 (2023.10.27일부터 적용)". This predates the "[수정]" (revised) notice, which says the limit was changed to 1 minute after customer feedback.
     - The rate-limit notice d0d1a83f says "접근토큰발급(/oauth2/tokenP)의 경우 1초당 1건".
     - Treat 1/min as binding, because it is the strictest current statement and matches the EGW00133 message text.
4. **Alert on issuance.** "접근토큰발급 사실을 카톡 등을 통하여 안내드리고 있사오니" (b9136772). The official sample says "Token 발급, 유효기간 1일, 6시간 이내 발급시 기존 token값 유지, 발급시 알림톡 무조건 발송". [OFF-GH examples_user/kis_auth.py, line 192] `https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/kis_auth.py`
5. **Does a new token revoke the old one? Not documented.** The docs only say the same token is returned within 6 h. Whether a token issued after the 6 h mark invalidates an earlier token that still has hours left is not stated anywhere official. [3P AlgoLab, 2026-08-09, `https://algolab.co.kr/blog/kis-api-access-token-expiry-refresh-2026`] does not say either; it recommends a single shared token file because "각자 발급을 시도하면 분당 제한에 함께 걸립니다".
6. **Explicit revoke.** `POST /oauth2/revokeP` with body `appkey`, `appsecret`, `token`. Purpose: "부여받은 접큰토큰을 더 이상 활용하지 않을 때 사용합니다." [OFF-PORTAL revokeP, doc mod 2022-04-24]
7. **WebSocket approval key.** `POST /oauth2/Approval` with body `grant_type`, `appkey`, `secretkey`. The doc notes "appsecret와 secretkey는 동일하오니". The key is used once at connect: "접속키는 세션 연결 시 초기 1회만 사용하기 때문에", and the session can then stay up indefinitely. Issuance is limited to 1/s. [OFF-PORTAL Approval, doc mod 2023-06-27; OFF-NOTICE d0d1a83f]
8. **Signature.** Requests are not HMAC-signed; auth is bearer token plus appkey/appsecret headers.
   - The legacy sample had a `/uapi/hashkey` call for POST bodies, but in the current sample the call is commented out: `# if (hashFlag): set_order_hash_key(headers, params)` [OFF-GH kis_auth.py].
   - `/uapi/hashkey` has no entry in the current portal (the portal JSON returned nothing for it). The error list keeps EGW00131 "유효하지 않은 hashkey입니다."
   - Hashkey is for order POSTs only, so it does not matter for E1.
9. **Transport.** TLS 1.2 or higher is mandatory since 2025-12-12: "TLS 1.0, 1.1로 호출 시 서비스 이용이 불가". [OFF-NOTICE 1510666f, 2025-11-25]. The WebSocket is plain `ws://`: "ws 프로토콜만 제공하며, wss(SSL 암호화) 접속은 지원하지 않습니다." [OFF-FAQ efa49825, 2025-08-11]

## 3. IP binding

1. **None for individuals.** "별도의 IP 화이트리스트 운영 없이 전체 허용 정책입니다." [OFF-FAQ 691e2917, 2025-08-11] `.../000000000002/post/691e2917-3eb9-486b-b94c-9630a5c186c6`
2. **No fixed IP needed.** "접속 IP와 무관하게 인증이 이루어지기 때문에 고정 IP가 필요하지 않습니다." [OFF-FAQ c5c4f097, 2025-07-28]. KIS will not whitelist a specific IP on request either. [OFF-FAQ ff32a7fd, 2025-08-11]
3. **Corporate only.** The `ip_addr` header is "[법인 필수] 사용자(회원)의 IP Address" [OFF-PORTAL, every account API], and EGW00303 reads "법인고객에게 허용되지 않은 IP접근입니다." [OFF-ERR]
4. **Abuse blocking.** Clients that reconnect the WebSocket in a loop may be blocked: "고객님의 IP 및 앱키가 일시 차단 될 수". [OFF-NOTICE 4f34b068, 2026-02-24]

## 4. Rate limits

1. **REST (current).** "(실전투자) 1초당 18건 (기존 20건)", "(모의투자) 1초당 1건 (기존 2건)". Limits apply per account: "계좌 단위로 유량 제한". [OFF-NOTICE d0d1a83f, title says "2026.04.20 기준"] `.../000000000001/post/d0d1a83f-6f8d-4437-9700-6d26702fd989`
   - Spacing advice: "동시 호출의 경우, 100ms ~ 150ms 텀을 두고".
   - When some calls fail under load-balancing, the advice is an immediate retry: "즉시 재호출 수행 부탁드립니다".
   - A per-account key is the same thing as a per-app-key limit: "1개의 앱키당" [OFF-FAQ bcfb94ee, 2022-11-13, older figures of 20/2].
2. **New registrations.** "신청 시점으로부터 3일 동안 초당 3건으로 제한". A cancel-and-re-register counts as new: "서비스 해지 후 등록 시에는 신규 등록으로 간주". This applies since 2026-04-03 17:00 and not to mock accounts. [OFF-NOTICE c1113824, 2026-03-20] `.../000000000001/post/c1113824-17c7-47a7-b7b8-8880506a847c`
3. **Stock-balance cap across all customers.** "개인 고객 유량 무관하게 초당 120 TPS로 제한되어 있습니다." It returns "EGW00215 원장에서 허용 가능한 초당 거래건수를 초과하였습니다." and the advice is to retry. [OFF-PORTAL inquire-balance, doc mod 2026-07-06; also OFF-NOTICE 050d6619, 2026-02-09]
4. **Token and approval key.** tokenP: 1/min (section 2.3). Approval key: "초당 1건으로 발급 제한". [OFF-NOTICE d0d1a83f]
5. **WebSocket.** "WEBSOCKET : 1세션" per app key. The subscription limit is "실시간 데이터 합산 41건까지 등록 가능", summed across all products. One PC may open sessions for several keys. [OFF-NOTICE d0d1a83f]
   - Over the limit: OPSP0008 "MAX SUBSCRIBE OVER" [OFF-ERR].
   - A second session on the same key: OPSP8996 "ALREADY IN USE appkey" [OFF-ERR].
   - "한 사용자가 2개의 소켓을 열 수 없습니다." [OFF-FAQ 434b97f1]
6. **Optional higher tier.** Accounts with at least KRW 7.5 bn of monthly Open API volume get 50/s REST and 201 WS subscriptions. Not relevant at this account size. [OFF-NOTICE eb3e2dcb, 2025-11-03]
7. **Stale figures elsewhere.**
   - The official sample still sleeps `_smartSleep = 0.05` (real) and `0.5` (mock), which matches the old 20/s and 2/s. [OFF-GH kis_auth.py lines 146 and 151]
   - The 2022 FAQ 8548106c says "1초당 10건". Superseded.
   - [3P AlgoLab `https://algolab.co.kr/platforms/kis`] quotes 20/s and 2/s. Stale against the official 18/1.
8. **Page sizes per call (official).**
   - Domestic balance: 50 per call (real), 20 (mock).
   - Daily fills: 100 (real), 15 (mock).
   - Cancellable orders: 50.
   - Overseas balance: 100 (real).
   - Overseas fills: 20 (real), 15 (mock).
   - Overseas open orders: 40.
   - Paging uses the `tr_cont` header (response "F or M : 다음 데이터 있음"; next request "N") plus the `CTX_AREA_FK100/NK100` keys (FK200/NK200 for overseas).

## 5. Read-only endpoints

**Headers common to every REST call** [OFF-PORTAL]: `content-type: application/json; charset=utf-8`, `authorization: Bearer <token>`, `appkey`, `appsecret`, `tr_id`, `custtype: P`, optional `tr_cont`. The response body has `rt_cd` ("0 : 성공  0 이외의 값 : 실패"), `msg_cd` and `msg1`. Every endpoint below is `GET` with query parameters. Real host: `https://openapi.koreainvestment.com:9443`. Mock host: `https://openapivts.koreainvestment.com:29443`.

### 5.1 Domestic stock (all under `/uapi/domestic-stock/v1/trading/`)

| Official id | Name | Path | Real TR | Mock TR | doc mod |
|---|---|---|---|---|---|
| v1_국내주식-004 | 주식정정취소가능주문조회 (open / cancellable orders) | `.../trading/inquire-psbl-rvsecncl` | TTTC0084R (old TTTC8036R) | 모의투자 미지원 | 2025-04-30 |
| v1_국내주식-005 | 주식일별주문체결조회 (orders & fills) | `.../trading/inquire-daily-ccld` | ≤3 mo TTTC0081R; >3 mo CTSC9215R | VTTC0081R / VTSC9215R | 2026-06-08 |
| v1_국내주식-006 | 주식잔고조회 (holdings + cash) | `.../trading/inquire-balance` | TTTC8434R | VTTC8434R | 2026-07-06 |
| v1_국내주식-007 | 매수가능조회 (buying power) | `.../trading/inquire-psbl-order` | TTTC8908R | VTTC8908R | 2025-04-30 |
| v1_국내주식-020 | 주식예약주문조회 (reserved orders) | `.../trading/order-resv-ccnl` | CTSC0004R | 미지원 | 2026-02-02 |
| v1_국내주식-032..036 | 퇴직연금 잔고/미체결/매수가능/예수금 (IRP) | `.../trading/pension/...` | TTTC2202R, TTTC2201R / TTTC2210R, TTTC0503R, TTTC0506R, TTTC2208R | 미지원 | 2025-04-30 to 2026-03-20 |
| v1_국내주식-041 | 주식잔고조회_실현손익 | `.../trading/inquire-balance-rlz-pl` | TTTC8494R | 미지원 | 2025-04-30 |
| v1_국내주식-042 | 신용매수가능조회 (credit buying power) | `.../trading/inquire-credit-psamount` | TTTC8909R | 미지원 | 2025-04-30 |
| v1_국내주식-048 | 투자계좌자산현황조회 (asset summary) | `.../trading/inquire-account-balance` | CTRP6548R | 미지원 | 2025-04-30 |
| v1_국내주식-052 | 기간별손익일별합산조회 | `.../trading/inquire-period-profit` | TTTC8708R | 미지원 | 2025-04-30 |
| v1_국내주식-060 | 기간별매매손익현황조회 | `.../trading/inquire-period-trade-profit` | TTTC8715R | 미지원 | 2025-04-30 |
| 국내주식-165 | 매도가능수량조회 (sellable qty) | `.../trading/inquire-psbl-sell` | TTTC8408R | 미지원 | 2025-04-30 |
| 국내주식-191 | 주식통합증거금 현황 (integrated margin) | `.../trading/intgr-margin` | TTTC0869R | 미지원 | 2025-04-30 |
| 국내주식-211 | 기간별계좌권리현황조회 (corporate-action rights) | `.../trading/period-rights` | CTRGA011R | 미지원 | 2025-04-30 |

Source for the whole table: the [OFF-PORTAL] list for category "[국내주식] 주문/계좌" (`.../api/apis/public/api-list/b0a44bfd-dfd5-47f1-9b06-758383e595db`), cross-checked against [OFF-GH] `examples_user/domestic_stock/domestic_stock_functions.py` (for example `api_url = "/uapi/domestic-stock/v1/trading/inquire-balance"`, line 3730).

**Details of the key endpoints:**

- **-006 inquire-balance (TTTC8434R).**
  - Required params: `CANO`, `ACNT_PRDT_CD`, `AFHR_FLPR_YN`, `INQR_DVSN`, `UNPR_DVSN`, `FUND_STTL_ICLD_YN`, `FNCG_AMT_AUTO_RDPT_YN`, `PRCS_DVSN`, plus `OFL_YN` (blank) and `CTX_AREA_FK100/NK100`.
  - Since 2026-09-14, AFHR_FLPR_YN means: N = KRX regular close, X = NXT, Y = KRX+NXT combined. [OFF-NOTICE 26dfe350, 2026-09-09]
  - `INQR_DVSN=02` is now rejected ("INPUT INVALID_CHECK_INQR_DVSN"), so use `01`. [OFF-NOTICE 050d6619, 2026-02-09]
  - output1 (per holding): `pdno`, `prdt_name`, `hldg_qty`, `ord_psbl_qty`, `pchs_avg_pric`, `pchs_amt`, `prpr`, `evlu_amt`, `evlu_pfls_amt`, `evlu_pfls_rt`, `thdt_buyqty`, `thdt_sll_qty`, `loan_dt`, `loan_amt`, `item_mgna_rt_name`.
  - output2 (cash): `dnca_tot_amt` (예수금총금액, "예수금"), `nxdy_excc_amt` ("D+1 예수금"), `prvs_rcdl_excc_amt` ("D+2 예수금"), `tot_evlu_amt` ("유가증권 평가금액 합계금액 + D+2 예수금"), `nass_amt`, `scts_evlu_amt`, `pchs_amt_smtl_amt`, `evlu_pfls_smtl_amt`, `tot_loan_amt`.
  - Caveats:
    - Holdings sold out today still appear at quantity 0 and disappear after D-2.
    - The doc warns it is "조회속도가 느린 API" and recommends the buying-power and sellable-quantity TRs before placing orders.
- **-007 inquire-psbl-order (TTTC8908R).**
  - Params: `CANO`, `ACNT_PRDT_CD`, `PDNO`, `ORD_UNPR`, `ORD_DVSN`, `CMA_EVLU_AMT_ICLD_YN`, `OVRS_ICLD_YN`. Per the doc, if PDNO and ORD_UNPR are blank, only the amount is returned (no quantity).
  - Output: `ord_psbl_cash` ("예수금으로 계산된 주문가능금액"), `ruse_psbl_amt`, `nrcvb_buy_amt`/`nrcvb_buy_qty` (no margin debt), `max_buy_amt`/`max_buy_qty` (with margin debt), `ord_psbl_frcr_amt_wcrc`.
  - Use `ORD_DVSN=01` so the stock's margin rate is applied.
- **-005 inquire-daily-ccld.**
  - Params: `CANO`, `ACNT_PRDT_CD`, `INQR_STRT_DT`, `INQR_END_DT`, `SLL_BUY_DVSN_CD`, `PDNO`, `ORD_GNO_BRNO`, `ODNO`, `CCLD_DVSN` (00 all / 01 filled / 02 unfilled), `INQR_DVSN`, `INQR_DVSN_1`, `INQR_DVSN_3`, `EXCG_ID_DVSN_CD` (KRX/NXT/SOR/ALL; "모의투자는 KRX만 제공"), `CTX_AREA_*`.
  - Old TR ids: "(구)TTTC8001R → (신)TTTC0081R" and CTSC9115R → CTSC9215R. The doc warns "구TR은 사전고지 없이 막힐 수 있으므로". Calls on old ids are still auto-mapped (Notice 7c894616), but do not use them.
  - output1: `ord_dt`, `odno`, `orgn_odno`, `sll_buy_dvsn_cd`, `pdno`, `ord_qty`, `ord_unpr`, `ord_tmd`, `tot_ccld_qty`, `avg_prvs`, `tot_ccld_amt`, `cncl_yn`, `rmn_qty`, `rjct_qty`, `excg_id_dvsn_Cd`.
  - Doc defect: the output2 labels are shifted (`tot_ccld_amt` is labelled 매입평균가격).
  - Sample gap: the official sample's params dict omits `EXCG_ID_DVSN_CD` (domestic_stock_functions.py lines ~4250-4265), although the portal marks it required.
- **-004 inquire-psbl-rvsecncl (TTTC0084R)** is the "open orders" view. Params: `INQR_DVSN_1` (0 by order / 1 by stock), `INQR_DVSN_2` (0 all / 1 sell / 2 buy), `CTX_AREA_*`. Output: `odno`, `orgn_odno`, `pdno`, `ord_qty`, `ord_unpr`, `tot_ccld_qty`, `psbl_qty`, `sll_buy_dvsn_cd`, `ord_dvsn_cd`, `excg_id_dvsn_cd`. Real accounts only.
- **-048 inquire-account-balance (CTRP6548R)**, the asset summary.
  - Params: `CANO`, `ACNT_PRDT_CD`, `INQR_DVSN_1` (blank), `BSPR_BF_DT_APLY_YN` (blank).
  - Output includes `tot_asst_amt`, `nass_tot_amt`, `tot_dncl_amt` (총예수금액), `dncl_amt` (예수금액), `frcr_evlu_tota`, `ovrs_stck_evlu_amt1`, `thdt_rcvb_amt` (당일미수금액), `crdt_fncg_amt`. (Field names are from [OFF-GH] `examples_llm/domestic_stock/inquire_account_balance/chk_inquire_account_balance.py`.)
- **국내주식-191 intgr-margin (TTTC0869R).** Params: `CMA_EVLU_AMT_ICLD_YN`=N, `WCRC_FRCR_DVSN_CD`, `FWEX_CTRT_FRCR_DVSN_CD`. Output includes `acmga_rt` (계좌증거금율), `acmga_pct100_aptm_rson` (reason the account is set to 100% margin), `stck_cash_ord_psbl_amt`, `rcvb_amt` (미수금액). This is the closest thing to an "account trading-terms" answer (margin rate and 100%-margin flag).
- **Ledger lag.** "체결통보 수신 ≠ 당사 원장 반영 완료". Before acting, re-confirm with the buying-power (-007) and sellable-quantity (-165) inquiries. [OFF-NOTICE 227ac529, 2025-05-20]

### 5.2 Overseas stock (all under `/uapi/overseas-stock/v1/trading/`)

| Official id | Name | Path | Real TR | Mock TR | doc mod |
|---|---|---|---|---|---|
| v1_해외주식-005 | 미체결내역 (open orders) | `.../trading/inquire-nccs` | TTTS3018R | 미지원 | 2025-04-30 |
| v1_해외주식-006 | 해외주식 잔고 (holdings) | `.../trading/inquire-balance` | TTTS3012R | VTTS3012R | 2025-04-30 |
| v1_해외주식-007 | 주문체결내역 (orders & fills) | `.../trading/inquire-ccnl` | TTTS3035R | VTTS3035R | 2026-06-11 |
| v1_해외주식-008 | 체결기준현재잔고 (holdings + cash by currency) | `.../trading/inquire-present-balance` | CTRP6504R | VTRP6504R | 2025-04-30 |
| v1_해외주식-013 | 예약주문조회 | `.../trading/order-resv-list` | TTTT3039R (US) / TTTS3014R (Asia) | 미지원 | 2025-05-23 |
| v1_해외주식-014 | 매수가능금액조회 (buying power) | `.../trading/inquire-psamount` | TTTS3007R | VTTS3007R | 2025-04-30 |
| v1_해외주식-032 | 기간손익 | `.../trading/inquire-period-profit` | TTTS3039R | 미지원 | 2025-04-30 |
| 해외주식-035 | 해외증거금 통화별조회 (margin by currency) | `.../trading/foreign-margin` | TTTC2101R | 미지원 | 2025-04-30 |
| 해외주식-063 | 일별거래내역 | `.../trading/inquire-period-trans` | CTOS4001R | 미지원 | 2025-04-30 |
| 해외주식-064 | 결제기준잔고 | `.../trading/inquire-paymt-stdr-balance` | CTRP6010R | 미지원 | 2025-04-30 |
| 해외주식-070 / 071 | TWAP/VWAP fills / order numbers | `.../trading/inquire-algo-ccnl`, `.../trading/algo-ordno` | TTTS6059R / TTTS6058R | 미지원 | 2025-05-23 |

Source: the [OFF-PORTAL] list for "[해외주식] 주문/계좌" (`.../api-list/fae9f1bb-0de9-4523-ab91-6c534e212700`) and [OFF-GH] `examples_user/overseas_stock/overseas_stock_functions.py`.

- **Common precondition.** "해외주식 서비스 신청 후 이용 가능합니다." This appears on the balance, fills, open-orders and buying-power docs.
- **-006 inquire-balance (TTTS3012R).**
  - Params: `CANO`, `ACNT_PRDT_CD`, `OVRS_EXCG_CD` (real: NASD = all US; also NAS/NYSE/AMEX/SEHK/SHAA/SZAA/TKSE/HASE/VNSE), `TR_CRCY_CD` (USD/HKD/CNY/JPY/VND), `CTX_AREA_FK200/NK200`.
  - Output: `ovrs_pdno`, `ovrs_cblc_qty`, `ord_psbl_qty`, `pchs_avg_pric`, `frcr_pchs_amt1`, `ovrs_stck_evlu_amt`, `now_pric2`, `frcr_evlu_pfls_amt`, `tr_crcy_cd`, `ovrs_excg_cd`, plus totals (`tot_evlu_pfls_amt`, `frcr_buy_amt_smtl1`).
  - Mini-stock holdings are not included ("미니스탁 잔고는 해당 API로 확인이 불가").
  - In the US daytime session, valuation follows night prices.
- **-008 inquire-present-balance (CTRP6504R).**
  - Params: `WCRC_FRCR_DVSN_CD` (01 KRW / 02 foreign), `NATN_CD` (000 all, 840 US, ...), `TR_MKET_CD`, `INQR_DVSN_CD`.
  - output2 (per currency): `frcr_dncl_amt_2` (외화예수금액2), `frcr_drwg_psbl_amt_1` ("출금가능한 외화금액"), `frst_bltn_exrt`.
  - output3: `tot_asst_amt`, `tot_dncl_amt`, `wdrw_psbl_tot_amt`, `frcr_use_psbl_amt`, `frcr_evlu_tota`.
  - In mock only output3 is valid.
  - It is not real-time at night: "야간에 실시간 잔고 반영이 안 됩니다". [OFF-FAQ 1f4b60d6, 2022-08-10]. That FAQ also mentions a day/night ledger API (`dayornight`, JTTT3012R) that **does not appear in the current portal list**, so treat it as possibly stale.
  - US trades after about 18:10 are not reflected in real time.
- **-007 inquire-ccnl (TTTS3035R).**
  - Params: `PDNO` ("%" = all), `ORD_STRT_DT`/`ORD_END_DT` (local date), `SLL_BUY_DVSN`, `CCLD_NCCS_DVSN`, `OVRS_EXCG_CD`, `SORT_SQN`, `ORD_DT`/`ORD_GNO_BRNO`/`ODNO` (blank; "주문번호로 검색 불가능합니다").
  - Output: `odno`, `orgn_odno`, `pdno`, `ft_ord_qty`, `ft_ord_unpr3`, `ft_ccld_qty`, `ft_ccld_unpr3`, `ft_ccld_amt3`, `nccs_qty`, `prcs_stat_name`, `rjct_rson`, `tr_crcy_cd`.
  - Fractional-share trades are not shown.
- **-005 inquire-nccs (TTTS3018R).** Params: `OVRS_EXCG_CD` (required for paging; NASD = all US), `SORT_SQN`, `CTX_AREA_*`. In mock, use -007's `nccs_qty` instead.
- **-014 inquire-psamount (TTTS3007R).** Params: `OVRS_EXCG_CD`, `OVRS_ORD_UNPR`, `ITEM_CD`. Output: `ord_psbl_frcr_amt`, `ovrs_ord_psbl_amt`, `max_ord_psbl_qty`, `echm_af_ord_psbl_amt`, `exrt`.
- **-035 foreign-margin (TTTC2101R).** Params: `CANO`, `ACNT_PRDT_CD`. Output: `natn_name`, `frcr_dncl_amt1`, `ustl_buy_amt`, `ustl_sll_amt`, `frcr_rcvb_amt`, `frcr_ord_psbl_amt1`, `itgr_ord_psbl_amt`, `bass_exrt`.

### 5.3 Product information (eligibility-adjacent, outside `/trading/`)

| Name | Path | TR | What it answers | doc mod |
|---|---|---|---|---|
| 상품기본조회 v1_국내주식-029 | `/uapi/domestic-stock/v1/quotations/search-info` | CTPF1604R | `prdt_risk_grad_cd` (product risk grade), `ivst_prdt_type_cd` | 2025-05-14 |
| 주식기본조회 v1_국내주식-067 | `/uapi/domestic-stock/v1/quotations/search-stock-info` | CTPF1002R | `scty_grp_id_cd` (EF ETF / EN ETN / EW ELW), `etf_chas_erng_rt_dbnb` (ETF tracking multiple), `etf_etn_ivst_heed_item_yn`, `tr_stop_yn`, `admn_item_yn`, `cptt_trad_tr_psbl_yn` (NXT tradable) | 2025-05-14 |
| 해외주식 상품기본정보 v1_해외주식-034 | `/uapi/overseas-price/v1/quotations/search-info` | CTPF1702R | `sgle_item_lvrg_etp_yn` (single-stock leveraged ETP), `etp_chas_erng_rt_dbnb` (ETP multiple), `ovrs_stck_etf_risk_drtp_cd`, ETP underlying class codes | 2026-08-11 |
| 당사 신용가능종목 국내주식-111 | `/uapi/domestic-stock/v1/quotations/credit-by-company` | FHPST04770000 | which stocks the broker allows on credit (product level) | 2026-04-10 |
| 당사 대주가능 종목 국내주식-195 | `/uapi/domestic-stock/v1/quotations/lendable-by-company` | CTSC2702R | which stocks can be borrowed (대주) (product level) | 2026-04-10 |

Notes on these:
- Overseas product info is blocked from 08:59 to 09:31 KST with "[EGW00317] 09:00 ~ 09:30 시간 동안에는 조회하실 수 없습니다." [OFF-NOTICE 365bc02b, 2026-07-24]
- The ETP class fields were added 2026-08-14. [OFF-NOTICE bb8d1be5]
- All of these are **product** attributes. None of them says whether **this account** may trade the product.

### 5.4 Eligibility: what is and is not documented

- **Overseas leveraged ETP 기본예탁금 and single-stock leveraged ETP 심화 사전교육**, effective 2026-05-22.
  - The target is the order API only: "대상 API : [해외주식] 주문/계좌 > 해외주식 주문".
  - A failing account gets `rt_cd "7"`, `msg_cd "APBK1681"`, "해당종목은 기본예탁금 충족한 계좌만 매수주문가능합니다".
  - Source: [OFF-NOTICE 15abe578, 2026-05-20] `.../000000000001/post/15abe578-7871-4f6d-80e7-ee1e40ffc0f3`
  - **No inquiry API reports whether the account meets the requirement; it surfaces only as an order rejection.**
- **Best-execution disclosure (최선집행의무 설명서).** Without registration, domestic stock orders fail with `APBK1943` "최선집행기준 설명서 미교부 고객은 주문이 불가합니다." [OFF-NOTICE 0778faf1, 2025-02-13]. No inquiry API exposes this status.
- **Domestic leveraged/inverse ETP pre-education and 기본예탁금** (the domestic rule): **not documented** anywhere in the KIS API docs, notices or FAQ that were checked. No rejection code is documented for it either.
- **Short selling eligibility: not documented.** Only the product-level lendable list (CTSC2702R) exists.
- **Derivatives account.** It needs a product-03 account registered under the key [OFF-FAQ 0b29069f]. Futures/options inquiries exist (`/uapi/domestic-futureoption/v1/trading/inquire-balance` CTFO6118R, `/trading/inquire-deposit` CTRP6550R). No eligibility API.
- **ELW.** Ordered through the ordinary cash-order API: "PDNO(상품코드)에 ELW 종목코드를 입력" [OFF-FAQ 842f4450, 2025-07-28]. ELW pre-education and deposit status: **not documented**.
- **Overseas trading enabled (해외주식 서비스 신청).** The error text "해외투자가 불가능한 계좌입니다. 확인하세요." is the title of [OFF-FAQ 704eedbe]. Which endpoint returns it, and whether a read-only inquiry such as inquire-psamount returns it on an account that has not applied, is **not documented** (it would be an inference).
- **Margin / credit status.** Account-level signals from read-only calls:
  - `acmga_rt` and `acmga_pct100_aptm_rson` from intgr-margin (TTTC0869R).
  - Credit buying power from inquire-credit-psamount (TTTC8909R).
  - Their exact semantics are not documented beyond the field names.

### 5.5 WebSocket fill notices (receive-only)

- **Connection.** Real: `ws://ops.koreainvestment.com:21000`. Mock: `ws://ops.koreainvestment.com:31000`. [OFF-GH kis_devlp.yaml]. The header carries `approval_key`, `custtype`, `tr_type` (1 subscribe / 2 unsubscribe), `content-type`. The body carries `tr_id` and `tr_key`.
- **Domestic H0STCNI0 (mock H0STCNI9)** [OFF-PORTAL `/tryitout/H0STCNI0`, doc mod 2025-04-30]
  - `tr_key` = **HTS ID**.
  - Two message types: "14번째 값(CNTG_YN;체결여부)가 2이면 체결통보" (fill); value 1 = order/modify/cancel/reject acknowledgement.
  - The payload is encrypted: "체결 통보 응답 결과는 암호화되어 출력됩니다." It is decrypted with the AES256 key and IV returned at subscribe.
  - Fields: `CUST_ID`, `ACNT_NO`, `ODER_NO`, `OODER_NO`, `SELN_BYOV_CLS`, `RCTF_CLS`, `ODER_KIND`, `STCK_SHRN_ISCD`, `CNTG_QTY`, `CNTG_UNPR`, `STCK_CNTG_HOUR`, `RFUS_YN`, `CNTG_YN`, `ACPT_YN`, `ODER_QTY`, `ORD_EXG_GB`, `CRDT_CLS`, `ODER_PRC`.
  - The field set changed on 2025-03-04 (ATS): `CNTG_ISNM` removed; `ORD_COND_PRC`, `ORD_EXG_GB`, `POPUP_YN`, `FILLER` added. [OFF-FAQ 26ee44dd; OFF-NOTICE cad37f81]
- **Overseas H0GSCNI0 (mock H0GSCNI9)** [OFF-PORTAL `/tryitout/H0GSCNI0`, doc mod 2025-05-23]
  - Same structure, `tr_key` = HTSID.
  - `CNTG_UNPR12` was added 2025-12-20 [OFF-NOTICE 3c75de0f].
  - Notes from the doc: "특정 거래소의 체결시간 데이터는 수신되지 않습니다." Also, `CNTG_QTY` carries the order quantity on order acknowledgements.
- **Scope of notices.** "체결통보의 경우 HTS ID 단위로 등록하여, ID에 연결된 모든 계좌의 체결 통보 수신" [OFF-NOTICE d0d1a83f]. So one subscription delivers fills for **every account under that HTS ID**, not only the CANO configured in E1.
- **Final-fill detection.** There is no "fully filled" flag: "최종 체결 여부를 직접 알려주는 별도 정보가 제공되지 않습니다". Sum `CNTG_QTY`, or compare `ord_qty` with `tot_ccld_qty` from -005. [OFF-FAQ 4f86cd4d, 2025-08-11]
- **Keep-alive.** The server closes the session after 100 s with no data; answer PINGPONG with a pong. [OFF-FAQ 07f312e5, 2023-11-22]. Do not reconnect in tight loops: IP and key blocking (section 3.4).
- **Is it read-only?** The documented WebSocket TRs are all real-time data and notices, and the client only sends subscribe/unsubscribe frames. An explicit statement that orders cannot be sent over the socket is **not documented**.

### 5.6 Deposit/withdrawal address lists

Not applicable to a securities broker. Neither the "[국내주식] 주문/계좌" nor the "[해외주식] 주문/계좌" list contains any transfer, withdrawal or bank-account endpoint (checked against the portal JSON lists). The withdrawable amounts that are visible come from read-only fields: `frcr_drwg_psbl_amt_1` and `wdrw_psbl_tot_amt` (overseas -008), and `prvs_rcdl_excc_amt` (D+2, domestic -006).

## 6. What distinguishes read-only from trading at the protocol level

1. **HTTP method.** "접근토큰발급과 주문은 POST 방식, 그 외 조회는 GET 방식으로 호출해야". [OFF-FAQ 695cfecd, 2025-08-19] Every account inquiry in section 5 is GET; every order (`order-cash`, `order-credit`, `order-rvsecncl`, `order-resv*`, overseas `order*`, `daytime-order*`) is POST.
2. **TR id.** "API 호출 시 TR ID 첫 글자는 해당 서버(원장)를 지정합니다." (T stock, S night F&O, O overseas F&O, C other, V mock). [OFF-FAQ 587c7efd, 2025-08-11]
   - *Observation, not a documented rule:* in the official tables every inquiry TR ends in `R` and every order TR ends in `U` (TTTC0011U/0012U/0013U, TTTT1002U/1006U/1004U, CTSC0008U/0009U/0013U).
   - The routing is by TR: "TR 기준으로 원장에 호출을 하기 때문에 TR이 보다 정확한 구분값". [OFF-FAQ 5c706351, 2023-05-10]
3. **Path is not a separator.** Inquiries and orders share `/uapi/domestic-stock/v1/trading/` and `/uapi/overseas-stock/v1/trading/`. Examples: `.../trading/inquire-balance` versus `.../trading/order-cash`, and overseas `.../trading/inquire-balance` versus `.../trading/order`.
4. **Domain is not a separator either.** The FAQ warns that with a switched domain, calls may still go through by TR: "도메인을 변경해서 사용하시면 TR 기준으로 API 호출되어서 거래가 되는 경우가". [OFF-FAQ 5c706351]
5. **Credentials are identical.** The same token, appkey and appsecret serve both (section 1.1). There is no per-call secret, PIN or account password on orders. Hashkey is not required in the current sample (section 2.8).
6. **The official sample silently rewrites TR ids for mock.** It turns a leading T/J/C into V: `if ptr_id[0] in ("T", "J", "C"): ... tr_id = "V" + ptr_id[1:]`. [OFF-GH kis_auth.py, lines 422-424]

## 7. Sandbox / paper environment (모의투자)

- **Hosts.** REST `https://openapivts.koreainvestment.com:29443` (portal `virtualDomain`). WebSocket `ws://ops.koreainvestment.com:31000`. [OFF-PORTAL tokenP JSON; OFF-GH kis_devlp.yaml]
- **Separate credentials.** It needs its own mock app key and secret (`paper_app` / `paper_sec`) and a mock account number. "TR_ID: V로 시작, ex) VTTT1234U", "앱정보: 모의계좌번호, 모의계좌의 appkey, appsecret". [OFF-FAQ 5c706351]
  - Mock account numbers: "모의투자 계좌는 5로 시작할 경우 주식," (6 = futures/options). [OFF-NOTICE 747384fe, 2026-08-25]
  - Corporations cannot use mock (EGW00210).
- **Inquiry coverage in mock.** Supported: domestic -005 (VTTC0081R / VTSC9215R), -006 (VTTC8434R), -007 (VTTC8908R); overseas -006 (VTTS3012R), -007 (VTTS3035R), -008 (VTRP6504R, output3 only), -014 (VTTS3007R); WebSocket H0STCNI9 / H0GSCNI9. **Everything else in sections 5.1 and 5.2 is "모의투자 미지원"**: cancellable orders, asset summary, margin, sellable quantity, overseas open orders, foreign margin, and the rest.
- **Limits and behaviour.**
  - 1 REST call/s (Notice d0d1a83f).
  - Mock runs on a separate operator: "모의투자는 별도 운영사(연합인포맥스)에서 시스템을 관리". [OFF-NOTICE 9858397d, 2024-03-27]
  - KRX only, no NXT. [OFF-NOTICE dd2e7e20]
  - Fills happen only when the real market trades at that price. [OFF-FAQ ca2cc700]
  - An expired mock account fails with "40910000 모의투자 주문이 불가한 계좌입니다." [OFF-NOTICE 747384fe]
- **Other test tools.** The official GitHub includes a backtester and strategy builder, and KIS recommends mock before going live. [OFF-FAQ 6005110f, 2026-04-07]

## 8. Error codes for auth and rate limits

Source is [OFF-ERR] unless noted.

| Code | Text (official) | Meaning for E1 |
|---|---|---|
| EGW00103 / EGW00105 | 유효하지 않은 AppKey입니다. / 유효하지 않은 AppSecret입니다. | Bad, cancelled or renewed key |
| EGW00121 | 유효하지 않은 token 입니다. | Token invalid; reissue, respecting 1/min |
| EGW00122 | token을 찾을 수 없습니다. | Token unknown |
| EGW00123 | 기간이 만료된 token 입니다. | Token expired (24 h) |
| EGW00133 | 접근토큰발급 잠시후 다시 시도하세요(1분당 1회) | tokenP called twice in one minute [OFF-NOTICE b9136772; not on the error page] |
| EGW00201 | 초당 거래건수를 초과하였습니다. | Per-key rate limit (18/s real, 1/s mock) |
| EGW00215 | 원장에서 허용 가능한 초당 거래건수를 초과하였습니다. | Cross-customer 120 TPS cap on TTTC8434R; retry [OFF-PORTAL inquire-balance] |
| EGW00205 | credentials_type이 유효하지 않습니다.(Bearer) | Missing "Bearer " prefix |
| EGW00206 | API 사용 권한이 없습니다. | Permission denied (when it triggers is not documented) |
| EGW00207 | IP 주소가 없거나 유효하지 않습니다. | Corporate IP header |
| EGW00213 | 모의투자 tr이 아닙니다. | Real TR sent to the mock host |
| EGW00304 | 고객식별키(법인 personalSeckey, 개인 appSecret)가 유효하지 않습니다. | Bad appsecret header |
| EGW00356 | 타겟 서버가 올바르지 않습니다 | Wrong TR first letter [OFF-FAQ 587c7efd] |
| EGW00317 | 09:00 ~ 09:30 시간 동안에는 조회하실 수 없습니다. | Overseas product-info time block [OFF-NOTICE 365bc02b] |
| EGW00301 / EGW00302 | 연결 시간이 초과되었습니다. / 거래시간이 초과되었습니다. (직전 거래를 반드시 확인하세요) | Timeouts |
| OPSP0002 / OPSP0008 / OPSP8996 / OPSP0011 | ALREADY IN SUBSCRIBE / MAX SUBSCRIBE OVER / ALREADY IN USE appkey / invalid approval(appkey) : NOT FOUND | WebSocket: duplicate subscription / over 41 / second session / bad approval key |
| (msg) | 처리계좌의 ID와 사용자정보가 상이하여 주문처리 불가능합니다. | HTS ID changed after key issue; enforced on TTTS3012R and TTTS3018R from 2026-08-17 [OFF-NOTICE bff7ecdb] |
| 90070000 / 40910000 | 모의투자 처리계좌의 ID와 사용자정보가 상이 / 모의투자 주문이 불가한 계좌 | Mock account mismatch / mock account expired [OFF-NOTICE 747384fe] |
| HTTP 403 | (FAQ) | Wrong host or wrong method (GET vs POST) [OFF-FAQ 695cfecd] |
| (msg) | 비밀번호 [5회] 오류입니다. | Account password changed after key issue; re-register [OFF-FAQ 765ed450] |

`rt_cd` is "0" on success. Order rejections use `rt_cd "7"` (APBK codes), but those are not part of E1.

## 9. Open questions (not documented; would need KIS VOC or a live test with the owner's approval)

1. **Inquiry-only key.** Is there any way to issue an app key or token that cannot place orders? The docs say the token calls "모든 API". The EGW00109/EGW00110 scope errors appear to belong to the partner Authorization-Code flow. This is the central risk for E1.
2. **Repo guard conflict.** Every E1 REST endpoint path contains `/uapi/domestic-stock/v1/trading/` or `/uapi/overseas-stock/v1/trading/`. A guard that bans that string blocks E1 entirely. The owner must decide how to tell inquiry from order (for example GET plus an allowlist of R-suffix TR ids). The path cannot be the discriminator.
3. **Revocation on reissue.** After the 6 h window, does a newly issued token invalidate an older one that is still within its 24 h? This matters if TRADEGEN and any other tool share a key.
4. **tokenP limit wording.** Official sources give 1/min (Notice 2023-10-17, FAQ 2025-08-11, README), 1/s (rate notice), and 5 min (FAQ 2023-07-18). Treat 1/min as binding; KIS has not reconciled these.
5. **What counts toward the 18/s.** Do tokenP, Approval and WebSocket traffic count toward the per-key REST limit? Not documented. Also not documented: whether the 3/s new-registration limit applies again after the yearly renewal (the notice says renewal goes straight to the base limit, but re-registration after cancellation counts as new).
6. **Eligibility.** There is no inquiry API for domestic leveraged/inverse ETP pre-education and 기본예탁금, overseas leveraged-ETP 기본예탁금 (APBK1681 appears only on orders), short selling, ELW, or derivatives-account status. The only read-only proxies are product-level flags plus the margin fields `acmga_rt` and `acmga_pct100_aptm_rson`. No rejection code is documented for the domestic leveraged-ETP rule.
7. **Overseas service not enabled.** On an account that has not applied, does a read-only inquiry (inquire-psamount, inquire-balance) fail with "해외투자가 불가능한 계좌입니다", which would make it a usable eligibility probe? Not documented.
8. **HTS-ID-wide fill notices.** H0STCNI0 and H0GSCNI0 deliver fills for every account under the HTS ID, so E1 must filter on `ACNT_NO`. The format of `ACNT_NO` in the notice (8 or 10 digits) is not documented.
9. **Missing required parameter in the sample.** inquire-daily-ccld: the official sample omits `EXCG_ID_DVSN_CD`, which the portal marks required. Which is correct is unverified.
10. **Overseas day/night ledger.** The 2022 FAQ references a `dayornight` API and the JTTT3012R TR, which are absent from the current portal list. Current behaviour of the overseas balance during the US daytime session is documented only as "valuation differs from HTS".
11. **KakaoTalk alert on token issuance.** Can E1 rely on it as an out-of-band intrusion signal (does it fire for the same-token return within 6 h)? Not documented.
12. **Mock coverage gap.** Most E1 endpoints are not supported in mock, so tests of -004, -048, -165, -191, overseas -005 and -035 can only use recorded fixtures, never a sandbox call.

---

## Verification (skeptic)

Checked 2026-10-24 by an independent pass. Documentation only: no key was used and no account or trading endpoint was called.

**Method.** I re-fetched every cited official source myself:
- the portal's per-API JSON (`https://apiportal.koreainvestment.com/api/apis/public/detail?accessUrl=<path>`);
- both account-category lists (`https://apiportal.koreainvestment.com/api/apis/public/api-list/b0a44bfd-dfd5-47f1-9b06-758383e595db` and `.../api-list/fae9f1bb-0de9-4523-ab91-6c534e212700`);
- all 119 notices and 173 FAQ posts, through the portal's own forum JSON (`https://apiportal.koreainvestment.com/api/forums/<forumId>/posts`);
- the error-code content JSON (`https://apiportal.koreainvestment.com/api/contents/kind?title=ERRORCODE&kind=CONTENTS`, lastModified 2025-04-25), which is what `https://apiportal.koreainvestment.com/faq-error-code` renders;
- the GitHub files at main `cd63caee6a` (2026-10-23).

Every cited post id resolved to an existing official post. Quotes below are verbatim from those fetches. [3P] claims were not re-checked; none is load-bearing.

**URL shorthand used below** (each expands to a full official URL):
- `N:<id>` = `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000001/post/<id>` (notices)
- `F:<id>` = `https://apiportal.koreainvestment.com/community/10000000-0000-0011-0000-000000000002/post/<id>` (FAQ)
- `P:<path>` = `https://apiportal.koreainvestment.com/apiservice-apiservice?<path>` (API guide)
- `ERR` = `https://apiportal.koreainvestment.com/faq-error-code`
- `GH:<file>` = `https://github.com/koreainvestment/open-trading-api/blob/main/<file>`

**Bottom line.** The note holds up. Four claims are **WRONG** (5.1 INQR_DVSN, 5.1 sample gap, 5.4 domestic ETP rule, 6.1 `order-resv*` wording) and two have **omissions** (2.7 approval-key expiry, 4.6 tier is time-limited). The central risk is unchanged and now confirmed: **no read-only key or scope exists for individuals**, so order blocking must be enforced on the client.

Claims are listed in the note's numerical order.

### 0. Short answers

- **0.1 Inquiry-only key.** CONFIRMED that none exists. F:58eeac3f-f5b5-4f22-a48d-ffd668fac8b4: "해당 토큰을 활용하여 조회 및 매수/매도 등 모든 API를 호출할 수 있습니다." Whether a read-only key would be refused for orders server-side is **UNVERIFIED and moot**: no such key type is documented. The only official order block is the IRP (29) account type (1.3), and no error code for an IRP order attempt is documented.
- **0.2 Key-to-account binding.** CONFIRMED (see 1.4 and 1.6).
- **0.3 Access token.** CONFIRMED (2.1 to 2.6). Revoke-on-reissue is UNVERIFIED (2.5).
- **0.4 Two programs on one key.** CONFIRMED (4.1, 4.5). What happens to program A's token is UNVERIFIED (2.5).
- **0.5 Real-account rate limit.** CONFIRMED (4.1 to 4.3).
- **0.6 Inquiries under `/trading/`.** CONFIRMED. All 41 entries in the two lists (30 GET, 11 POST) sit under `/trading/`. The names also mislead (see 6.1).
- **0.7 Eligibility API.** CONFIRMED that none is documented, with one correction (5.4: notice 15abe578 does mention the domestic single-stock leveraged/inverse ETP training).
- **0.8 Mock environment.** CONFIRMED (section 7).
- **0.9 WebSocket fill notices.** CONFIRMED (5.5).
- **0.10 No transfer API.** CONFIRMED. Neither list contains a transfer, withdrawal or bank-account endpoint.

### 1. Authentication and key scopes

- **1.1 One token for everything.** CONFIRMED (same quote as 0.1).
- **1.2 No scope parameter for individuals.** CONFIRMED. P:/oauth2/tokenP (doc mod 2025-04-28) has exactly three body properties: `grant_type`, `appkey`, `appsecret`. Individuals follow "OAuth 2.0의 Client Credentials Grant 절차를 준용"; partners follow "Authorization Code Grant 절차를 준용".
  - EGW00109 and EGW00110 are on ERR: CONFIRMED ("scope는 필수입니다.").
  - Whether scopes apply to individual keys: UNVERIFIED.
- **1.3 IRP is inquiry-only; DC cannot use the API.** CONFIRMED. F:0b29069f-812b-4a70-94db-63d07d5ad54c: "IRP(29): 주문은 불가하며, 계좌조회/시세조회만 이용 가능합니다." Also F:34b89bae-7d22-45b4-a8cc-2781fbbcd7aa: "IRP(29)계좌는 매매 기능이 제공되지 않고 조회 기능만 지원". The error code an IRP order would return is UNVERIFIED.
- **1.4 Key-to-account binding.**
  - Per 8-digit number: CONFIRMED. F:34b89bae-7d22-45b4-a8cc-2781fbbcd7aa: "종합계좌번호(8자리) 단위로 Open API 서비스 신청 및 앱 발급이 되므로".
  - CANO and ACNT_PRDT_CD: CONFIRMED. F:2b6c34cb-8067-4efa-a0f2-043644c922ab: "CANO에 종합계좌번호 8자리, ACNT_PRDT_CD에 계좌상품코드 2자리".
  - Codes 22 and 29: CONFIRMED. GH:kis_devlp.yaml: `# my_prod: "22" # 개인연금` and `# my_prod: "29" # 퇴직연금`.
  - Account limits: CONFIRMED. N:0d5bc017-eb8b-431a-98da-a2854f17f110: "실전투자계좌의 경우 최대 89개, 모의투자계좌의 경우 최대 2개까지".
  - Own accounts only: CONFIRMED. F:4cd60e0e-1c8a-4243-b0d6-23c55526de19: "현재 본인계좌 이외에는 매매가 불가능합니다."
- **1.5 Key lifetime.** CONFIRMED. N:0d5bc017-eb8b-431a-98da-a2854f17f110: "유효기간은 1년이며 만료 30일 전부터 앱키를 갱신하실 수 있습니다." and "갱신시 APP Key, APP Secret는 새로 발급됩니다." A renewal sends the cancellation notice first: F:544bdacd-16f1-47a1-9fa5-5a8f508981be, "갱신 시 ‘해지’ 알림이 먼저 발송되지만".
- **1.6 Events that invalidate the key.**
  - Password change: CONFIRMED. F:f7f6c853-fa53-4fed-84bd-f66e8b3c3929: "계좌비밀번호를 변경하신 경우는 기존 앱키, 앱시크리트 사용이 불가합니다."
  - HTS ID change: CONFIRMED. N:bff7ecdb-f13c-40d3-a5e6-403a5a9e0a6b: "기존에 발급받은 API Key는 더 이상 사용하실 수 없으며", effective 2026.08.17. Nit: the notice prints the TR ids as "TTS3012R / TTS3018R" (one T missing). The portal's real ids are TTTS3012R and TTTS3018R, so the note reads them correctly.
  - Manual cancellation: CONFIRMED. F:6a66821c-f902-466e-b9a1-76b80cd32985: "해지 완료 시 발급되었던 APP Key, APP Secret는 사용이 불가능합니다."
- **1.7 The secret goes on every call.** CONFIRMED. P:/uapi/domestic-stock/v1/trading/inquire-balance lists header `appsecret` as req=Y, with the note "(절대 노출되지 않도록 주의해주세요.)". Nit: `custtype` is req=N on inquire-balance but req=Y on order-cash, so send it always.
- **1.8 HTS ID.** CONFIRMED.
  - GH:README.md line 252: "체결통보, 나의 조건 목록 확인 등에 사용됩니다."
  - GH:examples_user/domestic_stock/domestic_stock_functions.py line 11347: "HTS ID에 반드시 연결되어있어야만 API 신청 및 앱정보 발급이 가능".
- **1.9 Terms of use.** CONFIRMED. F:1f422ddb-7a9c-4279-9ecb-21eb750a4b7a: "자신의 보안코드(앱키, 시크릿키)가 유출 및 도용되지 않도록 관리해야".

### 2. Token and signature rules and lifetimes

- **2.1 tokenP response.** CONFIRMED. The P:/oauth2/tokenP response example has `access_token_token_expired`, `token_type` "Bearer" and `expires_in` 86400. (The field's own description example, 7776000 s, is the 90-day partner value.)
- **2.2 Lifetime and reissue.** CONFIRMED.
  - P:/oauth2/tokenP: "갱신발급주기는 6시간 입니다.(6시간 이내는 기존 발급키로 응답)".
  - N:7e0da1f9-9540-4530-8ca9-cb1da1cc68ed: "6시간 이후에 발급 요청시 토큰값 신규생성 및 결과 값 리턴".
- **2.3 Issue-rate limit, EGW00133 at 1 per minute.** CONFIRMED.
  - N:b9136772-4f5b-4e72-92c5-bf9429b392fd: "1분당 1회 호출가능, 2회 이상 호출시 오류 리턴".
  - F:a046c19e-d638-4eda-bd1a-264934fdfd5e: "1분 내 2회 이상 호출 시 오류가 반환됩니다."
  - GH:README.md line 390: "토큰 재발급 - 1분당 1회 발급됩니다."
  - The conflicts are real:
    - F:0ad7f35e-8ada-4c37-ae11-c9ee293f3720 says "5분당 1회 (2023.10.27일부터 적용)".
    - N:d0d1a83f-6f8d-4437-9700-6d26702fd989 says "접근토큰발급(/oauth2/tokenP)의 경우 1초당 1건(23.10.27 시행)".
  - EGW00133 is absent from ERR: CONFIRMED.
- **2.4 KakaoTalk alert on issuance.** CONFIRMED.
  - N:b9136772-4f5b-4e72-92c5-bf9429b392fd: "접근토큰발급 사실을 카톡 등을 통하여 안내드리고".
  - GH:examples_user/kis_auth.py line 192: "발급시 알림톡 무조건 발송".
- **2.5 Does a new token revoke the old one?** UNVERIFIED. It is not stated in the tokenP doc, in N:7e0da1f9, or in the other tokenP FAQ, F:f2b74a2b-c63e-496a-81fc-fece1b38a825 (2023-06-07).
- **2.6 Explicit revoke.** CONFIRMED. P:/oauth2/revokeP (doc mod 2022-04-24) has body `appkey`, `appsecret` and `token`, all req=Y. Purpose: "부여받은 접큰토큰을 더 이상 활용하지 않을 때 사용합니다."
- **2.7 WebSocket approval key.** CONFIRMED. P:/oauth2/Approval (doc mod 2023-06-27) has body `grant_type`, `appkey`, `secretkey`, and says "접속키는 세션 연결 시 초기 1회만 사용하기 때문에".
  - **Omission:** the same doc says "접속키의 유효기간은 24시간이지만". The key itself expires after 24 h; only a session that is already open keeps running.
  - Issue limit of 1 per second: CONFIRMED. N:d0d1a83f: "접속키 발급의 경우, 초당 1건으로 발급 제한".
- **2.8 No HMAC signature; hashkey is optional.** CONFIRMED.
  - The portal JSON for `/uapi/hashkey` returns "API 정보가 존재하지 않습니다."
  - The inquire-balance and order-cash header lists contain no signature field.
  - GH:examples_user/kis_auth.py line 442: `# if (hashFlag): set_order_hash_key(headers, params)`. Line 270: "현재는 hash key 필수 사항아님".
  - A stronger source the note missed: N:21106822-e6da-4fb8-a718-7bb22159923b (2022-08-25), "hashkey값을 넣어도, 넣지 않아도 정상 호출됩니다."
  - EGW00131 is on ERR: CONFIRMED.
- **2.9 Transport.** CONFIRMED.
  - N:1510666f-5770-4de4-b0ff-2497ca98c616: "12.12(금) 이후부터는 TLS 1.0, 1.1로 호출 시 서비스 이용이 불가".
  - F:efa49825-6875-4f57-bf5f-c7094016d4fb: "wss(SSL 암호화) 접속은 지원하지 않습니다".

### 3. IP binding

- **3.1 None for individuals.** CONFIRMED. F:691e2917-3eb9-486b-b94c-9630a5c186c6: "별도의 IP 화이트리스트 운영 없이 전체 허용 정책입니다."
- **3.2 No fixed IP needed.** CONFIRMED.
  - F:c5c4f097-0f6d-46b9-aa0c-26e80519b9a8: "접속 IP와 무관하게 인증이 이루어지기 때문에 고정 IP가 필요하지 않습니다."
  - F:ff32a7fd-f6fc-4cb9-bfac-cb094eff4b62: "IP 허용 요청은 별도로 처리되지 않으며".
- **3.3 Corporate only.** CONFIRMED. The `ip_addr` header on P inquire-balance and order-cash reads "[법인 필수] 사용자(회원)의 IP Address". ERR lists EGW00303 "법인고객에게 허용되지 않은 IP접근입니다."
- **3.4 Abuse blocking.** CONFIRMED. N:4f34b068-3203-40fb-8936-c3bad5f154c0: "고객님의 IP 및 앱키가 일시 차단 될 수".
- **Consequence.** A leaked appkey plus appsecret works from any IP. Individuals have no IP-binding defence.

### 4. Rate limits

- **4.1 REST limits.** CONFIRMED. N:d0d1a83f-6f8d-4437-9700-6d26702fd989:
  - "(실전투자) 1초당 18건 (기존 20건)" and "(모의투자) 1초당 1건 (기존 2건)";
  - "1계좌당 1초당 18건";
  - spacing: "100ms ~ 150ms 텀을 두고";
  - retry: "즉시 재호출 수행 부탁드립니다".
  - Account, app key and 8-digit number are the same unit: CONFIRMED. N:eb3e2dcb-3d52-4ff1-9eb2-c09b1c880fb2: "계좌(appkey) 단위로 적용됩니다. (=종합계좌번호 8자리 단위)". F:bcfb94ee-5aa3-4915-bca6-d63378c620c2 gives the old figure, "1개의 앱키당 실전투자 1초당 20건". Nit: that FAQ is dated 2022-11-14 in KST; the note's 11-13 is the UTC date.
- **4.2 New registrations.** CONFIRMED. N:c1113824-17c7-47a7-b7b8-8880506a847c:
  - "신청 시점으로부터 3일 동안 초당 3건으로 제한";
  - "서비스 해지 후 등록 시에는 신규 등록으로 간주";
  - "모의투자 계좌는 해당되지 않습니다";
  - renewal: "갱신 시에는 기본 유량으로 자동 상향 처리".
- **4.3 Stock-balance cap across all customers.** CONFIRMED.
  - P inquire-balance: "개인 고객 유량 무관하게 초당 120 TPS로 제한".
  - N:050d6619-c967-46c2-840c-7e8f1c18ebc4: "초당 120 건으로 총량 제한".
- **4.4 Token and approval key limits.** CONFIRMED (see 2.3 and 2.7).
- **4.5 WebSocket.** CONFIRMED.
  - N:d0d1a83f: "실시간 데이터 합산 41건까지 등록 가능" and "1개의 PC에서 여러 개의 계좌(앱키)로 세션 연결 가능".
  - ERR: OPSP0008 "MAX SUBSCRIBE OVER" and OPSP8996 "ALREADY IN USE appkey".
  - F:434b97f1-c130-470e-b682-f184f00f1b50: "한 사용자가 2개의 소켓을 열 수 없습니다."
- **4.6 Optional higher tier.** **Omission**, current status UNVERIFIED. N:eb3e2dcb confirms 50/s REST and 201 WS subscriptions for accounts with at least KRW 7.5 bn of Open API volume, but only as a one-month programme: "12월 한 달간(12.1~12.31) 아래와 같이 유량을 확대 적용". That was December 2025, judged on volume from 11.3 to 11.27. No official source says whether it still runs in October 2026. It is irrelevant at KRW 42k.
- **4.7 Stale figures elsewhere.** CONFIRMED.
  - GH:examples_user/kis_auth.py line 146 `_smartSleep = 0.05` and line 151 `_smartSleep = 0.5`.
  - F:8548106c-c7a8-4126-abb7-b8ec46a8cb5c: "1초당 10건".
  - [3P] AlgoLab was not re-checked.
- **4.8 Page sizes.** CONFIRMED in each P doc:
  - inquire-balance: "최대 50건" (real) / "최대 20건" (mock);
  - inquire-daily-ccld: 100 / 15;
  - inquire-psbl-rvsecncl: 50;
  - overseas inquire-balance: 100;
  - inquire-ccnl: 20 / 15;
  - inquire-nccs: 40.
  - `tr_cont` "F or M : 다음 데이터 있음": CONFIRMED.

### 5. Read-only endpoints

- **5.0 Common headers, hosts, GET.** CONFIRMED.
  - Every inquiry in both lists has httpMethod GET.
  - The tokenP JSON gives realDomain `https://openapi.koreainvestment.com:9443` and virtualDomain `https://openapivts.koreainvestment.com:29443`.
  - `rt_cd`: "0 : 성공 / 0 이외의 값 : 실패".
- **5.1 Domestic table.** CONFIRMED. All 14 rows match the domestic list JSON on path, real TR, mock TR and doc mod.
  - -004 old TR, from its own doc: "(구)TTTC8036R → (신)TTTC0084R".
  - Pension -033: "TTTC2201R(기존 KRX만 가능), TTTC2210R (KRX,NXT/SOR)".
  - **-006 params:** CONFIRMED. AFHR_FLPR_YN N/X/Y is in the P doc, and N:26dfe350-eb72-48e5-8175-34eb27970f3e gives the date "2026년 9월 14일(월)".
  - **-006 INQR_DVSN=02: WRONG in detail.** N:050d6619 says 02 returns the error message but is then "01 (대출일별) 조회값으로 자동 분기 처리 됨". So 02 is auto-routed to 01, not hard-rejected. The advice to send 01 still stands. Nit: the notice is dated 2026-02-10 in KST.
  - **-006 caveats:** CONFIRMED. P inquire-balance: "최종 D-2일 이후에는 잔고에서 사라집니다." and "조회속도가 느린 API".
  - **-007:** CONFIRMED.
    - P inquire-psbl-order: "PDNO, ORD_UNPR 공란 입력 시, 매수수량 없이 매수금액만 조회됨".
    - ORD_DVSN advice: "반드시" ORD_DVSN:01(시장가)로 지정.
  - **-005:** CONFIRMED.
    - EXCG_ID_DVSN_CD is req=Y, with "※ 모의투자는 KRX만 제공".
    - Old-TR warning: "구TR은 사전고지 없이 막힐 수 있으므로".
    - Auto-mapping: N:7c894616-def7-425a-b62c-210e1a640f20, "기존-신규 TR 자동 매핑 지원".
    - output2 label shift: `tot_ccld_amt` is labelled 매입평균가격 and `pchs_avg_pric` is labelled 추정제비용합계.
  - **-005 sample gap: WRONG.** GH:examples_user/domestic_stock/domestic_stock_functions.py adds the field right after the dict, at lines 4269-4270: `if excg_id_dvsn_cd is not None: params["EXCG_ID_DVSN_CD"] = excg_id_dvsn_cd`. The docstring (line 4173) types it Optional. The sample omits it only when the caller passes None, so E1 must always pass it (the portal marks it req=Y).
  - **-004, -048, -191 fields:** CONFIRMED in the P docs: `psbl_qty`; `tot_asst_amt`, `dncl_amt`, `thdt_rcvb_amt`; `acmga_rt`, `acmga_pct100_aptm_rson`, `rcvb_amt`.
  - **Ledger lag:** CONFIRMED. N:227ac529-ad68-4007-9dd6-320f1d455a26: "체결통보 수신 ≠ 당사 원장 반영 완료".
- **5.2 Overseas table.** CONFIRMED. All 11 rows match the overseas list JSON. The -070 and -071 summaries do mention TWAP/VWAP.
  - Precondition, on the balance, nccs and psamount docs: "해외주식 서비스 신청 후 이용 가능합니다".
  - Mini-stock: "미니스탁 잔고는 해당 API로 확인이 불가".
  - -008 fields: `frcr_drwg_psbl_amt_1` ("출금가능한 외화금액") and `wdrw_psbl_tot_amt`.
  - F:1f4b60d6-017d-4b85-8ce3-d92efd8fc39a: "야간에 실시간 잔고 반영이 안 됩니다". It names JTTT3012R and `dayornight`, and neither is in the current list.
  - -007: "주문번호로 검색 불가능합니다".
- **5.3 Product information.** CONFIRMED. All 5 rows match on path, TR and doc mod; credit-by-company is FHPST04770000 and lendable-by-company is CTSC2702R, both 2026-04-10. The fields are present.
  - N:365bc02b-2b6e-4b3d-98b9-a9f1700a3e84: "거래제어시간 : 08:59 ~ 09:31".
  - N:bb8d1be5-ea48-4f0e-9b13-1b816b5342fd: "변경 시점 : 08.14 (금) 17:00~".
- **5.4 Eligibility.**
  - **APBK1681:** CONFIRMED. N:15abe578-7871-4f6d-80e7-ee1e40ffc0f3: "대상 API : [해외주식] 주문/계좌 > 해외주식 주문" and "해당종목은 기본예탁금 충족한 계좌만 매수주문가능합니다".
  - **APBK1943:** CONFIRMED. N:0778faf1-bf9c-4921-92ef-dc930b8d62af: "최선집행기준 설명서 미교부 고객은 주문이 불가합니다."
  - **Domestic leveraged/inverse ETP rule "not documented anywhere": WRONG in part.** N:15abe578 states that the 1-hour 심화 사전교육 also covers "국내/해외 단일종목 레버리지•인버스ETP" from 2026-05-22. Still undocumented:
    - any API that reports it;
    - any rejection code for a domestic order;
    - the older general domestic leveraged-ETP 사전교육 and 기본예탁금 rule.
  - **Short selling and ELW pre-education:** UNVERIFIED. No official source covers them. This matches my keyword sweep of all notices and FAQs, which found only 15abe578, 842f4450, and FAQ 13719c77 (the 신용/대주 product lists).
  - **Derivatives inquiries:** CONFIRMED in P: `/uapi/domestic-futureoption/v1/trading/inquire-balance` CTFO6118R (mock VTFO6118R) and `/trading/inquire-deposit` CTRP6550R.
  - **ELW orders:** CONFIRMED. F:842f4450-0ff9-4761-9b6a-42843f5611e5: "PDNO(상품코드)에 ELW 종목코드를 입력".
  - **Overseas service not enabled:** the title of F:704eedbe-ed92-4905-a725-d7359768536c is CONFIRMED. Which endpoint returns that error is UNVERIFIED.
  - **Margin field semantics:** UNVERIFIED.
- **5.5 WebSocket fill notices.** CONFIRMED.
  - GH:kis_devlp.yaml: `ops: "ws://ops.koreainvestment.com:21000"` and `vops: "ws://ops.koreainvestment.com:31000"`.
  - P:/tryitout/H0STCNI0 (doc mod 2025-04-30): "체결 통보 응답 결과는 암호화되어 출력됩니다", mock H0STCNI9.
  - P:/tryitout/H0GSCNI0 (doc mod 2025-05-23): mock H0GSCNI9, and "특정 거래소의 체결시간 데이터는 수신되지 않습니다".
  - Scope: N:d0d1a83f, "ID에 연결된 모든 계좌의 체결 통보 수신".
  - Field changes: N:cad37f81-475d-468c-884b-534bc7f29cb6 (CNTG_ISNM, ORD_COND_PRC) and N:3c75de0f-b92f-431c-9f7d-5cb92a7a7721 (CNTG_UNPR12).
  - Final fill: F:4f86cd4d-d3aa-43e5-ad18-027eb3ca6e27, "최종 체결 여부를 직접 알려주는 별도 정보가 제공되지 않습니다".
  - Keep-alive: F:07f312e5-0bf3-4bbe-8179-1ffd7246b392 (100초, PINGPONG).
  - Whether orders can be sent over the socket: UNVERIFIED.
- **5.6 No deposit/withdrawal endpoints.** CONFIRMED. Neither list has a transfer endpoint.

### 6. What distinguishes read-only from trading

- **6.1 HTTP method.** CONFIRMED. F:695cfecd-4379-4ea3-bd24-d23f9400985a: "접근토큰발급과 주문은 POST 방식, 그 외 조회는 GET 방식으로 호출해야". The two lists have 30 GET and 11 POST entries, with no exception.
  - **Wording WRONG:** the note counts `order-resv*` among the POST orders, but some of those paths are GET inquiries:
    - domestic `/trading/order-resv-ccnl` (CTSC0004R) is a GET inquiry;
    - overseas `/trading/order-resv-list` (TTTT3039R / TTTS3014R) is a GET inquiry;
    - overseas `/trading/order-resv-ccnl` (TTTT3017U) is a POST cancel.
  - The same path ending is an inquiry in domestic and an order in overseas, so a path prefix cannot classify either one. Use method plus TR id.
- **6.2 TR id.** CONFIRMED. F:587c7efd-2b76-4f82-9a84-0f924e03459b: "API 호출 시 TR ID 첫 글자는 해당 서버(원장)를 지정합니다."
  - The R/U pattern holds across both lists: every GET real TR ends in R and every POST real TR ends in U. It is still an observation, not a documented rule.
  - F:5c706351-631c-4276-b190-f2b52830a296: "TR 기준으로 원장에 호출을 하기 때문에".
- **6.3 Path is not a separator.** CONFIRMED (from the lists).
- **6.4 Domain is not a separator.** CONFIRMED. F:5c706351: "도메인을 변경해서 사용하시면 TR 기준으로 API 호출되어서 거래가 되는 경우가".
- **6.5 Credentials are identical.** CONFIRMED. P:/uapi/domestic-stock/v1/trading/order-cash uses the same token, appkey and appsecret headers. Its body (CANO, ACNT_PRDT_CD, PDNO, ORD_DVSN, ORD_QTY, ORD_UNPR and others) has no password or PIN field.
- **6.6 The sample rewrites TR ids for mock.** CONFIRMED. GH:examples_user/kis_auth.py lines 422-424.

### 7. Sandbox / paper environment

- **Hosts:** CONFIRMED.
- **Separate credentials:** CONFIRMED. F:5c706351: "앱정보: 모의계좌번호, 모의계좌의 appkey, appsecret".
- **Mock account numbers start with 5:** CONFIRMED (N:747384fe-f047-495c-8548-769c8e6f4c15).
- **EGW00210:** CONFIRMED. ERR: "법인고객의 경우 모의투자를 이용할 수 없습니다."
- **Inquiry coverage in mock:** CONFIRMED (the mock-TR column of both lists).
- **1 REST call/s:** CONFIRMED (see 4.1).
- **Separate operator:** CONFIRMED. N:9858397d-351b-4eda-b6b5-c5ccbcaa64ce: "별도 운영사(연합인포맥스)".
- **KRX only:** CONFIRMED. The title of N:dd2e7e20-51e8-45fd-b65a-24a128f6af34 includes "넥스트레이드 미지원".
- **40910000:** CONFIRMED (N:747384fe).
- **F:ca2cc700 and F:6005110f:** the posts exist, but I did not re-read their wording, so the note's paraphrase is UNVERIFIED.

### 8. Error codes

- **Verbatim match on ERR:** CONFIRMED for EGW00103, EGW00105, EGW00109, EGW00110, EGW00121, EGW00122, EGW00123, EGW00131, EGW00201, EGW00205, EGW00206, EGW00207, EGW00210, EGW00213, EGW00301, EGW00302, EGW00303, EGW00304, OPSP0002, OPSP0008, OPSP8996 and OPSP0011.
- **Not on ERR but CONFIRMED elsewhere:**
  - EGW00133 (N:b9136772);
  - EGW00215 (P inquire-balance);
  - EGW00356 (F:587c7efd);
  - EGW00317 (N:365bc02b);
  - 90070000 and 40910000 (N:747384fe);
  - HTTP 403 (F:695cfecd).
- **Nit:** ERR assigns EGW00213 twice, to "제휴사명(corpname)은 필수 입니다." and to "모의투자 tr이 아닙니다.", so do not key logic on that code alone.
- **F:765ed450-e3a4-4d67-b0f2-16d7d8a52ddc** ("비밀번호 [5회] 오류") exists. Linking it to a password change after key issue is the note's own reading: UNVERIFIED.

### 9. Open questions: status after this pass

1. Inquiry-only key: UNVERIFIED. It remains the central risk, and the guard has to be on the client.
2. Repo guard conflict: CONFIRMED (0.6, 6.1). Add the `order-resv-ccnl` trap: GET in domestic, POST in overseas.
3. Revocation on reissue: UNVERIFIED.
4. tokenP limit wording: CONFIRMED that the official sources conflict (1/min, 1/s and 5 min).
5. What counts toward the 18/s: UNVERIFIED for tokenP and WebSocket traffic. Renewal going straight to the base limit is CONFIRMED (N:c1113824).
6. Eligibility: UNVERIFIED, with the 15abe578 correction from 5.4.
7. Overseas service not enabled: UNVERIFIED.
8. `ACNT_NO` format in fill notices: UNVERIFIED.
9. Missing parameter in the sample: reword it. The sample sends the parameter whenever the caller passes it (5.1).
10. Overseas day/night ledger: UNVERIFIED.
11. KakaoTalk alert as an intrusion signal: UNVERIFIED.
12. Mock coverage gap: CONFIRMED (mock-TR column).

### Corrections to apply to the body above

1. **5.1 / -006:** INQR_DVSN=02 returns an error message and is then auto-routed to 01; it is not rejected (N:050d6619).
2. **5.1 / -005 and open question 9:** the official sample includes EXCG_ID_DVSN_CD conditionally (`domestic_stock_functions.py` lines 4269-4270). It is not omitted.
3. **5.4 and open question 6:** N:15abe578 announces the domestic single-stock leveraged/inverse ETP 심화교육 from 2026-05-22. No domestic API or rejection code is documented for it.
4. **6.1:** `order-resv*` is not all POST. Domestic `order-resv-ccnl` and overseas `order-resv-list` are GET inquiries.
5. **2.7:** add that the approval key is valid for 24 h.
6. **4.6:** the 50/s tier was a one-month programme in December 2025; whether it still runs is unverified.
