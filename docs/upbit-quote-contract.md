# Upbit public quote source contract

Status: implemented for synthetic verification and later owner integration. No
exchange or data API was called during development. This source does not arm a
session, submit orders, read credentials, or establish account readiness.

## Official interface and narrow local scope

The Korean [Upbit REST orderbook reference](https://docs.upbit.com/kr/reference/list-orderbooks)
was reviewed on 2026-11-02. It documents public `GET /v1/orderbook`, the `markets`,
`level`, and `count` parameters, millisecond `timestamp`, total bid/ask sizes,
and ordered `orderbook_units` containing bid/ask prices and sizes. Its count can
reach 30; native ungrouped depth uses level zero. The official limit is 10
requests per second per IP, shared with the orderbook group. The
[Korean WebSocket field reference](https://docs.upbit.com/kr/reference/websocket-orderbook)
corroborates the native-level and field meanings; no WebSocket is implemented.

`execution_accounts.quotes.E1UpbitQuoteSource` permits one fixed `KRW-<ASSET>`
spot symbol per instance. It always requests:

```text
GET https://api.upbit.com/v1/orderbook?markets=KRW-BTC&level=0&count=30
```

Only the selected symbol varies. There are no free-form URLs, foreign Upbit
hosts, batches, aggregation levels, or ticker substitutions. Existing E1
allowlists gain only this exact GET and its public classification. POST, DELETE,
plural/suffixed paths, and `/v1/orderbook/instruments` remain refused. Existing
account collection and snapshot polling do not automatically call this source.

## Public Python interface

```python
E1UpbitQuoteSource(symbol="KRW-BTC", clock=aware_clock, route=managed_route_or_none)
source.read()                         # explicit owner operation; performs E1 GET
parse_orderbook(receipt, symbol="KRW-BTC", now=aware_time)  # pure validation
to_runner_quote(book, now=tick_time)   # pure validation and conversion
```

Import and construction perform no I/O. The clock is required and injected into
E1's context-local inquiry clock. An optional validated `ManagedRoute` scopes
the existing proxy and CA behavior to the request and restores it on exit. The
source does not discover environment variables, read keys or local homes, change
network policy, or replace the transport. Cloud operation additionally requires
the deployed runtime's actual destination policy to allow `api.upbit.com:443`;
constructing a route cannot grant that permission.

`OrderbookQuote` contains the selected `symbol`, source `asof`, `received_at`,
HTTP `server_time`, ordered `levels`, best `bid`/`ask` and their sizes, total
sizes, `source_sha256`, and the original `receipt`. The receipt retains exact
raw bytes, query parameters and timestamps. Its fixed public scope is
`public-upbit-orderbook`, not an account identifier. Its digest is an integrity
reference, not a signature, account-identity proof, or independently trusted
provenance. `midpoint` is an exact derived mark, not a last trade, guaranteed
executable price, or OHLC candle. Displayed depth is not a fill guarantee or a
claim to possess the complete venue book.

## Validation and time semantics

The normalizer verifies the receipt's exact path, parameters, public scope,
raw-byte SHA-256, a 128 KiB body limit, unique JSON object keys, and finite numeric
tokens. It decodes numeric tokens from raw bytes directly into `Decimal`; it
never reuses the transport's binary-float parsed body. Prices and sizes must be
positive, bounded numeric values. Stringified numbers and booleans are refused.

Exactly one book must match the selected symbol and native numeric level zero.
One through 30 displayed levels must have strictly increasing asks, strictly
decreasing bids, and bid strictly below ask. Empty, locked, crossed, duplicate,
or unsorted depth is refused. Each total size must cover its displayed side;
larger totals do not imply the additional depth is available to this strategy.

All local times must be timezone aware. The exchange timestamp must be an
integer in milliseconds. Receipt and book age must each be between zero and ten
seconds at validation; the book also cannot postdate its receipt. HTTP `Date`
is required and must be within 60 seconds of receipt time. The source checks
that the E1 receive time lies between its explicit before/after clock readings.
These are strict local admission rules. Clock disagreement causes refusal; a
timestamp is never rounded, moved backward, or replaced with a scheduler time.

The pure runner bridge reparses the original receipt and compares the entire
frozen quote record before returning `execution_launch.runner.Quote`. It keeps
the original bid, ask, source digest and `asof`. Changed records, future quotes
and expired quotes are refused again at conversion.

## Owner orchestration and latency

Prefetch account evidence and the quote, then choose the runner's tick time:

1. Complete the account observation and receive a public book. Fetch the book
   after a long account capture when needed to keep quote age bounded.
2. Read the aware clock for the actual tick after both results exist.
3. Validate `to_runner_quote(book, now=tick_time)` and provide the already
   received quote and account observation to `Runner.tick(now=tick_time, ...)`.
4. If either observation has expired, do not tick with it. Recollect as needed
   and choose a new tick time after receiving the new observations.

Fetching inside a quote provider after choosing `tick_time` can produce a
legitimate quote newer than that tick and is refused. The runner is not changed
to disguise that timing error. Prospective fixed-slot capture separately needs
an explicit observation-slot contract preserving the receipt and source `asof`;
the quote source does not rebucket data or invent missing samples.

Existing E1 behavior remains: a 10-second request timeout, 0.2-second pacing per
attempt, and at most one GET retry after two seconds for eligible connection
errors, HTTP 429, or server errors. No extra retry loop is added here. Freshness
is assessed after the request/retry returns and again at consumption, so retry
success cannot make an old book fresh. A missed capture slot is a missed slot.
Multiple workers sharing one IP must coordinate their total rate outside this
binding. Fixed diagnostic codes omit raw provider errors and response bodies.

## Verification boundaries

`tests/accounts_quotes.py` covers exact decimal preservation, malformed or
contradictory receipts/depth, timestamp limits, public credential-free E1 calls,
the exact method/path guard and denied neighbors, explicit route restoration,
and tampered/stale/future runner records. All HTTP responses in those tests are
synthetic and use the existing hermetic E1 seams. Passing them cannot establish
live venue compatibility, network permission, owner approval, liquidity, or
profitability. Real capture and execution remain owner-operated deployment work.

This is software engineering documentation, not legal, tax or investment advice;
the author is not a licensed adviser.
