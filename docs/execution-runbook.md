# Execution runbook

E1 provides inquiry and alerts, E2 durable control and accounting, and E3 order codecs and transports.
These library interfaces have offline tests; live accounts and order execution remain unvalidated.
Strategy status is **UNVALIDATED**: software tests do not establish a profitable trading strategy.

## Supported orders

| Venue | Order identity | Supported limit order validity |
| --- | --- | --- |
| Upbit | `venue="upbit"`, `market="spot"`, pair such as `KRW-BTC` | `time_in_force="gtc"` |
| OKX | `venue="okx"`, `market="spot"`, pair ending in `-USDT` or `-USDC` | `time_in_force="gtc"`, cash spot only |
| KIS | `venue="kis"`, `market="krx"`, six-digit ticker | Explicit `time_in_force="day"`, whole shares |
| KIS US | `venue="kis"`, `market="nasd"`, `"nyse"` or `"amex"`, approved ticker | Explicit `time_in_force="day"`, whole shares |

Orders use `Decimal` quantity, limit price and quote-to-KRW conversion, plus a unique client ID
and opaque local `account_scope`. The default validity is GTC, so KIS callers must select DAY.
Instrument rules must match the exact venue, market and symbol. Invalid quantities, ticks and
minimums are refused without rounding. Margin, credit, derivatives, transfers and withdrawals
are outside this order interface. See [value types](../execution_control/model.py) and
[venue codecs](../execution_orders/) and [official wire-contract evidence](superpowers/specs/2026-10-31-e3-wire-evidence.md).

## Library integration

- E1: [`poll_once(now)`](../execution/poll.py) stores inquiry snapshots and alerts; it does not place exits or halt E2.
- E2: [`Journal()`](../execution_control/store.py) stores checked, locked control state under
  `TRADEGEN_HOME/execution-control`. [`prepare_session(...)`](../execution_control/session.py)
  reruns the selected odds plan with a fresh comparison seed and binds `instrument_rules`.
- [`Controller(journal=..., account_provider=..., policy=..., adapters=..., session_provider=...)`](../execution_control/controller.py)
  provides `observe`, `reserve`, `dispatch`, `reconcile`, `cancel`, `kill`, `halt` and
  `approve_floor_relaxation`. Operations receive explicit aware `now` values. The account
  provider supplies `AccountObservation`; the session provider returns the actual issued
  `PreparedSession`. Contexts, permits and dispatch capabilities are obtained internally.
- [`DryRunAdapter(codec, results=...)`](../execution_control/dry_run.py) uses supplied outcomes without HTTP; fills need separate evidence.
- [`AuthenticatedTransport(credentials=provider)`](../execution_orders/transport.py) implements
  `prepare`, `prepare_cancel`, `prepare_status` and `dispatch`. The explicit provider accepts
  `(venue, account_scope)` and returns matching `Credentials`. Its default refuses credentials;
  it has no environment reader, token refresh, automatic retry or default live configuration.

An explicit synchronous [launch runner](automatic-runner-contract.md) now connects supplied
quote, account, strategy and controller providers. Its default observes only; rehearsal uses
exact dry adapters and isolated state. A caller supplies bounded timestamps; there is no hidden
background worker or default live configuration. See the [owner checklist](first-trade-owner-checklist.md)
for configuration, strategy qualification and actual signing still required before a first trade.

## Owner setup still required

1. Review the final code closure and configure verified owner approvals, limits, required
   acknowledgments and current code signature using the existing owner workflow. Only the owner
   signs and arms a session; preparing a session does neither. Changed code needs renewed approval.
2. Supply complete, fresh, account-scoped balances, holdings, server time, trading dates, fills,
   fees, FX, external-flow reconciliation, exact `held_exposure_krw` and no-credit evidence.
   KIS needs verified `venue_trade_dates` and `cancellable_quantities`. E1 snapshots do not prove
   complete [FIFO history](../execution_control/risk.py). Sells require exact holdings matching
   legacy positions; external sell promises are unsupported and need manual reconciliation.
3. Supply current instrument provenance, lot/tick rules, minimums and fee reserves. Configure the
   policy's first-day and zero-profit-day loss budgets explicitly; missing values remain refusals.
   A profit target is diagnostic and does not raise position size or override a stop.
4. Prepare fresh odds with instrument rules before arming. The owner must arm the returned
   `prepared.session_id`, which binds the preparation content, never the original input label.
   Capital includes held exposure and pending reservations. Preparation expires and is process-bound;
   restart needs fresh preparation and reconciliation before new entries.
5. Integrate credentials only through the explicit provider in the owner's environment. KIS
   requires a supplied bearer token and account components. Do not send credentials to chat or
   commit them. Live connectivity and account permissions still require owner validation.

Equity equal to the protection floor is not a monitor breach; other entry checks still apply.
A floor reduction needs the approved deferred transition, not merely an activation threshold crossing.

## Uncertain outcomes and recovery

`DISPATCHING` recovered after restart is treated as `UNKNOWN`. Never retry an uncertain create
request or free its cash/unit reservation on a timeout. Reconcile the original identity first.
An acknowledgment is not a fill; cancellation acknowledgment is not terminal cancellation.
Release requires complete authoritative fill history and fees; missing acquisition history refuses FIFO.
Broker average price times filled quantity must equal fill-derived notional; rounding differences retain the reservation.
KIS status supports only a single complete response page; pagination or missing completion
evidence returns UNKNOWN. KIS US final cancellation mapping is unverified and remains UNKNOWN.
Corrupt journals, torn tails and checkpoint mismatches refuse use; do not delete or repair them
to resume trading. Kill/halt preserves qualified exits and known-order cancellation, but does
not invent an exit for unidentified holdings or guarantee execution at a protection floor.
If local/server clocks disagree on the Seoul date, kill/halt retains the local latch and returns
failure without appending an owner system entry; new account-dependent operations refuse.

## Reproduce offline checks

From the repository root, activate the configured Python 3.13 environment and run tests serially.
Wrappers use temporary state and fake HTTP without rewriting QA results; this block disables all inherited key inputs:

```sh
(
  export KIS_APP_KEY='<unset>' KIS_APP_SECRET='<unset>' KIS_ACCOUNT_8='<unset>' KIS_ACCOUNT_PD='<unset>'
  export UPBIT_ACCESS_KEY='<unset>' UPBIT_SECRET_KEY='<unset>'
  export OKX_API_KEY='<unset>' OKX_API_SECRET='<unset>' OKX_API_PASSPHRASE='<unset>'
  export OPENDART_API_KEY='<unset>' KRX_API_KEY='<unset>' FMP_API_KEY='<unset>'
  export ANTHROPIC_API_KEY='<unset>' GS_CLIENT_ID='<unset>' GS_CLIENT_SECRET='<unset>'
  export FINVIZ_API_KEY='<unset>' ALPACA_API_KEY='<unset>' ALPACA_SECRET_KEY='<unset>' FXMACRODATA_API_KEY='<unset>'
  python -m tests.execution_acceptance && python -m tests.control_acceptance
)
```

Either wrapper accepts an optional test-name substring. Inspect FAIL and NOT_RUN separately;
neither provides live validation. See the [E2/E3 design](superpowers/specs/2026-10-31-e2-e3-execution-design.md).
This software is not legal, tax or investment advice and is not a licensed adviser.
