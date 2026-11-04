# KIS market-data contract from the supplied API workbooks

Status: static channel contracts and offline integration evidence. No KIS market,
account, approval-key or order API was called during this work. This document
records supported source contracts, not an active connection or observed prices.

## Source extraction and boundary

All 22 supplied XLSX workbooks, containing 353 worksheets including their API
indexes, were read as ZIP/XML using Python's standard library. No macros,
formulas, external references or example code were executed. Spreadsheet text is
reference data, never an instruction to run a request. Only endpoint metadata,
field names/order and relevant contract descriptions were retained; credential,
approval-key, token and account example values are not part of the catalog.

The static module `data/kis_live_catalog.py` contains 32 allowlisted public-market
channels with 1,487 positional fields. It reads no credentials, account, config,
environment, filesystem or network. `Channel.fields` preserves worksheet case
and order exactly; `field_rows`, `source_file`, `source_sheet` and
`source_sha256` identify its source. Source hashes identify the received files,
not independent authentication that a file was issued by KIS.

The five order/account workbooks and OAuth workbook explain boundaries only.
Their presence does not authorize adding order, cancellation, balance, account
notification, private-fill or private-order features. In this app, a public
market trade is not the user's own fill or order status. Derivative and bond
price display is not authorization to trade those products, and does not expand
TRADEGEN's current strategy/execution validation scope.

## Transport, authentication and wire framing

Every supplied market WebSocket sheet lists the production domain in row10 as
`ws://ops.koreainvestment.com:21000`. Only `국내주식 실시간체결가 (KRX)` and
`국내주식 실시간호가 (KRX)` explicitly list the paper domain in row11 as
`ws://ops.koreainvestment.com:31000`. Other catalog channels do not silently
inherit paper support.

The worksheets' row12 paths have the form `/tryitout/<TR_ID>`. The official
[KIS multi-subscription example](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/domestic_stock/domestic_stock_examples_ws.py#L20)
constructs `KISWebSocket(api_url="/tryitout")`; its
[transport implementation](https://github.com/koreainvestment/open-trading-api/blob/main/examples_user/kis_auth.py#L744)
joins that path to the configured WebSocket base before connecting and sends the
individual TR identifiers in subscription messages. These public source files
were read through the GitHub connector; they were not executed. Accordingly the
shared endpoints recorded by the catalog are:

- Production: `ws://ops.koreainvestment.com:21000/tryitout`.
- Paper: `ws://ops.koreainvestment.com:31000/tryitout`, for supported channels.

These are cleartext WebSocket URLs. No uploaded source establishes a `wss://`
URL, alternate secure port, or TLS upgrade. Never invent one or silently connect
by changing the scheme. A deployment must explicitly handle the documented
cleartext transport and its exposure of the approval key; a network permission
or authenticated API key does not by itself establish secure transport. The
catalog neither connects nor approves that deployment decision.

`OAuth인증.xlsx`, sheet `실시간 (웹소켓) 접속키 발급`, rows9–12 documents
POST `/oauth2/Approval` with exact capitalization. The production HTTPS base is
`https://openapi.koreainvestment.com:9443` and the paper base is
`https://openapivts.koreainvestment.com:29443`. Rows17–22 specify the optional
`content-type` header; request body `grant_type`, `appkey`, `secretkey`; and
response `approval_key`. The grant is `client_credentials`. This is separate
from account orders and the ordinary REST access token. Do not log these values,
persist them in exported snapshots, or ask the user to paste them into chat.

Public subscription tables, rows17–22, define `approval_key`, `custtype`,
`tr_type`, `content-type`, and body input `tr_id`/`tr_key`. Registration uses
`tr_type="1"`, deregistration `"2"`; user type is an explicit deployment choice.
The worksheet HTTP Method cell saying POST is not an authorization for an order
POST and is not a replacement for the WebSocket message protocol.

The documented market frame is `encryption_flag|TR_ID|record_count|payload`,
with fields separated by `^`. Exact record count times the channel's field
count must match. JSON subscription/control acknowledgments are not price
frames. Public-market parsing must reject encrypted/account-notification frames
rather than importing private-notification decryptors. A successful subscription
acknowledgment alone does not prove any fresh quote has arrived.

## Enabled static schemas

Each row below cites the exact workbook/sheet. TR metadata is at rows6/12;
request key guidance is row22; the listed response rows contain the complete
positional layout. Catalog inclusion does not mean every channel already has a
fully validated normalized display: source clocks, scale and entitlement can
remain unresolved. Lowercase fields are preserved where the source uses them.

| Workbook | Sheet | TR_ID | Response rows | Fields |
|---|---|---|---|---:|
| [해외주식] 실시간시세.xlsx | 해외주식 실시간호가 | `HDFSASP0` | 24–94 | 71 |
| [해외주식] 실시간시세.xlsx | 해외주식 지연호가(아시아) | `HDFSASP1` | 24–40 | 17 |
| [해외주식] 실시간시세.xlsx | 해외주식 실시간지연체결가 | `HDFSCNT0` | 24–49 | 26 |
| [해외선물옵션]실시간시세.xlsx | 해외선물옵션 실시간체결가 | `HDFFF020` | 24–48 | 25 |
| [해외선물옵션]실시간시세.xlsx | 해외선물옵션 실시간호가 | `HDFFF010` | 24–58 | 35 |
| [장내채권] 실시간시세.xlsx | 일반채권 실시간체결가 | `H0BJCNT0` | 24–42 | 19 |
| [국내주식] 실시간시세.xlsx | 국내주식 실시간체결가 (KRX) | `H0STCNT0` | 24–70 | 47 |
| [국내주식] 실시간시세.xlsx | 국내주식 실시간호가 (KRX) | `H0STASP0` | 24–86 | 63 |
| [국내주식] 실시간시세.xlsx | 국내주식 시간외 실시간호가 (KRX) | `H0STOAA0` | 24–77 | 54 |
| [국내주식] 실시간시세.xlsx | 국내주식 시간외 실시간체결가 (KRX) | `H0STOUP0` | 24–66 | 43 |
| [국내주식] 실시간시세.xlsx | 국내지수 실시간체결 | `H0UPCNT0` | 24–53 | 30 |
| [국내주식] 실시간시세.xlsx | ELW 실시간호가 | `H0EWASP0` | 24–96 | 73 |
| [국내주식] 실시간시세.xlsx | ELW 실시간체결가 | `H0EWCNT0` | 24–86 | 63 |
| [국내주식] 실시간시세.xlsx | 국내ETF NAV추이 | `H0STNAV0` | 24–31 | 8 |
| [국내주식] 실시간시세.xlsx | 국내주식 실시간체결가 (통합) | `H0UNCNT0` | 24–70 | 47 |
| [국내주식] 실시간시세.xlsx | 국내주식 실시간호가 (통합) | `H0UNASP0` | 24–89 | 66 |
| [국내주식] 실시간시세.xlsx | 국내주식 실시간체결가 (NXT) | `H0NXCNT0` | 24–70 | 47 |
| [국내주식] 실시간시세.xlsx | 국내주식 실시간호가 (NXT) | `H0NXASP0` | 24–85 | 62 |
| [국내선물옵션] 실시간시세.xlsx | 지수선물 실시간호가 | `H0IFASP0` | 24–61 | 38 |
| [국내선물옵션] 실시간시세.xlsx | 지수선물 실시간체결가 | `H0IFCNT0` | 24–73 | 50 |
| [국내선물옵션] 실시간시세.xlsx | 지수옵션 실시간호가 | `H0IOASP0` | 24–61 | 38 |
| [국내선물옵션] 실시간시세.xlsx | 지수옵션  실시간체결가 | `H0IOCNT0` | 24–81 | 58 |
| [국내선물옵션] 실시간시세.xlsx | 상품선물 실시간호가 | `H0CFASP0` | 24–61 | 38 |
| [국내선물옵션] 실시간시세.xlsx | 상품선물 실시간체결가 | `H0CFCNT0` | 24–73 | 50 |
| [국내선물옵션] 실시간시세.xlsx | 주식선물 실시간호가 | `H0ZFASP0` | 24–91 | 68 |
| [국내선물옵션] 실시간시세.xlsx | 주식선물 실시간체결가 | `H0ZFCNT0` | 24–72 | 49 |
| [국내선물옵션] 실시간시세.xlsx | 주식옵션 실시간호가 | `H0ZOASP0` | 24–91 | 68 |
| [국내선물옵션] 실시간시세.xlsx | 주식옵션 실시간체결가 | `H0ZOCNT0` | 24–76 | 53 |
| [국내선물옵션] 실시간시세.xlsx | KRX야간옵션 실시간호가 | `H0EUASP0` | 24–61 | 38 |
| [국내선물옵션] 실시간시세.xlsx | KRX야간옵션 실시간체결가 | `H0EUCNT0` | 24–79 | 56 |
| [국내선물옵션] 실시간시세.xlsx | KRX야간선물 실시간호가 | `H0MFASP0` | 24–61 | 38 |
| [국내선물옵션] 실시간시세.xlsx | KRX야간선물 실시간종목체결 | `H0MFCNT0` | 24–72 | 49 |

## Price, volume, freshness and entitlement semantics

- KRX, consolidated and NXT stock trade schemas each have47 fields, but their
  field names are not interchangeable. Their book schemas have63,66 and62
  fields respectively. Never pad, truncate, rename by position or assume one
  older shared layout. Book normalization maps only actual `ASKP`/`BIDP` depth,
  excluding predicted `ANTC_*` values and midpoint aggregates.
- `HOUR_CLS_CODE` identifies indicative states A/B/C/D in the domestic stock
  source tables (`국내주식 실시간체결가 (KRX)` row67 and book row26). Preserve
  these states instead of presenting them as executable continuous-market
  quotes. Trading-halt and session fields remain additional source information;
  neither a nonzero price nor a channel name proves that orders can execute.
  Only the KRX trade/book sheets explicitly define this code set and regular
  value `0`; other sheets leave its description blank. Their catalog state
  values therefore remain unknown. Blank or unrecognized codes never become
  a regular session by default.
- Individual public trade size and cumulative volume are separate. Domestic
  `CNTG_VOL`, overseas-equity `EVOL`, derivative `LAST_CNQN` and overseas-
  derivative `LAST_QNTT` are distinct from `ACML_VOL`, `TVOL` or `VOL`. Do not
  treat an accumulated counter as each trade's size or compute indicators from
  duplicated/replayed frames without explicit handling.
- Overseas-equity fields `KYMD`/`KHMS` provide the documented Korean date/time;
  preserve `XYMD`/`XHMS` separately as local-market time. Some domestic books
  contain only a clock time, and ETF NAV contains neither date nor clock time.
  A receive timestamp is not an exchange timestamp. Date reconstruction,
  overnight sessions, clock uncertainty and stale data need explicit handling;
  absence of a source clock cannot be silently rewritten as fresh exchange time.
  There are additional unresolved length declarations: `HDFSCNT0` calls `KYMD`
  a Korean date but gives length6 in row30 (the book sheets give8); index
  future/option `BSOP_HOUR` length is16 in row25, commodity-future length9,
  and other domestic derivative lengths6. These may be upper bounds, but the
  tables do not establish alternate formats. Preserve strict reviewed date/time
  parsing and report an unsupported format instead of trimming or guessing.
- `HDFSASP0`, sheet overview row14 and key row22: US free books cover the Nasdaq
  market-center feed, not a guaranteed consolidated national best bid/offer.
  Use `D` plus NAS/NYS/AMS for the documented US free mode; US daytime uses
  `R` plus BAQ/BAY/BAA. Asian real-time subscriptions use `R` and require the
  applicable market-data entitlement. Free and paid coverage can differ.
- `HDFSASP1`, overview row14: Asian free books are15-minute delayed.
  `HDFSCNT0`, rows14/22: US free trades are documented as zero-minute delayed;
  Asian `D` keys are15-minute delayed, while entitled `R` subscriptions can
  receive real-time data. Display the mode and delay; a recently received
  delayed tick is not a current quote. The catalog's
  `subscription_delay_seconds()` encodes the documented minimum delay by key,
  not actual freshness or entitlement verification.
- `HDFFF010`/`HDFFF020`, overview row14: overseas future/option prices need the
  instrument master's `sCalcDesz` calculation exponent. Neither ordinary decimal
  parsing nor a guessed number of decimal places replaces it. CME/SGX require
  the documented paid entitlement and synchronization. `RECV_TIME` is named in
  response rows26/32, but its timezone and the book's12-character time layout
  are not resolved by these tables. Catalog metadata therefore marks
  `normalization="requires_master_scale"` and leaves timezone unknown. Raw data
  may be retained for diagnosis; normalized prices/freshness require an explicit
  reviewed scale/time contract before use.
- Domestic derivative book overviews note a0.2-second filtering option. These
  streams do not prove every exchange event was delivered. Bond prices/yields,
  option Greeks and ETF NAV have instrument-specific units; do not relabel them
  as interchangeable stock trade prices, guaranteed fills or realized account P&L.

Subscription-key regexes are conservative local syntax filters, not instrument
masters or entitlement checks. The catalog preserves exact exchange prefixes
and leading zeroes, rejects whitespace/separators/URLs/non-ASCII input, and never
normalizes an arbitrary string into a valid instrument. Unsupported symbols
require an explicit contract extension, not bypassing the allowlist.

## Quarantined and excluded contracts

Optional paired display uses only explicitly pinned trade/book companions:
KRX `H0STCNT0`/`H0STASP0`, consolidated `H0UNCNT0`/`H0UNASP0`, NXT
`H0NXCNT0`/`H0NXASP0`, and overseas `HDFSCNT0`/`HDFSASP0`. Both channels
must accept the exact same key and environment, and both must be supported by
the current backend. No key rewriting, venue mixing or atomic timing is implied.
In particular, an Asian delayed `D` trade key cannot subscribe to the real-time
overseas book channel, so `companion_channel()` returns no peer. Unpaired
contracts remain single-channel subscriptions with unavailable panels labeled.

`QUARANTINED` records unresolved public contracts outside the allowed mapping:

- `[장내채권] 실시간시세.xlsx`, `일반채권 실시간호가`: rows6 and21 name
  `H0BJCNT0`, while row12 names `/tryitout/H0BJASP0`. Row19 also duplicates
  `custtype` where registration type is described. The trade channel's19-field
  layout must not be reused for this34-field book. `H0BJASP0` remains disabled
  pending authoritative resolution.
- The same workbook's `채권지수 실시간체결가` row22 repeats a bond ISIN key
  example, whereas rows24 onward start with index `NMIX_ID`. Its key contract
  remains unresolved; `H0BICNT0` is not enabled by guessing an index code.
- Domestic KRX/consolidated/NXT VI sheets omit or confuse TR/key metadata.
  `H0STVIC0`, `H0UNVIC0`, and `H0NXVIC0` remain outside subscriptions.
- Predicted-auction, member-flow, program-flow and market-status channels are
  documented but not part of this initial32-channel schema set. They must not
  be inferred by a matching prefix or passed through unknown-frame handling.

Every private notification remains excluded, including `H0STCNI0/9`,
`H0GSCNI0/9`, `H0IFCNI0/9`, `H0EUCNI0`, `H0MFCNI0`, `HDFFF1C0`, and
`HDFFF2C0`. The domestic night-option notification sheet itself contains another
TR/path discrepancy; its private nature already excludes it regardless of how
that discrepancy is resolved. No CNI/notice wildcard is permitted.

## REST quotation references, without new execution permissions

The other workbooks also document snapshots, charts and indicators useful for
future display integration. The representative GET contracts below are
references only: this catalog adds no REST caller, E1 execution endpoint,
account lookup or order route. Each citation uses the named sheet's row6 for
TR_ID, row9 for method and row12 for path. Existing client behavior and any
future caller need separate review; uploading a workbook is not proof a field
was observed successfully in the current account.

| Workbook / sheet | TR_ID | Documented GET path |
|---|---|---|
| [해외주식] 시세분석.xlsx / 해외주식 거래량순위 | `HHDFS76310010` | `/uapi/overseas-stock/v1/ranking/trade-vol` |
| [해외주식] 기본시세.xlsx / 해외주식 현재가상세 | `HHDFS76200200` | `/uapi/overseas-price/v1/quotations/price-detail` |
| [해외주식] 기본시세.xlsx / 해외주식 현재가 호가 | `HHDFS76200100` | `/uapi/overseas-price/v1/quotations/inquire-asking-price` |
| [해외주식] 기본시세.xlsx / 해외주식분봉조회 | `HHDFS76950200` | `/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice` |
| [해외선물옵션] 기본시세.xlsx / 해외선물종목현재가 | `HHDFC55010000` | `/uapi/overseas-futureoption/v1/quotations/inquire-price` |
| [해외선물옵션] 기본시세.xlsx / 해외옵션종목현재가 | `HHDFO55010000` | `/uapi/overseas-futureoption/v1/quotations/opt-price` |
| [장내채권] 기본시세.xlsx / 장내채권현재가(호가) | `FHKBJ773401C0` | `/uapi/domestic-bond/v1/quotations/inquire-asking-price` |
| [장내채권] 기본시세.xlsx / 장내채권현재가(시세) | `FHKBJ773400C0` | `/uapi/domestic-bond/v1/quotations/inquire-price` |
| [국내주식] 종목정보.xlsx / 주식기본조회 | `CTPF1002R` | `/uapi/domestic-stock/v1/quotations/search-stock-info` |
| [국내주식] 업종_기타.xlsx / 국내업종 현재지수 | `FHPUP02100000` | `/uapi/domestic-stock/v1/quotations/inquire-index-price` |
| [국내주식] 업종_기타.xlsx / 금리 종합(국내채권_금리) | `(구) FHPST07020000 (신)HHPST070200C0` | `/uapi/domestic-stock/v1/quotations/comp-interest` |
| [국내주식] 순위분석.xlsx / 거래량순위 | `FHPST01710000` | `/uapi/domestic-stock/v1/quotations/volume-rank` |
| [국내주식] 기본시세.xlsx / 주식현재가 시세 | `FHKST01010100` | `/uapi/domestic-stock/v1/quotations/inquire-price` |
| [국내주식] 기본시세.xlsx / 주식현재가 호가_예상체결 | `FHKST01010200` | `/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn` |
| [국내주식] 기본시세.xlsx / 주식당일분봉조회 | `FHKST03010200` | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` |
| [국내주식] 기본시세.xlsx / ETF_ETN 현재가 | `FHPST02400000` | `/uapi/etfetn/v1/quotations/inquire-price` |
| [국내주식] ELW 시세.xlsx / ELW 현재가 시세 | `FHKEW15010000` | `/uapi/domestic-stock/v1/quotations/inquire-elw-price` |
| [국내선물옵션] 기본시세.xlsx / 선물옵션 시세 | `FHMIF10000000` | `/uapi/domestic-futureoption/v1/quotations/inquire-price` |
| [국내선물옵션] 기본시세.xlsx / 선물옵션 시세호가 | `FHMIF10010000` | `/uapi/domestic-futureoption/v1/quotations/inquire-asking-price` |

The interest-rate sheet explicitly contains both an old and a new TR identifier;
this reference preserves that distinction instead of silently choosing one.
The remaining analysis/ranking/instrument sheets were inventoried, not converted
into automatic requests. Screens that depend on personal watchlists or account
identifiers remain outside public market-data subscription scope.

## Input inventory

Hashes bind this extraction to the supplied workbook bytes. Sheet counts include
`API 목록`. Order/account and authentication files are boundary references; their
example data is not copied into source code or documentation.

| Workbook | Sheets | SHA-256 |
|---|---:|---|
| [해외주식] 주문_계좌.xlsx | 19 | `209af25e5820fc39ed8d1f95a2eb81b6983113c2e1ea3d6990c9bb74e2706619` |
| OAuth인증.xlsx | 4 | `b7c927dd77f420a55f2baa113141344d104a294610d888250318264eb5cd6335` |
| [해외주식] 실시간시세.xlsx | 5 | `983ad3d1d86f48f94fdf4513d44f1570a964723352d90d221aa6f8796f7315b8` |
| [해외주식] 시세분석.xlsx | 16 | `7f70d14cec14d7d0b9794efa4aa4cdb546cb948eb5dfa452baf75a25673ab77d` |
| [해외선물옵션]실시간시세.xlsx | 5 | `2c593fc2529da3144576c93218fc7c7761e24e63a5cb949590296b900a565384` |
| [해외주식] 기본시세.xlsx | 15 | `d67e869f8f28641cc31abdc61ce8451f6b0b0d32e352174053795ee1b59119cb` |
| [해외선물옵션] 기본시세.xlsx | 21 | `b83db21fa2a933ce1e00f6090f6dbd1940aff930de654ac5591ecafacc3b4c61` |
| [장내채권] 주문_계좌.xlsx | 8 | `2eca10fd3bc6fb3b3ff854387a2770fa18ce5c20a9a32c157baad8e9ca8c3adf` |
| [해외선물옵션] 주문_계좌.xlsx | 12 | `25023f9e4546281127ac580b9ab86a25ca93bb20a387ad7c0c384376931b31c4` |
| [장내채권] 기본시세.xlsx | 9 | `43c0bc8854784ebfe8adcf99fc3e06a79fe756b605bd8d876156078dc78b61f0` |
| [장내채권] 실시간시세.xlsx | 4 | `711bfc523159d8b5cb6a73212a3147f7605e441e75a1edead90629f3435f30bc` |
| [국내주식] 종목정보.xlsx | 20 | `b392f88dd06a569aff6d2b90360421404025436b51103e799212f8f04682438a` |
| [국내주식] 주문_계좌.xlsx | 24 | `63f289ecaa421f98df3a7b24b1bb90afe953b3490ef0380e01c5c33350ce7534` |
| [국내주식] 업종_기타.xlsx | 15 | `0da629ca3f3e87e9614ae2592a0c5bcbbab562b134328943b48fb4e65d39caf0` |
| [국내주식] 시세분석.xlsx | 30 | `31bd3b44b319690838361a6c55aeaccd87307e8710704ec38ab113206d35a755` |
| [국내주식] 순위분석.xlsx | 23 | `8d8d3c7cca49e8ce7410f642e34a60283ffff8d77423881452199a46c2f7567d` |
| [국내주식] 실시간시세.xlsx | 33 | `181eb9977ae96563d451f9632ea83bec6ef5b949938b9358a08cdf1faf240018` |
| [국내주식] 기본시세.xlsx | 23 | `e8073d49eb89edc283e053a60bd36aeb51260fec77ce3b52aa54df7090114afa` |
| [국내선물옵션] 실시간시세.xlsx | 21 | `54cdec4acbf7139a1c59af0a7ac563bc4ac7a49896377c105009d6d1530208a8` |
| [국내주식] ELW 시세.xlsx | 23 | `27df2330f23eacca11b6b6d62adcd0de46c7694a190711f4475d3ceee45782dd` |
| [국내선물옵션] 주문_계좌.xlsx | 16 | `6df5955129ce23176c193b8414038340ffa83b4e57c2831179e25b54a9d27a3a` |
| [국내선물옵션] 기본시세.xlsx | 7 | `55f3169c2cbaedf09c7ead1f5f9293818c4d8e9ea758174adc7c28b0a6e1e662` |

## Verification and operational meaning

`tests/kis_live_catalog.py` defines offline checks for exact positional schemas,
market/field mappings, immutable records, public/private separation, key syntax,
per-subscription delay, paper support, known source conflicts and absence of
network/config/execution imports. No test or real API call was run as part of
this extraction task; integration validation is recorded separately.

The catalog supplies metadata to the feed backend and app. The UI must distinguish
available channel documentation, a started session, subscription acknowledgment,
received data, source freshness, delayed data and disconnection. Unavailable
metrics remain unavailable. Live connection, credentials, instrument/entitlement
validation and cleartext-network handling are separate deployment facts. Display
feeds do not become prospective strategy evidence merely by appearing on screen.

This is engineering documentation, not legal, tax or investment advice; the
author is not a licensed adviser.
