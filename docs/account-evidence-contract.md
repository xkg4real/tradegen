# Exact account evidence contract

`execution_accounts` connects a trusted normalized account-data source to E2's
`AccountObservation`. It performs no network call, credential read, file access,
owner signature or session activation. A successful account-evidence assessment
is separate from an E1 inquiry response and from permission to execute an order.

## Entry points

```python
build_observation(bundle: AccountBundle, *, now: datetime) -> AccountObservation
assess_bundle(bundle: AccountBundle, *, now: datetime) -> EvidenceAssessment
ReconciledAccountProvider(evidence_source)(now) -> AccountObservation
```

The collector must return the immutable types in `execution_accounts/model.py`,
with exact `Decimal` values and aware timestamps. E1's `Snapshot` and arbitrary
JSON mappings are rejected. No fallback reinterprets missing history as zero.
`EvidenceAssessment` returns fixed reason codes and counts, excludes balances and
account IDs, and always has `execution_ready=False`: owner state, a prepared
session, policy and instrument rules remain separate E2 checks.

## What the collector must establish

One `AccountEvidence` is supplied per configured venue, with an opaque local
account scope. Its opening cash anchor must describe a verified zero-inventory
origin; existing holdings need full acquisition history from that origin. This
version does not invent opening cost basis, import an unexplained portfolio, or
repair an inconsistent account history.
The opening anchor's Seoul date cannot be later than the configured first trading
day. A newer cash-only reset must not hide the previous day's loss or turn missing
profit history into zero. Late-added accounts need a separately reviewed history
coverage model and are conservatively unsupported here.

The account includes currency balances with separate total and settled amounts,
marked positions, current FX, cash-only/no-borrowing configuration and liabilities,
server time, and complete normalized fill, external-flow and broker-order pages.
All three page kinds are required even when their record collections are empty.
Every page must cover the exact opening-to-observation interval. Cursors start at
`None`, connect in order without gaps or loops, and end at a terminal `None`.
A missing or unfinished page refuses the whole account.

`source_sha256` identifies the captured source bytes; `page_sha256` binds the
normalized page and its pagination metadata. These hashes prove content integrity,
not exchange authentication or the truth of a completeness claim. The trusted,
authenticated collector must verify account identity, request bounds, retention
limits and the venue's terminal-pagination semantics before constructing pages.
An internally consistent hand-written bundle does not become broker-certified.

## Reconciliation performed here

- FIFO accounting checks full acquisition history, exact quantities, execution
  fees, currency conversion, duplicate identities and authoritative KIS broker
  identities. It derives current/prior Seoul-day realized net profit from fills.
- Opening cash plus deduplicated deposits/withdrawals plus fill cash movements
  must exactly equal current total cash in each currency. Deposits change equity
  without manufacturing trading profit. Missing dividends, taxes, transfers or
  other movements produce a mismatch; unsupported flow types are refused.
- Reconstructed FIFO inventory must match every reported holding. Positive
  prices and current FX value cash and positions; no unpriced asset is omitted.
- Broker cumulative fills must match the complete fill history before a client
  ID can enter `reconciled_client_ids`. Active orders remain visible as cash
  reservations and sell promises. Reservations exceeding settled cash or held
  units are refused, and an acknowledgment never creates a fill.
  Observed broker cash reservations conservatively block new E2 entries even if
  they may belong to this journal; cancellation and reconciliation stay available.
  Gross settled cash is not advertised as free cash after discarding broker locks.
- Current observations, FX, prices and account configuration must be no more than
  30 seconds old. Future observations, server offsets above 60 seconds and local/
  server Seoul-date disagreement refuse use. KIS market trade dates must be
  supplied explicitly from authoritative current market evidence; US dates are
  never guessed from Seoul time.
  The account observation and history end must already belong to the current
  Seoul day; a just-before-midnight page cannot finalize yesterday's profit.
- The external risk baseline supplies the day-opening equity, lifetime peak,
  approved effective floor and explicitly reconciled daily loss measure. This
  adapter cannot infer a continuous lifetime peak or select an unspecified daily
  loss convention from one balance snapshot. E2 persists its own subsequent
  peak, day-start and stop latches.

## Cash currency and supported scope

Each account binds one `execution_quote`. Only that currency's settled amount,
converted at current FX, becomes `settled_cash_krw`. Other currency balances
contribute to valuation but cannot fund that quote's order. E2 requires the
binding to match at both reserve and dispatch, so equal KRW values cannot
substitute USDT for USDC or KRW for USD. Reducing sells do not require spendable
quote cash; their holdings and existing E2 checks still apply.

`quote_rates_krw[(venue, scope, currency)]` carries every current authoritative FX
rate. Both buy and sell orders must match their own quote's exact rate at reserve
and again at dispatch. Pending buy reservations are valued at that current rate,
not their old order rate; mixed pending account scopes or spending quotes block
new entries. Historical fill conversion remains the execution-time rate. A
changed current rate does not prevent status reconciliation or cancellation of
an existing order, although fresh account and applicable identity evidence are
still required.

`held_exposure_krw` retains the compliance specification's value of everything
held at a venue, including settlement assets. It and the matching legacy exposure
remain the inputs to D6's signed venue cap. `inventory_exposure_krw` separately
contains the marked non-settlement positions. Session capital uses inventory plus
pending orders and the proposed order's costs, so already funded cash is not
counted again as an invested position. Both amounts are explicit, nonnegative,
and inventory cannot exceed total venue exposure. The existing D6 cap formula is
preserved, including its conservative addition of the new order's notional.

Supported settlement balances are KRW on Upbit, USDT/USDC on OKX, and KRW/USD on
KIS. Other currencies/assets cannot be mislabeled cash to avoid exposure checks.
One market/pair per held base asset is supported in each venue; mixed quote-pair
acquisition histories require a reviewed shared-inventory accounting extension.
All amounts entering legacy float-based compliance fields must round-trip to the
same Decimal. Unsupported precision is refused, not silently rounded.

E1 currently uses floats, bounded recent/first-page inquiry records, incomplete
fill economics and venue-aggregated cash. Those snapshots remain useful inquiry
and alert inputs, but do not satisfy this complete exact evidence contract.
Authenticated production collectors, complete source history and owner setup
must be connected and validated separately. This is account-data integration
code with offline tests, not evidence of live trading readiness or profitability.
