# Equity monitor and strategy candidate: offline research design

Status: **DRAFT, UNINTEGRATED, NOT APPROVED FOR PRODUCTION**.

This document separates a strategy signal, an account-equity monitor, realized-profit accounting, and execution authorization. It specifies an offline research candidate and diagnostics. It neither changes the approved odds model nor authorizes a live order, an owner signature, a limit change, or a merge.

Owner capital, percentages, profit goals, and deployment deadlines belong in a private owner profile outside the public repository. This public document uses parameters. The historical dates and numerical research results below identify the already committed S_C3 evidence; they are not an owner deployment schedule.

This is research and software design, not legal, tax, or investment advice. Neither the software nor its author is a licensed advisor. A return target is not a guaranteed result, and a monitoring threshold does not guarantee a fill at that threshold.

## 1. Parameters and distinct measurements

| Symbol | Meaning |
|---|---|
| `W0` | Initial contributed capital to protect; positive account-currency amount |
| `A` | Equity high-water-mark threshold that activates the proposed drawdown regime; `A >= W0` |
| `alpha` | Fraction of the preceding day's positive realized net profit used as the next day's loss budget; `0 <= alpha <= 1` |
| `delta` | Allowed fraction of the applicable high-water mark lost after activation; `0 <= delta < 1` |
| `g` | Minimum daily realized-return **target**, expressed as a fraction of opening equity; `g >= 0` |
| `E_start[d]` | Account equity at the specified start of Seoul day `d` |
| `E[t]` | Current marked account equity under the selected valuation convention |
| `H[t]` | Persistent, cash-flow-adjusted highest observed account equity, including `W0` |
| `P[d]` | Reconciled realized net trading profit assigned to Seoul day `d` |
| `F_raw[t]` | Floor requested by the piecewise equity rule |
| `F_effective[t]` | Floor actually in force after approval and limit-change timing rules |

Reject missing, non-finite, incorrectly typed, or internally inconsistent observations. Missing profit history is not zero profit. Missing market valuation is not a zero-valued holding. Missing owner parameters are not unlimited allowances.

The private profile must version the account currency, valuation convention, profit-accounting method, cash-flow handling, day boundary, and rounding policy. The diagnostic preview must not read an account's real private profile, credentials, or owner log; it receives explicit example inputs.

## 2. Equity protection is not a cash-reserve rule

Ignoring fees and price movement for this accounting illustration, buying assets worth `q*p` changes cash to `C-q*p` and holdings to `q*p`; total equity remains `C`. Therefore `E_start == W0` alone is not a universal mathematical reason to prohibit every purchase.

The existing odds `floor_safe` model makes a stronger promise within its model: cash remaining after entry must cover the floor and reserved exit costs even if the acquired asset loses its entire value. Its affordability inequality is:

`stake * (1 + entry_cost_rate) + fixed_entry_cost + exit_reserve <= cash - floor`.

That model correctly returns no affordable positive stake when cash equals the floor. Its code and evidence must remain unchanged for existing odds cards. The current `stop_based` affordability formula also provides no positive loss budget at that equality; changing the mode name is not a solution.

References: the approved odds design, [sizing section](2026-10-23-compliance-gate-and-odds-engine-design.md#71-plans-and-stakes), and the reviewed [affordability implementation at d773b6c](https://github.com/xkg4real/tradegen/blob/d773b6c44c73b82492d7d9ce89d4d76c8ea62110/core/odds/costs.py#L263).

This candidate instead examines equity observations and produces monitoring diagnostics. Equality with a floor must be represented separately from a breach below it; an `AT_BOUNDARY` diagnostic is neither an order permit nor proof of available trading capacity. Admission must also consider fees, spread, current holdings, stale observations, existing orders, and the approved execution policy. A projected post-fill fee loss cannot disappear from equity merely because the strategy signal is positive.

Threshold monitoring can request cancellation of new exposure and a permitted exit. It cannot ensure that equity never falls below the threshold during a price gap, stale quote, network outage, failed cancellation, or delayed/partial fill. A literal no-breach guarantee is not established by this design. The existing D3 rule concerning reaching the total-loss floor and any proposed equality/initial-session exception require an explicit reconciled specification before integration.

## 3. Daily realized-profit policy

Use Seoul calendar days and a single reconciled day-close record. A day starts from an explicit equity snapshot; a restart does not create another day or rewrite its opening equity.

| Prior-day state | Proposed daily policy diagnostic |
|---|---|
| `P[d-1] > 0` | Daily loss budget `B[d] = alpha * P[d-1]` |
| `P[d-1] < 0` | `B[d] = 0`; no new exposure on day `d`; permitted exits remain available |
| `P[d-1] == 0`, with complete reconciled history | The daily rule does not prohibit entry solely because profit was zero. Report the realized-profit target `g * E_start[d]`. A numeric loss budget for this branch is **unspecified**, not zero and not unlimited. Other risk and authorization checks still apply. |
| Verified first trading session | Evaluate the separately specified first-session exception; do not invent a previous profitable day or a loss allowance |
| Missing, stale, disputed, or incomplete previous-day history | `HISTORY_UNAVAILABLE`; no affirmative new-entry diagnostic |

The confirmed first-session exception must be persisted as a one-time lifecycle state. Restarting, reinstalling, renaming a plan, crossing a process boundary, or deleting a local cache must not reissue it. Its breadth is not yet specified: it does not silently waive the principal floor, high-water-mark policy, fees, code approval, or daily/total loss checks. A separate numeric first-session loss allowance has not been defined. The preview reports those missing decisions rather than manufacturing one.

An individual filled trade's loss and a day's net realized loss are different measurements. For the candidate day-close reporting convention, `P[d]` is a signed net sum, and a positive budget is exhausted when the selected intraday realized-loss accumulator reaches it. Whether that accumulator is net daily loss or the sum of losing trades must be decided before an execution gate uses it; profitable exits must not silently replenish a budget under an undocumented convention.

The target applies to the defined zero-profit-prior-day branch. Its diagnostic is `target_amount = g * E_start[d]`, with `realized_return = realized_net_profit_so_far / E_start[d]` when opening equity is valid and positive. It is a performance target, not evidence available before an order. Being below target cannot enlarge a loss budget, compel another trade, increase exposure, or imply that a forecasted return will be realized.

## 4. High-water-mark protection

For a validated and appropriately cash-flow-adjusted high-water mark `H`, the requested rule is:

```text
if H < A:
    F_raw = H
else:
    F_raw = max(W0, (1 - delta) * H)
```

Below activation, the full high-water mark is the requested floor; the rule does not merely protect original contributed capital. Above activation, the original-capital floor remains a lower bound. Below-floor, at-floor, and above-floor observations must remain distinct in the diagnostics.

At the activation boundary, the requested floor can decrease discontinuously: just below `A` it is close to `A`, while at `A` it becomes `max(W0, (1-delta)*A)`. This is a loosening, not an ordinary high-water-mark ratchet.

Preserve [owner decision D12](2026-10-23-compliance-gate-and-odds-engine-design.md#2-owner-decisions-fixed-inputs): tighten immediately; loosen only from the next Seoul date, outside an armed session, and never after a recorded halt. Accordingly:

- A stricter new floor may take effect immediately through the approved limit-change mechanism.
- A lower requested floor remains `PENDING_LOOSENING` until its eligibility and owner authorization are established; the prior effective floor continues to apply.
- Merely touching `A`, receiving another quote, or restarting does not lower `F_effective` during an armed session.
- A halted account is not automatically rehabilitated by a subsequent price rise or a regime transition.
- A preview may show both `F_raw` and a supplied `F_effective`; it does not activate either one or write an owner event.

The account-wide peak must survive day changes and restarts. Deposits, withdrawals, transfers, FX conversion, and splits must not masquerade as trading profits or manufacture activation. A cash-flow adjustment convention, and whether deposited capital changes `W0` or `A`, are pending profile decisions; ambiguous cash flows require a diagnostic rather than a guessed correction.

## 5. Accounting and valuation contract

Realized net profit and marked equity are maintained separately. For a closed quantity matched to recorded acquisition lots:

`realized_net_profit = sale_proceeds - exit_fees - transaction_taxes - allocated_acquisition_cost`.

Acquisition cost includes the matching purchase price and its allocated entry fees. The selected lot-matching method must be consistent and reconciled to the venue; FIFO or weighted-average matching must not be switched after observing a result. Partial fills and partial closes allocate quantities and costs exactly once. Corrections retain the original event reference and produce a reproducible amended day record.

Entry fees reduce cash and marked equity when charged even when their expense is allocated to realized P&L on a later sale. This timing difference is deliberate; the same fee must not be counted twice. An appreciated open position is not realized trading profit. Funding, income distributions, rebates, deposits, and withdrawals need explicit categories rather than automatic inclusion in `P[d]`.

Marked equity must account for cash, remaining inventory, liabilities if any, and already incurred costs. Whether to value inventory at last trade, executable bid, or estimated liquidation proceeds including fees is an unresolved production choice. A last-trade mark cannot be described as a guaranteed liquidation value. Quote freshness, currency conversion, and any stale or unavailable holding must be explicit inputs.

Income tax treatment is distinct from per-fill transaction costs. This draft does not equate before-income-tax odds outcomes with an after-tax owner profit goal. Cross-currency target reporting needs a defined valuation time and FX convention, not a silently fixed exchange rate.

Event requirements for future integration:

- A stable fill identifier, venue/account scope, order reference, execution time, ingestion time, quantity, price, fee currency, and fee amount.
- Idempotent processing of duplicate, late, corrected, and out-of-order fills; unknown fees remain unresolved rather than zero.
- Day assignment from the documented execution-time convention, with a reconciliation status for late events.
- Separate opening equity, realized profit, marked equity, requested/effective floor, and peak records.
- Versioned policy and valuation sources so an audit can reproduce each diagnostic.

The initial offline preview consumes reconciled aggregates supplied by its caller. It is not a tax-lot engine and must not label those inputs as independently reconciled broker facts.

## 6. Existing S_C3 evidence: preserve the baseline

The existing research implementation is [crypto_trend](../../../core/quant/strategies.py#L330). It is a causal daily long/flat signal, not a live order adapter.

1. Form four sign votes from price changes over lookbacks `(7, 14, 21, 28)` and five from price relative to SMAs `(10, 20, 50, 100, 200)`.
2. Average the nine votes. After the 200-row warm-up, switch the research weight to `1` only when the average is strictly greater than `+hysteresis`, to `0` only when strictly less than `-hysteresis`, and otherwise retain the prior state. Equality does not switch it.
3. Weight at row `t` uses data through `t` and is held over `t -> t+1`; [simulate](../../../core/quant/strategies.py#L69) deducts turnover costs from the daily marked return.

The research value `1` means full research exposure. It is not an instruction to invest all live account capital. Converting a signal to quantities, adding exit overrides, or changing allocation creates a separately evaluated strategy variant.

The [S_C3 card](../../asset_expansion/cards/S_C3_crypto_trend_krwbtc.json) and [walk-forward implementation](../../../core/quant/validate.py#L345) specify:

| Evidence field | Recorded value |
|---|---|
| Card | `S_C3_crypto_trend_krwbtc` |
| Input | Upbit KRW-BTC; 3,288 daily rows, 2017-09-25 through 2026-09-25 |
| OOS | 2,530 rows, 2019-10-23 through 2026-09-25 |
| Grid | `hysteresis = (0.0, 0.222, 0.444, 0.667, 0.889)` |
| Selection | IS 756 / OOS 126 / minimum IS 504 / embargo 1; 21 origins |
| Trial accounting | 11 total trials; 5 current configurations; seed 11 |
| Cost | 10 basis points per side; separate stress at twice the cost |
| OOS Sharpe | 1.2160250195674127 |
| OOS Sharpe 90% interval | 0.6248430923037298 to 1.7733635785645205 |
| Twice-cost Sharpe | 1.171394227006523 |
| OOS maximum drawdown | -0.4933830078830207 |
| Position changes | 138 |
| Last selected parameter | `hysteresis = 0.667` |
| Historical verdict | `PASS` under that study's criteria |

Each walk-forward origin selects the best IS configuration for the following OOS block. The last selected parameter is not the parameter used in every historical block. Freezing it for a new candidate is a new selection/deployment protocol. The literal `0.667` must not be changed to the different floating-point value `2/3` while claiming exact reproduction.

The approved [D13 replay at d773b6c](https://github.com/xkg4real/tradegen/blob/d773b6c44c73b82492d7d9ce89d4d76c8ea62110/core/oddsdata/replay.py) reads committed cache/card/results, runs `pnl_matrix`, `walk_forward`, and `score_strategy`, and returns plain data. It does not import the study runner, fetch live data, write results, or read a clock. Its input really is the Upbit cache despite the card's generic source-description text. The cache's final row was a running price in the original study; retain that limitation for historical reproduction, not as a precedent for live signal inputs.

Reproduction pins from [models.py at d773b6c](https://github.com/xkg4real/tradegen/blob/d773b6c44c73b82492d7d9ce89d4d76c8ea62110/core/odds/models.py#L524) and the cache-file assertion in [odds_replay.py](https://github.com/xkg4real/tradegen/blob/d773b6c44c73b82492d7d9ce89d4d76c8ea62110/tests/odds_replay.py#L80):

| Bytes or canonical object | MD5 |
|---|---|
| Cache file | `de7eaec6f45d0dc12b2950f50433b89d` |
| Canonical input series | `18ec83bdfe158efe4d648caf45ff849f` |
| OOS P&L little-endian float64 bytes | `bbdcf17ca9462567fe351c54644bef0c` |
| OOS turnover little-endian float64 bytes | `2d4edeb2f042c87fd1750d9c68e275f7` |
| Card file | `40b1e7bfadf6d16246e0012495064704` |
| Aggregate results file | `ca757e25f508b588cb2f361719ec83cd` |

These hashes identify the accepted research input/output, not live freshness, market truth, or order authorization. Exact reproducibility tests are in [odds_replay.py at d773b6c](https://github.com/xkg4real/tradegen/blob/d773b6c44c73b82492d7d9ce89d4d76c8ea62110/tests/odds_replay.py#L80); causal strategy checks are in [expansion_acceptance.py](../../../tests/expansion_acceptance.py#L294).

## 7. New strategy candidate and validation

Working candidate ID: `C3_EQUITY_MONITOR_DRAFT`. Status: **UNVALIDATED**. It must not use `replay:S_C3_crypto_trend_krwbtc` to claim the original card's verdict or outcomes.

The proposed candidate has separate stages:

1. Accept validated finalized bars, their timestamps, and prior signal state; reject provisional or stale inputs.
2. Compute the research signal with an explicitly chosen, versioned parameter-selection protocol.
3. Evaluate reconciled daily realized-profit policy and observed equity protection independently of the signal.
4. Produce diagnostics identifying whether a proposed entry is eligible for further checks, is at a boundary, has a pending limit change, lacks policy information, or is blocked. No diagnostic is an execution permit.
5. Only a future reviewed execution layer may combine this with owner approvals, instruments/venue rules, sizing, minimums, reservations, idempotency, and a live adapter.

A target unmet by the signal is reported as unmet. Do not search until a configuration appears to meet it, relabel a modified strategy as the frozen replay, or use the target as a reason to override risk checks. The original strategy's historical drawdown and PASS do not validate this overlay; compatibility depends on the chosen parameters and the full equity path. Daily marked research P&L also cannot be relabelled as daily realized profit.

Validation work is split into implementation verification and statistical research:

- **Implementation verification:** hand-calculated event paths for entry fees, partial exits, lot matching, duplicate/corrected fills, stale marks, FX changes, and cash-flow adjustments. Check distinct realized and marked outputs.
- **Policy boundaries:** positive/zero/negative/missing prior-day profit; first-session state and restart persistence; exact-floor and below-floor observations; activation just below/at/above `A`; deferred loosening; daily/total conflicts; permanent halt; exits remaining eligible for the approved exit path.
- **Signal fidelity:** warm-up, strict hysteresis equality, retained state, bar finalization, and future-data perturbations. Compare the baseline on exactly the original data and protocol without changing its pins.
- **Execution stress, simulated only:** fees/spread, delayed and partial fills, cancellation races, rejected exits, stale quotes, gaps, minimum lots, and a discontinuity beyond a protective threshold. Record overshoot rather than fabricating a threshold-price fill.
- **Statistical protocol:** preregister the candidate, parameter trials, objective, benchmark, cost model, and data split before selecting a configuration. Previously inspected S_C3 history is exploratory evidence for a new variant, not a fresh untouched confirmation set.
- **Candidate report:** realized-return distribution, marked drawdown, loss/target frequencies with sampling uncertainty, target-unmet days, inactivity, turnover, costs, floor overshoots, and sensitivity to the unresolved conventions. Do not turn zero observed events into a zero-probability claim.

No candidate return distribution or success probability is supplied by this document. No new research study has been run for it, and no fresh validation verdict has been earned.

## 8. Offline preview boundary

The standalone preview is implemented in [tools/research/equity_policy_preview.py](../../../tools/research/equity_policy_preview.py). It consumes explicit parameter values and supplied synthetic/reconciled observations, computes diagnostic arithmetic, and explains missing decisions. It is outside the production execution path. From the repository root, run its isolated checks with `python -m unittest discover -s tools/research -p 'test_*.py' -v`. These checks verify diagnostic behavior, not statistical strategy performance or live readiness.

It must produce no orders, permits, owner events, arming state, real-home state, live account requests, or credential reads. It must not patch the signed odds core, alter S_C3 evidence, bypass the compliance gate, or imply that an equity diagnostic is an approved live position size. Private profiles and outputs containing personal amounts are not committed to the public repository.

The preview is allowed to show the piecewise requested floor and daily target/budget calculations. It must distinguish unknown budget from zero budget, missing day history from verified zero profit, first session from restart, requested limit from effective limit, and target from achieved result. It does not implement fill accounting, select a trading strategy, or establish no-loss guarantees.

## 9. Decisions still required before production integration

| Decision | Why it cannot be guessed |
|---|---|
| Exact scope and expiry of the first-session exception | An exception to prior-day classification does not define a currency loss allowance or a waiver of capital protection |
| Loss budget for the verified zero-profit-prior-day branch | Trading eligibility and a return target do not specify how much loss is allowed |
| Daily loss accumulator and treatment of realized intraday gains | Net daily loss, sum of losing trades, and peak-to-current loss produce different stops |
| Equality/breach semantics and relationship to existing D3 | A monitor boundary must not silently rewrite the approved permanent-halt rule |
| Valuation, quote freshness, tax lots, fees, day close, and corrections | These determine the actual inputs to profit, high-water mark, and limits |
| Deposit/withdrawal and FX treatment | External cash flows must not manufacture a profitable day or activate the drawdown regime |
| Activation and D12 transition approval | A newly lower floor cannot take effect immediately merely because a threshold was crossed |
| Candidate parameter-selection and validation protocol | The final historical hysteresis is not automatically a validated live strategy |

These are explicit unresolved production decisions. They do not prevent documenting the requested formulas or testing diagnostics, and the preview must expose them instead of pretending that they are settled.

## 10. Integration sequence and preserved controls

The dependency sequence remains: owner-approved merge of [odds PR #4](https://github.com/xkg4real/tradegen/pull/4), then E1 account inquiry, E2 execution control against a dry-run adapter, and E3 live adapters one venue at a time. See [E1 design](2026-10-24-e1-account-inquiry-design.md#1-purpose-and-scope) and [E1 plan owner gates](../plans/2026-10-24-e1-account-inquiry.md#owner-gates-during-execution). This draft and the standalone preview are not E1 implementation or evidence that any stage is complete.

Preserve D11: a new-exposure refusal must not indiscriminately block a permitted position-reducing exit; conduct rules and the approved corrupt-state handling still apply. Preserve D12's timing and halt rules, D14's owner-only signatures, and existing non-credit/non-borrowing restrictions. The controller must not arm, sign with real keys, move money, place orders, or merge without the required owner authorization.

Changes to `floor_safe`, the signed core, a validated replay, or any actual order-admission rule require their own reviewed implementation and regression evidence. None is made by this document.
