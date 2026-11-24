# BR-26 adaptive Y research preview

The preview estimates the direction of a fixed-horizon price move and proposes a working bid-gap threshold for a future observation. It is an offline tool for Upbit KRW long spot research. It reads a supplied JSON document and prints diagnostics. The software-wide maximum is 5% inclusive. The operator's already effective ceiling can be lower.

## Try the synthetic example

Run from the repository root with Python 3.13. The example uses deliberately one-sided synthetic returns to exercise the positive branch. The probabilities and model settings in this fixture are not performance estimates or suggested live terms.

```shell
python -m tools.research.adaptive_bid_gap_preview --example > example.json
python -m tools.research.adaptive_bid_gap_preview --input example.json
```

Windows PowerShell 5.1 defaults to UTF-16 for `>`. To save the example as UTF-8 there, use:

```powershell
$example = & .\.venv\Scripts\python.exe -m tools.research.adaptive_bid_gap_preview --example
[IO.File]::WriteAllLines((Join-Path $PWD 'example.json'), [string[]]$example, [Text.UTF8Encoding]::new($false))
& .\.venv\Scripts\python.exe -m tools.research.adaptive_bid_gap_preview --input .\example.json
```

Single-quote output keeps `current_y` at 0.02 and proposes `candidate_next_y` of 0.03 after the synthetic time in `applies_after`. The replay companion exercises a sequence of quotes and checks the next observation before activating a wider working value in the simulated state.

```shell
python -m tools.research.adaptive_bid_gap_replay --example > replay.json
python -m tools.research.adaptive_bid_gap_replay --input replay.json
```

## Input contract

Use `--example` for the complete format. Prices and fractions are nonnegative decimal strings; Y fractions must be positive and at most 0.05. Times are integer UTC epoch seconds.

| Object | Fields and meaning |
| --- | --- |
| `terms` | The scope, effective signed ceiling `ceiling_y`, last working `current_y`, and pinned `model_sha256`. The ceiling is also the static threshold. Pass the latest reconciled current value, including an earlier tightening. A null terms object means there is no effective positive signed Y. A null current value in otherwise present terms requires recovery. Both conditions block buys and monitor with zero. Out-of-range historical terms are refused. |
| `observation` | Names the same scope and provides the capture time `as_of`, last trade price and exchange time, current best bid and its observation time. For this preview the bid time must match the capture second. `prior_block_active` must reflect **all** independent active risk, quality or entry blocks for that capture, including floor halt and daily stop. |
| `model` | Pins the scope and source ID, version, freeze time, first holdout forecast time, bar spacing, trailing lookback, sampled block length, forecast horizon, number of simulated paths, seed, cost hurdle in basis points, confidence cutoff, required historical calls, acceptable calibration gap, and direction-specific target thresholds. `model_sha256` is the SHA-256 of the sorted compact ASCII JSON encoding of this object. A digest match checks consistency with the input's declared terms. A trusted runtime would have to authenticate those terms and their backing evidence independently. |
| `history` | The scope, source ID and full contiguous series of bars. Each bar has a close time `end`, first publication time `known_at`, and integer simple return in basis points. All bars must have been available before the capture, within one bar of the cutoff for the latest feature. Each historical fold must use values known by its own forecast time. Missing bars, shifted first fold, a changed model digest, stale features or broader target values suppress adaptation. Supply source-versioned point-in-time observations; fabricated timestamps or revisions cannot be detected from JSON alone. |

The direction, horizon and target map must be fixed before examining the evaluation period. A bullish target may stage a wider threshold inside the authorized envelope. A bearish target can only hold or tighten the prior working threshold. An uncertain forecast or failed check does not restore a previous wider value.

## What generates a proposal

1. Compare the current bid with the last trade using the **previously applicable** Y and exact decimal arithmetic. For a trade over 30 seconds old, a bid at or below `last_trade × (1 − current_y)` triggers the bid-gap condition. Unavailable bid data cannot support a proposal. A prior block or a triggered gap suppresses all proposals for that quote. A fresh trade does not trigger this stale-trade rule; a bid already across the old threshold still prevents widening.
2. Sample consecutive blocks of trailing simple returns with replacement until the pinned horizon is covered. Compound the path and count it as up or down only when it exceeds the positive or negative cost hurdle. The remainder is neutral. The seeded generator is local to each forecast time. Require the nominal 95% Wilson lower bound on the fraction of simulated paths in the chosen direction to meet the pinned confidence cutoff. Choosing 0.75 illustrates one configuration; it is not a universal setting.
3. Walk forward through earlier non-overlapping forecast outcome windows using the same method and feature length. Keep calls and hits for the proposed direction. Require the pinned minimum call count, a nominal 95% hit-rate lower bound above or equal to the cutoff, and an observed difference between mean predicted probability and empirical hit rate within `max_calibration_gap`. The tool bounds input size and simulation work and scores all fully matured outcome windows on the fixed grid. A missing bar or unavailable historical feature invalidates the series.
4. Report a prospective target only. The replay companion applies its next-observation rules. A widening cannot clear an existing block, alter a prior quote or replace a loss budget. First signing or relaxing the signed ceiling, or expanding the signed policy, follows the existing D12 schedule. Moving inside the effective signed envelope does not change its date. Neither CLI writes owner records, issues authorizations, submits orders or modifies the signed runtime.

## Interpretation

The Monte Carlo frequency is conditional on the submitted returns and resampling method. Its statistical bound addresses sampling variation under that method. The holdout hit rate can still reflect regime persistence, selection and serial dependence; the nominal interval does not establish a guaranteed future probability. A recurrent positive directional probability does not prove that widening Y improves protection or excess returns.

Before seeking operational approval, compare static and adaptive Y on the same independently frozen, prospective quote and fill records, checking alert misses and delays, adverse price moves, excess blocks, execution costs, stale or unknown evidence, floor/daily-stop latches, restart continuity and timing. A model that cannot support that comparison remains in research. These fixtures do not authenticate real data, venue clocks, signed terms, a deployed model or actual Windows performance.

```shell
python -m unittest tools.research.test_adaptive_bid_gap_preview tools.research.test_adaptive_bid_gap_replay
```
