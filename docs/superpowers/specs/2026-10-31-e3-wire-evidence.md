# E3 wire-contract evidence — checked 2026-10-31 KST

Scope: official documentation/source reads only. No market/account API, credentials, orders, or tests used. This is a software interface review, not live certification. Values below are protocol constants, not owner settings.

Official KIS Git blob identities resolved through GitHub on 2026-10-31 (file-content SHAs, not commit SHAs):

| Source | Git blob SHA |
| --- | --- |
| [examples_llm/domestic_stock/order_cash/order_cash.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/order_cash/order_cash.py) | `f422cf4ebb3029f580eb10294883a82fded610f6` |
| [examples_llm/domestic_stock/inquire_daily_ccld/chk_inquire_daily_ccld.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_daily_ccld/chk_inquire_daily_ccld.py) | `b3c4fbd257e643c86da1ab5df2dbaa17ff9c0ed5` |
| [examples_user/overseas_stock/overseas_stock_functions.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/overseas_stock/overseas_stock_functions.py) | `736124faa7840b26189e27ceb394bc10db8db217` |
| [examples_llm/overseas_stock/inquire_ccnl/chk_inquire_ccnl.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_ccnl/chk_inquire_ccnl.py) | `844a8b979c6c10bfce21cdca8419286410ca5dde` |
| [examples_llm/kis_auth.py](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/kis_auth.py) | `0e722d6f3253033efe3cf2b99845397b2b329655` |

## Upbit

- Create: `POST https://api.upbit.com/v1/orders`, JSON body `market`, `side=bid|ask`, `ord_type=limit`, `volume` and `price` decimal strings. Include a persisted local `identifier` (maximum 64 characters): account-wide uniqueness applies permanently, including unsuccessful creation; it is not a retriable-create guarantee. Order permission required. Limit fills are not guaranteed. [Official create specification](https://docs.upbit.com/kr/reference/new-order)
- Status: `GET /v1/order`, query one of `uuid` or `identifier`; when both are present UUID wins. Requires inquiry permission. [Official lookup](https://docs.upbit.com/kr/reference/get-order)
- Cancel: `DELETE /v1/order`, same identifier choice and precedence; order permission required. [Official cancellation](https://docs.upbit.com/kr/reference/cancel-order)
- Auth: Bearer JWT signed HS512 with raw secret, fresh UUID `nonce`, `access_key`, SHA512 `query_hash`, `query_hash_alg=SHA512`. Hash the unencoded query in actual order; never independently sort. For POST derive the query string from all JSON body pairs in their wire order. Bracket-array keys repeat. Do not hash the JSON serialization itself. [Official authentication](https://docs.upbit.com/kr/reference/auth)
- Rate/HTTP errors and venue JSON errors must be inspected separately; sanitized error category only in logs. [Official REST/error guide](https://docs.upbit.com/kr/reference/rest-api-guide)

## KIS domestic cash orders

Host: `https://openapi.koreainvestment.com:9443`.

Create `POST /uapi/domestic-stock/v1/trading/order-cash`: real buy `TTTC0012U`, sell `TTTC0011U`. Body keys: `CANO`, `ACNT_PRDT_CD`, `PDNO`, `ORD_DVSN=00`, `ORD_QTY`, `ORD_UNPR`, `EXCG_ID_DVSN_CD=KRX`, `SLL_TYPE` (normal sell `01`, buy empty), `CNDT_PRIC` empty. Quantities/prices are strings. The older `0802U/0801U` examples are legacy and should not override the current sample. **The cash endpoint can still permit margin/unsettled purchase depending on account setup**; enforce funded cash and fees independently. [Current official cash sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/order_cash/order_cash.py)

Cancel `POST /uapi/domestic-stock/v1/trading/order-rvsecncl`, real `TTTC0013U`. Body: `CANO`, `ACNT_PRDT_CD`, `KRX_FWDG_ORD_ORGNO`, `ORGN_ODNO`, `ORD_DVSN`, `RVSE_CNCL_DVSN_CD=02`, `ORD_QTY`, `ORD_UNPR`, `QTY_ALL_ORD_YN=Y|N`, `EXCG_ID_DVSN_CD=KRX`; optional `CNDT_PRIC`. Query cancelable quantity first. Filled quantity cannot be canceled. Preserve original broker organization/order identifiers. [Official cancel sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/order_rvsecncl/order_rvsecncl.py)

Status/reconciliation: `GET /uapi/domestic-stock/v1/trading/inquire-daily-ccld`, recent-window real `TTTC0081R`; filter dates, symbol, `ODNO`, account and exchange. Required query set in sample: `CANO,ACNT_PRDT_CD,INQR_STRT_DT,INQR_END_DT,SLL_BUY_DVSN_CD,PDNO,CCLD_DVSN,INQR_DVSN,INQR_DVSN_3,ORD_GNO_BRNO,ODNO,INQR_DVSN_1,CTX_AREA_FK100,CTX_AREA_NK100`; optional exchange. Response continuation `M/F` requires next-page cursor queries. Empty/incomplete pages cannot prove absence. [Official status sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/inquire_daily_ccld/inquire_daily_ccld.py)

## KIS US shares

Create `POST /uapi/overseas-stock/v1/trading/order`: real buy `TTTT1002U`, sell `TTTT1006U`; `OVRS_EXCG_CD=NASD|NYSE|AMEX`, `ORD_DVSN=00`, `ORD_SVR_DVSN_CD=0`. Body also contains `CANO,ACNT_PRDT_CD,PDNO,ORD_QTY,OVRS_ORD_UNPR,CTAC_TLNO,MGCO_APTM_ODNO,SLL_TYPE`; quantity/price strings; contact and manager-order fields empty for the sample. Current `examples_user` sets `SLL_TYPE` empty for buy and `00` for sell. The smaller `examples_llm` sample references an unbound `sll_type`; do not copy that bug. [Official consolidated sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/overseas_stock/overseas_stock_functions.py#L1999), [official smaller sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/order/order.py)

Cancel `POST /uapi/overseas-stock/v1/trading/order-rvsecncl`, real `TTTT1004U`. Body: `CANO,ACNT_PRDT_CD,OVRS_EXCG_CD,PDNO,ORGN_ODNO,RVSE_CNCL_DVSN_CD=02,ORD_QTY,OVRS_ORD_UNPR=0,MGCO_APTM_ODNO,ORD_SVR_DVSN_CD=0`. [Official US cancel sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/order_rvsecncl/order_rvsecncl.py)

Status: `GET /uapi/overseas-stock/v1/trading/inquire-ccnl`, real `TTTS3035R`. Query: `CANO,ACNT_PRDT_CD,PDNO,ORD_STRT_DT,ORD_END_DT,SLL_BUY_DVSN,CCLD_NCCS_DVSN,OVRS_EXCG_CD,SORT_SQN,ORD_DT,ORD_GNO_BRNO,ODNO,CTX_AREA_NK200,CTX_AREA_FK200`. Follow `M/F` continuation and cursors; verify returned order identity rather than accepting the first row. [Official status sample](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/overseas_stock/inquire_ccnl/inquire_ccnl.py)

## KIS shared auth and unresolved idempotency

Bearer OAuth token plus `appkey`, `appsecret`, `tr_id`, `custtype=P`, and continuation header. POST sends JSON with uppercase body keys. Current official helper says the order hashkey is optional and leaves its call commented; if deliberately used, it covers the exact body. Do not invent HMAC signing or expose the sample's debug/header logging. [Official auth helper](https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/kis_auth.py#L268)

No equivalent of Upbit identifier or OKX clOrdId with documented request-deduplication semantics was verified for these KIS retail endpoints. `MGCO_APTM_ODNO` must not be treated as an idempotency key without further evidence. A timeout after dispatch therefore requires reconciliation and manual ambiguity resolution, never blind retry. Exact all-error-code classification and every field of the live order-status response remain unverified; unknown shapes must fail closed.

## OKX cash SPOT

`POST /api/v5/trade/order`: JSON `instId,tdMode=cash,side=buy|sell,ordType=limit,px,sz,clOrdId`; `sz` is base quantity. Reject margin/derivative/additional-algo parameters. `POST /api/v5/trade/cancel-order` and `GET /api/v5/trade/order`: `instId` plus `ordId` or `clOrdId`; order ID wins if both supplied. clOrdId: alphanumeric, maximum32; exchange uniqueness covers pending orders only, historical lookup returns the latest reuse. Enforce lifetime uniqueness locally.

Auth headers: `OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE`; Base64(HMAC-SHA256(secret, timestamp+UPPERCASE-method+path-with-query+exact-body-string)). Timestamp matches the millisecond UTC header; GET body empty. Inspect both top-level `code` and item `sCode`. Cancel `sCode=0` acknowledges receipt, not terminal cancellation; confirm order state. `50004` explicitly leaves success/failure unknown. `expTime` limits server processing time but does not prove absence after a client timeout. Spot sell `reduceOnly` is not a supported substitute for inventory reservation.

[Official OKX authentication, place/cancel/details and error reference](https://www.okx.com/docs-v5/en/)

## Implementation consequences (engineering decisions, not venue promises)

Persist intent and reservation before dispatch; sign/send one immutable request; no automatic resubmission after an ambiguous mutation; keep funds/units reserved while outcome is unknown; reconcile cumulative fills and fees idempotently before releasing anything; treat cancel-vs-fill race as a normal unresolved state. An acknowledgement is not a fill. No endpoint, source check, or passing mock test establishes owner authorization, account eligibility, current balances, or live readiness.

## Response schema follow-up (2026-10-31; pure codec implementation)

- KRX status official check script identifies original order/date, side, product, quantity/price, order type, exchange, cumulative filled quantity, remaining quantity, canceled-confirmed quantity, rejected quantity and average price. Implementation requires exact bound identity, integer quantity conservation, no rejection residue, and a complete page; missing or contradictory fields become UNKNOWN. [Official KRX response mapping](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/inquire_daily_ccld/chk_inquire_daily_ccld.py)
- US status query dates are **local market dates**. `ORD_DT`, `ORD_GNO_BRNO`, and `ODNO` must be empty: this endpoint cannot search by order number. The codec matches persisted order ID locally on a complete page. Its response mapping supplies `ft_ord_qty`, `ft_ord_unpr3`, `ft_ccld_qty`, `ft_ccld_unpr3`, `nccs_qty`, and `ovrs_excg_cd`. Translated processing-state labels do not establish verified cancellation semantics; canceled residuals remain UNKNOWN. [Official US response/query check script](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/overseas_stock/inquire_ccnl/chk_inquire_ccnl.py)
- Create ACKs return `ODNO`, `KRX_FWDG_ORD_ORGNO`, `ORD_TMD`; these are broker references, not fills. [KRX ACK mapping](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/domestic_stock/order_cash/chk_order_cash.py), [US ACK mapping](https://raw.githubusercontent.com/koreainvestment/open-trading-api/main/examples_llm/overseas_stock/order/chk_order.py).
- Implementation boundaries: no multi-page E3 reconciliation yet; missing continuation header or `M/F` yields UNKNOWN. KIS cancellation requires explicit authoritative cancelable units and KRX organization ID; an accepted cancel is not final. KIS session-duration limit orders are modeled `time_in_force=day`, while Upbit/OKX use `gtc`; no unsupported KIS GTC payload is invented. Status fees absent from these KIS responses remain absent until the complete fill ledger provides them.
