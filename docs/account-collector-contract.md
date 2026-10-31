# Authenticated account collector contract

Status: implemented source binding and synthetic validation cases; no real account
has been contacted or connected by this change. Upbit KRW spot is the initial
reference implementation. Owner market selection, credentials, identity evidence,
opening/history evidence and live validation are still required. A successful
account collection does not authorize an order, owner signature or activation.

## Entry points and trust boundary

`execution_accounts.upbit_collector.E1UpbitSource` binds the existing E1
transport to seven literal read-only GET paths: accounts, open orders, closed
orders, individual order detail, deposits, withdrawals and ticker. No write route
is added. The individual detail path is `/v1/order`; the older E1 poll remains
unchanged and its bounded float summaries are not accepted as complete evidence.

The source requires an explicit account scope, absolute state directory matching
an explicitly configured `TRADEGEN_HOME`, and caller-owned aware clock. Both
`UPBIT_ACCESS_KEY` and `UPBIT_SECRET_KEY` environment **names** must be present
before every request. Only E1 reads their values; an unset name refuses before
E1 can fall back to the repository `.env`. Blank or placeholder values still
refuse in E1. The caller must control the process environment exclusively during
collection. Nothing here opens a credential file, persists an answer, loads an
owner signing key or sends an order.

Managed Cloud routing can wrap collection in
`execution_network.route.managed_route(reviewed_route)`. The collector's scoped
`execution.transport.inquiry_clock(clock)` preserves that surrounding route.
A route object must come from the separately reviewed managed-route factory;
no route is guessed from ambient proxy settings by this collector.

`collect_upbit(source, anchor=..., coverage=..., risk_baseline=..., clock=...)`
returns a `CollectionResult` containing:

- A fully reconciled `AccountBundle` for `ReconciledAccountProvider` / E2.
- Every raw `SourceReceipt`, retaining exact response bytes, request path and
  ordered parameters, account scope, receipt time, server time and SHA-256.
- A manifest SHA-256 over receipt metadata/hashes, opening anchor, reviewed
  coverage evidence and any explicit per-trade fee evidence.

The normalized fill/flow/order pages use that manifest as their source digest.
Their single terminal chain describes normalized output; it does **not** pretend
the exchange supplied a complete archive in one page. The retained source
receipts show all actual page numbers and time windows, including empty terminals.
The caller is responsible for retaining this result in an appropriately private
reviewed evidence store. This change does not implement that storage.

`SourceReceipt.decode()` rechecks raw-byte SHA-256 and decodes JSON numbers directly
as `Decimal`, rejecting duplicate keys, nonfinite values and oversized bodies.
Accounting fields documented as decimal strings must remain strings in raw JSON;
a binary float or legacy parsed E1 body is never promoted to exact evidence.
Errors contain fixed diagnostic codes, not response rows or credential values.

A custom injected source is a trusted broker-import/test boundary. A receipt hash
alone does not make that source authenticated. Production authentication comes
from `E1UpbitSource` using E1's JWT signing and checked HTTPS transport. The API's
balance response does not identify the owner; the credential-to-account binding
must be established independently.

## Evidence the API cannot supply

Before any fetch, the collector requires reviewed `OpeningAnchor`,
`CoverageEvidence` and a separately established `RiskBaseline`. These objects
refer to reviewed source-document hashes, not self-validating signatures. A hash
of arbitrary bytes or the expected literal statement is insufficient evidence in
an operational approval. The trusted caller/reviewer must inspect the documents.

The opening anchor must establish exact KRW cash, zero coin inventory **and zero
open/part-filled orders** at the origin. History must cover the entire period
from that origin through completion of collection, including orders created
before the current reporting day. The reviewed retention evidence must establish
that the exchange/import source still exposes every relevant record; the public
REST documentation does not promise an unlimited historical archive.

Coverage also establishes all of the following:

- The selected credentials correspond to the reviewed **main pocket** and scope.
- The account is KRW spot cash only, with no borrowing, loans or liabilities.
- There are no unreported flows, rewards, adjustments or pocket transfers.
  Deposits/withdrawals alone do not enumerate every possible pocket movement.
- A pre-established exclusive-account fence covers the entire capture: no manual
  or API trading/matching activity, transfers or balance-changing events occur
  within it. A market with resting orders cannot claim this merely because the
  operator is idle. If a genuine fence cannot be established, this collector
  must not supply execution-ready account evidence.

Balances, open orders and complete deposit/withdrawal page sets are read again
and must match. These checks detect many changes but cannot prove atomicity or
exclude an ABA sequence. They supplement the external fence rather than replacing
it. The account is stamped at the end of the capture only because the reviewed
fence establishes no intervening account changes. Both ticker metadata time and
the underlying last-trade time must be nonfuture and at most 30 seconds old;
the position's as-of time uses the trade time. A complete collection must finish
within 30 seconds; a large archive
needs a separately reviewed archive/delta source. This implementation refuses an
oversized/slow scan rather than truncating it.

The risk baseline's first trading day must equal the earliest captured fill's
**Seoul date** whenever fills exist. Yesterday's realized loss therefore cannot
be hidden by labeling today as the first day. With empty history, the proposed
first trading date is still external baseline evidence. A restart, new key,
account scope label or more recent zero-inventory anchor does not reset risk
history, first trading date, prior-day P&L or the high-water mark. Opening/retention
review must reject attempts to hide pre-origin activity. The collector does not
derive or approve an equity floor or loss budget.

## Exchange pagination and supported normalization

Official documentation reviewed for this implementation:

- [Closed orders](https://docs.upbit.com/kr/reference/list-closed-orders): created
  time filters, maximum seven-day query interval, limit at most 1,000. There is no
  documented page/cursor parameter. The collector covers origin through capture
  start with bounded millisecond windows, pads outer boundaries, overlaps adjacent
  windows and deduplicates identical UUID records. Saturated windows are split;
  saturation at a two-millisecond interval refuses. It never invents a page
  parameter. Neither undocumented timestamp tie behavior nor retention is assumed.
- [Open orders](https://docs.upbit.com/kr/reference/list-open-orders): explicit
  `states[]=wait` and `states[]=watch`, page starting at 1, limit 100. A short/empty
  terminal page is required. Repeated identifiers across numbered pages, changed
  records, exceeded bounds and unknown states refuse. `watch` is requested so it
  cannot be silently omitted, but its execution semantics are currently unsupported.
- [Order detail](https://docs.upbit.com/kr/reference/get-order): every listed order,
  including partial open orders, receives a UUID detail read. Shared fields must
  agree; every trade's UUID, side, market, time, volume, price and funds reconcile
  with the order's executed volume and trade count. Only limit orders in
  `wait`, `done` or `cancel` are supported. Market/best orders refuse pending a
  reviewed quantity/reservation model. Terminal canceled residual quantity is
  normalized to zero reservation while its actual fills remain in history.
- [Deposits](https://docs.upbit.com/kr/reference/list-deposits) and
  [withdrawals](https://docs.upbit.com/kr/reference/list-withdrawals): page/limit
  iteration through a terminal page. `from`/`to` are UUID cursors, **not dates**;
  this collector does not use them. Completed `ACCEPTED` deposits and `DONE`
  withdrawals require completion times. The supported flow path is KRW, default
  transaction type and zero fee. Pending/reversed flows, crypto transfers,
  internal transfers and nonzero flow fees refuse; the API's fee label alone
  does not establish a reviewed gross/net convention.
- [Pocket overview](https://docs.upbit.com/kr/reference/pocket-overview): account
  and order responses are pocket scoped; deposit/withdrawal history is main
  pocket only. Universal pocket-transfer history requires a different permission
  that also permits transfers. This change does not request it or broaden the
  inquiry key. Such movements must be excluded by reviewed evidence, or supported
  by a separately reviewed source before collection can succeed.
- [Ticker](https://docs.upbit.com/kr/reference/list-tickers): `trade_price` is a
  JSON number decoded losslessly; `trade_timestamp` is the most recent trade's
  epoch-millisecond time and `timestamp` is current-price information update
  time. A recently updated response cannot make an old trade price fresh.

`paid_fee` is an **order-level** decimal amount. A single trade receives the
exact order fee. Multiple trades can receive zero fees only when `paid_fee` is
zero. Otherwise every trade needs authoritative `TradeFeeEvidence` whose exact
sum equals the order's paid fee. The collector does not guess proportional fees
or assign all fees to one day. Unused, missing, contradictory or duplicate fee
evidence refuses.

Gross KRW balance is available plus locked balance. Coin quantity is likewise
available plus locked. Broker locks must equal the normalized active buy/sell
reservations exactly; unexplained locks refuse. Settled gross cash is passed to
the existing provider, which carries gross settled cash and reservations
separately; execution authorization subtracts commitments once. The provider
then verifies the full cash equation, FIFO inventory, all order fills,
reservations, quote currency, source freshness and risk-baseline structure before
a bundle can leave the collector.

## Safe integration sequence

1. Select the venue/market with the owner; confirm the reference implementation's
   scope and limitations fit that account. Do not silently choose Upbit for them.
2. Establish the private inquiry-only key and explicit state directory through
   the existing owner-controlled setup; never paste key values into chat or GitHub.
3. Review credential identity, opening cash/empty inventory and open orders,
   retained complete history, missing flow classes and a genuine capture fence.
   Obtain a fresh risk baseline and exact per-trade fee records if needed.
4. Under the reviewed network route, create `E1UpbitSource` and call
   `collect_upbit` with those explicit inputs. There is no automatic startup hook
   or default network source. Preserve the private receipts and manifest.
5. Supply `result.bundle` to the existing reconciled provider and inspect its
   account-evidence assessment. Owner local signature, session activation,
   execution checks and the remaining first-trade prerequisites are separate.

Synthetic coverage is in `tests/accounts_collector.py`: exact receipt decoding,
source binding with stubbed E1, pagination and saturation, fee attribution,
partial/canceled order reconciliation, unsupported flows, missing evidence,
mutating snapshots and prior-day-loss/first-day regression. No test contacts a
real exchange or reads a credential file.
