# Direction model study design (research only)

Status: proposed, 2026-11-24 (Asia/Seoul). Checklist item M11-T6, after the owner chose option (a) for O32: a
separate direction model in TRADEGEN research that uses QUANTGEN DIDM records and QuantGPT judgments as features.
This document is a design and has no code. It needs the owner decisions in section 10 before any implementation.

The study's forecasts are research inputs. They never become an order input, an approval or a signed term. Every
prohibition in `docs/direction-forecast-contract.md` section 5 applies:

- no import from the D14 code closure;
- no clearing of alerts, entry blocks, daily stops, floor halts or loss stops;
- the 5% maximum and the owner's signed ceiling stay;
- no producer access to orders, signatures, keys or `.env`.

## 1. The question and the default answer

**Question.** Can a direction forecast built from TRADEGEN's own price bars, plus DIDM records and QuantGPT
judgments, choose BR-26's working Y better than two alternatives?

- the static signed ceiling;
- a forecast from prices alone.

**Default answer.** No. The answer becomes yes only if every success criterion in section 7 holds on a forward
window registered before it opens. Without that evidence BR-26 keeps the static Y, as it does today.

**Prior.** The prior is weak. Public news reaches DIDM with a delay of minutes to days. Many participants see the
same news, and crypto direction over hours is hard to predict after costs. The design therefore tests the
incremental value of the news features over a price-only model, not just whether a model can pass a hit-rate gate.

## 2. Where the study sits

```text
TRADEGEN Upbit bars ─┐
DIDM snapshot ───────┼─> point-in-time feature table ─> frozen model ─> forecasts
QuantGPT snapshots ──┘         (owner PC, private)       (sha256)       (tradegen-direction-forecast-v1)
                                                                              │
                         BR-26 replay <── adapter (PR #75) <───────────────────┘
```

- **Price bars.** TRADEGEN's own Upbit record. A bar's `known_at` is when this PC actually had it.
- **DIDM.** Read only through `tools/research/didm_source_bridge.py` (PR #67, streaming fix PR #76). Features use
  the records the bridge selects as known at the forecast's `as_of`, which is decided by receipt time.
- **QuantGPT.** Its recorded outputs (M11-T7) are read as explicit snapshot files with a hash. A record counts as
  known at the later of its own `as_of` and its receipt on the owner's PC (contract section 3, rule 7). The model
  is never run during replay.
- **Model and forecasts.** All code lives in `tools/research/`. The fitted model, feature tables and forecasts stay
  in a private folder on the owner's PC: DIDM data rights are unverified, and forecasts are derived from them. Only
  code, this design and SHA-256 values go into the public repository.

## 3. Time scales

BR-26 works on two time scales:

- **Seconds.** Each quote is checked: a trade older than 30 seconds and a bid at or below `last × (1 − Y)` trigger
  the alert.
- **Hours.** A forecast only chooses which Y is in effect, and that working Y applies to later quotes until the
  forecast expires.

The inputs cannot support a seconds-scale forecast:

- GDELT arrives in 15-minute files.
- ALFRED, ECOS and OpenDART have only date precision; the bridge flags `PRECISE_RELEASE_TIME_UNAVAILABLE`.
- QuantGPT runs on request.

Proposal:

| Term | Proposed value | Reason |
| --- | --- | --- |
| Bar | 1 hour (`step_seconds` 3600) | The replay history holds at most 1,024 bars. Hourly bars give about 42 days, enough for one evaluation window; 15-minute bars give 10.7 days. |
| Horizon | 2 bars (7,200 s) | Up to 12 non-overlapping outcome windows per day. It is long enough for news received in the last hours to matter. It is the shortest the adapter allows. |
| Forecast time | Every bar close | The adapter (PR #75 after the PIT-1 fix) accepts only `as_of` on the bar grid. |
| Quotes | Unchanged, seconds | The forecast never changes the alert test itself, only the Y the test uses. |

## 4. Inputs and features

The feature set is fixed before training, with at most eight features. The study stops if a feature's
definition changes (section 8, S4).

| ID | Feature at `as_of` | Source | Known time |
| --- | --- | --- | --- |
| P1 | Log return of the last bar | TRADEGEN bars | bar `known_at` |
| P2 | Log return of the last 4 bars | TRADEGEN bars | bar `known_at` |
| P3 | Log return of the last 24 bars | TRADEGEN bars | bar `known_at` |
| P4 | Realized volatility over the last 24 bars | TRADEGEN bars | bar `known_at` |
| D1 | A new vintage received in the last 24 hours for a pre-registered macro series list (for example US CPI, payrolls, policy rate) | DIDM ALFRED, ECOS | `received_at` |
| D2 | GDELT event items received in the last 24 hours, divided by the trailing 7-day daily mean | DIDM GDELT | `received_at` |
| D3 | Mean `ess_like_0_100` of V0 scores known at `as_of` for event types `crypto_regulation_hack` and `monetary_policy` | DIDM V0 scores | score `received_at` and selected source |
| Q1 | Whether a QuantGPT judgment from a pre-registered set of risk news types was known in the last 24 hours | QuantGPT records | later of its `as_of` and receipt |

Rules:

- **Known times.** A feature uses only records known at or before `as_of`. Release dates and observation dates are
  never used as known times.
- **Missing data.** No imputation. A bar whose features are incomplete gets no forecast. Under the contract, no
  forecast means BR-26 keeps the working Y.
- **QuantGPT confidence.** Q1 is categorical. QuantGPT's confidence scores are uncalibrated (v0.1), so they are not
  used.
- **D3 is conditional.** The QUANTGEN collector writes no V0 scores, and the bridge reports `V0_MODEL_SCORES_MISSING`.
  D3 enters only if QUANTGEN produces scores for the whole training window before the model is frozen.
- **Q1 is conditional.** It enters only if M11-T7 records cover the whole training window. A feature without data is
  dropped before the freeze, never added later.

## 5. Model and baselines

- **Model M.** Multinomial logistic regression over `up`, `down` and `neutral`. The classes use the contract's
  hurdle: the compounded return over the window must clear plus or minus `hurdle_bps` net of costs.
  - The L2 penalty is fixed in advance.
  - Features are standardized with training-window statistics only.
  - Each class has at most nine coefficients.
  - It uses the standard library or packages already pinned in `constraints.txt`; nothing new is installed.
- **Baselines**, fitted and evaluated the same way on the same bars:
  - **B0:** training-window class frequencies.
  - **B1:** price-only, the same model with P1-P4.
  - **B2:** PR #70's moving-block forecast, as built into the replay.
- **One fit, then freeze.** M is fitted once on the training window and frozen. `model.sha256` is the SHA-256 of the
  coefficient file, and `frozen_at` is recorded. Refitting, retuning or changing features creates a new model
  version and therefore a new study (contract section 3, rule 5).

## 6. Pre-registration

These terms are fixed and recorded (M11-T4 form) before the evaluation window opens. The owner's choices in
section 10 supply the values.

- the model triple (name, version, sha256), market, bar, horizon and `hurdle_bps`;
- the feature definitions with their series and news-type lists, and the training-window dates;
- the adapter gate terms: `confidence`, `min_validation_calls` and `max_calibration_gap`;
- the target map `up_y` and `down_y`, at or below the signed ceiling;
- `evaluation_start`, `evaluation_end` and the interim check date;
- the success margin and the stop criteria (sections 7 and 8).

Sample size matters more than any threshold. The adapter gate needs the nominal 95% Wilson lower bound of the hit
rate to reach `confidence`. These are the non-overlapping calls needed if the true hit rate holds:

| `confidence` cutoff | True hit rate | Calls needed |
| --- | --- | --- |
| 0.55 | 0.60 | 381 |
| 0.60 | 0.65 | 369 |
| 0.60 | 0.70 | 93 |
| 0.75 | 0.80 | 289 |
| 0.75 | 0.85 | 73 |

With two-hour windows there are at most 12 windows a day. A 6-week evaluation (1,008 hourly bars, within the
replay's 1,024) gives at most 504 windows, and only a fraction will be calls. Realistic hit rates of 0.55 to 0.65
therefore need about 6 weeks or more, and high cutoffs such as 0.75 will usually end inconclusive. The study
reports that outcome honestly instead of extending the window.

## 7. Success criteria

All four must hold on the forward window.

1. **Adapter gate.** Non-overlapping calls reach `min_validation_calls`, the Wilson lower bound reaches
   `confidence`, and the calibration gap is within `max_calibration_gap`. The direction is up or down, whichever is
   acted on.
2. **Incremental value.** M's mean log loss is lower than B1's by at least the pre-registered margin, and the 95%
   interval of a day-block bootstrap excludes zero. M also beats B0. Without this, the news features add nothing and
   B1 or B2 is enough.
3. **BR-26 effect.** Adaptive Y and static Y are replayed on the same frozen quote records. Missed or delayed alerts
   do not increase; the tolerance is zero unless the owner sets another. Adverse price moves, excess blocks and
   unknown evidence are reported, as `docs/adaptive-bid-gap-preview.md` requires. One replay document holds at most
   128 observations, so the record is split into consecutive documents.
4. **Stability.** Criteria 1 and 2 also hold in each half of the window. This is a regime check.

Passing makes the model a candidate for the owner's decision M11-T5. It has no automatic effect.

## 8. Stop criteria

| ID | Trigger | Result |
| --- | --- | --- |
| S1 | A point-in-time violation, a hash mismatch, a refused snapshot, or more than 5% of bars without features | The window is void. A new window starts after the fix; windows are never spliced. |
| S2 | At the interim check (half the planned windows), the upper bound of M's log-loss improvement over B1 is at or below zero | Stop: no incremental value. |
| S3 | `evaluation_end` arrives with calls below `min_validation_calls` | Stop: inconclusive. The window is not extended. |
| S4 | Any change to features, model, thresholds or data sources after the window opens | Stop. A new study starts with a new model version. |
| S5 | A replay event that widens Y while a block, stop or alert is active | Stop and treat it as a bug. The replay's rules forbid it. |

## 9. Data collection plan

1. **Now.** There is no direction model yet. Code may be written and tested on synthetic data only.
2. **Prices.** Collection starts after the owner finishes O28 (A0 measurement) and lifts the Upbit no-call window.
   The record is a contiguous hourly bar record for the chosen market with real `known_at` times. Its source (the
   M9-T4 study record or a separate research recorder) is an owner decision.
3. **DIDM.** The owner runs the QUANTGEN collector on a fixed schedule and takes offline snapshots as in the O29
   guide. The bridge report at each snapshot gives the selected records. V0 scores are QUANTGEN's task.
4. **QuantGPT.** Under M11-T7, TRADEGEN's main session asked QUANTGEN on 2026-11-24 for periodic records
   (`as_of`, `issued_at`, model identity, snapshot hash); no answer yet. Q1 is possible only after those records
   exist.
5. **Training.** At least 4 weeks of complete aligned features: 672 hourly bars and 336 non-overlapping windows.
   Then the model is fitted and frozen.
6. **Evaluation.** The next 6 weeks run forward, with the terms of section 6 registered before they start.
7. **Owner decision (M11-T5).** It uses the report of sections 7 and 8.

At the earliest, training ends 4 weeks after price and DIDM collection start, and evaluation ends 6 weeks later.

## 10. Owner decisions

| # | Decision | Proposed |
| --- | --- | --- |
| 1 | Market, bar and horizon | KRW-BTC only, hourly bars, 2-hour horizon |
| 2 | Features | P1-P4 and D1-D2. D3 and Q1 only if their data covers the training window. |
| 3 | Price record source after O28 | Owner's choice: the M9-T4 study record or a separate research recorder |
| 4 | `hurdle_bps` | From TRADEGEN's measured fees, spread and slippage, not a guess |
| 5 | Gate terms and evaluation length | Chosen with the sample-size table in section 6 |
| 6 | Success margin | A log-loss margin over B1, and zero tolerance for missed or delayed alerts |
| 7 | Storage and data rights | A private folder outside Git and OneDrive. Confirm that DIDM-derived research use is allowed, since the bridge reports `DATA_RIGHTS_UNVERIFIED`. |
| 8 | Who builds the model | TRADEGEN research, as designed here, rather than a QUANTGEN producer |

## 11. Review against the edge-strategy-reviewer criteria

The skill's eight criteria, applied to this design. There is no position or exit: Y is a monitoring threshold, not
a trade.

| Criterion | Assessment |
| --- | --- |
| C1 Edge plausibility | Weak. The latency of public news makes the edge doubtful. Criterion 2 of section 7 tests exactly this, and the default answer is no. |
| C2 Overfitting risk | Controlled: at most 8 features, a fixed penalty, one fit, a frozen version and no tuning on the evaluation window. The feature lists still carry selection risk, so they are fixed before any training data is examined. |
| C3 Sample adequacy | The main risk. Realistic accuracy needs about 370 calls (section 6). An inconclusive result is likely and is reported as such. |
| C4 Regime dependency | Checked only by the half-window split. Six weeks covers few crypto regimes, so a pass is weak evidence. |
| C5 Exit calibration | Not applicable. Targets are Y values bounded by the signed ceiling. Tightening applies to the next observation; widening needs confirmation. |
| C6 Risk concentration | Not applicable. There is no position size or order, and Y stays at or below the signed ceiling and 5%. |
| C7 Execution realism | The hurdle is net of measured costs. Bars use real receipt times. Y does not change orders. |
| C8 Invalidation quality | Five specific stop rules (section 8). |

Overall: REVISE until the section 10 decisions are made. The design is not a trading strategy and is never
export-eligible.

## 12. Not in this document

- No code. After the owner decides, separate PRs add the following under `tools/research/`:
  - a point-in-time feature builder;
  - a fit-and-freeze tool;
  - a forecast writer that produces `tradegen-direction-forecast-v1` files privately.
- The M11-T4 pre-registration record.
- An OQ9 benefit metric. It is still undefined, so these forecasts can serve only offline study for OQ9, and no path
  leads to `entry_unblock`.

법률, 세무, 투자 조언이 아니며 면허를 가진 자문가가 아니다
