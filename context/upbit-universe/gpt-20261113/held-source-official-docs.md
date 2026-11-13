# Held-source authority: fresh official Upbit documentation check

Verification completed **2026-11-13 at 08:44 UTC** using the available web documentation tool. This supplements
[the source evidence table](held-source-contract-evidence.md); it does not change policy or approve a source.
Only documentation pages on `docs.upbit.com` and search results restricted to that domain were read.
No exchange/data API endpoint, WebSocket connection, credential, account/home, signer or order was used.

**Result:** the checked documents describe useful event fields, history queries and connection management,
and explicitly document silence and initial delivery delay. They do **not establish the combined contract
needed by TRADEGEN for lossless, commonly ordered account/mark intervals with a final coverage frontier**.
Here “unspecified” means no applicable guarantee was found in these checked pages; it does not mean that
the behavior is impossible or that Upbit has expressly denied every such guarantee.

## Directly checked documentation

Every link below was checked on the date above. Short quotations preserve the Korean original. Field names
and prose are documentation, not observations of a running exchange feed.

| Official document | Explicit statement / short excerpt | What this supports | What it does not establish |
| --- | --- | --- | --- |
| [Private MyOrder](https://docs.upbit.com/kr/reference/websocket-myorder) | “주문 또는 체결이 없으면 데이터가 전송되지 않습니다.” `trade_fee`: “체결 시 발생한 수수료 (state:trade가 아닐 경우 null)” | Event-driven private order/fill notifications; documented fill ID, fee, volume and timestamps. Omitting `codes` requests all markets in scope. | Silence cannot distinguish an inactive account from an unproven missing-event interval. No documented replay cursor, final coverage watermark, maximum delivery delay, cross-stream order, or fee-correction/finality contract was found here. Fee currency is not explicitly identified by the cited field description. |
| [Private MyAsset](https://docs.upbit.com/kr/reference/websocket-myasset) | “자산 변동이 없으면 데이터가 전송되지 않습니다.” “초기 수분 동안 데이터 수신이 지연될 수 있습니다.” | Both silence without asset changes and a possible minutes-long delay on first subscription are documented limitations. Asset UUID and asset/message timestamps are provided. | The example of later reconnection receiving updates does not specify replay of earlier changes, an atomic initial balance, a maximum late-event bound, or a no-event certificate. Its initial delay cannot be treated as meeting the current 30-second evidence budget. |
| [Public WebSocket Trade](https://docs.upbit.com/kr/reference/websocket-trade) | `sequential_id`: “체결 번호(Unique)” | A public trade record includes price/volume, trade and message timestamps, a unique trade identifier, and snapshot/realtime labels. Snapshot-only and realtime-only request switches are documented. | “Unique” is not a statement that values are consecutive, ordered across markets, shared with private fills, or usable to detect every omission. No replay cursor, delivery finality or complete-stream watermark was found in this page. Best bid/ask fields on a trade do not describe every intervening book change. |
| [Public WebSocket Orderbook](https://docs.upbit.com/kr/reference/websocket-orderbook) | “지원하지 않는 단위를 지정하면 데이터가 수신되지 않을 수 있습니다.” | Snapshot/realtime book records, timestamp, aggregation level, and 1/5/15/30-level depth selection. Unsupported aggregation can itself cause no data. | No source event sequence, delta-to-snapshot correspondence, historical replay cursor, all-change delivery bound, or private-fill common order is specified in the displayed subscription schema. A book snapshot is not a certificate of the entire intervening path. |
| [Closed orders](https://docs.upbit.com/kr/reference/list-closed-orders) | `start_time`: “지정한 시각으로부터 \"end_time\"까지 생성된 주문을 조회합니다.” | Queries cover **order creation time**, permit a maximum seven-day query window and at most 1,000 results, and support ascending/descending order. They include done/canceled orders. | A creation-time end is not an execution-finality watermark. This page does not specify total historical retention, a consistent snapshot across reads, same-time inclusion/tie rules, or a maximum delay before a newly terminal order becomes visible. A short/empty result is not independent proof of no omitted fills. |
| [WebSocket guide](https://docs.upbit.com/kr/reference/websocket-guide) | “클라이언트는 서버로 주기적으로 PING Frame을 보내 자동 연결 종료를 방지하고 연결 상태를 확인할 수 있습니다.” | PING/PONG provides connection liveness; the guide describes a 120-second idle timeout and optional `UP` status messages every ten seconds. Snapshot means a one-time current observation. | Liveness/status does not attest application-event coverage or finality. The guide separates public and private channels; it supplies no common ordering rule across them. A request ticket identifies the request, not a venue sequence. |
| [WebSocket best practice](https://docs.upbit.com/kr/docs/websocket-best-practice) | “연결이 해제된 경우 적절한 연결 재시도를 통해 데이터 누락을 방지할 수 있습니다.” | This is a positive operational recommendation to reconnect, which must be retained rather than claiming documentation says nothing about omission prevention. The examples implement reconnect/ping handling. | The sentence does not define a replay range, recovery cursor, acknowledgement, retention/delivery guarantee or proof that a particular gap was filled. Promoting it to a gap-free interval certificate would add an unstated premise. |
| [Public REST pair trades](https://docs.upbit.com/kr/reference/list-pair-trades) | `cursor`: “Pagination을 위한 조회 범위 지정용 커서.” | The direct page documents backwards pagination using a returned `sequential_id`, maximum 500 results, UTC date selection, and up to seven days of public trade history. This is a real documented retrieval capability. | It covers public pair trades, not every book change, private fee/asset event or their shared order. It supplies no final source frontier or snapshot-to-live barrier. Its response-schema ordering caveat is available through indexed official documentation, with the qualification below. |
| [Public REST orderbook](https://docs.upbit.com/kr/reference/list-orderbooks) | “지정한 종목들의 실시간 호가(Orderbook) 정보를 조회합니다.” | Current book information with depth/aggregation controls; unsupported aggregation returns an empty array. | The query is a current observation, with no documented historical replay or event-coverage cursor. An empty book result is not evidence of an event-free account interval. |

## Ordering wording conflict and retrieval qualification

An official **2018-07-20 changelog**, with changes stated to apply from 2018-08-03, describes `sequential_id`
as “체결의 유일성(Uniqueness) 및 순서 보장을 위한 필드”. That is affirmative historical wording and must not
be omitted. Its paragraph concerns the **REST Trade API**, not a unified public/private event ledger.
[Original changelog](https://docs.upbit.com/kr/changelog/%EC%95%88%EB%85%95%ED%95%98%EC%84%B8%EC%9A%94).

The search service returned the full official **v1.6.4 REST pair-trade response schema**, crawled last week,
whose `sequential_id` description instead says: “해당 필드는 체결 순서를 보장하지 않습니다.”
[Indexed official schema URL](https://docs.upbit.com/kr/v1.6.4/reference/list-pair-trades).
Opening that versioned URL redirects to the canonical page. Its direct text rendering exposes query fields
but omits the expanded response schema; the canonical `.md` rendering was unavailable through this tool.
Therefore the explicit no-order sentence is **freshly retrieved indexed official schema evidence**, not a
new direct rendering of that schema. The conflict should be resolved with a current authoritative schema
or venue clarification before any implementation relies on `sequential_id` ordering. Neither statement
establishes consecutiveness, loss detection, or common order with private fills and orderbook changes.

Another ambiguity: the MyOrder field table currently lists both `REALTIME` and `SNAPSHOT` as stream labels,
while the general guide's supported-types table lists MyOrder as realtime only. No private replay/initial
snapshot mechanism should be inferred from the enum alone. See the linked MyOrder page's subscription
schema and the guide's data-types/request-field tables.

## Evidence classification for the existing task

- **Documented limitations:** no-activity silence; delayed first MyAsset delivery; idle disconnect; query/depth
  bounds. The indexed REST `sequential_id` no-order statement has the retrieval/conflict qualification above.
- **Documented capabilities, insufficient alone:** authenticated private events, per-fill fee field, public
  trade pagination, current snapshots, ping/reconnect guidance, and creation-time closed-order searches.
- **Still unspecified in the checked pages:** lossless application delivery/repair; a source-issued final
  watermark; bounded late events/corrections; atomic snapshot/stream handoff; exhaustive account-change
  coverage; and authoritative common ordering of marks, fills and fees. Authentication and local hashes do
  not fill these gaps. Closed/negative queries, silence and heartbeats are not no-event proofs.
- **Engineering conclusion:** this fresh check does not justify replacing the current refusal with an
  affirmative production verifier. It narrows the required source clarification; it does not prove no suitable
  source can ever exist. No policy redesign or new runtime mechanism is proposed by this addendum.

## Method and limits

Direct opens covered the five requested references and their official guide/best-practice links. The official
[documentation index](https://docs.upbit.com/kr/llms.txt) identified the current `list-pair-trades` URL.
Domain-restricted searches checked ordering, omission, retransmission, replay and watermark wording; search
non-results are not a proof of absence across the whole documentation corpus. Search-only legal-footer
snippets were not relied on. Relative page update labels were not converted into exact publication dates.
The tool could not render several `.md` URLs; those failures are retrieval limits, not evidence about the API.

No runtime/spec/test files changed and no runtime tests ran. Software engineering evidence only; not legal,
tax or investment advice, and the author is not a licensed adviser.
