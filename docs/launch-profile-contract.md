# First-trade profile and preflight contract

`execution_launch.profile` is a pure configuration boundary. It does not read a file, environment variable, credential, owner log or clock, and cannot sign, activate a session or place an order. The public [example](launch-profile.example.json) deliberately leaves owner choices unconfigured. Actual amounts, account aliases and decisions belong in the owner's private profile, not in this repository or chat.

## Parse and inspect

`parse_profile_json(raw)` accepts explicit UTF-8 text/bytes up to 65,536 bytes. The schema version is integer1. Unknown fields, duplicate keys, invalid UTF-8, nonfinite values, floats and numeric monetary inputs are refused without echoing raw input. Money and fractions use finite nonnegative decimal strings, such as `"12.50"`; scientific notation is not accepted. Values are bounded before formatting. Missing decision fields remain `None`, including the two exceptional-day loss budgets. An explicit `"0"` is different from missing information and remains subject to the existing risk engine's zero-budget behavior.

`LaunchProfile` contains:

- Profile/schema version; an opaque local account scope; venue, market, symbol, quote currency and time in force.
- `PolicyInputs`: a version and provenance reference digest, principal and drawdown activation equity, the existing profit/loss/target fractions, and explicit first-day/zero-profit-day loss budgets. The source digest is a reference, not a signature or proof of authenticity.
- Explicit accounting conventions and first-day scope. The currently supported contracts are listed below. Choosing another convention blocks readiness until it is implemented and verified.
- Complete exact `InstrumentRules`, including source digest and aware observation timestamp; or `null` while absent.
- Strategy ID and implementation SHA256. Strategy evidence is supplied separately, so its digest does not form a circular dependency with the profile digest.

The instrument-rules JSON object has exactly the existing `InstrumentRules` fields: `venue`, `market`, `symbol`, decimal strings `lot_size`, `tick_size`, `min_quantity`, `min_notional_krw`, `fee_fraction`, aware ISO8601 `asof`, and lowercase64hex `source_digest`. Rules must match the selected instrument and be no older than five minutes, matching E2's current execution boundary. Fractions, whole-share limits, current tick bands and actual affordability are still checked by E2 for each order; a parsed profile does not replace them.

## Supported accounting contracts

| Field | Supported value | Meaning |
| --- | --- | --- |
| `valuation` | `marked_equity` | Use reconciled marked cash/positions for account equity. |
| `daily_loss` | `externally_reconciled` | An authenticated, reconciled source supplies the chosen loss accumulator; no profit-target inference. |
| `external_flows` | `externally_cashflow_adjusted` | A reviewed external baseline handles deposits/withdrawals and high-watermark adjustment. The profile does not invent the adjustment or produce that baseline. |
| `realized_profit` | `fifo_all_fees_krw` | Existing exact FIFO realized accounting includes all supported fees converted with execution-time evidence. |
| `fx` | `current_marks_execution_time_fills` | Current FX values cash/marks; historical fill FX values realized accounting. |
| `rounding` | `fifo_floor_18dp_remainder_to_final` | Existing FIFO partial allocations round down at18KRW decimal places; the last consumption receives the remaining cost. |
| `day_boundary` | `Asia/Seoul` | Daily boundaries use the existing Seoul accounting date. |
| `first_day_scope` | `first_trading_day_only` | The exception applies to the first trading day established by complete account history, not each process restart. |

These fields declare implemented contracts and source responsibilities. They do not prove a particular account follows them. Unsupported flows, missing acquisition history, uncertain fees and incomplete source coverage still fail in the account provider.

`risk_policy(profile)` converts complete policy/convention inputs to the existing `RiskPolicy`, without monetary defaults. It preserves the existing full-peak/principal floor formula, prior-day realized-profit rule, first-day exception, missing-budget refusals and target-as-diagnostic behavior. Equality with the protection floor is not a monitor breach. A target never changes the loss budget. Input parsing does not sign or approve a modified policy; the prepared session binds the exact policy, and the owner must review it through the existing workflow.

## Two hashes, two purposes

`profile_digest(profile)` binds the complete canonical runtime snapshot, including instrument `asof`. Numerically equal decimal spellings canonicalize identically; dictionary ordering does not matter. `profile_body(profile)` returns a detached canonical body for private storage and contains private input values; do not print it in a public diagnostic.

Prospective research needs a stable contract while current rule observations refresh. `profile_contract_digest(profile)` excludes only `instrument_rules.asof`. `rule_terms_digest(rules)` excludes only `asof` from the instrument rules. Both retain source provenance, all instrument terms and all applicable profile policy/scope/strategy fields. A changed fee, tick, lot, source version, policy or strategy changes the stable binding. Existing E2 preparation/dispatch still requires the full fresh `rules_digest`; this separation does not grant an execution freshness exception.

## Preflight status and signed-limit timing

`preflight_profile(profile, now=aware_datetime, context=None)` returns field-specific fixed reason codes and actions. Its report does not expose account aliases or monetary values. `profile_complete` concerns configuration and current rule inputs. `prerequisites_ready` additionally checks the explicit supplied context. `execution_ready` always remains false: account authentication, strategy qualification, current gates, owner session approval and order validation are separate requirements.

A context must be registered/sealed and have its canonical hash intact, match today's Seoul date, contain valid approved tables and signed code, and contain effective limits. A halted owner state blocks preparation readiness. A signed principal floor cannot be below the profile principal. Missing or inactive limits remain blockers. The function never calls `owner.load_context`; the caller supplies a newly loaded verified context in the owner's reviewed environment.

The existing owner-log fold is the authority for D12 timing, log order, armed sessions and system halts. Initial settings count as loosenings; loosenings apply no earlier than the following Seoul date and can be barred by an existing session or halt. `limit_change_earliest_date` is only a scheduling advisory: it calculates the earliest calendar date for a single first/tighter/looser change and does not certify actual effectiveness. Tightenings/equality can apply immediately. Do not manufacture a signed context from a review form or from this advisory.

No real owner key, signed state, account connection, session activation or order is created by this module. This software is not legal, tax or investment advice and is not a licensed adviser.
