# Delegated market selection: prospective evidence protocol

Status: design specification only. The user delegated market and asset selection
to TRADEGEN and selected a Windows PC for deployment. Market choice is therefore
an internal research task, not a pending request for the user to choose a venue.
Windows deployment does not establish a market's suitability or profitability.

The current honest selection is `NO_QUALIFIED_MARKET`. The frozen historical
21,408-setting study had zero passing candidates. Its data, results and settings
remain unchanged. No old study is rerun, no candidate is invented, and no live
market is selected by this document. An older strategy's PASS applies only to
its original protocol and cannot qualify a different deployment or study.

## Scope and present implementation

A market is a `(venue, product, settlement_currency)` group. An asset is the
underlying economic exposure within that group; symbols, parameter variations,
or repeated studies of the same exposure do not create additional assets.

The current prospective evaluator supports only **Upbit, KRW-settled spot**.
Upbit can remain the initial integration and prospective-research target. This
is an implementation scope decision, not evidence that it has the most validated
assets or the best risk-adjusted performance. Comparing KIS, OKX, foreign
settlement currencies, or other products requires separately reviewed source,
calendar, currency, fee, tax, trading-rule and execution models before any
cross-market claim. A new venue label cannot supply those models.

This protocol supplements [forward validation](forward-strategy-validation.md)
and the [quote source contract](upbit-quote-contract.md). Ranking never grants
execution permission or replaces account, risk, session or owner-signature
requirements.

## Freeze the comparison before new observations

TRADEGEN determines and records the research choices below from available
evidence under the delegated mandate. The user need not select the market.
Unavailable evidence remains unavailable; the system must not manufacture an
input or mark an unperformed review complete.

Before capture starts, publish an independently reviewable comparison record
binding all of the following:

- Every included market, asset and economic risk group, including a stable
  underlying-exposure mapping that prevents duplicate asset counting.
- Every candidate strategy, parameter bundle, source/program version and
  planned retry. Membership spans all assets and markets considered for this
  selection; a separate per-asset family alone does not account for the final
  market search. Failed and incomplete members remain disclosed.
- One common future window, return interval, capital basis and settlement
  currency for each comparable group; the treatment of sessions, missing
  observations, cash returns, costs and benchmarks must also be identical in
  meaning. Different studies cannot be compared merely because both report SR.
- Required sample length and completed roundtrips; fee/slippage and delay
  stresses; drawdown and benchmark-excess filters; inference error level,
  block length, resampling budget/seed and whole-family correction; maximum
  evidence age; and the exact selection order below.
- A future confirmation window and fixed acceptance criteria if a winner's
  performance will be claimed independently of the selection sample.

The registration must precede genuinely unseen observations. Local timestamps,
file hashes and a self-declared prospective label do not prove independence or
publication. Retuning after seeing results requires a new disclosed study and a
new future window; it does not erase earlier trials. Increasing a resampling
budget or changing a threshold after discovering that a candidate fails is not
part of the frozen comparison.

Existing evaluator bounds are software minimums, not proof of adequate effective
sample size. In particular, the smallest corrected bootstrap p-value is limited
by the complete family size and replication count. Check feasibility before
capture; do not omit unsuccessful candidates to make a pass possible.

## Eligibility before ranking

Only actual recomputed prospective results that meet all existing numerical
filters and have a currently valid authenticated source/implementation review
can enter the qualified set. Reuse `run_paper_validation()` and
`assess_strategy()`; imported summaries, copied PASS flags, synthetic fixtures
and retrospective replays cannot qualify.

Each candidate must pass the frozen baseline, twice-cost and additional-delay
conditions, sample/trade requirements, benchmark-excess test with the complete
family correction, and drawdown limits. Review must establish original source
records, publication before collection, an independent capture interval, the
complete trial history, and causal decisions from the frozen program. Current
capital, lot/minimum-order, fee, account and deployment bindings must match.

The existing evaluator's `family_members` mechanism is useful but must describe
the entire actual search when a result is used in this comparison. Do not assume
that independently passing small per-asset families controls a later search
across all assets, strategies and markets. Unsupported family sizes or inference
workloads produce an explicit unresolved result, not a partial selection.

## Breadth and comparable risk-adjusted performance

For every market, report both the number of distinct qualified assets and the
number of preregistered economic risk groups containing a qualified asset.
Report return correlations where aligned observations permit them. A risk-group
label or a distinct symbol is not proof of statistical independence. Multiple
Bitcoin wrappers or many correlated crypto strategies must not be described as
independent discoveries. Count an asset once even when several variants pass.

For ranking, compute a common **unannualized Sharpe ratio** from aligned,
cost-adjusted returns over the same fixed intervals:

```text
excess[t] = net_strategy_return[t] - frozen_cash_return[t]
SR = mean(excess) / sample_standard_deviation(excess)
```

Use the same explicitly justified cash-return convention throughout a comparable
group. Benchmark-relative returns and their tests remain separate; their ratio
is not silently substituted for the cash-relative SR. Nonfinite observations,
zero variance, insufficient samples or incompatible return grids make an item
`UNRANKABLE`, never an infinite-SR winner. Cash-only inactivity is not a strategy
qualification.

Do not sort annualized stock-day SR against calendar-day crypto SR, mix different
holding periods, or combine KRW and foreign-currency returns without an explicit
common-currency model. Optional annualized displays must state a consistent
calendar and assumptions; they do not change the ranking. Serial dependence
also means naive square-root annualization does not establish comparable risk.

Use the preregistered block-resampling method to estimate uncertainty while
retaining temporal dependence and, for aligned candidates, their shared market
shocks. Construct simultaneous lower confidence bounds over the **whole declared
selection family**, including parameter searches and retries, rather than
pointwise intervals for winners alone. Freeze the correction and confidence
level before capture. Resampling assumptions and finite effective sample size
remain explicit limitations; the interval is not a guarantee of future SR.

## Deterministic selection order

Within a comparable group, apply this order to eligible markets:

1. More preregistered economic risk groups containing qualified assets.
2. More distinct qualified assets.
3. Higher simultaneous SR lower bound of the market's representative candidate.
   That representative is the qualified candidate with the highest such bound;
   its selection is included in the same whole-family uncertainty calculation.
4. Lower worst drawdown across the representative's baseline and cost/delay
   stresses, then lower turnover measured on the same capital/time basis, then
   stable lexical candidate/market identifiers for reproducible ties.

Thus breadth is the first priority and risk-adjusted performance distinguishes
equally broad eligible markets. Report raw SR alongside its lower bound and
stress results. A representative's SR is not the return of an unconstructed
market-wide portfolio. Portfolio weights, covariance, cash allocation and
rebalancing require a separately frozen, executable portfolio experiment.

Never force a winner when there are no qualified candidates, incomplete family
accounting, missing reviews, or incomparable groups. Return the explicit reason
and preserve every failure. Selecting the highest observed statistic does not
make its performance estimate independent of selection; an independent
post-selection performance claim requires the previously frozen confirmation
window without reselection or retuning.

## Small offline implementation boundary

A future pure `rank_market_evidence(...)` helper can reuse:

- `strategy.py`: immutable protocols and registrations, recomputed
  `ValidationResult.net_returns`, deployment bindings and reviewed assessment.
- `review_auth.py`: the trusted review boundary; no generic always-accept
  callback or self-signed status supplied by the ranking input.
- `profile.py`: account/capital, economic rules and deployment contract checks.
- `paper_capture.py`: prospective capture and causal decisions, with original
  quote receipts retained for independent review.

The helper should take explicit comparison metadata, actual evaluated results,
the required trusted review dependency and the current aware time. It should
return comparison-group identities, exclusions, result/review digests, qualified
asset/risk-group counts, SR estimates and uncertainty, stress metrics, and either
a deterministic research selection or `NO_QUALIFIED_MARKET`/`INCOMPARABLE`.
Its authority fields remain `execution_ready=False`; it must not read keys,
fetch data, rewrite a launch profile, arm a session or submit orders.

This document adds no helper implementation, real capture, synthetic winner,
test run or historical reevaluation. Current evidence still supports no
qualified live market. Windows deployment preparation and additional offline
engineering may proceed independently while new evidence is gathered by the
authorized operator and reviewed.

This is engineering and research documentation, not legal, tax or investment
advice; the author is not a licensed adviser.
