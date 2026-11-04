# Forward strategy validation v1

Status: implementation available; no real strategy has qualified or been activated.
The existing frozen 21,408-setting retrospective study remains unchanged, with
zero passing candidates. Its selected rows, summary labels, and reused data do
not become prospective evidence. This change does not rerun or tune that study.

## Supported scope and meaning

`execution_launch.strategy` evaluates a newly preregistered **Upbit KRW spot**
paper capture. OKX, KIS, non-KRW settlement, leverage, derivatives, credit,
shorting, and cross-currency portfolios are explicitly unsupported. Restricting
settlement to KRW avoids treating a USD/USDT gain as a KRW gain when exchange
rates fall. A future expansion needs separate currency, tax, session, and cost
models plus new validation; changing a label is insufficient.

The evaluator uses executable-quote proxies, not exchange fills. Bid/ask,
latency, tick/lot/minimum-order rules, fees, and adverse price slippage are
modeled; queue position, depth, partial fills, outage recovery, and market impact
are not proven. `research_review_ready` means the complete, reviewed paper
artifact meets its frozen mathematical filter. It grants no order permission,
does not establish future profitability, and does not establish compliance with
all account-level drawdown limits. The existing E2 owner context, signed
PreparedSession, account reconciliation, risk policy, fresh rules, execution
adapter, and per-order controller remain mandatory. `execution_ready` in this
assessment therefore always remains false: that permission belongs to E2.

## Register before collecting new observations

1. Select a strategy implementation and fixed parameter bundle for review.
   Record the exact program digest used by the launch profile/runner. Freeze the
   strategy ID, capture-source ID and source-code digest, evaluator revision
   `forward-paper-v1`, one venue/market/symbol, and KRW settlement. Selecting a
   program for paper research does not activate it for an account.
2. Construct a complete `ForwardProtocol`. Bind `profile_contract_digest` and
   `rule_terms_digest` using `execution_launch.profile`; both omit only the
   current rules observation timestamp. They retain account scope, policy,
   strategy identity, economic rules, and rule-source version. Runtime profile
   and PreparedSession digests still include fresh `rules.asof` and must pass
   their existing freshness gates. A fee, tick, lot, source, policy, strategy, or
   account change invalidates the study binding.
3. Fix the entire capture interval and bar spacing, capital, costs, additional
   slippage, minimum decision-to-fill delay, sample/trade requirements,
   drawdown filter, block length, bootstrap count/seed, significance level,
   maximum review age, and the **complete candidate family** before observing
   the interval. `family_members` is sorted, unique, and includes this strategy.
   Every parameter variation or retry considered for selection belongs to the
   disclosed research history; do not hide trials by renaming a strategy.
4. Call `register_protocol(protocol, existing_registry)`, archive the returned
   append-only registry and `protocol_json(protocol)`, and publish them before
   `capture_start` to independently reviewable, dated storage. A registry cannot
   replace/reuse a study ID. Edits require a new protocol/study ID and a new,
   genuinely unseen future interval. Preserve all failed and incomplete trials.

The in-memory hash chain detects alteration relative to a known chain and
bindings. A local timestamp or SHA-256 **does not prove** publication time,
exchange origin, independence, ownership, or the absence of undisclosed trials.
These remain explicit external review duties. No actual protocol is registered
by this repository change; no current strategy or invented future result is
presented as eligible.

## Capture contract

Record immutable `PaperBar` values at the preregistered spacing, including both
`observed_at` and `received_at`, bid/ask/mark, `quote_krw="1"`, and a digest of the
archived original source record. Retain those original records separately, with
access and retention controls. Exact first/last timestamps must equal the frozen
window, and every expected observation must exist. There is no gap filling,
future backfill, duplicated timestamp, or acceptance of an unfinished window.

For each row except the final liquidation row, record `PaperDecision` with its
zero-based row index, actual decision time, target fraction in `[0,1]`, and the
corresponding `capture_history_digests(bars)` prefix digest. A decision may use
only the prefix received by that time. Its timestamp must be at or after that
row's receive time and at least `minimum_fill_delay_seconds` before the next
observation. All recorded decisions, including cash/hold decisions, are required.
A hash of a historical prefix does not itself prove that actual strategy code
avoided future information; the reviewer must verify capture and computation.

Strict JSON uses plain decimal strings, timezone-aware ISO timestamps, exact
schema fields, integer counters, and arrays for records. Duplicated keys, unknown
fields (including `eligible`/`PASS`), JSON decimal numbers, NaN, infinity,
scientific decimal strings, and oversized inputs are rejected. A capture has
exactly `registry`, `source_kind`, `bars`, and `decisions` at its top level.
`source_kind` is one of `prospective_paper_capture`, `synthetic`, or
`retrospective_replay`; the latter two are always ineligible for review readiness.
A self-declared prospective label is also insufficient without trusted review.

## Reproducible evaluator and selection filter

Run `run_paper_validation(protocol, bars, decisions, rules, registry=registry,
source_kind=source_kind, now=evaluation_time)` after the entire capture has been
received. `evaluate_capture_json(protocol, raw_capture, rules, now=...)` provides
strict archival import and reruns the same arithmetic. The evaluator has no
network, credential, owner-signing, or order-submission operation.

Cash and units use exact rational arithmetic, independent of ambient Decimal
precision. A target is applied at the following observation, after its decision
and configured minimum delay. Buys use ask plus slippage rounded up to a tick;
sells use bid minus slippage rounded down. Both sides pay fees. Quantities are
lot-rounded and constrained by cash, minimum quantity, and KRW minimum notional.
No borrowing or negative inventory is permitted. The final row liquidates all
holdings and pays costs; unliquidatable dust refuses the capture. Marked NAV
provides period returns/drawdown; terminal cash return is net of modeled costs.
These paper metrics are distinct from a real account's broker-verified daily
realized net P&L. The user's 30% minimum daily target remains a target, not a
statistical test outcome or a guaranteed return.

Each run computes the original strategy, twice the fees and slippage, an extra
one-bar decision lag, and a costed buy-and-hold benchmark on the same capture.
The paired excess-return mean is tested using a seeded centered circular
moving-block bootstrap. Its one-sided p-value is `(exceedances+1)/(B+1)`, then
Bonferroni-adjusted by the **entire preregistered family size**, even if some
members never produce complete results. The block length, family, and window
must not be altered after seeing a result. Dependence/nonstationarity outside
the block model and limited effective sample size remain research limitations;
a small p-value is not proof of market profitability.

All frozen requirements must pass: sufficient observations and completed
roundtrips; positive original net return and mean; positive benchmark excess;
family-adjusted p-value no greater than alpha; positive return and mean under
both cost/lag stresses; and drawdown within the frozen cap in all three strategy
runs. Implementation bounds require at least 60 observations, 20 roundtrips,
999 bootstrap replications, and alpha no greater than 0.1. These are lower
software bounds, not a recommendation that every such sample is adequate.
The p-value resolution and family size can make a pass impossible; collect a
new preregistered study with adequate resolution rather than lowering a
threshold after the fact. Runtime and input size limits produce explicit
refusals rather than partial “success”.

## Reviewed gate and trusted boundary

`assess_strategy(protocol, result, profile_contract_digest=...,
rule_terms_digest=..., strategy_code_sha256=..., now=current_time,
review_verifier=trusted_verifier)` checks exact deployment bindings, expiry,
source class, and all computed criteria. It only accepts results issued by the
current evaluator process with unchanged canonical contents. An imported
summary, copied dataclass, arbitrary boolean, or hand-written `PASS` cannot
qualify. After a restart, replay archived full inputs; use the original reviewed
evaluation timestamp to reproduce its evidence digest, then assess against the
actual current time. Review age remains bounded by the original capture end.

The optional verifier is an explicitly trusted integration dependency, **not**
a default acceptance callback. It must verify independent capture origin,
published preregistration before collection, disclosed trial family, source and
strategy code versions, faithful causal decisions from those versions, and the
original record archive. It must authenticate that review through the project's
reviewed/owner-controlled process. Only then may it return `ReviewReceipt`
containing the exact `ReviewBinding` digest, reviewer identifier, digest of the
review record, review timestamp, and finite expiry. This change does not invent
a new owner-signing event or treat a receipt's own hash as proof of its issuer.
An untrusted caller can fabricate receipt fields; therefore a generic lambda or
JSON receipt importer must never be connected as a trusted production verifier.
Default absence, malformed return, mismatched binding, expired/future review,
and verifier exceptions all refuse readiness.

`math_qualified` separates the computed numerical result from source/review
readiness. `research_review_ready` requires every check and a verified receipt;
`reasons` reports missing, stale, mismatched, nonprospective, or failed evidence.
There is no implicit conversion of insufficient/unknown evidence to a pass.
The runner additionally requires paper initial capital to equal the launch
profile initial principal exactly, preventing large-account paper fills from
concealing small-account lot/minimum-order constraints. It caps a prepared
entry stake at that principal; current reconciled account constraints still
apply. A runner must re-assess current bindings and expiry before acting and
separately verify the actual strategy callable/parameters against the reviewed
program.
Order authorization then remains exclusively with the existing E2 gates.

## Offline test evidence

`tests/launch_strategy.py` constructs invented 2030 sawtooth quotes and fake
review receipts to exercise both mathematical acceptance and refusal paths.
These fixtures are expressly not exchange data, source authentication,
preregistration evidence, market research, or owner authorization. They cover
cost/lot/lag arithmetic, rule timestamp refresh versus economic changes,
nonprospective sources, missing/altered/forged reviews and result objects,
expiry, registry integrity, causal prefixes, gaps, family correction, Decimal
context invariance, strict import, and unsupported settlement/market versions.
The frozen retrospective research is neither opened nor used by these tests.
